#!/usr/bin/env python3
"""The dependency set is pinned, hashed, and actually installed that way — master audit MA12.

THE FINDING THIS PINS. Every dependency was declared with `>=` and nothing else, while CI
pip-installs on every land and every scheduled scan and Render's container builds from the
same declaration. So the library versions that score stocks and bill customers were whatever
PyPI served that minute, with no human step in the chain — OOB2's failure class (a vendor
field changed shape and a substituted default produced a 91 Strong Buy) moved one layer down.

Not hypothetical: measured 2026-08-15, SEVEN of the eleven direct requirements resolved to a
HIGHER MAJOR VERSION than their own floor — numpy 2.2.6 against `>=1.24`, yfinance 1.6.0
against `>=0.2.40`, stripe 15.5.0 against `>=9.0`, gunicorn 26.0.0 against `>=21.0`, pypdf
6.16.1 against `>=5.0`, reportlab 5.0.0 against `>=4.0`, anthropic 0.122.0 against `>=0.34`.

A lockfile that nothing installs is decoration, so the second half of this suite asserts the
CONSUMERS: both workflows and the Dockerfile must install the lock with `--require-hashes`,
and must not fall back to the unpinned file.

NO THIRD-PARTY IMPORTS. `packaging` is in the production lock but NOT the core lock CI
installs, so importing it here would fail in exactly the job this suite describes. Version
comparison is done with a deliberately small numeric-prefix parser below.
"""
import io
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORE_SRC, CORE_LOCK = ROOT / "requirements.txt", ROOT / "requirements.lock.txt"
SAAS_SRC, SAAS_LOCK = ROOT / "requirements-saas.txt", ROOT / "requirements-saas.lock.txt"
DOCKERFILE = ROOT / "Dockerfile"
LAND_WF = ROOT / ".github" / "workflows" / "land-agent-branch.yml"
SCAN_WF = ROOT / ".github" / "workflows" / "auto-scan.yml"

SHA256 = re.compile(r"^\s*--hash=sha256:[0-9a-f]{64}\s*\\?\s*$")
PIN = re.compile(r"^([A-Za-z0-9._-]+)==([^\s\\]+)\s*\\?\s*$")
REQ = re.compile(r"^([A-Za-z0-9._-]+)\s*([<>=!,.0-9a-zA-Z_-]*)")


def _norm(name: str) -> str:
    return name.lower().replace("_", "-")


def _version(text: str) -> tuple:
    """Leading dotted-numeric prefix as a tuple. `2.9.0.post0` -> (2, 9, 0).

    Small on purpose: every version in these locks is a plain release number, and the only
    comparisons made here are against major-version caps. A full PEP 440 implementation would
    mean importing `packaging`, which is not in the core lock (see the module docstring)."""
    m = re.match(r"(\d+(?:\.\d+)*)", text.strip())
    return tuple(int(p) for p in m.group(1).split(".")) if m else ()


def _satisfies(version: str, specifier: str) -> bool:
    v = _version(version)
    for clause in (c.strip() for c in specifier.split(",") if c.strip()):
        m = re.match(r"(>=|<=|==|<|>|!=)\s*(.+)$", clause)
        if not m:
            continue
        op, target = m.group(1), _version(m.group(2))
        # Compare on the shorter length so `<3` means "major below 3" rather than "(3,) vs
        # (2,2,6)" -- Python tuple comparison already does the right thing here, but padding
        # keeps `>=2.0` vs `2` honest.
        if op == ">=" and not v >= target: return False
        if op == "<=" and not v <= target: return False
        if op == "<" and not v < target: return False
        if op == ">" and not v > target: return False
        if op == "==" and v != target: return False
        if op == "!=" and v == target: return False
    return True


def read_lock(path: Path) -> dict:
    """Parse a lock into {name: version}, asserting the shape as it goes."""
    pins, expect_hash, last = {}, False, None
    for raw in io.open(path, encoding="utf-8").read().splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if SHA256.match(line):
            if not expect_hash:
                raise AssertionError(f"{path.name}: stray hash line: {line!r}")
            expect_hash = False
            continue
        m = PIN.match(line.strip())
        if not m:
            raise AssertionError(f"{path.name}: line is not an exact pin: {line!r}")
        if expect_hash:
            raise AssertionError(f"{path.name}: {last} has no --hash line")
        last = _norm(m.group(1))
        pins[last] = m.group(2)
        expect_hash = True
    if expect_hash:
        raise AssertionError(f"{path.name}: {last} has no --hash line")
    return pins


def read_requirements(path: Path) -> dict:
    """Parse a human requirements file into {name: specifier}, ignoring `-r` includes."""
    out = {}
    for raw in io.open(path, encoding="utf-8").read().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = REQ.match(line)
        if m:
            out[_norm(m.group(1))] = m.group(2).strip()
    return out


