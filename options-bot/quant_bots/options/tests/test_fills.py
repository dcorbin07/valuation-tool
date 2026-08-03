"""
Tests for order fill confirmation (broker.wait_for_fill).
Uses a mocked Tradier client — no network.
"""
import unittest
from unittest.mock import MagicMock

from broker import TradierClient, TradierConfig


def make_client() -> TradierClient:
    cfg = TradierConfig(access_token="x", account_id="y", sandbox=True)
    client = TradierClient(cfg)
    return client


class TestWaitForFill(unittest.TestCase):
    def test_returns_immediately_when_filled(self):
        client = make_client()
        client.get_order = MagicMock(return_value={"id": 1, "status": "filled",
                                                    "avg_fill_price": 0.80})
        result = client.wait_for_fill(1, max_wait_secs=10, poll_interval_secs=0.01)
        self.assertEqual(result["status"], "filled")
        # Should have polled exactly once since it was already terminal
        self.assertEqual(client.get_order.call_count, 1)

    def test_returns_on_rejected(self):
        client = make_client()
        client.get_order = MagicMock(return_value={"id": 1, "status": "rejected"})
        result = client.wait_for_fill(1, max_wait_secs=10, poll_interval_secs=0.01)
        self.assertEqual(result["status"], "rejected")

    def test_polls_until_filled(self):
        client = make_client()
        # First two polls "open", third "filled"
        client.get_order = MagicMock(side_effect=[
            {"id": 1, "status": "open"},
            {"id": 1, "status": "open"},
            {"id": 1, "status": "filled"},
        ])
        result = client.wait_for_fill(1, max_wait_secs=10, poll_interval_secs=0.01)
        self.assertEqual(result["status"], "filled")
        self.assertEqual(client.get_order.call_count, 3)

    def test_times_out_still_open(self):
        client = make_client()
        client.get_order = MagicMock(return_value={"id": 1, "status": "open"})
        # Very short wait so the loop exits quickly
        result = client.wait_for_fill(1, max_wait_secs=0.05, poll_interval_secs=0.01)
        # Returns the last-seen (non-terminal) state
        self.assertEqual(result["status"], "open")

    def test_handles_get_order_error(self):
        from broker import TradierError
        client = make_client()
        client.get_order = MagicMock(side_effect=TradierError("boom"))
        result = client.wait_for_fill(1, max_wait_secs=5, poll_interval_secs=0.01)
        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
