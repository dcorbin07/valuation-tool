# W-3b — IBES ACTUALS INTO THE EARNINGS-DATE SPINE
## EXECUTOR'S EXECUTION RECORD. **ACCEPTED WITH TWO AMENDMENTS**, both forced by measurement.

> **THIS FILE IS NOT A PRE-REGISTRATION AND IS DELIBERATELY NOT NAMED `PREREG_`.** It was
> written AFTER the measurement, as the executor's adjudication of the scout's draft. It
> was first committed as `PREREG_w3b_ibes_event_spine.md` and
> `tests/test_ma60_conventions.py` correctly refused it: that suite requires every
> `PREREG_*.md` to have landed in a markdown-only commit, precisely so nobody can claim
> thresholds were fixed first when they were not. Renaming was the honest fix; adding it to
> the grandfather list would have exempted a file that genuinely is not blind. **The
> pre-registration for this item is the scout's `PREREG_DRAFT_w3b_ibes_event_spine.md`,
> which is reproduced unedited and which this file adjudicates.**
>
> A note on how it was caught, because it is a real gap in my own verification: the full
> suite was green locally BEFORE the commit existed, and this check can only bite once
> there is a commit to inspect. **A local run cannot see a commit-shape violation.**
## Zero trials, FIXED / instrument class. Executor: this lane, 2026-08-25.

The scout's draft is `PREREG_DRAFT_w3b_ibes_event_spine.md`, unedited. This file is the
executor's adjudication of it and the record of what was built.

---

## 0. TRIALS: ZERO, AND THE REASON IS STATED RATHER THAN ASSUMED

No hypothesis, no bar on any outcome, no verdict about returns. The V1 agreement gate is an
INSTRUMENT validation, and `MB1-SEL` governs: *a control can only ever BLOCK a finding, never
produce one, so it adds no degree of freedom to any published claim.* Precedent: `I-4` (0),
`I-2`/`I-3` (0), `MB15` (0), `S3-I3` (0).

**The counter-argument, stated because it is not frivolous:** this register CHANGES an instrument
that landed studies read, which is a bigger act than a census. It is still zero, because nothing
here scores an outcome and **no published verdict is re-read** — that prohibition is section 5's
and it is honoured in section 6.

---

## 1. THE DRAFT'S PREMISE HOLDS, AND ITS HEADLINE NUMBER IS EXCEEDED

`I-4` rests on Sharadar EVENTS code 22 and **29 of 186 optionable names carry ZERO coverage**,
every one a foreign private issuer filing 20-F/6-K. Reproduced exactly from the banked census
before anything was built, and the runner **ASSERTS** it — the before/after has to be of one
object, and that assertion is what caught the first defect (section 4).

**IBES recovers 29 of 29. The merged spine reads `COVERED` on all 186 names.** The draft's
expectation (2) was "≥20 of the 29 — 65/35"; it is 29.

**That number is worth less than it looks and section 3 is why.** The first route to reach 29 of
29 was contaminated, and a clean 29-of-29 is exactly the shape `MA31` warns about — a lookup that
computes cleanly and answers a different question.

---

## 2. AMENDMENT 1 — THE DRAFT'S §2 AND ITS §3 V3 ARE MUTUALLY INCONSISTENT, MEASURED

§2 fixes the precedence: *"IBES `anndats` where present; Sharadar code-22 where IBES is absent"*.
§3's V3 requires the merge to *"reproduce bit-identical on the unchanged rows, so the repair is
provably additive"*.

**Both cannot hold, and the gap is large rather than technical:**

| merge rule | total dates | code-22 dates DROPPED | names keeping every original date |
|---|---|---|---|
| §2 precedence (`other`) | 23,639 | **1,708** | **8 of 157** |
| union | 25,347 | **0** | **157 of 157** |

The draft assumed the two sources differ only where one is absent. They differ where both are
present, on 1,309 dates, for the reason in section 5.

**RESOLUTION: the UNION ships as the default merged spine; the precedence spine is built beside
it and both are reported.** Reasons, in order:

1. **V3's additivity is the SAFETY property and §2's precedence is an editorial claim.** No
   landed study's dates can vanish under the union. Under §2, 1,708 dates that landed studies
   used would disappear — the nearest thing to §5's own void condition (*"changing any published
   verdict on the strength of the repair"*), reached by deletion rather than by argument.
2. **The measurement says neither source is simply right.** Code 22's extra dates are real SEC
   Item 2.02 filings, not errors (section 5). Deleting them asserts a judgement the evidence does
   not support.
