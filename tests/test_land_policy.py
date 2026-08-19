#!/usr/bin/env python3
"""Tests for the auto-land policy and the gate/land split — master audit MA11.

WHAT IS BEING GUARDED. `land-agent-branch.yml` merges any pushed `worktree-*` branch into
main and runs every `tests/test_*.py` FROM THE MERGED TREE, so the branch supplies the code
that judges the branch. Before MA11 that ran in a job holding a `contents: write` token, and
`actions/checkout` persists that token into `.git/config` — so a file named `tests/test_zz.py`
could have pushed straight to main and skipped the gate entirely.

Two properties are pinned here, and they are different in kind:

  * The POLICY (`.github/land_policy.py`) refuses `.github/` changes and test deletions. It is
    read from MAIN's checkout, so a branch cannot switch it off by editing its own copy.
  * The SPLIT (two jobs, `contents: read` for the job that runs branch code) is the only part
    GitHub actually enforces. The policy is a convention the workflow honours; the permission
    is a capability the runner does not have.

`pyyaml` is deliberately not imported: it is not in requirements.lock.txt, so a test that
imported it would pass locally and fail in the very CI job it is meant to describe. The
workflow assertions are textual for that reason, not out of laziness.
"""
import contextlib
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / ".github" / "land_policy.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "land-agent-branch.yml"


