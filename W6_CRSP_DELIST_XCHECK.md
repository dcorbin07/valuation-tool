# W6_CRSP_DELIST_XCHECK — CRSP delisting cross-check (CONTROL, zero trials)

Register: `PREREG_w6_crsp_delist_xcheck.md`. Generated `2026-09-30T05:32:10+00:00`.

**Both vendors derive from the same exchange notices, so a pass means the mask is not independently contradicted and never that it is correct**

CRSP is cut at **2024-12-31**. The panel's 5 later rebalance dates are UNVERIFIABLE by construction and are listed, never scored: `2025-01-27`, `2025-04-28`, `2025-07-29`, `2025-10-27`, `2026-01-28`.

## C1 — fidelity (gate)

| field | got | want |
|---|---|---|
| `top_decile_alpha` | 0.07174142332098163 | 0.07174142332098163 |
| `long_short_tstat` | 2.8360640685320595 | 2.8360640685320595 |
| `long_short_tstat_nw` | 2.6199121240414884 | 2.6199121240414884 |
| `monotonicity` | -0.8909090909090909 | -0.8909090909090909 |

max |delta| **0.000e+00** at `None` — **PASS**

## Bars — every rate with the count it was computed over (C3)

| bar | rate | n compared | bar | verdict |
|---|---|---|---|---|
| V1 | 0.883249 | 591 | 0.95 | FAIL |
| V2 | 0.940613 | 522 | 0.95 | FAIL |
| V3 | 0.674603 | 504 | 0.9 | FAIL |

`K1` dated link **0.883249** against **0.8** — PASS

## The disagreement set, split by cause (`W-3b`'s taxonomy)

| cause | n | meaning |
|---|---|---|
| COVERAGE_GAP | 69 | CRSP has no dated interval or no record, so there was never a counterpart to agree with |
| REAL_CONFLICT_date | 31 | CRSP has a record and its date disagrees by more than the pre-committed window |
| REAL_CONFLICT_terminal_return | 164 | CRSP's dlret moves the terminal return past the pre-committed tolerance |

## Verdict

**NULL on a pre-committed bar (A6): V1, V2, V3 below bar. The disagreement set is the deliverable and a failing bar licenses a NEW register, not a repair here.**

Zero trials. ADOPTS NOTHING — a control can only block, never produce (`MB1-SEL`). A failing bar licenses a NEW register with its own charge and Don's decision.
