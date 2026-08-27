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

#: The invalidation stream is METADATA ABOUT the series above, not one of them, so it is
#: deliberately NOT in `SERIES`. `SERIES` means "a daily observation a book reads", and putting
#: a metadata stream in it made `coverage()` report it as a fourth series and forced
#: `record_all` to special-case it out again -- two wrongs describing one thing.
INVALIDATIONS = "invalidations"
INVALIDATION_COLUMNS = ("date", "n_spans", "payload")

BACKFILL_HINT = (" A missed day is a GAP and stays one: these series are evidence about what "
                 "was observable on a date, and a value computed later from today's data is "
                 "not that. Record the gap, never the guess.")

#: The reason a recorder refuses when its source was never consulted.
#:
#: **A SOURCE THAT WAS NOT CONSULTED IS NOT AN OBSERVATION OF NOTHING** (audit #5, `H2`). The
#: production caller passed nothing for months, so `dip_rejects` asserted "zero names were
#: rejected today" from a screen that never ran and `iv60_atm` asserted "no name had a solvable
#: 60-DTE IV" with no chain ever fetched. Both are positive claims of ABSENCE, and `F-11`'s
#: hypothesis is a name's FIRST APPEARANCE, so every fabricated empty day is evidence against
#: exactly the thing that book exists to detect.
#:
#: The distinction the recorders now enforce is between `None` (**NOT CONSULTED** -- refuse) and
#: an empty collection (**CONSULTED AND EMPTY** -- a real observation, recorded). It is the same
#: rule `record_iv60` already applied one level down, where a name with no solvable IV is
#: OMITTED rather than recorded as zero, lifted to the source.
NOT_CONSULTED = (
    "SOURCE NOT CONSULTED: pass an empty collection to assert 'ran and found nothing', or "
    "nothing at all to say 'did not run'. A content-free write is still a write, and a row "
    "that says zero when no screen ran is evidence AGAINST a first appearance that may have "
    "happened. Refusing leaves a GAP, which is recoverable; a fabricated zero is not.")


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


