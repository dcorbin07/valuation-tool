#!/usr/bin/env python3
"""s10_build_band_panel.py — the point-in-time fair-value panel WITH the scenario band.  [S10]

Rebuilds S23's valuation panel with `with_scenarios=True`, so every row carries the blended
bear/bull pair the live site renders as its scenario card. The band comes from
`pipeline._blend_scenarios` — imported, never re-implemented (PREREG_s10_downside_exclusion.md
§2, control C2).

`offline=True` pins the beta point-in-time, so the WACC ladder cannot reach its network rung and
value a 2011 cross-section with a beta regressed on 2021-2026 returns (S23's defect, control C7).

    python -m scripts.s10_build_band_panel \
        --data-dir C:/Users/donni/Downloads/valuation-tool/data/backtest \
        --out      C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_s10_band.pkl
"""
from __future__ import annotations

import argparse
import os
import sys
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rebalance-days", type=int, default=63)
    ap.add_argument("--horizon", type=int, default=63)
    ap.add_argument("--lookback-years", type=int, default=18)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    from valuation.edge.data_providers import WRDSProvider
    from valuation.engine.calibration import build_valuation_panel

    class _C:
        wrds_data_dir = args.data_dir

    t0 = time.time()
    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        print(f"Provider not ready: {msg}")
        return 1

    tickers = prov.universe(limit=args.limit) or []
    if not tickers:
        print("No tickers in the export.")
        return 1
    if len(tickers) < 2000:
        print(f"*** SMOKE TEST ONLY ({len(tickers)} names) — the methodology rule requires the "
              f"FULL universe for any keep/reject verdict. ***", flush=True)
    print(f"[s10] universe {len(tickers)} names", flush=True)

    panel = build_valuation_panel(prov, tickers, rebalance_days=args.rebalance_days,
                                  lookback_years=args.lookback_years, horizon=args.horizon,
                                  offline=True, with_scenarios=True)
    if panel.empty:
        print("Empty panel.")
        return 1

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    panel.to_pickle(args.out)
    have_bull = int(panel["bull_value"].notna().sum()) if "bull_value" in panel else 0
    print(f"[s10] wrote {args.out}", flush=True)
    print(f"[s10] rows {len(panel):,}  dates {panel['date'].nunique()}  "
          f"names {panel['ticker'].nunique()}  bull non-null {have_bull:,} "
          f"({have_bull/max(1,len(panel)):.1%})  in {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
