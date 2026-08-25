# O-1 COVERAGE PULL — COLLECTION RECORD
## Targeted entry chains for `MA28`'s flagged panel rows. **ZERO TRIALS.** 2026-08-25.

**Collection only: no analysis, no selection, no verdict.** Nothing here computes a return, picks
a contract, or compares an arm to a control. The freeze is **NEW** —
`D:\thetadata\freeze_o1_coverage_2026-08-25` — and no existing freeze was mutated.

---

## 1. THE HEADLINE, AND IT IS KNOWABLE FROM COVERAGE RATHER THAN AFTER SCORING

**The pull raises `O-1`'s flagged coverage from 74 names to 2,969 usable cells, and that is
0.82× its own registered floor.**

| | |
|---|---|
| `O-1`'s floor (its section 6) | **3,600 matched flagged trades, ≥1,200 per half** |
| flagged cells with a put in the registered PRIMARY band | **2,969** |
| ratio to floor | **0.82×** |
| early / late halves at the median date 2020-07-22 | **1,467 / 1,502** — both clear the 1,200 sub-floor |

**MATCHING CAN ONLY REDUCE 2,969**, because `O-1` section 5 drops an unmatched flagged cell and
counts it. So **the aggregate floor is not reachable at the primary tenor even from a complete
pull of everything the vendor holds**, while the half-split constraint *is* satisfiable — it is
the total that binds, not the balance.

**This is a coverage fact, not a verdict.** It says what the data can support; whether `O-1` is
re-registered at a different design, re-run and reported UNDERPOWERED as its own section 6
already provides for, or left alone, is that register's business and not this pull's.

**AND IT IS NOT A TENOR TO GO SHOPPING FOR.** Only the two REGISTERED bands are reported below.
Sweeping tenors until one clears the floor is choosing the design on the data — the exact defect
`O-1` caught and refused to commit, and the one this pull was told not to repeat. A different
band needs a new register.

---

## 2. WHAT WAS MEASURED BEFORE COMMITTING

The harvest's own discipline: a 3-name sample once missed by **+339%**; a 393-pair measurement
landed within **7.4%**.

### The vendor's history starts 2012-07-17, and 1,311 flagged rows are unobtainable at any price

Measured on the panel's **own 69 rebalance dates**, so the question of what is a trading day does
not arise. **55 of 69 carry data**; the 14 that do not are a contiguous
**2009-01-15 … 2012-04-17** prefix — which is what a history edge looks like, as against the
scatter a holiday produces.

| | |
|---|---|
| `MA28` 2-of-3 flagged panel rows | **6,542** (5.74% of 113,945) |
| of those, on or after 2012-07-17 | **5,231** |
| **unobtainable — before the vendor's history** | **1,311 = 20.0%** |

**Those 1,311 are recorded as not-obtainable, never as a pull that fell short.**

### A DEFECT IN MY OWN FIRST PROBE: six years read EMPTY because they were MLK DAY

The first history probe used a fixed mid-January date per year and returned EMPTY for 2010, 2012,
2016, 2017, 2021 and 2023. **Every one is the third Monday in January — the market is closed.** A
holiday is not a coverage boundary, and reading it as one would have truncated this pull by seven
years for nothing. Re-probing on the panel's own dates removed the question entirely.

### Sizing, and it was OPTIMISTIC by ~8 points

Stage 1 was sized on **30 real flagged cells stratified across five market-cap strata** — not on
megacaps, because `O-1`'s universe is accounting-flagged names that skew small and AAPL is the
least representative name in it.

| | sized | measured on 5,231 cells |
|---|---|---|
| cells empty at the vendor | 13% | **17.5%** |
| of cells WITH data, share carrying a primary-band put | 77% | **68.8%** |
| seconds per call | 0.31 | ~0.52 |

**The sample was optimistic on both, and the direction is the one that matters** — a sizing pass
that flatters coverage is how a pull gets committed to and then falls short. 30 cells is a small
sample and this is the third time in this project that sampling has erred in the generous
direction.

---

## 3. WHAT WAS PULLED

`scripts/o1_coverage_pull.py`, one unit = one **(arm, symbol, panel-date)** entry chain.

| | flagged | control |
|---|---|---|
| cells attempted | **5,231** | **13,840** |
| vendor returned data | 4,317 = 82.5% | 11,454 = 82.8% |
| empty at vendor | 914 = 17.5% | 2,386 = 17.2% |
| ≥1 put @ **150–210 DTE** (PRIMARY) | **2,969** | **7,491** |
| ≥1 put @ **330–400 DTE** (SECONDARY) | 771 = 14.7% | 1,401 = 10.1% |
| both bands | 515 | 958 |

**19,071 units, 15,771 payload files, 1.13 GB.** Freeze verified with `--full-hash`:
**0 missing, 0 wrong size, 0 wrong hash**, and pinned in `FREEZE.json` by a sha256 over the
manifest plus a per-unit sha256, so a later reader can prove both that nothing was added and
that nothing was altered.

