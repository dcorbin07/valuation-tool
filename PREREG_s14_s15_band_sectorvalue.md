# PRE-REGISTRATION — S14 + S15: the no-trade band on net alpha, and sector-relative value

**One register, both items, committed before any arm has been scored.**

---

## 0. THE PRIORS, AND ONE CORRECTION TO THE FRAMING I WAS GIVEN

### S14 — the only construction change here with a pure COST mechanism

**It makes no signal claim at all**, and that is the whole argument for re-opening it. Turnover
falls because trades are skipped; the saving is **arithmetic**, not an estimated IC. The audit's
framing is right that applying a signal-strength margin to a mechanical cost reduction is a
category error.

**A CORRECTION TO THE TASK'S FRAMING, STATED PLAINLY BECAUSE IT REVERSES THE EXPECTATION.** The
task describes S11 as having found *"that turnover cuts can be worth 11-23× their cost"*. **S11
measured the opposite.** Its horizon blend cut turnover 0.6352 → 0.4976 per rebalance (~55pp of
book a year) and that saved **≈18 bps/yr at the measured 33.4 bps one-way**, against **205–422 bps
of alpha given up** — the trade ran **11× to 23× AGAINST**. So S11's contribution to S14 is a
**scale**, and it is a discouraging one: **a large turnover cut is worth only tens of basis
points**, so a band can only pay if it gives up almost no gross alpha.

**AND THAT SCALE INDICTS THE AUDIT'S OWN DECISION RULE, BEFORE ANY ARM RUNS.** The audit
pre-commits: *"adopt the width that maximises net-of-cost top-decile alpha, provided it does not
reduce gross alpha by more than 1.5 percentage points."* On its own quoted numbers — turnover
251% → 172%, i.e. ~79pp/yr — the saving is on the order of **tens of bps**, while the rule
**permits giving up 150 bps of gross alpha**. **A rule that allows a 150 bps cost to buy a ~26 bps
saving is roughly 6× against.** The guard is not a guard; it is wider than the prize.

**So the rule is adopted with its gross-alpha allowance TIGHTENED to the actual saving**, and both
versions are reported (§3.1). The audit's own allowance is reported beside it so the difference is
visible rather than silently substituted.

**Lean: the band reduces turnover (near-certain, it is arithmetic) and FAILS to improve net alpha
by the margin — 70/30.**

### S15 — the last route back for sector-neutral, and the B6 mechanism does not settle it

**`SECTOR-NEUTRAL-B6` closed the broad version permanently** and named exactly two routes back:
`S25` (a point-in-time sector map) and `S15`. **`S25` was closed as UNOBTAINABLE in session 29**,
so **S15 is the last one.**

**DOES THE B6 VERDICT'S MECHANISM PREDICT THIS ONE FAILS? Partly, and the honest answer is that it
does not settle it.** B6's finding was that on the void panel sector-neutral **bought long-short
*t* and sold alpha**, and on the corrected panel **the gain vanished and reversed** (−0.494
deployed), leaving it worse on both metrics with no trade-off left to adjudicate.

* **The part that transfers:** whatever sector-relative ranking does to this book, the corrected
  panel says it was not a *t*-for-alpha trade — it was simply worse. If that is a property of
  de-meaning by sector at all, S15 inherits it.
* **The part that does NOT transfer, and it is why the audit calls this the only version worth
  re-opening:** B6 neutralised **every theme**, including ones where sector has no business —
  momentum and size travel across sectors fine, and de-meaning them throws away real signal for
  no reason. **S15 touches only the theme whose raw ratios are genuinely sector-determined.** A
  bank's `book_to_price` and a software company's are not the same quantity, and this project has
  measured that directly: **S10 found valuation-band flagging at 48.88% for Financial Services and
  40.32% for Real Estate against 15.79% for Industrials** — a three-fold spread that is exactly
  the sector-dependence S15 exists to remove.

**Lean: REJECT, 70/30** — lower confidence than the broad version's three rejections, because the
mechanism argument is specific and measured, and because B6's harm was spread over six themes S15
does not touch.

