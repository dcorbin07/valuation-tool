"""
Regression tests for the SIM exit-order bug.

THE BUG: each equity orchestrator built its price map from the CURRENT
selection only. A position that had dropped out of the top/bottom-N was by
definition not in the selection, so it had no price — and apply_orders_to_sim()
silently skipped any order it could not price. Exit orders therefore never
filled. Positions accumulated forever, and SimPortfolio.total_equity() marks an
unpriced holding at avg_cost, so each stranded position's P&L was frozen at
exactly zero. Every equity curve, Sharpe and correlation downstream was wrong.

These tests exercise the ORCHESTRATOR, not the pure functions. The bug lived
in the wiring between units that were each individually correct and
individually tested — which is precisely why the existing suites missed it.
"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import (
    EquitySide, SimPortfolio, TradingMode, apply_orders_to_sim, load_sim,
    resolve_prices,
)
from momentum import MomentumScore
from momentum.signals import RankedSelection as MomRankedSelection
from momentum.orchestrator import MomentumBotConfig, MomentumOrchestrator
from reversion.signals import RankedSelection as RevRankedSelection, ReversionScore
from reversion.orchestrator import ReversionBotConfig, ReversionOrchestrator


class _Order:
    def __init__(self, symbol, side, quantity):
        self.symbol, self.side, self.quantity = symbol, side, quantity


def _fake_tradier(quotes=None, account_value=100_000.0):
    """A Tradier double that only supports what the SIM path needs."""
    t = MagicMock()
    t.config.sandbox = True
    t.get_account_value.return_value = account_value
    quotes = quotes or {}

    def _get_quotes(symbols):
        return [{"symbol": s, "last": quotes[s]} for s in symbols if s in quotes]

    t.get_quotes.side_effect = _get_quotes
    return t


def _mom_score(sym, score, price, vol=0.20):
    return MomentumScore(symbol=sym, score=score, annualized_vol=vol,
                         last_price=price, bars_used=300, usable=True)


def _rev_score(sym, z, price, vol=0.20):
    return ReversionScore(symbol=sym, zscore=z, score=-z, annualized_vol=vol,
                          last_price=price, bars_used=100, usable=True)


# ─── resolve_prices: the new guarantee ──────────────────────────────────────


class TestResolvePrices(unittest.TestCase):
    def test_backfills_held_symbol_missing_from_base(self):
        t = _fake_tradier(quotes={"OLD": 42.0})
        prices, unresolved = resolve_prices(t, {"NEW": 10.0}, ["NEW", "OLD"])
        self.assertEqual(prices["OLD"], 42.0)
        self.assertEqual(prices["NEW"], 10.0)
        self.assertEqual(unresolved, [])

    def test_reports_symbols_it_cannot_price(self):
        t = _fake_tradier(quotes={})
        prices, unresolved = resolve_prices(t, {}, ["GHOST"])
        self.assertEqual(unresolved, ["GHOST"])

    def test_no_quote_call_when_everything_already_priced(self):
        t = _fake_tradier(quotes={"A": 1.0})
        resolve_prices(t, {"A": 5.0}, ["A"])
        t.get_quotes.assert_not_called()

    def test_falls_back_through_last_close_prevclose(self):
        t = MagicMock()
        t.get_quotes.return_value = [
            {"symbol": "A", "last": None, "close": 0, "prevclose": 7.5},
        ]
        prices, unresolved = resolve_prices(t, {}, ["A"])
        self.assertEqual(prices["A"], 7.5)
        self.assertEqual(unresolved, [])

    def test_survives_a_broker_exception(self):
        t = MagicMock()
        t.get_quotes.side_effect = RuntimeError("broker down")
        prices, unresolved = resolve_prices(t, {"A": 1.0}, ["A", "B"])
        self.assertEqual(unresolved, ["B"])          # reported, not swallowed
        self.assertEqual(prices["A"], 1.0)           # and it didn't blow up

    def test_batches_respect_the_size_limit(self):
        syms = [f"S{i}" for i in range(120)]
        t = _fake_tradier(quotes={s: 1.0 for s in syms})
        resolve_prices(t, {}, syms, batch_size=50)
        self.assertEqual(t.get_quotes.call_count, 3)  # 50 + 50 + 20


# ─── apply_orders_to_sim must not fail quietly ──────────────────────────────


class TestUnpricedOrderIsLoud(unittest.TestCase):
    def test_unpriced_order_logs_a_warning(self):
        sim = SimPortfolio(cash=100_000, starting_equity=100_000)
        with self.assertLogs("core.sim_execution", level="WARNING") as cm:
            fills = apply_orders_to_sim(sim, [_Order("XYZ", EquitySide.SELL, 10)], {})
        self.assertEqual(fills, [])
        self.assertIn("XYZ", "".join(cm.output))


# ─── Orchestrator integration: the actual bug ───────────────────────────────


class _EquityOrchestratorExitMixin:
    """Shared scenario: hold two names, then rotate to two different ones."""

    def _run(self, orch, selection):
        with patch.object(orch, "_build_universe_symbols", return_value=[]), \
             patch.object(orch.signals, "generate", return_value=selection):
            return orch.rebalance_job()

    def test_dropped_name_is_actually_exited(self):
        """The core regression: a name that leaves the selection must be CLOSED."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orch = self._make_orch(root, _fake_tradier())

            res = self._run(orch, self._selection_round_one())
            self.assertTrue(res.success, res.error)
            held = load_sim(root, self.bot_name, 100_000).signed_shares()
            self.assertIn("AAA", held)
            self.assertIn("BBB", held)

            # Round two: AAA/BBB are gone from the selection but are still
            # scored, so their prices ride along in all_prices.
            res = self._run(orch, self._selection_round_two(include_old_prices=True))
            self.assertTrue(res.success, res.error)
            held = load_sim(root, self.bot_name, 100_000).signed_shares()

            self.assertNotIn("AAA", held, "AAA was never exited — the SIM exit bug")
            self.assertNotIn("BBB", held, "BBB was never exited — the SIM exit bug")
            self.assertIn("CCC", held)
            self.assertIn("DDD", held)

    def test_exit_works_when_name_left_the_universe_entirely(self):
        """Harder case: the old name isn't even scored — backfill via quotes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Quotes are the ONLY source of a price for AAA/BBB in round two.
            tradier = _fake_tradier(quotes={"AAA": 105.0, "BBB": 95.0})
            orch = self._make_orch(root, tradier)

            self._run(orch, self._selection_round_one())
            self.assertIn("AAA", load_sim(root, self.bot_name, 100_000).signed_shares())

            res = self._run(orch, self._selection_round_two(include_old_prices=False))
            self.assertTrue(res.success, res.error)
            held = load_sim(root, self.bot_name, 100_000).signed_shares()

            self.assertNotIn("AAA", held, "quote backfill did not rescue the exit")
            self.assertNotIn("BBB", held, "quote backfill did not rescue the exit")
            tradier.get_quotes.assert_called()

    def test_position_count_does_not_grow_without_bound(self):
        """Three rotations should leave ~2 positions, not ~6."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orch = self._make_orch(root, _fake_tradier())
            self._run(orch, self._selection_round_one())
            self._run(orch, self._selection_round_two(include_old_prices=True))
            self._run(orch, self._selection_round_three())
            held = load_sim(root, self.bot_name, 100_000).signed_shares()
            self.assertLessEqual(len(held), 2, f"positions accumulated: {held}")


