"""
Orchestrator unit tests — focused on the safety-critical pieces: the
live/paper mode guardrails and the market calendar. No network required.
"""
import os
import unittest
from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from orchestrator import (
    BrokerEnvironmentMismatchError,
    LiveTradingNotAuthorizedError,
    OrchestratorConfig,
    TradingMode,
    is_market_open,
    is_trading_day,
)
from orchestrator.calendar import describe_market_state

EASTERN = ZoneInfo("America/New_York")


# ─── Safety switch ──────────────────────────────────────────────────────────


class TestTradingModeSafety(unittest.TestCase):
    def test_preview_only_is_default(self):
        config = OrchestratorConfig()
        self.assertEqual(config.mode, TradingMode.PREVIEW_ONLY)
        self.assertFalse(config.places_real_orders)

    def test_preview_only_validates_with_any_broker(self):
        config = OrchestratorConfig(mode=TradingMode.PREVIEW_ONLY)
        # Should not raise regardless of sandbox flag
        config.validate_against_broker(broker_is_sandbox=True)
        config.validate_against_broker(broker_is_sandbox=False)

    def test_paper_requires_sandbox_broker(self):
        config = OrchestratorConfig(mode=TradingMode.PAPER)
        # Sandbox broker — OK
        config.validate_against_broker(broker_is_sandbox=True)
        # Production broker — must raise
        with self.assertRaises(BrokerEnvironmentMismatchError):
            config.validate_against_broker(broker_is_sandbox=False)

    def test_paper_places_real_orders_flag(self):
        config = OrchestratorConfig(mode=TradingMode.PAPER)
        self.assertTrue(config.places_real_orders)

    def test_live_requires_confirmation_env_var(self):
        config = OrchestratorConfig(mode=TradingMode.LIVE)
        # No env var set — must raise
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(LiveTradingNotAuthorizedError):
                config.validate_against_broker(broker_is_sandbox=False)

    def test_live_requires_exact_confirmation_phrase(self):
        config = OrchestratorConfig(mode=TradingMode.LIVE)
        with patch.dict(os.environ, {"BOT_ALLOW_LIVE": "yes"}, clear=True):
            with self.assertRaises(LiveTradingNotAuthorizedError):
                config.validate_against_broker(broker_is_sandbox=False)

    def test_live_requires_production_broker(self):
        config = OrchestratorConfig(mode=TradingMode.LIVE)
        with patch.dict(os.environ, {"BOT_ALLOW_LIVE": "YES_I_UNDERSTAND"}, clear=True):
            # Even with confirmation, sandbox broker in LIVE mode must raise
            with self.assertRaises(BrokerEnvironmentMismatchError):
                config.validate_against_broker(broker_is_sandbox=True)

    def test_live_succeeds_with_both_keys(self):
        config = OrchestratorConfig(mode=TradingMode.LIVE)
        with patch.dict(os.environ, {"BOT_ALLOW_LIVE": "YES_I_UNDERSTAND"}, clear=True):
            # Confirmation set AND production broker — should not raise
            config.validate_against_broker(broker_is_sandbox=False)

    def test_from_env_defaults_to_preview(self):
        with patch.dict(os.environ, {}, clear=True):
            config = OrchestratorConfig.from_env()
            self.assertEqual(config.mode, TradingMode.PREVIEW_ONLY)

    def test_from_env_reads_mode(self):
        with patch.dict(os.environ, {"BOT_MODE": "paper"}, clear=True):
            config = OrchestratorConfig.from_env()
            self.assertEqual(config.mode, TradingMode.PAPER)

    def test_from_env_unknown_mode_defaults_to_preview(self):
        with patch.dict(os.environ, {"BOT_MODE": "garbage"}, clear=True):
            config = OrchestratorConfig.from_env()
            self.assertEqual(config.mode, TradingMode.PREVIEW_ONLY)


# ─── Calendar ───────────────────────────────────────────────────────────────


class TestCalendar(unittest.TestCase):
    def test_weekday_is_trading_day(self):
        # 2026-05-20 is a Wednesday, not a holiday
        self.assertTrue(is_trading_day(date(2026, 5, 20)))

    def test_saturday_not_trading_day(self):
        # 2026-05-23 is a Saturday
        self.assertFalse(is_trading_day(date(2026, 5, 23)))

    def test_sunday_not_trading_day(self):
        # 2026-05-24 is a Sunday
        self.assertFalse(is_trading_day(date(2026, 5, 24)))

    def test_christmas_not_trading_day(self):
        self.assertFalse(is_trading_day(date(2026, 12, 25)))

    def test_juneteenth_not_trading_day(self):
        self.assertFalse(is_trading_day(date(2026, 6, 19)))

    def test_thanksgiving_not_trading_day(self):
        self.assertFalse(is_trading_day(date(2026, 11, 26)))

    def test_market_open_during_hours(self):
        # Wednesday 2026-05-20 at 11:00 ET
        dt = datetime(2026, 5, 20, 11, 0, tzinfo=EASTERN)
        self.assertTrue(is_market_open(dt))

    def test_market_closed_before_open(self):
        # Wednesday at 08:00 ET — pre-market
        dt = datetime(2026, 5, 20, 8, 0, tzinfo=EASTERN)
        self.assertFalse(is_market_open(dt))

    def test_market_closed_after_close(self):
        # Wednesday at 17:00 ET — after hours
        dt = datetime(2026, 5, 20, 17, 0, tzinfo=EASTERN)
        self.assertFalse(is_market_open(dt))

    def test_market_closed_on_weekend(self):
        # Saturday at 11:00 ET
        dt = datetime(2026, 5, 23, 11, 0, tzinfo=EASTERN)
        self.assertFalse(is_market_open(dt))

    def test_market_open_at_open_bell(self):
        # Exactly 09:30 ET
        dt = datetime(2026, 5, 20, 9, 30, tzinfo=EASTERN)
        self.assertTrue(is_market_open(dt))

    def test_describe_market_state_returns_string(self):
        dt = datetime(2026, 5, 20, 11, 0, tzinfo=EASTERN)
        desc = describe_market_state(dt)
        self.assertIn("open", desc.lower())


if __name__ == "__main__":
    unittest.main()
