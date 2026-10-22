"""IS A REBALANCE LATE, REFUSED, OR COMING UP — the three things Don asked to be told. [item 74]

Don's ruling, 2026-10-18: *"A rebalance can't happen or is late"* goes to `#valquo-alerts`, with
three cases named:

  * **OVERDUE** — more than one trading day past the in-force book's `next_rebalance` with no
    newer book installed. For 2026-10-22 that means an alert from the morning of 10-26.
  * **REFUSED** — the service refused a new book (conformance, thin data, unpriced names, or
    anything else).
  * **HEADS-UP** — 14 calendar days before each rebalance date: *"Rebalance due `<date>`. It
    needs Sharadar data — make sure your access is active."*

**WHY THIS IS A MODULE AND NOT A STEP IN A WORKFLOW.** The dates are DERIVED — `next_rebalance`
is 63 trading days from the in-force event's own scan date, and `index_in_force` already owns
that arithmetic. A workflow carrying its own copy of the date would be right for one quarter and
silently wrong for every quarter after it, which is the clock-shaped guard this project has
repointed three times. So the workflow is thin and asks the service, and the service derives.

**WHY "ONE TRADING DAY PAST" AND NOT "ON THE DAY".** The book is built on the evening AFTER the
rebalance date (the runbook's own window), so an alert on 10-22 itself would fire during the
ordinary, correct sequence. One trading day of grace is the smallest bound that does not cry
wolf on the expected path — and `MA21`'s rule is the reason to care: a check that fires when
nothing is wrong is one you learn to ignore, and then the day it matters nobody looks.

**WHAT IT NEVER SAYS.** No level, no excess, no verdict. A rebalance alert is about whether an
event happened on time, and the figures have a pre-committed horizon.
"""
from __future__ import annotations

import datetime as _dt

#: Trading days past `next_rebalance` before a missing event is OVERDUE. See the docstring.
OVERDUE_GRACE_TRADING_DAYS = 1

#: Calendar days before a rebalance date that the heads-up fires. Calendar rather than trading
#: days on purpose: the thing it asks Don to do is renew a data subscription, and a vendor's
#: billing runs on the calendar.
HEADS_UP_CALENDAR_DAYS = 14

#: The sentence Don asked for, verbatim, with the date substituted. Held as a constant so the
#: door, the test and any future surface cannot each phrase it differently.
HEADS_UP_SENTENCE = ("Rebalance due {date}. It needs Sharadar data — make sure your access is "
                     "active.")


def _date(x):
    if x is None or x == "":
        return None
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def status(*, as_of=None, meta_path: str = None, refusal: dict = None) -> dict:
    """The rebalance's state, and the alerts it implies. Never raises.

    `refusal` is supplied by the caller — the service knows whether its last attempt to install
    a book was refused and this module cannot. Shaped `{"when": iso, "reason": str}`.

    Returns `{"ok", "reason", "in_force", "scan_date", "next_rebalance", "days_late",
    "overdue", "heads_up", "alerts"}`. `alerts` carries the registry kinds, so the caller routes
    them exactly as it routes a live-cycle alert — one classification for the whole project.
    """
    from . import index_in_force as IIF

    today = _date(as_of) or _dt.date.today()
    out = {"ok": True, "reason": "", "as_of": today.isoformat(), "in_force": None,
           "scan_date": None, "next_rebalance": None, "days_late": None,
           "overdue": False, "heads_up": False, "alerts": []}

    if refusal and (refusal.get("reason") or "").strip():
        # REPORTED FIRST AND INDEPENDENTLY OF THE DATES. A refused book is a problem whether or
        # not the date has passed, and it is the one case where the remedy is immediate.
        out["refused"] = {"when": str(refusal.get("when") or ""),
                          "reason": str(refusal.get("reason"))}
        out["alerts"].append({
            "kind": "rebalance_refused", "slot": "-",
            "reason": ("the service refused a new Index book: %s. No rebalance has been "
                       "recorded, so the book in force is unchanged. Open the run and fix the "
                       "refusal, then re-run the build."
                       % str(refusal.get("reason"))[:400])})

    try:
        bk = IIF.book_in_force(meta_path=meta_path, as_of=today) if meta_path \
            else IIF.book_in_force(as_of=today)
    except Exception as e:                                             # noqa: BLE001
        out["ok"] = False
        out["reason"] = "the bound book could not be read (%s)" % type(e).__name__
        return out

    if not bk.get("ok"):
        # **ABSENT IS NOT ON TIME (`C5`).** A book nobody can read cannot be shown to be
        # current, so this is an alert rather than a silent pass — and it names the file
        # problem rather than claiming a rebalance is late, because those are different faults.
        out["ok"] = False
        out["reason"] = bk.get("reason") or "no book is in force"
        out["alerts"].append({
            "kind": "rebalance_overdue", "slot": "-",
            "reason": ("the Index book in force could not be read, so whether a rebalance is "
                       "due cannot be answered: %s. Nothing is being traded off a book that "
                       "cannot be read. Check the service's bound record."
                       % (bk.get("reason") or "unknown"))})
        return out

    out["in_force"] = bk.get("formed_on") or bk.get("date")
    scan = bk.get("scan_date")
    out["scan_date"] = scan
    nxt = IIF.next_rebalance(scan) if scan else None
    out["next_rebalance"] = nxt
    if not nxt:
        out["reason"] = ("the book in force carries no scan date, so the next rebalance cannot "
                         "be derived")
        return out

    nd = _date(nxt)
    # THE HEADS-UP, on calendar days, and only while the date is still ahead.
    if today <= nd and (nd - today).days <= HEADS_UP_CALENDAR_DAYS:
        out["heads_up"] = True
        out["alerts"].append({
            "kind": "rebalance_due_soon", "slot": "-",
            "reason": HEADS_UP_SENTENCE.format(date=nxt)})

    # OVERDUE, on TRADING days past the date, and only if no newer book has landed. The event
    # in force being ON OR AFTER the due date IS a newer book: that is what a rebalance does.
    if today > nd:
        from . import market_session as _ms
        late = _ms.trading_days_between(nd, today, inclusive_start=False)
        out["days_late"] = int(late)
        landed = _date(out["in_force"])
        if landed is not None and landed >= nd:
            out["reason"] = ("the %s rebalance has landed (the book in force was formed on %s)"
                             % (nxt, out["in_force"]))
        elif late > OVERDUE_GRACE_TRADING_DAYS:
            out["overdue"] = True
            out["alerts"].append({
                "kind": "rebalance_overdue", "slot": "-",
                "reason": ("the Index rebalance due %s has not been recorded and it is now %d "
                           "trading days past. The book in force is still the one formed on "
                           "%s, so the Index is being marked on a stale selection. Run the "
                           "rebalance runbook, or decide to skip this quarter."
                           % (nxt, late, out["in_force"]))})
        else:
            out["reason"] = ("the %s rebalance is %d trading day(s) past and inside the %d-day "
                             "grace, which is the ordinary build window"
                             % (nxt, late, OVERDUE_GRACE_TRADING_DAYS))
    return out


