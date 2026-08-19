# -*- coding: utf-8 -*-
"""AUDIT MA38 - measure the OI-coverage defect and the cost of each candidate repair.

    python -m scripts.ma38_coverage [--symbols N] [--seed S]

Writes data/free_analysis/MA38_OI_COVERAGE.json. Read-only over the ThetaData chain cache.

WHAT IS MEASURED, and why each number decides something.

  1. The coverage distribution per front-expiry chain-DAY. The audit's 11.4% is a share of cache
     ROWS, which cannot settle the question: if coverage were all-or-nothing then `coi` would be
     either right or exactly 0, and the shipped `coi > 0` guard would already block the bonus,
     making the defect INERT. It is not all-or-nothing.

  2. How many days cross the 0.5 bonus bar for no reason but the mismatch - the true blast radius.

  3. What each candidate repair COSTS, in legitimate fires killed:
       (a) the audit's "scale coi by 1/known_frac"
       (b) the audit's "suppress when known_frac < 0.9"
       (c) MATCHED: both sums over the same rows - what shipped.

     (c) is the REFERENCE against which (a) and (b) are scored, so "(c) has no collateral" is
     TRUE BY CONSTRUCTION and is not evidence for it. The case for (c) is a priori - it imputes
     nothing and introduces no constant - plus the independent mechanism measurement in 4.

  4. Whether volume is concentrated in the known-OI rows. If it is, (a)'s imputation is not
     neutral: it credits average OI to rows carrying far below-average volume.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pickle
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import theta_bulk as TB   # noqa: E402

BAR = 0.5              # the shipped bonus threshold in intraday/options.py
AUDIT_SUPPRESS = 0.9   # the audit's proposed suppression floor, measured but NOT shipped


def _front_call_day(g, exp_series, asof):
    """calls of the FIRST expiry strictly after `asof`, exactly as chain_summary picks it."""
    ge = exp_series.loc[g.index]
    fut = sorted({e for e in ge if e > asof})
    if not fut:
        return None
    f = g[ge == fut[0]]
    return f[f["right"].astype(str).str.upper().str.startswith("C")]


def measure(root: str, syms: list) -> dict:
    import pandas as pd

    c = collections.Counter()
    cov_hist = collections.Counter()
    excess_share, false_fires, low_cov_fires = [], [], 0

    for s in syms:
        d = os.path.join(root, s)
        if not os.path.isdir(d):
            continue
        for fn in sorted(f for f in os.listdir(d) if f.endswith(".pkl")):
            try:
                with open(os.path.join(d, fn), "rb") as fh:
                    df = pickle.load(fh)
            except Exception:                                   # noqa: BLE001
                c["unreadable_year_files"] += 1
                continue
            if df is None or not len(df) or "open_interest" not in df.columns:
                continue
            df = df[["date", "expiration", "right", "open_interest", "volume"]].copy()
            exp = pd.to_datetime(df["expiration"]).dt.date
            for day, g in df.groupby("date"):
                asof = day if isinstance(day, dt.date) else dt.date.fromisoformat(str(day)[:10])
                calls = _front_call_day(g, exp, asof)
                if calls is None or not len(calls):
                    continue
                oi = pd.to_numeric(calls.get("open_interest"), errors="coerce").where(lambda v: v >= 0)
                vol = pd.to_numeric(calls.get("volume"), errors="coerce").fillna(0)
                known = oi.notna()
                frac, coi = float(known.mean()), float(oi.sum())
                cv_all, cv_known = float(vol.sum()), float(vol[known].sum())

                cov_hist["full" if frac >= 0.999 else ("none" if frac == 0.0 else "partial")] += 1
                if not (coi > 0):
                    c["denominator_zero_already_blocked"] += 1
                    continue
                c["days_scored"] += 1
                shipped = (cv_all / coi) > BAR
                matched = (cv_known / coi) > BAR
                scaled = frac > 0 and (frac * cv_all / coi) > BAR
                suppressed = shipped and frac >= AUDIT_SUPPRESS

                c["fires_shipped"] += bool(shipped)
                c["fires_matched"] += bool(matched)
                c["fires_scaled_a"] += bool(scaled)
                c["fires_suppress_b"] += bool(suppressed)
                if shipped and not matched:
                    c["true_defect_days"] += 1
                    if len(false_fires) < 25:
                        false_fires.append({"symbol": s, "date": str(asof), "coverage": round(frac, 4),
                                            "shipped_ratio": round(cv_all / coi, 4),
                                            "matched_ratio": round(cv_known / coi, 4)})
                if matched and not shipped:
                    c["reverse_days"] += 1
                if matched and not scaled:
                    c["a_kills_matched_legitimate"] += 1
                if matched and not suppressed:
                    c["b_kills_matched_legitimate"] += 1
                if matched and frac < 0.10:
                    low_cov_fires += 1
                if 0 < frac < 1 and cv_all > 0:
                    excess_share.append(cv_known / cv_all - frac)

    excess_share.sort()
    n = c["days_scored"] or 1
    return {
        "symbols": sorted(syms), "days_scored": c["days_scored"],
        "coverage_per_chain_day": {k: cov_hist[k] for k in ("full", "partial", "none")},
        "coverage_partial_pct": round(100.0 * cov_hist["partial"] / max(sum(cov_hist.values()), 1), 4),
        "denominator_zero_already_blocked": c["denominator_zero_already_blocked"],
        "fires": {"shipped": c["fires_shipped"], "matched_c": c["fires_matched"],
                  "scaled_a": c["fires_scaled_a"], "suppress_b": c["fires_suppress_b"]},
        "true_defect_days": c["true_defect_days"],
        "true_defect_pct": round(100.0 * c["true_defect_days"] / n, 4),
        "reverse_days": c["reverse_days"],
        "collateral_legitimate_fires_killed": {
            "a_scale_by_inverse_coverage": c["a_kills_matched_legitimate"],
            "b_suppress_below_0_90": c["b_kills_matched_legitimate"],
            "c_matched": 0,
            "NOTE": "(c) is the reference these are scored against, so its 0 is true by "
                    "construction and is NOT evidence for it. See the module docstring.",
        },
        "ratio_of_cure_to_disease": {
            "a": round(c["a_kills_matched_legitimate"] / max(c["true_defect_days"], 1), 1),
            "b": round(c["b_kills_matched_legitimate"] / max(c["true_defect_days"], 1), 1),
        },
        "volume_concentration_in_known_oi_rows": {
            "median_excess_share": round(excess_share[len(excess_share) // 2], 4) if excess_share else None,
            "n": len(excess_share),
            "reading": "share of VOLUME on known-OI rows minus share of ROWS; positive means "
                       "volume is concentrated there, which is why (a) over-corrects",
        },
        "disclosure_matched_fires_on_under_10pct_coverage": low_cov_fires,
        "sample_true_defect_days": false_fires,
        "bar": BAR, "audit_suppression_floor_measured_not_shipped": AUDIT_SUPPRESS,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1729)
    a = ap.parse_args()

    root = TB.CACHE_ROOT
    if not os.path.isdir(root):
        print("chain cache not found at %s" % root)
        return 2
    random.seed(a.seed)
    pool = [s for s in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, s))]
    syms = random.sample(pool, min(a.symbols, len(pool)))
    if "AAPL" in pool and "AAPL" not in syms:
        syms.append("AAPL")                       # the audit names AAPL 2020 explicitly

    out = measure(root, syms)
    out["seed"], out["cache_root"] = a.seed, root
    dest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "free_analysis", "MA38_OI_COVERAGE.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "sample_true_defect_days"}, indent=2))
    print("\nwrote %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
