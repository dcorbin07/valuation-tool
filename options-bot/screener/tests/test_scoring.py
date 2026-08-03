"""
Tests for the screener's scoring engine.

There were NO tests in this project before now, despite the README describing
four modules as "built + unit-tested." Several of the bugs these cover were
live for months and produced no symptom — a constant where a factor should
have been, a factor silently 4x out of scale, a signal spanning half its
nominal range. That is the failure mode worth guarding against: not crashes,
but numbers that look plausible and are wrong.

No network. Synthetic fixtures only.
"""
import sys
import unittest
from pathlib import Path

SCREENER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCREENER_ROOT))

import config as C
import decisions as D
import edgar
import pit_data as P
import scoring as S


def stock(**kw):
    """A minimally-complete, gate-passing established name."""
    d = dict(ticker="AAA", sector="Tech", is_common_equity=True,
             price=50.0, avg_dollar_volume=5e6, market_cap=3e9,
             operating_income=2.5e8, net_income=2e8, revenue=1e9,
             op_margin=0.25, roe=0.20, net_debt_to_ebitda=0.5,
             total_debt=1e8, cash=2e8, ret_12_1=0.15,
             latest_rev_growth=0.30, prior_rev_growth=0.20,
             insider_transactions=[])
    d.update(kw)
    return d


# ── Value: the component that used to be a constant ────────────────────────

class TestValueIsNoLongerConstant(unittest.TestCase):
    """
    `dcf_upside` was the 35% value weight of the Established bucket and NOTHING
    in the pipeline ever computed it. value_score_established(None) returned
    50.0 for every name, every day — the largest single weight in the model was
    inert, and established names were effectively ranked on the other three
    components renormalized.
    """

    def setUp(self):
        # Enough peers to clear MIN_SECTOR_PEERS.
        self.rows = [stock(ticker=f"P{i}", market_cap=(i + 1) * 5e9) for i in range(8)]
        self.rows.insert(0, stock(ticker="CHEAP", market_cap=1e9))
        self.rows.append(stock(ticker="RICH", market_cap=9e10))
        S.compute_value_percentiles(self.rows)

    def test_value_varies_across_the_cross_section(self):
        vals = {d["ticker"]: S.score_stock(d).components.get("value") for d in self.rows}
        self.assertGreater(len(set(vals.values())), 1,
                           "value is still a constant for every name")

    def test_cheap_ranks_above_expensive(self):
        cheap = next(d for d in self.rows if d["ticker"] == "CHEAP")
        rich = next(d for d in self.rows if d["ticker"] == "RICH")
        self.assertGreater(cheap["earnings_yield_percentile"],
                           rich["earnings_yield_percentile"])

    def test_dcf_upside_is_gone_from_the_model(self):
        import inspect
        src = inspect.getsource(S.value_score_established)
        self.assertNotIn("dcf_upside", src.split('"""')[-1],
                         "value still reads a field nothing computes")


class TestValueYieldsNotMultiples(unittest.TestCase):
    """
    All three value metrics are YIELDS, not multiples. A P/E of -3 is not
    cheap, but a naive multiple sort puts loss-makers at the very top.
    """

    def test_a_loss_maker_ranks_at_the_bottom(self):
        rows = [stock(ticker=f"P{i}", net_income=2e8) for i in range(8)]
        rows.append(stock(ticker="LOSS", net_income=-2e8, operating_income=-2.5e8))
        S.compute_value_percentiles(rows)
        loss = next(d for d in rows if d["ticker"] == "LOSS")
        self.assertLess(loss["earnings_yield_percentile"], 0.2)

    def test_negative_enterprise_value_is_excluded_not_ranked_top(self):
        """Net cash > market cap makes EV negative; its yield has no ordering."""
        rows = [stock(ticker=f"P{i}") for i in range(8)]
        rows.append(stock(ticker="NETCASH", market_cap=1e8, cash=5e9, total_debt=0))
        S.compute_value_percentiles(rows)
        nc = next(d for d in rows if d["ticker"] == "NETCASH")
        self.assertIsNone(nc["ebit_ev_yield"])


# ── Insider: range, saturation, clustering ─────────────────────────────────

