"""I-2 - the name-level percentile engine, ported from TIDEMARK.

WHAT THESE TESTS PIN.

`test_no_lookahead_appending_future_cannot_move_the_past` is **THE load-bearing test**, carried
over verbatim in intent from `tidemark/tests/test_percentile.py`, whose own comment reads: *"if
this fails, every percentile in the project is a lie."* Its panel form is stronger than the
series form it replaces - it must hold for every name at once, including names that enter and
leave, which is the case a single dense series never exercises.

Also pinned: the burn-in returns NaN and never a number; the inversion is applied exactly once;
publication lag moves the knowable DATE and not the VALUE; a non-ISO date RAISES (MB21's `C1`
coerced dates and matched zero of 113,945 rows, then scored a perfect 0.000e+00 by comparing
nothing); one name's history cannot reach another's percentile; and **no outcome relationship is
reachable** - `fwd_ret` appears nowhere in the module or its script, read from the SYNTAX TREE.

And the fence: **method crosses, no TIDEMARK DATA crosses** (`MB24`). Pinned by a source sweep
that STRIPS DOCSTRINGS FIRST, because this module's own prose cites TIDEMARK's file paths while
explaining the rule.

**FOUR OF THE GUARDS IN THIS FILE FIRED AGAINST THE CORRECT TREE BEFORE THEY WERE WRITTEN
PRECISELY**, and every one was the same defect: a ban on a SUBSTRING, tripped by prose that
documents the rule and therefore has to quote what the rule forbids. In order: the module
docstring citing `tidemark/stats/percentile.py`; an artifact key `fwd_ret_loaded` whose whole
job is to record that the outcome was NOT loaded; a key
`e6_reads_this_but_no_verdict_is_recorded_here`; and an error message containing both the word
TIDEMARK and a colon. `MA49` named this family and `MB1` hit it three times in one register and
wrote the fix down - *separate the label from the decision* - which is what the exact-match,
vocabulary and path-shape rules below finally do. Each loosened guard carries a POSITIVE
CONTROL proving it still bites, because a guard relaxed to stop crying wolf is worth nothing if
it stops biting too.

    python tests/test_i2_name_percentile.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from valuation.studies import name_percentile as NP  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(REPO, "valuation", "studies", "name_percentile.py")
SCRIPT = os.path.join(REPO, "scripts", "i2_burn_in_census.py")
_SKIPS = []


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _non_docstring_strings(tree):
    """Every string CONSTANT that is not a module/class/function docstring.

    Factored out because the naive version of this sweep failed against the CORRECT tree twice
    in this batch: prose that documents a rule necessarily quotes the thing the rule forbids.
    `MA49`'s family. Returned as a list so a caller can gate on its LENGTH - a stripper that
    returns nothing would make every guard built on it pass by seeing nothing (`MB15`).
    """
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


#: A TIDEMARK path is a path SHAPE, never a mention. Four of this batch's guards fired against
#: the correct tree before this was written precisely - the last of them because an error
#: message contained a colon and the word TIDEMARK. `MB1`'s three-substring-bans family, and it
#: is now at four instances inside one session. Match the separator, not the token.
_TIDEMARK_PATH = re.compile(r"(?:^|[\\/])tidemark(?:[\\/]|$)|tidemark[\\/]"
                            r"|market[ _]rotation[\\/]", re.IGNORECASE)


def _is_tidemark_path(s: str) -> bool:
    return bool(_TIDEMARK_PATH.search(s or ""))


def _panel(n_names=6, n_dates=30, seed=0, gaps=False):
    """A synthetic per-name panel with ISO string dates, as the real one carries them."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_names):
        vals = rng.normal(size=n_dates).cumsum()
        for d in range(n_dates):
            if gaps and i == 1 and d % 3:      # name 1 keeps only every third date
                continue
            rows.append({"ticker": f"T{i}", "date": f"20{10 + d // 4:02d}-{1 + 3 * (d % 4):02d}-15",
                         "value": float(vals[d])})
    return pd.DataFrame(rows)


