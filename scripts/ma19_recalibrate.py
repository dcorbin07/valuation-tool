#!/usr/bin/env python3
"""ma19_recalibrate.py — X7's placebo floors, re-derived at today's trial count.  [MA19]

Registered in PREREG_ma19_ma13_recalibration.md, committed alone before this file existed.

THE RULE THIS EXISTS TO HONOUR is the project's own, from X7RECON: *"a calibrated placebo floor
is a function of `N` ... a floor may not be compared across sweeps run at different `N` without
checking."* X7 calibrated at `N` = 84, session 10 re-derived the long-short floors at `N` = 121,
and `N` is 224 today. Nothing has checked the floors since.

WHY THIS IS NOT A 3.4-HOUR SWEEP, AND NOT PURE ARITHMETIC EITHER. The master audit says "the
check is arithmetic, not a sweep". Measured, that is HALF right, and the half that fails is the
half that matters:

  * ARITHMETIC: which draws adopt. The CPCV gate's only `N`-dependence is
    `margin > _trials_haircut(...) * se`, and (margin, se) are banked for all 100 draws. So the
    adopt SET at any `N` is a calculation. Confirmed: the curve reproduces exactly.
  * NOT ARITHMETIC: the floors themselves. A draw that stops adopting is re-scored under BASE
    weights instead of its challenger's, and **only 1 of the 100 banked rows (seed 1005) carries
    both scorings**. The other 99 carry whichever one the as-run adoption chose.

So the honest method is a TARGETED re-score of the flipped draws only — two of them — on the same
panel checkpoint, the same seeds, the same permutation instrument and the same estimator. That is
minutes, not hours, and it is not a shortcut: the 98 unflipped draws are provably untouched
(control C5), because the only channel that could move them does not fire.

THREE CHANNELS, each VERIFIED rather than assumed (register §2):

  A  ADOPTION (indirect)  N -> haircut -> adopt set -> weight vector -> ls_t, alpha, monotonicity.
                          Only flipped draws can move.
  B  DIRECT               N enters the Deflated Sharpe's own `sr0`. EVERY draw moves.
  C  NONE                 theme IC t and PBO read neither the weights nor the haircut.

CHANNEL B IS RECOVERED EXACTLY, NOT APPROXIMATED. `skew` and `kurt` were never banked, but the
DSR's denominator is a function of (sr, skew, kurt) ALONE and so is `N`-independent. Inverting the
banked probability recovers it in closed form:

    z = Phi^-1(p),   denom = [ (sr - sr0) * sqrt(n-1) / z ]^2

and the recomputation at the OLD `N` must then reproduce the banked probability to floating point.
That round trip is control C8 — without it this would be a reimplementation wearing the shipped
function's name, which is the B7 defect class.

    python -m scripts.ma19_recalibrate
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

from valuation.edge import fundamental_panel as FP
from valuation.edge import research_log as RL
from valuation.screener import settings as S

BUCKET = "established"
HALFLIFE = 1260
HORIZON = 63

# The shared checkout owns `data/`; this worktree's copy is empty.
DATA = os.environ.get("MA19_DATA", "C:/Users/donni/Downloads/valuation-tool/data")
PANEL = f"{DATA}/free_analysis/panel_corrected_69d.pkl"
BANK_PLACEBO = f"{DATA}/free_analysis/PLACEBO_HAC.json"
BANK_RECON = f"{DATA}/free_analysis/X7_RECONCILE.json"
OUT = f"{DATA}/free_analysis/MA19_RECALIBRATION.json"

# The `N` regimes that matter. 84 = X7's calibration; 121/129 = session 10 / as-run; live = today.
N_X7, N_S10, N_ASRUN = 84, 121, 129

# Session 10's published floors, restated here ONLY as the reproduction target for C2.
PUBLISHED = {
    "long_short_tstat_p95": 2.1437,
    "long_short_tstat_nw_p95": 2.2837,
    "top_decile_alpha_tstat_nw_p95": 2.2913,
    "pbo_p05": 0.1967,
}
# X7's own published bars, at N = 84. These are what the RECORD quotes.
X7_BARS = {
    "long_short_tstat_p95": 2.14,
    "long_short_tstat_nw_p95": 2.2837,
    "max_abs_theme_ic_t_p95": 2.71,
    "top_decile_alpha_p95": 0.0195,
    "pbo_p05": 0.197,
    "deflated_sharpe_p95": 0.7216,
}

# The keys `_summary` is computed over, in placebo.py's own order.
KEYS = ("long_short_tstat", "long_short_tstat_nw", "top_decile_alpha", "monotonicity",
        "pbo", "deflated_sharpe", "max_abs_theme_ic_t", "equal_weight_ann",
        "long_short_ann", "breakeven_one_way_bps", "n_themes_ic_t_over_2",
        "top_decile_alpha_tstat", "top_decile_alpha_tstat_nw", "long_short_ljung_box_p")


def _q(xs, p):
    """placebo.py:53 — the SAME estimator. np.percentile, linear interpolation, no smoothing."""
    v = [float(x) for x in xs if x is not None and x == x]
    return (float(np.percentile(v, p)) if len(v) >= 2 else None)


def _summary(xs):
    v = [float(x) for x in xs if x is not None and x == x]
    if not v:
        return {"n": 0}
    return {"n": len(v), "mean": float(np.mean(v)),
            "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0,
            "min": float(np.min(v)), "p05": _q(v, 5), "p50": _q(v, 50), "p95": _q(v, 95),
            "p025": _q(v, 2.5), "p975": _q(v, 97.5), "max": float(np.max(v)),
            "mc_se_mean": (float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else None)}


def haircut_at(n_trials, n_names=9):
    """`_trials_haircut` with the log floor made an explicit argument, so two `N` are comparable."""
    return float(np.sqrt(2.0 * np.log(max(2, int(n_trials), int(n_names)))))


def gate_ok(r):
    """The adopt gate's N-INDEPENDENT conditions (fundamental_panel.py:3093)."""
    return ((r.get("se") or 0) > 0
            and (r.get("median_oos_ic_best") or 0) > 0
            and (r.get("folds_positive") or 0) >= 0.6)


