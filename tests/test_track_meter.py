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
    # Amendment 1 (2026-08-09) voided run #1 and opened vintage 2. The CLOCK moved; the
    # STATISTICS did not -- sigma, rho, alpha and the cost drag are unchanged, and the
    # assertions below pin that separation.
    assert TM.CONTRACT_VERSION == "option-E-2026-08-09+amendment-1"
    # THE CLOCK ATTACHES TO THE CURRENT VINTAGE and is DERIVED, so a vintage event moves it
    # mechanically rather than by anyone remembering to. Asserted as a relationship, which is
    # the property the contract actually states; the literal dates moved when the theme
    # restoration opened vintage 3 (gate 2027-02-10 -> 2027-02-11).
    assert TM.INCEPTION == TM.current_vintage()["opened"]
    assert TM.OPERATIONAL_GATE == TM._months_after(TM.INCEPTION, TM.GATE_MONTHS)
    assert TM.FIRST_RENDER == TM.OPERATIONAL_GATE
    assert TM.VERDICT_DATE == TM._months_after(TM.INCEPTION, TM.VERDICT_MONTHS)
    assert TM.RHO == 3.0
    assert TM.ALPHA == 0.05
    assert TM.MARK_STALENESS_LIMIT_TD == 3
    assert TM.MAX_VOIDED_FRACTION == 0.10
    assert abs(TM.SIGMA_MONTHLY_PP - 3.9846917305386294) < 1e-12, TM.SIGMA_MONTHLY_PP
    assert abs(TM.COST_DRAG_PP_PER_MONTH - 0.14529) < 1e-12, TM.COST_DRAG_PP_PER_MONTH


# ------------------------------------------------- the vintage rule (Amendment 1)
def test_exactly_one_vintage_is_open_and_it_is_the_latest():
    """The INVARIANT, not the number. Pinning "it is vintage 2" made a legitimate vintage event
    fail a test that exists to catch two vintages being open at once."""
    v = TM.current_vintage()
    assert sum(1 for x in TM.VINTAGES if x["status"] == "OPEN") == 1
    assert v["vintage"] == max(x["vintage"] for x in TM.VINTAGES)
    assert v["closed"] is None
    # every earlier vintage is resolved, never left dangling
    for x in TM.VINTAGES:
        if x["vintage"] != v["vintage"]:
            assert x["status"] in ("VOID", "CLOSED") and x["closed"] is not None, x


def test_run_1_is_recorded_as_void_and_is_not_deleted():
    """§5a keeps the voided window. Deleting it would make the void unauditable."""
    v1 = [x for x in TM.VINTAGES if x["vintage"] == 1][0]
    assert v1["status"] == "VOID"
    assert v1["opened"] == dt.date(2026, 7, 30) and v1["closed"] == dt.date(2026, 8, 9)
    assert "no longer exists" in v1["reason"]


def test_the_amendment_moved_the_clock_and_not_the_statistics():
    """The whole defensibility of Amendment 1 rests on this separation."""
    assert abs(TM.SIGMA_MONTHLY_PP - 3.9846917305386294) < 1e-12
    assert TM.RHO == 3.0 and TM.ALPHA == 0.05
    assert abs(TM.COST_DRAG_PP_PER_MONTH - 0.14529) < 1e-12
    # And the horizons are derived from the vintage, not hand-entered.
    assert TM.OPERATIONAL_GATE == TM._months_after(TM.INCEPTION, TM.GATE_MONTHS)
    assert TM.VERDICT_DATE == TM._months_after(TM.INCEPTION, TM.VERDICT_MONTHS)


def test_the_voided_vintage_does_not_feed_the_meter():
    """Run #1's rows are inside the file and must contribute nothing to the live test."""
    live = [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
            {"date": "2026-08-06", "valquo": 0.7760, "spy": 3.6228}]
    m = TM.meter(live, as_of=dt.date(2026, 9, 30))
    assert m["vintage"] == TM.current_vintage()["vintage"]
    assert m["n_months"] == 0, "a voided vintage's rows reached the meter"
    assert m["gaps"]["inception"] == TM.INCEPTION.isoformat()


