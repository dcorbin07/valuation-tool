# PROMPT — app fixer — 2026-10-10 — item 46 still unlanded, then item 47

Read `DECISIONS.md` first.

## First: item 46 (the fleet that never filled)

Your worktree has item-46 work (`tests/test_item46_fleet_never_filled.py` and data from
2026-10-09) but nothing is committed or on origin/main. Finish it, land it, and give Don the
plain-words answer: why 16 of 18 books never ordered and why f3's 72 orders never filled.

## Then item 47: the public restatement, landed ONCE with the artifact swap

Don ruled (2026-10-07) to move the canonical backtest to the corrected universe and restate the
public pages once. r1 is writing `CANONICAL_MOVE_TABLE.md` (every public figure old → new, which
book, where it lives, the caveat). When it is on origin/main, in ONE commit:

1. Copy r1's banked corrected artifact into the tracked `BACKTEST_RESULTS.json` / `.md`.
2. Restate every claim in the table: README's evidence section, START_HERE, /proof (HLZ row,
   placebo counts against the CORRECTED floors, panel size, dates), /methodology, the Index tab and
   `index_book_measured.py`. Replace the "not a survey of survivors" sentence and the
   "cpcv.adopt is false on every run" sentence with accurate ones (CPCV now prefers a tuned
   weighting on the corrected data; the deployed equal weights are kept because the tuned book
   earns less — 2.83% against 6.07% — and nothing is adopted without Don).
3. **The landing figure fed by `settings.measured()` must describe the Valquo Index**, not the
   top-25-of-the-whole-universe research book (which goes −4.70%/yr on the corrected universe).
   DECISIONS.md: ONE Valquo Index; any research figure on a public page says in the same sentence
   that it is not the Index and names its universe.
4. Every changed figure carries r1's caveat that the old and new panels share no rebalance dates.
5. Apply Don's 2026-10-10 ruling in DECISIONS.md on three figures r1 flagged: drop "alpha vs the
   all-cap equal-weighted universe" from the Index tab (show the Index vs SPY and vs the
   equal-weighted $10B tier instead); show /proof's placebo block as it is on the corrected panel's
   own draws, with the like-for-like guard replacing the at-least-one-failure guard; and show the
   research decile's −1.14pp/yr net-of-costs result vs SPY plainly.
6. Keep "no '+32%', no 'beats SPY'". All 270+ suites green, including the six that went red for r1.
   Verify every page live after deploy and report each figure as it now reads.

Done means on origin/main, verified live.
