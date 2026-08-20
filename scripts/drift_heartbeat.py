#!/usr/bin/env python3
"""
drift_heartbeat.py - MB28. Give the staleness monitor a clock.

    python scripts/drift_heartbeat.py            # measure, write the heartbeat, exit
    python scripts/drift_heartbeat.py --out X    # write somewhere else (tests)
    python scripts/drift_heartbeat.py --print    # also print the JSON

WHAT MB28 ACTUALLY ASKED FOR, AND A CORRECTION TO IT
-----------------------------------------------------
MB28: *"`scripts/checkout_drift.py` is built, documented and tested. Measured: nothing
invokes it on a schedule ... the alarm for 'the relay dropped a packet' is itself gated
on a human remembering."*

**The first half is true and the framing is out of date.** Measured 2026-08-19:

  * the ALARM has no clock -- confirmed, no scheduled task and no workflow calls it;
  * the CURE does. `ValquoSyncCheckout` is registered, daily at 19:30, last run
    2026-08-18 19:30:01 with LastTaskResult 0, and its log holds 19 runs;
  * and it is working. The shared checkout reads **0 ahead / 19 behind**, against the
    **1 ahead / 514 behind** that motivated MA20, with the stranded PT-WRITER commit
    long since rescued.

So the alarm's job is no longer "tell Don he has drifted" -- the nightly sync handles
that, unattended. Its job is the one nothing covers: **tell the next session whether the
nightly sync is still running at all.** If that task is deleted, or the machine is off
for a week, `sync.log` simply stops growing and no surface anywhere says so. That is the
mandate's own thesis, one layer further in.

WHY A HEARTBEAT AND NOT A SECOND ALARM
---------------------------------------
A heartbeat is a file whose **mtime is the measurement**. `board_state.py` reports its
age, so a dead clock shows up as "72h old" in the report every session already reads,
instead of as silence.

**It could not be piggy-backed onto the sync task, and that is the whole point.** Adding
the heartbeat write to `valquo_sync_bootstrap.bat` would make it die exactly when the
sync task dies -- the failure it exists to detect. It needs its own task, and it is
scheduled at 20:30, after the 19:30 sync and the 20:00 auto-push, so it measures the
state the day's automation actually left behind.

**The regress is real and is bounded, not solved.** If `ValquoDriftCheck` is itself
deleted, its heartbeat freezes silently too. What stops that being invisible is that the
age is *reported to a reader* rather than watched by another watcher: `board_state.py`
prints "NOT INSTALLED" or "72h old" every time anybody runs it. There is no chain of
watchers that terminates; there is only the point at which a human sees a number.

IT ALWAYS WRITES, EVEN WHEN IT CANNOT MEASURE
----------------------------------------------
A run that fails to measure still writes a heartbeat recording `"unknown"`. Skipping the
write would make "the drift could not be measured" and "the task is not installed"
produce the identical observable -- a missing or frozen file -- and `checkout_drift`'s
own header exists because "I could not tell" and "all clear" once shared an exit code.
The exit code is passed through unchanged so Task Scheduler's LastTaskResult keeps
meaning what the alarm means.

ONE MEASURE, NOT TWO
--------------------
The drift itself is `checkout_drift.measure`/`verdict`, imported. A second implementation
of "how far behind is the checkout" is the defect MA5 and MA39 each closed once.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.checkout_drift import (  # noqa: E402
    DEFAULT_MAX_BEHIND, DriftUnknown, SHARED_CHECKOUT, measure, verdict,
)

# Outside the repo, for valquo_sync_bootstrap.bat's reason: the heartbeat must keep
# working while the checkout it measures is stale. board_state.HEARTBEAT reads this
# same path -- if you move one, move both; they are one fact.
DEFAULT_OUT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Valquo" / "drift.json"

OK = 0
ALARM = 1


def beat(repo: str = SHARED_CHECKOUT, max_behind: int = DEFAULT_MAX_BEHIND,
         no_fetch: bool = False, now: float | None = None) -> tuple[dict, int]:
    """Measure once. Returns (heartbeat, exit code). Never raises on a git failure."""
    now = time.time() if now is None else now
    hb = {
        "ran_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "ran_at_epoch": int(now),
        "source": "scripts/drift_heartbeat.py (MB28)",
        "measured": None,
        "state": "unknown",
    }
    try:
        v = verdict(measure(repo=repo, fetch=not no_fetch), max_behind=max_behind)
    except (DriftUnknown, Exception) as e:      # noqa: B014 - unknown is a state, not a crash
        hb["error"] = str(e)[:300]
        return hb, ALARM
    hb["measured"] = v
    hb["state"] = "alarm" if v["alarm"] else "ok"
    return hb, (ALARM if v["alarm"] else OK)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write the checkout-drift heartbeat.")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--repo", default=SHARED_CHECKOUT)
    ap.add_argument("--max-behind", type=int, default=DEFAULT_MAX_BEHIND)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args(argv)

    hb, rc = beat(repo=a.repo, max_behind=a.max_behind, no_fetch=a.no_fetch)

    out = Path(a.out)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(hb, indent=1) + "\n", encoding="utf-8")
    except Exception as e:
        # A heartbeat that cannot be written is worse than an alarm: nothing downstream
        # can tell it from "never installed". Say so on stderr and fail.
        print(f"[ALARM] could not write the heartbeat to {out}: {e}", file=sys.stderr)
        return ALARM

    if a.show:
        print(json.dumps(hb, indent=1))
    else:
        print(f"heartbeat {hb['state']} -> {out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
