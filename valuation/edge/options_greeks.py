"""
Higher-order greeks, GEX and IV-surface features derived from the LOCAL mined option cache.

WHY THIS EXISTS. `data/options/` holds slim EOD chains — expiration, strike, right, date, bid,
ask, volume, open_interest and nothing else (see `theta_bulk.KEEP`). IV and greeks were
deliberately not stored, so every piece of research that wants them has to re-invert Black-
Scholes on the whole cache first. This module does that inversion ONCE and caches the result in
a separate root (`data/options_derived/`), so the eventual signal work reuses a ready layer.

It makes ZERO vendor API calls. Everything here is arithmetic on files that are already on disk,
plus the underlying close from the existing Sharadar bars path.

WHAT IS AND IS NOT TRUSTWORTHY IN HERE — read this before using an IV out of these files.

  * The IV is inverted from the MID of an EOD bid/ask. That is the market's best estimate of
    value, but on a wide quote the mid is a midpoint of two numbers nobody traded at. Deep ITM
    and deep OTM contracts are exactly where the spread is widest and vega is smallest, so a
    penny of mid error becomes a large vol error. That is why inversion is restricted to a
    pre-registered band (`BAND`) and everything outside it is RECORDED AS SKIPPED rather than
    filled with a number.
  * These are EUROPEAN Black-Scholes greeks on AMERICAN options, with a dividend yield of ZERO.
    For calls on non-payers the early-exercise premium is nil and this is exact; for ITM puts
    and for names with a fat dividend it is a real approximation error, biasing put IV upward.
    It is not corrected here — it is stated, and the affected contracts are identifiable from
    `moneyness`/`right` in the output.
  * Nothing in here has been shown to predict anything. This module builds a cache; whether any
    of it carries signal is a separate, gated question.

UNITS — every greek is the RAW analytic derivative, unscaled:

    delta   dV/dS          per $1 of spot
    gamma   d2V/dS2        per $1^2
    vega    dV/dsigma      per 1.00 of vol (i.e. per 100 vol points)
    theta   dV/dt          per YEAR of calendar time (negative for a long option)
    rho     dV/dr          per 1.00 of rate (i.e. per 100%)
    vanna   d2V/dS dsigma
    charm   d2V/dS dt      delta decay, per year
    vomma   d2V/dsigma2    (a.k.a. volga)
    veta    d2V/dsigma dt  vega decay, per year
    speed   d3V/dS3
    color   d3V/dS2 dt     gamma decay, per year
    zomma   d3V/dS2 dsigma
    ultima  d3V/dsigma3

`blackscholes.greeks()` reports vega/100 and theta/365 instead. Both conventions are defensible;
mixing them silently is not, so this module keeps everything raw and says so. `test_options_
greeks.py` pins the exact relationship between the two, and checks every greek above against a
central finite difference of the analytic price — a hand-rolled third derivative that is quietly
wrong is precisely the silent-corruption failure this project keeps getting bitten by.

GEX SIGN CONVENTION (stated because it is an assumption, not a fact): the standard dealer-gamma
convention is used — dealers are assumed LONG gamma in calls and SHORT gamma in puts, so a
contract contributes `+gamma*OI*100*S` if it is a call and `-gamma*OI*100*S` if it is a put.
That assumption is a market-structure folk theorem, not something this repo has verified. If it
is wrong the sign of every GEX number here flips; the magnitudes and the strike profile do not.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import pickle
from typing import Optional

import numpy as np
import pandas as pd

from . import blackscholes as BS

SCHEMA_VERSION = 4
DERIVED_ROOT = os.path.join("data", "options_derived")

# ---- Pre-registered inversion band ---------------------------------------------------------
# Committed BEFORE looking at any output. Outside this band the mid-price inversion is not
# stable enough to be worth emitting: under a week to expiry vega collapses and a one-tick mid
# error swamps the vol; beyond ~130% / below ~70% moneyness the quote is mostly spread; a mid
# under a nickel is a rounding artefact.
#
# `max_dte` is 90 because the CACHE stops there: `theta_bulk.MAX_DTE = 90` is a deliberate
# mining decision (the live strategy only ever reads the front expiry and the 45-75 DTE band).
# So there is no such thing as a 6-month contract in these files, and a 180-day tenor here would
# be a column that is 100% empty while looking wired — exactly the failure the COVERAGE RULE in
# CLAUDE.md exists to prevent. Term structure beyond ~2 months is NOT derivable from this cache.
BAND = {
    "min_dte": 7,
    "max_dte": 90,
    "mny_lo": 0.70,          # strike / spot
    "mny_hi": 1.30,
    "min_mid": 0.05,
    "max_spread_frac": 1.00,  # (ask-bid)/mid
}

# Grid used to locate the zero-gamma (gamma flip) level, as a fraction of spot.
ZG_LO, ZG_HI, ZG_N = 0.75, 1.25, 51

SKIP_REASONS = ("no_spot", "no_quote", "crossed", "penny", "wide_spread",
                "neg_time", "dte_band", "mny_band",
                "below_intrinsic", "above_max_vol", "iv_unsolved")


# ============================== vectorised Black-Scholes ====================================
try:                                    # scipy is already a hard dependency (requirements.txt)
    from scipy.special import ndtr as _ndtr
except ImportError:                                                      # pragma: no cover
    def _ndtr(x):
        return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(x, dtype=float) / math.sqrt(2.0)))

_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def norm_cdf(x):
    return _ndtr(np.asarray(x, dtype=float))


def norm_pdf(x):
    x = np.asarray(x, dtype=float)
    return _INV_SQRT_2PI * np.exp(-0.5 * x * x)


def _d1d2(S, K, T, r, sigma, q=0.0):
    sq = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sq
    return d1, d1 - sq, sq


def bs_price(S, K, T, r, sigma, is_put, q=0.0):
    """Black-Scholes-Merton price, vectorised. NaN where the inputs are degenerate."""
    S, K, T, r, sigma, is_put = (np.asarray(v, dtype=float) if v is not is_put else np.asarray(v)
                                 for v in (S, K, T, r, sigma, is_put))
    bad = ~((S > 0) & (K > 0) & (T > 0) & (sigma > 0))
    Ss = np.where(bad, 1.0, S)
    Ks = np.where(bad, 1.0, K)
    Ts = np.where(bad, 1.0, T)
    sg = np.where(bad, 0.2, sigma)
    d1, d2, _ = _d1d2(Ss, Ks, Ts, r, sg, q)
    dq, dr = np.exp(-q * Ts), np.exp(-r * Ts)
    call = Ss * dq * norm_cdf(d1) - Ks * dr * norm_cdf(d2)
    put = Ks * dr * norm_cdf(-d2) - Ss * dq * norm_cdf(-d1)
    out = np.where(np.asarray(is_put, dtype=bool), put, call)
    return np.where(bad, np.nan, out)


def implied_vol(price, S, K, T, r, is_put, q=0.0, iters: int = 32):
    """Bisection IV, vectorised. Returns (iv, reason) with NaN iv wherever no vol explains the
    price.

    Bisection rather than Newton for the same reason `blackscholes.implied_vol` uses it: vega is
    near zero for the deep wings a wide chain is full of, and Newton diverges there. Bisection on
    a bracketed range always terminates. A price at or below intrinsic, or above the 500%-vol
    price, is a broken quote — it gets NaN and a reason code, never an invented vol.

    This is the hot loop of the whole job (millions of contract-days), so three things are done
    for speed WITHOUT changing the answer: log(S/K), sqrt(T) and the discount factors are
    hoisted out of the loop (they do not depend on sigma), the put branch comes from put-call
    parity rather than two more normal CDFs, and the iteration count is 32 — bisection over
    [0.005, 5.0] resolves to 1.2e-9, which is four orders of magnitude finer than any IV here
    is meaningful to. 50 iterations were pure waste in an inner loop that runs 2M times.
    """
    price = np.asarray(price, dtype=float)
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    r = np.asarray(r, dtype=float)
    is_put = np.asarray(is_put, dtype=bool)
    price, S, K, T, r, is_put = np.broadcast_arrays(price, S, K, T, r, is_put)

    valid = (np.isfinite(price) & np.isfinite(S) & np.isfinite(K) & np.isfinite(T)
             & (price > 0) & (S > 0) & (K > 0) & (T > 0))
    Ss = np.where(valid, S, 1.0)
    Ks = np.where(valid, K, 1.0)
    Ts = np.where(valid, T, 1.0)
    sqrtT = np.sqrt(Ts)
    logSK = np.log(Ss / Ks)
    fwd = Ss * np.exp(-q * Ts)          # discounted spot
    strike_pv = Ks * np.exp(-r * Ts)    # discounted strike
    drift = (r - q) * Ts

    def _px(sigma):
        sq = sigma * sqrtT
        d1 = (logSK + drift) / sq + 0.5 * sq
        call = fwd * norm_cdf(d1) - strike_pv * norm_cdf(d1 - sq)
        # put-call parity — exact, and half the normal-CDF evaluations
        return np.where(is_put, call - fwd + strike_pv, call)

    reason = np.full(price.shape, "", dtype=object)
    lo_p = _px(np.full(price.shape, BS.IV_LO))
    hi_p = _px(np.full(price.shape, BS.IV_HI))

    ok = valid & np.isfinite(lo_p) & np.isfinite(hi_p)
    below = ok & (price <= lo_p)
    above = ok & (price >= hi_p)
    solvable = ok & ~below & ~above
    reason[below] = "below_intrinsic"
    reason[above] = "above_max_vol"
    reason[~ok] = "iv_unsolved"

    lo = np.full(price.shape, BS.IV_LO)
    hi = np.full(price.shape, BS.IV_HI)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        too_high = _px(mid) > price
        hi = np.where(too_high, mid, hi)
        lo = np.where(too_high, lo, mid)
    iv = np.where(solvable, 0.5 * (lo + hi), np.nan)
    return iv, reason


def greeks(S, K, T, r, sigma, is_put, q=0.0) -> dict:
    """All fourteen greeks, vectorised, as RAW analytic derivatives (see module docstring)."""
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    r = np.asarray(r, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    is_put = np.asarray(is_put, dtype=bool)

    bad = ~((S > 0) & (K > 0) & (T > 0) & (sigma > 0))
    Ss, Ks, Ts = (np.where(bad, 1.0, S), np.where(bad, 1.0, K), np.where(bad, 1.0, T))
    sg = np.where(bad, 0.2, sigma)
    d1, d2, sq = _d1d2(Ss, Ks, Ts, r, sg, q)
    pdf = norm_pdf(d1)
    dq, dr = np.exp(-q * Ts), np.exp(-r * Ts)
    Nd1, Nd2 = norm_cdf(d1), norm_cdf(d2)
    sqrtT = np.sqrt(Ts)

    delta = np.where(is_put, dq * (Nd1 - 1.0), dq * Nd1)
    gamma = dq * pdf / (Ss * sq)
    vega = Ss * dq * pdf * sqrtT                                     # per 1.00 of vol
    common = -(Ss * dq * pdf * sg) / (2.0 * sqrtT)
    theta = np.where(is_put,
                     common + r * Ks * dr * norm_cdf(-d2) - q * Ss * dq * norm_cdf(-d1),
                     common - r * Ks * dr * Nd2 + q * Ss * dq * Nd1)  # per year
    rho = np.where(is_put, -Ks * Ts * dr * norm_cdf(-d2), Ks * Ts * dr * Nd2)

    vanna = -dq * pdf * d2 / sg
    charm_common = dq * pdf * (2.0 * (r - q) * Ts - d2 * sq) / (2.0 * Ts * sq)
    charm = np.where(is_put,
                     -q * dq * norm_cdf(-d1) - charm_common,
                     q * dq * Nd1 - charm_common)
    vomma = vega * d1 * d2 / sg
    # veta and color are quoted in the literature as derivatives with respect to TIME TO
    # EXPIRY; this module reports every time-derivative with respect to CALENDAR TIME, like
    # theta and charm. Hence the sign flip. It is not cosmetic — the finite-difference tests
    # caught both of these pointing the wrong way when they were transcribed as published.
    veta = Ss * dq * pdf * sqrtT * (q + ((r - q) * d1) / sq - (1.0 + d1 * d2) / (2.0 * Ts))

    speed = -gamma / Ss * (d1 / sq + 1.0)
    color = dq * pdf / (2.0 * Ss * Ts * sq) * (
        2.0 * q * Ts + 1.0 + (2.0 * (r - q) * Ts - d2 * sq) * d1 / sq)
    zomma = gamma * (d1 * d2 - 1.0) / sg
    ultima = -vega / (sg * sg) * (d1 * d2 * (1.0 - d1 * d2) + d1 * d1 + d2 * d2)

    out = {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho,
           "vanna": vanna, "charm": charm, "vomma": vomma, "veta": veta,
           "speed": speed, "color": color, "zomma": zomma, "ultima": ultima}
    return {k: np.where(bad, np.nan, v) for k, v in out.items()}


GREEK_COLS = ("delta", "gamma", "vega", "theta", "rho", "vanna", "charm", "vomma",
              "veta", "speed", "color", "zomma", "ultima")


# ============================== per-contract enrichment =====================================
def _to_pydate(x) -> dt.date:
    """datetime.date from whatever the cache stores (date objects or datetime64)."""
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    return pd.Timestamp(x).date()


def _is_put(col) -> np.ndarray:
    """Boolean put mask without touching a string per row — the cache stores `right` as a
    two-value category, so the answer is one lookup per CATEGORY, not per row."""
    s = pd.Series(col)
    if isinstance(s.dtype, pd.CategoricalDtype):
        put_map = np.array([str(c).upper().startswith("P") for c in s.cat.categories] + [False])
        codes = s.cat.codes.to_numpy()
        return put_map[np.where(codes < 0, len(put_map) - 1, codes)]
    vals, inv = np.unique(s.to_numpy().astype(str), return_inverse=True)
    return np.array([str(v).upper().startswith("P") for v in vals])[inv]


def enrich_frame(df: pd.DataFrame, spots: dict, q: float = 0.0):
    """Invert IV and compute the greek stack for one (symbol, year) chain.

    Returns (derived, raw_daily, coverage):
      derived   — one row per contract-day that produced a VALID IV, with the full greek stack.
      raw_daily — per-date put/call OI and volume totals from the UNFILTERED chain (these need
                  no IV, so they are computed before the band filter throws two thirds of the
                  rows away).
      coverage  — row counts by skip reason. Nothing is silently dropped.
    """
    n_in = int(len(df))
    cov = {"rows_in": n_in, "rows_iv_ok": 0, "skipped": {k: 0 for k in SKIP_REASONS},
           "dates_in": 0, "dates_out": 0}
    if n_in == 0:
        return (pd.DataFrame(), pd.DataFrame(), cov)

    # Everything below the DataFrame is deliberately numpy on UNIQUE keys rather than pandas
    # per row. A chain-year is ~2M rows and a `.dt.date.map(lambda ...)` over it is 2M Python
    # calls for 252 distinct answers — that one line was most of the runtime of the whole job.
    date_u, inv_d = np.unique(np.asarray(df["date"].values), return_inverse=True)
    exp_u, inv_e = np.unique(np.asarray(df["expiration"].values), return_inverse=True)
    date64_u = pd.to_datetime(pd.Index(date_u)).values
    exp64_u = pd.to_datetime(pd.Index(exp_u)).values
    cov["dates_in"] = int(len(date_u))

    strike = pd.to_numeric(df["strike"], errors="coerce").to_numpy(dtype="float64")
    bid = pd.to_numeric(df["bid"], errors="coerce").to_numpy(dtype="float64")
    ask = pd.to_numeric(df["ask"], errors="coerce").to_numpy(dtype="float64")
    volume = pd.to_numeric(df.get("volume"), errors="coerce").fillna(0).to_numpy(dtype="float64")
    # -1 IS A MISSING-DATA SENTINEL, NOT AN OPEN INTEREST. `theta_bulk` fills the OI merge miss
    # with -1 (`.fillna(-1).astype("int32")`), and 11% of the cache — including EVERY row of
    # AAPL 2020 — carries it. Treated as a number it silently flips the sign of that contract's
    # gamma contribution and poisons the put/call ratio. It becomes NaN here, is counted, and
    # every aggregate below is computed on known OI only.
    oi_raw = pd.to_numeric(df.get("open_interest"),
                           errors="coerce").fillna(-1).to_numpy(dtype="float64")
    oi_missing = ~np.isfinite(oi_raw) | (oi_raw < 0)
    oi = np.where(oi_missing, np.nan, oi_raw)
    cov["oi_missing_rows"] = int(oi_missing.sum())
    is_put_all = _is_put(df["right"])

    # --- per-date aggregates that need no IV (computed on the FULL chain) -------------------
    n_u = len(date_u)
    oi_known = np.where(oi_missing, 0.0, oi_raw)          # sums over KNOWN OI only
    known = (~oi_missing).astype(float)
    raw_daily = pd.DataFrame({
        "date": date64_u,
        "call_oi": np.bincount(inv_d, weights=np.where(is_put_all, 0.0, oi_known), minlength=n_u),
        "put_oi": np.bincount(inv_d, weights=np.where(is_put_all, oi_known, 0.0), minlength=n_u),
        "call_vol": np.bincount(inv_d, weights=np.where(is_put_all, 0.0, volume), minlength=n_u),
        "put_vol": np.bincount(inv_d, weights=np.where(is_put_all, volume, 0.0), minlength=n_u),
        "chain_rows": np.bincount(inv_d, minlength=n_u).astype(float),
        # how much of that date's chain had a real OI at all — a p/c ratio built on 5% of the
        # chain is not the same statistic as one built on all of it, and must not look like it
        "oi_known_rows": np.bincount(inv_d, weights=known, minlength=n_u),
    })
    raw_daily["oi_coverage"] = raw_daily["oi_known_rows"] / raw_daily["chain_rows"]
    # A date with no OI anywhere has no put/call OI ratio — not a ratio of zeros.
    for c in ("call_oi", "put_oi"):
        raw_daily[c] = raw_daily[c].where(raw_daily["oi_known_rows"] > 0)

    # --- band / quote filtering, one reason per row ------------------------------------------
    spot_u = np.array([float(spots.get(_to_pydate(x), np.nan)) if
                       spots.get(_to_pydate(x)) is not None else np.nan for x in date_u])
    spot = spot_u[inv_d]
    dte = ((exp64_u[inv_e] - date64_u[inv_d]) / np.timedelta64(1, "D")).astype("float64")
    mid = (bid + ask) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        spread_frac = np.where(mid > 0, (ask - bid) / np.where(mid > 0, mid, np.nan), np.inf)
        mny = strike / spot

    reason = np.full(n_in, "", dtype=object)

    def _mark(mask, why):
        m = np.asarray(mask) & (reason == "")
        reason[m] = why
        return m

    _mark(~np.isfinite(spot), "no_spot")
    _mark(~np.isfinite(bid) | ~np.isfinite(ask) | (bid <= 0) | (ask <= 0), "no_quote")
    _mark(ask < bid, "crossed")
    _mark(mid < BAND["min_mid"], "penny")
    _mark(spread_frac > BAND["max_spread_frac"], "wide_spread")
    _mark(dte < 0, "neg_time")
    _mark((dte < BAND["min_dte"]) | (dte > BAND["max_dte"]), "dte_band")
    _mark((mny < BAND["mny_lo"]) | (mny > BAND["mny_hi"]), "mny_band")

    keep = reason == ""
    if not keep.any():
        for k in SKIP_REASONS:
            cov["skipped"][k] = int((reason == k).sum())
        return (pd.DataFrame(), raw_daily, cov)

    k_idx = np.flatnonzero(keep)
    # one rate per DATE (FRED DGS3MO, already cached on disk by blackscholes)
    rate_u = np.array([BS.risk_free_rate(_to_pydate(x)) for x in date_u], dtype="float64")
    rate = rate_u[inv_d][k_idx]

    iv, iv_reason = implied_vol(mid[k_idx], spot[k_idx], strike[k_idx],
                                dte[k_idx] / 365.0, rate, is_put_all[k_idx], q)
    bad_iv = ~np.isfinite(iv)
    reason[k_idx[bad_iv]] = np.where(iv_reason[bad_iv] == "", "iv_unsolved", iv_reason[bad_iv])

    good = np.flatnonzero(np.isfinite(iv))
    g_idx = k_idx[good]
    iv_ok = iv[good]
    g = greeks(spot[g_idx], strike[g_idx], dte[g_idx] / 365.0, rate[good], iv_ok,
               is_put_all[g_idx], q)

    out = pd.DataFrame({
        "date": date64_u[inv_d][g_idx],
        "expiration": exp64_u[inv_e][g_idx],
        "strike": strike[g_idx].astype("float32"),
        "right": pd.Categorical(np.where(is_put_all[g_idx], "P", "C"), categories=["C", "P"]),
        "dte": dte[g_idx].astype("int16"),
        "spot": spot[g_idx].astype("float32"),
        "moneyness": mny[g_idx].astype("float32"),
        "mid": mid[g_idx].astype("float32"),
        "spread_frac": spread_frac[g_idx].astype("float32"),
        "volume": volume[g_idx].astype("float32"),
        "open_interest": oi[g_idx].astype("float32"),
        "risk_free": rate[good].astype("float32"),
        "iv": iv_ok.astype("float32"),
        **{k: v.astype("float32") for k, v in g.items()},
    })

    for k in SKIP_REASONS:
        cov["skipped"][k] = int((reason == k).sum())
    cov["rows_iv_ok"] = int(len(out))
    cov["dates_out"] = int(pd.unique(out["date"]).size) if len(out) else 0
    cov["iv_at_bound"] = int(((iv_ok <= BS.IV_LO * 1.01) | (iv_ok >= BS.IV_HI * 0.99)).sum())
    return (out, raw_daily, cov)


# ============================== GEX and the daily surface ===================================
def _dealer_sign(right_is_call) -> np.ndarray:
    """Dealer-gamma convention: long gamma in calls, short in puts. See module docstring — this
    is an assumption about who holds what, not a measured fact."""
    return np.where(right_is_call, 1.0, -1.0)


def gex_by_strike(day: pd.DataFrame) -> pd.DataFrame:
    """GEX profile for ONE date: gamma * OI * 100 * S, signed, summed per strike."""
    if day is None or len(day) == 0:
        return pd.DataFrame(columns=["strike", "gex", "call_gamma_oi", "put_gamma_oi"])
    is_call = day["right"].astype(str).str.startswith("C").values
    g = day["gamma"].values.astype(float)
    # Unknown OI (the -1 sentinel, stored as NaN) contributes NOTHING. It is not zero interest —
    # it is an unmeasured contract, and `oi_coverage` on the daily frame says how many there were.
    oi = np.nan_to_num(day["open_interest"].values.astype(float), nan=0.0)
    S = float(day["spot"].iloc[0])
    contrib = _dealer_sign(is_call) * g * oi * 100.0 * S
    prof = pd.DataFrame({
        "strike": day["strike"].values.astype(float),
        "gex": contrib,
        "call_gamma_oi": np.where(is_call, g * oi, 0.0),
        "put_gamma_oi": np.where(is_call, 0.0, g * oi),
    }).groupby("strike", as_index=False).sum()
    return prof.sort_values("strike").reset_index(drop=True)


def zero_gamma(day: pd.DataFrame, lo: float = ZG_LO, hi: float = ZG_HI,
               n: int = ZG_N) -> Optional[float]:
    """Spot level at which net dealer gamma flips sign.

    Computed properly rather than by reading it off the strike profile: every contract's gamma
    is RE-EVALUATED on a grid of hypothetical spots (IV and time held fixed) and the net is
    interpolated to its zero crossing. Holding IV fixed while moving spot is itself an
    assumption — a real surface would move with it — but it is the standard construction and it
    is at least explicit. Returns None when the net never crosses zero on the grid.
    """
    if day is None or len(day) == 0:
        return None
    S = float(day["spot"].iloc[0])
    if not np.isfinite(S) or S <= 0:
        return None
    K = day["strike"].values.astype(float)[:, None]
    T = (day["dte"].values.astype(float) / 365.0)[:, None]
    r = day["risk_free"].values.astype(float)[:, None]
    sig = day["iv"].values.astype(float)[:, None]
    sign = _dealer_sign(day["right"].astype(str).str.startswith("C").values)[:, None]
    oi = np.nan_to_num(day["open_interest"].values.astype(float), nan=0.0)[:, None]
    if not np.any(oi > 0):
        return None                      # no known open interest -> no gamma book to flip

    grid = np.linspace(lo * S, hi * S, n)[None, :]
    d1, _, sq = _d1d2(grid, K, T, r, sig)
    gam = norm_pdf(d1) / (grid * sq)
    net = np.nansum(sign * gam * oi * 100.0 * grid, axis=0)
    if not np.isfinite(net).any():
        return None
    gs = grid[0]
    sgn = np.sign(net)
    cross = np.flatnonzero(sgn[:-1] * sgn[1:] < 0)
    if cross.size == 0:
        return None
    # nearest crossing to today's spot — a surface can flip more than once
    j = cross[np.argmin(np.abs(gs[cross] - S))]
    x0, x1, y0, y1 = gs[j], gs[j + 1], net[j], net[j + 1]
    if y1 == y0:
        return float(x0)
    return float(x0 - y0 * (x1 - x0) / (y1 - y0))


def _interp_at(x, y, target) -> Optional[float]:
    """Linear interpolation of y at `target`, only WITHIN the observed range of x."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size == 0:
        return None
    o = np.argsort(x)
    x, y = x[o], y[o]
    if target < x[0] or target > x[-1]:
        return None
    return float(np.interp(target, x, y))


