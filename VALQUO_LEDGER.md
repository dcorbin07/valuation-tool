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
* **src** — `auto` = mechanically proposed and not yet read by a person; treat
  as a lead, not a fact. **Anything else** (`human`, or a lane name such as
  `pipeline builder`) = hand-verified against the write-up; `build_ledger.py`
  will NOT overwrite it, only report a disagreement. The test is *"is it
  `auto`?"*, not *"is it `human`?"* — it used to be the latter, which quietly
  demoted every row a lane had signed with its own name.

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
5. **A multi-item commit subject donates one item's verdict to every other id
   in it.** `275e9af` reads *"O16/O24 RESULTS: O24 is a NULL; O16 stopped at
   its own reproduction gate"*. The word `NULL` is **O24's** verdict, but the
   subject names both, so the proposal marks **O16 DONE** — an item that
   deliberately returned no verdict at all. Found 2026-08-08.
6. **`DEFERRED` is in the DONE vocabulary, so "deliberately deferred" reads as
   finished.** B23's own heading is `## B23 — DEFERRED, deliberately` and its
   body opens *"Not done, and not forgotten."* The proposal says DONE.
   Found 2026-08-08.

`build_ledger.py` encodes traps 1–4. **Traps 5 and 6 are NOT encoded** — both
were left as reported disagreements rather than fixed, because the fix is a
guess about commit-subject grammar and the human row already wins. Re-check
them on every refresh.

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

**C6 closed 2026-08-07 (same lane, separate task) — and it is the one row the ledger got wrong,
in an instructive direction.** The row named a blocker requiring Don and the Oracle box
("must scp quant_bots/data/*.py off the box"). That blocker was never real: the missing sources
sat in `options-bot/handoff/quant_bots.zip`, **tracked in this repository the entire time**, and
were recovered byte-identical without touching the box — which is as well, since the box is now
decommissioned. **The lesson is narrow and worth stating: "the only copy is on machine X" is a
claim about where you looked, not about where the file is.** Nobody had grepped the tracked zips.
`options-bot/.gitignore:34` (`!handoff/*.zip`) is the line that saved the project, and it should
not be tidied away.

## Refresh of 2026-08-08 (r1 lane) — counts, and the three ways `--write` was destroying this file

**`--write` had never been run since the out-of-band rows were added, and running it would have
deleted eight of them.** The refresh was done only after fixing that. All three defects share one
signature — the script curating content it did not write — against a docstring promising the
opposite (*"It never silently overwrites a human-verified row"*):

1. **`render()` iterated the 134 audit ids, so any row without an audit id was DROPPED.** That is
   all eight out-of-band rows: `OOB1`/`OOB2`/`OOB3` and the project's own pre-registered
   experiments `LOO`, `SELRULE`, `HACFLOOR`, `MLPREREG`, `MLCOMB` — Sessions 7–11 and the public
   fair-value leak closure. `OOB1`'s note had been carrying the warning *"build_ledger.py
   regenerates from the 134 audit ids only and will DROP this row"*: the defect was **documented in
   the data instead of fixed**, so the next person to type `--write` would have lost the rows and
   the warning together.
2. **The preserve check was `src == "human"` exactly**, so the seven rows signed
   `src=pipeline builder` were treated as machine-generated and rewritten from the proposal —
   `B8` and `P4` lost their `FIXED` verdicts that way. Now anything that is not the literal
   `auto` is protected, so a new `src` spelling degrades to *protected*, never to *overwrite me*.
3. **`render()` emitted the hard-coded `LEDGER_HEADER`**, deleting any prose written under it —
   here the entire "Ledger accuracy" section below, i.e. R3's stale-figure note and the C6 lesson.
   The header is now read back from the file.

Pinned by `tests/test_build_ledger.py` (**20 assertions**, incl. a round-trip of the real file).
**After the fix the whole refresh moved one cell**: `D4`'s note, `no mention anywhere` →
`prose mentions only` (`HANDOFF_data_spend.md:161`, genuine). Status unchanged, still OPEN.

**The fix for defect 3 had a bug of its own, caught by its own test.** The first version split the
header at the first line starting with `|` — which, once this very counts table was added below,
truncated the header there and deleted every section after it. The boundary is now the table's
exact `COLS` header line. The test was strengthened at the same time: it had asserted only that
the header was non-empty and contained no table rows, **both true of a truncated header**, so it
now compares the whole prose block byte-for-byte.

### Counts by series and status — 134 external-audit items

| series | OPEN | IN PROGRESS | DONE | BLOCKED | SUPERSEDED | total |
|---|---|---|---|---|---|---|
| S | 24 | 0 | 4 | 0 | 0 | 28 |
| B | 1 | 1 | 24 | 0 | 0 | 26 |
| O | 19 | 0 | 6 | 1 | 0 | 26 |
| R | 0 | 0 | 6 | 4 | 0 | 10 |
| D | 1 | 0 | 9 | 0 | 0 | 10 |
| X | 2 | 0 | 6 | 0 | 0 | 8 |
| U | 6 | 0 | 2 | 0 | 0 | 8 |
| C | 0 | 0 | 7 | 0 | 0 | 7 |
| M | 3 | 0 | 3 | 0 | 0 | 6 |
| P | 0 | 0 | 5 | 0 | 0 | 5 |
| **ALL** | **56** | **1** | **72** | **5** | **0** | **134** |

