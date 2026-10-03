"""ITEM 27 — THE ADMIN DOORS DRIVEN ON THE **SUCCESS** PATH, WITH A VALID TOKEN.

**THE DEFECT THIS SUITE EXISTS FOR WAS ALREADY WRITTEN DOWN IN THE FILE IT HAPPENED IN.** The
reconstruct door's own comment in `app_saas.py` records this exact bug -- `_store()` is
`web/app.py`'s helper and does not exist in the SaaS module, so the authorised path raises
`NameError` and the handler turns it into a 500 -- and it names the generalisation in as many
words: *"a door that answers 401 and 405 correctly and cannot serve a single caller who gets
past them."*

I then shipped `/admin/score-alerts` calling `_store()`, and wrote `test_admin_record_doors.py`
asserting **401, 405 and 422** -- precisely the three paths that comment says prove nothing.
Every one of those returns BEFORE the body runs, so the suite exercised the guards and never
the door. Don found it by using it: HTTP 500, with his token, on a plain GET preview.

**THE SECOND HALF WAS WORSE, BECAUSE IT MADE THE 500 UNDIAGNOSABLE.** `log_exception` was
CALLED by three handlers in `app_saas.py` and IMPORTED BY NONE, so each raised a second
`NameError` while handling the first and Flask returned a bare HTML 500 -- not even the JSON
body the handler writes. Two of the three only ever looked healthy because their happy path
does not raise. Measured with `pyflakes`: exactly four undefined names in the whole
`valuation/` package, all four in this one file.

WHAT THIS SUITE PINS, and the rule is one line: **every door is driven with a valid token, on
the path that reaches its body.** A refusal test is not a door test.

    python tests/test_admin_door_success.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                    # noqa: E402
from valuation.edge import fleet_history as FH         # noqa: E402
from valuation.edge import options_tracker as OT        # noqa: E402
from valuation.screener.store import Store              # noqa: E402
from valuation.saas.app_saas import create_saas_app     # noqa: E402

TOKEN = "test-token-door-success"

#: The four doors, and the status codes each may legitimately answer WITH a valid token.
#: 500 is in no row, which is the entire point of the file.
DOORS = {
    "/admin/score-alerts": (200,),
    "/admin/index-returns": (200, 422),
    "/admin/invalidate-dip-span?through=2026-10-03": (200, 422),
    "/admin/record-dip-rejects": (200, 422),
}


def _client():
    CONFIG.admin_token = TOKEN
    app = create_saas_app(CONFIG)
    # NOT `TESTING = True`: that makes Flask re-raise, so a handler that explodes surfaces as a
    # test ERROR rather than as the 500 a caller actually receives. The live service runs with
    # these off and that is the behaviour under test.
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    return app.test_client(), {"X-Admin-Token": TOKEN}


def _seed_two_alerts(store):
    """One scoreable alert and one with no contract. Returns (scoreable_id, nocontract_id).

    `is_scoreable` requires BOTH an `occ_symbol` and an `expiry`, and `log_alert` DERIVES the
    occ symbol from ticker+expiry+right+strike -- so the no-contract row is made by withholding
    the strike and expiry, which is how a real one arises: the alert fired and the chain was
    unavailable, so there is a fingerprint and no contract. Faking it by writing a literal empty
    `occ_symbol` would test a row shape the logger cannot produce.
    """
    OT.log_alert(store, {
        "alert_ts": "2026-09-01T20:05:00", "ticker": "AAPL", "opt_right": "call",
        "strike": 250.0, "expiry": "2026-12-18", "entry_premium": 10.0,
        "underlying_price": 240.0, "score": 80.0, "horizon": "swing",
    })
    OT.log_alert(store, {
        "alert_ts": "2026-09-02T20:05:00", "ticker": "MSFT", "opt_right": "call",
        "score": 75.0, "horizon": "swing",
    })
    # READ THE ROWS BACK rather than trusting `log_alert`'s return, AND MY FIRST CUT DID THE
    # OTHER THING AND FAILED FOR IT. `state_isolation` gives one temp store per PROCESS, not
    # per test, so the second `setUp` re-inserts these two rows, `INSERT OR IGNORE` ignores
    # them against the unique index, `rowcount` is 0 and `log_alert` returns `None` -- correct
    # behaviour surfacing as a test failure. Asserting on the insert's RETURN also asked the
    # wrong question: what this suite needs is that the rows are IN THE RECORD, which holds
    # whether this call wrote them or found them already there.
    rows = {r["ticker"]: r for r in OT.open_alerts(store)}
    return rows.get("AAPL"), rows.get("MSFT")


class NoDoorAnswers500WithAValidToken(unittest.TestCase):
    """THE HEADLINE. Four doors, a real token, the body reached on every one."""

    def test_every_door_reaches_its_body(self):
        c, hdr = _client()
        for door, allowed in DOORS.items():
            r = c.get(door, headers=hdr)
            self.assertNotEqual(
                r.status_code, 500,
                "%s returned 500 WITH a valid token. A 401/405/422 test cannot see this, "
                "because all three return before the body runs. Body: %s"
                % (door, (r.get_data(as_text=True) or "")[:300]))
            self.assertIn(r.status_code, allowed, door)

    def test_every_door_answers_json_not_an_html_error_page(self):
        """The bare 500 was HTML, so a caller branching on the JSON body got nothing.

        `log_exception` being undefined meant the handler died BEFORE writing its own
        `{"error": ...}` body, so an unattended caller saw a Flask error page.
        """
        c, hdr = _client()
        for door in DOORS:
            r = c.get(door, headers=hdr)
            self.assertIsNotNone(r.get_json(silent=True),
                                 "%s did not answer JSON: %s"
                                 % (door, (r.get_data(as_text=True) or "")[:200]))


class ScoreAlertsCountsTheNoContractRow(unittest.TestCase):
    """Don's named case: one scoreable alert, one with no contract, quotes stubbed."""

    def setUp(self):
        self.store = Store()
        self.good, self.bare = _seed_two_alerts(self.store)
        from valuation.edge import paper_broker as PB
        self._orig = PB.PaperBroker.quotes
        # A stub rather than the network. It returns a usable two-sided quote for anything
        # asked about, so the scoreable row marks and the no-contract row is never asked.
        PB.PaperBroker.quotes = lambda self, syms: {
            s: {"bid": 9.0, "ask": 9.4} for s in (syms or [])}
        self._PB = PB

    def tearDown(self):
        self._PB.PaperBroker.quotes = self._orig

    def test_both_rows_are_in_the_record(self):
        """Or every assertion below passes against an empty table (`MB21`'s C1)."""
        self.assertIsNotNone(self.good, "no AAPL row in the record")
        self.assertIsNotNone(self.bare, "no MSFT row in the record")
        self.assertEqual(len(OT.open_alerts(self.store)), 2)

    def test_the_two_rows_differ_in_SCOREABILITY_which_is_what_is_under_test(self):
        from valuation.edge.options_selfscore import is_scoreable
        rows = {r["ticker"]: r for r in OT.open_alerts(self.store)}
        self.assertTrue(is_scoreable(rows["AAPL"]))
        self.assertFalse(is_scoreable(rows["MSFT"]))

    def test_a_GET_with_the_token_returns_200_and_counts_one_no_contract(self):
        c, hdr = _client()
        r = c.get("/admin/score-alerts", headers=hdr)
        self.assertEqual(r.status_code, 200,
                         (r.get_data(as_text=True) or "")[:300])
        b = r.get_json()
        self.assertEqual(b["no_contract"], 1)
        self.assertIs(b["applied"], False, "a GET must not apply")

    def test_the_GET_wrote_nothing(self):
        """Asserted against the RECORD: both rows must still be open after a preview."""
        c, hdr = _client()
        c.get("/admin/score-alerts", headers=hdr)
        self.assertEqual(len(OT.open_alerts(self.store)), 2)


