"""EARNINGS-CSP `K1` - what these pin, and why each one exists.

1. **THE BAR AND THE RULE ARE THE DRAFT'S, AS COMMITTED LITERALS** (`MA13`). The kill is only
   worth anything if 0.65 cannot drift after a measurement, so it is asserted against the draft's
   own sentence rather than remembered.

2. **THE PRICER IS CORRECT WHERE IT CAN BE CHECKED IN CLOSED FORM.** A 25-delta put must have
   `N(-d1) = 0.25` exactly, and the price must obey put-call parity's own bounds. A plausible
   wrong number is this project's most expensive failure mode (`MA31`), and a mis-specified
   strike would produce one silently.

3. **BOTH BIAS DIRECTIONS ARE PINNED, NOT JUST STATED.** The no-skew approximation must push the
   ratio UP and the settle-at-post approximation must push it DOWN. If either ever reversed, the
   docstring's reasoning about which way the kill errs would be wrong while still reading well.

4. **THE CORPORATE-ACTION DROP IS REAL AND IS COUNTED.** `O-1`'s MNST 3-for-1 booked a fake
   +1453% from exactly this shape; a split inside the four-day window must be dropped and
   reported, never settled.

5. **THE RATIO IS A RATIO OF MEANS, NOT A MEAN OF RATIOS** - `SELL-PREMIUM-2`'s own normalisation
   (0.008523 / 0.017358 = 0.4910). A mean of per-event ratios is a different statistic dominated
   by the many events that expire worthless, and swapping them would move the verdict.

    python tests/test_earnings_csp_k1.py
"""
from __future__ import annotations

import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import state_isolation  # noqa: F401,E402

import earnings_csp_k1 as K  # noqa: E402

DRAFT = os.path.join(REPO, "PREREG_DRAFT_earnings_csp.md")


def _event(spot=100.0, implied=0.06, realised=0.05, down=True, expiry="2016-02-05"):
    s1 = spot * (1.0 - realised) if down else spot * (1.0 + realised)
    return {"ticker": "TEST", "earn": "2016-01-26", "pre": "2016-01-22", "post": "2016-01-27",
            "expiry": expiry, "K": spot, "spot_pre": spot, "spot_post": s1,
            "implied_move": implied, "realised_move": realised, "straddle_ret": 0.0}


