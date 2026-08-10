#!/usr/bin/env python3
"""Tests for the V2 live theme-health meter (`scripts/theme_health.py`).

THE POINT OF THIS FILE. The live record holds ZERO closed 63-day windows, so the live data
cannot exercise the estimator at all -- it can only exercise the refusal. That is exactly the
situation in which a project ships a meter that has never computed anything and finds out in
nine months that it computes the wrong thing. So the estimator is proved here instead, against
panels with a KNOWN planted IC, and the refusal is proved against the real record.

Run:  python tests/test_theme_health.py
"""
from __future__ import annotations

import datetime as _dt
import gzip
import json
import math
import os
import random
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import theme_health as TH                                    # noqa: E402
from valuation.edge.fundamental_panel import _spearman                    # noqa: E402
from valuation.screener import settings as S                              # noqa: E402
from valuation.screener.market_session import is_trading_day              # noqa: E402

FAILURES = []


def check(name, fn):
    try:
        fn()
        print("  PASS  %s" % name)
    except AssertionError as e:
        FAILURES.append((name, str(e)))
        print("  FAIL  %s\n        %s" % (name, e))
    except Exception as e:                                                # pragma: no cover
        FAILURES.append((name, "%s: %s" % (type(e).__name__, e)))
        print("  ERROR %s\n        %s: %s" % (name, type(e).__name__, e))


# ---------------------------------------------------------------------------
# Panel builders. Daily scans, because that is what the pipeline actually does
# (the hot list runs after every close) and it is what makes a mark exist at
# exactly d + 63 trading days.
# ---------------------------------------------------------------------------

def trading_days_from(start: _dt.date, n: int):
    out, d = [], start
    while len(out) < n:
        if is_trading_day(d):
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def planted_panel(months=9, n_names=60, planted=0.0, theme="quality", seed=7,
                  provider="free+broker"):
    """A daily-scan record in which `theme` has a KNOWN forward relationship.

    THE PRICE PATH IS DRAWN FIRST AND THE SCORE IS BUILT FROM IT, not the other way round.
    The obvious construction -- draw a score, then write the price that satisfies it -- looks
    right and is wrong here, because with 63-day windows starting on every trading day one
    date's ENTRY price is an earlier date's MARK price. Each realised return then carries an
    independent second term and the recovered IC is attenuated by 1/sqrt(2). That version of
    this builder produced 0.357 against an expected 0.483, and the arithmetic of the mistake
    predicts 0.341 -- i.e. it was the harness, and it would have been read as the estimator.

    So: a genuine multiplicative random walk per name, then for each entry date the realised
    63-trading-day return is converted to its normal score across that date's cross-section
    and the theme is set to `planted * z(ret) + sqrt(1 - planted^2) * noise`. That pair is
    bivariate normal with correlation `planted`, and because the normal score is monotone in
    the return, Spearman is exactly (6/pi)*asin(planted/2).

    Every other theme is independent noise, which makes this a control as well as a test:
    nine themes must come back at ~0 in the same run that one comes back at the planted value.
    """
    from statistics import NormalDist
    rng = random.Random(seed)
    nd = NormalDist()
    days = trading_days_from(_dt.date(2026, 1, 5), 21 * (months + 4))
    tickers = ["N%03d" % i for i in range(n_names)]
    idx = {d: i for i, d in enumerate(days)}

    price = {}
    for t in tickers:
        p = 100.0
        for d in days:
            price[(t, d)] = p
            p *= math.exp(rng.gauss(0.0, 0.02))

    rows = []
    for d in days:
        j = idx[d] + TH.HORIZON_TD
        zret = {}
        if j < len(days):
            md = days[j]
            rets = sorted(((price[(t, md)] / price[(t, d)] - 1.0), t) for t in tickers)
            n = len(rets)
            for rank, (_r, t) in enumerate(rets):
                zret[t] = nd.inv_cdf((rank + 0.5) / n)
        for t in tickers:
            factors = {th: rng.gauss(0, 1) for th in S.FACTORS_ALL}
            if t in zret:
                factors[theme] = (planted * zret[t]
                                  + math.sqrt(max(1.0 - planted * planted, 0.0)) * rng.gauss(0, 1))
            rows.append({"date": d, "ticker": t, "price": price[(t, d)],
                         "factors": factors, "provider": provider, "source": "test"})
    return rows, days


