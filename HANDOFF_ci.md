# HANDOFF — CI: stop the auto-land churn (r1 lane, 2026-08-07)

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

**`auto-scan.yml` and `track-backup.yml` still carry `checkout@v4` / `setup-python@v5` and I left
them that way ON PURPOSE, for this pass.** They use the same actions, so the bump is mechanical —
but `auto-scan.yml` runs the production scans with live secrets, and I am not willing to bump it on
the assumption that `v5`/`v6` resolve. Landing this branch *proves* they resolve, because the land
Action is the thing running them. Once green, the other two are a two-line change per file with the
evidence already in hand. Doing it in that order is the difference between a verified change and a
hopeful one.

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
