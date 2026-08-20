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

# Branch triage — the last stranded ref deleted, and Part 2 had written up a deletion it never did (2026-08-12)

Full record in `HANDOFF_branch_triage.md` **Part 3 (§J–§O)**; this is the pointer.

`worktree-p6-costs-and-robustness` (`428f4de`) was still live on `origin` **and** locally, five
days after that file's §F was written about it in the past tense and §E listed it under **"Three
refs deleted"**. Two of the three had gone; this one had not.

**The cause is legible in the file, and it is the transferable lesson: §4's `THEN DELETE` block
lists the commands, and it lists TWO.** `p6-costs` appears there only as the *precedent* for how to
prune, then acquired a verification section (§F) and a row in the deleted table — **but never a
command.** The ref with prose written about it and no runbook line is exactly the one that
survived. §E now carries a correction marker so it cannot be misread as completion again.

**Re-verified by content, because §F's line cites had already rotted** — `score_universe_now()` was
cited at `fundamental_panel.py:1355`, now `:1453`; the sector guard at `valquo_index.py:41-51`, now
`:67/:178/:200/:217`. Only `attribution.py:46` still resolved. All seven content items confirmed on
`main`; the `score_universe_now` body diff shows **main is a strict superset** (33 insertions, all
of them main's own market-cap-divergence guard).

**Two things reported that cut against the tidy version.** (a) **§F's evidence table was
incomplete** — it omitted *both* `test_screener` flake fixes. The commit message enumerates four
repairs under two headings, and §F's table covered the first and skipped the second entirely. They
are on `main`, so the conclusion held, but on evidence that did not cover the whole commit. (b) **The branch's only unique content is prose, and merging it would have
regressed the record** — its `method` string (a payload the Cowork agent parses) carries five
void pre-B6 figures where `main` carries the current ones: 2,710/110 vs **2,531/69**, +11.8%/yr vs
**+7.2%**, breakeven 236bps vs ~37bps against **134bps vs 33bps measured**. The original suspicion
— a stale `BACKTEST_RESULTS.json` — stays false; **the commit does not touch that file at all.**

**Scan clean for the first time:** of 57 refs, 56 were merged and exactly 1 was ahead; after
deletion, 58 refs / 0 ahead (the total moved because other lanes landed mid-run — both counts
quoted rather than one). Identity banked for recovery: tip `428f4de0…`, tree `85dbae31…`, parent
`b0f70b6c…` (on `main`, so exactly one commit). **Nothing rescued — there was nothing unique worth
keeping.** No code changed; zero trials; equity `N` unmoved.

**Not done, and why:** the 56 merged refs were left alone. They are the auto-land Action's normal
residue, not stranded work, and a sweep of 56 remote deletions is a far larger action than the one
asked for. §I's four open items were not touched.

---

# The blocked-R recheck — one lane rule held four items shut for a week, and R8's premise was false all along (2026-08-13)

`R4`, `R5`, `R6`, `R8` had sat `BLOCKED` in `VALQUO_LEDGER.md` for weeks. Read-only routing pass,
no measurement: establish what each blocker actually was, whether it still holds, and route.
All four rows updated. Merged `origin/main` first (85 commits); gate **71 suites, 0 failed**.

## The blocker was the same for all four, it was never technical, and it had already expired

The four rows all read *"sits in `valuation/edge/**` which pipeline builder holds (AGENTS.md)."*
That is **lane ownership, not evidence** — `AGENTS.md:15` says *"Only one terminal may ever hold
this lane"* and `:20` says r1's items are *"blocked until pipeline builder frees that lane."*

**That workflow no longer exists.** Measured: **59 non-merge commits have touched
`valuation/edge/**` since 2026-08-06**, from at least five different worktree branches
(`options-live`, `optionsbot-lane`, `close-the-leak`, `crowding-p2`, `p24-shortinterest`), landing
through the gated auto-land Action (`RUN_RULES.md:76`). The single-holder model was replaced by
worktree branches. `AGENTS.md` is dated 2026-08-05/06, its own second table is marked stale, and
the closeout it waits on — Session 5, `0fb22a8` — landed **2026-08-05**, with twenty-odd sessions
since.

**The ledger recorded the override and the reasoning that made it stick.** Its own
proposal-vs-verdict table had a row reading *"Script proposes OPEN, item is BLOCKED … Defensible
either way; kept as BLOCKED because that is what a reader needs to know."* The script was right and
the human override was wrong. **A hand-verified override is only as fresh as the document it was
verified against**, and *"defensible either way"* is the phrasing to distrust — it recorded a
judgement call with no re-check date and held four items shut after its premise expired. That row
is corrected in place rather than deleted, because it is the mechanism.

## R8 — OBSOLETE, premise refuted. The panel's returns are already total return

R8 asserts every forward return is `close_end/close_start − 1` on a series that *"handles splits
but excludes dividend income."* **It does not exclude them.** The panel's `close` **is** Sharadar
`closeadj`, which is split- **and dividend**-adjusted.

Four independent lines, because one would not have been enough:

1. `SharadarProvider.price_history` requests `date,closeadj` (`data_providers.py:149`).
2. `sharadar_freeze._split_prices` writes `prices/<T>.csv` as `date,close` **taking the `closeadj`
   column**, and says so in its docstring — *"close is `closeadj` (split- AND dividend-adjusted),
   which is what the live export wrote and what the panel expects"* (`sharadar_freeze.py:326,339`).
   `WRDSProvider.price_history` reads exactly that file (`data_providers.py:335-357`).
3. **Measured on the very file the panel reads.** SPY compounds **15.27%/yr 2009-01-15 →
   2026-01-15** — the total-return level, matching the record's own *"SPY total return +15.32%"*
   from `benchmarks.spy`; price-only would be ~2pp lower. And per-name adjustment factors track
   each name's **own yield**: 2009-01 file price against actual split-adjusted price gives
   **MSFT 1.41×, JNJ 1.67×, KO 1.76×, XOM 1.90×** — monotone in dividend yield, which is the
   signature of dividend adjustment and of nothing else.
4. **Audit B1, from a different lane with no stake in R8, found and fixed a bug *caused by* this
   series being dividend-adjusted** — *"corrupts every dividend payer on every date by a factor
   that grows with lookback"* (`options_backtest.py:208`).

**The audit told the reader to check first** — *"`closeadj` is dividend-adjusted retroactively …
resolve which series is actually feeding forward returns before assuming a direction"* — and nobody
did. The item sat `BLOCKED` for eight days on a premise ten minutes of reading refutes.

Two things that follow, stated so they are not re-litigated. **No look-ahead from the retroactive
adjustment** (argument, not measurement): in a ratio of two adjusted prices, every factor for a
dividend *after* the window cancels, and dividends *inside* it are correctly included. **The tilt
concern cannot arise at all** — the benchmark leg is computed from the same `fwd_ret` column, so
both legs sit on one total-return basis, and R8's central worry (the top decile losing more to the
omission than the benchmark) has no mechanism.

### The defect this turned up — reported, not fixed, and it runs the flattering way

`fundamental_panel.py:3597-3598` states the **opposite** in a shipped docstring — *"NO dividends
anywhere. The panel's forward returns are price-only"* — and uses it to justify omitting dividend
**tax** from the after-tax block, calling the pair *"Consistent."* They are not consistent.
**Dividend income IS in the gross return, so the after-tax figures omit tax on income they do
include, and net-of-tax is OVERSTATED.** Not repaired here: it is a numbers change on the edge
lane's after-tax block, it needs its own item, and it is not R8.

## R4 — OPEN. Two of three bullets were already delivered

- **Delivered:** the real `N` feeds the Deflated Sharpe (M1, `2f3529b`, hardened by session 12's
  parser fix), and the **Harvey–Liu–Zhu hurdle at the real `N`** is `_trials_haircut`,
  `sqrt(2·ln max(2, n_trials, _trial_N()))` (`fundamental_panel.py:2402`), quoted every session.
- **Remaining scope is one bullet:** Benjamini–Hochberg across the family of **equity** signal
  tests. BH exists in this tree but only in the options and tickflow lanes (`options_autopsy.py`,
  `tickflow_signals.py:288`) — there is no equity-side FDR pass.
- **Next session:** one small edge-lane session running BH over the existing per-signal IC table,
  shipped in the results file. **Zero trial cost** — it searches nothing, the argument that made
  session 10's HAC-floor calibration free.

## R5 / R6 — OPEN, cheap, and they are one commit

Both were blocked on **B12** (the alphabetical universe) as well as the lane. **B12 is DONE**
(`3def852`).

- **R5 is three signals, not four.** The low-volatility anomaly is already registered and measured
  (`neg_vol` → `low_risk`, `settings.py:212`; theme IC +0.46 on the corrected panel). `neg_ret_1m`,
  `neg_max_ret`, `neg_idio_vol` remain absent from `NUMBER_THEME` — no `z_` column, no coverage
  entry, no IC, exactly as the audit found.
- **R6's three** (`sm_conviction`, `sm_holders`, `sm_avg_position`) are likewise absent; they are
  computed into the frame (`factors.py:199-202`) but unmeasured.
- **The pattern to copy is in the same file:** S2 `cash_op_prof` (`settings.py:227-242`) registers a
  number so it is **MEASURED without SCORING** — `factors.py` must name it in a theme mean for that
  — and the composite was verified bit-identical with it registered.
- **The trial-cost objection no longer bites.** Equity `N` is **202** today, so R5's three trials
  move the haircut `sqrt(2·ln N)` from **3.2583 to 3.2628** (under 0.005 of a *t*), and R5+R6
  together to **3.2673**. At this `N` a cheap registration is close to free.
- **R6's expected value is low and the record says why** — a routing fact, not a verdict. Both
  family members measured on the full universe came back weak: `sm_breadth` fell **2.37 → +1.73**,
  and the close cousin `sm_elite_conviction` was **rejected at t +1.32** (2026-08-01). That lowers
  the prior; it does not substitute for the measurement, and a marginal rejection resting on a
  voided universe is exactly what B12 exists to force a re-run of.
- **Take them in one commit** — the dependency map already says so (`:343`): both edit the same
  `NUMBER_THEME` dict, and two branches on one dict conflict textually.

**Stale claim found, not fixed:** `settings.py:224` still records R5's three as *"all wrong-signed
here"*, and `settings.py:243-251` still quotes R6's rejections as the 800-name figures. Both are
**alphabetical-era findings B12 voided**, sitting in live comments as though current. Whoever runs
R5/R6 should replace them with the full-universe numbers rather than adding to them.

## Also found in the ledger, reported not repaired

The counts table's `BLOCKED` column was **already stale before this change**. Its remaining `1` is
`O16`, which went **DONE on 2026-08-08** without the table being refreshed. Measured across all 192
rows today, exactly **two** carry BLOCKED in a status cell: `B13` (`PARTIAL - BLOCKED ON DATA`,
still counted under `IN PROGRESS` from before its 2026-08-12 correction) and `PT-WRITER` (Cowork
lane, outside the 134). **The true count of plain-BLOCKED audit items is now zero.** Only the `R`
cells were re-derived — these counts are `build_ledger.py`'s generated snapshot, and hand-patching
a generated block is how it drifts from the rows it summarises. Owner: whoever next runs
`python scripts/build_ledger.py --write`.

## Not done, and why

