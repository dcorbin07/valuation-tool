# PREREG — S22: the term structure of the signal, and top-decile tenure

**Committed BEFORE any measurement code exists.** This file is committed ALONE, in a commit that
is a strict git ancestor of the commit introducing `scripts/term_structure.py`. That ordering is
the only thing that makes "pre-registered" checkable rather than asserted, and it is the same
discipline V2G used at `6d8750a`.

Ledger item **S22** ("Term structure of the signal", status OPEN, no prior mention anywhere in the
corpus). Routed to this lane as unblocked.

---

## 1. The two questions, stated so they can be answered wrongly

1. **How long does a hot name's edge last?** Every performance figure this project has ever
   published is measured at a **63-trading-day** forward window, because
   `build_fundamental_panel` computes exactly one `fwd_ret` column and the deployed rebalance
   period equals it. Nobody has ever asked what the composite predicts at 6 months, a year, or
   two years. The 63d choice is an inherited default, not a measured optimum.
2. **How long do names stay hot?** The top decile is the product. Its **tenure** — how many
   consecutive rebalances a name survives in it — has never been measured either, and it is the
   quantity a user actually experiences ("I bought this because it was hot; is it still hot?").

**Neither question changes the book.** Any change to the holding period or exit rule is **S23**,
which needs its own pre-registration and is a **vintage event** under the rule in
`PAPER_TRACK_CONTRACT.md`. Any change to what the site displays is the **web lane's**. This
register measures and reports; it adopts nothing.

---

## 2. The instrument, and why one panel build rather than eight

The horizon is baked into the panel: `build_fundamental_panel(..., horizon=63)` computes one
`fwd_ret` and — critically — its rebalance grid is
`range(_GRID_START, len(cal) - horizon, rebalance_days)`, so **the grid end moves with the
horizon**. Rebuilding the panel once per horizon would therefore vary the horizon *and* the date
set *and* the scored cross-sections together, and no difference between two such runs could be
attributed to the horizon.

