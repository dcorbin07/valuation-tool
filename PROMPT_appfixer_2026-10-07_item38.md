# PROMPT — app fixer — 2026-10-07 — item 38 (after item 37)

Read `DECISIONS.md` first — Don ruled on both held items on 2026-10-07.

## (a) Dip Detector: a separate group for companies whose health is not scored

Names whose ONLY failing check is a health sub-score withheld by regime (financial, reit,
regulated — item 26's rule) move out of "rejected on health" into their own group, shown on the
page under the label **"Health not scored for this kind of company (banks, insurers, REITs,
regulated utilities)"**, with one plain sentence saying the model's health metrics do not describe
these businesses, so the user must judge that part. Rules:

- They must still pass every OTHER check (depth, the disqualifier checks, any sub-score that IS
  scored and below its floor). A name below a floor elsewhere stays rejected.
- They are never counted as healthy anywhere: not in the main rows, not in any count, digest or
  export that implies a health pass.
- The identity the live check asserts gains the new bucket and must still hold exactly, capped 0.
- Verify live at 0.10 / 0.20 / 0.30 and report how many names land in the new group.

## (b) Public pages: restate once, after r1 moves the canonical backtest

Don approved moving the canonical backtest to the corrected universe and restating the public pages
once. r1 lands the move and hands you a table of every public figure, old → new. When it lands,
the same day: update the wording and every transcribed literal (/proof, /methodology, the Index tab
including the deeper drawdown, the landing tiles, `index_book_measured.py`), replace the "not a
survey of survivors" sentence with an accurate description of the corrected universe, keep the
"research decile is not the Index" disclosures, and keep DECISIONS.md's rule (no "+32%", no
"beats SPY"). Until r1's move lands, change none of these pages. A test should fail if any page
still quotes a figure from the old panel after the move.

Done means on origin/main, verified live.
