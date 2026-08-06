"""
AUDIT M3 — every guard is fed the bug it was built for, and must complain. Run:

    python tests/test_guards.py

WHY THIS FILE EXISTS
--------------------
This project has been bitten at least six times by the same shape: a check exists, the run
completes, and the check was not looking.

  * five wired factors non-null in 0 of 197,265 rows, contributing to themes for the project's
    entire history;
  * `sector_neutral` grouping on a constant column and reporting nothing;
  * `holdout_theme_validate` computing `rule_fired` and never reading it, so a stability check
    was labelled an out-of-sample confirmation;
  * `scoring.py`'s ">5x cannot be a strong buy" cap written `if base_fv and ...`, so it could
    not fire once the guard set `base_fv = None` — a safety check that only worked when the
    unsafe thing was present;
  * `results_file.build_payload` whitelisting output keys and dropping a correctly-computed
    `top_decile_alpha_tstat` of 4.517;
  * the OI coverage audit not counting a span with no `.pkl`, so a LOST symbol-year read as a
    repair.

Every one of those had a guard, a test suite, or an audit nearby. What none of them had was a
test that fed the guard a KNOWN-BAD INPUT and asserted it complained. **A guard that has never
fired is indistinguishable from a guard that cannot fire, and this project has shipped both.**

THE TWO RULES THIS FILE FOLLOWS
-------------------------------
1. **Use the real failure where one is known.** The KSPI 14.0x fair value, the `-1` open-interest
   sentinel, the `benchmarks` block R10 lost at the schema boundary, the NXPI-2017 symbol-year
   that vanished into its own backup. Synthetic fixtures pass more easily than reality does.
2. **Assert the REFUSAL direction too.** A guard that fires on everything is as useless as one
   that fires on nothing, and it gets switched off faster. Every fixture set below carries a
   clean input that must NOT trip the guard.

Nothing here modifies production code. Where a guard fails its own known-bad fixture the test is
registered with `@known_failure(...)`, naming the owning lane — visible and routed, not silently
green and not red. See `HANDOFF_optionsbot.md` for the census table.
"""
import json
import os
import pickle
import shutil
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd                                                          # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ===========================================================================================
#  known_failure — this suite's xfail, since the project runs tests as plain scripts
# ===========================================================================================
_KNOWN_FAILURES = {}


def known_failure(reason: str, lane: str):
    """Mark a test that SHOULD fail: the guard does not catch what it exists to catch.

    The failure is reported as XFAIL and does not turn the suite red — the repair belongs to
    `lane`, not here, and landing the test with the fix would mean nobody ever saw it fail.
    An unexpected PASS prints loudly (the marker is stale and should be removed) but does not
    fail the run either, so another lane fixing its own bug never breaks this gate.
    """
    def deco(fn):
        _KNOWN_FAILURES[fn.__name__] = (reason, lane)
        return fn
    return deco


def _classify(fn, marked: bool):
    """Run one test and decide what it counts as. Returns (verdict, error-or-None).

    THE RUNNER USES THIS, and so does `test_this_files_own_xfail_mechanism_is_not_itself_inert`
    — deliberately the same function rather than the test checking a copy of the rule, which is
    the mistake this whole file exists to catch.

    A CRASH is never an XFAIL: a marked test that throws a TypeError has rotted rather than
    found something, and filing that under "expected" is how a marker outlives its bug.
    """
    try:
        fn()
    except AssertionError as e:
        return ("XFAIL" if marked else "FAIL"), e
    except Exception as e:                                               # noqa: BLE001
        return "ERROR", e
    return ("XPASS" if marked else "PASS"), None


class _Tmp:
    """`tempfile.TemporaryDirectory` that survives Windows' file locks on teardown."""

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix="valquo_guard_")
        return self.path

    def __exit__(self, *exc):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


# ===========================================================================================
#  TIER 1 — the guards between a wrong number and a USER
# ===========================================================================================
#
# KSPI, 2026-08-05: a $1,289.60 fair value against a $92.19 price — 14.0x — reached the live
# page. These are the real figures.
KSPI_FV, KSPI_PRICE = 1289.5983215433105, 92.19


def _cd(price=KSPI_PRICE, financial_currency="USD", currency="USD",
        fx_rate=1.0, fx_unresolved=False):
    """A CompanyData stand-in. `publication_guard` reads it entirely through getattr."""
    return types.SimpleNamespace(price=price, financial_currency=financial_currency,
                                 currency=currency, fx_rate=fx_rate,
                                 fx_unresolved=fx_unresolved)


def _blend(value, valuable=True):
    return types.SimpleNamespace(value=value, valuable=valuable, growth_led=False)


def test_publication_guard_refuses_the_real_kspi_fair_value():
    """The guard with NO test of any kind before M3, sitting on the highest-blast-radius path
    in the product: it is the last thing between the engine's number and the valuation page."""
    from valuation.engine.pipeline import publication_guard

    reason = publication_guard(_cd(), _blend(KSPI_FV))
    assert reason, "a 14.0x fair value must be refused"
    assert "14.0x" in reason, f"the refusal must quote the observed ratio: {reason}"
    assert "1,289.60" in reason and "92.19" in reason, \
        f"the refusal must quote the numbers it is about: {reason}"


def test_publication_guard_lets_an_ordinary_valuation_through():
    """The refusal direction. A guard that refuses everything is switched off within a week."""
    from valuation.engine.pipeline import publication_guard

    assert publication_guard(_cd(), _blend(120.0)) is None      # 1.3x — an ordinary result
    assert publication_guard(_cd(), _blend(20.0)) is None       # 0.22x — expensive, not refused
    assert publication_guard(_cd(), _blend(9.3)) is None        # 0.10x, below FV_BAND_LOW:
    #                                                             the LOW side warns, never refuses


def test_publication_guard_publishes_exactly_on_the_band_and_refuses_just_past_it():
    """CONSOLIDATE-1 pre-committed `ratio > band` refuses and `ratio == band` publishes, so no
    name sitting exactly on the bar changed state when five implementations became one. An
    off-by-one here silently re-values every borderline name in the book."""
    from valuation.engine.pipeline import publication_guard
    from valuation.engine.publication import FV_BAND_HIGH

    px = 100.0
    assert publication_guard(_cd(price=px), _blend(px * FV_BAND_HIGH)) is None
    assert publication_guard(_cd(price=px), _blend(px * FV_BAND_HIGH + 0.01)) is not None


