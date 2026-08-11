"""How big must a bucket be before one lucky contract cannot flip its verdict?  [O26]

Pre-registered in `PREREG_o26_bucket_floor.md`, committed before this file existed.

`options_tracker.MIN_CLOSED_PER_BUCKET = 30` gates whether a subgroup may be tuned on or reported
as judgeable. Its own comment says what it is for:

    "Options outcomes are noisy and heavy-tailed: with ten trades a single triple-up decides the
     sign of every statistic. 30 is not a magic number, it is 'enough that one lucky contract
     cannot flip the verdict'."

That is a testable property and it has never been tested. This module measures it directly:
`P_flip(n)` is the probability that removing the SINGLE most extreme trade flips the sign of a
size-`n` bucket's mean.

WHY "MOST EXTREME" AND NOT "BEST". The trade removed is `argmax |R - mean|`, selected without
reference to which way it moves the mean. Removing the *best* trade instead would build the
answer's direction into its own definition and would guarantee a downward push on every draw.

No I/O and no data access: callers pass returns in, so the algebra stays testable where there is
no licensed data, which is every CI runner.
"""
from __future__ import annotations

import random
from typing import Iterable, Optional

# The candidate grid, fixed in the register. Extending it after seeing the curve voids the item.
N_GRID = (10, 20, 30, 40, 50, 75, 100, 150, 200, 300)
DRAWS = 5000
FLIP_BAR = 0.05
SHIPPED_FLOOR = 30


def most_extreme_index(rs: list) -> int:
    """Index of `argmax |R - mean|`. Ties break to the lowest index, deterministically."""
    m = sum(rs) / len(rs)
    best_i, best_d = 0, -1.0
    for i, r in enumerate(rs):
        d = abs(r - m)
        if d > best_d:
            best_i, best_d = i, d
    return best_i


def flips_sign(rs: list) -> Optional[bool]:
    """Does dropping the single most extreme trade flip the sign of the mean?

    A bucket whose mean is exactly zero has no sign to flip and returns None rather than being
    scored either way -- counting it as a flip would inflate the statistic, counting it as a
    non-flip would deflate it, and on a continuous distribution it essentially never happens.
    """
    if len(rs) < 2:
        return None
    m0 = sum(rs) / len(rs)
    if m0 == 0:
        return None
    i = most_extreme_index(rs)
    rest = rs[:i] + rs[i + 1:]
    m1 = sum(rest) / len(rest)
    if m1 == 0:
        return True                      # moved off a definite sign onto nothing: a flip
    return (m0 > 0) != (m1 > 0)


def p_flip(returns: list, n: int, draws: int = DRAWS, seed: int = 0) -> dict:
    """`P_flip(n)` by drawing size-`n` buckets with replacement from `returns`."""
    rng = random.Random(seed)
    rs = [float(x) for x in returns]
    if not rs or n < 2:
        return {"n": n, "draws": 0, "p_flip": None}
    flips = 0
    scored = 0
    for _ in range(draws):
        b = [rs[rng.randrange(len(rs))] for _ in range(n)]
        f = flips_sign(b)
        if f is None:
            continue
        scored += 1
        flips += 1 if f else 0
    return {"n": n, "draws": scored, "p_flip": (flips / scored) if scored else None}


def curve(returns: list, grid: Iterable[int] = N_GRID, draws: int = DRAWS,
          seed: int = 0) -> list:
    return [p_flip(returns, n, draws=draws, seed=seed + i)
            for i, n in enumerate(grid)]


def floor_from_curve(rows: list, bar: float = FLIP_BAR) -> Optional[int]:
    """Smallest `n` on the grid with `P_flip(n) <= bar`. None if nothing on the grid clears."""
    for r in sorted(rows, key=lambda d: d["n"]):
        if r["p_flip"] is not None and r["p_flip"] <= bar:
            return r["n"]
    return None


def half_sign_agreement(returns: list, n: int, draws: int = DRAWS, seed: int = 0) -> dict:
    """SECONDARY: split each drawn bucket in half and ask whether the halves agree in sign.

    Independent of the primary -- a bucket can be robust to losing its most extreme trade and
    still not replicate across its own halves, and vice versa. Reported separately rather than
    combined into a single score, because averaging two criteria hides which one failed.
    """
    rng = random.Random(seed)
    rs = [float(x) for x in returns]
    if not rs or n < 4:
        return {"n": n, "draws": 0, "agreement": None}
    agree = 0
    scored = 0
    for _ in range(draws):
        b = [rs[rng.randrange(len(rs))] for _ in range(n)]
        h = n // 2
        a, c = b[:h], b[h:]
        ma, mc = sum(a) / len(a), sum(c) / len(c)
        if ma == 0 or mc == 0:
            continue
        scored += 1
        agree += 1 if ((ma > 0) == (mc > 0)) else 0
    return {"n": n, "draws": scored, "agreement": (agree / scored) if scored else None}


def verdict(floor_early: Optional[int], floor_late: Optional[int],
            grid: Iterable[int] = N_GRID, shipped: int = SHIPPED_FLOOR) -> str:
    """The pre-committed rule. A NULL keeps the shipped value -- the failure direction is always
    'keep 30', never 'adopt an unvalidated number'."""
    g = list(grid)
    if floor_early is None or floor_late is None:
        return "NULL"
    try:
        ie, il = g.index(floor_early), g.index(floor_late)
    except ValueError:
        return "NULL"
    if abs(ie - il) > 1:
        return "NULL"
    return "RAISE" if max(floor_early, floor_late) > shipped else "KEEP_30"
