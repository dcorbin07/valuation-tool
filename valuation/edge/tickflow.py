"""Tick-flow execution measurement — O10 (passive fills) and O18 (spread-conditional cost).

Pre-registered in `PREREG_o10_passive_fills.md` and `PREREG_o18_spread_cost.md`, committed
together and ALONE at 34b0c11 before this file existed.

WHAT THIS MODULE IS NOT
-----------------------
It does not re-simulate the options book and it never returns a re-banked P&L. O14's cache holds
the alert-days and NOTHING ELSE — measured, not assumed: for the 3,870 split-clean banked entries
the immediate next session is cached for 0 of 3,870 and the exit day for 0 of 3,870. So:

  * the LIVE order-working question (submit after the close, rest on D+1) is NOT ANSWERABLE here;
  * only the ENTRY leg is coverable, while a round trip crosses the spread TWICE.

What is answerable, cleanly, is the EXECUTION ENVIRONMENT of the exact contracts the book traded
on the day it traded them, measured QUOTE-RELATIVELY — every quantity is defined against the
NBBO prevailing at the same instant, so nothing here needs a decision time and nothing here
carries look-ahead.

THE ONE THAT MATTERS: A PASSIVE FILL IS NOT A FREE HALF-SPREAD
--------------------------------------------------------------
A resting bid fills when a seller is aggressive, which is not a random moment. So the advantage
splits into two terms and the second is the whole point of the item:

    NPA(lam, H) = (1-lam) * E_S[half]        gross saving, per FILLED contract
                + ( E_S[delta] - E_all[delta] )   adverse selection, negative when fills
                                                  precede declines

where S is the subset of reference moments that filled and `all` is every reference moment (a
marketable order fills at every one of them). Quoting the first term alone is the answer that
ignores why you got filled.

CONDITION CODES ARE SPLIT BEHAVIOURALLY, NOT SEMANTICALLY
---------------------------------------------------------
The OPRA meaning of these codes is not documented anywhere in this repository and is NOT asserted.
Measured on 12,355 prints, one population seeks the touch (44-87% at bid or ask) and another
almost never reaches it and prints 81-93% INSIDE the quote — the signature of a package/multi-leg
print. The package-like group is excluded from the primary because crediting a single-leg resting
order with fills against package liquidity would OVERSTATE fillability, i.e. flatter the result.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

# ---- Pre-committed constants (PREREG_o10 §2, PREREG_o18 §2-3) -------------------------------
SINGLE_LEG_CODES = (0, 18, 35, 95, 106)     # touch-seeking; the PRIMARY set
PACKAGE_CODES = (125, 130, 131)             # print inside the quote; excluded from primary
MIN_PRINTS = 10                             # eligible prints for a contract-day to count

LAMBDA_GRID = (1.0, 0.5, 0.0, -0.5, -1.0)   # L = mid + lam*half; +1 = ask (incumbent), -1 = bid
HORIZONS_MIN = (5, 15, 30, 60, None)        # None = rest of session
PRIMARY_LAMBDA = 0.0
PRIMARY_HORIZON_MIN = 30

NPA_BAR_PP = 1.00                           # pp of entry premium
FILL_RATE_BAR = 0.50
SPLIT_DATE = "2021-03-08"                   # book median alert_ts

SESSION_CLOSE_S = 16 * 3600                 # 16:00:00 ET, seconds from midnight
N_PERM_DRAWS = 2000
PERM_SEED = 20260811
N_QUANTILES = 5

# Diagnostic only — NOT part of the registered eligibility rule. See `stale_share`.
FRESH_QUOTE_MAX_LAG_S = 60


# ---- Range-minimum, so the fill scan is not quadratic ---------------------------------------
def _sparse_min(p: np.ndarray):
    """Sparse table for O(1) range minimum. Built once per contract-day."""
    n = int(len(p))
    if n == 0:
        return [], np.zeros(0, dtype=np.int32)
    levels = [p.astype(np.float64, copy=True)]
    k = 1
    while (1 << k) <= n:
        prev = levels[-1]
        span = 1 << (k - 1)
        levels.append(np.minimum(prev[: n - (1 << k) + 1], prev[span: n - span + 1]))
        k += 1
    log = np.zeros(n + 1, dtype=np.int32)
    for i in range(2, n + 1):
        log[i] = log[i >> 1] + 1
    return levels, log


def _range_min(levels, log, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Minimum over [lo, hi) per element. Empty ranges return +inf."""
    out = np.full(len(lo), np.inf, dtype=np.float64)
    valid = hi > lo
    if not valid.any():
        return out
    l = lo[valid].astype(np.int64)
    h = hi[valid].astype(np.int64)
    k = log[(h - l)]
    a = levels_at(levels, k, l)
    b = levels_at(levels, k, h - (1 << k))
    out[valid] = np.minimum(a, b)
    return out


