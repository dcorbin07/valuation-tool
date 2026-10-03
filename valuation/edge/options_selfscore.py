# -*- coding: utf-8 -*-
"""ITEM 24 — the alert record scores itself, instead of waiting for a broker that never buys.

THE DEFECT, MEASURED ON THE LIVE SERVICE 2026-10-03
---------------------------------------------------
26 open alerts, 7 closed, and the open ones could not close for two separate reasons.

**EIGHT HAVE NO CONTRACT AT ALL.** Alert ids 9, 10, 12, 13, 16, 18, 24, 25 (JNJ, MET, JNJ,
DELL, ELV, ELV, ETN, KMI) carry `contract_source: "descriptor (no chain)"` and no expiry, so
there is nothing to mark, nothing to settle, and no date on which they could ever mature. They
sat in "26 open" forever, inflating the open count with rows that are not trades.

**AND OF THE 18 WITH A CONTRACT, ONLY THE ONES THE PAPER BROKER BOUGHT WERE EVER SCORED.** The
scream log is closed exclusively from `paper_track` via `options_tracker.record_outcome`, and
`options_tracker`'s own module docstring says why: *"an external scheduled process (Cowork)
writes `exit_*` back"*. That process no longer exists. So an alert the broker declined is an
alert that can never be scored, whatever the contract does.

The two live examples are the point:

* **ELV alert 14** — 420C expiring 2026-11-20, entry 27.80, last 7.00, **-75%**
* **HCA alert 7** — 430C expiring 2026-10-16, entry 22.40, last 8.60, **-62%**

both well past their own pre-registered **-50% stop**, neither held by the broker, neither
scored. The likeliest reason they were not held is the $1,000 sizing veto — one contract costs
$2,780 and $2,240 — which is a decision about THIS ACCOUNT'S SIZE and has nothing to do with
whether the alert was any good.

**SO THE CENSORING IS ONE-SIDED, WHICH IS MA36 ONE LAYER UP.** MA36 found a stranded expiry
being dropped from the paper book: *"winners and quoted losers are scored and the -100% tail is
dropped, which is the opposite of the backtest this book exists to validate."* The same shape
here, with the filter being affordability rather than expiry — and affordability correlates with
PREMIUM, so the trades excluded are systematically the expensive ones. Nothing about that is
random.

WHAT THIS MODULE DOES, AND WHAT IT DELIBERATELY DOES NOT
--------------------------------------------------------
It scores the **ALERT** against **its own logged exit policy** on daily marks, independent of
any broker: stop, target, time stop, expiry, bid-side marks, exactly the convention every
validated options figure in this repo is net of. It reuses, rather than reimplements:

* `options_tracker.exit_decision` — the ONE exit rule, which `paper_track._exit_decision` now
  delegates to as well (proved bit-identical over 113,400 cases, signature contract included);
* `paper_track._exit_policy` — the alert's OWN logged policy, defaults only where the row
  predates it;
* `options_tracker.record_outcome` — all the P&L arithmetic, including MA46's decision to
  record gross and net separately and MA36's rule that a worthless expiry reads exactly -100%.

**THE PAPER BOOK REMAINS A SEPARATE OBJECT AND IS NOT TOUCHED.** It answers a different
question — what a $1,000-budget account actually got, fills and sizing included — and merging
the two would destroy the one measurement this project has of real execution. Two books, two
questions; this module writes only to `option_alerts`.

**IT PRICES NOTHING ITSELF.** The quote source is injected, so the scoring logic is testable
with fixtures and the live caller supplies the same provider the rest of the lane uses. A
missing bid DEFERS on a live contract (audit B5-lesser: no two-sided market, no defensible exit
price) and SETTLES AT ZERO past expiry (MA36: there is no next run that will find a bid, and
zero is what the market quotes by declining to bid). The settlement price is never
reconstructed from today's underlying — that is V6-OPT's trap, and its error runs in the
flattering direction.
"""
from __future__ import annotations

import datetime as _dt
from typing import Callable, Optional

from . import options_tracker as OT
from . import paper_track as PT

#: The status a no-contract alert gets. NOT `closed`: nothing was ever entered, so it is not a
#: trade with an outcome of zero -- it is a row that was never scoreable, and calling it closed
#: would put it in the denominator of a hit rate it cannot belong to.
NO_CONTRACT = "no_contract"

