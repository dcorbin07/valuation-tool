# VALQUO_OPTIONS_FRONTIER.md — where could an options edge actually live?

**Commission:** read-only research design. Written 2026-08-16 against `origin/main` @ `c836b03`.
**Adopts nothing. Changes nothing else. Zero trials charged** — the four measurements in §2 are
scoping arithmetic on frozen artifacts, not tests of any hypothesis, and none of them carries a
verdict. Options `N` stays 287; equity `N` stays 227.

Read first, as instructed: `VALQUO_LEDGER.md` (O-series, 26/26 closed), `HANDOFF_optionsbot.md`,
`HANDOFF_edge_audit.md`, `VALQUO_MASTER_AUDIT_ULTIMATE.md`.

---

## 0. Three corrections to the commission's own premises

The commission is right about the shape of the problem and wrong about three facts. All three
change what is worth doing, so they go first.

**(a) "Dealer gamma/GEX is BUILT and never tested as a predictor" — false. It was tested twice
and rejected twice.** `valuation/edge/options_signals_v2.py:80` scores `gex_proxy` in the
five-signal pre-committed gate: threshold +0.048, kept 366/729 late-half trades, expectancy
+4.65% → +4.00%, **gain −0.65pp, verdict `reject`**. Four more GEX features — `gex_wall_conc`,
`gex_top_strike`/`d_dist_gex_wall`, `zero_gamma_vs_spot`, `d_gex_sign` — are inside the
126-feature autopsy (`options_autopsy.py:421-444`), which is the run the commission itself cites
as having **zero FDR discoveries** (`RESEARCH_LOG.md` row `OPT-AUTOPSY`, n=126, REJECTED, BH
within family). So single-name GEX is not an untested orthogonal dataset; it is a rejected
feature family, and re-opening it is the 126-feature autopsy in costume.

There is worse. `options_greeks.py:645-660` carries a measured artifact warning in the shipped
code: across 280 names the top strike's gamma share runs **0.31 on dates with >95% known open
interest and 0.55 when under a quarter is known**, with `corr(coverage, concentration)` negative
for 231 of them. `gex_wall_conc` is **partly an artifact of the B4 open-interest sentinel**, and
`gex_top_strike` / `call_wall` / `put_wall` inherit it. Flagged, deliberately not corrected. Any
future GEX arm inherits a known-contaminated instrument.

*What is genuinely untested is **index-level** GEX (SPX/SPY), which is where the published
evidence actually lives — Jonsson & Nyberg (2025) and Baltussen et al. predict S&P 500 returns
and intraday momentum, not a single-name cross-section. We own no index chain. See §5.*

**(b) "Cboe open-close volume (ledger D4, still open)" — false. D4 is DONE / REJECTED, and the
hypothesis behind it was independently closed by MA32 sixteen days ago.**

* **D4 (2026-08-11, `HANDOFF_data_spend_d4.md`): DON'T BUY.** Priced from SEC-filed schedules:
  EOD subscription **$500/mo per exchange**, ad-hoc historical **$400 per request where one
  request = one month of data**, filed per exchange across C1/C2/BZX/EDGX. The 94 purchasable
  months of this project's own alert window cost **$28,200–$37,600 for one exchange**. The
  licence forbids what Valquo is — *"raw data is licensed for internal use only and may not be
  redistributed externally in any form"*, external distribution of **derived** data is
  **$5,000/mo**. And ad-hoc history **starts January 2018**, so 24 of the book's 118 months
  (20.3%) are unavailable at any price **and they are the early ones** — D4 cannot be tested by
  this project's own both-halves standard.
* **MA32 (2026-08-15) already ran the hypothesis for free**, building the open-vs-close
  decomposition from open-interest change over the owned 27 GB raw chain cache.
  **Both arms NULL.** `call_open_share` incremental IC t −1.4146 early / −0.7169 late against
  its own within-date permutation p95 of 1.9547 / 1.7547; `put_open_share` +0.0633 / +1.0895
  against 2.0879 / 2.0978. Ge–Lin–Pearson's declared negative sign **is** reproduced in all three
  windows and fails on strength.

There is a **six-month free trial** of ad-hoc historical EOD open-close that Don qualifies for
(filed Dec 2025, clarified Jul 2026, one-shot). D4's own recommendation was to spend it only
after O14 and U2 had run. Both have now run and both are NULL. **Nothing in the current
catalogue is gated on it. Do not spend the trial.**

**(c) The horizon premise is right, but its authoritative number is not the one quoted.** The
commission cites rank IC +0.034 at 1Q → +0.072 at 3Q+. That is correctly quoted from S22 §3b.
But S22's **verdict** is `CONSTANT-RATE`, and its own single sentence is *"annualized top-decile
alpha is essentially flat from three months to two years, +6.59% → +5.10%."* The edge does not
*intensify* with horizon; it **keeps accruing at a constant rate**, so the *cumulative* prize
grows — +1.65% at one quarter to **+10.20% at two years**, alpha HAC *t* never below 3.16 and
**3.83 at the longest horizon**. That is a materially different claim and it is the one a LEAPS
proposal rests on.

Two S22 riders must travel with it, because each kills a naive version of the idea:

* **"Nobody may quote a long-short figure beyond about one year."** LS HAC *t* falls
  2.7167 → 0.6846 across the eight horizons and only **4 of 8** horizons clear their own
  calibrated LS floor — the four failures are exactly Q5–Q8. **The persistence lives entirely in
  the long leg.** Any long-horizon options proposal must be long-only.
* **Top-decile tenure is a Kaplan–Meier median of ONE rebalance**; 70.6% of spells last exactly
  one quarter; one-period retention 36.6%. This kills *tracking* the decile with options — you
  would churn ~63% of the book quarterly at options spreads. It does **not** kill a
  hold-to-expiry position, because S22 measures the forward return of **the cohort selected
  today**, regardless of whether it stays in the decile. That is exactly what a held LEAPS is.

---

## 1. The observation the commission starts from, sharpened

