#!/usr/bin/env python3
"""R5 + R6 — the two re-derivations audit B12 voided.

Executes `PREREG_r5_r6_alphabetical_rerun.md` unmodified. ONE panel build with
`keep_numbers=True`; every signal a z_ column on that one frame.

  R5  neg_ret_1m, neg_max_ret, neg_idio_vol   (short-term reversal, MAX/lottery, idio vol)
  R6  sm_conviction, sm_holders, sm_avg_position  (SF3 smart-money conviction)

Registration is MEASUREMENT, not SCORING (the S2 `cash_op_prof` pattern), and C1 GATES on the
composite coming back bit-identical.

Run:  python -m scripts.r5_r6_alphabetical_rerun --data-dir data/backtest
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

from valuation.config import CONFIG as CFG                    # noqa: E402
from valuation.edge import fundamental_panel as FP            # noqa: E402
from valuation.edge import statistics as ST                   # noqa: E402
from valuation.edge.data_providers import WRDSProvider        # noqa: E402
from valuation.screener import settings as S                  # noqa: E402

R5_SIGNALS = ("neg_ret_1m", "neg_max_ret", "neg_idio_vol")
R6_SIGNALS = ("sm_conviction", "sm_holders", "sm_avg_position")
ARMS = R5_SIGNALS + R6_SIGNALS
# free by-products: already registered, already measured, charged NOTHING (register 4)
BYPRODUCTS = ("neg_vol", "neg_beta", "sm_breadth", "inst_breadth", "sm_elite_conviction")
THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
MIN_COVERAGE = 0.30          # register 2.5 - pead_drift's own precedent
MIN_DATES_PER_HALF = 24
MIN_NAMES = 20
N_PERM = 500
SEED = 20260813
X7_THEME_BAR = 2.71          # reported as a LABELLED EXTRAPOLATION, never the verdict
CONVENTION_BAR = 2.0         # the historical convention, for continuity only

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

# The four live sites quoting voided figures (register 0, control C5).
STALE_SITES = {
    "settings.py:222-224": ("the three anomalies 'all wrong-signed here', median IC "
                            "-0.014 / -0.072 / -0.025, on '400 names, 12y, 110 rebalances'"),
    "settings.py:243-251": ("sm_breadth +2.37, sm_avg_position +1.26, sm_holders +1.57, "
                            "sm_conviction +1.25, on '800 large caps / 110 rebalances'"),
    "factors.py:294-296": ("the anomalies 'REJECTED - every one carried the wrong sign', "
                           "same 400-name measurement"),
    "factors.py:314-316": ("sm_breadth REPLACES inst_breadth in the LIVE institutional theme "
                           "mean, justified by 'IC t +2.37 vs +1.48 on 800 large caps' - a "
                           "LIVE SCORING DECISION resting on a voided number"),
}


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


def _ic_series(panel, zc, ret_col="fwd_ret"):
    """Per-date Spearman IC of one standardized number against the forward return.

    The same per-date construction `per_signal_ic` uses; kept here so the halves and the
    permutation null operate on the SAME series the shipped statistic summarises.
    """
    dates, ics, cells = [], [], []
    for d, sub in panel.groupby("date", sort=True):
        ss = sub.dropna(subset=[zc, ret_col])
        if len(ss) < MIN_NAMES:
            continue
        a = ss[zc].to_numpy(dtype=float)
        b = ss[ret_col].to_numpy(dtype=float)
        ic = FP._spearman(a, b)
        if ic == ic:
            dates.append(d)
            ics.append(float(ic))
            cells.append((a, b))
    return dates, ics, cells


def _t_of(ics):
    r = ST.mean_inference(list(ics))
    if not r or r.get("t") is None or not np.isfinite(r["t"]):
        return None
    return r


def _perm(cells, rng, n_perm=N_PERM):
    """Null: shuffle the signal WITHIN each date (the within-column scheme).

    `placebo_panel` is not used - it is exactly invariant on a composite and cannot
    calibrate a column-shaped object.
    """
    nulls = []
    for _ in range(n_perm):
        vals = []
        for a, b in cells:
            ic = FP._spearman(rng.permutation(a), b)
            if ic == ic:
                vals.append(float(ic))
        if len(vals) < 3:
            continue
        r = _t_of(vals)
        if r:
            nulls.append(float(r["t"]))
    if not nulls:
        return None, None, []
    return (float(np.percentile(nulls, 95)), float(np.percentile(nulls, 5)),
            [round(x, 6) for x in nulls])


def score_signal(panel, num, rng):
    zc = "z_" + num
    out = {"signal": num, "z_col": zc}
    if zc not in panel.columns:
        out["verdict"] = "VOID - NO z_ COLUMN (not registered, or keep_numbers off)"
        return out
    cov = float(panel[zc].notna().mean())
    out["coverage"] = cov
    dates, ics, cells = _ic_series(panel, zc)
    n = len(dates)
    out["n_dates"] = n
    if cov < MIN_COVERAGE:
        out["verdict"] = "VOID - UNDERPOWERED BY CONSTRUCTION (coverage)"
        return out
    mid = n // 2
    if mid < MIN_DATES_PER_HALF or (n - mid - 1) < MIN_DATES_PER_HALF:
        out["verdict"] = "VOID - UNDERPOWERED BY CONSTRUCTION (dates)"
        return out
    for tag, (a, b) in (("full", (0, n)), ("early", (0, mid)), ("late", (mid + 1, n))):
        s, c = ics[a:b], cells[a:b]
        r = _t_of(s)
        p95, p5, draws = _perm(c, rng)
        tt = float(r["t"]) if r else None
        out[tag] = {
            "n": len(s), "median_ic": float(np.median(s)), "mean_ic": float(np.mean(s)),
            "ic_t": tt, "n_eff": (float(r.get("n_eff")) if r else None),
            "perm_p95": p95, "perm_p5": p5, "n_perm_ok": len(draws),
            "clears_own_p95": bool(tt is not None and p95 is not None and tt > p95),
            "below_own_p5": bool(tt is not None and p5 is not None and tt < p5),
            # reported, NEVER the verdict (register 2.4)
            "vs_x7_theme_bar_2_71": (None if tt is None else tt > X7_THEME_BAR),
            "vs_convention_2_0": (None if tt is None else tt > CONVENTION_BAR),
            "perm_draws": draws,
        }
    e, l = out["early"], out["late"]
    out["both_halves_clear"] = bool(e["clears_own_p95"] and l["clears_own_p95"])
    out["both_halves_below_p5"] = bool(e["below_own_p5"] and l["below_own_p5"])
    out["halves_same_sign"] = bool(
        e["ic_t"] is not None and l["ic_t"] is not None
        and np.sign(e["ic_t"]) == np.sign(l["ic_t"]))
    out["verdict"] = verdict_of(out)
    return out


def verdict_of(o) -> str:
    """Register 2.5. A POSITIVE IC means the published anomaly REPRODUCES, because the R5
    signals arrive pre-negated; CONTRADICTS is its own verdict, never folded into 'rejected'."""
    if str(o.get("verdict", "")).startswith("VOID"):
        return o["verdict"]
    if (o["both_halves_clear"] and o["halves_same_sign"]
            and o["full"]["median_ic"] > 0):
        return "REPLICATES"
    if o["both_halves_below_p5"] and o["halves_same_sign"]:
        return "CONTRADICTS-PUBLISHED-SIGN"
    return "NULL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_r5r6.pkl")
    ap.add_argument("--json", default="data/free_analysis/R5_R6_ALPHABETICAL.json")
    ap.add_argument("--controls-only", action="store_true")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        _log(f"[r56] loading banked panel {args.panel_cache}")
        panel = pickle.load(open(args.panel_cache, "rb"))
    else:
        _log("[r56] building the panel ONCE with keep_numbers=True")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        panel = FP.build_fundamental_panel(
            prov, prov.universe(None), rebalance_days=63,
            lookback_years=CFG.backtest_lookback_years, horizon=63, keep_numbers=True)
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        pickle.dump(panel, open(args.panel_cache, "wb"))
        _log(f"[r56] banked {args.panel_cache}")

    n_d, n_t = panel["date"].nunique(), panel["ticker"].nunique()
    _log(f"[r56] panel {panel.shape}, {n_d} dates, {n_t} names")
    out = {"item": "R5+R6", "register": "PREREG_r5_r6_alphabetical_rerun.md",
           "r5_signals": list(R5_SIGNALS), "r6_signals": list(R6_SIGNALS),
           "byproducts": list(BYPRODUCTS), "n_perm": N_PERM, "seed": SEED,
           "min_coverage": MIN_COVERAGE,
           "stale_sites_quoted_verbatim": STALE_SITES,     # C5
           "controls": {}, "arms": {}, "free_byproducts": {}}

    # ---- C2 (GATING): canonical panel AND the six z_ columns actually exist ----
    missing = [f"z_{s}" for s in ARMS if f"z_{s}" not in panel.columns]
    c2 = {"n_dates": int(n_d), "n_names": int(n_t),
          "z_columns_missing": missing,
          "ok": bool(n_d >= 60 and n_t >= 2400 and not missing)}
    out["controls"]["C2_canonical_panel_and_z_columns"] = c2
    _log(f"[C2] canonical panel + z columns: {c2['ok']}  missing={missing}")
    if not c2["ok"]:
        out["ABORTED"] = "C2 failed - smoke-test panel, or registration did not take"
        _w(args.json, out)
        return 2

    # ---- C1 (GATING): the composite must be BIT-IDENTICAL with the six registered ----
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    exact = {k: (got.get(k) == v) for k, v in REC.items()}
    ok1 = all(exact.values())
    out["controls"]["C1_composite_bit_identical"] = {
        "ok": bool(ok1), "measured": got, "expected": REC, "exact_equality": exact,
        "why": ("Registration in NUMBER_THEME must be MEASUREMENT, not SCORING. Every theme "
                "mean is an explicit column list, so adding a number cannot move the "
                "composite - and this GATES on that being true rather than asserting it. "
                "NOT a vintage event if it holds; if it fails, it is one.")}
    _log(f"[C1] composite bit-identical: {ok1}")
    if not ok1:
        out["ABORTED"] = ("C1 FAILED - registration MOVED the composite, so this is a scoring "
                          "change and a VINTAGE EVENT. Every arm is VOID per register 6.4.")
        _w(args.json, out)
        return 2

    if args.controls_only:
        _w(args.json, out)
        _log("[r56] controls-only pass complete; arms NOT scored")
        return 0

    # ---- C3: coverage FIRST ----
    cov = {s: float(panel[f"z_{s}"].notna().mean()) for s in ARMS if f"z_{s}" in panel.columns}
    cov.update({s: float(panel[f"z_{s}"].notna().mean())
                for s in BYPRODUCTS if f"z_{s}" in panel.columns})
    out["controls"]["C3_coverage_first"] = {
        "coverage": cov, "floor": MIN_COVERAGE,
        "below_floor": [s for s, v in cov.items() if v < MIN_COVERAGE]}
    _log(f"[C3] coverage: {json.dumps(cov, default=float)}")

    rng = np.random.default_rng(SEED)

    # ---- the six arms ----
    for s in ARMS:
        r = score_signal(panel, s, rng)
        out["arms"][s] = r
        f = r.get("full", {})
        _log(f"[{s}] {r['verdict']}  medIC {f.get('median_ic')}  t {f.get('ic_t')}  "
             f"p95 {f.get('perm_p95')}  cov {r.get('coverage')}")

    # ---- free by-products: measured, reported, NO verdict, NO trial ----
    for s in BYPRODUCTS:
        zc = "z_" + s
        if zc not in panel.columns:
            out["free_byproducts"][s] = {"status": "no z_ column"}
            continue
        _, ics, _ = _ic_series(panel, zc)
        r = _t_of(ics) if ics else None
        out["free_byproducts"][s] = {
            "coverage": float(panel[zc].notna().mean()),
            "n_dates": len(ics),
            "median_ic": (float(np.median(ics)) if ics else None),
            "ic_t": (float(r["t"]) if r else None),
            "STATUS": "FREE BY-PRODUCT - NO VERDICT, NO TRIAL (register 4)",
        }
    bp = out["free_byproducts"]
    if bp.get("sm_breadth", {}).get("ic_t") is not None and \
            bp.get("inst_breadth", {}).get("ic_t") is not None:
        smb, isb = bp["sm_breadth"]["ic_t"], bp["inst_breadth"]["ic_t"]
        out["controls"]["C5b_live_swap_justification"] = {
            "sm_breadth_ic_t": smb, "inst_breadth_ic_t": isb,
            "swap_ordering_holds_on_corrected_universe": bool(smb > isb),
            "the_voided_figures": {"sm_breadth": 2.37, "inst_breadth": 1.48,
                                   "universe": "800 large caps, ALPHABETICAL (B12)"},
            "note": ("factors.py:314-316 swapped inst_breadth for sm_breadth in the LIVE "
                     "institutional theme mean on the strength of the voided pair. If the "
                     "ordering reverses here, a live scoring decision rests on a voided "
                     "number - ROUTED, not changed: swapping a theme input is a construction "
                     "change and a vintage event."),
        }
        _log(f"[C5b] live swap: sm_breadth {smb:.4f} vs inst_breadth {isb:.4f} -> "
             f"holds={smb > isb}")

    # ---- C6: redundancy ----
    c6 = {}
    for s in ARMS:
        zc = "z_" + s
        if zc not in panel.columns:
            continue
        row = {}
        for other in THEMES + [f"z_{o}" for o in ARMS if o != s]:
            if other not in panel.columns:
                continue
            a = pd.to_numeric(panel[zc], errors="coerce")
            b = pd.to_numeric(panel[other], errors="coerce")
            m = a.notna() & b.notna()
            if m.sum() > 1000:
                row[other] = round(float(a[m].corr(b[m], method="spearman")), 4)
        c6[s] = row
    out["controls"]["C6_redundancy"] = c6

    # ---- C7: R5's own earlier pre-registration, conditional ----
    vol_cousins = [s for s in ("neg_max_ret", "neg_idio_vol")
                   if out["arms"].get(s, {}).get("verdict") == "REPLICATES"]
    c7 = {"triggered_by": vol_cousins,
          "rule": ("R5's own earlier pre-registration: a positive result on the two "
                   "volatility cousins needs the size-interaction check, because low_risk "
                   "was zeroed for cancelling the small-cap tilt.")}
    for s in vol_cousins:
        a = pd.to_numeric(panel[f"z_{s}"], errors="coerce")
        b = pd.to_numeric(panel["size"], errors="coerce")
        m = a.notna() & b.notna()
        c7[s] = {"spearman_vs_size": round(float(a[m].corr(b[m], method="spearman")), 4)}
    if not vol_cousins:
        c7["status"] = "NOT TRIGGERED - neither volatility cousin replicated"
    out["controls"]["C7_size_interaction"] = c7

    _w(args.json, out)
    _log(f"[r56] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
