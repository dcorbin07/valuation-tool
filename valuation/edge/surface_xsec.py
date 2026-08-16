"""
ARCHIVED (master audit MA59, 2026-08-15) - a CLOSED study, kept so its
result stays reproducible. It is NOT reachable from the live product and
`tests/test_ma59_quarantine.py` fails if that ever changes.
Still imported by: scripts/o14_tickflow_signals.py, scripts/o3_o4_o5_surface.py, tests/test_surface_xsec.py, valuation/edge/tickflow_signals.py.
Do not extend this module; a new question needs a new register.

O3 + O4 + O5 — the surface-anomaly cross-section on a TRUE delta-hedged instrument.

Pre-registered in `PREREG_o3_o4_o5_surface.md`, committed ALONE at d2aa5f9 before this file
existed.

WHY THIS EXISTS AT ALL, since these three were tested once and REJECTED
----------------------------------------------------------------------
`64955ef` tested all three with the published signs declared first and rejected them. It used a
one-month ATM STRADDLE and said so up front:

    "Straddle, not Cao-Han's delta-hedged call ... their instrument needs roughly a million IV
     solves. A straddle is delta-neutral at inception, which is the property the test needs."

Delta-neutral AT INCEPTION is not delta-neutral. A straddle accumulates directional exposure
immediately and its return variance is dominated by the underlying's move -- exactly the variance
a daily-rebalanced hedge removes. So this module changes the INSTRUMENT and holds everything else
it can fixed. `A1` reuses the prior lane's own `idio_vol` values unchanged, so that arm differs
from the published rejection in the instrument alone.

THE SIGNS ARE DECLARED HERE AND PINNED BY TEST
-----------------------------------------------
Every published sign is "high characteristic predicts LOWER delta-hedged returns", so Q1 should
earn the most. A cross-sectional sort has two ends; a study that picks which end to go long after
seeing the numbers wins half the time by construction. An arm that clears with the sign REVERSED
is reported as CONTRADICTS-PUBLISHED-SIGN and is NOT a candidate.

A CANDIDATE IS NOT AN ADOPTION AND NOT A REVIVAL OF THE ENTRY SIGNAL
--------------------------------------------------------------------
R2 killed the options ENTRY. These are cross-sectional characteristics of the surface, a different
object, measured on a delta-hedged instrument the product does not trade. A positive is a candidate
for a future book that does not yet exist.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Optional, Sequence

import numpy as np

# ---- Pre-committed constants (PREREG_o3_o4_o5_surface §3-§5) --------------------------------
PUBLISHED_SIGNS = {              # +1 = "high characteristic predicts LOWER returns"
    "idio_vol": +1,              # Cao-Han (2013)
    "exp_idio_skew": +1,         # Boyer-Vorkink (2010)
    "vol_of_vol": +1,            # vol-of-vol risk premium
}
ARMS = ("idio_vol", "exp_idio_skew", "vol_of_vol")

DTE_LO, DTE_HI = 20, 45          # contract selection, same band as the prior panel
RATE = 0.03
DIV_YIELD = 0.0                  # q=0 for comparability; O21 measured the effect and it is small
HEDGE_BPS = 5.0                  # ASSUMPTION, not a measurement. 0 bps is a diagnostic.
MIN_HEDGE_DAYS = 10              # solvable contract-days for an event to count

N_QUANTILES = 5
MONO_BAR = 0.6                   # the catalogue's own monotonicity bar, quoted not restated
N_PERM_DRAWS = 2000
N_BOOT_DRAWS = 2000
SEED = 20260812

VOV_WINDOW = 63
MIN_NAMES_PER_DATE = 15          # void condition 1
MIN_DATES = 50                   # void condition 1


# ---- The instrument ---------------------------------------------------------------------------
def delta_hedged_return(days: Sequence[dict], hedge_bps: float = HEDGE_BPS,
                        rate: float = RATE) -> Optional[dict]:
    """Cao-Han normalised delta-hedged gain for one call, rebalanced daily.

        Pi = C_last - C_0 - SUM Delta_i (S_{i+1} - S_i) - SUM r (C_i - Delta_i S_i) dt
        DH = Pi / |Delta_0 S_0 - C_0|

    `days` is ordered and each entry carries `s` (underlying), `mark` (the mid), `delta`, `dt`
    (year fraction to the next day) and, on the ends, `entry_px` / `exit_px` for the traded
    prices. Interior marks are MIDS because they are marks, not trades; only the ends cross the
    spread. Returns None when the event cannot be priced.

    The terminal day has T = 0 and no solvable IV, so the hedge is CARRIED at the last solvable
    delta rather than dropped -- dropping it would silently leave the position unhedged over the
    final move, which is the single largest hedge error available.
    """
    d = [x for x in days if x.get("s") is not None and x.get("mark") is not None]
    if len(d) < 2:
        return None
    solvable = [x for x in d if x.get("delta") is not None]
    if len(solvable) < MIN_HEDGE_DAYS:
        return None

    entry = d[0].get("entry_px") or d[0]["mark"]
    exit_px = d[-1].get("exit_px") or d[-1]["mark"]
    d0, s0 = solvable[0]["delta"], d[0]["s"]
    scale = abs(d0 * s0 - entry)
    if not scale or scale <= 0 or not np.isfinite(scale):
        return None

    pi = float(exit_px) - float(entry)
    hedge_cost = 0.0
    last_delta = d0
    prev_delta = None
    for i in range(len(d) - 1):
        dl = d[i].get("delta")
        if dl is None:
            dl = last_delta                    # carry, never drop
        else:
            last_delta = dl
        pi -= dl * (d[i + 1]["s"] - d[i]["s"])
        pi -= rate * (d[i]["mark"] - dl * d[i]["s"]) * float(d[i].get("dt") or 0.0)
        traded = abs(dl - prev_delta) if prev_delta is not None else abs(dl)
        hedge_cost += traded * d[i]["s"] * (hedge_bps / 10000.0)
        prev_delta = dl
    hedge_cost += abs(prev_delta or 0.0) * d[-1]["s"] * (hedge_bps / 10000.0)
    pi -= hedge_cost
    return {"dh": pi / scale, "pi": pi, "scale": scale, "n_days": len(d),
            "n_solvable": len(solvable), "hedge_cost": hedge_cost,
            "entry": float(entry), "exit": float(exit_px)}


def year_fraction(a: str, b: str) -> float:
    return max((dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days, 0) / 365.0


# ---- Characteristics ----------------------------------------------------------------------------
def vol_of_vol_from_series(iv_by_date: dict, as_of: str, window: int = VOV_WINDOW) -> Optional[float]:
    """Stdev of daily LOG CHANGES in ATM IV, strictly before `as_of`."""
    ds = sorted(d for d in iv_by_date if d < as_of)[-(window + 1):]
    ch = []
    for i in range(1, len(ds)):
        a, b = iv_by_date[ds[i - 1]], iv_by_date[ds[i]]
        if a and b and a > 0 and b > 0:
            ch.append(math.log(b / a))
    if len(ch) < 20:
        return None
    m = sum(ch) / len(ch)
    return math.sqrt(sum((c - m) ** 2 for c in ch) / (len(ch) - 1))


def fit_expected_skew(train: Sequence[dict]) -> Optional[np.ndarray]:
    """Boyer-Vorkink in miniature: OLS of NEXT-period realised idio skew on current
    (idio_skew, idio_vol, mom6). A SIMPLIFICATION of their larger predictor set, labelled as one;
    the predictors are fixed in the register before any fit is run."""
    X, y = [], []
    for t in train:
        v = (t.get("idio_skew"), t.get("idio_vol"), t.get("mom6"), t.get("target"))
        if any(z is None or not np.isfinite(z) for z in v):
            continue
        X.append([1.0, v[0], v[1], v[2]])
        y.append(v[3])
    if len(y) < 40:
        return None
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return beta if np.all(np.isfinite(beta)) else None


def predict_expected_skew(beta, row: dict) -> Optional[float]:
    if beta is None:
        return None
    v = (row.get("idio_skew"), row.get("idio_vol"), row.get("mom6"))
    if any(z is None or not np.isfinite(z) for z in v):
        return None
    return float(beta[0] + beta[1] * v[0] + beta[2] * v[1] + beta[3] * v[2])


# ---- The cross-sectional sort ---------------------------------------------------------------------
def quintiles_within_date(values, dates, k: int = N_QUANTILES) -> np.ndarray:
    """Quintile 0..k-1 assigned WITHIN each formation date, -1 where unusable."""
    v = np.asarray(values, dtype=np.float64)
    d = np.asarray(dates)
    out = np.full(len(v), -1, dtype=np.int64)
    for day in np.unique(d):
        m = (d == day) & np.isfinite(v)
        n = int(m.sum())
        if n < k:
            continue
        idx = np.flatnonzero(m)
        order = idx[np.argsort(v[idx], kind="mergesort")]
        edges = np.linspace(0, n, k + 1).astype(int)
        for j in range(k):
            out[order[edges[j]:edges[j + 1]]] = j
    return out


def long_short_series(rets, labels, dates, k: int = N_QUANTILES):
    """Per-date equal-weighted Q1 minus Q5, plus each date's full quintile means."""
    r = np.asarray(rets, dtype=np.float64)
    lb = np.asarray(labels, dtype=np.int64)
    d = np.asarray(dates)
    days, ls, qmeans = [], [], []
    for day in np.unique(d):
        m = d == day
        row = []
        for j in range(k):
            mm = m & (lb == j) & np.isfinite(r)
            row.append(float(r[mm].mean()) if mm.any() else np.nan)
        if not (np.isfinite(row[0]) and np.isfinite(row[-1])):
            continue
        days.append(str(day))
        ls.append(row[0] - row[-1])
        qmeans.append(row)
    return days, np.asarray(ls, dtype=np.float64), np.asarray(qmeans, dtype=np.float64)


