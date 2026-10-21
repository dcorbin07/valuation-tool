# PROMPT — r1 — 2026-10-19 — execute the scout's three edge-data drafts, bonds first

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path). **Do not edit
  `DECISIONS.md`.**
- `EDGE_DATA_MAP.md`, `LIT_LARGECAP.md`.
- The three drafts: `PREREG_DRAFT_tracelead.md`, `PREREG_DRAFT_f13skill.md`,
  `PREREG_DRAFT_osap3.md`.

## What to do

Don's standing rule (2026-10-06) is to test everything that makes sense. So test all three, one at
a time, under the standing discipline:

- each register is accepted or amended **before** any outcome exists, and committed **ALONE**
  (markdown only);
- trials are booked first;
- the governing tier is $10B+, on the corrected raw universe;
- both halves must pass;
- BH applies where a register has more than one arm;
- staged confirmation as in `DECISIONS.md`.

Anything that passes goes to Don as a candidate at **half** its backtested size, never adopted by a
lane.

## Order

1. **`tracelead`** (corporate-bond spread changes leading the stock). TRACE coverage rises with
   size, and its live source (FINRA) is free.
2. **`f13skill`** (which managers are buying).
   - Its opening census FAILED, by the scout's own account in §3. Run that census first, as a free
     pre-outcome kill, before any trial is booked.
   - Only 2013 onward is usable.
3. **`osap3`** (three published signals).
   - Pull the firm-level OSAP file only for the three named signals, and keep it out of git.

## Rules

- Raw WRDS rows stay in `D:\wrds`; the repo is public.
- WRDS: one connection attempt only per session.
- No key or login printed.
- Nothing adopted.
- No change to the Index, the 2026-10-22 rebalance, or any live path.

## Done

Each register lands on origin/main with a plain-words summary for Don:

- what it tested;
- whether it passed in big companies, both halves, after costs;
- if it passed, what the live Index would need to use it, and what that costs.