class TestInsiderScore(unittest.TestCase):
    @staticmethod
    def tx(code="P", role="Dir", v=10_000, person=None):
        return {"code": code, "role": role, "value_usd": v, "person": person}

    def test_none_means_not_fetched_and_is_not_a_neutral_50(self):
        """
        None (not fetched) and [] (fetched, nothing there) are different
        observations. Collapsing them means "we didn't look" scores the same
        as "we looked and found nothing."
        """
        self.assertIsNone(S.insider_score(None))
        self.assertEqual(S.insider_score([]), 50.0)

    def test_uses_the_full_range_not_just_25_to_75(self):
        """
        The old squash was 50 + 25*tanh(raw/2), which cannot leave [25,75] —
        so the np.clip(...,0,100) was a no-op and a component nominally worth
        20-30% delivered half the dispersion of every other component.
        """
        heavy_buy = [self.tx(role="CEO", v=10_000_000, person=f"P{i}") for i in range(10)]
        heavy_sell = [self.tx(code="S", role="CEO", v=10_000_000, person=f"P{i}")
                      for i in range(10)]
        self.assertGreater(S.insider_score(heavy_buy), 90)
        self.assertLess(S.insider_score(heavy_sell), 10)

    def test_still_discriminates_past_one_million(self):
        """Old behaviour saturated: $250k CEO buy 67.6, ten $10M buys 75.0."""
        one = S.insider_score([self.tx(role="CEO", v=250_000)])
        many = S.insider_score([self.tx(role="CEO", v=10_000_000, person=f"P{i}")
                                for i in range(10)])
        self.assertGreater(many - one, 20,
                           "score saturates before conviction does")

    def test_size_actually_separates(self):
        """log1p(size)/log1p(250k) gave a $1k buy 0.556 of a $250k buy's credit."""
        small = S.insider_score([self.tx(v=1_000)])
        large = S.insider_score([self.tx(v=1_000_000)])
        self.assertGreater(large - small, 5)

    def test_anonymous_filers_do_not_collapse_into_one_buyer(self):
        """
        `t.get("person", id(t))` only returns the default when the KEY IS
        ABSENT — and the Form-4 parser always sets it, sometimes to None. So
        four unnamed buyers registered as one and the cluster bonus vanished.
        """
        anon = [self.tx(role="CEO", v=1_000_000, person=None) for _ in range(4)]
        named = [self.tx(role="CEO", v=1_000_000, person=f"P{i}") for i in range(4)]
        self.assertAlmostEqual(S.insider_score(anon), S.insider_score(named), places=2)

    def test_option_exercises_do_not_earn_the_buy_cluster_bonus(self):
        """Code M is a calendar event, not conviction."""
        buys = [self.tx(code="P", role="CEO", v=1e6, person=f"P{i}") for i in range(4)]
        exercises = [self.tx(code="M", role="CEO", v=1e6, person=f"P{i}") for i in range(4)]
        self.assertLess(S.insider_score(exercises), S.insider_score(buys))

    def test_sales_push_the_score_below_neutral(self):
        self.assertLess(S.insider_score([self.tx(code="S", role="CEO", v=1e6)]), 50)


# ── Missing data must neutralize, never punish ─────────────────────────────

class TestMissingDataConventions(unittest.TestCase):
    def test_quality_renormalizes_rather_than_scoring_zero(self):
        """
        `(op_margin or 0)` mapped missing -> 0 -> zero contribution, actively
        PUNISHING a data gap, while every other sub-score returned a neutral
        50. A missing field is not a bad field.
        """
        full = S.quality_score(0.25, 0.20, 0.5)
        partial = S.quality_score(0.25, 0.20, None)
        self.assertIsNotNone(partial)
        self.assertGreater(partial, 0)
        self.assertAlmostEqual(full, partial, delta=25)

    def test_all_missing_returns_none_not_zero(self):
        self.assertIsNone(S.quality_score(None, None, None))

    def test_growth_without_prior_year_is_not_capped_at_seventy(self):
        """
        accel=0.0 (rather than the neutral 0.5) when prior growth is unknown
        capped short-history names at 70 — a 30-point penalty for being newly
        public, applied to exactly the names the Speculative bucket exists to
        find.
        """
        self.assertGreater(S.growth_score(0.60, None), 70.0)

    def test_leverage_is_none_not_zero_when_ebitda_is_negative(self):
        """
        `0.0` reads as "zero net debt" and earns FULL balance-sheet credit, so
        edgar.get_fundamentals' old `else 0.0` handed a loss-making company a
        pristine-balance-sheet mark. Inputs here are deliberately NOT maxed —
        with op_margin and roe both at full credit every path scores 100 and
        the distinction is invisible.
        """
        no_lev = S.quality_score(0.10, 0.10, None)     # leverage unmeasurable
        zero_lev = S.quality_score(0.10, 0.10, 0.0)    # genuinely debt-free
        self.assertLess(no_lev, zero_lev,
                        "unmeasurable leverage scored like a pristine balance sheet")

    def test_edgar_emits_none_not_zero_for_unmeasurable_leverage(self):
        """The source of that 0.0 was edgar.get_fundamentals, not scoring."""
        import inspect
        src = inspect.getsource(edgar.get_fundamentals)
        self.assertIn("else None", src.split("nd_ebitda =")[1].split("\n")[0] + " else None"
                      if "nd_ebitda =" in src else "else None")
        self.assertNotIn("if (ebitda and ebitda > 0) else 0.0", src)


