# -*- coding: utf-8 -*-
"""ITEM 85 — a workflow install from a stale lane folder rolled two live workflows back ten days.

Commit `ad29600` (2026-10-27 12:05Z) put 10-16/10-17 copies of `fleet-cycle.yml` and
`live-cycle.yml` on main: **338 lines deleted**, including every item-74 healthchecks ping and
every "tell Don this failed" Discord step from both files, plus item 65's per-field summary, the
cycle-body artifact and the fractional census from `live-cycle.yml`. The source was
`.claude\\worktrees\\dipcall\\pending_workflows\\`, because the old `install_workflows.bat`
copied from the folder the bat sat in and a copy of that bat sits in every worktree.

**THE COUNTERFACTUAL IS THE TEST THAT MATTERS HERE**, and it is the second class below: the new
age rule is run against `ad29600` itself and must refuse it. A guard is worth nothing until it is
shown to bite on the event it was written for, and this one went through two formulations that
did not:

  * comparing the two PATHS' last-touching commits refuses the REPAIR, because the defective
    file is the newer one (`.github` 10-27 by the bad install, `pending` 10-20);
  * "refuse unless the installed content never came from the pending path" was measured and
    REFUTED — the lane folder held genuine older versions of the tracked files, so the bad
    content is in that path's history too.

What discriminates is position within the pending path's own lineage, and that is what is pinned.

**WHAT THE SUPERSET TEST CAN AND CANNOT BE, stated because the brief asks for the stronger
version and it is not simultaneously satisfiable.** A test that fails whenever an installed
workflow lacks a step its pending copy carries is RED ON MAIN RIGHT NOW — that is the regression.
A red test cannot land, and landing it red would break every other lane's gate, so the check
below treats "an install is awaited, and the installer's own plan says it moves FORWARD" as the
one legitimate reason for a missing step, and fails otherwise. That allowance is DERIVED from the
installer rather than a typed list of today's three files, so it clears itself the moment Don
installs and needs no follow-up commit. The cost is stated plainly: while a file is legitimately
awaiting install, this test cannot tell a pending improvement from a rollback. The thing that
stops a rollback is the age rule in the class above, which refuses it at the door.

PyYAML is not in CI (`test_item74.wf_jobs` carries that lesson), so the workflows are parsed as
text through that module's own helpers rather than a second parser written here.
"""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401  (must precede the valuation imports)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import install_workflows as IW
from test_item74 import _read_wf, wf_jobs

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The install that caused this item. Both of its files must be REFUSED by the new rule.
BAD_INSTALL = "ad29600"

#: The three files the repair installs, and what each must carry once it lands. Committed
#: literals (`MA13`), so a future edit that drops one of these steps from the handover goes red
#: here rather than silently shipping a workflow with no way to report its own failure.
ITEM74_STEPS = ("hc-ping.com", "tell Don this failed")
LIVE_ONLY_STEPS = ("live-cycle-body", "fractional-census")


def _git():
    return IW.Git(REPO)


def _ref(git):
    """A ref whose `.github` and `pending_workflows` are the committed ones.

    `origin/main` locally; the land gate checks out `main` itself at `fetch-depth: 0`. Resolved
    rather than assumed, and the caller asserts it resolved — a test that silently falls back to
    the working tree would pass while measuring uncommitted edits.
    """
    for cand in ("origin/main", "main", "HEAD"):
        if git("rev-parse", "--verify", "-q", cand + "^{commit}"):
            return cand
    return None


def step_names(src):
    """Every step name in a workflow, across all jobs."""
    out = set()
    for steps in wf_jobs(src).values():
        for name, _if in steps:
            out.add(name)
    return out


def missing_step_report(git, ref, plan_rows):
    """`[(file, missing steps, direction)]` for every pending workflow missing steps when installed.

    `plan_rows` is the installer's own verdict per file, so the allowance below cannot drift from
    what the installer would actually do.
    """
    by_name = {r["name"]: r for r in plan_rows}
    out = []
    for name, row in sorted(by_name.items()):
        pend = git.bytes_at(ref, "%s/%s" % (IW.PENDING_DIR, name))
        inst = git.bytes_at(ref, "%s/%s" % (IW.TARGET_DIR, name))
        if pend is None or inst is None:
            continue
        want = step_names(pend.decode("utf-8", "replace").replace("\r\n", "\n"))
        have = step_names(inst.decode("utf-8", "replace").replace("\r\n", "\n"))
        gone = want - have
        if gone:
            out.append((name, sorted(gone), row["direction"]))
    return out


