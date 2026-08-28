"""THE FLEET IS VISIBLE — the public shelf, and the notifier that breaks the silence.

Eighteen books accrued records and nothing rendered them and nothing announced a fill. Two
pieces, and the risk in each is the same one: a page about paper books with no verdict due is
one careless sentence away from reading as a track record, and an alert that fires every day
is one Don stops reading.

  * THE COPY IS ASSERTED AGAINST THE RENDERED PAYLOAD, never the source
    (`test_the_rendered_shelf_carries_no_banned_phrase`), because rendering is where copy
    leaks. The tuple has BOTH controls, and the negative one is not decorative: the first cut
    banned the bare token `track record` and fired on this project's own posture sentence,
    *"it is NOT a track record"*.
  * ZERO FILLS IS TWO DIFFERENT FACTS (`test_the_two_meanings_of_zero_are_distinguishable`).
    A working rule that found nothing is a market observation; no rule at all is a build gap.
    `fleet.cycle` refuses to conflate them and neither may the page.
  * THE ALERT IS QUIET WHEN NOTHING HAPPENED (`test_a_quiet_cycle_announces_nothing`) and does
    not repeat itself (`test_the_same_fill_is_never_announced_twice`), or it becomes the thing
    that gets ignored.
  * AND THE WATERMARK MOVES ONLY ON A SUCCESSFUL SEND
    (`test_a_failed_send_does_not_advance_the_watermark`) — advancing it on a failed post
    loses the very fill it failed to announce, silently and permanently.

Run: python tests/test_fleet_visible.py
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet_notify as N                # noqa: E402
from valuation.web import fleet_public as FP                # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# =======================================================================================
# THE SHELF
# =======================================================================================
class TheShelf(unittest.TestCase):

    def test_it_never_raises_and_says_why_when_the_harness_is_absent(self):
        real = FP._fleet
        FP._fleet = lambda: None
        try:
            d = FP.books()
        finally:
            FP._fleet = real
        self.assertFalse(d["available"])
        self.assertTrue(d["reason"])
        self.assertEqual(d["books"], [])

    def test_a_draft_is_not_a_book_and_the_exclusion_is_counted(self):
        """Mechanical, not editorial — `L7`'s rule is about dropping VERIFIED books somebody
        found uninteresting, and a draft is not a book by a test anyone can apply."""
        d = FP.books()
        if not d["available"]:
            return
        for b in d["books"]:
            self.assertFalse(str(b["book"]).startswith("DRAFT_"), b["book"])
        self.assertIsInstance(d["drafts_excluded"], int)

    def test_it_runs_no_entry_rule_and_calls_no_cycle(self):
        """A page render must not place an order, take a quote or cost a runner budget.

        Read from the SYNTAX TREE: `cycle()` executes rules, so calling it from a surface is
        the defect, and a runtime check only sees the paths a test happens to exercise.
        """
        tree = ast.parse(open(os.path.join(ROOT, "valuation", "web", "fleet_public.py"),
                              encoding="utf-8").read())
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for forbidden in ("cycle", "record", "record_fill", "submit", "place"):
            self.assertNotIn(forbidden, called, forbidden)
        # ...and it composes state from the primitives the cycle itself uses.
        self.assertIn("may_fill", called)
        self.assertIn("entry_rule", called)

    def test_the_two_meanings_of_zero_are_distinguishable(self):
        """`fleet.cycle` refuses to report a build gap as a quiet market, and so must this."""
        self.assertNotEqual(FP.ARMED, FP.ARMED_NO_ENTRY_RULE)
        self.assertIn("market", FP.STATE_BLURB[FP.ARMED])
        self.assertIn("build gap", FP.STATE_BLURB[FP.ARMED_NO_ENTRY_RULE])
        self.assertIn("build gap", FP.QUIET_MEANS)
        # The distinction is in the payload, not only in prose.
        self.assertEqual(len({FP.ARMED, FP.ARMED_NO_ENTRY_RULE, FP.BLOCKED}), 3)

    def test_the_link_is_pinned_at_the_commit_and_not_at_a_branch(self):
        """A link to `main` shows today's bytes under a sha promising yesterday's, which is
        the one thing this shelf exists to make checkable."""
        sha = "0123456789abcdef0123456789abcdef01234567"
        url = FP.declaration_url(sha, "DECL_x.md")
        self.assertIn(sha, url)
        self.assertNotIn("/main/", url)
        self.assertNotIn("/HEAD/", url)
        self.assertIsNone(FP.declaration_url("", "DECL_x.md"))
        self.assertIsNone(FP.declaration_url(sha, ""))

    def test_the_memo_is_opt_in_so_no_test_can_be_answered_stale(self):
        import inspect
        sig = inspect.signature(FP.books)
        self.assertIs(sig.parameters["cache"].default, False)
        FP.reset_memo()
        self.assertEqual(FP._MEMO, {})

    def test_the_banned_tuple_has_both_controls(self):
        """A tuple with no positive control passes by seeing nothing; one with no negative
        control is deleted the first week it fires on an honest caveat — which is exactly what
        the first cut did to this module's own posture sentence."""
        hits = FP.violations("Our track record proves the strategy. We recommend you buy now "
                             "for guaranteed, risk-free returns.")
        self.assertTrue(len(hits) >= 4, hits)
        self.assertEqual(FP.violations(FP.own_copy()), [],
                         "the module's own copy trips its own guard")
        # The specific near-miss that caused the repair: a DENIAL must survive.
        self.assertEqual(FP.violations("this is not a track record"), [])
        self.assertTrue(FP.violations("our track record"))

    def test_the_posture_travels_in_the_payload_not_the_template(self):
        d = FP.books()
        for key in ("posture", "not_a_record", "quiet_means", "repo_note"):
            self.assertTrue(d.get(key), key)
        self.assertIn("no capital is at risk", d["posture"].lower())

    def test_the_rendered_shelf_carries_no_banned_phrase(self):
        """Against the RENDERED payload. `hero.py`'s lesson: a caveat a surface can decline to
        show is not a safeguard, and the same is true of a ban it can render around."""
        import html as _h
        import tests.test_research_shelf_and_calibration as T   # noqa: WPS433

        page = T._page()
        i = page.find("Books declared before")
        if i < 0:
            return
        j = page.find("</section>", i)
        self.assertEqual(FP.violations(_h.unescape(page[i:j])), [])

    def test_the_shelf_renders_the_provenance_columns(self):
        import tests.test_research_shelf_and_calibration as T   # noqa: WPS433

        page = T._page()
        i = page.find("Books declared before")
        if i < 0:
            return
        sec = page[i:page.find("</section>", i)]
        for col in ("Declared in commit", "Declared on", "Days", "Fills", "State"):
            self.assertIn(col, sec, col)


