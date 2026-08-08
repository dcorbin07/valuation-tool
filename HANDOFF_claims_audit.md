# HANDOFF — CLAUDE.md claims audit (2026-08-07)

**Lane:** options bot terminal, out-of-band verification. **Scope:** read-only across the tree;
the only files written are this one, `VALQUO_LEDGER.md`, and proven-wrong lines corrected in
place in `CLAUDE.md`. **No code was modified.**

---

## The honest summary

**I checked 62 claims: 43 CURRENT, 10 STALE (8 substantive + 2 drifted file:line cites),
6 WRONG, 2 UNCHECKABLE, and 1 mixed** (the METHODOLOGY RULE, whose *rule* is current and whose
*number* is stale — I count that one as a seventh wrong instruction in the list below, because a
hard rule that names the wrong universe size misdirects an agent regardless of which half is at
fault).

The research numbers are in far better shape than the procedural ones. **Every headline statistic
I could check reproduced** — the long-short *t*, both HAC *t*s, top-decile alpha and its *t*,
monotonicity, PBO, the Ljung–Box *p*, breakeven and realised costs, and all nine rows of the
corrected theme IC table all match `BACKTEST_RESULTS.json` to 3-5 digits. The Deflated-Sharpe
chain (0.8997 at N = 84, 0.8789 at 104, **0.8674 at the current 116**) is one step weaker: only
the N = 84 figure is in the artifact, so I re-derived the other two from that run's shipped `sr`,
`var_sr` and `n_periods` — the derivation reproduces the shipped 0.8997 exactly before predicting
the others, which is the check that makes it worth quoting. **I could not find a single
fabricated or drifted research number.**

**The wrong claims are almost all procedural or task-list claims**, and that is the more
expensive category, because they are the ones an agent *acts on* rather than quotes:

- **CLAUDE.md tells you to hand-merge into `main`.** `.github/workflows/land-agent-branch.yml`
  auto-lands any pushed `worktree-*` branch behind a full-suite gate, and `RUN_RULES.md:76` —
  the file CLAUDE.md's own header calls "non-negotiable" — says merging is automatic. CLAUDE.md
  contradicts the document it declares governing, and following it means hand-merging `main` in
  a checkout several agents share.
- **Two of the three "OPEN" roadmap items are closed**, one of them *rejected with numbers*
  eight days ago. An agent picking up #16 would re-run a rejected experiment.
- **The test count is off by 15×** (16/16 → 249/249).
- **X8, the project's only out-of-sample replication, is absent from CLAUDE.md entirely** while
  two surviving sentences still point at it as the evidence that will *someday* arrive.

The single most misleading thing in the file is not any one sentence: it is the header
**"LATEST (2026-07-30) — SUPERSEDES much of CURRENT STATE above. Read this first."** That was
true when written. `CURRENT STATE` now carries material through 2026-08-06, so the instruction
now sends a cold reader to the *oldest* numbers in the file and tells them they supersede the
newest.

---

## Method — what counted as evidence

Per the prompt: **code, artifacts and `git log`; never other prose.** Where a claim was only
corroborated by `HANDOFF_STATUS.md` or a handoff file I treated it as unverified, because both
may be copies of the same stale sentence.

- Numbers were checked against `BACKTEST_RESULTS.json` (the landed canonical run,
  `generated_at 2026-08-05T12:46:11`) and, where the file quotes a superseded era, against the
  same file at an older commit (`git show <sha>:BACKTEST_RESULTS.json`).
- Statuses were checked against `VALQUO_LEDGER.md` **and** the commit it names.
- File:line citations were re-resolved against the current file.
- `.gitignore:26` is unanchored `data/`; all scanning was done with a plain Python walker that
  ignores git's ignore rules, per the prompt's warning.
- I ran `python tests/test_edge.py` (249/249, exit 0). I did **not** run the full backtest: it
  needs the licensed export and it overwrites the tracked `BACKTEST_RESULTS.json`, which is the
  artifact this audit is measuring against.

---

## The table

