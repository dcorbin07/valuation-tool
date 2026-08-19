# PRE-REGISTRATION — MB1, the alternatives MENU and the selection-vs-timing decomposition

**Committed before any measurement code for this item exists.** This file is the only file in its
commit; no `.py` accompanies it, so the ordering is provable with
`git show --name-only --format= <commit>`.

Item **MB1** of `VALQUO_MASTER_AUDIT_4.md`. Options domain. **2 trials, booked before the run:
options `N` 300 -> 302.**

---

## 0 · STATE OF KNOWLEDGE WHEN THIS WAS WRITTEN, DISCLOSED IN FULL

Everything here was measured **before** this register existed and **none of it is an outcome**.
Every item is a coverage, instrument or feasibility fact.

### 0.1 · THE AUDIT'S CENTRAL NUMBER IS THE WRONG OBJECT, AND THE REAL MENU IS 130x SMALLER

MB1 is built on *"2,713,919 alternative contracts, median 636 per entry date"* and proposes *"a
distribution over ~636"*. **That 636 is the whole chain. The ENGINE'S OWN in-band, fillable menu
— the thing `pick_contract` actually chooses from — has a median of FIVE.**

Measured on 80 randomly sampled covered alert entries, stage by stage through the shipped
prefilter:

| stage | median rows | survival |
|---|---|---|
| raw chain on the entry date | 864 | — |
| calls only | 432 | x0.500 |
| DTE in [45, 75] | **31** | **x0.072** |
| moneyness `strike/underlying` in [0.90, 1.20] | 10 | x0.323 |
| delta solvable | 9 | x0.900 |
| **fillable (`quote_reject_reason is None`)** | **5** | **x0.556** |

**The DTE band does most of the cutting** (the harvest carries expirations out to 1,200 DTE and
only one or two land in 45-75), and **the fillability filter removes nearly half of what is left**
— refused on `low_volume` 53.5%, `wide_spread` 44.1%, `thin_premium` 2.4%.

**This is MA31's pair-availability warning, and it is far more severe than MB1 anticipated.** The
item says only that *"the effective menu will be smaller than 636"*. It is **5**. The register
proceeds anyway — see 0.2 — but **any reading of this result that leans on "a distribution over
~636" is void.**

### 0.2 · WHY IT IS STILL WORTH RUNNING, STATED BEFORE THE RESULT

The question is unchanged: **does the alert-day menu distribution differ from the random-day menu
distribution?** A five-contract menu makes the *per-entry* median coarse, but the arms pool
**2,446 alert entries** and **18,531 control entries**, so the pooled menu distributions carry
roughly **12,000** and **93,000** legs. That is ample for the 1.0pp kill condition. **What is lost
is the ability to describe a rich within-entry distribution; what survives is the comparison MB1
exists to make.**

### 0.3 · COVERAGE, AND THE TWO ARMS ARE COMPARABLY COVERED — WHICH IS THE POINT

Requiring every harvest unit from the entry year through the **expiry** year:

| arm | covered | of | % |
|---|---|---|---|
| ALERT | 2,446 | 3,870 | **63.2** |
| control seed 0 | 3,756 | 6,003 | 62.6 |
| control seed 1 | 3,713 | 5,946 | 62.4 |
| control seed 2 | 3,676 | 5,869 | 62.6 |
| control seed 3 | 3,721 | 5,967 | 62.4 |
| control seed 4 | 3,665 | 5,869 | 62.4 |
| **control pooled** | **18,531** | **29,654** | **62.5** |

**63.2% against 62.5% is a 0.7pp difference, so the comparison is not confounded by differential
coverage** — which is the single most dangerous confound available to a two-arm design on a
partially covered freeze. Had they diverged materially this register would have had to match on
coverage before comparing.

Coverage is **systematic rather than random** (Tier A complete, Tier B partial), so **both arms
are early-tilted in the same way**. Stated now because it constrains generalisation, not the
comparison.

### 0.4 · THE PINNED ARTIFACT MOVED UNDER ME, AND THAT IS RECORDED RATHER THAN SMOOTHED OVER

`O21-D2` (2026-08-18) recorded the harvest freeze at manifest sha256 `db7f0f84...`, **1,865**
payload units, generated `2026-08-18T10:28:29Z`. **The same root
`D:\thetadata\freeze_rawpull_2026-08-18` now reads sha256 `ee6d38e5ff584420cd6305a22c7ff15d296872325d7e4ae39caecfc20c19f000`, 2,850 units, generated
`2026-08-19T03:39:52Z`.**

**A dated freeze directory whose contents were rewritten a day later is the O16 failure the pin
exists to prevent, in the artifact built to prevent it.** It was caught **only** because the
fingerprint is recorded rather than the label — which is the whole argument for recording it.

