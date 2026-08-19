# PRE-REGISTRATION — O21-D2, the alternative contract's P&L

**Committed before any measurement code for this item exists.** This file is the only file in its
commit; no `.py` accompanies it, so the ordering is provable with
`git show --name-only --format= <commit>`.

**This is a RE-OPEN, and it is the only one `HANDOFF_options_reopen_list.md` (`10977a2`) classified
as an unambiguous SAME-hypothesis re-open.** It does not re-litigate O21's verdict. It closes the
one door O21 itself named `UNRESOLVED` and reported as **not computable** rather than as zero.

Options domain. **1 trial, booked before the run.**

---

## 0 · STATE OF KNOWLEDGE WHEN THIS WAS WRITTEN, DISCLOSED IN FULL

Everything in this section was measured **before** this register existed and **none of it is an
outcome**. Every item is a coverage or instrument fact. Fixing them first is what O21 and
`DEEPITM-FIN` both did, and it is the only reason the scope limit below can be stated honestly
rather than discovered afterwards.

**O21's divergent set reproduces EXACTLY.** Re-running O21's own selection — its `_pick_contract`
at `q = 0` against `_pick_with_q` at `q_trailing`, on the same trade-scope freeze — gives
**scored 3,870, control reproduces the banked contract 3,870/3,870 = 100.00%, contract CHANGES on
179**. The 179 in this register are literally O21's 179, not a re-derivation that happens to agree
on a count.

**The referent now exists, and it is the harvest freeze rather than the one I pinned last
session.** `D:\thetadata\freeze_rawpull_2026-08-18` (1,865 units, 12.44 GB, `hash_mismatches_at_copy`
0) holds **full chains on every trading session**, not only on entry dates:

| probe unit | sessions | contracts/session (median) | bid/ask non-null |
|---|---|---|---|
| `AAPL-2018` | 251 | 1,558 | 100.00% / 100.00% |
| `A-2016` | 252 | 202 | 100.00% / 100.00% |

**That is precisely what O21 lacked.** Its blocker was that the trade-scope freeze
(`data/options_freeze/R2_CORRECTED_2026-08-08/`) holds the full chain only on ENTRY dates — median
**2** chain dates for an alternative, 10.1% with more than 3 — so a contract the book never held
had no forward path.

**The alternative's path is COMPLETE, not merely present.** On every coverable divergent entry the
alt contract carries a mark on **every session** in the holding window: completeness ratio
**median 1.0000, minimum 1.0000, p10 1.0000, and 100.0% of entries at full completeness.**

**THE TWO INSTRUMENTS AGREE BIT-FOR-BIT, and without this the arm would be uninterpretable.**
Comparing the harvest against the trade-scope freeze on the **BANKED** contract at its entry date:
**115 of 115 match on bid AND ask exactly, 0 mismatches, 0 unlocatable.** This is what licenses
pricing **both** arms on the harvest — otherwise a difference between arms would be partly a
difference between instruments.

**Coverage is 113 of 179 = 63.1%, and it is SYSTEMATIC rather than random.** Requiring every
harvest unit from the entry year through the later of the two contracts' **expiry** years:

| entry year | divergent | coverable | % |
|---|---|---|---|
| 2016 | 16 | 16 | 100.0 |
| 2017 | 22 | 22 | 100.0 |
| 2018 | 19 | 18 | 94.7 |
| 2019 | 16 | 5 | 31.2 |
| 2020 | 17 | 6 | 35.3 |
| 2021 | 25 | 15 | 60.0 |
| 2022 | 14 | 7 | 50.0 |
| 2023 | 15 | 7 | 46.7 |
| 2024 | 25 | 10 | 40.0 |
| 2025 | 10 | 7 | 70.0 |
| **total** | **179** | **113** | **63.1** |

**The covered set is EARLY-TILTED and this register says so before any number.** Tier A (alert
symbol-years 2016–2018) ran to completion; Tier B (2019–2025) was cancelled at 490 of 961 units
when the census showed the years were not perishable. So **56 of 113 covered entries (49.6%) are
2016–2018, against 57 of 179 (31.8%) in the full divergent set.** Any era-sensitive reading of the
result inherits that tilt.

**A CORRECTION TO MY OWN FIRST COVERAGE MEASUREMENT, recorded rather than quietly replaced.** The
first probe required units for `entry_year .. exit_year` where `exit = entry + held_days`, and
returned **115 (64.2%)**. That is the wrong window: `simulate_trade` holds to **EXPIRY** whenever
no trigger fires, and **22 of 179 alternatives (12.3%) carry a DIFFERENT expiry from the banked
contract.** The corrected requirement is stricter and gives **113 (63.1%)**. The looser figure is
not used anywhere below.

