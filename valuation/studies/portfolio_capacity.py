"""O11 + O19 + O22 + O25 — the portfolio-and-capacity batch.

Pure, testable pieces for `PREREG_o11_o19_o22_o25_portfolio.md`. Every constant is the
register's, fixed before any measurement code existed.

TWO THINGS IN THIS FILE ARE STRUCTURAL RATHER THAN ANALYTICAL, and both exist because a previous
session got them wrong:

1. **`assert_raw_spot` RAISES.** The U1-SPLIT defect class - as-traded strikes matched against a
   split-adjusted price series - has now appeared twice, most recently in session 30's own
   instrument, where it inflated an implied move from 5.45% to 19.57% and would have shipped a
   confident verdict built on it. It fails silently by nature: the option still prices, it is
   merely mostly intrinsic. So the guard is a hard failure, not a warning; a warning nobody reads
   is exactly how it survived to a second appearance.

2. **`o19_verdict` is read before any O11 number exists**, enforced by the runner refusing to
   score O11 without O19's artifact. Session 26 computed a gating control and its outcome
   statistics in the same pass and had to report that the control could not be claimed to have
   been read first.

`simulate_book`, the month-block bootstrap and `contracts_for` are IMPORTED from the shipped
modules rather than re-implemented, so this register quotes the same arithmetic every other
options result does (B7's defect class).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional, Sequence

import numpy as np

from valuation.edge.options_sizing import RISK_PER_TRADE, contracts_for  # noqa: F401

# ---------------------------------------------------------------------------------------------
# Register constants
SEED = 20260812
N_BOOT = 2000

# §2 - the split guard
SPOT_TOL = 1e-6

# §3.1 O19
O19_FLOORS = (1.0, 2.0)
O19_ARTEFACT_PP = 2.00          # a floor moving expectancy by more than this, CI excluding zero

# §3.2 O11 - four named cells, NO grid
O11_CELLS = ((50000.0, 10), (50000.0, 50), (250000.0, 10), (250000.0, 50))
DD_UNSURVIVABLE = 0.50
DD_SURVIVABLE = 0.25

# §3.3 O22
O22_LAMBDAS = (0.5, 1.0, 2.0)
O22_LAMBDA_HEADLINE = 1.0
O22_ALPHA = 1.5                 # P1's functional form: cost scales with participation^(alpha-1)

# §3.4 O25
O25_THRESHOLDS = (0.75, 1.00)
WING_DELTA = 0.15
RATE = 0.03
DIV_YIELD = 0.0

# §8 void floors
MIN_MARKED_TRADES = 3000
MIN_CROSSINGS = 200


class SpotBasisError(AssertionError):
    """Raised when a price series does not agree with the book's own as-traded spot."""


def assert_raw_spot(book_rows: Sequence[dict], close_by_ticker: dict,
                    tol: float = SPOT_TOL) -> dict:
    """**RAISES** if a price series is not on the book's as-traded basis.

    `close_by_ticker` is {ticker: {date: price}}. Compared against each row's own
    `underlying_entry`, which is as-traded by construction. Session 30 measured that `raw_close`
    agrees to a median relative error of 0.00000 while the adjusted `close` is off by >5% on 67%
    of entries - so this separates the two decisively and cheaply.

    It returns a report for the artifact, but the RETURN IS NOT THE POINT: on failure it raises,
    because the defect it guards is silent and a warning would be ignored.
    """
    errs, checked, worst = [], 0, None
    for r in book_rows:
        s = float(r.get("underlying_entry") or 0.0)
        if s <= 0:
            continue
        px = (close_by_ticker.get(r["ticker"]) or {}).get(str(r["alert_ts"]))
        if px is None or not np.isfinite(px) or px <= 0:
            continue
        checked += 1
        e = abs(float(px) / s - 1.0)
        errs.append(e)
        if worst is None or e > worst[0]:
            worst = (e, r["ticker"], str(r["alert_ts"]), float(px), s)
    if not checked:
        raise SpotBasisError(
            "assert_raw_spot: NOTHING could be checked - no overlapping (ticker, date) between "
            "the price series and the book. A guard that checks nothing passes vacuously, which "
            "is the failure mode it exists to prevent.")
    med = float(np.median(errs))
    if med > tol:
        raise SpotBasisError(
            "assert_raw_spot: price series is NOT on the book's as-traded basis - median relative "
            "error %.6f over %d entries exceeds %.1e. This is the U1-SPLIT defect class: option "
            "strikes are as-traded and `close` is split/dividend-adjusted. Use `raw_close`. "
            "Worst: %s %s series=%.4f book=%.4f" % (med, checked, tol, worst[1], worst[2],
                                                    worst[3], worst[4]))
    return {"checked": checked, "median_rel_err": med,
            "max_rel_err": float(max(errs)) if errs else None, "tol": tol}


