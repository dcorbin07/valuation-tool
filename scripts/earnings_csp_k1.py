"""EARNINGS-CSP `K1` — the earnings payoff ratio, on `O7`'s own 6,013 banked events.

**THE REGISTER'S PRE-COMMITTED KILL, RUN EXACTLY AS THE DRAFT FROZE IT:**

> *"the arm runs only if the measured earnings payoff ratio is <= 0.65. Above it, the register
> STOPS and reports the ratio."*

**ZERO TRIALS AND ZERO NEW DATA** (`DC-1`'s precedent): no option is quoted, no chain is read, no
forward return is taken beyond the one `O7` already read and banked. Every input is a column of
`O6O7O17_EVENTS.pkl`.

WHAT THE RATIO IS
-----------------
`E_physical[payoff] / price` for the put the book would SELL. `SELL-PREMIUM-2` measured **0.4910**
on dip events - expected payoff 0.008523 of strike against a market mid of 0.017358 - so the
seller keeps 50.9% there. Nobody has measured it over earnings, and the draft's own power table
makes the whole design a function of it.

HOW EACH PIECE COMES OUT OF `O7`'s COLUMNS, AND WHERE EACH APPROXIMATION PUSHES
------------------------------------------------------------------------------
`O7` banks `implied_move = (call_mid + put_mid) / S` for the **front expiry strictly after the
announcement** - an ATM straddle price as a fraction of spot, which is a PRICE and not a vol. For
an at-the-money straddle under a driftless lognormal that price is `S * v * sqrt(2/pi)`, so the
total implied move over the option's own life is

    v = implied_move / sqrt(2/pi)

and the 25-delta put strike follows from `N(-d1) = 0.25`, i.e. `d1 = 0.67449`:

    K = S * exp(v**2 / 2 - 0.67449 * v)
    price = K * N(-d2) - S * N(-d1),  d2 = d1 - v

**THREE APPROXIMATIONS, AND THE DIRECTION OF EACH IS STATED BEFORE THE NUMBER.**

1. **NO SKEW.** `O7` banks only the ATM straddle, so the 25-delta put is priced off the ATM vol.
   A real 25-delta put trades ABOVE flat-vol on equity skew, so the modelled price is **too LOW**,
   which makes the ratio **too HIGH** - the direction that makes the kill FIRE. **The safe
   direction**, and it is reported rather than corrected, because correcting it would need a
   quote this kill is defined not to take.
2. **SETTLEMENT AT `post`, NOT AT EXPIRY.** `O7` holds the price on the day after the
   announcement and never at expiry. Settling an option with time left is settling it EARLY, and
   it **drops the remaining time value**, so the measured payoff is **too LOW** and the ratio
   **too LOW** - the direction that makes the kill PASS, i.e. the UNSAFE one. It is therefore
   bounded rather than waved at: the run reports the ratio on the **DTE-matched** subset whose
   expiry is within the draft's own 15-day tenor, where the gap is small, beside the full sample.
3. **THE SIGN OF THE MOVE.** `realised_move` is an ABSOLUTE move off the ADJUSTED series; the
   sign is taken from the AS-TRADED pair. A corporate action inside the four-day window would
   corrupt the as-traded pair (`O-1`'s MNST 3-for-1 booked a fake +1453%), so rows where the two
   magnitudes disagree by more than `SPLIT_TOL` are **counted and dropped**, never settled.

    python scripts/earnings_csp_k1.py
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from valuation.studies import dipcall as D  # noqa: E402  (data_root lives here)

# EVERY CONSTANT BELOW IS THE DRAFT'S. Changing one after a measurement voids the kill.
BAR = 0.65                 # the pre-committed ceiling: at or below, the arm may run
PUT_DELTA = 0.25           # the strike the book sells
TENOR_DAYS = 15            # the draft's declared calendar DTE
SPLIT_TOL = 0.01           # as-traded vs adjusted magnitude gap that marks a corporate action
SQRT_2_OVER_PI = math.sqrt(2.0 / math.pi)
D1_AT_25_DELTA = 0.6744897501960817   # N(-d1) = 0.25


def _ncdf(x):
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(x, float) / math.sqrt(2.0)))


def _days(a, b):
    return (_dt.date.fromisoformat(str(b)) - _dt.date.fromisoformat(str(a))).days


def ratio_frame(events):
    """One row per scoreable event, with the price and the physical payoff per unit of strike."""
    out = []
    dropped_split = 0
    for e in events:
        S = float(e["spot_pre"])
        S1 = float(e["spot_post"])
        im = float(e["implied_move"])
        rm = float(e["realised_move"])
        if not (S > 0 and S1 > 0 and im > 0):
            continue
        # (3) the sign comes from the as-traded pair and the magnitude from the adjusted one;
        # a disagreement is a corporate action and is dropped rather than settled.
        raw = S1 / S - 1.0
        if abs(abs(raw) - rm) > SPLIT_TOL:
            dropped_split += 1
            continue
        signed = math.copysign(rm, raw) if raw != 0 else rm
        v = im / SQRT_2_OVER_PI                      # total implied move over the option's life
        if not (0 < v < 5):
            continue
        K = S * math.exp(v * v / 2.0 - D1_AT_25_DELTA * v)
        d1 = D1_AT_25_DELTA
        d2 = d1 - v
        price = K * float(_ncdf(-d2)) - S * float(_ncdf(-d1))
        if price <= 0:
            continue
        settle = S * (1.0 + signed)
        payoff = max(K - settle, 0.0)
        out.append({
            "ticker": e["ticker"], "earn": e["earn"], "pre": e["pre"],
            "dte": _days(e["pre"], e["expiry"]),
            "days_to_post": _days(e["pre"], e["post"]),
            "v": v, "K": K, "spot_pre": S,
            "price_of_strike": price / K,
            "payoff_of_strike": payoff / K,
            "itm": 1.0 if payoff > 0 else 0.0,
        })
    return pd.DataFrame(out), dropped_split


def ratio(df):
    """`E[payoff] / price`, both normalised by strike -- `SELL-PREMIUM-2`'s own normalisation."""
    if not len(df):
        return None
    p = float(df["payoff_of_strike"].mean())
    c = float(df["price_of_strike"].mean())
    return (p / c) if c > 0 else None



