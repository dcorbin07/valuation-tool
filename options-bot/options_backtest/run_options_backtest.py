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
from datetime import date, datetime, timedelta
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

# Cboe publishes the full daily history of its own volatility indices as plain
# CSV, with no key and no anti-bot layer. This is the AUTHORITATIVE source for
# VIX/VXN/RVX — Stooq was only ever a mirror of it — and it is the only free
# source for ^RVX at all (Yahoo does not carry it).
CBOE_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{name}_History.csv"

# Stooq blocks non-browser clients outright, so send a browser UA. As of
# 2026-08-03 that is no longer sufficient (see _fetch_stooq), but it costs
# nothing and keeps the primary path working if they drop the challenge.
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


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
    """
    Fetch daily closes from Stooq. Returns {date: close}. Empty on failure.

    STOOQ IS NO LONGER USABLE FROM A SCRIPT (verified 2026-08-03). A bare
    request returns HTTP 404; with a browser User-Agent it returns HTTP 200
    carrying a JavaScript browser-verification challenge instead of CSV. The
    module docstring's "Stooq is free and reliable" is now false, and this
    backtest could not have run against it on the day the audit was written
    either. We detect the challenge explicitly rather than letting DictReader
    parse HTML into an empty dict and reporting it as "no data" — a silent
    empty is how a dead feed turns into a wrong conclusion.
    """
    import requests
    # quote() turns the index caret into %5E; a bare ^ is not a legal URL char.
    s = quote(stooq_symbol(symbol), safe="")
    url = STOOQ_URL.format(symbol=s, start=start.strftime("%Y%m%d"),
                           end=end.strftime("%Y%m%d"))
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": _BROWSER_UA})
        resp.raise_for_status()
    except Exception as e:
        logger.info("Stooq unavailable for %s (%s); trying the next source.", symbol, e)
        return {}
    head = resp.text[:200].lstrip().lower()
    if not head.startswith("date,"):
        logger.info("Stooq returned a non-CSV body for %s (bot challenge); "
                    "trying the next source.", symbol)
        return {}
    return _parse_csv_closes(resp.text, "%Y-%m-%d", "Date", "Close")


def _parse_csv_closes(text: str, date_fmt: str, date_col: str, close_col: str) -> dict:
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out[datetime.strptime(row[date_col], date_fmt).date()] = float(row[close_col])
        except (KeyError, ValueError, TypeError):
            continue
    return out


def _fetch_cboe(symbol: str, start: date, end: date) -> dict:
    """
    Daily closes for a Cboe volatility index (^VIX / ^VXN / ^RVX) straight from
    Cboe. Full history, no key. Empty for anything that is not a Cboe index.
    """
    name = symbol.strip().lstrip("^").upper()
    if name not in ("VIX", "VXN", "RVX"):
        return {}
    import requests
    try:
        resp = requests.get(CBOE_URL.format(name=name), timeout=60,
                            headers={"User-Agent": _BROWSER_UA})
        resp.raise_for_status()
    except Exception as e:
        logger.info("Cboe unavailable for %s (%s); trying the next source.", symbol, e)
        return {}
    series = _parse_csv_closes(resp.text, "%m/%d/%Y", "DATE", "CLOSE")
    return {d: v for d, v in series.items() if start <= d <= end}


def _fetch_yfinance(symbol: str, start: date, end: date) -> dict:
    """Daily closes via yfinance. Carries the ETFs and ^IRX; has no ^RVX."""
    try:
        import yfinance as yf
    except ImportError:
        logger.info("yfinance not installed; skipping that source.")
        return {}
    try:
        h = yf.Ticker(symbol).history(start=start.isoformat(),
                                      end=(end + timedelta(days=1)).isoformat(),
                                      auto_adjust=False)
    except Exception as e:
        logger.info("yfinance failed for %s (%s).", symbol, e)
        return {}
    if h is None or len(h) == 0 or "Close" not in h:
        return {}
    return {ts.date(): float(c) for ts, c in h["Close"].items() if c == c}


# Source order per symbol. Stooq first because it is what the script was written
# against and what the docs claim; the rest are the fallbacks that make the
# thing actually runnable in 2026.
_SOURCES = (("stooq", _fetch_stooq), ("cboe", _fetch_cboe), ("yfinance", _fetch_yfinance))


