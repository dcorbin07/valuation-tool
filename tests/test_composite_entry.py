"""U1 — pins the composite-entry grid, the join, the arms and the null (options bot, 2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

What these pin is the set of things that could make U1 silently wrong rather than loudly broken:
that the entry join reaches BACKWARD only, that the arm bounds are the pre-registered ones, that
a null draw reproduces the arm's per-date shape exactly and its cap-tier histogram when asked,
and — the load-bearing one — that the bar is computable from an arm's SHAPE with no access to
the arm's P&L, which is what makes committing the bar before the score meaningful rather than
ceremonial.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import composite_entry as CE       # noqa: E402


def _row(asof, tk, pct, pnl, tier="mega"):
    return {"asof": asof, "ticker": tk, "u1_pct_univ": pct, "pnl_pct": pnl,
            "cap_tier": tier, "alert_ts": asof}


def _grid(n_per_date=20, dates=("2020-01-22", "2020-04-22", "2020-07-22")):
    rows = []
    for d in dates:
        for i in range(n_per_date):
            rows.append(_row(d, "T%02d" % i, i / (n_per_date - 1), 0.10 * i - 0.5,
                             tier=("mega" if i % 2 == 0 else "large")))
    return rows


class TheEntryJoinReachesBackwardOnly(unittest.TestCase):
    """The one defect that would flatter every U1 number: scoring an entry with a composite from
    a rebalance that had not happened yet. `entry_day_after` must be STRICTLY after."""

    def test_the_entry_day_is_strictly_after_the_rebalance(self):
        bars = ["2020-01-21", "2020-01-22", "2020-01-23", "2020-01-24"]
        got = CE.entry_day_after(bars, "2020-01-22", "2025-10-15")
        self.assertEqual(got, "2020-01-23")
        self.assertGreater(got, "2020-01-22")

    def test_a_rebalance_on_a_non_trading_day_still_steps_forward(self):
        bars = ["2020-01-21", "2020-01-24"]
        self.assertEqual(CE.entry_day_after(bars, "2020-01-22", "2025-10-15"), "2020-01-24")

    def test_it_refuses_to_walk_past_the_cache_window(self):
        bars = ["2025-10-14", "2025-10-16"]
        self.assertIsNone(CE.entry_day_after(bars, "2025-10-15", "2025-10-15"))

    def test_it_returns_none_rather_than_the_last_day_when_exhausted(self):
        self.assertIsNone(CE.entry_day_after(["2020-01-21"], "2020-06-01", "2025-10-15"))

    def test_grid_cells_never_emit_an_entry_on_or_before_its_own_asof(self):
        by_date = {"2020-01-22": {"AAA": (1.0, 0.9)}, "2020-04-22": {"AAA": (2.0, 0.5)}}
        bars = {"AAA": ["2020-01-22", "2020-01-23", "2020-04-22", "2020-04-23"]}
        cells = CE.grid_cells(by_date, bars, "2016-01-01", "2025-10-15")
        self.assertEqual(len(cells), 2)
        for c in cells:
            self.assertGreater(c["entry"], c["asof"])


class TheSplitFilterExcludesOnADateNotOnAReturn(unittest.TestCase):
    """U1-SPLIT (register section 10). Option chains are as-traded and unadjusted; bars are
    adjusted. GE's 1-for-8 on 2021-08-02 turned a $0.27 call into a +31,921% 'winner' worth
    6.28pp of the whole grid's mean.

    The property that matters is not that it drops that row — it is that it drops it for the
    RIGHT REASON. An exclusion keyed on the size of a return would be selecting on the outcome,
    which is the single thing a null exists to forbid."""

    SPL = {"GE": [("2021-08-02", 0.125)], "AAPL": [("2020-08-31", 4.0)]}

    def _t(self, tk, entry, expiry, pnl=0.0):
        return {"ticker": tk, "alert_ts": entry, "expiry": expiry, "pnl_pct": pnl}

    def test_a_trade_whose_life_crosses_a_split_is_dropped(self):
        r = self._t("GE", "2021-07-23", "2021-09-17", 319.21)
        self.assertTrue(CE.spans_split(r, self.SPL))

    def test_a_trade_that_expires_before_the_split_is_kept(self):
        r = self._t("GE", "2021-06-01", "2021-07-16", 0.4)
        self.assertFalse(CE.spans_split(r, self.SPL))

    def test_a_trade_that_starts_after_the_split_is_kept(self):
        r = self._t("GE", "2021-08-03", "2021-10-15", 0.4)
        self.assertFalse(CE.spans_split(r, self.SPL))

    def test_the_split_day_itself_counts_as_inside_the_window(self):
        self.assertTrue(CE.spans_split(self._t("GE", "2021-07-30", "2021-08-02"), self.SPL))

    def test_a_name_with_no_split_is_never_dropped_however_large_its_return(self):
        """The decisive test: a +50,000% return on a split-free name SURVIVES. If this ever
        fails, the filter has started keying on magnitude and is selecting on the outcome."""
        r = self._t("ZZZZ", "2020-01-02", "2020-03-20", 500.0)
        self.assertFalse(CE.spans_split(r, self.SPL))

    def test_a_tiny_return_on_a_split_crossing_name_is_still_dropped(self):
        """The mirror: the filter is blind to P&L in both directions."""
        r = self._t("AAPL", "2020-07-23", "2020-09-18", 0.001)
        self.assertTrue(CE.spans_split(r, self.SPL))

    def test_drop_split_spanners_partitions_without_loss(self):
        rows = [self._t("GE", "2021-07-23", "2021-09-17"),
                self._t("ZZZZ", "2021-07-23", "2021-09-17"),
                self._t("AAPL", "2020-07-23", "2020-09-18")]
        kept, dropped = CE.drop_split_spanners(rows, self.SPL)
        self.assertEqual(len(kept) + len(dropped), len(rows))
        self.assertEqual([r["ticker"] for r in dropped], ["GE", "AAPL"])
        self.assertEqual([r["ticker"] for r in kept], ["ZZZZ"])

    def test_a_row_missing_its_expiry_is_not_silently_dropped(self):
        self.assertFalse(CE.spans_split({"ticker": "GE", "alert_ts": "2021-07-23"}, self.SPL))


class TheArmBoundsAreThePreRegisteredOnes(unittest.TestCase):
    """`PREREG_u1_composite_entry.md` section 4 fixes three arms. If these drift, the register
    and the code disagree and the register is the authority."""

    def test_the_three_arms_and_their_cuts(self):
        self.assertEqual(sorted(CE.ARMS), ["BOT10", "TOP10", "TOP20"])
        self.assertAlmostEqual(CE.ARMS["TOP10"][0], 0.90)
        self.assertAlmostEqual(CE.ARMS["TOP20"][0], 0.80)
        self.assertAlmostEqual(CE.ARMS["BOT10"][1], 0.10)

    def test_select_respects_its_bounds(self):
        rows = _grid(n_per_date=11)
        top = CE.select(rows, *CE.ARMS["TOP10"])
        self.assertTrue(top)
        for r in top:
            self.assertGreaterEqual(r["u1_pct_univ"], 0.90)
        bot = CE.select(rows, *CE.ARMS["BOT10"])
        for r in bot:
            self.assertLess(r["u1_pct_univ"], 0.10)
        self.assertFalse(set(id(x) for x in top) & set(id(x) for x in bot))

    def test_a_row_with_no_percentile_is_never_selected(self):
        rows = [_row("2020-01-22", "X", None, 0.5)]
        self.assertEqual(CE.select(rows, *CE.ARMS["TOP10"]), [])


class TheNullReproducesTheArmsShapeExactly(unittest.TestCase):
    """Date composition held fixed is the whole reason a gain cannot come from picking better
    quarters. A null that drew a different number of cells per date would measure the calendar."""

    def test_a_draw_takes_the_same_count_on_every_date(self):
        grid = _grid()
        arm = CE.select(grid, *CE.ARMS["TOP20"])
        counts, _ = CE.arm_shape(arm, match_tier=False)
        pool = {}
        for r in grid:
            pool.setdefault(r["asof"], []).append(r)
        drawn, _sf = CE.draw_null(pool, counts, seed=7)
        self.assertEqual(CE.by_date_counts(drawn), counts)

    def test_draws_are_seeded_and_reproducible_and_differ_across_seeds(self):
        grid = _grid()
        arm = CE.select(grid, *CE.ARMS["TOP20"])
        counts, _ = CE.arm_shape(arm, match_tier=False)
        pool = {}
        for r in grid:
            pool.setdefault(r["asof"], []).append(r)
        a, _ = CE.draw_null(pool, counts, seed=3)
        b, _ = CE.draw_null(pool, counts, seed=3)
        c, _ = CE.draw_null(pool, counts, seed=4)
        self.assertEqual([id(x) for x in a], [id(x) for x in b])
        self.assertNotEqual(sorted(id(x) for x in a), sorted(id(x) for x in c))

    def test_a_draw_never_repeats_a_cell_within_a_date(self):
        grid = _grid()
        counts = {"2020-01-22": 20}
        pool = {"2020-01-22": [r for r in grid if r["asof"] == "2020-01-22"]}
        drawn, _ = CE.draw_null(pool, counts, seed=1)
        self.assertEqual(len(drawn), len({id(x) for x in drawn}))

    def test_the_cap_matched_null_reproduces_the_tier_histogram(self):
        """The ledger's reopen condition. A matched null that quietly stops matching is worse
        than an unmatched one, because it still calls itself matched."""
        grid = _grid(n_per_date=20)
        arm = CE.select(grid, *CE.ARMS["TOP20"])
        counts, tiers = CE.arm_shape(arm, match_tier=True)
        pool = {}
        for r in grid:
            pool.setdefault(r["asof"], []).append(r)
        drawn, shortfall = CE.draw_null(pool, counts, seed=11, tier_targets=tiers)
        self.assertEqual(shortfall, 0)
        got = {}
        for r in drawn:
            got.setdefault(r["asof"], {})
            got[r["asof"]][r["cap_tier"]] = got[r["asof"]].get(r["cap_tier"], 0) + 1
        self.assertEqual(got, tiers)

    def test_a_tier_short_of_cells_is_counted_not_silently_dropped(self):
        pool = {"D": [_row("D", "a", 0.5, 0.1, tier="mega")]}
        counts = {"D": 1}
        drawn, shortfall = CE.draw_null(pool, counts, seed=0,
                                        tier_targets={"D": {"small": 1}})
        self.assertEqual(shortfall, 1)
        self.assertEqual(len(drawn), 1)          # backfilled, and the shortfall is reported


class TheBarCannotSeeTheArmsPnl(unittest.TestCase):
    """THE LOAD-BEARING TEST. The bar is committed before the arm is scored; that ordering is
    only meaningful if the bar is not a function of the arm's outcome. `null_gains` takes a
    SHAPE — counts and a tier histogram — and the shape carries no P&L at all."""

    def test_arm_shape_carries_counts_and_tiers_and_nothing_else(self):
        arm = [_row("D", "a", 0.95, 9.99, tier="mega"), _row("D", "b", 0.99, -0.4, "large")]
        counts, tiers = CE.arm_shape(arm, match_tier=True)
        self.assertEqual(counts, {"D": 2})
        self.assertEqual(tiers, {"D": {"mega": 1, "large": 1}})
        blob = repr(counts) + repr(tiers)
        self.assertNotIn("9.99", blob)
        self.assertNotIn("pnl", blob)

    def test_the_bar_is_identical_when_the_arms_pnl_is_replaced_wholesale(self):
        """Same shape, wildly different arm P&L -> the same bar, to the digit."""
        grid = _grid()
        arm = CE.select(grid, *CE.ARMS["TOP20"])
        shape_a = CE.arm_shape(arm, match_tier=False)
        loud = [dict(r, pnl_pct=1e6) for r in arm]
        shape_b = CE.arm_shape(loud, match_tier=False)
        self.assertEqual(shape_a, shape_b)
        one = CE.null_gains(grid, shape_a[0], shape_a[1], n_draws=40, seed0=100)
        two = CE.null_gains(grid, shape_b[0], shape_b[1], n_draws=40, seed0=100)
        self.assertEqual(one["bar_pp"], two["bar_pp"])

    def test_null_gains_does_not_take_an_arm_at_all(self):
        import inspect
        sig = list(inspect.signature(CE.null_gains).parameters)
        self.assertNotIn("arm_rows", sig)
        self.assertEqual(sig[:3], ["grid_rows", "counts", "tier_targets"])

    def test_the_null_is_centred_near_zero_because_it_is_a_subset_of_its_own_grid(self):
        """Not a no-effect null: every draw is a real book on the real grid. Its median gain is
        therefore ~0 BY CONSTRUCTION, and the p95 answers 'distinguished among rules of this
        size', never 'does selecting names do anything'."""
        grid = _grid()
        counts = {d: 4 for d in {r["asof"] for r in grid}}
        got = CE.null_gains(grid, counts, None, n_draws=200, seed0=0)
        self.assertLess(abs(got["median_pp"]), 25.0)
        self.assertGreater(got["bar_pp"], got["median_pp"])
        self.assertLess(got["p5_pp"], got["median_pp"])


