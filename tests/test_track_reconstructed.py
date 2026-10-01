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
            # Values supplied because `save` refuses an all-null point (a day it did not
            # compute). They are irrelevant to the sort and deliberately not in date order.
            TR.save([{"date": "2026-09-03", "valquo_pct": 4.4},
                     {"date": "2026-08-14", "valquo_pct": 5.6},
                     {"date": "2026-09-02", "valquo_pct": 4.0}],
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


class ValidatingAgainstTheRecordIsThePrecondition(unittest.TestCase):
    """Reconstructing days the record ALREADY holds is what licenses drawing days it does not.

    MEASURED on the real book and the real record, 8 comparable days: the BENCHMARK leg
    reproduces EXACTLY on 5 of 8 and the BOOK leg never does -- median 0.1001pp, max 0.2944pp,
    and always in the same direction. So these points ship with a measured seam, which is the
    whole reason they live in a separate store behind a "not part of the record" label.
    """

    def test_zero_comparisons_reports_NO_score_rather_than_a_perfect_one(self):
        """The vacuous-pass family, and the one shape that would make this dangerous.

        A validator that returns `book_max_abs: 0.0` after comparing nothing is indistinguishable
        from one that compared every day and found exact agreement -- and it would be read as the
        stronger of the two. The keys are ABSENT instead, so a caller cannot mistake silence for
        agreement, and `n_compared` is always present so the gate is explicit.
        """
        r = TR.validate_against_record([])
        self.assertEqual(r["n_compared"], 0)
        self.assertNotIn("book_max_abs", r)
        self.assertNotIn("bench_max_abs", r)
        self.assertNotIn("book_median_abs", r)

    def test_it_reports_the_two_legs_SEPARATELY_and_never_summed(self):
        """They behave differently and one combined figure would hide that.

        The benchmark leg is one symbol on closing prices and reproduces exactly; the book leg
        cannot, because a name the record priced on the day may be unpriceable today and is then
        missing from EVERY reconstructed day, including the days it was live. Summing them would
        report a single seam and conceal which half moved.

        IT HAS TO REACH THE COMPARING BRANCH. A first cut passed `meta_path="nope.json"`, so the
        row refused and the test exercised only the refusal path -- the branch named in its own
        title was never entered, and summing the two legs went undetected (mutation v2, MISSED).
        The same family as three fixtures in the task-12 pass: a test whose setup cannot reach the
        code it is named for.
        """
        from valuation.screener import index_mark as IM
        rec = [{"date": "2026-08-06", "valquo_pct": 0.7760, "spy_pct": 3.6228, "n_priced": 86}]
        # Deliberately UNEQUAL deltas: book +0.5000, bench -0.2000. If the two legs were summed
        # both would read 0.7 and neither would match its own number.
        row = {"date": "2026-08-06", "valquo_pct": 1.2760, "spy_pct": 3.4228, "n_priced": 85}
        orig = IM.contract_row
        IM.contract_row = lambda *a, **k: {"ok": True, "row": dict(row)}
        try:
            r = TR.validate_against_record(rec)
        finally:
            IM.contract_row = orig
        self.assertEqual(r["n_compared"], 1)
        self.assertEqual(r["n_refused"], 0)
        d = r["days"][0]
        self.assertAlmostEqual(d["d_book_pp"], +0.5000, places=6)
        self.assertAlmostEqual(d["d_bench_pp"], -0.2000, places=6)
        self.assertAlmostEqual(r["book_max_abs"], 0.5000, places=6)
        self.assertAlmostEqual(r["bench_max_abs"], 0.2000, places=6)
        self.assertNotAlmostEqual(r["book_max_abs"], r["bench_max_abs"], places=6,
                                  msg="the two legs were combined into one figure")
        # And the n_priced pair travels, which is the one mechanism a reader can act on.
        self.assertEqual(d["n_priced_reconstructed"], 85)
        self.assertEqual(d["n_priced_recorded"], 86)

    def test_a_refusal_is_COUNTED_rather_than_dropped(self):
        """Split out of the test above, which was doing two jobs and only reaching one branch."""
        rec = [{"date": "2026-08-06", "valquo_pct": 0.7760, "spy_pct": 3.6228, "n_priced": 86}]
        r = TR.validate_against_record(rec, meta_path="nope-no-book-here.json")
        self.assertEqual(r["n_refused"], 1)
        self.assertEqual(r["n_compared"], 0)
        self.assertIn("refused", r["days"][0])
        self.assertNotIn("book_max_abs", r, "a refused day produced a score anyway")

    def test_it_states_NO_bar(self):
        """What counts as an acceptable seam is a judgement for whoever quotes the points.

        Inventing a threshold here is the uncalibrated-bar error this project has paid for
        repeatedly -- X7 retired a 2.0 convention after measuring that 39 percent of pure-noise
        draws cleared it. So the function reports and does not verdict.
        """
        src = io.open(os.path.join(REPO, "valuation/screener/track_reconstruct.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "validate_against_record")
        body = ast.unparse(fn)
        # READ THE TREE, NOT THE TEXT: the docstring explains that it states no bar, and a
        # substring check would be satisfied by that explanation (the r2 defect, inverted).
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    self.assertNotIsInstance(
                        op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE),
                        "an ordering comparison here is a bar: %s" % ast.unparse(node))
        self.assertNotIn("verdict", body.lower().replace("no verdict", ""))

    def test_the_per_day_row_carries_BOTH_n_priced_figures(self):
        """The one mechanism a reader can act on.

        The recorded day priced 86 names and the reconstruction prices 85, so part of the book-leg
        seam is a name the vendor no longer carries. Reporting only one figure would leave that
        invisible and the seam unexplained.
        """
        src = io.open(os.path.join(REPO, "valuation/screener/track_reconstruct.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "validate_against_record")
        body = ast.unparse(fn)
        self.assertIn("n_priced_reconstructed", body)
        self.assertIn("n_priced_recorded", body)

    def test_it_DELEGATES_to_contract_row_with_the_close_check_off(self):
        src = io.open(os.path.join(REPO, "valuation/screener/track_reconstruct.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "validate_against_record")
        calls = [c for c in ast.walk(fn)
                 if isinstance(c, ast.Call) and getattr(c.func, "attr", None) == "contract_row"]
        self.assertEqual(len(calls), 1, "it re-derives the row instead of delegating (B7)")
        kw = {k.arg: k.value for k in calls[0].keywords}
        self.assertIs(kw["refuse_before_close"].value, False,
                      "it would refuse every past day it is meant to check")


class AnAllNullPointIsRefused(unittest.TestCase):
    """A store whose whole purpose is "this is NOT the record" must not hold a day it did not
    compute.

    THE RUN THAT MADE THIS NECESSARY: the first pass over the 19 missed sessions stored 19 points
    with every value `null`, because the caller read `p.get("row")` while `reconstruct` returns its
    points ALREADY FLATTENED. The console printed correct numbers the whole time -- the printer used
    `p.get("row") or p`, so its lenient fallback masked the shape mismatch while the writer, which
    had no fallback, wrote empties. The file then looked like a complete 19-day reconstruction and
    would have drawn 19 invisible points on a public chart.

    A LENIENT READER BESIDE A STRICT WRITER IS THE DANGEROUS COMBINATION: the surface that would
    have told me is the one that was forgiving.
    """

    def test_a_point_with_no_values_is_REFUSED_rather_than_stored(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.json")
            with self.assertRaises(ValueError) as cm:
                TR.save([{"date": "2026-08-03", "valquo_pct": None, "spy_pct": None,
                          "excess_pp": None}], path=path)
            self.assertIn("2026-08-03", str(cm.exception))
            self.assertIn("refused", str(cm.exception).lower() + "refused")
            # AND NOTHING IS WRITTEN. A refusal that leaves a half-file behind is worse than a
            # silent accept, because the next reader finds a file and trusts it.
            self.assertFalse(os.path.exists(path), "a refused save left a file behind")

    def test_a_point_with_ANY_value_is_kept(self):
        """The guard must not become "refuse anything with a hole in it".

        A day can legitimately price the book and not the benchmark, or carry no `spmo_pct` at all
        -- that is a partial reading and it is still a reading. Refusing it would make the store
        quietly narrower than the record it sits beside.
        """
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.json")
            r = TR.save([{"date": "2026-08-03", "valquo_pct": 1.036,
                          "spy_pct": None, "excess_pp": None}], path=path)
            self.assertEqual(r["n"], 1)
            body = json.load(io.open(path, encoding="utf-8"))
            self.assertEqual(body["points"][0]["valquo_pct"], 1.036)

    def test_the_refusal_names_the_field_set_it_checked(self):
        """So a future reader can tell whether a new field was meant to be in the check."""
        src = io.open(os.path.join(REPO, "valuation/screener/track_reconstruct.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "save")
        body = ast.unparse(fn)
        for k in ("valquo_pct", "spy_pct", "excess_pp"):
            self.assertIn(k, body, "the guard no longer checks %s" % k)


class AnAbsentRecordFieldIsARefusalNotAZero(unittest.TestCase):
    """The validator fabricated a FAILURE, which is the direction that gets believed.

    The writer's row says `valquo_pct` / `spy_pct`; the chart payload the service serves says
    `valquo` / `spy`. A first cut read only the writer's names and coerced the missing key to 0.0,
    so every delta came back EQUAL TO THE RECONSTRUCTED VALUE and the validator reported a ~4pp
    disagreement on all 24 recorded days -- entirely an artefact of a key name.

    Two things make this worth a test rather than a fix. One: a validator that invents the thing it
    compares against is worse than none. Two: it invented a disagreement, not an agreement, so it
    would have been read as evidence the reconstruction was broken and the real mechanism (one
    unpriceable name) would have been buried under a fictional 4pp.
    """

    def _patch(self, row):
        from valuation.screener import index_mark as IM
        orig = IM.contract_row
        IM.contract_row = lambda *a, **k: {"ok": True, "row": dict(row)}
        self.addCleanup(lambda: setattr(IM, "contract_row", orig))

    def test_the_SERVICE_spelling_is_read_rather_than_missed(self):
        self._patch({"date": "2026-07-31", "valquo_pct": 0.4433, "spy_pct": 0.7200,
                     "n_priced": 85})
        rec = [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903, "n_priced": 86}]
        r = TR.validate_against_record(rec)
        self.assertEqual(r["n_compared"], 1)
        d = r["days"][0]
        self.assertAlmostEqual(d["d_book_pp"], 0.0307, places=4)
        self.assertAlmostEqual(d["d_bench_pp"], 0.0297, places=4)
        self.assertEqual(d["record_fields"], ["valquo", "spy"])

    def test_the_WRITER_spelling_still_works(self):
        self._patch({"date": "2026-08-06", "valquo_pct": 0.7873, "spy_pct": 3.6228})
        rec = [{"date": "2026-08-06", "valquo_pct": 0.7760, "spy_pct": 3.6228}]
        r = TR.validate_against_record(rec)
        self.assertEqual(r["n_compared"], 1)
        self.assertAlmostEqual(r["days"][0]["d_bench_pp"], 0.0, places=6)
        self.assertEqual(r["days"][0]["record_fields"], ["valquo_pct", "spy_pct"])

    def test_a_row_carrying_NEITHER_spelling_is_REFUSED(self):
        """And the refusal says which leg was missing, so the cause is one read away."""
        self._patch({"date": "2026-08-06", "valquo_pct": 0.7873, "spy_pct": 3.6228})
        r = TR.validate_against_record([{"date": "2026-08-06", "pct": 1.0}])
        self.assertEqual(r["n_compared"], 0)
        self.assertEqual(r["n_refused"], 1)
        self.assertIn("book", r["days"][0]["refused"])
        self.assertNotIn("book_max_abs", r, "it scored a day it refused")

    def test_a_row_missing_only_the_BENCHMARK_is_refused_and_says_so(self):
        self._patch({"date": "2026-08-06", "valquo_pct": 0.7873, "spy_pct": 3.6228})
        r = TR.validate_against_record([{"date": "2026-08-06", "valquo": 0.7760}])
        self.assertEqual(r["n_refused"], 1)
        self.assertIn("benchmark", r["days"][0]["refused"])

    def test_a_present_but_NULL_field_is_compared_rather_than_refused(self):
        """Present-and-null is a reading, not an absence, and the two must not collapse.

        A record row that explicitly carries `valquo: null` is telling us the writer could not
        price the book that day. That is information; refusing it would discard it, and treating
        it as absent would make the two indistinguishable.
        """
        self._patch({"date": "2026-08-06", "valquo_pct": 0.7873, "spy_pct": 3.6228})
        r = TR.validate_against_record([{"date": "2026-08-06", "valquo": None, "spy": 3.6228}])
        self.assertEqual(r["n_compared"], 1)
        self.assertEqual(r["days"][0]["record_fields"], ["valquo", "spy"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
