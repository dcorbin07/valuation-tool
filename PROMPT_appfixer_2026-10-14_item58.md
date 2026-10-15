# PROMPT — app fixer — 2026-10-14 — item 58: Alpaca paper for every paper book, and the signed §8 live path on Alpaca, shipping at 0%

Run this **after item 57 lands**. First read these:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy
  may be out of date), the 2026-10-14 Alpaca entry;
- `PAPER_TRACK_CONTRACT.md` §8, the real-money live path Don signed on 2026-09-02 and restored
  on 2026-09-15;
- `LIVE_PILOT_BLOCKED.md`, your own two refusals and the whole-share measurement;
- `ALPACA_SETUP.md`.

## Why

1. **Paper.** Every paper book trades through `valuation/edge/paper_broker.py`, the Tradier sandbox
   client, whose quotes are about 15 minutes late. That covers the fleet books, the options paper
   book (`scream_log.py`), the paper-trade door in `app_saas.py`, and the fleet self-check.
   Alpaca's paper fills are matched against the real-time NBBO.
2. **Live.** §8 authorizes a percentage-of-equity real-money path, but it was never built.
   - The first refusal was that §8 was not on main.
   - The second was the vendor: Tradier accepts whole shares only, so at $5,000 of book 51 of 68
     names got zero shares, and the minimum full book was $128,562.
   - Alpaca allows fractional shares, which is why Don moved.
   - **Don's instruction (chat, 2026-10-14): build it on Alpaca, fully disciplined, and ship it
     at 0% until he switches it on.**

## Facts to verify from Alpaca's own docs, never from here

- **Paper fills:** marketable orders fill at the touch. Non-marketable limits fill only when the
  market reaches them, with no queue position and no price improvement. Size is not checked
  against liquidity, and 10% of fills are randomly partial. Paper charges no regulatory fees
  and pays **no dividends**.
- **Data:** the Basic plan is IEX-only for stocks and an indicative feed for options. The full
  feed is $99/month.
- **API:** identical between paper and live; only the host and the keys differ. The keys
  identify the account, so no account number is needed.
- **Fractional orders:** check which order types and times-in-force allow them. §8 requires
  **limit orders only**; if fractional limit orders are not allowed, say so before building
  around it.
- **IRAs:** check whether Don's live account type allows fractional shares, and what cash-account
  settlement means for a rebalance that sells and then buys.

## Build

### A. Alpaca paper broker (paper books)

1. **Same safety model as `PaperBroker`, enforced in code.**
   - The trading host must be exactly `paper-api.alpaca.markets`, parsed and compared.
   - Keys come from `ALPACA_PAPER_KEY_ID` and `ALPACA_PAPER_SECRET_KEY`. Construction refuses if
     they are missing, or if they equal any live slot's keys.
   - The account endpoint must confirm a paper account (find the field; do not assume a prefix).
2. **The same interface the books call**, so they switch by configuration.
   - Every fill records the quote feed it was priced against.
   - The fill-assumption sentence travels in the payload.
3. **Switch over before the first fleet fill.** No fleet book has filled yet.
   - Keep the Tradier client until the Alpaca self-check passes on the service.
   - Record the switch as a dated event on each book.
   - If a declaration's frozen wording names the broker, use the harness's amendment route.
4. **Measure the feed gap on the first 30 paper fills**: recorded mid against fill price.
5. **Dividends:** any paper book holding shares through an ex-date adds them from a named
   source, or states the omission.
6. **`ALPACA_SETUP.md`:** change its key names to the ones above, so the two documents never
   disagree.

### B. The §8 live path: fully disciplined buy-and-hold of the Valquo Index

**Don's ruling (chat, 2026-10-14), to be followed exactly:**

> "I want it to be fully disciplined. Buy and hold and pilot at whatever percentage of the
> account is authorized and does that math per stock. Buying and selling only at quarterly
> rebalances and when that percentage changes. Otherwise no other restrictions because that's
> the whole point. If not, then we just have extra room for bugs, errors, and complications"

**The whole behaviour.** Each stock's target value is the slot's percentage × the account's
current equity × the stock's weight in the Index book in force. The slot buys or sells
fractional shares to reach that target, and acts on exactly three events:

1. **A quarterly rebalance**, meaning a new rebalance event on the bound Index record.
2. **A change in the slot's percentage.**
   - 0 to X is the first buy-in, executed at the next cycle.
   - X to Y resizes the slot.
   - X to 0 is a target of zero, so the slot sells what it holds.
3. **Nothing else.**
   - No loss stops, no drawdown rule, no drift rebalancing, no trading between events.
   - Dividends stay as cash until the next event.

**Execution mechanics** (these are part of doing the trades, not extra rules):

- Orders are limit orders, per §8.
- An order unfilled or partly filled by the close is re-priced and re-sent each following cycle
  until that event's targets are met. Log each attempt.
- The slot keeps its own record of what it bought, and only ever trades those positions. Don's
  other holdings in the account are never touched.

