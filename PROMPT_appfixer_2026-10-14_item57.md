# PROMPT — app fixer — 2026-10-14 — item 57: the valuation page's breakages, and four Index record defects before the 2026-10-22 rebalance

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy
may be out of date) first.

The manager measured everything below on valquo.co on 2026-10-14, against origin/main `9a27a6b`.
Verify each finding before changing anything.

**Scope.** No scoring, weight or construction change; none of this is a vintage event. **The Index
part must land before 2026-10-22.**

## A. The valuation page

1. **"d is not defined" on every search.**
   - Cause: `runValue` in `app.js` (~line 183) calls
     `loadRecent(ticker, (d.company && d.company.name) || "")`, but the variable there is `data`.
   - Effect: the red error box appears, and the earnings, press-release and headline panel never
     loads for any name.
   - Fix it, and add a check that would have caught it (for example an undefined-variable lint
     over `app.js` in the suite).
2. **Yahoo `info` is failing for every name on the server.** All seven tested (AAPL, NVDA, TSLA,
   KO, KNSL, APLD, JPM) carry *"Yahoo `info` unavailable; used fast_info + statements only."* It
   cost every name:
   - its name, so the page heads "KNSL (KNSL)";
   - its industry and its company description;
   - its vendor beta (the fallback from the name's own prices gives KO 0.28);
   - its next earnings date and its analyst target.

   Then:
   - **Find the cause first.** Candidates: the yfinance version against Yahoo's current
     endpoints, or the server's IP being throttled. Test whether item 54's per-name Yahoo scan
     fallback is the cause.
   - **Add free fallbacks:** name and industry from SEC (`company_tickers.json` title, submissions
     `sicDescription`), and a description from a named, verifiable free source, labelled as such.
   - **Make the degraded state visible** in one line on the page, and have `live-check` flag it
     when it hits every name.
3. **"Revenue (latest yr)" shows the OLDEST year, and the margin trend runs backwards.**
   - Cause: `company_profile_block` in `web/app.py` takes `rev[-1]` and `hist[0] → hist[-1]`,
     but the histories are newest-first (`fiscal_years` reads `[2025, 2024, 2023, 2022]`).
   - What the page shows: NVDA $26.97B against a true $215.94B, AAPL $394.33B against $416.16B,
     KNSL $838.80M against $1.87B. KNSL's margin reads "34.4% → 23.8%" when it actually rose from
     23.8% (2022) to 34.4% (2025).
   - Fix it, put the years on both endpoints, test with a newest-first fixture, and check every
     other reader of the `*_history` arrays for the same assumption.
4. **Format market cap and revenue compactly with two decimals** ($7.95B, $838.80M, $5.01T).
   - Use the existing `mcap()` formatter.
   - Change its `$M` branch to two decimals; its own comment says "Two decimals throughout". That
     also changes the Index and hot-list columns, which is intended.
5. **Dark mode: hard-coded light backgrounds make text unreadable.**
   - `.dcf-warn` (#fff8ea): the "Do not use the fair value below" box.
   - `.avg-risk` (#f4f7fb): the average-risk discount-rate box in the hero.
   - `.rc-q` and `.rc-h`: `var(--panel)` is never defined, so they fall back to #fafbfc. These
     are the headline boxes, which appear once part 1 is fixed.
   - `.thin-group` and `.thin-flag` on the hot list, and `code`.

   Move each to theme variables with dark values, and sweep `style.css` plus inline styles in
   `app.js` for any others.
6. **The Monte Carlo chart is empty for financials** (KNSL; check JPM).
   - Cause: `montecarlo` carries the P/B–ROE distribution with empty `hist_bins` and
     `hist_counts`, so `mcChart` draws a blank canvas above a correct median line.
   - Preferred fix: emit a histogram for that model server-side, since its 10,000 trials already
     run. Otherwise, treat empty bins as "no histogram" and show the percentile view.
7. **"the book takes the top 85 of None eligible names"** (`web/unified.py` ~472).
   - Python's `None` leaks into the text, and the sentence describes a daily top-N rather than a
     held book.
   - Rewrite it from the book in force: formed on 2026-07-30, held until the next rebalance on
     2026-10-22, and this name is not in it.
8. **Check more tickers yourself, in light and dark mode**, at least: AAPL, NVDA, TSLA, KO, KNSL,
   JPM, APLD, one foreign ADR and one recent IPO. Fix anything else broken and list what you
   found.

## B. The Index record

1. **ET has been unpriced in the daily record since 2026-10-05.**
   - Why: Energy Transfer moved its listing from the NYSE to the Texas Stock Exchange that day
     (ticker unchanged), and the free price route stopped returning it.
   - Effect: `n_priced` has read 84 of 85 every day since, and `contract_row` silently
     renormalises the name away.
   - Fix the price route for TXSE listings.
   - Make an unpriced holding visible in three places: on the Index card ("1 holding unpriced
     since …"), in the PT-WRITER response body, and as an alert after more than one trading day.
2. **The recording engine does not follow the contract's corporate-action rule.**
   - The rule: `PAPER_TRACK_CONTRACT.md` §5a says an acquired or delisted name is "sold at its
     last traded close, weight redistributed pro-rata", and that the engine already does this.
   - What the engine does: `contract_row` renormalises over the priced names from the segment
     base, which removes the name back to the segment start. That is the alternative the
     contract itself calls worse.
   - Size: WBS (0.78%) and ET (0.79%) together are a few hundredths of a point.
   - Do not touch recorded rows (append-only).
   - Implement the rule from the next segment (the 2026-10-22 rebalance), so the current segment
     stays reproducible, and store the last close on the record at the time (the contract's own
     stated limit).
   - Add a dated correction note to the contract, with the measured size.
   - Treat a vendor outage on a name that still trades as a data problem to fix, never as a sale.
3. **The WBS row.**
   - It sits at row 58 among the held names with 0.00% weight, $0 allocation and a blank company.
     Move exited names to a separate "left the book" line with date and reason.
   - Its exit note still says "PAPER_TRACK_CONTRACT amendment outstanding", but Amendment 2
     recorded the rule on 2026-10-04.
4. **The rebalance door** (`index_mark.append_rebalance`).
   - **Refuse an event dated before an already-recorded row.** Today it accepts an event dated D
     even when a later row exists, and that later row was marked on the old book.
     - Why it matters now: the 2026-10-22 event is appended on the evening of 2026-10-23. If that
       slips past PT-WRITER's 03:07 UTC run, the 10-23 row is marked on the old book.
     - Refuse with a clear message and pin it with a test.
   - **List unpriceable names in the dry run.** It should name any position the free price route
     cannot price on the event date. Otherwise the daily row silently leaves that name out.

## Done

Tests that fail on the old code, the full suite green, and each fix verified live on valquo.co.
Done means on origin/main, with a plain-words summary for Don of what was broken and what
changed.
