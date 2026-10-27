"""Item 83's pre-fix control: how many of its tests fail against the tree as it was.

THE BASELINE IS A COMMITTED SHA, NOT `HEAD` -- reading `HEAD` is correct exactly once, because
the moment the fix lands `HEAD` IS the fix and the control reports that the suite pins nothing.

`bc5fd24` is item 81, the last commit before items 82 and 83.

IT ALSO RESTORES `tests/test_item67.py`, and that is the point of including it: four of item 67's
guards asserted the OLD budget rule and FIRED when it changed. They are repointed in the same
commit (`MA59`), so this control shows both directions -- item 83's tests fail against the old
code, and item 67's repointed tests fail against it too, which is what proves the repoint was a
real change of rule rather than a loosening.

Binary I/O throughout, so restoring a CRLF source cannot rewrite it on the way back.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = "bc5fd24"
SOURCES = ("valuation/edge/settlement.py",
           "valuation/edge/live_cycle.py")
SUITES = ("tests/test_item83.py", "tests/test_item67.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, b):
    with open(p, "wb") as f:
        f.write(b)


def _baseline(rel):
    out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (BASELINE, rel)],
                         capture_output=True)
    if out.returncode:
        raise SystemExit("cannot read %s:%s -- %s" % (BASELINE, rel, out.stderr[:200]))
    return out.stdout


def _run(suite):
    out = subprocess.run([sys.executable, suite], cwd=REPO,
                         capture_output=True, text=True, errors="replace")
    tail = (out.stderr or "").strip().splitlines()
    ran = bad = 0
    for line in tail:
        if line.startswith("Ran "):
            ran = int(line.split()[1])
        if line.startswith("FAILED"):
            for part in line[line.find("(") + 1:line.rfind(")")].split(", "):
                k, _, v = part.partition("=")
                if k in ("failures", "errors"):
                    bad += int(v)
    names = [ln.split(" ")[1] for ln in tail
             if ln.startswith("FAIL: ") or ln.startswith("ERROR: ")]
    return out.returncode, ran, bad, names


def main():
    saved = {rel: _read(os.path.join(REPO, rel)) for rel in SOURCES}
    try:
        for rel in SOURCES:
            _write(os.path.join(REPO, rel), _baseline(rel))
        for suite in SUITES:
            rc, ran, bad, names = _run(suite)
            print("PRE-FIX  %-26s %d of %d fail (exit %s)" % (suite, bad, ran, rc))
            for n in sorted(names):
                print("     %s" % n)
    finally:
        for rel, b in saved.items():
            _write(os.path.join(REPO, rel), b)
        for rel, b in saved.items():
            assert _read(os.path.join(REPO, rel)) == b, "NOT RESTORED: " + rel
        print("sources restored byte-for-byte")
    worst = 0
    for suite in SUITES:
        rc, ran, bad, _ = _run(suite)
        print("POST-FIX %-26s %d of %d fail (exit %s)" % (suite, bad, ran, rc))
        worst = max(worst, bad, rc)
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
