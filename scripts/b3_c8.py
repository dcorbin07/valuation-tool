# -*- coding: utf-8 -*-
"""`STAGE1-BATCH3` — `C8` expected investment growth, in its OWN pass, with its strictness kill.

    python -m scripts.b3_c8 --panel <v3.pkl> --out <B3_C8.json>

**C8 IS THE ONLY ARM IN THE BATCH THAT FITS ANYTHING, WHICH IS ITS RISK AND WHY IT RUNS ALONE.**
The record has already paid for fitting on the panel and scoring on the panel: **+8.43%/yr
in-search → −0.04%/yr on the locked hold-out**, and the ML tree combiner whose deciles ran
**backwards** out of sample. So the expanding-window fit is not a nicety; it is the only reason
this arm is admissible at all.

**THE STRICTNESS IS A PRE-COMMITTED KILL AND IT HAS TWO HALVES** (register §0.3). The draft said
*"drop it rather than fit it loosely"* — but a judgement made after seeing whether the loose
version looks good is not a judgement, so it is mechanical:

1. **The predictors** of every training pair must be dated strictly before the scored date.
2. **The LABEL** must be too. `EG` predicts NEXT-year investment growth, so a pair is
   (predictors at `td`, realised growth at about `td + 1y`), and requiring only `td < d` lets a
   pair whose OUTCOME is dated at or after `d` into the fit — predictors in-sample, label from the
   future. **That is the half that leaks, and it is invisible to a check that looks only at where
   the predictors came from.**

So the audit trail records, per scored date, the latest **LABEL** date used — not the latest
predictor date — and `fit_is_strict` reads it. **If the check does not pass, `C8` is `NOT RUN` and
`k` stays 9.** `fit_is_strict` RETURNS the violations rather than raising, because a helper that
reports its own failure by raising makes every caller a crash where the data is thin.

**EVERY STATISTIC IS CALLED, NOT RE-IMPLEMENTED** (`B7`) — `build_quadrant`, `deployed_control`,
`score_ic_arm`, `tier_frame`. **The tier governs** (charter §5 Stage 1b). **The critical value is
the conventional 2.0, LABELLED UNCALIBRATED** — an incremental IC *t* has no calibrated floor
(`MB22`/`U2`), so `CORRECTED_FLOORS`' theme-IC bar may not be quoted beside it.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.stage1_kills import build_quadrant, BUILD_HALF_SPLIT          # noqa: E402
from scripts.stage1_batch2_kills import tier_frame                        # noqa: E402
from scripts.stage1_batch2_arms import deployed_control, score_ic_arm, CRIT  # noqa: E402
from scripts.b3_kills import attach, costume_block, tier_coverage, COVERAGE_FLOOR  # noqa: E402

COSTUME_BAR = 0.60
MIN_TRAIN_ROWS = 200       # below this a date is recorded unfitted rather than fitted loosely


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    from scripts.tiered_pool_run import _hist
    from scripts.b3_signals2 import (c8_predictors, c8_expected_investment_growth,
                                     fit_is_strict)

    panel = pd.read_pickle(args.panel)
    quad, qcen = build_quadrant(panel)
    quad, cols, w = deployed_control(quad.copy())
    print("[c8] build quadrant %d rows / %d dates" % (qcen["rows"], qcen["dates"]), flush=True)

    export = os.path.join(r"C:/Users/donni/Downloads/valuation-tool/data", "full2009", "backtest")
    hist = _hist(export)

    print("[c8] building the three predictors and the realised outcome ...", flush=True)
    pred = c8_predictors(quad, hist)
    audit = []
    print("[c8] fitting, expanding window, labels strictly before each scored date ...",
          flush=True)
    sig = c8_expected_investment_growth(pred, audit_sink=audit)

    violations = fit_is_strict(audit)
    fitted = [a for a in audit if a.get("fitted")]
    res = {
        "item": "STAGE1-BATCH3", "part": "C8 expected investment growth, its own pass",
        "trials": 0,
        "trial_class": "the trial was booked with the batch at 89593a6; this pass computes one "
                       "of the eight arms and charges nothing further.",
        "build_quadrant": qcen, "half_boundary": BUILD_HALF_SPLIT,
        "crit": CRIT,
        "crit_is": "UNCALIBRATED -- conventional. An incremental IC t has NO calibrated floor "
                   "(MB22/U2), so CORRECTED_FLOORS' theme-IC bar may not be quoted beside it.",
        "strictness": {
            "pre_committed": "register 0.3 -- BOTH the predictors and the LABEL of every "
                             "training pair must be dated strictly before the scored date",
            "dates_fitted": len(fitted),
            "dates_unfitted_too_little_history": len(audit) - len(fitted),
            "min_train_rows": MIN_TRAIN_ROWS,
            "violations": violations,
            "n_violations": len(violations),
            "audit": audit,
            # MB21 -- a clean strictness check over zero fitted dates proves nothing.
            "count_gate_passes": bool(fitted),
        },
    }
    res["strictness"]["passes"] = bool(fitted and not violations)

    if not res["strictness"]["passes"]:
        res["state"] = "NOT RUN"
        res["why"] = ("the strict-fit kill did not pass, and register 0.3 pre-committed that "
                      "C8 is NOT RUN rather than fitted loosely. k stays 9.")
        res["arms"] = {}
        io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, indent=1, default=str))
        print("\n[c8] STRICT-FIT KILL DID NOT PASS -> NOT RUN (%d violations, %d fitted dates)"
              % (len(violations), len(fitted)), flush=True)
        print("-> %s" % args.out)
        return 0

    col = "b3_c8"
    attach(quad, sig, col)
    cov = tier_coverage(quad, col)
    cst = costume_block(quad, col, "C8")
    res["coverage"] = cov
    res["costume"] = cst

    fails = []
    if not cov.get("count_gate_passes") or cov.get("cell_coverage") is None:
        fails.append("coverage not measurable")
    elif cov["cell_coverage"] < COVERAGE_FLOOR:
        fails.append("tier coverage %.4f < %.2f" % (cov["cell_coverage"], COVERAGE_FLOOR))
    for n in cst["named"]:
        if n.get("absent"):
            fails.append("the named comparison column %s is ABSENT" % n["column"])
        elif n.get("mean_abs_rho") is not None and n["mean_abs_rho"] >= COSTUME_BAR:
            fails.append("vs %s at %.4f >= %.2f" % (n["column"], n["mean_abs_rho"], COSTUME_BAR))
    wt = cst.get("worst_theme") or {}
    if wt.get("mean_abs_rho") is not None and wt["mean_abs_rho"] >= COSTUME_BAR:
        fails.append("costume vs %s at %.4f" % (wt["column"], wt["mean_abs_rho"]))
    res["kill_fails"] = fails
    res["kill_passes"] = not fails

    if fails:
        res["state"] = "NOT RUN"
        res["why"] = "its free pre-outcome kill fired; the bar does not move (W-28)."
        res["arms"] = {}
        print("\n[c8] KILL FIRES -> NOT RUN: %s" % fails, flush=True)
    else:
        tier = tier_frame(quad)
        tier = tier[0] if isinstance(tier, tuple) else tier
        wide = score_ic_arm(quad, col, "C8", "wide")
        tr = score_ic_arm(tier, col, "C8", "tier")
        gov = tr.get("verdict")
        if wide.get("verdict") == "SURVIVES" and gov != "SURVIVES":
            gov = "REAL BUT NOT INVESTABLE HERE"
        res["arms"] = {"C8": {"wide": wide, "tier": tr, "governing_verdict": gov}}
        res["state"] = "SCORED"
        print("\n[c8] wide %s | tier %s | GOVERNING %s"
              % (wide.get("verdict"), tr.get("verdict"), gov), flush=True)

    io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, indent=1, default=str))
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
