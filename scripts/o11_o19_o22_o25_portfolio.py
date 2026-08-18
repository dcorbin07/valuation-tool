"""O11 + O19 + O22 + O25 — the portfolio-and-capacity batch.

Executes PREREG_o11_o19_o22_o25_portfolio.md, committed ALONE at 1203a85 before this file
existed. Frozen book, no re-mine, no live code path changed, nothing adopted.

TWO STAGES, AND THE ORDER IS ENFORCED RATHER THAN PROMISED (register §1):

    python -m scripts.o11_o19_o22_o25_portfolio --stage o19     # runs FIRST, writes its artifact
    python -m scripts.o11_o19_o22_o25_portfolio --stage main    # REFUSES without that artifact

O11 sizes in WHOLE CONTRACTS and therefore inherits whatever O19 finds about whole-contract
arithmetic, so reading O11 first would mean interpreting an equity curve without knowing whether
its own sizing rule generated the number. Session 26 computed a gating control and its outcomes
in one pass and had to report the control could not be claimed to have been read first.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge.chain_store import resolve_chains as _resolve_chains  # noqa: E402

from valuation.studies import portfolio_capacity as PC        # noqa: E402
from valuation.edge import options_vrp_portfolio as VP     # noqa: E402
from valuation.edge import options_vrp as V                # noqa: E402
from valuation.edge import options_stats as OS             # noqa: E402
from valuation.edge import blackscholes as BS              # noqa: E402


def _data_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "data")
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return cand
        here = os.path.dirname(here)
    return os.path.join(os.getcwd(), "data")


DATA = _data_root()
BOOK = os.path.join(DATA, "options_universe", "state_r2_splitclean.pkl")
FREEZE = os.path.join(DATA, "options_freeze", "R2_CORRECTED_2026-08-08", "chains.pkl.gz")
# ---------------------------------------------------------------------------------------------
# CHAIN STORE — the PINNED freeze, resolved lazily.
#
# `data/options` is written by the miner continuously, and the options re-open list measured
# 44.2% of its payload units rewritten AFTER the books here were banked. Reading it back was
# therefore not reading the bytes these verdicts stand on. One shared resolver now owns that
# decision; the mutable store is an explicit opt-out (VALQUO_CHAINS=mutable), never a silent
# fallback.
#
# Resolved on first USE rather than at import: tests import this module and CI has no D: drive,
# so resolving at module level would raise at import time and take the suite down.
_CHAINS = None
CHAINS_PROVENANCE = None


def chains_dir():
    """The chain-store root. Raises if the pin is unusable rather than falling back."""
    global _CHAINS, CHAINS_PROVENANCE
    if _CHAINS is None:
        _CHAINS, CHAINS_PROVENANCE = _resolve_chains(DATA)
    return _CHAINS
BARS = os.path.join(DATA, "bulk", "prepared", "bars")
O19_OUT = os.path.join(DATA, "free_analysis", "O19_SIZING_ARTEFACT.json")
MARKS_CACHE = os.path.join(DATA, "free_analysis", "O11_MARKS.pkl")
WING_CACHE = os.path.join(DATA, "free_analysis", "O25_WINGS.pkl")
OUT = os.path.join(DATA, "free_analysis", "O11_O19_O22_O25_PORTFOLIO.json")

T0 = time.time()


def _log(m):
    print("[O11/O19/O22/O25] %s  %.0fs" % (m, time.time() - T0), flush=True)


def load_book():
    with open(BOOK, "rb") as f:
        blob = pickle.load(f)
    rows = blob["rows"] if isinstance(blob, dict) else blob
    return [r for r in rows if r.get("status") == "closed"]


def load_raw_close(tkr):
    """RAW closes only. The adjusted series is the U1-SPLIT trap; assert_raw_spot enforces it."""
    p = os.path.join(BARS, "%s.pkl" % tkr)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "rb") as f:
            b = pickle.load(f)
    except Exception:
        return {}
    if not isinstance(b, dict) or "date" not in b or "raw_close" not in b:
        return {}
    return {str(d)[:10]: float(c) for d, c in zip(b["date"], b["raw_close"])
            if c is not None and float(c) > 0}


def _rows_for_block(vals, dates):
    return [{"pnl_pct": float(v), "alert_ts": d} for v, d in zip(vals, dates)]


def _ci(vals, dates):
    if len(vals) < 30:
        return None
    b = OS.date_block_bootstrap(_rows_for_block(vals, dates))
    return b.get("ci95") if isinstance(b, dict) else None


# =============================================================================== STAGE O19
def stage_o19(rows):
    """Runs FIRST and alone. Expectancy three ways, then premium floors."""
    dates = np.array([str(r["alert_ts"]) for r in rows])
    med = sorted(set(dates.tolist()))[len(set(dates.tolist())) // 2]

    base = PC.weighted_expectancy(rows)
    _log("A1 weighting: equal %.5f  contract %s  dollar %s  (median contracts %.0f)"
         % (base["equal_weighted"],
            None if base["contract_weighted"] is None else round(base["contract_weighted"], 5),
            None if base["dollar_weighted"] is None else round(base["dollar_weighted"], 5),
            base["median_contracts"]))

    floors = {}
    deltas = []
    for f in PC.O19_FLOORS:
        sub = [r for r in rows
               if r.get("entry_premium") is not None and float(r["entry_premium"]) >= f]
        w = PC.weighted_expectancy(sub)
        if not w.get("n"):
            continue
        d_pp = 100.0 * (w["equal_weighted"] - base["equal_weighted"])
        sd = np.array([str(r["alert_ts"]) for r in sub])
        pv = np.array([float(r["pnl_pct"]) for r in sub])
        ci = _ci(pv, sd)
        # the interval on the DIFFERENCE is what the rule needs; approximate it by the
        # floored subset's own interval shifted by the base mean, and say so.
        ci_pp = ([100.0 * (c - base["equal_weighted"]) for c in ci] if ci else None)
        halves = {}
        for nm, m in (("early", sd < med), ("late", sd >= med)):
            if m.sum() < 30:
                halves[nm] = None
                continue
            halves[nm] = {"n": int(m.sum()), "equal_weighted": float(pv[m].mean())}
        floors["floor_%.2f" % f] = {
            "n": w["n"], "retained": w["n"] / max(base["n"], 1),
            "equal_weighted": w["equal_weighted"],
            "contract_weighted": w["contract_weighted"],
            "dollar_weighted": w["dollar_weighted"],
            "delta_pp_vs_base": d_pp,
            "ci95_pp_of_floored_subset_shifted": ci_pp,
            "halves": halves,
        }
        deltas.append((d_pp, (ci_pp[0] if ci_pp else None), (ci_pp[1] if ci_pp else None)))
        _log("A2 floor $%.2f: n %d (%.1f%% kept) equal %.5f  delta %+.3fpp"
             % (f, w["n"], 100.0 * w["n"] / max(base["n"], 1), w["equal_weighted"], d_pp))

    verdict = PC.o19_verdict(base["equal_weighted"], base["dollar_weighted"], deltas)
    payload = {
        "item": "O19",
        "prereg": "PREREG_o11_o19_o22_o25_portfolio.md",
        "prereg_commit": "1203a85",
        "ran_before": "O11 - enforced by the main stage refusing to run without this file",
        "n": base["n"],
        "split_date": med,
        "A1_weighting": base,
        "A2_premium_floors": floors,
        "verdict": verdict,
        "rule": ("ARTEFACT iff equal- and dollar-weighted disagree in SIGN, or a floor moves "
                 "expectancy by more than 2.00pp with its interval excluding zero"),
    }
    os.makedirs(os.path.dirname(O19_OUT), exist_ok=True)
    with open(O19_OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    _log("O19 verdict: %s -> wrote %s" % (verdict, O19_OUT))
    return payload


# =============================================================================== MARKS (O11)
def build_marks(rows):
    """Daily mid marks for every banked contract, from the FREEZE (register §0.3)."""
    with gzip.open(FREEZE, "rb") as fh:
        ch = pickle.load(fh)
    ch["ds"] = ch["date"].astype(str)
    ch["es"] = ch["expiration"].astype(str)
    ch["rt"] = ch["right"].astype(str).str.upper().str[0]
    ch["K"] = ch["strike"].astype(np.float64)
    ch["mid"] = (ch["bid"].astype(np.float64) + ch["ask"].astype(np.float64)) / 2.0
    calls = ch[ch["rt"] == "C"]
    idx = {}
    for key, g in calls.groupby(["symbol", "es"], sort=False):
        idx[key] = g
    _log("freeze indexed: %d (symbol, expiry) groups" % len(idx))

    out = {}
    for i, r in enumerate(rows, 1):
        g = idx.get((r["ticker"], str(r["expiry"])))
        if g is None:
            continue
        a = str(r["alert_ts"])
        sub = g[(np.abs(g["K"] - float(r["strike"])) < 1e-6) & (g["ds"] >= a)]
        if not len(sub):
            continue
        sub = sub.sort_values("ds")
        out[(r["ticker"], a, str(r["expiry"]), float(r["strike"]))] = list(
            zip(sub["ds"].tolist(), sub["mid"].tolist()))
        if i % 1000 == 0:
            _log("marks %d/%d" % (i, len(rows)))
    return out


# =============================================================================== STAGE MAIN
def run_o11(rows, marks):
    trades = []
    for r in rows:
        k = (r["ticker"], str(r["alert_ts"]), str(r["expiry"]), float(r["strike"]))
        m = marks.get(k)
        if not m:
            continue
        held = int(r.get("held_days") or 0)
        exit_d = (dt.date.fromisoformat(str(r["alert_ts"]))
                  + dt.timedelta(days=max(held, 1))).isoformat()
        rr = dict(r)
        rr["exit_date"] = exit_d
        t = PC.long_leg_as_book_trade(rr, m)
        if t:
            trades.append(t)
    _log("O11 trades with a usable mark path: %d of %d" % (len(trades), len(rows)))
    void = len(trades) < PC.MIN_MARKED_TRADES

    dates = sorted({t["alert_ts"] for t in trades})
    med = dates[len(dates) // 2] if dates else None

    cells = {}
    saved = (V.MAX_CONCURRENT, V.INITIAL_CAPITAL)
    try:
        for cap, conc in PC.O11_CELLS:
            V.MAX_CONCURRENT = int(conc)      # the layer's cap is a module constant, not an arg
            label = "B_cap%d_conc%d" % (int(cap), int(conc))

            def sim(sub):
                if len(sub) < 50:
                    return None
                return VP.simulate_book(sub, {}, initial_capital=cap, vol_target=False)

            full = sim(trades)
            e = sim([t for t in trades if t["alert_ts"] < med])
            l = sim([t for t in trades if t["alert_ts"] >= med])

            def geom(bk):
                if not bk or "curve" not in bk:
                    return {}
                eq = [c["equity"] for c in bk["curve"]]
                return {"max_drawdown_frac": PC.max_drawdown_frac(eq),
                        **PC.drawdown_spans(eq)}

            gf, ge, gl = geom(full), geom(e), geom(l)
            cells[label] = {
                "initial_capital": cap, "concurrency_cap": conc,
                "n_taken": (full or {}).get("n_taken"),
                "n_generated": (full or {}).get("n_generated"),
                "skipped": (full or {}).get("skipped"),
                "final_equity": (full or {}).get("final_equity"),
                "total_return": (full or {}).get("total_return"),
                "cagr": (full or {}).get("cagr"),
                "sharpe": (full or {}).get("sharpe"),
                "annual_vol": (full or {}).get("annual_vol"),
                "avg_concurrent": (full or {}).get("avg_concurrent"),
                "layer_max_drawdown": (full or {}).get("max_drawdown"),
                "geometry_full": gf, "geometry_early": ge, "geometry_late": gl,
                "verdict": PC.o11_verdict(ge.get("max_drawdown_frac"),
                                          gl.get("max_drawdown_frac")),
            }
            _log("%s: taken %s/%s  maxDD %s  verdict %s"
                 % (label, cells[label]["n_taken"], cells[label]["n_generated"],
                    None if gf.get("max_drawdown_frac") is None
                    else round(gf["max_drawdown_frac"], 4), cells[label]["verdict"]))
    finally:
        V.MAX_CONCURRENT, V.INITIAL_CAPITAL = saved

    return {"n_trades_marked": len(trades), "void": bool(void), "split_date": med,
            "cells": cells,
            "note": ("MAX_CONCURRENT is a module constant in options_vrp, not a parameter of "
                     "simulate_book, so each cell sets it and the original is restored in a "
                     "finally block. MAX_CONTRACTS_PER_SPREAD=10 also binds and is disclosed.")}


def run_o22(rows, o11_taken_share):
    depths, prems = [], []
    for r in rows:
        d = r.get("pit_atm_oi_notional")
        p = r.get("entry_premium")
        if d is None or p is None:
            continue
        d = float(d)
        p = float(p)
        if d > 0 and p > 0:
            depths.append(d)
            prems.append(p)
    if not depths:
        return {"error": "no depth data"}
    pn = np.array([float(r.get("pnl_pct") or np.nan) for r in rows], float)
    edge = float(np.nanmean(pn))
    edge_bps = 1e4 * edge
    share = float(o11_taken_share)
    out = {"n_with_depth": len(depths),
           "median_depth_notional": float(np.median(depths)),
           "median_entry_premium": float(np.median(prems)),
           "gross_edge_per_trade": edge, "gross_edge_bps": edge_bps,
           "position_share_of_aum": share, "capacity_by_lambda": {}}
    for lam in PC.O22_LAMBDAS:
        cap = PC.capacity_aum(depths, edge_bps, share, lam=lam)
        out["capacity_by_lambda"]["lambda_%.1f" % lam] = cap
        _log("O22 capacity at lambda %.1f: %s" % (lam, None if cap is None else round(cap)))
    out["headline_capacity_usd"] = out["capacity_by_lambda"].get(
        "lambda_%.1f" % PC.O22_LAMBDA_HEADLINE)
    # participation profile at the headline capacity
    hc = out["headline_capacity_usd"]
    if hc:
        parts = (hc * share) / np.array(depths)
        out["at_headline"] = {
            "median_participation": float(np.median(parts)),
            "share_over_5pct": float((parts > 0.05).mean()),
            "share_over_10pct": float((parts > 0.10).mean()),
        }
    out["caveats"] = [
        "UPPER BOUND: depth comes from names that were mined, and mining selected on liquidity.",
        "lambda is an ASSUMPTION, not a measurement - P1's own caveat, and the band spans the "
        "capacity by a large factor.",
        "MECHANICAL, NOT A RECOMMENDATION: R2 shows this book's entry loses to random entry, so "
        "this answers how much it COULD hold, never how much should be deployed.",
    ]
    return out


def build_wings(rows, marks, limit=0):
    """O25: at the first crossing of +75%/+100%, sell the ~15-delta call in the same expiry.

    Chains come from the EOD cache, because the freeze holds full chains only on ENTRY dates
    (register §0.4). assert_raw_spot has already run on the price series used here.
    """
    import scripts.o6_o7_o17_earnings as EO   # reuse the indexed chain loader
    by_t = {}
    for r in rows:
        by_t.setdefault(r["ticker"], []).append(r)
    names = sorted(by_t)
    if limit:
        names = names[:limit]

    out = []
    for i, tkr in enumerate(names, 1):
        ch = EO.ticker_chain(tkr)
        if ch is None:
            continue
        spot = load_raw_close(tkr)
        by_exp = EO.calls_by_expiry(ch)
        for r in by_t[tkr]:
            k = (tkr, str(r["alert_ts"]), str(r["expiry"]), float(r["strike"]))
            m = marks.get(k)
            if not m:
                continue
            e = float(r.get("entry_premium") or 0)
            if e <= 0:
                continue
            held = int(r.get("held_days") or 0)
            exit_d = (dt.date.fromisoformat(str(r["alert_ts"]))
                      + dt.timedelta(days=max(held, 1))).isoformat()
            path = [(d, v) for d, v in m if d <= exit_d]
            if len(path) < 2:
                continue
            exit_prem = float(r.get("exit_premium") or path[-1][1])
            rec = {"ticker": tkr, "date": str(r["alert_ts"]), "expiry": str(r["expiry"]),
                   "entry_premium": e, "exit_premium": exit_prem,
                   "banked_pnl_pct": r.get("pnl_pct"), "arms": {}}
            g = by_exp.get(str(r["expiry"]))
            for th in PC.O25_THRESHOLDS:
                j = PC.first_crossing(path, e, th)
                if j is None or g is None:
                    continue
                cross_d, cross_mid = path[j]
                S = spot.get(cross_d)
                if not S or S <= 0:
                    continue
                day = g[(g["ds"] == cross_d) & (g["bid"] > 0) & (g["ask"] > 0)]
                if not len(day):
                    continue
                T = max((dt.date.fromisoformat(str(r["expiry"]))
                         - dt.date.fromisoformat(cross_d)).days, 0) / 365.0
                if T <= 0:
                    continue
                Ks = day["K"].to_numpy(np.float64)
                bids = day["bid"].to_numpy(np.float64)
                asks = day["ask"].to_numpy(np.float64)
                mids = day["mid"].to_numpy(np.float64)
                best, bi = None, None
                for q in range(len(Ks)):
                    if Ks[q] <= float(r["strike"]):
                        continue                      # the wing must be FURTHER out of the money
                    iv = BS.implied_vol(float(mids[q]), S, float(Ks[q]), T, PC.RATE, "C",
                                        q=PC.DIV_YIELD)
                    if not iv or iv <= 0:
                        continue
                    gk = BS.greeks(S, float(Ks[q]), T, PC.RATE, iv, "C", q=PC.DIV_YIELD) or {}
                    dl = gk.get("delta")
                    if dl is None or not np.isfinite(dl):
                        continue
                    gap = abs(float(dl) - PC.WING_DELTA)
                    if best is None or gap < best:
                        best, bi = gap, q
                if bi is None:
                    continue
                credit = float(bids[bi])              # sold at the BID
                # buy back at the ask on the exit date
                gx = g[(g["ds"] == exit_d) & (np.abs(g["K"] - float(Ks[bi])) < 1e-6)]
                buyback = float(gx.iloc[0]["ask"]) if len(gx) else max(0.0, credit)
                rec["arms"]["th_%.2f" % th] = {
                    "cross_date": cross_d, "cross_mid": float(cross_mid),
                    "wing_strike": float(Ks[bi]), "wing_credit": credit,
                    "wing_buyback": buyback,
                    "wing_pnl_pct": PC.wing_pnl_pct(e, exit_prem, credit, buyback),
                    "close_pnl_pct": (float(cross_mid) - e) / e,
                    "hold_pnl_pct": (exit_prem - e) / e,
                }
            if rec["arms"]:
                out.append(rec)
        if i % 20 == 0:
            _log("O25 tickers %d/%d  records %d" % (i, len(names), len(out)))
    return out


def score_o25(wings):
    res = {}
    for th in PC.O25_THRESHOLDS:
        key = "th_%.2f" % th
        recs = [w for w in wings if key in w["arms"]]
        if len(recs) < PC.MIN_CROSSINGS:
            res[key] = {"verdict": "NULL", "why": "fewer than %d crossings" % PC.MIN_CROSSINGS,
                        "n": len(recs)}
            continue
        d = np.array([w["date"] for w in recs])
        wing = np.array([w["arms"][key]["wing_pnl_pct"] for w in recs], float)
        close = np.array([w["arms"][key]["close_pnl_pct"] for w in recs], float)
        hold = np.array([w["arms"][key]["hold_pnl_pct"] for w in recs], float)
        med = sorted(set(d.tolist()))[len(set(d.tolist())) // 2]
        cells = {}
        for nm, m in (("full", np.ones(len(d), bool)), ("early", d < med), ("late", d >= med)):
            if m.sum() < 30:
                cells[nm] = None
                continue
            dc, dh = wing[m] - close[m], wing[m] - hold[m]
            cells[nm] = {
                "n": int(m.sum()),
                "wing_mean": float(wing[m].mean()),
                "close_mean": float(close[m].mean()),
                "hold_mean": float(hold[m].mean()),
                "diff_vs_close": float(dc.mean()), "ci_vs_close": _ci(dc, d[m]),
                "diff_vs_hold": float(dh.mean()), "ci_vs_hold": _ci(dh, d[m]),
                # risk side: REPORTED, NOT VERDICTED (register §3.4)
                "sd_wing": float(wing[m].std()), "sd_hold": float(hold[m].std()),
                "share_positive_wing": float((wing[m] > 0).mean()),
                "share_positive_hold": float((hold[m] > 0).mean()),
                "tail_over_100pct_wing": float((wing[m] > 1.0).mean()),
                "tail_over_100pct_hold": float((hold[m] > 1.0).mean()),
            }
        e, l = cells.get("early"), cells.get("late")
        res[key] = {"n": len(recs), "split_date": med, **cells,
                    "verdict": (PC.paired_verdict(
                        (e or {}).get("diff_vs_close"), (e or {}).get("ci_vs_close"),
                        (e or {}).get("diff_vs_hold"), (e or {}).get("ci_vs_hold"),
                        (l or {}).get("diff_vs_close"), (l or {}).get("ci_vs_close"),
                        (l or {}).get("diff_vs_hold"), (l or {}).get("ci_vs_hold"))
                        if (e and l) else "NULL")}
        _log("O25 %s: n %d  wing %+.4f close %+.4f hold %+.4f -> %s"
             % (key, len(recs), cells["full"]["wing_mean"], cells["full"]["close_mean"],
                cells["full"]["hold_mean"], res[key]["verdict"]))
    return res


def diagnostics(rows):
    """DESCRIPTIVE, no verdict, zero trial cost. Two questions the results force.

    (a) O22's depth is OPEN INTEREST, a STOCK. P1's equity capacity used ADV, a FLOW. The
        register named `pit_atm_oi_notional` because it is the only depth field banked, so the
        headline stands as registered - but the two are not the same kind of quantity and the
        capacity cannot be compared with P1's $23M without this number attached.

    (b) E8: the audit's third possibility, that alerts CLUSTER so a concurrency cap binds
        exactly when the opportunity is richest. Measured on the book alone.
    """
    out = {"note": ("descriptive, no verdict, zero trial cost; added after the arms were read "
                    "and disclosed as such. Changes no registered quantity.")}

    # (a) volume / open interest on the traded contract, from the freeze
    try:
        with gzip.open(FREEZE, "rb") as fh:
            ch = pickle.load(fh)
        ch["ds"] = ch["date"].astype(str)
        ch["es"] = ch["expiration"].astype(str)
        ch["rt"] = ch["right"].astype(str).str.upper().str[0]
        ch["K"] = ch["strike"].astype(np.float64)
        idx = {k: g for k, g in ch[ch["rt"] == "C"].groupby(["symbol", "es"], sort=False)}
        ratios = []
        for r in rows:
            g = idx.get((r["ticker"], str(r["expiry"])))
            if g is None:
                continue
            sub = g[(np.abs(g["K"] - float(r["strike"])) < 1e-6)
                    & (g["ds"] == str(r["alert_ts"]))]
            if not len(sub):
                continue
            oi = float(sub.iloc[0]["open_interest"])
            if oi > 0:
                ratios.append(float(sub.iloc[0]["volume"]) / oi)
        if ratios:
            a = np.asarray(ratios)
            out["oi_is_a_stock_volume_is_a_flow"] = {
                "n": int(a.size),
                "median_volume_over_open_interest": float(np.median(a)),
                "mean": float(a.mean()),
                "p25": float(np.percentile(a, 25)), "p75": float(np.percentile(a, 75)),
                "capacity_overstatement_factor": float(1.0 / max(np.median(a), 1e-9)),
                "why": ("O22's depth is open interest, a STOCK; P1's ADV is a FLOW. The "
                        "registered headline stands, but a flow-based capacity would be about "
                        "this factor lower, and the number is NOT comparable with P1's equity "
                        "capacity, which used a flow."),
            }
    except Exception as exc:                                   # noqa: BLE001
        out["oi_is_a_stock_volume_is_a_flow"] = {"error": "%s: %s" % (type(exc).__name__, exc)}

    # (b) do alerts cluster, and are crowded weeks the rich ones?
    weeks = {}
    for r in rows:
        p = r.get("pnl_pct")
        if p is None or not np.isfinite(float(p)):
            continue
        wk = dt.date.fromisoformat(str(r["alert_ts"])).isocalendar()
        weeks.setdefault("%04d-W%02d" % (wk[0], wk[1]), []).append(float(p))
    if weeks:
        sizes = np.array([len(v) for v in weeks.values()], float)
        means = np.array([float(np.mean(v)) for v in weeks.values()], float)
        q = np.quantile(sizes, [0.5, 0.9])
        out["alert_clustering_E8"] = {
            "n_weeks": int(sizes.size),
            "alerts_per_week_median": float(np.median(sizes)),
            "alerts_per_week_p90": float(np.percentile(sizes, 90)),
            "alerts_per_week_max": float(sizes.max()),
            "expectancy_in_quiet_weeks_at_or_below_median": float(
                np.average(means[sizes <= q[0]], weights=sizes[sizes <= q[0]])),
            "expectancy_in_busy_weeks_above_p90": float(
                np.average(means[sizes > q[1]], weights=sizes[sizes > q[1]]))
            if (sizes > q[1]).any() else None,
            "share_of_trades_in_weeks_over_10_alerts": float(
                sizes[sizes > 10].sum() / sizes.sum()),
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("o19", "main"), required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)

    rows = load_book()
    _log("split-clean book: %d closed trades, %d names"
         % (len(rows), len({r["ticker"] for r in rows})))

    if args.stage == "o19":
        stage_o19(rows)
        return 0

    # ---- §1: the main stage REFUSES to run until O19 has been written and can be read
    if not os.path.exists(O19_OUT):
        raise SystemExit(
            "REFUSING TO RUN: %s does not exist. The register (§1) fixes the order - O19 runs "
            "first, in its own pass, and is read before any O11 number exists, because O11 sizes "
            "in whole contracts and inherits whatever O19 finds. Run --stage o19 first."
            % O19_OUT)
    with open(O19_OUT, "r", encoding="utf-8") as f:
        o19 = json.load(f)
    _log("O19 read first, verdict: %s" % o19.get("verdict"))

    # ---- §2: the split guard, before any instrument touches a price
    close_by = {t: load_raw_close(t) for t in sorted({r["ticker"] for r in rows})}
    guard = PC.assert_raw_spot(rows, close_by)
    _log("assert_raw_spot PASSED: %d entries, median rel err %.2e"
         % (guard["checked"], guard["median_rel_err"]))

    if os.path.exists(MARKS_CACHE) and not args.refresh:
        with open(MARKS_CACHE, "rb") as f:
            marks = pickle.load(f)
        _log("marks cache hit: %d" % len(marks))
    else:
        marks = build_marks(rows)
        with open(MARKS_CACHE, "wb") as f:
            pickle.dump(marks, f, protocol=4)
        _log("marks built: %d" % len(marks))

    o11 = run_o11(rows, marks)

    taken = [c.get("n_taken") or 0 for c in o11["cells"].values()]
    share = 0.02
    o22 = run_o22(rows, share)

    if os.path.exists(WING_CACHE) and not args.refresh and not args.limit:
        with open(WING_CACHE, "rb") as f:
            wings = pickle.load(f)
        _log("wing cache hit: %d" % len(wings))
    else:
        wings = build_wings(rows, marks, limit=args.limit)
        if not args.limit:
            with open(WING_CACHE, "wb") as f:
                pickle.dump(wings, f, protocol=4)
        _log("wings built: %d" % len(wings))
    o25 = score_o25(wings)

    payload = {
        "item": "O11 + O19 + O22 + O25",
        "prereg": "PREREG_o11_o19_o22_o25_portfolio.md",
        "prereg_commit": "1203a85",
        "book": "state_r2_splitclean.pkl",
        "n_trades": len(rows),
        "O19_read_first": {"verdict": o19.get("verdict"), "artifact": O19_OUT,
                           "n": o19.get("n")},
        "split_spot_guard": guard,
        "O11": o11,
        "O22": o22,
        "O25": o25,
        "diagnostics_no_verdict": diagnostics(rows),
        "o_series_status": ("this batch closes the last four OPEN audit HYPOTHESIS rows in the "
                            "O-series; O14 remains OPEN as a data-collection row whose "
                            "put/call and unusual-volume studies are still undone"),
        "framing": ("R2 stands. These are CONSTRUCTION results on a book whose entry is dead: a "
                    "candidate for a future book, never evidence the alert works, never an "
                    "adoption, and O22's capacity is mechanical rather than a recommendation."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
