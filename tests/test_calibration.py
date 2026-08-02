"""
Tests for the fair-value calibration harness (valuation/engine/calibration.py).

Two different jobs here, and it is worth being clear about which is which:

  * Tests of the POINT-IN-TIME construction — TTM vs quarterly flows, currency,
    look-ahead, the share-count cancellation. These are correctness tests: if any of
    them fails, the measured IC is measuring something other than the fair value.
  * Tests of the MEASUREMENT ITSELF — plant a known signal into a synthetic panel and
    confirm the IC/decile machinery finds it, then plant noise and confirm it doesn't.
    Without these, a null result is indistinguishable from a broken yardstick, and a
    null result is the single most likely outcome of this whole exercise.

Run with:
    python -m pytest tests/
    python tests/test_calibration.py     # no pytest required
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from valuation.config import CONFIG
from valuation.engine import calibration as C
from valuation.engine.pipeline import value_from_company
from tests.fixtures import build_nike, build_growth


# --------------------------------------------------------------------------- #
# Synthetic point-in-time filings
# --------------------------------------------------------------------------- #

def _quarters(n=12, start="2018-03-31", revenue=1e9, ebit=2e8, months=3, **over):
    """`n` consecutive quarterly ARQ-shaped rows, in raw reporting-currency dollars."""
    rows = []
    d = pd.Timestamp(start)
    for i in range(n):
        r = {"datekey": str((d + pd.DateOffset(months=months * i)).date()),
             "dimension": "ARQ", "revenue": revenue, "ebit": ebit, "ebitda": ebit * 1.4,
             "netinc": ebit * 0.75, "gp": revenue * 0.40, "fcf": ebit * 0.8,
             "ncfo": ebit * 1.2, "intexp": ebit * 0.05, "equity": 5e9, "debt": 2e9,
             "cashneq": 1e9, "invcap": 6e9}
        r.update(over)
        rows.append(r)
    return rows


def _cd(rows, as_of, price=100.0, market_cap=2e10, **kw):
    return C.pit_company("TEST", C._prep_fundamentals(rows), as_of, price, market_cap, **kw)


# --------------------------------------------------------------------------- #
# Point-in-time construction
# --------------------------------------------------------------------------- #

def test_flows_are_trailing_twelve_months_not_one_quarter():
    """The export is ARQ — one QUARTER per row. Feeding `revenue` straight in values the
    company off a quarter of its sales and makes every fair value ~4x too low, silently
    and uniformly. This is the single most dangerous bug available in this module."""
    cd = _cd(_quarters(revenue=1e9, ebit=2e8), "2021-06-30")
    assert abs(cd.revenue - 4000.0) < 1e-6, cd.revenue        # 4 x $1bn, in $mm
    assert abs(cd.ebit - 800.0) < 1e-6, cd.ebit
    assert abs(cd.ebit_margin - 0.20) < 1e-9


def test_stocks_are_period_end_not_summed():
    """Balance-sheet items must NOT be summed over four quarters — that would quadruple
    equity and debt and make every leverage-sensitive number nonsense."""
    cd = _cd(_quarters(), "2021-06-30")
    assert abs(cd.total_equity - 5000.0) < 1e-6, cd.total_equity
    assert abs(cd.total_debt - 2000.0) < 1e-6, cd.total_debt
    assert abs(cd.net_debt - 1000.0) < 1e-6, cd.net_debt


def test_a_missing_quarter_is_rejected_not_silently_summed():
    """Four rows spanning three years is not a TTM. Without the span guard, a company
    with a reporting gap gets several years of flow summed into one 'year'."""
    rows = _quarters(n=4, months=12)          # annual spacing -> a 3-year span
    assert _cd(rows, "2021-06-30") is None


def test_ttm_is_tolerant_per_key():
    """One missing extra must cost that extra, not the whole company. `_ttm` in the
    factor panel is all-or-nothing across every requested key, which is right there and
    wrong here: a blank `intexp` (only used for a cost-of-debt refinement) would
    otherwise discard the name entirely."""
    rows = _quarters()
    for r in rows:
        r["intexp"] = None
    cd = _cd(rows, "2021-06-30")
    assert cd is not None, "a missing extra must not discard the company"
    assert cd.interest_expense is None
    assert abs(cd.revenue - 4000.0) < 1e-6, "the other flows must survive intact"


def test_da_and_capex_are_derived_from_columns_that_exist():
    """Neither `depamor` nor `capex` is in the loader's column allowlist, and this module
    must not touch the loader. Both fall out of columns that are there."""
    cd = _cd(_quarters(revenue=1e9, ebit=2e8), "2021-06-30")
    assert abs(cd.da - (4 * 2e8 * 1.4 - 4 * 2e8) / 1e6) < 1e-6, cd.da     # EBITDA - EBIT
    assert abs(cd.capex - (4 * 2e8 * 1.2 - 4 * 2e8 * 0.8) / 1e6) < 1e-6   # NCFO - FCF
    assert cd.capex >= 0


def test_foreign_line_items_are_converted_to_usd():
    """P7: `marketcap` is USD, the line items are in the reporting currency. Mixing them
    is what computed SK Telecom's book/price as 892 against a true 0.589. `fxusd` is
    LOCAL UNITS PER USD, so it DIVIDES — using it as a multiplier squares the error."""
    local = _cd(_quarters(revenue=1e9), "2021-06-30")
    foreign = _cd(_quarters(revenue=1e9, fxusd=1000.0), "2021-06-30")
    assert abs(foreign.revenue - local.revenue / 1000.0) < 1e-9, foreign.revenue
    # The direction matters as much as the magnitude: a won reporter must come out
    # SMALLER in USD, never 1000x larger.
    assert foreign.revenue < local.revenue


def test_point_in_time_never_reads_a_future_filing():
    rows = _quarters(n=12, revenue=1e9)
    for r in rows:
        if r["datekey"] > "2020-01-01":
            r["revenue"] = 9e9                     # a huge future jump
    cd = _cd(rows, "2019-12-31")
    assert abs(cd.revenue - 4000.0) < 1e-6, "a filing after as_of leaked into the valuation"


def test_revenue_history_is_annual_not_quarterly():
    """CompanyData.revenue_growth() reads the history as a fiscal-year series. Handing it
    consecutive QUARTERS would report quarter-on-quarter growth as a yearly rate."""
    rows = []
    for yr, rev in ((2018, 1e9), (2019, 2e9), (2020, 4e9)):
        rows += _quarters(n=4, start=f"{yr}-03-31", revenue=rev)
    cd = _cd(rows, "2020-12-31")
    assert abs(cd.rev_growth_ttm - 1.0) < 0.02, cd.rev_growth_ttm      # revenue doubled


# --------------------------------------------------------------------------- #
# The valuation path
# --------------------------------------------------------------------------- #

def test_lean_path_matches_the_full_pipeline():
    """calibration skips Monte Carlo, sensitivity and scoring on the grounds that none of
    them can change `blend.value`. If that ever stops being true — someone wires the MC
    percentile into the headline — this fails instead of silently measuring a different
    number than the website publishes."""
    for build in (build_nike, build_growth):
        cd = build()
        lean = C.lean_fair_value(cd, CONFIG)
        full = value_from_company(cd, CONFIG, mc_trials=1)
        assert lean["fair_value"] is not None and full.base_fair_value is not None
        assert abs(lean["fair_value"] - full.base_fair_value) < 1e-9, (
            cd.ticker, lean["fair_value"], full.base_fair_value)
        assert lean["method"] == full.fair_value_blend.method
        assert lean["maturity"] == full.fair_value_blend.maturity
        assert lean["growth_led"] == full.fair_value_blend.growth_led


def test_gap_is_invariant_to_share_count():
    """The share count is derived as market_cap / price, so it cancels out of the gap:
    fair_value/price == fair_equity/market_cap. That makes the whole measurement immune
    to ADR ratios, share classes and split adjustments — which are exactly the fields
    that are unreliable across an 18-year point-in-time export."""
    rows = _quarters()
    a = C.lean_fair_value(_cd(rows, "2021-06-30", price=100.0, market_cap=2e10))
    # Same company, quoted as a 10:1 ADR: price and share count both change, cap does not.
    b = C.lean_fair_value(_cd(rows, "2021-06-30", price=1000.0, market_cap=2e10))
    assert a["gap"] is not None and b["gap"] is not None
    assert abs(a["gap"] - b["gap"]) < 1e-9, (a["gap"], b["gap"])


def test_a_bank_is_valued_on_book_not_on_a_dcf():
    """Spot-check across the archetype spectrum (task item 5). An unlevered FCFF DCF is
    meaningless for a bank, so the blend must fall through to justified P/B-ROE."""
    cd = _cd(_quarters(), "2021-06-30")
    cd.sector = "Financial Services"
    v = C.lean_fair_value(cd)
    assert v["regime"] == "financial"
    assert "P/B" in v["method"], v["method"]
    assert v["growth_ps"] is None, "the revenue lens must not run on a bank"


def test_a_preprofit_grower_is_growth_led_and_a_mature_name_is_not():
    """The other two points on the spectrum. Same construction, different economics."""
    burner = _cd(_quarters(revenue=1e8, ebit=-8e7, start="2018-03-31"), "2021-06-30",
                 price=60.0, market_cap=2e10)
    for i, r in enumerate(_quarters()):     # give it real growth in its history
        pass
    assert burner is not None
    v = C.lean_fair_value(burner)
    assert v["maturity"] < 0.5, v["maturity"]
    mature = C.lean_fair_value(_cd(_quarters(revenue=5e9, ebit=1.2e9), "2021-06-30",
                                   price=100.0, market_cap=2e11))
    assert mature["maturity"] > 0.5, mature["maturity"]
    assert mature["maturity"] > v["maturity"]


# --------------------------------------------------------------------------- #
# The measurement itself
# --------------------------------------------------------------------------- #

def _panel(n_dates=40, n_names=60, beta=0.0, seed=7, maturity=None):
    """A synthetic panel whose forward return is `beta * gap + noise`.

    beta = 0 gives a genuinely null panel — the case that MUST measure as null.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        for k in range(n_names):
            gap = float(rng.normal(0, 0.5))
            rows.append({
                "date": f"20{10 + d // 4:02d}-{1 + 3 * (d % 4):02d}-01",
                "ticker": f"T{k}", "gap": gap,
                "upside": float(np.exp(gap) - 1.0),          # a monotone transform of gap
                "fwd_ret": beta * gap + float(rng.normal(0, 0.10)),
                "market_cap": float(rng.uniform(1e9, 1e11)),
                "maturity": (float(rng.uniform(0, 1)) if maturity is None else maturity),
                "regime": "mature", "sector": "Technology",
                "is_adr": bool(k % 20 == 0), "valuable": True, "growth_led": False,
            })
    return pd.DataFrame(rows)


