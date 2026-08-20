"""E-1 / S-SEED-4 -- the graveyard votes. `PREREG_e1_graveyard_stouffer.md`.

Register ACCEPTED VERBATIM from the Frontier Scout's draft and committed **ALONE** at `e05c33c`,
markdown only, a strict git ancestor of this file. Equity trial booked at `dff46bc` BEFORE this
ran (`N` 236 -> 237).

**ONE PRE-COMMITTED COLUMN AND NOTHING IS FITTED.** The flat equal-weight mean of every
registered signal that is NOT an input to any of the seven weighted themes, each entering at its
published sign, weights fixed in advance. This is the only reason the register survives the wall
the record has built: `MLCOMB` FIT a combiner and it REVERSED out of sample (its deciles ran
backwards, monotonicity +0.382 and +0.842), and five weight schemes were rejected wholesale.
Nothing here is chosen on the data.

**IF IT CLEARS, IT DOES NOT LICENSE ASKING WHICH SIGNALS CARRIED IT.** That is a second register
with its own trial, and §5 void condition 3 makes asking without one a void. Enforced here as
well as promised: no per-signal outcome statistic is computed anywhere in the arm path, and a
test reads the syntax tree to pin it.

TWO PASSES, and the separation is the register's (§4: the kills run in their own pass and are
READ before the arm). Session 26's defect was computing a gating control and the outcomes it
gates in one pass, so it could not be claimed the control was read first.

    python -m scripts.e1_graveyard_stouffer --kills   # K1..K3, no outcome scored
    python -m scripts.e1_graveyard_stouffer --arm     # REFUSES without a passing kills artifact
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import power_gate as PG                                   # noqa: E402
from valuation.edge.statistics import mean_inference                          # noqa: E402
from valuation.screener import settings as S                                  # noqa: E402
from valuation.studies import incremental_ic as II                            # noqa: E402
from valuation.studies.incremental_ic import halves                           # noqa: E402

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join("data", "free_analysis", "panel_r5r6.pkl")
KILLS_JSON = os.path.join("data", "free_analysis", "E1_KILLS.json")
ARM_JSON = os.path.join("data", "free_analysis", "E1_ARM.json")

# --------------------------------------------------------------------------------------
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item.
# --------------------------------------------------------------------------------------
WEIGHTED = ("value", "quality", "momentum", "insider", "capital_discipline", "size",
            "institutional")
BAR = 2.71                    # §2, X7's calibrated incremental-IC threshold
K1_K2_RHO_MAX = 0.60          # §4 K1 and K2
K3_MIN_SIGNALS = 25           # §4 K3
BASES = ("six", "seven")      # §2, CO-PRIMARY
FACTORS_SRC = os.path.join("valuation", "screener", "factors.py")

#: the strongest RAW anchor this panel has ever carried, quoted with any null per §3.
STRONGEST_RAW_ANCHOR_SD = 0.4346


def _root(explicit=None):
    """`data/` is gitignored; probe for the FILE, never the directory (DEEPITM-FIN)."""
    cands = [explicit, os.environ.get("VALQUO_DATA_ROOT"), DEFAULT_ROOT]
    here = REPO
    for _ in range(6):
        cands.append(here)
        here = os.path.dirname(here)
    for c in cands:
        if c and os.path.isfile(os.path.join(c, PANEL)):
            return c
    raise SystemExit(f"[e1] no data root holding {PANEL}")


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, default=str)


# ------------------------------------------------------------------ the signal set (§1)

def weighted_theme_inputs():
    """The `z_` columns the seven weighted theme means ACTUALLY use, DERIVED from the source.

    Not retyped (`MA5`, `B7`). And derived from the theme MEANS rather than from
    `NUMBER_THEME`'s mapping, because the two disagree materially: `NUMBER_THEME` assigns 9
    signals to `institutional` and the theme mean uses 2 of them, 13 to `quality` and the mean
    uses 10, 5 to `momentum` and the mean uses 3. Taking the registry's mapping would have put
    17 genuinely non-incumbent signals in the incumbent bucket and fired K3 spuriously.
    """
    tree = ast.parse(io.open(os.path.join(REPO, FACTORS_SRC), encoding="utf-8").read())
    by_target = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        tgt = None
        for t in node.targets:
            if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant):
                tgt = t.slice.value
            elif isinstance(t, ast.Name):
                tgt = t.id
        if not isinstance(tgt, str):
            continue
        zs = {n.value for n in ast.walk(node.value)
              if isinstance(n, ast.Constant) and isinstance(n.value, str)
              and n.value.startswith("z_")}
        if zs:
            by_target.setdefault(tgt, set()).update(zs)
    # `value` is assembled through local names before the column is written
    val = set()
    for k in ("_est", "value_est", "value_spec", "value"):
        val |= by_target.get(k, set())
    by_target["value"] = val
    used, per_theme = set(), {}
    for t in WEIGHTED:
        cols = sorted(by_target.get(t, set()))
        per_theme[t] = cols
        used |= set(cols)
    return used, per_theme


def graveyard_signals(panel):
    """§1's set: registered, NOT an input to any weighted theme. Banked before the arm.

    Every one enters at the sign the shipped `z_` construction gives it -- the register's D2
    declares that convention IN WRITING as the sign record, and this function applies NO flip of
    its own. That is pinned by test.
    """
    used, per_theme = weighted_theme_inputs()
    inc = {c[2:] for c in used}
    registered = sorted(S.NUMBER_THEME)
    non = [n for n in registered if n not in inc]
    rows = []
    for n in non:
        z = f"z_{n}"
        present = z in panel.columns
        cov = float(panel[z].notna().mean()) if present else 0.0
        rows.append({"signal": n, "registry_theme": S.NUMBER_THEME[n], "column": z,
                     "on_panel": present, "coverage": cov})
    return {"registered_total": len(registered),
            "weighted_theme_inputs_distinct": len(used),
            "weighted_theme_inputs_per_theme": {k: len(v) for k, v in per_theme.items()},
            "graveyard_n": len(non),
            "graveyard": rows,
            "with_any_coverage": int(sum(1 for r in rows if r["coverage"] > 0)),
            "above_5pct_coverage": int(sum(1 for r in rows if r["coverage"] > 0.05))}


def graveyard_column(panel, cols):
    """Flat equal-weight mean of the oriented z-columns, `B7` convention.

    NaNs drop out of the mean exactly as the shipped composite renormalises by present-weight
    mass, and §1's eligibility rule requires at least HALF the set computable on a row.
    """
    have = [c for c in cols if c in panel.columns]
    block = panel[have].apply(pd.to_numeric, errors="coerce")
    n_ok = block.notna().sum(axis=1)
    need = int(np.ceil(len(cols) / 2.0))
    val = block.mean(axis=1, skipna=True)
    val = val.where(n_ok >= need)
    return val, n_ok, need


def _spearman(a, b):
    ra = pd.Series(a).rank().to_numpy(dtype=float)
    rb = pd.Series(b).rank().to_numpy(dtype=float)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def mean_abs_per_date_rho(panel, a, b):
    """Mean per-date |Spearman| between two columns. INPUTS ONLY -- no outcome is read.

    Returns the registered statistic plus the per-date DISTRIBUTION. The distribution carries no
    verdict and is reported because a kill that fires by hundredths invites the question of
    whether it is a stable property of the column or a few dates dragging a mean -- and a reader
    is entitled to that without having to re-run anything.
    """
    vals = []
    for d, g in panel.groupby("date", sort=True):
        x, y = g[a].to_numpy(dtype=float), g[b].to_numpy(dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < II.MIN_NAMES:
            continue
        r = _spearman(x[ok], y[ok])
        if r == r:
            vals.append(abs(r))
    if not vals:
        return None, 0, {}
    v = np.asarray(vals, dtype=float)
    dist = {"p05": float(np.quantile(v, 0.05)), "median": float(np.median(v)),
            "p95": float(np.quantile(v, 0.95)), "min": float(v.min()), "max": float(v.max()),
            "dates_above_0.60": int((v > K1_K2_RHO_MAX).sum()),
            "share_above_0.60": float((v > K1_K2_RHO_MAX).mean())}
    return float(np.mean(v)), len(vals), dist


# ------------------------------------------------------------------ pass 1: the kills

def run_kills(args):
    root = _root(args.data_root)
    panel = pickle.load(open(os.path.join(root, PANEL), "rb"))
    print(f"[e1] panel {panel.shape[0]:,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique():,} names")

    census = graveyard_signals(panel)
    cols = [r["column"] for r in census["graveyard"]]
    print(f"[e1] registered {census['registered_total']}, "
          f"weighted-theme inputs {census['weighted_theme_inputs_distinct']}, "
          f"GRAVEYARD {census['graveyard_n']}")
    for t, k in census["weighted_theme_inputs_per_theme"].items():
        reg = sum(1 for n, th in S.NUMBER_THEME.items() if th == t)
        print(f"       {t:20s} mean uses {k:>2}   (NUMBER_THEME assigns {reg:>2})")

    k3_pass = census["graveyard_n"] >= K3_MIN_SIGNALS
    print(f"\n[e1] K3  graveyard {census['graveyard_n']} vs floor {K3_MIN_SIGNALS}"
          f"  -> {'PASS' if k3_pass else 'FIRES (WITHDRAWN)'}")
    print(f"       with any coverage {census['with_any_coverage']}, "
          f"above 5pct {census['above_5pct_coverage']}")

    gv, n_ok, need = graveyard_column(panel, cols)
    panel = panel.assign(_graveyard=gv)
    elig = int(gv.notna().sum())
    print(f"\n[e1] column: flat mean of {len(cols)} oriented z-columns, "
          f"eligibility >= {need} of {len(cols)} computable")
    print(f"       eligible rows {elig:,} of {len(panel):,} = {elig / len(panel):.4f}")
    print(f"       computable-per-row: median {int(n_ok.median())}, "
          f"p05 {int(n_ok.quantile(0.05))}, p95 {int(n_ok.quantile(0.95))}")

    # The shipped composite is not a panel column -- it is BUILT from the seven weighted themes
    # by , audit B7's one definition, which is what MB8's C2 used. Built
    # here rather than re-derived, so K1 compares against the object the product actually scores.
    import valuation.edge.fundamental_panel as FP
    from valuation.screener.cross_sectional import zscore
    comp = []
    for d, g in panel.groupby("date", sort=True):
        c = FP.composite_from_frame(g, list(WEIGHTED), {c: 0.125 for c in WEIGHTED}, zscore)
        comp.append(pd.Series(np.asarray(c, dtype=float), index=g.index))
    panel = panel.assign(_composite=pd.concat(comp).reindex(panel.index))

    k1_rho, k1_n, k1_dist = mean_abs_per_date_rho(panel, "_graveyard", "_composite")
    k2_rho, k2_n, k2_dist = mean_abs_per_date_rho(panel, "_graveyard", "size")
    k1_pass = (k1_rho is not None) and (k1_rho <= K1_K2_RHO_MAX)
    k2_pass = (k2_rho is not None) and (k2_rho <= K1_K2_RHO_MAX)
    print(f"\n[e1] K1  mean per-date |rho| vs the shipped composite: {k1_rho:.4f} "
          f"({k1_n} dates) vs {K1_K2_RHO_MAX} -> {'PASS' if k1_pass else 'FIRES (WITHDRAWN)'}")
    print(f"[e1] K2  mean per-date |rho| vs the size theme        : {k2_rho:.4f} "
          f"({k2_n} dates) vs {K1_K2_RHO_MAX} -> {'PASS' if k2_pass else 'FIRES (WITHDRAWN)'}")

    print(f"       K2 per-date |rho|: median {k2_dist['median']:.4f}, "
          f"p05 {k2_dist['p05']:.4f}, p95 {k2_dist['p95']:.4f}, "
          f"{k2_dist['dates_above_0.60']} of {k2_n} dates above {K1_K2_RHO_MAX} "
          f"({k2_dist['share_above_0.60']:.3f})   [diagnostic, NO VERDICT]")

    all_pass = bool(k1_pass and k2_pass and k3_pass)
    out = {"item": "E-1", "register": "PREREG_e1_graveyard_stouffer.md",
           "register_commit": "e05c33c", "booking_commit": "dff46bc",
           "census": census,
           "column": {"n_signals": len(cols), "eligibility_min_computable": need,
                      "eligible_rows": elig, "eligible_share": elig / len(panel),
                      "median_computable_per_row": int(n_ok.median())},
           "K1_rho_vs_composite": k1_rho, "K1_pass": k1_pass, "K1_n_dates": k1_n,
           "K1_per_date_distribution_no_verdict": k1_dist,
           "K2_rho_vs_size": k2_rho, "K2_pass": k2_pass, "K2_n_dates": k2_n,
           "K2_per_date_distribution_no_verdict": k2_dist,
           "K3_graveyard_n": census["graveyard_n"], "K3_floor": K3_MIN_SIGNALS,
           "K3_pass": k3_pass,
           "bars": {"rho_max": K1_K2_RHO_MAX, "min_signals": K3_MIN_SIGNALS, "ic_bar": BAR},
           "no_outcome_read": True,
           "all_kills_pass": all_pass}
    _w(os.path.join(REPO, KILLS_JSON), out)
    print(f"\n[e1] wrote {KILLS_JSON}")
    print(f"[e1] ALL KILLS PASS = {all_pass}")
    return 0 if all_pass else 3


# ------------------------------------------------------------------ pass 2: the arm

def per_date_incremental_ic(frame, cand, incumbents, dates, ycol="fwd_ret"):
    """The PEAD/U2 construction: per-date OLS of the candidate on the incumbents WITH intercept,
    Spearman of the residual against the forward return. `MB18`'s implementation, unchanged."""
    inc = list(incumbents)
    out, used = [], []
    for d in dates:
        sub = frame[frame["date"] == d].dropna(subset=[cand, ycol] + inc)
        if len(sub) < II.MIN_NAMES:
            continue
        X = np.column_stack([np.ones(len(sub)), sub[inc].to_numpy(dtype=float)])
        y = sub[cand].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        f = sub[ycol].to_numpy(dtype=float)
        ok = np.isfinite(resid) & np.isfinite(f)
        if ok.sum() < II.MIN_NAMES:
            continue
        r = _spearman(resid[ok], f[ok])
        if r == r:
            out.append(float(r))
            used.append(str(d)[:10])
    return np.asarray(out), used


