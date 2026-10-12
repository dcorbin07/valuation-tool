# PROMPT — app fixer — 2026-10-12 — item 49 (item 48 is SUPERSEDED: the options lane fixed the clock-rotted tests at 6f05fe4)

Read `DECISIONS.md` first.

1. **Two pushes that never landed.** They failed the gate on 2026-10-10 while the clock-rotted
   tests had it red: the scout's SELL-PREMIUM draft (`worktree-scout-research-reset`, run #698,
   commits c4d9aa5 + 8f41b10) and r1's `CANONICAL_MOVE_TABLE.md` (`worktree-crowding-p2`, run
   #699, ae190f3). Re-run both land runs (`gh run rerun`), resolve anything that now conflicts
   with your item 47 (r1's table is the old-to-new RECORD; your generated
   `CANONICAL_FIGURE_TABLE.md` is the binding pin — say how the two relate rather than letting
   them disagree), and confirm both are on origin/main.
2. **One stale sentence on /proof, live now:** under "Stock-ranking tests 297" it still says
   "That is why the multiple-testing hurdle above is failed: we counted honestly", while the table
   above it now shows the hurdle CLEARED (4.594 against 3.362). Derive it from the same field the
   table reads, and sweep /proof, /methodology, README and START_HERE for any other sentence that
   still asserts the old pass/fail state.
3. **2026-10-14:** the intraday delivery re-measurement (a full week since the `53 17-19` backup
   cron), reported beside item 37's 72.2%.
4. **When Don has run FLEET SELF-CHECK** (after installing `fleet-selfcheck.yml` and the corrected
   `fleet-cycle.yml`), confirm the four armed books are breathing again and report what the next
   fleet cycle did.

Done means on origin/main, verified live, with a plain-words summary for Don.
