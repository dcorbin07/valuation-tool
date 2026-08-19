# HANDOFF — triage of `origin/worktree-ui-polish` (50 commits stranded)

**Session:** 2026-08-07, r1 lane. **Read-only.** Nothing was merged, cherry-picked, rebased or
deleted. The only file this session wrote is this one.

---

## 0. BOTTOM LINE

**The branch is misnamed and mostly already landed. "UI polish" is three of its fifty commits;
the other forty-seven are the project's entire early Edge Lab history — and that history reached
`main` on 2026-07-28 by a different route.**

- **Nine files** are unique to the branch. Not fifty commits' worth — nine files.
- **Four of them are one coherent, still-valuable module** (`param_search`), whose engine
  interface **still matches `main` exactly** and which exists nowhere else.
- **Five of them are a UI theme layer that `main` re-implemented independently** eight hours
  after the branch's last commit. Obsolete, not lost.
- **The 13F lag fix the prompt flagged as possibly-still-live is fully on `main`.** The bug is
  not live. That premise is corrected below with line numbers.
- **A merge is off the table**: a dry-run produces **22 conflicted files**, including `add/add`
  on `CLAUDE.md`.
- **Deleting `worktree-ui-polish` alone does nothing.** `worktree-honest-param-search` is a
  strict *ancestor* of it and holds 47 of the 50 commits, including the whole param stack.
  **Prune both or neither.**

**Recommended disposition: cherry-pick the four `param_search` files (edge lane), abandon
everything else, then delete BOTH branches.**

---

## 1. WHAT THE BRANCH ACTUALLY IS, AND WHY IT STRANDED

### History

| | |
|---|---|
| merge-base with `main` | `af5d2f9` — 2026-07-26 03:47, "Rebrand to Valquo" |
| branch commits | 50, all authored `Donovan Corbin`, 2026-07-26 04:58 → **2026-07-28 08:24** |
| `main` ahead by | **401 commits** |
| branch ahead by | 50 |

The branch diverged at the very start of the Sharadar era and, on its own, built: the
self-learning loop, the theme restructure, the point-in-time fundamental panel, the Sharadar
export/adapter path, CPCV + Deflated Sharpe + PBO, the 13F lag validation, `param_search`, and
finally three UI/doc commits. The last five commits are the only ones the branch's name
describes.

### Why it stranded — established, not assumed

`git cherry -v origin/main origin/worktree-ui-polish` marks **all 50 commits `+`** (no patch
equivalent on `main`). Taken alone that reads as "fifty commits of lost work." It is a trap.
`main` demonstrably *has* CPCV, the panel, and the 13F work.

The reconciliation is on `main` itself:

```
8a8c2b8  2026-07-28 15:19  Consolidate local work for a clean push: backtest validation
                           (CPCV / Deflated Sharpe / PBO / 13F lag test), growth +
                           capital-discipline themes, UI user-facing cleanup, docs/CLAUDE.md.
                           Licensed data/ excluded (a stray 138MB export was blocking the push).
```

**The branch's content was squash-landed onto `main` as a single commit, seven hours after the
branch's final commit.** A squash produces different patch-ids, which is exactly why `git cherry`
sees no equivalence while the features are plainly present. The commit message states the cause:
a stray 138 MB licensed export was blocking a normal push, so the work was consolidated rather
than merged, and the branch was left behind.

Measured directly — `git diff --stat 8a8c2b8 origin/worktree-ui-polish` — the squash absorbed
the entire Sharadar/backtest stack (`data_providers.py`, `export_sharadar.py`, `autolearn.py`,
`diagnostics.py`, all four `.bat` runners, `BACKTEST_RUNBOOK.md`). What it did **not** absorb is
the `param_search` stack and the separate-file UI theme layer.

### Relationship to `worktree-honest-param-search` — the prompt asked; here it is

`origin/worktree-honest-param-search` points at **`5da1473`**, the branch's own 47th commit.

```
git merge-base --is-ancestor origin/worktree-honest-param-search origin/worktree-ui-polish → true
```

**They are not siblings. `honest-param-search` is a strict ancestor of `ui-polish`**, which is
`honest-param-search` plus exactly three commits (`f0092a4`, `bb9fddb`, `f591961` — the UI and
doc commits). Both branches carry `valuation/edge/param_search.py`.

**Consequence for pruning:** deleting `worktree-ui-polish` and stopping there removes three
commits from the stranded-scan and leaves 47 — including every genuinely valuable file — still
stranded under the other name. The prune must be of both refs or it is theatre.

---

## 2. CLASSIFICATION

The unit that matters is the *file*, not the commit, because the squash already took most of the
content. Exactly nine files exist on the branch and not on `main`:

