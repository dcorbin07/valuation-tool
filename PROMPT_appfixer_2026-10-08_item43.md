# PROMPT — app fixer — 2026-10-08 — item 43: git_push.bat diverges whenever it is needed

On 2026-10-08 Don's `git_push.bat` and `sync.bat` both failed with "rejected (non-fast-forward)",
and running sync.bat did not cure it. Measured cause: the folder had uncommitted edits (the
manager's DECISIONS.md and PROMPT files) while lanes had landed on GitHub. `sync_checkout.py`
refuses a fast-forward over a dirty tree (parked the edits on a rescue/ branch), then
`git_push.bat` COMMITTED them on top of the stale main, which made main DIVERGED, and the push was
rejected. sync.bat then refuses a diverged branch by design. So the one sequence Don runs every
day — edits exist, lanes have landed — produces a divergence nothing he runs can fix.
`rebase_push.bat` (in the folder root, untracked) was the one-off cure.

Fix the flow so this cannot recur: commit the folder's edits first, then fetch, then replay ONLY
commits that exist solely in this folder onto origin/main (rebase), aborting and reporting —
never discarding — on any conflict, then push. Keep every existing guarantee (tests before push,
never push red, never merge agent branches locally, nothing discarded, .env and data never
committed). Decide whether `rebase_push.bat` should be committed as a documented recovery tool or
removed once the flow is fixed, and say which. Test the dirty-tree-plus-landed-lane case
explicitly against a real temporary repository with a fake remote.

Done means on origin/main, with the exact sequence Don should expect to see printed.
