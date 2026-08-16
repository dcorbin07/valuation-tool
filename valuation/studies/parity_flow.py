"""MA31 + MA32 — matched-strike parity deviation, and the open-vs-close volume decomposition.

Executes `PREREG_ma31_ma32_parity_openclose.md`, committed ALONE at `a51e372`, a strict ancestor
of every commit that computes an arm. Nothing here may be changed to fit a result.

WHAT THESE ANSWER, AND WHAT THEY DO NOT
---------------------------------------
`MA31` asks whether Cremers-Weinbaum's volatility spread — the open-interest-weighted mean of
`iv_call - iv_put` over pairs sharing an identical strike and expiry — predicts the UNDERLYING's
63-day forward return once the seven weighted incumbents are projected out. `MA32` asks the same
of the share of option volume that OPENS new positions, split by right.

Neither builds Ge-Lin-Pearson's O/S ratio: that needs STOCK volume, which per `MA25` exists for
only ~290 names. It is not built and **not proxied** — a proxy would be a different hypothesis
wearing this one's name.

FOUR PREMISE FACTS THAT SHAPE EVERY DEFINITION HERE
---------------------------------------------------
1. **A matched pair being PRESENT is not a matched pair being USABLE.** `V6-OPT` measured the
   cache at 1,288,750 puts against 1,288,751 calls with zero tickers lacking puts, which removed
   `U2`'s recorded blocker. But a pair needs a two-sided quote on BOTH legs, so the pair-level
   rate is roughly the SQUARE of `MA45`'s leg-level one: measured 42 of 92, 10 of 64, 2 of 25 on
   sampled cross-sections. Coverage is a primary risk here, and `coverage_report` gates on it.
2. **`B4`'s `-1` open-interest sentinel is live** — 2.5273% of 610,186 sampled rows. `MA32` is
   built ON the OI difference, so a sentinel reaching it manufactures flow out of a sentinel.
   Excluded, counted, and the count is REQUIRED to be non-zero: a zero would mean the filter never
   reached the data, which is a vacuous guard rather than a clean one.
3. **Recovering the spot from parity would set `MA31`'s answer to zero BY CONSTRUCTION.**
   `dividends.spot_from_parity` returns `S = C - P + K*exp(-rT)`; feed that back in and
   `iv_call - iv_put` is identically zero, and the arm reports a clean, plausible, fabricated
   null. Spot is the as-traded `raw_close` and nothing else. `FORBIDDEN_CALLS` names it and
   `tests/test_ma31_ma32_parity_flow.py` asserts at SOURCE level that it never appears here.
4. **`raw_close`, never `close`.** Strikes are as-traded; `close` is split- and dividend-adjusted
   (session 30: NVDA 2012 reads 0.27 against a raw 11.97, a 43x ratio) and the failure is SILENT.

WHAT THIS MODULE DELIBERATELY DOES NOT OWN
------------------------------------------
The join, the half-split, the IC arithmetic and the residualisation are `surface_stock`'s and are
IMPORTED. Re-typing them would be audit `B7`'s defect class — the error this project has already
recorded four times (`hlz_hurdle`, Benjamini-Hochberg, `_insider_formula`, `usable_quote`).
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ..edge import blackscholes as BS
from .surface_stock import (INCUMBENTS, MIN_DATES, MIN_NAMES, RegisterViolation,  # noqa: F401
                            _spearman, arm_ic, halves, ic_series_degenerate, ic_tstat,
                            join_pit, residualise)

# --------------------------------------------------------------------------- #
#  Constants — every one fixed by the register, none discovered at runtime
# --------------------------------------------------------------------------- #
MONEYNESS_BAND = 0.10       # |K/S - 1| for A1. A priori: wings carry unreliable IVs and no OI.
MONEYNESS_BAND_WIDE = 0.20  # C-BAND sensitivity. REPORTED, CARRIES NO VERDICT.
DTE_MIN, DTE_MAX = 7, 365
MIN_PAIRS = 3               # admitted matched pairs required to score a (ticker, date)
MIN_VOLUME = 100            # denominator floor for the MA32 shares
MAX_OI_GAP_DAYS = 5         # a hole in the cache must not read as a week of accumulated flow
DTE_AMERICAN = 60           # C-AMER restriction. REPORTED, CARRIES NO VERDICT.

PERM_DRAWS = 500            # MA32's own within-date permutation null
PERM_SEED = 31_32           # fixed here, not chosen after seeing a result

IC_BAR = 2.71               # X7's calibrated theme-IC p95. AN EXTRAPOLATION on this subsample.
POWER_BAR = 2.0             # the audit's own power-control bar

ARMS: Tuple[str, ...] = ("parity_dev", "call_open_share", "put_open_share")

#: Declared a priori, in the register, before any arm existed.
#: Cremers-Weinbaum: relatively expensive CALLS => the stock OUTPERFORMS => POSITIVE.
#: Ge-Lin-Pearson: the parent O/S ratio predicts NEGATIVELY and the audit states the effect
#: concentrates in call purchases that open new positions, so the carrying component inherits the
#: parent's sign. That inheritance is an ARGUMENT, not a citation, and is labelled one.
#: `put_open_share` has no establishable published direction and is TWO-SIDED.
DECLARED_SIGN: Dict[str, int] = {"parity_dev": +1, "call_open_share": -1}

#: Calling any of these on the arm path is a void condition of the register (§5.4).
FORBIDDEN_CALLS: Tuple[str, ...] = ("spot_from_parity", "q_scheduled")


# --------------------------------------------------------------------------- #
#  1. MA31 — matched pairs and the volatility spread
# --------------------------------------------------------------------------- #
def matched_pairs(xs: pd.DataFrame) -> pd.DataFrame:
    """Join one chain cross-section to itself on (expiration, strike), call leg against put leg.

    Returns one row per matched pair with both legs' bid/ask/open_interest. Rows whose legs are
    duplicated in the source are collapsed by taking the first, so a vendor duplicate cannot
    silently fan a pair out into several.
    """
    need = ("expiration", "strike", "right", "bid", "ask", "open_interest")
    for c in need:
        if c not in xs.columns:
            raise KeyError(f"chain cross-section missing {c!r}")
    key = ["expiration", "strike"]
    c = xs[xs["right"] == "C"].drop_duplicates(subset=key).set_index(key)
    p = xs[xs["right"] == "P"].drop_duplicates(subset=key).set_index(key)
    both = c.index.intersection(p.index)
    if len(both) == 0:
        return pd.DataFrame(columns=["expiration", "strike", "c_bid", "c_ask", "c_oi",
                                     "p_bid", "p_ask", "p_oi"])
    cc, pp = c.loc[both], p.loc[both]
    out = pd.DataFrame({
        "c_bid": cc["bid"].values.astype(float), "c_ask": cc["ask"].values.astype(float),
        "c_oi": cc["open_interest"].values.astype(float),
        "p_bid": pp["bid"].values.astype(float), "p_ask": pp["ask"].values.astype(float),
        "p_oi": pp["open_interest"].values.astype(float),
    }, index=both).reset_index()
    return out


def admit_pairs(pairs: pd.DataFrame, spot: float, t_years: pd.Series,
                band: float = MONEYNESS_BAND) -> pd.Series:
    """The register's §1.1 admission rules, as a boolean mask. Nothing here is a selection rule.

    `usable_quote` on BOTH legs is deliberately EXACTLY `MA45`'s predicate and no more: it is a
    statement about whether a number is a price. Moneyness and DTE are strategy choices and are
    kept OUT of it, which is the distinction `MA45` shipped.
    """
    if len(pairs) == 0:
        return pd.Series([], dtype=bool)
    usable = np.array([BS.usable_quote(b, a) for b, a in
                       zip(pairs["c_bid"], pairs["c_ask"])]) & \
             np.array([BS.usable_quote(b, a) for b, a in
                       zip(pairs["p_bid"], pairs["p_ask"])])
    no_sentinel = (pairs["c_oi"].values >= 0) & (pairs["p_oi"].values >= 0)   # B4
    mny = np.abs(pairs["strike"].values.astype(float) / float(spot) - 1.0) <= band
    tv = np.asarray(t_years, dtype=float)
    dte_ok = (tv >= DTE_MIN / 365.0) & (tv <= DTE_MAX / 365.0)
    return pd.Series(usable & no_sentinel & mny & dte_ok, index=pairs.index)


def volatility_spread(xs: pd.DataFrame, spot: float, asof, r: float, q: float = 0.0,
                      band: float = MONEYNESS_BAND) -> Optional[dict]:
    """Cremers-Weinbaum's volatility spread for one (ticker, date). None when unscoreable.

    `w_i = min(oi_call, oi_put)` — the conservative matched weight: a pair is only as deep as its
    thinner leg, and using the sum would let one fat leg carry a pair whose other side nobody
    holds.
    """
    pairs = matched_pairs(xs)
    if len(pairs) == 0:
        return None
    exp = pd.to_datetime(pairs["expiration"]).values.astype("datetime64[D]")
    a = np.datetime64(pd.Timestamp(asof).date(), "D")
    t_years = (exp - a).astype(int) / 365.0
    keep = admit_pairs(pairs, spot, t_years, band)
    pr, tt = pairs[keep.values], t_years[keep.values]
    if len(pr) < MIN_PAIRS:
        return None

    cmid = (pr["c_bid"].values + pr["c_ask"].values) / 2.0
    pmid = (pr["p_bid"].values + pr["p_ask"].values) / 2.0
    K = pr["strike"].values.astype(float)
    w = np.minimum(pr["c_oi"].values, pr["p_oi"].values).astype(float)

    num = den = 0.0
    n_solved = 0
    for i in range(len(pr)):
        ivc = BS.implied_vol(cmid[i], spot, K[i], tt[i], r, "C", q)
        if ivc is None:
            continue
        ivp = BS.implied_vol(pmid[i], spot, K[i], tt[i], r, "P", q)
        if ivp is None:
            continue
        wi = w[i]
        if not (wi > 0):
            continue                      # zero-OI pairs carry no weight; they are not evidence
        num += wi * (ivc - ivp)
        den += wi
        n_solved += 1
    if n_solved < MIN_PAIRS or den <= 0:
        return None
    return {"parity_dev": num / den, "n_pairs_admitted": int(len(pr)),
            "n_pairs_solved": int(n_solved), "oi_weight": float(den)}


# --------------------------------------------------------------------------- #
#  2. MA32 — the open-vs-close decomposition
# --------------------------------------------------------------------------- #
def open_shares(xs: pd.DataFrame, xs_prev: pd.DataFrame, asof, prev) -> Optional[dict]:
    """Share of each side's volume attributable to OPENING new positions.

    `opening_i = clip(dOI_i, 0, volume_i)`. The clip is doing two jobs and both are deliberate:
    a NEGATIVE dOI is net closing and contributes no opening volume, and an increase larger than
    the day's volume cannot have been opened by that day's trading, so it is capped rather than
    believed.

    Returns None when the gap to `prev` exceeds `MAX_OI_GAP_DAYS`: a hole in the cache must not be
    read as a week of accumulated flow.
    """
    gap = (pd.Timestamp(asof).date() - pd.Timestamp(prev).date()).days
    if gap <= 0 or gap > MAX_OI_GAP_DAYS:
        return None
    key = ["expiration", "strike", "right"]
    a = xs.drop_duplicates(subset=key).set_index(key)
    b = xs_prev.drop_duplicates(subset=key).set_index(key)
    common = a.index.intersection(b.index)
    if len(common) == 0:
        return None
    aa, bb = a.loc[common], b.loc[common]

    oi_now = aa["open_interest"].values.astype(float)
    oi_prev = bb["open_interest"].values.astype(float)
    vol = aa["volume"].values.astype(float)
    sentinel = (oi_now < 0) | (oi_prev < 0)                       # B4 — counted, not silent
    exp = pd.to_datetime(aa.index.get_level_values("expiration")).values.astype("datetime64[D]")
    t_days = (exp - np.datetime64(pd.Timestamp(asof).date(), "D")).astype(int)
    ok = (~sentinel) & (t_days >= DTE_MIN) & (t_days <= DTE_MAX) & (vol >= 0)
    if not ok.any():
        return None

    right = np.asarray(aa.index.get_level_values("right"), dtype=object)
    opening = np.clip(oi_now - oi_prev, 0.0, None)
    opening = np.minimum(opening, np.maximum(vol, 0.0))

    out = {"n_sentinel_dropped": int(sentinel.sum()), "n_contracts": int(ok.sum()),
           "gap_days": int(gap)}
    for side, name in (("C", "call_open_share"), ("P", "put_open_share")):
        m = ok & (right == side)
        v = float(vol[m].sum())
        out[name] = float(opening[m].sum() / v) if v >= MIN_VOLUME else None
        out[name + "_volume"] = v
    if out["call_open_share"] is None and out["put_open_share"] is None:
        return None
    return out


# --------------------------------------------------------------------------- #
#  3. The null, the bar, and the verdict
# --------------------------------------------------------------------------- #
def permutation_bar(frame: pd.DataFrame, cand: str, dates: Sequence, sign: Optional[int],
                    draws: int = PERM_DRAWS, seed: int = PERM_SEED,
                    incumbents: Sequence[str] = INCUMBENTS) -> dict:
    """The arm's OWN within-date permutation p95 — MA32's kill condition, verbatim.

    The candidate is shuffled WITHIN each date, so the per-date distribution, the missingness
    pattern and every incumbent stay exactly as they are; only the pairing with `fwd_ret` breaks.

    A DEGENERATE DRAW IS DROPPED, NOT SCORED AS ZERO. `V6` measured that treating a degenerate
    permutation as 0.0 pads the null with fake draws and LOWERS the p95 — i.e. makes the bar
    EASIER. `n_draws_used` is reported so a thinned null is visible rather than silent.
    """
    rng = np.random.default_rng(seed)
    sub = frame[frame["date"].isin(list(dates))].copy()
    stats = []
    for _ in range(draws):
        shuffled = sub.groupby("date")[cand].transform(
            lambda s: pd.Series(rng.permutation(s.values), index=s.index))
        sub["_perm"] = shuffled
        res = arm_ic(sub, "_perm", dates, incumbents)
        t = res.get("incremental_ic_tstat")
        if t is None or not np.isfinite(t) or res.get("incremental_degenerate"):
            continue
        stats.append(float(t) * sign if sign else abs(float(t)))
    if len(stats) < 2:
        return {"p95": None, "n_draws_used": len(stats), "ok": False}
    return {"p95": float(np.percentile(stats, 95)), "n_draws_used": len(stats),
            "median": float(np.median(stats)), "max": float(np.max(stats)), "ok": True}


def minimum_detectable_ic(ics: Sequence[float], bar: float) -> Optional[float]:
    """The incremental IC this design could have separated from zero at `bar`.

    `S19`'s rule, restated by `V6`: a NULL means "could not be separated at this resolution",
    NEVER "absent" — so it is quoted with its MDE or it is not quoted.
    """
    a = np.asarray([x for x in ics if x == x], dtype=float)
    if len(a) < 2:
        return None
    se = float(a.std(ddof=1)) / (len(a) ** 0.5)
    return bar * se


def verdict(arm: str, t_early: Optional[float], t_late: Optional[float], bar_early: float,
            bar_late: float, degenerate: bool = False, duplicate: bool = False,
            power_ok: bool = True) -> dict:
    """PASS only if BOTH halves clear their own bar AND the declared sign holds in both.

    A duplicate carries NO independent verdict (C-DUP), and a degenerate IC series can never be
    READ as a pass however large its t — the value-dependent zero-variance guard `surface_stock`
    inherited from the shipped arithmetic and reported rather than repaired.
    """
    sign = DECLARED_SIGN.get(arm)
    reasons = []
    if duplicate:
        return {"arm": arm, "verdict": "DUPLICATE", "t_early": t_early, "t_late": t_late,
                "reasons": ["declared a duplicate by C-DUP; carries no independent verdict"]}
    if degenerate:
        reasons.append("IC series degenerate")
    if t_early is None or t_late is None:
        reasons.append("a half could not be scored")
        return {"arm": arm, "verdict": "NULL", "t_early": t_early, "t_late": t_late,
                "reasons": reasons}
    if sign:
        se, sl = sign * t_early, sign * t_late
        clears = (se >= bar_early) and (sl >= bar_late)
        if not clears:
            reasons.append(f"declared sign {sign:+d}: {se:.4f} vs {bar_early:.4f} (early), "
                           f"{sl:.4f} vs {bar_late:.4f} (late)")
    else:
        clears = (abs(t_early) >= bar_early and abs(t_late) >= bar_late
                  and (t_early > 0) == (t_late > 0))
        if not clears:
            reasons.append(f"two-sided: |{t_early:.4f}| vs {bar_early:.4f}, "
                           f"|{t_late:.4f}| vs {bar_late:.4f}, signs "
                           f"{'agree' if (t_early > 0) == (t_late > 0) else 'DISAGREE'}")
    v = "PASS" if (clears and not degenerate) else "NULL"
    if v == "PASS" and not power_ok:
        reasons.append("power control did not clear; this pass is UNINTERPRETABLE")
    return {"arm": arm, "verdict": v, "t_early": t_early, "t_late": t_late,
            "bar_early": bar_early, "bar_late": bar_late, "declared_sign": sign,
            "power_ok": power_ok, "reasons": reasons}


def duplicate_check(frame: pd.DataFrame, a: str, b: str, threshold: float = 0.90) -> dict:
    """Is one arm another arm — or an incumbent — renamed? `U2`'s §0.3 discipline, as a control."""
    ss = frame.dropna(subset=[a, b])
    rho = _spearman(ss[a].values.astype(float), ss[b].values.astype(float)) if len(ss) >= 3 \
        else float("nan")
    dup = bool(rho == rho and abs(rho) > threshold)
    return {"a": a, "b": b, "n": int(len(ss)), "spearman": None if rho != rho else float(rho),
            "duplicate": dup, "threshold": threshold}


