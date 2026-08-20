"""MB3 - the deciding arithmetic for event ownership. ZERO TRIALS.

    python -m scripts.mb3_event_ownership_equity [--json PATH]

THE QUESTION, quoted from `VALQUO_MASTER_AUDIT_4.md` MB3: *"at what account equity does the cap-10
ruin arithmetic permit an earnings-spanning book to end above where it started?"*

**THIS IS NOT A HYPOTHESIS TEST AND CHARGES NOTHING.** It is a computation on banked distributions
with no bar of its own - the `S25` / `X7RECON` / `MB31` class. The audit's own framing: "a
computation on banked distributions with no hypothesis and no bar - zero trials."

THE KILL CONDITION, quoted, and fixed before the run because it is the audit's and not mine:

> "If the required equity exceeds **$250,000**, the answer is final for this operator and the
> family closes permanently, with the effect recorded as real and out of reach. Below it, the
> question becomes a live design and needs its own blind register."

AND THE THIRD OUTCOME, which the instruction requires be available rather than resolved by
judgement: if the equity curve is **non-monotone** in starting capital - i.e. it crosses the
break-even line more than once, so "the required equity" is not a single well-defined number -
the result is recorded **UNRESOLVED**. Ambiguous against a pre-committed threshold is a null
(`RUN_RULES` A6); it is never a judgement call.

NOTHING IS REIMPLEMENTED. The book simulation is the shipped
`options_vrp_portfolio.simulate_book` under the shipped `options_vrp.MAX_CONCURRENT`; the spanning
partition is the shipped `earnings_surface.owns_the_event` fed by the shipped
`bulk.earnings_dates`. A second copy of either would make this a measurement of my own arithmetic
rather than of `O11`'s and `O17C4`'s (audit B7's defect class).

TWO PROPERTIES OF THE SPANNING SET INHERITED FROM `O17C4`, both of which bound the reading:
  * `owns_the_event` returns **None for UNKNOWN** and those rows are DROPPED and COUNTED, never
    folded either way. 29 of 186 names are foreign private issuers with zero earnings dates.
  * The effect is a **MEAN** effect: DTE-matched, median-vs-median is +0.40pp (-51.41% against
    -51.81%). The typical trade is a near-total loss on either side. That is precisely why the
    concurrency cap bites, and it is the reason this arithmetic is worth doing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.studies import portfolio_capacity as PC      # noqa: E402
from valuation.edge import options_vrp_portfolio as VP      # noqa: E402
from valuation.edge import options_vrp as V                 # noqa: E402

# ---- constants, all inherited rather than chosen -------------------------------------------
CONC_CAP = 10                 # O11's binding cell
BAR_USD = 250_000.0           # MB3's own kill condition, quoted above
DATA = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data")
MARKS = os.path.join(DATA, "free_analysis", "O11_MARKS.pkl")
#: The SPLIT-CLEAN book (`U1-SPLIT`, 2026-08-11), which is what `O17C4` and `O11` both read.
#: NOT `state.pkl` (the void 3,042-trade book) and NOT `state_r2_corrected.pkl` (superseded by
#: the split-clean rebuild - 24% of R2's published gap was a corporate-action artifact).
BOOK = os.path.join(DATA, "options_universe", "state_r2_splitclean.pkl")

#: Geometric-ish sweep, wide enough that the answer is bracketed rather than extrapolated, and
#: FIXED BEFORE THE RUN so the grid cannot be chosen around the bar.
#:
#: EXTENDED DOWNWARD AFTER THE FIRST RUN, and the extension is declared rather than quietly
#: made. The first pass used a floor of $25,000 and the book was above its starting equity at
#: EVERY cell, so the answer was not bracketed from below and "required equity <= $25,000" was
#: the most that could honestly be said. The added cells run from $1,000 to $20,000 - i.e.
#: AWAY from the $250,000 bar in the direction that cannot change an ABOVE/BELOW verdict, since
#: every one of them is already an order of magnitude under it. A downward extension here can
#: only make the reported number smaller and the refusal stronger; it cannot manufacture a pass.
EQUITY_GRID = [1_000.0, 2_500.0, 5_000.0, 10_000.0, 15_000.0, 20_000.0,
               25_000.0, 50_000.0, 75_000.0, 100_000.0, 150_000.0, 200_000.0, 250_000.0,
               300_000.0, 400_000.0, 500_000.0, 750_000.0, 1_000_000.0, 1_500_000.0,
               2_000_000.0, 3_000_000.0, 5_000_000.0]


def _log(m):
    print(m, flush=True)


def load_alert_rows():
    with open(BOOK, "rb") as fh:
        b = pickle.load(fh)
    return list(b["rows"])


def spanning_flags(rows):
    """The SHIPPED partition. None is UNKNOWN, dropped and counted."""
    from valuation.edge import bulk
    from valuation.studies.earnings_surface import owns_the_event
    names = sorted({r.get("ticker") for r in rows if r.get("ticker")})
    ev = bulk.prepare_events(os.path.join(DATA, "bulk", "events.csv"))
    earn = {t: sorted(str(x) for x in (bulk.earnings_dates(ev, t) or [])) for t in names}
    span, notspan, unknown = [], [], []
    for r in rows:
        v = owns_the_event(r.get("alert_ts"), r.get("expiry"), earn.get(r.get("ticker")) or [])
        (unknown if v is None else span if v else notspan).append(r)
    return span, notspan, unknown


def build_trades(rows, marks):
    """O11's own construction, verbatim in shape: a trade needs a usable mark path."""
    trades = []
    for r in rows:
        k = (r["ticker"], str(r["alert_ts"]), str(r["expiry"]), float(r["strike"]))
        m = marks.get(k)
        if not m:
            continue
        held = int(r.get("held_days") or 0)
        rr = dict(r)
        rr["exit_date"] = (dt.date.fromisoformat(str(r["alert_ts"]))
                           + dt.timedelta(days=max(held, 1))).isoformat()
        t = PC.long_leg_as_book_trade(rr, m)
        if t:
            trades.append(t)
    return trades