**72 of 134 DONE (53.7%).** Hand-verified 91/134; 43 rows still `src=auto` (leads, not facts) —
and **every one of those 43 is OPEN** (S 24, O 14, U 2, M 2, D 1), so the auto rows are entirely
the untouched backlog rather than unreviewed claims. No `DONE` row anywhere rests on machine
evidence alone.

**The backlog is lopsided, and the counts are what make it legible:** `S` (4/28 DONE) and `O`
(6/26) hold **43 of the 56 OPEN items**. What remains is overwhelmingly signal ideas and options
studies, not corrections — `B` 24/26, `C` 7/7, `D` 9/10 and `P` 5/5 are essentially finished. The
other 13 OPEN items are spread thinly across `U` (6), `M` (3), `X` (2), `B` (1), `D` (1).

Plus **8 out-of-band rows** (7 DONE, 1 PRE-REGISTERED), counted separately and deliberately: they
are real work, but folding them in would silently change what "of 134" has always meant.

Landings of the last two days are all present and were verified individually rather than assumed:
`HACFLOOR` (session 10), `MLPREREG` + `MLCOMB` (session 11), `O16`, `O24`, `P2`, `C6`, `OOB1`
(the leak closure). **Every one had already been recorded by the lane that did it** — rule 1 of
the contract is being followed.

### Where sources disagree — 21 items, and the human row wins all 21

The proposal is mechanical and its asymmetry is deliberate (a wrongly-OPEN row costs a re-check;
a wrongly-DONE row stops work happening). Every disagreement below was checked against the
write-up. **No status changed.** Four causes:

| cause | items | why the human row is right |
|---|---|---|
| **Script proposes DONE, item is not done** | `B13`, `B23`, `O16` | The dangerous direction, and all three are false. `B13` is "PARTIALLY FIXED and labelled so" — `MIN_AVG_DOLLAR_VOLUME` still cannot bind. `B23` is trap 6. `O16` is trap 5 and **stopped at its own reproduction gate with no verdict**. |
| **Script proposes IN PROGRESS, item is DONE** | `B9`, `O2`, `U5`, `D8`, `D9`, `M5` | "section exists, no completion word found" — the write-ups conclude in words outside `DONE_CUES` (`RELABELLED`, `adopted: []`, "Protocol WRITTEN"). Vocabulary gap, not a status question. |
| **Script proposes OPEN, item is DONE** | `P2`, `P3`, `P5`, `D1`, `D2`, `D5`, `D6`, `D7` | The collision guards firing as designed. `P2` **has** headers (`HANDOFF_crowding.md:1`, `HANDOFF_STATUS.md:53`) but `P` is a colliding series and neither heading carries an audit cue. `D1`/`D2`/`D5`–`D7` are written up as **table rows** in `HANDOFF_data_spend.md`, not headings, so there is no HEADER evidence to find. |
| **Script proposes OPEN, item is BLOCKED** | `R4`, `R5`, `R6`, `R8` | Blocked on **lane ownership**, not on evidence: they sit in `valuation/edge/**`, which `AGENTS.md` assigns to the pipeline-builder lane. The script cannot see an ownership boundary. Defensible either way; kept as BLOCKED because that is what a reader needs to know. |

**One row is stale and is still not this lane's to edit:** `R3`'s note reads *"Shrinks every
options t ~1.36x"*; the corrected figure is **√2.212 = 1.487×** on the 3,885-trade book (1.36×
came from the pre-correction 3,042-trade book). Carried forward from the 2026-08-07 audit below,
unedited for the second refresh running. **Owner: whoever owns R3.**

## Refresh

    python scripts/build_ledger.py            # proposal + counts, writes nothing
    python scripts/build_ledger.py --write    # refresh src=auto rows only
    python scripts/build_ledger.py --evidence S12   # show why S12 sits where it does

