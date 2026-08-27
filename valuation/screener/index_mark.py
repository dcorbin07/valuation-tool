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

**DIAGNOSED 2026-08-20, AND IT IS THE FIRST OF THOSE TWO CANDIDATES, EXACTLY.** Re-priced on
all 86 names against the same vendor and the same dates, changing nothing but the adjustment
flag:

    auto_adjust=True    valquo_pct 0.7961   spy_pct 3.6228
    auto_adjust=False   valquo_pct 0.7760   spy_pct 3.6228
    recorded row        valquo_pct 0.7760   spy_pct 3.6228

**The adjustment flag moves the book leg by +0.0201pp and the benchmark leg by +0.0000pp, and
+0.0201pp is the whole seam.** 86 of 86 priced under both settings, zero empty fetches. So the
recorded row was priced on an **UNADJUSTED** basis and this mechanism re-derives on an
**ADJUSTED** one, because `yfinance` defaults `auto_adjust=True`.

**AND THE EXACT BENCHMARK HIT IS WHAT MADE THIS HARD TO SEE.** SPY reads 3.6228 under BOTH
settings, so the leg that "confirmed the convention" is precisely the leg that CANNOT
distinguish the two conventions — it agreed for a reason unrelated to the question. A control
that passes identically under both arms of the thing you are testing is not evidence about it.

**THE SECOND CANDIDATE IS ELIMINATED FOR THIS MACHINE.** "A different quote vendor for the
equity leg" requires two vendors, and measured the same day, **Stooq serves 0 of 10 probed
tickers** (HTTP 404 on the default user-agent, a JavaScript bot-challenge page on a browser
one), so every figure on this path comes from yfinance and there is no vendor mixing to blame.
`screener/prices.py` now LABELS every frame with the vendor that served it, so this question is
answerable from the payload instead of by re-derivation — see `contract_row`'s `vendors` block.

**NOTHING IS CHANGED HERE ABOUT HOW THE BOOK IS PRICED.** Switching the mechanism to an
unadjusted basis would make it reproduce the two hand-made rows exactly, and it is a
CONSTRUCTION CHANGE to a bound record — Don's call under the contract, not this lane's. The
seam is now diagnosed rather than merely disclosed; it is still ~0.02pp against a monthly sigma
of 3.9847pp, and it is still a real discontinuity.

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
import io
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


#: The natural JSON type of each recorded column. A row that has been through a CSV is all
#: strings, and handing that back beside a computed row -- which is `float` and `int` -- makes
#: one payload key change type depending on which outcome the caller got. Measured on the live
#: endpoint before this existed: the 201 body carried `valquo_pct: 4.0` and the 200 body
#: carried `"4.0"`, for the same recorded day.
_ROW_TYPES = {"date": str, "day_n": int, "valquo_pct": float, "spy_pct": float,
              "excess_pp": float, "n_priced": int,
              # PT-SPMO's sibling series. Additive and inert on the bound row, whose header
              # never carries these: `typed_row` is keyed by COLUMN NAME, so a column the bound
              # file does not have cannot change what the bound row types to. They are
              # registered here rather than in the sibling module for the reason this file
              # gives for everything else -- one spelling, so a second table cannot drift.
              "spmo_pct": float, "valquo_src": str}


def typed_row(row: dict) -> dict:
    """A row read back from CSV, with the recorded columns in their natural JSON types.

    A CELL THAT WILL NOT PARSE IS KEPT VERBATIM, NOT NULLED. The point of returning the row on
    disk is to report what is actually recorded; replacing an unreadable cell with `None`
    would hide a corrupt record behind a well-typed payload, which is the same failure as
    normalising a ragged file. A caller seeing a string where it expected a number is seeing
    something true about the file.

    Columns the file has gained beyond `ROW_COLUMNS` are passed through untouched — this
    module does not know what they mean and must not guess.
    """
    out = {}
    for k, v in (row or {}).items():
        want = _ROW_TYPES.get(k)
        if want is None or want is str or v is None or isinstance(v, (int, float)):
            out[k] = v
            continue
        f = _f(v)
        if f is None:
            out[k] = v                       # unreadable: report it as it is
        elif want is int and float(f).is_integer():
            out[k] = int(f)
        elif want is int:
            out[k] = v                       # "5.5" in an integer column is not a 5
        else:
            out[k] = f
    return out


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