def thin_panel(dates=3, n_names=50):
    days = trading_days_from(_dt.date(2026, 8, 1), dates)
    rows = []
    for d in days:
        for i in range(n_names):
            rows.append({"date": d, "ticker": "T%02d" % i, "price": 100.0 + i,
                         "factors": {t: 0.1 * i for t in S.FACTORS_ALL},
                         "provider": "free+broker", "source": "test"})
    return rows


# ---------------------------------------------------------------------------
# 1. The frozen parameters ARE the pre-registration
# ---------------------------------------------------------------------------

def test_every_frozen_parameter_matches_the_pre_registration():
    p = TH.frozen_parameters()
    assert p["horizon_td"] == 63, p["horizon_td"]
    assert p["cadence"] == "monthly"
    assert p["overlap_m"] == 3
    assert abs(p["overlap_design_effect"] - 3.0) < 1e-12, p["overlap_design_effect"]
    assert abs(p["sigma"] - math.sqrt(3.0)) < 1e-12, p["sigma"]
    assert p["rho"] == 3.0
    assert abs(p["alpha_family"] - 0.05) < 1e-12
    assert p["n_themes"] == 10, p["n_themes"]
    assert abs(p["alpha_theme"] - 0.005) < 1e-12, p["alpha_theme"]
    assert p["min_names_per_date"] == 20
    assert p["min_months"] == 6
    assert abs(p["min_theme_coverage"] - 0.30) < 1e-12
    assert abs(p["max_attrition"] - 0.20) < 1e-12
    assert abs(p["max_voided_fraction"] - 0.10) < 1e-12
    assert p["price_staleness_td"] == 3
    assert abs(p["ref_min_ic"] - 0.01) < 1e-12
    assert p["prereg"] == "PREREG_v2_theme_health.md"


def test_sigma_is_the_overlap_design_effect_and_the_derivation_is_not_decoration():
    # 1 + 2*sum_{j=1..m-1}(1 - j/m) at m=3  ->  1 + 2*(2/3 + 1/3) = 3
    manual = 1.0 + 2.0 * ((1 - 1 / 3.0) + (1 - 2 / 3.0))
    assert abs(TH.OVERLAP_DESIGN_EFFECT - manual) < 1e-12
    assert abs(TH.SIGMA - math.sqrt(manual)) < 1e-12
    # A wider sigma must give a wider band -- i.e. lowering sigma buys crossings, which is
    # why the pre-registration forbids it in one direction only.
    assert TH.boundary(10, sigma=TH.SIGMA, rho=TH.RHO, alpha=TH.ALPHA_THEME) > \
        TH.boundary(10, sigma=1.0, rho=TH.RHO, alpha=TH.ALPHA_THEME)


def test_the_family_wise_alpha_is_stricter_than_a_per_theme_one():
    """X7 measured that 8 themes at a per-theme bar lets 39% of noise draws clear it."""
    assert TH.ALPHA_THEME < TH.ALPHA_FAMILY
    assert TH.boundary(12, sigma=TH.SIGMA, rho=TH.RHO, alpha=TH.ALPHA_THEME) > \
        TH.boundary(12, sigma=TH.SIGMA, rho=TH.RHO, alpha=TH.ALPHA_FAMILY)


