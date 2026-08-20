"""MB36 - the guard that makes the documentation move SAFE to do later.

**THE MOVE IS NOT DONE.** `MB36` proposes moving 71 `PREREG_*.md` and 48 `HANDOFF_*.md` into
`register/` and `handoff/` as git renames. This file is the hazard neutralisation that must exist
FIRST, shipped ahead of the move so whoever performs it is protected rather than trusted.

HAZARD 1 - THE ONE THE AUDIT NAMED. `valuation/web/research_record.py` lists the pre-registration
documents by **globbing the filesystem** (`glob.glob(os.path.join(root, "PREREG_*.md"))`), not from
a manifest. A move that does not update that glob **in the same commit** silently empties the
public research page's register list, and nothing raises. An empty list is not an error; it renders
as a page that has no registers, which on a public page that exists to evidence the register
discipline is the worst possible failure.

HAZARD 2 - WHICH THE AUDIT DOES NOT NAME, AND WHOSE FAILURE MODE IS INVISIBLE. `.gitattributes`
sets `HANDOFF_*.md merge=union`, and that union rule is what keeps five parallel agent lanes
landing: the file's own header records `HANDOFF_STATUS.md` taking 29 commits from many lanes in
three days with every conflict resolved the same way. Measured here with `git check-attr`:

    HANDOFF_edge_audit.md          -> merge: union
    handoff/HANDOFF_edge_audit.md  -> merge: union      (prefix KEPT - protection survives)
    handoff/edge_audit.md          -> merge: unspecified (prefix DROPPED - protection LOST)

So the move is safe **only if the filenames keep their prefix** - and `handoff/HANDOFF_x.md`
stutters, so de-stuttering is the obvious tidy and it is the one that breaks it. Unlike hazard 1
this fails **invisibly**: nothing renders wrong, and it surfaces weeks later as branches that stop
landing. That asymmetry is why it is pinned here rather than left to the mover to remember.

WHAT THESE TESTS DO NOT DO. They do not require the move, forbid it, or assume a destination. They
assert the two INVARIANTS that must hold before and after it, so the move can be made in one
commit and verified in the same run.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import research_record as RR       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKIPS = []


def _check_attr(path):
    """`git check-attr merge -- <path>`; None when git is unavailable."""
    try:
        r = subprocess.run(["git", "check-attr", "merge", "--", path],
                           capture_output=True, text=True, cwd=ROOT, timeout=30)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    return out.rsplit(":", 1)[-1].strip() if ":" in out else None


class Hazard1_TheGlobMustNotSilentlyEmpty(unittest.TestCase):
    """The public register list is built by globbing. If the files move and the glob does not,
    the page goes blank and nothing raises."""

    def test_the_public_register_list_is_not_empty(self):
        """THE tripwire. Fails the instant the documents move without the reader moving with
        them - which is the whole hazard, expressed as the one assertion that catches it."""
        regs = RR.preregistrations()
        self.assertGreater(len(regs), 20,
                           "the public research page's register list is empty or near-empty. If "
                           "PREREG_*.md has just moved, research_record.preregistrations() must move "
                           "with it IN THE SAME COMMIT (MB36's named hazard).")

    def test_the_reader_and_the_files_agree_on_where_they_live(self):
        """Not 'the list is non-empty' but 'the list is as long as the tree says it should be'.
        A partial move - some files relocated, some not - would leave a shorter list that the
        test above would still pass."""
        on_disk = glob.glob(os.path.join(ROOT, "PREREG_*.md"))
        on_disk += glob.glob(os.path.join(ROOT, "register", "PREREG_*.md"))
        listed = [r for r in RR.preregistrations() if r["file"].startswith("PREREG_")]
        self.assertEqual(len(listed), len(on_disk),
                         f"{len(on_disk)} PREREG files on disk but {len(listed)} listed on the "
                         "page - the reader and the files disagree about where they live")

    def test_the_tripwire_is_not_vacuous(self):
        """It must be able to FAIL. Point the same function at an empty tree and it must return
        nothing - otherwise the assertion above passes on something other than the real list.
        This project's most-repeated test defect is a guard that inspects nothing."""
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(RR.preregistrations(root=d), [],
                             "preregistrations() returned rows for an EMPTY directory, so the "
                             "non-empty assertion above proves nothing")


class Hazard2_TheUnionMergeRuleMustSurviveTheMove(unittest.TestCase):
    """`.gitattributes` keys the union-merge on the FILENAME. Moving into a folder is safe;
    dropping the prefix while moving is not, and it fails invisibly."""

    def test_handoffs_currently_resolve_to_union(self):
        got = _check_attr("HANDOFF_edge_audit.md")
        if got is None:
            _SKIPS.append("git check-attr unavailable")
            self.skipTest("git check-attr unavailable")
        self.assertEqual(got, "union",
                         "HANDOFF_*.md no longer resolves to merge=union - the protection that "
                         "keeps parallel lanes landing has been lost")

    def test_a_move_that_KEEPS_the_prefix_keeps_the_protection(self):
        got = _check_attr("handoff/HANDOFF_edge_audit.md")
        if got is None:
            self.skipTest("git check-attr unavailable")
        self.assertEqual(got, "union",
                         "moving into handoff/ WITH the prefix must keep union; if this fails "
                         "the move is unsafe in a way MB36 did not anticipate")

    def test_a_move_that_DROPS_the_prefix_silently_loses_it(self):
        """The measurement that makes hazard 2 a fact rather than a worry. This test asserts the
        DANGER exists, so it documents the constraint rather than merely hoping for it."""
        got = _check_attr("handoff/edge_audit.md")
        if got is None:
            self.skipTest("git check-attr unavailable")
        self.assertNotEqual(
            got, "union",
            "de-stuttered handoff paths now resolve to union - if .gitattributes has been "
            "updated to cover them, delete this test and say so; until then the constraint is "
            "that a move must KEEP the HANDOFF_ prefix")

    def test_the_register_files_have_no_merge_rule_either_way(self):
        """PREREG files are write-once and are not union-merged, so the move carries no
        gitattributes risk on that side. Pinned so the asymmetry is recorded rather than
        rediscovered."""
        got = _check_attr("PREREG_mb22_mb23_power_and_hodrick.md")
        if got is None:
            self.skipTest("git check-attr unavailable")
        self.assertIn(got, ("unspecified", "unset"),
                      "a merge rule has appeared on PREREG files; MB36's move analysis assumed "
                      "there was none")


class TheMoveIsNotDone(unittest.TestCase):
    """Recorded so nobody reads this file as evidence the move happened."""

    def test_the_documents_are_still_at_the_repo_root(self):
        n = len(glob.glob(os.path.join(ROOT, "PREREG_*.md")))
        self.assertGreater(n, 20,
                           "PREREG files are no longer at the root. If the move HAS been made, "
                           "this test should be updated in the same commit to assert the new "
                           "location - it exists to make the move visible, not to prevent it.")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (not counted as passes):")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
