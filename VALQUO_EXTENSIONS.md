# VALQUO EXTENSIONS — V1–V5, adopted by Don 2026-08-09

Five items beyond the external audit's 134, each enabled by infrastructure built during the audit
era. Same rules as everything else: pre-register before measuring, ambiguous = NULL, every arm to
`RESEARCH_LOG.md`, ledger-style status tracked HERE (this file is their register — update your row
on landing). **First agent to execute any section commits this file.**

| id | title | owner | status |
|---|---|---|---|
| V1 | Shadow vintages — forward A/B of every adoption | pipeline builder | OPEN — blocked on Amendment 1 landing |
| V2 | Live theme-health meter | greeks agent | OPEN |
| V3 | Noise-calibrated hot score | r1 | OPEN |
| V4 | Public research-log page | app fixer | **DONE 2026-08-09** — `/work/research`, linked from `/work`; see `HANDOFF_appfixes.md` session 21 |
| V5 | Measured slippage vs modeled costs | options bot | OPEN |

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