def test_a_later_vintage_is_baselined_at_its_opening_level_not_at_zero():
    """The recorded series is cumulative since run #1, so vintage 2 must not inherit its drift."""
    rows = _series(dt.date(2026, 7, 30), 130, 0.10, 0.02)      # cumulative from run #1
    lvl = {r["date"]: r for r in rows}
    at_open = [r for r in rows if r["date"] <= TM.INCEPTION.isoformat()][-1]
    assert at_open["valquo"] > 0.5, at_open   # run #1 drift is genuinely non-zero

    mx = TM.monthly_excess(rows, as_of=dt.date(2026, 10, 31))
    first = mx["months"][0]
    assert first["month"] == "2026-09"        # August is a stub and merges forward
    # The first period runs from INCEPTION to end-September, so its return must be exactly the
    # ratio of those two recorded levels. Baselining at zero instead would fold run #1's drift
    # in and give a LARGER number; this pins the exact value rather than a band.
    end = lvl[first["mark_date"]]
    want_v = (1 + end["valquo"] / 100) / (1 + at_open["valquo"] / 100) - 1
    want_s = (1 + end["spy"] / 100) / (1 + at_open["spy"] / 100) - 1
    assert abs(first["valquo_ret_pp"] - want_v * 100) < 1e-9, (first, want_v * 100)
    assert abs(first["excess_gross_pp"] - (want_v - want_s) * 100) < 1e-9
    # And it is strictly smaller than the zero-baselined version, which is the actual defect.
    assert first["valquo_ret_pp"] < end["valquo"], "vintage 2 inherited run #1's drift"


def test_as_operated_keeps_the_voided_vintage_and_is_not_a_verdict():
    live = [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
            {"date": "2026-08-06", "valquo": 0.7760, "spy": 3.6228}]
    ao = TM.as_operated(live, as_of=dt.date(2026, 8, 9))
    assert ao["label"] == "the system as operated"
    # The disclaimer must name WHY it is not a verdict -- that it crosses models -- not merely
    # exist as a key. A key nobody reads is not a safeguard.
    dis = ao["not_a_verdict"].lower()
    assert "model" in dis and "vintage" in dis, ao["not_a_verdict"]
    leg1 = [l for l in ao["legs"] if l["vintage"] == 1][0]
    # The REAL experienced figures, not zero -- a six-day window holds no complete month, and
    # reporting 0.0% for a window that moved -2.85pp would be the flattering kind of wrong.
    assert abs(leg1["valquo_ret_pp"] - 0.7760) < 1e-9
    assert abs(leg1["spy_ret_pp"] - 3.6228) < 1e-9
    assert abs(leg1["excess_pp"] - (-2.8468)) < 1e-4


# ------------------------------------------------- the running-path block (session 15)
def test_detail_is_not_vacuously_green_before_the_vintage_starts():
    """A bound that cannot fail yet must say so rather than report a pass."""
    d = TM.detail(series=[], as_of=dt.date(2026, 8, 9))
    assert d["available"] is True
    assert d["started"] is False
    assert d["recording_ok"] is None, "reported a pass before any trading day was due"
    assert "not started" in d["recording_note"]


def test_detail_reports_a_missing_day_the_day_after_it_was_due():
    """The one-day test for whether the daily writer is actually running.

    Inception is day 0, so the FIRST row due is the next trading day and the earliest date on
    which its absence is detectable is the day after that. Derived from the open vintage rather
    than hard-coded, so a vintage event moves the test with the clock instead of breaking it.
    """
    day0 = TM.INCEPTION
    due = day0 + dt.timedelta(days=1)
    while due.weekday() >= 5:
        due += dt.timedelta(days=1)
    detect = due + dt.timedelta(days=1)
    while detect.weekday() >= 5:
        detect += dt.timedelta(days=1)
    d = TM.detail(series=[], as_of=detect)
    assert d["started"] is True and d["recording_ok"] is False
    assert "MISSING" in d["recording_note"]
    assert due.isoformat() in d["meter"]["gaps"]["missing_dates"]
    assert day0.isoformat() not in d["meter"]["gaps"]["missing_dates"], "demanded a row on day 0"


