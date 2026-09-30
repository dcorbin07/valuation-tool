# HANDOFF — scout / W-6 CRSP delisting cross-check

**2026-09-30. Zero trials, zero dollars, CONTROL class. Register
`PREREG_w6_crsp_delist_xcheck.md`, committed ALONE at `921c810` (markdown only, zero `.py`), a
strict git ancestor of every commit that computes an agreement rate.**

`W-6` had no ledger row and had never run. Under `MB1-SEL` a control can only **BLOCK** a
finding, never produce one, so this charges **zero trials** and **ADOPTS NOTHING**.

---

## 1. VERDICT — NULL ON ALL THREE BARS (A6)

| bar | rate | n compared | bar | verdict |
|---|---|---|---|---|
| **V1** flag agreement | **0.883249** | 591 names | 0.95 | **FAIL** |
| **V2** date agreement ±3d | **0.940613** | 522 events | 0.95 | **FAIL** (narrowly) |
| **V3** terminal return ±0.01 | **0.674603** | 504 events | 0.90 | **FAIL** |
| `K1` dated link | **0.883249** | 591 names | 0.80 | **PASS** |
| `K2` both-halves split | 241 early / 235 late event-dates | — | ≥16 | **AVAILABLE** |

**C1 is EXACT and it is what licenses every figure above.** The panel reproduces the published
record at **max |delta| 0.000e+00** on all four fields — `top_decile_alpha`
0.07174142332098163, long-short naive *t* 2.8360640685320595, HAC *t* 2.6199121240414884,
monotonicity −0.8909090909090909 — so the object cross-checked here IS the object the record
describes. It ran in its own pass and aborts the item on failure.

Ambiguous against a pre-committed bar is a NULL, and a failing bar **licenses a NEW register
with its own charge and Don's decision** — not a repair here.

## 2. THE SUBSTANTIVE FINDING

**164 of 504 matched delisting events — 32.5% — would have their terminal return moved by more
than 1 percentage point under CRSP's `dlret`.** Split by half on the effective dates: **79 early,
85 late** (boundary 2018-11-28), so it is **balanced and not an era artefact**.

The distribution matters as much as the count: median |Δ| is **0.0026** — most events barely move
— while p95 is **0.0568**. So the disagreement is a **tail phenomenon**, not a uniform drift, and
it is the tail that a survivorship mask most needs to be right about.

**V2 fails while most events agree EXACTLY**: median absolute date gap is **0.0 days**. It misses
0.95 by 0.94pp. That is the shape of a small hard-disagreement set inside otherwise perfect
agreement, not of a vendor-wide offset.

**V1's failure is coverage-limited rather than a conflict.** The residual 67 unmatched names are
dominated by foreign/ADR suffixes (`ABBNY`, `CAJPY`, `CIXXF`, `ALLGF`, `ARVLF`, `BBLNF`) that
CRSP's US-exchange tape does not carry at all. So for ~12% of delisted panel names **the mask
cannot be checked against CRSP in either direction**.

### The disagreement set, split on `W-3b`'s taxonomy

| cause | n | meaning |
|---|---|---|
| **COVERAGE GAP** | **69** | CRSP has no dated interval, so there was never a counterpart |
| **REAL CONFLICT — date** | **31** | CRSP has a record and its date disagrees by >3 days |
| **REAL CONFLICT — terminal return** | **164** | `dlret` moves the terminal return past ±0.01 |

## 3. AND AGREEMENT IS NOT PROOF — stated in the register before the run, and it binds

Both vendors ultimately read the same exchange and regulator notices. Where they agree, that
shows **neither mangled the transcription**; it does not show the notice was right, nor that a
delisting absent from both did not happen. So even the 67.5% of V3 that agrees is weaker evidence
than its size suggests, and **no PASS here would have meant "the mask is correct"** — only "not
independently contradicted".

## 4. BUGS FOUND — one, in my own instrument, and it decided the item's first answer

**The first cut of the join fired K1 at a dated link of 0.6633 and would have STOPPED the item.**
That was a **key mismatch, not a coverage gap**, and the shape of the failure is what exposed it:
all 199 unmatched names failed at the *ticker → permno* step and **zero** had a permno that
lacked a CRSP delisting record. Censused, **179 of the 199 carry a Sharadar suffix CRSP does not
use** — **109 a trailing digit** (appended when a ticker is REUSED by a later company) and **70 a
trailing `Q`** (bankruptcy). So the join was failing on precisely the names most likely to have
delisted: the bankrupt ones and the reused ones.

Repaired with a **fallback that runs only where the raw lookup already failed and stays
DATE-SCOPED**, rescuing **130** names — `AGN1→AGN` (Allergan), `AMTD1→AMTD` (TD Ameritrade,
acquired 2020), `APC1→APC` (Anadarko, 2019), `ALTR1→ALTR` (Altera), `AKRXQ→AKRX`.

