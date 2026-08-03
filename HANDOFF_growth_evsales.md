# HANDOFF — EV/Sales as a weighted panel value factor

Agent: Claude Code (growth-valuation lane). Date: 2026-08-03.
Task: `PROMPT_growth_evsales.md` — promote EV/Sales to a weighted value-theme input, A/B it on
the full universe through the same gate every other factor faces, and report an honest verdict.

**VERDICT: REJECTED.** EV/Sales and EV/EBITDA are now wired, measured and permanently
coverage-checked, but adding them to the established value branch does not improve the book and
fails the held-out gate in both directions. `CONFIG.value_ev_multiples` ships **OFF**.

A second, unrelated defect was found while doing this — enterprise value is never refreshed to
the rebalance date — and it is reported in section 6. That one is a genuine latent bug.

---

## 0. The premise needed correcting first

The prompt described EV/Sales as "a real value signal sitting outside the current factor set".
It is not outside the factor set. The value theme is **bucket-split**:

| branch | applies to | inputs |
|---|---|---|
| `value_est` | `established` (positive profit) | earnings_yield, fcf_yield, ebit_ev, book_to_price |
| `value_spec` | `speculative` (no positive profit) | **neg_ev_sales**, neg_ps, book_to_price |

So `neg_ev_sales` has been a wired, measured value input all along — it has simply **never
scored a single profitable company**. On the last full run it was the second-strongest of the
six value inputs (median IC +0.0214, IC t +2.11) while `book_to_price`, which feeds *both*
branches, is dead (median IC −0.0007, t +0.15).

`ev_ebitda` genuinely was absent: the panel never computed it.

The real question is therefore narrower and better posed: **does extending the two EV multiples
to the ESTABLISHED branch improve the composite?** That is what was tested.

---

## 1. What was built

- **`ev_ebitda` in the panel** (`_sf1_to_metrics`). USD-converted through the P7 divisor.
  **Positive EBITDA only** — a loss-maker's multiple is negative and negating it (higher =
  cheaper) would rank the deepest losses as the greatest bargains.
- **The same sign guard in `factors.py`**, because FMP returns `enterpriseValueMultipleTTM`
  unguarded and every provider passes through `build_frame`. All three live providers already
  supply `ev_ebitda`, so adoption would not have left a live-path gap.
- **`neg_ev_ebitda` registered in `NUMBER_THEME`** → z-scored, IC-measured and coverage-checked
  on every run from now on, regardless of the verdict.
- **`CONFIG.value_ev_multiples`** (default **off**) adds both EV multiples to `value_est` only.
- **`bucket` persisted on every panel row.** `value` means different things either side of the
  split, so a value diagnostic that ignores the bucket averages two different factors together.
- **`valuation/edge/ev_multiples_study.py`** — the A/B: coverage, per-bucket IC, correlation,
  the incremental test, the composite A/B and the held-out gate.
- **`EDGE_PANEL_PICKLE`** — optional panel dump, so a follow-up study does not re-pay the
  ~12-minute build.
- **20 tests** in `tests/test_ev_multiples.py`.

### Methodology note — why the A/B is exact

The flag only changes *which z-columns get averaged into `value`*, and standardization happens
strictly before the composite. So the WITH arm is reconstructible from a panel built WITHOUT it.
This was not assumed — it was verified three ways:

1. `test_value_is_recomputable_from_the_stored_z_columns` pins it on synthetic data.
2. Two independent full CLI runs produced panels differing in **exactly one column** (`value`),
   and the reconstruction matched the real WITH panel on **all 136,478 rows**.
3. The study's WITHOUT arm reproduces the official `BACKTEST_RESULTS.json` to four decimals
   (LS t 3.3957, alpha 11.819%, monotonicity −0.9515).

---

## 2. Coverage — checked FIRST, per the rule

Full universe: **136,478 rows / 2,710 names / 110 dates** (108,773 established, 27,705 speculative).

| signal | overall | established | speculative |
|---|---|---|---|
| z_earnings_yield | 98.0% | 100.0% | 90.3% |
| z_fcf_yield | 97.0% | 99.2% | 88.6% |
| z_ebit_ev | 97.8% | 99.9% | 89.5% |
| z_book_to_price | 100.0% | 100.0% | 100.0% |
| **z_neg_ev_sales** | 96.3% | **99.6%** | 83.2% |
| **z_neg_ev_ebitda** | 82.8% | **98.0%** | 23.2% |
| z_neg_ps | 96.4% | 99.7% | 83.5% |

