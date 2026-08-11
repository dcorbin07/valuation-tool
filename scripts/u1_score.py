#!/usr/bin/env python3
"""u1_score.py — score the U1 arms against bars fixed in an earlier commit.  [AUDIT U1]

    python -m scripts.u1_score

Pre-registered in `PREREG_u1_composite_entry.md` (sections 4-7, plus amendment 1 in section 10).
**Written after `scripts/u1_bar.py` had already banked the bars and after `U1_NULL.json` was
committed**, which is the whole point: this module READS the bars, it cannot set them.
`load_bars()` refuses to run at all if the artifact disagrees with the figures published in the
register by more than 5e-4, and a test fails if this file ever defines its own draw count,
percentile or selection bounds.

WHAT IT DECIDES. Four conditions, all fixed in section 7 before any of them was evaluated:

    V1  TOP10 gain > the NULL-PLAIN bar
    V2  TOP10 gain > the NULL-CAPMATCHED bar        (the ledger's reopen condition)
    V3  paired date-block CI95 on TOP10 - GRID excludes zero on the positive side
    V4  the TOP10 gain is positive in both halves of the window

PASS needs all four. REJECTED if the gain is negative or the decile table runs backwards.
Everything else is NULL, and ambiguous is a NULL.

THE CAVEAT TRAVELS: R2 stands. The shipped alert loses to random entry. U1 asks whether a
DIFFERENT entry works and a positive U1 would not make the alert tradeable.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.u1_bar import NULL_PATH                       # noqa: E402
from scripts.u1_entry import DATA, GRID_PATH, OUT_DIR      # noqa: E402
from valuation.edge import composite_entry as CE           # noqa: E402
from valuation.edge import options_stats as OS             # noqa: E402
from valuation.edge import options_veto as V               # noqa: E402

VERDICT_PATH = os.path.join(OUT_DIR, "U1_VERDICT.json")
SIGNAL_BOOK = os.path.join(DATA, "options_universe", "state_r2_corrected.pkl")
CONTROL_BOOKS = [os.path.join(DATA, "options_universe", "control_r2_seed%d.pkl" % s)
                 for s in range(5)]

# The figures published in `PREREG_u1_composite_entry.md` section 10. If the artifact and the
# register ever disagree, the honest move is to stop, not to prefer one silently.
BARS_IN_REGISTER = {"TOP10_PLAIN": 7.2870, "TOP10_CAPMATCHED": 9.4513}
BAR_TOL = 5e-4
DRAWS = 4000


def _fmt(x, p="+.4f"):
    return "n/a" if x is None else format(x, p)


def load_bars() -> dict:
    with open(NULL_PATH, "r", encoding="utf-8") as f:
        null = json.load(f)
    if null.get("verdict_basis") != "SPLIT_CLEAN":
        raise SystemExit("REFUSING TO SCORE: artifact verdict_basis is %r, expected SPLIT_CLEAN"
                         % null.get("verdict_basis"))
    for k, want in BARS_IN_REGISTER.items():
        got = float(null["bars"][k]["bar_pp"])
        if abs(got - want) > BAR_TOL:
            raise SystemExit("REFUSING TO SCORE: artifact bar %s = %.6f, register says %.4f"
                             % (k, got, want))
    return null


def verdict_of(gain_pp: float, v1: bool, v2: bool, v3: bool, v4: bool,
               backwards: bool) -> str:
    """Register section 7, as a function so a truth table can pin it.

    PASS needs ALL FOUR conditions. REJECTED if the gain is negative or the decile table runs
    the wrong way. Everything else is NULL — and "positive but does not clear a bar" is a NULL,
    not a near-miss worth arguing about. Ambiguous is a NULL.
    """
    if v1 and v2 and v3 and v4:
        return "PASS"
    if gain_pp < 0 or backwards:
        return "REJECTED"
    return "NULL"


def halves(rows, dates):
    cut = dates[len(dates) // 2]
    return ([r for r in rows if r["asof"] < cut],
            [r for r in rows if r["asof"] >= cut], cut)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U1 — score the arms against the committed bars.")
    ap.add_argument("--grid", default=GRID_PATH)
    ap.add_argument("--data-root", default=DATA)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--json", default=VERDICT_PATH)
    args = ap.parse_args(argv)

    null = load_bars()
    print("[U1] bars read from the artifact and reconciled with the register: "
          "TOP10 plain %+.4fpp, cap-matched %+.4fpp"
          % (null["bars"]["TOP10_PLAIN"]["bar_pp"],
             null["bars"]["TOP10_CAPMATCHED"]["bar_pp"]), flush=True)

    with open(args.grid, "rb") as f:
        raw = pickle.load(f)["rows"]
    splits = CE.load_splits(args.data_root)
    grid, dropped = CE.drop_split_spanners(raw, splits)
    dates = sorted({r["asof"] for r in grid})
    base = CE.mean_pnl(grid)
    print("[U1] grid %d trades (%d dropped by U1-SPLIT), %d dates, mean %+.4f%%"
          % (len(grid), len(dropped), len(dates), 100 * base), flush=True)

    out = {"item": "U1", "n_grid": len(grid), "n_dropped_u1_split": len(dropped),
           "n_dates": len(dates), "grid_mean_pct": base,
           "bars": {k: null["bars"][k]["bar_pp"] for k in sorted(null["bars"])},
           "arms": {}, "verdict_inputs": {}}

    # ---- diagnostic reported BEFORE any verdict: does the composite predict whether a
    # contract even exists? If it did, the grid would be a biased sample of the rule.
    conv = []
    for q in range(10):
        lo, hi = 1.0 - (q + 1) / 10, 1.0 - q / 10
        sel = [r for r in grid if lo <= float(r["u1_pct_univ"]) < hi or
               (q == 0 and float(r["u1_pct_univ"]) >= hi)]
        conv.append({"decile": q + 1, "n": len(sel)})
    out["cells_per_decile"] = conv

    # ---- the arms ------------------------------------------------------------------------
    for arm, (lo, hi) in sorted(CE.ARMS.items()):
        rows = CE.select(grid, lo, hi)
        m = CE.mean_pnl(rows)
        gain_pp = 100.0 * (m - base)
        rec = {"n_trades": len(rows), "mean_pct": m, "gain_pp": gain_pp}
        for flavour in ("PLAIN", "CAPMATCHED"):
            key = "%s_%s" % (arm, flavour)
            b = null["bars"][key]
            rec[flavour] = {
                "bar_pp": b["bar_pp"],
                "clears": bool(gain_pp > b["bar_pp"]),
                "percentile_in_null": CE.arm_position(b["draws_pp"], gain_pp),
                "null_median_pp": b["median_pp"], "null_max_pp": b["max_pp"]}
        boot = V.fast_block_diff(rows, grid, seed=0, draws=args.draws)
        rec["date_block"] = boot
        e, l, cut = halves(rows, dates)
        ge, gl = CE.mean_pnl(e), CE.mean_pnl(l)
        eg = [r for r in grid if r["asof"] < cut]
        lg = [r for r in grid if r["asof"] >= cut]
        rec["halves"] = {"cut": cut,
                         "early_gain_pp": (100.0 * (ge - CE.mean_pnl(eg))) if ge else None,
                         "late_gain_pp": (100.0 * (gl - CE.mean_pnl(lg))) if gl else None,
                         "n_early": len(e), "n_late": len(l)}
        rest = [r for r in grid if r.get("u1_pct_univ") is not None
                and not (lo <= float(r["u1_pct_univ"]) < hi)]
        rec["sign_test_vs_rest_of_grid"] = OS.paired_name_year(rows, rest)
        out["arms"][arm] = rec

        print("\n[U1] %-6s n=%4d  mean %+8.4f%%  gain %+8.4fpp" % (arm, len(rows), 100 * m,
                                                                   gain_pp))
        for flavour in ("PLAIN", "CAPMATCHED"):
            r_ = rec[flavour]
            print("        vs %-10s bar %+8.4fpp -> %-7s  arm sits at the %5.1fth pct "
                  "(null median %+.4f)"
                  % (flavour, r_["bar_pp"], "CLEARS" if r_["clears"] else "FAILS",
                     r_["percentile_in_null"] or float("nan"), r_["null_median_pp"]))
        if boot.get("ok"):
            print("        date-block CI95 [%+.4f, %+.4f]pp over %d months, excl0=%s pos=%s"
                  % (100 * boot["ci95"][0], 100 * boot["ci95"][1], boot["n_blocks"],
                     boot["excludes_zero"], boot["positive_at_significance"]))
        print("        halves: early %s  late %s"
              % (_fmt(rec["halves"]["early_gain_pp"]), _fmt(rec["halves"]["late_gain_pp"])))
        st = rec["sign_test_vs_rest_of_grid"]
        print("        sign test vs the rest of the grid: %d/%d cells won (%s), z %s, p %s"
              % (st.get("n_wins", 0), st.get("n_cells", 0),
                 _fmt(st.get("win_rate"), ".1%"), _fmt(st.get("sign_test_z"), "+.4f"),
                 _fmt(st.get("sign_test_p"), ".4f")))

    # ---- mechanism: the decile table, with the median beside the mean ---------------------
    # THE MEDIAN COLUMN IS THE POINT AND IT IS REPORTED WHATEVER THE VERDICT. An options book's
    # mean is a right-tail average; if the composite carried information about the typical trade
    # the medians would separate. Reporting mean-only would let a tail difference read as a
    # signal, which is the error `winsorised` exists to catch elsewhere in this lane.
    out["decile_table"] = CE.decile_table(grid)
    for d in out["decile_table"]:
        lo, hi = d["pct_range"]
        sel = [r for r in grid if lo <= float(r["u1_pct_univ"]) < hi
               or (d["decile"] == 1 and float(r["u1_pct_univ"]) >= hi)]
        v = sorted(float(r["pnl_pct"]) for r in sel if r.get("pnl_pct") is not None)
        d["median_pnl_pct"] = v[len(v) // 2] if v else None
        cap = CE.percentile(v, 99.0) if v else None
        d["winsorised_p99_mean_pct"] = (sum(min(x, cap) for x in v) / len(v)) if v else None
    print("\n[U1] expectancy by composite decile (1 = BEST composite), split-clean grid:")
    for d in out["decile_table"]:
        print("   D%-2d n=%4d  mean %+8.3f%%  winsor %+8.3f%%  MEDIAN %+8.3f%%  win %s"
              % (d["decile"], d["n_trades"], 100 * (d["mean_pnl_pct"] or 0),
                 100 * (d["winsorised_p99_mean_pct"] or 0),
                 100 * (d["median_pnl_pct"] or 0), _fmt(d["win_rate"], ".1%")))

    # ---- how much of each arm is its own right tail ----------------------------------------
    gv = sorted(float(r["pnl_pct"]) for r in grid if r.get("pnl_pct") is not None)
    gcap = CE.percentile(gv, 99.0)
    g_w = sum(min(x, gcap) for x in gv) / len(gv)
    out["tail_dependence"] = {"grid_winsorised_mean_pct": g_w, "grid_cap_pct": gcap}
    for arm in sorted(CE.ARMS):
        rows = CE.select(grid, *CE.ARMS[arm])
        v = sorted(float(r["pnl_pct"]) for r in rows if r.get("pnl_pct") is not None)
        cap = CE.percentile(v, 99.0)
        w = sum(min(x, cap) for x in v) / len(v)
        top5 = sum(v[-5:]) / len(v)
        out["tail_dependence"][arm] = {
            "winsorised_mean_pct": w, "winsorised_gain_pp": 100.0 * (w - g_w),
            "top5_contribution_pp": 100.0 * top5,
            "top5_share_of_mean": (top5 / (sum(v) / len(v))) if sum(v) else None,
            "median_pct": v[len(v) // 2]}
        out["arms"][arm]["winsorised_gain_pp"] = 100.0 * (w - g_w)
        print("   %-6s winsorised gain %+7.4fpp | top-5 trades are %+.3fpp of a %+.3f%% mean"
              % (arm, 100.0 * (w - g_w), 100 * top5, 100 * (sum(v) / len(v))))

    # ---- the comparison books -------------------------------------------------------------
    with open(SIGNAL_BOOK, "rb") as f:
        alert_raw = pickle.load(f)["rows"]
    alert, a_drop = CE.drop_split_spanners(alert_raw, splits)
    ctrl_raw = []
    for p in CONTROL_BOOKS:
        with open(p, "rb") as f:
            ctrl_raw.extend(pickle.load(f))
    ctrl, c_drop = CE.drop_split_spanners(ctrl_raw, splits)
    out["comparison"] = {
        "alert_book": {"n_raw": len(alert_raw), "n": len(alert),
                       "mean_pct": CE.mean_pnl(alert), "mean_pct_raw": CE.mean_pnl(alert_raw)},
        "random_day_control_5seed": {"n_raw": len(ctrl_raw), "n": len(ctrl),
                                     "mean_pct": CE.mean_pnl(ctrl),
                                     "mean_pct_raw": CE.mean_pnl(ctrl_raw)},
        "grid_vs_alert_pp": 100.0 * (base - CE.mean_pnl(alert)),
        "top10_vs_alert_pp": 100.0 * (CE.mean_pnl(CE.select(grid, *CE.ARMS["TOP10"]))
                                      - CE.mean_pnl(alert)),
        "note": ("Different calendars: the alert book is event-driven daily over 2016-2025, the "
                 "grid is 39 quarterly dates. These are per-trade expectancies on two different "
                 "sampling schemes and the difference is NOT a paired statistic.")}
    c = out["comparison"]
    print("\n[U1] comparison books (all split-clean):")
    print("   alert book        n=%5d  mean %+8.4f%%   (raw %+8.4f%%)"
          % (c["alert_book"]["n"], 100 * c["alert_book"]["mean_pct"],
             100 * c["alert_book"]["mean_pct_raw"]))
    print("   random-day ctrl   n=%5d  mean %+8.4f%%   (raw %+8.4f%%)"
          % (c["random_day_control_5seed"]["n"],
             100 * c["random_day_control_5seed"]["mean_pct"],
             100 * c["random_day_control_5seed"]["mean_pct_raw"]))
    print("   GRID vs alert %+.4fpp   TOP10 vs alert %+.4fpp"
          % (c["grid_vs_alert_pp"], c["top10_vs_alert_pp"]))

    # ---- the five pooled seeds, the register's own control --------------------------------
    top = CE.select(grid, *CE.ARMS["TOP10"])
    counts, _ = CE.arm_shape(top, match_tier=False)
    pool = {}
    for r in grid:
        pool.setdefault(r["asof"], []).append(r)
    seed_rows = []
    for s in range(5):
        drawn, _sf = CE.draw_null(pool, counts, seed=s)
        seed_rows.extend(drawn)
    out["five_pooled_seeds"] = {"n": len(seed_rows), "mean_pct": CE.mean_pnl(seed_rows),
                                "gain_pp": 100.0 * (CE.mean_pnl(seed_rows) - base)}
    print("   five pooled seeds n=%5d  mean %+8.4f%%  gain %+8.4fpp"
          % (len(seed_rows), 100 * out["five_pooled_seeds"]["mean_pct"],
             out["five_pooled_seeds"]["gain_pp"]))

    # ---- the verdict ----------------------------------------------------------------------
    t = out["arms"]["TOP10"]
    dt = out["decile_table"]
    v1 = t["PLAIN"]["clears"]
    v2 = t["CAPMATCHED"]["clears"]
    v3 = bool((t["date_block"] or {}).get("positive_at_significance"))
    v4 = bool(t["halves"]["early_gain_pp"] is not None
              and t["halves"]["late_gain_pp"] is not None
              and t["halves"]["early_gain_pp"] > 0 and t["halves"]["late_gain_pp"] > 0)
    backwards = bool((dt[0]["mean_pnl_pct"] or 0) < (dt[-1]["mean_pnl_pct"] or 0))
    out["verdict_inputs"] = {"V1_clears_plain_bar": v1, "V2_clears_capmatched_bar": v2,
                             "V3_date_block_positive": v3, "V4_positive_both_halves": v4,
                             "gain_negative": bool(t["gain_pp"] < 0),
                             "decile_table_backwards": backwards}
    verdict = verdict_of(t["gain_pp"], v1, v2, v3, v4, backwards)
    out["VERDICT"] = verdict
    out["failed_conditions"] = [k for k, ok in (("V1", v1), ("V2", v2), ("V3", v3), ("V4", v4))
                                if not ok]

    print("\n[U1] V1 plain bar %s | V2 cap-matched bar %s | V3 date-block %s | V4 halves %s"
          % (v1, v2, v3, v4))
    print("[U1] VERDICT: %s   (failed: %s)"
          % (verdict, ", ".join(out["failed_conditions"]) or "none"))

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("[U1] -> %s" % args.json, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
