# -*- coding: utf-8 -*-
"""Item 57 A4's reach: large dollar figures on the valuation page go through `mcap()`.

A4 fixed `mcap()` itself and **three call sites never used it**, so the manager measured MSFT
still printing `$3,962,939,637,760` and `$331,839,000,000` live on 2026-10-14, and the growth-lens
sentence printing `$395,246mm`.

**THE SOURCE HALF OF THIS SUITE FAILS AGAINST THE PRE-FIX LINES** — that is the brief's own
requirement and it is what makes the fix checkable rather than asserted.

**AND THE FORMATTER IS EVALUATED RATHER THAN GREPPED.** `mcap` is JavaScript; re-implementing it
in Python to check it would be two definitions of one convention (`B7`), so `node` is run against
the SHIPPED `app.js` on MSFT's own measured values. Where `node` is absent the evaluation half
skips **loudly** and the source half still runs — a guard whose input is missing must not pass
while checking nothing (`guards-that-fail-open-in-ci`).
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "valuation", "web", "static", "app.js")

#: MSFT as the manager measured it on 2026-10-14, and the strings the brief asks for.
#: `market_cap` and `revenue` arrive in **$mm**; `revenue_at_horizon` likewise.
MSFT = {"market_cap_mm": 3962939.63776, "revenue_mm": 331839.0,
        "revenue_at_horizon_mm": 395246.0}
WANT = {"market_cap": "$3.96T", "revenue": "$331.84B", "revenue_at_horizon": "$395.25B"}


def _src():
    return io.open(APP, encoding="utf-8").read()


class TheThreeNamedSitesUseMcap(unittest.TestCase):
    """Each assertion names the defect it replaces, so a revert is legible in the diff."""

    def test_market_cap_goes_through_mcap(self):
        s = _src()
        self.assertIn("mcap(p.market_cap * 1e6)", s)
        self.assertNotIn("money(p.market_cap * 1e6, 0)", s)

    def test_revenue_goes_through_mcap(self):
        s = _src()
        self.assertIn("mcap(p.revenue * 1e6)", s)
        self.assertNotIn("money(p.revenue * 1e6, 0)", s)

    def test_the_growth_lens_sentence_goes_through_mcap_and_drops_the_mm_suffix(self):
        """`money(...)` + a hand-written `mm` printed `$395,246mm`. The unit belongs to the
        formatter, not to the sentence — a suffix typed beside a number is how two conventions
        get published at once."""
        s = _src()
        self.assertIn("mcap(gl.revenue_at_horizon * 1e6)", s)
        self.assertNotIn("money(gl.revenue_at_horizon, 0)}mm", s)


class TheSweepFoundAFourthSite(unittest.TestCase):
    """The brief asks for a sweep of every `money(` call on a value of $1M or more. It found one
    the brief does not name — the last-reported-quarter revenue, `money(q.revenue / 1e6, 0)` with
    a hand-written `m` — the **same** defect: a large figure divided by hand and labelled by hand.
    """

    def test_the_quarterly_revenue_goes_through_mcap(self):
        s = _src()
        self.assertIn("mcap(q.revenue)", s)
        self.assertNotIn("money(q.revenue / 1e6, 0)}m", s)

    def test_no_money_call_is_followed_by_a_hand_written_magnitude_suffix(self):
        """The general form of the defect, so a fifth site cannot appear quietly."""
        s = _src()
        bad = re.findall(r"money\([^)]*\)\}\s*(?:mm|m|bn|b|k)\b", s)
        self.assertEqual(bad, [], "hand-written magnitude suffixes: %s" % bad)

    def test_that_sweep_is_not_vacuous(self):
        """POSITIVE CONTROL: the pattern must catch the exact pre-fix forms."""
        probe = ("x = `${money(gl.revenue_at_horizon, 0)}mm over` "
                 "+ `revenue ${money(q.revenue / 1e6, 0)}m`")
        hits = re.findall(r"money\([^)]*\)\}\s*(?:mm|m|bn|b|k)\b", probe)
        self.assertEqual(len(hits), 2, "the sweep must catch both pre-fix forms, got %s" % hits)


class WhatIsDeliberatelyLeftOnMoney(unittest.TestCase):
    """**Reported rather than silently skipped.** Two families of `money(` call can exceed $1M and
    are deliberately NOT converted, because `mcap()` would destroy information the surface exists
    to show:

    * the **allocation** figures (`alloc.total`, `a.alloc`, `investedWhole`, `cashLeftWhole`) —
      amounts the user typed, where `$1.50M` instead of `$1,500,000.00` loses the dollars the tool
      is for;
    * **cumulative P&L** (`cum_pnl_dollars`) — a ledger figure where cents are the point.

    Converting either would be applying a market-cap convention to a cash amount, which is the
    wrong-object family. The boundary is stated here so a later sweep does not "finish the job".
    """

    def test_the_allocation_figures_stay_on_money(self):
        s = _src()
        self.assertIn("money(alloc.total)", s)
        self.assertIn("money(a.alloc)", s)

    def test_cumulative_pnl_stays_on_money(self):
        self.assertIn("money(Math.abs(o.cum_pnl_dollars), 0)", _src())


class McapIsEvaluatedOnMsftsOwnNumbers(unittest.TestCase):
    """The formatter is RUN against the shipped source rather than re-implemented here."""

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")

    def _eval(self, exprs):
        if not self.node:
            self.skipTest("node is not on PATH, so the shipped mcap() cannot be EVALUATED; the "
                          "source assertions above still ran and they are the half that fails "
                          "against the pre-fix lines")
        src = _src()
        # Take ONLY the formatter prelude: everything up to the tabs section. Running the whole
        # file would need a DOM, and stubbing one would be testing the stub.
        cut = src.index("/* ---------- tabs ---------- */")
        prelude = src[:cut]
        script = prelude + "\nconsole.log(JSON.stringify(%s));\n" % json.dumps(exprs).replace(
            '"', "")
        r = subprocess.run([self.node, "-e", script], capture_output=True, timeout=60)
        if r.returncode != 0:
            self.fail("node failed: %s" % r.stderr.decode("utf-8", "replace")[:400])
        return json.loads(r.stdout.decode("utf-8").strip())

    def test_mcap_renders_msfts_market_cap_revenue_and_horizon_revenue(self):
        got = self._eval("[mcap(%r * 1e6), mcap(%r * 1e6), mcap(%r * 1e6)]"
                         % (MSFT["market_cap_mm"], MSFT["revenue_mm"],
                            MSFT["revenue_at_horizon_mm"]))
        self.assertEqual(got, [WANT["market_cap"], WANT["revenue"],
                               WANT["revenue_at_horizon"]])

    def test_the_old_call_would_have_printed_the_blur_this_replaces(self):
        """NON-VACUITY: the same prelude, through `money`, reproduces the strings the manager
        measured live — so the test is comparing against the real defect and not a straw man."""
        got = self._eval("[money(%r * 1e6, 0), money(%r * 1e6, 0)]"
                         % (MSFT["market_cap_mm"], MSFT["revenue_mm"]))
        self.assertEqual(got[0], "$3,962,939,637,760")
        self.assertEqual(got[1], "$331,839,000,000")

    def test_mcap_keeps_a_sub_billion_figure_in_millions_and_a_small_one_in_dollars(self):
        got = self._eval("[mcap(450e6), mcap(1.2e9), mcap(999), mcap(null)]")
        self.assertEqual(got, ["$450M", "$1.20B", "$999", "—"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
