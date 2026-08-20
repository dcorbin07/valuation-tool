"""E-3 / S-SEED-1 -- theme dispersion, the conviction statistic. `PREREG_e3_theme_dispersion.md`.

Register ACCEPTED from the Frontier Scout's draft and committed ALONE and BLIND at `5d308f5`
(markdown only, 218 lines, a strict ancestor of this file). The single EQUITY trial was booked
at `fa5433a`, before this file existed: equity 238 -> 239.

**THE COMPOSITE COMES FROM `composite_from_frame` AND IS NEVER RE-IMPLEMENTED** (`B7`, which
`E-1` re-proved days ago). The only thing this file supplies is the standardised matrix `Z` it
takes a row-wise SD over, and **C-IDENT gates on `composite(Z, w)` reproducing
`composite_from_frame(...)` elementwise at max |delta| 0.000e+00** -- both sides shipped
functions, so the identity is what proves `disp` and the composite are two moments of ONE
object rather than two lookalikes.

The incremental IC and its verdict come from the SHIPPED `surface_stock.arm_ic`,
`residualise` and `arm_verdict`; the coverage gate from `incremental_ic` (`MB7`). Nothing
statistical is written here that already exists there.

Run:
    python -m scripts.e3_theme_dispersion --controls   # C-IDENT, coverage, K1..K3, power
    python -m scripts.e3_theme_dispersion --arms       # REFUSES without a passing controls file

TWO PASSES. Computing a gating control and the outcomes it gates in one pass is session 26's
process defect and `O10`'s; `--arms` exits non-zero rather than proceeding.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import power_gate as PG                                    # noqa: E402
from valuation.edge.fundamental_panel import (composite, composite_from_frame)  # noqa: E402
from valuation.edge.research_log import trial_count                            # noqa: E402
# the SHIPPED standardiser, imported from the same place `fundamental_panel.py:1949`
# imports it for its own B7 call site -- not a lookalike from elsewhere in the tree
from valuation.screener.cross_sectional import zscore                          # noqa: E402
from valuation.studies import incremental_ic as II                             # noqa: E402
from valuation.studies.surface_stock import (IC_BAR, MIN_DATES, MIN_NAMES,      # noqa: E402
                                             arm_ic, arm_verdict, halves)

# ---------------------------------------------------------------------------------------
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item
# (§6.5). None of them is a new degree of freedom: the bar, the floors and the geometry are
# all shipped or inherited verbatim.
# ---------------------------------------------------------------------------------------
MIN_THEMES = 4                  # §2 eligibility. A sample SD of two or three numbers is noise.
DDOF = 1                        # §2, the sample standard deviation
KILL_RHO = 0.60                 # §4, all three kills
BASES = ("six", "seven")        # §3, BOTH co-primary and the arm must clear BOTH
DECLARED_SIGN = "negative"      # §3, the Diether-Malloy-Scherbina direction
BAR = IC_BAR                    # §3, 2.71 -- SHIPPED, an extrapolation, and labelled one
EXPECTED_R2_FLOOR = 0.20        # §7 expectation (6). Reported, NEVER a gate.

PANEL = os.path.join("data", "free_analysis", "panel_corrected_69d.pkl")
CTRL_JSON = "E3_CONTROLS.json"
ARMS_JSON = "E3_DISPERSION.json"
DEFAULT_OUT = os.path.join(REPO, "data", "free_analysis")

#: The deployed weights. Seven themes at 0.125 each -- MA28's C1 earned its keep on exactly
#: this: its first cut scored NINE panel themes at 1/7 and measured a different book under the
#: right name. The weight VALUE is irrelevant to `disp` (a SD is unweighted) and matters only
#: to C-IDENT's composite, which is why it is stated rather than assumed.
THEME_WEIGHT = 0.125


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------------
# the object
# ---------------------------------------------------------------------------------------
def standardised(sub: pd.DataFrame, cols: Sequence[str]) -> np.ndarray:
    """`Z` for one date: the per-date standardised theme columns.

    **THE SAME CONSTRUCTION `composite_from_frame` APPLIES**, and that is not asserted -- the
    caller gates it with `c_ident`. Building it here rather than reading it out of the
    composite is unavoidable (the shipped function returns only the weighted mean), so the
    identity control is what makes it the same object.

    §B2 of the register is why this cannot be skipped: the panel's theme columns are MEANS of
    z-scored numbers, so their per-date spreads differ by theme -- `S3` measured `quality` (ten
    inputs) near 0.50 against `insider` (one input) near 0.96. A dispersion over the raw
    columns would be a sort on how many inputs a theme happens to have.
    """
    return np.column_stack([zscore(sub[c]).values for c in cols])


def dispersion(Z: np.ndarray, min_themes: int) -> Tuple[np.ndarray, np.ndarray]:
    """Row-wise sample SD over the AVAILABLE entries, and the count of them.

    `ddof=1`, so a row with fewer than two available themes is undefined rather than zero. The
    eligibility floor is applied by the caller and ineligible rows are NaN -- never 0.0, which
    would read as "the themes agree perfectly" and is the fail-open this register's §2 forbids.
    """
    n = np.sum(~np.isnan(Z), axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        sd = np.nanstd(Z, axis=1, ddof=DDOF)
    sd = np.where(n >= int(min_themes), sd, np.nan)
    return sd, n


def c_ident(sub: pd.DataFrame, cols: Sequence[str], Z: np.ndarray) -> Dict[str, object]:
    """C-IDENT, GATING. `composite(Z, w)` must reproduce `composite_from_frame(...)` exactly.

    Both sides are SHIPPED functions; the only input this register supplies is `Z`. So an exact
    elementwise match is proof that the matrix `disp` is a spread of IS the matrix the composite
    is a weighted mean of -- `B7`'s requirement met by measurement rather than by two functions
    that look alike.
    """
    w = {c: THEME_WEIGHT for c in cols}
    mine = composite(Z, np.array([w[c] for c in cols], dtype=float))
    theirs = composite_from_frame(sub, list(cols), w, zscore)
    both = ~(np.isnan(mine) & np.isnan(theirs))
    nan_agree = bool(np.array_equal(np.isnan(mine), np.isnan(theirs)))
    d = np.abs(np.asarray(mine)[both] - np.asarray(theirs)[both])
    d = d[~np.isnan(d)]
    return {"n_compared": int(d.size), "max_abs_delta": float(d.max()) if d.size else None,
            "missing_pattern_identical": nan_agree,
            "ok": bool(d.size and nan_agree and float(d.max()) == 0.0)}


def build(panel: pd.DataFrame, basis: str, min_themes: int) -> Tuple[pd.DataFrame, Dict]:
    """Attach `disp_<basis>`, `n_themes_<basis>` and `abs_composite_<basis>` per date."""
    cols = list(II.basis_for(basis))
    dcol, ncol, acol = f"disp_{basis}", f"n_themes_{basis}", f"abs_composite_{basis}"
    out = panel.copy()
    out[dcol] = np.nan
    out[ncol] = 0
    out[acol] = np.nan
    ident = {"n_dates": 0, "max_abs_delta": 0.0, "dates_failing": [], "n_compared": 0,
             "missing_pattern_identical": True}
    for d, g in out.groupby("date", sort=True):
        idx = g.index
        Z = standardised(g, cols)
        ci = c_ident(g, cols, Z)
        ident["n_dates"] += 1
        ident["n_compared"] += int(ci["n_compared"])
        ident["missing_pattern_identical"] &= bool(ci["missing_pattern_identical"])
        if ci["max_abs_delta"] is not None:
            ident["max_abs_delta"] = max(ident["max_abs_delta"], float(ci["max_abs_delta"]))
        if not ci["ok"]:
            ident["dates_failing"].append(str(d)[:10])
        sd, n = dispersion(Z, min_themes)
        out.loc[idx, dcol] = sd
        out.loc[idx, ncol] = n
        out.loc[idx, acol] = np.abs(
            composite(Z, np.array([THEME_WEIGHT] * len(cols), dtype=float)))
    ident["ok"] = bool(not ident["dates_failing"] and ident["n_compared"] > 0
                       and ident["missing_pattern_identical"]
                       and ident["max_abs_delta"] == 0.0)
    return out, ident


# ---------------------------------------------------------------------------------------
# kills
# ---------------------------------------------------------------------------------------
def _spearman_rho(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    m = np.isfinite(a) & np.isfinite(b)
    if int(m.sum()) < MIN_NAMES:
        return None
    ra = pd.Series(a[m]).rank().to_numpy()
    rb = pd.Series(b[m]).rank().to_numpy()
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None                                   # a constant has no rank correlation
    return float(np.corrcoef(ra, rb)[0, 1])


def mean_per_date_rho(frame: pd.DataFrame, a: str, b: str) -> Dict[str, object]:
    """Mean per-date Spearman, with the dates it could not score COUNTED rather than dropped.

    A degenerate date returns `None` and is counted: if a comparison is undefined on most dates
    the mean of the remainder is not the statistic the kill names, and a reader has to be able
    to see that. `MB21`'s C1 scored a perfect result by comparing nothing.
    """
    vals, undefined = [], 0
    for _, g in frame.groupby("date", sort=True):
        r = _spearman_rho(g[a].to_numpy(dtype=float), g[b].to_numpy(dtype=float))
        if r is None or not np.isfinite(r):
            undefined += 1
        else:
            vals.append(r)
    if not vals:
        return {"mean_rho": None, "n_dates_scored": 0, "n_dates_undefined": int(undefined),
                "degenerate": True,
                "why": "no date could be scored; the comparison is undefined on this population"}
    return {"mean_rho": float(np.mean(vals)), "abs_mean_rho": float(abs(np.mean(vals))),
            "n_dates_scored": len(vals), "n_dates_undefined": int(undefined),
            "degenerate": False}


def kills_for(frame: pd.DataFrame, basis: str, label: str) -> Dict[str, object]:
    """K1/K2/K3 on one population. A kill FIRES when |mean rho| exceeds `KILL_RHO`.

    A DEGENERATE comparison is reported as `structurally_absent` and does NOT fire and does NOT
    pass -- the register's §B4: on the arm's scored rows the complete-case rule makes the theme
    count constant, and a Spearman against a constant is undefined, not a clean bill of health.
    """
    d, n, a = f"disp_{basis}", f"n_themes_{basis}", f"abs_composite_{basis}"
    out: Dict[str, object] = {"population": label, "basis": basis, "n_rows": int(len(frame))}
    for key, other, why in (("K1_size", "size", "R6's conviction aggregate died as a size sort"),
                            ("K2_abs_composite", a,
                             "a dispersion that just flags extreme names re-ranks the product"),
                            ("K3_theme_count", n,
                             "a dispersion that measures coverage is a data-quality column")):
        r = mean_per_date_rho(frame, d, other)
        fires = bool((not r["degenerate"]) and r.get("abs_mean_rho", 0.0) > KILL_RHO)
        out[key] = {**r, "bar": KILL_RHO, "fires": fires,
                    "structurally_absent": bool(r["degenerate"]), "why": why}
    out["any_fires"] = bool(any(out[k]["fires"] for k in
                                ("K1_size", "K2_abs_composite", "K3_theme_count")))
    return out


# ---------------------------------------------------------------------------------------
# CONTROLS PASS
# ---------------------------------------------------------------------------------------
def run_controls(args) -> int:
    with open(args.panel, "rb") as fh:
        panel = pickle.load(fh)
    _log(f"[panel] {len(panel)} rows, {panel['date'].nunique()} dates, "
         f"{panel['ticker'].nunique()} names")

    out: Dict[str, object] = {
        "item": "E-3", "also": "S-SEED-1",
        "register": "PREREG_e3_theme_dispersion.md", "register_commit": "5d308f5",
        "trial_commit": "fa5433a", "domain": "equity",
        "accepted_from": "PREREG_DRAFT_s1_theme_dispersion.md (Frontier Scout)",
        "constants": {"min_themes": MIN_THEMES, "ddof": DDOF, "kill_rho": KILL_RHO,
                      "bar": BAR, "declared_sign": DECLARED_SIGN, "bases": list(BASES),
                      "theme_weight": THEME_WEIGHT},
        "coverage_rule": II.COVERAGE_RULE,
        "bases": {},
    }

    ok_all = True
    for basis in BASES:
        cols = list(II.basis_for(basis))
        built, ident = build(panel, basis, MIN_THEMES)
        d = f"disp_{basis}"
        _log(f"[C-IDENT/{basis}] {ident['n_compared']} values, max |delta| "
             f"{ident['max_abs_delta']:.3e}, dates failing {len(ident['dates_failing'])} "
             f"-> {ident['ok']}")

        # ---- eligibility, MEASURED rather than borrowed (register §B1) ----
        nt = built[f"n_themes_{basis}"].to_numpy(dtype=int)
        have_y = built["fwd_ret"].notna().to_numpy()
        elig = np.isfinite(built[d].to_numpy(dtype=float))
        dist = {int(k): int(v) for k, v in
                pd.Series(nt).value_counts().sort_index().items()}
        scoreable_but_ineligible = int((have_y & (nt >= 2) & ~elig).sum())
        cost = (scoreable_but_ineligible / int((have_y & (nt >= 2)).sum())
                if int((have_y & (nt >= 2)).sum()) else None)

        # ---- MB7 coverage block, printed ----
        cov = II.effective_coverage(built, d, cols, min_names=MIN_NAMES, min_dates=MIN_DATES)
        try:
            II.require_effective_coverage(cov, split_used="effective")
            gate_ok, refusal = True, None
        except Exception as exc:                      # RegisterViolation
            gate_ok, refusal = False, str(exc)
        _log(f"[MB7/{basis}] {II.format_coverage(cov)}")

        ed = II.effective_dates(built, d, cols, min_names=MIN_NAMES)
        eff = built[built["date"].isin(ed)].dropna(subset=[d, "fwd_ret"] + cols)

        # ---- kills on BOTH populations (register §B4) ----
        elig_pop = built[np.isfinite(built[d].to_numpy(dtype=float))
                         & built["fwd_ret"].notna()]
        k_elig = kills_for(elig_pop, basis, "eligible_population")
        k_arm = kills_for(eff, basis, "arm_scored_rows")
        fires = bool(k_elig["any_fires"] or k_arm["any_fires"])
        _log(f"[kills/{basis}] eligible {[k_elig[k]['abs_mean_rho'] if not k_elig[k]['degenerate'] else None for k in ('K1_size','K2_abs_composite','K3_theme_count')]}")
        _log(f"[kills/{basis}] arm      {[k_arm[k]['abs_mean_rho'] if not k_arm[k]['degenerate'] else None for k in ('K1_size','K2_abs_composite','K3_theme_count')]}")

        # ---- power, BEFORE the verdict, both MB22 vocabularies (register §5) ----
        n_eff_dates = len(ed)
        se = 1.0 / np.sqrt(n_eff_dates) if n_eff_dates else None
        pw = None
        if se:
            pw = {"n_effective_dates": n_eff_dates,
                  "se_of_mean_ic_in_sd_units": float(se),
                  "detection_threshold_50pct_power_SD":
                      float(PG.detection_threshold(se, crit=BAR)),
                  "mde_at_80pct_power_SD":
                      float((BAR + PG.Z_POWER_CONVENTION) * se),
                  "crit": float(BAR),
                  "vocabulary": ("MB22: crit x se is a 50%-POWER detection threshold; the "
                                 "80%-power figure adds 0.84 se. Both are printed and each is "
                                 "labelled. Units are SD of the per-date IC series, so the "
                                 "figure is comparable with MB18's 0.4274 / 0.5071 class."),
                  "anchor": ("MB18 measured the strongest RAW anchor on rows of this shape at "
                             "z_fcf_margin 0.4346 SD, so a NULL here means 'no effect at least "
                             "as large as the best thing this panel has ever carried'.")}
            _log(f"[power/{basis}] {n_eff_dates} effective dates -> 50% "
                 f"{pw['detection_threshold_50pct_power_SD']:.4f} SD, 80% "
                 f"{pw['mde_at_80pct_power_SD']:.4f} SD")

        basis_ok = bool(ident["ok"] and gate_ok and not fires)
        ok_all = ok_all and basis_ok
        out["bases"][basis] = {
            "incumbents": cols,
            "C_IDENT": ident,
            "eligibility": {"theme_count_distribution": dist,
                            "min_themes": MIN_THEMES,
                            "rows_eligible": int(elig.sum()),
                            "rows_with_outcome_and_2plus_themes":
                                int((have_y & (nt >= 2)).sum()),
                            "scoreable_but_ineligible": scoreable_but_ineligible,
                            "share_cost": cost,
                            "note": ("MEASURED here rather than borrowed. The draft cited "
                                     "MA28's C7 22.01%, which counts ACCOUNTING-FLAG inputs "
                                     "and says nothing about theme availability.")},
            "MB7_effective_coverage": cov,
            "MB7_gate_ok": gate_ok, "MB7_refusal": refusal,
            "kills_eligible_population": k_elig,
            "kills_arm_scored_rows": k_arm,
            "any_kill_fires": fires,
            "power": pw,
            "ok": basis_ok,
        }

    out["all_gating_pass"] = bool(ok_all)
    _w(os.path.join(args.out_dir, CTRL_JSON), out)
    _log(f"[controls] all_gating_pass={out['all_gating_pass']} -> {CTRL_JSON}")
    return 0 if out["all_gating_pass"] else 3


# ---------------------------------------------------------------------------------------
# ARMS PASS
# ---------------------------------------------------------------------------------------
def run_arms(args) -> int:
    ctrl_path = os.path.join(args.out_dir, CTRL_JSON)
    if not os.path.exists(ctrl_path):
        _log("[arms] REFUSED: controls artifact missing. Run --controls first.")
        return 2
    with open(ctrl_path) as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        _log("[arms] REFUSED: controls artifact does not pass its gates.")
        return 2
    _log("[arms] controls artifact read and passing -- proceeding")

    with open(args.panel, "rb") as fh:
        panel = pickle.load(fh)

    out: Dict[str, object] = {
        "item": "E-3", "also": "S-SEED-1",
        "register": "PREREG_e3_theme_dispersion.md", "register_commit": "5d308f5",
        "trial_commit": "fa5433a", "domain": "equity", "trials": 1,
        "accepted_from": "PREREG_DRAFT_s1_theme_dispersion.md (Frontier Scout)",
        "bar": BAR, "declared_sign": DECLARED_SIGN,
        "bar_is_an_extrapolation": (
            "IC_BAR 2.71 is X7's calibrated RAW theme-IC p95 applied to an INCREMENTAL IC. U2, "
            "MA31, MA32, MA58 and MB18 all did the same; this register inherits that precedent "
            "and does not pretend it is a calibration."),
        "orthogonality_is_worth_nothing_here": (
            "residualise is LINEAR and a row-wise SD is a NON-linear function of the very "
            "columns it is residualised against, so a surviving residual is guaranteed by "
            "construction. A surviving incremental IC would be a claim about FUNCTIONAL FORM, "
            "never about new information (register §C)."),
        "controls_read_from": CTRL_JSON,
        "bases": {},
    }

    verdicts = []
    for basis in BASES:
        cols = list(II.basis_for(basis))
        built, _ = build(panel, basis, MIN_THEMES)
        d = f"disp_{basis}"
        ed = II.effective_dates(built, d, cols, min_names=MIN_NAMES)
        early, late, boundary = halves(list(ed), min_dates=MIN_DATES)

        full = arm_ic(built, d, ed, incumbents=cols)
        e = arm_ic(built, d, early, incumbents=cols)
        l = arm_ic(built, d, late, incumbents=cols)

        v = arm_verdict(e["incremental_ic_tstat"], l["incremental_ic_tstat"], d, bar=BAR,
                        power_ok=True,
                        degenerate_early=bool(e["incremental_degenerate"]),
                        degenerate_late=bool(l["incremental_degenerate"]))
        # DECLARED SIGN: a positive incremental IC is a CONTRADICTION, never a pass (§3).
        sign_ok = all((x["incremental_median_ic"] is not None
                       and x["incremental_median_ic"] < 0) for x in (full, e, l))
        verdict = v.get("verdict")
        if verdict == "ELIGIBLE" and not sign_ok:
            verdict = "CONTRADICTION"
        verdicts.append(verdict)

        out["bases"][basis] = {
            "incumbents": cols, "n_effective_dates": len(ed),
            "boundary_embargoed": str(boundary)[:10],
            "full": full, "early_half": e, "late_half": l,
            "shipped_arm_verdict": v, "declared_sign_respected": bool(sign_ok),
            "verdict": verdict,
            "mean_r2_on_incumbents": full.get("mean_r2_on_incumbents"),
            "r2_expectation_floor": EXPECTED_R2_FLOOR,
            "r2_above_expectation": bool((full.get("mean_r2_on_incumbents") or 0.0)
                                         > EXPECTED_R2_FLOOR),
            "power": ctrl["bases"][basis].get("power"),
        }
        _log(f"[{basis}] incremental IC t: full {full['incremental_ic_tstat']} "
             f"early {e['incremental_ic_tstat']} late {l['incremental_ic_tstat']} "
             f"| median IC {full['incremental_median_ic']} | R2 "
             f"{full.get('mean_r2_on_incumbents')} -> {verdict}")

    # BOTH bases co-primary: the arm must clear BOTH (MB18's rule, §3).
    if any(v == "CONTRADICTION" for v in verdicts):
        final = "CONTRADICTION"
    elif all(v == "ELIGIBLE" for v in verdicts):
        final = "CONFIRMED"
    else:
        final = "NULL"
    out["verdict"] = final
    out["per_basis_verdicts"] = dict(zip(BASES, verdicts))
    out["both_bases_required"] = (
        "MB18's rule: both bases are CO-PRIMARY and the arm must clear BOTH. Taking one alone "
        "would be choosing the design to buy power, MA58's void condition 5.")
    out["may_not_be_quoted_as"] = [
        "new information -- see orthogonality_is_worth_nothing_here",
        "a weighting, a sizing rule or any change to the book (§6.1)",
        "an MA55 claim -- different lenses, still unrun, its own register",
        "a per-name confidence or conviction label on any surface (V3)",
    ]
    _w(os.path.join(args.out_dir, ARMS_JSON), out)
    _log(f"\n[E-3] VERDICT {final}  per-basis {out['per_basis_verdicts']}")
    _log(f"[E-3] -> {ARMS_JSON}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=os.path.join(REPO, PANEL))
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    if a.arms:
        return run_arms(a)
    return run_controls(a)


if __name__ == "__main__":
    raise SystemExit(main())
