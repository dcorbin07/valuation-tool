# -*- coding: utf-8 -*-
"""ITEM 43 - the daily push flow, driven against REAL temporary repos with a fake remote.

WHY THIS IS NOT A UNIT TEST WITH MOCKS. The defect was an ORDER-OF-OPERATIONS failure between
three commands that each behaved correctly, and the state that made it bite -- "my uncommitted
edit touches a tracked file the remote also changed" -- is a property of git's index, not of
anything a stub could stand in for. A mocked `git` would have reproduced whatever I believed
about git and nothing about git. My own reproduction script proved that in the other direction:
its first cut dirtied only UNTRACKED files, which do not block `merge --ff-only`, so the whole
scenario quietly did not happen and the script printed success anyway.

Every case here builds a bare `github.git`, clones Don's folder from it, clones a SEPARATE lane
checkout, lands a commit from the lane, and only then dirties the folder.

THREE DEFECTS THIS SUITE FOUND ON ITS FIRST RUN, two of them in itself:

  * **IN THE PRODUCT:** `_blocked` stripped its prefix with `lstrip("./")`, which takes a SET
    OF CHARACTERS rather than a prefix, so `.env` came back as `env` and the one guard between
    a secret and a public remote matched nothing.
  * **IN THE FIXTURE:** `DECISIONS.md` had three lines, so the lane's append and Don's edit
    landed on the SAME line and every supposedly-clean replay case conflicted. The suite was
    measuring one scenario twice under two names.
  * **IN THE CONTROL:** the old-order test merged without fetching first, so `origin/main` was
    still an ancestor, the merge exited 0 saying "Already up to date", and the assertion read
    that SUCCESS as the refusal it was looking for. It passed while proving nothing.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from scripts import publish_folder as pf                                      # noqa: E402
from tests.source_bounds import code_only, function_source                    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEAD_MARK = "DON EDITS HERE"
TAIL_MARK = "LANE APPENDS HERE"


def git(repo, *args, check=True):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), (r.stderr or "")[:300]))
    return r


def write(repo, name, text):
    path = os.path.join(repo, name)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def read(repo, name):
    with open(os.path.join(repo, name)) as fh:
        return fh.read()


class Scene(object):
    """A bare remote, Don's folder, and a lane checkout that can land."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="item43-")
        self.remote = os.path.join(self.root, "github.git")
        git(self.root, "init", "--bare", "-b", "main", "github.git")

        self.don = os.path.join(self.root, "folder")
        git(self.root, "clone", "-q", self.remote, "folder")
        self._identify(self.don, "Don")
        write(self.don, "README.md", "start\n")
        # A BODY WITH ROOM IN IT, so the lane's change and Don's can land in DIFFERENT places.
        # The real DECISIONS.md is hundreds of lines and that is exactly what happened on
        # 2026-10-08; a three-line fixture cannot represent it and collapses every clean case
        # into a conflict.
        write(self.don, "DECISIONS.md",
              "# rulings\n\n%s\n%sEND\n" % (HEAD_MARK,
                                            "".join("- ruling %d\n" % i for i in range(1, 9))
                                            + TAIL_MARK + "\n"))
        git(self.don, "add", "-A")
        git(self.don, "commit", "-q", "-m", "initial")
        git(self.don, "push", "-q", "origin", "main")

        self.lane = os.path.join(self.root, "lane")
        git(self.root, "clone", "-q", self.remote, "lane")
        self._identify(self.lane, "Lane")

    @staticmethod
    def _identify(repo, who):
        git(repo, "config", "user.email", "%s@example.com" % who.lower())
        git(repo, "config", "user.name", who)
        git(repo, "config", "commit.gpgsign", "false")

    @staticmethod
    def _rewrite(repo, head=None, tail=None):
        """Replace the head marker line and/or append under the tail marker."""
        with open(os.path.join(repo, "DECISIONS.md")) as fh:
            lines = fh.readlines()
        out = []
        for ln in lines:
            if head is not None and ln.startswith(HEAD_MARK):
                out.append(head)
            elif tail is not None and ln.startswith(TAIL_MARK):
                out.append(TAIL_MARK + "\n" + tail)
            else:
                out.append(ln)
        with open(os.path.join(repo, "DECISIONS.md"), "w") as fh:
            fh.write("".join(out))

    def lane_lands(self, tail="- a ruling the gate landed\n", extra="LANDED.md", head=None):
        """A lane lands through the gate, touching the SAME tracked file Don edits.

        By default it appends at the tail, which is a clean replay. Pass `head` to put the
        lane's change on DON'S line instead, which produces a genuine conflict on purpose.
        """
        git(self.lane, "pull", "-q", "--ff-only", "origin", "main")
        self._rewrite(self.lane, head=head, tail=tail)
        if extra:
            write(self.lane, extra, "a lane's work\n")
        git(self.lane, "add", "-A")
        git(self.lane, "commit", "-q", "-m", "lane landed through the gate")
        git(self.lane, "push", "-q", "origin", "main")

    def don_edits(self, head="%s\n- what Don typed locally\n" % HEAD_MARK):
        self._rewrite(self.don, head=head)
        write(self.don, "PROMPT_appfixer_x.md", "a prompt\n")

    def reject_pushes(self):
        """Make the remote refuse every push, deterministically.

        A `pre-receive` hook that exits non-zero is the only way to exercise the
        push-was-rejected branch WITHOUT racing a second clone against publish()'s own fetch,
        and a test that depends on winning a race is flaky by construction.
        """
        hooks = os.path.join(self.remote, "hooks")
        os.makedirs(hooks, exist_ok=True)
        path = os.path.join(hooks, "pre-receive")
        with open(path, "w", newline="\n") as fh:
            fh.write("#!/bin/sh\necho 'someone landed a second ago' >&2\nexit 1\n")
        os.chmod(path, 0o755)

    def state(self):
        git(self.don, "fetch", "-q", "origin")
        ahead = int(git(self.don, "rev-list", "--count", "origin/main..HEAD").stdout or 0)
        behind = int(git(self.don, "rev-list", "--count", "HEAD..origin/main").stdout or 0)
        dirty = len([l for l in git(self.don, "status", "--porcelain").stdout.splitlines()
                     if l.strip()])
        return ahead, behind, dirty

    def remote_head_subjects(self, n=4):
        out = git(self.remote, "log", "--format=%s", "-n", str(n), "main").stdout
        return [l.strip() for l in out.splitlines() if l.strip()]

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TheCaseThatBroke(unittest.TestCase):
    """Dirty tree + a lane that landed on the same tracked file. THE prompt's named case."""

    def setUp(self):
        self.s = Scene()
        self.addCleanup(self.s.close)

    def test_the_old_order_DIVERGES_and_the_push_is_rejected(self):
        """The control. Without it the fix solves a problem nobody has shown to exist.

        This replays the OLD sequence by hand -- fast-forward first (refused), commit second
        -- and asserts the exact failure measured on 2026-10-08. If git ever stops behaving
        this way, this test says so rather than the fix quietly becoming decoration.
        """
        self.s.lane_lands()
        self.s.don_edits()
        # THE FETCH IS LOAD-BEARING: without it `origin/main` is still an ancestor of HEAD, the
        # merge exits 0 saying "Already up to date", and the refusal below never happens. The
        # old flow fetched inside sync_checkout.py.
        git(self.s.don, "fetch", "-q", "origin", "main")
        rc = git(self.s.don, "merge", "--ff-only", "origin/main", check=False).returncode
        self.assertNotEqual(rc, 0, "the premise requires the fast-forward to be refused")
        # The old flow's step 2: commit anyway, on top of stale main.
        git(self.s.don, "add", "-A")
        git(self.s.don, "commit", "-q", "-m", "Update 2026-10-08")
        ahead, behind, _ = self.s.state()
        self.assertTrue(ahead > 0 and behind > 0,
                        "expected DIVERGED, got ahead %d / behind %d" % (ahead, behind))
        push = git(self.s.don, "push", "origin", "main", check=False)
        self.assertNotEqual(push.returncode, 0, "the push should be rejected")
        self.assertIn("reject", (push.stderr or "").lower())

    def test_the_new_flow_PUSHES_and_keeps_both_sides_of_the_file(self):
        self.s.lane_lands()
        self.s.don_edits()
        before = self.s.state()
        self.assertEqual((before[0], before[1]), (0, 1))
        self.assertGreaterEqual(before[2], 2, "the premise needs a dirty tree")

        rec = pf.publish(self.s.don, stamp="2026-10-08 20:00")
        self.assertIsNone(rec["failed"], rec)
        self.assertTrue(rec["pushed"])

        self.assertEqual(self.s.state(), (0, 0, 0),
                         "after publishing the folder must be exactly in step and clean")

        # BOTH the lane's commit and Don's are on the remote, Don's on top.
        subjects = self.s.remote_head_subjects()
        self.assertEqual(subjects[0], "Update 2026-10-08 20:00")
        self.assertIn("lane landed through the gate", subjects)

        # And the replay really is a replay: the file carries BOTH edits, not one of them.
        body = read(self.s.don, "DECISIONS.md")
        self.assertIn("what Don typed locally", body)
        self.assertIn("a ruling the gate landed", body)
        self.assertTrue(os.path.exists(os.path.join(self.s.don, "LANDED.md")))

    def test_the_steps_run_in_the_order_the_fix_depends_on(self):
        """COMMIT BEFORE FETCH. The order is the entire repair, so it is asserted."""
        self.s.lane_lands()
        self.s.don_edits()
        rec = pf.publish(self.s.don, stamp="s")
        names = [s["step"] for s in rec["steps"]]
        self.assertEqual(names, ["on-branch", "commit", "fetch", "rebase", "push"], names)
        self.assertLess(names.index("commit"), names.index("fetch"))

    def test_nothing_is_discarded_the_pre_rebase_tip_is_a_named_ref(self):
        self.s.lane_lands()
        self.s.don_edits()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNone(rec["failed"], rec)
        self.assertTrue(rec["backup"], "a rebase must leave a backup ref behind")
        kept = git(self.s.don, "rev-parse", "--verify", rec["backup"]).stdout.strip()
        self.assertTrue(kept)
        # The backup is the tip as it was BEFORE the replay, so it must not be the new tip.
        self.assertNotEqual(kept, git(self.s.don, "rev-parse", "HEAD").stdout.strip())
        # And it holds Don's work WITHOUT the lane's, which is what makes it a recovery point.
        kept_body = git(self.s.don, "show", "%s:DECISIONS.md" % rec["backup"]).stdout
        self.assertIn("what Don typed locally", kept_body)
        self.assertNotIn("a ruling the gate landed", kept_body)


