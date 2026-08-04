#!/usr/bin/env python3
"""breaks.py — Bai-Perron structural-break test on the theme IC series.  [X6]

The project's two most important decay stories — the options edge fading, and `size` flipping
t +3.17 -> -0.67 "around 2012" — are both handled by splitting the sample at its midpoint,
which is the crudest possible response. Splitting at the midpoint cannot tell a genuine regime
change from gradual drift, and those have DIFFERENT remedies: a break argues for excluding or
down-weighting a regime, drift argues for an exponentially-weighted estimator (S27). The
project currently applies neither because it has never established which case it is in.

Method, pre-registered in PREREG_free_analysis.md:

  * series   per-rebalance-date cross-sectional Spearman IC, one per theme, plus the composite
  * test     Bai-Perron sequential supF(l+1|l), trimming eps=0.15, max 3 breaks, mean-shift
  * crit     NOT the published table. A stationary block bootstrap UNDER THE NULL OF NO BREAK
             (5,000 reps, mean block 4) generates each series' own null, preserving its own
             autocorrelation and non-normality. The published eps=0.15/q=1 value of 8.58 is
             reported alongside as a cross-check.
  * BREAK    supF(1|0) > bootstrap 95th pct AND break-date 90% CI <= 1/3 of the sample
  * DRIFT    first arm passes, second fails -> the date is not identified; remedy is S27
  * NULL     otherwise
  * multiplicity: Holm-Bonferroni across the themes tested

Stated in advance: with ~110 dates and IC series this noisy, POWER IS LOW and a null is the
expected outcome for most themes. A null means "keep the full sample". It does NOT mean
"nothing changed" and must not be written up as evidence of stability.

Modifies no existing file.

    python -m scripts.breaks --panel data/free_analysis/panel.pkl \
        --json data/free_analysis/BREAKS_RESULTS.json
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

EPS = 0.15          # trimming: each regime holds >= 15% of the sample
MAX_BREAKS = 3
N_BOOT = 5000
MEAN_BLOCK = 4
PUBLISHED_SUPF_CRIT_5PCT = 8.58     # Bai-Perron (2003), q=1, eps=0.15, supF(1|0)


# ------------------------------------------------------------------ the test

def _ssr_mean(y: np.ndarray) -> float:
    """SSR of a constant fit — the mean-shift model's per-regime loss."""
    return float(((y - y.mean()) ** 2).sum()) if len(y) else 0.0


def _best_single_break(y: np.ndarray, h: int):
    """Least-squares single break: the split minimising total SSR, respecting trimming."""
    n = len(y)
    best, best_ssr = None, np.inf
    for b in range(h, n - h + 1):
        s = _ssr_mean(y[:b]) + _ssr_mean(y[b:])
        if s < best_ssr:
            best, best_ssr = b, s
    return best, best_ssr


def _supf_1_0(y: np.ndarray, h: int):
    """supF statistic for one break vs none, mean-shift model (q=1).

        F(b) = (SSR_0 - SSR_1(b)) / (SSR_1(b) / (n - 2))
    """
    n = len(y)
    if n < 2 * h + 2:
        return None, None
    ssr0 = _ssr_mean(y)
    b, ssr1 = _best_single_break(y, h)
    if b is None or ssr1 <= 0:
        return None, None
    return float((ssr0 - ssr1) / (ssr1 / (n - 2))), int(b)


def _parametric_null(n: int, h: int, n_boot: int, rng) -> np.ndarray:
    """supF(1|0) null from fresh i.i.d. normal draws.

    Kept as a floor under the block bootstrap. MEASURED, not assumed: at n=110, h=16 this
    returns a 95th percentile of ~8.8, converging to ~8.2 by n=500 against Bai-Perron's
    published 8.58 — i.e. the statistic implemented here IS the textbook one.
    """
    out = np.empty(n_boot)
    for i in range(n_boot):
        s, _ = _supf_1_0(rng.normal(size=n), h)
        out[i] = s if s is not None else 0.0
    return out


