"""
run_backtest.py — does the screener's composite predict forward returns?

Builds a point-in-time panel from FREE data (EDGAR fundamentals + Stooq/yfinance
prices), scores each cross-section with the new self-calibrating model (sector-
relative value + quality + momentum + growth), and runs the edge backtest.

    pip install -r requirements.txt
    cp .env.example .env        # only EDGAR_USER_AGENT is needed for the backtest
    python run_backtest.py

NO Discord. NO Opus/AI calls. NO cost. It prints one report to the console.

SURVIVORSHIP CAVEAT: free prices only cover names still listed today, so delisted
losers are missing and any edge looks better than reality. A positive result here is
"worth confirming on survivorship-free data (e.g. Sharadar)", not proof.
"""
import os
import sys
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
import edgar
import prices
import cross_sectional as X
import backtest_engine as B

# ---------------- CONFIG ----------------
START, END   = "2021-01-01", "2025-06-01"   # rebalance window (needs ~1y of prior price + forward window)
REBALANCE     = "MS"                          # monthly (month start)
HORIZON_TD    = 21                            # 1-month holding = matches monthly rebalance (no overlap)
UNIVERSE_LIMIT = 300                          # bound the first pass; raise once it works
COST_BPS      = 8.0                           # per-side cost; small-caps are wide, be honest
WEIGHTS       = {"ey_sn": 0.30, "roe": 0.10, "opm": 0.10, "neg_lev": 0.10, "mom": 0.20, "growth": 0.20}
BENCH         = "IWM"
# ----------------------------------------


def _rebalance_dates():
    return list(pd.date_range(START, END, freq=REBALANCE))


def score_panel(panel):
    """Per date: sector-neutralize value, then cross-sectional composite."""
    parts = []
    for _, g in panel.groupby("date"):
        g = g.copy()
        g["ey_sn"] = g.groupby("sector")["ey"].transform(lambda s: s - s.mean())  # sector-relative value
        g["composite"] = X.composite_score(g, WEIGHTS)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def main():
    if not os.environ.get("EDGAR_USER_AGENT"):
        print("!! Set EDGAR_USER_AGENT in .env (e.g. 'Your Name you@email.com') — EDGAR requires it.")
        return
    import pit_data

    tickers = list(edgar.all_filers().keys())[:UNIVERSE_LIMIT]
    print(f"Universe: {len(tickers)} names | rebalance {START}..{END} ({REBALANCE}) | horizon {HORIZON_TD}td")
    print("Fetching sectors + building point-in-time panel (this is the slow part)...")

    sectors = {}
    for t in tickers:
        s = edgar.sector(t)
        if s:
            sectors[t] = s

    bench_px = prices.get_history_df(BENCH, days=2600)
    if bench_px is None:
        print("!! Could not load benchmark prices."); return

    panel = pit_data.build_panel(
        tickers, _rebalance_dates(),
        get_facts=edgar.companyfacts,
        get_prices=lambda t: prices.get_history_df(t, days=2600),
        bench_prices=bench_px, horizon_td=HORIZON_TD, sectors=sectors)

    if panel.empty:
        print("!! Empty panel — check EDGAR/price fetching."); return
    print(f"Panel: {len(panel)} rows, {panel['date'].nunique()} rebalance dates, "
          f"{panel['ticker'].nunique()} names with data.")

    scored = score_panel(panel)
    res = B.summarize(scored, score_col="composite",
                      factor_cols=["ey_sn", "roe", "opm", "neg_lev", "mom", "growth"],
                      cost_bps=COST_BPS, q=5)
    print("\n" + "=" * 72)
    B.print_report(res)
    print("=" * 72)
    print("SURVIVORSHIP CAVEAT: free prices exclude delisted names, so this is biased")
    print("optimistic. A positive result => confirm on survivorship-free data, not proof.")


if __name__ == "__main__":
    main()
