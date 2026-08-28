# -*- coding: utf-8 -*-
"""W-1 — sector-neutral ranking re-run on S25's POINT-IN-TIME map.

Executes `PREREG_w1_sector_neutral_pit.md` (committed ALONE at 9990c95, amended at e3174e5 before
any outcome existed). Three passes, and the split is the discipline:

    python -m scripts.w1_sector_neutral_pit --build     # ONE paired build, cached
    python -m scripts.w1_sector_neutral_pit --kills     # K1..K5, banked
    python -m scripts.w1_sector_neutral_pit --arm       # REFUSES without a passing kills artifact

`O10`'s process defect was computing a gating control and the outcome statistics in one pass. The
build is shared because `SECTOR-NEUTRAL-B6` established that ONE build scoring both arms from the
SAME `metrics` list is the correct construction -- it makes the row set provably identical and
makes the known `insider` nondeterminism common-mode -- but the KILLS are still read in their own
pass, and `--arm` refuses without their artifact.

THE PRIMARY IS `REPAIR-A`, PER AMENDMENT 1: the dated sector ONLY where the map disagrees with
ITSELF between the as-of date and today, so the crosswalk's vendor taxonomy disagreement cancels
by construction and what moves is look-ahead alone. `REPAIR-B` is CONFOUNDED and carries no
verdict. `s25_repair_sectors` is CALLED, never re-implemented (`B7`).

ADOPTS NOTHING. Sector-neutral shipping is a vintage event and Don's call.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
CACHE = os.path.join(FA, "panel_w1_pit_pair.pkl")
KILLS = os.path.join(FA, "W1_KILLS.json")
ARM = os.path.join(FA, "W1_ARM.json")

# ---- register constants. Changing one after a measurement voids the item.
K1_COVERAGE_BAR = 0.85        # §4, set AFTER the coverage census and with it printed
K2_BITE_BAR = 0.01            # AMENDMENT 1: REPAIR-A's bite, on the OVERALL covered set
K3_MIN_GROUP = 2              # a within-group demean on a singleton is the identity
K3_MIN_SECTORS = 5
#: `SECTOR-NEUTRAL-B6`'s OWN two weightings, IMPORTED rather than retyped (`B7`). DEPLOYED
#: is the seven weighted themes and CARRIES THE VERDICT; FLAT adds `growth` and `low_risk`,
#: the two the deployed vector zeroes, and tests whether the answer depends on the
#: weighting at all. `sentiment` is in neither because it is empty.
from scripts.sector_neutral_rerun import DEPLOYED, FLAT, BASE_WEIGHT   # noqa: E402

PUBLISHED = {"top_decile_alpha": 0.071741423321, "long_short_tstat": 2.8360640685320595,
             "long_short_tstat_nw": 2.6199121240414884, "monotonicity": -0.890909}
TOL = {"top_decile_alpha": 1e-9, "long_short_tstat": 1e-9,
       "long_short_tstat_nw": 1e-9, "monotonicity": 1e-5}


def _sector_at_factory():
    """`(ticker, as_of, base) -> sector`, REPAIR-A. Calls S25's own decision function."""
    from valuation.edge import sector_map as SM
    from valuation.engine.calibration import s25_repair_sectors
    smap = SM.load()
    seen = collections.Counter()

    def sector_at(ticker, as_of, base):
        a, b, state, pit = s25_repair_sectors(smap, str(ticker).upper(), str(as_of)[:10], base)
        seen[state] += 1
        seen["_moved_a"] += int(a != base)
        seen["_moved_b"] += int(b != base)
        seen["_cells"] += 1
        return a

    sector_at.seen = seen
    return sector_at


