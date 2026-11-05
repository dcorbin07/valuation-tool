"""Item 86's pre-fix control: run today's suites against the tree as it was.

Three fixes, three different "before" states, and the interesting one is the third:

  * the theme crawl REFUSED on an empty broker, so its new tests fail;
  * the LIVE CHECK had no due rule, so the previous session's scan and the previous session's
    signals feed both read as failures -- which is the pair of false alarms this item exists for;
  * **`test_proposal_auto_scan_themes` was ALREADY RED ON MAIN and nobody had found out**,
    because the last land gate ran 2026-10-28 and Don installed the workflows on 10-29. That one
    is not fixed by this item's new code at all; it is fixed by repointing two guards that item
    84B's design made wrong, and the control shows it red before and green after.

Sources are restored BYTE-FOR-BYTE from a pinned commit, never from `HEAD`, because `HEAD` moves
and a control measured against a moving baseline is measuring the clock. Binary I/O throughout:
a text round-trip rewrites CRLF and leaves the tree altered in exactly the files the control was
aimed at.

    python -m scripts.i86_before
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

#: The branch tip before item 86 touched anything. Pinned, not `HEAD`.
BASELINE = "a96243d"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Everything this item changed. A file absent at the baseline is removed for the run.
TOUCHED = (
    "scripts/live_check.py",
    "scripts/theme_cache_build.py",
    "tests/test_live_check.py",
    "tests/test_valreads.py",
    "tests/test_proposal_auto_scan_themes.py",
    "pending_workflows/valreads-record.yml",
)

#: Suites to score, and what each one is evidence about.
SUITES = (
    ("tests/test_item86.py", "this item's own tests"),
    ("tests/test_live_check.py", "the two false alarms"),
    ("tests/test_proposal_auto_scan_themes.py", "RED ON MAIN before this item"),
    ("tests/test_valreads.py", "the blind-register guard"),
)


def _git(*args):
    out = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    return out.stdout if out.returncode == 0 else None


def _score(path):
    r = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True)
    text = (r.stdout + r.stderr).decode("utf-8", "replace")
    m = re.search(r"Ran (\d+) tests?", text)
    ran = int(m.group(1)) if m else 0
    fails = len(re.findall(r"^(?:FAIL|ERROR):", text, re.M))
    if ran == 0:
        head = [ln for ln in text.strip().split("\n") if ln.strip()][-1:]
        return "could not run (%s)" % (head[0][:90] if head else "no output")
    return "ran %d, failed %d" % (ran, fails)


def main():
    saved = {}
    for rel in TOUCHED:
        p = os.path.join(REPO, rel)
        saved[rel] = open(p, "rb").read() if os.path.exists(p) else None

    print("=" * 94)
    print("AFTER  (the tree as it stands now)")
    print("=" * 94)
    after = {}
    for path, why in SUITES:
        after[path] = _score(path)
        print("  %-46s %-24s %s" % (path, after[path], why))

    try:
        for rel in TOUCHED:
            p = os.path.join(REPO, rel)
            was = _git("show", "%s:%s" % (BASELINE, rel))
            if was is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, "wb") as fh:
                    fh.write(was)
        print()
        print("=" * 94)
        print("BEFORE (every source restored from %s)" % BASELINE)
        print("=" * 94)
        for path, why in SUITES:
            print("  %-46s %-24s %s" % (path, _score(path), why))
    finally:
        for rel, was in saved.items():
            p = os.path.join(REPO, rel)
            if was is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, "wb") as fh:
                    fh.write(was)
        bad = [rel for rel, was in saved.items()
               if (open(os.path.join(REPO, rel), "rb").read()
                   if os.path.exists(os.path.join(REPO, rel)) else None) != was]
        print()
        print("  sources restored byte-for-byte: %s" % ("yes" if not bad else "NO -- %s" % bad))
        if bad:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
