# DESIGN MEMOS — audit #3's final nine: MA24, MA26, MA27, MA28, MA33, MA54, MA55, MA57, MA58

**These are design records and premise measurements, not backtests.** No hypothesis is
registered, no threshold is pre-committed, no verdict is issued against a bar, and **no trial is
charged** — `DESIGN_u4_u6_u8.md`'s precedent for closing a row with a memo where a memo is the
honest deliverable, `S25`'s for closing one on a fact about what data exists, session 8's for
declining a test that cannot resolve, and `MA56`'s for recording an item that must not be run
today. Where a memo states a number it is a measured fact about the data, the code, or
arithmetic on an already-published artifact, and it is labelled as such.

Reproduce every number below with `python -m scripts.ma_final_batch_measure --insiders`
(`data/free_analysis/MA_FINAL_BATCH.json`).

**Why these nine were not simply run.** Each of MA26-A/B, MA27, MA28, MA33, MA55, MA57 and MA58
is a research arm that charges trials and needs a blind pre-registration committed **alone**,
before any measurement, as a strict git ancestor. Running six of them inside one batch is
precisely what the register exists to prevent, and it is the failure `MA31` was pulled out of a
correctness batch to avoid. What *can* be settled without a trial is whether each is buildable,
whether the audit's evidence for it holds, and what its register would have to say — and on four
of the nine that turns out to change the answer.

---

## The four things the audit gets wrong, and one it gets right that nobody had checked

| # | audit's claim | measured | direction |
|---|---|---|---|
| 1 | the monthly rebuild (`MA33`) *"unlocks the whole [text] class at once"* and re-opening `S19` is *"the strongest argument for paying for that rebuild"* | **`S19`'s own kill condition FIRES on the monthly panel.** MDE falls +0.020549 → **+0.012324** at 114 months, still above the +0.009607 effect. It needs **188 months (15.6 years)**, i.e. ~2032 | the rebuild does **not** buy back `S19` |
| 2 | `MA57`'s columns *"cannot be built without adding them and re-exporting **while the Sharadar entitlement is live**"* | **both columns are already on disk** — 24 columns, 5,636,964 rows, 69,277 distinct `ownername`, zero missing on all 124,181 open-market purchase rows | the blocker does not exist |
| 3 | `MA26`-C: the withholding state is *"**NOT TESTABLE** point-in-time, and this is the finding"* | **it is testable and here is the base rate** — 5,403 of 108,100 valued rows (**4.998%**) on **69 of 69 dates**, per-date 2.04%–18.68% | the deliverable was naming a blocker that is not there |
| 4 | row 8 of §10's table: *"the unlock is **MA24's** monthly rebuild"* | the monthly rebuild is **`MA33`**, by the audit's own id map eleven lines above; `MA24` is *"Wrong rejections"* | a reader following the pointer lands on a different item |
| 5 | `MA27`'s premise: *"the **53 signals** already in `per_signal`"* | **confirmed exactly** — `per_signal.signals` has 53 entries and `settings.NUMBER_THEME` has 53 | holds |

**Item 1 is the consequential one and it is arithmetic, not judgement.** `MA24` pre-committed the
condition in writing: *"if the monthly panel's own MDE still exceeds +0.0096 on the 418+195 name
corpus, the question is unanswerable on data we own and should be closed permanently rather than
re-opened a third time."* That condition is now testable without building anything, because
`S19`'s minimum detectable effect is recoverable from its own shipped artifact.

**The MDE is DERIVED, not quoted.** `CLAUDE.md` states +0.020549 and `S19_MDNA.json` stores no
such key — but it stores `residual_ic_change` and `residual_ic_t_change`, and
`MDE(|t|=2) = 2·SE = 2·IC/t`. A1: `2 × 0.012202150018043164 / 1.1876022080477582` =
**0.02054922083397216**, reproducing the record to fifteen digits. A2 gives **0.0310262257234513**
against the record's +0.031026. So the argument rests on the artifact and not on prose.