**Other facts fixed now:** the shipped U1-SPLIT refusal rejects **0 of 113** in the base arm and
**0 of 113** in the alt arm, so no comparison is confounded by a refused trade; the coverable set
spans **59 names**; and the miner's `pre_panel_history` contamination flag has **zero** exposure
here — see C5, where it is reported **VACUOUS rather than PASSING**, which is a different claim.

**NOT KNOWN, and this is what the register commits to:** any P&L for any alternative contract, any
difference between the arms, and the sign of that difference.

---

## 1 · THE QUESTION, unchanged from O21's own UNRESOLVED door

O21 measured that the dividend-corrected pricer picks a **different contract on 179 of 3,870
entries (4.63%)**, and **not a near-substitute** — median absolute delta gap **0.129** against a
0.35 target, **93.9%** moving to a lower strike. It could not price that alternative book and
**reported the P&L as NOT COMPUTABLE rather than as zero**, which is the only reason this is
answerable now instead of settled.

**The question is exactly: what is the alternative book's per-trade P&L against the shipped book's,
on those entries?** Nothing else is asked. O21's `IMMATERIAL` verdict on D1 and D3 is not re-opened,
`q_scheduled` still may not carry a verdict, and the pricer is not being proposed for change.

---

## 2 · THE HONEST SCOPE, FIXED BEFORE ANY NUMBER — AND IT LARGELY DECIDES THE ANSWER

**113 entries is a small sample and 4.63% is a small share, and those two facts bound the result
before it is measured.** The arithmetic is stated here so nobody has to be trusted with it
afterwards.

The banked book is **3,870 trades at +3.2702%/trade**. Replacing the divergent trades changes book
expectancy by `(n_divergent / 3870) × mean(Δ)`. So:

* **across all 179 divergent entries (4.6253%), reaching O21's own 1.00pp materiality bar requires
  a mean per-trade difference of 21.62 percentage points;**
* **across the 113 coverable entries (2.9199%), it requires 34.25 percentage points.**

**A 21.6pp mean shift on a 0.13-delta substitution is not a plausible outcome, and saying so now is
the point of saying it now.** The maximum book-level impact is therefore bounded at roughly
**±0.05pp per 1pp of measured mean difference**, and this register expects the answer to be
**IMMATERIAL**.

**The value of running it is that O21's UNRESOLVED door closes with a measurement instead of a
shrug.** "Not computable" and "computable and small" are different states of knowledge, and only
the second one stops a future session re-opening this.

**A NULL HERE IS NOT A FINDING THAT THE PRICER IS CORRECT.** It is a finding that the pricer's
contract-selection error is too small a share of the book to matter, measured on 63.1% of the
affected entries. Those are different claims.

---

## 3 · DATA AND DEFINITIONS, FIXED NOW

**Book.** `state_r2_splitclean.pkl`, n 3,870 (U1-SPLIT, 2026-08-11). No other book. No re-mine.

**Selection instrument — UNCHANGED FROM O21.** The divergent set is produced by O21's own code on
O21's own trade-scope freeze, so the 179 are inherited rather than re-derived. `q_trailing` only;
`q_scheduled` is forbidden a verdict here exactly as it was there.

**Pricing instrument — the PINNED harvest freeze, and nothing else.**
`D:\thetadata\freeze_rawpull_2026-08-18`, resolved through the shared resolver
`valuation/edge/chain_store.py` built last session, extended to this freeze with the same
discipline: it verifies the freeze is **populated**, records the manifest fingerprint, and
**raises** rather than falling back. **The mutable `data/options` store may not be opened**, and a
test pins that.

**BOTH ARMS ARE PRICED ON THE SAME INSTRUMENT.** The base arm is **re-simulated** on the harvest
rather than read from the banked book, so any difference is attributable to the contract and not to
the data source. The banked figure's role is as the **control** (C2), not as the comparator.

**Exit engine — the SHIPPED one, unmodified.** `options_backtest.simulate_trade`, driven by a
harvest-backed provider supplying `contract_history`. Target, stop, time stop, fill model and
aggression are untouched. Re-implementing the exit walk would make the answer a function of a
second definition of the thing under test — the B7 defect class this project has paid for
repeatedly.

