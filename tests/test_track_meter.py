"""Tests for the paper track's pre-registered evidence meter.

Run: python tests/test_track_meter.py

These exist for one reason: `PAPER_TRACK_CONTRACT.md` fixed every parameter of this meter on
2026-08-09, before a single complete month of the series existed, and a pre-registration that
can be quietly edited is not one. So the constants are pinned to LITERALS here -- if someone
changes sigma, rho, alpha, the cost drag or a date, these tests go red and the change has to be
argued rather than merged. Widening the band is the conservative direction; narrowing it makes
crossing easier, which is indistinguishable from buying a result.

The other half is that the meter's guarantee is MEASURED here, not asserted. The false-crossing
rate is checked by Monte Carlo against its own nominal alpha, including on autocorrelated data,
and there is a test showing the naive (uninflated) sigma BREAKS the guarantee -- which is what
justifies the inflation being there at all.
"""
import datetime as dt
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import track_meter as TM                # noqa: E402


# ----------------------------------------------------------------- helpers
def _series(start, n_days, valquo_daily_pp, spy_daily_pp, skip=()):
    """A cumulative-since-inception series with a constant daily drift on each leg."""
    rows, d, cv, cs, i = [], start, 0.0, 0.0, 0
    while i < n_days:
        d += dt.timedelta(days=1)
        if not TM.is_trading_day(d):
            continue
        i += 1
        cv = (1 + cv / 100.0) * (1 + valquo_daily_pp / 100.0) * 100 - 100
        cs = (1 + cs / 100.0) * (1 + spy_daily_pp / 100.0) * 100 - 100
        if d.isoformat() in skip:
            continue
        rows.append({"date": d.isoformat(), "valquo": cv, "spy": cs})
    return rows


# ------------------------------------------------- the frozen pre-registration
def test_frozen_constants_are_exactly_what_the_contract_says():
    assert TM.CONTRACT_VERSION == "option-E-2026-08-09"
    assert TM.INCEPTION == dt.date(2026, 7, 30)
    assert TM.OPERATIONAL_GATE == dt.date(2027, 1, 30)
    assert TM.FIRST_RENDER == dt.date(2027, 1, 30)
    assert TM.VERDICT_DATE == dt.date(2031, 7, 30)
    assert TM.RHO == 3.0
    assert TM.ALPHA == 0.05
    assert TM.MARK_STALENESS_LIMIT_TD == 3
    assert TM.MAX_VOIDED_FRACTION == 0.10
    assert abs(TM.SIGMA_MONTHLY_PP - 3.9846917305386294) < 1e-12, TM.SIGMA_MONTHLY_PP
    assert abs(TM.COST_DRAG_PP_PER_MONTH - 0.14529) < 1e-12, TM.COST_DRAG_PP_PER_MONTH


def test_sigma_derivation_is_the_projects_own_measured_numbers():
    # 11.40pp/yr tracking error (benchmarks.spy) over sqrt(12), inflated by the AR(1) design
    # effect from R9's lag-1 +0.189. Recomputed here independently of the module's arithmetic.
    expect = (11.40 / math.sqrt(12.0)) * math.sqrt(1.189 / 0.811)
    assert abs(TM.SIGMA_MONTHLY_PP - expect) < 1e-9


def test_boundary_matches_the_closed_form():
    for n in (1, 6, 60):
        v = n + TM.RHO
        want = TM.SIGMA_MONTHLY_PP * math.sqrt(v * math.log(v / (TM.RHO * TM.ALPHA ** 2)))
        assert abs(TM.boundary(n) - want) < 1e-12


def test_published_detectable_edge_table_is_reproduced():
    # These six numbers are quoted in the contract and the handoff. If the construction moves,
    # the published table is wrong and this is where it must surface.
    want = {6: 63.7, 12: 42.5, 24: 29.6, 36: 24.3, 60: 19.0, 120: 13.8}
    for n, w in want.items():
        got = TM.detectable_edge_pp_per_year(n)
        assert abs(got - w) < 0.05, f"n={n}: {got:.2f} vs published {w}"


def test_the_boundary_widens_with_n_and_never_narrows():
    prev = 0.0
    for n in range(1, 200):
        b = TM.boundary(n)
        assert b > prev
        prev = b


# ------------------------------------------------- the guarantee, MEASURED
def _mc_cross_rate(sigma_used, ar1, sd_true, n_max, draws, seed):
    rnd = random.Random(seed)
    innov = sd_true * math.sqrt(1 - ar1 * ar1) if ar1 else sd_true
    hits = 0
    for _ in range(draws):
        s = prev = 0.0
        for n in range(1, n_max + 1):
            x = rnd.gauss(0.0, innov)
            if ar1:
                x += ar1 * prev
            prev = x
            s += x
            if abs(s) >= TM.boundary(n, sigma=sigma_used):
                hits += 1
                break
    return hits / draws