**The only switch besides the percentage:** `LIVE_PILOT_ENABLED=0` pauses every slot without
selling anything, and holdings stay as they are. Explain clearly in the status how pausing
differs from setting a percentage to 0.

**If anything is broken or wrong: don't trade, alert Don (Don, same day).** Before sending a
cycle's orders for a slot, check the inputs and the arithmetic. If any check fails, that slot
sends **no** orders that cycle, alerts Don through the project's existing alert route with the
reason, and checks again next cycle. An error never causes a sale and never changes holdings.

Treat at least these as broken:

- the Index book or its weights cannot be read, or fail conformance;
- the book is stale against its own rebalance date;
- a price is missing or stale for any name the cycle would trade;
- account equity or positions cannot be read;
- the orders do not reproduce the per-stock math, or differ from the paper book's math beyond a
  stated tolerance;
- an order would touch a position the slot did not buy;
- the slot's own record of holdings disagrees with the broker's;
- any broker API error.

These checks are about the software, never about performance.

**Removed from §8, by Don's instruction:**

- the per-account `MAX_DAILY_LOSS_PCT` and `MAX_DRAWDOWN_PCT`, together with their
  refuse-to-arm rule;
- every freeze or limit beyond the above.

Build nothing that halts, trims or freezes on performance.

**Many accounts, discovered automatically (Don, same day).**

- **The slot variables:**
  - `ALPACA_ACCOUNT_<n>_KEY_ID`
  - `ALPACA_ACCOUNT_<n>_SECRET_KEY`
  - `ALPACA_ACCOUNT_<n>_LIVE_PCT` (0–100)
  - `ALPACA_ACCOUNT_<n>_HOLDER` (a plain label)
- **Discovery.** Each cycle picks up every `n` that has both keys. Slot 1 is Don's own account.
- **Defaults.** A new slot starts at 0% even if its percentage variable is missing.
- **Holder authorization.** A slot other than 1 stays at 0% unless `PAPER_TRACK_CONTRACT.md`
  carries that holder's own signed authorization for that slot number (§8's family-slot rule),
  read the way `index_track.gate_state()` reads the contract.
- **Isolation.** Refuse two slots that share a key or resolve to the same account. One slot's
  failure never stops another.

**At 0%, which is how every slot ships:**

- the slot computes the orders it would place, logs them, and diffs them against the paper book.
  This is §8's dry-run parity, and it is how Don gets comfortable;
- it never sends an order;
- no live client is constructed for a slot unless its keys exist, `LIVE_PILOT_ENABLED=1`, its
  percentage is above 0, and (for slots other than 1) the holder's authorization row exists.

**Separation:**

- The live client is a different code path from the paper broker and accepts only the live
  host.
- No paper book can reach it, and nothing in tests or CI constructs it with real keys.
- It is triggered only by the service's own scheduled cycle.
- A lane never sets a percentage, never enters a key, and never triggers a live order.
- The owner-only status shows every slot: holder, percentage, armed or not, its next event, and
  what it would trade.

**The §8 amendment.** Add a dated §8a to the contract with Don's ruling quoted verbatim. It
records:

- the execution container is Alpaca instead of Tradier;
- fractional shares are allowed;
- the environment names above;
- the three-event behaviour;
- loss stops removed by Don's instruction;
- what pausing means and what 0% means.

**The auditor review.** §8 requires an auditor design review to land **before any live key is
entered**. Write it for the auditor lane as `PROMPT_auditor_live_path.md` in the main folder. Its
questions:

- does the slot trade only on the three events;
- does the per-stock math match the paper book;
- can a paper book ever reach the live client;
- can a lane trigger a live order;
- does a missing or bad environment value ever result in an order rather than no order.

## Don's steps (give him exact words, one at a time)

- **Now:** the two paper keys go on Render only, in the `valuation-tool` service's
  **Environment**. No GitHub secret is needed, because every workflow asks the service to do the
  work; confirm that is still true.
- **Already set by Don:** `LIVE_PILOT_ENABLED=0`. He may also have set `ALPACA_LIVE_PCT=0` from
  an earlier draft. That name is retired: tell him to delete it and add
  `ALPACA_ACCOUNT_1_LIVE_PCT=0`. Read no alias for the old name.
- **Later, after the auditor review:** slot 1's two live keys go on Render only, as
  `ALPACA_ACCOUNT_1_KEY_ID` and `ALPACA_ACCOUNT_1_SECRET_KEY`. The same pattern serves slot 2, 3
  and so on. Live keys never go on GitHub or in a local `.env`, and no lane ever sees them.

## Done

- Tests that fail on:
  - a live host in a paper book;
  - a missing key;
  - an order on a day with no event;
  - an order at 0%;
  - an order touching a position the slot did not buy;
  - a pause that sells;
  - any broken input that still produces an order rather than no order plus an alert.
- The full suite green.
- One real Alpaca **paper** fill through the self-check on the service.
- One dry-run cycle of slot 1 at 0% showing the orders it would place.

Done means on origin/main, with a plain-words summary for Don.
