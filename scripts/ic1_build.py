# -*- coding: utf-8 -*-
"""IC1 — build the deadline-aligned panel, and read K2 on it. ZERO TRIALS (no outcome scored).

The grid: for each shipped rebalance date, the first trading day on or after the most recent
quarter end + 45 calendar days (the 13F statutory deadline) + a settling lag of ONE trading day.

THE SETTLING LAG IS FIXED AT 1 AND THE REASON IS STATED, because it is the one free parameter
and `K1`'s outcome moved with it. A filing made ON the deadline is available that evening at the
earliest, so the first session a book could ACT on it is the next one. Lag 0 would score a book
on filings it could not yet have read; lag 2+ discards a day of freshness for nothing. The draft
requires it "fixed in the register from the filing calendar and never tuned", and 1 is the only
value the calendar itself implies.

NOTHING HERE SCORES A RETURN. It builds the instrument and reads the free coverage kill.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

SETTLING_LAG_TD = 1
FILING_DEADLINE_DAYS = 45
PANEL_MIN_XS, PANEL_MAX_XS = 1471, 1954
QE = ((12, 31), (9, 30), (6, 30), (3, 31))


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
OUT_PANEL = os.path.join(FA, "panel_ic1_aligned.pkl")
OUT = os.path.join(FA, "IC1_K2.json")


def _calendar():
    seen = {}
    for f in sorted(glob.glob(os.path.join(DATA, "backtest", "prices", "*.csv")))[::10]:
        try:
            d = pd.read_csv(f, usecols=["date"])
        except Exception:
            continue
        for s in d["date"].astype(str).str[:10]:
            seen[s] = seen.get(s, 0) + 1
    q = max(2, int(0.10 * max(seen.values())))
    return [dt.date.fromisoformat(s) for s in sorted(seen) if seen[s] >= q]


def aligned_grid():
    cal = _calendar()
    idx = {d: i for i, d in enumerate(cal)}
    cs = set(cal)
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    out = []
    for p in sorted(panel["date"].unique()):
        p = pd.Timestamp(p).date()
        qe = max(dt.date(y, m, d) for y in (p.year, p.year - 1) for m, d in QE
                 if dt.date(y, m, d) < p)
        x = qe + dt.timedelta(days=FILING_DEADLINE_DAYS)
        while x not in cs:
            x += dt.timedelta(days=1)
        j = idx[x] + SETTLING_LAG_TD
        if j < len(cal):
            out.append(cal[j])
    return sorted(set(out))


def main() -> int:
    grid = aligned_grid()
    print("deadline-aligned grid: %d dates, %s .. %s"
          % (len(grid), grid[0], grid[-1]), flush=True)

    from valuation.edge.fundamental_panel import build_fundamental_panel
    from valuation.edge.data_providers import WRDSProvider

    class _C:
        wrds_data_dir = os.path.join(DATA, "backtest")

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready: %s" % msg)
    tickers = prov.universe(None)
    print("universe: %d names; building (this is the ~20 minute step)" % len(tickers), flush=True)

    t0 = time.time()
    panel = build_fundamental_panel(prov, tickers, rebalance_days=63, lookback_years=18,
                                    horizon=63, grid_dates=[str(d) for d in grid])
    print("built in %.1f min: %s" % ((time.time() - t0) / 60.0, panel.shape), flush=True)
    pd.to_pickle(panel, OUT_PANEL)

    xs = panel.groupby("date").size()
    base = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    bxs = base.groupby("date").size()
    res = {
        "item": "IC1", "pass": "0 free kills (K2)", "trials": 0,
        "settling_lag_td": SETTLING_LAG_TD,
        "grid_dates_requested": len(grid),
        "panel_dates_scored": int(panel["date"].nunique()),
        "panel_rows": int(len(panel)), "panel_names": int(panel["ticker"].nunique()),
        "cross_section": {"min": int(xs.min()), "median": float(xs.median()),
                          "max": int(xs.max())},
        "shipped_cross_section": {"min": int(bxs.min()), "median": float(bxs.median()),
                                  "max": int(bxs.max())},
        "K2_bar": {"min": PANEL_MIN_XS, "max": PANEL_MAX_XS},
        "K2_pass": bool(xs.min() >= PANEL_MIN_XS and xs.max() <= PANEL_MAX_XS),
        "K1_dates_kept": bool(panel["date"].nunique() >= 69),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nK2 cross-sections: min %d median %.0f max %d (bar %d..%d) -> %s"
          % (xs.min(), xs.median(), xs.max(), PANEL_MIN_XS, PANEL_MAX_XS,
             "PASS" if res["K2_pass"] else "FIRES"))
    print("dates scored: %d (shipped 69) -> %s"
          % (res["panel_dates_scored"], "PASS" if res["K1_dates_kept"] else "FIRES"))
    print("wrote", OUT_PANEL, "and", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
