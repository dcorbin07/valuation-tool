#!/usr/bin/env python3
"""dump_panel.py — build the scored point-in-time panel once and pickle it.  [X3, X6]

The full backtest takes ~12 min and spends most of it on CPCV, cost models and gates that
neither X3 (ablation) nor X6 (structural breaks) reads. Both of those items need exactly one
object: the panel with `keep_numbers=True`, i.e. every standardized per-signal `z_*` column
plus the theme columns and the forward return.

This builds it with the SAME arguments `run_backtests` uses (rebalance_days=63,
lookback_years=18, horizon=63) so the panel is identical to the one behind
BACKTEST_RESULTS.json — not a cheaper approximation of it.

Modifies no existing file. Read-only against the repo; writes one pickle.

    python scripts/dump_panel.py --data-dir data/backtest --out data/free_analysis/panel.pkl
"""
from __future__ import annotations

import argparse
import os
import sys
import time


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dump the scored fundamental panel (X3/X6 input).")
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--out", default="data/free_analysis/panel.pkl")
    ap.add_argument("--limit", type=int, default=None,
                    help="universe cap; default is the config's full universe (3000)")
    args = ap.parse_args(argv)

    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.screener import universe as U
    from valuation.edge.fundamental_panel import build_fundamental_panel

    if os.path.exists(args.out):
        print(f"[dump_panel] {args.out} already exists — nothing to do.", flush=True)
        return 0

    class _C:
        wrds_data_dir = args.data_dir

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        print(f"[dump_panel] provider not ready: {msg}", file=sys.stderr, flush=True)
        return 1

    limit = args.limit or CONFIG.backtest_universe_limit
    tickers = prov.universe(limit=limit) or list(U.bundled_tickers())[:limit]
    print(f"[dump_panel] {len(tickers)} names via {prov.name}; building panel "
          f"(rebalance=63d, lookback={CONFIG.backtest_lookback_years}y, horizon=63d, "
          f"keep_numbers=True) …", flush=True)

    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=63,
        keep_numbers=True,
    )
    print(f"[dump_panel] built {len(panel):,} rows x {len(panel.columns)} cols "
          f"in {time.time() - t0:.0f}s", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    panel.to_pickle(args.out)
    print(f"[dump_panel] wrote {args.out}", flush=True)

    zc = [c for c in panel.columns if str(c).startswith("z_")]
    print(f"[dump_panel] {len(zc)} z_ columns; dates={panel['date'].nunique() if 'date' in panel else '?'}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