| file | lines | class | evidence |
|---|---|---|---|
| `valuation/edge/param_search.py` | 963 | **VALUABLE** | absent from `main`; engine interface intact (§2a) |
| `PARAMETER_SEARCH.md` | 289 | **VALUABLE** | the protocol + a recorded negative result (§2b) |
| `scripts/calibrate_param_search.py` | 121 | **VALUABLE (partly superseded)** | X7's doctrine, weaker method (§2c) |
| `param_search.bat` | 48 | VALUABLE (trivial) | wrapper for the above |
| `valuation/web/static/theme.css` | 293 | **OBSOLETE** | `main` re-implemented dark mode inline (§2d) |
| `valuation/web/static/ui.js` | 218 | **OBSOLETE** | same |
| `valuation/web/templates/_footer.html` | 52 | **OBSOLETE** | `main`'s footer predates the branch (`2971f71`, 07-24) |
| `valuation/web/templates/_head.html` | 22 | **OBSOLETE** | same |
| `valuation/web/templates/_theme_toggle.html` | 12 | **OBSOLETE** | `main` has a toggle in `_saas_base.html` / `app.js` |

Everything else the branch touches is content `main` already has in a later form, and falls into:

| group | class | evidence |
|---|---|---|
| CPCV / Deflated Sharpe / PBO / panel / themes / Sharadar path (~40 commits) | **OBSOLETE** | absorbed by `8a8c2b8`, then rewritten by the audit sessions (B6/B7/B13) |
| `5da1473` 13F lag fix + UTF-8 stdout | **OBSOLETE** | fully present on `main` — see §3 |
| `CLAUDE.md` (10.6 KB on branch vs **97 KB** on `main`) | **DANGEROUS** | predates the entire claims audit; would reintroduce corrected text |
| `OPTIMIZATION_RESEARCH.md` | **DANGEROUS** | same era, `add/add` conflict |
| `.github/workflows/auto-scan.yml` | **DANGEROUS** | branch pins `checkout@v4`/`setup-python@v5`; `main` was bumped to `v5`/`v6` on 2026-08-07 (`845363a`) because Node 20 is deprecated. Merging reverts that. |
| `/api/feedback` feature (`app.py`, `models.py`, `gating.py`) | **UNKNOWN — app lane's call** | see §2e |

### 2a. `param_search.py` still runs against today's engine — checked, not assumed

It touches the engine at exactly four symbols, and all four survive on `main` with compatible
signatures:

| call in `param_search.py` | `main` today |
|---|---|
| `FP._weight_schemes(mu, vol, Sigma, cols, eq, base)` | `fundamental_panel.py:1960` — identical six-arg signature |
| `FP._pbo(is_mat, oos_mat, keys)` | `:2590` — three positional args |
| `FP.build_fundamental_panel(..., rebalance_days=, lookback_years=, horizon=, inst_lag_days=)` | `:904` — all four kwargs present |
| `FP._spearman(a, b)` | `:1820` |

This is the reason the recommendation is a cherry-pick and not a rewrite. **The four files land
clean** — none of them appears in the dry-run merge's conflict list, because none exists on
`main` to conflict with. Only the CLI wiring needs hand-porting (§4).

### 2b. What `PARAMETER_SEARCH.md` records is a *negative* result, and negative results are this
project's most durable output

The protocol adds five things the current pipeline still lacks: a **locked hold-out** touched
once, **one joint declared search space**, selection by **lower confidence bound** rather than
argmax, **plateau smoothing + interiority** (a winner on a grid edge is not adoptable), and
White (2000) Reality Check / Hansen (2005) SPA.

Its first and only full run (July 2026; 3,584 configs × 15 CPCV paths, 88 rebalances searched,
22 locked away):

| | search window | locked hold-out |
|---|---|---|
| selected `ic-proportional, top20, band2.0x, hold3, all` | **+8.43%/yr** (LCB +6.33%) | **−0.04%/yr** |
| baseline `current-default, top25, band2.0x, hold2, all` | −0.83%/yr (LCB −2.00%) | **+5.12%/yr** |

Positive in 87% of 15 CPCV paths, PBO 33%, and the gain decomposed to +9.15%/yr of *selection*
against +0.11%/yr of saved turnover — so not a cost artefact. Then the two expensive tests:
**the hold-out collapsed**, and the **permutation null gave p = 0.077** (signal-free re-runs
averaged +2.65%/yr and one draw hit +8.59%/yr). Verdict: **keep the defaults.**

