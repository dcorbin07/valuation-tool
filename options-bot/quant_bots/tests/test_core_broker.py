"""
Tests for the equity-order extension to the Tradier client (T1).
Mocked — no network.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import EquitySide, OrderType, TradierClient, TradierConfig


def make_client() -> TradierClient:
    cfg = TradierConfig(access_token="x", account_id="y", sandbox=True)
    return TradierClient(cfg)


class TestEquityOrder(unittest.TestCase):
    def test_market_buy_builds_correct_payload(self):
        client = make_client()
        captured = {}

        def fake_request(method, path, data=None, params=None):
            captured["method"] = method
            captured["path"] = path
            captured["data"] = data
            return {"order": {"id": 1, "status": "ok"}}

        client._request = fake_request
        resp = client.place_equity_order("spy", EquitySide.BUY, 100, preview=True)
        self.assertEqual(resp["status"], "ok")
        d = captured["data"]
        self.assertEqual(d["class"], "equity")
        self.assertEqual(d["symbol"], "SPY")        # uppercased
        self.assertEqual(d["side"], "buy")
        self.assertEqual(d["quantity"], "100")
        self.assertEqual(d["type"], "market")
        self.assertEqual(d["preview"], "true")

    def test_short_sell_side(self):
        client = make_client()
        client._request = MagicMock(return_value={"order": {"id": 2, "status": "ok"}})
        client.place_equity_order("TLT", EquitySide.SELL_SHORT, 50, preview=True)
        data = client._request.call_args.kwargs["data"]
        self.assertEqual(data["side"], "sell_short")

    def test_limit_order_includes_price(self):
        client = make_client()
        client._request = MagicMock(return_value={"order": {"id": 3, "status": "ok"}})
        client.place_equity_order("QQQ", EquitySide.BUY, 10,
                                  order_type=OrderType.LIMIT, price=400.25, preview=True)
        data = client._request.call_args.kwargs["data"]
        self.assertEqual(data["type"], "limit")
        self.assertEqual(data["price"], "400.25")

    def test_limit_without_price_raises(self):
        client = make_client()
        with self.assertRaises(ValueError):
            client.place_equity_order("QQQ", EquitySide.BUY, 10,
                                      order_type=OrderType.LIMIT)

    def test_zero_quantity_raises(self):
        client = make_client()
        with self.assertRaises(ValueError):
            client.place_equity_order("SPY", EquitySide.BUY, 0)

    def test_negative_quantity_raises(self):
        client = make_client()
        with self.assertRaises(ValueError):
            client.place_equity_order("SPY", EquitySide.BUY, -5)

    def test_all_four_sides_valid(self):
        client = make_client()
        client._request = MagicMock(return_value={"order": {"id": 1, "status": "ok"}})
        for side in (EquitySide.BUY, EquitySide.SELL,
                     EquitySide.SELL_SHORT, EquitySide.BUY_TO_COVER):
            client.place_equity_order("SPY", side, 10, preview=True)
            data = client._request.call_args.kwargs["data"]
            self.assertEqual(data["side"], side.value)


class TestCoreImports(unittest.TestCase):
    def test_core_exposes_shared_infra(self):
        import core
        # The lifted infrastructure should all be importable from core
        for name in ["AccountState", "TradeJournal", "DiscordNotifier",
                     "TradierClient", "is_trading_day", "now_eastern",
                     "EquitySide"]:
            self.assertTrue(hasattr(core, name), f"core missing {name}")


if __name__ == "__main__":
    unittest.main()
