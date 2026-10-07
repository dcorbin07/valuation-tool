# PREREG DRAFT — STAGE-1 BATCH 3 — nine arms from the published literature

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no outcome statistic is computed, no
trial is booked, nothing is measured. A register is committed **ALONE** (markdown only, zero
`.py`, a strict git ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**Why it comes from the literature:** batch 2 found `IDEAS_LEDGER.md` **exhausted** — its season
portfolio `E-1`…`E-6` is fully spent and its `PARKED` list is options-lane, licence-blocked,
already landed, or needs data this project does not own. Don's ruling is to test everything that
makes sense, so the source of candidates moves outward.

---

## 0. WHAT EVERY ARM BELOW INHERITS

From charter §5 as repaired on 2026-10-07:

* **The incremental control is the DEPLOYED COMPOSITE**, one column from `composite_from_frame`
  (called, never re-implemented), z-scored within date — not complete-case residualisation on
  seven themes. All **44** build-quadrant dates survive; halves **24 / 20** at 2014-12-31.
* **Scored on BOTH populations, and the `cap >= $10B` TIER GOVERNS.** An arm that passes wide and
  fails the tier is `REAL BUT NOT INVESTABLE HERE` and does **not** reach Stage 2.
* **Costume kill in its own pass**: mean per-date |ρ| against **each** theme, bar **0.60**, before
  any forward return is touched.
* **Coverage is measured on the arm's own rows, on the governing population** — `O-1` applied an
  alert-book figure to the panel and was **~17× wrong**.

### 0a. THE BARS: use the CORRECTED universe's own floors, and DERIVE them

`CORRECTED-FLOORS` part 1 swept X7's placebo on this universe. **Its floors, not the old panel's:**

| floor | old (`N`=247) | **corrected** | harder? |
|---|---|---|---|
| theme IC *t* (p95) | 2.707234 | **2.885180** | **HARDER** |
| long-short naive *t* (p95) | 2.070231 | 1.510224 | easier |
| long-short HAC *t* (p95) | 2.056680 | 1.485155 | easier |
| top-decile alpha margin (p95) | 0.018629 | 0.009738 | easier |
| top-decile alpha HAC *t* (p95) | 1.826210 | 1.642480 | easier |
| PBO (p05) | 0.196667 | **0.133333** | **HARDER** |
| Deflated Sharpe (p95) | 0.663664 | 0.591244 | easier |

**NO FLOOR MAY BE TYPED AS A LITERAL.** Part 1 pinned that by test *"because the record carried a
superseded 1.95pp alpha margin for nine days for exactly that reason."* Every bar is **read from
the artifact** at run time.

**AND THE THEME-IC FLOOR IS NOT AN INCREMENTAL-IC FLOOR.** `MB22`/`U2`'s rule is explicit:
`ic_tstat` carries the calibrated bar and `ic_inference.t` *"is a NEW statistic with NO calibrated
floor — nobody may compare it to 2.71."* The same holds at 2.885180. **So a Stage-1 incremental-IC
arm is judged by BH plus the both-halves rule, and the corrected floors are quoted only for the
statistics they were calibrated on.** Writing 2.885180 beside an incremental *t* would be
`R1-VAR`'s category error.

### 0b. THE BATCH IS NINE ARMS, MEMBERSHIP FIXED HERE

**Benjamini-Hochberg at q = 0.10 across `k` = 9**, the *i*-th smallest *p* against *i* · 0.10 / 9:

| i | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| threshold | .01111 | .02222 | .03333 | .04444 | .05556 | .06667 | .07778 | .08889 | .10000 |

**An arm that cannot be built is NOT RUN and `k` STAYS 9.** All nine are incremental-IC arms, so
**all nine are in the BH set** — unlike batches 1 and 2, this batch needs no margin-only exclusion.

### 0c. ONE MOTIVATION THAT IS BANNED, AND NOT ONE ARM BELOW USES IT

**"It is structurally orthogonal to the incumbents" is a dead motivation on this record and no arm
here rests on it.** `U2`, `MA31`/`MA32`, `MA58`, `MB18` and `D6` — **five items**, every one
confirmed orthogonal at R² **0.027–0.158**, and **not one cleared.** `CLAUDE.md` already names it
as a motivation nobody should run again. Every arm below is motivated by a **published return
result**, and its orthogonality is a *kill input*, never an argument for it.

---

## 1. C1 — ABARBANELL-BUSHEE FUNDAMENTAL SIGNALS *(1997, 1998)*

**Paper.** Abarbanell & Bushee, *"Fundamental Analysis, Future Earnings, and Stock Prices"* (JAR
1997) and *"Abnormal Returns to a Fundamental Analysis Strategy"* (TAR 1998). Nine signals from
Lev-Thiagarajan, combined into a score.

**Construction — SIX of the nine, and the three omissions are structural rather than chosen.**
Each as a year-over-year change scaled to its own two-year base, signed so that "good" is high,
then equally weighted into one score:

| signal | from | in `_KEEP`? |
|---|---|---|
| Δ inventory, relative to Δ sales | `inventory`, `revenue` | ✓ |
| Δ receivables, relative to Δ sales | `receivables`, `revenue` | ✓ |
| Δ gross margin | `grossmargin` | ✓ |
| Δ SG&A, relative to Δ sales | `sgna`, `revenue` | ✓ |
| Δ capex, relative to the industry | **`capex`**, one line in `_KEEP` — or derived, see below | ✓ |
| Δ effective tax rate | `taxexp`, `ebt` | ✓ |

### 1a. A DEFECT IN MY OWN DRAFT, CAUGHT BY MEASURING THE IDENTITY INSTEAD OF ASSERTING IT

This section first read: *"capex is not in the allowlist and does not need to be: Sharadar defines
`fcf = ncfo − capex`, so `capex = ncfo − fcf` exactly."* **Both halves were wrong, and the second
was wrong by a SIGN.**

**Measured on the real export, 381,226 ARQ rows carrying all three fields:**

```
ncfo − fcf  ==  −capex     exact on 0.999879 of rows, max |dev| 1
ncfo − fcf  ==   capex     exact on 0.064489 of rows
capex < 0                  0.8874 of rows
```

**Sharadar stores `capex` as a NEGATIVE cash outflow**, so the identity is `fcf = ncfo + capex`
and therefore **`capex = fcf − ncfo`** — or, as a positive magnitude, `capex_outflow = ncfo − fcf`.
**Writing it the way I first did would have flipped the sign of the capex leg in C1 and of capex
intensity in C2**, and a sign-flipped signal does not raise: it produces a clean, plausible,
exactly-backwards number. That is `P7`'s currency bug, `V6-B`'s unsigned `transactionvalue` and
the `monotonicity` convention in a fourth costume.

**AND `capex` IS IN THE RAW EXPORT — it is column 15 of `fundamentals.csv`.** It is the
**loader allowlist** that drops it, not the data. So the arm has two routes and must **declare
which**: add `capex` to `WRDSProvider._KEEP["fundamentals"]` (one line, but a loader change), or
derive it from `fcf − ncfo`. **Either way the sign convention is declared in the register and
pinned by a test**, because the whole hazard here is that the wrong sign is silent.

**OMITTED, AND WHY — Δ labour force, audit qualification, and inventory accounting method.**
Employee counts, audit opinions and LIFO/FIFO elections are **not in Sharadar at any dimension**.
**So this is a six-signal AB score and not AB's nine**, labelled that way on every figure — a
declared deviation, not a silent one.

**Post-publication decay.** AB's result is in-sample 1974–1993. The general anchor is
McLean & Pontiff (2016), ~**58%** average post-publication attenuation across 97 anomalies —
which is also why `DECISIONS.md` requires an adopted return be quoted at **half** its backtested
size. I have **no arm-specific replication figure** for AB and say so rather than invent one.

**Overlap with shipped themes.** `gross_margin` and `op_margin` are **levels** already in
`quality`; AB uses their **changes**. `accruals_q` is already shipped and the inventory/receivables
legs are accrual-adjacent — **that is the overlap to watch**, and it is the kill.

**FREE PRE-OUTCOME KILL (`K1`).** Two legs, both censuses:
1. **Coverage on the tier** — the share of tier rows with all six signals computable (two
   consecutive fiscal years of each input) must be **≥ 0.70**.
2. **Costume against `quality` specifically at 0.60**, because four of the six legs are quality
   inputs' changes. **And a second, tighter leg: |ρ| against `z_accruals_q` must be < 0.60**, or
   the arm is Sloan accruals in six pieces.

---

## 2. C2 — MOHANRAM G-SCORE *(2005)*

**Paper.** Mohanram, *"Separating Winners from Losers among Low Book-to-Market Stocks using
Financial Statement Analysis"* (RAST 2005) — the growth-stock counterpart to Piotroski's F-score.

**AND PIOTROSKI IS ALREADY SHIPPED, WHICH IS THE WHOLE REASON THIS NEEDS A COSTUME KILL.**
`f_score` is a registered `quality` input (`NUMBER_THEME`), so G-score is **not** a duplicate but
**is** the same family, and its overlap must be measured before it is scored rather than argued
about after.

**Construction — SEVEN of eight signals**, each a binary scored against the date's cross-section:
ROA (`netinc`/`assets`), CFO/assets (`ncfo`/`assets`), **CFO > ROA**, ROA **variability** (low is
good), sales-growth **variability** (low is good), R&D intensity (`rnd`/`assets`), capex intensity
(**`|capex|`**/`assets`, with §1a's sign convention — Sharadar's `capex` is **negative**, so the
intensity is its absolute value and getting that wrong inverts the signal silently).

**OMITTED: ADVERTISING INTENSITY — Sharadar carries no advertising expense at any dimension.** So
this is a seven-signal G-score, labelled as such.

**Post-publication decay.** G-score has held up somewhat better than F-score in later work on
growth stocks, but I do **not** have a specific replication magnitude to quote and will not
manufacture one. McLean-Pontiff's ~58% is the anchor.

**Overlap.** ROA and CFO/assets against `roe`, `roic`, `cash_op_prof`, `fcf_margin`; R&D intensity
against **nothing shipped** (R&D is read only inside `op_margin`'s operating-profit construction);
the two variability legs against **nothing shipped at all** — earnings-variability is not a
registered signal, which is also candidate C5.

**FREE PRE-OUTCOME KILL (`K1`).** |ρ| against **`z_f_score`** must be **< 0.60**. This is the
sharpest kill in the batch and it is likely to fire: both scores are cross-sectional binaries over
overlapping profitability and cash-flow inputs. If it fires, **G-score is F-score for growth names
and carries no verdict** — and that is a useful finding at zero trials.

---

## 3. C3 — R&D-TO-MARKET *(Chan-Lakonishok-Sougiannis 2001)*

**Paper.** Chan, Lakonishok & Sougiannis, *"The Stock Market Valuation of Research and Development
Expenditures"* (JF 2001): R&D scaled by market value predicts returns; R&D scaled by sales does
not.

**WHY THIS IS THE MOST INTERESTING ARM IN THE BATCH, AND IT IS A DESIGN POINT RATHER THAN A HUNCH.**
Batch 1's **A1** tested the same economics — that markets misprice intangible capital — and its
kill fired at **0.6087** coverage against 0.70, because Peters-Taylor perpetual inventory needs a
**10-fiscal-year burn-in**. **R&D-to-market needs ONE year of `rnd` and a market cap**, so **it
cannot fail A1's kill**. It is the same hypothesis routed around the thing that killed it, which is
a legitimate new construction and not a re-run.

**And it is NOT re-opening A1.** A1 is closed at its anchored burn-in; batch 2 recorded that
re-running it at 3 or 5 years would be choosing the parameter on the outcome. **C3 changes the
CONSTRUCTION, not the parameter.**

**Construction.** `rnd / marketcap`, point-in-time, winsorised at the shipped 2% (`zscore`'s own
clip). **R&D is legitimately ZERO for most firms, not missing** — so the arm's population is
declared as *all tier rows*, with a true zero scored as zero and an **absent** `rnd` excluded, and
the three counts reported separately. A1 established that three-way reporting and it binds here.

**Post-publication decay.** Published 2001; the intangibles literature has moved to organisation
capital (Eisfeldt-Papanikolaou) rather than refuted this. McLean-Pontiff is the anchor.

**Overlap.** `rnd` enters nothing shipped as a signal — it is consumed only inside operating
profit (`op = rev − cor − sgna − rnd`, with an `or 0.0` default). So the nearest shipped relative
is `op_margin`, and the kill reads against it.

**FREE PRE-OUTCOME KILL (`K1`).** The **non-zero share on the tier** must be **≥ 0.30**. This is
*not* the 0.70 non-null rule and the difference is deliberate: a firm with no R&D is a valid
observation at zero, so the 0.70 rule would be the wrong object. What would make the arm
meaningless is too few names with any R&D to sort on — hence a **dispersion** floor rather than a
coverage floor, declared here with its reason.

---

## 4. C4 — COMPOSITE EQUITY ISSUANCE *(Daniel-Titman 2006)*

**Paper.** Daniel & Titman, *"Market Reactions to Tangible and Intangible Information"* (JF 2006):
the part of market-value growth **not** explained by return predicts negatively.

**Construction.** `iss = log(mktcap_t / mktcap_{t−5y}) − log(1 + cumulative total return over the
same window)`, signed negative so low issuance is good. It captures issuance through **market
value**, which picks up secondary offerings, option exercise and stock-financed acquisitions that
a share count can miss or mistime.

**OVERLAP WITH THE SHIPPED SIGNAL IS THE WHOLE RISK, AND `S16` IS WHY IT MUST BE MEASURED RATHER
THAN ARGUED.** `capital_discipline` is `neg_issuance`, derived in `_yoy()` from `sharesbas`
year-over-year. `S16` measured that splitting net issuance into buyback and dilution legs is a
**RANK IDENTITY — within-date rank correlation `1.000000000000` on all 69 dates** — because
`max(0, −net)` and `−max(0, net)` are both non-increasing in `net`. **Composite issuance is a
different construction (market value, five years, return-adjusted) and is almost certainly not
that identity — but "almost certainly" is not a measurement.**

**Post-publication decay.** The issuance family is among the better-replicated anomalies, and
Pontiff & Woodgate document attenuation in the share-issuance effect after 2004. **So the prior
here is of a real effect that has weakened**, which is the honest framing.

**FREE PRE-OUTCOME KILL (`K1`).** Within-date rank correlation against **`z_neg_issuance`** must
be **< 0.95** — looser than the 0.60 costume bar on purpose, because these two are *meant* to
measure the same economics and the question is whether they are the **same column**. Above 0.95 the
arm is the shipped signal re-scaled and carries no verdict. **Plus a five-year history floor**: the
share of tier rows with a market cap five years prior must be **≥ 0.70**, measured on the tier.

---

## 5. C5 — EARNINGS STABILITY / PERSISTENCE

**The literature.** Earnings persistence is the AR(1) coefficient of earnings; low **variability**
of earnings is the "safety" leg of Asness-Frazzini-Pedersen's quality-minus-junk. Both are standard
and neither is registered here.

**AND A NEAR-MISS I CHECKED RATHER THAN ASSUMED: "persistence" appears FIFTEEN times in the
research log and NOT ONCE as earnings persistence.** Every occurrence is `S22`'s score/return
persistence across horizons or `MB21`'s persistence-preserving null. **The candidate is genuinely
untested**, and that is checkable rather than asserted.

**Construction — two legs, scored as one arm.** Over a rolling 20-quarter window of `netinc`
scaled by `assets`: (a) **persistence** = the AR(1) coefficient on the name's own ROA series;
(b) **stability** = the negative of its standard deviation. Equally weighted after standardising.
**20 quarters is a five-year burn-in and it is the parameter most likely to decide this arm**, so
it is **fixed here, before any outcome**, and the register must report coverage at 12 / 20 / 28
quarters so a successor can see what the choice cost — which is exactly the reporting A1's
under-specified burn-in made necessary.

**Post-publication decay, and it is the most specific in the batch.** The accruals family this
belongs to has decayed sharply: Green, Hand & Soliman (2011) document the accruals anomaly's
post-2004 disappearance, which they attribute to hedge-fund capital. **`accruals_q` is already a
shipped `quality` input**, so the arm is adjacent to a signal whose literature has already decayed
— an **unfavourable** prior, stated up front.

**FREE PRE-OUTCOME KILL (`K1`).** Coverage on the tier at the 20-quarter window must be **≥ 0.70**,
and |ρ| against `z_accruals_q` and against `z_roe` must each be **< 0.60**.

---

## 6. C6 — CASH CONVERSION CYCLE

**Construction.** `CCC = DSO + DIO − DPO` with `DSO = 365 · receivables / revenue`,
`DIO = 365 · inventory / cor`, `DPO = 365 · payables / cor`, signed negative so a short cycle is
good. **All three inputs are in `_KEEP`** (`receivables`, `inventory`, `payables`) — no rebuild.

**THE WEAKEST LITERATURE SUPPORT IN THE BATCH, AND I AM SAYING SO RATHER THAN DRESSING IT UP.**
CCC is primarily an operations and working-capital metric; its use as a **return**-predictive
cross-sectional signal rests on thin and mixed academic evidence compared with every other arm
here. **It is included because it is cheap, buildable with no rebuild, and genuinely untested —
not because the literature is strong.** It is ranked **eighth of nine** below for that reason.

**Overlap.** `assetturnover` (derived by the panel, since Sharadar leaves it blank in ARQ) and
`accruals_q` are the nearest shipped relatives; working-capital efficiency is a component of both.

**FREE PRE-OUTCOME KILL (`K1`).** Coverage on the tier **≥ 0.70** — and the binding risk is
**sector structure rather than missingness**: `cor` and `inventory` are near-zero or meaningless
for financials and many software names, so the kill also requires that **no single panel sector
contribute more than 40% of the scoreable rows**, or the arm is a sector bet. `S7`'s `C6` and
`S10`'s 3× sector spread are the precedents.

---

## 7. C7 — OPERATING LEVERAGE *(Novy-Marx 2011)*

**Paper.** Novy-Marx, *"Operating Leverage"* (RoF 2011): firms with high fixed operating costs
relative to assets earn higher average returns, as a risk story.

**Construction.** `OL = (cor + sgna) / assets`, point-in-time. **A STANDALONE COLUMN, NOT AN
INTERACTION**, and that is deliberate: operating leverage is often framed as sales × fixed-cost
sensitivity, but **`S7` registered four interactions and rejected all four**, and batch 1's A3 took
the same decision for the same reason. If the standalone column carries nothing, the interaction is
a separate register and not a rescue of this one.

**Post-publication decay.** The profitability family Novy-Marx belongs to has partly persisted
(gross profitability), but **operating leverage specifically has a thinner replication record than
gross profitability**, and `gp_on_capital` — his other and better-known signal — **is already
shipped.** That is the honest comparison.

**Overlap.** `op_margin` and `gp_on_capital` share the inputs directly: `gp = revenue − cor` and
`op_margin` nets `sgna`. **So the costume risk is high and concrete**, not speculative.

**FREE PRE-OUTCOME KILL (`K1`).** |ρ| against **`z_gp_on_capital`** and **`z_op_margin`** must
each be **< 0.60**. Given shared inputs this is the second-likeliest kill in the batch to fire.

---

## 8. C8 — EXPECTED INVESTMENT GROWTH *(Hou-Mo-Xue-Zhang q5; Li-Wang-Yu)*

**Paper.** The `EG` factor of the q5 model (Hou, Mo, Xue & Zhang, 2021), motivated by investment
*q*-theory: expected **future** investment growth, not realised past growth.

**Construction.** A cross-sectional predictive fit of next-year investment growth on three
point-in-time predictors — Tobin's *q* (`(marketcap + debt) / assets`), cash flow (`ncfo / assets`)
and change in ROE — with the **fitted value** as the signal. **The fit is estimated INSIDE the
build quadrant only** and the coefficients are refreshed per date from history strictly before it;
no coefficient is estimated on data the arm is then scored on.

**AND THAT IS THE ARM'S LARGEST DESIGN RISK, NAMED HERE RATHER THAN DISCOVERED.** Unlike every
other arm in this batch it requires **fitting something**, and fitting on the panel then scoring on
the panel is the collapse this record has already paid for: **+8.43%/yr in-search → −0.04%/yr on
the locked hold-out**, and the ML tree combiner whose deciles ran **backwards** out of sample. The
expanding-window fit is the mitigation; **if a register cannot implement it strictly, the arm
should be dropped rather than fitted loosely.**

**Post-publication decay.** Published **2021**, so there is almost no post-publication history —
which cuts **both ways** and must be said both ways: little opportunity to decay, and little
out-of-sample validation by anyone else.

**Overlap.** **`neg_asset_growth` is already shipped** (Cooper-Gulen-Schill realised asset growth),
and `EG` is the *expected* analogue. That is the kill.

**FREE PRE-OUTCOME KILL (`K1`).** |ρ| against **`z_neg_asset_growth`** must be **< 0.60**, and
coverage on the tier **≥ 0.70** for all three predictors plus the one-year-ahead investment
outcome used to fit.

---

## 9. C9 — OHLSON O-SCORE *(1980)* — **INCLUDED LAST, AND I WOULD NOT RUN IT**

**Paper.** Ohlson, *"Financial Ratios and the Probabilistic Prediction of Bankruptcy"* (JAR 1980).
Nine inputs, logit coefficients published.

**ITS SCOPING KILL FIRES NOW, AT ZERO COST.** Four of the nine inputs need columns **absent from
`WRDSProvider._KEEP`** — `liabilities` (TLTA, OENEG, FUTL), `assetsc` and `workingcapital` (WCTA,
CLCA), `retearn` — and those are **four of the exact eight columns `S17`/`S19` identified as
absent**, the reason `S10`'s accounting half was excluded. **So O-score needs a panel rebuild**, and
should be batched with batch 2's **B5** rather than paying that cost alone.

**AND SUBSTITUTING `debt` FOR `liabilities` IS REFUSED RATHER THAN QUIETLY DONE.** `debt` and
`debtnc` are present, but total liabilities include payables, accruals and deferred tax, so `debt`
**understates** leverage — a different construction wearing O-score's name, and the error runs
toward making firms look safer.

**THREE REASONS IT IS RANKED LAST, AND THE THIRD IS DECISIVE.**
1. **It needs a rebuild** (above).
2. **Two of its siblings are already tested**: Altman Z and Beneish M are both inputs to
   `S10-ACCT`'s 2-of-3 veto and `MA28-CARD`'s crash flag — **8 and 9 mentions in the research log
   respectively** — and `S10-ACCT` was **REJECTED** on its drawdown leg.
3. **Campbell, Hilscher & Szilagyi (2008) — whose model is batch 2's B6 — showed their own hazard
   specification DOMINATES both O-score and Z-score.** So the published literature already says
   B6 is the better distress measure. **Running C9 is testing the weaker of two definitions, on a
   rebuild, in a tier where distress is rare.** Batch 2 already warns that the tier may be too
   clean for a junk filter to bite at all.

**Kept in the batch for honesty about what was surveyed, with the recommendation NOT to run it.**

---

## 10. NEAR-MISSES EXCLUDED, EACH WITH THE ROW THAT CLOSED IT

Requirement (c) checked against `NUMBER_THEME` (48 registered signals), `RESEARCH_LOG.md`,
`VALQUO_LEDGER.md` and `CLAUDE.md`.

| candidate | closed by |
|---|---|
| **Piotroski F-score** | **SHIPPED** — `f_score` is a registered `quality` input |
| **Gross profitability** (Novy-Marx 2013) | **SHIPPED** — `gp_on_capital` |
| **Cash-based operating profitability** (Ball-Gerakos-Linnainmaa-Nikolaev) | **SHIPPED** — `cash_op_prof`, added on the `S2` pattern |
| **Sloan accruals** | **SHIPPED** — `accruals_q` |
| **Asset growth** (Cooper-Gulen-Schill) | **SHIPPED** — `neg_asset_growth` |
| **Share issuance** | **SHIPPED** — `neg_issuance`; and `S16` found the buyback/dilution split a **rank identity at 1.000000000000** |
| **PEAD** | **SHIPPED** — `pead_car`, `pead_drift`; and batch 1's **A8** (IBES SUE) died on its kill at **2.6945** announcements/ticker-year |
| **Analyst revisions** | **`D6` REJECTED** — incremental IC *t* +0.7199 / +0.7957, **0.203× and 0.224×** its own MDE; and `earn_rev` is shipped |
| **Analyst neglect / low coverage** | **batch 2's B4, STILL BLOCKED** — `CORRECTED-FLOORS` part 3 built and validated the dated IBES link and its best route's cell coverage is **0.69999551 against the 0.70 floor**, failing by about **1.3 cells in 289,659**. Pinned as a failure that may never be written up as a pass; `W-28` forbids relaxing it. **See §11.** |
| **Short-term reversal, idiosyncratic vol, MAX** | **`R5` NULL on all three** on the corrected universe, and all three are registered (`neg_ret_1m`, `neg_idio_vol`, `neg_max_ret`) |
| **Beta / BAB** | `neg_beta` shipped; `R5` read it at **−0.3937**, and `low_risk` carries **zero weight** |
| **Short interest / crowding** | **`S18`** — covered on only **32 of 69 dates (46.4%)**, every covered date late, so a full-panel both-halves gate is impossible |
| **Intangible-adjusted book value** | **batch 1's A1**, kill fired at **0.6087**; re-running at a shorter burn-in is choosing the parameter on the outcome. **C3 routes around it by construction** |
| **Theme dispersion / disagreement** | **`E-3` NULL** on both co-primary bases |
| **Δ of the composite (fundamental momentum)** | **`E-2` NULL**, all six cells. **C1's Δ-signals are deltas of INDIVIDUAL inputs, not of the composite** — a different object, stated so it is not read as a re-run |
| **A name's own valuation history** | **`E-6` NULL** on both bases |
| **Implied-growth expectations gap** | **`MB18` REJECTED**, largest \|*t*\| 1.5617 against 2.71 |
| **Sector-relative / sector-neutral value** | **`S15` REJECTED** and **`SECTOR-NEUTRAL-B6` closed**; `S25`'s dated map is the only route back and batch 1's **A10** died on it at **0.3713** coverage |
| **Seasonality** (Heston-Sadka) | **`MA58` UNINTERPRETABLE** — and it is the item that first found the residualisation defect §0 repairs |
| **Peer / lead-lag momentum** | `IDEAS_LEDGER` **`S-SEED-6b` PARKED** — runs on customer-list and shared-analyst link data this project does not own |
| **Quality-minus-junk as a composite** | duplicative by construction — its profitability and safety legs are `quality`, and its junk leg is batch 2's **B1** |
| **Net operating assets** (Hirshleifer et al.) | needs `liabilities` — **absent from `_KEEP`**, same rebuild as C9 |
| **Volatility-managed exposure** | **batch 2's B2**, already drafted |
| **Junk filters** | **batch 2's B1** (the `TIERED-POOL` forward pointer) and **B6** (CHS). C9 is the third definition and is ranked last |

---

## 11. AN UPDATE TO BATCH 2, BECAUSE ITS CONDITION HAS NOW BEEN MEASURED

Batch 2's **B4** was drafted *conditional* on r1's dated IBES link existing. **It now exists and is
validated** — and the condition **fails**: `CORRECTED-FLOORS` part 3 measured route B (CRSP
`ncusip` → IBES `cusip`) at cell coverage **0.69999551** and name coverage **0.69041**, both below
the inherited **0.70** rule, and reports it **below the floor** with a test that fails if it is ever
written up as a pass.

**So B4 is NOT RUN, and `k` stays 6 in batch 2.** It is not re-drafted here and this is not a
second attempt at it.

**THE ONE LEGITIMATE ROUTE LEFT IS NOT A RELAXATION, AND IT IS WORTH NAMING PRECISELY.** That
0.69999551 is measured on the **full 289,659-cell universe**. Charter **Stage 1b** — fixed earlier
today, *before* this measurement existed — makes the **tier** the governing population, and
`O-1`/`W-1`'s rule is that **coverage is measured on the population the arm is scored on.** Analyst
coverage is mechanically far better among $10bn companies, so **the tier's coverage is a different
number and is UNMEASURED.** A successor may run that census as a free pre-outcome kill. **What it
may not do is read the full-universe 0.69999551 as a pass**, and the test pinning that stays.

Also recorded: part 3's identifier finding, because it would silently poison any IBES join —
**`oftic == 'ABT'` is claimed by SIX different IBES tickers**, so an exchange ticker is not a unique
key in IBES even at a single date, and the **cusip route is primary with the ticker route as
cross-check**.

---

## 12. RANKED, AND WHAT I WOULD RUN FIRST

| # | arm | why here |
|---|---|---|
| **1** | **C3 R&D-to-market** | the only arm that revives a *killed* hypothesis by changing its construction rather than its parameters, and its coverage profile cannot fail A1's kill |
| **2** | **C4 composite equity issuance** | best-replicated literature in the batch, and genuinely distinct from the shipped share-count issuance |
| **3** | **C1 Abarbanell-Bushee (six signals)** | six cheap signals, no rebuild, and the Δ-of-an-input object is untested |
| **4** | **C2 Mohanram G-score** | a strong published result whose costume kill against the shipped `f_score` is informative **whichever way it goes** |
| **5** | **C8 expected investment growth** | strongest theory, newest paper — and the only arm needing a fit, which is its risk |
| **6** | **C5 earnings stability / persistence** | genuinely untested (the 15 log hits are all `S22`/`MB21`), with an unfavourable decay prior |
| **7** | **C7 operating leverage** | high costume risk against two shipped signals with shared inputs |
| **8** | **C6 cash conversion cycle** | cheap and untested, weakest literature in the batch, and said so |
| — | **C9 Ohlson O-score** | **surveyed, not recommended**: needs a rebuild, two siblings already tested, and CHS dominates it in the literature |

---

## 13. WHAT THIS DRAFT DOES NOT DO

* **No register committed, no arm run, no trial booked, nothing measured.** `k` = 9 is a plan.
* **No Stage-2 look** — the check quadrant stays closed; using it to choose among these nine would
  spend it with no replacement.
* **No Stage-3 look**, and the 1999-2008 proxy inherits charter §5's constraint: it may test an
  increment on a five-theme base and may **not** validate the shipped seven-theme construction.
* **The 1972-1998 WRDS era stays closed** — `OOS1`'s Gate B reads **0.837303** against **0.90**.
* **No floor is typed as a literal**; every bar is read from `CORRECTED-FLOORS`' artifact, and the
  theme-IC floor is **not** applied to an incremental IC.
* **Nothing is adopted.** Adoption is Don's, is a vintage event, and quotes the expected return at
  **half** the backtested size.
* **C9 is recommended against**, and **C8 should be dropped rather than fitted loosely** if a
  register cannot implement its expanding-window fit strictly.