def test_as_operated_is_reconciled_against_the_one_authority():
    """PT-OUTBOUND: the authority for any vs-SPY claim is `index_track.vs_spy_claim`.

    This module legitimately computes its own excess -- the meter's statistic is monthly,
    per-vintage and net of a modelled cost drag, so reading it off the claim would be wrong.
    But `as_operated` IS the same kind of object as the claim, so a disagreement between the
    two must be reported rather than discovered. On 2026-08-05 two derivations that nobody
    reconciled is exactly how a wrong number shipped.
    """
    assert TM._reconcile({"cumulative_excess_pp": -2.8468},
                         {"available": True, "excess_pp": -2.8468}) is True
    assert TM._reconcile({"cumulative_excess_pp": -2.8468},
                         {"available": True, "excess_pp": +0.18}) is False
    # No authority is a normal state on a fresh deploy -- and must NOT read as agreement.
    assert TM._reconcile({"cumulative_excess_pp": -2.8468}, {"available": False}) is None
    assert TM._reconcile({"cumulative_excess_pp": 0.0},
                         {"available": True, "excess_pp": None}) is None


def test_detail_names_the_bound_source_and_never_raises():
    d = TM.detail(series=[], as_of=dt.date(2026, 8, 12))
    assert "Valquo Index" in d["source"] and d["not_the_sandbox_engine"] is True
    assert d["vintage"] == TM.current_vintage()["vintage"]
    # A broken series is a normal state, not a 500 on an unrelated page.
    bad = TM.detail(series=[{"date": "not-a-date", "valquo": None, "spy": None}],
                    as_of=dt.date(2026, 8, 11))
    assert bad["available"] is True


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
    a = TM.meter(up, as_of=TM.FIRST_RENDER)
    b = TM.meter(dn, as_of=TM.FIRST_RENDER)
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
    mx = TM.monthly_excess(s, as_of=TM.FIRST_RENDER)
    assert mx["n_months"] >= 5
    for mo in mx["months"]:
        assert abs(mo["excess_gross_pp"]) < 1e-9
        assert abs(mo["excess_pp"] + TM.COST_DRAG_PP_PER_MONTH) < 1e-9


def test_sigma_breach_fires_when_realised_volatility_exceeds_the_plug_in():
    calm = _series(TM.INCEPTION, 130, 0.05, 0.05)
    assert TM.meter(calm, as_of=TM.FIRST_RENDER)["sigma_breach"] is False
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
    assert TM.meter(rows, as_of=TM.FIRST_RENDER)["sigma_breach"] is True


# ------------------------------------------------- series construction
def test_the_one_day_stub_month_is_merged_forward_not_counted():
    """Inception is 2026-07-30, so July holds a single trading day of exposure."""
    s = _series(TM.INCEPTION, 40, 0.05, 0.01)
    mx = TM.monthly_excess(s, as_of=dt.date(2026, 10, 31))
    labels = [m["month"] for m in mx["months"]]
    assert "2026-08" not in labels, labels          # inception 2026-08-10 -> August is a stub
    assert labels[0] == "2026-09"


def test_an_interior_missing_day_does_not_corrupt_a_monthly_return():
    """Cumulative levels mean a month needs only its two endpoints -- pinned, not assumed."""
    full = _series(TM.INCEPTION, 130, 0.05, 0.01)
    holed = _series(TM.INCEPTION, 130, 0.05, 0.01,
                    skip=("2026-09-10", "2026-09-11", "2026-09-14"))
    a = TM.monthly_excess(full, as_of=TM.FIRST_RENDER)
    b = TM.monthly_excess(holed, as_of=TM.FIRST_RENDER)
    assert b["n_voided"] == 0
    assert [m["month"] for m in a["months"]] == [m["month"] for m in b["months"]]
    for x, y in zip(a["months"], b["months"]):
        assert abs(x["excess_pp"] - y["excess_pp"]) < 1e-9


