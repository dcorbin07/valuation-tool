"""
Backtest engine for the trend and momentum bots.

Replays each strategy day-by-day against historical daily prices and emits an
equity curve in the SAME format as the live SIM curves — so the existing
correlation_tracker.py works on backtested curves with zero changes.

Key idea: a backtest is just "run the existing pipeline against historical
prices instead of live ones." We reuse the real signal, strategy, risk, and
SimPortfolio code — nothing about the strategy logic is re-implemented here, so
the backtest tests the same code that trades. The only new thing is the
day-by-day replay loop and the historical price feed.

TWO DATA SOURCES, AND THEY ARE NOT EQUIVALENT
─────────────────────────────────────────────
  * Tradier (PriceHistory.fetch) — a few years of history, one HTTP call per
    symbol, and the universe comes from a LIVE screener. That last part means
    SURVIVORSHIP BIAS: delisted names are structurally absent and the survivors
    were pre-selected by an outcome that happened after the measured period.
    Usable for a rough correlation between two bots. NOT usable for return
    claims.

  * Sharadar (PriceHistory.from_store / load_panel, driven by
    scripts/run_sharadar_backtest.py) — decades of history including delisted
    tickers, with the universe rebuilt point-in-time at every rebalance. This
    is the one to trust for returns.

Remaining honest limitations, both sources:
  - Fills are assumed at the daily CLOSE of the decision day, and the signal is
    computed from closes including that same day. That is a mild look-ahead;
    the stricter construction is signal at close t, fill at t+1.
  - No commissions, no slippage, no borrow cost, and no check that the shorts
    were actually borrowable.
  - The rebalance cadence is indexed over the union of dates any symbol traded,
    not a real exchange calendar.
"""
from __future__ import annotations

import json
import logging
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core import SimPortfolio, TradierClient
from core.sim_execution import apply_orders_to_sim

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    start: date
    end: date
    initial_capital: float = 100_000.0
    # How often to rebalance, in trading days. Trend ≈ daily(1); momentum is
    # classically monthly(~21). Default 21 keeps turnover/log size sane.
    rebalance_every_days: int = 21
    # Warmup: the signal needs ~252 prior bars, so the backtest can't start
    # trading until it has that much history before `start`.
    warmup_days: int = 260


