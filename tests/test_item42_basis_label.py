# -*- coding: utf-8 -*-
"""ITEM 42 — Don's two rulings of 2026-10-08, pinned.

1. **The 52-week high STAYS on the split- and dividend-adjusted basis**, "labelled on the page
   as a drop that includes dividends". So **no figure moves**; what ships is the sentence that
   makes the figure mean what it says. The ruling asks for the wording to be pinned by test,
   which is what this file is.

2. **Intraday stays on GitHub's free scheduler** and "afternoon-only delivery is accepted", with
   the live check still "reporting honestly". The Signals tab said it *"Refreshes through the
   day"* — item 37 measured that to be false (176 slots, 49 runs, 72.2% dropped; 21 of 22
   sessions with no in-session run before 17:00 UTC), so the claim is corrected and the live
   check is left exactly as strict as it was.

WHY THE LABEL MATTERS, and it is a measured number rather than a nicety: at yfinance 1.6.0 on
2026-10-08 the AS-TRADED 52-week high sits **+3.15% above** the adjusted one for a monthly-paying
REIT (O), +0.60% for KO, +0.12% for GOOGL. An adjusted high divided into a price is a
TOTAL-RETURN drawdown and reads SMALLER than the share-price fall by roughly the trailing yield
— so a reader checking the shown percentage against a price chart finds them disagreeing, worst
on exactly the high-yield names this screen surfaces.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.web import dip                                              # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(REPO, "valuation", "web", "templates", "index.html")
JS = os.path.join(REPO, "valuation", "web", "static", "app.js")


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def flowed(text):
    """Line breaks collapsed, so a needle may span a wrap in prose or markup."""
    return " ".join(text.split())


def rendered(text):
    """The template with its Jinja and HTML COMMENTS removed -- what a user can actually see.

    THE DEFECT THIS EXISTS FOR, found by running it: the "promises no clock time" ban below
    fired on my OWN `{# ... #}` comment, which cites "17:00 UTC" as part of item 37's
    measurement. That is the comment-versus-code family -- a ban tripped by the prose that
    documents the rule -- and the property is about what RENDERS, not about what the file says.
    """
    import re
    out = re.sub(r"\{#.*?#\}", " ", text, flags=re.S)
    out = re.sub(r"<!--.*?-->", " ", out, flags=re.S)
    return " ".join(out.split())


OK = {"quality": 80.0, "health": 80.0, "growth": 80.0}


def row(t, prox=0.70):
    return {"ticker": t, "name": t, "price": 50.0, "market_cap": 5e9, "hot_score": 60,
            "rank": 1, "z_quality": 0.5, "extra": {"high_prox": prox}}


def meas():
    return {"drawdown": 0.30, "price": 50.0, "high_52w": 71.4, "subs": dict(OK),
            "cash_burning": False, "score": 70, "confidence": "high", "fair_value": 80.0,
            "upside": 0.6, "fair_value_low": 60.0, "fair_value_high": 100.0,
            "fair_value_withheld_reason": None, "regime": "mature",
            "health_not_scored": False, "high_source": "yahoo", "high_basis": "adjusted",
            "high_reason": None,
            "checks": {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                       "terminal_share": dip.PASS}}


def screen():
    return dip.screen([row("A")], min_drawdown=0.20,
                      measure=lambda r: meas(), shortlist=0)


class TheBasisIsLabelledAndServed(unittest.TestCase):

    def test_the_payload_declares_the_basis_as_a_MACHINE_field_too(self):
        """A caller reading JSON never sees the page's sentence, so the basis has to be a field
        as well as prose — and a field is what a future comparison can branch on."""
        out = screen()
        self.assertEqual(out["drawdown_basis"], "split_and_dividend_adjusted")

    def test_the_sentence_is_served_and_says_dividends_are_included(self):
        out = screen()
        self.assertEqual(out["drawdown_basis_note"], dip.DRAWDOWN_BASIS_NOTE)
        note = out["drawdown_basis_note"].lower()
        self.assertIn("includes dividends", note)
        self.assertIn("total-return drawdown", note)

    def test_it_says_which_WAY_the_difference_goes(self):
        """"Includes dividends" alone does not tell a reader whether the number is bigger or
        smaller than the price fall they can see on a chart. It is SMALLER."""
        note = dip.DRAWDOWN_BASIS_NOTE.lower()
        self.assertIn("smaller", note)

    def test_it_gives_the_SIZE_of_the_difference_measured_not_adjectival(self):
        """A reader cannot judge "slightly" without a number. 3% for a monthly REIT, <1%
        typical — the figures item 39 measured."""
        note = dip.DRAWDOWN_BASIS_NOTE
        self.assertIn("3%", note)
        self.assertIn("1%", note)

    def test_it_says_WHY_the_adjusted_basis_was_kept(self):
        """Don's ruling gives two reasons — the research was measured on it, and an as-traded
        series makes a split look like a crash. Both travel, or the label reads as an apology
        for a defect rather than a statement of a choice."""
        note = dip.DRAWDOWN_BASIS_NOTE.lower()
        self.assertIn("research", note)
        self.assertIn("split", note)

    def test_the_API_FIELD_description_carries_the_same_fact(self):
        out = screen()
        self.assertEqual(out["field_notes"]["drawdown"], dip.DRAWDOWN_FIELD_NOTE)
        d = dip.DRAWDOWN_FIELD_NOTE.lower()
        self.assertIn("dividend-adjusted", d)
        self.assertIn("252-session", d)

    def test_NO_FIGURE_MOVED_which_is_the_ruling(self):
        """The high STAYS adjusted. `auto_adjust=True` is what item 39 pinned and what the
        ruling keeps, so this item must not have changed any number."""
        out = screen()
        self.assertAlmostEqual(out["rows"][0]["drawdown"], 0.30, places=10)
        src = read(os.path.join(REPO, "valuation", "data", "yahoo.py"))
        self.assertIn('auto_adjust=True', src)


class ThePageRendersTheServersWording(unittest.TestCase):

    def test_the_template_holds_an_EMPTY_slot_and_no_copy_of_its_own(self):
        """`dip_posture.py`'s rule: prose in a template does not stop when a ruling changes."""
        tpl = read(TPL)
        self.assertIn('id="dipBasis"', tpl)
        self.assertNotIn("INCLUDES DIVIDENDS", tpl)
        self.assertNotIn("total-return drawdown", tpl)

    def test_the_js_fills_it_from_the_payload(self):
        js = read(JS)
        self.assertIn('setHtml("dipBasis"', js)
        self.assertIn("d.drawdown_basis_note", js)

    def test_it_sits_NEAR_THE_THRESHOLD_CONTROL_which_is_where_20pc_is_chosen(self):
        """The ruling says "near the threshold control" — that is where a reader decides what
        the number means, and a note at the bottom of a long table is not near anything."""
        tpl = flowed(read(TPL))
        i_sel = tpl.index('id="dipThreshold"')
        i_note = tpl.index('id="dipBasis"')
        self.assertGreater(i_note, i_sel, "the basis note is before the control")
        between = tpl[i_sel:i_note]
        self.assertNotIn('id="dipResults"', between,
                         "the basis note drifted past the results table")