Verdicts: **CURRENT** (verified today) · **STALE** (was true, superseded) · **WRONG** (never
true, or contradicted by a landed measurement) · **UNCHECKABLE**.

### Header, "How to run", HARD RULES

| # | claim (CLAUDE.md) | verdict | evidence |
|---|---|---|---|
| 1 | `RUN_RULES.md` exists and governs pushing/handoffs | CURRENT | file present, 80 lines |
| 2 | "Architecture is in section 4 below" (:8) | **WRONG** | CLAUDE.md has 11 `##` headings, none numbered; there is no section 4. Pointer leads nowhere |
| 3 | `OPTIMIZATION_RESEARCH.md` holds the roadmap | CURRENT | file present |
| 4 | Backtest CLI: `--data-dir`, `--json`, `--validate-institutional` | CURRENT | all three parse in `fundamental_panel.py` |
| 5 | `run_backtest.bat` / `validate_13f.bat` / `git_push.bat` exist | CURRENT | all three present at root |
| 6 | Full backtest "Takes 20-40 min" (:17) | **UNCHECKABLE** | needs the licensed export and would clobber the canonical results file. Note it contradicts task #3 (:791), "the full run now takes ~12 min end to end" — the two lines cannot both be right |
| 7 | "Tests (keep green, **currently 16/16**)" (:19) | **WRONG** | measured today: **249/249**, exit 0. Off by 15× |
| 8 | Never commit `data/` or `*.db` | CURRENT | `.gitignore:26` `data/`, `:27` `*.db` |
| 9 | `.env` holds real secrets, never print/commit | CURRENT | `.gitignore:2` |
| 10 | Keep `tests/test_edge.py` passing | CURRENT | 249/249 green today |

### Core file — `valuation/edge/fundamental_panel.py`

| # | claim | verdict | evidence |
|---|---|---|---|
| 11 | 17 named symbols exist (`build_fundamental_panel`, `_yoy`, `inst_lag_days`, `_weight_schemes`, `walk_forward`, `cpcv_validate`, `quantile_backtest`, `regime_split`, `institutional_dependence`, `validate_institutional`, `signal_coverage`, `holdout_theme_validate`, `_deflated_sharpe`, `_trials_haircut`, `theme_ic`, `composite`, `max-ir-decorr`) | CURRENT | all 17 resolve; e.g. `:904`, `:677`, `:1960`, `:2657`, `:3478`, `:3825` |
| 12 | "**8** weight schemes" | CURRENT | 7 dict entries + `max-ir-decorr` added at `:1983` = 8; docstring says "Eight" |
| 13 | CPCV is the authority; a rejection means keep defaults | CURRENT | `cpcv.adopt = false`, deployed weights are `current-default` |

### CURRENT STATE — the research numbers

