"""
ARCHIVED (master audit MA59, 2026-08-15) - a CLOSED study, kept so its
result stays reproducible. It is NOT reachable from the live product and
`tests/test_ma59_quarantine.py` fails if that ever changes.
Still imported by: scripts/o6_o7_o17_earnings.py, tests/test_earnings_surface.py.
Do not extend this module; a new question needs a new register.

O6 + O7 + O17 — the earnings-and-surface-selection family.

Pure, testable pieces for `PREREG_o6_o7_o17_earnings_surface.md`. Every constant here is the
register's, fixed before any measurement code existed.

THE ONE RULE THAT MATTERS MOST IN THIS FILE, and the reason several functions return `None`
where a bool would be more convenient: **a missing earnings date is UNKNOWN, never SAFE.**
29 of the book's 186 names are foreign private issuers with ZERO Sharadar code-22 coverage
(they file 20-F/6-K, not 8-K), carrying 10.0% of the trades. A filter that reads "no date" as
"no announcement" fails open on a systematically non-random tenth of the book. This lane has
already declined once to ship an earnings filter with that failure mode, and the `None` return
is how the refusal is enforced rather than merely intended.

Month-block inference is NOT re-implemented here — it is imported from `options_stats`, R3's
shipped module, so this register quotes the same arithmetic every other options result does.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional, Sequence

import numpy as np

# ---------------------------------------------------------------------------------------------
# Register constants — §2, §3, §4, §8 of PREREG_o6_o7_o17_earnings_surface.md
SEED = 20260812
N_PERM_DRAWS = 2000

# O6 — candidate set and the four rules
MONEYNESS_LO = 0.90              # the engine's own band, not a new degree of freedom
MONEYNESS_HI = 1.20
DELTA_BAND = 0.05                # O6a: "within +/-0.05 delta of target"
IV_RANK_WINDOW = 252             # O6b: "that name's own trailing IV rank"
SMILE_MIN_POINTS = 5             # a quadratic needs 3; 5 is the register's honest minimum
TAIL_K = 5                       # the audit's own tail-concentration clause

# O7 — earnings straddles
O7_PRE_DAYS = 3                  # Gao-Xing-Zhang: bought three days before
O7_POST_DAYS = 1                 # closed the day after
O7_COVERAGE_FLOOR = 0.40         # below this the backtest arm is COVERAGE-BOUND, no verdict

# O17 — the filter
O17_WINDOWS = (5, 10, 15)
RETENTION_FLOOR = 0.70           # a filter that refuses almost everything is a different product

# void conditions (§8.1)
MIN_TRADES_O6 = 2000
MIN_EVENTS_O7 = 500

RATE = 0.03
DIV_YIELD = 0.0                  # q=0 for comparability; O21 measured the effect and it is small


# ---------------------------------------------------------------------------------------------
# O6 — contract selection
def moneyness(strike: float, spot: float) -> Optional[float]:
    if not spot or spot <= 0 or strike is None:
        return None
    return float(strike) / float(spot)


def in_band(strike: float, spot: float) -> bool:
    """The engine's own 0.90-1.20 moneyness band, inclusive at both ends."""
    m = moneyness(strike, spot)
    if m is None:
        return False
    return (m >= MONEYNESS_LO - 1e-12) and (m <= MONEYNESS_HI + 1e-12)


def iv_rank(history: Sequence[float], current: float) -> Optional[float]:
    """Share of the trailing window at or below `current`. O6b's within-name cheapness measure.

    Returns None on an empty history rather than a neutral 0.5, so a name with no history is
    EXCLUDED from O6b rather than silently scored as median.
    """
    h = [float(x) for x in history if x is not None and np.isfinite(x)]
    if not h or current is None or not np.isfinite(current):
        return None
    return float(np.mean([1.0 if x <= current else 0.0 for x in h]))


def fit_smile(log_moneyness: Sequence[float], iv: Sequence[float]) -> Optional[np.ndarray]:
    """Quadratic fit of IV on log-moneyness across one date's chain (O6c)."""
    x = np.asarray(log_moneyness, dtype=np.float64)
    y = np.asarray(iv, dtype=np.float64)
    m = np.isfinite(x) & np.isfinite(y) & (y > 0)
    if int(m.sum()) < SMILE_MIN_POINTS:
        return None
    x, y = x[m], y[m]
    if np.ptp(x) <= 0:
        return None
    try:
        return np.polyfit(x, y, 2)
    except Exception:
        return None