def test_publication_guard_refuses_an_unresolved_currency_at_a_sane_ratio():
    """The failure the ratio bar CANNOT see. A KZT balance sheet priced in USD can land inside
    the 5x band and still be wrong by an unknown factor; only the currency check catches it."""
    from valuation.engine.pipeline import publication_guard

    cd = _cd(financial_currency="KZT", currency="USD", fx_rate=None, fx_unresolved=True)
    reason = publication_guard(cd, _blend(110.0))               # 1.19x — inside the band
    assert reason and "exchange rate could not be resolved" in reason, reason

    cd2 = _cd(financial_currency="KZT", currency="USD", fx_rate=None, fx_unresolved=False)
    reason2 = publication_guard(cd2, _blend(110.0))
    assert reason2 and "no currency conversion was applied" in reason2, reason2

    # ...and a name whose statements and price share a currency is untouched.
    assert publication_guard(_cd(financial_currency="USD"), _blend(110.0)) is None


def test_a_missing_valuation_is_not_reported_as_a_refusal():
    """`reason` empty means 'nothing to publish'; non-empty means 'we refuse'. Collapsing the
    two is how a name with no DCF yet invites a peer substitute — the erasure CONSOLIDATE-1
    was written for."""
    from valuation.engine.pipeline import publication_guard

    assert publication_guard(_cd(), _blend(KSPI_FV, valuable=False)) is None
    assert publication_guard(_cd(price=0.0), _blend(120.0)) is None
    assert publication_guard(_cd(price=None), _blend(120.0)) is None


def test_the_public_row_guard_is_fail_closed_against_a_nan_fair_value():
    """THE SHAPE THAT HAS BITTEN THIS PROJECT SIX TIMES, checked on the last line of defence.

    A NaN fair value slips past both upstream steps: `publication.decide` refuses it but with an
    EMPTY reason (so no refusal is recorded and no name is marked), and `estimate_fair_values`
    reads `fair_value is not None` as "a DCF exists" and tags the row `dcf`. Both measured.

    `withhold_implausible_fair_values` survives it only because it is written to CONTINUE when
    the row is provably fine, rather than to WITHHOLD when it is provably bad — every NaN
    comparison is False, so the fail-open form (`if ratio > band: withhold`) would pass it
    straight through. That inversion is the whole guard, and it is one edit away from being
    lost, so it is pinned here rather than left to a code reviewer's eye."""
    from valuation.engine.publication import decide
    from valuation.screener.fairvalue import estimate_fair_values
    from valuation.web.withhold import withhold_implausible_fair_values, ROW_WITHHELD

    nan = float("nan")

    # 1. The publication decision refuses it — but says nothing, so nothing downstream is marked.
    v = decide(nan, KSPI_PRICE)
    assert v.publish is False and v.reason == "", \
        "if this ever gains a reason, the row-level defence below stops being the only one"

    # 2. The screener reads NaN as a DCF that already exists and leaves it in place.
    row = {"ticker": "AAA", "sector": "Tech", "price": 50.0, "market_cap": 1e9,
           "fair_value": nan, "extra": {"earnings_yield": 0.09}}
    assert estimate_fair_values([row], peer_rows=[row]) == 0
    assert row["fair_value"] != row["fair_value"], "still NaN, and now tagged as a DCF"

    # 3. The public surface catches it anyway, because it is fail-CLOSED.
    assert (nan > 5.0) is False and (nan <= 5.0) is False, \
        "every NaN comparison is False in BOTH directions — that is the trap"
    assert withhold_implausible_fair_values([row]) == 1
    assert row["fair_value"] is None and row[ROW_WITHHELD] is True
    assert row["fair_value_withheld_reason"], "a blanked cell must still say why"

    # And it does not withhold the ordinary rows on the way past.
    ok = [{"ticker": "BBB", "price": 50.0, "fair_value": 65.0},
          {"ticker": "CCC", "price": 50.0, "fair_value": 250.0},      # exactly 5.0x — the band
          {"ticker": "DDD", "price": 50.0, "fair_value": None}]       # no estimate is not a lie
    assert withhold_implausible_fair_values(ok) == 0, [r["ticker"] for r in ok
                                                       if r.get(ROW_WITHHELD)]


def test_withheld_figures_are_stripped_and_a_clean_payload_is_untouched():
    """`withhold_derived_figures` is pinned in depth by tests/test_withhold.py against the real
    KSPI payload. This is the census cross-check: the alarm fires and the refusal direction
    holds, so a change that neutered it could not pass this file either."""
    from valuation.web import withhold

    withheld = {"fair_value_blend": {"valuable": False, "reason": "refused"},
                "base_fair_value": None,
                "fair_value_scenarios": {"method": "dcf", "bear": 620.27,
                                         "base": 1289.60, "bull": 2888.15},
                "dcf_per_share": 2293.69}
    out = withhold.withhold_derived_figures(withheld)
    assert out["dcf_per_share"] is None
    assert out["fair_value_scenarios"]["base"] is None
    assert json.dumps(out).find("1289.6") == -1, "the withheld number survived somewhere"

    clean = {"fair_value_blend": {"valuable": True, "value": 120.0},
             "base_fair_value": 120.0, "dcf_per_share": 118.0}
    assert withhold.withhold_derived_figures(clean) is clean, \
        "a publishable name must be returned untouched, not merely equal"


def test_the_screener_lens_refuses_the_levered_re_rating_that_produced_chtr():
    """The bar applied where the number is BORN, not only where it is shown.

    `_mature_value` bridges an EV re-rating to equity, and that bridge reduces to
    `implied/price = r + (nd/mc)*(r - 1)`. At the 3x enterprise re-rate cap a name with CHTR's
    4.68x leverage has a CEILING of 12.4x price. The arithmetic is right — equity is a residual
    claim and leverage amplifies it — but a uniform 3x enterprise re-rate is not a defensible
    assumption for a name that trades cheap on an enterprise multiple BECAUSE it is levered.
    Nothing bounded the per-share answer until the band was applied here too."""
    from valuation.screener import fairvalue as FV

    price, mc = 140.0, 20e9
    levered = {"ticker": "CHTR", "sector": "Communication Services", "price": price,
               "market_cap": mc, "extra": {"ev_sales": 2.0, "net_debt": 4.68 * mc}}
    meds = {(None, "ev_sales"): 6.0}                    # peers at 3x this name's multiple

    assert FV._mature_value(levered, meds, price) is None, \
        "a 12.4x per-share re-rating reached the hot list"

    # The refusal direction: the SAME 3x enterprise re-rate on an unlevered name is a 3x
    # equity move, which is inside the band and must still be published.
    unlevered = dict(levered, ticker="AAA", extra={"ev_sales": 2.0, "net_debt": 0.0})
    out = FV._mature_value(unlevered, meds, price)
    assert out is not None and abs(out / price - 3.0) < 1e-9, out


