# PRE-REGISTRATION — INDEX-CHOICE: the evidence for Don's 2026-10-22 rebalance decision

**Committed ALONE, markdown only, zero `.py`, BEFORE any of it is measured.** A strict git
ancestor of every commit that computes a number for items 1 or 3.

**THIS ITEM DOES NOT RE-PICK AND ADDS NO ARM. `INDEX-BEST`'s registered rule stands** — its
winner is arm 3 (liquid top 25) and its highest contract-conformant arm is arm 2 (liquid top
10%, ~150 names). Don's choice is between keeping the incumbent, arm 2, and arm 3. **Nothing
here may change that pick**; it supplies the evidence the pick cannot supply about itself.

---

## 0. Counter and the trial charge, argued from the record's OWN precedent

`by_domain` at writing: **equity 255, options 310, unified 0, infra 20**;
`rows_fixed_not_counted` 88, `rows_malformed` empty.

**THREE EQUITY TRIALS, and the split is taken from how the record charged the two items this
one re-uses rather than from taste:**

* **Item 1, the name split: 2 trials.** `X1` charged **2** for the identical machinery — two
  stable halves plus 100 seeded splits over 200 half-books — and it charged **per STATISTIC**
  (top-decile alpha, long-short *t*), not per book. Don asks for two statistics here: net Roth
  return **vs SPY** and **vs the incumbent**. Two statistics, two trials, across all three arms.
* **Item 3, the factor decomposition: 1 trial.** `R1` charged **exactly 1** for a full FF5+MOM
  regression plus the Hou-Xue-Zhang q-factor model across the long-only book, the long-short
  series and several subperiods. One hypothesis, one trial, across both arms.
* **Item 2, live buildability: 0 trials.** It is a CONTROL in the strict `MB1-SEL` sense — it
  can only BLOCK an arm from being servable on 2026-10-22, never produce a finding — and its
  decile leg **reproduces a figure `D9` has already published**, which makes that leg a
  reproduction as well. The same class as `D9-DIAG`, `W-28`'s `K1` and `MB15`.
* **Item 4, the memo: 0 trials.** It states numbers measured elsewhere and decides nothing.

Equity **255 → 258**. `MB31`: the next adopt-set flip is seed **1017 at equity `N` = 688**, so
**no permutation floor can move**, and this item uses none of them in any case — see §3.

---

## 1. Item 1 — the name split. METHOD INHERITED, NOT CHOSEN

**Every key is IMPORTED from `scripts/r4_x1_accounting_universe.py`, never retyped** (`B7`,
`MA5`): `stable_key_half` (`int(sha1(ticker).hexdigest(), 16) % 2` — no seed, no row order,
reproducible by anyone holding the ticker list), `SEED = 20260813`, `K_SPLITS = 100`, and
`_assert_split`, which is `X1`'s own `C2` control asserting each split is exhaustive, disjoint
and balanced **per split rather than spot-checked**.

**That inheritance is the blindness argument.** The split construction, the seed and the number
of splits were all fixed by `X1` in August, before arms 2 and 3 existed, so there is no
opportunity to choose a split that flatters one of them.

**Arms 1, 2 and 3 are each scored on each half**, exactly as `INDEX-BEST` scored them on the
full universe: the universe trim and the book are rebuilt **within the half**, because the
universe rank and the cross-sectional standardisation are both properties of the population.
`X1`'s own scope limit carries over verbatim and is restated because it bounds everything here:
**layers 1-2 of the panel are computed once over the full universe and are NOT rebuilt per
half, so this is a LOWER BOUND on total name-selection uncertainty.**

**REPORTED: the share of half-books positive vs SPY, the share positive vs the incumbent arm on
the SAME half, the median, and the 5th percentile.** `X1` read its own result against *"if the
5th percentile of that distribution is positive, the result is strong"*, so p05 is reported
because `X1` reported it — **and it is NOT adopted as a bar here**, for the reason in §3.

**WHY THIS IS THE CLOSEST THING TO OUT-OF-SAMPLE AVAILABLE BEFORE 2026-10-22**, which is Don's
own framing and is correct: every held-out gate this project owns splits by DATE, which
conflates *"does the signal generalise"* with *"does the PERIOD generalise"*. A universe split
has **no time-period confound at all**. `INDEX-BEST` found every arm's advantage carried by the
late half; a name split cannot be explained that way.

