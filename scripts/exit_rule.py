#!/usr/bin/env python3
"""exit_rule.py — the race between the incumbent exit and four alternatives.  [S23]

The live book buys the top 25 by composite and holds each name until it falls out of the top 50,
min-hold 2. That exit has never been tested against an alternative — an inherited rule, like the
63-day horizon S22 found was never a measured optimum.

S22 is the prior and it is strong: annualized top-decile alpha is flat from three months to two
years and rank IC RISES with horizon, so an edge still accruing at two years argues AGAINST
selling early on price. PREREG_s23_exit_rule.md §8 therefore expects the incumbent to win, at
75/25, and says so before any number exists.

Everything — the arms, both TP/SL pairs, the band definitions, the cost formula, the decision
rule, the split point, the trial cost and the expectations — is fixed in that register, committed
ALONE at 6a73485 BEFORE this file existed. Nothing here restates a threshold from a result.

ADOPTS NOTHING. Under the vintage rule an adopted construction change closes the current vintage
and resets the five-year clock for zero statistical gain; adoption is Don's call on this evidence.

    python -m scripts.exit_rule \
        --panel    data/free_analysis/panel_s22_h504.pkl \
        --fv-panel data/free_analysis/panel_s23_fairvalue.pkl \
        --json     data/free_analysis/EXIT_RULE.json
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

# ---- everything below is PRE-REGISTERED; see PREREG_s23_exit_rule.md ------------------------
TOP_N = 25                    # the deployed book
EXIT_RANK = 2 * TOP_N         # the incumbent's hysteresis band
MIN_HOLD = 2                  # identical across every arm, so churn protection is not a confound
BPS_ONE_WAY = 33.4            # B11's MEASURED realised cost, not the older assumed 37

# The deployed flat 1/8 over the seven weighted themes (`low_risk` zeroed) — V2G's A7 vector.
DEPLOYED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
            "capital_discipline": 0.125, "size": 0.125, "institutional": 0.125}

# §2b — named here, from convention, and never tuned. No grid is swept.
TP_ONEIL, SL_ONEIL = 0.25, 0.08      # O'Neil / CANSLIM: cut at 8%, take 20-25%
TP_2TO1, SL_2TO1 = 0.20, 0.10        # textbook 2:1 reward-to-risk

PAIRED_T_BAR = 2.0            # UNCALIBRATED — labelled everywhere it appears
PLACEBO_DRAWS = 200
PLACEBO_SEED0 = 3000

ARMS = ["A0_INCUMBENT", "A1_FV_POINT", "A2_FV_LENSBAND", "A3_TPSL_ONEIL", "A4_TPSL_2TO1",
        "C_NEVER"]


def _fmt(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


# --------------------------------------------------------------------------- fair-value gates


def fv_sets(fv):
    """The two pre-registered valuation exits, as (date, ticker) sets. Zero free parameters.

    A1 FV-POINT     — price has reached the blended point estimate: gap = ln(fv/price) <= 0.
    A2 FV-LENSBAND  — price has reached the LOWEST lens the engine actually produced for that
                      name (dcf_ps / comps_fv / growth_ps), i.e. the conservative edge of the
                      engine's OWN disagreement rather than a band width chosen here.

    A name with no usable fair value cannot trigger either exit and is held on the incumbent
    rule alone; that coverage is reported before any verdict (the COVERAGE RULE).
    """
    import pandas as pd
    point, lens = set(), set()
    n_valuable = n_lens = 0
    price = pd.to_numeric(fv["price"], errors="coerce").to_numpy(dtype=float)
    gap = pd.to_numeric(fv["gap"], errors="coerce").to_numpy(dtype=float)
    valuable = fv["valuable"].to_numpy()
    lenses = [pd.to_numeric(fv[c], errors="coerce").to_numpy(dtype=float)
              for c in ("dcf_ps", "comps_fv", "growth_ps")]
    dates = fv["date"].to_numpy()
    ticks = fv["ticker"].to_numpy()
    for k in range(len(fv)):
        if not bool(valuable[k]):
            continue
        n_valuable += 1
        key = (str(dates[k]), str(ticks[k]))
        if np.isfinite(gap[k]) and gap[k] <= 0.0:
            point.add(key)
        vals = [L[k] for L in lenses if np.isfinite(L[k]) and L[k] > 0]
        if vals:
            n_lens += 1
            if price[k] >= min(vals):
                lens.add(key)
    return {"point": point, "lens": lens, "n_rows": int(len(fv)),
            "n_valuable": n_valuable, "n_with_lens": n_lens}


# --------------------------------------------------------------------------- arms


def arm(panel, name, fvs, dates=None, charge_costs=True):
    """One exit rule, driven through the SHIPPED `_backtest_hold`. Never re-implemented."""
    from valuation.edge.fundamental_panel import _backtest_hold
    p = panel if dates is None else panel[panel["date"].isin(dates)]
    kw = dict(top_n=TOP_N, exit_rank=EXIT_RANK, min_hold=MIN_HOLD, horizon=63,
              cost_bps_one_way=(BPS_ONE_WAY if charge_costs else None), return_series=True)
    if name == "A1_FV_POINT":
        kw["fv_at_or_above"] = fvs["point"]
    elif name == "A2_FV_LENSBAND":
        kw["fv_at_or_above"] = fvs["lens"]
    elif name == "A3_TPSL_ONEIL":
        kw["take_profit"], kw["stop_loss"] = TP_ONEIL, SL_ONEIL
    elif name == "A4_TPSL_2TO1":
        kw["take_profit"], kw["stop_loss"] = TP_2TO1, SL_2TO1
    elif name == "C_NEVER":
        kw["disable_rank_exit"] = True
    r = _backtest_hold(p, list(DEPLOYED), DEPLOYED, **kw)
    if r:
        r["arm"] = name
    return r


def paired(a, b):
    """HAC t on the per-period NET difference b - a, over the dates both arms scored.

    Both arms are scored on the same panel and the same dates, so the market move that dominates
    each level cancels. This is V2G's construction and it is far more powerful than comparing two
    CAGRs.
    """
    from valuation.edge.fundamental_panel import _nw_tstat, _tstat
    sa, sb = a["series"], b["series"]
    da = dict(zip(sa["dates"], sa["net"]))
    db = dict(zip(sb["dates"], sb["net"]))
    ga = dict(zip(sa["dates"], sa["gross"]))
    gb = dict(zip(sb["dates"], sb["gross"]))
    both = sorted(set(da) & set(db))
    dnet = [db[d] - da[d] for d in both]
    dgro = [gb[d] - ga[d] for d in both]
    ppy = 252.0 / 63
    return {"n_paired_dates": len(both),
            "d_net_ann": float(np.mean(dnet) * ppy) if dnet else None,
            "d_net_t": _tstat(dnet), "d_net_t_nw": _nw_tstat(dnet, lag=1),
            "d_gross_ann": float(np.mean(dgro) * ppy) if dgro else None,
            "d_gross_t_nw": _nw_tstat(dgro, lag=1),
            "d_net_series": dnet, "paired_dates": both}


def summarise(r):
    keys = ("arm", "cagr", "bench_cagr", "ew_cagr", "ew_alpha", "total_return", "n_periods",
            "hit_rate", "avg_hold_years", "target_n", "held_median", "held_min", "held_max",
            "charges_costs", "cost_bps_one_way", "exit_reasons", "avg_bought_per_period",
            "avg_sold_per_period", "avg_drag_per_period")
    return {k: r.get(k) for k in keys if k in r}


# --------------------------------------------------------------------------- placebo


def placebo(panel, fvs, draws=PLACEBO_DRAWS, seed0=PLACEBO_SEED0):
    """§5 — no calibrated floor exists for a paired difference between two concentrated
    event-driven books, so one is BUILT rather than borrowed.

    Under a permuted signal the exit rules still differ from one another, so the p95 of the
    paired |HAC t| across draws answers "how big a difference between two exit rules does NO
    SIGNAL AT ALL produce?". A DIFFERENT and less conservative null than X7's (fixed weights, no
    CPCV), labelled `fixed_weights_null`, and its percentiles may NEVER be compared with 2.2837.
    """
    from valuation.edge.fundamental_panel import placebo_panel, placebo_signal_cols
    perm_cols = placebo_signal_cols(panel)
    leaked = [c for c in perm_cols if str(c).startswith("fwd_ret")]
    if leaked:
        raise SystemExit(f"[s23] placebo would permute forward returns: {leaked}")
    rows, t0 = [], time.time()
    for i in range(draws):
        pp = placebo_panel(panel, seed=seed0 + i)
        base = arm(pp, "A0_INCUMBENT", fvs)
        rec = {"seed": seed0 + i}
        for name in ARMS[1:]:
            r = arm(pp, name, fvs)
            pr = paired(base, r) if (r and base) else {}
            rec[name] = {"d_net_ann": pr.get("d_net_ann"), "d_net_t_nw": pr.get("d_net_t_nw")}
        rows.append(rec)
        if i == 2 or (i + 1) % 25 == 0:
            el = time.time() - t0
            print(f"[s23] placebo {i+1}/{draws}  {el:.0f}s elapsed, "
                  f"~{el/(i+1)*(draws-i-1):.0f}s left", flush=True)

    floors = {}
    for name in ARMS[1:]:
        ts = [abs(r[name]["d_net_t_nw"]) for r in rows if r[name].get("d_net_t_nw") is not None]
        ds = [r[name]["d_net_ann"] for r in rows if r[name].get("d_net_ann") is not None]
        floors[name] = {
            "abs_t_p95": float(np.percentile(ts, 95)) if ts else None,
            "abs_t_max": float(max(ts)) if ts else None,
            "d_net_ann_median": float(np.median(ds)) if ds else None,   # C5
            "d_net_ann_p95": float(np.percentile(ds, 95)) if ds else None,
            "n": len(ts)}
    return {"instrument": "fixed_weights_null",
            "not_comparable_with": "X7/session-10 floors (those calibrate quantile_backtest on "
                                   "the full-universe decile book, a different object)",
            "draws": draws, "seeds": [seed0, seed0 + draws - 1],
            "floors": floors, "rows": rows}


# --------------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="S23 exit-rule race.")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--fv-panel", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--placebo-draws", type=int, default=PLACEBO_DRAWS)
    ap.add_argument("--skip-placebo", action="store_true")
    args = ap.parse_args(argv)

    import pandas as pd

    panel = pd.read_pickle(args.panel)
    fv = pd.read_pickle(args.fv_panel)
    dates = sorted(panel["date"].unique())
    fvd = sorted(fv["date"].unique())

    out = {"prereg": "PREREG_s23_exit_rule.md", "arms": ARMS,
           "params": {"top_n": TOP_N, "exit_rank": EXIT_RANK, "min_hold": MIN_HOLD,
                      "bps_one_way": BPS_ONE_WAY, "tp_oneil": TP_ONEIL, "sl_oneil": SL_ONEIL,
                      "tp_2to1": TP_2TO1, "sl_2to1": SL_2TO1},
           "panel": {"rows": int(len(panel)), "dates": len(dates),
                     "names": int(panel["ticker"].nunique()),
                     "range": [dates[0], dates[-1]]},
           "fv_panel": {"rows": int(len(fv)), "dates": len(fvd),
                        "names": int(fv["ticker"].nunique()),
                        "range": [fvd[0], fvd[-1]]}}

    # ---- C1: the two panels are the same panel ---------------------------------------
    keys_f = set(zip(panel["date"].astype(str), panel["ticker"].astype(str)))
    keys_v = set(zip(fv["date"].astype(str), fv["ticker"].astype(str)))
    out["C1_same_calendar"] = {
        "dates_identical": bool(dates == fvd),
        "n_factor_dates": len(dates), "n_fv_dates": len(fvd),
        "fv_keys_subset_of_factor": bool(keys_v <= keys_f),
        "n_fv_keys_not_in_factor": len(keys_v - keys_f),
        "coverage_of_factor_rows": (len(keys_v & keys_f) / len(keys_f)) if keys_f else None}
    print(f"[s23] C1 dates identical={out['C1_same_calendar']['dates_identical']} "
          f"fv covers {out['C1_same_calendar']['coverage_of_factor_rows']:.1%} of factor rows",
          flush=True)

    # ---- fair-value gates + coverage (COVERAGE RULE: before any verdict) --------------
    fvs = fv_sets(fv)
    out["fv_coverage"] = {
        "fv_rows": fvs["n_rows"], "valuable": fvs["n_valuable"],
        "valuable_share": fvs["n_valuable"] / max(1, fvs["n_rows"]),
        "with_any_lens": fvs["n_with_lens"],
        "n_point_gate": len(fvs["point"]), "n_lens_gate": len(fvs["lens"]),
        "point_gate_share_of_valuable": len(fvs["point"]) / max(1, fvs["n_valuable"]),
        "lens_gate_share_of_valuable": len(fvs["lens"]) / max(1, fvs["n_valuable"])}
    print(f"[s23] fair value: {fvs['n_valuable']:,}/{fvs['n_rows']:,} valuable; "
          f"point gate fires on {len(fvs['point']):,}, lens gate on {len(fvs['lens']):,}",
          flush=True)

    # ---- C3: the incumbent reproduces _backtest_hold, costs OFF ----------------------
    from valuation.edge.fundamental_panel import _backtest_hold
    shipped = _backtest_hold(panel, list(DEPLOYED), DEPLOYED, top_n=TOP_N,
                             exit_rank=EXIT_RANK, min_hold=MIN_HOLD, horizon=63)
    mine = arm(panel, "A0_INCUMBENT", fvs, charge_costs=False)
    c3 = {k: {"shipped": shipped.get(k), "s23": mine.get(k)}
          for k in ("cagr", "ew_alpha", "total_return", "n_periods", "held_median")}
    out["C3_incumbent_reproduces_shipped"] = {
        "checks": c3,
        "all_ok": all(repr(v["shipped"]) == repr(v["s23"]) for v in c3.values())}
    print(f"[s23] C3 {'PASS' if out['C3_incumbent_reproduces_shipped']['all_ok'] else 'FAIL'} "
          f"(gross cagr {_fmt(shipped.get('cagr'))})", flush=True)

    # ---- the race, costs charged -----------------------------------------------------
    runs = {name: arm(panel, name, fvs) for name in ARMS}
    gross = {name: arm(panel, name, fvs, charge_costs=False) for name in ARMS}
    out["arms_net"] = {k: summarise(v) for k, v in runs.items()}
    out["arms_gross"] = {k: summarise(v) for k, v in gross.items()}

    # C4 — every arm holds the whole current top-N after buying; and C6 — costs bite
    out["C4_same_buy_rule"] = {
        "note": "buy COUNTS legitimately differ (a name sold this period is re-bought), so the "
                "invariant is that every arm scores the same dates and the same target_n",
        "same_dates": all(runs[n]["series"]["dates"] == runs["A0_INCUMBENT"]["series"]["dates"]
                          for n in ARMS),
        "same_target_n": len({runs[n]["target_n"] for n in ARMS}) == 1}
    out["C6_costs_bite"] = {
        "net_le_gross": {n: bool(runs[n]["cagr"] <= gross[n]["cagr"]) for n in ARMS},
        "turnover_rank": sorted(ARMS, key=lambda n: -(runs[n]["avg_sold_per_period"] or 0)),
        "drag_rank": sorted(ARMS, key=lambda n: -(runs[n]["avg_drag_per_period"] or 0))}

    base = runs["A0_INCUMBENT"]
    out["paired_vs_incumbent"] = {n: paired(base, runs[n]) for n in ARMS[1:]}

    # ---- both halves ------------------------------------------------------------------
    cut = len(dates) // 2
    halves = {}
    for label, ds in (("early", dates[:cut]), ("late", dates[cut:])):
        b = arm(panel, "A0_INCUMBENT", fvs, dates=ds)
        halves[label] = {"n_dates": len(ds),
                         "paired": {n: paired(b, arm(panel, n, fvs, dates=ds)) for n in ARMS[1:]}}
    out["both_halves"] = {"split_at": cut, "halves": halves}

    # ---- placebo ----------------------------------------------------------------------
    if args.skip_placebo:
        out["placebo"] = {"status": "skipped"}
    else:
        print(f"[s23] placebo: {args.placebo_draws} draws x {len(ARMS)} arms", flush=True)
        out["placebo"] = placebo(panel, fvs, draws=args.placebo_draws)

    # ---- verdicts, by the rule fixed in advance ---------------------------------------
    verdicts = {}
    fl = (out.get("placebo") or {}).get("floors") or {}
    for n in ARMS[1:]:
        pr = out["paired_vs_incumbent"][n]
        t = pr.get("d_net_t_nw")
        d = pr.get("d_net_ann")
        floor = (fl.get(n) or {}).get("abs_t_p95")
        e = halves["early"]["paired"][n].get("d_net_ann")
        l = halves["late"]["paired"][n].get("d_net_ann")
        same_sign = (e is not None and l is not None and (e > 0) == (l > 0))
        clears = (t is not None and floor is not None and abs(t) >= floor)
        if d is not None and d > 0 and clears and same_sign and e > 0:
            v = "BEATS"
        elif d is not None and d < 0 and clears:
            v = "WORSE"
        else:
            v = "NO IMPROVEMENT"
        verdicts[n] = {"verdict": v, "d_net_ann": d, "d_net_t_nw": t, "own_floor": floor,
                       "clears_own_floor": clears, "halves_same_sign": same_sign,
                       "early_d": e, "late_d": l}
    out["verdicts"] = verdicts
    out["headline"] = ("NO CHALLENGER BEATS THE INCUMBENT"
                       if not any(v["verdict"] == "BEATS" for v in verdicts.values())
                       else "AT LEAST ONE CHALLENGER BEATS THE INCUMBENT")

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[s23] wrote {args.json}", flush=True)

    print("\narm                net CAGR   ew_alpha   held  hold_yr  d_net/yr   HAC t   floor  verdict",
          flush=True)
    for n in ARMS:
        r = runs[n]
        pr = out["paired_vs_incumbent"].get(n, {})
        v = verdicts.get(n, {})
        print(f"{n:18s} {_fmt(r['cagr']):>8} {_fmt(r['ew_alpha']):>9} "
              f"{str(r['held_median']):>5} {str(r['avg_hold_years']):>7} "
              f"{_fmt(pr.get('d_net_ann')):>9} {(pr.get('d_net_t_nw') or 0):7.3f} "
              f"{(v.get('own_floor') or 0):6.3f}  {v.get('verdict','(base)')}", flush=True)
    print(f"\n  {out['headline']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
