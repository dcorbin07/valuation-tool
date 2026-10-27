"""Item 84's pre-fix control: how many of its tests fail against the tree as it was.

THE BASELINE IS A COMMITTED SHA, NOT `HEAD` -- reading `HEAD` is right exactly once, because the
moment the fix lands `HEAD` IS the fix and the control reports that the suite pins nothing.

`62d68a4` is item 82's correction note, the last commit before item 84.

`pending_workflows/auto-scan.yml` IS RESTORED TOO, deliberately: Part B's change is to a file
Don installs by hand, and a control that left it in place would report its tests as passing
pre-fix and understate what moved.

Binary I/O throughout, so restoring a CRLF source cannot rewrite it on the way back.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = "62d68a4"
SOURCES = ("valuation/edge/sharadar_freeze.py",
           "valuation/edge/valquo_index.py",
           "scripts/refresh_backtest_from_freeze.py",
           "pending_workflows/auto-scan.yml")
#: `valuation/screener/scan_catchup.py` is NEW, so there is nothing to restore -- every test
#: that imports it would fail at import against the baseline, which is why the suite is run
#: with the module left in place and the count below is about the four changed files.
SUITE = os.path.join("tests", "test_item84.py")


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
    out = subprocess.run([sys.executable, SUITE], cwd=REPO,
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
