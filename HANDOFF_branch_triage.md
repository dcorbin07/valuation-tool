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