def test_false_crossing_rate_is_within_alpha_on_autocorrelated_data():
    sd = 11.40 / math.sqrt(12.0)
    rate = _mc_cross_rate(TM.SIGMA_MONTHLY_PP, 0.189, sd, 120, 4000, 11)
    assert rate <= TM.ALPHA, f"false-crossing {rate:.4f} exceeds nominal {TM.ALPHA}"


def test_the_autocorrelation_inflation_is_load_bearing():
    """Without it the bound breaks its own guarantee -- this is why sigma is inflated."""
    sd = 11.40 / math.sqrt(12.0)
    naive = _mc_cross_rate(sd, 0.189, sd, 120, 4000, 12)          # uninflated sigma
    infl = _mc_cross_rate(TM.SIGMA_MONTHLY_PP, 0.189, sd, 120, 4000, 12)
    assert naive > TM.ALPHA, f"naive rate {naive:.4f} was expected to breach alpha"
    assert infl < naive


# ------------------------------------------------- anti-gaming invariants
def test_meter_has_no_sign_branch():
    """Flipping the sign of the whole series must not change WHETHER it renders.

    The contract makes suppressing an unfavourable render a whole-run void. The strongest
    guard is that the code cannot express the suppression: the render decision reads the date
    and the integrity of the series, never the result.
    """
    up = _series(TM.INCEPTION, 130, 0.30, 0.02)
    dn = _series(TM.INCEPTION, 130, 0.02, 0.30)
    a = TM.meter(up, as_of=dt.date(2027, 1, 30))
    b = TM.meter(dn, as_of=dt.date(2027, 1, 30))
    assert a["rendered"] == b["rendered"] is True
    assert a["n_months"] == b["n_months"]
    assert a["boundary_sum_pp"] == b["boundary_sum_pp"]
    assert a["sum_excess_pp"] > 0 > b["sum_excess_pp"]


def test_render_is_blocked_before_the_contracted_first_render_date():
    s = _series(TM.INCEPTION, 130, 0.05, 0.01)
    day_before = TM.meter(s, as_of=TM.FIRST_RENDER - dt.timedelta(days=1))
    on_the_day = TM.meter(s, as_of=TM.FIRST_RENDER)
    assert day_before["rendered"] is False
    assert "first-render" in day_before["render_blocked_reason"]
    assert on_the_day["rendered"] is True
    # It is still COMPUTED before the render date -- withheld from display, not unmeasured.
    assert day_before["computable"] is True and day_before["n_months"] >= 1


def test_cost_drag_is_a_constant_shift_against_the_strategy():
    s = _series(TM.INCEPTION, 130, 0.05, 0.05)      # identical legs -> zero gross excess
    mx = TM.monthly_excess(s, as_of=dt.date(2027, 1, 30))
    assert mx["n_months"] >= 5
    for mo in mx["months"]:
        assert abs(mo["excess_gross_pp"]) < 1e-9
        assert abs(mo["excess_pp"] + TM.COST_DRAG_PP_PER_MONTH) < 1e-9


def test_sigma_breach_fires_when_realised_volatility_exceeds_the_plug_in():
    calm = _series(TM.INCEPTION, 130, 0.05, 0.05)
    assert TM.meter(calm, as_of=dt.date(2027, 1, 30))["sigma_breach"] is False
    # A series whose monthly excess swings far wider than sigma must raise the flag.
    rows, d, cv, cs, i, sign = [], TM.INCEPTION, 0.0, 0.0, 0, 1
    while i < 130:
        d += dt.timedelta(days=1)
        if not TM.is_trading_day(d):
            continue
        i += 1
        cv = (1 + cv / 100.0) * (1 + (0.5 * sign) / 100.0) * 100 - 100
        cs = (1 + cs / 100.0) * 100 - 100
        if d.day > 25:
            sign = -sign
        rows.append({"date": d.isoformat(), "valquo": cv, "spy": cs})
    assert TM.meter(rows, as_of=dt.date(2027, 1, 30))["sigma_breach"] is True


# ------------------------------------------------- series construction
def test_the_one_day_stub_month_is_merged_forward_not_counted():
    """Inception is 2026-07-30, so July holds a single trading day of exposure."""
    s = _series(TM.INCEPTION, 40, 0.05, 0.01)
    mx = TM.monthly_excess(s, as_of=dt.date(2026, 9, 30))
    labels = [m["month"] for m in mx["months"]]
    assert "2026-07" not in labels, labels
    assert labels[0] == "2026-08"


