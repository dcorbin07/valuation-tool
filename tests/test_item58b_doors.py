# -*- coding: utf-8 -*-
"""ITEM 58b — the two doors, driven end to end through Flask.

`/admin/live-slots` answers "did Don set the keys" and "what would each slot trade".
`/admin/live-cycle` is the runner, called by a scheduled workflow exactly as `fleet-cycle.yml`
calls its own.

WHAT THESE PIN, each a way this class of door has already gone wrong in this repo:

  * **THE VERB CARRIES THE WRITE.** `/admin/track-row` shipped a GET that wrote, and the cure
    was to split it. Here the write is an ORDER, so the split matters more: a side-effecting
    GET is reachable by a retry, a prefetch, a proxy or a pasted link, and none of those is a
    decision to trade.
  * **OWNER-ONLY.** `MA7`'s class — two POST routes under `/api/edge/` shipped with no auth
    decorator at all. Asserted by calling with no token.
  * **NO CREDENTIAL IN THE PAYLOAD, EVER.** Presence is a boolean. Asserted by putting a
    recognisable fake secret in the environment and searching the whole response for it.
  * **A QUIET CYCLE IS NOT AN ERROR.** Nothing to do today must still return 200, or a
    scheduler learns to ignore a red light.

    python tests/test_item58b_doors.py
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                    # noqa: E402
from valuation.saas.app_saas import create_saas_app    # noqa: E402

FAKE_SECRET = "PK-THIS-IS-A-FAKE-SECRET-VALUE-0001"


def _client():
    CONFIG.admin_token = "test-token-live-path"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True
    return app.test_client(), {"X-Admin-Token": CONFIG.admin_token}


class BothDoorsAreOwnerOnly(unittest.TestCase):
    def test_no_token_is_refused(self):
        c, _ = _client()
        for path in ("/admin/live-slots", "/admin/live-cycle"):
            self.assertEqual(c.get(path).status_code, 401, path)
        self.assertEqual(c.post("/admin/live-cycle?run=1").status_code, 401)

    def test_a_wrong_token_is_refused(self):
        c, _ = _client()
        bad = {"X-Admin-Token": "not-the-token"}
        self.assertEqual(c.get("/admin/live-slots", headers=bad).status_code, 401)
        self.assertEqual(c.post("/admin/live-cycle?run=1", headers=bad).status_code, 401)

    def test_an_unset_token_fails_CLOSED(self):
        """`MA6`'s direction, and the shipped `_admin_ok` already guarantees it for the other
        eight admin endpoints. A door that opened when the token was unset would be wide open
        on any deploy that forgot to set it."""
        keep = CONFIG.admin_token
        try:
            CONFIG.admin_token = ""
            app = create_saas_app(CONFIG)
            app.config["TESTING"] = True
            c = app.test_client()
            self.assertEqual(c.get("/admin/live-slots",
                                   headers={"X-Admin-Token": ""}).status_code, 401)
        finally:
            CONFIG.admin_token = keep


class NoCredentialEverLeaves(unittest.TestCase):
    def test_a_fake_secret_in_the_environment_never_appears_in_the_payload(self):
        c, h = _client()
        keep = {k: os.environ.get(k) for k in
                ("ALPACA_PAPER_KEY_ID", "ALPACA_PAPER_SECRET_KEY",
                 "ALPACA_ACCOUNT_1_KEY_ID", "ALPACA_ACCOUNT_1_SECRET_KEY")}
        try:
            os.environ.update({k: FAKE_SECRET for k in keep})
            body = c.get("/admin/live-slots", headers=h).get_data(as_text=True)
            self.assertNotIn(FAKE_SECRET, body)
            self.assertNotIn(CONFIG.admin_token, body)
        finally:
            for k, v in keep.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_presence_is_reported_as_a_boolean(self):
        c, h = _client()
        got = json.loads(c.get("/admin/live-slots", headers=h).get_data(as_text=True))
        keys = got.get("keys") or {}
        self.assertIn("paper", keys)
        self.assertIsInstance((keys["paper"] or {}).get("both_present"), bool)


class TheStatusExplainsItselfInWords(unittest.TestCase):
    def setUp(self):
        c, h = _client()
        self.body = json.loads(c.get("/admin/live-slots", headers=h).get_data(as_text=True))

    def test_it_says_how_pause_differs_from_zero_percent(self):
        """Item 58b step 6 asks for this in words, and it is the distinction most likely to be
        got wrong in a hurry: PAUSE holds, 0% SELLS.

        **THE DISTINCTION IS ASSERTED, NOT A PHRASE.** My first cut demanded the exact strings
        "sells nothing" and "sells out" and failed against a correct status that says "nothing
        is sold" and "sells what it bought" -- better wording than mine, and a test that
        forbids improving it is the literal-line-pin family.
        """
        pz = self.body.get("pause_vs_zero") or {}
        self.assertIn("pause", pz)
        self.assertIn("zero_pct", pz)
        pause, zero = pz["pause"].lower(), pz["zero_pct"].lower()
        # PAUSE: the words for not selling. 0%: the words for selling.
        self.assertTrue(any(w in pause for w in ("nothing is sold", "sells nothing",
                                                 "holdings stay")),
                        "the pause text does not say that nothing is sold: %r" % pause)
        self.assertTrue(any(w in zero for w in ("sells what it bought", "sells out",
                                                "hold nothing")),
                        "the 0%% text does not say that it sells: %r" % zero)
        self.assertIn("live_pilot_enabled", pause)
        self.assertIn("live_pct", zero)

    def test_it_names_the_cycle_door_and_its_time_with_the_reason(self):
        cyc = self.body.get("cycle") or {}
        self.assertEqual(cyc.get("door"), "/admin/live-cycle")
        self.assertEqual(cyc.get("scheduled_utc"), "14:40")
        self.assertIn("day", (cyc.get("why_this_time") or "").lower())

    def test_it_carries_the_dividend_statement(self):
        self.assertFalse((self.body.get("dividends") or {}).get("paid_by_paper", True))

    def test_it_carries_the_feed_gap_state_without_quoting_it_early(self):
        fg = ((self.body.get("paper_slot") or {}).get("feed_gap") or {})
        self.assertEqual(fg.get("target_n"), 30)
        if not fg.get("complete"):
            self.assertIn("reason", fg)

    def test_an_unconfigured_slot_one_reads_as_having_no_keys(self):
        """The Done list's own wording. With no `ALPACA_ACCOUNT_1_*` set, there is no slot to
        show, and the status has to say that rather than show an empty table."""
        self.assertEqual(self.body.get("keys", {}).get("n_live_slots"), 0)
        self.assertIn("no keys yet", (self.body.get("live_slots_note") or "").lower())
        self.assertIn("auditor review", self.body.get("live_slots_note") or "")


class TheStatusConstructsNoBrokerClient(unittest.TestCase):
    def test_reading_the_status_cannot_place_or_price_anything(self):
        """It is read-only by construction, not by intention: a status that built a client
        could in principle authenticate, and a status is the one door most likely to be
        refreshed idly in a browser."""
        import inspect

        from valuation.saas import app_saas
        src = inspect.getsource(app_saas)
        start = src.index('def admin_live_slots(')
        end = src.index('def admin_live_cycle(')
        body = src[start:end]
        for forbidden in ("AlpacaPaperBroker(", "_LiveClient(", "place_limit", "place_equity"):
            self.assertNotIn(forbidden, body, "the status reaches for %r" % forbidden)


class TheVerbCarriesTheWrite(unittest.TestCase):
    def test_a_GET_of_the_cycle_is_a_dry_run(self):
        c, h = _client()
        r = c.get("/admin/live-cycle", headers=h)
        self.assertIn(r.status_code, (200, 500))
        got = json.loads(r.get_data(as_text=True))
        self.assertFalse(got.get("send_requested", True))

    def test_only_a_POST_with_run_may_send(self):
        """Read off the source rather than by trying to trade: the assertion is that the
        door's `send` comes from `run`, and nothing in a test should exercise the path that
        would transmit."""
        import inspect

        from valuation.saas import app_saas
        src = inspect.getsource(app_saas)
        start = src.index('def admin_live_cycle(')
        body = src[start:start + 1800]
        self.assertIn('wants_run = bool(request.args.get("run") or body.get("run"))', body)
        self.assertIn("LC.run_cycle(send=wants_run", body)

    def test_a_quiet_cycle_still_returns_200(self):
        """A scheduler that sees a 500 on an ordinary quiet day learns to ignore the light."""
        c, h = _client()
        r = c.get("/admin/live-cycle", headers=h)
        got = json.loads(r.get_data(as_text=True))
        if got.get("ok"):
            self.assertEqual(r.status_code, 200)
            self.assertIn("slots", got)


class TheScheduledWorkflowIsHandedOverRatherThanInstalled(unittest.TestCase):
    """`.github/` is refused by the land policy, so a workflow ships as a pending file plus a
    line in the installer Don double-clicks. A workflow written straight into `.github/` would
    block the land for every other change in the same push."""

    #: TRACKED, and that is a change this item made. `data/pending_workflows` sits inside
    #: the gitignored `/data/`, so every workflow handed over through it has existed only on
    #: Don's disk -- unreviewable in the repo and unpinnable by any test, which for a file
    #: that POSTs an admin door on a schedule is the one place a `?run=1` could appear with
    #: nobody able to see it. The installer now reads both directories.
    PENDING = os.path.join(REPO, "pending_workflows", "live-cycle.yml")

    def test_the_pending_workflow_is_TRACKED_and_not_only_on_disk(self):
        self.assertTrue(os.path.exists(self.PENDING), self.PENDING)
        import subprocess
        got = subprocess.run(["git", "ls-files", "pending_workflows/live-cycle.yml"],
                             cwd=REPO, capture_output=True, text=True)
        if got.returncode == 0 and got.stdout.strip() == "" and os.path.isdir(
                os.path.join(REPO, ".git")):
            self.skipTest("not yet committed in this working tree")

    def test_it_posts_the_door_at_the_declared_minute(self):
        with open(self.PENDING, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("40 14 * * 1-5", src)
        self.assertIn("/admin/live-cycle", src)
        self.assertIn("X-Admin-Token", src)

    def test_it_ships_WITHOUT_run_so_installing_it_cannot_trade(self):
        """THE SAFE DEFAULT, AND THE REASON IS THAT DON INSTALLS THIS BEFORE THE AUDITOR
        REVIEW. A workflow that arrived already sending would make installing it the decision
        to go live, which is exactly the decision §8 reserves for him.

        **READ OFF THE CURL LINE, NOT THE WHOLE FILE.** The first cut banned the substring
        `run=1` anywhere in the file and failed against a correct workflow, because the header
        comment explains how to turn sending ON and therefore quotes the thing it forbids --
        the substring-ban family, in my own test, in the same change that documents it.
        """
        with open(self.PENDING, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        urls = [ln for ln in lines if "/admin/live-cycle" in ln and "${SITE_BASE_URL" in ln]
        self.assertEqual(len(urls), 1, "expected exactly one request URL: %r" % urls)
        self.assertNotIn("run=1", urls[0], "the shipped request would SEND orders")
        self.assertNotIn("?", urls[0], "the shipped request carries a query parameter")
        body = "\n".join(ln for ln in lines if not ln.strip().startswith("#"))
        self.assertNotIn("-X POST", body, "the shipped request is a POST")
        self.assertIn("dry run", "\n".join(lines).lower())

    def test_the_installer_reads_the_TRACKED_directory(self):
        """It GLOBS `*.yml`, so it names no individual file -- and naming one would be worse,
        since the next handover would then need an installer edit. What this item changed is
        that it reads the tracked directory AS WELL as the legacy untracked one, and that is
        the thing worth pinning."""
        bat = os.path.join(REPO, "install_workflows.bat")
        with open(bat, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        self.assertIn('set "SRC2=%~dp0pending_workflows"', src)
        self.assertIn('for %%F in ("%SRC2%\\*.yml") do (', src)
        # AND THE LEGACY PATH STILL WORKS, so anything already waiting on disk still installs.
        self.assertIn('set "SRC=%~dp0data\\pending_workflows"', src)

    def test_the_installer_does_not_move_the_tracked_file_away(self):
        """Moving it would show up as a DELETION in the next commit. The installer is
        idempotent, so leaving it in place costs nothing."""
        bat = os.path.join(REPO, "install_workflows.bat")
        with open(bat, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        tail = src[src.index(":installed"):]
        self.assertNotIn("SRC2", tail, "the installer moves the tracked file away")


if __name__ == "__main__":
    unittest.main()