def test_the_screener_lens_drops_a_negative_yield_instead_of_pricing_off_it():
    """A loss-making company has a NEGATIVE earnings yield, and `price * (negative / positive)`
    hands back a negative fair value that looks authoritative and means nothing. The guard is
    the dropping, so a name whose only multiple is negative must get no estimate at all."""
    from valuation.screener import fairvalue as FV

    loss_maker = {"ticker": "AAA", "sector": "Tech", "price": 50.0, "market_cap": 1e9,
                  "extra": {"earnings_yield": -0.08}}
    meds = {(None, "earnings_yield"): 0.05}
    assert FV._pos_yield(loss_maker, "earnings_yield") is None
    assert FV._mature_value(loss_maker, meds, 50.0) is None

    profitable = dict(loss_maker, extra={"earnings_yield": 0.08})
    assert FV._mature_value(profitable, meds, 50.0) is not None


def test_a_recorded_refusal_is_never_overwritten_by_a_peer_estimate():
    """THE ERASURE, end to end. `_enrich_with_dcf` used to write `fair_value = None` on a
    refusal and record nothing, so `estimate_fair_values` read that None as 'no DCF computed
    yet' and substituted a peer estimate — which is how KSPI, STLA and CHTR sat on the public
    hot list with fair values while their own valuation pages refused them outright."""
    from valuation.engine.publication import ROW_WITHHELD, record_refusal
    from valuation.screener.fairvalue import estimate_fair_values

    refused = {"ticker": "KSPI", "sector": "Tech", "price": KSPI_PRICE, "market_cap": 1e10,
               "extra": {"earnings_yield": 0.09, "fcf_yield": 0.07}}
    record_refusal(refused, "Cannot value this name: the model's $1,289.60 is 14.0x the price.")
    peers = [{"sector": "Tech", "extra": {"earnings_yield": 0.03, "fcf_yield": 0.025}}
             for _ in range(8)]

    estimate_fair_values([refused], peer_rows=peers + [refused])
    assert refused["fair_value"] is None, "a refused name was handed a peer estimate anyway"
    assert refused["upside"] is None
    assert refused[ROW_WITHHELD] is True
    assert refused["fair_value_method"] == "withheld", \
        "the row must say WHY it is empty, or the next surface fills it in again"

    # The refusal direction: an ordinary name with no DCF still gets its peer estimate.
    ordinary = {"ticker": "AAA", "sector": "Tech", "price": 50.0, "market_cap": 1e9,
                "extra": {"earnings_yield": 0.09, "fcf_yield": 0.07}}
    assert estimate_fair_values([ordinary], peer_rows=peers + [ordinary]) == 1
    assert ordinary["fair_value"] is not None


# ===========================================================================================
#  TIER 2 — the guards between a wrong number and a RESEARCH VERDICT
# ===========================================================================================
def test_missing_result_blocks_names_the_block_r10_lost():
    """AUDIT B22/M6. A validation block that never ran leaves the results file looking like a
    run that ran and found nothing. `benchmarks` is in the list precisely because a silently
    absent benchmark block would leave the uninvestable equal-weight figure standing alone.

    This guard had ZERO test references before M3."""
    from valuation.edge.fundamental_panel import missing_result_blocks, RESULT_BLOCKS

    full = {k: {"x": 1} for k in RESULT_BLOCKS}
    assert missing_result_blocks(full) == [], "a complete run must report nothing missing"

    no_bench = dict(full)
    no_bench.pop("benchmarks")
    assert missing_result_blocks(no_bench) == ["benchmarks"]

    # EMPTY is the dangerous case, not absent: `{}` serialises, reads as "computed, nothing
    # found", and raises nothing. It must be reported exactly like an absence.
    empty = dict(full, cpcv={}, costs=[])
    assert set(missing_result_blocks(empty)) == {"cpcv", "costs"}

    none_valued = dict(full, holdout_validation=None)
    assert missing_result_blocks(none_valued) == ["holdout_validation"]


def test_a_block_that_threw_is_caught_by_the_writer_not_by_the_block_check():
    """Two guards, and knowing which does what. `missing_result_blocks` asks "is the block
    THERE"; a block that raised is there — it holds `{"status": "error: ..."}` — so it passes
    that check and is caught instead by `build_payload`'s `errors` scan. Assuming either one
    covers the other is how a degraded run reads as a run that found nothing."""
    from valuation.edge.fundamental_panel import missing_result_blocks, RESULT_BLOCKS
    from valuation.edge.results_file import build_payload

    threw = {k: {"x": 1} for k in RESULT_BLOCKS}
    threw["cpcv"] = {"status": "error: boom"}
    assert missing_result_blocks(threw) == [], \
        "an errored block IS present — this check is not the one that catches it"

    errs = build_payload(dict(threw, horizons={}))["errors"]
    assert [e["block"] for e in errs] == ["cpcv"], errs
    assert build_payload({"horizons": {}, "cpcv": {"n_paths": 15}})["errors"] == []


def test_missing_result_blocks_covers_every_block_the_record_argues_about():
    """The guard is only as good as its list. These four are the blocks whose absence has
    actually been argued over in the record — costs (P6), holdout_validation (the theme
    gate), cpcv (the weight authority), benchmarks (R10)."""
    from valuation.edge.fundamental_panel import RESULT_BLOCKS

    for k in ("costs", "holdout_validation", "cpcv", "benchmarks"):
        assert k in RESULT_BLOCKS, f"{k} can go missing without the run failing"


