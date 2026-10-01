# -*- coding: utf-8 -*-
"""REBAL-CADENCE pass 0 — the PRE-OUTCOME control. ZERO TRIALS.

WHY THIS RUNS BEFORE THE REGISTER, and the licence is on the record. `RUN_RULES` A11 requires a
register to state its minimum detectable effect BEFORE it runs, and `MB8` forbids borrowing an
`se` across perturbation sizes -- so the MDE for a paired within-panel cadence difference has to
be MEASURED on this arm and cannot be lifted from `V2G`'s 0.9354pp, `MB8`'s 0.1106pp or `W-1`'s
0.001600. `R1-VAR` settles the ordering explicitly: such an arm *"needs its OWN measured paired
SE - a CONTROL, which under `MB1-SEL` can only BLOCK and therefore costs ZERO TRIALS and may be
taken BEFORE any register is written."*

WHAT THIS PASS MAY AND MAY NOT EMIT. It emits dispersion and nothing else: `n`, the paired HAC
standard error, and the detection thresholds that follow from it. It emits NO mean, NO alpha
level, NO *t* and NO verdict, for any arm -- so running it cannot reveal which way any arm came
out, and the register that follows is still blind to the outcome. That is enforced by an AST
test over this file plus a key-level check on the artifact, not promised in a docstring.

AND THE MARGIN IS STILL NOT CHOSEN FROM THIS. The register takes `SECTOR-NEUTRAL-B6`'s gate
VERBATIM (+100bps net alpha AND +0.25 HAC *t*, both halves), as `W-1` and `PKG-MB20` did, so
the bar has precedent and is not tuned to the `se` measured here. What the `se` buys is the
honest label: a margin far above the 80%-power MDE means a null is BOUNDED rather than a
demonstration of absence.

C1 GATES THE WHOLE THING. The incumbent arm must reproduce the published contract book
(`BACKTEST_RESULTS.json` `book_configs.taxable`) or this exits non-zero and pass 1 refuses to
run -- the arms are then provably the object the record describes rather than a lookalike.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge.power_gate import critical_value                      # noqa: E402
from valuation.studies import rebal_cadence as rc                         # noqa: E402

# ---- the published contract book, as LITERALS so a drift is loud (`MA13`'s idiom)
PUBLISHED = {
    "net_alpha": 0.07752019016178369,
    "net_sharpe": 1.2095691568179565,
    "net_max_drawdown": -0.2754830109769675,
    "annual_turnover": 1.374714037832626,
}
C1_TOL = 1e-12

EQUITY_N_AT_REGISTRATION = 248          # re-read from research_log, stated in the register


def _data_root():
    """Derived, never typed. A git worktree carries `data/` EMPTY, so the primary checkout is
    the last candidate -- the literal that cost land run #571 a red gate."""
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(_HERE, "data"))
    parts = _HERE.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    for c in out:
        if os.path.exists(os.path.join(c, "free_analysis", "panel_corrected_69d.pkl")):
            return c
    raise FileNotFoundError("no data root carrying panel_corrected_69d.pkl; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
OUT = os.path.join(FA, "REBAL_CADENCE_CONTROL.json")
SERIES = os.path.join(FA, "REBAL_CADENCE_SERIES.pkl")


def _hac_se(x, lag=1) -> float:
    """Newey-West standard error of a mean, at the lag the overlap implies.

    The periods are consecutive 63-day windows that DO NOT overlap, so lag 1 is the project's
    own convention for this panel (`R9` measured lag-1 autocorrelation +0.189 on the long-short
    spread and made the HAC figure the one quoted). The lag is a PARAMETER and is reported, so
    nobody has to guess which one produced a number.
    """
    x = np.asarray([v for v in x if v == v], dtype=float)
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    g0 = float(np.dot(e, e) / n)
    s = g0
    for L in range(1, int(lag) + 1):
        if L >= n:
            break
        g = float(np.dot(e[L:], e[:-L]) / n)
        s += 2.0 * (1.0 - L / (lag + 1.0)) * g
    s = max(s, 1e-30)
    return float(np.sqrt(s / n))


def main() -> int:
    panel = pd.read_pickle(PANEL)
    import valuation.screener.settings as S
    cols = [c for c in S.FACTORS_ALL if c in panel.columns]
    rec = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if k in cols}

    out = {"item": "REBAL-CADENCE", "pass": "0 control", "trials": 0,
           "licence": ("MB1-SEL: a control can only BLOCK, never produce. R1-VAR licenses "
                       "measuring a paired se BEFORE the register, because MB8 forbids "
                       "borrowing one across perturbation sizes."),
           "emits": ("dispersion ONLY -- n, paired HAC se, detection thresholds. No mean, no "
                     "alpha level, no t, no verdict, for any arm."),
           "equity_n": EQUITY_N_AT_REGISTRATION,
           "hac_lag": 1,
           "per_year": rc.PER_YEAR}

    # ---------------- C1. the incumbent IS the published contract book, or nothing runs
    from valuation.edge.fundamental_panel import turnover_and_costs
    base = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3)
    c1 = {}
    worst = 0.0
    for k, v in PUBLISHED.items():
        got = base.get(k)
        dev = abs(float(got) - v) if got is not None else float("inf")
        c1[k] = {"published": v, "measured": got, "abs_dev": dev}
        worst = max(worst, dev)
    c1_pass = worst <= C1_TOL
    # GATED on the count as well as the deviation: `MB21`'s C1 scored a perfect 0.000e+00 on an
    # empty frame by comparing nothing.
    c1_pass = c1_pass and len(c1) == len(PUBLISHED) == 4
    out["C1_incumbent_reproduces_published_contract_book"] = {
        "pass": bool(c1_pass), "tol": C1_TOL, "worst_abs_dev": worst,
        "fields_compared": len(c1), "detail": c1}
    if not c1_pass:
        out["status"] = "C1 FAILED -- no arm may be scored against this incumbent"
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
        print(json.dumps(out["C1_incumbent_reproduces_published_contract_book"], indent=1))
        return 2

    # ---------------- the four arms, and the inertness of the extension at cadence=1
    arms = rc.build_all(panel, cols, rec)
    inert = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3,
                               cadence=1, offset=0)
    out["C2_cadence_1_is_bit_identical_to_the_shipped_default"] = {
        "pass": all(abs(float(inert[k]) - float(base[k])) <= 0.0
                    for k in ("net_alpha", "annual_turnover", "gross_ann", "net_ann")),
        "fields": {k: {"default": base.get(k), "cadence_1": inert.get(k)}
                   for k in ("net_alpha", "annual_turnover", "gross_ann", "net_ann")},
        "why": ("an opt-in parameter must leave the shipped path untouched (`C3`), and the "
                "weight-weighted book return reduces to np.mean EXACTLY when weights are equal")}

    common = rc.common_dates(arms)
    out["populations"] = {
        "panel_dates": int(panel["date"].nunique()),
        "arm_periods": {k: a["n_periods"] for k, a in arms.items()},
        "common_periods_all_arms": len(common),
        "first_common": common[0] if common else None,
        "last_common": common[-1] if common else None,
        "why_common": ("every arm is scored on ONE date set, so no paired difference is "
                       "partly a difference of windows. The staggered arm binds it: four "
                       "sub-books at offsets 0..3 are all live only from the 4th date."),
        "legs": {k: a["legs"] for k, a in arms.items()}}

    # ---------------- the dispersion, and ONLY the dispersion
    rest = rc.restrict(arms, common)
    crit_conv = 2.0
    crit_hlz = critical_value(n_trials=EQUITY_N_AT_REGISTRATION)
    disp = {}
    for name in rc.ARMS:
        if name == rc.INCUMBENT:
            continue
        pd_ = rc.paired_difference(rest, name)
        se = _hac_se(pd_["diff"], lag=1)
        row = {"n_paired_periods": pd_["n"], "paired_hac_se_per_period": se,
               "paired_hac_se_annualised_pp": se * rc.PER_YEAR * 100.0}
        for label, crit in (("conventional_crit_2.0", crit_conv),
                            ("hlz_hurdle_at_N_%d" % EQUITY_N_AT_REGISTRATION, crit_hlz)):
            row[label] = {
                "crit": crit,
                "mde_50pct_power_ann_pp": crit * se * rc.PER_YEAR * 100.0,
                "mde_80pct_power_ann_pp": (crit + 0.84) * se * rc.PER_YEAR * 100.0}
        disp[name] = row
    out["paired_dispersion"] = disp
    out["uncalibrated"] = ("EVERY critical value here is LABELLED UNCALIBRATED. V2G "
                           "established and R1-VAR re-confirmed that no calibrated floor "
                           "exists for a paired within-panel difference; X7 calibrates LEVELS.")

    # per-draw rows (`RUN_RULES` A9) -- the NET series per arm, which is what the se came from.
    pd.to_pickle({"arms": rest, "common_dates": common,
                  "note": "pass-0 control draws; no outcome statistic is stored here"}, SERIES)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    print("C1 reproduces the published contract book: %s (worst dev %.3e)"
          % (c1_pass, worst))
    print("C2 cadence=1 bit-identical: %s"
          % out["C2_cadence_1_is_bit_identical_to_the_shipped_default"]["pass"])
    print("common periods across all four arms: %d (%s .. %s)"
          % (len(common), common[0] if common else "-", common[-1] if common else "-"))
    for name, row in disp.items():
        print("  %-11s n %2d  paired HAC se %.6f/period (%.4fpp ann)"
              % (name, row["n_paired_periods"], row["paired_hac_se_per_period"],
                 row["paired_hac_se_annualised_pp"]))
        for label in row:
            if isinstance(row[label], dict) and "mde_80pct_power_ann_pp" in row[label]:
                print("      %-24s crit %.4f  MDE50 %.4fpp  MDE80 %.4fpp"
                      % (label, row[label]["crit"],
                         row[label]["mde_50pct_power_ann_pp"],
                         row[label]["mde_80pct_power_ann_pp"]))
    print("\nwrote", OUT, "and", SERIES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