**THE STANDING CAVEAT, WHICH CANNOT NOW BE REMOVED:** Sharadar TICKERS gives **today's** sector
applied to 1998 rows. `S25` — the item that would have fixed it — is **closed as unobtainable**.
So **a positive S15 result must be read MORE sceptically, not less**, and that is fixed here
before any number exists.

---

## 1. PREMISE CHECK

**(a) S14 NEEDS NO REBUILD.** `turnover_and_costs(panel, cols, weights, top_frac, horizon,
exit_frac)` already returns `annual_turnover`, `gross_alpha`, `net_alpha` and `cost_drag_ann`, and
the payload already sweeps `exit_frac` over `None, 0.12, 0.15, 0.20, 0.25, 0.30`. The machinery is
shipped; only the **decision** was never made on net alpha.

**(b) S14's PREREQUISITES ARE ONE-AND-A-HALF MET, NOT TWO.** The audit says re-run after **B11**
and **B13**. **B11 is met** — the realised cost is measured at **33.4 bps one-way**, not assumed.
**B13 is only PARTIAL**: its categorical filters bind, but `MIN_AVG_DOLLAR_VOLUME` structurally
cannot on this path, because the price export carries date and close only (the row was corrected
to `PARTIAL — BLOCKED ON DATA` in session 30). **So "the book is investable" is true of the
categorical screen and NOT of the liquidity screen**, and that limitation travels with the result.

**(c) S15's TARGET IS A SPECIFIC, SHORT LIST.** The value theme's inputs are
`earnings_yield`, `fcf_yield`, `ebit_ev`, `book_to_price` (established) and
`neg_ev_sales`, `neg_ps`, `book_to_price` (speculative). **Those columns and no others** get the
sector-median subtraction; every other theme stays cross-sectional.

**(d) THE PLUMBING IS PROVEN AND WAS EXTENDED LAST SESSION.** `sector_neutral` already subtracts a
within-sector median from the granular metrics before z-scoring, and session 34 added
`bucket_relative` on the identical pattern. S15 is that operation restricted to a **column
subset** — one new parameter, same shape.

---

## 2. THE ARMS

* **A1 — S14 NO-TRADE BAND, decided on NET alpha.** Widths swept over the **shipped grid**
  `{0.12, 0.15, 0.20, 0.25, 0.30}` plus the no-band incumbent. **The sweep runs on the DECIDE
  half; the argmax width is then measured on the HELD-OUT half, in both directions.** A
  sweep-and-pick on the full sample is the in-sample selection this project has already paid for
  (+8.43%/yr in-search → −0.04%/yr on the locked hold-out), and the audit itself warns the width
  surface is noisy — *"15% is worse than both 12% and 20%, which should not happen on a smooth
  tradeoff"*.
* **A2 — S15 SECTOR-RELATIVE VALUE ONLY.** The within-`(date, sector)` median is subtracted from
  the seven value inputs listed in §1c before the global z-score. **No other theme is touched**,
  and that is asserted as a control.

---

## 3. THE GATE

**A2** uses the shipped margins: **≥ +100 bps top-decile alpha AND ≥ +0.25 long-short *t*, in BOTH
halves, boundary embargoed** — and, per `SECTOR-NEUTRAL-B6`'s own metric priority, **top-decile
alpha decides; an arm that buys *t* and sells alpha is REJECTED regardless of the *t*.**

### 3.1 A1 is judged on NET alpha, and its guard is tightened

**A1's primary is NET top-decile alpha**, the quantity the band exists to improve — not gross, and
not the long-short *t*, which a sizing/turnover change has no business moving.

**ADOPT-ELIGIBLE** iff, on the **held-out** half in **both** directions:

1. **net alpha improves at all** (any positive margin — this is a deterministic cost saving, not a
   signal, so the +100bps signal margin is the category error the audit names); **AND**
2. **gross alpha falls by no more than the measured cost saving itself**, i.e. the trade must not
   be net-negative on its own arithmetic.

**Condition 2 is the tightened guard, and the audit's own ±1.5pp allowance is reported beside it
so the substitution is visible.** On the audit's numbers that allowance permits paying ~150 bps to
save ~26 bps; a guard wider than the prize is not a guard.