def test_the_ic_is_the_panels_own_spearman_and_not_a_reimplementation():
    rows = thin_panel(dates=1, n_names=40)
    d = rows[0]["date"]
    fwd = {r["ticker"]: (hash(r["ticker"]) % 97) / 100.0 for r in rows}
    got = TH.per_date_ic(rows, d, fwd)["quality"]["ic"]
    xs = [r["factors"]["quality"] for r in rows]
    ys = [fwd[r["ticker"]] for r in rows]
    assert abs(got - float(_spearman(xs, ys))) < 1e-15, (got, _spearman(xs, ys))


# ---------------------------------------------------------------------------
# 2. THE CONTROL: a planted IC is recovered, and the nine untouched themes are not
# ---------------------------------------------------------------------------

def test_a_planted_ic_is_recovered_and_the_other_nine_themes_stay_near_zero():
    rows, days = planted_panel(months=9, planted=0.5, theme="quality", seed=11)
    res = TH.analyse(rows, as_of=days[-1])
    q = res["themes"]["quality"]
    assert q["quotable"], q["blocked_by"]
    # Spearman of a bivariate normal with Pearson rho is (6/pi)*asin(rho/2) = 0.4826 at 0.5.
    expected = (6.0 / math.pi) * math.asin(0.5 / 2.0)
    assert abs(q["median_ic"] - expected) < 0.08, (q["median_ic"], expected)
    others = [t for t in S.FACTORS_ALL if t != "quality" and res["themes"][t]["quotable"]]
    assert others, "the control needs the other themes measured in the same run"
    for t in others:
        assert abs(res["themes"][t]["median_ic"]) < 0.15, (t, res["themes"][t]["median_ic"])


def test_a_zero_planted_ic_comes_back_at_zero():
    rows, days = planted_panel(months=9, planted=0.0, seed=3)
    res = TH.analyse(rows, as_of=days[-1])
    for t in S.FACTORS_ALL:
        v = res["themes"][t]
        if v["quotable"]:
            assert abs(v["median_ic"]) < 0.15, (t, v["median_ic"])


def test_a_strong_planted_edge_crosses_up_and_is_labelled_confirmed_live():
    rows, days = planted_panel(months=14, planted=0.5, theme="quality", seed=5)
    res = TH.analyse(rows, as_of=days[-1])
    q = res["themes"]["quality"]
    assert q["quotable"], q["blocked_by"]
    assert q["running_sum"] > q["boundary"], (q["running_sum"], q["boundary"])
    assert q["crossed"] == "up", q["crossed"]
    # quality's backtest median IC is +0.0356, i.e. reference_sign +1
    assert q["reference_sign"] == 1, q["reference_sign"]
    assert q["verdict"] == "CONFIRMED-LIVE", q["verdict"]


def test_a_planted_edge_with_the_wrong_sign_is_labelled_degraded():
    rows, days = planted_panel(months=14, planted=-0.5, theme="quality", seed=5)
    res = TH.analyse(rows, as_of=days[-1])
    q = res["themes"]["quality"]
    assert q["quotable"], q["blocked_by"]
    assert q["crossed"] == "down", q["crossed"]
    assert q["verdict"] == "DEGRADED", q["verdict"]


def test_pure_noise_does_not_cross():
    """The false-positive control. A band that never says no is not a band."""
    crossed = 0
    for seed in range(8):
        rows, days = planted_panel(months=12, planted=0.0, seed=100 + seed)
        res = TH.analyse(rows, as_of=days[-1])
        for t in S.FACTORS_ALL:
            v = res["themes"][t]
            if v["quotable"] and v["crossed"]:
                crossed += 1
    # 8 draws x 10 themes = 80 theme-runs at a 0.005 two-sided per-theme bar.
    assert crossed == 0, "%d of 80 pure-noise theme-runs crossed" % crossed


