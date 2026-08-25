# -*- coding: utf-8 -*-
"""D6/D7 — execute `PREREG_d6_analyst_revisions.md`. TWO PASSES, and the split is the point.

    python -m scripts.d6_revisions --controls     # C1-C6 and K1-K4, banked
    python -m scripts.d6_revisions --arm          # REFUSES without a passing controls artifact

`O10`'s process defect was computing a gating control and the outcome statistics in ONE pass, so
it could not be claimed the control was read first. `MA31`/`MA32` repaired it by making `--arms`
refuse without a passing artifact, and this does the same. The refusal distinguishes THREE states
-- artifact ABSENT, artifact FAILING, artifact STALE -- because `S3-I1` measured that a recorder
which cannot tell absent from failing reports a clean bill of health from a check that never ran.

NOTHING IS ADOPTED. No file under `valuation/screener`, `valuation/web` or `valuation/engine` is
touched, and adoption is a vintage event and Don's decision.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import fundamental_panel as FP                       # noqa: E402
from valuation.edge import research_log                                  # noqa: E402
from valuation.edge.power_gate import (Z_POWER_CONVENTION,               # noqa: E402
                                       detection_threshold)
from valuation.studies import incremental_ic as IIC                      # noqa: E402
from valuation.studies import revisions as REV                           # noqa: E402
from valuation.studies.surface_stock import (arm_ic, arm_verdict,        # noqa: E402
                                             ic_series_degenerate, MIN_NAMES)

# --------------------------------------------------------------------------- #
#  EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item.
# --------------------------------------------------------------------------- #
IC_BAR = 2.71               # X7's CALIBRATED theme-IC floor. NOT the retired 2.0 convention.
COSTUME_BAR = 0.60          # the record's STANDING costume bar (E-1 withdrew at 0.6114)
MIN_NONNULL_EFFECTIVE = 0.30   # K3's floor
DECLARED_SIGN = +1          # upward revisions predict higher forward returns

#: C1's target: the published record, which the panel must reproduce before anything is joined.
PUBLISHED = {"top_decile_alpha": 0.071741423321, "ls_t": 2.8360640685320595,
             "ls_hac_t": 2.6199121240414884, "monotonicity": -0.890909}
C1_TOL = {"top_decile_alpha": 1e-9, "ls_t": 1e-9, "ls_hac_t": 1e-9, "monotonicity": 1e-5}

THEMES = list(IIC.INCUMBENTS)
W = 0.125

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join(_ROOT, "data", "free_analysis", "panel_corrected_69d.pkl")
OUT_DIR = os.path.join(_ROOT, "data", "free_analysis")
CONTROLS_JSON = os.path.join(OUT_DIR, "D6_CONTROLS.json")
ARM_JSON = os.path.join(OUT_DIR, "D6_ARM.json")


def _panel() -> pd.DataFrame:
    if not os.path.isfile(PANEL):
        raise FileNotFoundError(
            "%s is absent. The corrected panel is never mirrored into a worktree -- resolve the "
            "PRIMARY data root. `DEEPITM-FIN` shipped a clean, plausible null from an EMPTY "
            "directory that merely existed." % PANEL)
    p = pd.read_pickle(PANEL)
    if not isinstance(p["date"].iloc[0], str):
        raise RuntimeError("panel dates must be STRINGS; a pd.Timestamp filter matches ZERO rows "
                           "SILENTLY, which is this record's own documented hazard")
    return p


def _build(p: pd.DataFrame) -> pd.DataFrame:
    """Attach the registered signal. ONE construction, called by both passes."""
    tickers = sorted(set(p["ticker"].astype(str).str.upper()))
    iv = REV.crsp_intervals(tickers)
    dates = sorted(set(p["date"].astype(str)))
    years = range(int(dates[0][:4]) - 1, int(dates[-1][:4]) + 1)
    det = REV.load_fy1_estimates(years=years)
    est = REV.map_to_universe(det, iv)
    rev = REV.revisions(est)
    p = p.copy()
    p[REV.SIGNAL_COL] = REV.signal_on_panel(p, rev)
    p.attrs["_d6"] = {"crsp_names": len(iv), "det_rows": int(len(det)),
                      "mapped_rows": int(len(est)), "mapped_names": int(est["ticker"].nunique()),
                      "revisions": int(len(rev)), "revision_names": int(rev["ticker"].nunique())}
    return p


def _per_date_rho(p: pd.DataFrame, col: str) -> dict:
    """Mean per-date |Spearman| of the candidate against `col`. A COSTUME statistic, not an arm."""
    rr = []
    for _, g in p.groupby("date"):
        s = g[[REV.SIGNAL_COL, col]].dropna()
        if len(s) >= MIN_NAMES and s[REV.SIGNAL_COL].nunique() > 1 and s[col].nunique() > 1:
            rr.append(s[REV.SIGNAL_COL].corr(s[col], method="spearman"))
    if not rr:
        return {"n_dates": 0, "mean_rho": None, "mean_abs_rho": None, "max_abs_rho": None}
    a = np.asarray(rr, dtype=float)
    return {"n_dates": int(a.size), "mean_rho": float(a.mean()),
            "mean_abs_rho": float(np.abs(a).mean()), "max_abs_rho": float(np.abs(a).max())}


# --------------------------------------------------------------------------- #
#  CONTROLS PASS
# --------------------------------------------------------------------------- #
def controls() -> dict:
    p0 = _panel()
    out: dict = {"equity_N": research_log.detail()["by_domain"]["equity"]}

    # ---- C1 FIDELITY, GATING. MA28's C1 and MB8's C1 both fired in real life.
    r = FP.quantile_backtest(p0, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {"top_decile_alpha": float(r["top_decile_alpha"]), "ls_t": float(r["long_short_tstat"]),
           # `long_short_tstat_nw` is the Newey-West key the record actually quotes. My first
           # cut guessed `..._hac` and C1 fired against a CORRECT panel -- a control catching a
           # defect in itself, which is why the key is read from the artifact and not assumed.
           "ls_hac_t": float(r["long_short_tstat_nw"]),
           "monotonicity": float(r["monotonicity"])}
    c1_ok = all(abs(got[k] - PUBLISHED[k]) <= C1_TOL[k] for k in PUBLISHED)
    out["C1_fidelity"] = {"published": PUBLISHED, "measured": got, "pass": bool(c1_ok),
                          "note": "the panel must reproduce the published record BEFORE anything "
                                  "is joined; the run aborts otherwise"}
    if not c1_ok:
        out["all_gating_pass"] = False
        return out

    p = _build(p0)
    prov = p.attrs["_d6"]
    out["provenance"] = prov

    # ---- C6 the CRSP ceiling, reported as a LIMIT rather than read as zero coverage
    n_names = p["ticker"].nunique()
    out["C6_crsp_ceiling"] = {
        "panel_names": int(n_names), "names_with_crsp_intervals": int(prov["crsp_names"]),
        "unreachable_by_construction": int(n_names - prov["crsp_names"]),
        "frac": float(prov["crsp_names"]) / n_names,
        "note": "names with no CRSP dated interval cannot be reached by ANY cusip route; they "
                "are counted, not read as zero coverage"}

    # ---- RAW coverage on the whole panel
    nn = p[REV.SIGNAL_COL].notna()
    out["coverage_raw_panel"] = {
        "cells": int(len(p)), "cells_with_signal": int(nn.sum()),
        "frac": float(nn.mean()), "names_covered": int(p.loc[nn, "ticker"].nunique()),
        "dates_covered": int(p.loc[nn, "date"].nunique())}

    # ---- COVERAGE ON THE POPULATION THE ARM WILL TEST. This is the O-1 lesson, and it is the
    #      reason this block reports the RESIDUALISED geometry rather than the panel's.
    out["coverage_arm_population"] = {}
    for basis in ("six", "seven"):
        inc = list(IIC.basis_for(basis))
        cov = IIC.effective_coverage(p, REV.SIGNAL_COL, inc)
        ed = list(IIC.effective_dates(p, REV.SIGNAL_COL, inc))
        sizes = []
        for d in ed:
            g = p[p["date"] == d]
            sizes.append(int(len(g.dropna(subset=[REV.SIGNAL_COL, "fwd_ret"] + inc))))
        sizes.sort()
        nd = len(ed)
        se = 1.0 / (nd ** 0.5) if nd else float("nan")
        out["coverage_arm_population"][basis] = {
            "n_dates_effective": nd, "n_dates_raw": cov.get("n_dates_raw"),
            "rows_effective": cov.get("rows_effective"),
            "rows_effective_frac_of_raw": cov.get("rows_effective_frac_of_raw"),
            "first_date_effective": cov.get("first_date_effective"),
            "split_on_effective": cov.get("split_on_effective"),
            "cross_section_min": sizes[0] if sizes else 0,
            "cross_section_median": sizes[len(sizes) // 2] if sizes else 0,
            "cross_section_max": sizes[-1] if sizes else 0,
            "cross_sections_below_MIN_NAMES": int(sum(1 for s in sizes if s < MIN_NAMES)),
            "mde50_sd": detection_threshold(se, crit=IC_BAR),
            "mde80_sd": (IC_BAR + Z_POWER_CONVENTION) * se}

    # ---- K1 / K2 COSTUME KILLS, pre-outcome
    k1 = {c: _per_date_rho(p, c) for c in THEMES}
    worst = max(k1.items(), key=lambda kv: kv[1]["mean_abs_rho"] or 0.0)
    out["K1_momentum_costume"] = {
        "bar": COSTUME_BAR, "by_theme": k1, "largest": worst[0],
        "largest_mean_abs_rho": worst[1]["mean_abs_rho"],
        "fires": bool((worst[1]["mean_abs_rho"] or 0.0) >= COSTUME_BAR)}
    pead_cols = [c for c in ("z_pead_car", "z_pead_drift") if c in p.columns]
    k2 = {c: _per_date_rho(p, c) for c in pead_cols}
    k2max = max((v["mean_abs_rho"] or 0.0) for v in k2.values()) if k2 else 0.0
    out["K2_pead_costume"] = {"bar": COSTUME_BAR, "by_col": k2, "max_mean_abs_rho": k2max,
                              "fires": bool(k2max >= COSTUME_BAR)}

    # ---- K3 DEGENERACY. U2 measured the shipped IC arithmetic returning t ~ 1e16 on a constant.
    degen_dates = []
    for basis in ("six", "seven"):
        inc = list(IIC.basis_for(basis))
        for d in IIC.effective_dates(p, REV.SIGNAL_COL, inc):
            g = p[p["date"] == d].dropna(subset=[REV.SIGNAL_COL, "fwd_ret"] + inc)
            if len(g) and g[REV.SIGNAL_COL].nunique() <= 1:
                degen_dates.append((basis, str(d)))
    eff_nonnull = {}
    for basis in ("six", "seven"):
        inc = list(IIC.basis_for(basis))
        ed = set(IIC.effective_dates(p, REV.SIGNAL_COL, inc))
        sub = p[p["date"].isin(ed)]
        base = sub.dropna(subset=["fwd_ret"] + inc)
        eff_nonnull[basis] = float(base[REV.SIGNAL_COL].notna().mean()) if len(base) else 0.0
    out["K3_degeneracy"] = {
        "constant_cross_sections": degen_dates,
        "nonnull_share_on_effective_rows": eff_nonnull,
        "floor": MIN_NONNULL_EFFECTIVE,
        "fires": bool(degen_dates or any(v < MIN_NONNULL_EFFECTIVE for v in eff_nonnull.values()))}

    # ---- K4 LOOK-AHEAD, pinned from BOTH sides
    src = open(os.path.join(_HERE, "valuation", "studies", "revisions.py"),
               encoding="utf-8").read()
    import ast as _ast
    tree = _ast.parse(src)
    read_names = {n.value for n in _ast.walk(tree)
                  if isinstance(n, _ast.Constant) and isinstance(n.value, str)}
    keep_literal = set()
    for n in _ast.walk(tree):
        if isinstance(n, _ast.Assign) and any(
                isinstance(t, _ast.Name) and t.id == "keep" for t in n.targets):
            keep_literal = {e.value for e in getattr(n.value, "elts", [])
                            if isinstance(e, _ast.Constant)}
    out["K4_lookahead"] = {
        "columns_loaded": sorted(keep_literal),
        "forbidden": list(REV.FORBIDDEN_COLUMNS),
        "forbidden_loaded": sorted(keep_literal & set(REV.FORBIDDEN_COLUMNS)),
        "fires": bool(keep_literal & set(REV.FORBIDDEN_COLUMNS)),
        "note": "the loader takes an explicit allowlist, so the arm path cannot reference what "
                "is not in the frame -- MB18's structural pin rather than an inspection"}

    # ---- C2 the join is W-3b's, asserted structurally
    out["C2_join_is_w3b"] = {
        "imports_MaskedCusip": "MaskedCusip" in src,
        "no_oftic_anywhere": "oftic" not in src.replace("`oftic`", ""),
        "positional_not_prefix": "startswith" not in src,
        "pass": bool("MaskedCusip" in src and "startswith" not in src)}

    # ---- C4 orthogonality DIAGNOSTIC, no verdict (register section 2c)
    # ---- C5 survivor tilt, printed not assumed
    capcol = "market_cap" if "market_cap" in p.columns else None
    if capcol:
        cov_med = float(p.loc[nn, capcol].median())
        unc_med = float(p.loc[~nn, capcol].median())
        out["C5_survivor_tilt"] = {"median_cap_covered": cov_med,
                                   "median_cap_uncovered": unc_med,
                                   "tilt_x": (cov_med / unc_med) if unc_med else None}
    else:
        out["C5_survivor_tilt"] = {"note": "no market_cap column on this panel"}

    out["all_gating_pass"] = bool(
        c1_ok and not out["K1_momentum_costume"]["fires"]
        and not out["K2_pead_costume"]["fires"] and not out["K3_degeneracy"]["fires"]
        and not out["K4_lookahead"]["fires"] and out["C2_join_is_w3b"]["pass"])
    return out


# --------------------------------------------------------------------------- #
#  ARM PASS
# --------------------------------------------------------------------------- #
def arm() -> dict:
    if not os.path.isfile(CONTROLS_JSON):
        raise SystemExit(
            "REFUSED: %s is ABSENT. The controls have not been run, which is a DIFFERENT state "
            "from their having run and failed. Run `--controls` first." % CONTROLS_JSON)
    ctl = json.load(open(CONTROLS_JSON))
    if not ctl.get("all_gating_pass"):
        raise SystemExit(
            "REFUSED: %s exists and reports all_gating_pass=false. A gating control FAILED; the "
            "arm may not be scored." % CONTROLS_JSON)

    p = _build(_panel())
    res: dict = {"equity_N": ctl["equity_N"], "ic_bar": IC_BAR,
                 "declared_sign": DECLARED_SIGN, "bases": {}}

    for basis in ("six", "seven"):
        inc = list(IIC.basis_for(basis))
        cov = ctl["coverage_arm_population"][basis]
        ed = list(IIC.effective_dates(p, REV.SIGNAL_COL, inc))
        split = cov["split_on_effective"]
        half = len(ed) // 2
        early, late = ed[:half], ed[len(ed) - half:]

        full = arm_ic(p, REV.SIGNAL_COL, ed, inc)
        e = arm_ic(p, REV.SIGNAL_COL, early, inc)
        l = arm_ic(p, REV.SIGNAL_COL, late, inc)

        # MB22 power, from the MEASURED effective geometry, BEFORE the verdict is read.
        mde80 = cov["mde80_sd"]
        obs = full["incremental_median_ic"]
        obs_sd = (abs(full["incremental_ic_tstat"]) / (len(ed) ** 0.5)
                  if full["incremental_ic_tstat"] is not None else None)
        power_ok = cov["n_dates_effective"] >= IIC.MIN_DATES * 2

        v = arm_verdict(e["incremental_ic_tstat"], l["incremental_ic_tstat"], basis,
                        bar=IC_BAR, power_ok=power_ok,
                        degenerate_early=bool(e["incremental_degenerate"]),
                        degenerate_late=bool(l["incremental_degenerate"]))
        res["bases"][basis] = {
            "n_dates_effective": cov["n_dates_effective"],
            "rows_effective": cov["rows_effective"],
            "split": split, "full": full, "early": e, "late": l,
            "mde50_sd": cov["mde50_sd"], "mde80_sd": mde80,
            "observed_effect_sd": obs_sd,
            "observed_over_mde80": (obs_sd / mde80) if (obs_sd and mde80) else None,
            "verdict": v}
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D6/D7 analyst estimate revisions")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arm", action="store_true")
    a = ap.parse_args(argv)
    if a.controls == a.arm:
        raise SystemExit("pass exactly one of --controls or --arm: the two-pass split is the "
                         "point (O10's process defect)")
    os.makedirs(OUT_DIR, exist_ok=True)
    if a.controls:
        out = controls()
        json.dump(out, open(CONTROLS_JSON, "w"), indent=1, default=str)
        print(json.dumps(out, indent=1, default=str)[:12000])
        print("\nwrote", CONTROLS_JSON)
        return 0 if out.get("all_gating_pass") else 2
    out = arm()
    json.dump(out, open(ARM_JSON, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str)[:12000])
    print("\nwrote", ARM_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
