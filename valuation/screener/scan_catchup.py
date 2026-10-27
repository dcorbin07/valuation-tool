# -*- coding: utf-8 -*-
"""ITEM 84 PART B — RUN THE HOT SCAN WHEN A CRON SLOT WAS DROPPED, NOT WHEN A STRING MATCHES.

**THE DEFECT, MEASURED.** On 2026-10-26 GitHub delivered NEITHER hot-list cron slot — not the
22:23 UTC primary and not the 23:41 backup — so the public hot list still showed the 2026-10-23
scan a full day later, and the daily LIVE CHECK failed on `hot list is fresh`. The `hot` job is
gated on `github.event.schedule` matching one of those two exact strings, so a dropped slot is
an unrun job with nothing to notice it.

That is not an unlucky night. `auto-scan.yml`'s own comments already quantify it: *"of the 176
cron slots these eight produce, 49 delivered a run and 127 did not"* — a delivery rate near one
in four. **A backup cron does not fix this**, because it is the same mechanism failing the same
way; 10-26 lost both slots to it.

**THE FIX IS TO STOP ASKING "WHICH CRON AM I?" AND START ASKING "IS THE HOT LIST BEHIND?"** Any
job that DOES fire can check, and the intraday crons demonstrably fire — three of them delivered
within forty minutes on the very night both hot slots were dropped (23:57, 00:05 and 00:08 UTC).
So the catch-up rides on whatever did arrive, instead of on what should have.

**WHAT MAKES IT SAFE, AND IT IS THE WHOLE OF THE DESIGN:**

  * **IDEMPOTENT PER SESSION.** It runs only when the published `scan_date` is strictly OLDER
    than the last closed session. A scan that already happened is not repeated however many
    later jobs fire, so ten delivered crons produce at most one scan.
  * **CLOSES, NEVER INTRADAY.** It refuses while the market is open, because the free price feed
    answers an open-market request with a LIVE quote — which would be published as that
    session's "close" and be wrong by however much the afternoon moved. This is the one
    condition that cannot be relaxed for convenience.
  * **IT NEVER MARKS FORWARD.** The target is always `last_closed_session`, the same function
    the track writer uses for the same reason: a job delayed past midnight must still record
    the session it was scheduled for, not the day it woke up in.

**IT IS A DECISION FUNCTION AND IT TOUCHES NOTHING.** No network, no clock of its own beyond the
`now` it is handed, no scan. The workflow asks it and acts; everything here is testable without
GitHub, which is the point — the logic that decides whether to publish a hot list should not live
in YAML where nothing can reach it.
"""
from __future__ import annotations

import datetime as _dt
import sys
from typing import Optional

from . import market_session as MS


def _d(x) -> Optional[_dt.date]:
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    if not x:
        return None
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def market_is_open(now: Optional[_dt.datetime] = None) -> bool:
    """Is a session currently trading? Open-inclusive, close-exclusive of the settle cutoff.

    Deliberately WIDER than `orders_window`, which trims the first five minutes and the last
    fifteen because an order needs a quote it can trust. This asks a different question — "would
    a price request right now come back with an intraday quote?" — and the answer is yes from
    the bell, so the five-minute grace does not apply.
    """
    n = now or MS.now_et()
    d = n.date()
    if d.weekday() >= 5 or d in MS.market_holidays(d.year):
        return False
    start = _dt.time(MS.OPEN_HOUR, MS.OPEN_MINUTE)
    end = _dt.time(MS.CLOSE_HOUR, MS.SETTLE_MINUTES)
    return start <= n.time() < end


