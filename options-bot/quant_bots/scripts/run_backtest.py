#!/usr/bin/env python3
"""
Run historical backtests for the trend and/or momentum bots.

Replays the REAL strategy pipelines against Tradier daily history and writes
equity curves in the same format as live SIM, so correlation_tracker.py works
on them directly (it reads data/sim/<name>/...; backtests write to
<name>_backtest/).

Usage (on your machine, where the Tradier connection works):
    python scripts/run_backtest.py --bots trend momentum --years 3
    python scripts/run_backtest.py --bots trend --start 2022-01-01 --end 2024-12-31

Then:
    python scripts/correlation_tracker.py --bots trend_backtest momentum_backtest

Notes:
  - Uses your existing TRADIER_TOKEN (sandbox is fine — history is the same).
  - The momentum backtest pulls a stock universe first; --universe-cap bounds
    how many names to fetch history for (default 150 to keep it quick).
  - Fills assumed at the daily close. Survivorship bias applies to the momentum
    stock universe (it's today's universe). Good for correlation estimation.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import TradierClient, TradierConfig
from core.backtest import Backtester, BacktestConfig, PriceHistory


def _tradier() -> TradierClient:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    token = os.environ.get("TRADIER_TOKEN") or os.environ.get("TREND_TRADIER_TOKEN")
    account = os.environ.get("TRADIER_ACCOUNT_ID") or os.environ.get("TREND_TRADIER_ACCOUNT_ID")
    if not token or not account:
        sys.exit("Need TRADIER_TOKEN + TRADIER_ACCOUNT_ID in .env for history.")
    sandbox = os.environ.get("TRADIER_SANDBOX", "true").lower() != "false"
    return TradierClient(TradierConfig(access_token=token, account_id=account, sandbox=sandbox))


def backtest_trend(tradier, cfg: BacktestConfig):
    from trend.universe import get_symbols
    from trend.signals import SignalConfig, compute_signal_from_closes
    from trend.strategy import StrategyConfig, TrendStrategy
    from trend.risk import RiskConfig, TrendRiskManager
    from trend.portfolio import PortfolioConfig, TrendPortfolioManager

    symbols = get_symbols()
    history = PriceHistory(tradier)
    fetch_start = cfg.start - timedelta(days=cfg.warmup_days + 100)
    logger.info("Trend: fetching history for %d ETFs...", len(symbols))
    history.fetch(symbols, fetch_start, cfg.end)

    sig_cfg = SignalConfig()
    strat = TrendStrategy(StrategyConfig())

    def build_target(as_of):
        signals = {}
        for sym in history.symbols():
            closes = history.closes_up_to(sym, as_of)
            signals[sym] = compute_signal_from_closes(sym, closes, sig_cfg)
        target = strat.build_target(signals)
        last_prices = {s.symbol: s.last_price for s in signals.values() if s.last_price > 0}
        return target, last_prices

    bt = Backtester(cfg, history, TrendRiskManager(RiskConfig()),
                    TrendPortfolioManager(PortfolioConfig(), tradier))
    return bt.run("trend", build_target, PROJECT_ROOT)


def backtest_momentum(tradier, cfg: BacktestConfig, universe_cap: int):
    from core import UniverseBuilder, UniverseConfig
    from momentum.signals import MomentumConfig, compute_score_from_closes, rank_and_select
    from momentum.strategy import StrategyConfig as MomStratConfig, MomentumStrategy
    from trend.risk import RiskConfig, TrendRiskManager
    from trend.portfolio import PortfolioConfig, TrendPortfolioManager

    logger.info("Momentum: building stock universe...")
    snap = UniverseBuilder(UniverseConfig(include_etfs=False), tradier).build()
    symbols = [t.symbol for t in snap.tickers][:universe_cap]
    history = PriceHistory(tradier)
    fetch_start = cfg.start - timedelta(days=cfg.warmup_days + 100)
    logger.info("Momentum: fetching history for %d stocks...", len(symbols))
    history.fetch(symbols, fetch_start, cfg.end)

    mom_cfg = MomentumConfig()
    strat = MomentumStrategy(MomStratConfig())

    def build_target(as_of):
        scores = {}
        for sym in history.symbols():
            closes = history.closes_up_to(sym, as_of)
            sc = compute_score_from_closes(sym, closes, mom_cfg)
            if sc.usable:
                scores[sym] = sc
        selection = rank_and_select(scores, mom_cfg)
        target = strat.build_target(selection)
        last_prices = {s.symbol: s.last_price for s in selection.longs + selection.shorts}
        return target, last_prices

    bt = Backtester(cfg, history, TrendRiskManager(RiskConfig()),
                    TrendPortfolioManager(PortfolioConfig(), tradier))
    return bt.run("momentum", build_target, PROJECT_ROOT)


def backtest_reversion(tradier, cfg: BacktestConfig, universe_cap: int):
    """
    Backtest the mean-reversion bot.

    C3: `--bots reversion` used to be accepted, run NOTHING, and print
    "Backtests complete." A flag that takes an argument, does nothing, and
    reports success is worse than an unimplemented flag, because it produces a
    clean-looking result a reader will take as evidence. One of four live
    strategies had therefore never been backtested at all.

    The audit costed this at "M to implement". It is not: the reversion module
    exposes exactly the same three entry points as momentum —
    `compute_score_from_closes(sym, closes, cfg)`, `rank_and_select(scores,
    cfg)`, `strategy.build_target(selection)` — so this is the momentum path
    with three imports changed.

    One deliberate difference from `backtest_momentum`: the price map is built
    from `selection.all_prices` (every scored name) rather than from
    `selection.longs + selection.shorts`. `all_prices` exists precisely because
    the selection-only map is what silently dropped exit orders for names that
    had fallen out of the book — see FIXES.md #1. The backtester's `mark_prices`
    union already covers that case, so this is belt-and-braces rather than a
    fix, but there is no reason for new code to use the shape that caused the
    bug.
    """
    from core import UniverseBuilder, UniverseConfig
    from reversion.signals import (MeanReversionConfig, compute_score_from_closes,
                                   rank_and_select)
    from reversion.strategy import StrategyConfig as RevStratConfig, MeanReversionStrategy
    from trend.risk import RiskConfig, TrendRiskManager
    from trend.portfolio import PortfolioConfig, TrendPortfolioManager

    logger.info("Reversion: building stock universe...")
    snap = UniverseBuilder(UniverseConfig(include_etfs=False), tradier).build()
    symbols = [t.symbol for t in snap.tickers][:universe_cap]
    history = PriceHistory(tradier)
    fetch_start = cfg.start - timedelta(days=cfg.warmup_days + 100)
    logger.info("Reversion: fetching history for %d stocks...", len(symbols))
    history.fetch(symbols, fetch_start, cfg.end)

    rev_cfg = MeanReversionConfig()
    strat = MeanReversionStrategy(RevStratConfig())

    def build_target(as_of):
        scores = {}
        for sym in history.symbols():
            closes = history.closes_up_to(sym, as_of)
            sc = compute_score_from_closes(sym, closes, rev_cfg)
            if sc.usable:
                scores[sym] = sc
        selection = rank_and_select(scores, rev_cfg)
        target = strat.build_target(selection)
        return target, dict(selection.all_prices)

    bt = Backtester(cfg, history, TrendRiskManager(RiskConfig()),
                    TrendPortfolioManager(PortfolioConfig(), tradier))
    return bt.run("reversion", build_target, PROJECT_ROOT)


# Every bot this script can actually backtest. A name absent from this map is
# rejected at argument-parse time rather than skipped in silence.
BACKTESTS = {
    "trend": lambda tradier, cfg, cap: backtest_trend(tradier, cfg),
    "momentum": backtest_momentum,
    "reversion": backtest_reversion,
}

# Bots that exist in this repository but that this script cannot backtest, with
# the reason. Naming them explicitly is the difference between "unsupported,
# here is why" and "accepted, ran nothing, reported success".
UNSUPPORTED = {
    "options": ("the options bot trades option chains, and this script's "
                "PriceHistory is an equity-close feed with no chain, no implied "
                "vol and no expirations. Its backtest lives in "
                "options_backtest/run_options_backtest.py instead."),
}


def main() -> int:
    p = argparse.ArgumentParser(description="Backtest the trend/momentum/reversion bots.")
    p.add_argument("--bots", nargs="+", default=["trend", "momentum"])
    p.add_argument("--years", type=float, default=3.0, help="Lookback window in years.")
    p.add_argument("--start", type=str, default=None)
    p.add_argument("--end", type=str, default=None)
    p.add_argument("--universe-cap", type=int, default=150,
                   help="Max stocks for the momentum backtest (history calls).")
    p.add_argument("--rebalance-days", type=int, default=21)
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # C3: reject anything we cannot actually run, BEFORE fetching anything.
    # Previously an unrecognised --bots value fell through both `if` statements
    # and the script printed "Backtests complete."
    for bot in args.bots:
        if bot in UNSUPPORTED:
            sys.exit(f"--bots {bot}: not supported here — {UNSUPPORTED[bot]}")
        if bot not in BACKTESTS:
            sys.exit(f"--bots {bot}: unknown bot. Known: "
                     f"{', '.join(sorted(BACKTESTS))}.")

    end = date.fromisoformat(args.end) if args.end else date.today()
    start = date.fromisoformat(args.start) if args.start else \
        end - timedelta(days=int(args.years * 365))
    cfg = BacktestConfig(start=start, end=end, rebalance_every_days=args.rebalance_days)

    # Both bots are backtested over this SINGLE shared window/config, so their
    # equity curves cover identical dates — a prerequisite for a valid
    # correlation between them. Never backtest the two bots over different
    # windows and then correlate them.
    logger.info("=" * 60)
    logger.info("SHARED BACKTEST WINDOW: %s → %s (both bots, identical dates)", start, end)
    logger.info("=" * 60)
    tradier = _tradier()
    ran = []
    with tradier:
        for bot in args.bots:
            BACKTESTS[bot](tradier, cfg, args.universe_cap)
            ran.append(bot)

    # Say what actually ran. "Backtests complete" with no subject was how the
    # reversion no-op read as success for as long as it existed.
    print(f"\nBacktests complete for: {', '.join(ran)}. "
          f"See equity curves under data/sim/*_backtest/.")
    print("Compare them:")
    print("  python scripts/correlation_tracker.py --bots "
          + " ".join(f"{b}_backtest" for b in ran))
    return 0


logger = logging.getLogger("run_backtest")

if __name__ == "__main__":
    sys.exit(main())
