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

### 4b. TWO QUESTIONS, TWO DESIGNS — the correction that makes the cap affordable

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

## 5. A CAP ON ARMS

**The program may spend at most TWELVE further equity arms before a construction is frozen and
the holdout is opened.** Equity `N` is **252** today and the Harvey-Liu-Zhu hurdle
**3.3254862** — derived, never quoted — and it only ever rises. Twelve arms take the hurdle to
about 3.33.

The cap is not budgeting; it is the admission that **252 arms produced one measured product
result of +1.95pp/yr vs SPY and +0.27pp in the recent half.** More arms on the same panel buy
hurdle, not knowledge. **When the twelve are spent, the answer is whatever the holdout says.**

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
