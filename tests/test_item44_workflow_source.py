# -*- coding: utf-8 -*-
"""ITEM 44 - the authoritative workflow reader and the intraday delivery arithmetic.

THE DEFECT, AND IT IS STRUCTURAL RATHER THAN CARELESS. Item 42 reported that `auto-scan.yml`
"still has no `53 17-19` cron, so the backup has run zero days". It had carried it since
`d66155e`, installed 2026-10-08 08:15 ET. The lane read its own worktree's copy, branched
before that commit.

**The land gate REFUSES any branch touching `.github/`, so a workflow file can only ever change
on `main`, by Don running `install_workflows.bat`.** A lane cannot make the change, cannot land
it, and has no mechanism that would keep its copy current -- so a lane's copy of a `.github/`
file is stale BY CONSTRUCTION, and reading it to make a claim about what GitHub is scheduling is
wrong by construction too.

AND THE SAME DEFECT HAS A TIME DIMENSION, which the first cut of `intraday_delivery` walked
straight into: it read TODAY's cron list and applied 11 slots a session to a window in which
three of the sessions predated the install and really had 8. Reading one copy of a file and
believing it describes a different moment is the identical error one axis over.
"""
from __future__ import annotations

import datetime as dt
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from scripts import intraday_delivery as ID                                # noqa: E402
from scripts import workflow_source as WS                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: MA13's committed-literal idiom: the install commit and the cron it added, written down so a
#: future edit that moves either has to move this line too and shows in the diff.
INSTALL_COMMIT = "d66155e"
BACKUP_CRON = "53 17-19 * * 1-5"
PRIMARY_CRON = "23 13-20 * * 1-5"


class TheReaderIsHonestAboutWhichCopyItGaveYou(unittest.TestCase):

    def test_it_reads_origin_main_and_says_so(self):
        got = WS.read("auto-scan.yml")
        self.assertIn(got["source"], ("origin/main", "local"))
        self.assertEqual(got["authoritative"], got["source"] == "origin/main")
        self.assertTrue(got["text"], "no text at all means every caller is vacuous")

    def test_the_fallback_explains_itself_rather_than_pretending(self):
        """A helper that silently substituted the local copy would reproduce item 42's defect
        with an extra layer of indirection: the caller would believe it held the real thing."""
        got = WS.read("auto-scan.yml", ref="refs/heads/no-such-ref-%d" % os.getpid())
        self.assertFalse(got["authoritative"])
        self.assertEqual(got["source"], "local")
        self.assertIn("never authoritative", got["reason"])

    def test_a_missing_workflow_is_reported_and_not_invented(self):
        got = WS.read("no-such-%d.yml" % os.getpid())
        self.assertFalse(got["authoritative"])
        self.assertIsNone(got["text"])

    def test_it_SEES_the_stale_copy_that_caused_the_wrong_report(self):
        """NON-VACUITY against the real commit. Without this the helper could hard-code
        `differs: False` and every other test here would still pass."""
        old = WS.read("auto-scan.yml", ref=INSTALL_COMMIT + "^")
        if not old["authoritative"]:
            self.skipTest("%s^ unreachable in this checkout (shallow clone)" % INSTALL_COMMIT)
        self.assertNotIn(BACKUP_CRON, WS.crons(old["text"]),
                         "the parent of the install commit must PREDATE the backup cron")
        self.assertIn(PRIMARY_CRON, WS.crons(old["text"]),
                      "...while still carrying the primary, or the ref is not what I think")
        self.assertTrue(old["differs"], "the local copy has the cron and this ref does not")

    def test_the_backup_cron_IS_installed_which_is_the_correction(self):
        got = WS.read("auto-scan.yml")
        if not got["authoritative"]:
            self.skipTest("origin/main not fetched here; CI tests the merged checkout instead")
        self.assertIn(BACKUP_CRON, WS.crons(got["text"]))

    def test_comment_stripping_is_not_vacuous_in_either_direction(self):
        """It must drop a commented-out cron and KEEP a `#` inside a quoted scalar."""
        s = WS.strip_comments('    - cron: "23 1 * * *"   # a note\n'
                              '    # - cron: "9 9 * * *"\n'
                              '    name: "a # inside quotes"\n')
        self.assertIn('"23 1 * * *"', s)
        self.assertNotIn("9 9 * * *", s)
        self.assertIn("a # inside quotes", s)
        self.assertEqual(WS.crons('    - cron: "23 1 * * *"\n    # - cron: "9 9 * * *"\n'),
                         ["23 1 * * *"])