def _block_bootstrap_null(y: np.ndarray, h: int, n_boot: int, rng) -> np.ndarray:
    """Null distribution of supF(1|0) for THIS series.

    Resampling the DEMEANED series in blocks imposes the null of no break (one common mean)
    while preserving the series' autocorrelation and fat tails. A published critical value
    assumes i.i.d. normal errors, which an IC series is not.
    """
    n = len(y)
    d = y - y.mean()
    p = 1.0 / MEAN_BLOCK
    stats = np.empty(n_boot)
    for i in range(n_boot):
        out, pos = [], rng.integers(0, n)
        while len(out) < n:                       # stationary bootstrap: geometric blocks
            out.append(d[pos % n])
            pos = rng.integers(0, n) if rng.random() < p else pos + 1
        s, _ = _supf_1_0(np.asarray(out[:n]), h)
        stats[i] = s if s is not None else 0.0
    return stats


def _break_date_ci(y: np.ndarray, h: int, b: int, n_boot: int, rng, level: float = 0.90):
    """Bootstrap CI for the break DATE: resample residuals within each regime, re-estimate."""
    n = len(y)
    m1, m2 = y[:b].mean(), y[b:].mean()
    r = np.concatenate([y[:b] - m1, y[b:] - m2])
    locs = []
    for _ in range(n_boot):
        rs = rng.choice(r, size=n, replace=True)
        sim = np.concatenate([np.full(b, m1), np.full(n - b, m2)]) + rs
        bb, _ = _best_single_break(sim, h)
        if bb is not None:
            locs.append(bb)
    if not locs:
        return None, None
    lo = float(np.percentile(locs, 100 * (1 - level) / 2))
    hi = float(np.percentile(locs, 100 * (1 + level) / 2))
    return lo, hi