The change would newly score **108,344 rows — 79.4% of the panel** — that EV/Sales has never
touched. This is not a coverage-starved factor being asked to carry weight; it is well
populated and the change genuinely reaches most of the book.

`neg_ev_ebitda`'s 23.2% speculative coverage is expected and correct: loss-makers mostly have
negative EBITDA, which the guard drops.

---

## 3. Per-number IC, overall and inside the branch the change touches

| signal | all rows medIC | all t | **established** medIC | **established** t |
|---|---|---|---|---|
| z_earnings_yield | +0.0078 | +2.41 | +0.0246 | +2.04 |
| z_fcf_yield | +0.0135 | +3.17 | +0.0140 | +1.90 |
| z_ebit_ev | +0.0219 | +2.29 | +0.0179 | +1.86 |
| z_book_to_price | −0.0007 | +0.15 | +0.0006 | +0.35 |
| **z_neg_ev_sales** | +0.0214 | +2.11 | **+0.0350** | +1.72 |
| **z_neg_ev_ebitda** | +0.0236 | +1.91 | +0.0208 | +1.70 |
| z_neg_ps | +0.0391 | +1.51 | +0.0321 | +1.25 |

**The lead was real.** Restricted to established names, EV/Sales has the *highest median IC of
all six value inputs* — ahead of earnings yield. Nothing here says it is a weak signal.

---

## 4. Correlation, and the test that actually decides it

Mean per-date Spearman on established rows (per-date rather than pooled: a pooled figure blends
cross-sectional structure with 18 years of drift in the level).

| pair | corr |
|---|---|
| z_ebit_ev vs z_neg_ev_ebitda | **+0.864** |
| z_neg_ev_sales vs z_neg_ps | +0.905 |
| z_earnings_yield vs z_neg_ev_ebitda | +0.663 |
| z_neg_ev_sales vs z_neg_ev_ebitda | +0.597 |
| z_ebit_ev vs z_neg_ev_sales | +0.468 |
| z_book_to_price vs z_neg_ev_ebitda | +0.355 |
| z_earnings_yield vs z_neg_ev_sales | +0.282 |
| z_book_to_price vs z_neg_ev_sales | +0.255 |
| z_fcf_yield vs z_neg_ev_ebitda | +0.242 |
| z_fcf_yield vs z_neg_ev_sales | +0.177 |

Correlation alone is not the answer — the prompt asked whether it "adds incremental information
ratio or just duplicates them", so that was measured directly. Each date, regress the candidate
on the four incumbent value z-scores and keep the **residual** — the part of EV/Sales that
book/earnings/FCF cheapness cannot explain — then measure the residual's IC like any other signal.

| candidate | raw medIC | raw t | residual medIC | residual t | R² explained by incumbents |
|---|---|---|---|---|---|
| z_neg_ev_sales | +0.0350 | +1.72 | **−0.0026** | **+0.67** | 15.7% |
| z_neg_ev_ebitda | +0.0208 | +1.70 | **−0.0006** | **+0.20** | 31.1% |

**This is the finding.** The incumbents explain only **15.7%** of EV/Sales's variance, so it is
*not* a linear duplicate. But the 84% that is genuinely new **carries no predictive power at
all**. Its entire forecasting content already lies inside the span of what the theme had; what
is distinctive about it is noise. EV/EBITDA is worse — 31.1% explained, residual t +0.20, and
+0.864 correlated with `ebit_ev`, which is nearly the same ratio with a different profit line.

---

## 5. The A/B, through the full gate — WITH vs WITHOUT

Two independent full-universe runs (2,827 tickers → 2,710 with usable history, 110 dates),
each through CPCV, held-out both halves, coverage and sanity.

| metric | WITHOUT (shipped) | WITH EV multiples | verdict |
|---|---|---|---|
| **value theme medIC** | +0.0211 | **+0.0248** | better |
| **value theme IC t** | +1.461 | **+1.708** | better |
| long-short t | **+3.396** | +3.345 | worse |
| long-short /yr | **+17.16%** | +16.55% | worse |
| top-decile alpha (gross) | **+13.76%** | +13.06% | worse |
| top-decile alpha vs EW | **+11.82%** | +11.14% | worse |
| net alpha after costs | **+11.44%** | +10.78% | worse |
| breakeven bps (one-way) | **235** | 226 | worse |
| net Sharpe | **1.113** | 1.101 | worse |
| monotonicity | **−0.952** | −0.939 | worse |
| **PBO** | **6.7%** | **13.3%** | worse (doubled) |
| Deflated Sharpe | 99.99984% | 99.99618% | ~equal (both saturated) |
| CPCV adopt | no (current-default) | no (current-default) | unchanged |