class TheOtherThreeDoorsOnTheirSuccessPath(unittest.TestCase):

    def test_invalidate_dip_span_previews_with_the_functions_own_answer(self):
        """ITEM 27(a): the preview used to re-implement the idempotency test.

        It matched any span whose reason merely CONTAINED "dip", while the function skips
        spans whose reason STARTS WITH "ITEM 19" intersected with `UNMEASURED_DIP_SERIES`.
        Two conditions, both wrong, so it reported `dip_rejects` and `iv60_atm` as already
        done when neither was. The route now calls the function with `dry_run=True`.
        """
        c, hdr = _client()
        r = c.get("/admin/invalidate-dip-span?through=2026-10-03", headers=hdr)
        self.assertEqual(r.status_code, 200)
        b = r.get_json()
        # On a clean store NOTHING has been invalidated, so a preview claiming otherwise is
        # the defect. The old code answered from the wrong predicate and could not know this.
        self.assertEqual(b["already_done"], [])
        self.assertIs(b.get("dry_run"), True, "the preview must say it did not write")

    def test_the_preview_and_the_writer_are_ONE_function(self):
        """`B7`: the route may not hold a second definition of `already done`."""
        import ast
        with open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "admin_invalidate_dip_span")
        body = ast.unparse(fn)
        self.assertIn("dry_run", body)
        self.assertNotIn("invalid_spans", body,
                         "the route is reading spans itself again, which is how the "
                         "idempotency test drifted from the function's in the first place")

    def test_record_dip_rejects_never_dates_a_row_from_the_clock(self):
        """The contract, asserted against the store's ACTUAL state rather than an assumed one.

        TWO ORDERING LESSONS IN ONE TEST, both of which failed first. My first cut asserted
        200 and failed against correct code, because an empty store has no `scan_date` and the
        door refuses rather than clock-dating the row. My second asserted 422 and then failed
        once a SIBLING class seeded a snapshot -- `state_isolation` gives one store per
        PROCESS, so a test that assumes an empty store is really asserting test ORDER.

        So it asserts the invariant instead, which holds in both states and cannot pass
        vacuously: **either there is no snapshot and the door refuses naming `scan_date`, or
        there is one and the row is dated by IT.** Never by the clock.
        """
        c, hdr = _client()
        latest = Store().latest_scan_date()
        r = c.get("/admin/record-dip-rejects", headers=hdr)
        b = r.get_json()
        self.assertIs(b.get("wrote"), False)
        if not latest:
            self.assertEqual(r.status_code, 422)
            self.assertIn("scan_date", b["reason"])
            return
        if r.status_code == 422:        # the item-19 guard is allowed to fire first
            self.assertIn("measured", b["reason"])
            return
        self.assertEqual(b["session"], latest,
                         "the row must be dated by the snapshot, not the clock")


