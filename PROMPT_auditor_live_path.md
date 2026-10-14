# PROMPT — auditor — the §8 real-money live path on Alpaca, shipping at 0%

**§8 of `PAPER_TRACK_CONTRACT.md` requires your design review to land BEFORE any live key is
entered.** No live key exists yet. Your review is the gate, not a formality: if you find one of
the five questions below answered wrongly, say so and the keys do not go on.

> **WHERE THIS FILE LIVES.** The item-58 brief asked for it in the main folder
> (`C:\Users\donni\Downloads\valuation-tool\`). A lane working in a git worktree cannot write
> there, so it is committed at the repository root instead and reaches the main folder with the
> next `git merge --ff-only origin/main`. If the manager prefers it alongside the other
> `PROMPT_*` files and off GitHub, copy it across and delete the tracked copy.

Read first, in this order:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — a worktree's copy
  may be stale), the two 2026-10-14 Alpaca entries;
- `PAPER_TRACK_CONTRACT.md` **§8** (signed 2026-09-02, restored 2026-09-15) and **§8a**
  (the 2026-10-14 amendment, which quotes Don's instruction verbatim);
- `LIVE_PILOT_BLOCKED.md` — the two prior refusals and the whole-share measurement that moved
  the vendor;
- the code: `valuation/edge/live_slots.py`, `valuation/edge/alpaca_broker.py`,
  `tests/test_item58.py`.

## What was built

A percentage-of-equity buy-and-hold of the Valquo Index, per numbered account slot, on Alpaca,
with fractional shares. Each stock's target value is
`slot_pct × account_equity × weight_in_the_book_in_force`. A slot acts on **three events only**:
a new rebalance event on the bound Index record, a change in its own percentage, and nothing
else. §8's per-account loss stops are **removed by Don's instruction**, recorded in §8a.

**Every slot ships at 0%.** At 0% the cycle computes the orders it would place, logs them, diffs
them against the paper book, and constructs **no live client at all**.

## Your five questions

Answer each from the code, not from this prompt and not from the docstrings. A docstring
claiming a property is exactly the thing worth checking.

1. **Does a slot trade only on the three events?** `live_slots.event_for`. Look for any other
   read that can reach an order — in particular anything that reads a return, a price history,
   a drawdown, or any date other than the book's `formed_on` and the slot's own percentage.
2. **Does the per-stock math match the paper book's?** `live_slots.targets` and
   `live_slots.order_plan`. The brief requires the live orders to reproduce the paper book's
   arithmetic within a stated tolerance, and a mismatch to produce **no orders plus an alert**.
   Check that the tolerance is stated and that the failure direction is "no orders".
   **This is the weakest part of the build and you should treat it as such:** the paper-side
   comparison is a dry-run diff rather than two implementations of one function, so satisfy
   yourself that a divergence would actually be caught.
3. **Can a paper book ever reach the live client?** `alpaca_broker.AlpacaPaperBroker` accepts
   only `paper-api.alpaca.markets`; `live_slots._LiveClient` accepts only `api.alpaca.markets`;
   they are separate classes rather than one class with a flag. Check that no module imports
   `live_slots` (a test asserts it through the AST, after a first version was tripped by a
   comment), and that no host can be threaded through from a caller.
4. **Can a lane trigger a live order?** The only trigger is meant to be the service's own
   scheduled cycle. Check that no CLI, script, test or admin door constructs `_LiveClient`, and
   that the keys are reachable only from the service's environment — `config.py` deliberately
   holds the PAPER keys and **not** the live ones, so that nothing holding a config object can
   obtain a live credential.
5. **Does a missing or bad environment value ever result in an order rather than no order?**
   Walk every environment read in `live_slots`: a missing percentage (0), a non-numeric one
   (refuse and alert — **not** 0, because reading a typo as 0 would SELL the book), a missing
   key pair (not discovered), `LIVE_PILOT_ENABLED` set to anything but `1` (pause), a slot other
   than 1 with no signed authorization row, and two slots sharing a credential.

## Two things the build could not settle — please form a view

1. **There is no API way to confirm a paper account.** `GET /v2/account` carries no `is_paper`,
   no `account_type` and no environment field. The only hint in Alpaca's docs is an example
   account number rendered `PALPACA_123` — a prefix, which the brief explicitly forbade relying
   on. So the **host** carries the whole guarantee and the account number's shape is recorded as
   corroboration only. **Is the host check sufficient on its own?**
2. **Alpaca's docs do not say whether fractional shares work in an IRA, nor what settlement
   means for a rebalance that sells and then buys.** They record only that IRA accounts run
   *"limited margin (1x margin)"*. The design assumes neither: a buy rejected for buying power
   is a broker error → no orders for that slot that cycle plus an alert, and the
   re-send-next-cycle behaviour resolves it once cash settles. **Is that the right handling, and
   should Don's first real rebalance be watched for it specifically?**

## What is NOT in scope

Performance, strategy, the Index construction, the forward track, the 2027 gate and the 2031
verdict. §8's own sentence governs: *"This is a fills experiment, not a verdict."* You are
reviewing whether the software can place an order it should not.

## Done

A written review in the main folder, with a verdict on each of the five questions and a view on
the two open facts. If your verdict is that it is safe to proceed, say so explicitly — Don reads
that line before he enters a key.