class TestMomentumSimExits(_EquityOrchestratorExitMixin, unittest.TestCase):
    bot_name = "momentum"

    def _make_orch(self, root, tradier):
        cfg = MomentumBotConfig(mode=TradingMode.SIM, use_regime_gate=False)
        return MomentumOrchestrator(cfg, tradier, root)

    def _selection_round_one(self):
        longs = [_mom_score("AAA", 0.40, 100.0), _mom_score("BBB", 0.30, 50.0)]
        return MomRankedSelection(
            longs=longs, shorts=[],
            all_prices={"AAA": 100.0, "BBB": 50.0})

    def _selection_round_two(self, include_old_prices):
        longs = [_mom_score("CCC", 0.50, 80.0), _mom_score("DDD", 0.45, 60.0)]
        prices = {"CCC": 80.0, "DDD": 60.0}
        if include_old_prices:
            prices.update({"AAA": 105.0, "BBB": 45.0})
        return MomRankedSelection(longs=longs, shorts=[], all_prices=prices)

    def _selection_round_three(self):
        longs = [_mom_score("EEE", 0.60, 70.0), _mom_score("FFF", 0.55, 90.0)]
        return MomRankedSelection(
            longs=longs, shorts=[],
            all_prices={"EEE": 70.0, "FFF": 90.0,
                        "CCC": 82.0, "DDD": 58.0, "AAA": 105.0, "BBB": 45.0})


