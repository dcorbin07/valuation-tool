"""(D) THE RECORDERS — start the clocks the history-starved books need, TODAY.

Four declared books gate on a series nothing in this repository writes:

    F-5   an own-history percentile of 60-DTE ATM implied vol   (needs ~20 observations)
    F-11  a name's FIRST appearance in the dip-reject population this quarter
    F-19  a market-wide alert count against the trailing TWO YEARS
    F-20  two years of realised vol on the paper index book's own daily series

**A BOOK THAT NEEDS TWO YEARS OF HISTORY SHOULD BE BANKING DAY 1 TODAY, NOT ON THE DAY
SOMEBODY REMEMBERS.** No amount of coding produces a series retroactively -- this is the one
class of blocker where waiting is strictly more expensive than acting, and where the cost of
acting is a few rows a day.

**F-20's RECORDER ALREADY EXISTS AND IS NOT REBUILT HERE.** Its series is the bound paper
index track, written by `PT-WRITER`'s door; it stands at four rows and needs about five
hundred. Building a second writer for it would be a second copy of a fact (`MA5`) and would
put two series under one name -- exactly the split `PT-SPLIT` had to unpick. **F-20 is
TIME-starved, not recorder-starved, and its recorder is somebody else's open row.**

THE SHAPE, and why it is one row per day. Each series appends **ONE row per date**, with the
per-name payload carried as a JSON cell. That keeps the shipped `append_only.append`
primitive usable UNMODIFIED -- idempotent on the date, refusing any backward write -- instead
of a per-name key that would re-read the whole file once per name and grow quadratically. It
also makes a day's observation atomic: a cycle either recorded that day or it did not, and
there is no half-written cross-section to reason about.

WHAT THESE ARE NOT. **No outcome statistic is stored** -- percentiles, realised vol and
"first appearance" are all computed at READ time from the raw series, which is `S3-I1`'s own
rule that a record stream carries observations and never conclusions. And **nothing here
touches a licensed export**: every input is live (the chain snapshot, the screener, the scan).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

from . import append_only as AO

#: series -> (columns, description). A series absent here cannot be written by accident.
SERIES = {
    "iv60_atm": (("date", "n_names", "payload"),
                 "60-DTE ATM implied vol per optionable name, from the live chain (F-5)"),
    "dip_rejects": (("date", "n_names", "payload"),
                    "the dip-detector REJECT population for the day (F-11)"),
    "alert_count": (("date", "n_alerts", "payload"),
                    "market-wide alert count for the day (F-19)"),
}

BACKFILL_HINT = (" A missed day is a GAP and stays one: these series are evidence about what "
                 "was observable on a date, and a value computed later from today's data is "
                 "not that. Record the gap, never the guess.")


def history_dir(root: str = None) -> str:
    base = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "fleet", "history")


def series_path(name: str, root: str = None) -> str:
    return os.path.join(history_dir(root), str(name) + ".csv")


def record(name: str, date: str, payload, *, count=None, root: str = None) -> dict:
    """Append ONE day to `name`. Idempotent per date; a backward write is REFUSED.

    Idempotent because a cycle can legitimately run twice in a day (a retry, a manual
    dispatch) and the second run must not double-record. Backward-refusing because a series
    whose past can be rewritten is not evidence.
    """
    if name not in SERIES:
        return {"ok": False, "wrote": False,
                "reason": "unknown series %r; SERIES names the closed set" % name}
    cols = SERIES[name][0]
    os.makedirs(history_dir(root), exist_ok=True)
    n = len(payload) if count is None and hasattr(payload, "__len__") else count
    row = {"date": str(date)[:10],
           cols[1]: int(n or 0),
           "payload": json.dumps(payload, sort_keys=True, separators=(",", ":"))}
    return AO.append(row, series_path(name, root), key="date", columns=cols,
                     append_only=True, backfill_hint=BACKFILL_HINT)


def read(name: str, root: str = None) -> dict:
    """The whole series, oldest first, with its payloads decoded.

    An ABSENT series and an EMPTY one are reported apart (`O21-D2`'s `C5`): "no recorder has
    ever run" and "the recorder ran and observed nothing" need different fixes.
    """
    path = series_path(name, root)
    rows, cols, err = AO.read_rows(path)
    if err:
        return {"ok": False, "absent": not os.path.exists(path), "reason": err,
                "rows": [], "n": 0}
    if not os.path.exists(path):
        return {"ok": True, "absent": True, "vacuous": True, "rows": [], "n": 0,
                "reason": "no %s series yet; it begins on the first cycle that records one"
                          % name}
    out = []
    for r in rows:
        try:
            payload = json.loads(r.get("payload") or "null")
        except ValueError:
            payload = None
        out.append({"date": (r.get("date") or "")[:10], "payload": payload, "raw": r})
    return {"ok": True, "absent": False, "vacuous": not out, "rows": out, "n": len(out),
            "columns": cols, "reason": ""}


def history_for(name: str, ticker: str, root: str = None) -> list:
    """`[(date, value)]` for one name, oldest first, skipping days it was not observed.

    A day on which the name was absent is NOT carried forward and is NOT zero-filled. An
    expanding percentile over a forward-filled series would count one observation many times
    and report a burn-in that had not been served -- `I-2`'s finding, that an observation
    COUNT and an elapsed SPAN come apart, in its most damaging form.
    """
    t = str(ticker).upper()
    out = []
    for r in read(name, root)["rows"]:
        p = r["payload"]
        if isinstance(p, dict) and t in p:
            out.append((r["date"], p[t]))
        elif isinstance(p, list) and t in {str(x).upper() for x in p}:
            out.append((r["date"], True))
    return out


def coverage(root: str = None) -> dict:
    """What every series holds, for a cycle to report without opening them."""
    out = {}
    for name in sorted(SERIES):
        r = read(name, root)
        if r.get("absent"):
            out[name] = {"present": False, "n_days": 0, "reason": r.get("reason", "")}
            continue
        dates = [x["date"] for x in r["rows"]]
        out[name] = {"present": True, "n_days": len(dates),
                     "first": dates[0] if dates else None,
                     "last": dates[-1] if dates else None,
                     "vacuous": not dates,
                     "description": SERIES[name][1]}
    return out


# ---------------------------------------------------------------------------------------
# THE RECORDERS. Every source is injectable so a test drives them without a network.
# ---------------------------------------------------------------------------------------
def record_alert_count(date: str = None, *, store=None, root: str = None) -> dict:
    """F-19: one market-wide alert count per day."""
    date = date or _dt.date.today().isoformat()
    if store is None:
        from ..screener.store import Store
        store = Store()
    rows = store.load_intraday() or []
    return record("alert_count", date, {"n": len(rows)}, count=len(rows), root=root)


def record_dip_rejects(date: str = None, *, rejects=None, root: str = None) -> dict:
    """F-11: the day's dip-REJECT population, so a FIRST appearance becomes datable.

    `rejects` is the caller's -- this module does not run the dip screen, because that screen
    drives the valuation engine per name and belongs to whatever process already pays for it.
    Passing `None` records an EMPTY day, which is a real observation and is why the count is
    stored beside the payload.
    """
    date = date or _dt.date.today().isoformat()
    names = sorted({str(t).upper() for t in (rejects or [])})
    return record("dip_rejects", date, names, count=len(names), root=root)


def record_iv60(date: str = None, *, quotes=None, root: str = None) -> dict:
    """F-5: 60-DTE ATM implied vol per name, from the live chain.

    `quotes` is `{ticker: iv}` supplied by the caller for the same reason as above: fetching a
    chain per name is the expensive part and the process that already holds a provider should
    own it. **A name with no solvable IV is OMITTED, never recorded as zero** -- a zero IV
    would enter an expanding percentile as the cheapest observation the name ever had, which
    is precisely backwards.
    """
    date = date or _dt.date.today().isoformat()
    clean = {}
    for t, v in (quotes or {}).items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == f and f > 0:
            clean[str(t).upper()] = round(f, 6)
    return record("iv60_atm", date, clean, count=len(clean), root=root)


def record_all(date: str = None, *, store=None, rejects=None, quotes=None,
               root: str = None) -> dict:
    """Every recorder, once. Returns per-series outcomes; never raises on one failing.

    A recorder that raised would take the whole cycle down with it, and the cycle's other work
    -- the gates, the refusals, the fills -- is independent of whether a series accrued.
    """
    date = date or _dt.date.today().isoformat()
    out = {"date": date, "series": {}}
    for name, fn, kw in (("alert_count", record_alert_count, {"store": store}),
                         ("dip_rejects", record_dip_rejects, {"rejects": rejects}),
                         ("iv60_atm", record_iv60, {"quotes": quotes})):
        try:
            r = fn(date, root=root, **kw)
            out["series"][name] = {"wrote": bool(r.get("wrote")),
                                   "already_present": bool(r.get("already_present")),
                                   "ok": bool(r.get("ok")),
                                   "reason": r.get("reason", "")}
        except Exception as e:                                   # noqa: BLE001
            out["series"][name] = {"wrote": False, "ok": False, "reason": str(e)}
    out["recorded"] = sum(1 for v in out["series"].values() if v["wrote"])
    return out
