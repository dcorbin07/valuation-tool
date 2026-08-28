# -*- coding: utf-8 -*-
"""W-1 — the MDE, from THIS arm's OWN measured paired HAC standard error.

`§6` of the register: *a verdict quoted without its MDE is a void condition.* And `MB8`'s rule
binds — **an `se` may NOT be borrowed across perturbation sizes**; its own 0.1106pp and `V2G`'s
0.9354pp differ 8.5-fold for exactly that reason. So this measures its own and quotes no other.

**THE CRITICAL VALUE IS LABELLED UNCALIBRATED WHEREVER IT APPEARS.** `V2G` established and
`R1-VAR` re-confirmed that **no calibrated floor exists for a paired within-panel difference** —
`X7` calibrates LEVELS. Both vocabularies are reported at both critical values: the conventional
2.0 that `V2G` and `MB8` used, and the honest hurdle at the post-booking `N` = 247.

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
from scripts.w1_sector_neutral_pit import (build, split_arms,        # noqa: E402
                                           DEPLOYED, FLAT, BASE_WEIGHT, FA)

OUT = os.path.join(FA, "W1_MDE.json")


def _paired(a_series, b_series):
    """Per-date paired difference and its HAC standard error."""
    d = np.asarray(b_series, dtype=float) - np.asarray(a_series, dtype=float)
    d = d[np.isfinite(d)]
    n = d.size
    mean = float(d.mean())
    t = _nw_tstat(d.tolist(), lag=1)
    se = abs(mean / t) if (t and np.isfinite(t) and t != 0) else float("nan")
    return {"n": int(n), "mean": mean, "hac_t": float(t) if t is not None else None,
            "hac_se": se}


def main() -> int:
    panel = build()
    flat, sn = split_arms(panel)
    neq = RL.detail()["by_domain"]["equity"]
    hurdle = critical_value(n_trials=neq)
    out = {"item": "W-1", "equity_N": neq, "hurdle": hurdle,
           "uncalibrated_note": ("NO calibrated floor exists for a paired within-panel difference "
                                 "(V2G, re-confirmed by R1-VAR); X7 calibrates LEVELS. Every "
                                 "critical value below is UNCALIBRATED and labelled so."),
           "weightings": {}}

    for label, cset in (("deployed", DEPLOYED), ("flat", FLAT)):
        cols = [c for c in cset if c in flat.columns]
        w = {c: BASE_WEIGHT for c in cols}
        ra = quantile_backtest(flat, cols, w, n_q=10, horizon=63, return_series=True)
        rb = quantile_backtest(sn, cols, w, n_q=10, horizon=63, return_series=True)
        blk = {}
        # The shipped series keys are `alpha` and `long_short`, READ FROM THE PRODUCER rather
        # than guessed. My first cut asked for `top_decile_alpha` and got nothing back -- the
        # wrong-object family, and the same defect D6's C1 hit on `long_short_tstat_hac`. A key
        # that does not exist returns None silently, so it is taken from the source.
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
                         "mde80": (crit + Z_POWER_CONVENTION) * p["hac_se"]}
            blk[key] = p
        out["weightings"][label] = blk
        print("\n=== %s ===" % label.upper())
        for key, p in blk.items():
            if "hac_se" not in p:
                print("  %-12s %s" % (key, p.get("note")))
                continue
            print("  %-12s n=%d  mean %+.6f  HAC t %+.4f  paired HAC se %.6f"
                  % (key, p["n"], p["mean"], p["hac_t"] or float("nan"), p["hac_se"]))
            for cl in [k for k in p if k.startswith("crit_")]:
                print("       %-34s MDE50 %.6f   MDE80 %.6f"
                      % (cl, p[cl]["mde50"], p[cl]["mde80"]))
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
