#!/usr/bin/env python3
"""
Build the trading universe and save it to disk.

Usage from the project root:
    python scripts/build_universe.py            # uses defaults
    python scripts/build_universe.py --top 100  # show top 100 after build
    python scripts/build_universe.py --force    # rebuild even if today's snapshot exists

The output is written to:
    data/cache/universe_<YYYY-MM-DD>.json

This is what downstream layers (the screener in V3) will consume.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Make the project root importable regardless of where this is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from broker import TradierClient, TradierConfig  # noqa: E402
from data import UniverseBuilder, UniverseConfig  # noqa: E402


def _load_env() -> tuple[str, str, bool]:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    token = os.environ.get("TRADIER_TOKEN")
    account_id = os.environ.get("TRADIER_ACCOUNT_ID")
    sandbox = os.environ.get("TRADIER_SANDBOX", "true").lower() != "false"

    if not token:
        sys.exit("ERROR: TRADIER_TOKEN not set.")
    if not account_id:
        sys.exit("ERROR: TRADIER_ACCOUNT_ID not set.")
    return token, account_id, sandbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the trading universe.")
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top names to display after build (default: 20).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if today's snapshot already exists on disk.",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=None,
        help="Override min price filter.",
    )
    parser.add_argument(
        "--min-market-cap",
        type=float,
        default=None,
        help="Override min market cap filter (raw dollars).",
    )
    parser.add_argument(
        "--min-avg-volume",
        type=int,
        default=None,
        help="Override min 30-day avg daily volume filter.",
    )
    parser.add_argument(
        "--no-etfs",
        action="store_true",
        help="Skip the ETF whitelist (equities only).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("build_universe")

    cache_dir = PROJECT_ROOT / "data" / "cache"
    today_path = cache_dir / f"universe_{date.today().isoformat()}.json"

    if today_path.exists() and not args.force:
        logger.info("Today's snapshot already exists at %s", today_path)
        logger.info("(Use --force to rebuild.)")
        snapshot = UniverseBuilder.load(today_path)
    else:
        token, account_id, sandbox = _load_env()
        tradier_config = TradierConfig(
            access_token=token,
            account_id=account_id,
            sandbox=sandbox,
        )

        config_kwargs: dict = {}
        if args.min_price is not None:
            config_kwargs["min_price"] = args.min_price
        if args.min_market_cap is not None:
            config_kwargs["min_market_cap"] = args.min_market_cap
        if args.min_avg_volume is not None:
            config_kwargs["min_avg_volume"] = args.min_avg_volume
        if args.no_etfs:
            config_kwargs["include_etfs"] = False

        universe_config = UniverseConfig(**config_kwargs)

        with TradierClient(tradier_config) as tradier:
            builder = UniverseBuilder(universe_config, tradier)
            snapshot = builder.build()
            builder.save(snapshot, today_path)

    # ─── Print summary ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"  Universe snapshot: {snapshot.count} tickers")
    print(f"  Saved to: {today_path}")
    print("=" * 70)

    etfs = [t for t in snapshot.tickers if t.is_etf]
    stocks = [t for t in snapshot.tickers if not t.is_etf]
    print(f"  Stocks: {len(stocks)}")
    print(f"  ETFs:   {len(etfs)}")
    print()

    print(f"Top {args.top} by sort priority (ETFs first, then market cap):")
    print(f"  {'Symbol':<7} {'Type':<5} {'Price':>10} {'Market Cap':>15} {'Avg Volume':>14}")
    print("  " + "-" * 60)
    for t in snapshot.tickers[: args.top]:
        cap_str = (
            f"${t.market_cap/1e9:.1f}B"
            if t.market_cap >= 1e9
            else (f"${t.market_cap/1e6:.0f}M" if t.market_cap else "—")
        )
        vol_str = (
            f"{int(t.avg_volume_30d):,}"
            if t.avg_volume_30d is not None
            else "—"
        )
        type_str = "ETF" if t.is_etf else "STK"
        print(
            f"  {t.symbol:<7} {type_str:<5} {t.last_price:>10.2f} "
            f"{cap_str:>15} {vol_str:>14}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
