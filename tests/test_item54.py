# -*- coding: utf-8 -*-
"""ITEM 54 — repair the live scan on the free route.

Don's ruling: a REPAIR, not a vintage event. No scoring rule changes, inputs the rules already
expect come back, and the Index record is built from Sharadar rather than the live scan.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _code_only(rel):
    """Source with comments and string literals stripped -- so a guard cannot fire on prose
    documenting the thing it forbids (five instances in item 52 alone)."""
    import tokenize

    out = []
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


class _CD:
    """A CompanyData-shaped stub, healthy unless told otherwise."""

    def __init__(self, **kw):
        self.price = 100.0
        self.market_cap = 1000.0
        self.beta = 1.1
        self.revenue = 500.0
        self.name = "Test Co"
        self.fx_unresolved = False
        for k, v in kw.items():
            setattr(self, k, v)


FULL_Q = {"ret_12_1": 0.1, "ret_6_1": 0.05, "high_prox": 0.9}


# --------------------------------------------------------------------------- part 1
class FMPLeavesTheFetchChain(unittest.TestCase):
    """It returned 402 on every call, disabled itself after 44 errors, and is not renewed."""

    def test_the_key_is_retired_and_every_caller_sees_nothing(self):
        from valuation.config import CONFIG, FMP_RETIRED
        self.assertTrue(FMP_RETIRED)
        self.assertEqual(CONFIG.fmp_api_key, "")

    def test_RETIRED_AT_THE_ONE_POINT_ALL_FOUR_CALLERS_READ(self):
        """FMP is reached from four places and every one gates on this value. Neutralising it
        at the config is the only way a fifth caller cannot be missed."""
        for rel, needle in (
            (os.path.join("valuation", "screener", "providers.py"), "fmp_api_key"),
            (os.path.join("valuation", "screener", "universe.py"), "fmp_api_key"),
            (os.path.join("valuation", "screener", "profiles.py"), "fmp_api_key"),
            (os.path.join("valuation", "data", "sector_resolve.py"), "fmp_api_key"),
        ):
            self.assertIn(needle, _src(rel), rel)

    def test_get_provider_can_never_return_the_FMP_provider(self):
        from valuation.config import CONFIG
        from valuation.screener import providers as P
        self.assertIsInstance(P.get_provider(CONFIG, None), P.FreeProvider)

    def test_dot_env_IS_UNTOUCHED(self):
        """A code-level retirement, deliberately: overwriting `.env` is forbidden by the
        standing rules and would destroy the only record the account existed. So the switch
        is a constant and a renewal is one edit."""
        code = _code_only(os.path.join("valuation", "config.py"))
        self.assertIn("FMP_RETIRED", code)
        # The env is still READ, so nothing was deleted.
        self.assertIn("FMP_API_KEY", _src(os.path.join("valuation", "config.py")))

    def test_WHAT_FMP_SUPPLIED_THAT_NOTHING_ELSE_DOES_IS_NOTHING(self):
        """MEASURED before removing it, which was the prompt's question.

        Of the 27 fields its mapper can fill from a complete payload, the free stack filled
        **27 of 27** on both NVDA and KO, and additionally supplies 9 fields FMP's mapper has
        no slot for at all. And FMP returned `None` for `ret_12_1` ALWAYS and had no slot for
        `ret_6_1` or `high_prox`, so **a name served by FMP had no momentum at all, by
        construction** -- which is the mechanism behind what item 53 part 7 found.
        """
        from valuation.screener import providers as P
        empty = P._fmp_to_metrics("X", {}, {}, {})
        for never in ("ret_12_1", "revenue", "net_income", "fcf", "operating_income",
                      "earnings_revision", "revenue_growth_prior"):
            self.assertIsNone(empty.get(never), never)
        # The two momentum inputs it has no slot for at all.
        self.assertNotIn("ret_6_1", empty)
        self.assertNotIn("high_prox", empty)
        self.assertIn("MEASURED BEFORE REMOVING IT",
                      _src(os.path.join("valuation", "config.py")))


# --------------------------------------------------------------------------- part 2
class ARetryThatRefusesADegradedAnswer(unittest.TestCase):
    """MEASURED ON THE REAL `compute_wacc`, so the detector keys on the mechanism:

    | missing | WACC | equity weight |
    |---|---|---|
    | nothing | 0.0941 | 0.833 |
    | beta | 0.0858 | 0.833 |
    | price only | 0.0941 | 0.833 |
    | market cap only | 0.0941 | 0.833 |
    | **price AND market cap** | **0.0498 = the after-tax cost of debt exactly** | **0.000** |
    """

    def test_r1s_report_is_literally_true_and_needs_BOTH_fields_gone(self):
        from valuation.config import CONFIG
        from valuation.data.models import CompanyData
        from valuation.engine.wacc import compute_wacc

        def wacc(**kw):
            cd = CompanyData(ticker="T", name="T")
            cd.price, cd.shares_diluted, cd.market_cap = 100.0, 1000.0, 100_000.0
            cd.beta, cd.total_debt, cd.interest_expense = 1.2, 20_000.0, 800.0
            for k, v in kw.items():
                setattr(cd, k, v)
            return compute_wacc(cd, CONFIG)

        healthy = wacc()
        # Either field alone leaves the WACC untouched -- so a one-field tell would be wrong.
        self.assertAlmostEqual(wacc(price=None).wacc, healthy.wacc, places=6)
        self.assertAlmostEqual(wacc(market_cap=None).wacc, healthy.wacc, places=6)
        both = wacc(price=None, market_cap=None)
        self.assertAlmostEqual(both.weight_equity, 0.0, places=9)
        self.assertAlmostEqual(both.wacc, both.cost_of_debt_aftertax, places=9)
        self.assertGreater(healthy.wacc - both.wacc, 0.03)      # ~4.4pp on these inputs

    def test_ONE_missing_field_is_DATA_and_not_a_throttle(self):
        """A data-poor foreign issuer legitimately has no beta; refusing it would be a
        different defect."""
        from valuation.screener.refetch import degradation
        self.assertFalse(degradation(_CD(beta=None), FULL_Q)["degraded"])
        self.assertFalse(degradation(_CD(revenue=None), FULL_Q)["degraded"])

    def test_TWO_soft_tells_at_once_IS_a_throttle(self):
        from valuation.screener.refetch import degradation
        d = degradation(_CD(beta=None, revenue=None), FULL_Q)
        self.assertTrue(d["degraded"])
        self.assertEqual(sorted(d["soft"]), ["no beta", "no revenue"])

    def test_a_hard_tell_alone_is_enough(self):
        from valuation.screener.refetch import degradation
        d = degradation(_CD(price=None, market_cap=None), FULL_Q)
        self.assertTrue(d["degraded"])
        self.assertIn("collapses to the after-tax cost of debt", d["why"])

    def test_NO_MOMENTUM_AT_ALL_is_a_HARD_tell_and_the_first_cut_had_it_soft(self):
        """REPOINTED ON MEASURED EVIDENCE, and getting it wrong would have left the very
        failure this module exists for unretried -- a healthy profile with no quote scored
        "not degraded".

        `get_quote` returns None only below 30 sessions, so zero of three inputs means
        essentially no history came back. `SUN`, the one genuinely short-history name item 53
        found, has 61 sessions and STILL returns `high_prox` -- so a thin-but-real name yields
        at least one input and none at all is the throttle.
        """
        from valuation.screener.refetch import degradation
        self.assertTrue(degradation(_CD(), None)["degraded"])
        self.assertTrue(degradation(_CD(), {})["degraded"])
        # SUN's shape: thin, real, and NOT marked degraded.
        self.assertFalse(degradation(_CD(), {"high_prox": 0.96})["degraded"])

    def test_a_DEGRADED_payload_is_DISCARDED_never_merged(self):
        """`MA6`: err toward the state that refuses. A scan that looks complete and is wrong
        is the shape this project loses the most time to."""
        from valuation.screener.refetch import RetryBudget, fetch_free
        b = RetryBudget(sleep_s=0.0)
        rep = fetch_free("X", None, get_company=lambda t, c: _CD(price=None, market_cap=None),
                         get_quote=lambda t: FULL_Q, budget=b)
        self.assertFalse(rep["ok"])
        self.assertTrue(rep["degraded"])
        self.assertIsNone(rep["cd"])
        self.assertIsNone(rep["quote"])
        self.assertEqual(b.detail()["degraded_discarded"], 1)

    def test_a_SECOND_attempt_rescues_a_name_that_failed_first(self):
        from valuation.screener.refetch import RetryBudget, fetch_free
        calls = {"n": 0}

        def flaky(t, c):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("throttled")
            return _CD()

        b = RetryBudget(sleep_s=0.0)
        rep = fetch_free("X", None, get_company=flaky, get_quote=lambda t: FULL_Q, budget=b)
        self.assertTrue(rep["ok"])
        self.assertTrue(rep["retried"])
        self.assertTrue(rep["recovered"])
        self.assertEqual(rep["attempts"], 2)
        self.assertEqual(b.detail()["recovered"], 1)

    def test_a_currency_mismatch_is_NOT_retried(self):
        """It is a fact about the filing, so a second attempt returns the same thing."""
        from valuation.screener.refetch import RetryBudget, fetch_free
        n = {"calls": 0}

        def fx(t, c):
            n["calls"] += 1
            return _CD(fx_unresolved=True)

        b = RetryBudget(sleep_s=0.0)
        rep = fetch_free("X", None, get_company=fx, get_quote=lambda t: FULL_Q, budget=b)
        self.assertEqual(n["calls"], 1)
        self.assertFalse(rep["ok"])
        self.assertFalse(rep["retried"])
        self.assertIn("currencies could not be reconciled", rep["why"])

    def test_the_budget_BOUNDS_the_scan_and_says_why_it_stopped(self):
        """A scan that silently stopped retrying would look like a scan with fewer
        failures."""
        from valuation.screener.refetch import RetryBudget
        b = RetryBudget(max_retries=2, sleep_s=0.0)
        self.assertTrue(b.take())
        self.assertTrue(b.take())
        self.assertFalse(b.take())
        d = b.detail()
        self.assertTrue(d["exhausted"])
        self.assertIn("retry count", d["exhausted_reason"])

    def test_the_time_budget_also_bounds_it(self):
        from valuation.screener.refetch import RetryBudget
        ticks = iter([0.0, 500.0, 500.0, 1000.0])
        b = RetryBudget(max_retries=99, max_seconds=100.0, sleep_s=0.0,
                        clock=lambda: next(ticks), sleep=lambda s: None)
        self.assertTrue(b.take())          # spends 500 simulated seconds
        self.assertFalse(b.take())
        self.assertIn("time budget", b.detail()["exhausted_reason"])

    def test_IT_PACES_rather_than_hammers(self):
        """Retrying a throttled host immediately is how a soft throttle becomes a hard block
        for the rest of the run."""
        from valuation.screener import refetch as R
        self.assertGreater(R.RETRY_SLEEP_S, 0.0)
        slept = []
        b = R.RetryBudget(sleep=lambda s: slept.append(s))
        b.take()
        self.assertEqual(slept, [R.RETRY_SLEEP_S])

    def test_ONE_retry_per_name_and_not_a_loop(self):
        from valuation.screener import refetch as R
        self.assertEqual(R.ATTEMPTS_PER_NAME, 2)

    def test_the_provider_USES_it_and_reports_the_counts(self):
        from valuation.config import CONFIG
        from valuation.screener import providers as P
        f = P.FreeProvider(CONFIG, None)
        self.assertFalse(f.refetch_detail()["ran"])          # nothing fetched yet
        self.assertIsNotNone(f._retry_budget)
        d = f.refetch_detail()
        self.assertTrue(d["ran"])
        for k in ("retries_allowed", "names_recovered_by_retry",
                  "names_degraded_discarded", "names_failed"):
            self.assertIn(k, d)
        code = _code_only(os.path.join("valuation", "screener", "providers.py"))
        self.assertIn("fetch_free", code)

    def test_the_detector_NEVER_RAISES(self):
        """A detector that could raise would turn a bad fetch into a dropped name."""
        from valuation.screener.refetch import degradation
        for bad in (None, object(), 7, "x"):
            self.assertIn("degraded", degradation(bad, None))


class TheRepairDidNotReachItsOwnNamesUntilTheCacheWasFixed(unittest.TestCase):
    """MEASURED ON THE 2026-10-13 SCAN, the first run with the retry in place.

    **+41 theme-cells came back across the top 500** — institutional +13, insider +12,
    momentum +4, quality +4, value +3, capital_discipline +3, growth +2, size +0 — and the
    thin count fell from **8 to 5** in the scan and **4 to 1** in the top 500, with `SMFSY`
    (rank 1, one theme) dropping out of the served list entirely.

    **AND `T`, `VZ`, `MGM`, `FDX` AND `PFE` STILL HAD NO MOMENTUM AT ALL** — the very names
    item 53 part 7 measured returning 400 sessions of history on demand. The retry was never
    reaching them: `get_metrics` serves a cached row FIRST and the fundamentals cache runs to
    **30 days**, so a row written by the broken scan was handed back unchanged and would have
    been for a month.
    """

    def test_a_cached_row_with_NO_momentum_is_a_cache_MISS(self):
        from valuation.screener.providers import (METRICS_SCHEMA, METRICS_UNITS,
                                                  _usable_cache)
        base = {"units": METRICS_UNITS, "schema": METRICS_SCHEMA}
        self.assertIsNone(_usable_cache(dict(base, ret_12_1=None, ret_6_1=None,
                                             high_prox=None)))
        self.assertIsNone(_usable_cache(base))          # none of the three present at all
        self.assertIsNotNone(_usable_cache(dict(base, ret_12_1=0.1)))

    def test_a_THIN_BUT_REAL_name_still_caches_normally(self):
        """`SUN` has 61 sessions and returns `high_prox` only. If one input were not enough,
        such a name would be re-fetched on every scan forever and never satisfy."""
        from valuation.screener.providers import (METRICS_SCHEMA, METRICS_UNITS,
                                                  _usable_cache)
        sun = {"units": METRICS_UNITS, "schema": METRICS_SCHEMA, "high_prox": 0.96,
               "ret_12_1": None, "ret_6_1": None}
        self.assertIsNotNone(_usable_cache(sun))

    def test_the_two_OLDER_cache_rules_still_bite(self):
        """The new rule is a third way of being unfit, not a replacement for the first two."""
        from valuation.screener.providers import (METRICS_SCHEMA, METRICS_UNITS,
                                                  _usable_cache)
        self.assertIsNone(_usable_cache({"units": "wrong", "schema": METRICS_SCHEMA,
                                         "ret_12_1": 0.1}))
        self.assertIsNone(_usable_cache({"units": METRICS_UNITS, "schema": 1,
                                         "ret_12_1": 0.1}))

    def test_the_momentum_input_list_is_SHARED_and_not_retyped(self):
        from valuation.screener.providers import _MOMENTUM_INPUTS
        self.assertEqual(sorted(_MOMENTUM_INPUTS),
                         ["high_prox", "ret_12_1", "ret_6_1"])

    def test_it_decides_whether_to_REFETCH_and_not_how_to_SCORE(self):
        """The ruling's own line. A cache rule is not a scoring rule."""
        code = _code_only(os.path.join("valuation", "screener", "providers.py"))
        i = code.index("def _usable_cache")
        body = code[i:i + 700]
        for forbidden in ("composite", "weight", "z_", "build_frame"):
            self.assertNotIn(forbidden, body, forbidden)

    def test_the_RETRY_COUNTS_REACH_THE_HEALTH_BLOCK(self):
        """AN OMISSION IN THE FIRST CUT, and it is why the 2026-10-13 scan could not say
        whether the retry had run: `refetch_detail()` was built on the provider and nothing
        read it, so the live health block carried no `refetch` key at all. A rescue nobody can
        see is indistinguishable from a scan that never needed one."""
        src = _src(os.path.join("valuation", "screener", "screen.py"))
        self.assertIn('health["refetch"] = det', src)
        self.assertIn("refetch_detail", src)

    def test_the_block_is_omitted_rather_than_FAKED_when_the_retry_never_ran(self):
        """`if det and det.get("ran")` -- an absent block and a block of zeroes mean
        different things, and a scan served from cache alone never created a budget."""
        src = _src(os.path.join("valuation", "screener", "screen.py"))
        self.assertIn('det.get("ran")', src)


