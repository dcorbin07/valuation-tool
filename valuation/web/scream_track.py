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



# ---------------------------------------------------------------------------- item 66, part 3
#: Checked ONCE A DAY, which is why a stop books past its level. The scorer walks daily
#: bid-side marks, so a contract that gaps through -50% overnight is booked at wherever it was
#: when the scorer next looked -- not at -50%. The number on the screen is therefore the REAL
#: outcome and not the policy's, and a reader comparing it to "-50% stop" needs that sentence.
STOP_CADENCE_NOTE = (
    "Stops are checked ONCE A DAY against the previous session's bid-side mark, so a stop "
    "books at wherever the contract was when the scorer next looked -- past -50%, often well "
    "past it, when the move happened overnight. These are realised outcomes, not the policy's "
    "levels.")

#: Why a closed row closed where it did. Three sources, and they are different kinds of
#: evidence: a PAPER FILL is an execution, a SCORED exit is this project marking its own
#: alert, and a REFUSED one never had a position at all.
EXIT_SOURCE_PAPER = "paper fill"
EXIT_SOURCE_SCORED = "scored from daily bid-side marks"
EXIT_SOURCE_REFUSED = "broker refused - no position was ever held"
EXIT_SOURCE_UNKNOWN = "unknown"


def exit_source(row: dict, paper_filled: set = None, paper_refused: set = None) -> str:
    """Where a closed row's exit price came from. PURE, and it says UNKNOWN rather than guess.

    **THE THREE ARE NOT INTERCHANGEABLE AND THE TAB MUST NOT IMPLY THEY ARE.** A paper fill is
    an execution at a broker; a scored exit is this project marking its own alert against a
    daily bid-side quote, which is the path `/admin/score-alerts` takes and which exists
    precisely because the $1,000 budget declined many alerts; and a refused alert never held a
    position, so its "outcome" is a scoring convention rather than a trade. Labelling all
    three "closed" is how a record comes to look like a book it never was.
    """
    occ = str(row.get("occ_symbol") or "")
    if occ and occ in (paper_refused or set()):
        return EXIT_SOURCE_REFUSED
    if occ and occ in (paper_filled or set()):
        return EXIT_SOURCE_PAPER
    if row.get("exit_premium") is not None:
        return EXIT_SOURCE_SCORED
    return EXIT_SOURCE_UNKNOWN


def _pct(entry, now_) -> "float|None":
    try:
        e, n = float(entry), float(now_)
    except (TypeError, ValueError):
        return None
    if e <= 0:
        return None
    return 100.0 * (n - e) / e


def marked_to_market(rows) -> dict:
    """Every REAL trade marked to market, beside the closed-only figure.

    **WHY BOTH, AND WHY THE CLOSED-ONLY ONE IS THE PESSIMISTIC HALF:** losers close fast and
    winners stay open, so a closed-only mean is a sample selected on the outcome. Marking the
    open positions too is the only reading that covers the whole book -- and it is the one
    that moves, because an open mark is not a realised result. **Neither replaces the other
    and the tab shows both.**

    `no_contract` rows are excluded from both: they have nothing to mark (`options_paper`'s
    own rule, and the reason item 29(a) gave them a status of their own).
    """
    closed, openp, names = [], [], set()
    for r in rows or []:
        st = str(r.get("status") or "")
        if st == "NO CONTRACT - not scoreable":
            continue
        names.add(str(r.get("ticker") or ""))
        if st == "LIVE":
            p = _pct(r.get("entry_premium"), r.get("current_premium"))
            if p is not None:
                openp.append(p)
        else:
            v = r.get("pnl_pct_net")
            v = r.get("pnl_pct") if v is None else v
            if v is not None:
                closed.append(float(v))
    allp = closed + openp
    def _mean(xs):
        return (sum(xs) / len(xs)) if xs else None
    return {
        "n_trades": len(closed) + len(openp),
        "n_closed": len(closed), "n_open_marked": len(openp),
        "n_distinct_names": len(names - {""}),
        "closed_only_mean_pct": _mean(closed),
        "marked_to_market_mean_pct": _mean(allp),
        "open_only_mean_pct": _mean(openp),
        "why_both": ("losers close fast and winners stay open, so the closed-only mean is a "
                     "sample selected on the outcome; the marked figure covers the whole book "
                     "and moves because an open mark is not a realised result. Neither "
                     "replaces the other."),
    }


