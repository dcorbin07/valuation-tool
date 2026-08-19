# PRE-REGISTRATION — O14, the tick-flow signal studies

**One register, five arms, committed ALONE before any measurement code exists.** Ledger row `O14`,
whose status is `OPEN — collection DONE, first analysis LANDED, the justifying studies still
undone`. **This register is those studies.**

---

## §0 SCOPE FACTS, ALL MEASURED BEFORE THIS REGISTER WAS WRITTEN

### §0.1 The `O14` ledger row is ACCURATE — and it is the one written by a human

Six audit rows in this series carried `src=auto` notes claiming no audit section existed, and all
six were wrong (`O6`, `O17`, then `O11`, `O19`, `O22`, `O25`). **`O14`'s row is `src=human`, and
it is correct in every particular**: collection complete, first analysis landed, *"the put/call and
unusual-volume studies this cache was justified by are still not done."* That is exactly the gap
this register closes. **The one row a human wrote is the one that was right**, which is the
strongest argument yet for reading `src=auto` as a lead and never as a fact.

`VALQUO_EDGE_AUDIT.md:1106` is a full section and every definition below is **quoted** from it.

### §0.2 Coverage: 3,869 of 3,870, and the one gap is named

Every banked split-clean trade has its alert-day tick file except **`BUD` 2024-01-10**, the known
single feed gap. **99.97%.** That one trade is excluded and named rather than silently dropped.

### §0.3 The tape carries everything the audit's method needs

Per print: `price`, `size`, the prevailing `bid`/`ask` (Lee–Ready), `exchange` (sweep detection),
and `right` (put/call). Measured on a 12-day sample: **190,130 prints, median 15,844 per alert-day,
puts are a median 32.6% of prints** (so a put/call imbalance is real, not degenerate), **19 distinct
exchanges**, print size median 1 with p99 52 and max 4,886.

### §0.4 A DAILY CROSS-SECTION IS IMPOSSIBLE, SO THE SORT IS MONTHLY

Measured on the book: **per DATE median 2 names, max 17, and ZERO dates reach 20** — a quintile
sort needs roughly 20. Per WEEK median 7, only 20 weeks reach 20. **Per MONTH median 31, and 89 of
118 months reach 20.** **The cross-section is therefore cut WITHIN CALENDAR MONTH**, and that is a
forced choice disclosed here rather than a preference discovered later.

### §0.5 There is no look-ahead, and it is checked rather than asserted

The banked book's `entry_premium` matches the **alert-day EOD quote** (O10 measured it against the
tape's last prevailing ask at a median relative error of 0.0233, and far closer to the ask than the
mid). So the banked entry is struck at the alert day's close, and **the whole alert-day tape
precedes it**. A control re-measures this before any arm is scored.

### §0.6 What this cache CANNOT do, stated now

The cache is **alert-days only** — the adjacent sessions are not there (O10 measured D+1 cached for
0 of 3,870). **So no tick-derived feature may use a trailing window across days.** Print-level
"unusual size" is computable within the day; **day-level unusual VOLUME is not computable from
ticks** and is taken from the EOD chain cache instead (arm A5), which is disclosed rather than
quietly substituted.

## §1 THE SIGN IS AMBIGUOUS BY THE AUDIT'S OWN ARGUMENT, SO THE TEST IS TWO-SIDED

The audit's literature note is the most important constraint in this register and is quoted:

> *Pan and Poteshman (2006) found that buyer-initiated, open-interest-increasing put-call ratios
> predict next-day returns — but they used proprietary CBOE data with participant identification.
> Bryzgalova et al. (2023) used wholesaler flags to identify retail option flow and found retail is
> over 60% of options volume … and **loses money on average**. So signed retail flow is a **fade**
> candidate, not a follow candidate. Public tick data cannot separate the two populations. Build
> the features, but expect the sign to be ambiguous.*

**Consequence, fixed here: every arm is tested TWO-SIDED.** This project's other registers declare
a published sign first precisely because a study that picks which end to go long after seeing the
numbers wins half the time by construction. **Here no sign CAN be declared** — the same feature is
predicted to point one way if the flow is institutional and the other way if it is retail, and the
data cannot tell them apart. **A two-sided test costs power and that is accepted as the honest
price**; it is not a licence to read whichever tail is larger.

## §2 THE FIVE ARMS — DEFINITIONS FIXED HERE

**Aggressor classification is the standard Lee–Ready rule**, quoted from the audit and specified
completely: `price > mid` → **buy-initiated**; `price < mid` → **sell-initiated**; `price == mid` →
**tick test** against the previous different price in the same contract (higher → buy, lower →
sell, otherwise unclassified and excluded). The quote used is the print's own prevailing
`bid`/`ask`; O10 measured the quote lag at a median 0.0s with only 0.19% over 60s, so this is sound.

**Eligibility:** the single-leg condition codes fixed in session 26 (`tickflow.SINGLE_LEG_CODES`),
imported rather than restated, so package prints are not credited as directional flow.

