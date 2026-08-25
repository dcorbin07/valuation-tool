"""F-8 ARMED — the first SHORT book, and the proof that family (A) actually bought something.

HANDOFF 72 called F-8 *"the closest book in the fleet to armable, blocked on NOTHING ELSE"*
than S3-I3's registration. Registering it should therefore have made F-8 writable with no
further infrastructure — and this suite is that claim being tested rather than repeated.

  * **IT READS THE PUBLISHED ARTIFACT, NEVER THE SCORING PATH** — the declaration says so
    twice, and `data_export/` is the one place that is both tracked AND shipped in the image.
  * **THE SHORT SEAM IS CHECKED BY THE RULE ITSELF**, not only by the cycle's gate. A rule
    that would place a short order is the last place that should assume somebody else checked.
  * **THE TIE-BREAK IS AMENDED IN THE OPEN** because the declared source has no composite
    score, and the amendment's stated limit — the weight cap compressing the top — is pinned
    here rather than left as prose.

    python tests/test_fleet_f8.py
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                # noqa: E402
from valuation.edge import fleet_books as FB         # noqa: E402
from valuation.edge import assignment as A           # noqa: E402

TODAY = dt.date(2026, 8, 24)
DECL = {"structure": {"moneyness": 0.95, "dte": 30}, "concurrency_cap": 5}


def _row(t, weight, entry_date="2026-08-24", price=100.0):
    return {"ticker": t, "weight": str(weight), "entry_date": entry_date,
            "entry_price": str(price), "note": "quote-marked"}


def _opt(strike, exp, right="put", sym=None):
    return {"symbol": sym or ("O%s%d" % (exp.replace("-", ""), int(strike))),
            "strike": strike, "option_type": right, "expiration_date": exp,
            "bid": 1.0, "ask": 1.2}


class Provider:
    def get_option_chain(self, ticker, dte_range=(20, 45)):
        exp = (TODAY + dt.timedelta(days=30)).isoformat()
        return [_opt(90.0, exp, sym=ticker + "P90"), _opt(95.0, exp, sym=ticker + "P95")]


class Broker:
    def __init__(self):
        self.placed = []

    def place_option(self, occ, underlying, side, qty, price=None, duration="day"):
        self.placed.append({"occ": occ, "side": side, "qty": qty})
        return {"order": {"id": "1"}, "ok": True}

    def order(self, oid):
        return {"id": oid, "status": "filled", "avg_fill_price": 1.0,
                "exec_quantity": 1, "quantity": 1}

    def cancel(self, oid):
        return {"ok": True}

    def quotes(self, syms):
        return {}


class TheSelection(unittest.TestCase):

    def test_only_names_ENTERING_TODAY_qualify(self):
        rows = [_row("AAA", 0.02), _row("BBB", 0.03, entry_date="2026-08-11")]
        got = FB.f8_select(rows, TODAY, set(), cap=5)
        self.assertEqual([p["ticker"] for p in got], ["AAA"])

    def test_a_day_with_no_new_entries_returns_nothing(self):
        """A market observation, not a build gap -- `cycle()` reports the two apart."""
        rows = [_row("AAA", 0.02, entry_date="2026-08-11")]
        self.assertEqual(FB.f8_select(rows, TODAY, set(), cap=5), [])

    def test_the_tie_break_is_weight_then_alphabetical(self):
        """Amendment 1: the declared 'composite score' is not in the declared source."""
        rows = [_row("CCC", 0.01), _row("AAA", 0.03), _row("BBB", 0.03)]
        self.assertEqual([p["ticker"] for p in FB.f8_select(rows, TODAY, set(), cap=5)],
                         ["AAA", "BBB", "CCC"])

    def test_the_capped_weight_case_the_amendment_WARNS_about(self):
        """Where the weight cap binds, two different composite scores share a weight and the
        alphabetical tie-break decides -- which is NOT what 'highest composite score' would
        have done. Pinned so the amendment's stated limit is a demonstrated one."""
        rows = [_row("ZZZ", 0.023), _row("AAA", 0.023)]
        self.assertEqual([p["ticker"] for p in FB.f8_select(rows, TODAY, set(), cap=1)],
                         ["AAA"])

    def test_the_cap_counts_names_already_held(self):
        rows = [_row("A%d" % i, 0.05 - i / 1000.0) for i in range(6)]
        self.assertEqual(len(FB.f8_select(rows, TODAY, set(), cap=5)), 5)
        self.assertEqual(len(FB.f8_select(rows, TODAY, {"H1", "H2", "H3"}, cap=5)), 2)
        self.assertEqual(FB.f8_select(rows, TODAY, {"H%d" % i for i in range(5)}, cap=5), [])

    def test_a_held_name_is_not_re_entered(self):
        rows = [_row("AAA", 0.02), _row("BBB", 0.01)]
        self.assertEqual([p["ticker"] for p in FB.f8_select(rows, TODAY, {"AAA"}, cap=5)],
                         ["BBB"])

    def test_cap_has_NO_default(self):
        with self.assertRaises(TypeError):
            FB.f8_select([], TODAY, set())


