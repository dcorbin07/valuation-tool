"""E-2 / S-SEED-3 -- Δcomposite, fundamental momentum of the score itself.
`PREREG_e2_delta_composite.md`.

Register ACCEPTED VERBATIM from the Frontier Scout's draft and committed **ALONE** at `c93ffc8`,
markdown only, a strict git ancestor of this file. Equity trial booked at `441344c` BEFORE this
ran (`N` 238 -> 239).

**THE OBJECT.** `dc(i,t) = c(i,t) - c(i,t-1)` on consecutive rebalance dates, where `c` is the
SHIPPED composite under deployed weights via `composite_from_frame` -- the `B7`-renormalised
object `MB21` identified as the one `S22` actually scores. **Built by calling the shipped
function, never re-derived** (`MB18`'s defect two items ago), and the composite is required to
reproduce the published record before any kill is read (`C-FIDELITY`, the register's D2).

**IT IS A CHANGE IN RELATIVE STANDING, NOT AN ABSOLUTE IMPROVEMENT** -- `composite_from_frame`
standardises WITHIN each date, so a name whose fundamentals improve exactly as much as the
cross-section's has `dc` near zero. The register's D4 declares that in writing; every verdict
here is a verdict about relative standing.

TWO PASSES, and the separation is the register's §6 void condition 2 (`O10`'s process rule):
the kills run in their own pass and are READ before the arm.

    python -m scripts.e2_delta_composite --kills   # C-FIDELITY, K1..K3; no arm scored
    python -m scripts.e2_delta_composite --arm     # REFUSES without a passing kills artifact
"""
from __future__ import annotations

import argparse
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

import valuation.edge.fundamental_panel as FP                                 # noqa: E402
from valuation.edge import power_gate as PG                                   # noqa: E402
from valuation.edge.statistics import mean_inference                          # noqa: E402
from valuation.screener.cross_sectional import zscore                         # noqa: E402
from valuation.studies import incremental_ic as II                            # noqa: E402
from valuation.studies.incremental_ic import halves                           # noqa: E402

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join("data", "free_analysis", "panel_r5r6.pkl")
KILLS_JSON = os.path.join("data", "free_analysis", "E2_KILLS.json")
ARM_JSON = os.path.join("data", "free_analysis", "E2_ARM.json")

# --------------------------------------------------------------------------------------
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item.
# --------------------------------------------------------------------------------------
THEMES = ("value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional")
W = 0.125                      # the deployed weight, seven themes
BAR = 2.71                     # §3, X7's calibrated incremental-IC threshold
DECLARED_SIGN = "POSITIVE"     # §3, fixed before the run
KILL_RHO_MAX = 0.60            # §4, K1 / K2 / K3
BASES = ("six", "seven")       # §3, CO-PRIMARY
PEAD_COLS = ("z_pead_car", "z_pead_drift")   # D1: BOTH, fires if EITHER exceeds

#: §3's C-FIDELITY target -- the published record the differenced composite must reproduce.
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

#: the strongest RAW anchor this panel has ever carried, quoted with any null per §5.
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
    raise SystemExit(f"[e2] no data root holding {PANEL}")


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, default=str)


def _spearman(a, b):
    ra = pd.Series(a).rank().to_numpy(dtype=float)
    rb = pd.Series(b).rank().to_numpy(dtype=float)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


# ------------------------------------------------------------------ the object (§2)

def add_composite(panel):
    """The SHIPPED composite, per date, by CALLING `composite_from_frame`.

    Not re-derived. `MB18` re-derived a construction two items ago and its probe appeared to
    refute a mechanism it in fact confirmed; `MA28`'s `C1` caught a nine-theme composite wearing
    a seven-theme name on its own first run. `C-FIDELITY` then proves this is the shipped object
    rather than a lookalike.
    """
    out = []
    for d, g in panel.groupby("date", sort=True):
        c = FP.composite_from_frame(g, list(THEMES), {t: W for t in THEMES}, zscore)
        out.append(pd.Series(np.asarray(c, dtype=float), index=g.index))
    return pd.concat(out).reindex(panel.index)


