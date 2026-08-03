"""
Tests for the mean-reversion bot signals.
The critical thing to verify: oversold names (price below recent mean, negative
z) get selected LONG, and overbought names (positive z) get selected SHORT —
the OPPOSITE of momentum.
"""
import sys, unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from reversion.signals import (
    MeanReversionConfig, compute_score_from_closes, rank_and_select, Direction,
)


def flat_then_drop(base=100.0, n=90, drop_pct=0.15):
    """A series that's flat then drops sharply at the end → oversold (neg z)."""
    prices = [base] * (n - 5)
    last = base
    for _ in range(5):
        last *= (1 - drop_pct / 5)
        prices.append(last)
    return prices


def flat_then_spike(base=100.0, n=90, up_pct=0.15):
    """Flat then spikes up at the end → overbought (pos z)."""
    prices = [base] * (n - 5)
    last = base
    for _ in range(5):
        last *= (1 + up_pct / 5)
        prices.append(last)
    return prices


class TestReversionSignal(unittest.TestCase):
    def test_oversold_has_negative_zscore_and_positive_score(self):
        cfg = MeanReversionConfig()
        s = compute_score_from_closes("DROP", flat_then_drop(), cfg)
        self.assertTrue(s.usable)
        self.assertLess(s.zscore, 0)        # price below recent mean
        self.assertGreater(s.score, 0)      # score = -z → positive → ranks LONG

    def test_overbought_has_positive_zscore_and_negative_score(self):
        cfg = MeanReversionConfig()
        s = compute_score_from_closes("SPIKE", flat_then_spike(), cfg)
        self.assertTrue(s.usable)
        self.assertGreater(s.zscore, 0)     # price above recent mean
        self.assertLess(s.score, 0)         # score = -z → negative → ranks SHORT

    def test_insufficient_history_unusable(self):
        cfg = MeanReversionConfig()
        s = compute_score_from_closes("SHORT", [100.0] * 30, cfg)
        self.assertFalse(s.usable)

    def test_selection_longs_oversold_shorts_overbought(self):
        cfg = MeanReversionConfig(long_count=2, short_count=2, min_abs_zscore=0.5)
        scores = {
            "DROP1": compute_score_from_closes("DROP1", flat_then_drop(drop_pct=0.20), cfg),
            "DROP2": compute_score_from_closes("DROP2", flat_then_drop(drop_pct=0.15), cfg),
            "SPIKE1": compute_score_from_closes("SPIKE1", flat_then_spike(up_pct=0.20), cfg),
            "SPIKE2": compute_score_from_closes("SPIKE2", flat_then_spike(up_pct=0.15), cfg),
        }
        sel = rank_and_select(scores, cfg)
        long_syms = {s.symbol for s in sel.longs}
        short_syms = {s.symbol for s in sel.shorts}
        # The dropped names should be long (oversold), spiked names short (overbought)
        self.assertTrue(long_syms.issubset({"DROP1", "DROP2"}))
        self.assertTrue(short_syms.issubset({"SPIKE1", "SPIKE2"}))

    def test_min_zscore_filters_noise(self):
        # A nearly-flat series has |z| ~ 0 and should be filtered out
        cfg = MeanReversionConfig(min_abs_zscore=1.0)
        flat = [100.0 + (i % 2) * 0.01 for i in range(90)]
        scores = {"FLAT": compute_score_from_closes("FLAT", flat, cfg)}
        sel = rank_and_select(scores, cfg)
        self.assertEqual(len(sel.longs) + len(sel.shorts), 0)


if __name__ == "__main__":
    unittest.main()
