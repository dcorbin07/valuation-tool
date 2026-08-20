"""MB16 pass 2 - THE ARM. Scores quote-classified VPIN against the alert book's returns.

Refuses to run without a PASSING kill artifact, so the arm cannot be scored before the item's
pre-scoring gate has been computed AND read - session 26's defect, where a gating control and the
outcomes it gates ran in one pass, repaired rather than repeated.

The scoring arithmetic is `O14.score_arm`, IMPORTED VERBATIM: the identical monthly-quintile
long-short with a month-block t and a within-month permutation null that O3, O4, O5 and O14 were
judged by. Re-implementing it would decouple this verdict from the bars calibrated on it.

    python -m scripts.mb16_arm
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

import scripts.o14_tickflow_signals as O14
from scripts.mb16_vpin import DATA, KILL_BAR, N_BUCKETS, SENSITIVITY_BUCKETS

UNITS = os.path.join(DATA, "free_analysis", "MB16_VPIN_UNITS.pkl")
KILL = os.path.join(DATA, "free_analysis", "MB16_KILL.json")
O14_FEATURES = os.path.join(DATA, "free_analysis", "O14_FEATURES.pkl")
OUT = os.path.join(DATA, "free_analysis", "MB16_ARM.json")

MIN_MONTHS = 40          # O14's void condition 1, inherited
MIN_TRADES = 2500


def _gate():
    """Refuse without a kill artifact that RAN and did NOT fire."""
    if not os.path.exists(KILL):
        raise SystemExit("REFUSING: no kill artifact at %s - run scripts.mb16_vpin first" % KILL)
    k = json.load(io.open(KILL, encoding="utf-8"))
    if k.get("kill_fires"):
        raise SystemExit("REFUSING: the item's pre-scoring kill FIRED (%.4f > %.2f). The arm is "
                         "withdrawn before any outcome is read."
                         % (k["registered_kill_statistic"], KILL_BAR))
    ctrl = k.get("gating_control") or {}
    if not ctrl.get("rate_reproduces") or not ctrl.get("signed_volume_reproduces_exactly"):
        raise SystemExit("REFUSING: the instrument control did not reproduce O14 exactly - VPIN "
                         "is not built on O14's instrument and no comparison means anything.")
    return k


def main():
    kill = _gate()
    print("gate: kill statistic %.4f vs %.2f - did not fire; instrument control exact"
          % (kill["registered_kill_statistic"], KILL_BAR))

    units = pickle.load(open(UNITS, "rb"))["units"]
    feats = {(r["ticker"], r["date"]): r for r in pickle.load(open(O14_FEATURES, "rb"))["recs"]}

    recs = []
    for u in units:
        f = feats.get((u["ticker"], u["date"]))
        if f is None:
            continue
        r = {"month": u["month"], "pnl_pct": f.get("pnl_pct"), "vpin": u["vpin"],
             "sweep_share": f.get("sweep_share"), "signed_volume": f.get("signed_volume")}
        for nb in SENSITIVITY_BUCKETS:
            r["vpin_n%d" % nb] = u.get("vpin_n%d" % nb)
        recs.append(r)

    arm = O14.score_arm(recs, "vpin")

    # ---- the pre-committed bar: full-sample AND both halves AND sign agreement ---------------
    def _clears(d):
        if not d or d.get("abs_t") is None or d.get("null_p95_abs_t") is None:
            return None
        return bool(d["abs_t"] > d["null_p95_abs_t"])

    full_ok = _clears(arm)
    halves = arm.get("halves") or {}
    early, late = halves.get("early"), halves.get("late")
    early_ok, late_ok = _clears(early), _clears(late)
    signs = [np.sign(d["t"]) for d in (early, late) if d and d.get("t") is not None]
    sign_agree = bool(len(signs) == 2 and signs[0] == signs[1])

    underpowered = (arm.get("n_months") or 0) < MIN_MONTHS or (arm.get("n") or 0) < MIN_TRADES
    passes = bool(full_ok and early_ok and late_ok and sign_agree)
    verdict = ("UNDERPOWERED" if underpowered else
               ("CANDIDATE" if passes else "NULL"))

    # ---- diagnostics, no verdict --------------------------------------------------------------
    df = pd.DataFrame(recs)
    sens = {}
    for nb in SENSITIVITY_BUCKETS:
        col = "vpin_n%d" % nb
        m = np.isfinite(df["vpin"]) & np.isfinite(df[col])
        sens["rho_vs_primary_n%d" % nb] = float(
            df.loc[m, "vpin"].rank().corr(df.loc[m, col].rank()))
    m = np.isfinite(df["vpin"]) & np.isfinite(df["sweep_share"])
    rho_sweep = float(df.loc[m, "vpin"].rank().corr(df.loc[m, "sweep_share"].rank()))

    # ---- the design's own RESOLUTION. A null is not a zero, and the register requires this ----
    # V6 and S19's lesson: NULL means "could not be separated from zero at this resolution",
    # never "absent" - so the minimum detectable effect travels with the verdict or the verdict
    # is not quotable. Derived from the arm's OWN standard error and its OWN calibrated bar,
    # never from a convention.
    se = None
    if arm.get("t") not in (None, 0) and arm.get("ls_mean") is not None:
        se = abs(float(arm["ls_mean"]) / float(arm["t"]))
    resolution = {
        "implied_se": se,
        "mde_at_own_p95_bar": (se * float(arm["null_p95_abs_t"])
                               if se and arm.get("null_p95_abs_t") else None),
        "mde_at_conventional_t2": (2.0 * se) if se else None,
        "observed_ls_mean": arm.get("ls_mean"),
        "observed_reaches_its_own_mde": (
            bool(abs(float(arm["ls_mean"])) >= se * float(arm["null_p95_abs_t"]))
            if se and arm.get("null_p95_abs_t") else None),
        "note": "A NULL here means the effect could not be separated from zero at this "
                "resolution on alert days - never that it is absent. Quote the MDE with the "
                "verdict or do not quote the verdict.",
    }

    payload = {
        "item": "MB16",
        "pass": "arm",
        "conditioning": "ALERT DAYS ONLY - the tick cache is exactly the alert days, so every "
                        "figure is conditioned on them and none generalises to the tape.",
        "vpin_version": "QUOTE-CLASSIFIED (Lee-Ready). The Bulk Volume classifier "
                        "Andersen-Bondarenko dispute is NOT built.",
        "n_buckets": N_BUCKETS,
        "scoring": "O14.score_arm imported verbatim - the same monthly-quintile long-short, "
                   "month-block t and within-month permutation null O3/O4/O5/O14 were judged by",
        "two_sided": "no sign is declarable - VPIN is unsigned by construction and EL O'H's claim "
                     "is about volatility, not direction",
        "kill_statistic": kill["registered_kill_statistic"],
        "arm": arm,
        "bar": {"full_clears_own_p95": full_ok,
                "early_clears_own_p95": early_ok,
                "late_clears_own_p95": late_ok,
                "halves_agree_in_sign": sign_agree,
                "all_three_required": True},
        "verdict": verdict,
        "diagnostics_no_verdict": {
            "vpin_p05": float(np.nanpercentile(df["vpin"], 5)),
            "vpin_median": float(np.nanmedian(df["vpin"])),
            "vpin_p95": float(np.nanpercentile(df["vpin"], 95)),
            "sensitivity_rank_corr_vs_primary": sens,
            "rho_vs_sweep_share": rho_sweep,
        },
        "resolution": resolution,
        "framing": "R2 STANDS. A CANDIDATE here is a candidate for a FUTURE book that does not "
                   "exist - never evidence the alert entry works, never an adoption. O11 binds.",
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print()
    print("n %s over %s months, split %s" % (arm.get("n"), arm.get("n_months"),
                                             arm.get("split_month")))
    print("quintile means:", ["%+.4f" % q for q in (arm.get("quintile_means") or [])])
    print("long-short mean %+.4f   t %+.4f   |t| %.4f   own null p95 %.4f"
          % (arm.get("ls_mean") or float("nan"), arm.get("t") or float("nan"),
             arm.get("abs_t") or float("nan"), arm.get("null_p95_abs_t") or float("nan")))
    for nm, d in (("early", early), ("late", late)):
        if d:
            print("  %-5s n %-5s months %-4s ls %+.4f  t %+.4f  own p95 %.4f  clears %s"
                  % (nm, d["n"], d["n_months"], d["ls_mean"], d["t"], d["null_p95_abs_t"],
                     _clears(d)))
    print("  halves agree in sign:", sign_agree)
    print()
    print("VERDICT:", verdict)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
