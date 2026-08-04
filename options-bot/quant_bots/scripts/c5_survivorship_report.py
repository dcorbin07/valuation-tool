#!/usr/bin/env python3
"""
c5_survivorship_report.py — run the point-in-time universe on REAL data.

C5. `core/pit_universe.py` reconstructs a survivorship-free universe and reports
how many of its names are invisible to a live screener today. Both it and
`AsOfHistory` had only ever been verified against a synthetic 30-name mirror in
which 8 names delist mid-window. This runs them on the real Sharadar freeze.

The number this exists to produce is the one the audit asks for:

    pct_invisible_to_a_live_screener, PER PERIOD

i.e. of the companies genuinely in the tradable universe on a historical date,
what share are dead today and therefore structurally absent from any universe a
live screener could build. That is the size of the bias every prior
today's-universe backtest carried.

Reported per period, never averaged: the bias necessarily grows with distance
into the past, and a single 18-year mean would conceal exactly that.

    python scripts/c5_survivorship_report.py \
        --db ../../data/c5_pit_mirror.db \
        --dates 2000-06-30,...,2026-06-30 \
        --json ../../data/c5_survivorship.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.pit_universe import PITUniverseBuilder, PITUniverseConfig
from core.sharadar import AsOfHistory, SharadarStore

logger = logging.getLogger("c5")


def check_no_lookahead_fields(store):
    """
    Anti-cheat, pre-committed: the universe must not be filtered on
    TICKERS.scalemarketcap / scalerevenue. Those are MAX-OVER-LIFETIME buckets —
    a company that became a mega-cap in 2024 is labelled mega-cap in 2005 — so
    filtering on them leaks look-ahead into the very universe being validated.

    `pit_universe` refuses to offer them. This asserts the mirror does not even
    carry them, which makes the mistake structurally impossible rather than
    merely discouraged.
    """
    cols = {r[1] for r in store.db.execute("PRAGMA table_info(tickers)")}
    leaky = cols & {"scalemarketcap", "scalerevenue"}
    return {"tickers_columns": len(cols),
            "lookahead_columns_present": sorted(leaky),
            "pass": not leaky}


def check_asof_history(store, as_of, probe_ticker):
    """
    `AsOfHistory` is the structural look-ahead backstop: it must refuse to return
    any bar after its as-of date, no matter what window a caller asks for. Only
    ever tested on the synthetic mirror. Test it on real data.
    """
    hist = AsOfHistory(store, as_of, adjusted=True)
    rows = hist.get_history(probe_ticker, as_of - timedelta(days=365),
                            as_of + timedelta(days=365))
    after = [r for r in rows if r["date"] > as_of.isoformat()]
    return {
        "as_of": as_of.isoformat(),
        "probe": probe_ticker,
        "bars_returned": len(rows),
        "bars_after_as_of": len(after),
        "pass": len(rows) > 0 and not after,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="C5 — PIT universe on real data.")
    p.add_argument("--db", required=True)
    p.add_argument("--dates", required=True)
    p.add_argument("--json", default=None)
    p.add_argument("--min-price", type=float, default=None)
    p.add_argument("--min-market-cap", type=float, default=None)
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    store = SharadarStore(Path(args.db))
    dates = [date.fromisoformat(s.strip()) for s in args.dates.split(",") if s.strip()]

    kw = {}
    if args.min_price is not None:
        kw["min_price"] = args.min_price
    if args.min_market_cap is not None:
        kw["min_market_cap"] = args.min_market_cap
    cfg = PITUniverseConfig(**kw)
    builder = PITUniverseBuilder(store, cfg)

    out = {
        "db": args.db,
        "config": {"min_price": cfg.min_price, "min_market_cap": cfg.min_market_cap,
                   "min_avg_volume": cfg.min_avg_volume,
                   "exchanges": list(cfg.exchanges), "include_adrs": cfg.include_adrs},
        "anti_cheat": check_no_lookahead_fields(store),
        "periods": [],
    }

    print(f"{'as_of':<12} {'universe':>9} {'delisted':>9} {'invisible':>10}   examples")
    print("-" * 78)
    for d in dates:
        try:
            rep = builder.survivorship_report(d)
        except Exception as e:                      # a bad date must not kill the sweep
            print(f"{d.isoformat():<12} ERROR {e}")
            out["periods"].append({"as_of": d.isoformat(), "error": str(e)})
            continue
        out["periods"].append(rep)
        print(f"{rep['as_of']:<12} {rep['universe_size']:>9,} "
              f"{rep['delisted_since']:>9,} "
              f"{rep['pct_invisible_to_a_live_screener']:>9.1f}%   "
              f"{', '.join(rep['examples'][:5])}")

    ok = [r for r in out["periods"] if "error" not in r and r["universe_size"] > 0]
    if ok:
        pcts = sorted(r["pct_invisible_to_a_live_screener"] for r in ok)
        med = pcts[len(pcts) // 2]
        out["summary"] = {
            "periods_with_a_universe": len(ok),
            "median_pct_invisible": med,
            "min_pct_invisible": pcts[0],
            "max_pct_invisible": pcts[-1],
            "universe_size_min": min(r["universe_size"] for r in ok),
            "universe_size_max": max(r["universe_size"] for r in ok),
            "any_delisted_included": any(r["delisted_since"] > 0 for r in ok),
        }
        # The pre-registered interpretation, applied mechanically so it cannot
        # drift once the number is on screen.
        band = ("m < 2% — the bias is SMALL and the record overstates it"
                if med < 2 else
                "m > 10% — prior today's-universe backtests are ARTEFACTS"
                if med > 10 else
                "2% <= m <= 10% — material but bounded")
        out["summary"]["preregistered_band"] = band
        print("-" * 78)
        print(f"median invisible: {med:.1f}%  (min {pcts[0]:.1f}%, max {pcts[-1]:.1f}%) "
              f"over {len(ok)} periods")
        print(f"pre-registered band: {band}")

        # Probe the look-ahead backstop on a real, mid-history date.
        probe_date = ok[len(ok) // 2]
        pd_ = date.fromisoformat(probe_date["as_of"])
        snap = builder.build(pd_)
        probe_ticker = snap.symbols()[0] if snap.symbols() else "AAPL"
        out["asof_history_check"] = check_asof_history(store, pd_, probe_ticker)
        print(f"AsOfHistory backstop @ {pd_} on {probe_ticker}: "
              f"{out['asof_history_check']['bars_returned']} bars, "
              f"{out['asof_history_check']['bars_after_as_of']} after as-of -> "
              f"{'PASS' if out['asof_history_check']['pass'] else 'FAIL'}")
    print(f"anti-cheat (no scalemarketcap/scalerevenue in the mirror): "
          f"{'PASS' if out['anti_cheat']['pass'] else 'FAIL'}")

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2, default=str))
        print(f"wrote {args.json}")
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