class TestReversionSimExits(_EquityOrchestratorExitMixin, unittest.TestCase):
    bot_name = "reversion"

    def _make_orch(self, root, tradier):
        cfg = ReversionBotConfig(mode=TradingMode.SIM, use_regime_gate=False)
        return ReversionOrchestrator(cfg, tradier, root)

    def _selection_round_one(self):
        longs = [_rev_score("AAA", -2.5, 100.0), _rev_score("BBB", -2.0, 50.0)]
        return RevRankedSelection(
            longs=longs, shorts=[],
            all_prices={"AAA": 100.0, "BBB": 50.0})

    def _selection_round_two(self, include_old_prices):
        longs = [_rev_score("CCC", -3.0, 80.0), _rev_score("DDD", -2.8, 60.0)]
        prices = {"CCC": 80.0, "DDD": 60.0}
        if include_old_prices:
            prices.update({"AAA": 105.0, "BBB": 45.0})
        return RevRankedSelection(longs=longs, shorts=[], all_prices=prices)

    def _selection_round_three(self):
        longs = [_rev_score("EEE", -3.2, 70.0), _rev_score("FFF", -3.1, 90.0)]
        return RevRankedSelection(
            longs=longs, shorts=[],
            all_prices={"EEE": 70.0, "FFF": 90.0,
                        "CCC": 82.0, "DDD": 58.0, "AAA": 105.0, "BBB": 45.0})


# ─── The same bug in the backtester ─────────────────────────────────────────


class TestBacktesterExits(unittest.TestCase):
    def test_backtest_closes_a_dropped_name(self):
        """
        core.backtest passed last_prices (selection-only) to the fill function
        while holding a correct mark_prices dict two lines above. Same bug,
        same consequence: exits vanished and stranded positions froze at cost.
        """
        from core.backtest import Backtester, BacktestConfig, PriceHistory

        dates = [date(2024, 1, d) for d in range(2, 12)]
        # AAA drifts up so the exit realizes a NON-ZERO P&L — that proves the
        # sale really executed at a marked price rather than being skipped.
        series = {
            "AAA": [(d, 100.0 + i) for i, d in enumerate(dates)],
            "CCC": [(d, 80.0) for d in dates],
        }
        history = PriceHistory()
        history.load_panel(series)

        from trend.portfolio import PortfolioConfig, TrendPortfolioManager
        from trend.risk import RiskConfig, TrendRiskManager
        from trend.strategy import TargetPortfolio, TargetWeight
        from trend.signals import Direction

        def _target(symbol):
            return TargetPortfolio(weights=[TargetWeight(
                symbol=symbol, direction=Direction.LONG, raw_weight=1.0,
                normalized_weight=1.0, annualized_vol=0.20)])

        cfg = BacktestConfig(start=dates[0], end=dates[-1], rebalance_every_days=1)
        bt = Backtester(cfg, history,
                        TrendRiskManager(RiskConfig()),
                        TrendPortfolioManager(PortfolioConfig(), None))

        def build_target(as_of):
            # Hold AAA on day one, then rotate entirely into CCC.
            if as_of == dates[0]:
                return _target("AAA"), {"AAA": 100.0}
            return _target("CCC"), {"CCC": 80.0}   # note: no AAA price

        with tempfile.TemporaryDirectory() as tmp:
            snapshots = bt.run("unittest_bot", build_target, Path(tmp))

        # The backtester keeps its book in memory and reports it per day, so
        # num_positions is the direct read on the symptom: with the bug AAA is
        # never closed and the count climbs to 2 and stays there forever.
        self.assertEqual(snapshots[0]["num_positions"], 1, "should hold only AAA on day 1")
        self.assertTrue(
            all(s["num_positions"] == 1 for s in snapshots),
            f"positions accumulated across the run: "
            f"{[s['num_positions'] for s in snapshots]}",
        )
        # And the rotation must have actually cost something to execute, i.e.
        # AAA really was sold rather than silently abandoned.
        self.assertNotEqual(snapshots[-1]["realized_pnl"], 0.0)


if __name__ == "__main__":
    unittest.main()