**Settlement on as-traded spot.** `bars["raw_close"]`, never the adjusted `close`, per the
U1-SPLIT/O6 rule: `raw_close` for anything touching a STRIKE. The shipped `simulate_trade` already
does this and is not being altered.

**pre_panel_history.** The miner's flag is applied and its result **reported**, per §4 C5.

---

## 4 · ARMS, CONTROLS AND THE BAR

### The single arm

**A1 (PRIMARY, and the only arm).** Over the coverable divergent entries: simulate the **banked**
contract and the **alternative** contract through the shipped exit policy on the harvest, and
report the **mean and median per-trade return difference `alt − base`**, with `n` printed beside
every estimate.

**There is no second arm.** Adding one after seeing A1 is a void condition (§6).

### THE BAR, pre-committed

**D2 is MATERIAL if either:**

* **(a)** the implied **book-level** expectancy effect, `(179 / 3870) × mean(Δ)`, is **≥ 1.00pp in
  absolute value** — i.e. `|mean(Δ)| ≥ 21.62pp` — reusing **O21's own materiality bar verbatim
  rather than inventing a new one**; or
* **(b)** any published verdict's relationship to its bar changes. **This clause governs even if
  (a) fails**, and it is the one that matters.

**Below both, the finding is IMMATERIAL and the pricer is left alone with the measurement
recorded.** A near miss is IMMATERIAL, not a fix (`RUN_RULES` A6).

**The bound in §2 is quoted with the verdict or the verdict is not quoted.** Reporting a mean Δ
without the 21.62pp bar beside it invites reading a 5pp per-trade difference as a large effect when
it is 0.23pp of book expectancy.

### The halves rule

The headline is a **cost measurement**, not a hypothesis test, so it carries no half-split
requirement — a defect's size is what it is. **But any DIRECTIONAL claim** — of the form *"the
dividend-corrected pricer picks better (or worse) contracts"* — **requires the sign of mean(Δ) to
agree across both halves**, split at the median entry date of the coverable set. **Sign
disagreement means no directional claim may be made in either direction**, and the cost measurement
still stands.

**Stated in advance because it weakens that leg: the coverage tilt in §0 makes the two halves
unbalanced by construction**, the early half being far better covered. So a halves agreement here
is weaker evidence than a halves agreement on a fully covered sample, and a disagreement is
correspondingly cheap. **The directional claim is the secondary reading and the cost is the
primary one.**

### Controls — C1 and C2 are GATING and run in their own pass

**The controls pass is separate and its artifact is written first.** `--arms` **refuses** to run
without a passing controls artifact. This is session 26's defect repaired rather than repeated: a
gating control computed in the same pass as the outcomes cannot be claimed to have been read first.

* **C1 · GATING — the selection reproduces.** O21's control must re-fire: the `q = 0` arm must
  return the banked contract on **3,870 of 3,870** entries, and the divergent count must be
  **exactly 179**. Anything else means the selection harness has drifted and no difference it
  reports means anything. **Abort.**

* **C2 · GATING — THE NULL INSTRUMENT, and it is the brief's own control.** The **non-divergent**
  entries hold the **same contract in both arms**, so re-simulating them on the harvest must
  reproduce the **banked** `return_pct`. Measured over every non-divergent entry with harvest
  coverage. **Bar: ≥ 95% exact reproduction to within 1e-9.** Below 95%, **A1 is reported as
  UNINTERPRETABLE and no Δ is quoted** — because at that point the harvest and the banked
  instrument disagree about trades on which they cannot legitimately disagree, and the arm would be
  measuring that disagreement.
  **The reproduction rate is reported BEFORE any Δ, unconditionally, whatever it says.**
  **A genuine risk named in advance: the harvest carries MORE holding days than the trade-scope
  freeze**, so a stop or target could trigger on a day the banked simulation never saw. **That
  would be a real finding about the banked instrument, not a bug in this one**, and it is exactly
  what C2 exists to expose rather than absorb.

* **C3 · the chain source is the PINNED freeze.** The mutable `data/options` is never opened.
  Pinned by test and by the resolver raising rather than falling back.

* **C4 · as-traded spot.** Settlement uses `raw_close`. Reported, and pinned by the shipped
  engine's own code path.