Every dead options test asked "can we predict which options go up?" — and the record is worse
than that summary suggests, because **three separate published option signs failed to reproduce
here**: O7 vs Gao–Xing–Zhang (pre-earnings straddles measured **RICH**, −0.6739pp, CI excluding
zero), U2 vs Xing–Zhang–Zhao (`skew_25d` raw IC runs **positive**), and MA31 vs Cremers–Weinbaum
(every window **negative** against their positive +51bps/week). That is not three unlucky draws.
It is the signature of a megacap universe on which cross-sectional option forecasting does not
work, full stop.

But there is a second, quieter finding that constrains the frontier far more than any of the
rejections, and it is the strongest argument in the corpus **against** the whole family:

> **MA32:** on the options-listed sub-population the panel's own best-known signals cannot be
> separated from zero, and `size` dominates. Raw IC *t* decomposed across three nested
> populations: `gp_on_capital` **+3.6745 → +2.4776 → +0.9919**; `quality` **+3.1015 → +2.8014 →
> −0.0594**; `value` +0.8380 → +0.7505 → −0.0681; while `size` **flips −0.3005 → −0.7996 →
> +3.0765**. U7 independently: inside 187 megacaps the composite decile is *largely a market-cap
> sort* ($62.7B → $133.5B, D1→D9).

If that holds at the decile level, **every "express the equity edge in options" idea is dead
before a single contract is priced**, and no cleverness about tenor or delta rescues it. So I
measured it rather than assuming it. That is §2d, and it is the most consequential number in
this document.

---

## 2. Four measurements made for this commission (read-only, zero trials)

All four run on frozen artifacts already on disk. Scripts lived in the job scratch directory and
are reproduced in §7; **nothing was written into `valuation/` or `scripts/`.**

### 2a. The owned option cache is hard-capped at 200 DTE. LEAPS do not exist in any dataset we own.

| cache | ceiling | scope |
|---|---|---|
| `data/options/<TKR>/<TKR>-<YEAR>.pkl` (raw) | **200 DTE** on 2,836 symbol-years / **608 names**; **90 DTE** on 2,227 symbol-years | 1,044 ticker dirs |
| `data/options_derived/...` (per-contract greeks/IV) | same | 502 ticker dirs, 486 in the equity panel |

Measured directly: AAPL / MSFT / NVDA max DTE **90** (they carry no `.dte` sidecar, so they are
legacy-depth); AA / ADBE / ALB max DTE **200**, with 12.4% / 20.9% / 24.1% of rows beyond 90 DTE,
2.08% / 3.42% / 4.25% beyond 180 — and **0.000% beyond 365 on every name checked**.

**So the commission's class 1 is `NEEDS-DATA`, unambiguously.** The maximum tenor we own is
0.55 years against S22's two-year result — a 3.6× gap. Every dead options test used a ~60-day
contract; the honest intermediate that owned data *does* support is **180–200 DTE on 608 names**,
which is still ~3.3× the dead tests' tenor.

**But the data is a re-mine, not a purchase.** `THETADATA_API_KEY` is live; `dte_extend.py` and
`ThetaBulk(max_dte=..., upgrade_depth=True)` already exist and already executed this exact
manoeuvre once for O15 (90 → 200). Raising the ceiling to ~800 DTE is a parameter change on
working infrastructure. The costs are wall-clock and quota, not dollars — with two honest
riders: the account **serialises**, so heavy pulls run `--workers 1`, and **D2's licence finding
is unresolved** (individual tiers are "personal use only, no business use"; lawful commercial
starts ~$250/mo plus OPRA firm registration). A LEAPS re-mine adds **no new** licence exposure —
it inherits exactly the exposure every existing byte already carries — but it does enlarge a
position Don has not resolved.

### 2b. Deep-ITM calls are the cheapest part of the surface by an order of magnitude

`data/options_derived/AAPL/AAPL-2023.pkl`, calls only, by delta bucket:

| delta | n | median DTE | median `spread_frac` (of premium) | median moneyness |
|---|---|---|---|---|
| 0.0–0.2 | 9,810 | 32 | **10.00%** | 1.121 |
| 0.2–0.4 | 3,434 | 31 | 3.82% | 1.044 |
| 0.4–0.6 | 3,370 | 31 | 2.96% | 1.006 |
| 0.6–0.8 | 4,906 | 31 | 3.19% | 0.966 |
| 0.8–0.9 | 4,360 | 30 | 2.88% | 0.920 |
| 0.9–0.95 | 4,228 | 28 | 2.91% | 0.881 |
| **0.95–1.0** | **10,348** | 22 | **1.79%** | 0.814 |

The comparison that matters is not spread-as-%-of-premium but **spread as bps of notional**,
because that is what it costs to control one share. Across 20 liquid names × 10 years,
deep-ITM (δ≥0.85) one-way half-spread is **median 26.5 bps of notional** (p25 16.6, p75 44.0).
The 35-delta contract every dead test bought pays ~10% of a small premium; the 0.95-delta
contract pays **~27 bps of a large notional**. This is why the deep-ITM end is a different
instrument, not a re-parameterisation of the dead one.

*Caveat carried forward: O18 measured that real trades print at **rho 0.6743** of the quoted
half-spread (CI95 0.6617–0.6871), so quoted is an over-estimate — but O18's register forbids
quoting the 0.0545 availability term as a saving; only the price-improvement term is a property
of execution. I use quoted throughout, which is conservative.*

### 2c. The financing embedded in a deep-ITM call is risk-free + ~43 bps, flat across tenor

This is the arithmetic the commission says was never asked here. It never was. It is now.

Over matched `(date, expiration, strike)` call/put pairs with two-sided quotes and δ≥0.85, solve
put-call parity for the implied rate: `S − (C − P) = K·exp(−r*·T)`.

