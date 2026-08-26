"""AUDIT #5 remediation — H1, H2 and the correctness items.

WHAT THESE PIN, and why each earns its place.

**H2 IS THE ONE THAT WAS CONTAMINATING A RECORD EVERY WEEKDAY.** `record_all`'s production
caller passed no sources, so two of the three (D) recorders asserted "nothing appeared today"
from screens that never ran. The rule now enforced is that `None` means NOT CONSULTED and
REFUSES, while an empty collection means *ran and found nothing* and records — the same
distinction `record_iv60` already drew one level down, where a name with no solvable IV is
OMITTED rather than written as zero.

**AND THE ALARM'S REAL BLIND SPOT IS PINNED SEPARATELY.** `failed_to_start` re-reads the series
and asks whether it has any rows, so a series with months of history passes forever — a source
that silently stopped being consulted could never reach it. The test that matters writes a day
of history FIRST and then drops the source.

**H1 IS PINNED IN AN IMAGE-SHAPED ROOT WITH A POSITIVE CONTROL.** A local pass is not evidence
for a deploy-only defect — this is the fourth of that family — so the test builds a root with no
`DECL_*.md` and no `.git`, asserts the OLD route still raises there, and asserts the new one
resolves. Without the control the test would pass on a tree where the defect was never real.

**M1** the day-1 certificate counted NOT-RUN checks as passes and said the opposite in `skip`'s
own docstring; **M2** `read_meter` returned a verdict, a first-read flag and a trial-charge
instruction with no dated record of the read; **M3** the third harness state was structurally
unreachable for both implemented order-placing rules; **M4** the fingerprint covered two of the
eight modules its certificate attests to, including the one that prices every fill; **M5** the
shipped manifest is the whole evidence base in production and nothing kept it fresh.
"""
import ast
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet as F              # noqa: E402
from valuation.edge import fleet_history as H      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKIPS = []


class _Store:
    def __init__(self, rows=None):
        self._rows = rows if rows is not None else [{"ticker": "AAPL", "detail": {}}]

    def load_intraday(self):
        return self._rows


