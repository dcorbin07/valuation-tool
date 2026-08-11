#!/usr/bin/env python3
"""live_theme_cost.py — what do the three dead live themes cost in return?  [V2G]

The greeks lane measured (HANDOFF_live_data_bugs.md Part 12.7) that three of the seven weighted
themes reach no live score: `insider` is constant, `capital_discipline` and `institutional` are
absent on 100% of served rows. That is 0.375 of 0.875 — 42.9% of the composite's weight mass — so
the live hot list is a FOUR-theme book wearing the weights of a seven-theme one.

That lane declined to price it ("that is a backtest question ... not this lane's"). This is it.

Two pre-specified arms, nothing selected:

    A7  deployed        value quality momentum insider capital_discipline size institutional
    B4  the live book   value quality momentum size

Everything about the design — the arms, the bars, the decision rule, the split point, the trial
cost and the expectations — is fixed in PREREG_v2g_live_theme_cost.md, committed alone at 6d8750a
BEFORE this file existed. Nothing here restates a threshold from a result.

    python -m scripts.live_theme_cost \
        --panel C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_corrected_69d.pkl \
        --json  C:/Users/donni/Downloads/valuation-tool/data/free_analysis/LIVE_THEME_COST.json
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np

# ---- everything below is PRE-REGISTERED; see PREREG_v2g_live_theme_cost.md ------------------
DEAD = ["insider", "capital_discipline", "institutional"]   # not reaching a live score
LIVE = ["value", "quality", "momentum", "size"]             # the four that do
W = 0.125

MARGIN_BAR = 0.0195          # X7 calibrated top-decile alpha margin (1.95pp)
PAIRED_T_BAR = 2.0           # UNCALIBRATED - no placebo floor exists for a paired difference
LS_HAC_FLOOR = 2.2837        # session 10 placebo p95, long-short HAC t
ALPHA_HAC_FLOOR = 2.2913     # session 10 placebo p95, top-decile alpha HAC t
LS_NAIVE_FLOOR = 2.1437      # X7 / session 10, diagnostic only


def _fmt(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


def _arm(panel, weights, label, **kw):
    from valuation.edge.fundamental_panel import quantile_backtest
    cols = list(weights)
    r = quantile_backtest(panel, cols, weights, n_q=10, horizon=63, return_series=True, **kw)
    r["label"] = label
    r["themes"] = cols
    return r


def _paired(a, b):
    """HAC t on the per-period difference b - a, over the dates BOTH arms scored.

    Two arms scored on the same dates share the market move that dominates each level, so
    differencing them cancels it. This is far more powerful than comparing two point estimates,
    and it is the only honest way to say whether a gap between two overlapping arms is real.
    """
    from valuation.edge.fundamental_panel import _nw_tstat, _tstat
    sa, sb = a["series"], b["series"]
    da = {d: (x, y) for d, x, y in zip(sa["dates"], sa["alpha"], sa["long_short"])}
    db = {d: (x, y) for d, x, y in zip(sb["dates"], sb["alpha"], sb["long_short"])}
    both = sorted(set(da) & set(db))
    d_alpha = [db[d][0] - da[d][0] for d in both]
    d_ls = [db[d][1] - da[d][1] for d in both]
    ppy = 252.0 / 63
    return {"n_paired_dates": len(both),
            "dates_only_in_a": sorted(set(da) - set(db)),
            "dates_only_in_b": sorted(set(db) - set(da)),
            "d_alpha_ann": float(np.mean(d_alpha) * ppy) if d_alpha else None,
            "d_alpha_t": _tstat(d_alpha), "d_alpha_t_nw": _nw_tstat(d_alpha, lag=1),
            "d_ls_ann": float(np.mean(d_ls) * ppy) if d_ls else None,
            "d_ls_t": _tstat(d_ls), "d_ls_t_nw": _nw_tstat(d_ls, lag=1),
            "d_alpha_series": d_alpha, "d_ls_series": d_ls, "paired_dates": both}


def _summary(r):
    return {k: r.get(k) for k in
            ("label", "themes", "n_periods", "top_decile_alpha", "top_decile_alpha_tstat_nw",
             "long_short_ann", "long_short_tstat", "long_short_tstat_nw", "monotonicity",
             "equal_weight_ann", "top_decile_alpha_hit", "long_short_hit")}


def _controls(panel, out):
    """C1/C2 — prove B4 IS the live book rather than merely resembling it.

    `fundamental_panel.composite` and `cross_sectional.composite_score` both renormalise by the
    present-weight mass, so a theme that is ABSENT (all-NaN) or CONSTANT (z-scores to all-NaN)
    drops out of numerator and denominator identically -- which is exactly what dropping it from
    `weights` does. If that is true, scoring the SEVEN-theme weight vector on a panel where the
    three dead themes are dead reproduces the FOUR-theme arm name for name.
    """
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    a7 = {t: W for t in LIVE + DEAD}
    b4 = {t: W for t in LIVE}
    worst1 = worst2 = 0.0
    n = 0
    for d in sorted(panel["date"].unique()):
        sub = panel[panel["date"] == d]
        want = composite_from_frame(sub, list(b4), b4, zscore)

        absent = sub.copy()
        for t in DEAD:
            absent[t] = np.nan
        got1 = composite_from_frame(absent, list(a7), a7, zscore)

        const = sub.copy()                      # the LIVE condition, exactly
        const["insider"] = 0.0                  # 500/500 non-null, one distinct value
        for t in ("capital_discipline", "institutional"):
            const[t] = np.nan
        got2 = composite_from_frame(const, list(a7), a7, zscore)

        for got, which in ((got1, 1), (got2, 2)):
            ok = np.isfinite(want) | np.isfinite(got)
            same_nan = np.array_equal(np.isfinite(want), np.isfinite(got))
            both = np.isfinite(want) & np.isfinite(got)
            dev = float(np.max(np.abs(want[both] - got[both]))) if both.any() else 0.0
            if not same_nan:
                dev = float("inf")
            if which == 1:
                worst1 = max(worst1, dev)
            else:
                worst2 = max(worst2, dev)
        n += int(len(sub))
    out["controls"] = {
        "C1_absence_equivalence_max_abs_dev": worst1,
        "C2_constancy_equivalence_max_abs_dev": worst2,
        "tolerance": 1e-12,
        "C1_pass": worst1 <= 1e-12, "C2_pass": worst2 <= 1e-12,
        "rows_compared": n,
        "note": ("C1 scores the A7 weight vector with the three dead themes NaN'd; C2 does the "
                 "live case exactly - `insider` CONSTANT, the other two absent. Both must "
                 "reproduce the B4 arm name for name, or the arms are not what the register "
                 "says they are and no verdict may be reported.")}
    print(f"[V2G] C1 absence  max|dev| {worst1:.3e}  pass={out['controls']['C1_pass']}", flush=True)
    print(f"[V2G] C2 constant max|dev| {worst2:.3e}  pass={out['controls']['C2_pass']}", flush=True)
    return out["controls"]["C1_pass"] and out["controls"]["C2_pass"]


def _floor_check(out, n_now):
    """C3 — are session 10's calibrated floors still the floors at today's N?

    `N` moves individual placebo draws through the CPCV adopt gate (session 12), and the floor is
    a percentile of the resulting null. My arms never call CPCV so the coupling cannot touch them,
    but it can move the floor they are compared against. Adoption is monotone DECREASING in N, so
    the adopter set at a higher N is a subset of the set at a lower one; if the two sets are
    identical, every draw scores identically and the floors are unchanged. That needs only the
    banked (margin, se), not a re-run.
    """
    import os
    p = os.path.join(os.path.dirname(out["panel"]["path"]), "X7_RECONCILE.json")
    try:
        d = json.load(open(p))
    except Exception as e:                                  # pragma: no cover - reported, not fatal
        out["floor_check"] = {"status": f"unavailable: {e}"}
        return
    hc = lambda n: math.sqrt(2.0 * math.log(n))
    base = 129
    adopt_at = lambda n: {r["seed"] for r in d["rows"]
                          if r.get("adopt_as_run") and r["margin"] > hc(n) * r["se"]}
    s_base, s_now = adopt_at(base), adopt_at(n_now)
    out["floor_check"] = {
        "n_baseline": base, "n_now": n_now,
        "haircut_baseline": hc(base), "haircut_now": hc(n_now),
        "n_adopters_baseline": len(s_base), "n_adopters_now": len(s_now),
        "adopter_set_identical": s_base == s_now,
        "seeds_that_stopped_adopting": sorted(s_base - s_now),
        "floors_unchanged": s_base == s_now,
        "note": ("Adoption is monotone decreasing in N, so an identical adopter set means every "
                 "draw is scored under the same weights and the calibrated percentiles cannot "
                 "have moved. If the set differs, the published floors must be re-measured "
                 "before they are quoted at this N.")}
    print(f"[V2G] C3 floors: adopters {len(s_base)} at N={base} -> {len(s_now)} at N={n_now}; "
          f"identical={s_base == s_now}", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="What the three dead live themes cost (V2G).")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--n-trials", type=int, default=135,
                    help="equity N AFTER this register's 4 arms are charged (prereg 9)")
    args = ap.parse_args(argv)

    import pandas as pd

    panel = pd.read_pickle(args.panel)
    dates = sorted(panel["date"].unique())
    cut = len(dates) // 2                                   # 69 -> first 34 / last 35, per prereg 6
    early, late = set(dates[:cut]), set(dates[cut:])

    out = {"item": "V2G", "prereg": "PREREG_v2g_live_theme_cost.md",
           "question": ("what the three themes that reach no live score "
                        "(insider constant, capital_discipline and institutional absent) cost"),
           "panel": {"path": args.panel, "rows": int(len(panel)),
                     "dates": len(dates), "names": int(panel["ticker"].nunique()),
                     "first": str(dates[0])[:10], "last": str(dates[-1])[:10],
                     "split_index": cut, "n_early": len(early), "n_late": len(late)},
           "bars": {"alpha_margin": MARGIN_BAR, "paired_t": PAIRED_T_BAR,
                    "paired_t_is_calibrated": False,
                    "ls_hac_floor": LS_HAC_FLOOR, "alpha_hac_floor": ALPHA_HAC_FLOOR,
                    "ls_naive_floor": LS_NAIVE_FLOOR}}
    print(f"[V2G] panel {len(panel):,} rows, {len(dates)} dates, "
          f"{panel['ticker'].nunique():,} names, {out['panel']['first']} -> "
          f"{out['panel']['last']}", flush=True)

    # ---- controls first: if these fail there is no verdict to report -----------------------
    controls_ok = _controls(panel, out)
    _floor_check(out, args.n_trials)

    a7w = {t: W for t in LIVE + DEAD}
    b4w = {t: W for t in LIVE}
    slices = {"full": panel,
              "early": panel[panel["date"].isin(early)],
              "late": panel[panel["date"].isin(late)]}

    out["arms"], out["paired"] = {}, {}
    for sl, pan in slices.items():
        a7 = _arm(pan, a7w, "A7 deployed")
        b4 = _arm(pan, b4w, "B4 live book")
        pr = _paired(a7, b4)
        out["arms"][sl] = {"A7": _summary(a7), "B4": _summary(b4),
                           "d_alpha": (None if a7["top_decile_alpha"] is None
                                       else b4["top_decile_alpha"] - a7["top_decile_alpha"]),
                           "d_ls_hac_t": (None if a7.get("long_short_tstat_nw") is None
                                          else b4["long_short_tstat_nw"] - a7["long_short_tstat_nw"]),
                           "n_scored_median": {
                               "A7": float(np.median(a7["series"]["n_scored"])),
                               "B4": float(np.median(b4["series"]["n_scored"]))}}
        out["paired"][sl] = pr
        print(f"\n[V2G] --- {sl} ({a7['n_periods']} periods) ---", flush=True)
        for r in (a7, b4):
            print(f"  {r['label']:14s} alpha={_fmt(r['top_decile_alpha']):>8s}  "
                  f"LS_HAC_t={_fmt(r.get('long_short_tstat_nw'), '.4f'):>7s}  "
                  f"LS_t={_fmt(r.get('long_short_tstat'), '.4f'):>7s}  "
                  f"alpha_HAC_t={_fmt(r.get('top_decile_alpha_tstat_nw'), '.4f'):>7s}  "
                  f"mono={_fmt(r.get('monotonicity'), '+.3f')}", flush=True)
        print(f"  {'DELTA (B4-A7)':14s} alpha={_fmt(out['arms'][sl]['d_alpha']):>8s}  "
              f"paired d_alpha={_fmt(pr['d_alpha_ann']):>8s}  "
              f"paired HAC t={_fmt(pr['d_alpha_t_nw'], '.4f')}  "
              f"(n={pr['n_paired_dates']})", flush=True)

    # ---- exploratory decomposition — NO VERDICT (prereg 7) ---------------------------------
    out["decomposition_exploratory"] = {"WARNING": (
        "NO VERDICT. Session 7 established on this exact panel that a full-sample ablation arm "
        "is not a finding - four of seven LOO arms changed sign between halves. These rank build "
        "priority; they decide nothing and may not be quoted as findings.")}
    for drop in DEAD:
        w = {t: W for t in LIVE + DEAD if t != drop}
        row = {}
        for sl, pan in slices.items():
            r = _arm(pan, w, f"A7 minus {drop}")
            base = out["arms"][sl]["A7"]
            row[sl] = {"top_decile_alpha": r["top_decile_alpha"],
                       "long_short_tstat_nw": r.get("long_short_tstat_nw"),
                       "d_alpha": (None if r["top_decile_alpha"] is None
                                   else r["top_decile_alpha"] - base["top_decile_alpha"])}
        out["decomposition_exploratory"][f"drop_{drop}"] = row
        print(f"[V2G] exploratory  drop {drop:20s} "
              + "  ".join(f"{s}: dalpha={_fmt(row[s]['d_alpha'])}" for s in slices), flush=True)

    # ---- verdict, against the pre-registered rule ONLY --------------------------------------
    f = out["arms"]["full"]
    p = out["paired"]["full"]
    d_alpha, pt = f["d_alpha"], p["d_alpha_t_nw"]
    b4 = f["B4"]
    stands = {"ls_hac_t": b4["long_short_tstat_nw"], "ls_hac_floor": LS_HAC_FLOOR,
              "clears_ls_hac": (b4["long_short_tstat_nw"] is not None
                                and b4["long_short_tstat_nw"] >= LS_HAC_FLOOR),
              "alpha_hac_t": b4["top_decile_alpha_tstat_nw"], "alpha_hac_floor": ALPHA_HAC_FLOOR,
              "clears_alpha_hac": (b4["top_decile_alpha_tstat_nw"] is not None
                                   and b4["top_decile_alpha_tstat_nw"] >= ALPHA_HAC_FLOOR),
              "ls_naive_t": b4["long_short_tstat"], "ls_naive_floor": LS_NAIVE_FLOOR,
              "clears_ls_naive": (b4["long_short_tstat"] is not None
                                  and b4["long_short_tstat"] >= LS_NAIVE_FLOOR)}

    if not controls_ok:
        verdict = "NO VERDICT — control C1/C2 failed; the arms are not what the register defines"
    elif d_alpha is None or pt is None:
        verdict = "INCONCLUSIVE — a required arm did not compute"
    elif d_alpha <= -MARGIN_BAR and abs(pt) >= PAIRED_T_BAR:
        verdict = "MATERIAL — building live sources for the dead themes is high-value"
    elif d_alpha > -MARGIN_BAR and abs(pt) < PAIRED_T_BAR:
        verdict = "IMMATERIAL — a nice-to-have"
    else:
        verdict = "NULL — ambiguous (the margin and the paired test disagree)"

    out["verdict"] = {"verdict": verdict, "d_alpha": d_alpha, "alpha_margin_bar": -MARGIN_BAR,
                      "paired_alpha_hac_t": pt, "paired_t_bar": PAIRED_T_BAR,
                      "paired_t_is_calibrated": False,
                      "does_the_live_book_stand_on_its_own": stands,
                      "halves": {s: {"d_alpha": out["arms"][s]["d_alpha"],
                                     "paired_alpha_hac_t": out["paired"][s]["d_alpha_t_nw"]}
                                 for s in ("early", "late")}}

    print(f"\n[V2G] d_alpha={_fmt(d_alpha)} (bar {_fmt(-MARGIN_BAR)})  "
          f"paired HAC t={_fmt(pt, '.4f')} (bar {PAIRED_T_BAR}, UNCALIBRATED)")
    print(f"[V2G] B4 alone: LS_HAC_t={_fmt(stands['ls_hac_t'], '.4f')} vs floor {LS_HAC_FLOOR} "
          f"-> {'CLEARS' if stands['clears_ls_hac'] else 'FAILS'};  "
          f"alpha_HAC_t={_fmt(stands['alpha_hac_t'], '.4f')} vs floor {ALPHA_HAC_FLOOR} "
          f"-> {'CLEARS' if stands['clears_alpha_hac'] else 'FAILS'}")
    print(f"[V2G] VERDICT: {verdict}")

    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[V2G] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
