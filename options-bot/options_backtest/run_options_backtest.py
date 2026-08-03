#!/usr/bin/env python3
"""
Run the options put-credit-spread backtest on the index ETFs using FREE data.

Fetches (no paid subscription, no API key):
  - ETF daily prices from Stooq (SPY, QQQ, IWM)
  - Implied vol from the VIX family via Stooq (^VIX, ^VXN, ^RVX)
  - Risk-free rate from the 3-month T-bill (^IRX) via Stooq, used both as the
    discount rate in the pricing and as the risk-free leg of the Sharpe ratio

Then simulates the deployed strategy (20-delta, $5-wide, 35 DTE, 50%/2x/21-DTE
exits, 2% vol-scaled sizing with the bot's contract/concurrency/buying-power
caps) with conservative slippage + commissions + stop gap-through, and
prints/saves the results with an explicit stress-period breakdown (2020 crash,
2022 bear).

USAGE (run on your machine or the Oracle box — needs internet to the data hosts):
    pip install requests
    python run_options_backtest.py --etf SPY --start 2018-01-01 --end 2025-12-31
    python run_options_backtest.py --etf QQQ
    python run_options_backtest.py --etf IWM

    # what is the bot's vol-scaled sizing actually worth in the stress windows?
    python run_options_backtest.py --etf SPY --no-vol-scaling

Note: this can't run from a locked-down sandbox; it needs network access to
stooq.com. Outputs a results JSON + a readable summary. The engine itself has no
network dependency — see test_options_backtest.py, which drives it entirely on
injected synthetic series.

DATA SOURCE NOTE: Stooq is free and reliable for daily bars and the vol indices.
If a symbol fails, the script says so. The VIX-family value is divided by 100 to
get a decimal vol (VIX 18 -> 0.18).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import backtest_engine as be

logger = logging.getLogger("options_backtest")

# Map each ETF to its implied-vol index (the real historical IV source).
ETF_VOL_INDEX = {
    "SPY": "^VIX",
    "QQQ": "^VXN",
    "IWM": "^RVX",
}

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&d1={start}&d2={end}&i=d"


def stooq_symbol(symbol: str) -> str:
    """
    Translate a plain ticker into Stooq's symbol convention.

    Stooq namespaces by market: US-listed equities and ETFs carry a `.us`
    suffix (`spy.us`, `qqq.us`, `iwm.us`), while indices are prefixed with a
    caret and take NO suffix (`^vix`, `^vxn`, `^rvx`, `^irx`). Everything is
    lower-case.

    This replaces `symbol.lower().replace("^", "^")`, which replaced a caret
    with a caret and therefore did nothing at all — the collapsed remains of
    exactly this index-vs-equity branch. Its absence meant the ETF legs were
    requested as bare `spy` / `qqq` / `iwm`, which are not the US tickers on
    Stooq.
    """
    s = symbol.strip().lower()
    if s.startswith("^"):
        return s          # index — no market suffix
    if "." in s:
        return s          # already market-qualified, e.g. "spy.us"
    return f"{s}.us"      # US-listed equity / ETF


def _fetch_stooq(symbol: str, start: date, end: date) -> dict:
    """Fetch daily closes from Stooq. Returns {date: close}. Empty on failure."""
    import requests
    # quote() turns the index caret into %5E; a bare ^ is not a legal URL char.
    s = quote(stooq_symbol(symbol), safe="")
    url = STOOQ_URL.format(symbol=s, start=start.strftime("%Y%m%d"),
                           end=end.strftime("%Y%m%d"))
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Fetch failed for %s: %s", symbol, e)
        return {}
    out = {}
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        try:
            d = datetime.strptime(row["Date"], "%Y-%m-%d").date()
            c = float(row["Close"])
            out[d] = c
        except (KeyError, ValueError):
            continue
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Options PCS backtest on index ETFs.")
    p.add_argument("--etf", default="SPY", choices=list(ETF_VOL_INDEX.keys()))
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default="2025-12-31")
    p.add_argument("--capital", type=float, default=100_000.0)
    p.add_argument("--entry-every", type=int, default=1,
                   help="Attempt a new entry every N trading days (1=daily ladder).")
    p.add_argument("--no-vol-scaling", action="store_true",
                   help="Disable the bot's vol-scaled sizing (flat 2%%). Use this "
                        "to measure what the vol scaling is worth in 2020/2022.")
    p.add_argument("--rf", type=float, default=None,
                   help="Pin the risk-free rate for the Sharpe (e.g. 0.04). "
                        "Default: average of the ^IRX series over the window.")
    p.add_argument("--expiry-calendar", default="weekly",
                   choices=["weekly", "monthly", "calendar"],
                   help="weekly=every Friday (default, matches these ETFs' real "
                        "chains); monthly=third Friday only; calendar=legacy "
                        "today+35d approximation.")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    vol_idx = ETF_VOL_INDEX[args.etf]

    logger.info("Fetching %s prices, %s vol, ^IRX rate (%s to %s)...",
                args.etf, vol_idx, start, end)
    prices = _fetch_stooq(args.etf, start, end)
    vols_raw = _fetch_stooq(vol_idx, start, end)
    rates_raw = _fetch_stooq("^IRX", start, end)  # 13-week T-bill yield (in %)

    if not prices or not vols_raw:
        logger.error("Could not fetch required data. Prices=%d Vols=%d. "
                     "Check internet access to stooq.com.", len(prices), len(vols_raw))
        return 1

    vols = {d: v / 100.0 for d, v in vols_raw.items()}     # VIX 18 -> 0.18
    rates = {d: v / 100.0 for d, v in rates_raw.items()} if rates_raw else {}
    if not rates:
        logger.warning("No rate data; defaulting to 3%% flat (and the Sharpe's "
                       "risk-free leg with it).")

    logger.info("Fetched: %d price days, %d vol days, %d rate days.",
                len(prices), len(vols), len(rates))

    cfg = be.BacktestConfig(
        initial_capital=args.capital,
        entry_every_n_days=args.entry_every,
        use_vol_scaled_sizing=not args.no_vol_scaling,
        risk_free_rate=args.rf,
        expiration_calendar=args.expiry_calendar,
    )
    bt = be.OptionsBacktester(cfg)
    res = bt.run(prices, vols, rates)

    if "error" in res:
        logger.error("Backtest error: %s", res["error"])
        return 1

    _print_report(args.etf, res, cfg)

    out_path = Path(f"options_backtest_{args.etf}_{date.today().isoformat()}.json")
    out_path.write_text(json.dumps(res, indent=2))
    logger.info("Full results saved to %s", out_path)
    return 0


def _stress_window_return(equity_curve, lo: str, hi: str):
    """Return over a date window [lo, hi] (ISO strings), or None if no data."""
    pts = [e for e in equity_curve if lo <= e["date"] <= hi]
    if len(pts) < 2:
        return None
    return pts[-1]["equity"] / pts[0]["equity"] - 1.0


def _print_report(etf, res, cfg):
    s = res["stats"]
    ec = res["equity_curve"]
    print("\n" + "=" * 64)
    print(f"  OPTIONS PUT-CREDIT-SPREAD BACKTEST — {etf} (index proxy)")
    print("=" * 64)
    print(f"  Period: {ec[0]['date']} to {ec[-1]['date']}")
    print(f"  Implied vol source: real {ETF_VOL_INDEX[etf]} (errs conservative — ignores put skew)")
    print(f"  Sizing: 2% per trade, vol-scaled={cfg.use_vol_scaled_sizing}, "
          f"max {cfg.max_contracts_per_spread} contracts/spread, "
          f"max {cfg.max_concurrent} concurrent, <= {cfg.max_total_deployed_pct:.0%} deployed")
    print(f"  Expirations: {cfg.expiration_calendar}")
    if s["halted_early"]:
        print("-" * 64)
        print("  *** RUN HALTED EARLY ***")
        print(f"  {s['halt_reason']}")
        print(f"  Open positions at halt: {s['open_positions_at_halt']}")
        print("  Every number below covers only the period up to the halt.")
    print("-" * 64)
    print(f"  Total return:        {s['total_return']*100:+8.2f}%")
    print(f"  Final equity:        ${s['final_equity']:,.0f}")
    print(f"  Annualized return:   {s['annualized_return']*100:+8.2f}%  (raw, before risk-free)")
    print(f"  Risk-free used:      {s['risk_free_rate_used']*100:7.2f}%  (^IRX avg over window)")
    print(f"  Annualized vol:      {s['annualized_vol']*100:7.1f}%")
    print(f"  Sharpe (excess):     {s['sharpe']:7.2f}  <- (return - risk-free) / vol; THE one")
    print(f"  Sharpe (no rf):      {s['sharpe_raw']:7.2f}  <- return / vol; flattering, don't quote it")
    print(f"  Max drawdown:        {s['max_drawdown']*100:7.1f}%")
    if s["margin_breach_days"]:
        print(f"  Margin-breach days:  {s['margin_breach_days']}  <- equity below the buying "
              f"power held against open spreads")
    print("-" * 64)
    print(f"  Trades:              {s['num_trades']}")
    print(f"  Win rate:            {s['win_rate']*100:7.1f}%")
    print(f"  Avg win:             ${s['avg_win']:,.0f}")
    print(f"  Avg loss:            ${s['avg_loss']:,.0f}")
    print(f"  Worst single trade:  ${s['worst_trade']:,.0f}   <- the tail that matters")
    print(f"  Exits by reason:     {s['exits_by_reason']}")
    print("-" * 64)
    print("  STRESS PERIODS (where premium-selling gets tested):")
    for label, lo, hi in [
        ("COVID crash (Feb-Apr 2020)", "2020-02-15", "2020-04-30"),
        ("2022 bear market", "2022-01-01", "2022-12-31"),
    ]:
        r = _stress_window_return(ec, lo, hi)
        if r is not None:
            print(f"    {label:32s} {r*100:+7.2f}%")
        else:
            print(f"    {label:32s} (outside tested range)")
    print("=" * 64)
    print("  HOW TO READ THIS:")
    print("  - High win rate + small avg win + large avg loss = the expected")
    print("    'pick up pennies' profile. The question is whether the pennies")
    print("    outrun the bricks — check total return AND the stress rows.")
    print("  - If the stress-period returns are deeply negative, that's the")
    print("    real risk of the strategy showing through (as it should).")
    print("  - Quote the EXCESS Sharpe. On a ~5%-vol strategy with cash at ~4%,")
    print("    the no-rf number is inflated by roughly 0.8 — nearly all of it.")
    print("  - Vol-scaled sizing is ON by default because the live bot has it on.")
    print("    Re-run with --no-vol-scaling to see the flat-2% stress losses;")
    print("    the gap between the two IS what that rule buys you.")
    print("  - This is the INDEX proxy. Your single-stock version has wider")
    print("    spreads, higher costs, and more blow-up risk — so it would do")
    print("    WORSE than this, not better. A weak index result here is a red")
    print("    flag for the whole approach; a strong one is necessary but not")
    print("    sufficient for the single-stock names.")
    print("  - Read the 'WHAT THIS DOES NOT MODEL' block at the top of")
    print("    backtest_engine.py before quoting any of these numbers. One IV")
    print("    for every strike and maturity, and no portfolio/correlation")
    print("    dimension at all, are the two that would move them most.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    sys.exit(main())
