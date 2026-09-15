# REAL-MONEY SCALE-UP PLAYBOOK

**For Don. Written 2026-09-01, revised 2026-09-02 on Don's ruling: percentage-of-equity,
per account, set in the environment — no dollar caps and no numbers hard-coded in files.**

This is the file to open when you want to (A) raise the percentage or (B) put another
account on the live path. Both are gate events with steps, and the steps exist because the
project's own history says bugs — not markets — are what hurt.

Governing rule, carried from the charter: **every increase is a signed amendment to
`PAPER_TRACK_CONTRACT.md` (§8.1, §8.2, …), written BEFORE the environment changes, never
after.** A percentage raised after seeing a good month is a percentage chosen on the outcome.

---

## HOW THE PERCENTAGE MODEL WORKS (read once)

Every account slot in the environment carries its own live setting:

```
TRADIER_ACCOUNT_<n>_LIVE_PCT          share of THAT account's equity the book may hold
TRADIER_ACCOUNT_<n>_MAX_DAILY_LOSS_PCT   loss stop, % of the book, one session
TRADIER_ACCOUNT_<n>_MAX_DRAWDOWN_PCT     loss stop, % of the book, from its high-water mark
LIVE_PILOT_ENABLED                    global kill switch: 0 = no orders anywhere, ever
LIVE_PILOT_DRYRUN_SESSIONS            sessions of logged parity required before any real order
```

- **`LIVE_PCT` is a share of the account's total equity** (cash + positions, read live from
  Tradier balances at every cycle — never a stored number). At each rebalance the target book
  size is `LIVE_PCT × current equity`. The book **grows with the account and shrinks with it.**
  That is the safeguard: a drawdown automatically reduces what is at risk.
- **Cash outside the percentage is never touched.** Sells are never blocked by it; buys never
  exceed it.
- **`0` or absent = alerts-only for that slot.** Every slot ships at 0. Nothing goes live by
  default, and family slots stay at 0 unless Part B has been executed for that person.
- **Fail closed, not open:** a slot with `LIVE_PCT > 0` but a missing loss stop, or a value
  outside 0–100, or a non-number, **refuses to arm** and says so loudly. The code carries no
  default risk numbers of its own — you set every one, on Render, yourself.
- **The dry-run gate is per account:** a slot logs what it *would* trade for
  `LIVE_PILOT_DRYRUN_SESSIONS` sessions and diffs it against the paper book before its first
  real order. A new account restarts that clock.

---

## A. RAISING THE PERCENTAGE

### The steps, in order — do not skip one
1. **Read the evidence first, write the number second.** Open the live record (hash-chained,
   on the Render disk, exported weekly) and confirm ALL of:
   - Zero orders that exceeded the percentage, ever.
   - Zero orders the kill switch or a loss stop had to catch *unexpectedly* (a stop that fired
     on a real drawdown is fine; a stop that fired on a bug is a blocker).
   - Zero orders that did not match the paper book's intended order for that day (parity
     held *through* the live period, not just before it).
   - Measured live slippage recorded and compared to the 33 bps one-way assumption.
   If any line fails, you do not raise anything; you file the defect.
2. **Write the amendment.** Append to `PAPER_TRACK_CONTRACT.md`:
   ```
   ### §8.1 PERCENTAGE RAISED — SIGNED <date>
   Account <label>: LIVE_PCT <old>% -> <new>%. Evidence: <N> live sessions, 0 breaches,
   0 bug-stops, parity held, measured slippage <x> bps vs 33 assumed.
   ```
3. **Set the new `LIVE_PCT` on Render** for that slot. You do this, nobody else. No code
   change, no push — the environment is the only place the number lives.
4. Fund the account as you see fit; the book resizes at the next cycle on its own.

### Suggested staging (a discipline, not a schedule)
Start at the percentage that makes `LIVE_PCT × equity` an amount you are fully comfortable
losing. Then:
- **First raise:** after ≥ 40 live sessions (~2 months) clean on every line above.
- **Past 50% of any account:** not before the **operational gate, 2027-02-13** — the first
  scheduled judgment on whether the forward track is behaving.
- **100%:** treat as a new decision, not a step. Re-read the −29% backtest drawdown and
  assume a concentrated live book will draw down deeper than the backtest did.
- **Never** raise in the same week a raise was just made, and **never** on the strength of a
  good month. Raise on clean mechanics + elapsed evidence only.

### What never changes when the percentage changes
Equity-only. Limit orders only. Kill switch present. Loss stops present for every armed slot.
The forward track, the 2027 gate and the 2031 verdict are untouched — the live path is a
fills experiment, not the verdict.

---

## B. PUTTING ANOTHER ACCOUNT ON THE LIVE PATH

**Read this part twice. It is a different category of decision from Part A.**
Trading your own money is your business. Automatically trading someone else's — even family,
even free, even with their blessing — can fall under investment-adviser rules depending on
your state and how it's structured. I am not a lawyer and this is not legal advice: **before
executing Part B for anyone, spend one hour with an actual securities attorney or your
state's securities regulator FAQ.** That hour is cheaper than any outcome it prevents.

### The clean shape (what the slots do at LIVE_PCT = 0)
Family members get **alerts** — the same digest you act on — and place their own trades in
their own accounts. No one manages anyone's money. **This is the default and should stay
the default for most people.**

### If, after the legal check, you still want a family slot live
1. **Their written authorization first.** A dated, signed note from the account holder: their
   account only, their percentage, their understanding that this is an unproven backtest, and
   that they can revoke by telling you. Keep it. This is their §8.
2. **They enter their own live token on Render.** Not you, not me. The person whose money it
   is holds the credential.
3. **Set their `LIVE_PCT`, `MAX_DAILY_LOSS_PCT` and `MAX_DRAWDOWN_PCT`** — the slot refuses
   to arm without all three.
4. **Their percentage starts low regardless of yours**, and their slot runs its own dry-run
   parity clock first. Your clean record does not transfer to their account's plumbing.
5. **Amend the contract** with a §8.x row naming the account label, percentage and date.
6. **One account at a time.** Never add two in the same amendment.

---

## C. THE STOP CONDITIONS — when you go DOWN, not up
Set `LIVE_PILOT_ENABLED=0` (halts every slot at once), flatten manually if needed, and do not
resume until the cause is filed, if ANY of these happen:
- Any order that exceeded a slot's percentage or that the paper book did not intend.
- A loss stop firing for a reason you cannot explain from the market alone.
- The forward track's operational gate (2027-02-13) reads UNSUPPORTED.
- Live slippage measured at more than 2x the 33 bps assumption for a full month.
- You find yourself wanting to raise the percentage because of a good run. That feeling is the
  signal to wait, not to act.

---

*Companion to `PAPER_TRACK_CONTRACT.md` §8. If this file and the contract disagree, the
contract wins. If this file and your gut disagree, re-read section C.*
