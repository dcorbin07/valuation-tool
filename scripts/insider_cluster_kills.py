# -*- coding: utf-8 -*-
"""`INSIDER-CLUSTER` §7 — the four FREE PRE-OUTCOME KILLS, in their own pass.

    python -m scripts.insider_cluster_kills

Register: `PREREG_insider_cluster.md`, committed **ALONE at `fd87870`**, markdown only, a strict
git ancestor of this file. Trials booked at `4a34a00` (equity 297 -> 301) **before this file
existed**.

**NO FORWARD RETURN IS READ HERE.** `O10`'s process defect is that a gating control and its
outcomes ran in one pass, so this pass can be run and read without having seen an outcome, and
`scripts/insider_cluster_arm.py` REFUSES without the artifact this writes.

**EVERY BAR BELOW IS FROM THE REGISTER.** Changing one after a measurement voids the item
(`MA28`'s rule), and `W-28`'s rule binds too: a bar may be RAISED and never LOWERED once watched.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402

OUT = "INSIDER_CLUSTER_KILLS.json"

# ----------------------------------------------------------------------- REGISTER BARS (§6, §7)
#: §5's derived requirement, per horizon: the n at which the NAIVE 80%-power MDE equals the
#: hypothesised long-only drift at that horizon. Copied from the census artifact at run time
#: rather than retyped, so there is one definition (`MA5`).
HORIZONS_PRIMARY = (63, 126)
HORIZONS_SENSITIVITY = (5, 21)

#: K2 — the share of cluster events within `DIP_WINDOW` sessions of a DIP-CALL event.
DIP_OVERLAP_BAR = 0.25
DIP_WINDOW = 5

#: K3 — mean per-date |Spearman| of the event flag against each weighted theme.
COSTUME_BAR = 0.60

#: Stage 1b's floor on the governing tier's per-date name count.
CONTRACT_MIN_POSITIONS = D.CONTRACT_MIN_POSITIONS


def _events(k: int = IC.K_PRIMARY) -> pd.DataFrame:
    """The banked strict event set from the census. REFUSES rather than rebuilding silently."""
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % k)
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: no banked event set at %s -- run the census first" % p)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    return ev


def _build_half0(ev: pd.DataFrame) -> pd.DataFrame:
    return ev[(ev["era"] == "build") & (ev["half"] == 0)].reset_index(drop=True)


def k1_event_floor(bq: pd.DataFrame, cens2: dict) -> dict:
    """§7 K1. Already measured in the census; re-derived here so the kill is read in its pass."""
    sched = D.tier_schedule()
    from scripts.insider_cluster_census import tier_flags
    tf = tier_flags(bq, sched)
    out = {"bar": "the cell's event count must reach the register's derived required n",
           "cells": {}}
    for pop, mask in (("full_universe", np.ones(len(bq), dtype=bool)),
                      ("tier_cap_ge_10bn", tf)):
        n = int(mask.sum())
        g = int(bq.loc[mask, "ticker"].nunique())
        for h in HORIZONS_PRIMARY:
            req = float(cens2["mde"][pop][str(h)]["required_n_at_cmp_longonly"])
            out["cells"]["%s_h%d" % (pop, h)] = {
                "n_events": n, "n_ticker_clusters": g, "required_n": req,
                "clears": bool(n >= req),
                "shortfall_x": (req / n) if n else float("inf"),
                "power_vs_hypothesised_clustered":
                    cens2["mde"][pop][str(h)]["power_vs_cmp_longonly_clustered"],
            }
    out["assessable_cells"] = sorted(c for c, v in out["cells"].items() if v["clears"])
    out["not_assessable_cells"] = sorted(c for c, v in out["cells"].items() if not v["clears"])
    # A KILL THAT REMOVES A CELL IS NOT A KILL THAT STOPS THE ITEM, and the register says which
    # is which: K1 marks the tier UNDERPOWERED-BY-CONSTRUCTION (declared in advance), while K2
    # and K3 stop the whole item. Collapsing the two would make a declared limitation look like
    # a failure.
    out["fires_but_does_not_stop_the_item"] = True
    return out


def k2_dip_overlap(bq: pd.DataFrame) -> dict:
    """§7 K2. Is this `V6-B`'s dip x insider arm again? Bar 0.25, and it STOPS the item."""
    sched = D.tier_schedule()
    near = 0
    checked = 0
    missing_price = 0
    by_tk = {t: g["date"].tolist() for t, g in bq.groupby("ticker")}
    for tk, dates in by_tk.items():
        f = D.name_frame(tk, sched.get(tk, []), k=D.K_PRIMARY)
        if f is None:
            missing_price += len(dates)
            continue
        idx = {d: i for i, d in enumerate(f["date"].astype(str).tolist())}
        evmask = f["event"].to_numpy(dtype=bool)
        for dt in dates:
            i = idx.get(str(dt))
            if i is None:
                missing_price += 1
                continue
            checked += 1
            lo = max(0, i - DIP_WINDOW)
            if evmask[lo:i + 1].any():
                near += 1
    share = (near / checked) if checked else float("nan")
    return {
        "bar": DIP_OVERLAP_BAR, "window_sessions": DIP_WINDOW,
        "events_checked": checked, "events_with_a_dip_within_window": near,
        "share": share,
        "events_without_a_price_series": missing_price,
        "fires": bool(np.isfinite(share) and share >= DIP_OVERLAP_BAR),
        "WHY": ("V6-B's arm 3 tested dip x insider open-market buying and was NULL. If clusters "
                "mostly follow crashes this register is re-running a failed arm under a new "
                "name."),
        "DIP_IS": "the shipped DIP-CALL construction, z <= -2.5 on a strictly-prior 60-session scale",
    }


