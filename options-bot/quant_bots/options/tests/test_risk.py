"""
Risk module unit tests. No network access required.
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from risk import (
    AccountState,
    RejectReason,
    RiskConfig,
    RiskManager,
)
from strategy import SpreadOrder


def make_order(
    symbol: str = "SPY",
    short_strike: float = 90.0,
    long_strike: float = 85.0,
    target_credit_per_contract: float = 0.80,
    spread_width: float = 5.0,
) -> SpreadOrder:
    return SpreadOrder(
        symbol=symbol,
        expiration=date(2026, 6, 19),
        short_strike=short_strike,
        long_strike=long_strike,
        contracts=1,
        short_put_occ=f"{symbol}260619P{int(short_strike*1000):08d}",
        long_put_occ=f"{symbol}260619P{int(long_strike*1000):08d}",
        target_credit=target_credit_per_contract,
        target_credit_per_contract=target_credit_per_contract,
        estimated_max_loss=(spread_width - target_credit_per_contract) * 100,
        short_delta=0.20,
        atm_iv=0.30,
        spread_width=spread_width,
        fingerprint=f"{symbol}|2026-06-19|{short_strike:.4f}|{long_strike:.4f}",
        tag=f"pcs-{symbol}",
    )


def make_position(symbol: str, cost_basis: float = -100.0) -> dict:
    return {
        "symbol": symbol,
        "cost_basis": cost_basis,
        "quantity": 1,
        "date_acquired": "2026-05-10",
    }


class TestPositionSizing(unittest.TestCase):
    def test_sizes_to_one_contract_at_25k_account(self):
        manager = RiskManager(RiskConfig(risk_pct_per_trade=0.02))
        order = make_order(target_credit_per_contract=1.00, spread_width=5.0)
        result = manager.filter_orders(
            orders=[order], account_value=25_000.0,
            current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(result.accepted[0].contracts, 1)

    def test_sizes_to_multiple_contracts_at_100k(self):
        manager = RiskManager(RiskConfig(risk_pct_per_trade=0.02))
        order = make_order(target_credit_per_contract=1.00, spread_width=5.0)
        result = manager.filter_orders(
            orders=[order], account_value=100_000.0,
            current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(result.accepted[0].contracts, 5)

    def test_drops_when_order_too_big_for_account(self):
        manager = RiskManager(RiskConfig(risk_pct_per_trade=0.02))
        order = make_order(target_credit_per_contract=1.00, spread_width=5.0)
        result = manager.filter_orders(
            orders=[order], account_value=4_000.0,
            current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 0)
        self.assertEqual(len(result.rejected), 1)
        self.assertEqual(
            result.rejected[0].reason, RejectReason.DOES_NOT_FIT_RISK_BUDGET
        )

    def test_max_contracts_cap_enforced(self):
        manager = RiskManager(RiskConfig(
            risk_pct_per_trade=0.10, max_contracts_per_spread=10,
        ))
        order = make_order(target_credit_per_contract=1.00, spread_width=5.0)
        result = manager.filter_orders(
            orders=[order], account_value=10_000_000.0,
            current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(result.accepted[0].contracts, 10)


class TestPerTickerLimit(unittest.TestCase):
    def test_rejects_when_already_open_on_underlying(self):
        manager = RiskManager(RiskConfig(max_positions_per_ticker=1))
        positions = [
            make_position("SPY260619P00565000"),
            make_position("SPY260619P00560000"),
        ]
        order = make_order(symbol="SPY", short_strike=550, long_strike=545)
        result = manager.filter_orders(
            orders=[order], account_value=100_000.0,
            current_positions=positions, today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 0)
        self.assertEqual(
            result.rejected[0].reason, RejectReason.EXCEEDS_PER_TICKER_LIMIT
        )

    def test_allows_orders_on_different_tickers(self):
        manager = RiskManager(RiskConfig(max_positions_per_ticker=1))
        result = manager.filter_orders(
            orders=[make_order(symbol="SPY"), make_order(symbol="QQQ")],
            account_value=100_000.0, current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 2)

    def test_rejects_second_order_on_same_ticker_in_same_batch(self):
        manager = RiskManager(RiskConfig(max_positions_per_ticker=1))
        result = manager.filter_orders(
            orders=[
                make_order(symbol="SPY", short_strike=90, long_strike=85),
                make_order(symbol="SPY", short_strike=88, long_strike=83),
            ],
            account_value=100_000.0, current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(
            result.rejected[0].reason, RejectReason.EXCEEDS_PER_TICKER_LIMIT
        )


class TestMaxConcurrent(unittest.TestCase):
    def test_caps_at_max_concurrent(self):
        manager = RiskManager(RiskConfig(
            max_concurrent_positions=3, max_positions_per_ticker=10,
        ))
        orders = [make_order(symbol=f"SYM{i}") for i in range(5)]
        result = manager.filter_orders(
            orders=orders, account_value=100_000.0,
            current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 3)
        self.assertEqual(len(result.rejected), 2)
        for r in result.rejected:
            self.assertEqual(r.reason, RejectReason.EXCEEDS_CONCURRENT_LIMIT)

    def test_counts_existing_positions_against_cap(self):
        manager = RiskManager(RiskConfig(
            max_concurrent_positions=2, max_positions_per_ticker=10,
        ))
        positions = [
            make_position("AAA260619P00100000"),
            make_position("AAA260619P00095000"),
            make_position("BBB260619P00100000"),
            make_position("BBB260619P00095000"),
        ]
        result = manager.filter_orders(
            orders=[make_order(symbol="CCC")],
            account_value=100_000.0, current_positions=positions, today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 0)
        self.assertEqual(
            result.rejected[0].reason, RejectReason.EXCEEDS_CONCURRENT_LIMIT
        )


class TestBuyingPowerCap(unittest.TestCase):
    def test_caps_deployed_at_threshold(self):
        manager = RiskManager(RiskConfig(
            max_total_deployed_pct=0.50, risk_pct_per_trade=0.50,
            max_concurrent_positions=10, max_positions_per_ticker=10,
        ))
        result = manager.filter_orders(
            orders=[
                make_order(symbol="A", target_credit_per_contract=0.80),
                make_order(symbol="B", target_credit_per_contract=0.80),
            ],
            account_value=1_000.0, current_positions=[], today_pnl_pct=0.0,
        )
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(
            result.rejected[0].reason, RejectReason.EXCEEDS_BUYING_POWER_CAP
        )


class TestKillSwitch(unittest.TestCase):
    def test_kills_when_pnl_below_limit(self):
        manager = RiskManager(RiskConfig(daily_loss_limit_pct=-0.05))
        result = manager.filter_orders(
            orders=[make_order(symbol="SPY"), make_order(symbol="QQQ")],
            account_value=100_000.0, current_positions=[], today_pnl_pct=-0.06,
        )
        self.assertTrue(result.kill_switch_active)
        self.assertEqual(len(result.accepted), 0)
        for r in result.rejected:
            self.assertEqual(r.reason, RejectReason.KILL_SWITCH_ACTIVE)

    def test_no_kill_when_within_limits(self):
        manager = RiskManager(RiskConfig(daily_loss_limit_pct=-0.05))
        result = manager.filter_orders(
            orders=[make_order(symbol="SPY")],
            account_value=100_000.0, current_positions=[], today_pnl_pct=-0.03,
        )
        self.assertFalse(result.kill_switch_active)
        self.assertEqual(len(result.accepted), 1)

    def test_kill_triggers_exactly_at_limit(self):
        manager = RiskManager(RiskConfig(daily_loss_limit_pct=-0.05))
        result = manager.filter_orders(
            orders=[make_order(symbol="SPY")],
            account_value=100_000.0, current_positions=[], today_pnl_pct=-0.05,
        )
        self.assertTrue(result.kill_switch_active)


class TestAccountState(unittest.TestCase):
    def test_fresh_init_uses_current_as_starting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = AccountState.load_or_init(path, current_equity=50_000.0)
            self.assertEqual(state.starting_equity, 50_000.0)
            self.assertEqual(state.last_seen_equity, 50_000.0)
            self.assertEqual(state.date, date.today().isoformat())

    def test_same_day_keeps_starting_equity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            AccountState.load_or_init(path, current_equity=50_000.0)
            state2 = AccountState.load_or_init(path, current_equity=48_000.0)
            self.assertEqual(state2.starting_equity, 50_000.0)
            self.assertEqual(state2.last_seen_equity, 48_000.0)

    def test_new_day_resets_starting_equity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            yesterday = date.today() - timedelta(days=1)
            path.write_text(json.dumps({
                "date": yesterday.isoformat(),
                "starting_equity": 50_000.0,
                "last_seen_equity": 49_500.0,
            }))
            state = AccountState.load_or_init(path, current_equity=49_500.0)
            self.assertEqual(state.date, date.today().isoformat())
            self.assertEqual(state.starting_equity, 49_500.0)

    def test_day_pnl_pct_computation(self):
        state = AccountState(
            date="2026-05-19", starting_equity=100_000.0, last_seen_equity=95_000.0,
        )
        self.assertAlmostEqual(state.day_pnl_pct(), -0.05)

    def test_corrupted_file_recovers_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{ garbage not json")
            state = AccountState.load_or_init(path, current_equity=50_000.0)
            self.assertEqual(state.starting_equity, 50_000.0)


class TestEndToEnd(unittest.TestCase):
    def test_realistic_full_run(self):
        manager = RiskManager(RiskConfig(
            risk_pct_per_trade=0.02, max_concurrent_positions=10,
            max_positions_per_ticker=1, max_total_deployed_pct=0.50,
            daily_loss_limit_pct=-0.05,
        ))
        existing = [
            make_position("SPY260619P00565000"),
            make_position("SPY260619P00560000"),
        ]
        orders = [
            make_order(symbol="NVDA", target_credit_per_contract=1.00),
            make_order(symbol="SPY", short_strike=550, long_strike=545),
            make_order(symbol="META", target_credit_per_contract=0.90),
            make_order(symbol="AAPL", target_credit_per_contract=0.80),
        ]
        result = manager.filter_orders(
            orders=orders, account_value=50_000.0,
            current_positions=existing, today_pnl_pct=-0.01,
        )
        accepted_symbols = sorted([s.order.symbol for s in result.accepted])
        self.assertEqual(accepted_symbols, ["AAPL", "META", "NVDA"])
        self.assertIn("SPY", [r.symbol for r in result.rejected])


if __name__ == "__main__":
    unittest.main()


class TestVolScaledSizing(unittest.TestCase):
    """Vol-scaled sizing: smaller size at extreme IV, full size when moderate."""

    def _cfg(self):
        from risk.risk import RiskConfig
        return RiskConfig()

    def test_moderate_iv_full_size(self):
        from risk.risk import RiskManager
        self.assertEqual(RiskManager._vol_scale_factor(0.30, self._cfg()), 1.0)

    def test_extreme_iv_floored(self):
        from risk.risk import RiskManager
        cfg = self._cfg()
        self.assertAlmostEqual(RiskManager._vol_scale_factor(1.50, cfg), cfg.vol_scale_floor)

    def test_monotonic_decreasing(self):
        from risk.risk import RiskManager
        cfg = self._cfg()
        a = RiskManager._vol_scale_factor(0.50, cfg)
        b = RiskManager._vol_scale_factor(0.70, cfg)
        c = RiskManager._vol_scale_factor(0.90, cfg)
        self.assertGreater(a, b)
        self.assertGreater(b, c)

    def test_disabled_always_full(self):
        from risk.risk import RiskManager, RiskConfig
        cfg = RiskConfig(use_vol_scaled_sizing=False)
        self.assertEqual(RiskManager._vol_scale_factor(2.0, cfg), 1.0)