def smile_residuals(log_moneyness: Sequence[float], iv: Sequence[float]) -> Optional[np.ndarray]:
    """Actual minus fitted IV. NEGATIVE = cheap relative to the surface it sits on."""
    beta = fit_smile(log_moneyness, iv)
    if beta is None:
        return None
    x = np.asarray(log_moneyness, dtype=np.float64)
    y = np.asarray(iv, dtype=np.float64)
    return y - np.polyval(beta, x)


def vega_per_spread(vega: float, spread: float) -> Optional[float]:
    """O6d: the most theta-efficient expression of the same directional view."""
    if vega is None or spread is None:
        return None
    if not np.isfinite(vega) or not np.isfinite(spread) or spread <= 0:
        return None
    return float(vega) / float(spread)


def pick_extreme(values: Sequence[Optional[float]], lowest: bool = True) -> Optional[int]:
    """Index of the min (or max) finite value; None if nothing is scoreable."""
    idx, best = None, None
    for i, v in enumerate(values):
        if v is None or not np.isfinite(v):
            continue
        if best is None or (v < best if lowest else v > best):
            idx, best = i, float(v)
    return idx


def delta_eligible(deltas: Sequence[Optional[float]], target: float,
                   band: float = DELTA_BAND) -> np.ndarray:
    """O6a's gate: candidates within +/-band of the banked target delta."""
    out = np.zeros(len(deltas), dtype=bool)
    if target is None or not np.isfinite(target):
        return out
    for i, d in enumerate(deltas):
        if d is not None and np.isfinite(d) and abs(float(d) - float(target)) <= band + 1e-12:
            out[i] = True
    return out


def tail_concentration(pnls: Sequence[float], k: int = TAIL_K) -> Optional[float]:
    """Share of total POSITIVE P&L carried by the best k trades (the audit's own clause).

    Measured on the positive side only: with a barbell payoff the signed total can approach zero
    and make a ratio explode, which would flag concentration that is an artefact of the
    denominator rather than of the tail.
    """
    v = np.asarray([x for x in pnls if x is not None and np.isfinite(x)], dtype=np.float64)
    if v.size == 0:
        return None
    pos = v[v > 0]
    if pos.size == 0 or pos.sum() <= 0:
        return None
    top = np.sort(pos)[::-1][:max(1, int(k))]
    return float(top.sum() / pos.sum())


# ---------------------------------------------------------------------------------------------
# O17 — the earnings filter. UNKNOWN is never SAFE.
def _d(x) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def refuse_within(entry: str, earnings: Sequence[str], window_days: int) -> Optional[bool]:
    """True = the filter REFUSES this entry (an announcement lands within `window_days` after it).

    Returns **None for UNKNOWN** — no earnings coverage for this name — and the caller MUST drop
    those rows rather than treat them as False. Returning False here would be the fail-open bug
    this whole register is built to avoid, so it is not reachable from an empty calendar.
    """
    e = _d(entry)
    if e is None:
        return None
    ds = sorted(x for x in (_d(v) for v in (earnings or [])) if x is not None)
    if not ds:
        return None
    for a in ds:
        if 0 <= (a - e).days <= int(window_days):
            return True
    return False


def owns_the_event(entry: str, expiry: str, earnings: Sequence[str]) -> Optional[bool]:
    """C4: True when the contract's EXPIRY falls after the next announcement, so the position
    owns the event rather than paying decay into it and exiting first. None = UNKNOWN."""
    e, x = _d(entry), _d(expiry)
    if e is None or x is None:
        return None
    ds = sorted(v for v in (_d(v) for v in (earnings or [])) if v is not None)
    if not ds:
        return None
    nxt = [a for a in ds if a > e]
    if not nxt:
        return None
    return bool(x > nxt[0])


def partition(rows: Sequence[dict], decide) -> dict:
    """Split rows into kept / refused / unknown by a decision function returning True/False/None.

    The `unknown` bucket is returned explicitly and separately so a caller cannot silently fold
    it into either side.
    """
    kept, refused, unknown = [], [], []
    for r in rows:
        d = decide(r)
        if d is None:
            unknown.append(r)
        elif d:
            refused.append(r)
        else:
            kept.append(r)
    return {"kept": kept, "refused": refused, "unknown": unknown}