def test_an_interior_missing_day_does_not_corrupt_a_monthly_return():
    """Cumulative levels mean a month needs only its two endpoints -- pinned, not assumed."""
    full = _series(TM.INCEPTION, 130, 0.05, 0.01)
    holed = _series(TM.INCEPTION, 130, 0.05, 0.01,
                    skip=("2026-09-10", "2026-09-11", "2026-09-14"))
    a = TM.monthly_excess(full, as_of=dt.date(2027, 1, 30))
    b = TM.monthly_excess(holed, as_of=dt.date(2027, 1, 30))
    assert b["n_voided"] == 0
    assert [m["month"] for m in a["months"]] == [m["month"] for m in b["months"]]
    for x, y in zip(a["months"], b["months"]):
        assert abs(x["excess_pp"] - y["excess_pp"]) < 1e-9


def test_a_stale_month_end_mark_voids_that_month():
    s = _series(TM.INCEPTION, 130, 0.05, 0.01,
                skip=tuple(f"2026-09-{d:02d}" for d in range(20, 31)))
    mx = TM.monthly_excess(s, as_of=dt.date(2027, 1, 30))
    voided = [v["month"] for v in mx["voided"]]
    assert "2026-09" in voided, mx["voided"]
    assert all("stale" in v["reason"] or "no mark" in v["reason"] for v in mx["voided"])


def test_too_many_voided_months_blocks_the_render():
    s = _series(TM.INCEPTION, 130, 0.05, 0.01)
    mx = TM.monthly_excess(s, as_of=dt.date(2027, 1, 30))
    n = mx["n_months"]
    # Drop the back half of every month so most marks are unusably stale.
    skip = []
    for mo in mx["months"][1:]:
        y, m = (int(x) for x in mo["month"].split("-"))
        skip += [f"{y:04d}-{m:02d}-{d:02d}" for d in range(15, 32)]
    holed = _series(TM.INCEPTION, 130, 0.05, 0.01, skip=tuple(skip))
    out = TM.meter(holed, as_of=dt.date(2027, 1, 30))
    assert out["voided_fraction"] > TM.MAX_VOIDED_FRACTION
    assert out["rendered"] is False
    assert "voided" in out["render_blocked_reason"]
    assert n >= 1


# ------------------------------------------------- the gap report
def test_gap_report_does_not_demand_a_row_on_the_inception_day():
    """Inception is day 0. Demanding a row there reports a gap that can never be closed."""
    s = _series(TM.INCEPTION, 5, 0.05, 0.01)
    g = TM.gap_report(s, as_of=dt.date(2026, 8, 6))
    assert TM.INCEPTION.isoformat() not in g["missing_dates"]
    assert g["complete"] is True, g


def test_gap_report_names_the_missing_dates_not_just_a_count():
    s = _series(TM.INCEPTION, 6, 0.05, 0.01, skip=("2026-08-04",))
    g = TM.gap_report(s, as_of=dt.date(2026, 8, 7))
    assert g["missing_dates"] == ["2026-08-04"], g
    assert g["complete"] is False and g["missing_count"] == 1


def test_gap_report_flags_a_row_on_a_non_trading_day():
    s = _series(TM.INCEPTION, 5, 0.05, 0.01)
    s.append({"date": "2026-08-08", "valquo": 1.0, "spy": 1.0})     # a Saturday
    g = TM.gap_report(s, as_of=dt.date(2026, 8, 7))
    assert "2026-08-08" in g["unexpected_dates"]
    assert g["complete"] is False


def test_the_live_gap_as_recorded_is_reproduced():
    """The real state on 2026-08-09: rows for day 1 and day 5, four trading days missing."""
    live = [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
            {"date": "2026-08-06", "valquo": 0.7760, "spy": 3.6228}]
    g = TM.gap_report(live, as_of=dt.date(2026, 8, 9))
    assert g["expected_trading_days"] == 6 and g["present"] == 2
    assert g["missing_dates"] == ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-07"]
    # And zero complete months, which is why the pre-registration is blind.
    assert TM.monthly_excess(live, as_of=dt.date(2026, 8, 9))["n_months"] == 0


def test_empty_series_is_a_normal_state_not_a_crash():
    out = TM.meter([], as_of=dt.date(2027, 1, 30))
    assert out["computable"] is False and out["rendered"] is False
    assert out["n_months"] == 0


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
    print(f"\n{passed}/{len(tests)} track-meter tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
