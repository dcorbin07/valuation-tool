<!-- GENERATED-AND-CURATED. Refresh with: python scripts/build_ledger.py -->
# VALQUO_LEDGER.md — the one place that answers "where do we stand?"

One row per external-audit item (`valquo_audit_items.json`, 134 items). This
file replaces reconstructing project state from git history.

## The contract (three rules — read them, they are why this file exists)

1. **Every agent updates its rows as part of its handoff.** A landed item with
   no ledger row is not finished work — the same standing as the existing
   "code without a handoff entry is not finished work" rule in `RUN_RULES.md`.
2. **The ledger is the answer to "where do we stand."** If it cannot answer,
   the ledger is broken and *fixing the ledger* is the task. Never another
   archaeology dig.
3. **Rows are append-and-amend, never silently rewritten.** A status that
   changes keeps its history in the note (`was X (sha) -> now Y`), because this
   project has already been bitten by claims that quietly changed meaning.

## How to read a row

* **status** — `OPEN` / `IN PROGRESS` / `DONE` / `BLOCKED` / `SUPERSEDED`.
* **verdict** — only for items that were actually measured: `ADOPTED` /
  `REJECTED` / `NULL` / `INCONCLUSIVE` / `DEFERRED`. It is filled in **only when
  the write-up literally uses one of those five words.** Most of the B series
  concluded `FIXED`, and `X8` concluded `REPLICATES` — real outcomes, but not
  verdicts in this vocabulary, so their column is blank and the write-up's own
  word is quoted in the note instead. Blank therefore means *"not measured, or
  measured and reported in different words"* — never *"we don't know"*.
* **commit** — a sha, so any claim here is checkable in one step. It is the
  commit whose *subject names the item* where one exists; otherwise it is the
  commit that **introduced the write-up**. Many items landed inside multi-item
  commits ("eleven Part I corrections") that never name them, so for much of the
  B series this is *"where it was recorded"*, not *"where it was fixed"* — a
  weaker claim, and stated here rather than left to be assumed. Unfinished rows
  carry no sha at all: a commit that merely *mentioned* an item reads as
  evidence of work done, and is worse than a blank.
* **handoff** — where the real write-up lives. The ledger is an index, not a
  replacement for it.
* **src** — `human` = hand-verified against the write-up; `build_ledger.py`
  will NOT overwrite it, only report a disagreement. `auto` = mechanically
  proposed and not yet read by a person; treat as a lead, not a fact.

## Four traps that already produced wrong counts — do not re-make them

1. **A forward reference is not a completion.** "feeds U1", "needed for S12",
   "(supports D1)" say the item is *wanted*, not *done*. Counting these is what
   produced the 68/134 figure against a header-only count of 38/134.
2. **`P1`–`P5` collide with the project's own PHASE labels.** CLAUDE.md's
   "DONE (P4 commit)" is phase P4; audit item P4 is open and explicitly "out of
   band". `P6`–`P10` and `P24.x` are phases only — the audit's P series stops
   at P5.
3. **`M2` is ambiguous across documents.** HANDOFF_STATUS.md's "the audit's M2
   (SanDisk/WDC)" is `CODE_AUDIT.md`'s M2. The external audit's M2 is
   "clustered inference default" and has never been touched.
4. **`D1`–`D10` collide with DECILE labels**, which this project writes
   constantly ("long-short (D1-D10)", "D1 22.8% → D10 10.7%").

`build_ledger.py` encodes all four. If you add a source file, re-check them.

## Ledger accuracy — checked against the tree 2026-08-07 (out-of-band claims audit)

The `CLAUDE.md` claims audit (`HANDOFF_claims_audit.md`, options-bot lane) verified every status
it touched against the commit the row names, not against prose. **The ledger came out well: every
status it checked — B6, B7, B8, B11, B12, B17, M1, R1, R9, R10, X2, X3, X7, X8, U7 — was
corroborated by the code or the artifact.** Two things worth carrying, neither edited here because
the rows are not this lane's:

* **`R3`'s note is stale.** It reads "Shrinks every options t ~1.36x". The corrected figure is
  **√2.212 = 1.487×** on the 3,885-trade book; 1.36× came from the pre-correction 3,042-trade book
  and `CLAUDE.md` already carries the correction. **Owner: whoever owns R3.**
