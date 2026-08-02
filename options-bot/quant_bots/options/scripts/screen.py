#!/usr/bin/env python3
"""
Run the screener against today's universe snapshot.

Usage from the project root:
    python scripts/screen.py                       # use today's universe, default config
    python scripts/screen.py --top 50              # show top 50 candidates
    python scripts/screen.py --no-earnings-filter  # skip the (slow) yfinance step
    python scripts/screen.py --universe data/cache/universe_2026-05-18.json

The output is written to:
    data/cache/candidates_<YYYY-MM-DD>.json
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from broker import TradierClient, TradierConfig  # noqa: E402
from data import EarningsCalendar, UniverseBuilder  # noqa: E402
from screener import Screener, ScreenerConfig  # noqa: E402


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
    parser = argparse.ArgumentParser(description="Run the daily screener.")
    parser.add_argument("--top", type=int, default=25, help="Show top N candidates in summary.")
    parser.add_argument("--universe", type=Path, default=None, help="Path to universe JSON (default: today's).")
    parser.add_argument("--no-earnings-filter", action="store_true", help="Skip yfinance earnings lookups (much faster).")
    parser.add_argument("--no-iv-filter", action="store_true", help="Skip ATM IV threshold filter.")
    parser.add_argument("--limit", type=int, default=None, help="Only screen first N tickers (for testing).")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("screen")

    # ─── Load universe ───────────────────────────────────────────────────────
    universe_path = args.universe or (
        PROJECT_ROOT / "data" / "cache" / f"universe_{date.today().isoformat()}.json"
    )
    if not universe_path.exists():
        sys.exit(
            f"Universe file not found: {universe_path}\n"
            "Run `python scripts/build_universe.py` first."
        )
    universe = UniverseBuilder.load(universe_path)
    logger.info("Loaded universe with %d tickers from %s", universe.count, universe_path)

    if args.limit:
        universe.tickers = universe.tickers[: args.limit]
        universe.count = len(universe.tickers)
        logger.info("Limited to first %d tickers for this run", args.limit)

    # ─── Config ──────────────────────────────────────────────────────────────
    config = ScreenerConfig(
        apply_earnings_filter=not args.no_earnings_filter,
        apply_atm_iv_filter=not args.no_iv_filter,
    )

    # ─── Run ─────────────────────────────────────────────────────────────────
    token, account_id, sandbox = _load_env()
    tradier_config = TradierConfig(
        access_token=token, account_id=account_id, sandbox=sandbox
    )

    earnings_calendar = (
        EarningsCalendar(unknown_means_safe=True) if config.apply_earnings_filter else None
    )

    with TradierClient(tradier_config) as tradier:
        screener = Screener(config, tradier, earnings_calendar)
        result = screener.screen(universe)

    out_path = PROJECT_ROOT / "data" / "cache" / f"candidates_{date.today().isoformat()}.json"
    screener.save(result, out_path)

    # ─── Summary ─────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"  Screener result: {len(result.candidates)} candidates from {result.universe_count} tickers")
    print(f"  Saved to: {out_path}")
    print("=" * 70)
    print()
    print("Funnel:")
    s = result.stats
    print(f"  Input:                          {s.input}")
    print(f"  No expiration in DTE window:    -{s.no_expiration_in_dte}")
    print(f"  Earnings in window:             -{s.has_earnings_in_window}")
    print(f"  Empty chain:                    -{s.chain_empty}")
    print(f"  No short strike (no greeks):    -{s.no_short_strike}")
    print(f"  Short strike too far from 20d:  -{s.short_strike_too_far_from_target}")
    print(f"  Invalid short put pricing:      -{s.short_mid_invalid}")
    print(f"  Bid-ask too wide:               -{s.bid_ask_too_wide}")
    print(f"  Low open interest:              -{s.low_open_interest}")
    print(f"  No matching long strike:        -{s.no_long_strike}")
    print(f"  Invalid long put pricing:       -{s.long_mid_invalid}")
    print(f"  No ATM strike:                  -{s.no_atm_strike}")
    print(f"  ATM IV too low:                 -{s.atm_iv_too_low}")
    print(f"  API errors:                     -{s.api_error}")
    print(f"  PASSED:                         {s.passed}")
    print()

    if not result.candidates:
        print("No candidates passed all filters. Consider loosening thresholds.")
        return 0

    n = min(args.top, len(result.candidates))
    print(f"Top {n} candidates by ATM IV:")
    print(
        f"  {'Symbol':<7} {'Type':<4} {'Px':>8} {'DTE':>4} "
        f"{'Short':>7} {'Long':>7} {'Δ':>6} {'Credit':>7} "
        f"{'MaxLoss':>8} {'RoR':>6} {'ATM IV':>7}"
    )
    print("  " + "-" * 90)
    for c in result.candidates[:n]:
        type_str = "ETF" if c.is_etf else "STK"
        print(
            f"  {c.symbol:<7} {type_str:<4} {c.last_price:>8.2f} {c.dte:>4} "
            f"{c.short_put_strike:>7.1f} {c.long_put_strike:>7.1f} "
            f"{c.short_put_delta:>6.2f} ${c.spread_credit_mid:>5.2f} "
            f"${c.spread_max_loss:>7.0f} {c.spread_return_on_risk*100:>5.1f}% "
            f"{c.atm_iv*100:>6.1f}%"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
