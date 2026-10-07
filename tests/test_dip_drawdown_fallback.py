# -*- coding: utf-8 -*-
"""ITEM 36(a) — the engine's 52-week high has no fallback, and the scan's does.

THE DEFECT. `cd.price_52w_high` is set in exactly ONE place, `yahoo.py`'s
`t.history(period="1y")` block, and EDGAR's gap-fill cannot supply a price. When that single call
comes back empty the measurement carries `drawdown: None` -- a real valuation the screen cannot
turn into a row. Measured on the 2026-10-06 precompute: **90 of 210** qualifying names, against
**0 of 36** on an identical 6-worker burst from a desktop. `providers.py` names the cause in its
own comment: the per-name free fetch "is aggressively rate-limited from a cloud IP, and when it
fails it returns nothing at all". The SCAN survives that because the broker prefills the universe,
which is why only 59 of the 210 lack `high_prox` while 90 lack the engine's high.

THE QUANTITY ALREADY EXISTS ON THE ROW. `high_prox` is `price / max(close over the trailing 252
sessions)` -- the same 252-session maximum, from history the scan already fetched -- so
`1 - high_prox` IS the drawdown.

WHAT THESE PIN, each one a way this goes wrong:

  * **NO ADJUSTED-VERSUS-RAW MIXING.** The fallback is a RATIO from one vendor's own pair, so a
    split scales both legs and cancels. Driven with a 4-for-1 split to prove it.
  * **THE Z-SCORE IS NEVER READ.** `extra["numbers"]["high_prox"]` is the within-date z-score and
    reading it would put a fabricated percentage on a public surface. The fallback goes through
    `cheap_drawdown`, the named reader for the RAW ratio.
  * **THE MEASURED FIGURE ALWAYS WINS.** The fallback is for a missing high, never a second
    opinion on a present one.
  * **THE ROW SAYS WHICH VINTAGE IT STANDS ON**, because the two disagree near the threshold --
    which is what `PRESELECT_SLACK` exists for.
  * **THE DISPLAYED TRIPLE SATISFIES ITS OWN ARITHMETIC**, or a reader checking
    `1 - price/high` against `drawdown` finds them disagreeing.

    python tests/test_dip_drawdown_fallback.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.web import dip                                            # noqa: E402


def _row(ticker, high_prox, z=1.0, price=10.0):
    """`extra.high_prox` is the RAW ratio; `extra.numbers.high_prox` is the z-score."""
    return {"ticker": ticker, "name": ticker, "sector": "Tech", "price": price,
            "market_cap": 5e9, "hot_score": 50, "rank": 1,
            "z_quality": z, "z_growth": z,
            "extra": {"high_prox": high_prox, "numbers": {"high_prox": -z}}}


def _m(dd, price=10.0, high=None):
    """A measurement. `dd=None` is the engine-had-no-52-week-high case."""
    return {"drawdown": dd, "price": price, "high_52w": high,
            "subs": {"health": 80, "quality": 80, "growth": 80},
            "score": 70, "confidence": "medium", "fair_value": 20.0, "upside": 1.0,
            "fair_value_low": 15.0, "fair_value_high": 25.0,
            "fair_value_withheld_reason": None,
            "checks": {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                       "terminal_share": dip.PASS}}


class TheFallbackRescuesTheRow(unittest.TestCase):

    def test_a_name_with_no_engine_high_now_produces_a_row(self):
        """THE DEFECT: 90 of 210 arrived as `n_unmeasured` and could never be shown."""
        rows = [_row("AAA", 0.60)]                          # 40% down per the scan
        out = dip.screen(rows, min_drawdown=0.10, measure=lambda r: _m(None), shortlist=0)
        self.assertEqual(len(out["rows"]), 1, out)
        self.assertEqual(out["n_unmeasured"], 0)
        self.assertAlmostEqual(out["rows"][0]["drawdown"], 0.40, places=6)

    def test_the_row_says_the_drawdown_came_from_the_scan(self):
        rows = [_row("AAA", 0.60)]
        out = dip.screen(rows, min_drawdown=0.10, measure=lambda r: _m(None), shortlist=0)
        self.assertEqual(out["rows"][0]["drawdown_source"], "scan")
        self.assertEqual(out["n_drawdown_from_scan"], 1)

    def test_a_MEASURED_drawdown_always_wins(self):
        """The fallback is for a MISSING high, never a second opinion on a present one."""
        rows = [_row("AAA", 0.60)]                          # the scan says 0.40
        out = dip.screen(rows, min_drawdown=0.10,
                         measure=lambda r: _m(0.25, high=13.33), shortlist=0)
        self.assertAlmostEqual(out["rows"][0]["drawdown"], 0.25, places=6)
        self.assertEqual(out["rows"][0]["drawdown_source"], "measured")
        self.assertEqual(out["n_drawdown_from_scan"], 0)

    def test_no_engine_high_AND_no_scan_depth_is_still_unmeasured(self):
        """Absent is absent. Inventing a drawdown here is the one thing worse than no row."""
        r = _row("AAA", 0.60)
        r["extra"]["high_prox"] = None
        out = dip.screen([r], min_drawdown=0.10, measure=lambda _r: _m(None), shortlist=0)
        self.assertEqual(len(out["rows"]), 0)
        self.assertEqual(out["n_unmeasured"], 1)

    def test_the_identity_still_holds_with_the_fallback_in_play(self):
        """Item 35's live-check identity. The fallback MOVES names out of `unmeasured` into rows,
        health or shallow -- it must not create or lose one."""
        rows = [_row("A", 0.55), _row("B", 0.70), _row("C", 0.88), _row("D", 0.95)]

        def mixed(r):
            t = r["ticker"]
            if t == "A":
                return _m(0.45, high=18.18)                 # measured
            if t == "B":
                return _m(None)                             # falls back to 0.30
            if t == "C":
                m = _m(None)                                # falls back to 0.12, unhealthy
                m["subs"] = {"health": 1, "quality": 1, "growth": 1}
                return m
            return _m(None)                                 # falls back to 0.05, too shallow

        for th in (0.10, 0.20, 0.30, 0.40):
            out = dip.screen(rows, min_drawdown=th, measure=mixed, shortlist=0)
            total = (len(out["rows"]) + out["n_unmeasured"] + out["rejected_health"]
                     + out["rejected_shallow"])
            self.assertEqual(total, out["n_qualified_on_depth"],
                             "threshold %.2f: %s" % (th, out))


class TheBasisIsNeverMixed(unittest.TestCase):
    """The property the task names: never mix adjusted and raw."""

    def test_a_split_cancels_because_the_fallback_is_a_RATIO(self):
        """`high_prox` is `price / high` from ONE vendor's own series -- `prices.get_quote`
        divides within a single `get_history_df` frame, `broker_universe` within a single quote.
        A 4-for-1 split scales both legs, so the ratio is unchanged and the drawdown is right.

        The alternative -- an adjusted HIGH against an as-traded PRICE -- would read
        `1 - 40/(160/4)` = 0.0 on a name genuinely 60% down, and the name would vanish from the
        screen rather than show a wrong number. That is the failure this construction avoids.
        """
        pre_split_high, pre_split_price = 160.0, 64.0       # genuinely 60% down
        ratio = pre_split_price / pre_split_high
        for factor in (1.0, 4.0, 0.125):                    # unsplit, 4-for-1, 1-for-8 reverse
            r = _row("AAA", ratio, price=pre_split_price / factor)
            out = dip.screen([r], min_drawdown=0.10, measure=lambda _r: _m(None), shortlist=0)
            self.assertAlmostEqual(out["rows"][0]["drawdown"], 0.60, places=6,
                                   msg="split factor %s moved the drawdown" % factor)

    def test_the_fallback_reads_the_RAW_ratio_and_not_the_z_score(self):
        """`extra["numbers"]["high_prox"]` is the within-date z-score. Rendering it as a
        percentage would put a fabricated per-name number on a public surface -- the failure
        class `withhold.py` exists for, and the one this module's docstring names first."""
        r = _row("AAA", 0.60)
        r["extra"]["numbers"]["high_prox"] = -3.0           # a z-score, not a ratio
        out = dip.screen([r], min_drawdown=0.10, measure=lambda _r: _m(None), shortlist=0)
        self.assertAlmostEqual(out["rows"][0]["drawdown"], 0.40, places=6)
        # 1 - (-3.0) = 4.0 would be the number if the z-score were read.
        self.assertLess(out["rows"][0]["drawdown"], 1.0)

    def test_it_goes_through_cheap_drawdown_rather_than_the_field(self):
        """ONE reader for the raw ratio. Reaching for `extra["high_prox"]` here would be a
        second definition, and the two fields differ by being a ratio and a z-score."""
        import inspect
        src = inspect.getsource(dip.screen)
        self.assertIn("cheap_drawdown(r)", src)


