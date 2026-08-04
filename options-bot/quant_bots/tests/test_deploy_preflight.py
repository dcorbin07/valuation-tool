"""
C6 — "fixed in repo, not deployed" must not be a state this project can sit in.

Three correctness fixes (FIXES.md) were found, fixed, and left undeployed. The
mechanism that was supposed to catch that — "test counts changed; if you see the
old numbers after a deploy, the old code is still there" — could not fire,
because deploy.sh's copy of the expected counts had gone stale by two
generations and the check is a `-lt` warning that continues anyway.

These tests pin the replacement:
  * the FIXES.md fixes are checked directly, by symbol and by behaviour;
  * deploy.sh actually runs the preflight and treats a failure as fatal;
  * the stale-constant bug becomes self-detecting — the expected test count is
    not allowed to drift far behind the real one again.

    python -m unittest tests.test_deploy_preflight -v
"""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SH = PROJECT_ROOT / "deploy" / "deploy.sh"

# Allowed drift between deploy.sh's EXPECTED_CORE_TESTS and the real count.
# Small enough that "two generations behind" fails; large enough that adding a
# test does not break the build on the same commit.
MAX_COUNT_DRIFT = 12


def _count_tests(start_dir):
    """Number of test cases the discoverer would collect, WITHOUT running them."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    suite = unittest.defaultTestLoader.discover(str(start_dir), top_level_dir=str(PROJECT_ROOT))

    def walk(s):
        n = 0
        for item in s:
            n += walk(item) if isinstance(item, unittest.TestSuite) else 1
        return n

    return walk(suite)


def _load_preflight():
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    spec = importlib.util.spec_from_file_location(
        "_preflight", PROJECT_ROOT / "deploy" / "preflight.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FixesArePresent(unittest.TestCase):
    """
    These two are checkable without the options bot's missing `data` package.
    Fix 3 is not, which is itself the C6 finding and is asserted separately.
    """

    def setUp(self):
        self.pf = _load_preflight()

    def test_fix_1_exit_orders_still_priced_from_the_full_map(self):
        self.assertTrue(self.pf.check_fix_1_exit_orders())

    def test_fix_2_reversion_never_shorts_an_all_oversold_cross_section(self):
        self.assertTrue(self.pf.check_fix_2_reversion_sign())

    def test_every_fix_has_a_check(self):
        """One check per numbered fix in FIXES.md. If a fourth fix lands and no
        check comes with it, this fails and says so."""
        text = (PROJECT_ROOT.parent / "FIXES.md").read_text(encoding="utf-8",
                                                            errors="ignore")
        numbered = re.findall(r"^## (\d+)\. ", text, flags=re.MULTILINE)
        self.assertEqual(len(self.pf.FIX_CHECKS), len(numbered),
                         f"FIXES.md documents {len(numbered)} fixes but preflight "
                         f"checks {len(self.pf.FIX_CHECKS)}")


class DeployScriptGate(unittest.TestCase):
    def setUp(self):
        self.src = DEPLOY_SH.read_text(encoding="utf-8", errors="ignore")

    def test_deploy_runs_the_preflight(self):
        self.assertIn("deploy/preflight.py", self.src,
                      "deploy.sh must run the preflight")

    def test_preflight_failure_is_fatal(self):
        """It must `die`, not warn. The stale test-count check warns and
        continues, which is why it never stopped anything."""
        idx = self.src.index("deploy/preflight.py")
        tail = self.src[idx:idx + 200]
        self.assertIn("||", tail, "preflight must be followed by `|| die`")
        self.assertIn("die", tail)

    def test_preflight_runs_before_any_restart(self):
        self.assertLess(self.src.index("deploy/preflight.py"),
                        self.src.index("install_services.sh"),
                        "preflight must run before services are restarted")

    def test_expected_core_test_count_has_not_gone_stale(self):
        """
        The bug this replaces: EXPECTED_CORE_TESTS sat at 106 while the suite had
        148. A floor that far below reality cannot detect old code on the box,
        which is exactly what it exists to do.
        """
        m = re.search(r"^EXPECTED_CORE_TESTS=(\d+)", self.src, flags=re.MULTILINE)
        self.assertIsNotNone(m, "EXPECTED_CORE_TESTS not found in deploy.sh")
        expected = int(m.group(1))
        # COUNT the suite; do not RUN it. Running `unittest discover tests` from
        # inside a test that lives in `tests/` re-discovers this very module and
        # recurses until the machine gives up — which it duly did, once.
        actual = _count_tests(PROJECT_ROOT / "tests")
        self.assertLessEqual(
            actual - expected, MAX_COUNT_DRIFT,
            f"deploy.sh expects >= {expected} core tests but the suite has "
            f"{actual}. Bump EXPECTED_CORE_TESTS — a stale floor is a check "
            f"that cannot fire.")
        self.assertLessEqual(
            expected, actual,
            f"deploy.sh expects {expected} core tests but only {actual} exist; "
            f"every deploy would warn.")


class TheOptionsBotCannotBeDeployedFromThisRepo(unittest.TestCase):
    """
    The C6 finding itself, asserted rather than described.

    `options/orchestrator/jobs.py` imports `data`, and no `data/*.py` is tracked
    anywhere in this repository, because the repo-ROOT .gitignore's bare `data/`
    rule matches at every depth. quant_bots/.gitignore now re-includes the
    directory, but the source has to be committed once from the box that has it.

    This test is written to PASS once that happens — it asserts the gitignore
    escape hatch is in place, not that the package is still missing.
    """

    def test_quant_bots_gitignore_re_includes_the_data_package(self):
        gi = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
        lines = [l.strip() for l in gi.splitlines()]
        self.assertIn("!data/", lines,
                      "without `!data/` the root .gitignore's blanket `data/` "
                      "rule silently excludes the options bot's source package")
        for state_dir in ("data/cache/", "data/state/", "data/journal/"):
            self.assertIn(state_dir, lines,
                          f"{state_dir} must stay ignored — re-including data/ "
                          f"must not start committing bot state")

    def test_bot_state_is_still_excluded(self):
        """Re-including data/ must not sweep the sim books and reports into git."""
        gi = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
        lines = [l.strip() for l in gi.splitlines()]
        for state_dir in ("data/sim/", "data/reports/"):
            self.assertIn(state_dir, lines)


if __name__ == "__main__":
    unittest.main()
