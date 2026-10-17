# PROMPT — auditor — 2026-10-16 — re-review the §8 live path after item 63

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), your own review
`AUDITOR_REVIEW_live_path.md` (now on main), and item 63's commits `2344529` and `502dc94` first.

Your verdict was "do not enter a live key yet", on two blockers plus failed questions 2 and 7.
Item 63 says it closed all of them. **Verify each one against the code and the tests, not the
commit message.** Reproduce your original failing cases where you can.

1. **Blocker 1:** `run_slot` can place an order through the **real** paper broker class. Check the
   derived method-presence test, and whether it would catch the next divergence. Check the
   `_LiveClient` has-no-`quotes` handling.
2. **Blocker 2:** no duplicate buy-in is reachable through an empty or stale record, a failed
   write, or an unreadable position list. Check that the reverse-direction preflight is scoped
   correctly, so it cannot refuse on Don's own unrelated holdings and cannot miss the slot's own
   positions.
3. **Question 2:** parity blocks a live send on mismatch and on absence, diffs target weights, and
   cannot brick a live slot that arms after the paper slot closes an event.
4. **Question 7:** an unreadable position list refuses.
5. **The new pieces:** account-id pinning, the 5-cycle retry ceiling, the `valquo-<slot>-`
   order-id namespace, and full-page refusal. Could any of them send an order a broken input
   should have stopped?
6. **Restate your eight original questions'** pass or fail as of today.

## Verdict

One of two, stated in the first line:

- **LIVE KEYS MAY BE ENTERED AT 0%**; or
- **NOT YET**, with the remaining blockers named.

Entering keys at 0% sends nothing; going live is a separate later step for Don. Review only:
change no source file. Land the review on main.