def catchup_decision(scan_date, now: Optional[_dt.datetime] = None) -> dict:
    """Should a hot scan run now? -> `{run, reason, target, published, market_open}`.

    `scan_date` is what the PUBLIC feed says it last scanned — passed in rather than fetched,
    so this is a pure function and the workflow owns the one network call.

    A missing or unreadable `scan_date` RUNS, deliberately: "the feed does not say when it last
    scanned" is not evidence that it is current, and the cost of an extra scan is one run while
    the cost of skipping is another day of a stale public page (`C5`, and `MA6`'s direction).
    """
    if now is None:
        n = MS.now_et()
        # **NO TIMEZONE, NO CATCH-UP.** `now_et` falls back to NAIVE UTC when tzdata is
        # missing, and a naive UTC clock compared against ET market hours is wrong by four
        # or five hours -- which would let a catch-up fire at 14:00 UTC, in the middle of the
        # session, and publish live quotes as the previous close. Refusing costs one stale
        # day; the other direction publishes a wrong hot list. A caller that passes its own
        # `now` is a test and is trusted, which is what keeps this function testable.
        if n.tzinfo is None:
            return {"run": False, "target": None, "published": None, "market_open": None,
                    "reason": ("the ET timezone is unavailable on this machine (no tzdata), "
                               "so whether the market is open cannot be established -- "
                               "refusing rather than risking an intraday scan")}
    else:
        n = now
    target = MS.last_closed_session(n)
    published = _d(scan_date)
    open_now = market_is_open(n)
    out = {"run": False, "reason": "", "target": target.isoformat() if target else None,
           "published": published.isoformat() if published else None,
           "market_open": open_now, "at": n.isoformat(timespec="seconds")}

    if target is None:
        out["reason"] = ("no closed session could be found within a fortnight, which no real "
                         "calendar produces -- refusing rather than guessing a target")
        return out

    # THE OPEN-MARKET REFUSAL COMES FIRST, because it holds whatever the dates say. A scan
    # during the session would publish live quotes under the previous close's date.
    if open_now:
        out["reason"] = ("the market is open (%s ET), so a scan now would price names at "
                         "INTRADAY quotes and publish them as %s's closes"
                         % (n.strftime("%H:%M"), target.isoformat()))
        return out

    if published is None:
        out["run"] = True
        out["reason"] = ("the feed reports no readable scan date, which is not evidence that it "
                         "is current -- scanning %s's closes" % target.isoformat())
        return out

    if published >= target:
        out["reason"] = ("the hot list is already at %s, which is the last closed session%s -- "
                         "nothing to catch up"
                         % (published.isoformat(),
                            " (it is ahead)" if published > target else ""))
        return out

    behind = MS.trading_days_between(published, target, inclusive_start=False)
    out["run"] = True
    out["reason"] = ("the hot list is at %s and the last closed session is %s, %d trading "
                     "day(s) behind -- scanning %s's closes"
                     % (published.isoformat(), target.isoformat(), behind, target.isoformat()))
    out["behind_trading_days"] = behind
    return out


def main(argv=None) -> int:
    """`python -m valuation.screener.scan_catchup --scan-date YYYY-MM-DD`.

    Prints the reason and exits **0 to run, 1 to skip**, so a workflow step can branch on the
    exit code without parsing anything. A skip is a normal outcome and not a failure, which is
    why the message says so in words: a step that exits 1 and prints nothing teaches its reader
    that red means broken.
    """
    import argparse
    ap = argparse.ArgumentParser(description="Decide whether to run a catch-up hot scan.")
    ap.add_argument("--scan-date", default="", help="what the public feed last scanned")
    # **THE FEED'S JSON ON STDIN, so the workflow needs ONE line and no embedded Python.**
    # The first cut put a multi-line `python -c` inside a YAML block scalar; its lines
    # de-indented to column 0 and broke the document. Parsing belongs in a tested module and
    # the network stays in `curl`.
    ap.add_argument("--json-stdin", action="store_true",
                    help="read the feed payload on stdin and take its scan_date")
    ap.add_argument("--now", default="", help="ET timestamp to judge against (tests)")
    a = ap.parse_args(argv)
    now = None
    if a.now:
        try:
            now = _dt.datetime.fromisoformat(a.now)
        except ValueError:
            print("--now %r is not an ISO timestamp" % a.now)
            return 2
    sd = a.scan_date or None
    if a.json_stdin:
        import json
        try:
            sd = (json.load(sys.stdin) or {}).get("scan_date") or None
        except Exception:                                            # noqa: BLE001
            # AN UNREADABLE REPLY IS NOT A CURRENT ONE. `catchup_decision` treats None as
            # "not known to be current" and scans -- and still cannot scan while the market
            # is open, which is what makes failing this way safe.
            sd = None
    got = catchup_decision(sd, now=now)
    print("%s: %s" % ("RUN" if got["run"] else "SKIP", got["reason"]))
    return 0 if got["run"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
