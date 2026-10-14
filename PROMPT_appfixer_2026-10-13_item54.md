# PROMPT — app fixer — 2026-10-13 — item 54: repair the live scan on the free route

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy may be out of date) first: Don ruled on your item 53 part 7 today. The repair goes ahead on the
free route, and it is a REPAIR, NOT A VINTAGE EVENT — no scoring rule changes, inputs the rules
already expect come back, and the Index record is built from Sharadar rather than the live scan.

1. **Take FMP out of the fetch chain.** It returns 402 and disables itself after 44 errors; it is
   not being renewed. Remove it cleanly (do not leave a source that fails on every run) and say what
   it used to supply that nothing else does, if anything.
2. **Retry a failed per-name fetch on Yahoo** (you measured that T, VZ, MGM and RNR return full
   momentum from yfinance while the scan has nothing for them). Pace it so the scan stays inside its
   budget and does not trip Yahoo's per-IP throttle — r1 measured that a throttled feed degrades
   silently (betas go missing, WACCs collapse to the cost of debt), so check for those tells and
   count a degraded fetch as a failure, never as data.
3. **A name scored on too few themes is marked and not ranked at the top.** Define "too few" with a
   rule stated on the page (for example fewer than four of the seven weighted themes), show such a
   name in its own clearly labelled group, and use `score_confidence.THIN_DATA`'s wording. SMFSY,
   #1 today on size alone, is the test case. This applies to the live hot list and the Index tab's
   "today's hot score" labels ONLY — `build_index` and the rebalance path are not touched (that would
   be a construction change).
4. **The bank bug r1 reported:** `app.py` reads `result.financial_extras`, which does not exist —
   the field is `financial_surfaces` — so every bank's "what the price assumes" sentence renders as
   unavailable while the engine has the number (ABCB 12.2%). Fix it and test it on two banks.
5. **Measure and report after the deploy:** how many names gained a theme, how many hot scores and
   ranks moved (you estimated 13 of the top 500 and 4 of the top 100), NVDA's themes, and where
   SMFSY now sits.

Paper only, no real trades, `.env` untouched. Done means on origin/main, verified live, with a
plain-words summary for Don.