# ------------------------------------------------------- THE load-bearing test, ported

class TestNoLookAhead(unittest.TestCase):

    def test_no_lookahead_appending_future_cannot_move_the_past(self):
        """THE load-bearing test. If this fails, every percentile built on this is a lie.

        The panel form: computing on a panel truncated to its first k dates must be
        BIT-IDENTICAL to computing on the whole panel and truncating afterwards.
        """
        p = _panel(n_names=5, n_dates=28)
        dates = sorted(p["date"].unique())
        keep = set(dates[:18])
        full = NP.name_percentiles(p, "value", burn_in=6, invert=False)
        short = NP.name_percentiles(p[p["date"].isin(keep)], "value", burn_in=6, invert=False)
        f = full[full["date"].isin(keep)].sort_values(["ticker", "date"]).reset_index(drop=True)
        s = short.sort_values(["ticker", "date"]).reset_index(drop=True)
        self.assertEqual(f.shape, s.shape)
        self.assertGreater(len(f), 40, "the comparison must not be vacuous")
        a, b = f["value_pct"].to_numpy(), s["value_pct"].to_numpy()
        both_nan = np.isnan(a) & np.isnan(b)
        self.assertTrue(np.array_equal(np.isnan(a), np.isnan(b)))
        self.assertEqual(float(np.max(np.abs(np.where(both_nan, 0.0, a - b)))), 0.0)

    def test_an_extreme_future_value_cannot_move_the_past(self):
        p = _panel(n_names=3, n_dates=20)
        base = NP.name_percentiles(p, "value", burn_in=5, invert=False)
        shocked = p.copy()
        last = shocked["date"].max()
        shocked.loc[shocked["date"] == last, "value"] = 1e9
        after = NP.name_percentiles(shocked, "value", burn_in=5, invert=False)
        b = base[base["date"] < last].sort_values(["ticker", "date"])["value_pct"].to_numpy()
        a = after[after["date"] < last].sort_values(["ticker", "date"])["value_pct"].to_numpy()
        both_nan = np.isnan(a) & np.isnan(b)
        self.assertEqual(float(np.max(np.abs(np.where(both_nan, 0.0, a - b)))), 0.0)

    def test_one_names_history_cannot_reach_another_names_percentile(self):
        """The panel-specific hazard a single-series port would never exercise."""
        p = _panel(n_names=3, n_dates=16)
        base = NP.name_percentiles(p, "value", burn_in=4, invert=False)
        moved = p.copy()
        moved.loc[moved["ticker"] == "T2", "value"] *= 1000.0
        after = NP.name_percentiles(moved, "value", burn_in=4, invert=False)
        for t in ("T0", "T1"):
            b = base[base["ticker"] == t].sort_values("date")["value_pct"].to_numpy()
            a = after[after["ticker"] == t].sort_values("date")["value_pct"].to_numpy()
            both_nan = np.isnan(a) & np.isnan(b)
            self.assertEqual(float(np.max(np.abs(np.where(both_nan, 0.0, a - b)))), 0.0,
                             f"{t}'s percentile moved when a different name's values changed")


# ------------------------------------------------------- rule 3: NaN, never a number