**The control pool is 2.5× the flagged arm at the primary band (7,491 against 2,969)**, so
matching is not pool-limited — which matters, because it means the 0.82× shortfall is a property
of the flagged side and cannot be fixed by pulling more controls.

**THE SECONDARY TENOR IS THIN AND THAT IS A COLLECTION FACT WORTH CARRYING: 771 cells against
the primary's 2,969.** `O-1` already declares the secondary as carrying **no verdict power**;
this says it could not carry one on availability either.

**Whole chains are stored — both rights, every strike, every expiry to 1200 DTE.** The pull does
NOT filter to puts or to a moneyness band, because filtering at collection time bakes a selection
rule into the data and would force a re-pull if the rule moved — and **the vendor window closes
2026-09-01, so there is no second chance.** Pinned by an AST test that the payload written is the
unfiltered frame.

**Control candidates are 3 nearest-market-cap unflagged cells within the same date**, not one.
The register's matcher chooses; pre-selecting a single control here would make the collection
depend on a matching rule this script has no business fixing.

---

## 4. WHAT WAS DELIBERATELY NOT PULLED, AND WHY IT IS NOT A SHORTFALL

**STAGE 2 — the exit PATH of a held contract — IS NOT PULLED.** Sized on 23 real spans at
**53.6 s/span**, projecting **~78 h for the flagged arm alone and ~156 h with a control**. That
is outside a 7-day window with no margin, and the instruction was explicit: take the
highest-value stratum first rather than start a sweep that ends half-done.

**Stage 1 is that stratum.** It is the index without which no trade can even be *defined*, and a
**hold-to-expiry** settlement needs only the entry chain plus the underlying's close at expiry —
which this project already owns in `data/bulk/prepared/bars`. **A stop-or-target exit rule needs
stage 2 and is recorded here as NOT COVERED.**

The span timings also carry a warning for whoever runs stage 2: **3 of 23 sampled spans returned
0 rows after 154 s**, which is the call-timeout ceiling rather than an absence, so the true
per-span cost is bimodal and a naive mean understates the tail.

**Also not done:** the 45–75 DTE band is not pulled as an arm (`O-1` section 7 void condition 3);
no contract is selected; no return is computed; no arm is scored; `O-1`'s ledger row is not
changed and its verdict is untouched.

---

## 5. DISCIPLINE

* **Resume by unit.** A unit recorded `ok` or `empty_vendor` is not re-pulled; a `fault` is.
  Those are three states, not two — "no chain existed" is a fact about the vendor and "the call
  broke" is a unit to retry, and collapsing them loses 914 real absences into noise.
* **Payload written atomically BEFORE its fsynced manifest line.** A crash between the two costs
  one re-pulled unit and can never leave a half-written file the manifest calls complete.
* **A torn final manifest line costs that unit, not the file.**
* **`_replace_retry`** for the Windows scanner race — the fourth writer in this project to need
  it. It RAISES rather than skipping: a skipped unit is a silent hole in a pull whose whole point
  is completeness. *(Its test's first cut passed against a mutant that skipped, because it
  asserted an error `os.replace` raises anyway. Found by mutation, not by reading.)*
* **New freeze, not a mutation of an existing one**, pinned by test.
* Raw payload on **`D:` only**; nothing licensed in the checkout.

**18 tests; 10 of 10 mutations caught with sources restored byte-for-byte**, including a tenor
silently swapped to the 45–75 band `E-5` refutes, chains truncated below the declared secondary
tenor, the payload filtered to puts at collection time, and the vendor start reverting to the
handoff's assumed 2016.

### THE RESUME DESIGN EARNED ITS KEEP, AND MY FIRST DIAGNOSIS OF WHY WAS WRONG

The control run stopped at **7,400 of 13,840** and wrote nothing for 57 minutes. I diagnosed a
**dead vendor channel** — the failure this project has recorded in the ThetaData miner and that I
had fixed in the WRDS puller the same day — and was about to add reconnection logic.

**The evidence refuted it.** The output file ends cleanly at 7,400 with **no traceback and no
fault records**, and the process was **not in the process table** while two other lanes' jobs
were. It was not hung: it was **killed**. The cause is mine and has nothing to do with the
vendor — I launched it with a shell `&` inside a tool call, which is not a durable background job
in this harness, so it died when its parent call returned.

**Recorded because the near-miss is the useful part: I nearly hardened a component against a
fault it never suffered, on the strength of a symptom that fits two very different causes.** A
stalled log looks identical from the outside whether the remote end died or the local process
did, and the process table settles it in one command.

**Nothing was lost, which is the whole point of the unit-level resume**: the relaunch computed
6,433 units remaining, skipped the 7,407 already recorded, and continued. A pull whose recovery
depends on nothing going wrong is not a design.

**A DEFECT IN MY OWN TEST, the seventh instance of one family:** the selection guard banned the
SUBSTRING `moneyness` and fired against the correct tree, because the module docstring says the
pull does *not* filter to a moneyness band. Prose documenting a rule quotes what the rule
forbids. It reads identifiers from the AST now, with a positive control proving it still catches
a real selection and a negative one proving it ignores prose.
