# -*- coding: utf-8 -*-
"""`STAGE1-BATCH2` — the terminal-window sensitivity, and the answer to a 10pp question.

    python -m scripts.stage1_batch2_terminal

**THE QUESTION.** The incumbent's late half reads **1.88%/yr** on the build quadrant while SPY
returned roughly 11-12%/yr over calendar 2015-2019. Real, or a defect?

**REAL, AND THE COMPARISON AS POSED IS THE WRONG OBJECT.** Checked against the panel's OWN
`bench_ret` on the IDENTICAL windows and annualised by the SAME function:

* the panel's benchmark late half is **5.69%/yr**, not 11-12%, so the book lags by **3.81pp** and
  not by ten;
* because the quadrant's own `BUILD_END` is **2019-12-31**, and a 63-trading-day FORWARD window
  from that date lands in **2020-04** — the benchmark's terminal window returns **-23.05%**,
  which is COVID 2020Q1;
* **drop that single window and the benchmark late half reads 12.00%/yr**, which is exactly the
  figure the question quoted. So the 11-12% is a CALENDAR-period return and every figure in this
  batch is a mean of FORWARD windows. Two different objects.

`S10` already measured this book's drawdown as spanning *"exactly ONE 63-day period on every arm,
at the same trough index — COVID 2020Q1"*, so the quarter dominating the terminal window is the
one that register names.

**AND IT CHANGES NO VERDICT, WHICH IS WHAT MATTERS FOR THE BATCH.** Don's rule judges each arm
against the incumbent on the SAME windows, so a shock common to both cancels. Re-running both
construction arms without the terminal window leaves `B1` and `B2` **REJECTED**, and both still
fail on the EARLY half's return, which the terminal window cannot touch.

**ONE FIGURE DOES MOVE, AND IT IS REPORTED RATHER THAN LEFT TO BE DISCOVERED.** `B1`'s late-half
drawdown gain is **+5.471pp** as registered and **+0.045pp** without that window — so `B1`'s
apparent drawdown improvement (-0.3068 -> -0.2521 full sample) is **substantially a COVID-window
effect**: the junk filter helped in the crash and almost nowhere else. A reader quoting B1's
drawdown as a general property would be quoting one quarter.

**THIS IS A SENSITIVITY AND NOT THE RESULT.** The registered reading is all 44 dates; dropping a
date after seeing a figure would be choosing the design on the outcome. The registered verdicts
stand and this run exists to say whether they rest on one window. They do not.

**ZERO TRIALS** — a sensitivity on an already-scored arm that changes no verdict and adopts
nothing.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

ARMS = "STAGE1_BATCH2_ARMS.json"
OUT = "STAGE1_BATCH2_TERMINAL.json"
PANEL = "UNIVERSE_BIAS_PANEL_full_v3.pkl"
DON_ALLOWANCE_PP = 3.0


def fa_or_none():
    """The free-analysis directory, or None where there is no licensed data root.

    A helper that reports its own inability must do so as a STATE rather than by raising -- the
    rule two CI failures taught, the second of them at CALL level after the first was fixed at
    IMPORT level.
    """
    try:
        from scripts.index_best import _data_root
        return os.path.join(_data_root(), "free_analysis")
    except Exception:
        return None


def main(argv=None):
    import pandas as pd
    from scripts.stage1_kills import build_quadrant, BUILD_HALF_SPLIT
    from scripts.tiered_pool_run import _ann
    import scripts.tiered_pool as TP

    f = fa_or_none()
    if f is None:
        raise SystemExit("REFUSING: no licensed data root on this host.")
    ap = os.path.join(f, ARMS)
    if not os.path.exists(ap):
        raise SystemExit("REFUSING: %s absent — the sensitivity is on an already-scored arm, "
                         "so there is nothing to be sensitive about." % ap)

    panel = pd.read_pickle(os.path.join(f, PANEL))
    quad, _cen = build_quadrant(panel)
    grid = [str(d)[:10] for d in sorted(quad["date"].unique())]
    bench = [float(quad[quad["date"] == d]["bench_ret"].iloc[0])
             for d in sorted(quad["date"].unique())]

    with io.open(ap, encoding="utf-8") as fh:
        arms = json.load(fh)
    ca = arms["construction_arms"]

    def split(series, drop_terminal):
        pr = list(zip(grid[:len(series)], series))
        if drop_terminal:
            pr = pr[:-1]
        e = [v for d, v in pr if d <= BUILD_HALF_SPLIT]
        l = [v for d, v in pr if d > BUILD_HALF_SPLIT]
        return {"early_ann": _ann(e) if e else None, "late_ann": _ann(l) if l else None,
                "early_mdd": TP._mdd(e) if e else None, "late_mdd": TP._mdd(l) if l else None,
                "early_n": len(e), "late_n": len(l)}

    def dons(inc, arm):
        out, ok = {}, True
        for half in ("early", "late"):
            a, b = arm["%s_ann" % half], inc["%s_ann" % half]
            da, db = arm["%s_mdd" % half], inc["%s_mdd" % half]
            if None in (a, b, da, db):
                out[half] = {"state": "NOT ASSESSABLE"}
                ok = False
                continue
            rb = bool(a > b)
            # max_drawdown is NEGATIVE, so the gain is `arm - incumbent` -- S10's sign.
            gain = (float(da) - float(db)) * 100.0
            within = bool(gain >= -DON_ALLOWANCE_PP)
            out[half] = {"arm_ann": a, "incumbent_ann": b, "return_beats": rb,
                         "drawdown_gain_pp": gain, "within_allowance": within,
                         "clears": bool(rb and within)}
            ok = ok and rb and within
        return {"halves": out,
                "verdict": ("STAGE-1 PASS, 1999-2008 LEG NOT RUN" if ok else "REJECTED")}

    bench_pairs = list(zip(grid, bench))
    bl = [v for d, v in bench_pairs if d > BUILD_HALF_SPLIT]
    res = {
        "item": "STAGE1-BATCH2 — the terminal-window sensitivity",
        "register": "PREREG_stage1_batch2.md",
        "trials": 0,
        "trial_class": "a SENSITIVITY on an already-scored arm. It changes no verdict and "
                       "adopts nothing; the REGISTERED reading is all 44 dates, and dropping a "
                       "date after seeing a figure would be choosing the design on the outcome.",
        "the_question": "the incumbent's late half reads 1.88%/yr while SPY returned roughly "
                        "11-12%/yr over calendar 2015-2019. Real, or a defect?",
        "the_answer": "REAL, and the comparison as posed is the WRONG OBJECT.",
        "why": {
            "panel_own_bench_late_half_ann": _ann(bl),
            "panel_own_bench_late_half_ann_dropping_terminal": _ann(bl[:-1]),
            "terminal_window_date": grid[-1],
            "terminal_window_bench_return": bench[-1],
            "book_lags_its_OWN_bench_by_pp": (ca["0_incumbent"]["late_ann_at_register_boundary"]
                                              - _ann(bl)) * 100.0,
            "note": "every figure in this batch is a mean of 63-trading-day FORWARD windows; the "
                    "11-12% is a CALENDAR-period return. The quadrant's BUILD_END is 2019-12-31 "
                    "and a 63-day forward window from there lands in 2020-04, so the terminal "
                    "window IS COVID 2020Q1 -- the quarter S10 measured as the one 63-day period "
                    "that dominates this book's drawdown on every arm.",
        },
        "series_alignment_checked": {
            "dates": len(grid), "net_series_len": len(ca["0_incumbent"]["net_series"]),
            "aligned_one_to_one": len(grid) == len(ca["0_incumbent"]["net_series"]),
            "why_it_was_checked": "a short series zipped against the full grid would misassign "
                                  "every return by one and move the half boundary -- which looks "
                                  "exactly like a real underperformance",
        },
        "arms": {},
    }
    for drop in (False, True):
        tag = "dropping_terminal" if drop else "as_registered"
        inc = split(ca["0_incumbent"]["net_series"], drop)
        blk = {"0_incumbent": inc}
        for k in ("B1_junk_on_the_tier", "B2_vol_managed"):
            a = split(ca[k]["net_series"], drop)
            blk[k] = {"halves": a, "dons_rule": dons(inc, a)}
        res["arms"][tag] = blk

    a0 = res["arms"]["as_registered"]
    a1 = res["arms"]["dropping_terminal"]
    res["verdicts_unchanged"] = all(
        a0[k]["dons_rule"]["verdict"] == a1[k]["dons_rule"]["verdict"]
        for k in ("B1_junk_on_the_tier", "B2_vol_managed"))
    res["THE_ONE_FIGURE_THAT_MOVES"] = {
        "B1_late_drawdown_gain_pp_as_registered":
            a0["B1_junk_on_the_tier"]["dons_rule"]["halves"]["late"]["drawdown_gain_pp"],
        "B1_late_drawdown_gain_pp_dropping_terminal":
            a1["B1_junk_on_the_tier"]["dons_rule"]["halves"]["late"]["drawdown_gain_pp"],
        "consequence": "B1's apparent drawdown improvement is SUBSTANTIALLY a COVID-window "
                       "effect -- the junk filter helped in the crash and almost nowhere else. "
                       "A reader quoting B1's full-sample drawdown as a general property would "
                       "be quoting one quarter.",
    }

    dest = os.path.join(f, OUT)
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)

    print("the question: incumbent late half 1.88%/yr vs SPY ~11-12%/yr 2015-2019", flush=True)
    print("  panel's OWN bench, same windows, same _ann : %.4f" % _ann(bl), flush=True)
    print("  same, dropping the terminal window         : %.4f" % _ann(bl[:-1]), flush=True)
    print("  terminal window (%s)              : %+.4f" % (grid[-1], bench[-1]), flush=True)
    print("  -> REAL, not a defect. The book lags its own bench by %+.2fpp, not ten."
          % res["why"]["book_lags_its_OWN_bench_by_pp"], flush=True)
    print("\n  verdicts unchanged dropping the terminal window: %s"
          % res["verdicts_unchanged"], flush=True)
    for k in ("B1_junk_on_the_tier", "B2_vol_managed"):
        print("    %-20s %s -> %s" % (k, a0[k]["dons_rule"]["verdict"],
                                      a1[k]["dons_rule"]["verdict"]), flush=True)
    print("\nwrote %s" % dest, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
