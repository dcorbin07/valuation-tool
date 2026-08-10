# PROMPT — Session 14: commit the contract as OPTION E, pre-register the meter, fix the recording

**Owner:** `pipeline builder`. **Handoff:** append to `HANDOFF_edge_audit.md`.
**Audit session: 14.** Session 13 verified landed; the contract draft was blocked on Don. **Don has
decided. His choice, verbatim, to be recorded in the register:**

> **OPTION E** — Option C's structure (keep 2026-07-30 inception including the accrued negative
> days; 6-month operational gate; 60-month statistical verdict vs SPY; the ~36-month costed
> equal-weight-basket secondary once built), PLUS a pre-registered anytime-valid evidence meter
> that runs from inception but **first renders at the 6-month operational gate (2027-01-30) and
> monthly thereafter — whatever it says, favourable or not.**

## SCOPE / collision safety
You own `valuation/edge/**` minus the options carve-out. The 60-day auto-flip fix in
`valuation/screener/index_track.py` is the greeks lane's, being prompted separately — do NOT fix
it here, but your register may (and should) reference it as a dependency of the public posture.

## ITEM 1 — commit the register

Fill `PAPER_TRACK_CONTRACT.md` §5 with Option E, Don's choice and today's date, and flip the
status line from DRAFT to **IN FORCE from this commit**. Add the meter section:

- **Method, fixed now:** an anytime-valid confidence sequence (state the exact construction and
  its parameters — mixture/e-process choice, variance estimate source, the autocorrelation
  handling) on the monthly excess-vs-SPY series. Boundaries chosen for validity at continuous
  monitoring; **no parameter may be revisited after this commit.**
- **Display rule, fixed now:** computed from inception, **first rendered 2027-01-30**, monthly
  thereafter, owner-side. Public surfaces keep the "paper, thin, too early" posture until the
  operational gate PASSES; the meter reaches the public/demo side only with the day count and
  band beside it, never as a bare number. Rendering is unconditional on sign — a suppressed bad
  month voids the run under the abort rule, same as a back-fill.
- **Early-conclusion boundaries:** if the sequence crosses its pre-registered boundary before
  60 months, that IS a valid conclusion (state the boundary and what crossing means in each
  direction). This is the only legitimate early exit, and it exists because the boundaries are
  being fixed today.
- Log the register itself to `RESEARCH_LOG.md` per M1 — this is a trial, the most important one
  in the project.

## ITEM 2 — make the operational gate passable: fix the recording

§1's own findings, now work orders. The gate would fail today; repair it so it can pass honestly:

1. **Gap days** — only 2 of 5 rows exist. Find why the daily write skipped days 2–4 (scheduler,
   crash, or conditional write), fix it, and add the guard that a missed day is LOUD (a gap
   report in the track file itself), since the abort rule distinguishes "missed and filled same
   week" from "missing".
2. **The engine has never been fed** — `paper_option_orders`, `paper_index_holdings`,
   `paper_index_track` are 0 rows while the Cowork-side `valquo_track.json` is the only live
   record. Wire the tested engine (45/45) into the daily path so the contract governs the
   mechanism that actually records, or state plainly which mechanism the register binds and why
   the divergence is acceptable. Two recorders that can disagree is a B7-class split; do not
   leave it standing silently.
3. **Backfill nothing.** Days 2–4 stay missing, logged as the abort rule requires. The fix is
   for tomorrow's rows, not yesterday's.

## Report

Append: the committed register (quote §5), the meter's exact parameters, the recording fixes with
evidence the daily write now happens (two consecutive days landing), what you did NOT do,
`## BUGS FOUND`, Session 15's first item with `needs first`. Ledger; merge origin/main first;
suites green; push; **verify the land**.
