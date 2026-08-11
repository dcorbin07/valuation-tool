# HANDOFF — CI: stop the auto-land churn (r1 lane, 2026-08-07)

## STATUS: LANDED AND VERIFIED ON `main`

Commits `f47661c`, `f11cdec`, `52e1c01`, landed as `343465d`. Confirmed present on `origin/main`:
`.gitattributes` with 4 union rules; `land-agent-branch.yml` carrying the per-branch concurrency
group, `code_changed()`, the `exit $fail` literal, `checkout@v5` and `setup-python@v6`.
`tests/test_edge.py` **249/249**; full 24-suite gate green locally.

**The union merge has already proved itself in practice**, not just in the scratch test: the merge
of `origin/main` that produced `343465d` pulled in another lane's `HANDOFF_STATUS.md` edits and
resolved with **zero conflict markers and no hand-editing** — the first such merge since
`.gitattributes` existed, on the exact file that caused every previous conflict.


Out-of-band infrastructure. Nothing under `valuation/**` touched; I own `.gitattributes` (new),
`.github/workflows/**` and this file.

**Headline, in one line each:**

1. **Conflicts:** `.gitattributes` now gives `HANDOFF_STATUS.md`, `RESEARCH_LOG.md` and
   `HANDOFF_*.md` a **union merge**, so "keep both sides" happens automatically. Tested, not
   assumed.
2. **`VALQUO_LEDGER.md`: union REJECTED**, deliberately. Reasoning in §2 — it is a keyed table
   and union's failure mode silently breaks its one guarantee.
3. **Dropped runs: CONFIRMED, and the cause is the `concurrency: land-main` group.** Exactly one
   branch silently failed to land — **`worktree-r1` @`3fb0809`, mine**. Fixed by scoping
   concurrency per branch.
4. **The "auto-land Action is down repo-wide" note (`21fbe46`) is REFUTED by evidence.** The
   Action was healthy the whole time and landed four other branches during the window.

---

## 1. ITEM 1 — `.gitattributes` (new file; the repo had none)

### What churns, measured

Distinct commits touching each shared file across all refs, 2026-08-04 → 08-06:

| file | commits / 3d | shape | union? |
|---|---|---|---|
| `HANDOFF_STATUS.md` | **29** | every lane **prepends** a section at the top | **yes** |
| `CLAUDE.md` | 19 | corrections made **in place** | **no** |
| `VALQUO_LEDGER.md` | 16 | keyed table, one row per audit item | **no** — §2 |
| `RESEARCH_LOG.md` | 5 | append-only table, rows added at the end | **yes** |
| `RUN_RULES.md` | 1 | stable | no |
| `CODE_AUDIT.md` | 0 | stable | no |

`HANDOFF_STATUS.md` is the obvious one and the measurement confirms it: every lane writes to the
*same lines* (the top of the file), so collisions are structural rather than unlucky. Both
conflicts this lane hit were at line 20, and both were resolved by hand with the same answer.

**`CLAUDE.md` is the one the churn number would have led you astray on.** It is second-highest at
19 commits/3d, but its edits *replace* — "this claim was wrong, here is the right number". Union
would leave the old and the new claim side by side in the file every session reads as fact. It is
excluded, and the reason is written into `.gitattributes` so nobody adds it later for tidiness.

### Proof it works

Not taken from documentation — run in a scratch repo against the real `.gitattributes`, reproducing
the exact collision shape (two lanes each prepending a section):

| file | two lanes did | result |
|---|---|---|
| `HANDOFF_STATUS.md` | both prepended a section at the top | **both sections kept, no markers** |
| `RESEARCH_LOG.md` | both appended a different row | **both rows kept** |
| `VALQUO_LEDGER.md` | both edited the **same** row `B1` | **conflict markers** — proves it is excluded |

### What I did NOT add

**`* text=auto`**, the usual first line of a `.gitattributes`. This repo has CRLF working copies;
enabling it would renormalise line endings across the whole tree — a diff touching nearly every
file, conflicting with every branch currently open. That is the exact churn this file exists to
reduce. Left off deliberately.

---

## 2. THE `VALQUO_LEDGER.md` DECISION — union is WRONG for it, and here is why

**Decision: no union.** The prompt asked me to decide rather than assume, and the two files look
similar but are not.

`HANDOFF_STATUS.md` is a **log**: append-per-lane, no key, duplication is visible and harmless.
`VALQUO_LEDGER.md` is a **keyed table** — "one row per external-audit item (134 items)", and its
own contract says it "replaces reconstructing project state from git history".

Three reasons, in order of weight:

1. **Union's failure mode here is silent and it breaks the file's only guarantee.** Two lanes
   editing the same row produce **two rows with the same id and no rule for which wins**. Two
   `| B1 |` rows sixty lines apart look completely normal in a 135-row table, and the next agent
   reads whichever it hits first as fact. A conflict is loud; a duplicate key is not.
2. **The ledger conflicts *less* than the raw churn number suggests.** Its 16 commits/3d are spread
   across 134 distinct rows, so ordinary 3-way merge already resolves most concurrent edits with no
   help. A conflict means two lanes touched the **same row** — precisely the case where "keep both"
   is wrong and someone should look.
