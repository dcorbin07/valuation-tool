"""
Edge Lab — your private research bench (owner-only).

Three commands, all in the honest spirit of your screener:

  backtest  — simulate following the strategy's PIT picks (momentum or the Signals
              technical score) from the S&P 500 vs SPY, at 1/5/10-year horizons.
  optimize  — build a multi-factor price panel and walk-forward-tune the weights;
              adopt changes ONLY if they beat baseline out-of-sample (no overfit),
              with Claude proposing mechanism-driven candidates.
  track     — accrue the live "paper account": realized forward returns of past
              hot-list picks vs SPY, per horizon, with hit rates.

    python -m valuation.edge.lab backtest --strategy momentum --hold 15 --limit 120
    python -m valuation.edge.lab optimize --limit 120
    python -m valuation.edge.lab track
"""
from __future__ import annotations

import argparse
import sys

from ..config import CONFIG
from ..screener.store import Store
from ..screener.universe import sp500_tickers


def run_backtest(strategy="momentum", tickers=None, cfg=CONFIG, hold_top=15,
                 rebalance_days=21, years=(1, 5, 10), price_fn=None, limit=None) -> dict:
    from .portfolio_backtest import run, momentum_score, technical_score_fn
    tickers = tickers or sp500_tickers(cfg)
    if limit:
        tickers = tickers[:limit]
    sf = technical_score_fn if strategy == "technical" else momentum_score
    res = run(tickers, benchmark="SPY", score_fn=sf, hold_top=hold_top,
              rebalance_days=rebalance_days, years=years, price_fn=price_fn)
    res["strategy"] = strategy
    res["n_universe"] = len(tickers)
    return res


def run_optimize(tickers=None, cfg=CONFIG, price_fn=None, limit=None) -> dict:
    from .panel import build_factor_panel, FACTORS
    from .walkforward import walk_forward
    from .advisor import propose_and_validate
    tickers = tickers or sp500_tickers(cfg)
    if limit:
        tickers = tickers[:limit]
    panel = build_factor_panel(tickers, price_fn=price_fn)
    if panel.empty:
        return {"error": "Empty panel — no price data (check network/tickers)."}
    wf = walk_forward(panel, FACTORS, n_folds=5, step_grid=0.25)
    adv = propose_and_validate(panel, FACTORS, cfg)
    return {"walk_forward": wf, "advisor": {k: adv.get(k) for k in
            ("factor_ic_discovery", "baseline_holdout_ic", "adopted", "note")},
            "n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
            "factors": FACTORS}


def run_track(source="hot", cfg=CONFIG, store=None, price_fn=None, top=15) -> dict:
    from . import track
    store = store or Store()
    # Seed the track record from existing dated snapshots (hot list = dated picks).
    if source == "hot":
        for s in store.list_scans():
            rows = store.load_snapshot(s["scan_date"], top=top)
            track.log_picks(store, "hot", s["scan_date"], [r["ticker"] for r in rows])
    upd = track.update_returns(store, source, price_fn=price_fn)
    return {"updated": upd, "summary": track.summary(store, source)}


# ---------------- CLI ---------------- #
def _p_backtest(res):
    if res.get("error"):
        print("ERROR:", res["error"]); return
    print(f"\nStrategy: {res.get('strategy')} | universe {res.get('n_universe')} | "
          f"{res.get('survivorship_caveat', '')[:0]}")
    for h in ("1y", "5y", "10y", "full"):
        s = res.get(h, {})
        if not s.get("available"):
            print(f"  {h:>4}: n/a"); continue
        p, b = s["portfolio"], s["benchmark"]
        print(f"  {h:>4}: strategy CAGR {p['cagr']:+.1%} vs SPY {b['cagr']:+.1%} | "
              f"alpha {s['alpha_cagr']:+.1%} | Sharpe {p['sharpe']:.2f} | maxDD {p['max_drawdown']:.0%}")
    print("  NOTE:", res.get("survivorship_caveat", ""))


def _p_optimize(res):
    if res.get("error"):
        print("ERROR:", res["error"]); return
    wf = res["walk_forward"]
    print(f"\nPanel: {res['n_rows']} rows over {res['n_dates']} dates | factors {res['factors']}")
    print("WALK-FORWARD:", wf["verdict"])
    print("  recommended weights:", {k: round(v, 2) for k, v in wf["final_weights"].items()})
    adv = res["advisor"]
    print("ADVISOR:", adv["note"])
    if adv.get("adopted"):
        print("  proposal:", {k: round(v, 2) for k, v in adv["adopted"]["weights"].items()},
              "| holdout IC", round(adv["adopted"]["holdout_ic"], 3))


def _p_track(res):
    print("\nSeeded/updated:", res["updated"])
    print("PAPER TRACK RECORD (picks vs SPY):")
    for h, s in res["summary"].items():
        if not s:
            print(f"  {h}d: no matured picks yet"); continue
        print(f"  {h}d: n={s['n']} | avg {s['avg_return']:+.1%} vs SPY {s['avg_bench']:+.1%} | "
              f"alpha {s['avg_alpha']:+.1%} | beat-SPY {s['hit_rate_vs_bench']:.0%} | win {s['win_rate']:.0%}")


def main():
    ap = argparse.ArgumentParser(description="Edge Lab (owner-only research bench)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backtest"); b.add_argument("--strategy", default="momentum", choices=["momentum", "technical"])
    b.add_argument("--hold", type=int, default=15); b.add_argument("--rebalance", type=int, default=21)
    b.add_argument("--limit", type=int, default=120)
    o = sub.add_parser("optimize"); o.add_argument("--limit", type=int, default=120)
    t = sub.add_parser("track"); t.add_argument("--source", default="hot")
    args = ap.parse_args()

    if args.cmd == "backtest":
        _p_backtest(run_backtest(strategy=args.strategy, hold_top=args.hold,
                                 rebalance_days=args.rebalance, limit=args.limit))
    elif args.cmd == "optimize":
        _p_optimize(run_optimize(limit=args.limit))
    elif args.cmd == "track":
        _p_track(run_track(source=args.source))


if __name__ == "__main__":
    sys.exit(main())