**MB1 runs on the CURRENT bytes and records the current fingerprint.** `O21-D2`'s numbers are
being independently re-verified against the new bytes in a separate pass; that result is reported
with this one and **is not a condition of this register**.

### 0.5 · Other facts fixed now

* **The comparator books are `control_r2_splitclean_seed{0..4}.pkl`** — `R2`'s own five split-clean
  random-entry books, 29,654 rows pooled. No new control is constructed.
* **The delta axis of the surviving menu**: p05 0.123, p25 0.291, median **0.470**, p75 0.641,
  p95 0.812. **The menu's median delta is 0.47, well above the 0.35 the engine targets** — so the
  menu is not centred on the pick, and a delta axis is genuinely needed rather than decorative.
* `pre_panel_history` is filtered; its exposure is reported (C5).

**NOT KNOWN, and this is what the register commits to:** any menu return, any difference between
the arms, and the sign of that difference.

---

## 1 · THE MENU DEFINITION, VERBATIM FROM THE SHIPPED PREFILTER

Taken from `options_backtest.pick_contract` so it is **the engine's own menu**, not a
reconstruction. The menu is everything that survives the prefilter; `pick_contract` then takes
`argmin |‌|delta| - 0.35|` over exactly this set, so **the shipped pick is by construction a member
of the menu.**

1. `right` starts with `C` (calls only — the banked book is 100% calls, per `O13`);
2. `DTE in [45, 75]`, i.e. `OB.DTE_RANGE`, inclusive both ends;
3. moneyness `strike / underlying_entry in [0.90, 1.20]`, **including the shipped fallback**: if
   nothing lands in the band, the DTE-band set is used instead. Kept verbatim rather than
   "cleaned", because removing it would make this a different menu from the engine's;
4. `enrich_chain` then `dropna(subset=["delta"])`;
5. `options_fill.quote_reject_reason(q) is None`, with `q` carrying bid, ask, open interest and
   volume — the fillability filter, which 0.1 shows removes nearly half.

**Any deviation from this list is a void condition.** The menu is built by a function that is
tested against `pick_contract` returning a member of it.

## 2 · ARMS, STATISTICS AND THE BAR

**Instrument.** Both arms read the **PINNED harvest freeze** through
`valuation.edge.chain_store.resolve_harvest`, which raises rather than falling back. The mutable
`data/options` may not be opened. Chains are as-traded; `raw_close` for anything touching a
strike and `close` only for a return (`U1-SPLIT`/`O6`).

**Simulation.** Every menu contract is run through the **SHIPPED**
`options_backtest.simulate_trade`, unmodified — same target, stop, time stop, fill model and
aggression as the book. Re-implementing the exit walk would make the answer a function of a second
definition of the thing under test (the B7 defect class), and it is what `O21-D2` did.

**A1 — PRIMARY: the POOLED menu median.** Within an arm, pool every menu leg across every covered
entry and take the **median** `return_pct`. This is literally *"the outcome distribution of the
whole in-band menu"*, and it is what the kill condition compares.

**A2 — DECLARED SECONDARY: the pooled menu p75**, reported with the same both-halves treatment and
carrying no independent verdict.

**Reported, no verdict:** the **entry-weighted** variant (per-entry menu median, then the median
across entries). Registered now because a reader will ask which weighting was used, and choosing
it after seeing both is what the void conditions forbid. **A1 is pooled; the entry-weighted figure
may never be quoted as the primary.**

**Comparator.** The five split-clean random-entry books pooled. The identical menu construction,
the identical simulator, the identical coverage requirement.

**Both halves.** Split at the median entry date of the covered ALERT set, applied to both arms.
The kill condition is evaluated **in each half separately**.

**Delta-bucket reporting grid**, pre-committed from 0.5's measured distribution, `|delta|`:
`[0.00, 0.15)` (thin, 6.8% of legs — flagged as such in advance), `[0.15, 0.35)`, `[0.35, 0.60)`,
`[0.60, 1.01)`. **Reported for both arms in both halves. It carries NO verdict** — it exists so
that delta is a reported axis rather than an uncontrolled by-product, which is the remedy
`MA54-4` prescribed and `O6` could not apply.

## 3 · THE KILL CONDITION, AS WRITTEN

**If the alert-day and random-day pooled menu medians differ by LESS THAN 1.0pp in EITHER half,
contract selection is declared IRRELEVANT and no further contract-selection register may be
opened on this book.** Permanently.

Stated the other way so it cannot be softened afterwards: **the condition fires on the weaker of
the two halves.** A 3pp gap in one half and a 0.4pp gap in the other **fires the kill** — the rule
is "less than 1.0pp in either half", not "in both".

**If the gap is at least 1.0pp in both halves and the signs agree**, the alert is picking bad
*chains* rather than bad *days*, `O13`'s within-bin finding needs re-reading, and that re-reading
is a **NEW** register. **A pass does not license a trade — `O11` binds** (a book with positive
per-trade expectancy ended at $37,059 from $50,000 at a concurrency cap of 10).