**The rescaling runs in the conservative direction, and saying so is the point.** `SE` falls as
`1/√T` only if the dates are independent. Monthly 63-day forward returns **overlap**, and `R9`
measured lag-1 autocorrelation **+0.189** on this project's own quarterly spread — so the true
monthly `SE` is *larger* than this and the true MDE *worse*. A conclusion of "still underpowered"
therefore holds a fortiori. The cross-section per date is unchanged by the rebuild, so it cannot
rescue the power either.

**A trap in the artifact that would mislead anyone checking this.** `S19_MDNA.json` ships
`underpowered: false`. That flag is the register's own **coverage** gate — `min_covered_dates`
24, `min_heldout_names` 100, `min_names_per_date` 30, all of which passed — and it is a different
quantity from the MDE. Read as a power verdict it flatly contradicts the write-up's *"the design
could not have returned a positive verdict even if the effect were exactly true."* **Both are
right; they are two different power concepts and only the weaker one was stored.**

---

## MA24 · Wrong rejections — the recommendation is ADOPTED, and its open clause is now closed

**Status: `DONE`. Zero trials.**

The audit's own answer is *do not re-open* `S21` (missed by 17 bps) or `S12-A2` (18 bps), because
`SELRULE` already settled the meta-question **NOT ANSWERABLE** before any run, and re-running a
17-bps miss on the same panel is the p-hacking the commission forbids. **Verified rather than
accepted:**

* `S12-A2`'s late half reads **+0.008235149382270185** against a +0.01 bar in `S11_S12.json` —
  a miss of **17.6 bps**, and its `gate.verdict` is `NOT_REPLICATED` with `alpha_decides: true`.
  The audit's "18 bps" is that number rounded.
* The three *"the design could not have caught it"* verdicts are all already labelled by the
  project: `S19`'s MDE (derived above), `V6-B` M2 (**42** distress events against a
  pre-committed floor of **60**, VOID), `O10`/`O18` (voided by the registered C2 gate).

**What is new here: `MA24`'s one open clause is now resolved, and it resolves against re-opening.**
Its `S19` bullet did not close the row — it named a **NEW DESIGN** (the monthly panel) as *"the
only thing that re-opens it"* and attached a kill condition. That condition fires. **`S19` is
closed permanently on `MA24`'s own pre-committed terms**, and no monthly rebuild changes it before
roughly 2032.

**The recommendation is adopted, with one honest qualification the audit does not state.** A near
miss and a *design that could not have detected the effect* are different objects, and only the
second is settled by power arithmetic. `S21` and `S12-A2` are the first kind: they were adequately
powered and simply did not clear. Nothing here says they are false — it says re-measuring them on
the same panel buys no evidence.

---

## MA26 · Untested combinations — C is refuted, D is recorded, A folds into MA28, B is design-recorded

**Status: `DONE` on C and D; A and B `DESIGN-RECORDED`. Zero trials.**

### C — the withholding state · **THE AUDIT'S FINDING IS REFUTED, AND THIS WAS THE ROW'S DELIVERABLE**

The ledger note reads *"Arm C's deliverable is naming the blocker."* There is no blocker to name.

`withhold_implausible_fair_values` triggers on exactly one thing: `fair_value / price >
FV_BAND_HIGH` (5.0), imported from `engine.pipeline` so the two surfaces cannot drift. It reads
**no live sub-score, no WACC and no quote** — so `V6`'s finding (the live sub-scores are not
computable historically) and `S23`'s (that path fetched **live Yahoo prices to value 1999**) are
both true and **neither one binds this arm**. `S23` then fixed the network problem itself: the
valuation panel now has an explicit offline mode and the build *asserts zero network calls*.

Measured on `S23`'s banked panel, 2009-01-15 → 2026-01-28:

| | |
|---|---|
| rows carrying both `fair_value` and `price` | **108,100 of 108,241 (99.87%)** |
| would have been withheld | **5,403 = 4.998%** |
| dates with at least one withholding | **69 of 69** |
| per-date withheld share | min 2.04%, median 4.17%, max 18.68% |