def sweep(trades, grid, cap=CONC_CAP):
    saved = (V.MAX_CONCURRENT, V.INITIAL_CAPITAL)
    rows = []
    try:
        V.MAX_CONCURRENT = int(cap)
        for eq in grid:
            bk = VP.simulate_book(trades, {}, initial_capital=eq, vol_target=False)
            if not bk:
                rows.append({"initial_capital": eq, "simulated": False})
                continue
            fin = bk.get("final_equity")
            rows.append({
                "initial_capital": eq,
                "simulated": True,
                "final_equity": fin,
                "total_return": bk.get("total_return"),
                "n_taken": bk.get("n_taken"),
                "n_generated": bk.get("n_generated"),
                "skipped": bk.get("skipped"),
                "avg_concurrent": bk.get("avg_concurrent"),
                "above_start": (fin is not None and fin > eq),
            })
            _log("  $%-10s taken %-5s/%-5s  final $%-12s  %s"
                 % (f"{int(eq):,}", rows[-1]["n_taken"], rows[-1]["n_generated"],
                    "n/a" if fin is None else f"{fin:,.0f}",
                    "ABOVE start" if rows[-1]["above_start"] else "below start"))
    finally:
        V.MAX_CONCURRENT, V.INITIAL_CAPITAL = saved
    return rows


