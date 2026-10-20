"""ITEM 51 — THE FLEET RE-CERTIFIES ITSELF, AND A FAILING SELF-CHECK IS NEVER RETRIED.

Don's ruling, 2026-10-13: *"The daily fleet cycle runs the self-check automatically when the
certificate is stale because the harness code changed (SELFCHECK_STALE / SELFCHECK_ABSENT). If
the self-check FAILS, the books stay shut and Don is alerted — a failing check is never re-run
into a pass. Paper only."*

**THE RULE THAT NEEDS ENFORCING RATHER THAN NOTING, AND IT IS MEASURED IN `run_day1` ITSELF.**
When the SYNTHETIC leg fails, `run_day1` returns **before writing any row** — so every book
stays `SELFCHECK_STALE`, which is the exact state that triggers an automatic attempt. Left
unguarded the cron would attempt it again every evening, indefinitely: the retry loop the
ruling forbids, arrived at by doing nothing wrong. `prior_automatic_failure` is that guard, and
it is keyed on the FINGERPRINT so that fixing the harness re-opens the door by itself.

The same measurement is why the alert is explicit. A failing synthetic leg changes no refusal
CODE, and `fleet_notify` announces a refusal only when the code changes — correctly, and
silently. Relying on it would have met the letter of "Don is alerted" and sent nothing.

    python tests/test_item51_auto_recertify.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                               # noqa: E402
from valuation.edge import fleet_notify as FN                       # noqa: E402
from test_fleet_harness import _repo, BOOK, _sha                    # noqa: E402


def _seed_selfcheck(root, book=BOOK, fate="pass", detail=None):
    """Local, because the sibling helper takes neither `fate` nor `detail`.

    Both are needed here and neither belongs in a shared helper for this suite's sake:
    STALE is a row whose `detail` is an OLD fingerprint and FAILING is one whose `fate` is
    not `pass`, and those two states are the whole subject.
    """
    F.record(book, "selfcheck",
             {"fate": fate,
              "detail": F.harness_fingerprint() if detail is None else detail},
             decl_sha=_sha(root, book), root=root)


def _event(**kw):
    ev = {"trigger": "automatic", "ok": False,
          "fingerprint_after": F.harness_fingerprint(),
          "fingerprint_before": "older-fingerprint",
          "books": [BOOK], "n_books": 1, "reason": "the LIVE leg failed"}
    ev.update(kw)
    return ev


class TheTriggerIsTheRulingsTwoStatesAndNoOthers(unittest.TestCase):

    def setUp(self):
        self.root = _repo(book=BOOK)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_an_ABSENT_certificate_is_OWED_and_attemptable(self):
        a = F.recertify_attempt(self.root)
        self.assertTrue(a["attempt"])
        self.assertEqual(a["state"], "OWED")
        self.assertEqual(a["codes"], ["SELFCHECK_ABSENT"])
        # No certificate at all is NOT "pinned to something older", and it is recorded as the
        # different fact it is rather than as an empty string.
        self.assertIsNone(a["fingerprint_before"])

    def test_a_STALE_certificate_is_OWED_and_carries_the_fingerprint_it_had(self):
        _seed_selfcheck(self.root, BOOK, detail="a-previous-harness")
        st = F.selfcheck_state(BOOK, self.root)
        self.assertEqual(st["state"], "STALE")
        a = F.recertify_attempt(self.root)
        self.assertTrue(a["attempt"])
        self.assertEqual(a["fingerprint_before"], "a-previous-harness")
        self.assertEqual(a["fingerprint_after"], F.harness_fingerprint())
        self.assertNotEqual(a["fingerprint_before"], a["fingerprint_after"])

    def test_a_CURRENT_certificate_asks_for_nothing(self):
        _seed_selfcheck(self.root, BOOK)
        self.assertTrue(F.selfcheck_state(BOOK, self.root)["ok"])
        a = F.recertify_attempt(self.root)
        self.assertFalse(a["attempt"])
        self.assertEqual(a["state"], "NOT_NEEDED")

    def test_a_FAILING_certificate_is_UNTOUCHED_by_this_change(self):
        # The ruling names SELFCHECK_STALE and SELFCHECK_ABSENT and nothing else. A failing
        # harness is not a stale certificate and a re-run is not its remedy.
        _seed_selfcheck(self.root, BOOK, fate="fail")
        self.assertEqual(F.selfcheck_state(BOOK, self.root)["state"], "FAILING")
        a = F.recertify_attempt(self.root)
        self.assertFalse(a["attempt"])
        self.assertEqual(a["state"], "NOT_NEEDED")
        # POSITIVE CONTROL: not attempting must not mean not refusing.
        self.assertFalse(F.may_fill(BOOK, self.root)["ok"])


class AFailingSelfCheckIsNeverRetriedIntoAPass(unittest.TestCase):

    def setUp(self):
        self.root = _repo(book=BOOK)
        _seed_selfcheck(self.root, BOOK, detail="a-previous-harness")   # STALE -> attemptable

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_before_any_attempt_it_is_attemptable(self):
        self.assertTrue(F.recertify_attempt(self.root)["attempt"])

    def test_a_recorded_automatic_FAILURE_blocks_every_later_attempt(self):
        F.record_recertification(_event(), self.root)
        a = F.recertify_attempt(self.root)
        self.assertFalse(a["attempt"])
        self.assertEqual(a["state"], "BLOCKED_BY_PRIOR_FAILURE")
        self.assertIn("already FAILED", a["reason"])

    def test_the_block_is_keyed_on_the_FINGERPRINT_so_a_FIX_reopens_the_door(self):
        # The only way out is to change the harness, which is the only thing that can fix it.
        # A flag keyed on nothing would have to be cleared by hand, and nobody would.
        F.record_recertification(_event(fingerprint_after="some-other-harness"), self.root)
        self.assertTrue(F.recertify_attempt(self.root)["attempt"])

    def test_a_MANUAL_failure_does_not_block_the_automatic_path(self):
        # A human re-running the declared fallback is not a cron retrying.
        F.record_recertification(_event(trigger="manual"), self.root)
        self.assertTrue(F.recertify_attempt(self.root)["attempt"])

    def test_a_recorded_SUCCESS_does_not_block(self):
        F.record_recertification(_event(ok=True), self.root)
        self.assertTrue(F.recertify_attempt(self.root)["attempt"])

    def test_the_NEWEST_attempt_decides_and_not_the_first(self):
        F.record_recertification(_event(ok=True, ts="2026-10-13T01:00:00"), self.root)
        F.record_recertification(_event(ok=False, ts="2026-10-13T02:00:00"), self.root)
        self.assertFalse(F.recertify_attempt(self.root)["attempt"])

    def test_an_UNREADABLE_log_blocks_rather_than_assuming_the_best(self):
        # `MA6`'s direction: a log we cannot read cannot rule out a prior failure, and the
        # safe state is books shut.
        with io.open(F.recert_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        a = F.recertify_attempt(self.root)
        self.assertFalse(a["attempt"])
        self.assertEqual(a["state"], "BLOCKED_BY_PRIOR_FAILURE")
        self.assertIn("unreadable", a["reason"])

    def test_AND_THE_BOOKS_STAY_SHUT_THROUGHOUT(self):
        """The ruling's own words, and the property the whole item rests on."""
        self.assertFalse(F.may_fill(BOOK, self.root)["ok"])
        F.record_recertification(_event(), self.root)
        gate = F.may_fill(BOOK, self.root)
        self.assertFalse(gate["ok"])
        self.assertEqual(gate["code"], "SELFCHECK_STALE")


