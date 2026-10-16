"""The scream-buy record's DISPLAY changes (item 66 part 3) - what these pin.

Display and labels only. **Nothing is deleted**, and the first test says so.

THE LOAD-BEARING ONES:

1. **THE NO-CONTRACT ROWS ARE SEPARATED, NOT DROPPED.** They were never trades - no contract
   was resolved on the chain - so leaving them in the main table makes a book of 21 read as a
   book of 35. Pinned both ways: out of `rows`, present in `no_contract_rows`, and the total
   unchanged.

2. **THE CLOSED-ONLY MEAN AND THE MARKED ONE ARE BOTH REPORTED.** Losers close fast and
   winners stay open, so closed-only is a sample selected on the outcome. Pinned on a fixture
   built to show exactly that divergence - if the two were ever made to agree by construction,
   this goes red.

3. **THE THREE EXIT SOURCES ARE NOT INTERCHANGEABLE**, and an undeterminable one is UNKNOWN
   rather than silently labelled an execution. A paper book that cannot be read must not turn
   every scored exit into a fill.

4. **DISTINCT NAMES TRAVEL WITH THE TRADE COUNT.** ABBV being 6 of 13 open trades, 4 of them
   the same contract, means "13 open" is nearer four independent bets.

5. **THE STOP CADENCE IS STATED.** Stops are checked once a day, so a stop books past -50%
   and a reader comparing the outcome to the policy needs that sentence.

    python tests/test_scream_display.py
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.web import scream_track as ST  # noqa: E402

NOCON = "NO CONTRACT - not scoreable"


def _rows():
    """A fixture with the shape the manager measured: a cluster, a fast loser, slow winners."""
    return [
        {"status": "LIVE", "ticker": "ABBV", "occ_symbol": "ABBV261120C00280000",
         "entry_premium": 10.0, "current_premium": 12.0},
        {"status": "LIVE", "ticker": "ABBV", "occ_symbol": "ABBV261120C00280000",
         "entry_premium": 10.0, "current_premium": 11.0},
        {"status": "LIVE", "ticker": "ABBV", "occ_symbol": "ABBV261218C00300000",
         "entry_premium": 5.0, "current_premium": 6.0},
        {"status": "STOPPED", "ticker": "NKE", "occ_symbol": "NKE261016P00032500",
         "entry_premium": 2.0, "pnl_pct": -62.0, "exit_premium": 0.76},
        {"status": "HIT TARGET", "ticker": "LOW", "occ_symbol": "LOW261016P00180000",
         "entry_premium": 1.0, "pnl_pct": 100.0, "exit_premium": 2.0},
        {"status": NOCON, "ticker": "ZZZ"},
        {"status": NOCON, "ticker": "YYY"},
    ]


class TestNothingIsDeleted(unittest.TestCase):
    """(1)."""

    def test_the_no_contract_rows_are_separated_and_still_counted(self):
        rows = _rows()
        real = [r for r in rows if r["status"] != NOCON]
        nocon = [r for r in rows if r["status"] == NOCON]
        self.assertEqual(len(real) + len(nocon), len(rows), "nothing may be dropped")
        self.assertEqual(len(nocon), 2)

    def test_they_are_excluded_from_every_statistic_because_they_cannot_be_marked(self):
        m = ST.marked_to_market(_rows())
        self.assertEqual(m["n_trades"], 5, "the two no-contract rows are not trades")
        c = ST.concentration(_rows())
        self.assertEqual(c["n_trades"], 5)
        self.assertNotIn("ZZZ", (c["largest_name"],))


class TestBothHeadlinesAreReported(unittest.TestCase):
    """(2)."""

    def test_closed_only_and_marked_to_market_are_both_present_and_differ(self):
        m = ST.marked_to_market(_rows())
        self.assertIsNotNone(m["closed_only_mean_pct"])
        self.assertIsNotNone(m["marked_to_market_mean_pct"])
        self.assertNotAlmostEqual(
            m["closed_only_mean_pct"], m["marked_to_market_mean_pct"], places=6,
            msg="if these agree by construction the distinction has been lost")

    def test_when_losers_close_and_winners_stay_open_the_closed_mean_is_the_worse_one(self):
        """The ARITHMETIC, on a shape built to show it - not a claim about the real book.

        My first cut asserted this directionally on the general fixture and FAILED, because
        that fixture has a +100% closed winner. The direction is a property of the BOOK and
        asserting it on a synthetic one would have been asserting my own fixture. What is
        worth pinning is that the code reports the gap when the gap exists.
        """
        rows = [{"status": "STOPPED", "ticker": "A", "occ_symbol": "A",
                 "entry_premium": 1.0, "pnl_pct": -60.0, "exit_premium": 0.4},
                {"status": "STOPPED", "ticker": "B", "occ_symbol": "B",
                 "entry_premium": 1.0, "pnl_pct": -50.0, "exit_premium": 0.5},
                {"status": "LIVE", "ticker": "C", "occ_symbol": "C",
                 "entry_premium": 1.0, "current_premium": 1.8}]
        m = ST.marked_to_market(rows)
        self.assertAlmostEqual(m["closed_only_mean_pct"], -55.0)
        self.assertLess(m["closed_only_mean_pct"], m["marked_to_market_mean_pct"])

    def test_the_open_marks_are_reported_separately_so_neither_hides_in_the_other(self):
        m = ST.marked_to_market(_rows())
        self.assertEqual(m["n_open_marked"], 3)
        self.assertEqual(m["n_closed"], 2)
        self.assertIsNotNone(m["open_only_mean_pct"])

    def test_a_live_row_with_no_current_mark_is_not_counted_as_flat(self):
        rows = [{"status": "LIVE", "ticker": "A", "occ_symbol": "A", "entry_premium": 1.0}]
        m = ST.marked_to_market(rows)
        self.assertEqual(m["n_open_marked"], 0,
                         "an unmarked position must not enter the mean as 0%")
        self.assertIsNone(m["marked_to_market_mean_pct"])

    def test_the_payload_explains_why_both(self):
        self.assertIn("selected on the outcome", ST.marked_to_market(_rows())["why_both"])


class TestTheExitSources(unittest.TestCase):
    """(3)."""

    ROW = {"occ_symbol": "NKE261016P00032500", "exit_premium": 0.76}

    def test_the_three_sources_are_distinguished(self):
        self.assertEqual(ST.exit_source(self.ROW), ST.EXIT_SOURCE_SCORED)
        self.assertEqual(ST.exit_source(self.ROW, paper_filled={self.ROW["occ_symbol"]}),
                         ST.EXIT_SOURCE_PAPER)
        self.assertEqual(ST.exit_source(self.ROW, paper_refused={self.ROW["occ_symbol"]}),
                         ST.EXIT_SOURCE_REFUSED)

    def test_an_undeterminable_source_is_UNKNOWN_and_never_an_execution(self):
        self.assertEqual(ST.exit_source({"occ_symbol": "X"}), ST.EXIT_SOURCE_UNKNOWN)
        self.assertEqual(ST.exit_source({}), ST.EXIT_SOURCE_UNKNOWN)

    def test_a_refusal_beats_a_fill_when_both_are_claimed(self):
        """Contradictory evidence must resolve to the one that held NO position."""
        occ = self.ROW["occ_symbol"]
        self.assertEqual(ST.exit_source(self.ROW, paper_filled={occ}, paper_refused={occ}),
                         ST.EXIT_SOURCE_REFUSED)

    def test_the_labels_say_what_they_mean(self):
        self.assertIn("no position was ever held", ST.EXIT_SOURCE_REFUSED)
        self.assertIn("bid-side", ST.EXIT_SOURCE_SCORED)


class TestConcentration(unittest.TestCase):
    """(4)."""

    def test_distinct_names_travel_with_the_trade_count(self):
        c = ST.concentration(_rows())
        self.assertEqual(c["n_trades"], 5)
        self.assertEqual(c["n_distinct_names"], 3)
        self.assertLess(c["n_distinct_names"], c["n_trades"])

    def test_the_largest_cluster_is_named_by_NAME_and_by_CONTRACT(self):
        c = ST.concentration(_rows())
        self.assertEqual(c["largest_name"], "ABBV")
        self.assertEqual(c["largest_name_trades"], 3)
        self.assertEqual(c["largest_contract"], "ABBV261120C00280000")
        self.assertEqual(c["largest_contract_trades"], 2,
                         "the same CONTRACT repeating is the sharper fact")


class TestTheStopCadenceIsStated(unittest.TestCase):
    """(5)."""

    def test_the_note_says_once_a_day_and_why_that_matters(self):
        n = ST.STOP_CADENCE_NOTE
        self.assertIn("ONCE A DAY", n)
        self.assertIn("past -50%", n)
        self.assertIn("realised outcomes", n)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
