"""MB22 + MB23 - the required-n power gate, and the Hodrick 1B cross-check.

    python -m scripts.mb22_mb23_power_and_hodrick [--panel PATH] [--json PATH] [--quick]

Register: `PREREG_mb22_mb23_power_and_hodrick.md`, committed ALONE (markdown, zero .py) as a
strict git ancestor of every measurement commit. Two infra trials.

WHAT IT RUNS, in the order the register fixed:

  A. MB22 positive controls - EXTERNAL (TIDEMARK's charter power table and `POWER_GATE.md`'s
     own published figures) and INTERNAL (this project's three recorded MDEs: `S19` +0.020549,
     `V2G` 1.8708 pp, `V6` +4.177 pp), plus the exactness of the two-route identity.
  B. MB23 estimator verification against PRINTED numbers - Wei-Wright (2009) FEDS 2009-27
     Table 1 coverage, at `alpha = 0` (the only case 1B is valid for) and, more
     discriminatingly, its published DEGRADATION away from that null.
  C. The null-calibration positive control, which reproduces `POWER_GATE.md` 5.2's recorded
     specification error INDEPENDENTLY on this implementation.
  D. THE CROSS-CHECK, with the register's pre-committed 10% bar, on the shipped H=63 statistics.
  E. The h-sweep, DIAGNOSTIC ONLY, carrying no verdict about `S22` (void condition, PREREG 2.4).

NOTHING HERE MOVES A CLAIM. Both branches of the cross-check were pre-committed to move nothing:
a pass validates an instrument and a fail flags one, and re-scoring `S22` would additionally
require `MB21`'s persistence-preserving null, which is NOT built here.

`RUN_RULES` rule 9 - the per-draw rows are banked, not just the percentiles: the artifact carries
every coverage cell's hit count and the full vector of null-calibration t-statistics.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import hodrick as HD                       # noqa: E402
from valuation.edge import power_gate as PG                    # noqa: E402
from valuation.edge import statistics as ST                    # noqa: E402

# ---- PRE-REGISTERED constants ------------------------------------------------------------
COVERAGE_TOL = 0.03          # PREREG 2.2, at 400 draws per cell
COVERAGE_REPS = 400
DEGRADATION_TOL = 0.05
DEGRADATION_REPS = 400
SEED = 20260819
AGREEMENT_TOL = HD.AGREEMENT_TOL       # 0.10, PREREG 2.3 - imported, never re-typed

DEPLOYED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
            "capital_discipline": 0.125, "size": 0.125, "institutional": 0.125}
PANEL_ROWS = 113945          # the corrected 69-date panel; POPULATION, not existence

#: Wei-Wright Table 1, the alpha = 0 column. (phi, rho, h, published coverage)
PUBLISHED_NULL = [(0.98, -0.5, 12, 0.95), (0.98, 0.0, 24, 0.95), (0.98, 0.5, 48, 0.94),
                  (0.99, -0.5, 48, 0.94), (0.99, 0.0, 12, 0.95), (0.99, 0.5, 36, 0.94)]
#: Table 1 Panel A, phi=0.98, rho=+0.5, h=48: the published collapse away from the null.
PUBLISHED_DEGRADATION = [(0.00, 0.94), (0.05, 0.71), (0.10, 0.53)]

#: TIDEMARK's charter power table, printed at crit 1.96 (POWER_GATE.md 1).
CHARTER_TABLE = [(0.20, 196), (0.30, 87), (0.15, 348)]
#: POWER_GATE.md 3.1's IR-needed column, at N = 66.
TIDEMARK_IR_NEEDED = [(82.3, 0.41), (45.8, 0.55), (25.2, 0.74), (52.4, 0.52)]


# ------------------------------------------------------------------ the published DGP
def simulate(T, phi, rho, alpha, rng):
    """Wei-Wright section 3, exactly.

        (r_t, x_t)' = Phi (r_{t-1}, x_{t-1})',  Phi = [[0, alpha], [0, phi]]
        e_t ~ iid N(0, Sigma),  Sigma = [[1, rho], [rho, 1]]

    x starts from its stationary distribution.
    """
    L = np.linalg.cholesky(np.array([[1.0, rho], [rho, 1.0]]))
    e = rng.standard_normal((T + 1, 2)) @ L.T
    x = np.empty(T + 1)
    r = np.empty(T + 1)
    x[0] = rng.standard_normal() / np.sqrt(1 - phi ** 2)
    r[0] = 0.0
    for t in range(1, T + 1):
        r[t] = alpha * x[t - 1] + e[t, 0]
        x[t] = phi * x[t - 1] + e[t, 1]
    return r[1:], x[1:]


def long_horizon_beta(alpha, phi, h):
    """Population slope of the h-period overlapping regression under that DGP.

    THE READING THIS SETTLES: Table 1's headings print "beta" and the values are the DGP's
    `alpha`, the ONE-period slope. Establishing that uses only the DGP - no estimator - so it is
    independent of the thing being verified.
    """
    return alpha * (1 - phi ** h) / (1 - phi)


def coverage(phi, rho, alpha, h, reps, T=500, seed=SEED):
    """Share of draws whose 95% Wald interval covers the true slope. Returns (rate, hits)."""
    rng = np.random.default_rng(seed)
    b_true = long_horizon_beta(alpha, phi, h)
    hits = 0
    for _ in range(reps):
        r, x = simulate(T, phi, rho, alpha, rng)
        f = HD.hodrick_1b(r, x, h)
        if abs((f["beta"] - b_true) / f["se"]) < 1.96:
            hits += 1
    return hits / reps, hits


# ------------------------------------------------------------------ A. MB22 controls
def mb22_controls():
    out = {"external": [], "internal": [], "identity": {}}
    for ir, printed in CHARTER_TABLE:
        got = PG.required_n(ir, crit=1.96)
        out["external"].append({"control": f"charter power table, IR {ir}", "got": got,
                                "printed": printed, "ok": abs(got - printed) <= 0.5})
    hurdle66 = ST.hlz_hurdle(66)
    out["external"].append({"control": "hlz_hurdle(66)", "got": hurdle66, "printed": 2.8947,
                            "ok": abs(hurdle66 - 2.8947) < 5e-5})
    req155 = PG.required_n(0.30, n_trials=66)
    out["external"].append({"control": "required_n(IR 0.30, N=66)", "got": req155,
                            "printed": 155.0, "ok": abs(req155 - 155.0) < 0.05})
    for yrs, printed in TIDEMARK_IR_NEEDED:
        got = PG.mde_at_power(yrs, n_trials=66)
        out["external"].append({"control": f"IR needed at {yrs} available years", "got": got,
                                "printed": printed, "ok": abs(got - printed) < 0.005})

    s19 = PG.detection_threshold_from_observed(0.012202150018043164, 1.1876022080477582,
                                               crit=2.0)
    out["internal"].append({"register": "S19 A1 (via MA33)", "got": s19, "recorded": 0.020549,
                            "ok": abs(s19 - 0.020549) < 5e-7})
    v2g = PG.detection_threshold(0.9354, crit=2.0)
    out["internal"].append({"register": "V2G paired HAC", "got": v2g, "recorded": 1.8708,
                            "ok": v2g == 1.8708})
    v6 = PG.detection_threshold(2.0885, crit=2.0)
    out["internal"].append({"register": "V6 A1", "got": v6, "recorded": 4.177,
                            "ok": v6 == 4.177})

    # V2G computed its own power and printed it. Reproducing that from the SAME two numbers is
    # what proves the two vocabularies below are one quantity read at two power levels.
    pw = PG.power_at(1.95, 0.9354, crit=1.96)
    out["internal"].append({"register": "V2G power at its own 1.95pp bar",
                            "got": round(pw * 100, 1), "recorded": 55.0,
                            "ok": abs(pw * 100 - 55.0) < 0.05})

    rng = np.random.default_rng(SEED)
    bad = 0
    for _ in range(2000):
        e = float(rng.uniform(-5, 5)) or 0.1
        t = float(rng.uniform(0.05, 9))
        if (PG.detection_threshold_from_observed(e, t, crit=2.0)
                != PG.detection_threshold(abs(e) / t, crit=2.0)):
            bad += 1
    out["identity"] = {"pairs": 2000, "exact_disagreements": bad, "ok": bad == 0}

    # THE DISTINCTION MB22 EXISTS TO KEEP STRAIGHT, quantified on this project's own numbers.
    out["vocabulary"] = {
        "note": ("Every MDE this project has published is crit*se, a 50%-power DETECTION "
                 "THRESHOLD. The 80%-power MDE is (crit+z)*se and is larger by "
                 "(crit+z)/crit."),
        "ratio_at_crit_2": (2.0 + PG.Z_POWER_CONVENTION) / 2.0,
        "S19_at_50pct": s19,
        "S19_at_80pct": (2.0 + PG.Z_POWER_CONVENTION) * (0.012202150018043164
                                                         / 1.1876022080477582),
        "V2G_at_50pct": v2g,
        "V2G_at_80pct": (2.0 + PG.Z_POWER_CONVENTION) * 0.9354,
    }
    out["all_ok"] = (all(c["ok"] for c in out["external"])
                     and all(c["ok"] for c in out["internal"])
                     and out["identity"]["ok"])
    return out


# ------------------------------------------------------------------ B/C. MB23 verification
def mb23_verification(quick=False):
    reps_n = 120 if quick else COVERAGE_REPS
    reps_d = 120 if quick else DEGRADATION_REPS
    out = {"published_null": [], "published_degradation": [], "identities": {},
           "reps_null": reps_n, "reps_degradation": reps_d, "seed": SEED}

    worst = 0.0
    for phi, rho, h, printed in PUBLISHED_NULL:
        got, hits = coverage(phi, rho, 0.0, h, reps=reps_n)
        dev = abs(got - printed)
        worst = max(worst, dev)
        out["published_null"].append({"phi": phi, "rho": rho, "h": h, "published": printed,
                                      "got": got, "hits": hits, "reps": reps_n,
                                      "abs_dev": dev, "ok": dev <= COVERAGE_TOL})
    out["max_abs_deviation_null"] = worst
    out["null_bar"] = COVERAGE_TOL
    out["null_ok"] = all(c["ok"] for c in out["published_null"])

    worst_d = 0.0
    for alpha, printed in PUBLISHED_DEGRADATION:
        got, hits = coverage(0.98, 0.5, alpha, 48, reps=reps_d)
        dev = abs(got - printed)
        worst_d = max(worst_d, dev)
        out["published_degradation"].append({"alpha": alpha, "published": printed, "got": got,
                                             "hits": hits, "reps": reps_d, "abs_dev": dev,
                                             "ok": dev <= DEGRADATION_TOL})
    out["max_abs_deviation_degradation"] = worst_d
    out["degradation_ok"] = all(c["ok"] for c in out["published_degradation"])

    # exact identities, no tolerance and no simulation
    rng = np.random.default_rng(1)
    T = 300
    x = rng.standard_normal(T)
    r = 0.3 * np.roll(x, 1) + rng.standard_normal(T)
    r[0] = rng.standard_normal()
    got = HD.hodrick_1b(r, x, 1)["se"]
    X = HD._design(x)[:T - 1]
    y = HD.overlapping_sums(r, 1)
    _, XtX_inv = HD.ols(y, X)
    e = r[1:] - r.mean()
    u = X * e[:, None]
    want = float(np.sqrt((XtX_inv @ (u.T @ u) @ XtX_inv)[1, 1]))
    rr = np.arange(1.0, 21.0)
    bumped = rr.copy()
    bumped[7] += 1000.0
    moved = HD.overlapping_sums(bumped, 4) - HD.overlapping_sums(rr, 4)
    out["identities"] = {
        "h1_collapses_to_white_sandwich": {"got": got, "want": want,
                                           "ok": bool(np.isclose(got, want, rtol=1e-12))},
        "no_leakage_of_r_t_into_y_t": {"at_t": float(moved[7]), "at_t_minus_h": float(moved[3]),
                                       "ok": bool(moved[7] == 0.0 and moved[3] == 1000.0)},
    }
    out["identities_ok"] = all(v["ok"] for v in out["identities"].values())
    return out


def mb23_null_calibration(quick=False):
    """POWER_GATE.md 5.2's specification error, reproduced INDEPENDENTLY on this port."""
    c = HD.null_calibration(phi=0.98, sd=1.0, n=500, h=12,
                            reps=200 if quick else 600, seed=SEED)
    c["reads"] = ("The estimator is correctly SIZED (unit variance, rejection at nominal) and "
                  "the AS-COMMITTED criterion flags it anyway. A rule that fails on the "
                  "verified case is a broken rule, not a finding about the data.")
    return c


