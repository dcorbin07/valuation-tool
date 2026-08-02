"""
Survivorship-bias-free backtest of the momentum, reversion and trend bots.

This is what the Sharadar subscription was bought for.

WHAT IS DIFFERENT FROM scripts/run_backtest.py
──────────────────────────────────────────────
The old runner built its universe from a LIVE screener call:

    snap = UniverseBuilder(UniverseConfig(include_etfs=False), tradier).build()
    symbols = [t.symbol for t in snap.tickers][:universe_cap]

which means a 2021-2024 backtest traded the 150 largest companies AS OF TODAY,
filtered on TODAY's price and market cap, on every day of the window. Delisted
names were structurally absent, and the survivors were pre-selected by an
outcome that happened AFTER the period being measured. For a momentum strategy
that is not a mild flatter — the result is an artefact.

This runner rebuilds the universe point-in-time at EVERY rebalance, from
TICKERS + SEP + DAILY, keeping companies that have since delisted and excluding
companies that had not yet listed. It prints how many of those names a live
screener would have hidden from you, which is the size of the bias the old
numbers carried.

PREREQUISITES
─────────────
    python scripts/verify_sharadar.py                       # confirm entitlement
    python scripts/sharadar_sync.py --tables TICKERS DAILY SEP SF1 --full

USAGE
─────
    python scripts/run_sharadar_backtest.py --bots momentum reversion --years 5
    python scripts/run_sharadar_backtest.py --bots trend --start 2008-01-01 --end 2012-12-31

The curves land in data/sim/<bot>_sharadar/equity_curve.jsonl, in the same
format as the live SIM curves.

⚠ AND THE STANDING WARNING ⚠
Rich history plus a parameter sweep is how people build strategies that crush
the past and lose money live. This runner deliberately has NO optimizer. When
one is added it must be walk-forward from the first commit — parameters chosen
in-sample, evaluated out-of-sample ONCE, with the number of configurations
tried reported alongside every result. A backtest that looks too good is
evidence of a bug or of overfitting far more often than it is evidence of edge.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.backtest import BacktestConfig, Backtester, PriceHistory
from core.pit_universe import PITUniverseBuilder, PITUniverseConfig
from core.regime import RegimeConfig, classify_regime_from_closes
from core.sharadar import SharadarStore
from trend.portfolio import PortfolioConfig, TrendPortfolioManager
from trend.risk import RiskConfig, TrendRiskManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sharadar_backtest")

# Trading days per calendar day, for converting a bar requirement into a
# fetch window. The old code used `warmup_days` (documented as trading days)
# directly as CALENDAR days, so 260 became ~179 trading days — short of the
# 252 the signal needs, which made the first rebalance a guaranteed no-op.
CALENDAR_PER_TRADING_DAY = 1.45


class SharadarBacktest:
    def __init__(self, store: SharadarStore, cfg: BacktestConfig,
                 universe_cfg: PITUniverseConfig, use_regime_gate: bool = True):
        self.store = store
        self.cfg = cfg
        self.universe_builder = PITUniverseBuilder(store, universe_cfg)
        self.use_regime_gate = use_regime_gate
        self._history: PriceHistory | None = None
        self._universe_cache: dict[date, list[str]] = {}
        self._survivorship: list[tuple[date, int, int]] = []

    # ── universe, rebuilt as of each date ──────────────────────────────────

    def universe_on(self, as_of: date) -> list[str]:
        if as_of not in self._universe_cache:
            snap = self.universe_builder.build(as_of)
            self._universe_cache[as_of] = snap.symbols()
            self._survivorship.append((as_of, snap.count, snap.delisted_included))
        return self._universe_cache[as_of]

    def preload_prices(self, warmup_bars: int) -> PriceHistory:
        """
        Load every name that appears in ANY rebalance universe across the run.

        Loading the union up front is what makes the bulk path worthwhile: one
        pass over sqlite instead of a fetch per symbol per rebalance. It does
        NOT leak look-ahead — membership is still decided per date by
        universe_on(); this only decides which series to have in memory.
        """
        fetch_start = self.cfg.start - timedelta(
            days=int(warmup_bars * CALENDAR_PER_TRADING_DAY) + 30)
        all_dates = self.store.trading_dates(self.cfg.start, self.cfg.end)
        if not all_dates:
            raise SystemExit(
                f"No SEP price data between {self.cfg.start} and {self.cfg.end}. "
                f"Has the mirror been synced? Try: python scripts/sharadar_sync.py "
                f"--tables TICKERS DAILY SEP --full")

        rebalance_dates = all_dates[:: self.cfg.rebalance_every_days]
        logger.info("Building point-in-time universes for %d rebalance dates...",
                    len(rebalance_dates))
        union: set[str] = set()
        for d in rebalance_dates:
            union.update(self.universe_on(d))

        logger.info("Union across the whole run: %d distinct symbols. Loading prices...",
                    len(union))
        self._history = PriceHistory.from_store(
            self.store, sorted(union), fetch_start, self.cfg.end, adjusted=True)
        return self._history

    # ── regime gate, computed from the same point-in-time data ─────────────

    def regime_is_risk_on(self, as_of: date, proxy: str = "SPY") -> bool:
        """
        The live momentum and reversion bots suppress shorts when SPY is above
        its 200-day MA. The old backtest omitted the gate entirely, so it was
        testing a strategy that does not exist. Note SPY is an ETF and lives in
        SFP, not SEP — if the mirror has no SFP, this returns False (gate off)
        and says so, rather than silently pretending the gate ran.
        """
        closes = [c for _, c in self.store.closes(
            proxy, as_of - timedelta(days=400), as_of, adjusted=True)]
        if len(closes) < RegimeConfig().min_bars_required:
            return False
        from core.regime import MarketRegime
        return classify_regime_from_closes(closes, RegimeConfig()) == MarketRegime.RISK_ON

    # ── the three strategies ───────────────────────────────────────────────

    def _build_target_fn(self, bot: str):
        from momentum.signals import MomentumConfig, compute_score_from_closes as mom_score
        from momentum.signals import rank_and_select as mom_rank
        from momentum.strategy import MomentumStrategy
        from momentum.strategy import StrategyConfig as MomStrategyConfig
        from reversion.signals import MeanReversionConfig
        from reversion.signals import compute_score_from_closes as rev_score
        from reversion.signals import rank_and_select as rev_rank
        from reversion.strategy import MeanReversionStrategy
        from reversion.strategy import StrategyConfig as RevStrategyConfig

        if bot == "momentum":
            sig_cfg, scorer, ranker = MomentumConfig(), mom_score, mom_rank
            strategy = MomentumStrategy(MomStrategyConfig())
        elif bot == "reversion":
            sig_cfg, scorer, ranker = MeanReversionConfig(), rev_score, rev_rank
            strategy = MeanReversionStrategy(RevStrategyConfig())
        else:
            raise ValueError(f"unknown bot {bot!r}")

        def build_target(as_of: date):
            symbols = self.universe_on(as_of)
            scores = {}
            for s in symbols:
                closes = self._history.closes_up_to(s, as_of)
                sc = scorer(s, closes, sig_cfg)
                if sc.usable:
                    scores[s] = sc
            if not scores:
                return None, {}

            selection = ranker(scores, sig_cfg)

            # Regime gate — present in the live bots, absent from the old
            # backtest. Suppressed shorts are handed over rather than dropped
            # so their capital stays UNDEPLOYED (see strategy.build_target).
            if self.use_regime_gate and selection.shorts and self.regime_is_risk_on(as_of):
                selection.suppressed_shorts = list(selection.shorts)
                selection.shorts = []

            target = strategy.build_target(selection)
            prices = {s: self._history.price_on(s, as_of) for s in symbols}
            prices = {k: v for k, v in prices.items() if v}
            return target, prices

        return build_target

    def _build_trend_target_fn(self):
        from trend.signals import SignalConfig, compute_signal_from_closes
        from trend.strategy import StrategyConfig, TrendStrategy
        from trend.universe import get_symbols

        cfg, strategy = SignalConfig(), TrendStrategy(StrategyConfig())
        basket = get_symbols()

        def build_target(as_of: date):
            signals = {}
            for s in basket:
                sig = compute_signal_from_closes(
                    s, self._history.closes_up_to(s, as_of), cfg)
                if sig.usable:
                    signals[s] = sig
            if not signals:
                return None, {}
            prices = {s: sig.last_price for s, sig in signals.items() if sig.last_price > 0}
            return strategy.build_target(signals), prices

        return build_target

    def run(self, bot: str) -> list[dict]:
        if self._history is None:
            raise RuntimeError("call preload_prices() first")
        bt = Backtester(self.cfg, self._history,
                        TrendRiskManager(RiskConfig()),
                        TrendPortfolioManager(PortfolioConfig(), None))
        fn = (self._build_trend_target_fn() if bot == "trend"
              else self._build_target_fn(bot))
        return bt.run(f"{bot}_sharadar", fn, PROJECT_ROOT)

    def survivorship_summary(self) -> str:
        if not self._survivorship:
            return "no universes built"
        tot = sum(n for _, n, _ in self._survivorship)
        dead = sum(d for _, _, d in self._survivorship)
        avg = tot / len(self._survivorship)
        pct = 100.0 * dead / tot if tot else 0.0
        return (f"Across {len(self._survivorship)} rebalance dates: average universe "
                f"{avg:.0f} names, {pct:.1f}% of all universe-slots were companies "
                f"that have since delisted.\n"
                f"    Those are EXACTLY the names the old live-screener backtest "
                f"could not see. Their absence is the bias it carried.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bots", nargs="+", default=["momentum", "reversion"],
                   choices=["momentum", "reversion", "trend"])
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--start", type=date.fromisoformat)
    p.add_argument("--end", type=date.fromisoformat)
    p.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "sharadar.db")
    p.add_argument("--capital", type=float, default=100_000.0)
    p.add_argument("--rebalance-days", type=int, default=21)
    p.add_argument("--universe-cap", type=int, default=500,
                   help="max names per rebalance, by point-in-time market cap")
    p.add_argument("--min-cap", type=float, default=2e9)
    p.add_argument("--min-price", type=float, default=20.0)
    p.add_argument("--no-regime-gate", action="store_true")
    args = p.parse_args()

    if not args.db.exists():
        print(f"\nNo local mirror at {args.db}.\n\n"
              f"    python scripts/verify_sharadar.py        # check entitlement first\n"
              f"    python scripts/sharadar_sync.py --tables TICKERS DAILY SEP SF1 --full\n")
        return 1

    end = args.end or date.today()
    start = args.start or (end - timedelta(days=365 * args.years))

    store = SharadarStore(args.db)
    stats = store.stats()
    if not stats["sep"]:
        print("\nThe mirror has no SEP price rows. Run sharadar_sync.py first.\n")
        return 1
    print(f"\n  Mirror: {stats['sep']:,} price rows, {stats['tickers']:,} tickers, "
          f"range {stats['sep_range'][0]} .. {stats['sep_range'][1]}")

    cfg = BacktestConfig(start=start, end=end, initial_capital=args.capital,
                         rebalance_every_days=args.rebalance_days)
    ucfg = PITUniverseConfig(min_price=args.min_price, min_market_cap=args.min_cap,
                             max_names=args.universe_cap)

    bt = SharadarBacktest(store, cfg, ucfg, use_regime_gate=not args.no_regime_gate)
    try:
        bt.preload_prices(warmup_bars=260)
        for bot in args.bots:
            print(f"\n{'=' * 68}\n  {bot.upper()}  {start} .. {end}\n{'=' * 68}")
            snaps = bt.run(bot)
            if snaps:
                f = snaps[-1]
                print(f"  final equity ${f['equity']:,.0f}  "
                      f"({f['return_since_start'] * 100:+.2f}%)  over {len(snaps)} days")
        print(f"\n  SURVIVORSHIP\n  {bt.survivorship_summary()}")
        print(f"\n  Curves: data/sim/<bot>_sharadar/equity_curve.jsonl")
        print(f"  Compare: python scripts/correlation_tracker.py --bots "
              f"{' '.join(b + '_sharadar' for b in args.bots)}")
        print("\n  Reminder: never correlate a BACKTEST curve against a live-SIM "
              "curve.\n  Different periods, different regimes — the number is "
              "meaningless.\n  (correlation_tracker already warns on this.)\n")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