- **`AGENTS.md` was left alone** even though it carries the false blocker. It is another lane's
  coordination document, the task scoped this to the four ledger rows, and the ledger is the
  documented authority for *"where do we stand"* — so correcting the rows is sufficient. Flagged
  here so the next agent to touch `AGENTS.md` knows its ownership table has expired.
- **No measurement of any kind**, per the task. Routing searches no hypothesis space: **zero
  trials, equity `N` unchanged at 202**, no shipped number, weight or code path touched.
- The R5/R6 registrations themselves were **not** performed — that is the next session's work, and
  doing it here would have been a measurement.

---

# The MA dependency map, and three wave-1 items — the brief's in-flight list was wrong, and the drift has already cost 42 GB (2026-08-14)

Two deliverables in one session: the dependency/lane/wave map for cold audit #3, and the three
wave-1 items this lane owns (MA15, MA16, MA20).

## 0. THE HEADLINE, because it connects the two halves

**MA20's drift is not a tidiness problem. Measured today: the stale checkout's copy of
`backup_now.bat` put 42 GB of `.claude` and `.git` mirrors back onto D: in a single manual run,
less than 24 hours after that exact junk was cleaned off.** The version of that script on `main`
is a harmless three-line shim that delegates to the allowlist. The version Windows runs is the
2026-08-03 `/E` copy-everything design with no `.git`/`.claude` exclusion and no `/XJ`. They are
the same filename, 514 commits apart.

So the drift actively re-arms the failure that destroyed the previous drive, and it will keep
doing so on every double-click until the checkout syncs. That is the argument for MA20 being
HIGH, and it is stronger than the audit's own framing (which is about stale *reads* and one
stranded commit).

## 1. THE MAP — `MA_DEPENDENCY_MAP.md`, `ma_dependency_edges.json`, `ma_in_flight.json`

Built from `valquo_master_audit_ultimate_items.json` (the merged 60-row record: Pass A MA1-35 +
Pass B MA36-60), following the audit-#1 precedent — but **generated**, by
`scripts/ma_dependency_map.py`, so it cannot drift from the record. Audit #1's map closed by
warning that hand-maintained write-sets go stale and shipped no check; this one has `--check`,
it is wired into a test, and the test is what fails if the items file moves.

Per item: files touched, owning lane, needs-first edges, wave, trial cost, in-flight status.
**Four kinds of edge**, kept apart because their cures differ: `explicit` (the audit's own
`depends_on`), `logical` (derived here, each carrying its reason — disagree with the reason and
the edge goes), `hard-file` (same file, expect a text conflict), `soft-import` (import-coupled;
**the merge is clean and the build can still break** — the class audit #1 found between B1 and
B2, and the class git cannot see).

| lane | items | wave 1 |
|---|---|---|
| pipeline (edge/research/backtest) | 28 | 2 |
| options-bot | 10 | 2 |
| infra (CI/backup/docs/process) | 10 | 3 |
| app-fixer (web/saas) | 8 | 2 |
| greeks (screener/engine/intraday) | 4 | 2 |

**Wave 1 = 11 items and it is NOT eleven parallel branches.** Eight collisions sit inside wave 1,
five of them involving MA1, which reaches `app_saas.py`, `track_meter.py` and `auto-scan.yml`
simultaneously. MA1 wants a quiet tree and a single owner. A safe first fan-out is MA1 alone on
that territory with MA4, MA38, MA39 and MA50 beside it.

`valuation/edge/fundamental_panel.py` is named by 12 of 60 items — a smaller share than audit
#1's 46-of-134, the same conclusion: the panel cannot be split across owners.

## 2. FOUR CORRECTIONS THE MAP MAKES TO ITS OWN BRIEF

* **THE IN-FLIGHT LIST WAS WRONG, AND IT ROUTES WORK.** The brief named MA1-MA3 and MA5/MA6 as
  in flight. Measured across every local and remote branch, `main`, and all eleven registered
  worktrees: **none of the five has a commit anywhere.** What IS in flight is **MA13+MA19**
  (`worktree-options-live`, PREREG committed 20:22) and **MA36+MA37**
  (`worktree-optionsbot-lane`, PREREG committed 20:28) — both within twenty minutes of the map
  being built. Dispatching MA19 off the brief's list would have put two lanes on the same
  recalibration of X7's floors, and there is no rule that says which answer would win.
* **THE THREE-WAVE RULE LEAVES A CRITICAL ITEM IN NO WAVE.** Read literally — wave 1 is
  CRITICAL+HIGH with no unmet deps, wave 2 is *MEDIUMs* — then MA2 (CRITICAL, needs MA1), MA3,
  MA10 and MA19 belong to nothing. They sit at the **head of wave 2, severity-first**, and the
  corrected rule is written into the JSON so the next reader inherits the fix, not the gap.
* **THE ITEMS FILE DISAGREES WITH ITSELF ABOUT MA18.** `_meta.corrections_to_pass_A` re-rates it
  MEDIUM→HIGH; the item body still says MEDIUM. The map applies the later statement and records
  both as `severity` and `severity_as_written`. Nothing is silently overwritten.
* **`modifies` CANNOT FIND THE COLLISIONS HERE.** All 25 Pass B items ship an empty `modifies`.
  The audit-#1 machinery keys on it, so it would have reported **zero collisions for 25 of 60
  items** — a map that looks clean because it is blind. Collisions are computed from `files`, and
  a test fails if no Pass B item ever collides.

**A dependency worth naming: MA19 `depends_on` MA16.** The lane that committed a PREREG for MA19
tonight was, on the audit's own edge, blocked on a backup item. MA16 was delivered an hour later
in this session, so the edge is satisfied — but by coincidence of timing, not by design.

## 3. MA15 + MA16 — the two allowlist gaps, closed and verified on the drive

Both were real and both are now `$KEEP`, in one commit (they are the same file; splitting them
across branches guarantees a `$KEEP` conflict).

* **MA15 `data\options_ticks` → bucket 2.** Named nowhere in the script, and an allowlist is
  silent about anything unnamed — silence is indistinguishable from a decision to drop it.
  4.40 GB, 3,894 files, 70.3M prints over 3,884 of 3,885 alert-days. Justified on D2's verified
  finding (ledger `D2`, `HANDOFF_data_spend.md:43`): the individual ThetaData tier is
  *"personal use only, no business use"*, lawful commercial access starts ~$250/mo plus OPRA firm
  registration, and the account serialises so a re-mine cannot be parallelised out of its runtime.
  It is the sole input to O10, O18 and O14.
* **MA16 `data\free_analysis` → bucket 1.** The `$SKIP` reason was wrong twice over. It says
  **0.07 GB**; measured it is **0.80 GB — eleven times larger** (the audit's own "70 MB" is wrong
  the same way). And it says "results JSONs recomputed by the scripts that wrote them", while
  **more than half of it is banked PANELS** — `panel.pkl` (the pre-B6 panel S19's C6 compares
  against), `panel_corrected_69d.pkl`, `panel_s20_s21.pkl`, `panel_r5r6.pkl`, `S17_PRICES.pkl`,
  `m4_metrics_sink.pkl`. **A panel is a snapshot of a code state, so "the script can rebuild it"
  stops being true the moment the script changes** — which is the whole of RUN_RULES rule 9.

**Verified on the drive, not asserted:** 45.84 → **51.04 GB**, and the arithmetic closes exactly
(45.84 + 4.40 + 0.80 = 51.04). `data\options_ticks` reads 3,894 files / 4.397 GB on D: and
`data\free_analysis` 0.797 GB. All 17 KEEP entries present, 406 GB free.

**Answering MA15's `evidence_needed` ("ask Don whether it is on D: by some other route"): it was
— by the wrong route.** The ticks were on D: only because the copy-everything script put them
there, so yesterday's prune removed them and today's rogue run restored them. The only thing that
had ever protected the crown-jewel tick cache was the design that fills the drive.

## 4. MA20 — the alarm, delivered; the cure is Don's

`scripts/checkout_drift.py` + `check_drift.bat`, wired into `git_push.bat`. Read-only, changes
nothing, and **`sync.bat` remains the cure** — a guard that silently repairs is a guard whose
failures are invisible, which is the whole item.

Measured on the real checkout: **1 ahead, 514 behind** (the audit measured 508 yesterday), and
the one local commit is the dated PT-WRITER failure note stranded since **2026-08-10 20:06**.

* **THE AUDIT'S PROPOSED FIX CANNOT WORK AS STATED.** It suggests the existing `auto-scan.yml`
  watchdog report the divergence to Discord. That job runs on GitHub's runners and **cannot see a
  directory on Don's PC**. The alarm has to be local, which is why this is a script and a `.bat`.
* **THE CAUSE THE AUDIT DID NOT HAVE, AND IT IS THE USEFUL PART.** `ValuationToolAutoPush` runs
  `git_push.bat` **daily at 20:00**, ran today, and Windows recorded `LastTaskResult=0`. It has
  been "succeeding" for days while the commit sat unpushed, because **the script calls `git fetch`
  nowhere at all.** It merges local `worktree-*` branches, runs the tests and pushes; once local
  `main` has diverged the push is rejected as a non-fast-forward, and the script prints
  *"Run connect_github.bat once so Windows saves your GitHub login"* — **blaming credentials for a
  divergence** — then exits 0. Four consecutive green task results, no push.
* Consequences built in: the guard **does its own fetch** (an alarm reading a stale remote ref
  would reproduce exactly the defect it exists to catch); **unknown is an alarm, not a pass** (no
  git, not a repo, missing upstream ref, failed fetch — "I could not tell" and "all clear" must
  never share an exit code); and being **ahead** is its own alarm at any threshold, because that
  commit exists nowhere else. `git_push.bat`'s misleading failure message now names divergence
  first and `connect_github.bat` second.
* **The threshold is derived, not chosen.** `origin/main` takes a median of **49 commits/day**
  (measured over the twelve days to 2026-08-14), so the default `--max-behind 50` is about one
  day of drift — the point at which a `.bat` on disk stops being the `.bat` on main. It is a round
  number from a measured rate; it is **not** a calibrated threshold and carries no verdict.
* **THE RECURSION, STATED PLAINLY: this guard cannot deploy itself.** It lives in the tree that is
  514 commits behind. Nothing here starts protecting anything until Don syncs once — which is
  MA20's own point, and the reason the item is HIGH rather than housekeeping.

## 5. GATES

`tests/test_checkout_drift.py` **18/18** (real git repos, no mocks — a mocked git would pin my
belief about git rather than git). `tests/test_ma_dependency_map.py` **23/23**.
**Full python gate: 76 suites, 0 failed** (by exit code, per the project rule — not by grepping
for `OK`).

**A SECOND DEFECT IN MY OWN INSTRUMENT, AND IT FAILED IN THE DANGEROUS DIRECTION.** The path
normaliser stripped line numbers and parentheticals but not a trailing *field* reference, so
`BACKTEST_RESULTS.json cpcv.adopt_detail`, `BACKTEST_RESULTS.json multiple_testing.hlz` and
`BACKTEST_RESULTS.json` normalised to **three different strings** — and the map reported **no
collision at all** between MA5, MA19 and MA21, which all edit that file. A collision map that
misses collisions is worse than none, because its silence reads as clearance. Fixed, **4
collisions recovered (281 → 285)**, and pinned by a test that also checks a prose entry
(`owned daily closes`) is *not* mangled into a filename.