def coverage_report(frame: pd.DataFrame, arm: str, min_names: int = MIN_NAMES) -> dict:
    """Names per date and dates scoreable — C-COV. Coverage is reported BEFORE any verdict.

    `dates` are the FRAME'S OWN date values, not strings, and that is load-bearing rather than
    stylistic. The first cut returned `str(d)[:10]` so the artifact would read nicely; every
    consumer (`arm_ic`, `halves`) then filtered a datetime64 column with `.isin([...strings])`,
    matched nothing, and every arm came back with `n_dates = 0`.

    THE FAILURE PRESENTED AS A RESULT. Coverage said 40 dates and 16,736 joined rows while the
    arms all read NULL, and "an options arm is null" is the single most believable sentence in
    this record. Stringify at the JSON boundary, never at the computation boundary.
    """
    have = frame[arm].notna()
    g = frame.loc[have].groupby("date").size()
    dates = sorted(d for d, k in g.items() if k >= min_names)
    return {"arm": arm, "rows_joined": int(have.sum()),
            "row_coverage": float(have.mean()) if len(frame) else 0.0,
            "dates_any": int((g > 0).sum()), "dates_scoreable": len(dates),
            "median_names_per_date": float(np.median(g.values)) if len(g) else 0.0,
            "min_names": min_names, "dates": dates}
