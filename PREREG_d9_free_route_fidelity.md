# PRE-REGISTRATION — `D9`: FREE-DATA ROUTE FIDELITY FOR THE OCT 22 REBALANCE

**Committed ALONE, markdown only, zero `.py`, before any cross-vendor number exists.**

**ZERO TRIALS.** `MB1-SEL`: a fidelity control can only ever BLOCK, never produce a finding, so
it adds no degree of freedom to any published claim. Equity `N` stays **248**
(`sqrt(2 ln 248)` = 3.3206712412296953), options **310**, infra **20**.

**ADOPTS NOTHING.** The bound track, `PAPER_TRACK_CONTRACT.md` and the live service are not
touched. A NO-GO routes a fallback to Don; it does not take one.

---

## 0. THE DECISION THIS SERVES

Don decided 2026-09-30 that the Oct 22 rebalance and every one after is built from the **FREE
LIVE PATH** (broker + free fundamentals; SEC 13F / Form 4 via the MC1 theme cache), not Sharadar,
which lapsed in August. **THE QUESTION: does the live path rank the large-cap tier closely
enough to the Sharadar panel that the forward record still measures the backtested
construction?**

---

## 1. PREMISE CORRECTIONS, ALL MEASURED BEFORE THIS REGISTER WAS WRITTEN

### 1a. The brief's named live store is EMPTY OF LIVE SCANS — but a real snapshot exists elsewhere

The brief states *"local `data/screener.db` holds laptop-era live scans through 2026-08-15"*.
**Measured, it does not.** `screener.db` carries **ONE** scan row dated **2099-01-01** — a test
fixture — and an **empty** `universe` table. `data/archive/scans/` carries three files
(2026-08-02/03/04), **every one self-labelled `provider: "synthetic (offline test)"`** with
tickers named `SYN0802`, `SYN0309`, `SYN0905`. None is a live scan.

**THE CHECK IS NOT BLOCKED, BECAUSE THE CENSUS FOUND THE REAL ONE SOMEWHERE ELSE:**
`data/live_cache/snapshot_2026-08-08.json` — **scan_date 2026-08-08, provider "Financial
Modeling Prep", universe 800, scored 594, 500 rows** carrying `composite`, `hot_score`,
`market_cap` and the `z_*` themes. That is a genuine live-path snapshot, and it sits **6 trading
days after the freeze's last date**.

**A census that probes only the store a brief names measures the brief.** `W-14` recorded that
exact failure for `WRDS_CENSUS.md`; here it would have closed a runnable item as unrunnable.

### 1b. Two of the five named themes are NOT exposed, and one is reconstructible

The brief's (d) asks for per-theme Spearman on *value, quality/growth, momentum, size, capital
discipline*. The served payload exposes **`z_value`, `z_quality`, `z_growth`, `z_momentum`,
`z_insider`** — and **no `z_size`, no `z_capital_discipline`**.

* **`size` IS reconstructible on both sides**: `factors.py` defines it as `z_neg_log_mktcap`, and
  `market_cap` is in the payload. It is rebuilt identically on both sides and LABELLED a
  reconstruction.
* **`capital_discipline` is NOT comparable** from the served payload — it is `z_neg_issuance`
  and issuance is not served. Recorded as not-measured, never as zero.

### 1c. The live composite is NOT weighted like the panel's, so the primary is made like-for-like

`screen.py::_effective_weights` returns **bucket-specific** weights (established / speculative),
while the panel's deployed composite is **flat 0.125 over seven themes**, renormalised. A
Spearman between the two as-served would measure **vendor AND weighting together** and could not
separate them.

**So the PRIMARY is a LIKE-FOR-LIKE composite**: flat, equal weight, over exactly the themes both
sides expose — **`value`, `quality`, `momentum`, `insider`, `size`** (five of the deployed seven;
`institutional` and `capital_discipline` are not served). Computed by one code path on both
sides. The **served** composite is reported as a SECONDARY, labelled as carrying the weighting
difference.

**No learned override is in play, checked rather than assumed:** `_effective_weights` uses
defaults unless `weight_adoption.authorisation` clears a stored row, and `learned_config` is
**empty** in the store that produced the snapshot.

---

## 2. THE TWO SIDES

| | |
|---|---|
| **Sharadar side (primary)** | `score_universe_now` on `data/backtest_freeze_2026-08`, **`as_of=2026-07-31`** |
| **Sharadar side (second reading)** | `score_universe_now` on `data/backtest`, **`as_of=2026-07-24`** |
| **Live side** | `data/live_cache/snapshot_2026-08-08.json` (FMP, 594 scored of 800) |
| **THE GAP** | **6 trading days** (2026-07-31 → 2026-08-08) |

The tier is the live book's own: **market cap >= $10bn**, confirmed from the served payload's
`criteria.large_cap_min`. Metrics are computed on the **overlapping** names of that tier.