def monotonicity(qmeans: np.ndarray) -> Optional[float]:
    """Spearman of the quintile means against the quintile index, averaged over dates.

    POSITIVE means returns RISE with the characteristic. The published sign is +1 = "high
    predicts LOWER", so a confirming sort is NEGATIVE here.
    """
    if not len(qmeans):
        return None
    idx = np.arange(qmeans.shape[1], dtype=np.float64)
    vals = []
    for row in qmeans:
        if np.all(np.isfinite(row)):
            vals.append(_spearman(idx, row))
    good = [v for v in vals if v is not None]
    return float(np.mean(good)) if good else None


def _spearman(x, y) -> Optional[float]:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if len(x) < 3:
        return None
    rx, ry = _rank(x), _rank(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return None
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def _rank(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    r = np.empty(len(a), dtype=np.float64)
    r[order] = np.arange(len(a), dtype=np.float64)
    _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt), dtype=np.float64)
    np.add.at(sums, inv, r)
    return (sums / cnt)[inv]


def month_block_t(ls: np.ndarray, days: Sequence[str], draws: int = N_BOOT_DRAWS,
                  seed: int = SEED) -> dict:
    """Long-short t under a calendar-month date-block bootstrap. R3's standing rule: a
    trade-level t is never quoted."""
    v = np.asarray(ls, dtype=np.float64)
    m = np.isfinite(v)
    v = v[m]
    blocks = np.asarray([str(d)[:7] for d in np.asarray(days)[m]])
    if len(v) < 3:
        return {"mean": None, "t": None}
    uniq = np.unique(blocks)
    idx = {b: np.flatnonzero(blocks == b) for b in uniq}
    rng = np.random.default_rng(seed)
    out = np.empty(int(draws), dtype=np.float64)
    for i in range(int(draws)):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([idx[b] for b in pick])
        out[i] = v[sel].mean()
    sd = float(out.std(ddof=1))
    mean = float(v.mean())
    return {"mean": mean, "t": (mean / sd) if sd > 0 else None,
            "se": sd, "n_blocks": int(len(uniq)), "n_dates": int(len(v)),
            "ci95": [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]}


