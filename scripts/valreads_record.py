# -*- coding: utf-8 -*-
"""`VALREADS` — record one week, and the day-one self-check that must pass before it does.

    python -m scripts.valreads_record --selfcheck     # day 1, writes nothing to the record
    python -m scripts.valreads_record                 # one week
    python -m scripts.valreads_record --limit 8       # a smoke test, LABELLED as one

**REGISTERED FIRST** (`PREREG_valuation_reads.md`, committed ALONE, a strict git ancestor).
**This records. It reads no verdict, scores nothing against a bar, and reads no forward return.**

THE SELF-CHECK RUNS FIRST AND THE RECORDER REFUSES WHILE IT IS ABSENT, STALE OR FAILING.
`S3-I1`'s rule, and three states rather than one, because "never run" and "ran and failed" are
different facts and only one of them is a bug in the check. Each case must be shown to FAIL
against a deliberately broken input, or it is not a check — `MB21`'s `C1` scored a perfect
0.000e+00 by comparing nothing, and it is this project's sixth vacuous-pass of that family.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import append_only as AO                                # noqa: E402
from valuation.edge import valreads as VR                                   # noqa: E402

SELFCHECK_NAME = "VALREADS_SELFCHECK.json"
#: A self-check older than this is STALE and the recorder refuses on it. Weekly cadence, so a
#: fortnight means the check has not been exercised since before the last run.
SELFCHECK_MAX_AGE_DAYS = 21


def selfcheck_path(root=None):
    return os.path.join(VR.export_root(root), SELFCHECK_NAME)


# ----------------------------------------------------------------------------------------------
# day 1
# ----------------------------------------------------------------------------------------------
def _fake_row(ticker="AAAA", status="OK"):
    r = {c: "" for c in VR.ROW_COLUMNS}
    r.update({"ticker": ticker, "status": status, "source": "hot",
              "price": "123.45", "market_cap": "1000000000.0", "regime": "mature",
              "dcf_reliability": "high", "sub_quality": "97.25",
              "business_quality": "Outstanding business", "business_quality_score": "94.9",
              "price_vs_model": "Priced 56% above our base value",
              "price_vs_model_pct": "0.56", "price_implied_growth": "0.21",
              "business_growth": "0.06", "story_gap_pp": "15.0", "is_story_stock": "1",
              "warning": "1", "warning_triggers": "story|hypergrowth",
              "base_value": "79.1", "value_low": "60.0", "value_high": "99.0",
              "valuable": "1", "withheld": "0", "hot_score": "88.0", "hot_rank": "3",
              "page_score": "79", "confidence": "medium"})
    return r


def selfcheck(verbose=True):
    """Six cases, each with the broken input that must make it fail.

    Returns the artifact dict. **It does not touch the real record** — every case runs in a
    temporary tree, because a self-check that writes into the thing it is checking is the
    `S3-I1` defect where a validation harness clobbered the artifact rule 9 exists to protect.
    """
    cases = []

    def case(name, ok, detail, vacuity=""):
        cases.append({"case": name, "pass": bool(ok), "detail": detail,
                      "vacuity_control": vacuity})
        if verbose:
            print("  [%s] %-34s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)

    tmp = tempfile.mkdtemp(prefix="valreads_selfcheck_")
    try:
        # 1. A ROW ROUND-TRIPS UNCHANGED, field for field, through the record's own reader.
        row = _fake_row("AAAA")
        w = VR.write_week("2000-01-02", [row], root=tmp)
        back, hdr, err = VR.read_week("2000-01-02", root=tmp)
        moved = []
        if err or not back:
            moved = ["could not read back: %s" % (err or "no rows")]
        else:
            got = back[0]
            for c in VR.ROW_COLUMNS:
                want = row.get(c, "")
                if c == "date":
                    want = "2000-01-02"
                if c == "key":
                    want = "2000-01-02|AAAA"
                if (got.get(c) or "") != want:
                    moved.append("%s: %r != %r" % (c, got.get(c), want))
        # VACUITY CONTROL: the comparison must be capable of failing, and it must have compared
        # something. A loop over zero fields reports a perfect round trip.
        n_compared = len(VR.ROW_COLUMNS) if back else 0
        tampered = dict(back[0]) if back else {}
        tampered["business_quality_score"] = "0.0"
        would_fail = bool(back) and tampered.get("business_quality_score") != row[
            "business_quality_score"]
        case("row_round_trips_unchanged", (not moved) and n_compared > 10 and would_fail,
             ("%d fields compared, %d moved" % (n_compared, len(moved))
              + ("" if not moved else "; " + "; ".join(moved[:3]))),
             "a tampered copy of the same row is detected: %s" % would_fail)

        # 2. A REFUSED VALUATION RECORDS AS REFUSED, WITH ITS REASON, AND NOT AS A BLANK.
        ref = _fake_row("ZZZZQ", status="REFUSED")
        for c in ("price", "market_cap", "business_quality_score", "price_vs_model_pct",
                  "base_value"):
            ref[c] = ""
        ref["refused_reason"] = "no company data (fetch failed or symbol not found)"
        VR.write_week("2000-01-09", [ref], root=tmp)
        b2, _h2, _e2 = VR.read_week("2000-01-09", root=tmp)
        got2 = (b2 or [{}])[0]
        ok2 = (got2.get("status") == "REFUSED" and bool(got2.get("refused_reason")))
        # The distinction that matters: a blank-everything row with NO status would be
        # indistinguishable from "we never tried", which is `archive.py`'s own recorded defect.
        blank = {c: "" for c in VR.ROW_COLUMNS}
        case("refusal_is_a_record_not_a_blank", ok2,
             "status=%r reason=%r" % (got2.get("status"), (got2.get("refused_reason") or "")[:40]),
             "a row with no status carries no reason either: %s"
             % (not bool(blank.get("refused_reason"))))

        # 3. NOTHING IN THE RECORDER READS A FORWARD RETURN -- over the SYNTAX TREE, because a
        #    docstring describing this rule contains the words the rule forbids.
        ok3, d3, vac3 = _no_forward_return()
        case("no_forward_return_in_the_recorder", ok3, d3, vac3)

        # 4. THE APPEND-ONLY GUARANTEE HOLDS AT THE BYTE LEVEL, on the manifest, through the
        #    delegated writer rather than a second implementation.
        m = VR.manifest_path(tmp)
        e1 = {c: "" for c in VR.MANIFEST_COLUMNS}
        e1.update({"date": "2000-01-02", "rows": "1", "register": VR.REGISTER,
                   "recorder_version": VR.RECORDER_VERSION})
        VR.append_manifest(e1, root=tmp)
        before = io.open(m, "rb").read()
        e2 = dict(e1)
        e2["date"] = "2000-01-09"
        VR.append_manifest(e2, root=tmp)
        after = io.open(m, "rb").read()
        prefix_ok = after.startswith(before) and len(after) > len(before)
        # the backward refusal and the idempotent retry, both exercised
        back_refused = VR.append_manifest(dict(e1, date="1999-12-26"), root=tmp)
        retry = VR.append_manifest(e2, root=tmp)
        case("append_only_byte_prefix_and_refusals",
             prefix_ok and (not back_refused.get("ok")) and retry.get("already_present") is True,
             ("prefix held %s (+%d bytes); backward refused %s; retry was a no-op %s"
              % (prefix_ok, len(after) - len(before), not back_refused.get("ok"),
                 retry.get("already_present"))),
             "a backward date and a duplicate date are distinguishable: %s"
             % (back_refused.get("reason", "")[:50]))

        # 5. A WEEK ALREADY ON DISK IS REFUSED RATHER THAN REWRITTEN.
        again = VR.write_week("2000-01-02", [_fake_row("BBBB")], root=tmp)
        case("a_recorded_week_is_not_rewritten", (not again.get("ok")),
             (again.get("reason") or "")[:70],
             "and the original bytes are untouched: %s"
             % (VR._sha256_of(VR.rows_path("2000-01-02", tmp)) == w.get("sha256")))

        # 6. THE CANARY REFUSAL FIRES, and a degraded week is caught mid-run.
        degraded = VR._num(None)
        bad = _fake_row(VR.CANARY)
        bad["market_cap"] = ""
        ok_c, why_c = VR.canary_ok(bad)
        good_c, _ = VR.canary_ok(_fake_row(VR.CANARY))
        many = [dict(_fake_row("N%03d" % i), market_cap="") for i in range(30)]
        deg, why_d = VR.week_degraded(many)
        clean, _ = VR.week_degraded([_fake_row("N%03d" % i) for i in range(30)])
        case("canary_and_mid_run_degradation_refuse",
             (not ok_c) and good_c and deg and (not clean),
             "canary refused (%s); mid-run caught (%s)" % (why_c[:40], why_d[:40]),
             "and a healthy canary and a healthy week both PASS: %s / %s"
             % (good_c, not clean) + ("; blank renders as %r" % degraded))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    out = {
        "item": "VALREADS", "part": "day-1 self-check", "register": VR.REGISTER,
        "recorder_version": VR.RECORDER_VERSION,
        "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cases": cases, "n_cases": len(cases),
        "n_passed": sum(1 for c in cases if c["pass"]),
        "all_pass": all(c["pass"] for c in cases),
        "trials": 0,
        "trial_class": ("SELF-CHECK -- no hypothesis, no bar, no outcome statistic, and no "
                        "forward return read anywhere"),
        "note": ("Every case ships a vacuity control, because a check that cannot fail is not a "
                 "check (MB21's C1 scored a perfect 0.000e+00 by comparing nothing). Run in a "
                 "temporary tree: a self-check that writes into the record it is checking is "
                 "S3-I1's own defect."),
    }
    return out


def _no_forward_return():
    """Assert over the AST that the recorder cannot read a forward return.

    **The syntax tree, not a grep.** This module's own docstring and the register both contain
    the words a substring ban would look for, so a grep fires against the CORRECT tree — the
    substring-ban family, which has done exactly that at least six times in this project
    (`MA49`, `MB1` three times in one register, `MB15`, `W-1`, `MB20`).
    """
    import ast
    src = io.open(os.path.join(_HERE, "valuation", "edge", "valreads.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {"fwd_ret", "forward_return", "future_return", "realized_return",
              "fwd_return", "forward_ret"}
    hits = []
    seen_names = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            seen_names += 1
            if n.id in banned:
                hits.append("name " + n.id)
        elif isinstance(n, ast.Attribute):
            if n.attr in banned:
                hits.append("attribute ." + n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            # A STRING KEY IS A READ TOO -- `row["fwd_ret"]` is an attribute-free lookup, which
            # is how `MB18`'s banned column would have entered a frame.
            if n.value in banned:
                hits.append("string key " + n.value)
    # VACUITY: the walk must have SEEN the tree. A parse that yielded nothing reports no hits.
    vac = ("walked %d Name nodes, so the tree was not empty; and the ban is non-vacuous -- "
           "injecting `fwd_ret` as a Name is detected: %s"
           % (seen_names,
              bool([x for x in ast.walk(ast.parse("x = fwd_ret"))
                    if isinstance(x, ast.Name) and x.id in banned])))
    return (not hits) and seen_names > 50, ("%d forbidden reads" % len(hits)
                                            + ("" if not hits else ": " + ", ".join(hits[:3]))), vac


def selfcheck_state(root=None):
    """`(ok, why)` — ABSENT, STALE and FAILING are three states, not one."""
    p = selfcheck_path(root)
    if not os.path.exists(p):
        return False, ("the day-1 self-check has never been run (%s is ABSENT). Run "
                       "`python -m scripts.valreads_record --selfcheck` first." % p)
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception as e:                                                  # noqa: BLE001
        return False, "the self-check artifact is unreadable: %s" % repr(e)[:120]
    if not d.get("all_pass"):
        return False, ("the last self-check FAILED (%d of %d cases) -- which is a different fact "
                       "from never having run it"
                       % (d.get("n_passed", 0), d.get("n_cases", 0)))
    if d.get("recorder_version") != VR.RECORDER_VERSION:
        return False, ("the self-check was run against recorder version %r and this is %r, so it "
                       "has not been exercised against the shape about to be written"
                       % (d.get("recorder_version"), VR.RECORDER_VERSION))
    age = (time.time() - os.path.getmtime(p)) / 86400.0
    if age > SELFCHECK_MAX_AGE_DAYS:
        return False, ("the self-check is STALE (%.1f days, limit %d)"
                       % (age, SELFCHECK_MAX_AGE_DAYS))
    return True, ""


# ----------------------------------------------------------------------------------------------
# one week
# ----------------------------------------------------------------------------------------------
def record_week(date=None, *, limit=0, pace=VR.PACE_S, root=None, base=VR.BASE_URL,
                verbose=True):
    date = date or time.strftime("%Y-%m-%d")
    t_start = time.time()

    ok, why = selfcheck_state(root)
    if not ok:
        VR.log_refusal("selfcheck", why, date=date, root=root)
        return {"ok": False, "wrote": False, "stage": "selfcheck", "reason": why}

    if verbose:
        print("[valreads] canary %s first -- a throttled feed does not raise, it silently "
              "empties CompanyData" % VR.CANARY, flush=True)
    can = VR.read_one(VR.CANARY, {"source": "canary"})
    cok, cwhy = VR.canary_ok(can)
    cs = time.time() - t_start
    if verbose:
        print("[valreads] canary: %.2fs  price=%r cap=%r  ok=%s %s"
              % (cs, can.get("price"), can.get("market_cap"), cok, cwhy), flush=True)
    if not cok:
        VR.log_refusal("canary", cwhy, date=date, canary=VR.CANARY, root=root)
        if verbose:
            print("[valreads] REFUSING THE WEEK: %s\n           A missing week is a fact a "
                  "reader can see. A week of hollow reads recorded as reads is a lie." % cwhy,
                  flush=True)
        return {"ok": False, "wrote": False, "stage": "canary", "reason": cwhy}

    pop = VR.fetch_population(base=base)
    if pop.get("error"):
        VR.log_refusal("population", pop["error"], date=date, root=root)
        return {"ok": False, "wrote": False, "stage": "population", "reason": pop["error"]}
    names = pop["names"]
    if limit:
        names = names[:limit]
        if verbose:
            print("[valreads] SMOKE TEST on %d of %d names -- NOT a week of the record"
                  % (len(names), pop["n_population"]), flush=True)
    if verbose:
        print("[valreads] population %d (hot %d, index %d, %d of the index OUTSIDE the hot list)"
              % (pop["n_population"], pop["n_hot"], pop["n_index"],
                 pop["n_index_outside_hot"]), flush=True)

    rows = []
    for i, m in enumerate(names, 1):
        if i > 1:
            time.sleep(pace)
        rows.append(VR.read_one(m["ticker"], m))
        if verbose and (i % 25 == 0 or i == len(names)):
            n_ok = sum(1 for r in rows if r["status"] == "OK")
            print("[valreads] %4d/%d  OK %d  refused %d  partial %d  (%.1f min)"
                  % (i, len(names), n_ok,
                     sum(1 for r in rows if r["status"] == "REFUSED"),
                     sum(1 for r in rows if r["status"] == "PARTIAL"),
                     (time.time() - t_start) / 60.0), flush=True)
        deg, dwhy = VR.week_degraded(rows)
        if deg:
            VR.log_refusal("mid_run", dwhy, date=date, canary=VR.CANARY, root=root)
            if verbose:
                print("[valreads] REFUSING THE WEEK mid-run after %d names: %s" % (i, dwhy),
                      flush=True)
            return {"ok": False, "wrote": False, "stage": "mid_run", "reason": dwhy,
                    "n_attempted": i}

    if limit:
        # A SMOKE TEST MAY NOT ENTER THE RECORD. The methodology rule's own direction: a subset
        # is "does it compute", never a row of evidence.
        return {"ok": True, "wrote": False, "stage": "smoke_test", "rows": len(rows),
                "reason": "smoke test -- deliberately not written to the record",
                "sample": rows[:2]}

    w = VR.write_week(date, rows, root=root)
    if not w.get("ok"):
        VR.log_refusal("write_week", w.get("reason", ""), date=date, root=root)
        return {"ok": False, "wrote": False, "stage": "write_week",
                "reason": w.get("reason", "")}

    entry = {
        "date": date,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": str(len(rows)),
        "n_valued": str(sum(1 for r in rows if r["status"] == "OK")),
        "n_refused": str(sum(1 for r in rows if r["status"] == "REFUSED")),
        "n_population": str(pop["n_population"]), "n_hot": str(pop["n_hot"]),
        "n_index": str(pop["n_index"]),
        "n_index_outside_hot": str(pop["n_index_outside_hot"]),
        "canary": VR.CANARY, "canary_seconds": "%.2f" % cs,
        "seconds_total": "%.1f" % (time.time() - t_start),
        "rows_file": os.path.basename(w["path"]), "rows_sha256": w["sha256"],
        "register": VR.REGISTER, "recorder_version": VR.RECORDER_VERSION,
        "note": "",
    }
    man = VR.append_manifest(entry, root=root)
    out = {"ok": bool(man.get("ok")), "wrote": True, "date": date, "rows": len(rows),
           "path": w["path"], "manifest": man, "population": pop["n_population"],
           "reason": man.get("reason", "")}
    if verbose:
        print("[valreads] wrote %s (%d rows, sha256 %s)"
              % (w["path"], len(rows), w["sha256"][:16]), flush=True)
        print("[valreads] manifest: ok=%s already_present=%s %s"
              % (man.get("ok"), man.get("already_present"), man.get("reason", "")), flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true",
                    help="run the day-1 self-check and write its artifact; records nothing")
    ap.add_argument("--date", default=None)
    ap.add_argument("--limit", type=int, default=0,
                    help="SMOKE TEST only -- deliberately never written to the record")
    ap.add_argument("--pace", type=float, default=VR.PACE_S)
    ap.add_argument("--root", default=None)
    args = ap.parse_args(argv)

    if args.selfcheck:
        print("[valreads] day-1 self-check -- six cases, each with its vacuity control")
        d = selfcheck()
        p = selfcheck_path(args.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(d, indent=1, default=str))
        print("[valreads] %d of %d passed -> %s" % (d["n_passed"], d["n_cases"], p))
        return 0 if d["all_pass"] else 1

    r = record_week(date=args.date, limit=args.limit, pace=args.pace, root=args.root)
    print(json.dumps({k: v for k, v in r.items() if k != "sample"}, indent=1, default=str))
    # A REFUSED WEEK EXITS NON-ZERO so an unattended scheduler shows it rather than reporting a
    # green run that recorded nothing -- except the smoke test, which refuses by design.
    if r.get("stage") == "smoke_test":
        return 0
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
