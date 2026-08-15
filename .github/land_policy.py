"""Decide whether an agent branch may be auto-landed on `main` (master audit MA11).

THE PROBLEM, VERIFIED RATHER THAN ASSUMED. `land-agent-branch.yml` triggers on any
`worktree-*` push, merges that branch into `main`, and runs `python "$f"` for every
`tests/test_*.py` IN THE MERGED TREE. So the branch supplies the code that judges the branch:
adding `tests/test_zz.py` is sufficient to execute arbitrary code inside the workflow, and
before this item the job held a `contents: write` token while doing it.

WHAT THIS FILE DOES AND, MORE IMPORTANTLY, WHAT IT DOES NOT.

It refuses two specific things that no legitimate agent branch needs to do:

  1. ANY change under `.github/`. The gate, the schedule and the deploy trigger all live
     there, and a branch editing them is editing the thing that judges it. Workflow changes
     are exactly the change that should cost a human step.

  2. DELETING a test suite. A branch may ADD tests (that is the normal workflow, and every
     added suite runs in the gate before landing) and may EDIT them. Removing one shrinks
     the gate, which is the quiet version of rewriting it.

     Deliberately NOT "run main's copy of tests/ instead of the branch's", which is the other
     hardening the audit floats. That would break the ordinary case where a branch changes
     behaviour and updates the test in the same commit -- main's old test would fail against
     the branch's new source, so every legitimate paired change would red-X. Refusing
     DELETIONS gets the property that matters (a branch cannot shrink its own gate) without
     that false-failure class.

WHERE IT IS READ FROM, WHICH IS THE WHOLE TRICK. The workflow copies this file out of
`main`'s checkout BEFORE merging the branch, and runs that copy. So a branch cannot disable
the policy by editing its own copy -- and because the policy lives under `.github/`, any
branch that tries to edit or delete it trips rule 1 and is refused by main's copy. The file
protects itself.

THE RESIDUAL, STATED PLAINLY BECAUSE IT CANNOT BE CLOSED HERE. For `push` events GitHub runs
the workflow YAML from the PUSHED branch, so a branch that rewrites `land-agent-branch.yml`
to not call this script at all escapes it. No file in the repository can prevent that; the
control is a GitHub-side ruleset (require a status check / protect `.github/**`), which is
Don's setting to apply. This closes the accident and the drift; it does not claim to stop a
determined agent, and it should never be described as if it did.

Exit codes: 0 = may auto-land, 2 = refused (human step required), 1 = internal error.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

# A branch may add and edit suites; it may not remove them. See the module docstring.
TESTS_PREFIX = "tests/test_"
GUARDED_PREFIX = ".github/"


def parse_name_status(text: str) -> list[tuple[str, tuple[str, ...]]]:
    """Parse `git diff --name-status` into (status, paths).

    Renames and copies arrive as `R100\told\tnew` and carry TWO paths -- both matter here,
    since renaming `tests/test_edge.py` to `notes/test_edge.txt` removes a suite from the
    gate just as surely as deleting it.
    """
    out: list[tuple[str, tuple[str, ...]]] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        paths = tuple(p.strip().replace("\\", "/") for p in parts[1:] if p.strip())
        if paths:
            out.append((status, paths))
    return out


def decide(entries: list[tuple[str, tuple[str, ...]]]) -> tuple[bool, list[str]]:
    """Return (allowed, refusals). Empty refusals means the branch may auto-land."""
    refusals: list[str] = []

    for status, paths in entries:
        code = status[0] if status else ""

        for path in paths:
            if path.startswith(GUARDED_PREFIX):
                refusals.append(
                    f"{path} -- the branch changes {GUARDED_PREFIX}, which is the gate that "
                    f"judges it ({status})"
                )
                break

        # A deletion carries one path; a rename carries (old, new) and only the OLD one is
        # the suite that stops existing.
        if code in ("D", "R"):
            old = paths[0]
            if old.startswith(TESTS_PREFIX) and old.endswith(".py"):
                if code == "R" and len(paths) > 1 and paths[1].startswith(TESTS_PREFIX) \
                        and paths[1].endswith(".py"):
                    continue  # renamed one suite to another suite: still in the gate
                refusals.append(
                    f"{old} -- a test suite is removed from the gate ({status})"
                )

    # De-duplicate while keeping order: one path can trip only one message per rule, but a
    # single refusal repeated reads like several problems.
    seen: set[str] = set()
    unique = [r for r in refusals if not (r in seen or seen.add(r))]
    return (not unique), unique


def git_name_status(base: str, head: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", f"{base}...{head}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"land_policy: git diff failed: {proc.stderr.strip()}")
    return proc.stdout


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Auto-land policy for agent branches (MA11).")
    ap.add_argument("--base", help="merge-base side, e.g. origin/main")
    ap.add_argument("--head", help="branch side, e.g. the pushed sha")
    ap.add_argument("--diff-file", help="read `git diff --name-status` output from a file "
                                        "instead of running git (used by the tests)")
    args = ap.parse_args(argv)

    if args.diff_file:
        with open(args.diff_file, encoding="utf-8") as fh:
            text = fh.read()
    elif args.base and args.head:
        text = git_name_status(args.base, args.head)
    else:
        ap.error("need --diff-file, or both --base and --head")
        return 1

    entries = parse_name_status(text)
    allowed, refusals = decide(entries)

    print(f"land policy: {len(entries)} changed path(s) inspected")
    if allowed:
        print("land policy: OK -- nothing guarded was touched")
        return 0

    # `::error::` so it is loud in the Actions UI rather than buried in a log group.
    print("::error::land policy REFUSED this branch -- it may not be auto-landed:")
    for r in refusals:
        print(f"::error::  {r}")
    print("::error::A change under .github/, or removing a suite, needs a human. "
          "Open a PR and have Don merge it; do not weaken this check to get around it.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
