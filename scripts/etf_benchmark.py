#!/usr/bin/env python3
"""etf_benchmark.py — could a user just buy cheap factor ETFs instead?  [X4]

R1 asks whether the excess return is explained by factor exposure in a regression sense. X4
asks the practical version of the same question, and they can disagree: a regression can show
full factor loading while the implementation still adds value through better construction,
fresher data or a tighter universe. That gap, if it exists, is the actual product.

The blend, matched to the composite's themes, equal-weighted, rebalanced on the panel's own
63-trading-day grid:

    value VTV | quality QUAL | momentum MTUM | size IWM

Only 4 of the composite's 7 weighted themes have a retail ETF analogue — `insider`,
`capital_discipline` and `institutional` have none. That is a RESULT of this item, not a defect
in it: it is the half of the model a user cannot buy off the shelf.

QUAL lists 2013-07, so the matched blend covers only the back half of the panel. The strategy is
therefore measured on the IDENTICAL window — comparing a full-sample +11.88% against a 2013-2026
blend would be the central dishonesty available here.

ETF adjusted closes are already net of expense ratios, so the blend is measured NET of fees —
stricter than the audit asked. The strategy is charged the project's own cost model.

Thresholds are pre-registered in PREREG_free_analysis.md and are not restated from results.
Modifies no existing file.

    python -m scripts.etf_benchmark --panel data/free_analysis/panel.pkl
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

MATCHED = {"value": "VTV", "quality": "QUAL", "momentum": "MTUM", "size": "IWM"}
LONG_HISTORY = {"value": "IWD", "size": "IWM"}
MARKET = "SPY"
MIN_EXCESS_PP = 0.020          # +2.0pp — pre-registered
NO_ETF_ANALOGUE = ["insider", "capital_discipline", "institutional"]


def _fmt(x, p="+.2%"):
    return "n/a" if x is None or (isinstance(x, float) and x != x) else format(x, p)


def strategy_series(panel, weights, top_frac=0.1):
    """Per-rebalance-date top-decile return, equal-weight benchmark, and mean cost bps.

    This is the series R1 also needs ('already exists inside quantile_backtest as q_rets[0]
    and ewb; it just needs to be shipped'), computed here without touching the panel module.
    """
    import pandas as pd
    from valuation.screener.cross_sectional import zscore
    from valuation.edge.fundamental_panel import one_way_cost_bps

    rows, prev = [], set()
    for d, sub in panel.groupby("date"):
        comp = np.zeros(len(sub))
        for c, w in weights.items():
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * w
        ok = np.isfinite(comp) & np.isfinite(sub["fwd_ret"].values)
        s = sub[ok].assign(_c=comp[ok]).sort_values("_c", ascending=False)
        if len(s) < 30:
            continue
        k = max(1, int(len(s) * top_frac))
        top = s.head(k)
        held = set(top["ticker"])
        # one-way cost on the names entering the book this period
        traded = held - prev
        bps = np.mean([one_way_cost_bps(v) for v in
                       top.loc[top["ticker"].isin(traded), "market_cap"]]) if traded else 0.0
        rows.append({"date": d, "top": float(top["fwd_ret"].mean()),
                     "ew": float(s["fwd_ret"].mean()),
                     "turnover": len(traded) / max(1, k),
                     "cost_bps": float(bps) if bps == bps else 0.0,
                     "n": int(k)})
        prev = held
    return pd.DataFrame(rows)


def etf_windows(tickers, grid):
    """Total return of each ETF over each (t, t+1] window of the panel's grid."""
    import pandas as pd
    import yfinance as yf

    px = yf.download(list(tickers), start="1998-01-01", end="2026-08-01",
                     auto_adjust=True, progress=False)["Close"]
    if isinstance(px, pd.Series):
        px = px.to_frame(tickers[0])
    px.index = pd.to_datetime(px.index).tz_localize(None)

    g = pd.to_datetime(pd.Series(sorted(pd.to_datetime(grid).unique())))
    out = []
    for a, b in zip(g[:-1], g[1:]):
        rec = {"start": a, "end": b}
        for t in px.columns:
            s = px[t].dropna()
            s = s[(s.index > a) & (s.index <= b)]
            base = px[t].dropna()
            base = base[base.index <= a]
            if len(s) and len(base):
                rec[t] = float(s.iloc[-1] / base.iloc[-1] - 1.0)
            else:
                rec[t] = np.nan
        out.append(rec)
    return pd.DataFrame(out).set_index("end")


def ann(series, periods_per_year):
    s = np.asarray([x for x in series if x == x], dtype=float)
    if not len(s):
        return None
    return float((1.0 + s).prod() ** (periods_per_year / len(s)) - 1.0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Factor-ETF benchmark (X4).")
    ap.add_argument("--panel", default="data/free_analysis/panel.pkl")
    ap.add_argument("--json", default="data/free_analysis/ETF_BENCHMARK_RESULTS.json")
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.screener import settings as S

    panel = pd.read_pickle(args.panel)
    panel["date"] = pd.to_datetime(panel["date"])
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}

    strat = strategy_series(panel, dep)
    strat = strat.set_index("date")
    ppy = 252.0 / 63.0                                   # 4 windows a year
    print(f"[X4] strategy series: {len(strat)} periods "
          f"{strat.index.min().date()} -> {strat.index.max().date()}", flush=True)

    grid = list(strat.index)
    all_etfs = sorted(set(MATCHED.values()) | set(LONG_HISTORY.values()) | {MARKET})
    ew = etf_windows(all_etfs, grid)
    print(f"[X4] ETF windows: {len(ew)}", flush=True)

    out = {"item": "X4", "prereg": "PREREG_free_analysis.md",
           "threshold_min_excess_pp": MIN_EXCESS_PP,
           "matched_blend": MATCHED, "long_history_blend": LONG_HISTORY,
           "themes_with_no_etf_analogue": NO_ETF_ANALOGUE,
           "note_fees": "ETF adjusted closes are already net of expense ratios — the blend is "
                        "measured NET of fees, stricter than the audit asked.",
           "blends": {}}

    def evaluate(label, mapping):
        etfs = sorted(set(mapping.values()))
        sub = ew[etfs].dropna()
        if sub.empty:
            out["blends"][label] = {"status": "no overlapping window"}
            return
        idx = [d for d in sub.index if d in strat.index]
        sub = sub.loc[idx]
        st = strat.loc[idx]
        blend = sub.mean(axis=1)                          # equal-weighted across the sleeves

        # strategy net of its own costs: one-way bps on the fraction of the book that turned over
        cost = (st["cost_bps"] / 1e4) * st["turnover"]
        net = st["top"] - cost

        a_net = ann(net, ppy); a_gross = ann(st["top"], ppy)
        a_blend = ann(blend, ppy); a_ew = ann(st["ew"], ppy)
        a_spy = ann(ew.loc[idx, MARKET].dropna(), ppy) if MARKET in ew else None
        exc = None if (a_net is None or a_blend is None) else a_net - a_blend

        h = len(idx) // 2
        e1 = (ann(net.iloc[:h], ppy) or 0) - (ann(blend.iloc[:h], ppy) or 0)
        e2 = (ann(net.iloc[h:], ppy) or 0) - (ann(blend.iloc[h:], ppy) or 0)

        rec = {"etfs": etfs, "n_periods": len(idx),
               "window": [str(idx[0].date()), str(idx[-1].date())],
               "strategy_gross_ann": a_gross, "strategy_net_ann": a_net,
               "blend_ann": a_blend, "equal_weight_universe_ann": a_ew, "spy_ann": a_spy,
               "excess_vs_blend": exc, "excess_first_half": e1, "excess_second_half": e2,
               "both_halves_positive": bool(e1 > 0 and e2 > 0),
               "strategy_cost_drag_ann": (None if a_gross is None or a_net is None
                                          else a_gross - a_net),
               "per_etf_ann": {t: ann(sub[t], ppy) for t in etfs}}
        if exc is None:
            rec["verdict"] = "INCONCLUSIVE"
        elif exc >= MIN_EXCESS_PP and rec["both_halves_positive"]:
            rec["verdict"] = "BEATS THE CHEAP FACTOR BLEND"
        elif exc < 0:
            rec["verdict"] = "LOSES TO THE CHEAP FACTOR BLEND — the product's claim must change"
        else:
            rec["verdict"] = "NULL — margin not demonstrated"
        out["blends"][label] = rec

        print(f"\n  [{label}]  {rec['window'][0]} -> {rec['window'][1]}  n={len(idx)}")
        print(f"    strategy gross {_fmt(a_gross)}  net {_fmt(a_net)}  "
              f"(cost drag {_fmt(rec['strategy_cost_drag_ann'])})")
        print(f"    blend {_fmt(a_blend)}   SPY {_fmt(a_spy)}   EW universe {_fmt(a_ew)}")
        for t in etfs:
            print(f"      {t:5s} {_fmt(rec['per_etf_ann'][t])}")
        print(f"    EXCESS vs blend {_fmt(exc)}  (bar +2.00%)  "
              f"halves {_fmt(e1)} / {_fmt(e2)}  both+={rec['both_halves_positive']}")
        print(f"    -> {rec['verdict']}")

    evaluate("matched_4factor", MATCHED)
    evaluate("long_history_2factor", LONG_HISTORY)

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    strat.to_csv(args.json.replace(".json", "_strategy_series.csv"))
    print(f"\n[X4] -> {args.json}")
    print("[X4] strategy per-period series also written — R1 needs exactly this object.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