# ---------------------------------------------------------------------------------------------
# Calibrated nulls — §3. Every bar is a permutation p95, never the conventional 2.0.
def perm_null_removal(pnls: Sequence[float], n_remove: int, draws: int = N_PERM_DRAWS,
                      seed: int = SEED) -> dict:
    """O17's null: remove a RANDOM subset of the SAME SIZE and record the improvement.

    A filter that removes trades changes expectancy mechanically; this asks whether removing
    THESE trades does.
    """
    v = np.asarray([x for x in pnls if x is not None and np.isfinite(x)], dtype=np.float64)
    n = v.size
    k = int(n_remove)
    if n == 0 or k <= 0 or k >= n:
        return {"p95": None, "median": None, "draws": 0}
    base = float(v.mean())
    rng = np.random.default_rng(seed)
    out = np.empty(int(draws), dtype=np.float64)
    for i in range(int(draws)):
        keep = rng.permutation(n)[k:]
        out[i] = float(v[keep].mean()) - base
    return {"p95": float(np.percentile(out, 95)), "median": float(np.median(out)),
            "draws": int(draws)}


def perm_null_switch(per_trade_alternatives: Sequence[Sequence[float]],
                     base: Sequence[float], draws: int = N_PERM_DRAWS,
                     seed: int = SEED) -> dict:
    """O6's null, and the sharpest thing in this register: switch each trade to a RANDOM
    alternative contract from its OWN candidate set, and record the improvement.

    Any contract switch moves expectancy. This isolates whether CHEAPNESS specifically does,
    which a raw improvement over the incumbent cannot show.
    """
    b = np.asarray([x for x in base if x is not None and np.isfinite(x)], dtype=np.float64)
    pool = [np.asarray([y for y in alts if y is not None and np.isfinite(y)], dtype=np.float64)
            for alts in per_trade_alternatives]
    if b.size == 0 or len(pool) != b.size or any(p.size == 0 for p in pool):
        return {"p95": None, "median": None, "draws": 0}
    rng = np.random.default_rng(seed)
    base_mean = float(b.mean())
    out = np.empty(int(draws), dtype=np.float64)
    for i in range(int(draws)):
        pick = np.array([p[rng.integers(0, p.size)] for p in pool], dtype=np.float64)
        out[i] = float(pick.mean()) - base_mean
    return {"p95": float(np.percentile(out, 95)), "median": float(np.median(out)),
            "draws": int(draws)}


# ---------------------------------------------------------------------------------------------
# Verdict rules — §4, fixed before any number existed. Ambiguous against a bar is a NULL (A6).
def _clears(gain, p95) -> bool:
    return (gain is not None and p95 is not None and np.isfinite(gain) and np.isfinite(p95)
            and gain > p95)


def o6_verdict(gain_early, p95_early, tail_early_base, tail_early_arm,
               gain_late, p95_late, tail_late_base, tail_late_arm) -> str:
    """CANDIDATE iff in BOTH halves the gain is positive, clears the arm's own
    random-alternative p95, and tail concentration does not rise."""
    for g, p, tb, ta in ((gain_early, p95_early, tail_early_base, tail_early_arm),
                         (gain_late, p95_late, tail_late_base, tail_late_arm)):
        if g is None or not np.isfinite(g) or g <= 0:
            return "NULL"
        if not _clears(g, p):
            return "NULL"
        if tb is not None and ta is not None and np.isfinite(tb) and np.isfinite(ta) and ta > tb:
            return "NULL"
    return "CANDIDATE"


def o17_verdict(gain_early, p95_early, retention_early,
                gain_late, p95_late, retention_late) -> str:
    """CANDIDATE iff in BOTH halves the gain is positive, clears the matched random-removal p95,
    and at least RETENTION_FLOOR of trades survive."""
    for g, p, ret in ((gain_early, p95_early, retention_early),
                      (gain_late, p95_late, retention_late)):
        if g is None or not np.isfinite(g) or g <= 0:
            return "NULL"
        if not _clears(g, p):
            return "NULL"
        if ret is None or not np.isfinite(ret) or ret < RETENTION_FLOOR:
            return "NULL"
    return "CANDIDATE"


def o7_direction(mean_diff, ci_lo, ci_hi) -> str:
    """B1 returns a DIRECTION, not a pass/fail. realised - implied:
    CHEAP  = realised exceeds implied (Gao-Xing-Zhang's published sign)
    RICH   = implied exceeds realised (the retail 'sell the IV crush' view)
    NULL   = the interval includes zero."""
    if mean_diff is None or ci_lo is None or ci_hi is None:
        return "NULL"
    if not all(np.isfinite(x) for x in (mean_diff, ci_lo, ci_hi)):
        return "NULL"
    if ci_lo > 0:
        return "CHEAP"
    if ci_hi < 0:
        return "RICH"
    return "NULL"