**AN ASYMMETRY FIXED IN ADVANCE.** Arm 3 holds **25 names**. On a half universe its book is
still 25 names drawn from ~750 — so halving the universe does **not** halve its book, while it
does roughly halve arm 2's. Arm 3 therefore gets a **mechanically noisier** half-book than arm 2
at the same split, and any comparison of their split-stability must say so rather than reading
arm 3's spread as a property of the construction alone.

---

## 2. Item 2 — can a 25-name book be BUILT on 2026-10-22?

**The question is feasibility, not performance, and the answer gates adoption rather than
informing it.** A top-25 book amplifies composite error: it selects the top ~1.7% of a
1,500-name universe against the top 10% for arm 2, so a given per-name ranking error moves a far
larger share of the book.

**What `D9` already measured on the `freeze_2026-07-31` reading, quoted and not re-derived:**
431 overlapping names between the Sharadar-built and live-route books; like-for-like composite
Spearman **0.4321**; **B2 decile overlap 0.2326 against a 60% bar — FAIL**; informative-themes-
only decile overlap **0.3721** — still fail; per-theme Spearman value 0.787, quality 0.626,
momentum 0.965, size 0.984, with **`capital_discipline` NOT MEASURED** (`z_neg_issuance` is not
served) and **`institutional` and `insider` contributing 0**.

**WHAT IS NEW HERE AND WHAT IS NOT. The top-25 overlap on that same population has never been
measured** — that is the new number. **The decile leg is a reproduction**, and reproducing
`D9`'s 0.2326 is the control that proves the instrument is `D9`'s rather than a lookalike.

**A HARD LIMIT STATED BEFORE MEASURING, because it bounds what item 2 can answer: the live
snapshot persists only 500 rows, so arm 2's 1,500-name universe CANNOT be reconstructed from the
`D9` artifacts at all.** What is measurable is the overlap of the TOP-N books on the 431-name
shared population. A top-25 drawn from 431 is the top 5.8% — close in selectivity to arm 3's
1.7% of 1,500 and not identical, and the figure is labelled accordingly.

