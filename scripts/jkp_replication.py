#!/usr/bin/env python3
"""jkp_replication.py — does the theme structure survive a different vendor and country?  [X8]

The deepest unaddressed risk in the equity programme is that every signal, IC and verdict rests
on ONE vendor's construction of ONE country's fundamentals over ONE window. This item attacks all
four at once using Global Factor Data (jkpfactors.com): 13 themes across 93 countries, built from
an entirely different pipeline.

The question, and nothing more than it: does a composite with the SAME theme structure and the
SAME equal weights earn a positive premium in Japan and developed Europe? NOTHING IS TUNED — the
value of this test is entirely in the absence of tuning.

  Valquo theme        JKP theme      Valquo theme        JKP theme
  value               value          size                size
  quality             quality        capital_discipline  investment
  momentum            momentum       insider/institutional   NO ANALOGUE (excluded)

Five of seven map, so this validates 5/7 of the composite's weight. The two that do not map are
the same two X4 found have no retail ETF analogue: the part of the model a user cannot buy is
also the part that cannot be externally validated.

JKP theme factors are LONG-SHORT, so the comparable Valquo statistic is its long-short t of 3.52,
NOT its +11.88% top-decile alpha. Do not mix them.

LICENCE: CC BY-NC 4.0 — RESEARCH ONLY. This validates the model; it can never ship in the
product. Everything lands under data/factors/research_only/.

Thresholds pre-registered in PREREG_free_analysis.md. Modifies no existing file.

    python -m scripts.jkp_replication
"""
from __future__ import annotations

import argparse
import io
import json
import os
import urllib.request
import zipfile

import numpy as np

S3 = "https://jkpfactors-data.s3.amazonaws.com"
UA = {"User-Agent": "Mozilla/5.0 (valquo-research; X8 replication)"}

THEME_MAP = {"value": "value", "quality": "quality", "momentum": "momentum",
             "size": "size", "capital_discipline": "investment"}
NO_ANALOGUE = ["insider", "institutional"]

EUROPE = ["gbr", "deu", "fra", "ita", "esp", "nld", "che", "swe",
          "dnk", "nor", "fin", "bel", "aut", "irl", "prt"]
CONTROLS = ["usa", "world_ex_us", "developed"]

MATCHED_START, MATCHED_END = "1999-01-01", "2026-04-30"
MIN_T = 2.0
NW_LAGS = 12

# secondary monotonicity arm — one characteristic per theme, fixed in advance
MONO_CHARS = {"value": "be_me", "quality": "qmj", "momentum": "ret_12_1",
              "size": "market_equity", "capital_discipline": "at_gr1"}


def _get_zip_csv(path: str, cache_dir: str):
    os.makedirs(cache_dir, exist_ok=True)
    fn = os.path.join(cache_dir, path.split("/")[-1].replace("%5B", "[").replace("%5D", "]"))
    if os.path.exists(fn):
        with open(fn, "rb") as f:
            blob = f.read()
    else:
        r = urllib.request.urlopen(urllib.request.Request(S3 + path, headers=UA), timeout=120)
        blob = r.read()
        with open(fn, "wb") as f:
            f.write(blob)
    z = zipfile.ZipFile(io.BytesIO(blob))
    return z.read(z.namelist()[0]).decode("utf-8", "ignore")


def load_themes(region: str, cache_dir: str):
    import pandas as pd
    p = f"/public/%5B{region}%5D_%5Ball_themes%5D_%5Bmonthly%5D_%5Bvw_cap%5D.zip"
    df = pd.read_csv(io.StringIO(_get_zip_csv(p, cache_dir)))
    df["date"] = pd.to_datetime(df["date"])
    return df


def nw_tstat(x, lags=NW_LAGS):
    """Newey-West t on the mean. Monthly factor returns are autocorrelated; OLS t overstates."""
    x = np.asarray([v for v in x if v == v], dtype=float)
    n = len(x)
    if n < 24:
        return None, None, n
    mu = x.mean()
    e = x - mu
    g0 = (e @ e) / n
    var = g0
    for L in range(1, min(lags, n - 1) + 1):
        g = (e[L:] @ e[:-L]) / n
        var += 2.0 * (1.0 - L / (lags + 1.0)) * g
    se = np.sqrt(max(var, 1e-18) / n)
    return float(mu), float(mu / se), n