# Only tenors the 90-DTE cache can actually reach. 90 and 180 were tried and came back 99.9%
# and 100% empty respectively — see the BAND note.
TENORS = (14, 30, 60)


def daily_features(derived: pd.DataFrame, raw_daily: pd.DataFrame) -> pd.DataFrame:
    """One row per date: GEX summary, ATM-IV term structure, 25-delta skew, p/c ratios."""
    if derived is None or len(derived) == 0:
        base = (raw_daily.copy() if raw_daily is not None and len(raw_daily)
                else pd.DataFrame(columns=["date"]))
        return base
    rows = []
    for day_dt, day in derived.groupby("date", observed=True, sort=True):
        S = float(day["spot"].iloc[0])
        oi_known = float(np.isfinite(day["open_interest"].astype(float)).mean())
        prof = gex_by_strike(day)
        tot_gex = float(prof["gex"].sum())
        abs_gex = float(prof["gex"].abs().sum())
        top_strike = (float(prof.loc[prof["gex"].abs().idxmax(), "strike"])
                      if len(prof) else np.nan)
        wall_conc = float(prof["gex"].abs().max() / abs_gex) if abs_gex > 0 else np.nan
        cw = (float(prof.loc[prof["call_gamma_oi"].idxmax(), "strike"])
              if len(prof) and prof["call_gamma_oi"].max() > 0 else np.nan)
        pw = (float(prof.loc[prof["put_gamma_oi"].idxmax(), "strike"])
              if len(prof) and prof["put_gamma_oi"].max() > 0 else np.nan)
        zg = zero_gamma(day)

        # ATM IV per expiry: mean of the nearest-strike call and put
        day = day.assign(_ad=(day["strike"].astype(float) - S).abs())
        atm = (day.sort_values("_ad")
                  .drop_duplicates(["expiration", "right"])
                  .groupby("expiration", as_index=False)
                  .agg(atm_iv=("iv", "mean"), dte=("dte", "first")))
        term = {f"atm_iv_{t}": _interp_at(atm["dte"], atm["atm_iv"], t) for t in TENORS}
        front = (float(atm.sort_values("dte")["atm_iv"].iloc[0]) if len(atm) else None)

        # 25-delta skew on the expiry nearest 30 DTE (only if one exists in 15..60)
        sk = cs = ps = None
        cand = day[(day["dte"] >= 15) & (day["dte"] <= 60)]
        if len(cand):
            exp_pick = cand.assign(_dd=(cand["dte"] - 30).abs()).sort_values("_dd")["expiration"].iloc[0]
            e = cand[cand["expiration"] == exp_pick]
            calls = e[e["right"].astype(str).str.startswith("C")]
            puts = e[e["right"].astype(str).str.startswith("P")]
            cs = _interp_at(calls["delta"].astype(float), calls["iv"].astype(float), 0.25)
            ps = _interp_at(puts["delta"].astype(float).abs(), puts["iv"].astype(float), 0.25)
            if cs is not None and ps is not None:
                sk = ps - cs

        # With no known open interest there IS no gamma exposure to report. Emitting 0.0 would
        # read as "the dealers are flat" instead of "we do not know", which is exactly the kind
        # of quiet fiction the coverage rule exists to stop.
        blind = oi_known <= 0.0
        rows.append({
            "date": day_dt, "spot": S,
            "n_iv": int(len(day)),
            "oi_coverage_iv": oi_known,
            "total_gex": np.nan if blind else tot_gex,
            "gex_per_1pct": np.nan if blind else tot_gex * S * 0.01,
            "gex_top_strike": np.nan if blind else top_strike,
            "gex_wall_conc": np.nan if blind else wall_conc,
            "call_wall": np.nan if blind else cw,
            "put_wall": np.nan if blind else pw,
            "zero_gamma": zg,
            "zero_gamma_vs_spot": (zg / S - 1.0) if zg else np.nan,
            "atm_iv_front": front,
            "skew_25d": sk, "iv_call_25d": cs, "iv_put_25d": ps,
            **term,
        })
    out = pd.DataFrame(rows)
    if "atm_iv_30" in out and "atm_iv_60" in out:
        out["term_slope_60_30"] = out["atm_iv_60"] - out["atm_iv_30"]
    if raw_daily is not None and len(raw_daily):
        rd = raw_daily.copy()
        rd["date"] = pd.to_datetime(rd["date"])
        out = out.merge(rd, on="date", how="outer").sort_values("date").reset_index(drop=True)
        out["pc_oi"] = out["put_oi"] / out["call_oi"].replace(0, np.nan)
        out["pc_vol"] = out["put_vol"] / out["call_vol"].replace(0, np.nan)
    return out