`VALQUO_LEDGER.md` is deliberately **not** in the scanned corpus (`HANDOFF_*.md` + `CLAUDE.md`,
`RUN_RULES.md`, `VALQUO_ACTION_PLAN.md`, `AGENTS.md`), so nothing written here feeds back into the
next proposal. A handoff file that enumerates ids **is** scanned — wrap those regions in
`<!-- ledger:ignore -->` … `<!-- /ledger:ignore -->`.

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
| X8 | X | Replicate on JKP / another country | DONE | REPLICATES | 7edf594 | HANDOFF_free_analysis.md | 2026-08-04 | human | REPLICATES on another vendor's data in another country. Untuned 5-theme equal-weight composite, JKP Global Factor Data, monthly vw_cap, 1999-01 -> 2025-12, NW(12): Japan +2.05%/yr (t 3.85), developed Europe +3.36% (t 4.30), world ex-US +3.37% (t 5.03); all 15 European countries positive, 12 of 15 clear t>2. THE USA IS THE WEAKEST REGION TESTED (t 2.35) - the theme structure is not a US artifact. Reported not buried: quality (-0.12) and momentum (+0.88) do NOT generalise to Japan, so the composite replicates while its composition does not; only 5 of 7 themes map (insider/institutional have no analogue); JKP earns +2 to +3.4%/yr vs Valquo's +20.4% long-short, a factor of six on a different instrument, so this corroborates the PREMIA and NOT the magnitude. CC BY-NC 4.0 research-only, can never ship. **This result was absent from CLAUDE.md and HANDOFF_STATUS.md until session 8 (2026-08-07) added it; two sessions treated a passed test as pending.** |
| SELRULE | X | Test the LOO SELECTION RULE (stability vs argmax) | DONE | NOT ANSWERABLE - declined |  | HANDOFF_edge_audit.md session 8 | 2026-08-07 | pipeline builder | Session 7 nominated a pre-registered test of the selection rule. Answerability settled BEFORE any run, on the already-published session-7 arm table, so it cost ZERO trials. NOT ANSWERABLE on the Sharadar panel, three reasons: (a) a 3-block split gives 22-date blocks where sigma is 1.57pp against a 1.00pp committed margin - pure noise clears it 26.1% of the time and power is 50.6%; (b) Monte Carlo over the design shows the stability and argmax rules select the SAME arm 90% of the time and reach a different verdict on only 5.1% of panels; (c) DECISIVE and assumption-free - one panel is one draw, and a paired sign test at n=1 has a minimum achievable p of 0.50, so no outcome could ever have been quotable. TEST DELIBERATELY NOT RUN; equity N stays 116 (DSR 0.8674) instead of 123 (0.8609). ANSWERABLE on X8's JKP data, which is already on disk: 16 held-out countries give 16 draws, sign test reaches alpha 3.84% at >=12/16, power 79.8% at p=0.80 but only 8.5% at p=0.55 - can settle "substantially better", never "slightly better". Pre-registered in full, blind; session 9 executes. **SESSION 9 (2026-08-07) EXECUTED IT AND THE ANSWERABILITY CLAIM IN THE PREVIOUS SENTENCE IS VOID - "16 independent draws" was an assumption, never measured, and it is FALSE.** The clustering gate (valuation/edge/cross_country.py) was built, tested and committed BEFORE the measure set was touched. Clustering is measurable on 10 of 10 arm-pairs (design effects 3.97-8.27 vs shuffled-null p95 ~1.13), rho 0.198-0.484, **n_eff 1.94-4.03 countries out of 16**. Calibrated critical count is **17 of 16**; even a unanimous 16/16 gives p 0.0546 (400k draws, se 0.0004), so the rejection region is EMPTY and the design's power at alpha 5% is ZERO. **The pre-registered 12/16 bar carries a true alpha of 28.7%, not 3.84% - a 7.5x understatement caught only because the gate was built first.** Separately: **NO CONTRAST** - both rules select `size` on usa, so every paired difference is identically zero (pre-registered outcome; not a NULL, not a tie); 4 of 5 arms are same-sign across both usa halves so the stability constraint does not bind. X8's own headline is UNAFFECTED - it tests each region separately with NW(12) and never pooled countries into a count. Equity N 116 -> 121 as pre-committed (DSR 0.8628, sqrt(2 ln 121) 3.097). **THE QUESTION IS CLOSED ON BOTH DATASETS; do not re-open without new data.** |
| HACFLOOR | X | Re-derive X7 calibrated long-short floor on the HAC statistic | DONE | CLEARS - headline 2.620 vs a re-derived floor of 2.2837 |  | HANDOFF_edge_audit.md session 10 | 2026-08-07 | pipeline builder | X7 calibrated 2.14 on the NAIVE t; R9 then made the HAC t the number the project quotes (Ljung-Box rejects independence at p 0.036), so a bar and a number from different estimators had been compared ever since. Cause was a WRITER bug: quantile_backtest has computed long_short_tstat_nw on every draw since R9 and scripts/placebo.py never stored it - and X7 raw draws were never saved, so all 100 had to be re-run. Same panel, same seeds 1000-1099, same instrument, costs measured, procedure pre-committed in PREREG_session10_hac_floor.md before launch; sharded across 4 processes with the merge proving bit-for-bit reproduction of the serial draws. RESULT: **HAC floor (p95) 2.2837, shipped HAC t 2.61991 CLEARS at empirical p 0.03.** But BOTH moves go against the strategy - the HAC floor is higher than the naive floor (2.28 vs 2.14) while the real HAC t is lower than the real naive t (2.620 vs 2.836) - so **the margin over the floor falls 0.692 -> 0.336, roughly half. Quote 2.620 vs 2.28, never vs 2.14.** Old mismatch was mild: noise clears 2.14 on the HAC statistic 6% of the time vs the 5% intended. FREE BY-PRODUCT and the stronger number: top-decile alpha HAC t now has a floor (2.2913) and the shipped +4.376 sits ABOVE ALL 100 noise draws (emp p 0.00). Control reproduces X7 p95 2.14 and max 3.44 to the digit; the ls_t>=2.0 rate comes back 7% vs the recorded 8%, one draw, NOT rounding, and unreconcilable because X7 draws do not exist - reported, moves no floor. Trial cost ZERO, equity N stays 121. Artifact data/free_analysis/PLACEBO_HAC.json retains all 100 draws. |
| MLPREREG | X | ML tree combiner (roadmap #16) - PRE-REGISTERED, not run | PRE-REGISTERED | design committed blind, no training runs | ec6c01d | PREREG_ml_combiner.md | 2026-08-07 | pipeline builder | Design only, committed BEFORE any model was fit. Features: the SEVEN deployed theme z-scores only - NOT the 56 raw signals, NOT low_risk or sentiment (those would be theme-membership changes smuggled in as features). Target: cross-sectional RANK of fwd_ret, 63d, corrected 69-date panel. Selection never touches the measurement set: all 8 grid points scored by CPCV WITHIN a decide half, the single winner refit and measured ONCE on the held-out half, both directions - the direct answer to X7 finding that CPCV adoption manufactures ~+1.4 of long-short t when selection and measurement share a panel. HistGradientBoostingRegressor, grid = max_depth{2,3} x lr{0.03,0.10} x max_iter{100,300} = 8 points, everything else held constant at anti-overfit values. THE GRID IS PRICED UP FRONT: 8 points -> equity N 129, headline DSR 0.8556; 128 points -> N 249, DSR 0.7716; **230 points -> N 351, DSR 0.7213, BELOW X7 calibrated floor of 0.7216** - a grid that size would not test the model, it would destroy the incumbent evidence as a side effect. Scored on calibrated bars only (HAC long-short t vs the session-10 floor, 1.95pp alpha margin); PBO explicitly NOT a criterion. Ambiguous is NULL, no re-runs. Expectation recorded first: NULL 70/30. Trial cost 8 rows is owed WHEN IT RUNS, not now.  **EXECUTED SESSION 11 (2026-08-08) - VERDICT REJECTED.** See the MLCOMB row. |
| MLCOMB | X | ML tree combiner (roadmap #16) - EXECUTED | DONE | REJECTED |  | HANDOFF_edge_audit.md session 11 | 2026-08-08 | pipeline builder | Register executed UNMODIFIED (PREREG_ml_combiner.md, blind at ec6c01d; execution protocol and executor committed before the run at 9b1abfc). REJECTED by the registered rule - worse on alpha in BOTH directions: decide-early/measure-late tree +1.88% vs linear +11.58% (d -9.70pp, d_HAC_t -2.118); decide-late/measure-early tree -2.66% vs linear +2.82% (d -5.48pp, d_HAC_t -2.877). All three ADOPT criteria fail in both. **THE FINDING IS STRONGER THAN THE VERDICT: the tree monotonicity is +0.382 and +0.842, and negative is well-ordered, so its top decile UNDERPERFORMS its bottom decile out of sample.** The run carries its own control - the linear arm on the IDENTICAL rows through the IDENTICAL quantile_backtest call is well-ordered (-0.903, -0.855) and the equal-weight benchmark matches between arms to four decimals - so it is the model, not the harness. NOT a fitting failure either: all 16 grid x direction cells had POSITIVE decide-half CPCV out-of-sample rank IC (+0.011 to +0.024) across 15 purged paths, so the model generalises inside the decide half and REVERSES across the boundary. The two directions selected OPPOSITE ENDS of the grid, monotonically - capacity helps in one half and hurts in the other. Quote beside the param-search precedent (+8.43%/yr in-search -> -0.04%/yr locked hold-out): selection on this panel does not merely fail to generalise, it can generalise backwards. Does NOT vindicate the flat 1/7 linear form and does NOT close roadmap #16 - a raw-signal or different-model-class variant is a NEW pre-registration inheriting this reversal as its prior. Trial cost paid as registered: equity N 121 -> 129, DSR 0.8628 -> 0.8556, sqrt(2 ln 129) 3.118. |
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
| O16 | O | Is term_slope a front-IV level? | DONE |  |  | HANDOFF_optionsbot.md | 2026-08-08 | human | VERDICT **IS DISTINCT** (2026-08-08 re-run; the ledger's five-word vocabulary has no entry for it, so the column is blank and the write-up's own word is quoted here, the X8 convention). Was BLOCKED/INCONCLUSIVE at 2026-08-07 (41a0294) -> now DONE. THE BLOCKER WAS REAL AND WAS REPAIRED, NOT WAIVED: the register's gate compares recomputed term_slope against the BANKED value, that comparison fails at 86.435% and can NEVER pass, because the drifted rows' inputs no longer exist anywhere. So a chain freeze was built first (valuation/edge/options_freeze.py, 42 tests, replay pin at theta_bulk's single load choke point) and the verdict is delivered on the REFROZEN book, where atm_front, atm_mid and term_slope are recomputed together from one frozen store and are mutually consistent by construction. 3,885 of 3,885 rows (100% of the book), 186 names, 118 months, 0 errors, 0 drift, under a replay pin re-verified afterwards at 1,429/1,429 symbol-years clean. Spearman(term_slope, atm_front) -0.53966, date-block CI95 [-0.5740, -0.5022], entirely below the committed 0.60 distinct bar. THE VERDICT HINGES ON THE PRE-REGISTERED CHOICE OF SPEARMAN AND MUST NEVER BE QUOTED WITHOUT IT: Pearson is -0.82793, which CLEARS the 0.80 level bar, so the same data under Pearson returns the OPPOSITE verdict. Variance shares (front 1.883, mid 0.611, -2cov -1.494) exceed 1 because the legs co-move at +0.791 and are meaningless without the covariance term. Predictive arm was informative this time and corroborates: the residual of term_slope on atm_front predicts BETTER (+0.07034) than raw term_slope (+0.05673) while atm_front alone predicts nothing (+0.01316, CI spans zero) - the opposite of a confound signature. Trial cost CHARGED AGAIN rather than waived, because last cycle's exploratory read had already shown this answer and the re-run was not blind: options N 164 -> 169. Equity N unchanged at 129. |
| O17 | O | Earnings filter for the long arm | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O18 | O | Spread-conditional cost model | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O19 | O | Cheap-contract sizing artefact | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O20 | O | PIT option-universe selection | DONE | ADOPTED | 0fb22a8 | HANDOFF_edge_audit.md | 2026-08-05 | human | As a reported partition; the audit's expectation is REFUTED. Does NOT rescue the signal. |
| O21 | O | Dividends / early exercise | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O22 | O | Capacity-constrained replay | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O23 | O | Exits vs the underlying | OPEN |  |  |  |  | auto | no mention anywhere in the corpus |
| O24 | O | Is term_slope an earnings cal? | DONE | NULL |  | HANDOFF_optionsbot.md | 2026-08-07 | human | NULL by the committed rule, on n=3,458 eligible alerts / 157 names / 118 months. R2 of term_slope on days-to-earnings buckets is 0.2144 with a date-block CI95 of [0.183, 0.248] - the WHOLE interval below the committed 0.25 bar - and the pre-committed monotone direction test gives Spearman +0.0018, CI [-0.051, +0.055], spanning zero. THE MECHANISM IS REAL BUT LOCAL: mean term_slope is -0.1916 in the 0-7d bucket against about +0.01 to +0.02 at 8-30d and -0.031 at 61-120d. It is a SPIKE, not a gradient, which is exactly why a categorical R2 nearly clears while a monotone rank test is near-blind. The direction test was the wrong shape for the effect and was committed before any data was seen, so the NULL stands as written. The no-new-data control runs the OTHER way: keeping only alerts >30d from earnings makes the book WORSE (-0.95% vs +3.81%, diff -4.76pp, CI [-7.59, -2.10], excludes zero), so the calendar is a different and better sort, not a redundant copy. RE-CHECKED 2026-08-08 on the REFROZEN feature and the NULL is RE-CONFIRMED rather than assumed: eligibility identical (3,458 of 3,885, 157 names, 118 months), R2 0.21443 -> 0.21555 with CI95 [0.1840, 0.2498] still wholly below the 0.25 bar, direction +0.00183 -> +0.00579 still spanning zero, every bucket mean moving by <=0.0014 (0-7d -0.19159 -> -0.19120). The refrozen book differs materially ROW BY ROW (13.6% of rows, up to 0.463) and barely at all IN AGGREGATE. No new arms: a re-measurement of already-paid registered arms on repaired inputs. |
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
| C6 | C | Three undeployed fixes | DONE | ADOPTED |  | HANDOFF_optionsbot.md | 2026-08-07 | human | CLOSED on the RECORDED branch of its own criterion: the Oracle box is decommissioned, so "deployed" is permanently n/a and all three fixes are instead verified by symbol and behaviour on every `deploy/preflight.py` run (exit 0, all three `ok`, measured 2026-08-07). THE BLOCKER WAS MISDIAGNOSED AND NO scp WAS EVER NEEDED: `options/data/*.py` was in `handoff/quant_bots.zip`, TRACKED in this repo the whole time (`options-bot/.gitignore:34` re-includes `handoff/*.zip` on purpose). Restored, byte-identical by sha256 to three other copies. Options suite 53-collected/14-errors -> 181 passing; 353 tests green (172 core + 181 options). State through 2026-07-31 restored from quant_data.tgz into the gitignored data/ tree. Docs swept with decommission notices; `*.tgz` and `options-bot2/` now ignored (both were one `git add -A` from being committed). |
| C7 | C | Widen the CI gate | DONE | ADOPTED | a2894a8 | HANDOFF_edge_audit.md | 2026-08-03 | human | Widened the CI gate. Mattered because the pipeline auto-merges to main and Render deploys. |
| P1 | P | Estimate capacity | DONE |  | 6eb5a2f | HANDOFF_free_analysis.md | 2026-08-04 | human | Capacity ~= $23M, and that is an UPPER bound. **CORRECTED 2026-08-08 by P2: the $23M is OVERSTATED 4.72x -> ~$4.9M.** `scripts/capacity.py:36` hard-codes BREAKEVEN_BPS=234.505 (pre-B6); the live measured breakeven is 134.113. Re-derived from P1's own published cells (fit reproduces all 15 to zero residual). Strategic conclusion UNCHANGED and strengthened -- still not a managed vehicle; Don's $1M account still clears (87bps vs 134bps). |
| P2 | P | Model user crowding | DONE |  |  | HANDOFF_crowding.md | 2026-08-08 | human | MODEL, no verdict (not a hypothesis test; no threshold pre-committed, stated as such). **Answer depends ~700x on WHICH book is published:** live Index (86 names, large-cap, median cap $22.2B) cancels the +7.17% alpha at a **$5.1B** cohort (~506k users at $10k); an all-cap top-25 at **$7.4M** (~740 users); top-10 at **$1.6M** (~160). **3 of P2's 4 premises are FALSE** -- the Index is OWNER-ONLY (`surfaces.py:80`), not 25 names (86; and `exit_rank=top_n*2` makes even the backtest book ~50), not small-cap (`LARGE_CAP_MIN=10e9`). Concentration+cap-floor is the whole lever; staggering entry is ~linear in days (4.97x at 5d). **Slippage is NOT the binding risk** -- McLean-Pontiff decay is ~3x larger at 10k users and unmodellable here. 6 BUGS FOUND incl. void +8.81%/t 5.74 live on the public /work page. **BUGS 1-3 FIXED 2026-08-08 (app-fixer lane, `HANDOFF_appfixes.md` session 19, branch `worktree-demo-link`): every P2-corrected figure swept from every RENDERED surface -- public `/work` and `/methodology`, the demo view, the shipped Index `method` payload and the track export. Capacity $23M -> $4.9M, breakeven 236bps/37bps -> 134bps/33bps, alpha +8.81%/t 5.74/109 windows -> +6.99%/t 3.98/68 windows, panel 2,710/110 -> 2,531/69. The `/work` long-short claim "t 3.52, above the 3.0 hurdle" was corrected to t 2.84 (NW 2.62), which is BELOW it. TWO FURTHER DEFECTS FOUND IN THE SAME SWEEP THAT P2 DID NOT LIST, both worse than any it did: the PUBLIC landing page rendered "Backtested net alpha +17.4%/yr" from a pre-B6 `settings.BOOK_CONFIGS[...]["measured"]` block (corrected +11.6%), and the taxable book's after-tax alpha was overstated SIXFOLD (4.86% -> 0.81%). Bugs 4-5 (`scripts/capacity.py`) remain OPEN, free-analysis lane; bug 6 remains OPEN.** |
| P3 | P | Design for a 37% hit rate | DONE |  | 52f523d | HANDOFF_appfixes.md | 2026-08-06 | human | Was OPEN ('prose mentions only') -> DONE. `web/payoff.py` + 30 tests. Distribution measured first: hit 35.3%, median trade -52.2%, 25.0% at least double and those are 86.8% of all winnings. Streak rule derived from a MEASURED table (control seq, n=6,032) not the Bernoulli formula, because outcomes cluster: design effect 2.667 vs shuffled-null p95 1.244, p<0.001. Verdict can return unusual/rare/beyond_record and refuses below 10 closed trades. Sizing half (O12) NOT done - no banked result to render, routed. |
| P4 | P | Fix the track's rules | DONE | FIXED |  | HANDOFF_edge_audit.md session 7 | 2026-08-06 | pipeline builder | seed_book only ever INSERTED, so the paper index was an ever-growing union of everything ever held. Departed names are now CLOSED into paper_index_closed (not deleted - deleting is reverse survivorship bias), a truncated export closes nothing, inception spans closed stints, index_summary gains a `realized` block. Daily point is still an open-holdings snapshot: NOT chained, flagged in detail.scope. 45/45 paper-track tests. |
| P5 | P | Decide the claim before R1 | DONE |  |  | HANDOFF_edge_audit.md |  | human | Pre-committed CLAIM A/B language rule; CLAIM A's text ships. No section of its own - weakest DONE here. |
| D1 | D | Sharadar direct at $29/mo | DONE | REJECTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | DON'T BUY. Bundle is $29/mo verified, but sharadar.com/terms is personal-use only and forbids commercial use of the data 'or any derivation'. The 18 GB freeze already runs the panel keyless, so $29 buys continuation, not the corpus. |
| D2 | D | ThetaData tier + licence | DONE | REJECTED |  | HANDOFF_data_spend.md | 2026-08-06 | human | DON'T BUY. Individual $40/$80/$160 is 'personal use only, no business use'; lawful commercial starts ~$250/mo + OPRA firm registration. Would replace a greeks layer already built and validated, for a book whose entry signal is dead (R2). |
| D3 | D | Fetch the free factor datasets | DONE |  | bd495f5 | HANDOFF_free_analysis.md | 2026-08-03 | human | COMPLETE - every dataset R1 requires is present and verified. |
| D4 | D | Cboe Open-Close Volume Summary | OPEN |  |  |  |  | auto | prose mentions only, no section, no commit |
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
| OOB1 | OOB | Public fair-value leak: the DB drops the refusal, and ~387 served names never get one | DONE | FIXED |  | HANDOFF_live_data_bugs.md | 2026-08-07 | human | OUT-OF-BAND, not one of the 134 audit items. Bug A REPRODUCED on the real 399-row production snapshot (refusing rank-1 STT republished $386.68083192601813 as 'blended') and FIXED: two columns + in-place migration; control bound HELD, 399 rows bit-identical. Bug B FIXED structurally but measured EMPTY -- 0 genuine refusals of 387 served names, so it removes no published number today; refusal-only screen chosen over raising dcf_top because that would REPLACE the number on ~387 names. Bigger find: _enrich_with_dcf conflated 'not valuable' with 'REFUSED' and was suppressing ordinary peer estimates (NVS $185.41, SAP $364.97, TD $79.73). NOTE: build_ledger.py regenerates from the 134 audit ids only and will DROP this row. |
| OOB3 | OOB | Reinvestment undercharge for capex-heavy names (the CHTR class defect) | DONE | REJECTED |  | HANDOFF_live_data_bugs.md Part 8 | 2026-08-07 | human | OUT-OF-BAND. Pre-commitment 4f99d8f committed alone; measured offline on the 241-name 2026-08-05 pickle, one process, deterministic. BOTH ARMS REJECTED, nothing behavioural ships (REINVESTMENT_FLOOR_MODE defaults "off"). Control bound HELD perfectly for both arms: 116 names bit-identical, because the gate (capex - D&A > 0) IS the control group. ARM A (decay, explicit years only) passes F1/F2/F3 and fails F4 at +0.0% -- it cannot touch the terminal by construction, and the decisive names carry 80%+ of EV there; three of my four success criteria were YEAR-ONE statistics that a terminal-blind fix passes trivially. ARM B (persistent, terminal floored) passes ALL SIX pre-registered bounds and is still unshippable: 18 negative enterprise values, 16 negative terminal values, 14 names whose DCF is pushed non-positive. The rejection rests on a criterion I did not pre-register -- my bounds asked whether the number moved in the right direction and never whether it was still a number. KEY REFRAMING: the 33-name decisive set is TWO populations -- 14 genuine flat-revenue undercharges and 19 capex-boom names (ORCL net capex is 68.8% of revenue while revenue grows 3.1x) whose spend IS growth capital the revenue path already prices, so charging it double-counts. Part 4's "34 names undercharged" therefore OVERSTATED the defect; the honest count is ~14. Mechanism works where the defect is real: F1 held 8/8 on flat-revenue names. LIVE DEFECT FOUND: 6 names are published today with a NON-POSITIVE DCF (INTC -0.53 -> $34.54, F -31.92 -> $60.25, BA -24.97 -> $94.27, SRE, CCI, IRM) because blend._usable drops a non-positive lens and renormalises -- which is why charging MORE reinvestment moved EQIX +121%, GM +92%, XEL +73% UP. Characterised and pinned, NOT fixed. |
| OOB2 | OOB | Beta reproducibility: a vendor field vanishing silently rewrote a headline | DONE | FIXED |  | HANDOFF_live_data_bugs.md Part 7 | 2026-08-07 | human | OUT-OF-BAND. MRK went from 'cannot value' to a 91 Strong Buy because Yahoo dropped one beta field and wacc.py substituted 1.10; the field is INTERMITTENT (back at 0.211 on 2026-08-07). Shipped: valuation/data/beta.py (5y-monthly vs SPY; 1y-daily was tried first and is WRONG, giving KO -0.286 and XOM -0.484), a stated ladder in wacc.py, constant 1.10 -> 1.0 (market beta by construction), rejection on HISTORY not value (KSPI n=30 < 36; GILD/CI/CHTR/MRK/XOM are genuinely low-beta so a value floor would assert something false), and InputProvenance stamps on beta + risk-free. All four pre-registered bounds (04d9f12) HELD on a 46-name paced sample: control group 37 names 0 moved; MRK vendor-absent swing 0.133pp vs the old code's 3.85pp; KSPI rejected for its 30 observations; 0 published/withheld flips. Trigger insensitive at 0.10/0.15/0.25 (0 betas differ). TWO EARLIER FULL-UNIVERSE RUNS WERE INVALIDATED BY THEIR OWN RATE LIMITING (176 and 297 throttled; run 2 had 302 of 403 names arrive with no vendor beta) and both bounds 2 and 3 'passed' run 1 VACUOUSLY. That exposed the real defect: the first ladder treated 'check failed' as 'history is thin' and pushed 178 of 402 names onto the constant -- the same bug with a new trigger. Also fixed: the plausibility band was applied to the vendor's beta but not to our own (PDD adopted a COMPUTED -0.039, clamping WACC to 4% and turning a $217.82 fair value into a refusal). Also fixed: .gitignore's bare data/ matched valuation/data/, so the new module was unaddable and would have shipped as a runtime ModuleNotFoundError. CAVEAT: 46 names not 403; the fix cannot help a name whose vendor beta is missing AND uncomputable, and it moves fair values systematically UP (ARGX +83%, COP +69%, DTEGY +61%) for names formerly priced at 1.10. |
| M1-PARSE | X | Trial counter reads a FIXED verdict from the whole row, not the verdict column | DONE | FIXED - real defect, NEVER FIRED, N unchanged at 129 |  | HANDOFF_edge_audit.md session 12 | 2026-08-08 | pipeline builder | research_log._parse tested \bFIXED\b against every cell of a row joined together, so any row whose hypothesis/threshold/source/note contained the word "fixed" was silently dropped from N. Understating N OVERSTATES the significance of every DSR-gated claim - M1's own error inside M1's own parser, carried three sessions and worked around by choosing synonyms, i.e. the shipped denominator was protected by authors' word choice rather than by code. TWO SIBLING DEFECTS of the same class found by reading and fixed with it: the `n=<k>` grid multiplier was grepped from the WHOLE LINE (any prose containing n=100 would have multiplied that row's trials) and the domain was taken from the first cell matching any domain name rather than the domain column (which moves trials between BH-FDR families). The fix resolves columns from EACH TABLE'S OWN HEADER - RESEARCH_LOG.md holds two tables with different layouts (verdict at index 7 and at index 6), so a hard-coded index would have been a fourth bug; unresolvable fields resolve toward a LARGER N, the less favourable direction. **RECOUNT: NOTHING MOVES.** On the merged log: equity 129 -> 129, options 164, infra 3, total 296, 57 counted / 18 dropped - identical against the shipped module itself and against ALL FIFTEEN historical revisions of RESEARCH_LOG.md, and no `fix*` word appears outside a verdict cell in any of the 72 data rows as they stood at the recount (zero near-misses). **THE REPAIR NEARLY SHIPPED THE ERROR IT WAS FIXING:** merging origin/main brought in O16, which writes |Spearman(term_slope, atm_front)| - an absolute value - INSIDE a markdown table cell, so the unescaped pipes give that row 11 cells against a 9-cell header and shift every column after the metric. The first-cut column parser read `n` off prose and charged the row 1 trial instead of 5, understating options N by 4 - the exact direction this session exists to eliminate, and the whole-line grep it replaced was accidentally immune. Caught only because merging origin/main and re-running the recount was written into the pre-registered procedure. Misaligned rows now resolve toward a LARGER N on every field and are reported in rows_malformed rather than absorbed; pinned by test_session12_a_row_with_unescaped_pipes_may_not_silently_lose_its_trials. The O16 row itself was NOT edited (the register forbids editing rows this session) - its pipes want escaping as \| by the lane that owns it. No published N was ever wrong; DSR 0.8556 and sqrt(2 ln 129) 3.118 stand. All six named claims re-checked mechanically via ablation.deflated_sharpe_at and reproduce to six decimals (N=84 0.899659, N=116 0.867360, N=121 0.862756, N=129 0.855608). Pre-registered in PREREG_session12_recount.md at 21069ac BEFORE the parser was touched, including the rule that no row's TEXT may be edited to change N; the written expectation (N rises, 60/40) was WRONG. Pinned by test_session12_the_trial_counter_reads_verdicts_from_the_verdict_column_only - a fixture with 3 real trials of which the old parser counts 1 - and detail() now ships rows_rescued_by_parser_fix so a silent revert is loud. |
| X7RECON | X | The 8%-vs-7% ls_t>=2.0 mismatch between X7's placebo and session 10's re-run | DONE | DIAGNOSED - one draw, seed 1005 |  | HANDOFF_edge_audit.md session 12 | 2026-08-08 | pipeline builder | Open and called "undiagnosable" for two sessions because X7's raw draws were never retained. CAUSE: THE TWO SWEEPS RAN AT DIFFERENT PROJECT TRIAL COUNTS, AND N MOVES ls_t. cpcv_validate's adopt gate is (med[best]-med[default]) > _trials_haircut(len(names))*se, and _trials_haircut (fundamental_panel.py:2097) is FLOORED AT THE RESEARCH LOG'S N (audit M1). X7 ran at N=84 (haircut 2.97685), session 10 at N=121 (haircut 3.09703); scripts/placebo.py then feeds the ADOPTED weights to quantile_backtest, so adoption is monotone decreasing in N and a draw that stops adopting is re-scored under different weights. SEED 1005: margin 0.00287097 vs se 0.00094470, so it clears the N=84 bar of 0.0028122 and fails the N=121 bar of 0.0029257 - scored at naive ls_t 2.1273 under the challenger's weights and 1.0454 under base. Session 10's retained artifact records 1.0453572947436582, IDENTICAL to this session's base-weight recomputation to sixteen digits. Substituting the adopted value into session 10's 100 draws gives EXACTLY 8 at t>=2.0 (X7's figure), the adopt count at N=84 comes back 21 (M1's recorded 21%), and the naive p95 stays 2.1437 with max 3.436 - which is why session 10's control reproduced X7's percentiles to the digit while missing one draw: 2.1273 lands just below the 95th percentile. It also explains why it looked undiagnosable - seed 1005 did not drift across 2.0, it JUMPED 1.08 of a t because its weights changed, so "no draw near the boundary" was the wrong thing to look for. CONSEQUENCE THAT OUTLIVES IT: THE CALIBRATED PLACEBO FLOORS ARE FUNCTIONS OF N and nobody knew; here they happened not to move because the affected draw landed below the percentile, which is luck not design. Every future sweep must record the N it ran at, and a floor may not be compared across sweeps at different N without checking. The SHIPPED strategy is unaffected - it does not adopt, it keeps current-default, so no haircut touches its ls_t; the exposure is to the CALIBRATION, not the headline. Instrumentation: cpcv_validate now banks adopt_detail (margin, se, haircut, n_trials_used, folds_positive) and challenger_weights_cols - the challenger's weights WHETHER OR NOT adopted - so "what would this run have scored one haircut lower" is arithmetic. Zero trial cost. scripts/x7_reconcile.py; data/free_analysis/X7_RECONCILE.json retains all 100 rows. |
