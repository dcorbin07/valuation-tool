# PROMPT — pipeline builder: the accounting red-flag risk card (MA26-A + MA28 + MA54-1, one register)

**Owner:** pipeline builder. **Handoff:** `HANDOFF_edge_audit.md`.
**This is not audit cleanup.** Audit #3 closed at `cbeb658` with zero OPEN — 53 DONE,
5 DESIGN-RECORDED, MA18 blocked on the Cowork lane, MA60 routed to Don. This is the first item of
the post-audit research programme, and it is chosen because it is the only one whose gate is not
alpha.

## Run ONE register. Not five.

Five items sit DESIGN-RECORDED — MA27 (ridge), MA28 (this one), MA55 (confidence-weighted
mispricing), MA57 (insider ownername) and MA58 (return seasonality). Running them as a batch would
be a five-arm search dressed as a backlog, at a moment when N is 230 and every additional arm
raises the bar for all of them. **Run this one. Leave the other four alone.** MA57 in particular is
already decided: the data blocker was refuted, the change is one line in `_KEEP`, and it was
deliberately not taken because a column with no consumer is dead weight. Do not re-open it as a
warm-up.

## What this item is

Your own last batch collapsed three audit IDs into one hypothesis: **MA26-A, MA28 and MA54-1 get
ONE register.** The hypothesis is a name-level **accounting red-flag risk card** — the surviving
half of S10, whose valuation half was already rejected.

**THE GATE IS THE CRASH-RATE REPLICATION. IT IS NOT ALPHA.** This is stated three times in the
record and it is the single thing most likely to go wrong here, because every instinct in this
repository is pointed at alpha bars. The claim being tested is a **disclosure**, not a screen:
*names carrying flag X went on to suffer outcome Y at rate Z, against a base rate of W.* Whether
flagged names underperform on a composite is a **different hypothesis** and it is not this one.
If you find yourself computing top-decile alpha to decide this item, you have swapped the
hypothesis mid-run.

Concretely, the register must fix, before any measurement:

1. **The named bad outcome**, precisely and in advance — a drawdown threshold over a stated
   horizon, or a delisting/distress event from the ACTIONS mask, or whatever you choose. One
   definition. Not a family you pick from afterwards.
2. **The base rate it is measured against**, and how it is computed on the same universe and the
   same dates. A rate without its base rate is not a finding.
3. **The flag construction** — which accounting inputs, at what thresholds, with coverage stated
   per input before any rate is read. The COVERAGE RULE binds: check coverage first, and if a
   component is under the floor, say so before quoting anything built on it.
4. **The replication requirement** — the rate must hold in both halves of the panel, on the
   held-out protocol this project already uses. A rate that appears in one half only is NULL.
5. **The kill condition**, written so it can fire: what separation between flagged and base rate,
   in both halves, would fail. Ambiguous against that threshold is **NULL**, not a judgement call.
6. **What the product would be permitted to say** if it passes — the exact sentence, with its base
   rate in it, subject to V3 (no per-name precision) and the withholding rules. If you cannot write
   a sentence the product could honestly display, the item has no deliverable and should say so.

## Discipline

- **Pre-register in a markdown-only commit, committed alone**, a strict git ancestor of the
  measurement commit — MA60's convention check now enforces this, so a register bundled with code
  will fail CI rather than merely being frowned at.
- **Book the trial budget in `RESEARCH_LOG.md` before running**, not after. Count every arm the
  register permits, including the ones you expect to discard. Equity N is 230; say what it becomes.
- **Controls, on the template your last batch used:** reproduce the published record first and
  abort before reading any arm if it does not; confirm no arm is inert; confirm the flag is not a
  proxy for an incumbent (report the largest absolute correlation against existing signals).
- **Point-in-time or it does not ship.** The flag must be computable from data knowable at the
  scoring date, pinned by a test, on the same protocol as `tests/test_pead.py`.
- **Report a defect in your own instrument as loudly as a result.** Your last batch caught two —
  a blank-code counter reading 0 against 1,544,490 blanks because `pd.NA` compares False against
  every literal, and a test helper returning the worktree's own `data/` so two tests skipped while
  believing they had looked. That habit is why this record is worth anything.

## Expect NULL

The record is ~250 tested, one adopted. Say your prior in the register before you measure, as you
did on MA27 (REJECTED at ~75/25). A register that predicts success and finds it is worth less than
one that predicts failure and is surprised.

## Deliverables

- `PREREG_*.md` — committed alone, before measurement
- the measurement script + tests, with mutation testing on any tripwire
- `HANDOFF_edge_audit.md` — committed threshold · what was run (command, panel, dates, n) · the
  numbers · the verdict · **the mechanism, not just the number** · `## BUGS FOUND` · **what was NOT
  done and why**
- `VALQUO_LEDGER.md`: MA26-A, MA28 and MA54-1 resolved by the one register; `RESEARCH_LOG.md`
  updated with the trial count and the new N
- Merge main first; 107 suites green; push and verify the land.

**Do not touch** `.github/` — MA11's land policy refuses any branch that does, and MA60's residual
is already routed to Don as a human PR.