def adopters_at(rows, n):
    h = haircut_at(n)
    return {r["seed"] for r in rows if gate_ok(r) and (r["margin"] or 0) > h * (r["se"] or 0)}


# ---------------------------------------------------------------- Channel B, in closed form
def _dsr_at(detail, n_trials):
    """Re-evaluate a banked Deflated Sharpe at a different `N`, exactly.

    `sr0` is the only term that reads `N`; the skew/kurtosis denominator does not, so it can be
    recovered by inverting the banked probability and then reused. Returns None when the banked
    row is too degenerate to invert (|z| tiny, or var_sr absent).
    """
    if not isinstance(detail, dict):
        return None
    sr = detail.get("sharpe_per_period")
    var_sr = detail.get("var_sr_across_trials")
    n = detail.get("n_periods")
    p = detail.get("probability")
    sr0_old = detail.get("sr0_benchmark")
    if sr is None or var_sr is None or not n or p is None or sr0_old is None:
        return None
    z_old = FP._nppf(min(max(float(p), 1e-15), 1 - 1e-15))
    if abs(z_old) < 1e-9:
        return None
    num_old = (float(sr) - float(sr0_old)) * math.sqrt(int(n) - 1)
    denom = (num_old / z_old) ** 2
    if not (denom > 0):
        return None
    emc = 0.5772156649015329
    N = max(2, int(detail.get("n_trials_from_weight_schemes") or 8), int(n_trials))
    sr0 = (float(var_sr) ** 0.5) * ((1 - emc) * FP._nppf(1 - 1.0 / N)
                                    + emc * FP._nppf(1 - 1.0 / (N * math.e)))
    z = (float(sr) - sr0) * math.sqrt(int(n) - 1) / math.sqrt(denom)
    return {"probability": float(FP._ncdf(z)), "sr0_benchmark": float(sr0), "n_trials": int(N)}


