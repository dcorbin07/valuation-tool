"""Reconstructed track days, for the CHART ONLY — never for the record.

WHY THIS IS THE ONLY SHAPE THIS FEATURE MAY TAKE. `PAPER_TRACK_CONTRACT.md` §3:

    **VOIDS THE WHOLE RUN**: any back-fill of prices or positions after the fact

Not the affected window — **the whole run**. So a reconstructed day may never enter
`valquo_track_history.csv`, `valquo_track.json`, the meter, the operational gate, any verdict, or
any count of recorded sessions. It lives in its own store, carries the date it was computed, and
reaches exactly one consumer: the chart, where it is drawn as visibly distinct and labelled.

**THE DISTINCTION THAT MAKES IT LEGITIMATE.** A back-fill answers *"what does the record say"*
with a number nobody recorded at the time. This answers a different question — *"what would the
book in force have done on the days the writer missed"* — and answers it in a place that is not
the record. The bound series still says **24 of 43 days recorded**; nothing here changes that,
and a test pins that every gate and meter input is **byte-identical** with this on and off.

**WHY IT IS WORTH HAVING AT ALL.** 19 of 43 trading days since inception are missing (11 since
vintage 4 opened), so the published chart has visible holes that read as the book having stopped.
A labelled reconstruction shows continuity without claiming it was recorded — and being able to
see the shape of the missing stretch is how anyone notices whether the writer's outage coincided
with something interesting.

**THE ARITHMETIC IS THE WRITER'S, NOT A SECOND IMPLEMENTATION (B7).** Same price routing, same
adjusted basis, same `index_mark` primitives, same book-in-force resolution through the rebalance
events. A reconstruction computed a different way would be a second definition of the series and
the two would disagree for reasons nobody could attribute.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from typing import Optional

_LOG = logging.getLogger(__name__)

#: A SEPARATE FILE, next to the bound one but never it. The name says what it holds so nobody
#: mistakes it for the record while reading a directory listing.
DEFAULT_PATH = os.path.join("data", "valquo_track_reconstructed.json")

SCHEMA = "track_reconstructed/1"

#: The label every consumer must render. Fixed here rather than in a template, because the one
#: thing that must not drift is the word that distinguishes these points from recorded ones.
POINT_LABEL = "reconstructed"

NOTE = ("Reconstructed from closing prices and the book in force on each day, for days the "
        "automated writer missed. NOT part of the recorded track: excluded from the recorded-day "
        "count, the evidence meter, the operational gate and every verdict, because the "
        "contract's section 3 treats a back-fill of the record as voiding the whole run.")


def load(path: str = None) -> dict:
    path = path or DEFAULT_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh) or {}
    except (OSError, ValueError):
        return {"schema": SCHEMA, "points": []}
    pts = [p for p in (d.get("points") or []) if isinstance(p, dict) and p.get("date")]
    return {"schema": d.get("schema") or SCHEMA,
            "points": sorted(pts, key=lambda p: str(p["date"]))}


def save(points, path: str = None, computed_at: str = None) -> dict:
    """Write the reconstruction. EVERY POINT CARRIES THE DATE IT WAS COMPUTED.

    Not the date it describes -- that is `date` -- but when this run produced it. A reconstructed
    number is a function of whatever the price vendor said on the day it was asked, so a reader
    comparing two versions of this file needs to know which run each point came from. The bound
    record never needs this because it is written once, on the day, and never recomputed.
    """
    path = path or DEFAULT_PATH
    at = computed_at or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for p in points:
        q = dict(p)
        q["computed_at"] = q.get("computed_at") or at
        q["kind"] = POINT_LABEL
        out.append(q)
    out.sort(key=lambda p: str(p.get("date")))
    body = {"schema": SCHEMA, "note": NOTE, "computed_at": at, "points": out}
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)
    os.replace(tmp, path)
    return {"ok": True, "path": path, "n": len(out), "computed_at": at}


def missing_dates(series, inception: str, through: str = None) -> list:
    """Trading days between inception and `through` that the RECORD does not contain.

    Reads the recorded series and nothing else, so it cannot disagree with the gap the meter
    reports about which days are missing -- it is the same subtraction.
    """
    from . import market_session as _session
    have = {str(r.get("date"))[:10] for r in (series or [])}
    try:
        start = _dt.date.fromisoformat(str(inception)[:10])
    except (TypeError, ValueError):
        return []
    end = (_dt.date.fromisoformat(str(through)[:10]) if through
           else _dt.date.today())
    out, d = [], start
    while d <= end:
        iso = d.isoformat()
        if _session.is_trading_day(d) and iso not in have and iso != start.isoformat():
            out.append(iso)
        d += _dt.timedelta(days=1)
    return out


def chart_points(path: str = None) -> list:
    """The reconstruction as the chart wants it: labelled, sorted, and nothing else.

    Deliberately NOT merged with the recorded series here. A single merged array is exactly how
    a reconstructed point ends up counted as a recorded one three refactors later -- the consumer
    receives two arrays and has to decide, visibly, how to draw each.
    """
    return [{"date": p.get("date"), "valquo_pct": p.get("valquo_pct"),
             "spy_pct": p.get("spy_pct"), "excess_pp": p.get("excess_pp"),
             "spmo_pct": p.get("spmo_pct"),
             "kind": POINT_LABEL, "computed_at": p.get("computed_at")}
            for p in load(path)["points"]]


def payload(path: str = None) -> dict:
    """What `/api/index-track` carries. `recorded_days` is deliberately ABSENT.

    Anything that looks like a count of days belongs to the record. This block reports how many
    points it reconstructed under its own name, so a reader adding the two together has to do it
    on purpose rather than by reading a single field.
    """
    pts = chart_points(path)
    return {"label": POINT_LABEL, "note": NOTE, "n_reconstructed": len(pts),
            "points": pts,
            "excluded_from": ["recorded_days", "evidence_meter", "operational_gate", "verdict"]}