#: Why, in the record, so a reader does not have to infer it from an absent expiry.
NO_CONTRACT_REASON = ("no contract - not scoreable: the alert was logged from a descriptor "
                      "with no chain, so it has no strike/expiry to mark, no exit to apply "
                      "and no date on which it could mature")


def _f(x):
    return PT._f(x)


def is_scoreable(alert: dict) -> bool:
    """Does this alert name a contract that can be marked and settled?

    BOTH an expiry and an OCC symbol are required, and that is not belt-and-braces. The expiry
    is what makes the time stop and the settlement decidable; the OCC symbol is what a quote is
    fetched by. An alert with one and not the other cannot be scored either, and saying so here
    is what stops it sitting in "open" forever.
    """
    return bool(str(alert.get("occ_symbol") or "").strip()
                and str(alert.get("expiry") or "").strip())


def levels(alert: dict) -> dict:
    """The alert's own target, stop and time-stop date, from the policy IT logged.

    `PT._exit_policy` is the shipped reader and takes an ALERT row -- which is the fresh path,
    the one session 16 found was correct while the resume path was silently reading an order row
    and collapsing to the defaults. Reusing it is the whole point: a second derivation of
    "what were this alert's exit levels" is how a scorer and a broker come to disagree about the
    same trade.
    """
    pol = PT._exit_policy(alert)
    entry = _f(alert.get("entry_premium"))
    out = {"target_pct": pol["target_pct"], "stop_pct": pol["stop_pct"],
           "time_stop_frac": pol["time_stop_frac"],
           "target_premium": None, "stop_premium": None, "time_stop_date": None,
           "entry_premium": entry}
    if entry is not None and entry > 0:
        out["target_premium"] = entry * (1.0 + pol["target_pct"])
        out["stop_premium"] = entry * (1.0 + pol["stop_pct"])
    # THE TIME STOP IS ANCHORED ON THE ALERT'S OWN TIMESTAMP AND ITS OWN DTE, because that is
    # what the policy means: half the ORIGINAL tenor. Computing it from today's date-to-expiry
    # would re-arm the clock on every run and the stop would never fire.
    start = PT._d(str(alert.get("alert_ts") or "")[:10])
    dte = _f(alert.get("dte"))
    if start is not None and dte is not None and dte > 0:
        out["time_stop_date"] = (start + _dt.timedelta(
            days=int(round(float(dte) * pol["time_stop_frac"])))).isoformat()
    return out


def as_order_row(alert: dict, mark=None) -> dict:
    """The alert in the ORDER-ROW vocabulary `exit_decision` speaks.

    A translation, not a second rule. Keeping the rule's vocabulary fixed and translating into
    it means the alert path and the broker path cannot drift on what "the stop fired" means.
    """
    lv = levels(alert)
    return {"last_mark": mark,
            "target_premium": lv["target_premium"],
            "stop_premium": lv["stop_premium"],
            "expiry": alert.get("expiry"),
            "time_stop_date": lv["time_stop_date"]}


def decide(alert: dict, mark, today: _dt.date) -> Optional[str]:
    """Which of the alert's own rules fires, or None. Delegates to the one shared rule."""
    return OT.exit_decision(mark, *[as_order_row(alert, mark)[k] for k in
                                    ("target_premium", "stop_premium", "expiry",
                                     "time_stop_date")], today)