def resolve(rows, bar=BAR_USD):
    """Find the crossing, and REFUSE to name one if the curve crosses more than once."""
    ok = [r for r in rows if r.get("simulated")]
    flags = [bool(r["above_start"]) for r in ok]
    transitions = [i for i in range(1, len(flags)) if flags[i] != flags[i - 1]]

    if not flags:
        return {"verdict": "UNRESOLVED", "reason": "no cell simulated"}
    if all(flags):
        req = ok[0]["initial_capital"]
        note = ("the book is above its starting equity at EVERY cell on the grid, including the "
                "smallest - so the required equity is at or below the grid floor and the grid "
                "does not bracket it from below")
        return {"verdict": "BELOW_BAR", "required_equity": req, "bracketed": False,
                "reason": note, "n_transitions": 0}
    if not any(flags):
        note = ("the book is below its starting equity at EVERY cell on the grid, up to "
                f"${int(ok[-1]['initial_capital']):,} - so the required equity exceeds the top of "
                "the grid and therefore exceeds the bar")
        return {"verdict": "ABOVE_BAR", "required_equity": None, "bracketed": False,
                "reason": note, "n_transitions": 0}
    if len(transitions) > 1:
        return {"verdict": "UNRESOLVED", "n_transitions": len(transitions),
                "reason": ("the curve crosses break-even more than once, so 'the required "
                           "equity' is not a single well-defined number. Ambiguous against a "
                           "pre-committed threshold is a NULL (RUN_RULES A6), never a "
                           "judgement call."),
                "crossing_cells": [ok[i]["initial_capital"] for i in transitions]}

    i = transitions[0]
    if not flags[i]:
        return {"verdict": "UNRESOLVED", "n_transitions": 1,
                "reason": ("the single crossing runs the WRONG WAY - the book is above its start "
                           "at LOW equity and below it at HIGH equity, which no monotone "
                           "'required equity' reading can express")}
    req = ok[i]["initial_capital"]
    lo = ok[i - 1]["initial_capital"]
    return {"verdict": ("ABOVE_BAR" if req > bar else "BELOW_BAR"),
            "required_equity": req, "bracketed": True,
            "bracket": [lo, req], "n_transitions": 1,
            "reason": (f"break-even is first reached at ${int(req):,}, bracketed between "
                       f"${int(lo):,} (below) and ${int(req):,} (above)")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DATA, "free_analysis", "MB3_EVENT_EQUITY.json"))
    a = ap.parse_args(argv)

    _log("MB3 - event ownership: the deciding arithmetic. ZERO TRIALS.")
    _log(f"  cap {CONC_CAP}, bar ${int(BAR_USD):,} (the audit's own kill condition)")

    rows = load_alert_rows()
    _log(f"  alert book rows: {len(rows)}")
    span, notspan, unknown = spanning_flags(rows)
    _log(f"  spanning {len(span)}   not-spanning {len(notspan)}   "
         f"UNKNOWN dropped {len(unknown)}")

    with open(MARKS, "rb") as fh:
        marks = pickle.load(fh)
    trades = build_trades(span, marks)
    _log(f"  spanning trades with a usable mark path: {len(trades)} of {len(span)}")

    out = {"item": "MB3", "trials": 0, "concurrency_cap": CONC_CAP, "bar_usd": BAR_USD,
           "n_alert_rows": len(rows), "n_spanning": len(span),
           "n_not_spanning": len(notspan), "n_unknown_dropped": len(unknown),
           "n_spanning_marked": len(trades), "equity_grid": EQUITY_GRID}

    if len(trades) < 50:
        out["verdict"] = "UNRESOLVED"
        out["reason"] = (f"only {len(trades)} spanning trades carry a usable mark path; "
                         "simulate_book requires 50 and this is NOT a null - nothing was "
                         "measured")
        _log("  ** " + out["reason"])
    else:
        _log("  sweeping starting equity:")
        cells = sweep(trades, EQUITY_GRID)
        out["cells"] = cells
        out.update(resolve(cells))

        # ------------------------------------------------------------------ THE CONTROL
        # Without it the headline is uninterpretable. `O11` measured the WHOLE alert book
        # ending at $37,059 from $50,000 at this cap; if the spanning half ends above its
        # start, the question is immediately "then where did O11's loss come from?". Running
        # the complement on the identical grid, cap and simulator answers that by measurement
        # instead of leaving it to inference. Still zero trials: no hypothesis, no bar.
        ctrl_trades = build_trades(notspan, marks)
        _log(f"\n  CONTROL - the NOT-spanning complement ({len(ctrl_trades)} marked trades):")
        out["n_not_spanning_marked"] = len(ctrl_trades)
        if len(ctrl_trades) >= 50:
            ctrl = sweep(ctrl_trades, EQUITY_GRID)
            out["control_cells"] = ctrl
            out["control_resolution"] = resolve(ctrl)
            at50 = next((c for c in ctrl if c["initial_capital"] == 50_000.0), None)
            sp50 = next((c for c in cells if c["initial_capital"] == 50_000.0), None)
            out["at_50k"] = {
                "spanning_final": (sp50 or {}).get("final_equity"),
                "not_spanning_final": (at50 or {}).get("final_equity"),
                "o11_whole_book_final_recorded": 37059.0,
                "note": ("O11's recorded whole-book figure is quoted from the record, NOT "
                         "recomputed here - the two books are not required to sum, because "
                         "the UNKNOWN rows are dropped from both partitions."),
            }
        else:
            out["control_cells"] = None
            out["control_resolution"] = {"verdict": "NOT RUN", "reason": "too few marked trades"}

    _log("")
    _log("  VERDICT: " + str(out.get("verdict")))
    _log("  " + str(out.get("reason", "")))
    if out.get("verdict") == "ABOVE_BAR":
        _log("  -> the audit's kill condition FIRES: the family closes permanently, with the "
             "effect recorded as REAL and OUT OF REACH for this operator.")
    elif out.get("verdict") == "BELOW_BAR":
        _log("  -> below the bar: this becomes a LIVE DESIGN NEED requiring its own blind "
             "register. It is NOT a licence to trade - O11 governs.")

    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    _log(f"\n  wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
