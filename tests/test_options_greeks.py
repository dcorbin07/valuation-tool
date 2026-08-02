"""
Greeks / GEX derivation tests (offline, no data, no network). Run:
    python tests/test_options_greeks.py

The point of this file is ONE thing: a hand-rolled third derivative that is quietly wrong would
corrupt everything built on the derived layer while every run completed normally — the exact
silent-corruption failure this project has hit repeatedly (empty roe/roic, the currency bug,
the SF3 positional arg). So every greek here is checked against a CENTRAL FINITE DIFFERENCE of
the analytic price, and the vectorised pricer/IV solver is checked against the existing scalar
`blackscholes` implementation the live code already uses.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import blackscholes as BS
from valuation.edge import options_greeks as G

# These tests must never touch the network and must not depend on whether a rate cache happens
# to be on disk, so the rate loader is pinned to its deterministic fallback schedule. The chain
# fixtures below then price at exactly the rate `enrich_frame` will solve at.
BS._RATES_TRIED = True
BS._RATE_CACHE.clear()

# A spread of cases: ITM/ATM/OTM, near and far dated, calm and wild vol, calls and puts.
CASES = [
    # S,    K,     T,     r,     sigma, is_put
    (100.0, 100.0, 0.50, 0.04, 0.25, False),
    (100.0, 120.0, 0.25, 0.04, 0.35, False),
    (100.0, 80.0, 1.00, 0.02, 0.20, False),
    (100.0, 100.0, 0.50, 0.04, 0.25, True),
    (100.0, 120.0, 0.75, 0.05, 0.45, True),
    (100.0, 85.0, 0.10, 0.01, 0.60, True),
    (37.5, 40.0, 0.33, 0.03, 0.30, False),
    (410.0, 380.0, 0.08, 0.05, 0.22, True),
]


def _arr(i):
    return [np.array([c[i]], dtype=float) for c in CASES]


def _cols():
    S = np.array([c[0] for c in CASES], dtype=float)
    K = np.array([c[1] for c in CASES], dtype=float)
    T = np.array([c[2] for c in CASES], dtype=float)
    r = np.array([c[3] for c in CASES], dtype=float)
    sig = np.array([c[4] for c in CASES], dtype=float)
    put = np.array([c[5] for c in CASES], dtype=bool)
    return S, K, T, r, sig, put


def _price(S, K, T, r, sig, put):
    return G.bs_price(S, K, T, r, sig, put)


def _fd(f, x, h):
    """Central difference of a scalar-in/array-out function."""
    return (f(x + h) - f(x - h)) / (2.0 * h)


def _fd2(f, x, h):
    return (f(x + h) - 2.0 * f(x) + f(x - h)) / (h * h)


# --------------------------------------------------------------------------- #
#  vectorised pricer agrees with the scalar one the live code uses
# --------------------------------------------------------------------------- #
def test_vector_price_matches_scalar():
    for S, K, T, r, sig, put in CASES:
        mine = float(G.bs_price(S, K, T, r, sig, put))
        theirs = BS.bs_price(S, K, T, r, sig, "P" if put else "C")
        assert abs(mine - theirs) < 1e-9, (mine, theirs)


def test_put_call_parity():
    S, K, T, r, sig, _ = _cols()
    c = G.bs_price(S, K, T, r, sig, np.zeros(len(S), dtype=bool))
    p = G.bs_price(S, K, T, r, sig, np.ones(len(S), dtype=bool))
    lhs = c - p
    rhs = S - K * np.exp(-r * T)
    assert np.max(np.abs(lhs - rhs)) < 1e-9, np.max(np.abs(lhs - rhs))


# --------------------------------------------------------------------------- #
#  implied vol round-trips, and matches the scalar bisection
# --------------------------------------------------------------------------- #
def test_iv_round_trip():
    S, K, T, r, sig, put = _cols()
    px = G.bs_price(S, K, T, r, sig, put)
    iv, reason = G.implied_vol(px, S, K, T, r, put)
    assert np.all(np.isfinite(iv)), reason
    assert np.max(np.abs(iv - sig)) < 1e-6, np.max(np.abs(iv - sig))


def test_iv_matches_scalar_blackscholes():
    for S, K, T, r, sig, put in CASES:
        px = float(G.bs_price(S, K, T, r, sig, put))
        mine = float(G.implied_vol(np.array([px]), np.array([S]), np.array([K]),
                                   np.array([T]), np.array([r]), np.array([put]))[0][0])
        theirs = BS.implied_vol(px, S, K, T, r, "P" if put else "C")
        assert theirs is not None
        assert abs(mine - theirs) < 1e-3, (mine, theirs)


def test_iv_refuses_garbage_rather_than_inventing_a_vol():
    """Below intrinsic and above the 500%-vol price must return NaN WITH a reason. A fabricated
    vol here would flow into every downstream feature and never announce itself."""
    S = np.array([100.0, 100.0, 100.0])
    K = np.array([80.0, 100.0, 100.0])
    T = np.array([0.5, 0.5, 0.5])
    r = np.array([0.04, 0.04, 0.04])
    put = np.array([False, False, False])
    # 1: mid far below intrinsic (S-K discounted). 2: absurdly rich. 3: fine.
    px = np.array([1.0, 99.0, 10.0])
    iv, reason = G.implied_vol(px, S, K, T, r, put)
    assert not np.isfinite(iv[0]) and reason[0] == "below_intrinsic", (iv[0], reason[0])
    assert not np.isfinite(iv[1]) and reason[1] == "above_max_vol", (iv[1], reason[1])
    assert np.isfinite(iv[2]) and reason[2] == ""


# --------------------------------------------------------------------------- #
#  EVERY greek against a central finite difference of the analytic price
# --------------------------------------------------------------------------- #
def _check(name, analytic, numeric, tol):
    scale = np.maximum(np.abs(numeric), 1e-6)
    err = np.abs(analytic - numeric) / scale
    assert np.max(err) < tol, f"{name}: max rel err {np.max(err):.2e}\n{analytic}\n{numeric}"


def test_first_order_greeks_match_finite_difference():
    S, K, T, r, sig, put = _cols()
    g = G.greeks(S, K, T, r, sig, put)
    hS, hv, hT, hr = 1e-4 * S, 1e-5, 1e-6, 1e-7
    _check("delta", g["delta"], _fd(lambda x: _price(x, K, T, r, sig, put), S, hS), 1e-5)
    _check("gamma", g["gamma"], _fd2(lambda x: _price(x, K, T, r, sig, put), S, hS), 1e-4)
    _check("vega", g["vega"], _fd(lambda x: _price(S, K, T, r, x, put), sig, hv), 1e-6)
    _check("rho", g["rho"], _fd(lambda x: _price(S, K, T, x, sig, put), r, hr), 1e-5)
    # theta is dV/dt = -dV/dT: time passing SHRINKS time to expiry.
    _check("theta", g["theta"], -_fd(lambda x: _price(S, K, x, r, sig, put), T, hT), 1e-4)


def test_second_order_greeks_match_finite_difference():
    S, K, T, r, sig, put = _cols()
    g = G.greeks(S, K, T, r, sig, put)
    hS, hv, hT = 1e-4 * S, 1e-5, 1e-6

    def delta_of_sigma(x):
        return G.greeks(S, K, T, r, x, put)["delta"]

    def delta_of_T(x):
        return G.greeks(S, K, x, r, sig, put)["delta"]

    def vega_of_T(x):
        return G.greeks(S, K, x, r, sig, put)["vega"]

    _check("vanna", g["vanna"], _fd(delta_of_sigma, sig, hv), 1e-5)
    _check("charm", g["charm"], -_fd(delta_of_T, T, hT), 1e-3)
    _check("vomma", g["vomma"], _fd(lambda x: G.greeks(S, K, T, r, x, put)["vega"], sig, hv), 1e-5)
    _check("veta", g["veta"], -_fd(vega_of_T, T, hT), 1e-3)
    # vanna is also d(vega)/dS — check the cross-partial the other way round.
    _check("vanna(dvega/dS)", g["vanna"],
           _fd(lambda x: G.greeks(x, K, T, r, sig, put)["vega"], S, hS), 1e-4)


def test_third_order_greeks_match_finite_difference():
    S, K, T, r, sig, put = _cols()
    g = G.greeks(S, K, T, r, sig, put)
    hS, hv, hT = 1e-3 * S, 1e-4, 1e-6

    def gamma_of_S(x):
        return G.greeks(x, K, T, r, sig, put)["gamma"]

    def gamma_of_T(x):
        return G.greeks(S, K, x, r, sig, put)["gamma"]

    def gamma_of_sigma(x):
        return G.greeks(S, K, T, r, x, put)["gamma"]

    def vomma_of_sigma(x):
        return G.greeks(S, K, T, r, x, put)["vomma"]

    _check("speed", g["speed"], _fd(gamma_of_S, S, hS), 1e-4)
    _check("color", g["color"], -_fd(gamma_of_T, T, hT), 1e-3)
    _check("zomma", g["zomma"], _fd(gamma_of_sigma, sig, hv), 1e-5)
    _check("ultima", g["ultima"], _fd(vomma_of_sigma, sig, hv), 1e-4)


def test_greeks_agree_with_blackscholes_module_after_the_stated_rescale():
    """Pins the unit convention: this module is RAW, blackscholes.py reports vega/100 and
    theta/365. If either side ever changes silently, this fails."""
    for S, K, T, r, sig, put in CASES:
        mine = G.greeks(S, K, T, r, sig, put)
        theirs = BS.greeks(S, K, T, r, sig, "P" if put else "C")
        assert abs(float(mine["delta"]) - theirs["delta"]) < 1e-9
        assert abs(float(mine["gamma"]) - theirs["gamma"]) < 1e-9
        assert abs(float(mine["vega"]) / 100.0 - theirs["vega"]) < 1e-9
        assert abs(float(mine["theta"]) / 365.0 - theirs["theta"]) < 1e-9


def test_put_call_greek_relations():
    """gamma, vega, vomma are identical for a call and a put on the same contract; delta differs
    by exactly the discount factor. A sign slip in the put branch shows up here."""
    S, K, T, r, sig, _ = _cols()
    c = G.greeks(S, K, T, r, sig, np.zeros(len(S), dtype=bool))
    p = G.greeks(S, K, T, r, sig, np.ones(len(S), dtype=bool))
    for k in ("gamma", "vega", "vomma", "speed", "zomma", "ultima", "vanna"):
        assert np.max(np.abs(c[k] - p[k])) < 1e-10, k
    assert np.max(np.abs((c["delta"] - p["delta"]) - 1.0)) < 1e-12


# --------------------------------------------------------------------------- #
#  frame-level enrichment: coverage accounting and the band
# --------------------------------------------------------------------------- #
def _chain_fixture():
    """One date, one expiry, a ladder of strikes priced at a KNOWN vol, plus four deliberately
    broken rows that must each be skipped for a DIFFERENT recorded reason."""
    import datetime as dt

    d0 = dt.date(2024, 3, 1)
    exp = dt.date(2024, 4, 19)          # 49 DTE — inside the band
    S, sig = 100.0, 0.28
    r = BS.risk_free_rate(d0)           # the same rate enrich_frame will invert at
    T = (exp - d0).days / 365.0
    rows = []
    for K in [85, 90, 95, 100, 105, 110, 115]:
        for right in ("C", "P"):
            px = float(G.bs_price(S, K, T, r, sig, right == "P"))
            rows.append({"expiration": exp, "strike": float(K), "right": right, "date": d0,
                         "bid": px * 0.99, "ask": px * 1.01, "volume": 100,
                         "open_interest": 1000})
    broken = [
        # no quote (zero bid), penny mid, moneyness far outside the band, expired
        {"expiration": exp, "strike": 100.0, "right": "C", "date": d0, "bid": 0.0,
         "ask": 5.0, "volume": 1, "open_interest": 1},
        {"expiration": exp, "strike": 105.0, "right": "P", "date": d0, "bid": 0.01,
         "ask": 0.02, "volume": 1, "open_interest": 1},
        {"expiration": exp, "strike": 500.0, "right": "C", "date": d0, "bid": 0.30,
         "ask": 0.40, "volume": 1, "open_interest": 1},
        {"expiration": dt.date(2024, 2, 1), "strike": 100.0, "right": "C", "date": d0,
         "bid": 1.0, "ask": 1.2, "volume": 1, "open_interest": 1},
    ]
    return pd.DataFrame(rows + broken), {d0: S}, sig


def test_enrich_frame_recovers_the_true_vol_and_accounts_for_every_row():
    df, spots, true_sig = _chain_fixture()
    derived, raw_daily, cov = G.enrich_frame(df, spots)
    assert cov["rows_in"] == len(df)
    # every single input row is either enriched or skipped with a named reason — no leakage
    assert cov["rows_iv_ok"] + sum(cov["skipped"].values()) == cov["rows_in"], cov
    assert cov["skipped"]["no_quote"] == 1, cov["skipped"]
    assert cov["skipped"]["penny"] == 1, cov["skipped"]
    assert cov["skipped"]["mny_band"] == 1, cov["skipped"]
    assert cov["skipped"]["neg_time"] == 1, cov["skipped"]
    # the ladder was priced at one vol; inversion must recover it on every strike
    assert len(derived) == 14, len(derived)
    assert abs(float(derived["iv"].median()) - true_sig) < 0.02, derived["iv"].describe()
    assert set(G.GREEK_COLS).issubset(derived.columns)
    # p/c ratios come from the UNFILTERED chain, so they see the broken rows too
    assert len(raw_daily) == 1
    assert float(raw_daily["call_oi"].iloc[0]) > 0 and float(raw_daily["put_oi"].iloc[0]) > 0


def test_enrich_frame_marks_missing_spot_rather_than_guessing():
    df, _, _ = _chain_fixture()
    derived, _, cov = G.enrich_frame(df, {})          # no underlying close at all
    assert len(derived) == 0
    assert cov["skipped"]["no_spot"] == cov["rows_in"], cov["skipped"]


# --------------------------------------------------------------------------- #
#  GEX
# --------------------------------------------------------------------------- #
def test_gex_sign_convention_and_profile():
    df, spots, _ = _chain_fixture()
    derived, raw_daily, _ = G.enrich_frame(df, spots)
    prof = G.gex_by_strike(derived)
    assert len(prof) == 7, prof
    # calls contribute positive, puts negative — the stated dealer convention
    calls = derived[derived["right"].astype(str) == "C"]
    puts = derived[derived["right"].astype(str) == "P"]
    assert G.gex_by_strike(calls)["gex"].min() > 0
    assert G.gex_by_strike(puts)["gex"].max() < 0
    # equal call and put OI at every strike => the two sides cancel to ~0 net, measured against
    # the GROSS exposure (the netted profile is itself zero here, so it cannot be the yardstick)
    gross = float((derived["gamma"].astype(float) * derived["open_interest"].astype(float)
                   * 100.0 * derived["spot"].astype(float)).abs().sum())
    assert gross > 0
    assert abs(float(prof["gex"].sum())) < 1e-6 * gross, (prof["gex"].sum(), gross)


def test_zero_gamma_is_found_when_the_book_actually_flips():
    """Calls only above spot, puts only below: net dealer gamma is positive high and negative
    low, so a flip level must exist between them."""
    import datetime as dt

    d0, exp = dt.date(2024, 3, 1), dt.date(2024, 4, 19)
    S, sig = 100.0, 0.28
    r = BS.risk_free_rate(d0)
    T = (exp - d0).days / 365.0
    rows = []
    for K, right in [(105, "C"), (110, "C"), (95, "P"), (90, "P")]:
        px = float(G.bs_price(S, K, T, r, sig, right == "P"))
        rows.append({"expiration": exp, "strike": float(K), "right": right, "date": d0,
                     "bid": px * 0.99, "ask": px * 1.01, "volume": 10, "open_interest": 5000})
    derived, _, _ = G.enrich_frame(pd.DataFrame(rows), {d0: S})
    zg = G.zero_gamma(derived)
    assert zg is not None and 90.0 < zg < 110.0, zg
    # and None rather than a fabricated level when nothing flips (calls only)
    only_calls = derived[derived["right"].astype(str) == "C"]
    assert G.zero_gamma(only_calls) is None


def test_daily_features_shape_and_skew_sign():
    df, spots, _ = _chain_fixture()
    derived, raw_daily, _ = G.enrich_frame(df, spots)
    daily = G.daily_features(derived, raw_daily)
    assert len(daily) == 1
    row = daily.iloc[0]
    for c in ("total_gex", "zero_gamma", "call_wall", "put_wall", "pc_oi", "pc_vol",
              "gex_wall_conc", "skew_25d"):
        assert c in daily.columns, c
    # the fixture is a flat-vol surface, so 25d skew must be ~0 rather than drifting
    assert abs(float(row["skew_25d"])) < 0.02, row["skew_25d"]
    assert abs(float(row["atm_iv_front"]) - 0.28) < 0.02, row["atm_iv_front"]


def test_iv_rank_is_backward_looking_only():
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    iv = np.linspace(0.20, 0.60, 120)
    daily = G.add_iv_rank(pd.DataFrame({"date": dates, "atm_iv_30": iv}), window=60)
    # a strictly rising series: today is always the max SO FAR, so rank pins at 1.0 …
    assert float(daily["iv_rank"].dropna().iloc[-1]) == 1.0
    # … and the first 59 rows have too little history to rank at all (min_periods=60)
    assert daily["iv_rank"].iloc[:59].isna().all()


def test_sanity_flags_fire_rather_than_staying_quiet():
    cov = {"rows_in": 1000, "rows_iv_ok": 50, "iv_at_bound": 30,
           "skipped": {"neg_time": 7, "no_spot": 0}}
    daily = pd.DataFrame({"gex_wall_conc": [0.9] * 10, "zero_gamma": [None] * 10})
    flags = G.sanity_flags(daily, cov)
    joined = " | ".join(flags)
    assert "iv_ok_frac" in joined and "expiration before quote date" in joined, flags
    assert "pegged" in joined and "zero-gamma" in joined, flags
    assert G.sanity_flags(pd.DataFrame({"gex_wall_conc": [0.1] * 10,
                                        "zero_gamma": [100.0] * 10}),
                          {"rows_in": 100, "rows_iv_ok": 80, "iv_at_bound": 0,
                           "skipped": {"neg_time": 0, "no_spot": 0}}) == []


def test_empty_column_guard_fires():
    """The COVERAGE RULE applied to this layer. An all-NaN derived column must announce itself
    here; the 90-DTE tenors did exactly this before they were removed."""
    daily = pd.DataFrame({"gex_wall_conc": [0.1] * 10, "zero_gamma": [100.0] * 10,
                          "atm_iv_180": [np.nan] * 10})
    flags = G.sanity_flags(daily, {"rows_in": 100, "rows_iv_ok": 80, "iv_at_bound": 0,
                                   "skipped": {"neg_time": 0, "no_spot": 0}})
    assert any("atm_iv_180" in f and "empty" in f for f in flags), flags


def test_band_max_dte_matches_what_the_miner_actually_caches():
    """The cache stops at 90 DTE (`theta_bulk.MAX_DTE`). If the miner ever raises that, this
    fails and whoever raises it gets told that the derived tenors can be widened too."""
    from valuation.edge import theta_bulk

    assert G.BAND["max_dte"] == theta_bulk.MAX_DTE, (G.BAND["max_dte"], theta_bulk.MAX_DTE)
    assert max(G.TENORS) < theta_bulk.MAX_DTE, G.TENORS


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:                                            # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} options-greeks tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