def add_iv_rank(daily: pd.DataFrame, window: int = 252, col: str = "atm_iv_30") -> pd.DataFrame:
    """Trailing IV rank and percentile of the 30-day ATM IV.

    The window is the trailing `window` sessions ENDING ON and INCLUDING today, which is the
    conventional definition of IV rank (where today's vol sits in the past year's range). It
    uses nothing after date t, so it is point-in-time safe; it is not, however, a "past only"
    statistic, and a study that wants one should shift it by a day.
    """
    if daily is None or len(daily) == 0 or col not in daily.columns:
        return daily
    d = daily.sort_values("date").reset_index(drop=True)
    s = pd.to_numeric(d[col], errors="coerce")
    roll = s.rolling(window, min_periods=60)
    lo, hi = roll.min(), roll.max()
    d["iv_rank"] = np.where((hi - lo) > 0, (s - lo) / (hi - lo), np.nan)
    d["iv_pct"] = s.rolling(window, min_periods=60).rank(pct=True)
    return d


# ============================== sanity (never silently green) ================================
def sanity_flags(daily: pd.DataFrame, cov: dict) -> list:
    """Cheap checks that say a derived layer is SANE, not merely present.

    Same idea as `fundamental_panel.sanity_check`: coverage proves a column is populated, this
    asks whether the numbers are believable. A flag here is something to investigate, not
    something to silence.
    """
    flags = []
    rows_in = max(1, int(cov.get("rows_in", 0)))
    ok_frac = cov.get("rows_iv_ok", 0) / rows_in
    if ok_frac < 0.15:
        flags.append(f"iv_ok_frac {ok_frac:.1%} of raw rows (<15%)")
    if cov.get("skipped", {}).get("neg_time", 0):
        flags.append(f"{cov['skipped']['neg_time']} rows with expiration before quote date")
    if cov.get("skipped", {}).get("no_spot", 0) > 0.05 * rows_in:
        flags.append(f"{cov['skipped']['no_spot']} rows had no underlying close")
    if cov.get("iv_at_bound", 0) > 0.01 * max(1, cov.get("rows_iv_ok", 1)):
        flags.append(f"{cov['iv_at_bound']} solved IVs sit on the 0.5%/500% bracket")
    miss = cov.get("oi_missing_rows", 0)
    if miss and miss > 0.02 * rows_in:
        flags.append(f"open interest missing (-1 sentinel) on {miss / rows_in:.0%} of raw rows")
    if daily is not None and len(daily) and "oi_coverage_iv" in daily:
        blind = float(pd.to_numeric(daily["oi_coverage_iv"], errors="coerce").le(0).mean())
        if blind > 0.02:
            flags.append(f"no open interest at all on {blind:.0%} of dates — GEX is blank there")
    if daily is not None and len(daily) and "gex_wall_conc" in daily:
        peg = float(pd.to_numeric(daily["gex_wall_conc"], errors="coerce").gt(0.5).mean())
        if peg > 0.25:
            flags.append(f"GEX pegged to one strike on {peg:.0%} of dates")
        zg = pd.to_numeric(daily.get("zero_gamma"), errors="coerce")
        if len(zg) and float(zg.isna().mean()) > 0.5:
            flags.append(f"zero-gamma not found on {float(zg.isna().mean()):.0%} of dates")
    # The COVERAGE RULE, applied to this layer: a derived column that is essentially empty is
    # the single failure mode this project keeps repeating (roe/roic/beta/growth_accel were all
    # wired and all empty for years). It is caught HERE rather than by whoever consumes it.
    if daily is not None and len(daily):
        for c in daily.columns:
            if c in ("date",) or not pd.api.types.is_numeric_dtype(daily[c]):
                continue
            na = float(pd.to_numeric(daily[c], errors="coerce").isna().mean())
            if na > 0.95:
                flags.append(f"column {c} is {na:.0%} empty")
    return flags


