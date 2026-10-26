"""Item 82's pre-fix control: how many of its tests fail against the tree as it was.

A test suite that passes both before and after a change has not pinned the change.

THE BASELINE IS A COMMITTED SHA, NOT `HEAD`. Reading `HEAD` is correct exactly once -- the
moment the fix lands, `HEAD` IS the fix and a control reports "0 fail", i.e. that the suite pins
nothing, which a later session would read and believe. That cost item 81 a second commit.

`bc5fd24` is item 81, the last commit before item 82. Measured against it on 2026-10-26:
**10 of 12 failing**.

Binary I/O throughout, so restoring a CRLF source cannot rewrite it on the way back.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = "bc5fd24"
SOURCES = ("scripts/live_check.py",)


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


def _run():
    out = subprocess.run([sys.executable, os.path.join("tests", "test_item82.py")],
                         cwd=REPO, capture_output=True, text=True, errors="replace")
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
        rc, ran, bad, names = _run()
        print("PRE-FIX: %d of %d tests fail (exit %s)" % (bad, ran, rc))
        for n in sorted(names):
            print("   %s" % n)
    finally:
        for rel, b in saved.items():
            _write(os.path.join(REPO, rel), b)
        for rel, b in saved.items():
            assert _read(os.path.join(REPO, rel)) == b, "NOT RESTORED: " + rel
        print("sources restored byte-for-byte")
    rc, ran, bad, _ = _run()
    print("POST-FIX: %d of %d tests fail (exit %s)" % (bad, ran, rc))
    return 0 if (rc == 0 and bad == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