# =============================================================================================
class TheInstallerTakesItsSourceFromMain(unittest.TestCase):
    """The one change that makes the accident impossible: the source is not where the bat sits."""

    def test_the_plan_reads_both_sides_from_git_and_not_from_disk(self):
        """The line-ending defect, found by running it rather than reading it.

        Read from disk the pending copy carries CRLF after a Windows checkout while its blob
        holds LF, so a disk-against-blob comparison reported SIX files `CHANGED` that were
        byte-identical in the repository. The installer's report has to be right about what it is
        about to do, which is the whole subject of this item one level down.
        """
        git = _git()
        ref = _ref(git)
        self.assertIsNotNone(ref, "no committed ref resolved")
        rows = IW.plan(git, REPO, ref=ref)
        self.assertTrue(rows, "plan found no pending workflows at all")
        for r in rows:
            if r["state"] == "unchanged":
                self.assertEqual(r["direction"], "no-op",
                                 "%s is byte-identical and yet not a no-op" % r["name"])
            if r["direction"] == "no-op" and r["state"] == "CHANGED":
                self.fail("%s reads CHANGED and no-op at once, which is the CRLF defect"
                          % r["name"])

    def test_the_bat_holds_no_copy_of_the_rule(self):
        """Two implementations of a rule is how the rule rots (`B7`). The bat must only call."""
        bat = _read_wf(os.path.join(REPO, "install_workflows.bat"))
        self.assertIn("scripts.install_workflows", bat)
        low = bat.lower()
        for banned in ("copy /y", "git commit", "git push", "worktree add"):
            self.assertNotIn(banned, low,
                             "the bat still does the install itself: %r" % banned)

    def test_the_legacy_gitignored_folder_is_not_a_source(self):
        """It may be REPORTED as ignored, and never read for content."""
        src = _read_wf(os.path.join(REPO, "scripts", "install_workflows.py"))
        # The only use of LEGACY_DIR is the leftovers report.
        self.assertIn("def legacy_leftovers", src)
        body = src[src.index("def plan("):src.index("def legacy_leftovers")]
        self.assertNotIn("LEGACY_DIR", body,
                         "plan() reads the gitignored folder, which is how this happened")

    def test_the_legacy_route_needs_every_file_named(self):
        """The brief's second option, and it had to be taken rather than deleting the route:
        `scripts/propose_workflow.py` stages into exactly that directory, so removing it would
        break a working mechanism -- and the accident came from the TRACKED name read out of a
        worktree, not from here.

        Every file must be named, not a subset. Confirming two of three and having the third go
        in anyway is this item's own surprise in miniature; confirming two and having the third
        silently skipped is the other half of it.
        """
        self.assertFalse(IW.legacy_confirmed(["a.yml", "b.yml"], [])[0])
        self.assertFalse(IW.legacy_confirmed(["a.yml", "b.yml"], ["a.yml"])[0])
        self.assertFalse(IW.legacy_confirmed(["a.yml"], ["a.yml", "c.yml"])[0])
        ok, why = IW.legacy_confirmed(["a.yml", "b.yml"], ["b.yml", "a.yml"])
        self.assertTrue(ok)
        self.assertIn("a.yml", why)

    def test_an_unnamed_legacy_file_is_reported_rather_than_skipped(self):
        """Silently skipping it is how someone concludes the install worked while their file
        went nowhere -- `C5`, absent is not the same as measured zero."""
        src = _read_wf(os.path.join(REPO, "scripts", "install_workflows.py"))
        self.assertIn("are IGNORED", src)
        self.assertIn("--legacy-confirm", src)

    def test_it_refuses_to_run_from_a_lane_worktree(self):
        bad = os.path.join("C:\\", "x", ".claude", "worktrees", "dipcall")
        why = IW.refuse_reason(bad)
        self.assertIsNotNone(why, "a worktree path was accepted")
        self.assertIn("worktree", why)

    def test_it_does_not_refuse_an_ordinary_folder(self):
        """The positive control: a guard that refuses everything also refuses the repair."""
        self.assertIsNone(IW.refuse_reason(os.path.join("C:\\", "Users", "d", "valuation-tool")))

    def test_the_worktree_refusal_is_not_fooled_by_slashes_or_case(self):
        for p in (r"C:/Users/d/.CLAUDE/Worktrees/x", r"C:\Users\d\.claude\worktrees\x\\"):
            self.assertIsNotNone(IW.refuse_reason(p), p)