# ---------------------------------------------------------------------------------------------
# O19 — the sizing artefact
def weighted_expectancy(rows: Sequence[dict], risk: float = RISK_PER_TRADE) -> dict:
    """Expectancy three ways, per the audit: equal-, contract- and dollar-weighted.

    Contract weight is the whole-contract count the shipped sizer would buy, which is the whole
    point: a $0.50 contract gets twenty and a $5.00 contract gets two.
    """
    pn, ct, dl = [], [], []
    for r in rows:
        p = r.get("pnl_pct")
        prem = r.get("entry_premium")
        if p is None or prem is None or not np.isfinite(float(p)) or float(prem) <= 0:
            continue
        n = contracts_for(float(prem), risk)
        pn.append(float(p))
        ct.append(float(n))
        dl.append(float(n) * float(prem) * 100.0)
    if not pn:
        return {"n": 0}
    pn = np.asarray(pn, float)
    ct = np.asarray(ct, float)
    dl = np.asarray(dl, float)
    out = {"n": int(pn.size), "equal_weighted": float(pn.mean())}
    out["contract_weighted"] = float((pn * ct).sum() / ct.sum()) if ct.sum() > 0 else None
    out["dollar_weighted"] = float((pn * dl).sum() / dl.sum()) if dl.sum() > 0 else None
    out["mean_contracts"] = float(ct.mean())
    out["median_contracts"] = float(np.median(ct))
    return out


def o19_verdict(equal_w, dollar_w, floor_deltas_pp) -> str:
    """ARTEFACT iff equal- and dollar-weighted disagree in SIGN, or a premium floor moves
    expectancy by more than O19_ARTEFACT_PP with its CI excluding zero.

    `floor_deltas_pp` is a sequence of (delta_pp, ci_lo_pp, ci_hi_pp); a None entry is skipped.
    """
    if equal_w is not None and dollar_w is not None:
        if np.isfinite(equal_w) and np.isfinite(dollar_w):
            if (equal_w > 0) != (dollar_w > 0):
                return "ARTEFACT"
    for item in (floor_deltas_pp or ()):
        if not item:
            continue
        d, lo, hi = item
        if d is None or lo is None or hi is None:
            continue
        if abs(float(d)) > O19_ARTEFACT_PP and (lo > 0 or hi < 0):
            return "ARTEFACT"
    return "NOT-AN-ARTEFACT"


# ---------------------------------------------------------------------------------------------
# O11 — drawdown geometry on a marked equity curve
def max_drawdown_frac(equity: Sequence[float]) -> Optional[float]:
    """Peak-to-trough drawdown as a POSITIVE FRACTION of the running peak.

    Fraction of PEAK, not of initial capital: a book that doubles and halves has drawn down 50%,
    and measuring against the starting stake would call that 0%.
    """
    e = np.asarray([x for x in equity if x is not None and np.isfinite(x)], float)
    if e.size == 0:
        return None
    peak = np.maximum.accumulate(e)
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = np.where(peak > 0, (peak - e) / peak, 0.0)
    return float(np.max(dd))