class TheDisplayedTripleIsConsistent(unittest.TestCase):

    def test_the_high_is_implied_from_the_rows_own_price(self):
        """A reader checking `1 - price/high` against `drawdown` must find them agreeing.
        Rendering the engine's `None` would show a fall from nothing; rendering the scan's own
        high would put it on a different basis from the price beside it."""
        out = dip.screen([_row("AAA", 0.60, price=12.0)], min_drawdown=0.10,
                         measure=lambda _r: _m(None, price=12.0), shortlist=0)
        row = out["rows"][0]
        self.assertAlmostEqual(row["high_52w"], 20.0, places=6)
        self.assertAlmostEqual(1.0 - row["price"] / row["high_52w"], row["drawdown"], places=6)

    def test_a_measured_row_keeps_the_engines_own_high(self):
        out = dip.screen([_row("AAA", 0.60)], min_drawdown=0.10,
                         measure=lambda _r: _m(0.25, high=13.33), shortlist=0)
        self.assertAlmostEqual(out["rows"][0]["high_52w"], 13.33, places=6)

    def test_the_implied_high_refuses_the_degenerate_cases(self):
        self.assertIsNone(dip._implied_high(None, 0.4))
        self.assertIsNone(dip._implied_high(10.0, None))
        self.assertIsNone(dip._implied_high(0.0, 0.4))
        self.assertIsNone(dip._implied_high(10.0, 1.0), "a 100% fall implies an infinite high")
        self.assertAlmostEqual(dip._implied_high(6.0, 0.4), 10.0, places=6)