| # | claim | verdict | evidence (`BACKTEST_RESULTS.json` unless noted) |
|---|---|---|---|
| 14 | long-short *t* **2.836** | CURRENT | `construction.long_short_tstat = 2.83606` |
| 15 | HAC/NW long-short *t* **2.620** | CURRENT | `long_short_tstat_nw = 2.61991` |
| 16 | top-decile alpha **+7.17%** | CURRENT | `top_decile_alpha = 0.0717414` |
| 17 | top-decile alpha *t* **+4.517**, HAC **+4.376**, hit **71.0%** | CURRENT | `4.51742` / `4.37623` / `0.710145` |
| 18 | monotonicity **−0.891**, and −1.0 = ideal | CURRENT | `−0.89091`; `monotonicity_want = "negative (-1.0 = perfectly ordered)"` ships the convention |
| 19 | Ljung–Box rejects independence at **p = 0.036**, lag-1 acf **+0.189** | CURRENT | `p_value = 0.03647`, `acf[0] = 0.18905` |
| 20 | PBO **73.3%**, scope = weight-scheme selection only | CURRENT | `cpcv.pbo = 0.73333`, `pbo_scope = weight_scheme_selection_only` |
| 21 | Deflated Sharpe **0.8997** at N = 84; `sr0` 0.406; self-reports as a genuine DSR | CURRENT | `deflated_sharpe_detail`: `0.899659`, `sr0 0.405623`, `metric = deflated_sharpe_ratio`, `is_effectively_undeflated = false` |
| 22 | Session 6: N 104 → DS **0.8789**, √(2·ln N) **3.048** | CURRENT | recomputed from the shipped `sr`/`var_sr`/`n`: **0.8789**, 3.048 |
| 23 | Session 7: **quote N = 116**, DS **0.8674**, √(2·ln 116) **3.083** | CURRENT | `research_log.trial_count(domain='equity') = 116`; recomputed DS **0.8674**; 3.083 |
| 24 | A missing research log degrades to N = 8, never to an unpenalised N | CURRENT | `trial_count(path='nope.md') = 8`; `N = max(2, len(trials), _n_logged)` at `:2569` |
| 25 | Corrected 9-row theme IC table (69 dates) | CURRENT | **all nine match to 3 dp**: quality 3.101, capital_discipline 2.756, institutional 1.547, momentum 1.312, value 0.838, growth 0.752, low_risk 0.462, insider −0.236, size −0.301 |
| 26 | `sentiment` still empty | CURRENT | `per_theme.sentiment.coverage = 0.0` |
| 27 | Equal-weight benchmark **+18.14%** (the control) | CURRENT | `equal_weight_ann = 0.181371` |
| 28 | Four benchmarks ship on every run | CURRENT | `benchmarks` block present with all four |
| 29 | Realised cost **33.4 bps**, breakeven **134 bps** | CURRENT | `realised_one_way_bps 33.36`, `breakeven_one_way_bps 134.11` |
| 30 | P6 bullet: "breakeven **236 bps** vs **37 bps** (~6.4×); net alpha **+11.41%**; **249%** turnover" (:604) | **STALE** | corrected panel measures **134.1 / 33.4 (4.0×) / +6.07% / 261%**. The corrected-panel bullet fixes breakeven and realised but leaves net alpha and turnover uncorrected here |
| 31 | `panel_window` ships every run (available vs retained, the cut, cross-sections) | CURRENT | `cleanups.panel_window`: retained 2008-01-16 → 2026-07-24, 69 dates, cross-sections 1,471–1,954 — matches the prose exactly |
| 32 | Panel is 69 dates over 2008-01-16 → 2026-07-24 | CURRENT | as above; `universe.n_dates = 69` |
| 33 | "full **2,710-name** universe" (header :36, sector bullet :625, METHODOLOGY :770) | **STALE** | current full run is **2,531 names** (`universe.n_names`, `label = "full"`). 2,710 was the P6-era 110-date panel (`git show b0f70b6` = 2710/110). Changed at the B6/B13 corrections |
| 34 | `institutional` coverage **61.4%** | **STALE** | now **71.7%** (`0.717241`). 0.614 is exactly the P6-era value — same field, so the comparison is sound. Rose because B6 dropped the pre-2008 dates where the theme was empty |
| 35 | `insider` coverage **85.0%** | **STALE** | now **83.1%** (`0.830752`); P6-era file read `0.850445` |
| 36 | M1 trial counts "equity **84**, options **139**, infra 1, total **224**" | **STALE** | measured today: **equity 116, options 155, infra 1, total 272** (`research_log.detail()`). The same file quotes 116 correctly 140 lines later |
| 37 | B8 fixed; `oos_verdicts` + `stability_verdicts` both ship | CURRENT | both in `fundamental_panel.py` (`:3498`, `:3503`), plus `oos_directions_tested`, `confirmed_oos`, `rejected_oos` |
| 38 | `rule_fired` is at `fundamental_panel.py:3545` | **STALE (cite)** | now `:3576`; and it *is* read at `:3594`, which is the substance of the B8 fix |
| 39 | B6 fixed — the `.tail(4659)` truncation is gone | CURRENT | no `tail(4659)` anywhere in `valuation/`; only a historical note in `ablation.py:9` |
| 40 | B7 fixed — one composite, `CONFIG` flags default false | CURRENT | `config.py:165-166` both default `"false"`; `composite` at `:1549` |
| 41 | `screen.py:256` calls `build_frame(metrics)` with no kwargs | **STALE (cite)** | now `screen.py:232`; still no kwargs, which is now *correct* because the CONFIG defaults are false |
| 42 | `SCREENER_SECTOR_NEUTRAL` / `EDGE_EV_POINT_IN_TIME` revert switches exist | CURRENT | `config.py:165` and `:177` |
| 43 | B12 fixed — universe ranked by market cap, sort key in the banner, subsets labelled smoke tests | CURRENT | `data_providers.py:384` `UNIVERSE_SORT_KEY`, ranking at `:405`, banner at `:407` prints "SMOKE-TEST SUBSET, not a verdict" |
| 44 | B17 — the "top-25" book holds to **fifty** (`exit_rank = top_n × 2`) | CURRENT | `fundamental_panel.py:1710`, and `:1777` ships a `label_warning` saying the realised size is ~`exit_rank`, not `top_n` |
| 45 | `low_risk` zeroed live; `insider` still 0.125 | CURRENT | `settings.py:75-80`: `low_risk 0.0`, `sentiment 0.0`, seven themes at 0.125 (= the "flat 1/7") |
| 46 | `ev_freshness` ships, 100% fresh | CURRENT | `ev_freshness.fresh = 1.0`, `ok = true`; drift median 5.04% matches the claimed "median 5.1%" |
| 47 | `sanity_check` layer runs every backtest | CURRENT | `sanity_check` block present with range / pegging / divergence checks |
| 48 | `signal_coverage` warns under 5% and ships `below_floor` | CURRENT | block present, `floor` set, and **currently non-empty and correctly reported**: `govt_award_momentum` at 4.75% is named in `BACKTEST_RESULTS.md:12` as an empty signal. The guard fires and the report carries it |
| 49 | Standing caveat: "Deflated Sharpe is a **saturated 0.9999991** … an **undeflated PSR** — not a proof of anything" (:671) | **WRONG** | contradicted by a landed measurement and by the same file 400 lines earlier: **0.8674 at N = 116**, `is_effectively_undeflated = false`, `metric = deflated_sharpe_ratio`. M1 retired this on 2026-08-05 |
| 50 | Standing caveat: the held-out test "is a **both-halves stability check rather than an out-of-sample confirmation** (B8)" (:673) | **STALE** | B8 was fixed in session 7; `oos_verdicts` now enforces the documented rule and `low_risk` reads `confirmed_oos`. The caveat describes the pre-fix object |
| 51 | X8 is the out-of-sample evidence, "still ONE panel" (:469, :494) | **STALE** | X8 **landed 2026-08-04** (`7edf594`, `scripts/jkp_replication.py`, ledger DONE): **REPLICATES** — Japan NW *t* 3.85, developed Europe *t* 4.30 (12 of 15 countries clear *t* > 2), with the **US control the weakest region at *t* 2.35**. CLAUDE.md records this nowhere |

