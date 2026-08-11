#!/usr/bin/env python3
"""construction_rerun.py — S20 (rank composite) and S21 (winsorisation), on the corrected panel.

Ledger items S20 and S21, both OPEN, both src=auto, neither ever run. They are the same decision
seen twice: how a cross-section becomes a number before the weighted sum happens. P6.3 already
measured one point in that space - robust z-scores HALVED the long-short t while every per-signal
IC stayed flat - which is why this layer gets a register rather than a code review.

Everything about the design is fixed in PREREG_s20_s21_construction.md, committed ALONE at 27af414
BEFORE this file existed. Nothing here restates a threshold from a result.

THE STANDING RULE IS THE SPEC: never judge a construction change by per-signal IC. The verdict is
carried by the BOOK - the decile structure and the top-decile alpha. Per-signal and per-theme ICs
are diagnostics here and may not move a verdict in either direction.

Adopts nothing. An eligible arm QUEUES BEHIND the theme restoration's vintage (prereg 11).

    python -m scripts.construction_rerun \
        --data-dir C:/Users/donni/Downloads/valuation-tool/data/backtest \
        --panel    C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_s20_s21.pkl \
        --json     C:/Users/donni/Downloads/valuation-tool/data/free_analysis/S20_S21_CONSTRUCTION.json
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

# ---- everything below is PRE-REGISTERED; see PREREG_s20_s21_construction.md -----------------

# prereg 5 - the two weightings. DEPLOYED carries the verdict.
DEPLOYED = ["value", "quality", "momentum", "insider",
            "capital_discipline", "size", "institutional"]
# `sentiment` is excluded because it is empty (control C6); `growth` and `low_risk` are the two
# themes the deployed vector zeroes.
FLAT = DEPLOYED + ["growth", "low_risk"]
BASE_WEIGHT = 0.125

# prereg 6 - valid at THIS configuration: the full-universe decile book, 69 dates, H=63, lag 1.
# Quoted without caveat for the INCUMBENT arm; an EXTRAPOLATION for the challenger arms, and
# labelled one everywhere it appears.
LS_HAC_FLOOR = 2.2837
ALPHA_HAC_FLOOR = 2.2913
LS_NAIVE_FLOOR = 2.1437
HAC_LAG = 1

# prereg 6a - UNCALIBRATED, and labelled so everywhere. It cannot overturn the primary gate.
PAIRED_T_UNCALIBRATED = 2.0

# prereg 9 - C1, the published record the INCUMBENT arm must reproduce to the digit.
C1_RECORD = {"top_decile_alpha": 0.071741423321,
             "long_short_tstat": 2.8360640685320595,
             "long_short_tstat_nw": 2.6199,
             "top_decile_alpha_tstat_nw": 4.3762,
             "monotonicity": -0.8909090909090909,
             "equal_weight_ann": 0.18137118752419476}

# prereg 7 - the book, by name. No verdict attaches to it.
TOP_BOOK_N = 25

# P6.3, quoted from cross_sectional.py:16-42. Reference only - nothing is scored against it.
P6_ROBUST_Z = {"ls_t_classic": 3.485, "ls_t_robust": 1.721,
               "alpha_classic": 0.1177, "alpha_robust": 0.0899,
               "note": "measured on the VOID pre-B6 110-date panel; direction only"}


def _std_fns():
    """The three standardizers. prereg 3."""
    from valuation.screener.cross_sectional import rank_score, zscore, zscore_nowinsor
    return {"base": zscore, "rk": rank_score, "nw": zscore_nowinsor}


ARM_LABEL = {"base": "INCUMBENT (winsorized z, p=0.02)",
             "rk": "A20 RANK ((pct_rank-0.5)*2)",
             "nw": "A21 NOWINSOR (zscore, p=0.0)"}


def _f(x, p="+.4f"):
    return "n/a" if x is None else format(x, p)


# --------------------------------------------------------------------------- panel


def load_panel(path, data_dir):
    """ONE build. All three arms are scored from the same `metrics` list in the same pass."""
    import pandas as pd
    if os.path.exists(path):
        print(f"[s2021] reading cached panel {path}", flush=True)
        return pd.read_pickle(path)

    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel
    from valuation.screener.cross_sectional import rank_score, zscore_nowinsor

    class _C:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit(f"[s2021] provider not ready: {msg}")
    tickers = prov.universe(limit=CONFIG.backtest_universe_limit)
    print(f"[s2021] {len(tickers)} names; ONE build, three scorings "
          f"(prereg 4 - every arm shares the metrics list)", flush=True)
    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=63,
        keep_numbers=True,          # C5 needs the per-number columns
        standardizer_arms={"rk": rank_score, "nw": zscore_nowinsor},
    )
    print(f"[s2021] built {len(panel):,} rows x {len(panel.columns)} cols in "
          f"{time.time()-t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    panel.to_pickle(path)
    return panel


def split_arms(panel):
    """The three arms as three frames over an IDENTICAL row set (prereg 4)."""
    from valuation.screener import settings as S
    prefixes = ("rk_", "nw_")
    drop = [c for c in panel.columns if c.startswith(prefixes)]
    out = {"base": panel.drop(columns=drop, errors="ignore")}
    for p in ("rk", "nw"):
        a = panel.copy()
        for theme in S.FACTORS_ALL:
            src = f"{p}_{theme}"
            if src in a.columns:
                a[theme] = a[src]
        out[p] = a.drop(columns=drop, errors="ignore")
    return out


# --------------------------------------------------------------------------- arms


def arm(panel, cols, std, label):
    """Full-sample levels for one arm, scored by the SHIPPED quantile_backtest."""
    from valuation.edge.fundamental_panel import _nw_tstat, _tstat, quantile_backtest
    w = {c: BASE_WEIGHT for c in cols}
    r = quantile_backtest(panel, cols, w, n_q=10, horizon=63, return_series=True,
                          standardizer=std)
    if not r or "series" not in r:
        return {"label": label, "status": "no series"}
    a, ls = r["series"]["alpha"], r["series"]["long_short"]
    ls_hac, a_hac = _nw_tstat(ls, lag=HAC_LAG), _nw_tstat(a, lag=HAC_LAG)
    return {
        "label": label, "n_cols": len(cols), "cols": list(cols),
        "n_periods": r["n_periods"], "dates": r["series"]["dates"],
        "n_scored": r["series"]["n_scored"],
        "top_decile_alpha": r["top_decile_alpha"],
        "long_short_ann": r["long_short_ann"],
        "long_short_tstat": r["long_short_tstat"],
        "ls_t_hac": ls_hac,
        "alpha_t_naive": _tstat(a), "alpha_t_hac": a_hac,
        "monotonicity": r["monotonicity"],
        "equal_weight_ann": r["equal_weight_ann"],
        "decile_ann_return": r["decile_ann_return"],
        "alpha_hit": r["top_decile_alpha_hit"], "ls_hit": r["long_short_hit"],
        # prereg 6 - an EXTRAPOLATION for every arm but `base`.
        "clears_ls_hac_floor": (ls_hac is not None and ls_hac >= LS_HAC_FLOOR),
        "clears_alpha_hac_floor": (a_hac is not None and a_hac >= ALPHA_HAC_FLOOR),
        "clears_ls_naive_floor": (r["long_short_tstat"] is not None
                                  and r["long_short_tstat"] >= LS_NAIVE_FLOOR),
        "floors_are_extrapolated": label != "base",
        "alpha_series": a, "ls_series": ls,
    }


def paired(a_base, a_chal, dates=None, label="full"):
    """prereg 6a - the paired within-panel difference (the V2G construction).

    The arms score the SAME dates, so differencing per date cancels the market move. The 2.0 bar
    is UNCALIBRATED and cannot overturn the primary gate.
    """
    from valuation.edge.fundamental_panel import _nw_tstat, _tstat
    da = dict(zip(a_base["dates"], a_base["alpha_series"]))
    db = dict(zip(a_chal["dates"], a_chal["alpha_series"]))
    la = dict(zip(a_base["dates"], a_base["ls_series"]))
    lb = dict(zip(a_chal["dates"], a_chal["ls_series"]))
    keys = [d for d in a_base["dates"] if d in db and (dates is None or d in set(dates))]
    if len(keys) < 4:
        return {"label": label, "n_paired_dates": len(keys), "status": "too few dates"}
    d_alpha = [db[d] - da[d] for d in keys]
    d_ls = [lb[d] - la[d] for d in keys]
    n = len(keys)

    def block(v):
        m = float(np.mean(v))
        se = float(np.std(v, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
        return {"mean_period": m, "ann": m * 4.0, "se_period": se, "se_ann": se * 4.0,
                "t_naive": _tstat(v), "t_hac": _nw_tstat(v, lag=HAC_LAG)}

    return {"label": label, "n_paired_dates": n, "bar_uncalibrated": PAIRED_T_UNCALIBRATED,
            "alpha": block(d_alpha), "long_short": block(d_ls),
            "d_alpha_series": d_alpha, "d_ls_series": d_ls, "dates": keys}


# --------------------------------------------------------------------------- the book


def top_book(panel, cols, std, n=TOP_BOOK_N):
    """prereg 7 - the top-N names on the most recent rebalance date. NO VERDICT."""
    from valuation.edge.fundamental_panel import composite_from_frame
    last = sorted(panel["date"].unique())[-1]
    sub = panel[panel["date"] == last]
    w = {c: BASE_WEIGHT for c in cols}
    comp = np.asarray(composite_from_frame(sub, cols, w, std), dtype=float)
    tick = sub["ticker"].astype(str).to_numpy()
    ok = np.isfinite(comp)
    comp, tick = comp[ok], tick[ok]
    order = np.argsort(-comp)
    return {"date": str(last)[:10], "n_scored": int(len(comp)),
            "names": [str(tick[i]) for i in order[:n]],
            "scores": [float(comp[i]) for i in order[:n]]}


# --------------------------------------------------------------------------- controls


def controls(panel, arms, a_base_dep, std_fns):
    """prereg 9 - each control is a named way for this study to fail."""
    import pandas as pd
    from valuation.edge.fundamental_panel import _spearman, composite_from_frame
    from valuation.screener import settings as S
    from valuation.screener.cross_sectional import rank_score, winsorize
    out = {}

    # C1 - the incumbent reproduces the published record to the digit.
    got = {"top_decile_alpha": a_base_dep.get("top_decile_alpha"),
           "long_short_tstat": a_base_dep.get("long_short_tstat"),
           "long_short_tstat_nw": a_base_dep.get("ls_t_hac"),
           "top_decile_alpha_tstat_nw": a_base_dep.get("alpha_t_hac"),
           "monotonicity": a_base_dep.get("monotonicity"),
           "equal_weight_ann": a_base_dep.get("equal_weight_ann")}
    tol = {"top_decile_alpha": 5e-9, "long_short_tstat": 5e-9, "long_short_tstat_nw": 5e-5,
           "top_decile_alpha_tstat_nw": 5e-5, "monotonicity": 5e-9, "equal_weight_ann": 5e-9}
    c1 = {k: {"expected": C1_RECORD[k], "got": got[k],
              "abs_diff": (None if got[k] is None else abs(got[k] - C1_RECORD[k])),
              "ok": (got[k] is not None and abs(got[k] - C1_RECORD[k]) <= tol[k])}
          for k in C1_RECORD}
    out["C1_reproduces_record"] = {"detail": c1, "all_ok": all(v["ok"] for v in c1.values())}

    # C2 - identical row sets across all three arms.
    keys = {k: set(zip(v["date"].astype(str), v["ticker"].astype(str))) for k, v in arms.items()}
    dates = sorted(panel["date"].astype(str).unique())
    out["C2_identical_rows"] = {
        "n_rows": {k: int(len(v)) for k, v in arms.items()},
        "key_sets_identical": all(keys["base"] == keys[k] for k in keys),
        "n_dates": len(dates), "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "n_names": int(panel["ticker"].nunique()),
    }

    # C3 - the toggles are NOT inert. If an arm IS inert that is the finding, reported as such.
    inert = {}
    for p in ("rk", "nw"):
        cors, moved, tot = [], 0, 0
        for d in panel["date"].unique():
            sub_b = arms["base"][arms["base"]["date"] == d]
            sub_c = arms[p][arms[p]["date"] == d]
            w = {c: BASE_WEIGHT for c in DEPLOYED}
            cb = np.asarray(composite_from_frame(sub_b, DEPLOYED, w, std_fns["base"]), dtype=float)
            cc = np.asarray(composite_from_frame(sub_c, DEPLOYED, w, std_fns[p]), dtype=float)
            ok = np.isfinite(cb) & np.isfinite(cc)
            if ok.sum() < 30:
                continue
            cors.append(float(_spearman(cb[ok], cc[ok])))
            nq = 10
            ob, oc = np.argsort(-cb[ok]), np.argsort(-cc[ok])
            db_ = np.empty(ok.sum(), dtype=int)
            dc_ = np.empty(ok.sum(), dtype=int)
            for qi, b in enumerate(np.array_split(ob, nq)):
                db_[b] = qi
            for qi, b in enumerate(np.array_split(oc, nq)):
                dc_[b] = qi
            moved += int((db_ != dc_).sum())
            tot += int(ok.sum())
        inert[p] = {"composite_spearman_mean": (float(np.mean(cors)) if cors else None),
                    "composite_spearman_min": (float(np.min(cors)) if cors else None),
                    "frac_names_changing_decile": (moved / tot if tot else None),
                    "n_dates_measured": len(cors),
                    "is_inert": bool(cors and float(np.mean(cors)) > 0.9999 and moved == 0)}
    out["C3_not_inert"] = inert

    # C4 - no new missing values.
    nn = {}
    for theme in S.FACTORS_ALL:
        row = {}
        for k, v in arms.items():
            row[k] = int(pd.to_numeric(v[theme], errors="coerce").notna().sum()) \
                if theme in v.columns else None
        nn[theme] = {**row, "identical": len({x for x in row.values() if x is not None}) <= 1}
    out["C4_no_new_missing"] = {"per_theme": nn,
                                "all_identical": all(v["identical"] for v in nn.values())}

    # C5 - per-NUMBER Spearman IC is EXACTLY invariant to a rank transform.
    # The identity the standing rule rests on: rank-IC cannot see this change at all, while the
    # composite - a weighted SUM - may move a great deal.
    znums = [c for c in panel.columns if c.startswith("z_")]
    worst, per = 0.0, {}
    fwd_all = pd.to_numeric(panel["fwd_ret"], errors="coerce")
    for c in znums:
        diffs = []
        for d in panel["date"].unique():
            m = panel["date"] == d
            x = pd.to_numeric(panel.loc[m, c], errors="coerce")
            y = fwd_all[m]
            ok = x.notna() & y.notna()
            if ok.sum() < 30:
                continue
            i1 = _spearman(x[ok].to_numpy(dtype=float), y[ok].to_numpy(dtype=float))
            i2 = _spearman(rank_score(x[ok]).to_numpy(dtype=float), y[ok].to_numpy(dtype=float))
            if i1 == i1 and i2 == i2:
                diffs.append(abs(float(i1) - float(i2)))
        if diffs:
            per[c] = float(np.max(diffs))
            worst = max(worst, per[c])
    out["C5_rank_ic_invariant"] = {
        "n_number_columns": len(per), "max_abs_delta_ic": worst,
        "ok": worst < 1e-12,
        "scope": "Spearman IC of an already-standardized column vs the same column rank-transformed; "
                 "the incumbent's own winsorization is upstream of both sides and cancels",
        "per_column_max_abs_delta": per}

    # C6 - `sentiment` empty; `insider`'s layer-1 exemption verified rather than assumed.
    sent = pd.to_numeric(panel["sentiment"], errors="coerce") if "sentiment" in panel.columns else None
    ins_same = {}
    for p in ("rk", "nw"):
        src = f"{p}_insider"
        if src in panel.columns and "insider" in panel.columns:
            a = pd.to_numeric(panel["insider"], errors="coerce")
            b = pd.to_numeric(panel[src], errors="coerce")
            both = a.notna() & b.notna()
            ins_same[p] = {"n_compared": int(both.sum()),
                           "max_abs_diff": (float((a[both] - b[both]).abs().max())
                                            if both.any() else None),
                           "identical": bool(both.any() and float((a[both] - b[both]).abs().max()) == 0.0)}
    out["C6_sentiment_empty_insider_exempt"] = {
        "sentiment_non_null": (int(sent.notna().sum()) if sent is not None else None),
        "sentiment_in_weights": "sentiment" in DEPLOYED or "sentiment" in FLAT,
        "insider_layer1_identical_across_arms": ins_same,
        "note": "insider is (insider_score-50)/25 at layer 1, not a z-score, so the layer-1 swap "
                "cannot touch it; it IS standardized at layer 3 like every other theme"}

    # C7 - is the RANK arm invariant to winsorization? Measured, not assumed.
    # Registered as "must be bit-identical". Winsorization is WEAKLY monotone - it is flat in the
    # clipped tails - so it creates TIES, and pct-rank is not invariant to ties. Measured here on
    # the real columns rather than argued.
    c7, n_diff_tot, n_tot = {}, 0, 0
    for c in znums[:40]:
        mx = 0.0
        for d in list(panel["date"].unique())[:8]:
            m = panel["date"] == d
            x = pd.to_numeric(panel.loc[m, c], errors="coerce")
            if x.notna().sum() < 30:
                continue
            r_raw = rank_score(x)
            r_win = rank_score(winsorize(x, 0.02))
            ok = r_raw.notna() & r_win.notna()
            if not ok.any():
                continue
            dd = (r_raw[ok] - r_win[ok]).abs()
            mx = max(mx, float(dd.max()))
            n_diff_tot += int((dd > 1e-12).sum())
            n_tot += int(ok.sum())
        c7[c] = mx
    out["C7_rank_invariant_to_winsorization"] = {
        "registered_expectation": "bit-identical",
        "max_abs_delta_rank_score": (max(c7.values()) if c7 else None),
        "frac_rows_differing": (n_diff_tot / n_tot if n_tot else None),
        "bit_identical": bool(c7 and max(c7.values()) == 0.0),
        "n_columns_checked": len(c7), "per_column_max": c7}

    return out


# --------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from valuation.edge.fundamental_panel import (MIN_HOLDOUT_ALPHA_GAIN,
                                                  MIN_HOLDOUT_TSTAT_GAIN,
                                                  holdout_compare_panels)

    t0 = time.time()
    panel = load_panel(a.panel, a.data_dir)
    std = _std_fns()
    arms = split_arms(panel)
    print(f"[s2021] arms: {list(arms)}; {len(panel):,} rows", flush=True)

    res = {
        "study": "S20_S21_CONSTRUCTION",
        "prereg": "PREREG_s20_s21_construction.md (committed alone at 27af414)",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "gate": {"fn": "holdout_compare_panels",
                 "min_alpha_gain": MIN_HOLDOUT_ALPHA_GAIN,
                 "min_tstat_gain": MIN_HOLDOUT_TSTAT_GAIN,
                 "note": "both margins, BOTH halves, boundary embargoed; constants read from the "
                         "tree, not restated by this study"},
        "floors": {"ls_hac": LS_HAC_FLOOR, "alpha_hac": ALPHA_HAC_FLOOR,
                   "ls_naive": LS_NAIVE_FLOOR, "hac_lag": HAC_LAG,
                   "scope": "full-universe decile book, 69 dates, H=63, lag 1; an EXTRAPOLATION "
                            "for every arm but the incumbent"},
        "arm_labels": ARM_LABEL, "p6_robust_z_reference": P6_ROBUST_Z,
        "weightings": {}, "controls": {}, "books": {},
    }

    for wname, cols in (("deployed", DEPLOYED), ("flat", FLAT)):
        print(f"[s2021] === {wname} ({len(cols)} themes) ===", flush=True)
        levels = {k: arm(arms[k], cols, std[k], k) for k in ("base", "rk", "nw")}
        for k, v in levels.items():
            print(f"[s2021]   {k:5s} alpha {_f(v.get('top_decile_alpha'))}  "
                  f"ls_t {_f(v.get('long_short_tstat'))}  ls_hac {_f(v.get('ls_t_hac'))}  "
                  f"mono {_f(v.get('monotonicity'))}", flush=True)

        gates, pairs = {}, {}
        dates_all = levels["base"]["dates"]
        mid = len(dates_all) // 2
        halves = {"full": None, "early_half": dates_all[:mid], "late_half": dates_all[mid + 1:]}
        for p in ("rk", "nw"):
            gates[p] = holdout_compare_panels(
                arms["base"], arms[p], cols, label_a="base", label_b=p,
                n_q=10, horizon=63, base_weight=BASE_WEIGHT,
                standardizer_a=std["base"], standardizer_b=std[p])
            print(f"[s2021]   GATE {p}: {gates[p].get('verdict')}", flush=True)
            pairs[p] = {hn: paired(levels["base"], levels[p], ds, hn)
                        for hn, ds in halves.items()}

        res["weightings"][wname] = {"cols": cols, "levels": levels,
                                    "gates": gates, "paired": pairs}

    # prereg 7 - the book, by name, on the most recent date.
    books = {k: top_book(arms[k], DEPLOYED, std[k]) for k in ("base", "rk", "nw")}
    base_names = set(books["base"]["names"])
    for k in ("rk", "nw"):
        n = set(books[k]["names"])
        books[k]["overlap_with_base"] = len(base_names & n)
        books[k]["entering"] = sorted(n - base_names)
        books[k]["leaving"] = sorted(base_names - n)
    res["books"] = {"n": TOP_BOOK_N, "weighting": "deployed", "no_verdict_attaches": True,
                    **books}

    res["controls"] = controls(panel, arms, res["weightings"]["deployed"]["levels"]["base"], std)

    # verdicts, by prereg 5a
    verdicts = {}
    for p in ("rk", "nw"):
        gd = res["weightings"]["deployed"]["gates"][p].get("verdict")
        gf = res["weightings"]["flat"]["gates"][p].get("verdict")
        v = ("ADOPTED" if (gd == "adopt" and gf != "reject")
             else "REJECTED" if gd == "reject" else "NOT REPLICATED")
        verdicts[p] = {"verdict": v, "deployed_gate": gd, "flat_gate": gf,
                       "adopts_nothing": True,
                       "queues_behind": "the theme restoration's vintage (prereg 11)"}
    res["verdicts"] = verdicts

    os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print(f"[s2021] wrote {a.json} in {time.time()-t0:.0f}s", flush=True)
    for p in ("rk", "nw"):
        print(f"[s2021] {ARM_LABEL[p]}: {verdicts[p]['verdict']} "
              f"(deployed {verdicts[p]['deployed_gate']}, flat {verdicts[p]['flat_gate']})",
              flush=True)


if __name__ == "__main__":
    main()
