# PROMPT — app fixer — 2026-10-23 evening — item 80 (URGENT, the rebalance is waiting on it): the rebalance door refuses EVERY book

**Don is mid-rebalance right now. Fix it, land it, and confirm it is deployed on Render as fast as
safely possible.** Don authorises landing tonight; the usual "no landing Friday evening" rule
existed to protect this send, and this fix is what the send needs.

Do not edit `DECISIONS.md`.

## The defect, measured 2026-10-23 ~8:45pm ET

Don ran, with a book that passes every check (81 names, largest weight 1.96%, conformance
`conforms: true`, as of 2026-10-22):

```
python -m scripts.seed_track --rebalance data/valquo_index.json --rebalance-date 2026-10-22 --pull --send
```

and got:

```
HTTP 422  the rebalance is not the contract-bound Index: conformance refused
```

**The cause is a key mismatch.** `index_mark.append_rebalance` calls
`valquo_index.conformance(...)` and then tests:

```
(c or {}).get("ok")
```

But `conformance()` returns `{"conforms": ..., "why_not": [...]}`. It has no `"ok"` and no
`"reason"` key. So the door refuses every book, conforming or not, and falls back to the generic
reason text. The door's tests must have injected a conformance function that returns `ok`, which is
why they passed.

## The fix

1. **Make the door read `conforms`.** Take the reason from `why_not`, joined into one string.
2. **Add a test that uses the REAL `valquo_index.conformance`, not an injected one.**
   - It must fail on today's code.
   - A conforming book must be accepted.
   - A non-conforming book must still be refused, and its reason must name `why_not`.
3. **Check the seed door and every other caller of `conformance()`** for the same key mismatch,
   and fix any you find.
4. **Change nothing else**, and do not touch the other refusals.

## Done

1. Land on origin/main and confirm the Render deploy is live: the service's commit, or a health
   endpoint showing the new code.
2. Then tell Don, in one line, that he can re-run the same `--send` command.

The token is already set in his PowerShell window.

No key, no percentage, no `.github` change.
