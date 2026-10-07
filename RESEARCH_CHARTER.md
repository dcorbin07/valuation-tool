# RESEARCH CHARTER — binding on every future register

**Adopted from Don's ruling of 2026-10-03. Supersedes nothing in `RUN_RULES.md`; adds to it.
Every register committed after this file exists must satisfy all seven clauses or be withdrawn.**

---

## 1. THE ONE METRIC

**The net-of-trading-cost return of a book the live scan can actually build, held in a Roth,
against SPY, out of sample.** Not gross. Not against the equal-weighted universe. Not a book the
scan cannot produce.

Everything else — theme IC, long-short spread, monotonicity, Sharpe, PBO, Deflated Sharpe — is a
**diagnostic**. A diagnostic may block a claim and may never establish one.

**Why the wrapper is in the metric, measured:** `INDEX-BOOK` priced the served book at Roth
**17.1619%/yr** against taxable **12.2033%/yr**, a tax cost of **4.9586pp/yr** that puts the
taxable book **3.03pp BELOW SPY**. The product is only a product inside a Roth.

## 2. EVERY NUMBER NAMES ITS BOOK

**No figure reaches the site, a resume, a conversation or a commit message without naming the
exact book it was measured on** — universe, cap tier, weighting, breadth, band, rebalance rule,
costs charged, tax treatment, and the benchmark.

This clause exists because the site quoted **+32%/yr gross** for a "roth top-25" and the
full-universe decile's figures as though they described the product, and `INDEX-BOOK` then
measured the served $10B book at **+1.9488pp/yr vs SPY net** — and **+0.2702pp in the recent
half**. Both of `INDEX-BOOK`'s alpha sentences are true (**−0.0576pp** vs the all-cap equal-weighted
universe, **+4.1209pp** vs its own tier) and **neither may travel alone.**

## 3. PRE-REGISTRATION

Unchanged from `RUN_RULES`, restated because it is load-bearing: the register is committed
**ALONE**, markdown only, zero `.py`, as a strict git ancestor of every commit that computes an
outcome. It fixes the arms, the bar, the kills and the void conditions **before** the instrument
exists.

## 4. BOTH HALVES **AND** LOCKED HOLDOUTS — *amended by Don's Addition 2, 2026-10-03*

**ADDITION 2 SUPERSEDES THE SINGLE-HOLDOUT RULE BELOW. The structure is now:**

**(a) THE CURRENT MODEL, FROZEN.** Tested **ONCE** on **US ~1972–1989** and **ONCE** on
**1990–2008** — **two eras, each read once** — plus the forward track. **S&P 500 total return is
the benchmark before SPY existed**; SPY began trading in 1993, so no era before it may quote a
backfilled SPY.

**(b) NEW RESEARCH** is built on **2009–2019 × a fixed half of tickers**, checked **once** on
**2020–2026 × the other half**, and survivors get **one final check on the pre-2009 eras**.

