"""Fractional Kelly and ruin for the options paper book.  [O12]

Pre-registered in `PREREG_o12_kelly_ruin.md`, committed before this file existed.

THE CAVEAT IS PART OF THE MODULE, NOT A FOOTNOTE. Kelly sizing requires an edge that is real,
and R2 says this book's entry is dead: +3.2702%/trade against a random-entry control's +8.3342%
(split-clean, U1-SPLIT). Every fraction computed here is conditional on a distribution the
project has already shown is WORSE than random entry on the same names. Nothing in this module
is a position-sizing recommendation for real money.

WHAT IT COMPUTES. The growth-optimal fraction on the EMPIRICAL return distribution — not on a
two-outcome approximation, which would be badly wrong for a barbell whose median trade is -52%
and whose best is +782%. Then where ruin lives at that fraction and its divisors, by a
month-block bootstrap (R3's clustering rule; i.i.d. resampling of options trades is exactly the
error R3 exists to prevent).

THE HARD UPPER BOUND IS ARITHMETIC, NOT A FINDING. The worst trade in the book returns -101.44%
— a total loss of premium PLUS commission, which is correct accounting and was checked rather
than assumed. So `log(1 + f*R)` is undefined at and above `f = 1/1.0144 = 0.98580`, and no
fraction at or beyond that can be evaluated at all.

No I/O, no network: callers pass returns in. The algebra stays testable where there is no
licensed data, which is every CI runner.
"""
from __future__ import annotations

import math
import random
from typing import Iterable, Optional

F_MIN = 0.0005
F_STEP = 0.0005
GOLDEN_ITERS = 200
DEFAULT_PATHS = 10000

# Ruin thresholds, fixed in the register before anything ran.
RUIN_TERMINAL = (0.5, 0.2)
RUIN_DRAWDOWN = (0.5, 0.8)


def max_fraction(returns: Iterable[float]) -> float:
    """The largest `f` at which `log(1 + f*R)` is defined for every trade, minus a hair.

    Arithmetic, not a result: a trade returning worse than -100% caps leverage below 1.0.
    """
    rs = [float(r) for r in returns]
    worst = min(rs) if rs else -1.0
    if worst >= 0:
        return 1.0
    return (1.0 / abs(worst)) * (1.0 - 1e-9)


def growth(returns: list, f: float) -> Optional[float]:
    """E[log(1 + f*R)] on the empirical distribution. None if `f` is out of the defined range.

    The readable reference. `grid_growth` below is the vectorised form the optimiser actually
    calls; `tests/test_kelly.py` proves the two agree rather than assuming it.
    """
    if f <= 0:
        return 0.0
    tot = 0.0
    for r in returns:
        x = 1.0 + f * r
        if x <= 0:
            return None
        tot += math.log(x)
    return tot / len(returns)


