# PR — move PT-WRITER to a GitHub Action, and repair the shared checkout

**For Don to run.** Two independent problems, both found 2026-08-16. Closes ledger rows
`PT-WRITER` and `MA18`, and carries MA60's residual as an optional second commit.

---

## Why this is a human PR

`MA11`'s land policy refuses any agent branch that touches `.github/`. That is a good rule and
should not be weakened to let this through — weakening it would be silencing a check to make a
run green. So this lands as a PR you open. `MA60`'s last bullet (splitting the land gate from the
register pins) is blocked on the identical rule, so if you want, the two travel together.

---

## Problem 1 — the writer could never have worked from where it was running

The task ran on 2026-08-14 and **correctly refused**: exit 2, *"the benchmark SPY could not be
priced on the inception 2026-07-30 (a benchmark gap makes the excess unmeasurable, so no row is
emitted rather than a Valquo-only one)."* It pushed a dated failure note and modified nothing.
The contract worked.

**The root cause is the network and it is structural.** The Cowork lane's egress allowlist blocks
both shipped price vendors — `stooq.com` and `query1.finance.yahoo.com` both return
proxy-refused — so no ticker priced at all. Rescheduling, retrying, or adding a fallback vendor
cannot fix it. GitHub's runners reach both, which `auto-scan.yml` has demonstrated every weekday
for weeks.

Moving it also retires MA18's second half: the record stops depending on one desktop app being
open at 20:01.

## Problem 2 — the shared checkout has been drifting for weeks

```
local HEAD  41d7b12      origin/main  cbeb658
behind:     621 commits      local-only: 1 commit
```

`scripts/track_row.py` **does not exist in your working tree** — it is on origin only. So step 2
of the old task (`git pull`) had to merge rather than fast-forward, and the script it then tried
to run was absent. Your agents work in worktrees off origin, so none of them ever saw this.

**The local-only commit is safe to discard, and here is the evidence rather than the assurance:**
`41d7b12` is *already recorded on origin* — origin's `HANDOFF_STATUS.md` line 450 cites it by
hash and describes the whole incident. Its diff is 2,226 insertions against 2,212 deletions on a
single file, which is a line-ending rewrite, not content. You still keep a ref, because this
project archives rather than deletes.

---

## Step 1 — repair the checkout

PowerShell, in `C:\Users\donni\Downloads\valuation-tool`. **Separate lines, not joined with `&&`.**

```
git fetch origin
git branch backup/local-main-2026-08-16 41d7b12
git status --porcelain
```

If that last command prints anything, stop and tell me what — there is uncommitted work to keep.
If it prints nothing:

```
git reset --hard origin/main
git log --oneline -1
```

You should see `cbeb658 AUDIT #3 EXECUTED: the final nine...`. Confirm the script now exists:

```
python -c "import scripts.track_row; print('present')"
```

## Step 2 — open the PR

```
git checkout -b pt-writer-action
mkdir -Force .github\workflows
git mv PROPOSED_track-row.yml .github\workflows\track-row.yml
git add .github\workflows\track-row.yml
git commit -m "PT-WRITER: move the daily row to an Action; the Cowork lane cannot reach either price vendor"
git push -u origin pt-writer-action
gh pr create --fill
```

Then merge it in the GitHub UI.

## Step 3 — verify it actually writes, before trusting it

Do not wait for the cron to prove it. In the Actions tab, run **PT-WRITER** via
*Run workflow* on a weekday after the US close, then:

```
git pull
Get-Content data\valquo_track_history.csv -Tail 3
```

**Two outcomes are both correct.** A new dated row means it works. A pushed refusal note appended
to `HANDOFF_STATUS.md` means the vendors were unreachable *from the runner too*, which would be
new information and worth telling me. A silent success with no file change fails the job by
design — the workflow treats "exited 0 and wrote nothing" as a failure.

---

## What the workflow does, and the three things it refuses to do

One cron at 22:12 UTC weekdays — 6:12pm EDT and 5:12pm EST, so it is after the close in both
halves of the year and needs no DST pair. A backup at 23:37 UTC because GitHub's free scheduler
drops top-of-the-hour runs; it is a no-op if the primary landed. Odd minutes, hash-pinned deps
per MA12, concurrency-grouped so the two can never race the same file.

It refuses, mechanically rather than by intention:

1. **It cannot modify a prior row.** The file's previous content must remain an exact prefix of
   the new content or the job fails and pushes nothing. The contract's "gaps are logged, never
   filled" stops being a promise and becomes a check.
2. **It cannot report a silent success.** Exit 0 with no file change fails.
3. **It cannot fail quietly.** A refusal is appended to `HANDOFF_STATUS.md`, committed, pushed,
   and announced to Discord if the webhook secret exists. No new secrets are required.

## One thing I could not verify from here

Whether branch protection on `main` will accept a push from `GITHUB_TOKEN`. If the Action's push
is rejected, the fix is either to allow the `pt-writer[bot]` actor in the branch-protection
settings or to have it open a PR instead of pushing. I would rather flag that now than have you
discover it as a red run at 6pm on a Tuesday.