Its own summary is the sentence worth carrying: *"this is what overfitting looks like from the
inside — 87% of paths positive, PBO 33%, a large decomposed selection edge, and it is still
worth nothing out of sample."* That is corroborating evidence for the standing rule that CPCV
rejection means keep the defaults, and it was produced by a procedure the project no longer has.

### 2c. The branch anticipated X7 by eight days

`scripts/calibrate_param_search.py` opens: *"Calibrate the parameter search's own gates — i.e.
test the tests,"* and closes: **"A gate whose false-positive rate you have not measured is not a
gate."** It reports Hansen SPA firing on **~35% of signal-free panels**, which is why SPA was
demoted from a gate to a reported statistic.

That is precisely audit **X7**'s doctrine (2026-08-05), reached independently **eight days
later**. This is the concrete cost of the strand: the project rebuilt a method it already owned.

**Not a claim that X7 is redundant — X7 is strictly stronger.** This script calibrates on
*synthetic no-signal panels*; `scripts/placebo.py` block-permutes the *real* panel, preserving
per-date distribution, missingness and cross-theme correlation. Keep X7's method. The branch's
value here is the five measured gate false-positive rates and the SPA finding, which X7 never
covered because SPA is not on `main`.

### 2d. The UI work is obsolete, not lost — verified rather than assumed

`main` has a full dark theme: 16 `:root[data-theme="dark"]` rules in `style.css:278-301`, plus
theme toggles in `_saas_base.html`, `index.html`, `portfolio.html` and `app.js`. It arrived via
`833a6f1` / `b79e8c2` (2026-07-28 16:29/16:39, *"site polish (dark mode, footer, feedback, sign
out)"*) — eight hours after the branch's last commit, implemented **inline in `style.css`/`app.js`
rather than as separate `theme.css`/`ui.js` files**. Same mechanism, different file layout.
Landing the branch's version would duplicate a working system.

`main` also already has `og-image.png` and `favicon.svg`, so CLAUDE.md's open task #18 (social
preview) is further along than that list suggests — flagged for whoever owns the task list, not
acted on.

### 2e. `/api/feedback` — genuinely absent from `main`, and the one open question

`main` has **no `/api/feedback` route at all** and no `feedback` table. The branch's version is
a complete small feature: a `feedback` table, `add_feedback`/`recent_feedback` on `UserStore`,
the POST route, and an entry in `gating.py`'s public allowlist.

**I looked for a spam/amplification vector and did not find one.** The endpoint is rate-limited
per-IP (`_feedback_rate_limited`, honouring `X-Forwarded-For`), all inputs are length-capped
(message 4000, email 254, kind 24, page 200), SQL is parameterized, and it degrades gracefully if
neither the store nor the mailer works. It is reasonable code.

The open question is **posture, not correctness**: `main`'s allowlist is now
`("/api/health", "/api/hotstocks", "/api/track", "/api/valquo-index")`, set during the
public-leak closure. Whether an unauthenticated write endpoint that emails the owner belongs on
that list is the app/security lane's decision, made after four sessions of work that this branch
predates. **Classified UNKNOWN and routed, not recommended.**

---

## 3. THE 13F LAG FIX (`5da1473`) — THE PROMPT'S PREMISE IS WRONG. THE BUG IS NOT LIVE.

The prompt lists this as *"at least one commit [that] looks like a real, still-relevant fix"* and
asks whether the inert lag grid is still on `main`. It is not. All three parts are present:

| part of `5da1473` | on `main` today |
|---|---|
| the corrected grid | `fundamental_panel.py:2780` — `INST_LAG_GRID = (15, 45, 135, 225)` |
| the property-based guard test | `tests/test_edge.py:404` — `test_inst_lag_grid_crosses_quarter_boundary` |
| UTF-8 stdout reconfigure | `fundamental_panel.py:3967` — `_stream.reconfigure(encoding="utf-8", errors="replace")` |

Route of arrival: the squash `8a8c2b8` already carried `INST_LAG_GRID = (15, 45, 135, 225)` at
its line 1156, so the fix reached `main` on 2026-07-28 and has survived every rewrite since.

**There is no `## BUGS FOUND` entry for the edge lane on this item.** The remaining 47-line
difference in `fundamental_panel.py` between the branch and the squash is not the 13F fix at all
— it is the `--param-search` CLI wiring (argparse flags plus the dispatch block).

Worth preserving as the finding: **the branch's most-cited reason to exist does not survive
contact with the current tree.** Anyone scanning stranded branches by commit *message* would
re-flag this every time.

---

## 4. RECOMMENDED DISPOSITION

### CHERRY-PICK — edge lane

Four files, all additive, all landing without conflict:

