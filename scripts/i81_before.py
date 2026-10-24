"""Item 81's pre-fix control: how many of its tests fail against the tree as it was.

A test suite that passes both before and after a change has not pinned the change. This
restores the four changed sources from `HEAD`, runs `tests/test_item81.py` against them, puts
them back BYTE-FOR-BYTE, and reports the count.

BINARY I/O THROUGHOUT, deliberately. A harness that reads and writes text with `newline`
forced to LF rewrites a CRLF source on the way back, and then fails its own byte-for-byte
check *after* the mutation has run -- leaving the tree altered in exactly the files it was
aimed at. That cost a previous session a recovery from git.

THE RUNBOOK IS A NEW FILE AND IS NOT RESTORED, so the `TheRunbook` tests pass in both
directions. That is honest rather than convenient: this control measures the CODE changes, and
a document's tests are tripwires on its content, not on a behaviour that moved.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ("valuation/edge/bulk.py",
           "valuation/edge/data_providers.py",
           "valuation/edge/valquo_index.py",
           "valuation/edge/sharadar_freeze.py")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, b):
    with open(p, "wb") as f:
        f.write(b)


def _head(rel):
    out = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + rel],
                         capture_output=True)
    if out.returncode:
        raise SystemExit("cannot read HEAD:%s -- %s" % (rel, out.stderr[:200]))
    return out.stdout


def _run():
    out = subprocess.run([sys.executable, os.path.join("tests", "test_item81.py")],
                         cwd=REPO, capture_output=True, text=True, errors="replace")
    tail = (out.stderr or "").strip().splitlines()
    ran = fails = errs = 0
    for line in tail:
        if line.startswith("Ran "):
            ran = int(line.split()[1])
        if line.startswith("FAILED"):
            for part in line[line.find("(") + 1:line.rfind(")")].split(", "):
                k, _, v = part.partition("=")
                if k == "failures":
                    fails = int(v)
                elif k == "errors":
                    errs = int(v)
    names = [ln.split(" ")[1] for ln in tail
             if ln.startswith("FAIL: ") or ln.startswith("ERROR: ")]
    return out.returncode, ran, fails + errs, names


def main():
    saved = {rel: _read(os.path.join(REPO, rel)) for rel in SOURCES}
    try:
        for rel in SOURCES:
            _write(os.path.join(REPO, rel), _head(rel))
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