def _cell(ics):
    if len(ics) < 4:
        return {"n_dates": int(len(ics)), "t": None, "median_ic": None, "mean_ic": None}
    r = mean_inference(list(map(float, ics)), lag=1)
    return {"n_dates": int(len(ics)), "mean_ic": float(np.mean(ics)),
            "median_ic": float(np.median(ics)),
            "t": (float(r["t"]) if r and r.get("t") is not None else None)}


def stouffer(frame, cols, dates, ycol="fwd_ret"):
    """§2's DECLARED SECONDARY, reported beside the primary and carrying NO VERDICT.

    Per-date Z combining the per-signal ICs with FLAT weights and an
    input-correlation-matrix denominator. The correlation is of SIGNAL VALUES -- inputs only,
    computed once and banked -- so the denominator never touches an outcome.

    Z = sum(z_i) / sqrt(1' R 1), the standard correlated-Stouffer correction.
    """
    have = [c for c in cols if c in frame.columns]
    sub = frame.dropna(subset=[ycol])
    R = sub[have].apply(pd.to_numeric, errors="coerce").corr(method="spearman").to_numpy()
    R = np.nan_to_num(R, nan=0.0)
    np.fill_diagonal(R, 1.0)
    denom = float(np.sqrt(max(R.sum(), 1e-12)))
    per_date = []
    for d in dates:
        g = frame[frame["date"] == d]
        zs = []
        for c in have:
            x = g[c].to_numpy(dtype=float)
            y = g[ycol].to_numpy(dtype=float)
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < II.MIN_NAMES:
                continue
            r = _spearman(x[ok], y[ok])
            if r != r:
                continue
            # Fisher z of a Spearman IC, scaled by its own sample size
            n = int(ok.sum())
            zs.append(np.arctanh(np.clip(r, -0.999999, 0.999999)) * np.sqrt(n - 3.0))
        if len(zs) >= 2:
            per_date.append(float(np.sum(zs) / denom))
    arr = np.asarray(per_date)
    return {"n_dates": int(len(arr)), "denominator_sqrt_1R1": denom,
            "n_signals_in_matrix": len(have),
            "mean_Z": (float(np.mean(arr)) if len(arr) else None),
            "median_Z": (float(np.median(arr)) if len(arr) else None),
            "t_of_mean_Z": (_cell(arr)["t"] if len(arr) >= 4 else None),
            "note": "DECLARED SECONDARY. No verdict of its own (register section 2). Reading it "
                    "as a verdict is void condition 3."}