* **C5 · pre_panel_history — REPORTED AS VACUOUS, NOT AS PASSING.** The filter is applied. It is
  already measured that **0 of the 114 harvest units this arm reads carry the flag**, and that
  **none of the five named ticker-reuse symbols (FOXA, IR, VG, CR, AZPN) appears among the 59
  coverable names** — because those are Tier C names and this book is Tier A/B. **The key is ABSENT
  on these units rather than present-and-false**, so the filter passes by having nothing to look
  at. **A vacuous filter reported as a clean pass is this project's most repeated failure class**,
  so it is labelled here instead.

* **C6 · era balance, reported.** The coverable set's year distribution ships beside the result, so
  the tilt in §0 travels with the number rather than being available only in this file.

* **C7 · the uncoverable 66 are reported as UNMEASURED, never as zero.** Their Δ is unknown. Any
  statement of the form *"D2 is worth X across the book"* must carry the 63.1% coverage figure.

---

## 5 · TRIAL COST — BOOKED BEFORE THE RUN

**1 options trial.** One arm, one pre-committed bar, no grid, no sweep, no second definition.

`N` (options) **297 → 298**. Booked in `RESEARCH_LOG.md` **before** the measurement runs, per the
brief and per the `DEEPITM-FIN` precedent of committing the budget at a named commit ahead of the
result.

**Why 1 and not 0.** O21's own row was first charged **zero** as a `FIXED`-class correctness
measurement and that was **rejected** by another lane's research-page test, on the rule that a row
returning a verdict against a bar is a trial whatever its motivation. This row returns a verdict
against a bar. **Charged upward for the same reason, and the precedent is O21's own correction
against itself.**

**Why not 2.** There is one arm. Charging 2 for one arm would overstate `N`, which is the safe
direction for significance but is still wrong, and the halves split is a robustness reading of the
same arm rather than a second search.

---

## 6 · WHAT WOULD MAKE THIS REGISTER VOID

* Re-mining, or using any book other than `state_r2_splitclean.pkl`.
* Opening the mutable `data/options` store for any read in the arm path.
* Changing the exit policy, the fill model, the aggression, or the moneyness/DTE bands.
* Letting `q_scheduled` carry a verdict.
* Quoting a Δ without first reporting C2's reproduction rate.
* Reading the 66 uncoverable entries' Δ as zero, or quoting a book-level figure without the 63.1%
  coverage limit.
* Adding a second arm, a second bar, or a sub-population cut after seeing A1.
* Re-deriving the divergent set by any route other than O21's own code, or quoting a divergent
  count other than 179.
* Changing any ledger verdict. **This register cannot move O21's verdict**; it can only replace
  the string `NOT COMPUTABLE` with a measurement, and if the result were material the consequence
  would be a **new** register proposing a pricer change, not an edit here.

---

## 7 · EXPECTATIONS, WRITTEN BEFORE ANY OF IT RUNS

* **E1 — IMMATERIAL. 85/15.** The bound in §2 requires a **21.62pp** mean per-trade difference.
  Nothing in O21's substitution statistics suggests a shift of that size, and this is the most
  confident prediction in the register.
* **E2 — mean(Δ) is NEGATIVE: the alternative earns LESS. 65/35.** The alt moves to a **lower
  strike on 93.9%** of entries, i.e. deeper in the money, median absolute delta gap **0.129** above
  a 0.35 target. A higher-delta call is **less levered**, so in percentage terms it should capture
  less of the right tail that carries this book's positive expectancy. **The mechanism is the
  prediction; a positive mean would refute it.**
* **E3 — |mean(Δ)| < 15pp. 60/40.** Genuinely uncertain and the least confident call here. These
  are levered instruments and 0.13 of delta is a large move; a fat-tailed per-trade distribution on
  n = 113 can produce a big mean from a handful of trades.
* **E4 — C2 reproduces ≥ 99%.** Charged as a harness check, **not scored as a prediction**.
* **E5 — the sign of mean(Δ) does NOT agree across both halves. 55/45.** n = 113 split in two is
  thin and the halves are unbalanced by the coverage tilt. If this is right, **no directional claim
  is made and E2 is recorded as unresolved rather than as confirmed.**
* **E6 — the median Δ is closer to zero than the mean. 70/30.** O13 and O17-C4 both found this
  book's effects to be mean phenomena on a right-skewed distribution; the same shape is expected
  here.

**Scored honestly at the end, wrong calls first.** This lane's expectation record is the reason the
predictions are written down: the four registered priors in `DEEPITM-FIN` were all right and the
**brief's** own expectation was wrong as stated, and the sessions before that ran 2-right-4-wrong
and 3-right-4-wrong. **A prior that keeps being wrong is worth more written down than remembered.**
