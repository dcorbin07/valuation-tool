# PROMPT — app fixer — 2026-10-22 — item 79: cap "high confidence" below 0.5× price, and draft Amendment 4 (the six-month checkpoint counts from 2026-09-23)

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your item 76
section 6 first. **Do not edit `DECISIONS.md`.**

**Never land between Friday 2026-10-23 4pm ET and the 10-22 rebalance being recorded that night.**

## 1. No fair value below 0.5× price is shown as "high confidence"

**Don's ruling, 2026-10-22, option 1 of 3.** Item 76 measured 17 served names between 0.2× and
0.5× of price, 11 of them served `confidence: high` (for example ISRG 0.270×, AppLovin 0.477×).

- Below 0.5×, the confidence label is capped at the next level down: no "high". Everything else
  is unchanged:
  - no new warning text;
  - nothing hidden;
  - the fair value itself unchanged;
  - item 76's loud flag below 0.2× unchanged.
- Define 0.5× **once**, beside `FV_BAND_LOW`. Comment it as a display judgment Don chose, not a
  measured threshold, and import it everywhere; never retype it.
- Apply it at every surface that shows a confidence label, including the API payloads, through
  one function. Add a test that fails if any site skips it.
- Report how many served names change label today.

## 2. Draft Amendment 4 to `PAPER_TRACK_CONTRACT.md`, for Don's signature

**Don approved the direction in chat on 2026-10-22.** He signs the text separately, after reading
it.

Item 76 found that the operational gate cannot pass on 2027-02-13:

- vintage 4 missed 11 trading days in August and September;
- §3's tolerance covers only a single day filled the same week;
- the daily writer has been gapless since 2026-09-23.

Draft the amendment to say:

- **The six-month operational-gate window starts at 2026-09-23**, the date the automated writer
  became gapless. Give the reason: an operational repair, independent of any outcome — the same
  argument as Amendment 1. **The gate date becomes 2027-03-23.**
- **The missed days stay visible as gaps and are never backfilled.** The reconstructed points stay
  excluded from every count, meter and verdict, as today.
- **The gate's realised-cost condition** is written against 33.4 bps, which is the superseded
  panel's research-decile figure. Replace it with the figure that actually describes the SERVED
  Index book, read from the tracked artifact, and say which one and why. The research decile's
  77 bps is NOT the Index's cost either.
- **State explicitly what does NOT change:**
  - the 2031 verdict date;
  - σ, ρ, α and the cost drag in the frozen meter;
  - the SUPPORTED and UNSUPPORTED bars;
  - Amendments 1–3.
- Confirm in writing that §3's whole-run void clause is not engaged.

**Implement it behind its signature row** (Amendment 3's pattern): unsigned, the site keeps
today's behaviour exactly. Pin both states by test.

Also:

- Re-check the gate's other outstanding condition. The one unpriced holding since 2026-08-20
  (WBS) should clear with the 10-22 rebalance; say whether it did.
- Update `PT-WRITER`, the README and `recording_not_ok`'s alert text to name the new date once
  signed.

## Done

On origin/main, with a plain-words summary for Don. It must include the amendment's text in plain
words and the exact one-line instruction Don sends to sign it.

No key, no percentage, no `.github` change.