def test_the_schema_boundary_carries_the_two_fields_it_actually_dropped():
    """The R9/R10 loss, reproduced. `quantile_backtest` computed `top_decile_alpha_tstat`
    correctly on the first full run and the canonical file showed `None` beside a real 4.517,
    because `build_payload` whitelists what it writes. Nothing raised.

    4.517421601141459 is the value from the run that lost it."""
    from valuation.edge.results_file import build_payload

    res = {"horizons": {}, "cpcv": {},
           "construction": {"top_decile_alpha": 0.0717,
                            "top_decile_alpha_tstat": 4.517421601141459,
                            "top_decile_alpha_tstat_nw": 4.376230427940328},
           "benchmarks": {"spy_total_return": {"excess": 0.0999, "hac_t": 3.770}}}
    p = build_payload(res)
    cn = p["construction"]
    assert cn["top_decile_alpha_tstat"] == 4.517421601141459, \
        "the headline's significance statistic was dropped at the schema boundary again"
    assert cn["top_decile_alpha_tstat_nw"] == 4.376230427940328
    assert p["benchmarks"]["spy_total_return"]["excess"] == 0.0999, \
        "R10's investable benchmarks were dropped at the schema boundary again"


def test_the_schema_boundary_still_drops_a_metric_nobody_whitelisted():
    """CHARACTERISATION, NOT AN ENDORSEMENT — and the reason this file has a BUGS FOUND entry.

    `missing_result_blocks` guards BLOCK absence. Nothing guards FIELD absence, and the R9 loss
    was field-level: a metric added to a computation does not reach the canonical file, and the
    canonical file is what every other agent reads. This test pins the hazard so it is visible
    rather than assumed. It fails the day someone closes it — which is the point."""
    from valuation.edge.results_file import build_payload

    p = build_payload({"horizons": {}, "cpcv": {},
                       "construction": {"a_brand_new_metric": 1.23}})
    assert "a_brand_new_metric" not in p["construction"], \
        "GOOD NEWS: field-level pass-through now exists — update the M3 census and delete this"


def test_signal_coverage_catches_the_all_null_column_and_stays_quiet_on_a_good_panel():
    """The original sin: `roe`, `roic`, `assetturnover` were non-null in 0 of 197,265 rows
    because the Sharadar export is ARQ-only and those columns are filled in ART/ARY. An empty
    column contributes nothing to a theme mean, raises no error, and the run completes."""
    import numpy as np
    from valuation.edge.fundamental_panel import signal_coverage, COVERAGE_FLOOR

    n = 200
    good = pd.DataFrame({"z_roe": np.linspace(-2, 2, n), "z_gp_on_capital": np.linspace(-1, 1, n),
                         "fwd_ret": np.linspace(-0.1, 0.1, n)})
    assert signal_coverage(good, warn=False)["below_floor"] == []

    dead = good.copy()
    dead["z_roe"] = np.nan                                   # the actual ARQ/ART shape
    below = signal_coverage(dead, warn=False)["below_floor"]
    named = {b["name"] for b in below}
    assert "roe" in named, f"a wired-but-empty signal must be named: {below}"
    # The entry has to say WHICH THEME was silently averaging over it — "roe is empty" and
    # "quality has been running on 9 of its 10 inputs for years" are different findings.
    assert [b for b in below if b["name"] == "roe"][0]["theme"] == "quality"
    assert COVERAGE_FLOOR > 0, "a floor of 0 would make this guard unable to fire"


def test_options_coverage_block_catches_an_empty_input_and_passes_a_full_one():
    """The same rule on the options arm, which had ZERO test references before M3. An absent
    option input fails exactly like an absent factor: the trade never fires, nothing raises."""
    from valuation.edge.options_vrp import coverage_block

    full = [{"iv_rank": 0.4, "atm_iv": 0.28, "short_delta": -0.22, "short_oi": 400,
             "earnings_known": True} for _ in range(50)]
    assert coverage_block(full, {}, floor=0.05)["below_floor"] == []

    dead = [dict(r, iv_rank=None) for r in full]             # the wired-but-empty shape
    r = coverage_block(dead, {}, floor=0.05)
    assert r["below_floor"] == ["iv_rank"], r["below_floor"]
    assert r["coverage"]["iv_rank"] == 0.0

    # The floor is a FRACTION of trades, so a signal present on a handful of rows out of many
    # must still read as absent — the case a naive `any()` check would pass.
    thin = [dict(r0, iv_rank=None) for r0 in full[:49]] + [full[49]]
    assert coverage_block(thin, {}, floor=0.05)["below_floor"] == ["iv_rank"]


def test_options_sanity_block_catches_an_arithmetically_impossible_trade():
    """Coverage says an input is PRESENT; this says the OUTPUT is SANE. Every check in
    `sanity_block` is an arithmetic invariant of a defined-risk put credit spread, so a flag is
    a bug and not a market observation.

    NOT all new: `test_edge.py:2416` already fed it the clean, impossible-loss, wide-credit and
    off-delta cases. M3 adds the DTE window (an entry outside 25-50 is a different strategy
    wearing this one's name) and re-states the rest here so the census row is checkable in one
    place."""
    from valuation.edge.options_vrp import sanity_block

    def _trade(**kw):
        base = {"pnl_pct": 0.3, "credit_ps": 0.8, "width": 5.0, "short_delta": -0.22,
                "dte": 35, "clamped_marks": 0, "marks_seen": 30, "exit_reason": "profit_target"}
        base.update(kw)
        return base

    clean = ([_trade() for _ in range(8)]
             + [_trade(exit_reason="expiry") for _ in range(2)])   # 80% dominant: under the bar
    assert sanity_block(clean)["clean"] is True, sanity_block(clean)["flags"]

    # A spread cannot lose more than its width net of credit; -150% is a bug in the fill engine.
    impossible = clean[:-1] + [_trade(pnl_pct=-1.5)]
    assert any("MORE than max risk" in f for f in sanity_block(impossible)["flags"])

    # Credit above the width means the position was opened for more than it can ever lose.
    assert any("credit outside" in f
               for f in sanity_block(clean[:-1] + [_trade(credit_ps=7.0)])["flags"])

    # A 0.80-delta short leg is not the strategy that was backtested.
    assert any("short delta outside" in f
               for f in sanity_block(clean[:-1] + [_trade(short_delta=-0.80)])["flags"])

    # An entry outside the committed 25-50 DTE window is a different strategy wearing the name.
    assert any("DTE window" in f
               for f in sanity_block(clean[:-1] + [_trade(dte=400)])["flags"])


