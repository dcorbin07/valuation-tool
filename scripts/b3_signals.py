# -*- coding: utf-8 -*-
"""`STAGE1-BATCH3` — the eight arms' signal constructions, and nothing else.

**NO OUTCOME IS COMPUTED HERE.** This module builds `{date: {ticker: value}}` for each arm from
point-in-time fundamentals. It never reads a forward return, never sorts a decile and never
compares anything to a bar — so it can be exercised and reviewed before the register's kill pass
runs, which is `O10`'s ordering rule in module form.

**EVERYTHING POINT-IN-TIME GOES THROUGH THE SHIPPED HELPERS** (`B7`): `_pit_row` for the last
filed row at or before a date, and `fundamental_panel._ttm` for trailing-four-quarter sums —
the latter matters because it **collapses restatements by `reportperiod`**, a defect a hand-rolled
four-row window cannot see (`D10-a`: 3.15% of (ticker, reportperiod) groups carry more than one
datekey, so a naive window can sum Q1, Q2, Q2', Q3).

**THE `capex` SIGN IS THE REGISTER'S AMENDMENT 0.2 AND IT LIVES IN ONE FUNCTION.** Sharadar
stores `capex` as a negative outflow on 95.40% of NONZERO rows; 11.29% of rows are exactly zero
and 4.60% of nonzero rows are genuinely POSITIVE (disposals exceeding purchases, with the signed
identity `capex == fcf - ncfo` holding on 99.95% of them). So `abs()` would score a divestiture
as heavy investment, and `capex_outflow()` floors at zero instead — with the three states
counted so the choice is visible in the artifact rather than buried in a helper.
"""
from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.tiered_pool import _num, _pit_row                              # noqa: E402

MIN_NAMES_PER_DATE = 20

#: counts for the three capex states, filled as `capex_outflow` is called. Reported, never
#: silently folded into one number.
CAPEX_STATES = {"outflow": 0, "exactly_zero": 0, "net_inflow": 0, "absent": 0}


def capex_outflow(row):
    """The capital-expenditure OUTFLOW as a non-negative magnitude, or None.

    Register amendment 0.2: `max(0, -capex)`. **NOT `abs(capex)`** — a positive `capex` row is a
    period in which disposals exceeded purchases, and `abs()` would score it as a heavy
    investor. Floored at zero so a net disposal reads as "no capital expenditure", which is the
    honest reading of the quantity the literature means.
    """
    c = _num(row.get("capex"))
    if c is None:
        CAPEX_STATES["absent"] += 1
        return None
    if c == 0.0:
        CAPEX_STATES["exactly_zero"] += 1
        return 0.0
    if c > 0:
        CAPEX_STATES["net_inflow"] += 1
        return 0.0
    CAPEX_STATES["outflow"] += 1
    return -c


def _ttm_sum(rows, as_of, keys, n=4):
    """`fundamental_panel._ttm`, CALLED. Returns a dict of summed keys or None."""
    from valuation.edge.fundamental_panel import _ttm
    return _ttm(rows, as_of, keys, n=n)


def _rows_before(rows, as_of):
    """Every filed row at or before `as_of`, in order. The caller walks back from the end."""
    out = []
    for r in rows:
        dk = r.get("datekey") or r.get("date")
        if dk and dk <= as_of:
            out.append(r)
        elif dk and dk > as_of:
            break
    return out


def _yoy_row(rows, as_of, back=4):
    """The row `back` quarters before the point-in-time row, for a year-over-year change.

    Returns `(now, then)` or `(None, None)`. **Both rows must exist** — a delta against a
    missing base is not a small delta, it is no observation, and defaulting it to zero is how a
    missing input becomes a neutral score (`V6-B`'s `_f()` defect).
    """
    pre = _rows_before(rows, as_of)
    if len(pre) < back + 1:
        return (None, None)
    return (pre[-1], pre[-1 - back])


def _scaled_delta(now_v, then_v):
    """A change scaled to the mean of its own two-year base — Lev-Thiagarajan's form.

    The denominator is the MEAN of the two levels rather than the base alone, because a base
    near zero makes a ratio explode and the sign of the explosion depends on which side is
    nearly zero. `None` where the base is not usable, never a capped number.
    """
    if now_v is None or then_v is None:
        return None
    base = (abs(now_v) + abs(then_v)) / 2.0
    if base <= 0:
        return None
    return (now_v - then_v) / base


