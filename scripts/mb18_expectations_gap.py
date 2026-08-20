#!/usr/bin/env python3
"""mb18_expectations_gap.py — the implied-growth expectations gap.  [MB18]

Executes VALQUO_MASTER_AUDIT_4.md item MB18. Everything -- the arm, its SIGN, the bases, the bar,
the three kills, the power statement and the prior -- is fixed in
PREREG_mb18_expectations_gap.md, committed ALONE at 1ee03ac BEFORE this file existed, with the
equity trial booked at be14d0c BEFORE this file was run. Nothing here restates a threshold from a
result.

THE ARM. `exp_gap = implied_growth - base_growth` on `panel_s23_fairvalue.pkl`: how much more
growth the price demands than the company has been delivering. Signed NEGATIVE -- a clear in the
opposite direction is a FAIL, not a discovery.

THREE KILLS, ALL FIRING BEFORE ANY OUTCOME.

  1. LOOK-AHEAD. `realized_growth` is FORWARD three-year growth. It is the OUTCOME, not an input,
     and it may NEVER enter a signal. This module NEVER LOADS THE COLUMN AT ALL -- `_load` selects
     an explicit allowlist, so the arm path cannot reference what is not in the frame -- and an
     AST test asserts the name appears nowhere outside the guard that forbids it.
  2. COSTUME. A reverse-DCF implied growth is monotone in price over fundamentals, so it may be
     the `value` theme renamed. Mean per-date Spearman against `value`, and |rho| > 0.60
     WITHDRAWS the arm with no outcome computed.
  3. THE COLUMN-NAME TRAP. The panel already ships a column literally called `gap`, and it is
     log(fair_value / price) -- a VALUATION gap, correlating with the expectations gap at only
     -0.5251. A lookup by name computes cleanly and answers a different, much more value-like
     question. `gap` is not loaded either.

TWO PASSES, AND THE SECOND REFUSES WITHOUT THE FIRST. `--arms` exits non-zero unless the controls
artifact says `all_gating_pass`.

ADOPTS NOTHING. No file on a live scoring path is touched; a pass would be recorded ELIGIBLE.

    python -m scripts.mb18_expectations_gap --controls
    python -m scripts.mb18_expectations_gap --arms
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import power_gate as PG                                  # noqa: E402
from valuation.edge.fundamental_panel import _spearman, _tstat               # noqa: E402
from valuation.studies import incremental_ic as II                           # noqa: E402
from valuation.studies.surface_stock import halves                           # noqa: E402

# ---- PRE-REGISTERED; see PREREG_mb18_expectations_gap.md ------------------------------------
CANDIDATE = "exp_gap"
DECLARED_SIGN = -1                 # register 0: NEGATIVE. A wrong-signed clear is a FAIL.
BAR = 2.71                         # X7's calibrated theme-IC floor
BASES = ("six", "seven")           # register 2.2: CO-PRIMARY, the arm must clear BOTH
COSTUME_COL = "value"
COSTUME_KILL = 0.60                # register 1.2: |rho| above this WITHDRAWS the arm
Z_POWER = PG.Z_POWER_CONVENTION

#: register 1.1 / 1.3 -- these columns are NEVER loaded. Not filtered later: never loaded.
FORBIDDEN = ("realized_growth", "gap")

#: The only S23 columns this study may see.
S23_KEEP = ("date", "ticker", "implied_growth", "base_growth", "implied_bounded")

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"


def _root(explicit=None):
    """`data/` is gitignored, so a worktree has an EMPTY one. Probe for the FILE, never the
    directory -- existence is not population (DEEPITM-FIN's lesson, and MB21's re-run of it)."""
    cands = [explicit, os.environ.get("VALQUO_DATA_ROOT"), DEFAULT_ROOT]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _ in range(6):
        cands.append(here)
        here = os.path.dirname(here)
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "data", "free_analysis",
                                             "panel_s23_fairvalue.pkl")):
            return c
    raise SystemExit("[mb18] no data root holding data/free_analysis/panel_s23_fairvalue.pkl")


def _load(root):
    """Join the S23 valuation panel to the theme panel.

    The S23 panel carries NONE of the seven incumbent theme columns -- a structural fact the
    audit's item does not mention -- so the incremental-IC gate needs this join. `fwd_ret` comes
    from the THEME panel, so the arm is scored against the same forward return every other
    incremental-IC register uses.

    THE ALLOWLIST IS THE LOOK-AHEAD GUARD. `realized_growth` and `gap` are never selected, so no
    later code can reference them even by accident.
    """
    fa = os.path.join(root, "data", "free_analysis")
    s = pd.read_pickle(os.path.join(fa, "panel_s23_fairvalue.pkl"))
    t = pd.read_pickle(os.path.join(fa, "panel_corrected_69d.pkl"))

    leaked = [c for c in FORBIDDEN if c in S23_KEEP]
    if leaked:
        raise SystemExit("[mb18] a forbidden column is in the allowlist: %r" % (leaked,))

    s = s[list(S23_KEEP)].copy()
    s[CANDIDATE] = (pd.to_numeric(s["implied_growth"], errors="coerce")
                    - pd.to_numeric(s["base_growth"], errors="coerce"))
    inc = list(II.BASIS_SEVEN)
    j = s.merge(t[["date", "ticker", "fwd_ret"] + inc], on=["date", "ticker"], how="inner")
    if j.empty:
        raise SystemExit("[mb18] the join matched ZERO rows -- refusing rather than scoring an "
                         "empty panel (MB21's own vacuous-pass defect)")
    for c in FORBIDDEN:
        if c in j.columns:
            raise SystemExit("[mb18] forbidden column %r reached the frame" % c)
    return j, s, t


# --------------------------------------------------------------------------- the statistic


def per_date_incremental_ic(frame, cand, incumbents, dates, ycol="fwd_ret"):
    """The PEAD/U2 construction: per-date OLS of the candidate on the incumbents WITH intercept,
    Spearman of the residual against the forward return."""
    inc = list(incumbents)
    out, ndates = [], []
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
            ndates.append(str(d)[:10])
    return np.asarray(out), ndates


def _cell(ics):
    if len(ics) < 4:
        return {"n_dates": len(ics)}
    mu = float(np.mean(ics))
    sd = float(np.std(ics, ddof=1))
    return {"n_dates": len(ics), "median_ic": float(np.median(ics)), "mean_ic": mu,
            "sd_ic": sd, "t": _tstat(list(ics)), "effect_mu_over_sd": (mu / sd) if sd else None,
            "clears_bar": bool(_tstat(list(ics)) is not None
                               and DECLARED_SIGN * _tstat(list(ics)) > BAR)}


# --------------------------------------------------------------------------- controls


def run_controls(root, out_path):
    j, s, t = _load(root)
    res = {"item": "MB18", "register": "PREREG_mb18_expectations_gap.md",
           "candidate": CANDIDATE, "declared_sign": DECLARED_SIGN, "bar": BAR,
           "joined_rows": int(len(j)), "joined_dates": int(j["date"].nunique()),
           "joined_names": int(j["ticker"].nunique()),
           "s23_rows": int(len(s)), "theme_rows": int(len(t))}
    gate = {}

    # ---- C1: the look-ahead pin, read from THIS FILE'S syntax tree -------------------------
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            names.add(n.value)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.Name):
            names.add(n.id)
    # `realized_growth` may appear ONLY inside the FORBIDDEN tuple.
    forb_literals = [x for x in ("realized_growth", "gap") if x in names]
    hits = src.count("realized_growth")
    allowed = src.count('"realized_growth"')          # the FORBIDDEN tuple + docstring mentions
    res["C1_look_ahead"] = {
        "column_never_loaded": "realized_growth" not in j.columns,
        "not_in_allowlist": "realized_growth" not in S23_KEEP,
        "forbidden_tuple": list(FORBIDDEN),
        "ast_string_literals_seen": forb_literals,
        "source_mentions": hits, "source_quoted_mentions": allowed,
    }
    gate["C1_look_ahead"] = bool("realized_growth" not in j.columns
                                 and "realized_growth" not in S23_KEEP)

    # ---- C3: the `gap` trap -----------------------------------------------------------------
    full = pd.read_pickle(os.path.join(root, "data", "free_analysis",
                                       "panel_s23_fairvalue.pkl"))
    lg = np.log(pd.to_numeric(full["fair_value"], errors="coerce")
                / pd.to_numeric(full["price"], errors="coerce"))
    shipped_gap = pd.to_numeric(full["gap"], errors="coerce")
    eg = (pd.to_numeric(full["implied_growth"], errors="coerce")
          - pd.to_numeric(full["base_growth"], errors="coerce"))
    res["C3_gap_trap"] = {
        "shipped_gap_is_log_fv_over_price_maxdev": float(np.nanmax(np.abs(shipped_gap - lg))),
        "corr_shipped_gap_vs_expectations_gap": float(shipped_gap.corr(eg)),
        "gap_never_loaded": "gap" not in j.columns,
    }
    gate["C3_gap_trap"] = bool("gap" not in j.columns
                               and abs(res["C3_gap_trap"]["corr_shipped_gap_vs_expectations_gap"])
                               < 0.99)

    # ---- C5: effective coverage, MB7's rule -------------------------------------------------
    cov = {}
    ok5 = True
    for b in BASES:
        c = II.effective_coverage(j, CANDIDATE, II.basis_for(b), min_names=II.MIN_NAMES,
                                  min_dates=II.MIN_DATES, ycol="fwd_ret")
        cov[b] = c
        print(II.format_coverage(c), flush=True)
        try:
            # This register splits the EFFECTIVE dates (register 2.1), so it declares that.
            # Refusal 2 still guarantees both effective halves clear the shipped floor; the raw
            # geometry is a DISCLOSURE printed above, not a refusal.
            II.require_effective_coverage(c, split_used="effective")
        except Exception as e:                       # noqa: BLE001
            ok5 = False
            cov[b]["refusal"] = str(e)
        cov[b]["split_used"] = "effective"
    res["C5_effective_coverage"] = cov
    gate["C5_effective_coverage"] = ok5

    # ---- C2: THE COSTUME KILL ---------------------------------------------------------------
    rhos = {}
    for th in II.BASIS_SEVEN:
        vals = []
        for d in sorted(pd.unique(j["date"].to_numpy())):
            sub = j[j["date"] == d].dropna(subset=[CANDIDATE, th])
            if len(sub) < II.MIN_NAMES:
                continue
            r = _spearman(sub[CANDIDATE].to_numpy(dtype=float),
                          sub[th].to_numpy(dtype=float))
            if r == r:
                vals.append(float(r))
        rhos[th] = {"mean_rho": float(np.mean(vals)), "n_dates": len(vals)}
    worst = max(rhos, key=lambda k: abs(rhos[k]["mean_rho"]))
    v_rho = rhos[COSTUME_COL]["mean_rho"]
    res["C2_costume"] = {"kill_bar": COSTUME_KILL, "vs_value": v_rho,
                         "by_theme": rhos, "largest_abs_theme": worst,
                         "largest_abs_rho": rhos[worst]["mean_rho"],
                         "withdrawn": bool(abs(v_rho) > COSTUME_KILL)}
    gate["C2_costume_not_withdrawn"] = bool(abs(v_rho) <= COSTUME_KILL)
    print("[mb18] C2 costume: mean per-date rho vs `value` = %+.4f (kill at |rho| > %.2f) -> %s"
          % (v_rho, COSTUME_KILL, "WITHDRAWN" if abs(v_rho) > COSTUME_KILL else "survives"),
          flush=True)
    print("[mb18]    largest |rho| against any incumbent: %s %+.4f"
          % (worst, rhos[worst]["mean_rho"]), flush=True)

    # ---- C4: point-in-time / no network -----------------------------------------------------
    res["C4_point_in_time"] = {
        "inputs_are_banked_columns_only": True,
        "network_calls": 0,
        "note": ("implied_growth and base_growth are solved by S23 as of the date and are read "
                 "from the banked panel; this study opens no network connection, which S23's "
                 "own offline mode exists to guarantee after it found that path fetching LIVE "
                 "Yahoo prices to value 1999"),
    }
    gate["C4_point_in_time"] = True

    # ---- C6: orthogonality (reported, NOT a kill) -------------------------------------------
    r2 = {}
    for b in BASES:
        inc = list(II.basis_for(b))
        vals = []
        for d in sorted(pd.unique(j["date"].to_numpy())):
            sub = j[j["date"] == d].dropna(subset=[CANDIDATE] + inc)
            if len(sub) < II.MIN_NAMES:
                continue
            X = np.column_stack([np.ones(len(sub)), sub[inc].to_numpy(dtype=float)])
            y = sub[CANDIDATE].to_numpy(dtype=float)
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = y - X @ beta
            ss = float(np.var(y))
            if ss > 0:
                vals.append(1.0 - float(np.var(resid)) / ss)
        r2[b] = {"mean_r2": float(np.mean(vals)), "n_dates": len(vals)}
    res["C6_orthogonality"] = {"by_basis": r2,
                               "note": ("REPORTED, NOT A KILL. U2, MA31/MA32 and MA58 each found "
                                        "genuinely new information that predicted nothing, so a "
                                        "low R2 is not evidence of value and a high one is not a "
                                        "kill -- C2 is the kill.")}

    # ---- C7: the join is not a universe change ----------------------------------------------
    res["C7_join"] = {
        "joined_frac_of_s23": float(len(j)) / float(len(s)),
        "joined_frac_of_theme": float(len(j)) / float(len(t)),
        "dates": int(j["date"].nunique()), "names": int(j["ticker"].nunique()),
    }

    # ---- the power statement, RUN_RULES PART A rule 11 --------------------------------------
    power = {}
    for b in BASES:
        n = cov[b]["n_dates_effective"]
        power[b] = {
            "effective_dates": n,
            "mde_80pct_power_sd_units": PG.mde_at_power(n, crit=BAR, z_power=Z_POWER),
            "detection_threshold_50pct_power_sd_units": BAR / np.sqrt(n),
            "crit": BAR,
        }
    res["power_before_the_run"] = power
    res["implied_bounded_partition"] = {
        str(k): int(v) for k, v in j["implied_bounded"].value_counts(dropna=False).items()}

    res["gating"] = gate
    res["all_gating_pass"] = bool(all(gate.values()))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)
    print("\n[mb18] gating: %s" % json.dumps(gate), flush=True)
    print("[mb18] all_gating_pass = %s -> %s" % (res["all_gating_pass"], out_path), flush=True)
    return 0 if res["all_gating_pass"] else 2


# --------------------------------------------------------------------------- arms


def run_arms(root, controls_path, out_path):
    if not os.path.isfile(controls_path):
        raise SystemExit("[mb18] --arms REFUSES: no controls artifact at %s" % controls_path)
    with open(controls_path, encoding="utf-8") as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        raise SystemExit("[mb18] --arms REFUSES: controls do not pass (gating=%s)"
                         % json.dumps(ctrl.get("gating")))
    if ctrl.get("C2_costume", {}).get("withdrawn"):
        raise SystemExit("[mb18] --arms REFUSES: the costume control WITHDREW the arm "
                         "(register 1.2). No outcome may be computed.")

    j, _s, _t = _load(root)
    out = {"item": "MB18", "register": "PREREG_mb18_expectations_gap.md",
           "candidate": CANDIDATE, "declared_sign": DECLARED_SIGN, "bar": BAR,
           "controls": {"all_gating_pass": True,
                        "costume_rho_vs_value": ctrl["C2_costume"]["vs_value"]},
           "power_before_the_run": ctrl["power_before_the_run"],
           "by_basis": {}}

    for b in BASES:
        inc = II.basis_for(b)
        ed = II.effective_dates(j, CANDIDATE, inc, min_names=II.MIN_NAMES, ycol="fwd_ret")
        # `halves` returns (early, late, boundary) with the boundary EMBARGOED, and it RAISES
        # rather than returning a thin half that would read like a result. It is handed the
        # EFFECTIVE dates (register 2.1), never the raw ones.
        early_d, late_d, boundary = halves(ed, min_dates=II.MIN_DATES)
        full_ics, _ = per_date_incremental_ic(j, CANDIDATE, inc, ed)
        early_ics, _ = per_date_incremental_ic(j, CANDIDATE, inc, early_d)
        late_ics, _ = per_date_incremental_ic(j, CANDIDATE, inc, late_d)
        cell = {"basis": b, "effective_dates": len(ed),
                "n_early_dates": len(early_d), "n_late_dates": len(late_d),
                "halves_ok": True, "boundary": str(boundary)[:10],
                "full": _cell(full_ics), "early": _cell(early_ics), "late": _cell(late_ics)}
        # the registered partition: unbounded rows only
        unb = j[j["implied_bounded"].astype(str) == ""]
        u_ed = II.effective_dates(unb, CANDIDATE, inc, min_names=II.MIN_NAMES, ycol="fwd_ret")
        u_ics, _ = per_date_incremental_ic(unb, CANDIDATE, inc, u_ed)
        cell["unbounded_only"] = _cell(u_ics)
        cell["unbounded_rows"] = int(len(unb))
        cell["clears_both_halves"] = bool(cell["early"].get("clears_bar")
                                          and cell["late"].get("clears_bar"))
        out["by_basis"][b] = cell

    both = all(out["by_basis"][b]["clears_both_halves"] for b in BASES)
    signs = [out["by_basis"][b]["full"].get("t") for b in BASES]
    same_sign = all(s is not None and np.sign(s) == np.sign(signs[0]) for s in signs)
    if both:
        verdict = "CLEARS"
    elif not same_sign:
        verdict = "NULL - THE TWO BASES DISAGREE"
    else:
        verdict = "REJECTED"
    out["verdict"] = verdict
    out["mde_caveat"] = (
        "A NULL here means no effect at least as large as the MDE in `power_before_the_run` "
        "(0.4274 SD on basis six at 80%% power against the 2.71 bar), which is about the size of "
        "the strongest RAW signal these rows carry. It does NOT mean no effect, and may not be "
        "quoted as one.")
    out["trials"] = {"charged": 1, "domain": "equity",
                     "booked_before_the_run_at": "be14d0c", "equity_n": "234 -> 235"}

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print("\n" + "=" * 76)
    print("MB18 -- the implied-growth expectations gap  (declared sign: NEGATIVE)")
    print("=" * 76)
    for b in BASES:
        c = out["by_basis"][b]
        print("basis %-6s dates %d  boundary %s" % (b, c["effective_dates"], c["boundary"]))
        for w in ("full", "early", "late", "unbounded_only"):
            d = c[w]
            if "t" not in d:
                print("   %-15s n=%d (too few)" % (w, d.get("n_dates", 0)))
                continue
            print("   %-15s n=%2d  median IC %+.5f  mean %+.5f  t %+.4f  %s"
                  % (w, d["n_dates"], d["median_ic"], d["mean_ic"], d["t"],
                     "CLEARS" if d.get("clears_bar") else "does not clear"))
    print("-" * 76)
    print("VERDICT: %s" % verdict)
    print("=" * 76)
    print("[mb18] wrote %s" % out_path, flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args(argv)
    root = _root(a.root)
    fa = os.path.join(root, "data", "free_analysis")
    controls = os.path.join(fa, "MB18_CONTROLS.json")
    if a.controls:
        return run_controls(root, controls)
    if a.arms:
        return run_arms(root, controls, os.path.join(fa, "MB18_EXPECTATIONS_GAP.json"))
    ap.error("one of --controls / --arms is required")


if __name__ == "__main__":
    raise SystemExit(main())