3. **Nothing is lost either way, because the precedence view is reachable by FILTERING.** Every
   date carries `date_sources` — `code22`, `ibes` or `both` — so a consumer wanting
   earnings-announcements-only takes the `ibes`/`both` subset. A deletion cannot be undone; a
   stamp can always be filtered.

**THE UNION IS ADDITIVE IN DATES AND IS NOT INERT FOR CONSUMERS, and that must travel with it.**
It adds 11,863 dates to names that already had coverage, so `refuse_within` and `owns_the_event`
return different answers on the merged spine than on the code-22 spine. **Every landed result
stands on the code-22 spine and none is re-read here.** The merged spine is a NEW instrument for
future work.

---

## 3. AMENDMENT 2 — THE IDENTIFIER ROUTE IS NOT THE DRAFT'S, AND THE DEPARTURE IS EVIDENCED

§2 says the dates are *"joined to the panel through `ibcrsphist`"*. Three traps were measured,
each of which the obvious route walks into:

* **`oftic` IS A LEASE.** Matching on IBES's official-ticker column reaches 29 of 29 and is
  contaminated: `SPOT` carries PANAMSAT CORP 1996-2004 beside SPOTIFY TECH, `RIO` carries ROYAL
  INTL OPTIC and VALE beside RIO TINTO, `ARM` carries ARMSTRONG RUB, ARM FINL GROUP and
  ARVINMERITOR. **Across the 29, 17.7% of the rows `oftic` offers are a different company.**
  `S3-I5`'s ticker reuse in a third table.
* **ESCAPING REUSE NEEDS A DATE, NOT A DIFFERENT COLUMN.** The first CUSIP fix collected every
  cusip CRSP ever tied to a ticker and re-imported the same contamination through another door —
  it returned MORE rows for TTE, SONY and BHP than the naive route did. Restricting instead to
  the CURRENT cusip committed the OPPOSITE error and truncated continuing histories: **HWM
  unmatched on 82.9% of its code-22 dates, MRVL 80.6%, STX 79.8%, GE 79.3%.**
* **IBES MASKS CUSIP CHARACTERS WITH `X` AND AN EXACT MATCH FAILS SILENTLY.** IBES writes
  `0636711X` where CRSP writes `06367110`. Zero rows returned is indistinguishable from "not
  covered", and it hit **BMO, CNQ and TD** — three of the very issuers this item exists to
  recover. Masking is **1.64% of rows**, in positions 6 and 8.

**Built instead:** CRSP `stocknames` **dated intervals** against IBES's cusip with a
**positional** `X` wildcard. Positional, not a prefix: `0028931X` matches `00289310` while
`00108281` (BOS BETTER ONLINE) still does not match `00108282` (TECHNOPRISES) — **328 seven-
character prefixes in this file are shared by more than one distinct cusip.**

**THE DRAFT'S ROUTE WAS THEN RUN AS A CONTROL, AND IT AGREES.** Scoped the same way,
`ibcrsphist` recovers the same 29 of 29 and **97.38% of the same dates**. So the departure is
**immaterial to the result** and is recorded as a preference with evidence, not a correction to
the scout. Two notes for anyone who prefers the draft's route: `ibcrsphist` carries **7,337 of
37,662 rows with a NULL permno**, and run WITHOUT date scoping it returns 6,189 extra dates with
only 11 of 186 names matching — **the difference between the two routes is dominated by whether
you scope, not by which identifier you scope.**

---

## 4. V1 FAILS AT 86.18% AGAINST A 95% BAR, AND THE DISAGREEMENT IS THE DELIVERABLE

The draft: *"the two dates agree within ±1 session on ≥95% of pairs. **The disagreement set is
the deliverable either way**."* Honoured as written — the bar is not moved.

**11,621 of 13,484 code-22 dates sit within ±3 calendar days of an IBES date = 86.18%.** Tolerance
is stated in calendar days because one session spans up to three of them across a weekend; the
looser reading is used so Fridays do not manufacture disagreements.

**The residual is split, because a bare rate cannot distinguish two causes that imply opposite
actions:**

| | count | share |
|---|---|---|
| COVERAGE GAP — IBES has nothing that year, so there was never a counterpart | **554** | 29.7% |
| REAL CONFLICT — IBES has dates that year and none is near ours | **1,309** | 70.3% |

Excluding coverage-gap years the rate is **89.88%**. Still short of 95.

**INTERVAL SCOPING ALONE MOVED IT 81.03% → 86.18%**, which is the measured value of Amendment 2.

---

## 5. THE FINDING: CODE 22 IS BROADER THAN "EARNINGS", AND THE SPINE HAS ALWAYS SAID OTHERWISE

