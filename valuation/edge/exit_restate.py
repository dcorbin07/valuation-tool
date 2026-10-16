# -*- coding: utf-8 -*-
"""RE-PRICE THE "LEFT COVERAGE" EXITS THAT WERE BOOKED AT THEIR OWN ENTRY PRICE. [item 65 part 4]

Six closes in the hot-stock paper record -- CNA, ABCL, BEAM, HIVE, IDYA, NUVB -- were bought on
2026-08-10/11 and closed *"left coverage"* on 2026-09-01/02 **at their entry price**. The cause is
recorded in `positions.update_positions`: the live scan covers the ~800 most liquid names and its
membership churns at the edge, so a name can enter the top 10 and never be scanned again, and the
`price_fn` re-pricing that fixes it did not exist until 2026-09-30.

`positions.summary` already detects them and **excludes them from the realised average** -- *"an
exit that was never re-priced is UNKNOWN, not zero"* -- so the published figure is honest and six
of twenty-nine closes simply carry no return. This module supplies the missing prices.

WHAT MAKES IT A RESTATEMENT RATHER THAN AN EDIT
-----------------------------------------------
The old value stays, beside the new one, with the date and the source
(`store.restate_exit_price`). A restatement that keeps no record of what it replaced is
indistinguishable from the figure having always been that -- `scream_log`'s convention, applied
to a number rather than to a message.

THE PRICE IS OUR OWN VENDOR'S CLOSE ON THE EXIT DATE
----------------------------------------------------
Not the last close, not today's: **the close on the day the position was recorded as closed**, so
the restated return is the return the book actually experienced. The brief supplies the manager's
own check (CNA -4.5%, ABCL +20.8%, BEAM +6.4%, HIVE +1.5%, IDYA +8.7%, NUVB +0.6%) and says not to
copy it. So it is kept as a **CONTROL** rather than used as a source: two independent vendors
agreeing on six names is evidence, and copying would have manufactured the agreement.

WHY A VENDOR MISS IS A REFUSAL AND NEVER A FALLBACK
---------------------------------------------------
If no close exists on the exit date the name is **left unrestated** and reported. The tempting
fallbacks are all wrong in the same direction: the nearest available close is a different day's
price under this day's label, and the last close is today's price on a position that closed six
weeks ago. An unpriced exit is already handled honestly by being excluded; replacing it with a
wrong price would turn an acknowledged gap into a silent error.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

#: The hot-stock paper account's source key in the position store.
SOURCE = "hotstocks"

#: The manager's independent check, entry day to exit day. **A CONTROL, NEVER A SOURCE.**
#: Quoted here so a reader can compare our vendor's answer against a figure computed from a
#: different one -- which is the only thing it is good for. The brief's own instruction.
MANAGER_CHECK = {"CNA": -0.045, "ABCL": 0.208, "BEAM": 0.064,
                 "HIVE": 0.015, "IDYA": 0.087, "NUVB": 0.006}

#: How far either side of the exit date a close may come from. **ZERO.** See the module
#: docstring: a neighbouring day's close under this day's label is a wrong number, and the
#: honest alternative (leaving it unrestated) already exists and is already reported.
EXIT_DATE_TOLERANCE_DAYS = 0


def unpriced_exits(rows) -> list:
    """The closes whose exit price equals their entry price, and which are not yet restated.

    The predicate is `positions.summary`'s own `_unpriced_exit`, deliberately -- a second
    definition of "which rows are broken" would drift from the one that excludes them from the
    average, and then the set being fixed and the set being excluded would differ.
    """
    out = []
    for p in (rows or []):
        if not (p.get("exit_reason") or "").startswith("left coverage"):
            continue
        if p.get("exit_price") is None or p.get("entry_price") is None:
            continue
        if p.get("exit_price_original") is not None:
            continue                       # already restated; the original is kept
        if float(p["exit_price"]) == float(p["entry_price"]):
            out.append(p)
    return out


def close_on(ticker: str, on_date: str, history=None) -> dict:
    """Our own vendor's close for `ticker` on exactly `on_date`.

    `history` is injectable so this is testable without a network; by default it is the shipped
    `prices.get_history_df`, which is the same route the Index record is marked from -- so the
    restated price comes from the vendor this project already trusts for a close rather than
    from a second one chosen for this job.
    """
    if history is None:
        from ..screener.prices import get_history_df as history      # noqa: N813
    want = str(on_date)[:10]
    try:
        d = _dt.date.fromisoformat(want)
    except ValueError:
        return {"ok": False, "reason": "%r is not a date" % (on_date,)}
    # Enough history to reach the exit date from today, plus slack for weekends and holidays.
    days = max(30, (_dt.date.today() - d).days + 20)
    try:
        df = history(ticker, days=days)
    except Exception as e:                                           # noqa: BLE001
        return {"ok": False, "reason": "the vendor raised %s" % type(e).__name__}
    if df is None or getattr(df, "empty", True):
        return {"ok": False, "reason": "the vendor returned no history"}
    cols = {str(c).lower(): c for c in df.columns}
    dcol = cols.get("date")
    ccol = cols.get("close") or cols.get("adj close") or cols.get("raw_close")
    if dcol is None or ccol is None:
        return {"ok": False, "reason": "the vendor's frame has no date/close columns"}
    hit = None
    for _, r in df.iterrows():
        if str(r[dcol])[:10] == want:
            hit = r
            break
    if hit is None:
        # **NO FALLBACK.** A neighbouring close under this date's label is a wrong number, and
        # leaving the exit unrestated is already handled honestly.
        return {"ok": False, "reason": "no close on %s (tolerance %d days)"
                                       % (want, EXIT_DATE_TOLERANCE_DAYS)}
    try:
        px = float(hit[ccol])
    except (TypeError, ValueError):
        return {"ok": False, "reason": "the close on %s is not a number" % want}
    if px <= 0:
        return {"ok": False, "reason": "the close on %s is %r" % (want, px)}
    return {"ok": True, "price": px, "date": want}


def plan(rows, *, history=None) -> dict:
    """What a restatement WOULD do, computing every price and writing nothing.

    The door reads this first, because a restatement of a published figure is not something to
    discover the shape of while making it.
    """
    out = {"n_candidates": 0, "rows": [], "n_priceable": 0, "n_unpriceable": 0,
           "control": dict(MANAGER_CHECK), "control_note": (
               "the manager's independent figures, entry day to exit day. A CONTROL rather "
               "than a source: our own vendor supplies every price below, so agreement is "
               "evidence from two vendors instead of a copy.")}
    for p in unpriced_exits(rows):
        out["n_candidates"] += 1
        got = close_on(p["ticker"], p.get("exit_date"), history=history)
        entry = float(p["entry_price"]) if p.get("entry_price") else None
        row = {"ticker": p["ticker"], "entry_date": p.get("entry_date"), "entry_price": entry,
               "exit_date": p.get("exit_date"), "exit_price_booked": p.get("exit_price"),
               "ok": bool(got.get("ok")), "reason": got.get("reason") or ""}
        if got.get("ok"):
            row["exit_price_restated"] = got["price"]
            row["ret_gross"] = (got["price"] / entry - 1.0) if entry else None
            ctrl = MANAGER_CHECK.get(p["ticker"].upper())
            if ctrl is not None and row["ret_gross"] is not None:
                row["control_ret"] = ctrl
                row["control_gap_pp"] = round((row["ret_gross"] - ctrl) * 100.0, 3)
            out["n_priceable"] += 1
        else:
            out["n_unpriceable"] += 1
        out["rows"].append(row)
    out["rows"].sort(key=lambda r: r["ticker"])
    return out


def apply_plan(store, planned: dict, *, source: str = SOURCE,
               on_date: Optional[str] = None) -> dict:
    """Write the priceable restatements. Returns what it did, per name.

    **ONLY the rows the plan could price.** An unpriceable exit stays unrestated and stays
    excluded from the realised average, which is the honest state it was already in.
    """
    stamp = on_date or _dt.date.today().isoformat()
    out = {"restated": [], "skipped": [], "on_date": stamp}
    for r in (planned.get("rows") or []):
        if not r.get("ok"):
            out["skipped"].append({"ticker": r["ticker"], "why": r.get("reason")})
            continue
        res = store.restate_exit_price(
            source, r["ticker"], r["entry_date"], r["exit_price_restated"], stamp,
            "our own price vendor's close on %s (item 65 part 4)" % r["exit_date"])
        if res.get("ok"):
            out["restated"].append({"ticker": r["ticker"], "was": res["was"],
                                    "now": res["now"], "exit_date": r["exit_date"]})
        else:
            out["skipped"].append({"ticker": r["ticker"], "why": res.get("reason")})
    return out
