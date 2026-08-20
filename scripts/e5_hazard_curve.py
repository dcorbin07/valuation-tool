"""E-5 / INV-A -- the hazard curve of flagged names. `PREREG_e5_hazard_curve.md`.

Register committed ALONE and BLIND at `dd6fe93`, markdown only, 308 lines, a strict git
ancestor of this file. The single EQUITY trial was booked at `5696055`, before this file
existed: equity 236 -> 237.

**THE VERDICT OBJECT IS A CRASH RATE, NEVER ALPHA.** `quantile_backtest` is not called and no
return-based statistic is computed anywhere in this file; an AST test pins that, because the
docstring saying so is not the same as the tree doing so (`MA49`'s defect).

Run:
    python -m scripts.e5_hazard_curve --controls     # K1..K3 + the census, no arm scored
    python -m scripts.e5_hazard_curve --arms         # REFUSES without a passing controls file

TWO PASSES, and the separation is the point: computing a gating control and the outcomes it
gates in one pass is session 26's process defect and `O10`'s, and `--arms` exits non-zero
rather than proceeding when the controls artifact is missing or failing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from valuation.studies import crash_gate as CG                      # noqa: E402
from valuation.studies import hazard_curve as HC                    # noqa: E402
from valuation.edge import power_gate as PG                         # noqa: E402
from valuation.edge.research_log import trial_count                 # noqa: E402
from s10_accounting_veto import build_flags                         # noqa: E402  ONE definition

# ---------------------------------------------------------------------------------------
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item
# (§9.2). The crash level, the quarter length and the two per-date floors are MA28's own,
# reused VERBATIM rather than re-picked with MA28's results already published -- MB1SEL's
# discipline, and the reason none of them is a new degree of freedom.
# ---------------------------------------------------------------------------------------
CRASH = -0.50                    # §2, MA28's registered threshold
QUARTER_TD = 63                  # §2, the panel's own forward window
K_MAX = 4                        # §2, the proposal's horizon
MIN_FLAGGED_PER_DATE = 30        # §4 K1, MA28's floor
MIN_KEPT_PER_DATE = 100          # §4 K1, MA28's floor
RATIO_FLOOR_Q1 = 2.0             # §5 L1, MA28's B2 floor
FRONT_SHARE_FLOOR = 0.60         # §5 L3, the proposal's own bar
FRONT = (1, 2)                   # §5 L2/L3
BACK = (3, 4)                    # §5 L2
N_PERM = 500                     # §5 L2
PERM_SEED = 20260820
MIN_EVENTS = 10                  # §2, the floor below which quotable() withholds a ratio

# K1 -- coverage floors, §4
K1_MIN_OBSERVABLE_SHARE = 0.70
K1_MIN_QUALIFYING_DATES = 55
# K2 -- required-n, §4/§7
K2_TARGET_RATIO = 2.0
K2_POWER = 0.80
# K3 -- the instrument gate, §4. MA28's PUBLISHED figures (CLAUDE.md), not a JSON on disk.
K3_MIN_AGREEMENT = 0.99
MA28_RATE_FLAGGED = 0.026597
MA28_RATE_KEPT = 0.008743
MA28_RATIO = 3.0422
K3_RATE_TOL_PP = 0.02
K3_RATIO_TOL = 0.05
# REPORTED, NEVER GATING. `tests/test_i3_crash_gate.py` carries MA28's three window ratios at
# full precision, read from the artifact when it still existed. They are a tighter reference
# than CLAUDE.md's rounded 3.0422 -- but the register fixed the tolerance against the ROUNDED
# figures before anything ran, and tightening a registered bar after the fact is a change to a
# bar, however favourable its direction. So the full-precision deltas ship as a diagnostic
# beside the gate and decide nothing.
MA28_RATIO_FULL = {"full_sample": 3.0422123745999063,
                   "early_half": 3.4208900608295076,
                   "late_half": 2.9321220447443164}
MA28_N_FLAGGED_FULL = 6542
# C6 -- the null must have compared something, §8
C6_MIN_DISTINCT_DRAWS = 100
C6_MAX_UNDEFINED_SHARE = 0.05

PANEL = os.path.join("data", "free_analysis", "panel_r5r6.pkl")
# Artifact names are fixed; WHERE they land is a --out-dir argument. RUN_RULES rule 9 is why:
# this lane runs in a git worktree whose data/ is deleted with it, so the banked draws must be
# writable to the primary data root rather than to a directory that disappears.
CTRL_JSON = "E5_CONTROLS.json"
ARMS_JSON = "E5_HAZARD_CURVE.json"
FLAG_CACHE = "E5_FLAGS.pkl"
FWD_CACHE = "E5_FORWARD.pkl"
DEFAULT_OUT = os.path.join(REPO, "data", "free_analysis")

DISTRESS_ACTIONS = ("bankruptcyliquidation", "regulatorydelisting")   # V6-B's definitions


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------------------
def load_panel(panel_path: str) -> pd.DataFrame:
    with open(panel_path, "rb") as f:
        return pickle.load(f)


def attach_flags(panel: pd.DataFrame, data_dir: str, cache: str) -> pd.DataFrame:
    """MA28's own `attach_flags`, with the flag frame cached so the two passes agree by
    construction rather than by running the same 157 MB scan twice and hoping."""
    if os.path.exists(cache):
        with open(cache, "rb") as f:
            flags = pickle.load(f)
        _log(f"[flags] cache hit {cache} ({len(flags)} rows)")
    else:
        dates = sorted(panel["date"].unique())
        tickers = sorted(panel["ticker"].unique())
        _log(f"[flags] building over {len(tickers)} tickers x {len(dates)} dates ...")
        flags = build_flags(data_dir, tickers, dates)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump(flags, f)
    p = panel.merge(flags, on=["date", "ticker"], how="left")
    p["flagged"] = p["vetoed"].fillna(False).astype(bool)
    return p


def attach_forward(p: pd.DataFrame, price_dir: str, cache: str) -> pd.DataFrame:
    if os.path.exists(cache):
        with open(cache, "rb") as f:
            fw = pickle.load(f)
        _log(f"[fwd] cache hit {cache} ({len(fw)} rows)")
    else:
        dates = sorted(p["date"].unique())
        tickers = sorted(p["ticker"].unique())
        _log(f"[fwd] building forward quarters over {len(tickers)} tickers ...")
        fw = HC.forward_quarters(price_dir, tickers, dates,
                                 quarter_td=QUARTER_TD, k_max=K_MAX)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump(fw, f)
    q = p.copy()
    q["date"] = q["date"].astype(str).str[:10]
    fw = fw.copy()
    fw["date"] = fw["date"].astype(str).str[:10]
    m = q.merge(fw, on=["date", "ticker"], how="inner")
    # K3's repair, found pre-arm: a DELISTED name has a terminal value, not a short window.
    # The panel's own fwd_ret does exactly this and the two agree at max |delta| 0.000e+00.
    glast = str(fw["last_price_date"].astype(str).max())
    m = HC.apply_terminal_value(m, quarter_td=QUARTER_TD, k_max=K_MAX,
                                global_last_price_date=glast)
    return HC.event_and_observable(m, crash=CRASH, k_max=K_MAX)


# ---------------------------------------------------------------------------------------
# CONTROLS PASS
# ---------------------------------------------------------------------------------------
def run_controls(args) -> int:
    panel = load_panel(args.panel)
    _log(f"[panel] {len(panel)} rows, {panel['date'].nunique()} dates, "
         f"{panel['ticker'].nunique()} names")
    p = attach_flags(panel, args.data_dir, os.path.join(args.out_dir, FLAG_CACHE))
    m = attach_forward(p, os.path.join(args.data_dir, "prices"),
                       os.path.join(args.out_dir, FWD_CACHE))
    _log(f"[join] {len(m)} rows carry a price anchor "
         f"({len(m) / len(p):.4f} of panel rows)")

    out: Dict[str, object] = {
        "item": "E-5", "also": "INV-A",
        "register": "PREREG_e5_hazard_curve.md", "register_commit": "dd6fe93",
        "trial_commit": "5696055", "domain": "equity",
        "gate": "CRASH RATES AND RATIOS via I-3, NEVER ALPHA",
        "constants": {"crash": CRASH, "quarter_td": QUARTER_TD, "k_max": K_MAX,
                      "min_flagged_per_date": MIN_FLAGGED_PER_DATE,
                      "min_kept_per_date": MIN_KEPT_PER_DATE,
                      "ratio_floor_q1": RATIO_FLOOR_Q1,
                      "front_share_floor": FRONT_SHARE_FLOOR,
                      "n_perm": N_PERM, "perm_seed": PERM_SEED,
                      "min_events": MIN_EVENTS},
        "panel_rows": int(len(p)), "joined_rows": int(len(m)),
        "n_dates": int(m["date"].nunique()), "n_names": int(m["ticker"].nunique()),
        "gates": {}, "census": {},
    }

    # ---- K1 coverage (pre-outcome: observability, which bounds the risk set from above) ----
    f = m["flagged"].to_numpy(dtype=bool)
    obsv = m["obs"].to_numpy(dtype=int)
    obs_k4 = obsv >= K_MAX
    share = float((obs_k4 & f).sum()) / float(f.sum()) if f.sum() else 0.0
    per_date = []
    for d, g in m.groupby("date", sort=True):
        gf = g["flagged"].to_numpy(dtype=bool)
        go = g["obs"].to_numpy(dtype=int) >= K_MAX
        per_date.append({"date": str(d)[:10],
                         "flagged_observable_k4": int((go & gf).sum()),
                         "kept_observable_k4": int((go & ~gf).sum())})
    qual = sum(1 for r in per_date
               if r["flagged_observable_k4"] >= MIN_FLAGGED_PER_DATE
               and r["kept_observable_k4"] >= MIN_KEPT_PER_DATE)
    k1_ok = bool(share >= K1_MIN_OBSERVABLE_SHARE and qual >= K1_MIN_QUALIFYING_DATES)
    out["gates"]["K1_coverage"] = {
        "flagged_rows": int(f.sum()),
        "flagged_share_of_joined": float(f.mean()),
        "flagged_observable_at_k4_share": share,
        "floor": K1_MIN_OBSERVABLE_SHARE,
        "qualifying_dates_at_k4": int(qual), "dates_floor": K1_MIN_QUALIFYING_DATES,
        "n_dates": len(per_date), "per_date": per_date, "ok": k1_ok,
        "note": ("observability, not at-risk: who is at risk at k depends on who crashed "
                 "earlier, which is an OUTCOME. Observability bounds it from above and is "
                 "computable before any hazard is read."),
    }
    _log(f"[K1] flagged observable at k=4: {share:.4f} (floor {K1_MIN_OBSERVABLE_SHARE}); "
         f"qualifying dates {qual}/{len(per_date)} (floor {K1_MIN_QUALIFYING_DATES}) -> {k1_ok}")

    # ---- K2 required-n, rule 11, BEFORE the arm ----
    n_equity = trial_count(domain="equity")
    req = CG.required_rows(MA28_RATE_KEPT, K2_TARGET_RATIO, float(f.mean()),
                           n_trials=n_equity, power=K2_POWER)
    observable_rows = int(obs_k4.sum())
    k2_ok = bool(req["required_rows_total"] <= observable_rows)
    out["gates"]["K2_required_n"] = {
        "equity_N": int(n_equity), "crit": req["crit"], "power": K2_POWER,
        "target_ratio": K2_TARGET_RATIO, "base_rate_used": MA28_RATE_KEPT,
        "required_rows_total": req["required_rows_total"],
        "required_rows_flagged": req["required_rows_flagged"],
        "required_rows_equal_allocation_for_contrast":
            req["required_rows_equal_allocation_for_contrast"],
        "allocation_penalty_x": req["allocation_penalty_x"],
        "expected_crashes_flagged": req["expected_crashes_flagged"],
        "normal_approximation_thin": req["normal_approximation_thin"],
        "observable_rows_at_k4": observable_rows, "ok": k2_ok,
        "vocabulary": ("this is the 80%-POWER required n. MB22 established that the project's "
                       "historical MDEs were crit x se, a 50%-power detection threshold; both "
                       "are reported and each is labelled."),
    }
    _log(f"[K2] required rows {req['required_rows_total']} at ratio {K2_TARGET_RATIO}, "
         f"power {K2_POWER}, crit {req['crit']:.4f} vs {observable_rows} observable -> {k2_ok}")

    # ---- K3 the instrument gate ----
    both = m["fwd_ret"].notna() & m["r_1"].notna()
    a = (pd.to_numeric(m.loc[both, "fwd_ret"], errors="coerce") <= CRASH).to_numpy(dtype=bool)
    b = (pd.to_numeric(m.loc[both, "r_1"], errors="coerce") <= CRASH).to_numpy(dtype=bool)
    agree = float((a == b).mean()) if len(a) else 0.0

    q1 = m.copy()
    q1["_crash"] = q1["r_1"].astype(float) <= CRASH
    w = CG.window_result(q1[q1["r_1"].notna()], "ma28_quarter1_reproduction",
                         crash_col="_crash", ratio_floor=RATIO_FLOOR_Q1, abs_floor_pp=0.50,
                         n_perm=1, perm_seed=PERM_SEED,
                         min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                         min_kept_per_date=MIN_KEPT_PER_DATE)
    po = w.get("pooled", {})
    d_flag = abs(float(po.get("rate_flagged") or 0.0) - MA28_RATE_FLAGGED) * 100.0
    d_kept = abs(float(po.get("rate_kept") or 0.0) - MA28_RATE_KEPT) * 100.0
    d_ratio = abs(float(po.get("ratio") or 0.0) - MA28_RATIO)
    k3_ok = bool(agree >= K3_MIN_AGREEMENT and d_flag <= K3_RATE_TOL_PP
                 and d_kept <= K3_RATE_TOL_PP and d_ratio <= K3_RATIO_TOL)
    out["gates"]["K3_instrument"] = {
        "rows_with_both": int(both.sum()),
        "crash_indicator_agreement": agree, "agreement_floor": K3_MIN_AGREEMENT,
        "reproduced_pooled": po,
        "published_MA28": {"rate_flagged": MA28_RATE_FLAGGED, "rate_kept": MA28_RATE_KEPT,
                           "ratio": MA28_RATIO, "source": "CLAUDE.md MA28-CARD bullet"},
        "delta_rate_flagged_pp": d_flag, "delta_rate_kept_pp": d_kept,
        "delta_ratio": d_ratio,
        "tolerances": {"rate_pp": K3_RATE_TOL_PP, "ratio": K3_RATIO_TOL},
        "ok": k3_ok,
        "reported_not_gating": {
            "delta_ratio_vs_full_precision": abs(float(po.get("ratio") or 0.0)
                                                 - MA28_RATIO_FULL["full_sample"]),
            "full_precision_reference": MA28_RATIO_FULL["full_sample"],
            "n_flagged_reproduced": po.get("n_flagged"),
            "n_flagged_published": MA28_N_FLAGGED_FULL,
            "source": "tests/test_i3_crash_gate.py literals, read from MA28_CARD.json when it "
                      "still existed",
            "why_not_gating": "the register fixed its tolerance against the rounded published "
                              "figures before running; tightening a bar afterwards is a change "
                              "to a bar however favourable its direction",
        },
        "note": ("MA28_CARD.json is not on disk on this machine, so the gate RE-DERIVES MA28's "
                 "quarter-1 window from the panel and compares against the figures CLAUDE.md "
                 "publishes. Re-deriving is a stronger gate than re-reading."),
    }
    _log(f"[K3] agreement {agree:.6f}; flagged {po.get('rate_flagged')} vs {MA28_RATE_FLAGGED}, "
         f"kept {po.get('rate_kept')} vs {MA28_RATE_KEPT}, ratio {po.get('ratio')} -> {k3_ok}")

    # ---- census: coverage of the outcome, C3 censoring, C5 persistence, C8 size ----
    out["census"]["outcome_coverage"] = CG.coverage(m["r_1"])
    glast = str(m["last_price_date"].astype(str).max())
    out["census"]["C3_censoring"] = HC.censoring_census(
        m, flag_col="flagged", k_max=K_MAX, global_last_price_date=glast)
    _log(f"[C3] delisting-censor rate ratio flagged/kept: "
         f"{out['census']['C3_censoring']['delisting_censor_rate_ratio']}")
    out["census"]["C5_flag_persistence"] = HC.flag_persistence(
        m, flag_col="flagged", date_col="date", k_max=K_MAX)
    _log(f"[C5] still flagged after 4 quarters: "
         f"{out['census']['C5_flag_persistence']['still_flagged_after_4_quarters']}")

    if "market_cap" in m.columns:
        mc = pd.to_numeric(m["market_cap"], errors="coerce")
        out["census"]["C8_size"] = {
            "median_market_cap_flagged": float(mc[m["flagged"]].median()),
            "median_market_cap_kept": float(mc[~m["flagged"]].median()),
            "note": ("diagnostic, NO verdict. Altman Z contains market cap directly, so the "
                     "flag is mechanically size-linked; MA28's C4 already adjudicated the size "
                     "question for the RATE and re-adjudicating it for the TIMING would be a "
                     "second hypothesis on one trial."),
        }

    out["all_gating_pass"] = bool(k1_ok and k2_ok and k3_ok)
    _w(os.path.join(args.out_dir, CTRL_JSON), out)
    _log(f"[controls] all_gating_pass={out['all_gating_pass']} -> {CTRL_JSON}")
    return 0 if out["all_gating_pass"] else 3


# ---------------------------------------------------------------------------------------
# ARMS PASS
# ---------------------------------------------------------------------------------------
def _cells(frame: pd.DataFrame) -> pd.DataFrame:
    return HC.hazard_cells(frame, flag_col="flagged", date_col="date", k_max=K_MAX,
                           min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                           min_kept_per_date=MIN_KEPT_PER_DATE)


def _window(frame: pd.DataFrame, label: str) -> Dict[str, object]:
    """One window's full record: per-quarter pooled hazards, the ratio path, the decay
    statistic and the excess share. No bar is applied here -- the legs are assembled in
    `run_arms` so every threshold sits in one place."""
    cells = _cells(frame)
    per_q = {}
    for k in range(1, K_MAX + 1):
        po = HC.pooled_hazard(cells, [k])
        per_q[k] = {
            "pooled": po,
            "quotable": CG.quotable(
                {"n_flagged": po["at_risk_flagged"], "n_kept": po["at_risk_kept"],
                 "n_crash_flagged": po["event_flagged"], "n_crash_kept": po["event_kept"],
                 "rate_flagged": po["rate_flagged"], "rate_kept": po["rate_kept"],
                 "ratio": po["ratio"]},
                min_events=MIN_EVENTS),
        }
    return {
        "label": label,
        "qualifying_cells": int(cells["qualifies"].sum()),
        "per_quarter": per_q,
        "front": HC.pooled_hazard(cells, FRONT),
        "back": HC.pooled_hazard(cells, BACK),
        "decay": HC.decay_statistic(cells, front=FRONT, back=BACK),
        "excess": HC.excess_share(cells, front=FRONT, k_max=K_MAX),
        "_cells": cells,
    }


def _distress_dates(actions_csv: str, tickers) -> Dict[str, str]:
    """Earliest DISTRESS delisting per ticker. The acquisition umbrella is deliberately NOT
    included: V6-B measured 82.63% of delistings on this universe to be takeovers, so folding
    them in would turn a distress sensitivity into a merger sensitivity."""
    if not os.path.exists(actions_csv):
        raise SystemExit(f"[E-5] C4 REFUSES: actions file not found at {actions_csv}. An empty "
                         f"distress map would make the sensitivity agree with the primary BY "
                         f"CONSTRUCTION and read as a passing control.")
    a = pd.read_csv(actions_csv, usecols=["date", "action", "ticker"], low_memory=False)
    a = a[a["ticker"].isin(set(tickers)) & a["action"].isin(DISTRESS_ACTIONS)]
    out = {str(t): str(d)[:10] for t, d in a.groupby("ticker")["date"].min().items()}
    if not out:
        raise SystemExit("[E-5] C4 REFUSES: zero distress actions matched. The sensitivity "
                         "cannot bound anything if it moves nothing.")
    return out


def _apply_distress(m: pd.DataFrame, dd: Dict[str, str]) -> pd.DataFrame:
    """C4's sensitivity: distress delisting counts as an EVENT in the quarter it falls in.

    The quarter boundary is the OBSERVED date at that quarter end where the price series
    reaches it, and a calendar fallback of 91.31 days per quarter where it does not -- which is
    exactly the case a distress delisting creates. The approximation is stated rather than
    hidden, and it can only ever move an event between adjacent quarters.
    """
    q = m.copy()
    d0 = pd.to_datetime(q["date"], errors="coerce")
    dist = pd.to_datetime(q["ticker"].map(dd), errors="coerce")
    ev = q["ev"].to_numpy(dtype=int)
    obs = q["obs"].to_numpy(dtype=int)
    new_ev = ev.copy()
    bounds = []
    for k in range(1, K_MAX + 1):
        b = pd.to_datetime(q[f"dt_{k}"], errors="coerce")
        fallback = d0 + pd.to_timedelta(91.31 * k, unit="D")
        bounds.append(b.fillna(fallback))
    has = dist.notna() & (dist > d0)
    kd = np.zeros(len(q), dtype=int)
    for k in range(K_MAX, 0, -1):
        kd = np.where(has & (dist <= bounds[k - 1]), k, kd)
    take = has.to_numpy() & (kd > 0) & ((ev == 0) | (kd < ev))
    new_ev = np.where(take, kd, ev)
    q["ev"] = new_ev
    q["obs"] = np.maximum(obs, np.where(take, kd, 0))
    q["_distress_event_added"] = take
    return q


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

    panel = load_panel(args.panel)
    p = attach_flags(panel, args.data_dir, os.path.join(args.out_dir, FLAG_CACHE))
    m = attach_forward(p, os.path.join(args.data_dir, "prices"),
                       os.path.join(args.out_dir, FWD_CACHE))

    early, late, boundary = CG.halves(m, date_col="date")
    windows = {name: _window(fr, name) for name, fr in
               (("full_sample", m), ("early_half", early), ("late_half", late))}

    # ---- L2's null: the decay statistic under I-3's within-date flag shuffle ----
    def _decay_stat(cells: pd.DataFrame) -> Optional[float]:
        return HC.decay_statistic(cells, front=FRONT, back=BACK)

    _log(f"[L2] permutation null, {N_PERM} draws ...")
    null = HC.permutation_draws(m, flag_col="flagged", date_col="date", k_max=K_MAX,
                                n_draws=N_PERM, seed=PERM_SEED,
                                min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                                min_kept_per_date=MIN_KEPT_PER_DATE,
                                statfn=_decay_stat)
    draws = null.pop("draws", [])
    c6_ok = bool(null.get("n_distinct", 0) >= C6_MIN_DISTINCT_DRAWS
                 and float(null.get("sd") or 0.0) > 0.0
                 and (null.get("n_undefined", 0) / max(1, N_PERM)) <= C6_MAX_UNDEFINED_SHARE)
    _log(f"[C6] null distinct {null.get('n_distinct')} sd {null.get('sd')} "
         f"undefined {null.get('n_undefined')} -> {c6_ok}")

    # ---- the three legs ----
    hr1 = windows["full_sample"]["per_quarter"][1]["pooled"]["ratio"]
    L1 = bool(hr1 is not None and hr1 >= RATIO_FLOOR_Q1)

    decays = {k: v["decay"] for k, v in windows.items()}
    dir_ok = all(v is not None and v > 0 for v in decays.values())
    p95 = null.get("p95")
    L2 = bool(dir_ok and p95 is not None and decays["full_sample"] > p95)

    share = windows["full_sample"]["excess"].get("share")
    L3 = bool(share is not None and share >= FRONT_SHARE_FLOOR)

    reversal = all(v is not None and v < 0 for v in decays.values())

    # ---- C4 sensitivity: distress delisting as an event ----
    dd = _distress_dates(args.actions_csv, set(m["ticker"]))
    ms = _apply_distress(m, dd)
    s_windows = {name: _window(fr, name) for name, fr in
                 (("full_sample", ms),
                  ("early_half", ms[ms["date"].isin(early["date"].unique())]),
                  ("late_half", ms[ms["date"].isin(late["date"].unique())]))}
    s_decays = {k: v["decay"] for k, v in s_windows.items()}
    s_hr1 = s_windows["full_sample"]["per_quarter"][1]["pooled"]["ratio"]
    s_share = s_windows["full_sample"]["excess"].get("share")
    _log(f"[C4] distress events added: {int(ms['_distress_event_added'].sum())}")

    def _verdict(l1, l2, l3, dec, rev) -> str:
        if l1 and l2 and l3:
            return "FRONT-LOADED"
        if l1 and rev:
            return "BACK-LOADED"
        if l1 and not l2 and not l3 and not rev:
            return "FLAT"
        return "UNRESOLVED"

    verdict = _verdict(L1, L2, L3, decays, reversal)

    s_dir = all(v is not None and v > 0 for v in s_decays.values())
    s_L2 = bool(s_dir and p95 is not None and s_decays["full_sample"] > p95)
    s_L1 = bool(s_hr1 is not None and s_hr1 >= RATIO_FLOOR_Q1)
    s_L3 = bool(s_share is not None and s_share >= FRONT_SHARE_FLOOR)
    s_rev = all(v is not None and v < 0 for v in s_decays.values())
    s_verdict = _verdict(s_L1, s_L2, s_L3, s_decays, s_rev)
    if s_verdict != verdict:
        verdict = "UNRESOLVED"

    # ---- MDE, both vocabularies, quoted WITH the verdict (V6 / S19 / MB16's rule) ----
    sd = float(null.get("sd") or 0.0)
    obs_decay = decays["full_sample"]
    mde = {
        "bar_is_the_permutation_p95": p95,
        "null_sd": sd,
        "detection_threshold_50pct_power": p95,
        "mde_at_80pct_power": (None if (p95 is None) else p95 + PG.Z_POWER_CONVENTION * sd),
        "observed_decay": obs_decay,
        "observed_over_80pct_mde": (
            None if (p95 is None or not sd) else obs_decay / (p95 + PG.Z_POWER_CONVENTION * sd)),
        "vocabulary": ("MB22: an effect exactly at the bar is detected HALF the time. The "
                       "80%-power figure adds 0.84 null standard deviations. A NULL here means "
                       "'no decay at least this large', never 'no decay'."),
    }

    out: Dict[str, object] = {
        "item": "E-5", "also": "INV-A",
        "register": "PREREG_e5_hazard_curve.md", "register_commit": "dd6fe93",
        "trial_commit": "5696055", "domain": "equity", "trials": 1,
        "gate": "CRASH RATES AND RATIOS via I-3, NEVER ALPHA",
        "controls_read_from": CTRL_JSON,
        "boundary_date_embargoed": boundary,
        "constants": {"crash": CRASH, "quarter_td": QUARTER_TD, "k_max": K_MAX,
                      "ratio_floor_q1": RATIO_FLOOR_Q1,
                      "front_share_floor": FRONT_SHARE_FLOOR,
                      "front": list(FRONT), "back": list(BACK),
                      "n_perm": N_PERM, "perm_seed": PERM_SEED},
        "windows": {k: {kk: vv for kk, vv in v.items() if kk != "_cells"}
                    for k, v in windows.items()},
        "legs": {
            "L1_hr_q1_ge_2.0x": L1, "hr_q1": hr1,
            "L2_decay_both_halves_and_clears_p95": L2,
            "decay_by_window": decays, "decay_null": null,
            "L3_front_share_ge_0.60": L3, "front_share": share,
        },
        "reversal_all_windows": reversal,
        "verdict": verdict,
        "mde": mde,
        "C4_distress_sensitivity": {
            "distress_events_added": int(ms["_distress_event_added"].sum()),
            "tickers_with_distress_action": len(dd),
            "hr_q1": s_hr1, "decay_by_window": s_decays, "front_share": s_share,
            "legs": {"L1": s_L1, "L2": s_L2, "L3": s_L3}, "verdict": s_verdict,
            "agrees_with_primary": bool(s_verdict == _verdict(L1, L2, L3, decays, reversal)),
            "windows": {k: {kk: vv for kk, vv in v.items() if kk != "_cells"}
                        for k, v in s_windows.items()},
            "note": ("same hypothesis, stated sensitivity, NO extra trial. A disagreement with "
                     "the primary makes the item UNRESOLVED by the register's own rule."),
        },
        "C6_null_non_vacuous": {"ok": c6_ok, **{k: null.get(k) for k in
                                                ("n_distinct", "sd", "n_undefined", "n_draws")}},
        "C3_censoring": ctrl["census"]["C3_censoring"],
        "C5_flag_persistence": ctrl["census"]["C5_flag_persistence"],
        "C8_size": ctrl["census"].get("C8_size"),
        "hazard_rule": HC.HAZARD_RULE,
        "crash_gate_rule": CG.CRASH_GATE_RULE,
        "may_not_be_quoted_as": [
            "a screen, a trade, or a reason to exclude a name (S10)",
            "a BOOK result -- this is the PANEL, and MB8 measured the same flag firing on 3.56% "
            "of the top-decile book and catching one crash of eighty-four",
            "evidence about alpha in any direction",
            "a causal claim",
        ],
    }
    _w(os.path.join(args.out_dir, ARMS_JSON), out)
    _log(f"\n[E-5] VERDICT {verdict}  (L1 {L1}, L2 {L2}, L3 {L3}; sensitivity {s_verdict})")
    _log(f"[E-5] HR by quarter: " + ", ".join(
        f"k{k}={windows['full_sample']['per_quarter'][k]['pooled']['ratio']}"
        for k in range(1, K_MAX + 1)))
    _log(f"[E-5] decay full {decays['full_sample']} vs null p95 {p95}; front share {share}")
    _log(f"[E-5] -> {ARMS_JSON}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(REPO, "data", "backtest"))
    ap.add_argument("--panel", default=os.path.join(REPO, PANEL))
    ap.add_argument("--actions-csv",
                    default=os.path.join(REPO, "data", "bulk", "actions.csv"))
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    if a.arms:
        return run_arms(a)
    return run_controls(a)


if __name__ == "__main__":
    raise SystemExit(main())