def _sequential(y: np.ndarray, h: int, rng, n_boot: int, max_breaks: int):
    """Sequential supF(l+1|l): find a break, split, test each segment, repeat."""
    found, segs = [], [(0, len(y))]
    for _ in range(max_breaks):
        cand = None
        for (a, b) in segs:
            seg = y[a:b]
            if len(seg) < 2 * h + 2:
                continue
            s, loc = _supf_1_0(seg, h)
            if s is None:
                continue
            crit = float(np.percentile(_block_bootstrap_null(seg, h, max(400, n_boot // 10), rng), 95))
            if s > crit and (cand is None or s > cand[0]):
                cand = (s, a + loc, a, b, crit)
        if cand is None:
            break
        s, gl, a, b, crit = cand
        found.append({"index": int(gl), "supF": float(s), "boot_crit_95": crit})
        segs = [x for x in segs if x != (a, b)] + [(a, gl), (gl, b)]
    return found


# ------------------------------------------------------------------ series

def theme_ic_series(panel, themes, horizon_col="fwd_ret", min_names=20):
    """Per-date cross-sectional Spearman IC — the series Bai-Perron runs on."""
    import pandas as pd
    from valuation.edge.fundamental_panel import _spearman

    rows = []
    for d, sub in panel.groupby("date"):
        rec = {"date": d}
        for t in themes:
            if t not in sub.columns:
                continue
            ss = sub.dropna(subset=[t, horizon_col])
            if len(ss) >= min_names:
                ic = _spearman(ss[t].values, ss[horizon_col].values)
                rec[t] = ic if ic == ic else np.nan
            else:
                rec[t] = np.nan
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bai-Perron structural-break test (X6).")
    ap.add_argument("--panel", default="data/free_analysis/panel.pkl")
    ap.add_argument("--json", default="data/free_analysis/BREAKS_RESULTS.json")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.screener import settings as S

    rng = np.random.default_rng(20260803)
    panel = pd.read_pickle(args.panel)
    panel["date"] = pd.to_datetime(panel["date"])    # the panel stores dates as strings
    themes = [t for t in S.FACTORS_ALL if t in panel.columns]

    # the deployed composite, as its own series
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}
    panel = panel.copy()
    from valuation.screener.cross_sectional import zscore
    comp = np.zeros(len(panel))
    for d in panel["date"].unique():
        m = (panel["date"] == d).values
        c = np.zeros(int(m.sum()))
        for col, w in dep.items():
            z = zscore(panel.loc[m, col]).values
            c = c + np.where(np.isnan(z), 0.0, z) * w
        comp[m] = c
    panel["__composite"] = comp

    ser = theme_ic_series(panel, themes + ["__composite"])
    print(f"[X6] {len(ser)} dates, {ser['date'].min().date()} -> {ser['date'].max().date()}",
          flush=True)

    out = {"item": "X6", "n_dates": int(len(ser)),
           "date_min": str(ser["date"].min().date()), "date_max": str(ser["date"].max().date()),
           "params": {"trim_eps": EPS, "max_breaks": MAX_BREAKS, "n_boot": args.boot,
                      "mean_block": MEAN_BLOCK,
                      "published_supF_crit_5pct": PUBLISHED_SUPF_CRIT_5PCT},
           "prereg": "PREREG_free_analysis.md", "series": {}}

    pvals = {}
    for t in themes + ["__composite"]:
        if t not in ser.columns:
            continue
        s = ser[["date", t]].dropna()
        y = s[t].values.astype(float)
        n = len(y)
        h = max(2, int(np.floor(EPS * n)))
        if n < 2 * h + 2:
            out["series"][t] = {"status": f"too few dates ({n})"}
            continue

        stat, b = _supf_1_0(y, h)
        if stat is None:
            out["series"][t] = {"status": "supF did not compute", "n": n}
            continue
        null = _block_bootstrap_null(y, h, args.boot, rng)
        boot95 = float(np.percentile(null, 95))
        # The block bootstrap is ANTI-CONSERVATIVE here and this was measured, not assumed:
        # fed i.i.d. normal data at n=110 it returns a 95th percentile of ~6.3 against the
        # correct ~8.8, so used alone it would over-declare breaks. Take the conservative
        # maximum — genuine autocorrelation can still RAISE the bar above the i.i.d. floor,
        # which is the only thing the block bootstrap is here to do.
        par95 = float(np.percentile(_parametric_null(n, h, min(2000, args.boot), rng), 95))
        crit95 = max(boot95, par95)
        p = float((null >= stat).mean())
        pvals[t] = p

        rec = {"n": n, "trim_h": h, "supF_1_0": float(stat),
               "boot_crit_95": boot95, "parametric_crit_95": par95,
               "crit_95_used": crit95, "crit_rule": "max(block-bootstrap, parametric iid)",
               "boot_p": p,
               "published_crit_8.58_exceeded": bool(stat > PUBLISHED_SUPF_CRIT_5PCT),
               "break_index": int(b), "break_date": str(s["date"].iloc[b].date()),
               "mean_before": float(y[:b].mean()), "mean_after": float(y[b:].mean())}

        if stat > crit95:
            lo, hi = _break_date_ci(y, h, b, min(1000, args.boot), rng)
            if lo is not None:
                rec["ci90_index"] = [lo, hi]
                rec["ci90_dates"] = [str(s["date"].iloc[int(max(0, min(n - 1, lo)))].date()),
                                     str(s["date"].iloc[int(max(0, min(n - 1, hi)))].date())]
                rec["ci90_width_frac"] = float((hi - lo) / n)
                rec["localised"] = bool((hi - lo) / n <= 1.0 / 3.0)
            else:
                rec["localised"] = False
            rec["verdict"] = "BREAK" if rec.get("localised") else "DRIFT"
            rec["seq_breaks"] = _sequential(y, h, rng, args.boot, MAX_BREAKS)
        else:
            rec["verdict"] = "NULL"
        out["series"][t] = rec
        print(f"  {t:16s} n={n:3d} supF={stat:7.3f} crit95={crit95:6.3f} p={p:.4f} "
              f"-> {rec['verdict']:5s} @ {rec['break_date']}", flush=True)

    # Holm-Bonferroni across the tested series
    if pvals:
        order = sorted(pvals.items(), key=lambda kv: kv[1])
        m = len(order)
        holm, prev = {}, 0.0
        for i, (k, p) in enumerate(order):
            adj = max(prev, min(1.0, (m - i) * p))
            holm[k] = adj
            prev = adj
        out["holm_adjusted_p"] = holm
        for k, adj in holm.items():
            if k in out["series"] and isinstance(out["series"][k], dict):
                out["series"][k]["holm_p"] = adj
                out["series"][k]["significant_after_multiplicity"] = bool(adj < 0.05)

    # the pre-specified case of interest
    sz = out["series"].get("size", {})
    if sz.get("break_date"):
        yr = int(sz["break_date"][:4])
        out["size_2012_check"] = {
            "break_date": sz["break_date"], "verdict": sz.get("verdict"),
            "lands_in_2011_2013": 2011 <= yr <= 2013,
            "note": ("Confirms the project's 2012 story" if 2011 <= yr <= 2013 and
                     sz.get("verdict") == "BREAK" else
                     "Does NOT confirm the 2012 story as a localised break")}

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    ser.to_csv(args.json.replace(".json", "_ic_series.csv"), index=False)
    print(f"[X6] -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