def levels_at(levels, k: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Gather level[k][idx] for vector k. Small loop over distinct k (at most ~20)."""
    res = np.empty(len(idx), dtype=np.float64)
    for kk in np.unique(k):
        m = k == kk
        res[m] = levels[int(kk)][idx[m]]
    return res


# ---- Eligibility -----------------------------------------------------------------------------
def eligible_mask(bid, ask, condition, codes: Sequence[int] = SINGLE_LEG_CODES) -> np.ndarray:
    """Two-sided, non-crossed, non-locked, and in the requested condition set."""
    bid = np.asarray(bid, dtype=np.float64)
    ask = np.asarray(ask, dtype=np.float64)
    cond = np.asarray(condition)
    ok = (bid > 0) & (ask > 0) & (ask >= bid) & ((ask - bid) > 0)
    ok &= np.isin(cond, np.asarray(codes))
    return ok


def signed_aggression(price, bid, ask) -> np.ndarray:
    """e = (price - mid)/half. +1 at the ask, -1 at the bid, 0 at mid."""
    price = np.asarray(price, dtype=np.float64)
    bid = np.asarray(bid, dtype=np.float64)
    ask = np.asarray(ask, dtype=np.float64)
    mid = (bid + ask) / 2.0
    half = (ask - bid) / 2.0
    out = np.full(len(price), np.nan, dtype=np.float64)
    m = half > 0
    out[m] = (price[m] - mid[m]) / half[m]
    return out


# ---- O10: the passive fill model --------------------------------------------------------------
def passive_stats(t_s, price, bid, ask, lam: float, horizon_min: Optional[int],
                  entry_premium: float) -> Optional[dict]:
    """One contract-day, one (lam, horizon) cell.

    `t_s` is seconds from midnight ET. Reference moments are the eligible prints themselves, each
    carrying the NBBO prevailing at that instant — which is what makes this free of any assumed
    decision time. A reference moment whose horizon would run past the 16:00 close is DROPPED,
    never silently truncated to the close.

    The fill price is the limit itself: no price improvement is credited, the conservative
    direction. Returns None when the cell has no usable reference moment.
    """
    t = np.asarray(t_s, dtype=np.int64)
    p = np.asarray(price, dtype=np.float64)
    b = np.asarray(bid, dtype=np.float64)
    a = np.asarray(ask, dtype=np.float64)
    n = len(t)
    if n < 2 or not (entry_premium and entry_premium > 0):
        return None
    mid = (a + b) / 2.0
    half = (a - b) / 2.0
    lim = mid + float(lam) * half

    if horizon_min is None:
        end_t = np.full(n, SESSION_CLOSE_S, dtype=np.int64)
        keep = np.ones(n, dtype=bool)
    else:
        end_t = t + int(horizon_min) * 60
        keep = end_t <= SESSION_CLOSE_S
    if not keep.any():
        return None

    hi = np.searchsorted(t, end_t, side="right")          # exclusive end of the window
    lo = np.arange(n, dtype=np.int64) + 1                 # strictly after the reference print
    levels, log = _sparse_min(p)
    wmin = _range_min(levels, log, lo, hi)
    filled = (wmin <= lim) & keep

    # Mark: the mid carried by the last eligible print at or before the horizon.
    k = np.clip(hi - 1, 0, n - 1)
    delta = mid[k] - mid

    ref = keep
    n_ref = int(ref.sum())
    n_fill = int(filled.sum())
    if n_ref == 0:
        return None
    e_all_delta = float(delta[ref].mean())
    if n_fill == 0:
        gross = adverse = npa = float("nan")
    else:
        gross = float((1.0 - float(lam)) * half[filled].mean())
        adverse = float(delta[filled].mean() - e_all_delta)
        npa = gross + adverse
    scale = 100.0 / float(entry_premium)
    return {
        "n_ref": n_ref, "n_fill": n_fill,
        "fill_rate": n_fill / float(n_ref),
        "gross_pp": gross * scale, "adverse_pp": adverse * scale, "npa_pp": npa * scale,
        "mean_half": float(half[ref].mean()),
    }


# ---- O18: effective vs quoted half-spread ------------------------------------------------------
def rho_contract_day(price, bid, ask, size=None) -> Optional[dict]:
    """rho = |price - mid| / half, size-weighted and unweighted, for one contract-day."""
    p = np.asarray(price, dtype=np.float64)
    b = np.asarray(bid, dtype=np.float64)
    a = np.asarray(ask, dtype=np.float64)
    mid = (a + b) / 2.0
    half = (a - b) / 2.0
    m = half > 0
    if not m.any():
        return None
    r = np.abs(p[m] - mid[m]) / half[m]
    if size is None:
        w = np.ones(int(m.sum()), dtype=np.float64)
    else:
        w = np.asarray(size, dtype=np.float64)[m]
        w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
        if w.sum() <= 0:
            w = np.ones(len(r), dtype=np.float64)
    return {"rho_w": float((r * w).sum() / w.sum()), "rho_u": float(r.mean()),
            "n": int(m.sum()), "mean_half": float(half[m].mean())}


def quintile_labels(values, k: int = N_QUANTILES) -> np.ndarray:
    """Quantile bin index 0..k-1, -1 where the value is missing. Ties keep bins non-empty."""
    v = np.asarray(values, dtype=np.float64)
    out = np.full(len(v), -1, dtype=np.int64)
    ok = np.isfinite(v)
    if ok.sum() < k:
        return out
    edges = np.quantile(v[ok], np.linspace(0, 1, k + 1)[1:-1])
    out[ok] = np.searchsorted(edges, v[ok], side="right")
    return out


def r_range(values, labels, k: int = N_QUANTILES) -> Optional[float]:
    """max - min of the per-bin mean. None if fewer than two bins are populated."""
    v = np.asarray(values, dtype=np.float64)
    lb = np.asarray(labels, dtype=np.int64)
    means = []
    for j in range(k):
        m = (lb == j) & np.isfinite(v)
        if m.any():
            means.append(float(v[m].mean()))
    if len(means) < 2:
        return None
    return float(max(means) - min(means))


def spearman(x, y) -> Optional[float]:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return None
    rx = _rank(x[m])
    ry = _rank(y[m])
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return None
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def _rank(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    r = np.empty(len(a), dtype=np.float64)
    r[order] = np.arange(len(a), dtype=np.float64)
    # average ties
    _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt), dtype=np.float64)
    np.add.at(sums, inv, r)
    return (sums / cnt)[inv]


def perm_null_r_range(values, labels, draws: int = N_PERM_DRAWS,
                      seed: int = PERM_SEED, k: int = N_QUANTILES) -> dict:
    """Within-book label permutation. Holds every measured value fixed and every bin size fixed,
    so a wide raw range is scored against how wide it gets from label assignment alone.

    R3 recorded the error this exists to prevent: a design effect near 1.8 arising from pure
    sampling error. A raw dispersion is not evidence of anything until it has its own null.
    """
    v = np.asarray(values, dtype=np.float64)
    lb = np.asarray(labels, dtype=np.int64)
    m = np.isfinite(v) & (lb >= 0)
    v, lb = v[m], lb[m]
    if len(v) < k:
        return {"p95": None, "draws": 0}
    rng = np.random.default_rng(seed)
    out = np.empty(int(draws), dtype=np.float64)
    for d in range(int(draws)):
        out[d] = r_range(v, rng.permutation(lb), k) or np.nan
    good = out[np.isfinite(out)]
    if not len(good):
        return {"p95": None, "draws": 0}
    return {"p95": float(np.percentile(good, 95)), "median": float(np.median(good)),
            "max": float(good.max()), "draws": int(len(good))}


# ---- Verdicts ---------------------------------------------------------------------------------
def o10_verdict(npa_early, fill_early, npa_late, fill_late) -> str:
    """MATERIAL only if BOTH halves clear BOTH bars. Ambiguous is a NULL (RUN_RULES A6)."""
    vals = (npa_early, fill_early, npa_late, fill_late)
    if any(v is None or not np.isfinite(v) for v in vals):
        return "NULL"
    npa_ok = (npa_early >= NPA_BAR_PP) and (npa_late >= NPA_BAR_PP)
    fill_ok = (fill_early >= FILL_RATE_BAR) and (fill_late >= FILL_RATE_BAR)
    if npa_ok and fill_ok:
        return "MATERIAL"
    if npa_ok and not fill_ok:
        return "PARTIAL"
    return "NULL"


def o18_family_verdict(rng_early, p95_early, sp_early,
                       rng_late, p95_late, sp_late) -> str:
    """WARRANTED needs the range to clear its OWN half's null in both halves AND the ordering to
    agree in sign. A family that clears full-sample but not both halves is reported, not acted on.
    """
    vals = (rng_early, p95_early, sp_early, rng_late, p95_late, sp_late)
    if any(v is None or not np.isfinite(v) for v in vals):
        return "NULL"
    if not (rng_early > p95_early and rng_late > p95_late):
        return "NULL"
    if sp_early == 0 or sp_late == 0 or (sp_early > 0) != (sp_late > 0):
        return "NULL"
    return "WARRANTED"


def month_blocks(dates: Sequence[str]) -> np.ndarray:
    """Calendar-month block id, so the bootstrap resamples months (R3's standing rule)."""
    return np.asarray([str(d)[:7] for d in dates])


def block_bootstrap_mean(values, blocks, draws: int = 2000, seed: int = PERM_SEED) -> dict:
    v = np.asarray(values, dtype=np.float64)
    bl = np.asarray(blocks)
    m = np.isfinite(v)
    v, bl = v[m], bl[m]
    if not len(v):
        return {"mean": None, "lo": None, "hi": None}
    uniq = np.unique(bl)
    idx = {b: np.flatnonzero(bl == b) for b in uniq}
    rng = np.random.default_rng(seed)
    out = np.empty(int(draws), dtype=np.float64)
    for d in range(int(draws)):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([idx[b] for b in pick])
        out[d] = v[sel].mean()
    return {"mean": float(v.mean()), "lo": float(np.percentile(out, 2.5)),
            "hi": float(np.percentile(out, 97.5)), "n_blocks": int(len(uniq))}