```
valuation/edge/param_search.py          (963 lines, new file)
PARAMETER_SEARCH.md                     (289 lines, new file)
scripts/calibrate_param_search.py       (121 lines, new file)
param_search.bat                        ( 48 lines, new file)
```

Then two small hand-ports, which are the only real work:

1. **CLI wiring** — six `argparse` flags (`--param-search`, `--fast`, `--permutations`,
   `--cost-bps`, `--holdout-frac`, `--refresh-panel`) and the ~20-line dispatch block into
   `fundamental_panel.main()`. `git show origin/worktree-ui-polish:valuation/edge/param_search.py`
   and the branch's `main()` are the sources. Do **not** merge the file.
2. **Five tests** — append to `main`'s `tests/test_edge.py`; they are self-contained:
   `test_param_search_reality_check_calibration`, `..._plateau_beats_argmax`,
   `..._interiority_and_ledger`, `..._rejects_a_signal_free_panel`,
   `..._detects_a_planted_signal`.

Caveats to carry, so nobody re-runs it and quotes the old numbers:

- **Every number in `PARAMETER_SEARCH.md` was measured on the pre-B6 panel** (88 searched + 22
  locked rebalances). The current panel is 69 dates over 2008-01-16 → 2026-07-24. Re-landing the
  *code* does not re-validate the *result*; the verdict ("keep the defaults") is what transfers.
- Its `TrialsLedger` is a **second, independent trial counter** alongside `research_log.py`. Two
  counters that disagree is worse than one. Wire it to `research_log.py` or leave it off.
- The module was written before `holdout_theme_validate`'s B8 repair and before the calibrated
  X7 bars. Its internal thresholds are the old conventions.

### ABANDON

Everything else: the ~40 superseded edge commits, the five UI files, both doc files, the
workflow change. Reason per group in §2.

### ROUTE, DO NOT DECIDE

- **`/api/feedback`** → app/security lane (§2e). Complete and rate-limited; the question is
  whether it belongs on the public allowlist.
