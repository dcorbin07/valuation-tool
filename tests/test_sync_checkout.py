#!/usr/bin/env python3
"""Tests for scripts/sync_checkout.py - the MA20 cure.

The thing being guarded is narrow and severe: this is the only tool in the project that
writes to the SHARED checkout unattended, so every test here is really asking one of two
questions - "can it lose work?" and "can it report success when it has not succeeded?".
The second is the one that created MA20 in the first place: sync.bat prints "you are
fully up to date" on a diverged branch it did nothing about.

FIXTURES. An earlier draft shared six class-level repos and four tests failed -- not on
their assertions but because unittest runs tests ALPHABETICALLY and the earlier ones had
already pushed the rescue ref or consumed the fast-forward. Sharing a fixture that any
test mutates buys speed by making the suite depend on method names. So: read-only tests
share, and every test that writes builds its own. That costs about eight extra repos and
buys independence, which is the property that matters in a suite about not losing work.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import sync_checkout as sc  # noqa: E402
from scripts.checkout_drift import DriftUnknown  # noqa: E402

PASSED = FAILED = 0


def git(repo, *args, check=True):
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} in {repo}: {p.stderr or p.stdout}")
    return p.stdout.strip()


def write(repo, rel, text):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build(base, name, *, ahead=0, behind=0, dirty=False, untracked_collision=False):
    """A bare origin plus a clone in a chosen state of drift."""
    origin = Path(base) / f"{name}-origin.git"
    work = Path(base) / f"{name}-seed"
    shared = Path(base) / f"{name}-shared"

    git(base, "init", "--bare", "-b", "main", str(origin))
    git(base, "clone", "-q", str(origin), str(work))
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        git(work, "config", k, v)
    write(work, "README.md", "seed\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "seed")
    git(work, "push", "-q", "origin", "main")

    git(base, "clone", "-q", str(origin), str(shared))
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        git(shared, "config", k, v)

    for i in range(behind):
        write(work, f"upstream_{i}.txt", f"remote {i}\n")
        if untracked_collision and i == 0:
            write(work, "COLLIDE.md", "the remote's version\n")
        if dirty and i == 0:
            # The upstream must touch the SAME file the clone dirties, or git will
            # fast-forward straight past an uncommitted edit and nothing is blocked.
            # An earlier draft missed this and the "refuses" test passed vacuously.
            write(work, "README.md", "seed\nchanged upstream too\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", f"upstream {i}")
    if behind:
        git(work, "push", "-q", "origin", "main")

    for i in range(ahead):
        write(shared, f"local_{i}.txt", f"local {i}\n")
        git(shared, "add", "-A")
        git(shared, "commit", "-q", "-m", f"stranded local {i}")
    if dirty:
        write(shared, "README.md", "seed\nlocally edited, never committed\n")
    if untracked_collision:
        write(shared, "COLLIDE.md", "MY OWN UNTRACKED VERSION\n")
    git(shared, "fetch", "-q", "origin")
    return str(shared), str(origin)


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sync_ck_")
        # Read-only across the suite: every test using these passes dry=True, or runs a
        # sync that has nothing to do.
        cls.clean, _ = build(cls.tmp, "clean")
        cls.diverged, _ = build(cls.tmp, "div", ahead=1, behind=3, dirty=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def mk(self, **kw):
        """A fixture owned by exactly one test, named after it."""
        return build(self.tmp, self.id().rsplit(".", 1)[-1][5:33], **kw)[0]

    def go(self, repo, **kw):
        kw.setdefault("fetch", False)
        return sc.run(repo, **kw)

    # ------------------------------------------------------------ the false all-clear
    def test_a_diverged_checkout_never_reports_success(self):
        """THE regression for MA20. sync.bat's own last line on this state is
        'everything is merged. You are fully up to date'."""
        r = self.go(self.diverged, dry=True)
        self.assertTrue(r["alarm"])
        self.assertIn("fast-forward", r["outstanding"])
        txt = "\n".join(sc.render(r)).lower()
        self.assertIn("alarm", txt)
        self.assertNotIn("up to date", txt)

    def test_a_clean_checkout_reports_success_and_exits_zero(self):
        r = self.go(self.clean)
        self.assertFalse(r["alarm"], r["phases"])
        self.assertEqual(sc.main(["--repo", self.clean, "--no-fetch"]), 0)

    def test_unknown_is_an_alarm_not_a_pass(self):
        self.assertEqual(sc.main(["--repo", str(Path(self.tmp) / "nope"), "--no-fetch"]), 1)

    # ------------------------------------------------------------ A: rescue
    def test_stranded_commits_are_pushed_to_a_rescue_ref(self):
        repo = self.mk(ahead=2)
        r = self.go(repo)
        ph = r["phases"][0]
        self.assertEqual(ph["action"], "pushed")
        self.assertTrue(ph["ref"].startswith("rescue/main-"))
        remote = git(repo, "ls-remote", "--heads", "origin", ph["ref"])
        self.assertTrue(remote, "the rescue ref is not on the remote")
        self.assertEqual(remote.split()[0], git(repo, "rev-parse", "main"))

    def test_rescuing_twice_is_a_no_op(self):
        repo = self.mk(ahead=1)
        self.go(repo)
        again = self.go(repo)["phases"][0]
        self.assertEqual(again["action"], "already-rescued")

    def test_rescue_does_not_go_to_a_branch_the_gate_would_auto_land(self):
        """`worktree-*` is auto-merged into main by the land Action. The commit actually
        stranded on Don's machine rewrites a merge=union file end to end, so landing it
        unreviewed would roughly double that file. Rescue != land; --land opts in."""
        repo = self.mk(ahead=1)
        self.assertFalse(self.go(repo)["phases"][0]["ref"].startswith("worktree-"))
        r = sc.run(repo, fetch=False, land=True, dry=True)
        self.assertTrue(r["phases"][0]["ref"].startswith("worktree-sync"))

    # ------------------------------------------------------------ B: snapshot
    def test_uncommitted_edits_are_banked_without_touching_anything_local(self):
        repo = self.mk(behind=2, dirty=True)
        # The snapshot phase ALONE - a full run() also fast-forwards, which is supposed
        # to move HEAD, and measuring across both would let a snapshot side effect hide.
        st = sc.survey(repo, "main", "origin", fetch=False)
        idx = Path(repo) / ".git" / "index"
        before = (git(repo, "rev-parse", "HEAD"), git(repo, "status", "--porcelain"),
                  (Path(repo) / "README.md").read_text(encoding="utf-8"),
                  idx.stat().st_mtime_ns)
        ph = sc.snapshot_worktree(repo, st, dry=False)
        self.assertEqual(ph["action"], "pushed")
        after = (git(repo, "rev-parse", "HEAD"), git(repo, "status", "--porcelain"),
                 (Path(repo) / "README.md").read_text(encoding="utf-8"),
                 idx.stat().st_mtime_ns)
        self.assertEqual(before, after, "the snapshot changed local state")

    def test_the_snapshot_actually_contains_the_uncommitted_text(self):
        """A snapshot that banks the committed version instead would look identical in
        every log line and preserve nothing."""
        repo = self.mk(behind=2, dirty=True)
        ph = self.go(repo)["phases"][1]
        blob = git(repo, "show", f"{ph['commit']}:README.md")
        self.assertIn("locally edited, never committed", blob)

    def test_untracked_files_are_reported_as_not_banked(self):
        repo = self.mk(behind=2, untracked_collision=True)
        ph = self.go(repo)["phases"][1]
        self.assertIn("COLLIDE.md", ph["untracked_not_banked"])

    def test_it_never_uses_the_shared_stash_stack(self):
        """The stash stack is shared with every worktree of this repo and other sessions
        pop it; project memory records that as a standing hazard."""
        src = (ROOT / "scripts" / "sync_checkout.py").read_text(encoding="utf-8")
        self.assertNotIn('"stash"', src)
        self.assertNotIn("'stash'", src)

    # ------------------------------------------------------------ C: fast-forward
    def test_a_plain_behind_checkout_is_fast_forwarded(self):
        repo = self.mk(behind=3)
        r = self.go(repo)
        self.assertFalse(r["alarm"], r["phases"])
        self.assertEqual(r["phases"][-1]["action"], "fast-forwarded")
        self.assertTrue((Path(repo) / "upstream_2.txt").exists())

    def test_a_blocking_untracked_file_is_moved_aside_and_never_deleted(self):
        repo = self.mk(behind=2, untracked_collision=True)
        r = self.go(repo)
        ff = r["phases"][-1]
        self.assertEqual(ff["action"], "fast-forwarded", ff)
        self.assertIn("COLLIDE.md", ff["quarantined"])
        kept = list((Path(repo) / sc.QUARANTINE).rglob("COLLIDE.md"))
        self.assertTrue(kept, "the file was not preserved")
        self.assertIn("MY OWN UNTRACKED VERSION", kept[0].read_text(encoding="utf-8"))
        self.assertIn("the remote's version",
                      (Path(repo) / "COLLIDE.md").read_text(encoding="utf-8"))

    def test_a_blocking_tracked_edit_refuses_and_changes_nothing(self):
        """The one case where completing would destroy work. It must stop."""
        repo = self.mk(behind=2, dirty=True)
        before = (Path(repo) / "README.md").read_text(encoding="utf-8")
        ff = self.go(repo)["phases"][-1]
        self.assertEqual(ff["action"], "refused")
        self.assertEqual(ff["reason"], "local-changes")
        self.assertIn("README.md", ff["blocking_tracked"])
        self.assertEqual((Path(repo) / "README.md").read_text(encoding="utf-8"), before)

    def test_it_refuses_to_fast_forward_a_diverged_branch(self):
        ff = self.go(self.diverged, dry=True)["phases"][-1]
        self.assertEqual((ff["action"], ff["reason"]), ("refused", "diverged"))

    # ------------------------------------------------------------ D: adopt
    def test_adopt_refuses_while_the_work_is_only_local(self):
        r = sc.run(self.diverged, fetch=False, dry=True, adopt=True)
        ad = [p for p in r["phases"] if p["phase"] == "adopt-remote"][0]
        self.assertEqual((ad["action"], ad["reason"]), ("refused", "unverified"))

    def test_adopt_completes_only_after_the_work_is_verified_on_the_remote(self):
        repo = self.mk(ahead=1, behind=2, dirty=True)
        local_sha = git(repo, "rev-parse", "main")
        r = sc.run(repo, fetch=False, adopt=True)
        rescue = r["phases"][0]["ref"]
        snap = r["phases"][1]["commit"]
        ad = [p for p in r["phases"] if p["phase"] == "adopt-remote"][0]
        self.assertEqual(ad["action"], "reset", r["phases"])
        self.assertFalse(r["alarm"], r["phases"])
        # the local pointer moved...
        self.assertEqual(git(repo, "rev-parse", "main"), git(repo, "rev-parse", "origin/main"))
        # ...and BOTH the commit and the uncommitted edit still exist, on the remote.
        self.assertEqual(git(repo, "ls-remote", "--heads", "origin", rescue).split()[0],
                         local_sha)
        self.assertIn("locally edited, never committed", git(repo, "show", f"{snap}:README.md"))

    # ------------------------------------------------------------ dry run
    def test_dry_run_writes_nothing_anywhere(self):
        repo = self.mk(ahead=1, behind=2, dirty=True, untracked_collision=True)
        snap =(git(repo, "rev-parse", "HEAD"), git(repo, "status", "--porcelain"),
                git(repo, "ls-remote", "--heads", "origin"),
                sorted(p.name for p in Path(repo).iterdir()))
        sc.run(repo, fetch=False, dry=True, adopt=True)
        self.assertEqual(snap, (git(repo, "rev-parse", "HEAD"),
                                git(repo, "status", "--porcelain"),
                                git(repo, "ls-remote", "--heads", "origin"),
                                sorted(p.name for p in Path(repo).iterdir())))

    # ------------------------------------------------------------ parsing
    def test_porcelain_parsing_keeps_the_first_character_of_the_first_path(self):
        """Regression. `_out()` strips the whole blob, which ate the leading space of
        porcelain's first line, so a fixed [3:] slice read ` M HANDOFF_STATUS.md` as
        `ANDOFF_STATUS.md`. A phantom name here is a file quarantine silently misses."""
        repo = self.mk(behind=1, dirty=True, untracked_collision=True)
        st = sc.survey(repo, "main", "origin", fetch=False)
        self.assertEqual(st["modified"], ["README.md"])
        self.assertIn("COLLIDE.md", st["untracked"])
        for name in st["modified"] + st["untracked"]:
            self.assertTrue((Path(repo) / name).exists(), name)

    def test_blocked_file_names_keep_their_case(self):
        msg = ("error: The following untracked working tree files would be overwritten "
               "by merge:\n\tCOLLIDE.md\n\tdocs/READ Me.md\nPlease move or remove them.\n")
        self.assertEqual(sc._blocked_files(msg, sc._UNTRACKED_HDR),
                         ["COLLIDE.md", "docs/READ Me.md"])

    def test_it_parses_the_two_headers_git_actually_prints(self):
        """Both strings are quoted from git's own source wording; if git changes them the
        quarantine step silently stops finding anything, so they are pinned here."""
        repo = self.mk(behind=2, untracked_collision=True)
        p = subprocess.run(["git", "merge", "--ff-only", "origin/main"], cwd=repo,
                           capture_output=True, text=True)
        if p.returncode != 0:
            self.assertIn(sc._UNTRACKED_HDR, (p.stderr + p.stdout).lower())

    # ------------------------------------------------------------ blast radius
    def test_the_only_destructive_command_is_behind_adopt_remote(self):
        src = (ROOT / "scripts" / "sync_checkout.py").read_text(encoding="utf-8")
        for danger in ("--force", "-f\"", "clean -", "checkout --"):
            self.assertNotIn(danger, src, danger)
        hard = [m.start() for m in re.finditer(r'"reset", "--hard"', src)]
        self.assertEqual(len(hard), 1, "reset --hard appears more than once")
        fn = src.index("def adopt_remote")
        nxt = src.index("def run(", fn)
        self.assertTrue(fn < hard[0] < nxt, "reset --hard is outside adopt_remote")


class Wiring(unittest.TestCase):
    """The script is only half the item. These pin the parts that make it RUN."""

    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8", errors="replace")

    def test_sync_bat_no_longer_claims_success_on_a_diverged_folder(self):
        """Its old last word on exactly today's state was 'everything is merged. You are
        fully up to date' -- the false all-clear that made 540 commits of drift invisible
        for ten days while the file everyone called 'the cure' ran fine."""
        s = self.read("sync.bat")
        self.assertNotIn("everything is merged. You are fully up to date", s)
        self.assertIn("SYNCRC", s)
        # the all-clear must sit behind the sync result, not only behind the branch count
        allclear = s.index("All agent work is on GitHub and merged into main")
        gate = s.index('if not "!SYNCRC!"=="0"')
        self.assertLess(gate, allclear, "the all-clear is not gated on the sync result")

    def test_sync_bat_rescues_commits_on_main_not_only_worktree_branches(self):
        s = self.read("sync.bat")
        self.assertIn("scripts\\sync_checkout.py", s)

    def test_git_push_syncs_before_it_merges_and_pushes(self):
        """Order is the point: fast-forwarding first is what makes the final push a
        fast-forward. Running it afterwards would report the same thing and fix nothing."""
        s = self.read("git_push.bat")
        self.assertIn("scripts\\sync_checkout.py", s)
        self.assertLess(s.index("sync_checkout.py"), s.index("Auto-land finished agent work"))
        self.assertLess(s.index("sync_checkout.py"), s.index('"%GIT%" push'))

    def test_git_push_does_not_wrap_errorlevel_in_a_parenthesised_block(self):
        """cmd evaluates `if errorlevel` inside ( ) at PARSE time; this cost a day once."""
        s = self.read("git_push.bat")
        block = s[s.index("where python >nul 2>nul || goto :nodrift"):s.index(":drifted")]
        self.assertNotIn("if errorlevel 1 (", block)

    def test_the_bootstrap_reads_the_script_from_origin_and_not_from_disk(self):
        """The whole reason it exists. A launcher that ran this folder's copy would be as
        stale as the folder, so it could only start working after someone had already done
        the thing it is supposed to do automatically."""
        b = self.read("scripts/valquo_sync_bootstrap.bat")
        self.assertIn("git show origin/main:scripts/sync_checkout.py", b)
        self.assertIn("git fetch origin main", b)

    def test_the_bootstrap_refuses_a_truncated_download(self):
        """`git show` still leaves a zero-byte file behind when it fails, and python runs an
        empty file happily and exits 0 - a silent all-clear, which is this item's disease."""
        self.assertIn("LSS", self.read("scripts/valquo_sync_bootstrap.bat"))

    def test_the_installer_copies_the_bootstrap_out_of_the_repo(self):
        i = self.read("install_sync_task.bat")
        self.assertIn("LOCALAPPDATA", i)
        self.assertIn("schtasks /Create", i)
        self.assertIn("scripts\\valquo_sync_bootstrap.bat", i)

    def test_nothing_schedules_the_destructive_step(self):
        """--adopt-remote moves a branch pointer past local commits. It is verified and
        non-destructive in practice, but it must never run with nobody watching."""
        for f in ("install_sync_task.bat", "scripts/valquo_sync_bootstrap.bat",
                  "sync.bat", "git_push.bat"):
            self.assertNotIn("--adopt-remote", self.read(f).replace(
                "python scripts/sync_checkout.py --adopt-remote", ""), f)


def run():
    global PASSED, FAILED
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(T),
        unittest.TestLoader().loadTestsFromTestCase(Wiring),
    ])
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    PASSED = r.testsRun - len(r.failures) - len(r.errors)
    FAILED = len(r.failures) + len(r.errors)
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