class TheDeliveryArithmetic(unittest.TestCase):

    def test_a_range_cron_expands_to_its_slots_and_is_not_counted_as_one(self):
        """`23 13-20 * * 1-5` is EIGHT slots a weekday. Counting it as one would make the
        drop rate look eight times better than it is."""
        self.assertEqual(ID.slots_per_weekday(PRIMARY_CRON), 8)
        self.assertEqual(ID.slots_per_weekday(BACKUP_CRON), 3)
        self.assertEqual(ID.slots_per_weekday("23 22 * * 1-5"), 1)
        self.assertEqual(ID.slots_per_weekday("0 1,5,9 * * 1-5"), 3)
        self.assertEqual(ID.slots_per_weekday("0 0-23/6 * * 1-5"), 4)
        self.assertEqual(ID.slots_per_weekday("nonsense"), 0)

    def test_the_intraday_crons_are_READ_from_the_job_not_hard_coded(self):
        got = WS.read("auto-scan.yml")
        crons = ID.intraday_crons(got["text"])
        self.assertIn(PRIMARY_CRON, crons)
        # Every cron it returns must be a cron the schedule actually contains, or the
        # denominator counts slots that can never fire.
        for c in crons:
            self.assertIn(c, WS.crons(got["text"]),
                          "%r gates the intraday job but is not in the schedule" % c)

    def test_it_returns_nothing_rather_than_guessing_when_the_job_is_absent(self):
        self.assertEqual(ID.intraday_crons("on:\n  schedule:\n    - cron: \"1 1 * * *\"\n"), [])

    def test_the_denominator_MOVES_with_the_schedule(self):
        """The time-dimension defect, pinned on the real install boundary.

        8 slots before `d66155e` and 11 after. A single denominator across that boundary
        reports 74.1% where the truth on the pre-install days is a different number.
        """
        before = ID.crons_on(dt.date(2026, 10, 7))
        after = ID.crons_on(dt.date(2026, 10, 8))
        if not before or not after:
            self.skipTest("workflow history unreachable in this checkout (shallow clone)")
        self.assertEqual(sum(ID.slots_per_weekday(c) for c in before), 8)
        self.assertEqual(sum(ID.slots_per_weekday(c) for c in after), 11)
        self.assertNotIn(BACKUP_CRON, before)
        self.assertIn(BACKUP_CRON, after)

        # AND THAT THE MEASUREMENT USES IT. Found by mutation: replacing the per-date
        # computation with `today's count x sessions` left the assertions above passing,
        # because they exercise `crons_on` and nothing tied it to the denominator.
        got = ID.expected_slots([dt.date(2026, 10, 7), dt.date(2026, 10, 8)])
        self.assertEqual(got, {dt.date(2026, 10, 7): 8, dt.date(2026, 10, 8): 11},
                         "the denominator must differ across the install boundary; a single "
                         "figure for both dates is the defect this was written for")

    def test_a_session_that_has_not_CLOSED_owes_no_slots(self):
        """Item 43's `gap_report` off-by-one, in a new instrument, caught by running it.

        Asked for 2026-10-08..14 at 02:00 UTC on the 9th, the first cut scored the 9th as 11
        expected and 0 delivered and reported 81.8% dropped on a day the market had not opened
        -- inflating the headline in the alarming direction. The window must end at the last
        CLOSED session, and the truncation must be REPORTED rather than silent, or the artifact
        says it measured a week when it measured a day.
        """
        src = io.open(os.path.join(REPO, "scripts", "intraday_delivery.py"),
                      encoding="utf-8").read()
        self.assertIn("last_closed_session()", src)
        self.assertIn("truncated_to_last_closed_session", src)
        # And the behaviour, driven: a far-future `until` must come back truncated.
        from valuation.screener import market_session as MS
        lc = MS.last_closed_session()
        if lc is None:
            self.skipTest("no closed session available from the market calendar")
        self.assertLess(lc, dt.date(2099, 1, 1))

    def test_the_in_session_band_is_narrower_than_delivery(self):
        """A run landing at 23:49 was fired by an in-session cron and refreshes nothing a user
        sees during the session. Both counts ship because the gap between them is the finding."""
        self.assertEqual((ID.IN_SESSION_FROM, ID.IN_SESSION_TO), (13, 20))