class TheAttemptIsRecorded(unittest.TestCase):

    def setUp(self):
        self.root = _repo(book=BOOK)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_an_absent_log_is_not_an_unreadable_one(self):
        log = F.recert_log(self.root)
        self.assertTrue(log["ok"])
        self.assertTrue(log["absent"])
        self.assertEqual(log["events"], [])

    def test_when_why_and_BOTH_fingerprints_are_on_the_record(self):
        F.record_recertification(_event(), self.root)
        ev = F.recert_log(self.root)["events"][-1]
        self.assertTrue(ev["ts"])                       # stamped if the caller did not
        self.assertEqual(ev["fingerprint_before"], "older-fingerprint")
        self.assertEqual(ev["fingerprint_after"], F.harness_fingerprint())
        self.assertIn("reason", ev)
        self.assertEqual(ev["trigger"], "automatic")

    def test_the_log_appends_rather_than_replaces(self):
        F.record_recertification(_event(ts="a"), self.root)
        F.record_recertification(_event(ts="b"), self.root)
        evs = F.recert_log(self.root)["events"]
        self.assertEqual([e["ts"] for e in evs], ["a", "b"])

    def test_a_schema_it_does_not_recognise_is_REFUSED_not_read_as_empty(self):
        os.makedirs(F.fleet_dir(self.root), exist_ok=True)
        with io.open(F.recert_path(self.root), "w", encoding="utf-8") as fh:
            json.dump({"schema": "something/else", "events": [_event()]}, fh)
        log = F.recert_log(self.root)
        self.assertFalse(log["ok"])
        self.assertEqual(log["events"], [])


