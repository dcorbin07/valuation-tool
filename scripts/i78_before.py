# -*- coding: utf-8 -*-
"""ITEM 78 — THE CONTROL: run item 78's reproductions against the PRE-FIX sources.

**WHY THIS EXISTS.** `tests/test_item78.py` asserts that the paper slot reads its whole order
history, that the privacy filter posts the warning saying it could not, that a 0% slot holding
nothing needs no prices, that a run which evaluated nothing clears nothing, and that a permanent
gap is announced once. All of them pass on the tree that ships them -- which is what a test
asserting the implementation's own behaviour would also do. The control is to run the identical
cases against the sources as they were BEFORE item 78 and require them to fail.
`scripts/i77_before.py` does the same for item 77 and this follows it.

    python -m scripts.i78_before            # resolves the baseline itself; see `_baseline`

**IT DISTINGUISHES TWO KINDS OF FAILURE, and the distinction is the honest part.** A case that
fails on the old tree because the behaviour was wrong is strong evidence. A case that fails
because the keyword or the constant it names did not exist yet is weaker -- it proves the test is
new, not that the old code was broken. Both are reported, separately and by name, so nobody
reads an `AttributeError` as a measured defect.

It writes nothing outside the temporary directory and places no order: every HTTP reply in those
tests is a recorded fixture.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

#: The modules item 78 changed.
SOURCES = ("valuation/edge/live_cycle.py",
           "valuation/edge/live_notify.py",
           "valuation/edge/live_slots.py",
           "valuation/edge/settlement.py",
           "valuation/saas/alert_routing.py",
           "valuation/saas/app_saas.py",
           "valuation/screener/rebalance_watch.py")

#: **EXPECTED TO PASS ON BOTH TREES, and each one says why.** A test here that started failing
#: on the OLD tree would mean the control had drifted into asserting the new behaviour twice.
PASS_ON_BOTH = {
    "test_the_510_IS_NOT_NESTING_AND_NO_nested_PARAMETER_IS_SENT":
        "the pager never sent `nested` on either tree -- the point is that 510 is a TOTAL, so "
        "this is the negative evidence for the brief's nesting question and not a repair",
    "test_a_FAILED_second_page_still_REFUSES":
        "the refusal item 78 had to KEEP. If this ever fails, the fix went too far",
    "test_an_UNPAGED_client_keeps_the_full_page_refusal":
        "the length check still means what it says where it is still true",
    "test_a_whole_page_sharing_ONE_timestamp_still_refuses":
        "the one read that genuinely cannot be resumed from. Both cursors refuse it, so this "
        "is the intersection of the old rule and the new one",
    "test_a_REAL_return_claim_is_still_blocked":
        "the control on the word-boundary change: narrowing a filter must not open it",
    "test_a_variable_NAME_is_never_blocked":
        "a value-based scrubber never blocked a bare name -- which is why the brief's guess "
        "that `paper_client_absent` was the blocked line is measured WRONG rather than fixed",
}

#: Failing on the old tree because the symbol did not exist yet is not evidence about behaviour.
_ABSENCE = re.compile(r"(TypeError: [\w.]+\(\) got an unexpected keyword|"
                      r"TypeError: [\w.]+\(\) takes|AttributeError: module|"
                      r"KeyError: 'price_only'|KeyError: 'unpriced'|"
                      r"AttributeError: .*has no attribute)")


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _baseline(repo):
    """Which revision is "before item 78" -- DERIVED, never a hard-coded `HEAD~1`.

    `HEAD~1` is right only while item 78 is the tip. Run it one commit later and the default is
    silently the wrong tree, the control reports zero failures, and that reads as *"these tests
    mirror the implementation"* rather than as *"you pointed it at the wrong commit"*. So: if the
    working tree still carries item 78's edits, the baseline is `HEAD`; once they are committed
    it is the commit before them.
    """
    dirty = subprocess.run(["git", "diff", "--name-only", "HEAD", "--"] + list(SOURCES),
                           cwd=repo, capture_output=True)
    if (dirty.stdout or b"").strip():
        return "HEAD"
    return "HEAD~1"


def main(rev=None):
    repo = _repo()
    rev = rev or _baseline(repo)
    tmp = tempfile.mkdtemp(prefix="i78_before_")
    try:
        for name in os.listdir(repo):
            if name in (".git", ".claude"):
                continue
            src, dst = os.path.join(repo, name), os.path.join(tmp, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(src, dst)
        for rel in SOURCES:
            blob = subprocess.run(["git", "show", "%s:%s" % (rev, rel)],
                                  cwd=repo, capture_output=True)
            if blob.returncode != 0:
                print("could not read %s at %s" % (rel, rev))
                return 2
            # BYTES, not text: decoding git's output as the console codepage is how a Windows
            # run manufactures a diff that is not there.
            with open(os.path.join(tmp, rel), "wb") as fh:
                fh.write(blob.stdout)
        r = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_item78"],
                           cwd=tmp, capture_output=True)
        text = (r.stdout + r.stderr).decode("utf-8", "replace")
        blocks = text.split("=" * 70)
        failed, absence = [], {}
        for b in blocks:
            m = re.search(r"^(FAIL|ERROR): (\w+)", b.strip(), re.M)
            if not m:
                continue
            failed.append(m.group(2))
            hit = _ABSENCE.search(b)
            if hit:
                absence[m.group(2)] = hit.group(1)[:70]
        failed = sorted(set(failed))
        ran = text.rsplit("Ran ", 1)[-1].split(" ")[0] if "Ran " in text else "?"
        subj = subprocess.run(["git", "log", "-1", "--format=%h %s", rev],
                              cwd=repo, capture_output=True)
        print("sources rolled back to %s  (%s)"
              % (rev, subj.stdout.decode("utf-8", "replace").strip() or "unknown"))
        print("ran %s tests; %d FAILED on the pre-item-78 tree" % (ran, len(failed)))
        print()
        behaviour = [n for n in failed if n not in absence]
        print("  BEHAVIOUR was wrong on the old tree (%d):" % len(behaviour))
        for n in behaviour:
            print("    FAILS (as it must):", n)
        print()
        print("  the SYMBOL did not exist yet, so the failure is weaker evidence (%d):"
              % len(absence))
        for n in sorted(absence):
            print("    new-symbol:", n, "--", absence[n])
        print()
        unexpected = [n for n in PASS_ON_BOTH if n in failed]
        for name, why in sorted(PASS_ON_BOTH.items()):
            print("  %-16s %s\n      %s"
                  % ("DRIFTED" if name in failed else "passes on both", name, why))
        if unexpected:
            print()
            print("WARNING: a control that should pass on both trees FAILED: %r" % unexpected)
            return 1
        if not behaviour:
            print()
            print("WARNING: nothing failed on BEHAVIOUR, so these tests are a mirror of the "
                  "implementation rather than a check on it.")
            return 1
        return 0
    finally:
        shutil.rmtree(tmp, True)


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:] or [])))