So *"the model cannot value this name"* is a measured, dated, per-name **historical** state, and
the arm is testable. **Two limits travel with that, and they are why this memo stops here rather
than scoring it:** the panel's `fair_value` is `S23`'s reconstruction, not the value the live site
published on the day (nothing recorded that historically — which is `LA1`'s class and `MA29`'s
surface); and turning a 5% base rate into a predictor is a hypothesis needing its own register
with a both-halves gate, not an extension of this one.

### D — `pead_car` as a conditioner · **DO NOT RE-OPEN**

Recorded exactly as the audit asks, and for its stated reason: the rejection rests on two controls
stronger than the IC, and a control using no earnings data beat it. Listed so it is not
re-proposed. **No work.**

### A — accounting flags as name-level catastrophe information

**This is the same object as `MA28` and as `MA54`-1.** The audit files one effect under three ids
in two passes: `MA26`-A frames it as a disclosure, `MA28` as a product card, `MA54`-1 as a
re-examination on the `V6-B` M1 instrument. **They want ONE register, not three**, and building
three would triple-charge one hypothesis. Folded into `MA28` below.

### B — minimum hold as construction, separated from the band

The mechanism is real and measured: `S22` found alpha still accruing at two years against a KM
median top-decile tenure of **one rebalance**, and `S14` found **half** its gain is a signal
effect rather than the cost saving its register claimed. The design the audit specifies is right —
an explicit minimum hold **instead of** a rank band, so the two mechanisms are separated rather
than compounded — and its C-control (rank correlation > 0.97 against the width-0.30 book means it
is `S14` renamed) is the correct kill condition.

**Not run. `DESIGN-RECORDED`, 2 trials when it is.** One caution the audit does not state: `S14`
at width 0.30 is **live in the `taxable` configuration and is an adoption decision already sitting
with Don**. Registering a competing hold mechanism while its sibling is mid-decision invites
adopting both and attributing the sum to either. **This should queue behind `S14`'s decision** —
`S20`/`S21`'s queueing clause, which cost nothing to write and turned out to bind.

---

## MA27 · KNS ridge on the 53-signal cross-section

**Status: `DESIGN-RECORDED`. Zero trials. 1–2 when run.**

**Premise verified:** `per_signal.signals` carries exactly **53** entries in the shipped
`BACKTEST_RESULTS.json`, and `settings.NUMBER_THEME` carries **53**. The audit's three
distinguishing arguments hold on inspection: `S5` shrank 7 theme mean-ICs with no `Σ` in it;
`MLCOMB` searched a non-linear interaction space over 7 theme z-scores; the eight
`_weight_schemes` — including the two that *do* use `Σ` — operate at the **theme** layer, after
the theme mean has collapsed the within-theme covariance, which is exactly what `S16` proved by
showing a split at that layer is a **rank identity**.

**The register it needs, unchanged from the audit's and repeated here so it is in one place:**
`b = (Σ + γ·I)⁻¹ μ` over the 53 within-date standardised signals; **`γ` selected on a strictly
prior window and never on the scoring window — a `γ` chosen anywhere on the scoring window voids
the arm outright**; score names as `Z·b`; rejected if `top_decile_alpha` fails the calibrated
margin (**1.8629pp** at today's `N`, not the 1.95pp the audit quotes — that figure has been
superseded since `MA19`) in **either** half, or if within-date rank correlation against the
deployed composite exceeds **0.97**.

**Two things this memo adds.** First, the audit's prior — *REJECTED at ~75/25* — is the right
prior and should travel with the register, because everything in the weighting family has failed
here by margins up to **79×**. Second, and cutting the other way: `MA27` is the one member of that
family whose mechanism has never been tested at all, and `S16` measured that the theme layer is
where the information is destroyed. **Both belong in the register; neither is a reason to skip the
blind commitment.**

---

## MA28 · Accounting red flags as a name-level risk card — the ONE register for MA26-A, MA28 and MA54-1

