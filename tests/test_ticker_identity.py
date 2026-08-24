"""
S3-I5 — the ticker-reuse adjudication. Offline, synthetic registry, no `data/`. Run:

    python tests/test_ticker_identity.py

WHAT THESE PIN.

1. **FAIL-CLOSED.** An unadjudicated symbol is `UNKNOWN`, never `SAME_COMPANY`. The whole
   instrument exists because a fail-open default turns an unexamined ticker into an implicit
   clean bill of health -- which is what `pre_panel_history` was invented to stop.

2. **THE BOUNDARY IS EXACT.** `firstpricedate` on 1 January is SAME_COMPANY; on 31 December is
   SPLIT_YEAR; on 1 January of the NEXT year is REUSED. Off-by-one here silently promotes a
   reused year to usable.

3. **SPLIT_YEAR IS NOT ROUNDABLE.** It carries a cut date. Rounding it down loses a year of
   real data; rounding it up imports another company's.

4. **A DISTINCT-PERMATICKER CHECK WOULD HAVE PASSED THE REUSED CASES.** Pinned with a fixture
   that has ONE permaticker and is still REUSED, because that is the trap this module was built
   around and a future simplification would walk straight back into it.

5. **THE STRIKE TEST CANNOT OVERTURN THE REGISTRY.** It is one-sided: a big step corroborates
   reuse, a small step means "found nothing". `SE` is the live case -- 1.03 across Spectra
   Energy -> Sea Ltd, a coincidence of price level.
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import ticker_identity as TI                        # noqa: E402


def _tickers_csv(rows):
    """A minimal TICKERS extract. One row per (ticker, table), like the real snapshot."""
    p = os.path.join(tempfile.mkdtemp(), "tickers.csv")
    cols = ["table", "permaticker", "ticker", "name", "firstpricedate", "lastpricedate",
            "isdelisted", "cusips"]
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r.get(c, "")) for c in cols) + "\n")
    return p


def _table(rows, flagged=None, strike_fn=None):
    return TI.build({r["ticker"] for r in rows}, _tickers_csv(rows), "",
                    strike_fn=strike_fn, flagged_years=flagged or {})


SNOWLIKE = [{"table": "SEP", "permaticker": "631956", "ticker": "SNOW", "name": "SNOWFLAKE INC",
             "firstpricedate": "2020-09-16", "lastpricedate": "2026-07-31", "isdelisted": "N",
             "cusips": "833445109"}]


class TestFailClosed(unittest.TestCase):

    def test_an_unadjudicated_symbol_is_unknown_never_same_company(self):
        t = _table(SNOWLIKE)
        self.assertEqual(t.verdict("NEVERSEEN", 2016), TI.UNKNOWN)
        self.assertNotEqual(t.verdict("NEVERSEEN", 2016), TI.SAME_COMPANY)
        self.assertIsNone(t.usable_from("NEVERSEEN", 2016))

    def test_a_symbol_present_but_without_a_listing_date_is_unknown(self):
        t = _table([dict(SNOWLIKE[0], firstpricedate="")])
        self.assertEqual(t.verdict("SNOW", 2016), TI.UNKNOWN)


class TestTheBoundaryIsExact(unittest.TestCase):

    def _t(self, fpd):
        return _table([dict(SNOWLIKE[0], firstpricedate=fpd)])

    def test_first_of_january_is_same_company(self):
        self.assertEqual(self._t("2017-01-01").verdict("SNOW", 2017), TI.SAME_COMPANY)

    def test_thirty_first_of_december_is_a_split_year(self):
        self.assertEqual(self._t("2017-12-31").verdict("SNOW", 2017), TI.SPLIT_YEAR)

    def test_first_of_january_next_year_is_reused(self):
        self.assertEqual(self._t("2018-01-01").verdict("SNOW", 2017), TI.REUSED)

    def test_a_year_after_listing_is_same_company(self):
        self.assertEqual(self._t("2020-09-16").verdict("SNOW", 2021), TI.SAME_COMPANY)


class TestSplitYearIsNotRoundable(unittest.TestCase):

    def test_split_year_carries_the_cut_date(self):
        t = _table([dict(SNOWLIKE[0], firstpricedate="2018-12-07", ticker="MRNA")])
        self.assertEqual(t.verdict("MRNA", 2018), TI.SPLIT_YEAR)
        self.assertEqual(t.usable_from("MRNA", 2018), "2018-12-07")

    def test_reused_has_no_usable_date_and_same_company_starts_at_january(self):
        t = _table([dict(SNOWLIKE[0], firstpricedate="2020-09-16")])
        self.assertIsNone(t.usable_from("SNOW", 2016))
        self.assertEqual(t.usable_from("SNOW", 2021), "2021-01-01")


class TestThePermatickerTrap(unittest.TestCase):

    def test_one_permaticker_is_not_evidence_of_one_company(self):
        """TICKERS is a CURRENT snapshot, so a reused ticker still shows a single permaticker.

        This fixture is what a distinct-permaticker check would have called clean: three rows,
        one permaticker, and a 2016 year that provably is not this company.
        """
        rows = [dict(SNOWLIKE[0], table=t) for t in ("SEP", "SF1", "SF2")]
        t = _table(rows, flagged={"SNOW": [2016, 2017]})
        rec = t.evidence("SNOW")
        self.assertEqual(rec["registry_rows"], 3)
        self.assertFalse(rec["permaticker_disagreement"],
                         "the fixture must have ONE permaticker or it does not test the trap")
        self.assertEqual(t.verdict("SNOW", 2016), TI.REUSED)
        self.assertEqual(rec["year_verdicts"], {"2016": TI.REUSED, "2017": TI.REUSED})


class TestTheStrikeTestIsOneSided(unittest.TestCase):

    def test_a_small_step_does_not_overturn_a_reused_verdict(self):
        """SE: 1.03 across Spectra Energy -> Sea Ltd. Similar price, different company."""
        rows = [dict(SNOWLIKE[0], ticker="SE", name="SEA LTD", firstpricedate="2017-10-20")]
        t = _table(rows, flagged={"SE": [2016]}, strike_fn=lambda s, y: 40.0)
        rec = t.evidence("SE")
        self.assertEqual(rec["behavioural"], "CONTINUOUS")
        self.assertTrue(rec["evidence_disagreement"])
        self.assertIn("cannot refute", rec["disagreement_note"])
        self.assertEqual(t.verdict("SE", 2016), TI.REUSED,
                         "a no-step behavioural reading must NOT flip the registry verdict")

    def test_a_large_step_corroborates_and_raises_no_disagreement(self):
        t = _table(SNOWLIKE, flagged={"SNOW": [2016]},
                   strike_fn=lambda s, y: 10.0 if y < 2020 else 200.0)
        rec = t.evidence("SNOW")
        self.assertEqual(rec["behavioural"], "STEP")
        self.assertFalse(rec["evidence_disagreement"])
        self.assertGreaterEqual(rec["strike_step"], TI.STEP_SUSPECT)

    def test_the_threshold_is_shared_with_the_prior_audit(self):
        """One definition of 'a step'. Two tools with two thresholds is the drift this project
        keeps paying for."""
        self.assertEqual(TI.STEP_SUSPECT, 1.5)


class TestTheTable(unittest.TestCase):

    def test_round_trips_through_json_with_its_rules_attached(self):
        t = _table(SNOWLIKE, flagged={"SNOW": [2016]})
        p = os.path.join(tempfile.mkdtemp(), "adj.json")
        payload = t.to_json(p)
        self.assertEqual(payload["trials"], 0)
        self.assertIn("FIXED", payload["class"])
        self.assertIn("CURRENT snapshot", payload["why_not_permaticker"])
        self.assertIn(TI.UNKNOWN, payload["verdicts"])
        back = TI.IdentityTable.from_json(p)
        self.assertEqual(back.verdict("SNOW", 2016), TI.REUSED)
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["symbols"]["SNOW"]["firstpricedate"], "2020-09-16")

    def test_a_symbol_absent_from_the_registry_is_recorded_not_dropped(self):
        t = TI.build(["GHOST"], _tickers_csv(SNOWLIKE), "", flagged_years={"GHOST": [2016]})
        rec = t.evidence("GHOST")
        self.assertEqual(rec["registry_rows"], 0)
        self.assertIn("UNKNOWN", rec["note"])
        self.assertEqual(t.verdict("GHOST", 2016), TI.UNKNOWN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
