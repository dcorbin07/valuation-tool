"""Pins for MC12's census. Register: `PREREG_panel_ext_census.md`.

    python tests/test_panel_ext_census.py

WHY THE AST AND NOT A GREP
    The register's void condition 1 forbids computing any forward return, price return, IC or
    *t* anywhere in the census path. A SUBSTRING ban cannot express that: this module's own
    docstring names the forbidden things in order to say it does not compute them, so a grep
    fires against the CORRECT tree. This record has paid for that family five times (`MA49`,
    `MB1` x3, `MB15`, `W-1`). So the check reads the SYNTAX TREE -- names, attributes and
    calls -- and each guard carries a POSITIVE CONTROL proving it can still bite.
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "scripts", "panel_ext_census.py")

sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def _tree(path=SRC):
    return ast.parse(io.open(path, encoding="utf-8").read())


def _identifiers(tree):
    """Every NAME and ATTRIBUTE in the tree. Deliberately excludes string constants, so prose
    about a forbidden quantity cannot trip the guard while real code still does."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _subscript_strings(tree):
    """String literals used as SUBSCRIPTS -- `df["fwd_ret"]` is a read even though the token is
    a string, so the identifier sweep alone would miss it."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and isinstance(n.slice.value, str):
            out.add(n.slice.value)
    return out


#: Reading any of these IS computing an outcome on this panel.
BANNED = {"fwd_ret", "fwd_ret_h63", "forward_return", "top_decile_alpha",
          "long_short_tstat", "long_short_tstat_nw", "long_short_tstat_hac",
          "alpha_t_hac", "monotonicity", "closeadj"}


class VoidCondition1(unittest.TestCase):
    """No outcome statistic is reachable from the census."""

    def test_no_outcome_column_is_read_anywhere(self):
        t = _tree()
        seen = _identifiers(t) | _subscript_strings(t)
        hits = sorted(BANNED & seen)
        self.assertEqual(hits, [], "the census reads an outcome column: %s. Void condition 1 of "
                                   "PREREG_panel_ext_census.md forbids it." % hits)

    def test_the_guard_can_actually_fire(self):
        """POSITIVE CONTROL. A guard that cannot bite is not a guard."""
        t = ast.parse("import pandas as pd\nx = df['fwd_ret'].mean()\n")
        seen = _identifiers(t) | _subscript_strings(t)
        self.assertIn("fwd_ret", BANNED & seen,
                      "the AST sweep would not catch a real fwd_ret read")

    def test_prose_naming_the_banned_thing_does_not_trip_it(self):
        """The other direction, which is why this is an AST check and not a grep."""
        t = ast.parse('"""This module never reads fwd_ret."""\nY = 1\n')
        seen = _identifiers(t) | _subscript_strings(t)
        self.assertEqual(BANNED & seen, set(),
                         "a docstring mentioning the banned name tripped the guard -- that is "
                         "the substring-ban family this check exists to avoid")

    def test_the_census_never_imports_the_scoring_path(self):
        t = _tree()
        bad = []
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                bad += [a.name for a in n.names if "fundamental_panel" in a.name]
            elif isinstance(n, ast.ImportFrom):
                if n.module and "fundamental_panel" in n.module:
                    bad.append(n.module)
        self.assertEqual(bad, [], "the census imports the scoring path: %s" % bad)


class Bars(unittest.TestCase):
    """Every bar is the register's, and a silent change shows up here rather than in a verdict."""

    def test_bars_match_the_register(self):
        import panel_ext_census as P
        self.assertEqual(P.K1_MIN_NAMES, 1030)
        self.assertEqual(P.K2_NONNULL, 0.70)
        self.assertEqual((P.K3_LO, P.K3_HI), (0.5, 2.0))
        self.assertEqual(P.K4_MAX_SHORTFALL_PP, 10.0)
        self.assertEqual(P.PIT_LAG_DAYS, 120)
        self.assertEqual(P.K3_PRIMARY_H, 5)
        self.assertEqual(P.MIN_PLAUSIBLE_SESSIONS, 200)

    def test_the_window_is_the_registered_one(self):
        import panel_ext_census as P
        self.assertEqual(P.YEARS[0], 1995)
        self.assertEqual(P.YEARS[-1], 2008)
        self.assertEqual(P.START_YEARS, (1995, 1999, 2000))


class LoadBearingSet(unittest.TestCase):
    """The scope is defined on the AST-derived set, so the derivation is pinned."""

    def test_the_derived_z_column_count_is_24(self):
        import panel_ext_census as P
        used, per_theme = P.weighted_theme_inputs()
        self.assertEqual(len(used), 24,
                         "the AST-derived z-column set moved to %d. DESIGN 1.1's prose says 24 "
                         "and its table lists 25 rows; the 25th is `insider_score`, which is "
                         "NOT a z-column because factors.py maps insider as a fixed affine "
                         "(insider_score-50)/25." % len(used))

    def test_insider_contributes_no_z_column(self):
        """The precise reason DESIGN 1.1's table and its prose disagree."""
        import panel_ext_census as P
        _, per_theme = P.weighted_theme_inputs()
        self.assertEqual(list(per_theme.get("insider", [])), [],
                         "`insider` now carries a z-column; DESIGN 1.1's 25th table row would "
                         "then be right and this census's scope note needs re-deriving")

    def test_every_weighted_theme_is_in_scope(self):
        """All SEVEN, not the four SF1 can answer -- the gap this census had to close."""
        import panel_ext_census as P
        _, per_theme = P.weighted_theme_inputs()
        for t in ("value", "quality", "momentum", "capital_discipline", "size",
                  "institutional", "insider"):
            self.assertIn(t, per_theme, "weighted theme %r fell out of the derived map" % t)


class K3MatchedWindows(unittest.TestCase):
    """The repaired comparison, pinned so the defect cannot come back silently."""

    def test_the_unbounded_share_is_labelled_not_comparable(self):
        """It is retained for the record and must never be the scored quantity."""
        t = _tree()
        keys = _subscript_strings(t)
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("unbounded_later_delist_share_NOT_COMPARABLE", src,
                      "the unbounded share lost its NOT_COMPARABLE label")
        self.assertNotIn('d.get("later_delist_share")', src,
                         "K3 is reading the unbounded share again -- that comparison put a "
                         "~29-year forward window against a ~17-year one and failed 13 of 14 "
                         "years for that reason alone")
        del keys

    def test_a_censored_window_is_not_scored(self):
        import panel_ext_census as P
        self.assertGreater(P.ACTIONS_LAST_YEAR, 2008)
        self.assertIn(P.K3_PRIMARY_H, P.K3_HORIZONS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