**Status: `DESIGN-RECORDED`. Zero trials. 1–2 when run.**

The effect is measured and it is the strongest name-level risk signal in the record after `V6-B`
M1: names tripping 2 of 3 published accounting-stress flags fell >50% in a quarter at **2.660%**
against **0.874%** — **3.04×**, on 113,945 rows, from `S10-ACCT`.

**Why it is a disclosure and never a screen, and this is the whole design.** `S10-ACCT` was
**REJECTED**, and its valuation sibling `S10` found the **opposite** sign — a valuation-band screen
deleted names that crashed at *half* the rate of those it kept. So the copy may state a **base rate
in a specific named bad outcome** with its sample and window attached, and may never say *"avoid
these names"*, which is a return claim this project has measured to be unsupported.

**The one register, replacing three:**

* **Gate = the CRASH-RATE replication in both halves, NOT alpha.** `S10-ACCT` failed on portfolio
  drawdown, and `S10` had already measured that this book's max drawdown is decided by **one**
  market-wide quarter (COVID 2020Q1, trough index 44 of 69) that no name-level flag can move.
  Re-registering it on the portfolio leg would fail for the same reason a third time.
* **Instrument = `V6-B` M1's**, per `MA54`-1: per-date name-level `P(further fall)`, within-date
  permutation p5, a pre-committed economic floor. That is the instrument that produced the
  record's one clean risk positive, and the 3.04× is the pilot.
* **Controls, both mandatory.** A **market-cap control** — `U7` and `S10` both turned out to be
  size sorts wearing another name, and `V6-B` needed a within-size stratification to survive. And
  a **`BANNED` phrase tuple asserted against the RENDERED payload**, not the source, because
  rendering is where copy leaks — the app lane's `dip_posture.py` design, which the record already
  says should be carried forward.
* **`V6B-PRODUCT` is the proven template** (2026-08-13): a risk claim with numbers beside a return
  claim held at NULL.

**One caution measured for this memo:** the flags are computed from SF1 and joined, so no panel
rebuild is needed — `S10-ACCT` established that. But `S10-ACCT` ran **2-of-THREE**, not the
audit's 2-of-four, because NT late-filing notices are unbuildable from anything we own. **A null
on 2-of-3 does not close the 4-flag rule**, and the register must say so before it runs rather
than after.

---

## MA33 · The monthly theme panel

**Status: `DONE — SCOPED, AND ITS HEADLINE JUSTIFICATION IS REFUTED`. Zero trials.**

**The stated reason to build it does not survive.** See the table at the top: `S19`'s kill
condition fires at 114 months, and the corpus would need 188. **`S19` is not what a monthly panel
buys**, and the audit's *"strongest argument for paying for that rebuild"* is therefore not an
argument for it.

**What is still true about the rebuild, stated so this is a scoping memo and not a rejection:**

* **It is feasible on owned data.** `bulk.prepare_daily` already down-samples DAILY to **one row
  per ticker-month** — monthly is the *native* granularity of the point-in-time market-cap path,
  not a stretch of it. Fundamentals are as-of-any-date by construction. The binding cost is
  compute: the 69-date build runs ~20 minutes, and ~205 monthly dates over the same window is
  roughly 3× that per build, on every build thereafter.
* **Every calibrated bar would become an EXTRAPOLATION.** X7's floors are calibrated for *this*
  panel, universe and 69 dates. A monthly panel is a different object, and quoting 2.2837, 2.7072,
  1.8629pp or 19.667% against it is the error `U2` avoided by declining and the one this record
  warns about most. **A monthly panel needs its own placebo sweep before it can carry a verdict**,
  and that cost is not in the audit's estimate.
* **`S8`/`S9` already found a defect that a monthly panel would inherit and worsen or fix,
  depending on which way it is built:** `prepare_daily`'s month down-sample means the
  point-in-time market cap can be **up to 31 days stale** while the price feeding `_price_factors`
  is same-day. On a quarterly panel that is a precision defect; on a monthly one the staleness is
  a third of the rebalance interval.

