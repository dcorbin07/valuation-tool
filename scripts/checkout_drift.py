#!/usr/bin/env python3
"""
checkout_drift.py - the alarm for MA20.

    python scripts/checkout_drift.py                 # check the shared checkout
    python scripts/checkout_drift.py --json          # machine-readable
    python scripts/checkout_drift.py --repo X --no-fetch

WHAT THIS IS FOR
----------------
Agents work in .claude/worktrees/* and land through the auto-land Action, so nobody's
normal workflow ever refreshes the SHARED checkout at C:\\Users\\donni\\Downloads\\valuation-tool.
Windows runs its .bat files from that tree by absolute path. Measured 2026-08-14 it was
**1 commit ahead and 514 behind origin/main**, and the one local commit -- a dated
PT-WRITER failure note that answers an open ledger row -- had been stranded since
2026-08-10 20:06.

`sync.bat` is the cure. This is only the alarm: it measures and reports, and changes
nothing. Deliberately - a guard that silently repairs is a guard whose failures are
invisible, and this whole item exists because something failed invisibly.

WHY IT DOES ITS OWN FETCH
-------------------------
`git_push.bat` runs daily at 20:00 and calls no `git fetch` anywhere, so it cannot
know it is behind: it merges local worktree-* branches, runs the tests and pushes.
Once local main has diverged that push is rejected as a non-fast-forward, and the
script prints "Run connect_github.bat once so Windows saves your GitHub login" --
blaming credentials for a divergence. It then exits 0, so the Task Scheduler recorded
LastTaskResult=0 on four consecutive days while the commit sat unpushed. An alarm that
reads a stale remote ref would reproduce exactly that failure, so this fetches first
and treats a failed fetch as an alarm rather than as a pass.

FAIL LOUD, NOT SILENT
---------------------
Every state that is not provably fine is an alarm: no git, not a repository, no such
remote, a failed fetch. "I could not tell" and "all clear" must never share an exit
code -- that equivalence is what let this run for ten days.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# The shared checkout. Pinned, not derived from __file__: this script also exists inside
# every worktree, and a copy that measured "its own tree" would report the worktree --
# which is always fresh, and so would always say everything is fine. Same reasoning as
# backup_to_D.ps1's pinned $SRC, and the same trap.
SHARED_CHECKOUT = r"C:\Users\donni\Downloads\valuation-tool"

# origin/main takes a median of 49 commits a day (measured over the twelve days to
# 2026-08-14: 17, 46, 67, 27, 75, 53, 49, 25, 57, 90, 46, 49). So 50 behind is about ONE
# DAY of drift, which is the point at which a .bat on disk stops being the .bat on main.
# It is a round number chosen from a measured rate, not a bare convention -- but it is
# also not a calibrated threshold and carries no verdict.
COMMITS_PER_DAY = 49          # the measured median; used only to phrase "days of drift"
DEFAULT_MAX_BEHIND = 50       # COMMITS_PER_DAY rounded up to a round number

OK = 0
ALARM = 1


class DriftUnknown(Exception):
    """Raised when the state cannot be measured. Never silently a pass."""


def _git(repo: str, *args: str, timeout: int = 120) -> str:
    try:
        p = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise DriftUnknown("git is not on PATH")
    except subprocess.TimeoutExpired:
        raise DriftUnknown(f"git {' '.join(args)} timed out after {timeout}s")
    except NotADirectoryError:
        raise DriftUnknown(f"not a directory: {repo}")
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip().splitlines()
        raise DriftUnknown(f"git {' '.join(args)} failed: {err[0] if err else '?'}")
    return p.stdout.strip()


def measure(repo: str = SHARED_CHECKOUT, remote: str = "origin", branch: str = "main",
            fetch: bool = True) -> dict:
    """Ahead/behind of `repo`'s local `branch` against `remote/branch`.

    Raises DriftUnknown for anything it cannot establish.
    """
    _git(repo, "rev-parse", "--is-inside-work-tree")
    if fetch:
        # Read-only. Never --prune here: this is an alarm, and an alarm does not mutate
        # refs it does not own.
        _git(repo, "fetch", remote, branch, timeout=300)

    upstream = f"{remote}/{branch}"
    counts = _git(repo, "rev-list", "--left-right", "--count", f"{branch}...{upstream}")
    parts = counts.split()
    if len(parts) != 2:
        raise DriftUnknown(f"could not parse rev-list output: {counts!r}")
    ahead, behind = int(parts[0]), int(parts[1])

    head = _git(repo, "rev-parse", "--short", branch)
    stranded = []
    if ahead:
        out = _git(repo, "log", "--format=%h %ad %s", "--date=short",
                   f"{upstream}..{branch}")
        stranded = [ln for ln in out.splitlines() if ln.strip()]

    return {"repo": repo, "branch": branch, "upstream": upstream, "head": head,
            "ahead": ahead, "behind": behind, "stranded": stranded, "fetched": fetch}


def verdict(state: dict, max_behind: int = DEFAULT_MAX_BEHIND) -> dict:
    """Two INDEPENDENT alarms. Reported separately because the cures differ: being
    behind is stale reads, being ahead is work that exists nowhere else."""
    too_far = state["behind"] > max_behind
    unpushed = state["ahead"] > 0
    return {**state, "max_behind": max_behind, "too_far_behind": too_far,
            "has_unpushed": unpushed, "alarm": bool(too_far or unpushed)}


def render(v: dict) -> list[str]:
    out = ["", "=" * 64, "  SHARED CHECKOUT DRIFT", "=" * 64,
           f"  {v['repo']}",
           f"  {v['branch']} @ {v['head']}  vs  {v['upstream']}",
           f"  behind: {v['behind']}   ahead: {v['ahead']}   (alarm at behind > {v['max_behind']}, or any ahead)",
           ""]
    if not v["alarm"]:
        out += ["  [OK] The checkout is current. Nothing to do.", ""]
        return out

    if v["too_far_behind"]:
        out += [f"  [ALARM] {v['behind']} commits behind - roughly "
                f"{v['behind'] / COMMITS_PER_DAY:.1f} days of drift.",
                "          Every .bat Windows runs from this folder is that old, including the",
                "          backup and the deploy. A fix landed on main is NOT a fix on this machine.",
                ""]
    if v["has_unpushed"]:
        out += [f"  [ALARM] {v['ahead']} local commit(s) exist ONLY here - not on GitHub, not in any backup:",
                ""]
        out += [f"            {ln}" for ln in v["stranded"]]
        out += ["",
                "          A diverged main also makes `git push` fail as a non-fast-forward.",
                "          git_push.bat reports that as a login problem and exits 0, so the",
                "          Task Scheduler records success. Do not read a green task as a push.",
                ""]
    out += ["  THE CURE:  sync.bat        (fetches, pushes agent branches, fast-forwards main)",
            "  If sync.bat reports uncommitted changes in the main folder, commit them first -",
            "  it skips the fast-forward rather than discarding anything.", ""]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Alarm when the shared checkout drifts.")
    ap.add_argument("--repo", default=SHARED_CHECKOUT)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--max-behind", type=int, default=DEFAULT_MAX_BEHIND)
    ap.add_argument("--no-fetch", action="store_true",
                    help="measure against the remote ref already on disk (tests, offline)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        v = verdict(measure(a.repo, a.remote, a.branch, fetch=not a.no_fetch),
                    a.max_behind)
    except DriftUnknown as e:
        # Unknown is an ALARM, not a pass.
        if a.json:
            print(json.dumps({"alarm": True, "unknown": str(e), "repo": a.repo}, indent=1))
        else:
            print(f"\n  [ALARM] Could not measure {a.repo}: {e}")
            print("          Unknown is not the same as fine, so this exits non-zero.\n")
        return ALARM

    print(json.dumps(v, indent=1) if a.json else "\n".join(render(v)))
    return ALARM if v["alarm"] else OK


if __name__ == "__main__":
    sys.exit(main())
