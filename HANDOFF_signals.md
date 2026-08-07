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

---

## RESULTS — measured after the pre-commitment above (fee0fbc)

**Nothing changes the book. All three items came back NULL or REJECTED against their
pre-registered thresholds**, and the one code change that ships (S2's registration) is
explicitly a visibility change that leaves the composite bit-identical.

That is a disappointing answer to "make the picks better" and it is the honest one. What the
three arms did produce is a clean, repeated demonstration of the standing rule the brief put
second — **a theme's own IC and the composite it feeds move in opposite directions** — measured
three separate times below.

### The panel these were run on, and the check that it is the right one

Full universe, `lookback_years=18` (the value `run_backtest` uses — my first build used the
function default of 6 and produced a 21-date panel, which is not verdict-grade; caught and
rebuilt). **113,945 rows, 2,710 names, 69 rebalance dates, 2009-01-15 → 2026-01-28.**

The reproduction check that makes the rest believable: with `growth` absent, this panel scores
**long-short t 2.8360640685320595, top-decile alpha 7.174%** — which is CLAUDE.md's shipped
headline (t 2.836, alpha +7.17%) to the digit.

### Coverage first, as the standing rule requires

| signal | coverage |
|---|---|
| cash_op_prof | **95.3%** |
| book_to_price | 100.0% |
| neg_ev_ebitda | 95.6% |
| earnings_yield / fcf_yield / ebit_ev | 97.9% / 96.8% / 97.4% |
| revenue_growth / growth_accel | 92.8% / 89.5% |

**One signal is below the 5% floor and the guard caught it: `govt_award_momentum` at 4.75%.**
It is registered to the `growth` theme but is *not* in `factors.py`'s growth mean, so it is
measured-only and does not corrupt anything today — but it is a wired signal that is
effectively empty, which is the exact class of defect that cost this project five factors.
Logged in BUGS FOUND, not fixed here (it is not one of S1/S2/S4).

### Theme IC on the corrected panel, against X7's calibrated bar of 2.71

| theme | median IC | t | clears 2.71? |
|---|---|---|---|
| quality | +0.0356 | **3.10** | **yes** |
| capital_discipline | +0.0297 | **2.76** | **yes** |
| institutional | +0.0144 | 1.55 | no |
| momentum | +0.0212 | 1.31 | no |
| value | +0.0110 | 0.84 | no |
| growth | +0.0181 | 0.75 | no |
| low_risk | +0.0247 | 0.46 | no |
| insider | −0.0052 | −0.24 | no |
| size | −0.0109 | −0.30 | no |

Two of nine clear, which reproduces the CLAUDE.md table exactly.

---

### S4 — `growth` in `WEIGHTS_ESTABLISHED`. VERDICT: **NULL**

**The audit's observation is TRUE**: `settings.py:75-77` has no `growth` key, `WEIGHTS_SPECULATIVE`
carries 0.125, and the backtest runs the established bucket. So the theme is computed and never
scored on profitable names. It reads as an omission, and it is now a tested decision.

Pre-registered rule: adopt only if **zeroing growth COSTS ≥0.25 long-short t AND ≥100bps alpha in
BOTH split directions**.

| direction | Δ long-short t from zeroing growth | Δ alpha | costs the margin? |
|---|---|---|---|
| decide early → measure late | **−0.263** | −0.48pp | t yes, alpha **no** |
| decide late → measure early | **+0.549** | +0.38pp | **no — zeroing HELPS** |

**Growth helps in one half and hurts in the other.** That is the signature of noise, not of an
omitted factor, and it is why the pre-registered rule requires both directions.
`holdout_theme_validate`'s own verdict for growth is `rejected`.

On the full panel adding growth is a hair better — LS t 2.836 → 2.853, alpha 7.174% → 7.244%,
monotonicity −0.891 → −0.964 — but that is in-sample, an order of magnitude below the margin,
and exactly the kind of number the held-out gate exists to refuse.

**The reverse question the audit also asked:** is the speculative branch better *without* growth?
`holdout_theme_validate` on the speculative theme set returns `rejected` for growth — no evidence
to remove it there either. So growth stays out of established and in speculative, and that is now
recorded as a decision rather than an omission.

**And the book argues against it too.** Adding growth keeps only **15 of 25** top names and pulls
the median market cap **$1.09B → $1.73B**, swapping deep-value names (BETR, BODI, DDD, ECO, INTR,
MBI, OPEN, POWL, STAA, TERN) for momentum/thematic ones (IREN, CIFR, STEM, SEDG, BE, ORLA, ARIS,
APLS, GEG, LGND). Don's read of what the tool does well is *solid businesses trading down where
the weakness looks like sentiment*. **This arm moves the book away from that.** Statistically null
and directionally wrong for the product is an easy decline.

### S1 — the value theme's inputs. VERDICT: **REJECTED**, both arms

**I got this wrong on the first pass and the correction changed the numbers' signs.** My first
harness recomputed `value` as the established recipe for *every* row; the shipped column is
`np.where(bucket == 'established', value_est, value_spec)` and **23,412 of 113,945 rows are
speculative**. The flawed pass reported dropping `book_to_price` as a small *improvement*; the
faithful pass (verified bit-identical to the shipped `value` column before changing anything)
reports it as a *deterioration*. Both passes reject; only the faithful numbers are below.

| arm | Δ LS t (early) | Δ LS t (late) | value theme IC t | full-panel LS t | verdict |
|---|---|---|---|---|---|
| current (4 inputs) | — | — | **0.84** | 2.836 | — |
| **S1a** drop `book_to_price` | **−0.207** | **−0.079** | **1.57** | 2.685 | reject |
| **S1b** swap for `neg_ev_ebitda` | **−0.270** | +0.012 | **1.37** | 2.741 | reject |

**This is the finding.** Removing `book_to_price` nearly doubles the value theme's own IC t
(0.84 → 1.57) **and makes the composite worse in both held-out directions.** The audit's
hypothesis — that a flat input is "diluting three genuinely informative inputs" — is measured
false: the flat input is doing work in the composite that its own IC cannot see. That is standing
rule 2 (rank-IC is invariant to a monotone rescale; the composite is a weighted sum and is
scale-sensitive), and this is the third time the project has hit it after P6 and the EV/Sales
promotion.

S1c ("does it do better with three inputs than four") is the same question as S1a and is not
counted as a separate trial.

Book effect: S1a keeps 23/25 names, S1b 22/25 — small, and moot given both reject.

### S2 — `cash_op_prof`. VERDICT: **NULL** (predicted in advance)

**The audit's premise is false.** It calls this "the single cheapest **untested** signal in the
repository" and says it is "invisible to the coverage guard". `settings.py:196` — the same file
it cites — records *"Rejected and deliberately NOT listed: cash_op_prof (t +0.22, no signal)."*
It was tested. The legitimate reason to re-run was narrower and the audit does not state it:
**that measurement was on 400 names**, and CLAUDE.md's methodology rule says a subset is a smoke
test, never a verdict.

Re-run on the full 2,710-name / 69-date panel, gated in the pre-registered order:

| gate | result |
|---|---|
| 1 — coverage ≥ 5% floor | **PASS, 95.3%.** It was never empty or invisible |
| 2 — standalone IC t ≥ **2.71** (calibrated) | **FAIL. median IC +0.0026, t +0.84** |
| 3 — correlation vs quality's holdings | gp_on_capital **0.27**, fcf_margin **0.31**, roic 0.44, op_margin 0.37 — all far below 0.7, so it is genuinely distinct |
| 4 — held-out gate | **reject** (Δ LS t +0.200 / −0.112) |

**The 400-name rejection replicates at full-universe scale** (t +0.22 → +0.84, still nowhere near
2.71). And gate 3 makes the null more interesting rather than less: this is *not* a redundant
signal being crowded out — it is orthogonal to what quality holds and still carries nothing, the
same shape as the EV/Sales diagnostic. Folding it into the quality mean *lowers* that theme's IC
t from 3.10 to 2.91 and the composite's long-short t from 2.836 to 2.790.

**What ships from S2, and why it is not nothing:** `cash_op_prof` is now **registered in
`NUMBER_THEME` as measured-but-not-scored**, following the `roe_ttm`/`roic_ttm` precedent already
in that file. Registering a number gives it a `z_` column and puts it in the coverage guard and
the per-signal IC table; it only *scores* if `factors.py` names it in a theme mean, and the
quality mean does not. **Verified: the composite is bit-identical either way — long-short t
2.8360640685320595 with and without.** That answers the audit's real complaint (a signal invisible
to the guard, with six columns carried in `_KEEP` solely to compute it) at zero risk to the book.