**The value theme gets better and the book gets worse.** Every construction metric moves the
wrong way and PBO doubles.

### Held-out, both directions — the deciding test

Same protocol as `holdout_theme_validate`: split the 110 dates by time, embargo the boundary,
measure on the half that informed nothing, run it both ways. Against the **pre-specified**
margins (Δt ≥ +0.25, Δalpha ≥ +100bps) committed before P6 and not re-chosen here:

| half | Δ long-short t | Δ top-decile alpha | clears? |
|---|---|---|---|
| early (55 dates) | −0.011 | −0.91% | no |
| late (54 dates) | −0.125 | −0.51% | no |

**NOT_REPLICATED — and both directions are negative**, so this is not a change that narrowly
missed a margin. It is worse on data it never saw, twice.

This test is cleaner than the usual theme-zeroing one: there is no "decide" half, because the
change was not selected by looking at this panel's composite at all — it came from a separate
study of the fair-value gap. Both halves are honest measurements.

---

## 6. Separate finding: enterprise value is never refreshed to the rebalance date

Found while wiring the above. **This is a real latent defect, independent of the verdict.**

Sharadar's `ev` is exactly `marketcap + debt − cashneq` — verified on **193,811 ARQ rows**
(median |diff|/mc = 0, 96.4% inside 1%) — and the `marketcap` inside it is the **filing-date**
one. The panel long ago replaced its buggy shares×price market cap with a point-in-time figure
from DAILY, but `ev` was left behind. Consequence:

- `earnings_yield`, `fcf_yield`, `book_to_price` → priced at the **rebalance date**.
- `ebit_ev`, `ev_sales`, `ev_ebitda` → priced at a quote roughly **111 days old** (the panel's
  effective fundamental lag).

Scale of the handicap, from the same export: the median one-quarter market-cap move is
**10.5%**, **51.7%** of names move more than 10% and **18.6%** move more than 25%. That is not
a rounding detail on a value ratio.

It is **stale, not look-ahead** — the embedded price is always older than the rebalance, never
newer — so the bias is conservative and no past result is invalidated upward. But it does mean
section 5 rejected a **handicapped** factor, which is why it was tested rather than caveated.

Fix, behind `CONFIG.ev_point_in_time` (default **off**): rebuild EV as PIT market cap + filing
net debt, with net debt **currency-converted first** — `debt`/`cashneq` are reporting-currency
line items and `marketcap` is USD, so adding them raw is the P7 bug in a different costume. A
test pins that a foreign filer and its USD twin produce identical multiples. It is a separate
flag because turning it on also changes `ebit_ev`, an already-adopted factor.

### 6a. Measured: the fix is real but performance-neutral

A third full-universe run with `ev_point_in_time=true`. It changes exactly the seven columns it
should (`raw_/z_` for `ebit_ev`, `ev_sales`, `ev_ebitda`, plus the downstream `value`) and
nothing else, on identical `(date, ticker)` keys.

| metric | stale EV (shipped) | PIT EV |
|---|---|---|
| long-short t | +3.396 | **+3.520** |
| long-short /yr | +17.16% | **+17.58%** |
| top-decile alpha | +11.82% | **+11.88%** |
| net alpha after costs | **+11.44%** | +11.40% |
| breakeven bps | 235 | 235 |
| monotonicity | −0.952 | −0.952 |
| PBO | 6.7% | 6.7% |
| Deflated Sharpe | 99.99984% | 99.99986% |

The EV signals themselves get materially better, which is the direct evidence that the
staleness was a real handicap: **`neg_ev_sales` median IC +0.0214 → +0.0363** (+70%),
`neg_ev_ebitda` +0.0236 → +0.0289, `ebit_ev` IC t +2.295 → +2.358.

But on the held-out gate the *book-level* effect is noise:

| half | Δ long-short t | Δ top-decile alpha | clears? |
|---|---|---|---|
| early (55 dates) | +0.147 | +0.18% | no |
| late (54 dates) | −0.015 | −0.09% | no |

**not_replicated** — helps one direction slightly, hurts the other slightly.

The likely reason is worth recording: the composite ranks names **cross-sectionally** and every
input is z-scored, so a staleness that shifts most names in the same direction largely cancels
out of the ranking. The per-signal IC improves because the ratio is more accurate; the book
barely moves because the *ordering* was already roughly right.

### 6b. And it does NOT rescue EV/Sales

The point of running this arm was to check whether section 5 rejected a handicapped factor. It
did not. Re-running the identical A/B on the PIT-EV panel — where EV/Sales is no longer stale
and its median IC is up 70% — the change is rejected **more** decisively:

