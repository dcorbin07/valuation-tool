# -*- coding: utf-8 -*-
"""ITEM 77 — THE CONTROL: run the auditor's reproductions against the PRE-FIX sources.

**WHY THIS EXISTS.** `tests/test_item71_table.py`'s item-77 section asserts that a missing
percentage does not liquidate, that a percentage event works more than once, and that a price
move inside an open event does not trade. All three pass on the tree that ships them -- which
is exactly what a test asserting the implementation's own behaviour would also do. The control
is to run the identical cases against the sources as they were BEFORE item 77 and require them
to fail. `scripts/i71_table_before.py` does the same thing for item 71 and this follows it.

    python -m scripts.i77_before            # defaults to comparing against HEAD~1

It restores the three live-path modules from a git revision into a temporary tree, runs the
four item-77 test classes there, and prints which of them fail. It writes nothing outside the
temporary directory and places no order: every HTTP reply in those tests is a recorded fixture.

**MEASURED 2026-10-21, against the commit before item 77's fix: 11 of 16 fail.** The five that
pass on both trees are the controls and the positive cases, and they are listed by name below
so a future reader can tell "this control is supposed to pass on both" from "this stopped
biting".
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

#: The modules item 77 changed.
SOURCES = ("valuation/edge/live_cycle.py",
           "valuation/edge/live_slots.py",
           "valuation/saas/alert_routing.py")

#: The four classes holding the auditor's reproductions.
CLASSES = ("BlockerAAnAbsentPercentageMustNotLiquidate",
           "BlockerBEachPercentageEventWorksMoreThanOnce",
           "BlockerCAPriceMoveInsideAnOpenEventDoesNotTrade",
           "TheTwoNonBlockingRepairs")

#: **EXPECTED TO PASS ON BOTH TREES, and each one says why.** A test here that started failing
#: on the OLD tree would mean the control had drifted into asserting the new behaviour twice.
PASS_ON_BOTH = {
    "test_a_STATED_zero_still_winds_down":
        "the positive control: Don's documented way out worked before and after",
    "test_a_slot_that_holds_NOTHING_stays_quiet_with_no_percentage":
        "the ordinary dormant state, unchanged by item 77",
    "test_a_restart_still_never_repeats_the_SAME_occurrence":
        "the property item 77 had to preserve, not the one it fixed",
    "test_the_mark_cancels_in_the_planner_itself":
        "asserted on the shipped planner with the frozen SHARE COUNT supplied by the test, "
        "so it is a statement about the arithmetic rather than about the freeze",
    "test_the_OLD_dollar_freeze_really_did_sell_which_is_the_control":
        "it reproduces the OLD behaviour deliberately, so it must pass on both",
}


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(rev="HEAD~1"):
    repo = _repo()
    tmp = tempfile.mkdtemp(prefix="i77_before_")
    try:
        # The whole tree, so imports resolve exactly as they do in CI.
        for name in os.listdir(repo):
            if name in (".git", ".claude"):
                continue
            src = os.path.join(repo, name)
            dst = os.path.join(tmp, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(src, dst)
        # ... then the three modules rolled back.
        for rel in SOURCES:
            blob = subprocess.run(["git", "show", "%s:%s" % (rev, rel)],
                                  cwd=repo, capture_output=True)
            if blob.returncode != 0:
                print("could not read %s at %s" % (rel, rev))
                return 2
            # BYTES, not text: decoding git's output as the console codepage is how a
            # Windows run manufactures a diff that is not there.
            with open(os.path.join(tmp, rel), "wb") as fh:
                fh.write(blob.stdout)
        args = [sys.executable, "-m", "unittest", "-v"] + \
               ["tests.test_item71_table.%s" % c for c in CLASSES]
        r = subprocess.run(args, cwd=tmp, capture_output=True)
        text = (r.stdout + r.stderr).decode("utf-8", "replace")
        failed = sorted({ln.split("(")[0].strip().split(":")[-1].strip()
                         for ln in text.splitlines()
                         if ln.startswith(("FAIL:", "ERROR:"))})
        ran = text.rsplit("Ran ", 1)[-1].split(" ")[0] if "Ran " in text else "?"
        # **WHAT IT ACTUALLY COMPARED AGAINST, not just the name it was given.** `HEAD~1` means
        # "before item 77" only while item 77 is the tip; once anything lands on top of it the
        # default is silently the wrong tree and the control would report zero failures, which
        # reads as "these tests are a mirror" rather than as "you pointed it at the wrong
        # commit". Printing the resolved subject makes that visible in one line.
        subj = subprocess.run(["git", "log", "-1", "--format=%h %s", rev],
                              cwd=repo, capture_output=True)
        print("sources rolled back to %s  (%s)"
              % (rev, subj.stdout.decode("utf-8", "replace").strip() or "unknown"))
        print("ran %s tests; %d FAILED on the pre-item-77 tree" % (ran, len(failed)))
        print()
        for name in failed:
            print("  FAILS (as it must):", name)
        print()
        unexpected = [n for n in PASS_ON_BOTH if n in failed]
        for name, why in sorted(PASS_ON_BOTH.items()):
            mark = "DRIFTED" if name in failed else "passes on both"
            print("  %-16s %s\n      %s" % (mark, name, why))
        if unexpected:
            print()
            print("WARNING: a control that should pass on both trees FAILED: %r" % unexpected)
            return 1
        if not failed:
            print()
            print("WARNING: nothing failed on the old tree, so these tests are a mirror of "
                  "the implementation rather than a check on it.")
            return 1
        return 0
    finally:
        shutil.rmtree(tmp, True)


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:] or [])))