def test_the_yardstick_finds_a_planted_signal():
    """If this fails, a null result from the real run means nothing."""
    ic = C.gap_ic(_panel(beta=0.30))
    assert ic["median_ic"] > 0.5, ic
    assert ic["ic_tstat"] > 5, ic
    q = C.gap_quantiles(_panel(beta=0.30))
    assert q["long_short_ann"] > 0 and q["long_short_tstat"] > 3, q


def test_the_yardstick_reports_a_null_panel_as_null():
    """The other half of the same guarantee: no signal must not produce one."""
    ic = C.gap_ic(_panel(beta=0.0))
    assert abs(ic["median_ic"]) < 0.05, ic
    assert abs(ic["ic_tstat"]) < 2.5, ic


def test_monotonicity_follows_the_project_sign_convention():
    """Buckets are ordered BEST-FIRST, so -1.0 is perfectly ordered and +1.0 is backwards
    — the same convention as quantile_backtest, whose sign this project had been reading
    inverted for months. Pinned here so the two can't drift apart."""
    q = C.gap_quantiles(_panel(beta=0.60))
    assert q["monotonicity"] < -0.8, q["monotonicity"]
    backwards = _panel(beta=-0.60)
    assert C.gap_quantiles(backwards)["monotonicity"] > 0.8


