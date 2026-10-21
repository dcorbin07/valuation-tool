# PROMPT — app fixer — 2026-10-19 — item 75 (URGENT, before item 74): build the rebalance book AS OF a date, and refuse a book built after its event

**Land this before Thursday 2026-10-22, 12:00 ET. It comes before items 74 and 73.**

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and
`REBALANCE_RUNBOOK_2026-10-22.md` first. **Do not edit `DECISIONS.md`.**

## The problem, found 2026-10-19

The rebalance is dated 2026-10-22 and runs on the evening of 10-23. That evening is the only safe
window to append the event: after the 10-22 track row exists, and before track-row writes the
10-23 row (~03:07 UTC on 10-24).

Path B builds with:

```
python -m valuation.edge.valquo_index --full-universe data/backtest --config taxable --out data/valquo_index.json
```

`_full_universe_rows` calls `score_universe_now(prov, tickers)` **with no `as_of`**, so the book is
scored as of the export's **latest** close. Sharadar's recommended pull time is about 5:20 PM ET
on the same day, so the 10-23 7pm refresh will very likely carry the **10-23** close. That has two
consequences:

1. The runbook's freshness gate (`as_of == 2026-10-22`) stops the rebalance, and there is no way
   to build as of 10-22. The CLI has no `--as-of`, though `score_universe_now` already accepts one.
2. If the gate were skipped, `index_mark.append_rebalance` would let the book through. Its
   freshness check refuses only a book too **old**
   (`trading_days_between(as_of, d) > REBALANCE_MAX_STALE_DAYS`), never one built **after** its
   event date. A 10-23 book dated 10-22 is a one-day look-ahead, and nothing downstream could
   tell.

## The fix

1. **`--as-of YYYY-MM-DD`** on the `valquo_index` CLI, passed through `_full_universe_rows` to
   `score_universe_now(as_of=...)`.
   - Verify, rather than assume, that **every** input is cut at that date: prices, SF1 by
     `datekey`, DAILY market cap, SF3/13F and insiders by filing date, and the stale-price cutoff.
   - Test with a fixture export: adding a later day of data must leave the `--as-of` book
     bit-identical.
   - On the real `data/backtest`, show locally that `--as-of 2026-10-01` and `--as-of 2026-10-02`
     differ only as expected. Commit no licensed rows.
   - The payload's `data_as_of` and `scan_date` must equal the requested date.
   - Refuse a date that is not a trading day in the export, or that is later than its newest close.
2. **The 30% band still applies.** `held` still comes from the book at `--out`. Pin it:
   `no_trade_band.applied` stays true with `--as-of`.
3. **The door refuses a book built after its event.** `append_rebalance` refuses when the book's
   as-of date is **later** than the event date, with a plain reason. The same rule applies on the
   CLI and on `POST /admin/track-rebalance`. Test it fails on the old code.
4. **Runbook.**
   - Add `--as-of 2026-10-22` to Path B's build command and to Arm 2's.
   - Fix the stale `--config` help text: it says a 20% band and the code uses 30% (runbook §6.2).

## Rules

- No construction change.
- Nothing appended or published.
- No key or token printed.
- No `.github` change.

## Done

On origin/main, with a plain-words summary for Don. Its first line says whether Friday's command is
now:

```
python -m valuation.edge.valquo_index --full-universe data/backtest --config taxable --as-of 2026-10-22 --out data/valquo_index.json
```