class TestBurnIn(unittest.TestCase):

    def test_burn_in_returns_nan_not_a_number(self):
        p = NP.expanding_percentile(np.arange(10.0), burn_in=6)
        self.assertTrue(np.isnan(p[:5]).all(), "a percentile was emitted before the burn-in")
        self.assertTrue(np.isfinite(p[5:]).all())

    def test_a_history_shorter_than_the_burn_in_is_all_nan(self):
        p = NP.expanding_percentile(np.arange(4.0), burn_in=20)
        self.assertTrue(np.isnan(p).all())

    def test_burn_in_is_required_and_must_be_positive(self):
        with self.assertRaises(TypeError):
            NP.expanding_percentile(np.arange(5.0))
        with self.assertRaises(ValueError):
            NP.expanding_percentile(np.arange(5.0), burn_in=None)
        with self.assertRaises(ValueError):
            NP.expanding_percentile(np.arange(5.0), burn_in=0)

    def test_percentile_is_bounded_and_a_new_all_time_high_sits_at_one(self):
        p = NP.expanding_percentile(np.arange(30.0), burn_in=5)
        f = p[~np.isnan(p)]
        self.assertTrue(((f > 0) & (f <= 1)).all())
        self.assertTrue(np.allclose(f, 1.0), "a rising series must sit at the 100th percentile")

    def test_n_history_counts_the_names_own_observations(self):
        out = NP.name_percentiles(_panel(n_names=2, n_dates=12), "value", burn_in=3,
                                  invert=False)
        for t, g in out.groupby("ticker"):
            g = g.sort_values("date")
            self.assertEqual(list(g["n_history"]), list(range(1, len(g) + 1)))


# ------------------------------------------------------- observations vs calendar time

class TestObservationsAndCalendarTimeComeApart(unittest.TestCase):
    """The one place the port MUST differ from TIDEMARK, made visible rather than assumed."""

    def test_a_gapped_name_buys_more_calendar_years_at_the_same_burn_in(self):
        p = _panel(n_names=3, n_dates=30, gaps=True)
        out = NP.name_percentiles(p, "value", burn_in=6, invert=False)
        dense = out[(out["ticker"] == "T0") & (out["n_history"] == 6)]["history_years"].iloc[0]
        gapped = out[(out["ticker"] == "T1") & (out["n_history"] == 6)]["history_years"].iloc[0]
        self.assertGreater(gapped, dense,
                           "a gapped name reaching the same OBSERVATION count must span more "
                           "CALENDAR time; if these are equal the span is not being measured")

    def test_eligible_rows_can_additionally_require_calendar_time(self):
        p = _panel(n_names=3, n_dates=30, gaps=True)
        out = NP.name_percentiles(p, "value", burn_in=6, invert=False)
        loose = int(NP.eligible_rows(out, "value_pct").sum())
        tight = int(NP.eligible_rows(out, "value_pct", min_history_years=4.0).sum())
        self.assertGreater(loose, 0)
        self.assertLess(tight, loose, "the calendar gate did nothing")


# ------------------------------------------------------- rule 4 and the sign

class TestLagAndOrientation(unittest.TestCase):

    def test_lag_shifts_the_knowable_date_not_the_value(self):
        p = _panel(n_names=2, n_dates=12)
        a = NP.name_percentiles(p, "value", burn_in=3, invert=False, lag_days=0)
        b = NP.name_percentiles(p, "value", burn_in=3, invert=False, lag_days=45)
        self.assertTrue(np.allclose(a["value_pct"].to_numpy(), b["value_pct"].to_numpy(),
                                    equal_nan=True))
        self.assertTrue((b["knowable_at"].to_numpy() > a["knowable_at"].to_numpy()).all(),
                        "a lag must push the knowable date later")
        self.assertTrue((a["date"].to_numpy() == b["date"].to_numpy()).all(),
                        "the reference date must not move")

    def test_publication_lag_is_required(self):
        with self.assertRaises(TypeError):
            NP.publication_lag_dates(["2020-01-15"])
        with self.assertRaises(ValueError):
            NP.publication_lag_dates(["2020-01-15"], lag_days=None)

    def test_inversion_is_applied_exactly_once(self):
        """A double inversion is a no-op that looks like a decision."""
        p = _panel(n_names=3, n_dates=20)
        up = NP.name_percentiles(p, "value", burn_in=5, invert=False)["value_pct"].to_numpy()
        dn = NP.name_percentiles(p, "value", burn_in=5, invert=True)["value_pct"].to_numpy()
        m = ~np.isnan(up)
        self.assertTrue(m.any())
        self.assertTrue(np.allclose(up[m] + dn[m], 1.0))

    def test_invert_is_required(self):
        with self.assertRaises(TypeError):
            NP.name_percentiles(_panel(), "value", burn_in=4)
        with self.assertRaises(ValueError):
            NP.name_percentiles(_panel(), "value", burn_in=4, invert=None)