**Recommendation: not a reason to refuse the rebuild, and not a reason to pay for it today.** It
should be justified by whatever the *next* text-or-frequency item actually needs, measured in
advance, rather than by `S19`.

---

## MA54 · Re-examination list — reconciled against the options frontier, not duplicated

**Status: `DONE — RECONCILED`. Zero trials in this lane.**

The row has four legs and they are in four different states. **None of them is this lane's to run,
and one is already answered.**

| leg | state on 2026-08-16 | who |
|---|---|---|
| **-2 O17-C4 "own the event"** | **ANSWERED, and not by this batch.** Re-registered as its own strategy in `PREREG_o17c4_own_the_event.md` (alone at `aeca6f0`), measured at `25ede1b`, ledger row **`O17C4` = `DONE — REJECTED`** on c3 with c1/c2/c4 passing. Options `N` 292 → 294. **The effect is real and survives the alert's death** — applying the shipped rule to the five-seed split-clean random-**entry** control books gives **+10.30% against +5.50%** on 27,350 trades, **+4.79pp**, positive in both halves, paired name-year sign **z +2.054, p 0.040** | options-bot lane |
| **-1 S10-ACCT on the M1 instrument** | **the same object as `MA26`-A and `MA28`.** One register, folded above | edge lane, `DESIGN-RECORDED` |
| **-3 O14 `sweep_share` on new dates** | **NEEDS-DATA.** The cache is alert-days-only, so a same-design re-run is impossible by construction; the design needs a **~4.7 GB** new pull on the optionable panel's rebalance dates | not taken |
| **-4 O6 delta-matched cheapness** | **ORPHANED BY ITS OWN VEHICLE.** The frontier routed this remedy into **P1's** register (*"should be adopted verbatim"*). **`P1S0` then FAILED at its power anchor on 2026-08-16 and the options-expression family is CLOSED** (ledger `P1S0`). The remedy is sound and has nowhere to live | reported, not taken |

**The disagreement the frontier reported rather than resolved is now resolved, and in the frontier's
favour.** Its §4b flagged that its hard rule names `O6`/`O7`/`O17` dead while `MA54` proposed new
designs for three of them, and declined to override a commission. The options lane then ran the
one that mattered on its own terms — deriving the replacement bar **first**, on the `TP-BAR`
precedent, rather than lowering the one that failed — and it rejected. **This lane adds nothing to
that and deliberately does not re-measure it**; duplicating a landed measurement is how two
lanes come to publish two numbers for one question.

---

## MA55 · Confidence-weighted mispricing

**Status: `DESIGN-RECORDED`. Zero trials. ~2 when run.**

**Premise verified buildable, which is the part that could have blocked it.** `S23`'s banked panel
carries three lens columns — `dcf_ps` (99.87%), `comps_fv` (100.00%), `growth_ps` (74.55%) — so
`w = (max−min lens)/fair_value` is computable on **108,100 of 108,241 rows (99.87%)** with **zero**
degenerate zero-width rows, and it has real dispersion: p05 **0.1195**, median **0.8777**, p95
**4.1069**.

**The `w_floor` in the audit's formula is load-bearing, not cosmetic, and the measurement is why.**
The width's maximum is **3,585** — four orders of magnitude above its median. Without a floor,
`ln(fv/price)/w` collapses to ~0 for the widest names and the arm becomes a *disagreement* screen
rather than a precision-weighted mispricing signal. **The floor must be pre-committed as a number
before the arm runs**, and it must not be tuned; this project has paid for an uncalibrated
constant before.

**The rest of the register, unchanged:** residualise on the seven themes per date; enter at 0.125
with present-weight renormalisation; gate on incremental IC ≥ the theme bar in **both** halves plus
the holdout gate; kill if it fails the calibrated alpha margin in either half **or** its within-date
rank correlation against the deployed composite exceeds **0.97**.