---

## 3. THE NOISE CEILING — MEASURED FIRST, BARS WRITTEN AGAINST IT

A cross-vendor Spearman of 0.70 is excellent if the vendor-free ceiling is 0.72 and worthless if
it is 0.98. `W-28` died on a bar its account could not reach and `W-1`'s `K2` was set from the
wrong arm's figure, so the ceiling is measured before any bar is written.

**MEASURED (`D9_NOISE_CEILING.json`), on the large-cap tier:**

| ceiling | gap | composite Spearman | top-decile overlap |
|---|---|---|---|
| Sharadar vs itself | 63 trading days | **0.4971** | **0.2705** |
| Sharadar vs itself | 126 trading days | 0.4151 | 0.2008 |
| live vs itself (2026-08-08 vs 2026-09-29) | 36 trading days | **0.6859** | **0.3800** |

**INTERPOLATED TO THE 6-TRADING-DAY GAP, linear in trading days, and LABELLED an interpolation:**
Sharadar gives **0.952**, live gives **0.948**. **Two independent vendors agree on a ~0.95
ceiling**, which is what makes it worth setting a bar against. Rank persistence decays faster
than linearly at short lags, so both figures **OVERSTATE** the ceiling — the conservative
direction for a GO.

**THE NUMBER THAT PUTS IT IN PROPORTION, and Don should see it whatever the verdict: the Sharadar
panel's own large-cap top decile retains only 27.05% of its names across ONE rebalance.** Any
vendor disagreement smaller than that is second-order against the churn the strategy already
runs.

---

## 4. BARS — fixed here, before any cross-vendor number is read

Ambiguous against a bar is **NO-GO** (`RUN_RULES` A6). **GO requires ALL of:**

| # | metric (large-cap tier, overlapping names) | bar | why this number |
|---|---|---|---|
| **B1** | like-for-like composite Spearman | **>= 0.80** | the ceiling is ~0.95, so 0.80 allows ~0.15 of rank correlation to vendor and no more; and it is far above the 0.4971 the SAME vendor shows across one rebalance |
| **B2** | top-decile overlap (Sharadar decile also in live decile) | **>= 0.60** | the 6-day ceiling interpolates to ~0.90; 0.60 permits real slippage while still requiring a clear majority, and it is **2.2x** the 0.2705 the vendor's own decile retains across a rebalance |
| **B3** | per-theme Spearman, EACH of `value`, `quality`, `momentum`, `size` | **>= 0.70** | these are the same formula on different fundamentals vendors; below 0.70 a theme is measuring something else |
| **B4** | `institutional` and `insider` | **cited, not re-derived** | `FIDELITY-2` measured **+0.9190** and **+0.8726**; both clear any bar this register would set, and re-deriving them would spend a second measurement on a settled question |

`z_growth` is reported as a diagnostic: it is served but is **not** one of the deployed seven, so
it carries no bar.

---

## 5. COVERAGE CENSUS (the brief's (f)), REQUIRED OUTPUT WHATEVER THE VERDICT

Every name in the **Sharadar** large-cap decile that is **absent from the live universe**, listed
with its market cap. The live universe is an **800-name liquidity cut** against the panel's
2,531, so absence is expected; what matters is whether it is concentrated anywhere that changes
the book. Reported as a list, never as a percentage alone.

---

## 6. VOID CONDITIONS

1. Reading a verdict from a subset of the four bars, or from the secondary served-composite
   Spearman alone.
2. Re-deriving `FIDELITY-2`'s institutional/insider figures instead of citing them.
3. Moving any bar after a cross-vendor number is read. The bars in §4 are this register's; a
   successor may not relax one after watching it fail (`W-28`'s rule).
4. Treating `capital_discipline` as agreeing because it was not measured.
5. Quoting the interpolated ceiling as a measurement.
6. Any adoption, any change to the bound track, the contract or the service.

---

## 7. WHAT EACH OUTCOME DOES

* **GO** — the free live path ranks the large-cap tier closely enough that the forward record
  continues to measure the backtested construction. Recorded; **nothing is adopted**, because
  nothing needs to be: Don has already decided the route.
* **NO-GO** — names the failing metric and **routes the fallback, a one-month Sharadar renewal,
  to Don.** It is the right fallback for a measurable reason: a renewal is the only thing that
  puts both sides on the SAME DATE, which is the one condition under which this question is
  cleanly answerable at all.

**Expectations, scored afterwards.** (1) B1 clears, 65% — the two paths share the formula and
differ only in fundamentals vendor. (2) B2 is the binding bar, 60% — a decile is a small set and
overlap is the harshest of the four. (3) At least one of the four themes misses B3, 55% — the
free vendor's coverage differs most on the accounting-heavy inputs. (4) The coverage census finds
the absent names concentrated in the smaller half of the tier, 70%.