def test_a_stale_month_end_mark_voids_that_month():
    s = _series(TM.INCEPTION, 130, 0.05, 0.01,
                skip=tuple(f"2026-09-{d:02d}" for d in range(20, 31)))
    mx = TM.monthly_excess(s, as_of=TM.FIRST_RENDER)
    voided = [v["month"] for v in mx["voided"]]
    assert "2026-09" in voided, mx["voided"]
    assert all("stale" in v["reason"] or "no mark" in v["reason"] for v in mx["voided"])


def test_too_many_voided_months_blocks_the_render():
    s = _series(TM.INCEPTION, 130, 0.05, 0.01)
    mx = TM.monthly_excess(s, as_of=TM.FIRST_RENDER)
    n = mx["n_months"]
    # Drop the back half of every month so most marks are unusably stale.
    skip = []
    for mo in mx["months"][1:]:
        y, m = (int(x) for x in mo["month"].split("-"))
        skip += [f"{y:04d}-{m:02d}-{d:02d}" for d in range(15, 32)]
    holed = _series(TM.INCEPTION, 130, 0.05, 0.01, skip=tuple(skip))
    out = TM.meter(holed, as_of=TM.FIRST_RENDER)
    assert out["voided_fraction"] > TM.MAX_VOIDED_FRACTION
    assert out["rendered"] is False
    assert "voided" in out["render_blocked_reason"]
    assert n >= 1


# ------------------------------------------------- the gap report
def test_gap_report_does_not_demand_a_row_on_the_inception_day():
    """Inception is day 0. Demanding a row there reports a gap that can never be closed."""
    s = _series(TM.INCEPTION, 5, 0.05, 0.01)
    g = TM.gap_report(s, as_of=dt.date(2026, 8, 17))
    assert TM.INCEPTION.isoformat() not in g["missing_dates"]
    assert g["complete"] is True, g


def test_gap_report_names_the_missing_dates_not_just_a_count():
    s = _series(TM.INCEPTION, 6, 0.05, 0.01, skip=("2026-08-13",))
    g = TM.gap_report(s, as_of=dt.date(2026, 8, 18))
    assert g["missing_dates"] == ["2026-08-13"], g
    assert g["complete"] is False and g["missing_count"] == 1


def test_gap_report_flags_a_row_on_a_non_trading_day():
    s = _series(TM.INCEPTION, 5, 0.05, 0.01)
    s.append({"date": "2026-08-15", "valquo": 1.0, "spy": 1.0})     # a Saturday
    g = TM.gap_report(s, as_of=dt.date(2026, 8, 17))
    assert "2026-08-15" in g["unexpected_dates"]
    assert g["complete"] is False


def test_the_voided_run_1_gap_as_recorded_is_still_reproduced():
    """Run #1's real state on 2026-08-09, checked against ITS OWN inception.

    Amendment 1 voided this window but kept it. The historical fact is pinned here so the void
    stays auditable: 2 of 6 due rows, four named missing days, and zero complete months -- the
    last being why the meter's parameters could not have been tuned to it.
    """
    live = [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
            {"date": "2026-08-06", "valquo": 0.7760, "spy": 3.6228}]
    v1 = dt.date(2026, 7, 30)
    g = TM.gap_report(live, as_of=dt.date(2026, 8, 9), inception=v1)
    assert g["expected_trading_days"] == 6 and g["present"] == 2
    assert g["missing_dates"] == ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-07"]
    assert TM.monthly_excess(live, as_of=dt.date(2026, 8, 9), inception=v1)["n_months"] == 0


def test_empty_series_is_a_normal_state_not_a_crash():
    out = TM.meter([], as_of=TM.FIRST_RENDER)
    assert out["computable"] is False and out["rendered"] is False
    assert out["n_months"] == 0