class PriceHistory:
    """
    Stores daily closes for a set of symbols, then serves point-in-time slices:
    "the closes for symbol X up to date D".

    PERFORMANCE NOTE. `closes_up_to` and `price_on` are called once per symbol
    per simulated day. The original implementation scanned the whole series
    linearly each time — for 150 symbols x 750 days x ~1,000 bars that is
    roughly 10^8 operations BEFORE any signal maths runs, and it is why the
    old backtest was unusably slow on a realistic universe. Both now bisect a
    pre-sorted date list, which turns each call into a binary search.

    The dates are kept in a parallel list precisely so `bisect` can be used
    directly; zipping tuples on every call would give back the cost.
    """

    def __init__(self, tradier: Optional[TradierClient] = None):
        self.tradier = tradier
        self._closes: dict[str, list[tuple[date, float]]] = {}
        self._dates: dict[str, list[date]] = {}      # parallel, for bisect
        self._vals: dict[str, list[float]] = {}

    # ── loading ────────────────────────────────────────────────────────────

    def _index(self, sym: str, series: list[tuple[date, float]]) -> None:
        series.sort(key=lambda t: t[0])
        self._closes[sym] = series
        self._dates[sym] = [d for d, _ in series]
        self._vals[sym] = [c for _, c in series]

    def load_panel(self, panel: dict[str, list[tuple[date, float]]]) -> None:
        """
        Bulk-load an entire price panel in one go.

        THIS IS THE SHARADAR PATH. `fetch()` below makes one HTTP call per
        symbol with a rate-limit floor between them — fine for 25 ETFs, absurd
        for a 3,000-name point-in-time universe. A Sharadar-backed caller reads
        the whole panel out of local sqlite and hands it over here, and the
        per-symbol loop never happens.
        """
        for sym, series in panel.items():
            if series:
                self._index(sym, list(series))
        logger.info("Loaded price panel: %d symbols, %d total bars",
                    len(self._closes), sum(len(v) for v in self._vals.values()))

    @classmethod
    def from_store(cls, store, symbols: list[str], start: date, end: date,
                   adjusted: bool = True) -> "PriceHistory":
        """
        Build directly from a SharadarStore.

        adjusted=True (default) uses closeadj — the split AND dividend adjusted
        total-return series. Every signal here is a ratio of two closes at
        different times, so anything else silently understates return by the
        dividend yield.
        """
        h = cls(tradier=None)
        h.load_panel({s: store.closes(s, start, end, adjusted) for s in symbols})
        return h

    def fetch(self, symbols: list[str], start: date, end: date) -> None:
        """Per-symbol fetch over a broker client. Kept for the Tradier path."""
        if self.tradier is None:
            raise ValueError("PriceHistory has no client; use load_panel()/from_store()")
        dropped = 0
        for i, sym in enumerate(symbols, 1):
            try:
                bars = self.tradier.get_history(sym, start=start, end=end, interval="daily")
            except Exception as e:
                logger.warning("History fetch failed for %s: %s", sym, e)
                continue
            series = []
            for b in bars:
                d, c = b.get("date"), b.get("close")
                # An explicit zero/None close is a DATA problem, not a valid
                # bar. The old `if d and c` silently swallowed both; count them
                # so a broken feed shows up instead of quietly shortening
                # every series.
                if not d or c in (None, ""):
                    dropped += 1
                    continue
                try:
                    px = float(c)
                except (TypeError, ValueError):
                    dropped += 1
                    continue
                if px <= 0:
                    dropped += 1
                    continue
                try:
                    series.append((date.fromisoformat(d), px))
                except ValueError:
                    dropped += 1
            if series:
                self._index(sym, series)
            if i % 50 == 0:
                logger.info("Fetched history: %d/%d symbols", i, len(symbols))
        if dropped:
            logger.warning("Dropped %d unusable bar(s) across the fetch", dropped)
        logger.info("History ready for %d/%d symbols", len(self._closes), len(symbols))

    # ── point-in-time reads ────────────────────────────────────────────────

    def symbols(self) -> list[str]:
        return list(self._closes.keys())

    def closes_up_to(self, symbol: str, as_of: date) -> list[float]:
        """All closes for `symbol` on or before `as_of` (oldest first)."""
        dates = self._dates.get(symbol)
        if not dates:
            return []
        return self._vals[symbol][: bisect_right(dates, as_of)]

    def price_on(self, symbol: str, as_of: date) -> Optional[float]:
        """The most recent close on or before `as_of`."""
        dates = self._dates.get(symbol)
        if not dates:
            return None
        i = bisect_right(dates, as_of)
        return self._vals[symbol][i - 1] if i else None

    def trading_dates(self, start: date, end: date) -> list[date]:
        """Union of all dates we have any data for, within [start, end]."""
        all_dates: set[date] = set()
        for dates in self._dates.values():
            lo = bisect_left(dates, start)
            hi = bisect_right(dates, end)
            all_dates.update(dates[lo:hi])
        return sorted(all_dates)


def _apply_plan_to_sim(sim: SimPortfolio, orders: list, prices: dict[str, float]) -> list[dict]:
    """
    Thin wrapper over the SHARED sim-execution path.

    This used to be a second, near-identical implementation — which is exactly
    how the live and backtest paths drifted apart (the duplicate silently
    dropped unpriced orders at no log level at all). Route through the one
    function so a fix in either place fixes both.
    """
    return apply_orders_to_sim(sim, orders, prices)