# ===========================================================================================
# H2 — the fabricated zero
# ===========================================================================================
class TestH2NotConsultedRefuses(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_the_production_call_shape_no_longer_writes_a_fabricated_zero(self):
        out = H.record_all(date="2026-08-26", store=_Store(), root=self.root)
        self.assertEqual(sorted(out["not_consulted"]), ["dip_rejects", "iv60_atm"])
        self.assertFalse(out["ok"])
        self.assertTrue(out["loud"])
        # and NOTHING was written for either
        for name in ("dip_rejects", "iv60_atm"):
            self.assertTrue(H.read(name, self.root).get("absent"), name)

    def test_alert_count_still_records_because_it_has_a_real_source(self):
        H.record_all(date="2026-08-26", store=_Store(), root=self.root)
        self.assertEqual(H.read("alert_count", self.root)["n"], 1)

    def test_an_empty_collection_IS_an_observation_and_records(self):
        """RAN-AND-FOUND-NOTHING must stay recordable, or the fix breaks the series."""
        out = H.record_all(date="2026-08-26", store=_Store(), rejects=[], quotes={},
                           root=self.root)
        self.assertEqual(out["not_consulted"], [])
        self.assertTrue(out["ok"])
        self.assertEqual(H.read("dip_rejects", self.root)["n"], 1)
        self.assertEqual(H.read("iv60_atm", self.root)["n"], 1)

    def test_THE_BLIND_SPOT_a_series_with_history_still_goes_loud(self):
        """The defect the alarm could never have caught: `failed_to_start` asks whether the
        SERIES has rows, and a series with history passes that forever."""
        H.record_all(date="2026-08-20", store=_Store(), rejects=["AAPL"], quotes={"AAPL": 0.3},
                     root=self.root)
        out = H.record_all(date="2026-08-21", store=_Store(), root=self.root)
        self.assertEqual(out["failed_to_start"], [], "history masks it, as it always did")
        self.assertEqual(sorted(out["not_consulted"]), ["dip_rejects", "iv60_atm"])
        self.assertFalse(out["ok"], "the old alarm read ok=True in exactly this state")

    def test_the_recorders_themselves_refuse_and_say_why(self):
        for fn in (H.record_dip_rejects, H.record_iv60):
            r = fn(date="2026-08-26", root=self.root)
            self.assertFalse(r["ok"])
            self.assertFalse(r["wrote"])
            self.assertTrue(r["not_consulted"])
            self.assertIn("NOT CONSULTED", r["reason"])


class TestH2Iv60HasARealSource(unittest.TestCase):
    def test_it_reads_the_scan_the_cycle_already_paid_for(self):
        s = _Store([{"ticker": "AAPL", "detail": {"atm_iv_60d": 0.31}},
                    {"ticker": "MSFT", "detail": {"atm_iv_60d": None}},
                    {"ticker": "NVDA", "detail": {}}])
        self.assertEqual(H.iv60_from_store(s), {"AAPL": 0.31})

    def test_an_unavailable_scan_returns_None_so_the_recorder_REFUSES(self):
        class Dead:
            def load_intraday(self):
                raise RuntimeError("store down")
        self.assertIsNone(H.iv60_from_store(Dead()))

    def test_a_scan_that_solved_nothing_returns_an_empty_dict_and_RECORDS(self):
        self.assertEqual(H.iv60_from_store(_Store([])), {})

    def test_a_zero_or_negative_iv_is_omitted_never_recorded(self):
        s = _Store([{"ticker": "A", "detail": {"atm_iv_60d": 0.0}},
                    {"ticker": "B", "detail": {"atm_iv_60d": -1.0}}])
        self.assertEqual(H.iv60_from_store(s), {})


class TestH2Invalidation(unittest.TestCase):
    """The rows already written. Append-only is NOT weakened; a forward record marks them."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for d in ("2026-08-17", "2026-08-18", "2026-08-19"):
            H.record("dip_rejects", d, [], count=0, root=self.root)
            H.record("iv60_atm", d, {}, count=0, root=self.root)

    def test_a_backward_write_is_still_refused(self):
        """The rule that makes these series evidence stays exactly as it was."""
        r = H.record("dip_rejects", "2026-08-01", ["X"], count=1, root=self.root)
        self.assertFalse(r.get("wrote"))

    def test_the_span_is_marked_and_every_consumer_honours_it(self):
        H.invalidate_fabricated_span(self.root, date="2026-08-26")
        for name in ("dip_rejects", "iv60_atm"):
            c = H.coverage(self.root)[name]
            self.assertEqual(c["n_days"], 3, "the rows are KEPT, not erased")
            self.assertEqual(c["n_days_valid"], 0)
            self.assertEqual(c["n_days_invalid"], 3)
            self.assertFalse(c["usable"])
            self.assertTrue(all(r["invalid"] for r in H.read(name, self.root)["rows"]))

    def test_history_for_skips_invalid_days(self):
        H.record("dip_rejects", "2026-08-20", ["AAPL"], count=1, root=self.root)
        H.invalidate_fabricated_span(self.root, date="2026-08-26")
        # AAPL's only appearance is inside the invalid span -> not an observation
        self.assertEqual(H.history_for("dip_rejects", "AAPL", self.root), [])

    def test_it_runs_ONCE_and_does_not_swallow_later_real_rows(self):
        """The span is frozen at first application. Recomputing it daily from 'everything on
        disk' would eat the good days as soon as the caller started supplying a source."""
        H.invalidate_fabricated_span(self.root, date="2026-08-26")
        H.record("iv60_atm", "2026-08-27", {"AAPL": 0.4}, count=1, root=self.root)
        again = H.invalidate_fabricated_span(self.root, date="2026-08-27")
        self.assertEqual(again["applied"], [])
        self.assertEqual(H.history_for("iv60_atm", "AAPL", self.root), [("2026-08-27", 0.4)])

    def test_two_spans_on_ONE_date_both_land(self):
        """`record` is idempotent per DATE, so a second same-day write is a no-op that returns
        the row already on disk. Writing the two spans separately dropped the second SILENTLY,
        in the direction that reads as success -- `S3-I1`'s defect, hit again here."""
        spans = [s["series"] for s in H.invalid_spans(self.root)]
        self.assertEqual(spans, [])
        H.invalidate_fabricated_span(self.root, date="2026-08-26")
        self.assertEqual(sorted(s["series"] for s in H.invalid_spans(self.root)),
                         ["dip_rejects", "iv60_atm"])

    def test_a_same_date_collision_is_REPORTED_not_silently_dropped(self):
        H.invalidate("dip_rejects", "2026-08-17", "2026-08-19", "first", date="2026-08-26",
                     root=self.root)
        r = H.invalidate("iv60_atm", "2026-08-17", "2026-08-19", "second", date="2026-08-26",
                         root=self.root)
        self.assertFalse(r["ok"])
        self.assertIn("idempotent per date", r["reason"])

    def test_invalidations_is_not_counted_as_a_recorder_that_failed_to_start(self):
        """It is metadata about the other series, not a daily observation. Counting it would
        make the alarm cry wolf on every cycle -- `MA21`'s rule."""
        out = H.record_all(date="2026-08-26", store=_Store(), rejects=[], quotes={},
                           root=self.root)
        self.assertNotIn("invalidations", out["failed_to_start"])
        self.assertTrue(out["ok"])


# ===========================================================================================
# H1 — the fleet cannot fill in the image
# ===========================================================================================
def _image_root():
    """A root shaped like the deployed image: data_export present, NO `*.md`, NO `.git`."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "data_export"), exist_ok=True)
    for f in glob.glob(os.path.join(REPO, "data_export", "*")):
        if os.path.isfile(f):
            shutil.copy2(f, os.path.join(root, "data_export", os.path.basename(f)))
    return root


class TestH1DeclSha(unittest.TestCase):
    BOOKS = ("f3_bear_puts", "f8_csp_entry_financing")

    @classmethod
    def setUpClass(cls):
        cls.root = _image_root()
        if not os.path.exists(os.path.join(cls.root, "data_export",
                                           "fleet_declarations.json")):
            _SKIPS.append("data_export/fleet_declarations.json absent - cannot build an "
                          "image-shaped root")
            raise unittest.SkipTest("no shipped manifest")

    def test_the_root_really_is_image_shaped(self):
        self.assertEqual(glob.glob(os.path.join(self.root, "DECL_*.md")), [])
        self.assertFalse(os.path.exists(os.path.join(self.root, ".git")))

    def test_POSITIVE_CONTROL_the_old_route_still_raises_there(self):
        """Without this the test proves nothing: it would pass on a tree where reading the
        markdown had always worked."""
        from valuation.edge import fleet_books as B
        for book in self.BOOKS:
            with self.assertRaises(OSError, msg=book):
                F.declaration_sha(B._read(F.declaration_path(book, self.root)))

    def test_the_shared_resolver_resolves_both_books_in_the_image(self):
        for book in self.BOOKS:
            self.assertTrue(F.decl_sha_for(book, self.root), book)

    def test_neither_rule_reads_the_markdown_directly_any_more(self):
        """Read from the SYNTAX TREE. A grep would fire on the repair comment, which names the
        very call it forbids -- `MA49`'s defect, hit four times in this record."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet_books.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        bad = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "declaration_sha":
                # declaration_sha(...) is only legitimate on text the caller already holds;
                # the defect is declaration_sha(_read(declaration_path(...))).
                for a in node.args:
                    if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) \
                            and a.func.id == "_read":
                        bad.append(ast.dump(node)[:60])
        self.assertEqual(bad, [], "route it through F.decl_sha_for")


