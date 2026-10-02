# -*- coding: utf-8 -*-
"""(F) ONE VALQUO INDEX, EVERYWHERE — the end-to-end guard.

WHAT WENT WRONG, AND WHY A SPEC WAS THE ANSWER. A Cowork scrub on 2026-10-02 found the Index tab
showing a 25-name book rebuilt from each day's scan while the forward record beneath it tracked
an 86-name quarterly book -- and `PAPER_TRACK_CONTRACT.md` §5 defines the tracked book as "the
Valquo Index exactly as the site shows it", so the contract's own premise was false. The same
scrub found a backtest of ONE construction printed beside the live curve of ANOTHER on three
surfaces, and eleven wrong statements of cadence or mechanism.

Every one of those is a surface disagreeing with another surface about which object it shows. No
single unit test catches that, because each surface is individually self-consistent. So this
suite asserts the three things the spec says must agree:

  1. the Index tab's holdings ARE the bound book,
  2. the backtest block's construction IS the tracked one,
  3. no public page states a cadence contradicting the spec.

PLUS the thresholds and the paper/sandbox distinction, which are the two places the copy drifted
twice.
"""
from __future__ import annotations

import io
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

SPEC = os.path.join(REPO, "PRODUCT_SPEC.md")
TPL = os.path.join(REPO, "valuation", "web", "templates")
JS = os.path.join(REPO, "valuation", "web", "static", "app.js")


def _read(p):
    return io.open(p, encoding="utf-8").read()


def _flat(p):
    """Whitespace-normalised, because every sentence in these files is line-wrapped and a
    literal containing a newline cannot match -- a test that fails against correct prose."""
    return " ".join(_read(p).split())


PUBLIC_PAGES = ["index.html", "methodology.html", "landing.html", "portfolio.html"]