def test_options_sanity_block_notices_when_one_exit_reason_eats_the_book():
    """Not an arithmetic error — a design failure that looks like a clean run. If 100% of trades
    leave the same way, the exit discipline is not binding and the backtest is measuring one
    rule, not the four it claims."""
    from valuation.edge.options_vrp import sanity_block

    one_way = [{"pnl_pct": 0.3, "credit_ps": 0.8, "width": 5.0, "short_delta": -0.22, "dte": 35,
                "clamped_marks": 0, "marks_seen": 30, "exit_reason": "expiry"} for _ in range(50)]
    assert any("exit reason accounts for" in f for f in sanity_block(one_way)["flags"])


def test_autopsy_feature_coverage_reports_an_empty_feature_as_zero():
    """The options autopsy's own coverage rule, applied before any IC is believed. `_f` is the
    numeric coercion, so a feature that is present but non-numeric on every row is EMPTY — the
    distinction a `k in row` check gets wrong."""
    from valuation.edge.options_autopsy import feature_coverage

    rows = [{"_f": {"iv_rank": 0.4, "term_slope": None, "junk": "n/a"}} for _ in range(10)]
    rows[0]["_f"]["term_slope"] = 0.02
    cov = feature_coverage(rows)
    assert cov["iv_rank"] == 1.0
    assert cov["term_slope"] == 0.1
    assert cov["junk"] == 0.0, "a non-numeric column is not coverage"


def test_the_vendor_pricer_check_catches_a_subtly_wrong_delta():
    """`validate_against_vendor` exists because a hand-rolled pricer that is quietly wrong would
    corrupt every options signal while every run completed normally. It works — and it has NO
    CALLER anywhere in the tree, which is its own finding (see BUGS FOUND)."""
    from valuation.edge.blackscholes import validate_against_vendor

    keys = {"expiration": ["2026-01-16"] * 4, "strike": [100.0, 105.0, 110.0, 115.0],
            "right": ["C"] * 4}
    vendor = pd.DataFrame(dict(keys, delta=[0.62, 0.51, 0.39, 0.28],
                               implied_vol=[0.31, 0.30, 0.29, 0.29]))
    agree = pd.DataFrame(dict(keys, delta=[0.63, 0.50, 0.40, 0.28],
                              iv=[0.31, 0.31, 0.29, 0.30]))
    r = validate_against_vendor(agree, vendor)
    assert r["n"] == 4 and r["delta_agree_pct"] == 1.0 and r["iv_agree_pct"] == 1.0

    wrong = pd.DataFrame(dict(keys, delta=[0.42, 0.31, 0.19, 0.08],      # every delta -0.20
                              iv=[0.31, 0.30, 0.29, 0.29]))
    bad = validate_against_vendor(wrong, vendor)
    assert bad["delta_agree_pct"] == 0.0, "a uniformly wrong pricer must not read as agreement"
    assert abs(bad["delta_median_abs_err"] - 0.20) < 1e-9


def test_the_vendor_pricer_check_reports_no_overlap_as_n_zero_not_as_agreement():
    """The silence to be careful with: nothing in common returns `{'n': 0}` with no agreement
    fields at all. A caller writing `.get('delta_agree_pct', 1.0)` reads a total miss as a
    perfect score, which is why the n must be checked first."""
    from valuation.edge.blackscholes import validate_against_vendor

    vendor = pd.DataFrame({"expiration": ["2026-01-16"], "strike": [100.0], "right": ["C"],
                           "delta": [0.62], "implied_vol": [0.31]})
    mine = pd.DataFrame({"expiration": ["2027-01-15"], "strike": [100.0], "right": ["C"],
                         "delta": [0.62], "iv": [0.31]})
    r = validate_against_vendor(mine, vendor)
    assert r == {"n": 0}
    assert "delta_agree_pct" not in r, \
        "a no-overlap comparison must not report an agreement rate of any kind"


# ===========================================================================================
#  TIER 3 — the guards between a wrong number and the DATA ON DISK
# ===========================================================================================
def _oi_frame(oi_values, rows_per=1):
    n = len(oi_values) * rows_per
    return pd.DataFrame({
        "expiration": ["2020-06-19"] * n, "strike": [100.0] * n, "right": ["C"] * n,
        "date": ["2020-05-01"] * n, "bid": [1.0] * n, "ask": [1.2] * n, "volume": [10] * n,
        "open_interest": [v for v in oi_values for _ in range(rows_per)]})


def test_the_oi_audit_reads_minus_one_as_unknown_and_zero_as_known():
    """`scan_one`, the per-file worker of the open-interest audit — ZERO test references before
    M3. `-1` is the feed's UNKNOWN sentinel, not an open interest. Reading it as a quantity is
    audit B4, and reading a genuine zero as unknown would be the same error mirrored."""
    import oi_coverage_audit as A

    with _Tmp() as tmp:
        def _write(name, df):
            p = os.path.join(tmp, name + ".pkl")
            with open(p, "wb") as f:
                pickle.dump(df, f)
            return p

        key, rows, known, mn, err = A.scan_one(_write("AAA-2020", _oi_frame([-1, -1, -1, -1])))
        assert (key, rows, known, err) == ("AAA-2020", 4, 0.0, None)
        assert mn == -1, "the audit must record how bad it is, not merely that it is bad"

        assert A.scan_one(_write("BBB-2020", _oi_frame([-1, 5, -1, 5])))[2] == 0.5
        assert A.scan_one(_write("CCC-2020", _oi_frame([10, 20, 30])))[2] == 1.0
        # A contract that genuinely has no open interest is KNOWN to have none.
        assert A.scan_one(_write("DDD-2020", _oi_frame([0, 0, 0])))[2] == 1.0