# ------------------------------------------------------------------ D/E. the Valquo side
def load_series(panel_path):
    """The shipped H=63 per-period draws. POPULATION is checked, not existence.

    An empty or wrong-shaped panel that merely EXISTS is this project's own recorded failure
    (`DEEPITM-FIN`: a worktree's empty `bars` directory shadowed the populated one and the run
    reported a clean, plausible coverage null from an input that never loaded). So this raises
    rather than returning something a caller could mistake for a measurement.
    """
    import pickle
    with open(panel_path, "rb") as fh:
        panel = pickle.load(fh)
    if getattr(panel, "shape", (0,))[0] != PANEL_ROWS:
        raise RuntimeError(
            f"{panel_path} has {getattr(panel, 'shape', None)} rows, expected {PANEL_ROWS}. "
            "EXISTENCE IS NOT POPULATION - refusing to score a panel that is not the corrected "
            "69-date one.")
    from valuation.edge.fundamental_panel import quantile_backtest
    qb = quantile_backtest(panel, list(DEPLOYED), DEPLOYED, n_q=10, horizon=63,
                           return_series=True)
    return qb, qb["series"]


def resolve_panel(explicit=None):
    if explicit:
        return explicit
    for cand in (os.path.join(REPO, "data", "free_analysis", "panel_corrected_69d.pkl"),
                 r"C:\Users\donni\Downloads\valuation-tool\data\free_analysis"
                 r"\panel_corrected_69d.pkl"):
        if os.path.isfile(cand) and os.path.getsize(cand) > 1_000_000:
            return cand
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    ap.add_argument("--json", default=None,
                    help="defaults BESIDE the resolved panel, not under this checkout: a "
                         "worktree's data/ is gitignored AND disappears with the worktree, so "
                         "an artifact written there is lost rather than banked (RUN_RULES 9)")
    ap.add_argument("--quick", action="store_true",
                    help="fewer Monte-Carlo draws; for smoke-testing the wiring ONLY - a "
                         "quick run may NOT be quoted as the registered verification")
    a = ap.parse_args(argv)
    t0 = time.time()

    res = {"item": "MB22+MB23", "register": "PREREG_mb22_mb23_power_and_hodrick.md",
           "quick_run_not_quotable": bool(a.quick),
           "trials": {"domain": "infra", "charged": 2,
                      "note": "infra N gates no published claim"}}

    print("=" * 78)
    print("  MB22 - required-n / MDE gate: POSITIVE CONTROLS")
    print("=" * 78)
    res["mb22"] = mb22_controls()
    for c in res["mb22"]["external"]:
        print(f"  {'ok ' if c['ok'] else '** ':>4s}{c['control']:<42s} got {c['got']:>10.4f}"
              f"   printed {c['printed']}")
    for c in res["mb22"]["internal"]:
        print(f"  {'ok ' if c['ok'] else '** ':>4s}{c['register']:<42s} got {c['got']:>10.6g}"
              f"   recorded {c['recorded']}")
    print(f"  {'ok ' if res['mb22']['identity']['ok'] else '** ':>4s}"
          f"{'two MDE routes agree EXACTLY':<42s} "
          f"{res['mb22']['identity']['exact_disagreements']} disagreements over 2000 pairs")
    print(f"\n  VOCABULARY: every MDE this project has published is crit*se, a 50%-power")
    print(f"  DETECTION THRESHOLD. The 80%-power figure is "
          f"{res['mb22']['vocabulary']['ratio_at_crit_2']:.2f}x larger at crit 2.0.")

    print()
    print("=" * 78)
    print("  MB23 - estimator verification against PRINTED numbers")
    print("=" * 78)
    res["mb23_verification"] = mb23_verification(a.quick)
    v = res["mb23_verification"]
    for c in v["published_null"]:
        print(f"  {'ok ' if c['ok'] else '** ':>4s}phi={c['phi']} rho={c['rho']:+.1f} "
              f"h={c['h']:2d}: coverage {c['got']:.3f}  published {c['published']:.2f}  "
              f"|dev| {c['abs_dev']:.3f}")
    print(f"      max abs deviation {v['max_abs_deviation_null']:.4f} against a "
          f"pre-registered bar of {COVERAGE_TOL}")
    print("      -- and the more discriminating half, the PUBLISHED collapse away from b=0:")
    for c in v["published_degradation"]:
        print(f"  {'ok ' if c['ok'] else '** ':>4s}alpha={c['alpha']:.2f}: coverage "
              f"{c['got']:.3f}  published {c['published']:.2f}")
    for k, d in v["identities"].items():
        print(f"  {'ok ' if d['ok'] else '** ':>4s}{k}")

    print()
    res["mb23_null_calibration"] = mb23_null_calibration(a.quick)
    nc = res["mb23_null_calibration"]
    print("  POSITIVE CONTROL for the cross-check criterion itself "
          "(Wei-Wright phi=0.98, n=500, h=12):")
    print(f"      Var(t_H) {nc['var_t_hodrick']:.3f}   q97.5|t_H| "
          f"{nc['q975_abs_t_hodrick']:.3f}   rejection {nc['rejection_rate_at_1_96']:.3f}")
    print(f"      criterion CORRECTED (rejection vs nominal 0.05): "
          f"{'passes' if nc['agrees'] else '** fails'}")
    print(f"      criterion AS COMMITTED (q97.5 within 10% of 1.96): "
          f"{'passes' if nc['agrees_criterion_as_committed'] else '** FAILS on the verified cell'}")

    panel_path = resolve_panel(a.panel)
    out_json = a.json or os.path.join(
        os.path.dirname(panel_path) if panel_path
        else os.path.join(REPO, "data", "free_analysis"), "MB22_MB23.json")
    if not panel_path:
        res["mb23_cross_check"] = {"status": "SKIPPED - banked panel not available",
                                   "note": "NOT a null. Nothing was measured."}
        print("\n  ** cross-check SKIPPED: panel_corrected_69d.pkl not found. "
              "This is NOT a null - nothing was measured.")
    else:
        print()
        print("=" * 78)
        print("  MB23 - THE CROSS-CHECK, pre-committed bar "
              f"{AGREEMENT_TOL:.0%} on BOTH shipped H=63 statistics")
        print("=" * 78)
        qb, series = load_series(panel_path)
        res["panel"] = {"path": panel_path, "rows": PANEL_ROWS,
                        "long_short_tstat": qb["long_short_tstat"],
                        "top_decile_alpha": qb["top_decile_alpha"]}
        cc, sweep = {}, {}
        for name, label in (("long_short", "long-short spread"),
                            ("alpha", "top-decile alpha")):
            c = HD.cross_check(series[name], lag=ST.DEFAULT_HAC_LAG, h=1, tol=AGREEMENT_TOL)
            cc[name] = c
            print(f"  {label}:  Newey-West shipped {c['t_newey_west_shipped']:.6f}   "
                  f"same rows {c['t_newey_west_same_rows']:.6f}")
            print(f"  {'':>{len(label) + 3}s}Hodrick 1B      {c['t_hodrick_1b']:.6f}   "
                  f"naive {c['t_naive']:.6f}")
            print(f"  {'':>{len(label) + 3}s}gap vs shipped {c['relative_gap_vs_shipped']:.2%}"
                  f"   vs same rows {c['relative_gap_vs_same_rows']:.2%}   "
                  f"-> {'AGREES' if c['agrees'] else '** DISAGREES'}")
            sweep[name] = HD.horizon_sweep(series[name])
        res["mb23_cross_check"] = cc
        res["mb23_horizon_sweep"] = {
            "verdict": None,
            "void_condition": ("Quoting any h > 1 cell as a verdict about S22 voids the "
                               "register (PREREG 2.4). S22's null is separately "
                               "mis-specified (MB21) and is NOT fixed here."),
            "not_s22s_construction": ("These cumulate the SAME 69 quarterly draws. S22 built "
                                      "per-horizon forward returns from the panel's own "
                                      "fwd_ret_h{H} columns. Related object, not the same one."),
            "rows": sweep}
        agrees = all(c["agrees"] for c in cc.values())
        res["verdict"] = "VALIDATED" if agrees else "DISAGREES"
        res["verdict_note"] = ("Pre-committed: BOTH branches move no claim. A pass validates "
                               "an instrument; it does not re-score anything.")
        print()
        print("=" * 78)
        print(f"  MB23 VERDICT: {res['verdict']} - and NO CLAIM MOVES, as pre-committed.")
        print("=" * 78)
        print("  h-sweep (DIAGNOSTIC ONLY, no verdict about S22):")
        for name in ("long_short", "alpha"):
            gaps = " ".join(f"{r['relative_gap']:.1%}" for r in sweep[name]
                            if r.get("relative_gap") is not None)
            print(f"      {name:11s} h=1..8 gap: {gaps}")

    res["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\n  wrote {out_json}  [{res['elapsed_s']}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
