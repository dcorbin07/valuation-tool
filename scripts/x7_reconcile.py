"""x7_reconcile.py — close the 8%-vs-7% `ls_t >= 2.0` discrepancy.  [SESSION 12, item 3]

X7 (2026-08-05) recorded that 8 of 100 pure-noise placebo draws produced a naive long-short
`t >= 2.0`. Session 10 re-ran the identical panel with the identical seeds 1000-1099 and got
**7**, with no draw anywhere near the 2.0 boundary (nearest 1.885 and 2.067) — so it is not
rounding. Session 10 recorded it as undiagnosable because X7's raw draws were never retained,
and the record has carried it as an open defect for two sessions.

THE HYPOTHESIS THIS SCRIPT TESTS, stated before it ran:

    The two sweeps ran at DIFFERENT PROJECT TRIAL COUNTS. `cpcv_validate`'s adopt gate is

        (med[best] - med[default]) > _trials_haircut(len(names)) * se

    and `_trials_haircut` is FLOORED AT THE RESEARCH LOG'S `N` (audit M1, `_trial_N`). X7's
    sweep was re-run at **N = 84**; session 10's artifact records **N = 121**. A larger `N` is a
    larger haircut, so adoption is MONOTONE DECREASING in `N` — a draw can stop adopting when
    `N` rises and can never start. `scripts/placebo.py` then feeds the ADOPTED weights to
    `quantile_backtest`, and X7's own post-hoc split measured that adopting draws average
    long-short t +1.343 against -0.065 for non-adopters. So one draw dropping out of adoption
    can drop its `ls_t` below 2.0 — an 8 -> 7 change, with no draw moving near the boundary.

    The recorded adopt rates are consistent with exactly that: **21% at N = 84 (M1), 20% at
    N = 121 (session 10's retained artifact)**. One draw.

WHAT WOULD FALSIFY IT: if no draw's adopt decision differs between the two haircuts, or if the
draw that differs does not cross `ls_t = 2.0`, the hypothesis is dead and the discrepancy has
another cause. Both outcomes are reported.

Monotonicity is what makes this cheap: only draws that did NOT adopt at N = 121 can have
adopted at N = 84, so the search set is those draws alone. This script recomputes the adopt
margin for each (one `cpcv_validate` per draw), identifies every draw whose decision flips
between the two haircuts, and for each flipped draw scores `quantile_backtest` under BOTH the
base weights and the challenger's, giving the `ls_t` each sweep would have recorded.

    python -m scripts.x7_reconcile --shard 0 --n-shards 4
    python -m scripts.x7_reconcile --combine
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from valuation.edge import fundamental_panel as FP     # noqa: E402

HALFLIFE, HORIZON = 1260, 63
SEEDS = list(range(1000, 1100))
N_X7, N_S10 = 84, 121                                   # the two trial counts in question

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `data/` is not materialised inside a git worktree; fall back to the primary checkout.
_CANDIDATES = [os.path.join(ROOT, "data", "free_analysis"),
               os.path.abspath(os.path.join(ROOT, "..", "..", "..", "data", "free_analysis"))]
OUTDIR = next((p for p in _CANDIDATES if os.path.isdir(p)), _CANDIDATES[0])
PANEL = os.path.join(OUTDIR, "panel_corrected_69d.pkl")
OUT = os.path.join(OUTDIR, "X7_RECONCILE.json")


def haircut_at(n_trials, n_names):
    """`_trials_haircut` reproduced explicitly, so the two N's are visible side by side."""
    return float(np.sqrt(2.0 * np.log(max(2, int(n_names), int(n_trials)))))


