#!/usr/bin/env python3
"""mb21_persistence_null.py — rebuild S22's per-horizon floors against a null that remembers. [MB21]

Executes VALQUO_MASTER_AUDIT_4.md item MB21. Everything about the design -- the instrument, the
draw count, the seeds, the dates, the statistic, the controls, the kill condition and the prior --
is fixed in PREREG_mb21_persistence_null.md, committed ALONE at ec55efe BEFORE this file existed.
Nothing here restates a threshold from a result.

TWO PASSES, AND THE SECOND REFUSES WITHOUT THE FIRST. Gating controls are computed and READ in
their own pass; `--floors` exits non-zero unless the controls artifact says `all_gating_pass`.
That is session 26's defect repaired rather than repeated -- a gating control that runs in the
same pass as the outcome it gates has not gated anything.

ADOPTS NOTHING. No file on a live scoring path is touched, TERM_STRUCTURE.json is opened
read-only, and valuation/web/hold_horizon.py is not edited by this lane (register section 6).

    python -m scripts.mb21_persistence_null --controls
    python -m scripts.mb21_persistence_null --floors --shard 0 --nshards 4
    python -m scripts.mb21_persistence_null --merge
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.term_structure import DEPLOYED, HORIZONS, arm, ret_col       # noqa: E402
from valuation.edge.fundamental_panel import placebo_panel, placebo_signal_cols  # noqa: E402
from valuation.studies.persistence_null import (                          # noqa: E402
    PRIMARY, THINNED, RegisterViolation, association_ic, composite_by_date, coverage_block,
    format_coverage, persistence_panel, rank_autocorrelation, stratified_panel,
    thinned_within_date_panel)

# ---- PRE-REGISTERED; see PREREG_mb21_persistence_null.md -----------------------------------
DRAWS = 200
SEED0 = 3000                 # deliberately NOT S22's 2000, so no reader can confuse the two
SEVEN = list(DEPLOYED)

#: register 6 -- the decisive cell, READ from the shipped artifact and never recomputed here.
KILL_HORIZON = 504
KILL_STATISTIC = "alpha_t_hac"
KILL_TOLERANCE = 0.05        # register 6: ambiguity resolves AGAINST the claim

#: register 4 -- the gating bars.
C1_SEEDS = [2000, 2001, 2002, 2003, 2004]     # S22's own seeds
C1_TOL = 1e-9
C2_DRAWS, C2_LAGS, C2_TOL = 20, (1, 2, 4, 8), 0.05
#: register 4 C3 fixes 200 draws, not 20. The first cut of this file used 20 and that is a
#: deviation from the register, so the CODE was corrected rather than the register.
C3_DRAWS, C3_TOL = DRAWS, 0.003
C4_MAX_ABS_MEDIAN = 0.5
C6_MAX_MEAN_FIXED_POINTS = 5.0

#: register 1 -- the real composite's persistence, measured read-only before the register.
#: These are the SHIPPED composite's values; the audit's 0.5802 / 0.4099 come from a composite
#: that does not renormalise by present-weight mass (register 1a).
REAL_AUTOCORR = {1: 0.5677, 2: 0.4709, 4: 0.4433, 8: 0.3983}

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"


def _root(explicit=None):
    """data/ is gitignored, so a worktree has an empty one. Resolve to a POPULATED root --
    existence is not population, which is DEEPITM-FIN's lesson and it cost that lane a run."""
    cands = [explicit, os.environ.get("VALQUO_DATA_ROOT"), DEFAULT_ROOT]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _ in range(6):
        cands.append(here)
        here = os.path.dirname(here)
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "data", "free_analysis",
                                             "panel_s22_h504.pkl")):
            return c
    raise SystemExit("[mb21] no data root holding data/free_analysis/panel_s22_h504.pkl")


