"""E-6 / S-SEED-2 -- the temporal axis (TIDEMARK transform). `PREREG_e6_temporal_axis.md`.

Register committed ALONE at `0008008` (markdown only, 268 lines, a strict ancestor of this
file); the single EQUITY trial was booked at `cfa9722`, before this file existed: 239 -> 240.

**THE BURN-IN IS AN OBSERVATION COUNT, AND §0 OF THE REGISTER IS WHY.** `I-2`'s census was
already published with two readings straddling the pre-committed 60% kill, so the choice was
made on an EXTERNAL anchor predating it -- TIDEMARK's `percentile.py` commits burn-in as a
count of valid observations at `76fa895`, 2026-08-16, four days before the census -- and on the
fact that the ported engine implements exactly that while `min_history_years` is an optional
extra with no default. **Both census numbers travel with every statement of the result, and
§4.3's calendar sensitivity bounds what the choice can have bought.**

**THIS ADDS AN AXIS AND SWAPS NOTHING.** `S20`/`S21` swapped the cross-sectional standardiser
and are the graveyard; no weight, standardiser or book statistic is touched here and an AST
test pins it.

Run:
    python -m scripts.e6_temporal_axis --controls   # K1..K4, power, no arm scored
    python -m scripts.e6_temporal_axis --arms       # REFUSES without a passing controls file
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import power_gate as PG                                    # noqa: E402
from valuation.studies import incremental_ic as II                             # noqa: E402
from valuation.studies import name_percentile as NP                            # noqa: E402
from valuation.studies.surface_stock import (IC_BAR, MIN_DATES, MIN_NAMES,      # noqa: E402
                                             arm_ic, arm_verdict, halves)

# ---------------------------------------------------------------------------------------
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item
# (§6.2). The burn-in in particular is DECLARED in §0.8 against an external anchor and may not
# be re-declared here or anywhere downstream.
# ---------------------------------------------------------------------------------------
VALUE_COL = "value"             # §2, the theme the seed names
BURN_IN = 20                    # §0.8, OBSERVATIONS -- never calendar years
MIN_HISTORY_YEARS = None        # §0.8, the calendar filter DECLINED for the primary
INVERT = False                  # §2, `value` is already oriented high = cheap = good
LAG_DAYS = 0                    # §2, the panel has applied its own lag
KILL_SHARE = 0.60               # §4 K1, the seed's own pre-committed kill
RENAME_RHO = 0.90               # §4 K3, catches a duplicate, not ordinary overlap
BASES = ("six", "seven")        # §3, BOTH co-primary and the arm must clear BOTH
DECLARED_SIGN = "positive"      # §3
BAR = IC_BAR                    # §3, 2.71 -- SHIPPED, an extrapolation, labelled one
SENSITIVITY_YEARS = 5.0         # §4.3, the reading §0 declined
CENSUS_BURN_INS = (4, 8, 12, 16, 20, 24)      # §4 K1, I-2's own grid, re-derived

#: `I-2`'s published readings, quoted so the artifact carries BOTH whatever the arm says (§0.1).
#: These are TARGETS the controls pass must REPRODUCE, never inputs to a decision.
I2_PUBLISHED = {"observations_20": 0.6060731054456098,
                "observations_20_AND_calendar_5y": 0.5888630479617359,
                "observations_21": 0.5883628066172276}
I2_REPRO_TOL = 1e-12

PANEL = os.path.join("data", "free_analysis", "panel_corrected_69d.pkl")
CTRL_JSON = "E6_CONTROLS.json"
ARMS_JSON = "E6_TEMPORAL_AXIS.json"
DEFAULT_OUT = os.path.join(REPO, "data", "free_analysis")


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


# ---------------------------------------------------------------------------------------
def build(panel: pd.DataFrame, min_history_years: Optional[float]) -> pd.DataFrame:
    """Attach `value_pct`, `n_history` and `history_years` to every row.

    `history_years` is carried on EVERY scored row and reaches the artifact, so a reader can
    check what "five years" actually bought instead of taking it on trust -- the port's own
    invitation and the register's §2.
    """
    pct = NP.name_percentiles(panel, VALUE_COL, burn_in=BURN_IN, invert=INVERT,
                              lag_days=LAG_DAYS)
    # NORMALISE BOTH SIDES BEFORE MERGING, AND REQUIRE THE MERGE TO HAVE MATCHED. The port
    # canonicalises dates through `validate_dates` while this panel carries them as strings, so
    # the two sides can differ in dtype. A dtype mismatch raises here, which is the SAFE
    # direction; the dangerous one is a merge that matches ZERO rows in SILENCE -- the hazard
    # this record already documents for these panels, where filtering a string date column with
    # a Timestamp matches nothing and raises nothing. So the join key is forced to one form and
    # the result is checked for having attached anything at all.
    left = panel.copy()
    left["date"] = left["date"].astype(str).str[:10]
    pct = pct.copy()
    pct["date"] = pct["date"].astype(str).str[:10]
    out = left.merge(pct, on=["ticker", "date"], how="left")
    if len(out) != len(panel):
        raise AssertionError(f"the percentile merge changed the row count: "
                             f"{len(panel)} -> {len(out)}")
    matched = float(out["n_history"].notna().mean()) if len(out) else 0.0
    if matched < 0.5:
        raise AssertionError(
            f"the percentile merge attached a history to only {matched:.4f} of rows; a "
            f"near-empty join is the silent failure this guard exists to make loud")
    ok = NP.eligible_rows(out, f"{VALUE_COL}_pct", min_history_years=min_history_years)
    out = out.copy()
    out["_eligible"] = ok.to_numpy(dtype=bool)
    out.loc[~out["_eligible"], f"{VALUE_COL}_pct"] = np.nan
    return out


def _mean_per_date_rho(frame: pd.DataFrame, a: str, b: str) -> Optional[float]:
    vals = []
    for _, g in frame.groupby("date", sort=True):
        x = pd.to_numeric(g[a], errors="coerce")
        y = pd.to_numeric(g[b], errors="coerce")
        m = x.notna() & y.notna()
        if int(m.sum()) < MIN_NAMES:
            continue
        if x[m].std() == 0 or y[m].std() == 0:
            continue
        vals.append(float(x[m].rank().corr(y[m].rank())))
    return float(np.mean(vals)) if vals else None


# ---------------------------------------------------------------------------------------
def run_controls(args) -> int:
    with open(args.panel, "rb") as fh:
        panel = pickle.load(fh)
    _log(f"[panel] {len(panel)} rows, {panel['date'].nunique()} dates, "
         f"{panel['ticker'].nunique()} names")

    out: Dict[str, object] = {
        "item": "E-6", "also": "S-SEED-2",
        "register": "PREREG_e6_temporal_axis.md", "register_commit": "0008008",
        "trial_commit": "cfa9722", "domain": "equity",
        "declaration": {
            "burn_in_observations": BURN_IN, "min_history_years": MIN_HISTORY_YEARS,
            "invert": INVERT, "lag_days": LAG_DAYS, "declared_sign": DECLARED_SIGN,
            "bar": BAR, "bases": list(BASES),
            "why": ("register §0: the burn-in is an OBSERVATION COUNT, declared against an "
                    "EXTERNAL anchor that predates I-2's census -- TIDEMARK percentile.py "
                    "commit 76fa895, 2026-08-16, four days before the census of 2026-08-20 -- "
                    "and because the ported engine implements the observation count while "
                    "min_history_years is an optional extra with no default. No argument from "
                    "which side of the kill either reading falls appears anywhere."),
        },
        "both_census_readings_published_by_I2": I2_PUBLISHED,
        "gates": {}, "bases": {},
    }

    # ---- K1: the burn-in census, RE-DERIVED and required to reproduce I-2 ----
    cen = NP.burn_in_census(panel, VALUE_COL, CENSUS_BURN_INS, invert=INVERT,
                            min_names_per_date=MIN_NAMES)
    at20 = next(b for b in cen["burn_ins"] if b["burn_in_observations"] == BURN_IN)
    share = float(at20["eligible_row_share"])
    repro = abs(share - I2_PUBLISHED["observations_20"]) <= I2_REPRO_TOL
    # the reading §0 declined, computed here so BOTH travel in this artifact
    cal = build(panel, SENSITIVITY_YEARS)
    cal_share = float(cal["_eligible"].mean())
    k1_ok = bool(share >= KILL_SHARE and repro)
    out["gates"]["K1_burn_in_census"] = {
        "declared_reading": "observations", "burn_in": BURN_IN,
        "eligible_row_share": share, "kill_bar": KILL_SHARE, "kill_fires": bool(share < KILL_SHARE),
        "reproduces_I2_published": repro,
        "calendar_reading_share_for_disclosure": cal_share,
        "eligible_names": at20["eligible_names"], "eligible_dates": at20["eligible_dates"],
        "first_eligible_date": at20["first_eligible_date"],
        "median_history_years_all_eligible_rows": at20["median_history_years_all_eligible_rows"],
        "median_history_years_at_eligibility": at20["median_history_years_at_eligibility"],
        "one_quarter_step": ("20 quarterly observations span 19 intervals = 4.75 years, so the "
                             "calendar reading is ~one further observation. The 60% bar sits "
                             "INSIDE that single step -- a finding about the BAR, reported "
                             "because it is true whichever side falls, and NOT an argument for "
                             "either reading (register §0.7)."),
        "ok": k1_ok,
    }
    _log(f"[K1] declared reading (observations, burn_in {BURN_IN}): {share:.6f} vs bar "
         f"{KILL_SHARE} -> fires={share < KILL_SHARE}; reproduces I-2 = {repro}")
    _log(f"[K1] the reading §0 DECLINED (calendar {SENSITIVITY_YEARS}y): {cal_share:.6f} "
         f"-- disclosed, never compared to the bar")
    _log(f"[K1] median history on eligible rows: "
         f"{at20['median_history_years_all_eligible_rows']:.3f} years")

    built = build(panel, MIN_HISTORY_YEARS)
    cand = f"{VALUE_COL}_pct"

    # ---- K3: not a renamed incumbent (executor's control; can only block) ----
    elig = built[built["_eligible"] & built["fwd_ret"].notna()]
    rhos = {c: _mean_per_date_rho(elig, cand, c) for c in II.BASIS_SEVEN}
    worst = max(((c, v) for c, v in rhos.items() if v is not None),
                key=lambda kv: abs(kv[1]), default=(None, None))
    k3_ok = bool(worst[1] is None or abs(worst[1]) <= RENAME_RHO)
    out["gates"]["K3_not_a_renamed_incumbent"] = {
        "mean_per_date_rho": rhos, "largest": {"theme": worst[0], "rho": worst[1]},
        "bar": RENAME_RHO, "ok": k3_ok,
        "note": ("the interesting cell is `momentum`: a high own-history value percentile is a "
                 "name whose value score has RISEN, which is a change signal. Diagnostic, NO "
                 "verdict -- the incremental gate handles ordinary overlap by construction."),
    }
    _log(f"[K3] largest |rho| vs an incumbent: {worst[0]} {worst[1]} (bar {RENAME_RHO}) "
         f"-> {k3_ok}")

    # ---- K2 (S18 floor via MB7's repaired gate) + power, per basis ----
    ok_all = k1_ok and k3_ok
    for basis in BASES:
        cols = list(II.basis_for(basis))
        cov = II.effective_coverage(built, cand, cols, min_names=MIN_NAMES, min_dates=MIN_DATES)
        try:
            II.require_effective_coverage(cov, split_used="effective")
            gate_ok, refusal = True, None
        except Exception as exc:
            gate_ok, refusal = False, str(exc)
        _log(f"[MB7/{basis}] {II.format_coverage(cov)}")
        ed = II.effective_dates(built, cand, cols, min_names=MIN_NAMES)
        n = len(ed)
        se = 1.0 / np.sqrt(n) if n else None
        pw = None
        if se:
            pw = {"n_effective_dates": n, "se_of_mean_ic_in_sd_units": float(se),
                  "detection_threshold_50pct_power_SD": float(PG.detection_threshold(se, crit=BAR)),
                  "mde_at_80pct_power_SD": float((BAR + PG.Z_POWER_CONVENTION) * se),
                  "crit": float(BAR),
                  "vocabulary": ("MB22: crit x se is a 50%-POWER detection threshold; the "
                                 "80%-power figure adds 0.84 se. Both printed, each labelled."),
                  "anchor": ("MB18's strongest RAW anchor on rows of this shape is z_fcf_margin "
                             "at 0.4346 SD, so a NULL means 'no effect at least as large as the "
                             "best thing this panel has ever carried'.")}
            _log(f"[power/{basis}] {n} effective dates -> 50% "
                 f"{pw['detection_threshold_50pct_power_SD']:.4f} SD, 80% "
                 f"{pw['mde_at_80pct_power_SD']:.4f} SD")
        hist = pd.to_numeric(built.loc[built["date"].isin(ed) & built["_eligible"],
                                       "history_years"], errors="coerce")
        ok_all = ok_all and gate_ok
        out["bases"][basis] = {
            "incumbents": cols, "MB7_effective_coverage": cov,
            "K2_MB7_gate_ok": gate_ok, "K2_refusal": refusal,
            "n_effective_dates": n, "power": pw,
            "history_years_on_scored_rows": {
                "median": float(hist.median()) if len(hist) else None,
                "p05": float(hist.quantile(0.05)) if len(hist) else None,
                "min": float(hist.min()) if len(hist) else None},
        }

    # ---- K4: no look-ahead, from the census artifact the port's own run produced ----
    src = os.path.join(args.out_dir, "I2_BURN_IN_CENSUS.json")
    k4 = {"source": src, "present": os.path.exists(src)}
    if k4["present"]:
        with open(src) as fh:
            j = json.load(fh)
        la = j.get("no_lookahead_on_the_real_panel", {})
        k4.update({"max_abs_delta": la.get("max_abs_delta"),
                   "rows_compared": la.get("rows_compared"),
                   "ok": bool(la.get("max_abs_delta") == 0.0
                              and int(la.get("rows_compared") or 0) > 10_000)})
    else:
        k4["ok"] = False
        k4["why"] = "the I-2 census artifact is absent; the look-ahead check cannot be read"
    out["gates"]["K4_no_lookahead"] = k4
    ok_all = ok_all and bool(k4["ok"])
    _log(f"[K4] look-ahead max |delta| {k4.get('max_abs_delta')} over "
         f"{k4.get('rows_compared')} rows -> {k4['ok']}")

    out["all_gating_pass"] = bool(ok_all)
    _w(os.path.join(args.out_dir, CTRL_JSON), out)
    _log(f"[controls] all_gating_pass={out['all_gating_pass']} -> {CTRL_JSON}")
    return 0 if out["all_gating_pass"] else 3


# ---------------------------------------------------------------------------------------
def score(built: pd.DataFrame, label: str) -> Dict[str, object]:
    cand = f"{VALUE_COL}_pct"
    res: Dict[str, object] = {"label": label, "bases": {}}
    verdicts = []
    for basis in BASES:
        cols = list(II.basis_for(basis))
        ed = II.effective_dates(built, cand, cols, min_names=MIN_NAMES)
        if len(ed) < 2 * MIN_DATES:
            res["bases"][basis] = {"VOID": f"only {len(ed)} effective dates"}
            verdicts.append("UNPOWERED")
            continue
        early, late, boundary = halves(list(ed), min_dates=MIN_DATES)
        full = arm_ic(built, cand, ed, incumbents=cols)
        e = arm_ic(built, cand, early, incumbents=cols)
        l = arm_ic(built, cand, late, incumbents=cols)
        v = arm_verdict(e["incremental_ic_tstat"], l["incremental_ic_tstat"], cand, bar=BAR,
                        power_ok=True,
                        degenerate_early=bool(e["incremental_degenerate"]),
                        degenerate_late=bool(l["incremental_degenerate"]))
        # DECLARED SIGN POSITIVE: a negative incremental IC is a CONTRADICTION, never a pass.
        sign_ok = all((x["incremental_median_ic"] is not None
                       and x["incremental_median_ic"] > 0) for x in (full, e, l))
        verdict = v.get("verdict")
        if verdict == "ELIGIBLE" and not sign_ok:
            verdict = "CONTRADICTION"
        verdicts.append(verdict)
        res["bases"][basis] = {
            "incumbents": cols, "n_effective_dates": len(ed),
            "boundary_embargoed": str(boundary)[:10],
            "full": full, "early_half": e, "late_half": l,
            "shipped_arm_verdict": v, "declared_sign_respected": bool(sign_ok),
            "mean_r2_on_incumbents": full.get("mean_r2_on_incumbents"),
            "verdict": verdict}
        _log(f"[{label}/{basis}] incremental t: full {full['incremental_ic_tstat']} "
             f"early {e['incremental_ic_tstat']} late {l['incremental_ic_tstat']} "
             f"| median inc IC {full['incremental_median_ic']} "
             f"| raw t {full['raw_ic_tstat']} | R2 {full.get('mean_r2_on_incumbents')} "
             f"-> {verdict}")
    if any(v == "CONTRADICTION" for v in verdicts):
        res["verdict"] = "CONTRADICTION"
    elif all(v == "ELIGIBLE" for v in verdicts):
        res["verdict"] = "CONFIRMED"
    elif any(v == "UNPOWERED" for v in verdicts):
        res["verdict"] = "UNPOWERED"
    else:
        res["verdict"] = "NULL"
    res["per_basis_verdicts"] = dict(zip(BASES, verdicts))
    return res


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

    primary = score(build(panel, MIN_HISTORY_YEARS), "primary_observations")
    _log("")
    sens = score(build(panel, SENSITIVITY_YEARS), "sensitivity_calendar")

    final = primary["verdict"]
    if sens["verdict"] != primary["verdict"]:
        final = "UNRESOLVED"

    out = {
        "item": "E-6", "also": "S-SEED-2",
        "register": "PREREG_e6_temporal_axis.md", "register_commit": "0008008",
        "trial_commit": "cfa9722", "domain": "equity", "trials": 1,
        "declaration": ctrl["declaration"],
        "both_census_readings_published_by_I2": I2_PUBLISHED,
        "burn_in_census_gate": ctrl["gates"]["K1_burn_in_census"],
        "primary": primary,
        "calendar_sensitivity": sens,
        "verdict": final,
        "sensitivity_rule": (
            "§4.3. Same hypothesis, same bar, one stated sensitivity on a definitional choice; "
            "NO extra trial, and it can only ever WEAKEN the result. THE ASYMMETRY IS REAL: "
            "under the calendar reading the burn-in census FAILS its own kill (58.886%), so "
            "that arm is UNDERPOWERED BY ITS OWN GATE. A DISAGREEMENT makes the item "
            "UNRESOLVED; an AGREEMENT is NOT evidence the burn-in choice was immaterial."),
        "controls_read_from": CTRL_JSON,
        "may_not_be_quoted_as": [
            "a standardiser swap -- S20/S21 are the graveyard; this adds an AXIS and swaps nothing",
            "a weighting, a sizing rule or any change to the book",
            "an adoption -- an eligible arm is ELIGIBLE, never adopted, and queues behind the "
            "open vintage",
            "evidence about any theme other than `value`",
        ],
    }
    _w(os.path.join(args.out_dir, ARMS_JSON), out)
    _log(f"\n[E-6] VERDICT {final}   primary {primary['verdict']} "
         f"{primary['per_basis_verdicts']} | calendar sensitivity {sens['verdict']} "
         f"{sens['per_basis_verdicts']}")
    _log(f"[E-6] -> {ARMS_JSON}")
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
