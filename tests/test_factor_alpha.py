"""
R1 factor-adjusted-alpha tests (offline, deterministic). Run:
    python tests/test_factor_alpha.py

The R1 verdict rests entirely on an intercept and a Newey-West t-statistic computed by
`scripts/factor_alpha.py`, and statsmodels is not installed in this environment, so that
regression is hand-written. These tests pin it against closed-form results, pin the window
aggregation against look-ahead, and pin the rank guard that caught the one real bug in the
first run of the script (a duplicated market column in the q-factor design).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from scripts.factor_alpha import (ols_nw, regress, _agg, factor_windows, decile_series,
                                  PPY, FF_MODEL)


# ------------------------------------------------------------------ the regression itself
def test_ols_recovers_known_coefficients():
    """With no noise the fit must return the generating coefficients exactly."""
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    y = 0.05 + 1.5 * X[:, 0] - 0.7 * X[:, 1] + 0.2 * X[:, 2]
    r = ols_nw(y, X, lag=1)
    assert abs(r["beta"][0] - 0.05) < 1e-10, r["beta"][0]
    assert np.allclose(r["beta"][1:], [1.5, -0.7, 0.2], atol=1e-10)
    assert abs(r["r2"] - 1.0) < 1e-12


def test_ols_betas_match_lstsq():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(120, 4))
    y = rng.normal(size=120) + 0.3 * X[:, 0]
    Z = np.column_stack([np.ones(120), X])
    ref, *_ = np.linalg.lstsq(Z, y, rcond=None)
    assert np.allclose(ols_nw(y, X)["beta"], ref, atol=1e-10)


def test_lag0_matches_white_sandwich():
    """lag=0 must reduce to the plain heteroskedasticity-robust (White) covariance."""
    rng = np.random.default_rng(2)
    X = rng.normal(size=(150, 2))
    y = 0.01 + X @ [0.4, -0.3] + rng.normal(scale=0.5, size=150)
    r = ols_nw(y, X, lag=0)

    Z = np.column_stack([np.ones(150), X])
    b = np.linalg.pinv(Z.T @ Z) @ (Z.T @ y)
    u = Z * (y - Z @ b)[:, None]
    inv = np.linalg.pinv(Z.T @ Z)
    cov = inv @ (u.T @ u) @ inv * (150 / (150 - 3))
    assert np.allclose(r["se"], np.sqrt(np.diag(cov)), atol=1e-12)


def test_newey_west_bartlett_weights_are_applied():
    """The lag-1 meat must equal G0 + 0.5*(G1 + G1'), i.e. a Bartlett weight of 1/2."""
    rng = np.random.default_rng(3)
    X = rng.normal(size=(100, 2))
    y = 0.02 + X @ [0.5, 0.1] + rng.normal(scale=0.4, size=100)
    r = ols_nw(y, X, lag=1)

    Z = np.column_stack([np.ones(100), X])
    inv = np.linalg.pinv(Z.T @ Z)
    b = inv @ (Z.T @ y)
    u = Z * (y - Z @ b)[:, None]
    G1 = u[1:].T @ u[:-1]
    S = u.T @ u + 0.5 * (G1 + G1.T)
    cov = inv @ S @ inv * (100 / (100 - 3))
    assert np.allclose(r["se"], np.sqrt(np.diag(cov)), atol=1e-12)


def test_newey_west_widens_se_under_positive_autocorrelation():
    """A positively autocorrelated residual must not be allowed to look more precise."""
    rng = np.random.default_rng(4)
    n = 400
    e = np.zeros(n)
    for i in range(1, n):
        e[i] = 0.8 * e[i - 1] + rng.normal(scale=0.3)
    X = rng.normal(size=(n, 1))
    y = 0.01 + 0.2 * X[:, 0] + e
    assert ols_nw(y, X, lag=4)["se"][0] > ols_nw(y, X, lag=0)["se"][0]


def test_rank_deficient_design_raises():
    """The real bug this guard caught: two copies of the market column in one design."""
    rng = np.random.default_rng(5)
    x = rng.normal(size=80)
    X = np.column_stack([x, x * 1.0])                 # exact duplicate
    try:
        ols_nw(rng.normal(size=80), X)
    except ValueError as exc:
        assert "rank-deficient" in str(exc)
        return
    raise AssertionError("a duplicated regressor must not be silently fitted")


def test_intercept_is_reported_as_the_alpha():
    """`regress` must annualise the INTERCEPT (not the mean) and label loadings in order."""
    rng = np.random.default_rng(6)
    F = pd.DataFrame(rng.normal(scale=0.05, size=(120, 6)), columns=FF_MODEL)
    y = 0.03 + F.values @ np.array([1.0, 0.5, 0.0, 0.0, 0.0, 0.0])
    r = regress(y, F, FF_MODEL, "t")
    assert abs(r["alpha_63d"] - 0.03) < 1e-10
    assert abs(r["alpha_ann"] - 0.03 * PPY) < 1e-10
    assert abs(r["loadings"]["MKT"]["beta"] - 1.0) < 1e-9
    assert abs(r["loadings"]["SMB"]["beta"] - 0.5) < 1e-9
    assert abs(r["loadings"]["HML"]["beta"]) < 1e-9
    # alpha != raw mean whenever the factors carry any of the return
    assert abs(r["raw_ann"] - r["alpha_ann"]) > 1e-6


# ------------------------------------------------------------------ window aggregation
def test_agg_compound_and_sum():
    v = [0.01, 0.02, -0.005]
    assert abs(_agg(v, "compound") - ((1.01 * 1.02 * 0.995) - 1)) < 1e-15
    assert abs(_agg(v, "sum") - 0.025) < 1e-15


def test_agg_refuses_incomplete_windows():
    """A window missing any factor day must be dropped, never partially compounded."""
    assert _agg([0.01, np.nan, 0.02], "compound") != _agg([0.01, 0.02], "compound")
    assert np.isnan(_agg([0.01, np.nan], "compound"))
    assert np.isnan(_agg([], "compound"))


def _synthetic_daily(monkeypatch_target):
    days = pd.bdate_range("2020-01-01", periods=300)
    n = len(days)
    return pd.DataFrame({
        "date": days,
        "MKT_RF": np.full(n, 0.001), "SMB": np.full(n, 0.0), "HML": np.full(n, 0.0),
        "RMW": np.full(n, 0.0), "CMA": np.full(n, 0.0), "RF": np.full(n, 0.0),
        "UMD": np.full(n, 0.0),
        "qMKT": np.full(n, 0.001), "ME": np.full(n, 0.0), "IA": np.full(n, 0.0),
        "ROE": np.full(n, 0.0), "EG": np.full(n, 0.0), "qRF": np.full(n, 0.0),
    })


def test_factor_windows_use_only_days_inside_the_window():
    """No look-ahead: window (a, b] must exclude day a and include day b, nothing beyond.

    Built so each day contributes a known constant, which makes the window return a pure
    function of how many days were counted.
    """
    import scripts.factor_alpha as fa

    daily = _synthetic_daily(None)
    orig = fa._load_daily
    fa._load_daily = lambda: daily
    try:
        grid = [daily["date"].iloc[0], daily["date"].iloc[10], daily["date"].iloc[20]]
        w = fa.factor_windows(grid, how="sum")
        assert list(w["n_days"]) == [10, 10], list(w["n_days"])
        # 10 days at 0.001 excess each, summed
        assert np.allclose(w["MKT"].values, 0.010)
        # the day AT the left edge is excluded and the right edge included
        assert w.index[0] == grid[0] and w["end"].iloc[0] == grid[1]
    finally:
        fa._load_daily = orig


def test_factor_windows_drop_a_window_with_missing_factor_days():
    import scripts.factor_alpha as fa

    daily = _synthetic_daily(None)
    daily.loc[5, "SMB"] = np.nan
    orig = fa._load_daily
    fa._load_daily = lambda: daily
    try:
        grid = [daily["date"].iloc[0], daily["date"].iloc[10], daily["date"].iloc[20]]
        w = fa.factor_windows(grid, how="sum")
        assert np.isnan(w["SMB"].iloc[0]), "a window with a missing factor day must be NaN"
        assert not np.isnan(w["SMB"].iloc[1])
    finally:
        fa._load_daily = orig


# ------------------------------------------------------------------ the strategy series
def _toy_panel():
    rows = []
    for d in ("2020-01-01", "2020-04-01"):
        for i in range(50):
            rows.append({"date": pd.Timestamp(d), "ticker": f"T{i:02d}",
                         # value rises with i, fwd_ret rises with i -> top decile wins
                         "value": float(i), "fwd_ret": 0.001 * i,
                         "bench_ret": 0.02})
    return pd.DataFrame(rows)


def test_decile_series_orders_top_above_bottom():
    s = decile_series(_toy_panel(), {"value": 1.0})
    assert len(s) == 2
    assert (s["top"] > s["ew"]).all() and (s["ew"] > s["bot"]).all()
    # top decile of 50 names is 5 names: i = 49..45
    assert abs(s["top"].iloc[0] - np.mean([0.001 * i for i in range(45, 50)])) < 1e-12
    assert abs(s["bot"].iloc[0] - np.mean([0.001 * i for i in range(0, 5)])) < 1e-12
    assert abs(s["ew"].iloc[0] - np.mean([0.001 * i for i in range(50)])) < 1e-12


def test_decile_series_carries_the_benchmark_for_the_alignment_check():
    s = decile_series(_toy_panel(), {"value": 1.0})
    assert "bench" in s.columns and (s["bench"] == 0.02).all()


def test_top_minus_ew_reproduces_the_headline_arithmetic():
    """`top_decile_alpha` is 4 * mean(top - ew). R1 must be regressing THAT object."""
    s = decile_series(_toy_panel(), {"value": 1.0})
    headline = 4.0 * float((s["top"] - s["ew"]).mean())
    r = regress((s["top"] - s["ew"]).values,
                pd.DataFrame({c: np.zeros(len(s)) for c in FF_MODEL}), [], "x")
    assert abs(r["raw_ann"] - headline) < 1e-12, (r["raw_ann"], headline)


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
    print(f"\n{passed}/{len(tests)} R1 factor-alpha tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