**So: ONE panel build, at the deployed `horizon=63`, carrying additional forward-return columns
`fwd_ret_h{H}` computed inside the same loop from the same price array.** The scores, the dates,
the names and the composite are then **identical across every arm**, and the forward window is
the only thing that varies. This also means any run-to-run nondeterminism in the panel (the
record's known `insider` instability) is **common to all arms** and cancels out of every
across-horizon comparison.

**Horizons: H ∈ {63, 126, 189, 252, 315, 378, 441, 504}** — exactly 1 through 8 quarters. A
complete grid in units of the rebalance period is required, because the incremental analysis in
§4 differences adjacent horizons and those differences are only comparable if every step is one
quarter.

`fwd_ret_h{H}` is computed with the **same delisting-aware rule** the shipped `fwd_ret` uses: if
the horizon-end price is NaN because the survivorship mask cut the name mid-window, fall back to
the last price it actually traded at, so the delisting outcome is realized rather than discarded.

### 2a. Right-censoring is NOT delisting, and conflating them would fabricate the result

If `i + H` runs past the end of the calendar, the long-horizon return **does not exist**. It must
be `NaN`. It must **NOT** fall through to the delisting branch, because that branch returns the
last available price — which would silently deliver a *shorter* realized return **labelled as a
long-horizon one**, and would do so precisely for the most recent dates. That is a
result-fabricating bug, it points in the flattering direction for short horizons and the
pessimistic direction for long ones, and it is pre-committed here as the single most likely way
this study goes wrong. Pinned by a test.

**Consequence, accepted in advance:** longer horizons are observable on **fewer rebalance dates**.

---

## 3. Date sets — primary and secondary, both fixed now

* **PRIMARY: the COMMON date set** — the rebalance dates observable at **every** horizon, i.e.
  the H = 504 set. Every arm is scored on **exactly these dates**. This is the only comparison in
  which the horizon is the sole varying quantity, so it carries the verdict.
* **SECONDARY: the ALL-AVAILABLE set** — each horizon scored on every date it can reach. Short
  horizons get more dates. Reported alongside, never as the verdict, because a difference between
  two arms here confounds the horizon with the window.

Both are reported for every arm. If they disagree in sign anywhere, that disagreement is reported
in the handoff as a finding about the window rather than resolved by picking one.

---

## 4. The primary statistic: cumulative alpha, not annualized alpha

Annualizing (`ppy = 252/H`) is the wrong lens for a term-structure question — it divides by the
horizon and would make a *fixed* one-off edge look like it decays as `1/k` when nothing decayed
at all. The quantity that answers "how long does the edge last" is the **cumulative,
non-annualized top-decile alpha**:

> `cum_alpha(H)` = mean over dates of ( mean fwd_ret_H of the top decile − mean fwd_ret_H of all
> scored names )

with the deciles formed by the **shipped** `argsort(-composite)` convention, `n_q = 10`, on the
**deployed** flat 1/7 weights over the seven weighted themes. Both annualized and cumulative
figures are reported; **cumulative carries the verdict**.

Define `R(H) = cum_alpha(H) / cum_alpha(63)` and `k = H/63` (quarters). The three shapes are:

| shape | meaning | signature |
|---|---|---|
| **CONSTANT-RATE** | the edge keeps accruing at the same rate | `R(k) ≈ k` |
| **SATURATING** | the edge is front-loaded and then stops | `R(k)` flattens well below `k` |
| **REVERSING** | the edge is given back | `R(k)` turns down |

**Pre-registered classification, decided on `R(8)` (H = 504):**

* **CONSTANT-RATE** if `R(8) ≥ 6.0` (≥ 75% of linear accrual);
* **SATURATING** if `R(8) ≤ 2.0` (≤ 25% of linear accrual);
* **INTERMEDIATE** if `2.0 < R(8) < 6.0`;
* **REVERSING** — overrides all three — if `cum_alpha(H) < 0` at any `H ≥ 189` with alpha HAC
  `t ≤ −2.0` on that arm.

`INTERMEDIATE` is a real outcome and will be reported as one. It is not a failure to decide.

**The incremental series** `Δ_k = cum_alpha(63k) − cum_alpha(63(k−1))` is the direct answer to
"how long does the edge last": the quarter at which `Δ_k` stops being positive. It is reported for
k = 1..8 **with its limitation stated**: adjacent cumulative windows overlap almost entirely, so
`Δ_k` is a difference of two highly dependent quantities and its standard error is not the
difference of their standard errors. HAC inference on `Δ_k` is reported as **approximate and
uncalibrated**, and no verdict rests on it.

### 4a. Overlapping windows — the HAC lag is set by the design, in advance

At horizon `H` with a 63-day rebalance, consecutive forward windows overlap by `H/63 − 1`
periods. Ignoring that would inflate every long-horizon *t*. **Primary HAC lag =
`max(1, H//63 − 1)`** — which is exactly the shipped R9 convention (lag 1) at H = 63, and rises
to 7 at H = 504. The full lag profile `0 … H//63 + 2` is reported per arm as a sensitivity, and
the naive i.i.d. *t* is reported as a diagnostic only, never quoted.

---

## 5. Bars — what is calibrated, what is not, and the refusal to pretend otherwise

**The X7 / session-10 calibrated floors (long-short HAC 2.2837, top-decile alpha HAC 2.2913,
long-short naive 2.1437) are valid at ONE configuration: H = 63, the full 69-date panel, HAC
lag 1.** They were calibrated there and nowhere else. `n` changes with the horizon, the overlap
changes, and the HAC lag changes with it. **They will not be quoted against any other arm.**
Doing so is the same error the record already paid for twice — comparing a HAC *t* to a
naive-calibrated floor (closed in session 10), and comparing a floor across different `N`
(closed in session 12).

So the H = 63 all-available arm is scored against those floors as the **harness control**, and
every other arm needs its own null:

**Per-horizon placebo (pre-registered).** The shipped `placebo_panel` block permutation — within
each rebalance date, permute the signal columns as a whole row-block, leaving `fwd_ret*`,
`market_cap` and `sector` in place. **200 draws, seeds 2000–2199**, fixed base weights, evaluated
through `quantile_backtest` at every horizon. Report the p95 of the alpha HAC *t* and of the
long-short HAC *t* per horizon as that horizon's floor.

Two things about this instrument are stated now, not discovered later:

* **The known invariance does not apply here.** `placebo_panel` is *exactly* invariant on the
  composite — a permuted row's theme vector and its present-weight renormalization denominator
  travel together, so the sorted score comes back identical, and pointing it at anything
  score-shaped yields a null equal to the real book. That is why it may never calibrate a score.
  It is the **correct** null here because every statistic in this register is **return-based**:
  the permutation severs the association between the signal and `fwd_ret`, which is exactly the
  null hypothesis being tested.
* **This is a DIFFERENT and LESS CONSERVATIVE null than X7's**, because X7 pushed each draw
  through CPCV and weight selection, and adoption on a noise draw manufactures long-short *t*
  (the record's own estimate is ~+1.4). Fixed weights remove that. **Therefore these percentiles
  may never be compared with 2.2837 or 2.2913**, and they are labelled `fixed_weights_null` in
  the artifact so a later reader cannot mistake them.

**By-product, no verdict attached:** running the fixed-weights null at H = 63 and comparing its
p95 to X7's 2.2837 quantifies how much of X7's floor was the adoption step. Reported as an
observation with its own uncertainty; it is not a test and adopts nothing.

---

## 6. Tenure — definitions fixed before measurement

Top-decile membership per date uses the identical convention as the backtest
(`argsort(-composite)`, `n_q = 10`, first bucket). A **spell** is a maximal run of *consecutive*
rebalance dates in which a name is in the top decile.

* **Primary: Kaplan–Meier median spell length**, in rebalances and converted to months at
  63 trading days ≈ 3 months. Spells still open at the panel end are **right-censored** and
  enter KM as censored observations.
* **Also reported: the naive median** over completed spells, which is biased *downward* by
  discarding long ongoing spells — reported precisely so the size of that bias is visible rather
  than hidden by a choice.
* **Full distribution** of spell lengths, plus the survival curve `S(j)` = P(still in the decile
  after `j` further rebalances | in it now).
* **A name that leaves and returns starts a NEW spell.** Re-entry is counted and reported
  separately; it is not stitched into one long spell.
* **By cap tier:** market-cap **tertiles computed WITHIN each date**, so the tiers are relative.
  Absolute dollar thresholds would drift across an 18-year window and would measure the market's
  growth rather than the name's size. A spell is assigned the tier it had at its **start**.

### 6a. Tenure must reconcile with the shipped turnover figure — or it is a bug

The shipped `costs` block reports ~261% annual turnover for the top-decile book. At four
rebalances a year that implies roughly 65% of the decile replaced per rebalance, i.e. a one-period
retention near 35%. **Pre-committed: the measured one-period decile retention must land in
20–50%.** Outside that band, the two numbers describe incompatible books and the correct action is
to **report a BUG** (RUN_RULES A3) and withhold the tenure verdict — not to publish a tenure
figure that contradicts the cost model. The comparison is directional, not an identity: shipped
turnover is weight-based and includes the signal-weighting, while retention here is name-based.

---

## 7. Both-halves stability

Anything that looks like a finding is re-measured on the **first 34** and **last 35** rebalance
dates — the split point used by V2G, fixed here before any number exists. Specifically: the term
structure shape `R(8)`, the incremental series sign pattern, and the KM median tenure. Agreement
in sign across halves is reported; **a sign flip is reported as loudly as a confirmation**, per
session 7's finding that four of seven LOO arms flipped between halves.

Half-arms are the same arms measured on subsets, not new hypotheses, so they are **not charged**
as trials — session 7's precedent.

---

## 8. Controls, committed in advance

* **C0 — the extra column is the shipped column.** `fwd_ret_h63` must equal `fwd_ret` for every
  row, exactly. If it does not, the new code path is not the shipped one and the register is void.
* **C1 — the incumbent reproduces the record.** The H = 63 all-available arm must reproduce the
  published figures to the digit: `top_decile_alpha` 0.071741423321, long-short naive *t*
  2.8360640685320595, long-short HAC *t* 2.6199, alpha HAC *t* 4.3762, monotonicity
  −0.8909090909090909, equal-weight benchmark 0.18137118752419476.
* **C2 — censoring is real and counted.** The number of dates dropped per horizon must equal
  exactly the number for which `i + H` exceeds the calendar, and must be monotone increasing in H.
* **C3 — default payloads unchanged.** With no extra horizons requested, the panel builder's
  output must be identical to today's, column for column.
* **C4 — the placebo destroys what it claims to.** On a permuted panel the median alpha HAC *t*
  across draws must be near zero at every horizon; a null centred away from zero means the
  instrument is broken.

---

## 9. Trial cost

**Eight horizon arms charged: equity `N` 135 → 143.** H = 63 is charged even though it is the
incumbent control, because a sweep from which a best horizon *could* be quoted is a search over
eight cells regardless of which one was already known. Understating `N` overstates the
significance of every DSR-gated claim, so the conservative direction is to charge it.

**Charged at zero:** the tenure statistics (descriptive — no hypothesis, no threshold, no
selection), the per-horizon placebo (a calibration searches nothing — session 10's precedent), and
the half-splits (§7).

`BACKTEST_RESULTS.json` must be regenerated from a clean tree so its Deflated Sharpe is computed
at `N = 143` rather than going stale on the denominator — the failure sessions 13, 14, 15 and 17
each had to repair. **It is re-run, never hand-patched**, even though the DSR is closed-form in
`N`.

---

## 10. Expectations, written down first because this project's are usually wrong

The record's own standing rule is that reasoning about the direction of an effect here has failed
more often than it has worked. Stated anyway, so the score is kept:

| # | expectation | odds |
|---|---|---|
| 1 | The term structure is **SATURATING** — the edge is front-loaded in the first quarter or two | 60/40 |
| 2 | KM median top-decile tenure ≤ 2 rebalances (~6 months) | 65/35 |
| 3 | At least one horizon ≥ 252d fails its own per-horizon placebo floor | 70/30 |
| 4 | Large-cap tertile tenure is **longer** than small-cap tertile tenure | 55/45 |
| 5 | `Δ_k` is positive for k = 1 and 2 and not reliably positive beyond k = 4 | 60/40 |
| 6 | C1 reproduces the record to the digit | 95/5 |

---

## 11. The product sentence

The handoff must state the **one sentence** about horizon and tenure that is defensible from these
numbers — the sentence the web lane may later display. Pre-committed constraints on it: it must
name the horizon it was measured at, it must be derivable from a measured figure with **no
extrapolation**, and if the tenure verdict is withheld under §6a it must say so rather than quote
a number. Display is the web lane's; wording it is this register's.

---

## 12. What voids this register

* The panel is not the corrected **2,531-name / 69-date** universe (`universe.label == "full"`).
* **C0** fails — the added column is not the shipped forward return.
* **C1** fails — the incumbent arm does not reproduce the published record.
* Any horizon arm is scored on dates that do not satisfy `i + H < len(cal)`, i.e. §2a's censoring
  rule was not honoured.
