#!/usr/bin/env python3
"""
Weekly correlation report — writes a self-explanatory report FILE.

Unlike correlation_tracker.py (which just prints to the terminal), this writes a
timestamped report to data/reports/ that:
  - explains every number inline, so you can read and understand it on its own
  - is plain text/markdown, so it's easy to skim on a phone
  - bundles the raw stats as JSON at the bottom, so you can upload the whole
    file to Claude for deeper interpretation

Run it manually (python scripts/weekly_report.py) or on a weekly timer. It also
posts a short summary to Discord if configured, with a note to check the file
for detail.

The file is written to:  data/reports/correlation_YYYY-MM-DD.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the existing, tested math from the correlation tracker.
from scripts.correlation_tracker import (
    correlation,
    daily_returns,
    load_equity_curve,
    stats,
)


def _interpret_corr(c: float) -> str:
    """Plain-English reading of a correlation value."""
    if math.isnan(c):
        return "not enough shared data yet"
    a = abs(c)
    strength = ("very weak" if a < 0.2 else "weak" if a < 0.4 else
                "moderate" if a < 0.6 else "strong" if a < 0.8 else "very strong")
    direction = "positive" if c > 0 else "negative"
    if a < 0.2:
        return f"{strength} — effectively independent (ideal for diversification)"
    return f"{strength} {direction}"


def _interpret_sharpe(s: float) -> str:
    if s <= 0:
        return "losing money (negative) so far"
    if s < 0.5:
        return "weak risk-adjusted return"
    if s < 1.0:
        return "okay risk-adjusted return"
    if s < 2.0:
        return "good risk-adjusted return"
    return "excellent (be skeptical — likely too few days, or a lucky stretch)"


def build_report(bots: list[str]) -> tuple[str, dict]:
    curves = {b: load_equity_curve(b) for b in bots}
    curves = {b: c for b, c in curves.items() if len(c) >= 2}

    lines: list[str] = []
    raw: dict = {"generated": datetime.now().isoformat(), "bots": {}, "correlations": {}}

    lines.append(f"# Weekly Strategy Report — {date.today().isoformat()}")
    lines.append("")
    if not curves:
        lines.append("No strategy data recorded yet. The bots need to run on at "
                     "least a couple of market days before there's anything to report.")
        return "\n".join(lines), raw

    # ── Per-strategy performance ──
    lines.append("## How each strategy is doing")
    lines.append("")
    lines.append("Each strategy runs its own simulated account. Here's where each stands:")
    lines.append("")
    rets = {}
    for bot, curve in curves.items():
        s = stats(curve)
        rets[bot] = daily_returns(curve)
        dates = sorted(curve)
        raw["bots"][bot] = {
            "days": s["days"], "total_return": s["total_return"],
            "ann_vol": s.get("ann_vol", 0), "sharpe": s.get("sharpe", 0),
            "first_date": dates[0], "last_date": dates[-1],
            "start_equity": curve[dates[0]], "latest_equity": curve[dates[-1]],
        }
        lines.append(f"### {bot}")
        lines.append(f"- **Days of data:** {s['days']} "
                     f"({dates[0]} to {dates[-1]})")
        lines.append(f"- **Total return:** {s['total_return']*100:+.2f}% "
                     f"(equity went from ${curve[dates[0]]:,.0f} to ${curve[dates[-1]]:,.0f})")
        lines.append(f"- **Annualized volatility:** {s.get('ann_vol',0)*100:.1f}% "
                     f"— how much it bounces around; higher = wilder ride")
        lines.append(f"- **Sharpe ratio:** {s.get('sharpe',0):.2f} "
                     f"— return earned per unit of risk; {_interpret_sharpe(s.get('sharpe',0))}")
        lines.append("")

    # ── Correlation matrix ──
    bots_with_data = list(curves.keys())
    if len(bots_with_data) >= 2:
        lines.append("## How the strategies move together (correlation)")
        lines.append("")
        lines.append("Correlation runs from -1 to +1. It measures whether two "
                     "strategies tend to have good and bad days *at the same time*:")
        lines.append("")
        lines.append("- **+1.0** = they move in lockstep (no diversification — "
                     "redundant)")
        lines.append("- **0.0** = independent (great — their ups and downs don't "
                     "line up, so combining them smooths the ride)")
        lines.append("- **-1.0** = perfect opposites (one zigs when the other zags)")
        lines.append("")
        lines.append("**What you want:** low or negative numbers between different "
                     "strategies. That's the whole point of running three — when "
                     "their bad patches don't coincide, the combined portfolio is "
                     "steadier than any single one.")
        lines.append("")
        for i in range(len(bots_with_data)):
            for j in range(i + 1, len(bots_with_data)):
                a, b = bots_with_data[i], bots_with_data[j]
                c, n = correlation(rets[a], rets[b])
                raw["correlations"][f"{a}__{b}"] = {"correlation": c if not math.isnan(c) else None,
                                                     "overlapping_days": n}
                cval = f"{c:+.2f}" if not math.isnan(c) else "n/a"
                flag = "  ⚠ (too few overlapping days — not yet meaningful)" if n < 20 else ""
                lines.append(f"- **{a} vs {b}:** {cval} "
                             f"({n} overlapping days) — {_interpret_corr(c)}{flag}")
        lines.append("")

    # ── Reading guidance ──
    lines.append("## How to read this / what to do")
    lines.append("")
    lines.append("1. **First few weeks:** ignore the correlations — under ~20 "
                 "overlapping days they're noise. Just confirm each strategy is "
                 "running and recording data.")
    lines.append("2. **After ~1-2 months:** the correlations start to mean "
                 "something. Look for the off-diagonal pairs being low or negative.")
    lines.append("3. **Sharpe ratios** tell you which strategies are actually "
                 "earning their risk. Negative = losing; below ~0.5 = weak.")
    lines.append("4. **If you want deeper analysis:** upload this whole file to "
                 "Claude and ask — the raw data is bundled at the bottom.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### Raw data (for deeper analysis / uploading to Claude)")
    lines.append("```json")
    lines.append(json.dumps(raw, indent=2))
    lines.append("```")

    return "\n".join(lines), raw


def main() -> int:
    p = argparse.ArgumentParser(description="Write the weekly correlation report.")
    p.add_argument("--bots", nargs="+", default=["options", "trend", "momentum", "reversion"])
    args = p.parse_args()

    report_text, raw = build_report(args.bots)

    reports_dir = PROJECT_ROOT / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"correlation_{date.today().isoformat()}.md"
    out_path.write_text(report_text)
    print(f"Report written to: {out_path}")

    # Optional: post a short Discord heads-up pointing to the file.
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        from core import DiscordNotifier
        notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))
        n_bots = len(raw.get("bots", {}))
        notifier.send(f"📈 Weekly report ready ({n_bots} strategies). "
                      f"Saved to data/reports/correlation_{date.today().isoformat()}.md "
                      f"on the box — SSH in to read it, or download to review.")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
