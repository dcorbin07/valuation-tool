# PROMPT — app fixer — 2026-10-15 — item 62: the Alpaca seam "passed" on three bars; make it measure before it can pass

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your item 59
commit `22f1c92` first.

Don ran `POST /admin/alpaca-seam?run=1` on 2026-10-15 at 22:27Z. It wrote
`/app/data_export/ALPACA_SEAM.json` and returned `switch.allowed=false`, with the reason "the seam
measurement passed, so the switch is AVAILABLE". **The pass rests on almost nothing**, so Don is
told not to set `PRICES_PRIMARY_ALPACA` until this is fixed.

## What the response shows

- **The closes leg** passed at agree_rate 1.000 "across 3 names". It compared **ET, GBTC and TSM,
  one bar each, all on 2026-10-15**. The whole run spent **6 requests**. That is not a daily-close
  comparison of the 222-name sample over any history; it is three quotes on one day.
- **`vs_recorded`** (against the bound Index series) is **UNMEASURED**: "no name had overlapping
  dates on both vendors". This is the leg that matters most for switching the Index record, and
  the switch reported "available" without it.
- **Coverage** read 212 of 220 at 96.4%.
  - The OTC names (CYATY, KBGGY, LKNCY, OBICY, VBREY) are legitimately refused, because the free
    plan returns 403 for OTC.
  - **AVB, BK and EQR are NYSE-listed and should be covered.** Find out why they were reported
    missing: pagination not followed, a batch cut off, or a symbol-format issue. Until that is
    known, the coverage figure cannot be trusted.
- **Every 52-week high** reads raw equal to adjusted (60 names, median gap 0). That may be right,
  since the splits in the sample are more than a year old. Confirm it is not both bases returning
  the same series, using a name with a dividend inside the window.

## Fix

1. **The closes leg compares real history.** Use the daily closes of all 222 sample names over a
   stated window (at least 250 trading days), on both `adjustment=all` and `raw`, against
   yfinance's adjusted and as-traded closes. Follow pagination to the end and count requests from
   the response headers.
2. **`vs_recorded` is measured, and it is required for the Index switch.** Price the Index's held
   names through Alpaca at `adjustment=all` on every recorded date, recompute those rows with
   `contract_row`'s own arithmetic, and compare them to the recorded values. Report agreement per
   row and the largest gap in basis points.
3. **A pass needs a floor of evidence, declared in code with its reason.** For example: at least
   200 names and 40,000 comparable bars on the closes leg, and every recorded row on
   `vs_recorded`. Below the floor the result is UNMEASURED, never passed. **`switch.allowed` stays
   false unless both legs pass.** Add a test that fails on the current three-bar pass.
4. **Explain the AVB, BK and EQR misses**, fix the cause if it is ours, and re-state coverage by
   category.
5. **Give Don the one curl command to re-run it**, with the masked admin-token steps, and say
   in plain words what a pass and a fail would mean for the 2026-10-22 rebalance.

Nothing switches. Done means on origin/main, with a plain-words summary for Don.
