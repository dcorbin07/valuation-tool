# Options Put-Credit-Spread Backtest (free, honest, index-ETF version)

Validates the CONCEPT behind your deployed options bot: does selling 20-delta
$5-wide put credit spreads, managed with your exact rules (50% profit / 2x stop
/ 21-DTE exit), actually have a historical edge after costs — including through
the 2020 crash and 2022 bear?

## Why index ETFs only (the honest constraint)
Your edge is the variance risk premium — the gap between the IMPLIED vol you
sell at and the REALIZED vol that follows. A faithful backtest MUST use real
historical implied vol. The only FREE source of that is the VIX family:
  - VIX  -> SPY
  - VXN  -> QQQ
  - RVX  -> IWM
So this tests the concept on the index ETFs faithfully. It does NOT test your
single-stock names (their historical implied vol isn't free). The logic: if
index put-spread selling doesn't clear costs here, your single-stock version
(wider spreads, higher costs, more blow-up risk) won't either. A pass is
NECESSARY but not SUFFICIENT for the stock names.

Two features make this err AGAINST the strategy (conservative, good):
  1. VIX understates OTM-put premium (ignores put skew) -> our credit is low.
  2. Stop gap-through: a 2x stop doesn't fill at 2x in a vol spike; we exit at
     the real marked price, which can be worse. Naive backtests cap the loss at
     the stop and lie about exactly the tail that matters.
Plus conservative slippage (sell below mid, buy above mid) + commissions.

## Run it (needs internet to stooq.com — your machine or the Oracle box)
```bash
pip install requests
python run_options_backtest.py --etf SPY --start 2018-01-01 --end 2025-12-31
python run_options_backtest.py --etf QQQ
python run_options_backtest.py --etf IWM
```

Output: total return, Sharpe, max drawdown, win rate, avg win/loss, worst trade,
exit breakdown, and an explicit COVID-crash and 2022-bear stress breakdown — vs.
what the index itself did. Saves a full results JSON.

## Files
- `bs_pricing.py`     — Black-Scholes put pricing + delta (finds the 20-delta strike)
- `backtest_engine.py`— day-by-day simulation of your exact strategy + exits
- `run_options_backtest.py` — fetches free data, runs it, prints the report

## What it can't tell you
- Whether your specific STOCK picks work (index proxy only).
- It's a concept test, not an execution test — your live SIM on Oracle is the
  execution validator. Don't correlate this backtest curve against the live-SIM
  curves; they're different timeframes (the correlation tracker warns on this).

## Caveats baked in (read before trusting numbers)
- European BS pricing on American ETF options (small error for OTM puts exited
  before deep ITM).
- Expiration approximated as a calendar date target_dte out (not exact monthly
  expiries).
- Dividend yield is a rough constant (~1.3%); rates from ^IRX as a proxy.
- These approximations are minor next to the IV-source and gap-through choices,
  which are the things that actually decide whether the test is honest.