# ============================== per-symbol driver ============================================
def source_signature(sym: str, options_root: str) -> dict:
    """(year -> size+mtime) of the miner's files, so a re-mined name is re-enriched."""
    sig = {}
    d = os.path.join(options_root, sym)
    if not os.path.isdir(d):
        return sig
    for f in sorted(os.listdir(d)):
        if f.endswith(".pkl") and "-" in f:
            yr = f.rsplit("-", 1)[-1][:-4]
            try:
                st = os.stat(os.path.join(d, f))
            except OSError:
                continue
            sig[yr] = {"size": int(st.st_size), "mtime": int(st.st_mtime)}
    return sig


def _atomic_pickle(obj, path: str):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def _atomic_json(obj, path: str):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    os.replace(tmp, path)


def enrich_symbol(sym: str, spots: dict, options_root: str, out_root: str,
                  q: float = 0.0, write_contracts: bool = True) -> dict:
    """Derive one symbol end to end. READ-ONLY on `options_root`; writes only under `out_root`."""
    src_dir = os.path.join(options_root, sym)
    dst_dir = os.path.join(out_root, sym)
    os.makedirs(dst_dir, exist_ok=True)
    sig = source_signature(sym, options_root)

    cov_all = {"symbol": sym, "schema_version": SCHEMA_VERSION, "years": {},
               "source_signature": sig, "band": dict(BAND), "q_dividend_yield": q,
               "rows_in": 0, "rows_iv_ok": 0, "oi_missing_rows": 0,
               "skipped": {k: 0 for k in SKIP_REASONS}, "iv_at_bound": 0}
    dailies = []
    for yr in sorted(sig):
        path = os.path.join(src_dir, f"{sym}-{yr}.pkl")
        try:
            with open(path, "rb") as f:
                raw = pickle.load(f)
        except (OSError, pickle.UnpicklingError, EOFError) as e:
            cov_all["years"][yr] = {"error": f"{type(e).__name__}"}
            continue
        derived, raw_daily, cov = enrich_frame(raw, spots, q)
        if write_contracts and len(derived):
            _atomic_pickle(derived, os.path.join(dst_dir, f"{sym}-{yr}.pkl"))
        if len(derived) or len(raw_daily):
            dailies.append(daily_features(derived, raw_daily))
        cov_all["years"][yr] = cov
        cov_all["rows_in"] += cov["rows_in"]
        cov_all["rows_iv_ok"] += cov["rows_iv_ok"]
        cov_all["iv_at_bound"] += cov.get("iv_at_bound", 0)
        cov_all["oi_missing_rows"] += cov.get("oi_missing_rows", 0)
        for k in SKIP_REASONS:
            cov_all["skipped"][k] += cov["skipped"].get(k, 0)

    daily = pd.DataFrame()
    if dailies:
        daily = pd.concat(dailies, ignore_index=True).sort_values("date").reset_index(drop=True)
        daily = add_iv_rank(daily)
        _atomic_pickle(daily, os.path.join(dst_dir, f"{sym}-daily.pkl"))

    cov_all["dates"] = int(len(daily))
    cov_all["iv_ok_frac"] = (cov_all["rows_iv_ok"] / cov_all["rows_in"]) if cov_all["rows_in"] else 0.0
    # Which risk-free curve actually priced these contracts. An empty rate cache means
    # blackscholes fell back to its coarse hard-coded schedule (flat 2% for all of 2022, when
    # the real 3-month bill went 0.06% -> 4.4%), and that must never be invisible.
    cov_all["rate_cache_obs"] = len(BS._RATE_CACHE)
    cov_all["rate_source"] = ("dgs3mo daily series" if BS._RATE_CACHE
                              else "COARSE FALLBACK SCHEDULE")
    cov_all["flags"] = sanity_flags(daily, cov_all)
    if not BS._RATE_CACHE:
        cov_all["flags"].append("priced with the coarse fallback rate schedule, not a real "
                                "3-month Treasury series")
    _atomic_json(cov_all, os.path.join(dst_dir, "coverage.json"))
    return cov_all


def already_enriched(sym: str, options_root: str, out_root: str) -> bool:
    """True when a coverage record exists for the CURRENT source files and schema."""
    p = os.path.join(out_root, sym, "coverage.json")
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8") as f:
            cov = json.load(f)
    except (OSError, ValueError):
        return False
    if cov.get("schema_version") != SCHEMA_VERSION:
        return False
    return cov.get("source_signature") == source_signature(sym, options_root)
