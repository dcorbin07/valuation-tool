# -*- coding: utf-8 -*-
"""PKG-MB20 — full-sample levels and the MDE, from THIS arm's OWN paired HAC standard error.

§8 of the register: a verdict quoted without its MDE at both `MB22` vocabularies is a void
condition. And `MB8`'s rule binds -- **an `se` may NOT be borrowed across perturbation sizes**;
its own 0.1106pp and `V2G`'s 0.9354pp differ 8.5-fold for exactly that reason, and `W-1`'s
0.001600 is a different perturbation again. So this measures its own and quotes no other.

EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED. `V2G` established and `R1-VAR` re-confirmed that
no calibrated floor exists for a paired within-panel difference -- `X7` calibrates LEVELS.

ZERO ADDITIONAL TRIALS: this is the power statement the already-booked register owes.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import research_log as RL                        # noqa: E402
from valuation.edge.fundamental_panel import (quantile_backtest,     # noqa: E402
                                              _nw_tstat)
from valuation.edge.power_gate import (critical_value,               # noqa: E402
                                       Z_POWER_CONVENTION)
from scripts.mb20_arm import (build, split_arms, DEPLOYED, FLAT,     # noqa: E402
                              BASE_WEIGHT, FA)

OUT = os.path.join(FA, "MB20_MDE.json")

#: X7's LEVEL floors at the post-booking N, re-derived by W-1 at N=247 and unmoved at 248
#: (MB31: the next adopt-set change is seed 1017 at N=688).
LEVEL_FLOORS = {"long_short_naive": 2.070231,
                "long_short_hac": 2.056680,
                "top_decile_alpha_hac": 1.826210}


def _paired(a_series, b_series):
    d = np.asarray(b_series, dtype=float) - np.asarray(a_series, dtype=float)
    d = d[np.isfinite(d)]
    mean = float(d.mean())
    t = _nw_tstat(d.tolist(), lag=1)
    se = abs(mean / t) if (t and np.isfinite(t) and t != 0) else float("nan")
    return {"n": int(d.size), "mean": mean,
            "hac_t": float(t) if t is not None else None, "hac_se": se}


def main() -> int:
    panel, _ = build()
    base, opp = split_arms(panel)
    neq = RL.detail()["by_domain"]["equity"]
    hurdle = critical_value(n_trials=neq)
    out = {"item": "PKG-MB20", "equity_N": neq, "hurdle": hurdle,
           "level_floors_UNCALIBRATED_for_a_difference": LEVEL_FLOORS,
           "uncalibrated_note": ("NO calibrated floor exists for a paired within-panel "
                                 "difference (V2G, re-confirmed by R1-VAR); X7 calibrates "
                                 "LEVELS. Every critical value below is UNCALIBRATED."),
           "weightings": {}}

    for label, cset in (("deployed", DEPLOYED), ("flat", FLAT)):
        cols = [c for c in cset if c in base.columns]
        w = {c: BASE_WEIGHT for c in cols}
        ra = quantile_backtest(base, cols, w, n_q=10, horizon=63, return_series=True)
        rb = quantile_backtest(opp, cols, w, n_q=10, horizon=63, return_series=True)
        blk = {"levels": {
            "A_BASE": {k: ra.get(k) for k in ("top_decile_alpha", "long_short_tstat",
                                              "long_short_tstat_nw", "monotonicity")},
            "A_OPP": {k: rb.get(k) for k in ("top_decile_alpha", "long_short_tstat",
                                             "long_short_tstat_nw", "monotonicity")}}}
        # The shipped series keys, READ FROM THE PRODUCER rather than guessed -- W-1's own
        # first cut asked for `top_decile_alpha` and got nothing back, the wrong-object family.
        for key in ("alpha", "long_short"):
            sa = (ra.get("series") or {}).get(key)
            sb = (rb.get("series") or {}).get(key)
            if sa is None or sb is None:
                blk[key] = {"note": "series key %r not returned" % key}
                continue
            p = _paired(sa, sb)
            for cl, crit in (("crit_2.0_UNCALIBRATED", 2.0),
                             ("crit_hurdle_%.4f_UNCALIBRATED" % hurdle, hurdle)):
                p[cl] = {"mde50": crit * p["hac_se"],
                         "mde80": (crit + Z_POWER_CONVENTION) * p["hac_se"],
                         "observed_over_mde80": (abs(p["mean"]) /
                                                 ((crit + Z_POWER_CONVENTION) * p["hac_se"])
                                                 if p["hac_se"] else None)}
            blk[key] = p
        out["weightings"][label] = blk

        print("\n=== %s ===" % label.upper())
        for arm_lbl, lv in blk["levels"].items():
            print("  %-7s alpha %+.6f  ls_t %+.4f  ls_nw %+.4f  mono %+.4f"
                  % (arm_lbl, lv["top_decile_alpha"], lv["long_short_tstat"],
                     lv["long_short_tstat_nw"], lv["monotonicity"]))
        for key in ("alpha", "long_short"):
            p = blk.get(key, {})
            if "hac_se" not in p:
                continue
            print("  %-11s n=%d mean %+.6f  HAC t %+.4f  paired HAC se %.6f"
                  % (key, p["n"], p["mean"], p["hac_t"] or float("nan"), p["hac_se"]))
            for cl in [k for k in p if k.startswith("crit_")]:
                print("      %-34s MDE80 %.6f   observed/MDE80 %.3fx"
                      % (cl, p[cl]["mde80"], p[cl]["observed_over_mde80"]))

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