def concentration(rows) -> dict:
    """Distinct names beside the trade count, and the largest cluster. PURE.

    A trade count reads as breadth and is not: **ABBV is 6 of the 13 open trades and 4 of
    those are the same November $280 call**, so "13 open" is nearer four independent bets than
    thirteen. The tab shows the name count next to the trade count for exactly that reason.
    """
    real = [r for r in (rows or [])
            if str(r.get("status") or "") != "NO CONTRACT - not scoreable"]
    by_name, by_contract = {}, {}
    for r in real:
        by_name[str(r.get("ticker") or "")] = by_name.get(str(r.get("ticker") or ""), 0) + 1
        k = str(r.get("occ_symbol") or "")
        if k:
            by_contract[k] = by_contract.get(k, 0) + 1
    top_name = max(by_name.items(), key=lambda kv: kv[1]) if by_name else ("", 0)
    top_con = max(by_contract.items(), key=lambda kv: kv[1]) if by_contract else ("", 0)
    return {"n_trades": len(real), "n_distinct_names": len([k for k in by_name if k]),
            "largest_name": top_name[0], "largest_name_trades": top_name[1],
            "largest_contract": top_con[0], "largest_contract_trades": top_con[1],
            "note": ("a trade count reads as breadth and is not: the same name, and often the "
                     "same contract, repeats")}


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
        "n_no_contract": 0,
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

    # ITEM 29(a) -- THREE KINDS, NOT TWO, AND THE COMPLEMENT IS WHY THIS NEEDED TOUCHING.
    #
    # `n_live` keys on the DISPLAY status, so giving `no_contract` its own status fixes the live
    # count on its own: 23 -> 15, which is what `/api/options-scorecard` already read. But
    # `n_closed` was `len(recs) - len(live)`, i.e. "everything that is not live", and that
    # definition breaks the moment a third kind exists -- it would have reported the 8
    # no-contract rows as CLOSED, so the tab would read 18 closed trades where only 10 closed.
    # Fixing LIVE without fixing its complement moves the error rather than removing it.
    live = [r for r in recs if (r.get("status") or "") == SL.STATUS_LIVE]
    nocon = [r for r in recs if (r.get("status") or "") == SL.STATUS_NO_CONTRACT]
    # ITEM 66 PART 3 -- THE NO-CONTRACT ROWS GET THEIR OWN LIST, AND NOTHING IS DELETED.
    # They were never trades: no contract was resolved on the chain, so there is nothing to
    # mark and no date on which they could mature. Leaving them in the main table makes the
    # record look like a book of 35 when it is a book of 21.
    real = [r for r in recs if (r.get("status") or "") != SL.STATUS_NO_CONTRACT]
    out["rows"] = real
    out["no_contract_rows"] = nocon
    out["n_rows"] = len(recs)
    out["n_real_rows"] = len(real)
    out["n_live"] = len(live)
    out["n_no_contract"] = len(nocon)
    out["n_closed"] = len(recs) - len(live) - len(nocon)

    # The paper book is a DIFFERENT object from this record (the conflation this module was
    # rewritten to undo), and it is the only thing that can say whether a given alert was
    # actually bought. Read defensively: an unavailable paper book must leave the label
    # UNKNOWN rather than silently making every scored exit look like an execution.
    filled, refused = set(), set()
    try:
        from ..edge import paper_track as _PT
        for o in (_PT.options_summary(store).get("orders") or []):
            occ = str(o.get("occ") or o.get("occ_symbol") or "")
            if not occ:
                continue
            (filled if o.get("fill_price") is not None else refused).add(occ)
    except Exception:                                                # noqa: BLE001
        filled, refused = set(), set()
    for r in real:
        r["exit_source"] = (exit_source(r, filled, refused)
                            if (r.get("status") or "") != SL.STATUS_LIVE else "")
    out["exit_sources"] = {k: sum(1 for r in real if r.get("exit_source") == k)
                           for k in (EXIT_SOURCE_PAPER, EXIT_SOURCE_SCORED,
                                     EXIT_SOURCE_REFUSED, EXIT_SOURCE_UNKNOWN)}
    out["marked_to_market"] = marked_to_market(recs)
    out["concentration"] = concentration(recs)
    out["stop_cadence_note"] = STOP_CADENCE_NOTE
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
