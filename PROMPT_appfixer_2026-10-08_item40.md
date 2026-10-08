# PROMPT — app fixer — 2026-10-08 — item 40

Read `DECISIONS.md` first.

## (a) Measure the FMP seam (do NOT enable it)

Item 39 showed the price-history chain has no rung that is not Yahoo: yesterday Yahoo refused the
runner outright (401 "Invalid Crumb") and the fallback could not help, because its own primary is
the same Yahoo call. `prices.py` has an FMP rung that is configured and deliberately off, and its
docstring's precondition is "measure the seam first". Do that measurement:

- On the current hot-list universe (or a stated sample of at least 200 names, including banks,
  REITs, ADRs and recent splitters), pull the same window from Yahoo and from FMP and compare:
  as-traded closes, the 52-week high on each basis, and split/dividend handling. Report agreement
  rates, the worst disagreements by name, and anything systematic.
- Report whether the FMP key on the service works and what plan/limits it has, without printing
  the key.
- State plainly whether FMP is safe to enable as a third rung for the Dip Detector and the scan,
  and what it must never feed (anything append-only, such as the forward track record).

Nothing is enabled in this item. Don decides after reading the numbers.

## (b) and (c) still held until DECISIONS.md records Don's ruling

The 52-week-high basis mix (adjusted high against an as-traded price), the intraday scheduler,
and the public pages (until r1's canonical move lands).

Done means on origin/main, with a plain-words summary for Don.