def drawdown_spans(equity: Sequence[float]) -> dict:
    """Longest drawdown duration and time-to-recovery, both in observations."""
    e = np.asarray([x for x in equity if x is not None and np.isfinite(x)], float)
    if e.size == 0:
        return {"longest_duration": None, "time_to_recovery": None, "recovered": None}
    peak = -np.inf
    start = None
    longest = 0
    recov = None
    worst_dd, worst_start = 0.0, None
    for i, x in enumerate(e):
        if x >= peak:
            if start is not None:
                longest = max(longest, i - start)
                if worst_start is not None and start == worst_start and recov is None:
                    recov = i - start
            peak = x
            start = None
        else:
            if start is None:
                start = i
            if peak > 0:
                d = (peak - x) / peak
                if d > worst_dd:
                    worst_dd, worst_start = d, start
    if start is not None:
        longest = max(longest, len(e) - start)
    return {"longest_duration": int(longest),
            "time_to_recovery": (int(recov) if recov is not None else None),
            "recovered": bool(recov is not None)}


def o11_verdict(dd_early, dd_late) -> str:
    """UNSURVIVABLE if either half draws down >= 50% of peak; SURVIVABLE only if BOTH are
    < 25%; otherwise MARGINAL. Both halves required, as registered."""
    ds = [d for d in (dd_early, dd_late) if d is not None and np.isfinite(d)]
    if len(ds) < 2:
        return "MARGINAL"
    if any(d >= DD_UNSURVIVABLE for d in ds):
        return "UNSURVIVABLE"
    if all(d < DD_SURVIVABLE for d in ds):
        return "SURVIVABLE"
    return "MARGINAL"


def long_leg_as_book_trade(row: dict, marks: Sequence[tuple]) -> Optional[dict]:
    """Map a LONG single-leg call into `simulate_book`'s vocabulary.

    **This is the one place a sign error could hide, so it is a named function with its own
    tests rather than three lines inside the runner.** `simulate_book` was written for SHORT
    spreads: it marks unrealised P&L as `(credit_ps - mark)`, which is the P&L of something you
    sold. A long call is the opposite sign.

    The mapping is exact rather than approximate: set `credit_ps = -debit` and negate every
    mark, and the layer's own expression becomes

        (credit_ps - m) = (-debit) - (-mark) = mark - debit

    which is precisely the long position's unrealised P&L. `max_risk_dollars` is the full debit,
    because a long option can lose all of it. Nothing in the shipped layer is modified.
    """
    e = row.get("entry_premium")
    if e is None or not np.isfinite(float(e)) or float(e) <= 0:
        return None
    if row.get("pnl_dollars") is None:
        return None
    debit = float(e)
    exit_date = row.get("exit_date")
    if not exit_date:
        held = int(row.get("held_days") or 0)
        try:
            exit_date = (dt.date.fromisoformat(str(row["alert_ts"]))
                         + dt.timedelta(days=max(held, 1))).isoformat()
        except Exception:
            return None
    return {
        "ok": True,
        "ticker": row["ticker"],
        "alert_ts": str(row["alert_ts"]),
        "exit_date": str(exit_date),
        "pnl_dollars": float(row["pnl_dollars"]),
        "credit_ps": -debit,
        "max_risk_dollars": debit * 100.0,
        "atm_iv": row.get("iv"),
        "marks": [(d, -float(m)) for d, m in marks
                  if m is not None and np.isfinite(float(m))],
    }


# ---------------------------------------------------------------------------------------------
# O22 — capacity, P1's method ported to option depth
def participation(position_notional: float, depth_notional: float) -> Optional[float]:
    if depth_notional is None or not np.isfinite(depth_notional) or depth_notional <= 0:
        return None
    return float(position_notional) / float(depth_notional)