def _load(root):
    """Load the panel, S22's artifact, and S22's own `common` date set.

    THE DATE COLUMN IS `str`, NOT datetime64, and this cost a run: coercing S22's stored dates
    to `pd.Timestamp` matched ZERO of 113,945 rows, `arm()` returned a bare status dict for the
    empty frame, and C1's max-|delta| loop -- which skips a cell whose value is None -- came back
    0.000e+00 on all five seeds. A PERFECT SCORE FROM A COMPARISON THAT COMPARED NOTHING. Hence
    both the normalisation below and C1's cell counter: a control that cannot say how many cells
    it checked cannot be read.
    """
    import pandas as pd
    panel = pd.read_pickle(os.path.join(root, "data", "free_analysis", "panel_s22_h504.pkl"))
    with open(os.path.join(root, "data", "free_analysis", "TERM_STRUCTURE.json"),
              encoding="utf-8") as fh:
        s22 = json.load(fh)

    def _key(d):
        return str(d)[:10]

    common = [_key(d) for d in s22["date_sets"]["common"]]
    keys = panel["date"].map(_key)
    sub = panel[keys.isin(common)].copy()
    if sub.empty:
        raise SystemExit("[mb21] the common-date filter matched ZERO rows -- refusing rather "
                         "than scoring an empty panel (panel date dtype %r, first %r; "
                         "S22 common first %r)"
                         % (panel["date"].dtype, panel["date"].iloc[0], common[0]))
    n_dates = sub["date"].nunique()
    if n_dates != len(common):
        raise SystemExit("[mb21] matched %d of S22's %d common dates -- refusing"
                         % (n_dates, len(common)))
    return panel, sub, s22, sorted(pd.unique(sub["date"].to_numpy()))


def _draw(sub, seed, cols, kind):
    if kind == PRIMARY:
        return persistence_panel(sub, seed, cols)
    if kind == THINNED:
        return thinned_within_date_panel(sub, seed, cols)
    raise RegisterViolation("unknown instrument %r" % (kind,))


def _score(pp, label):
    rec = {}
    for h in HORIZONS:
        a = arm(pp, h, label="%s_h%d" % (label, h))
        rec[str(h)] = {k: a.get(k) for k in ("alpha_t_hac", "ls_t_hac", "alpha_t_naive",
                                             "ls_t_naive", "cum_alpha", "n_periods")}
    return rec


# --------------------------------------------------------------------------- controls