3. **It already has a better recovery path.** `python scripts/build_ledger.py` regenerates it from
   `valquo_audit_items.json` plus the corpus, and will not overwrite `src=human` rows — it reports
   the disagreement instead. So the answer to a ledger conflict is "regenerate and reconcile", which
   is strictly better than "concatenate and hope".

**If ledger conflicts do become frequent, the alternative I would take is not union** but splitting
it by series (B / M / O / R / S / X) into one file per series, so lanes working different series
stop sharing lines at all. That preserves the one-row-per-item guarantee instead of trading it away.

### The contrast that decided `RESEARCH_LOG.md` the other way

`RESEARCH_LOG.md` is also a keyed table, so the same objection applies — but its failure direction
is the opposite, and that is what settles it. `valuation/edge/research_log.py:_parse` counts **every**
table row and never dedupes by id, so a union duplicate inflates `N`. A larger `N` raises
`sr0_benchmark` and **lowers** the Deflated Sharpe — it makes this project's own bar *harder*, never
easier. **A union artefact in the research log cannot flatter a result**, which is exactly the
property the ledger lacks. (Worth adding a duplicate-id check to `_parse` anyway; that file is
another lane's, so it is listed under BUGS FOUND rather than changed here.)

---

## 3. ITEM 2 — dropped runs: CONFIRMED, with the evidence

**Answer: `concurrency: land-main` was cancelling queued runs. Branches silently never landed.**

### The mechanism

GitHub allows only **one pending run per concurrency group**. If a run is executing and a second is
pending, a third arrival **cancels the pending one outright** — no failure, no red X, no annotation.
`cancel-in-progress` does not control this; it governs *running* jobs, not queued ones. Every
`worktree-*` push shared the single group `land-main`, so with five or six lanes pushing, a branch
that lost the pending slot never ran at all.

### The evidence (all times UTC)

| time | event |
|---|---|
| 21:45, 21:46 | `worktree-r1` pushes `8e3b372`, then `3fb0809` |
| 22:33 | another lane commits `21fbe46` — *"the auto-land Action is down repo-wide"* |
| — | `worktree-options-live`, `worktree-p24-shortinterest`, `worktree-optionsbot-lane` **all land** |
| 00:20 | `worktree-r1` pushes `21d0bc9`, an **empty** commit, purely to re-trigger |
| ~00:31 | `3fb0809` lands as `5f70750` — the same tree that had sat unlanded for 2h34m |
| 00:31 → 00:37 | `worktree-s124-picks` pushes and lands in ~6 min |

Three things follow, and they are independent:

- **The Action was healthy.** It landed four other branches across the same window. Whatever stopped
  `3fb0809` was selective, so "down repo-wide", "out of minutes", "disabled" and "permissions" are
  all refuted — every one of those is repo-wide and would have blocked the others too.
- **It was not a conflict.** `3fb0809` test-merged cleanly against `origin/main` throughout, and it
  landed with no conflict resolution the moment it got a runner.
- **It was not a test failure.** The content was markdown-only, and the identical tree passed on
  re-trigger.

That leaves a cancelled queued run, which is what the concurrency rule predicts.

**One caveat on reading those timestamps, so nobody over-reads them later:** a commit's date on
`main` is when CI *created the merge commit* (start of the land step) or when the branch commit was
*authored* for a fast-forward — **not when it landed**. Land times are therefore later than the
table shows, and latency is understated. The 2h34m gap is measured from my own push, which is a real
observation, but do not treat these as land timestamps.

### Was any *other* branch silently dropped?

**No — exactly one, and it was mine.** I checked every remote `worktree-*` branch for commits not on
`main`, and whether each merges cleanly (ahead + clean = a land that should have happened):

| branch | ahead | merges | verdict |
|---|---|---|---|
| `worktree-s124-picks` | 3 | clean | **landed at ~00:37 while I was writing this.** Not a drop — it was 1 minute old when I first looked, and I nearly reported it as one. |
| `worktree-honest-param-search` | 47 | CONFLICT | pre-dates the Action (added 2026-08-02); last commit 07-28 |
| `worktree-ui-polish` | 50 | CONFLICT | same, 07-28 |
| `worktree-p6-costs-and-robustness` | 1 | CONFLICT | same, 07-31 |

The three stale ones are from the **manual-merge era before the Action existed**, so they were never
auto-land candidates and are not CI drops. They are flagged below anyway, because one of them looks
like real lost work.

### The fix

Two changes in `land-agent-branch.yml`, both contained — **no settings change is needed from Don**:

1. **`concurrency: group: land-${{ github.ref }}`** — per branch. One lane's push can no longer
   cancel another lane's queued run. Within a branch a newer push still supersedes an older queued
   one, which is correct: the newer commit contains the older.
2. **A merge → test → push cycle that retries as a whole (3 attempts).** Removing the global group
   means two runs can now finish together and both try to push `main`; the loser is rejected as
   non-fast-forward. **Retrying the push alone would ship a tree that never passed the gate in that
   combination**, so the retry re-merges onto the new tip *and re-runs every suite*. The gate is not
   weakened — every commit reaching `main` is still a tree that passed all suites exactly as it
   stands. This replaces the serialization the old group provided, at the layer where it belongs.

3. **The retry skips the gate when only documentation landed under us.** This was NOT in the first
   version of the fix; it was forced by watching the fix run — see below.

If all 3 attempts lose the race the job fails loudly telling you to push again — a red X, never
silence. That is the whole point.

### The retry alone was not enough, and the fix's own land is what proved it

Landing this branch exposed a livelock that the design review had missed. **The gate is 24 suites
and takes ~20 minutes; `main` was landing a new commit roughly every ~10.** So attempt 1 finished,
found `main` had moved, and started attempt 2 — which was also overtaken. Observed live:
`0bb4b72` landed during attempt 1, `ff39eb0` during attempt 2. With three attempts each costing a
full gate, a branch can burn an hour and still fail.

**Removing the global concurrency group trades dropped runs for lost races.** That is the right
trade — a race fails loudly and a drop does not — but only if a race is cheap to lose.

What made it cheap: **the commits winning those races were markdown handoffs.** `ff39eb0` touches
`HANDOFF_STATUS.md` and nothing else. If the commits that landed under us contain no code, the
merged tree's code is byte-identical to the tree that just passed every suite, so re-running the
gate is provably unnecessary. The loop now checks:

```sh
code_changed() {
  [ -n "$(git diff --name-only "$1" "$2" -- . ':(exclude)*.md' ':(exclude).gitattributes')" ]
}
```

and re-merges-and-pushes without re-testing when that is empty. Anything not markdown counts as
code — **including `.yml`**, so a workflow change never skips the gate. Verified against real
commits in this repo before it went near CI:

| range | expected | got |
|---|---|---|
| `ff39eb0~1..ff39eb0` (HANDOFF_STATUS.md only) | docs | **docs** |
| `f47661c~1..f47661c` (my commit — adds a `.yml`) | code | **code** |
| empty range | docs | **docs** |

This turns the common retry from ~20 minutes into seconds, which is what makes the concurrency fix
survivable under this repo's churn. **The gate is still not weakened:** every commit reaching `main`
is a tree whose *code* passed every suite, and the only thing allowed to differ is markdown.

**Honest note on how this was found:** I proposed it as an optional refinement, then watched my own
branch lose two races in a row and promoted it to required. The first design was correct and
impractical; that distinction only showed up by running it.

### …and the thing that was ACTUALLY blocking the land was not a race at all

I spent three watcher cycles attributing the delay to lost races. **It was a failing test**, and I
found it only by running the 24-suite gate locally instead of waiting again.

Another lane landed `90fd576` ("Verify the test gate by exit code, and check CI for the same flaw")
**while my run was in flight**. It adds `test_audit_c7_every_test_suite_gates_the_auto_merge` to
`tests/test_edge.py`, which reads `land-agent-branch.yml` and asserts two literal strings:

```python
assert "for f in tests/test_*.py" in wf, "the gate must run every suite, not one"
assert "exit $fail" in wf, "one red suite must not be hidden by a later green one"
```

My rewrite kept the first and broke the second — I had replaced `exit $fail` with
`[ "$fail" -eq 0 ] || exit 1`, which does exactly the same thing and does not contain the string.
So the CI job merged onto the new `main`, ran the gate, and failed on 247/248. **From outside that
is indistinguishable from losing a race: `main` does not move and nothing tells you why.**

**Resolved in my file, not theirs.** The workflow now uses `if [ "$fail" -ne 0 ]; then exit $fail; fi`
— same behaviour, keeps the literal, with a comment saying why so nobody "simplifies" it back.
Editing another lane's assertion to fit my code would have been the wrong direction: their
assertion's intent is sound and `tests/test_edge.py` is required to stay green. **248/248.**

**Two lessons worth more than the fix:**
- **A structural test that greps a config file is brittle to a legitimate rewrite, and that is the
  price of it being cheap.** It caught a real class of regression here, so it earns its place — but
  anyone rewriting `land-agent-branch.yml` must run `tests/test_edge.py`, not just validate YAML.
  I validated the YAML and thought that was sufficient. It was not.
- **When CI goes quiet, run the gate locally before theorising about the runner.** I had a
  plausible, evidence-backed race story and it was wrong for this particular delay. The race is
  real and documented above — it just was not what was happening this time.

---

## 4. ITEM 3 — deprecated action versions

`land-agent-branch.yml`: `actions/checkout@v4 → v5`, `actions/setup-python@v5 → v6`. Non-blocking;
they were being forced onto Node 24 because Node 20 is deprecated.

**`auto-scan.yml` and `track-backup.yml` were deliberately left on the old versions for one land,
then bumped.** They use the same actions, so the bump is mechanical — but `auto-scan.yml` runs the
production scans with live secrets, and bumping it on the *assumption* that `v5`/`v6` resolve is
exactly how you break scheduled scans. Landing this branch proved they resolve, because the land
Action is the thing that ran them. **Both are now bumped, with evidence rather than hope.** That
ordering is the whole difference between a verified change and a hopeful one, and it cost one land.

**Left alone: `actions/cache@v4`** in `auto-scan.yml`. The prompt named `checkout` and
`setup-python`; I have no evidence about the current major for `cache` and did not want to guess at
a version number inside the production scan workflow. Worth checking separately.

**Still unverified, and stated plainly:** `auto-scan.yml` and `track-backup.yml` are on schedules
and need live secrets, so **I could not execute them.** What is verified is that the two action
versions resolve (proved by the land) and that all three files parse. The first scheduled run is
the real test; if a scan red-Xes, revert those two files to `@v4`/`@v5` — nothing else in this
change touches them.

---

## 5. Verification

- Union merge behaviour **executed** in a scratch repo against the real `.gitattributes` (§1) — all
  three files behaved as designed, including the ledger correctly still conflicting.
- All three workflow files **parse** (`yaml.safe_load`), and `land-agent-branch.yml` reports
  `concurrency = {group: land-${{ github.ref }}, cancel-in-progress: False}` with the four steps in
  order.
- `code_changed()` **executed against real commits** in this repo (table in §3), including the
  conservative case that a `.yml` change counts as code.
- **This branch was landed through the modified Action itself.** A CI fix that has not passed
  through CI is a claim, not a result — and this one earned the distinction: the first version
  passed review and then livelocked in practice.

**One bootstrap detail worth knowing, because it cuts both ways:**

- **The concurrency fix protected its own land.** For `push` events GitHub runs the workflow file
  **from the pushed commit**, not from `main` — so this branch's run already used the per-branch
  group and could not be cancelled by another lane.
- **The union merge did NOT apply to its own land.** `git merge` reads `.gitattributes` from the
  working tree, which is `main` — and `main` did not have the file yet. It takes effect for every
  merge *after* this one.
- **Other lanes keep the old behaviour until they merge `main`.** Their branches still carry
  `concurrency: land-main` in their own copy of the workflow, so they can still cancel *each
  other's* queued runs. This is self-healing — each lane picks up the fix the next time it merges
  `main` — but it means the drop symptom can recur once or twice more before it stops.

---

## BUGS FOUND

1. **`concurrency: land-main` silently dropped branches.** The headline of this handoff. A pending
   run cancelled by a newer arrival produces no failure signal anywhere — the branch simply never
   lands, and the agent watching it sees nothing move. Fixed. **This is worse than the noisy
   conflicts it was masking**, because a conflict at least tells you it happened.
2. **An agent recorded a repo-wide outage that did not exist** (`21fbe46`, "the auto-land Action is
   down repo-wide"). Four branches landed during the window it describes. The symptom was real and
   the diagnosis was wrong, and it went into the shared project-state file as fact. Worth a line in
   `RUN_RULES.md`: *before recording an outage, check whether anything else landed.*
3. **`param_search.py` is absent from `main`.** `worktree-honest-param-search` (2026-07-28, 47
   commits) contains "Edge Lab: an honest parameter-search protocol (`param_search.py`)" plus "the
   tuned winner fails out of sample" — and no file matching `param_search` exists anywhere on `main`.
   It pre-dates the Action so this is not a CI drop, but it looks like **real research work stranded
   in the manual-merge era**, which is the exact failure CLAUDE.md's git-handoff rule warns about.
   Someone should decide whether to rescue or delete it; it conflicts heavily, so it is not a
   mechanical merge. Same question for `worktree-ui-polish` (50 commits).
4. **`research_log.py:_parse` does not dedupe by id.** Pre-existing, and not introduced by the union
   merge — but union makes a duplicate row reachable, so it is now worth guarding. It already
   collects `ids`, so the check is a few lines. The failure direction is self-penalising (§2), which
   is why this is a nice-to-have rather than a blocker. Not changed here: `valuation/**` is out of
   scope for this lane.
5. **A 24-suite gate and a busy `main` livelock each other.** Not a bug in anything anyone wrote —
   an emergent property of gate duration (~20 min) exceeding the interval between lands (~10 min).
   Any serialization scheme has to survive it. Mitigated here by skipping the gate for docs-only
   races (§3), which works precisely because this repo's churn is markdown. **If the code churn rate
   ever rises to match, this comes back**, and the answer then is a faster gate (parallel suites, or
   only running suites affected by the diff), not more retries.
6. **A failing gate and a lost race look identical from outside.** Both present as "`main` does not
   move." Without the Actions UI (no `gh` on this machine) the only way to tell them apart is to run
   the gate locally. I got this wrong for ~30 minutes, and the fix is procedural: **when a land is
   slow, run `for f in tests/test_*.py; do python "$f"; done` before theorising about the runner.**
7. **Structural CI tests are brittle to legitimate rewrites — by design, and worth it.**
   `test_audit_c7_every_test_suite_gates_the_auto_merge` asserts the literal string `exit $fail` in
   `land-agent-branch.yml`. My rewrite preserved the behaviour exactly and broke the string. That is
   a false positive in the strict sense, but the assertion is cheap and the failure it guards
   (a red suite hidden by a later green one) is severe, so it should stay. **The requirement it
   creates: anyone editing `land-agent-branch.yml` must run `tests/test_edge.py`, not just validate
   the YAML.** Now noted in the workflow itself, next to the literal.
8. **The old workflow could push an untested combination, and still can in one narrow case.** The
   job checks out `main`, merges, tests, then pushes. If another lane landed during the test run the
   push was rejected — loudly, so no harm. My retry now re-merges *and re-tests*, closing that. But
   note the general shape: the tested tree and the pushed tree are only identical because the push
   is rejected otherwise. That guarantee rests on `git push` being non-fast-forward-safe, which it
   is — worth knowing if anyone ever adds `--force` anywhere near this file.

---

# Repo records cleanup (r1 lane, 2026-08-09)

Two commits. **Thirteen files that govern this project were never in git**; six executed era
prompts and one superseded status doc were carrying on in the working tree. Gate: **26 suites,
0 failing** before the push.

## Commit 1 — `Repo records: commit the untracked project-governing files.`

13 files, 5,795 insertions plus a 7.8 MB PDF. The audit's own **input** was untracked while
`VALQUO_LEDGER.md` — one row per item in it — has been tracked all along; that asymmetry is why
`build_ledger.py` carries `SEARCH_DIRS = [ROOT, ROOT.parent.parent.parent]`, reaching outside the
repo to find `valquo_audit_items.json`. With the file tracked, that fallback is now a
belt-and-braces path rather than the only one. **Given the backup drive is dead, "exists on one
disk, untracked" was the project's single largest unforced risk.**

Also tracked: `VALQUO_EDGE_AUDIT.md`, the delivered PDF catalogue, the dependency map, the action
plan (NO-SKIP + SEQUENCING verbatim), the master roadmap, state-of-play, the auditor's original
protocol, the Option E record, `AGENTS.md`, `check_lanes.py`, `sync.bat`.

**`AGENTS.md` is worth singling out: four of the ledger's five BLOCKED rows (R4, R5, R6, R8) are
blocked by lane ownership defined in it** — that is, the ledger's blockers referenced a file that
was not in the repo.

### `RUN_RULES.md` was on the list and needed nothing
Already tracked. Its main-checkout copy differs from the tracked file by 80 bytes, and that is
**line endings only** — `Compare-Object` reports the two identical line for line. Recorded so the
next reader does not re-investigate an 80-byte delta.

### The secret gate ran BEFORE `git add`, not after
Checked for `sk-ant-*`, `sk-*`, `AKIA*`, `gh?_*`, `xox?-*`, PEM private keys, bearer literals,
`NAME=<12+ chars>` and 40+ char hex, plus a soft pass over secret vocabulary. **68 hard hits, all
in the PDF, all cleared by decoding rather than by assumption**: they are hex-encoded PDF text
strings whose font maps CID+29, so `0037004B0048` is `The`, `0037004B004C` is `Thi`.

`VALQUO_MASTER_ROADMAP.md` names `TRADIER_PAPER_TOKEN`, `TRADIER_PAPER_ACCOUNT_ID`, `ADMIN_TOKEN`
and `DISCORD_WEBHOOK_URL` — **names only, in instructions about what Render's env must hold, no
values**. `sync.bat`'s flagged lines are `git for-each-ref` loops; it carries no credential.
`.env` untouched and still ignored; `data/` and `*.db` untouched.

**Keep the soft pass.** `ADMIN_TOKEN` was not in the hard pattern list and only the soft pass
surfaced it. A scanner that only reports what it was told to look for cannot tell you what you
forgot.

## Commit 2 — `Retire superseded era documents.`

7 files, 567 deletions: the six options-era prompts and `WHERE_WE_STAND.md`.

### `WHERE_WE_STAND.md` was NOT a tracked file being retired
The task said to `git rm` it because "history preserves them". **It didn't.** `git log --
WHERE_WE_STAND.md` was empty and `git ls-files` never listed it: it was an untracked 11 KB
document whose only copy was on one disk. `git rm` would have failed on it, and deleting it would
have been unrecoverable — not a retirement.

**So it was committed in commit 1 and removed in commit 2.** Net effect on the tracked tree is
exactly what was asked; the difference is that the content still exists, at
`git show a91dae5:WHERE_WE_STAND.md`. **The generalisable check: before retiring anything on the
grounds that history holds it, confirm history actually holds it.** One `git log --` is cheap;
this file was 177 lines of project narrative.

### Two dangling references, created deliberately and flagged not silenced
`VALQUO_MASTER_ROADMAP.md:59` sends "full narrative status + edge assessment + the generational
product plan" to `WHERE_WE_STAND.md`, and `:240` sends PHASE 9's detail to the same place. Both
now point at a path not in the tree.

**Left as-is rather than repointed at `VALQUO_STATE_OF_PLAY.md`**, because the two are not the
same document and I did not verify that state-of-play carries PHASE 9's product detail. Silently
repointing a reference at a file that may not answer it is worse than a reference that is visibly
stale. **Fix by reading both, then either repointing or restoring the section.**

`PROMPT_options_A2A5.md:5` referenced `PROMPT_phase4_big.md`; both leave together, so that one
does not dangle.

### Why the six prompts are safe to drop
Executed briefs. Findings live in the ledger, `HANDOFF_universe_backtest.md` and CLAUDE.md's
options section, and the entry signal they were written to develop has since been measured dead on
corrected data (real +3.27%/trade vs a random-entry control's +8.33%, sign test z −4.961 — CORRECTED 2026-08-11, `U1-SPLIT`; was +3.41 / +10.06 / −4.903).
**A superseded plan left in the tree invites a reader to treat it as a live one.**

Untouched as instructed: every `HANDOFF_*.md`, every results file and register, `RUN_RULES.md`,
and the two prompts still in force (`PROMPT_edge_audit_execution.md`,
`PROMPT_session14_commit_option_e.md`).

## File-count attribution — most of the change is not mine

**Cowork separately deleted 73 executed untracked prompts directly on disk.** Those were never
tracked, so they appear in **no commit here**. If the root directory looks ~80 files lighter:
**73 is Cowork's deletion, 7 is commit 2.** Recorded because a git-only reading of the repo would
otherwise credit this lane with a cleanup it did not do.

**One consequence Don should know:** because Cowork's 73 were untracked and are now deleted, they
are gone permanently — there is no `git show` for them, same class of loss that
`WHERE_WE_STAND.md` avoided by one commit.

## Residual: the main checkout still holds its own untracked copies

Committing here does not remove the untracked originals sitting in
`C:\Users\donni\Downloads\valuation-tool\`. Once this lands, those paths become tracked and the
on-disk copies simply become the working-tree files — **except `WHERE_WE_STAND.md`, which lands as
deleted while an untracked copy remains on disk.** Harmless, but it means the file will still be
visible there; it can be deleted freely now that history holds it.

## Trial cost: none

No `RESEARCH_LOG.md` row owed; equity `N` stays **129**. Nothing here searched a hypothesis space,
fitted anything or selected among arms. No threshold was pre-committed because there is no verdict
— this is repo hygiene, not a measurement.

---

# LA2 — the track backup was backing up the wrong book (r1 lane, 2026-08-10)

## STATUS: fixed, tested, verified end-to-end. 34/34 suites green.

Cold-audit item LA2 (`VALQUO_LIVE_AUDIT.md`). **The finding reproduces exactly, and it is worse
than "a file was missing": the weekly job was green the entire time.**

## What was wrong — measured before anything was changed

The committed `data_export/paper_track_history.json` read:

    "ingested_index_days": 0,   "ingested_index_track": null
    "index_days": 4,            "index_holdings": 10,   "paper_orders": 3

So the backup faithfully preserved **4 days of the Tradier sandbox engine** (10 names,
equal-weighted at 10%, inception 2026-08-03) and **zero rows of the contract-bound Valquo Index**
(86 names, score-weighted, 8% cap, inception 2026-07-30) — the one record
`PAPER_TRACK_CONTRACT.md` binds, and the one thing in this project that cannot be re-derived.

**Cause.** `payload()` did reach for the bound series, but only through
`store.get_meta("index_track")` — and nothing has ever ingested that key on the live service. The
only copy was `data/valquo_track_history.csv` on one laptop, 127 bytes, with (per CLAUDE.md) **no
writer for it anywhere in this repository**.

**Why nobody saw it.** The anti-regression guard counted `data_export/paper_track_index.csv` — the
*sandbox* book. The bound series was never counted at all, so it could go from two rows to zero
without tripping anything. **A relative guard cannot catch a quantity that was always zero**;
zero is never fewer than zero. That is the transferable lesson here.

## The fix, four parts

1. **Gather from everywhere it can live.** `bound_series()` reads the committed backup, the local
   `data/` tracker files, and the live store's meta; `merge_bound_rows()` unions them **by date —
   a later source wins a shared date and no date is ever dropped.** That asymmetry is the safety
   property: a legitimately empty source (fresh Render disk, a store that never ingested) can
   never erase a populated one. This matters immediately, because the deployed service is still
   running pre-LA2 code and its payload has no bound key at all.
2. **Give it its own file.** `valquo_index_track.csv` + `valquo_index_meta.json`, using the
   tracker's **own column names**, so restoring is `cp` and not a transformation written at 2am
   against a lost original.
3. **Guard the right thing.** `guard_counts()` reports `bound_index_days`; the workflow fails on a
   regression in *either* book, **plus an absolute presence check** — because the failure above
   was invisible to a relative one.
4. **Fix the label.** The emitted README no longer calls `paper_track_index.csv` "daily Valquo
   Index vs SPY". That exact mislabel put a false *"Index beating SPY"* claim into Discord on
   2026-08-05, on a day the bound recorder had the track **2.85pp behind**. The README now leads
   with the two-books distinction and states both weight caps (8% vs 10%), which is what tells
   them apart.

## The bound series is now in git

Committed to the already-tracked `data_export/`: 2026-07-31 (−0.2777pp) and 2026-08-06
(−2.8468pp), 86 names, inception 2026-07-30. Its existence no longer depends on one laptop.

**`data/` is untouched and still gitignored.** That rule exists because `data/` holds the licensed
Sharadar exports, which may not be redistributed; the bound series is a different object —
Valquo's own derived, unlicensed output — so a copy lives with the rest of the backup and the hard
rule is not bent.

**It is a BACKUP, not a second recorder.** `index_track.load()` still reads `data/` and only
`data/`, so `index_track.vs_spy_claim()` remains the single authority for a vs-SPY statement.
Nothing reads the committed copy back into the live path. This project has already been bitten
twice by two recorders of one number disagreeing (audit B7 on the site; the Discord recap); a
backup that quietly became an input would be that bug a third time.

## Verification — what I actually ran

`gh` is not installed on this machine, so **I did not dispatch the Action**; I ran its steps
locally against the payload the **current, pre-LA2 live service actually returns** (confirmed to
carry no `bound_index_track` key), which is the realistic next-run scenario:

    render exit 0
    guard: committed={'bound_index_days': 2, 'sandbox_index_days': 4}
                new={'bound_index_days': 2, 'sandbox_index_days': 4}
    artifact valquo_index_track.csv -> both bound rows present

**Negative control:** with no committed copy to merge, the same command warns loudly and the
presence check returns 0, i.e. the workflow fails — which is exactly the state that had been
silently green for months.

The scheduled run itself is unverified until it fires (Sunday 06:17 UTC, or dispatch by hand).

## Tests

**`tests/test_track_export.py` — new, 18 tests. The module had NO test suite at all**, which is
part of how this survived. They are written against the failure, not the feature: an empty payload
cannot erase the committed series; a payload from the *older* service cannot either; the guard
catches a bound-row regression (with a passing control, so it cannot pass by always failing); a
corrupt committed backup **raises rather than reading as zero rows**; and a real restore through
`index_track.load()` reproduces the published **−2.8468pp** from the backed-up copy.

**A bug in my own fix, caught by its own test.** Recording the write-time merge count inside the
artifact made two runs of identical input differ — breaking the byte-idempotence this module has
promised in prose since it was written and never tested. The count moved to the run log.

**One existing test was rewritten, not silenced.**
`test_private.py::test_the_backup_workflow_guards_against_clobbering_a_good_backup` asserted the
old step's *name* and the presence of bash `-lt`. Both were legitimately replaced when the
comparison moved into `track_export --guard-against` (which counts through the `csv` module, so an
embedded newline in a quoted field cannot inflate the count `grep -c` trusted). The intent is
unchanged and the test is now **stricter**: it requires the bound series to be covered, and it
**executes** the guard instead of grepping for an operator.

## What I did NOT do

* **Nothing ingests the bound series into the live service's store.** On a fresh Render disk the
  API still serves an empty live column until the files are restored by hand. LA2 does not cover
  that writer, and **there is still no automated daily writer for the bound series anywhere** —
  which remains the operational gate's actual blocker, not this.
* **No change to `index_track.py`, the contract, or any public surface.** Deliberate: this is a
  backup fix. Nothing about what the site says or what the contract binds moved.
* **`data/` unchanged**, including the gitignore rule.

## Trial cost: none

No `RESEARCH_LOG.md` row owed; equity `N` stays **131**. Nothing here searched a hypothesis space,
fitted anything or selected among arms — it is infrastructure, not a measurement.


---

# LA11 — the retracted 8%-cap diagnosis, still standing in eight places (2026-08-11)

**Cold audit #2 is now fully executed.** LA11 was the last open item; all fifteen (LA1–LA15) are
resolved, with LA6 tracked as `V2F`/`V2G` rather than as its own row.

## What the defect was

Session 16 (`PT-SPLIT`) retracted a diagnosis: the Tradier sandbox engine's 10% weights were
reported as breaching `PAPER_TRACK_CONTRACT.md`'s own 8% cap. **They do not.**
`valquo_index.build_index` sets `cap = max(MAX_WEIGHT, 1/len(picks))` deliberately — ten names at
8% sum to 80%, so on a small book the cap must relax to equal weight or the redistribution loop
never terminates — and the payload has always self-reported `effective_max_weight`. The weights
were right for the book; the **book** was wrong, on **size** (10 names against the published 86).

The **conclusion** (the engine is not the Index and may never be evidence under the contract)
survives untouched. Only its **reason** moved. But the retracted reason was left standing in prose,
and that is a worse state than no reason at all: a reader who checks the cap finds it correct and
may then doubt the separation itself.

## The audit named three sites. There were eight.

| site | named by the audit? |
|---|---|
| `valuation/edge/track_meter.py` | yes |
| `valuation/screener/index_track.py` | yes — as `:286`, actually `:368` |
| `valuation/saas/recap.py` | yes |
| `valuation/web/hero.py` | **no** |
| `valuation/edge/track_export.py` (module docstring) | **no** |
| `valuation/edge/track_export.py` (`_README`, emitted) | **no** |
| `.github/workflows/track-backup.yml` | **no** |
| `PAPER_TRACK_CONTRACT.md` §0a.2 | **no** |

The five extra sites were found by grepping **the claim** rather than following the audit's
citations. The `index_track.py` cite had drifted 82 lines in a day, which is CLAUDE.md's own
warning about line cites in this project rotting within days, confirmed once more.

## Two things worse than a stale docstring

**1. It shipped as committed DATA, and that is mine.** `track_export._README` is *emitted*, so the
retracted claim was written into `data_export/README.md` and committed — by my own LA2 work one day
earlier, which carried the stale reason forward. Regenerated from the corrected source.

**2. The contract asserted it in one section and corrected it in another.**
`PAPER_TRACK_CONTRACT.md` §5b has carried the full correction since 2026-08-10 while §0a.2 still
stated the retracted clause — exactly the shape the audit's preamble names. Struck in place with a
dated pointer to §5b; the original text is left visible because that document does not delete.
**No threshold, date or parameter moved**, so no void clause is engaged.

## A test was pinning the retracted diagnosis into the artifact

`tests/test_track_export.py` asserted `"8%" in readme and "10%" in readme` with the message *"the
README does not state the weight caps that tell the two books apart"*. The weight caps are exactly
what does **not** tell them apart — so that assertion **would have failed had the README been fixed
and the test left alone**, and a future reader would have concluded the README was wrong. It now
pins **book size** (86 vs 10 names), the ground the conclusion actually rests on. This was my own
test from LA2.

A comment in `tests/test_paper_track.py` also carried the retracted claim while
`test_ptsplit_a_ten_percent_weight_is_not_a_cap_violation`, in the same module, pinned the correct
reading. The comment and the test disagreed; the test was right.

## Verification

A regex sweep over every `.py`, `.yml` and `.md` in the tree returns **22 surviving matches**, and
each is one of: a dated correction quoting what it used to say, `VALQUO_LIVE_AUDIT.md`'s own record
of the defect, or a historical session handoff that already self-corrects (`HANDOFF_edge_audit.md`
§6414 lists it as "MY OWN, TWICE-PUBLISHED"). No site asserts it live.

**Full gate: 52 suites, all green.**

## Trial cost: none

A documentation correction — nothing searched, fitted or selected. Equity `N` unchanged at **151**
as measured today by `research_log.detail()`.

## Not done

* **The correction is prose only.** Nothing about what the code computes, what the site says, or
  what the contract binds has moved. That is deliberate and is the whole scope of LA11.
* **The still-open blocker is unchanged and is not this:** nothing ingests the bound series into
  the live service's store, and there is still **no automated daily writer** for it anywhere. That
  remains the operational gate's actual blocker (`PT-WRITER`, Cowork lane).

---

# D4 — Cboe Open-Close Volume Summary: DON'T BUY (2026-08-11)

**The full memo is `HANDOFF_data_spend_d4.md`**, written in the `HANDOFF_data_spend.md` house
style. This section is the lane pointer, not a second copy. **Research only — no code changed,
zero trials, equity `N` unmoved.** Ledger row `D4` OPEN → DONE/REJECTED. **The D series is now
complete**; D4 was the one item the 2026-08-06 buy-nothing pass explicitly left out
(*"not in this task's list, still unpriced, still gated on O14"*).

## What the memo establishes

| | |
|---|---|
| Cost, EOD subscription | **$500/mo**, filed with the SEC |
| Cost, EOD ad-hoc history | **$400 per request per month**; **one request = one month of data** (verbatim) |
| Cost for this project's own window | **$28,200–$37,600, ONE exchange**; fees are filed per exchange across C1/C2/BZX/EDGX |
| Audit's indicative figure | *"roughly $600/yr"* — understates the **recurring** line ~**10×** ($6,000/yr per exchange) and has **no counterpart** for the one-time history cost. Not compressed into one multiple: a one-time cost over an annual rate means nothing. The audit did label it indicative |
| Free trial | **Six months of ad-hoc historical EOD, $0**, non-TPHs eligible, **one-shot** |
| Licence to ship anything derived | **$5,000/mo = $60,000/yr**, plus approval |
| History start | **January 2018** — leaves **24 of 118 months (20.3%) unbuyable, the early ones** |
| Open items it feeds | **Exactly one that is not its own gate: `U2`** |

## The three things worth carrying out of it

1. **A public free trial replaced the audit's recommended action.** The audit says "one sales
   call". Cboe now gives six months of exactly this dataset to non-TPHs who have never subscribed.
   **The decision no longer costs money — but the trial is one-shot, so spending it before `O14`
   has produced a hypothesis wastes the one free look.**
2. **The licence is the same trap as D1, a third time.** Internal use only; external distribution
   of derived data is a separate $60k/yr product. Research-only, exactly like JKP. Any plan that
   ends with a flow-derived number on valquo.co has an unbudgeted $60k/yr in it.
3. **D4 cannot be tested by this project's own standard.** Ad-hoc history begins 2018-01, the alert
   book begins 2016-01, and the early/late split is the instrument nearly every options verdict
   rests on. **A fifth of the window, on the early side, is unavailable at any price.** Nobody had
   checked the dataset's start date against the book's window.

## Method note

The price was not on the vendor page and I did not accept that as unpriced. The product page's own
sentence — *"Fee Schedules have been filed with the SEC (see 'LiveVol Fees')"* — is the route, and
the filed schedules are public, quotable and current. **Two independent retrievals agreed on the
EOD figures before I used them**, and the "one request = one month" unit was confirmed verbatim
rather than inferred, because the whole cost estimate scales on it. `federalregister.gov`,
`sec.gov` and `justia.com` all refuse automated fetches (302 to an unblock page, or 403);
**`govinfo.gov` serves the same filings as plain HTML** and is the source that worked.

## Not done, and why

* **`O14` was not run.** It is the gate, it is free, and it is ~7 hours of compute — but it is a
  measurement with a pre-registration requirement (Benjamini–Hochberg across however many features
  are built), and this task was scoped to the purchase decision. It is the recommended next step.
* **`U2` was not run** — same reason, and it is the only open item D4 would feed.
* **No email or trial signup was initiated.** Both are outbound actions and Don's call.
* **The two per-exchange ambiguities were left ambiguous** rather than resolved by assumption: the
  $500-vs-$600/$300 structure, and whether C1 sells history back to 2005 as the audit claims. **If
  C1 does, the 24-month hole closes and the cost roughly triples.** Listed in UNRESOLVED, not
  estimated.
