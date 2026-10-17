# PROMPT — auditor — after item 65 lands — third review of the §8 live path

**Start only once item 65 is on origin/main.** If it is not, stop and say so.

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- both of your reviews (`AUDITOR_REVIEW_live_path.md` and
  `AUDITOR_REREVIEW_live_path_2026-10-16.md`);
- item 64's and item 65's commits.

Verify against the code and the tests, and reproduce your cases rather than reading commit
messages.

1. **Your residual route:** state lost, `/v2/orders` unreadable, `/v2/positions` readable. Does it
   now refuse, end to end through `run_cycle`, with the real client class? Look for any other
   empty-scope route the same derivation could reach.
2. **Item 64's changes, which you have not reviewed:**
   - the per-attempt order-id suffix;
   - the two counters (`send_seq` never resets; the no-progress ceiling resets on holdings
     progress);
   - the `_rejection_reason` reader;
   - the new schedule.

   Could any of them send an order a broken input should have stopped? Could a remainder re-send
   double a position?
3. **Item 65's wash-trade handling:** the cancel must be confirmed before the opposite side is
   sent, and an unconfirmed cancel must not trade.
4. **Your notes:** the id pin when the broker returns no id, the `HOLDERS` list, and pagination.
5. Restate your eight questions' pass or fail as of today.

## Verdict

One of two, stated in the first line:

- **LIVE KEYS MAY BE ENTERED AT 0%**; or
- **NOT YET**, with the remaining blockers named.

Entering keys at 0% sends nothing; going live is a separate later step for Don. This is a review
only: change no source file, and land the review on main.