# =======================================================================================
# THE NOTIFIER
# =======================================================================================
class TheNotifier(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="fnotify_")
        self.sent = []

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _send(self, ok=True):
        def send(cfg, body):
            self.sent.append(body)
            return ok
        return send

    FILL = {"kind": "fill", "seq": "1", "symbol": "SPY", "occ": "SPY260101C00500000",
            "side": "buy", "qty": "1", "fill_price": "1.25", "arm": "B"}

    def test_a_fill_announces(self):
        r = N.announce({"f1": [dict(self.FILL)]}, {}, self.d, send=self._send())
        self.assertTrue(r["sent"])
        self.assertEqual(r["n_fills"], 1)
        self.assertIn("f1", self.sent[0])
        self.assertIn("SPY260101C00500000", self.sent[0])

    def test_the_same_fill_is_never_announced_twice(self):
        """The cycle door can legitimately run twice — a retry, a manual dispatch. Without the
        watermark the second run re-announces the first run's fill and the alert starts lying."""
        rows = {"f1": [dict(self.FILL)]}
        N.announce(rows, {}, self.d, send=self._send())
        again = N.announce(rows, {}, self.d, send=self._send())
        self.assertFalse(again["sent"])
        self.assertTrue(again["quiet"])
        self.assertEqual(len(self.sent), 1)

    def test_a_later_fill_still_announces_after_an_earlier_one(self):
        N.announce({"f1": [dict(self.FILL)]}, {}, self.d, send=self._send())
        second = dict(self.FILL, seq="2", occ="SPY260101C00510000")
        r = N.announce({"f1": [dict(self.FILL), second]}, {}, self.d, send=self._send())
        self.assertTrue(r["sent"])
        self.assertEqual(r["n_fills"], 1)
        self.assertIn("SPY260101C00510000", self.sent[-1])

    def test_a_quiet_cycle_announces_nothing(self):
        """Not even a 'nothing to report' line, which is the same noise wearing a politer hat."""
        r = N.announce({"f1": []}, {}, self.d, send=self._send())
        self.assertTrue(r["quiet"])
        self.assertFalse(r["sent"])
        self.assertEqual(self.sent, [])

    def test_a_NEW_refusal_announces_and_the_same_one_does_not_repeat(self):
        """A book that cannot fill is same-day news. Eighteen books blocked on the same check
        every evening is not — and an alert that says the same thing daily is one you stop
        reading, so the day it changes nobody notices."""
        ref = {"f3": "SELFCHECK_ABSENT"}
        first = N.announce({}, ref, self.d, send=self._send())
        self.assertTrue(first["sent"])
        self.assertEqual(first["n_new_refusals"], 1)
        again = N.announce({}, ref, self.d, send=self._send())
        self.assertTrue(again["quiet"])
        self.assertEqual(len(self.sent), 1)

    def test_a_refusal_that_CHANGES_reason_announces_again(self):
        N.announce({}, {"f3": "SELFCHECK_ABSENT"}, self.d, send=self._send())
        r = N.announce({}, {"f3": "SHORT_BOOK_WITHOUT_ASSIGNMENT"}, self.d, send=self._send())
        self.assertTrue(r["sent"])
        self.assertIn("SHORT_BOOK_WITHOUT_ASSIGNMENT", self.sent[-1])

    def test_a_book_that_stops_being_blocked_is_also_news(self):
        N.announce({}, {"f3": "SELFCHECK_ABSENT"}, self.d, send=self._send())
        r = N.announce({}, {}, self.d, send=self._send())
        self.assertTrue(r["sent"])
        self.assertEqual(r["n_cleared"], 1)
        self.assertIn("No longer blocked", self.sent[-1])

    def test_a_failed_send_does_not_advance_the_watermark(self):
        """Advancing on a failed post loses the very fill it failed to announce, silently and
        permanently."""
        rows = {"f1": [dict(self.FILL)]}
        bad = N.announce(rows, {}, self.d, send=self._send(ok=False))
        self.assertFalse(bad["sent"])
        good = N.announce(rows, {}, self.d, send=self._send(ok=True))
        self.assertTrue(good["sent"], "the fill was lost by a failed send")
        self.assertEqual(good["n_fills"], 1)

    def test_it_never_raises_when_the_webhook_explodes(self):
        def boom(cfg, body):
            raise RuntimeError("discord is down")
        r = N.announce({"f1": [dict(self.FILL)]}, {}, self.d, send=boom)
        self.assertFalse(r["sent"])
        self.assertIn("webhook failed", r["reason"])

    def test_the_message_reports_what_happened_and_never_how_it_is_going(self):
        """No P&L, no running total, no verdict — those have pre-committed horizons and a
        Discord line is not where they get read early."""
        msg = N.compose(N.pending({"f1": [dict(self.FILL)]}, {}, self.d))
        low = msg.lower()
        for banned in ("p&l", "pnl", "profit", "return", "up ", "down ", "%",
                       "winning", "losing", "verdict"):
            self.assertNotIn(banned, low, banned)
        self.assertEqual(FP.violations(msg), [])

    def test_the_state_file_sits_beside_the_streams_and_survives_a_bad_read(self):
        with open(N.state_path(self.d), "w", encoding="utf-8") as f:
            f.write("{ not json")
        r = N.announce({"f1": [dict(self.FILL)]}, {}, self.d, send=self._send())
        self.assertTrue(r["sent"], "an unreadable state file must not swallow a fill")


class TheWiring(unittest.TestCase):

    def test_the_cycle_door_announces_only_on_a_writing_run(self):
        """A GET computes and must not tell anyone something happened, because nothing did."""
        src = open(os.path.join(ROOT, "valuation", "saas", "app_saas.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                   and n.name == "admin_fleet_cycle"), None)
        self.assertIsNotNone(fn)
        guarded = False
        for node in ast.walk(fn):
            if isinstance(node, ast.If):
                names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
                body = ast.dump(ast.Module(body=node.body, type_ignores=[]))
                if "wants_run" in names and "announce" in body:
                    guarded = True
        self.assertTrue(guarded, "the announcement is not gated on a writing run")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