def test_observations_are_variance_standardised_for_cross_section_size():
    """The same IC on a bigger cross-section is stronger evidence, and must count as such."""
    small = TH.observations_to_z([(0.10, 26)])
    big = TH.observations_to_z([(0.10, 101)])
    assert abs(small[0] - 0.10 * 5.0) < 1e-12, small
    assert abs(big[0] - 0.10 * 10.0) < 1e-12, big
    assert big[0] > small[0]


# ---------------------------------------------------------------------------
# 3. THE REFUSALS -- what the live record actually exercises today
# ---------------------------------------------------------------------------

def test_no_ic_is_printed_until_every_floor_is_met():
    rows = thin_panel(dates=3, n_names=50)
    res = TH.analyse(rows, as_of=rows[-1]["date"])
    assert not res["any_quotable"], res["quotable_themes"]
    for t in S.FACTORS_ALL:
        v = res["themes"][t]
        assert v["verdict"] == "NOT-QUOTABLE", (t, v["verdict"])
        # The statistic itself is suppressed, not merely the verdict: a number printed beside
        # its own reason for being untrustworthy gets quoted without it.
        assert v["median_ic"] is None and v["mean_ic"] is None, t
        assert v["running_sum"] is None and v["boundary"] is None, t
        assert v["blocked_by"], t
    text = TH.render(res, {"requested": "test", "chosen": None})
    assert "NOT-QUOTABLE" in text
    assert "NO THEME IS QUOTABLE" in text