# =============================================================================================
# C7 — OPERATING LEVERAGE (Novy-Marx 2011). The simplest arm, and the template for the rest.
# =============================================================================================
def c7_operating_leverage(frame, hist):
    """`(cor + sgna) / assets`, point-in-time, TTM on the two flows."""
    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        per = {}
        for t in frame.loc[frame["date"] == d, "ticker"].astype(str):
            rows = hist.get(t) or []
            row = _pit_row(rows, dd)
            if not row:
                continue
            a = _num(row.get("assets"))
            if a is None or a <= 0:
                continue
            # the two cost flows are TTM: a single ARQ quarter would make the ratio depend on
            # which fiscal quarter the name happens to sit in, which is `_ttm`'s own motivation
            s = _ttm_sum(rows, dd, ("cor", "sgna"))
            if not s:
                continue
            cor, sgna = s.get("cor"), s.get("sgna")
            if cor is None and sgna is None:
                continue
            per[t] = ((cor or 0.0) + (sgna or 0.0)) / a
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    return sig


# =============================================================================================
# C3 — R&D-TO-MARKET (Chan-Lakonishok-Sougiannis 2001).
# =============================================================================================
def c3_rnd_to_market(frame, hist, zero_sink=None):
    """`rnd / marketcap`, TTM on `rnd`.

    **A TRUE ZERO IS SCORED AS ZERO AND AN ABSENT `rnd` IS EXCLUDED**, with the three counts kept
    apart — `A1` established that reporting and the register inherits it. Most firms legitimately
    have no R&D, so treating absent as zero would score 'we do not know' as 'they spend nothing'.
    """
    counts = {"scored_nonzero": 0, "scored_zero": 0, "excluded_absent": 0}
    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        g = frame[frame["date"] == d]
        per = {}
        for t, mc in zip(g["ticker"].astype(str), g["market_cap"]):
            m = _num(mc)
            if m is None or m <= 0:
                continue
            rows = hist.get(t) or []
            s = _ttm_sum(rows, dd, ("rnd",))
            if not s or s.get("rnd") is None:
                counts["excluded_absent"] += 1
                continue
            v = float(s["rnd"])
            counts["scored_zero" if v == 0.0 else "scored_nonzero"] += 1
            per[t] = v / m
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    if zero_sink is not None:
        zero_sink.update(counts)
    return sig


# =============================================================================================
# C6 — CASH CONVERSION CYCLE.
# =============================================================================================
def c6_cash_conversion_cycle(frame, hist):
    """`-(DSO + DIO - DPO)`, signed so a SHORT cycle is high (good).

    `DSO = 365 * receivables / revenue`, `DIO = 365 * inventory / cor`,
    `DPO = 365 * payables / cor`. Revenue and `cor` are TTM; the balance-sheet items are
    point-in-time levels, which is the standard mixed convention.
    """
    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        per = {}
        for t in frame.loc[frame["date"] == d, "ticker"].astype(str):
            rows = hist.get(t) or []
            row = _pit_row(rows, dd)
            if not row:
                continue
            s = _ttm_sum(rows, dd, ("revenue", "cor"))
            if not s:
                continue
            rev, cor = s.get("revenue"), s.get("cor")
            rec = _num(row.get("receivables"))
            inv = _num(row.get("inventory"))
            pay = _num(row.get("payables"))
            if None in (rev, cor, rec, inv, pay) or rev <= 0 or cor <= 0:
                continue
            dso = 365.0 * rec / rev
            dio = 365.0 * inv / cor
            dpo = 365.0 * pay / cor
            per[t] = -(dso + dio - dpo)
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    return sig


# =============================================================================================
# C5 — EARNINGS STABILITY / PERSISTENCE, 20 quarters.
# =============================================================================================
PERSISTENCE_QUARTERS = 20          # the register's own, fixed before any outcome


def c5_earnings_stability(frame, hist, window=PERSISTENCE_QUARTERS, cov_sink=None):
    """AR(1) on the name's own ROA series plus the negative of its sd, equally weighted.

    Both legs come from ONE window so a name cannot contribute to one and not the other —
    otherwise the two legs would be averaged over different populations, which is `MB8`'s rule
    about borrowing a statistic across constructions in miniature.
    """
    counts = {"scored": 0, "short_history": 0}
    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        per = {}
        for t in frame.loc[frame["date"] == d, "ticker"].astype(str):
            rows = _rows_before(hist.get(t) or [], dd)
            if len(rows) < window:
                counts["short_history"] += 1
                continue
            roa = []
            for r in rows[-window:]:
                ni, a = _num(r.get("netinc")), _num(r.get("assets"))
                if ni is None or a is None or a <= 0:
                    roa = []
                    break
                roa.append(ni / a)
            if len(roa) < window:
                counts["short_history"] += 1
                continue
            n = len(roa)
            mu = sum(roa) / n
            var = sum((x - mu) ** 2 for x in roa) / n
            if var <= 0:
                continue
            # AR(1) as the lag-1 autocorrelation of the own-ROA series
            num = sum((roa[i] - mu) * (roa[i - 1] - mu) for i in range(1, n))
            ar1 = num / (var * n)
            per[t] = (ar1, -math.sqrt(var))
            counts["scored"] += 1
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    if cov_sink is not None:
        cov_sink.update(counts)
    return sig