# ---------------------------------- session 28: the guard must not demand an unwritable row
def test_a_perfect_writer_is_never_reported_as_missing_a_row():
    """THE DEFECT THIS PINS, measured 2026-08-12.

    A trading day's row is written after that day's close. `gap_report` counted the current day
    as due from midnight, so a writer holding every row it could possibly have written still
    read `recording_ok: false` every trading-day morning, naming the current day. That is a red
    light nobody can clear, on public surfaces (LA8), and it is the exact mirror of the vacuous
    PASS session 15 caught in this same function.
    """
    inc = dt.date(2026, 7, 1)
    bad = []
    for k in range(30):
        day = dt.date(2026, 8, 12) - dt.timedelta(days=k)
        if not TM.is_trading_day(day):
            continue
        # every trading day since inception EXCEPT the day itself, which is not writable yet
        rows = [{"date": d.isoformat(), "valquo": 1.0, "spy": 1.0}
                for d in TM._trading_days(inc, day) if inc < d < day]
        g = TM.gap_report(rows, as_of=day, inception=inc)
        if not g["complete"]:
            bad.append((day.isoformat(), g["missing_dates"]))
    assert not bad, f"a perfect writer was reported incomplete on {len(bad)} mornings: {bad[:3]}"


def test_the_days_own_row_is_demanded_once_the_next_trading_day_begins():
    """The other half: the fix must not stop the guard detecting a real miss, only delay it."""
    inc = dt.date(2026, 7, 1)
    due = dt.date(2026, 8, 11)                      # a Tuesday, genuinely owed
    detect = dt.date(2026, 8, 12)                   # the next trading day
    rows = [{"date": d.isoformat(), "valquo": 1.0, "spy": 1.0}
            for d in TM._trading_days(inc, detect) if inc < d < detect and d != due]
    on_the_day = TM.gap_report(rows, as_of=due, inception=inc)
    assert due.isoformat() not in on_the_day["missing_dates"], "demanded a row on the day itself"
    after = TM.gap_report(rows, as_of=detect, inception=inc)
    assert due.isoformat() in after["missing_dates"], "a real miss stopped being detected"
    assert after["complete"] is False


def test_a_vintage_event_does_not_erase_a_dated_miss():
    """Vintage 1 owed six rows and got two. Those four dates are invisible to `recording_ok`.

    `recording_ok` is scoped to the open vintage by contract, so the misses legitimately leave
    that field -- but they must not leave the RECORD, or "logged, not voided" cannot be honoured.
    """
    live = [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
            {"date": "2026-08-06", "valquo": 0.776, "spy": 3.6228}]
    hist = TM.recording_history(live, as_of=dt.date(2026, 8, 12))
    v1 = [h for h in hist if h["vintage"] == 1][0]
    assert v1["expected_trading_days"] == 6 and v1["present"] == 2, v1
    assert v1["missing_dates"] == ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-07"], v1

    # ...and none of them is reachable from the open vintage's own gap report, which is the
    # whole reason this record has to exist separately.
    assert TM.gap_report(live)["missing_dates"] == []

    # Vintage 2 owed NOTHING: it closed 2026-08-11, and that day's row does not fall due until
    # 2026-08-12. Pinned because the first draft of this test asserted the opposite, having
    # computed the miss under the off-by-one the same change repairs.
    v2 = [h for h in hist if h["vintage"] == 2][0]
    assert v2["expected_trading_days"] == 0 and v2["complete"] is True, v2
    assert [h for h in hist if h["status"] == "OPEN"], hist


def test_detail_says_which_row_is_awaited_and_when_it_becomes_assessable():
    """Without these, a morning `None`/`false` is indistinguishable from a writer failure.

    On 2026-08-12 the open vintage (3) began the previous day, so the row awaited is 2026-08-12's
    and it is not demanded until 2026-08-13 -- which is the whole reason this session could not
    close PT-WRITER either way.
    """
    d = TM.detail(series=[], as_of=dt.date(2026, 8, 12))
    assert d["recording_ok"] is None, "claimed a verdict before any row was due"
    assert d["row_awaited"] == "2026-08-12", d.get("row_awaited")
    assert d["assessable_from"] == "2026-08-13", d.get("assessable_from")
    assert any(h["vintage"] == 2 for h in d["per_vintage_recording"])


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
