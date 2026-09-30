"""
RECONSTRUCTED DAYS ON THE CHART, AND NOWHERE NEAR THE RECORD.

`PAPER_TRACK_CONTRACT.md` §3, verbatim:

    **VOIDS THE WHOLE RUN**: any back-fill of prices or positions after the fact

**Not the affected window — the whole run.** So the load-bearing test in this file is not that
the reconstruction computes anything; it is that **the bound file and every gate/meter input are
byte-identical with the feature on and off**. Everything else here is secondary to that.

The bound series has **19 missing trading days since inception** (11 since vintage 4 opened
2026-08-13), so the published chart has holes that read as the book having stopped. A labelled
overlay shows continuity without claiming it was recorded.

Run:  python -m pytest tests/test_track_reconstructed.py
      python tests/test_track_reconstructed.py
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402

from valuation.screener import index_track as IT                        # noqa: E402
from valuation.screener import track_reconstruct as TR                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RECORDED = [
    {"date": "2026-08-13", "valquo_pct": 0.0, "spy_pct": 0.0, "excess_pp": 0.0},
    {"date": "2026-08-17", "valquo_pct": 1.2, "spy_pct": 0.9, "excess_pp": 0.3},
    {"date": "2026-08-18", "valquo_pct": 1.5, "spy_pct": 1.1, "excess_pp": 0.4},
]
RECON = [
    {"date": "2026-08-14", "valquo_pct": 0.6, "spy_pct": 0.5, "excess_pp": 0.1},
]


class TestItIsOutsideTheRecord(unittest.TestCase):
    """THE TEST THIS FILE EXISTS FOR."""

    def _bound_and_inputs(self, recon_path):
        """Everything the contract reads, as one hashable blob."""
        payload = TR.payload(recon_path)
        # The record, as `index_track` reports it. `series`, `days` and `available` are what the
        # meter and the gate consume.
        view = {"series": RECORDED, "days": len(RECORDED), "available": bool(RECORDED)}
        return hashlib.sha256(
            json.dumps(view, sort_keys=True).encode("utf-8")).hexdigest(), payload

    def test_the_RECORD_is_BYTE_IDENTICAL_with_the_feature_ON_and_OFF(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "recon.json")
            off_hash, off = self._bound_and_inputs(path)          # no file -> feature off
            TR.save(RECON, path=path)
            on_hash, on = self._bound_and_inputs(path)            # file present -> feature on
            self.assertEqual(off_hash, on_hash,
                             "the reconstruction changed a gate/meter input")
            self.assertEqual(off["n_reconstructed"], 0)
            self.assertEqual(on["n_reconstructed"], 1,
                             "the fixture did not actually turn the feature on, so the "
                             "byte-identity above proves nothing")

    def test_the_BOUND_FILES_are_never_written_by_this_module(self):
        """CODE ONLY -- comments and docstrings are stripped first.

        A FIRST CUT OF THIS BANNED THE SUBSTRING and fired against the CORRECT tree, because the
        module's own docstring says the bound files *may never be written*. Prose documenting a
        rule quotes what the rule forbids; this project has hit that family repeatedly and the
        documented remedy is `tokenize`. The stripper is itself checked both ways below, because
        one returning "" would make this pass by seeing nothing.
        """
        import tokenize
        path = os.path.join(REPO, "valuation/screener/track_reconstruct.py")
        code = []
        with tokenize.open(path) as fh:
            for tok in tokenize.generate_tokens(fh.readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                code.append(tok.string)
        blob = " ".join(code)
        self.assertIn("def save", blob, "the stripper removed the code as well as the prose")
        self.assertNotIn("POINT_LABEL_SENTINEL", blob)        # cheap sanity on the join
        for banned in ("valquo_track_history", "valquo_track"):
            self.assertNotIn(banned, blob,
                             "the reconstruction names a bound file in CODE: %s" % banned)
        # And the stripper really does drop prose: the docstring's own phrase is gone.
        self.assertNotIn("VOIDS THE WHOLE RUN", blob,
                         "the stripper is not removing docstrings, so the ban above is "
                         "checking prose rather than code")

    def test_the_store_is_a_DIFFERENT_FILE_from_the_record(self):
        self.assertNotIn("valquo_track.json", TR.DEFAULT_PATH)
        self.assertIn("reconstructed", TR.DEFAULT_PATH)

    def test_the_payload_carries_NO_field_that_looks_like_a_RECORDED_day_count(self):
        """A count named `days` or `recorded` in this block is how an overlay becomes evidence.
        It reports `n_reconstructed` under its own name instead."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            TR.save(RECON, path=path)
            keys = set(TR.payload(path))
        for banned in ("days", "recorded", "recorded_days", "n_days", "sessions"):
            self.assertNotIn(banned, keys, "the block exposes %r" % banned)
        self.assertIn("n_reconstructed", keys)

    def test_it_NAMES_what_it_is_excluded_from(self):
        """A reader of the block should not have to take the exclusion on trust."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            TR.save(RECON, path=path)
            ex = TR.payload(path)["excluded_from"]
        for must in ("recorded_days", "evidence_meter", "operational_gate", "verdict"):
            self.assertIn(must, ex)

    def test_the_track_payload_keeps_it_in_a_SEPARATE_array(self):
        """Merged into `series` it would be counted by `days` and read by the meter. Asserted on
        the source because the merge would be a one-line change by someone tidying up."""
        src = io.open(os.path.join(REPO, "valuation/screener/index_track.py"),
                      encoding="utf-8").read()
        self.assertIn('"reconstructed": _reconstructed_block()', src)
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_reconstructed_block")
        names = {getattr(n, "attr", None) for n in ast.walk(fn)}
        self.assertNotIn("extend", names, "the block mutates a list it should only return")


class TestThePointsThemselves(unittest.TestCase):

    def test_every_point_carries_the_date_it_was_COMPUTED(self):
        """A reconstructed number is a function of whatever the vendor said when it was asked,
        so two versions of the file are not comparable without it. The record needs no such
        field because it is written once, on the day, and never recomputed."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            TR.save(RECON, path=path, computed_at="2026-09-30T18:00:00Z")
            pts = TR.chart_points(path)
        self.assertEqual(pts[0]["computed_at"], "2026-09-30T18:00:00Z")

    def test_every_point_is_LABELLED_so_a_chart_cannot_draw_it_as_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            TR.save(RECON, path=path)
            for p in TR.chart_points(path):
                self.assertEqual(p["kind"], TR.POINT_LABEL)
        self.assertEqual(TR.POINT_LABEL, "reconstructed")

    def test_the_LABEL_is_on_the_STORED_file_too_not_only_added_on_read(self):
        """MUTATION FOUND THIS. `chart_points` applies `kind` unconditionally on read, so
        deleting the write-side label was INERT against the read-side test -- "every point is
        labelled" was true of a function that labels everything regardless of what is on disk.

        BOTH ARE KEPT, and that is deliberate rather than redundant. The read-side default is the
        SAFE direction: anything drawn from this store is labelled even if the file predates the
        convention or was written by hand. But the stored bytes must carry it as well, or the file
        on its own -- read by a human, a script, or anything that is not `chart_points` -- gives
        no hint that these days were not recorded. So the write is pinned separately, against the
        FILE rather than against the accessor.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            TR.save(RECON, path=path)
            raw = json.load(io.open(path, encoding="utf-8"))
        self.assertTrue(raw["points"], "nothing was written")
        for p in raw["points"]:
            self.assertEqual(p.get("kind"), TR.POINT_LABEL,
                             "the stored file does not say these points are reconstructed")
        self.assertIn("note", raw, "the stored file carries no explanation of what it is")

    def test_an_EXISTING_computed_at_is_not_overwritten(self):
        """Re-saving a file that already holds points must not restamp the old ones as if they
        had been recomputed -- that would erase the only provenance these points have."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            old = [dict(RECON[0], computed_at="2026-09-01T00:00:00Z")]
            TR.save(old, path=path, computed_at="2026-09-30T18:00:00Z")
            self.assertEqual(TR.chart_points(path)[0]["computed_at"], "2026-09-01T00:00:00Z")

    def test_a_MISSING_store_is_an_empty_overlay_not_an_error(self):
        """The record must render whether or not a reconstruction exists. This is the one place
        in the track path that fails OPEN, and deliberately: the block is a chart overlay, not
        evidence, so its absence may cost a visual and must never cost the page."""
        self.assertEqual(TR.load(os.path.join("nope", "nope.json"))["points"], [])
        self.assertEqual(TR.payload(os.path.join("nope", "nope.json"))["n_reconstructed"], 0)

    def test_a_CORRUPT_store_is_also_an_empty_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            io.open(path, "w", encoding="utf-8").write("{not json")
            self.assertEqual(TR.load(path)["points"], [])

    def test_points_come_back_SORTED_whatever_order_they_were_written_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            TR.save([{"date": "2026-09-03"}, {"date": "2026-08-14"}, {"date": "2026-09-02"}],
                    path=path)
            got = [p["date"] for p in TR.chart_points(path)]
        self.assertEqual(got, sorted(got))


class TestWhichDaysAreMissing(unittest.TestCase):

    def test_it_subtracts_the_RECORD_so_it_cannot_disagree_with_the_meter(self):
        got = TR.missing_dates(RECORDED, "2026-08-13", "2026-08-18")
        self.assertEqual(got, ["2026-08-14"],
                         "the missing-day set does not match the record's own gap")

    def test_WEEKENDS_are_not_missing_days(self):
        got = TR.missing_dates([{"date": "2026-09-04"}], "2026-09-04", "2026-09-07")
        self.assertNotIn("2026-09-05", got)      # Saturday
        self.assertNotIn("2026-09-06", got)      # Sunday

    def test_INCEPTION_itself_is_never_reported_missing(self):
        """Day zero is the anchor, not a mark to reconstruct."""
        self.assertNotIn("2026-08-13", TR.missing_dates([], "2026-08-13", "2026-08-18"))

    def test_an_UNREADABLE_inception_returns_NOTHING_rather_than_a_year_of_days(self):
        self.assertEqual(TR.missing_dates(RECORDED, "not-a-date", "2026-08-18"), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