def test_the_oi_audit_distinguishes_an_unreadable_file_from_a_clean_one():
    """Three failure shapes that must not be silently scored as coverage: an unpicklable file,
    an empty frame, and a frame with no `open_interest` column at all. Each returns an `err`,
    and only the third carries a coverage number — 0.0, the safe direction."""
    import oi_coverage_audit as A

    with _Tmp() as tmp:
        broken = os.path.join(tmp, "AAA-2020.pkl")
        with open(broken, "wb") as f:
            f.write(b"not a pickle at all")
        key, rows, known, mn, err = A.scan_one(broken)
        assert known is None and err and rows == 0, (known, err)

        empty = os.path.join(tmp, "BBB-2020.pkl")
        with open(empty, "wb") as f:
            pickle.dump(pd.DataFrame({"open_interest": []}), f)
        assert A.scan_one(empty)[4] == "empty frame"

        nocol = os.path.join(tmp, "CCC-2020.pkl")
        with open(nocol, "wb") as f:
            pickle.dump(pd.DataFrame({"strike": [100.0, 105.0]}), f)
        key, rows, known, mn, err = A.scan_one(nocol)
        assert known == 0.0 and err == "no open_interest column" and rows == 2


@known_failure("`year_files` enumerates *.pkl only, so a symbol-year that exists ONLY as a "
               "`.bak_oi` orphan vanishes from the scan and its absence reads as a repair. "
               "This is the NXPI-2017 loss (144,300 rows) exactly. `oi_remine` sweeps orphans "
               "back at the START of its own run, which mitigates but does not close it: an "
               "audit run while a shard is stopped still cannot see the gap.",
               lane="options bot (this lane owns oi_coverage_audit.py) — needs a decision, "
                    "not a patch: either the audit counts orphans, or it records the cache's "
                    "file inventory so a shrinking one is loud")
def test_the_oi_audit_can_see_a_symbol_year_that_vanished_into_its_backup():
    """THE KNOWN-BAD FIXTURE, and it is not caught. NXPI-2017 was set aside at `.bak_oi` before
    a re-pull, the shard was killed in that window, and the span showed up in the coverage diff
    as a span that had been FIXED — because it had simply stopped being counted."""
    import oi_coverage_audit as A

    with _Tmp() as tmp:
        d = os.path.join(tmp, "NXPI")
        os.makedirs(d)
        with open(os.path.join(d, "NXPI-2017.pkl.bak_oi"), "wb") as f:
            pickle.dump(_oi_frame([-1, -1, 5]), f)          # 144,300 rows, in miniature
        seen = A.year_files(tmp)
        assert any("NXPI-2017" in os.path.basename(p) for p in seen), (
            "a symbol-year that exists only as a backup is invisible to the audit, so its "
            "loss reads as a repair")


def test_the_oi_audit_finds_every_ordinary_symbol_year():
    """The refusal direction for the row above: on an intact cache the enumeration is complete,
    and non-pickle litter beside it is correctly ignored."""
    import oi_coverage_audit as A

    with _Tmp() as tmp:
        for sym, years in (("AAA", (2019, 2020)), ("BBB", (2020,))):
            d = os.path.join(tmp, sym)
            os.makedirs(d)
            for y in years:
                with open(os.path.join(d, f"{sym}-{y}.pkl"), "wb") as f:
                    pickle.dump(_oi_frame([1, 2]), f)
                for junk in (".dte", ".oi_degraded", ".alias"):
                    with open(os.path.join(d, f"{sym}-{y}.pkl{junk}"), "w") as f:
                        f.write("x\n")
        with open(os.path.join(tmp, "_oi_audit_checkpoint.json"), "w") as f:
            f.write("{}")                                  # a file, not a directory, at the root
        found = sorted(os.path.basename(p) for p in A.year_files(tmp))
        assert found == ["AAA-2019.pkl", "AAA-2020.pkl", "BBB-2020.pkl"], found


def _stub_thetabulk_without_a_key():
    """A ThetaBulk that can never touch the network. `oi_remine.main` stops the moment it sees
    an empty key, which is exactly the window the recovery sweep runs in."""
    class _Stub:
        def __init__(self, *a, **kw):
            self._key = ""
    return _Stub


def _drive_oi_remine(tmp, below_floor=None):
    """Run `oi_remine.main()` against a temporary cache with the network stubbed out."""
    import oi_remine as R

    cov = os.path.join(tmp, "OI_COVERAGE.json")
    with open(cov, "w", encoding="utf-8") as f:
        json.dump({"below_floor": below_floor or {}}, f)

    saved = (R.CACHE_ROOT, R.COVERAGE_JSON, R.RESULT_JSON, R.PROGRESS, R.ThetaBulk, sys.argv)
    R.CACHE_ROOT = os.path.join(tmp, "cache")
    R.COVERAGE_JSON = cov
    R.RESULT_JSON = os.path.join(tmp, "OI_REMINE_RESULT.json")
    R.PROGRESS = os.path.join(tmp, "progress.txt")
    R.ThetaBulk = _stub_thetabulk_without_a_key()
    sys.argv = ["oi_remine.py"]
    try:
        R.main()
    finally:
        (R.CACHE_ROOT, R.COVERAGE_JSON, R.RESULT_JSON, R.PROGRESS, R.ThetaBulk,
         sys.argv) = saved


def test_oi_remine_sweeps_an_orphaned_backup_back_before_doing_anything_else():
    """THE NXPI-2017 REPAIR, driven rather than grepped.

    The existing check for this asserts that the string `.bak_oi` appears in the source file —
    which passes just as happily if the sweep is commented out. This runs it: an orphan on disk,
    the network stubbed to a keyless client so `main` returns immediately after the sweep, and
    the symbol-year must be back at its live path with its rows intact."""
    with _Tmp() as tmp:
        d = os.path.join(tmp, "cache", "NXPI")
        os.makedirs(d)
        live = os.path.join(d, "NXPI-2017.pkl")
        with open(live + ".bak_oi", "wb") as f:
            pickle.dump(_oi_frame([-1, -1, 5, 7]), f)
        assert not os.path.exists(live)

        _drive_oi_remine(tmp)

        assert os.path.exists(live), "the orphaned symbol-year was not swept back"
        assert not os.path.exists(live + ".bak_oi"), "the backup must be consumed, not copied"
        with open(live, "rb") as f:
            assert len(pickle.load(f)) == 4, "the recovered frame lost rows"


