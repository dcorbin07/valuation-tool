#!/usr/bin/env python3
"""failure_cases.py — read the twenty worst holdings the top decile ever bought.  [S26]

Every statistical test in the audit asks whether the average is positive. None asks WHAT THE
MODEL IS WRONG ABOUT, and models are wrong in patterned rather than random ways — a value tilt
buys value traps, a quality tilt buys peak margins, a momentum tilt buys the top of a run.
Finding the pattern is what produces the next real signal, and averages cannot show it.

Output per case: the full standardized signal vector, every theme score, and the composite at
entry, plus the forward return that followed.

Discipline, pre-registered in PREREG_free_analysis.md:
  * a pattern seen in 20 hand-read cases is a HYPOTHESIS, never a finding
  * the 20 worst are reported against the top decile's OWN loss distribution, so it is visible
    whether they are freak tails or just the left end of an ordinary spread
  * whatever appears is reported, including "no pattern"

Modifies no existing file.

    python -m scripts.failure_cases --panel data/free_analysis/panel.pkl
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

N_WORST = 20


def _num(v):
    """None-safe float: theme columns carry None as well as NaN."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read the twenty worst top-decile holdings (S26).")
    ap.add_argument("--panel", default="data/free_analysis/panel.pkl")
    ap.add_argument("--json", default="data/free_analysis/FAILURE_CASES.json")
    ap.add_argument("--n", type=int, default=N_WORST)
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.screener import settings as S
    from valuation.screener.cross_sectional import zscore

    panel = pd.read_pickle(args.panel)
    panel["date"] = pd.to_datetime(panel["date"])
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}
    themes = [t for t in S.FACTORS_ALL if t in panel.columns]
    zcols = [c for c in panel.columns if str(c).startswith("z_")]

    held = []
    for d, sub in panel.groupby("date"):
        comp = np.zeros(len(sub))
        for c, w in dep.items():
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * w
        ok = np.isfinite(comp) & np.isfinite(sub["fwd_ret"].values)
        s = sub[ok].assign(_comp=comp[ok]).sort_values("_comp", ascending=False)
        if len(s) < 30:
            continue
        held.append(s.head(max(1, len(s) // 10)))
    book = pd.concat(held, ignore_index=True)

    r = book["fwd_ret"]
    dist = {"n_holdings": int(len(book)),
            "mean": float(r.mean()), "median": float(r.median()),
            "std": float(r.std()),
            "pct_negative": float((r < 0).mean()),
            "p01": float(r.quantile(0.01)), "p05": float(r.quantile(0.05)),
            "p10": float(r.quantile(0.10)), "p25": float(r.quantile(0.25)),
            "p75": float(r.quantile(0.75)), "p95": float(r.quantile(0.95)),
            "worst": float(r.min()), "best": float(r.max())}

    print(f"[S26] top-decile holdings: {len(book):,} name-dates over "
          f"{book['date'].nunique()} rebalances")
    print(f"[S26] forward-return distribution (63d): mean {r.mean():+.2%} median "
          f"{r.median():+.2%} sd {r.std():.2%}")
    print(f"      {(r < 0).mean():.1%} negative | p01 {r.quantile(0.01):+.1%} "
          f"p05 {r.quantile(0.05):+.1%} p25 {r.quantile(0.25):+.1%} "
          f"p95 {r.quantile(0.95):+.1%} | worst {r.min():+.1%}")

    worst = book.nsmallest(args.n, "fwd_ret")
    cases = []
    print(f"\n[S26] the {args.n} worst holdings\n" + "=" * 108)
    for _, row in worst.iterrows():
        rec = {"ticker": row["ticker"], "date": str(row["date"].date()),
               "fwd_ret": float(row["fwd_ret"]), "composite": float(row["_comp"]),
               "market_cap": _num(row.get("market_cap")),
               "sector": row.get("sector"),
               "themes": {t: _num(row[t]) for t in themes},
               "signals": {c: _num(row[c]) for c in zcols}}
        cases.append(rec)
        cap = f"${rec['market_cap']/1e6:,.0f}M" if rec["market_cap"] else "n/a"
        print(f"\n{row['ticker']:6s} {rec['date']}  fwd {row['fwd_ret']:+.1%}  "
              f"composite {row['_comp']:+.3f}  cap {cap}  sector {rec['sector']}")
        tt = "  ".join(f"{t[:9]}={rec['themes'][t]:+.2f}" for t in themes
                       if rec["themes"][t] is not None)
        print(f"   themes: {tt}")
        top = sorted([(k, v) for k, v in rec["signals"].items() if v is not None],
                     key=lambda kv: -abs(kv[1]))[:8]
        print(f"   strongest signals: " + "  ".join(f"{k[2:]}={v:+.2f}" for k, v in top))

    # aggregate the 20 against the book, so a "pattern" can be checked rather than asserted
    agg = {}
    for t in themes:
        w = worst[t].dropna(); b = book[t].dropna()
        if len(w) and len(b):
            agg[t] = {"worst20_mean": float(w.mean()), "book_mean": float(b.mean()),
                      "diff": float(w.mean() - b.mean())}
    capw = worst["market_cap"].dropna(); capb = book["market_cap"].dropna()
    print("\n[S26] the 20 worst vs the whole top-decile book (theme means)")
    for t, v in sorted(agg.items(), key=lambda kv: kv[1]["diff"]):
        print(f"   {t:20s} worst {v['worst20_mean']:+.3f}  book {v['book_mean']:+.3f}  "
              f"diff {v['diff']:+.3f}")
    if len(capw) and len(capb):
        print(f"   median market cap: worst20 ${capw.median()/1e6:,.0f}M  "
              f"book ${capb.median()/1e6:,.0f}M  ratio {capw.median()/capb.median():.2f}x")
    print(f"   dates: {sorted(set(str(d.date())[:7] for d in worst['date']))}")

    out = {"item": "S26", "prereg": "PREREG_free_analysis.md",
           "loss_distribution": dist, "worst_cases": cases,
           "worst20_vs_book_theme_means": agg,
           "worst20_median_mktcap": (float(capw.median()) if len(capw) else None),
           "book_median_mktcap": (float(capb.median()) if len(capb) else None),
           "note": "Hypothesis-generating only. A pattern in 20 hand-read cases is not a "
                   "finding and must clear holdout_theme_validate() before touching a weight."}
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\n[S26] -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