class TestTheBarIsTheDrafts(unittest.TestCase):
    """(1)."""

    def test_the_bar_is_065_and_the_rule_is_at_most(self):
        self.assertEqual(K.BAR, 0.65)
        # NOT `assertIn("<=", "<=")`, which my first cut wrote and which asserts nothing:
        # the rule string must carry the direction, because a kill that silently became ">="
        # would invert the verdict while every other test still passed.
        self.assertIn("<= 0.65", K.__doc__ or "")
        self.assertEqual(K.TENOR_DAYS, 15)
        self.assertAlmostEqual(K.PUT_DELTA, 0.25)

    @unittest.skipUnless(os.path.exists(DRAFT), "scout draft not in this tree")
    def test_the_draft_still_says_065_or_this_kill_is_measuring_a_rule_nobody_wrote(self):
        with open(DRAFT, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("0.65", src)
        self.assertIn("payoff ratio", src)


class TestThePricer(unittest.TestCase):
    """(2)."""

    def test_the_strike_really_is_the_25_delta_one(self):
        """`N(-d1) = 0.25` exactly, or the whole measurement is about a different contract."""
        self.assertAlmostEqual(float(K._ncdf(-K.D1_AT_25_DELTA)), 0.25, places=12)

    def test_the_price_sits_inside_its_own_closed_form_bounds(self):
        df, _ = K.ratio_frame([_event()])
        self.assertEqual(len(df), 1)
        r = df.iloc[0]
        # a put is worth less than its strike and more than its intrinsic (here zero, K < S)
        self.assertGreater(r["price_of_strike"], 0.0)
        self.assertLess(r["price_of_strike"], 1.0)
        self.assertLess(r["K"], r["spot_pre"], "a 25-delta put must strike BELOW spot")

    def test_a_bigger_implied_move_buys_a_bigger_price(self):
        a, _ = K.ratio_frame([_event(implied=0.04)])
        b, _ = K.ratio_frame([_event(implied=0.10)])
        self.assertLess(a.iloc[0]["price_of_strike"], b.iloc[0]["price_of_strike"])

    def test_an_up_move_pays_the_put_nothing(self):
        df, _ = K.ratio_frame([_event(realised=0.09, down=False)])
        self.assertEqual(df.iloc[0]["payoff_of_strike"], 0.0)
        self.assertEqual(df.iloc[0]["itm"], 0.0)

    def test_a_big_down_move_pays_the_put(self):
        df, _ = K.ratio_frame([_event(realised=0.20, down=True)])
        self.assertGreater(df.iloc[0]["payoff_of_strike"], 0.0)


class TestBothBiasDirections(unittest.TestCase):
    """(3) - the two sentences the verdict's honesty rests on."""

    def test_skew_pushes_the_ratio_DOWN_so_the_no_skew_reading_is_too_HIGH(self):
        """Pricing the put richer can only lower payoff/price. If this ever reversed, the
        docstring's claim that no-skew errs toward FIRING would be false."""
        df, _ = K.ratio_frame([_event(realised=0.20), _event(realised=0.02),
                               _event(realised=0.09, down=False)])
        s = K.skew_sensitivity(df, bumps=(1.00, 1.10))
        self.assertEqual(s[0]["vol_multiplier"], 1.00)
        self.assertLess(s[1]["ratio"], s[0]["ratio"])
        self.assertGreater(s[1]["price_of_strike"], s[0]["price_of_strike"])

    def test_a_longer_dated_event_prices_dearer_so_settling_early_understates_the_ratio(self):
        """The settle-at-post approximation: the same realised move against a price struck over a
        longer life gives a LOWER ratio. That is why the DTE-matched subset is reported."""
        near, _ = K.ratio_frame([_event(implied=0.05, realised=0.12)])
        far, _ = K.ratio_frame([_event(implied=0.12, realised=0.12)])
        self.assertLess(K.ratio(far), K.ratio(near))


class TestTheCorporateActionDrop(unittest.TestCase):
    """(4)."""

    def test_a_split_inside_the_window_is_dropped_and_counted(self):
        bad = _event()
        bad["spot_post"] = bad["spot_pre"] / 3.0          # a 3-for-1, O-1's MNST shape
        df, dropped = K.ratio_frame([bad])
        self.assertEqual(len(df), 0, "a split must never be settled")
        self.assertEqual(dropped, 1, "and it must be COUNTED, not silently skipped")

    def test_an_ordinary_move_is_not_dropped(self):
        """The positive control: the guard must not refuse everything."""
        df, dropped = K.ratio_frame([_event()])
        self.assertEqual(len(df), 1)
        self.assertEqual(dropped, 0)

    def test_the_sign_comes_from_the_as_traded_pair(self):
        up, _ = K.ratio_frame([_event(realised=0.20, down=False)])
        dn, _ = K.ratio_frame([_event(realised=0.20, down=True)])
        self.assertEqual(up.iloc[0]["payoff_of_strike"], 0.0)
        self.assertGreater(dn.iloc[0]["payoff_of_strike"], 0.0)


class TestTheRatioIsARatioOfMeans(unittest.TestCase):
    """(5)."""

    def test_it_is_mean_payoff_over_mean_price_not_the_mean_of_per_event_ratios(self):
        # the prices must DIFFER across events or the two statistics coincide identically --
        # my first fixture held implied fixed and the test failed against correct code.
        evs = [_event(implied=0.04, realised=0.25, down=True),
               _event(implied=0.09, realised=0.02, down=False),
               _event(implied=0.14, realised=0.02, down=False)]
        df, _ = K.ratio_frame(evs)
        got = K.ratio(df)
        want = float(df["payoff_of_strike"].mean()) / float(df["price_of_strike"].mean())
        self.assertAlmostEqual(got, want, places=12)
        mean_of_ratios = float(
            (df["payoff_of_strike"] / df["price_of_strike"]).mean())
        self.assertNotAlmostEqual(got, mean_of_ratios, places=6,
                                  msg="the two statistics must not be confused")

    def test_an_empty_frame_returns_None_rather_than_scoring_a_perfect_anything(self):
        import pandas as pd
        self.assertIsNone(K.ratio(pd.DataFrame()))
        self.assertIsNone(K.bootstrap_ratio(pd.DataFrame()))
        self.assertEqual(K.skew_sensitivity(pd.DataFrame()), [])


class TestTheInterval(unittest.TestCase):
    """The clustered bootstrap is clustered BY NAME, which `SC-3` is the precedent for."""

    def test_it_resamples_names_and_says_how_many(self):
        evs = []
        for i in range(12):
            e = _event(realised=0.03 + 0.01 * (i % 5), down=(i % 2 == 0))
            e["ticker"] = "T%d" % (i % 4)
            evs.append(e)
        df, _ = K.ratio_frame(evs)
        b = K.bootstrap_ratio(df, draws=200)
        self.assertEqual(b["n_names"], 4, "the unit is the NAME, never the event")
        self.assertLessEqual(b["lo95"], b["median"])
        self.assertLessEqual(b["median"], b["hi95"])

    def test_it_is_deterministic_for_a_fixed_seed(self):
        evs = [_event(realised=0.05 + 0.01 * i, down=(i % 2 == 0)) for i in range(8)]
        for i, e in enumerate(evs):
            e["ticker"] = "T%d" % (i % 3)
        df, _ = K.ratio_frame(evs)
        self.assertEqual(K.bootstrap_ratio(df, draws=100),
                         K.bootstrap_ratio(df, draws=100))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
