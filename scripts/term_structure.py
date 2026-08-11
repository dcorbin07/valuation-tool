#!/usr/bin/env python3
"""term_structure.py — how long does the edge last, and how long do names stay hot?  [S22]

Every performance figure this project has published is measured at a 63-trading-day forward
window, because `build_fundamental_panel` computes exactly one `fwd_ret` and the deployed
rebalance period equals it. That is an inherited default, not a measured optimum. And the top
decile IS the product, yet how long a name survives in it has never been measured either.

Everything about the design — the horizons, the primary statistic, the date sets, the HAC lag,
the bars, the tenure definitions, the trial cost and the expectations — is fixed in
PREREG_s22_term_structure.md, committed ALONE at 6b187dd BEFORE this file existed. Nothing here
restates a threshold from a result.

Adopts nothing. Holding-period changes are S23's own register and a vintage event; display is
the web lane's.

    python -m scripts.term_structure \
        --data-dir C:/Users/donni/Downloads/valuation-tool/data/backtest \
        --panel    C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_s22_h504.pkl \
        --json     C:/Users/donni/Downloads/valuation-tool/data/free_analysis/TERM_STRUCTURE.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

# ---- everything below is PRE-REGISTERED; see PREREG_s22_term_structure.md -------------------
HORIZONS = [63, 126, 189, 252, 315, 378, 441, 504]      # 1..8 quarters (prereg 2)
BASE_H = 63

# The deployed book: flat 1/8 over the seven weighted themes (`low_risk` zeroed). This is the
# same vector V2G's A7 arm used, and reproducing the record with it is control C1.
DEPLOYED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
            "capital_discipline": 0.125, "size": 0.125, "institutional": 0.125}

# prereg 4 — classification of the term-structure shape, decided on R(8).
R_CONSTANT_RATE = 6.0        # >= 75% of linear accrual
R_SATURATING = 2.0           # <= 25% of linear accrual
REVERSE_T = -2.0             # UNCALIBRATED, and labelled so everywhere it appears

# prereg 5 — valid at ONE configuration only: H=63, the full 69-date panel, HAC lag 1.
LS_HAC_FLOOR = 2.2837
ALPHA_HAC_FLOOR = 2.2913
LS_NAIVE_FLOOR = 2.1437

PLACEBO_DRAWS = 200
PLACEBO_SEED0 = 2000

# prereg 8 — C1, the published record the incumbent arm must reproduce to the digit.
C1_RECORD = {"top_decile_alpha": 0.071741423321,
             "long_short_tstat": 2.8360640685320595,
             "long_short_tstat_nw": 2.6199,
             "top_decile_alpha_tstat_nw": 4.3762,
             "monotonicity": -0.8909090909090909,
             "equal_weight_ann": 0.18137118752419476}

# prereg 6a — the band the measured one-period decile retention must land in, derived from the
# shipped ~261%/yr turnover at four rebalances a year. Outside it, this is a BUG report and the
# tenure verdict is withheld.
RETENTION_BAND = (0.20, 0.50)


def hac_lag(h):
    """prereg 4a — the overlap the grid induces. At H=63 this is 1, the shipped R9 lag."""
    return max(1, h // BASE_H - 1)


def ret_col(h):
    return "fwd_ret" if h == BASE_H else f"fwd_ret_h{h}"


def _f(x, p="+.4f"):
    return "n/a" if x is None else format(x, p)


# --------------------------------------------------------------------------- panel


def load_panel(path, data_dir):
    import pandas as pd
    if os.path.exists(path):
        print(f"[s22] reading cached panel {path}", flush=True)
        return pd.read_pickle(path)

    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _C:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit(f"[s22] provider not ready: {msg}")
    tickers = prov.universe(limit=CONFIG.backtest_universe_limit)
    print(f"[s22] {len(tickers)} names; building panel with extra_horizons={HORIZONS} "
          f"(this is the ONE build every arm shares)", flush=True)
    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=BASE_H,
        extra_horizons=HORIZONS,
    )
    print(f"[s22] built {len(panel):,} rows x {len(panel.columns)} cols in "
          f"{time.time()-t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    panel.to_pickle(path)
    return panel


# --------------------------------------------------------------------------- arms


def arm(panel, h, dates=None, label=""):
    """One horizon, scored by the SHIPPED quantile_backtest on the deployed weights."""
    from valuation.edge.fundamental_panel import quantile_backtest, _nw_tstat, _tstat
    p = panel if dates is None else panel[panel["date"].isin(dates)]
    cols = list(DEPLOYED)
    r = quantile_backtest(p, cols, DEPLOYED, n_q=10, horizon=h,
                          return_series=True, ret_col=ret_col(h))
    if "series" not in r:
        return {"horizon": h, "label": label, "status": r.get("status", "no series")}
    a = r["series"]["alpha"]
    ls = r["series"]["long_short"]
    lag = hac_lag(h)
    # prereg 4 — the CUMULATIVE (non-annualized) alpha is the primary. Annualizing divides by
    # the horizon and would make a fixed one-off edge look like it decays as 1/k.
    out = {
        "horizon": h, "quarters": h // BASE_H, "label": label, "hac_lag": lag,
        "n_periods": r["n_periods"], "dates": r["series"]["dates"],
        "cum_alpha": float(np.mean(a)),
        "cum_long_short": float(np.mean(ls)),
        "alpha_ann": r["top_decile_alpha"],
        "long_short_ann": r["long_short_ann"],
        "alpha_t_naive": _tstat(a), "alpha_t_hac": _nw_tstat(a, lag=lag),
        "ls_t_naive": _tstat(ls), "ls_t_hac": _nw_tstat(ls, lag=lag),
        "monotonicity": r["monotonicity"],
        "equal_weight_ann": r["equal_weight_ann"],
        "decile_ann_return": r["decile_ann_return"],
        "alpha_hit": r["top_decile_alpha_hit"], "ls_hit": r["long_short_hit"],
        # prereg 4a — the full lag profile, as a sensitivity. The primary is `hac_lag`.
        "alpha_t_by_lag": {str(L): _nw_tstat(a, lag=L) for L in range(0, h // BASE_H + 3)},
        "ls_t_by_lag": {str(L): _nw_tstat(ls, lag=L) for L in range(0, h // BASE_H + 3)},
        "alpha_series": a, "ls_series": ls,
    }
    return out


def rank_ic(panel, h, dates=None):
    """Predictive power in its purest form: per-date Spearman(composite, fwd_ret_H)."""
    from valuation.edge.fundamental_panel import (composite_from_frame, _spearman, _nw_tstat,
                                                  _tstat)
    from valuation.screener.cross_sectional import zscore
    import pandas as pd
    p = panel if dates is None else panel[panel["date"].isin(dates)]
    cols = list(DEPLOYED)
    ics = []
    for d in sorted(p["date"].unique()):
        sub = p[p["date"] == d]
        comp = composite_from_frame(sub, cols, DEPLOYED, zscore)
        fwd = pd.to_numeric(sub[ret_col(h)], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(fwd)
        if ok.sum() < 30:
            continue
        ic = _spearman(comp[ok], fwd[ok])
        if ic == ic:
            ics.append(float(ic))
    if len(ics) < 4:
        return {"horizon": h, "n_dates": len(ics)}
    return {"horizon": h, "n_dates": len(ics), "median_ic": float(np.median(ics)),
            "mean_ic": float(np.mean(ics)), "ic_t_naive": _tstat(ics),
            "ic_t_hac": _nw_tstat(ics, lag=hac_lag(h)), "ic_series": ics}


# --------------------------------------------------------------------------- placebo


def placebo(panel, dates, draws=PLACEBO_DRAWS, seed0=PLACEBO_SEED0):
    """prereg 5 — a per-horizon null, because X7's floors are valid at ONE configuration.

    FIXED WEIGHTS, NO CPCV. This is deliberately a DIFFERENT and LESS CONSERVATIVE null than
    X7's, which pushed each draw through weight selection where adoption on a noise draw
    manufactures long-short t. Its percentiles may NEVER be compared with 2.2837 / 2.2913, and
    they are labelled `fixed_weights_null` in the artifact so a later reader cannot mistake them.

    The known exact-invariance of `placebo_panel` on the composite does not apply here: every
    statistic in this register is RETURN-based, and the permutation severs signal from return,
    which is exactly the null being tested.
    """
    from valuation.edge.fundamental_panel import placebo_panel, placebo_signal_cols
    p = panel[panel["date"].isin(dates)]
    perm_cols = placebo_signal_cols(p)
    leaked = [c for c in perm_cols if str(c).startswith("fwd_ret")]
    if leaked:                                    # a forward return must never be permuted
        raise SystemExit(f"[s22] placebo would permute forward returns: {leaked}")
    rows, t0 = [], time.time()
    for i in range(draws):
        pp = placebo_panel(p, seed=seed0 + i)
        rec = {"seed": seed0 + i}
        for h in HORIZONS:
            a = arm(pp, h, label=f"placebo{seed0+i}_h{h}")
            rec[str(h)] = {"alpha_t_hac": a.get("alpha_t_hac"), "ls_t_hac": a.get("ls_t_hac"),
                           "alpha_t_naive": a.get("alpha_t_naive"),
                           "ls_t_naive": a.get("ls_t_naive"),
                           "cum_alpha": a.get("cum_alpha")}
        rows.append(rec)
        if i == 2 or (i + 1) % 25 == 0:
            el = time.time() - t0
            print(f"[s22] placebo {i+1}/{draws}  {el:.0f}s elapsed, "
                  f"~{el/(i+1)*(draws-i-1):.0f}s left", flush=True)

    def pct(h, key, q):
        v = [r[str(h)][key] for r in rows if r[str(h)].get(key) is not None]
        return float(np.percentile(v, q)) if v else None

    def med(h, key):
        v = [r[str(h)][key] for r in rows if r[str(h)].get(key) is not None]
        return float(np.median(v)) if v else None

    floors = {}
    for h in HORIZONS:
        floors[str(h)] = {
            "alpha_t_hac_p95": pct(h, "alpha_t_hac", 95),
            "ls_t_hac_p95": pct(h, "ls_t_hac", 95),
            "alpha_t_naive_p95": pct(h, "alpha_t_naive", 95),
            "ls_t_naive_p95": pct(h, "ls_t_naive", 95),
            # C4 — a null centred away from zero means the instrument is broken.
            "alpha_t_hac_median": med(h, "alpha_t_hac"),
            "ls_t_hac_median": med(h, "ls_t_hac"),
            "alpha_t_hac_max": (max(r[str(h)]["alpha_t_hac"] for r in rows
                                    if r[str(h)].get("alpha_t_hac") is not None)),
        }
    return {"instrument": "fixed_weights_null",
            "not_comparable_with": "X7/session-10 floors (those include CPCV adoption)",
            "draws": draws, "seeds": [seed0, seed0 + draws - 1],
            "floors": floors, "rows": rows}


# --------------------------------------------------------------------------- tenure


def _decile_membership(panel, dates):
    """Top-decile membership per date, by the SHIPPED convention (argsort(-composite), n_q=10).

    Every panel row carries a finite base `fwd_ret` by construction, so the backtest's
    finite-mask reduces to "finite composite" here — the two definitions coincide, which is
    checked and reported rather than assumed.
    """
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    import pandas as pd
    members, tiers, scored, mask_agrees = {}, {}, {}, True
    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols=list(DEPLOYED), weights=DEPLOYED, zscore=zscore)
        base = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok_c = np.isfinite(comp)
        ok_both = ok_c & np.isfinite(base)
        if int(ok_c.sum()) != int(ok_both.sum()):
            mask_agrees = False
        idx = np.where(ok_both)[0]
        if len(idx) < 30:
            continue
        c = comp[idx]
        tick = sub["ticker"].to_numpy()[idx]
        mc = pd.to_numeric(sub["market_cap"], errors="coerce").to_numpy(dtype=float)[idx]
        order = np.argsort(-c)
        buckets = np.array_split(order, 10)
        members[d] = set(tick[buckets[0]])
        scored[d] = set(tick)
        # prereg 6 — market-cap TERTILES computed WITHIN each date, so tiers are relative.
        # Absolute dollar thresholds would drift across 18 years and measure the market's
        # growth rather than the name's size.
        fin = np.isfinite(mc)
        if fin.sum() >= 30:
            q1, q2 = np.percentile(mc[fin], [33.3333, 66.6667])
            tiers[d] = {t: ("small" if m <= q1 else ("mid" if m <= q2 else "large"))
                        for t, m in zip(tick, mc) if m == m}
        else:
            tiers[d] = {}
    return members, tiers, scored, mask_agrees


def _km(spells):
    """Kaplan-Meier over spell lengths. `spells` is a list of (length, censored)."""
    if not spells:
        return [], None
    at_risk = len(spells)
    curve, S = [], 1.0
    for t in sorted({l for l, _ in spells}):
        d = sum(1 for l, c in spells if l == t and not c)
        cen = sum(1 for l, c in spells if l == t and c)
        if at_risk > 0 and d:
            S *= (1.0 - d / at_risk)
        curve.append({"t": int(t), "at_risk": int(at_risk), "events": int(d),
                      "censored": int(cen), "survival": float(S)})
        at_risk -= (d + cen)
    median = next((r["t"] for r in curve if r["survival"] <= 0.5), None)
    return curve, median


def tenure(panel, dates):
    members, tiers, scored, mask_agrees = _decile_membership(panel, dates)
    ds = [d for d in dates if d in members]
    pos = {d: i for i, d in enumerate(ds)}
    last = len(ds) - 1

    # spells: maximal runs of CONSECUTIVE rebalance dates in the decile
    by_name = {}
    for d in ds:
        for t in members[d]:
            by_name.setdefault(t, []).append(pos[d])
    spells, exit_reason = [], {"fell_out": 0, "left_panel": 0, "censored": 0}
    for t, idxs in by_name.items():
        idxs.sort()
        run = [idxs[0]]
        for x in idxs[1:]:
            if x == run[-1] + 1:
                run.append(x)
            else:
                spells.append((t, run[0], len(run)))
                run = [x]
        spells.append((t, run[0], len(run)))

    recs = []
    for t, start, length in spells:
        end = start + length - 1
        censored = (end == last)
        if censored:
            exit_reason["censored"] += 1
            why = "censored"
        else:
            nxt = ds[end + 1]
            if t in scored.get(nxt, set()):
                exit_reason["fell_out"] += 1
                why = "fell_out"
            else:
                # left the panel entirely — reported separately rather than silently pooled
                exit_reason["left_panel"] += 1
                why = "left_panel"
        recs.append({"ticker": t, "start": ds[start], "length": int(length),
                     "censored": bool(censored), "exit": why,
                     "tier": tiers.get(ds[start], {}).get(t)})

    km_curve, km_median = _km([(r["length"], r["censored"]) for r in recs])
    done = [r["length"] for r in recs if not r["censored"]]
    naive_median = float(np.median(done)) if done else None

    by_tier = {}
    for tier in ("small", "mid", "large"):
        sel = [r for r in recs if r["tier"] == tier]
        c, m = _km([(r["length"], r["censored"]) for r in sel])
        dn = [r["length"] for r in sel if not r["censored"]]
        by_tier[tier] = {"n_spells": len(sel), "km_median": m,
                         "naive_median": (float(np.median(dn)) if dn else None),
                         "mean_length": (float(np.mean([r["length"] for r in sel]))
                                         if sel else None),
                         "km_curve": c}

    # one-period retention (prereg 6a) and persistence at lag j, with and without re-entry
    ret = []
    for i in range(len(ds) - 1):
        a, b = members[ds[i]], members[ds[i + 1]]
        if a:
            ret.append(len(a & b) / float(len(a)))
    retention = float(np.mean(ret)) if ret else None

    surv_cont, surv_any = {}, {}
    for j in range(1, 9):
        cont_n = cont_d = any_n = any_d = 0
        for i, d in enumerate(ds):
            if i + j > last:
                continue
            for t in members[d]:
                any_d += 1
                if t in members[ds[i + j]]:
                    any_n += 1
                cont_d += 1
                if all(t in members[ds[i + k]] for k in range(1, j + 1)):
                    cont_n += 1
        surv_cont[str(j)] = (cont_n / cont_d) if cont_d else None
        surv_any[str(j)] = (any_n / any_d) if any_d else None

    counts = {}
    for r in recs:
        counts[str(r["length"])] = counts.get(str(r["length"]), 0) + 1

    return {
        "n_dates": len(ds), "n_spells": len(recs),
        "n_distinct_names": len(by_name),
        "decile_size_median": float(np.median([len(members[d]) for d in ds])),
        "mask_definitions_coincide": bool(mask_agrees),
        "km_median_rebalances": km_median,
        "km_median_months": (None if km_median is None else km_median * 3.0),
        "naive_median_rebalances": naive_median,
        "mean_spell_rebalances": float(np.mean([r["length"] for r in recs])) if recs else None,
        "max_spell_rebalances": int(max(r["length"] for r in recs)) if recs else None,
        "spell_length_counts": counts,
        "km_curve": km_curve,
        "exit_reason": exit_reason,
        "one_period_retention": retention,
        "retention_band": list(RETENTION_BAND),
        "retention_in_band": (None if retention is None
                              else bool(RETENTION_BAND[0] <= retention <= RETENTION_BAND[1])),
        "survival_continuous": surv_cont,
        "persistence_any": surv_any,
        "by_cap_tier": by_tier,
        "reentry_names": sum(1 for t, i in by_name.items() if len([r for r in recs
                                                                   if r["ticker"] == t]) > 1),
        "spells": recs,
    }


# --------------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="S22 term structure + top-decile tenure.")
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--placebo-draws", type=int, default=PLACEBO_DRAWS)
    ap.add_argument("--skip-placebo", action="store_true")
    args = ap.parse_args(argv)

    import pandas as pd

    panel = load_panel(args.panel, args.data_dir)
    all_dates = sorted(panel["date"].unique())
    out = {"prereg": "PREREG_s22_term_structure.md", "horizons": HORIZONS,
           "weights": DEPLOYED, "n_rows": int(len(panel)), "n_dates": len(all_dates),
           "date_range": [all_dates[0], all_dates[-1]],
           "n_names": int(panel["ticker"].nunique())}

    # ---- C0: the added column IS the shipped column -----------------------------------
    c0_col = f"fwd_ret_h{BASE_H}"
    a = pd.to_numeric(panel["fwd_ret"], errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(panel[c0_col], errors="coerce").to_numpy(dtype=float)
    both_nan = (~np.isfinite(a)) & (~np.isfinite(b))
    dev = np.where(both_nan, 0.0, np.abs(a - b))
    c0_max = float(np.nanmax(dev)) if len(dev) else None
    out["C0_extra_column_is_shipped_column"] = {
        "column": c0_col, "n_rows": int(len(a)), "max_abs_dev": c0_max,
        "exact": bool(c0_max == 0.0),
        "n_base_non_finite": int((~np.isfinite(a)).sum()),
    }
    print(f"[s22] C0 max|fwd_ret - {c0_col}| = {c0_max:.3e} over {len(a):,} rows", flush=True)

    # ---- C2: censoring is real, counted, monotone -------------------------------------
    cens = {}
    for h in HORIZONS:
        col = ret_col(h)
        n_obs = int(np.isfinite(pd.to_numeric(panel[col], errors="coerce")
                                .to_numpy(dtype=float)).sum())
        d_obs = sorted(panel.loc[pd.to_numeric(panel[col], errors="coerce").notna(),
                                 "date"].unique())
        cens[str(h)] = {"rows_observable": n_obs, "dates_observable": len(d_obs),
                        "dates_censored": len(all_dates) - len(d_obs),
                        "last_date": (d_obs[-1] if d_obs else None)}
    mono = all(cens[str(HORIZONS[i])]["dates_observable"]
               >= cens[str(HORIZONS[i + 1])]["dates_observable"]
               for i in range(len(HORIZONS) - 1))
    out["C2_censoring"] = {"per_horizon": cens, "monotone_in_horizon": bool(mono)}
    print("[s22] C2 dates observable: "
          + ", ".join(f"h{h}={cens[str(h)]['dates_observable']}" for h in HORIZONS), flush=True)

    # ---- date sets --------------------------------------------------------------------
    all_avail = {h: arm(panel, h, label=f"all_h{h}") for h in HORIZONS}
    common = set(all_avail[HORIZONS[0]]["dates"])
    for h in HORIZONS:
        common &= set(all_avail[h].get("dates", []))
    common = sorted(common)
    out["date_sets"] = {"all_dates": len(all_dates), "common_dates": len(common),
                        "common_range": [common[0], common[-1]] if common else None,
                        "common": common}
    print(f"[s22] COMMON date set = {len(common)} dates "
          f"({common[0]} .. {common[-1]})", flush=True)

    # ---- C1: the incumbent reproduces the record --------------------------------------
    inc = all_avail[BASE_H]
    c1 = {}
    for k, want in C1_RECORD.items():
        got = {"top_decile_alpha": inc["alpha_ann"], "long_short_tstat": inc["ls_t_naive"],
               "long_short_tstat_nw": inc["ls_t_hac"],
               "top_decile_alpha_tstat_nw": inc["alpha_t_hac"],
               "monotonicity": inc["monotonicity"],
               "equal_weight_ann": inc["equal_weight_ann"]}[k]
        tol = 5e-5 if abs(want) < 10 and len(str(want)) <= 7 else 1e-9
        c1[k] = {"want": want, "got": got,
                 "ok": bool(got is not None and abs(got - want) <= tol), "tol": tol}
    out["C1_incumbent_reproduces_record"] = {"checks": c1,
                                             "all_ok": bool(all(v["ok"] for v in c1.values())),
                                             "n_dates": inc["n_periods"]}
    print("[s22] C1 " + ("PASS" if out["C1_incumbent_reproduces_record"]["all_ok"] else "FAIL")
          + " — " + ", ".join(f"{k}={_f(v['got'], '+.6f')}" for k, v in c1.items()), flush=True)

    # ---- PRIMARY: every arm on the COMMON date set ------------------------------------
    primary = {str(h): arm(panel, h, dates=common, label=f"common_h{h}") for h in HORIZONS}
    base_cum = primary[str(BASE_H)]["cum_alpha"]
    for h in HORIZONS:
        p = primary[str(h)]
        p["R"] = (p["cum_alpha"] / base_cum) if base_cum else None
        p["R_linear"] = float(h // BASE_H)
        p["R_over_linear"] = (p["R"] / p["R_linear"]) if p["R"] is not None else None
    out["primary_common_dates"] = primary
    out["secondary_all_available"] = {str(h): all_avail[h] for h in HORIZONS}

    # incremental series (prereg 4) — approximate inference, no verdict rests on it
    incr = {}
    for i, h in enumerate(HORIZONS):
        prev = 0.0 if i == 0 else primary[str(HORIZONS[i - 1])]["cum_alpha"]
        incr[str(h)] = {"quarter": h // BASE_H,
                        "delta_cum_alpha": primary[str(h)]["cum_alpha"] - prev,
                        "positive": bool(primary[str(h)]["cum_alpha"] - prev > 0)}
    out["incremental_by_quarter"] = {
        "note": "adjacent cumulative windows overlap almost entirely, so these are differences "
                "of highly dependent quantities; inference is APPROXIMATE and UNCALIBRATED and "
                "no verdict rests on it (prereg 4)",
        "series": incr}

    # ---- classification (prereg 4) ----------------------------------------------------
    r8 = primary[str(HORIZONS[-1])]["R"]
    reversing = any(primary[str(h)]["cum_alpha"] < 0
                    and (primary[str(h)]["alpha_t_hac"] or 0) <= REVERSE_T
                    for h in HORIZONS if h >= 189)
    if reversing:
        shape = "REVERSING"
    elif r8 is not None and r8 >= R_CONSTANT_RATE:
        shape = "CONSTANT-RATE"
    elif r8 is not None and r8 <= R_SATURATING:
        shape = "SATURATING"
    else:
        shape = "INTERMEDIATE"
    out["verdict"] = {"shape": shape, "R_8": r8,
                      "bars": {"constant_rate_at_or_above": R_CONSTANT_RATE,
                               "saturating_at_or_below": R_SATURATING,
                               "reversing_alpha_t_hac_at_or_below": REVERSE_T,
                               "reversing_bar_is": "UNCALIBRATED — conventional"},
                      "reversing_triggered": bool(reversing)}
    print(f"[s22] VERDICT shape={shape}  R(8)={_f(r8, '+.4f')}", flush=True)

    # ---- rank IC by horizon -----------------------------------------------------------
    out["rank_ic_common"] = {str(h): rank_ic(panel, h, dates=common) for h in HORIZONS}

    # ---- calibrated bars: only where they are valid ------------------------------------
    out["calibrated_bars"] = {
        "valid_configuration": "H=63, full 69-date panel, HAC lag 1 — the ONLY arm these apply to",
        "ls_hac_floor": LS_HAC_FLOOR, "alpha_hac_floor": ALPHA_HAC_FLOOR,
        "ls_naive_floor": LS_NAIVE_FLOOR,
        "h63_all_available": {
            "ls_t_hac": inc["ls_t_hac"], "clears_ls_hac": bool((inc["ls_t_hac"] or 0) >= LS_HAC_FLOOR),
            "alpha_t_hac": inc["alpha_t_hac"],
            "clears_alpha_hac": bool((inc["alpha_t_hac"] or 0) >= ALPHA_HAC_FLOOR),
            "ls_t_naive": inc["ls_t_naive"],
            "clears_ls_naive": bool((inc["ls_t_naive"] or 0) >= LS_NAIVE_FLOOR)},
        "why_not_elsewhere": "n changes with the horizon, the windows overlap, and the HAC lag "
                             "changes with them; these floors were calibrated at one "
                             "configuration and are not quoted against any other arm (prereg 5)",
    }

    # ---- both-halves stability (prereg 7) ----------------------------------------------
    cut = len(all_dates) // 2
    halves = {}
    for name, ds in (("early", all_dates[:cut]), ("late", all_dates[cut:])):
        dd = [d for d in common if d in set(ds)]
        if len(dd) < 8:
            halves[name] = {"n_dates": len(dd), "status": "too few common dates"}
            continue
        hh = {str(h): arm(panel, h, dates=dd, label=f"{name}_h{h}") for h in HORIZONS}
        b = hh[str(BASE_H)]["cum_alpha"]
        r = (hh[str(HORIZONS[-1])]["cum_alpha"] / b) if b else None
        halves[name] = {"n_dates": len(dd), "R_8": r,
                        "cum_alpha_by_h": {str(h): hh[str(h)]["cum_alpha"] for h in HORIZONS},
                        "alpha_t_hac_by_h": {str(h): hh[str(h)]["alpha_t_hac"] for h in HORIZONS}}
    same_sign = (halves.get("early", {}).get("R_8") is not None
                 and halves.get("late", {}).get("R_8") is not None
                 and (halves["early"]["R_8"] > 0) == (halves["late"]["R_8"] > 0))
    out["both_halves"] = {"split_at": cut, "halves": halves, "R8_same_sign": bool(same_sign)}

    # ---- tenure ------------------------------------------------------------------------
    print("[s22] tenure …", flush=True)
    out["tenure"] = tenure(panel, all_dates)
    t = out["tenure"]
    print(f"[s22] tenure KM median={t['km_median_rebalances']} rebalances, "
          f"retention={_f(t['one_period_retention'], '.4f')} "
          f"(band {RETENTION_BAND}, in_band={t['retention_in_band']})", flush=True)
    out["tenure_halves"] = {}
    for name, ds in (("early", all_dates[:cut]), ("late", all_dates[cut:])):
        th = tenure(panel, ds)
        out["tenure_halves"][name] = {k: th[k] for k in
                                      ("n_dates", "n_spells", "km_median_rebalances",
                                       "naive_median_rebalances", "one_period_retention")}

    # ---- placebo -----------------------------------------------------------------------
    if args.skip_placebo:
        out["placebo"] = {"status": "skipped"}
    else:
        print(f"[s22] placebo: {args.placebo_draws} draws x {len(HORIZONS)} horizons "
              f"on {len(common)} common dates", flush=True)
        out["placebo"] = placebo(panel, common, draws=args.placebo_draws)
        fl = out["placebo"]["floors"]
        for h in HORIZONS:
            p = primary[str(h)]
            f95 = fl[str(h)]["alpha_t_hac_p95"]
            l95 = fl[str(h)]["ls_t_hac_p95"]
            p["clears_own_alpha_floor"] = bool(p["alpha_t_hac"] is not None and f95 is not None
                                               and p["alpha_t_hac"] >= f95)
            p["clears_own_ls_floor"] = bool(p["ls_t_hac"] is not None and l95 is not None
                                            and p["ls_t_hac"] >= l95)
            p["own_alpha_floor"] = f95
            p["own_ls_floor"] = l95
        # by-product, no verdict (prereg 5)
        out["adoption_inflation_byproduct"] = {
            "fixed_weights_ls_hac_p95_at_h63": fl[str(BASE_H)]["ls_t_hac_p95"],
            "x7_session10_ls_hac_p95": LS_HAC_FLOOR,
            "difference": (None if fl[str(BASE_H)]["ls_t_hac_p95"] is None
                           else LS_HAC_FLOOR - fl[str(BASE_H)]["ls_t_hac_p95"]),
            "note": "the gap is what CPCV adoption adds to a noise draw's floor; an observation "
                    "with its own uncertainty, not a test, and it adopts nothing",
        }

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[s22] wrote {args.json}", flush=True)

    # ---- console summary ----------------------------------------------------------------
    print("\n  H   Q   n    cum_alpha   R      R/lin   alpha_t_hac  ls_t_hac  medIC", flush=True)
    for h in HORIZONS:
        p = primary[str(h)]
        ic = out["rank_ic_common"][str(h)].get("median_ic")
        print(f"{h:4d} {h//63:3d} {p['n_periods']:4d} {p['cum_alpha']:+10.4%} "
              f"{p['R']:6.2f} {p['R_over_linear']:6.2f}  {_f(p['alpha_t_hac'],'+8.4f')} "
              f"{_f(p['ls_t_hac'],'+8.4f')}  {_f(ic,'+.4f')}", flush=True)
    print(f"\n  shape = {shape}   R(8) = {_f(r8,'+.4f')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