| arm | feature | source | definition |
|---|---|---|---|
| **A1** | `signed_volume` | ticks | (buy-initiated contracts − sell-initiated contracts) / total classified contracts, over the whole chain that day |
| **A2** | `pc_flow_imbalance` | ticks | Pan–Poteshman in put/call form: buy-initiated **PUT** premium / (buy-initiated put premium + buy-initiated **CALL** premium). High = put buying dominates |
| **A3** | `sweep_share` | ticks | share of classified premium in **sweeps** — prints in the same contract touching **≥3 distinct exchanges within 500 ms** (the audit's *"multiple exchanges within a short window"*) |
| **A4** | `block_share` | ticks | share of classified premium in **blocks** — prints whose size is **≥10×** that contract's own mean print size that day (the audit's *"size relative to the contract's own average"*) |
| **A5** | `unusual_volume` | EOD chain | the traded contract's alert-day volume / its **trailing 20-session median volume**. **Not tick-derived** — §0.6 explains why it cannot be |

**Outcome:** the banked trade's `pnl_pct`. **Sort:** quintiles cut within calendar month (§0.4);
long-short is Q1 − Q5, reported with its sign, and **a two-sided |t| is what is judged**.

## §3 STATISTICS, CALIBRATION AND MULTIPLICITY

* **Clustering:** month-block bootstrap, R3's standing rule, 2,000 draws, seed **20260812**. A
  trade-level *t* is never quoted.
* **Calibrated bar:** each arm's long-short |*t*| is scored against **its own within-month label
  permutation null** — quintile labels permuted inside each month, holding every return and every
  bin size fixed, 2,000 draws. **The bar is that null's p95 of |t|**, two-sided by construction.
* **MULTIPLICITY — the audit requires Benjamini–Hochberg and it is applied across all five arms**
  at **q = 0.10**, on the permutation p-values. **Both the calibrated bar AND BH must pass**; the
  project's calibrated-margin practice and the audit's BH requirement are different instruments and
  neither is dropped in favour of the other.
* **Both halves** at the panel's median month.

**An arm is a CANDIDATE iff, in BOTH halves:** |t| exceeds its own permutation p95, **AND** the
long-short sign agrees between the halves, **AND** the arm survives BH at q = 0.10 on the full
sample. Otherwise **NULL**. Ambiguous against a bar is a NULL (`RUN_RULES` A6).

**The sign-agreement clause is doing real work here.** With a two-sided test and no declared sign,
an arm that is strongly positive in one half and strongly negative in the other would otherwise
clear on |t| twice while carrying no usable information. This project has recorded that exact
pattern — sign flips between halves — more often than any other result.

## §4 DEAD-ENTRY FRAMING — FIXED BEFORE ANY RESULT

**R2 stands: the alert entry loses to random entry by −5.0640pp, and nothing here re-opens it.**
These features are measured **on the alert days**, so a positive arm says *"within a book whose
entry is already known to be bad, this flow feature separates better trades from worse ones."*

* A CANDIDATE is a **candidate for a future book that does not yet exist** — never evidence the
  alert works, never an adoption.
* **Nothing is adopted whatever the result.** No live path, no constant.
* **The most likely misreading is the tradability of a sweep or block feature**: these are
  measured across the whole chain on the alert day, not on a single tradeable instrument, and no
  execution model is attached.

## §5 EXPECTATIONS — WRITTEN DOWN FIRST

| # | expectation | confidence |
|---|---|---|
| E1 | No arm reaches CANDIDATE — the autopsy's record is 0 discoveries in 126 hypotheses, twice | 75/25 |
| E2 | At least one arm clears its own permutation p95 on the FULL sample before BH and both-halves | 60/40 |
| E3 | `pc_flow_imbalance` (A2) has the largest \|t\| of the five | 40/60 |
| E4 | At least one arm flips sign between halves | 70/30 |
| E5 | BH at q=0.10 removes at least one arm that cleared its own bar | 45/55 |
| E6 | `unusual_volume` (A5), the one arm needing no tick data, is not the best arm — i.e. the tick pull bought something | 55/45 |

## §6 TRIAL COST

**5 options trials**, one per arm. Options `N` **280 → 285**. Equity and infra untouched.

Controls — the look-ahead check, the Lee–Ready classification rate, the coverage report and the
BH-versus-calibrated-bar comparison — are charged **zero**; none carries a verdict.

## §7 VOID CONDITIONS

1. Fewer than **40** months carry a full quintile cross-section, or fewer than **2,500** trades
   acquire all four tick-derived features.
2. Any change after an outcome is read to: the five feature definitions, the Lee–Ready rule, the
   sweep or block thresholds, the monthly cut, the two-sided treatment, the seed, the draw count,
   BH's q, or any verdict clause.
3. **Declaring a sign for any arm after seeing its result**, or reporting a one-sided p-value.
4. Adding a sixth arm after seeing the first five.
5. Quoting any arm as an adoption or as evidence about the options ENTRY signal.
6. **Claiming the O-series is closed before the `O14` ledger row actually flips to `DONE`.**