def bootstrap_ratio(df, draws=2000, seed=20261016):
    """A NAME-CLUSTERED interval on the ratio, because the event is never the unit.

    `SC-3` priced this exact mistake: 2.35M option pairs over ~408 names are not 2.35M draws, and
    a per-name resample is the only honest unit. Here one ticker contributes up to ~40 earnings
    events whose implied vols and skews move together, so an event-level interval would be far
    too narrow on a ratio that lands 0.0014 from its own bar.
    """
    if not len(df):
        return None
    rng = np.random.default_rng(seed)
    groups = [g for _, g in df.groupby("ticker", sort=True)]
    pay = np.array([float(g["payoff_of_strike"].sum()) for g in groups])
    pri = np.array([float(g["price_of_strike"].sum()) for g in groups])
    n = np.array([len(g) for g in groups], float)
    out = []
    for _ in range(draws):
        i = rng.integers(0, len(groups), len(groups))
        tot_n = n[i].sum()
        if tot_n <= 0:
            continue
        c = pri[i].sum() / tot_n
        if c > 0:
            out.append((pay[i].sum() / tot_n) / c)
    if not out:
        return None
    a = np.sort(np.array(out))
    return {"draws": int(len(a)), "n_names": int(len(groups)),
            "lo95": float(a[int(0.025 * len(a))]), "hi95": float(a[int(0.975 * len(a))]),
            "median": float(np.median(a))}