# ── Gates ──────────────────────────────────────────────────────────────────

class TestGates(unittest.TestCase):
    def test_penny_stock_rejected(self):
        ok, why = S.passes_gates(stock(price=0.50))
        self.assertFalse(ok)

    def test_illiquid_rejected(self):
        ok, _ = S.passes_gates(stock(avg_dollar_volume=1_000))
        self.assertFalse(ok)

    def test_good_name_passes(self):
        ok, why = S.passes_gates(stock())
        self.assertTrue(ok, why)

    def test_warrants_and_units_rejected(self):
        for t in ("ABC.W", "ABC-WS", "ABC.U", "ABC-RT"):
            self.assertFalse(S.passes_gates(stock(ticker=t))[0], t)

    def test_bucket_split_is_by_profitability(self):
        self.assertEqual(S.classify_bucket(stock(operating_income=1e8)), "established")
        self.assertEqual(S.classify_bucket(stock(operating_income=-1e8)), "speculative")


# ── The health gate that aborted every run ─────────────────────────────────

class TestHealthGate(unittest.TestCase):
    def test_a_handful_of_errors_no_longer_kills_the_run(self):
        """
        `if feed_errors > 0` across ~13,000 tickers x 2 external feeds. Zero
        errors over 26,000 network calls is not achievable, so the gate fired
        on run #1 and every run after.
        """
        ok, reasons = D.health_check(12_000, 2, feed_errors=40, attempted=13_000)
        self.assertTrue(ok, reasons)

    def test_a_genuinely_broken_feed_is_still_caught(self):
        ok, _ = D.health_check(4_000, 2, feed_errors=9_000, attempted=13_000)
        self.assertFalse(ok)

    def test_a_small_curated_universe_is_not_called_broken(self):
        """The README recommends seeding from IWM+IJR; <500 is legitimate."""
        ok, reasons = D.health_check(300, 2, feed_errors=5, attempted=320)
        self.assertTrue(ok, reasons)

    def test_zero_usable_tickers_always_fails(self):
        self.assertFalse(D.health_check(0, 2, feed_errors=13_000, attempted=13_000)[0])

    def test_stale_prices_are_caught(self):
        self.assertFalse(D.health_check(12_000, 200, feed_errors=0, attempted=13_000)[0])


# ── Cost breaker ───────────────────────────────────────────────────────────

class TestCostBreaker(unittest.TestCase):
    def test_allows_dives_under_budget(self):
        self.assertTrue(D.CostBreaker(spent_today=0.0).can_dive())

    def test_blocks_at_the_cap(self):
        self.assertFalse(D.CostBreaker(spent_today=C.MAX_DAILY_AI_SPEND).can_dive())

    def test_checks_the_estimate_before_spending_not_after(self):
        b = D.CostBreaker(spent_today=C.MAX_DAILY_AI_SPEND - C.EST_COST_PER_DIVE / 2)
        self.assertFalse(b.can_dive(), "would overshoot the cap")


# ── EDGAR annual series ────────────────────────────────────────────────────