class TheDipDoorDatesByTheSnapshot(unittest.TestCase):
    """The 200 path, against a seeded snapshot. Item 20's rule, applied to this recorder."""

    SCAN_DATE = "2026-09-30"

    def setUp(self):
        self.store = Store()
        # A snapshot whose date is deliberately NOT today, so a clock-dated row would be
        # visibly wrong. Two rows, neither of which the dip screen can qualify (no price
        # history in a temp store), which is fine: what is under test is the DATING and the
        # refusal logic, not the screen's own arithmetic -- that has its own 37-test suite.
        self.store.save_snapshot(self.SCAN_DATE, [
            {"ticker": "AAPL", "rank": 1, "score": 80.0},
            {"ticker": "MSFT", "rank": 2, "score": 75.0},
        ])

    def test_the_preview_dates_the_row_by_the_SNAPSHOT_not_the_clock(self):
        c, hdr = _client()
        r = c.get("/admin/record-dip-rejects", headers=hdr)
        self.assertIn(r.status_code, (200, 422),
                      (r.get_data(as_text=True) or "")[:300])
        b = r.get_json()
        if r.status_code == 422:
            # The item-19 guard may legitimately fire on a store with no price history.
            self.assertIn("measured", b["reason"])
            return
        self.assertEqual(b["session"], self.SCAN_DATE)
        self.assertEqual(b["scan_date"], self.SCAN_DATE)
        self.assertIs(b["wrote"], False)

    def test_it_reports_whether_the_snapshot_is_CURRENT_rather_than_assuming_it(self):
        """A dropped scan leaves yesterday's snapshot served, and the response says so."""
        c, hdr = _client()
        b = c.get("/admin/record-dip-rejects", headers=hdr).get_json()
        if "snapshot_is_current" not in b:
            self.skipTest("the item-19 guard fired first on this store")
        self.assertIs(b["snapshot_is_current"], False,
                      "a 2026-09-30 snapshot is not the last closed session today")
        self.assertNotEqual(b["last_closed_session"], self.SCAN_DATE)

    def test_index_returns_reaches_its_body(self):
        """422 here is a REFUSAL FROM THE BODY (no book file in temp state), not a crash.

        The distinction is the whole item: before the fix this door's 422 and the
        score-alerts door's 500 were the same code path, and only one of them had a happy
        path that avoided the undefined name.
        """
        c, hdr = _client()
        r = c.get("/admin/index-returns", headers=hdr)
        self.assertIn(r.status_code, (200, 422))
        self.assertIsNotNone(r.get_json(silent=True))