class ThePrecomputeNamesWhatItCouldNotMeasure(unittest.TestCase):

    def test_the_no_drawdown_names_are_listed_not_just_counted(self):
        """The 2026-10-06 run reported 90 with no drawdown and nothing said WHICH, so the cause
        had to be inferred. The throttle hypothesis is checkable only against the list."""
        class _R:
            def __init__(self, high):
                self.company = type("C", (), {"price": 10.0, "price_52w_high": high})()
                self.score = type("S", (), {"subscores": {"health": 80}, "score": 70,
                                            "confidence": "medium"})()
                self.fair_value_blend = type("B", (), {
                    "tv_share": 0.5, "confidence": "medium", "value": 20.0,
                    "withheld_value": None, "growth_led": False})()
                self.base_fair_value = 20.0
                self.fair_value_scenarios = {}
                self.classification = None
                self.wacc = type("W", (), {"beta_provenance": None})()

        rows = [_row("AAA", 0.60), _row("BBB", 0.70)]
        c = dip.precompute(rows, lambda t: _R(20.0 if t == "AAA" else None),
                           min_drawdown=0.10, workers=1)
        self.assertEqual(c["shape"]["with_drawdown"], 1)
        self.assertEqual(c["shape"]["no_drawdown"], 1)
        self.assertEqual(c["shape"]["no_drawdown_tickers"], ["BBB"])

    def test_the_list_is_bounded(self):
        """It rides in the ingest payload, so it cannot be the whole universe."""
        import inspect
        self.assertIn("no_dd[:40]", inspect.getsource(dip.precompute))


class TheHealthRejectionsAreSplitByReason(unittest.TestCase):
    """`health_check` treats a MISSING sub-score as a failure, and item 26 deliberately withholds
    the health sub-score for the financial, reit and regulated regimes. Measured live at 0.10 on
    the 2026-10-06 scan: of 110 health rejections, 73 are below a floor and **31 are a missing
    health score** -- EVR, SCHW, VIRT, VCTR, AEG, BBVA, OHI. So the screen structurally cannot
    show a bank, an insurer, a REIT or a regulated utility, and the aggregate counter hid it.
    """

    def _run(self, subs_by_ticker):
        rows = [_row(t, 0.60) for t in subs_by_ticker]
        return dip.screen(rows, min_drawdown=0.10, shortlist=0,
                          measure=lambda r: dict(_m(0.40, high=16.67),
                                                 subs=subs_by_ticker[r["ticker"]]))

    def test_a_withheld_sub_score_counts_as_MISSING_not_below(self):
        out = self._run({"BANK": {"quality": 80, "growth": 80}})     # health withheld
        self.assertEqual(out["rejected_health"], 1)
        self.assertEqual(out["rejected_health_missing"], 1)
        self.assertEqual(out["rejected_health_below"], 0)

    def test_a_genuinely_weak_name_counts_as_BELOW(self):
        out = self._run({"WEAK": {"quality": 10, "growth": 80, "health": 80}})
        self.assertEqual(out["rejected_health_missing"], 0)
        self.assertEqual(out["rejected_health_below"], 1)

    def test_the_split_sums_to_the_aggregate(self):
        """A name failing BOTH ways must be counted once, under `missing`, or the sum breaks."""
        out = self._run({"BANK": {"quality": 80, "growth": 80},
                         "WEAK": {"quality": 10, "growth": 80, "health": 80},
                         "BOTH": {"quality": 10, "growth": 80}})
        self.assertEqual(out["rejected_health"], 3)
        self.assertEqual(out["rejected_health_missing"] + out["rejected_health_below"],
                         out["rejected_health"])
        self.assertEqual(out["rejected_health_missing"], 2)           # BANK and BOTH

    def test_a_healthy_name_is_counted_in_neither(self):
        out = self._run({"OK": {"quality": 80, "growth": 80, "health": 80}})
        self.assertEqual(out["rejected_health"], 0)
        self.assertEqual(out["rejected_health_missing"], 0)
        self.assertEqual(out["rejected_health_below"], 0)
        self.assertEqual(len(out["rows"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
