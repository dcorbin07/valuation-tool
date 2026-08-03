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


# Every line item a foreign filer reports is in its own currency, so a fixture that converts
# only the field under test is not a foreign filer — it is a chimera, and it will "fail" any
# check that touches a second field (net debt, in the EV case) for a reason that is the
# fixture's fault rather than the code's.
_LOCAL_FIELDS = ("revenue", "netinc", "ebit", "ebitda", "gp", "fcf", "equity", "debt",
                 "cashneq", "intexp", "invcap", "taxexp", "ebt")


def _sf1_foreign(fx, **over):
    """The same real company as `_sf1()`, reporting in a currency worth 1/fx of a dollar."""
    row = _sf1(**over)
    for k in _LOCAL_FIELDS:
        if row.get(k) is not None:
            row[k] = row[k] * fx
    row["fxusd"] = fx
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
    # EV is rebuilt at the rebalance date by default now: 1200 cap + (300 - 100) net debt.
    assert abs(m["ev_ebitda"] - 1400.0 / 200.0) < 1e-9, m["ev_ebitda"]


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
    m_local = _sf1_to_metrics("T", _sf1_foreign(fx), price=10.0, market_cap=1200.0)
    m_usd = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=1200.0)
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
def test_ev_is_the_filings_own_when_the_fix_is_disabled():
    """The pre-fix behaviour, pinned so the A/B keeps a fixed reference point and so the
    revert path (EDGE_EV_POINT_IN_TIME=false) stays honest rather than becoming a no-op."""
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
    a = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=3000.0, ev_point_in_time=True)
    b = _sf1_to_metrics("T", _sf1_foreign(fx), price=10.0, market_cap=3000.0,
                        ev_point_in_time=True)
    for k in ("ev_sales", "ev_ebitda", "ebit_ev"):
        assert abs(a[k] - b[k]) < 1e-6, f"{k}: usd {a[k]} vs foreign {b[k]} — currency bug"


def test_point_in_time_ev_falls_back_when_a_piece_is_missing():
    """No net-debt line items AND no filing market cap means no rebuild — keep the filing's
    `ev` rather than inventing an EV equal to the market cap."""
    m = _sf1_to_metrics("T", _sf1(debt=None, cashneq=None), price=10.0,
                        market_cap=3000.0, ev_point_in_time=True)
    assert abs(m["ev_sales"] - 2400.0 / 1000.0) < 1e-9, "should fall back to the filing ev"
    assert m["_ev_src"] == "stale_no_netdebt"


def test_point_in_time_ev_is_on_by_default():
    from valuation.config import CONFIG
    assert CONFIG.ev_point_in_time is True, (
        "ev_point_in_time defaults OFF — the EV ratios are being priced ~111 days stale "
        "while earnings_yield / fcf_yield / book_to_price are priced at the rebalance date")


# --------------------------------------------------------------------------- #
#  THE regression this can silently suffer: EV drifting loose from the rebalance
#  date again. A single-row test cannot see it — the value only looks wrong once
#  you ask whether it MOVED when the price did.
# --------------------------------------------------------------------------- #
def test_ev_tracks_market_cap_across_rebalances_from_one_filing():
    """The defect, stated as a property: ONE filing scored at several rebalance dates must
    produce an EV that moves dollar-for-dollar with the point-in-time market cap.

    This is the AAPL case from the prompt in miniature. Under the stale behaviour all three
    rebalances reuse the filing's single `ev` and this comes out constant, which is the whole
    bug: a name whose price doubled between filings kept its old cheapness.
    """
    sf1 = _sf1()                                   # net debt = 300 - 100 = 200, filing ev 2400
    caps = [2000.0, 3000.0, 5000.0]                # same quarter, three rebalances
    evs = [_sf1_to_metrics("T", sf1, price=10.0, market_cap=c, ev_point_in_time=True)["ev_sales"]
           * 1000.0 for c in caps]                 # ev_sales * revenue -> back out EV

    assert evs == sorted(evs), f"EV did not rise with market cap: {evs}"
    for cap, ev in zip(caps, evs):
        assert abs((ev - cap) - 200.0) < 1e-6, (
            f"implied net debt {ev - cap:.2f} != 200 at cap {cap} — the debt leg should be "
            "held at its last reported value while the equity leg re-prices")
    # dollar-for-dollar with the cap, not merely monotone
    assert abs((evs[2] - evs[0]) - (caps[2] - caps[0])) < 1e-6
    # and it is genuinely different from the stale answer it replaced
    stale = [_sf1_to_metrics("T", sf1, price=10.0, market_cap=c,
                             ev_point_in_time=False)["ev_sales"] * 1000.0 for c in caps]
    assert len(set(round(x, 6) for x in stale)) == 1, "stale EV should be constant by definition"
    assert not any(abs(a - b) < 1e-6 for a, b in zip(evs, stale)), (
        "the fix produced the stale value at every cap — is the rebuild running at all?")


