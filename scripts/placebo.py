#!/usr/bin/env python3
"""placebo.py — what does this pipeline report when the signal is definitionally nothing?  [X7]

The options bot has a no-edge self-test. The equity pipeline has never had one. Every threshold
this project uses -- the IC *t* > 2.0 bar, the PBO < 50% bar, the 0.25 *t*-gain margin on the
held-out gate, the informal "1% alpha" margin -- was chosen by convention, and none has ever been
measured against what THIS machinery produces on a signal known to be worthless. Until that floor
exists, "PBO 73.3%" and "long-short t 2.836" are numbers without a scale.

WHAT THE PLACEBO IS. `fundamental_panel.placebo_panel` permutes the signal columns WITHIN each
rebalance date, as a block. Preserved exactly: each theme's per-date distribution, the missingness
pattern (it travels with the row), and the cross-theme correlation matrix. Untouched: `fwd_ret`,
`marketcap`, `sector`. Destroyed: the association between signal and return, and nothing else.

WHAT IS RUN PER ITERATION -- the same sequence `run_backtests` runs, in the same order, so the
floor is the floor of the ACTUAL pipeline and not of a simplified stand-in:

    cpcv_validate      -> PBO, Deflated Sharpe, and the adopt/reject on the weight scheme
    (the CPCV verdict then chooses the weights, exactly as the real run does)
    quantile_backtest  -> long-short t, top-decile alpha, monotonicity
    theme_ic           -> the max |t| across themes, which is what a "is this theme real"
                          decision actually looks at
    holdout_theme_validate -> the false-positive rate of the gate that produced
                          `low_risk = confirmed`
    cost_breakeven_bps -> what breakeven looks like on noise

The panel is built ONCE and re-permuted, because building it is ~12 minutes and permuting it is
milliseconds. That is not a shortcut: the null is about the SCORING machinery, and rebuilding the
same panel N times would consume the entire budget to produce N identical panels.

Thresholds are pre-registered in HANDOFF_edge_audit.md Part 4 and are NOT restated from results.

    python -m scripts.placebo --panel <panel.pkl> --n 100 --out placebo_results.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np
import pandas as pd

from valuation.edge import fundamental_panel as FP
from valuation.screener import settings as S

BUCKET = "established"
HALFLIFE = 1260
HORIZON = 63


def _q(xs, p):
    """Percentile over the values that exist, or None if too few to mean anything."""
    v = [float(x) for x in xs if x is not None and x == x]
    return (float(np.percentile(v, p)) if len(v) >= 2 else None)


def _summary(xs):
    v = [float(x) for x in xs if x is not None and x == x]
    if not v:
        return {"n": 0}
    return {"n": len(v), "mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0,
            "min": float(np.min(v)), "p05": _q(v, 5), "p50": _q(v, 50), "p95": _q(v, 95),
            "p025": _q(v, 2.5), "p975": _q(v, 97.5), "max": float(np.max(v)),
            # Monte Carlo standard error of the MEAN. The committed thresholds are read off
            # percentiles, whose MC error is larger; this is the honest floor on precision.
            "mc_se_mean": (float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else None)}


def one_iteration(panel, cols, base, seed, permute=True, costs=True):
    """One complete pass of the real pipeline over one placebo draw.

    `permute=False` runs the identical code path on the UNPERMUTED panel, which is how the
    real result is measured here. Measuring it through this same function rather than
    quoting the results file is deliberate: it proves the harness reproduces the shipped
    pipeline before any placebo is drawn, so a gap between the two is visible as a harness
    bug rather than being read as a finding.
    """
    pl = FP.placebo_panel(panel, seed=seed) if permute else panel

    cpcv = FP.cpcv_validate(pl, cols, base, halflife_days=HALFLIFE, horizon=HORIZON) or {}
    # Mirror run_backtests exactly: CPCV is the authority, and only a CPCV `adopt` moves the
    # weights off the defaults. Getting this wrong would measure a floor for a pipeline nobody
    # runs.
    if not cpcv.get("status") and cpcv.get("adopt"):
        rec = cpcv.get("recommended_weights_cols") or base
    else:
        rec = base

    qb = FP.quantile_backtest(pl, cols, rec, n_q=10, horizon=HORIZON) or {}
    # theme_ic returns the per-theme blocks at the TOP level, keyed by theme name. The
    # "themes" wrapper seen in BACKTEST_RESULTS.json is added by the results writer, not by
    # this function — reading it here yields {} and a silent max-|t| of None on every draw.
    themes = FP.theme_ic(pl) or {}
    themes = themes.get("themes") if isinstance(themes.get("themes"), dict) else themes
    hv = FP.holdout_theme_validate(pl, cols) or {}

    bk = {}
    if costs:
        try:
            bk = FP.cost_breakeven_bps(pl, cols, rec, horizon=HORIZON) or {}
        except Exception as e:                   # a cost failure must not kill the sweep
            bk = {"error": f"{type(e).__name__}: {e}"}

    t_abs = [abs(v.get("ic_tstat")) for v in themes.values()
             if isinstance(v, dict) and v.get("ic_tstat") is not None]
    verdicts = hv.get("verdicts") or {}

    return {
        "seed": int(seed),
        "long_short_tstat": qb.get("long_short_tstat"),
        "long_short_ann": qb.get("long_short_ann"),
        "top_decile_alpha": qb.get("top_decile_alpha"),
        "monotonicity": qb.get("monotonicity"),
        "equal_weight_ann": qb.get("equal_weight_ann"),
        "n_periods": qb.get("n_periods"),
        "pbo": cpcv.get("pbo"),
        "deflated_sharpe": cpcv.get("deflated_sharpe"),
        # AUDIT M1 — bank the DSR's INTERNALS, not just its probability. X7's first sweep stored
        # the scalar only, and when M1 replaced the trial count N=8 with the measured equity
        # count N=84 the whole 3.4-hour sweep had to be re-run to move one column: DSR depends on
        # N through `sr0`, and (sharpe, var_sr, n_trials) cannot be recovered from Phi(.) alone.
        # With these four numbers per draw, any future re-denomination is arithmetic.
        "deflated_sharpe_detail": cpcv.get("deflated_sharpe_detail"),
        "cpcv_adopt": bool(cpcv.get("adopt")),
        "cpcv_recommend": cpcv.get("recommend"),
        "max_abs_theme_ic_t": (max(t_abs) if t_abs else None),
        "n_themes_ic_t_over_2": int(sum(1 for t in t_abs if t >= 2.0)),
        "holdout_confirmed": sorted([c for c, v in verdicts.items() if v == "confirmed"]),
        "holdout_any_confirmed": any(v == "confirmed" for v in verdicts.values()),
        "holdout_n_confirmed": int(sum(1 for v in verdicts.values() if v == "confirmed")),
        "holdout_n_not_replicated": int(sum(1 for v in verdicts.values() if v == "not_replicated")),
        "breakeven_one_way_bps": bk.get("breakeven_one_way_bps"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="X7 — placebo through the full pipeline.")
    ap.add_argument("--panel", required=True, help="pickled scored panel (EDGE_PANEL_PICKLE dump)")
    ap.add_argument("--n", type=int, default=100, help="placebo draws")
    ap.add_argument("--out", default="placebo_results.json")
    ap.add_argument("--seed0", type=int, default=1000, help="first seed; draws are seed0..seed0+n-1")
    ap.add_argument("--no-costs", action="store_true",
                    help="skip cost_breakeven_bps (13 turnover simulations per draw). Use only "
                         "if it dominates the per-draw cost; the omission is recorded in the "
                         "output so a missing block never looks like a measured zero.")
    args = ap.parse_args(argv)
    costs = not args.no_costs

    panel = pd.read_pickle(args.panel)
    cols = [c for c in S.BUCKET_FACTORS[BUCKET]
            if c in panel.columns and panel[c].notna().any()]
    base = FP._base_weights(cols, BUCKET)
    dates = sorted(panel["date"].unique())

    print(f"[placebo] panel {len(panel):,} rows · {len(dates)} dates "
          f"({dates[0]} -> {dates[-1]}) · {len(cols)} themes: {', '.join(cols)}", flush=True)
    print(f"[placebo] permuting {len(FP.placebo_signal_cols(panel))} signal columns per date", flush=True)

    # The REAL result on this same panel, through the identical code path. Without it the null
    # distribution has nothing to be a null FOR, and it also proves the harness reproduces the
    # shipped pipeline before any placebo is drawn.
    print("[placebo] measuring the real (unpermuted) panel first ...", flush=True)
    t0 = time.time()
    real = one_iteration(panel, cols, base, seed=0, permute=False, costs=costs)
    real["_note"] = "REAL panel — placebo_panel NOT applied; same code path as every draw"
    per_iter = time.time() - t0
    print(f"[placebo] real: ls_t={real['long_short_tstat']} alpha={real['top_decile_alpha']} "
          f"pbo={real['pbo']} dsr={real['deflated_sharpe']} ({per_iter:.1f}s/iteration)", flush=True)
    print(f"[placebo] {args.n} draws -> about {per_iter * args.n / 60.0:.0f} min", flush=True)

    draws = []
    for k in range(args.n):
        seed = args.seed0 + k
        t1 = time.time()
        try:
            d = one_iteration(panel, cols, base, seed=seed, costs=costs)
        except Exception as e:
            print(f"[placebo] draw {k} (seed {seed}) FAILED: {type(e).__name__}: {e}", flush=True)
            continue
        draws.append(d)
        print(f"[placebo] {k + 1}/{args.n} seed={seed} ls_t={d['long_short_tstat']} "
              f"alpha={d['top_decile_alpha']} pbo={d['pbo']} dsr={d['deflated_sharpe']} "
              f"maxIC_t={d['max_abs_theme_ic_t']} conf={d['holdout_confirmed']} "
              f"({time.time() - t1:.1f}s)", flush=True)
        # Written every draw: a sweep killed at draw 63 must still be usable.
        _write(args.out, real, draws, args, costs)

    _write(args.out, real, draws, args, costs)
    print(f"\n[placebo] {len(draws)}/{args.n} draws -> {args.out}", flush=True)
    return 0


def _write(path, real, draws, args, costs=True):
    keys = ("long_short_tstat", "top_decile_alpha", "monotonicity", "pbo", "deflated_sharpe",
            "max_abs_theme_ic_t", "equal_weight_ann", "long_short_ann",
            "breakeven_one_way_bps", "n_themes_ic_t_over_2")
    n = len(draws)
    out = {
        "test": "X7 — placebo through the full pipeline",
        "costs_measured": bool(costs),
        "instrument": "fundamental_panel.placebo_panel: within-date block permutation of the "
                      "theme and z_* columns; fwd_ret / marketcap / sector untouched",
        "n_draws": n,
        "n_requested": args.n,
        "seeds": f"{args.seed0}..{args.seed0 + args.n - 1}",
        "panel": args.panel,
        # AUDIT M1 — which denominator this sweep ran at, stamped on the file. X7's first sweep
        # was silently N=8 on both sides, and nothing in its output said so; the claim it
        # supported ("the Deflated Sharpe survives calibration") had to be marked PROVISIONAL a
        # session later. A sweep that does not record its own N cannot be read afterwards.
        "trial_count": _trials_stamp(real),
        "real": real,
        "null": {k: _summary([d.get(k) for d in draws]) for k in keys},
        "rates": {
            # The quantities the committed thresholds are actually read off.
            "cpcv_adopt": (sum(1 for d in draws if d.get("cpcv_adopt")) / n if n else None),
            "holdout_any_confirmed": (sum(1 for d in draws if d.get("holdout_any_confirmed")) / n
                                      if n else None),
            "long_short_t_over_2": (sum(1 for d in draws
                                        if (d.get("long_short_tstat") or 0) >= 2.0) / n if n else None),
            "long_short_t_over_3": (sum(1 for d in draws
                                        if (d.get("long_short_tstat") or 0) >= 3.0) / n if n else None),
            "max_theme_ic_t_over_2": (sum(1 for d in draws
                                          if (d.get("max_abs_theme_ic_t") or 0) >= 2.0) / n if n else None),
            "pbo_under_50": (sum(1 for d in draws if (d.get("pbo") is not None and d["pbo"] < 0.5))
                             / n if n else None),
            "deflated_sharpe_over_95": (sum(1 for d in draws
                                            if (d.get("deflated_sharpe") or 0) >= 0.95) / n if n else None),
            "top_decile_alpha_over_1pp": (sum(1 for d in draws
                                              if (d.get("top_decile_alpha") or 0) >= 0.01) / n if n else None),
        },
        "holdout_confirmed_by_theme": _confirm_counts(draws),
        "draws": draws,
    }
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


def _trials_stamp(real):
    """The N the Deflated Sharpe was computed against, read off the run rather than assumed."""
    d = (real or {}).get("deflated_sharpe_detail") or {}
    try:
        from valuation.edge.research_log import detail as _rl
        log = _rl()
    except Exception:                                                     # noqa: BLE001
        log = {"available": False}
    return {"n_trials_used": d.get("n_trials"),
            "n_trials_from_weight_schemes": d.get("n_trials_from_weight_schemes"),
            "n_trials_from_research_log": d.get("n_trials_from_research_log"),
            "source": d.get("n_trials_source"),
            "research_log_available": bool(log.get("available"))}


def _confirm_counts(draws):
    counts = {}
    for d in draws:
        for c in d.get("holdout_confirmed") or []:
            counts[c] = counts.get(c, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    sys.exit(main())
