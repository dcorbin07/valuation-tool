# PROMPT — options lane — 2026-10-17 — unblock F-21/F-22, find why the dip screens were not consulted, and re-declare F-4 on the free calendar

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- your sections 95–96;
- commits `0b3db9c`, `0a3ff1d` and `8b93b0b`.

**Don's answers (chat, 2026-10-17):**

1. **Remedy (b) for the broken chain: yes.**
   - A re-anchored stream continues the sequence at `high_water + 1`, with `prev_hash` = the
     current declaration hash.
   - Build it in the write door, so the high-water guard and the tamper evidence both still hold.
   - Test it through the real write path, including the next ordinary write after the re-anchor,
     because that is where your first attempt failed.
   - It may only re-anchor a break at row 0 on a stream with no fills or closes. It must leave a
     dated, visible record that it happened.
   - Apply it to F-21 and F-22 only.
   - **Add a guard so this cannot happen again:** an amendment to a declaration whose stream
     already has a first record must be refused, or must force the re-anchor path visibly.
2. **Find out why `dip_healthy` and `dip_rejects` were NOT CONSULTED** on the 2026-10-17 cycle, and
   why F-21's entry population has only two valid days. Fix it if it is a defect; report it if it
   is a data limit.
   - Also report on `RULE_ARMED_NEVER_FIRES` for F-8 and F-11 at 32 observations: is the rule
     unable to qualify anyone, or is the market quiet?
3. **F-4 is re-declared at 25 delta on the free forward calendar. F-10 stays retired.**
   - The short-side tenor comparison favours 30 DTE in both quadrants, and F-10 clears the crash
     gate by only 2.3%.
   - Declare F-4 ALONE through the harness's own route:
     - 25 delta, its declared 30 DTE;
     - the Yahoo forward calendar you measured, with at least the 7-day buffer your drift
       measurement implies;
     - a name with no forward date is REFUSED, never treated as event-free.
   - Carry `FLEET_RETIREMENTS.md`'s crash-gate figures and §87b's 2020 result in the declaration.
4. **EARNINGS-CSP stays stopped.** The tenor-matched reading (0.7358, its whole interval above the
   bar) says that even a real effect would be too small for that design to see. Do not re-measure
   it now.

Also report:

- whether the fleet's paper keys are present on the service;
- whether the out-of-hours cycle has now attempted an option order, and what Alpaca answered.

## Rules

Paper only; no real trades. Done means on origin/main, with a plain-words summary for Don: which
books can now enter, and when the first fill could come.
