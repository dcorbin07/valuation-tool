#!/usr/bin/env python3
"""V6-OPT premise probe — what data exists, BEFORE any register is written.

Every number this prints is a fact about the repository's own caches and about the
coverage of an already-decided population (V6-B's dips). Nothing here is a hypothesis
and nothing is scored against a threshold, so it charges NO trial (S25's precedent).

It exists because the previous session's `U6` memo asserted a blocker -- "the cache is
100% calls, so no put-chain history exists to replay a CSP against" -- and that claim
is about the TRADED BOOK, not the chain cache. This measures the chain cache directly.

    python -m scripts.v6opt_premise --data-dir data/backtest
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# V6's construction, IMPORTED so the floors and the drawdown cannot drift (V6-B void 6.3).
from scripts.v6_dip_detector import (HEALTH_FLOOR, QUALITY_FLOOR,          # noqa: E402
                                     health_panel, trailing_drawdown)

ROOT = r"C:/Users/donni/Downloads/valuation-tool"
PANEL = os.path.join(ROOT, "data/free_analysis/panel_v6.pkl")
CHAINS = os.path.join(ROOT, "data/options")
DERIVED = os.path.join(ROOT, "data/options_derived")
OUT = os.path.join(ROOT, "data/free_analysis/V6OPT_PREMISE.json")
DIPS_CACHE = os.path.join(ROOT, "data/free_analysis/V6OPT_DIPS.pkl")

DEPTH = 0.20          # V6-B's dip population, unchanged


def _log(m):
    print(m, flush=True)


def _years(root):
    """{ticker: [years]} for a per-ticker/<TICKER>-<YEAR>.pkl cache."""
    out = {}
    for t in sorted(os.listdir(root)):
        p = os.path.join(root, t)
        if not os.path.isdir(p):
            continue
        out[t] = sorted(f.rsplit("-", 1)[-1].split(".")[0]
                        for f in os.listdir(p) if f.endswith(".pkl"))
    return out


def put_call_mix(root, years, n=40, seed=0):
    """Is the CHAIN cache calls-only? Measured, not inferred from the traded book."""
    rng = np.random.default_rng(seed)
    cands = [t for t, v in years.items() if v]
    pick = rng.choice(cands, size=min(n, len(cands)), replace=False)
    rows = []
    for t in pick:
        ys = [y for y in years[t] if y.isdigit()]
        if not ys:
            continue
        y = ys[len(ys) // 2]
        try:
            d = pd.read_pickle(os.path.join(root, t, f"{t}-{y}.pkl"))
        except Exception:
            continue
        vc = d["right"].value_counts()
        rows.append({"ticker": t, "year": y, "rows": int(len(d)),
                     "calls": int(vc.get("C", 0)), "puts": int(vc.get("P", 0)),
                     "bid_gt0": float((d["bid"] > 0).mean()),
                     "oi_gt0": float((d["open_interest"] > 0).mean())})
    tot_c = sum(r["calls"] for r in rows)
    tot_p = sum(r["puts"] for r in rows)
    return {"n_tickers_sampled": len(rows), "total_calls": tot_c, "total_puts": tot_p,
            "put_share": (tot_p / (tot_c + tot_p)) if (tot_c + tot_p) else None,
            "tickers_with_zero_puts": sum(1 for r in rows if r["puts"] == 0),
            "per_ticker": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    a = ap.parse_args()

    art = {"item": "V6-OPT", "stage": "premise (no register, no hypothesis, zero trials)"}

    # ---------------------------------------------------------------- P1: puts exist?
    _log("[premise] P1 - does the CHAIN cache carry puts?")
    ch_years = _years(CHAINS)
    dv_years = _years(DERIVED)
    art["P1_put_availability"] = {
        "chain_cache_tickers": len(ch_years),
        "derived_cache_tickers": len(dv_years),
        "chains": put_call_mix(CHAINS, ch_years),
    }
    m = art["P1_put_availability"]["chains"]
    _log(f"    chains: {m['total_puts']:,} puts vs {m['total_calls']:,} calls "
         f"across {m['n_tickers_sampled']} tickers; zero-put tickers {m['tickers_with_zero_puts']}")

    # ---------------------------------------------------------------- P2: cache depth
    ch_depth = collections.Counter(len([y for y in v if y.isdigit()]) for v in ch_years.values())
    dv_depth = collections.Counter(len([y for y in v if y.isdigit()]) for v in dv_years.values())
    per_year = collections.Counter()
    for v in dv_years.values():
        for y in v:
            if y.isdigit():
                per_year[y] += 1
    art["P2_depth"] = {
        "chain_years_per_ticker": {str(k): v for k, v in sorted(ch_depth.items())},
        "derived_years_per_ticker": {str(k): v for k, v in sorted(dv_depth.items())},
        "derived_tickers_per_year": {k: v for k, v in sorted(per_year.items())},
        "derived_ge8y": sum(1 for v in dv_years.values()
                            if len([y for y in v if y.isdigit()]) >= 8),
    }
    _log(f"    derived tickers with >=8 years: {art['P2_depth']['derived_ge8y']}")

    # ---------------------------------------------------------------- the dip population
    if os.path.exists(DIPS_CACHE):
        _log("[premise] dip frame - reusing cache")
        p = pd.read_pickle(DIPS_CACHE)
    else:
        _log("[premise] dip frame - rebuilding with V6's own imported construction")
        panel = pd.read_pickle(PANEL)
        dates = sorted(pd.unique(panel["date"]))
        tickers = sorted(set(panel["ticker"].astype(str)))
        dd = trailing_drawdown(os.path.join(a.data_dir, "prices"), tickers, dates)
        hp = health_panel(a.data_dir, tickers, dates)
        p = panel.merge(dd, on=["date", "ticker"], how="left") \
                 .merge(hp, on=["date", "ticker"], how="left")
        p["_dip"] = pd.to_numeric(p["drawdown"], errors="coerce") <= -DEPTH
        p["_healthy"] = (pd.to_numeric(p["quality"], errors="coerce") > QUALITY_FLOOR) & \
                        (pd.to_numeric(p["health"], errors="coerce") >= HEALTH_FLOOR)
        p.to_pickle(DIPS_CACHE)
    dips = p[p["_dip"]].copy()
    dips["_year"] = dips["date"].astype(str).str[:4]
    _log(f"    panel rows {len(p):,}; dipped rows {len(dips):,}; "
         f"healthy {int(dips['_healthy'].sum()):,}")

    # ---------------------------------------------------------------- P3: dip x surface
    have = {t: set(y for y in v if y.isdigit()) for t, v in dv_years.items()}
    dips["_covered"] = [bool(str(tk) in have and yr in have[str(tk)])
                        for tk, yr in zip(dips["ticker"], dips["_year"])]
    by_date = dips.groupby("date").agg(n=("ticker", "size"), cov=("_covered", "sum"))
    art["P3_dip_coverage"] = {
        "dip_rows": int(len(dips)),
        "dip_rows_covered": int(dips["_covered"].sum()),
        "coverage_frac": float(dips["_covered"].mean()),
        "healthy_dip_rows": int(dips["_healthy"].sum()),
        "healthy_covered": int((dips["_healthy"] & dips["_covered"]).sum()),
        "unhealthy_covered": int((~dips["_healthy"] & dips["_covered"]).sum()),
        "panel_dates": int(p["date"].nunique()),
        "dates_with_any_covered_dip": int((by_date["cov"] > 0).sum()),
        "dates_zero_covered": sorted(str(d)[:10] for d in by_date.index[by_date["cov"] == 0]),
        "covered_per_date_median": float(by_date["cov"].median()),
        "covered_per_date_min": int(by_date["cov"].min()),
        "covered_per_date_max": int(by_date["cov"].max()),
    }
    c = art["P3_dip_coverage"]
    _log(f"    dips covered by the derived surface: {c['dip_rows_covered']:,} of "
         f"{c['dip_rows']:,} = {c['coverage_frac']:.4f}")
    _log(f"    dates with at least one covered dip: {c['dates_with_any_covered_dip']} "
         f"of {c['panel_dates']}")

    # ---------------------------------------------------------------- P4: the size tilt
    mc = pd.to_numeric(dips.get("market_cap"), errors="coerce")
    art["P4_size_tilt"] = {
        "median_mcap_covered": float(mc[dips["_covered"]].median()),
        "median_mcap_uncovered": float(mc[~dips["_covered"]].median()),
        "ratio": float(mc[dips["_covered"]].median() / mc[~dips["_covered"]].median())
        if float(mc[~dips["_covered"]].median()) else None,
        "note": ("V6-B measured M1's separation WEAKEST in megacaps (-3.787pp) and strongest "
                 "in the smallest quintile (-14.287pp). If the covered set is the large end, "
                 "a CSP study can only be built where the risk separation is weakest."),
    }
    _log(f"    median mcap covered {art['P4_size_tilt']['median_mcap_covered']:,.0f} vs "
         f"uncovered {art['P4_size_tilt']['median_mcap_uncovered']:,.0f}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(art, f, indent=2, default=float)
    _log(f"[premise] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