The ticker half is the **stable key `X1` already used and published** — `sha1(ticker) % 2`,
**1266 / 1265**, no seed, reproducible by anyone holding the ticker list. **`X1` is the record's
strongest positive result** (200 of 200 half-books positive, median half-book alpha +0.07233 against
the full universe's +0.07174, minimum +0.04382), which is what makes a ticker split a sound
partition rather than a convenience: halving the universe moved the centre not at all.

**The 2×2 is a BUDGET, not a menu.** Four cells exist; a construction may consume **one** build
cell and **one** check cell. Looking at the check cell to choose among constructions spends it, and
there is no replacement. The pre-2009 eras are the **third and final** look and they are spent in
era order.

**WHAT THE 2026-10-06 RULING CHANGED HERE, AND WHAT IT DID NOT.** With no cap on tests, the
**BUILD** cell is **deliberately reused** — every Stage-1 arm looks there, which is the whole
point of a cheap screen — and **that reuse is precisely why Benjamini-Hochberg is mandatory on a
batch** (§5). The **CHECK** cell is **not** reused: it stays one read per construction, and so do
the pre-2009 eras. **So "unlimited arms" means unlimited looks at the BUILD quadrant and nothing
else.** Reading the two sections as contradictory is the one misreading to avoid.

### 4b. TWO QUESTIONS, TWO DESIGNS — *and since 2026-10-06 this is the MECHANISM for new signals, not a way to afford a cap*

> **The cap this section was written to make affordable is GONE (§5, Don's ruling 2026-10-06).**
> The section is **not** obsolete — it is now load-bearing for a different reason. With no cap,
> the binding constraint on a Stage-1 batch is no longer how many arms you may spend but **which
> space you spend them in**, and the table below is the measurement that decides it.

`SEARCH_DOCTRINE.md` §1.4 measures the spaces this project can search, and its finding governs how
an arm should be designed:

| space | effective n | 80%-power MDE |
|---|---|---|
| equity panel cross-section | 69 → **58.65** | **0.4274–0.5071 SD** |
| **event time on the same panel** | **100s–1,000s** | **1.66pp at n_eff 400** |
| forward fleet | unbounded in time | ~60 paired fills ≈ 1–2 months |

Its own conclusion: *"On the 69-date cross-section, the 80%-power MDE is approximately equal to the
largest effect the panel has ever contained. That space can essentially only detect signals as
strong as the best signal already in it. A merely good new signal is invisible there BY
CONSTRUCTION"* — **and 245 of the equity trials were spent in exactly that space.**

**So every register must now separate two questions and design for each:**

1. **IS THE SIGNAL REAL?** Answer it in **event time** where the MDE is an order of magnitude
   smaller. Cheap, powerful, and it establishes existence.
2. **IS THE BOOK WORTH HOLDING?** Answer it with charter clause 1 — net-of-cost return vs SPY.
   This is the **weak** space: at the book's ~11.401 pp/yr tracking error a 2pp/yr edge needs
   roughly **30 years** for *t* = 2. **It is the product question and it cannot be made powerful**,
   which is precisely why the pre-2009 eras (1972–1989 and 1990–2008, ~37 years) exist.

**A register that answers only (1) has found a signal and not a product. A register that answers
only (2) will almost certainly return a null that means nothing.** Both, or say which is missing.

---

## 4-OLD. BOTH HALVES **AND** A LOCKED HOLDOUT — *retained as the record of the pre-Addition-2 rule*

Three layers, and the third is new:

1. **Decide half / measure half**, boundary embargoed, as every register already does.
2. **Both halves must clear.** A result that clears one half is `NOT_REPLICATED` and may not be
   quoted as a finding.
3. **A LOCKED HOLDOUT THAT NOBODY LOOKS AT UNTIL A CONSTRUCTION IS FROZEN.** The holdout is
   **pre-2009 US** (`PREREG_DRAFT_oos1_pre2009_holdout.md`). It is opened **once**, for a
   construction that is already frozen and already published, and **a look is irreversible**: the
   date of the look and the construction's hash are recorded before the result is read.
   **Opening it to choose between constructions destroys it**, and there is no second one.

**Why layer 3 is necessary:** the record's own count is that nearly every figure was tuned and
measured on the **same 2009–2026 panel**. The only things presently out of sample are **`X8`'s
international replication** (Japan +2.05%/yr *t* 3.85, developed Europe +3.36%/yr *t* 4.30, with
the **USA the weakest region tested**) and a **two-month forward track**. That is not enough to
support a product claim.

## 5. NO CAP ON TESTS — THE THREE-STAGE PROTOCOL — *Don's ruling, 2026-10-06*

**THE TWELVE-ARM CAP IS REMOVED.** Test everything that makes sense. Fluke risk is controlled by
**counting** every test, by **Benjamini-Hochberg** across a batch, by the **both-halves** rule, by
**blind registers committed ALONE**, by **placebo-calibrated bars**, and by **staged
confirmation** — **never by declining to run a test. "It might be luck" is a reason to confirm,
not a reason not to test.** `DECISIONS.md`, 2026-10-06; that file overrides any older prose here.

**NOTHING ELSE IN THIS CHARTER RELAXES.** §3 (pre-registration), §4 (both halves and the locked
holdouts), §6 (no uncalibrated bar, no borrowed standard error) and §7 (a null is a result) are
unchanged, and the ruling says so explicitly.

**§4(b)'s 2×2 IS THE MECHANISM FOR NEW SIGNALS, and the three stages are how it is spent.**

### Stage 1 — SCREEN. Unlimited arms.

Every candidate is scored on the **BUILD quadrant only**: **2009–2019 × the fixed ticker half**
(`X1`'s `sha1(ticker) % 2`).

* **THE PANEL IS THE CORRECTED FULL RAW UNIVERSE** — the one `UNIVERSE-BIAS` built from the
  **2026-10 freeze** (`data/free_analysis/UNIVERSE_BIAS_PANEL_full.pkl`, exported by
  `scripts/universe_bias_prep.py` from `data/backtest_freeze_2026-10/raw`). **NEVER
  `data/backtest`**, and the reason is measured rather than stylistic:
  `sharadar_freeze._fresh_universe` ranks the **TICKERS snapshot by TODAY's `scalemarketcap`** and
  keeps the top 3,000, so that directory is *the names that are biggest in 2026* — selection on a
  present-day property. `UNIVERSE-BIAS` measured what it costs: the wider-pool advantage
  **reverses sign, +7.24pp to −4.14pp**, on the correction alone.
* **EVERY ARM IS BOOKED IN THE RESEARCH LOG.** That is what keeps the Harvey-Liu-Zhu hurdle and
  the Deflated Sharpe counting it. Removing the cap removes a *budget*, not the *counter*.
  **Derive the hurdle, never quote it** — `statistics.hlz_hurdle`. For scale only, and already
  stale by the time anyone reads it: equity `N` was **262** at the committed stamp, hurdle
  **3.3371678**.
* **A BATCH IS JUDGED WITH BENJAMINI-HOCHBERG AT q = 0.10 ACROSS THE BATCH.** The batch's
  membership is fixed **in the register, before any arm runs** — choosing afterwards which arms
  were "in the batch" is how BH is gamed. For a batch of *k*, the *i*-th smallest *p* is compared
  against *i* · 0.10 / *k*: at *k* = 11 the smallest must beat **0.00909** and the largest
  **0.10**. **BH controls the false-discovery rate across the batch; it is not a licence to
  present a survivor as confirmed** — that is Stage 2's job.
  * **BH NEEDS p-VALUES, AND THIS PROJECT'S BARS ARE MOSTLY MARGINS.** Where an arm's statistic
    has no calibrated *p*, it is judged by its own pre-committed margin and is **excluded from
    the BH set with that exclusion declared in the register** — §6 forbids inventing a *p* to
    make a method apply. `R1-VAR` is the precedent: a *detection* threshold used as a
    *preference* threshold is a category error, and so is a margin dressed as a *p*.
* **UNIVERSE FILTERS MUST BE RELATIVE (percentiles), NEVER ABSOLUTE RANKS.**
  `INDEX-CHOICE-ARM4`'s portable rule, measured: *"a universe filter expressed as an ABSOLUTE
  RANK is not invariant to subsampling the universe, so `X1`'s name-split method cannot evaluate
  one."* A top decile scales with the population; a top-1,500 does not, and on a half universe it
  silently becomes a different filter.
* **THE BOTH-HALVES RULE APPLIES INSIDE THE BUILD QUADRANT** — 2009–2014 / 2015–2019, boundary
  embargoed. An arm clearing one half is `NOT_REPLICATED` and does not reach Stage 2.

### Stage 2 — CONFIRM. Rationed.

Only Stage-1 survivors, **with the bar fixed in the register before the look**, get **ONE** read
of the **CHECK quadrant**: **2020–2026 × the other ticker half**. **Each read is logged, and a
construction gets one.** Looking in order to choose among constructions spends it, and there is
no replacement.

### Stage 3 — HOLDOUTS AND FORWARD.

Survivors get **one read of the 1999–2008 five-theme proxy** and a **forward paper book** on the
`S3-I1` fleet harness.

* **THE PROXY IS FIVE THEMES AND THAT IS STRUCTURAL, NOT A CHOICE.** `institutional` has **no
  pre-2009 source at all** (SF3 starts **2013-06-30**) and `insider` reaches only **0.307 by
  2008** against the 70% rule (SF2 starts 2008-01-02). `PANEL-EXT-CENSUS` — committed ALONE at
  `5cff93a`, 2026-09-30 — **failed all three candidate start years, 1995, 1999 and 2000**, and
  `PANEL-EXT-RECHECK` confirmed the 2026-10 renewal **extended the recent end, not the far end**,
  so both structural kills survive.
* **SO THE PROXY MAY TEST A NEW SIGNAL'S INCREMENT AND MAY NOT VALIDATE THE SHIPPED
  CONSTRUCTION.** A 1999–2008 panel scores a FIVE-theme composite against a SEVEN-theme published
  figure — in the census's own words *"not an extension of the published figure"* but *"a
  different composite wearing the same name."* **Five-theme-WITH against five-theme-WITHOUT on the
  same panel is a sound paired question; five-theme-against-the-published-seven is not.** Any
  Stage-3 result carries that sentence.
* **DISCLOSED, AS THE RULING REQUIRES: `POOL-SIZE` HAS ALREADY READ THIS PROXY ONCE**, for pool
  width — labelled in its own memo *"A LABELLED PROXY FOR POOL WIDTH, NOT A TEST OF THE SHIPPED
  COMPOSITE"*, five themes, **11,052 names, 39 quarterly dates, 1998-12-31 → 2008-07-10**, built
  with the shipped panel builder from the freeze's **full raw** SEP/SF1/SFP and **not** from
  `data/backtest`. A new-signal increment is a **different question on the same data**, which is a
  real cost and is recorded rather than waved past.
* **THE 1972–1998 WRDS ERA STAYS CLOSED** until `OOS1`'s Gate B clears its pre-committed **0.90**.
  It reads **0.837303** today (`value` 0.783 against `momentum` 0.984), so the era is **not
  opened**, and `W-28`'s rule forbids relaxing that bar after watching it fail.

### ADOPTION

Anything that passes all three stages goes to **Don** as a candidate for the next rebalance, with
its **expected return quoted at HALF its backtested size** (McLean-Pontiff). **Nothing is adopted
by a lane. Adoption is Don's and is a vintage event**, which resets the forward clock — §4's
budget is spent in days, and a vintage in five-year units.

### WHAT THE CAP WAS ADMITTING, KEPT BECAUSE IT IS STILL TRUE

The cap existed because **252 arms had produced one measured product result of +1.95pp/yr vs SPY
and +0.27pp in the recent half.** Removing the cap does not refute that; it answers it
differently. **More arms on the same panel still buy hurdle rather than knowledge** — which is
why Stage 1 is deliberately the *cheap* stage and why §4b's instruction stands: answer *"is the
signal real?"* in **event time**, where the 80%-power MDE is **1.66pp at n_eff 400** instead of
**0.4274–0.5071 SD** on a 69-date cross-section that *"can essentially only detect signals as
strong as the best signal already in it."* **The cap's replacement is not more cross-sectional
arms; it is arms designed in the powerful space and confirmed in stages.**

## 6. NO UNCALIBRATED BAR, AND NO BORROWED STANDARD ERROR

Any bar must be either (a) **calibrated** on this panel by placebo, or (b) **pre-committed and
labelled UNCALIBRATED**. `X7` calibrates **LEVELS**; `V2G` established and `R1-VAR` re-confirmed
that **no calibrated floor exists for a paired within-panel difference**. Current calibrated
floors, re-derived at `N` = 247 by `W-1`: long-short naive **2.070231**, long-short HAC
**2.056680**, top-decile alpha HAC **1.826210**, theme IC **2.7072**, PBO p5 **19.667%**.

Every register states its **80%-power MDE** from **its own measured** paired HAC SE — `MB8`
forbids borrowing one across perturbation sizes — before the verdict is read, not after.

## 7. A NULL IS A RESULT AND A FREE KILL IS BETTER

Every register carries at least one **free pre-outcome kill** that can close it at **zero trials**.
`MB15`, `W-14`, `DC-1` and `W-28` all closed questions for nothing, and `DC-1`'s own words stand
as the rule: a kill that fires *"is the cheapest good outcome available to it."*

A null is reported **with its MDE** or not at all — `NULL` means *"nothing this design could
see"*, never *"no effect"*.

---

## WHAT THIS CHARTER FORBIDS OUTRIGHT

* Quoting a gross figure as a product figure.
* Quoting a long-short figure as a product figure — the product is **long-only**.
* Quoting a figure measured on the all-cap universe as a figure about the served tier, or the
  reverse.
* Opening the locked holdout to choose between constructions.
* Relaxing a pre-committed bar after seeing it fail (`W-28`'s closing rule).
* Adopting on a Sharpe or volatility gain bought with alpha, unless the Sharpe is itself bad —
  Don's `R1-VAR` ruling, and at Sharpe **1.0318** on the served book the antecedent does not fire.
* Any adoption without Don's decision: an adoption is a **vintage event** that discards the
  accrued forward clock, and Rule 6 prices that at nothing statistically. Derive the vintage from
  `track_meter.VINTAGES`; never quote one.
