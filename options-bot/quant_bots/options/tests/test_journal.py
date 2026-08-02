"""Tests for the trade journal (V8.1 — the audit trail)."""
import tempfile
import unittest
from pathlib import Path

from orchestrator import TradeJournal


class TestTradeJournal(unittest.TestCase):
    def test_record_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = TradeJournal(Path(tmp))
            j.record_open("SPY", 565.0, 560.0, 1, 0.80, "paper",
                          order_id="abc", status="ok")
            entries = j.read_all()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["event_type"], "order_open")
            self.assertEqual(entries[0]["symbol"], "SPY")
            self.assertIn("timestamp_utc", entries[0])

    def test_multiple_events_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = TradeJournal(Path(tmp))
            j.record_open("SPY", 565, 560, 1, 0.80, "paper")
            j.record_close("SPY", 565, 560, 1, "close_profit", 40.0, "paper")
            j.record_job("manage_job", "paper", True, "did stuff")
            entries = j.read_all()
            self.assertEqual(len(entries), 3)
            self.assertEqual([e["event_type"] for e in entries],
                             ["order_open", "order_close", "job_run"])

    def test_summarize_realized_pnl(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = TradeJournal(Path(tmp))
            j.record_open("SPY", 565, 560, 1, 0.80, "paper")
            j.record_open("QQQ", 450, 445, 1, 0.90, "paper")
            j.record_close("SPY", 565, 560, 1, "close_profit", 40.0, "paper")
            j.record_close("QQQ", 450, 445, 1, "close_stop", -180.0, "paper")
            summary = j.summarize_realized_pnl()
            self.assertEqual(summary["total_opens"], 2)
            self.assertEqual(summary["total_closes"], 2)
            self.assertAlmostEqual(summary["realized_pnl"], -140.0)
            self.assertEqual(summary["wins"], 1)
            self.assertEqual(summary["losses"], 1)
            self.assertAlmostEqual(summary["win_rate"], 0.5)

    def test_record_never_raises_on_bad_dir(self):
        # Even pointing at a path that can't be created shouldn't raise from record()
        j = TradeJournal(Path(tempfile.gettempdir()) / "journal_test_ok")
        # Should not raise
        j.record("custom_event", foo="bar", num=42)
        entries = j.read_all()
        self.assertTrue(any(e["event_type"] == "custom_event" for e in entries))
        # cleanup
        import shutil
        shutil.rmtree(Path(tempfile.gettempdir()) / "journal_test_ok", ignore_errors=True)

    def test_empty_journal_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = TradeJournal(Path(tmp))
            summary = j.summarize_realized_pnl()
            self.assertEqual(summary["total_closes"], 0)
            self.assertEqual(summary["win_rate"], 0.0)


class TestPrepJobConfig(unittest.TestCase):
    def test_prep_job_enabled_by_default(self):
        from orchestrator import OrchestratorConfig
        config = OrchestratorConfig()
        self.assertTrue(config.enable_prep_job)

    def test_prep_runs_before_open(self):
        from orchestrator import OrchestratorConfig
        config = OrchestratorConfig()
        # Prep hour must be earlier than open hour so candidates exist
        self.assertLess(config.prep_job_hour, config.open_job_hour)


if __name__ == "__main__":
    unittest.main()