def test_oi_remine_does_not_overwrite_a_live_frame_with_a_stale_backup():
    """The refusal direction, and the one that matters most: a `.bak_oi` sitting BESIDE a
    completed re-pull is litter from a successful run. Restoring it would trade the newer frame
    for the older one — the guard destroying data instead of saving it."""
    with _Tmp() as tmp:
        d = os.path.join(tmp, "cache", "AAPL")
        os.makedirs(d)
        live = os.path.join(d, "AAPL-2020.pkl")
        with open(live, "wb") as f:
            pickle.dump(_oi_frame([5, 6, 7, 8, 9, 10]), f)          # the good, re-pulled frame
        with open(live + ".bak_oi", "wb") as f:
            pickle.dump(_oi_frame([-1, -1]), f)                     # the stale, degraded one

        _drive_oi_remine(tmp)

        with open(live, "rb") as f:
            kept = pickle.load(f)
        assert len(kept) == 6 and (kept["open_interest"] >= 0).all(), \
            "a stale backup was restored over a healthy frame"


def test_oi_remine_refuses_to_run_at_all_without_a_key():
    """Without a key every span would be re-pulled to nothing and marked `.oi_nosource` — the
    permanent 'never retry this again' mark. The refusal is the guard."""
    with _Tmp() as tmp:
        d = os.path.join(tmp, "cache", "AAA")
        os.makedirs(d)
        with open(os.path.join(d, "AAA-2020.pkl"), "wb") as f:
            pickle.dump(_oi_frame([-1, -1, -1]), f)

        _drive_oi_remine(tmp, below_floor={"AAA-2020": 0.0})

        assert not os.path.exists(os.path.join(d, "AAA-2020.pkl.oi_nosource")), \
            "a keyless run must not mark a span permanently unrecoverable"
        assert not os.path.exists(os.path.join(tmp, "OI_REMINE_RESULT.json")), \
            "a keyless run must record no verdicts at all"


def test_the_degraded_year_sidecar_is_written_cleared_and_never_silent():
    """The writer side of B4. When the separate open-interest call faults, every row of the span
    gets `-1` and the year caches as COMPLETE — indistinguishable on disk from a year whose
    contracts genuinely have no OI. The sidecar is what tells the two apart."""
    from valuation.edge import theta_bulk as TB

    with _Tmp() as tmp:
        tb = TB.ThetaBulk(api_key="test-key-never-used", root=tmp)
        path = TB.year_path("ZZZ", 2020, tmp)

        tb._fetch_year = lambda s, y: (_oi_frame([-1] * 20), False)
        assert tb.ensure_year("ZZZ", 2020) is True
        assert os.path.exists(path + ".oi_degraded"), "a degraded year must be visible on disk"
        body = open(path + ".oi_degraded", encoding="utf-8").read()
        assert "coverage 0.000000" in body and "oi_call_faults" in body, body

        os.remove(path)                                   # re-mine the same span, cleanly
        tb._mem, tb._mem_order = {}, []
        tb._fetch_year = lambda s, y: (_oi_frame(list(range(20))), False)
        assert tb.ensure_year("ZZZ", 2020) is True
        assert not os.path.exists(path + ".oi_degraded"), \
            "a recovered year must clear the mark, or the report never stops accusing it"


def test_a_deeper_pull_that_lost_rows_is_refused_and_a_genuine_superset_is_kept():
    """AUDIT O15. A 200-DTE pull of a span is a strict SUPERSET of the 90-DTE pull, so a deeper
    frame with FEWER rows means the pull was partial in a way the failure flags did not catch.
    Keeping it would trade real, expensive data for an unproven frame."""
    from valuation.edge import theta_bulk as TB

    with _Tmp() as tmp:
        path = TB.year_path("ZZZ", 2020, tmp)
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as f:
            pickle.dump(_oi_frame(list(range(40)), rows_per=4), f)      # 160 rows at 90 DTE
        with open(path + ".dte", "w", encoding="utf-8") as f:
            f.write("90 pulled 2026-01-01\n")

        tb = TB.ThetaBulk(api_key="test-key-never-used", root=tmp, max_dte=200,
                          upgrade_depth=True)
        tb._fetch_year = lambda s, y: (_oi_frame(list(range(30)), rows_per=1), False)   # 30 rows
        assert tb.ensure_year("ZZZ", 2020) is False, "a thinner deep pull must be refused"
        with open(path, "rb") as f:
            assert len(pickle.load(f)) == 160, "the shallow frame was overwritten"
        assert TB.cached_dte("ZZZ", 2020, tmp) == 90, "the refused pull moved the depth stamp"

        tb._mem, tb._mem_order = {}, []
        tb._fetch_year = lambda s, y: (_oi_frame(list(range(50)), rows_per=8), False)   # 400
        assert tb.ensure_year("ZZZ", 2020) is True, "a genuine superset must be accepted"
        assert TB.cached_dte("ZZZ", 2020, tmp) == 200


def test_a_partial_deepening_stays_visible_in_the_depth_report():
    """After O15 only the most liquid ~100 names sit at 200 DTE and everything else is still at
    90. Any claim about term structure has to say which set it is talking about, so a cache that
    is deep in parts must never report as uniformly deep."""
    from valuation.edge import theta_bulk as TB

    with _Tmp() as tmp:
        def _year(sym, year, dte):
            d = os.path.join(tmp, sym)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{sym}-{year}.pkl"), "wb") as f:
                pickle.dump(_oi_frame([1, 2]), f)
            if dte is not None:
                with open(os.path.join(d, f"{sym}-{year}.pkl.dte"), "w", encoding="utf-8") as f:
                    f.write(f"{dte} pulled 2026-01-01\n")

        _year("DEEP", 2019, 200); _year("DEEP", 2020, 200)
        _year("MIXED", 2019, 90); _year("MIXED", 2020, 200)
        _year("LEGACY", 2019, None)          # no sidecar: recorded history, pulled at 90

        rep = TB.depth_report(tmp)
        assert rep["names_fully_deep"] == ["DEEP"], rep["names_fully_deep"]
        assert rep["names_mixed"] == ["MIXED"], rep["names_mixed"]
        assert rep["by_depth"]["90"] == 2 and rep["by_depth"]["200"] == 3, rep["by_depth"]
        assert rep["n_names"] == 3

    with _Tmp() as tmp:
        assert TB.depth_report(os.path.join(tmp, "nothing-here"))["by_depth"] == {}