# ===========================================================================================
# M1 / M2 / M3 / M4 / M5
# ===========================================================================================
class TestM1SkipsAreNotPasses(unittest.TestCase):
    def test_skip_records_pass_false(self):
        from scripts import fleet_selfcheck as SC
        checks = []

        def skip(name, why):
            checks.append({"check": name, "pass": False, "skipped": True, "detail": why})
        skip("x", "y")
        self.assertFalse(checks[0]["pass"])
        # and the shipped one agrees
        src = io.open(os.path.join(REPO, "scripts", "fleet_selfcheck.py"),
                      encoding="utf-8").read()
        self.assertIn('checks.append({"check": name, "pass": False, "skipped": True', src)
        self.assertTrue(hasattr(SC, "run"))

    def test_ok_is_decided_on_what_RAN_and_the_floor_counts_executed_checks(self):
        src = io.open(os.path.join(REPO, "scripts", "fleet_selfcheck.py"),
                      encoding="utf-8").read()
        self.assertIn('"ok": n_pass == n_run and n_run >= 15', src)

    def test_run_day1_forwards_the_skips(self):
        src = io.open(os.path.join(REPO, "scripts", "fleet_selfcheck.py"),
                      encoding="utf-8").read()
        self.assertIn('"skipped": syn.get("skipped")', src)