**The bar was NOT touched.** K1 stays at 0.80, V1 at 0.95; what changed is the key. Void
condition 1 forbids relaxing a bar and void condition 4 forbids an undated map — the retry is
date-scoped, so both hold. Both link shares ship: **0.6633 raw-only** and **0.8832 repaired**.

**Independent corroboration that the repair is right rather than convenient:** the repaired link
of **0.883249** lands within **0.0002** of `W-28`'s separately measured dated link of **88.34%**
on the same account.

### The rescue validated itself, and it is not clean

Stripping a suffix could match a **different company** — `W-28`'s contamination shape — so V2 and
V3 were computed **per route**. If the rescue were matching wrong companies their delisting dates
would not agree, so the rescued route's own rate IS the test:

| route | V2 | V3 | n |
|---|---|---|---|
| raw | **0.9643** | **0.7222** | 392 / 378 |
| suffix-stripped | **0.8692** | **0.5317** | 130 / 126 |

The rescued route agrees **far above chance** but **measurably less well on both bars**, which is
consistent with **some** wrong-company matches among the 130. Reported as it came out: the repair
is sound in aggregate and is not exact, and a successor leaning on the rescued subset should
carry these two rates with it.

## 5. SCOPE HONOURED IN ADVANCE

CRSP is cut at **2024-12-31**. The panel's **five** later rebalance dates — 2025-01-27,
2025-04-28, 2025-07-29, 2025-10-27, 2026-01-28 — are **UNVERIFIABLE by construction** and are
**listed, never scored**, along with the **125** ACTIONS delisting events past the cut.
**`W-28` read this exact cut as a coverage gap** and had to repair its instrument mid-item; here
it is declared before the run.

`C6`: the unmatched names are **counted and listed**, never read as agreement.
`C3`: every rate above carries the count it was computed over, and a rate over zero events is
reported **VACUOUS**, never PASSING.

## 6. POWER (A11)

**No MDE applies — no return statistic is computed; the pre-declared bars are agreement rates.
Equity N 248, hurdle 3.3207, unchanged by this file.** `by_domain` bit-identical before and
after — equity 248, options 310, unified 0, infra 20 — with `rows_fixed_not_counted` rising
**84 → 85**, the proof the row was seen and correctly excluded.

**A log-convention point a successor will hit, found by a suite rather than by reading.** The
first cut of this row led with *"ZERO TRIALS, CONTROL class"* and
`tests/test_research_page.py::test_fixed_rows_are_in_the_record_but_count_zero_trials` went red:
its rule is `all(n_trials >= 1 for rows whose verdict does not bucket as "fixed")`, so **a row
charging nothing must carry the `FIXED` class marker** regardless of whether anything was
repaired. `FIXED` is the record's marker for *charges no trial*, not for *fixed a bug* — `W-28`
is the exact precedent, a control that stopped at its own K1 and logged `FIXED-class, ZERO
TRIALS` at `n=0`. Note this does **not** contradict `O21`, which was corrected **upward** to one
trial: `O21` measured an outcome about returns against a materiality bar, which is a search,
whereas this item is a control that can only block. The brief fixes the charge at zero
explicitly under `MB1-SEL`.

## 7. NOT DONE

Nothing is adopted and **no correction to the mask is made**. The three failing bars license a
**new register**, not an edit here, and none is proposed. The `dlstcd` *reason codes* are read
but not analysed — whether the 31 date conflicts and 164 return conflicts concentrate in
particular delisting causes (merger vs bankruptcy vs regulatory) is **unmeasured** and is the
obvious successor. No second tolerance and no second bar was tried.

**Expectations scored: 1 WRONG** (V1 ≥ 95%, priced 60/40), **2 WRONG** (V2 ≥ 95%, 55/45 — missed
by 0.94pp), **3 RIGHT** (disagreement set non-empty with at least one moved terminal return,
70/30 — 164 of them), **4 RIGHT, but only after the join was repaired** (K1 does not fire, 80/20:
it fired at 0.6633 on the first cut and passes at 0.8832 on the repaired key, which is the honest
way to score it).

## 8. ARTEFACTS

`PREREG_w6_crsp_delist_xcheck.md` · `scripts/w6_crsp_delist_xcheck.py` ·
`W6_CRSP_DELIST_XCHECK.md` (tracked) · `D:\wrds\W6_CRSP_DELIST_XCHECK.json` (banked per rule 9,
outside the repo) · `tests/test_w6_crsp_delist_xcheck.py` (14 of 14 passing, the over-stripping
guard carrying a positive control) · `RESEARCH_LOG.md` and `VALQUO_LEDGER.md` rows `W-6`.

**Fence honoured: no raw CRSP row leaves `D:\wrds`.** Nothing under `data/`, no `*.pkl`, and
nothing from `D:\wrds` is committed.