def test_a_window_that_has_not_closed_is_never_measured():
    """The look-ahead guard. A 63-day window read early is a made-up number."""
    rows, days = planted_panel(months=9, planted=0.5, seed=2)
    early = days[TH.HORIZON_TD // 2]
    res = TH.analyse(rows, as_of=early)
    assert res["windows_closed"] == 0, res["windows_closed"]
    assert not res["any_quotable"]
    for w in res["windows"]:
        if not w["window_closed"]:
            assert w["ic"] is None and w["voided"], w


def test_attrition_voids_a_date_rather_than_measuring_its_survivors():
    rows, days = planted_panel(months=9, planted=0.5, seed=4)
    # Delete the forward marks for 60% of names on one measurement date's target.
    mdates = TH.measurement_dates(rows)
    victim = mdates[2]
    target = TH._plus_trading_days(victim, TH.HORIZON_TD)
    drop = {"N%03d" % i for i in range(36)}          # 36 of 60 names
    window = {target + _dt.timedelta(days=k) for k in range(-6, 7)}
    kept = [r for r in rows if not (r["ticker"] in drop and r["date"] in window)]
    res = TH.analyse(kept, as_of=days[-1])
    hit = [w for w in res["windows"] if w["date"] == victim.isoformat()][0]
    assert hit["voided"], hit
    assert "attrition" in (hit["void_reason"] or ""), hit["void_reason"]


def test_a_theme_below_the_coverage_floor_is_refused_even_with_enough_months():
    rows, days = planted_panel(months=14, planted=0.5, theme="quality", seed=9)
    for r in rows:                                    # blank one theme almost everywhere
        if r["ticker"] != "N000":
            r["factors"]["growth"] = None
    res = TH.analyse(rows, as_of=days[-1])
    g = res["themes"]["growth"]
    assert g["verdict"] == "NOT-QUOTABLE", g["verdict"]
    assert any("coverage" in b for b in g["blocked_by"]), g["blocked_by"]
    assert res["themes"]["quality"]["quotable"], "the other themes must be unaffected"


def test_a_theme_the_backtest_makes_no_directional_claim_about_gets_no_reference():
    rows, days = planted_panel(months=14, planted=0.5, theme="insider", seed=6)
    res = TH.analyse(rows, as_of=days[-1])
    v = res["themes"]["insider"]
    # insider's backtest median IC is -0.0052, below REF_MIN_IC = 0.01
    assert v["reference_sign"] is None, v["reference_sign"]
    assert v["verdict"] == "NO-REFERENCE", v["verdict"]
    assert v["crossed"] == "up", "the crossing is still reported, only the label is withheld"


def test_the_report_states_what_the_chosen_cross_section_can_detect():
    """The single most consequential number in the run, and it is invisible unless printed.

    Measured by `--calibrate`: at 100 names this band has 2.5% power at 60 months against
    quality's own backtested IC of +0.0356; at 800 names, 80.3%. Same band, same horizon --
    the source decides whether the meter can ever return a verdict, so the report must say
    which regime it is in rather than leaving a reader to assume the favourable one.
    """
    rows, days = planted_panel(months=9, n_names=60, planted=0.2, seed=8)
    res = TH.analyse(rows, as_of=days[-1])
    assert res["typical_cross_section"] >= 20, res["typical_cross_section"]
    assert res["detectable_ic_60m"] < res["detectable_ic_24m"], res
    text = TH.render(res, {"requested": "test", "chosen": None})
    assert "typical cross-section" in text, text[:400]
    assert "detectable by month 24" in text
    # And it must scale the right way: more names -> a smaller detectable IC.
    big, days2 = planted_panel(months=9, n_names=200, planted=0.2, seed=8)
    res2 = TH.analyse(big, as_of=days2[-1])
    assert res2["detectable_ic_60m"] < res["detectable_ic_60m"], (res2, res)


def test_a_missing_backtest_artifact_degrades_to_no_reference_not_to_a_guess():
    signs, ref = TH.reference_signs("/definitely/not/a/path/BACKTEST_RESULTS.json")
    assert set(signs) == set(S.FACTORS_ALL)
    assert all(v is None for v in signs.values()), signs
    assert ref["provenance"]["present"] is False


def test_sigma_breach_is_reported_when_dispersion_exceeds_the_plug_in():
    obs = [(0.9, 101), (-0.9, 101), (0.9, 101), (-0.9, 101), (0.9, 101), (-0.9, 101)]
    m = TH.meter(obs, reference_sign=1)
    assert m["sigma_realised"] > TH.SIGMA, m["sigma_realised"]
    assert m["sigma_breach"] is True


# ---------------------------------------------------------------------------
# 4. THE LOADERS -- synthetic and future-dated rows never reach a statistic
# ---------------------------------------------------------------------------

def test_synthetic_sources_are_excluded_and_named_in_the_output():
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "scans")
        os.makedirs(root)
        for day, provider, tkr in (("2026-06-01", "synthetic (offline test)", "SYN1"),
                                   ("2026-06-02", "free+broker", "AAPL")):
            payload = {"kind": "scan", "scan_date": day, "provider": provider, "n": 1,
                       "rows": [{"ticker": tkr, "rank": 1, "price": 100.0,
                                 "factors": {t: 0.5 for t in S.FACTORS_ALL}}]}
            with gzip.open(os.path.join(root, "%s.json.gz" % day), "wt", encoding="utf-8") as f:
                json.dump(payload, f)
        rows, prov = TH.load_archive(root, today=_dt.date(2026, 12, 31))
        assert prov["dates_seen"] == 2, prov
        assert prov["dates_synthetic"] == 1, prov
        assert [r["ticker"] for r in rows] == ["AAPL"], rows
        text = TH.render(TH.analyse(rows, as_of=_dt.date(2026, 12, 31)),
                         {"requested": "archive", "chosen": "archive", "archive": prov})
        assert "EXCLUDED AS SYNTHETIC" in text


