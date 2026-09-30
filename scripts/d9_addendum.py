# -*- coding: utf-8 -*-
"""D9 addendum — the insider degeneracy, and the repaired 4-theme reading. ZERO TRIALS.

WHY THIS EXISTS. The register's §1c built the primary over "exactly the themes both sides
expose". `insider` IS exposed on both sides and is **degenerate on one**: on 2026-08-08 the live
path's `insider` is CONSTANT at exactly 0.0 across all 431 overlapping names, which is `V2G`'s
documented signature for a missing insider score -- `factors.py:344` makes the theme
`(insider_score - 50) / 25`, so an absent score is exactly 0.0.

**EXPOSURE IS NOT INFORMATION.** That is this record's own "coverage is not fidelity" one level
down, and it means the as-registered primary compared a FIVE-theme Sharadar composite against a
FOUR-informative-theme live one.

THE REPAIR IS REPORTED BESIDE THE AS-REGISTERED NUMBER, NEVER INSTEAD OF IT, and it changes no
bar. It happens to be immaterial: both readings fail both bars, so the verdict does not hinge on
a correction made after the outcome was seen. Had the repaired reading PASSED, `RUN_RULES` A6
would still have made it a NO-GO, because a bar cleared only after a post-hoc construction
change is not cleared.
"""
from __future__ import annotations

import json
import os

import pandas as pd

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
OUT = os.path.join(FA, "D9_FIDELITY.json")

AS_REGISTERED = ("value", "quality", "momentum", "insider", "size")
REPAIRED = ("value", "quality", "momentum", "size")
B1, B2 = 0.80, 0.60


def main() -> int:
    rep = json.load(open(OUT, encoding="utf-8"))
    add = {}
    for lab in ("freeze_2026-07-31", "backtest_2026-07-24"):
        p = os.path.join(FA, "D9_FIDELITY_ROWS_%s.pkl" % lab)
        if not os.path.exists(p):
            continue
        d = pd.read_pickle(p)
        s, l, both = d["sharadar"], d["live"], d["overlap"]
        live_ins = pd.to_numeric(l.loc[both, "insider"], errors="coerce").dropna()
        blk = {"live_insider_distinct_values": int(live_ins.nunique()),
               "live_insider_value": (float(live_ins.iloc[0]) if len(live_ins) else None),
               "sharadar_insider_distinct_values":
                   int(pd.to_numeric(s.loc[both, "insider"], errors="coerce").nunique()),
               "insider_spearman": None,
               "insider_note": ("UNDEFINED: the live theme is constant, so no rank correlation "
                                "exists. NOT zero -- a constant carries no ranking at all.")}
        for name, themes in (("as_registered_5_theme", AS_REGISTERED),
                             ("repaired_4_theme_insider_dropped", REPAIRED)):
            a = s.loc[both, [t for t in themes if t in s.columns]].astype(float).mean(
                axis=1, skipna=True)
            b = l.loc[both, [t for t in themes if t in l.columns]].astype(float).mean(
                axis=1, skipna=True)
            m = a.notna() & b.notna()
            rho = float(a[m].corr(b[m], method="spearman"))
            n = max(1, int(round(int(m.sum()) * 0.10)))
            ta, tb = set(a[m].nlargest(n).index), set(b[m].nlargest(n).index)
            ov = len(ta & tb) / max(1, len(ta))
            blk[name] = {"n": int(m.sum()), "composite_spearman": rho,
                         "decile_overlap": ov,
                         "B1_pass": bool(rho >= B1), "B2_pass": bool(ov >= B2)}
        blk["verdict_unchanged_by_the_repair"] = bool(
            not blk["as_registered_5_theme"]["B1_pass"]
            and not blk["repaired_4_theme_insider_dropped"]["B1_pass"]
            and not blk["as_registered_5_theme"]["B2_pass"]
            and not blk["repaired_4_theme_insider_dropped"]["B2_pass"])
        add[lab] = blk

    # WHAT THE VENDOR SWITCH COSTS, EXPRESSED IN THE UNITS THE RECORD ALREADY HAS. The ceiling
    # measured Sharadar against itself at 0.4971 over 63 trading days and ~0.95 over 6. Solving
    # the same linear interpolation for the observed cross-vendor rho says how many trading days
    # of ordinary drift the vendor change is worth. LABELLED an interpolation, like the ceiling.
    ceil = json.load(open(os.path.join(FA, "D9_NOISE_CEILING.json"), encoding="utf-8"))
    r63 = ceil["by_lag"]["1_rebalances_63_trading_days"]["composite_spearman_mean"]
    obs = add["freeze_2026-07-31"]["repaired_4_theme_insider_dropped"]["composite_spearman"]
    add["vendor_cost_in_trading_days"] = {
        "observed_cross_vendor_rho_repaired": obs,
        "same_vendor_rho_at_63_trading_days": r63,
        "equivalent_trading_days_of_drift": 63.0 * (1.0 - obs) / (1.0 - r63),
        "LABEL": ("INTERPOLATION on the same linear-in-trading-days map the ceiling used. It "
                  "says the vendor switch disrupts the large-cap ranking by about as much as "
                  "letting the panel go stale for this many trading days."),
    }
    rep["addendum_insider_degeneracy"] = add
    json.dump(rep, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(add, indent=1, default=str))
    print("\nupdated", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