def _load_policy():
    """Import `.github/land_policy.py` by path — `.github` is not an importable package."""
    spec = importlib.util.spec_from_file_location("land_policy", POLICY_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lp = _load_policy()


def diff(*lines: str) -> str:
    return "".join(l + "\n" for l in lines)


# An ordinary agent branch: source, a handoff, and a NEW suite. This must stay landable —
# adding a test is the normal workflow and every added suite runs in the gate before landing.
ORDINARY = diff(
    "M\tvaluation/edge/fundamental_panel.py",
    "M\tHANDOFF_ci.md",
    "A\ttests/test_new_thing.py",
    "M\tVALQUO_LEDGER.md",
)


class Policy(unittest.TestCase):

    def test_an_ordinary_branch_is_allowed(self):
        """The guard is worthless if it blocks the workflow it is protecting."""
        ok, refusals = lp.decide(lp.parse_name_status(ORDINARY))
        self.assertTrue(ok, refusals)
        self.assertEqual(refusals, [])

    def test_a_branch_touching_github_is_refused(self):
        for path in (".github/workflows/land-agent-branch.yml",
                     ".github/workflows/auto-scan.yml",
                     ".github/land_policy.py"):
            ok, refusals = lp.decide(lp.parse_name_status(diff(f"M\t{path}")))
            self.assertFalse(ok, path)
            self.assertTrue(any(path in r for r in refusals), refusals)

    def test_the_policy_guards_itself(self):
        """It lives under `.github/` precisely so that weakening it trips its own rule.

        If this file ever moves to `scripts/`, a branch could land a change that softens the
        policy WITHOUT tripping the `.github/` rule, and the next branch would be judged by
        the softened copy. The location is the mechanism, so the location is pinned."""
        self.assertTrue(str(POLICY_PATH).replace("\\", "/").endswith(".github/land_policy.py"))
        rel = ".github/land_policy.py"
        for status in ("M", "D", "A"):
            ok, _ = lp.decide(lp.parse_name_status(diff(f"{status}\t{rel}")))
            self.assertFalse(ok, f"a {status} on the policy itself must be refused")

    def test_deleting_a_test_suite_is_refused(self):
        ok, refusals = lp.decide(lp.parse_name_status(diff("D\ttests/test_edge.py")))
        self.assertFalse(ok)
        self.assertTrue(any("removed from the gate" in r for r in refusals), refusals)

    def test_renaming_a_suite_out_of_the_gate_is_refused(self):
        """`git mv tests/test_edge.py notes/edge.txt` shrinks the gate exactly as a delete
        does, and arrives as a three-field R line rather than a D line."""
        ok, refusals = lp.decide(lp.parse_name_status(
            diff("R100\ttests/test_edge.py\tnotes/edge_old.txt")))
        self.assertFalse(ok)
        self.assertTrue(any("tests/test_edge.py" in r for r in refusals), refusals)

    def test_renaming_a_suite_to_another_suite_is_allowed(self):
        """Renaming `tests/test_a.py` -> `tests/test_b.py` keeps it in `tests/test_*.py`, so
        the gate is unchanged in size. Refusing it would be a false positive."""
        ok, refusals = lp.decide(lp.parse_name_status(
            diff("R100\ttests/test_a.py\ttests/test_b.py")))
        self.assertTrue(ok, refusals)

    def test_editing_a_suite_is_allowed(self):
        """A branch may change behaviour and update the test in the same commit. This is why
        the policy refuses DELETIONS rather than running main's copy of tests/ — that
        alternative would red-X every legitimate paired change."""
        ok, refusals = lp.decide(lp.parse_name_status(diff("M\ttests/test_edge.py")))
        self.assertTrue(ok, refusals)

    def test_a_non_suite_file_under_tests_may_be_deleted(self):
        ok, _ = lp.decide(lp.parse_name_status(diff("D\ttests/fixtures/old.json")))
        self.assertTrue(ok)

    def test_refusals_are_deduplicated(self):
        ok, refusals = lp.decide(lp.parse_name_status(
            diff("M\t.github/workflows/a.yml", "M\t.github/workflows/a.yml")))
        self.assertFalse(ok)
        self.assertEqual(len(refusals), len(set(refusals)))

    def test_parse_ignores_blank_and_malformed_lines(self):
        entries = lp.parse_name_status("\n\nM\tfoo.py\ngarbage\n\n")
        self.assertEqual(entries, [("M", ("foo.py",))])

    def test_exit_codes_distinguish_refusal_from_error(self):
        """0 = land, 2 = refused. They must differ, or the workflow cannot tell a policy
        refusal from a crashed policy — and treating a crash as a refusal (or worse, as a
        pass) is how a check quietly stops checking.

        STDOUT IS CAPTURED, AND NOT FOR TIDINESS. The policy speaks in GitHub Actions workflow
        commands (`::error::`), so when this test exercised the refusal path in-process the
        runner parsed those lines out of the SUITE's output and rendered three red annotations
        on a completely green land run. Found on the first run that carried this file. A gate
        that cries wolf is one you learn to ignore, and annotations that are red on every
        successful land are exactly that. Capturing also lets the test assert the message,
        which the previous version did not."""
        with tempfile.TemporaryDirectory() as td:
            ok_file = os.path.join(td, "ok.diff")
            bad_file = os.path.join(td, "bad.diff")
            io.open(ok_file, "w", encoding="utf-8").write(ORDINARY)
            io.open(bad_file, "w", encoding="utf-8").write(diff("M\t.github/workflows/x.yml"))

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                allowed_rc = lp.main(["--diff-file", ok_file])
                refused_rc = lp.main(["--diff-file", bad_file])
            out = buf.getvalue()

        self.assertEqual(allowed_rc, 0)
        self.assertEqual(refused_rc, 2)
        self.assertIn(".github/workflows/x.yml", out, "the refusal must name the offending path")
        self.assertIn("::error::", out, "the refusal must be loud in the Actions UI")

    def test_the_suite_leaks_no_workflow_commands_to_the_runner(self):
        """The guard for the defect above, rather than a promise to remember.

        Any `::error::`/`::warning::` this suite prints becomes an annotation on a PASSING
        run. This walks every test in the module, runs it with stdout captured, and fails if
        a workflow command escaped -- so a future test that calls the policy directly cannot
        quietly reintroduce three red marks on every land."""
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(Policy)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        escaped = [l for l in buf.getvalue().splitlines()
                   if l.startswith("::error::") or l.startswith("::warning::")]
        self.assertEqual(escaped, [], f"workflow commands leaked to the runner: {escaped[:3]}")

    def test_the_policy_runs_under_the_ci_interpreter_as_a_script(self):
        """It is invoked as `python land_policy.py`, not imported, so a syntax or CLI error
        surfaces only in CI. Run it the way the workflow runs it."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "d.diff")
            io.open(p, "w", encoding="utf-8").write(ORDINARY)
            proc = subprocess.run([sys.executable, str(POLICY_PATH), "--diff-file", p],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("land policy", proc.stdout)


class Workflow(unittest.TestCase):
    """The half GitHub enforces. Textual, because pyyaml is not in the lock (see the docstring)."""

    @classmethod
    def setUpClass(cls):
        cls.body = io.open(WORKFLOW_PATH, encoding="utf-8").read()
        # Split at the `land:` job header so each job can be asserted about separately.
        marker = "\n  land:\n"
        cls.assertTrue(cls, marker in cls.body, "expected a `land:` job")
        head, tail = cls.body.split(marker, 1)
        cls.gate_text, cls.land_text = head, tail

    def test_the_job_that_runs_branch_code_cannot_write(self):
        """MA11's actual security property. Everything else here is convention; this is a
        capability the runner does not possess."""
        self.assertIn("contents: read", self.gate_text)
        self.assertIn("gate:", self.gate_text)

    def test_the_job_that_can_write_runs_no_branch_code(self):
        """If the test loop ever reappears in the `land` job, the split has been undone and
        the write token is back in the same process as untrusted code.

        Asserted on the EXECUTION forms, not on the glob string. The first cut checked for
        `tests/test_*.py` anywhere in the job and failed — on a COMMENT explaining what
        `code_changed` is for. A probe that cannot tell a comment from a command would have
        forced the comment to be deleted to make the suite green, which is silencing a check
        by rewording the thing it reads."""
        code = self._without_comments(self.land_text)
        self.assertNotIn("for f in tests/test_*.py", code)
        self.assertNotIn('python "$f"', code)
        self.assertIn("contents: write", self.land_text)
        self.assertIn("needs: gate", self.land_text)

    def test_that_probe_can_actually_see_an_execution(self):
        """Positive control. The assertion above is two `assertNotIn`s, which pass just as
        happily against an empty string — so prove the same probe FIRES on the gate job,
        where the loop really does run."""
        code = self._without_comments(self.gate_text)
        self.assertIn("for f in tests/test_*.py", code)
        self.assertIn('python "$f"', code)

    @staticmethod
    def _without_comments(text: str) -> str:
        return "\n".join(l for l in text.splitlines() if not l.strip().startswith("#"))

    def test_the_gate_still_runs_every_suite(self):
        """Audit C7's property must survive MA11's restructuring."""
        self.assertIn("for f in tests/test_*.py", self.gate_text)
        self.assertIn("exit $fail", self.gate_text)

    def test_the_retry_for_a_moving_main_lives_in_the_read_only_job(self):
        """Learned from the FIRST live run of the split, not from reasoning.

        The first cut deleted the in-job retry (it would have meant re-running branch code in
        the job holding the write token) and had `land` fail with "push again" instead. Main
        then moved with code inside the ~5 minutes the gate takes, on that very run, and the
        branch refused to land. With six lanes pushing, a re-push is no more likely to win than
        the run it replaces -- so removing the retry does not make the system stricter, it makes
        it livelock. The retry has to exist AND has to be where the token cannot write."""
        self.assertIn("for attempt in 1 2 3; do", self.gate_text,
                      "the gate must retry when main moves under it")
        self.assertIn("code_changed", self.gate_text)
        # and re-running the suites must be part of what it retries
        loop_at = self.gate_text.index("for attempt in 1 2 3; do")
        suites_at = self.gate_text.index("for f in tests/test_*.py")
        self.assertLess(loop_at, suites_at, "the suites must run INSIDE the retry loop")

    def test_both_jobs_agree_on_what_counts_as_code(self):
        """`code_changed` exists in both jobs. If they ever drift, `gate` could clear a tree
        that `land` then pushes onto a main the gate never saw -- which is precisely the
        'combination no gate tested' the split exists to prevent."""
        body_re = re.compile(r"code_changed\(\) \{\s*(.+?)\s*\}", re.S)
        gate_body = body_re.search(self.gate_text)
        land_body = body_re.search(self.land_text)
        self.assertIsNotNone(gate_body, "gate has no code_changed()")
        self.assertIsNotNone(land_body, "land has no code_changed()")
        self.assertEqual(gate_body.group(1).strip(), land_body.group(1).strip(),
                         "the two code_changed() bodies have drifted apart")

    def test_the_policy_is_read_from_mains_checkout_not_the_merged_tree(self):
        """The whole trick. If the workflow ever invokes `.github/land_policy.py` from the
        working tree, it is running the BRANCH's copy — which the branch can neuter."""
        self.assertIn("RUNNER_TEMP/policy/land_policy.py", self.gate_text)
        self.assertNotIn('python .github/land_policy.py', self.body)
        # and it must be copied out BEFORE the merge brings branch content into the tree
        copy_at = self.body.index('cp .github/land_policy.py')
        merge_at = self.body.index('git merge --no-edit "$SHA"')
        self.assertLess(copy_at, merge_at,
                        "the policy must be saved from main before the branch is merged")

    def test_dependencies_install_from_the_hash_pinned_lock(self):
        """MA12, pinned here because it is the same file and the same failure class."""
        self.assertIn("--require-hashes -r requirements.lock.txt", self.body)
        self.assertNotIn("pip install -r requirements.txt", self.body)

    def test_the_runner_python_is_still_pinned(self):
        self.assertIn("python-version: '3.11'", self.body)

    def test_the_residual_is_documented_rather_than_implied_closed(self):
        """For `push` events GitHub runs the YAML from the pushed branch, so a branch that
        rewrites this file escapes the policy. That cannot be fixed from inside the repo, and
        an undocumented residual reads as a solved problem to the next reader."""
        low = self.body.lower()
        self.assertIn("residual", low)
        self.assertIn("ruleset", low)


if __name__ == "__main__":
    unittest.main(verbosity=2)
