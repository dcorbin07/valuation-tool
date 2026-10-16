# PROMPT — app fixer — 2026-10-14 — everything still open, in one queue

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy
may be out of date) first.

This one prompt replaces pasting the items one by one. Each item below has its own full brief in
the main folder; read it before starting that item, because it carries the detail.

**Before each item, check origin/main and skip whatever has already landed.** You may already be
part-way through item 58b. Land each item separately (its own commit and landing) before
starting the next, so finished work is never held hostage by the next item. After each landing,
check once that it landed; no wait loops.

## The queue, in order

### 1. The number formatting on the valuation page (small; do it first)

This was added to the top of `PROMPT_appfixer_2026-10-14_item58b.md` **after** item 58b may
already have been started, so it was likely missed. On MSFT the company panel prints
"$3,962,939,637,760" and "$331,839,000,000".

- **Cause:** `app.js` (~lines 500–501) calls `money(p.market_cap * 1e6, 0)` and
  `money(p.revenue * 1e6, 0)` and never `mcap()`.
- **Same defect:** the growth-lens sentence (~line 649) prints "$395,246mm".
- **Fix:** route all three through `mcap()` so they read $3.96T, $331.84B and $395.25B. Sweep
  `app.js` for any other `money(` call on a value of $1M or more, add a test that fails on the old
  lines, and verify it live on MSFT.

### 2. Finish item 58b — `PROMPT_appfixer_2026-10-14_item58b.md`

The live-path cycle runner, the paper slot on Alpaca paper running the identical code, the
switch of the paper books from Tradier, dry-run parity, alerts and the status page, the feed-gap
measurement, and dividends for paper books.

- Item 58's rules all stand: the three events, no loss stops, broken input means no orders plus
  an alert, numbered slots, separation.
- No lane ever sets a percentage, enters a key, or triggers a live order.
- **If Don's paper keys are not on Render yet**, say so with the exact steps and do everything
  that does not need them.

### 2b. Follow-up to 58b (it landed as `d933f12`, `3f95b57`): let the paper slot actually trade paper

`pending_workflows/live-cycle.yml` ships with no `?run=1`, so the cycle is a dry run for
**every** slot, the paper slot included. As shipped, the paper slot will never place a paper
order, and Don cannot watch the 2026-10-22 rebalance go through on paper, which was the point of
the paper slot.

- **Add a paper-only send mode**, e.g. `POST /admin/live-cycle?run=paper`. It transmits orders
  for the paper slot only, on the paper client only, and live slots stay dry run whatever their
  settings.
- **Live sending stays `?run=1`** and remains reserved for after the auditor review.
- **Pin it with tests:**
  - `run=paper` cannot reach the live client;
  - `run=paper` sends nothing for a live slot, even one fully armed;
  - `run=1` behaves exactly as before.
- **Update `pending_workflows/live-cycle.yml`** to call `?run=paper`, and give Don the
  one-at-a-time steps to install it.

### 3. Item 59 — `PROMPT_appfixer_2026-10-14_item59.md`

Alpaca market data becomes the primary price source wherever it measures at least as good,
measured first.

- The Index record switches at a segment boundary, with base and mark from one vendor. Use the
  2026-10-22 rebalance if ready, otherwise record the seam.
- Fundamentals stay on Yahoo with the SEC fallback.
- Do not touch the live-path trading code beyond its price inputs.

### 4. Item 60 — `PROMPT_appfixer_2026-10-14_item60.md`

The valuation page opens on a **valuation verdict**: Undervalued, Fairly valued or Overvalued vs
our model, from the price against bear/base/bull, with the range, confidence, the two reads, and
what the price assumes.

- No buy, sell or target-price wording anywhere.
- The rest of the page is ordered from most to least relevant, with the deep model detail behind
  "Show the full model".

### 5. Item 61 — `PROMPT_appfixer_2026-10-14_item61.md`

The Proof page leads with the Valquo Index's own backtest and the forward track's honest status.
The research decile follows as the evidence the ranking works. Fix the "per quarter" label on
the annual 6.07%.

## After the queue

One plain-words summary for Don covering all five items:

- what changed;
- what is verified live;
- anything you could not do and why;
- what Don has to do next: the auditor review (`PROMPT_auditor_live_path.md`) before any live
  key, and the Render steps if his paper keys are not there yet.
