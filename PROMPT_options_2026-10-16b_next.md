# PROMPT — options lane — 2026-10-16 (b) — after the fleet keys go in: confirm the fills, run EARNINGS-CSP's free kill, and measure a forward earnings calendar

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- your item 66 commits;
- the scout's drafts `d5c50e4` (EARNINGS-CSP) and `da616fc` (F-21b), and its ranking `3fe844f`.

## Don's answer on F-4 and F-10: not now

Do not re-declare them yet. Both books avoid scheduled earnings, and the scout measured that the
event spine holds no forward dates, which is why F-4 "enters nothing, ever". So re-declaring them
now would add two books that cannot enter. Also:

- the short-side tenor comparison is already answered by K3's arithmetic: 30 DTE beats 52 DTE on
  both axes in both quadrants;
- F-10's build cell clears the crash gate by only 2.3%.

Revisit once part 3 below says whether a forward earnings calendar exists.

## 1. Confirm the fleet trades (once Don has added `ALPACA_FLEET_PAPER_KEY_ID` / `_SECRET_KEY`)

- **F-21, F-22 and F-8** should place and fill on the fleet paper account, and F-3 and F-11 on
  the existing key, through the **scheduled** door. Verify on the service; do not assume.
- **Check the timing.** The fleet cycle has been running at about 00:24Z, after the close.
  Measure whether an Alpaca paper option order submitted then is accepted, queued or rejected.
  - If it does not work out of hours, hand a schedule inside market hours to Don through
    `pending_workflows/`.
  - GitHub fires this repo's crons 3.5–7.5 hours late (item 64's measurement).
- **Report the starting balance the fleet account should have** for the declarations' sizing to
  mean what they say, so Don can set or reset it in Alpaca. Do not amend a declaration without Don.

## 2. EARNINGS-CSP: run its free kill K1, exactly as the draft froze it

- K1 is the payoff ratio on O7's 6,013 banked events. The arm runs only if it is at most 0.65.
- No new data, no option quote, and zero trials (DC-1's precedent).
- If K1 passes: commit the register ALONE, book its trials before any runner exists, and run
  stage 1 on the build quadrant.
- If K1 fires: stop, and say so plainly.
- Stage 3 (forward) depends on part 3.

## 3. A forward earnings calendar: measure the free route

The app already takes earnings dates from Yahoo (DECISIONS 2026-10-14). On the fleet's optionable
gate (487 names), measure Yahoo's next-earnings dates against the realised 8-K Item 2.02 filing
dates over recent quarters:

- coverage;
- date accuracy;
- how far ahead the date is known;
- how often it moves.

This calendar is what F-4, F-10, EARNINGS-CSP's stage 3 and any event-avoiding book need. Report
it; do not wire it into a book yet.

## 4. F-21b: freeze the rule now, before F-21's first fill

- Commit the draft's zero-parameter rule (SPY below its 200-day average) ALONE, charged as the
  draft prices it.
- Computing what it would have done on 2016–2026 stays a void condition.
- State in the register that it cannot resolve statistically in any horizon Don will wait for
  (about 17.5 years). What it reports is the gate's **cost**.

## Not now

- MB2's single cell (60–90 DTE × 0.85–0.95 delta) is Don's call; leave it.
- The scout's sizing item (SELL-PREMIUM-2 at a concurrency cap of 3) is Don's call too; leave it.

## Done

On origin/main, with a plain-words summary for Don:

- which books filled, and when;
- K1's number and what it decides;
- whether a free forward earnings calendar is good enough.

Paper only; no real trades.
