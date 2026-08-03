"""
The orchestrator's two core jobs.

  open_job:    Run the morning pipeline — load candidates, build orders, risk-
               check, then place (or preview) the accepted opening orders.
  manage_job:  Sync the portfolio, decide exits, then place (or preview) any
               closing orders.

Both jobs are mode-aware via OrchestratorConfig:
  - PREVIEW_ONLY: orders go through place_multileg_order(preview=True)
  - PAPER / LIVE: orders go through place_multileg_order(preview=False)

Both jobs are defensive: any exception in a single order is logged and the job
continues with the rest. A job should never crash the scheduler.

Both jobs return a JobResult with structured outcomes for the notifier (V9) and
for logging/audit.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from broker import (
    OptionLeg,
    OrderSide,
    OrderType,
    TradierClient,
    TradierError,
    parse_occ_symbol,
)
from data import EarningsCalendar, UniverseBuilder, UniverseConfig
from portfolio import (
    ExitDecision,
    PortfolioConfig,
    PortfolioManager,
    fingerprints_from_positions,
    price_credit_spread,
)
from risk import AccountState, RiskConfig, RiskManager
from screener import ScreenedCandidate, Screener, ScreenerConfig
from strategy import PutCreditSpreadStrategy, StrategyConfig, make_fingerprint

from .config import OrchestratorConfig, TradingMode
from .journal import TradeJournal

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    job_name: str
    timestamp: str
    mode: str
    success: bool
    summary: str
    details: dict = field(default_factory=dict)
    error: Optional[str] = None


def _load_candidates(path: Path) -> list[ScreenedCandidate]:
    payload = json.loads(path.read_text())
    out = []
    for d in payload["candidates"]:
        out.append(ScreenedCandidate(
            symbol=d["symbol"], last_price=d["last_price"], is_etf=d["is_etf"],
            target_expiration=date.fromisoformat(d["target_expiration"]),
            dte=d["dte"],
            short_put_strike=d["short_put_strike"], short_put_delta=d["short_put_delta"],
            short_put_bid=d["short_put_bid"], short_put_ask=d["short_put_ask"],
            short_put_mid=d["short_put_mid"], short_put_iv=d["short_put_iv"],
            short_put_open_interest=d["short_put_open_interest"],
            long_put_strike=d["long_put_strike"],
            long_put_bid=d["long_put_bid"], long_put_ask=d["long_put_ask"],
            long_put_mid=d["long_put_mid"],
            spread_credit_mid=d["spread_credit_mid"],
            spread_max_loss=d["spread_max_loss"],
            spread_return_on_risk=d["spread_return_on_risk"],
            atm_iv=d["atm_iv"],
            next_earnings=(date.fromisoformat(d["next_earnings"]) if d.get("next_earnings") else None),
        ))
    return out


# NOTE: the old module-local _fingerprints_from_positions() lived here (and a
# verbatim copy lived in scripts/build_orders.py). It hard-coded widths of
# (5.0, 10.0) and emitted seven fingerprints per real spread. Both call sites
# now use portfolio.fingerprints_from_positions(positions, spread_width), which
# derives the width from StrategyConfig and emits one fingerprint per spread
# that is actually open. See that function for the full history.


class Jobs:
    """Holds the wiring and exposes open_job() / manage_job()."""

    def __init__(
        self,
        config: OrchestratorConfig,
        tradier: TradierClient,
        project_root: Path,
        strategy_config: Optional[StrategyConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        portfolio_config: Optional[PortfolioConfig] = None,
        advisor=None,
    ):
        self.config = config
        self.tradier = tradier
        self.project_root = project_root
        self.strategy = PutCreditSpreadStrategy(strategy_config or StrategyConfig())
        self.risk = RiskManager(risk_config or RiskConfig())
        self.portfolio = PortfolioManager(portfolio_config or PortfolioConfig(), tradier)
        # Optional LLM advisor (flag-and-log only; never blocks orders).
        self.advisor = advisor
        # Durable trade journal — the audit trail / performance record.
        self.journal = TradeJournal(project_root / "data" / "journal")
        # Lazily-resolved starting capital for the SIM book. Cached because it
        # used to hit the broker once PER ORDER inside the open loop.
        self._sim_initial_cash_cache: Optional[float] = None


    # ─── Prep job (builds universe + candidates for the day) ──────────────────

    def prep_job(self) -> JobResult:
        """
        Build today's universe and screen it into a candidates file, so the
        open job has something to read. This is the morning's FIRST job —
        without it, open_job finds no candidates and skips. Runs pre-market.
        """
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        mode = self.config.mode.value
        logger.info("=== PREP JOB START ===")

        try:
            cache_dir = self.project_root / "data" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            today = date.today()

            # 1. Build the universe
            universe_builder = UniverseBuilder(UniverseConfig(), self.tradier)
            snapshot = universe_builder.build()
            universe_path = cache_dir / f"universe_{today.isoformat()}.json"
            universe_builder.save(snapshot, universe_path)
            logger.info("Prep: universe built with %d tickers", snapshot.count)

            # 2. Screen into candidates
            earnings = EarningsCalendar(unknown_means_safe=True)
            screener = Screener(ScreenerConfig(), self.tradier, earnings)
            result = screener.screen(snapshot)
            candidates_path = cache_dir / f"candidates_{today.isoformat()}.json"
            screener.save(result, candidates_path)
            logger.info("Prep: %d candidates screened", len(result.candidates))

            msg = (
                f"Prep complete: {snapshot.count} universe → "
                f"{len(result.candidates)} candidates"
            )
            self.journal.record_job("prep_job", mode, True, msg)
            logger.info("=== PREP JOB DONE: %s ===", msg)
            return JobResult("prep_job", ts, mode, True, msg, details={
                "universe_count": snapshot.count,
                "candidate_count": len(result.candidates),
            })

        except Exception as e:
            logger.exception("Prep job crashed")
            self.journal.record_job("prep_job", mode, False, f"error: {e}")
            return JobResult("prep_job", ts, mode, False,
                              f"Prep job error: {e}", error=str(e))

    # ─── Order placement helper (mode-aware) ──────────────────────────────────

    def _place_or_preview(
        self, underlying: str, legs: list[OptionLeg],
        order_type: OrderType, price: float, tag: str,
    ) -> dict:
        """Place an order if mode allows, else preview. Returns Tradier response."""
        preview = not self.config.places_real_orders
        return self.tradier.place_multileg_order(
            underlying=underlying, legs=legs, order_type=order_type,
            price=price, preview=preview, tag=tag,
        )

    # ─── Open job ──────────────────────────────────────────────────────────────

    def open_job(self) -> JobResult:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        mode = self.config.mode.value
        logger.info("=== OPEN JOB START (mode=%s) ===", mode)

        try:
            candidates_path = (
                self.project_root / "data" / "cache"
                / f"candidates_{date.today().isoformat()}.json"
            )
            if not candidates_path.exists():
                msg = f"No candidates file for today ({candidates_path.name}). Run screener first."
                logger.warning(msg)
                return JobResult("open_job", ts, mode, False, msg)

            candidates = _load_candidates(candidates_path)[: self.config.max_candidates_to_consider]

            # In SIM the broker has no positions and never will, so risk state
            # MUST come from the sim book — otherwise every cap is inert and the
            # book grows without bound. See sim_positions_view().
            sim_book = None
            if self.config.is_sim:
                sim_book = self._load_sim_book()
                positions = self.sim_positions_view(sim_book)
                account_value = sim_book.total_equity({})
                logger.info(
                    "SIM risk state: %d open spread(s) -> %d synthetic legs, "
                    "sim equity $%s",
                    len(sim_book.open_spreads), len(positions), f"{account_value:,.0f}",
                )
            else:
                account_value = self.tradier.get_account_value()
                positions = self.tradier.get_positions()

            state_path = self.project_root / "data" / "state" / "account_state.json"
            account_state = AccountState.load_or_init(state_path, current_equity=account_value)

            # Idempotency: skip candidates whose exact spread is already open.
            # The width comes from OUR strategy config, so changing spread_width
            # keeps dedup working instead of silently disabling it.
            open_fps = fingerprints_from_positions(
                positions, self.strategy.config.spread_width)
            strat_result = self.strategy.build_orders(candidates, already_open_fingerprints=open_fps)

            risk_result = self.risk.filter_orders(
                orders=strat_result.orders,
                account_value=account_value,
                current_positions=positions,
                today_pnl_pct=account_state.day_pnl_pct(),
            )

            if risk_result.kill_switch_active:
                msg = f"Kill switch active: {risk_result.kill_switch_reason}"
                logger.warning(msg)
                self.journal.record_kill_switch(risk_result.kill_switch_reason, mode)
                return JobResult("open_job", ts, mode, True, msg,
                                  details={"kill_switch": True})

            # Backstop: cap opens per run
            to_open = risk_result.accepted[: self.config.max_opens_per_run]

            # ─── LLM advisory pass (flag-and-log only; NEVER blocks) ─────────
            advisories = {}
            if self.advisor is not None and getattr(self.advisor, "enabled", False):
                symbols = [s.order.symbol for s in to_open]
                advisory_results = self.advisor.review_orders(symbols)
                for sym, adv in advisory_results.items():
                    advisories[sym] = {
                        "signal": adv.signal.value,
                        "events": adv.flagged_events,
                        "reasoning": adv.reasoning,
                    }
                    if adv.is_concern:
                        logger.warning(
                            "ADVISORY CONCERN for %s (informational, NOT "
                            "blocking): %s | events: %s",
                            sym, adv.reasoning, ", ".join(adv.flagged_events),
                        )

            placed, failed = [], []
            for sized in to_open:
                order = sized.order

                # ── SIM mode: open the spread in the sim book, skip broker ──
                if self.config.is_sim:
                    from portfolio.sim_portfolio import SimSpread
                    sim_path = self._sim_path()
                    # Reuse the book already loaded for the risk check above —
                    # reloading per order re-hit the broker for account value on
                    # every iteration and could race its own writes.
                    sim = sim_book
                    sid = (f"{order.symbol}-{order.expiration}-"
                           f"{order.short_strike}-{order.long_strike}")
                    sim.open_spread(SimSpread(
                        spread_id=sid, underlying=order.symbol,
                        expiration=str(order.expiration),
                        short_strike=order.short_strike, long_strike=order.long_strike,
                        contracts=sized.contracts,
                        # Store credit in PER-SPREAD DOLLARS (premium × 100) to
                        # match the per-spread-dollar close cost computed in the
                        # sim manage job. target_credit_per_contract is per-share.
                        credit_received_per_spread=order.target_credit_per_contract * 100.0,
                        short_put_occ=order.short_put_occ, long_put_occ=order.long_put_occ,
                    ))
                    sim.save(sim_path)
                    self.journal.record_open(
                        symbol=order.symbol, short_strike=order.short_strike,
                        long_strike=order.long_strike, contracts=sized.contracts,
                        credit=order.target_credit_per_contract, mode=mode,
                        order_id=sid, status="sim_filled",
                    )
                    placed.append({
                        "symbol": order.symbol, "contracts": sized.contracts,
                        "credit": order.target_credit_per_contract,
                        "order_id": sid, "status": "sim_filled",
                    })
                    continue

                legs = [
                    OptionLeg(order.short_put_occ, OrderSide.SELL_TO_OPEN, sized.contracts),
                    OptionLeg(order.long_put_occ, OrderSide.BUY_TO_OPEN, sized.contracts),
                ]
                try:
                    resp = self._place_or_preview(
                        order.symbol, legs, OrderType.CREDIT,
                        order.target_credit_per_contract, order.tag,
                    )
                    ok = resp.get("status") in ("ok", "open", "pending")
                    order_id = resp.get("id")
                    fill_status = resp.get("status")

                    # ── Fill confirmation (only when actually placing) ───────
                    if ok and self.config.places_real_orders and order_id \
                            and self.config.confirm_fills \
                            and self.config.fill_wait_secs > 0:
                        final = self.tradier.wait_for_fill(
                            order_id,
                            max_wait_secs=self.config.fill_wait_secs,
                            poll_interval_secs=self.config.fill_poll_interval_secs,
                        )
                        fill_status = (final.get("status") or fill_status or "").lower()
                        logger.info(
                            "%s order %s final status: %s",
                            order.symbol, order_id, fill_status,
                        )
                        self.journal.record_fill(
                            symbol=order.symbol, order_id=order_id,
                            status=fill_status,
                            fill_price=final.get("avg_fill_price"),
                        )
                        # Cancel if still working after the wait window
                        if (fill_status not in ("filled", "partially_filled")
                                and self.config.cancel_unfilled_opens):
                            try:
                                self.tradier.cancel_order(order_id)
                                logger.info(
                                    "Canceled unfilled order %s (%s)",
                                    order_id, order.symbol,
                                )
                                fill_status = "canceled_unfilled"
                            except TradierError as ce:
                                logger.warning(
                                    "Could not cancel unfilled %s: %s",
                                    order_id, ce,
                                )

                    (placed if ok else failed).append({
                        "symbol": order.symbol, "contracts": sized.contracts,
                        "credit": order.target_credit_per_contract,
                        "order_id": order_id, "status": fill_status,
                    })
                    # Journal the open (only when actually placing, not preview)
                    if ok and self.config.places_real_orders:
                        self.journal.record_open(
                            symbol=order.symbol,
                            short_strike=order.short_strike,
                            long_strike=order.long_strike,
                            contracts=sized.contracts,
                            credit=order.target_credit_per_contract,
                            mode=mode,
                            order_id=order_id,
                            status=fill_status,
                        )
                except TradierError as e:
                    logger.warning("Open failed for %s: %s", order.symbol, e)
                    failed.append({"symbol": order.symbol, "error": str(e)})

            verb = "Placed" if self.config.places_real_orders else "Previewed"
            msg = (
                f"{verb} {len(placed)} opening orders "
                f"({len(failed)} failed, {len(risk_result.rejected)} risk-rejected)"
            )
            logger.info("=== OPEN JOB DONE: %s ===", msg)
            return JobResult("open_job", ts, mode, True, msg, details={
                "placed": placed, "failed": failed,
                "risk_rejected": len(risk_result.rejected),
                "account_value": account_value,
                "advisories": advisories,
            })

        except Exception as e:
            logger.exception("Open job crashed")
            return JobResult("open_job", ts, mode, False,
                              f"Open job error: {e}", error=str(e))

    # ─── Manage job ────────────────────────────────────────────────────────────

    def manage_job(self) -> JobResult:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        mode = self.config.mode.value
        logger.info("=== MANAGE JOB START (mode=%s) ===", mode)

        if self.config.is_sim:
            return self._manage_job_sim(ts, mode)

        try:
            snapshot = self.portfolio.sync()
            to_close = snapshot.positions_to_close()

            if not to_close:
                msg = (
                    f"{len(snapshot.spreads)} open spreads, "
                    f"P&L ${snapshot.total_unrealized_pnl:,.0f}, none to close"
                )
                logger.info("=== MANAGE JOB DONE: %s ===", msg)
                return JobResult("manage_job", ts, mode, True, msg, details={
                    "open_spreads": len(snapshot.spreads),
                    "total_pnl": snapshot.total_unrealized_pnl,
                })

            closed, failed = [], []
            for spread in to_close:
                close_price = round(max(spread.current_close_cost_per_spread / 100.0, 0.01), 2)
                try:
                    resp = self._place_or_preview(
                        spread.underlying, spread.to_closing_legs(),
                        OrderType.DEBIT, close_price, f"close-{spread.underlying}",
                    )
                    ok = resp.get("status") in ("ok", "open", "pending")
                    (closed if ok else failed).append({
                        "symbol": spread.underlying,
                        "decision": spread.decision.value,
                        "pnl": spread.unrealized_pnl_dollars,
                        "status": resp.get("status"),
                    })
                    # Journal the close with realized P&L (only when placing)
                    if ok and self.config.places_real_orders:
                        self.journal.record_close(
                            symbol=spread.underlying,
                            short_strike=spread.short_strike,
                            long_strike=spread.long_strike,
                            contracts=spread.contracts,
                            decision=spread.decision.value,
                            realized_pnl=spread.unrealized_pnl_dollars,
                            mode=mode,
                            order_id=resp.get("id"),
                            status=resp.get("status"),
                        )
                except TradierError as e:
                    logger.warning("Close failed for %s: %s", spread.underlying, e)
                    failed.append({"symbol": spread.underlying, "error": str(e)})

            verb = "Closed" if self.config.places_real_orders else "Previewed close of"
            msg = (
                f"{verb} {len(closed)} spreads "
                f"({len(failed)} failed); {len(snapshot.spreads)} total open, "
                f"P&L ${snapshot.total_unrealized_pnl:,.0f}"
            )
            logger.info("=== MANAGE JOB DONE: %s ===", msg)
            return JobResult("manage_job", ts, mode, True, msg, details={
                "closed": closed, "failed": failed,
                "open_spreads": len(snapshot.spreads),
                "total_pnl": snapshot.total_unrealized_pnl,
            })

        except Exception as e:
            logger.exception("Manage job crashed")
            return JobResult("manage_job", ts, mode, False,
                              f"Manage job error: {e}", error=str(e))

    # ─── SIM helpers ─────────────────────────────────────────────────────────

    def _sim_initial_cash(self) -> float:
        """
        Starting capital for the options sim book. Uses the broker account value
        if reachable (so the sim mirrors a realistic balance), else a default.

        Only ever called when a NEW sim book has to be seeded — it is passed to
        load_or_init as a callable, which invokes it lazily. See the note there:
        calling it eagerly cost one broker round-trip per manage cycle (12 a
        day) whose result was thrown away because the file already existed.
        """
        if self._sim_initial_cash_cache is None:
            try:
                self._sim_initial_cash_cache = float(self.tradier.get_account_value())
            except Exception as e:
                logger.warning(
                    "Could not read broker account value to seed the sim book "
                    "(%s); seeding with $100,000.", e,
                )
                self._sim_initial_cash_cache = 100_000.0
        return self._sim_initial_cash_cache

    def _sim_dir(self) -> Path:
        return self.project_root / "data" / "sim" / "options"

    def _sim_path(self) -> Path:
        return self._sim_dir() / "portfolio.json"

    def _load_sim_book(self):
        from portfolio.sim_portfolio import OptionsSimPortfolio
        # Pass the seed as a CALLABLE so the broker is only hit when there is
        # no book on disk to load.
        return OptionsSimPortfolio.load_or_init(
            self._sim_path(), initial_cash=self._sim_initial_cash)

    @staticmethod
    def sim_positions_view(sim) -> list[dict]:
        """
        Render the sim book as Tradier-shaped option position dicts.

        WHY THIS EXISTS: in SIM the bot places no broker orders, so
        tradier.get_positions() returns [] forever. The risk manager and the
        strategy's dedup both take their state from that list — so every single
        day the risk layer saw ZERO open positions and happily re-approved a
        full book. max_concurrent_positions, max_positions_per_ticker,
        max_total_deployed_pct and the fingerprint dedup were all inert in SIM,
        and the sim book grew without bound. Its equity curve therefore did not
        describe the risk-limited strategy at all.

        Each spread renders as TWO legs, matching how Tradier reports a spread.
        cost_basis follows Tradier's own convention — TOTAL premium dollars for
        the leg, negative for the short (we received it), positive for the long
        (we paid it) — because the consumers now derive capital-at-risk from
        strikes and credit rather than reading cost_basis as if it were already
        max loss. The sim book stores only the NET credit per spread, so the
        whole credit is attributed to the short leg and the long leg carries
        zero; net premium, width and contracts are identical either way, so
        every downstream figure (deployed max loss, per-ticker counts,
        fingerprints) comes out the same.
        """
        positions: list[dict] = []
        for s in sim.open_spreads.values():
            positions.append({
                "symbol": s.short_put_occ,
                "quantity": -s.contracts,
                "cost_basis": -(s.credit_received_per_spread * s.contracts),
            })
            positions.append({
                "symbol": s.long_put_occ,
                "quantity": s.contracts,
                "cost_basis": 0.0,
            })
        return positions

    def _manage_job_sim(self, ts: str, mode: str) -> JobResult:
        """
        SIM manage: price each open spread in the sim book from current option
        quotes, apply the same profit/stop/time exit rules, close the ones that
        hit, mark to market, and append an equity-curve snapshot.
        """
        from datetime import date
        from portfolio.sim_portfolio import OptionsSimPortfolio
        from portfolio.portfolio import ExitDecision

        cfg = self.portfolio.config  # reuse the same exit thresholds
        sim_dir = self.project_root / "data" / "sim" / "options"
        sim_path = sim_dir / "portfolio.json"
        curve_path = sim_dir / "equity_curve.jsonl"
        sim = OptionsSimPortfolio.load_or_init(sim_path, initial_cash=self._sim_initial_cash())

        if not sim.open_spreads:
            snap = sim.record_equity_snapshot(curve_path, {}, label="manage")
            msg = f"SIM: 0 open spreads; equity ${snap['equity']:,.0f}"
            logger.info("=== MANAGE JOB DONE: %s ===", msg)
            return JobResult("manage_job", ts, mode, True, msg,
                             details={"open_spreads": 0})

        today = date.today()
        close_costs: dict[str, float] = {}   # spread_id -> close cost per spread ($)
        to_close: list[tuple[str, str, float]] = []  # (id, decision, close_cost)

        for sid, s in list(sim.open_spreads.items()):
            # Price both legs from current quotes (buy back short at ask, sell long at bid)
            try:
                quotes = self.tradier.get_quotes([s.short_put_occ, s.long_put_occ])
            except Exception as e:
                logger.warning("SIM: could not quote %s: %s; holding.", sid, e)
                continue
            qmap = {q.get("symbol"): q for q in quotes} if isinstance(quotes, list) else {}
            short_q = qmap.get(s.short_put_occ, {})
            long_q = qmap.get(s.long_put_occ, {})
            short_ask = _q(short_q, "ask") or _q(short_q, "last")
            long_bid = _q(long_q, "bid") or _q(long_q, "last")
            if short_ask <= 0 and long_bid <= 0:
                continue  # un-priceable; hold
            close_cost_per_spread = (short_ask - long_bid) * 100.0
            close_costs[sid] = close_cost_per_spread

            credit = s.credit_received_per_spread
            pnl_pct = ((credit - close_cost_per_spread) / credit) if credit > 0 else 0.0
            dte = (date.fromisoformat(s.expiration) - today).days

            if pnl_pct >= cfg.profit_target_pct:
                to_close.append((sid, "close_profit", close_cost_per_spread))
            elif pnl_pct <= -cfg.stop_loss_multiple:
                to_close.append((sid, "close_stop", close_cost_per_spread))
            elif dte <= cfg.time_exit_dte:
                to_close.append((sid, "close_time", close_cost_per_spread))

        closed = []
        for sid, decision, cost in to_close:
            s = sim.open_spreads[sid]
            pnl = sim.close_spread(sid, cost)
            self.journal.record_close(
                symbol=s.underlying, short_strike=s.short_strike,
                long_strike=s.long_strike, contracts=s.contracts,
                decision=decision, realized_pnl=pnl, mode=mode,
                order_id=sid, status="sim_closed")
            closed.append({"spread_id": sid, "decision": decision, "pnl": round(pnl, 2)})

        sim.save(sim_path)
        snap = sim.record_equity_snapshot(curve_path, close_costs, label="manage")
        msg = (f"SIM: closed {len(closed)}; {len(sim.open_spreads)} open; "
               f"equity ${snap['equity']:,.0f} "
               f"({snap['return_since_start']*100:+.2f}% since start)")
        logger.info("=== MANAGE JOB DONE: %s ===", msg)
        return JobResult("manage_job", ts, mode, True, msg, details={
            "closed": closed, "open_spreads": len(sim.open_spreads),
            "total_pnl": snap["unrealized_pnl"],
        })


def _q(quote: dict, field: str) -> float:
    """Safely pull a numeric field from a quote dict; 0.0 if missing/bad."""
    try:
        v = quote.get(field)
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