class TheRemedyToldToDonDependsOnWhich(unittest.TestCase):

    def setUp(self):
        self.root = _repo(book=BOOK)
        _seed_selfcheck(self.root, BOOK, detail="a-previous-harness")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_stale_certificate_says_the_cycle_will_do_it(self):
        a = F.selfcheck_action(self.root)
        self.assertTrue(a["needed"])
        self.assertEqual(a["remedy"], F.SELFCHECK_REMEDY)
        self.assertIn("next daily fleet cycle", a["remedy"])
        self.assertFalse(a["recertify_blocked"])

    def test_after_a_failure_it_says_DO_NOT_re_run_it(self):
        # The states are identical (STALE either way) and the instruction is the opposite, so
        # one remedy string would be wrong in one of the two cases.
        F.record_recertification(_event(), self.root)
        a = F.selfcheck_action(self.root)
        self.assertEqual(a["remedy"], F.SELFCHECK_REMEDY_AFTER_FAILURE)
        self.assertIn("DO NOT re-run it", a["remedy"])
        self.assertTrue(a["recertify_blocked"])

    def test_the_two_remedies_are_not_the_same_string(self):
        self.assertNotEqual(F.SELFCHECK_REMEDY, F.SELFCHECK_REMEDY_AFTER_FAILURE)