# ------------------------------------------------------- MB21's date trap

class TestDatesAreValidatedNotCoerced(unittest.TestCase):

    def test_a_non_iso_date_raises_FROM_THIS_GUARD(self):
        """The message is asserted, and that is this test's own repair.

        The first cut used `15/01/2010` and only asked that *something* raise `ValueError`. It
        PASSED WITH THE GUARD DELETED - caught by mutation, not by reading - because pandas
        rejects that string too, on mixed-format parsing, several lines downstream. A test that
        asserts a raise without asserting WHO raised it can pass on a coincidence.
        """
        p = _panel(n_names=2, n_dates=8)
        p.loc[0, "date"] = "15/01/2010"
        with self.assertRaisesRegex(ValueError, "is not ISO"):
            NP.name_percentiles(p, "value", burn_in=3, invert=False)

    def test_a_date_pandas_would_happily_accept_is_still_refused(self):
        """The decisive case: slashes instead of dashes.

        `2010/01/15` parses cleanly in pandas, so NOTHING downstream would object - and it does
        not sort chronologically as a string against `2010-04-15`, which is how the ordering is
        taken. Only this guard stands between that and a silently mis-ordered history.
        """
        self.assertEqual(str(pd.to_datetime("2010/01/15").date()), "2010-01-15")
        p = _panel(n_names=2, n_dates=8)
        p.loc[0, "date"] = "2010/01/15"
        with self.assertRaisesRegex(ValueError, "is not ISO"):
            NP.name_percentiles(p, "value", burn_in=3, invert=False)

    def test_a_timestamp_is_accepted_and_normalised(self):
        p = _panel(n_names=2, n_dates=8)
        p["date"] = pd.to_datetime(p["date"])
        out = NP.name_percentiles(p, "value", burn_in=3, invert=False)
        self.assertTrue(all(isinstance(d, str) and len(d) == 10 for d in out["date"]))

    def test_a_missing_column_raises_rather_than_returning_empty(self):
        with self.assertRaises(KeyError):
            NP.name_percentiles(_panel(), "not_a_column", burn_in=3, invert=False)


# ------------------------------------------------------- the fences