def build() -> "pd.DataFrame":
    if os.path.exists(CACHE):
        print("[w1] reading cached paired panel %s" % CACHE, flush=True)
        return pd.read_pickle(CACHE)
    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _C:
        wrds_data_dir = os.path.join(_ROOT, "data", "backtest")

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("[w1] provider not ready: %s" % msg)
    tickers = prov.universe(limit=CONFIG.backtest_universe_limit)
    sa = _sector_at_factory()
    print("[w1] %d names; ONE build, sector_neutral_pair=True, PIT sector via REPAIR-A"
          % len(tickers), flush=True)
    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=63, sector_neutral_pair=True, sector_at=sa)
    print("[w1] built %d rows x %d cols in %.0fs" % (len(panel), len(panel.columns),
                                                     time.time() - t0), flush=True)
    panel.attrs["_w1_sector_states"] = dict(sa.seen)
    os.makedirs(FA, exist_ok=True)
    panel.to_pickle(CACHE)
    return panel


def split_arms(panel):
    """The two arms over an IDENTICAL row set -- `SECTOR-NEUTRAL-B6`'s own split."""
    from valuation.screener import settings as S
    flat, sn = panel.copy(), panel.copy()
    for theme in S.FACTORS_ALL:
        src = "sn_" + theme
        if src in sn.columns:
            sn[theme] = sn[src]
    drop = [c for c in sn.columns if c.startswith("sn_")]
    return flat.drop(columns=drop, errors="ignore"), sn.drop(columns=drop, errors="ignore")


def kills(panel) -> dict:
    from valuation.edge import research_log as RL
    from valuation.edge.fundamental_panel import quantile_backtest
    from valuation.screener import settings as S

    st = panel.attrs.get("_w1_sector_states") or {}
    n_cells = int(st.get("_cells") or 0)
    out = {"item": "W-1", "trials": 2, "equity_N": RL.detail()["by_domain"]["equity"],
           "sector_states": st}

    # ---- K2 BITE, on REPAIR-A and on the OVERALL covered set (Amendment 1)
    bite = (st.get("_moved_a", 0) / n_cells) if n_cells else 0.0
    out["K2_bite"] = {"bar": K2_BITE_BAR, "repair_a_moved": st.get("_moved_a"),
                      "repair_b_moved_confounded": st.get("_moved_b"),
                      "cells_seen": n_cells, "frac": bite,
                      "fires": bool(bite < K2_BITE_BAR)}

    # ---- K1 COVERAGE, per rebalance date, on the arm's own population
    ok_states = int(st.get("OK") or 0)
    out["K1_coverage"] = {"bar": K1_COVERAGE_BAR,
                          "frac_cells_OK": (ok_states / n_cells) if n_cells else 0.0,
                          "fires": bool((ok_states / n_cells if n_cells else 0.0)
                                        < K1_COVERAGE_BAR)}

    # ---- K3 DEGENERACY on the ARM's grouping
    bad_dates, min_grp, min_sec = [], 10 ** 9, 10 ** 9
    for d, g in panel.groupby("date"):
        vc = g["sector"].fillna("").replace("", np.nan).dropna().value_counts()
        if len(vc) == 0:
            bad_dates.append((str(d), 0, 0))
            continue
        min_grp = min(min_grp, int(vc.min()))
        min_sec = min(min_sec, int(len(vc)))
        if int(vc.min()) < K3_MIN_GROUP or len(vc) < K3_MIN_SECTORS:
            bad_dates.append((str(d), int(vc.min()), int(len(vc))))
    out["K3_degeneracy"] = {"min_group": min_grp, "min_sectors": min_sec,
                            "bad_dates": bad_dates[:10], "n_bad": len(bad_dates),
                            "fires": bool(bad_dates)}

    # ---- K4 FIDELITY: the INCUMBENT arm must reproduce the published record
    flat, _sn = split_arms(panel)
    # `MA28`'s C1 defect, committed here and caught by this very control on its first
    # run: the first cut scored the NINE bucket themes at 0.125 when the deployed
    # composite is SEVEN. The published record comes from DEPLOYED, so that is what
    # fidelity is checked against.
    cols = [c for c in DEPLOYED if c in flat.columns]
    r = quantile_backtest(flat, cols, {c: BASE_WEIGHT for c in cols}, n_q=10, horizon=63)
    got = {k: float(r[k]) for k in PUBLISHED}
    ok = all(abs(got[k] - PUBLISHED[k]) <= TOL[k] for k in PUBLISHED)
    out["K4_fidelity"] = {"published": PUBLISHED, "measured": got, "fires": not ok}

    # ---- K5 LOOK-AHEAD: the map must refuse rather than carry a classification backwards
    out["K5_lookahead"] = {"states_seen": {k: v for k, v in st.items() if not k.startswith("_")},
                           "BEFORE_GICS_or_future": int(st.get("BEFORE_GICS") or 0),
                           "fires": bool(st.get("BEFORE_GICS"))}

    out["all_kills_pass"] = not any(out[k]["fires"] for k in
                                    ("K1_coverage", "K2_bite", "K3_degeneracy",
                                     "K4_fidelity", "K5_lookahead"))
    return out


