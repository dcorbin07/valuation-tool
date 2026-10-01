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
        # AN ALL-NULL POINT IS REFUSED, and the caller that made this necessary is instructive.
        #
        # A first pass through the 19 missed sessions wrote 19 points with every value `null`,
        # because it read `p.get("row")` while `reconstruct` returns its points ALREADY FLATTENED.
        # The console showed the right numbers throughout -- the printer used
        # `p.get("row") or p`, so its lenient fallback masked the shape mismatch while the writer,
        # which had no fallback, emitted empties. The stored file then looked like a complete
        # reconstruction of 19 days and would have drawn 19 invisible points.
        #
        # A store whose whole purpose is "this is NOT the record" must not be able to hold a day
        # it did not compute. `reconstruct` already returns an unpriceable day as a REFUSAL; this
        # closes the other door in.
        vals = [p.get(k) for k in ("valquo_pct", "spy_pct", "excess_pp")]
        if all(v is None for v in vals):
            raise ValueError(
                "refusing to store a reconstructed point with no values for %s -- a day that "
                "could not be computed belongs in `refused`, not in `points`" % p.get("date"))
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


def reconstruct(dates, *, meta_path: str = None, history_path: str = None,
                fetch=None, now=None) -> dict:
    """Compute the missed days with `index_mark.contract_row`, the WRITER's own function.

    **NOT A SECOND IMPLEMENTATION (B7), AND HERE THAT IS THE ENTIRE ARGUMENT FOR TRUSTING THE
    OUTPUT.** `contract_row` already resolves the book in force through the rebalance events,
    prices on the same routing (yfinance first since 2026-09-30, Stooq as the fallback), on the
    same adjusted basis, refuses a non-trading day, and refuses rather than returning a partial
    number. A reconstruction computed any other way would be a different series wearing the
    record's units, and the two would disagree for reasons nobody could attribute.

    `refuse_before_close=False` is the one thing that differs from a same-day write, and it is
    what the parameter exists for: the session-close question is about a day that has already
    ended. It does NOT let an unclosed current session through -- the price lookup is by date and
    an unclosed day has no close to find.

    **A DAY THAT CANNOT BE PRICED IS RETURNED AS A REFUSAL, NEVER AS A GAP-FILLED GUESS.** The
    whole point of this store is that it is not the record; the moment it starts inventing a
    number for a day the vendor could not price, it is worse than the hole it replaces.
    """
    from . import index_mark
    out, refused = [], []
    for d in dates:
        try:
            r = index_mark.contract_row(as_of=d, meta_path=meta_path,
                                        history_path=history_path, fetch=fetch, now=now,
                                        refuse_before_close=False)
        except Exception as e:                                          # noqa: BLE001
            refused.append({"date": str(d), "reason": "%s: %s" % (type(e).__name__, e)})
            continue
        if not r.get("ok") or not r.get("row"):
            refused.append({"date": str(d), "reason": r.get("reason") or "refused"})
            continue
        row = r["row"]
        out.append({"date": str(row.get("date") or d),
                    "valquo_pct": row.get("valquo_pct"),
                    "spy_pct": row.get("spy_pct"),
                    "excess_pp": row.get("excess_pp"),
                    "spmo_pct": row.get("spmo_pct"),
                    "n_priced": row.get("n_priced"),
                    "coverage": r.get("coverage")})
    return {"points": out, "refused": refused,
            "n_requested": len(list(dates)), "n_computed": len(out)}


