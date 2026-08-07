# HANDOFF — S1, S2, S4: the three defects that decide which names surface (2026-08-06)

Everything shipped in this lane over the last week stopped the product printing wrong numbers.
None of it made a pick better. These three are the first items that change **which names reach
the hot list**.

---

## PRE-COMMITMENT — written and committed BEFORE any arm was run

Committed on its own so the git history evidences the ordering, as in Parts 2–5 of
`HANDOFF_live_data_bugs.md`.

### What I already know before running anything (verification, not results)

Two of the three audit claims were checked against the code first, because the brief says
verify rather than obey:

- **S4 is TRUE.** `settings.py:75-77` — `WEIGHTS_ESTABLISHED` has keys `value, quality,
  momentum, insider, low_risk, capital_discipline, sentiment, size, institutional`. **No
  `growth`.** `WEIGHTS_SPECULATIVE` (`:78-80`) does carry `growth: 0.125`. The backtest runs
  the established bucket, so the theme is computed (`factors.py:229`) and never scored.
- **S2's premise is FALSE as written.** The audit says `cash_op_prof` is "never registered in
  `NUMBER_THEME`", "invisible to the coverage guard", and "the single cheapest **untested**
  signal in the repository". `settings.py:196` says otherwise, in the same file the audit
  cites: *"Rejected and deliberately NOT listed: cash_op_prof (t +0.22, no signal)."* It was
  tested and rejected. **But that measurement was taken on a 400-name panel**, and CLAUDE.md's
  METHODOLOGY RULE says 400/800-name subsets are smoke tests, never a verdict. So S2 is not
  "untested" — it is **tested at sub-verdict scale**, which is a different and narrower reason
  to re-run it.

### Thresholds, fixed now

All three are scored against **X7's calibrated bars**, not the retired conventions: theme IC
*t* **2.71**, long-short *t* **2.14**, top-decile alpha margin **1.95pp**, PBO **< 19.7%**,
Deflated Sharpe **0.72** at N = 84. Using the old 2.0 would manufacture a survivor.

**S4 — adding `growth` to `WEIGHTS_ESTABLISHED`.**
Measured with the shipped, pinned `holdout_theme_validate` on the theme set *including*
`growth`, read in the direction that matters here: **zeroing growth must COST at least the
standing margin — ≥ 0.25 of long-short *t* AND ≥ 100bps of top-decile alpha — in BOTH split
directions.** That is the exact inverse of the `low_risk` test that zeroed a theme, run through
the same function, so the standard is the one the project already accepted.
- **ADOPT** only on that double-direction result.
- Anything weaker is **NULL** and `WEIGHTS_ESTABLISHED` is left alone. A near miss is a null.
- Separately and reported either way: is the *speculative* branch better **without** growth?

**S1 — the value theme's inputs.** Three arms, one column changed each, through
`holdout_compare_panels` at the standing margins (`MIN_HOLDOUT_ALPHA_GAIN = 0.01`,
`MIN_HOLDOUT_TSTAT_GAIN = 0.25`), verdict `adopt` required in BOTH directions:
- **S1a** drop `book_to_price` (4 inputs → 3).
- **S1b** swap `book_to_price` → `neg_ev_ebitda` (4 → 4, a substitution).
- **S1c** is the same question as S1a and is reported as such rather than counted twice.

**S2 — `cash_op_prof`.** Coverage FIRST, before any IC is quoted, per the standing rule that
cost this project five empty factors. Then, in order, and each must pass before the next is
asked:
1. coverage ≥ the 5% floor `signal_coverage()` enforces;
2. theme-level IC *t* ≥ **2.71** (calibrated), not the retired 2.0;
3. correlation vs `gp_on_capital` and `fcf_margin` — if |r| > 0.7 with either, it is tested as a
   **replacement**, never an addition, for the dispersion-compression reason that killed the
   EV/Sales promotion;
4. the held-out gate in both directions.
Expected outcome, stated in advance so a surprise is visible: **NULL.** The 400-name run put it
at *t* +0.22, and the honest prior is that a full-universe run moves that a little, not past 2.71.

### Control group — checked before committing, per the lesson from Part 4

**There is no do-no-harm bound to commit here, and I am not going to invent one.** These are
signal-inclusion tests, not refactors: every arm deliberately changes the ranking for every
name, so no set of names exists that the change is mechanically incapable of touching. Part 4
committed a bound whose "control group" was a proxy and it breached; Part 5's held because the
control was the defining property. Here the honest statement is that **the held-out gate IS the
test** — decide on one half, measure on the other, both directions — and there is nothing else
to hold fixed.

### Trial accounting

Every arm below is a trial and goes to `RESEARCH_LOG.md`: S4 (2 arms: established-with-growth,
speculative-without-growth), S1 (2 distinct arms), S2 (1 arm). **5 new equity trials.** N is 84
today; the new N is reported in the results section, and the Deflated Sharpe bar moves with it.

### What "better" means, and what would make me reject a winner

The deliverable is the book, not the t-stat. I will report the **top 25 before vs after by
name**, and whether the change tilts by size, sector or coverage. Don's read — the tool surfaces
solid businesses trading down, where the weakness looks like sentiment rather than deterioration,
with value and quality carrying the composite — is the design intent. **If an arm improves a
statistic and moves the book away from that, I will say so and it counts against the arm.**