def _closes(ticker: str, fetch: Callable, seen: Optional[dict] = None) -> dict:
    """`{'YYYY-MM-DD': close}` for one ticker, or `{}`.

    The fetcher is injected so the tests can run the whole mechanism offline against fixed
    prices. A price path that can only be exercised against the live internet is a path
    nobody exercises.

    `seen`, when supplied, accumulates `{ticker: vendor}` from the label `prices.get_history_df`
    stamps on the frame. It is read OFF THE FRAME rather than from a module-global precisely
    because `fetch` is injectable — a global would be blind to whatever the caller passed, and
    an injected fetcher that carries no label is recorded as `None`, meaning "cannot tell",
    never as the primary.
    """
    try:
        import pandas as pd
    except Exception:
        return {}
    try:
        df = fetch(ticker, days=HISTORY_DAYS)
    except Exception:
        if seen is not None:
            seen[ticker] = "fetch_raised"
        return {}
    if seen is not None:
        try:
            seen[ticker] = (df.attrs.get("valquo_src") if df is not None else None)
        except Exception:                                               # noqa: BLE001
            seen[ticker] = None
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

    `as_of` defaults to the LAST CLOSED SESSION — the most recent day whose close is in —
    rather than to "today". `refuse_before_close=False` is offered for backfilling a past
    date, where the session-close question is about a day that has already ended; it does NOT
    let a caller mark an unclosed *current* session, because the price lookup is by date and
    an unclosed day has no close to find.

    **THE DEFAULT USED TO BE TODAY, AND THAT LOST ROWS. Measured on the service 2026-08-27.**
    The cron is scheduled for the evening ET, well after the close. GitHub's scheduler delayed
    it past midnight; it ran at **00:58 ET**, asked to mark the new calendar day, and was
    refused with a 422 that was correct on its own terms — that day had not closed. The guard
    was right and **the target was wrong**: the run should have marked the session that ended
    the previous afternoon, which it had been scheduled to mark all along. A job that slips
    past midnight could then only ever refuse, and the bound track quietly lost a row.

    Asking "what is the last session that closed?" instead of "has today closed?" fixes the
    target without touching a single rule. The two questions differ only between midnight and
    the settle cutoff, which is exactly the window a delayed evening job lands in.

    **NOTHING ELSE MOVES, and the intraday guard is strictly unweakened.**
    `last_closed_session` cannot name an unclosed day by construction, and the explicit-date
    guard below still refuses `--date <today>` while today is open — that guard is on the
    DATE rather than on how the date was chosen, which is what makes it survive this change.
    """
    from . import prices as _prices
    fetch = fetch or _prices.get_history_df

    book = load_book(meta_path)
    if not book["ok"]:
        return {"ok": False, "reason": book["reason"], "row": None}

    inception = book["inception_date"]
    state = _session.session_state(now)
    if as_of is None:
        # THE LAST CLOSED SESSION, not today. See the docstring: a delayed run must still
        # record the session it was scheduled for, and one that has slipped past midnight ET
        # is being asked about a day that cannot have closed.
        mark = _session.last_closed_session(now)
        if mark is None:
            return {"ok": False,
                    "reason": "no closed trading session found in the last fortnight",
                    "row": None, "session": state}
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
    vendors: dict = {}
    bc = _closes(bench, fetch, vendors)
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
        m = _closes(p["ticker"], fetch, vendors)
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
            "n_positions": len(book["positions"]),
            "source": "screener/prices.py (Stooq primary, yfinance fallback)",
            "vendors": _vendor_census(vendors, bench)}


def _vendor_census(seen: dict, benchmark: str) -> dict:
    """WHICH vendor actually served, per leg. Not the route -- the route is a constant.

    The benchmark leg is broken out because it is the one `index_mark`'s own reproduction note
    found EXACT (SPY 3.6228 recorded against 3.6228 re-derived) while the book leg missed by
    +0.0201pp. If those two legs are ever served by different vendors, that is a candidate
    explanation for the seam and this block is where it becomes visible instead of being
    hypothesised again.

    `None` counts as `unlabelled` and is reported as its own bucket -- it means the fetcher did
    not say, which a reader must not resolve to the primary.
    """
    def bucket(v):
        return v if v else "unlabelled"

    by = {}
    for t, v in seen.items():
        if t == benchmark:
            continue
        by[bucket(v)] = by.get(bucket(v), 0) + 1
    return {
        "benchmark_leg": bucket(seen.get(benchmark)),
        "book_leg_by_vendor": by,
        "book_leg_single_vendor": (len(by) <= 1),
        "legs_agree": (bucket(seen.get(benchmark)) in by) if by else None,
        "note": ("A vendor label of 'unlabelled' means the fetcher did not record one -- it "
                 "does NOT mean the primary served. yfinance's Close is AUTO-ADJUSTED and is a "
                 "different quantity from an as-traded close."),
    }

def _canonical_csv(rows: list, fields: list) -> bytes:
    """The rows serialised exactly as `append_row` writes them.

    ONE SERIALISER IS WHAT MAKES THE BYTE-PREFIX RULE CHECKABLE. `seed` compares the bytes on
    disk against the bytes this produces, and `append_row` writes through the same
    `csv.DictWriter` with the same `newline=""`, so "the previous bytes are still an exact
    prefix" is a property both functions can actually hold rather than a claim about one of
    them. It also makes the rule immune to the CALLER's line endings -- an upload sent with
    bare LF and one sent with CRLF canonicalise identically -- so a refusal means a recorded
    value changed, which is the thing worth refusing over.
    """
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in fields})
    return buf.getvalue().encode("utf-8")


def _parse_history(text: str, what: str, raw: bytes = None) -> dict:
    """Rows + header + raw bytes of a recorded CSV, or a reason it cannot be used.

    Shares `append_row`'s ragged-file rule and its sentinels: a surplus cell or a short row is
    REFUSED, never normalised, because normalising invents or discards cells and the file looks
    perfectly well-formed afterwards.
    """
    rd = csv.DictReader(io.StringIO(text, newline=""), restkey=_RESTKEY, restval=_RESTVAL)
    try:
        rows = [r for r in rd]
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "reason": "could not parse " + what + ": " + str(e)}
    fields = [c for c in (rd.fieldnames or []) if c]
    for i, r in enumerate(rows):
        if _RESTKEY in r or any(v is _RESTVAL for v in r.values()):
            return {"ok": False, "reason":
                    what + " is ragged: data row " + str(i + 2) + " does not match its "
                    "header, so reading it would discard or invent cells. Repair it by hand."}
    return {"ok": True, "rows": rows, "fields": fields,
            "raw": raw if raw is not None else text.encode("utf-8"), "exists": True}


def _read_history(path: str) -> dict:
    """`_parse_history` of what is on disk. A missing file is a normal state, not an error."""
    try:
        raw = open(path, "rb").read()
    except FileNotFoundError:
        return {"ok": True, "rows": [], "fields": [], "raw": b"", "exists": False}
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "reason": "could not read " + str(path) + ": " + str(e)}
    return _parse_history(raw.decode("utf-8-sig", errors="replace"), str(path), raw=raw)


def _write_atomic(path: str, payload: bytes):
    """Write bytes through a temp file and `os.replace`. Returns a reason on failure, else None.

    `open(path, "w")` truncates before it writes, so an interruption leaves the target empty or
    partial -- and one of these two targets is the file `track-backup.yml` calls *"the one thing
    that can't be re-derived"*. Renaming over the original means a failed write leaves the
    PREVIOUS file intact, which is also why no separate pre-write copy is taken: the original
    *is* the copy until the rename succeeds. Same construction as `append_row`, deliberately.
    """
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:                               # noqa: BLE001
            return "could not create " + d + ": " + str(e)
    tmp = path + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception as e:                                   # noqa: BLE001
        try:
            os.remove(tmp)
        except OSError:
            pass
        return "could not write " + str(path) + ": " + str(e)
    return None


def seed(book: dict, history_text: str = None, *, meta_path: str = None,
         history_path: str = None) -> dict:
    """Install the bound book and its recorded history on a service that has neither.

    THE PROBLEM THIS SOLVES, MEASURED RATHER THAN ASSUMED. On 2026-08-18 the PT-WRITER Action
    reached `POST /admin/track-row?append=1` on the live service, authenticated, and was
    refused with *"the book file /app/data/valquo_track.json is missing or unreadable"* --
    which is `load_book` working exactly as written. `data/` is gitignored, so the book has
    never shipped with any deploy; it exists only on Don's machine. The write door was never
    the blocker. THE SERVICE HAS NOTHING TO MARK.

    AFTER A SUCCESSFUL SEED THE SERVICE COPY IS THE RECORD. The local files become a stale
    backup the moment the service writes its first row, and nothing here syncs them back. That
    is a deliberate choice of ONE recorder over two: this project has already published two
    different "Valquo Index vs SPY" numbers from two books -- see `index_track`'s own comment
    on the 2026-08-05 recap -- and the cure for that is a single authority, not better
    reconciliation between several.

    THREE RULES, ENFORCED HERE RATHER THAN IN A CALLER, so every door obeys one implementation:

    1. **THE BOOK MUST BE THE INDEX.** Validated through `valquo_index.conformance` -- the same
       check `PT-SPLIT` built and `paper_track.seed_book` gates on -- so a truncated scan cannot
       be installed under the contract's name. A refusal carries `why_not` verbatim.

    2. **THE HISTORY MAY EXTEND WHAT IS ON DISK AND MAY NEVER REWRITE IT.** If the service
       already holds rows, the upload's first N records must match them cell for cell AND the
       bytes on disk must be an exact prefix of the canonicalised upload. Both, and they are
       reported separately on purpose: the record check is the substantive rule, and when it
       passes while the byte check fails the reason names the encoding difference instead of
       reading as a mystery refusal. A shorter upload is a truncation and is refused.

    3. **A BOOK MAY NOT BE SEEDED WITHOUT A HISTORY TO STAND ON.** If the service holds no rows
       and none are supplied, this refuses -- because `append_row` would then create a fresh
       series whose first row is TODAY, every earlier recorded day would be absent from the copy
       this seed is about to make the record, and NOTHING WOULD RAISE. `day_n` is computed from
       the inception date, so the new first row would carry a plausible day number, which is
       precisely what would make the loss invisible.

    THE HEADER MUST BE THE ONE `append_row` WOULD COMPUTE -- `ROW_COLUMNS` in order, then any
    columns the file has gained. Not a tidiness rule: `append_row(append_only=True)` REFUSES a
    header it would have to widen, so seeding a differently-shaped header installs a series the
    unattended writer can never append to. The end-to-end sequence is the deliverable here, not
    the seed on its own.

    Both files are written through `_write_atomic`, and THE HISTORY IS WRITTEN FIRST. The two
    orderings are not symmetric: history-then-book leaves, on a failed book write, a service
    that refuses at `load_book` -- exactly today's state, no harm done. Book-then-history would
    leave a service holding a book and no series, which is the one state rule 3 exists to
    prevent.
    """
    from . import index_track
    from ..edge import valquo_index as _vi

    mp, hp = index_track.default_paths()
    meta_path = meta_path or mp
    history_path = history_path or hp

    out = {"ok": False, "stage": "book", "reason": "", "book_wrote": False,
           "history_wrote": False, "meta_path": meta_path, "history_path": history_path}

    if not isinstance(book, dict) or not book:
        out["reason"] = "no book supplied"
        return out

    positions = []
    for pos in (book.get("positions") or []):
        t = str(pos.get("ticker") or "").strip().upper()
        w = _f(pos.get("weight"))
        if t and w and w > 0:
            positions.append({"ticker": t, "weight": w})
    if not positions:
        out["reason"] = "the book carries no priceable positions"
        return out
    if _date(book.get("inception_date")) is None:
        out["reason"] = "the book carries no readable inception_date"
        return out

    # THE CAP IS DERIVED, AND THE DERIVATION IS THE HONEST PART. `build_index` records the cap
    # it APPLIED as `effective_max_weight`; the tracker's meta file does not carry that field
    # -- measured on the real book, it holds benchmark, inception_date, positions and scan_date
    # and nothing else -- so the observed maximum weight stands in for it. That is sound because
    # a cap is an upper bound: an observed max at or under 8% cannot have been produced by a cap
    # that failed to bind at 8%. The one case where the two diverge is a book of 13 or fewer
    # names whose score weights happen to peak below the relaxed cap, and that book misses the
    # 50-name floor by a wide margin, so `conforms` is unmoved. A recorded value is PREFERRED
    # when the file gains one, so this degrades to reading the truth rather than inferring it.
    cap = _f(book.get("effective_max_weight"))
    cap_derived = cap is None
    if cap is None:
        cap = max(p["weight"] for p in positions)
    conf = _vi.conformance(len(positions), cap)
    conf["effective_max_weight_derived_from_positions"] = cap_derived
    out["conformance"] = conf
    if not conf.get("conforms"):
        out["stage"] = "conformance"
        out["reason"] = ("this book is not the contract-bound Valquo Index and will not be "
                         "installed under its name: " + "; ".join(conf.get("why_not") or [])
                         + ". PAPER_TRACK_CONTRACT.md binds ONE object.")
        return out

    disk = _read_history(history_path)
    if not disk.get("ok"):
        out["stage"] = "history"
        out["reason"] = disk["reason"]
        return out
    out["history_rows_before"] = len(disk["rows"])

    if history_text is None:
        if not disk["rows"]:
            out["stage"] = "history"
            out["reason"] = ("refusing to seed a book with no recorded history: the service "
                             "holds no rows and none were supplied, so the first append would "
                             "start a NEW series at today's date and every earlier recorded "
                             "day would be silently absent from the copy this seed makes the "
                             "record. Supply the history CSV.")
            return out
        out["history_rows_after"] = len(disk["rows"])
        out["history_rows_added"] = 0
        out["prefix_verified"] = None      # no upload, so nothing was compared
    else:
        up = _parse_history(str(history_text).lstrip("\ufeff"), "the uploaded history")
        if not up.get("ok"):
            out["stage"] = "history"
            out["reason"] = up["reason"]
            return out
        rows, fields = up["rows"], up["fields"]
        if not rows:
            out["stage"] = "history"
            out["reason"] = "the uploaded history carries no data rows"
            return out

        want = list(ROW_COLUMNS) + [c for c in fields if c not in ROW_COLUMNS]
        if fields != want:
            out["stage"] = "history"
            out["reason"] = ("the uploaded history's header is " + ",".join(fields)
                             + " and append_row would compute " + ",".join(want)
                             + ". Seeding a header the unattended writer would have to widen "
                               "installs a series it can never append to, because append_only "
                               "REFUSES a schema change.")
            return out

        dates = [(r.get("date") or "").strip() for r in rows]
        if any(not d for d in dates):
            out["stage"] = "history"
            out["reason"] = "the uploaded history has a row with no date"
            return out
        if len(set(dates)) != len(dates):
            out["stage"] = "history"
            out["reason"] = ("the uploaded history repeats a date. index_track.load keeps the "
                             "LAST row per date, so a duplicate silently decides which of two "
                             "readings of one day is the record.")
            return out
        if dates != sorted(dates):
            out["stage"] = "history"
            out["reason"] = ("the uploaded history is not in date order, and the byte prefix "
                             "is defined on the order the file is written in")
            return out

        n = len(disk["rows"])
        if n:
            if disk["fields"] != fields:
                out["stage"] = "history"
                out["would_rewrite"] = True
                out["reason"] = ("the uploaded history's header (" + ",".join(fields)
                                 + ") differs from the one on disk (" + ",".join(disk["fields"])
                                 + "); an upload may EXTEND the recorded series, never reshape "
                                   "it")
                return out
            if len(rows) < n:
                out["stage"] = "history"
                out["would_rewrite"] = True
                out["reason"] = ("the uploaded history has " + str(len(rows)) + " rows against "
                                 + str(n) + " on disk. An upload may extend the recorded "
                                 "series, never truncate it.")
                return out
            for i in range(n):
                a, b = disk["rows"][i], rows[i]
                for k in fields:
                    if (a.get(k) or "") != (b.get(k) or ""):
                        out["stage"] = "history"
                        out["would_rewrite"] = True
                        out["reason"] = ("the upload rewrites a recorded day: row "
                                         + str(i + 2) + " (" + str(a.get("date"))
                                         + ") column " + k + " is " + repr(a.get(k))
                                         + " on disk and " + repr(b.get(k)) + " in the upload. "
                                         "This door may EXTEND the series and may never "
                                         "rewrite it.")
                        return out

        canonical = _canonical_csv(rows, fields)
        if n and not canonical.startswith(disk["raw"]):
            out["stage"] = "history"
            out["would_rewrite"] = True
            out["reason"] = ("every recorded value matches and the bytes on disk are still not "
                             "an exact prefix of the canonical upload -- so the file on disk is "
                             "not in this writer's form (line endings, quoting, or a missing "
                             "trailing newline). Refusing rather than rewriting it, because "
                             "rewriting every line is precisely what the append-only guarantee "
                             "forbids. Repair the file on the service by hand.")
            return out
        out["prefix_verified"] = True if n else None
        out["history_rows_after"] = len(rows)
        out["history_rows_added"] = len(rows) - n

        if canonical != disk["raw"]:
            w = _write_atomic(history_path, canonical)
            if w:
                out["stage"] = "history"
                out["reason"] = w
                return out
            out["history_wrote"] = True

    meta = dict(book)
    meta["positions"] = positions
    payload = json.dumps(meta, indent=2, sort_keys=True, default=str).encode("utf-8")
    try:
        unchanged = open(meta_path, "rb").read() == payload
    except Exception:                                        # noqa: BLE001
        unchanged = False
    if not unchanged:
        w = _write_atomic(meta_path, payload)
        if w:
            out["reason"] = w
            return out
        out["book_wrote"] = True
    out["changed"] = bool(out["book_wrote"] or out["history_wrote"])
    out["ok"] = True
    out["stage"] = ""
    out["n_positions"] = len(positions)
    return out


_BACKFILL_HINT = (" A gap stays a logged gap; filling one is a deliberate act under "
                  "PAPER_TRACK_CONTRACT.md section 3 and lives on "
                  "scripts.track_row --date.")


def append_row(row: dict, history_path: str = None, *, append_only: bool = False,
               columns: tuple = None) -> dict:
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

    `append_only=True` IS THE UNATTENDED WRITER'S MODE, and it is strictly narrower than the
    default. The contract's rules are enforced here rather than in a caller, so that every
    door obeys one implementation instead of several that can drift:

      * **A duplicate date is a NO-OP, not a rewrite.** It returns `wrote: False`,
        `already_present: True` and the row ALREADY ON DISK -- never the freshly computed one.
        Those can differ: a vendor revises, a fallback answers where the primary did not, and
        a retry an hour later can compute a different close for a day already recorded.
        Returning the recomputed row would report a number the file does not contain.
      * **A date at or before the last recorded one is REFUSED.** Filling a gap is a
        deliberate human act under the contract's section 3 same-week clause and stays on the
        CLI's `--date`; an unattended writer that can reach backwards can rewrite history on a
        retry, and a five-year evidence record cannot offer that.
      * **A schema change is REFUSED** rather than performed, because widening the header
        rewrites every line and so cannot preserve the prefix below.

    `columns` IS HOW THE SPMO SIBLING SERIES REUSES THIS RULE SET RATHER THAN COPYING IT.
    It defaults to `ROW_COLUMNS`, so every existing caller is bit-identical and the
    contract-bound file cannot be written under any other schema by accident. `PT-SPMO`
    records a SECOND, unbound series (`data/valquo_vs_spmo.csv`) that needs the same three
    refusals, the same idempotency and the same byte-prefix property against a different
    header -- and a second implementation of "append-only" is exactly the B7 split this
    module keeps warning about. The alternative considered and rejected was adding an SPMO
    column to the bound file: that widens the contract-bound header, rewrites every line, and
    so cannot preserve the prefix `track-row.yml` verifies. The sibling is a different FILE
    for that reason, not for tidiness.

    THE GUARANTEE IS BYTE-LEVEL, BECAUSE THE ACTION'S OWN CHECK IS. After an `append_only`
    write the file's previous bytes are still an exact prefix of the new file.
    `.github/workflows/track-row.yml` verifies precisely that -- `cmp` on `head -n N` -- and
    fails the job otherwise, so a guarantee stated in weaker terms than the check would be
    untestable against it. The rewrite path is shared with the default mode deliberately: a
    second write implementation for the strict case is the B7 split this module already warns
    about, and the three refusals above are exactly what make the shared path's output
    prefix-identical rather than merely value-identical.
    THE IMPLEMENTATION MOVED TO `valuation.edge.append_only` AND THIS FUNCTION DELEGATES.
    `S3-I1`'s fleet books need these exact rules on a key that is not `date` -- a book records
    many orders per day, and every rule above is about the key. Copying them would be the B7
    split the paragraph above warns about, so the rules are keyed on a parameter now and both
    callers share one implementation. Every refusal message, the check ORDER, the header union
    and the byte prefix are unchanged, and `scripts/i1_append_only_validate.py` proves it
    against the pre-refactor source restored from git before anything new used it.
    """
    from . import index_track
    from ..edge import append_only as AO
    _, hp = index_track.default_paths()
    # `columns` is the CALLER'S, defaulting to the bound series' own schema. The first cut of
    # this delegation hard-coded `ROW_COLUMNS` and so SILENTLY IGNORED the argument the SPMO
    # sibling passes to reuse this writer with its own header -- the parameter was accepted and
    # dropped, which refused a correct write rather than raising. Caught by the full gate;
    # `scripts/i1_append_only_validate.py` could not see it, because 200 cases swept every
    # BRANCH and never varied a PARAMETER.
    return AO.append(row, history_path or hp, key="date",
                     columns=(ROW_COLUMNS if columns is None else columns),
                     append_only=append_only, typer=typed_row,
                     backfill_hint=_BACKFILL_HINT)