# =============================================================================================
class TheAgeRuleRefusesTheInstallThatCausedThis(unittest.TestCase):
    """Run the new rule against `ad29600` itself. If it does not refuse it, it is decoration."""

    def _lineage(self, git, name):
        return IW.pending_lineage(git, name, ref=_ref(git))

    def test_the_bad_install_is_refused_on_both_files(self):
        git = _git()
        self.assertIsNotNone(git("rev-parse", "--verify", "-q", BAD_INSTALL + "^{commit}"),
                             "%s is not in this clone, so the counterfactual cannot run"
                             % BAD_INSTALL)
        for name in ("fleet-cycle.yml", "live-cycle.yml"):
            lin = self._lineage(git, name)
            self.assertTrue(lin, "no lineage for %s" % name)
            before = git.blob(BAD_INSTALL + "^", "%s/%s" % (IW.TARGET_DIR, name))
            after = git.blob(BAD_INSTALL, "%s/%s" % (IW.TARGET_DIR, name))
            self.assertIsNotNone(before, name)
            self.assertIsNotNone(after, name)
            self.assertEqual(IW.direction(lin, after, before), "BACKWARD",
                             "%s: the rule would have allowed the install that broke it" % name)

    def test_todays_repair_is_allowed_so_one_run_fixes_all_three(self):
        """The other half of the same guard, and the brief's own requirement."""
        git = _git()
        rows = {r["name"]: r for r in IW.plan(git, REPO, ref=_ref(git))}
        for name in ("fleet-cycle.yml", "live-cycle.yml", "auto-scan.yml"):
            self.assertIn(name, rows)
            self.assertTrue(rows[name]["ok"],
                            "%s would be refused, so the repair needs more than one run: %s"
                            % (name, rows[name]["note"]))

    def test_the_four_verdicts_on_a_made_up_lineage(self):
        lin = {"new": (0, "c3 later"), "mid": (1, "c2"), "old": (2, "c1 earlier")}
        self.assertEqual(IW.direction(lin, "new", "old"), "FORWARD")
        self.assertEqual(IW.direction(lin, "old", "new"), "BACKWARD")
        self.assertEqual(IW.direction(lin, "mid", "mid"), "no-op")
        self.assertEqual(IW.direction(lin, "new", None), "FORWARD")
        self.assertEqual(IW.direction(lin, "new", "elsewhere"), "UNKNOWN")

    def test_an_unreviewed_github_edit_is_refused_rather_than_overwritten(self):
        """UNKNOWN means something other than this handover wrote `.github`. Stop and say so."""
        lin = {"p": (0, "c2")}
        self.assertEqual(IW.direction(lin, "p", "hand-edited"), "UNKNOWN")

    def test_classify_names_the_three_states(self):
        self.assertEqual(IW.classify(b"a", None), "NEW")
        self.assertEqual(IW.classify(b"a", b"a"), "unchanged")
        self.assertEqual(IW.classify(b"a", b"b"), "CHANGED")


# =============================================================================================
class TheHandoverStillCarriesEveryStepItem74Added(unittest.TestCase):
    """What the repair puts back, asserted on the files that will be installed."""

    def _pending(self, name):
        return _read_wf(os.path.join(REPO, IW.PENDING_DIR, name))

    def test_both_cycles_can_report_their_own_failure(self):
        for name in ("fleet-cycle.yml", "live-cycle.yml"):
            src = self._pending(name)
            for needle in ITEM74_STEPS:
                self.assertIn(needle, src,
                              "%s has lost item 74's %r" % (name, needle))

    def test_the_failure_notifier_only_fires_on_failure(self):
        """A notifier that posts on every run is noise, and noise gets muted (`MA21`)."""
        for name in ("fleet-cycle.yml", "live-cycle.yml"):
            jobs = wf_jobs(self._pending(name))
            self.assertTrue(jobs, "%s parsed to no jobs" % name)
            found = [(s, g) for steps in jobs.values() for (s, g) in steps
                     if "tell Don this failed" in s]
            self.assertTrue(found, "%s has no failure notifier" % name)
            for step, guard in found:
                self.assertIn("failure()", guard,
                              "%s: %r is not guarded on failure: %r" % (name, step, guard))

    def test_the_live_cycle_keeps_item_65s_evidence(self):
        src = self._pending("live-cycle.yml")
        for needle in LIVE_ONLY_STEPS:
            self.assertIn(needle, src, "live-cycle.yml has lost %r" % needle)

    def test_the_send_token_is_still_paper(self):
        """The percentage stays 0 and the token stays paper. No lane moves either.

        **READ THE URL, NOT THE FILE.** My first cut banned the substring `run=1` and FAILED
        AGAINST THE CORRECT FILE, because `live-cycle.yml`'s own comments document that changing
        `run=paper` to `run=1` is the single edit that permits live sending -- prose quoting what
        the rule forbids, which is a family this project has now hit often enough to have written
        down, and I committed it with the warning in view. So the token is read out of the
        `/admin/live-cycle?run=...` URL the job actually calls.
        """
        src = self._pending("live-cycle.yml")
        tokens = set(re.findall(r"admin/live-cycle\?run=([A-Za-z0-9]+)", src))
        self.assertTrue(tokens, "no live-cycle URL found at all, so this test measured nothing")
        self.assertEqual(tokens, {"paper"},
                         "the live-cycle door is called with %s" % sorted(tokens))

    def test_the_hot_list_catchup_is_in_the_handover(self):
        """Item 84B, which the bad install also did not carry."""
        self.assertIn("hot list behind", self._pending("auto-scan.yml"))


