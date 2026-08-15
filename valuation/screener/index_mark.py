"""
THE DOCUMENTED PRICE MECHANISM for the contract-bound Valquo Index forward track.

This module exists to answer one dated failure. On 2026-08-10 the writer lane tried to
record the day's contract row, could not, and said why (commit `41d7b12`):

    "The mechanism for retrieving daily closing prices to calculate the Index returns is
     NOT DOCUMENTED IN THIS REPOSITORY ... Cannot write today's row without (a) a
     documented price-fetching mechanism, or (b) guessing at a vendor. Per instructions,
     logging the gap rather than inventing data."

That was the correct call, and it names the missing ingredient exactly: not a scheduler
fault, not a crash — a missing documented price mechanism. `PT-WRITER` has been BLOCKED on
it since 2026-08-09. This module is the ingredient. It computes today's contract row from
the service's own machinery and hands it back; it does not decide when to run, and it does
not write. Scheduling and writing stay with the lane that owns the recorder.

WHAT IT RETURNS is exactly the row `valuation/screener/index_track.py` reads back:

    date, day_n, valquo_pct, spy_pct, excess_pp, n_priced

`valquo_pct` and `spy_pct` are CUMULATIVE PERCENT SINCE INCEPTION, not daily returns —
that is the convention the recorded series already uses and the one `index_track._daily_
returns` un-chains. Writing a daily return into those columns would produce a plausible
file that silently re-bases the whole track, so `contract_row` emits the cumulative figure
and `ROW_COLUMNS` below is the single spelling of the header.

NO NEW VENDOR, WHICH WAS HALF THE BLOCKER. Prices come from `screener/prices.py` — Stooq
primary, yfinance fallback — the same module the momentum factor and the liquidity gate
already run on. There is no API key, no licensed row, and nothing here that a fresh deploy
does not already have. The alternative the failure note refused, "guessing at a vendor", is
refused here too, by not having a vendor to guess at.

HOW CLOSELY IT REPRODUCES THE RECORDED ROWS — MEASURED, AND THE TWO LEGS DIFFER. Both rows
already in `valquo_track_history.csv` were re-derived from this mechanism against live
prices on 2026-08-14:

    2026-08-06   spy_pct    recorded 3.6228   re-derived 3.6228   EXACT
    2026-08-06   valquo_pct recorded 0.7760   re-derived 0.7961   +0.0201pp
    2026-07-31   spy_pct    recorded 0.6903   re-derived 0.7200   +0.0297pp

**THE BENCHMARK LEG REPRODUCES EXACTLY, AND THE BOOK LEG DOES NOT.** The exact hit on SPY
is what confirms the CONVENTION — closing prices, cumulative since inception, this vendor —
because a wrong base date or a daily-return convention would miss by percent, not by
nothing. The book leg is 0.0201pp away with all 86 names priced on both sides, so it is
close but **NOT bit-identical, and this module may not be described as the source of the
recorded series.** HYPOTHESIS, NOT DIAGNOSED: dividend/adjustment treatment across 86 names
(the yfinance fallback auto-adjusts) or a different quote vendor for the equity leg. It was
not chased, because the rows were hand-made and nobody recorded how they were priced.

CONSEQUENCE, STATED SO NOBODY DISCOVERS IT LATER: a row written by this mechanism is not
bit-comparable with the two hand-made rows, and a series that switches to it acquires a
~0.02pp seam. Against the contract's own sigma of 3.9847pp per MONTH that is immaterial —
it is roughly half a percent of one month's noise — but it is a real discontinuity and it
is disclosed rather than rounded away.

THE DAY-1 ROW IS NOT A USABLE COMPARISON IN EITHER DIRECTION. Only 78 of 86 names have a
2026-07-31 close in this tape against a recorded `n_priced` of 86, so its book leg compares
two different books. Its BENCHMARK leg is comparable and misses by 0.0297pp in the same
direction. HYPOTHESIS, NOT A FINDING: that row looks marked from an intraday quote rather
than the close — consistent in sign and size, and exactly the failure `refuse_before_close`
below exists to prevent. Not confirmed, not claimed, and reported only because anyone
re-deriving the series will hit the same 0.03pp and should know it is expected.

REFUSING IS A FIRST-CLASS OUTCOME, and it is the behaviour the writer lane already got
right. Every failure path returns `ok: False` with a `reason` a human can act on, and NONE
of them returns a number. A price mechanism that fills a gap with its best guess is worse
than no price mechanism, because the gap is then invisible and the track is quietly wrong.
The refusals are:

  * the session has not closed (see `market_session.session_state`) — marking now would
    write an intraday quote under a closing-price column;
  * the requested date is not a trading day;
  * the book or its inception date is unreadable;
  * the benchmark cannot be priced at BOTH inception and the mark date;
  * fewer than `MIN_COVERAGE` of the book's weight can be priced.

WHAT IT DELIBERATELY DOES NOT DO. It does not write the CSV, it does not decide the
schedule, and it does not touch `data/`. `PT-WRITER` is a Cowork-lane row and stays one;
this repository now documents the mechanism so that lane has something to call. It also
never re-derives the BOOK — the 86 names and their weights are read from the recorded
`valquo_track.json`, because re-scoring the universe on the mark date would silently
substitute today's book for the one the track has been recording since inception, which is
a different series wearing the same name.
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
from typing import Callable, Optional

from . import market_session as _session

#: The recorded file's header, in order. `index_track.load()` reads `date`, `valquo_pct`,
#: `spy_pct`, `excess_pp` and `n_priced` by name; `day_n` is carried because the existing
#: rows carry it. ONE spelling, so a writer cannot invent a column the reader ignores.
ROW_COLUMNS = ("date", "day_n", "valquo_pct", "spy_pct", "excess_pp", "n_priced")

#: Sentinels handed to `csv.DictReader` so `append_row` can TELL a ragged file rather than
#: silently normalising it. By default a surplus cell lands under the key `None` and a short
#: row is padded with `None`, both of which are indistinguishable from an honestly-empty
#: field once the dict exists. These two are distinguishable, which is the whole point.
_RESTKEY = "__surplus_cells__"
_RESTVAL = object()

#: Fraction of the book's WEIGHT (not its name count) that must price before a row is
#: emitted. Weight, because a book is a set of exposures: losing one 2.3% name is not the
#: same event as losing one 0.4% name, and a name-count floor prices those identically.
#: 0.95 is a judgement, stated as one — it is not derived from anything, and it is set high
#: because the recorded rows priced 86 of 86, so anything materially short of the whole book
#: is a data failure rather than a normal day.
MIN_COVERAGE = 0.95

#: Trading days of history to pull. Needs to span inception to today; 400 covers about 19
#: months, and the contract's verdict horizon is 60. A track that outlives this window wants
#: the number raised, and `contract_row` says so in its refusal rather than silently
#: returning a base price it could not find.
HISTORY_DAYS = 400


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _date(s) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _closes(ticker: str, fetch: Callable) -> dict:
    """`{'YYYY-MM-DD': close}` for one ticker, or `{}`.

    The fetcher is injected so the tests can run the whole mechanism offline against fixed
    prices. A price path that can only be exercised against the live internet is a path
    nobody exercises.
    """
    try:
        import pandas as pd
    except Exception:
        return {}
    try:
        df = fetch(ticker, days=HISTORY_DAYS)
    except Exception:
        return {}
    if df is None or getattr(df, "empty", True):
        return {}
    if "Date" not in df.columns or "Close" not in df.columns:
        return {}
    try:
        # `utc=True` because the yfinance fallback returns tz-aware stamps and Stooq
        # returns naive ones; without it a mixed frame raises and the name reads as
        # unpriced, which would be a coverage failure caused purely by a formatting
        # difference between two interchangeable sources.
        d = pd.to_datetime(df["Date"], utc=True, errors="coerce").dt.strftime("%Y-%m-%d")
    except Exception:
        return {}
    out = {}
    for key, close in zip(d.tolist(), df["Close"].tolist()):
        v = _f(close)
        if key and v and v > 0:
            out[key] = v
    return out


def load_book(meta_path: str = None) -> dict:
    """The recorded book: inception date, benchmark and the (ticker, weight) positions.

    Read from the tracker's own meta file rather than rebuilt, deliberately — see the module
    docstring. `index_track.default_paths()` is the one place those paths are spelled.
    """
    from . import index_track
    mp, _ = index_track.default_paths()
    meta_path = meta_path or mp
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f) or {}
    except Exception:
        return {"ok": False, "reason": "the book file " + str(meta_path) + " is missing or unreadable",
                "positions": [], "inception_date": None, "benchmark": None}

    positions = []
    for p in (meta.get("positions") or []):
        t = str(p.get("ticker") or "").strip().upper()
        w = _f(p.get("weight"))
        if t and w and w > 0:
            positions.append({"ticker": t, "weight": w})
    inception = _date(meta.get("inception_date"))
    benchmark = str(meta.get("benchmark") or "SPY").strip().upper()
    if not positions:
        return {"ok": False, "reason": "the book carries no priceable positions",
                "positions": [], "inception_date": inception, "benchmark": benchmark}
    if inception is None:
        return {"ok": False, "reason": "the book carries no readable inception_date",
                "positions": positions, "inception_date": None, "benchmark": benchmark}
    return {"ok": True, "reason": "", "positions": positions,
            "inception_date": inception, "benchmark": benchmark,
            "scan_date": meta.get("scan_date")}


def contract_row(as_of=None, *, meta_path: str = None, fetch: Callable = None,
                 now: _dt.datetime = None, refuse_before_close: bool = True) -> dict:
    """Today's contract row, or a refusal that says why.

    On success:  `{"ok": True, "row": {...ROW_COLUMNS...}, "coverage": .., "unpriced": [..]}`
    On refusal:  `{"ok": False, "reason": "...", "row": None}`  — never a partial number.

    `as_of` defaults to the session date `market_session` reports, which is the day whose
    close has just been recorded. `refuse_before_close=False` is offered for backfilling a
    past date, where the session-close question is about a day that has already ended; it
    does NOT let a caller mark an unclosed *current* session, because the price lookup is by
    date and an unclosed day has no close to find.
    """
    from . import prices as _prices
    fetch = fetch or _prices.get_history_df

    book = load_book(meta_path)
    if not book["ok"]:
        return {"ok": False, "reason": book["reason"], "row": None}

    inception = book["inception_date"]
    state = _session.session_state(now)
    if as_of is None:
        if refuse_before_close and not state.get("ok"):
            return {"ok": False, "reason": state.get("reason") or "the session has not closed",
                    "row": None, "session": state}
        mark = _date(state.get("date"))
    else:
        mark = _date(as_of)
    if mark is None:
        return {"ok": False, "reason": "could not read a mark date", "row": None}
    # NAMING TODAY EXPLICITLY MUST NOT BUY WHAT NOT NAMING IT REFUSES. The close check above
    # only guards the default path, so `--date <today>` would once have walked straight past
    # it — and a vendor that returns a partial bar for a live session would then price the
    # row against an intraday quote under a closing-price column. That is precisely the
    # failure the recorded day-1 row appears to carry (see the reproduction note above), so
    # the guard is on the DATE rather than on how the date was chosen.
    if refuse_before_close and not state.get("ok") and mark.isoformat() == state.get("date"):
        return {"ok": False,
                "reason": state.get("reason") or "the session has not closed",
                "row": None, "session": state}
    if not _session.is_trading_day(mark):
        return {"ok": False, "reason": mark.isoformat() + " is not a trading day", "row": None}
    if mark <= inception:
        return {"ok": False,
                "reason": ("the mark date " + mark.isoformat() + " is on or before inception "
                           + inception.isoformat() + "; inception is day 0 and carries a zero "
                           "return by definition"),
                "row": None}

    base_key, mark_key = inception.isoformat(), mark.isoformat()

    # --- benchmark ---
    bench = book["benchmark"]
    bc = _closes(bench, fetch)
    b_base, b_mark = bc.get(base_key), bc.get(mark_key)
    if not b_base or not b_mark:
        which = "inception " + base_key if not b_base else "mark date " + mark_key
        return {"ok": False,
                "reason": ("the benchmark " + bench + " could not be priced on the " + which
                           + " (a benchmark gap makes the excess unmeasurable, so no row is "
                             "emitted rather than a Valquo-only one)"),
                "row": None}
    spy_pct = (b_mark / b_base - 1.0) * 100.0

    # --- the book ---
    # Renormalised over the names that priced, so an unpriced name is treated as "not
    # measured" rather than silently as "held at a zero return" — the latter would drag the
    # mark toward zero in exactly the weeks a data outage is most likely.
    num, wsum, unpriced = 0.0, 0.0, []
    total_w = sum(p["weight"] for p in book["positions"])
    for p in book["positions"]:
        m = _closes(p["ticker"], fetch)
        base, cur = m.get(base_key), m.get(mark_key)
        if not base or not cur:
            unpriced.append(p["ticker"])
            continue
        num += p["weight"] * (cur / base - 1.0)
        wsum += p["weight"]

    coverage = (wsum / total_w) if total_w else 0.0
    if coverage < MIN_COVERAGE:
        return {"ok": False,
                "reason": ("only " + format(coverage * 100.0, ".2f") + "% of the book's weight "
                           "could be priced on " + mark_key + ", below the "
                           + format(MIN_COVERAGE * 100.0, ".0f") + "% floor; "
                           + str(len(unpriced)) + " names unpriced"),
                "row": None, "coverage": coverage, "unpriced": unpriced}
    valquo_pct = (num / wsum) * 100.0

    row = {
        "date": mark_key,
        "day_n": _session.trading_days_between(inception, mark, inclusive_start=False),
        "valquo_pct": round(valquo_pct, 4),
        "spy_pct": round(spy_pct, 4),
        "excess_pp": round(valquo_pct - spy_pct, 4),
        "n_priced": len(book["positions"]) - len(unpriced),
    }
    return {"ok": True, "reason": "", "row": row, "coverage": coverage, "unpriced": unpriced,
            "inception_date": inception.isoformat(), "benchmark": bench,
            "n_positions": len(book["positions"]), "source": "screener/prices.py (Stooq -> yfinance)"}


def append_row(row: dict, history_path: str = None) -> dict:
    """Append (or replace) one row in the recorded CSV, idempotently.

    Offered so the writer does not have to re-spell the header — a writer that hand-builds
    the CSV is free to emit a column `index_track.load()` does not read, and that failure is
    silent on both sides. Rewriting a date rather than duplicating it matches `index_track.
    load()`, which already keeps the LAST row per date.

    It is a convenience, not a policy: whether and when to write is the recorder lane's.

    APPENDING ONE ROW REWRITES THE WHOLE FILE, so the two hazards below are about every row
    in it, not about the row being added. `track-backup.yml` calls this file *"the one thing
    that can't be re-derived"*, and both were live until `MA4` (2026-08-15):

    1. **It is written through a temp file and `os.replace`, never in place.** `open(path,
       "w")` truncates first, so an interruption between truncate and flush leaves the bound
       series empty or partial. Renaming over the original means a failed write leaves the
       PREVIOUS file intact — which is also why no separate pre-write copy is taken: the
       original *is* the copy until the rename succeeds.
    2. **The header is the UNION of what is on disk with `ROW_COLUMNS`, never a projection
       onto it.** Reading each historical row into a dict and re-writing it under
       `ROW_COLUMNS` alone would delete any column the file had gained — a `vintage`, a
       `source`, an `n_priced_method` — from *every row*, on the first append, silently. The
       docstring above guards the opposite direction; the loss ran this way.

    A column that exists on disk is therefore preserved forever, while a key on the incoming
    `row` that is in neither the file nor `ROW_COLUMNS` is NOT written — widening the
    contract-bound schema should take a deliberate edit here, not a caller's typo — and is
    returned in `ignored_fields` rather than dropped in silence.

    A RAGGED FILE IS REFUSED, NOT NORMALISED. `csv.DictReader` files surplus cells under a
    single `None` key and pads short rows with `None`, so rewriting a file whose rows do not
    match its header would quietly discard or invent cells. Refusing leaves a recording gap,
    which `track_meter.recording_history` can see; normalising loses data that nothing can.
    """
    from . import index_track
    _, hp = index_track.default_paths()
    history_path = history_path or hp
    if not row or not row.get("date"):
        return {"ok": False, "reason": "no row to append", "wrote": False}

    existing, on_disk = [], []
    try:
        with open(history_path, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f, restkey=_RESTKEY, restval=_RESTVAL)
            existing = [r for r in rd]
            on_disk = [c for c in (rd.fieldnames or []) if c]
    except FileNotFoundError:
        existing, on_disk = [], []
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "reason": "could not read " + str(history_path) + ": " + str(e),
                "wrote": False}

    for i, r in enumerate(existing):
        if _RESTKEY in r or any(v is _RESTVAL for v in r.values()):
            return {"ok": False, "wrote": False, "reason":
                    "refusing to rewrite " + str(history_path) + ": data row " + str(i + 2)
                    + " does not match its header, so a rewrite would discard or invent "
                      "cells. Repair the file by hand."}

    fields = list(ROW_COLUMNS) + [c for c in on_disk if c not in ROW_COLUMNS]
    ignored = sorted(k for k in row if k not in fields)

    kept = [r for r in existing if (r.get("date") or "").strip() != row["date"]]
    replaced = len(kept) != len(existing)
    kept.append({k: row.get(k) for k in fields})
    kept.sort(key=lambda r: (r.get("date") or ""))

    d = os.path.dirname(os.path.abspath(history_path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    tmp = history_path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in kept:
                w.writerow({k: r.get(k) for k in fields})
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, history_path)
    except Exception as e:                                   # noqa: BLE001
        try:
            os.remove(tmp)
        except OSError:
            pass
        return {"ok": False, "wrote": False,
                "reason": "could not write " + str(history_path) + ": " + str(e)}
    return {"ok": True, "reason": "", "wrote": True, "replaced": replaced,
            "path": history_path, "rows": len(kept), "columns": fields,
            "ignored_fields": ignored}
