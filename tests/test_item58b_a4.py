# -*- coding: utf-8 -*-
"""ITEM 57 A4's MISSING HALF — the call sites, not the helper.  [item 58b]

**WHY THE FIRST ROUND OF A4 TESTS PASSED WHILE THE PAGE DID NOT CHANGE.** Every one of them
exercised `mcap()` directly. `mcap()` was correct. The company panel called `money()`. A test
that checks a helper cannot see that nothing calls it, and that is the whole lesson here — these
tests check the CALL SITES, and one of them runs the real formatter in node against the exact
strings the manager measured on MSFT on 2026-10-14.
"""
import os
import re
import shutil
import subprocess
import unittest

import state_isolation  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
APP_JS = os.path.join(HERE, "..", "valuation", "web", "static", "app.js")


def _src():
    with open(APP_JS, encoding="utf-8") as fh:
        return fh.read()


class TheCallSitesRouteThroughTheFormatter(unittest.TestCase):
    """The four company-scale figures. Each assertion names the string that was on the page."""

    def setUp(self):
        self.src = _src()

    def test_market_cap_goes_through_mcap(self):
        """Printed $3,962,939,637,760 on MSFT. Must read $3.96T."""
        self.assertIn('metric("Market cap", p.market_cap == null ? na '
                      ': mcap(p.market_cap * 1e6))', self.src)

    def test_revenue_latest_year_goes_through_mcap(self):
        """Printed $331,839,000,000. Must read $331.84B."""
        self.assertIn('metric("Revenue (latest yr)", p.revenue == null ? na '
                      ': mcap(p.revenue * 1e6))', self.src)

    def test_the_growth_lens_sentence_goes_through_mcap(self):
        """Printed $395,246mm. Must read $395.25B, with the "mm" gone."""
        self.assertIn("revenue compounds to ${mcap(gl.revenue_at_horizon * 1e6)} over",
                      self.src)
        self.assertNotIn("}mm over", self.src)

    def test_last_quarters_revenue_goes_through_mcap(self):
        """Printed $70,066m. Must read $70.07B. Found by the sweep, not by the report."""
        self.assertIn("bits.push(`revenue ${mcap(q.revenue)}`)", self.src)

    def test_none_of_the_pre_fix_forms_survives(self):
        """THE DIRECTION THAT MATTERS: each of these is what the page actually printed, so a
        revert puts the four-digit blur back and this test is the thing that notices."""
        for gone in ('money(p.market_cap * 1e6, 0)',
                     'money(p.revenue * 1e6, 0)',
                     'money(gl.revenue_at_horizon, 0)',
                     'money(q.revenue / 1e6, 0)'):
            self.assertNotIn(gone, self.src, "the pre-fix call %r is back" % gone)


class TheSweepIsComplete(unittest.TestCase):
    """Every remaining `money(` is per-share, a premium, a strike, or the user's own dollars."""

    #: THE ALLOCATION PANEL IS EXEMPT, AND THE REASON IS NOT CONVENIENCE. These are dollars the
    #: user typed. A reader checking that the parts sum to the total cannot do it in two
    #: significant figures, and rounding somebody's own money to "$1.23M" loses information
    #: they supplied. Company-scale figures are the opposite case: nobody needs a market cap
    #: to the dollar and the precision is a blur.
    USER_DOLLARS = ("alloc.total", "alloc.sum", "a.alloc", "investedWhole", "allocPriced",
                    "cashLeftWhole", "cum_pnl_dollars")

    def test_no_money_call_prints_a_company_scale_field(self):
        """A field whose NAME says it is company-scale must not reach `money`.

        Shape-based rather than a substring ban on the word `money`: this looks for `money(`
        applied to an argument naming one of these fields, so a comment mentioning the old call
        cannot trip it. The substring-ban family has cost this project repeatedly.
        """
        src = _src()
        bad = []
        for m in re.finditer(r"money\(\s*([^),]+)", src):
            arg = m.group(1)
            if any(u in arg for u in self.USER_DOLLARS):
                continue
            for field in ("market_cap", "revenue", "ebitda", "total_debt", "assets",
                          "enterprise_value", "net_income"):
                if re.search(r"\b" + field + r"\b", arg):
                    bad.append(arg.strip())
        self.assertEqual(bad, [], "company-scale fields still printed with money(): %r" % bad)

    def test_the_guard_can_actually_fire(self):
        """A POSITIVE CONTROL. Without it the test above passes by matching nothing, which is
        exactly how a sweep that checks nothing reads as a clean sweep."""
        probe = 'money(p.market_cap * 1e6, 0)'
        bad = [m.group(1).strip() for m in re.finditer(r"money\(\s*([^),]+)", probe)
               if re.search(r"\bmarket_cap\b", m.group(1))]
        self.assertEqual(len(bad), 1)


