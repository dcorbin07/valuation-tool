"""Pins for the free-kills census.

    python tests/test_free_kills_census.py

THE ONE PROPERTY THAT MATTERS: these are CENSUSES, not arms. No forward return may be joined to
anything and no outcome statistic may be computed, or a "free kill" has quietly spent a trial.

Checked over the SYNTAX TREE, not by grep, because the module's own docstring names the forbidden
quantities in order to say it does not compute them -- a substring ban fires against the correct
tree, which this record has paid for five times. Every guard carries a positive control.
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "scripts", "free_kills_census.py")

sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import source_bounds as SB   # noqa: E402

BANNED = {"fwd_ret", "fwd_ret_h63", "forward_return", "top_decile_alpha",
          "long_short_tstat", "long_short_tstat_nw", "long_short_tstat_hac",
          "alpha_t_hac", "monotonicity", "quantile_backtest"}


def _tree():
    return ast.parse(io.open(SRC, encoding="utf-8").read())


def _identifiers(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _subscript_strings(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and isinstance(n.slice.value, str):
            out.add(n.slice.value)
    return out


class NoOutcomeIsComputed(unittest.TestCase):
    def test_no_outcome_column_or_scorer_is_touched(self):
        t = _tree()
        seen = _identifiers(t) | _subscript_strings(t)
        hits = sorted(BANNED & seen)
        self.assertEqual(hits, [], "the census touches an outcome: %s. A free kill that scores an "
                                   "outcome has spent a trial." % hits)

    def test_the_guard_can_fire(self):
        """POSITIVE CONTROL."""
        t = ast.parse("x = df['fwd_ret'].mean()\n")
        self.assertIn("fwd_ret", BANNED & (_identifiers(t) | _subscript_strings(t)))

    def test_prose_naming_the_banned_thing_does_not_fire(self):
        t = ast.parse('"""This census never reads fwd_ret or top_decile_alpha."""\nY = 1\n')
        self.assertEqual(BANNED & (_identifiers(t) | _subscript_strings(t)), set())


class BarsAreTheDraftsOwn(unittest.TestCase):
    def test_bars_match_the_drafts(self):
        import free_kills_census as F
        self.assertEqual(F.MIN_BOOK, 50)            # CONTRACT_MIN_POSITIONS
        self.assertEqual(F.NONNULL_RULE, 0.70)      # the project's 70% rule
        self.assertEqual(F.COSTUME_BAR, 0.60)       # R6's / E-1's own bar, verbatim
        self.assertEqual(F.SPINOFF_CLOSE, 100)
        self.assertEqual(F.SPINOFF_UNDERPOWERED, 400)   # DC-1's n_eff reference

    def test_the_band_is_below_the_served_tier(self):
        """The whole premise is the part of the universe the $10B tier declines to hold."""
        import free_kills_census as F
        self.assertLess(F.BAND_CEILING, 1e10)
        self.assertGreater(F.BAND_FLOOR, 0)


class JoinsAreDateNormalised(unittest.TestCase):
    """The panel's `date` is a STRING and B13_ADV_PANEL's is a `datetime.date`. Merging them
    unnormalised matches ZERO rows IN SILENCE, which is this record's most expensive join defect."""

    def test_both_loaders_normalise_the_date(self):
        """REPOINTED 2026-10-07 (item 36b). This read `src[i:i + 420]` from each `def` -- the
        narrowest of the surviving character windows, so the cheapest to break: five comment
        lines inside either loader would have taken it red against a correct tree.
        """
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("_norm_date", src)
        for fn in ("load_panel", "load_adv"):
            body = SB.function_source(SRC, fn)
            self.assertIn("_norm_date", body, "%s does not normalise its date column" % fn)
            # NON-VACUITY: the bound is ONE function, so a needle in the other cannot satisfy
            # it. Without this a whole-file bound would pass both iterations on one call site.
            other = "load_adv" if fn == "load_panel" else "load_panel"
            self.assertNotIn("def %s" % other, body,
                             "the bound runs past %s into %s" % (fn, other))

    def test_the_band_merge_refuses_a_row_count_change(self):
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("the ADV merge changed the row count", src)

    def test_norm_date_is_idempotent_and_handles_both_types(self):
        import datetime as dt
        import free_kills_census as F
        self.assertEqual(list(F._norm_date(["2009-01-15"])), ["2009-01-15"])
        self.assertEqual(list(F._norm_date([dt.date(2009, 1, 15)])), ["2009-01-15"])


class TheVendorCutIsExcludedNotScored(unittest.TestCase):
    """W-28's defect: a vendor's end-of-data read as a coverage gap."""

    def test_n1_excludes_zero_coverage_dates_and_lists_them(self):
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("excluded_dates_zero_adv_coverage", src)
        self.assertIn("LISTED, NOT SCORED", src)

    def test_the_exclusion_is_derived_not_hard_coded(self):
        """A hard-coded date list would go stale the moment CRSP extends."""
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("cov[cov == 0]", src)
        for d in ("2025-01-27", "2025-04-28", "2026-01-28"):
            self.assertNotIn('"%s"' % d, src,
                             "the excluded dates are hard-coded; they must be DERIVED from "
                             "coverage so they move when the vendor does")


if __name__ == "__main__":
    unittest.main(verbosity=2)
