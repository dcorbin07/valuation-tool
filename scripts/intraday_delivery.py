# -*- coding: utf-8 -*-
"""ITEM 44 - how many intraday cron slots actually produce a run, re-measurable on demand.

Item 37 measured 72.2% of slots dropped over the 30 days to 2026-10-07, when the schedule
carried eight intraday crons. A BACKUP CRON (`53 17-19 * * 1-5`) was installed on 2026-10-08 at
08:15 ET (`d66155e`), so the denominator changed and the question has to be re-asked.

WHY THE JOB AND NOT THE CLOCK -- item 37's reasoning, kept because it is the load-bearing part.
GitHub's API does not say which cron fired, so attributing a run to a schedule by its
`created_at` minute would assume the scheduler is punctual, which is the thing being measured.
It would be circular, and a late run would be scored as a different cron or as none. The JOBS
are the attribution and they are exact: every job in this workflow is gated on
`github.event.schedule`, so a run whose `intraday` job EXECUTED (rather than skipped) was fired
by an intraday cron, whenever it happened to arrive.

**WHAT THIS CANNOT DO, STATED RATHER THAN GLOSSED: it cannot tell the primary cron from the
backup.** Both gate the SAME `intraday` job, and the API does not expose the schedule, so a
delivered run is attributable to "an intraday cron" and no further. That is enough for the three
numbers the question asks for -- slots expected, runs delivered, sessions with zero in-session
runs -- and it is NOT enough to say "the backup rescued N sessions". Anyone wanting that needs
the job to record which schedule fired it, which is a `.github/` change.

THE DENOMINATOR IS DERIVED FROM THE AUTHORITATIVE WORKFLOW, NOT TYPED. Item 42 hard-reasoned
from its own worktree's copy and reported a cron absent that had been installed hours earlier;
`workflow_source` reads `origin/main`. A cron expression like `23 13-20 * * 1-5` is expanded to
its eight slots a weekday rather than counted as one.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import workflow_source as WS                                  # noqa: E402

REPO_SLUG = "dcorbin07/valuation-tool"
WORKFLOW = "auto-scan.yml"
JOB = "intraday"

#: The band the intraday feed exists to cover: 13:00-20:00 UTC is roughly 9am-4pm ET.
IN_SESSION_FROM = 13
IN_SESSION_TO = 20


def _gh(path: str, jq: str | None = None) -> str:
    cmd = ["gh", "api", "--paginate", path]
    if jq:
        cmd += ["--jq", jq]
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    return (r.stdout or b"").decode("utf-8", "replace")


def intraday_crons(text: str) -> list:
    """The crons whose gate names the `intraday` job -- read, not assumed.

    Taking "the intraday crons" from a hard-coded list is how item 42 went wrong. These come
    from the workflow itself: the job's `if:` names its schedules, and only those crons can
    make it run.
    """
    body = WS.strip_comments(text)
    m = re.search(r"^  %s:\s*$" % JOB, body, re.M)
    if not m:
        return []
    rest = body[m.end():]
    nxt = re.search(r"^  [A-Za-z0-9_-]+:\s*$", rest, re.M)
    block = rest[:nxt.start()] if nxt else rest
    return re.findall(r"github\.event\.schedule\s*==\s*'([^']+)'", block)


def slots_per_weekday(cron: str) -> int:
    """How many times a weekday cron fires in one weekday. `23 13-20 * * 1-5` is EIGHT."""
    parts = cron.split()
    if len(parts) != 5:
        return 0
    hour = parts[1]
    n = 0
    for piece in hour.split(","):
        if "-" in piece:
            a, b = piece.split("-", 1)
            step = 1
            if "/" in b:
                b, s = b.split("/", 1)
                step = int(s)
            n += len(range(int(a), int(b) + 1, step))
        elif piece == "*":
            n += 24
        else:
            n += 1
    return n


def _commit_before(when: dt.date, ref: str) -> str | None:
    """The last commit touching the workflow at or before the END of `when`."""
    out = WS._git("rev-list", "-1", "--before=%sT23:59:59" % when.isoformat(), ref,
                  "--", "%s/%s" % (WS.WORKFLOW_DIR.replace(os.sep, "/"), WORKFLOW))
    return (out or "").strip() or None


def crons_on(when: dt.date, ref: str = "origin/main", _cache={}) -> list:
    """The intraday crons as the workflow stood ON `when`.

    THE DENOMINATOR HAS TO MOVE WITH THE SCHEDULE, and the first cut of this script got it
    wrong in a way worth recording: it read today's cron list and applied 11 slots to every
    session in the window, including 2026-10-06 and -07, when the backup cron did not exist and
    the real figure was 8. **That is item 42's defect in the TIME dimension -- reading one
    copy of a file and believing it describes a different moment** -- so the fix is the same
    one: read the copy that was in force, per date.
    """
    key = (when.isoformat(), ref)
    if key in _cache:
        return _cache[key]
    sha = _commit_before(when, ref)
    text = None
    if sha:
        text = WS._git("show", "%s:%s/%s" % (sha, WS.WORKFLOW_DIR.replace(os.sep, "/"),
                                             WORKFLOW))
    if not text:
        text = WS.read(WORKFLOW, ref)["text"] or ""
    _cache[key] = intraday_crons(text)
    return _cache[key]


def expected_slots(sessions: list, ref: str = "origin/main") -> dict:
    """`{session date: slots that date's schedule really had}`.

    EXTRACTED SO IT CAN BE TESTED, and that was found by mutation rather than by reading:
    replacing this computation with `today's slot count x session count` left a test that
    exercised `crons_on` directly passing green, because nothing asserted that `measure`
    actually USED the per-date figure. It needs no network -- only git -- so a test can drive
    it on the real install boundary.
    """
    return {d: sum(slots_per_weekday(c) for c in crons_on(d, ref)) for d in sessions}


def measure(since: dt.date, until: dt.date, ref: str = "origin/main") -> dict:
    wf = WS.read(WORKFLOW, ref)
    if not wf["text"]:
        raise SystemExit("could not read %s: %s" % (WORKFLOW, wf["reason"]))
    crons = intraday_crons(wf["text"])
    per_day = sum(slots_per_weekday(c) for c in crons)

    # Sessions come from the project's own market calendar, so a holiday is not scored as a
    # missed day -- item 37's rule. `is_trading_day` is the only authority on which days those
    # are (it knows the holidays), and counting weekdays by hand here would be a second, wrong
    # calendar, wrong exactly on the days a false alarm is least welcome.
    from valuation.screener import market_session as MS

    # A SESSION THAT HAS NOT CLOSED OWES NOTHING, and the first cut counted one: asked for
    # 2026-10-08..09 at 02:00 UTC on the 9th it scored the 9th as 11 expected slots and 0
    # delivered, pushing the drop rate from 63.6% to 81.8% on a day the market had not opened.
    # **That is item 43's `gap_report` off-by-one exactly** -- treating the current day as due
    # from midnight -- and it inflates the headline in the alarming direction.
    last_closed = MS.last_closed_session()
    truncated = None
    if last_closed and until > last_closed:
        truncated = {"asked": until.isoformat(), "used": last_closed.isoformat(),
                     "why": "sessions after the last CLOSED session owe no slots yet"}
        until = last_closed

    sessions = []
    d = since
    while d <= until:
        if MS.is_trading_day(d):
            sessions.append(d)
        d += dt.timedelta(days=1)

    wid = _gh("/repos/%s/actions/workflows" % REPO_SLUG,
              '.workflows[] | select(.path | endswith("%s")) | .id' % WORKFLOW).strip()
    wid = wid.splitlines()[0] if wid else ""
    raw = _gh("/repos/%s/actions/workflows/%s/runs?per_page=100&event=schedule"
              % (REPO_SLUG, wid),
              ".workflow_runs[] | [.id,.created_at] | @tsv")

    delivered = {}
    for line in raw.strip().splitlines():
        bits = line.split("\t")
        if len(bits) < 2:
            continue
        rid, created = bits[0], bits[1]
        when = dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
        if not (since <= when.date() <= until):
            continue
        jobs = _gh("/repos/%s/actions/runs/%s/jobs" % (REPO_SLUG, rid),
                   ".jobs[] | [.name,.conclusion] | @tsv")
        ran = any(ln.split("\t")[0] == JOB and ln.split("\t")[-1] not in ("", "skipped")
                  for ln in jobs.strip().splitlines() if "\t" in ln)
        if ran:
            delivered.setdefault(when.date(), []).append(when)

    n_sessions = len(sessions)
    slots_by_date = expected_slots(sessions, ref)
    expected = sum(slots_by_date.values())
    runs = sum(len(v) for v in delivered.values())
    in_session = {d: [w for w in ws if IN_SESSION_FROM <= w.hour <= IN_SESSION_TO]
                  for d, ws in delivered.items()}
    zero_in_session = [d for d in sessions if not in_session.get(d)]
    zero_at_all = [d for d in sessions if not delivered.get(d)]

    return {
        "window": {"since": since.isoformat(), "until": until.isoformat(),
                   "sessions": n_sessions, "dates": [d.isoformat() for d in sessions],
                   "truncated_to_last_closed_session": truncated},
        "workflow_source": wf["source"], "authoritative": wf["authoritative"],
        "intraday_crons_today": crons, "slots_per_session_today": per_day,
        "slots_by_date": {d.isoformat(): n for d, n in sorted(slots_by_date.items())},
        "crons_by_date": {d.isoformat(): crons_on(d, ref) for d in sessions},
        "slots_expected": expected, "runs_delivered": runs,
        "dropped": expected - runs,
        "dropped_pct": (round(100.0 * (expected - runs) / expected, 1) if expected else None),
        # THE NUMBER THAT MATTERS, AND IT IS SMALLER THAN `runs_delivered`. A run that arrives
        # at 23:49 was fired by an in-session cron and delivers nothing to a user watching the
        # Signals tab during the session. Counting it as delivery answers the question "did
        # GitHub eventually run it" when the question is "did the feed refresh while the market
        # was open". Both ship, because the gap between them IS the finding.
        "runs_delivered_in_session": sum(len(v) for v in in_session.values()),
        "in_session_band_utc": "%02d:00-%02d:59" % (IN_SESSION_FROM, IN_SESSION_TO),
        # A run arriving at 00:16 was almost certainly fired by the PREVIOUS session's 20:23
        # cron. Arrival date is the only key the API offers, so late-night runs are attributed
        # to the day they LANDED, not the day they were due -- which inflates delivery slightly
        # on the day after a session and deflates it on the session itself.
        "attribution": "runs are keyed by ARRIVAL date, not by the session whose cron fired",
        "sessions_with_no_in_session_run": [d.isoformat() for d in zero_in_session],
        "sessions_with_no_run_at_all": [d.isoformat() for d in zero_at_all],
        "per_session": {d.isoformat(): [w.strftime("%H:%M") for w in sorted(ws)]
                        for d, ws in sorted(delivered.items())},
        "caveat": ("a delivered run cannot be attributed to the primary or the backup cron: "
                   "both gate the same `intraday` job and the API does not expose the schedule"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Intraday cron delivery rate.")
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    got = measure(dt.date.fromisoformat(a.since), dt.date.fromisoformat(a.until), a.ref)
    print(json.dumps(got, indent=1))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(got, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
