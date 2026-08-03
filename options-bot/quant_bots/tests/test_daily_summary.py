"""Tests for the end-of-day summary builder."""
import json, sys, tempfile, unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import build_summaries, post_end_of_day, summarize_bot


def _write_curve(root, bot, rows):
    d = root / "data" / "sim" / bot
    d.mkdir(parents=True)
    with (d / "equity_curve.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class _CapturingNotifier:
    """Stand-in for DiscordNotifier that records what it would send."""
    def __init__(self): self.sent = []
    def send(self, content): self.sent.append(("text", content)); return True
    def send_embed(self, title, description, color=0, fields=None):
        self.sent.append(("embed", title, description, fields)); return True


class TestDailySummary(unittest.TestCase):
    def test_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = summarize_bot(root, "trend")
            self.assertFalse(s.has_data)

    def test_day_return_computed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_curve(root, "trend", [
                {"date": "2026-05-01", "equity": 100000, "return_since_start": 0.0,
                 "num_positions": 10, "realized_pnl": 0},
                {"date": "2026-05-02", "equity": 101000, "return_since_start": 0.01,
                 "num_positions": 10, "realized_pnl": 0},
            ])
            s = summarize_bot(root, "trend")
            self.assertTrue(s.has_data)
            self.assertAlmostEqual(s.day_return, 0.01, places=4)
            self.assertAlmostEqual(s.total_return, 0.01, places=4)

    def test_post_sends_embed_when_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_curve(root, "trend", [
                {"date": "2026-05-01", "equity": 100000, "return_since_start": 0.0,
                 "num_positions": 5, "realized_pnl": 0},
                {"date": "2026-05-02", "equity": 102000, "return_since_start": 0.02,
                 "num_positions": 5, "realized_pnl": 0},
            ])
            n = _CapturingNotifier()
            post_end_of_day(n, root, bots=["trend", "momentum", "options"])
            self.assertEqual(n.sent[0][0], "embed")
            # Only trend had data → one field
            self.assertEqual(len(n.sent[0][3]), 1)

    def test_post_text_when_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            n = _CapturingNotifier()
            post_end_of_day(n, root, bots=["trend"])
            self.assertEqual(n.sent[0][0], "text")


if __name__ == "__main__":
    unittest.main()
