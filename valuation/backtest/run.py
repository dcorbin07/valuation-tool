"""
Backtest runners — tie panel construction to the engine and print/return a verdict.
"""
from __future__ import annotations

from typing import Optional

from . import engine
from . import panel as panelmod


def run_on_panel(panel, factor_cols=None, q=5, cost_bps=5.0, horizon_days=21) -> dict:
    return engine.summarize(panel, factor_cols=factor_cols, q=q,
                            cost_bps=cost_bps, horizon_days=horizon_days)


def run_from_tickers(tickers: list, horizon_days=21, lookback_years=5,
                     rebalance_days=21, benchmark="SPY", cost_bps=5.0,
                     score_fn=None) -> dict:
    """Momentum (or injected-score) backtest on real prices for a ticker list."""
    panel = panelmod.build_price_panel(tickers, horizon_days=horizon_days,
                                       lookback_years=lookback_years, rebalance_days=rebalance_days,
                                       benchmark=benchmark, score_fn=score_fn)
    if panel.empty:
        return {"error": "Empty panel — could not build return series (check tickers / network)."}
    res = run_on_panel(panel, factor_cols=["momentum"], q=min(5, max(2, panel["ticker"].nunique() // 5)),
                       cost_bps=cost_bps, horizon_days=horizon_days)
    res["n_names"] = int(panel["ticker"].nunique())
    res["n_rows"] = int(len(panel))
    res["survivorship_caveat"] = ("Free price feeds only carry names still listed today, so "
                                  "delisted losers are missing and any edge is overstated. "
                                  "This is a screen, not proof.")
    return res


def run_from_store(store, top=50, **kwargs) -> dict:
    """Backtest the tickers in the latest hot-stocks snapshot."""
    rows = store.load_snapshot(top=top)
    if not rows:
        return {"error": "No snapshot found. Run a scan first."}
    tickers = [r["ticker"] for r in rows]
    out = run_from_tickers(tickers, **kwargs)
    out["source"] = f"latest snapshot top {len(tickers)}"
    return out


def print_verdict(res: dict):
    if res.get("error"):
        print("ERROR:", res["error"]); return
    ic = res["ic"]
    print(f"\n{'='*60}\n BACKTEST VERDICT\n{'='*60}")
    print(f"  periods: {ic['n_periods']} | names: {res.get('n_names','?')}")
    print(f"  Mean IC: {ic['mean_ic']:+.4f}  (t={ic.get('ic_t', float('nan')):.2f}, "
          f"hit-rate {ic.get('hit_rate', float('nan')):.0%})")
    if res.get("quantiles"):
        q = res["quantiles"]
        print(f"  Quantile spread (net): {q['top_minus_bottom_net']:+.4f}  "
              f"monotonic={q['monotonic_increasing']}")
    if res.get("equity"):
        p, b = res["equity"]["port"], res["equity"]["bench"]
        print(f"  Top-quintile: total {p['total_return']:+.1%} | ann {p['ann_return']:+.1%} "
              f"| Sharpe {p['sharpe']} | maxDD {p['max_drawdown']:.1%}")
        print(f"  Benchmark:    total {b['total_return']:+.1%} | ann {b['ann_return']:+.1%}")
    print(f"\n  VERDICT: {res['verdict']}")
    if res.get("survivorship_caveat"):
        print(f"  NOTE: {res['survivorship_caveat']}")