def run_controls(root, out_path):
    panel, sub, s22, common = _load(root)
    cols = placebo_signal_cols(sub)
    res = {"instrument": PRIMARY, "register": "PREREG_mb21_persistence_null.md",
           "panel_rows": int(len(panel)), "scored_rows": int(len(sub)),
           "dates_scored": len(common), "permuted_cols": list(cols),
           "s22_dates_common": len(s22["date_sets"]["common"])}
    gate = {}

    # C7 first -- it is an assertion, not a measurement, and everything else assumes it.
    from valuation.studies.persistence_null import assert_no_forward_return_permuted
    assert_no_forward_return_permuted(cols)
    gate["C7_no_forward_return_permuted"] = True

    # ---- C1: the harness IS S22's ----------------------------------------------------------
    print("[mb21] C1: reproducing S22's own placebo draws ...", flush=True)
    c1, worst, cells = [], 0.0, 0
    for s in C1_SEEDS:
        stored = next((r for r in s22["placebo"]["rows"] if r["seed"] == s), None)
        if stored is None:
            raise SystemExit("[mb21] C1: seed %d absent from the S22 artifact" % s)
        mine = _score(placebo_panel(sub, seed=s, cols=cols), "c1_%d" % s)
        row = {"seed": s, "max_abs_delta": 0.0, "cells": 0}
        for h in HORIZONS:
            for k in ("alpha_t_hac", "ls_t_hac", "alpha_t_naive", "ls_t_naive"):
                a, b = stored[str(h)].get(k), mine[str(h)].get(k)
                if a is None or b is None:
                    continue
                row["cells"] += 1
                row["max_abs_delta"] = max(row["max_abs_delta"], abs(float(a) - float(b)))
        worst = max(worst, row["max_abs_delta"])
        cells += row["cells"]
        c1.append(row)
        print("    seed %d  %d cells  max |delta| %.3e"
              % (s, row["cells"], row["max_abs_delta"]), flush=True)
    # NON-VACUITY. Without this, an empty panel scores a perfect 0.000e+00 by comparing nothing
    # -- which is exactly what the first run of this control did.
    expected_cells = len(C1_SEEDS) * len(HORIZONS) * 4
    res["C1_harness_identity"] = {"seeds": C1_SEEDS, "rows": c1, "max_abs_delta": worst,
                                  "tolerance": C1_TOL, "cells_compared": cells,
                                  "cells_expected": expected_cells}
    gate["C1_harness_identity"] = bool(worst < C1_TOL and cells == expected_cells)
    print("    compared %d of %d cells%s"
          % (cells, expected_cells,
             "" if cells == expected_cells else "  <-- VACUOUS, control FAILS"), flush=True)

    # ---- C2 / C3 / C6 in ONE sweep over the registered 200 draws --------------------------
    # Each draw is built once and read by every control that wants it. C2 samples the first
    # C2_DRAWS of them, exactly as the register specifies; C3 and C6 read all of them.
    print("[mb21] C2/C3/C6: sweeping %d draws ..." % C3_DRAWS, flush=True)
    real_ac = {k: rank_autocorrelation(composite_by_date(sub, SEVEN, DEPLOYED, common), k)
               for k in C2_LAGS}
    got = {k: [] for k in C2_LAGS}
    assoc = {h: {"median": [], "mean": []} for h in (63, KILL_HORIZON)}
    ref = {h: {"median": [], "mean": []} for h in (63, KILL_HORIZON)}
    fps, fracs = [], []
    t0 = time.time()
    for i in range(C3_DRAWS):
        seed = SEED0 + i
        pp, info = _draw(sub, seed, cols, PRIMARY)
        fps.append(info["fixed_points"])
        fracs.append(info["rows_kept_frac"])
        if i < C2_DRAWS:
            cbd = composite_by_date(pp, SEVEN, DEPLOYED, common)
            for k in C2_LAGS:
                ac = rank_autocorrelation(cbd, k)
                if "mean" not in ac:
                    raise SystemExit("[mb21] C2: lag %d produced ZERO usable date pairs on "
                                     "draw %d -- refusing rather than reporting a control "
                                     "that measured nothing" % (k, seed))
                got[k].append(ac["mean"])
        for h in (63, KILL_HORIZON):
            a = association_ic(pp, SEVEN, DEPLOYED, ret_col(h), common)
            if a.get("median_ic") is None:
                raise SystemExit("[mb21] C3: no scorable dates on draw %d at H=%d" % (seed, h))
            assoc[h]["median"].append(a["median_ic"])
            assoc[h]["mean"].append(a["mean_ic"])
            # C3-REF: the INCUMBENT within-date null, same seed, same statistic. Without it a
            # nonzero reading cannot be attributed to THIS instrument rather than to the
            # statistic -- the median of a skewed per-date IC distribution need not be zero
            # even when the mean is.
            b = association_ic(placebo_panel(sub, seed=seed, cols=cols), SEVEN, DEPLOYED,
                               ret_col(h), common)
            ref[h]["median"].append(b["median_ic"])
            ref[h]["mean"].append(b["mean_ic"])
        if (i + 1) % 25 == 0:
            el = time.time() - t0
            print("    %d/%d  %.0fs elapsed, ~%.0fs left"
                  % (i + 1, C3_DRAWS, el, el / (i + 1) * (C3_DRAWS - i - 1)), flush=True)

    c2, ok2 = {}, True
    for k in C2_LAGS:
        m = float(np.mean(got[k]))
        dr = abs(m - real_ac[k]["mean"])
        c2[str(k)] = {"real_mean": real_ac[k]["mean"], "placebo_mean": m,
                      "abs_delta_vs_real": dr,
                      "abs_delta_vs_registered_69date": abs(m - REAL_AUTOCORR[k]),
                      "n_pairs": real_ac[k]["n_pairs"], "n_draws": len(got[k])}
        ok2 = ok2 and dr < C2_TOL
        print("    C2 lag %d  real %.4f  placebo %.4f  |delta| %.4f"
              % (k, real_ac[k]["mean"], m, dr), flush=True)
    res["C2_persistence_retained"] = {"tolerance": C2_TOL, "draws": C2_DRAWS, "by_lag": c2,
                                      "registered_real_69_dates": REAL_AUTOCORR}
    gate["C2_persistence_retained"] = bool(ok2)

    c3, ok3 = {}, True
    for h in (63, KILL_HORIZON):
        mm = float(np.mean(assoc[h]["median"]))
        rm = float(np.mean(ref[h]["median"]))
        c3[str(h)] = {
            "mean_of_median_ic": mm, "sd_of_median_ic": float(np.std(assoc[h]["median"])),
            "mean_of_mean_ic": float(np.mean(assoc[h]["mean"])),
            "within_date_reference_mean_of_median_ic": rm,
            "excess_over_within_date_reference": mm - rm,
            "n_draws": len(assoc[h]["median"]),
        }
        ok3 = ok3 and abs(mm) < C3_TOL
        print("    C3 H=%3d  mean median IC %+.5f  (bar +/-%.3f)   within-date ref %+.5f"
              % (h, mm, C3_TOL, rm), flush=True)
    res["C3_association_nil"] = {"tolerance": C3_TOL, "draws": C3_DRAWS, "by_horizon": c3}
    gate["C3_association_nil"] = bool(ok3)

    res["C6_fixed_points"] = {"mean": float(np.mean(fps)), "max": int(np.max(fps)),
                              "n_names": int(sub["ticker"].nunique()),
                              "bar_mean_below": C6_MAX_MEAN_FIXED_POINTS,
                              "n_draws": len(fps)}
    gate["C6_fixed_points"] = bool(np.mean(fps) < C6_MAX_MEAN_FIXED_POINTS)
    res["rows_kept_frac"] = {"mean": float(np.mean(fracs)), "min": float(np.min(fracs)),
                             "max": float(np.max(fracs))}
    print("    C6 fixed points  mean %.2f of %d names" % (np.mean(fps), sub["ticker"].nunique()),
          flush=True)

    pp0, _ = _draw(sub, SEED0, cols, PRIMARY)
    cov = coverage_block(sub, pp0, cols, common)
    res["C8_effective_coverage"] = cov
    gate["C8_effective_coverage"] = bool(cov["clears_cross_section_floor"]
                                         and cov["dates_scored"] == len(s22["date_sets"]["common"]))
    print("\n" + format_coverage(cov), flush=True)

    # ---- 2b: the stratified variant, reported as DISQUALIFIED ---------------------------------
    print("[mb21] 2b: re-measuring the disqualified stratified variant ...", flush=True)
    strat = []
    for s in (SEED0, SEED0 + 1, SEED0 + 2):
        sp, info = stratified_panel(sub, s, cols)
        rec = dict(info)
        for h in (63, KILL_HORIZON):
            a = association_ic(sp, SEVEN, DEPLOYED, ret_col(h), common)
            rec["assoc_h%d" % h] = {"median_ic": a.get("median_ic"), "ic_t": a.get("ic_t")}
        strat.append(rec)
    res["register_2b_stratified_disqualified"] = strat

    res["gating"] = gate
    res["all_gating_pass"] = bool(all(gate.values()))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)
    print("\n[mb21] gating: %s" % json.dumps(gate), flush=True)
    print("[mb21] all_gating_pass = %s -> %s" % (res["all_gating_pass"], out_path), flush=True)
    return 0 if res["all_gating_pass"] else 2