def validate_against_record(series, *, meta_path: str = None, history_path: str = None,
                            fetch=None, limit: int = None) -> dict:
    """Reconstruct days the record ALREADY HOLDS and report the disagreement, leg by leg.

    **THE ONLY THING THAT LICENSES DRAWING A RECONSTRUCTED POINT.** If the reconstruction cannot
    reproduce a day the record already contains, it has no business drawing days the record does
    not -- so this is not a diagnostic, it is the precondition, and it ships as a function rather
    than as a one-off script precisely so the next run re-measures instead of inheriting a number.

    The two legs are reported SEPARATELY and never summed, because they behave differently and a
    single combined figure would hide that: the benchmark leg reproduces exactly (one symbol,
    closing prices, cumulative since inception), while the book leg cannot, for a reason that is
    a property of the vendor rather than of this code -- a name the record could price on the day
    may be unpriceable TODAY, and it is then missing from the reconstruction of EVERY day,
    including the days it was live. That is vendor-side survivorship, it moves the book average,
    and `n_priced` is returned per day so a reader can see it happening.

    Returns per-day deltas plus `book_max_abs` / `bench_max_abs` / `book_median_abs`. It states no
    bar: what counts as an acceptable seam is a judgement for whoever quotes these points, and
    inventing a threshold here would be the uncalibrated-bar error this project has paid for
    repeatedly.
    """
    from . import index_mark
    rows = {}
    for r in (series or []):
        d = str(r.get("date"))[:10]
        if d:
            rows[d] = r
    out, bl, bn = [], [], []
    for d in sorted(rows)[:limit] if limit else sorted(rows):
        rec = rows[d]
        got = index_mark.contract_row(as_of=d, meta_path=meta_path, history_path=history_path,
                                      fetch=fetch, refuse_before_close=False)
        if not got.get("ok"):
            out.append({"date": d, "refused": got.get("reason") or "refused"})
            continue
        row = got.get("row") or {}
        # BOTH SPELLINGS, AND AN ABSENT FIELD IS A REFUSAL RATHER THAN A ZERO.
        #
        # The writer's row says `valquo_pct` / `spy_pct`; the chart payload `index_track.summarize`
        # serves says `valquo` / `spy`. A first cut read only the writer's names, and `_num`
        # returned 0.0 for the missing key -- so every delta came back EQUAL TO THE
        # RECONSTRUCTED VALUE ITSELF and the validator reported a 4pp disagreement on all 24 days
        # that was entirely an artefact of a key name. A validator that fabricates the thing it is
        # comparing against is worse than no validator, and this one fabricated a FAILURE, which
        # is the direction that gets believed.
        #
        # Treating absent as zero is the same lenient-reader defect as the all-null write above,
        # one layer up: a plausible substitute for a value that is not there.
        rb, kb = _pick(rec, ("valquo_pct", "valquo"))
        rn, kn = _pick(rec, ("spy_pct", "spy"))
        if kb is None or kn is None:
            out.append({"date": d, "refused": ("the record row carries no %s field"
                                               % ("book" if kb is None else "benchmark"))})
            continue
        db = _num(row.get("valquo_pct")) - _num(rb)
        dn = _num(row.get("spy_pct")) - _num(rn)
        bl.append(abs(db))
        bn.append(abs(dn))
        out.append({"date": d, "d_book_pp": round(db, 6), "d_bench_pp": round(dn, 6),
                    "record_fields": [kb, kn],
                    "n_priced_reconstructed": row.get("n_priced"),
                    "n_priced_recorded": rec.get("n_priced")})
    res = {"days": out, "n_compared": len(bl), "n_refused": len(out) - len(bl)}
    if bl:
        res["book_max_abs"] = round(max(bl), 6)
        res["book_median_abs"] = round(sorted(bl)[len(bl) // 2], 6)
        res["bench_max_abs"] = round(max(bn), 6)
        res["bench_exact_days"] = sum(1 for x in bn if x == 0.0)
    return res


def _pick(row, names):
    """The first of `names` PRESENT on the row, with the name that was found.

    Returns `(None, None)` when none is present, so a caller can refuse. It deliberately does not
    fall back to a default: the whole hazard here is a missing field quietly becoming a number.
    """
    for n in names:
        if n in (row or {}):
            return (row or {})[n], n
    return None, None


def _num(v) -> float:
    """Parse a value that IS present. Never used to supply one that is not -- see `_pick`."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


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
