# PROMPT — options lane — 2026-10-16 — the paper options fleet has never traded: move it onto Alpaca paper, and clean up the scream-buy record

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- your sections 84–90 in `HANDOFF_optionsbot.md`;
- `ALPACA_SETUP.md`.

The app fixer is on item 65 (the live-path files `live_cycle.py` and `alpaca_broker.py`'s
equities path, plus the Track tab's hot-stock account). **Do not edit those**; build beside them.

## Why this comes first

Every options strategy here ends on the same rung: a forward paper book, because no options data
exists before 2016. That rung is not running.

- The fleet's broker is `valuation/edge/paper_broker.PaperBroker`, which is the **Tradier
  sandbox**. Tradier closed on 2026-10-08 (DECISIONS), and your own section 90 says the fleet
  "could not paper-trade a pass anyway".
- In the last fleet backup on main (`data_export/fleet_records/`, as of 2026-10-04), **no book
  had recorded a single order**: every stream holds only self-check rows.
- The nightly fleet cycle reports "success", which means only that the door answered 200.

## 1. Measure what the fleet does today

On the service, for each armed book (F-4, F-8, F-10, F-11, F-21, F-22 and the rest):

- what does the cycle do: refuse, and with which code?
- has any book ever placed an order, anywhere?

Report it plainly.

## 2. Alpaca paper for options

Find out, from Alpaca's own documentation and from the paper account itself:

- whether paper accepts option orders, and at what approval level;
- how paper fills options;
- what quotes the free plan gives for options (the "indicative" feed).

Then:

- **Build an Alpaca paper options client in its own module.** Keep the paper-only safety model:
  - the paper host checked exactly;
  - paper keys only;
  - refuse any key that matches a live slot;
  - refuse naked short calls and anything an IRA at Level 2 cannot hold, unless the book's
    declaration says otherwise.
- **Point the fleet at it.**
- **Shared buying power, decided before any order:** the Index paper slot already uses the paper
  account at 100%. Cash-secured puts need cash, so the two cannot share one account.
  - If a second free Alpaca paper account is the answer, give Don the exact steps and the
    Render variable names.
  - Don creates the account and enters the keys himself; no lane handles a key.
- **Fill realism:** record bid, ask and mid at submit beside every fill, and compare paper fills
  with our measured model (O10/O18: real trades pay about two thirds of the quoted half-spread).
  If paper fills are optimistic, label them so on every surface.

## 3. The scream-buy record on the Track tab (display and labels only; nothing is deleted)

- Move the 14 "no contract" alerts into their own collapsed list. They were never trades.
- Label each closed trade's exit source: paper fill, scored from live quotes, or broker refused.
- Headline all real trades marked to market beside the closed-only figure. Losers close fast
  and winners stay open, so closed-only reads worse than the book.
  - The manager's read on 10-16: 35 trades, −9.2% a trade, −$9,581 on $44,986.
- Show the number of distinct names beside the trade count. ABBV is 6 of the 13 open trades,
  and 4 of those are the same Nov $280 call.
- Note that stops are checked once a day, so a stop books past −50%.

## Done

- At least one fleet book has placed and recorded a real **Alpaca paper** option order through
  the scheduled door, verified on the service.
- F-21, F-22, F-4 and F-10 are recording.
- The scream record is relabelled.

All of it on origin/main, with a plain-words summary for Don: which books trade now, and what
he has to do, if anything. Paper only; no real trades.
