# PRE-REGISTRATION — V2-follow-up: rate-limit-tolerant live-input coverage

Committed **alone, before `scripts/live_cache.py` existed and before any coverage number was
measured.** Greeks lane, 2026-08-10.

## 1. The question, and the premise it corrects

The brief says *"the theme-health meter and beta source cover 46 of 403 served names because two
full-universe attempts died on vendor rate limits."* **That is true of the beta source and false
of the theme-health meter, and the two failures have nothing in common.**

| | covered | why not more |
|---|---|---|
| beta source | **46 of 403** | genuine: Yahoo throttling killed runs 1 and 2 (`HANDOFF_live_data_bugs.md` §7.1) |
| theme-health meter | **0 of 403** | **not rate limits.** It reads the screener snapshot store, which in a checkout holds one synthetic 2099-01-01 fixture row. `auto-scan.yml` POSTs to the live site, so a checkout never receives a real scan (Part 11). |

A rate-limit-tolerant fetch path fixes the first and **cannot** fix the second. Both are in
scope; they are answered separately and must never be quoted as one number.

## 2. Scope (inherited from V2, stated so it can be checked)

**NEW FILES ONLY + reads.** No edits anywhere under `valuation/**` — not `valuation/edge/**`,
and not `valuation/engine/wacc.py` or `valuation/data/beta.py` either, which is stricter than the
brief requires. The beta ladder and the beta estimator are **imported and driven, never
reimplemented**, so the project keeps one definition of each. The only edits to existing files are
the report/register appends the brief mandates: `HANDOFF_live_data_bugs.md`, `VALQUO_LEDGER.md`,
`VALQUO_EXTENSIONS.md`.

## 3. The universe — pinned before fetching

The served universe is the latest saved scan snapshot, served publicly at
`GET /api/hotstocks?top=500` (no credential; `valuation/web/app.py:471`). It is **captured to disk
and pinned before any per-name fetch begins**, so the denominator cannot drift mid-run and cannot
be chosen after the numerator is known. The captured `scan_date`, `universe_size` and row count are
reported with every coverage figure.

Note the denominator is not a constant: the record's 403 was measured 2026-08-07; the endpoint is
capped at 500. **Coverage is always reported as `n / N` with `N` named and dated, never as a bare
percentage.**

## 4. Coverage definition — fixed now

A served name is **COVERED for beta** iff its cache record holds **both**:
1. the vendor beta field, either a number or a definitive absence (the name was fetched and the
   field was not there), and
2. a 5y monthly close series that pairs with the market proxy in **≥ 2** months,

so that the real ladder can be driven **offline, with zero network calls**. Anything less is NOT
covered. A name whose fetch was throttled is **not covered and not recorded**, so it is retried.

**Coverage counts what the ladder can be RUN on, not what was downloaded.** A cached record that
cannot produce a rung is not coverage.

## 5. The contamination rule — the run-2 lesson, made structural

*A measurement that consumes the resource it is measuring will report on its own exhaustion and
call it a result.* Run 1 satisfied two bounds because both arms landed on the same constant.

Therefore, fixed before the run:

- **Throttle and failure events are counted continuously and printed BEFORE any coverage figure.**
- **A failed or throttled fetch is never written to the manifest as terminal** — the miner's
  tri-state rule (`mine_options_cache.py:332-336`): a failed probe is not recorded at all, so the
  next run retries it. Only positive outcomes are durable.
- **The fetch aborts cleanly** when throttle events breach the configured budget, leaving the cache
  intact and resumable. An aborted fetch is a partial cache, never a partial verdict.
- **The report phase makes zero network calls.** It is therefore re-runnable and deterministic,
  and it cannot be contaminated by the conditions it is reporting on.

## 6. Bounds, committed before the run

**B1 — DO NO HARM (control). The batched path must not change any beta.** For every name where a
beta is resolvable both ways, the batched-and-cached close series must produce a beta **equal to
the per-ticker estimator within 1e-9**, and the same rung.

> **Stated honestly: this one is already measured, not blind.** During design I verified it on
> AAPL, MSFT, KO, XOM, CI, GILD, CHTR — all EXACT to 1e-9, and KO 0.3078 / XOM 0.2060 / CI 0.2885 /
> GILD 0.3050 / CHTR 0.6694 reproduce the values already in `HANDOFF_live_data_bugs.md` §7.6.
> It is recorded here as a **pinned invariant with a test**, not as a prediction. The reason it
> needed checking first: batched `yf.download` returns a **tz-naive** index while the market proxy
> is **tz-aware**, so the intersection is empty, `compute_beta` returns `unavailable`, and rung 3a
> keeps the vendor beta. **That failure is silent and fails in the safe direction** — corroboration
> would be disabled on every name with no error raised. B1 exists to make it loud.

**B2 — NO INFLATION BY CONTAMINATION.** Zero names may be counted as covered on a throttled or
failed fetch. Verified structurally (§5) and by test, not by inspection.

**B3 — HONEST DENOMINATOR.** I will report realized coverage whatever it is. I may **not** use the
phrase "full universe" unless **≥ 95%** of the pinned served names reach a terminal status.
Below that it is reported as a fraction and called a partial run.

**B4 — THE THEME READINGS MAY NOT MOVE.** The beta work and the theme-health meter share no input.
`scripts/theme_health.py` is run **before and after**, and every theme's verdict and depth is
reported both times. **If any theme reading changes, that is evidence of an unintended coupling
and I report it as a defect**, not as a result.

**B5 — REFUSAL SURVIVES BREADTH.** Real breadth does not create a closed 63-day window. If the
captured record makes any theme quotable, I must show the closed windows that justify it. A theme
that becomes quotable without closed windows is a defect in the meter.

## 7. What I expect — written down first, because this project's expectations keep being wrong

| prediction | confidence |
|---|---|
| beta coverage after ≥ 95% of the pinned served universe | 70 / 30 |
| **zero** theme readings change (B4 holds) | 95 / 5 |
| all ten themes remain NOT-QUOTABLE after capture, on zero closed windows | 90 / 10 |
| `capital_discipline`, `institutional`, `sentiment` stay at 0% live coverage | 85 / 15 |
| the full universe shows a **higher** `fallback` share than the 46-name sample, because that sample was the 7 named cases + every 12th name and is biased toward large, well-covered names | 60 / 40 |

## 8. What voids this pre-registration

Changing the coverage definition (§4), the contamination rule (§5) or any bound (§6) after seeing a
number. Tightening is permitted and must be recorded in the report with its reason; loosening is
not. Re-running the report phase is free and does not constitute a new trial.

## 9. Trial cost

**Zero.** This is an instrumentation and coverage exercise: it searches nothing, selects nothing,
and adopts nothing. Equity `N` stays **129**. No figure produced here may be quoted as evidence for
or against the edge.
