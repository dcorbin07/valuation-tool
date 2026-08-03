"""
EV multiples in the value theme: the wiring, not the verdict. Run:
    python tests/test_ev_multiples.py

Background. The value theme is bucket-split. Profitable ("established") names are judged on
earnings-based yields; loss-makers ("speculative") on sales multiples, because an earnings
yield is meaningless when earnings are negative. The consequence nobody had noticed is that
`neg_ev_sales` — the SECOND-strongest value input on the full panel (median IC +0.0214,
IC t +2.11) — has never scored a single profitable name, and `ev_ebitda` was not computed by
the panel at all.

`value_ev_multiples` extends the ESTABLISHED branch with both EV multiples so that A/B can be
measured. These tests pin the WIRING, in the spirit of the coverage rule: a wired thing that
silently does nothing is this project's most repeated bug (the five empty factors, the dropped
`assets` column, the inert sector-neutral toggle). They deliberately do NOT pin the verdict —
that is a research finding recorded in HANDOFF_growth_evsales.md and may change.

The one substantive correctness claim here is the SIGN GUARD. EV/EBITDA is only meaningful on
positive EBITDA: a loss-maker's multiple is negative, and negating it (higher = cheaper) would
rank the deepest losses as the greatest bargains. That must hold at BOTH the panel construction
and the factor-engine layer, because FMP hands back its own unguarded value.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from valuation.edge.fundamental_panel import _sf1_to_metrics
from valuation.screener import settings as S
from valuation.screener.factors import build_frame


# --------------------------------------------------------------------------- #
#  fixtures
# --------------------------------------------------------------------------- #
def _sf1(**over):
    """A minimal SF1 (ARQ) row. USD reporter unless `fxusd` is overridden."""
    row = {"ticker": "T", "datekey": "2015-05-01", "revenue": 1000.0, "netinc": 100.0,
           "ebit": 150.0, "ebitda": 200.0, "gp": 400.0, "fcf": 90.0,
           "equity": 800.0, "debt": 300.0, "cashneq": 100.0, "ev": 2400.0,
           "intexp": 10.0, "invcap": 1100.0, "taxexp": 40.0, "ebt": 140.0,
           "equityusd": None, "revenueusd": None, "ebitusd": None,
           "netinccmnusd": None, "fxusd": 1.0}
    row.update(over)
    return row


def _metrics(n=40, established=True, ev_ebitda=None, ev_sales=None):
    """A cross-section wide enough to z-score, with a spread on every value input so that
    changing which inputs feed the composite necessarily changes the composite."""
    out = []
    for i in range(n):
        m = {"ticker": f"T{i}", "price": 10.0, "market_cap": 1e9,
             "revenue": 5e8, "gross_profit": 2e8, "total_equity": 3e8, "total_debt": 1e8,
             "fcf": 4e7, "ev": 1.1e9,
             # sign of profit is what picks the bucket
             "operating_income": (6e7 if established else -6e7),
             "net_income": (5e7 if established else -5e7),
             "earnings_yield": 0.02 + i * 0.001,
             "fcf_yield": 0.01 + i * 0.001,
             "ebit_ev": 0.03 + i * 0.001,
             "book_to_price": 0.10 + i * 0.01,
             "ev_sales": (1.0 + i * 0.2) if ev_sales is None else ev_sales,
             "ps": 1.0 + i * 0.15,
             "ev_ebitda": (4.0 + i * 0.5) if ev_ebitda is None else ev_ebitda}
        out.append(m)
    return out


# --------------------------------------------------------------------------- #
#  panel construction
# --------------------------------------------------------------------------- #
def test_panel_computes_ev_ebitda():
    m = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=1200.0)
    assert m["ev_ebitda"] is not None, "ev_ebitda must be populated (the coverage-rule bug class)"
    assert abs(m["ev_ebitda"] - 2400.0 / 200.0) < 1e-9, m["ev_ebitda"]


def test_a_loss_makers_ev_ebitda_is_dropped_not_negative():
    """The whole point of the guard: a negative multiple negated becomes a huge positive,
    i.e. the deepest loss-maker would look like the cheapest stock in the market."""
    for bad in (-200.0, 0.0):
        m = _sf1_to_metrics("T", _sf1(ebitda=bad), price=10.0, market_cap=1200.0)
        assert m["ev_ebitda"] is None, f"EBITDA={bad} must yield no multiple, got {m['ev_ebitda']}"


def test_ev_ebitda_is_converted_to_usd_for_a_foreign_reporter():
    """P7, exactly: `ev` is USD but `ebitda` is in the REPORTING currency. Dividing one by
    the other hands a foreign reporter a fake multiple — SK Telecom's book_to_price came out
    at 892 against a true 0.589 from precisely this. fxusd is LOCAL PER USD, so it divides."""
    fx = 1514.2                                  # won per USD
    local = _sf1(ebitda=200.0 * fx, fxusd=fx)    # same real company, reporting in won
    usd = _sf1()
    m_local = _sf1_to_metrics("T", local, price=10.0, market_cap=1200.0)
    m_usd = _sf1_to_metrics("T", usd, price=10.0, market_cap=1200.0)
    assert abs(m_local["ev_ebitda"] - m_usd["ev_ebitda"]) < 1e-6, (
        f"foreign reporter got {m_local['ev_ebitda']} vs {m_usd['ev_ebitda']} — currency bug")


def test_ev_ebitda_is_exempt_from_the_range_check_like_the_other_multiples():
    """Its tail is driven by barely-profitable denominators, not by a sign error (the sign
    error is already impossible), so a range band would only produce false positives."""
    from valuation.edge.fundamental_panel import SANE_RANGES, SANE_RANGE_EXEMPT
    assert "ev_ebitda" in SANE_RANGE_EXEMPT
    assert "ev_ebitda" not in SANE_RANGES


# --------------------------------------------------------------------------- #
#  factor engine
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
#  point-in-time EV  (a latent defect found while wiring the above)
# --------------------------------------------------------------------------- #
def test_ev_is_the_filings_own_by_default():
    """Baseline behaviour, pinned so the A/B has a fixed reference point."""
    m = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=3000.0, ev_point_in_time=False)
    assert abs(m["ev_sales"] - 2400.0 / 1000.0) < 1e-9, m["ev_sales"]


def test_point_in_time_ev_uses_the_rebalance_market_cap_plus_filing_net_debt():
    """Sharadar's `ev` is `marketcap + debt - cashneq` with the FILING's market cap, so the
    EV ratios price cheapness ~111 days stale while the market-cap ratios do not."""
    m = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=3000.0, ev_point_in_time=True)
    want = 3000.0 + 300.0 - 100.0                 # PIT cap + net debt
    assert abs(m["ev_sales"] - want / 1000.0) < 1e-9, m["ev_sales"]
    assert abs(m["ev_ebitda"] - want / 200.0) < 1e-9
    assert abs(m["ebit_ev"] - 150.0 / want) < 1e-9


def test_point_in_time_ev_converts_net_debt_before_adding_it_to_a_usd_market_cap():
    """P7 wearing a different hat: `debt`/`cashneq` are REPORTING currency, `marketcap` is
    USD. Adding won to dollars would dwarf the market cap by ~1,500x."""
    fx = 1514.2
    loc = _sf1(fxusd=fx)
    for k in ("revenue", "netinc", "ebit", "ebitda", "gp", "fcf", "equity", "debt",
              "cashneq", "intexp", "invcap", "taxexp", "ebt"):
        loc[k] = loc[k] * fx                       # a foreign filer reports EVERY line in won
    a = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=3000.0, ev_point_in_time=True)
    b = _sf1_to_metrics("T", loc, price=10.0, market_cap=3000.0, ev_point_in_time=True)
    for k in ("ev_sales", "ev_ebitda", "ebit_ev"):
        assert abs(a[k] - b[k]) < 1e-6, f"{k}: usd {a[k]} vs foreign {b[k]} — currency bug"


def test_point_in_time_ev_falls_back_when_a_piece_is_missing():
    """No net-debt line items means no rebuild — keep the filing's `ev` rather than
    inventing an EV equal to the market cap."""
    m = _sf1_to_metrics("T", _sf1(debt=None, cashneq=None), price=10.0,
                        market_cap=3000.0, ev_point_in_time=True)
    assert abs(m["ev_sales"] - 2400.0 / 1000.0) < 1e-9, "should fall back to the filing ev"


def test_point_in_time_ev_is_off_by_default():
    from valuation.config import CONFIG
    assert CONFIG.ev_point_in_time is False, (
        "ev_point_in_time defaults ON — it silently changes ebit_ev, an adopted factor")


def test_the_number_is_registered_to_the_value_theme():
    """Unregistered = never z-scored, never measured, never coverage-checked."""
    assert S.NUMBER_THEME.get("neg_ev_ebitda") == "value"
    assert "neg_ev_ebitda" in S.NUMBERS_ALL


def test_a_negative_provider_multiple_is_dropped_by_the_factor_engine_too():
    """FMP returns enterpriseValueMultipleTTM unguarded, so the panel-side guard is not
    enough — every provider passes through build_frame, so the guard lives there as well."""
    ms = _metrics()
    ms[0]["ev_ebitda"] = -8.0                    # a loss-maker the provider did not filter
    ms[1]["ev_ebitda"] = 6.0
    fr = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)
    assert np.isnan(fr.loc["T0", "neg_ev_ebitda"]), "negative EV/EBITDA must read as missing"
    assert fr.loc["T1", "neg_ev_ebitda"] == -6.0


def test_the_flag_is_off_by_default():
    """Default OFF is what makes the A/B a real comparison against shipped behaviour."""
    from valuation.config import CONFIG
    assert CONFIG.value_ev_multiples is False, (
        "value_ev_multiples defaults ON — the baseline arm would no longer be the live config")


def test_the_flag_changes_established_names():
    ms = _metrics(established=True)
    off = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=False)
    on = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)
    assert (off["bucket"] == "established").all()
    assert not np.allclose(off["value"].values, on["value"].values), (
        "flag did not move the value theme for profitable names — it is inert")


def test_the_flag_leaves_speculative_names_untouched():
    """The speculative branch already used EV/Sales; the flag must not double-count it or
    otherwise disturb the side of the split that was never the question."""
    ms = _metrics(established=False)
    off = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=False)
    on = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)
    assert (off["bucket"] == "speculative").all()
    assert np.allclose(off["value"].values, on["value"].values, equal_nan=True), (
        "flag altered speculative names — it must only extend the established branch")


def test_flag_off_reproduces_the_previous_definition_exactly():
    """Guards against silent drift in the baseline: with the flag off, `value` for a
    profitable name is still exactly the mean of the four original z-scores."""
    ms = _metrics(established=True)
    fr = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=False)
    want = fr[["z_earnings_yield", "z_fcf_yield", "z_ebit_ev", "z_book_to_price"]].mean(axis=1)
    assert np.allclose(fr["value"].values, want.values, equal_nan=True)


def test_flag_on_is_the_mean_of_six_inputs():
    ms = _metrics(established=True)
    fr = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)
    want = fr[["z_earnings_yield", "z_fcf_yield", "z_ebit_ev", "z_book_to_price",
               "z_neg_ev_sales", "z_neg_ev_ebitda"]].mean(axis=1)
    assert np.allclose(fr["value"].values, want.values, equal_nan=True)


def test_the_flag_does_not_disturb_any_other_theme():
    """It must be a pure value-theme change: if it moved quality or momentum, the A/B would
    be measuring something other than the thing under test."""
    ms = _metrics(established=True)
    off = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=False)
    on = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)
    for theme in S.FACTORS_ALL:
        if theme == "value":
            continue
        a, b = off[theme].values, on[theme].values
        assert np.allclose(a, b, equal_nan=True), f"{theme} moved when only value should have"


def test_the_z_scores_themselves_are_unaffected_by_the_flag():
    """Standardization happens BEFORE the composite, so every z-column must be identical
    across arms. This is what makes an A/B computable from one stored panel."""
    ms = _metrics(established=True)
    off = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=False)
    on = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)
    for num in S.NUMBERS_ALL:
        zc = "z_" + num
        if zc in off.columns and zc in on.columns:
            assert np.allclose(off[zc].values, on[zc].values, equal_nan=True), f"{zc} moved"


def test_value_is_recomputable_from_the_stored_z_columns():
    """Pins the shortcut the A/B analysis relies on: because the flag only changes which
    z-columns are averaged, the WITH arm can be reconstructed exactly from a panel built
    WITHOUT it — no second 12-minute panel build, and no chance of the two arms differing
    by anything other than the composite."""
    ms = _metrics(established=True) + _metrics(n=20, established=False)
    for i, m in enumerate(ms):
        m["ticker"] = f"N{i}"                    # unique index across the two blocks
    off = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=False)
    on = build_frame(ms, sector_neutral=False, residual_momentum=False, value_ev_multiples=True)

    est = off["bucket"].eq("established")
    rebuilt = off["value"].copy()
    rebuilt[est] = off.loc[est, ["z_earnings_yield", "z_fcf_yield", "z_ebit_ev",
                                 "z_book_to_price", "z_neg_ev_sales",
                                 "z_neg_ev_ebitda"]].mean(axis=1)
    assert np.allclose(rebuilt.values, on["value"].values, equal_nan=True), (
        "reconstruction from stored z-columns does not reproduce the WITH arm")


def test_panel_rows_record_the_bucket():
    """`value` means different things either side of the split, so a value diagnostic that
    ignores the bucket is averaging two different factors together."""
    import inspect
    from valuation.edge import fundamental_panel as F
    src = inspect.getsource(F.build_fundamental_panel)
    assert 'row["bucket"]' in src, "panel must persist the bucket for per-branch diagnostics"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} EV-multiple tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