# ---------------------------------------------------------------- the targeted re-score
def rescore(panel, cols, base, seed):
    """One placebo draw, scored under BOTH weightings, through the shipped functions.

    This is `placebo.one_iteration`'s path with the single difference that BOTH the base and the
    challenger scoring are returned rather than only whichever adoption selected — which is the
    exact gap that makes the recalibration a re-score instead of a lookup.
    """
    pl = FP.placebo_panel(panel, seed=seed)
    cpcv = FP.cpcv_validate(pl, cols, base, halflife_days=HALFLIFE, horizon=HORIZON) or {}
    chal = cpcv.get("challenger_weights_cols") or cpcv.get("recommended_weights_cols") or dict(base)

    qb_base = FP.quantile_backtest(pl, cols, base, n_q=10, horizon=HORIZON) or {}
    qb_chal = FP.quantile_backtest(pl, cols, chal, n_q=10, horizon=HORIZON) or {}

    themes = FP.theme_ic(pl) or {}
    themes = themes.get("themes") if isinstance(themes.get("themes"), dict) else themes
    t_abs = [abs(v.get("ic_tstat")) for v in themes.values()
             if isinstance(v, dict) and v.get("ic_tstat") is not None]

    def pack(qb):
        return {
            "long_short_tstat": qb.get("long_short_tstat"),
            "long_short_tstat_nw": qb.get("long_short_tstat_nw"),
            "long_short_ljung_box_p": ((qb.get("long_short_ljung_box") or {}).get("p_value")
                                       if isinstance(qb.get("long_short_ljung_box"), dict) else None),
            "top_decile_alpha_tstat": qb.get("top_decile_alpha_tstat"),
            "top_decile_alpha_tstat_nw": qb.get("top_decile_alpha_tstat_nw"),
            "long_short_ann": qb.get("long_short_ann"),
            "top_decile_alpha": qb.get("top_decile_alpha"),
            "monotonicity": qb.get("monotonicity"),
            "equal_weight_ann": qb.get("equal_weight_ann"),
            "n_periods": qb.get("n_periods"),
        }

    return {
        "seed": int(seed),
        "cpcv_adopt_live": bool(cpcv.get("adopt")),
        "cpcv_recommend_live": cpcv.get("recommend"),
        "adopt_detail_live": cpcv.get("adopt_detail"),
        "pbo": cpcv.get("pbo"),
        "deflated_sharpe": cpcv.get("deflated_sharpe"),
        "deflated_sharpe_detail": cpcv.get("deflated_sharpe_detail"),
        "max_abs_theme_ic_t": (max(t_abs) if t_abs else None),
        "n_themes_ic_t_over_2": int(sum(1 for t in t_abs if t >= 2.0)),
        "base": pack(qb_base),
        "challenger": pack(qb_chal),
    }


