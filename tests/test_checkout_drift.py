#!/usr/bin/env python3
"""Tests for scripts/checkout_drift.py - MA20's alarm.

Every test drives real git repositories. No mocks: the thing under test is "what does
git say about two refs", and a mocked git would pin my belief about git rather than git.

THE FIXTURES ARE BUILT ONCE PER RUN, NOT ONCE PER TEST, and that is a correctness
choice rather than a speed one. Per-test construction issued ~200 git subprocesses per
run and the suite then failed about one run in four on Windows - always as an ERROR
during setup, never on an assertion. A gate that cries wolf is one you learn to ignore,
which this project has written down twice. Six repositories are built once, and every
test is read-only against them, so the whole class of failure is gone rather than
retried.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.checkout_drift import (  # noqa: E402
    DEFAULT_MAX_BEHIND, DriftUnknown, main, measure, render, verdict,
)

PASSED = FAILED = 0


def git(repo, *args):
    # gc.auto=0 so a clone cannot spawn a background gc that outlives the call and keeps
    # the object store open.
    p = subprocess.run(["git", "-c", "gc.auto=0", *args], cwd=str(repo),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {args} in {repo}: {p.stderr.strip()}")
    return p.stdout.strip()


def commit(repo, msg, name="f.txt"):
    (Path(repo) / name).write_text(msg, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", msg)


def build(root, tag, ahead=0, behind=0):
    """An 'origin' and a clone whose main is `ahead`/`behind` it."""
    origin = Path(root) / f"{tag}-origin"
    origin.mkdir(parents=True)
    git(origin, "init", "-q", "-b", "main")
    commit(origin, "base")
    local = Path(root) / f"{tag}-local"
    git(root, "clone", "-q", str(origin), str(local))
    for i in range(behind):
        commit(origin, f"remote-{i}")
    for i in range(ahead):
        commit(local, f"local-{i}", name="g.txt")
    if behind:
        git(local, "fetch", "-q", "origin", "main")
    return str(local)


class T(unittest.TestCase):
    """Read-only against fixtures built once. Nothing here may mutate a repo."""

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="drift-")
        cls.clean = build(cls.root, "clean")
        cls.behind7 = build(cls.root, "b7", behind=7)
        cls.behind5 = build(cls.root, "b5", behind=5)
        cls.behind9 = build(cls.root, "b9", behind=9)
        cls.ahead1 = build(cls.root, "a1", ahead=1)
        cls.ahead2 = build(cls.root, "a2", ahead=2)
        cls.both = build(cls.root, "both", ahead=1, behind=3)
        cls.plain = str(Path(cls.root) / "plain")          # exists, not a repo
        os.makedirs(cls.plain, exist_ok=True)
        cls.solo = Path(cls.root) / "solo"                 # a repo with no remote
        cls.solo.mkdir()
        git(cls.solo, "init", "-q", "-b", "main")
        commit(cls.solo, "only")

    @classmethod
    def tearDownClass(cls):
        # Windows can still hold handles under .git/objects; leaking a temp dir is
        # strictly better than failing a green run in teardown.
        shutil.rmtree(cls.root, ignore_errors=True)

    # ---------------------------------------------------------------- measurement
    def test_a_current_checkout_is_zero_ahead_zero_behind(self):
        s = measure(self.clean, fetch=False)
        self.assertEqual((s["ahead"], s["behind"]), (0, 0))
        self.assertFalse(verdict(s)["alarm"])

    def test_behind_is_counted_and_ahead_is_not_confused_with_it(self):
        """The two directions have opposite cures; swapping them would send Don to push
        work that does not exist while the real problem went unreported."""
        s = measure(self.behind7, fetch=False)
        self.assertEqual((s["ahead"], s["behind"]), (0, 7))

    def test_ahead_is_counted_and_the_stranded_commits_are_named(self):
        s = measure(self.ahead2, fetch=False)
        self.assertEqual((s["ahead"], s["behind"]), (2, 0))
        self.assertEqual(len(s["stranded"]), 2)
        self.assertIn("local-1", " ".join(s["stranded"]))

    def test_the_real_shape_of_ma20_diverged_both_ways(self):
        """1 ahead / 514 behind was the measured state on 2026-08-14."""
        s = measure(self.both, fetch=False)
        self.assertEqual((s["ahead"], s["behind"]), (1, 3))
        v = verdict(s, max_behind=2)
        self.assertTrue(v["too_far_behind"] and v["has_unpushed"])

    # ---------------------------------------------------------------- the threshold
    def test_the_threshold_is_strictly_greater_than_not_equal(self):
        s = measure(self.behind5, fetch=False)
        self.assertFalse(verdict(s, max_behind=5)["alarm"], "5 behind at a bar of 5 must not fire")
        self.assertTrue(verdict(s, max_behind=4)["alarm"])

    def test_one_unpushed_commit_alarms_at_any_threshold(self):
        """Being ahead is not a matter of degree - that commit exists nowhere else."""
        s = measure(self.ahead1, fetch=False)
        self.assertTrue(verdict(s, max_behind=10_000)["alarm"])

    def test_default_threshold_is_the_measured_daily_rate(self):
        self.assertEqual(DEFAULT_MAX_BEHIND, 50)

    # ---------------------------------------------------------------- fail loud
    def test_a_directory_that_is_not_a_repo_is_an_alarm_not_a_pass(self):
        with self.assertRaises(DriftUnknown):
            measure(self.plain, fetch=False)
        self.assertEqual(main(["--repo", self.plain, "--no-fetch"]), 1)

    def test_a_missing_directory_is_an_alarm_not_a_pass(self):
        self.assertEqual(main(["--repo", str(Path(self.root) / "nope-zz"), "--no-fetch"]), 1)

    def test_a_missing_upstream_ref_is_an_alarm_not_a_pass(self):
        """The failure mode that matters: never-fetched looks identical to up-to-date if
        a missing ref is read as zero."""
        with self.assertRaises(DriftUnknown):
            measure(str(self.solo), fetch=False)

    # ---------------------------------------------------------------- exit codes
    def test_exit_code_zero_only_when_clean(self):
        self.assertEqual(main(["--repo", self.clean, "--no-fetch"]), 0)
        self.assertEqual(main(["--repo", self.ahead1, "--no-fetch"]), 1)
        self.assertEqual(main(["--repo", self.behind9, "--no-fetch", "--max-behind", "2"]), 1)

    def test_json_mode_is_parseable_and_carries_the_alarm(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["--repo", self.ahead1, "--no-fetch", "--json"])
        d = json.loads(buf.getvalue())
        self.assertTrue(d["alarm"] and d["has_unpushed"])

    def test_json_mode_reports_the_unknown_case_too(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--repo", self.plain, "--no-fetch", "--json"])
        self.assertEqual(rc, 1)
        self.assertTrue(json.loads(buf.getvalue())["alarm"])

    # ---------------------------------------------------------------- the message
    def test_the_alarm_names_the_cure(self):
        txt = "\n".join(render(verdict(measure(self.behind9, fetch=False), 2)))
        self.assertIn("sync.bat", txt)

    def test_the_stranded_alarm_warns_that_a_green_task_is_not_a_push(self):
        """git_push.bat exits 0 whether or not the push succeeded; four days of
        LastTaskResult=0 hid this. If that sentence goes, the alarm loses its point."""
        txt = "\n".join(render(verdict(measure(self.ahead1, fetch=False))))
        self.assertIn("git_push.bat", txt)
        self.assertIn("green task", txt)

    def test_a_clean_checkout_says_nothing_alarming(self):
        txt = "\n".join(render(verdict(measure(self.clean, fetch=False))))
        self.assertIn("[OK]", txt)
        self.assertNotIn("[ALARM]", txt)

    # ---------------------------------------------------------------- pinned constant
    def test_the_shared_checkout_path_is_pinned_not_derived(self):
        """A copy of this script lives in every worktree. If it measured its own tree it
        would always be fresh and would always pass - the exact way backup_to_D.ps1's
        $SRC could have gone wrong, and the reason both are pinned."""
        src = (Path(__file__).resolve().parents[1] / "scripts" / "checkout_drift.py").read_text(encoding="utf-8")
        self.assertIn(r'SHARED_CHECKOUT = r"C:\Users\donni\Downloads\valuation-tool"', src)
        self.assertNotIn("__file__", src.split("def _git")[0].split("SHARED_CHECKOUT")[1])

    def test_the_fixtures_are_shared_so_no_test_may_mutate_them(self):
        """Pins the design above: if a future test starts building its own repo per
        call, the subprocess count climbs back and the flakiness returns."""
        body = Path(__file__).read_text(encoding="utf-8").split("class T(")[1]
        self.assertNotIn("build(", body.split("def tearDownClass")[1])


def run():
    global PASSED, FAILED
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestLoader().loadTestsFromTestCase(T))
    PASSED = r.testsRun - len(r.failures) - len(r.errors)
    FAILED = len(r.failures) + len(r.errors)
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
