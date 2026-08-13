"""The scream-buy options track record, reset on 2026-08-13 and rebuilt with real fields.

WHAT DON ASKED FOR
------------------
Don, 2026-08-13: *"the options scream buys track record wiped, and include target sale, price
bought in, and current price, same as our paper account tracks."*

A WIPE IS THE ONE THING THIS PROJECT MUST NOT DO SILENTLY
---------------------------------------------------------
Deleting a track record is indistinguishable, after the fact, from deleting a track record
that was going badly. This project has already had to reason about exactly that: Amendment 1
voided paper-track run #1 while it sat **−2.85pp**, and the only reason that void is
defensible is that the cause was independent of the outcome, its clause pre-existed the run,
the new run accrued ZERO days so no window's sign could inform the start date, and **the
voided rows were kept and stayed visible** in `as_operated()`.

So this is not a wipe. It is a dated, reasoned **display epoch** with the prior record intact
in two places:

  * every pre-reset row is STILL IN THE DATABASE — nothing here deletes, updates or hides a
    row at the source. This module is a reader; it holds no SQL that writes.
  * the pre-reset record is in the committed archive `data_export/paper_track_history.json`,
    written by the weekly `track-backup` Action and carrying the full `option_alerts` and
    `paper_option_orders` tables. It was already an archive before this change; the reset did
    not create it and cannot lose it.

`RESET` below is the register note, rendered in the tab's footer. `SCREAM_TRACK_RESET.md` is
the same statement as a tracked document. The reason is recorded because a reset whose reason
is not written down is a reset whose reason gets reconstructed later, favourably.

THE REASON IS REAL AND IT IS NOT PERFORMANCE
--------------------------------------------
The prior record predates the corrected alert stack. `B1` alone re-based every underlying
price the options book was measured against — trades rose 3,042 → 3,885 once an adjusted spot
stopped being compared to as-traded strikes, and median entry IV moved 1.4200 → 0.2497,
because "142% vol" was never a vol. `U1-SPLIT` then removed a corporate-action artifact worth
24% of the published R2 gap. And the rows themselves lacked the entry/target/current fields
this display is built on, which is Don's actual complaint.

**THE DISCLOSURE THAT TRAVELS WITH IT:** the pre-reset record's own sign is not the reason,
but a reader is entitled to check that for themselves, which is why the archive path is on the
surface and not merely in this docstring.

CONSUME, DO NOT RECOMPUTE
-------------------------
Every number below is read from a column another lane writes:

  price bought in   `paper_option_orders.entry_premium`   the FILL, not the submit price
  target sale       `paper_option_orders.target_premium`  the alert's own policy, +100% default
  stop level        `paper_option_orders.stop_premium`
  current price     `paper_option_orders.last_mark` (+ `last_mark_ts` for staleness)
  DTE remaining     from `expiry`
  status            `state` + `exit_reason`

That list is not a wish. Those columns exist today (`paper_track.ensure_schema`) and the
weekly export already carries them. This module joins them to `option_alerts` for the contract
description, which is the same join `track_export._trade_rows` performs — *"the two tables
hold different halves of the same trade"*.

**WHY IT MATTERS THAT THESE ARE NOT RECOMPUTED HERE, and it is not tidiness.** Session 16
found that `_place_entry` anchored target and stop to the SUBMIT price while `mark_open`
overwrote `entry_premium` with the FILL, so **2 of 3 open positions were trading to levels no
backtest describes** — MET sat 10.2% above a stop the strategy would never have taken. The
repair put the levels on the fill, in `paper_track`, and `options_summary.level_conformance`
reports off-spec rows read-only on every request. A display that re-derived `entry × 2.0`
would look right, agree with the fixed code by coincidence, and silently stop agreeing the
next time the policy differs from the default. So this reads the stored level and, where the
conformance check has something to say, shows that too.

NOTHING HERE TRADES, AND NOTHING HERE WRITES. A display module that could write is one refresh
away from being an execution path.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from . import payoff

# --------------------------------------------------------------------------------------- #
# THE RESET REGISTER
# --------------------------------------------------------------------------------------- #

#: The epoch. Alerts stamped on or after this date are the rebuilt record; everything earlier
#: is the archived one. An ISO date, not a row id, so the boundary is checkable against the
#: archive by anyone with a text editor.
RESET_DATE = "2026-08-13"

#: Where the prior record lives, in the repository, committed. Quoted on the surface.
ARCHIVE_PATH = "data_export/paper_track_history.json"

#: The tracked long-form note. Same statement, somewhere a non-technical reader can find it.
REGISTER_DOC = "SCREAM_TRACK_RESET.md"

RESET_NOTE = (
    f"Record reset {RESET_DATE} at Don's direction; prior record archived at "
    f"{ARCHIVE_PATH}; reason: predates the corrected alert stack (B1 price basis, C-series "
    f"fixes) and lacked entry/target/current fields. Nothing was deleted — the archived rows "
    f"are still in the database and in the committed export."
)


def register() -> dict:
    """The reset, as the footer renders it."""
    return {"reset_date": RESET_DATE, "archive_path": ARCHIVE_PATH,
            "register_doc": REGISTER_DOC, "note": RESET_NOTE}


# --------------------------------------------------------------------------------------- #
# STATUS
# --------------------------------------------------------------------------------------- #

#: `exit_reason` (written by `paper_track._exit_decision`) -> the label Don asked for. The
#: mapping is a constant so the surface cannot invent a sixth status, and so an exit reason
#: this display has never seen renders as itself rather than as a guess.
STATUS_BY_REASON = {
    "target": "HIT TARGET",
    "stop": "STOPPED",
    "time_stop": "TIME-STOPPED",
    "expiry": "EXPIRED",
}

LIVE = "LIVE"

#: Live states in `paper_option_orders.state`. `closing` is LIVE on purpose: an exit order is
#: working but the position is still on, and calling it closed would book an outcome that has
#: not happened.
LIVE_STATES = ("open", "closing")


def status_for(row: dict) -> str:
    """The display status for one order row."""
    state = (row.get("state") or "").strip().lower()
    if state in LIVE_STATES:
        return LIVE
    reason = (row.get("exit_reason") or "").strip().lower()
    if reason in STATUS_BY_REASON:
        return STATUS_BY_REASON[reason]
    if reason:
        # An unmapped reason is shown verbatim rather than bucketed into the nearest label.
        # A wrong-but-plausible status is worse than an unfamiliar one.
        return reason.replace("_", " ").upper()
    return "CLOSED"


# --------------------------------------------------------------------------------------- #
# HELPERS
# --------------------------------------------------------------------------------------- #

def _f(x) -> Optional[float]:
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def _date(x) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


def dte(expiry, today: Optional[_dt.date] = None) -> Optional[int]:
    """Calendar days to expiry. Negative means it is past — reported, not clamped to zero."""
    d = _date(expiry)
    if d is None:
        return None
    return (d - (today or _dt.date.today())).days


#: How stale a mark may be before the surface says so, in calendar days. Deliberately not
#: reusing `freshness.WARN_AFTER` (2 TRADING days, for a daily scan): a quote and a scan are
#: different objects on different clocks, and borrowing a constant across them is how the
#: `MIN_LIVE_DAYS` / `MIN_DAYS_FOR_MEANING` pair came to govern one track with two numbers.
STALE_MARK_DAYS = 2


def mark_age(last_mark_ts, today: Optional[_dt.date] = None) -> dict:
    """{"days", "stale"} for a live mark, or {"days": None, "stale": True} if there is none.

    NO TIMESTAMP IS STALE, NOT FRESH. A missing `last_mark_ts` means nobody has marked this
    position, and rendering an unmarked price as current is the failure this flag exists for.
    """
    d = _date(last_mark_ts)
    if d is None:
        return {"days": None, "stale": True}
    age = ((today or _dt.date.today()) - d).days
    return {"days": age, "stale": age > STALE_MARK_DAYS}


def _pct_from(entry: Optional[float], level: Optional[float]) -> Optional[float]:
    """`level` as a return on `entry`, e.g. 2.0 from 1.0 -> +1.00 (+100%)."""
    if entry is None or level is None or entry <= 0:
        return None
    return level / entry - 1.0


# --------------------------------------------------------------------------------------- #
# THE TABLE
# --------------------------------------------------------------------------------------- #

def build_rows(orders: list, alerts: Optional[dict] = None,
               today: Optional[_dt.date] = None, reset_date: str = None) -> dict:
    """The rebuilt display rows. Pure — the caller supplies the two tables.

    `orders` are `paper_option_orders` rows; `alerts` maps `option_alerts.id` -> alert row and
    supplies the contract description only. Split this way so the whole table is testable
    against fixtures with no database, and so a missing alert row degrades one column rather
    than dropping a real position from a track record.
    """
    reset = reset_date or RESET_DATE
    alerts = alerts or {}
    today = today or _dt.date.today()
    rows, archived = [], 0

    for o in orders or []:
        if not isinstance(o, dict):
            continue
        a = alerts.get(o.get("alert_id")) or {}
        stamp = str(a.get("alert_ts") or o.get("created_at") or o.get("entry_ts") or "")[:10]
        # An UNDATED row counts as archived rather than current. The alternative — treating
        # "no date" as "after the reset" — would let the old record leak into the new one
        # through exactly the rows whose provenance is least clear.
        if not stamp or stamp < reset:
            archived += 1
            continue

        entry = _f(o.get("entry_premium"))
        target = _f(o.get("target_premium"))
        stop = _f(o.get("stop_premium"))
        mark = _f(o.get("last_mark"))
        st = status_for(o)
        age = mark_age(o.get("last_mark_ts"), today)
        exit_prem = _f(o.get("exit_premium"))
        # For a closed row the settled figure is the exit, not the last mark. Showing a stale
        # mark beside a realised outcome invites the reader to compute a third P&L.
        current = exit_prem if (st != LIVE and exit_prem is not None) else mark

        rows.append({
            "alert_id": o.get("alert_id"),
            "ticker": o.get("ticker") or a.get("ticker"),
            "occ_symbol": o.get("occ_symbol") or a.get("occ_symbol"),
            "opt_right": a.get("opt_right"),
            "strike": _f(a.get("strike")),
            "expiry": o.get("expiry") or a.get("expiry"),
            "alert_ts": a.get("alert_ts"),
            "entry_ts": o.get("entry_ts"),
            "contracts": o.get("contracts"),
            "status": st,
            "live": st == LIVE,
            # --- the four Don named, each read from its stored column ---
            "entry_premium": entry,
            "target_premium": target,
            "stop_premium": stop,
            "current_premium": current,
            # --- and the same levels as returns, which is how the policy is stated ---
            "target_pct": _pct_from(entry, target),
            "stop_pct": _pct_from(entry, stop),
            "current_pct": _pct_from(entry, current),
            "mark_stale": bool(age["stale"]) if st == LIVE else False,
            "mark_age_days": age["days"],
            "last_mark_ts": o.get("last_mark_ts"),
            "dte": dte(o.get("expiry") or a.get("expiry"), today),
            "exit_reason": o.get("exit_reason"),
            "exit_ts": o.get("exit_ts"),
        })

    rows.sort(key=lambda r: (str(r.get("alert_ts") or ""), str(r.get("alert_id") or "")),
              reverse=True)
    n_live = sum(1 for r in rows if r["live"])
    return {
        "rows": rows,
        "n_rows": len(rows),
        "n_live": n_live,
        "n_closed": len(rows) - n_live,
        "n_archived": archived,
        "register": register(),
        # R2, quoted from the one module that owns it rather than restated. `payoff` already
        # renders this sentence on the Signals tab; two copies of a caveat is two things to
        # keep true.
        "context": payoff.NOT_A_CLAIM,
        "context_source": payoff.SOURCE,
    }


def summary(store, today: Optional[_dt.date] = None) -> dict:
    """The route's payload: the rebuilt table read from the live store.

    Wraps `build_rows` with the database read and nothing else, so everything with a decision
    in it stays pure. Failure returns an EMPTY TABLE WITH ITS REGISTER, never a bare error: a
    track record that cannot be read must still say what it is and where the archive is.
    """
    from ..edge import paper_track

    try:
        paper_track.ensure_schema(store)
        orders = paper_track.paper_orders(store, limit=100000)
        alerts = {}
        with store._conn() as c:
            cur = c.execute("SELECT * FROM option_alerts")
            cols = [d[0] for d in cur.description]
            for r in cur.fetchall():
                row = dict(zip(cols, r))
                alerts[row.get("id")] = row
        out = build_rows(orders, alerts, today=today)
        # Read-only, and it stays here for the reason session 16 gave: the first time this
        # book was inspected, 2 of 3 open positions were trading to off-spec levels and
        # nothing anywhere said so.
        try:
            out["level_conformance"] = paper_track.options_summary(store).get(
                "level_conformance")
        except Exception:                                            # noqa: BLE001
            out["level_conformance"] = None
        return out
    except Exception as e:                                           # noqa: BLE001
        empty = build_rows([], {}, today=today)
        empty["error"] = type(e).__name__
        empty["unavailable"] = True
        return empty
