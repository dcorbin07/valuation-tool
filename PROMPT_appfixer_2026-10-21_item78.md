# PROMPT — app fixer — 2026-10-21 — item 78 (URGENT, before item 77): the paper slot can no longer read its own order history

**Land by Friday 2026-10-23, 12:00 ET.** Never land between Friday 4pm ET and the 10-22 rebalance
being recorded that night. Pause item 77 first (WIP on a side branch, not landed), and resume it
after this lands.

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.**

## What Don saw (2026-10-21, ~5:56pm ET)

Don replaced the Index paper keys on Render, then ran **LIVE PATH CYCLE #25** by hand. It
succeeded, with two warnings and a Discord line.

## 1. The paper slot is blocked by its own order count (blocks Monday's paper rebalance)

The warning, verbatim:

```
slot paper reconcile_truncated x1: the broker returned a FULL page of 510 orders, so older fills
may be outside the window and this slot's holdings cannot be totalled reliably
```

`reconcile` calls `client.orders(limit=ORDERS_PAGE_LIMIT)` (500) once, and correctly refuses when
the page is full. The paper slot now has more orders than that, mostly day orders re-sent every
cycle since 10-16. So **every cycle will refuse from now on**, including Monday's first real
rebalance. The IRA slot reaches the same wall in time.

- **Read the slot's WHOLE order history by paging.** Use Alpaca's `/v2/orders` `after`/`until` and
  `direction`, or another documented route you prove complete.
- **Keep the refusal for a read that is genuinely incomplete or failed.** A full last page means
  fetch the next one, never "assume done".
- **Explain the 510:** more than the 500 requested. Does nesting count? Is a `nested` parameter in
  play?
- **Report the paper account's real order count**, and whether the slot's recorded holdings match
  its fills once every page is read.
- **Say whether the re-send pattern should cancel or replace rather than pile up.** Report it; do
  not change it here.
- **Tests:** recorded HTTP across several pages, including exactly 500 on a page, a failed second
  page, and pages that overlap. Each must fail on today's code.

## 2. The privacy filter blocked a real alert

Discord posted: *"A Valquo alert was composed and NOT posted: its text failed the nothing-private
check."* Most likely this was the "cleared" line for `paper_client_absent`, which names
`ALPACA_PAPER_KEY_ID` and `ALPACA_PAPER_SECRET_KEY`.

- Find the blocked text in run #25's log and say exactly which rule fired.
- `safe_body` must block secret **values**:
  - any configured secret;
  - key-shaped strings;
  - webhook URLs;
  - tokens;
  - account numbers.
- It must **never** block a variable **name**.
- Redact the matching span rather than blocking the whole message wherever that is safe.
- Test that the cleared line, and item 77's coming *"no ALPACA_ACCOUNT_1_LIVE_PCT set"* line,
  both post.
- Test that a real key-shaped value is still caught.

## 3. Why does a 0% slot holding nothing list 31 names it "would trade"?

Verbatim:

```
slot 1 preflight_failed x1: no usable price for 31 name(s) the cycle would trade: APA, CF, INCY,
FDX, JBHT, STM, MRNA, TTE
```

Slot 1 is Don's IRA: `LIVE_PCT` 0, paused, and it holds nothing of its own. Nothing could be sent,
because the workflow is paper-only.

- Explain why preflight thinks this slot would trade anything at all.
- If its plan is empty, it needs no prices, and must neither refuse nor alert on prices.
- A missing price **outside the orders window** is expected. It must not become a daily
  `#valquo-alerts` reminder.
- Inside the window it stays an alert.

## 4. A job that never ran the slots declared their problems "cleared"

At 4:54pm ET (the REBALANCE WATCH run, 20:53 UTC), `#valquo-alerts` posted:

- *"slot 1: preflight_failed has cleared"*;
- *"slot paper: reconcile_truncated has cleared"*.

One hour later, run #25 showed both problems again. The watch does not run the trading slots, so
it had no evidence either way, and "not evaluated" was announced as "fixed".

- A condition may only be declared cleared by a run that evaluated it and found it gone.
- Test: a watch-only run beside an open slot condition posts nothing about that condition.

## 5. Permanent facts should not be daily reminders (recommended; Don may veto)

Two of the 4:54pm lines can never clear by repair:

- `record_row_missing` lists the 11 August–September days that cannot be backfilled;
- `recording_not_ok` follows from them.

Reminding Don daily about something nobody can fix is the cry-wolf failure that `MA21` warns
about. The new rule:

- announce a permanent gap **once**;
- alert again only when a **new** trading day goes missing;
- re-announce `recording_not_ok` only when its cause **changes**.

Every new missed day must still alert the first day it is missed. Section 6 of item 76 found the
remedy for the gate, and it is Don's contract decision, not code.

## 6. Late runs land after the close

The 12:10pm ET cron fired at 4:04pm ET, after the market had closed. Report how often the five
crons land outside the orders window, measured from the run history. Late runs are harmless to
the planner by design, so this is a measurement, not a change.

## Done

On origin/main, with a plain-words summary for Don. Its **first line** says whether Monday's paper
rebalance can now run.

No key, no percentage, no arming change, no `.github` change. Then resume item 77. The auditor's
review 9 covers items 77 and 78 together.
