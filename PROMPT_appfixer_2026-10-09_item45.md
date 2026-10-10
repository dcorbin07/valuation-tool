# PROMPT — app fixer — 2026-10-09 — item 45: Tradier is gone; get off it

Read `DECISIONS.md` first (2026-10-08 ruling on Tradier). This REPLACES the earlier item 45 — the
Tradier seam test is cancelled (Don will not fund Tradier again; the pending workflow was moved to
`data/pending_workflows/cancelled/` and must not be installed).

## Measured fact

Don withdrew his funds and Tradier deactivated the brokerage account. The live feed died with it:
intraday run 37853898863 (2026-10-08 22:31 UTC) printed `scored 0 of 150 names — nothing scored —
not ingesting` and exited 1, and /api/signals is frozen at run_time 2026-10-08 00:20. Nothing
alerted (`no DISCORD_WEBHOOK_URL`).

## 1. Inventory, measured not assumed

List every path that uses `TRADIER_TOKEN` (live) or `TRADIER_PAPER_TOKEN` (sandbox): the intraday
scan, the options record's scoring/settling (daily-doors score-alerts), `broker_universe`,
`broker_fundamentals`, recap/notify/surfaces, the paper-track engine and the S3-I1 fleet books.
For each: what it does, whether it is broken now, and what the user sees. Probe both tokens'
status from where they live (status code only, no token ever printed or handled). Confirm the bound
Index record does NOT depend on Tradier (it should not: index_mark prices via screener/prices.py).

## 2. Stop the silent failure today, with what already exists

`intraday/providers.py` already has `FreeProvider` (yfinance, delayed), chosen only when the token
is empty, so a dead token means zero names. Make a Tradier auth failure fall back to the free
provider for the Signals scan, label the feed's source and delay on the page and in the payload,
and make the run fail loudly when BOTH sources produce nothing. Do the same for anything else in
the inventory that has a free fallback. Where something has NO honest fallback (e.g. options
quotes needed to settle a live alert), stop it explicitly and say so on the surface rather than
recording zeros or gaps silently.

## 3. A replacement source, measured before anything depends on it

Robinhood is NOT an option: it has no official market-data API for equities or options (its
official developer API is crypto-only), and the unofficial route needs Don's login, which this
project never stores. The candidate to measure is Alpaca's free tier (real-time IEX stock data and
the indicative options feed; paper trading). Write down exactly what Don must do — create a free
Alpaca account and API key himself, and enter it as a GitHub secret and a Render environment
variable himself, under the names you specify; no lane ever sees a key — and then, once he has,
measure the seam the way you measured FMP (bars, option chains with IV/greeks, coverage on the
same 222-name sample, rate limits, and what "indicative" means for fill realism). Nothing is
switched to Alpaca until Don has seen the numbers.

## 4. The fleet paper books

If the sandbox token is dead, the S3-I1 fleet's declared books cannot place paper fills. Do NOT
switch their broker — a book's fill source is part of its declared rules. Report what is dead and
what changing it would mean, for Don to decide.

Also still owed from the earlier item 45: the append-only writer's transient-error retry, and the
intraday delivery re-measurement on 2026-10-14.

Done means on origin/main, verified live, with a plain-words summary for Don.
