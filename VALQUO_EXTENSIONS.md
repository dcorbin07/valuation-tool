# VALQUO EXTENSIONS — V1–V5, adopted by Don 2026-08-09

Five items beyond the external audit's 134, each enabled by infrastructure built during the audit
era. Same rules as everything else: pre-register before measuring, ambiguous = NULL, every arm to
`RESEARCH_LOG.md`, ledger-style status tracked HERE (this file is their register — update your row
on landing). **First agent to execute any section commits this file.**

| id | title | owner | status |
|---|---|---|---|
| V1 | Shadow vintages — forward A/B of every adoption | pipeline builder | **REGISTERED 2026-08-10** — `valuation/edge/shadow_vintage.py`, pre-reg `PREREG_v1_shadow_vintages.md`, 26 tests, `HANDOFF_edge_audit.md` session 16. **No measurement and no verdict, because no vintage pair exists yet** — vintage 2 opened 2026-08-10 with no successor, which is exactly why the decision rule is registered now: not one parameter could have been chosen to suit a comparison, even in principle. Vintage 2's parameters are pinned in a tracked file at `params_id 0060c5ef3dda`. **The power is stated in advance and the honest half is unflattering:** pairing is a large real gain — at 2.0 pp/yr between-book TE the 60-month detectable difference is **3.34 pp/yr against the vs-SPY meter's 19.01** — but the tension is structural: σ is small exactly when the adoption changed little, and a change big enough to matter raises σ. **A pair that has not crossed is the EXPECTED outcome, not evidence the adoption was worthless.** Control: fed the contract meter's own 11.40 pp/yr TE it reproduces σ 3.9847 and ~19 pp/yr to the digit, because it imports `track_meter.boundary` rather than re-implementing it. Research-only, fenced off every public surface by an AST test before it has any numbers to leak. |
| V2 | Live theme-health meter | greeks agent | **BUILT 2026-08-09** — `scripts/theme_health.py`, pre-reg `PREREG_v2_theme_health.md`, 23 tests, `HANDOFF_live_data_bugs.md` Part 11. Reports **NOT-QUOTABLE on all ten themes, on ZERO usable rows** — every archived scan day is synthetic and the store's one row is a 2099 test fixture. **The finding is the calibration: at 100 names the band has 2.5% power at 60 months against `quality`'s own backtested IC, at 800 names 80.3% — so the full-universe store is the asset and the top-100 archive cannot answer this, ever.** Needs real full-universe snapshots retained; earliest first reading ~9 months after capture starts. **FOLLOW-UP LANDED 2026-08-10 (`scripts/live_cache.py`, pre-reg `PREREG_v2f_live_coverage.md`, 40 tests, Part 12):** the real record IS reachable from a checkout after all — the public credential-free `/api/hotstocks` carries all ten per-name theme scores, so the meter now reads **500 real rows** instead of 0. It serves the LATEST scan only, so the record accrues **forward** one day per run and can never be backfilled. **All ten verdicts unchanged** (still 0 closed 63d windows), but seven themes moved from *blocked by absent data* to *blocked by elapsed time*. **Two live defects found: three themes carrying 42.9% of the deployed weight contribute nothing to any live score, and the meter itself had no variance guard — a constant theme would have produced a VERDICT, not a refusal.** **SECOND FOLLOW-UP LANDED 2026-08-10 (`scripts/live_theme_sources.py`, pre-reg `PREREG_v2g_live_theme_sources.md` committed alone at `66310e7`, 53 tests, Part 13):** a free, public source now exists for all three dead themes — **13F straight from SEC's structured data sets** (the licensed thing is SF3, not the filings), **share issuance from XBRL company facts**, and the repo's already-fixed **Form 4 scraper** called unmodified. Coverage against the same 500 served rows: `institutional` **0 → 411 (82.2%)**, `capital_discipline` **0 → 456 (91.2%)**, `insider` **1 distinct value → 297**; deployed weight reaching a live score **56.5% → 95.5%**. All five pre-committed bounds held, including the falsifiable one (NVDA 5,775 filers; Spearman(breadth, log mcap) +0.539). **MEASURED ONLY — zero files under `valuation/` touched, so no composite change, no weight flip and no vintage event, and a test enforces it rather than prose promising it.** The CUSIP join is the weak point and is reported as such: 26.8% failure inside Financial Services against 13.2% outside, because a company that is itself an asset manager files 13Gs about *other* issuers into its own EDGAR feed. **The register's own ownership anchor turned out to be one-sided** — it waved through 12 megacaps (CMCSA, RIO, BTI, HSBC…) joined to a CUSIP with ONE reporting holder; fixed with a structural `MIN_HOLDERS = 2` and both figures published. **ADOPTION IS EXPLICITLY NOT LICENSED BY THIS** — it needs the cost measurement and the held-out gate, and under Rule 6 it would close vintage 2 and reset the whole forward clock. |
| V3 | Noise-calibrated hot score | r1 | **DONE 2026-08-10 — NOT DISTINGUISHABLE at rank 10 (real 1.0909 vs noise p95 1.1117, p 0.116); holds on 45 of 69 dates, so the confidence language must weaken. `HANDOFF_extensions_v3.md`** — **AND IT HAS, 2026-08-10 (app fixer):** the one dependency r1 left open is closed. `valuation/web/score_confidence.py` is the single source for the calibrated wording; the hot-list legend, the discovery blurb, the per-name attribution panel and `/methodology` all read it, and every sentence is pinned **verbatim** to the handoff by `tests/test_score_confidence.py` (mutation-tested, 4 of 4 drifts caught). Scope held deliberately: this weakens the **score's** precision claim and **not** the backtested return spread, which V3 explicitly does not settle. `HANDOFF_appfixes.md` session 22, ledger `V3-COPY`. **STILL OPEN — V3's finding 3:** the thin-coverage tilt (p 0.018) is now *disclosed* but not *corrected*; a minimum-coverage floor or a variance penalty on thinly-scored names is a new edge-lane pre-registration. |
| V4 | Public research-log page | app fixer | **DONE 2026-08-09** — `/work/research`, linked from `/work`; see `HANDOFF_appfixes.md` session 21 |
| V5 | Measured slippage vs modeled costs | options bot | **DONE 2026-08-09** — `scripts/slippage_report.py`, pre-reg `PREREG_v5_slippage.md`, 57 tests, `HANDOFF_optionsbot.md`. Headline **INSUFFICIENT and that is the pre-registered outcome**: the paper book holds **3 entry fills and ZERO exits**, so the exit half-spread has n=0 against a minimum of 30. **The bar is measured, not assumed — 410.0 bps of premium (mean) on 3,885 of 3,885 banked trades — and the brief's "modelled 33.4bps" is audit B11's EQUITY cost in bps of stock notional, a ~12x category error.** Two shipped-code bugs found in the first three real fills (exit levels anchored to the pre-fill submit price; the alert's own sizing veto ignored), both routed not repaired. |

---

## V1 — Shadow vintages (pipeline builder; `valuation/edge/**`; AFTER Amendment 1 lands)

When a rules-changing adoption opens vintage N+1, the daily scan keeps scoring vintage N's frozen
composite in shadow: two books, same dates, same costs, one extra stored column set. The meter
machinery then answers, anytime-validly, "did the adoption help, live?" Requirements: the shadow
book is constructed by the SAME code path with the OLD frozen parameters (a pinned snapshot of the
config, not a re-derivation); divergence between the books is reported per rebalance; a
pre-registered rule (written before the first vintage pair exists) states what difference over what
period counts as CONFIRMED-LIVE / HARMED / NULL. The shadow never reaches any public surface — it
is research instrumentation. Report in `HANDOFF_edge_audit.md`.

## V2 — Live theme-health meter (greeks agent; NEW FILES ONLY + reads)

The backtest's theme ICs (quality +3.39, momentum +2.62, …) have never been checked against live
forward returns. Build `scripts/theme_health.py`: from the persisted per-name snapshots (in the
screener store since task #97), compute each theme's realized forward rank-IC on live data at the
63d horizon as windows close, monthly cadence, with an anytime-valid band per theme. Pre-register
BEFORE first computation: the horizon, the IC definition (same as the panel's), the band
construction, and what counts as a DEGRADED flag (e.g. band excludes the backtest IC's sign).
Scope: new script + owner-side Edge Lab surface data only; you may IMPORT the edge meter library
read-only but edit nothing in `valuation/edge/**`. Coverage rule applies: report snapshot depth per
theme before quoting any IC — the early months will be too thin to say anything, and the output
must say so itself. Report in `HANDOFF_live_data_bugs.md`.

## V3 — Noise-calibrated hot score (r1; NEW FILES ONLY + reads)

X7's placebo harness calibrated the research bars; point it at the product. Build
`scripts/score_calibration.py`: generate noise universes by the X7 permutation method (import the
edge harness read-only; same seeds convention), score each through the LIVE composite path, and
measure the distribution of top-decile scores/compositions noise produces. Deliverable: a
calibration table — "a #k-ranked name with composite z ≥ x occurs in fewer than y% of noise
universes" — and ONE plain sentence per rank band suitable for the product. Pre-register the
permutation scheme, n draws, and the statistic before running. If the answer is unflattering (noise
routinely produces books this clean), that ships too — it would mean the score's confidence
language must weaken, which is a finding, not a failure. Report in `HANDOFF_backup.md`? No — new
file `HANDOFF_extensions_v3.md`. Store the draws, not just the summary (RUN_RULES).

## V4 — Public research-log page (app fixer; `valuation/web/**`; AFTER the Discord fix)

Render the research record as a public page: every pre-registration, every verdict —
ADOPTED / REJECTED / NULL — with dates and the one-line reason, sourced from `RESEARCH_LOG.md` and
the registers (never hand-maintained twice). Method as the credential. Hard constraints: NO
performance figures beyond what the public posture already allows; a REJECTED/NULL-heavy record is
the point, render it proudly, not apologetically; vendor names fine, raw vendor data never; the
page carries one sentence explaining pre-registration to a lay reader. Link it from /work — it is
the strongest thing a recruiter can see. Report in `HANDOFF_appfixes.md`.

**DONE 2026-08-09** (app fixer, session 21). `/work/research`, rendered from
`RESEARCH_LOG.md` through `research_log.rows()` — the SAME parse that produces the trial
denominator `N`, so the page and the counter cannot disagree — plus the registers listed by
reading the files on disk. **83 entries: 32 rejected, 7 null, 4 inconclusive, 15 adopted,
21 defects fixed, 4 other.** The publishing rule is in one place
(`valuation/web/research_record.py::withhold`) and the page renders **no performance figure at
all**, which is stricter than "nothing beyond the public posture" and is what makes it testable;
`test_research_page.py` asserts it on the rendered HTML. Registration dates are deliberately NOT
shown — scraping them gave one register a date of 1998-01-01 from its own contents, and a wrong
date is the one error that would undermine the page's whole claim.

## V5 — Measured slippage vs modeled costs (options bot; NEW FILES ONLY + reads)

Session 14 wired the Tradier sandbox engine, so paper fills now accrue. Build
`scripts/slippage_report.py`: as fills accumulate, compare realized fill-vs-mark against the
modeled 33.4bps, per trade and cumulatively, with the sample size ALWAYS printed beside the
estimate. Pre-register: the slippage definition (which mark, which timestamp), the minimum n before
any aggregate is quoted (suggest ≥30 fills), and the rule for flagging divergence (e.g. measured
90% CI excludes the modeled cost). Output feeds S14 (no-trade band) and the capacity number — note
in the report that P2 showed assumed-vs-measured moved capacity 4.72x, which is why this exists.
Sandbox fills are optimistic vs real fills; say so in every output. Report in `HANDOFF_optionsbot.md`.

## V2G — What the three dead live themes cost in return (edge lane) — **DONE 2026-08-10**

Follow-up to V2F, which measured that `insider` (constant), `capital_discipline` and
`institutional` (both absent) reach no live score, carrying **42.9% of the deployed weight
mass** between them — and which explicitly left the price of that to a backtest.

**Answered.** Deployed 7-theme composite vs the same composite restricted to the four
live-present themes, renormalised exactly as `composite_score` does (proved exact, not
assumed). **Top-decile alpha +7.17% → +5.86%, Δ −1.31pp, paired HAC t −1.4040** against a
pre-registered −1.95pp bar → **IMMATERIAL**, at **55% power** against that bar.

**But the live four-theme book fails the calibrated long-short floor** (HAC t 1.8811 vs
2.2837) while clearing the top-decile alpha floor (3.2087 vs 2.2913). The product is
long-only, so what users receive stays demonstrable; the long-short statistic quoted beside
it does not. Exploratory: `institutional` is the only one of the three whose absence costs
in both halves — build 13F first, if any.

`PREREG_v2g_live_theme_cost.md`, `scripts/live_theme_cost.py`,
`data/free_analysis/LIVE_THEME_COST.json`. Equity `N` 131 → 135.

## S22 — Term structure of the signal and top-decile tenure (edge lane) — **DONE 2026-08-10**

Registered blind in `PREREG_s22_term_structure.md` at `6b187dd`, a strict git ancestor of the
measurement commit `ec4a5d3`. Eight horizons (1–8 quarters) scored from **one** panel build, so the
forward window is the only thing that varies.

* **VERDICT CONSTANT-RATE.** Annualized top-decile alpha is **essentially flat from three months to
  two years, +6.59% → +5.10%**; cumulative alpha reaches **+10.20%** at eight quarters,
  `R(8) = 6.195` against a pre-registered 6.0. Alpha HAC *t* never falls below **3.16**.
* **But the long-short spread decays to nothing** — HAC *t* **2.72 → 0.68**, cumulative spread
  peaking at Q5. The persistence is entirely in the **long** leg, which is the leg the product
  ships. Do not quote a long-short figure beyond about a year.
* **The classification does not replicate across halves** (early 8.56, late 5.47) even though the
  persistence does. `R(8)`'s denominator is one noisy quarter.
* **Tenure: KM median ONE rebalance**, 70.6% of spells last exactly one, retention 36.6% (inside
  the pre-committed 20–50% band derived from the shipped 261%/yr turnover). Re-entry is the norm —
  74% of names have more than one spell. Small caps stay **longest**, not large.
* **Per-horizon placebo** (200 draws, fixed weights, no CPCV, labelled `fixed_weights_null` and NOT comparable with X7's floors): 8 of 8 horizons clear their own top-decile alpha floor, 4 of 8 clear their own long-short floor.
* **Adopts nothing.** Rebalance-frequency change is **S23**'s own register and a **vintage event**.
  Display is the **web lane's**; the defensible product sentence is written in the handoff.
* Equity `N` 135 → 143.

## S23 — Exit rule for the equity book (edge lane) — **DONE 2026-08-11**

Registered blind in `PREREG_s23_exit_rule.md` at `6a73485`, a strict ancestor of the measurement
commit. One buy rule, `min_hold` identical across arms, five exits plus a never-sell control.

* **NO CHALLENGER BEATS THE INCUMBENT.** All four price-based exits move the book by **under
  0.4pp/yr in either direction** (|HAC *t*| ≤ 0.87), and **three of four flip sign across
  halves** — including the only positive one, which is exactly what the both-halves requirement
  exists to catch.
* **Never selling costs 10.89pp/yr at HAC *t* -3.801** —
  the only measurable effect in the study. The book grows to 417 names
  and alpha falls 15.48% → 3.37%.
  **This CONFIRMS S22 rather than contradicting it:** S22 measured one cohort over ~8 quarters,
  while a never-sell book keeps buying and converges on the universe. **Dilution, not friction.**
* **TP/SL pairs came from published convention and were never tuned**; no grid was swept.
* **Three defects found and fixed** — B6's per-ticker tail still in `build_valuation_panel`, live
  Yahoo hindsight in the point-in-time beta ladder, and a shipped `_backtest_hold` hot loop that
  cost 61 of every 70 seconds (fix proved bit-identical over 1,818 leaves).
* **Adopts nothing.** Adoption is a **vintage event** and Don's call. Equity `N` 143 → 149.
