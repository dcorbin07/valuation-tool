"""I-1 census - run the RND builder over the PINNED freeze and print what it can and cannot do.

    python -m scripts.i1_rnd_census [--symbols 60] [--dates 3] [--out data/free_analysis/...]

WHY A CENSUS AND NOT A DEMO. `PREREG_DRAFT_o1_flagged_puts.md` gates its whole family on K1 -
"RND integrates to 1 +/- 0.02; CDF monotone; parity forward reproduces the as-traded spot within
its quoted-spread band on >=95% of used chains" - and then says "chains failing K1 are excluded
and counted". This is the counting. It prints per-slice fit diagnostics rather than asserting
convergence, which is the difference between an instrument and a claim.

IT COMPUTES NO RELATIONSHIP TO ANY FORWARD RETURN, by construction and by test. Every number
below is a statement about option PRICES on the day they were quoted.

SOURCE: the pinned harvest freeze by default, because it holds a FULL chain on every session
while `data/options` holds one only on entry dates. `--store` switches to the options freeze.
The mutable store is unreachable from here - `chain_store` RAISES rather than falling back.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import chain_store  # noqa: E402
from valuation.studies import rnd  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PRIMARY = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data")


def _data(*parts) -> str:
    """Repo-anchored, falling back to the primary checkout. EXISTENCE IS NOT POPULATION.

    The worktree carries an EMPTY `data/bulk/prepared/bars` while the primary checkout holds
    hundreds of files, so a plain `os.path.exists` picks the empty one and every spot lookup
    silently returns nothing - measured, not hypothetical (`deepitm_financing` shipped it once).
    """
    p = os.path.join(_REPO, "data", *parts)
    if os.path.isdir(p):
        if os.listdir(p):
            return p
    elif os.path.exists(p):
        return p
    return os.path.join(_PRIMARY, *parts)


def raw_close_series(bars_dir: str, sym: str):
    """`raw_close`, never `close`. Strikes are as-traded (`U1-SPLIT`)."""
    p = os.path.join(bars_dir, "%s.pkl" % sym)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as fh:
            d = pickle.load(fh)
    except (OSError, pickle.UnpicklingError):
        return None
    if not isinstance(d, dict) or "raw_close" not in d or "date" not in d:
        return None
    return pd.Series(np.asarray(d["raw_close"], dtype=float),
                     index=pd.to_datetime(d["date"])).sort_index()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=int, default=60)
    ap.add_argument("--dates", type=int, default=3, help="sample dates per symbol-year file")
    ap.add_argument("--rate", type=float, default=0.02)
    ap.add_argument("--store", choices=("harvest", "options"), default="harvest")
    ap.add_argument("--out", default=os.path.join("data", "free_analysis", "I1_RND_CENSUS.json"))
    a = ap.parse_args(argv)

    if a.store == "harvest":
        chains_dir, prov = chain_store.resolve_harvest()
    else:
        chains_dir, prov = chain_store.resolve_chains(_data())
    print("SOURCE %s pinned=%s  %s" % (prov["source"], prov["pinned"], prov["path"]))
    print("  manifest_sha256 %s  payload_units %s"
          % (str(prov.get("manifest_sha256"))[:16], prov.get("payload_units")))
    assert prov["pinned"], "the census may only run against a PINNED freeze"

    bars = _data("bulk", "prepared", "bars")
    slices = []
    used_syms = []
    for sym in sorted(os.listdir(chains_dir)):
        if len(used_syms) >= a.symbols:
            break
        sd = os.path.join(chains_dir, sym)
        if not os.path.isdir(sd):
            continue
        files = [f for f in sorted(os.listdir(sd)) if f.endswith(".pkl")]
        rc = raw_close_series(bars, sym)
        if not files or rc is None or rc.empty:
            continue
        try:
            with open(os.path.join(sd, files[-1]), "rb") as fh:
                obj = pickle.load(fh)
        except (OSError, pickle.UnpicklingError):
            continue
        df = obj.get("rows") if isinstance(obj, dict) else None
        if df is None or not len(df):
            continue
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["expiration"] = pd.to_datetime(df["expiration"])
        days = sorted(df["date"].unique())
        if not days:
            continue
        picks = [days[int((i + 1) * len(days) / (a.dates + 1))] for i in range(a.dates)]
        for d in picks:
            if d not in rc.index:
                continue
            spot = float(rc.loc[d])
            if not (math.isfinite(spot) and spot > 0):
                continue
            slices.extend(rnd.build_name_day(df, spot=spot, asof=d, symbol=sym, r=a.rate))
        used_syms.append(sym)

    cen = rnd.coverage_census(slices)
    usable = [s for s in slices if s.usable]
    in_band = [s for s in slices if s.reasons != ("dte_out_of_band",)]
    print("\nsymbols %d   slices %d   in DTE band %d   usable %d (%.1f%% of in-band)"
          % (len(used_syms), len(slices), len(in_band), len(usable),
             100.0 * len(usable) / max(1, len(in_band))))
    print("refusals:", cen["refusal_reasons"])

    def q(key, vals):
        v = np.asarray(vals, dtype=float)
        if not v.size:
            return None
        return {"median": float(np.median(v)), "p05": float(np.percentile(v, 5)),
                "p95": float(np.percentile(v, 95)), "max": float(v.max())}

    diag = {k: q(k, [s.diagnostics[k] for s in usable if k in s.diagnostics])
            for k in ("integral", "negative_mass", "cdf_route_max_gap", "atm_vol")}
    parity_all = [abs(s.diagnostics["parity_spot_dev_frac"]) for s in slices
                  if "parity_spot_dev_frac" in s.diagnostics]
    within = [bool(s.diagnostics["parity_within_band"]) for s in slices
              if "parity_within_band" in s.diagnostics]
    k1_parity = float(np.mean(within)) if within else None
    print("\nfit diagnostics over usable slices:")
    for k, v in diag.items():
        if v:
            print("  %-20s med %.6g  p05 %.6g  p95 %.6g  max %.6g"
                  % (k, v["median"], v["p05"], v["p95"], v["max"]))
    print("  %-20s med %.6g  p95 %.6g" % ("|parity_dev_frac|", float(np.median(parity_all)),
                                          float(np.percentile(parity_all, 95))))
    print("\nK1 parity-vs-raw_close within band: %.4f  (register wants >= 0.95) -> %s"
          % (k1_parity, "PASS" if (k1_parity or 0) >= 0.95 else "FAIL"))
    print("\nEXTRAPOLATED SHARE BY THRESHOLD - read this before quoting a tail mass:")
    for k, v in sorted(cen["extrapolated_share_by_threshold"].items()):
        print("  %-6s %s" % (k, "n/a" if v is None else "%.4f" % v))

    payload = {
        "instrument": "I-1",
        "method": rnd.METHOD,
        "citations": list(rnd.CITATIONS),
        "provenance": prov,
        "n_symbols": len(used_syms),
        "census": cen,
        "n_in_dte_band": len(in_band),
        "usable_share_of_in_band": len(usable) / max(1, len(in_band)),
        "fit_diagnostics": diag,
        "k1_parity_within_band_share": k1_parity,
        "thresholds": list(rnd.TAIL_THRESHOLDS),
        "gates": {"integral_tol": rnd.INTEGRAL_TOL, "max_neg_mass": rnd.MAX_NEG_MASS,
                  "min_smile_points": rnd.MIN_SMILE_POINTS,
                  "dte_band": [rnd.MIN_DTE_DAYS, rnd.MAX_DTE_DAYS]},
        "note": ("prices only. This instrument computes no relationship between any RND "
                 "quantity and any forward return; that is pinned by tests/test_rnd.py."),
    }
    out = a.out if os.path.isabs(a.out) else os.path.join(_REPO, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print("\nwrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