**One caution this memo adds.** `S10` measured that the *unscaled* gap is momentum-contaminated —
engine-expensive names carry z-momentum **+0.95 vs +0.67** — which is the audit's own motivation
for the width term. It is also the reason the register needs a **momentum control**, not only a
composite rank-correlation control: an arm that is 90% inverse-momentum would pass a 0.97 threshold
against the *composite* while being a theme this panel already scores.

---

## MA57 · Routine-vs-opportunistic insiders — **UNBLOCKED**, and it was never blocked

**Status: `DESIGN-RECORDED — BLOCKER REFUTED`. Zero trials. 1–2 when run.**

The audit calls this *"the highest-EV untested equity item in either pass"* and then attaches a
data-acquisition blocker to it: the columns *"cannot be built without adding them and re-exporting
**while the Sharadar entitlement is live**."* **Measured on the export already on disk:**

| | |
|---|---|
| columns in `data/backtest/insiders.csv` | **24** |
| `ownername` present | **yes** |
| `transactioncode` present | **yes** |
| rows | **5,636,964**, spanning **1980-11-25 → 2026-07-24** |
| distinct `ownername` | **69,277** |
| `ownername` missing on open-market purchase (code `P`) rows | **0 of 124,181** |

**So there is no re-export and no entitlement question.** `_KEEP["insiders"]`
(`valuation/edge/data_providers.py`) is a six-column allowlist and the loader drops everything
else — `df[[c for c in keep if c in df.columns]]` — which is why the columns read as absent. It is
a **one-line allowlist change**, and the audit's own §MA57 verified the allowlist correctly and
then drew the wrong conclusion about the file behind it.

**Buildability of the classification itself, measured.** Cohen-Malloy-Pomorski define a **routine**
trader as one who traded in the same calendar month in each of three consecutive prior years;
everyone else is **opportunistic**, and only the opportunistic trades predict. Applied to
`(ownername, ticker)` pairs on the export:

| population | pairs | routine | share |
|---|---|---|---|
| all coded rows (CMP classify on the whole trading record) | **87,318** | **42,537** | **48.72%** |
| open-market purchases and sales only (codes `P`/`S`) | 53,551 | 3,713 | 6.93% |

**The classification is computable, and the top row is the one CMP's rule corresponds to** —
they classify a trader from *any* trade, not from purchases alone. A ~49% routine share is in the
published ballpark, which is corroboration that the rule is being applied to the right object
rather than proof that it predicts anything.

**Its coverage is the register's first control, and it is not small:** `transactioncode` is
**absent on 1,544,490 of 5,636,964 rows (27.40%)**, and a blank code can be classified neither
routine nor opportunistic. The register must decide in advance whether those rows are dropped or
pooled, because choosing after seeing which is kinder is the thing the register exists to stop.

**A defect I predicted and then refuted by measuring it — reported because it ran against my own
hypothesis.** `_insider_score` computes `val = (sh × pr) if both present else transactionvalue`.
`transactionshares` is **signed** (2,216,036 negatives) while `transactionvalue` is **unsigned**
(0 negatives in 2.6M), so the fallback branch should be scoring sales as buys and inflating both
`net` and `buys`. **It fires on 2 rows of 5,636,964, neither of them a sale.** The branch is
effectively dead and the live insider score has no sign defect. The same pass independently
reproduced `V6-B`'s **2,182,601** silently-skipped rows exactly.

**Deliberately NOT taken: the `_KEEP` change itself.** Adding two columns with no consumer is dead
weight on a 580 MB load, and the COVERAGE RULE's discipline is to add source columns *when the
signal that needs them is added*. It belongs in `MA57`'s own register, in the same commit as the
classifier, where it is visible.

**A dead allowlist entry found in passing, reported not repaired.** `_KEEP["insiders"]` requests
`"date"`, and the export has **no such column** — it is `transactiondate`. So
`r.get("filingdate") or r.get("date")` in `_insider_score` and `_prep_insider` has a fallback that
**can never fire**. Harmless today because `filingdate` is present on every row and is the
point-in-time field `B26` fixed. It is the COVERAGE-RULE class — an allowlist entry that silently
matches nothing — and it is left alone rather than tidied, because removing it changes a live
scoring path's source for no measured benefit. **Pinned instead**, so it is a known fact rather
than a surprise.