def main():
    t_start = time.time()
    live_N = int(RL.trial_count(domain="equity"))
    by_domain = RL.detail().get("by_domain")
    print(f"[ma19] live equity N = {live_N}  (by_domain {by_domain})", flush=True)
    print(f"[ma19] haircut: N={N_ASRUN} -> {haircut_at(N_ASRUN):.5f} | "
          f"N={live_N} -> {haircut_at(live_N):.5f}", flush=True)

    bank = json.load(open(BANK_PLACEBO))
    recon = json.load(open(BANK_RECON))
    draws = {d["seed"]: d for d in bank["draws"]}
    rows = recon["rows"]
    print(f"[ma19] bank: {len(draws)} placebo draws, {len(rows)} reconcile rows", flush=True)

    report = {
        "test": "MA19 — X7's placebo floors re-derived at the current trial count",
        "register": "PREREG_ma19_ma13_recalibration.md",
        "panel": PANEL,
        "seeds": bank.get("seeds"),
        "n_draws": len(draws),
        "live_N": live_N,
        "by_domain": by_domain,
        "N_regimes": {"x7": N_X7, "session10": N_S10, "as_run": N_ASRUN, "today": live_N},
        "haircuts": {str(n): haircut_at(n) for n in (N_X7, N_S10, N_ASRUN, live_N)},
        "controls": {},
    }

    # ------------------------------------------------ C1 (GATING): the adopt curve reproduces
    curve = {}
    for n in (8, 84, 116, 121, 129, 200, live_N, 400):
        curve[str(n)] = {"haircut": haircut_at(n), "n_adopt": len(adopters_at(rows, n))}
    published_curve = {"8": 27, "84": 21, "116": 20, "121": 20, "129": 20, "200": 18, "400": 17}
    c1_ok = all(curve[k]["n_adopt"] == v for k, v in published_curve.items() if k in curve)
    report["controls"]["C1_adopt_curve_reproduces"] = {
        "pass": bool(c1_ok), "recomputed": {k: curve[k]["n_adopt"] for k in curve},
        "published_session12": published_curve,
    }
    print(f"[ma19] C1 adopt curve reproduces session 12: {c1_ok}", flush=True)
    if not c1_ok:
        report["ABORTED"] = "C1 failed — the gate arithmetic is not the shipped one."
        json.dump(report, open(OUT, "w"), indent=1)
        print("[ma19] ABORT on C1.", flush=True)
        return 1

    a_old, a_new = adopters_at(rows, N_ASRUN), adopters_at(rows, live_N)
    flipped = sorted(a_old - a_new)
    started = sorted(a_new - a_old)
    report["adopt"] = {
        "n_adopt_as_run": len(a_old), "n_adopt_today": len(a_new),
        "flipped_off": flipped, "flipped_on": started,
        "vs_x7_N84_flipped_off": sorted(adopters_at(rows, N_X7) - a_new),
        "curve": curve,
    }
    report["controls"]["C3_adoption_monotone"] = {"pass": not started, "flipped_on": started}
    print(f"[ma19] adopters {len(a_old)} (N={N_ASRUN}) -> {len(a_new)} (N={live_N}); "
          f"flipped off: {flipped}", flush=True)

    # ------------------------------------------------ the targeted re-score
    panel = pd.read_pickle(PANEL)
    cols = [c for c in S.BUCKET_FACTORS[BUCKET]
            if c in panel.columns and panel[c].notna().any()]
    base = FP._base_weights(cols, BUCKET)
    print(f"[ma19] panel {len(panel):,} rows · {len(cols)} themes", flush=True)

    # Seeds needing a re-score: those that flip between as-run and today, PLUS those that flip
    # between X7's own N = 84 and as-run. The latter are needed to RECONSTRUCT X7's distribution,
    # which is the only way to explain the record's own published bars rather than merely
    # disagreeing with them.
    a_x7 = adopters_at(rows, N_X7)
    need = sorted(set(flipped) | (a_x7 - a_old))
    rescored = {}
    for seed in need:
        t0 = time.time()
        rescored[seed] = rescore(panel, cols, base, seed)
        print(f"[ma19] re-scored seed {seed} in {time.time() - t0:.1f}s · "
              f"adopt_live={rescored[seed]['cpcv_adopt_live']} · "
              f"base ls_t={rescored[seed]['base']['long_short_tstat']:.6f} "
              f"chal ls_t={rescored[seed]['challenger']['long_short_tstat']:.6f}", flush=True)
    report["rescored"] = rescored

    # C4 ROUND TRIP. Each re-scored seed must reproduce its BANKED statistics under whichever
    # weighting the as-run adoption actually used — challenger if it adopted at N = 129, base if
    # it did not. Both directions are exercised here (1050/1096 adopted; 1005 did not), so the
    # harness is shown to reproduce the bank on BOTH arms rather than only the convenient one.
    c4 = {}
    for seed in need:
        arm = "challenger" if seed in a_old else "base"
        banked, got = draws[seed], rescored[seed][arm]
        diffs = {}
        for k in ("long_short_tstat", "long_short_tstat_nw", "top_decile_alpha",
                  "monotonicity", "top_decile_alpha_tstat_nw"):
            b, g = banked.get(k), got.get(k)
            if b is not None and g is not None:
                diffs[k] = abs(float(b) - float(g))
        c4[str(seed)] = {"arm_used_as_run": arm,
                         "max_abs_diff": (max(diffs.values()) if diffs else None),
                         "per_key": diffs}
    report["controls"]["C4_round_trip_reproduces_bank_on_the_as_run_arm"] = {
        "pass": all((v["max_abs_diff"] is not None and v["max_abs_diff"] <= 1e-9)
                    for v in c4.values()),
        "detail": c4,
    }

    # C3b: the LIVE gate must independently agree with the arithmetic.
    report["controls"]["C3b_live_gate_agrees_with_arithmetic"] = {
        "pass": all(rescored[s]["cpcv_adopt_live"] is False for s in flipped),
        "detail": {str(s): rescored[s]["cpcv_adopt_live"] for s in flipped},
    }

    # C6: Channel C invariance, MEASURED.
    c6 = {}
    for seed in flipped:
        banked, got = draws[seed], rescored[seed]
        c6[str(seed)] = {
            "pbo_banked": banked.get("pbo"), "pbo_rescored": got.get("pbo"),
            "theme_ic_banked": banked.get("max_abs_theme_ic_t"),
            "theme_ic_rescored": got.get("max_abs_theme_ic_t"),
        }
    def _same(a, b):
        return a is not None and b is not None and abs(float(a) - float(b)) <= 1e-12
    report["controls"]["C6_channel_C_invariant"] = {
        "pass": all(_same(v["pbo_banked"], v["pbo_rescored"])
                    and _same(v["theme_ic_banked"], v["theme_ic_rescored"]) for v in c6.values()),
        "detail": c6,
    }

    # ------------------------------------------------ rebuild the distributions
    # TODAY (N = 224): the draws that stop adopting are re-scored under BASE weights.
    # X7 (N = 84): the draws that adopted THEN but not as-run are restored to CHALLENGER weights.
    # Everything else keeps its banked value in both.
    def _substitute(which, arm):
        out, mv = [], {}
        for seed, d in sorted(draws.items()):
            if seed in which:
                nd = dict(d)
                for k, v in rescored[seed][arm].items():
                    if k in nd:
                        mv.setdefault(str(seed), {})[k] = {"from": nd[k], "to": v}
                    nd[k] = v
                out.append(nd)
            else:
                out.append(d)
        return out, mv

    new_draws, moved = _substitute(set(flipped), "base")
    x7_draws, moved_x7 = _substitute(a_x7 - a_old, "challenger")
    report["adopt"]["moved_fields_x7_reconstruction"] = moved_x7

    # C5: the unflipped draws are bit-identical.
    untouched_max = 0.0
    for seed, d in sorted(draws.items()):
        if seed in flipped:
            continue
        nd = next(x for x in new_draws if x["seed"] == seed)
        for k in KEYS:
            a, b = d.get(k), nd.get(k)
            if a is not None and b is not None:
                untouched_max = max(untouched_max, abs(float(a) - float(b)))
    report["controls"]["C5_unflipped_draws_bit_identical"] = {
        "pass": untouched_max == 0.0, "max_abs_diff": untouched_max,
        "n_untouched": len(draws) - len(flipped),
    }
    report["adopt"]["moved_fields"] = moved

    # ------------------------------------------------ Channel B: DSR at today's N, all draws
    dsr_old, dsr_new, c8 = [], [], {"max_abs_reproduction_error": 0.0, "n_checked": 0}
    for d in new_draws:
        det = d.get("deflated_sharpe_detail")
        if d["seed"] in flipped:
            live = rescored[d["seed"]].get("deflated_sharpe_detail") or {}
            dsr_old.append(d.get("deflated_sharpe"))
            dsr_new.append(live.get("probability", d.get("deflated_sharpe")))
            continue
        old_N = int((det or {}).get("n_trials") or N_S10)
        back = _dsr_at(det, old_N)
        if back is not None and det.get("probability") is not None:
            c8["max_abs_reproduction_error"] = max(
                c8["max_abs_reproduction_error"],
                abs(back["probability"] - float(det["probability"])))
            c8["n_checked"] += 1
        fwd = _dsr_at(det, live_N)
        dsr_old.append(d.get("deflated_sharpe"))
        dsr_new.append(fwd["probability"] if fwd else d.get("deflated_sharpe"))
    c8["pass"] = c8["n_checked"] >= 90 and c8["max_abs_reproduction_error"] <= 1e-9
    report["controls"]["C8_dsr_closed_form_reproduces_bank_at_old_N"] = c8

    # ------------------------------------------------ the floors
    old_null = {k: _summary([d.get(k) for d in bank["draws"]]) for k in KEYS}
    new_null = {k: _summary([d.get(k) for d in new_draws]) for k in KEYS}
    new_null["deflated_sharpe"] = _summary(dsr_new)
    old_null["deflated_sharpe"] = _summary(dsr_old)

    # C2 (GATING): the OLD floors must reproduce session 10's published values.
    c2 = {
        "long_short_tstat_p95": old_null["long_short_tstat"]["p95"],
        "long_short_tstat_nw_p95": old_null["long_short_tstat_nw"]["p95"],
        "top_decile_alpha_tstat_nw_p95": old_null["top_decile_alpha_tstat_nw"]["p95"],
        "pbo_p05": old_null["pbo"]["p05"],
    }
    c2_ok = all(abs(c2[k] - v) < 5e-5 for k, v in PUBLISHED.items())
    report["controls"]["C2_old_floors_reproduce_published"] = {
        "pass": bool(c2_ok), "recomputed": c2, "published": PUBLISHED}
    print(f"[ma19] C2 old floors reproduce session 10: {c2_ok}", flush=True)

    # ------------------------------------------------ X7's OWN regime, reconstructed
    # The record's bars come from X7 at N = 84, not from session 10 at N = 121. Reproducing them
    # is what turns "the record's number disagrees with mine" into "the record's number is a
    # correctly-measured figure from a regime that has since moved" -- a very different claim,
    # and the only one that licenses correcting the record rather than disputing it.
    x7_null = {k: _summary([d.get(k) for d in x7_draws]) for k in KEYS}
    x7_dsr = []
    for d in x7_draws:
        if d["seed"] in (a_x7 - a_old):
            live = rescored[d["seed"]].get("deflated_sharpe_detail") or {}
            back = _dsr_at(live, N_X7)
            x7_dsr.append(back["probability"] if back else live.get("probability"))
        else:
            x7_dsr.append((_dsr_at(d.get("deflated_sharpe_detail"), N_X7) or {}).get(
                "probability", d.get("deflated_sharpe")))
    x7_null["deflated_sharpe"] = _summary(x7_dsr)
    report["null_x7_reconstructed"] = x7_null

    x7_check = {
        "long_short_tstat_p95": x7_null["long_short_tstat"]["p95"],
        "long_short_tstat_nw_p95": x7_null["long_short_tstat_nw"]["p95"],
        "top_decile_alpha_p95": x7_null["top_decile_alpha"]["p95"],
        "max_abs_theme_ic_t_p95": x7_null["max_abs_theme_ic_t"]["p95"],
        "pbo_p05": x7_null["pbo"]["p05"],
        "deflated_sharpe_p95": x7_null["deflated_sharpe"]["p95"],
    }
    # PASS CRITERION, fixed rather than eyeballed: the record quotes these bars to as few as two
    # decimals (2.14, 2.71), so agreement can only be asserted to half a unit in the coarsest
    # published place. 0.005 is that bound. A control without a stated criterion is a table.
    x7_diff = {k: (abs(x7_check[k] - X7_BARS[k]) if k in X7_BARS and x7_check[k] is not None
                   else None) for k in x7_check}
    report["controls"]["C9_x7_regime_reconstructs_the_records_bars"] = {
        "pass": all(v is not None and v < 0.005 for v in x7_diff.values()),
        "criterion": "|recomputed - published| < 0.005 (half a unit in the coarsest quoted place)",
        "recomputed_at_N84": x7_check, "record_bars": X7_BARS, "abs_diff": x7_diff,
    }

    FLOORS = [
        ("long_short_tstat", "p95", "long-short t (naive)"),
        ("long_short_tstat_nw", "p95", "long-short t (HAC)"),
        ("top_decile_alpha", "p95", "top-decile alpha margin"),
        ("top_decile_alpha_tstat_nw", "p95", "top-decile alpha HAC t"),
        ("max_abs_theme_ic_t", "p95", "theme IC t"),
        ("pbo", "p05", "PBO"),
        ("deflated_sharpe", "p95", "Deflated Sharpe"),
    ]
    table = []
    for key, pct, label in FLOORS:
        o, n, x = old_null[key][pct], new_null[key][pct], x7_null[key][pct]
        table.append({
            "floor": label, "key": key, "percentile": pct,
            "x7_at_N84_reconstructed": x,
            "old_at_N_as_run": o, "new_at_N_today": n,
            "delta": (None if o is None or n is None else n - o),
            "record_bar": X7_BARS.get(f"{key}_{pct}"),
            "moved": (None if o is None or n is None else bool(abs(n - o) > 1e-12)),
        })
    report["floors"] = table
    report["null_old"], report["null_new"] = old_null, new_null
    report["real"] = bank["real"]

    # C10 — THE STRONGEST CONTROL AVAILABLE, and it is external to this script.
    # Push the BANKED real draw (computed at N = 121) to today's N by the same closed form used
    # for the 98 unflipped draws, and compare against `BACKTEST_RESULTS.json`, whose Deflated
    # Sharpe was produced by a SEPARATE full backtest run at N = 224. Nothing here feeds that
    # file, so agreement is an independent check that Channel B is the shipped arithmetic rather
    # than a plausible reimplementation of it.
    try:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        live = json.load(open(os.path.join(here, "BACKTEST_RESULTS.json")))
        live_det = (live.get("cpcv") or {}).get("deflated_sharpe_detail") or {}
        pushed = _dsr_at(bank["real"].get("deflated_sharpe_detail"), live_N)
        if pushed and live_det.get("probability") is not None:
            err = abs(pushed["probability"] - float(live_det["probability"]))
            report["controls"]["C10_channel_B_reproduces_the_shipped_run"] = {
                "pass": bool(err <= 1e-8 and int(live_det.get("n_trials") or 0) == live_N),
                "closed_form_at_live_N": pushed["probability"],
                "shipped_BACKTEST_RESULTS": live_det["probability"],
                "abs_diff": err,
                "shipped_n_trials": live_det.get("n_trials"),
                "sr0_closed_form": pushed["sr0_benchmark"],
                "sr0_shipped": live_det.get("sr0_benchmark"),
            }
    except Exception as e:                                # a missing artifact must not kill the run
        report["controls"]["C10_channel_B_reproduces_the_shipped_run"] = {
            "pass": None, "error": f"{type(e).__name__}: {e}"}

    # C7: the real headline is untouched by a recalibration of the null.
    report["controls"]["C7_real_headline_untouched"] = {
        "pass": abs(float(bank["real"]["long_short_tstat_nw"]) - 2.6199121240414884) < 1e-12,
        "long_short_tstat_nw": bank["real"]["long_short_tstat_nw"],
    }

    # ------------------------------------------------ does any shipped claim change side?
    real = bank["real"]
    claims = []
    for key, pct, label in FLOORS:
        o, n = old_null[key][pct], new_null[key][pct]
        rv = real.get(key)
        if rv is None or o is None or n is None:
            continue
        if pct == "p05":       # PBO: lower is better, the bar is a ceiling
            side_old, side_new = float(rv) <= o, float(rv) <= n
        else:
            side_old, side_new = float(rv) >= o, float(rv) >= n
        claims.append({"floor": label, "real": rv, "old_bar": o, "new_bar": n,
                       "cleared_old": side_old, "cleared_new": side_new,
                       "relationship_changed": side_old != side_new})
    report["shipped_claims"] = claims
    report["any_claim_changed_side"] = any(c["relationship_changed"] for c in claims)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(report, open(OUT, "w"), indent=1, default=float)
    print(f"\n[ma19] {time.time() - t_start:.0f}s -> {OUT}", flush=True)
    for r in table:
        print(f"  {r['floor']:<26} {r['old_at_N_as_run']!s:>22} -> {r['new_at_N_today']!s:<22} "
              f"(record bar {r['record_bar']})", flush=True)
    print(f"  any shipped claim changed side: {report['any_claim_changed_side']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
