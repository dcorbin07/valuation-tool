"""V6-OPT — the post-dip option surface, and the cash-secured put a seller would actually sell.

Registered in `PREREG_v6opt_csp.md`, committed ALONE at `88685c9` before this file existed.

STAGE 1 IS DESCRIPTIVE. Nothing here scores an arm; the only threshold in the module is the
richness gate of register section 3, and its three bars are UNCALIBRATED and say so.

THREE CONVENTIONS THAT HAVE COST THIS PROJECT REAL MONEY, ENFORCED HERE:

* **`max_drawdown` is NEGATIVE**, so an arm improves it by being LESS negative and the gain is
  `arm - base`. `S10` shipped the opposite and reported a 2.61pp WORSENING as an improvement.
* **A zero-variance guard must carry a TOLERANCE.** `if sd > 0` passes on `[0.1, 0.1, 0.1]`,
  whose floating-point sd is ~5.8e-17, and returns a *t* of ~1e16 — the `SECTOR-NEUTRAL-B6`
  defect, met again in `U2`'s `theme_ic`. Every guard below tests `<= _EPS`.
* **`skew_25d` IS `iv_put_25d - iv_call_25d`**, exactly (U2: max |diff| 0.000e+00). It is ONE
  column and its negation, never two pieces of evidence.

POINT-IN-TIME IS STRUCTURAL, NOT A FLAG: every surface read takes the last row dated `<= d`, and
`forward_path` starts at the first row STRICTLY AFTER `d`. There is no argument that turns this
off, because a look-ahead that is one keyword away is a look-ahead that eventually happens.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from valuation.edge.options_fill import Quote, fill_price

_EPS = 1e-12

# ---- PRE-REGISTERED constants. Nothing here is swept; a sweep is void condition 8.3/8.5. ----
BASELINE_WINDOW = 252          # register 2, D1 - the name's OWN trailing year
FORWARD_DAYS = 30              # register 2, D2/D6 - "decay curve over 30d"
TARGET_DELTA = -0.25           # register 2, D4
DTE_LO, DTE_HI = 30, 45        # register 2, D4
MIN_OI = 100                   # register 4
MAX_SPREAD_FRAC = 0.25         # register 4 - the PROJECT's quote-sanity bar, not the bot's 0.10
DELTA_TOLERANCE = 0.05         # register 5, C4
SELL_AGGRESSION = 1.0          # register 4 - the shipped honest default; A3's headline too
COST_RHO = 0.6743              # O18, a DECLARED DIAGNOSTIC only - never the headline

# register 3 - the richness gate. ALL THREE ARE UNCALIBRATED (register 3.1).
G1_MIN_CREDIT_FRAC = 0.005     # >= 0.50% of strike
G2_MIN_ELEVATION_RATIO = 0.75  # healthy elevation >= 75% of unhealthy
TRADING_DAYS = 252.0


class RegisterViolation(AssertionError):
    """Raised when the code would depart from `PREREG_v6opt_csp.md`."""


# ---------------------------------------------------------------------------------------
# surface access
# ---------------------------------------------------------------------------------------
def daily_path(root: str, ticker: str) -> str:
    return os.path.join(root, ticker, f"{ticker}-daily.pkl")


def load_daily(root: str, ticker: str) -> Optional[pd.DataFrame]:
    """The shipped per-ticker daily surface, or None. Sorted, deduplicated by date."""
    p = daily_path(root, ticker)
    if not os.path.exists(p):
        return None
    try:
        d = pd.read_pickle(p)
    except Exception:
        return None
    if d is None or not len(d) or "date" not in d.columns:
        return None
    d = d.copy()
    d["date"] = pd.to_datetime(d["date"])
    return d.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)


def as_of(daily: pd.DataFrame, d) -> Optional[pd.Series]:
    """The last surface row dated <= d. POINT-IN-TIME; there is no 'nearest' fallback.

    A nearest-match would silently read TOMORROW's surface on a date the market was shut,
    which is the whole class of defect C2 exists to count.
    """
    if daily is None or not len(daily):
        return None
    ts = pd.Timestamp(str(d)[:10])
    i = int(np.searchsorted(daily["date"].to_numpy(dtype="datetime64[ns]"),
                            np.datetime64(ts, "ns"), side="right"))
    if i <= 0:
        return None
    return daily.iloc[i - 1]


def baseline(daily: pd.DataFrame, d, col: str = "atm_iv_30",
             window: int = BASELINE_WINDOW, min_obs: int = 60) -> Optional[float]:
    """Median of `col` over the `window` rows STRICTLY BEFORE `d` - the name's own baseline.

    Median, not mean: an implied-vol series has spikes, and the register asks how elevated the
    dip-date reading is against a NORMAL one.
    """
    if daily is None or not len(daily):
        return None
    ts = np.datetime64(pd.Timestamp(str(d)[:10]), "ns")
    arr = daily["date"].to_numpy(dtype="datetime64[ns]")
    i = int(np.searchsorted(arr, ts, side="left"))       # STRICTLY before
    if i < min_obs:
        return None
    lo = max(0, i - window)
    v = pd.to_numeric(daily[col].iloc[lo:i], errors="coerce").dropna()
    if len(v) < min_obs:
        return None
    m = float(v.median())
    return m if np.isfinite(m) else None


def forward_path(daily: pd.DataFrame, d, col: str = "atm_iv_30",
                 n: int = FORWARD_DAYS) -> List[Optional[float]]:
    """`col` on the n trading days STRICTLY AFTER d. Short paths are padded with None.

    Padding with None rather than dropping keeps a truncated path visible: a series that ends
    early because the cache ends is not the same object as one that decayed to nothing, and
    averaging the two together is how a right-censored path becomes a finding.
    """
    if daily is None or not len(daily):
        return [None] * n
    ts = np.datetime64(pd.Timestamp(str(d)[:10]), "ns")
    arr = daily["date"].to_numpy(dtype="datetime64[ns]")
    i = int(np.searchsorted(arr, ts, side="right"))
    v = pd.to_numeric(daily[col].iloc[i:i + n], errors="coerce").tolist()
    out: List[Optional[float]] = [float(x) if x is not None and np.isfinite(x) else None
                                  for x in v]
    return out + [None] * (n - len(out))


def elevation(level: Optional[float], base: Optional[float]) -> Optional[float]:
    """level / base - 1. None unless BOTH exist and the base is meaningfully non-zero."""
    if level is None or base is None:
        return None
    if not (np.isfinite(level) and np.isfinite(base)) or abs(base) <= _EPS:
        return None
    return float(level) / float(base) - 1.0


# ---------------------------------------------------------------------------------------
# the contract a cash-secured put seller would actually sell
# ---------------------------------------------------------------------------------------
def reconstruct_quote(mid: float, spread_frac: float) -> Quote:
    """A Quote from the derived layer's own `mid` and `spread_frac = (ask - bid) / mid`.

    So bid = mid * (1 - spread_frac/2) and ask = mid * (1 + spread_frac/2). The identity is
    verified against the RAW chain's own bid/ask by control C-QUOTE rather than assumed - the
    derived layer is a second copy of the same numbers and two copies can disagree (audit B7).

    `Quote.mid` is a PROPERTY computed from bid and ask, not a constructor argument, so it is
    never passed here - handing a mid in would silently do nothing.
    """
    m = float(mid)
    half = 0.5 * float(spread_frac) * m
    return Quote(bid=max(0.0, m - half), ask=m + half, oi=None, volume=None)


def sell_credit(mid: float, spread_frac: float,
                aggression: float = SELL_AGGRESSION) -> Optional[float]:
    """What SELLING this contract actually pays, through the SHIPPED fill engine.

    aggression 1.0 = hit the bid, the honest default and the aggression A3's headline used, so
    the two results are comparable. Lower values are diagnostics and never the headline.
    """
    q = reconstruct_quote(mid, spread_frac)
    return fill_price(q, "sell", aggression)


def pick_csp(chain_day: pd.DataFrame,
             target_delta: float = TARGET_DELTA,
             dte_lo: int = DTE_LO, dte_hi: int = DTE_HI,
             min_oi: int = MIN_OI, max_spread: float = MAX_SPREAD_FRAC) -> Optional[dict]:
    """The put nearest `target_delta` inside the DTE band that passes the liquidity gate.

    Returns None - never a fallback contract - when nothing qualifies. A near-miss substitute
    would answer a different question under this one's name, which is `O6`'s finding: a
    selection rule that moves the delta has changed the trade, not merely repriced it.
    """
    if chain_day is None or not len(chain_day):
        return None
    d = chain_day
    d = d[d["right"].astype(str).str.upper().str.startswith("P")]
    if not len(d):
        return None
    dte = pd.to_numeric(d["dte"], errors="coerce")
    d = d[(dte >= dte_lo) & (dte <= dte_hi)]
    if not len(d):
        return None
    oi = pd.to_numeric(d.get("open_interest"), errors="coerce")
    sf = pd.to_numeric(d.get("spread_frac"), errors="coerce")
    mid = pd.to_numeric(d.get("mid"), errors="coerce")
    dl = pd.to_numeric(d.get("delta"), errors="coerce")
    ok = (oi >= min_oi) & (sf > 0) & (sf <= max_spread) & (mid > 0) & dl.notna()
    d = d[ok.fillna(False)]
    if not len(d):
        return None
    gap = (pd.to_numeric(d["delta"], errors="coerce") - float(target_delta)).abs()
    r = d.loc[gap.idxmin()]
    strike = float(r["strike"])
    if strike <= 0:
        return None
    credit = sell_credit(float(r["mid"]), float(r["spread_frac"]))
    if credit is None or credit <= 0:
        return None
    return {"strike": strike, "expiration": str(r.get("expiration"))[:10],
            "dte": int(r["dte"]), "delta": float(r["delta"]),
            "mid": float(r["mid"]), "spread_frac": float(r["spread_frac"]),
            "open_interest": float(r["open_interest"]), "iv": float(r.get("iv", np.nan)),
            "spot": float(r.get("spot", np.nan)),
            "credit": float(credit),
            "credit_frac_strike": float(credit) / strike,
            "credit_rho": float(_rho_credit(float(r["mid"]), float(r["spread_frac"]))),
            }


def _rho_credit(mid: float, spread_frac: float, rho: float = COST_RHO) -> float:
    """O18's DIAGNOSTIC: a real trade pays about rho of the QUOTED half-spread, not all of it.

    Never the headline (register 4, void condition 9). O18's own rule travels with it: its
    availability term is SELECTED and may never be quoted as a saving.
    """
    return float(mid) * (1.0 - rho * 0.5 * float(spread_frac))


def annualise_credit(credit_frac_strike: float, dte: int) -> Optional[float]:
    """Simple (not compounded) annualisation of a credit-to-strike over its own DTE.

    Deliberately simple: compounding a premium implies reinvestment this study does not model,
    and `U3` is the standing reminder that a construction which tops a book back up flatters it.
    """
    if dte is None or dte <= 0:
        return None
    return float(credit_frac_strike) * (365.0 / float(dte))


# ---------------------------------------------------------------------------------------
# realised volatility, for the variance-risk-premium measurement (register D6)
# ---------------------------------------------------------------------------------------
def realised_vol(closes: Sequence[float], ann: float = TRADING_DAYS) -> Optional[float]:
    """Annualised close-to-close volatility of a forward price path.

    Guard carries a TOLERANCE, not `> 0` (module docstring). Needs >= 10 returns: a realised
    vol on three days is not a measurement of anything and would enter D6 as though it were.
    """
    c = np.asarray([x for x in closes if x is not None and np.isfinite(x) and x > 0],
                   dtype=float)
    if c.size < 11:
        return None
    r = np.diff(np.log(c))
    if r.size < 10:
        return None
    sd = float(np.std(r, ddof=1))
    if not np.isfinite(sd) or sd <= _EPS:
        return None
    return sd * float(np.sqrt(ann))


def vrp(implied: Optional[float], realised: Optional[float]) -> Optional[float]:
    """Implied minus subsequent realised. Positive = the seller was paid more than it cost."""
    if implied is None or realised is None:
        return None
    if not (np.isfinite(implied) and np.isfinite(realised)):
        return None
    return float(implied) - float(realised)


# ---------------------------------------------------------------------------------------
# splits, summaries and the gate
# ---------------------------------------------------------------------------------------
def halves(dates: Sequence, min_dates: int = 16):
    """Split a COVERED date list at its median and EMBARGO the boundary date.

    Register 1c. The embargo is why the two halves sum to one less than the total, and the
    caller is expected to report both counts rather than the total alone.
    """
    ds = sorted(pd.Timestamp(str(x)[:10]) for x in pd.unique(pd.Series(list(dates))))
    if len(ds) < 2 * min_dates:
        raise RegisterViolation(
            f"{len(ds)} covered dates cannot make two halves of >= {min_dates}")
    k = len(ds) // 2
    boundary = ds[k]
    return ds[:k], ds[k + 1:], boundary


def summarise(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    """n / mean / median / p05 / p95 with an explicit-tolerance sd guard."""
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"n": 0, "mean": None, "median": None, "sd": None, "p05": None, "p95": None}
    sd = float(np.std(v, ddof=1)) if v.size > 1 else 0.0
    return {"n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
            "sd": (sd if sd > _EPS else 0.0),
            "p05": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}


def gate(healthy_credit_frac_median: Optional[float],
         healthy_elev_median: Optional[float],
         unhealthy_elev_median: Optional[float],
         healthy_vrp_median: Optional[float]) -> Dict[str, object]:
    """Register section 3. Returns each leg's pass/fail and the conjunction.

    A missing input is a FAIL, never a pass: `holdout_theme_validate` had to learn that
    `oos_directions_tested = 0` is not a negative result, and a gate that opens because a
    number could not be computed is the same error wearing a different hat.
    """
    g1 = (healthy_credit_frac_median is not None
          and healthy_credit_frac_median > 0
          and healthy_credit_frac_median >= G1_MIN_CREDIT_FRAC)
    if (healthy_elev_median is None or unhealthy_elev_median is None
            or abs(unhealthy_elev_median) <= _EPS):
        g2, ratio = False, None
    else:
        ratio = float(healthy_elev_median) / float(unhealthy_elev_median)
        g2 = ratio >= G2_MIN_ELEVATION_RATIO
    g3 = healthy_vrp_median is not None and healthy_vrp_median > 0
    return {"G1_credit": bool(g1), "G2_not_priced": bool(g2), "G3_vrp": bool(g3),
            "elevation_ratio": ratio,
            "open": bool(g1 and g2 and g3),
            "uncalibrated": True,
            "note": ("Register 3.1: X7 calibrates no floor for any of these statistics. "
                     "A gate that OPENS is not evidence of anything; only stage 2 can be.")}


# ---------------------------------------------------------------------------------------
# settlement (stage 2)
# ---------------------------------------------------------------------------------------
def spot_on(daily: pd.DataFrame, d) -> Optional[float]:
    """The AS-TRADED spot from the derived surface at the last date <= d.

    THIS IS THE ONLY LEGITIMATE SETTLEMENT BASIS FOR A STRIKE, and the reason is measured, not
    stylistic. Option strikes are as-traded and UNADJUSTED. `data/backtest/prices/*.csv` carries
    SEP's split- AND dividend-ADJUSTED close. Measured on AAPL, whose 4:1 split fell on
    2020-08-31: the derived `spot` is 300.35 on 2020-01-02 where the adjusted close is 72.34, a
    ratio of 4.152, and the two differ by more than 5% on 46.66% of that name's 2,514 days.

    Settling a $300 strike against a $72 adjusted close books a ~76% assignment loss on a trade
    that never happened. That is session 30's O6/O7/O17 defect - "raw_close for anything touching
    a STRIKE, close only for a RETURN" - and it fails SILENTLY, because the trade still prices.
    """
    r = as_of(daily, d)
    if r is None:
        return None
    v = pd.to_numeric(pd.Series([r.get("spot")]), errors="coerce").iloc[0]
    return float(v) if np.isfinite(v) and v > 0 else None


def settle_put(strike: float, credit: float, spot_at_expiry: Optional[float]) -> Optional[dict]:
    """One cash-secured put held to expiry. Return is on the CASH SECURED, i.e. the strike.

    Assigned when the underlying finishes below the strike; the assigned stock is marked at
    expiry rather than carried, so the trade is a closed-form result and no exit rule is
    smuggled in (register 4, and `S23` is why no exit grid is swept).
    """
    if spot_at_expiry is None or strike is None or strike <= 0 or credit is None:
        return None
    k, c, s = float(strike), float(credit), float(spot_at_expiry)
    loss = max(0.0, k - s)
    pnl = c - loss
    return {"assigned": bool(s < k), "intrinsic_loss": loss,
            "pnl_per_share": pnl, "ret_on_strike": pnl / k}


def concurrency_book(trades: List[dict], cap: int) -> Dict[str, object]:
    """Fill trades in date order subject to `cap` simultaneous open positions; refuse when full.

    `O11`'s own construction and its lesson: a book with POSITIVE per-trade expectancy ended at
    $37,059 from $50,000 at cap 10, because opportunity clusters and a cap refuses trades exactly
    when the crowd is richest. Per-trade expectancy is not a verdict; this is what decides.
    """
    ev = []
    for i, t in enumerate(trades):
        ev.append((pd.Timestamp(t["entry"]), 0, i))       # 0 sorts opens before closes same day
        ev.append((pd.Timestamp(t["expiry"]), 1, i))
    ev.sort()
    open_n, taken, skipped = 0, [], 0
    is_open = {}
    for _, kind, i in ev:
        if kind == 0:
            if open_n < cap:
                open_n += 1
                is_open[i] = True
                taken.append(i)
            else:
                skipped += 1
        else:
            if is_open.pop(i, False):
                open_n -= 1
    rets = [float(trades[i]["ret_on_strike"]) for i in taken]
    return {"cap": int(cap), "taken": len(taken), "skipped": int(skipped),
            "mean_ret": (float(np.mean(rets)) if rets else None),
            "max_drawdown": max_drawdown(rets),
            "assigned_frac": (float(np.mean([bool(trades[i]["assigned"]) for i in taken]))
                              if taken else None)}


def paired_sign_test(cells: Sequence[tuple]) -> Dict[str, Optional[float]]:
    """R2's construction: pair (name, year) cells, count signs, z on the binomial.

    R2's standing rule is that the SIGN TEST carries the verdict on this kind of comparison and
    the paired t does not - a barbell payoff's mean is set by a handful of extreme trades, and a
    single control seed moved that mean enough to flip the reading.
    """
    diffs = [float(a) - float(b) for a, b in cells
             if a is not None and b is not None and np.isfinite(a) and np.isfinite(b)]
    d = [x for x in diffs if abs(x) > _EPS]
    n = len(d)
    if n < 2:
        return {"n_cells": n, "n_positive": None, "z": None, "p": None}
    pos = sum(1 for x in d if x > 0)
    z = (pos - n / 2.0) / np.sqrt(n / 4.0)
    from math import erfc, sqrt
    return {"n_cells": int(n), "n_positive": int(pos), "frac_positive": float(pos / n),
            "z": float(z), "p": float(erfc(abs(z) / sqrt(2.0)))}


def max_drawdown(rets: Sequence[float]) -> Optional[float]:
    """NEGATIVE. An arm improves it by being LESS negative, so a gain is `arm - base`."""
    r = np.asarray([x for x in rets if x is not None and np.isfinite(x)], dtype=float)
    if r.size == 0:
        return None
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    return float(dd.min())