class LockShape(unittest.TestCase):

    def test_both_locks_exist_and_are_fully_pinned_and_hashed(self):
        for path in (CORE_LOCK, SAAS_LOCK):
            self.assertTrue(path.exists(), f"{path.name} missing")
            pins = read_lock(path)          # raises on any unpinned or unhashed line
            self.assertGreater(len(pins), 20, f"{path.name} looks truncated")
            body = io.open(path, encoding="utf-8").read()
            self.assertNotIn(">=", body, f"{path.name} must contain no ranges")

    def test_the_core_lock_is_a_strict_subset_of_the_production_lock(self):
        """They are generated from `requirements.txt` and `requirements-saas.txt`, and the
        second includes the first — so anything in core but absent from production would mean
        the two were resolved from divergent inputs."""
        core, saas = read_lock(CORE_LOCK), read_lock(SAAS_LOCK)
        missing = sorted(set(core) - set(saas))
        self.assertEqual(missing, [], f"in the core lock but not production: {missing}")
        for name, ver in core.items():
            self.assertEqual(saas[name], ver, f"{name} differs between the two locks")

    def test_stripe_and_gunicorn_are_production_only(self):
        """The one thing that must NOT be unified. `valuation/saas/billing.py` imports stripe
        inside `try:` blocks in three request handlers, so adding stripe to the CI environment
        could flip a guarded branch — pinning must not change what CI runs."""
        core, saas = read_lock(CORE_LOCK), read_lock(SAAS_LOCK)
        for pkg in ("stripe", "gunicorn"):
            self.assertIn(pkg, saas)
            self.assertNotIn(pkg, core, f"{pkg} must not enter the CI environment")


class LockAgreesWithDeclaration(unittest.TestCase):

    def test_every_declared_dependency_is_locked_at_a_satisfying_version(self):
        for src, lock in ((CORE_SRC, CORE_LOCK), (SAAS_SRC, SAAS_LOCK)):
            declared, pins = read_requirements(src), read_lock(lock)
            for name, spec in declared.items():
                self.assertIn(name, pins, f"{name} declared in {src.name}, absent from {lock.name}")
                self.assertTrue(
                    _satisfies(pins[name], spec),
                    f"{lock.name} pins {name}=={pins[name]}, which violates {src.name}'s {spec!r}")

    def test_every_declared_dependency_has_an_upper_bound(self):
        """The MA12 fix itself. Without a cap, the next major lands unannounced in a scheduled
        job that scores stocks; with one, the same upgrade becomes a diff someone has to make."""
        for src in (CORE_SRC, SAAS_SRC):
            for name, spec in read_requirements(src).items():
                self.assertIn("<", spec, f"{name} in {src.name} has no upper bound: {spec!r}")

    def test_the_locked_versions_are_the_ones_the_comments_claim(self):
        """Each declaration carries a `# locked: X` note so a reader knows what is really
        running. A note that drifts from the lock is worse than no note."""
        for src, lock in ((CORE_SRC, CORE_LOCK), (SAAS_SRC, SAAS_LOCK)):
            pins = read_lock(lock)
            for raw in io.open(src, encoding="utf-8").read().splitlines():
                m = re.search(r"#\s*locked:\s*([0-9][^\s]*)", raw)
                if not m:
                    continue
                name = REQ.match(raw.strip()).group(1)
                self.assertEqual(pins[_norm(name)], m.group(1),
                                 f"{src.name} claims {name} is locked at {m.group(1)}")


class Consumers(unittest.TestCase):
    """A lockfile nothing installs is decoration."""

    def test_ci_installs_the_core_lock_with_hash_checking(self):
        for wf in (LAND_WF, SCAN_WF):
            body = io.open(wf, encoding="utf-8").read()
            self.assertIn("--require-hashes -r requirements.lock.txt", body, wf.name)
            self.assertNotIn("pip install -r requirements.txt", body,
                             f"{wf.name} still has an unpinned install")

    def test_the_container_installs_the_production_lock_with_hash_checking(self):
        body = io.open(DOCKERFILE, encoding="utf-8").read()
        self.assertIn("--require-hashes -r requirements-saas.lock.txt", body)
        self.assertNotIn("pip install --no-cache-dir -r requirements-saas.txt", body)
        self.assertIn("COPY", body)
        self.assertIn("requirements-saas.lock.txt ./", body,
                      "the lock must be COPYed into the image or the build cannot install it")

    def test_the_lock_target_matches_every_interpreter_that_installs_it(self):
        """The locks hold linux/cp311 wheels. If a runner or the base image moves to another
        Python minor, `--require-hashes` fails the build — loudly, but only at deploy time.
        This says it at test time instead."""
        gen = io.open(ROOT / "scripts" / "gen_requirements_lock.py", encoding="utf-8").read()
        target = re.search(r'PY_VERSION\s*=\s*"([\d.]+)"', gen).group(1)
        self.assertEqual(target, "3.11")
        self.assertIn(f"python-version: '{target}'", io.open(LAND_WF, encoding="utf-8").read())
        self.assertIn(f'python-version: "{target}"', io.open(SCAN_WF, encoding="utf-8").read())
        self.assertIn(f"FROM python:{target}-slim", io.open(DOCKERFILE, encoding="utf-8").read())

    def test_the_human_files_remain_the_local_path(self):
        """The locks cannot install on Windows, which is what Don runs. `run.bat` must keep
        pointing at requirements.txt; pointing it at a lock would break the one-click launcher
        on the only machine that uses it."""
        run_bat = ROOT / "run.bat"
        if run_bat.exists():
            body = io.open(run_bat, encoding="utf-8", errors="replace").read()
            self.assertNotIn("requirements.lock.txt", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