def read(name: str, root: str = None, *, honour_invalidations: bool = True) -> dict:
    """The whole series, oldest first, with its payloads decoded.

    An ABSENT series and an EMPTY one are reported apart (`O21-D2`'s `C5`): "no recorder has
    ever run" and "the recorder ran and observed nothing" need different fixes.

    **EVERY ROW CARRIES `invalid`, and `n_valid` IS REPORTED BESIDE `n` (audit #5, `H2`).** The
    rows are still returned -- they are kept, not erased -- but a consumer that reads `n` and
    ignores `invalid` is counting fabricated days. `history_for` honours it for you, which is
    the path every book actually uses.

    `honour_invalidations=False` exists so `invalid_spans` can read its own series without
    recursing, and for a caller that genuinely wants the raw stream. It is not a way to get a
    clean-looking count.
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
    spans = invalid_spans(root) if honour_invalidations else []
    out = []
    for r in rows:
        try:
            payload = json.loads(r.get("payload") or "null")
        except ValueError:
            payload = None
        d = (r.get("date") or "")[:10]
        bad = is_invalid(name, d, spans=spans) if honour_invalidations else False
        out.append({"date": d, "payload": payload, "raw": r, "invalid": bad})
    n_invalid = sum(1 for r in out if r["invalid"])
    return {"ok": True, "absent": False, "vacuous": not out, "rows": out, "n": len(out),
            "n_valid": len(out) - n_invalid, "n_invalid": n_invalid,
            "columns": cols, "reason": ""}


def history_for(name: str, ticker: str, root: str = None) -> list:
    """`[(date, value)]` for one name, oldest first, skipping days it was not observed.

    A day on which the name was absent is NOT carried forward and is NOT zero-filled. An
    expanding percentile over a forward-filled series would count one observation many times
    and report a burn-in that had not been served -- `I-2`'s finding, that an observation
    COUNT and an elapsed SPAN come apart, in its most damaging form.

    **A ROW A FORWARD RECORD MARKS INVALID IS SKIPPED (audit #5, `H2`)**, for the same reason
    an absent day is: it is not an observation. This is the path the books read, so honouring
    it here is what actually protects a study.
    """
    t = str(ticker).upper()
    out = []
    for r in read(name, root)["rows"]:
        if r.get("invalid"):
            continue
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
        good = [x["date"] for x in r["rows"] if not x.get("invalid")]
        out[name] = {"present": True, "n_days": len(dates),
                     # AUDIT #5 H2: `n_days` alone would still report the fabricated span as
                     # coverage. A consumer must be able to see what is actually usable.
                     "n_days_valid": len(good), "n_days_invalid": len(dates) - len(good),
                     "first": dates[0] if dates else None,
                     "last": dates[-1] if dates else None,
                     "first_valid": good[0] if good else None,
                     "last_valid": good[-1] if good else None,
                     "vacuous": not dates,
                     "usable": bool(good),
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

    **`None` REFUSES (audit #5, `H2`).** It used to record an EMPTY day, and its docstring
    called that "a real observation", which is exactly what it is not when the caller never ran
    a screen. Pass `[]` to assert *ran and found nothing*; pass nothing to say *did not run*,
    and the day is left as a GAP.
    """
    date = date or _dt.date.today().isoformat()
    if rejects is None:
        return {"ok": False, "wrote": False, "already_present": False,
                "not_consulted": True, "reason": NOT_CONSULTED}
    names = sorted({str(t).upper() for t in rejects})
    return record("dip_rejects", date, names, count=len(names), root=root)


def record_iv60(date: str = None, *, quotes=None, root: str = None) -> dict:
    """F-5: 60-DTE ATM implied vol per name, from the live chain.

    `quotes` is `{ticker: iv}` supplied by the caller for the same reason as above: fetching a
    chain per name is the expensive part and the process that already holds a provider should
    own it. **A name with no solvable IV is OMITTED, never recorded as zero** -- a zero IV
    would enter an expanding percentile as the cheapest observation the name ever had, which
    is precisely backwards.

    **AND `None` NOW REFUSES (audit #5, `H2`), which is that same rule one level up.** Omitting
    a name with no solvable IV was always right; recording `{}` because no chain was ever
    fetched asserted that NO name had one. Pass `{}` to assert *ran and solved nothing*.
    """
    date = date or _dt.date.today().isoformat()
    if quotes is None:
        return {"ok": False, "wrote": False, "already_present": False,
                "not_consulted": True, "reason": NOT_CONSULTED}
    clean = {}
    for t, v in quotes.items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == f and f > 0:
            clean[str(t).upper()] = round(f, 6)
    return record("iv60_atm", date, clean, count=len(clean), root=root)


#: The two series whose every pre-fix row was written from a source that was never consulted.
FABRICATED_SERIES = ("dip_rejects", "iv60_atm")

FABRICATED_REASON = (
    "AUDIT #5 H2: every row in this span was written by a production caller that passed NO "
    "source. `dip_rejects` asserted 'zero names rejected' from a dip screen that does not "
    "exist in this repository; `iv60_atm` asserted 'no name had a solvable 60-DTE IV' with no "
    "chain ever fetched. These are positive assertions of ABSENCE and must not be read as "
    "observations. F-11's hypothesis is a name's FIRST APPEARANCE, so treating these days as "
    "real would date the first appearance to the day the screen was finally wired and read the "
    "preceding span as genuine absence -- the finding would be manufactured by the recorder.")


def invalidate_fabricated_span(root: str = None, *, date: str = None) -> dict:
    """Mark every PRE-EXISTING row of the fabricated series invalid. Runs ONCE, ever.

    **THE SPAN IS FROZEN AT FIRST APPLICATION, and that is the load-bearing detail.** Once the
    caller is fixed these series start accruing REAL rows, so a span recomputed daily from
    "everything on disk" would swallow the good days too. The idempotency key is therefore the
    EXISTENCE of any invalidation for that series, not the span's endpoints.

    Forward-only, by construction: it appends an `invalidations` record and never touches the
    series it describes. The append-only rule is not weakened anywhere.
    """
    done = {s.get("series") for s in invalid_spans(root)}
    out = {"applied": [], "already_done": sorted(done & set(FABRICATED_SERIES)),
           "nothing_to_do": [], "ok": True, "reason": ""}
    spans = []
    for name in FABRICATED_SERIES:
        if name in done:
            continue
        r = read(name, root, honour_invalidations=False)
        dates = [x["date"] for x in (r.get("rows") or []) if x.get("date")]
        if not dates:
            out["nothing_to_do"].append(name)      # never ran here; nothing to invalidate
            continue
        spans.append({"series": name, "from": min(dates), "to": max(dates),
                      "reason": FABRICATED_REASON})
        out["applied"].append({"series": name, "from": min(dates), "to": max(dates),
                               "n_days": len(dates)})
    if not spans:
        return out
    # ONE call, so the date-keyed stream cannot drop the second span.
    res = invalidate_many(spans, date=date, root=root)
    out["ok"] = bool(res.get("ok"))
    out["reason"] = res.get("reason", "")
    if not out["ok"]:
        out["applied"] = []                        # nothing landed; do not claim it did
    return out


def iv60_from_store(store=None) -> dict:
    """`{ticker: iv}` from the intraday scan the cycle has ALREADY paid for.

    **THIS IS THE SOURCE `record_iv60` WAS ALWAYS MEANT TO GET (audit #5, `H2`).** The module
    declines to fetch a chain per name because that is expensive -- but the intraday options
    scan already solved a 60-DTE ATM IV and carries it as `detail.atm_iv_60d`, in the same
    store `record_alert_count` reads. So the real source cost nothing and simply was not wired.

    Returns `{}` when the scan ran and solved nothing, which is a REAL observation and records.
    Returns `None` only when the scan itself is unavailable, which is NOT CONSULTED and refuses.
    A name whose IV is missing or unusable is OMITTED, never zero-filled.
    """
    if store is None:
        from ..screener.store import Store
        store = Store()
    try:
        rows = store.load_intraday()
    except Exception:                                            # noqa: BLE001
        return None                                              # scan unavailable -> refuse
    if rows is None:
        return None
    out = {}
    for r in rows:
        t = str((r or {}).get("ticker") or "").upper().strip()
        if not t:
            continue
        d = (r or {}).get("detail") or {}
        try:
            v = float(d.get("atm_iv_60d"))
        except (TypeError, ValueError):
            continue
        if v == v and v > 0:
            out[t] = v
    return out


def record_all(date: str = None, *, store=None, rejects=None, quotes=None,
               root: str = None) -> dict:
    """Every recorder, once. Returns per-series outcomes; never raises on one failing.

    A recorder that raised would take the whole cycle down with it, and the cycle's other work
    -- the gates, the refusals, the fills -- is independent of whether a series accrued.

    **BUT A SERIES THAT FAILS TO START IS LOUD, AND THAT IS THE POINT OF THIS FAMILY.** The
    whole value of a recorder is that a two-year clock begins TODAY, and **the one failure that
    would make that false while every test still passes is a series that quietly records
    nothing** -- an unreachable service, a read-only disk, a permissions fault. So after every
    attempt each series is RE-READ from disk, and one that is still ABSENT is reported in
    `failed_to_start`, which the runner's door surfaces and the cycle note names.

    ABSENT-AFTER-ATTEMPT IS THE TEST, not the return value of the write. A writer can return
    a cheerful `ok` and leave nothing on disk; only reading it back can tell.
    """
    date = date or _dt.date.today().isoformat()
    out = {"date": date, "series": {}}

    # A SERIES WHOSE ROW FOR TODAY IS ALREADY ON DISK NEEDS NO SOURCE, and must not be
    # reported as one that went unconsulted. The expensive sources belong to whichever
    # process already pays for them -- the dip screen costs ~188s on the service, measured,
    # against the runner's 120s budget -- so the scan worker records and the cycle finds the
    # row already there. Crying wolf on a day that IS recorded is the fastest way to teach
    # everyone to ignore this alarm (`MA21`).
    already = set()
    for name in SERIES:
        for r in ((read(name, root) or {}).get("rows") or []):
            if r.get("date") == date and not r.get("invalid"):
                already.add(name)
                break

    for name, fn, kw in (("alert_count", record_alert_count, {"store": store}),
                         ("dip_rejects", record_dip_rejects, {"rejects": rejects}),
                         ("iv60_atm", record_iv60, {"quotes": quotes})):
        try:
            r = fn(date, root=root, **kw)
            out["series"][name] = {"wrote": bool(r.get("wrote")),
                                   "already_present": bool(r.get("already_present")),
                                   "ok": bool(r.get("ok")),
                                   "not_consulted": bool(r.get("not_consulted")),
                                   "reason": r.get("reason", "")}
        except Exception as e:                                   # noqa: BLE001
            out["series"][name] = {"wrote": False, "ok": False, "already_present": False,
                                   "not_consulted": False, "reason": str(e)}
    out["recorded"] = sum(1 for v in out["series"].values() if v["wrote"])

    failed, not_consulted = [], []
    for name in SERIES:
        back = read(name, root)
        started = bool(back.get("ok")) and not back.get("absent") and back.get("n")
        out["series"].setdefault(name, {"wrote": False, "ok": False, "reason": "not attempted"})
        out["series"][name]["series_started"] = bool(started)
        if not started:
            failed.append(name)
        if out["series"][name].get("not_consulted") and name not in already:
            not_consulted.append(name)
        if name in already:
            out["series"][name]["already_recorded_today"] = True

    out["failed_to_start"] = failed
    out["not_consulted"] = not_consulted
    # **BOTH STATES ARE LOUD, AND THE SECOND IS THE ONE AUDIT #5 FOUND.** A series with months
    # of history passes `series_started` forever, so a source that silently stopped being
    # consulted could never reach `failed_to_start`. TODAY's row is the thing being asserted,
    # and a day on which no source was consulted is a day this cycle recorded nothing --
    # whatever the series holds from before.
    out["ok"] = not failed and not not_consulted
    parts = []
    if failed:
        parts.append(
            "SERIES FAILED TO START: %s. A recorder whose series is still ABSENT after "
            "an attempted write has recorded NOTHING, and a clock that has not started "
            "cannot be started retroactively. Check the filesystem is writable where "
            "the cycle runs." % ", ".join(failed))
    if not_consulted:
        parts.append(
            "SOURCE NOT CONSULTED, SO NO ROW WAS WRITTEN: %s. This is a GAP, deliberately, "
            "and a gap is recoverable. The alternative -- a row saying zero when nothing ran "
            "-- is a positive assertion of ABSENCE that a first-appearance study cannot tell "
            "from a real one. Wire a source or accept the gap." % ", ".join(not_consulted))
    out["loud"] = " ".join(parts)
    return out


# ---------------------------------------------------------------------------------------
# INVALIDATION. A forward record, because backward writes are REFUSED and stay refused.
# ---------------------------------------------------------------------------------------
def invalidate(series: str, first: str, last: str, reason: str, *, date: str = None,
               root: str = None) -> dict:
    """Mark `series` rows in `[first, last]` INVALID, by appending a record TODAY.

    **THE APPEND-ONLY RULE IS NOT WEAKENED, and that is the whole design.** These streams
    refuse a backward write because "a series whose past can be rewritten is not evidence",
    and audit #5's fabricated rows do not earn an exception -- a recorder that could erase its
    own bad days could erase its good ones. So the bad span is not edited, not deleted and not
    corrected: a FORWARD record says it must not be read, and every consumer here honours it.

    `PT-AMEND1`'s shape: dated, disclosed, kept, never edited away.
    """
    return invalidate_many([{"series": series, "from": first, "to": last, "reason": reason}],
                           date=date, root=root)


def invalidate_many(spans, *, date: str = None, root: str = None) -> dict:
    """Mark several spans invalid in ONE forward record.

    **IT TAKES A LIST BECAUSE THE UNDERLYING STREAM IS IDEMPOTENT PER DATE.** `record` is keyed
    on `date`, so a second write on the same day is a NO-OP that returns the row already on
    disk -- and a caller invalidating two series in one cycle would have had the second span
    SILENTLY DROPPED, in the direction that reads as success. That is `S3-I1`'s defect
    verbatim, where reusing a date-keyed writer for a many-per-day record dropped every entry
    after the first. Found here by a test that invalidated two series at once and watched the
    second vanish.

    The written payload is CUMULATIVE, so one read answers the whole question, and the write
    is verified by reading it back -- a same-date collision that dropped content is reported
    as a failure rather than returning a cheerful `ok`.
    """
    date = date or _dt.date.today().isoformat()
    prior = [s for s in invalid_spans(root) if s.get("series")]
    fresh = []
    for sp in spans or []:
        name = str(sp.get("series"))
        if name not in SERIES:
            return {"ok": False, "wrote": False,
                    "reason": "cannot invalidate %r; it is not a daily series" % name}
        span = {"series": name, "from": str(sp.get("from"))[:10],
                "to": str(sp.get("to"))[:10], "reason": str(sp.get("reason") or "")}
        if any(p["series"] == span["series"] and p["from"] == span["from"]
               and p["to"] == span["to"] for p in prior + fresh):
            continue
        fresh.append(span)
    if not fresh:
        return {"ok": True, "wrote": False, "already_present": True,
                "reason": "every requested span is already marked invalid"}
    payload = prior + fresh
    os.makedirs(history_dir(root), exist_ok=True)
    row = {"date": str(date)[:10], "n_spans": len(payload),
           "payload": json.dumps(payload, sort_keys=True, separators=(",", ":"))}
    res = AO.append(row, series_path(INVALIDATIONS, root), key="date",
                    columns=INVALIDATION_COLUMNS, append_only=True,
                    backfill_hint=BACKFILL_HINT)

    # READ IT BACK. The write above can be a same-date no-op, which returns `ok` while
    # storing nothing -- the exact failure this function exists to avoid.
    stored = invalid_spans(root)
    missing = [s for s in fresh
               if not any(t["series"] == s["series"] and t["from"] == s["from"]
                          and t["to"] == s["to"] for t in stored)]
    if missing:
        return {"ok": False, "wrote": False, "dropped": missing,
                "reason": ("the invalidation was NOT stored: an `invalidations` record already "
                           "exists for %s and the stream is idempotent per date, so this write "
                           "was a no-op. Re-run on a later date, or pass every span in ONE "
                           "call." % date)}
    res["spans_added"] = fresh
    return res


def invalid_spans(root: str = None) -> list:
    """Every span ever marked invalid, from the LATEST forward record.

    The record is cumulative rather than incremental so one read answers the question. An
    absent series means nothing has been invalidated, which is different from an empty one and
    is why `read` reports the two apart.
    """
    rows, _cols, err = AO.read_rows(series_path(INVALIDATIONS, root))
    if err or not rows:
        return []
    try:
        payload = json.loads(rows[-1].get("payload") or "null")
    except ValueError:
        return []
    return [s for s in (payload or []) if isinstance(s, dict)]


def is_invalid(series: str, date: str, spans=None, root: str = None) -> bool:
    """Does a forward record say this `(series, date)` row must not be read?"""
    d = str(date)[:10]
    for s in (invalid_spans(root) if spans is None else spans):
        if s.get("series") == series and str(s.get("from")) <= d <= str(s.get("to")):
            return True
    return False