**FAMILY-WISE:** two arms. A single clearing arm is recorded **`ELIGIBLE — UNREPLICATED, 1 OF 2
SIBLING ARMS`**, never adopted. This clause has fired in each of the **last four** sessions.

---

## 4. ADOPTION

Either arm is a **VINTAGE EVENT** — A2 changes the composite users receive; A1 changes the
construction of the book. The current vintage is **DERIVED, never assumed** (`PT-GAPDUE`) at run
time. **No arm is adopted by this register.** Note that A1's band is **already live in the
`taxable` configuration only**, so an adopt would be a change to the *default* configuration, and
the write-up must not imply the band is currently absent everywhere.

---

## 5. CONTROLS — read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record** (alpha 0.07174142332098163, LS *t*
  2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909). **ABORTS**
  otherwise.
* **C2 — identical rows** across arms.
* **C3 — no arm is inert:** within-date rank correlation against the deployed composite (A2), and
  turnover actually falling (A1). **An A1 width that does not cut turnover is not a band.**
* **C4 — A2 TOUCHES ONLY VALUE.** Every non-value theme must be **bit-identical** to the deployed
  panel's. This is the control that makes A2 the narrow experiment it claims to be, and a failure
  here means the arm is a broad sector-neutral run wearing a narrow label.
* **C5 — THE COST SAVING IS MEASURED, NOT ASSUMED.** `cost_drag_ann` is reported per width, so
  condition 2 of §3.1 is evaluated against a measured number rather than the 33.4 bps constant.
* **C6 — THE WIDTH SURFACE'S NOISE IS REPORTED.** The audit flags that 15% was worse than both 12%
  and 20%. Whether that non-monotonicity persists is reported per half; **if it does, the argmax
  width is noise and its held-out verdict must be read as one draw from a rough surface.**
* **C7 — THE SECTOR CAVEAT IS QUANTIFIED, NOT JUST RESTATED.** A2's sector coverage and the number
  of distinct sectors per date are reported, and the write-up must carry the today's-classification
  caveat with `S25`'s closure beside it.

**TOP-25 BEFORE/AFTER BY NAME** is reported for both arms on the last scored date.

---

## 6. EXPECTATIONS

1. **A1 cuts turnover materially — 95/5.** It is arithmetic; the only question is how much.
2. **A1 fails the net-alpha gate — 70/30**, because S11's scale says a large turnover cut is worth
   only tens of bps and the band must therefore give up almost nothing in gross alpha.
3. **The measured cost saving is under 40 bps/yr at every width — 75/25.** If true, no width can
   justify the audit's 150 bps allowance and §3.1's tightening is vindicated rather than merely
   argued.
4. **C6 finds the width surface still non-monotone — 65/35.** The audit saw it on the void panel;
   there is no reason a noisy surface became smooth.
5. **A2 fails — 70/30.**
6. **A2 moves the book LESS than the broad sector-neutral arm did — 80/20**, since it touches one
   theme of seven. Reported as a rank correlation against deployed, compared with
   `SECTOR-NEUTRAL-B6`'s measured 0.9836.
7. **A2 does NOT reproduce B6's buy-*t*-sell-alpha shape — 55/45.** Low confidence, and it is the
   cell I most want measured: B6's own re-run found that trade-off had vanished on the corrected
   panel, so if it reappears in the narrow arm that is informative about where it came from.

---

## 7. TRIAL COST

**Two arms: equity `N` 183 → 185.** A1's width sweep is charged as **one** trial, not five,
because the argmax is taken on the decide half and only the selected width is measured — one
hypothesis, one measurement. The controls and the top-25 tables charge nothing.

`BACKTEST_RESULTS.json` is re-run **from a clean tree**.

---

## 8. WHAT THIS REGISTER DOES NOT DO

* It does **not** re-open broad sector-neutral. S15 is a **different construction**, and if it
  fails, **both** named routes back are closed and the item should be recorded as finished rather
  than dormant.
* It does **not** change `MIN_AVG_DOLLAR_VOLUME` or wire SEP volume to complete B13 (§1b).
* It does **not** sweep the band's `enter_frac`, which stays at the shipped 0.10.
* It does **not** adopt anything, and it does not touch the `taxable` configuration where the band
  already lives.