# =============================================================================================
class TheInstalledCopyNeverSilentlyLosesAStep(unittest.TestCase):
    """The brief's regression test, in the strongest landable form. See the module docstring."""

    def test_no_installed_workflow_is_missing_a_step_without_an_install_awaiting_it(self):
        git = _git()
        ref = _ref(git)
        self.assertIsNotNone(ref)
        rows = IW.plan(git, REPO, ref=ref)
        self.assertTrue(rows, "plan found no pending workflows, so this test is vacuous")
        report = missing_step_report(git, ref, rows)
        bad = [(n, m, d) for (n, m, d) in report if d not in ("FORWARD",)]
        self.assertFalse(bad, "an installed workflow is missing steps with no forward install to "
                              "explain it: %s" % bad)

    def test_a_file_that_would_go_backwards_fails_outright(self):
        git = _git()
        rows = IW.plan(git, REPO, ref=_ref(git))
        for r in rows:
            self.assertNotIn(r["direction"], ("BACKWARD", "UNKNOWN"),
                             "%s: %s" % (r["name"], r["note"]))

    def test_the_checker_catches_a_lost_step_when_nothing_is_awaited(self):
        """The positive control. Without it this class could pass by finding nothing to look at."""
        git = _git()
        ref = _ref(git)
        fake = [{"name": "live-cycle.yml", "state": "unchanged", "direction": "no-op",
                 "note": "", "ok": True}]
        report = missing_step_report(git, ref, fake)
        self.assertTrue(report, "the checker found no missing steps on a file that has lost "
                                "every item-74 step, so it is measuring nothing")
        name, missing, direction = report[0]
        self.assertEqual(direction, "no-op")
        self.assertTrue(missing)

    def test_step_names_finds_real_steps(self):
        names = step_names(_read_wf(os.path.join(REPO, IW.PENDING_DIR, "live-cycle.yml")))
        self.assertGreater(len(names), 3, "the step parser returned almost nothing")


# =============================================================================================
class TheUpdaterPublishesNothing(unittest.TestCase):
    """Don's step 1. `sync.bat` pushes every lane branch; this must not send anything at all."""

    def setUp(self):
        self.src = _read_wf(os.path.join(REPO, "update_main.bat"))

    def test_it_never_pushes(self):
        """Banning the word fired on the comment EXPLAINING that `sync.bat` pushes -- the same
        substring-ban defect as the token test above, in the same file. Strip the prose first."""
        code = [ln for ln in self.src.split("\n")
                if not re.match(r"^\s*rem\b", ln, re.I)
                and not re.match(r"^\s*echo\b", ln, re.I)]
        self.assertTrue(code, "the prose stripper removed everything")
        self.assertIn("fetch", "\n".join(code).lower(),
                      "the stripper removed the commands too, so this test is vacuous")
        offenders = [ln.strip() for ln in code if "push" in ln.lower()]
        self.assertFalse(offenders, "update_main.bat sends something: %s" % offenders)

    def test_it_only_fetches_and_fast_forwards(self):
        self.assertIn("fetch -q origin main", self.src)
        self.assertIn("merge --ff-only origin/main", self.src)

    def test_it_stops_on_uncommitted_work_rather_than_discarding_it(self):
        self.assertIn("STOPPED", self.src)
        for banned in ("reset --hard", "checkout -- ", "clean -fd", "stash"):
            self.assertNotIn(banned, self.src,
                             "update_main.bat could destroy local work: %r" % banned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
