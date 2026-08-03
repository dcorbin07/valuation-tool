"""
Orchestrator for the mean-reversion bot (Bot #4).

Structurally identical to the momentum bot's orchestrator — one daily rebalance
job, same guardrails, same journal/notifier/kill-switch, same SIM wiring, and it
REUSES the trend bot's risk + portfolio machinery wholesale (they operate on
generic target weights). The only differences from momentum:
  - It uses the short-horizon mean-reversion signal (z-score reversal) instead
    of cross-sectional momentum.
  - Cadence: mean-reversion is a short-horizon strategy, so it's run daily and
    genuinely turns over more often than momentum (the signal changes faster).

Risk note carried over from signals.py: mean-reversion has a high win rate but a
left tail. Risk is controlled by BREADTH (many small names) and the shared risk
layer's vol-targeting + per-name caps — NOT by tight stops, which the evidence
shows hurt mean-reversion. The kill switch still provides a hard floor.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core import (
    AccountState,
    DiscordNotifier,
    EquitySide,
    MarketRegime,
    OrderType,
    RegimeConfig,
    RegimeFilter,
    TradeJournal,
    TradierClient,
    TradierError,
    TradingMode,
    UniverseBuilder,
    UniverseConfig,
    apply_orders_to_sim,
    describe_market_state,
    finalize_sim,
    resolve_prices,
    is_sim,
    is_trading_day,
    load_sim,
    now_eastern,
    places_real_orders,
    validate_mode_against_broker,
)
from trend.risk import RiskConfig, TrendRiskManager
from trend.portfolio import PortfolioConfig, TrendPortfolioManager

from .signals import MeanReversionConfig, MeanReversionSignalGenerator
from .strategy import MeanReversionStrategy, StrategyConfig

logger = logging.getLogger(__name__)


@dataclass
class ReversionBotConfig:
    mode: TradingMode = TradingMode.PREVIEW_ONLY
    rebalance_hour: int = 11
    rebalance_minute: int = 0          # after trend (10:30) and momentum (10:45)
    enable_rebalance_job: bool = True
    max_orders_per_rebalance: int = 120
    max_universe_for_history: int = 400
    # Regime gate: suppress SHORTS in a broad-market uptrend (same rationale as
    # the momentum bot — shorting into a rising market is the worst case).
    use_regime_gate: bool = True


@dataclass
class JobResult:
    job_name: str
    timestamp: str
    mode: str
    success: bool
    summary: str
    details: dict = field(default_factory=dict)
    error: Optional[str] = None


class ReversionOrchestrator:
    def __init__(
        self,
        config: ReversionBotConfig,
        tradier: TradierClient,
        project_root: Path,
        notifier: Optional[DiscordNotifier] = None,
        reversion_config: Optional[MeanReversionConfig] = None,
        strategy_config: Optional[StrategyConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        portfolio_config: Optional[PortfolioConfig] = None,
    ):
        self.config = config
        self.tradier = tradier
        self.project_root = project_root
        self.notifier = notifier or DiscordNotifier(webhook_url=None)
        self.signals = MeanReversionSignalGenerator(
            reversion_config or MeanReversionConfig(), tradier)
        self.strategy = MeanReversionStrategy(strategy_config or StrategyConfig())
        self.risk = TrendRiskManager(risk_config or RiskConfig())
        self.portfolio = TrendPortfolioManager(portfolio_config or PortfolioConfig(), tradier)
        self.regime_filter = RegimeFilter(RegimeConfig(), tradier)
        self.journal = TradeJournal(project_root / "data" / "journal" / "reversion")
        validate_mode_against_broker(config.mode, tradier.config.sandbox)

    def _place_or_preview(self, symbol: str, side: EquitySide, qty: int) -> dict:
        preview = not places_real_orders(self.config.mode)
        return self.tradier.place_equity_order(
            symbol=symbol, side=side, quantity=qty,
            order_type=OrderType.MARKET, preview=preview, tag=f"rev-{symbol}",
        )

    def _build_universe_symbols(self) -> list[str]:
        builder = UniverseBuilder(UniverseConfig(include_etfs=False), self.tradier)
        snapshot = builder.build()
        symbols = [t.symbol for t in snapshot.tickers][: self.config.max_universe_for_history]
        logger.info("Reversion universe: %d stocks (capped from %d)",
                    len(symbols), snapshot.count)
        return symbols

    def rebalance_job(self) -> JobResult:
        ts = datetime.now(timezone.utc).isoformat()
        mode = self.config.mode.value
        logger.info("=== REVERSION REBALANCE START (mode=%s) ===", mode)

        try:
            account_value = self.tradier.get_account_value()

            symbols = self._build_universe_symbols()
            selection = self.signals.generate(symbols)

            regime_note = ""
            if self.config.use_regime_gate:
                regime = self.regime_filter.current_regime()
                if regime == MarketRegime.RISK_ON and selection.shorts:
                    dropped = len(selection.shorts)
                    # See MeanReversionStrategy.build_target: the suppressed
                    # shorts must stay visible so their share of the book is
                    # held back rather than re-normalized onto the longs.
                    selection.suppressed_shorts = list(selection.shorts)
                    selection.shorts = []
                    regime_note = f" [regime risk-on: suppressed {dropped} shorts]"
                    logger.info("Regime risk-on — suppressing %d shorts", dropped)

            target = self.strategy.build_target(selection)

            # Prices for the WHOLE scored universe, not just the selected names —
            # a held position that no longer qualifies still needs a price or its
            # exit order can't be filled in the sim book.
            last_prices = dict(selection.all_prices)
            for s in selection.longs + selection.shorts:
                last_prices[s.symbol] = s.last_price

            sim = None
            current_override = None
            unpriced = []
            if is_sim(self.config.mode):
                sim = load_sim(self.project_root, "reversion", initial_cash=account_value)
                # Backfill anything we hold but didn't score this cycle. Without a
                # price the exit is silently skipped and the position marks at cost.
                last_prices, unpriced = resolve_prices(
                    self.tradier, last_prices, sim.signed_shares().keys())
                account_value = sim.total_equity(last_prices)
                current_override = sim.signed_shares()

            # Per-bot kill-switch state; in SIM tracks the simulated equity.
            state_path = self.project_root / "data" / "state" / "reversion_account_state.json"
            account_state = AccountState.load_or_init(state_path, current_equity=account_value)

            risk_result = self.risk.size(
                target, account_value, last_prices,
                today_pnl_pct=account_state.day_pnl_pct(),
            )

            if risk_result.kill_switch_active:
                self.journal.record("kill_switch", reason=risk_result.kill_switch_reason, mode=mode)
                plan = self.portfolio.build_rebalance_plan({}, current_override=current_override)
                msg = f"Kill switch — {risk_result.kill_switch_reason}"
            else:
                plan = self.portfolio.build_rebalance_plan(
                    risk_result.targets, current_override=current_override)
                msg = ""

            orders = plan.orders[: self.config.max_orders_per_rebalance]
            placed, failed = [], []

            if is_sim(self.config.mode):
                fills = apply_orders_to_sim(sim, orders, last_prices)
                placed = fills
                snap = finalize_sim(sim, self.project_root, "reversion", last_prices,
                                    label="rebalance")
                for f in fills:
                    self.journal.record("sim_fill", mode=mode, **f)
                msg = (f"SIM: applied {len(fills)} fills; equity ${snap['equity']:,.0f} "
                       f"({snap['return_since_start']*100:+.2f}% since start), "
                       f"{snap['num_positions']} positions")
                # Never let an unfilled order pass silently — an unpriced EXIT
                # strands the position and freezes its P&L at cost.
                if len(fills) < len(orders):
                    skipped = len(orders) - len(fills)
                    msg += f" ⚠ {skipped} order(s) UNFILLED (no price)"
                    logger.warning("%d of %d sim orders went unfilled", skipped, len(orders))
                if unpriced:
                    msg += f" ⚠ {len(unpriced)} held name(s) unpriced: {unpriced[:5]}"

            else:
                for o in orders:
                    try:
                        resp = self._place_or_preview(o.symbol, o.side, o.quantity)
                        ok = resp.get("status") in ("ok", "open", "pending", "filled")
                        rec = {"symbol": o.symbol, "side": o.side.value,
                               "qty": o.quantity, "status": resp.get("status")}
                        (placed if ok else failed).append(rec)
                        if ok and places_real_orders(self.config.mode):
                            self.journal.record(
                                "rebalance_order", symbol=o.symbol, side=o.side.value,
                                quantity=o.quantity, reason=o.reason, mode=mode,
                                order_id=resp.get("id"), status=resp.get("status"),
                            )
                    except TradierError as e:
                        logger.warning("Order failed for %s: %s", o.symbol, e)
                        failed.append({"symbol": o.symbol, "error": str(e)})

            verb = "Placed" if places_real_orders(self.config.mode) else "Previewed"
            if not msg:
                msg = (f"{verb} {len(placed)} rebalance orders ({len(failed)} failed); "
                       f"target {len(risk_result.targets)} positions "
                       f"({target.long_count()}L/{target.short_count()}S), "
                       f"gross {risk_result.gross_exposure*100:.0f}% net {risk_result.net_exposure*100:.0f}%"
                       f"{regime_note}")
            self.journal.record_job("reversion_rebalance", mode, True, msg)
            logger.info("=== REVERSION REBALANCE DONE: %s ===", msg)
            result = JobResult("reversion_rebalance", ts, mode, True, msg, details={
                "placed": placed, "failed": failed,
                "target_positions": len(risk_result.targets),
                "gross_exposure": risk_result.gross_exposure,
                "net_exposure": risk_result.net_exposure,
                "account_value": account_value,
            })
            self.notifier.notify_job_result(result)
            return result

        except Exception as e:
            logger.exception("Reversion rebalance crashed")
            self.journal.record_job("reversion_rebalance", mode, False, f"error: {e}")
            return JobResult("reversion_rebalance", ts, mode, False,
                             f"Rebalance error: {e}", error=str(e))

    def run_rebalance_guarded(self) -> JobResult:
        if not is_trading_day(now_eastern().date()):
            logger.info("Skipping reversion rebalance: %s", describe_market_state())
            return JobResult("reversion_rebalance", datetime.now(timezone.utc).isoformat(),
                             self.config.mode.value, True, "Skipped — not a trading day")
        try:
            clock = self.tradier.get_clock()
            if clock.get("state") not in ("open", "premarket"):
                return JobResult("reversion_rebalance", datetime.now(timezone.utc).isoformat(),
                                 self.config.mode.value, True, "Skipped — market closed")
        except Exception as e:
            logger.warning("Clock check failed (%s); proceeding on local calendar.", e)
        return self.rebalance_job()

    def start(self) -> None:
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            raise SystemExit("apscheduler not installed. Run: pip install apscheduler")
        from core.calendar import EASTERN
        scheduler = BlockingScheduler(timezone=EASTERN)
        if self.config.enable_rebalance_job:
            scheduler.add_job(
                self.run_rebalance_guarded,
                CronTrigger(day_of_week="mon-fri", hour=self.config.rebalance_hour,
                            minute=self.config.rebalance_minute, timezone=EASTERN),
                id="reversion_rebalance", name="Daily reversion rebalance",
                misfire_grace_time=3600,
            )
            logger.info("Scheduled reversion rebalance at %02d:%02d ET, Mon-Fri",
                        self.config.rebalance_hour, self.config.rebalance_minute)
        logger.info("Reversion bot starting in %s mode. %s",
                    self.config.mode.value.upper(), describe_market_state())
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Reversion bot shutting down.")
            scheduler.shutdown(wait=False)
