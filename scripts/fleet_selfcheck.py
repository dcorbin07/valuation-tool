"""S3-I1 DAY-1 SELF-VERIFICATION. Under Don's ruling, no fleet book fills until this passes.

The register's section E6, and the run-#6 pattern: prove on the day, end to end, that a
DECLARED book's fills round-trip into append-only records that read back UNCHANGED -- and that
every refusal the convention promises actually fires.

IT RUNS AGAINST A REAL GIT REPOSITORY, not a mock. The declaration-before-fill rule is a
statement about commits (`declaration_commit`), so checking it against a stub would be checking
the stub. A temporary repo is initialised, a declaration is committed ALONE into it, and the
same code the fleet runs is pointed at that root.

NINE CHECKS, and every one of them must be able to FAIL -- a self-check that cannot fail is the
vacuous pass this record has caught six times:

  1. A valid declaration validates.
  2. Fills round-trip: recorded, read back, compared field-for-field.
  3. The hash chain verifies over the whole stream.
  4. A TAMPERED copy is REFUSED, and the break is located.
  5. An out-of-order (backward) sequence is REFUSED by the append-only writer.
  6. An UNCOMMITTED declaration refuses the fill.
  7. A declaration committed ALONGSIDE another file refuses the fill.
  8. A SHORT book refuses with no assignment provider and passes with one (S3-I3's seam).
  9. The A/B randomizer is deterministic, salted by the declaration, and roughly balanced.

`--book <id>` additionally RECORDS the outcome on that book's real stream, which is what
`fleet.selfcheck_state` reads and what gates every subsequent fill. Without it the run is a
dry check and records nothing.

Run:  python -m scripts.fleet_selfcheck            (dry)
      python -m scripts.fleet_selfcheck --book f1  (records the gate for book f1)
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import append_only as AO      # noqa: E402
from valuation.edge import fleet as F             # noqa: E402

BOOK = "selfcheck"


def _decl(side="long", with_short_fields=False) -> str:
    d = {
        "book": BOOK, "domain": "options", "hypothesis_class": "cost",
        "entry_rule": "synthetic: every order in the fixture",
        "structure": {"strike_selection": "moneyness", "moneyness": 0.90, "dte": [30, 45]},
        "universe": "fixture", "sizing": "1 contract", "concurrency_cap": 10,
        "side": side,
        "sells_premium": side == "short",
        "records_schema": [],
        "verdict_horizon": {"expected_fills_per_month": 30, "min_effect": 0.10,
                            "sigma": 1.0, "rho": 3.0, "alpha": 0.05,
                            "fills_needed": 60, "earliest_honest_read": "2026-10-23"},
        "verdict_grammar": ["SUPPORTED", "UNSUPPORTED", "NO CONCLUSION", "horizon-not-reached"],
        "trial": {"domain": "options", "charged_at": "first_verdict_read"},
        "o11_sentence": F.O11_SENTENCE,
    }
    if with_short_fields:
        # S3-I3's five fields, not S3-I1's original three -- the seam was reconciled to the
        # LANDED module on 2026-08-24 (runbook: confirm against the landed S3-I3, not the map).
        d["assignment_model"] = "at expiry per moneyness"
        d["margin_method"] = "cash_secured_put"
        d["spot_basis"] = "as_traded"
        d["early_assignment_flag"] = "O21's q-machinery"
        d["return_denominator"] = "secured_cash"
    return "# DECL " + BOOK + "\n\n```json\n" + json.dumps(d, indent=2) + "\n```\n"


def _git(root, *args):
    return subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True)


def _init_repo(root):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "selfcheck@valquo.local")
    _git(root, "config", "user.name", "fleet selfcheck")
    open(os.path.join(root, "README.md"), "w").write("fixture\n")
    _git(root, "add", "README.md")
    _git(root, "commit", "-q", "-m", "base")


def _commit_decl(root, text, alone=True):
    p = os.path.join(root, "DECL_" + BOOK + ".md")
    open(p, "w", encoding="utf-8", newline="\n").write(text)
    _git(root, "add", "DECL_" + BOOK + ".md")
    if not alone:
        open(os.path.join(root, "extra.py"), "w").write("# landed alongside\n")
        _git(root, "add", "extra.py")
    _git(root, "commit", "-q", "-m", "declare")
    return p


def _fills():
    """Three V5-grade fills, including one unfilled and one B-fallback."""
    return [
        {"symbol": "AAPL", "occ": "AAPL260918C00250000", "side": "buy", "arm": "A",
         "order_type": "market", "qty": 1, "quote_bid": 2.50, "quote_ask": 2.70,
         "quote_mid": 2.60, "limit_price": "", "fill_price": 2.70,
         "submitted_ts": "2026-08-24T15:00:00", "filled_ts": "2026-08-24T15:00:02",
         "time_to_fill_s": 2, "fate": "filled", "fallback": "", "venue": "SANDBOX"},
        {"symbol": "MSFT", "occ": "MSFT260918C00500000", "side": "buy", "arm": "B",
         "order_type": "limit_mid", "qty": 1, "quote_bid": 4.00, "quote_ask": 4.40,
         "quote_mid": 4.20, "limit_price": 4.20, "fill_price": 4.40,
         "submitted_ts": "2026-08-24T15:00:00", "filled_ts": "2026-08-24T15:01:03",
         "time_to_fill_s": 63, "fate": "filled", "fallback": "B-fallback", "venue": "SANDBOX"},
        {"symbol": "NVDA", "occ": "NVDA260918C00900000", "side": "buy", "arm": "B",
         "order_type": "limit_mid", "qty": 1, "quote_bid": 9.00, "quote_ask": 9.80,
         "quote_mid": 9.40, "limit_price": 9.40, "fill_price": "",
         "submitted_ts": "2026-08-24T15:00:00", "filled_ts": "", "time_to_fill_s": "",
         "fate": "unfilled", "fallback": "", "venue": ""},
    ]


def run(verbose=True) -> dict:
    checks, root = [], tempfile.mkdtemp(prefix="fleet_selfcheck_")

    def ck(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:220]})
        if verbose:
            print(("  PASS  " if ok else "  FAIL  ") + name + (("  -- " + str(detail)[:160])
                                                               if not ok else ""))

    try:
        _init_repo(root)
        text = _decl()
        _commit_decl(root, text)
        sha = F.declaration_sha(text)

        # 1 -------------------------------------------------------------- valid declaration
        p = F.parse_declaration(text)
        v = F.validate_declaration(p.get("declaration") or {}, book=BOOK)
        ck("1 a valid declaration validates", p["ok"] and v["ok"], v.get("refusals"))

        # A self-check has to seed its own gate, or check 2 refuses on the gate it exists to
        # establish. Recorded FIRST and re-stamped at the end with the real outcome.
        F.record(BOOK, "selfcheck", {"fate": "pass", "detail": F.harness_fingerprint()},
                 decl_sha=sha, root=root)

        gate = F.may_fill(BOOK, root)
        ck("1b the harness permits fills for a correctly declared book", gate["ok"],
           gate.get("reason"))

        # 2 ----------------------------------------------------------------- fills round-trip
        wrote = [F.record(BOOK, "fill", f, decl_sha=sha, root=root) for f in _fills()]
        rd = F.read_records(BOOK, root)
        got = [r for r in rd["rows"] if r.get("kind") == "fill"]
        same = len(got) == 3 and all(
            all(str(f.get(k, "")) == str(g.get(k, "")) for k in f)
            for f, g in zip(_fills(), got))
        ck("2 fills round-trip into records that read back unchanged",
           all(w.get("wrote") for w in wrote) and same,
           [w.get("reason") for w in wrote if not w.get("wrote")])

        # 3 ------------------------------------------------------------------- chain verifies
        chain = F.verify_chain(BOOK, root, decl_sha=sha)
        ck("3 the hash chain verifies over the whole stream",
           chain["ok"] and not chain.get("vacuous") and chain["n"] == 4, chain.get("reason"))

        # 4 --------------------------------------------------------------- tampering REFUSED
        rp = F.records_path(BOOK, root)
        backup = open(rp, "rb").read()
        rows, header, err = AO.read_rows(rp)
        rows[2]["fill_price"] = "999.99"                     # a fill silently improved
        with open(rp, "w", encoding="utf-8", newline="") as fh:
            import csv
            w = csv.DictWriter(fh, fieldnames=header)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in header})
        bad = F.verify_chain(BOOK, root, decl_sha=sha)
        ck("4 a tampered row is REFUSED and located",
           (not bad["ok"]) and bad.get("broken_at") == 2, bad)
        open(rp, "wb").write(backup)
        ck("4b the stream is restored byte-for-byte after the tamper test",
           open(rp, "rb").read() == backup)

        # 5 ------------------------------------------------- out-of-order write REFUSED
        # Seq zero: not on disk, and below every key that is. A DUPLICATE seq is a different
        # case and is correctly a no-op, so probing with one would have tested idempotency
        # under the name of ordering -- which is what the first cut of this check did.
        back = AO.append({"seq": "00000000", "kind": "fill", "book": BOOK},
                         rp, key="seq", columns=F.RECORD_COLUMNS, append_only=True)
        ck("5 an out-of-order sequence is REFUSED by the append-only writer",
           (not back["ok"]) and back.get("would_modify") is True, back.get("reason"))

        # 6 ------------------------------------------------- uncommitted declaration REFUSED
        r2 = tempfile.mkdtemp(prefix="fleet_selfcheck_uncommitted_")
        _init_repo(r2)
        open(os.path.join(r2, "DECL_" + BOOK + ".md"), "w", encoding="utf-8").write(text)
        g2 = F.may_fill(BOOK, r2)
        ck("6 an UNCOMMITTED declaration refuses the fill",
           (not g2["ok"]) and g2["code"] == "DECLARATION_NOT_COMMITTED", g2.get("code"))

        # 7 ------------------------------------------------ not-committed-alone REFUSED
        r3 = tempfile.mkdtemp(prefix="fleet_selfcheck_notalone_")
        _init_repo(r3)
        _commit_decl(r3, text, alone=False)
        g3 = F.may_fill(BOOK, r3)
        ck("7 a declaration committed ALONGSIDE another file refuses the fill",
           (not g3["ok"]) and g3["code"] == "DECLARATION_NOT_COMMITTED_ALONE", g3.get("code"))

        # 8 ---------------------------------------------------- the S3-I3 seam, both ways
        # RECONCILED AGAIN 2026-08-24, AFTER THE SEAM SETTLED WITH r1. The previous cut read
        # `F._S3I3_REGISTRATION` and `F._SB`, which existed only while this harness imported
        # r1's module and registered it AT IMPORT. Both are gone: `assignment.py` states that
        # *"fleet does not import this module"* and that registration is *"an explicit CALL and
        # never an import side effect"*, and this lane yielded to that. So the seam starts EMPTY
        # and the day-1 gate REGISTERS IT ITSELF -- which is also the honest shape, since the
        # runner is the composition root and this script stands in for the runner.
        from valuation.edge import assignment as ASSIGN        # the REAL module, never a stub
        shortd = F.parse_declaration(_decl("short", with_short_fields=True))["declaration"]

        v_no_first = F.validate_declaration(shortd, book=BOOK)
        ck("8a a SHORT book is REFUSED before anything registers -- the DEFAULT, not a "
           "contrived case",
           "SHORT_BOOK_WITHOUT_ASSIGNMENT" in v_no_first["refusals"], v_no_first["refusals"])

        reg = ASSIGN.register(F)
        ck("8b r1's LANDED provider satisfies the FROZEN interface with nothing aliased",
           reg.get("ok") and F.assignment_provider() is ASSIGN.PROVIDER, reg)

        ck("8c the required-short-field lists AGREE across the two lanes",
           tuple(F.REQUIRED_SHORT_FIELDS) == tuple(ASSIGN.REQUIRED_SHORT_FIELDS),
           (F.REQUIRED_SHORT_FIELDS, ASSIGN.REQUIRED_SHORT_FIELDS))

        v_yes = F.validate_declaration(shortd, book=BOOK)
        ck("8d a complete SHORT book validates once a provider is registered",
           v_yes["ok"], v_yes.get("refusals"))

        bad_reg = F.register_assignment_provider(object())
        ck("8e a provider that does NOT satisfy the interface is refused, and does not evict "
           "the working one",
           (not bad_reg["ok"])
           and len(bad_reg["missing"]) == len(F.ASSIGNMENT_INTERFACE["callables"])
           and F.assignment_provider() is ASSIGN.PROVIDER, bad_reg)

        missing_field = dict(shortd)
        missing_field.pop("margin_method")
        v_mf = F.validate_declaration(missing_field, book=BOOK)
        # 8f, not a second 8e -- the duplicate label was hiding one of two checks in the output.
        #
        # THIS IS THE CHECK THAT EARNED ITS KEEP TODAY. It asserted the delegated refusal
        # `SHORT_BOOK_REFUSED_BY_S3I3`, and when the seam settled it went RED against a tree
        # everything else called green: r1's provider exposes the three interface callables and
        # NOT `validate_declaration`, so making the delegation optional switched the short-field
        # rules silently OFF and a book missing `margin_method` validated cleanly. Presence is
        # now this harness's own gate, so the code it names is this harness's own.
        ck("8f a SHORT book missing an S3-I3 field is REFUSED, BY NAME",
           "MISSING_FIELD:margin_method" in v_mf["refusals"], v_mf["refusals"])

        contradiction = dict(shortd)
        contradiction["side"] = "long"                        # while sells_premium stays True
        v_cd = F.validate_declaration(contradiction, book=BOOK)
        ck("8g `side` and `sells_premium` must AGREE, or the declaration is refused",
           "SIDE_AND_SELLS_PREMIUM_DISAGREE" in v_cd["refusals"], v_cd["refusals"])

        # 9 ----------------------------------------------------------------- the randomizer
        syms = ["SYM%03d" % i for i in range(400)]
        arms = [F.arm(BOOK, "2026-08-24", s, sha) for s in syms]
        again = [F.arm(BOOK, "2026-08-24", s, sha) for s in syms]
        other = [F.arm(BOOK, "2026-08-24", s, "different-declaration-hash") for s in syms]
        share = arms.count("B") / float(len(arms))
        ck("9a the randomizer is deterministic", arms == again)
        ck("9b the declaration hash salts it, so the split is fixed when the declaration lands",
           arms != other)
        ck("9c the split is roughly balanced (0.40-0.60 over 400 draws)",
           0.40 <= share <= 0.60, "B share %.3f" % share)

        # 10 ------------------------------------------- reading the meter IS a recorded read
        m = F.read_meter(BOOK, [0.1, -0.05, 0.2], decl_sha=sha, root=root,
                         why="self-check, synthetic values")
        reads = [r for r in F.read_records(BOOK, root)["rows"] if r.get("kind") == "meter_read"]
        ck("10 a meter read is itself a record, flagged first-read and early",
           m.get("ok") and m["is_first_verdict_read"] and m["early"] and len(reads) == 1, m)

    except Exception as e:                                    # noqa: BLE001
        ck("RUN COMPLETED WITHOUT RAISING", False, repr(e))
    finally:
        for d in (root,):
            shutil.rmtree(d, ignore_errors=True)

    n_pass = sum(1 for c in checks if c["pass"])
    return {"instrument": "S3-I1 fleet harness day-1 self-verification",
            "harness_fingerprint": F.harness_fingerprint(),
            "checks": checks, "n_checks": len(checks), "n_pass": n_pass,
            "ok": n_pass == len(checks) and len(checks) >= 15}


# ===========================================================================================
# THE LIVE LEG -- against the REAL Tradier sandbox, on a REAL declared book
# ===========================================================================================
def run_live(book: str, verbose: bool = True) -> dict:
    """One real sandbox fill, recorded through the harness and read back bit-identical.

    `DECL_CEREMONY_RUNBOOK.md` section 1 requires this and it is the half the synthetic run
    cannot do: the synthetic checks prove the RULES, this proves the harness against a real
    broker, a real chain and the real records store. A harness that passes on fixtures and
    fails on a live quote has proved nothing about the fleet.

    SANDBOX ONLY, and pinned: `assert_sandbox` refuses any base but Tradier's sandbox host, so
    this cannot be pointed at a live account by editing a constant. One contract, one order.

    The tamper case runs on a COPY of the real stream, never on the stream itself -- proving
    detection must not corrupt the evidence it is proving something about.
    """
    from valuation.edge.paper_broker import PaperBroker, assert_sandbox, SANDBOX_BASE

    checks = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:220]})
        if verbose:
            print(("  PASS  " if ok else "  FAIL  ") + name
                  + (("  -- " + str(detail)[:170]) if not ok else ""))

    ck("L0 the broker base is PINNED to the sandbox",
       assert_sandbox(SANDBOX_BASE).startswith("https://sandbox.tradier.com"))

    b = PaperBroker()
    h = b.health()
    ck("L1 the sandbox account is reachable", bool(h.get("ok")) and bool(h.get("sandbox")),
       {k: h.get(k) for k in ("ok", "sandbox", "base")})
    if not h.get("ok"):
        return {"ok": False, "checks": checks, "reason": "sandbox unreachable"}

    gate = F.may_fill(book)
    ck("L2 the harness permits fills for the declared test-book", gate["ok"],
       gate.get("code") or gate.get("reason"))
    if not gate["ok"]:
        return {"ok": False, "checks": checks, "reason": gate.get("reason")}
    sha = gate["decl_sha"]

    # --- pick a REAL contract: nearest-ATM SPY call, 25-60 DTE, two-sided quote -------------
    spot = None
    q_spy = b.quotes(["SPY"]).get("SPY") or {}
    for k in ("last", "close", "prevclose"):
        try:
            spot = float(q_spy.get(k))
            break
        except (TypeError, ValueError):
            continue
    ck("L3 a real SPY spot is available", spot is not None, q_spy.get("last"))

    chain = b.provider.get_option_chain("SPY", dte_range=(25, 60)) or []
    usable = [c for c in chain
              if str(c.get("option_type")).lower() == "call"
              and c.get("bid") is not None and c.get("ask") is not None
              and float(c.get("ask") or 0) > 0
              and float(c.get("ask") or 0) >= float(c.get("bid") or 0)]
    ck("L4 the real chain returns usable two-sided calls", len(usable) > 0, len(chain))
    if not usable or spot is None:
        return {"ok": False, "checks": checks, "reason": "no usable contract"}

    pick = min(usable, key=lambda c: abs(float(c.get("strike") or 0) - spot))
    occ = pick.get("symbol")
    quote = {"bid": pick.get("bid"), "ask": pick.get("ask")}
    arm = F.arm(book, _dt.date.today().isoformat(), "SPY", sha)
    ck("L5 the F-1 randomizer assigns an arm and REPRODUCES it",
       arm in ("A", "B")
       and arm == F.arm(book, _dt.date.today().isoformat(), "SPY", sha), arm)

    # --- ONE real sandbox order -------------------------------------------------------------
    submitted = _dt.datetime.now().isoformat(timespec="seconds")
    limit = round(float(pick["ask"]), 2)          # marketable limit; arm A's convention
    # `place_option(occ, underlying, side, quantity, price=...)` -- LIMIT when a price is
    # given, MARKET otherwise. Priced at the ASK, which is `options_fill.DEFAULT_AGGRESSION
    # = 1.0`, the punishing convention every validated options number in this repo is net of.
    res = b.place_option(occ, "SPY", "buy_to_open", 1, price=limit)
    oid = PaperBroker.order_id(res)
    ck("L6 a REAL sandbox order was accepted and returned an id", bool(oid), res)

    order, filled_ts = {}, None
    for _ in range(12):
        order = b.order(oid) or {}
        st = str(order.get("status") or "").lower()
        if st in ("filled", "rejected", "canceled", "expired") or order.get("avg_fill_price"):
            break
        time.sleep(2.0)
    if order.get("avg_fill_price"):
        filled_ts = _dt.datetime.now().isoformat(timespec="seconds")
    # L7 WAS TOO WEAK AND IT LET A FABRICATED FILL THROUGH. Its first cut asserted only that
    # a status string existed, so it PASSED on `status: pending` while the record said
    # `fate: filled` at the limit price. What matters is not that the order finished -- a
    # marketable limit in a 15-minute-delayed sandbox legitimately rests -- but that the
    # RECORD AGREES WITH THE BROKER about what happened.
    st = str(order.get("status") or "").lower()
    try:
        execd = float(order.get("exec_quantity") or 0)
    except (TypeError, ValueError):
        execd = 0.0
    ck("L7 the broker reports a status this harness understands",
       st in ("filled", "pending", "open", "partially_filled", "rejected", "canceled",
              "cancelled", "expired"),
       {"status": order.get("status"), "exec_quantity": order.get("exec_quantity")})

    fields = F.fill_fields(symbol="SPY", occ=occ, side="buy_to_open", qty=1,
                           order_type="limit", quote=quote, order=order,
                           submitted_ts=submitted, filled_ts=filled_ts,
                           limit_price=limit, arm=arm, venue="TRADIER_SANDBOX")
    ck("L8 the fill record carries bid, ask and mid at submission (the columns V5 routed)",
       fields["quote_bid"] != "" and fields["quote_ask"] != "" and fields["quote_mid"] != "",
       {k: fields[k] for k in ("quote_bid", "quote_ask", "quote_mid")})

    before = F.read_records(book)["rows"]
    w = F.record_fill(book, fields)
    ck("L9 the fill was RECORDED through the harness's only write door",
       bool(w.get("wrote")), w.get("reason") or w.get("code"))

    # THE CHECK THAT WOULD HAVE CAUGHT THE FABRICATED FILL, and it is the load-bearing one.
    truthful = ((fields["fate"] == "filled" and execd > 0 and fields["fill_price"] != "")
                or (fields["fate"] in ("working", "rejected", "canceled", "expired")
                    and execd == 0 and fields["fill_price"] == "")
                or (fields["fate"] == "partial" and execd > 0))
    ck("L9b the RECORD AGREES WITH THE BROKER -- no fill price without an execution",
       truthful, {"fate": fields["fate"], "fill_price": fields["fill_price"],
                  "exec_quantity": order.get("exec_quantity"),
                  "status": order.get("status")})

    # --- read back and compare BIT-IDENTICAL ------------------------------------------------
    rows = F.read_records(book)["rows"]
    got = [r for r in rows if r.get("kind") == "fill"]
    same = bool(got) and all(str(fields[k]) == str(got[-1].get(k, "")) for k in fields)
    ck("L10 the record reads back UNCHANGED, field for field", same,
       [(k, fields[k], got[-1].get(k)) for k in fields
        if got and str(fields[k]) != str(got[-1].get(k, ""))][:4])
    ck("L11 the stream GREW by exactly one row", len(rows) == len(before) + 1,
       (len(before), len(rows)))

    chain_ok = F.verify_chain(book, decl_sha=sha)
    ck("L12 the hash chain verifies over the real stream",
       chain_ok["ok"] and not chain_ok.get("vacuous"), chain_ok.get("reason"))

    # --- the tamper case, RUN, on a COPY ----------------------------------------------------
    real = F.records_path(book)
    tmpdir = tempfile.mkdtemp(prefix="fleet_tamper_")
    try:
        os.makedirs(os.path.join(tmpdir, "data", "fleet"), exist_ok=True)
        shutil.copy(real, F.records_path(book, tmpdir))
        original = open(real, "rb").read()
        rws, header, err = AO.read_rows(F.records_path(book, tmpdir))
        rws[-1]["fill_price"] = "999.99"
        with io.open(F.records_path(book, tmpdir), "w", encoding="utf-8", newline="") as fh:
            wtr = csv.DictWriter(fh, fieldnames=header)
            wtr.writeheader()
            for r in rws:
                wtr.writerow({k: r.get(k) for k in header})
        bad = F.verify_chain(book, tmpdir, decl_sha=sha)
        ck("L13 a TAMPERED row is DETECTED and located (run, not assumed)",
           (not bad["ok"]) and bad.get("broken_at") == len(rws) - 1, bad.get("reason"))
        ck("L14 the REAL stream was never touched by the tamper test",
           open(real, "rb").read() == original)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # --- the refusals fire on the real repo -------------------------------------------------
    g_undeclared = F.may_fill("no-such-book-exists")
    ck("L15 an UNDECLARED book is refused on the real repo",
       (not g_undeclared["ok"]) and g_undeclared["code"] == "DECLARATION_MISSING",
       g_undeclared.get("code"))

    short_probe = dict(F.parse_declaration(_decl("short", with_short_fields=True))["declaration"])
    short_probe.pop("margin_method")
    v_sp = F.validate_declaration(short_probe, book=BOOK)
    ck("L16 a SHORT declaration missing an S3-I3 field is REFUSED",
       "SHORT_BOOK_REFUSED_BY_S3I3" in v_sp["refusals"], v_sp["refusals"])

    n_pass = sum(1 for c in checks if c["pass"])
    return {"ok": n_pass == len(checks), "checks": checks, "n_pass": n_pass,
            "n_checks": len(checks), "occ": occ, "arm": arm,
            "order_id": oid, "order_status": order.get("status"),
            "fill_price": fields["fill_price"], "quote": quote}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="record the outcome on this book's real stream")
    ap.add_argument("--live", action="store_true",
                    help="ALSO run the real-sandbox leg: one real fill on --book, recorded and "
                         "read back bit-identical (DECL_CEREMONY_RUNBOOK section 1)")
    ap.add_argument("--close", action="store_true",
                    help="close --book with a ZERO-CHARGE closing row (test-books only)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    print("S3-I1 fleet harness -- day-1 self-verification")
    out = run(verbose=not a.json)
    if a.json:
        print(json.dumps(out, indent=2))
    print("\n%d/%d synthetic checks passed" % (out["n_pass"], out["n_checks"]))

    # The self-check row is recorded BEFORE the live leg, because `may_fill` gates on it and
    # the live leg's whole point is to go through that gate rather than around it.
    if a.book:
        path = F.declaration_path(a.book)
        try:
            with open(path, encoding="utf-8") as fh:
                sha = F.declaration_sha(fh.read())
        except OSError:
            print("\nREFUSED to record: " + path + " not found. A self-check is recorded on a "
                  "DECLARED book's stream or not at all.")
            return 2
        w = F.record(a.book, "selfcheck",
                     {"fate": "pass" if out["ok"] else "fail",
                      "detail": F.harness_fingerprint()}, decl_sha=sha)
        print("recorded on %s: wrote=%s %s" % (a.book, w.get("wrote"), w.get("reason", "")))

    live = None
    if a.live:
        if not a.book:
            print("\nREFUSED: --live needs --book. A real fill is recorded on a DECLARED "
                  "book's stream or not at all.")
            return 2
        if not out["ok"]:
            print("\nREFUSED: the synthetic checks did not pass, so the live leg does not run. "
                  "Fix the harness, never the check.")
            return 1
        print("\n--- LIVE LEG: real Tradier sandbox, book %r ---" % a.book)
        live = run_live(a.book, verbose=not a.json)
        if a.json:
            print(json.dumps(live, indent=2))
        print("\n%d/%d live checks passed" % (live["n_pass"], live["n_checks"]))

    if a.close:
        if not a.book:
            print("\nREFUSED: --close needs --book.")
            return 2
        with open(F.declaration_path(a.book), encoding="utf-8") as fh:
            sha = F.declaration_sha(fh.read())
        c = F.record(a.book, "close",
                     {"fate": "closed",
                      "detail": ("ZERO-CHARGE CLOSE. This book carried no hypothesis and no "
                                 "bar; no meter was ever read on it, so no trial is charged "
                                 "in any domain (harness section 2: the charge comes at FIRST "
                                 "VERDICT READ, and there was none).")},
                     decl_sha=sha)
        print("\nclosed %s with a zero-charge row: wrote=%s %s"
              % (a.book, c.get("wrote"), c.get("reason", "")))

    ok = out["ok"] and (live is None or live["ok"])
    if not ok:
        print("\nFAILED -- under Don's ruling no fleet book fills until this passes.")
        return 1
    print("\nPASS -- the harness has verified itself"
          + (" against the REAL sandbox" if live else "")
          + "; declared books may begin filling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
