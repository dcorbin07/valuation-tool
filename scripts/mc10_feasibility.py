# -*- coding: utf-8 -*-
"""MC10 STEP 0 — FEASIBILITY. ZERO TRIALS, and the mean difference is NOT computed.

`MB15` separation: this pass measures DISPERSION and COVERAGE only. It banks per-date turnover,
realised cost, the correlation between the two books' net series, and the paired HAC(1) standard
error of their annualised difference -- and it **never reports or banks the mean of that
difference**, which is the outcome. A standard error is a statement about how precisely a thing
could be measured; the thing itself belongs to the register, which does not exist yet.

THE GATE, PRE-COMMITTED BY THE BRIEF AND NOT BY ME: if the 80%-power MDE at crit 2.0 exceeds
**0.0083** -- the artifact's own gross gap, `0.0800 - 0.0717`, which is the CEILING of any net
gap because costs can only subtract -- the register is UNPOWERED BY CONSTRUCTION, the item
closes as "label only", and nothing is charged.

EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED. `V2G` established and `R1-VAR` re-confirmed that
no calibrated floor exists for a paired within-panel difference; `MB8`'s 0.1106pp and `V2G`'s
0.9354pp bracket the class by a factor of 8.5.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import research_log as RL                          # noqa: E402
from valuation.edge import power_gate as PG                            # noqa: E402
from valuation.edge.fundamental_panel import (composite_from_frame,    # noqa: E402
                                              one_way_cost_bps,
                                              _nw_tstat, COST_BPS_MICRO)
from valuation.screener.cross_sectional import zscore                  # noqa: E402
#: The deployed seven at 0.125, IMPORTED from `SECTOR-NEUTRAL-B6` rather than retyped -- `W-1`'s
#: `K4` fired against a correct panel for exactly that error. `composite_from_frame`
#: renormalises by present-weight mass, so seven at 0.125 IS the deployed 1/7 the brief names.
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT         # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
OUT = os.path.join(FA, "MC10_FEASIBILITY.json")

#: The brief's gate. The artifact's gross gap is the ceiling of any NET gap, because costs
#: subtract from both books and the SW book trades at least as much (C5).
GATE_EFFECT = 0.0083
HORIZON = 63
N_Q = 10

#: `C1`'s targets, from the shipped artifact.
C1 = {"top_decile_alpha": 0.071741423321,
      "annual_turnover": 2.6069687969064415,
      "realised_one_way_bps": 33.359867748,
      "net_alpha": 0.0606965408}
#: `C2`'s target -- the artifact's own "signal weighted" figure.
C2_TARGET = 0.08001508891469325


def _hot_score(comp: np.ndarray) -> np.ndarray:
    """`screen.py:339` -- the LIVE hot score is the composite's PERCENTILE RANK, not its level.

        scored["hot_score"] = scored["composite"].rank(pct=True) * 99 + 1

    Reproduced rather than approximated, because it is the whole reason the served weighting is
    a different object from the artifact's: a rank transform destroys the level information the
    artifact's `clip(composite, 0, None)` weights by.
    """
    return pd.Series(comp).rank(pct=True).to_numpy() * 99.0 + 1.0


def _sw_weights(hot: np.ndarray, tickers) -> dict:
    """The LIVE weighting, IMPORTED as ONE CODE OBJECT from `valquo_index.build_index`.

    `build_index` is called with the decile's own names, `large_cap_min=0` so it re-filters
    nothing and `top_n=len(rows)` so it re-selects nothing -- membership is fixed by the caller
    and only the weighting is taken. `held=None`, so the no-trade band cannot fire and change
    the book underneath the comparison.
    """
    from valuation.edge.valquo_index import build_index
    rows = [{"ticker": str(t), "hot_score": float(h), "price": 1.0, "market_cap": 1e12}
            for t, h in zip(tickers, hot)]
    out = build_index(rows, large_cap_min=0.0, weighting="score",
                      top_n=len(rows), held=None)
    # The key is "positions" (valquo_index.py:272). `weight` there is ROUNDED to 5dp for
    # display, so the vector is re-normalised by the caller rather than trusted to sum to 1.
    w = {p["ticker"]: float(p["weight"]) for p in out["positions"]}
    return w, out


def main() -> int:
    panel = pd.read_pickle(PANEL)
    neq = RL.detail()["by_domain"]["equity"]
    hurdle = PG.critical_value(n_trials=neq)
    cols = [c for c in DEPLOYED if c in panel.columns]
    weights = {c: BASE_WEIGHT for c in cols}

    dates = sorted(panel["date"].unique())
    rec = []
    prev_ew, prev_sw, prev_cost = {}, {}, {}
    cap_binds_dates = 0
    max_w_seen = 0.0
    alpha_series = []
    sw_gross_series, ew_gross_series = [], []

    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)
        fwd = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(fwd)
        comp, fwd = comp[ok], fwd[ok]
        tk = sub["ticker"].to_numpy()[ok]
        mc = (pd.to_numeric(sub["market_cap"], errors="coerce").to_numpy()[ok]
              if "market_cap" in sub.columns else np.full(len(fwd), np.nan))
        if len(fwd) < N_Q * 3:
            continue
        # SHIPPED MEMBERSHIP, the brief's rule: argsort(-composite), n_q=10, first bucket.
        order = np.argsort(-comp)
        top = np.array_split(order, N_Q)[0]
        t_tk, t_fwd, t_mc, t_comp = tk[top], fwd[top], mc[top], comp[top]

        alpha_series.append(float(np.mean(t_fwd) - np.mean(fwd)))
        ew_gross_series.append(float(np.mean(t_fwd)))
        # the ARTIFACT's own signal weighting, for C2 -- clip(composite,0), uncapped
        _wp = np.clip(t_comp, 0.0, None)
        sw_gross_series.append(float(np.sum(_wp * t_fwd) / _wp.sum()) if _wp.sum() > 0
                               else float(np.mean(t_fwd)))

        # the SERVED weighting
        hot = _hot_score(comp)[top]
        wmap, _idx = _sw_weights(hot, t_tk)
        w_sw = np.array([wmap.get(str(t), 0.0) for t in t_tk], dtype=float)
        s = w_sw.sum()
        w_sw = w_sw / s if s > 0 else np.full(len(t_tk), 1.0 / len(t_tk))
        w_ew = np.full(len(t_tk), 1.0 / len(t_tk))
        max_w_seen = max(max_w_seen, float(w_sw.max()))
        if float(w_sw.max()) >= 0.08 - 1e-9:
            cap_binds_dates += 1

        cur_cost = {str(t): (one_way_cost_bps(m) if np.isfinite(m) else COST_BPS_MICRO)
                    for t, m in zip(t_tk, t_mc)}

        def _trade(prev, cur):
            turn = cost = num = den = 0.0
            for t in set(prev) | set(cur):
                dw = abs(cur.get(t, 0.0) - prev.get(t, 0.0))
                if dw <= 0:
                    continue
                bps = cur_cost.get(t, prev_cost.get(t, COST_BPS_MICRO))
                turn += dw
                cost += dw * bps * 1e-4
                num += dw * bps
                den += dw
            return turn, cost, num, den

        cur_ew = {str(t): float(w) for t, w in zip(t_tk, w_ew)}
        cur_sw = {str(t): float(w) for t, w in zip(t_tk, w_sw)}
        turn_ew, cost_ew, num_ew, den_ew = _trade(prev_ew, cur_ew)
        turn_sw, cost_sw, num_sw, den_sw = _trade(prev_sw, cur_sw)

        g_ew = float(np.sum(w_ew * t_fwd))
        g_sw = float(np.sum(w_sw * t_fwd))
        rec.append({"date": str(d)[:10], "n_top": int(len(t_tk)),
                    "turn_ew": turn_ew, "turn_sw": turn_sw,
                    "cost_ew": cost_ew, "cost_sw": cost_sw,
                    "bps_num_ew": num_ew, "bps_den_ew": den_ew,
                    "bps_num_sw": num_sw, "bps_den_sw": den_sw,
                    "net_ew": g_ew - cost_ew, "net_sw": g_sw - cost_sw,
                    "max_w_sw": float(w_sw.max())})

        grown_ew = {t: w * (1.0 + r) for t, w, r in zip(map(str, t_tk), w_ew, t_fwd)}
        grown_sw = {t: w * (1.0 + r) for t, w, r in zip(map(str, t_tk), w_sw, t_fwd)}
        tew, tsw = sum(grown_ew.values()) or 1.0, sum(grown_sw.values()) or 1.0
        prev_ew = {t: v / tew for t, v in grown_ew.items()}
        prev_sw = {t: v / tsw for t, v in grown_sw.items()}
        prev_cost = cur_cost

    df = pd.DataFrame(rec)
    ppy = 252.0 / HORIZON

    # ---- the PAIRED SE, and the mean is never reported. `_nw_tstat` returns mean/se, so the
    # se is recovered as |mean/t| -- the same route `W-1` and `PKG-MB20` used -- and the mean
    # is discarded in the same expression that consumes it.
    diff = (df["net_sw"] - df["net_ew"]).to_numpy(dtype=float)
    diff = diff[np.isfinite(diff)]
    _t = _nw_tstat(diff.tolist(), lag=1)
    _m = float(diff.mean())
    se_period = abs(_m / _t) if (_t and np.isfinite(_t) and _t != 0) else float("nan")
    del _m, _t                       # the outcome is NOT part of this pass
    se_ann = se_period * ppy

    out = {
        "item": "MC10", "step": "0 FEASIBILITY", "trials": 0,
        "equity_N": neq, "hurdle": hurdle,
        "panel": {"dates": int(len(df)), "mean_top_decile_size": float(df["n_top"].mean())},
        "turnover": {
            "ew_annual": float(df["turn_ew"].mean() / 2.0 * ppy),
            "sw_annual": float(df["turn_sw"].mean() / 2.0 * ppy)},
        "realised_one_way_bps": {
            "ew": float(df["bps_num_ew"].sum() / max(1e-12, df["bps_den_ew"].sum())),
            "sw": float(df["bps_num_sw"].sum() / max(1e-12, df["bps_den_sw"].sum()))},
        "cost_drag_ann": {"ew": float(df["cost_ew"].mean() * ppy),
                          "sw": float(df["cost_sw"].mean() * ppy)},
        "cap": {"max_weight_seen": max_w_seen, "dates_where_8pct_cap_binds": cap_binds_dates,
                "ever_binds": bool(cap_binds_dates > 0)},
        "rho_net_ew_sw": float(np.corrcoef(df["net_ew"], df["net_sw"])[0, 1]),
        "paired_se": {"per_period": se_period, "annualised": se_ann,
                      "n": int(diff.size),
                      "note": ("HAC(1). The MEAN of this difference is deliberately NOT "
                               "computed, reported or banked -- it is the outcome and this is "
                               "the feasibility pass (MB15 separation).")},
        "C1_targets": C1,
        "C1_measured": {
            "top_decile_alpha": float(np.mean(alpha_series) * ppy),
            "annual_turnover": float(df["turn_ew"].mean() / 2.0 * ppy),
            "realised_one_way_bps": float(df["bps_num_ew"].sum()
                                          / max(1e-12, df["bps_den_ew"].sum()))},
        "C2_target_artifact_signal_weighted_alpha": C2_TARGET,
        "C2_measured_artifact_rule": float((np.mean(sw_gross_series)
                                            - np.mean(ew_gross_series)) * ppy
                                           + np.mean(alpha_series) * ppy
                                           - np.mean(alpha_series) * ppy),
    }
    # the artifact's figure is sw_ann - ew_universe_ann; rebuild it on its own terms
    ew_universe = []
    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)
        fwd = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(fwd)
        if int(ok.sum()) < N_Q * 3:
            continue
        ew_universe.append(float(np.mean(fwd[ok])))
    out["C2_measured_artifact_rule"] = float((np.mean(sw_gross_series)
                                              - np.mean(ew_universe)) * ppy)

    # ---- RUN_RULES A11, from power_gate so the arithmetic is not retyped
    out["A11_crit_2.0_UNCALIBRATED"] = PG.state(effect=GATE_EFFECT, se=se_ann, crit=2.0)
    out["A11_hurdle_UNCALIBRATED"] = PG.state(effect=GATE_EFFECT, se=se_ann, n_trials=neq)
    mde80_crit2 = (2.0 + PG.Z_POWER_CONVENTION) * se_ann
    mde50_crit2 = 2.0 * se_ann
    out["mde"] = {"gate_effect": GATE_EFFECT,
                  "mde50_crit2_UNCALIBRATED": mde50_crit2,
                  "mde80_crit2_UNCALIBRATED": mde80_crit2,
                  "mde50_hurdle_UNCALIBRATED": hurdle * se_ann,
                  "mde80_hurdle_UNCALIBRATED": (hurdle + PG.Z_POWER_CONVENTION) * se_ann}
    out["GATE"] = {
        "rule": "UNPOWERED-BY-CONSTRUCTION iff MDE80 at crit 2.0 > 0.0083",
        "mde80_crit2": mde80_crit2, "threshold": GATE_EFFECT,
        "fires": bool(mde80_crit2 > GATE_EFFECT)}

    df.to_pickle(os.path.join(FA, "MC10_FEASIBILITY_PERDATE.pkl"))
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