def arm(panel) -> dict:
    if not os.path.isfile(KILLS):
        raise SystemExit("REFUSED: %s is ABSENT -- the kills have not been run, which is a "
                         "DIFFERENT state from their having run and failed." % KILLS)
    k = json.load(open(KILLS))
    if not k.get("all_kills_pass"):
        raise SystemExit("REFUSED: %s exists and reports all_kills_pass=false. A kill fired; "
                         "the arm may not be scored." % KILLS)

    from valuation.edge.fundamental_panel import (holdout_compare_panels, quantile_backtest,
                                                  MIN_HOLDOUT_ALPHA_GAIN, MIN_HOLDOUT_TSTAT_GAIN)
    from valuation.screener import settings as S
    flat, sn = split_arms(panel)
    out = {"item": "W-1", "deployed_cols": DEPLOYED, "flat_cols": FLAT,
           "margins": {"alpha": MIN_HOLDOUT_ALPHA_GAIN, "tstat": MIN_HOLDOUT_TSTAT_GAIN},
           "weightings": {}}

    # deployed = flat 1/7 across the scored themes is the SHIPPED vector for this bucket; the
    # register scores BOTH it and the explicit flat base_weight, as SECTOR-NEUTRAL-B6 did.
    for label, cset in (("deployed", DEPLOYED), ("flat", FLAT)):
        cols = [c for c in cset if c in flat.columns]
        bw = BASE_WEIGHT
        g = holdout_compare_panels(flat, sn, cols, label_a="OFF_today",
                                   label_b="ON_pit_sector", base_weight=bw)
        lev = {}
        for aname, p in (("incumbent", flat), ("arm_pit", sn)):
            r = quantile_backtest(p, cols, {c: bw for c in cols}, n_q=10, horizon=63)
            lev[aname] = {kk: float(r[kk]) for kk in
                          ("top_decile_alpha", "long_short_tstat", "long_short_tstat_nw",
                           "monotonicity")}
        out["weightings"][label] = {"gate": g, "levels": lev}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--kills", action="store_true")
    ap.add_argument("--arm", action="store_true")
    a = ap.parse_args(argv)
    if sum(map(bool, (a.build, a.kills, a.arm))) != 1:
        raise SystemExit("pass exactly one of --build, --kills or --arm")
    os.makedirs(FA, exist_ok=True)
    p = build()
    if a.build:
        print("[w1] build cached at %s" % CACHE)
        return 0
    if a.kills:
        o = kills(p)
        json.dump(o, open(KILLS, "w"), indent=1, default=str)
        print(json.dumps(o, indent=1, default=str)[:6000])
        print("\nwrote", KILLS)
        return 0 if o["all_kills_pass"] else 2
    o = arm(p)
    json.dump(o, open(ARM, "w"), indent=1, default=str)
    print(json.dumps(o, indent=1, default=str)[:8000])
    print("\nwrote", ARM)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