class TheGuardsMutationProvedUntested(unittest.TestCase):
    """THREE GUARDS THE MUTATION HARNESS CAUGHT ME NOT TESTING, and the third is Don's bug.

    The route-level tests above cannot reach these states: a clean store has no invalidations
    and no snapshot, so the already-done predicate, the item-19 guard and the missing-date
    refusal were all dead to them. Mutation found all three -- 3 missed of 9 -- which is the
    whole argument for running it on a suite I had just written to fix a testing gap.

    Each is driven DIRECTLY: the predicate against a seeded invalidation, the two route guards
    with `screen_snapshot` stubbed, which is the only way to put the screen into a state a
    temp store cannot produce.
    """

    #: `fleet_history` IS A FIFTH `state_isolation` ESCAPE, FOUND BY THIS SUITE WRITING INTO
    #: THE REPOSITORY. `history_dir()` derives its base from the MODULE'S OWN FILE LOCATION --
    #: `dirname(dirname(dirname(__file__)))` -- so it ignores the temp state root entirely and
    #: resolves to `<repo>/data/fleet/history`. Measured: a first run of this class created
    #: `invalidations.csv` AND `dip_rejects.csv` in the worktree's `data/`, the latter holding
    #: `2026-09-29,0,[]`.
    #:
    #: **THAT ROW IS A FALSE "ran and found nothing", WHICH IS EXACTLY THE KIND ITEMS 19 AND 23
    #: EXIST TO INVALIDATE.** It was harmless here only because a worktree's `data/` is
    #: gitignored and disposable, and the primary checkout has no `data/fleet/history` at all.
    #: Run from the primary checkout against a populated record, this suite would have
    #: corrupted the series it was written to protect. So the class points the module at a
    #: temp directory and asserts it landed there, rather than trusting an isolation layer
    #: that does not reach this module.
    TMP = None

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.TMP = tempfile.mkdtemp(prefix="fh-isolated-")
        cls._orig_history_dir = FH.history_dir
        FH.history_dir = staticmethod(
            lambda root=None: os.path.join(cls.TMP, "data", "fleet", "history"))
        os.makedirs(FH.history_dir(), exist_ok=True)
        # Seeded ONCE, in a single `invalidate_many` call, because that function is idempotent
        # per date -- *"IT TAKES A LIST BECAUSE THE UNDERLYING STREAM IS IDEMPOTENT PER DATE"*.
        # Three earlier attempts seeded per test and silently dropped every span after the
        # first, which is `S3-I1`'s defect re-enacted by the test meant to be careful about it.
        FH.invalidate_many([
            # a decoy whose reason MENTIONS dip and is not item 19's
            {"series": "dip_rejects", "from": "2026-07-01", "to": "2026-07-02",
             "reason": "SOME OTHER ITEM: these dip rows are void for an unrelated reason"},
            # an ITEM 19 span on a series NOT in `UNMEASURED_DIP_SERIES`
            {"series": "iv60_atm", "from": "2026-08-06", "to": "2026-08-07",
             "reason": FH.UNMEASURED_DIP_REASON},
        ])

    @classmethod
    def tearDownClass(cls):
        FH.history_dir = cls._orig_history_dir
        import shutil
        shutil.rmtree(cls.TMP, ignore_errors=True)

    def test_the_isolation_actually_took_and_the_repo_is_untouched(self):
        """Or every assertion in this class is about the repository's own record."""
        self.assertIn("fh-isolated-", FH.history_dir())
        self.assertFalse(
            os.path.exists(os.path.join(REPO, "data", "fleet", "history",
                                        "invalidations.csv")),
            "this suite wrote an invalidation into the REPOSITORY's fleet record")

    # --- Don's reported symptom, reproduced ------------------------------------------------
    def test_a_span_whose_reason_merely_mentions_dip_is_NOT_already_done(self):
        """ITEM 27(a) EXACTLY. This is the assertion that would have caught it.

        Don's preview reported `already_done: ["dip_rejects", "iv60_atm"]` and the POST then
        correctly applied `dip_rejects` -- because the route matched any reason CONTAINING
        "dip" while the function requires `startswith("ITEM 19")` intersected with
        `UNMEASURED_DIP_SERIES`. So an unrelated invalidation that happens to mention the word
        made the preview claim the work was done.
        """
        spans = FH.invalid_spans() or []
        self.assertTrue(any("dip" in (sp.get("reason") or "") for sp in spans),
                        "the decoy did not land, so the assertion below is vacuous")
        # STATE-INDEPENDENT, because `state_isolation` shares one store across the process and
        # a sibling test seeds an ITEM 19 span. Asserting `already_done == []` would really be
        # asserting test ORDER -- the trap this file has already recorded twice. The invariant
        # holds in every state: `dip_rejects` is already done IF AND ONLY IF an ITEM 19 span
        # exists for it. A reason that merely mentions "dip" must not move that either way.
        item19 = any((sp.get("reason") or "").startswith("ITEM 19")
                     and sp.get("series") == "dip_rejects" for sp in spans)
        res = FH.invalidate_unmeasured_dip_span(through="2026-10-03", dry_run=True)
        self.assertEqual(
            "dip_rejects" in res["already_done"], item19,
            "a span whose reason merely MENTIONS dip is not item 19's invalidation; "
            "reporting it as already done is what told Don the work was finished")

    def test_no_series_OUTSIDE_the_declared_set_is_ever_already_done(self):
        """THE OTHER HALF OF DON'S SYMPTOM, and the one that identifies the missing clause.

        His preview listed `iv60_atm` -- and `UNMEASURED_DIP_SERIES` is `("dip_rejects",)`, so
        that series is not in scope for this invalidation at all and the function would never
        touch it. The old route matched reasons across EVERY span and never intersected with
        the declared set, so it could report work on a series the writer does not own. Seeded
        with an ITEM 19 span on an out-of-scope series, which is the exact shape that produced
        his output.
        """
        self.assertTrue(any(sp.get("series") == "iv60_atm"
                            for sp in (FH.invalid_spans() or [])),
                        "the fixture did not land")
        res = FH.invalidate_unmeasured_dip_span(through="2026-10-03", dry_run=True)
        self.assertNotIn("iv60_atm", res["already_done"])
        self.assertTrue(set(res["already_done"]) <= set(FH.UNMEASURED_DIP_SERIES))

    def test_the_predicate_is_NOT_vacuous_it_recognises_item_19s_own_wording(self):
        """The positive control, WITHOUT a second write to a date-keyed stream.

        My first cut seeded another span to prove the predicate can say yes, and could not --
        the stream is idempotent per date and forward-only, so the write was dropped. The
        property is testable without writing anything: the predicate is
        `reason.startswith("ITEM 19")` intersected with the declared set, and the class seed
        already contains an ITEM 19 span. So assert it MATCHES that wording on the seeded span
        and would therefore report the series if that series were in scope. This is why the
        `iv60_atm` seed is useful twice: it proves the reason test fires and the intersection
        still excludes it.
        """
        spans = FH.invalid_spans() or []
        item19 = [sp for sp in spans
                  if (sp.get("reason") or "").startswith("ITEM 19")]
        self.assertTrue(item19, "the class seed did not land; everything here is vacuous")
        self.assertEqual([sp["series"] for sp in item19], ["iv60_atm"])
        # The reason test fires on it, and the intersection is what keeps it out.
        res = FH.invalidate_unmeasured_dip_span(through="2026-10-03", dry_run=True)
        self.assertNotIn("iv60_atm", res["already_done"])
        self.assertNotIn("iv60_atm", FH.UNMEASURED_DIP_SERIES)

    # --- the two route guards, with the screen stubbed ------------------------------------
    def _stub_screen(self, payload):
        from valuation.web import dip as _dip
        self._orig_ss = _dip.screen_snapshot
        self._orig_dr = _dip.dip_rejects
        _dip.screen_snapshot = lambda *a, **k: payload
        _dip.dip_rejects = lambda *a, **k: []
        self._dip = _dip
        self.addCleanup(self._restore)

    def _restore(self):
        self._dip.screen_snapshot = self._orig_ss
        self._dip.dip_rejects = self._orig_dr

    def test_a_screen_that_MEASURED_NOTHING_leaves_the_day_a_GAP(self):
        """THE ITEM-19 GUARD, and the reason this door is not a repeat of the bug upstream.

        Item 19's defect was a screen that RAN, reached every eligible name and valued ZERO --
        and the recorder wrote those days down as real observations, which is the span this
        batch just invalidated. Recording `[]` here would assert *ran and found nothing*;
        `record_dip_rejects` reserves `None` for *did not run* (audit #5 `H2`), and this door
        is what decides which.
        """
        self._stub_screen({"scan_date": "2026-09-30", "n_eligible": 242, "n_measured": 0})
        c, hdr = _client()
        r = c.post("/admin/record-dip-rejects?write=1", headers=hdr)
        self.assertEqual(r.status_code, 422)
        b = r.get_json()
        self.assertIs(b["wrote"], False)
        self.assertIn("measured", b["reason"])
        self.assertEqual(b["n_measured"], 0)

    def test_a_screen_with_no_scan_date_is_refused_rather_than_clock_dated(self):
        """Dating from the clock is how yesterday's population lands on today's session."""
        self._stub_screen({"n_eligible": 5, "n_measured": 3})
        c, hdr = _client()
        r = c.post("/admin/record-dip-rejects?write=1", headers=hdr)
        self.assertEqual(r.status_code, 422)
        self.assertIn("scan_date", r.get_json()["reason"])

    def test_a_healthy_screen_DOES_record_under_the_snapshots_date(self):
        """The positive control: the guards above must not refuse everything (`O21-D2` C5).

        Without this the two refusals could be satisfied by a door that never records at all,
        which is the vacuous-guard family in its most convenient form.
        """
        self._stub_screen({"scan_date": "2026-09-29", "n_eligible": 40, "n_measured": 9})
        c, hdr = _client()
        r = c.post("/admin/record-dip-rejects?write=1", headers=hdr)
        self.assertEqual(r.status_code, 200, (r.get_data(as_text=True) or "")[:300])
        b = r.get_json()
        self.assertEqual(b["session"], "2026-09-29")
        self.assertTrue(b["wrote"] or b.get("already_present"),
                        "a healthy screen must reach the record")