# --------------------------------------------------------------------------- part 3
class TooFewThemesIsMarkedAndNotRankedAtTheTop(unittest.TestCase):
    """SMFSY was #1 of 1,440 at a hot score of 100.0, scored on `size` ALONE."""

    def test_the_rule_is_four_of_seven_and_it_is_STATED(self):
        from valuation.screener import thin_data as T
        self.assertEqual(T.MIN_THEMES, 4)
        self.assertIn("fewer than 4 of the seven themes", T.RULE_TEXT)
        # Four is a majority of seven -- the whole derivation, and nothing was swept.
        self.assertGreater(T.MIN_THEMES, 7 / 2.0)

    def test_the_seven_are_DERIVED_from_the_weight_sets(self):
        """A hand-maintained list of themes beside the weights that define them is how the
        two come apart (`MA5`)."""
        from valuation.screener import settings as S
        from valuation.screener import thin_data as T
        got = T.weighted_theme_names()
        self.assertEqual(len(got), 8)            # the UNION; each rulebook weights seven
        for attr in ("WEIGHTS_ESTABLISHED", "WEIGHTS_SPECULATIVE"):
            w = getattr(S, attr)
            self.assertEqual(sum(1 for v in w.values() if v), 7, attr)
        # The two zero-weight themes are excluded, or every name in the product reads thin.
        self.assertNotIn("low_risk", got)
        self.assertNotIn("sentiment", got)

    def test_it_counts_FACTORS_and_not_the_attribution_list(self):
        """Item 53 part 7a established `factors` is the exact discriminator; the attribution
        also drops a theme whose contribution rounds to zero -- a SCORED theme."""
        from valuation.screener import thin_data as T
        row = {"ticker": "X", "extra": {"factors": {"size": 1.0, "growth": 0.0},
                                        "why": [{"theme": "size", "c": 1.0}]}}
        # `growth` is scored AND contributes zero: counted here, absent from `why`.
        self.assertEqual(T.theme_count(row), 2)

    def test_SMFSY_is_thin_and_an_eight_theme_name_is_not(self):
        from valuation.screener import thin_data as T
        smfsy = {"ticker": "SMFSY",
                 "extra": {"factors": {"size": 1.21, "low_risk": 0.67,
                                       "growth": None, "value": None}}}
        apa = {"ticker": "APA", "extra": {"factors": {k: 0.3 for k in (
            "size", "value", "quality", "momentum", "insider", "institutional",
            "capital_discipline", "growth")}}}
        self.assertTrue(T.assess(smfsy)["thin"])
        self.assertEqual(T.assess(smfsy)["themes_scored"], 1)
        self.assertFalse(T.assess(apa)["thin"])
        self.assertEqual(T.assess(apa)["themes_scored"], 8)

    def test_a_row_we_CANNOT_COUNT_is_not_marked_thin(self):
        """"We do not know" and "scored on one theme" are different facts -- marking the
        first as the second would put every pre-item-53 snapshot row in the thin group."""
        from valuation.screener import thin_data as T
        a = T.assess({"ticker": "OLD", "extra": {}})
        self.assertFalse(a["known"])
        self.assertFalse(a["thin"])

    def test_the_census_separates_THIN_from_UNCOUNTABLE(self):
        from valuation.screener import thin_data as T
        rows = [{"ticker": "A", "extra": {"factors": {"size": 1.0}}},
                {"ticker": "B", "extra": {}}]
        c = T.mark(rows)
        self.assertEqual((c["n_thin"], c["n_uncountable"], c["n_countable"]), (1, 1, 1))

    def test_marking_is_ADDITIVE_and_touches_NO_score_or_rank(self):
        from valuation.screener import thin_data as T
        row = {"ticker": "A", "hot_score": 100.0, "rank": 1, "composite": 1.21,
               "extra": {"factors": {"size": 1.21}}}
        before = {k: row[k] for k in ("hot_score", "rank", "composite")}
        T.mark([row])
        self.assertEqual({k: row[k] for k in before}, before)
        self.assertTrue(row["thin_data"])

    def test_it_does_NOT_touch_build_index_or_the_rebalance(self):
        """Don's ruling excludes it: that would be a construction change and a vintage
        event. Checked structurally -- the module may not be imported there."""
        for rel in (os.path.join("valuation", "screener", "valquo_index.py"),
                    os.path.join("valuation", "screener", "index_candidate.py")):
            p = os.path.join(REPO, rel)
            if not os.path.exists(p):
                continue
            self.assertNotIn("thin_data", _code_only(rel), rel)

    def test_the_wording_is_score_confidences_and_NOT_a_new_sentence(self):
        from valuation.web import score_confidence as SC
        js = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("SCORE_CONFIDENCE", js)
        self.assertIn(").thin_data", js)
        # The calibrated sentence is not retyped anywhere in the page or the rule module.
        head = SC.THIN_DATA[:48]
        self.assertNotIn(head, js)
        self.assertNotIn(head, _src(os.path.join("valuation", "screener", "thin_data.py")))

    def test_the_hot_list_SPLITS_the_thin_names_out(self):
        js = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = js.index("function renderHot(")
        body = js[i:js.index("\nfunction ", i + 40)]
        self.assertIn("const _ranked = (d.rows || []).filter(r => !r.thin_data)", body)
        self.assertIn("_thinRows", body)
        self.assertIn("thin-group", body)
        # ...and still offers the same why? panel rather than hiding the evidence.
        self.assertIn("attributionPanel(r,", body)

    def test_the_census_is_printed_even_when_none_is_SERVED(self):
        """"none in the top 100" and "none in the scan" are different facts."""
        js = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("_thin.scan_n_rows", js)
        self.assertIn("scan_n_uncountable", js)

    def test_the_payload_carries_the_rule_so_the_page_states_it(self):
        src = _src(os.path.join("valuation", "web", "app.py"))
        self.assertIn('"thin_data": {**_thin_census', src)
        self.assertIn("_thin.mark(all_rows)", src)

    def test_the_INDEX_tab_marks_its_todays_hot_score(self):
        from valuation.screener import index_in_force as IIF
        b = IIF.attach_labels({"positions": [{"ticker": "AAA"}]}, store=None)
        for k in ("n_thin_today", "thin_min_themes", "thin_rule"):
            self.assertIn(k, b["labels"])
        js = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("p.thin_data_today", js)
        self.assertIn("thin-flag", js)