def run_arm(args):
    kp = os.path.join(REPO, KILLS_JSON)
    if not os.path.isfile(kp):
        raise SystemExit("[e1] REFUSING: no kills artifact. Run --kills first and read it "
                         "(register section 4: the kills run in their own pass).")
    with io.open(kp, encoding="utf-8") as fh:
        kills = json.load(fh)
    if not kills.get("all_kills_pass"):
        raise SystemExit("[e1] REFUSING: the kills artifact does not pass. The register "
                         "WITHDRAWS the arm rather than running it.")

    root = _root(args.data_root)
    panel = pickle.load(open(os.path.join(root, PANEL), "rb"))
    cols = [r["column"] for r in kills["census"]["graveyard"]]
    gv, n_ok, need = graveyard_column(panel, cols)
    panel = panel.assign(graveyard=gv)
    print(f"[e1] arm on the BANKED set of {len(cols)} signals (kills read from {KILLS_JSON})")

    result = {"item": "E-1", "register": "PREREG_e1_graveyard_stouffer.md",
              "register_commit": "e05c33c", "booking_commit": "dff46bc",
              "kills_read_from": KILLS_JSON, "bar": BAR, "two_sided": True,
              "bases_co_primary": list(BASES), "bases": {}}

    for b in BASES:
        inc = list(II.basis_for(b))
        cov = II.effective_coverage(panel, "graveyard", inc, min_names=II.MIN_NAMES,
                                    min_dates=II.MIN_DATES, ycol="fwd_ret")
        print(f"\n=== BASIS {b.upper()} ===")
        print(II.format_coverage(cov), flush=True)
        II.require_effective_coverage(cov, split_used="effective")

        ed = II.effective_dates(panel, "graveyard", inc, min_names=II.MIN_NAMES,
                                ycol="fwd_ret")
        early_d, late_d, boundary = halves(ed, min_dates=II.MIN_DATES)
        full_ics, _ = per_date_incremental_ic(panel, "graveyard", inc, ed)
        early_ics, _ = per_date_incremental_ic(panel, "graveyard", inc, early_d)
        late_ics, _ = per_date_incremental_ic(panel, "graveyard", inc, late_d)
        cells = {"full": _cell(full_ics), "early": _cell(early_ics), "late": _cell(late_ics)}

        # RUN_RULES A-11, printed on REALIZED coverage BEFORE the verdict is read.
        n_eff = len(ed)
        power = {"n_effective_dates": n_eff,
                 "mde_80pct_sd": PG.mde_at_power(n_eff, crit=BAR),
                 "mde_50pct_sd": PG.mde_at_power(n_eff, crit=BAR, z_power=0.0),
                 "strongest_raw_anchor_sd": STRONGEST_RAW_ANCHOR_SD,
                 "state": PG.state(effect=abs(cells["full"]["mean_ic"] or 0.0),
                                   se=(abs(cells["full"]["mean_ic"] or 0.0)
                                       / abs(cells["full"]["t"]))
                                   if cells["full"]["t"] else 1.0, crit=BAR)}
        print(f"[e1] A-11 power on realized coverage: {n_eff} effective dates, "
              f"MDE {power['mde_80pct_sd']:.4f} SD at 80pct, "
              f"{power['mde_50pct_sd']:.4f} SD at 50pct "
              f"(strongest raw anchor ever: {STRONGEST_RAW_ANCHOR_SD})")

        for k in ("full", "early", "late"):
            c = cells[k]
            t = c["t"]
            print(f"[e1]   {k:<6} n_dates {c['n_dates']:>3}  median IC "
                  f"{(c['median_ic'] if c['median_ic'] is not None else float('nan')):+.6f}  "
                  f"t {(t if t is not None else float('nan')):+.4f}  vs bar {BAR}")

        clears = {k: (cells[k]["t"] is not None and abs(cells[k]["t"]) >= BAR)
                  for k in ("full", "early", "late")}
        basis_confirmed = bool(clears["early"] and clears["late"])
        result["bases"][b] = {"incumbents": inc, "basis": II.basis_name(inc),
                              "coverage": cov, "boundary": str(boundary)[:10],
                              "cells": cells, "clears": clears, "power": power,
                              "both_halves_clear": basis_confirmed,
                              "stouffer_secondary": stouffer(panel, cols, ed)}
        st = result["bases"][b]["stouffer_secondary"]
        print(f"[e1]   SECONDARY Stouffer (no verdict): mean Z "
              f"{st['mean_Z'] if st['mean_Z'] is None else round(st['mean_Z'], 4)}, "
              f"t {st['t_of_mean_Z'] if st['t_of_mean_Z'] is None else round(st['t_of_mean_Z'], 4)}"
              f", denominator {st['denominator_sqrt_1R1']:.4f} over "
              f"{st['n_signals_in_matrix']} signals")

    # §2: both bases CO-PRIMARY -- the arm must clear BOTH halves on BOTH bases.
    confirmed = all(result["bases"][b]["both_halves_clear"] for b in BASES)
    result["verdict"] = "CONFIRMED" if confirmed else "NULL"
    result["verdict_rule"] = ("CONFIRMED requires |t| >= 2.71 in BOTH halves on BOTH co-primary "
                             "bases. Anything else is NULL (RUN_RULES A-6).")
    result["null_sentence"] = (
        "A NULL here means 'no diffuse aggregate at least as large as the best single signal "
        f"this panel has ever carried' ({STRONGEST_RAW_ANCHOR_SD} SD), never 'no effect'.")
    result["does_not_license"] = (
        "This verdict licenses NO component-level claim. Asking which signals carried the "
        "aggregate needs its own register and its own trial (register section 5, void "
        "condition 3). No per-signal outcome statistic is computed in the arm path.")
    _w(os.path.join(REPO, ARM_JSON), result)
    print(f"\n[e1] wrote {ARM_JSON}")
    print(f"[e1] VERDICT = {result['verdict']}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kills", action="store_true")
    ap.add_argument("--arm", action="store_true")
    ap.add_argument("--data-root", default=None)
    a = ap.parse_args()
    if a.kills:
        return run_kills(a)
    if a.arm:
        return run_arm(a)
    ap.error("choose --kills or --arm")


if __name__ == "__main__":
    sys.exit(main())