class TheSignalsTabNoLongerClaimsAllDayRuns(unittest.TestCase):

    def test_the_refreshes_through_the_day_claim_is_GONE(self):
        """Item 37 measured 72.2% of intraday slots producing no run and 21 of 22 sessions with
        nothing before 17:00 UTC. On 2026-10-08 `/api/signals` read `run_time 00:20`."""
        tpl = flowed(read(TPL))
        self.assertNotIn("Refreshes through the day", tpl)

    def test_it_says_the_honest_shape_instead(self):
        tpl = flowed(read(TPL)).lower()
        self.assertIn("free scheduler", tpl)
        self.assertIn("afternoon or evening", tpl)
        self.assertIn("may be hours old", tpl)

    def test_it_names_no_specific_HOUR_which_would_rot(self):
        """The delivery window moves with GitHub's load; a sentence promising "by 2pm" is the
        same defect one level down. The run TIME is rendered from the payload's freshness
        banner, so the prose says the shape and the data says the hour."""
        tpl = rendered(read(TPL))
        i = tpl.index("free scheduler")
        window = tpl[i - 400:i + 400]
        for rot in ("17:00", "2pm", "4pm", "by noon", "every 30"):
            self.assertNotIn(rot, window, "the Signals copy promises a clock time: %r" % rot)


class TheLiveCheckIsNOTWeakened(unittest.TestCase):
    """Don's ruling is explicit: *"The live check keeps reporting honestly."*

    So the in-session signals check must still FAIL when no run landed in the window — which it
    did today, and which is now the expected steady state rather than a bug. Accepting
    afternoon-only delivery is a decision about the PRODUCT, not permission to stop measuring.
    """

    def test_the_in_session_window_check_still_exists_and_still_fails(self):
        src = read(os.path.join(REPO, "scripts", "live_check.py"))
        self.assertIn("signals ran during today's session", src)
        # The window is still asserted, not softened to "ran at all" -- and it is read from the
        # market-calendar CONSTANTS rather than a literal hour, which is the better property:
        # the first cut of this test asserted "13:00" and failed, because the check formats
        # those constants rather than spelling the time. A guard on the formatting would have
        # gone red the day the window moved legitimately.
        self.assertIn("MARKET_OPEN_UTC <= t <= MARKET_CLOSE_UTC", src)
        self.assertIn("MARKET_OPEN_UTC", src)
        self.assertIn("MARKET_CLOSE_UTC", src)

    def test_nothing_in_this_item_touched_the_live_check(self):
        """A ruling that accepts a failure is not a ruling to stop detecting it. Pinned by
        asserting the check's own bad-path message survives verbatim."""
        src = read(os.path.join(REPO, "scripts", "live_check.py"))
        self.assertIn("want %s between", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