class TestNoOutcomeRelationshipIsReachable(unittest.TestCase):
    """`MB18`'s structural pin: an allowlist, not a promise.

    THESE GUARDS MATCH EXACTLY, NOT BY CONTAINMENT, AND THAT IS THIS FILE'S OWN REPAIR. The
    first cut banned the SUBSTRING `fwd_ret` and failed against the CORRECT tree, because the
    census artifact carries a field called `fwd_ret_loaded` whose entire job is to record that
    the column was NOT loaded. `MB1` hit this three times in one register and wrote the fix
    down: *separate the label from the decision*. A column cannot be selected with the string
    `"fwd_ret_loaded"`; only an exact `"fwd_ret"` selects the outcome.
    """

    def test_the_outcome_column_is_never_selected(self):
        for path in (LIB, SCRIPT):
            tree = ast.parse(_src(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    self.assertNotEqual(node.attr, "fwd_ret", f"{path} reaches .fwd_ret")
            exact = [s for s in _non_docstring_strings(tree) if s == "fwd_ret"]
            self.assertEqual(exact, [],
                             f"{path} selects the column fwd_ret; I-2 computes no outcome "
                             f"relationship, that is E-6's arm and E-6's trial")

    def test_that_exactness_rule_still_catches_the_real_thing(self):
        """A guard loosened to stop crying wolf must still bite. Proved, not asserted."""
        tree = ast.parse('KEEP = ("date", "ticker", "value", "fwd_ret")\n'
                         'NOTE = "fwd_ret_loaded"\n')
        strings = _non_docstring_strings(tree)
        self.assertIn("fwd_ret", strings, "the exact-match guard would miss a real selection")
        self.assertIn("fwd_ret_loaded", strings)
        self.assertEqual([s for s in strings if s == "fwd_ret"], ["fwd_ret"])

    def test_the_scripts_allowlist_excludes_the_outcome(self):
        tree = ast.parse(_src(SCRIPT))
        keep = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "KEEP" for t in node.targets):
                keep = [e.value for e in node.value.elts]
        self.assertIsNotNone(keep, "the census script must carry an explicit column allowlist")
        self.assertNotIn("fwd_ret", keep)
        self.assertEqual(sorted(keep), ["date", "ticker", "value"])

    def test_no_verdict_is_recorded_by_the_census(self):
        """E-6's 60% bar is E-6's. This script prints the input and compares nothing.

        Separated by ROLE, per `MB1`: a verdict is a string VALUE the script could emit, so the
        ban is on the vocabulary. A KEY saying `e6_reads_this_but_no_verdict_is_recorded_here`
        is a LABEL disclaiming a verdict, and banning it by substring is the defect `MB1`
        recorded and this test committed anyway.
        """
        vocab = {"confirmed", "rejected", "unpowered", "unpowered-by-construction", "null",
                 "adopt", "adopted", "eligible", "kill", "killed", "pass", "fail"}
        for s in _non_docstring_strings(ast.parse(_src(SCRIPT))):
            self.assertNotIn(s.strip().lower(), vocab,
                             f"the census emits the verdict word {s!r}; E-6's bar is E-6's")

    def test_that_vocabulary_rule_still_catches_the_real_thing(self):
        tree = ast.parse('out = {"verdict": "UNPOWERED-BY-CONSTRUCTION"}\n')
        vals = [s.strip().lower() for s in _non_docstring_strings(tree)]
        self.assertIn("unpowered-by-construction", vals,
                      "the vocabulary guard would miss an actual verdict being emitted")


class TestNoTidemarkDataCrosses(unittest.TestCase):
    """`MB24`: data flow is out of scope; only the method crosses."""

    def test_nothing_imports_or_reads_a_tidemark_path(self):
        """A PATH, not a mention. The distinction is this test's own repair.

        Banning the substring `tidemark` failed against the CORRECT tree because the module's
        `PERCENTILE_RULES` constant says *"Ported from tidemark; method only, no data (MB24)"* -
        a string whose entire purpose is to record the fence it was accused of breaching. The
        hazard is a filesystem path or an import; a mention in prose is the citation `MB22`'s
        port was praised for carrying.
        """
        for path in (LIB, SCRIPT):
            tree = ast.parse(_src(path))
            strings = _non_docstring_strings(tree)
            self.assertGreater(len(strings), 5,
                               "the docstring stripper removed everything; this guard would "
                               "then pass by seeing nothing (MB15's vacuous-stripper lesson)")
            for s in strings:
                self.assertFalse(
                    _is_tidemark_path(s),
                    f"{path} carries a TIDEMARK path in code: {s!r} -- MB24 puts data flow out "
                    f"of scope; only the method crosses")
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        self.assertNotIn("tidemark", a.name.lower())
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("tidemark", (node.module or "").lower())

    def test_that_path_rule_still_catches_the_real_thing_and_spares_prose(self):
        """Both directions, because a guard loosened to stop crying wolf must still bite."""
        self.assertTrue(_is_tidemark_path(
            "C:/Users/donni/Downloads/Market Rotation/tidemark/data/x.csv"))
        self.assertTrue(_is_tidemark_path(r"..\tidemark\stats\percentile.py"))
        self.assertTrue(_is_tidemark_path("tidemark/stats/percentile.py"))
        # prose that MENTIONS the source, which is the citation the port is supposed to carry
        self.assertFalse(_is_tidemark_path("Ported from TIDEMARK; method only, no data (MB24)."))
        self.assertFalse(_is_tidemark_path(
            "name_percentiles: `invert` is required. TIDEMARK's own rule: a sign error here "
            "inverts every conclusion."))

    def test_the_stripper_itself_is_not_vacuous(self):
        """It must KEEP a code string and DROP the docstring, proved in both directions."""
        tree = ast.parse('"""doc mentions tidemark/stats/percentile.py"""\nX = "kept"\n')
        got = _non_docstring_strings(tree)
        self.assertIn("kept", got)
        self.assertFalse(any("tidemark" in s for s in got))


# ------------------------------------------------------- the census

class TestCensus(unittest.TestCase):

    def test_a_longer_burn_in_never_leaves_more_rows(self):
        c = NP.burn_in_census(_panel(n_names=5, n_dates=24), "value", (4, 8, 12), invert=False)
        shares = [r["eligible_row_share"] for r in c["burn_ins"]]
        self.assertEqual(shares, sorted(shares, reverse=True))
        self.assertLess(shares[-1], shares[0], "the burn-in costs nothing; it is not applied")

    def test_the_census_reports_calendar_years_beside_every_row_share(self):
        c = NP.burn_in_census(_panel(n_names=4, n_dates=20), "value", (5,), invert=False)
        r = c["burn_ins"][0]
        for k in ("eligible_rows", "eligible_row_share", "eligible_names", "eligible_dates",
                  "first_eligible_date", "median_history_years_at_eligibility"):
            self.assertIn(k, r)
        self.assertIsNotNone(r["median_history_years_at_eligibility"])

    def test_banked_census_is_internally_consistent(self):
        p = os.path.join(REPO, "data", "free_analysis", "I2_BURN_IN_CENSUS.json")
        if not os.path.isfile(p):
            _SKIPS.append("I2_BURN_IN_CENSUS.json absent (data/ is gitignored)")
            self.skipTest("census artifact absent")
        with io.open(p, encoding="utf-8") as fh:
            c = json.load(fh)
        self.assertTrue(c["all_pass"])
        self.assertFalse(c["fwd_ret_loaded"])
        self.assertEqual(sorted(c["columns_loaded"]), ["date", "ticker", "value"])
        nl = c["no_lookahead_on_the_real_panel"]
        self.assertEqual(nl["max_abs_delta"], 0.0)
        self.assertTrue(nl["keys_identical"])
        self.assertGreater(nl["rows_compared"], 10_000,
                           "the real-panel look-ahead check must not be vacuous")
        shares = [r["eligible_row_share"] for r in c["census"]["burn_ins"]]
        self.assertEqual(shares, sorted(shares, reverse=True))

    def test_the_two_readings_of_five_years_are_both_reported(self):
        """The measured fact E-6 turns on: they land on opposite sides of E-6's own 60% bar.

        No verdict is asserted here - only that BOTH readings travel, so E-6's register has to
        DECLARE which it means instead of inheriting whichever the code happened to do.
        """
        p = os.path.join(REPO, "data", "free_analysis", "I2_BURN_IN_CENSUS.json")
        if not os.path.isfile(p):
            _SKIPS.append("I2_BURN_IN_CENSUS.json absent (data/ is gitignored)")
            self.skipTest("census artifact absent")
        with io.open(p, encoding="utf-8") as fh:
            r = json.load(fh)["five_year_readings"]
        for k in ("observations_20", "observations_20_AND_calendar_5y", "observations_21"):
            self.assertIn(k, r)
            self.assertGreater(r[k]["eligible_rows"], 0)
        self.assertGreater(r["observations_20"]["share"],
                           r["observations_20_AND_calendar_5y"]["share"],
                           "the calendar gate must be STRICTER than the observation count; if "
                           "these are equal the two readings are not being distinguished")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