| metric | WITHOUT | WITH (on PIT-EV panel) |
|---|---|---|
| value theme IC t | +1.466 | **+1.714** |
| long-short t | **+3.520** | +3.124 |
| top-decile alpha | **+11.88%** | +11.16% |
| monotonicity | **−0.952** | −0.927 |

Held-out: early Δt **−0.370** / Δalpha −1.01%, late Δt −0.160 / Δalpha −0.46%. **NOT_REPLICATED**,
both directions negative again. The residual test agrees: EV/Sales residual t **+0.50**,
EV/EBITDA residual t **−0.06**.

So the rejection in section 5 is **not** an artifact of the stale price. Giving EV/Sales a fair
price makes it a better *signal* and a worse *input* — the same pattern, more sharply.

---

## 7. What shipped, what did not

**Shipped (wiring, permanently measured):**
- `ev_ebitda` computed in the panel, USD-correct, positive-EBITDA-only.
- `neg_ev_ebitda` registered to the value theme → IC and coverage reported every run.
- The provider-agnostic sign guard in `factors.py`.
- `bucket` on every panel row.
- `ev_multiples_study.py`, `EDGE_PANEL_PICKLE`, 20 tests.

**NOT shipped (both flags default off):**
- `value_ev_multiples` — rejected on both the stale-EV and PIT-EV panels, sections 5 and 6b.
- `ev_point_in_time` — a correctness fix that does not clear the performance gate (6a). Left
  off so nothing ships silently; **this one is a judgment call and it is Don's, not mine.**
  The case for turning it on is consistency — right now half the value ratios are priced at the
  rebalance date and half at a ~111-day-old quote, and there is no principled reason for that.
  The case for leaving it off is the project's own rule against shipping changes that do not
  clear the bar. It is one environment variable either way.

The wiring stays even though the verdict is reject, following the `sector_neutral` precedent:
the wiring is pinned by tests, the verdict is a research finding that may change. Re-testing is
now one environment variable, not a re-implementation.

---

## 8. Honest caveats

- The value theme's IC genuinely improved. If a future weighting scheme leaned much harder on
  value, that could in principle change the composite conclusion — but CPCV still adopts no
  weighting over the defaults, so there is no such scheme today.
- Both halves of the held-out test come from the same 18-year Sharadar panel. Consistent with
  every other finding in this project, the *decision* is confirmed out-of-sample; the panel is
  not.
- The residual test is **linear**. It rules out EV/Sales adding information a linear combination
  of the incumbents cannot reach. A tree combiner (CLAUDE.md item #16) could in principle find
  interaction structure this cannot see — that is the one honest route to re-opening this.
- Deflated Sharpe is saturated in both arms and discriminates nothing here; PBO and the held-out
  deltas are doing the work.

---

## 9. Recommended next step

**Do not re-open EV/Sales as a linear value input.** It was tested properly, on the full
universe, and the reason it fails is understood rather than merely observed: its predictive
content is already spanned by the existing inputs.

It was tested on BOTH a stale-EV and a fair-priced panel and rejected on both, more decisively
on the fair one.

The two things worth doing next, in order:

1. **Decide on `ev_point_in_time` (section 6).** A one-variable call, laid out in section 7.
2. **The ML tree combiner** (CLAUDE.md #16) is now better motivated than before. This study is
   a concrete demonstration that a linear composite cannot use a signal whose marginal
   information is non-linear — and that a per-signal IC can improve while the book does not.

### The transferable lesson

**A theme's IC improving is not evidence the book improves.** Here the value theme's IC rose a
clean 17% (t +1.461 → +1.708) in every arm tested, while the composite's long-short t, alpha,
monotonicity and PBO all got worse. Judging this change the way factor changes are usually
judged — by the theme's own IC — would have adopted it.

This is the mirror image of the P6 lesson already in CLAUDE.md ("a signal's IC can be flat while
the composite built from it moves a lot"). Both point the same way: **the composite is the unit
of decision, not the signal and not the theme.**

And correlation would have pointed the wrong way too. The incumbents explain only 15.7% of
EV/Sales's variance, which reads as "mostly orthogonal — adopt it". The residual test is what
separates *orthogonal* from *informative*: the 84% that is genuinely new predicts nothing.
Anyone testing a new input against the existing ones should residualize, not just correlate.

Suites at handoff: edge 123/123, screener 47/47, sector-neutral 6/6, calibration 23/23,
engine 28/28, EV multiples 20/20.
