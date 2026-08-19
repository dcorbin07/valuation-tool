"""
ARCHIVED (master audit MA59, 2026-08-15) - a CLOSED study, kept so its
result stays reproducible. It is NOT reachable from the live product and
`tests/test_ma59_quarantine.py` fails if that ever changes.
Still imported by: scripts/u3_convex_overlay.py, tests/test_convex_overlay.py.
Do not extend this module; a new question needs a new register.

U3 — a convex overlay on the equity book, sized as insurance rather than as a strategy.

Registered in `PREREG_u3_convex_overlay.md`, committed ALONE at `9603e64` before this file
existed. Read that register before reading this module; in particular §0.2, §0.4 and §0.5.

WHAT THIS IS FOR
----------------
`VALQUO_EDGE_AUDIT.md:1268` argues that the equity book is short volatility in the tail, that the
options book is a long-volatility sleeve "built by accident", and that their combination has a
property neither has alone. Its step 2 says the conditional correlation of the sleeve to the
equity book in the equity book's worst quarters "is the whole question".

THE PREMISE IS MEASURABLE AND IS NOT ASSUMED HERE
-------------------------------------------------
The banked book is `opt_right == "call"` on 3,870 of 3,870 rows at mean delta +0.3725. A long
call is long vega AND long delta. Whether that behaves as insurance is exactly what `arm_a2`
measures, rather than something this module takes on faith.

THREE SIGN CONVENTIONS THAT HAVE EACH COST A SESSION SOMEWHERE IN THIS PROJECT
-----------------------------------------------------------------------------
1. `max_drawdown` is NEGATIVE. An arm IMPROVES it by being LESS negative, so the gain is
   `arm - base` (S10's first cut computed `base - arm` and reported a 2.61pp worsening as a
   2.61pp improvement).
2. A POSITIVE conditional correlation means the sleeve is NOT insurance. The intuitive reading
   of "high correlation" as "good" is backwards for a hedge.
3. Costs may only make an arm WEAKLY WORSE. A cost model that improves an arm is a bug, and C5
   exists to catch it.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------------------------
# Constants. Every one of these is fixed by the register; changing one is a void condition.
# ---------------------------------------------------------------------------------------------

#: O18's MEASURED effective-to-quoted half-spread ratio (CI95 [0.6617, 0.6871]). Not an
#: assumption. The `$0.0545` availability term O18 decomposed out is deliberately NOT credited
#: here: O18 established it is SELECTED (you avoid it only by trading when the market is there)
#: and may never be quoted as an execution saving.
COST_RHO = 0.6743

#: The X grid from the audit's own method (`:1278`), percent of capital in the equity book.
X_GRID: Tuple[int, ...] = (90, 91, 92, 93, 94, 95, 96, 97, 98, 99)

#: O11's own two concurrency caps. BOTH are reported for every X; neither is selected after the
#: fact, and eligibility requires the conjunction to hold at both.
CONCURRENCY_CAPS: Tuple[int, ...] = (10, 50)

#: A quarter needs this many sleeve trades before it counts as covered.
MIN_TRADES_PER_QUARTER = 5

#: The register's floor on either half (the shipped `min_dates`).
MIN_DATES = 16

#: Periods per year for a 63-trading-day rebalance.
PPY = 252.0 / 63.0

#: C1/C2 tolerances against the published record.
RECORD_TOL = 1e-6

#: The published record the harness must reproduce before ANY arm is read.
RECORD = {
    "top_decile_alpha": 0.071741,
    "long_short_tstat": 2.8361,
    "equal_weight_ann": 0.181371,
}
#: The split-clean options book's own record (U1-SPLIT).
BOOK_MEAN_PNL = 0.032702


class RegisterViolation(AssertionError):
    """Raised when the instrument would depart from `PREREG_u3_convex_overlay.md`.

    Deliberately an AssertionError subclass: a register violation is a bug in the instrument,
    not a data condition to be handled and continued past.
    """


# ---------------------------------------------------------------------------------------------
# Risk/return primitives
# ---------------------------------------------------------------------------------------------

def sharpe(rets: Sequence[float], ppy: float = PPY) -> Optional[float]:
    """Annualised Sharpe of a per-period return series, zero risk-free.

    Returns None on a degenerate series rather than a large number. This is the
    `SECTOR-NEUTRAL-B6` / U2 zero-variance lesson: a guard written as `if sd > 0` passes on a
    constant series whose floating-point sd is ~1e-17 and returns an absurd statistic that reads
    as a spectacular result. The guard here is an explicit tolerance, not `> 0`.
    """
    r = np.asarray([x for x in rets], dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return None
    sd = float(np.std(r, ddof=1))
    if sd <= 1e-12:
        return None
    return float(np.mean(r) / sd * math.sqrt(ppy))


def max_drawdown(rets: Sequence[float]) -> Optional[float]:
    """Worst peak-to-trough of the compounded series. NEGATIVE, or 0.0 if it never falls.

    SIGN: an arm improves this by being LESS negative, so a gain is `arm - base`. Pinned by a
    test carrying S10's real measured pair.
    """
    r = np.asarray([x for x in rets], dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return None
    curve = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(curve)
    dd = curve / peak - 1.0
    return float(np.min(dd))


def drawdown_episodes(rets: Sequence[float], floor: float = -0.05) -> int:
    """How many DISTINCT drawdown episodes deeper than `floor` the series contains.

    Exists because of the register's §4.3: a drawdown improvement resting on one episode may not
    be reported as an adoption. This is the number that has to travel with any such claim, and
    S10 measured that this book's worst drawdown is a single 63-day period.
    """
    r = np.asarray([x for x in rets], dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return 0
    curve = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(curve)
    dd = curve / peak - 1.0
    n, inside = 0, False
    for v in dd:
        if v <= floor and not inside:
            n, inside = n + 1, True
        elif v >= -1e-12:
            inside = False
    return n


def annualised(rets: Sequence[float], ppy: float = PPY) -> Optional[float]:
    """Geometric annualised return of a per-period series."""
    r = np.asarray([x for x in rets], dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return None
    total = float(np.prod(1.0 + r))
    if total <= 0:
        return -1.0
    return float(total ** (ppy / len(r)) - 1.0)


# ---------------------------------------------------------------------------------------------
# The equity leg
# ---------------------------------------------------------------------------------------------

def top_decile_series(qb: Dict) -> pd.DataFrame:
    """The equity book's per-period RETURN series from a shipped `quantile_backtest` payload.

    `top = alpha + equal_weight` is an IDENTITY in the shipped code, not an approximation:
    `fundamental_panel` appends `mean(fwd[top]) - mean(fwd)` and `mean(fwd)` on the same date in
    the same loop. C4 pins it. You cannot compound an alpha, which is why the level is needed.
    """
    ser = qb.get("series")
    if not ser:
        raise RegisterViolation("quantile_backtest must be called with return_series=True")
    if "equal_weight" not in ser:
        raise RegisterViolation(
            "series lacks 'equal_weight' — this build predates the U3 addition, and "
            "reconstructing the benchmark here instead would be a second copy of shipped "
            "arithmetic (the B7 defect class)")
    a = np.asarray(ser["alpha"], dtype=float)
    e = np.asarray(ser["equal_weight"], dtype=float)
    return pd.DataFrame({
        "date": pd.to_datetime(ser["dates"]),
        "top": a + e,
        "equal_weight": e,
        "alpha": a,
    })


# ---------------------------------------------------------------------------------------------
# The sleeve leg
# ---------------------------------------------------------------------------------------------

def _round_trip_cost(spread_pct: float, rho: float) -> float:
    """Round-trip execution cost as a FRACTION of premium.

    Each leg pays `rho` of the QUOTED HALF-spread, so the round trip pays
    `2 * rho * (spread_pct / 2)` = `rho * spread_pct`. `rho < 1` because O18 measured that a real
    trade pays about two thirds of the quoted half-spread — not because a passive fill is free.
    """
    s = float(spread_pct) if np.isfinite(spread_pct) else 0.0
    return max(0.0, rho * max(0.0, s))


def sleeve_curve(book: pd.DataFrame, marks: Dict, boundaries: Sequence[pd.Timestamp],
                 cap: int, rho: float = COST_RHO) -> pd.DataFrame:
    """A capital-constrained, costed mark-to-market curve for the options sleeve.

    Deliberately NOT per-trade P&L attributed to exit dates: a lumpy exit-date attribution puts
    the crash quarter's losses in whatever quarter the position happened to close, which is
    precisely the quarter the whole item is about.

    Sizing follows O11 rather than re-deriving one: equal notional per slot, `cap` slots, and a
    trade arriving when every slot is full is REFUSED (O11 measured 1,677 of 3,870 refused at
    cap 10, and that the refusals cluster in the richest weeks). Idle capital earns zero, which
    is conservative and is stated rather than hidden.

    Returns one row per quarter with the sleeve's total return, trade counts and refusals.
    """
    if cap <= 0:
        raise RegisterViolation("concurrency cap must be positive")
    bd = list(pd.to_datetime(pd.Series(list(boundaries))).sort_values())

    # index marks by (ticker, alert) so a position can be valued on any date it is open
    per: Dict[Tuple[str, pd.Timestamp], pd.Series] = {}
    for (tkr, alert, _expiry, _strike), seq in marks.items():
        if not seq:
            continue
        s = pd.Series({pd.Timestamp(d): float(p) for d, p in seq}).sort_index()
        key = (str(tkr), pd.Timestamp(alert))
        per[key] = s if key not in per else pd.concat([per[key], s]).groupby(level=0).last()

    bk = book.copy()
    bk["alert_ts"] = pd.to_datetime(bk["alert_ts"])
    bk = bk.sort_values("alert_ts").reset_index(drop=True)

    # walk trades in time order, filling slots; a slot frees when its position's marks run out
    slots: List[Optional[Tuple[str, pd.Timestamp, pd.Timestamp]]] = [None] * cap
    taken: List[Dict] = []
    refused = 0
    for _, row in bk.iterrows():
        key = (str(row["ticker"]), pd.Timestamp(row["alert_ts"]))
        s = per.get(key)
        if s is None or len(s) < 2:
            continue
        entry, exit_ = s.index[0], s.index[-1]
        for i, occ in enumerate(slots):
            if occ is None or occ[2] <= entry:
                slots[i] = (key[0], key[1], exit_)
                taken.append({"key": key, "entry": entry, "exit": exit_,
                              "spread": row.get("entry_spread_pct", 0.0)})
                break
        else:
            refused += 1

    unit = 1.0 / cap                       # notional per slot as a fraction of sleeve capital
    rows = []
    for qi in range(len(bd) - 1):
        t0, t1 = bd[qi], bd[qi + 1]
        gross, n = 0.0, 0
        for t in taken:
            s = per[t["key"]]
            w = s[(s.index >= t0) & (s.index < t1)]
            if len(w) < 2:
                continue
            first, last = float(w.iloc[0]), float(w.iloc[-1])
            if first <= 0:
                continue
            r = last / first - 1.0
            # charge the round trip in the quarter the position OPENS in, which is the only
            # quarter in which both legs are attributable to this sleeve's own decision
            if t["entry"] >= t0 and t["entry"] < t1:
                r -= _round_trip_cost(t["spread"], rho)
            gross += unit * r
            n += 1
        rows.append({"date": t0, "sleeve": gross if n else np.nan, "n_open": n})
    out = pd.DataFrame(rows)
    out.attrs["refused"] = refused
    out.attrs["taken"] = len(taken)
    out.attrs["cap"] = cap
    return out


# ---------------------------------------------------------------------------------------------
# Combination and the arms
# ---------------------------------------------------------------------------------------------

def combine(equity: Sequence[float], sleeve: Sequence[float], x_pct: float) -> List[float]:
    """Combined per-period return at `x_pct` percent equity, rebalanced every period.

    At x_pct == 100 this must return the equity series EXACTLY (C8). A sweep whose endpoint does
    not reproduce its own baseline is measuring something other than the overlay.
    """
    if not 0.0 <= x_pct <= 100.0:
        raise RegisterViolation(f"x_pct out of range: {x_pct}")
    w = x_pct / 100.0
    out = []
    for e, s in zip(equity, sleeve):
        if not np.isfinite(e):
            out.append(np.nan)
        elif w == 1.0:
            out.append(float(e))                       # exact, not w*e + 0*s
        elif not np.isfinite(s):
            out.append(np.nan)
        else:
            out.append(float(w * e + (1.0 - w) * s))
    return out


def arm_a1(equity: Sequence[float], sleeve: Sequence[float], early: Sequence[int],
           late: Sequence[int], x_grid: Sequence[int] = X_GRID) -> Dict:
    """A1 — the overlay. ELIGIBLE only if some X improves Sharpe AND max drawdown in BOTH halves.

    The whole curve is reported; no cell is selected after the fact. Both bars are UNCALIBRATED
    (X7 calibrates no floor for Sharpe or drawdown) and are labelled so in the payload.
    """
    def _cells(idx):
        e = [equity[i] for i in idx]
        base = {"sharpe": sharpe(e), "max_drawdown": max_drawdown(e), "ann": annualised(e)}
        out = {}
        for x in x_grid:
            c = combine(e, [sleeve[i] for i in idx], x)
            out[int(x)] = {"sharpe": sharpe(c), "max_drawdown": max_drawdown(c),
                           "ann": annualised(c), "n": int(np.sum(np.isfinite(c)))}
        return base, out

    full_base, full = _cells(range(len(equity)))
    e_base, e_cells = _cells(early)
    l_base, l_cells = _cells(late)

    def _improves(base, cell):
        if base["sharpe"] is None or cell["sharpe"] is None:
            return False
        if base["max_drawdown"] is None or cell["max_drawdown"] is None:
            return False
        # max_drawdown is NEGATIVE: improving means LESS negative, i.e. arm - base > 0
        return (cell["sharpe"] > base["sharpe"]) and (cell["max_drawdown"] - base["max_drawdown"] > 0)

    clearing = [int(x) for x in x_grid
                if _improves(e_base, e_cells[int(x)]) and _improves(l_base, l_cells[int(x)])]
    return {
        "bar": "audit :1284 verbatim — combined Sharpe improves AND max drawdown falls, both halves",
        "bar_calibrated": False,
        "bar_note": "X7 calibrates NO floor for Sharpe or drawdown (S13, S10). Convention only.",
        "baseline": {"full": full_base, "early": e_base, "late": l_base},
        "cells": {"full": full, "early": e_cells, "late": l_cells},
        "x_clearing_both_halves": clearing,
        "verdict": "ELIGIBLE-BUT-UNRESOLVED" if clearing else "REJECTED",
        "unresolved_note": (
            "A favourable A1 rests substantially on ONE drawdown episode; per the register "
            "§4.3 and the audit's own :1549 it may never be reported ADOPTED."
        ) if clearing else None,
    }


def arm_a2(equity: Sequence[float], sleeve: Sequence[float], iv: Sequence[float],
           worst_decile_frac: float = 0.10) -> Dict:
    """A2 — the mechanism. Does the sleeve pay when the equity book does not?

    PRE-COMMITTED READING (register §4/A2, and §0.5 discloses the sign was seen in a crude probe
    before the register): a POSITIVE conditional correlation means the sleeve is NOT insurance,
    and no capital weight can make it insurance.

    Three conditionings are reported and the register says which is which:
      * unconditional — immune to the audit's :1282 trap because it conditions on nothing;
      * IV split — the audit's PRIMARY prescription at :1282;
      * equity worst-decile — the audit's own step 2 at :1279, which IS return-conditioned and
        is reported WITH that label rather than as the clean number.
    """
    e = np.asarray(equity, dtype=float)
    s = np.asarray(sleeve, dtype=float)
    v = np.asarray(iv, dtype=float)
    ok = np.isfinite(e) & np.isfinite(s)
    e, s, v = e[ok], s[ok], v[ok]
    if len(e) < 4:
        return {"status": "insufficient covered quarters"}

    uncond = float(np.corrcoef(e, s)[0, 1])

    okv = np.isfinite(v)
    if okv.sum() >= 4:
        hi = v >= np.nanmedian(v[okv])
        iv_hi = float(np.corrcoef(e[hi & okv], s[hi & okv])[0, 1]) if (hi & okv).sum() >= 3 else None
        iv_lo = float(np.corrcoef(e[~hi & okv], s[~hi & okv])[0, 1]) if (~hi & okv).sum() >= 3 else None
    else:
        iv_hi = iv_lo = None

    k = max(3, int(round(len(e) * worst_decile_frac)))
    worst = np.argsort(e)[:k]
    ret_split = float(np.corrcoef(e[worst], s[worst])[0, 1]) if k >= 3 else None

    return {
        "n_quarters": int(len(e)),
        "correlation_unconditional": uncond,
        "correlation_high_iv": iv_hi,
        "correlation_low_iv": iv_lo,
        "correlation_equity_worst_decile_RETURN_CONDITIONED": ret_split,
        "sleeve_mean_all_quarters": float(np.mean(s)),
        "sleeve_mean_worst_decile": float(np.mean(s[worst])),
        "equity_mean_worst_decile": float(np.mean(e[worst])),
        "n_worst": int(k),
        "is_insurance": bool(uncond < 0.0),
        "reading": (
            "POSITIVE correlation — the sleeve co-moves WITH the equity book, so it is NOT "
            "insurance and no capital weight can make it insurance"
            if uncond >= 0.0 else
            "NEGATIVE correlation — the sleeve moves against the equity book, consistent with "
            "the audit's insurance premise; the SIZE of the benefit is a separate question and "
            "rests on the crash count"
        ),
    }


def arm_a3(equity: Sequence[float], sleeve: Sequence[float],
           x_grid: Sequence[int] = X_GRID) -> Dict:
    """A3 — the cost of carry, in return units. No bar, no verdict, charges no trial."""
    e = np.asarray(equity, dtype=float)
    s = np.asarray(sleeve, dtype=float)
    ok = np.isfinite(e) & np.isfinite(s)
    base_ann = annualised(e[ok])
    out = {}
    for x in x_grid:
        c = combine(e[ok], s[ok], x)
        ca = annualised(c)
        # NAMED FOR ITS SIGN, not for the answer expected. A first cut of this module called it
        # `drag_vs_equity_pp`; the quantity is `combined - equity`, which is POSITIVE when the
        # sleeve ADDS return, and calling that a drag would have printed a gain under a loss's
        # name. Presentational only -- no number changes.
        out[int(x)] = {"ann": ca,
                       "combined_minus_equity_pp": None if (ca is None or base_ann is None)
                       else 100.0 * (ca - base_ann)}
    return {"equity_ann": base_ann,
            "sleeve_ann_geometric": annualised(s[ok]),
            "sleeve_mean_arithmetic": float(np.mean(s[ok])) if ok.any() else None,
            "rebalancing_note": (
                "The combined book is REBALANCED to weight X every quarter (register A1), so a "
                "sleeve whose GEOMETRIC return is deeply negative can still raise the combined "
                "geometric return, because rebalancing harvests its ARITHMETIC mean. Both are "
                "reported so the gap is visible rather than surprising. It also means the "
                "construction TOPS THE SLEEVE BACK UP after a crash quarter, which flatters it."),
            "by_x": out}


def halves(n: int, min_dates: int = MIN_DATES) -> Tuple[List[int], List[int], int]:
    """Split `n` covered quarters into early/late with the boundary embargoed.

    Raises rather than returning a thin split: the register's void condition 4 says fewer than
    16 in either half voids the run, and a silent thin split is how a gate stops meaning what it
    says.
    """
    if n < 2 * min_dates + 1:
        raise RegisterViolation(
            f"{n} covered quarters cannot make two halves of >= {min_dates} with an embargo")
    b = n // 2
    return list(range(0, b)), list(range(b + 1, n)), b
