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
import json
import os
import shutil
import subprocess
import sys
import tempfile

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
        "records_schema": [],
        "verdict_horizon": {"expected_fills_per_month": 30, "min_effect": 0.10,
                            "sigma": 1.0, "rho": 3.0, "alpha": 0.05,
                            "fills_needed": 60, "earliest_honest_read": "2026-10-23"},
        "verdict_grammar": ["SUPPORTED", "UNSUPPORTED", "NO CONCLUSION", "horizon-not-reached"],
        "trial": {"domain": "options", "charged_at": "first_verdict_read"},
        "o11_sentence": F.O11_SENTENCE,
    }
    if with_short_fields:
        d["assignment"] = "at expiry per moneyness; early flagged via O21's q-machinery"
        d["margin"] = "Reg-T cash-secured"
        d["secured_cash_is_denominator"] = True
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
        shortd = F.parse_declaration(_decl("short", with_short_fields=True))["declaration"]
        v_no = F.validate_declaration(shortd, book=BOOK)
        ck("8a a SHORT book is REFUSED with no assignment provider registered",
           "SHORT_BOOK_WITHOUT_ASSIGNMENT" in v_no["refusals"], v_no["refusals"])

        class _Stub:                                          # satisfies ASSIGNMENT_INTERFACE
            def assign_at_expiry(self, *a, **k):
                raise NotImplementedError("S3-I3 is r1's; this stub only proves the seam")

            def early_assignment_flag(self, *a, **k):
                raise NotImplementedError("S3-I3 is r1's; this stub only proves the seam")

            def secured_cash(self, *a, **k):
                raise NotImplementedError("S3-I3 is r1's; this stub only proves the seam")

        reg = F.register_assignment_provider(_Stub())
        v_yes = F.validate_declaration(shortd, book=BOOK)
        bad_reg = F.register_assignment_provider(object())
        F._PROVIDER = None                                    # leave no provider registered
        ck("8b a SHORT book validates once a provider satisfying the interface is registered",
           reg["ok"] and v_yes["ok"], v_yes.get("refusals"))
        ck("8c a provider that does NOT satisfy the interface is refused",
           (not bad_reg["ok"]) and len(bad_reg["missing"]) == 3, bad_reg)
        ck("8d the seam is left EMPTY -- this run registers no provider permanently",
           F.assignment_provider() is None)

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="record the outcome on this book's real stream")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    print("S3-I1 fleet harness -- day-1 self-verification")
    out = run(verbose=not a.json)
    if a.json:
        print(json.dumps(out, indent=2))

    if a.book:
        path = F.declaration_path(a.book)
        try:
            sha = F.declaration_sha(open(path, encoding="utf-8").read())
        except OSError:
            print("\nREFUSED to record: " + path + " not found. A self-check is recorded on a "
                  "DECLARED book's stream or not at all.")
            return 2
        w = F.record(a.book, "selfcheck",
                     {"fate": "pass" if out["ok"] else "fail",
                      "detail": F.harness_fingerprint()}, decl_sha=sha)
        print("\nrecorded on %s: wrote=%s %s" % (a.book, w.get("wrote"), w.get("reason", "")))

    print("\n%d/%d checks passed" % (out["n_pass"], out["n_checks"]))
    if not out["ok"]:
        print("FAILED -- under Don's ruling no fleet book fills until this passes.")
        return 1
    print("PASS -- the harness has verified itself; declared books may begin filling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
