#!/usr/bin/env python3
"""u1_entry.py — mine the U1 grid: every optionable name at every rebalance date.  [AUDIT U1]

    python -m scripts.u1_entry --data-root <repo>/data [--workers 6]

Pre-registered in `PREREG_u1_composite_entry.md` (committed alone at `7d7c414`). This script
produces NO verdict and computes NO bar. It mines one corpus — 182 names x 39 rebalance dates —
and banks it. Selection, nulls, bars and the verdict live in `scripts/u1_score.py`, written
afterwards, so the calibration can be committed before any arm is scored against it.

RESUMABLE PER DATE. Each rebalance date's rows are written atomically and skipped if present, so
a kill costs at most the date in flight. This is not defensive decoration: a `run_in_background`
task here has been reaped twice at 15-20 minutes mid-sweep with `status: killed` and no error.

READ-ONLY on `data/options/`. The contract rule, fill model and shipped exit are CALLED from
`options_backtest`, never reimplemented — the entry sequence is byte-for-byte the one
`options_universe.random_entry_control` uses, with the entry DATES supplied by the composite
instead of by a random draw. That is the only difference between this book and the R2 control,
and it is the whole experiment.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import sys
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    """`data/` is gitignored and lives in the primary checkout, so a worktree looks up.

    MUST NOT raise at import — `tests/test_u1_entry.py` imports this module to pin the arm set
    and the join, and a fresh CI checkout has no `data/` at all. An import-time SystemExit would
    fail the whole auto-land gate.
    """
    for cand in (os.path.join(_HERE, "data"),
                 os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
OUT_DIR = os.path.join(DATA, "options_u1")
CHUNK_DIR = os.path.join(OUT_DIR, "chunks")
GRID_PATH = os.path.join(OUT_DIR, "U1_GRID.pkl")
CELLS_PATH = os.path.join(OUT_DIR, "U1_CELLS.json")
PANEL = os.path.join(DATA, "free_analysis", "panel_corrected_69d.pkl")
SIGNAL_BOOK = os.path.join(DATA, "options_universe", "state_r2_corrected.pkl")

_G = {}


def _init(data_root: str, aggression: float):
    from valuation.edge import options_universe as U
    from valuation.edge.theta_bulk import ThetaBulk
    _G["prov"] = ThetaBulk(root=os.path.join(data_root, "options"), max_years_in_memory=3)
    _G["bars_dir"] = os.path.join(data_root, "bulk", "prepared", "bars")
    _G["caps"] = U.load_caps(data_root)
    _G["aggression"] = aggression
    from valuation.edge import options_backtest as OB
    _G["splits"] = OB.load_splits(data_root)


def _mine_cell(cell: dict, bars: dict) -> dict:
    """One candidate entry -> one trade row, or a counted reject.

    The sequence below is `options_universe.random_entry_control`'s, unchanged and in the same
    order, including the B1 as-traded spot and the O20 point-in-time liquidity fields. Any
    divergence here would make U1's book incomparable with the control it is measured against,
    which is the single most consequential thing this function could get wrong.
    """
    from valuation.edge import options_backtest as OB
    from valuation.edge.options_universe import cap_at, tier_of, pit_liquidity, pit_liquid_ok

    d = cell["entry"]
    w = OB.bars_asof(bars, d)
    if not w:
        return {"reject": "no_bars_asof"}
    day = dt.date.fromisoformat(d)
    chain = _G["prov"].chain_on(cell["ticker"], day)
    if chain is None or len(chain) == 0:
        return {"reject": "no_chain"}
    und = OB.spot_asof(w)                      # AUDIT B1 — as-traded, matching settlement
    row = OB.pick_contract(chain, und, day, right="C")
    if row is None:
        return {"reject": "no_contract_in_band"}
    # U1-SPLIT at source. U1 already filtered these rows post hoc; passing the guard here means a
    # re-mine never produces them in the first place, and the two routes must agree exactly —
    # `test_u1_split_repair` pins that equivalence, since it is what lets the banked books be
    # re-banked by filtering rather than re-mined.
    t = OB.simulate_trade(_G["prov"], cell["ticker"], row, day, bars,
                          aggression=_G["aggression"], splits=_G.get("splits"))
    if not t or not t.get("ok"):
        # Propagate the REASON. This used to collapse every simulation failure to "no_trade",
        # which silently hid the U1-SPLIT guard's own rejections behind a generic counter —
        # found by the equivalence check, not by reading the code. The register promised these
        # would be counted and named, so they are.
        return {"reject": str((t or {}).get("reason") or "no_trade")}
    r = OB.to_alert_row(cell["ticker"], day, row, t, None, [], None, None)
    mc = cap_at(_G["caps"], cell["ticker"], d)
    r["marketcap_musd"] = mc
    r["cap_tier"] = tier_of(mc)
    r["entry_spread_pct"] = t.get("entry_spread_pct")
    _pl = pit_liquidity(chain, day)
    r["pit_liquid"] = pit_liquid_ok(_pl)
    r["pit_median_spread_pct"] = _pl.get("median_spread_pct")
    r["pit_atm_oi"] = _pl.get("atm_oi")
    r["pit_atm_oi_notional"] = _pl.get("atm_oi_notional")
    # the U1 fields — what selected this cell, and which rebalance said so
    r["asof"] = cell["asof"]
    r["u1_comp"] = cell["u1_comp"]
    r["u1_pct_univ"] = cell["u1_pct_univ"]
    return {"row": r}


def _mine_date(arg):
    """All cells for one rebalance date. One task = one checkpoint."""
    from valuation.edge import options_backtest as OB
    asof, cells = arg
    t0 = time.time()
    rows, rejects = [], {}
    bars_cache = {}
    for c in cells:
        tk = c["ticker"]
        if tk not in bars_cache:
            bars_cache[tk] = OB.load_bars(tk, cache_dir=_G["bars_dir"])
        b = bars_cache[tk]
        if not b:
            rejects["no_bars"] = rejects.get("no_bars", 0) + 1
            continue
        got = _mine_cell(c, b)
        if "row" in got:
            rows.append(got["row"])
        else:
            rejects[got["reject"]] = rejects.get(got["reject"], 0) + 1
    return {"asof": asof, "rows": rows, "rejects": rejects,
            "n_cells": len(cells), "seconds": time.time() - t0}


def _atomic_dump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(obj, f, protocol=4)
    os.replace(tmp, path)


def build_cells(data_root: str) -> tuple:
    """The grid, before any mining: which (date, ticker) pairs are candidates and why."""
    import pandas as pd
    from valuation.edge import composite_entry as CE
    from valuation.edge import options_backtest as OB
    from valuation.edge.fundamental_panel import _base_weights
    from valuation.screener import settings as S

    start, end = CE.window()
    panel = pd.read_pickle(PANEL)
    with open(SIGNAL_BOOK, "rb") as f:
        book = pickle.load(f)["rows"]
    alert_names = {str(r.get("ticker")) for r in book}
    panel_names = set(panel["ticker"].astype(str))
    universe = alert_names & panel_names
    dropped = sorted(alert_names - panel_names)

    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    weights = _base_weights(cols, "established")
    by_date = CE.universe_percentiles(panel, cols, weights, universe)

    bars_dir = os.path.join(data_root, "bulk", "prepared", "bars")
    bars_by_ticker = {}
    for tk in sorted(universe):
        b = OB.load_bars(tk, cache_dir=bars_dir)
        bars_by_ticker[tk] = list(b["date"]) if b else None

    cells = CE.grid_cells(by_date, bars_by_ticker, start, end)
    meta = {"window": [start, end],
            "n_alert_names": len(alert_names), "n_universe": len(universe),
            "names_dropped_not_in_panel": dropped,
            "themes": cols, "n_dates": len({c["asof"] for c in cells}),
            "n_cells": len(cells),
            "dates": sorted({c["asof"] for c in cells})}
    return cells, meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U1 — mine the composite-entry grid.")
    ap.add_argument("--data-root", default=DATA)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--aggression", type=float, default=1.0)
    ap.add_argument("--cells-only", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(CHUNK_DIR, exist_ok=True)
    print("[U1] building the grid ...", flush=True)
    cells, meta = build_cells(args.data_root)
    with open(CELLS_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    print("[U1] universe %d names (%d dropped: %s), %d dates, %d candidate cells"
          % (meta["n_universe"], len(meta["names_dropped_not_in_panel"]),
             ", ".join(meta["names_dropped_not_in_panel"]) or "-",
             meta["n_dates"], meta["n_cells"]), flush=True)
    if args.cells_only:
        return 0

    _init(args.data_root, args.aggression)
    by_date = {}
    for c in cells:
        by_date.setdefault(c["asof"], []).append(c)

    todo = []
    for asof in sorted(by_date):
        p = os.path.join(CHUNK_DIR, "%s.pkl" % asof)
        if not os.path.exists(p):
            todo.append((asof, by_date[asof]))
    print("[U1] %d of %d dates still to mine" % (len(todo), len(by_date)), flush=True)

    done = len(by_date) - len(todo)
    for arg in todo:
        got = _mine_date(arg)
        _atomic_dump(got, os.path.join(CHUNK_DIR, "%s.pkl" % got["asof"]))
        done += 1
        print("[U1] %s  %3d/%3d cells -> %3d trades  %-28s  %5.1fs  (%d/%d dates)"
              % (got["asof"], got["n_cells"], got["n_cells"], len(got["rows"]),
                 json.dumps(got["rejects"])[:28], got["seconds"], done, len(by_date)),
              flush=True)

    rows, rejects = [], {}
    for asof in sorted(by_date):
        p = os.path.join(CHUNK_DIR, "%s.pkl" % asof)
        if not os.path.exists(p):
            continue
        with open(p, "rb") as f:
            ch = pickle.load(f)
        rows.extend(ch["rows"])
        for k, v in ch["rejects"].items():
            rejects[k] = rejects.get(k, 0) + v
    _atomic_dump({"rows": rows, "rejects": rejects, "meta": meta}, GRID_PATH)
    print("[U1] GRID: %d trades from %d cells; rejects %s"
          % (len(rows), meta["n_cells"], json.dumps(rejects)), flush=True)
    print("[U1] -> %s" % GRID_PATH, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
