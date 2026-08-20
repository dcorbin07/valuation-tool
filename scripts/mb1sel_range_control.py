"""MB1-SEL pass 1 - C-RANGE, the range-restriction control. GATING. ITS OWN PASS.

READ-ONLY. NO ARM IS SCORED HERE and the selection residual is not computed.

WHY ITS OWN PASS. `O10`'s process defect, quoted from its own write-up: *"C2 and the outcome
statistics were computed in the SAME pass, so it cannot be claimed the control was read before the
numbers. A gating control must run and be read in a separate pass."* `scripts/mb1sel_arm.py`
REFUSES without the artifact this writes.

WHAT IT MEASURES. `MB1`'s menu covers 63.20% of alert entries and 62.49% of control entries. The
selection residual is a DIFFERENCE OF DIFFERENCES, so a coverage effect CONSTANT ACROSS THE ARMS
cancels exactly; it is vulnerable only to one that DIFFERS between them. So the statistic is the
differential:

    differential = (covered - uncovered)_alert - (covered - uncovered)_control

**VOID if |differential| > 1.00pp** - the same bar the residual is judged against, because a
confound as large as the effect cannot be ruled out as its cause. The bar is the register's, fixed
before this ran.

    python -m scripts.mb1sel_range_control
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pickle
import sys

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"),
                 os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isfile(os.path.join(cand, "MB1_LEGS.pkl")):
            return os.path.abspath(cand)
    raise SystemExit("REFUSING: MB1_LEGS.pkl not found - MB1's arms pass must have run")


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
LEGS_IN = os.path.join(DATA, "MB1_LEGS.pkl")
OUT = os.path.join(DATA, "free_analysis", "MB1SEL_RANGE_CONTROL.json")

BAR_PP = 1.00                      # the register's, fixed before this ran
N_SEEDS = 5


def _load_book(p):
    with open(p, "rb") as fh:
        d = pickle.load(fh)
    return d["rows"] if isinstance(d, dict) else d


def _shift(covered, uncovered):
    """(mean covered - mean uncovered) in pp, or None when either side is empty."""
    if not covered or not uncovered:
        return None
    return (float(np.mean(covered)) - float(np.mean(uncovered))) * 100.0


def main():
    legs = pickle.load(open(LEGS_IN, "rb"))
    a_legs, c_legs = legs["alert"], legs["control"]

    st = os.stat(LEGS_IN)
    fp = hashlib.sha256(("%d|%d" % (st.st_size, int(st.st_mtime))).encode()).hexdigest()

    a_keys = {(l["ticker"], l["entry"]) for l in a_legs}
    c_keys = {(l["ticker"], l["entry"], l["seed"]) for l in c_legs}

    # ---- alert arm ---------------------------------------------------------------------------
    a_cov, a_unc = [], []
    for r in _load_book(os.path.join(UNIV, "state_r2_splitclean.pkl")):
        v = r.get("pnl_pct")
        if v is None or not np.isfinite(float(v)):
            continue
        key = (r["ticker"], str(r["alert_ts"])[:10])
        (a_cov if key in a_keys else a_unc).append(float(v))

    # ---- control arm ------------------------------------------------------------------------
    c_cov, c_unc = [], []
    for s in range(N_SEEDS):
        for r in _load_book(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s)):
            v = r.get("pnl_pct")
            if v is None or not np.isfinite(float(v)):
                continue
            key = (r["ticker"], str(r["alert_ts"])[:10], s)
            (c_cov if key in c_keys else c_unc).append(float(v))

    a_shift = _shift(a_cov, a_unc)
    c_shift = _shift(c_cov, c_unc)
    differential = (a_shift - c_shift) if (a_shift is not None and c_shift is not None) else None
    passes = differential is not None and abs(differential) <= BAR_PP

    def _sd(x):
        return float(np.std(x, ddof=1)) * 100.0 if len(x) > 1 else None

    payload = {
        "item": "MB1-SEL",
        "pass": "C-RANGE (gating, its own pass)",
        "status": "READ-ONLY - no arm scored, the selection residual is NOT computed here",
        "register": "PREREG_mb1sel_selection_residual.md",
        "legs_artifact": LEGS_IN,
        "legs_fingerprint_sha256": fp,
        "legs_fingerprint_basis": "(size, mtime) of MB1_LEGS.pkl - the menu legs were produced by "
                                  "MB1's arms pass from the PINNED harvest freeze; this item reads "
                                  "those banked legs rather than re-simulating, so there is no "
                                  "re-simulation drift between MB1's decomposition and this one",
        "bar_pp": BAR_PP,
        "alert": {"covered_n": len(a_cov), "uncovered_n": len(a_unc),
                  "covered_mean_pp": float(np.mean(a_cov)) * 100.0 if a_cov else None,
                  "uncovered_mean_pp": float(np.mean(a_unc)) * 100.0 if a_unc else None,
                  "shift_pp": a_shift,
                  "covered_sd_pp": _sd(a_cov), "uncovered_sd_pp": _sd(a_unc)},
        "control": {"covered_n": len(c_cov), "uncovered_n": len(c_unc),
                    "covered_mean_pp": float(np.mean(c_cov)) * 100.0 if c_cov else None,
                    "uncovered_mean_pp": float(np.mean(c_unc)) * 100.0 if c_unc else None,
                    "shift_pp": c_shift,
                    "covered_sd_pp": _sd(c_cov), "uncovered_sd_pp": _sd(c_unc)},
        "differential_pp": differential,
        "c_range_passes": bool(passes),
        "interpretation": "The residual is a difference of differences, so a coverage effect "
                          "CONSTANT across the arms cancels exactly. Only the DIFFERENTIAL can "
                          "confound it, which is why that is the gated statistic and the "
                          "individual shifts are reported rather than gated.",
        "c_disp_note": "Standard deviations are reported so genuine range RESTRICTION - an "
                       "attenuating narrowing of the covered set - is visible rather than assumed "
                       "absent. They carry no verdict.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print("alert   covered %6d mean %+8.4fpp sd %8.2f | uncovered %6d mean %+8.4fpp sd %8.2f"
          % (len(a_cov), payload["alert"]["covered_mean_pp"], payload["alert"]["covered_sd_pp"],
             len(a_unc), payload["alert"]["uncovered_mean_pp"], payload["alert"]["uncovered_sd_pp"]))
    print("control covered %6d mean %+8.4fpp sd %8.2f | uncovered %6d mean %+8.4fpp sd %8.2f"
          % (len(c_cov), payload["control"]["covered_mean_pp"], payload["control"]["covered_sd_pp"],
             len(c_unc), payload["control"]["uncovered_mean_pp"],
             payload["control"]["uncovered_sd_pp"]))
    print()
    print("shift  alert %+8.4fpp   control %+8.4fpp" % (a_shift, c_shift))
    print("DIFFERENTIAL %+8.4fpp against a bar of %.2fpp -> %s"
          % (differential, BAR_PP, "PASSES" if passes else "VOID"))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
