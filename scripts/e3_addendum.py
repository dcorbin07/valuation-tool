"""E-3 addendum -- POST-HOC DIAGNOSTICS, NO VERDICT. `PREREG_e3_theme_dispersion.md` §5/§7.

**Nothing here can change the verdict.** No leg is recomputed and no bar is applied. Two
reasons this file exists, both of them obligations the register itself created:

1. **§7's expectation (4) names a quantity the registered design does not produce.** The draft
   predicted *"dispersion's largest input correlation is with `institutional` coverage effects
   on basis seven"*, but the three kills correlate `disp` against `size`, `|composite|` and the
   theme COUNT -- there is no per-theme table anywhere in the arm. Scoring that expectation
   therefore requires computing it, and refusing to compute it would mean quietly dropping an
   expectation the register promised to score. It is produced here, LABELLED post-hoc, with no
   bar attached. **That an expectation was written against a quantity the design never emits is
   itself a small finding about the draft, and it is recorded rather than smoothed over.**

2. **§5 requires the MDE beside the verdict in both `MB22` vocabularies.** The arm prints the
   two thresholds; what it does not print is the OBSERVED effect in the same units, which is
   the comparison `V6`/`S19`/`MB16` actually demand. `ic_tstat` is `mean / (sd / sqrt(n))`, so
   the effect in SD units of the per-date IC series is `t / sqrt(n)` -- derived from the
   shipped definition rather than assumed.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import pickle
import sys
from typing import Dict

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from valuation.studies import incremental_ic as II          # noqa: E402
import e3_theme_dispersion as E3                            # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--arms-json", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with io.open(a.arms_json, encoding="utf-8") as fh:
        arm = json.load(fh)
    with open(a.panel, "rb") as fh:
        panel = pickle.load(fh)

    out: Dict[str, object] = {
        "item": "E-3", "kind": "POST-HOC DIAGNOSTIC, NO VERDICT",
        "register": "PREREG_e3_theme_dispersion.md",
        "verdict_is_unchanged": arm["verdict"],
        "bases": {},
    }

    for basis in E3.BASES:
        cols = list(II.basis_for(basis))
        built, _ = E3.build(panel, basis, E3.MIN_THEMES)
        d = f"disp_{basis}"
        ed = II.effective_dates(built, d, cols, min_names=E3.MIN_NAMES)
        eff = built[built["date"].isin(ed)].dropna(subset=[d, "fwd_ret"] + cols)

        # ---- (1) the per-theme table §7(4) asks for. Descriptive, no bar. ----
        per_theme = {}
        for c in cols:
            per_theme[c] = E3.mean_per_date_rho(eff, d, c).get("mean_rho")
        ranked = sorted(((k, v) for k, v in per_theme.items() if v is not None),
                        key=lambda kv: -abs(kv[1]))

        # ---- (2) the observed effect in the MDE's own units ----
        B = arm["bases"][basis]
        p = B["power"]
        n = int(B["n_effective_dates"])
        t_full = float(B["full"]["incremental_ic_tstat"])
        eff_sd = abs(t_full) / math.sqrt(n)          # ic_tstat = mean / (sd / sqrt(n))
        raw_t = float(B["full"]["raw_ic_tstat"])
        raw_sd = abs(raw_t) / math.sqrt(int(B["full"]["n_dates_raw"]))

        out["bases"][basis] = {
            "per_theme_mean_rho": per_theme,
            "largest_absolute": {"theme": ranked[0][0], "rho": ranked[0][1]} if ranked else None,
            "ranked_by_absolute": [{"theme": k, "rho": v} for k, v in ranked],
            "mde": {
                "observed_incremental_effect_SD": eff_sd,
                "detection_threshold_50pct_power_SD": p["detection_threshold_50pct_power_SD"],
                "mde_at_80pct_power_SD": p["mde_at_80pct_power_SD"],
                "factor_below_80pct_mde": p["mde_at_80pct_power_SD"] / eff_sd if eff_sd else None,
                "observed_RAW_effect_SD": raw_sd,
                "units": ("SD of the per-date IC series. ic_tstat is mean / (sd / sqrt(n)), the "
                          "SHIPPED theme_ic arithmetic, so effect = |t| / sqrt(n)."),
                "anchor": ("MB18 measured the strongest RAW anchor on rows of this shape at "
                           "z_fcf_margin 0.4346 SD. A NULL at these thresholds means 'no effect "
                           "at least as large as the best thing this panel has ever carried', "
                           "never 'no effect'."),
            },
            "raw_versus_incremental": {
                "raw_median_ic": B["full"]["raw_median_ic"],
                "raw_ic_tstat": raw_t,
                "incremental_median_ic": B["full"]["incremental_median_ic"],
                "incremental_ic_tstat": t_full,
                "mean_r2_on_incumbents": B["mean_r2_on_incumbents"],
                "reading": ("the RAW column sorts in the declared NEGATIVE direction and the "
                            "INCREMENTAL one does not; residualisation removes almost all of "
                            "it. That is the PEAD template detecting a repackaging, which is "
                            "what it is for."),
            },
        }

    six = out["bases"]["six"]["raw_versus_incremental"]
    seven = out["bases"]["seven"]["raw_versus_incremental"]
    out["headline_reading"] = {
        "raw_clears_the_retired_2.0_convention_on_both_bases": bool(
            abs(six["raw_ic_tstat"]) > 2.0 and abs(seven["raw_ic_tstat"]) > 2.0),
        "raw_clears_the_CALIBRATED_2.71_bar": bool(
            abs(six["raw_ic_tstat"]) > E3.BAR and abs(seven["raw_ic_tstat"]) > E3.BAR),
        "why_that_matters": (
            "X7 measured that 39% of PURE-NOISE draws produce at least one theme at |t| >= 2.0, "
            "which is why this project retired 2.0 and calibrated 2.71. A raw |t| of 2.17-2.30 "
            "points the declared way and clears NEITHER bar that governs here."),
        "r2_context": (
            "U2 measured the incumbents explaining 41.3% of gp_on_capital and 78.4% of ret_6_1, "
            "against 5.5-8.8% for genuinely new options-derived columns, and four "
            "orthogonality-motivated items landed at R2 0.027-0.145. disp sits at 0.347/0.413 "
            "-- squarely in the REPACKAGED-INCUMBENT range, which is what a function OF the "
            "incumbents should look like."),
    }

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)

    for b, r in out["bases"].items():
        lg = r["largest_absolute"]
        print(f"[{b}] largest |rho| vs a theme: {lg['theme']} {lg['rho']:+.4f}   "
              f"observed {r['mde']['observed_incremental_effect_SD']:.4f} SD vs 80% MDE "
              f"{r['mde']['mde_at_80pct_power_SD']:.4f} "
              f"({r['mde']['factor_below_80pct_mde']:.2f}x below)")
        print(f"      ranked: " + ", ".join(f"{x['theme']} {x['rho']:+.3f}"
                                            for x in r["ranked_by_absolute"]))
    print(f"[addendum] -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
