# PROMPT — app fixer — 2026-10-14 — item 59: Alpaca market data as the primary price source wherever it measures better

Run this after item 58 (the Alpaca broker and the paper keys). Read
`C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy may
be out of date) and `ALPACA_SETUP.md` first.

## The ruling

Don's ruling (chat, 2026-10-14): **Alpaca becomes the primary price source wherever it is at
least as good, with the current routes as fallbacks.** Today nothing reads Alpaca. Prices come
from three places:

- `screener/prices.py`: Stooq, then yfinance. This prices the bound Index record.
- yfinance for the valuation page and the free-route scan.
- whatever now feeds intraday quotes and option chains. Find out; Tradier is closed.

## Measure first

Run `ALPACA_SETUP.md`'s seam measurement on its stated 222-name sample.

**Where it runs.** The keys exist only on Render, so the measurement runs on the service, behind
an owner or admin door. Lanes test with recorded fixtures and never see a key.

**Daily closes.** Compare against the recorded series and against yfinance on three things:
- agreement rate, with the worst disagreements by name;
- whether closes are as-traded or adjusted (state the `adjustment` parameter used);
- whether the consolidated (SIP) close is reachable on the free plan, which is expected once
  data is more than 15 minutes old. Verify that in the docs.

**Coverage, as a share of the hot-list universe, with gaps named.**
- Coverage of the current Index's 85 names.
- Whether Texas Stock Exchange listings are covered. ET has been unpriced on the current route
  since 2026-10-05.
- Whether OTC or foreign names are covered.

**Rate limits** (200 per minute on the free plan) against the scan's needs. Use the
multi-symbol bars and snapshots endpoints, not one call per name.

**Intraday quotes.** Free real-time is IEX only. Measure how far IEX quotes sit from the fills
item 58 records before Signals relies on them.

**Options.** The free feed is indicative. It is fine for scoring an alert and not adequate for
settling one; keep that line.

## Then switch, where the measurement supports it

Each switch has a fallback, and every recorded number names its source.

1. **The Index daily row.**
   - Alpaca daily closes become primary, with Stooq then yfinance as fallbacks.
   - **This is the one series that cannot be rebuilt.** Inside a segment, base and mark must
     always come from the same vendor.
   - Cut over at the 2026-10-22 rebalance if ready, so the new segment starts on Alpaca.
     Otherwise cut over on a later date, with the measured seam recorded on that date.
   - Add a dated note to `PAPER_TRACK_CONTRACT.md` naming the source and the date.
   - This is not a vintage event: the rules are unchanged, only the price vendor.
2. **Scan prices and momentum inputs, beta, and the valuation page's current price.** Use Alpaca
   bars and snapshots. That also takes load off Yahoo; test whether it ends the `info` throttling
   item 57 found.
3. **Paper-book quotes and Signals intraday.** Use Alpaca, with the IEX caveat shown.

**What stays where it is:** company fundamentals, descriptions and earnings dates. Alpaca does
not carry financial statements; those stay on Yahoo with item 57's SEC fallback. Confirm what
Alpaca does and does not carry from its docs, and say so.

## Done

- Each switch backed by its measurement.
- Tests that fail on the old route.
- The full suite green, and verified live.

Done means on origin/main, with a plain-words summary for Don of what is now on Alpaca, what is
not, and why.