class TestM2AnUnrecordedReadWithholdsTheVerdict(unittest.TestCase):
    def test_the_source_withholds_rather_than_returning_ok_true(self):
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        self.assertIn("THE READ WAS NOT RECORDED, so the verdict is WITHHELD", src)

    def test_an_already_present_record_still_counts_as_landed(self):
        """The read IS on the stream, which is what the rule requires. Refusing here would
        make a legitimate second read look like a failure."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        self.assertIn('landed = bool(w.get("wrote")) or bool(w.get("already_present"))', src)


class TestM3TheThirdStateIsReachable(unittest.TestCase):
    def test_a_rule_that_writes_no_rows_still_accrues_observations(self):
        root = tempfile.mkdtemp()
        book = "f3_bear_puts"
        self.assertEqual(F.never_fires(book, root)["observations"], 0)
        for _ in range(F.NEVER_FIRES_AFTER + 1):
            F.note_cycle_ran(book, root)
        nf = F.never_fires(book, root)
        self.assertEqual(nf["rows_observed"], 0, "the rule wrote nothing, as it does")
        self.assertGreaterEqual(nf["cycles_ran"], F.NEVER_FIRES_AFTER)
        self.assertEqual(nf["state"], "RULE_ARMED_NEVER_FIRES")

    def test_it_stays_OK_below_the_bar(self):
        root = tempfile.mkdtemp()
        F.note_cycle_ran("f3_bear_puts", root)
        self.assertEqual(F.never_fires("f3_bear_puts", root)["state"], "OK")

    def test_the_counter_is_monotonic(self):
        root = tempfile.mkdtemp()
        self.assertEqual(F.note_cycle_ran("b", root), 1)
        self.assertEqual(F.note_cycle_ran("b", root), 2)
        self.assertEqual(F.cycles_ran("b", root), 2)


class TestM4FingerprintCoversWhatItCertifies(unittest.TestCase):
    def test_it_covers_all_eight_modules(self):
        self.assertEqual(len(F.FINGERPRINTED_MODULES), 8)
        here = os.path.dirname(os.path.abspath(F.__file__))
        for m in F.FINGERPRINTED_MODULES:
            self.assertTrue(os.path.exists(os.path.join(here, m)), m)

    def test_paper_broker_is_covered_because_it_prices_every_fill(self):
        self.assertIn("paper_broker.py", F.FINGERPRINTED_MODULES)

    def test_it_actually_moves_when_a_covered_module_moves(self):
        """Proved by perturbing, not asserted. Source restored byte-for-byte."""
        p = os.path.join(os.path.dirname(os.path.abspath(F.__file__)), "paper_broker.py")
        orig = io.open(p, encoding="utf-8", newline="").read()
        before = F.harness_fingerprint()
        try:
            io.open(p, "w", encoding="utf-8", newline="").write(orig + "\n# mutation\n")
            self.assertNotEqual(before, F.harness_fingerprint())
        finally:
            io.open(p, "w", encoding="utf-8", newline="").write(orig)
        self.assertEqual(before, F.harness_fingerprint())

    def test_L4_it_is_line_ending_independent(self):
        """CRLF on Windows, LF in the image, same commit -- it must be the same fingerprint."""
        p = os.path.join(os.path.dirname(os.path.abspath(F.__file__)), "append_only.py")
        orig = io.open(p, encoding="utf-8", newline="").read()
        before = F.harness_fingerprint()
        try:
            flipped = orig.replace("\r\n", "\n") if "\r\n" in orig else orig.replace(
                "\n", "\r\n")
            io.open(p, "w", encoding="utf-8", newline="").write(flipped)
            self.assertEqual(before, F.harness_fingerprint(),
                             "line endings must not change the harness identity")
        finally:
            io.open(p, "w", encoding="utf-8", newline="").write(orig)


class TestM5TheShippedManifestIsFresh(unittest.TestCase):
    """The manifest is the ENTIRE evidence base for the gate in production. Nothing kept it
    fresh, and for a book with no records yet drift is SILENT — the chain only anchors once a
    first row exists, and all eighteen books have none."""

    def test_the_committed_manifest_equals_a_fresh_build(self):
        path = os.path.join(REPO, "data_export", "fleet_declarations.json")
        if not os.path.exists(path):
            _SKIPS.append("data_export/fleet_declarations.json absent")
            self.skipTest("no shipped manifest")
        try:
            from scripts import fleet_export_declarations as EX
        except ImportError:
            _SKIPS.append("exporter not importable")
            self.skipTest("no exporter")
        fresh = EX.build(REPO)
        with io.open(path, encoding="utf-8") as fh:
            shipped = json.load(fh)
        fresh_books = (fresh.get("books") or {})
        ship_books = (shipped.get("books") or {})
        self.assertEqual(sorted(fresh_books), sorted(ship_books),
                         "a declaration landed without re-exporting the manifest")
        drift = [b for b in sorted(fresh_books)
                 if (fresh_books[b] or {}).get("decl_sha")
                 != (ship_books.get(b) or {}).get("decl_sha")]
        self.assertEqual(drift, [], "decl_sha drift between the tree and the shipped manifest")


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