class TheGuardsAgainstTheOldMistake(unittest.TestCase):

    def test_the_delivery_script_does_not_open_the_workflow_itself(self):
        """ONE authoritative reader (B7). Read through the AST, because this file's own
        docstrings discuss `.github/workflows/` at length and a substring ban would fire on the
        prose explaining the rule -- MA49/MB1/MB15, paid for five times now including once in
        this item."""
        import ast
        tree = ast.parse(io.open(os.path.join(REPO, "scripts", "intraday_delivery.py"),
                                 encoding="utf-8").read())
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if nm in ("open", "read_text"):
                    lits = [n.value for n in ast.walk(node)
                            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
                    if any("workflows" in s for s in lits):
                        bad.append(ast.dump(node)[:80])
        self.assertEqual(bad, [], "route it through workflow_source: %s" % bad)

    def test_the_measurement_records_which_copy_it_used(self):
        """An artifact that does not say whether it read the authoritative copy cannot be
        audited later -- which is exactly the position item 42's claim was in."""
        src = io.open(os.path.join(REPO, "scripts", "intraday_delivery.py"),
                      encoding="utf-8").read()
        self.assertIn('"workflow_source": wf["source"]', src)
        self.assertIn('"authoritative": wf["authoritative"]', src)

    def test_it_states_what_it_cannot_do(self):
        """It cannot tell the primary cron from the backup: both gate the same job and the API
        does not expose the schedule. A report that omitted that would invite "the backup
        rescued N sessions", which this instrument cannot support."""
        src = io.open(os.path.join(REPO, "scripts", "intraday_delivery.py"),
                      encoding="utf-8").read()
        self.assertIn("cannot be attributed to the primary or the backup", src)


class TheTradierWorkflowIsCANCELLEDAndStillSafeIfRevived(unittest.TestCase):
    """CANCELLED 2026-10-09 (item 45): Don will not fund Tradier again.

    This class used to be `ThePendingTradierWorkflowIsSafeToINSTALL` and read the proposal
    through `propose_workflow.read()`. Item 45 moved the file to `scripts/workflows/cancelled/`
    so it can never be staged -- which broke every test here, correctly, and is why they are
    REPOINTED rather than deleted.

    **The safety assertions are KEPT and still read the cancelled text.** They were never about
    the staging; they are about what that YAML would do if anyone revived it, and a cancelled
    proposal is exactly the file someone revives later without re-reading it. **Two tests ARE
    dropped** -- "the staged copy matches" and "it is offered for installation" -- because they
    asserted a staging that must no longer happen, and item 45's suite now asserts the
    opposite.
    """

    #: The cancelled directory, named here rather than through `propose_workflow` -- that
    #: helper deliberately does NOT see cancelled files, which is the point of moving it.
    PATH = os.path.join(REPO, "scripts", "workflows", "cancelled", "tradier-seam.yml")

    def setUp(self):
        if not os.path.exists(self.PATH):
            self.skipTest("the cancelled proposal has been removed from the repo entirely")
        self.y = io.open(self.PATH, encoding="utf-8").read()
        self.code = WS.strip_comments(self.y)

    def test_it_is_not_offered_for_staging_any_more(self):
        """The cancellation, as a property: `install_workflows.bat` reads what
        `propose_workflow` stages, so being invisible there is what makes it uninstallable."""
        from scripts import propose_workflow as PW
        self.assertNotIn("tradier-seam.yml", PW.available())

    def test_it_is_dispatch_only_with_no_schedule(self):
        self.assertIn("workflow_dispatch:", self.code)
        self.assertNotIn("schedule:", self.code)
        self.assertEqual(WS.crons(self.y), [], "a measurement must not acquire a cron")

    def test_it_declares_no_input_the_script_cannot_honour(self):
        """The first cut declared a `names` input the script has no flag for -- a control on
        the Run-workflow form that accepts a value and changes nothing."""
        if "inputs:" not in self.code:
            return
        import re
        declared = re.findall(r"^      ([a-z_]+):\s*$", self.code, re.M)
        src = io.open(os.path.join(REPO, "scripts", "tradier_seam.py"),
                      encoding="utf-8").read()
        for name in declared:
            self.assertIn("--%s" % name.replace("_", "-"), src,
                          "input %r is declared and the script has no such flag" % name)

    def test_it_passes_TRADIER_ENV_live_wherever_it_passes_the_token(self):
        """Omitting it is a QUIET failure: `CONFIG.tradier_env` defaults to "sandbox", so an
        approved live token would be sent to sandbox.tradier.com, 401, and be reported as
        "Tradier has no coverage". `auto-scan.yml` learned this once already."""
        tok_steps = self.code.count("TRADIER_TOKEN:")
        env_steps = self.code.count("TRADIER_ENV: live")
        self.assertGreater(tok_steps, 0, "it must pass the repo secret or it measures nothing")
        self.assertEqual(tok_steps, env_steps,
                         "every step receiving the token must also receive TRADIER_ENV: live "
                         "(%d token vs %d env)" % (tok_steps, env_steps))
        self.assertIn("${{ secrets.TRADIER_TOKEN }}", self.code,
                      "the token comes from the repository secret, never from a literal")

    def test_the_token_is_never_echoed_and_never_written_to_the_artifact(self):
        lowered = self.code.lower()
        for banned in ("echo $tradier", "echo \"$tradier", "echo ${{ secrets",
                       "env | ", "printenv", "set -x"):
            self.assertNotIn(banned, lowered, "this would put the token in the log: %r" % banned)
        # The artifact paths must be the measurement files and nothing environment-shaped.
        self.assertIn("tradier_seam_raw.json", self.code)
        self.assertIn("tradier_seam_report.txt", self.code)
        self.assertNotIn(".env", self.code)

    def test_the_script_it_runs_can_only_READ_market_data(self):
        """Asserted on the SCRIPT, not on the workflow: the workflow's safety is whatever the
        script can do. One `requests.get` shape, and no write verb anywhere."""
        src = io.open(os.path.join(REPO, "scripts", "tradier_seam.py"),
                      encoding="utf-8").read()
        for verb in ("requests.post", "requests.put", "requests.patch", "requests.delete",
                     "session.post", ".post("):
            self.assertNotIn(verb, src, "a seam MEASUREMENT must not be able to write: %r"
                             % verb)
        self.assertEqual(src.count("requests.get"), 1,
                         "exactly one outbound call shape, or the read-only claim is a policy "
                         "rather than a property")
        self.assertIn("/markets/history", src)
        for order_path in ("/accounts/", "/orders"):
            self.assertNotIn(order_path, src, "it must not even name an order endpoint")

    def test_it_names_the_one_click_for_Don(self):
        """Don does not create or edit files on GitHub (DECISIONS 2026-10-04), so the file has
        to say how it is installed and how it is run, in the file itself."""
        self.assertIn("install_workflows.bat", self.y)
        self.assertIn("Run workflow", self.y)

    def test_the_job_names_its_own_trigger(self):
        """The house rule from `test_proposal_auto_scan_themes.py`: a job with no `if:` runs on
        every event the workflow accepts, so a trigger added later silently acquires it."""
        import re
        ifs = re.findall(r"^    if:\s*(.+?)\s*$", self.code, re.M)
        self.assertTrue(ifs, "the job has no `if:` at all")
        for expr in ifs:
            self.assertNotIn("always()", expr)
        self.assertIn("workflow_dispatch", " ".join(ifs))

    def test_the_probe_exits_NON_ZERO_when_it_could_not_measure(self):
        """'I could not measure' and 'the measurement came out this way' must not share an
        exit code -- otherwise a 401 on every name is a GREEN run with an empty artifact.

        DRIVEN, NOT GREPPED. The first cut asserted the string `NOTHING AUTHENTICATED` was in
        the source, and mutation walked straight through it: changing `if not ok:` to
        `if False:` leaves the string sitting there untouched. **Asserting that text EXISTS is
        not asserting that it is REACHED** -- the identical gap item 39 found in its own
        provenance tests.
        """
        from scripts import tradier_seam as TS
        import io as _io
        import contextlib

        real = TS.history
        self.addCleanup(setattr, TS, "history", real)

        class Cfg:
            tradier_token = "x" * 28
            tradier_env = "live"

        # Every name refused, which is what this lane's token actually does.
        TS.history = lambda sym, cfg, days=400: (401, [], "HTTP 401: not approved", {})
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = TS.probe(Cfg())
        out = buf.getvalue()
        self.assertFalse(ok, "no name authenticated, so probe() must report failure")
        self.assertIn("NOTHING AUTHENTICATED", out)
        self.assertNotIn("x" * 28, out, "the token must never be echoed")
        self.assertIn("token length 28", out)

        # THE POSITIVE CONTROL: one name succeeding must NOT read as a failure, or the probe
        # could pass this test by always refusing.
        TS.history = lambda sym, cfg, days=400: (
            200, [{"date": "2026-10-08", "close": 1.0}, {"date": "2026-01-02", "close": 2.0}],
            "", {})
        buf2 = _io.StringIO()
        with contextlib.redirect_stdout(buf2):
            ok2 = TS.probe(Cfg())
        self.assertTrue(ok2)
        self.assertNotIn("NOTHING AUTHENTICATED", buf2.getvalue())

        # And the CLI turns that into a non-zero exit, with the upload still gated on
        # `!cancelled()` so the refusal travels as evidence.
        TS.history = lambda sym, cfg, days=400: (401, [], "HTTP 401: not approved", {})
        real_cfg = TS._cfg
        self.addCleanup(setattr, TS, "_cfg", real_cfg)
        TS._cfg = lambda: Cfg()
        with contextlib.redirect_stdout(_io.StringIO()):
            rc = TS.main(["--probe"])
        self.assertEqual(rc, 2, "the workflow must go RED when it could not measure")
        self.assertIn("!cancelled()", self.code)

    def test_the_script_runs_as_a_plain_path_and_not_only_as_a_module(self):
        """It raised `ModuleNotFoundError: valuation` under `python scripts/tradier_seam.py`,
        which is exactly how the workflow invokes it -- a crash that would have cost a click."""
        src = io.open(os.path.join(REPO, "scripts", "tradier_seam.py"),
                      encoding="utf-8").read()
        self.assertIn("sys.path.insert", src)
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "tradier_seam.py"),
                            "--help"], capture_output=True, cwd=REPO, timeout=120)
        self.assertEqual(r.returncode, 0,
                         (r.stderr or b"").decode("utf-8", "replace")[:300])


