"""
T7 — Orchestrator for the trend-following bot.

The trend bot's cycle is simpler than the options bot's prep/open/manage: it has
ONE job, rebalance, which runs once per trading day. Each run:

    fetch signals (T3) → build target (T4) → size + cap (T5)
    → diff vs current and generate orders (T6) → place or preview them

It reuses core for everything generic: market calendar, trading-mode guardrails,
trade journal, Discord notifications, account-state kill-switch input.

Why once a day, not every 30 min: 12-month momentum changes slowly, so the
target portfolio barely moves intraday. A daily rebalance (after the open
settles) is the standard cadence and keeps turnover/costs low. The deadband in
T6 means most days only a few instruments actually trade.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from core import (
    AccountState,
    DiscordNotifier,
    EquitySide,
    OrderType,
    TradeJournal,
    TradierClient,
    TradierError,
    TradingMode,
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

from .portfolio import PortfolioConfig, TrendPortfolioManager
from .risk import RiskConfig, TrendRiskManager
from .signals import SignalConfig, SignalGenerator
from .strategy import StrategyConfig, TrendStrategy
from .universe import get_symbols

logger = logging.getLogger(__name__)


@dataclass
class TrendConfig:
    mode: TradingMode = TradingMode.PREVIEW_ONLY
    rebalance_hour: int = 10          # 10:30 ET after the open settles
    rebalance_minute: int = 30
    enable_rebalance_job: bool = True
    # Backstop: never place more than this many orders in one rebalance.
    max_orders_per_rebalance: int = 60


@dataclass
class JobResult:
    job_name: str
    timestamp: str
    mode: str
    success: bool
    summary: str
    details: dict = field(default_factory=dict)
    error: Optional[str] = None


class TrendOrchestrator:
    def __init__(
        self,
        config: TrendConfig,
        tradier: TradierClient,
        project_root: Path,
        notifier: Optional[DiscordNotifier] = None,
        signal_config: Optional[SignalConfig] = None,
        strategy_config: Optional[StrategyConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        portfolio_config: Optional[PortfolioConfig] = None,
    ):
        self.config = config
        self.tradier = tradier
        self.project_root = project_root
        self.notifier = notifier or DiscordNotifier(webhook_url=None)
        self.signals = SignalGenerator(signal_config or SignalConfig(), tradier)
        self.strategy = TrendStrategy(strategy_config or StrategyConfig())
        self.risk = TrendRiskManager(risk_config or RiskConfig())
        self.portfolio = TrendPortfolioManager(portfolio_config or PortfolioConfig(), tradier)
        self.journal = TradeJournal(project_root / "data" / "journal" / "trend")

        # Enforce safety guardrails immediately.
        validate_mode_against_broker(config.mode, tradier.config.sandbox)

    def _place_or_preview(self, symbol: str, side: EquitySide, qty: int) -> dict:
        preview = not places_real_orders(self.config.mode)
        return self.tradier.place_equity_order(
            symbol=symbol, side=side, quantity=qty,
            order_type=OrderType.MARKET, preview=preview, tag=f"trend-{symbol}",
        )

    def rebalance_job(self) -> JobResult:
        ts = datetime.now(timezone.utc).isoformat()
        mode = self.config.mode.value
        logger.info("=== REBALANCE JOB START (mode=%s) ===", mode)

        try:
            account_value = self.tradier.get_account_value()

            # T3 → T4 → T5
            symbols = get_symbols()
            signals = self.signals.generate(symbols)
            target = self.strategy.build_target(signals)
            last_prices = {s.symbol: s.last_price for s in signals.values() if s.last_price > 0}

            # In SIM mode, size against the sim book's equity, and diff against
            # its holdings rather than the broker's.
            sim = None
            current_override = None
            unpriced = []
            if is_sim(self.config.mode):
                sim = load_sim(self.project_root, "trend", initial_cash=account_value)
                # Trend's basket is fixed, so last_prices normally covers every
                # held name already. Backfill anyway: if a history fetch fails
                # for one ETF, an exit order on it would otherwise be silently
                # skipped and the position would mark at cost forever.
                last_prices, unpriced = resolve_prices(
                    self.tradier, last_prices, sim.signed_shares().keys())
                account_value = sim.total_equity(last_prices)
                current_override = sim.signed_shares()

            # Kill-switch input: each bot keeps its OWN daily-P&L state file, and
            # in SIM it must track the SIMULATED equity (computed just above), not
            # the broker account — otherwise the kill switch watches the wrong
            # account and never fires.
            state_path = self.project_root / "data" / "state" / "trend_account_state.json"
            account_state = AccountState.load_or_init(state_path, current_equity=account_value)

            risk_result = self.risk.size(
                target, account_value, last_prices,
                today_pnl_pct=account_state.day_pnl_pct(),
            )

            if risk_result.kill_switch_active:
                self.journal.record("kill_switch", reason=risk_result.kill_switch_reason, mode=mode)
                msg = f"Kill switch — {risk_result.kill_switch_reason}"
                plan = self.portfolio.build_rebalance_plan({}, current_override=current_override)
            else:
                plan = self.portfolio.build_rebalance_plan(
                    risk_result.targets, current_override=current_override)
                msg = ""

            # T6 → execute: SIM applies fills to the sim book; other modes
            # place/preview against the broker.
            orders = plan.orders[: self.config.max_orders_per_rebalance]
            placed, failed = [], []

            if is_sim(self.config.mode):
                fills = apply_orders_to_sim(sim, orders, last_prices)
                placed = fills
                snap = finalize_sim(sim, self.project_root, "trend", last_prices,
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
                               "qty": o.quantity, "reason": o.reason,
                               "status": resp.get("status")}
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
                msg = (f"{verb} {len(placed)} rebalance orders "
                       f"({len(failed)} failed); target {len(risk_result.targets)} "
                       f"positions, gross {risk_result.gross_exposure*100:.0f}% "
                       f"net {risk_result.net_exposure*100:.0f}%")
            self.journal.record_job("rebalance_job", mode, True, msg)
            logger.info("=== REBALANCE JOB DONE: %s ===", msg)
            result = JobResult("rebalance_job", ts, mode, True, msg, details={
                "placed": placed, "failed": failed,
                "target_positions": len(risk_result.targets),
                "gross_exposure": risk_result.gross_exposure,
                "net_exposure": risk_result.net_exposure,
                "account_value": account_value,
            })
            self.notifier.notify_job_result(result)
            return result

        except Exception as e:
            logger.exception("Rebalance job crashed")
            self.journal.record_job("rebalance_job", mode, False, f"error: {e}")
            return JobResult("rebalance_job", ts, mode, False,
                             f"Rebalance error: {e}", error=str(e))

    # ─── Scheduling ────────────────────────────────────────────────────────────

    def run_rebalance_guarded(self) -> JobResult:
        if not is_trading_day(now_eastern().date()):
            logger.info("Skipping rebalance: %s", describe_market_state())
            return JobResult("rebalance_job", datetime.now(timezone.utc).isoformat(),
                             self.config.mode.value, True, "Skipped — not a trading day")
        try:
            clock = self.tradier.get_clock()
            if clock.get("state") not in ("open", "premarket"):
                logger.info("Skipping rebalance: market state '%s'", clock.get("state"))
                return JobResult("rebalance_job", datetime.now(timezone.utc).isoformat(),
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
                CronTrigger(day_of_week="mon-fri",
                            hour=self.config.rebalance_hour,
                            minute=self.config.rebalance_minute, timezone=EASTERN),
                id="rebalance_job", name="Daily rebalance", misfire_grace_time=3600,
            )
            logger.info("Scheduled rebalance at %02d:%02d ET, Mon-Fri",
                        self.config.rebalance_hour, self.config.rebalance_minute)
        logger.info("Trend bot starting in %s mode. %s",
                    self.config.mode.value.upper(), describe_market_state())
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Trend bot shutting down.")
            scheduler.shutdown(wait=False)