- **The 3,584-config trial count** → edge lane (see BUGS FOUND #1).

### THEN DELETE — **both refs**

```
git push origin --delete worktree-ui-polish
git push origin --delete worktree-honest-param-search
```

Precedent is `worktree-p6-costs-and-robustness`: prune, but only after an agent verified nothing
unique remained. That verification is §2 of this file — nine files, each classified with
evidence. **Do not delete before the four files are on `main`**, and delete both or the work
stays stranded under the other name.

---

## 5. METHOD — how each claim above was checked

| claim | command |
|---|---|
| what stranded, and when | `git log --format=... origin/main..origin/worktree-ui-polish` |
| why it stranded | `git log origin/main --since=2026-07-25 --until=2026-07-30` → found `8a8c2b8` |
| what the squash absorbed | `git diff --stat 8a8c2b8 origin/worktree-ui-polish` |
| the nine unique files | `git ls-tree -r --name-only` on both refs, `comm -23` |
| engine interface intact | `grep -o 'FP\.[A-Za-z_]*'` → `git grep '^def ...' origin/main` |
| 13F fix present | `git grep INST_LAG_GRID / inst_lag_grid_crosses_quarter_boundary / reconfigure origin/main` |
| dark mode present | `git grep -c 'prefers-color-scheme\|data-theme' origin/main -- style.css` → 16 |
| merge is off the table | `git merge-tree --write-tree --name-only origin/main origin/worktree-ui-polish` → exit 1, 22 files |
| branch relationship | `git merge-base --is-ancestor origin/worktree-honest-param-search origin/worktree-ui-polish` |

Nothing in this session wrote to either branch, to `main`'s history, or to the working tree
outside this file.

---

## BUGS FOUND

1. **`RESEARCH_LOG.md` has never counted the parameter search's 3,584 configs — equity `N` may
   be understated.** `PARAMETER_SEARCH.md` records a completed search over **3,584
   configurations** (plus 25 permutation re-runs of the whole procedure). `main`'s
   `RESEARCH_LOG.md` shows no param-search row, and the only mentions of `param_search` anywhere
   on `main` are two prose references in handoffs. Current quoted equity `N` is 116.
   **By the project's own precedents this appears to count:** `research_log.py:27` explicitly
   supports a row representing a pre-registered grid via `n_trials`, and CLAUDE.md settled that
   **`SUPERSEDED` rows DO count toward `N`** — so "it ran on the pre-B6 panel" is not on its own
   a reason to exclude it. The genuine counter-argument is domain: this searched *construction*
   parameters (scheme × top_n × band × min_hold × cap_tier), not the signal-inclusion decisions
   the equity composite is charged for, and `DOMAINS` (`research_log.py:50`) would let it sit
   under a different heading. **Direction, so the stakes are clear: adding trials RAISES `sr0`
   and LOWERS the Deflated Sharpe, so counting them is the self-penalising choice.** At `N = 116`
   the figure is 0.8674 with √(2·ln N) = 3.083; a jump toward ~3,700 would move both materially.
   **Edge lane's decision — flagged, not made, and nothing was changed.**

2. **`git cherry` is actively misleading on this repo and will mislead the next triage too.** It
   marks all 50 commits as unmerged when all but five of them (`50a4bf3`, `09a7730`, `f0092a4`,
   `bb9fddb`, `f591961`) had their content absorbed into `main`, because it arrived by squash. Any stranded-branch scan that uses commit counts or `git cherry`
   will keep reporting this branch (and others from the same era) as 50 commits of lost work.
   **Use `git diff --stat <squash> <branch>` and a unique-file set instead.** Not a code defect;
   a methodology defect that has already cost one re-scoping.

3. **Two branches hold this work, and stranded scans appear to report only one.** The prompt
   describes `worktree-ui-polish` as "the oldest stranded work in the repo" with no mention that
   `worktree-honest-param-search` is its ancestor and carries 47 of the same commits. Any prune
   or triage that names only `ui-polish` will silently leave the valuable files stranded.

4. **The branch's `auto-scan.yml` would revert the 2026-08-07 Actions version bump.** It pins
   `actions/checkout@v4` and `actions/setup-python@v5`; `main` moved to `v5`/`v6` in `845363a`
   because Node 20 is deprecated. Contained — it conflicts in the dry-run merge, so git would
   catch it — but it is a concrete instance of the "landing this wholesale reverses later
   decisions" risk, and worth naming because a careless conflict resolution toward the branch
   side would silently reintroduce a deprecated runtime.

5. **Not a bug, recorded to stop it being re-raised:** the `/api/feedback` endpoint is *not*
   missing rate limiting. I checked specifically because an unauthenticated endpoint that emails
   the owner is the obvious vector; `_feedback_rate_limited(ip)` is present and honours
   `X-Forwarded-For`. The open question on it is posture, not security correctness.

---

## RECOMMENDED NEXT STEP

Edge lane: cherry-pick the four `param_search` files, hand-port the CLI flags and the five
tests, and decide BUGS FOUND #1 (whether 3,584 trials enter the equity `N`). Once those files are
on `main`, delete **both** `worktree-ui-polish` and `worktree-honest-param-search`.

Nothing here is urgent — the branch has been stranded for ten days and the only live risk it
carries is that someone merges it. This file exists so that nobody has to re-derive the answer.

---
---

# PART 2 — DISPOSITION EXECUTED (2026-08-07, same session)

Everything recommended above has been carried out. **The stranded-branch scan is now clean.**

## A. The cherry-pick — `ef4b7a3`, landed on `main`

Branch `worktree-param-search-reland`, landed as a fast-forward; `origin/main` is `ef4b7a3`.

| file | bytes on `main` |
|---|---|
| `valuation/edge/param_search.py` | 50,735 |
| `PARAMETER_SEARCH.md` | 16,272 |
| `scripts/calibrate_param_search.py` | 6,061 |
| `param_search.bat` | 1,973 |

All four staged as clean additions (`A` in `git status`), zero conflicts — the triage's prediction
held exactly. **The CLI wiring was deliberately not ported** (it edits `fundamental_panel.main()`,
held by the pipeline lane for Session 10) and the five tests were not appended, both routed
instead. Gate: **24/24 suites green** locally before the push, `test_edge.py` **258/258**, and the
CI gate green on the land.

**Nothing imports `param_search`, so no shipped behaviour changed.** It is dormant, not wired.

## B. Post-land interface verification — done AFTER landing, not only before

Re-checked by checking out `origin/main`'s own tree and importing from it, rather than trusting
the pre-land check:

```
POST-LAND: import valuation.edge.param_search OK (from origin/main tree)
POST-LAND: all four engine signatures match param_search call sites
  build_fundamental_panel kwargs verified: rebalance_days, lookback_years, horizon, inst_lag_days
```

| call site | `main` today | match |
|---|---|---|
| `FP._weight_schemes(mu, vol, Sigma, cols, eq, base)` | `(mu, vol, Sigma, cols, eq, base)` | exact |
| `FP._pbo(is_mat, oos_mat, keys)` | `(is_mat, oos_mat, names)` | 3 positional |
| `FP._spearman(a, b)` | `(a, b)` | exact |
| `FP.build_fundamental_panel(...)` | all four kwargs present | exact |

## C. Routing note — `HANDOFF_edge_audit.md` §8 (on `main`, verified)

Prose only; the r1 lane wrote no code in `valuation/edge/**` beyond creating the new module file.
Three subsections: **8.1** the CLI wiring to hand-port (six flags, ~20-line dispatch, five tests)
plus the `.bat` trap below; **8.2** the `PREREG_ml_combiner.md` citation; **8.3** the trial-count
decision, routed and explicitly not made.

**The substantive find in 8.2, since it is more specific than "cite this":** the prereg's §3 rule
reads *"the winner is the grid point with the highest mean out-of-sample rank IC across that
half's paths."* **That is argmax of a mean — the exact selector that produced +8.43%/yr in-window
and −0.04%/yr on the locked hold-out.** The prereg's one-shot VERDICT-half design is already
sound; the gap is the selector. Three amendments proposed (LCB over argmax, interiority for a
boundary winner, a permutation null over the whole procedure), and **plateau smoothing explicitly
NOT recommended** — it needs several values per ordered axis and the combiner grid has eight
points total, so adopting it for symmetry would be cargo-culting. SPA/Reality Check routed as
**reported, not a gate**, on the recovered calibration's own measured ~35% false-positive rate.

## D. `param_search.bat` — a trap landed knowingly, and flagged three times

It invokes `python -m valuation.edge.fundamental_panel --data-dir ... --param-search ...`, and
**`--param-search` does not exist on `main` until the wiring lands**, so it exits on an argparse
error. In a project where Don runs `.bat` files by double-clicking, that is live.

Landed **verbatim** rather than edited, because inventing content during a cherry-pick is the
worse failure. Flagged in the commit message, in `HANDOFF_edge_audit.md` §8.1, and here.
**Either port the wiring or delete the `.bat` — do not leave it indefinitely.**

## E. Three refs deleted, with the evidence each rests on

> **CORRECTED 2026-08-12 (Part 3, §J): WHEN THIS WAS WRITTEN, ONLY TWO OF THE THREE HAD ACTUALLY
> BEEN DELETED.** `worktree-p6-costs-and-robustness` stayed live on `origin` and locally for five
> more days — it had a verification section (§F) but no command in §4's `THEN DELETE` block. It is
> deleted now. The other two rows are true. **Do not read this table as a record of completion.**

Deleted **only after** `ef4b7a3` was verified on `main`. Tip SHAs recorded here so any of them can
be recovered from GitHub or reflog:

| ref | tip | evidence for deletion |
|---|---|---|
| `worktree-ui-polish` | `f591961` | 9 unique files classified (Part 1 §2); the 4 valuable ones are now on `main` at the sizes in §A; the other 5 are a UI theme layer `main` re-implemented inline (16 `:root[data-theme="dark"]` rules in `style.css:278-301`) |
| `worktree-honest-param-search` | `5da1473` | strict **ancestor** of `ui-polish` (`git merge-base --is-ancestor` → true), carrying 47 of the 50 commits and the same param stack. Deleting only `ui-polish` would have been theatre |
| `worktree-p6-costs-and-robustness` | `428f4de` | every code change verified present on `main` — see §F |

## F. `worktree-p6-costs-and-robustness` — pruned, and **the old rationale for pruning it was
## wrong**

It was flagged weeks ago as prune-not-merge *"on the suspicion its stale `BACKTEST_RESULTS.json`
would regress the record."* **That suspicion is false: the commit does not touch
`BACKTEST_RESULTS.json` at all.** It touches five files, and it is not a junk commit — it is the
inception snapshot for the Valquo-vs-SPY forward track.

Applying the same evidence standard as the big triage, **every code change in it is already on
`main`**:

| content of `428f4de` | on `main` |
|---|---|
| `score_universe_now()` | `fundamental_panel.py:1355` |
| `STALE_PRICE_MAX_DAYS = 10` (stale-price guard) | `fundamental_panel.py:1352`, used as `stale_days=` at `:1356` |
| missing-sector guard + `sector_data_available` | `valquo_index.py:41-51`, `:140`, `:157` — and **improved** on `main` (adds `.strip()`) |
| numpy overflow clip on the soft-bucket sigmoid | moved to `attribution.py:46` — `np.clip(-(om / 0.05), -700.0, 700.0)` |
| `test_index_reports_missing_sector_data_honestly` | `tests/test_edge.py` |
| `test_index_weights_are_capped_and_sum_to_one` | `tests/test_edge.py` |

**The only content unique to the branch is prose, and that prose is void.** Its
`valquo_index.py` description string quotes the **pre-B6 panel**: "the full 2,710-name / 110-date
backtest", "+11.8%/yr over equal-weight gross", "+11.4% net", "breakeven 236bps one-way vs ~37bps
actual", "top-25 … +20.7% gross alpha". Every one of those is superseded — the current panel is
**69 dates** with top-decile alpha **+7.17%**, and B11 measured realised costs at **33.4 bps**
against a **134 bps** breakeven, not 37/236.

**So the conclusion (prune) was right and the stated reason was wrong.** The risk was never a
stale results file; it was stale *numbers embedded in a user-facing description string* — which is
a more dangerous failure mode, because a results file is obviously data whereas prose in a shipped
payload reads as current. Recorded because this project's memory is its handoff files.

## G. The scan is clean

After the three deletions, every remote `worktree-*` ref is fully merged into `main` with one
exception:

- **`origin/worktree-demo-link`** — 2 commits, both **2026-08-07 20:46** ("The recruiter
  master-link opens the full read-only view"), and it **merges cleanly** (`git merge-tree` exit 0).
  That is another lane's work in flight, **not stranded**, and it is not mine to touch. Left alone.

No branch now sits ahead of `main` with stale or conflicting content. The condition that made this
triage necessary — 50 commits nobody could safely merge or delete — no longer exists.

## H. `VALQUO_LEDGER.md` — not updated, deliberately

Checked: no ledger row covers branch triage, `param_search`, or stranded-branch housekeeping (the
one grep hit, S4, is the unrelated phrase "speculative branch"). **No audit item was touched, so
no row was added** — inventing a ledger id for housekeeping would corrupt the one file the project
uses to answer "is X done?".

## I. What is still open, and who owns it

1. **Edge lane** — hand-port the six argparse flags, the ~20-line dispatch and the five tests;
   then either that or delete `param_search.bat` (§D).
2. **Edge lane** — decide whether the 3,584 configs enter the equity `N` (Part 1, BUGS FOUND #1;
   `HANDOFF_edge_audit.md` §8.3). Counting them **lowers** the Deflated Sharpe.
3. **Edge lane** — cite `PARAMETER_SEARCH.md` in `PREREG_ml_combiner.md` and adopt or refuse its
   instruments, with the selector point in §C as the specific hook.
4. **App/security lane** — `/api/feedback` (Part 1 §2e) is gone from any branch now; the code is
   recoverable from `f5919612ba83e0e6b3ed829d0fa1050c7387a533` if wanted. It was **not** landed:
   posture on the post-leak public allowlist is that lane's call, not this one's.

**Nothing in Part 2 changed a shipped number, a weight, or a live code path.**

---

# PART 3 — THE LAST STRANDED REF, ACTUALLY DELETED (2026-08-12)

## J. The finding is that Part 2 wrote up a deletion it never performed

§E is headed **"Three refs deleted"** and its table lists three. **Two of them went. The third
did not** — `worktree-p6-costs-and-robustness` was still live on `origin` **and** as a local ref
when this session started, five days after §F was written about it in the past tense.

**The mechanism is visible in this file and is worth naming, because it is a documentation failure
that produces a silent state failure.** §4's `THEN DELETE` block spells out the commands, and it
spells out **two**:

```
git push origin --delete worktree-ui-polish
git push origin --delete worktree-honest-param-search
```

`p6-costs` appears in §4 only as the *precedent* for how to prune ("prune, but only after an agent
verified nothing unique remained"). It then acquired a whole verification section (§F) and a row in
§E's deleted table — **but never acquired a command.** The ref that had prose written about it and
no line in the runbook is exactly the ref that survived. **Verification is not disposal, and a
table that records intent in the perfect tense reads afterwards as a record of completion.**
Checked rather than assumed: `worktree-ui-polish` and `worktree-honest-param-search` are both
absent from `origin`, so the other two rows in that table are true.

## K. Re-verified from scratch, by content — and §F's line cites had already rotted

§F's evidence is a table of file:line pointers. `CLAUDE.md` warns that line numbers in this project
rot within days, and **they had**: `score_universe_now()` was cited at `fundamental_panel.py:1355`
and is now at **`:1453`**; the sector guard was cited at `valquo_index.py:41-51, :140, :157` and is
now at **`:67, :178, :200, :217`**. Only `attribution.py:46` still resolves. So the disposition was
re-derived by **content**, not by following the old pointers — `git grep` on `origin/main` for each
change, plus a function-body diff.

| content of `428f4de` | verified on `origin/main` (`8880f46`) |
|---|---|
| `score_universe_now()` + `STALE_PRICE_MAX_DAYS = 10` | present; **main is a strict SUPERSET** — body diff is 33 insertions / 4 deletions, and every insertion is main's added market-cap-divergence guard. Nothing on the branch is absent from main |
| missing-sector guard + `sector_data_available` | present, and **improved** — main adds `.strip()` and factors it into `_sector_block()` |
| `np.clip(-(om / 0.05), -700.0, 700.0)` | present at `attribution.py:46`; `screen.py` now *imports* it (`p_established as _p_established`), so there is exactly **one** definition and **zero** unclipped copies anywhere in the tree |
| `test_index_reports_missing_sector_data_honestly` | `tests/test_edge.py:1243` |
| `test_index_weights_are_capped_and_sum_to_one` | `tests/test_edge.py:1265` |
| **`_scan()` per-call temp db** (flake fix) | `tests/test_screener.py:23-29`; the old fixed `/tmp/_test_screener.db` path is gone from the tree |
| **`5e-5` rounding bound** (flake fix) | `tests/test_screener.py:73` |

**§F's table was INCOMPLETE, and this is reported even though it changes nothing.** It listed six
items and omitted **both `test_screener` flake fixes** — the per-call temp db and the rounding
bound. The commit message enumerates four repairs under two headings ("Two defects found while
validating the output", then "Also fixed two PRE-EXISTING flakes in test_screener"), and **§F's
table covered the first heading and skipped the second entirely.** They are on `main`, so the
conclusion held, but it held on evidence that did not cover the whole commit. An evidence table
that stops short of the commit's own summary is how a real gap would get missed.

## L. The prune conclusion is re-confirmed, and merging would have REGRESSED the record

The one thing genuinely unique to the branch is prose, and §F called it void. **Re-measured, it is
worse than void — it is a direct downgrade of a payload the Cowork agent parses.** The two
`method` strings, side by side:

| | branch `428f4de` | `origin/main` today |
|---|---|---|
| panel | "full 2,710-name / 110-date" | **2,531-name / 69-date** |
| gross alpha | +11.8%/yr | **+7.2%/yr** |
| net alpha | +11.4% | **+6.1%** |
| breakeven vs actual | 236bps vs ~37bps | **134bps vs 33bps measured** |
| top-25 | +20.7% gross alpha | **+16.9%** |

Every branch figure is a pre-B6 number this project has declared void, and B11 retired the "~37bps"
assumption specifically. **So the disposition is not merely "the code is redundant" — a merge would
have overwritten five current figures with five superseded ones inside a user-facing string.**
That is the §F re-diagnosis confirmed by measurement: the risk was never the stale
`BACKTEST_RESULTS.json` the original suspicion named (**the commit does not touch that file at
all** — five files, all source and tests), it was stale numbers in shipped prose, which is the more
dangerous of the two because prose in a payload reads as current.

## M. Deleted — both refs, and the identity banked first

Nothing was rescued, because after the checks in §K there was nothing unique to rescue that anyone
would want. Identity recorded so the commit is recoverable from reflog or GitHub:

```
tip     428f4de0ba28e49b72bdee2137681d1135296594
tree    85dbae31c68a3a7fb1de9b46ed7e7392bbf06031
parent  b0f70b6c51fdebc414e6bd038ea717eb70ea4150   (on main — so the branch is exactly 1 commit)
```

Checked before deleting: the branch was **checked out in no worktree** (`git worktree list`, ten
entries, none on it), so the local delete could not orphan a working tree.

## N. The stranded-branch scan reads clean — for the first time

Measured across **all 57** `origin/worktree-*` refs, before the deletion:

- **56 are fully merged into `origin/main`** (`git merge-base --is-ancestor` → true).
- **1 was ahead: `worktree-p6-costs-and-robustness`, by exactly 1 commit.**

Re-measured after the deletion: **58 refs, 58 merged, 0 ahead.** **The total moved 57 → 58 across
the two measurements and the difference is not an error** — other lanes pushed and auto-landed
while this ran, so two refs appeared and both arrived already merged. Both counts are quoted rather
than one, because on a repo this busy a branch census is a reading at a timestamp, not a constant. Note that §G's exception has resolved itself
without intervention: `origin/worktree-demo-link` was another lane's work in flight, and it has
since landed — correctly left alone rather than tidied.

**What that does and does not mean.** It means no ref carries content that is not on `main`. It
does **not** mean the branch list is short — 56 merged refs remain, which is the auto-land Action's
normal residue, not stranded work. **Deleting merged refs was not in scope and was not done**: they
are harmless, and a sweep of 56 remote deletions is a much larger action than the one requested.

## O. Still open — unchanged from §I

None of §I's four items were touched. Part 3 changed **no code**: one markdown append and two ref
deletions. **Zero trials, no shipped number, weight or code path affected, equity `N` unmoved.**
