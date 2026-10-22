# -*- coding: utf-8 -*-
"""ITEM 79 — THE CONTROL: run item 79's reproductions against the PRE-FIX sources.

**WHY THIS EXISTS.** `tests/test_item79.py` asserts that no fair value below half the price is
labelled "high confidence" and that Amendment 4 is dormant until its row says YES. Both pass on
the tree that ships them -- which is what a test asserting the implementation's own behaviour
would also do. The control is to run the identical cases against the sources as they were BEFORE
item 79 and require them to fail. `scripts/i78_before.py` does the same for item 78.

    python -m scripts.i79_before            # resolves the baseline itself; see `_baseline`

**IT SPLITS THE FAILURES TWO WAYS, and the split is the honest part.** A case that fails because
the old behaviour was wrong is strong evidence. A case that fails because the function or the
constant it names did not exist yet proves only that the test is new. Both are reported by name.

**AMENDMENT 4's SECTION IS EXPECTED TO BE MOSTLY NEW-SYMBOL, and that is not a weakness: an
amendment drafted behind a signature row is additive by construction.** Its load-bearing claim
is the opposite one -- that the UNSIGNED state is unchanged -- and that is pinned in the suite
itself (`AmendmentFourIsDraftedAndDormant`) rather than here, because the pre-fix tree has no
signature row to read.

It writes nothing outside the temporary directory, contacts no network and places no order.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

#: Everything item 79 changed, including the contract itself -- the amendment's text IS the
#: switch, so rolling the sources back without it would leave a signature row with no reader.
SOURCES = ("valuation/engine/publication.py",
           "valuation/engine/blend.py",
           "valuation/engine/scoring.py",
           "valuation/engine/pipeline.py",
           "valuation/web/withhold.py",
           "valuation/web/app.py",
           "valuation/web/dip.py",
           "valuation/web/unified.py",
           "valuation/edge/track_meter.py",
           "valuation/screener/rebalance_watch.py",
           "scripts/ci_scan.py",
           "PAPER_TRACK_CONTRACT.md")

#: **EXPECTED TO PASS ON BOTH TREES, and each says why.** One that started failing on the OLD
#: tree would mean the control had drifted into asserting the new behaviour twice.
PASS_ON_BOTH = {
    "test_the_served_figures_come_from_the_tracked_module":
        "`index_book_measured` is NOT in SOURCES -- item 79 reads its figures and does not "
        "touch it. If this ever fails, the served cost pair moved and the amendment's own "
        "number is stale",
    "test_and_NEITHER_DOES_ANY_FROZEN_METER_PARAMETER":
        "sigma, rho, alpha and the cost drag are the things the amendment must NOT move, so "
        "they read the same on both trees. That is the point of the test",
}

#: **A CLAIM I MADE AND THE CONTROL REFUTED, kept because the correction is the useful part.**
#: `test_the_VERDICT_DATE_DOES_NOT_MOVE` was listed above as passing on both trees, on the
#: reasoning that 60-months-on-the-vintage is a pre-existing property. It is -- and the test
#: also reads `gate_window(path)` to show the gate moved while the verdict did not, so on a tree
#: with no `gate_window` it cannot run at all. A control has to be satisfiable by the old tree
#: to be a control, and half of this one is not. It is classified as new-symbol, which is
#: accurate, and the pre-existing half of its property is covered by
#: `test_and_NEITHER_DOES_ANY_FROZEN_METER_PARAMETER` above.
NOT_A_CONTROL_AFTER_ALL = ("test_the_VERDICT_DATE_DOES_NOT_MOVE",)

_ABSENCE = re.compile(r"(AttributeError: module|has no attribute|"
                      r"TypeError: [\w.]+\(\) got an unexpected keyword|"
                      r"ImportError: cannot import name|"
                      r"cannot import name|KeyError: 'price_ratio_cap')")


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _baseline(repo):
    """Which revision is "before item 79" -- DERIVED, never a hard-coded `HEAD~1`.

    `HEAD~1` is right only while item 79 is the tip; one commit later the default is silently
    the wrong tree, the control reports nothing, and that reads as *"these tests mirror the
    implementation"* rather than as *"you pointed it at the wrong commit"*.
    """
    dirty = subprocess.run(["git", "diff", "--name-only", "HEAD", "--"] + list(SOURCES),
                           cwd=repo, capture_output=True)
    return "HEAD" if (dirty.stdout or b"").strip() else "HEAD~1"


def main(rev=None):
    repo = _repo()
    rev = rev or _baseline(repo)
    tmp = tempfile.mkdtemp(prefix="i79_before_")
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
        r = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_item79"],
                           cwd=tmp, capture_output=True)
        text = (r.stdout + r.stderr).decode("utf-8", "replace")
        failed, absence = [], {}
        for b in text.split("=" * 70):
            m = re.search(r"^(FAIL|ERROR): (\w+)", b.strip(), re.M)
            if not m:
                continue
            failed.append(m.group(2))
            hit = _ABSENCE.search(b)
            if hit:
                absence[m.group(2)] = hit.group(1)[:60]
        failed = sorted(set(failed))
        ran = text.rsplit("Ran ", 1)[-1].split(" ")[0] if "Ran " in text else "?"
        subj = subprocess.run(["git", "log", "-1", "--format=%h %s", rev],
                              cwd=repo, capture_output=True)
        print("sources rolled back to %s  (%s)"
              % (rev, subj.stdout.decode("utf-8", "replace").strip() or "unknown"))
        print("ran %s tests; %d FAILED on the pre-item-79 tree" % (ran, len(failed)))
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
            print("WARNING: nothing failed on BEHAVIOUR, so these tests mirror the "
                  "implementation rather than checking it.")
            return 1
        return 0
    finally:
        shutil.rmtree(tmp, True)


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:] or [])))