def test_every_ev_ratio_moves_with_the_rebalance_and_not_one_of_them_is_left_behind():
    """`ebit_ev` is the one that is actually deployed, so it is the one most worth pinning:
    all three EV ratios must re-price together or the value theme mixes two vintages."""
    sf1 = _sf1()
    lo = _sf1_to_metrics("T", sf1, price=10.0, market_cap=2000.0, ev_point_in_time=True)
    hi = _sf1_to_metrics("T", sf1, price=10.0, market_cap=5000.0, ev_point_in_time=True)
    assert hi["ev_sales"] > lo["ev_sales"]         # pricier on a bigger cap
    assert hi["ev_ebitda"] > lo["ev_ebitda"]
    assert hi["ebit_ev"] < lo["ebit_ev"]           # a YIELD — moves the other way
    # market-cap-based ratios are untouched by this change
    for k in ("book_to_price", "earnings_yield", "fcf_yield"):
        assert lo[k] != hi[k], f"{k} should already track the cap"


def test_the_ev_identity_route_recovers_a_row_with_no_debt_line_items():
    """Second route: `ev - marketcap` is Sharadar's own net debt, already USD, so it needs no
    fx at all. Worth 82 rows on the real export — small, but the alternative for those rows is
    silently keeping the stale value, which is the failure mode this whole change is about."""
    sf1 = _sf1(debt=None, cashneq=None, marketcap=2200.0)   # implies net debt 2400-2200 = 200
    m = _sf1_to_metrics("T", sf1, price=10.0, market_cap=3000.0, ev_point_in_time=True)
    assert m["_ev_src"] == "pit_ev_identity"
    assert abs(m["ev_sales"] * 1000.0 - (3000.0 + 200.0)) < 1e-6


def test_the_two_routes_agree_when_both_are_available():
    """They agree to a p99 of 0.001% of market cap on 193,811 real rows; on a clean fixture
    they should be exact. If these ever diverge, one of them is wrong about currency."""
    a = _sf1_to_metrics("T", _sf1(marketcap=2200.0), price=10.0, market_cap=3000.0,
                        ev_point_in_time=True)
    b = _sf1_to_metrics("T", _sf1(debt=None, cashneq=None, marketcap=2200.0), price=10.0,
                        market_cap=3000.0, ev_point_in_time=True)
    assert a["_ev_src"] == "pit_line_items" and b["_ev_src"] == "pit_ev_identity"
    assert abs(a["ev_sales"] - b["ev_sales"]) < 1e-9


def test_the_route_taken_is_recorded_on_every_row():
    """`ev_freshness` is only as good as this tag — an untagged row cannot be counted as
    stale, and an uncounted stale row is exactly what went unnoticed for months."""
    on = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=3000.0, ev_point_in_time=True)
    off = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=3000.0, ev_point_in_time=False)
    assert on["_ev_src"] == "pit_line_items"
    assert off["_ev_src"] == "stale_flag_off"
    assert on["_ev_drift"] > 0.0, "drift should be non-zero when the cap moved"
    assert abs(off["_ev_drift"]) < 1e-12, "flag off cannot drift — it IS the filing value"


def test_no_market_cap_cannot_silently_produce_a_debt_only_ev():
    m = _sf1_to_metrics("T", _sf1(), price=10.0, market_cap=None, ev_point_in_time=True)
    assert m["_ev_src"] == "stale_no_mc"
    assert abs(m["ev_sales"] - 2400.0 / 1000.0) < 1e-9


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


# --------------------------------------------------------------------------- #
#  ev_freshness — the guard that makes a silent revert loud
# --------------------------------------------------------------------------- #
def _fresh_panel(srcs, drifts=None):
    import pandas as pd
    drifts = drifts if drifts is not None else [0.1] * len(srcs)
    return pd.DataFrame({"ev_src": srcs, "ev_drift": drifts})