class TheAlertGoesOutBecauseTheCodesWouldNot(unittest.TestCase):

    def test_a_failing_synthetic_leg_changes_NO_refusal_code(self):
        """The measurement the explicit alert exists for, asserted rather than asserted of.

        `run_day1` returns before writing a row when the synthetic leg fails, so the books'
        codes are identical before and after. `pending` announces a refusal only when the code
        changes, so with no alert this cycle would say nothing at all.
        """
        root = _repo(book=BOOK)
        try:
            _seed_selfcheck(root, BOOK, detail="a-previous-harness")
            before = F.may_fill(BOOK, root)["code"]
            # the failure writes nothing to the stream -- only the recertification log moves
            F.record_recertification(_event(), root)
            self.assertEqual(F.may_fill(BOOK, root)["code"], before)
            p = FN.pending({}, {BOOK: before}, F.fleet_dir(root))
            # first sight of a refusal is news; the point is that the SECOND is not, which is
            # the steady state a failed re-certification sits in
            FN.announce({}, {BOOK: before}, F.fleet_dir(root), send=lambda c, b, ch=None: True)
            p2 = FN.pending({}, {BOOK: before}, F.fleet_dir(root))
            self.assertTrue(p["new_refusals"])
            self.assertFalse(p2["new_refusals"])
            self.assertTrue(p2["quiet"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_alert_alone_is_enough_to_send(self):
        p = FN.pending({}, {}, "C:/no-such-dir", alerts=["the self-check FAILED"])
        self.assertFalse(p["quiet"])
        self.assertIn("the self-check FAILED", FN.compose(p))

    def test_the_alert_comes_FIRST_in_the_message(self):
        # An alert is the one line here that asks for attention rather than recording
        # something that happened; below a list of fills it is furniture.
        p = FN.pending({}, {"zz": "SELFCHECK_STALE"}, "C:/no-such-dir",
                       alerts=["HARNESS BROKEN"])
        body = FN.compose(p)
        self.assertTrue(body.startswith("HARNESS BROKEN"), body[:80])

    def test_a_quiet_cycle_with_no_alert_still_says_nothing(self):
        p = FN.pending({}, {}, "C:/no-such-dir")
        self.assertTrue(p["quiet"])
        self.assertEqual(FN.compose(p), "")


class TheRouteWiresItTogether(unittest.TestCase):
    """End to end through Flask, with `run_day1` stubbed so no sandbox order is placed.

    THE STUB IS THE POINT, not a shortcut: the real day-1 run places a live sandbox fill, and
    what is under test here is the ROUTE's behaviour on a FAILURE — which cannot be provoked on
    a working harness without breaking the harness.
    """

    def setUp(self):
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        CONFIG.admin_token = "test-token-item51"
        app = create_saas_app(CONFIG)
        app.config["TESTING"] = True
        self.c = app.test_client()
        self.hdr = {"X-Admin-Token": CONFIG.admin_token}
        import scripts.fleet_selfcheck as SC
        self.SC = SC
        self.real = SC.run_day1

    def tearDown(self):
        self.SC.run_day1 = self.real

    def test_a_GET_never_runs_a_self_check_however_owed_it_is(self):
        """The verb carries the write, and a re-certification is a write."""
        calls = []
        self.SC.run_day1 = lambda **k: calls.append(1) or {"ok": True}
        b = self.c.get("/admin/fleet-cycle", headers=self.hdr).get_json()
        self.assertEqual(calls, [])
        self.assertFalse((b.get("recertified") or {}).get("ran"))

    def test_NO_SUITE_can_reach_the_automatic_path_and_place_a_sandbox_ORDER(self):
        """A census, because the automatic path made this reachable where it was not before.

        Until today certification needed `selfcheck=1`, so no test could start it by accident.
        Now a writing cycle starts it whenever one is owed — and in a test the fleet store is
        a fresh temp directory, so every declared book reads ABSENT and one is always owed. A
        suite that POSTed a writing cycle would therefore place a real sandbox order and spend
        ~37s doing it, in CI, on every run.

        The door itself already refuses the cheap mistake: `GET ?run=1` is 405. This pins the
        expensive one.
        """
        here = os.path.dirname(os.path.abspath(__file__))
        offenders = []
        for fn in sorted(os.listdir(here)):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            with io.open(os.path.join(here, fn), encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            for ln, line in enumerate(src.splitlines(), 1):
                if "/admin/fleet-cycle" not in line or ".post(" not in line:
                    continue
                if "run=1" in line or "selfcheck=1" in line:
                    offenders.append("%s:%d" % (fn, ln))
        self.assertEqual(offenders, [], (
            "a suite POSTs a WRITING fleet cycle, which now runs the self-check itself and "
            "places a real sandbox order: %s" % offenders))

    def test_the_body_reports_the_recertification_state_either_way(self):
        b = self.c.get("/admin/fleet-cycle", headers=self.hdr).get_json()
        rec = b.get("recertified")
        self.assertIsInstance(rec, dict)
        self.assertIn(rec.get("state"),
                      ("OWED", "NOT_NEEDED", "BLOCKED_BY_PRIOR_FAILURE"))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    print("\nitem 51 automatic re-certification: %d run, %d failures, %d errors"
          % (r.testsRun, len(r.failures), len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
