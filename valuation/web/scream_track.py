"""The scream-buy track record, as the tab renders it. A CONSUMER, not a second logger.

WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT
----------------------------------------------
Don, 2026-08-13: *"the options scream buys track record wiped, and include target sale, price
bought in, and current price, same as our paper account tracks."*

The prompt split that in two: the greeks lane owns the LOGGER (schema, archive, status
vocabulary, the read-time quote) and this lane owns the TAB. `valuation/edge/scream_log.py`
landed first, and its field contract is in `HANDOFF_appfixes.md` under *"FROM THE GREEKS
LANE"*. Every number below comes from that module. This file computes **no** premium, **no**
status, **no** staleness and **no** epoch boundary of its own.

THIS FILE WAS REWRITTEN TO BECOME A CONSUMER, AND THE REASON IS WORTH KEEPING
-----------------------------------------------------------------------------
Its first version was written before the logger landed and reimplemented all of it: its own
five-status map, its own reset note, its own staleness rule, and an epoch expressed as
`alert_ts >= "2026-08-13"`. Three of those were not merely duplicated, they were **wrong**:

  * **It read `paper_option_orders`, so its "price bought in" was the BROKER FILL.** The
    logger's `entry_premium` is the **alert-time** premium. Those are different books, and
    session 16 exists precisely because they were once conflated — which the old docstring
    quoted at length, while making the same mistake one layer up. This is the substantive
    correction, and it is the one that would have put a wrong number on the screen.
  * **The epoch was a DATE COMPARISON.** The real boundary is `record_epoch`, a value stamped
    on the row by `reset_record`. A date is a guess about when a reset ran; the stamp is the
    reset. And the record has NOT been reset yet — it cannot be from a dev box, because every
    local database holds zero scream-buy rows and the real one is on Render's disk. A
    date-based epoch would have hidden every pre-2026-08-13 row **as though** a reset had
    already happened. That is the worst available failure for a track record: it looks reset.
  * **Staleness was a two-day calendar rule.** The logger marks a quote stale at **15
    minutes**, because a current option premium is a different object from a daily scan's
    freshness. Borrowing a constant across two clocks is the `MIN_LIVE_DAYS` /
    `MIN_DAYS_FOR_MEANING` defect, and this had it.

There were also five statuses here and there are **six**: `CLOSED (unscoreable)` exists so a
closed row whose exit reason maps to none of Don's five is not forced into one that
misdescribes it.

WHAT THIS FILE STILL DOES
-------------------------
Exactly three things, none of which is a measurement:

  1. calls `records` → `attach_live_marks` → `record_summary`, in that order;
  2. carries the **R2 context line**, quoted from `web/payoff.py` — the module that owns it —
     so the tab cannot show a track record without the finding that the entry signal loses to
     random entry;
  3. fails soft. A record that cannot be read still returns its footer, because a track record
     rendering as a bare error has lost the one thing it was supposed to say.

NOTHING HERE WRITES, AND THE RESET IS NOT TRIGGERED HERE. `scream_log.reset_record` is an
admin action; a display module that could reset a track record is one refresh away from being
able to erase one.
"""
from __future__ import annotations

from typing import Optional

from . import payoff

#: Rows fetched per request. The logger's own default is 500; this is the display's slice and
#: it is reported in the payload rather than applied silently.
DEFAULT_LIMIT = 200


def _summary_fallback() -> dict:
    """The footer when the record cannot be read at all."""
    return {"epoch": None, "reset": None, "n_prior_epochs": None, "unavailable": True}


def summary(store, limit: int = DEFAULT_LIMIT, quotes: Optional[dict] = None) -> dict:
    """The tab's payload: the current epoch's record, marked live, with its footer.

    `quotes` is injectable so a test can drive the live-mark path without a broker; left None,
    the logger fetches quotes for the LIVE rows only.
    """
    from ..edge import scream_log as SL

    out = {
        "rows": [],
        "n_rows": 0,
        "n_live": 0,
        "n_closed": 0,
        "limit": int(limit),
        "statuses": list(SL.ALL_STATUSES),
        "live_fields": list(SL.LIVE_FIELDS),
        # R2, from the one module that owns it. Not restated here — a second copy of a caveat
        # is a second thing to keep true.
        "context": payoff.NOT_A_CLAIM,
        "context_source": payoff.SOURCE,
    }

    try:
        recs = SL.records(store, limit=int(limit))
        q = quotes if quotes is not None else SL.live_quotes_for(recs)
        recs = SL.attach_live_marks(recs, q)
        foot = SL.record_summary(store)
    except Exception as e:                                           # noqa: BLE001
        out["summary"] = _summary_fallback()
        out["unavailable"] = True
        out["error"] = type(e).__name__
        return out

    live = [r for r in recs if (r.get("status") or "") == SL.STATUS_LIVE]
    out["rows"] = recs
    out["n_rows"] = len(recs)
    out["n_live"] = len(live)
    out["n_closed"] = len(recs) - len(live)
    out["summary"] = foot
    # Lifted out of the footer because these are what make a reset VISIBLE rather than merely
    # honest: a table of three rows reads very differently when the footer says 41 alerts sit
    # in an earlier epoch. `reset` is None until a reset has actually run, and the surface says
    # so rather than implying one happened.
    out["epoch"] = foot.get("epoch")
    out["reset"] = foot.get("reset")
    out["n_prior_epochs"] = foot.get("n_prior_epochs")

    # Read-only, and kept for the reason session 16 gave: the first time the paper book was
    # inspected, 2 of 3 open positions were trading to off-spec levels and nothing anywhere
    # said so. Labelled `paper_` because it describes the PAPER BOOK, which is a different
    # object from the record above — the conflation this module was rewritten to undo.
    try:
        from ..edge import paper_track
        out["paper_level_conformance"] = paper_track.options_summary(store).get(
            "level_conformance")
    except Exception:                                                # noqa: BLE001
        out["paper_level_conformance"] = None
    return out