def record_status(*, as_of=None, detail: dict = None) -> dict:
    """Is the daily record complete, and does `recording_ok` read false? [item 74]

    `detail` is `track_meter.detail()`, passed in rather than computed: this module must not be
    the second place that decides what a gap is, and the contract's own meter is the first.
    `track_meter` already names every missing trading day, so this turns that into the two
    alerts Don asked for and adds nothing of its own.

    **`recording_ok is None` IS NOT A FAILURE.** The meter returns `None` before the vintage's
    first row is due, which is the contract's own not-vacuously-green rule. Alerting on it would
    fire every time a vintage opens.

    **THE MISSING DATES COME FROM `per_vintage_recording`, AND I GUESSED THAT KEY WRONG FIRST.**
    My first cut read `detail()["gaps"]["missing"]`, and `detail()` has no `gaps` key at all —
    so `missing` was always empty and the row-missing alert could never fire, while
    `recording_ok` was independently False and made the function look like it was working. The
    wrong-object family: a lookup that computes cleanly, raises nothing, and answers about an
    object that does not exist. Measured instead: the dates live in
    `per_vintage_recording[*]["missing_dates"]`, and only the OPEN vintage's are owed — a closed
    vintage's misses are history the contract has already recorded and cannot be acted on.
    """
    out = {"ok": True, "recording_ok": None, "missing": [], "alerts": []}
    d = dict(detail or {})
    if not d:
        return out
    ok = d.get("recording_ok")
    out["recording_ok"] = ok
    missing = []
    for v in (d.get("per_vintage_recording") or []):
        if str((v or {}).get("status") or "").upper() == "OPEN":
            missing.extend(str(x) for x in ((v or {}).get("missing_dates") or []))
    out["missing"] = missing

    if missing:
        out["alerts"].append({
            "kind": "record_row_missing", "slot": "-",
            "reason": ("the forward record is missing %d trading day row(s): %s. The record is "
                       "append-only and a missed day cannot be backfilled, so each one is "
                       "permanent. Check that the daily writer ran."
                       % (len(missing), ", ".join(missing[:8])
                          + (" and %d more" % (len(missing) - 8) if len(missing) > 8 else "")))})
    if ok is False:
        out["ok"] = False
        # **THE CAUSE IS IN THE REASON, AND THAT IS WHAT MAKES "ONCE" SAFE [item 78 §5].**
        # This kind is exempt from the daily reminder (`alert_routing.NO_DAILY_REMINDER`)
        # because it follows from missed days that cannot be backfilled. A condition is keyed
        # on `(kind, reason[:120])`, so with a CONSTANT reason it would be announced once and
        # then never again however much worse it got -- which is the opposite failure. Naming
        # the count makes a new missing day a new signature and therefore a new post, which is
        # the brief's *"re-announce only when its cause changes"*.
        out["alerts"].append({
            "kind": "recording_not_ok", "slot": "-",
            "reason": ("the contract's own recording gate reads FALSE (%d missing trading day "
                       "row(s)), so the forward record is not complete for the open vintage. "
                       "The operational gate cannot pass while this is false. See /api/track."
                       % len(missing))})
    return out