class TheShortSeam(unittest.TestCase):

    def setUp(self):
        self._saved = F._PROVIDER

    def tearDown(self):
        F._PROVIDER = self._saved

    def test_the_rule_REFUSES_ITSELF_when_S3I3_is_not_registered(self):
        """Belt and braces. The cycle's gate refuses every short book without a provider, and
        a rule that would place a SHORT order is the last place to assume that ran."""
        F._PROVIDER = None
        out = FB.f8_csp_entry_financing(DECL, REPO, provider=Provider(), broker=Broker(),
                                        today=TODAY, holdings=[_row("AAA", 0.02)])
        self.assertEqual(out, [])

    def test_with_S3I3_registered_it_sells_the_declared_put(self):
        A.register()
        b = Broker()
        out = FB.f8_csp_entry_financing(DECL, REPO, provider=Provider(), broker=b,
                                        today=TODAY, holdings=[_row("AAA", 0.02)])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["symbol"], "AAA")
        self.assertEqual(out[0]["side"], "sell_to_open", "a CSP SELLS the put")
        self.assertEqual(out[0]["occ"], "AAAP95", "0.95 x 100 = 95, the listed strike")
        self.assertEqual(out[0]["qty"], FB.F8_QTY)
        self.assertIn(out[0]["arm"], ("A", "B"), "every fleet order carries an F-1 arm")

    def test_registering_S3I3_is_what_makes_the_declaration_VALID(self):
        """Family (A), end to end on this book: the one refusal that blocked it, gone."""
        with open(os.path.join(REPO, "DECL_f8_csp_entry_financing.md"),
                  encoding="utf-8") as fh:
            decl = F.parse_declaration(fh.read())["declaration"]
        F._PROVIDER = None
        before = F.validate_declaration(decl, book="f8_csp_entry_financing")
        self.assertIn("SHORT_BOOK_WITHOUT_ASSIGNMENT", before["refusals"])
        A.register()
        after = F.validate_declaration(decl, book="f8_csp_entry_financing")
        self.assertTrue(after["ok"], after["refusals"])


class ThePublishedSource(unittest.TestCase):

    def test_it_reads_data_export_and_not_the_scoring_path(self):
        rows = FB.read_published_holdings(REPO)
        self.assertTrue(rows, "the published holdings file is missing")
        self.assertIn("entry_date", rows[0])
        self.assertIn("weight", rows[0])
        self.assertNotIn("composite", rows[0],
                         "if a composite ever appears, amendment 1 should be revisited")

    def test_a_missing_artifact_yields_no_entries_rather_than_raising(self):
        self.assertEqual(FB.read_published_holdings(os.path.join(REPO, "nope")), [])

    def test_the_rule_is_registered_and_PLACES_orders(self):
        FB.register_all()
        self.assertIsNotNone(F.entry_rule("f8_csp_entry_financing"))
        self.assertTrue(F.places_orders("f8_csp_entry_financing"))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
