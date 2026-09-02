# -*- coding: utf-8 -*-
"""PKG-MB20 STAGE 0b — THE BITE, measured on the arm's own population BEFORE any register.

ZERO TRIALS. No forward return is loaded, no outcome statistic is computed, and the word
`fwd_ret` appears nowhere in the arm path this builds. It answers one question:

    On the rows the shipped insider theme is actually scored on, how much does removing routine
    traders MOVE the score?

WHY IT COMES FIRST. `W-1`'s `K2` and `W-28`'s `K1` both turned on a bar set against the wrong
population, and `W-28` died because a pre-committed bar could not be reached on this account at
all. A register whose intervention is nearly inert cannot return an interpretable null: it could
not tell "the hypothesis is false" from "nothing was done". So the bite is measured, printed,
and only THEN is a bar written -- `W-28`'s closing lesson, applied to this register's own kill.

The score is the SHIPPED one. `_insider_formula` is CALLED, never re-implemented (`B7`), and the
window arithmetic is `_insider_score_at`'s so the two arms differ in the ROW SET and in nothing
else.
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

from valuation.edge.fundamental_panel import _insider_formula        # noqa: E402
from valuation.studies import insider_routine as IR                  # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
SRC = os.path.join(_ROOT, "data", "backtest", "insiders.csv")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
OUT = os.path.join(FA, "MB20_BITE.json")

LOOKBACK_DAYS = 90          # the shipped default


def _prep():
    """Per-ticker (filingdates, values, routine_mask), sorted by filing date.

    `values` is exactly what `_insider_score_at` sums: signed shares x price where both exist,
    else the unsigned `transactionvalue`. That fallback fires on 2 rows of 5.6M (`MA57`), so it
    is effectively dead, but it is reproduced rather than dropped because the arms must differ in
    the row set alone.
    """
    d = pd.read_csv(SRC, low_memory=False,
                    usecols=["ticker", "filingdate", "transactiondate", "ownername",
                             "transactionshares", "transactionpricepershare",
                             "transactionvalue"])
    sh = pd.to_numeric(d["transactionshares"], errors="coerce")
    pr = pd.to_numeric(d["transactionpricepershare"], errors="coerce")
    va = pd.to_numeric(d["transactionvalue"], errors="coerce")
    val = (sh * pr).where(sh.notna() & pr.notna(), va)
    fd = pd.to_datetime(d["filingdate"], errors="coerce")

    keep = val.notna() & fd.notna()
    d = d[keep].copy()
    d["_val"] = val[keep].to_numpy()
    d["_fd"] = fd[keep].to_numpy()
    d["_label"] = IR.classify(d)
    cov = IR.coverage(d["_label"])

    d = d.sort_values("_fd")
    out = {}
    for tk, g in d.groupby(d["ticker"].astype(str).str.upper(), sort=False):
        out[tk] = (g["_fd"].to_numpy("datetime64[D]"),
                   g["_val"].to_numpy(float),
                   (g["_label"].to_numpy() != IR.ROUTINE))
    return out, cov, int(len(d))


def _score(dts, vals, hi, lookback=LOOKBACK_DAYS):
    """`_insider_score_at`'s window arithmetic, then the SHIPPED formula. None where it is None."""
    lo = hi - np.timedelta64(lookback, "D")
    a = int(np.searchsorted(dts, lo, side="left"))
    b = int(np.searchsorted(dts, hi, side="left"))
    if b <= a:
        return None
    w = vals[a:b]
    net, buys = float(w.sum()), int((w > 0).sum())
    return _insider_formula(net, buys)


def main() -> int:
    prep, cov, n_rows = _prep()
    panel = pd.read_pickle(PANEL)
    grid = panel[["date", "ticker"]].drop_duplicates()
    dates = sorted(set(str(x)[:10] for x in grid["date"]))

    n_cells = 0
    n_base = n_opp = 0          # cells where each arm returns a score
    n_moved = 0                 # cells where the score CHANGES
    n_lost = 0                  # cells scoreable in base and NOT in the variant
    deltas = []
    for d0 in dates:
        hi = np.datetime64(d0, "D")
        sub = grid[grid["date"].astype(str).str[:10] == d0]
        for tk in sub["ticker"].astype(str).str.upper():
            p = prep.get(tk)
            n_cells += 1
            if p is None:
                continue
            dts, vals, keep = p
            a = _score(dts, vals, hi)
            b = _score(dts[keep], vals[keep], hi)
            n_base += a is not None
            n_opp += b is not None
            if a is None:
                continue
            if b is None:
                n_lost += 1
                continue
            if a != b:
                n_moved += 1
                deltas.append(b - a)

    dl = np.asarray(deltas, dtype=float)
    out = {
        "item": "PKG-MB20", "stage": "bite", "trials": 0,
        "rule": "3 consecutive years, same calendar month, same (ticker, ownername)",
        "insider_rows_scoreable": n_rows,
        "classification_coverage_on_scoreable_rows": cov,
        "panel_cells": n_cells,
        "cells_with_a_shipped_score": n_base,
        "cells_with_an_opportunistic_score": n_opp,
        "cells_the_variant_cannot_score": n_lost,
        "cells_whose_score_MOVES": n_moved,
        "bite_frac_of_scored_cells": (n_moved / n_base) if n_base else None,
        "delta": ({"n": int(dl.size), "mean": float(dl.mean()),
                   "median": float(np.median(dl)),
                   "p05": float(np.percentile(dl, 5)),
                   "p95": float(np.percentile(dl, 95)),
                   "min": float(dl.min()), "max": float(dl.max()),
                   "frac_negative": float((dl < 0).mean())} if dl.size else None),
    }
    os.makedirs(FA, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
