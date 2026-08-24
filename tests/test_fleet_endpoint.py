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

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

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
        direct = F.cycle(write=False)
        for k in ("books_declared", "armed", "blocked", "entry_rules_implemented",
                  "breathing"):
            self.assertEqual(b[k], direct[k], k)

    def test_the_web_app_does_NOT_import_the_assignment_model(self):
        """`MA59`'s quarantine, and it caught this handler in the act.

        The route briefly registered S3-I3 itself, reasoning that the runner is the
        composition root. **`valuation/edge/assignment.py` imports the ARCHIVED
        `valuation/edge/dividends.py`**, so importing the model from the web app made a closed
        study reachable from a production entry point — *"reaching one from the live app means
        the product is running an experiment."* Checked on the SYNTAX TREE of the handler's own
        module, so a lazy import inside the function is caught too: hiding the edge from a
        static guard is silencing it, not satisfying it.
        """
        import ast
        src = io.open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                names.update(a.name for a in n.names)
                if n.module:
                    names.add(n.module.rsplit(".", 1)[-1])
            elif isinstance(n, ast.Import):
                names.update(a.name.rsplit(".", 1)[-1] for a in n.names)
        self.assertIn("fleet", names, "the import scan saw nothing")
        self.assertNotIn("assignment", names)
        self.assertNotIn("dividends", names)

    def test_the_door_REGISTERS_the_entry_rules_or_the_arming_is_invisible(self):
        """Registration is an explicit call and never an import side effect (`S3-I3`'s
        convention), so if this handler does not make it, NOTHING does.

        The failure this closes is worse than not building the rules: the door would keep
        reporting `entry_rules_implemented: 0` with the rules sitting built and unreachable,
        which reads as *"the work was not done"* rather than *"the work is not wired"*.
        """
        c, hdr = _client()
        b = c.get("/admin/fleet-cycle", headers=hdr).get_json()
        self.assertIn("f1_fill_ab", b["entry_rules_registered"])
        self.assertIn("f3_bear_puts", b["entry_rules_registered"])
        self.assertGreaterEqual(b["entry_rules_implemented"], 2)

    def test_registering_the_rules_did_not_smuggle_in_a_quarantined_study(self):
        """The contrast that makes the quarantine a TEST rather than a blanket ban.

        `fleet_books` is registered and `assignment` is not, and the difference is measured:
        one closure is clean, the other reaches the archived `dividends`. If importing
        `fleet_books` ever pulled an archived module in, `tests/test_ma59_quarantine.py`
        fails -- this asserts the narrower thing the handler itself controls.
        """
        import ast
        src = io.open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                      encoding="utf-8").read()
        names = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.ImportFrom):
                names.update(a.name for a in n.names)
            elif isinstance(n, ast.Import):
                names.update(a.name.rsplit(".", 1)[-1] for a in n.names)
        self.assertIn("fleet_books", names)
        self.assertNotIn("assignment", names)
        self.assertNotIn("dividends", names)

    def test_the_short_books_refuse_and_the_body_SAYS_WHY(self):
        """The cost of the quarantine, stated in the response rather than left to be inferred.

        A reader seeing six books at DECLARATION_INVALID must be able to tell *"the assignment
        model is not registered in this process"* from *"these declarations are malformed"*.
        """
        c, hdr = _client()
        b = c.get("/admin/fleet-cycle", headers=hdr).get_json()
        self.assertFalse(b["assignment_provider_registered"])
        self.assertIn("MA59", b["assignment_note"])
        self.assertIn("dividends", b["assignment_note"])
        states = {r["book"]: r["state"] for r in b["books"] if r.get("is_book")}
        for short in ("f4_eventfree_premium", "f6_collar_ledger", "f8_csp_entry_financing",
                      "f10_clean_csp", "f17_vrp_percentile_sells", "f18_boring_book"):
            self.assertEqual(states.get(short), "DECLARATION_INVALID", short)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