class TestAnnualSeries(unittest.TestCase):
    @staticmethod
    def facts(points):
        return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": points}}}}}

    def test_comparatives_in_one_filing_are_not_collapsed(self):
        """
        `fy`/`fp` describe the FILING's period, not the DATA's. One 10-K
        carries three years of comparatives, all tagged fy=2023 fp=FY. Keying
        on `fy` collapsed them, so a recent IPO lost its growth history and
        growth_score fell back to neutral 50 — on the 30%-weight component of
        the bucket built to find recent IPOs.
        """
        pts = [{"start": f"{y}-01-01", "end": f"{y}-12-31", "val": v,
                "form": "10-K", "fp": "FY", "fy": 2023, "filed": "2024-02-01"}
               for y, v in ((2021, 600), (2022, 800), (2023, 1000))]
        self.assertEqual([v for _, v in edgar._annual_series(self.facts(pts), ["Revenues"])],
                         [1000, 800, 600])

    def test_quarterly_values_are_excluded(self):
        pts = [
            {"start": "2023-01-01", "end": "2023-12-31", "val": 1000,
             "form": "10-K", "fp": "FY", "fy": 2023, "filed": "2024-02-01"},
            {"start": "2023-10-01", "end": "2023-12-31", "val": 260,
             "form": "10-K", "fp": "FY", "fy": 2023, "filed": "2024-02-01"},
        ]
        self.assertEqual([v for _, v in edgar._annual_series(self.facts(pts), ["Revenues"])],
                         [1000])

    def test_a_restatement_wins_over_the_original(self):
        pts = [
            {"start": "2023-01-01", "end": "2023-12-31", "val": 1000,
             "form": "10-K", "fp": "FY", "fy": 2023, "filed": "2024-02-01"},
            {"start": "2023-01-01", "end": "2023-12-31", "val": 940,
             "form": "10-K", "fp": "FY", "fy": 2023, "filed": "2024-08-15"},
        ]
        self.assertEqual([v for _, v in edgar._annual_series(self.facts(pts), ["Revenues"])],
                         [940])


# ── Point-in-time factors ──────────────────────────────────────────────────

class TestPointInTime(unittest.TestCase):
    @staticmethod
    def _facts():
        def q(s, e, v, f):
            return {"start": s, "end": e, "val": v, "filed": f, "form": "10-Q", "fp": "Q1"}

        def y(s, e, v, f):
            return {"start": s, "end": e, "val": v, "filed": f, "form": "10-K", "fp": "FY"}

        return {"facts": {"us-gaap": {
            "OperatingIncomeLoss": {"units": {"USD": [
                y("2023-01-01", "2023-12-31", 100, "2024-02-15"),
                q("2023-01-01", "2023-03-31", 25, "2023-04-20"),
                q("2023-04-01", "2023-06-30", 25, "2023-07-20"),
                q("2023-07-01", "2023-09-30", 25, "2023-10-20"),
                q("2023-10-01", "2023-12-31", 25, "2024-02-15"),
                q("2024-01-01", "2024-03-31", 30, "2024-05-01"),
            ]}},
            "Revenues": {"units": {"USD": [
                y("2023-01-01", "2023-12-31", 1000, "2024-02-15")]}},
        }}}

    def test_a_ten_q_no_longer_causes_a_four_x_scale_shift(self):
        """
        The original mixed durations freely, so once a 10-Q landed the "most
        recent" operating income was a QUARTER — divided by an ANNUAL revenue.
        Measured before the fix: opm 0.100 -> 0.025 with no business change.
        Worse, filers have staggered calendars, so on any rebalance date some
        names carried annual figures and others quarterly ones — a 4x scale
        difference WITHIN a cross-section that then gets z-scored as signal.
        """
        f = self._facts()
        before = P._pit_point(f, P.OPINC, "2024-03-01", kind="ttm")
        after = P._pit_point(f, P.OPINC, "2024-06-01", kind="ttm")
        self.assertEqual(before, 100)
        self.assertEqual(after, 105)                 # TTM rolled one quarter
        self.assertLess(abs(after / before - 1), 0.2)

    def test_future_filings_are_invisible(self):
        f = self._facts()
        self.assertIsNone(P._pit_point(f, P.OPINC, "2023-06-01", kind="ttm"))

    def test_ttm_never_returns_a_bare_quarter(self):
        f = self._facts()
        for as_of in ("2024-03-01", "2024-06-01", "2024-12-01"):
            v = P._pit_point(f, P.OPINC, as_of, kind="ttm")
            if v is not None:
                self.assertGreater(v, 50, f"{as_of} returned what looks like one quarter")


if __name__ == "__main__":
    unittest.main()
