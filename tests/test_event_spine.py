"""
I-4 — the event spine. Offline, synthetic calendars, no `data/` dependency. Run:

    python tests/test_event_spine.py

WHAT THESE PIN, AND WHY EACH ONE EXISTS.

1. **THE AGREEMENT TEST IS THE POINT OF THE WHOLE INSTRUMENT.** The spine exists so that one
   earnings-date derivation serves every event-time consumer. That is worth nothing as an
   intention: `PT-SPLIT` was two mechanisms describing one named object, and the disagreement
   surfaced only when a wrong figure had already shipped. So this file imports BOTH the spine
   and the SHIPPED `earnings_surface` predicates and drives them over an exhaustive grid,
   requiring agreement on every cell -- INCLUDING which cells are UNKNOWN. If they ever diverge
   the test prints the disagreeing cells rather than a count, because "3 cells differ" is not
   actionable and `(entry, expiry, window, calendar)` is.

2. **UNKNOWN IS NOT FALSE, IN BOTH DIRECTIONS.** O17's rule. A test that only checks the True
   and False cases passes on a fail-open implementation, which is the bug the rule exists to
   prevent, so the None cells are asserted explicitly and the "empty calendar behaves differently
   from a distant announcement" pair is asserted directly.

3. **THE DECODE IS NOT DUPLICATED.** `bulk.py` owns `EARNINGS_CODES`; the spine reuses it. A copy
   would drift silently the moment either changed, which is this project's most-repeated defect.

4. **THE SUNSET TRAVELS WITH THE TABLE.** Codes 34/35 stop mid-panel. Nothing in the spine uses
   them -- that is exactly why a future reader could rediscover the cliff in their own data and
   report it as a finding, so the dates ride along in the census.
"""
import ast
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import bulk                                        # noqa: E402
from valuation.edge import event_spine as SP                           # noqa: E402
# The ARCHIVED study. Importing it from a TEST is fine and is what MA59's quarantine permits --
# it gates reachability from PRODUCTION entry points, and `tests/test_earnings_surface.py`
# already imports it. The spine itself must never import it; test 3 below pins that.
from valuation.studies import earnings_surface as ES                   # noqa: E402


def _spine(cal: dict) -> SP.EventSpine:
    return SP.EventSpine(dict(cal), source="synthetic")


def _spine_source() -> str:
    with open(SP.__file__, encoding="utf-8") as fh:
        return fh.read()


# The grid. Deliberately includes an empty calendar, a calendar entirely BEFORE the entry
# (announcements exist but none is upcoming), a same-day announcement, and boundary cells at
# exactly the window edge -- the four places an off-by-one or a fail-open hides.
CALENDARS = {
    "EMPTY": [],
    "ALL_PAST": ["2022-01-05", "2022-04-06"],
    "SAME_DAY": ["2023-05-08"],
    "EDGE": ["2023-05-13"],
    "JUST_OUT": ["2023-05-14"],
    "QUARTERLY": ["2023-02-01", "2023-05-10", "2023-08-02", "2023-11-01"],
    "DENSE": ["2023-05-09", "2023-05-10", "2023-05-11"],
}
ENTRIES = ["2023-05-08", "2023-05-10", "2023-12-31"]
EXPIRIES = ["2023-05-09", "2023-05-19", "2023-07-21", "2024-01-19"]
WINDOWS = (0, 1, 5, 10, 15)


class TestAgreementWithTheShippedPaths(unittest.TestCase):
    """The two derivations must not drift. This is the two-recorders bug, pre-empted."""

    def test_refuse_within_agrees_cell_for_cell(self):
        bad = []
        for cname, cal in CALENDARS.items():
            sp = _spine({"T": cal})
            for entry in ENTRIES:
                for w in WINDOWS:
                    mine = SP.refuse_within(sp, "T", entry, w)
                    theirs = ES.refuse_within(entry, cal, w)
                    if mine is not theirs:
                        bad.append(f"refuse_within[{cname} entry={entry} w={w}] "
                                   f"spine={mine!r} shipped={theirs!r}")
        self.assertEqual(bad, [], "SPINE AND SHIPPED PATH DISAGREE:\n  " + "\n  ".join(bad))

    def test_owns_the_event_agrees_cell_for_cell(self):
        bad = []
        for cname, cal in CALENDARS.items():
            sp = _spine({"T": cal})
            for entry in ENTRIES:
                for exp in EXPIRIES:
                    mine = SP.owns_the_event(sp, "T", entry, exp)
                    theirs = ES.owns_the_event(entry, exp, cal)
                    if mine is not theirs:
                        bad.append(f"owns_the_event[{cname} entry={entry} exp={exp}] "
                                   f"spine={mine!r} shipped={theirs!r}")
        self.assertEqual(bad, [], "SPINE AND SHIPPED PATH DISAGREE:\n  " + "\n  ".join(bad))

    def test_the_grid_actually_exercises_all_three_outcomes(self):
        """A grid that never produces a None makes the agreement test vacuous on the case that
        matters most."""
        seen = set()
        for cal in CALENDARS.values():
            sp = _spine({"T": cal})
            for entry in ENTRIES:
                for w in WINDOWS:
                    seen.add(SP.refuse_within(sp, "T", entry, w))
                for exp in EXPIRIES:
                    seen.add(SP.owns_the_event(sp, "T", entry, exp))
        self.assertEqual(seen, {True, False, None},
                         f"grid does not cover all three outcomes, saw {seen}")


