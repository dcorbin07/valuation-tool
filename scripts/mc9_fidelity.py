# -*- coding: utf-8 -*-
"""MC9 step 4 — `B7` FIDELITY of the SEP ADV against the two series that already exist.

ZERO TRIALS. Nothing here ranks, filters or scores.

TWO COMPARISONS, AND THEY ARE EXPECTED TO GO OPPOSITE WAYS. That is what makes the pair a test
rather than a reassurance:

* **vs CRSP** (`B13_ADV_PANEL.pkl`, 90,025 cells). CRSP pairs as-traded `|prc|` with as-traded
  `vol`; SEP pairs split-adjusted `close` with split-adjusted `volume`. **Dollar volume is
  split-INVARIANT when both legs share a basis**, so these two must AGREE -- median ratio ~1.000
  on both sides of every split. A disagreement concentrated at splits would mean one of the two
  pairings is mixed.
* **vs `adv_from_bars`** (`scripts/capacity.py:69`). `B13_ADV_BARS_DEFECT.json` already measured
  that bars' `volume` is split-ADJUSTED while its `raw_close` is AS-TRADED -- volume ratio
  bars/CRSP reads **50.0** for CMG and **1.0** for the price on the same rows. So bars multiplies
  an unadjusted price by an adjusted share count and is wrong by the split factor BEFORE each
  split. **The disagreement is expected to resolve AGAINST bars**, and this quantifies it.
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

from valuation.edge import adv_sep as A                                # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
DATA = os.path.join(_ROOT, "data")
FA = os.path.join(DATA, "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
CRSP = os.path.join(FA, "B13_ADV_PANEL.pkl")
CACHE = os.path.join(FA, "MC9_SEP_ADV.pkl")
BARS = os.path.join(DATA, "bulk", "prepared", "bars")
OUT = os.path.join(FA, "MC9_FIDELITY.json")

APART = 0.25          # "> 25% apart", the brief's own wording


def _pit_index():
    d = pd.read_pickle(CACHE)
    by_t = d["by_ticker"]
    ser = A.adv_series(by_t)
    idx = A.by_cell(ser)
    sessions = {t: [r[0] for r in rows] for t, rows in by_t.items()}
    return idx, sessions, by_t


def _ratio_block(r):
    r = np.asarray([x for x in r if np.isfinite(x) and x > 0], dtype=float)
    if not r.size:
        return {"n": 0}
    return {"n": int(r.size), "median_ratio": float(np.median(r)),
            "p05": float(np.percentile(r, 5)), "p95": float(np.percentile(r, 95)),
            "share_more_than_25pct_apart":
                float(np.mean((r > 1.0 + APART) | (r < 1.0 / (1.0 + APART))))}


def main() -> int:
    panel = pd.read_pickle(PANEL)
    panel["_d"] = panel["date"].astype(str).str[:10]
    panel["_t"] = panel["ticker"].astype(str).str.upper()
    idx, sessions, by_t = _pit_index()

    out = {"item": "MC9", "step": "B7 fidelity", "trials": 0}

    # ---------------- vs CRSP, on CRSP's own 90,025 cells
    crsp = pd.read_pickle(CRSP)
    crsp["_t"] = crsp["ticker"].astype(str).str.upper()
    crsp["_d"] = crsp["date"].astype(str).str[:10]
    rows = []
    for t, d0, a_crsp in zip(crsp["_t"], crsp["_d"], crsp["adv"]):
        a_sep = A.pit_adv_at(idx, t, d0, sessions.get(t, ()))
        if a_sep is not None and a_crsp and np.isfinite(a_crsp) and a_crsp > 0:
            rows.append((t, d0, float(a_crsp), float(a_sep)))
    f = pd.DataFrame(rows, columns=["ticker", "date", "crsp", "sep"])
    f["ratio"] = f["sep"] / f["crsp"]
    out["vs_crsp"] = dict(_ratio_block(f["ratio"]),
                          crsp_cells=int(len(crsp)),
                          overlapping_cells=int(len(f)),
                          sep_covers_crsp_cells=float(len(f) / max(1, len(crsp))))

    # by size decile -- the brief's third cut. `size` is the panel's own theme column, so the
    # decile is the one the composite uses rather than a market cap re-derived here.
    key = panel.set_index(["_t", "_d"])
    have_mc = "market_cap" in panel.columns
    if have_mc:
        mc = key["market_cap"]
        f["mc"] = [mc.get((t, d), np.nan) for t, d in zip(f["ticker"], f["date"])]
        ok = f[np.isfinite(f["mc"])].copy()
        if len(ok) > 100:
            ok["dec"] = pd.qcut(ok["mc"].rank(method="first"), 10, labels=False)
            out["vs_crsp_by_size_decile"] = {
                int(k): _ratio_block(g["ratio"]) for k, g in ok.groupby("dec")}
    out["vs_crsp_by_size_decile_note"] = (
        "decile 0 = smallest by the panel's own market_cap" if have_mc
        else "market_cap absent from the panel; decile cut not taken")

    # ---------------- vs adv_from_bars, on the bars cells
    bars_rows = []
    if os.path.isdir(BARS):
        have = {fn[:-4] for fn in os.listdir(BARS) if fn.endswith(".pkl")}
        for t in sorted(have):
            T = t.upper()
            if T not in by_t:
                continue
            try:
                b = pd.read_pickle(os.path.join(BARS, "%s.pkl" % t))
            except Exception:
                continue
            # The bars cache is a DICT OF LISTS, not a DataFrame -- `adv_from_bars` reads it
            # with `b["date"]`, which works for both, so a `.columns` access here looked right
            # and was not. Handled explicitly rather than duck-typed.
            keys = set(b.keys()) if isinstance(b, dict) else set(b.columns)
            if not {"date", "raw_close", "volume"} <= keys:
                continue
            bd = pd.DataFrame({
                # `pd.to_datetime` on a LIST returns a DatetimeIndex, which has `.strftime`
                # directly and no `.dt` accessor -- the dict-of-lists shape again.
                "date": pd.DatetimeIndex(pd.to_datetime(b["date"])).strftime("%Y-%m-%d"),
                "dv_bars": np.asarray(b["raw_close"], float) * np.asarray(b["volume"], float)})
            sep = pd.DataFrame(by_t[T], columns=["date", "o", "h", "l", "close",
                                                 "volume", "closeunadj"])
            sep["dv_sep"] = sep["close"] * sep["volume"]
            sep["split_factor"] = sep["closeunadj"] / sep["close"]
            m = bd.merge(sep[["date", "dv_sep", "split_factor"]], on="date", how="inner")
            m = m[(m["dv_bars"] > 0) & (m["dv_sep"] > 0)]
            for d0, db, ds, sf in zip(m["date"], m["dv_bars"], m["dv_sep"],
                                      m["split_factor"]):
                bars_rows.append((T, d0, float(db), float(ds), float(sf)))
    bf = pd.DataFrame(bars_rows, columns=["ticker", "date", "bars", "sep", "split_factor"])
    if len(bf):
        bf["ratio"] = bf["bars"] / bf["sep"]
        out["vs_bars"] = dict(_ratio_block(bf["ratio"]),
                              names=int(bf["ticker"].nunique()))
        # THE DISCRIMINATING CUT: rows BEFORE a split (factor > 1) against rows at factor ~1.
        # If bars mixes bases, the disagreement lives entirely in the split-affected rows and
        # its size IS the split factor.
        # A REVERSE split has a factor BELOW 1 (SIRI's 1:10 reads 0.0995), so a one-sided
        # `> 1.01` cut misfiles those rows as UNSPLIT and contaminates the control bucket with
        # the very disagreement it exists to exclude. Found by SIRI showing a median ratio of
        # 0.1 inside the "unsplit" group. The cut is on DISTANCE FROM 1 in either direction.
        _far = (bf["split_factor"] > 1.01) | (bf["split_factor"] < 1.0 / 1.01)
        pre = bf[_far]
        flat = bf[~_far]
        out["vs_bars_split_affected_rows"] = _ratio_block(pre["ratio"])
        out["vs_bars_unsplit_rows"] = _ratio_block(flat["ratio"])
        if len(pre) > 20:
            out["vs_bars_ratio_vs_split_factor_corr"] = float(
                np.corrcoef(pre["ratio"], pre["split_factor"])[0, 1])
        out["vs_bars_named"] = {}
        for t in ("CMG", "AAPL", "WMT", "MSTR", "SIRI", "JPM"):
            g = bf[bf["ticker"] == t]
            if len(g):
                _gfar = ((g["split_factor"] > 1.01)
                         | (g["split_factor"] < 1.0 / 1.01))
                gp, gf = g[_gfar], g[~_gfar]
                out["vs_bars_named"][t] = {
                    "rows": int(len(g)),
                    "median_ratio_bars_over_sep_SPLIT_AFFECTED":
                        float(gp["ratio"].median()) if len(gp) else None,
                    "median_ratio_bars_over_sep_UNSPLIT":
                        float(gf["ratio"].median()) if len(gf) else None,
                    "median_split_factor_on_affected":
                        float(gp["split_factor"].median()) if len(gp) else None}
    else:
        out["vs_bars"] = {"n": 0, "note": "no overlapping bars cells"}

    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
