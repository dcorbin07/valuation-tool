#!/usr/bin/env python3
"""S14-WIDTH — extend the no-trade-band width grid past 0.30.

Executes `PREREG_s14_width_extension.md` unmodified.

Needs no panel rebuild: `turnover_and_costs` already returns gross alpha, net alpha, turnover
and the measured cost drag, and this register changes only which widths are swept.

Run:  python -m scripts.s14_width_extension
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP          # noqa: E402
from valuation.screener import cross_sectional as CS        # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125

# Register 3.1 — the SHIPPED five plus three conventional round extensions. Final; adding to
# this tuple after a result exists is void condition 1.
SHIPPED_WIDTHS = (0.12, 0.15, 0.20, 0.25, 0.30)
NEW_WIDTHS = (0.40, 0.50, 0.75)
WIDTHS = SHIPPED_WIDTHS + NEW_WIDTHS
ENTER_FRAC = 0.10                            # shipped, NOT swept (void condition 3)
AUDIT_GROSS_ALLOWANCE = 0.015                # reported beside ours, never substituted

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

# Session 35's own decide-half sweep, for the strengthened C1. NOT separately pre-registered:
# a reproduction check, carrying no verdict.
S35 = {
    "early_half": {"none": 0.011114, "0.12": 0.008719, "0.15": 0.020169,
                   "0.20": 0.020760, "0.25": 0.021734, "0.30": 0.028790},
    "late_half": {"none": 0.109434, "0.12": 0.118787, "0.15": 0.121729,
                  "0.20": 0.119076, "0.25": 0.123864, "0.30": 0.127240},
}


def band_sweep(panel, dates_subset):
    """Every width on one set of dates, through the SHIPPED cost machinery."""
    sub = panel[panel["date"].isin(dates_subset)]
    rows = {}
    for xf in (None,) + WIDTHS:
        c = FP.turnover_and_costs(sub, THEMES, {k: W for k in THEMES}, top_frac=0.10,
                                  horizon=63, exit_frac=xf) or {}
        rows["none" if xf is None else f"{xf:.2f}"] = {
            "annual_turnover": c.get("annual_turnover"),
            "gross_alpha": c.get("gross_alpha"),
            "net_alpha": c.get("net_alpha"),
            "cost_drag_ann": c.get("cost_drag_ann")}
    return rows


def book_diagnostics(panel, dates_subset):
    """C4 + C5 — realised book size and INCUMBENT SHARE at every width.

    Mirrors `turnover_and_costs`'s own selection loop and calls the SAME `_band_select`, so this
    reports on the object the arms are measured on rather than on a re-implementation of it.
    Returns are never touched here; this is mechanics only.
    """
    sub_all = panel[panel["date"].isin(dates_subset)]
    dates = sorted(sub_all["date"].unique())
    out = {}
    for xf in (None,) + WIDTHS:
        prev, sizes, inc_share = set(), [], []
        for d in dates:
            sub = sub_all[sub_all["date"] == d]
            if len(sub) < 20:
                continue
            comp = FP.composite_from_frame(sub, THEMES, {k: W for k in THEMES}, CS.zscore)
            k = max(1, int(len(sub) * 0.10))
            allt = sub["ticker"].values
            xr = k if xf is None else max(k, int(len(sub) * xf))
            sel = FP._band_select(comp, allt, set(prev), k, xr)
            # only rows with a usable forward return survive into the book, as in the shipped loop
            pos = {t: i for i, t in enumerate(allt)}
            order = np.array([pos[t] for t in sel], dtype=int)
            ok = np.isfinite(sub["fwd_ret"].values[order])
            kept = list(np.array(sel)[ok])
            if not kept:
                continue
            sizes.append(len(kept))
            if prev:
                inc_share.append(sum(1 for t in kept if t in prev) / len(kept))
            prev = set(kept)
        out["none" if xf is None else f"{xf:.2f}"] = {
            "mean_book_size": float(np.mean(sizes)) if sizes else None,
            "min_book_size": int(np.min(sizes)) if sizes else None,
            "max_book_size": int(np.max(sizes)) if sizes else None,
            "mean_incumbent_share": float(np.mean(inc_share)) if inc_share else None,
            "final_incumbent_share": float(inc_share[-1]) if inc_share else None}
    return out


def _monotone(v):
    if len(v) < 3:
        return None
    return bool(all(a <= b for a, b in zip(v, v[1:])) or all(a >= b for a, b in zip(v, v[1:])))


def run(panel, dates):
    """Sweep on the DECIDE half, measure the argmax width on the HELD-OUT half, both ways."""
    mid = len(dates) // 2
    halves = {"early_half": dates[:mid], "late_half": dates[mid + 1:]}   # boundary embargoed
    res = {"widths_grid": list(WIDTHS), "shipped_widths": list(SHIPPED_WIDTHS),
           "new_widths": list(NEW_WIDTHS), "enter_frac": ENTER_FRAC,
           "audit_gross_allowance": AUDIT_GROSS_ALLOWANCE, "directions": {}}
    sweeps = {name: band_sweep(panel, dts) for name, dts in halves.items()}
    picks, verdicts = [], []

    for decide, measure in (("early_half", "late_half"), ("late_half", "early_half")):
        dsw, msw = sweeps[decide], sweeps[measure]
        cands = {k: v for k, v in dsw.items() if k != "none" and v.get("net_alpha") is not None}
        if not cands:
            res["directions"][decide] = {"status": "no candidate widths"}
            picks.append(None)
            verdicts.append(False)
            continue
        pick = max(cands, key=lambda k: cands[k]["net_alpha"])
        base, arm = msw.get("none") or {}, msw.get(pick) or {}
        d_net = (arm.get("net_alpha") or 0) - (base.get("net_alpha") or 0)
        d_gross = (arm.get("gross_alpha") or 0) - (base.get("gross_alpha") or 0)
        saving = (base.get("cost_drag_ann") or 0) - (arm.get("cost_drag_ann") or 0)
        # Register 3.2 — the guard, unchanged from session 35 and fixed before its result.
        ok = bool(d_net > 0 and (-d_gross) <= saving)
        picks.append(pick)
        verdicts.append(ok)
        res["directions"][decide] = {
            "decide_sweep": dsw, "picked_width": pick, "measure_sweep": msw,
            "picked_is_new_width": pick in {f"{w:.2f}" for w in NEW_WIDTHS},
            "picked_is_grid_boundary": pick == f"{max(WIDTHS):.2f}",
            "delta_net_alpha": d_net, "delta_gross_alpha": d_gross,
            "measured_cost_saving": saving,
            "passes_tightened_guard": bool((-d_gross) <= saving),
            "passes_audits_own_allowance": bool((-d_gross) <= AUDIT_GROSS_ALLOWANCE),
            "improves": ok,
            "decide_surface_monotone_in_net": _monotone(
                [cands[f"{w:.2f}"]["net_alpha"] for w in WIDTHS if f"{w:.2f}" in cands]),
            "decide_net_alpha_argmax_rank": sorted(
                cands, key=lambda k: -cands[k]["net_alpha"])[:3]}
        print(f"[S14W] decide {decide:11s} -> width {pick}   measure: d_net {d_net:+.4f}  "
              f"d_gross {d_gross:+.4f}  saving {saving:+.4f}  improves {ok}")

    # ---- Register 4: the three committed outcomes, with the ambiguity rule applied ----
    boundary = f"{max(WIDTHS):.2f}"
    both_interior = all(p is not None and p != boundary for p in picks)
    any_boundary = any(p == boundary for p in picks)
    all_improve = all(verdicts)
    if any_boundary and all_improve:
        outcome, verdict = "b_UNBOUNDED_ON_THIS_GRID", "ELIGIBLE-BUT-UNBOUNDED"
    elif both_interior and all_improve:
        outcome, verdict = "a_INTERIOR_OPTIMUM", "ADOPTION-DECISION-ROUTED"
    elif not any(verdicts):
        outcome, verdict = "c_DIRECTIONS_DISAGREE", "REJECTED"
    else:
        outcome, verdict = "c_DIRECTIONS_DISAGREE", "NULL"
    res["picked_widths"] = picks
    res["directions_agree_on_width"] = bool(picks[0] == picks[1])
    res["outcome_branch"] = outcome
    res["verdict"] = verdict
    return res


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=r"C:/Users/donni/Downloads/valuation-tool/data/"
                                       r"free_analysis/panel_corrected_69d.pkl")
    ap.add_argument("--json", default="data/free_analysis/S14_WIDTH.json")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel, "rb"))
    print(f"[s14w] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"
    out = {"n_rows": int(len(panel)), "controls": {}, "arms": {}}

    # ---- C1: the run ABORTS before reading any width if the record does not reproduce ----
    base_r = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    c1 = {k: float(base_r.get(k)) for k in REC if base_r.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": c1}
    print(f"[C1] reproduces record: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 failed"
        _write(args.json, out)
        return 2

    dates = sorted(panel["date"].unique())
    arm = run(panel, dates)
    out["arms"]["A1_BAND_WIDTH_EXTENDED"] = arm

    # ---- C1 strengthened: do the five SHIPPED widths reproduce session 35 exactly? ----
    rep = {}
    for half, want in S35.items():
        sw = arm["directions"].get(half, {}).get("decide_sweep", {})
        rep[half] = {k: {"session35": v, "now": sw.get(k, {}).get("net_alpha"),
                         "abs_diff": (None if sw.get(k, {}).get("net_alpha") is None
                                      else abs(sw[k]["net_alpha"] - v))}
                     for k, v in want.items()}
    worst = max((c["abs_diff"] for h in rep.values() for c in h.values()
                 if c["abs_diff"] is not None), default=None)
    out["controls"]["C1b_shipped_widths_reproduce_session35"] = {
        "ok": bool(worst is not None and worst < 1e-5), "worst_abs_diff": worst,
        "detail": rep,
        "note": "NOT separately pre-registered - a reproduction check, carries no verdict"}
    print(f"[C1b] shipped widths reproduce session 35: worst |diff| {worst}")

    # ---- C2 / C4 / C5 ----
    mid = len(dates) // 2
    halves = {"early_half": dates[:mid], "late_half": dates[mid + 1:]}
    diags, turn_ok = {}, {}
    for half, dts in halves.items():
        diags[half] = book_diagnostics(panel, dts)
        sw = arm["directions"][half]["decide_sweep"]
        seq = [sw[f"{w:.2f}"]["annual_turnover"] for w in WIDTHS]
        turn_ok[half] = {"turnover_by_width": dict(zip([f"{w:.2f}" for w in WIDTHS], seq)),
                         "strictly_decreasing": bool(all(a > b for a, b in zip(seq, seq[1:]))),
                         "new_widths_below_030": bool(
                             all(sw[f"{w:.2f}"]["annual_turnover"] < sw["0.30"]["annual_turnover"]
                                 for w in NEW_WIDTHS))}
    out["controls"]["C2_wider_widths_actually_cut_turnover"] = turn_ok
    out["controls"]["C4_C5_book_size_and_incumbent_share"] = diags
    print("[C2] turnover strictly decreasing: "
          + ", ".join(f"{h} {v['strictly_decreasing']}" for h, v in turn_ok.items()))

    # ---- C3: the no-band case IS a width, not a different code path ----
    # DEFECT IN MY OWN CONTROL, found by running it: the first cut asserted LIST equality and
    # failed 176/200. `_band_select` returns survivors FIRST and then fills, so the ORDER differs
    # while the SET is identical - which is what `_band_select`'s docstring means and, under an
    # equal-weighted book, the only thing that can reach a number. Both halves are now measured:
    # the set claim on synthetic draws, and the order's irrelevance PROVED on the real panel by
    # swapping in a strict-rank selector and diffing every reported field.
    rng = np.random.default_rng(7)
    tick = np.array([f"T{i:03d}" for i in range(200)])
    set_ok, list_ok = 0, 0
    for _ in range(200):
        comp = rng.standard_normal(200)
        held = set(rng.choice(tick, 20, replace=False))
        plain = list(tick[np.argsort(-comp)][:20])
        got = list(FP._band_select(comp, tick, held, 20, 20))
        set_ok += (set(got) == set(plain))
        list_ok += (got == plain)

    def _strict_rank(comp, tickers, held, n_target, exit_rank):
        assert exit_rank == n_target, "the order probe is only valid for the no-band case"
        return list(np.array(tickers)[np.argsort(-comp)][:n_target])

    _sub = panel[panel["date"].isin(dates[:len(dates) // 2])]
    _orig = FP._band_select
    _a = FP.turnover_and_costs(_sub, THEMES, {k: W for k in THEMES}, top_frac=0.10,
                               horizon=63, exit_frac=None)
    try:
        FP._band_select = _strict_rank
        _b = FP.turnover_and_costs(_sub, THEMES, {k: W for k in THEMES}, top_frac=0.10,
                                   horizon=63, exit_frac=None)
    finally:
        FP._band_select = _orig
    _fields = ["annual_turnover", "gross_alpha", "net_alpha", "cost_drag_ann", "gross_ann",
               "net_ann", "realised_one_way_bps", "net_sharpe", "net_max_drawdown"]
    _worst = max(abs(_a[f] - _b[f]) for f in _fields
                 if _a.get(f) is not None and _b.get(f) is not None)
    out["controls"]["C3_no_band_reduces_to_plain_topN"] = {
        "ok": bool(set_ok == 200 and _worst < 1e-12),
        "set_equal": set_ok, "list_equal": list_ok, "n": 200,
        "order_irrelevance_max_abs_delta": _worst, "fields_diffed": _fields,
        "note": "SET equality is the docstring's claim and the only one an equal-weighted book "
                "can see; the first cut asserted LIST equality and failed 176/200 on ORDER alone"}
    print(f"[C3] set-equal {set_ok}/200 (list-equal {list_ok}/200); "
          f"order irrelevance max |d| {_worst:.3e}")

    # C6 is carried per-direction inside the arm; surface it for the write-up.
    out["controls"]["C6_surface_monotone_by_half"] = {
        h: arm["directions"][h].get("decide_surface_monotone_in_net")
        for h in halves if h in arm["directions"]}

    _write(args.json, out)
    print(f"\n[s14w] verdict {arm['verdict']} ({arm['outcome_branch']}), "
          f"picks {arm['picked_widths']}")
    print(f"[s14w] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
