"""EVOWN pass 3 - THE ARMS. A1 the DTE-matched mean gap, A2 survivability. BOTH REQUIRED.

`PREREG_evown_event_ownership.md`. Refuses without the built book.

A1 - the MEAN gap of the event-ownership book against a DTE-MATCHED random-entry control.
     THE MEDIAN IS BANNED BY MEASUREMENT (O17C4 recorded the effect as "a MEAN effect, not a
     MEDIAN one"; MB1 reproduced it) and a test pins that none is computed here.
     Matching is BY DESIGN, not checked afterwards: same ticker, same year, same DTE bucket on
     O17C4's own quartile cuts (51/58/66), and a trade whose cell is empty on either side is
     DROPPED AND COUNTED rather than matched loosely.
     Uncertainty: PAIRED name-year cluster bootstrap on R3's own unit, same keys both arms.

A2 - SURVIVABILITY on O11's own simulator, imported. Per-trade expectancy without survivability
     is the exact mistake O11 exists to prevent: a book with +3.27%/trade ended at $37,059 from
     $50,000 at cap 10.

    python -m scripts.evown_arms
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys

import numpy as np

from valuation.edge import power_gate as PG
from valuation.edge import research_log as RL
from valuation.edge import options_vrp as V
from valuation.edge import options_vrp_portfolio as VP
from valuation.studies import portfolio_capacity as PC
from scripts.mb_evown_census import DATA

BOOK = os.path.join(DATA, "free_analysis", "EVOWN_BOOK.pkl")
UNIV = os.path.join(DATA, "options_universe")
OUT = os.path.join(DATA, "free_analysis", "EVOWN_ARMS.json")

DTE_CUTS = (51.0, 58.0, 66.0)      # O17C4's own quartile cuts, reused verbatim
N_DRAWS = 2000
SEED = 20260820
EQUITIES = (50_000.0, 250_000.0)
CAPS = (10, 50)
MIN_TRADES, MIN_HALF = 500, 200    # register floors -> UNDERPOWERED, never null
N_SEEDS = 5


def _bucket(dte):
    d = float(dte)
    return 0 if d <= DTE_CUTS[0] else 1 if d <= DTE_CUTS[1] else 2 if d <= DTE_CUTS[2] else 3


def _load_controls(names):
    out = []
    for s in range(N_SEEDS):
        with open(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s), "rb") as fh:
            d = pickle.load(fh)
        for r in (d["rows"] if isinstance(d, dict) else d):
            if r.get("ticker") not in names or r.get("pnl_pct") is None:
                continue
            dte = r.get("dte")
            if dte is None:
                continue
            out.append({"ticker": r["ticker"], "entry": str(r["alert_ts"])[:10],
                        "year": str(r["alert_ts"])[:4], "dte": float(dte),
                        "ret": float(r["pnl_pct"]), "seed": s})
    return out


def _cellkey(r):
    return (r["ticker"], r["year"], _bucket(r["dte"]))


def _gap(strat, ctrl):
    """Mean(strategy) - mean(control) in pp, on the COMMON SUPPORT of matched cells."""
    if not strat or not ctrl:
        return None
    return (float(np.mean([r["ret"] for r in strat]))
            - float(np.mean([r["ret"] for r in ctrl]))) * 100.0


def main():
    if not os.path.exists(BOOK):
        raise SystemExit("REFUSING: no built book at %s - run scripts.evown_build first" % BOOK)
    rows = pickle.load(open(BOOK, "rb"))["rows"]
    rows = [r for r in rows if r.get("ret") is not None]
    names = {r["ticker"] for r in rows}
    ctrl = _load_controls(names)

    # ---- DTE MATCHING, BY DESIGN -------------------------------------------------------------
    s_cells, c_cells = {}, {}
    for r in rows:
        s_cells.setdefault(_cellkey(r), []).append(r)
    for r in ctrl:
        c_cells.setdefault(_cellkey(r), []).append(r)
    common = set(s_cells) & set(c_cells)
    s_m = [r for k in common for r in s_cells[k]]
    c_m = [r for k in common for r in c_cells[k]]
    dropped = {"strategy_no_control_cell": len(rows) - len(s_m),
               "control_no_strategy_cell": len(ctrl) - len(c_m)}

    cut = sorted(r["entry"] for r in s_m)[len(s_m) // 2]
    windows = {"full": lambda e: True, "early": lambda e: e < cut, "late": lambda e: e >= cut}

    # ---- POWER, PRINTED BEFORE ANY ARM IS SCORED ---------------------------------------------
    n_opt = RL.detail()["by_domain"]["options"]
    rets = np.array([r["ret"] for r in s_m], dtype=float)
    se = float(rets.std(ddof=1) / np.sqrt(len(rets))) * 100.0
    power_line = PG.state(4.79, se, n_trials=n_opt)      # O17C4's own +4.79pp, not chosen here
    print("[EVOWN] POWER (before scoring): %s" % power_line, flush=True)

    underpowered = (len(s_m) < MIN_TRADES
                    or min(sum(1 for r in s_m if w(r["entry"])) for w in
                           (windows["early"], windows["late"])) < MIN_HALF)

    # ---- A1, with the paired cluster bootstrap ------------------------------------------------
    rng = np.random.default_rng(SEED)
    a1 = {}
    for wname, sel in windows.items():
        S = [r for r in s_m if sel(r["entry"])]
        C = [r for r in c_m if sel(r["entry"])]
        sb, cb = {}, {}
        for r in S:
            sb.setdefault((r["ticker"], r["year"]), []).append(r)
        for r in C:
            cb.setdefault((r["ticker"], r["year"]), []).append(r)
        keys = sorted(set(sb) & set(cb))
        point = _gap(S, C)
        draws = []
        for _ in range(N_DRAWS):
            pick = rng.choice(len(keys), size=len(keys), replace=True)
            kk = [keys[i] for i in pick]                       # PAIRED: same keys for both arms
            g = _gap([r for k in kk for r in sb[k]], [r for k in kk for r in cb[k]])
            if g is not None:
                draws.append(g)
        arr = np.asarray(draws)
        lo, hi = (float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))) \
            if arr.size else (None, None)
        a1[wname] = {
            "n_strategy": len(S), "n_control": len(C), "n_clusters": len(keys),
            "strategy_mean_pp": float(np.mean([r["ret"] for r in S])) * 100.0 if S else None,
            "control_mean_pp": float(np.mean([r["ret"] for r in C])) * 100.0 if C else None,
            "gap_pp": point, "ci95_lo_pp": lo, "ci95_hi_pp": hi,
            "excludes_zero": (lo is not None and (lo > 0 or hi < 0)),
            "positive": (point is not None and point > 0),
        }
        print("[EVOWN] A1 %-5s n %5d vs %6d | strat %+8.4fpp ctrl %+8.4fpp | gap %+8.4fpp "
              "CI95 [%+8.4f, %+8.4f]" % (wname, len(S), len(C), a1[wname]["strategy_mean_pp"],
                                         a1[wname]["control_mean_pp"], point, lo, hi), flush=True)

    a1_pass = all(a1[w]["excludes_zero"] and a1[w]["positive"] for w in windows)

    # ---- A2, SURVIVABILITY on O11's own simulator ---------------------------------------------
    trades = []
    for r in s_m:
        t = PC.long_leg_as_book_trade(r, r.get("marks") or [])
        if t:
            trades.append(t)
    a2, saved = {}, (V.MAX_CONCURRENT, V.INITIAL_CAPITAL)
    try:
        for cap in CAPS:
            V.MAX_CONCURRENT = int(cap)
            for eq in EQUITIES:
                bk = VP.simulate_book(trades, {}, initial_capital=eq, vol_target=False)
                fin = (bk or {}).get("final_equity")
                key = "cap%d_$%d" % (cap, int(eq))
                a2[key] = {
                    "cap": cap, "initial_capital": eq, "final_equity": fin,
                    "total_return": (bk or {}).get("total_return"),
                    "n_taken": (bk or {}).get("n_taken"),
                    "n_generated": (bk or {}).get("n_generated"),
                    "skipped": (bk or {}).get("skipped"),
                    "avg_concurrent": (bk or {}).get("avg_concurrent"),
                    "above_start": (fin is not None and fin > eq),
                }
                sk = a2[key]["skipped"] or {}
                print("[EVOWN] A2 cap %-3d $%-8d taken %5s/%-5s final %12s  %s  refused_conc %s"
                      % (cap, int(eq), a2[key]["n_taken"], a2[key]["n_generated"],
                         "n/a" if fin is None else "%,.0f" % fin if False else ("%.0f" % fin),
                         "ABOVE" if a2[key]["above_start"] else "below",
                         sk.get("concurrency")), flush=True)
    finally:
        V.MAX_CONCURRENT, V.INITIAL_CAPITAL = saved

    a2_pass = all(a2["cap10_$%d" % int(e)]["above_start"] for e in EQUITIES)

    verdict = ("UNDERPOWERED" if underpowered else
               "VIABLE" if (a1_pass and a2_pass) else
               "REAL-BUT-UNSURVIVABLE" if (a1_pass and not a2_pass) else
               "NOT-DEMONSTRATED")

    payload = {
        "item": "EVOWN", "pass": "arms",
        "register": "PREREG_evown_event_ownership.md",
        "scope": "157 scoreable alert-book names, 2016-2025, the covered ~75% of in-window "
                 "announcements; the uncovered remainder is UNMEASURED and never read as zero",
        "median_is_banned": "O17C4 recorded the effect as a MEAN effect and not a MEDIAN one; "
                            "MB1 reproduced it. No median is computed in this file.",
        "dte_cuts": list(DTE_CUTS), "half_cut": cut,
        "matched": {"n_strategy": len(s_m), "n_control": len(c_m),
                    "n_cells": len(common), "dropped": dropped},
        "power_before_scoring": power_line, "options_N_at_run": n_opt,
        "A1": a1, "A1_pass": bool(a1_pass),
        "A2": a2, "A2_pass": bool(a2_pass),
        "A2_bar": "final equity above initial at cap 10 at BOTH account sizes; cap 50 reported "
                  "beside it and carries no verdict",
        "underpowered": bool(underpowered),
        "verdict": verdict,
        "framing": "O11 GOVERNS and nothing here licenses a trade. R2 stands - the alert "
                   "subtracts value inside this very effect.",
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)
    print()
    print("A1_pass=%s  A2_pass=%s  ->  VERDICT: %s" % (a1_pass, a2_pass, verdict))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
