# PROMPT — app fixer — 2026-10-17 — item 67: settlement-aware rebalancing, and a read-only fractional-share check for the IRA

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), PAPER_TRACK_CONTRACT.md
§8a, and your items 63–65 first. Finish item 65's part 5 (the seam's evening `end`) first if it
has not landed.

The auditor is reviewing items 64–65 now. **Item 67 changes the live path, so the auditor reviews
it too before any percentage above 0.** Say that in your summary.

Don, in chat on 2026-10-17: *"let's account for waiting for cash to settle now and try again to buy
next day when it is settled. also the whole point of us switching to alpaca from tradier was
because we could use fractional shares so lets check that now."* Don's IRA is open. No live key is
on Render yet.

## 1. Settlement: wait and buy the next day, and never alarm on it

What Alpaca publishes (verify each point yourself; do not take this file's word):

- IRAs are **limited margin**, which *"allows you to avoid certain Federal Reserve Board
  Regulation T settlement periods"*.
- IRAs never borrow, short, or withdraw unsettled funds.
- Alpaca says you *"don't need to wait for trades to settle before using the proceeds to buy more
  equities"*.

So a sell-then-buy rebalance may never wait at all. Build for the case where it does:

- **Within an event, send sells first.** Size buys only to what the broker reports as available
  **without borrowing**: cash or non-marginable buying power, never margin buying power. Decide
  which field from Alpaca's own documentation, and say which.
- **A buy that is refused, or that would exceed what is available, is a SETTLEMENT WAIT, not a
  broker error.**
  - Keep the sells.
  - Record `awaiting_settlement` on the event.
  - Re-send the buys on the **next trading day's** cycles.
  - Alert Don only if the wait outlasts T+1 by a full trading day.
  - Every other broker error still means no orders that cycle, plus an alert.
- **The no-progress ceiling must count trading days, not cycles.** There are now up to five
  scheduled cycles a day plus manual ones, so a one-day settlement wait must not burn it and
  stop a healthy rebalance. That is item 64's false-alarm family. Test it against the real
  schedule.
- **Never create a margin debit.** Add a test that fails if any buy is sized off margin buying
  power.
- Tests must fail on the old code, use recorded responses, and drive the real client class.
  Watch it for real on the paper slot's 2026-10-22 rebalance.

## 2. Fractional shares: check, read-only, without placing anything

Fractional orders already work on the **paper** account: 85 fractional orders were accepted on
2026-10-16. The open question is the **IRA**, and Alpaca's documentation does not say whether
fractional shares work there.

- **Now, with the paper keys:** read `/v2/assets` for every name in the current book (and for the
  10-22 book once it is formed). Report `fractionable` and `tradable` per name.
  - Say what the slot does today with a name that is not fractionable.
  - If that is "the whole slot refuses every cycle", say so plainly and give Don the choice. Do
    not decide it yourself.
- **Once slot 1's IRA keys are on Render** (Don adds them only after the auditor's yes), have
  `/admin/live-slots` read the IRA, read-only:
  - `/v2/account`: status, multiplier, cash, buying power, non-marginable buying power, account
    number shape;
  - `/v2/account/configurations`: `fractional_trading` if the field is present, and the options
    level.
  - Construct no order.
  - In plain words: "fractional trading: enabled / disabled / not reported by the API".
- **If the API does not report it, say so.** The definitive test is a $1 buy by hand in Alpaca's
  app, and that is Don's to make or not. No lane places it.

## Rules

Item 58's rules all stand:

- three events only;
- no loss stops;
- broken input means no orders plus an alert;
- no lane enters a key, sets a percentage or triggers a live order.

## Done

On origin/main, with a plain-words summary for Don:

- whether a rebalance can wait for settlement without a false alarm;
- how many of the book's names are fractionable;
- what the IRA reports, once its keys are in.
