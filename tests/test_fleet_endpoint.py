"""S3-I1 THE RUNNER'S DOOR — `/admin/fleet-cycle`, driven end to end through Flask.

`PT-WRITER`'s lesson is the architecture: a fleet cycle needs the Tradier sandbox token, the
network and the fleet records store AT ONCE, and only the Render service holds all three. So
the runner is a cron POSTing this door, exactly as `track-row.yml` does for the bound Index.

WHAT THESE PIN, and each is a way this class of door has already gone wrong here:

  * **THE VERB CARRIES THE WRITE.** `/admin/track-row` shipped a GET that wrote, and the
    recorded cure was to split it: a side-effecting GET on an append-only record is reachable
    by a retry, a prefetch, a proxy or a pasted link, and none of those is a decision to
    record a trading day. Fleet streams are append-only AND hash-chained, so the same split
    is enforced here from the first commit rather than after the defect.
  * **IT IS OWNER-ONLY.** `MA7`'s class -- two POST routes under `/api/edge/` shipped with no
    auth decorator. Asserted by calling with no token.
  * **A QUIET DAY IS NOT AN ERROR.** The cycle places nothing today and must still return
    200, or a scheduler learns to ignore a red light. The body carries `breathing` and a
    `note` instead, which is what an alert should key on.

    python tests/test_fleet_endpoint.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                    # noqa: E402
from valuation.edge import fleet as F                  # noqa: E402
from valuation.saas.app_saas import create_saas_app    # noqa: E402


def _client():
    CONFIG.admin_token = "test-token-fleet-cycle"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True
    return app.test_client(), {"X-Admin-Token": CONFIG.admin_token}


class TheRunnersDoor(unittest.TestCase):

    def test_it_refuses_without_the_admin_token(self):
        """`MA7`'s class: two POST routes under /api/edge/ shipped with no auth at all."""
        c, _ = _client()
        self.assertIn(c.get("/admin/fleet-cycle").status_code, (401, 403))
        self.assertIn(c.post("/admin/fleet-cycle").status_code, (401, 403))

    def test_a_GET_computes_the_cycle_and_returns_it(self):
        c, hdr = _client()
        r = c.get("/admin/fleet-cycle", headers=hdr)
        self.assertEqual(r.status_code, 200)
        b = r.get_json()
        self.assertTrue(b["ok"])
        self.assertFalse(b["wrote"])
        self.assertEqual(b["fills_written"], 0)

    def test_a_GET_asking_to_RUN_is_refused_405_and_writes_nothing(self):
        """THE `track-row` DEFECT, closed here before it could ship rather than after."""
        c, hdr = _client()
        r = c.get("/admin/fleet-cycle?run=1", headers=hdr)
        self.assertEqual(r.status_code, 405)
        b = r.get_json()
        self.assertFalse(b["wrote"])
        self.assertIn("POST-only", b["error"])

    def test_a_quiet_cycle_is_200_and_says_so_in_the_body_rather_than_in_the_status(self):
        """A refusal-as-5xx teaches a scheduler to retry something that is not broken; a
        quiet-day-as-error teaches an operator to ignore the alert. Neither is wanted."""
        c, hdr = _client()
        b = c.get("/admin/fleet-cycle", headers=hdr).get_json()
        self.assertFalse(b["breathing"])
        self.assertIn("DECLARED-BUT-NOT-BREATHING", b["note"])

    def test_the_body_names_every_declared_book_and_the_sandbox_caveat_travels(self):
        c, hdr = _client()
        b = c.get("/admin/fleet-cycle", headers=hdr).get_json()
        self.assertGreaterEqual(b["books_declared"], 17)
        self.assertIn("sandbox", b["sandbox_caveat"].lower())

    def test_the_route_delegates_to_fleet_cycle_and_does_no_arithmetic_of_its_own(self):
        """B7. A door that recomputes is a second implementation waiting to drift."""
        c, hdr = _client()
        b = c.get("/admin/fleet-cycle", headers=hdr).get_json()
        from valuation.edge import assignment
        assignment.register(F)          # the door registers; match it before comparing
        direct = F.cycle(write=False)
        for k in ("books_declared", "armed", "blocked", "entry_rules_implemented",
                  "breathing"):
            self.assertEqual(b[k], direct[k], k)

    def test_the_door_registers_S3I3_so_the_SIX_SHORT_BOOKS_are_not_refused(self):
        """THE COMPOSITION ROOT. r1's model does not self-register on import, on purpose:
        *"importing this module to read one number cannot silently unblock every short book
        in the fleet."* So the process that actually runs the fleet must make the call, and
        a script that reads one number must not. Without it F-4, F-6, F-8, F-10, F-17 and
        F-18 refuse with SHORT_BOOK_WITHOUT_ASSIGNMENT -- the safe direction, and not the one
        a live runner wants."""
        c, hdr = _client()
        b = c.get("/admin/fleet-cycle", headers=hdr).get_json()
        self.assertTrue(b.get("assignment_provider_registered"),
                        b.get("assignment_registration_error"))
        states = {r["book"]: r["state"] for r in b["books"] if r.get("is_book")}
        for short in ("f4_eventfree_premium", "f6_collar_ledger", "f8_csp_entry_financing",
                      "f10_clean_csp", "f17_vrp_percentile_sells", "f18_boring_book"):
            self.assertIn(short, states)
            self.assertNotEqual(states[short], "DECLARATION_INVALID",
                                "%s refused for want of an assignment provider" % short)

    def test_a_broken_assignment_model_does_not_take_the_whole_cycle_down(self):
        """The long books are unaffected by it and the short ones then refuse by the ordinary
        rule, which is exactly what should happen -- so this must be a 200, not a 500."""
        import valuation.edge.assignment as A
        real = A.register
        A.register = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("model is broken"))
        try:
            c, hdr = _client()
            r = c.get("/admin/fleet-cycle", headers=hdr)
            self.assertEqual(r.status_code, 200)
            b = r.get_json()
            self.assertFalse(b["assignment_provider_registered"])
            self.assertIn("broken", str(b["assignment_registration_error"]))
            self.assertGreaterEqual(b["books_declared"], 17)
        finally:
            A.register = real


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
