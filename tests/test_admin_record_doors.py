"""ITEMS 23 AND 24 — THE TWO RECORD-REPAIR DOORS, DRIVEN THROUGH FLASK.

**THIS SUITE EXISTS BECAUSE OF A GAP IN MY OWN WORK ON THIS BATCH.** Item 24 shipped
`/admin/score-alerts` with 41 tests behind the SCORER and not one behind the DOOR, and item 23
shipped `fleet_history.invalidate_unmeasured_dip_span` with **zero callers and no route at all**
-- a repair nobody, including the owner, could apply. Its own docstring said *"run this on the
service"* and nothing on the service could. **A repair with no door is not a repair**, and the
contract-bound track writer already paid for that lesson: it needed four doors before one row
could be written, and the gap was invisible for exactly as long as nobody tried.

WHAT THESE PIN, each a way this class of door has gone wrong in this repository:

  * **THE VERB CARRIES THE WRITE.** `/admin/track-row` shipped a GET that wrote, and the cure
    was to split it: a side-effecting GET on an append-only record is reachable by a retry, a
    prefetch, a proxy or a pasted link, and none of those is a decision to restate a published
    figure. Both doors are asserted to refuse `GET ?write=1` with 405 **before** auth, so the
    refusal does not depend on a token.
  * **OWNER-ONLY.** `MA7`'s class -- two POST routes under `/api/edge/` shipped with no auth
    decorator at all. Asserted by calling with no token.
  * **`through` HAS NO DEFAULT AND THE REFUSAL SAYS WHY.** It is the last day item 19's broken
    screen wrote, and a constant would silently mislabel real rows if the deploy slipped --
    `MA5`'s defect with a one-way cost, since by the time anyone runs this genuine rows are
    already accruing after that date.
  * **A PREVIEW WRITES NOTHING.** Asserted against the record itself, not against the response.

    python tests/test_admin_record_doors.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                    # noqa: E402
from valuation.edge import fleet_history as FH          # noqa: E402
from valuation.saas.app_saas import create_saas_app     # noqa: E402

DOORS = ("/admin/invalidate-dip-span", "/admin/score-alerts")


def _client():
    CONFIG.admin_token = "test-token-record-doors"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True
    return app.test_client(), {"X-Admin-Token": CONFIG.admin_token}


class BothDoorsAreOwnerOnly(unittest.TestCase):
    def test_no_token_is_refused_on_every_verb(self):
        c, _ = _client()
        for d in DOORS:
            self.assertIn(c.get(d).status_code, (401, 403), d)
            self.assertIn(c.post(d).status_code, (401, 403), d)


class AGetNeverWrites(unittest.TestCase):
    """The `track-row` defect, closed on both doors."""

    def test_a_GET_asking_to_write_is_405(self):
        c, hdr = _client()
        for d in DOORS:
            r = c.get(d + "?write=1", headers=hdr)
            self.assertEqual(r.status_code, 405, d)
            self.assertIn("POST-only", (r.get_json() or {}).get("error", ""), d)

    def test_the_405_does_not_depend_on_the_token(self):
        """Ordering matters: a refusal that needs auth first is one an unauthenticated
        prefetch never reaches, so the write-shaped GET would 401 and look handled."""
        c, _ = _client()
        for d in DOORS:
            self.assertEqual(c.get(d + "?write=1").status_code, 405, d)


class ThroughIsRequiredAndSaysWhy(unittest.TestCase):
    def test_a_missing_through_is_422_and_explains_itself(self):
        c, hdr = _client()
        r = c.post("/admin/invalidate-dip-span?write=1", headers=hdr)
        self.assertEqual(r.status_code, 422)
        b = r.get_json()
        self.assertIn("through", b["error"])
        self.assertIn("deploy", b["why"])
        self.assertEqual(b["span_starts"], FH.UNMEASURED_DIP_FROM)

    def test_a_through_before_the_span_start_is_refused_by_the_function(self):
        """The bar belongs to `invalidate_unmeasured_dip_span`, not to the route -- or the
        route and the function would hold two definitions of one rule (`B7`)."""
        res = FH.invalidate_unmeasured_dip_span(through="2026-01-01")
        self.assertFalse(res["ok"])
        self.assertIn(FH.UNMEASURED_DIP_FROM, res["reason"])

    def test_a_malformed_through_is_refused(self):
        for bad in ("2026-8-6", "yesterday", "20260806", ""):
            self.assertFalse(FH.invalidate_unmeasured_dip_span(through=bad)["ok"], bad)


class APreviewWritesNothing(unittest.TestCase):
    def test_a_GET_reports_and_leaves_the_record_alone(self):
        """Asserted against the RECORD, not the response: a door that said `applied: []`
        while appending would pass a response-only check."""
        c, hdr = _client()
        before = len(FH.invalid_spans() or [])
        r = c.get("/admin/invalidate-dip-span?through=2026-10-03", headers=hdr)
        self.assertEqual(r.status_code, 200)
        b = r.get_json()
        self.assertEqual(b["applied"], [])
        self.assertEqual(b["would_label"]["from"], FH.UNMEASURED_DIP_FROM)
        self.assertEqual(b["would_label"]["through"], "2026-10-03")
        self.assertEqual(len(FH.invalid_spans() or []), before)

    def test_the_preview_carries_the_reason_it_would_record(self):
        """ITEM 27(a) MOVED THIS FIELD, AND THE CHECK IS KEPT RATHER THAN RETIRED.

        The preview used to be hand-built in the route and put the invalidation reason in
        `reason`. It now calls `invalidate_unmeasured_dip_span(dry_run=True)`, whose `reason`
        already means *why this failed* and is empty on success -- so the reason it WOULD
        record moved to `would_record_reason` instead of overwriting a refusal field. The
        property this test exists for is unchanged: a preview must say what it would write.
        """
        c, hdr = _client()
        b = c.get("/admin/invalidate-dip-span?through=2026-10-03",
                  headers=hdr).get_json()
        self.assertEqual(b["would_record_reason"], FH.UNMEASURED_DIP_REASON)
        self.assertIn("ITEM 19", b["would_record_reason"])
        self.assertEqual(b["reason"], "", "`reason` is the failure field, empty on success")


class TheFunctionAppendsAndNeverDeletes(unittest.TestCase):
    """Item 23's own instruction: label the rows, do not delete them."""

    def test_the_source_has_no_delete_or_truncate(self):
        import ast
        with open(os.path.join(REPO, "valuation", "edge", "fleet_history.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "invalidate_unmeasured_dip_span")
        body = ast.unparse(fn)
        for banned in ("os.remove", "os.unlink", "shutil.rmtree"):
            self.assertNotIn(banned, body, banned)

    def test_it_is_reachable_from_the_route(self):
        """THE WHOLE REASON THIS SUITE EXISTS. It shipped with zero callers."""
        import ast
        with open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "admin_invalidate_dip_span")
        self.assertIn("invalidate_unmeasured_dip_span", ast.unparse(fn))


if __name__ == "__main__":
    unittest.main(verbosity=2)
