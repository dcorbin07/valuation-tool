"""
Regression tests for the regime-gate exposure bug.

THE BUG: momentum and reversion suppress their SHORTS when SPY is above its
200-day MA. build_target() then gross-normalized to 1.0 over the SURVIVING
longs — so removing the short book didn't shrink the position, it DOUBLED the
long one. Net weight went from ~0.00 to +1.00.

Both strategies are documented as dollar-neutral-ish. Whenever SPY was above
its 200-day MA — which is most days of most years — they were instead running
100% net long, single-sided equity beta, and nothing in the code, the logs or
the README acknowledged it. The `max_net_exposure` cap could not catch it
either: with max_gross_exposure = 1.0 forcing vol_scale <= 1.0, the net check
was unreachable dead code.

The fix normalizes by the PRE-suppression denominator, so the longs keep the
share of the book they would have had and the shorts' capital stays
undeployed. Suppression now REDUCES exposure, which is the whole point of a
risk gate.
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from momentum.signals import MomentumScore
from momentum.signals import RankedSelection as MomSelection
from momentum.strategy import MomentumStrategy
from momentum.strategy import StrategyConfig as MomStrategyConfig
from reversion.signals import RankedSelection as RevSelection, ReversionScore
from reversion.strategy import MeanReversionStrategy
from reversion.strategy import StrategyConfig as RevStrategyConfig


class _SuppressionContract:
    """Both bots must satisfy the same exposure contract."""

    def _both(self, n_long, n_short):
        """Returns (ungated_target, gated_target)."""
        longs, shorts = self._names(n_long, n_short)
        st = self._strategy()
        return (st.build_target(self._selection(longs, shorts, [])),
                st.build_target(self._selection(longs, [], shorts)))

    def test_ungated_book_is_roughly_dollar_neutral(self):
        full, _ = self._both(20, 20)
        self.assertAlmostEqual(full.gross_weight(), 1.0, places=2)
        self.assertAlmostEqual(full.net_weight(), 0.0, places=2)

    def test_suppressing_shorts_halves_gross_instead_of_doubling_longs(self):
        _, gated = self._both(20, 20)
        self.assertAlmostEqual(gated.gross_weight(), 0.5, places=2)
        self.assertAlmostEqual(gated.net_weight(), 0.5, places=2)

    def test_net_never_reaches_fully_long(self):
        """The specific failure: net used to be +1.00 on every risk-on day."""
        _, gated = self._both(20, 20)
        self.assertLess(
            gated.net_weight(), 0.99,
            "regime gate produced a 100% net long book — the bug is back")

    def test_long_weights_are_identical_gated_or_not(self):
        """
        The longs must not change AT ALL when shorts are suppressed. That is
        the whole idea: we withhold the shorts' capital, we do not redeploy it.
        """
        full, gated = self._both(20, 20)
        full_longs = {w.symbol: w.normalized_weight
                      for w in full.weights if w.normalized_weight > 0}
        gated_longs = {w.symbol: w.normalized_weight for w in gated.weights}
        self.assertEqual(set(full_longs), set(gated_longs))
        for sym, w in full_longs.items():
            self.assertAlmostEqual(gated_longs[sym], w, places=6)

    def test_suppressed_weight_is_reported(self):
        _, gated = self._both(20, 20)
        self.assertAlmostEqual(gated.suppressed_gross_weight, 0.5, places=2)

    def test_partial_suppression_scales_proportionally(self):
        """5 suppressed of 25 total → about 20% withheld."""
        longs, shorts = self._names(20, 5)
        gated = self._strategy().build_target(self._selection(longs, [], shorts))
        self.assertAlmostEqual(gated.suppressed_gross_weight, 0.2, places=2)
        self.assertAlmostEqual(gated.gross_weight(), 0.8, places=2)

    def test_nothing_suppressed_leaves_the_book_unchanged(self):
        longs, _ = self._names(20, 0)
        t = self._strategy().build_target(self._selection(longs, [], []))
        self.assertAlmostEqual(t.gross_weight(), 1.0, places=2)
        self.assertEqual(t.suppressed_gross_weight, 0.0)

    def test_empty_selection_does_not_divide_by_zero(self):
        t = self._strategy().build_target(self._selection([], [], []))
        self.assertEqual(t.weights, [])
        self.assertEqual(t.gross_weight(), 0.0)


class TestMomentumSuppression(_SuppressionContract, unittest.TestCase):
    def _strategy(self):
        return MomentumStrategy(MomStrategyConfig())

    def _names(self, n_long, n_short):
        mk = lambda s, sc: MomentumScore(s, sc, 0.20, 100.0, 300, True)
        return ([mk(f"L{i}", 0.40) for i in range(n_long)],
                [mk(f"S{i}", -0.40) for i in range(n_short)])

    def _selection(self, longs, shorts, suppressed):
        return MomSelection(longs=longs, shorts=shorts, suppressed_shorts=suppressed)


class TestReversionSuppression(_SuppressionContract, unittest.TestCase):
    def _strategy(self):
        return MeanReversionStrategy(RevStrategyConfig())

    def _names(self, n_long, n_short):
        mk = lambda s, z: ReversionScore(s, z, -z, 0.20, 100.0, 100, True)
        return ([mk(f"L{i}", -2.0) for i in range(n_long)],
                [mk(f"S{i}", 2.0) for i in range(n_short)])

    def _selection(self, longs, shorts, suppressed):
        return RevSelection(longs=longs, shorts=shorts, suppressed_shorts=suppressed)


class TestOrchestratorsPopulateSuppressedShorts(unittest.TestCase):
    """
    The strategy fix is inert unless the orchestrator actually hands over the
    shorts it removed. It previously just did `selection.shorts = []`, throwing
    them away — so the denominator had nothing to count and the fix would have
    silently done nothing.
    """

    def _assert_hands_over(self, source):
        text = (PROJECT_ROOT / source).read_text()
        self.assertIn("suppressed_shorts = list(selection.shorts)", text,
                      f"{source} discards the suppressed shorts instead of "
                      f"passing them to build_target")
        gate = text.index("selection.suppressed_shorts")
        clear = text.index("selection.shorts = []", gate)
        self.assertLess(gate, clear,
                        f"{source} clears shorts before capturing them")

    def test_momentum_orchestrator(self):
        self._assert_hands_over("momentum/orchestrator.py")

    def test_reversion_orchestrator(self):
        self._assert_hands_over("reversion/orchestrator.py")


if __name__ == "__main__":
    unittest.main()