def grid_growth(returns, fs):
    """`growth` evaluated at every `f` in `fs` at once — one C-level outer product.

    This exists for a measured reason, not for tidiness: the month-block bootstrap re-optimises
    `f*` on each of 400 resamples, and a pure-Python grid over ~2,000 fractions x 3,870 returns
    is ~3 billion `log` calls. The first attempt at this item did not finish and had to be
    killed. Out-of-range cells become -inf so they lose the argmax without special-casing.
    """
    import numpy as np

    r = np.asarray(returns, dtype=float)
    f = np.asarray(fs, dtype=float)
    x = 1.0 + f[:, None] * r[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(x > 0, np.log(np.where(x > 0, x, 1.0)), -np.inf)
    return g.mean(axis=1)


def kelly_fraction(returns: list, f_min: float = F_MIN, step: float = F_STEP) -> dict:
    """`f*` maximising empirical log-growth, by a fixed grid then golden-section refinement.

    The grid is fixed in the register and is NOT tuned to the answer. If the mean return is <= 0
    the answer is exactly 0 and is returned as such: `G'(0) = mean(R)`, so a non-positive mean
    admits no positive optimal fraction. Returning 0 here rather than a tiny grid artefact is
    what makes the zero-edge control in the register a real check on the implementation.
    """
    rs = [float(r) for r in returns]
    if not rs:
        return {"f_star": None, "growth_at_f_star": None, "f_max": None, "n": 0}
    fmax = max_fraction(rs)
    mean_r = sum(rs) / len(rs)
    if mean_r <= 0:
        return {"f_star": 0.0, "growth_at_f_star": 0.0, "f_max": fmax, "n": len(rs),
                "mean_return": mean_r, "note": "mean <= 0, so no positive fraction is optimal"}

    import numpy as np

    grid = np.arange(f_min, fmax, step)
    best_f, best_g = 0.0, 0.0
    if len(grid):
        gs = grid_growth(rs, grid)
        i = int(np.nanargmax(gs))
        if np.isfinite(gs[i]) and gs[i] > 0:
            best_f, best_g = float(grid[i]), float(gs[i])

    lo = max(0.0, best_f - step)
    hi = min(fmax, best_f + step)
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    for _ in range(GOLDEN_ITERS):
        if b - a < 1e-12:
            break
        c, d = b - phi * (b - a), a + phi * (b - a)
        # Both probe points in one vectorised call: this runs inside the 400-draw bootstrap, so
        # a pure-Python pass over 3,870 returns per probe is what made the first attempt at this
        # item fail to finish.
        gcd = grid_growth(rs, [c, d])
        gc = float(gcd[0]) if math.isfinite(float(gcd[0])) else None
        gd = float(gcd[1]) if math.isfinite(float(gcd[1])) else None
        if gc is None:
            a = c
            continue
        if gd is None:
            b = d
            continue
        if gc < gd:
            a = c
        else:
            b = d
    fs = (a + b) / 2.0
    gs = growth(rs, fs)
    if gs is None or gs < best_g:
        fs, gs = best_f, best_g
    return {"f_star": fs, "growth_at_f_star": gs, "f_max": fmax, "n": len(rs),
            "mean_return": mean_r}


# ------------------------------------------------------------------------------------------- #
# Month-block resampling — R3's clustering rule
# ------------------------------------------------------------------------------------------- #
def month_blocks(rows: list, ret: str = "pnl_pct", date: str = "alert_ts") -> list:
    """Group returns into calendar-month blocks, so a resample moves whole months."""
    by = {}
    for r in rows:
        d = str(r.get(date) or "")[:7]
        v = r.get(ret)
        if not d or v is None:
            continue
        by.setdefault(d, []).append(float(v))
    return [by[k] for k in sorted(by)]


def block_resample(blocks: list, n_target: int, rng: random.Random) -> list:
    out = []
    if not blocks:
        return out
    while len(out) < n_target:
        out.extend(blocks[rng.randrange(len(blocks))])
    return out[:n_target]


def bootstrap_f_star(blocks: list, n_target: int, n_draws: int = 400, seed: int = 0) -> dict:
    """CI95 for `f*` by month-block resampling. Slow by construction — `f*` is re-optimised
    on every draw, because resampling and then reusing the point estimate's fraction would
    measure the wrong thing."""
    rng = random.Random(seed)
    xs = []
    for _ in range(n_draws):
        s = block_resample(blocks, n_target, rng)
        k = kelly_fraction(s)
        if k.get("f_star") is not None:
            xs.append(k["f_star"])
    if not xs:
        return {"n_draws": 0}
    return {"n_draws": len(xs), "p2_5": _pct(xs, 2.5), "p50": _pct(xs, 50),
            "p97_5": _pct(xs, 97.5), "min": min(xs), "max": max(xs),
            "share_at_zero": sum(1 for x in xs if x <= 1e-9) / len(xs)}


def _pct(xs: list, q: float) -> float:
    ys = sorted(xs)
    pos = q / 100.0 * (len(ys) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(ys) - 1)
    frac = pos - lo
    return ys[lo] * (1 - frac) + ys[hi] * frac


# ------------------------------------------------------------------------------------------- #
# Ruin
# ------------------------------------------------------------------------------------------- #
def ruin_profile(blocks: list, f: float, n_trades: int, n_paths: int = DEFAULT_PATHS,
                 seed: int = 0) -> dict:
    """Sequential compounding at fraction `f` over `n_trades`, month-block resampled.

    CONCURRENCY CAVEAT, stated in the output rather than left to the reader: the live book holds
    several positions at once, so real trades are not sequential. Sequential compounding is the
    standard Kelly frame and it UNDERSTATES the drawdown of a concurrent book, because
    simultaneous positions can lose together. These figures are therefore a floor on the pain,
    not an estimate of it.
    """
    rng = random.Random(seed)
    term, dd = [], []
    for _ in range(n_paths):
        rs = block_resample(blocks, n_trades, rng)
        w, peak, worst = 1.0, 1.0, 0.0
        busted = False
        for r in rs:
            w *= (1.0 + f * r)
            if w <= 0:
                busted = True
                w = 0.0
                break
            peak = max(peak, w)
            worst = max(worst, 1.0 - w / peak)
        term.append(w)
        dd.append(1.0 if busted else worst)
    out = {"f": f, "n_paths": n_paths, "n_trades": n_trades,
           "median_terminal": _pct(term, 50),
           "p5_terminal": _pct(term, 5), "p95_terminal": _pct(term, 95),
           "median_max_drawdown": _pct(dd, 50),
           "concurrency_caveat": ("sequential compounding understates a concurrent book's "
                                  "drawdown; treat these as a floor")}
    for t in RUIN_TERMINAL:
        out["p_terminal_below_%gx" % t] = sum(1 for x in term if x < t) / len(term)
    for t in RUIN_DRAWDOWN:
        out["p_drawdown_over_%d" % int(t * 100)] = sum(1 for x in dd if x > t) / len(dd)
    return out


def zero_edge(returns: Iterable[float]) -> list:
    """Returns shifted so the mean is exactly zero — the register's implementation check."""
    rs = [float(r) for r in returns]
    if not rs:
        return []
    m = sum(rs) / len(rs)
    return [r - m for r in rs]


def implied_fraction(premium: float, contracts: int, equity: float) -> Optional[float]:
    """What flat sizing actually stakes: contracts * 100 * premium / equity."""
    if not equity or equity <= 0:
        return None
    return (contracts * 100.0 * float(premium)) / float(equity)


def equity_for_fraction(premium: float, contracts: int, f: float) -> Optional[float]:
    """The account size at which flat sizing equals fraction `f`. The actionable inversion —
    it needs no knowledge of anyone's real account balance."""
    if not f or f <= 0:
        return None
    return (contracts * 100.0 * float(premium)) / float(f)
