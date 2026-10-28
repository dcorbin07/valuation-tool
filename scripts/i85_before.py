"""Item 85's pre-fix control: run the new suite against the tree as it was, and show the defect.

Two halves, because the counting half alone would be uninformative here. `scripts/
install_workflows.py` did not exist before this item, so restoring the old tree makes
`tests/test_item85.py` fail at IMPORT and every test errors -- a true figure that says nothing
about which rule changed. So this script also reproduces the OLD installer's source selection
directly, from the folder it actually ran in, and names the files it would have installed.

Sources are restored BYTE-FOR-BYTE from a pinned commit, never from `HEAD`: `HEAD` moves, and a
control measured against a moving baseline is measuring the clock. Binary I/O throughout, because
a text round-trip rewrites CRLF and leaves the tree altered in exactly the files the control was
aimed at -- a mutation harness that cannot put a file back is worse than none.

    python -m scripts.i85_before
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

#: The branch tip before item 85 touched anything. Pinned, not `HEAD`.
BASELINE = "0f0b85a"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Files this item changed or added. A file absent at the baseline is REMOVED for the run and
#: restored afterwards, which is what "the tree as it was" means.
TOUCHED = (
    "install_workflows.bat",
    "scripts/install_workflows.py",
    "update_main.bat",
)

SUITE = "tests/test_item85.py"


def _git(*args):
    out = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    return out.stdout if out.returncode == 0 else None


def _baseline_bytes(rel):
    return _git("show", "%s:%s" % (BASELINE, rel))


def the_old_rule_would_have_installed(folder):
    """The old bat's source selection, reproduced: `%~dp0pending_workflows\\*.yml`.

    This is the whole defect in one function. It takes no reference to origin/main, to the repo
    it belongs to, or to what is already installed -- only to the folder the file sits in.
    """
    out = []
    for sub in ("pending_workflows", os.path.join("data", "pending_workflows")):
        d = os.path.join(folder, sub)
        if os.path.isdir(d):
            out += [f for f in sorted(os.listdir(d)) if f.endswith(".yml")]
    return out


def main():
    print("=" * 94)
    print("HALF ONE -- the old rule, run from the folder the accident ran from")
    print("=" * 94)
    worktrees = os.path.join(REPO, "..")
    dipcall = os.path.normpath(os.path.join(worktrees, "dipcall"))
    if os.path.isdir(dipcall):
        would = the_old_rule_would_have_installed(dipcall)
        print("  folder : %s" % dipcall)
        print("  it would have installed: %s" % (", ".join(would) or "(nothing)"))
        print("  ad29600 installed      : fleet-cycle.yml, live-cycle.yml")
        print("  the old rule reproduces the accident: %s"
              % (sorted(would) == ["fleet-cycle.yml", "live-cycle.yml"]))
    else:
        print("  (the dipcall worktree is gone, so this half cannot be measured here)")

    print()
    print("  and the new rule, on the same folder:")
    sys.path.insert(0, REPO)
    from scripts import install_workflows as IW
    why = IW.refuse_reason(dipcall)
    print("    %s" % (("REFUSED: " + why) if why else "ACCEPTED -- the guard does not bite"))

    print()
    print("=" * 94)
    print("HALF TWO -- the new suite against the pre-fix tree")
    print("=" * 94)
    saved = {}
    for rel in TOUCHED:
        p = os.path.join(REPO, rel)
        saved[rel] = open(p, "rb").read() if os.path.exists(p) else None
    try:
        for rel in TOUCHED:
            p = os.path.join(REPO, rel)
            was = _baseline_bytes(rel)
            if was is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, "wb") as fh:
                    fh.write(was)
        res = subprocess.run([sys.executable, SUITE], cwd=REPO, capture_output=True)
        text = (res.stdout + res.stderr).decode("utf-8", "replace")
        m = re.search(r"Ran (\d+) tests?", text)
        ran = int(m.group(1)) if m else 0
        fails = len(re.findall(r"^(?:FAIL|ERROR):", text, re.M))
        if ran == 0:
            print("  the suite could not even be imported, which is the honest pre-fix result:")
            for ln in text.strip().split("\n")[-4:]:
                print("    %s" % ln)
            print("  -> 0 of this item's 23 tests could run before the fix")
        else:
            print("  ran %d, failed %d" % (ran, fails))
    finally:
        for rel, was in saved.items():
            p = os.path.join(REPO, rel)
            if was is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, "wb") as fh:
                    fh.write(was)
        # Byte-for-byte, asserted rather than hoped for.
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
