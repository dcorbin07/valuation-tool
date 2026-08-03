"""
Tests for the lazy-prices IC gate (offline, synthetic fixtures). Run:
    python tests/test_lazy_prices_ic.py

Kept out of test_edge.py on purpose — research code must not be able to break the suite the
live panel depends on.

The tests that matter are the ones that would catch a FLATTERING bug, because that is the
kind nobody notices: a signal used on the day it was filed, a forward return that reaches
backwards, a stale score carried for a year, an autocorrelated t-stat quoted as if the
observations were independent, and the decile sign convention this project has already read
backwards once.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.research import lazy_prices_ic as ic


# ---------------------------------------------------------------------------- fixtures

def _calendar(start="2018-01-01", periods=800):
    return pd.bdate_range(start=start, periods=periods)


def _closes(tickers, drifts, cal=None, noise=0.0, seed=0):
    """Price frame where each ticker compounds a constant daily drift, so forward returns
    over any window rank like `drifts`. A little noise is usually wanted: a NOISELESS path
    makes the per-date IC identically 1.0, whose standard deviation is zero, and every
    t-stat then comes back undefined."""
    cal = _calendar() if cal is None else cal
    rng = np.random.default_rng(seed)
    data = {}
    for t, d in zip(tickers, drifts):
        step = np.full(len(cal), 1.0 + d)
        if noise:
            step = step + rng.normal(0.0, noise, len(cal))
        data[t] = 100.0 * np.cumprod(step)
    return pd.DataFrame(data, index=cal)


def _scores(tickers, sims, cal=None, every=63, form="10-Q", first_offset=5):
    """One filing per ticker per quarter, similarity constant per ticker."""
    cal = _calendar() if cal is None else cal
    rows = []
    for t, s in zip(tickers, sims):
        for i in range(first_offset, len(cal), every):
            rows.append({"ticker": t, "form": form, "available_from": cal[i],
                         "cosine_tf": s, "jaccard": s, "n_words": 20000,
                         "prior_n_words": 20000, "doc_source": "primary",
                         "prior_doc_source": "primary"})
    return pd.DataFrame(rows).sort_values(["ticker", "available_from"]).reset_index(drop=True)


def _planted(n=40, reverse=False, noise=0.0004):
    """n tickers whose similarity rank matches (or exactly opposes) their return rank."""
    tickers = [f"T{i:02d}" for i in range(n)]
    sims = [0.90 + 0.002 * i for i in range(n)]
    drifts = [(-0.0002 + 0.00002 * i) for i in range(n)]
    if reverse:
        drifts = list(reversed(drifts))
    return _scores(tickers, sims), _closes(tickers, drifts, noise=noise)


# ---------------------------------------------------------------------------- point in time

def test_a_filing_is_never_used_on_the_day_it_was_filed():
    """EDGAR filings often land after the close. Same-day use is a free look-ahead."""
    cal = _calendar(periods=400)
    scores = pd.DataFrame([{"ticker": "AAA", "form": "10-K", "available_from": cal[100],
                            "cosine_tf": 0.99, "n_words": 20000}])
    closes = _closes(["AAA"], [0.0005], cal)
    on_the_day = ic.build_panel(scores, closes, dates=[cal[100]])
    day_after = ic.build_panel(scores, closes, dates=[cal[101]])
    assert on_the_day.empty, "a filing was used on its own filing date"
    assert len(day_after) == 1, "the score should be usable the very next day"


def test_no_future_filing_leaks_into_an_earlier_date():
    cal = _calendar(periods=400)
    scores = pd.DataFrame([
        {"ticker": "AAA", "form": "10-Q", "available_from": cal[50], "cosine_tf": 0.80,
         "n_words": 20000},
        {"ticker": "AAA", "form": "10-Q", "available_from": cal[120], "cosine_tf": 0.99,
         "n_words": 20000}])
    closes = _closes(["AAA"], [0.0005], cal)
    p = ic.build_panel(scores, closes, dates=[cal[80]])
    assert len(p) == 1 and abs(p.iloc[0]["signal"] - 0.80) < 1e-9, \
        f"used a score filed in the future: {p.to_dict('records')}"


def test_a_stale_score_expires_instead_of_being_carried_forever():
    cal = _calendar(periods=500)
    scores = pd.DataFrame([{"ticker": "AAA", "form": "10-K", "available_from": cal[10],
                            "cosine_tf": 0.99, "n_words": 20000}])
    closes = _closes(["AAA"], [0.0005], cal)
    fresh = ic.build_panel(scores, closes, dates=[cal[40]], max_stale_days=120)
    stale = ic.build_panel(scores, closes, dates=[cal[300]], max_stale_days=120)
    assert len(fresh) == 1
    assert stale.empty, "a filing older than the staleness cap was still being traded"


def test_forward_return_runs_forward_and_matches_the_price_path():
    cal = _calendar(periods=400)
    scores = pd.DataFrame([{"ticker": "AAA", "form": "10-Q", "available_from": cal[50],
                            "cosine_tf": 0.9, "n_words": 20000}])
    closes = _closes(["AAA"], [0.001], cal)
    p = ic.build_panel(scores, closes, horizon=63, dates=[cal[100]])
    want = closes["AAA"].iloc[163] / closes["AAA"].iloc[100] - 1.0
    assert abs(p.iloc[0]["fwd_ret"] - want) < 1e-9, p.iloc[0]["fwd_ret"]
    assert p.iloc[0]["fwd_ret"] > 0


def test_attach_signal_uses_only_filings_strictly_before_the_panel_date():
    scores = pd.DataFrame([
        {"ticker": "AAA", "available_from": pd.Timestamp("2020-03-10"), "cosine_tf": 0.7},
        {"ticker": "AAA", "available_from": pd.Timestamp("2020-06-01"), "cosine_tf": 0.95}])
    tp = pd.DataFrame([{"date": "2020-04-01", "ticker": "AAA", "fwd_ret": 0.1},
                       {"date": "2020-06-01", "ticker": "AAA", "fwd_ret": 0.1}])
    out = ic.attach_signal(tp, scores)
    assert abs(out.iloc[0]["lazy"] - 0.7) < 1e-9
    assert abs(out.iloc[1]["lazy"] - 0.7) < 1e-9, "same-day filing leaked into the join"


# ---------------------------------------------------------------------------- recovery

def test_a_planted_relationship_is_recovered_with_a_positive_ic():
    scores, closes = _planted()
    panel = ic.build_panel(scores, closes)
    s = ic.summarize_ic(ic.ic_by_date(panel))
    assert s["mean_ic"] > 0.5, s
    assert s["ic_tstat_nw"] > 2.0, s


def test_a_reversed_relationship_is_reported_as_negative_not_flipped():
    """The direction is pre-registered. A signal that works backwards must show up as a
    rejection, never as a sign-flip opportunity."""
    scores, closes = _planted(reverse=True)
    panel = ic.build_panel(scores, closes)
    s = ic.summarize_ic(ic.ic_by_date(panel))
    assert s["mean_ic"] < -0.5, s
    q = ic.quantile_stats(panel)
    assert q["long_short_ann"] < 0, q["long_short_ann"]
    v = ic.verdict(s, q, {"both_halves_positive": False}, None)
    assert v["decision"] == "REJECT", v


def test_monotonicity_is_minus_one_when_the_signal_is_perfectly_ordered():
    """Buckets run best-first, so -1.0 is the IDEAL. This project has read that backwards
    before; the convention is pinned here as it is in the panel."""
    scores, closes = _planted()
    q = ic.quantile_stats(ic.build_panel(scores, closes))
    assert q["monotonicity"] < -0.95, q["monotonicity"]
    assert q["decile_ann_return"][0] > q["decile_ann_return"][-1], q["decile_ann_return"]
    assert q["top_decile_alpha"] > 0 and q["bottom_decile_alpha"] < 0, q


def test_a_signal_with_no_relationship_produces_no_significance():
    """The signal must vary filing to filing here. A similarity that is CONSTANT per ticker
    against a return that is also constant per ticker produces the identical IC on every
    date — a zero-variance series whose t-stat is enormous no matter how spurious the
    correlation is. That is a property of persistent signals worth remembering when reading
    the real numbers, not something to engineer away in the fixture.

    A single random draw clears t=2 about one time in twenty, so this checks CALIBRATION
    over ten independent nulls rather than seed-shopping for one quiet draw.
    """
    cal = _calendar(periods=800)
    tickers = [f"T{i:02d}" for i in range(40)]
    hits, ts = 0, []
    for seed in range(10):
        rng = np.random.default_rng(100 + seed)
        rows = []
        for t in tickers:
            for i in range(5, len(cal), 63):
                rows.append({"ticker": t, "form": "10-Q", "available_from": cal[i],
                             "cosine_tf": float(rng.random()), "n_words": 20000})
        closes = _closes(tickers, [0.0002] * 40, cal, noise=0.001, seed=seed)
        s = ic.summarize_ic(ic.ic_by_date(ic.build_panel(pd.DataFrame(rows), closes)))
        ts.append(abs(s["ic_tstat_nw"]))
        hits += abs(s["ic_tstat_nw"]) > 2.0
    assert hits <= 2, f"{hits}/10 pure-noise runs looked significant: {[round(x, 2) for x in ts]}"
    assert float(np.median(ts)) < 1.5, [round(x, 2) for x in ts]


# ---------------------------------------------------------------------------- statistics

def test_newey_west_is_more_conservative_than_the_plain_t_on_overlapping_data():
    """Monthly observations of a 3-month forward return overlap; treating them as
    independent inflates the t-stat. NW must shrink it."""
    rng = np.random.default_rng(3)
    raw = rng.normal(0.02, 1.0, 400)
    overlap = np.convolve(raw, np.ones(3) / 3.0, mode="valid")   # 3-period overlap
    plain, nw = ic.tstat(overlap), ic.nw_tstat(overlap, 2)
    assert plain > nw > 0, (plain, nw)


def test_nw_lag_matches_the_overlap_of_the_holding_period():
    assert ic.nw_lag_for(21) == 0          # monthly hold, monthly rebalance: no overlap
    assert ic.nw_lag_for(63) == 2          # 3-month hold: two months of overlap
    assert ic.nw_lag_for(252) == 11


def test_spearman_is_rank_based_and_scale_invariant():
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert abs(ic.spearman(a, a * 1000.0) - 1.0) < 1e-9
    assert abs(ic.spearman(a, -a) + 1.0) < 1e-9
    assert abs(ic.spearman(a, np.exp(a)) - 1.0) < 1e-9, "a monotone transform changed the IC"


def test_ic_skips_dates_with_too_thin_a_cross_section():
    scores, closes = _planted(n=8)
    panel = ic.build_panel(scores, closes)
    assert not panel.empty
    assert ic.ic_by_date(panel, min_names=20).empty, "scored an 8-name cross-section"


# ---------------------------------------------------------------------------- data hygiene

def test_stub_and_non_primary_filings_are_filtered_and_counted(tmp=None):
    import tempfile
    rows = [{"ticker": "AAA", "form": "10-K", "available_from": "2020-01-02",
             "cosine_tf": 0.99, "jaccard": 0.9, "n_words": 20000, "prior_n_words": 20000,
             "doc_source": "primary", "prior_doc_source": "primary"},
            {"ticker": "BBB", "form": "10-K", "available_from": "2020-01-02",
             "cosine_tf": 0.999, "jaccard": 0.99, "n_words": 900, "prior_n_words": 900,
             "doc_source": "primary", "prior_doc_source": "primary"},
            {"ticker": "CCC", "form": "10-K", "available_from": "2020-01-02",
             "cosine_tf": 0.5, "jaccard": 0.4, "n_words": 40000, "prior_n_words": 40000,
             "doc_source": "full", "prior_doc_source": "primary"}]
    path = os.path.join(tempfile.mkdtemp(), "s.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    df, drops = ic.load_scores(path)
    assert list(df["ticker"]) == ["AAA"], df["ticker"].tolist()
    assert drops["not_primary_document"] == 1 and drops["rows_in"] == 3, drops
    assert drops["stub_filings_under_2000_words"] == 1, drops


def test_prices_are_not_forward_filled_across_a_long_gap():
    """Filling through a trading halt would invent a flat return where the name stopped."""
    cal = _calendar(periods=300)
    s = pd.Series(np.full(len(cal), 100.0), index=cal)
    s.iloc[150:] = np.nan                       # stops trading
    frame = pd.DataFrame({"AAA": s}).ffill(limit=ic.MAX_FFILL_DAYS)
    assert frame["AAA"].iloc[155] == 100.0      # short gap: filled
    assert not np.isfinite(frame["AAA"].iloc[200])   # long gap: still missing


def test_within_form_zscore_removes_a_pure_form_level_difference():
    """If 10-Ks simply score lower than 10-Qs, a raw cross-sectional rank partly ranks FORM.
    The within-form variant must neutralize that."""
    cal = _calendar(periods=400)
    tickers = [f"T{i:02d}" for i in range(30)]
    rows = []
    for i, t in enumerate(tickers):
        form = "10-K" if i % 2 else "10-Q"
        base = 0.80 if form == "10-K" else 0.95      # pure form-level offset
        rows.append({"ticker": t, "form": form, "available_from": cal[50],
                     "cosine_tf": base + 0.001 * i, "n_words": 20000})
    scores = pd.DataFrame(rows)
    closes = _closes(tickers, [0.0003] * 30, cal)
    raw = ic.build_panel(scores, closes, dates=[cal[100]])
    wf = ic.build_panel(scores, closes, dates=[cal[100]], within_form=True)
    ks_raw = raw[raw["form"] == "10-K"]["signal"].mean()
    qs_raw = raw[raw["form"] == "10-Q"]["signal"].mean()
    ks_wf = wf[wf["form"] == "10-K"]["signal"].mean()
    qs_wf = wf[wf["form"] == "10-Q"]["signal"].mean()
    assert qs_raw - ks_raw > 0.1, (ks_raw, qs_raw)
    assert abs(qs_wf - ks_wf) < 1e-9, (ks_wf, qs_wf)


# ---------------------------------------------------------------------------- held out

def test_holdout_reports_both_halves_and_embargoes_the_boundary():
    scores, closes = _planted()
    panel = ic.build_panel(scores, closes)
    h = ic.holdout_split(panel, horizon=63, min_dates=6)
    assert "early" in h and "late" in h, h
    assert h["embargo_periods"] == 3, h["embargo_periods"]
    assert h["both_halves_positive"] is True, h
    assert pd.Timestamp(h["early"]["last_date"]) < pd.Timestamp(h["late"]["first_date"]), h


def test_holdout_flags_a_signal_that_only_works_in_one_half():
    """The failure mode a single full-sample number cannot see."""
    n, cal = 40, _calendar(periods=1000)
    tickers = [f"T{i:02d}" for i in range(n)]
    sims = [0.90 + 0.002 * i for i in range(n)]
    half = len(cal) // 2
    data = {}
    for i, t in enumerate(tickers):
        step = np.concatenate([np.full(half, 1.0 - 0.0002 + 0.00002 * i),
                               np.full(len(cal) - half, 1.0 - 0.0002 + 0.00002 * (n - 1 - i))])
        data[t] = 100.0 * np.cumprod(step)          # relationship reverses at the midpoint
    closes = pd.DataFrame(data, index=cal)
    panel = ic.build_panel(_scores(tickers, sims, cal), closes)
    h = ic.holdout_split(panel, horizon=63, min_dates=6)
    assert h["both_halves_positive"] is False, h
    assert h.get("confirmed") is False, h


# ---------------------------------------------------------------------------- verdict

def test_verdict_requires_significance_stability_and_incremental_value():
    strong_ic = {"ic_tstat_nw": 3.0}
    strong_q = {"long_short_tstat_nw": 2.5, "monotonicity": -0.8}
    stable = {"both_halves_positive": True}
    assert ic.verdict(strong_ic, strong_q, stable, None)["adopt"] is True
    assert ic.verdict({"ic_tstat_nw": 1.2}, strong_q, stable, None)["adopt"] is False
    assert ic.verdict(strong_ic, {"long_short_tstat_nw": 0.4}, stable, None)["adopt"] is False
    assert ic.verdict(strong_ic, strong_q, {"both_halves_positive": False},
                      None)["adopt"] is False
    dupe = {"base_long_short_tstat_nw": 2.0, "with_signal_long_short_tstat_nw": 1.95}
    assert ic.verdict(strong_ic, strong_q, stable, dupe)["adopt"] is False, \
        "adopted a signal that made the composite worse"


def test_verdict_states_its_rule_and_its_reasons():
    v = ic.verdict({"ic_tstat_nw": 0.3}, {"long_short_tstat_nw": 0.2, "monotonicity": 0.1},
                   {"both_halves_positive": False}, None)
    assert v["decision"] == "REJECT"
    assert "IC t" in v["rule"] and len(v["reasons"]) >= 3, v


# ---------------------------------------------------------------------------- orthogonality

def test_orthogonality_sees_through_a_signal_that_is_just_a_theme_in_disguise():
    """A repackaged theme must lose its IC once the themes are regressed out."""
    rng = np.random.default_rng(11)
    rows = []
    for d in pd.date_range("2018-01-01", periods=30, freq="QE"):
        for i in range(60):
            q = rng.normal()
            rows.append({"date": str(d.date()), "ticker": f"T{i:02d}", "quality": q,
                         # a thin repackaging of quality — the case that must not pass
                         "value": rng.normal(), "lazy": q + rng.normal(0, 0.1),
                         "fwd_ret": 0.02 * q + rng.normal(0, 0.01)})
    tp = pd.DataFrame(rows)
    o = ic.orthogonality(tp, ["quality", "value"])
    assert o["theme_correlation"]["quality"] > 0.95, o["theme_correlation"]
    assert o["raw_ic_tstat"] > 2.0, o
    assert abs(o["residual_ic_mean"]) < 0.1, o["residual_ic_mean"]
    assert abs(o["residual_ic_mean"]) < 0.25 * abs(o["raw_ic_mean"]), o


def test_orthogonality_keeps_an_independent_signal_alive_after_residualizing():
    rng = np.random.default_rng(12)
    rows = []
    for d in pd.date_range("2018-01-01", periods=30, freq="QE"):
        for i in range(60):
            q, lz = rng.normal(), rng.normal()
            rows.append({"date": str(d.date()), "ticker": f"T{i:02d}", "quality": q,
                         "value": rng.normal(), "lazy": lz,
                         "fwd_ret": 0.02 * q + 0.02 * lz + rng.normal(0, 0.005)})
    o = ic.orthogonality(pd.DataFrame(rows), ["quality", "value"])
    assert abs(o["theme_correlation"]["quality"]) < 0.2, o["theme_correlation"]
    assert o["residual_ic_tstat"] > 2.0, o
    assert o["with_signal_long_short_ann"] > o["base_long_short_ann"], o


# ---------------------------------------------------------------------------- isolation

def test_run_writes_a_complete_result_file_end_to_end():
    """Covers the whole `run()` path on tiny synthetic inputs. Everything above tests one
    function at a time, which missed a real bug: a local named `out` inside the
    orthogonality block shadowed the `out` JSON PATH parameter, so a ten-minute run
    computed every number correctly and then died on the write."""
    import json
    import tempfile
    root = tempfile.mkdtemp()
    data_dir = os.path.join(root, "backtest")
    os.makedirs(os.path.join(data_dir, "prices"))
    scores, closes = _planted(n=40)
    for t in closes.columns:
        pd.DataFrame({"date": closes.index.strftime("%Y-%m-%d"),
                      "close": closes[t].values}).to_csv(
            os.path.join(data_dir, "prices", f"{t}.csv"), index=False)
    sp = os.path.join(root, "scores.csv")
    scores.to_csv(sp, index=False)
    out = os.path.join(root, "nested", "result.json")
    r = ic.run(sp, data_dir, measures=("cosine_tf",), horizons=(21,),
               do_orthogonality=False, out=out, log=lambda *_a: None)
    assert os.path.exists(out), "run() did not write its result file"
    on_disk = json.load(open(out, encoding="utf-8"))
    for key in ("config", "coverage", "grid", "primary", "holdout", "within_form",
                "flagged_cells", "verdict"):
        assert key in on_disk, f"missing {key} in the written result"
    assert on_disk["verdict"]["decision"] in ("ADOPT", "REJECT")
    assert r["coverage"]["tickers"] == 40, r["coverage"]


def test_research_code_is_not_imported_by_the_live_panel():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for sub in ("edge", "screener", "web", "saas", "engine", "report", "intraday"):
        base = os.path.join(root, "valuation", sub)
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith(".py"):
                    with open(os.path.join(dirpath, fn), encoding="utf-8",
                              errors="ignore") as f:
                        if "lazy_prices" in f.read():
                            hits.append(os.path.join(sub, fn))
    assert not hits, f"research module leaked into production code: {hits}"


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
    print(f"\n{passed}/{len(tests)} lazy-prices IC tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
