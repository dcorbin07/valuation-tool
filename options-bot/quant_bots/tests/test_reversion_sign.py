"""
Regression tests for the mean-reversion sign-partition bug.

THE BUG: rank_and_select() filtered the pool on |z| >= min_abs_zscore, sorted
the WHOLE pool by score, then took the top N as longs and the bottom N as
shorts. Nothing required a short to have z > 0.

In a market-wide selloff every name has z < 0, so the "bottom" of the pool is
the LEAST oversold name — which is still oversold. The bot therefore SHORTED
names it had itself just classified as oversold, in exactly the fat-left-tail
scenario this strategy is most exposed to. Instead of hedging, it doubled the
directional loss.

The fix partitions by sign first. The cost is a lopsided book on skewed days,
which is the honest answer: there genuinely were no overbought names.
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from reversion import MeanReversionConfig, rank_and_select
from reversion.signals import ReversionScore


def _score(sym, z, price=100.0, vol=0.20):
    return ReversionScore(symbol=sym, zscore=z, score=-z, annualized_vol=vol,
                          last_price=price, bars_used=100, usable=True)


def _pool(zs):
    return {f"S{i}": _score(f"S{i}", z) for i, z in enumerate(zs)}


class TestSignPartition(unittest.TestCase):
    def test_broad_selloff_never_shorts_an_oversold_name(self):
        """THE regression. Every name oversold → zero shorts, not 20."""
        zs = [-3.65 + i * 0.05 for i in range(50)]      # all in [-3.65, -1.20]
        self.assertTrue(all(z < 0 for z in zs))
        sel = rank_and_select(_pool(zs), MeanReversionConfig())

        self.assertEqual(len(sel.shorts), 0,
                         f"shorted oversold names: {[(s.symbol, s.zscore) for s in sel.shorts]}")
        self.assertEqual(len(sel.longs), 20)
        self.assertTrue(all(s.zscore < 0 for s in sel.longs))

    def test_broad_rally_never_longs_an_overbought_name(self):
        """The mirror case: everything overbought → zero longs."""
        zs = [1.20 + i * 0.05 for i in range(50)]
        sel = rank_and_select(_pool(zs), MeanReversionConfig())

        self.assertEqual(len(sel.longs), 0,
                         f"bought overbought names: {[(s.symbol, s.zscore) for s in sel.longs]}")
        self.assertEqual(len(sel.shorts), 20)
        self.assertTrue(all(s.zscore > 0 for s in sel.shorts))

    def test_every_long_is_oversold_and_every_short_is_overbought(self):
        """The invariant that should hold on ANY cross-section."""
        zs = [-4.0, -3.0, -2.5, -2.0, -1.5, -1.2, 1.1, 1.4, 2.0, 2.6, 3.3]
        sel = rank_and_select(_pool(zs), MeanReversionConfig())

        for s in sel.longs:
            self.assertLess(s.zscore, 0, f"{s.symbol} is not oversold")
        for s in sel.shorts:
            self.assertGreater(s.zscore, 0, f"{s.symbol} is not overbought")

    def test_picks_the_most_extreme_names_from_each_side(self):
        zs = [-4.0, -3.0, -2.0, -1.5, 1.5, 2.0, 3.0, 4.0]
        cfg = MeanReversionConfig(long_count=2, short_count=2)
        sel = rank_and_select(_pool(zs), cfg)

        self.assertEqual([round(s.zscore, 1) for s in sel.longs], [-4.0, -3.0])
        self.assertEqual([round(s.zscore, 1) for s in sel.shorts], [4.0, 3.0])

    def test_min_abs_zscore_still_gates_the_pool(self):
        zs = [-0.5, -0.2, 0.3, 0.7]                     # nothing past |z| >= 1.0
        sel = rank_and_select(_pool(zs), MeanReversionConfig())
        self.assertEqual(len(sel.longs), 0)
        self.assertEqual(len(sel.shorts), 0)

    def test_a_name_is_never_both_long_and_short(self):
        zs = [-2.0, 2.0]
        cfg = MeanReversionConfig(long_count=20, short_count=20)
        sel = rank_and_select(_pool(zs), cfg)
        self.assertEqual(set(s.symbol for s in sel.longs)
                         & set(s.symbol for s in sel.shorts), set())

    def test_unusable_scores_are_excluded(self):
        pool = _pool([-2.0, -2.5])
        pool["DEAD"] = ReversionScore(symbol="DEAD", zscore=-9.0, score=9.0,
                                      annualized_vol=0.0, last_price=10.0,
                                      bars_used=100, usable=False)
        sel = rank_and_select(pool, MeanReversionConfig())
        self.assertNotIn("DEAD", [s.symbol for s in sel.longs])

    def test_short_count_zero_disables_shorts(self):
        sel = rank_and_select(_pool([-2.0, 2.0]),
                              MeanReversionConfig(short_count=0))
        self.assertEqual(len(sel.shorts), 0)


class TestAllPricesCarriesTheWholeUniverse(unittest.TestCase):
    """
    all_prices must cover every scored name, not just the selected ones —
    that is what lets the orchestrator price an EXIT on a name that has since
    dropped out of the selection.
    """

    def test_includes_names_that_were_not_selected(self):
        pool = {f"S{i}": _score(f"S{i}", -3.0 + i * 0.1, price=10.0 + i)
                for i in range(40)}
        cfg = MeanReversionConfig(long_count=2, short_count=2)
        sel = rank_and_select(pool, cfg)

        selected = {s.symbol for s in sel.longs + sel.shorts}
        self.assertLess(len(selected), len(pool))
        for sym in pool:
            self.assertIn(sym, sel.all_prices,
                          f"{sym} was scored but has no price for an exit")

    def test_excludes_zero_prices(self):
        pool = _pool([-2.0])
        pool["ZERO"] = _score("ZERO", -2.5, price=0.0)
        sel = rank_and_select(pool, MeanReversionConfig())
        self.assertNotIn("ZERO", sel.all_prices)


if __name__ == "__main__":
    unittest.main()
