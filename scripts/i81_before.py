"""Item 81's pre-fix control: how many of its tests fail against the tree as it was.

A test suite that passes both before and after a change has not pinned the change. This
restores the five changed sources from `HEAD`, runs `tests/test_item81.py` against them, puts
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

#: THE BASELINE IS A COMMITTED SHA, NOT `HEAD`, AND THAT IS NOT PEDANTRY.
#:
#: This read `HEAD` while item 81 was uncommitted, which is correct exactly once -- the
#: moment the fix lands, `HEAD` IS the fix and the control comes back "0 of 46 fail", i.e.
#: it reports that the tests pin nothing. A later session would read that and believe it.
#:
#: `d674186` is item 80b, the commit immediately before item 81, and the measurement taken
#: against it on 2026-10-24 was **34 of 46 failing**. Pinning the SHA means that number stays
#: reproducible however many commits land on top -- `MA13`'s committed-literal idiom.
BASELINE = "d674186"
SOURCES = ("valuation/edge/bulk.py",
           "valuation/edge/data_providers.py",
           "valuation/edge/valquo_index.py",
           "valuation/edge/sharadar_freeze.py",
           "refresh_sharadar.bat")


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