def test_rank_ic_is_invariant_to_how_the_gap_is_expressed():
    """log(fv/price), fv/price - 1 and fv/price are monotone transforms of one another,
    so a RANK IC cannot distinguish them. Worth pinning: it is why this module can report
    one number and the UI can show another without them disagreeing."""
    p = _panel(beta=0.25)
    a, b = C.gap_ic(p, col="gap"), C.gap_ic(p, col="upside")
    assert abs(a["median_ic"] - b["median_ic"]) < 1e-9, (a["median_ic"], b["median_ic"])


def test_nonoverlapping_check_partitions_the_dates():
    """A 252-day forward return sampled every 63 days overlaps its next three
    observations, and the resulting t-stat is inflated by roughly sqrt(4). Taking every
    4th date restores independence; doing it at all four offsets shows whether the answer
    depends on which dates happen to get picked.

    This is load-bearing for the conclusion: the 252-day top-decile alpha t-stat drops
    from +3.71 to +1.78..+1.93 when measured this way."""
    p = _panel(n_dates=40, beta=0.25)
    ov = C.nonoverlapping_check(p, horizon=252, rebalance_days=63)
    assert ov["stride"] == 4, ov["stride"]
    assert len(ov["offsets"]) == 4
    # The four subsamples must together cover every date exactly once.
    total = sum(r["n_dates"] for r in ov["offsets"].values())
    assert total == p["date"].nunique(), (total, p["date"].nunique())
    assert ov["ic_tstat_range"][0] <= ov["ic_tstat_range"][1]
    # An already-independent panel must not be resampled at all.
    assert C.nonoverlapping_check(p, horizon=63, rebalance_days=63)["stride"] == 1


