# `OSAP3` — **the free kill shrinks the batch from three to one, and the survivor is blocked on a Google Drive quota**

**2026-10-19, r1 lane. ZERO TRIALS, `FIXED`-class.** Equity `N` stays **307**. **NO REGISTER WAS
COMMITTED, NO ARM RAN, NO FORWARD RETURN WAS LOADED** — pinned by test. **ADOPTS NOTHING.** No app
file, no live path, no change to the Index or the 2026-10-22 rebalance.

`PREREG_DRAFT_osap3.md` §4 runs its kills "before any arm, in their own pass, zero trials under
`MB1-SEL`". **`K1` ran and it is decisive.**

---

## 1. SCREEN 1 REPRODUCES THE DRAFT EXACTLY, FROM A FILE ALREADY ON DISK

`data/factors/raw/osap_signal_docs.csv`, 331 rows × 29 columns — no download, no licence:

| screen | draft | **measured** |
|---|---|---|
| all rows | 331 | **331** |
| `Cat.Signal == Predictor` | 212 | **212** |
| …and `Stock Weight == VW` | 28 | **28** |
| …and holding period ≥ 3 months | 12 | **12** |

**And the twelve acronyms are the draft's twelve, in the same order of evidence.** `184 of 212
predictors are equal-weighted`, confirmed — **one free column removes 87% of the published catalogue
before a byte is pulled**, which is the draft's strongest argument and it holds.

---

## 2. `K1` — THE BATCH GOES FROM THREE TO ONE, AND THE TWO DROPS ARE DIFFERENT KINDS OF DROP

The bar is the draft's own ≥ 0.70 input coverage, reused verbatim. Measured on
`data/backtest/fundamentals.csv`, **232,469 rows**:

| input | non-null |
|---|---|
| `ppnenet` | 0.999763 |
| `assets` | 0.999695 |
| `equity` | 0.999626 |
| `revenue` | 0.976595 |
| `netinc` | 0.976517 |
| **`roe`** | **0.000000** |
| **`roic`** | **0.000000** |
| **`assetturnover`** | **0.000000** |

**THE COVERAGE RULE'S OWN NAMED EXAMPLE REPRODUCES AT EXACTLY ZERO.** `roe`, `roic` and
`assetturnover` are present in the header and empty in the data, because the licensed export is
ARQ-only and Sharadar fills its ratio columns only in ART/ARY. **This is why `K1` checks non-null
coverage rather than column existence** — and the draft's §8 lists `EquityDuration` as rebuildable
"from book equity, **ROE** and growth", so a naive reading of the header would have built it on an
empty column and produced a clean, plausible, meaningless number. ROE has to be derived from
`netinc / equity`, which the project already does.

| signal | verdict |
|---|---|
| **`EquityDuration`** | **inputs PRESENT at the bar** (worst input 0.9765) |
| **`realestate`** | **DROPS — a CONSTRUCTION blocker, not a coverage shortfall** |
| **`BetaLiquidityPS`** | **DROPS — the factor series is not in this repo** |

**`realestate`'s drop is the one worth stating precisely, because it would otherwise be misread.**
Tuzel's measure is **real-estate PP&E (buildings and land) over total PP&E**. Net PP&E is present at
**99.98%** — so it is not that Sharadar lacks PP&E — but **none of the nine probed component columns
exists**, so the signal cannot be built from this export **at any coverage**. The draft recorded its
mapping as "unverified"; it measures **absent**. **A construction blocker is permanent until a
different source is bought; a coverage shortfall might improve.**

`BetaLiquidityPS` drops on the draft's own §8 wording — the Pástor-Stambaugh factor is "published
free and monthly but **is not in this repo**", so it is a download plus a schedule rather than an
existing column, and **`K1` measures what is present rather than what is obtainable.**

**AND THE SHRINKING BATCH TIGHTENS BENJAMINI-HOCHBERG, WHICH THE DRAFT PRE-COMMITTED BECAUSE THE
INCENTIVE RUNS THE OTHER WAY.** At k = 1 the threshold is **0.10**; keeping two failing signals in
would have left k = 3 and a *looser* per-signal threshold. The draft calls shrinking "the correct
behaviour rather than a reason to keep a failing signal in", and that is what happened. **The three
trials would still all be charged** (§6, `MA6`'s safe direction, and `E-1`'s precedent of keeping a
trial for an arm that never ran) — so the cost of running would be three trials to test **one**
signal.

---

## 3. WHY THE SURVIVOR DID NOT RUN, AND IT IS AN EXTERNAL DATED BLOCKER

The arm scores the **OSAP-provided** signal values (§1: "a register must read the actual signal
values"). Measured today:

* the firm-level file is **a single 1.6 GB zipped wide CSV of all 209 predictors**; the site offers
  **no per-predictor download**, which is why the draft's §7 void condition 2 — *"the pull is 3–5
  columns"* — needed a route in the first place;
* the `openassetpricing` package is the documented per-signal route, and it returns
  **`Google Drive — Quota exceeded: "Too many users have viewed or downloaded this file recently…
  may take up to 24 hours"`.**

**So the values are not obtainable today, by anyone, from the published route.** No register was
committed and no trial was spent — which is the right way round: **committing a register and then
being unable to run it would have burned three trials and raised the hurdle on every future equity
claim for nothing.**

**A DEFECT OF MY OWN, AND IT IS THE MOST USEFUL THING IN THIS FILE.** Installing that package
**silently downgraded pandas to 2.2.3**, because `wrds` pins `pandas<2.3` — and **every banked panel
is a pandas-3 pickle**, so `dipcall.panel_path()` immediately stopped loading with
`TypeError: issubclass() arg 1 must be a class`. The toolchain was restored to **pandas 3.0.6**, the
package removed, and the panel re-read at 289,659 rows. **Two consequences recorded rather than
glossed:** a 325-suite gate that was in flight across the downgrade was **killed and re-run**,
because results measured on a different runtime are contaminated; and **all five of this session's
measurements were taken on pandas 3.0.6, before the install** — checked, not assumed. **The pip
warning that `wrds` wants an older pandas is expected and must never be "fixed".**

---

## 4. WHAT IS NOT DONE

**`K2` (the dated `crsp.stocknames` tier join), `K3` (the costume kill against the seven themes and
`size`), `K4` (ambiguity) and `K5` (composite reproduction) were NOT REACHED** — they only matter for
a signal whose values exist. **`EquityDuration` is UNTESTED, not rejected.** Nothing is claimed about
whether any of the three works.

**The draft's refusal of the brief's own 209-trial design stands and is not revisited** — its hurdle
arithmetic (+0.1501 on every future and existing equity claim, permanently, and a best-signal
requirement of *p* = 0.00048) is unchanged by anything here.

**`S2`, `P5-3`, `R5`, `W-28`, `A1` and `C3` are not re-opened.**

**The next session's first act, if this is picked up:** retry the per-signal fetch once the Drive
quota clears, and if it has not, the honest alternative is a register that scores a
**Sharadar-rebuilt** `EquityDuration` — declared as an amendment **before any outcome** — which then
owes the fidelity gate §8 names and which this session did **not** take, because rebuilding
Dechow-Sloan-Soliman duration by hand is a construction I could get wrong, and a wrong construction
returns a clean plausible null (`MA31`'s family).

**13 tests.** `scripts/osap3_k1.py`; `data/free_analysis/OSAP3_K1.json`.