def k3_costume(bq: pd.DataFrame) -> dict:
    """§7 K3. Is the event flag the `insider` theme, or any other weighted theme, in disguise?

    The flag is an EVENT-TIME indicator and a theme is a quarterly cross-sectional z-score, so
    the comparison is made the only way it can be: at each panel date, the flag is 1 for a name
    with a cluster event in the preceding quarter and 0 otherwise, and the Spearman is taken
    within that date. Stated because a reader could otherwise assume a daily correlation.
    """
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    panel = panel[(panel["date"] >= "2009-01-01") & (panel["date"] <= D.BUILD_HI)]
    panel = panel[panel["ticker"].map(D.stable_key_half) == 0]
    themes = [c for c in ("value", "quality", "growth", "momentum", "size",
                          "insider", "institutional", "capital_discipline", "low_risk")
              if c in panel.columns]
    dates = sorted(set(panel["date"]))
    ev_by_tk = {t: sorted(g["date"].astype(str).tolist())
                for t, g in bq.groupby("ticker")}
    rows = {t: [] for t in themes}
    n_used = 0
    for j, d in enumerate(dates):
        prev = dates[j - 1] if j else None
        if prev is None:
            continue
        g = panel[panel["date"] == d]
        if len(g) < 30:
            continue
        flag = np.array([1.0 if any(prev < x <= d for x in ev_by_tk.get(t, []))
                         else 0.0 for t in g["ticker"].tolist()])
        if flag.sum() < 5 or flag.sum() == len(flag):
            continue
        n_used += 1
        fr = pd.Series(flag).rank().to_numpy()
        for th in themes:
            v = pd.to_numeric(g[th], errors="coerce").to_numpy(dtype=float)
            ok = np.isfinite(v)
            if ok.sum() < 30:
                continue
            vr = pd.Series(v[ok]).rank().to_numpy()
            f2 = pd.Series(flag[ok]).rank().to_numpy()
            if vr.std() == 0 or f2.std() == 0:
                continue
            rows[th].append(abs(float(np.corrcoef(vr, f2)[0, 1])))
    per = {th: (float(np.mean(xs)) if xs else float("nan")) for th, xs in rows.items()}
    worst = max((v for v in per.values() if np.isfinite(v)), default=float("nan"))
    worst_th = max(per, key=lambda t: (per[t] if np.isfinite(per[t]) else -1)) if per else ""
    return {
        "bar": COSTUME_BAR, "dates_used": n_used,
        "mean_abs_spearman_per_theme": per,
        "worst_theme": worst_th, "worst": worst,
        "fires": bool(np.isfinite(worst) and worst >= COSTUME_BAR),
        "WHY": ("the insider theme's own IC t is -0.24; a flag that is mostly the theme inherits "
                "that and is not a new signal"),
    }


def k4_look_ahead(k: int = IC.K_PRIMARY) -> dict:
    """§7 K4. No event may be dated before its own filing, and the habit reads prior years only.

    A POSITIVE CONTROL is included so the guard cannot pass by refusing everything: a synthetic
    frame with a deliberate same-month repeat in both prior years MUST classify ROUTINE.
    """
    from valuation.studies import insider_routine as IR
    ev = _events(k)
    bad = 0
    for lo, dt in zip(ev["window_lo"].astype(str), ev["date"].astype(str)):
        if dt < lo:
            bad += 1
    # positive control, and its mirror
    rout = pd.DataFrame({
        "ticker": ["AAA"] * 3, "ownername": ["X"] * 3,
        "transactiondate": ["2017-03-10", "2018-03-11", "2019-03-12"]})
    opp = pd.DataFrame({
        "ticker": ["BBB"] * 3, "ownername": ["Y"] * 3,
        "transactiondate": ["2017-01-10", "2018-06-11", "2019-03-12"]})
    rl = IR.classify(rout).tolist()
    ol = IR.classify(opp).tolist()
    return {
        "events_dated_before_their_window": int(bad),
        "fires": bool(bad > 0),
        "positive_control_routine_detected": bool(rl[-1] == IR.ROUTINE),
        "negative_control_stays_opportunistic": bool(ol[-1] == IR.OPPORTUNISTIC),
        "control_note": ("a guard that refuses everything would pass the look-ahead test and "
                         "fail the positive control, which is why both run"),
    }