class ThePercentileIsTheOneTheBarQuotes(unittest.TestCase):
    def test_it_interpolates_the_way_tp_bar_does(self):
        self.assertAlmostEqual(CE.percentile([0.0, 1.0], 50.0), 0.5)
        self.assertAlmostEqual(CE.percentile(list(range(101)), 95.0), 95.0)
        self.assertAlmostEqual(CE.percentile([5.0], 95.0), 5.0)

    def test_it_agrees_with_the_tp_bar_implementation_on_random_data(self):
        import random
        from scripts import tp_bar as TB
        rnd = random.Random(0)
        xs = [rnd.gauss(0, 1) for _ in range(137)]
        for p in (5.0, 50.0, 95.0):
            self.assertAlmostEqual(CE.percentile(xs, p), TB.percentile(xs, p), places=12)

    def test_arm_position_reports_distance_not_just_a_verdict(self):
        gains = [float(i) for i in range(100)]
        self.assertAlmostEqual(CE.arm_position(gains, 82.0), 82.0)
        self.assertIsNone(CE.arm_position([], 1.0))


class TheDecileTableIsOrderedBestFirst(unittest.TestCase):
    """Decile 1 = BEST composite, matching `quantile_backtest` and `options_veto.decile_table`.
    This project has already spent one correction on reading an ordering backwards."""

    def test_decile_one_holds_the_highest_percentiles(self):
        rows = _grid(n_per_date=20)
        tab = CE.decile_table(rows)
        self.assertEqual(len(tab), 10)
        self.assertEqual(tab[0]["pct_range"], [0.9, 1.0])
        self.assertEqual(tab[-1]["pct_range"], [0.0, 0.1])
        self.assertEqual(sum(d["n_trades"] for d in tab), len(rows))

    def test_a_perfectly_ordered_signal_shows_decile_one_best(self):
        rows = _grid(n_per_date=20)
        tab = CE.decile_table(rows)
        self.assertGreater(tab[0]["mean_pnl_pct"], tab[-1]["mean_pnl_pct"])


class TheModuleSurvivesACheckoutWithNoLicensedData(unittest.TestCase):
    """`data/` is gitignored, so the auto-land gate has none. An import-time failure here would
    fail every suite, not just this one."""

    def test_import_and_pure_helpers_need_no_data(self):
        import importlib
        m = importlib.import_module("valuation.edge.composite_entry")
        self.assertTrue(hasattr(m, "ARMS"))
        self.assertEqual(m.select([], 0.9, 1.01), [])
        self.assertEqual(m.by_date_counts([]), {})
        self.assertIsNone(m.mean_pnl([]))

    def test_the_entry_window_is_imported_from_options_universe_not_copied(self):
        import inspect
        src = inspect.getsource(CE.window)
        self.assertIn("from .options_universe import ENTRY_START, ENTRY_END", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