class Backtester:
    """
    Generic day-by-day replay. Takes callables that produce, for a given
    as-of date, (target_weights_obj, last_prices) — i.e. the strategy's target —
    plus the risk + portfolio managers to size and diff. Reused by both bots.
    """

    def __init__(self, config: BacktestConfig, history: PriceHistory,
                 risk_manager, portfolio_manager):
        self.config = config
        self.history = history
        self.risk = risk_manager
        self.portfolio = portfolio_manager

    def run(self, bot_name: str, build_target_fn, project_root: Path) -> list[dict]:
        """
        build_target_fn(as_of) -> (TargetPortfolio, last_prices_dict)
        Returns the equity-curve snapshots and writes them to
        data/sim/<bot_name>_backtest/equity_curve.jsonl.
        """
        cfg = self.config
        sim = SimPortfolio(cash=cfg.initial_capital, starting_equity=cfg.initial_capital)
        dates = self.history.trading_dates(cfg.start, cfg.end)
        if not dates:
            logger.warning("No trading dates in window — is history loaded?")
            return []

        curve_path = project_root / "data" / "sim" / f"{bot_name}_backtest" / "equity_curve.jsonl"
        curve_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file and move on success. Truncating in place meant a
        # crashed run left a PARTIAL curve that is indistinguishable from a
        # complete one — you would compute a Sharpe over half a backtest and
        # never know.
        tmp_path = curve_path.with_suffix(".jsonl.partial")
        tmp_path.write_text("")

        # ── Kill-switch state, so the backtest runs the SAME risk code ──────
        #
        # risk.size() was previously called without today_pnl_pct, which
        # defaults to 0.0 — so the -5% daily stop could never fire in a
        # backtest, and the module docstring's claim that "the backtest tests
        # the same code that trades" was false. We track simulated daily P&L
        # here and feed it in.
        day_start_equity = cfg.initial_capital
        current_day = None
        kill_switch_days = 0

        snapshots = []
        for i, as_of in enumerate(dates):
            # Mark-to-market prices for everything currently held + tradable
            held = list(sim.signed_shares().keys())
            mark_prices = {}
            for sym in set(held):
                p = self.history.price_on(sym, as_of)
                if p:
                    mark_prices[sym] = p

            if current_day != as_of:
                day_start_equity = sim.total_equity(mark_prices) or cfg.initial_capital
                current_day = as_of

            # Rebalance only every N days
            if i % cfg.rebalance_every_days == 0:
                target, last_prices = build_target_fn(as_of)
                mark_prices.update(last_prices)
                if target is not None and last_prices:
                    account_value = sim.total_equity(mark_prices)
                    day_pnl_pct = (
                        (account_value - day_start_equity) / day_start_equity
                        if day_start_equity else 0.0)
                    risk_result = self.risk.size(target, account_value, last_prices,
                                                 today_pnl_pct=day_pnl_pct)
                    if getattr(risk_result, "kill_switch_active", False):
                        kill_switch_days += 1
                        logger.info("%s: kill switch fired on %s (day P&L %.2f%%)",
                                    bot_name, as_of, day_pnl_pct * 100)
                    plan = self.portfolio.build_rebalance_plan(
                        risk_result.targets, current_override=sim.signed_shares())
                    # Fill from mark_prices, NOT last_prices. last_prices covers
                    # only names the signal selected this cycle; a position being
                    # EXITED is by definition not among them, so passing
                    # last_prices silently dropped every exit order — positions
                    # accumulated forever and marked at cost. mark_prices is
                    # last_prices ∪ prices for everything currently held.
                    _apply_plan_to_sim(sim, plan.orders, mark_prices)

            # Daily equity snapshot
            equity = sim.total_equity(mark_prices)
            snap = {
                # The SIMULATED date, not wall-clock. utcnow() stamped every
                # row of a backtest with the moment the backtest ran, which is
                # useless to anything reading timestamp_utc and actively
                # misleading when comparing two runs.
                "timestamp_utc": datetime.combine(
                    as_of, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
                "date": as_of.isoformat(),
                "equity": round(equity, 2),
                "cash": round(sim.cash, 2),
                "realized_pnl": round(sim.realized_pnl, 2),
                "unrealized_pnl": round(sim.unrealized_pnl(mark_prices), 2),
                "num_positions": len(sim.holdings),
                "return_since_start": round(equity / cfg.initial_capital - 1.0, 6),
                "label": "backtest",
            }
            with tmp_path.open("a") as f:
                f.write(json.dumps(snap) + "\n")
            snapshots.append(snap)

        # Only now, having completed, does this become THE curve.
        tmp_path.replace(curve_path)

        final = snapshots[-1] if snapshots else {}
        logger.info(
            "Backtest %s done: %d days, final equity $%.0f (%.2f%%), "
            "kill switch fired on %d rebalance(s)",
            bot_name, len(snapshots), final.get("equity", 0),
            final.get("return_since_start", 0) * 100, kill_switch_days)
        return snapshots