def test_coverage_report_flags_an_empty_column():
    """The COVERAGE RULE, enforced. Five wired factors in this project were blank in 100%
    of rows for its entire history and nothing surfaced it."""
    p = _panel()
    p["growth_ps"] = np.nan
    cov = C.coverage_report(p)
    assert "growth_ps" in cov.get("below_floor", []), cov


def test_sanity_flags_foreign_over_representation():
    """The P7 signature: a currency bug fills every column (so coverage is clean) and
    quietly sweeps foreign reporters to the top of the value ranking."""
    p = _panel(beta=0.0, seed=3)
    p.loc[p["is_adr"], "gap"] = 10.0            # plant ADRs at the top of the ranking
    s = C.sanity_check(p, warn=False)
    assert s["adr_over_representation"] > 2.0, s
    assert any("P7" in f or "over-represented" in f for f in s["flags"]), s["flags"]
    clean = C.sanity_check(_panel(beta=0.0, seed=3), warn=False)
    assert clean["adr_over_representation"] < 2.0, clean


def test_maturity_tiers_cover_the_whole_panel():
    """A name must land in exactly one tier — a gap in the bounds would silently drop
    rows from the tier comparison and make the tiers non-comparable."""
    lo = [t[1] for t in C.MATURITY_TIERS]
    hi = [t[2] for t in C.MATURITY_TIERS]
    assert lo[0] <= 0.0 and hi[-1] > 1.0
    for i in range(len(C.MATURITY_TIERS) - 1):
        assert hi[i] == lo[i + 1], C.MATURITY_TIERS
    res = C.by_maturity(_panel(beta=0.0), n_q=5)
    assert sum(r["rows"] for k, r in res.items() if k != "growth_led") == len(_panel(beta=0.0))


def test_realized_growth_needs_a_filing_far_enough_out():
    """Otherwise a company whose history stops early has its 1-year growth reported as if
    it were 3-year, which would flatter every 'the implied growth never showed up' claim."""
    prep = C._prep_fundamentals(_quarters(n=20, start="2015-03-31"))
    assert C._realized_growth(prep, "2016-06-30", years=3) is not None
    assert C._realized_growth(prep, "2019-06-30", years=3) is None    # runs off the end


def test_realized_growth_measures_the_actual_rate():
    rows = []
    for i, rev in enumerate((1e9, 2e9, 4e9, 8e9, 16e9, 32e9)):   # doubling every year
        rows += _quarters(n=4, start=f"{2015 + i}-03-31", revenue=rev)
    g = C._realized_growth(C._prep_fundamentals(rows), "2016-12-31", years=3)
    assert g is not None and abs(g - 1.0) < 0.15, g              # ~100%/yr


def test_ev_ebitda_bridges_enterprise_value_to_equity():
    """Task item 4. An EV multiple is not an equity multiple: the implied enterprise
    value has to have net debt taken OUT of it before it becomes a per-share number.
    Checked on the deep path (comps.py), where a name with no P/E and no revenue
    multiple has nothing else to be valued on."""
    from valuation.data.models import CompanyData
    from valuation.engine.comps import compute_comps

    def one(net_debt):
        cd = CompanyData(ticker="X", sector="Industrials", price=10.0,
                         shares_diluted=100.0, market_cap=1000.0, revenue=500.0,
                         ebit=80.0, da=20.0,
                         total_debt=max(net_debt, 0.0) + 50.0,
                         cash_sti=50.0 - min(net_debt, 0.0))
        return compute_comps(cd)

    cash, debt = one(-400.0), one(400.0)
    assert "ev_ebitda" in cash.implied, cash.implied
    # Industrials benchmark 14x EBITDA of 100 = 1,400 EV; equity = EV - net debt.
    assert abs(cash.implied["ev_ebitda"] - (14 * 100.0 + 400.0) / 100.0) < 1e-6
    assert abs(debt.implied["ev_ebitda"] - (14 * 100.0 - 400.0) / 100.0) < 1e-6
    assert cash.implied["ev_ebitda"] > debt.implied["ev_ebitda"], (
        "net cash must be worth MORE per share than the same business carrying debt")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