def test_ev_freshness_reports_a_clean_panel_as_ok():
    from valuation.edge.fundamental_panel import ev_freshness
    r = ev_freshness(_fresh_panel(["pit_line_items"] * 99 + ["pit_ev_identity"]), warn=False)
    assert r["fresh"] == 1.0 and r["stale"] == 0.0
    assert r["ok"] is True and not r["warnings"]
    assert r["by_source"]["pit_ev_identity"] == 1


def test_ev_freshness_catches_the_flag_being_turned_off():
    """The most likely way this regresses is somebody flipping the env var and nobody
    noticing, so that has to be the loudest case rather than a silent pass."""
    from valuation.edge.fundamental_panel import ev_freshness
    r = ev_freshness(_fresh_panel(["stale_flag_off"] * 100, [0.0] * 100), warn=False)
    assert r["ok"] is False
    assert any("OFF" in w for w in r["warnings"]), r["warnings"]


def test_ev_freshness_catches_a_rebuild_that_quietly_fell_back():
    """A fallback path doing most of the work looks identical to a working fix from the
    outside — same columns, same coverage, no error."""
    from valuation.edge.fundamental_panel import ev_freshness
    r = ev_freshness(_fresh_panel(["pit_line_items"] * 50 + ["stale_no_netdebt"] * 50),
                     warn=False)
    assert abs(r["fresh"] - 0.5) < 1e-9
    assert r["ok"] is False and any("floor" in w for w in r["warnings"])


def test_ev_freshness_reports_the_drift_the_fix_actually_produced():
    """Effect size, not just a pass/fail: a rebuild that runs but never moves anything is
    its own kind of broken and would otherwise read as perfectly healthy."""
    from valuation.edge.fundamental_panel import ev_freshness
    r = ev_freshness(_fresh_panel(["pit_line_items"] * 4, [0.0, 0.05, 0.20, 0.40]), warn=False)
    assert abs(r["drift"]["median"] - 0.125) < 1e-9
    assert abs(r["drift"]["frac_over_10pct"] - 0.5) < 1e-9
    assert abs(r["drift"]["frac_over_25pct"] - 0.25) < 1e-9


def test_ev_freshness_does_not_pretend_a_panel_without_the_column_is_fine():
    from valuation.edge.fundamental_panel import ev_freshness
    import pandas as pd
    r = ev_freshness(pd.DataFrame({"ticker": ["A"]}), warn=False)
    assert r["ok"] is False and r["warnings"]


def test_ev_freshness_is_computed_by_the_backtest():
    import inspect
    from valuation.edge import fundamental_panel as F
    src = inspect.getsource(F.run_backtests)
    assert 'out["ev_freshness"] = ev_freshness(panel)' in src


def test_ev_freshness_reaches_backtest_results_json():
    """`run_backtests` putting it in its own dict is NOT enough: results_file builds a
    curated payload and silently drops anything it does not name, so a block can be computed
    every run and still never reach the file Don and the Cowork agent actually read."""
    from valuation.edge.results_file import build_payload
    res = {"ev_freshness": {"fresh": 0.9995, "stale": 0.0005, "floor": 0.95, "ok": True,
                            "by_source": {"pit_line_items": 136000},
                            "drift": {"median": 0.104, "frac_over_25pct": 0.186},
                            "warnings": []}}
    p = build_payload(res, universe_label="full")
    ev = p.get("ev_freshness")
    assert ev and ev["available"] is True, "ev_freshness dropped by the payload builder"
    assert abs(ev["fresh"] - 0.9995) < 1e-12
    assert ev["by_source"]["pit_line_items"] == 136000
    assert abs(ev["drift"]["median"] - 0.104) < 1e-12


def test_a_stale_run_says_so_in_the_markdown_not_just_the_json():
    """The .md is what gets read at a glance. A stale run has to be visible there or the
    warning only exists somewhere nobody looks."""
    from valuation.edge.results_file import build_payload, render_md
    res = {"ev_freshness": {"fresh": 0.0, "stale": 1.0, "floor": 0.95, "ok": False,
                            "by_source": {"stale_flag_off": 136000}, "drift": {},
                            "warnings": ["ev_point_in_time is OFF for 136,000 rows"]}}
    md = render_md(build_payload(res, universe_label="full"))
    assert "EV IS STALE" in md, md[:2000]


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