def test_future_dated_rows_are_excluded():
    """`tests/test_saas.py:200` really does leave a 2099-01-01 row in the live store."""
    assert TH.is_future(_dt.date(2099, 1, 1), today=_dt.date(2026, 8, 9)) is True
    assert TH.is_future(_dt.date(2026, 8, 8), today=_dt.date(2026, 8, 9)) is False
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "screener.db")
        c = sqlite3.connect(db)
        c.execute("CREATE TABLE scans (scan_date TEXT, provider TEXT)")
        c.execute("CREATE TABLE snapshot_rows (scan_date TEXT, ticker TEXT, price REAL, "
                  "extra TEXT)")
        fac = json.dumps({"factors": {t: 0.5 for t in S.FACTORS_ALL}})
        for day in ("2099-01-01", "2026-08-08"):
            c.execute("INSERT INTO scans VALUES (?,?)", (day, "ci"))
            c.execute("INSERT INTO snapshot_rows VALUES (?,?,?,?)", (day, "X", 10.0, fac))
        c.commit()
        c.close()
        rows, prov = TH.load_store(db, today=_dt.date(2026, 8, 9))
        assert prov["dates_future"] == 1, prov
        assert [r["date"].isoformat() for r in rows] == ["2026-08-08"], rows


def test_the_two_sources_are_never_merged():
    """They record different books -- whole universe vs top 100 -- so pooling them would
    change what the cross-section IS from date to date, which changes what the IC means."""
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "scans")
        os.makedirs(root)
        payload = {"kind": "scan", "scan_date": "2026-06-02", "provider": "free+broker",
                   "n": 1, "rows": [{"ticker": "ARCH", "price": 1.0, "factors": {}}]}
        with gzip.open(os.path.join(root, "2026-06-02.json.gz"), "wt", encoding="utf-8") as f:
            json.dump(payload, f)
        db = os.path.join(td, "screener.db")
        c = sqlite3.connect(db)
        c.execute("CREATE TABLE scans (scan_date TEXT, provider TEXT)")
        c.execute("CREATE TABLE snapshot_rows (scan_date TEXT, ticker TEXT, price REAL, "
                  "extra TEXT)")
        for day in ("2026-06-01", "2026-06-02", "2026-06-03"):
            c.execute("INSERT INTO scans VALUES (?,?)", (day, "free+broker"))
            c.execute("INSERT INTO snapshot_rows VALUES (?,?,?,?)", (day, "STORE", 1.0, "{}"))
        c.commit()
        c.close()
        rows, prov = TH.load_observations("auto", db_path=db, archive_root=root,
                                          today=_dt.date(2026, 12, 31))
        tickers = {r["ticker"] for r in rows}
        assert tickers == {"STORE"}, tickers          # store wins on date count, alone
        assert prov["chosen"] == "store", prov["chosen"]


def test_the_real_local_record_is_refused_today():
    """Not a mock: the actual repo paths. Every archive day is synthetic and the one store
    row is the 2099 fixture, so the honest output is a refusal on all ten themes."""
    rows, prov = TH.load_observations("auto")
    res = TH.analyse(rows)
    assert not res["any_quotable"], res["quotable_themes"]
    assert res["windows_closed"] == 0, res["windows_closed"]
    assert all(res["themes"][t]["verdict"] == "NOT-QUOTABLE" for t in S.FACTORS_ALL)


def test_the_script_runs_end_to_end_and_writes_an_artifact_with_per_date_rows():
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "THEME_HEALTH.json")
        rc = TH.main(["--json", out])
        assert rc == 0
        with open(out, encoding="utf-8") as f:
            art = json.load(f)
        # RUN_RULES rule 9: the draws, not just the summary.
        for key in ("parameters", "depth", "reference", "windows", "themes", "provenance"):
            assert key in art, key
        assert art["parameters"]["prereg"] == "PREREG_v2_theme_health.md"


if __name__ == "__main__":
    print("theme_health (V2 live theme-health meter)")
    for nm, fn in sorted((k, v) for k, v in list(globals().items())
                         if k.startswith("test_") and callable(v)):
        check(nm, fn)
    print()
    if FAILURES:
        print("%d FAILED" % len(FAILURES))
        for nm, err in FAILURES:
            print("  - %s: %s" % (nm, err))
        raise SystemExit(1)
    n = len([k for k in globals() if k.startswith("test_")])
    print("all %d passed" % n)
