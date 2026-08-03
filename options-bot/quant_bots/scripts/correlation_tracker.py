#!/usr/bin/env python3
"""
Correlation tracker — the payoff tool for the multi-strategy pilot.

Reads each bot's simulated equity curve (data/sim/<bot>/equity_curve.jsonl) plus
the options bot's journal, aligns them by date, and reports:
  - each strategy's total return, daily-return volatility, and rough Sharpe
  - the correlation matrix between the strategies' daily returns

That correlation matrix is the whole point of running them in parallel: it tells
you how the strategies actually move together (or don't), which is what you need
to decide how to weight them in a combined portfolio. Low/negative correlations
mean the combination will be smoother than any single strategy.

Usage:
    python scripts/correlation_tracker.py
    python scripts/correlation_tracker.py --bots trend momentum

Needs at least ~20 overlapping days per pair of bots for the correlation to mean
anything; with fewer it prints the returns but flags the correlation as
preliminary.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_equity_curve(bot: str) -> dict[str, float]:
    """Return {date: equity} from a bot's sim equity curve, latest per date."""
    path = PROJECT_ROOT / "data" / "sim" / bot / "equity_curve.jsonl"
    if not path.exists():
        return {}
    by_date: dict[str, float] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            snap = json.loads(line)
            by_date[snap["date"]] = float(snap["equity"])  # last write per date wins
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return by_date


def daily_returns(equity_by_date: dict[str, float]) -> dict[str, float]:
    """Convert an equity series into {date: daily_return}."""
    dates = sorted(equity_by_date)
    rets: dict[str, float] = {}
    for i in range(1, len(dates)):
        prev, cur = equity_by_date[dates[i - 1]], equity_by_date[dates[i]]
        if prev > 0:
            rets[dates[i]] = cur / prev - 1.0
    return rets


def stats(equity_by_date: dict[str, float]) -> dict:
    dates = sorted(equity_by_date)
    if len(dates) < 2:
        return {"days": len(dates), "total_return": 0.0, "vol": 0.0, "sharpe": 0.0}
    total = equity_by_date[dates[-1]] / equity_by_date[dates[0]] - 1.0
    rets = list(daily_returns(equity_by_date).values())
    if len(rets) >= 2:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        vol = math.sqrt(var)
        ann_vol = vol * math.sqrt(252)
        ann_ret = mean * 252
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    else:
        ann_vol = sharpe = 0.0
    return {"days": len(dates), "total_return": total,
            "ann_vol": ann_vol, "sharpe": sharpe}


def correlation(a: dict[str, float], b: dict[str, float]) -> tuple[float, int]:
    """Pearson correlation of two {date: return} series over shared dates."""
    shared = sorted(set(a) & set(b))
    n = len(shared)
    if n < 2:
        return float("nan"), n
    xs = [a[d] for d in shared]
    ys = [b[d] for d in shared]
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return float("nan"), n
    return cov / math.sqrt(vx * vy), n


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-strategy correlation tracker.")
    parser.add_argument("--bots", nargs="+", default=["trend", "momentum", "options", "reversion"],
                        help="Which bots' sim curves to compare.")
    args = parser.parse_args()

    curves = {bot: load_equity_curve(bot) for bot in args.bots}
    curves = {bot: c for bot, c in curves.items() if len(c) >= 2}

    if not curves:
        print("No equity curves found yet. Run the bots in SIM mode first:")
        print("  $env:BOT_MODE='sim'; python scripts/run_trend_bot.py --once")
        print("  $env:BOT_MODE='sim'; python scripts/run_momentum_bot.py --once")
        return 0

    print("\n" + "=" * 60)
    print("PER-STRATEGY PERFORMANCE (simulated)")
    print("=" * 60)
    print(f"{'Strategy':<12}{'Days':>6}{'Return':>10}{'AnnVol':>10}{'Sharpe':>9}")
    print("-" * 60)
    rets = {}
    for bot, curve in curves.items():
        s = stats(curve)
        rets[bot] = daily_returns(curve)
        print(f"{bot:<12}{s['days']:>6}{s['total_return']*100:>9.2f}%"
              f"{s.get('ann_vol',0)*100:>9.1f}%{s.get('sharpe',0):>9.2f}")

    bots = list(curves.keys())

    # Guard: detect curves that barely overlap in time. Correlating a backtest
    # curve (e.g. 2022-2024) against a live-SIM curve (e.g. 2026) is meaningless
    # because they share almost no dates. Warn loudly rather than silently
    # report a garbage number built on a few coincidental dates.
    ranges = {}
    for bot, curve in curves.items():
        ds = sorted(curve)
        ranges[bot] = (ds[0], ds[-1])
    print("\nDate ranges:")
    for bot, (lo, hi) in ranges.items():
        print(f"  {bot:<18} {lo} → {hi}  ({len(curves[bot])} days)")

    if len(bots) >= 2:
        for i in range(len(bots)):
            for j in range(i + 1, len(bots)):
                a, b = bots[i], bots[j]
                shared = set(daily_returns(curves[a])) & set(daily_returns(curves[b]))
                if len(shared) < 20:
                    print(f"\n  ⚠ WARNING: {a} and {b} share only {len(shared)} "
                          f"overlapping days. Their correlation is NOT meaningful.")
                    print("    This usually means you're comparing curves from "
                          "different timeframes")
                    print("    (e.g. a backtest vs. a live-SIM run). Correlate only "
                          "curves over the SAME window — backtests with backtests, "
                          "live-SIM with live-SIM.")

    if len(bots) >= 2:
        print("\n" + "=" * 60)
        print("CORRELATION MATRIX (daily returns)")
        print("=" * 60)
        header = " " * 12 + "".join(f"{b:>12}" for b in bots)
        print(header)
        for b1 in bots:
            row = f"{b1:<12}"
            for b2 in bots:
                if b1 == b2:
                    row += f"{'1.00':>12}"
                else:
                    corr, n = correlation(rets[b1], rets[b2])
                    cell = f"{corr:+.2f}" if not math.isnan(corr) else "n/a"
                    flag = "*" if n < 20 else ""
                    row += f"{cell + flag:>12}"
            print(row)
        print("\n  * = fewer than 20 overlapping days; correlation is preliminary.")
        print("  Goal: low or negative off-diagonal values → strategies diversify")
        print("  each other, so the combined portfolio is smoother than any one.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