class AConflictStopsAndReports(unittest.TestCase):
    def setUp(self):
        self.s = Scene()
        self.addCleanup(self.s.close)

    def _collide(self):
        self.s.lane_lands(head="GITHUB CHANGED THIS LINE\n", tail=None, extra=None)
        self.s.don_edits(head="DON CHANGED THE SAME LINE\n")

    def test_a_real_conflict_aborts_reports_and_loses_nothing(self):
        self._collide()
        rec = pf.publish(self.s.don, stamp="s")

        self.assertIsNotNone(rec["failed"])
        self.assertFalse(rec["pushed"])
        rebase = [s for s in rec["steps"] if s["step"] == "rebase"][0]
        self.assertFalse(rebase["ok"])
        self.assertEqual(rebase["action"], "aborted")
        self.assertIn("NOTHING was lost", rec["failed"])
        self.assertTrue(any("CONFLICT" in ln for ln in rebase["detail"]), rebase["detail"])

        # Not left mid-rebase: the folder is usable, and Don's commit still exists.
        self.assertFalse(os.path.exists(os.path.join(self.s.don, ".git", "rebase-merge")))
        self.assertFalse(os.path.exists(os.path.join(self.s.don, ".git", "rebase-apply")))
        self.assertEqual(git(self.s.don, "log", "--format=%s", "-n", "1").stdout.strip(),
                         "Update s")
        self.assertIn("DON CHANGED THE SAME LINE", read(self.s.don, "DECISIONS.md"))
        # No conflict markers were left in the working file.
        self.assertNotIn("<<<<<<<", read(self.s.don, "DECISIONS.md"))
        # And the remote is untouched by a failed attempt.
        self.assertEqual(self.s.remote_head_subjects(1), ["lane landed through the gate"])

    def test_the_report_names_the_backup_branch_so_recovery_is_a_copy_paste(self):
        self._collide()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertTrue(rec["backup"])
        git(self.s.don, "rev-parse", "--verify", rec["backup"])
        printed = "\n".join(pf.render(rec))
        self.assertIn(rec["backup"], printed)
        self.assertIn("NOTHING was lost", printed)
        self.assertNotIn("GitHub is up to date", printed)