class TheSpecExistsAndNamesTheObjects(unittest.TestCase):

    def test_the_spec_is_present_and_names_every_object(self):
        t = _flat(SPEC)
        for obj in ("Hot Stocks", "Options signals", "The Valquo Index",
                    "The forward record", "The backtest beside it"):
            self.assertIn(obj, t, obj)

    def test_the_spec_names_the_tracked_construction_and_it_MATCHES_the_code(self):
        """The spec is only worth anything if it cannot drift from the code it describes."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        t = _flat(SPEC)
        self.assertIn('BOOK_CONFIGS["taxable"]', t)
        self.assertEqual(IT.TRACKED_CONFIG, "taxable",
                         "the code's tracked construction is not the spec's")
        cfg = (S.BOOK_CONFIGS or {})[IT.TRACKED_CONFIG]
        # DECILE, QUARTERLY, 30% BAND -- checked against the config, not the prose, so renaming
        # or re-tuning the config cannot leave the spec describing a book nobody builds.
        self.assertEqual(cfg.get("top_frac"), 0.1, "the tracked config is not the decile")
        self.assertEqual(cfg.get("rebalance_days"), 63, "the tracked config is not quarterly")
        self.assertEqual(cfg.get("exit_frac"), 0.3, "the tracked config has no 30% band")
        self.assertIsNone(cfg.get("top_n"), "the tracked config is a fixed-N book")

    def test_the_spec_names_the_one_rule_that_was_broken(self):
        t = _flat(SPEC)
        self.assertIn("THE HOLDINGS, THE CURVE AND THE BACKTEST ARE ALL THE SAME BOOK", t)


class TheIndexTabShowsTheBoundBook(unittest.TestCase):
    """(1) The holdings a reader sees must come from the record, not from a scan."""

    def test_the_route_reads_the_book_in_force_and_never_a_scan_by_default(self):
        import ast
        src = _read(os.path.join(REPO, "valuation", "web", "app.py"))
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "api_valquo_index")
        # THE DOCSTRING IS DROPPED FIRST, and that is not tidiness. The route's docstring
        # QUOTES the defect it fixed -- "It called `build_index(st.load_snapshot(...))` on
        # every request" -- so an order check over the unparsed function found that quotation
        # at offset 465 and failed against a CORRECT route. Prose documenting a rule contains
        # what the rule forbids; this project has paid for that shape repeatedly.
        fn = ast.FunctionDef(
            name=fn.name, args=fn.args, decorator_list=[], returns=None, type_params=[],
            body=[st for st in fn.body
                  if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)
                          and isinstance(st.value.value, str))] or [ast.Pass()])
        ast.fix_missing_locations(fn)
        body = ast.unparse(fn)
        self.assertIn("book_in_force", body,
                      "the Index route does not read the bound book at all")
        # THE ORDER MATTERS: the book-in-force branch must come BEFORE any build_index
        # CALL, or the default would still be a rebuild.
        #
        # MEASURED ON THE CALL, NOT THE NAME. My first cut compared `body.index("build_index")`
        # against the same for `book_in_force` and failed against a CORRECT route, because the
        # `from ..edge.valquo_index import build_index` line is hoisted to the top of the
        # function -- so it was comparing an import's position with a call's. The import says
        # nothing about which branch runs first.
        self.assertLess(body.index("book_in_force("), body.index("build_index("),
                        "the route builds a book from a scan before it reads the record")
        self.assertIn("preview", body, "there is no labelled preview branch")

    def test_the_DEFAULT_request_really_RETURNS_the_book_in_force(self):
        """BEHAVIOURAL, and the structural check above is not enough on its own: disabling the
        branch with `if False:` leaves both calls in the source in the same order, so the
        order assertion still passed while every request fell through to the preview. Caught by
        mutation, not by reading."""
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        from valuation.screener import index_in_force as IF
        prior = CONFIG.owner_split
        CONFIG.owner_split = False
        real = IF.book_in_force
        IF.book_in_force = lambda **k: {
            "ok": True, "formed_on": "2026-07-30", "scan_date": "2026-07-24",
            "next_rebalance": "2026-10-22", "n_positions": 1, "n_exited": 0,
            "positions": [{"ticker": "A", "weight": 1.0, "status": "held"}]}
        try:
            app = create_saas_app()
            app.config.update(TESTING=True)
            d = app.test_client().get("/api/valquo-index").get_json() or {}
        finally:
            IF.book_in_force = real
            CONFIG.owner_split = prior
        self.assertIs(d.get("is_preview"), False,
                      "the default request returned a preview, not the book in force")
        self.assertEqual(d.get("formed_on"), "2026-07-30",
                         "the default payload carries no formation date, so it is not the book")

    def test_the_tab_sends_NO_construction_and_cannot_fall_back_to_roth(self):
        """The dropdown is gone AND the `|| "roth"` fallback is gone. Removing the element
        alone would have left the page asking for the 25-name book with nothing on screen to
        say so -- which is why both are asserted."""
        js = _read(JS)
        self.assertNotIn("bookConfig", js, "the account-type dropdown is still read")
        self.assertNotIn('/api/valquo-index?config=', js,
                         "the holdings request still names a construction")
        self.assertNotIn('/api/index-track?config=', js,
                         "the performance request still names a construction")
        self.assertNotIn('bookConfig', _read(os.path.join(TPL, "index.html")),
                         "the dropdown is still in the template")

    def test_roth_is_unreachable_from_every_public_page(self):
        """Pending Don's answer on keeping it at all, it stays in BOOK_CONFIGS for the owner
        preview and the research scripts, and is reachable from no public surface."""
        for name in PUBLIC_PAGES:
            t = _read(os.path.join(TPL, name))
            self.assertNotIn('value="roth"', t, "%s offers the roth construction" % name)
            self.assertNotIn("Roth / IRA", t, "%s names the roth book" % name)


class TheBacktestBesideTheRecordIsTheSameConstruction(unittest.TestCase):
    """(2) The defect: roth's backtest (11.63%/yr, 3.169x turnover) beside the decile's curve
    (7.75%/yr, 1.375x) -- on the Index tab, the hero AND the landing page."""

    def test_summarize_defaults_to_the_tracked_construction(self):
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        got = IT.summarize()
        self.assertEqual(got.get("config"), IT.TRACKED_CONFIG,
                         "summarize defaults to something other than the tracked book")
        want = S.measured(IT.TRACKED_CONFIG) or {}
        self.assertEqual((got.get("backtested") or {}).get("annual_turnover"),
                         want.get("annual_turnover"),
                         "the backtested block is not the tracked construction's")

    def test_it_does_NOT_default_to_the_sites_account_type_preference(self):
        """`DEFAULT_BOOK_CONFIG` is a UI preference; this card reports the backtest of the book
        the RECORD is of. They are different books and the figures differ materially."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        if S.DEFAULT_BOOK_CONFIG == IT.TRACKED_CONFIG:
            print("       (DEFAULT_BOOK_CONFIG now equals the tracked config, so this cannot "
                  "discriminate; the source check below still binds)")
        else:
            a = (S.measured(S.DEFAULT_BOOK_CONFIG) or {}).get("annual_turnover")
            b = (S.measured(IT.TRACKED_CONFIG) or {}).get("annual_turnover")
            self.assertNotEqual(a, b, "fixture assumption: the two configs differ")
            self.assertEqual((IT.summarize().get("backtested") or {}).get("annual_turnover"), b)
        import ast
        src = _read(os.path.join(REPO, "valuation", "screener", "index_track.py"))
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "summarize")
        body = ast.unparse(fn)
        self.assertIn("TRACKED_CONFIG", body)
        self.assertNotIn("DEFAULT_BOOK_CONFIG", body,
                         "summarize still reads the site's account-type preference")

    def test_the_hero_and_the_landing_page_do_not_pin_a_construction(self):
        for mod in ("hero.py", "showcase.py"):
            src = _read(os.path.join(REPO, "valuation", "web", mod))
            self.assertNotIn('summarize("roth"', src, "%s pins roth" % mod)

    def test_the_MEASURED_BASIS_caveat_is_still_carried(self):
        """It says the backtest is a full-universe EQUAL-WEIGHTED decile, not the served
        score-weighted large-cap book -- so the two are the same CONSTRUCTION and not the same
        measured object. Dropping it would make the block look like a backtest of the record."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        got = (IT.summarize().get("backtested") or {}).get("basis")
        self.assertTrue(got, "the basis caveat is gone from the payload")
        self.assertEqual(got, S.MEASURED_BASIS, "the caveat is a second spelling of itself")
        self.assertIn("not the served", got)

    def test_the_tab_no_longer_claims_the_forward_column_is_the_same_BOOK(self):
        t = _flat(os.path.join(TPL, "index.html"))
        self.assertNotIn("The forward column is the same model book", t,
                         "the tab still claims the backtest and the record are one book")
        self.assertIn("same", t)


class OneBookShownInTwoTaxTreatments(unittest.TestCase):
    """17-AMEND. The roth CONFIG is retired; "Roth/IRA" becomes a tax wrapper on the one book,
    so the cost of taxes is visible instead of being left to a reader to difference out."""

    def _tt(self):
        from valuation.screener import index_track as IT
        return ((IT.summarize().get("backtested") or {}).get("tax_treatments") or {})

    def test_both_treatments_describe_the_SAME_construction(self):
        from valuation.screener import index_track as IT
        t = self._tt()
        self.assertTrue(t, "the two-treatment block is missing")
        self.assertIs(t.get("same_book"), True)
        self.assertEqual(t.get("construction"), IT.TRACKED_CONFIG,
                         "the treatments are not of the tracked construction")
        self.assertIn("only the tax treatment differs", t.get("note", ""))

    def test_the_two_legs_come_from_the_tracked_configs_own_measurement(self):
        """Not a second computation -- the same `measured()` block, so they cannot drift from
        the backtested figures printed beside them."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        m = S.measured(IT.TRACKED_CONFIG) or {}
        t = self._tt()
        self.assertEqual(t["roth"]["alpha"], m.get("net_alpha"))
        self.assertEqual(t["roth"]["sharpe"], m.get("net_sharpe"))
        self.assertEqual(t["taxable"]["alpha"], m.get("after_tax_alpha"))
        self.assertEqual(t["taxable"]["sharpe"], m.get("after_tax_sharpe"))

    def test_the_bases_are_named_and_are_not_the_same_words(self):
        """"Net of costs, no tax" and "after tax" are the whole distinction; two legs under one
        description is how the tax cost disappeared in the first place."""
        t = self._tt()
        self.assertIn("no tax", t["roth"]["basis"])
        self.assertIn("after tax", t["taxable"]["basis"])
        self.assertNotEqual(t["roth"]["basis"], t["taxable"]["basis"])
        self.assertIn("Roth", t["roth"]["label"])
        self.assertIn("taxable", t["taxable"]["label"])

    def test_the_cost_of_taxes_is_REPORTED_and_is_the_difference(self):
        t = self._tt()
        want = round((t["roth"]["alpha"] - t["taxable"]["alpha"]) * 100.0, 4)
        self.assertEqual(t["tax_cost_pp"], want)
        self.assertGreater(t["tax_cost_pp"], 0,
                           "fixture assumption: tax costs something on this book")

    def test_a_missing_leg_reports_None_rather_than_a_zero_tax_bill(self):
        """A zero would read as "tax is free", which is the one wrong answer available here."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        real = S.measured
        S.measured = lambda *a, **k: dict(real(IT.TRACKED_CONFIG) or {},
                                          after_tax_alpha=None)
        try:
            t = ((IT.summarize().get("backtested") or {}).get("tax_treatments") or {})
        finally:
            S.measured = real
        self.assertIsNone(t.get("tax_cost_pp"))

    def test_it_says_it_is_PROVISIONAL_on_r1s_measurement(self):
        t = self._tt()
        self.assertIn("INDEX-BOOK", t.get("pending", ""))

    def test_the_spec_describes_the_two_treatments(self):
        s = _flat(SPEC)
        self.assertIn("ONE BOOK, TWO TAX TREATMENTS", s)
        self.assertIn("in a Roth/IRA", s)
        self.assertIn("in a taxable account", s)
        self.assertIn("TAX WRAPPER, not a", s)
        self.assertIn("retired from every surface", s)


class NoPublicPageStatesAContradictoryCadence(unittest.TestCase):
    """(3) The cadence claims, which is where eleven of the wrong sentences lived."""

    def test_no_page_says_the_INDEX_holdings_are_rebuilt_daily(self):
        for name in PUBLIC_PAGES:
            t = _flat(os.path.join(TPL, name))
            for bad in ("The holdings are rebuilt from each day's scan",
                        "separate, fixed book"):
                self.assertNotIn(bad, t, "%s: %r" % (name, bad))

    def test_no_page_says_the_LIVE_LIST_re_ranks_quarterly(self):
        """E1. The live list re-ranks every close; the BACKTEST re-ranked quarterly. One
        sentence giving the quarterly cadence for the live list is wrong."""
        from valuation.web import hold_horizon as HH
        t = HH.NOT_A_HOLD_RULE
        # THE QUOTED RESEARCH CLAUSE STAYS -- `tests/test_hold_horizon.py` pins that this
        # opens with §7's registered sentence verbatim, and rewriting a research sentence to
        # fix a product one is not the repair. What must be present is the SCOPE that was
        # missing: whose cadence that is, and what the other two are.
        self.assertIn("That quarterly cadence is the BACKTEST's", t)
        self.assertIn("re-ranked after every market close", t)
        self.assertIn("only at a quarterly rebalance", t)

    def test_the_index_tab_states_the_held_cadence(self):
        t = _flat(os.path.join(TPL, "index.html"))
        self.assertIn("ONE FIXED BOOK, HELD FOR THE QUARTER", t)
        self.assertIn("not a daily pick", t)

    def test_the_INDEX_record_is_not_described_as_a_broker_sandbox(self):
        """E4. Only the options book is in a sandbox. Both pages conflated them."""
        for name in ("methodology.html", "portfolio.html"):
            t = _flat(os.path.join(TPL, name))
            self.assertIn("sandbox", t, "fixture assumption: the page discusses the sandbox")
            self.assertIn("options", t.lower())
            # The giveaway phrasing: one list of "every one of them" ending in a sandbox.
            self.assertNotIn("every one of them is a paper record: a model book priced at "
                             "closing marks, and a broker sandbox", t, name)


class ThresholdsAreStatedOnce(unittest.TestCase):

    def test_the_sharpe_gate_defers_to_the_headline_gate(self):
        """E6. 20 against 60 put a Sharpe on the same card as a sentence withholding
        annualised figures."""
        from valuation.screener import index_track as IT
        self.assertEqual(IT.MIN_SHARPE_DAYS, IT.MIN_LIVE_DAYS,
                         "there are two day-count gates on one card again")

    def test_the_spec_states_the_gates_and_they_match_the_code(self):
        from valuation.screener import index_track as IT
        from valuation.screener import index_in_force as IF
        t = _flat(SPEC)
        self.assertIn("%d trading days" % IT.MIN_LIVE_DAYS, t)
        self.assertIn("%d trading days" % IF.REBALANCE_TRADING_DAYS, t)

    def test_the_recorded_series_is_described_as_GROSS(self):
        """E5. The chart said "net of modelled costs"; the record subtracts none."""
        js = _read(JS)
        self.assertIn("GROSS of costs", js)
        self.assertIn("0.14529", js, "the drag the verdict subtracts is not named")
        self.assertNotIn("net of modelled costs. No capital is invested", js)


class NumbersArePulledNotTyped(unittest.TestCase):
    """E9, E12 -- the literal-figure class."""

    def test_no_public_page_hard_codes_a_trial_count_or_the_universe_size(self):
        for name in PUBLIC_PAGES + ["_saas_base.html"]:
            t = _read(os.path.join(TPL, name))
            self.assertNotIn("~800", t, "%s hard-codes the universe size" % name)
            for n in ("248", "578", "252", "582"):
                self.assertNotIn(">%s<" % n, t,
                                 "%s hard-codes a trial count (%s)" % (name, n))

    def test_the_live_facts_degrade_to_no_number_rather_than_a_wrong_one(self):
        from valuation.web import live_facts as LF
        got = LF.universe_size(store=object())      # a store with no methods
        self.assertFalse(got["available"])
        self.assertIsNone(got["n"])
        self.assertTrue(got["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
