"""
Black-Scholes implied vol + greeks, computed locally from the EOD chain.

WHY LOCAL RATHER THAN THE VENDOR'S GREEKS. ThetaData does serve delta/IV, but only per-expiry
and only as tick data: one expiry on one day is 2,246,496 rows, and even coarsened to a
one-hour window it is a separate call per expiry. A backtest over ~40 symbols x ~100 dates x
~10 expiries would be ~40,000 calls at ~1.1s each - roughly twelve hours - against ONE call per
symbol-date for the quote chain. Computing greeks from the mid we already have is not a
shortcut; it is the only version of this that finishes.

The vendor's greeks are still used, as an INDEPENDENT CHECK on this implementation rather than
as an input (see `validate_against_vendor`). A hand-rolled pricer that is quietly wrong is
exactly the silent-corruption failure this project keeps getting bitten by, so it is verified
against a reference rather than trusted.

RISK-FREE RATE comes from FRED's 3-month Treasury (DGS3MO), which is free - deliberately not
ThetaData's paid rate tier. It is fetched once, cached, and falls back to a fixed schedule if
FRED is unreachable, because a missing rate must not silently become 0% (that would bias every
call delta downward and every put delta up).

IMPLIED VOL is solved by bisection, not Newton. Newton is faster but diverges for deep ITM/OTM
contracts where vega is nearly zero - precisely the contracts a wide chain is full of. Bisection
on a bracketed range always terminates, and returns None rather than a garbage root when the
price is outside the no-arbitrage bounds.
"""
from __future__ import annotations

import math
import os
from typing import Optional

IV_LO, IV_HI = 0.005, 5.0       # 0.5% to 500% vol - anything outside is a bad quote, not a vol
IV_TOL = 1e-4
IV_MAX_ITER = 40        # bisection over [0.005, 5] reaches 1e-4 in ~16 halvings;
                        # 100 was pure waste in the inner loop of every chain
MIN_T = 1.0 / 365.0             # under a day to expiry, greeks are meaningless

_RATE_CACHE = {}
_RATES_TRIED = False    # load ONCE per process, success or failure
FRED_CSV = ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS3MO"
            "&cosd=1995-01-01")
# Fallback if FRED is unreachable. Coarse but never silently zero.
_FALLBACK_RATES = ((2001, 0.035), (2003, 0.010), (2006, 0.048), (2008, 0.020),
                   (2009, 0.002), (2016, 0.005), (2018, 0.020), (2020, 0.004),
                   (2022, 0.020), (2023, 0.050), (2025, 0.042))


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bs_price(S, K, T, r, sigma, right="C", q=0.0) -> Optional[float]:
    """Black-Scholes-Merton price. `right` starts with C or P."""
    try:
        S, K, T, r, sigma = float(S), float(K), float(T), float(r), float(sigma)
    except (TypeError, ValueError):
        return None
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return None
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if str(right).upper().startswith("P"):
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)
    return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)


def implied_vol(price, S, K, T, r, right="C", q=0.0) -> Optional[float]:
    """Bisection IV. Returns None when the price violates no-arbitrage bounds.

    Returning None matters: a contract whose mid sits below intrinsic has a broken quote, and
    inventing a vol for it would push a fabricated number into every downstream signal.
    """
    try:
        price, S, K, T = float(price), float(S), float(K), float(T)
    except (TypeError, ValueError):
        return None
    if price <= 0 or S <= 0 or K <= 0 or T < MIN_T:
        return None
    lo_p = bs_price(S, K, T, r, IV_LO, right, q)
    hi_p = bs_price(S, K, T, r, IV_HI, right, q)
    if lo_p is None or hi_p is None:
        return None
    if price <= lo_p:
        return None                      # at or below intrinsic: no positive vol explains it
    if price >= hi_p:
        return None                      # above the 500%-vol price: bad quote, not a vol
    lo, hi = IV_LO, IV_HI
    for _ in range(IV_MAX_ITER):
        mid = 0.5 * (lo + hi)
        pm = bs_price(S, K, T, r, mid, right, q)
        if pm is None:
            return None
        if abs(pm - price) < IV_TOL:
            return mid
        if pm > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def greeks(S, K, T, r, sigma, right="C", q=0.0) -> dict:
    """delta, gamma, vega, theta. Gamma is computed from IV exactly as the mandate specifies."""
    try:
        S, K, T, r, sigma = float(S), float(K), float(T), float(r), float(sigma)
    except (TypeError, ValueError):
        return {}
    if S <= 0 or K <= 0 or T < MIN_T or sigma <= 0:
        return {}
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sq
    d2 = d1 - sq
    disc_q, disc_r = math.exp(-q * T), math.exp(-r * T)
    is_put = str(right).upper().startswith("P")
    delta = disc_q * (_norm_cdf(d1) - 1.0) if is_put else disc_q * _norm_cdf(d1)
    gamma = disc_q * _norm_pdf(d1) / (S * sq)
    vega = S * disc_q * _norm_pdf(d1) * math.sqrt(T) / 100.0        # per 1 vol point
    theta_common = -(S * disc_q * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
    if is_put:
        theta = (theta_common + q * S * disc_q * _norm_cdf(-d1)
                 + r * K * disc_r * _norm_cdf(-d2)) / 365.0
    else:
        theta = (theta_common - q * S * disc_q * _norm_cdf(d1)
                 - r * K * disc_r * _norm_cdf(d2)) / 365.0
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def risk_free_rate(date, cache_path: Optional[str] = None) -> float:
    """3-month Treasury on/just before `date`, as a decimal. FRED, free; never silently zero."""
    import datetime as dt

    d = date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date)[:10])
    global _RATES_TRIED
    if not _RATE_CACHE and not _RATES_TRIED:
        # Load ONCE. Guarding only on an empty cache meant a FAILED fetch was retried on every
        # single call - measured at 19.7s then 60.3s per call, which was essentially the entire
        # runtime of the backtest. It presented as slow option maths; it was a network round
        # trip inside the inner loop.
        _RATES_TRIED = True
        _load_rates(cache_path)
    if _RATE_CACHE:
        key = max((k for k in _RATE_CACHE if k <= d), default=None)
        if key is not None:
            return _RATE_CACHE[key]
    r = 0.02
    for yr, val in _FALLBACK_RATES:
        if d.year >= yr:
            r = val
    return r


