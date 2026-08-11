# PRE-REGISTRATION — O12, fractional Kelly and ruin

**Committed before any measurement code for this item exists**, in the same commit as
`PREREG_o13_antisignal.md` and no `.py`. Strict git ancestor of every measurement commit that
follows.

Item **O12** in `VALQUO_LEDGER.md` (`OPEN`, src=human, "Unblocked by B3 (tail and sizing work).
No write-up yet."). Options domain.

---

## 0 · The caveat that governs every number in this item

**Kelly sizing requires an edge that is real, and R2 says this book's entry is dead.** The alert
book earns +3.2702%/trade against a random-entry control's +8.3342% (split-clean, U1-SPLIT).
Every fraction computed here is therefore **conditional on a distribution the project has
already shown is worse than random entry on the same names**.

This item is not a recommendation to size up. It answers a bounded question — *given the
measured payoff distribution, what does sizing arithmetic say, and where is ruin* — and its most
useful output is expected to be the sensitivity, not the point estimate. **No number here may be
quoted as a position-sizing recommendation for real money.** Don executes; this lane does not
size his book.

## 1 · Inputs measured BEFORE this register was written, and disclosed

The empirical return distribution is an *input* to O12, not an answer to it, but it was measured
today and honesty requires listing it:

* Split-clean alert book, n **3,870**. Mean **+0.0327**, median **−0.5222**.
* **Hit rate (return > 0) = 0.3527.** The task brief said 37%; **that does not reproduce** — it
  is 0.3532 on the as-published 3,885-row book and 0.3527 split-clean. The measured value is
  used throughout and the discrepancy is reported rather than quietly adopted.
* Quantiles: p1 −0.9152, p5 −0.7507, p25 −0.5918, p50 −0.5222, p75 +0.9993, p95 +1.5270,
  p99 +2.5691. Min **−1.0144**, max **+7.8231**.
* Exit mix: stop 2,294, target 1,047, time_stop 525, expiry 4.
* **The minimum is below −100% and that is CORRECT, not a bug** — checked, not assumed: DHR
  2016-06-30 paid $90.00 of premium and lost $91.30, the difference being commission. A total
  loss plus commission genuinely exceeds 100% of premium. 4 rows (0.10%) are affected.
* **Live sizing is flat 1 contract** — `paper_track` reads `paper_contracts_per_trade`
  (default 1) and honours the alert's own `$1,000` budget veto (session 16). It does **not**
  read `sizing.contracts`; that was pinned as a deliberate non-change.

**Not known:** any Kelly fraction, any growth curve, any ruin probability, any half-split of
those. Those are what this register commits to.

## 2 · Definitions, fixed now

Per-trade return `R_i = pnl_pct`. Growth of a book betting fraction `f` of equity on each trade
sequentially:

> `G(f) = (1/n) · Σ_i log(1 + f · R_i)`, and `f* = argmax G(f)`.

**`f*` is bounded above by `1 / |min R| = 1 / 1.0144 = 0.98580`** — arithmetic, because a trade
losing more than 100% of its stake makes `log(1 + f·R)` undefined at and above that fraction.
Stated here so it is not later mistaken for a finding.

Search grid `f ∈ [0.0005, 0.9850]` in 0.0005 steps, plus a golden-section refinement; the grid
is fixed now and is **not** tuned to the answer.

## 3 · The three questions

**Q1 — what is `f*`, and is it a measurable quantity?** Computed on the full sample and,
because the user requires both-halves wherever a verdict is claimed, **independently on the
early and late calendar halves**.

**Q2 — where does ruin live?** Sequential compounding over the book's measured trade rate, at
fractions `f ∈ {f*, f*/2, f*/4, 0.01, 0.02, 0.05, 0.10, 0.25}`. Ruin is reported on
pre-committed thresholds — `P(terminal < 0.5×)`, `P(terminal < 0.2×)`, `P(max drawdown > 50%)`,
`P(max drawdown > 80%)` — over **10,000 bootstrap paths per fraction**, resampling trades in
**calendar-month blocks** (R3's clustering rule; i.i.d. resampling of options trades is exactly
the error R3 exists to prevent).

**Q3 — what does the current flat sizing imply?** Flat 1 contract at the book's median premium
is a *dollar* stake, so the implied fraction depends on account equity, which this lane does not
know and will not guess. Reported instead as the **equity at which flat sizing equals** `f*`,
`f*/2` and `f*/4`, plus the implied fraction across a stated grid of account sizes. Needs no
private data and is the actionable form.

**Q4 — the sensitivity that is expected to matter most.** `f*` recomputed on (i) the alert book,
(ii) the pooled control's distribution, (iii) a **zero-edge** version of the alert book with
returns shifted so the mean is exactly 0. If (iii) gives a materially positive `f*` the
statistic is being driven by distribution shape rather than by edge, which would be worth
knowing on its own.

## 4 · Bars and the verdict rule, fixed now

O12 claims exactly one verdict, on whether the number is usable:

| verdict | condition |
|---|---|
| **USABLE** | `f*(early) > 0` **and** `f*(late) > 0` **and** `max/min ≤ 2.0` between them, **and** the month-block bootstrap CI95 of full-sample `f*` excludes 0 |
| **NOT USABLE** | the halves disagree by more than 2×, or either half is 0, or the CI includes 0 |
| **NULL** | anything ambiguous |

The 2.0 factor is committed now. It is deliberately generous — `f*` is a ratio of noisy moments
on a barbell distribution, and a bar tighter than 2× would fail on sampling noise alone.

Ruin figures (Q2) and the equity table (Q3) are **descriptive** and carry **no** verdict; they
are arithmetic on a fixed distribution, not a hypothesis test, and are labelled as such.

## 5 · Expectations, written before any of it runs

* **E1 — `f*` is small, under 0.10. 60/40.** The median trade is −52%; a barbell with a 35% hit
  rate punishes size hard.
* **E2 — the halves DISAGREE by more than 2×, so the verdict is NOT USABLE. 60/40.** `f*`
  depends on the right tail, and the right tail of an options book is a handful of trades.
* **E3 — `f*` on the control distribution EXCEEDS `f*` on the alert book. 75/25.** The control
  has the higher mean on nearly the same shape. If this fails it means shape, not mean, drives
  the fraction.
* **E4 — the zero-edge book gives `f* = 0`** (to grid resolution). Charged as arithmetic, not
  scored: `G'(0) = mean(R)`, so a zero mean means no positive fraction is optimal. Stated so
  that if it comes back non-zero I have to explain a broken implementation rather than announce
  a discovery.
* **E5 — flat 1-contract sizing implies a fraction BELOW `f*` for plausible account sizes, i.e.
  the live paper book is UNDER-sized rather than over-sized. 55/45.** Genuinely uncertain.
* **E6 — at full `f*`, `P(max drawdown > 50%)` exceeds 0.5. 70/30.** Full Kelly is famously
  violent; on a 35%-hit-rate barbell it should be worse than the textbook case.

## 6 · Trial cost

Q1 is **one** hypothesis with one statistic (`f*`), measured on the full sample and two halves —
halves are the *test*, not extra arms. Q2/Q3 are descriptive arithmetic on a fixed distribution
and carry no verdict, so they are charged **zero**, consistent with the treatment of the tenure
and placebo blocks in S22. Q4 is **3** arms (alert / control / zero-edge), of which the alert arm
is Q1's and is not double-counted → **2** additional.

**Options `N` +3** (1 for `f*`, 2 for the Q4 comparison arms), logged in `RESEARCH_LOG.md` with
this file as source. Combined with O13's +18 this session moves options **210 → 231**.

## 7 · What would make this register void

* Using any book other than the split-clean banked one.
* Re-mining, or changing the exit policy — the distribution under test is the shipped policy's.
* Tuning the `f` grid, the ruin thresholds, or the 2.0 half-agreement factor after seeing a
  result.
* Quoting any fraction here as a recommendation for real money.