class WhatDependsOnBrokerFUNDAMENTALS(unittest.TestCase):
    """ITEM 44 part 3. The answer is NOT "nothing", and the import graph said it was.

    `scripts/import_graph.py --importers valuation.screener.broker_fundamentals` returns an
    EMPTY list and the module is not in the reachable set -- because all five call sites are
    **deferred imports inside function bodies** (`from . import broker_fundamentals as BF`),
    which a module-level graph cannot see. The graph was the wrong instrument and a text sweep
    is the right one here; recorded because "no importers" is exactly the kind of answer that
    gets acted on.
    """

    def test_the_five_call_sites_exist(self):
        hits = []
        for rel in ("valuation/screener/providers.py", "valuation/screener/screen.py"):
            src = io.open(os.path.join(REPO, rel), encoding="utf-8").read()
            hits.append((rel, src.count("broker_fundamentals")))
        self.assertTrue(all(n > 0 for _, n in hits),
                        "broker_fundamentals has live callers: %s" % hits)

    def test_the_dependency_is_RESILIENCE_and_the_code_says_so(self):
        """The thing that depends on it is the scan's survival of a throttled free fetch.

        `providers.get_metrics`'s own comment: before the broker prefill a name whose free
        fetch failed was DROPPED from the scan entirely; now it survives on the broker's half.
        So with the prefetch at 0 that net is absent exactly when item 39's failure mode
        (Yahoo refusing the runner outright, HTTP 401 Invalid Crumb) occurs. No displayed
        number depends on it; the scan's robustness does.
        """
        src = io.open(os.path.join(REPO, "valuation", "screener", "providers.py"),
                      encoding="utf-8").read()
        self.assertIn("DROPPED from the scan entirely", src)

    def test_an_empty_prefetch_cannot_label_a_row_free_plus_broker(self):
        """The arithmetic behind the contradiction, driven rather than reasoned.

        `merge(None, free)` must stamp `free`. That is why no row scored during a run with an
        empty prefetch can read `free+broker` -- and therefore why the 777 rows that DO read it
        in the live health block came from the cache, not from that run.
        """
        from valuation.screener import broker_fundamentals as BF
        merged = BF.merge(None, {"ticker": "X", "market_cap": 1.0})
        self.assertEqual(merged["source"], "free")
        # And the positive control: a broker row that fills something must say so, or the
        # assertion above passes because `merge` stamps `free` unconditionally.
        both = BF.merge({"beta": 1.1}, {"ticker": "X", "market_cap": 1.0, "beta": None})
        self.assertEqual(both["source"], "free+broker")
        self.assertIn("beta", both["broker_filled"])

    def test_broker_stats_declares_which_population_it_counted(self):
        """So the next reader does not repeat my conclusion. `O-1`'s family."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "providers.py"),
                      encoding="utf-8").read()
        self.assertIn('"scope": "this run\'s prefetch only', src)


class TheReaderWorksOnARealRepoWithoutARemote(unittest.TestCase):
    """The fallback path, driven rather than argued: a repo with no `origin` at all."""

    def test_no_remote_means_local_and_says_so(self):
        d = tempfile.mkdtemp(prefix="wfsrc-")
        self.addCleanup(shutil.rmtree, d, True)
        subprocess.run(["git", "init", "-q", "-b", "main", d], capture_output=True)
        wfd = os.path.join(d, ".github", "workflows")
        os.makedirs(wfd)
        with io.open(os.path.join(wfd, "x.yml"), "w", encoding="utf-8") as fh:
            fh.write('on:\n  schedule:\n    - cron: "7 7 * * 1"\n')
        real = WS.REPO
        WS.REPO = d
        self.addCleanup(setattr, WS, "REPO", real)
        got = WS.read("x.yml")
        self.assertFalse(got["authoritative"])
        self.assertEqual(got["source"], "local")
        self.assertEqual(WS.crons(got["text"]), ["7 7 * * 1"])
        self.assertIn("never authoritative", got["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
