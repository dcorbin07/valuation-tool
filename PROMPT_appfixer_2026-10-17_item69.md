# PROMPT — app fixer — 2026-10-17 — item 69: the auditor's fourth blocker (a silent unpriced exit), and spin-offs in the bound record

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), the auditor's
fourth review (`e345bb2`) and your items 67–68 first.

## 1. The blocker: an exit the feed cannot price is dropped in silence

The auditor reproduced it end to end through `run_cycle` with the real `AlpacaPaperBroker`:

- `exits_planned: ['MSFT']`, but no price;
- nothing is sent and no alert is raised;
- the event is recorded COMPLETE, and `marks_coverage` reads "1 of 1 priced".

Two things cause it:

- preflight's `need` and `marks_coverage`'s `need` come from the **held** book only, not from the
  exits;
- `if not plan["orders"]` closes the event without reading `plan["skipped"]`.

§8 requires three things: no trade, an alert, and a retry next cycle. Today only the first
happens.

- Widen both populations to include planned exits.
- An event with a skipped exit is **not** complete: it stays open, alerts, and retries.
- "Nothing to do" and "could not work out what to do" must be different values. This is the third
  time this path has collapsed two states into one, so add a test that fails if any planner
  outcome other than "targets met" closes an event.
- Test through the real client class, and make sure the test fails on the old code.

## 2. Spin-offs in the bound Index record (item 68's finding, applied to the record)

Item 68 measured that yfinance (the record's vendor, `auto_adjust`) left Aptiv's and Unilever's
spin-offs as **−10.6% and −7.0% cliffs**.

- Check what happens to the bound record if a **held** name spins something off.
  - Would the record book a fake loss?
  - Does Amendment 2's corporate-action rule (acquisition or delisting = sold at the last close)
    cover a spin-off at all?
- Report it, and propose the rule. **Do not change the record or the contract.** Any rule
  change is Don's decision, and it would be a contract amendment.
- Name any current Index holding with an announced spin-off before the next rebalance.

## Done

On origin/main, with a plain-words summary for Don. The auditor reviews part 1 before any live
key goes in.

The pending five-cron `live-cycle.yml` was cleared as safe to install by the auditor, but **Don
waits** to install it: `fleet-cycle-in-hours.yml` must first be turned into a replacement (see the
options lane). Do not add any new pending workflow without saying so.
