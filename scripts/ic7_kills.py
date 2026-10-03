# -*- coding: utf-8 -*-
"""IC7 — the FREE pre-outcome kills, run and READ before any register is committed. ZERO TRIALS.

`MB1-SEL`: a control can only BLOCK, never produce. All five of the draft's kills are free
arithmetic on the banked 69-date panel -- no rebuild, no purchase, no new placebo sweep -- so
they are run first, and if one fires the item closes at zero trials and no register exists.

`K4` is the FIDELITY gate and it ABORTS: with imputation disabled the arm must reproduce the
published record at max |delta| 0.000e+00. That is the control `MA28`'s C1 and `W-1`'s K4 both
caught on their own first runs, in both cases from scoring nine themes at a seven-theme weight.
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

PUBLISHED = {
    "top_decile_alpha": 0.07174142332098163,
    "long_short_tstat": 2.8360640685320595,
    "long_short_tstat_nw": 2.6199121240414884,
    "monotonicity": -0.8909090909090909,
}
K1_FLOOR = 0.10          # pre-committed: below a tenth of rows the arm is inert. ~28% expected.
K3_SIZE_BAR = 0.60       # R6's own costume bar, reused VERBATIM
INST_EMPTY_BEFORE = "2013-06-30"


def _data_root():
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
    raise FileNotFoundError("no data root; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
OUT = os.path.join(FA, "IC7_KILLS.json")


def main() -> int:
    import valuation.screener.settings as S
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    weighted = [k for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns]

    out = {"item": "IC7", "pass": "0 free kills", "trials": 0,
           "licence": "MB1-SEL: a control can only BLOCK, never produce.",
           "weighted_themes": weighted,
           "pre_committed": {"K1_floor_share_of_rows": K1_FLOOR,
                             "K3_size_costume_bar": K3_SIZE_BAR,
                             "K3_bar_source": "R6's own 0.60, reused verbatim"}}

    # ---------------- K1. the exposure census
    miss = panel[weighted].isna()
    any_hole = miss.any(axis=1)
    per_theme = {c: float(miss[c].mean()) for c in weighted}
    share = float(any_hole.mean())
    by_date = panel.assign(_h=any_hole).groupby("date")["_h"].mean()
    out["K1_exposure_census"] = {
        "share_of_rows_missing_at_least_one_weighted_theme": share,
        "per_theme_missing_share": per_theme,
        "per_date": {"min": float(by_date.min()), "median": float(by_date.median()),
                     "max": float(by_date.max())},
        "floor": K1_FLOOR,
        "pass": bool(share >= K1_FLOOR),
        "expected_in_advance": ("~28%, from institutional's 71.7% coverage -- stated so a "
                                "surprise is visible rather than rationalised")}

    # ---------------- K2. the era structure, REPORTED not discovered
    d = panel.assign(_h=any_hole)
    early = d[d["date"] < INST_EMPTY_BEFORE]["_h"]
    late = d[d["date"] >= INST_EMPTY_BEFORE]["_h"]
    out["K2_era_structure"] = {
        "boundary": INST_EMPTY_BEFORE,
        "share_before": float(early.mean()) if len(early) else None,
        "share_after": float(late.mean()) if len(late) else None,
        "rows_before": int(len(early)), "rows_after": int(len(late)),
        "institutional_first_date_with_any_value": (
            str(panel.loc[panel["institutional"].notna(), "date"].min())
            if "institutional" in panel.columns else None),
        "why": ("institutional is empty early, so the affected share is NOT stationary and the "
                "both-halves gate may be measuring two different interventions. Reported "
                "BEFORE the arm so the register states it rather than discovering it.")}

    # ---------------- K3. the size costume -- R6's failure mode, three items died on it
    rhos = []
    for dt_, g in panel.assign(_h=any_hole.astype(float)).groupby("date"):
        if g["_h"].nunique() < 2 or g["size"].notna().sum() < 20:
            continue
        r = g[["_h", "size"]].corr(method="spearman").iloc[0, 1]
        if r == r:
            rhos.append(abs(float(r)))
    mean_rho = float(np.mean(rhos)) if rhos else float("nan")
    out["K3_size_costume"] = {
        "mean_per_date_abs_rho_hole_vs_size": mean_rho,
        "n_dates": len(rhos), "bar": K3_SIZE_BAR,
        "pass": bool(mean_rho < K3_SIZE_BAR),
        "why": ("coverage correlates with size -- a 13F filer reports large positions -- so the "
                "imputed set is probably smaller-cap. U7, S10 and R6 were each decided by this "
                "exact failure mode.")}

    # ---------------- K4. FIDELITY, and it aborts
    from valuation.edge.fundamental_panel import quantile_backtest
    cols = [c for c in S.FACTORS_ALL if c in panel.columns]
    rec = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if k in cols}
    qb = quantile_backtest(panel, cols, rec, n_q=10, horizon=63)
    got = {"top_decile_alpha": qb.get("top_decile_alpha"),
           "long_short_tstat": qb.get("long_short_tstat"),
           "long_short_tstat_nw": qb.get("long_short_tstat_nw"),
           "monotonicity": qb.get("monotonicity")}
    devs = {k: (abs(float(got[k]) - v) if got.get(k) is not None else float("inf"))
            for k, v in PUBLISHED.items()}
    worst = max(devs.values())
    out["K4_fidelity"] = {"published": PUBLISHED, "measured": got, "abs_dev": devs,
                          "worst": worst, "fields_compared": len(devs),
                          "pass": bool(worst == 0.0 and len(devs) == 4)}

    # ---------------- K5. no look-ahead, by construction
    out["K5_no_look_ahead"] = {
        "imputation_source": "the date's OWN cross-section median of the z-scored theme",
        "pass": True,
        "why": ("the imputed value is the per-date median of the theme being imputed, so it "
                "cannot reach a later date. Pinned by test with a positive control rather than "
                "asserted here.")}

    fired = [k for k, v in out.items()
             if isinstance(v, dict) and v.get("pass") is False]
    out["any_kill_fired"] = fired

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    k = out
    print("K1 exposure: %.4f of rows missing >= 1 weighted theme (floor %.2f) -> %s"
          % (share, K1_FLOOR, "PASS" if k["K1_exposure_census"]["pass"] else "FIRES"))
    print("   per theme: %s" % {c: round(v, 4) for c, v in per_theme.items()})
    print("   per date: min %.4f median %.4f max %.4f"
          % (by_date.min(), by_date.median(), by_date.max()))
    print("K2 era: before %s %.4f | after %.4f  (institutional first value %s)"
          % (INST_EMPTY_BEFORE, k["K2_era_structure"]["share_before"] or -1,
             k["K2_era_structure"]["share_after"] or -1,
             k["K2_era_structure"]["institutional_first_date_with_any_value"]))
    print("K3 size costume: mean |rho| %.4f over %d dates (bar %.2f) -> %s"
          % (mean_rho, len(rhos), K3_SIZE_BAR,
             "PASS" if k["K3_size_costume"]["pass"] else "FIRES"))
    print("K4 fidelity: worst |dev| %.3e over %d fields -> %s"
          % (worst, len(devs), "PASS" if k["K4_fidelity"]["pass"] else "ABORT"))
    print("\nkills fired: %r" % (fired or "none"))
    print("wrote", OUT)
    return 0 if not fired else 3


if __name__ == "__main__":
    raise SystemExit(main())