### The book: current top 25 (2026-01-28 rebalance, shipped weights)

`FOSL, INDV, NKTX, BNR, OPEN, SSL, SCHL, ALXO, WDH, BODI, CGAU, CTRI, HUT, TTI, PMVP, POWL,
TNGX, DDD, STAA, MBI, NRGV, ECO, BETR, INTR, TERN` — median market cap **$1.09B**.

**Unchanged by this session**, since nothing was adopted.

One observation worth recording rather than acting on: at equal shipped weights on the panel's
own universe this is a **micro/small-cap deep-value book**, not obviously the "solid businesses
trading down" the product is understood to surface. That is a statement about the *backtest
panel's* ranking with no market-cap floor, not about the live hot list, which screens a different
universe. I am flagging the discrepancy rather than claiming the live book looks like this —
confirming that would need a live scan, which is the app lane's surface.

### What I did NOT do, and why

- **Did not adopt anything.** Three arms, three failures against thresholds fixed in advance. A
  near miss is a null; S4's one-directional −0.263 t is exactly the kind of result that becomes a
  false positive if you read it after the fact.
- **Did not re-tune any threshold** after seeing results, and scored everything against X7's
  calibrated bars — under the retired 2.0 convention, `capital_discipline` and `quality` still
  clear and nothing else changes, but S2's t +0.84 would have looked closer than it is.
