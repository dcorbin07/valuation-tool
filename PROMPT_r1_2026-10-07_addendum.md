# PROMPT — r1 — 2026-10-07 — addendum to PROMPT_r1_2026-10-07_rebuild_and_batch2.md

Read `DECISIONS.md` again: Don ruled on 2026-10-07 to move the canonical backtest to the corrected
universe after your full rebuild, and to restate the public pages once from it.

So item 5 changes from a plan to the move itself, done after items 1-4:

1. Write `DECISION_canonical_move.md` first (what moves, what gets re-derived, machine hours) and
   land it, so the record says what was intended before it happened.
2. The canonical run's HEADLINE must describe the DEPLOYED flat 1/7 book. You established that
   `run_backtests`' headline describes the CPCV-adopted book whenever CPCV adopts, and on the
   corrected universe it adopts. Fix that so the headline is always the deployed book, and the
   adopted book (when there is one) ships beside it under its own clearly-named block. A canonical
   file whose headline is a book nobody runs is the defect, whichever way it flatters.
3. Make the corrected universe canonical: the corrected panel, `BACKTEST_RESULTS.json` re-run from a
   clean tree, the corrected placebo draws as the floors the pages read (the X7 floors on the old
   panel stay in the record as history), and `INDEX_BOOK` re-measured so the Index tab's figures
   come from the corrected universe. Every landed figure you list as needing re-derivation is either
   re-derived or marked UNMEASURED in the artifact — never left silently describing the old panel.
4. Do NOT touch `PAPER_TRACK_CONTRACT.md`'s frozen meter parameters, the forward record, or the
   deployed weights.
5. Hand the app fixer a single table of every public figure, old → new, with where each lives
   (read live, or a transcribed literal in `index_book_measured.py` or a template). /proof reads
   its numbers live, so the numbers change the moment your file lands; the app fixer will follow
   the same day with the wording and the transcribed literals. Say in your handoff when you land
   so that happens.

Done means on origin/main, with a plain-words summary for Don.