def score_open_alerts(store, quotes: Callable[[list], dict], *,
                      today=None, limit: int = 500, apply: bool = True) -> dict:
    """Score every open alert against its OWN exit rules. The one entry point.

    `quotes(occ_symbols) -> {occ: {"bid": .., "ask": ..}}` is injected. `apply=False` reports
    what WOULD happen and writes nothing, which is how this is exercised against the live
    record before it is allowed to restate a published figure.

    **MA36's ARCHIVE DISCIPLINE APPLIES AND IS NOT OPTIONAL HERE.** Settling the censored tail
    RESTATES the published expectancy, and a restatement that keeps no record of the figure it
    replaced is indistinguishable from the figure having always been that. So the scorecard is
    snapshotted before and after and both travel in the result -- and only when there is
    something to settle, so a quiet run writes nothing.
    """
    day = PT._d(today) or PT._session_today()
    out = {"ok": True, "scored": 0, "closed": 0, "no_contract": 0, "deferred_no_bid": 0,
           "settled_expired": 0, "unchanged": 0, "errors": [], "exits": [],
           "applied": bool(apply), "day": day.isoformat(),
           "expectancy_before": None, "expectancy_after": None}

    try:
        alerts = OT.open_alerts(store, limit=limit)
    except Exception as e:                                           # noqa: BLE001
        out["ok"] = False
        out["errors"].append("open_alerts: %s" % type(e).__name__)
        return out

    scoreable = [a for a in alerts if is_scoreable(a)]
    unscoreable = [a for a in alerts if not is_scoreable(a)]

    # ---------------------------------------------------------------- the rows that are not trades
    for a in unscoreable:
        out["no_contract"] += 1
        out["exits"].append({"alert_id": a.get("id"), "ticker": a.get("ticker"),
                             "status": NO_CONTRACT, "reason": NO_CONTRACT_REASON,
                             "contract_source": (a.get("contract_source")
                                                 or _source_of(a))})
        if apply:
            try:
                _mark_no_contract(store, a.get("id"))
            except Exception as e:                                   # noqa: BLE001
                out["errors"].append("%s: %s" % (a.get("ticker"), type(e).__name__))

    if not scoreable:
        return out

    # ---------------------------------------------------------------- marks, in ONE call
    occs = [a["occ_symbol"] for a in scoreable if a.get("occ_symbol")]
    try:
        qs = quotes(occs) or {}
    except Exception as e:                                           # noqa: BLE001
        out["ok"] = False
        out["errors"].append("quotes: %s" % type(e).__name__)
        return out

    pre = None
    for a in scoreable:
        out["scored"] += 1
        occ = a.get("occ_symbol")
        bid = _f((qs.get(occ) or {}).get("bid"))
        reason = decide(a, bid, day)
        exp = PT._d(a.get("expiry"))
        past_expiry = exp is not None and day > exp

        if not (bid and bid > 0):
            # B5-lesser for a LIVE contract; MA36 for a DEAD one. The two are opposite and the
            # distinction is STRICTLY `day > expiry` -- inside CLOSE_BEFORE_EXPIRY_DAYS the
            # contract is still alive and a missing bid is a thin market, not a settlement.
            if past_expiry:
                if pre is None and apply:
                    pre = _expectancy(store)
                ok = _close(store, a, 0.0, "expiry (settled at zero; no bid past expiry)",
                            day, apply)
                if ok:
                    out["settled_expired"] += 1
                    out["closed"] += 1
                    out["exits"].append({"alert_id": a.get("id"), "ticker": a.get("ticker"),
                                         "reason": "expiry_settled_zero", "exit_premium": 0.0})
                else:
                    out["errors"].append("%s: settle refused" % a.get("ticker"))
            else:
                out["deferred_no_bid"] += 1
            continue

        if not reason:
            out["unchanged"] += 1
            continue

        if pre is None and apply:
            pre = _expectancy(store)
        if _close(store, a, bid, reason, day, apply):
            out["closed"] += 1
            out["exits"].append({"alert_id": a.get("id"), "ticker": a.get("ticker"),
                                 "reason": reason, "exit_premium": bid,
                                 "entry_premium": _f(a.get("entry_premium"))})
        else:
            out["errors"].append("%s: close refused" % a.get("ticker"))

    if pre is not None:
        out["expectancy_before"] = pre
        out["expectancy_after"] = _expectancy(store)
    return out


def _source_of(alert: dict) -> str:
    try:
        return str((PT._features(alert).get("contract") or {}).get("source") or "")
    except Exception:                                                # noqa: BLE001
        return ""


def _mark_no_contract(store, alert_id) -> bool:
    if alert_id is None:
        return False
    OT.ensure_pnl_schema(store)
    with store._conn() as c:
        cur = c.execute("UPDATE option_alerts SET status=?, exit_reason=? "
                        "WHERE id=? AND status='open'",
                        (NO_CONTRACT, NO_CONTRACT_REASON, alert_id))
        return bool(cur.rowcount)


def _close(store, alert: dict, exit_premium: float, reason: str,
           day: _dt.date, apply: bool) -> bool:
    if not apply:
        return True
    return bool(OT.record_outcome(store, alert_id=alert.get("id"),
                                  exit_premium=exit_premium,
                                  exit_ts=day.isoformat(),
                                  exit_reason="%s [self-scored]" % reason))


def _expectancy(store):
    """The published figure, snapshotted. Only the fields a restatement changes."""
    try:
        o = (OT.scorecard(store) or {}).get("overall") or {}
    except Exception:                                                # noqa: BLE001
        return None
    return {k: o.get(k) for k in ("n_closed", "hit_rate", "expectancy_pct",
                                  "expectancy_pct_net", "cum_pnl_dollars", "profit_factor")}
