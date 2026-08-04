#!/usr/bin/env python3
"""capacity.py — at what AUM does this strategy stop working?  [P1]

The book is 25 names with a deliberate small-cap tilt at ~251% annual turnover, and the shipped
cost model is keyed on market cap with NO PARTICIPATION-RATE TERM AT ALL. That is fine for one
personal account and is not obviously fine for a product. Capacity determines whether Valquo can
ever be a managed vehicle or must stay a research tool users implement themselves — a strategic
question that is much cheaper to answer before launch than after.

DATA FINDING, recorded because it changes the method: the audit says "the ADV data is in SEP,
already on disk." IT IS NOT. SEP is not on disk in any form — the bulk extracts are ACTIONS,
DAILY, EVENTS and SF3, none of which carries volume, and the per-ticker price CSVs are
`date,close` only. The only volume on disk is data/bulk/prepared/bars/*.pkl: 290 large-cap names
from the options miner, covering ~3.5% of the top-25 book's 918 distinct names.

So ADV comes from, in order: (1) bars/ where present, (2) yfinance, (3) a market-cap proxy
calibrated on (1)+(2) for names neither covers. The split is reported, never hidden.

BIAS, pre-registered: sources (1) and (2) are survivorship-biased — delisted names are exactly
the ones that vanish, and survivors are larger and more liquid. EVERY CAPACITY NUMBER HERE IS AN
UPPER BOUND.

Modifies no existing file.

    python -m scripts.capacity --panel data/free_analysis/panel.pkl
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

AUMS = [1e6, 10e6, 50e6, 250e6, 1e9]
BREAKEVEN_BPS = 234.505            # costs.breakeven_one_way_bps, the project's own measurement
LAMBDAS = [0.5, 1.0, 2.0]          # square-root impact coefficient; 1.0 is the headline
TOP_N = 25
TRADING_DAYS = 63                  # ADV window before each rebalance


def _fmt_usd(x):
    for u, d in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= d:
            return f"${x/d:,.1f}{u}"
    return f"${x:,.0f}"


def load_book(panel, top_n=TOP_N):
    import pandas as pd
    from valuation.screener import settings as S
    from valuation.screener.cross_sectional import zscore

    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}
    out = []
    for d, sub in panel.groupby("date"):
        c = np.zeros(len(sub))
        for col, w in dep.items():
            z = zscore(sub[col]).values
            c = c + np.where(np.isnan(z), 0.0, z) * w
        ok = np.isfinite(c) & np.isfinite(sub["fwd_ret"].values)
        s = sub[ok].assign(_c=c[ok]).sort_values("_c", ascending=False)
        if len(s) < 30:
            continue
        out.append(s.head(top_n)[["date", "ticker", "market_cap", "fwd_ret"]])
    return pd.concat(out, ignore_index=True)


def adv_from_bars(tickers, bars_dir="data/bulk/prepared/bars"):
    """Dollar ADV series per ticker from the miner's cached bars."""
    import pandas as pd
    out = {}
    if not os.path.isdir(bars_dir):
        return out
    have = {f[:-4] for f in os.listdir(bars_dir)}
    for t in tickers:
        if t not in have:
            continue
        try:
            b = pd.read_pickle(os.path.join(bars_dir, f"{t}.pkl"))
            s = pd.DataFrame({"date": pd.to_datetime(b["date"]),
                              "dv": np.asarray(b["raw_close"], dtype=float)
                                    * np.asarray(b["volume"], dtype=float)}).set_index("date")["dv"]
            out[t] = s[s > 0]
        except Exception:
            continue
    return out