def _load_rates(cache_path: Optional[str] = None):
    import csv
    import datetime as dt

    # Repo-anchored, not relative. A relative path resolved against whatever the working
    # directory happened to be, so the cache was never found and never persisted.
    _here = os.path.dirname(os.path.abspath(__file__))
    _repo = os.path.dirname(os.path.dirname(_here))
    path = cache_path or os.path.join(_repo, "data", "bulk", "prepared", "dgs3mo.csv")
    if not os.path.exists(path):
        _alt = os.path.join("C:\\Users\\donni\\Downloads\\valuation-tool", "data", "bulk", "prepared", "dgs3mo.csv")
        if os.path.exists(_alt):
            path = _alt
    text = None
    if os.path.exists(path):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            text = None
    if text is None:
        try:
            import requests
            resp = requests.get(FRED_CSV, timeout=15,
                                headers={"User-Agent": "Valquo research"})
            if resp.status_code == 200 and "," in resp.text:
                text = resp.text
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                except OSError:
                    pass
        except Exception:                                            # noqa: BLE001
            return
    if not text:
        return
    rdr = csv.reader(text.splitlines())
    header = next(rdr, None) or []
    di = 0
    vi = 1 if len(header) > 1 else 0
    for row in rdr:
        if len(row) <= vi:
            continue
        try:
            d = dt.date.fromisoformat(row[di][:10])
            v = float(row[vi])
        except (ValueError, TypeError):
            continue
        _RATE_CACHE[d] = v / 100.0


def enrich_chain(df, underlying_price, as_of, expiry_col="expiration", q=0.0):
    """Add iv/delta/gamma/vega/theta to an EOD chain, computed from the MID.

    The mid is used for the vol solve because it is the market's best estimate of value; the
    FILL is still charged at the touch by options_fill. Mixing those up - solving IV off a fill
    price - would put the spread into the vol surface.
    """
    import datetime as dt

    import numpy as np
    import pandas as pd

    if df is None or len(df) == 0:
        return df
    d = df.copy()
    asof = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    r = risk_free_rate(asof)
    exp = pd.to_datetime(d[expiry_col]).dt.date
    T = np.array([(e - asof).days / 365.0 for e in exp], dtype=float)
    mid = (pd.to_numeric(d["bid"], errors="coerce")
           + pd.to_numeric(d["ask"], errors="coerce")) / 2.0
    ivs, deltas, gammas, vegas, thetas = [], [], [], [], []
    S = float(underlying_price)
    for i in range(len(d)):
        K = float(d["strike"].iloc[i])
        right = str(d["right"].iloc[i])
        v = implied_vol(mid.iloc[i], S, K, T[i], r, right, q)
        ivs.append(v)
        g = greeks(S, K, T[i], r, v, right, q) if v else {}
        deltas.append(g.get("delta"))
        gammas.append(g.get("gamma"))
        vegas.append(g.get("vega"))
        thetas.append(g.get("theta"))
    d["dte"] = (T * 365.0).round().astype(int)
    d["mid"] = mid
    d["iv"] = ivs
    d["delta"] = deltas
    d["gamma"] = gammas
    d["vega"] = vegas
    d["theta"] = thetas
    d["risk_free"] = r
    d["underlying"] = S
    return d


def validate_against_vendor(mine, vendor, tol_delta=0.05, tol_iv=0.05) -> dict:
    """Compare locally-computed delta/IV against the vendor's on the same contracts.

    This exists because a hand-rolled pricer that is subtly wrong would corrupt every signal
    downstream while every run completed normally - the exact failure mode this project has hit
    four times. Merges on (expiration, strike, right) and reports agreement rates.
    """
    import pandas as pd

    keys = ["expiration", "strike", "right"]
    v = vendor.drop_duplicates(subset=keys, keep="last")
    vcol = "implied_vol" if "implied_vol" in v.columns else "iv"
    m = mine.merge(v[keys + ["delta", vcol]], on=keys, how="inner",
                   suffixes=("", "_vendor"))
    if len(m) == 0:
        return {"n": 0}
    dd = (pd.to_numeric(m["delta"], errors="coerce")
          - pd.to_numeric(m["delta_vendor"], errors="coerce")).abs()
    vv = (pd.to_numeric(m["iv"], errors="coerce")
          - pd.to_numeric(m[vcol + ("_vendor" if vcol == "iv" else "")], errors="coerce")).abs()
    return {
        "n": int(len(m)),
        "n_delta_compared": int(dd.notna().sum()),
        "delta_agree_pct": float((dd <= tol_delta).mean()),
        "delta_median_abs_err": float(dd.median()) if dd.notna().any() else None,
        "iv_agree_pct": float((vv <= tol_iv).mean()) if vv.notna().any() else None,
        "iv_median_abs_err": float(vv.median()) if vv.notna().any() else None,
    }