def composite_series(df, start=None, end=None):
    """Equal-weighted mean of the five mapped theme factor returns, per month."""
    import pandas as pd
    d = df[df["name"].isin(THEME_MAP.values())].copy()
    if start:
        d = d[d["date"] >= pd.Timestamp(start)]
    if end:
        d = d[d["date"] <= pd.Timestamp(end)]
    w = d.pivot_table(index="date", columns="name", values="ret", aggfunc="mean")
    have = [c for c in THEME_MAP.values() if c in w.columns]
    w = w[have].dropna(how="all")
    return w.mean(axis=1), w


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JKP international replication (X8).")
    ap.add_argument("--dest", default="data/factors/research_only/jkp")
    ap.add_argument("--json", default="data/free_analysis/JKP_REPLICATION.json")
    ap.add_argument("--skip-mono", action="store_true")
    args = ap.parse_args(argv)

    import pandas as pd

    cache = args.dest
    os.makedirs(cache, exist_ok=True)
    with open(os.path.join(cache, "LICENCE.txt"), "w") as f:
        f.write("Global Factor Data (jkpfactors.com) — CC BY-NC 4.0, NON-COMMERCIAL ONLY.\n"
                "Research validation only. Product code must never read this directory.\n"
                "Cite: Jensen, Kelly & Pedersen, 'Is There a Replication Crisis in Finance?', "
                "Journal of Finance (2023).\n")

    out = {"item": "X8", "prereg": "PREREG_free_analysis.md",
           "licence": "CC BY-NC 4.0 — research only, never shipped",
           "theme_map": THEME_MAP, "no_analogue": NO_ANALOGUE,
           "weighting": "vw_cap", "frequency": "monthly",
           "matched_window": [MATCHED_START, MATCHED_END],
           "min_t": MIN_T, "nw_lags": NW_LAGS,
           "europe_countries": EUROPE, "regions": {}}

    def evaluate(label, df, start, end, tag):
        comp, wide = composite_series(df, start, end)
        if comp.empty:
            return {"status": "no data"}
        mu, t, n = nw_tstat(comp.values)
        rec = {"n_months": n, "mean_monthly": mu,
               "ann_return": (None if mu is None else (1 + mu) ** 12 - 1),
               "nw_t": t, "themes_present": list(wide.columns),
               "window": [str(comp.index.min().date()), str(comp.index.max().date())],
               "per_theme": {}}
        for c in wide.columns:
            m2, t2, n2 = nw_tstat(wide[c].dropna().values)
            rec["per_theme"][c] = {"mean_monthly": m2, "ann": (None if m2 is None else
                                                               (1 + m2) ** 12 - 1),
                                   "nw_t": t2, "n": n2}
        print(f"  {label:22s} [{tag}] n={n:4d}  ann={rec['ann_return']*100:+6.2f}%  "
              f"NW t={t:+5.2f}", flush=True)
        pt = "  ".join(f"{c[:6]}={rec['per_theme'][c]['nw_t']:+.2f}" for c in wide.columns)
        print(f"      per-theme t: {pt}", flush=True)
        return rec

    # ---- controls + Japan -------------------------------------------------------------
    print("[X8] matched window "
          f"{MATCHED_START} -> {MATCHED_END} (5 themes, equal-weighted, untuned)", flush=True)
    dfs = {}
    for reg in CONTROLS + ["jpn"]:
        try:
            dfs[reg] = load_themes(reg, cache)
        except Exception as e:
            print(f"  {reg}: FETCH FAILED {type(e).__name__}", flush=True)
            continue
        out["regions"][reg] = {
            "matched": evaluate(reg, dfs[reg], MATCHED_START, MATCHED_END, "matched"),
            "full": evaluate(reg, dfs[reg], None, None, "full"),
        }

    # ---- developed Europe: equal-weighted across the committed country list -----------
    print("\n[X8] developed Europe (equal-weighted across "
          f"{len(EUROPE)} committed countries)", flush=True)
    eu_comp, eu_ok, eu_fail = {}, [], []
    for c in EUROPE:
        try:
            d = load_themes(c, cache)
            s, _ = composite_series(d, MATCHED_START, MATCHED_END)
            if len(s) >= 24:
                eu_comp[c] = s
                eu_ok.append(c)
            else:
                eu_fail.append(c)
        except Exception:
            eu_fail.append(c)
    print(f"  countries with data: {len(eu_ok)}/{len(EUROPE)}  missing={eu_fail}", flush=True)

    eu = pd.DataFrame(eu_comp)
    eu_series = eu.mean(axis=1)
    mu, t, n = nw_tstat(eu_series.values)
    out["regions"]["europe_developed"] = {
        "matched": {"n_months": n, "mean_monthly": mu,
                    "ann_return": (None if mu is None else (1 + mu) ** 12 - 1), "nw_t": t,
                    "countries_used": eu_ok, "countries_missing": eu_fail,
                    "window": [str(eu_series.index.min().date()),
                               str(eu_series.index.max().date())],
                    "per_country_ann": {c: float((1 + eu[c].mean()) ** 12 - 1) for c in eu_ok},
                    "per_country_t": {c: nw_tstat(eu[c].dropna().values)[1] for c in eu_ok}}}
    print(f"  EUROPE composite   n={n}  ann={(1+mu)**12*100-100:+6.2f}%  NW t={t:+5.2f}",
          flush=True)

    # ---- verdict, against the pre-registered bar only ---------------------------------
    jp = (out["regions"].get("jpn") or {}).get("matched") or {}
    eu_m = out["regions"]["europe_developed"]["matched"]
    us = (out["regions"].get("usa") or {}).get("matched") or {}

    jt, et = jp.get("nw_t"), eu_m.get("nw_t")
    jm, em = jp.get("mean_monthly"), eu_m.get("mean_monthly")
    v = {"usa_control_t": us.get("nw_t"), "japan_t": jt, "europe_t": et}

    if us.get("mean_monthly") is not None and us["mean_monthly"] <= 0:
        v["verdict"] = "VOID — the USA control is not positive; the theme mapping is wrong"
    elif None in (jt, et):
        v["verdict"] = "INCONCLUSIVE — a required region did not compute"
    elif jm > 0 and em > 0 and jt > MIN_T and et > MIN_T:
        v["verdict"] = "REPLICATES — positive and significant in both Japan and developed Europe"
    elif jm > 0 and em > 0:
        v["verdict"] = "PARTIAL — direction confirmed in both, significance not"
    else:
        neg = [k for k, m in (("Japan", jm), ("Europe", em)) if m is not None and m <= 0]
        v["verdict"] = f"DOES NOT REPLICATE in {', '.join(neg)} — the edge is US-specific there"
    out["verdict"] = v
    print(f"\n[X8] USA control t={v['usa_control_t']}  Japan t={jt}  Europe t={et}")
    print(f"[X8] VERDICT: {v['verdict']}")

    # ---- secondary: decile monotonicity, descriptive only ------------------------------
    if not args.skip_mono:
        print("\n[X8] secondary monotonicity arm (descriptive, does not change the verdict)")
        out["monotonicity"] = {}
        for reg in ["jpn", "usa"]:
            out["monotonicity"][reg] = {}
            for theme, ch in MONO_CHARS.items():
                try:
                    p = (f"/public/portfolios/%5B{reg}%5D_%5B{ch}%5D_"
                         f"%5Bmonthly%5D_%5Bvw_cap%5D.zip")
                    d = pd.read_csv(io.StringIO(_get_zip_csv(p, cache)))
                    d["date"] = pd.to_datetime(d["date"])
                    d = d[(d["date"] >= pd.Timestamp(MATCHED_START))
                          & (d["date"] <= pd.Timestamp(MATCHED_END))]
                    g = d.groupby("pf")["ret"].mean().sort_index()
                    rho = float(pd.Series(g.values).corr(pd.Series(range(len(g))),
                                                         method="spearman"))
                    out["monotonicity"][reg][theme] = {
                        "characteristic": ch, "n_portfolios": int(len(g)),
                        "decile_mean_monthly": [float(x) for x in g.values],
                        "spearman_rank_vs_return": rho}
                    print(f"   {reg} {theme:20s} ({ch:14s}) spearman={rho:+.2f} "
                          f"pf1={g.values[0]*100:+.2f}%/mo pf{len(g)}={g.values[-1]*100:+.2f}%/mo",
                          flush=True)
                except Exception as e:
                    out["monotonicity"][reg][theme] = {"error": f"{type(e).__name__}"}
                    print(f"   {reg} {theme:20s} FAILED {type(e).__name__}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\n[X8] -> {args.json}")
    print("[X8] JKP data is CC BY-NC 4.0 — research only, never shipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