def adv_from_yf(tickers, chunk=120):
    """Dollar ADV from yfinance. Delisted names simply fail — that is the survivorship bias."""
    import pandas as pd
    import yfinance as yf
    out = {}
    tl = sorted(tickers)
    for i in range(0, len(tl), chunk):
        part = tl[i:i + chunk]
        try:
            d = yf.download(part, start="1997-01-01", end="2026-08-01", auto_adjust=False,
                            progress=False, threads=True)
        except Exception:
            continue
        if d is None or d.empty:
            continue
        try:
            cl, vo = d["Close"], d["Volume"]
        except Exception:
            continue
        if isinstance(cl, pd.Series):
            cl, vo = cl.to_frame(part[0]), vo.to_frame(part[0])
        for t in cl.columns:
            s = (cl[t] * vo[t]).dropna()
            s = s[s > 0]
            if len(s) > 60:
                s.index = pd.to_datetime(s.index).tz_localize(None)
                out[t] = s
        print(f"    yfinance {min(i+chunk, len(tl))}/{len(tl)} … {len(out)} with volume",
              flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Estimate strategy capacity (P1).")
    ap.add_argument("--panel", default="data/free_analysis/panel.pkl")
    ap.add_argument("--json", default="data/free_analysis/CAPACITY_RESULTS.json")
    ap.add_argument("--no-yf", action="store_true")
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.edge.fundamental_panel import one_way_cost_bps

    panel = pd.read_pickle(args.panel)
    panel["date"] = pd.to_datetime(panel["date"])
    book = load_book(panel)
    names = sorted(book["ticker"].unique())
    print(f"[P1] top-{TOP_N} book: {len(book)} positions, {len(names)} distinct names, "
          f"{book['date'].nunique()} rebalances", flush=True)

    adv = adv_from_bars(names)
    print(f"[P1] ADV from local bars: {len(adv)}/{len(names)} names", flush=True)
    if not args.no_yf:
        missing = [t for t in names if t not in adv]
        print(f"[P1] fetching {len(missing)} from yfinance …", flush=True)
        adv.update(adv_from_yf(missing))
    print(f"[P1] ADV real coverage: {len(adv)}/{len(names)} names "
          f"({len(adv)/len(names)*100:.1f}%)", flush=True)

    # daily vol per name, from the close-only price CSVs (full universe coverage)
    vol = {}
    for t in names:
        f = f"data/backtest/prices/{t}.csv"
        if os.path.exists(f):
            try:
                s = pd.read_csv(f, parse_dates=["date"]).set_index("date")["close"]
                r = s.pct_change().dropna()
                if len(r) > 60:
                    vol[t] = r
            except Exception:
                pass

    # per-position ADV at entry: mean dollar volume over the 63 days BEFORE the rebalance
    rows = []
    for _, p in book.iterrows():
        t, d = p["ticker"], p["date"]
        a = np.nan
        if t in adv:
            s = adv[t]
            w = s[(s.index <= d)].tail(TRADING_DAYS)
            if len(w) >= 20:
                a = float(w.mean())
        sd = np.nan
        if t in vol:
            w = vol[t][vol[t].index <= d].tail(252)
            if len(w) >= 60:
                sd = float(w.std())
        rows.append({"date": d, "ticker": t, "mktcap": p["market_cap"],
                     "adv": a, "sigma_d": sd})
    df = pd.DataFrame(rows)
    real = df["adv"].notna()
    print(f"[P1] positions with real ADV at entry: {real.sum()}/{len(df)} "
          f"({real.mean()*100:.1f}%)", flush=True)

    # calibrate log(ADV) ~ a + b log(mktcap) on the covered positions, to fill the rest
    m = df["adv"].notna() & df["mktcap"].notna() & (df["mktcap"] > 0)
    b1, b0 = np.polyfit(np.log(df.loc[m, "mktcap"]), np.log(df.loc[m, "adv"]), 1)
    pred = np.exp(b0 + b1 * np.log(df["mktcap"].where(df["mktcap"] > 0)))
    resid = np.log(df.loc[m, "adv"]) - np.log(pred[m])
    r2 = 1 - resid.var() / np.log(df.loc[m, "adv"]).var()
    df["adv_filled"] = df["adv"].fillna(pred)
    df["adv_is_proxy"] = df["adv"].isna()
    print(f"[P1] ADV proxy log-log fit: log(ADV) = {b0:.2f} + {b1:.3f}·log(mktcap), "
          f"R²={r2:.3f}, n={int(m.sum())}", flush=True)
    print(f"[P1] median dollar ADV in book: {_fmt_usd(np.nanmedian(df['adv_filled']))}; "
          f"median mktcap {_fmt_usd(np.nanmedian(df['mktcap']))}", flush=True)

    med_sigma = float(np.nanmedian(df["sigma_d"]))
    df["sigma_d"] = df["sigma_d"].fillna(med_sigma)
    df["base_bps"] = [one_way_cost_bps(c) for c in df["mktcap"]]

    out = {"item": "P1", "prereg": "PREREG_free_analysis.md",
           "breakeven_one_way_bps": BREAKEVEN_BPS, "top_n": TOP_N,
           "n_positions": int(len(df)), "n_names": len(names),
           "adv_real_coverage": float(real.mean()),
           "adv_proxy_fit": {"intercept": float(b0), "slope": float(b1), "r2": float(r2),
                             "n": int(m.sum())},
           "median_adv_usd": float(np.nanmedian(df["adv_filled"])),
           "median_sigma_daily": med_sigma,
           "sep_on_disk": False,
           "bias": "UPPER BOUND — ADV sources are survivorship-biased toward larger survivors.",
           "by_aum": {}, "capacity": {}}

    print(f"\n[P1] participation and cost by AUM (λ=1.0)")
    print(f"{'AUM':>8s} {'pos/name':>10s} {'med part':>9s} {'>5%ADV':>8s} {'>10%ADV':>8s} "
          f"{'cost bps':>9s} {'vs 234.5':>9s}")
    for aum in AUMS:
        pos = aum / TOP_N
        part = pos / df["adv_filled"]
        rec = {"position_usd": pos, "median_participation": float(np.nanmedian(part)),
               "share_over_5pct_adv": float((part > 0.05).mean()),
               "share_over_10pct_adv": float((part > 0.10).mean()),
               "n_over_10pct_adv": int((part > 0.10).sum())}
        for lam in LAMBDAS:
            cost = df["base_bps"] + lam * df["sigma_d"] * np.sqrt(part.clip(0, None)) * 1e4
            rec[f"mean_cost_bps_lambda{lam}"] = float(np.nanmean(cost))
        c1 = rec["mean_cost_bps_lambda1.0"]
        out["by_aum"][f"{aum:.0f}"] = rec
        print(f"{_fmt_usd(aum):>8s} {_fmt_usd(pos):>10s} {rec['median_participation']*100:8.2f}% "
              f"{rec['share_over_5pct_adv']*100:7.1f}% {rec['share_over_10pct_adv']*100:7.1f}% "
              f"{c1:9.1f} {'OVER' if c1 > BREAKEVEN_BPS else 'under':>9s}")

    # capacity: solve for the AUM where mean modelled cost == breakeven
    print(f"\n[P1] capacity — AUM at which modelled one-way cost hits {BREAKEVEN_BPS:.0f} bps")
    for lam in LAMBDAS:
        lo, hi = 1e5, 1e12
        for _ in range(80):
            mid = np.sqrt(lo * hi)
            part = (mid / TOP_N) / df["adv_filled"]
            c = float(np.nanmean(df["base_bps"] + lam * df["sigma_d"]
                                 * np.sqrt(part.clip(0, None)) * 1e4))
            if c < BREAKEVEN_BPS:
                lo = mid
            else:
                hi = mid
        out["capacity"][f"lambda{lam}"] = float(np.sqrt(lo * hi))
        tag = " <- headline" if lam == 1.0 else ""
        print(f"   λ={lam:<4} capacity ≈ {_fmt_usd(np.sqrt(lo*hi))}{tag}")

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\n[P1] -> {args.json}")
    print("[P1] Every number above is an UPPER BOUND (survivorship-biased ADV).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