SEC Item 2.02 is *"Results of Operations and Financial Condition"* — which issuers also file for
monthly sales, preliminary results and guidance revisions. `I-4` treats every code-22 date as an
earnings announcement.

**Measured across 3,097 name-years where both sources have data:**

| | share |
|---|---|
| code 22 has MORE dates than IBES | **23.3%** |
| equal | 71.3% |
| code 22 has FEWER | 5.4% |

**Per name, the split is stark and it is not noise:** PNC **7.67** code-22 dates a year against
IBES's 4.00; NKE **6.20**; XOM **5.53**; ROST **8 a year until 2013**, then 4 — the signature of a
retailer that published monthly sales and stopped. Against that, MSFT, JPM and AAPL read **exactly
4.00 against 4.00**.

**The clean individual case is AAPL `2019-01-02`** — Apple's revenue-guidance letter. A genuine
Item 2.02 filing, a genuine information event, and **not a quarterly earnings announcement**.
`owns_the_event` has been answering "owns the next Item 2.02 filing".

**WHAT THIS DOES AND DOES NOT SAY.** It does NOT say any landed number is wrong: those figures are
correct for the dates they were computed on. It says the dates mean *"results filing"* rather than
*"earnings announcement"*, and the two differ for about a quarter of name-years. **No verdict is
re-read here and §5's void condition forbids it** — a re-read is a new register with its own
charge.

**THE ONE EXPOSURE WORTH NAMING, because it runs in a direction a reader should know:** `EVOWN`'s
central measurement is that a DTE-matched control is **61.9% spanning** because announcements
arrive every ~63 trading days. On earnings-only dates the cadence is slightly sparser (IBES 3.85
per name-year against code 22's 4.17), so that spanning share would move **DOWN** — i.e. toward
the alert arm looking slightly better. **UNMEASURED, NOT RUN, and named so nobody discovers it as
a surprise.**

---

## 6. WHAT WAS BUILT, AND THE DEFECT THAT NEARLY MADE IT LOOK PERFECT

`valuation/edge/ibes_events.py` (the second source), `EventSpine.merge_source` (three precedence
rules, per-date source stamps), `scripts/w3b_ibes_spine.py` (the runner),
`data/free_analysis/W3B_IBES_SPINE.json`.

**A DEFECT IN MY OWN RUN, CAUGHT BY THE ASSERTION WRITTEN TO CATCH IT.** `event_spine`'s default
events path resolves relative to the module, which inside a git worktree lands on an **EMPTY**
`data/bulk/`. The build succeeded, returned zero dates, and **all 186 names read FAIL_CLOSED** — a
clean, plausible "coverage is nil" against which IBES would have appeared to recover *every* name
from nothing. `DEEPITM-FIN`'s existence-is-not-population defect. The runner now resolves the
primary root and **refuses** if the file is absent.

**A DEFECT IN MY OWN MERGE, and it is `S3-I1`'s `columns=` regression in a second place.**
`merge_source` validated `precedence`, stored it on the result, and then **took the union
regardless** — a caller asking for either rule got neither. It was invisible while the union was
the intended default and would have surfaced as a wrong spine the first time anyone asked for
precedence. Three named values now, with `union` spelled out rather than being what you get by
accident.

**19 tests; 7 of 7 mutations caught with sources restored byte-for-byte**, including the X-mask
being dropped, the mask loosened to a prefix, interval scoping removed, and the ignored-parameter
defect itself.

---

## 7. NOT DONE, named so it is not mistaken for done

**No consumer is repointed.** `EVOWN`, `O17C4`, `O6`/`O7`/`O17`, `F-4`/`F-12`/`F-13` all still
read the code-22 spine and every landed figure stands on it. **No verdict is re-read.** The
merged spine is not written into `I-4`'s artifact — it is a separate table with its own file, so
adopting it is a deliberate act by whoever needs it. **The 5.4% of name-years where IBES has MORE
dates than code 22 is not diagnosed.** **`anntims` is loaded and unused** — an announcement's
time-of-day decides whether the market can react that session or the next, and using it is a
construction change with its own register. **The scout's expectation (3)** — that the disagreement
set contains a date our studies used and IBES contradicts — is **RIGHT, 1,309 times**, and (4)
holds: no published verdict needs revision, because none is re-read.

**Expectations: (1) V1 ≥95% — WRONG (86.18%). (2) ≥20 of 29 recovered — RIGHT (29). (3) the
disagreement set is non-empty — RIGHT. (4) no verdict needs revision — RIGHT.**