**PATH A vs PATH B is decided on the measurement and declared as a REFUSAL CONDITION, not a
preference:** if the top-25 overlap on the shared population is below `D9`'s own 60% bar, then
**that book cannot be built correctly by the free route on 2026-10-22** and Path B — Don's
renewed Sharadar, planned ~2026-10-12 — is the only route. The bar is `D9`'s, reused verbatim
rather than re-chosen after seeing the number (`W-28`'s closing lesson).

**The theme job's first run is 2026-10-04**, so `institutional` and `insider` may be non-zero by
2026-10-22. **That is a FORWARD fact this item cannot measure**, and it is recorded as a
condition on Path A rather than assumed either way.

---

## 3. Item 3 — factor loadings, and what may be concluded from them

**`FF5+MOM`, as `R1` did, and `R1`'s own machinery is CALLED rather than reimplemented** —
`scripts/factor_alpha.py`'s `ols_nw`, `regress` and `factor_windows`, with `FF_MODEL` imported.
Newey-West at **lag 1**, which is `R1`'s own choice on non-overlapping 63-day windows.

**REPORTED for arms 2 and 3: the intercept, its NW *t*, R², and every loading.** Don's question
is *"how much of each is a size/momentum tilt rather than selection"*, and the loadings answer
it; the intercept is what is left over.

**NO ALPHA VERDICT IS TAKEN, AND THE REASON IS PRE-COMMITTED RATHER THAN DISCOVERED.** `R1`
pre-registered *"'alpha' only if the FF5+MOM intercept is positive with NW t > 2.0"* and earned
that word on the full panel. **This item does not inherit that licence**, because: (a) these are
NEW constructions whose selection `INDEX-BEST` already measured as not statistically separable
from the incumbent's, (b) `INDEX-BEST` established that **every** arm's advantage is carried by
the late half, which a full-sample intercept cannot see, and (c) `R1`'s own fragility work found
a ~10-year window at *t* 1.39 with 8 of 70 rolling windows insignificant. **So a positive
intercept here is a DECOMPOSITION, not a new claim**, and the write-up may not call it alpha.

---

## 4. No bar, and therefore no uncalibrated threshold anywhere

**This item sets NO pre-committed bar of its own, and that is deliberate.** `V2G` and `R1-VAR`
established that **no calibrated floor exists for a paired within-panel difference**, and
`INDEX-BEST` measured that the design cannot separate these arms anyway — even at ρ = 0.95 its
80%-power MDE was **+3.69pp/yr** against an incumbent edge over SPY of +1.95pp.

**Every critical value quoted anywhere in this item is LABELLED UNCALIBRATED**, including the
conventional 2.0 and `X1`'s p05 reading. **`D9`'s 60% overlap bar is the ONE exception** — it is
a feasibility bar `D9` pre-committed, and it is reused verbatim.

**THE OUTPUT IS A DECISION MEMO FOR DON, NOT A VERDICT.** §5 fixes what the memo may and may
not say before any of it is known.

---

## 5. The memo's rules, fixed before the evidence exists

1. **Every return figure is quoted in `INDEX-BEST`'s fixed sentence form** — in-sample, 69
   quarterly rebalances, net of modelled trading costs, no tax, not a forward test, and the
   difference from the incumbent not statistically separable.
2. **Every option carries its early/late split**, because that is where `INDEX-BEST` found the
   whole effect.
3. **Arm 3's contract consequence is stated every time it is named**: 25 names against
   `CONTRACT_MIN_POSITIONS = 50`, conformant on 0 of 69 dates, refused by `seed_book`.
4. **Adoption of ANY option is a vintage event** that closes the current vintage and opens the
   next, resetting the five-year clock for no statistical gain (`RUN_RULES` rule 6). **The
   vintage number is DERIVED from `track_meter.VINTAGES` and never quoted from a document** —
   three separate items in this record have quoted a stale one.
5. **NO RECOMMENDATION unless the evidence makes one obvious, and the memo must say which case
   it is.** If the three options are separated by less than this design can resolve — which §4
   says is likely — the honest output is "these are not distinguishable on the evidence; here is
   what each costs you", and saying so is the deliverable rather than a failure to deliver.

---

## 6. Void conditions

1. **No re-pick.** `INDEX-BEST`'s rule stands and its winner is not revisited.
2. **No new arm.** Arms 1, 2, 3 only; arm 4 (the ceiling) is not carried into this item.
3. **No bar invented after a number is read**, and `D9`'s 60% is not relaxed.
4. **No alpha claim** from §3, in either direction.
5. **Nothing is adopted.** No live constant, no contract constant, no `MEASURED_BASIS`.
6. **`X1`'s method is not modified** — not the key, not the seed, not the split count.

---

## 7. Expectations, registered now and scored afterwards

1. **All three arms are positive vs SPY on a large majority of half-books: 80/20.** `X1` found
   200 of 200 half-books positive for the incumbent decile and `INDEX-BEST` found all three arms
   positive full-sample, so the sign is not in doubt; the share is.
2. **Arm 2 beats the incumbent on MORE half-books than arm 3 does: 60/40.** Arm 3's larger
   full-sample margin is offset by the §1 asymmetry — its 25-name book does not shrink with the
   universe, so its half-books are noisier.
3. **Arm 3's half-book distribution is the widest of the three: 85/15** (`B17`, and the §1
   asymmetry compounds it).
4. **Both arms load positively on SMB with *t* > 2: 75/25.** Their median market cap is ~$2.1-2.5bn
   against the incumbent's $18.1bn, so a size loading is close to mechanical.
5. **Neither arm's FF5+MOM intercept is the dominant term — the loadings explain more than the
   intercept: 55/45.** `R1` found R² 0.308 on the incumbent spread, which leaves a lot
   unexplained, so this is genuinely uncertain.
6. **The top-25 live overlap is BELOW `D9`'s decile overlap of 0.2326: 70/30.** A tighter cut
   amplifies the same per-name error.
7. **Path A cannot build either book correctly on 2026-10-22: 85/15.** `D9`'s verdict is NO-GO
   and two of seven themes still contribute nothing.
8. **The memo ends with NO recommendation: 60/40** — §4's arithmetic says the options are not
   separable, and that is the modal outcome.

---

## 8. NOT done, named so it is not mistaken for done

* **No re-pick, no new arm, nothing adopted.**
* **No forward test.** A name split is not out-of-sample in time and does not become one.
* **`X1` is not re-run** and its published figures are not re-derived.
* **`D9` is not re-opened**; its verdict stands and only the top-25 leg is new.
* **No q-factor model.** `R1` ran Hou-Xue-Zhang as a secondary; Don asked for FF5+MOM and that
  is what runs, so no claim is made about robustness to a different factor model.
* **The live route's post-2026-10-04 state is unmeasured** and is a condition, not a finding.