def tier_name_counts() -> dict:
    """Stage 1b requires the tier's PER-DATE name count to ship, because a nominal $10bn floor
    drifts in real terms across 2009-2019 and a reader must see the tier's size moving."""
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    panel = panel[(panel["date"] >= "2009-01-01") & (panel["date"] <= D.BUILD_HI)]
    panel = panel[panel["ticker"].map(D.stable_key_half) == 0]
    cap = pd.to_numeric(panel["market_cap"], errors="coerce")
    tier = panel[cap >= D.TIER_FLOOR]
    per = tier.groupby("date")["ticker"].nunique()
    return {
        "dates": int(per.size),
        "min": int(per.min()) if per.size else 0,
        "median": float(per.median()) if per.size else 0.0,
        "max": int(per.max()) if per.size else 0,
        "dates_below_contract_min": int((per < CONTRACT_MIN_POSITIONS).sum()),
        "contract_min_positions": CONTRACT_MIN_POSITIONS,
        "clears_on_every_date": bool(per.size and (per >= CONTRACT_MIN_POSITIONS).all()),
    }


def main(argv=None):
    t0 = time.time()
    cens2 = json.load(io.open(D.out_path("INSIDER_CLUSTER_CENSUS2.json"), encoding="utf-8"))
    ev = _events(IC.K_PRIMARY)
    bq = _build_half0(ev)
    print("[kills] build x half0: %d events over %d tickers"
          % (len(bq), bq["ticker"].nunique()), flush=True)

    out = {"item": "INSIDER-CLUSTER", "part": "section 7 -- the free pre-outcome kills",
           "register": "PREREG_insider_cluster.md", "register_commit": "fd87870",
           "trials_booked_at": "4a34a00",
           "reads_no_forward_return": True,
           "build_half0": {"events": int(len(bq)),
                           "tickers": int(bq["ticker"].nunique()),
                           "early": int((bq["inner_half"] == "early").sum()),
                           "late": int((bq["inner_half"] == "late").sum())}}

    print("[kills] K1 the derived event floor ...", flush=True)
    out["K1_event_floor"] = k1_event_floor(bq, cens2)
    print("    assessable: %s" % out["K1_event_floor"]["assessable_cells"], flush=True)
    print("    NOT assessable: %s" % out["K1_event_floor"]["not_assessable_cells"], flush=True)

    print("[kills] K2 overlap with a DIP-CALL event ...", flush=True)
    out["K2_dip_overlap"] = k2_dip_overlap(bq)
    print("    share %.4f against a bar of %.2f -> fires: %s"
          % (out["K2_dip_overlap"]["share"], DIP_OVERLAP_BAR,
             out["K2_dip_overlap"]["fires"]), flush=True)

    print("[kills] K3 the costume check against every weighted theme ...", flush=True)
    out["K3_costume"] = k3_costume(bq)
    print("    worst %s at %.4f against a bar of %.2f -> fires: %s"
          % (out["K3_costume"]["worst_theme"], out["K3_costume"]["worst"], COSTUME_BAR,
             out["K3_costume"]["fires"]), flush=True)

    print("[kills] K4 look-ahead, with a positive control ...", flush=True)
    out["K4_look_ahead"] = k4_look_ahead()
    print("    %s" % json.dumps(out["K4_look_ahead"]), flush=True)

    out["tier_name_counts"] = tier_name_counts()
    print("[kills] tier per-date names: %s" % json.dumps(out["tier_name_counts"]), flush=True)

    stoppers = ["K2_dip_overlap", "K3_costume", "K4_look_ahead"]
    out["stopping_kill_fired"] = any(out[k]["fires"] for k in stoppers)
    out["all_stopping_kills_pass"] = not out["stopping_kill_fired"]
    out["assessable_cells"] = out["K1_event_floor"]["assessable_cells"]
    out["seconds"] = round(time.time() - t0, 1)

    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[kills] stopping kills pass: %s | assessable cells: %s"
          % (out["all_stopping_kills_pass"], out["assessable_cells"]), flush=True)
    print("[kills] wrote %s in %.0fs" % (p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    r = main()
    raise SystemExit(0 if r["all_stopping_kills_pass"] else 2)
