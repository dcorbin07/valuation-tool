"""
S3-I2 — the catalyst calendar. Offline, synthetic fetch records, NO NETWORK. Run:

    python tests/test_catalyst_calendar.py

WHAT THESE PIN.

1. **NEVER BACKFILLED FROM MEMORY** is a code path, not a promise. `add_snapshot` raises on a
   row whose source has no successful fetch in the same snapshot, so there is no way for a
   remembered date, a reconstructed schedule or a hand-typed correction to become a row. It
   RAISES rather than dropping — a silently discarded row makes a partial write look complete.

2. **IMPRECISE IS NEVER ROUNDED.** Measured on the first live pull: 328 of 452 rows are month-
   or quarter-precision. Rounding those to the first of the month invents a day the source never
   published, which is backfilling from inference and no better for being arithmetic.

3. **ABSENT, BLOCKED, EMPTY AND UNREACHABLE ARE FOUR DIFFERENT FACTS.** A table that cannot
   tell them apart reads as "no catalysts" on the day a scraper breaks — the fail-open shape
   this project keeps paying for. In particular BLOCKED means *we did not have permission to
   look*, not *we looked and found nothing*.

4. **APPEND-ONLY.** The value of this table is the record of what was published on which day.
   A run that rewrote a snapshot would destroy the only thing being accrued.
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import catalyst_calendar as CC                      # noqa: E402


def _fetch(sid="pdufa_bio_events", status=CC.STATUS_OK):
    return {"source_id": sid, "url": "https://example.invalid/x", "fetched_utc": "2026-08-23T00:00:00+00:00",
            "status": status, "http": 200 if status == CC.STATUS_OK else None,
            "sha256": "0" * 64}


def _row(date="2026-12-01", precision=CC.DAY, sid="pdufa_bio_events", ticker="ABCD"):
    return {"source_id": sid, "source_row_id": f"x_{ticker}_{date}", "ticker": ticker,
            "company": "ACME", "event_type": "PDUFA", "event_name": "n",
            "date_raw": date, "precision": precision, "precision_raw": precision,
            "status": "Upcoming", "url": "https://example.invalid/e"}


class TestNeverBackfilled(unittest.TestCase):

    def test_a_row_with_no_fetch_record_is_refused(self):
        cal = CC.CatalystCalendar()
        with self.assertRaises(ValueError) as cm:
            cal.add_snapshot([_fetch("pdufa_bio_events")],
                             [_row(sid="remembered_from_training_data")])
        self.assertIn("never", str(cm.exception).lower())
        self.assertEqual(cal.snapshots, [], "a refused snapshot must not be half-written")

    def test_a_row_citing_a_failed_fetch_is_refused(self):
        """The subtler case: the source WAS contacted, and it failed. Rows attributed to it can
        only have come from somewhere else."""
        cal = CC.CatalystCalendar()
        with self.assertRaises(ValueError):
            cal.add_snapshot([_fetch(status=CC.STATUS_UNREACHABLE)], [_row()])

    def test_it_raises_rather_than_dropping_the_offending_rows(self):
        """Dropping would let a partial write look like a complete one."""
        cal = CC.CatalystCalendar()
        with self.assertRaises(ValueError):
            cal.add_snapshot([_fetch()], [_row(), _row(sid="ghost")])
        self.assertEqual(len(cal.snapshots), 0)

    def test_a_clean_snapshot_is_accepted(self):
        cal = CC.CatalystCalendar()
        snap = cal.add_snapshot([_fetch()], [_row(), _row(ticker="EFGH")])
        self.assertEqual(snap["n_rows"], 2)
        self.assertEqual(len(cal.snapshots), 1)


class TestPrecisionFailsClosed(unittest.TestCase):

    def test_an_imprecise_row_has_no_usable_date_and_is_not_rounded(self):
        cal = CC.CatalystCalendar()
        r = _row(date="2026-11", precision=CC.IMPRECISE)
        self.assertIsNone(cal.usable_date(r))
        self.assertNotEqual(cal.usable_date(r), "2026-11-01",
                            "an imprecise date must never be rounded to a day")

    def test_unknown_precision_is_also_unusable(self):
        cal = CC.CatalystCalendar()
        self.assertIsNone(cal.usable_date(_row(precision=CC.UNKNOWN_PRECISION)))

    def test_only_day_precision_rows_reach_forward_rows(self):
        cal = CC.CatalystCalendar()
        cal.add_snapshot([_fetch()], [
            _row(date="2027-01-05", precision=CC.DAY, ticker="AAA"),
            _row(date="2027-02", precision=CC.IMPRECISE, ticker="BBB"),
        ])
        fwd = cal.forward_rows(as_of="2026-08-23")
        self.assertEqual([r["ticker"] for r in fwd], ["AAA"])
        loose = cal.forward_rows(as_of="2026-08-23", usable_only=False)
        self.assertEqual(sorted(r["ticker"] for r in loose), ["AAA", "BBB"])

    def test_forward_is_strict_and_excludes_today(self):
        cal = CC.CatalystCalendar()
        cal.add_snapshot([_fetch()], [_row(date="2026-08-23")])
        self.assertEqual(cal.forward_rows(as_of="2026-08-23"), [])
        self.assertEqual(len(cal.forward_rows(as_of="2026-08-22")), 1)


class TestFourDifferentFacts(unittest.TestCase):

    def test_no_snapshot_does_not_read_as_no_catalysts(self):
        cov = CC.CatalystCalendar().coverage()
        self.assertEqual(cov["snapshots"], 0)
        self.assertIn("NOT", cov["note"])

    def test_blocked_and_unreachable_and_empty_are_distinguishable(self):
        cal = CC.CatalystCalendar()
        cal.add_snapshot([_fetch("pdufa_bio_events", CC.STATUS_OK),
                          _fetch("sp_index_announcements", CC.STATUS_BLOCKED),
                          _fetch("ftse_russell_recon", CC.STATUS_UNREACHABLE)],
                         [_row()])
        cov = cal.coverage()
        self.assertEqual(cov["sources_blocked"], ["sp_index_announcements"])
        self.assertEqual(cov["sources_unreachable"], ["ftse_russell_recon"])
        self.assertNotEqual(CC.STATUS_BLOCKED, CC.STATUS_EMPTY)
        self.assertNotEqual(CC.STATUS_BLOCKED, CC.STATUS_UNREACHABLE)

    def test_the_index_sources_are_declared_blocked_with_a_stated_reason(self):
        """The index half of S3-I2 does not ship as an empty table. It ships as BLOCKED, with
        why, because permission could not be established rather than because nothing was there."""
        for sid in ("sp_index_announcements", "ftse_russell_recon"):
            src = CC.SOURCES[sid]
            self.assertEqual(src["preset_status"], CC.STATUS_BLOCKED)
            self.assertIn("UNDETERMINABLE", src["robots"])
            self.assertEqual(src["kind"], "INDEX_RECONSTITUTION")

    def test_a_blocked_source_is_never_fetched(self):
        """No network: `fetch` must short-circuit on a preset status without opening a socket."""
        rec = CC.fetch("sp_index_announcements")
        self.assertEqual(rec["status"], CC.STATUS_BLOCKED)
        self.assertIsNone(rec["http"])
        self.assertIn("not fetched", rec["note"])


class TestAppendOnly(unittest.TestCase):

    def test_a_second_snapshot_does_not_replace_the_first(self):
        p = os.path.join(tempfile.mkdtemp(), "cal.json")
        cal = CC.CatalystCalendar()
        cal.add_snapshot([_fetch()], [_row(ticker="AAA")], observed_utc="2026-08-23T00:00:00+00:00")
        cal.save(p)
        again = CC.CatalystCalendar.load(p)
        again.add_snapshot([_fetch()], [_row(ticker="BBB")],
                           observed_utc="2026-08-24T00:00:00+00:00")
        again.save(p)
        back = CC.CatalystCalendar.load(p)
        self.assertEqual(len(back.snapshots), 2)
        self.assertEqual(back.snapshots[0]["rows"][0]["ticker"], "AAA")
        self.assertEqual(back.snapshots[1]["rows"][0]["ticker"], "BBB")
        self.assertEqual(back.latest()["rows"][0]["ticker"], "BBB")

    def test_the_saved_payload_carries_its_own_honest_note(self):
        p = os.path.join(tempfile.mkdtemp(), "cal.json")
        cal = CC.CatalystCalendar()
        cal.add_snapshot([_fetch()], [_row()])
        payload = cal.save(p)
        self.assertEqual(payload["trials"], 0)
        self.assertTrue(payload["forward_only"])
        self.assertIn("NO history", payload["history_note"])
        self.assertIn("REFUSES", payload["never_backfilled"])
        self.assertIn("never rounded", payload["precision_rule"])
        with open(p, encoding="utf-8") as fh:
            self.assertIn("sp_index_announcements", json.load(fh)["sources"])

    def test_load_of_a_missing_file_is_empty_not_an_error(self):
        cal = CC.CatalystCalendar.load(os.path.join(tempfile.mkdtemp(), "nope.json"))
        self.assertEqual(cal.snapshots, [])
        self.assertEqual(cal.coverage()["snapshots"], 0)


class TestParser(unittest.TestCase):

    def test_precision_is_carried_not_normalised(self):
        body = json.dumps({"meta": {"as_of": "2026-08-23", "total": 3},
                           "data": [
                               {"id": "a", "ticker": "aaa", "date": "2026-12-01",
                                "date_precision": "day", "type": "PDUFA"},
                               {"id": "b", "ticker": "bbb", "date": "2026-12",
                                "date_precision": "month", "type": "Readout"},
                               {"id": "c", "ticker": "ccc", "date": "2026-Q4",
                                "date_precision": "quarter", "type": "Readout"},
                           ]}).encode()
        rows, meta = CC.parse_pdufa_bio(body)
        self.assertEqual([r["precision"] for r in rows],
                         [CC.DAY, CC.IMPRECISE, CC.IMPRECISE])
        self.assertEqual([r["precision_raw"] for r in rows], ["day", "month", "quarter"])
        self.assertEqual([r["ticker"] for r in rows], ["AAA", "BBB", "CCC"])
        self.assertEqual(meta["as_of"], "2026-08-23")


if __name__ == "__main__":
    unittest.main(verbosity=2)