### METHODOLOGY / COVERAGE rules

| # | claim | verdict | evidence |
|---|---|---|---|
| 52 | Report verdicts only from the full universe; subsets are smoke tests | CURRENT (rule) / **STALE (number)** | the rule is enforced in code (`data_providers.py:388-409`); the "~2,710-name" figure in it is stale — see #33 |
| 53 | B12 — the 800-name era was an alphabetical slice | CURRENT | `sorted(keys)[:limit]` is gone; the fix is at `:405` |
| 54 | `WRDSProvider._KEEP` is the column allowlist to extend | CURRENT | `data_providers.py:247` |
| 55 | Coverage rule: check coverage before quoting an IC | CURRENT | `signal_coverage` ships and is non-empty today |

### Task list and routing

| # | claim | verdict | evidence |
|---|---|---|---|
| 56 | #12 forward paper-track vs SPY is OPEN and "**→ Cowork's lane. Tell Don to take it there**" | **WRONG** | it was **built in this repo, in this lane**: `valuation/edge/paper_track.py` (docstring: "roadmap #12, the project's #1 remaining validation"), plus `paper_broker.py`, `options_tracker.py`, `track_export.py` and `tests/test_paper_track.py`. First landed at `cde1579` |
| 57 | #16 ML tree combiner is OPEN and "clearly worthwhile now" | **WRONG** | **TESTED AND REJECTED** at commit `f53b248` ("ML tree combiner: TESTED AND REJECTED on every criterion"), pre-registered first at `620e0a5`. `CODE_AUDIT.md:15-18`: median OOS IC +0.0531 linear vs +0.0393 GBM, net alpha −8.2pp roth / −4.0pp taxable, fails in both halves — "closed, not pending — re-open only with materially more data, not a different model" |
| 58 | #18 social preview / Open Graph tags are OPEN | **STALE** | shipped in `valuation/web/templates/_saas_base.html:34-44`: `og:title`, `og:image` (+`secure_url`, `type`, 1200×630, `alt`), `twitter:card = summary_large_image` |
| 59 | #13 sector-neutral rejected, stays OFF, pinned by a test | CURRENT | `tests/test_sector_neutral.py` present; `CONFIG.sector_neutral` defaults false |
| 60 | #15 PEAD rejected, pinned by `tests/test_pead.py` | CURRENT | file present |
| 62 | "`CODE_AUDIT.md`'s M2 (SanDisk/WDC ~10×) does NOT reproduce" | **UNCHECKABLE** | the claim is about the licensed price series; not re-derivable without the Sharadar export. Note the ledger's trap #3: the external audit's M2 is a different item ("clustered inference default", still OPEN) |
| 61 | Git handoff: "Commit directly to `main` in the primary checkout … you MUST land the work on `main` … (`git checkout main && git merge --ff-only <branch>`) … Don deploys from `main` with `git_push.bat`" (:883-889) | **WRONG** | `.github/workflows/land-agent-branch.yml` auto-lands any pushed `worktree-*` branch behind a full-suite gate — its own header says "No local merge … no git_push.bat, no you in the loop". **`RUN_RULES.md:76`**: "Merging is automatic — the GitHub Action lands any pushed `worktree-*` branch behind the test gate." CLAUDE.md's header calls RUN_RULES non-negotiable and then contradicts it |