**Dividend-payers are excluded**, because ignoring `PV(D)` biases `r*` **downward** by an amount
growing with `T` — and that bias is visible: on a 20-name mixed sample the excess carry runs
+0.29 / +0.25 / **−0.29 / −0.88** pp across DTE buckets (20-45 / 45-90 / 90-140 / 140-200), a
spurious "long-dated financing is free" gradient that is entirely my own omission. On
**non-payers** (AMZN, GOOGL, ADBE, NFLX, TSLA, CRM, BKNG, ISRG, REGN, VRTX, MELI, WDAY, SNAP, SQ,
ZM — **1.54M pairs, 2016-2025**) the gradient vanishes and the estimate is unbiased:

| statistic | value |
|---|---|
| median `r*` − contemporaneous risk-free | **+0.43 pp** |
| by DTE bucket (20-45 / 45-90 / 90-140 / 140-200) | +0.40 / +0.44 / **+0.50** / +0.45 pp — **flat** |
| by year, 2016→2025 (median excess) | +0.31, +0.33, +0.76, +0.33, +0.32, +0.53, +0.27, +0.28, +0.45, +0.55 pp |
| share of pairs with `r*` above rf | 70.6% |
| share above a 5.75% margin rate | **9.4%** |
| share above 11.00% | **0.2%** |

Mids are used, which also favours the option (you buy the call at the ask and sell the put at the
bid), so this is a **lower bound on the embedded rate and an upper bound on the saving** in both
directions at once.

**Read plainly: the option market lends to a retail account at roughly the risk-free rate plus
40 bps, at every tenor, in every year including the zero-rate years and the 2023-25 high-rate
years.** Against Robinhood Gold at ~5.75% flat (≈ rf + 145 bps in 2025) that is a saving of
**~100 bps/yr**; against Robinhood's standard ~11-12% it is **~600+ bps/yr**.

And the cost that offsets it is §2b: a round trip is ~53 bps of notional. Annualised, that is
**~97 bps/yr at 200 DTE** — which very nearly *cancels* the saving versus cheap margin — and
**~26 bps/yr at 730 DTE**, which does not. **The financing case is real, small, and it only
becomes clearly positive at a tenor we do not own.** That single sentence is the honest state of
the commission's class 2, and it is also, independently, the strongest argument for paying the
re-mine cost in 2a.

### 2d. The gating control: the composite does NOT weaken on optionable names — it strengthens

Run on `data/free_analysis/panel_s22_h504.pkl` (S22's own panel, 113,945 rows / 2,531 names /
69 dates, carrying all eight forward-return columns). Composite = the seven deployed themes at
flat 1/7 with `low_risk` = 0, z-scored per date, renormalised by present-weight mass. Deciles
re-ranked **within** each universe, which is the right construction for "trade the best of what
is optionable".

| universe | H=63 | H=126 | H=252 | **H=504** | H=504 HAC *t* | median names/date |
|---|---|---|---|---|---|---|
| full panel (2,531 names) | +1.87% | +3.77% | +6.81% | **+10.59%** | 4.13 | 1,557 |
| optionable only (486 names) | +2.78% | +6.03% | +13.35% | **+17.52%** | 3.22 | 409 |
| 200-DTE-deep only (567 names) | +1.87% | +4.81% | +11.86% | **+18.58%** | 3.31 | 444 |

Restricted to 2016+ (41 dates), where optionability is roughly contemporaneous rather than
imposed retrospectively: full panel +13.70%, optionable **+22.39%** (t 2.54), deep **+23.47%**
(t 2.47) at H=504.

**Four caveats, and they are load-bearing:**

1. **This is not a verdict and my instrument is not the shipped one.** My C1 reproduces S22's
   published all-dates H=63 annualised alpha at **+7.48% against +7.17%** — within 0.31pp, close
   enough to say the composite is substantially right, **not** close enough to publish a number.
   The real gate must call the shipped builder, which reproduces the record to the digit.
2. **Optionability is measured TODAY, not point-in-time.** A name with a liquid 2024 chain was,
   in 2009, disproportionately a future winner. That is a survivorship tilt in exactly the
   flattering direction, and it is the same class of defect as the non-PIT sector map. The
   2016+ restriction shrinks it but does not remove it. **The fix already exists and is
   adopted: O20's PIT option-universe partition.** The real gate must use it.
3. **It does not contradict MA32, and saying so would be sloppy.** MA32 measured *signal-level*
   IC on the rows its arms could actually be computed on — contract-level, two-sided quotes on
   both legs, ~431 names/date on 40 covered dates. This measures *decile-level* alpha on "the
   name has a chain at all", ~409-444 names/date across 69 dates. Different populations,
   different statistics. **Both can be true**: individual themes can be indistinguishable from
   zero on a narrow megacap slice while the seven-theme composite still sorts a broader
   optionable universe. Reconciling them is itself a registered arm, not an aside.
4. The optionable decile is **~41 names against ~156**, so it is a more concentrated, noisier
   book, and H=504 rests on 34-62 non-independent dates.

With those four attached: **the single fact most likely to have killed this family did not kill
it.** That moves the whole class from "probably foreclosed" to "worth one properly-registered
session", and it is why the ranking in §3 looks the way it does.

### 2e. By-product — U6's coverage blocker is measured against the wrong leg

U6 is `DESIGN-RECORDED / NOT BUILDABLE ON DATA WE OWN` on a measured **1.81%** chain coverage:
*"of 7,132 names ENTERING the top decile across 68 transitions only 129 have mined chains"*,
with **zero covered entries on 18 of 68 dates**. That number is correct for what it measures.

But U6 is a **two-leg** proposal — cash-secured puts on the entry leg, covered calls on the exit
leg — and an overwrite is written on **holdings**, not on transitions. Measured on decile
*membership*:

| | median per date | share of all top-decile slots | dates with none |
|---|---|---|---|
| top-decile size | 155 | — | — |
| with a derived chain | **19** | **11.3%** | **0 of 69** |
| with 200-DTE depth | **34** | **20.7%** | **0 of 69** |