* **`X8` is DONE and `CLAUDE.md` did not know it.** The ledger was right and the brief was wrong —
  which is rule 2 of the contract working exactly as intended. `CLAUDE.md` now records it.

## Refresh

    python scripts/build_ledger.py            # proposal + counts, writes nothing
    python scripts/build_ledger.py --write    # refresh src=auto rows only
    python scripts/build_ledger.py --evidence S12   # show why S12 sits where it does

| id | series | title | status | verdict | commit | handoff | date | src | note |
|---|---|---|---|---|---|---|---|---|---|
| B1 | B | Price basis in options_universe | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED. Every options number in the record predates it; the re-run is R2. |
| B2 | B | Exit-path quote censoring | DONE |  | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED, not yet re-measured. Stop days were censored exactly when the stop fires. |
| B3 | B | Stale-quote expiry marks | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED. Ships stale_mark_rejected + exit_quote_age_days; unblocks O12. |
| B4 | B | OI sentinel into chain_summary | DONE |  | 18f77db | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED. -1 OI sentinel read as a number; miner side re-mined (18f77db). |
| B5 | B | Four paper-track defects | DONE |  | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED, all four. Every defect flattered the track; its history predates the fix. |
| B6 | B | Panel truncation + date ranges | DONE |  | 5fce8bc | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED - largest correction in the audit. B6 is the whole headline drop (5fce8bc). |
| B7 | B | Unify the three composites | DONE |  | 5fce8bc | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED at nine call sites. Attribution: B7 is a null; B6 carried the drop. |
| B8 | B | Holdout rule vs documentation | DONE | FIXED |  | HANDOFF_edge_audit.md session 7 | 2026-08-06 | pipeline builder | rule_fired was computed at fundamental_panel.py:3545 and never read. FIXED, not renamed: oos_verdicts enforces the documented rule; `verdicts` keeps FROZEN semantics under the alias stability_verdicts because scripts/placebo.py:108 reads it and X7's ~6% FPR was calibrated against that object. NEITHER shipped decision changes - low_risk confirmed_oos, insider rejected_oos - but low_risk is confirmed in 1 of 2 directions, not 2. |
| B9 | B | DSR / PBO trial accounting | DONE |  | 1b8ff17 | HANDOFF_edge_audit.md | 2026-08-04 | human | RELABELLED, not recomputed. The honest recompute arrived via M1 (N=8 -> 84). |
| B10 | B | accruals_q silent overwrite | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED and it CHANGES THE COMPOSITE - but the recovered signal is the WORSE one. |
| B11 | B | Compute the 37bps figure | DONE |  | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED. The 37bps was an assumption quoted as a measurement; now both are measured. |
| B12 | B | Alphabetical universe | DONE |  | 3def852 | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED. Consequence is not: every 800-name-era result was an alphabetical slice. |
| B13 | B | prefilter in the backtest | IN PROGRESS |  | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | PARTIALLY FIXED and labelled so. Categorical filters bind; MIN_AVG_DOLLAR_VOLUME still cannot. |
| B14 | B | Ship delisting-mask coverage | DONE |  | 1b8ff17 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED. First number shipped: the ACTIONS delisting mask is complete. |
| B15 | B | Commission in return_pct | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED. Note profit_factor is still a ratio of summed percentages - non-standard. |
| B16 | B | Quarantine dead exit module | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED. The audit was PARTLY WRONG here and the correction is recorded. |
| B17 | B | top-25 hold holds fifty | DONE |  | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED (disclosure only). No behaviour changed and none should. |
| B18 | B | Negative EV read two ways | DONE |  | 1b8ff17 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED - and the new sign check caught the first fix being incomplete. |
| B19 | B | Sharpe uses rf=0 | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED (Sharpe rf=0), in the five cheap corrections. |
| B20 | B | earnings_yield numerator switch | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED (earnings_yield numerator), in the five cheap corrections. |
| B21 | B | _sector_capped never invoked | DONE | NULL | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | Measured for the first time, NOT adopted. Unusually flat null; caps stay off. |
| B22 | B | Results file loses blocks silently | DONE |  | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED. Verified on the corrected run - all 12 blocks present, no 'errors' key. |
| B23 | B | Four panel builds per run | OPEN | DEFERRED |  | HANDOFF_edge_audit.md |  | human | 'Not done, and not forgotten.' Speed-only item, NO blocker; take it alone. |
| B24 | B | sanity_check double-counts | DONE |  | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | FIXED (sanity_check double-count), in the five cheap corrections. |
| B25 | B | Three DSR conventions | DONE | REJECTED | 018ebc2 | HANDOFF_edge_audit.md | 2026-08-04 | human | The AUDIT'S finding is rejected as stated; one real defect found underneath and FIXED. |
| B26 | B | Same-day insider/grades | DONE |  | 2ded1f3 | HANDOFF_edge_audit.md | 2026-08-04 | human | FIXED - but see RETRACTION 2ded1f3: B26 did NOT flip the insider theme. DISPUTED. |
| R1 | R | Factor-adjusted alpha | DONE |  | b2b3f40 | HANDOFF_edge_audit.md | 2026-08-05 | human | THRESHOLD CLEARED, CLAIM A APPLIES: 'alpha' permitted as a range. Re-run after B6/B7. |
| R2 | R | Re-run broad options study | DONE | REJECTED | 0fb22a8 | HANDOFF_edge_audit.md | 2026-08-05 | human | The entry signal does not beat random entry on corrected data. Survived the correction. |
| R3 | R | Clustered inference (options) | DONE | ADOPTED | 0fb22a8 | HANDOFF_edge_audit.md | 2026-08-05 | human | Inference layer of record. Shrinks every options t ~1.36x and overturns NO verdict. |
| R4 | R | Multiple-testing accounting | BLOCKED |  |  | AGENTS.md |  | human | r1 lane open item; sits in valuation/edge/** which pipeline builder holds (AGENTS.md). |
| R5 | R | Four classic anomalies, full universe | BLOCKED |  |  | AGENTS.md |  | human | r1 lane open item; sits in valuation/edge/** which pipeline builder holds (AGENTS.md). |
| R6 | R | SF3 conviction family | BLOCKED |  |  | AGENTS.md |  | human | r1 lane open item; sits in valuation/edge/** which pipeline builder holds (AGENTS.md). |
| R7 | R | Re-commit term_slope floor | DONE | REJECTED | 0fb22a8 | HANDOFF_edge_audit.md | 2026-08-05 | human | New floor passes, the filter fails anyway. term_slope rejected; B2 fails the economic arm. |
| R8 | R | Total return, not price-only | BLOCKED |  |  | AGENTS.md |  | human | r1 lane open item; sits in valuation/edge/** which pipeline builder holds (AGENTS.md). |
| R9 | R | t-stat on headline; HAC | DONE | ADOPTED | 8cfcef5 | HANDOFF_edge_audit.md | 2026-08-05 | human | Headline finally has a significance statistic: t 4.517, HAC t 4.376, 71% hit rate. |
| R10 | R | Investable benchmark | DONE | ADOPTED | 8cfcef5 | HANDOFF_edge_audit.md | 2026-08-05 | human | Pre-registered EXPECTATION WAS WRONG, in the strategy's favour. |
| X1 | X | Split on universe, not time | OPEN |  |  | VALQUO_ACTION_PLAN.md |  | human | No write-up, no commit. Listed for Session 8+ in VALQUO_ACTION_PLAN.md. |
| X2 | X | Rebalance-grid offset | DONE |  | f70b380 | HANDOFF_edge_audit.md | 2026-08-05 | human | LEVEL is robust, SIGNIFICANCE STATISTICS are not; one Session-2 claim retired. |
| X3 | X | Ablate to best single signal | DONE | NULL | 3feeded | HANDOFF_edge_audit.md | 2026-08-06 | human | RE-RUN 2026-08-06. was DONE/'Earns its complexity' (bd495f5, 2026-08-03) -> now DONE/NULL. That run is SUPERSEDED: pre-B6 110-date panel (alpha +11.88% vs the corrected +7.17%) AND a 1.0pp three-theme bar BELOW X7's calibrated 1.95pp noise floor. Re-run: full composite beats its best single signal by +4.51%/yr but CI95 [-0.14%, +9.12%] includes zero -> NULL. Only the full 7-theme arm clears X7's LS bar of 2.14. Theme IC does NOT predict marginal contribution: `size` has the WORST IC (-0.30) and carries the composite. Equity N 84 -> 104; trials haircut 2.977 -> 3.048. |
| LOO | X | Pre-registered held-out leave-one-out | DONE | NULL |  | HANDOFF_edge_audit.md session 7 | 2026-08-06 | pipeline builder | Select the best LOO arm on a decide half, measure only that arm on the held-out half, both directions. Drop momentum: -1.30%/-0.706. Drop capital_discipline: +0.20%/-0.201. Neither clears the committed MIN_HOLDOUT margins; different theme selected in each direction. 4 of 7 arms CHANGE SIGN between halves, which is why session 6's exploratory full-sample LOO did not replicate. `size` is worst in both halves independently (-2.64%, -3.46%) - corroborated, not pre-registered. equity N 104 -> 111. |
| X4 | X | Factor-ETF benchmark | DONE | NULL | 6b1dff9 | HANDOFF_free_analysis.md | 2026-08-04 | human | +9.21pp vs the 4-factor blend but t=1.10 and negative in the first half. Margin not demonstrated. |
| X5 | X | Bootstrap the pipeline | OPEN |  |  |  |  | human | No write-up, no commit anywhere in the corpus. |
| X6 | X | Structural-break test | DONE | NULL | bd495f5 | HANDOFF_free_analysis.md | 2026-08-03 | human | Structural-break test null under Holm-Bonferroni; the 2012 story is NOT confirmed. |
| X7 | X | Placebo through the pipeline | DONE |  | 1caacec | HANDOFF_edge_audit.md | 2026-08-06 | human | 3 of the project's 4 thresholds are UNCALIBRATED, 1 survives. Re-run at true N=84 CONFIRMED. |
| X8 | X | Replicate on JKP / another country | DONE |  | 7edf594 | HANDOFF_free_analysis.md | 2026-08-04 | human | REPLICATES on another vendor's data in another country (JKP, Europe). |
| S1 | S | Fix value theme inputs | DONE | REJECTED |  | HANDOFF_signals.md | 2026-08-06 | human | Both arms REJECTED on the full 69-date panel. Dropping book_to_price RAISES the value theme IC t 0.84->1.57 and makes the composite WORSE in both directions (-0.207/-0.079 t); swapping for neg_ev_ebitda likewise. Third instance of the P6 rule: a theme's IC and the composite it feeds move opposite ways. |
| S2 | S | Register cash_op_prof | DONE | NULL |  | HANDOFF_signals.md | 2026-08-06 | human | Audit premise WRONG: not untested (settings.py already recorded t +0.22) and not empty (95.3% coverage). Full-universe re-run replicates the rejection: median IC +0.0026, t +0.84 vs X7 calibrated 2.71; corr 0.27-0.44 so distinct yet uninformative. SHIPPED as measured-not-scored (roe_ttm precedent); composite bit-identical either way. |
| S3 | S | Rebuild the insider score | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| S4 | S | Growth theme carries zero weight | DONE | NULL |  | HANDOFF_signals.md | 2026-08-06 | human | Observation TRUE (no growth key in WEIGHTS_ESTABLISHED) but adding it fails the pre-registered both-directions rule: zeroing growth costs -0.263 t one way and HELPS +0.549 t the other. Speculative branch: no evidence to remove it either. Book argues against too: only 15/25 names kept, median cap $1.09B->$1.73B, tilting to momentum/thematic. Now a tested decision, not an omission. |
| S5 | S | Hierarchical shrinkage | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| S6 | S | Factor momentum on themes | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S7 | S | Pre-registered interactions | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| S8 | S | Signal-freshness weighting | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S9 | S | Data-staleness conditioning | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S10 | S | Downside-exclusion screen | OPEN |  |  |  |  | auto | only forward references -- mentioned as a dependency, never written up |
| S11 | S | Horizon ensemble | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S12 | S | Rank within bucket | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S13 | S | Vol-targeted weighting | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S14 | S | No-trade band on net alpha | OPEN |  |  |  |  | auto | only forward references -- mentioned as a dependency, never written up |
| S15 | S | Sector-relative value only | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S16 | S | Decompose net issuance | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S17 | S | Decode the rest of EVENTS | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| S18 | S | Short interest as interaction | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S19 | S | MD&A anomaly left on the table | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S20 | S | Rank composite, not z-sum | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S21 | S | Winsorise before standardising | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S22 | S | Term structure of the signal | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S23 | S | Exit rule for the equity book | OPEN |  |  |  |  | auto | only forward references -- mentioned as a dependency, never written up |
| S24 | S | Ensemble across draws | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S25 | S | Point-in-time sector map | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| S26 | S | Read the twenty worst holdings | DONE |  | 6eb5a2f | HANDOFF_free_analysis.md | 2026-08-04 | human | Pattern named, then PARTLY REFUTED and retracted in place. Refines low_risk. |
| S27 | S | Weight recent observations more | OPEN |  |  |  |  | auto | only forward references -- mentioned as a dependency, never written up |
| S28 | S | Distribution, not just the mean | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O1 | O | Exit sweep incl. random entries | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| O2 | O | Cross-sectional VRP | DONE | REJECTED | bd495f5 | HANDOFF_free_analysis.md | 2026-08-03 | human | Audit of the existing implementation, NOT an independent test. Nothing clears the gate; adopted: []. |
| O3 | O | Delta-hedged vs idio vol | OPEN |  |  | HANDOFF_free_analysis.md |  | human | Held until R1 returned (HANDOFF_free_analysis:392). R1 has now returned - UNBLOCKED. |
| O4 | O | Expected idio skewness | OPEN |  |  | HANDOFF_free_analysis.md |  | human | Held until R1 returned (HANDOFF_free_analysis:392). R1 has now returned - UNBLOCKED. |
| O5 | O | Volatility of volatility | OPEN |  |  | HANDOFF_free_analysis.md |  | human | Held until R1 returned (HANDOFF_free_analysis:392). R1 has now returned - UNBLOCKED. |
| O6 | O | Cheapest-on-surface selection | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| O7 | O | Earnings straddles | OPEN |  |  | HANDOFF_free_analysis.md |  | human | Held until R1 returned (HANDOFF_free_analysis:392). R1 has now returned - UNBLOCKED. |
| O8 | O | Index VRP - run existing bt | DONE | INCONCLUSIVE | ce03500 | HANDOFF_optionsbot.md | 2026-08-03 | human | SPY INCONCLUSIVE (excess Sharpe 0.14 vs a 0.50 bar); QQQ and IWM REJECTED. |
| O9 | O | IV rank as sell-timing | DONE | REJECTED | 22aa0ac | HANDOFF_optionsbot.md | 2026-08-04 | human | Effect flips sign across SPY/QQQ/IWM. Per the audit's pre-registration the short-vol question is CLOSED. |
| O10 | O | Passive-limit fill model | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O11 | O | Portfolio layer for single-leg | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O12 | O | Fractional Kelly / ruin | OPEN |  |  | HANDOFF_edge_audit.md |  | human | Unblocked by B3 (tail and sizing work). No write-up yet. |
| O13 | O | Anti-signal decomposition | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
| O14 | O | Tick flow, alert days only | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O15 | O | Re-mine beyond 90 DTE | DONE |  | 06e44fe | HANDOFF_miner_remine.md | 2026-08-06 | human | Re-mined to 200 DTE, 100 names deep; a silent symbol-year loss was found and fixed. |
| O16 | O | Is term_slope a front-IV level? | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O17 | O | Earnings filter for the long arm | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O18 | O | Spread-conditional cost model | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O19 | O | Cheap-contract sizing artefact | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O20 | O | PIT option-universe selection | DONE | ADOPTED | 0fb22a8 | HANDOFF_edge_audit.md | 2026-08-05 | human | As a reported partition; the audit's expectation is REFUTED. Does NOT rescue the signal. |
| O21 | O | Dividends / early exercise | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O22 | O | Capacity-constrained replay | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O23 | O | Exits vs the underlying | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O24 | O | Is term_slope an earnings cal? | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O25 | O | Sell the wing after the move | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O26 | O | Raise the per-bucket floor | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| U1 | U | Stock composite -> options entry | OPEN |  |  | HANDOFF_edge_audit.md |  | human | DO NOT RUN AS WRITTEN (2026-08-06, session 6). U7 was the audit's own 'strictly easier bar' for the same hypothesis and it FAILED with a mechanism: on the 187-name options universe the composite decile is largely a market-cap sort, so it carries no alert-specific information (interaction vs control -0.08pp). Reopen only with a composite built WITHIN the options universe or with size neutralised. |
| U2 | U | Options surface -> stock signals | OPEN |  |  | VALQUO_ACTION_PLAN.md |  | human | Session 7, runs FIRST of the unification. Replaces the dead WRDS lever. |
| U3 | U | Convex overlay as insurance | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| U4 | U | One decision object | OPEN |  |  | VALQUO_ACTION_PLAN.md |  | human | Deliberately gated on U1/U2 - do not ship over two disconnected engines. |
| U5 | U | Tax-aware arm allocation | DONE |  | 7edf594 | HANDOFF_free_analysis.md | 2026-08-04 | human | Decided, and the headline corrected. Roth +17.4% vs taxable +4.86% - a 3.6x lever. |
| U6 | U | CSPs in, covered calls out | OPEN |  |  | VALQUO_ACTION_PLAN.md |  | human | Session 7 (the unification), after U1. |
| U7 | U | Composite as an options veto | DONE | REJECTED | 3feeded | HANDOFF_edge_audit.md | 2026-08-06 | human | was OPEN -> now DONE/REJECTED. Join built and pinned (most recent rebalance <= alert date; tested against its own look-ahead variant). Coverage 98.1% of alerts / 97.8% of names, measured. The veto HURTS in all three pre-registered cells (lift -0.57pp / -1.04pp / -0.44pp, all CIs straddling zero) because the composite's BOTTOM decile is the 3rd most profitable (+10.64%). Interaction vs the 5-seed control -0.08pp: the composite describes the UNDERLYING, not the alert. Mechanism: inside 187 megacaps the composite decile is largely a market-cap sort ($62.7B -> $133.5B, D1->D9). |
| U8 | U | One risk budget across books | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| C1 | C | Backtest the model that ships | DONE | REJECTED | 6041e8f | HANDOFF_optionsbot.md | 2026-08-04 | human | REJECTED for both models. Found a LIVE bug on the way: Form 4 URLs pointed at XSL views, 597/597 empty. |
| C2 | C | Universe is inverse of target | DONE | ADOPTED | 6041e8f | HANDOFF_optionsbot.md | 2026-08-04 | human | ADOPTED (correctness). --universe legacy still reproduces the old behaviour. |
| C3 | C | --bots reversion does nothing | DONE | ADOPTED | f5c5a37 | HANDOFF_optionsbot.md | 2026-08-03 | human | ADOPTED (correctness). --bots reversion did nothing and reported success. 6 tests. |
| C4 | C | Wire the tracking loop | DONE | ADOPTED | f5c5a37 | HANDOFF_optionsbot.md | 2026-08-03 | human | ADOPTED (correctness). 18 tests. run_review now refuses an all-NULL table. |
| C5 | C | PIT universe on real data | DONE |  | 52091d6 | HANDOFF_edge_audit.md | 2026-08-04 | human | PASSED, after fixing a units bug that returned an EMPTY universe on all 27 dates. Median 32.1% invisible. |
| C6 | C | Three undeployed fixes | BLOCKED | ADOPTED |  | HANDOFF_optionsbot.md |  | human | ADOPTED-in-repo and still UNDEPLOYED. Blocker: Don must scp quant_bots/data/*.py off the box. |
| C7 | C | Widen the CI gate | DONE | ADOPTED | a2894a8 | HANDOFF_edge_audit.md | 2026-08-03 | human | Widened the CI gate. Mattered because the pipeline auto-merges to main and Render deploys. |
| P1 | P | Estimate capacity | DONE |  | 6eb5a2f | HANDOFF_free_analysis.md | 2026-08-04 | human | Capacity ~= $23M, and that is an UPPER bound. |
| P2 | P | Model user crowding | OPEN |  |  |  |  | auto | only forward references -- mentioned as a dependency, never written up |
| P3 | P | Design for a 37% hit rate | DONE |  | 52f523d | HANDOFF_appfixes.md | 2026-08-06 | human | Was OPEN ('prose mentions only') -> DONE. `web/payoff.py` + 30 tests. Distribution measured first: hit 35.3%, median trade -52.2%, 25.0% at least double and those are 86.8% of all winnings. Streak rule derived from a MEASURED table (control seq, n=6,032) not the Bernoulli formula, because outcomes cluster: design effect 2.667 vs shuffled-null p95 1.244, p<0.001. Verdict can return unusual/rare/beyond_record and refuses below 10 closed trades. Sizing half (O12) NOT done - no banked result to render, routed. |
| P4 | P | Fix the track's rules | DONE | FIXED |  | HANDOFF_edge_audit.md session 7 | 2026-08-06 | pipeline builder | seed_book only ever INSERTED, so the paper index was an ever-growing union of everything ever held. Departed names are now CLOSED into paper_index_closed (not deleted - deleting is reverse survivorship bias), a truncated export closes nothing, inception spans closed stints, index_summary gains a `realized` block. Daily point is still an open-holdings snapshot: NOT chained, flagged in detail.scope. 45/45 paper-track tests. |
| P5 | P | Decide the claim before R1 | DONE |  |  | HANDOFF_edge_audit.md |  | human | Pre-committed CLAIM A/B language rule; CLAIM A's text ships. No section of its own - weakest DONE here. |
| D1 | D | Sharadar direct at $29/mo | DONE | REJECTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | DON'T BUY. Bundle is $29/mo verified, but sharadar.com/terms is personal-use only and forbids commercial use of the data 'or any derivation'. The 18 GB freeze already runs the panel keyless, so $29 buys continuation, not the corpus. |
| D2 | D | ThetaData tier + licence | DONE | REJECTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | DON'T BUY. Individual $40/$80/$160 is 'personal use only, no business use'; lawful commercial starts ~$250/mo + OPRA firm registration. Would replace a greeks layer already built and validated, for a book whose entry signal is dead (R2). |
| D3 | D | Fetch the free factor datasets | DONE |  | bd495f5 | HANDOFF_free_analysis.md | 2026-08-03 | human | COMPLETE - every dataset R1 requires is present and verified. |
| D4 | D | Cboe Open-Close Volume Summary | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| D5 | D | ORATS | DONE | DEFERRED |  | HANDOFF_data_spend.md | 2026-08-06 | human | DON'T BUY YET. $99/$199/$399 verified; bulk historical quote-only; licence NOT stated on the pricing page (ambiguous, left ambiguous). Gate is O2/O6 and neither has returned anything. |
| D6 | D | Estimate-revision situation | DONE | REJECTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | STAY PARKED. No retail point-in-time revisions exist at any price. Path is IBES via WRDS, so D6 and D7 are ONE decision, not two. |
| D7 | D | WRDS reality check | DONE | REJECTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | NOT PURCHASABLE. Verified on WRDS's own page: seven account types, every one requiring affiliation with a subscribing institution. No alumni, no unaffiliated, no corporate. Resolves the DISPUTED note - the action plan's 'dead end' claim is correct. |
| D8 | D | What not to buy | DONE | ADOPTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | Decline D1, D2, D5, D6, D7. Buy-nothing case is strong: freeze + free factor libraries + the existing options cache cover everything on the critical path; S series is 2 of 28 with none blocked on a purchase. Own-data finding added: the -1 OI sentinel manufactures fake gamma walls, which is what retail GEX vendors infer from. |
| D9 | D | Options costs are a step change | DONE | ADOPTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | Calibration recorded, nothing to buy. Equity book 37bps vs 236bps breakeven (6.4x) does NOT transfer to options at 4.7-12.6% of premium. Percentages are the audit's literature citations, not measured here. |
| D10 | D | Freeze verification + legend | DONE | ADOPTED | a2894a8 | HANDOFF_edge_audit.md | 2026-08-03 | human | Adopted as record; all six schema questions settled. Found D10-a, a defect NOT in the audit. |
| M1 | M | Research log with real N | DONE | ADOPTED | 2f3529b | HANDOFF_edge_audit.md | 2026-08-03 | human | N = 8 (shipped) vs 84 (measured). Consequence fired: the edge does NOT clear the Deflated Sharpe. |
| M2 | M | Clustered inference default | OPEN |  |  |  |  | human | No genuine mention. HANDOFF_STATUS's 'the audit's M2' is CODE_AUDIT.md's M2 - a different document. |
| M3 | M | Guards with known-bad fixtures | DONE | ADOPTED | d0aad64 | HANDOFF_optionsbot.md | 2026-08-06 | human | tests/test_guards.py, 36 tests: 35 pass, 1 XFAIL. Census of 34 guards; 29 of 30 testable ones fire. Two defects found and deliberately NOT fixed (year_files blind to a vanished symbol-year; no field-level schema guard). |
| M4 | M | Live-replay harness | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| M5 | M | Protocol for tail-hedge tests | DONE |  | 7edf594 | HANDOFF_free_analysis.md | 2026-08-04 | human | Protocol WRITTEN, which was the deliverable - it is not an evaluation of any hedge. |
| M6 | M | Results-file schema assertion | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