def test_an_alias_that_is_a_different_live_company_is_caught():
    """`WBD -> T` wrote ~1.00M rows of AT&T's chains into WBD's cache before this check existed.
    Overlap is the discriminator: a rename is a handover, so a predecessor that traded in the
    same year as its 'successor' is not a predecessor at all."""
    from valuation.edge import theta_bulk as TB

    with _Tmp() as tmp:
        def _years(sym, years):
            d = os.path.join(tmp, sym)
            os.makedirs(d, exist_ok=True)
            for y in years:
                with open(os.path.join(d, f"{sym}-{y}.pkl"), "wb") as f:
                    pickle.dump(_oi_frame([1]), f)

        _years("WBD", [2022, 2023, 2024])
        _years("T", [2021, 2022, 2023, 2024])          # still live, and overlapping
        _years("DISCA", [2016, 2018, 2021])            # genuinely stopped where WBD began

        assert TB.alias_overlap_conflicts({"WBD": ["T"]}, tmp) == {"WBD<-T": [2022, 2023, 2024]}
        assert TB.alias_overlap_conflicts({"WBD": ["DISCA"]}, tmp) == {}
        # No cached data is NO EVIDENCE, and must not be reported as a clean bill either way.
        assert TB.alias_overlap_conflicts({"WBD": ["NEVERTRADED"]}, tmp) == {}


def test_the_shipped_alias_table_has_no_overlap_conflict_against_the_real_cache():
    """The table that actually ships, checked against whatever cache this machine has. Skips
    rather than lies when the cache is absent — a check with no data is not a pass."""
    from valuation.edge import theta_bulk as TB

    if not os.path.isdir(TB.CACHE_ROOT):
        return                       # no mined cache here (CI): no evidence, nothing claimed
    conflicts = TB.alias_overlap_conflicts()
    assert conflicts == {}, f"a shipped alias overlaps its successor: {conflicts}"


# ===========================================================================================
#  The census itself — the guards this file could NOT reach, recorded rather than skipped
# ===========================================================================================
UNTESTABLE = {
    "check_lanes.py": "NOT IN GIT. The import-graph lane validator exists only in the shared "
                      "checkout and `git ls-files` does not know it, so no worktree and no "
                      "clean clone can run or test it. Same class as the four untracked audit "
                      "documents. Owning lane: whoever owns the audit tooling.",
    "theta_bulk._fetch_span": "Needs a live ThetaData subscription. The RETRY/backoff policy "
                              "around it is only observable against a faulting feed.",
    "options_greeks.repair_coverage": "Needs the mined cache (~18GB) plus a live feed to "
                                      "re-pull what it repairs.",
    "fundamental_panel.build_fundamental_panel": "Needs the licensed Sharadar exports in "
                                                 "data/backtest; the guards INSIDE it "
                                                 "(signal_coverage, sanity_check, "
                                                 "ev_freshness) are all pinned separately.",
}


def test_this_files_own_xfail_mechanism_is_not_itself_inert():
    """M3's thesis, turned on M3. `known_failure` is the guard that keeps a non-firing guard
    VISIBLE, so if it silently swallowed everything, the one real finding in this file would
    read as a pass and nobody would ever chase it.

    Both directions are exercised against the real runner state: a marked test that fails must
    be counted XFAIL (not FAIL), and a marked test that passes must be counted XPASS (not PASS),
    because a stale marker hides a guard that has since been repaired."""
    assert _KNOWN_FAILURES, "no test is marked — the mechanism has nothing to prove"
    for name in _KNOWN_FAILURES:
        assert name in globals() and callable(globals()[name]), \
            f"@known_failure marks {name}, which is not a test in this file — a stale marker " \
            f"would silently downgrade nothing at all"
        reason, lane = _KNOWN_FAILURES[name]
        assert len(reason) > 80, f"{name}: an XFAIL without a real reason is just a skip"
        assert lane and "lane" not in lane.lower()[:4], f"{name}: name the owning lane"

    # The classification itself, run for real: the runner must route a failure by whether the
    # test is marked, not by anything about the exception.
    def _boom():
        raise AssertionError("x")

    def _fine():
        return None

    def _kaboom():
        raise ValueError("not an assertion")

    assert _classify(_boom, marked=False)[0] == "FAIL"
    assert _classify(_boom, marked=True)[0] == "XFAIL"
    assert _classify(_fine, marked=True)[0] == "XPASS"
    assert _classify(_fine, marked=False)[0] == "PASS"
    # A CRASH is never an XFAIL. A marked test that stops importing or throws a TypeError has
    # rotted, and quietly filing that under "expected" is how the marker outlives its bug.
    assert _classify(_kaboom, marked=True)[0] == "ERROR"


def test_the_untestable_list_is_specific_rather_than_a_shrug():
    """'Needs a live API' is a legitimate reason; absence is not. Each entry must name a real
    blocker, so the row cannot quietly become a place to put guards nobody wanted to write."""
    assert len(UNTESTABLE) >= 4
    for guard, why in UNTESTABLE.items():
        assert len(why) > 60, f"{guard}: give a real reason, not a shrug"
        assert any(w in why for w in ("Needs", "NOT IN GIT")), f"{guard}: {why}"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    n = {"PASS": 0, "FAIL": 0, "XFAIL": 0, "XPASS": 0, "ERROR": 0}
    for t in tests:
        known = _KNOWN_FAILURES.get(t.__name__)
        verdict, err = _classify(t, marked=bool(known))
        n[verdict] += 1
        if verdict == "PASS":
            print(f"  PASS  {t.__name__}")
        elif verdict == "FAIL":
            print(f"  FAIL  {t.__name__}: {err}")
        elif verdict == "ERROR":
            print(f"  ERROR {t.__name__}: {type(err).__name__}: {err}")
        elif verdict == "XFAIL":
            print(f"  XFAIL {t.__name__}\n         GUARD DOES NOT FIRE: {err}"
                  f"\n         owning lane: {known[1]}")
        else:
            print(f"  XPASS {t.__name__} — the guard now fires; delete its "
                  f"@known_failure marker and update the M3 census")
    print(f"\n{n['PASS']}/{len(tests)} guard tests passed"
          f"  ({n['XFAIL']} xfail, {n['XPASS']} xpass, "
          f"{n['FAIL'] + n['ERROR']} failed)")
    failed = n["FAIL"] + n["ERROR"]
    xfail = n["XFAIL"]
    if xfail:
        print("XFAIL = a guard was fed the bug it exists to catch and did NOT complain. "
              "Routed to its owning lane above; see HANDOFF_optionsbot.md '## BUGS FOUND'.")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
