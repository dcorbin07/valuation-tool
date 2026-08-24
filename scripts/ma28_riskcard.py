"""MA28-CARD — the accounting red-flag risk card. `PREREG_ma28_accounting_riskcard.md`.

The ONE register for `MA26-A` + `MA28` + `MA54-1`. Register committed ALONE at `6ff578b`,
markdown only, a strict git ancestor of this file. Budget booked at `7f294df`, before this ran.

**THE GATE IS THE CRASH-RATE REPLICATION, NOT ALPHA.** The claim is a disclosure — *names
carrying flag X went on to suffer outcome Y at rate Z against a base rate of W* — not a screen.
`quantile_backtest` appears in exactly ONE place in this file, control C1, which reproduces the
published headline to prove the panel is the right object and aborts if it does not. It is a gate
on the instrument and is never an input to a verdict. Calling it anywhere in the arm path is a
void condition of the register.

Run:
    python -m scripts.ma28_riskcard --controls-only     # C1..C7, no arm scored
    python -m scripts.ma28_riskcard --arms              # refuses without a passing controls file

TWO PASSES, and the separation is deliberate. Session 26's defect was computing a gating control
and the outcomes it gates in the same pass, so it could not be claimed the control was read
first. `--arms` REFUSES to run unless the controls artifact exists and passed.
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
sys.path.insert(0, os.path.join(REPO, "scripts"))

import valuation.edge.fundamental_panel as FP                      # noqa: E402
from s10_accounting_veto import build_flags                        # noqa: E402  ONE definition

# ---------------------------------------------------------------------------------------
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item.
# ---------------------------------------------------------------------------------------
CRASH = -0.50                 # §3.2 the ONE named bad outcome, over the panel's 63d window
RECORD_CORRECTION = -0.20     # §2 reported with NO verdict; may not become the arm
MIN_FLAGGED_PER_DATE = 30     # §3.4
MIN_KEPT_PER_DATE = 100       # §3.4
RATIO_FLOOR = 2.0             # §4 B2
ABS_FLOOR_PP = 0.50           # §4 B3
N_PERM = 500                  # §4 B1
PERM_SEED = 20260816
MIN_COVERAGE = 0.05           # §5 C2, the COVERAGE RULE floor
INERT_LO, INERT_HI = 0.005, 0.25          # §5 C3
SIZE_Q = 5                                # §5 C4
SIZE_RATIO_FLOOR = 1.5                    # §5 C4
SIZE_MIN_QUINTILES = 3                    # §5 C4
INCUMBENT_RHO_MAX = 0.50                  # §5 C5

# THE DEPLOYED COMPOSITE IS SEVEN THEMES AT 0.125 EACH, and getting that wrong is how C1
# earned its keep on the first run of this script. My first cut listed all NINE panel themes
# (adding `growth` and `low_risk`, which carry ZERO live weight) at W = 1/7, and C1 came back
# with alpha 0.0499 against the published 0.0717 -- a different composite wearing the right
# name. Nothing downstream would have raised; it would simply have measured the wrong book.
# Taken from the shipped `s10_accounting_veto.py` rather than retyped from memory a second time.
THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125

# C5 walks the SAME seven, plus the two zero-weight panel themes, because a flag could be a
# proxy for a theme the composite does not weight and that would still be a repackaging.
C5_THEMES = THEMES + ["growth", "low_risk"]

# C1: the published record this panel must reproduce, exactly.
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

PANEL = os.path.join("data", "free_analysis", "panel_r5r6.pkl")
CTRL_JSON = os.path.join("data", "free_analysis", "MA28_CARD_CONTROLS.json")
ARMS_JSON = os.path.join("data", "free_analysis", "MA28_CARD.json")


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------------
# the statistic -- DELEGATED to valuation/studies/crash_gate.py (I-3), 2026-08-20.
#
# The four functions that used to be written out here are now ONE implementation shared with
# every other crash-flag register (`E-4`, `E-5`/`INV-A`, `E-8`, `O-1`'s C1). B7's lesson: an
# idea written twice is an idea maintained once.
#
# WHAT DID NOT MOVE, DELIBERATELY: the register's CONSTANTS. `crash_gate` takes every bar
# keyword-only with no default, so the 2.0x ratio floor, the 0.50pp absolute floor, the 30/100
# per-date qualification counts and the seed are still declared HERE, by this register, and are
# still governed by the comment above them. MA5's finding is that a shared default is exactly
# how a bar freezes; a library that supplied these would let the next register inherit MA28's
# pre-registration without writing one.
#
# The refactor is proved INERT rather than asserted to be: `scripts/i3_crash_gate_validate.py`
# reproduces this file's own banked MA28_CARD.json at max |delta| 0.000e+00 across all three
# windows, and separately checks the library against the pre-refactor source restored from git.
# ---------------------------------------------------------------------------------------
from valuation.studies import crash_gate as CG                      # noqa: E402

_nw_t = CG.nw_t


def per_date_diff(df, crash_col="_crash"):
    return CG.per_date_diff(df, crash_col=crash_col,
                            min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                            min_kept_per_date=MIN_KEPT_PER_DATE)


def pooled(df, crash_col="_crash"):
    return CG.pooled(df, crash_col=crash_col)


def permutation_p95(df, crash_col="_crash", n=N_PERM, seed=PERM_SEED):
    return CG.permutation_null(df, crash_col=crash_col, n_draws=n, seed=seed,
                               min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                               min_kept_per_date=MIN_KEPT_PER_DATE)


def window_result(df, label):
    return CG.window_result(df, label, crash_col="_crash",
                            ratio_floor=RATIO_FLOOR, abs_floor_pp=ABS_FLOOR_PP,
                            n_perm=N_PERM, perm_seed=PERM_SEED,
                            min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                            min_kept_per_date=MIN_KEPT_PER_DATE)


# ---------------------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------------------
def load_panel(panel_path):
    with open(panel_path, "rb") as f:
        return pickle.load(f)


def attach_flags(panel, data_dir):
    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())
    flags = build_flags(data_dir, tickers, dates)
    p = panel.merge(flags, on=["date", "ticker"], how="left")
    p["flagged"] = p["vetoed"].fillna(False).astype(bool)
    p["_crash"] = pd.to_numeric(p["fwd_ret"], errors="coerce") <= CRASH
    p["_crash20"] = pd.to_numeric(p["fwd_ret"], errors="coerce") <= RECORD_CORRECTION
    return p


def halves(p):
    """First 34 dates / last 34, with the 35th EMBARGOED. Register §3.4."""
    ds = sorted(p["date"].unique())
    assert len(ds) == 69, f"expected 69 dates, got {len(ds)}"
    early, boundary, late = ds[:34], ds[34], ds[35:]
    return (p[p["date"].isin(early)], p[p["date"].isin(late)], str(boundary)[:10])


def run_controls(args):
    out = {"item": "MA28-CARD", "register": "PREREG_ma28_accounting_riskcard.md",
           "register_commit": "6ff578b", "budget_commit": "7f294df",
           "gate": "CRASH-RATE REPLICATION, NOT ALPHA",
           "crash_threshold": CRASH, "controls": {}}

    panel = load_panel(args.panel)
    _log(f"[panel] {panel.shape}, {panel['date'].nunique()} dates, "
         f"{panel['ticker'].nunique()} names")

    # ---- C1 GATING: reproduce the published headline, then abort if it does not ----
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(got.get(k) == v for k, v in REC.items())
    out["controls"]["C1_headline_reproduces"] = {"ok": bool(ok1), "measured": got,
                                                 "expected": REC}
    _log(f"[C1] headline reproduces exactly: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 FAILED — the panel is not the object the register describes"
        _w(args.controls_json, out)
        return 2

    p = attach_flags(panel, args.data_dir)

    # ---- C2 GATING: COVERAGE FIRST, before any rate is read ----
    cov = {
        "rows": int(len(p)),
        "beneish_computable": float(pd.to_numeric(p["beneish_m"], errors="coerce").notna().mean()),
        "altman_computable": float(pd.to_numeric(p["altman_z"], errors="coerce").notna().mean()),
        "extfin_computable": float(pd.to_numeric(p["extfin"], errors="coerce").notna().mean()),
        "beneish_flagged": float(p["beneish_flag"].fillna(False).mean()),
        "altman_flagged": float(p["altman_flag"].fillna(False).mean()),
        "extfin_flagged": float(p["extfin_flag"].fillna(False).mean()),
        "flagged_share": float(p["flagged"].mean()),
        "flagged_rows": int(p["flagged"].sum()),
    }
    out["controls"]["C2_coverage"] = cov
    _log(f"[C2] coverage {json.dumps(cov, default=float)}")
    below = [k for k in ("beneish_computable", "altman_computable", "extfin_computable")
             if cov[k] < MIN_COVERAGE]
    if below:
        out["controls"]["C2_coverage"]["VOID"] = below
        out["ABORTED"] = "C2 FAILED — an input is below the COVERAGE RULE floor"
        _w(args.controls_json, out)
        return 2

    # ---- C3: not inert ----
    inert_ok = INERT_LO < cov["flagged_share"] < INERT_HI
    out["controls"]["C3_not_inert"] = {"flagged_share": cov["flagged_share"],
                                       "band": [INERT_LO, INERT_HI], "ok": bool(inert_ok)}
    _log(f"[C3] not inert: {inert_ok}")

    # ---- C5: not a repackaged incumbent ----
    rhos = {}
    for th in C5_THEMES:
        if th not in p.columns:
            continue
        vals = []
        for _d, g in p.groupby("date", sort=True):
            a = pd.to_numeric(g[th], errors="coerce")
            b = g["flagged"].astype(float)
            m = a.notna()
            if m.sum() < 50 or b[m].nunique() < 2:
                continue
            vals.append(float(a[m].corr(b[m], method="spearman")))
        if vals:
            rhos[th] = float(np.mean(vals))
    mx = max(rhos, key=lambda k: abs(rhos[k])) if rhos else None
    out["controls"]["C5_incumbent_proxy"] = {
        "mean_per_date_spearman": rhos,
        "largest_abs": {"theme": mx, "rho": rhos.get(mx)} if mx else None,
        "bar": INCUMBENT_RHO_MAX,
        "ok": bool(mx is not None and abs(rhos[mx]) <= INCUMBENT_RHO_MAX)}
    _log(f"[C5] largest |rho| {mx} {rhos.get(mx)}")

    # ---- C7: the coverage asymmetry, reported not assumed ----
    n_computable = (pd.to_numeric(p["beneish_m"], errors="coerce").notna().astype(int)
                    + pd.to_numeric(p["altman_z"], errors="coerce").notna().astype(int)
                    + pd.to_numeric(p["extfin"], errors="coerce").notna().astype(int))
    c7 = {}
    for k in (0, 1, 2, 3):
        m = n_computable == k
        c7[f"{k}_inputs_computable"] = {
            "rows": int(m.sum()),
            "share": float(m.mean()),
            "flagged_share": float(p.loc[m, "flagged"].mean()) if int(m.sum()) else None,
            "crash_rate": float(p.loc[m, "_crash"].mean()) if int(m.sum()) else None}
    out["controls"]["C7_coverage_asymmetry"] = c7
    _log(f"[C7] {json.dumps(c7, default=float)}")

    out["controls_passed"] = bool(ok1 and not below and inert_ok)
    _w(args.controls_json, out)
    _log(f"[controls] wrote {args.controls_json}; passed={out['controls_passed']}")
    return 0


# ---------------------------------------------------------------------------------------
# arms
# ---------------------------------------------------------------------------------------
def run_arms(args):
    if not os.path.exists(args.controls_json):
        _log("[arms] REFUSED — no controls artifact. Run --controls-only first.")
        return 2
    with io.open(args.controls_json, encoding="utf-8") as f:
        ctrl = json.load(f)
    if not ctrl.get("controls_passed"):
        _log("[arms] REFUSED — the controls artifact does not record a pass.")
        return 2
    _log("[arms] controls artifact read and passing — proceeding")

    panel = load_panel(args.panel)
    p = attach_flags(panel, args.data_dir)
    early, late, boundary = halves(p)

    out = {"item": "MA28-CARD", "register": "PREREG_ma28_accounting_riskcard.md",
           "register_commit": "6ff578b", "budget_commit": "7f294df",
           "gate": "CRASH-RATE REPLICATION, NOT ALPHA",
           "crash_threshold": CRASH, "boundary_date_embargoed": boundary,
           "bars": {"B1": "within-date permutation p95", "B2_ratio_floor": RATIO_FLOOR,
                    "B3_abs_floor_pp": ABS_FLOOR_PP},
           "controls_read_from": args.controls_json,
           "windows": {}, "controls": {}}

    for name, frame in (("full_sample", p), ("early_half", early), ("late_half", late)):
        r = window_result(frame, name)
        out["windows"][name] = r
        _log(f"[A1:{name}] mean_d {r.get('mean_per_date_diff_pp')}pp  "
             f"ratio {r.get('pooled', {}).get('ratio')}  "
             f"B1 {r.get('B1_clears_permutation_p95')} B2 {r.get('B2_ratio_ge_2.0x')} "
             f"B3 {r.get('B3_abs_diff_ge_0.50pp')}")

    both = (out["windows"]["early_half"].get("clears_all_three")
            and out["windows"]["late_half"].get("clears_all_three"))

    # ---- C4: the size control the register expects to decide this ----
    q = p.copy()
    q["_mc"] = pd.to_numeric(q["market_cap"], errors="coerce")
    q["_sq"] = q.groupby("date")["_mc"].transform(
        lambda s: pd.qcut(s.rank(method="first"), SIZE_Q, labels=False, duplicates="drop")
        if s.notna().sum() >= SIZE_Q * 10 else np.nan)
    c4 = {}
    n_ok = 0
    for k in range(SIZE_Q):
        g = q[q["_sq"] == k]
        po = pooled(g) if len(g) else None
        ok = bool(po and po["ratio"] is not None and po["ratio"] >= SIZE_RATIO_FLOOR)
        n_ok += int(ok)
        c4[f"q{k + 1}"] = {"pooled": po, "clears_1.5x": ok,
                           "median_market_cap": float(g["_mc"].median()) if len(g) else None}
    c4_pass = n_ok >= SIZE_MIN_QUINTILES
    out["controls"]["C4_size"] = {
        "quintiles": c4, "quintiles_clearing_1.5x": n_ok,
        "required": SIZE_MIN_QUINTILES, "ok": bool(c4_pass),
        "median_mcap_flagged": float(q.loc[q["flagged"], "_mc"].median()),
        "median_mcap_kept": float(q.loc[~q["flagged"], "_mc"].median()),
        "note": ("Altman Z contains market cap directly (X4 = marketcap / liabilities), so this "
                 "flag is MECHANICALLY size-linked. Failing here labels the finding a SIZE SORT "
                 "and it may not be displayed whatever the arm says.")}
    _log(f"[C4] quintiles clearing 1.5x: {n_ok}/{SIZE_Q} -> {c4_pass}")

    out["controls"]["C5_incumbent_proxy"] = ctrl["controls"]["C5_incumbent_proxy"]
    c5_pass = bool(ctrl["controls"]["C5_incumbent_proxy"]["ok"])

    # ---- diagnostics, NO verdict ----
    per_flag = {}
    for col, nm in (("beneish_flag", "beneish"), ("altman_flag", "altman"),
                    ("extfin_flag", "extfin")):
        f = p[col].fillna(False).to_numpy(dtype=bool)
        c = p["_crash"].to_numpy(dtype=bool)
        if f.sum() and (~f).sum():
            per_flag[nm] = {"rate_flagged": float(c[f].mean()),
                            "rate_kept": float(c[~f].mean()),
                            "ratio": float(c[f].mean() / c[~f].mean()) if c[~f].mean() else None,
                            "n_flagged": int(f.sum())}
    # C7's sensitivity: 22% of rows carry FEWER THAN TWO computable inputs and therefore CANNOT
    # be flagged at all, whatever their accounts say. They sit in the "kept" group by
    # construction, so the base rate is partly a statement about names we could not score. The
    # arm stays as registered (all rows); this re-reads it on ELIGIBLE rows only and carries NO
    # verdict -- it exists so a coverage artefact cannot masquerade as a signal.
    n_comp = (pd.to_numeric(p["beneish_m"], errors="coerce").notna().astype(int)
              + pd.to_numeric(p["altman_z"], errors="coerce").notna().astype(int)
              + pd.to_numeric(p["extfin"], errors="coerce").notna().astype(int))
    elig = p[n_comp >= 2]
    elig_windows = {}
    for name, frame in (("full_sample", elig),
                        ("early_half", elig[elig["date"].isin(early["date"].unique())]),
                        ("late_half", elig[elig["date"].isin(late["date"].unique())])):
        po = pooled(frame)
        pdd = per_date_diff(frame)
        elig_windows[name] = {
            "pooled": po,
            "mean_per_date_diff_pp": float(pdd["d"].mean() * 100.0) if len(pdd) else None,
            "n_dates": int(len(pdd))}

    out["diagnostics_no_verdict"] = {
        "per_flag_individual": per_flag,
        "eligible_rows_only": {
            "definition": "rows with at least TWO of the three inputs computable",
            "rows_excluded": int((n_comp < 2).sum()),
            "share_excluded": float((n_comp < 2).mean()),
            "crash_rate_of_excluded_rows": float(p.loc[n_comp < 2, "_crash"].mean()),
            "windows": elig_windows,
            "note": ("A row with fewer than two computable inputs cannot reach 2 flags and so "
                     "is KEPT by construction. Reported because the base rate would otherwise "
                     "be partly a statement about names the flag could never have scored. NO "
                     "VERDICT: the registered arm is on all rows.")},
        "record_correction_at_minus_20pct": {
            "threshold": RECORD_CORRECTION,
            "pooled": pooled(p, "_crash20"),
            "note": ("VALQUO_MASTER_AUDIT.md:950 proposes a product sentence saying names "
                     "tripping 2 of 3 'fell 20%+ in a quarter 2.66% of the time against 0.87%'. "
                     "Those rates are the -50% rates. This is what -20% actually reads. NO "
                     "VERDICT attaches to it and it may not become the arm — register section 2.")},
    }

    verdict = "PASS" if (both and c4_pass and c5_pass) else "NULL"
    out["verdict"] = verdict
    out["verdict_detail"] = {
        "clears_all_three_in_both_halves": bool(both),
        "C4_size_ok": bool(c4_pass), "C5_incumbent_ok": bool(c5_pass),
        "rule": ("PASS requires B1+B2+B3 in BOTH halves AND C4 AND C5. Ambiguous against any "
                 "threshold is NULL, never a judgement call (RUN_RULES A6)."),
        "asymmetry": ("The register disclosed that it is NOT blind to the full-sample separation, "
                      "so a PASS here is WEAKER evidence than a FAIL would have been.")}
    _w(args.arms_json, out)
    _log(f"[VERDICT] {verdict}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(REPO, "data", "backtest"))
    ap.add_argument("--panel", default=os.path.join(REPO, PANEL))
    ap.add_argument("--controls-json", default=os.path.join(REPO, CTRL_JSON))
    ap.add_argument("--arms-json", default=os.path.join(REPO, ARMS_JSON))
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    if a.arms:
        return run_arms(a)
    return run_controls(a)


if __name__ == "__main__":
    raise SystemExit(main())