def add_delta(panel):
    """§2: `dc(i,t) = c(i,t) - c(i,t-1)` on CONSECUTIVE rebalance dates.

    Presence at BOTH dates is required. The lag is taken over each name's own ordered dates and
    then REQUIRED to be the immediately preceding rebalance -- a name absent for a quarter must
    NOT silently difference across a two-quarter gap, which would be a longer lookback and §6
    void condition 1 forbids one.
    """
    dates = sorted(panel["date"].astype(str).str[:10].unique())
    pos = {d: i for i, d in enumerate(dates)}
    p = panel.assign(_i=panel["date"].astype(str).str[:10].map(pos))
    p = p.sort_values(["ticker", "_i"], kind="mergesort")
    prev_c = p.groupby("ticker")["composite"].shift(1)
    prev_i = p.groupby("ticker")["_i"].shift(1)
    consecutive = (p["_i"] - prev_i) == 1
    dc = (p["composite"] - prev_c).where(consecutive)
    return dc.reindex(panel.index), consecutive.reindex(panel.index).fillna(False)


def mean_abs_per_date_rho(panel, a, b):
    """Mean per-date |Spearman|, plus the DISTRIBUTION (no verdict).

    `E-1` added the distribution an hour ago because a kill that fires by hundredths invites the
    question of whether it is a stable property or a few dates dragging a mean. Carried here so
    the same question is answerable without re-running anything, whichever way the kill goes.
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
            "dates_above_bar": int((v > KILL_RHO_MAX).sum()),
            "share_above_bar": float((v > KILL_RHO_MAX).mean())}
    return float(np.mean(v)), len(vals), dist


# ------------------------------------------------------------------ pass 1: the kills

def run_kills(args):
    root = _root(args.data_root)
    panel = pickle.load(open(os.path.join(root, PANEL), "rb"))
    print(f"[e2] panel {panel.shape[0]:,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique():,} names")

    panel = panel.assign(composite=add_composite(panel))

    # ---- C-FIDELITY (register D2). A CONTROL: it can only BLOCK, never produce. ----
    res = FP.quantile_backtest(panel, list(THEMES), {t: W for t in THEMES}, n_q=10)
    got = {k: (float(res[k]) if res.get(k) is not None else None) for k in REC}
    worst, worst_at = 0.0, None
    for k, want in REC.items():
        d = abs((got[k] if got[k] is not None else float("nan")) - want)
        if d == d and d > worst:
            worst, worst_at = d, k
    fid_pass = bool(worst == 0.0)
    print(f"\n[e2] C-FIDELITY  the composite being differenced IS the shipped one")
    for k, want in REC.items():
        print(f"       {k:22s} got {got[k]!r}  want {want!r}")
    print(f"       max |delta| {worst:.3e} at {worst_at}  -> "
          f"{'PASS' if fid_pass else 'FIRES (the object is not the published one)'}")

    dc, consec = add_delta(panel)
    panel = panel.assign(dc=dc)
    elig = int(panel["dc"].notna().sum())
    print(f"\n[e2] delta coverage: {elig:,} of {len(panel):,} rows = {elig/len(panel):.4f}")
    per_date = panel.dropna(subset=["dc"]).groupby("date")["ticker"].nunique()
    print(f"       dates with a cross-section >= {II.MIN_NAMES}: "
          f"{int((per_date >= II.MIN_NAMES).sum())} of {panel['date'].nunique()}")
    print(f"       names per date: median {int(per_date.median())}, min {int(per_date.min())}")

    # survivor tilt, §2 requires it PRINTED not assumed
    kept = panel[panel["dc"].notna()]
    drop = panel[panel["dc"].isna()]
    tilt = {"median_market_cap_kept": float(pd.to_numeric(kept["market_cap"],
                                                          errors="coerce").median()),
            "median_market_cap_dropped": float(pd.to_numeric(drop["market_cap"],
                                                             errors="coerce").median())}
    tilt["ratio_kept_over_dropped"] = (tilt["median_market_cap_kept"]
                                       / tilt["median_market_cap_dropped"]
                                       if tilt["median_market_cap_dropped"] else None)
    print(f"       survivor tilt: median market cap kept {tilt['median_market_cap_kept']:,.0f} "
          f"vs dropped {tilt['median_market_cap_dropped']:,.0f} "
          f"(ratio {tilt['ratio_kept_over_dropped']:.3f})")

    kills = {}
    k1_rho, k1_n, k1_d = mean_abs_per_date_rho(panel, "dc", "momentum")
    kills["K1_vs_momentum_theme"] = {"rho": k1_rho, "n_dates": k1_n, "distribution": k1_d,
                                     "pass": bool(k1_rho is not None
                                                  and k1_rho <= KILL_RHO_MAX)}
    print(f"\n[e2] K1  |rho| vs the momentum theme : {k1_rho:.4f} ({k1_n} dates) vs "
          f"{KILL_RHO_MAX} -> {'PASS' if kills['K1_vs_momentum_theme']['pass'] else 'FIRES'}")

    # D1: BOTH banked PEAD columns; fires if EITHER exceeds. Stricter than either alone.
    k2_each = {}
    for c in PEAD_COLS:
        if c not in panel.columns:
            k2_each[c] = {"rho": None, "n_dates": 0, "distribution": {},
                          "note": "column absent"}
            continue
        r, n, d = mean_abs_per_date_rho(panel, "dc", c)
        k2_each[c] = {"rho": r, "n_dates": n, "distribution": d,
                      "coverage": float(panel[c].notna().mean())}
        print(f"[e2] K2  |rho| vs {c:14s}    : "
              f"{(r if r is not None else float('nan')):.4f} ({n} dates)")
    k2_vals = [v["rho"] for v in k2_each.values() if v["rho"] is not None]
    k2_pass = bool(k2_vals and max(k2_vals) <= KILL_RHO_MAX)
    kills["K2_vs_banked_pead"] = {"columns": k2_each, "max_rho": (max(k2_vals) if k2_vals else None),
                                  "rule": "BOTH banked columns; FIRES if EITHER exceeds the bar "
                                          "(register D1) -- stricter than either alone",
                                  "pass": k2_pass}
    print(f"[e2] K2  max over both              : "
          f"{(max(k2_vals) if k2_vals else float('nan')):.4f} vs {KILL_RHO_MAX} -> "
          f"{'PASS' if k2_pass else 'FIRES'}")

    k3_rho, k3_n, k3_d = mean_abs_per_date_rho(panel, "dc", "composite")
    kills["K3_vs_composite_level"] = {"rho": k3_rho, "n_dates": k3_n, "distribution": k3_d,
                                      "pass": bool(k3_rho is not None
                                                   and k3_rho <= KILL_RHO_MAX)}
    print(f"[e2] K3  |rho| vs the composite LEVEL: {k3_rho:.4f} ({k3_n} dates) vs "
          f"{KILL_RHO_MAX} -> {'PASS' if kills['K3_vs_composite_level']['pass'] else 'FIRES'}")
    print(f"       K3 per-date: median {k3_d['median']:.4f}, p05 {k3_d['p05']:.4f}, "
          f"p95 {k3_d['p95']:.4f}, {k3_d['dates_above_bar']} of {k3_n} above the bar "
          f"[diagnostic, NO VERDICT]")

    all_pass = bool(fid_pass and all(v["pass"] for v in kills.values()))
    out = {"item": "E-2", "register": "PREREG_e2_delta_composite.md",
           "register_commit": "c93ffc8", "booking_commit": "441344c",
           "C_FIDELITY": {"published": REC, "got": got, "max_abs_delta": worst,
                          "max_abs_delta_at": worst_at, "pass": fid_pass,
                          "note": "a CONTROL: can only BLOCK, never produce (MB1-SEL)"},
           "delta_coverage": {"eligible_rows": elig, "total_rows": int(len(panel)),
                              "share": elig / len(panel),
                              "dates_with_cross_section": int((per_date >= II.MIN_NAMES).sum()),
                              "median_names_per_date": int(per_date.median())},
           "survivor_tilt": tilt,
           "kills": kills, "bar": KILL_RHO_MAX, "ic_bar": BAR,
           "declared_sign": DECLARED_SIGN,
           "all_kills_pass": all_pass}
    _w(os.path.join(REPO, KILLS_JSON), out)
    print(f"\n[e2] wrote {KILLS_JSON}")
    print(f"[e2] ALL KILLS PASS = {all_pass}")
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


def run_arm(args):
    kp = os.path.join(REPO, KILLS_JSON)
    if not os.path.isfile(kp):
        raise SystemExit("[e2] REFUSING: no kills artifact. Run --kills first and read it "
                         "(register section 6, void condition 2).")
    with io.open(kp, encoding="utf-8") as fh:
        kills = json.load(fh)
    if not kills.get("all_kills_pass"):
        raise SystemExit("[e2] REFUSING: the kills artifact does not pass. The register "
                         "WITHDRAWS the arm rather than running it.")

    root = _root(args.data_root)
    panel = pickle.load(open(os.path.join(root, PANEL), "rb"))
    panel = panel.assign(composite=add_composite(panel))
    dc, _ = add_delta(panel)
    panel = panel.assign(dc=dc)
    print(f"[e2] arm (kills read from {KILLS_JSON})")

    result = {"item": "E-2", "register": "PREREG_e2_delta_composite.md",
              "register_commit": "c93ffc8", "booking_commit": "441344c",
              "kills_read_from": KILLS_JSON, "bar": BAR,
              "declared_sign": DECLARED_SIGN,
              "bases_co_primary": list(BASES), "bases": {}}

    for b in BASES:
        inc = list(II.basis_for(b))
        cov = II.effective_coverage(panel, "dc", inc, min_names=II.MIN_NAMES,
                                    min_dates=II.MIN_DATES, ycol="fwd_ret")
        print(f"\n=== BASIS {b.upper()} ===")
        print(II.format_coverage(cov), flush=True)
        II.require_effective_coverage(cov, split_used="effective")

        ed = II.effective_dates(panel, "dc", inc, min_names=II.MIN_NAMES, ycol="fwd_ret")
        early_d, late_d, boundary = halves(ed, min_dates=II.MIN_DATES)
        full_ics, _ = per_date_incremental_ic(panel, "dc", inc, ed)
        early_ics, _ = per_date_incremental_ic(panel, "dc", inc, early_d)
        late_ics, _ = per_date_incremental_ic(panel, "dc", inc, late_d)
        cells = {"full": _cell(full_ics), "early": _cell(early_ics), "late": _cell(late_ics)}

        n_eff = len(ed)
        power = {"n_effective_dates": n_eff,
                 "mde_80pct_sd": PG.mde_at_power(n_eff, crit=BAR),
                 "mde_50pct_sd": PG.mde_at_power(n_eff, crit=BAR, z_power=0.0),
                 "strongest_raw_anchor_sd": STRONGEST_RAW_ANCHOR_SD}
        print(f"[e2] A-11 power on realized coverage: {n_eff} effective dates, "
              f"MDE {power['mde_80pct_sd']:.4f} SD at 80pct, "
              f"{power['mde_50pct_sd']:.4f} SD at 50pct "
              f"(strongest raw anchor ever: {STRONGEST_RAW_ANCHOR_SD})")

        for k in ("full", "early", "late"):
            c = cells[k]
            t = c["t"]
            print(f"[e2]   {k:<6} n_dates {c['n_dates']:>3}  median IC "
                  f"{(c['median_ic'] if c['median_ic'] is not None else float('nan')):+.6f}  "
                  f"t {(t if t is not None else float('nan')):+.4f}  vs bar {BAR}")

        # DECLARED SIGN POSITIVE: a cell clears only in the declared direction.
        clears = {k: bool(cells[k]["t"] is not None and cells[k]["t"] >= BAR)
                  for k in ("full", "early", "late")}
        result["bases"][b] = {"incumbents": inc, "basis": II.basis_name(inc),
                              "coverage": cov, "boundary": str(boundary)[:10],
                              "cells": cells, "clears_in_declared_direction": clears,
                              "power": power,
                              "both_halves_clear": bool(clears["early"] and clears["late"])}

    confirmed = all(result["bases"][b]["both_halves_clear"] for b in BASES)
    result["verdict"] = "CONFIRMED" if confirmed else "NULL"
    result["verdict_rule"] = (
        f"CONFIRMED requires t >= {BAR} IN THE DECLARED POSITIVE DIRECTION in BOTH halves on "
        f"BOTH co-primary bases. Anything else is NULL (RUN_RULES A-6).")
    result["null_sentence"] = (
        "A NULL here means 'no trajectory effect at least as large as the best single signal "
        f"this panel has ever carried' ({STRONGEST_RAW_ANCHOR_SD} SD), never 'no effect'.")
    result["scope"] = (
        "THE OBJECT IS A CHANGE IN RELATIVE STANDING. composite_from_frame standardises WITHIN "
        "each date, so a name improving exactly as much as the cross-section has dc near zero. "
        "Register D4. This verdict is a verdict about relative standing.")
    _w(os.path.join(REPO, ARM_JSON), result)
    print(f"\n[e2] wrote {ARM_JSON}")
    print(f"[e2] VERDICT = {result['verdict']}")
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