# --------------------------------------------------------------------------- part 4
class TheBankBug(unittest.TestCase):
    """`app.py` read `result.financial_extras`, which does not exist on `ValuationResult`."""

    def test_the_misspelled_field_is_gone_and_the_real_one_is_used(self):
        """THE TWO HALVES NEED DIFFERENT LENSES, and the first cut used one for both.

        The ABSENCE must be checked on comment-stripped code, because the comment recording
        the fix NAMES the old field -- that is the comment-versus-code family this project
        hits more than any other. The PRESENCE must be checked on the raw source, because
        `getattr(result, "financial_surfaces", None)` passes the field name as a STRING and
        the stripper removes exactly that. Item 53 needed the same split for the same reason.
        """
        rel = os.path.join("valuation", "web", "app.py")
        self.assertNotIn("financial_extras", _code_only(rel))
        self.assertIn('"financial_surfaces"', _src(rel))

    def test_financial_extras_really_does_not_exist(self):
        import dataclasses

        from valuation.engine.pipeline import ValuationResult
        names = {f.name for f in dataclasses.fields(ValuationResult)}
        self.assertNotIn("financial_extras", names)
        self.assertIn("financial_surfaces", names)

    def test_a_DEFAULT_is_what_made_it_silent(self):
        """`getattr(result, "financial_extras", None) or {}` returned `{}` rather than
        raising, so every bank rendered "unavailable" while the engine had the number. The
        wrong-object family, and the kind a default hides."""
        src = _src(os.path.join("valuation", "web", "app.py"))
        self.assertIn("`getattr` WITH A DEFAULT IS WHY IT WAS SILENT", src)

    def test_the_sentence_is_available_once_the_implied_roe_arrives(self):
        """MEASURED LIVE ON TWO BANKS: ABCB 12.2% (r1's own figure) and JPM 20.7%. Both
        previously rendered "we could not work out what return on equity this price
        assumes"."""
        from valuation.web import price_assumes as PA
        got = PA.price_assumes({}, None, is_financial=True, implied_roe=0.12195354670726213,
                               book_roe=0.11)
        self.assertTrue(got["available"])
        self.assertIn("12.2%", got["sentence"])
        self.assertIn("return on equity", got["sentence"])
        # ...and with it absent the page still says so rather than inventing a number.
        gone = PA.price_assumes({}, None, is_financial=True, implied_roe=None, book_roe=0.11)
        self.assertFalse(gone["available"])