So the overwrite leg has **~6-11× the coverage** the row's blocker asserts, and there is no date
on which it is unbuildable. This does not overturn U6 — the CSP entry leg genuinely is
coverage-bound, and U6's own correction note already conceded one of its two blockers was false —
but **the row currently reads as though both legs are dead, and one of them is not.** Worth a
ledger note whatever else happens. (Same caveats as 2d: my composite, today's optionability.)

---

## 3. Proposals, ranked by expected value

Options `N` = **287**, so the Harvey–Liu–Zhu hurdle is √(2·ln 287) = **3.36**. Every trial cost
below is charged against that.

### P1 — Deep-ITM long-dated calls as a *financed* expression of the equity top decile
**Rank 1. Fuses the commission's classes 1 and 2, which are the same trade.**

This is the only proposal here I would actually spend three sessions on.

**MECHANISM.** Two economically separate payments, and the case rests on keeping them separate:

* **The equity alpha, which is already measured and is not an options claim at all.** S22:
  cumulative top-decile alpha **+10.20% at 504 days**, alpha HAC *t* 3.83 at that horizon, every
  one of eight incremental quarters positive, rank IC plateauing at +0.070-0.073. §2d indicates
  it survives — and may strengthen — on optionable names. A held deep-ITM call with δ≈0.9 is a
  ~1.0-beta claim on that return, levered ~2-3× by paying ~35-45% of spot.
* **The financing spread, measured in §2c: rf + 43 bps versus retail margin at rf + 145 to
  rf + 670.** A deep-ITM call is the *only* option that collects this without paying for the
  things that killed every dead test: it is nearly all intrinsic, so it pays little variance risk
  premium (V6-OPT measured VRP at +0.0391 vol points; vega at δ≈0.95 is a small fraction of ATM
  vega), and it pays **27 bps of notional** rather than 10% of premium (§2b).

**The reframe that matters: this is a leverage decision, not an alpha discovery.** The question
is not "can we forecast options" — the entire record says no. It is *"for a book whose alpha is
already measured and persists two years, are options the cheapest available leverage?"* That
question has never been asked here, it is arithmetic rather than forecasting, and §2c says the
answer is plausibly yes.

**WHY IT SURVIVES — who is on the other side.** This has a real published answer, which most
proposals in this catalogue do not. **Frazzini & Pedersen, "Embedded Leverage" (NBER w18558):**
instruments with embedded leverage offer *low* risk-adjusted returns because they relax
investors' leverage constraints; a portfolio long **low**-embedded-leverage and short
**high**-embedded-leverage securities earns large abnormal returns, **t = 8.6 for equity
options**. Deep-ITM is the low-embedded-leverage end — the long leg of that trade. The mechanism
is a *constraint*, not a mispricing: leverage-constrained investors bid up OTM lottery tickets
and leave the unglamorous deep-ITM end cheap, and **capturing it requires being
leverage-constrained**, which is precisely Don's position. An unconstrained arbitrageur has no
reason to compete for it, because for them margin is already cheap. The counterparty is a market
maker funding at wholesale who is content to lend at rf + 43.

This is the strongest "why has this not been arbitraged" answer available anywhere in the
catalogue, and it is the main reason P1 ranks first despite a modest expected size.

**WHAT DATA, AND DO WE OWN IT.** *Partially.* 180-200 DTE on 608 names: **owned** (§2a) — enough
for a real dry run. 365-730 DTE: **not owned, zero rows**, obtainable by re-mining an existing
subscription with `dte_extend.py` (§2a), at wall-clock-and-quota cost, `--workers 1`, inheriting
D2's unresolved licence question. The equity side needs nothing new: `panel_s22_h504.pkl` exists.

**THE REGISTER.**

*Stage 0 — the gate, and it runs alone.* Redo §2d with **the shipped composite builder** (must
reproduce the published H=63 figures to the digit, C1-style) and **O20's PIT optionable
partition**. Pre-commit the bar before looking: top-decile alpha on the PIT-optionable universe
at H=252 and H=504 must clear its own per-horizon `placebo_panel` floor (200 draws, the S22
protocol) **in both halves**. **Kill condition: if it fails, the entire family dies here and no
option is ever priced.** Zero options trials — this is an equity measurement. ~1 session.

*Stage 1 — the instrument, on owned 200-DTE data.* Arms, all held to expiry, no exit rule
(deliberately: every exit rule is dead per O1/O23, and a hold-to-expiry policy is the *absence*
of the dead object, not a variant of it):

* A1: δ≈0.90 call, longest owned tenor (180-200 DTE), on the PIT-optionable top decile.
* A2: δ≈0.70, same names and dates — tests whether the result is monotone in moneyness, which
  Frazzini–Pedersen predicts it should be.
* A3: δ≈0.35 at the same tenor — **the incumbent geometry at the new tenor**, which separates
  "tenor was the problem" from "delta was the problem". Without A3 the study cannot attribute.

*Controls, this project's standard, all mandatory:*

* **The stock expression is the primary control** and the comparison is *per dollar of exposure*,
  not per dollar of premium. The proposition is "cheaper leverage", so the arm must beat
  **stock-on-margin at a stated rate** — pre-commit Robinhood Gold's rate, the hostile choice —
  and be reported against standard margin too.
* **Random entry, ≥5 seeds pooled**, matched on date and market-cap tier (U1's cap-matched null,
  which subtracted U7's mechanism rather than acknowledging it).
* **Both halves**, embargoed at 2021-01-21 — the geometry U2, U3, V6-OPT and MA31 all landed on.
* **C-SETTLE:** strikes are as-traded, `data/backtest/prices` is adjusted. Settle on the derived
  layer's own `spot`; use the adjusted close only for the stock control's *return*. This trap has
  now bitten U1-SPLIT, O7 and V6-OPT — three times.
* **C-DIV:** deep ITM on payers has a real early-exercise obligation (see P3). Report payers and
  non-payers separately; the headline is non-payers, where §2c is unbiased.
* **C-CARRY:** re-derive §2c's implied rate on the exact contracts the arm buys. If it is not
  rf + ~40 bps on the traded set, the mechanism is absent and the arm is uninterpretable.

*Kill conditions, fixed in advance:* (i) Stage 0 fails; (ii) A1 fails to beat the stock-on-margin
control net of quoted spreads in **either** half; (iii) A1 does not beat the cap-matched random
null at p95; (iv) the delta gradient A1 > A2 > A3 does not hold in sign (the mechanism predicts
it; its absence means something else is driving the number).

*Trial cost:* Stage 0 = 0 options trials. Stage 1 = **3** (three delta arms; tenor is not a
free parameter, it is the maximum owned). Options N 287 → 290. A LEAPS re-mine adds 2-3 more.

**HONEST PROBABILITY, stated before anyone runs it.** Decomposed, because the joint number hides
the informative part:

* the financing sub-claim (rf + ~40 bps, beats retail margin) replicates on traded contracts:
  **~85%** — largely measured already;
* Stage 0 passes with the shipped builder and PIT optionability: **~65%** (§2d indicates yes;
  PIT and the real builder can move it, and MA32 is a genuine warning);
* **A1 beats stock-on-margin net of costs in both halves at owned 200-DTE tenor: ~25%.** The
  round-trip spread almost exactly cancels the financing saving at 0.55 years (§2c);
* the same at 730 DTE if the re-mine happens: **~40%**;
* **the whole thing turns into something Don should trade: ~15%.** O11 is why — a book with
  *positive* +3.27%/trade expectancy still lost money at $50k with a concentration cap of 10,
  ending at $37,059 after a 67% drawdown. Options sizing has killed a positive-expectancy book
  in this project before, and O12 found no Kelly fraction that is usable (CI includes zero).

**Why it still ranks first at 15%:** every stage is individually informative, Stage 0 is free and
answers a question that gates six other items, and the failure modes are *arithmetic* — they
resolve to numbers rather than to "the signal decayed".

---

### P2 — Early-exercise discipline on any deep-ITM position (a prerequisite, not an edge)
**Rank 2 by ratio of value to cost, because the cost is zero.**

**MECHANISM.** Pool, Stoll & Whaley (JFM 2008): US exchange-traded calls are unprotected against
cash dividends, so it becomes optimal to exercise deep-ITM calls the day before ex-dividend.
**More than half of outstanding long positions go unexercised**, costing holders **>$491M over
ten years**, and **market makers capture the lion's share** through the dividend-spread trade.

**WHY IT SURVIVES.** It survives because it is a *retail error*, not a mispricing — and this is
the one item in the document where Valquo would be on the **losing** side by default. Nobody
arbitrages it away because the arbitrage *is* the market maker's dividend spread, which needs
zero-cost exercise and pro-rata assignment. Don cannot run that trade.

**WHY IT MATTERS HERE.** O21 measured early exercise as **IMMATERIAL** on the current book — 34
of 3,870 exits below intrinsic (0.879%), worth +0.2002pp against a 1.00pp bar. That verdict is
correct **and it does not transfer**, because the current book is 100% short-dated calls at mean
delta +0.3725. P1's instrument is δ≈0.9 held for months. Exposure is already large: **81.4% of
trades sit on payers, median trailing yield 2.02%, and 2,107 of 3,870 calls span an ex-div
date.** At δ≈0.9 that becomes a live obligation on every ex-div date.

**REGISTER.** None — this is not a hypothesis. It is an operating rule and a pre-flight check
that must exist **before** P1 Stage 1 prices a single payer, plus a note on the O21 row that its
IMMATERIAL verdict is scoped to δ≈0.37 short-dated calls.

**DATA.** Owned (`datekey`/dividend data in the Sharadar export; the derived layer has δ).
**TRIAL COST: 0.** **PROBABILITY: n/a** — it is a known, published, quantified leak, not a bet.

---

### P3 — U6's overwrite leg, re-opened on the corrected coverage number
**Rank 3.**

**MECHANISM.** Write calls on top-decile *holdings*. S22 supplies the reason this is not free
money and must be registered carefully: **top-decile alpha is still accruing at two years**, so a
call written on a name you still hold is written on a population whose forward return is
measurably **not** zero — you are selling the thing you are being paid for. U6's own memo says
exactly this.

**WHY IT SURVIVES.** Weakly. The buy-write premium is a well-documented risk transfer, not an
anomaly. **Label: this is closer to a lottery ticket than P1** — I cannot name a constrained
counterparty who must sell to us. What it has instead is a *cost* argument: it monetises the
25-delta wing where spread is 10% of a small premium, which §2b says is the expensive end.

**WHAT'S NEW.** Only §2e: the blocker on this leg is ~6-11× smaller than the row records
(19 optionable / 34 deep names per date, **no date with zero**), because U6 applied an
entry-leg coverage number to a two-leg proposal.

**REGISTER.** One arm (write ~25-delta, ~45 DTE, on optionable top-decile holdings, roll
quarterly), controls: the un-overwritten stock book as primary, ≥5-seed random-name overwrite
matched per date, both halves. **Kill: any reduction in cumulative H=252 alpha beyond the premium
collected** — i.e. it must not sell the persistence. Inherits O25's finding that the wing is
*reliably worse* than closing or holding (−9.34pp / −13.03pp, both halves, all CIs excluding
zero) — **O25 is short-dated and post-move, so it is not this, but it is the prior and it is
unfavourable.** **Trial cost 1-2.** **PROBABILITY: ~15%.**

---

### P4 — Expiration pinning (Ni, Pearson & Poteshman, JFE 2005)
**Rank 4 — measurable, almost certainly not tradeable. Included because it is real and the
commission asked for structural mechanisms.**

**MECHANISM.** Real and well identified: market-maker delta-hedge rebalancing as option deltas
move sharply near expiry causes optionable stock closes to cluster at strikes. Returns on
optionable stocks are altered by **at least 16.5 bps** on expiration dates, ~$9B of aggregate
market cap.

**WHY IT SURVIVES.** It is a mechanical hedging flow, not a forecast, so it does not get
competed away in the usual sense. **But 16.5 bps is the whole effect**, against a one-way
deep-ITM half-spread of 26.5 bps and an OTM spread of 10% of premium. **The mechanism is real and
the magnitude is fatal** — it is smaller than one leg of the cost of expressing it.

**TESTABLE-HERE**, and cheaply: strikes, open interest and daily closes are all owned. It should
be run **as a disclosure, not a screen** (the MA29/MA30 pattern), if it is run at all.
**Trial cost 1.** **PROBABILITY it produces a tradeable rule: ~3%.** Probability it reproduces
as a measurable effect: ~60%.

---

### P5 — Regime conditioning of the options book (the commission's class 5)
**Rank 5, and I recommend against it.**

Nothing options-side was ever conditioned on vol regime and the tree has regime machinery
(`quant_bots/core/regime.py`), so the commission's factual premise is right. But **conditioning a
dead entry signal on a regime variable is R2 in costume**, and it is the single most common way a
rejected result gets resurrected: 32 arms in O13 already sliced the anti-signal every way the
label vocabulary allowed and found the gap is **entirely a within-bin rate effect** (−4.23pp to
−5.79pp against a −5.0640pp total; largest mix component anywhere 0.7711pp). The alert does not
lose by picking different contracts — **it loses inside every kind it picks.** Regime is another
binning of the same book.

**Independent corroboration, which is why this is a recommendation and not a preference.**
`VALQUO_MASTER_AUDIT_ULTIMATE.md:114` records that the external-research lane, working from the
2023-2026 literature and *not* from this project's results, arrived at the same stop-list as the
internal MA24 §12 pass: **"ML combiner, regime/vol overlays, VRP."** Two lanes reached
"regime overlays are not where the edge is" by independent routes. That is stronger evidence than
either produced alone, and it is the closest thing to an out-of-sample verdict this question will
get without spending trials on it.

**The one non-disqualified version:** regime as a *pre-registered conditioning variable inside
P1's Stage 1*, declared before the run, on the new instrument. Not as its own study.
**Standalone trial cost: 2-3, and I would not spend them.** **PROBABILITY: ~5%.**

---

### P6 — Index-level GEX
**Rank 6. NEEDS-DATA, and the data is the point.**

Single-name GEX is dead here twice over (§0a) and on a contaminated instrument. The *published*
evidence is index-level — Jonsson & Nyberg (2025) find the **derivative** of GEX significantly
related to subsequent S&P 500 returns, robust pre- and post-2020 with diminished strength after;
Baltussen et al. (JFE) give the intraday-momentum mechanism. **We own no index chain**; the cache
is single-name equity only. Acquiring SPX/SPY chain history is a fresh mine (feasible on the
existing key) or a purchase.

**WHY IT SURVIVES:** poorly answered. The effect is publicised to the point of being a retail
product (SpotGamma et al.), which is the classic post-publication decay setup — and MA34, *"write
the post-publication decay prior into the register"*, is **OPEN**, so this project does not yet
have the machinery to score it honestly. **PROBABILITY: ~7%.** Do not spend on it before MA34.

---

## 4. Near-miss disqualifications — required by the hard rule, item by item

Each dead thing, and whether any proposal above is it in costume.

| Dead item | Verdict | Is anything above this in costume? |
|---|---|---|
| **R2** entry signal vs random | REJECTED, −5.0640pp split-clean | **No.** P1 uses the *equity composite* at a 3-8× tenor with a 2.5× delta and no exit rule. But P5 **is** this in costume, and is disqualified above on exactly that ground. |
| **U1** equity composite → options entry | REJECTED; TOP10 −1.1892pp, fails all four conditions | **This is P1's closest call and it must be argued, not waved.** U1's own write-up carves out the re-opening: *"it does not refute the equity composite, whose rank IC RISES with horizon (S22) while a 30-75 DTE contract lives at the short end where it is weakest — pre-registered in section 1 as testing the composite where it is least strong."* P1 differs on **three** axes at once (tenor 200-730d vs 30-75d; δ≈0.9 vs ≈0.35; hold-to-expiry vs +100/−50). U1's mechanism finding also does not transfer: *"every decile's MEDIAN trade is between −52.5% and −54.3% — all ten"* describes 35-delta short-dated calls whose median outcome is near-total loss; a δ≈0.9 two-year call's median outcome is the stock's median outcome, levered. **Not in costume — but P1 must cite U1's carve-out in its register and pre-commit that a failure at 200 DTE closes the family rather than prompting a fourth tenor.** |
| **U2** surface → stock signals | REJECTED, all four arms | **No.** P1 uses no surface feature as a predictor; it uses the surface only to *price* an expression of an equity signal. |
| **O13** the inverse / anti-signal | DIFFUSE; inverse NULL | **No.** Nothing above shorts the gap. O13 is cited *against* P5. |
| **O1 / O23 / path study, 13 arms; all exit rules** | REJECTED / NULL | **No — and P1 goes the opposite way.** P1 has *no exit rule*: hold to expiry. That is the absence of the dead object. O23's Greek attribution is in fact P1's supporting evidence — delta 50.70% of absolute mark movement, and gamma +0.8528 / theta −0.7708 **nearly cancel**, leaving delta +0.4617. *"What survives is the direction of the stock."* A δ≈0.9 hold-to-expiry call is the instrument that keeps only that term. |
| **O3 / O4 / O5** vol-surface anomalies | NULL ×3 | **No.** No proposal sorts on idio vol, expected skew or vol-of-vol. |
| **O14** tick flow | ALL FIVE ARMS NULL | **No.** No proposal uses flow. Note the cache is alert-days only and covers 0 of 3,870 next-sessions (O10). |
| **O6 / O7 / O17** earnings straddles & filters | NULL / REJECTED | **No.** P1 does not select on the surface, does not trade the event, and does not filter on earnings. O17's finding cuts *toward* holding through: avoiding earnings gets monotonically **worse** as the window widens (+0.797 / −0.479 / −1.429 pp at 5/10/15d). |
| **V6-OPT** CSPs on healthy dips | Stage 1 GATE OPEN; Stage 2 REJECTED | **P3 is adjacent and must be distinguished.** V6-OPT rejected because *the health floors do no work* — a 25-delta put is a 25% assignment probability **by construction**, so strike selection had already spent the risk difference. P3 writes **calls on holdings**, selected by the composite rather than by a dip filter, and inherits V6-OPT's warning that a delta-targeted strike is blind to a priced risk difference. If P3 is registered on a *delta* target it repeats V6-OPT's defect; **it must target moneyness**, which V6-OPT explicitly named as the obvious re-opening. |
| **126-feature autopsy** | REJECTED, n=126, zero FDR discoveries | **P6 would be this in costume** — four GEX features are inside that family. Disqualified above; only the untested *index-level* variant survives, and on data we do not own. |
| **O9 / O8** short vol, IV rank | REJECTED / INCONCLUSIVE; *"the short-vol question is CLOSED"* | Disqualifies **Goyal–Saretto** (IV minus historical vol) — see §5. P3 is short a *call against stock*, not short vol standalone; the distinction is real but thin and must be declared in its register. |
| **O16 / O24 / MA56** term_slope | IS DISTINCT / NULL / RECORDED-NOT-RUN | **No.** No proposal uses term_slope. MA56's carry-forward is explicitly *"do not run today"* and its residual IC was measured **against a losing book**. |
| **MA31** put-call parity deviation | NULL and uninterpretable | **Adjacent and worth naming.** MA31 used matched call/put pairs as a *predictor of stock returns*. §2c uses the identical construction as **pricing arithmetic** — solving for an implied rate rather than sorting on a deviation. Same data, different question, no verdict inherited. It also inherits MA31's warning: pair-level two-sided availability is roughly the **square** of the leg-level rate, so P1's n will be smaller than a naive count suggests. |

### 4b. Where this commission's hard rule collides with an OPEN ledger row — Don's call, not mine

The hard rule names **O6 / O7 / O17** dead and disqualifies anything that is them in costume. I
have applied it. But **MA54 is `OPEN` in the ledger and proposes new pre-registerable designs for
three of the items this commission forecloses**, on the argument that their failing leg was *an
instrument the arm could not move* rather than an absent effect. Silently applying the hard rule
over an open audit row would hide a real disagreement, so it is reported instead of resolved:

* **MA54-2, O17-C4 "own the event".** Measured **+4.686pp/trade**, positive in both halves,
  clearing its own calibrated null in both, positive in **every DTE quartile** — and recorded
  NULL **solely** because retention 0.5706 fell under a 0.70 floor *set for a product reason*.
  MA54's new design registers it as its own **book** (an entry rule, not a filter), judged on
  expectancy vs matched random entries, so the retention floor does not exist by construction.
  MA54 itself attaches the caveat that it sits behind R2's dead entry. **This is the largest
  un-harvested measured effect in the options catalogue**, and this document does not propose it
  only because the commission forbids it by name.
* **MA54-3, O14 `sweep_share`** — the one options arm to survive Benjamini-Hochberg, sign-stable
  across halves, NULL only because the late half missed its own bar by **0.16 of a t**. New
  design: collect Lee-Ready sweep-share on **new dates** (the optionable panel's rebalance dates)
  as an *equity-side* conditioner under the incremental-IC gate. **~4.7 GB pull.** This is the
  live version of the commission's class 4, and it is a better use of a data pull than D4.
* **MA54-4, O6** — the cheapness rules **changed the delta** rather than holding exposure fixed,
  so cheapness-at-fixed-exposure was never tested. **This is a direct constraint on P1's design,
  and P1 already honours it**: P1 compares *per dollar of exposure*, treats delta as an explicit
  arm (A1/A2/A3) rather than an uncontrolled by-product, and requires the gradient to hold in
  sign. MA54's prescribed remedy — score on the non-delta residual via O23's Greek attribution,
  or use delta-matched pairs — should be adopted verbatim in P1's register.

**Recommendation:** treat the hard rule as binding for this document, and put MA54-2 to Don
separately as an explicit re-open request with its history attached. It is not my call to
override a commission, and it is not right to let a +4.686pp both-halves result sit unmentioned
because of a phrase written before MA54 was read.

---

## 5. Literature map — what the field knows that this project has not absorbed

| Result | Status here | Detail |
|---|---|---|
| **Frazzini & Pedersen, Embedded Leverage** (NBER w18558) | **TESTABLE-HERE (partial) / NEEDS-DATA (full)** | Long low-, short high-embedded-leverage options: **t = 8.6** in equity options. *Mentioned nowhere in the corpus.* This is **P1's mechanism** and the best "why it survives" answer available. Testable to 200 DTE on owned data; the LEAPS version needs the re-mine. |
| **Pool, Stoll & Whaley, Failure to Exercise** (JFM 2008) | **TESTABLE-HERE** (owned) | >50% of ITM positions unexercised, **$491M/10yr**, MMs capture it. **P2.** O21 covers the *current* book only and does not transfer to δ≈0.9. |
| **Ni, Pearson & Poteshman, Expiration pinning** (JFE 2005) | **TESTABLE-HERE** (owned: strikes, OI, closes) | **≥16.5 bps** on expiration dates. **P4** — real mechanism, magnitude below one leg of cost. |
| **Ge, Lin & Pearson, open-vs-close** | **ALREADY-TESTED-HERE — MA32, both arms NULL** | Declared negative sign reproduced in all three windows, fails on strength. Buying D4 would re-buy a closed question. |
| **Cremers & Weinbaum, parity deviation** | **ALREADY-TESTED-HERE — MA31, NULL + sign not reproduced** | Every window negative against their +51 bps/week. |
| **Goyal & Saretto, IV−HV deviation** | **ALREADY-TESTED-HERE, and disqualified twice** | `vrp` scored in the v2 gate: late +0.54pp, **early −3.11pp**, `reject`. It is also short-vol, and O9's pre-registration **closed** that question. Do not re-open. |
| **Cao & Han, idio vol; Boyer & Vorkink, skew; vol-of-vol** | **ALREADY-TESTED-HERE — O3 / O4 / O5, all NULL** | O4 is informative: the literature's *expected*-skew construction is **stronger** than the prior lane's realised one (1.9143 vs 1.5805). Prefer it in any future register. |
| **Xing, Zhang & Zhao, skew** | **ALREADY-TESTED-HERE — U2, sign not reproduced** | `skew_25d` raw IC runs positive. |
| **Gao, Xing & Zhang, pre-earnings straddles** | **ALREADY-TESTED-HERE — O7, sign contradicted** | Options measured **RICH** on this megacap universe; their effect is strongest in small firms, which this book has none of. |
| **Jonsson & Nyberg (2025); Baltussen et al., GEX** | **NEEDS-DATA (index chain) — single-name version already dead** | **P6.** Index-level only; heavily publicised, and MA34 (decay prior) is OPEN. |
| **Heston & Sadka, return seasonality** | **TESTABLE-HERE — and it is already ledger row MA58, OPEN, never run** | *Equity*, not options; owned daily closes; trial cost 1-2. Outside this commission's mandate but it is the cheapest un-run external result in the catalogue and deserves the mention. |

---

## 6. The answer the commission asked for

**Given everything dead, where would I spend the next three sessions?**

**Session 1 — P1 Stage 0, and nothing else.** Re-run §2d with the shipped composite builder and
O20's point-in-time optionable partition, against per-horizon placebo floors in both halves. It
charges **zero options trials**, needs **no new data**, takes about a session, and it is the
single gate under six separate items — P1, P3, U6, and any future attempt to express the equity
book in derivatives. My §2d run says it probably passes; my §2d run is also not the shipped
instrument, which is exactly why it must be redone rather than cited. **If it fails, stop. The
whole family is closed, cheaply, and that is a good outcome.**

**Session 2 — P1 Stage 1 on owned 200-DTE data**, three delta arms, held to expiry, stock-on-margin
as the primary control and cap-matched 5-seed random entry as the null. This is a **dry run at
insufficient tenor and it should be labelled one**: §2c says the round-trip spread nearly cancels
the financing saving at 0.55 years, so the *expected* outcome is "does not clear, for a reason we
can compute in advance". Its value is that it tests the **delta gradient** — A1 > A2 > A3 — which
is Frazzini–Pedersen's prediction and is what distinguishes a real mechanism from a tenor
coincidence. It also closes U1 properly, on U1's own carve-out.

**Session 3 — conditional, and the condition is set in advance.** If the gradient holds in
session 2, spend it on the **LEAPS re-mine** (`dte_extend.py` with the ceiling at ~800 DTE,
`--workers 1`, on the 608 already-deep names), and route D2's licence question to Don **before**
the pull rather than after. If the gradient does not hold, spend it on **P2** — the early-exercise
operating rule and the O21 scope note — and then stop working on options.

Alongside all three, and free: **P2's operating rule**, the **§2e ledger note** correcting U6's
blocker to the leg it actually measures, and **§4b's re-open request for MA54-2 (O17-C4) routed to
Don** — a +4.686pp/trade, both-halves, every-DTE-quartile result currently NULL on a product-policy
retention floor, which this commission forbids me to propose and which somebody should decide about
on purpose rather than by inheritance.

**And what would I never touch again?**

**Forecasting.** Every variant of "which options will go up" — direction, implied vol, skew,
term structure, flow, dealer positioning, earnings timing, entry rules, exit rules. That question
has been asked 26 ways in the O-series alone, plus U1, U2, U7, R2, R7, MA31, MA32, the 126-feature
autopsy and three failed replications of published signs, and it has never once returned a
survivable answer on this universe. The record is not ambiguous and it is not underpowered — O7,
U2 and MA31 each *contradicted* a published sign rather than merely missing it. **Specifically and
permanently: do not re-open exit rules (O1/O23 settled it — delta is what survives, gamma and
theta cancel), do not re-open short vol (O9 closed it by pre-registration), do not re-open
single-name GEX or anything else inside the 126-feature family, do not buy D4, and do not
condition a dead book on a regime variable and call it new.**

The one thing the record has *never* tested is whether options are cheap **plumbing** for an edge
that already exists somewhere else. §2c is the first measurement in this project's history to
suggest they might be: **rf + 43 bps, flat across tenor, stable across ten years.** That is not an
edge — it is roughly 100 bps a year against cheap margin and 600 against expensive margin, and
O11 is a standing reminder that a positive-expectancy options book can still lose money at real
account sizes. But it is the only door in the building that nobody has tried, and it is arithmetic
rather than prophecy, which means it will give a clean answer either way.

---

## 7. Reproducing §2 (nothing here was written into the repo)

All four measurements ran from a scratch directory against read-only artifacts:

* **§2a** — `.dte` sidecar census over `data/options/*/*.dte` (absent sidecar ⇒ 90 by
  `theta_bulk.LEGACY_MAX_DTE`), plus direct `max(expiration − date)` on AAPL/MSFT/NVDA (90) and
  AA/ADBE/ALB (200).
* **§2b** — `data/options_derived/AAPL/AAPL-2023.pkl` grouped by delta bucket; notional
  half-spread = `spread_frac/2 × mid / spot × 1e4`.
* **§2c** — matched `(date, expiration, strike)` call/put pairs across
  `data/options_derived/<TKR>/<TKR>-<YEAR>.pkl`, δ≥0.85, `mid > 0.05`, `dte ≥ 20`;
  `r* = −ln((S − C + P)/K)/T` with `S` the derived layer's own as-traded `spot`; excess measured
  against the file's own `risk_free` column. Non-payer basket named in §2c.
* **§2d / §2e** — `data/free_analysis/panel_s22_h504.pkl`; seven deployed themes at flat 1/7 with
  `low_risk = 0`, per-date z-scores renormalised by present-weight mass; deciles by
  `nlargest(len(g)//10)`; HAC lag `max(1, H/63 − 1)`, matching S22's overlap correction.

**Instrument caveat, restated because it governs every number in §2d/§2e:** my composite
reproduces S22's published all-dates H=63 annualised alpha at **+7.48% against +7.17%**. That is
close enough to scope a decision and **not** close enough to publish. Nothing in §2d or §2e is a
verdict, none of it is calibrated against a placebo floor, and none of it may be quoted as a
result. It exists to rank the proposals in §3.