---

## WRONG (6 rows, + the mixed METHODOLOGY row as a 7th)

1. **The git-handoff instruction** (#61) — tells an agent to hand-merge `main` in a shared
   checkout while other lanes are live. Contradicts `RUN_RULES.md:76` and the shipped Action.
2. **Task #12 routing to Cowork** (#56) — the forward paper track exists here, with tests.
3. **Task #16, ML tree combiner "clearly worthwhile"** (#57) — rejected with numbers on
   2026-07-31, one day after the task list's own "updated 2026-07-30" stamp.
4. **"currently 16/16" tests** (#7) — it is 249/249.
5. **The standing Deflated-Sharpe caveat** (#49) — "saturated 0.9999991 / undeflated PSR" is
   contradicted by the file's own M1 bullet and by the landed artifact.
6. **"Architecture is in section 4 below"** (#2) — no such section.
7. *(counted under #52)* the **METHODOLOGY RULE's universe size** — a hard rule quoting a
   number that no longer describes the full universe is a wrong instruction, not just a stale
   figure: an agent seeing 2,531 could reasonably conclude it is looking at a subset and
   withhold a verdict.

## STALE (10)

`institutional` 61.4% → **71.7%** (#34) · `insider` 85.0% → **83.1%** (#35) · universe 2,710 →
**2,531** (#33) · P6 cost profile 236/37 bps, +11.41%, 249% → **134/33.4 bps, +6.07%, 261%**
(#30) · trial counts 84/139/224 → **116/155/272** (#36) · the B8 standing caveat (#50) · X8
recorded nowhere (#51) · task #18, OG tags already shipped (#58) · and two drifted cites,
`screen.py:256` → **:232** (#41) and `fundamental_panel.py:3545` → **:3576** (#38).

Separately, and not counted as a claim because it is a structural label rather than an
assertion: the **"LATEST (2026-07-30) … Read this first"** header, which is the single most
misleading line in the file — see below.

## UNCHECKABLE (2)

- **Backtest wall-clock "20-40 min"** — needs the licensed Sharadar export and would overwrite
  the canonical `BACKTEST_RESULTS.json` this audit measures against. Flagged rather than
  guessed, but note it contradicts task #3's "~12 min" in the same file.
- **`CODE_AUDIT.md`'s M2 (SanDisk/WDC ~10×) "does not reproduce"** — the claim is about the
  licensed price series; not re-derivable without the export.

---

## The five most likely to mislead the next agent

1. **"LATEST (2026-07-30) — SUPERSEDES much of CURRENT STATE above. Read this first."** It now
   points a cold reader at the *oldest* numbers in the file (PBO 13.3%, DS ~100%, LS *t* 3.485,
   alpha +11.77% — all void since B6) and tells them those supersede the 2026-08-06 material
   above. This is the exact failure the prompt was written about, still live.
2. **The git-handoff paragraph.** Acting on it means a hand-merge into `main` in a checkout
   several agents share.
3. **Task #16.** An agent picking up the "OPEN, clearly worthwhile" ML combiner would spend a
   session reproducing a rejection.
4. **The standing Deflated-Sharpe caveat.** It instructs agents to carry a caveat ("saturated,
   undeflated, not proof of anything") that the project's own measurement retired — and it sits
   in a bullet headed "do not drop them", so it propagates by design.
5. **X8's absence.** The file repeats "it is still ONE panel" as a live limitation while the
   16-country replication that partly answers it has been landed for three days.

---

## BUGS FOUND

**Five live, one withdrawn.** None were repaired — every one belongs to another lane, and the
scope for this task was read-only outside `CLAUDE.md`. Each is routed by name.

1. **`_deflated_sharpe`'s docstring contradicts its own function.** `fundamental_panel.py:2499-2519`
   still says "N = 8 is not the number of trials", "Nothing is being deflated", and "Feeding a
   real trial count is item M1 … and is **NOT done here**". M1 landed: `:2568-2569` reads the
   research log and `N = max(2, len(trials), _n_logged)`, and the shipped run self-reports
   `metric = deflated_sharpe_ratio`. An agent reading the docstring would conclude M1 is
   undone. **Owning lane: pipeline builder / edge.** Not fixed here — I do not touch code.
2. **`VALQUO_LEDGER.md`'s R3 row is stale in a way CLAUDE.md already corrected.** The row says
   "Shrinks every options t ~1.36x"; the corrected figure is **√2.212 = 1.487×** on the
   3,885-trade book (CLAUDE.md, session-5 closeout). The 1.36× came from the pre-correction
   3,042-trade book. **Owning lane: whoever owns R3** — I did not edit another lane's row.
3. ~~**A signal is below the coverage floor right now and nothing says so.**~~ **WITHDRAWN — my
   claim, not the project's.** `signal_coverage.below_floor` does hold one entry
   (`govt_award_momentum`, **4.75%**, theme `growth`), and I first wrote this up as an unreported
   guard hit. It is reported, in two places: `BACKTEST_RESULTS.md:12` calls it out by name
   ("EMPTY SIGNALS (1) — wired but below 5% coverage, so contributing nothing"), and
   `HANDOFF_sharadar_extract.md:104,396` tracks it deliberately. **The coverage guard is working
   and the reporting chain around it is working** — the only true residue is that `CLAUDE.md`
   does not mention it, which is not a defect. Recorded rather than deleted because the whole
   point of this audit is that unverified claims must not be promoted, including mine.
4. **`sync.bat` is not in git.** `RUN_RULES.md:79-80` tells agents to run it ("repo root,
   double-click"); it exists only in the main checkout, so no worktree-based agent can see it.
   Same class as `check_lanes.py`, which `HANDOFF_free_analysis.md:630` invokes and which is
   also untracked. **Owning lane: CI / whoever owns RUN_RULES.**
5. **X8's write-up states Valquo's long-short as +20.4%/yr; the landed panel says 11.04%.**
   `HANDOFF_free_analysis.md` frames the JKP-vs-Valquo magnitude gap as "a factor of six" using
   +20.4%; `construction.long_short_ann` on the corrected panel is **0.11038**. The +20.4% looks
   like a pre-B6 figure. The caveat's direction is unaffected (the gap is still 3-5×, and X8
   still corroborates none of it), so no verdict moves — but the number should not travel.
   I quoted the artifact, not the handoff, in the CLAUDE.md bullet I added.
   **Owning lane: free-analysis / X8.**
6. **`B13` is `IN PROGRESS` in the ledger but reads as landed in CLAUDE.md.** The ledger note
   is honest ("PARTIALLY FIXED and labelled so. Categorical filters bind;
   `MIN_AVG_DOLLAR_VOLUME` still cannot"), while CLAUDE.md's corrected-panel bullet lists B13
   alongside B6 and B7 as though all three are complete. Not corrected in place — the CLAUDE.md
   sentence is about B13's *measured effect*, which is real; it is the completeness implication
   that is loose. **Owning lane: edge audit.**

---

## What I changed in `CLAUDE.md`

**Twelve in-place corrections plus one new bullet**, each following the file's existing
convention (state the correction, quote what the old text said, date it `2026-08-07`). Nothing
was rewritten for style, and **no claim was deleted** — every superseded sentence is quoted
inside the correction that replaces it, which is verifiable in `git diff`: all 43 deleted lines
are re-quoted in the additions.

1. The test count, 16/16 → **249/249**, plus a note that the gate runs all 24 suites, not just
   `test_edge.py` (audit C7).
2. The "section 4" pointer → "Core file" below.
3. The `LATEST (2026-07-30)` header → re-marked **HISTORICAL, do not read first**, with the
   void numbers it contains named explicitly.
4. The standing Deflated-Sharpe caveat (**wrong**) and the B8 caveat (**stale**), split into
   sub-bullets so the retired text stays attached to what replaced it.
5. The METHODOLOGY RULE's universe size, **2,710 → 2,531**, with the `git show` that proves when
   it changed.
6. `institutional` **61.4% → 71.7%** and `insider` **85.0% → 83.1%**, with the mechanism.
7. The P6 cost profile → **134.1 bps / 33.4 bps / +6.07% / 261%**.
8. The M1 trial counts → **equity 116, options 155, total 272**.
9. Task list **#12** (built here, not Cowork's), **#16** (rejected, closed), **#18** (shipped).
10. The task-list section header, with a warning that 2 of 3 checked OPEN items were closed.
11. The git-handoff paragraph → push and let the Action land it; never merge `main` by hand.
12. The footer telling Don to buy an FMP/Intrinio key — contradicted by roadmap #20 and
    `HANDOFF_data_spend.md`; the item is parked on WRDS/IBES, not on a purchase.

The **new bullet** records X8, because an omission cannot be corrected in place and the two
surviving forward references to it would otherwise keep reading as pending work.

**One correction I had to correct.** My first draft of the P6 edit said "every number in this
bullet is stale" while I had only re-measured four of them; the bottom-decile market-cap figures
were never re-run. It now says the cost profile is stale and marks those figures **unverified,
not corrected**. Same discipline as the rest of the audit: an unverified claim promoted to
verified is the failure being audited.

---

## Recommended next step

**Do not attempt a general rewrite of `CLAUDE.md`.** Its repetition is load-bearing — the
corrections stay attached to the claims they correct, which is why the research numbers
survived intact while the prose around them rotted.

The cheap, high-value fix is structural: **the file is ordered oldest-instruction-last but
labelled newest-first.** Re-titling the three era headers (`CURRENT STATE`, `LATEST`,
`PREVIOUS`) with the date range each actually covers would kill the single worst misreading
without touching a claim.

Second: **the task list is the least trustworthy section in the file** (2 of 3 checked open
items were closed, one with a rejection). It is stamped "updated 2026-07-30" and has taken
landings from at least five sessions since. It should be regenerated from `VALQUO_LEDGER.md`
rather than hand-maintained.