- **Did not touch `factors.py`'s theme means**, `valuation/edge/**`, `valuation/web/**` or
  `valuation/report/**`.
- **Did not chase `govt_award_momentum`** — a real coverage failure, but not one of S1/S2/S4, and
  inventing scope mid-task is how the last two sessions' bounds became unmeasurable.

### Trial accounting (M1)

5 new equity trials logged to `RESEARCH_LOG.md`: S4, S4b, S1a, S1b, S2.
**Equity N: 104 → 109** (CLAUDE.md still says 84; the log had already reached 104 before this
session). √(2·ln 109) = **3.063**, still above the Harvey–Liu–Zhu hurdle of 3.0. The Deflated
Sharpe bar tightens accordingly on the next full run, which picks the count up automatically.

## BUGS FOUND

1. **`govt_award_momentum` is below the coverage floor at 4.75%** on 113,945 rows — the guard
   fires on every run. It is registered to `growth` in `NUMBER_THEME` but absent from
   `factors.py`'s growth mean, so it is measured-only and corrupts nothing today. Still a wired
   signal that is effectively empty, which is the exact class that cost this project five factors.
2. **The audit's S2 is factually wrong in two of its three claims** — `cash_op_prof` is not
   untested (it was rejected at t +0.22) and not invisible for lack of computation (it is 95.3%
   covered once registered). Its *third* claim — six columns carried in `_KEEP` solely to feed a
   signal nothing consumes — was true and is now addressed by registering it as measured.
3. **`build_fundamental_panel`'s default `lookback_years=6` silently produces a 21-date panel**,
   while `run_backtest` passes 18 and produces 69. Anyone calling the builder directly for a
   study gets a third of the window with no warning. My first build hit this.
4. **My own S1 harness changed the speculative branch while testing the established one.** Caught
   by a sanity check (rebuilt base must equal the shipped `value` column) that I only added on the
   second pass. The flawed pass would have reported S1a as a small improvement; the faithful one
   reports a deterioration. Verdicts agreed, signs did not.