def modelled_cost_bps(part: float, lam: float = O22_LAMBDA_HEADLINE,
                      alpha: float = O22_ALPHA) -> Optional[float]:
    """P1's functional form: cost in bps rises as participation^(alpha-1), scaled by lambda.

    lambda is an ASSUMPTION, not a measurement - P1 said so and its capacity range spanned 16x
    across the lambda band. The same caveat travels with every number here.
    """
    if part is None or not np.isfinite(part) or part < 0:
        return None
    return float(1e4 * lam * (part ** (alpha - 1.0)) * part)


def capacity_aum(depths: Sequence[float], edge_bps: float, position_share: float,
                 lam: float = O22_LAMBDA_HEADLINE, lo: float = 1e4,
                 hi: float = 1e11) -> Optional[float]:
    """The AUM at which median modelled one-way cost crosses the book's own gross edge.

    Bisection on a monotone function; returns None if the edge is never crossed inside the
    bracket, which is reported as such rather than as a huge number.
    """
    d = np.asarray([x for x in depths if x is not None and np.isfinite(x) and x > 0], float)
    if d.size == 0 or edge_bps is None or edge_bps <= 0:
        return None

    def cost_at(aum):
        pos = aum * position_share
        parts = pos / d
        cs = [modelled_cost_bps(p, lam) for p in parts]
        cs = [c for c in cs if c is not None]
        return float(np.median(cs)) if cs else None

    c_lo, c_hi = cost_at(lo), cost_at(hi)
    if c_lo is None or c_hi is None:
        return None
    if c_lo > edge_bps or c_hi < edge_bps:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if cost_at(mid) < edge_bps:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2.0)


# ---------------------------------------------------------------------------------------------
# O25 — sell the wing after the move
def first_crossing(marks: Sequence[tuple], entry_premium: float,
                   threshold: float) -> Optional[int]:
    """Index of the FIRST mark whose return crosses `threshold`. None if never crossed.

    `marks` is [(date, mid), ...] in order. The first crossing is used, not the best one - the
    latter would be a look-ahead that picks the peak.
    """
    if not marks or entry_premium is None or float(entry_premium) <= 0:
        return None
    e = float(entry_premium)
    for i, (_d, mid) in enumerate(marks):
        if mid is None or not np.isfinite(mid):
            continue
        if (float(mid) - e) / e >= float(threshold):
            return i
    return None


def wing_pnl_pct(entry_premium: float, exit_premium: float,
                 wing_credit: float, wing_buyback: float) -> Optional[float]:
    """Return of long call + short wing, as a fraction of the LONG leg's entry premium.

    The short leg is entered at the BID and bought back at the ASK, matching the book's
    aggression of 1.0 - a wing sold at the mid would be a free half-spread, which O10 measured
    is not available.
    """
    if entry_premium is None or float(entry_premium) <= 0:
        return None
    e = float(entry_premium)
    long_leg = float(exit_premium) - e
    short_leg = float(wing_credit) - float(wing_buyback)
    return (long_leg + short_leg) / e


def paired_verdict(diff_vs_close_early, ci_close_early, diff_vs_hold_early, ci_hold_early,
                   diff_vs_close_late, ci_close_late, diff_vs_hold_late, ci_hold_late) -> str:
    """CANDIDATE iff the paired mean beats BOTH comparators with CI95 excluding zero, in BOTH
    halves. Anything else is a NULL (RUN_RULES A6)."""
    cells = ((diff_vs_close_early, ci_close_early), (diff_vs_hold_early, ci_hold_early),
             (diff_vs_close_late, ci_close_late), (diff_vs_hold_late, ci_hold_late))
    for d, ci in cells:
        if d is None or ci is None or len(ci) != 2:
            return "NULL"
        lo, hi = ci
        if lo is None or hi is None or not np.isfinite(lo) or not np.isfinite(hi):
            return "NULL"
        if not (d > 0 and lo > 0):
            return "NULL"
    return "CANDIDATE"