**A DEFECT IN MY OWN INSTRUMENT, FOUND BY REPETITION AND FIXED BY DESIGN RATHER THAN BY RETRY.**
The drift suite passed, so I ran it repeatedly instead of once — and it failed **1 run in 4** under
load, always as a **setup ERROR, never a failed assertion**, and always two tests at a time. Cause:
building a fresh pair of git repositories inside every test issued **~200 git subprocesses per
run**, and on Windows that surface fails intermittently. **The first fix — `ignore_cleanup_errors`
plus `gc.auto=0`, aimed at temp-dir teardown — did not work**, and is reported because it was the
obvious diagnosis and it was wrong. What worked is structural: **six fixtures built once per run,
every test read-only against them**, which removes the failure class instead of retrying through
it, and a test pins that design so the subprocess count cannot climb back. **A single green run is
not evidence a test is deterministic** — this one was green three times before it failed.
`tests/test_backup_to_D.ps1` **62/62** (was 55; +7 pinning MA15/MA16 from both ends — the copy
must happen *and* the path must not reappear in `$SKIP`, because a re-skip would leave every
path assertion still passing).

## 6. REPORTED, NOT FIXED

* **The `-Prune` blind spot reproduced independently.** Yesterday I reported that the ownership
  map is built at `data\<first-level>` granularity, so `data\bulk\prepared` being in `$KEEP` marks
  all of `data\bulk` owned and the pruner cannot see strays inside a partially-owned directory.
  Today's rogue run restored the same four loose Sharadar CSVs (**5.11 GB**: actions 44.4,
  daily 2373.1, events 50.3, sf3 2763.8 MB) and **the prune left every one of them**. D: reads
  56.14 GB against the script's own 51.04 — the difference is exactly the blind spot. Diagnosed
  twice now, still unfixed here, because a second behavioural change to the deletion path in as
  many days deserves its own register and its own tests, and the brief asked for the allowlist.
* **The catalogue has already outgrown the file this map was built from.** `worktree-optionsbot-lane`
  has committed a PREREG for **MA36+MA37** and the ledger now carries **60 MA rows**. Regenerate
  the map when that lane lands.
* **A note for whoever lands next:** `test_ma_dependency_map.py` fails if the items file changes
  and the map is not regenerated. That is deliberate, and it means an edit to
  `valquo_master_audit_ultimate_items.json` in *any* lane must be followed by
  `python scripts/ma_dependency_map.py`. The failure message says so.

## 7. NOT DONE, AND WHY

* **The checkout was not synced by me.** It is the shared working copy, ten other worktrees hang
  off its object store, and it carries an unpushed commit. `HANDOFF_backup.md` §9f still holds and
  is now more urgent: until Don runs `sync.bat`, `backup_now.bat` in that tree stays a live 42-GB
  weapon and none of tonight's guards are on the machine.
* **MA35 was verified, not re-done** — `.gitattributes` carries `*.pdf binary` on main (`c759250`).
* **`VALQUO_LEDGER.md` was deliberately NOT touched.** `worktree-optionsbot-lane` is mid-flight
  ingesting the 60 MA rows into it, and those rows are not on `main` yet — so there is nothing to
  mark `DONE` against, and editing the same table from two branches is how a ledger loses a row.
  **MA15, MA16 and MA20 need their ledger rows closed once that lane lands**, and
  `ma_in_flight.json` records the state each is in so whoever does it does not have to re-derive it.
