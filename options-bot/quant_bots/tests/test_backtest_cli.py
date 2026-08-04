"""
C3 — `--bots reversion` must never again be accepted, run nothing, and succeed.

The defect was not a missing feature. It was a flag that took an argument, fell
through every `if` in main(), and printed "Backtests complete." One of four live
strategies had therefore never been backtested, and the script said otherwise.

These tests assert the two properties that make that impossible:
  1. every bot this repo deploys is either backtestable or explicitly rejected;
  2. an unrunnable --bots value exits non-zero BEFORE any network call.

    python -m unittest tests.test_backtest_cli -v
"""
import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_script():
    """scripts/ is not a package; load run_backtest.py by path."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    path = PROJECT_ROOT / "scripts" / "run_backtest.py"
    spec = importlib.util.spec_from_file_location("_bt_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BotCoverage(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script()

    def test_reversion_is_implemented(self):
        self.assertIn("reversion", self.mod.BACKTESTS,
                      "reversion must be backtestable, not silently skipped")
        self.assertTrue(callable(self.mod.BACKTESTS["reversion"]))

    def test_every_deployed_bot_is_accounted_for(self):
        """
        deploy/*-bot.service is the list of strategies that actually trade. Each
        one must be either runnable here or listed in UNSUPPORTED with a reason
        — never merely absent, which is what "silently does nothing" looks like
        from the outside.
        """
        deployed = {p.name.replace("-bot.service", "")
                    for p in (PROJECT_ROOT / "deploy").glob("*-bot.service")}
        self.assertTrue(deployed, "expected deploy/*-bot.service unit files")
        known = set(self.mod.BACKTESTS) | set(self.mod.UNSUPPORTED)
        missing = deployed - known
        self.assertFalse(missing,
                         f"deployed bots neither backtestable nor explicitly "
                         f"unsupported: {sorted(missing)}")

    def test_unsupported_entries_carry_a_reason(self):
        for bot, reason in self.mod.UNSUPPORTED.items():
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason), 40,
                               f"{bot}: 'unsupported' needs an explanation, not a flag")


class FailsLoudly(unittest.TestCase):
    """
    The validation must run BEFORE _tradier(), so these tests never touch the
    network or need a token. If one of them ever hangs, the check has drifted
    below the credential lookup and the loud failure is no longer loud.
    """

    def setUp(self):
        self.mod = _load_script()
        self._argv = sys.argv

    def tearDown(self):
        sys.argv = self._argv

    def _run(self, *bots):
        sys.argv = ["run_backtest.py", "--bots", *bots]
        with self.assertRaises(SystemExit) as ctx:
            self.mod.main()
        return ctx.exception

    def test_unknown_bot_exits_with_a_message(self):
        exc = self._run("frobnicate")
        self.assertIsInstance(exc.code, str)
        self.assertIn("frobnicate", exc.code)
        self.assertIn("unknown", exc.code.lower())

    def test_options_is_rejected_with_a_reason_not_skipped(self):
        exc = self._run("options")
        self.assertIsInstance(exc.code, str)
        self.assertIn("options_backtest", exc.code,
                      "point the user at the backtest that DOES cover the options bot")

    def test_a_bad_name_alongside_good_ones_still_fails(self):
        """A valid bot in the list must not buy a free pass for an invalid one."""
        exc = self._run("trend", "frobnicate")
        self.assertIsInstance(exc.code, str)


if __name__ == "__main__":
    unittest.main()
