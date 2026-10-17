# PROMPT — app fixer — 2026-10-16 — item 64: the seam pull's SIP window, the paper cycle's schedule, and the IEX quote question

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your item 62 and
63 commits first. Do part 3 first if the market is open when you start: it closes at 4pm ET.

## 1. The seam pull asks for SIP data that is too recent

Don ran `POST /admin/alpaca-seam?run=1` ten times on 2026-10-16, and every run returned the same
thing:

- `"pull":{"complete":false,"n_alpaca":0,"requests":1}`
- the reason: "subscription does not permit querying recent SIP data (HTTP 403)"
- the window: `"start":"2025-09-11","end":"2026-10-16"`

The free plan serves SIP only once it is more than 15 minutes old, and `end` is today, so the whole
request is refused at the first call.

- Set `end` to the last completed session's close, or "now minus 16 minutes", whichever is
  earlier.
- A no-progress reply says plainly that re-running will not help, instead of "run it again until
  complete".
- Test both.
- Then either run the pull yourself through the door, or give Don the PowerShell commands. Say how
  many runs a full 222-name, 250-day pull needs.

## 2. The scheduled paper cycle is not reliably on time

Measured from GitHub's API on 2026-10-16:

- PT-WRITER, cron `7 3` and `37 4` UTC, actually ran at **08:04Z and 09:13Z** on both
  2026-10-15 and 2026-10-16. That is about five hours late.
- `live-cycle.yml`'s 14:40Z schedule had **no run at all** by 17:19Z today. The only run ever is
  the manual dispatch at 02:54Z.

A late cycle falls outside the orders window (09:35–15:45 ET) and refuses.

- Add backup schedules inside the window. The door is idempotent, so extra runs are no-ops: for
  example 14:40, 16:10 and 17:40 UTC, which stay inside the window in both daylight regimes.
- Check whether the original schedule ever fires.
- Report when each scheduled run actually started.
- Hand the updated workflow to Don through `pending_workflows/`, with his `install_workflows.bat`
  step.

## 3. Answer the IEX quote question during market hours

Item 63's first real cycle, run after hours, refused because 26 of the book's names had no
two-sided IEX quote. Your note says the real test is a run while the market is open.

- Dispatch the cycle with `?run=paper` while the market is open, today if possible.
- Report `marks_coverage`: how many names priced, and which did not.
  - If the book prices, the paper slot places its first orders. Report them and their fills.
  - If names are still missing while the market is open, that is a measured finding about the
    free IEX feed. Do not invent a fallback mark.
- In plain words, put the choice to Don, priced:
  - Alpaca's $99/month plan, for full quotes;
  - a different mark rule, which would need its own justification and the auditor's view;
  - or trading only the names IEX can quote, which would change the book and is a construction
    change.

## Done

Nothing switches and no live key is touched. Done means on origin/main, with a plain-words
summary for Don that answers part 3 first.