class NoUndefinedNamesInTheSaasApp(unittest.TestCase):
    """THE GENERAL FORM, because the next one of these will be a different name.

    A door's body is only reached by callers who get past the guards, so an undefined name in
    it is invisible to every refusal test and to import alone. `pyflakes` sees all of them at
    once, and it found exactly four -- three `log_exception` and one `_store` -- in the whole
    package.
    """

    def test_pyflakes_reports_no_undefined_name_in_the_saas_app(self):
        try:
            import pyflakes  # noqa: F401
        except ImportError:
            self.skipTest("pyflakes not installed — UNDEFINED NAMES ARE UNCHECKED HERE")
        r = subprocess.run([sys.executable, "-m", "pyflakes",
                            os.path.join("valuation", "saas", "app_saas.py")],
                           cwd=REPO, capture_output=True, text=True, errors="replace")
        bad = [ln for ln in (r.stdout or "").splitlines() if "undefined name" in ln]
        self.assertEqual(bad, [], "undefined names in app_saas.py: %s" % bad)

    def test_the_saas_app_does_not_call_web_apps_private_store_helper(self):
        """`_store` is `web/app.py`'s. Twice now, so it is asserted rather than remembered."""
        import ast
        with open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                  encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "_store"]
        self.assertEqual(calls, [], "app_saas.py calls `_store()`, which does not exist here; "
                                    "every door in this module imports `Store` and calls it")


if __name__ == "__main__":
    unittest.main(verbosity=2)
