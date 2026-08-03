"""
Tests for the cross-sectional momentum bot's distinctive logic:
the 12-1 score computation and the rank-and-select. Pure, no network.
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from momentum import (
    Direction,
    MomentumConfig,
    MomentumScore,
    MomentumStrategy,
    StrategyConfig,
    compute_score_from_closes,
    rank_and_select,
)


# ─── 12-1 score computation ─────────────────────────────────────────────────


class TestMomentumScore(unittest.TestCase):
    def _series(self, n, fn):
        return [fn(i) for i in range(n)]

    def test_strong_riser_has_high_score(self):
        # Steady riser → strong positive 12-1 momentum
        closes = self._series(300, lambda i: 100 * (1.002 ** i))
        s = compute_score_from_closes("WIN", closes, MomentumConfig())
        self.assertTrue(s.usable)
        self.assertGreater(s.score, 0)

    def test_faller_has_negative_score(self):
        closes = self._series(300, lambda i: 100 * (0.998 ** i))
        s = compute_score_from_closes("LOSE", closes, MomentumConfig())
        self.assertLess(s.score, 0)

    def test_skips_recent_month(self):
        # Build a series that rises for 11 months then crashes in the last month.
        # 12-1 momentum should still be POSITIVE because it ignores the last ~21 days.
        rise = [100 * (1.003 ** i) for i in range(279)]
        crash = [rise[-1] * (0.95 ** (j + 1)) for j in range(21)]
        closes = rise + crash
        s = compute_score_from_closes("X", closes, MomentumConfig())
        # The recent crash is excluded, so the 12-1 window still shows the rise
        self.assertGreater(s.score, 0)

    def test_insufficient_data_unusable(self):
        s = compute_score_from_closes("X", [100.0] * 100, MomentumConfig())
        self.assertFalse(s.usable)

    def test_volatility_computed(self):
        closes = [100 * (1.001 ** i) for i in range(300)]
        s = compute_score_from_closes("X", closes, MomentumConfig())
        self.assertGreater(s.annualized_vol, 0)


# ─── Rank and select ────────────────────────────────────────────────────────


def score(symbol, val, vol=0.2):
    return MomentumScore(symbol, val, vol, 100.0, 300, True)


class TestRankAndSelect(unittest.TestCase):
    def _universe(self):
        # 10 names with scores 0.0 .. 0.9
        return {f"S{i}": score(f"S{i}", i / 10.0) for i in range(10)}

    def test_top_n_long_bottom_n_short(self):
        cfg = MomentumConfig(long_count=3, short_count=3)
        sel = rank_and_select(self._universe(), cfg)
        long_syms = {s.symbol for s in sel.longs}
        short_syms = {s.symbol for s in sel.shorts}
        # Highest scores S9,S8,S7 long; lowest S0,S1,S2 short
        self.assertEqual(long_syms, {"S9", "S8", "S7"})
        self.assertEqual(short_syms, {"S0", "S1", "S2"})

    def test_long_only_when_short_count_zero(self):
        cfg = MomentumConfig(long_count=3, short_count=0)
        sel = rank_and_select(self._universe(), cfg)
        self.assertEqual(len(sel.longs), 3)
        self.assertEqual(len(sel.shorts), 0)

    def test_no_overlap_between_long_and_short(self):
        # Tiny universe where top-N and bottom-N could overlap
        small = {f"S{i}": score(f"S{i}", i / 10.0) for i in range(4)}
        cfg = MomentumConfig(long_count=3, short_count=3)
        sel = rank_and_select(small, cfg)
        long_syms = {s.symbol for s in sel.longs}
        short_syms = {s.symbol for s in sel.shorts}
        self.assertEqual(long_syms & short_syms, set())

    def test_unusable_excluded_from_ranking(self):
        u = self._universe()
        u["BAD"] = MomentumScore("BAD", 5.0, 0.2, 100.0, 300, False)  # huge score but unusable
        cfg = MomentumConfig(long_count=3, short_count=0)
        sel = rank_and_select(u, cfg)
        self.assertNotIn("BAD", {s.symbol for s in sel.longs})


# ─── Strategy weighting ─────────────────────────────────────────────────────


class TestMomentumStrategy(unittest.TestCase):
    def test_longs_positive_shorts_negative(self):
        from momentum.signals import RankedSelection
        sel = RankedSelection(
            longs=[score("A", 0.5, 0.2)],
            shorts=[score("B", -0.5, 0.2)],
        )
        target = MomentumStrategy(StrategyConfig()).build_target(sel)
        weights = {w.symbol: w.normalized_weight for w in target.weights}
        self.assertGreater(weights["A"], 0)
        self.assertLess(weights["B"], 0)

    def test_gross_normalizes_to_one(self):
        from momentum.signals import RankedSelection
        sel = RankedSelection(
            longs=[score("A", 0.5, 0.2), score("C", 0.4, 0.3)],
            shorts=[score("B", -0.5, 0.25)],
        )
        target = MomentumStrategy(StrategyConfig()).build_target(sel)
        gross = sum(abs(w.normalized_weight) for w in target.weights)
        self.assertAlmostEqual(gross, 1.0, places=6)

    def test_equal_weight_mode(self):
        from momentum.signals import RankedSelection
        sel = RankedSelection(
            longs=[score("A", 0.5, 0.10), score("C", 0.4, 0.40)],
            shorts=[],
        )
        target = MomentumStrategy(StrategyConfig(equal_weight=True)).build_target(sel)
        # Equal weight: both longs get the same absolute weight despite diff vol
        weights = {w.symbol: abs(w.normalized_weight) for w in target.weights}
        self.assertAlmostEqual(weights["A"], weights["C"], places=6)


if __name__ == "__main__":
    unittest.main()
