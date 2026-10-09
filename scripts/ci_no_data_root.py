# -*- coding: utf-8 -*-
"""Run a suite as a CI RUNNER sees it: with NO licensed data root at all.

    python -m scripts.ci_no_data_root tests/test_foo.py [tests/test_bar.py ...]
    python -m scripts.ci_no_data_root --all

**WHY THIS EXISTS, AND IT IS MEASURED RATHER THAN ANTICIPATED.** `data/` is gitignored, so on a
runner it is absent — and this project has now lost **two** lands to suites that pass locally and
ERROR there:

* `CORRECTED-FLOORS` part 1 — a module resolved its data root at **IMPORT** time, so
  `import scripts.corrected_floors` raised and every test touching it errored.
* `CORRECTED-CLAIMS-2` — the paths were lazy, but `fa()` still **RAISES** at **CALL** time, so
  two gated helpers errored before they could return their own "not available" state. Eight
  reported skips became eight ERRORS. **Making a path lazy moves the exception from import time
  to call time; it does not remove it.**

**THE RULE BOTH FAILURES TEACH: A HELPER THAT REPORTS ITS OWN INABILITY MUST DO SO AS A STATE,
NOT BY RAISING.** And the corollary for tests: skip LOUDLY. A test that passes *because* the data
is absent is the vacuous pass this record keeps finding, which is why every skip here prints.

**WHY AN ENVIRONMENT VARIABLE CANNOT DO THIS.** `index_best.data_candidates()` always appends the
derived primary root, so `VALQUO_DATA_ROOT` only PREPENDS a candidate and the real root still
resolves on a developer machine. The only faithful reproduction is to patch the candidate list to
EMPTY before the suite imports anything, which is what this does. **A suite that passes locally
is not a suite that passes CI, and now there is one command that tells you which.**

It is a developer tool and nothing imports it: it changes no behaviour, writes nothing, and
touches no artifact.
"""
from __future__ import annotations

import glob
import os
import runpy
import subprocess
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_one(target: str) -> int:
    """Each suite in its OWN process, because the patch is global and a suite that mutates
    `sys.modules` would otherwise leak into the next one — and because `RUN_RULES` judges a suite
    by its own exit code."""
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--child", target],
                          cwd=_HERE).returncode


def _child(target: str) -> int:
    # THE TARGET'S OWN DIRECTORY GOES ON `sys.path` FIRST, exactly as the interpreter does for
    # `python tests/x.py`. `runpy.run_path` does NOT do this, so any suite importing a sibling by
    # bare name (`import state_isolation`) raised ModuleNotFoundError -- and the first sweep
    # reported **12 suites failing** that were my harness rather than CI. A simulator that is
    # HARSHER than the thing it simulates produces false positives, which is worse than no
    # simulator: I nearly published those 12 as a CI finding.
    sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.join(_HERE, target))))
    sys.path.insert(0, _HERE)
    os.chdir(_HERE)
    import scripts.index_best as IB
    # EMPTY, not a bogus path: a nonexistent directory still lets the DERIVED primary root
    # resolve, so the condition would not reproduce.
    IB.data_candidates = lambda: []
    IB.DATA = None
    IB.FA = None
    sys.argv = [target]
    try:
        runpy.run_path(os.path.join(_HERE, target), run_name="__main__")
    except SystemExit as e:
        return int(e.code or 0)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--child":
        return _child(argv[1])
    if argv == ["--all"]:
        argv = sorted(os.path.relpath(p, _HERE).replace("\\", "/")
                      for p in glob.glob(os.path.join(_HERE, "tests", "test_*.py")))
    if not argv:
        print(__doc__)
        return 2
    bad = []
    for t in argv:
        rc = _run_one(t)
        print("  %-6s %s" % ("OK" if rc == 0 else "FAILED", t), flush=True)
        if rc != 0:
            bad.append(t)
    print("\n%d suite(s), %d failing with NO data root" % (len(argv), len(bad)))
    for b in bad:
        print("  FAIL " + b)
    if bad:
        print("\nThese pass locally and would ERROR on a runner. The fix is NOT to skip the "
              "check: make the helper report its inability as a STATE rather than raising, and "
              "make the test skip LOUDLY.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