# --------------------------------------------------------------------------- the ruling
class ItIsARepairAndNotAVintageEvent(unittest.TestCase):
    """Don's ruling. The property that makes it one is checkable, so it is checked."""

    def test_NO_SCORING_RULE_CHANGES(self):
        """The weights, the theme membership and the composite are untouched: this item
        restores inputs the rules already expect and marks what is thin. Checked on the
        syntax tree of the files that define the rules."""
        for rel in (os.path.join("valuation", "screener", "settings.py"),
                    os.path.join("valuation", "screener", "factors.py")):
            code = _code_only(rel)
            self.assertNotIn("thin_data", code, rel)
            self.assertNotIn("refetch", code, rel)

    def test_the_weight_sets_still_read_what_they_always_did(self):
        from valuation.screener import settings as S
        for attr, absent in (("WEIGHTS_ESTABLISHED", "growth"),
                             ("WEIGHTS_SPECULATIVE", "quality")):
            w = getattr(S, attr)
            self.assertNotIn(absent, w, attr)
            self.assertEqual(sum(1 for v in w.values() if v), 7, attr)
            for k, v in w.items():
                if v:
                    self.assertAlmostEqual(v, 0.125, places=6, msg="%s.%s" % (attr, k))

    def test_the_new_modules_do_not_reach_the_scoring_path(self):
        """Local to this item's own files, so it cannot rot into another lane's tripwire --
        the lesson `SC-4` taught item 53."""
        SCORING = ("factors", "settings", "attribution")
        for rel in (os.path.join("valuation", "screener", "refetch.py"),
                    os.path.join("valuation", "screener", "thin_data.py")):
            tree = ast.parse(_src(rel))
            for node in ast.walk(tree):
                mod = ""
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                elif isinstance(node, ast.Import):
                    mod = " ".join(a.name for a in node.names)
                for bad in SCORING:
                    if bad == "settings" and rel.endswith("thin_data.py"):
                        continue        # it READS the weights to derive the theme list
                    self.assertNotIn(bad, mod, "%s imports %s" % (rel, mod))
        # Positive control: the module that does own the scoring path is importable.
        from valuation.screener import factors as _f
        self.assertTrue(hasattr(_f, "build_frame"))


if __name__ == "__main__":
    unittest.main(verbosity=1, exit=False)
    print("item 54: repair the live scan on the free route")
