#!/usr/bin/env python3
"""
Watchdog — is the live site still being fed?

On 2026-07-29 the scheduled scan stopped running. Nothing errored anywhere a human would
see it: the site kept serving the last snapshot, the pages looked normal, and the data was
five days old before anyone noticed. This script is the thing that would have caught it.

It runs SEPARATELY from the scan on purpose. A check bolted onto the end of the scan job
cannot fire when the scan job is the thing that died — which is precisely the failure being
guarded against. This hits the public API from outside and judges what a real visitor would
actually receive.

Exit code 1 when something is stale, so the Action goes red as well as pinging Discord.

Environment:
  BASE_URL             https://your-site.onrender.com   (required)
  DISCORD_WEBHOOK_URL  optional; without it this still fails loudly in CI
  MAX_TRADING_DAYS     staleness threshold for the hot list (default 3)
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.screener.freshness import trading_days_between  # noqa: E402

TIMEOUT = 45


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "valquo-watchdog"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def _post_discord(text: str) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("  (no DISCORD_WEBHOOK_URL — alert not sent)")
        return
    body = json.dumps({"content": text[:1900]}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            print(f"  discord: {r.status}")
    except Exception as e:
        print(f"  discord FAILED: {e}")


def main() -> int:
    base = os.environ.get("BASE_URL", "").rstrip("/")
    if not base:
        print("BASE_URL not set")
        return 2
    limit = int(os.environ.get("MAX_TRADING_DAYS", "3"))
    today = _dt.date.today()
    problems = []

    # The hot list is the one that feeds everything else — the Index is a slice of it.
    try:
        d = _get(f"{base}/api/hotstocks?top=1")
    except Exception as e:
        problems.append(f"`/api/hotstocks` is not responding: {e}")
        d = None

    if d is not None:
        if d.get("empty"):
            problems.append("the site has NO scan snapshot at all")
        else:
            scan_date = d.get("scan_date")
            try:
                sd = _dt.date.fromisoformat(str(scan_date)[:10])
                age = trading_days_between(sd, today)
                scored = d.get("scored")
                print(f"  hot list: {scan_date} ({age} trading days old), {scored} scored")
                if age >= limit:
                    problems.append(
                        f"the hot list is **{age} trading days old** (from {scan_date}). "
                        f"The scheduled scan has not landed.")
                # A scan that runs but collapses is its own failure — 154 names instead of
                # ~800 is what a dead data subscription looks like from the outside.
                if isinstance(scored, int) and scored < 300:
                    problems.append(
                        f"the last scan only scored **{scored}** names — the universe has "
                        f"collapsed (expected several hundred).")
            except (TypeError, ValueError):
                problems.append(f"the hot list has an unreadable scan_date: {scan_date!r}")

    # The forward paper track. Its whole value is being an unbroken daily record, so a run
    # that silently stops is worse here than anywhere else on the site — a gap cannot be
    # backfilled honestly once the prices have moved on.
    #
    # Deliberately only complains ONCE THE TRACK HAS STARTED. Before the first point,
    # `available: false` is the correct state (the cron is scheduled but the book has not been
    # seeded yet), and alerting on it would train the reader to ignore this channel — which is
    # how the July outage went unnoticed for four days.
    try:
        t = _get(f"{base}/api/index-track")
        if not t.get("available"):
            print("  paper track: not started yet (no live points) — not an alert")
        else:
            last = ((t.get("series") or [{}])[-1] or {}).get("date") or t.get("as_of")
            try:
                ld = _dt.date.fromisoformat(str(last)[:10])
                age = trading_days_between(ld, today)
                print(f"  paper track: {t.get('days')} points, last {last} "
                      f"({age} trading days old)")
                if age >= limit:
                    problems.append(
                        f"the forward paper track has not recorded a point in **{age} trading "
                        f"days** (last {last}). The daily cycle is not running.")
            except (TypeError, ValueError):
                problems.append(f"the paper track has an unreadable date: {last!r}")
    except Exception as e:
        print(f"  paper track: /api/index-track not responding ({e}) — not an alert")

    if not problems:
        print("OK — the live site is being fed.")
        return 0

    msg = ("🔴 **Valquo data pipeline problem**\n"
           + "\n".join(f"• {p}" for p in problems)
           + f"\n\n{base}/app — checked {today.isoformat()}")
    print(msg)
    _post_discord(msg)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
