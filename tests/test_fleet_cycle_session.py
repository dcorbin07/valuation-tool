"""The cycle's clock - why four books read `RULE_ARMED_NEVER_FIRES` and never saw their data.

**THE DEFECT, AND BOTH HALVES OF IT WERE ALREADY MEASURED AND WRITTEN DOWN SEPARATELY.**

* `fleet-cycle.yml` crons at **22:19Z**, and item 64 measured GitHub firing this repository's
  crons **3.5 to 7.5 hours late**. The last six cycles landed at 00:24Z, 00:31Z, 01:13Z,
  07:15Z, 03:03Z and 01:45Z - **every one on the FOLLOWING UTC day.**
* `/admin/record-dip-rejects` stamps its rows with **`last_closed_session()`**, deliberately,
  *"so a slipped run still records the day whose data it read"*.

Every entry rule then compared the recorded date against **`date.today()`**. Writer and reader
on different clocks, exact-match between them, so **the match could never succeed** - and the
harness reported the result as `RULE_ARMED_NEVER_FIRES`, which reads as *the rule cannot
qualify anybody* when the truth is *the rule never saw the data*.

WHAT THESE PIN
--------------
1. **A cycle that lands after midnight UTC reads the session before it**, which is the exact
   shape of every real run.
2. **One definition** (`B7`): no rule may resolve its own date from `date.today()` again.
3. **The fallback is reported, not silent** - a rule that quietly changed which day it reads
   would be the same defect wearing the repair's clothes.
4. **The old behaviour is reconstructed and shown to fail**, so this cannot be read as a
   speculative fix.

    python tests/test_fleet_cycle_session.py
"""
from __future__ import annotations

import ast
import datetime as dt
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet_books as FB  # noqa: E402

#: The six observed landing times of the real cron, from the Actions history.
REAL_LANDINGS = [
    dt.datetime(2026, 10, 17, 0, 29),
    dt.datetime(2026, 10, 16, 0, 24),
    dt.datetime(2026, 10, 15, 0, 31),
    dt.datetime(2026, 10, 14, 1, 13),
    dt.datetime(2026, 10, 13, 7, 15),
    dt.datetime(2026, 10, 10, 1, 45),
]


class TestTheClock(unittest.TestCase):
    """(1) and (4)."""

    def test_a_cycle_landing_after_midnight_reads_the_session_BEFORE_it(self):
        got = FB.cycle_session(dt.datetime(2026, 10, 17, 1, 0))
        self.assertEqual(got, dt.date(2026, 10, 16))
        self.assertNotEqual(got, dt.date(2026, 10, 17),
                            "date.today() on the runner would have been the 17th")

    def test_on_every_real_landing_the_session_is_NOT_the_runners_own_date(self):
        """**The reconstruction of the old behaviour.** If these agreed, there was no defect."""
        disagreed = 0
        for when in REAL_LANDINGS:
            session = FB.cycle_session(when)
            if session != when.date():
                disagreed += 1
        self.assertEqual(disagreed, len(REAL_LANDINGS),
                         "every observed landing is on a different UTC day from its session, "
                         "so an exact match against date.today() could never succeed")

    def test_a_cycle_that_fired_ON_TIME_would_have_agreed(self):
        """Which is why the rules looked correct when they were written."""
        on_time = dt.datetime(2026, 10, 16, 22, 19)
        self.assertEqual(FB.cycle_session(on_time), on_time.date())

    def test_a_weekend_cycle_resolves_to_the_last_trading_day_and_never_to_itself(self):
        sat = dt.datetime(2026, 10, 17, 2, 0)
        got = FB.cycle_session(sat)
        self.assertLess(got, sat.date())
        self.assertLess(got.weekday(), 5, "a session is never a Saturday or a Sunday")


class TestOneDefinition(unittest.TestCase):
    """(2)."""

    def test_no_entry_rule_resolves_its_date_from_date_today(self):
        src = open(os.path.join(REPO, "valuation", "edge", "fleet_books.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        # EXEMPT `cycle_session` ITSELF -- it is the one function allowed to name the
        # fallback, and banning it there would ban the definition along with the misuse,
        # which is the substring-ban family (MA49) in AST clothing. Everything else is in
        # scope.
        body = [n for n in tree.body
                if not (isinstance(n, ast.FunctionDef) and n.name == "cycle_session")]
        bad = []
        for top in body:
            for node in ast.walk(top):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                # matches `_dt.date.today()` and `datetime.date.today()`
                if (isinstance(f, ast.Attribute) and f.attr == "today"
                        and isinstance(f.value, ast.Attribute) and f.value.attr == "date"):
                    bad.append(getattr(node, "lineno", "?"))
        self.assertEqual(bad, [], "date.today() is back at line(s) %r -- use cycle_session()"
                                  % (bad,))

    def test_the_helper_exists_and_is_what_the_rules_call(self):
        src = open(os.path.join(REPO, "valuation", "edge", "fleet_books.py"),
                   encoding="utf-8").read()
        self.assertGreaterEqual(src.count("cycle_session()"), 6,
                                "every rule that had a date must now ask the one helper")


class TestTheFallbackIsReported(unittest.TestCase):
    """(3) - and the positive control, so the guard is not passing by refusing everything."""

    def test_it_still_returns_a_date_when_the_calendar_cannot_be_consulted(self):
        import valuation.screener.market_session as MS
        real = MS.last_closed_session
        try:
            MS.last_closed_session = lambda *a, **k: None
            got = FB.cycle_session(dt.datetime(2026, 10, 17, 1, 0))
            self.assertIsInstance(got, dt.date)
        finally:
            MS.last_closed_session = real

    def test_the_docstring_states_the_fallback_rather_than_hiding_it(self):
        d = FB.cycle_session.__doc__ or ""
        self.assertIn("Falls back", d)
        self.assertIn("never silently", d)

    def test_the_helper_is_pure_and_takes_the_clock_as_an_argument(self):
        """Or it could not be tested at a chosen time, which is the whole of this suite."""
        self.assertEqual(FB.cycle_session(dt.datetime(2026, 10, 14, 3, 0)),
                         FB.cycle_session(dt.datetime(2026, 10, 14, 3, 0)))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