def fetch_series(symbol: str, start: date, end: date) -> tuple[dict, str]:
    """
    Fetch daily closes for `symbol`, trying each free source in turn.

    Returns (series, source_name). The source name is recorded in the results
    JSON: a backtest whose data provenance is not written down cannot be
    reproduced, and this script silently changed feeds once already.
    """
    for name, fn in _SOURCES:
        series = fn(symbol, start, end)
        if series:
            logger.info("%s: %d days from %s (%s to %s)", symbol, len(series), name,
                        min(series), max(series))
            return series, name
    logger.error("No free source returned data for %s.", symbol)
    return {}, "none"


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
    p.add_argument("--iv-rank-min", type=float, default=None,
                   help="O9: open a spread ONLY when the vol index is at or "
                        "above this percentile of its own trailing window "
                        "(e.g. 0.667 = top tercile). Omit for the always-on "
                        "O8 baseline. Exits are never gated — this is a "
                        "sell-TIMING rule, not an exit rule.")
    p.add_argument("--iv-rank-window", type=int, default=252,
                   help="Trailing sessions for the IV-rank percentile (default 252).")
    p.add_argument("--slippage", type=float, default=None,
                   help="Slippage per share per leg (default 0.02). The single "
                        "most decision-relevant constant in the model: on the "
                        "index legs it is 3x commission and consumes most of "
                        "the gross premium. Use to bound the result.")
    p.add_argument("--commission", type=float, default=None,
                   help="Commission per contract per leg (default 0.65).")
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
    prices, px_src = fetch_series(args.etf, start, end)
    vols_raw, vol_src = fetch_series(vol_idx, start, end)
    rates_raw, rate_src = fetch_series("^IRX", start, end)  # 13-week T-bill yield (in %)

    if not prices or not vols_raw:
        logger.error("Could not fetch required data. Prices=%d Vols=%d. "
                     "Every free source failed — check network access.",
                     len(prices), len(vols_raw))
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
        iv_rank_min=args.iv_rank_min,
        iv_rank_window=args.iv_rank_window,
        **({"slippage_per_share": args.slippage} if args.slippage is not None else {}),
        **({"commission_per_contract": args.commission} if args.commission is not None else {}),
    )
    bt = be.OptionsBacktester(cfg)
    res = bt.run(prices, vols, rates)

    if "error" in res:
        logger.error("Backtest error: %s", res["error"])
        return 1

    # Provenance. Written into the results file because this script has already
    # silently changed feeds once, and a number whose data source is unrecorded
    # cannot be reproduced or challenged.
    res["data_sources"] = {
        "prices": {"symbol": args.etf, "source": px_src, "days": len(prices)},
        "implied_vol": {"symbol": vol_idx, "source": vol_src, "days": len(vols)},
        "risk_free": {"symbol": "^IRX", "source": rate_src, "days": len(rates)},
        "window_requested": [args.start, args.end],
    }
    res["config"] = {k: v for k, v in vars(cfg).items()}

    _print_report(args.etf, res, cfg)
    print(f"  Data sources: prices={px_src}, vol={vol_src}, rate={rate_src}")

    out_path = Path(f"options_backtest_{args.etf}_{args.start}_{args.end}.json")
    # default=str: every Trade carries `entry_date`/`exit_date` as real `date`
    # objects, which json cannot encode. Without this the script raised
    # TypeError AFTER printing the report and BEFORE writing the file — so even
    # a fully successful run left nothing on disk. That is a second, independent
    # reason no result from this backtest appears anywhere in the corpus.
    out_path.write_text(json.dumps(res, indent=2, default=str))
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
    ivr = res.get("iv_rank") or {}
    if ivr:
        print("-" * 64)
        print("  O9 — IV RANK AS A SELL-TIMING RULE "
              f"(trailing {ivr.get('window')} sessions)")
        if ivr.get("gate_applied"):
            print(f"    Gate: open only when IV rank >= {ivr['iv_rank_min']:.3f}")
            fti = ivr.get("fraction_of_time_invested")
            if fti is not None:
                print(f"    Fraction of time invested: {fti*100:5.1f}%  "
                      f"({ivr.get('entry_days_allowed'):,} of "
                      f"{ivr.get('entry_days_allowed',0)+ivr.get('entry_days_blocked',0):,} "
                      f"entry opportunities)")
        else:
            print("    Gate: OFF (always-on baseline)")
        bt = ivr.get("by_tercile")
        if bt:
            cuts = ivr.get("tercile_cuts", {})
            print(f"    Terciles cut on the OBSERVED IV-rank distribution "
                  f"(low<{cuts.get('low',0):.3f}, high>={cuts.get('high',0):.3f}):")
            for k in ("bottom", "middle", "top"):
                b = bt.get(k) or {}
                if b.get("n_trades"):
                    print(f"      {k:7s} n={b['n_trades']:5,}  "
                          f"mean P&L ${b['mean_pnl']:8,.2f}  "
                          f"total ${b['total_pnl']:11,.0f}  "
                          f"win {b['win_rate']*100:4.1f}%")
            tvr = ivr.get("top_vs_rest_mean_pnl") or {}
            if tvr.get("top") is not None and tvr.get("rest") is not None:
                delta = tvr["top"] - tvr["rest"]
                verdict = "HIGHER" if delta > 0 else "LOWER"
                print(f"    Top tercile mean P&L is {verdict} than the rest by "
                      f"${abs(delta):,.2f}/trade "
                      f"(${tvr['top']:,.2f} vs ${tvr['rest']:,.2f})")
                print("      ^ THE directional test of the hypothesis: does "
                      "expensive vol predict good short-vol outcomes?")

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
