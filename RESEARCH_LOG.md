# RESEARCH_LOG — one row per pre-registered test, append-only

**Audit item M1.** Started 2026-08-03 while executing `VALQUO_EDGE_AUDIT.md`.

## Why this file exists

Every multiple-testing claim in this project is currently computed against a denominator of **8**
— the eight weight schemes `_deflated_sharpe` is handed. The external audit reconstructed roughly
**146 distinct pre-registered tests** across the handoff corpus. Those two facts cannot both
inform the same claim, and the smaller one is the one shipping in `BACKTEST_RESULTS.json`.

The purpose here is a single, honest trial counter that survives sessions, so that:

- `_deflated_sharpe` can be fed a real `N` instead of 8;
- Benjamini–Hochberg can be applied across the family of *equity* signal tests, the way
  `options_autopsy` already does across its 126 option features;
- the Harvey–Liu–Zhu adjusted hurdle can be quoted for the number of trials **actually run**.

At N ≈ 146, √(2·ln N) ≈ 3.16 — which is, near enough, the Harvey–Liu–Zhu hurdle of 3.0 that the
long-short *t* of 3.52 already clears. **That is a stronger claim than the current one precisely
because it is defensible**, which is the whole argument for maintaining this file.

## Status — read this before using the count

**The retrospective population is NOT done, and `N` is NOT wired into `_deflated_sharpe`.**

The audit's own instruction was to populate this from "section A of the ledger", the reconstructed
list of ~146 prior tests. **That section is not in `VALQUO_EDGE_AUDIT.md` and no such document is
in the working folder** — only the count is quoted, in four places. So the retrospective rows have
to be re-extracted from the handoff corpus (`HANDOFF_*.md`, `OPTIONS_*.md`, the roadmap files),
which is real clerical work and was not attempted in a session already carrying thirteen
corrections.

**Wiring a partial count would be worse than the current state, not better.** A denominator of 30
carries the same false precision as a denominator of 8 while looking like it was measured. The
current statistic at least now *labels itself* as an undeflated PSR when `sr0` collapses (audit
B9), which is an honest signal. Wiring `N` happens when the count is complete, in one step.

## Schema

One row per test. A test earns a row when its threshold was committed **before** its run — that
is what makes it a trial rather than an observation. Exploratory looks, smoke tests and
diagnostics do **not** get rows; they get no claim either.

| Field | Meaning |
|---|---|
| `id` | stable, never reused. `<domain><n>` or the audit's own item ID where one exists |
| `date` | ISO date the verdict was recorded |
| `domain` | `equity` / `options` / `unified` / `infra` — BH-FDR families are formed within a domain |
| `hypothesis` | what was predicted, in one line, in the direction predicted |
| `universe` | the exact set. "full 2,710-name panel", "187-name options book", "smoke test: 12 names" |
| `metric` | the statistic the verdict rests on |
| `threshold` | the bar, as committed **before** the run |
| `verdict` | `ADOPTED` / `REJECTED` / `NULL` / `INCONCLUSIVE` / `SUPERSEDED` / `FIXED` |
| `source` | the handoff or commit carrying the numbers |

`FIXED` marks a correctness repair rather than a hypothesis test. **`FIXED` rows do NOT count
toward `N`** — repairing a bug is not a search over the data, and inflating the denominator with
bug fixes would understate the evidence rather than overstate it. Only `ADOPTED` / `REJECTED` /
`NULL` / `INCONCLUSIVE` rows are trials.

---

## Rows

| id | date | domain | hypothesis | universe | metric | threshold (pre-committed) | verdict | source |
|---|---|---|---|---|---|---|---|---|
| C7 | 2026-08-03 | infra | The auto-merge gate covering one suite of sixteen lets regressions reach production | 16 suites, 552 tests | all suites green | every suite must pass locally before it may gate | FIXED | `HANDOFF_edge_audit.md` |
| D10 | 2026-08-03 | infra | Sharadar's schema questions can be settled from the live entitlement before it lapses | live API key | 6 documented questions | answer or record the failure | ADOPTED | `HANDOFF_edge_audit.md` |
| D10-a | 2026-08-03 | equity | Restatements append a new ARQ row, so a datekey-deduplicated TTM window can double-count a quarter | full export, 197,265 ARQ rows | share of (ticker, reportperiod) groups with >1 datekey | any non-zero share is a defect | FIXED | `HANDOFF_edge_audit.md` |
| B1 | 2026-08-03 | options | The broad options universe feeds an adjusted close into option maths that requires the as-traded price | 5 call sites, 4 modules | code + entry-IV sanity band | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B3 | 2026-08-03 | options | Expiry is marked at a stale quote rather than intrinsic value | `options_fill.round_trip` | mark age vs settlement | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B9 | 2026-08-03 | equity | The "Deflated Sharpe" is an undeflated PSR because the eight trials are indistinguishable | 8 weight schemes | `sr0` vs Sharpe | `sr0` < 5% of SR = undeflated | FIXED (relabel only) | `HANDOFF_edge_audit.md` |
| B10 | 2026-08-03 | equity | `accruals_q` is computed as Sloan and silently overwritten with FCF/NI | full panel | which definition survives `build_frame` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B12 | 2026-08-03 | equity | Every "800 largest names" result was an alphabetical slice | `WRDSProvider.universe` | sort key | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B14 | 2026-08-03 | equity | The delisting mask's coverage is measured and discarded, so a missed delisting is silent | full panel | `ended_early_unmasked` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B15 | 2026-08-03 | options | The per-trade headline is gross of commission, contrary to its documentation | all options trades | `return_pct` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B16 | 2026-08-03 | options | A dead exit module is the likeliest thing to be mistaken for the live exit logic | — | imports | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B18 | 2026-08-03 | equity | Negative enterprise value is read two opposite ways within one theme | full panel, ~0.70% of rows | sign convention | one convention across all three ratios | FIXED | `HANDOFF_edge_audit.md` |
| B19 | 2026-08-03 | equity | Every "Sharpe" in the results file is an information ratio versus zero | all books | `rf` passed to `risk_stats` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B20 | 2026-08-03 | equity | `earnings_yield` switches numerator definition mid-cross-section | full panel | numerator basis | one definition throughout | FIXED | `HANDOFF_edge_audit.md` |
| B24 | 2026-08-03 | equity | `sanity_check` evaluates factors more than once, on different bases | full panel | scan-list duplicates | each factor once | FIXED | `HANDOFF_edge_audit.md` |
| B26 | 2026-08-03 | equity | A filing dated `as_of` is usable at that day's close | insider + grades | `searchsorted` side | exclude same-day | FIXED | `HANDOFF_edge_audit.md` |

**Trials counted toward `N` from this session: 1** (D10; the rest are `FIXED`). The pre-committed
thresholds for **R1**, **R2** and **R7** are recorded in `HANDOFF_edge_audit.md` Part 0 and become
rows when they run.

---

## How to add a row

1. Write the hypothesis and the threshold **before** the run, in the session handoff.
2. Run it.
3. Append one row here with the verdict — including, especially, the rejections and the nulls.
   A log that only records adoptions is a denominator of 8 with extra steps.
4. Never edit or delete a row. A superseded result gets a **new** row with verdict `SUPERSEDED`
   pointing at the one that replaced it.
