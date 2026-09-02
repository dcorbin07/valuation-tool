# -*- coding: utf-8 -*-
"""PKG-MB20 STAGE 0c — the SIZE-COSTUME subject, measured BEFORE its bar is written.

ZERO TRIALS, no forward return loaded anywhere.

`R6`'s ghost. That item's arm never ran: its flat aggregate of the 29 graveyard signals read
**0.6114** against the `size` theme and was WITHDRAWN on a costume kill, because a candidate
orthogonal to the blend while proxying its most load-bearing component is the costume that
matters most (`X3`: `size` has the worst theme IC and carries the composite's entire
significance). `U7` and `S10` died the same way in different clothes.

THE SUBJECT HERE IS THE INTERVENTION, NOT THE SIGNAL. What the arm does is MOVE the insider
score on some names and not others. If which names move is largely a size sort, then a verdict
about "routine versus opportunistic" would really be a verdict about market capitalisation.

Measured first, bar written afterwards with the distribution in view -- `W-28` died on a bar its
account could not reach, and `W-1`'s own `K2` was set from the wrong arm's bite and would have
killed a legitimate register. A bar chosen before the distribution is a bar chosen blind.
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

from scripts.mb20_bite import _prep, _score                          # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
OUT = os.path.join(FA, "MB20_COSTUME.json")


def main() -> int:
    prep, cov, _ = _prep()
    panel = pd.read_pickle(PANEL)
    themes = [c for c in ("size", "value", "quality", "momentum", "insider",
                          "institutional", "capital_discipline") if c in panel.columns]

    rows = []
    for d0, g in panel.groupby(panel["date"].astype(str).str[:10]):
        hi = np.datetime64(d0, "D")
        for tk, idx in zip(g["ticker"].astype(str).str.upper(), g.index):
            p = prep.get(tk)
            if p is None:
                continue
            dts, vals, keep = p
            a = _score(dts, vals, hi)
            if a is None:
                continue
            b = _score(dts[keep], vals[keep], hi)
            rows.append((d0, idx, a, b if b is not None else a, 1 if b is None else 0))

    df = pd.DataFrame(rows, columns=["date", "idx", "base", "opp", "fellback"]).set_index("idx")
    df["delta"] = df["opp"] - df["base"]
    df["moved"] = (df["delta"] != 0).astype(float)
    j = panel.loc[df.index, themes].join(df[["date", "delta", "moved", "fellback"]])

    out = {"item": "PKG-MB20", "stage": "costume", "trials": 0,
           "n_rows": int(len(j)), "n_dates": int(j["date"].nunique()),
           "fallback_cells": int(j["fellback"].sum()),
           "per_theme_mean_abs_spearman": {}}

    for t in themes:
        rs_d, rs_m = [], []
        for _d, g in j.groupby("date"):
            if len(g) < 20:
                continue
            if g[t].notna().sum() >= 20 and g["delta"].nunique() > 1:
                rs_d.append(g[[t, "delta"]].corr(method="spearman").iloc[0, 1])
            if g[t].notna().sum() >= 20 and g["moved"].nunique() > 1:
                rs_m.append(g[[t, "moved"]].corr(method="spearman").iloc[0, 1])
        rs_d = [x for x in rs_d if pd.notna(x)]
        rs_m = [x for x in rs_m if pd.notna(x)]
        out["per_theme_mean_abs_spearman"][t] = {
            # The SIGNED mean says which way it leans; the mean of ABSOLUTE values is what a
            # costume kill must bar, because a correlation that flips sign across dates still
            # means the intervention is picking names on that axis.
            "delta_signed_mean": float(np.mean(rs_d)) if rs_d else None,
            "delta_mean_abs": float(np.mean(np.abs(rs_d))) if rs_d else None,
            "moved_signed_mean": float(np.mean(rs_m)) if rs_m else None,
            "moved_mean_abs": float(np.mean(np.abs(rs_m))) if rs_m else None,
            "dates": len(rs_d),
        }

    os.makedirs(FA, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