# --------------------------------------------------------------------------- floors


def run_floors(root, controls_path, shard, nshards, out_dir):
    if not os.path.isfile(controls_path):
        raise SystemExit("[mb21] --floors REFUSES: no controls artifact at %s" % controls_path)
    with open(controls_path, encoding="utf-8") as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        raise SystemExit("[mb21] --floors REFUSES: controls artifact does not pass "
                         "(gating=%s)" % json.dumps(ctrl.get("gating")))

    _, sub, _s22, common = _load(root)
    cols = placebo_signal_cols(sub)
    seeds = [SEED0 + i for i in range(DRAWS)][shard::nshards]
    print("[mb21] shard %d/%d: %d seeds, %s .. %s"
          % (shard, nshards, len(seeds), seeds[0], seeds[-1]), flush=True)

    rows = {PRIMARY: [], THINNED: []}
    t0 = time.time()
    for n, s in enumerate(seeds, 1):
        for kind in (PRIMARY, THINNED):
            pp, info = _draw(sub, s, cols, kind)
            rec = _score(pp, "%s_%d" % (kind, s))
            rec["seed"] = s
            rec["rows_kept_frac"] = info["rows_kept_frac"]
            rows[kind].append(rec)
        el = time.time() - t0
        print("[mb21] shard %d: %d/%d  %.0fs elapsed, ~%.0fs left"
              % (shard, n, len(seeds), el, el / n * (len(seeds) - n)), flush=True)

    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "MB21_SHARD_%02d_of_%02d.json" % (shard, nshards))
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"shard": shard, "nshards": nshards, "seeds": seeds, "rows": rows}, fh,
                  default=str)
    print("[mb21] wrote %s" % p, flush=True)
    return 0