class TheOtherStates(unittest.TestCase):
    def setUp(self):
        self.s = Scene()
        self.addCleanup(self.s.close)

    def test_behind_only_fast_forwards_and_pushes_nothing(self):
        self.s.lane_lands()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNone(rec["failed"])
        actions = {s["step"]: s.get("action") for s in rec["steps"]}
        self.assertEqual(actions["fast-forward"], "fast-forwarded")
        self.assertEqual(actions["push"], "nothing-to-push")
        self.assertEqual(self.s.state(), (0, 0, 0))
        self.assertIn("a ruling the gate landed", read(self.s.don, "DECISIONS.md"))

    def test_in_step_and_clean_does_nothing_at_all(self):
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNone(rec["failed"])
        actions = {s["step"]: s.get("action") for s in rec["steps"]}
        self.assertEqual(actions["commit"], "clean")
        self.assertEqual(actions["align"], "in-step")
        self.assertEqual(actions["push"], "nothing-to-push")

    def test_ahead_only_pushes_without_a_rebase(self):
        self.s.don_edits()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNone(rec["failed"])
        self.assertTrue(rec["pushed"])
        self.assertIsNone(rec["backup"], "no rebase means no backup ref")
        self.assertNotIn("rebase", [s["step"] for s in rec["steps"]])
        self.assertEqual(self.s.remote_head_subjects(1), ["Update s"])

    def test_it_refuses_to_publish_from_another_branch_rather_than_switching(self):
        git(self.s.don, "checkout", "-q", "-b", "worktree-something")
        self.s.don_edits()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNotNone(rec["failed"])
        self.assertFalse(rec["pushed"])
        self.assertEqual(git(self.s.don, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
                         "worktree-something", "it must not move the user off their branch")
        # It also did not commit: refusing happens before anything is staged.
        self.assertGreaterEqual(self.s.state()[2], 2)

    def test_a_rejected_push_is_REPORTED_and_never_forced(self):
        """The one failure mode the replay cannot remove: someone lands in the push window."""
        self.s.don_edits()
        self.s.reject_pushes()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNotNone(rec["failed"])
        self.assertFalse(rec["pushed"])
        push = [s for s in rec["steps"] if s["step"] == "push"][0]
        self.assertFalse(push["ok"])
        self.assertIn("run this once more", rec["failed"])
        # Don's commit survives the failed push, and the remote is where it was.
        self.assertEqual(git(self.s.don, "log", "--format=%s", "-n", "1").stdout.strip(),
                         "Update s")
        self.assertEqual(self.s.remote_head_subjects(1), ["initial"])

    def test_a_refused_fast_forward_is_REPORTED_rather_than_raised(self):
        """The report path, driven directly, because the scenario below does NOT reach it.

        `_git` raises on non-zero, which would throw an exception out of the middle of Don's
        daily tool -- "it crashed" and "it stopped and told you why" are not the same product.
        The branch is defensive: the only candidate I could construct for a refused
        fast-forward turns out NOT to refuse (see the next test), so this drives the report
        path by making the merge fail, rather than claiming a reachability I cannot show.
        """
        self.s.lane_lands()
        real = pf._run

        def failing(repo, *args):
            if args[:2] == ("merge", "--ff-only"):
                return 1, "error: Your local changes to the following files would be overwritten"
            return real(repo, *args)

        pf._run = failing
        self.addCleanup(setattr, pf, "_run", real)
        rec = pf.publish(self.s.don, stamp="s")
        ff = [s for s in rec["steps"] if s["step"] == "fast-forward"][0]
        self.assertFalse(ff["ok"])
        self.assertIsNotNone(rec["failed"])
        self.assertIn("does not track", rec["failed"])
        self.assertFalse(rec["pushed"])
        self.assertNotIn("push", [s["step"] for s in rec["steps"]],
                         "it must stop, not push a branch it failed to align")

    def test_git_OVERWRITES_an_ignored_file_the_remote_starts_tracking(self):
        """MEASURED, and it is not what I assumed when I added the branch above.

        `merge --ff-only` protects TRACKED modified files. An IGNORED file sitting at a path
        the incoming commit tracks is replaced without a word -- so the fast-forward is not
        refused at all, and the local copy is gone. This is git's behaviour and `git pull`
        does the same thing; it is recorded here rather than repaired, because changing it
        would mean this tool second-guessing a plain fast-forward.
        """
        # It has to be an IGNORED file: `add -A` would otherwise commit it, so no untracked
        # path survives to collide with. 1) the ignore rule is on both sides.
        write(self.s.don, ".gitignore", "NOTES.txt\n")
        git(self.s.don, "add", "-A")
        git(self.s.don, "commit", "-q", "-m", "ignore NOTES.txt")
        git(self.s.don, "push", "-q", "origin", "main")
        # 2) Don has a local copy git will not touch or stage.
        write(self.s.don, "NOTES.txt", "Don's untracked version\n")
        self.assertFalse(git(self.s.don, "status", "--porcelain").stdout.strip(),
                         "an ignored file must leave the tree clean, or the premise is wrong")
        # 3) the lane force-adds the same path and lands it.
        git(self.s.lane, "pull", "-q", "--ff-only", "origin", "main")
        write(self.s.lane, "NOTES.txt", "the lane's version\n")
        git(self.s.lane, "add", "-f", "NOTES.txt")
        git(self.s.lane, "commit", "-q", "-m", "lane landed through the gate")
        git(self.s.lane, "push", "-q", "origin", "main")

        rec = pf.publish(self.s.don, stamp="s")
        ff = [s for s in rec["steps"] if s["step"] == "fast-forward"][0]
        self.assertTrue(ff["ok"], "measured: git does NOT refuse this, it overwrites")
        self.assertIsNone(rec["failed"])
        self.assertEqual(read(self.s.don, "NOTES.txt"), "the lane's version\n",
                         "git replaced the ignored local file -- recorded, not repaired")

    def test_an_unreachable_remote_is_an_error_and_not_a_pass(self):
        """'I could not tell' and 'all clear' must never share an exit code."""
        self.s.don_edits()
        git(self.s.don, "remote", "set-url", "origin",
            os.path.join(self.s.root, "no-such-remote.git"))
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNotNone(rec["failed"])
        self.assertFalse(rec["pushed"])
        self.assertIn("could not read GitHub", rec["failed"])
        # The commit still happened, which is the point of committing first: the edits are
        # saved even when GitHub is unreachable.
        self.assertEqual(git(self.s.don, "log", "--format=%s", "-n", "1").stdout.strip(),
                         "Update s")


class TheGuaranteesAreCode(unittest.TestCase):
    def setUp(self):
        self.s = Scene()
        self.addCleanup(self.s.close)

    def test_env_is_refused_and_left_uncommitted(self):
        write(self.s.don, ".env", "ADMIN_TOKEN=secret\n")
        write(self.s.don, "README.md", "edited\n")
        # Forced into the index the way a stale entry or a `git add -f` would.
        git(self.s.don, "add", "-f", ".env")
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNotNone(rec["failed"])
        self.assertIn(".env", rec["failed"])
        self.assertFalse(rec["pushed"])
        # Nothing was committed, and nothing reached the remote.
        self.assertNotIn("Update s", git(self.s.don, "log", "--format=%s").stdout)
        self.assertEqual(self.s.remote_head_subjects(1), ["initial"])
        # And it is no longer staged, so a later honest run is not poisoned.
        self.assertNotIn(".env", git(self.s.don, "diff", "--cached", "--name-only").stdout)

    def test_data_is_refused_too(self):
        write(self.s.don, os.path.join("data", "valquo_track.json"), "{}\n")
        git(self.s.don, "add", "-f", "data/valquo_track.json")
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNotNone(rec["failed"])
        self.assertIn("data/", rec["failed"])
        self.assertEqual(self.s.remote_head_subjects(1), ["initial"])

    def test_blocked_classifies_the_real_shapes_and_nothing_else(self):
        """MA13: a committed literal, so a widened rule shows in the diff."""
        self.assertEqual(pf._blocked([".env"]), [".env"])
        self.assertEqual(pf._blocked(["./.env"]), ["./.env"])
        self.assertEqual(pf._blocked([".env.local"]), [".env.local"])
        self.assertEqual(pf._blocked(["data/valquo_track.json"]), ["data/valquo_track.json"])
        self.assertEqual(pf._blocked(["data\\valquo_track.json"]),
                         ["data\\valquo_track.json"])
        for safe in ("DECISIONS.md", "scripts/publish_folder.py", "data_export/track.csv",
                     "valuation/web/app.py", "tests/test_item43_publish_folder.py",
                     ".environment.md", "database.py"):
            self.assertEqual(pf._blocked([safe]), [], safe)

    def test_no_worktree_branch_is_ever_touched(self):
        """'Agent branches are never merged locally' -- as a property of the source."""
        src = code_only(function_source(os.path.join(REPO, "scripts", "publish_folder.py"),
                                        "publish"), keep_strings=True)
        # `code_only` joins TOKENS with a space, so every needle here is a single token.
        # THIS IS THE REPAIR OF A REAL GAP AND IT WAS THE MOST DANGEROUS MUTATION OF THE SET:
        # the list used to read "push --force", a needle with a space in it, which the
        # tokenised source can never contain -- so turning the push into a FORCE PUSH TO MAIN
        # went straight through. `MB15`'s family: a ban whose shape cannot match what it bans.
        #
        # AND `"clean"` HAD TO COME OFF THIS LIST, which is the same family one level down:
        # `action="clean"` is a legitimate STEP LABEL, so banning the token fired against
        # correct code. Only tokens that are dangerous in every context stay.
        for banned in ('"worktree-"', '"--force"', '"--force-with-lease"', '"-d"', '"-D"',
                       '"--hard"', '"--no-ff"', '"-fd"', '"-x"', '"stash"', '"checkout"',
                       '"+refs/"'):
            self.assertNotIn(banned, src, "publish() must not reach for %s" % banned)
        # And the push's shape EXACTLY, so any extra argument at all breaks it -- a positive
        # assertion catches what an enumeration of bans cannot anticipate.
        self.assertIn('_run ( repo , "push" , remote , "HEAD:%s" % branch )', src)
        # The only merge it performs is a fast-forward of its own branch.
        self.assertIn('"merge" , "--ff-only"', src)
        # `-f` is NOT banned, deliberately: `branch -f` force-moves the local BACKUP ref, which
        # is the line that makes "nothing is discarded" true. Banning the bare token would fire
        # against correct code -- so the push is pinned positively instead.
        self.assertIn('"branch" , "-f" , backup , "HEAD"', src)

    def test_a_landed_agent_branch_is_left_alone_by_a_publish(self):
        """The 2026-10-06 shape: a branch the gate already landed must not block Don."""
        git(self.s.don, "branch", "worktree-item43")
        self.s.lane_lands()
        self.s.don_edits()
        rec = pf.publish(self.s.don, stamp="s")
        self.assertIsNone(rec["failed"], rec)
        self.assertTrue(rec["pushed"])
        self.assertTrue(git(self.s.don, "rev-parse", "--verify",
                            "worktree-item43").stdout.strip(), "the branch must still exist")
        self.assertEqual(self.s.remote_head_subjects(1), ["Update s"])

    def test_the_cli_refuses_to_push_without_tests_passed(self):
        self.s.don_edits()
        self.assertEqual(pf.main(["--repo", self.s.don, "--stamp", "s"]), pf.FAILED)
        self.assertNotIn("Update s", git(self.s.don, "log", "--format=%s").stdout)
        self.assertEqual(self.s.remote_head_subjects(1), ["initial"])

    def test_the_cli_pushes_with_tests_passed_and_exits_zero(self):
        self.s.don_edits()
        self.assertEqual(pf.main(["--repo", self.s.don, "--stamp", "s", "--tests-passed"]),
                         pf.OK)
        self.assertEqual(self.s.remote_head_subjects(1), ["Update s"])

    def test_the_cli_exits_non_zero_on_a_conflict(self):
        self.s.lane_lands(head="GITHUB LINE\n", tail=None, extra=None)
        self.s.don_edits(head="DON LINE\n")
        self.assertEqual(pf.main(["--repo", self.s.don, "--stamp", "s", "--tests-passed"]),
                         pf.FAILED, "a conflict must not report success")

    def test_dry_run_changes_nothing_but_still_names_the_step_it_would_take(self):
        self.s.lane_lands()
        self.s.don_edits()
        before = (git(self.s.don, "rev-parse", "HEAD").stdout.strip(),
                  git(self.s.don, "status", "--porcelain").stdout)
        rec = pf.publish(self.s.don, dry=True, stamp="s")
        self.assertIsNone(rec["failed"])
        after = (git(self.s.don, "rev-parse", "HEAD").stdout.strip(),
                 git(self.s.don, "status", "--porcelain").stdout)
        self.assertEqual(before, after, "a dry run must not commit or touch the tree")
        self.assertEqual(self.s.remote_head_subjects(1), ["lane landed through the gate"])
        # A PREVIEW THAT PREVIEWS NOTHING IS WORSE THAN NONE: the first cut skipped the fetch,
        # read a stale ref and reported "in step" on exactly the state this item is about.
        self.assertEqual([s.get("action") for s in rec["steps"] if s["step"] == "rebase"],
                         ["would-rebase"])


class TheCallerIsWiredToIt(unittest.TestCase):
    """git_push.bat is the only caller Don runs, so the wiring is part of the fix."""

    @staticmethod
    def _bat():
        with open(os.path.join(REPO, "git_push.bat")) as fh:
            return fh.read()

    def test_git_push_calls_publish_folder_with_tests_passed(self):
        bat = self._bat()
        self.assertIn("scripts\\publish_folder.py", bat)
        self.assertIn("--tests-passed", bat)

    def test_git_push_still_runs_the_tests_BEFORE_it_publishes(self):
        bat = self._bat()
        self.assertLess(bat.index("test_edge.py"), bat.index("publish_folder.py"),
                        "never push red: the suite runs first")
        self.assertIn("refusing to push", bat)

    def test_git_push_no_longer_commits_or_pushes_by_itself(self):
        """ONE definition of the order (B7). Two orders in two files is how this recurs."""
        lines = [l.strip() for l in self._bat().splitlines()
                 if l.strip() and not l.strip().lower().startswith("rem")
                 and not l.strip().lower().startswith("echo")]
        body = "\n".join(lines)
        for owned_by_publish in ('"%GIT%" add -A', '"%GIT%" commit', '"%GIT%" push',
                                 "sync_checkout.py"):
            self.assertNotIn(owned_by_publish, body,
                             "%r belongs to publish_folder.py now" % owned_by_publish)

    def test_git_push_still_says_agent_branches_are_not_merged_here(self):
        self.assertIn("Agent branches land through the GitHub gate", self._bat())

    def test_no_tab_character_survives_in_the_bat(self):
        """A tab ate `tests\\test_edge.py` once -- `\\t` in a heredoc. cmd would have run
        `python tests` and the test gate would have been silently absent."""
        self.assertNotIn("\t", self._bat())

    def test_rebase_push_bat_is_NOT_committed(self):
        """The decision, pinned. Its cure is step 4 of the normal flow now, and a second copy
        of one cure is audit B7's shape -- the second copy is the one that drifts."""
        self.assertFalse(os.path.exists(os.path.join(REPO, "rebase_push.bat")),
                         "rebase_push.bat was removed deliberately, not forgotten")


class TheReportIsLegible(unittest.TestCase):
    def test_every_step_renders_a_plain_english_label(self):
        rec = {"steps": [{"step": s, "ok": True} for s in
                         ("on-branch", "commit", "fetch", "fast-forward", "rebase", "align",
                          "push")],
               "pushed": True, "failed": None, "backup": None}
        printed = "\n".join(pf.render(rec))
        for s in rec["steps"]:
            self.assertNotIn("  [OK ] %s " % s["step"], printed,
                             "step %r rendered its raw key, so it has no label" % s["step"])
        self.assertIn("GitHub is up to date", printed)

    def test_a_failure_renders_the_warning_and_not_a_success_line(self):
        rec = {"steps": [{"step": "rebase", "ok": False, "action": "aborted"}],
               "pushed": False, "failed": "it stopped", "backup": "backup/main-abc1234"}
        printed = "\n".join(pf.render(rec))
        self.assertIn("[!!", printed)
        self.assertIn("it stopped", printed)
        self.assertIn("backup/main-abc1234", printed)
        self.assertNotIn("GitHub is up to date", printed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
