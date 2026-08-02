"""
Tests for the notify layer (Discord notifier + LLM advisor).

No network required — Discord sends are tested in "disabled" mode (no webhook),
and the advisor is tested with stub advise_fn callables.
"""
import unittest

from notify import (
    Advisory,
    AdvisorySignal,
    DiscordNotifier,
    LLMAdvisor,
)


# ─── Discord notifier ───────────────────────────────────────────────────────


class TestDiscordNotifier(unittest.TestCase):
    def test_disabled_without_webhook(self):
        n = DiscordNotifier(webhook_url=None)
        self.assertFalse(n.enabled)

    def test_disabled_send_returns_false_but_no_raise(self):
        n = DiscordNotifier(webhook_url=None)
        # Should log and return False, never raise
        self.assertFalse(n.send("hello"))
        self.assertFalse(n.send_embed("title", "desc"))

    def test_enabled_with_webhook(self):
        n = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/xxx/yyy")
        self.assertTrue(n.enabled)

    def test_notify_job_result_disabled_no_raise(self):
        # A fake JobResult-like object
        class FakeResult:
            job_name = "open_job"
            mode = "preview_only"
            success = True
            summary = "Previewed 3 orders"
            error = None
            details = {
                "placed": [
                    {"symbol": "SPY", "contracts": 1, "credit": 0.80},
                    {"symbol": "QQQ", "contracts": 1, "credit": 0.90},
                ],
                "failed": [],
                "account_value": 25000.0,
            }
        n = DiscordNotifier(webhook_url=None)
        # Disabled → returns False, logs, never raises
        self.assertFalse(n.notify_job_result(FakeResult()))

    def test_notify_manage_result_disabled_no_raise(self):
        class FakeResult:
            job_name = "manage_job"
            mode = "paper"
            success = True
            summary = "Closed 1 spread"
            error = None
            details = {
                "open_spreads": 5,
                "total_pnl": 230.0,
                "closed": [{"symbol": "NVDA", "decision": "close_profit", "pnl": 60.0}],
            }
        n = DiscordNotifier(webhook_url=None)
        self.assertFalse(n.notify_job_result(FakeResult()))


# ─── LLM advisor ────────────────────────────────────────────────────────────


class TestLLMAdvisor(unittest.TestCase):
    def test_disabled_without_fn(self):
        advisor = LLMAdvisor(advise_fn=None)
        self.assertFalse(advisor.enabled)
        result = advisor.review_symbol("SPY")
        self.assertEqual(result.signal, AdvisorySignal.UNAVAILABLE)

    def test_parses_no_concern(self):
        def stub(symbol):
            return (
                "SIGNAL: NO_CONCERN\n"
                "EVENTS: NONE\n"
                "REASONING: No specific binary events found for this ticker."
            )
        advisor = LLMAdvisor(advise_fn=stub)
        result = advisor.review_symbol("AAPL")
        self.assertEqual(result.signal, AdvisorySignal.NO_CONCERN)
        self.assertEqual(result.flagged_events, [])
        self.assertFalse(result.is_concern)

    def test_parses_concern_with_events(self):
        def stub(symbol):
            return (
                "SIGNAL: CONCERN\n"
                "EVENTS: pending FDA decision, clinical trial readout\n"
                "REASONING: PDUFA date in 3 weeks could cause a large gap."
            )
        advisor = LLMAdvisor(advise_fn=stub)
        result = advisor.review_symbol("BIIB")
        self.assertEqual(result.signal, AdvisorySignal.CONCERN)
        self.assertTrue(result.is_concern)
        self.assertIn("pending FDA decision", result.flagged_events)
        self.assertEqual(len(result.flagged_events), 2)

    def test_events_listed_forces_concern(self):
        # Even if SIGNAL line says NO_CONCERN, listed events => concern
        def stub(symbol):
            return (
                "SIGNAL: NO_CONCERN\n"
                "EVENTS: announced merger\n"
                "REASONING: Acquisition pending."
            )
        advisor = LLMAdvisor(advise_fn=stub)
        result = advisor.review_symbol("ATVI")
        self.assertEqual(result.signal, AdvisorySignal.CONCERN)

    def test_advise_fn_exception_yields_unavailable(self):
        def stub(symbol):
            raise RuntimeError("API down")
        advisor = LLMAdvisor(advise_fn=stub)
        result = advisor.review_symbol("SPY")
        self.assertEqual(result.signal, AdvisorySignal.UNAVAILABLE)

    def test_empty_response_yields_unavailable(self):
        def stub(symbol):
            return ""
        advisor = LLMAdvisor(advise_fn=stub)
        result = advisor.review_symbol("SPY")
        self.assertEqual(result.signal, AdvisorySignal.UNAVAILABLE)

    def test_review_orders_batch(self):
        def stub(symbol):
            if symbol == "BIIB":
                return "SIGNAL: CONCERN\nEVENTS: FDA decision\nREASONING: PDUFA soon."
            return "SIGNAL: NO_CONCERN\nEVENTS: NONE\nREASONING: Clear."
        advisor = LLMAdvisor(advise_fn=stub)
        results = advisor.review_orders(["SPY", "BIIB", "QQQ"])
        self.assertEqual(len(results), 3)
        self.assertFalse(results["SPY"].is_concern)
        self.assertTrue(results["BIIB"].is_concern)
        self.assertFalse(results["QQQ"].is_concern)

    def test_advisory_never_blocks(self):
        """
        The advisor returns records but has no mechanism to block. This test
        documents that contract: review_orders returns advisories, full stop.
        There is no 'approved' or 'rejected' field, no filtering of orders.
        """
        def stub(symbol):
            return "SIGNAL: CONCERN\nEVENTS: halt\nREASONING: Halted."
        advisor = LLMAdvisor(advise_fn=stub)
        results = advisor.review_orders(["XYZ"])
        # The advisory exists and flags concern...
        self.assertTrue(results["XYZ"].is_concern)
        # ...but it's just an Advisory record. No blocking API exists.
        self.assertIsInstance(results["XYZ"], Advisory)


if __name__ == "__main__":
    unittest.main()