# --------------------------------------------------------------------------- merge


def _floors(rows):
    def vals(h, k):
        return [r[str(h)][k] for r in rows if r[str(h)].get(k) is not None]

    out = {}
    for h in HORIZONS:
        d = {}
        for k in ("alpha_t_hac", "ls_t_hac", "alpha_t_naive", "ls_t_naive"):
            v = vals(h, k)
            d[k + "_p95"] = float(np.percentile(v, 95)) if v else None
            d[k + "_median"] = float(np.median(v)) if v else None
            d[k + "_max"] = float(np.max(v)) if v else None
        d["n_draws"] = len(vals(h, "alpha_t_hac"))
        out[str(h)] = d
    return out


def run_merge(root, controls_path, shard_dir, out_path):
    with open(controls_path, encoding="utf-8") as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        raise SystemExit("[mb21] --merge REFUSES: controls do not pass")

    files = sorted(glob.glob(os.path.join(shard_dir, "MB21_SHARD_*.json")))
    if not files:
        raise SystemExit("[mb21] --merge: no shards in %s" % shard_dir)
    rows = {PRIMARY: [], THINNED: []}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        for k in rows:
            rows[k].extend(d["rows"][k])
    n = len(rows[PRIMARY])
    if n != DRAWS:
        raise SystemExit("[mb21] --merge REFUSES: %d primary draws, register fixes %d"
                         % (n, DRAWS))
    if len({r["seed"] for r in rows[PRIMARY]}) != DRAWS:
        raise SystemExit("[mb21] --merge REFUSES: duplicate seeds across shards")

    _, _sub, s22, common = _load(root)
    obs = s22["primary_common_dates"]
    prim, thin = _floors(rows[PRIMARY]), _floors(rows[THINNED])
    s22f = s22["placebo"]["floors"]

    per_h = {}
    for h in HORIZONS:
        o = obs[str(h)]
        row = {
            "horizon": h, "quarters": h // 63, "hac_lag": o["hac_lag"],
            "observed_alpha_t_hac": o["alpha_t_hac"],
            "observed_ls_t_hac": o["ls_t_hac"],
            "observed_cum_alpha": o["cum_alpha"],
            "s22_within_date_alpha_p95": s22f[str(h)]["alpha_t_hac_p95"],
            "thinned_within_date_alpha_p95": thin[str(h)]["alpha_t_hac_p95"],
            "persistence_alpha_p95": prim[str(h)]["alpha_t_hac_p95"],
            "s22_within_date_ls_p95": s22f[str(h)]["ls_t_hac_p95"],
            "thinned_within_date_ls_p95": thin[str(h)]["ls_t_hac_p95"],
            "persistence_ls_p95": prim[str(h)]["ls_t_hac_p95"],
            "persistence_alpha_median": prim[str(h)]["alpha_t_hac_median"],
            "persistence_alpha_max": prim[str(h)]["alpha_t_hac_max"],
        }
        # register 7 -- the attribution, a DIAGNOSIS and never a defence.
        row["coverage_effect"] = row["thinned_within_date_alpha_p95"] - row["s22_within_date_alpha_p95"]
        row["memory_effect"] = row["persistence_alpha_p95"] - row["thinned_within_date_alpha_p95"]
        row["total_effect"] = row["persistence_alpha_p95"] - row["s22_within_date_alpha_p95"]
        row["clears_persistence_alpha_floor"] = bool(
            row["observed_alpha_t_hac"] > row["persistence_alpha_p95"] + KILL_TOLERANCE)
        row["clears_persistence_ls_floor"] = bool(
            row["observed_ls_t_hac"] > row["persistence_ls_p95"] + KILL_TOLERANCE)
        per_h[str(h)] = row

    k = per_h[str(KILL_HORIZON)]
    observed = k["observed_alpha_t_hac"]
    floor = k["persistence_alpha_p95"]
    if floor >= observed - KILL_TOLERANCE:
        verdict = "NOT SUPPORTED"
        consequence = ("S22-DISPLAY's two-year copy is WITHDRAWN OR RE-SCOPED. Named in register "
                       "section 6: hold_horizon.DEFENSIBLE's 'still ahead by about 5.1% "
                       "annualized two years later', ALPHA_ANN_TWO_YEARS, RANK_IC_TWO_YEARS and "
                       "the displayed CONSTANT-RATE verdict. THE PRODUCT EDIT IS ROUTED TO THE "
                       "APP LANE, NOT MADE BY THIS ONE.")
    else:
        verdict = "STANDS"
        consequence = ("S22 stands. The null upgrade is recorded as a CONFIRMATION and no "
                       "product copy changes.")

    c4 = {str(h): abs(prim[str(h)]["alpha_t_hac_median"]) < C4_MAX_ABS_MEDIAN for h in HORIZONS}
    out = {
        "item": "MB21", "register": "PREREG_mb21_persistence_null.md",
        "instrument": PRIMARY,
        "not_comparable_with": ("X7/session-10 floors (those include CPCV adoption); S22's "
                                "fixed_weights_null (that has no persistence); and not across "
                                "horizons, each floor being calibrated at its own configuration"),
        "draws": DRAWS, "seeds": [SEED0, SEED0 + DRAWS - 1],
        "dates_scored": len(common),
        "kill": {"horizon": KILL_HORIZON, "statistic": KILL_STATISTIC,
                 "observed_pinned_in_register": observed,
                 "persistence_floor": floor,
                 "tolerance": KILL_TOLERANCE,
                 "verdict": verdict, "consequence": consequence},
        "per_horizon": per_h,
        "floors_persistence": prim, "floors_thinned_within_date": thin,
        "C4_null_is_centred": {"bar_abs_median_below": C4_MAX_ABS_MEDIAN, "by_horizon": c4,
                               "pass": bool(all(c4.values()))},
        "controls": {"path": os.path.basename(controls_path),
                     "all_gating_pass": ctrl.get("all_gating_pass"),
                     "gating": ctrl.get("gating")},
        "effective_coverage": ctrl.get("C8_effective_coverage"),
        "trials": {"charged": 1, "domain": "infra",
                   "why": ("building and validating a null is infrastructure (HACFLOOR / "
                           "X7RECON precedent) and infra N gates no published claim; "
                           "re-scoring a landed claim on a NEW INSTRUMENT is not a new search "
                           "and charges nothing further")},
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print("\n" + "=" * 78)
    print("MB21 -- S22 against a null that remembers")
    print("=" * 78)
    print("%-5s %-9s | %-9s %-9s %-9s | %-8s %-8s" %
          ("H", "observed", "S22 p95", "thinned", "persist", "coverage", "memory"))
    for h in HORIZONS:
        r = per_h[str(h)]
        print("%-5d %+9.4f | %9.4f %9.4f %9.4f | %+8.4f %+8.4f  %s"
              % (h, r["observed_alpha_t_hac"], r["s22_within_date_alpha_p95"],
                 r["thinned_within_date_alpha_p95"], r["persistence_alpha_p95"],
                 r["coverage_effect"], r["memory_effect"],
                 "clears" if r["clears_persistence_alpha_floor"] else "DOES NOT CLEAR"))
    print("-" * 78)
    print("KILL CELL  H=%d %s: observed %.6f  vs persistence-preserving p95 %.6f"
          % (KILL_HORIZON, KILL_STATISTIC, observed, floor))
    print("VERDICT: %s" % verdict)
    print(consequence)
    print("=" * 78)
    print("[mb21] wrote %s" % out_path, flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--floors", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args(argv)

    root = _root(a.root)
    fa = os.path.join(root, "data", "free_analysis")
    controls = os.path.join(fa, "MB21_CONTROLS.json")
    out = os.path.join(fa, "MB21_PERSISTENCE_NULL.json")
    shards = os.path.join(fa, "mb21_shards")

    if a.controls:
        return run_controls(root, controls)
    if a.floors:
        return run_floors(root, controls, a.shard, a.nshards, shards)
    if a.merge:
        return run_merge(root, controls, shards, out)
    ap.error("one of --controls / --floors / --merge is required")


if __name__ == "__main__":
    raise SystemExit(main())