* **`valquo_master_audit_ultimate_items.json` is committed here byte-identical to that lane's
  copy** (`git hash-object` matches `41a19b0`'s blob), so if both land, git resolves the add/add
  without a conflict. It is committed rather than merely referenced because the map's freshness
  check needs its source in the same tree.
* Nothing in wave 2 or wave 3 was started, and no MA item outside MA15/MA16/MA20 was modified.

---

## MA20 - the cure (2026-08-15, r1/infra lane)

**The alarm landed yesterday and changed nothing. That is this section's whole subject.**
`checkout_drift.py` shipped on 2026-08-14 and was correct on every reading; with only a
report, the drift got *measured* daily instead of *fixed*, and it grew **514 -> 540 in one
day**. MA20 asked for detection. This is the cure.

### 1. Three findings, each measured rather than argued

**(a) The audit's own proposed fix cannot work.** MA20's note says the cheapest fix is *"have
the existing watchdog report the shared checkout's divergence to Discord."* `auto-scan.yml`
runs on GitHub's hosted runners. It has no view of a directory on Don's PC. Nothing that runs
in CI can ever see this.

**(b) The file everyone calls "the cure" could not cure it - and said it had.** Reading
`sync.bat`:

1. step 2 pushes `refs/heads/worktree-*` **only**, so a commit sitting on `main` is never
   sent anywhere. `41d7b12` was on `main`.
2. step 3's `git merge --ff-only origin/main` is *impossible* on a diverged branch, and its
   exit code was never checked, so the failure scrolled past in the noise.
3. with no agent branch pending it then printed
   **"none - everything is merged. You are fully up to date"** and
   **"Nothing. All agent work is on GitHub and merged into main."**

So the drift was not invisible for want of a cure. **The cure reported success.** That string
is now deleted and the all-clear is gated on a real measurement; the three-way branch was
verified in real `cmd` (`SYNCRC=1,ANY=0 -> not-in-step`, `0,0 -> all-clear`,
`0,1 -> work-pushed`).

**(c) A second silent success, in the daily task.** `ValuationToolAutoPush` shows
`LastTaskResult=0` for 2026-08-14 20:00 and nothing was pushed. Two independent reasons:
`git_push.bat` never fetched, so its push was rejected as a non-fast-forward and the handler
blamed the login; and its auto-land loop aborts on the **first** branch because the tree
carries **27 dirty entries**, printing `[!] A branch could not be merged cleanly` and exiting
**0**. A green Task Scheduler row has meant nothing here for five days.

### 2. What shipped

| file | what it is |
|---|---|
| `scripts/sync_checkout.py` | the cure. Four phases, each reported separately |
| `scripts/valquo_sync_bootstrap.bat` | the launcher that survives a stale checkout |
| `install_sync_task.bat` | double-click once; registers a per-user daily task |
| `sync.bat` | false all-clear removed; now delegates the sync |
| `git_push.bat` | syncs **before** it merges and pushes |
| `check_drift.bat` | points at both the manual and the permanent fix |
| `tests/test_sync_checkout.py` | 29 tests |

Phases: **A** rescue unpushed commits to `rescue/<branch>-<sha>`; **B** bank uncommitted
*tracked* edits as a commit; **C** fast-forward; **D** report. A and B are additive and can
only ever create refs on the remote. C is the only phase that writes to the working tree.

**B builds its commit through a throwaway `GIT_INDEX_FILE` plus `write-tree`/`commit-tree`,
so HEAD, the index and every file on disk are untouched** - asserted, including the index's
mtime. It is deliberately **not** `git stash`: that stack is shared with every worktree of
this repository and other sessions pop it.

Blocking untracked files are **moved** into `_sync_quarantine/<timestamp>/`, never deleted,
and the collision list is parsed from git's own refusal rather than re-derived.

### 3. Rescue goes to `rescue/*`, not `worktree-*` - and that is a measurement

`worktree-*` is auto-landed by the gate Action, so rescuing onto it would merge stranded work
unreviewed. Measured on the commit actually sitting there: `41d7b12` diffs as **2,226
insertions / 2,212 deletions** of `HANDOFF_STATUS.md`, and
`--ignore-all-space --ignore-blank-lines` shows the real content is **14 added lines**. The
rest is the CRLF renormalisation `.gitattributes` explicitly says it avoids - and that file is
`merge=union`, so a merge would have kept both sides and roughly **doubled** it. `--land` opts
into the gated route for callers who want it.

### 4. The destructive step is not automated, and no scheduled path can reach it

Un-diverging means discarding one side's branch pointer. `--adopt-remote` does it and
**refuses unless it has just re-read the remote and confirmed every local commit is there**,
and every tracked modification is inside the snapshot commit. A test asserts that neither the
installer, the bootstrap, `sync.bat` nor `git_push.bat` passes that flag.

### 5. Verified against today's real drift

`540 behind, 1 ahead, 2 modified, 25 untracked`:

```
[OK ] rescue-commits:    pushed   rescue/main-41d7b12
[OK ] snapshot-worktree: pushed   rescue/wip-main-c4a3939
[!! ] fast-forward:      refused  reason: diverged
[ALARM] Not finished: fast-forward                       exit 1
```

Both refs confirmed present on `origin` with `git ls-remote`, and the PT-WRITER text read back
**from the remote**. **The commit that CLAUDE.md calls the answer to `PT-WRITER` has existed in
two places since today, after five days on one laptop.** Not one file in Don's checkout was
touched.

### 6. The automation is staleness-immune - the part that makes it a cure

A launcher inside the repo would be as stale as the repo: it could only start working after
someone had already done the thing it exists to do automatically. So `install_sync_task.bat`
copies the bootstrap **out** to `%LOCALAPPDATA%\Valquo`, and that bootstrap pulls
`scripts/sync_checkout.py` straight out of `origin/main` on every run.

**Proved end to end**, not asserted: a scratch clone reset to a root commit that **did not
contain `scripts/` at all** was fast-forwarded correctly by the bootstrap, logging
`using origin/main`. It size-checks the download, because a failed `git show` leaves a
zero-byte file that python runs happily and exits 0 - a silent all-clear, which is this item's
own disease.

Scheduled at **19:30**, half an hour before `ValuationToolAutoPush` at 20:00, so that task's
push becomes a fast-forward. Task creation needs **no administrator rights** (probed).

**`ValquoSyncCheckout` is INSTALLED and has run.** Registered against the shared checkout with
its bootstrap taken from `origin/main` (not from a worktree, which can be deleted). Its first
run logged `using origin/main` and exercised the whole path on the real tree. Log:
`%LOCALAPPDATA%\Valquo\sync.log`. To remove it: `schtasks /Delete /TN "ValquoSyncCheckout" /F`.
It will keep reporting **exit 1** until the diverged branch is finished off — correctly, and
that is the alarm doing its job, not a fault.

### 7. What is left, and why it cannot be automated away

**One bootstrap step is Don's**, and it is the thing being fixed: the checkout is 540 commits
behind, so it does not yet contain any of this.

```
cd C:\Users\donni\Downloads\valuation-tool
git fetch origin
python .claude\worktrees\r1\scripts\sync_checkout.py --adopt-remote
```

The second command finishes the diverged branch. It is safe **because it verifies**, not
because I say so: `rescue/main-41d7b12` is already on GitHub at exactly the local `main` sha,
and `rescue/wip-main-c4a3939` holds the uncommitted `HANDOFF_STATUS.md` and
`LAZY_PRICES_COVERAGE.md` edits. It will refuse if either check fails. Some untracked files
will be moved into `_sync_quarantine/<timestamp>/` - nothing is deleted.

Then, once and never again:

```
install_sync_task.bat
```

**I did not run either.** The shared checkout has ten other worktrees hanging off its object
store and other lanes may be live in it; `--adopt-remote` moves a branch pointer in a tree I
do not own, and the installer registers a recurring job on Don's machine. The additive half -
the part that could not lose anything - is already done.

### 8. Two defects in my own instrument

**`--dry-run` caught the serious one before anything ran.** `_out()` strips the whole blob,
which eats the **leading space of `git status --porcelain`'s first line**, so a fixed `[3:]`
slice read `" M HANDOFF_STATUS.md"` as **`ANDOFF_STATUS.md`**. A phantom filename here is a
file that quarantine silently misses. Pinned by a regression test.

**A test of mine passed vacuously.** The "refuses on a blocking tracked edit" fixture dirtied
`README.md` while the upstream commits only added new files, so git fast-forwarded straight
past the edit and the test asserted nothing. The fixture now makes the upstream touch the same
file. It was found only because a *different* fix made it start failing.

**And a third, caught by the land gate rather than by me** (first push red, `82 suites 0 failed`
locally). The "snapshot touches nothing" test compared `.git/index`'s `st_mtime_ns` — and read
it *after* calling `git status`, which refreshes the index's stat cache and rewrites the file.
**The act of measuring changed the thing being measured**, so the assertion was about whether
any git command had refreshed a cache, not about the snapshot. It failed on Linux and not on
Windows purely on timing (29 ms apart). The index is now compared by *content*
(`git diff --cached --name-status`), which is the actual claim — and since that compares two
*empty* outputs, exactly what a blind probe also produces, a positive control asserts it turns
non-empty when something really is staged.

**A fourth, found by installing the task and running it** — which is why the mandate's "verify
by running it" was worth taking literally. The snapshot's idempotency check compared the
**commit** on the remote ref against the commit just built, and `commit-tree` stamps a fresh
timestamp every run: an unchanged working tree still yields a **new** commit sha, a *sibling*
of the one already there rather than a descendant. So the push was rejected as a
non-fast-forward and the daily task would have alarmed **every day after the first**. It now
compares **trees**, fetched into a private `refs/valquo/` ref so no scratch ref of the user's is
disturbed, and pushes a fresh suffixed ref rather than failing if the tree cannot be
established. **The gap was in the tests, not just the code**: `rescuing twice is a no-op` was
tested and `snapshotting twice` was not. Both now are. Verified twice in a row against the real
checkout — `already-rescued` / `already-snapshotted`, exit unchanged.

Also reported: the daily task will create a new `rescue/wip-*` ref whenever the tracked
working-tree content changes (identical trees are idempotent). That is ref clutter over
months. Deliberately not auto-pruned - a tool built to stop work disappearing should not
delete refs on a schedule.

### 9. Ledger

`MA20` **DONE**. `MA15` and `MA16` closed in the same commit - they were finished on
2026-08-14 (`caeb542`) but their rows were left `OPEN` because the options-bot lane was
mid-flight ingesting all 60 MA rows at the time. `tests/test_build_ledger.py` 20/20,
257 rows = 134 audit + 123 out-of-band, 60 unique MA ids.

**Zero trials.** A process repair with no hypothesis and no threshold; equity `N` stays 224.


---

## MA11 + MA12 + MA17 + MA22 — wave 2, infra lane (2026-08-15, r1)

Four MEDIUM items, one session, all four `OPEN` at the start and `DONE` at the end. **Zero
trials** — every one is a process or correctness repair with no hypothesis and no threshold, so
equity `N` stays **224**. `main` merged first (fast-forward, 8 commits).

**Every claim was verified against the tree before it was acted on (`RUN_RULES` A8). All four
reproduce. Three of them measure worse than the audit states, and one names the wrong file.**

### 1. MA11 — the auto-land Action is unreviewed code execution with write access to main

**Verified.** `on: push branches ['worktree-*']`, `permissions: contents: write`, and the gate
runs `python "$f"` over `tests/test_*.py` **from the merged tree** — so the branch supplies the
code that judges the branch, exactly as the audit says.

**Worse than the audit states, and this is the part that made the fix obvious.**
`actions/checkout` defaults to `persist-credentials: true`, so that write token sat in
`.git/config` while branch code ran. A file named `tests/test_zz.py` could have run
`git push --force origin main` and skipped the gate altogether — the gate would then be
judging a branch that had already landed.

**THE FIX IS THE PERMISSIONS SPLIT, because it is the only control here GitHub enforces rather
than merely encourages.** `permissions:` is per-job, so:

* **`gate` — `contents: read`.** Every line of branch code executes here. A stolen token now
  buys read access to a repository the branch is already inside.
* **`land` — `contents: write`, `needs: gate`.** Merges and pushes; runs no branch code.

Everything else in this item is a convention the workflow chooses to honour. This one is a
capability the runner does not have.

**Plus `.github/land_policy.py`, and where it is read from is the whole trick.** The workflow
copies it out of **main's** checkout *before* merging the branch, so a branch cannot switch the
policy off by editing its own copy. It refuses two things: any change under `.github/`, and the
**deletion** of a test suite.

**It lives under `.github/` deliberately** — weakening it is itself a `.github/` change, so it
trips its own rule. That is pinned by test, because moving it to `scripts/` would silently
reopen the hole: the workflow reads main's copy, and main's copy would then no longer be
guarded.

**THE AUDIT'S OTHER SUGGESTION IS DECLINED, WITH THE REASON.** It floats "run the gate against
main's copy of `tests/` merged with the branch's source". That would red-X every legitimate
change that alters behaviour and updates the covering test in the same commit — main's old test
against the branch's new source — which is the ordinary case, not the exception. Refusing
**deletions** gets the property that actually matters (a branch cannot shrink its own gate) with
no false-positive class. A branch may still add and edit suites, and every added suite runs in
the gate before it lands.

**THE RESIDUAL, STATED RATHER THAN PAPERED OVER.** For `push` events GitHub runs the workflow
YAML **from the pushed branch**, so a branch that rewrites `land-agent-branch.yml` to skip the
policy escapes it. No file in this repository can prevent that. The control is a GitHub-side
ruleset protecting `.github/**` — **Don's setting to apply, not an agent's.** This item closes
accidents and drift; it does not stop a determined agent and must never be described as if it
did. It is in the workflow header, the policy docstring and a test.

**ONE BEHAVIOUR CHANGE, DECLARED.** The old in-job retry re-ran the whole gate when `main` moved
underneath it — which is precisely "run branch code again in the job holding the write token",
so it could not survive the split. `land` still re-merges and pushes when `main` moved with
**documentation only** (the overwhelmingly common case here, and the existing `code_changed`
helper already encoded that judgement), and now **fails with "push again" when `main` moved with
code**. That is the same outcome the old loop reached after three attempts, arrived at sooner,
and it can never push a combination that no gate has tested.

**Verified against this branch's own diff:** the policy exits **2** and names all three
`.github/` paths, including itself.

**LANDED IN TWO PUSHES ON PURPOSE.** Landing the rewritten workflow and the policy together
would have armed a lock against the very file that would need fixing if the rewrite were wrong —
and I cannot run GitHub Actions locally. So push 1 was the restructure (main has no policy yet,
so `.github/` edits still auto-land and a bad rewrite is recoverable), and push 2 armed the
policy only after the new workflow had proved itself on a real run.

`tests/test_land_policy.py`, 20 tests.

### 2. MA12 — every dependency unpinned on a chain that installs fresh and auto-deploys

**Verified, and the measurement is the finding.** The audit says "all ten requirements use
`>=`". There are **eleven** in `requirements.txt` and two more in `requirements-saas.txt` — and
resolving the set for the real target (linux / CPython 3.11) shows **seven of the eleven resolve
today to a higher MAJOR version than the floor they were written against**:

| package | declared | resolves to |
|---|---|---|
| numpy | `>=1.24` | **2.2.6** |
| yfinance | `>=0.2.40` | **1.6.0** |
| stripe | `>=9.0` | **15.5.0** |
| gunicorn | `>=21.0` | **26.0.0** |
| pypdf | `>=5.0` | **6.16.1** |
| reportlab | `>=4.0` | **5.0.0** |
| anthropic | `>=0.34` | **0.122.0** |

So OOB2's class ("something plausible but different reaches the scoring path with no human
step") was not a *risk* in the dependency layer — it was already the *state* of it. yfinance is
the vendor library in OOB2's own story, and it is three majors above its floor.

**TWO LOCKS, NOT ONE, AND THE REASON IS A BEHAVIOUR RISK RATHER THAN TIDINESS.** CI installs
`requirements.txt`; the container installs `requirements-saas.txt`, which adds stripe and
gunicorn. Locking both from the saas superset would have **added stripe to the CI environment**,
and `valuation/saas/billing.py` imports stripe inside `try:` blocks in three request handlers —
so a suite exercising one of those paths could take a different branch purely because the lock
made the import succeed. **Pinning must not change what CI runs.** Hence
`requirements.lock.txt` (52 packages) and `requirements-saas.lock.txt` (55), every line `==`
pinned with a sha256; the core set is a proved strict subset, the delta being exactly stripe,
gunicorn and gunicorn's own `packaging`.

**THE AUDIT NAMES THE WRONG FILE FOR PRODUCTION.** Its `modifies` list is `requirements.txt` and
its file list adds the `Dockerfile` — but the Dockerfile installs **`requirements-saas.txt`**,
which is where stripe (the *billing* path) and gunicorn were floating. Pinning only what the
audit named would have left production's two most operationally sensitive dependencies unpinned.

**NO BEHAVIOUR CHANGE, PROVED RATHER THAN ASSERTED.** Upper bounds were added to both human
files, then the locks regenerated: **byte-identical, both files** (SHA-256 compared). So no
resolution that works today stops working; what the caps close is the *next* silent jump. Each
declaration also carries a `# locked:` note naming the version really running, and a test fails
if that note drifts from the lock.

**Consumers wired** — both `auto-scan.yml` jobs, the land gate, and the Dockerfile, all with
`--require-hashes`, so pip refuses anything that is not byte-for-byte the resolved artifact.
The locks are linux/cp311 **by design** (both consumers are exactly that) and will **not**
install on Windows; `requirements.txt` stays the local path, and a test pins that `run.bat` is
not repointed at a lock that cannot resolve on the only machine that runs it.

Regenerate with `python scripts/gen_requirements_lock.py`. `tests/test_requirements_lock.py`,
10 tests.

### 3. MA17 — the bus test

**Both measured claims reproduce.** README names `VALQUO_LEDGER.md`, `RUN_RULES.md` and
`CLAUDE.md` **zero** times. And the code half genuinely does survive a stranger — every suite
passes with no `data/` directory at all, which is what CI does on every land, since `data/` is
gitignored and the runner never has it.

**THE AUDIT UNDERSTATES THE DOCUMENTATION HALF, AND THIS IS THE PART WORTH CARRYING.** README
did not merely *omit* the ledger — it stated something **false**. Its "Honest limitations"
section read *"I have **not** yet run a point-in-time backtest establishing that it predicts
forward returns"*, and its roadmap listed that backtest as the top open item. Both were written
before the Edge Lab and neither was ever updated — so the front door of the repository told a
stranger that the central piece of work did not exist, months after 224 logged equity trials.
The project-structure diagram made the same omission structurally: no `edge/`, no `screener/`,
no `intraday/`, no `saas/`.

Corrected in place, with the caveats kept and nothing oversold — the headline appears only
alongside the bar it **fails**.

**New `START_HERE.md`** takes a reader clone → green suites → what is actually true → which file
answers which question. It states the licence wall the audit correctly identifies as the real
barrier: **D1 verified Sharadar is personal-use only and forbids commercial use of the data "or
any derivation"**, so a stranger can reproduce the headline only under a licence that would not
let them publish what they derived. That belongs on the quick-start page, not three documents
away.

`tests/test_docs_entry_points.py` pins that the two false sentences cannot return, that
START_HERE names the licence, and that its **directional** claims still agree with
`BACKTEST_RESULTS.json` — directions, not decimals, following `MA19`'s own decision to refuse an
exact-value pin against an artifact refreshed by a 20-40 minute backtest, because *"a gate that
cries wolf is one you learn to ignore"*.

### 4. MA22 — CLAUDE.md has outgrown its job

**Every measured claim reproduces and all three numbers have drifted further.** 371,892 bytes
over **4,112 lines** (the audit says 344 KB / 3,813). Line 23 says `tests/` holds **62** suites;
the git-handoff section at the other end of the same file says the Action *"runs all 24
suites"*; measured, **83**.

**Then it went to 86 before this session ended**, because the session added three suites of its
own. That is the entire argument in one line: **a count that moves inside a single sitting
cannot be maintained by hand.** `RUN_RULES.md` PART 0 now *derives* it
(`ls tests/test_*.py | wc -l`), and a test fails on any document that instructs from a
hard-coded one.

**What moved** — the four sections the audit names (how to run, hard rules, git handoff, tool
routing) plus the session close-out, verbatim except where provably wrong, into **PART 0 of
`RUN_RULES.md`**, which is short and read first. RUN_RULES stays under its own "short on
purpose" promise; a test caps it.

**What was deleted** — the task list, **118 lines**, whose own header read *"This list is the
least trustworthy section in the file."*

**NOTHING WAS LOST, AND THAT WAS CHECKED ROW BY ROW BEFORE DELETING RATHER THAN ASSUMED.** Each
item is recorded elsewhere, in every case more fully: the gated auto-apply of learned weights →
ledger **`MA1`**, which carries the production verification and both commits the task-list entry
lacked; estimate revisions → ledger **`D6`**; sector-neutral, PEAD, the ML combiner and the
forward paper track → their own CURRENT STATE bullets with the numbers; the monotonicity sign
convention → pinned by `test_monotonicity_sign_convention`. The one standing *reading*
instruction (−1.0 is well-ordered, +1.0 is backwards) was carried forward explicitly.

**The findings record was not trimmed** — the audit is explicit that it is load-bearing — and a
test asserts `CLAUDE.md` still exceeds 250 KB, so a future tidy-up cannot trim the wrong half.
**4,112 → 3,966 lines.**

### 5. Defects in my own work

Four, all caught before landing, and two by the tests written to pin the thing they broke.

1. **The anti-rot suite-count check fired on the fix itself.** It flagged `"runs all 24 suites"`
   inside the correction written to *explain* the repair. The only way to green it would have
   been to **delete the historical record** — this project's house style is to correct in place
   by quoting what a claim used to say. Quoted text is now exempt, with a positive control
   proving the exemption is narrow: the same sentence written as an *instruction* is still
   caught.
2. **A workflow probe that could not tell a comment from a command.** The "the write job runs no
   branch code" test searched for `tests/test_*.py` anywhere in the job and failed — on a
   *comment* explaining `code_changed`. Rewritten to assert on the execution forms, with a
   positive control proving the probe fires on the gate job where the loop really runs.
3. **A prose assertion that depended on line-wrapping**, twice: `"or any\n> derivation"` survived
   whitespace collapse as `or any > derivation` because the blockquote marker was still there.
   A test that forces paragraphs to be reflowed to stay green is a test people learn to route
   around.
4. **A false negative I nearly reported as a fact.** Checking whether `origin/main` already had
   the policy, Git Bash mangled `origin/main:.github/land_policy.py` into `origin\main;...`; the
   command failed for that reason and my `|| echo ABSENT` branch printed **"ABSENT"** — the
   answer I expected, arrived at by a route that had checked nothing. Re-done with
   `git ls-tree`, which confirmed it properly.

### 6. Bugs found, not fixed (`RUN_RULES` A3)

* **`auto-scan.yml` grants its jobs no explicit `permissions:` block**, so they inherit the
  repository default. That is MA1/MA10's territory rather than MA11's, and I did not widen scope
  into a workflow that posts to the live service — but the same per-job least-privilege argument
  applies there and nobody has made it.
* **`requirements-saas.txt` names `psycopg2-binary` only in a comment** ("For Postgres in
  production also add..."). If Postgres is ever switched on, that dependency enters production
  unpinned and outside both locks.

### 7. What I did NOT do (`RUN_RULES` A4)

* **I did not apply the GitHub-side ruleset** that would close MA11's residual. It is a
  repository setting, not a file, and it is Don's.
* **I did not run the Actions locally** — that is not possible. The workflow restructure is
  verified by YAML parse, by the two suites that pin its content, and by live fire on this
  branch's own land runs. The two-push sequencing exists precisely because that verification is
  weaker than running it.
* **I did not upgrade any dependency.** The locks pin what was *already resolving*; every
  version above is what CI and Render have been installing. Deciding to move one is a separate
  change with a visible diff, which is the point.
* **I did not touch `RESEARCH_LOG.md`.** All four items are `FIXED`-class with no hypothesis and
  no threshold; charging a trial for them would inflate `N` and *lower* every DSR- and HLZ-gated
  claim.

### 8. A fifth defect, found by watching the run rather than reading it

**The policy speaks in GitHub Actions workflow commands, and the SUITE that tests it was
speaking them too.** `land_policy.main()` prints `::error::` lines so a refusal is loud in the
Actions UI. `test_exit_codes_distinguish_refusal_from_error` calls that function in-process to
check the refusal path — so on the first land run carrying the file, the runner parsed those
lines out of the *suite's* stdout and rendered **three red annotations on a completely green
run**, naming a fixture path (`.github/workflows/x.yml`) that does not exist.

Nothing was broken and that is exactly why it mattered: every future land would have shown red
annotations it should not have, and *"a gate that cries wolf is one you learn to ignore"* is
this project's own phrase. Stdout is now captured — which also let the test assert the refusal
**message**, not just the exit code — and `test_the_suite_leaks_no_workflow_commands_to_the_runner`
walks every test in the module with stdout captured and fails if any workflow command escapes,
so a future test calling the policy directly cannot reintroduce it.

**Found by reading the annotations on a successful run. A green tick is not the whole signal.**

### 9. Verification — live runs, and the sequencing earned its keep

| run | result | what it proved |
|---|---|---|
| `31897680804` | gate ok, land FAILED | The split works; and the first cut's deleted retry was wrong — main moved with code mid-gate and the branch refused to land. |
| `31898053895` | landed | The retry, restored inside the read-only `gate` job, absorbs a moving main. gate 4m39s, land 9s. |
| `31898373985` | landed | The policy reached `main` via the bootstrap branch, exactly as designed. |

Local gate before the first push: **86/86 in 1,320s, zero failures**. Both locks additionally
validated under `pip install --require-hashes --dry-run` for the real target (linux / cp311):
52 and 55 packages resolved, exit 0 — so CI was not the first thing to find out whether the
lock was installable.

**The two-push sequencing was not caution for its own sake — it paid.** The workflow restructure
was wrong on its first run. Had the policy landed in the same push, the lock would have been
armed against `.github/` while `.github/` still contained the bug, and the fix could not have
auto-landed.

---

## 10. MA59 + MA60 — infra's last two audit-#3 rows (2026-08-15, infra lane)

**Zero trials.** Both are simplification/process work with no hypothesis, no threshold and no
verdict against a bar, so equity `N` stays **224** and no published claim moves.
`BACKTEST_RESULTS.json` needs no re-run.

### 10.1 MA59 — the audit is right about every entry on both lists, and it was checked first

The item names two lists: modules whose only importer is a closed study's own script, and
modules that **look** dead and are load-bearing. Both were verified against a **derived** import
graph before anything was touched.

| | claimed | measured |
|---|---|---|
| archive candidates unreachable from a live entry point | 17 | **17 of 17** |
| load-bearing modules still reachable | 6 | **6 of 6** |
| unreachable modules in the package overall | — | **53 of 192** |

**DEADNESS IS TRANSITIVE, AND THAT IS THE WHOLE POINT.** Counting *direct* importers calls
`surface_xsec` production code, because a file under `valuation/` imports it — that file is
`tickflow_signals`, which nothing live reaches. A direct-importer rule protects the wrong module
and leaves the real question unanswered, so the transitive example is pinned as a live test: if
someone rewrites the analysis to count importers, it fails.

**Archived in place, never moved or deleted**, per the audit's own instruction and the B16
pattern already used for `deprecated_options_exit.py`. Each of the 16 modules gains a banner
naming the study that closed and its **real** importers, derived rather than typed so the banner
cannot become a second hand-maintained list that drifts from the first.

**The pin is bidirectional, and the second direction is the valuable one.** A quarantine test
that only checks the dead list catches the harmless mistake — a closed study wired into the live
app — and misses the expensive one: someone reads "looks dead", deletes a D-series alt-data
module, and changes what a past `BACKTEST_RESULTS.json` reproduces.

**Two corrections to the audit.**

* It says to *"keep the pin test as the quarantine proof"*. **`options_tail` and
  `ev_multiples_study` have no importer anywhere in the tree** — no script, no test — so there
  was no pin test to keep. `tests/test_ma59_quarantine.py` is now their only one.
* It says `options_vrp` is archivable while **keeping** `options_vrp_portfolio` for O11.
  **Portfolio imports vrp**, so the two cannot be separated. Archiving in place is fine;
  deleting, as a reader might infer, would not have been.

**The three rejected-intervention env vars now warn.** `SCREENER_SECTOR_NEUTRAL`,
`SCREENER_RESIDUAL_MOMENTUM` and `VALQUO_ROBUST_Z` each re-enable something the research
eliminated, and a run with one set reports under the ordinary headline with nothing anywhere
saying the model changed. The audit offered *"delete the override or make it warn"*; deleting
removes the ability to A/B the rejected arm at all, so it warns. **A test pins that the default
path warns about nothing** — a warning on every ordinary run is noise, and noise gets muted.

**Not done, named so it is not mistaken for done:** nothing is physically moved or removed; the
`options-bot/` tree is untouched; and `WHERE_WE_STAND.md` and `AGENT_LOG.md` are already absent
from the repo, so there was nothing to retire.

### 10.2 MA60 — three of four shipped, and the fourth is blocked by this lane's own MA11

**Bullet 1 (the builder as data-destroyer) was already repaired by a prior lane**, and is
verified here rather than taken on trust: all three sub-defects are fixed, `build_ledger.py`
carries a docstring for each naming what it used to destroy, and `tests/test_build_ledger.py`
pins them. The audit is correct about the history and stale about the tree.

**Bullet 3 (the hand-typed import dict) is the finding, and the audit understates it.**

| | hand-typed | derived |
|---|---|---|
| keys | 13 | **118** |
| edges | 40 | **546** |
| files with real imports absent entirely | — | **105** |
| of its own 13 keys, wrong | — | **12** |

**The failure that matters is not the absences — it is that it was wrong in a direction that
reads as safe.** Four options modules were recorded as importing `statistics.py` when they
actually import `options_stats.py`, so a SOFT collision between two options items fired against
a file they do not share and never fired against the file they do.

**Consequence, measured across all 8,911 item pairs: 150 pairs it reported safe to run in
parallel are genuinely import-coupled, and 7 collisions it reported never existed.** A lane
checker whose graph is stale gets wrong the one answer it exists to get right. It is now derived
from the same graph MA59 uses — **one definition, because two copies of one list is precisely
the MA39 defect**.

**Bullet 4 (CI enforces none of the conventions) ships three checks, each measured before being
pinned** so it could not fail on arrival and be switched off the same day.

* **The canonical artifact may LAG the research log and may never LEAD it.** Exact equality is
  **declined**, following MA19's own refusal on this same comparison: a 20–40 minute backtest
  against an `N` that rises the moment a register lands would be red for the ordinary interval
  between them, and *"a gate that cries wolf is one you learn to ignore"*. The directional check
  has no such window — leading means rows left the log after the artifact counted them, which
  **lowers `N` and raises every DSR- and HLZ-gated claim**. **Live on its first run the artifact
  reads 530 all-domain trials against the log's 531** — exactly the drift the audit says happened
  twice in a week.
* **Every commit a ledger row cites must exist in history.**
* **A register must be added in a markdown-only commit** — the mechanised form of the *"strict
  git ancestor"* evidence the corpus asserts by hand dozens of times. **Measured first: 53 of 59
  registers are clean.** The **6** that are not are grandfathered **by name**, never by pattern,
  because a pattern exemption widens silently. Grandfathering is recorded as *"these six cannot
  support the claim the others can"*, not as exoneration.

**Not encoded, named so it is not mistaken for encoded:** handoff-before-done.

**Bullet 2 (split the land gate from the register pins) is NOT applied, and cannot be from a
branch.** Splitting the gate means editing `.github/workflows/`, and **MA11's land policy —
landed by this same lane the day before — refuses any branch that touches `.github/`.** That is
the policy working, not failing. Weakening it to let this through would be silencing a check to
make a run green, so it is **routed to Don as a human PR**, alongside MA11's own GitHub-ruleset
residual.

**The judgement half ships, derived**, in `scripts/suite_manifest.py`, so applying it is a
two-line workflow edit. **It also corrects the audit: 14 of 94 suites are pure register pins,
not the large tail the item implies** — most closed studies' pin tests import a live module too
and so genuinely exercise production code. The audit's 77-suite figure is now **94**.

**A defect in my own classifier, caught by disbelieving a number rather than by a test.**
`from valuation.edge import kelly` also resolves the package `__init__`, which is reachable, so
the first cut classified **92 of 94** suites as product and the split looked as though it barely
existed. Importing a package is not touching live code.

### 10.3 Verification

`tests/test_ma59_quarantine.py` 11/11 Â· `tests/test_ma60_conventions.py` 10/10 Â·
`tests/test_build_ledger.py` 20/20 Â· **6 of 6 mutations caught** (an archived study made
reachable; a load-bearing module made unreachable; a vacuous graph; the artifact ahead of the
log; a ledger row citing a non-existent commit; a register committed with code).

### 10.3a Is infra closed on audit #3? No — and the two rows that keep it open are these two's parents

This lane was handed MA59 and MA60 as *"infra's last two"*. They are landed. **Infra is not
closed, because `MA21` and `MA23` are still OPEN**, and the audit itself makes them the parents
of exactly this work: *"Pass A's MA23 established the principle (studies mixed into the shipped
package). Pass B's options and factory lanes supply the specific list"*, and MA21 names the
prose-only-conventions class MA60 mechanises.

Both are **advanced and deliberately not closed here.**

* **MA23** asks for a *boundary*, and MA59 draws it — but MA23 also names the `options-bot/`
  tree, which this lane did not touch.
* **MA21** names three recurring manual steps. MA60 mechanises one of them (refreshing
  `BACKTEST_RESULTS.json` after `N` moves is now detected, in the safe direction). `sync.bat` is
  MA20's; re-reading `by_domain` after a merge is still unchecked.

**Closing either on this evidence would be the multi-item-commit-donates-a-verdict trap that
MA60's own first bullet names as still un-encoded.** They stay OPEN, with the work recorded
against MA59/MA60 where it was done.

### 10.4 For Don — two human-only items, both now in one place

1. **A GitHub ruleset protecting `.github/**`** (MA11's residual). For `push` events GitHub runs
   the workflow YAML *from the pushed branch*, so a branch that rewrites
   `land-agent-branch.yml` escapes the in-repo policy. No file can close this.
2. **The land-gate split** (MA60 bullet 2). `python scripts/suite_manifest.py --product` prints
   the suites the gate must keep; `--register` prints the 14 that could move to a nightly run.
   Worth knowing before spending the change: it removes about **15%** of the suites from the
   land path, not the large tail the audit implies.

---

## 11. The repository went public — the visitor-facing accuracy pass (2026-08-16)

**Zero trials** — documentation accuracy, no hypothesis and no threshold. Equity `N` stays
**224**. Ledger row `PUBLIC-DOCS`.

### 11.1 The two findings that were not about accuracy

**Internal business planning was tracked and public.** `LAUNCH_CHECKLIST.md` and `GO_LIVE.md`
are not project documentation — they name a **separate LLC**, discuss **entity structuring to
ring-fence liability**, and set out a **securities-law risk posture about this product**
("don't take a paid subscriber until it's cleared"). Both were tracked, and
`LAUNCH_CHECKLIST.md` has been in the repository since 2026-07-24.

They are now **untracked and gitignored, and both files remain on disk.** Stated plainly because
a half-measure that reads as a fix is worse than none:

> **This stops them being served on the repository page going forward. It does NOT remove them
> from public git history.** Only making the repository private again, or rewriting history
> (`git filter-repo`, then a force-push, which invalidates every existing clone), actually
> removes them. **That is Don's decision and this lane did not take it.**

**No `LICENSE` file exists**, so default copyright applies — all rights reserved. That is a
defensible posture for a public portfolio repo, but it is currently implicit. Choosing a licence
is Don's call; the README now states the position rather than leaving it unstated.

### 11.2 What was actually wrong with the README

It described the DCF engine well and was **three months and three audits stale** on everything
after it.

* It was **silent on four of the five product surfaces** — screener, Valquo Index, Dip Detector,
  options.
* Its roadmap still listed the point-in-time backtest as the **top unbuilt item**, months after
  224 pre-registered equity trials had been charged against it. (The body had been half-corrected
  by MA17; the roadmap had not, so the document contradicted itself.)
* It linked two sibling projects by **relative path**, and one of them — `../screener` — names a
  repository that **does not exist** (it is `stock_screener`). Both are absolute URLs now.
* The **GitHub repo description was empty**, which is the first thing a visitor reads. Set.

### 11.3 The rewrite's organising idea

Not "what does Valquo do" but **what does each surface actually claim**, because they do not
carry equal evidence and that distinction matters more than any single number:

| surface | status now stated |
|---|---|
| Valuation engine | a model; never backtested as a return signal |
| Hot-stocks screener | **the one measured claim** |
| Valquo Index | running paper track; **no verdict before 2031** |
| Dip Detector | return claim **NULL**, risk claim measured |
| Options / intraday | **measured and negative** — loses to random entry by 5.06pp |

Every figure was **re-derived from `BACKTEST_RESULTS.json`**, not copied from prose: alpha
+7.17%/yr, net +6.07%/yr, long-short HAC *t* 2.6199, X7 floor 2.2837 (clears), HLZ hurdle 3.2899
at `N` 224 (fails by 0.6700). The README states **both** sides of that tension, as the artifact
itself does.

The paper-track dates are **derived from `track_meter`, never quoted** — gate 2027-02-13, verdict
2031-08-13 — and a test fails if the README carries a literal instead. The record shows that same
date wrong in three documents at once because each had quoted one. The README also says the track
is **currently not recording** (`recording_ok: false`, ledger `PT-WRITER`), rather than implying
a healthy live test.

### 11.4 A correction to the record, found while verifying

**`CLAUDE.md`'s "THE LIVE PRODUCT SCORES A FOUR-THEME BOOK" is superseded.** `FIDELITY-2` rebuilt
`institutional` and `insider` to the panel's own definitions and both cleared the fidelity gate
at **+0.9190** and **+0.8726**, so **all seven weighted themes now reach a live score**. The
README does not repeat the stale claim. This is exactly what `RUN_RULES` A8 is for — the four-
theme figure was the single most quotable honesty caveat available and it is no longer true.

### 11.5 `DATA_AND_METHODS.md` was a private consulting memo

Written in the second person, it named **a specific university** as the recommended data route,
recommended **buying data the project had already bought**, and listed three capabilities as
*"to add"* — a survivorship-free adapter, point-in-time fundamentals, delisting returns — **all
three of which have shipped**. It also contradicted itself: §3 asserted the "HLZ *t* > 3" gate
that §4's own MA5 correction refutes. De-personalised, corrected, and the Sharadar
personal-use-only licence limit now appears wherever a headline figure does.

### 11.6 Verification

`tests/test_public_docs.py` **17/17**, **6 of 6 mutations caught** (a stale alpha; dropping the
failed HLZ bar; losing the licence wording; a private-business phrase reappearing; a relative
sibling link returning; a product surface going undocumented). Full local gate green before push.

**A defect in my own mutation harness, worth recording because it looked like a failing check.**
The licence mutation reported MISSED, which reads as "the test cannot fail". The test was fine:
the README wraps the phrase as `"or any\nderivation"`, so the suite's `flat()` normaliser sees it
and my raw-text replacement never applied. **The harness was wrong, not the check** — diagnosed
before concluding anything about the test.

---

## 12. The licensed-data question, answered; and two decisions recorded as decisions (2026-08-16)

**Zero trials.** Ledger row `PUBLIC-DOCS` (amended).

### 12.1 THE SHARADAR DATA WAS PURGED. It is not in the public repository.

Three commits — `4376560`, `e0a0732`, `4f01655` — did add licensed Sharadar exports
(`data/backtest_med/`, `data/backtest_test/`: `fundamentals.csv`, ~1.43M rows of `insiders.csv`,
`institutional.csv`, and hundreds of per-ticker price CSVs). **They were removed from published
history by a rewrite on 2026-07-28 07:35:40** and are not reachable from GitHub.

Five independent checks, each reproducible:

| check | command | result |
|---|---|---|
| Which refs contain them | `git branch -a --contains 4376560` | **local only** — `backup/pre-filter-20260728-073540`, `backup/ui-polish-preRebase`. No `remotes/origin/*`. |
| Ancestor of published main | `git merge-base --is-ancestor <sha> origin/main` | **no**, all three |
| Any origin ref touching the paths | `git log --remotes=origin -- data/backtest_med` | **zero commits** (same for `backtest_test`) |
| Everything ever added under `data/` | `git log --remotes=origin --diff-filter=A --name-only -- data/` | **exactly one file: `data/.gitignore`** |
| GitHub itself, abbreviated **and** full SHA | `gh api repos/.../commits/<sha>` | **HTTP 422 "No commit found"** |

**The API check has a positive control**, because a negative result from a broken probe is the
classic false all-clear: `2971f71` — the repository's root commit — resolves to its full SHA
through the same call. So the 422s mean the objects are absent, not that the check is blind.

**The backup ref's own name is the citation.** `backup/pre-filter-20260728-073540` is the
pre-rewrite snapshot, dated to the second, and it is **local**. That is why the data still exists
on Don's machine and nowhere else.

**A broader sweep, because the question implies a general property rather than three commits.**
Every data-shaped file ever added to published history: four `data_export/*.csv` (Valquo's **own**
paper-track output, not vendor data) and three `options-bot/handoff/*.zip` — inspected, **zero**
`.csv`/`.parquet`/`.pkl`/`.db` entries between them; they are the source-recovery archives that
preserved the decommissioned box's code. **No vendor data anywhere in published history.**

**THE REAL GAP WAS THAT NOBODY WROTE THIS DOWN.** The rewrite happened operationally and appears
in no ledger row, handoff or commit message — the only trace was a local branch name. That is why
the question recurred. It is now recorded here, and
`tests/test_public_docs.py::NoLicensedDataIsTracked` makes the **next** accidental commit fail
before it can be pushed: nothing may be tracked under `data/` except its `.gitignore`, and no
`.csv`/`.parquet`/`.pkl`/`.db` may be tracked outside `data_export/` and test fixtures. A rewrite
already happened once; a guard is much cheaper than a second one.

### 12.2 DECISION — the two business documents stay in history

**Don's call, 2026-08-16, recorded so it is a decision and not an oversight.**
`LAUNCH_CHECKLIST.md` and `GO_LIVE.md` remain in public git history. They are untracked going
forward (section 11) and will not be rewritten out.

**The reasoning, in his terms:** they are business-plan notes for a free tool, not credentials
and not vendor data. A `filter-repo` + force-push costs **every terminal a re-clone and breaks
eleven worktrees**, which is a real and immediate cost set against a near-zero risk.

**This is the correct call and the asymmetry is worth stating**, because it is exactly what
separates it from §12.1: the licensed-data case would have justified the same expensive operation
— a vendor licence breach on a public repo is a different class of problem from a founder's own
planning notes being visible — and it turned out not to need it. **Reopen this only if the
content changes character** (credentials, third-party data, or anything under an NDA), not merely
because it is still findable.

### 12.3 DECISION — MIT, with a scope note

**Don's call, 2026-08-16.** `LICENSE` is MIT, © 2026 Donovan Corbin, referenced from the README.

**It carries a scope note, and that is not boilerplate.** MIT grants rights over *the copyright
holder's own work*, and this repository publishes figures **derived from licensed vendor data** —
`BACKTEST_RESULTS.json`, `data/free_analysis/`. A bare MIT header would purport to grant
redistribution rights over material that is not Don's to grant, which is the same licence problem
the data purge was about, one level up. The note says plainly: MIT covers the **source code**; no
vendor data is distributed; the research artifacts are published as a **record of what was
measured so the claims can be checked**, not as a dataset anyone may redistribute; and the JKP
international factor data is CC BY-NC 4.0, research-only.

`tests/test_public_docs.py` 23/23 — the licence's existence, its MIT identity, the scope note and
the README's link to it are all pinned.

**A defect in my own test, and it is the second instance of one trap in one day.** The scope-note
assertion first read the LICENSE raw and failed, because the file wraps the phrase as
`"or any\n    derivation"`. The identical wrap had already produced a misleading MISSED in the
mutation harness that morning. **A wrapped claim is still the claim** — assert on the flattened
text.


---

# 13. MB27 + MB28 — the board derives itself, and the monitor gets a clock (2026-08-19)

**Zero trials.** Every statement here is a fact about what git says or what a scheduled task
does — no hypothesis, no threshold, no verdict against a bar. `RESEARCH_LOG.md` is untouched, so
`by_domain` is unchanged by construction; **re-read after this merge it is equity 234, options
300, infra 15**, which independently corroborates `MB31`'s staleness map. No `RESEARCH_LOG` row
is appended, following `MA59`/`MA60`, which are infra items of this same class and appear
nowhere in that log. Nothing under `valuation/` changed and no published figure moves.

**A correction to my own first draft of this line, made before it shipped:** it read *"equity `N`
stays 224, options 292"* — figures carried from a prior session's context rather than re-read.
This file records that error twice already (*"an equity figure must be RE-READ from `by_domain`
after a merge and never quoted from a session's own mid-run measurement"*), and it was committed
here with the warning in view.

`.github/` was not touched. Both items were checked against the tree before being built, and
**three of the audit's own prescriptions did not survive that check** — they are corrected below
rather than obeyed (`RUN_RULES` A8: verify, do not repeat).

---

## 13.1 MB27 — the premise is exact, and two of its four derivations are not

**The premise, verified rather than repeated.** `ma_in_flight.json` was hand-typed on 2026-08-14
and lists `MA13`, `MA19`, `MA36`, `MA37`, `MA15`, `MA16`, `MA20`, `MA35`. Read back through
`build_ledger.read_ledger()`, **all eight are `DONE`** — so "five days stale and 100% wrong" is
exact, and the file was carrying its own `how_to_refresh` command that nobody ran. That is
`MA59`/`MA60` one level up: a hand-typed snapshot of something git already knows.

**Shipped: `scripts/board_state.py`.** Six ingredients, no hand-typed input, ~6 seconds.

```
  LANES IN FLIGHT: 1   (kept rescue/backup refs, not lanes: 5)
    worktree-optionsbot-lane                     +3    local+remote
  WORKTREES: 12   with uncommitted work: 8
  ITEMS CLAIMING TO BE IN FLIGHT: 1     D11  INPROGRESS
  HANDOFFS: 48   oldest by last commit: HANDOFF_growth_valuation.md 16.94 d
  GIT LOCKS: 2       39.57 h  objects/maintenance.lock
  DRIFT HEARTBEAT (MB28): NOT INSTALLED
```

### The two derivations that are wrong, both measured

**(1) `IN ?PROGRESS` against the ledger status cell matches a cell that says the opposite.**
`B13`'s status reads `**PARTIAL - BLOCKED ON DATA, NOT IN PROGRESS**`. The audit predicts two
hits and names both; **one of the two is a negation**, so the literal rule carries a **50%
false-positive rate on its own predicted evidence**. This project already found that exact trap
once, by hand, in the `PT-WRITER` session — *"the single string match is `B13`, whose cell reads
'NOT IN PROGRESS' — a negation"* — and the audit re-proposed the naive rule anyway. Negation is
handled, and it ships with a **control that fails if the naive rule ever stops being wrong**,
so the guard cannot quietly become pointless.

**(2) A HANDOFF's mtime is not its freshness.** Measured in this worktree immediately after
`git merge origin/main`: `HANDOFF_edge_audit.md` and `HANDOFF_optionsbot.md` both carried
**11:27, the merge minute**, as their mtime, while `HANDOFF_ci.md` — which the merge did not
touch — still read three days old. **mtime records when git last WROTE the file into this
checkout**, so in a fresh worktree every handoff would read as newly touched and the ingredient
would be pure noise. Age comes from the newest commit touching the file; uncommitted
modification is read from `git status` rather than inferred.

### (3) The one permitted assertion cries wolf, and is declined — with the reason

MB27 allows exactly one failing assertion: *"the generated board file is older than the newest
branch tip it claims to describe."* Measured against this board's own strongest ingredient, that
fires constantly. **Worktrees carrying uncommitted work read 8 of 12 today and change whenever
anybody saves a file**, so a committed snapshot goes stale within minutes of every regeneration
and the pin would be red on ordinary work — **`MA21`'s failure mode reached by a pin instead of
by a warning**, which is precisely what `MB30` makes binding on this item.

**A generated snapshot rots exactly like a hand-typed one; it just rots honestly.** So there is
**one copy of the fact and it is git**:

* `ma_in_flight.json` is **RETIRED into a pointer** carrying its 2026-08-14 contents verbatim
  (rule 9 — nothing deleted), plus the measurement that retired it and the reason a generated
  file did not take its place;
* `--write` emits a snapshot **to a gitignored `.board_state.json`** when a session actually
  wants one to hand on;
* and the assertion that **cannot** cry wolf is the one that ships: **the retired file makes no
  dated claim at all.** A file that says nothing about today can never again be wrong about it.

### What it adds that the hand file could not

`ma_in_flight.json`'s own caveat named its hole: *"an agent editing files in a worktree with
nothing committed yet is invisible here."* That is derivable, and it is **8 of 12 worktrees
right now** — the ingredient most likely to catch a live collision, and the one the audit's
table does not have. The board also reports **how old the refs it derived from are**, because a
board saying "0 lanes in flight" off a week-old fetch is not measuring the board.

**It corrects the audit's own table in passing:** MB27 gives in-flight branches as **0**;
measured, it is **1** — `worktree-optionsbot-lane`, +3, live on local and remote.

**And it demonstrated its own point inside one session.** Run again thirty minutes later the
board read **2** lanes: `worktree-demo-link` had gone +2 and is **local only**, so no other
lane's `git fetch` can see it at all. In the same half hour the `audit4-frontier` worktree lock
was released and two more worktrees picked up modifications. **That is four state changes in
thirty minutes on a file that was hand-refreshed once in five days** — the reason the answer is
a command and not a document.

### It never warns

Counts only. **Exit 0 on every finding** — a stale lock, eight dirty worktrees and an empty
board all exit 0. The only non-zero exit is **2, meaning the script itself broke**.
`checkout_drift.py` takes the opposite line (*"'I could not tell' and 'all clear' must never
share an exit code"*) and both are right, because an **ALARM exists to fail and a REPORT exists
to describe**. What carries across is the half that always applies: **an unmeasurable ingredient
reads `null` and renders `UNMEASURED`, never silently `0`.** A zero meaning "nothing in flight"
and a zero meaning "git did not answer" would be `checkout_drift`'s founding defect in a new
costume.

---

## 13.2 MB28 — the item's first half holds, its framing is out of date

**Confirmed:** nothing invokes `checkout_drift.py` on a schedule. No task, no workflow.

**Corrected, and this changes what the fix is for.** The **cure** has a clock and it is working:

| | MA20 measured (2026-08-14) | today (2026-08-19) |
|---|---|---|
| shared checkout | **1 ahead, 514 behind** | **0 ahead, 19 behind** |
| `ValquoSyncCheckout` | not yet installed | registered, daily 19:30, last run 2026-08-18 19:30:01, result **0**, 19 runs logged |
| stranded `PT-WRITER` commit | unpushed since 2026-08-10 | rescued |

So the alarm's job is no longer *"tell Don he has drifted"* — the nightly sync handles that,
unattended. Its job is the one nothing covers: **tell the next session whether that sync is
still running at all.** If the task is deleted, or the machine is off for a week, `sync.log`
simply stops growing and no surface anywhere says so. That is the mandate's own thesis, one
layer further in.

**Shipped and proven runnable:**

* `scripts/drift_heartbeat.py` — measures once and writes `%LOCALAPPDATA%\Valquo\drift.json`.
  **The file's mtime is the measurement**; `board_state.py` reports its age, so a dead clock
  shows up as a number in a report somebody already reads instead of as silence.
* `drift_heartbeat.bat` — what the task runs; passes the alarm's exit code straight through so
  Task Scheduler's `LastTaskResult` keeps meaning what the alarm means.
* `install_drift_task.bat` — registers `ValquoDriftCheck`, daily **20:30**, no admin rights.

**Three design points, each pinned by test:**

1. **One measure, not two.** It imports `checkout_drift.measure`/`verdict`. A second
   implementation of "how far behind is the checkout" is the defect `MA5` and `MA39` each closed.
2. **It always writes, even when it cannot measure.** A failed run still writes `state:
   "unknown"` and exits `ALARM`. Skipping the write would make *"could not measure"* and *"the
   task is not installed"* produce the identical observable — a missing or frozen file.
3. **It is a separate task, not a line in the sync bootstrap.** Bolting it on would make it die
   exactly when the sync task dies, **which is the failure it exists to detect.** 20:30 is after
   the 19:30 sync and the 20:00 auto-push, so it measures what the day's automation left behind.

**The regress is bounded, not solved, and it is stated in the source.** If `ValquoDriftCheck` is
itself deleted, its heartbeat freezes silently too. What stops that being invisible is that the
age is **reported to a reader** rather than watched by another watcher: there is no chain of
watchers that terminates, only the point at which a human sees a number.

**NOT INSTALLED BY ME, and that is deliberate.** Registering a scheduled task is Don's machine
state. The board currently reports the heartbeat as **NOT INSTALLED**, which is the truth and is
what makes the field non-vacuous.

### For Don — the two-line wiring (`MA60`'s pattern)

```
  double-click   install_drift_task.bat        (once; no administrator rights)
  then any time  python scripts\board_state.py
```

To remove it: `schtasks /Delete /TN "ValquoDriftCheck" /F`. It only looks — it never fetches,
merges, pushes or repairs. The cure is still `sync.bat` and still a human's call.

---

## 13.3 Defects in my own work, reported because each produced a plausible wrong answer

* **The board counted one lane as two.** `worktree-optionsbot-lane` and
  `origin/worktree-optionsbot-lane` are the same lane seen locally and remotely; the first run
  printed **"LANES IN FLIGHT: 2"** for a single live lane. Caught by running it, pinned.
* **A speedup that was wrong, reverted rather than kept.** Replacing 48 per-file `git log -1`
  calls with one `--name-only` walk cut 10.1s to 1.0s and **disagreed on 2 of 48**, always
  returning an *older* commit — because **`--name-only` prints no filenames for a MERGE commit**,
  and this repo lands every lane through a merge, so it is the common case rather than a corner.
  The identical command is parallelised instead (2.8s), **verified bit-identical on all 48**.
  `branches()` kept its optimisation, which is a different shape: `for-each-ref --no-merged`
  narrows the candidate set before counting, 17.3s to 1.3s, and cannot change an answer.
* **Two of my own tests passed against a defective tree**, both caught by the mutation harness
  rather than in production:
  * the mtime test touched a file to `now` and compared before with after — but the file it
    picked **already carried a near-`now` mtime**, so both readings were ~0 under the defect and
    it agreed with itself. It now drives the mtime to a value no handoff can legitimately have.
  * `assertIn("20:30", bat)` passed against an installer whose schedule had been moved to 09:00,
    because **the comment block above still said 20:30**. Comment-versus-code — the family this
    project has now found five times. It reads the `set "WHEN=..."` assignment.

* **AND ONE OF MY TESTS PASSED LOCALLY AND FAILED IN CI, which is the worst way to be wrong.**
  `test_a_healthy_run_writes_ok_and_exits_zero` ran the heartbeat with no `--repo`, so it
  measured `checkout_drift.SHARED_CHECKOUT` — a pinned `C:\Users\donni\...` path that exists on
  exactly one machine. Green on that machine, and on the ubuntu runner it read
  `AssertionError: 'unknown' not found in ('ok', 'alarm')`. **The pin is correct and deliberate**
  — `checkout_drift`'s own header explains that a copy measuring "its own tree" would always see
  a fresh worktree and always say fine — so the defect is a test that silently inherited a
  machine-specific default. It now builds its own origin-and-clone via
  `test_checkout_drift.build`, the one fixture builder, and **the fix is verified against the CI
  condition rather than assumed**: re-run with `SHARED_CHECKOUT` pointed at a nonexistent path,
  all 31 pass. The local gate could not have caught this, because locally the path exists.

**MUTATION-TESTED 8 of 8 caught, 0 missed.** The eight include the audit's own naive
`IN ?PROGRESS` rule, rescue refs counted as lanes, `UNMEASURED` degrading to `0`, the board
exiting non-zero on a finding, handoff age following the filesystem, the two modules disagreeing
on the heartbeat path, the heartbeat skipping its write, and the installer scheduled before the
sync. **A tripwire that cannot bite is not a check.**

---

## 13.3a The retirement broke a consumer, and the break IS the finding

**`scripts/ma_dependency_map.py` read `ma_in_flight.json`**, stamping an `[IN FLIGHT]` flag onto
every item in two rendered tables and into `ma_dependency_edges.json`. Retiring the file left
those fields null, so the committed artifact no longer matched its generator and
`test_ma_dependency_map.py::test_the_committed_artifacts_are_current_against_the_items_file`
went red.

**A CORRECTION AGAINST MY OWN FIRST DIAGNOSIS, WHICH I HAD ALREADY REPORTED.** I attributed the
staleness to the merge — nine new modules under `valuation/`, since `MA59`/`MA60` made the map's
import graph derived — and said it was not mine. **Measured, it is entirely mine:** restoring the
original `ma_in_flight.json` and re-running `--check` exits **0**. The nine modules moved nothing.
The right control was one command and I published a hypothesis before running it.

**Why the break is worth more than the fix.** It is the concrete demonstration of the very
argument §13.1 makes for declining MB27's assertion: **retiring one hand-typed file staled a
committed artifact.** If a *file being replaced* can do that, a *branch moving* certainly can —
which is what a committed board snapshot would have to survive, several times a day, forever.

**AND THE FLAGS WERE NOT MERELY STALE, THEY WERE ROUTING PEOPLE AWAY FROM FINISHED WORK.** The
regeneration diff removes `**[PREREG committed blind]**` from **`MA13`, `MA19`, `MA36` and
`MA37`** — every one of them `DONE`. A dispatcher reading the map to pick an item was being told
that four completed items were claimed and half-measured, which is the precise harm the flag was
built to prevent, inverted. **A stale in-flight flag is worse than none**, because absence
prompts a check and a confident wrong label does not.

**So the coupling is cut rather than patched.** Regenerating would have "fixed" it while leaving
the generator reading a retired file to emit a permanently-null field, and leaving the map's own
prose advertising that file as the live authority in three places. Instead:

* the generator no longer opens `ma_in_flight.json`, and `in_flight` is gone from the schema —
  the artifact now derives only from the items file and the import graph, neither of which moves
  when a branch does;
* the map's three pointers now name `python scripts/board_state.py`, and it carries a paragraph
  saying it **deliberately does not know** what is in flight, with the reason;
* the two tests that read the retired file are replaced. **Left alone they would have passed
  VACUOUSLY** — the stub's only non-`_meta` key is `_retired_2026_08_14`, which is not an MA id,
  so both loops iterated nothing. A green test that inspects nothing is the failure this repo
  keeps finding, so they now pin that no live board state is embedded and that the map points at
  the derivation.

**And the comment-versus-code family showed up inverted.** My replacement test stripped comment
lines and asserted the bare filename was absent from the generator — and **failed against the
fixed tree**, because the generator now emits a paragraph of prose *about* the retired file into
the map. Documentation inside a string literal reads as code to a line filter. It names the read
(`ROOT / "ma_in_flight.json"`) instead.

---

## 13.4 A trap worth writing down: `pytest tests/` is not the gate

Verifying this work, `python -m pytest tests/` reported **115 failed / 3176 passed** in 20
minutes on a tree the real gate passes clean. **CI runs `for f in tests/test_*.py; do python
"$f"; done` — one process per suite — and that isolation is load-bearing**: run everything in a
single process and Flask app singletons, `create_saas_app`'s idempotency and shared module state
contaminate each other. Every one of the 115 is an artefact CI will never see.

It is recorded here because the failure mode is expensive in the wrong direction: **115 red
suites is exactly the sort of result that gets read as "my branch broke the world"**, and the
honest reading is "I ran the wrong command". Mirror the loop when checking a branch.

---

## 13.5 Reported outside this lane (`RUN_RULES` rule 3)

* **`RUN_RULES.md` said "Repo is private"** — false since 2026-08-16, and it is the rule most
  likely to be relied on when deciding what is safe to commit. **Fixed here** as a one-clause
  correction, declared as a scope departure rather than absorbed: leaving a false privacy claim
  standing in the governing document of a public repo is not a stylistic matter.
* **`RUN_RULES` Part B rule 6 told agents in flight work is unobservable** — *"ask for a
  screenshot … that is not a failure of the handoff method, it is its boundary."* `MB27` moved
  that boundary, so the rule now points at `board_state.py` first and keeps the screenshot for
  what is genuinely unobservable: an agent's live reasoning, and other machines. **A tool nobody
  is told to run reproduces the disease it cures**, which is why this edit is part of the item
  and not decoration.
* **~~`tests/test_o21d2_alternative_pnl.py::test_the_real_harvest_freeze_resolves_when_mounted`
  is unpassable wherever it is not skipped~~ — SUPERSEDED THE SAME DAY, and the correction is
  recorded rather than the finding quietly dropped.** Diagnosed here independently: it skips when
  the freeze is absent (Linux CI has no `D:`), so it landed green, while on the machine that
  actually holds the data it asserted `prov["frozen_from"] == "D:/thetadata/chains"` against a
  real `D:\thetadata\chains` — a path-separator comparison, every other field in the block
  correct. **The options-bot lane had already fixed it as `MB42` (`90738f7`), landing while this
  was being written**, and their fix is better than the one I was about to suggest: a `_same_path`
  helper plus `test_the_frozen_from_comparison_runs_on_every_platform`, which pins both
  separators **and** a negative case, so the comparison is exercised on Linux CI where the
  original could only ever skip. Confirmed green on the merged tree. **Reported, not fixed, was
  the right call** — rule 3 — and it is a clean instance of two lanes finding one defect from
  opposite ends within hours.
* **`tests/test_sync_checkout.py` failed in the full-gate loop and passes 32/32 in isolation.**
  The known intermittent temp-directory permission error on `%TEMP%` under Windows, already
  recorded; Linux CI is unaffected. Reported so the next reader does not chase it.
* **`RUN_RULES` Part B rule 3 carried a caveat `MA59`/`MA60` had already spent** — it warned that
  `check_lanes.py`'s map "reported (nobody) for `config.py` and `screen.py`", a symptom of the
  hand-typed import dict measured at 13 keys / 40 edges against a real 118 / 546. That dict is
  gone; the caveat is corrected in place rather than repeated.
* **Audit #4 is not ingested into the ledger.** `grep -c '^| MB' VALQUO_LEDGER.md` read **0**
  before this session; only `MB27` and `MB28` are added here. The other MB rows are somebody's
  ingest job, and the `MA` precedent says do it deliberately — that ingest previously collided
  with live human rows and had to be resolved by contract rather than by `merge=union`.
* **`D11` is the only genuine `IN PROGRESS` row and its own handoff says the miner is idle.**
  Reported, not changed: correcting another lane's status cell from outside it is exactly the
  kind of edit the ledger's `src` column exists to prevent.

## 13.6 What this did not do, named so it is not mistaken for done

* **`MB29` (the prompt receipt) is NOT implemented.** The audit costs it as *"a convention plus
  ~5 lines inside `MB27`'s script"*, and the reporting half genuinely is nearly free — but the
  **convention** half is the load-bearing part (*a lane's first commit on its branch is its
  prompt, committed alone, as `PROMPT_<lane>.md`*), and adopting a convention for every other
  lane is not a thing this lane can do by writing five lines. Reporting a receipt nobody has
  agreed to leave would put a permanently-red-looking column on the board on day one.
* **`ValquoDriftCheck` is not registered.** Shipped runnable, routed to Don, and the board says
  `NOT INSTALLED` until he runs it.
* **`MB27`'s kill condition is answered early and in favour of deriving**: it asks for the
  generated and hand boards to be compared over four weeks and the generated one deleted if they
  disagree on fewer than two items. They disagree on **8 of 8** today, so the comparison is
  already decisive; the hand file is retired rather than kept running for four more weeks.