class TestTheOneRule(unittest.TestCase):
    """A missing earnings date is UNKNOWN, never 'no announcement'."""

    def test_dates_raises_for_an_uncovered_name_rather_than_returning_empty(self):
        sp = _spine({"COVERED": ["2023-05-10"]})
        with self.assertRaises(SP.UnknownCoverage):
            sp.dates("FPI")
        self.assertIsNone(sp.dates_or_unknown("FPI"))
        self.assertEqual(sp.dates("COVERED"), ["2023-05-10"])

    def test_an_uncovered_name_is_fail_closed_not_a_gap(self):
        sp = _spine({"COVERED": ["2023-05-10"], "FPI": []})
        self.assertEqual(sp.coverage("FPI"), SP.FAIL_CLOSED)
        self.assertEqual(sp.coverage("FPI", 2023), SP.FAIL_CLOSED)
        self.assertFalse(sp.is_known("FPI"))
        # a covered name with nothing in ONE year is a GAP -- a different statement
        self.assertEqual(sp.coverage("COVERED", 2019), SP.GAP)

    def test_unknown_is_distinguishable_from_no_upcoming_announcement(self):
        """Both return None from `next_after`, and the caller must be able to tell them apart."""
        sp = _spine({"COVERED": ["2022-01-05"], "FPI": []})
        self.assertIsNone(sp.next_after("COVERED", "2023-05-08"))   # none upcoming
        self.assertIsNone(sp.next_after("FPI", "2023-05-08"))       # unknown
        self.assertNotEqual(sp.coverage("COVERED"), sp.coverage("FPI"))

    def test_partial_is_its_own_state_and_is_not_rounded_to_covered(self):
        """Code 22 runs ~2.83/ticker-year against a quarterly 4, so a year with one date is real
        coverage AND demonstrably incomplete. Collapsing that into COVERED is how a hole in the
        calendar becomes an implied 'no announcement'."""
        sp = _spine({"THIN": ["2023-05-10", "2023-08-02"],
                     "FULL": ["2023-02-01", "2023-05-10", "2023-08-02", "2023-11-01"]})
        self.assertEqual(sp.coverage("THIN", 2023), SP.PARTIAL)
        self.assertEqual(sp.coverage("FULL", 2023), SP.COVERED)
        self.assertNotEqual(SP.PARTIAL, SP.COVERED)