**If the two halves disagree in SIGN**, no directional claim is made in either direction and the
item is recorded UNRESOLVED on the direction while the kill condition is still evaluated on the
magnitudes.

## 4 · CONTROLS — C1 and C2 are GATING and run in their own pass

`--arms` **refuses** without a passing controls artifact. A gating control computed in the same
pass as the outcomes cannot be claimed to have been read first (session 26's defect, repaired in
O19 and kept since).

* **C1 · GATING — the menu contains the shipped pick.** On covered alert entries, the contract
  `pick_contract` returns must be a **member of the menu** this register builds, and the menu's
  `argmin |‌|delta| - 0.35|` must **be** that contract. **Bar: >= 99% agreement.** Below that, the
  menu is not the engine's menu and no comparison it supports means anything. **Abort.**
* **C2 · GATING — coverage parity.** The alert and pooled-control coverage shares must lie within
  **2.0pp** of each other (measured: 63.2% vs 62.5%). Outside that, the arms are not comparable
  and A1 is reported UNINTERPRETABLE.
* **C3 · the chain source is the PINNED harvest**; the mutable store is never opened. Pinned by
  test, and the fingerprint ships in the artifact.
* **C4 · menu-size parity, reported.** The two arms' menu-size distributions ship side by side. A
  large asymmetry would mean the arms are comparing differently-sized menus, which is a caveat on
  the pooled statistic and is disclosed rather than corrected.
* **C5 · `pre_panel_history`** filtered and reported, **VACUOUS vs PASSING distinguished** — the
  key is absent on Tier A/B units, so a clean pass there is the absence of a question, not an
  answer to one.
* **C6 · the uncovered ~37% is UNMEASURED, never zero.** Every quoted figure carries the coverage
  share.

## 5 · TRIAL COST

**2 options trials**, exactly as the item specifies. `N` **300 -> 302**, booked in
`RESEARCH_LOG.md` **before** the measurement runs.

Two rather than one because there are two pre-registered statistics carrying stated treatments
(A1 median and A2 p75), and one rather than four because the delta buckets and the entry-weighted
variant carry **no verdict** and are reported for every arm and half regardless of what they say.

## 6 · WHAT WOULD MAKE THIS REGISTER VOID

* Deviating from the menu definition in section 1, including "fixing" the shipped fallback.
* Opening the mutable `data/options`, or reading any freeze other than the pinned harvest.
* Constructing a new random-entry control instead of using `R2`'s five books.
* Quoting the entry-weighted variant as the primary, or swapping A1 and A2 after seeing them.
* Quoting a menu figure without the coverage share, or reading the uncovered entries as zero.
* Softening the kill condition from *"either half"* to *"both halves"*.
* Leaning on "a distribution over ~636" — see 0.1.
* Adding a delta cut, a DTE cut or a sub-population after seeing A1.
* Treating a passing gap as a licence to trade; `O11` binds.

## 7 · EXPECTATIONS, WRITTEN BEFORE ANY OF IT RUNS

* **E1 — the kill condition FIRES: the menu medians differ by less than 1.0pp in at least one
  half. 75/25.** The audit's own prior is *"~20% that selection carries any of the loss"*, and
  `O13` already measured the `R2` gap to be **entirely within-bin** — the largest mix component
  anywhere was 0.77pp of a 5.06pp gap. If composition carried nothing, a menu-wide comparison
  should show little.
* **E2 — both arms' pooled menu medians are DEEPLY NEGATIVE, near -100%. 70/30.** A 45-75 DTE
  call at a median delta of 0.47 held under a -50% stop and a 100% target mostly expires worthless;
  `O17C4` measured the median spanning trade at about -51% on a far narrower selection. **If true,
  the median is a weak instrument here and the p75 secondary will carry more information than the
  primary** — registered now because it would otherwise look like a post-hoc excuse.
* **E3 — the alert arm is WORSE than the control arm on the pooled median, if it differs at all.
  55/45.** Barely better than a coin flip: `R2` says the alert loses on the *pick*, and `O13` says
  the loss is within-bin, which points at neither arm's menu.
* **E4 — the delta buckets show returns falling monotonically as delta falls** (lower delta, more
  levered, more total losses). **60/40.**
* **E5 — C1 clears 99%.** A harness check, **not scored**.
* **E6 — the two halves DISAGREE on the sign of the gap. 50/50**, recorded as a genuine coin flip
  rather than a prediction.

**Scored honestly at the end, wrong calls first.** This lane's last register went 4 right, 0 wrong
and 1 unresolved, and that was discounted rather than celebrated because the priors came from
measured facts. The same discount applies here: E1 and E2 lean on `O13` and `O17C4` measurements
already in the record.