def skew_sensitivity(df, bumps=(1.00, 1.05, 1.10, 1.15, 1.20)):
    """What the ratio becomes if the 25-delta put is genuinely richer than the ATM vol says.

    **THE ONE APPROXIMATION THAT CUTS AGAINST FIRING, SO IT IS BOUNDED RATHER THAN NAMED.** Equity
    put skew makes a real 25-delta put trade above flat-vol, so the modelled price is too low and
    the measured ratio too high. Each row re-prices the SAME strike and the SAME realised payoff
    with the pricing vol multiplied by `b`, and reports the ratio that results. The strike is held
    at the ATM-vol 25-delta point rather than re-solved on a smile this data cannot see - stated,
    because re-solving would move the payoff too and the direction would stop being readable.
    """
    if not len(df):
        return []
    v = df["v"].to_numpy(float)
    K = df["K"].to_numpy(float)
    S = df["spot_pre"].to_numpy(float)
    pay = df["payoff_of_strike"].to_numpy(float)
    out = []
    for b in bumps:
        vb = v * b
        # the strike is FIXED, so d1 must be re-derived at the bumped vol rather than reused
        d1 = (np.log(S / K) + vb * vb / 2.0) / vb
        d2 = d1 - vb
        price = (K * _ncdf(-d2) - S * _ncdf(-d1)) / K
        ok = price > 0
        out.append({"vol_multiplier": float(b),
                    "price_of_strike": float(price[ok].mean()),
                    "ratio": float(pay[ok].mean() / price[ok].mean())})
    return out

def main():
    pkl = os.path.join(D.data_root(), "free_analysis", "O6O7O17_EVENTS.pkl")
    ev = pd.read_pickle(pkl)["o7"]
    df, dropped = ratio_frame(ev)

    full = ratio(df)
    matched = df[df["dte"] <= TENOR_DAYS]
    m = ratio(matched)

    res = {
        "kill": "K1",
        "bar": BAR,
        "rule": "the arm runs only if the measured earnings payoff ratio is <= 0.65",
        "n_banked": len(ev),
        "n_scored": int(len(df)),
        "n_dropped_corporate_action": int(dropped),
        "full_sample": {
            "n": int(len(df)),
            "payoff_of_strike": float(df["payoff_of_strike"].mean()),
            "price_of_strike": float(df["price_of_strike"].mean()),
            "ratio": full,
            "share_finishing_itm": float(df["itm"].mean()),
            "median_dte": float(df["dte"].median()),
            "median_days_to_post": float(df["days_to_post"].median()),
        },
        "dte_matched_to_the_declared_tenor": {
            "tenor_days": TENOR_DAYS,
            "n": int(len(matched)),
            "payoff_of_strike": float(matched["payoff_of_strike"].mean()) if len(matched) else None,
            "price_of_strike": float(matched["price_of_strike"].mean()) if len(matched) else None,
            "ratio": m,
            "share_finishing_itm": float(matched["itm"].mean()) if len(matched) else None,
            "median_dte": float(matched["dte"].median()) if len(matched) else None,
        },
        "reference_dip_event_ratio": 0.4910,
        "approximations": {
            "no_skew": "the 25-delta put is priced off the ATM vol, so the price is too LOW and "
                       "the ratio too HIGH -- the direction that makes the kill FIRE (safe)",
            "settled_at_post_not_expiry": "remaining time value is dropped, so the payoff is too "
                                          "LOW and the ratio too LOW -- the direction that makes "
                                          "the kill PASS (unsafe), which is why the DTE-matched "
                                          "subset is reported beside the full sample",
        },
    }
    res["skew_sensitivity_full"] = skew_sensitivity(df)
    res["skew_sensitivity_matched"] = skew_sensitivity(matched)
    res["full_sample"]["name_clustered_ci95"] = bootstrap_ratio(df)
    res["dte_matched_to_the_declared_tenor"]["name_clustered_ci95"] = bootstrap_ratio(matched)
    for key in ("full_sample", "dte_matched_to_the_declared_tenor"):
        r = res[key]["ratio"]
        res[key]["fires"] = (None if r is None else bool(r > BAR))

    out = os.path.join(D.data_root(), "free_analysis", "EARNINGS_CSP_K1.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res, indent=1))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
