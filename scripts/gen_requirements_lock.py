"""Regenerate the hashed dependency locks (master audit MA12).

WHY THIS EXISTS. `requirements.txt` declares every dependency with `>=` and nothing else.
CI pip-installs it on every land and every scheduled scan, and Render's Docker build installs
`requirements-saas.txt`, so the versions that score stocks and bill customers were whatever
PyPI happened to serve that minute -- with no human step anywhere in the chain. That is OOB2's
failure class (a vendor field changed shape and a substituted default produced a 91 Strong Buy)
moved down into the dependency layer.

MEASURED 2026-08-15, and this is why the item is not theoretical: seven of the eleven direct
requirements resolve TODAY to a HIGHER MAJOR VERSION than the floor they were written against --
numpy 2.2.6 (`>=1.24`), yfinance 1.6.0 (`>=0.2.40`), stripe 15.5.0 (`>=9.0`), gunicorn 26.0.0
(`>=21.0`), pypdf 6.16.1 (`>=5.0`), reportlab 5.0.0 (`>=4.0`), anthropic 0.122.0 (`>=0.34`).

TWO LOCKS, DELIBERATELY, AND THE REASON IS A BEHAVIOUR RISK RATHER THAN TIDINESS. CI installs
`requirements.txt`; the container installs `requirements-saas.txt`, which adds stripe and
gunicorn. Locking both from the saas superset would have ADDED stripe to the CI environment, and
`valuation/saas/billing.py` imports stripe inside `try:` blocks in three request handlers -- so
a suite exercising one of those paths could take a different branch purely because the lock made
the import succeed. Pinning must not change what CI runs, so the two sets stay separate.

THE LOCKS ARE PLATFORM-SPECIFIC AND THAT IS INTENTIONAL, NOT AN OVERSIGHT. They are resolved for
linux x86_64 / CPython 3.11 -- which is what BOTH consumers are (`ubuntu-latest` with
`python-version: '3.11'`, and `FROM python:3.11-slim`). They will NOT install on Windows or on
another Python minor, and they are not meant to: `requirements.txt` remains the human entry
point for local development. `tests/test_requirements_lock.py` pins that separation so nobody
"helpfully" points `run.bat` at a lock that cannot resolve on the machine running it.

USAGE (needs network; run it when a dependency is deliberately upgraded):
    python scripts/gen_requirements_lock.py
Then read the diff. A version moving is a decision, and the diff is where it becomes visible --
which is the entire point of the exercise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Both consumers are linux/x86_64 + CPython 3.11. Keep these three in step with
# `.github/workflows/*.yml` (`python-version`) and `Dockerfile` (`FROM python:3.11-slim`);
# tests/test_requirements_lock.py fails if the workflow and this constant disagree.
PY_VERSION = "3.11"
PLATFORM = "manylinux2014_x86_64"

PAIRS = [
    ("requirements.txt", "requirements.lock.txt",
     "the CORE set -- installed by .github/workflows/land-agent-branch.yml and auto-scan.yml"),
    ("requirements-saas.txt", "requirements-saas.lock.txt",
     "the PRODUCTION set -- installed by Dockerfile (Render). Core + stripe + gunicorn."),
]

HEADER = """\
# ============================================================================
#  {out} -- GENERATED. Do not hand-edit.
#
#  {what}
#
#  Regenerate with:  python scripts/gen_requirements_lock.py
#  Source of truth for WHICH packages:  {src}
#  Resolved for:  CPython {py} / linux {plat}  (see the script's docstring --
#  this lock deliberately does NOT install on Windows; use {src} there).
#
#  Master audit MA12. Every line is exact-pinned and hash-checked, so
#  `pip install --require-hashes` refuses anything that is not byte-for-byte
#  the artifact this lock was resolved against.
# ============================================================================
"""


def resolve(src: str) -> list[tuple[str, str, str]]:
    """Return sorted (name, version, sha256) for the full transitive closure of `src`."""
    with tempfile.TemporaryDirectory() as td:
        report = os.path.join(td, "report.json")
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--dry-run", "--quiet",
            "--report", report,
            "--only-binary=:all:",
            "--python-version", PY_VERSION,
            "--platform", PLATFORM,
            "--target", os.path.join(td, "tgt"),
            "-r", os.path.join(REPO, src),
        ]
        subprocess.run(cmd, check=True)
        with open(report, encoding="utf-8") as fh:
            data = json.load(fh)

    out: list[tuple[str, str, str]] = []
    for item in data["install"]:
        meta = item["metadata"]
        hashes = item.get("download_info", {}).get("archive_info", {}).get("hashes", {})
        sha = hashes.get("sha256")
        if not sha:
            # Never emit a partial lock: a line without a hash makes the whole file
            # unusable with --require-hashes, and a lock that silently drops a package
            # is worse than no lock at all.
            raise SystemExit(f"no sha256 for {meta['name']} {meta['version']} in {src}")
        out.append((meta["name"].lower().replace("_", "-"), meta["version"], sha))
    return sorted(out)


def main() -> int:
    for src, out, what in PAIRS:
        pkgs = resolve(src)
        lines = [HEADER.format(out=out, what=what, src=src, py=PY_VERSION, plat=PLATFORM)]
        for name, ver, sha in pkgs:
            lines.append(f"{name}=={ver} \\\n    --hash=sha256:{sha}\n")
        with open(os.path.join(REPO, out), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(lines))
        print(f"{out}: {len(pkgs)} packages pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
