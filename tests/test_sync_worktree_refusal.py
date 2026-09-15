"""SYNC MUST NOT TAKE A PATH GIT ALWAYS REFUSES — the 211-commit drift, pinned.

THE DEFECT THIS PINS, because the number is the argument. The shared checkout sat **0 ahead
and 211 behind** `origin/main` while `sync.bat` ran and reported. `survey` records `on_branch`
from `git rev-parse --abbrev-ref HEAD`, which answers *"is the branch checked out **HERE**"*.
Git's refusal to fetch into a ref is repo-**WIDE**: it declines if the branch is checked out in
**ANY** worktree, and says so —

    fatal: refusing to fetch into branch 'refs/heads/main' checked out at '<path>'

This repository has twelve worktrees. Run the sync from any of them and `on_branch` is false
while `main` is still checked out in the main folder, so the tool took the one path git always
refuses. It failed every time, the exit code scrolled past, and the branch never moved. **A
worktree-local property was standing in for a repo-wide constraint** — MA20's own shape, in the
tool written to cure MA20.

**THE DETECTION IS TESTED AGAINST REAL GIT, NOT A STUB.** `checked_out_at` is asked about a
genuine temporary repository with a genuine second worktree, because checking a git rule
against a fake answers a question about the fake — the same reason the fleet harness tests its
declaration-before-fill rule against a real repository.

**AND THE REFUSAL IS TESTED BY WATCHING WHAT IT RUNS.** Asserting "it did not fail" would pass
if the tool silently skipped the phase; the test records every git command and asserts that the
refspec fetch is NEVER among them, and that the phase stays NOT done so the run alarms.

Run: python tests/test_sync_worktree_refusal.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

import sync_checkout as SC                                               # noqa: E402

PASSED = FAILED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def _git(d, *a):
    return subprocess.run(["git"] + list(a), cwd=d, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _real_repo_with_a_worktree(d):
    """A genuine repo on `main`, plus a second worktree on `side`. Returns (repo, worktree)."""
    repo = os.path.join(d, "repo")
    os.makedirs(repo)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    with open(os.path.join(repo, "f.txt"), "w", encoding="utf-8") as f:
        f.write("one\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "one")
    wt = os.path.join(d, "wt")
    _git(repo, "worktree", "add", "-q", "-b", "side", wt)
    return repo, wt


# =======================================================================================
# DETECTION — against real git
# =======================================================================================
def test_a_branch_checked_out_in_the_main_folder_is_found_from_anywhere():
    if not shutil.which("git"):
        print("       (SKIPPED LOUDLY: no git on PATH — this rule is UNVERIFIED here)")
        return
    with tempfile.TemporaryDirectory() as d:
        repo, wt = _real_repo_with_a_worktree(d)
        # Asked FROM THE WORKTREE, which is the case that broke: `main` is checked out in the
        # main folder, and the worktree's own HEAD says `side`.
        found = SC.checked_out_at(wt, "main")
        assert found, "main was not detected as checked out, asked from the second worktree"
        assert os.path.normcase(os.path.abspath(found)) == os.path.normcase(
            os.path.abspath(repo)), (found, repo)
        # ...and the worktree's own branch is found too, so the helper is not just returning
        # the first entry.
        side = SC.checked_out_at(wt, "side")
        assert side and os.path.normcase(os.path.abspath(side)) == os.path.normcase(
            os.path.abspath(wt)), (side, wt)


def test_a_branch_checked_out_nowhere_is_reported_as_such():
    """The legitimate case must still be distinguishable, or the fix is just a blanket refusal."""
    if not shutil.which("git"):
        return
    with tempfile.TemporaryDirectory() as d:
        repo, wt = _real_repo_with_a_worktree(d)
        _git(repo, "branch", "parked")
        assert SC.checked_out_at(repo, "parked") is None, "a parked branch read as checked out"


# =======================================================================================
# THE REFUSAL — by watching what it runs
# =======================================================================================
def _fast_forward_recording(st):
    """Run `fast_forward` with every git call recorded instead of executed."""
    calls = []

    def fake(repo, *args, **kw):
        calls.append(tuple(args))
        class _P:
            returncode = 0
            stdout = ""
            stderr = ""
        return _P()

    real_git, real_out = SC._git, SC._out
    SC._git = fake
    SC._out = lambda repo, *a, **kw: ""
    try:
        r = SC.fast_forward("/nonexistent", st, dry=False)
    finally:
        SC._git, SC._out = real_git, real_out
    return r, calls


def _state(**over):
    st = {"branch": "main", "remote": "origin", "upstream": "origin/main",
          "behind": 211, "ahead": 0, "on_branch": False, "head_branch": "side",
          "modified": [], "untracked": []}
    st.update(over)
    return st


def test_sync_never_emits_a_refspec_fetch_for_a_branch_checked_out_elsewhere():
    """THE pin. `git fetch origin main:main` is refused repo-wide, so it must never be run."""
    real = SC.checked_out_at
    SC.checked_out_at = lambda repo, branch: r"C:\some\main\folder"
    try:
        r, calls = _fast_forward_recording(_state())
    finally:
        SC.checked_out_at = real

    for c in calls:
        assert not (c and c[0] == "fetch" and any(":" in str(x) for x in c[1:])), (
            "a refspec fetch of a checked-out branch was emitted: %r" % (c,))
    assert r.get("action") == "refused", r
    assert r.get("reason") == "checked-out-elsewhere", r


def test_it_does_not_report_success_while_the_branch_is_still_behind():
    """Four green days with nothing pushed is the failure this repairs: the phase must stay
    NOT done, which is what makes the whole run alarm and exit non-zero."""
    real = SC.checked_out_at
    SC.checked_out_at = lambda repo, branch: r"C:\some\main\folder"
    try:
        r, _ = _fast_forward_recording(_state(behind=211))
    finally:
        SC.checked_out_at = real
    assert r.get("done") is False, "the phase reported done while main was 211 behind"
    assert "211" in str(r.get("detail") or ""), (
        "the refusal does not say how far behind the branch was left: %r" % r.get("detail"))


def test_the_refusal_names_the_folder_and_the_command_to_run_there():
    """A clear instruction, not just a complaint — the operator has to be able to act on it."""
    real = SC.checked_out_at
    SC.checked_out_at = lambda repo, branch: r"C:\some\main\folder"
    try:
        r, _ = _fast_forward_recording(_state())
    finally:
        SC.checked_out_at = real
    d = str(r.get("detail") or "")
    assert r.get("checked_out_at") == r"C:\some\main\folder", r
    assert r"C:\some\main\folder" in d, d
    assert "merge --ff-only" in d and "origin/main" in d, d


def test_the_legitimate_ref_update_still_happens_when_nothing_has_it_checked_out():
    """The fix must not be a blanket refusal: a branch checked out nowhere is still moved."""
    real = SC.checked_out_at
    SC.checked_out_at = lambda repo, branch: None
    try:
        r, calls = _fast_forward_recording(_state())
    finally:
        SC.checked_out_at = real
    assert r.get("done") is True and r.get("action") == "ref-updated", r
    assert any(c and c[0] == "fetch" and "main:main" in str(c) for c in calls), (
        "the legitimate ref update no longer happens: %r" % (calls,))


def test_an_on_branch_checkout_is_untouched_by_this_change():
    """When the branch IS checked out here, the tool still fast-forwards normally."""
    real = SC.checked_out_at
    SC.checked_out_at = lambda repo, branch: None
    try:
        r, calls = _fast_forward_recording(_state(on_branch=True, head_branch="main"))
    finally:
        SC.checked_out_at = real
    assert any(c and c[0] == "merge" for c in calls), (
        "the on-branch path no longer merges: %r" % (calls,))


def run():
    global PASSED, FAILED
    print("SYNC / WORKTREE REFUSAL")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