def one(panel, cols, base, seed):
    pl = FP.placebo_panel(panel, seed=seed)
    cpcv = FP.cpcv_validate(pl, cols, base, halflife_days=HALFLIFE, horizon=HORIZON) or {}
    ad = cpcv.get("adopt_detail") or {}
    margin, se = ad.get("margin"), ad.get("se")
    n_names = 9                                          # 8 schemes + current-default
    row = {"seed": int(seed), "adopt_as_run": bool(cpcv.get("adopt")),
           "recommend": cpcv.get("recommend"), "margin": margin, "se": se,
           "folds_positive": ad.get("folds_positive"),
           "median_oos_ic_best": ad.get("median_oos_ic_best"),
           "median_oos_ic_default": ad.get("median_oos_ic_default"),
           "haircut_as_run": ad.get("haircut"), "n_trials_as_run": ad.get("n_trials_used")}

    # The gate's two N-independent conditions must hold before the haircut can matter at all.
    gate_ok = (se is not None and se > 0 and margin is not None
               and (ad.get("folds_positive") or 0) >= 0.6
               and (ad.get("median_oos_ic_best") or 0) > 0)
    for tag, n in (("x7", N_X7), ("s10", N_S10)):
        h = haircut_at(n, n_names)
        row[f"haircut_{tag}"] = h
        row[f"adopt_{tag}"] = bool(gate_ok and margin > h * se)

    row["flips"] = row["adopt_x7"] != row["adopt_s10"]

    # Only a flipped draw needs the second scoring pass; for everything else the recorded
    # long-short t already IS the number both sweeps would have seen.
    if row["flips"]:
        chal = cpcv.get("challenger_weights_cols") or dict(base)
        qb_base = FP.quantile_backtest(pl, cols, base, n_q=10, horizon=HORIZON) or {}
        qb_chal = FP.quantile_backtest(pl, cols, chal, n_q=10, horizon=HORIZON) or {}
        row["ls_t_base_weights"] = qb_base.get("long_short_tstat")
        row["ls_t_challenger_weights"] = qb_chal.get("long_short_tstat")
        row["ls_t_nw_base_weights"] = qb_base.get("long_short_tstat_nw")
        row["ls_t_nw_challenger_weights"] = qb_chal.get("long_short_tstat_nw")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=1)
    ap.add_argument("--seeds", type=str, default="")
    ap.add_argument("--combine", action="store_true")
    a = ap.parse_args()

    if a.combine:
        rows = []
        for i in range(64):
            p = OUT.replace(".json", f".shard{i}.json")
            if os.path.exists(p):
                rows += json.load(open(p))["rows"]
        rows.sort(key=lambda r: r["seed"])
        flips = [r for r in rows if r["flips"]]
        out = {
            "test": "X7 vs session-10 placebo reconciliation: does the trial count N move ls_t?",
            "panel": PANEL, "seeds": "1000..1099", "n_rows": len(rows),
            "n_trials_x7": N_X7, "n_trials_session10": N_S10,
            "haircut_x7": haircut_at(N_X7, 9), "haircut_session10": haircut_at(N_S10, 9),
            "n_adopt_at_x7_N": sum(1 for r in rows if r["adopt_x7"]),
            "n_adopt_at_session10_N": sum(1 for r in rows if r["adopt_s10"]),
            "flipped_seeds": [r["seed"] for r in flips],
            "flipped": flips,
            "rows": rows,
        }
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
        print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
        return

    # Panel, themes and base weights are taken from `scripts.placebo`'s own constants rather
    # than restated here, so this reconciliation cannot drift from the sweep it reconciles.
    from scripts.placebo import BUCKET                     # noqa: E402
    from valuation.screener import settings as S          # noqa: E402

    with open(PANEL, "rb") as f:
        panel = pickle.load(f)
    cols = [c for c in S.BUCKET_FACTORS[BUCKET]
            if c in panel.columns and panel[c].notna().any()]
    base = FP._base_weights(cols, BUCKET)

    seeds = ([int(s) for s in a.seeds.split(",") if s.strip()] if a.seeds
             else [s for i, s in enumerate(SEEDS) if i % a.n_shards == a.shard])
    print(f"[x7rec] shard {a.shard}/{a.n_shards} · {len(seeds)} seeds · {len(cols)} themes "
          f"· haircut x7(N={N_X7})={haircut_at(N_X7, 9):.5f} "
          f"s10(N={N_S10})={haircut_at(N_S10, 9):.5f}", flush=True)

    rows = []
    import time
    for i, sd in enumerate(seeds, 1):
        t0 = time.time()
        r = one(panel, cols, base, sd)
        rows.append(r)
        print(f"[x7rec] {i}/{len(seeds)} seed {sd} margin {r['margin']} se {r['se']} "
              f"adopt x7={r['adopt_x7']} s10={r['adopt_s10']} flips={r['flips']} "
              f"({time.time()-t0:.0f}s)", flush=True)
        p = OUT.replace(".json", f".shard{a.shard}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"rows": rows}, f, indent=1)


if __name__ == "__main__":
    main()