def perm_null_ls_t(rets, labels, dates, draws: int = N_PERM_DRAWS, seed: int = SEED) -> dict:
    """Within-DATE label permutation. Holds every return and every bin size fixed and destroys
    only the characteristic-to-return association, so the bar is what label assignment alone
    produces. R3 recorded the error this exists to prevent."""
    r = np.asarray(rets, dtype=np.float64)
    lb = np.asarray(labels, dtype=np.int64)
    d = np.asarray(dates)
    keep = (lb >= 0) & np.isfinite(r)
    r, lb, d = r[keep], lb[keep], d[keep]
    if not len(r):
        return {"p95": None, "draws": 0}
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(d == day) for day in np.unique(d)]
    out = []
    for i in range(int(draws)):
        perm = lb.copy()
        for g in groups:
            perm[g] = rng.permutation(lb[g])
        days, ls, _ = long_short_series(r, perm, d)
        st = month_block_t(ls, days, draws=200, seed=seed + i)
        if st.get("t") is not None:
            out.append(abs(st["t"]))
    if not out:
        return {"p95": None, "draws": 0}
    a = np.asarray(out, dtype=np.float64)
    return {"p95": float(np.percentile(a, 95)), "median": float(np.median(a)),
            "max": float(a.max()), "draws": int(len(a))}


def arm_verdict(mono_early, t_early, p95_early, mean_early,
                mono_late, t_late, p95_late, mean_late, sign: int = +1) -> str:
    """CANDIDATE needs all three conditions in BOTH halves. Sign-reversed clears are reported as
    CONTRADICTS-PUBLISHED-SIGN, never as a find."""
    vals = (mono_early, t_early, p95_early, mean_early,
            mono_late, t_late, p95_late, mean_late)
    if any(v is None or not np.isfinite(v) for v in vals):
        return "NULL"
    # published sign +1 => high predicts LOWER => monotonicity should be NEGATIVE, Q1-Q5 POSITIVE
    want_mono = -1.0 * sign
    conf_e = (mono_early * want_mono >= MONO_BAR) and (mean_early > 0)
    conf_l = (mono_late * want_mono >= MONO_BAR) and (mean_late > 0)
    strong_e = abs(t_early) > p95_early
    strong_l = abs(t_late) > p95_late
    if conf_e and conf_l and strong_e and strong_l:
        return "CANDIDATE"
    rev_e = (mono_early * want_mono <= -MONO_BAR) and (mean_early < 0)
    rev_l = (mono_late * want_mono <= -MONO_BAR) and (mean_late < 0)
    if rev_e and rev_l and strong_e and strong_l:
        return "CONTRADICTS-PUBLISHED-SIGN"
    return "NULL"
