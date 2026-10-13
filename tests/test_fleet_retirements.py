"""FLEET_RETIREMENTS.md — the record, and the lock that makes it more than prose.

1. **A RETIREMENT IS MECHANICAL.** A retirement written only in prose is one somebody re-arms by
   adding a line to `RULES`. `register_all` refuses any retired book, so undoing one means
   deleting its row and saying why — which shows in the diff.

2. **THE READER FAILS OPEN, DELIBERATELY.** A missing or unreadable record must never silently
   disarm a live book. Every book retired today is already absent from `RULES`, so the refusal
   is a SECOND lock and never the only one — and that asymmetry is pinned in both directions.

3. **A RETIREMENT CLOSES A DECLARATION, NEVER A HYPOTHESIS**, and the file has to say so.

    python tests/test_fleet_retirements.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet as F  # noqa: E402
from valuation.edge import fleet_books as FB  # noqa: E402


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


RETIRED = ("f17_vrp_percentile_sells", "f5_ivcheap", "f12_postevent_reversal",
           "f13_second_event", "f18_boring_book", "f6_collar_ledger",
           "f20_married_put_storm", "testbook", "f4_eventfree_premium", "f10_clean_csp")


class TheRecord(unittest.TestCase):
    def test_every_named_book_is_read_back(self):
        got = F.retired_books()
        for b in RETIRED:
            self.assertIn(b, got, "%s is not read back from the record" % b)
        self.assertEqual(len(got), len(RETIRED),
                         "the reader picked up a row that is not a book: %s"
                         % sorted(set(got) - set(RETIRED)))

    def test_every_row_carries_the_RESULT_that_closed_it(self):
        """A retirement without a landed result is an opinion."""
        for b, why in F.retired_books().items():
            self.assertGreater(len(why), 60, "%s: the reason is too short to be a result" % b)

    def test_the_surviving_books_are_NOT_retired(self):
        """The positive control: if everything read as retired the lock would be vacuous."""
        for b in ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin", "f14_fda_nohump",
                  "f15_insider_cluster", "f2_menu_gate", "f19_density_gate",
                  "f1_fill_ab", "f3_bear_puts", "f8_csp_entry_financing",
                  "f11_dip_reject_puts"):
            self.assertFalse(F.is_retired(b), "%s was retired and should not be" % b)

    def test_it_closes_declarations_and_NOT_hypotheses(self):
        t = _src("FLEET_RETIREMENTS.md")
        self.assertIn("CLOSES A DECLARATION, NEVER A HYPOTHESIS", t)
        self.assertIn("It retires **no hypothesis**", t)

    def test_F4_and_F10_retire_only_their_DECLARED_EXPRESSION(self):
        """They are the two the review offered a re-declaration to, and the reason they are not
        re-declared today is `MB8` — an income may not travel across populations."""
        why = F.retired_books()
        for b in ("f4_eventfree_premium", "f10_clean_csp"):
            self.assertIn("DECLARED 0.90-MONEYNESS EXPRESSION ONLY", why[b])
        t = _src("FLEET_RETIREMENTS.md")
        self.assertIn("MB8", t)
        self.assertIn("+0.2957", t, "the named cheap next step is missing its measured figure")

    def test_F2_and_F19_are_NOT_retired_and_are_folded_in_instead(self):
        t = _src("FLEET_RETIREMENTS.md")
        self.assertIn("F-2 AND F-19 ARE NOT RETIRED", t)
        for b in ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin"):
            d = _src("DECL_%s.md" % b)
            self.assertIn("menu_depth", d)
            self.assertIn("density_percentile", d)

    def test_the_F14_and_F15_input_findings_are_MEASURED_and_stated(self):
        t = _src("FLEET_RETIREMENTS.md")
        self.assertIn("6,688,777", t, "F-15's measured row count is missing")
        self.assertIn("28.52%", t, "F-15's measured missing-code share is missing")
        self.assertIn("NO catalyst data anywhere", t, "F-14's measured finding is missing")
        self.assertIn("INVERTS THE REVIEW'S PRIORITY ORDERING", t)


class TheLock(unittest.TestCase):
    def test_register_all_refuses_a_retired_book(self):
        """Mutation: put a retired book into `RULES` and it must NOT arm."""
        real = dict(FB.RULES)
        try:
            FB.RULES["f17_vrp_percentile_sells"] = (lambda *a, **k: [], True)
            out = FB.register_all()
            self.assertNotIn("f17_vrp_percentile_sells", out["registered"])
            self.assertIn("f17_vrp_percentile_sells", out["refused_retired"])
        finally:
            FB.RULES.clear()
            FB.RULES.update(real)

    def test_and_it_is_NOT_vacuous_a_live_book_still_arms(self):
        out = FB.register_all()
        self.assertIn("f3_bear_puts", out["registered"])
        self.assertEqual(out["refused_retired"], [])

    def test_a_MISSING_record_retires_NOTHING(self):
        """Fails OPEN on purpose: a missing record must never silently disarm a live book."""
        root = tempfile.mkdtemp()
        try:
            self.assertEqual(F.retired_books(root), {})
            self.assertFalse(F.is_retired("f17_vrp_percentile_sells", root))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_no_retired_book_is_in_RULES_today(self):
        """The FIRST lock. Both must hold, or one of them is doing nothing."""
        for b in RETIRED:
            self.assertNotIn(b, FB.RULES)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