class TestProvenance(unittest.TestCase):

    def test_the_spine_reuses_bulks_decode_and_does_not_copy_the_code_set(self):
        """One owner for 'which code means earnings'. A second copy drifts silently.

        Checked against the module NAMESPACE and its assignment targets, not its text: the
        docstring legitimately says the words "EARNINGS_CODES" while explaining that it keeps no
        copy, and a substring check cannot tell a promise from a violation. (Both earlier cuts of
        this file made exactly that mistake, in two different tests -- which is itself the
        argument for parsing rather than grepping.)
        """
        self.assertFalse(hasattr(SP, "EARNINGS_CODES"),
                         "the spine defines its own EARNINGS_CODES; bulk.py owns that set")
        assigned = set()
        for node in ast.walk(ast.parse(_spine_source())):
            if isinstance(node, ast.Assign):
                assigned.update(t.id for t in node.targets if isinstance(t, ast.Name))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                assigned.add(node.target.id)
        self.assertNotIn("EARNINGS_CODES", assigned,
                         "the spine assigns EARNINGS_CODES; it must read bulk's")
        src = _spine_source()
        self.assertIn("bulk.earnings_dates", src)
        self.assertIn("bulk.prepare_events", src)
        self.assertEqual(bulk.EARNINGS_CODES, {"22"},
                         "bulk's decode changed; the spine's legend row needs re-checking")

    def test_the_spine_does_not_import_the_archived_study(self):
        """MA59: reaching an archived study from a live module means the product runs an
        experiment. The comparison lives in this TEST precisely so it cannot.

        Checked by PARSING THE IMPORTS, not by grepping the text -- the spine's docstring
        legitimately names `earnings_surface` to explain why it does not import it, and a string
        check cannot tell an explanation from a dependency. (First cut of this test did exactly
        that and failed on its own comment.)
        """
        imported = set()
        for node in ast.walk(ast.parse(_spine_source())):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                imported.add(base)
                imported.update(f"{base}.{a.name}" for a in node.names)
        leaked = sorted(m for m in imported if "earnings_surface" in m)
        self.assertEqual(leaked, [], f"the spine imports the archived study: {leaked}")
        self.assertIn("valuation.edge.bulk",
                      {m for m in imported} | {f"{m}.bulk" for m in imported},
                      f"the spine no longer imports bulk; imports were {sorted(imported)}")

    def test_the_legend_row_matches_the_transcribed_reference(self):
        leg = SP.EARNINGS_CODE_LEGEND
        self.assertEqual(leg["code"], "22")
        self.assertEqual(leg["meaning"], "Results of Operations and Financial Condition")
        self.assertEqual((leg["first"], leg["last"]), ("2004-08-23", "2026-07-31"))
        self.assertEqual((leg["occurrences"], leg["tickers"]), (385896, 10149))

    def test_the_34_35_sunset_is_recorded_with_its_dates(self):
        """So nobody reads their disappearance as a signal. Nothing here USES 34/35 -- that is
        the reason it has to be written down rather than discovered later in someone's data."""
        s = SP.CODE_SUNSETS
        self.assertEqual(s["34"]["last"], "2024-12-17")
        self.assertEqual(s["35"]["last"], "2025-05-16")
        self.assertIn("13G", s["34"]["meaning"])
        self.assertIn("13D", s["35"]["meaning"])
        # and the earnings code must NOT be in the sunset set
        self.assertNotIn("22", s)
        self.assertEqual(SP.EARNINGS_CODE_LEGEND["last"], "2026-07-31")

    def test_the_end_years_are_marked_source_bounded_not_left_looking_like_decay(self):
        """The source begins 2004-08-23 and ends 2026-07-31, so both end years are PARTIAL by
        calendar. Unmarked, a consumer plotting coverage over time reports a cliff.

        This is the same mistake, in a different costume, as reading a not-yet-finished year as a
        damaged one -- which cost a whole tier of the chain harvest.
        """
        sp = _spine({"A": ["2004-09-01", "2015-02-01", "2015-05-01", "2015-08-01",
                           "2026-02-01", "2026-05-01"]})
        c = sp.census(years=[2004, 2015, 2026])
        self.assertIn("2004", c["source_bounded_years"])
        self.assertIn("2026", c["source_bounded_years"])
        self.assertNotIn("2015", c["source_bounded_years"],
                         "an interior year must NOT be excused as source-bounded")
        self.assertIn("not because", c["source_bounded_note"])

    def test_the_census_carries_the_rule_the_sunset_and_the_named_fail_closed_list(self):
        sp = _spine({"A": ["2023-02-01", "2023-05-10", "2023-08-02"], "FPI": []})
        c = sp.census()
        self.assertIn("UNKNOWN", c["rule"])
        self.assertEqual(c["code_sunsets"]["34"]["last"], "2024-12-17")
        self.assertIn("never be read as a signal", c["sunset_note"])
        self.assertEqual(c["fail_closed_names"], ["FPI"],
                         "fail-closed names must be LISTED, not merely counted")
        self.assertEqual(c["n_fail_closed"], 1)
        self.assertEqual(c["per_name_year"]["A"]["2023"], SP.COVERED)


class TestConstruction(unittest.TestCase):

    def test_a_requested_name_absent_from_the_source_becomes_fail_closed_not_dropped(self):
        """A name missing from the table entirely cannot be flagged, and an unflagged missing
        name is the fail-open bug wearing a different hat."""
        sp = SP.EventSpine({"KNOWN": ["2023-05-10"], "NEVER_SEEN": []})
        self.assertIn("NEVER_SEEN", sp.zero_coverage)
        self.assertEqual(sp.coverage("NEVER_SEEN"), SP.FAIL_CLOSED)
        self.assertIn("NEVER_SEEN", sp.census()["fail_closed_names"])

    def test_dates_are_sorted_deduplicated_and_case_insensitive(self):
        sp = SP.EventSpine({"T": ["2023-08-02", "2023-05-10", "2023-05-10"]})
        self.assertEqual(sp.dates("t"), ["2023-05-10", "2023-08-02"])

    def test_next_after_is_strict(self):
        sp = _spine({"T": ["2023-05-10", "2023-08-02"]})
        self.assertEqual(sp.next_after("T", "2023-05-10"), "2023-08-02")
        self.assertEqual(sp.next_after("T", "2023-05-09"), "2023-05-10")


if __name__ == "__main__":
    unittest.main(verbosity=2)