---

## MA58 · Cross-sectional return seasonality

**Status: `DESIGN-RECORDED`. Zero trials. 1–2 when run.**

**Premise verified, with one refinement.** The audit says the topic has *"zero mentions in the
entire Valquo corpus."* True in substance: every occurrence of "seasonal" outside the audit
documents is **fiscal-quarter seasonality in fundamentals** — comparing a Q4 to a Q2, and why TTM
smoothing is or is not worth its cost — which is a different thing entirely. And
`settings.NUMBER_THEME`'s 53 entries contain **no** seasonality-shaped key.

**The refinement, and it is the `MA23` lesson again: a name match is not a paper census.**
`Linnainmaa` appears **twice** in `VALQUO_EDGE_AUDIT.md` — for Ball-Gerakos-Linnainmaa-Nikolaev's
cash-based operating profitability and for Ehsani-Linnainmaa's factor momentum. Neither is
Keloharju-Linnainmaa-Nyberg. A grep for the author would have read as "already covered"; a grep
for the *result* is what settles it.

**Buildable from owned data.** `data/backtest/prices/` holds **2,998** per-ticker daily close
series, the deepest starting **1997-12-31**, and the panel rebalances quarterly — so the
annual-lag same-quarter return fits the rebalance calendar natively and needs no new vendor and no
new column.

**Two constraints the register must state before it runs, neither of which the audit mentions:**

* **The lag structure is the hypothesis, and it must be fixed in writing first.**
  Heston-Sadka's result is a *pattern across lags* (same-month returns at annual lags 1–20 predict
  positively, non-annual lags negatively). Sweeping lags and reporting the best is the p-hacking
  the register exists to stop. Commit to the published construction — an annual-lag average and its
  non-annual complement — and to nothing else.
* **Depth binds at the panel's early end.** A 20-year lag structure is unavailable in 2009 with
  prices starting 1997-12-31, so the arm is either a **covered-subsample** test on the
  `S18`/`U2`/`U3`/`V6-OPT` protocol or a shallower lag set applied uniformly. **Choose in the
  register, before seeing which is kinder.**

---

## A defect in my own instrument, found by disbelieving a zero

The coverage counter above first read **0 blank transaction codes** on a column that has
1,544,490 of them. Under pandas' string dtype a missing cell is `pd.NA`; `astype(str)` leaves it
`NA` rather than producing `"nan"`, and **`NA` compares False against every literal** — so
`code.eq("") | code.eq("NAN")` was asking a question the data could not answer and getting a
clean, confident zero. It is counted on the raw column now.

**It is the vacuous-pass family in a new costume**, and worth recording for the same reason
`MA14`'s `columns_absent` exists: *a guard that reports zero because it could not see the value
is indistinguishable from a guard that looked and found nothing.* The two neighbouring counts in
the same block — the CMP pair census and the scorer-branch counts — were unaffected, because
boolean indexing treats `NA` as False and that happened to be the correct exclusion there. **The
same language feature produced a right answer in one place and a silent zero in another**, which
is precisely why it was caught by the number looking wrong and not by anything raising.

---

## What this memo does NOT do

* **It measures no arm and adopts nothing.** No file under `valuation/` changes behaviour.
* **`MA26`-A/B, `MA27`, `MA28`, `MA33`, `MA55`, `MA57` and `MA58` are NOT run**, and closing them
  `DESIGN-RECORDED` is not a finding that they would fail. `DESIGN-RECORDED` is a statement that
  the design question is answered, never that the hypothesis is. Anyone opening one of them opens a
  live question, and each needs its own blind pre-registration committed **alone** first.
* **It does not re-measure `MA54`-2.** That landed in the options lane on the same day and is cited,
  not reproduced.
* **`S19` is the one thing here that closes permanently**, and it closes on `MA24`'s own
  pre-committed kill condition rather than on this memo's judgement.