class TheFormatterItselfRunsInNode(unittest.TestCase):
    """THE STRONGEST CHECK AVAILABLE: evaluate the shipped `mcap` on the measured inputs.

    A text assertion proves the call site was repointed. This proves the output is the string
    Don will read -- and it is the check that could not have been written for the first round,
    because the first round's problem was never the function.
    """

    def test_mcap_renders_the_measured_msft_figures(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed; the text assertions above still run")
        src = _src()
        # Lift the two helpers out of the shipped file rather than retyping them -- `MA5`: a
        # retyped copy is a second definition and would pass while the real one drifted.
        mcap = re.search(r"const mcap = \(x\) => \{.*?\n\};", src, re.S)
        money = re.search(r"const money = [^\n]*\n(?:[^\n]*\n)*?[^\n]*;\n", src)
        self.assertIsNotNone(mcap, "the shipped mcap could not be located")
        prog = (src[money.start():money.end()] if money else
                "const money = (v, d = 2) => '$' + Number(v).toFixed(d);")
        prog += "\n" + mcap.group(0) + """
const out = [mcap(3962939637760), mcap(331839000000), mcap(395246 * 1e6),
             mcap(70066000000), mcap(838800000), mcap(null)];
console.log(JSON.stringify(out));
"""
        p = os.path.join(os.environ.get("TEMP") or "/tmp", "_i58b_mcap_probe.mjs")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(prog)
        try:
            # ENCODING DECLARED, NOT INHERITED. `text=True` alone decodes with the LOCALE
            # encoding, which is cp1252 on this machine -- so node's em dash came back as a
            # replacement character and this test failed against a correct file. The same
            # defect family as reading `git show` output undeclared, which has cost this
            # project a false diff before.
            got = subprocess.run([node, p], capture_output=True, text=True, timeout=30,
                                 encoding="utf-8")
            self.assertEqual(got.returncode, 0, got.stderr[:400])
            vals = __import__("json").loads(got.stdout.strip().splitlines()[-1])
        finally:
            try:
                os.remove(p)
            except OSError:
                pass
        self.assertEqual(vals[0], "$3.96T")      # was $3,962,939,637,760
        self.assertEqual(vals[1], "$331.84B")    # was $331,839,000,000
        self.assertEqual(vals[2], "$395.25B")    # was $395,246mm
        self.assertEqual(vals[3], "$70.07B")     # was $70,066m
        self.assertEqual(vals[4], "$838.80M")    # A4's own two-decimal case
        self.assertEqual(vals[5], "—")      # absent stays an em dash, never "$0"

    def test_the_whole_file_parses(self):
        """THE CHECK THAT WOULD HAVE CAUGHT MY OWN NEAR-MISS. The first cut of this fix put a
        `${/* ... */ ""}` comment at two sites that are PLAIN JS rather than inside a template
        literal -- a syntax error, which takes the entire page down rather than one panel.
        `node --check` is free and sees it; no amount of text assertion does."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        got = subprocess.run([node, "--check", os.path.abspath(APP_JS)],
                             capture_output=True, text=True, timeout=60, encoding="utf-8")
        self.assertEqual(got.returncode, 0, got.stderr[:600])


class TheDarkModeSiteTheFirstPassMissed(unittest.TestCase):
    def test_the_sensitivity_grid_default_is_a_theme_variable(self):
        """Item 57 A5's family, a fourth site. It was missed because it is a DEFAULT assigned
        to a variable rather than a colour written into a style attribute -- so a sweep of
        `style="..."` could not see it."""
        src = _src()
        self.assertIn('let bg = "var(--panel)"', src)
        self.assertNotIn('let bg = "#fff"', src)


if __name__ == "__main__":
    unittest.main()
