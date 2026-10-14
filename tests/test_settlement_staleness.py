"""The stale-settlement defect that VOIDED SELL-PREMIUM-2's stage 2 - what these pin.

**WHAT HAPPENED.** `settlement_spot` returned *"the last session at or before the expiry"* with
no limit, and `spot_maps` built its years from `SP.era_years()` - STAGE 1's era. Stage 2 imported
both for a book whose expiries run to 2026, so the map stopped at 2020-12-31 and **73.02% of the
4,522-trade book settled at its ticker's last 2020 close**: GE $10.80 on 15 of 15 assigned
post-2020 trades, AAPL $132.69 on 17 of 17, NVDA $522.20, and **177 of 177** tickers with two or
more assigned post-2020 trades landing on exactly ONE price. **Nothing raised and nothing was
dropped.** The arm produced a clean, plausible, wrong verdict - `MA31`'s failure mode - and the
pattern it produced (losses growing monotonically with distance past 2020: -3.9%, -6.0%, -7.4%,
-18.5%, -18.4%, -22.6%) was reported as a FINDING about the late half.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **THE NAMED CASE FAILS ON THE OLD CODE.** GE expiring 2025-09-26 against a map that ends
   2020-12-31 must REFUSE, not return $10.80. This is the regression test the repair exists for
   and it is written so that deleting the limit makes it red.

2. **THE LIMIT IS REQUIRED, WITH NO DEFAULT.** A default is how the silence comes back (`MA5`).
   Both the signature and every in-tree caller are checked, from the SYNTAX TREE.

3. **THE ORDINARY CASES STILL SETTLE** - a Saturday monthly expiry, and a holiday stretch. A
   guard that refuses everything would pass test 1 and destroy every book, so the positive
   controls are what make test 1 mean anything.

4. **STALENESS IS MEASURED ON THE CALENDAR, AND IT HAS TO BE.** A map that has stopped has no
   sessions after its own end, so a SESSION count reads ZERO staleness for a map that is years
   short - it cannot see the gap it is guarding against. Pinned with the real failing shape.

5. **`spot_maps` TAKES ITS YEARS FROM THE TRADES.** `years_spanning` must cover the expiry year,
   or the repair is cosmetic: the limit would then refuse 73% of the book instead of settling it
   wrongly, which is honest and still useless.

    python tests/test_settlement_staleness.py
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import sellpremium as SP  # noqa: E402

LIMIT = SP.MAX_SETTLEMENT_STALE_DAYS


def _map(pairs):
    return {d: float(v) for d, v in pairs}


class TestTheNamedRegression(unittest.TestCase):
    """(1). The exact case from the void stage-2 book."""

    #: GE's real last 2020 close, and the real expiry the void book settled against it.
    GE_LAST_2020 = ("2020-12-31", 10.80)
    GE_EXPIRY = "2025-09-26"

    def test_GE_expiring_2025_does_not_settle_at_its_2020_close(self):
        spot = _map([("2020-12-30", 10.71), self.GE_LAST_2020])
        got = SP.settlement_spot(spot, self.GE_EXPIRY, max_stale_days=LIMIT)
        self.assertIsNone(
            got,
            "a map ending 2020-12-31 cannot settle a 2025 expiry; returning its final close "
            "is an answer about the MAP wearing the costume of an answer about the market")

    def test_the_old_behaviour_is_what_this_refuses(self):
        """Non-vacuity: with no limit the SAME inputs return exactly the wrong $10.80, so this
        suite is pinning a real change rather than a tautology."""
        spot = _map([("2020-12-30", 10.71), self.GE_LAST_2020])
        ds = [d for d in spot if d <= self.GE_EXPIRY]
        old = float(spot[max(ds)])          # the pre-repair body, inlined
        self.assertAlmostEqual(old, 10.80, places=2)

    def test_every_named_ticker_from_the_void_book_refuses(self):
        for last, px, exp in (("2020-12-31", 10.80, "2025-09-26"),
                              ("2020-12-31", 132.69, "2021-06-18"),
                              ("2020-12-31", 522.20, "2024-01-19"),
                              ("2020-12-31", 28.54, "2022-03-18"),
                              ("2020-12-31", 8.07, "2023-07-21")):
            self.assertIsNone(SP.settlement_spot(_map([(last, px)]), exp,
                                                 max_stale_days=LIMIT),
                              "expiry %s against a map ending %s" % (exp, last))


class TestTheLimitIsRequired(unittest.TestCase):
    """(2). From the syntax tree, so a default cannot creep back."""

    def test_the_parameter_is_keyword_only_with_no_default(self):
        with io.open(os.path.join(REPO, "valuation", "studies", "sellpremium.py"),
                     encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "settlement_spot")
        names = [a.arg for a in fn.args.kwonlyargs]
        self.assertIn("max_stale_days", names)
        i = names.index("max_stale_days")
        self.assertIsNone(fn.args.kw_defaults[i],
                          "a default is how the silence comes back (MA5)")
        self.assertNotIn("max_stale_days", [a.arg for a in fn.args.args],
                         "keyword-only, so no caller can pass it by position by accident")

    def test_every_in_tree_caller_states_a_limit(self):
        for rel in ("scripts", "valuation"):
            for root, _d, files in os.walk(os.path.join(REPO, rel)):
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    p = os.path.join(root, f)
                    with io.open(p, encoding="utf-8") as fh:
                        src = fh.read()
                    if "settlement_spot(" not in src:
                        continue
                    for n in ast.walk(ast.parse(src)):
                        if (isinstance(n, ast.Call)
                                and getattr(n.func, "attr", None) == "settlement_spot"):
                            kws = {k.arg for k in n.keywords}
                            self.assertIn("max_stale_days", kws,
                                          "%s calls settlement_spot without a limit" % p)


class TestTheOrdinaryCasesStillSettle(unittest.TestCase):
    """(3). Positive controls, or test 1 passes on a guard that refuses everything."""

    def test_a_saturday_monthly_expiry_settles_on_the_friday(self):
        spot = _map([("2018-01-18", 44.0), ("2018-01-19", 45.5)])
        got = SP.settlement_spot(spot, "2018-01-20", max_stale_days=LIMIT)  # Saturday
        self.assertAlmostEqual(got, 45.5)

    def test_an_exact_session_match_settles(self):
        spot = _map([("2019-06-20", 10.0), ("2019-06-21", 11.0)])
        self.assertAlmostEqual(
            SP.settlement_spot(spot, "2019-06-21", max_stale_days=LIMIT), 11.0)

    def test_a_holiday_stretch_inside_the_limit_still_settles(self):
        spot = _map([("2020-12-24", 70.0)])
        self.assertAlmostEqual(
            SP.settlement_spot(spot, "2021-01-02", max_stale_days=LIMIT), 70.0)

    def test_the_limit_bites_just_past_itself(self):
        spot = _map([("2020-01-01", 50.0)])
        inside = "2020-01-%02d" % (1 + LIMIT)
        outside = "2020-01-%02d" % (1 + LIMIT + 1)
        self.assertIsNotNone(SP.settlement_spot(spot, inside, max_stale_days=LIMIT))
        self.assertIsNone(SP.settlement_spot(spot, outside, max_stale_days=LIMIT))


class TestStalenessIsOnTheCalendar(unittest.TestCase):
    """(4). The reason a session count cannot do this job."""

    def test_a_map_that_has_stopped_has_no_sessions_after_its_own_end(self):
        spot = _map([("2020-12-30", 10.71), ("2020-12-31", 10.80)])
        after = [d for d in spot if d > "2025-09-26"]
        self.assertEqual(after, [],
                         "zero sessions after the expiry is exactly what a 5-year-short map "
                         "looks like, so a session count would read ZERO staleness")
        self.assertIsNone(SP.settlement_spot(spot, "2025-09-26", max_stale_days=LIMIT))


class TestSpotMapsTakeTheirYearsFromTheTrades(unittest.TestCase):
    """(5). Or the limit refuses 73% of the book instead of the map covering it."""

    def test_years_spanning_covers_entry_through_expiry(self):
        import pandas as pd
        from scripts.sellpremium2_arm import years_spanning
        picks = pd.DataFrame({"date": ["2020-03-02", "2025-11-14"],
                              "expiration": ["2020-04-17", "2026-01-30"]})
        self.assertEqual(years_spanning(picks), [2020, 2021, 2022, 2023, 2024, 2025, 2026])

    def test_spot_maps_requires_its_years(self):
        with io.open(os.path.join(REPO, "scripts", "sellpremium2_arm.py"),
                     encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "spot_maps")
        self.assertEqual([a.arg for a in fn.args.args], ["tickers", "years"])
        self.assertEqual(fn.args.defaults, [],
                         "no default era, or stage 2's defect returns")

    def test_the_stage2_runner_derives_its_years_rather_than_importing_an_era(self):
        with io.open(os.path.join(REPO, "scripts", "sellpremium2_stage2.py"),
                     encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and getattr(n.func, "attr", None) == "spot_maps"]
        self.assertTrue(calls, "stage 2 must still build spot maps")
        for c in calls:
            self.assertEqual(len(c.args), 2, "the years must be passed explicitly")
        self.assertIn("years_spanning", src)
        self.assertNotIn("era_years", src,
                         "importing an era constant here is the defect itself")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
