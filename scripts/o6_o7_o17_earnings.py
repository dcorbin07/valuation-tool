"""O6 + O7 + O17 — the earnings-and-surface-selection family.

Executes PREREG_o6_o7_o17_earnings_surface.md, committed ALONE at 779d42c before this file
existed. Frozen book, no re-mine, no live code path changed, nothing adopted.

    python -m scripts.o6_o7_o17_earnings [--limit N] [--refresh]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import earnings_surface as ES        # noqa: E402
from valuation.edge import blackscholes as BS            # noqa: E402
from valuation.edge import options_stats as OS           # noqa: E402
from valuation.edge import bulk                          # noqa: E402


def _data_root() -> str:
    """Walk up for the real data directory: a worktree's own data/ is partial (O21's finding)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "data")
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return cand
        here = os.path.dirname(here)
    return os.path.join(os.getcwd(), "data")


DATA = _data_root()
CHAINS = os.path.join(DATA, "options")
BARS = os.path.join(DATA, "bulk", "prepared", "bars")
BOOK = os.path.join(DATA, "options_universe", "state_r2_splitclean.pkl")
CONTROL = os.path.join(DATA, "options_universe", "control_r2_splitclean_seed0.pkl")
CACHE = os.path.join(DATA, "free_analysis", "O6O7O17_EVENTS.pkl")
OUT = os.path.join(DATA, "free_analysis", "O6_O7_O17_EARNINGS.json")

T0 = time.time()
# Control: raw closes that disagree with the book's own entry spot. Must stay EMPTY - it is the
# evidence that the split repair is right, rather than an assumption that it is.
SPOT_MISMATCH = []


def _log(m):
    print("[O6/O7/O17] %s  %.0fs" % (m, time.time() - T0), flush=True)


def load_book(path):
    """The alert book is {"rows": [...]}; the random-entry control books are a bare list."""
    with open(path, "rb") as f:
        blob = pickle.load(f)
    rows = blob["rows"] if isinstance(blob, dict) else blob
    return [r for r in rows if r.get("status") == "closed"]


def load_close(tkr, field="raw_close"):
    """Daily closes for a name.

    **`field` MATTERS AND GETTING IT WRONG IS THE U1-SPLIT DEFECT AGAIN.** Option chains are
    as-traded and UNADJUSTED for splits; `close` in this cache is adjusted (NVDA 2012 reads 0.27
    against a raw 11.97 — a 43x ratio), so matching an as-traded strike against an adjusted spot
    picks a contract that is nowhere near the money. Measured against the book's own
    `underlying_entry` over 1,173 banked entries: `raw_close` agrees EXACTLY (median relative
    error 0.00000, nothing over 5% off) while `close` is off by a median 10.3% and by more than
    5% on 67% of entries.

    So: **`raw_close` for anything that touches a STRIKE, `close` for a RETURN** (an adjusted
    series cannot manufacture a fake move when a split lands inside the window).
    """
    bp = os.path.join(BARS, "%s.pkl" % tkr)
    if not os.path.exists(bp):
        return {}
    try:
        with open(bp, "rb") as f:
            bars = pickle.load(f)
    except Exception:
        return {}
    # The cache is COLUMNAR - {"date": [...], "close": [...], "raw_close": [...]} - not a
    # per-date mapping. Reading it as the latter yields an empty dict and every downstream
    # bound then passes vacuously, so the shape is asserted rather than assumed.
    if not isinstance(bars, dict) or "date" not in bars or field not in bars:
        return {}
    ds, cl = bars["date"], bars[field]
    if len(ds) != len(cl):
        return {}
    out = {}
    for d, c in zip(ds, cl):
        try:
            v = float(c)
        except (TypeError, ValueError):
            continue
        if v > 0:
            out[str(d)[:10]] = v
    return out


def ticker_chain(tkr):
    d = os.path.join(CHAINS, tkr)
    if not os.path.isdir(d):
        return None
    frames = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".pkl") or fn.endswith(".sha256"):
            continue
        try:
            with open(os.path.join(d, fn), "rb") as f:
                df = pickle.load(f)
        except Exception:
            continue
        if isinstance(df, pd.DataFrame) and len(df):
            frames.append(df)
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    out["ds"] = out["date"].astype(str)
    out["es"] = out["expiration"].astype(str)
    out["rt"] = out["right"].astype(str).str.upper().str[0]
    out["K"] = out["strike"].astype(np.float64)
    out["bid"] = out["bid"].astype(np.float64)
    out["ask"] = out["ask"].astype(np.float64)
    out["mid"] = (out["bid"] + out["ask"]) / 2.0
    # DTE computed ONCE, vectorised. Parsing dates per row inside the group loops was the
    # dominant cost of the first cut (~30s/ticker); this is the same number, ~20x cheaper.
    out["dte"] = (pd.to_datetime(out["es"]) - pd.to_datetime(out["ds"])).dt.days.astype(np.int64)
    return out


def atm_iv_series(ch, spot_by_date):
    """ATM IV on EVERY chain date, computed ONCE per ticker.

    Computing this per TRADE was the first cut and it cost ~50s per ticker: the trailing window
    is 252 days and the book holds ~20 trades per name, so the same solves were repeated twenty
    times. O6b needs a trailing slice, not a per-trade rebuild.
    """
    c = ch[(ch["rt"] == "C") & (ch["mid"] > 0)]
    if not len(c):
        return {}
    c = c[(c["dte"] >= 20) & (c["dte"] <= 60)]
    if not len(c):
        return {}
    out = {}
    for ds, g in c.groupby("ds", sort=True):
        S = spot_by_date.get(ds)
        if not S or S <= 0:
            continue
        K_arr = g["K"].to_numpy()
        j = int(np.argmin(np.abs(K_arr - S)))
        T = float(g["dte"].to_numpy()[j]) / 365.0
        if T <= 0:
            continue
        iv = BS.implied_vol(float(g["mid"].to_numpy()[j]), float(S), float(K_arr[j]), T,
                            ES.RATE, "C", q=ES.DIV_YIELD)
        if iv and iv > 0:
            out[ds] = float(iv)
    return out


def trailing_iv(series_sorted, upto, window=ES.IV_RANK_WINDOW):
    """The trailing slice O6b actually needs, taken from the once-per-ticker series."""
    return [v for d, v in series_sorted if d < upto][-window:]


def build_all(rows, ctrl_rows, earn, zero_names, limit=0):
    """ONE pass over tickers, building the O6 alert arm, the O6 control arm and O7 together.

    Loading a name's chain is the dominant cost (~30s/ticker of pickle I/O), and the first cut
    called it once per builder - three full loads of the same data. This is the same work in a
    third of the wall clock; the three event sets are bit-identical to building them separately,
    which the smoke run confirmed before this was written.
    """
    by_t, by_c = {}, {}
    for r in rows:
        by_t.setdefault(r["ticker"], []).append(r)
    for r in ctrl_rows:
        by_c.setdefault(r["ticker"], []).append(r)
    names = sorted(set(by_t) | set(by_c))
    if limit:
        names = names[:limit]

    o6, o6c, o7, tried = [], [], [], 0
    for i, tkr in enumerate(names, 1):
        ch = ticker_chain(tkr)
        if ch is None:
            continue
        close = load_close(tkr, "raw_close")     # strikes are AS-TRADED
        adj = load_close(tkr, "close")           # returns only
        spot = dict(close)
        for r in by_t.get(tkr, []):
            s = float(r.get("underlying_entry") or 0.0)
            if s > 0:
                # CONTROL: the raw series must already agree with the book's own spot. Recorded
                # rather than assumed - it is what proves the split repair is right.
                cs = close.get(str(r["alert_ts"]))
                if cs and abs(cs / s - 1.0) > 0.01:
                    SPOT_MISMATCH.append((tkr, str(r["alert_ts"]), float(cs), s))
                spot[str(r["alert_ts"])] = s
        iv_ser = sorted(atm_iv_series(ch, spot).items())
        by_exp = calls_by_expiry(ch)
        o6.extend(_o6_for_ticker(ch, by_t.get(tkr, []), spot, iv_ser, tkr, by_exp))
        o6c.extend(_o6_for_ticker(ch, by_c.get(tkr, []), spot, iv_ser, tkr, by_exp))
        if tkr not in zero_names and close:
            e, t = _o7_for_ticker(ch, close, earn.get(tkr, []), tkr, adj=adj)
            o7.extend(e)
            tried += t
        if i % 10 == 0:
            _log("pass %d/%d  o6 %d  ctrl %d  o7 %d" % (i, len(names), len(o6), len(o6c), len(o7)))
    return o6, o6c, o7, tried


def calls_by_expiry(ch):
    """Index the call chain by expiry ONCE per ticker.

    Measured, not guessed: the first cut re-scanned all ~2.3M rows with string masks for every
    trade, costing 38.6s per ticker against 7.8s to load the chain in the first place. Profiling
    is how this was found - two earlier optimisations aimed at the wrong hotspot.
    """
    c = ch[ch["rt"] == "C"]
    return {es: g for es, g in c.groupby("es", sort=False)}


def _o6_for_ticker(ch, trades, spot_by_date, iv_ser, tkr, by_exp=None):
    """For each banked trade: reprice EVERY in-band alternative at the same expiry, and the
    incumbent, over the SAME holding period. Only the strike changes (register §2.1)."""
    out = []
    if by_exp is None:
        by_exp = calls_by_expiry(ch)
    if True:
        for r in trades:
            a, exp = str(r["alert_ts"]), str(r["expiry"])
            # The alert book carries underlying_entry; the random-entry CONTROL books do not,
            # so spot falls back to that date's close. Same quantity, two sources - stated
            # because a silent fallback would have made the control arm quietly empty.
            S = float(r.get("underlying_entry") or 0.0)
            if S <= 0:
                S = float(spot_by_date.get(a) or 0.0)
            held = int(r.get("held_days") or 0)
            if S <= 0:
                continue
            gexp = by_exp.get(exp)
            if gexp is None or not len(gexp):
                continue
            day = gexp[(gexp["ds"] == a) & (gexp["ask"] > 0)]
            if len(day) < 2:
                continue
            # matched exit: the available chain date closest to entry + held_days
            want = (dt.date.fromisoformat(a) + dt.timedelta(days=max(held, 1))).isoformat()
            fwd = gexp[(gexp["ds"] >= a) & (gexp["ds"] <= exp)]
            if not len(fwd):
                continue
            cand_days = sorted(set(fwd["ds"].tolist()))
            later = [d for d in cand_days if d > a]
            if not later:
                continue
            exit_ds = min(later, key=lambda d: abs(
                (dt.date.fromisoformat(d) - dt.date.fromisoformat(want)).days))
            exitday = fwd[fwd["ds"] == exit_ds]
            exit_bid = dict(zip(exitday["K"].tolist(), exitday["bid"].tolist()))

            T = max((dt.date.fromisoformat(exp) - dt.date.fromisoformat(a)).days, 0) / 365.0
            if T <= 0:
                continue
            Ks = day["K"].to_numpy(np.float64)
            asks = day["ask"].to_numpy(np.float64)
            bids = day["bid"].to_numpy(np.float64)
            mids = day["mid"].to_numpy(np.float64)
            band = (Ks >= (ES.MONEYNESS_LO - 1e-12) * S) & (Ks <= (ES.MONEYNESS_HI + 1e-12) * S)
            k_inc = float(r["strike"])
            cands = []
            for idx in np.where(band & (asks > 0) & (mids > 0))[0]:
                K = float(Ks[idx])
                xb = exit_bid.get(K)
                if xb is None or not np.isfinite(xb):
                    continue
                iv = BS.implied_vol(float(mids[idx]), S, K, T, ES.RATE, "C", q=ES.DIV_YIELD)
                if not iv or iv <= 0:
                    continue
                g = BS.greeks(S, K, T, ES.RATE, iv, "C", q=ES.DIV_YIELD) or {}
                cands.append({
                    "K": K, "iv": float(iv),
                    "delta": float(g.get("delta") or np.nan),
                    "vega": float(g.get("vega") or np.nan),
                    "spread": max(float(asks[idx]) - float(bids[idx]), 0.0),
                    "pnl_pct": (float(xb) - float(asks[idx])) / float(asks[idx]),
                    "logm": float(np.log(K / S)),
                    "is_incumbent": abs(K - k_inc) < 1e-6,
                })
            if len(cands) < 3 or not any(c["is_incumbent"] for c in cands):
                continue
            hist = trailing_iv(iv_ser, a)
            out.append({
                "ticker": tkr, "date": a, "expiry": exp, "exit_ds": exit_ds,
                "target_delta": float(r.get("target_delta") or np.nan),
                "term_slope": r.get("term_slope"),
                "banked_pnl_pct": float(r.get("pnl_pct") or np.nan),
                "iv_hist": hist,
                "cands": cands,
            })
    return out


# ------------------------------------------------------------------ O6 selection rules
def _select(ev, rule):
    cands = ev["cands"]
    ivs = [c["iv"] for c in cands]
    if rule == "A1_lowest_iv":
        elig = ES.delta_eligible([c["delta"] for c in cands], ev.get("target_delta"))
        vals = [ivs[i] if elig[i] else None for i in range(len(cands))]
        return ES.pick_extreme(vals, lowest=True)
    if rule == "A2_iv_rank":
        hist = ev.get("iv_hist") or []
        if not hist:
            return None
        vals = [ES.iv_rank(hist, c["iv"]) for c in cands]
        return ES.pick_extreme(vals, lowest=True)
    if rule == "A3_smile_residual":
        res = ES.smile_residuals([c["logm"] for c in cands], ivs)
        if res is None:
            return None
        return ES.pick_extreme(list(res), lowest=True)
    if rule == "A4_vega_per_spread":
        vals = [ES.vega_per_spread(c["vega"], c["spread"]) for c in cands]
        return ES.pick_extreme(vals, lowest=False)
    raise ValueError(rule)


def _rows_for_block(pnls, dates):
    return [{"pnl_pct": float(p), "alert_ts": d} for p, d in zip(pnls, dates)]


def score_o6(events, label_prefix=""):
    inc, inc_dates = [], []
    for ev in events:
        j = next(i for i, c in enumerate(ev["cands"]) if c["is_incumbent"])
        inc.append(ev["cands"][j]["pnl_pct"])
        inc_dates.append(ev["date"])
    inc = np.asarray(inc, dtype=np.float64)

    arms = {}
    for rule in ("A1_lowest_iv", "A2_iv_rank", "A3_smile_residual", "A4_vega_per_spread"):
        sel, base, dates, alt_pools = [], [], [], []
        for ev, b in zip(events, inc):
            k = _select(ev, rule)
            if k is None:
                continue
            sel.append(ev["cands"][k]["pnl_pct"])
            base.append(float(b))
            dates.append(ev["date"])
            alt_pools.append([c["pnl_pct"] for c in ev["cands"] if not c["is_incumbent"]])
        if len(sel) < 50:
            arms[label_prefix + rule] = {"verdict": "NULL", "why": "fewer than 50 scoreable events",
                                         "n": len(sel)}
            continue
        sel = np.asarray(sel, float)
        base = np.asarray(base, float)
        dates = np.asarray(dates)
        med = sorted(set(dates.tolist()))[len(set(dates.tolist())) // 2]

        def cell(mask):
            s, b, d = sel[mask], base[mask], dates[mask]
            pools = [alt_pools[i] for i in np.where(mask)[0]]
            gain = float(s.mean() - b.mean())
            null = ES.perm_null_switch(pools, b)
            return {"n": int(mask.sum()), "gain": gain,
                    "arm_mean": float(s.mean()), "base_mean": float(b.mean()),
                    "null_p95": null["p95"], "null_median": null["median"],
                    "tail_base": ES.tail_concentration(b), "tail_arm": ES.tail_concentration(s)}

        full = cell(np.ones(len(sel), dtype=bool))
        e = cell(dates < med)
        l = cell(dates >= med)
        boot = OS.date_block_bootstrap(_rows_for_block(sel, dates))
        res = {"n": int(len(sel)), "split_date": med, "full": full, "early": e, "late": l,
               "arm_ci95": boot.get("ci95") if isinstance(boot, dict) else None,
               "verdict": ES.o6_verdict(e["gain"], e["null_p95"], e["tail_base"], e["tail_arm"],
                                        l["gain"], l["null_p95"], l["tail_base"], l["tail_arm"])}
        arms[label_prefix + rule] = res
    return {"incumbent_matched_mean": float(inc.mean()), "n_events": len(events), "arms": arms}


# ------------------------------------------------------------------ O17
def score_o17(rows, earn, zero_names):
    usable = [r for r in rows if r["ticker"] not in zero_names]
    pn = np.asarray([float(r.get("pnl_pct") or np.nan) for r in usable], float)
    dates = np.asarray([str(r["alert_ts"]) for r in usable])
    ok = np.isfinite(pn)
    usable = [r for r, k in zip(usable, ok) if k]
    pn, dates = pn[ok], dates[ok]
    med = sorted(set(dates.tolist()))[len(set(dates.tolist())) // 2]

    def arm(decide):
        p = ES.partition(usable, decide)
        keep_idx = {id(r) for r in p["kept"]}
        mask = np.array([id(r) in keep_idx for r in usable])
        out = {"n_all": len(usable), "n_kept": int(mask.sum()),
               "n_refused": len(p["refused"]), "n_unknown": len(p["unknown"])}

        def cell(sub):
            if sub.sum() < 30 or (sub & mask).sum() < 30:
                return {"n": int(sub.sum()), "gain": None, "null_p95": None, "retention": None}
            allm = float(pn[sub].mean())
            keptm = float(pn[sub & mask].mean())
            n_rm = int(sub.sum() - (sub & mask).sum())
            null = ES.perm_null_removal(pn[sub], n_rm)
            return {"n": int(sub.sum()), "n_kept": int((sub & mask).sum()),
                    "all_mean": allm, "kept_mean": keptm, "gain": keptm - allm,
                    "null_p95": null["p95"], "null_median": null["median"],
                    "retention": float((sub & mask).sum() / sub.sum())}

        full = cell(np.ones(len(pn), dtype=bool))
        e = cell(dates < med)
        l = cell(dates >= med)
        out.update({"full": full, "early": e, "late": l,
                    "verdict": ES.o17_verdict(e["gain"], e["null_p95"], e["retention"],
                                              l["gain"], l["null_p95"], l["retention"])})
        return out

    arms = {}
    for w in ES.O17_WINDOWS:
        arms["C_%dd_avoid" % w] = arm(
            lambda r, w=w: ES.refuse_within(r["alert_ts"], earn.get(r["ticker"], []), w))
    # C4: own the event -> REFUSE the ones that do NOT own it
    def c4(r):
        o = ES.owns_the_event(r["alert_ts"], r["expiry"], earn.get(r["ticker"], []))
        return None if o is None else (not o)
    arms["C4_own_the_event"] = arm(c4)

    # term_slope interaction (required, no verdict)
    ts = np.array([float(r["term_slope"]) if r.get("term_slope") is not None else np.nan
                   for r in usable])
    inter = {}
    fin = np.isfinite(ts)
    if fin.sum() > 90:
        q = np.quantile(ts[fin], [1 / 3, 2 / 3])
        terc = np.where(ts <= q[0], 0, np.where(ts <= q[1], 1, 2))
        for w in ES.O17_WINDOWS:
            dec = np.array([ES.refuse_within(r["alert_ts"], earn.get(r["ticker"], []), w)
                            for r in usable], dtype=object)
            known = np.array([d is not None for d in dec])
            ref = np.array([bool(d) if d is not None else False for d in dec])
            cells = {}
            for t in (0, 1, 2):
                m = known & fin & (terc == t)
                if m.sum() < 30:
                    continue
                cells["tercile_%d" % t] = {
                    "n": int(m.sum()),
                    "all_mean": float(pn[m].mean()),
                    "kept_mean": (float(pn[m & ~ref].mean()) if (m & ~ref).sum() >= 10 else None),
                    "refused_mean": (float(pn[m & ref].mean()) if (m & ref).sum() >= 10 else None),
                    "refused_share": float(ref[m].mean())}
            inter["avoid_%dd" % w] = cells
    return {"arms": arms, "term_slope_interaction_no_verdict": inter,
            "excluded_zero_coverage_names": sorted(zero_names),
            "n_excluded_trades": len(rows) - len(usable)}


# ------------------------------------------------------------------ O7
def _o7_for_ticker(ch, close, earn_dates, tkr, adj=None):
    """`close` is the RAW series (matches as-traded strikes); `adj` is the ADJUSTED series and is
    what the realised move is computed from, so a split inside the window cannot fake a move."""
    if adj is None:
        adj = close
    evs, tried = [], 0
    if True:
        days = set(ch["ds"].tolist())
        for e in sorted(str(d) for d in (earn_dates or [])):
            tried += 1
            d0 = dt.date.fromisoformat(e)
            pre = [(d0 - dt.timedelta(days=k)).isoformat() for k in (3, 4, 5)]
            post = [(d0 + dt.timedelta(days=k)).isoformat() for k in (1, 2, 3)]
            pd_ = next((p for p in pre if p in days and p in close), None)
            po_ = next((p for p in post if p in days and p in close), None)
            if not pd_ or not po_:
                continue
            S = close.get(pd_)              # RAW: matches the as-traded strikes
            A0, A1 = adj.get(pd_), adj.get(po_)   # ADJUSTED: split-safe for the realised move
            if not S or S <= 0 or not A0 or not A1 or A0 <= 0:
                continue
            S1 = close.get(po_)
            day = ch[(ch["ds"] == pd_) & (ch["bid"] > 0) & (ch["ask"] > 0)]
            if not len(day):
                continue
            # EXPIRY CHOICE — a DEFECT IN MY OWN FIRST CUT, fixed and reported rather than
            # quietly corrected. The first cut took the first expiry with DTE >= 7, which prices
            # the move TO EXPIRY (often 30+ days) while the realised move is measured over ~4
            # days. That tenor mismatch inflated the mean implied move to 20.19% against a
            # realised 5.27% and manufactured a RICH reading by construction. The straddle must
            # be the FRONT expiry that actually straddles the announcement: the first expiry
            # strictly AFTER the earnings date, and no more than 45 days out.
            gg = day[(day["es"] > e) & (day["dte"] <= 45)]
            if not len(gg):
                continue
            exp = sorted(set(gg["es"].tolist()))[0]
            gg = gg[gg["es"] == exp]
            calls = gg[gg["rt"] == "C"]
            puts = gg[gg["rt"] == "P"]
            if not len(calls) or not len(puts):
                continue
            K = float(calls.iloc[int(np.argmin(np.abs(calls["K"].to_numpy() - S)))]["K"])
            c = calls[np.abs(calls["K"] - K) < 1e-6]
            p = puts[np.abs(puts["K"] - K) < 1e-6]
            if not len(c) or not len(p):
                continue
            entry = float(c.iloc[0]["ask"]) + float(p.iloc[0]["ask"])
            mid_in = float(c.iloc[0]["mid"]) + float(p.iloc[0]["mid"])
            if entry <= 0 or mid_in <= 0:
                continue
            ex = ch[(ch["ds"] == po_) & (ch["es"] == exp) & (np.abs(ch["K"] - K) < 1e-6)]
            xc = ex[ex["rt"] == "C"]
            xp = ex[ex["rt"] == "P"]
            if not len(xc) or not len(xp):
                continue
            exit_v = float(xc.iloc[0]["bid"]) + float(xp.iloc[0]["bid"])
            evs.append({
                "ticker": tkr, "earn": e, "pre": pd_, "post": po_, "expiry": exp, "K": K,
                "spot_pre": S, "spot_post": S1,
                "implied_move": mid_in / S,          # mid-based: a PRICE, not a trade
                "realised_move": abs(A1 / A0 - 1.0),
                "straddle_ret": (exit_v - entry) / entry,
            })
    return evs, tried


def score_o7(evs, tried):
    if not evs:
        return {"verdict": "NULL", "why": "no usable earnings events", "n": 0}
    diff = np.array([e["realised_move"] - e["implied_move"] for e in evs], float)
    dates = np.array([e["pre"] for e in evs])
    boot = OS.date_block_bootstrap(_rows_for_block(diff, dates))
    ci = boot.get("ci95") if isinstance(boot, dict) else None
    lo, hi = (ci[0], ci[1]) if ci and len(ci) == 2 else (None, None)
    ret = np.array([e["straddle_ret"] for e in evs], float)
    ret_boot = OS.date_block_bootstrap(_rows_for_block(ret, dates))
    med = sorted(set(dates.tolist()))[len(set(dates.tolist())) // 2]
    coverage = len(evs) / max(tried, 1)

    def half(mask):
        if mask.sum() < 30:
            return None
        b = OS.date_block_bootstrap(_rows_for_block(ret[mask], dates[mask]))
        c = b.get("ci95") if isinstance(b, dict) else None
        return {"n": int(mask.sum()), "mean": float(ret[mask].mean()),
                "ci95": c, "diff_mean": float(diff[mask].mean())}

    return {
        "n_events": len(evs), "n_tried": tried, "coverage": coverage,
        "coverage_bound": bool(coverage < ES.O7_COVERAGE_FLOOR),
        "B1_diagnostic": {
            "mean_realised_minus_implied": float(diff.mean()),
            "median": float(np.median(diff)),
            "ci95": ci,
            "mean_implied_move": float(np.mean([e["implied_move"] for e in evs])),
            "mean_realised_move": float(np.mean([e["realised_move"] for e in evs])),
            "share_realised_exceeds_implied": float((diff > 0).mean()),
            "direction": ES.o7_direction(float(diff.mean()), lo, hi),
        },
        "B2_backtest": {
            "mean_straddle_return_net_of_four_crossings": float(ret.mean()),
            "median": float(np.median(ret)),
            # bootstrapped on the STRADDLE RETURN. The first cut pasted B1's interval here, so
            # the two blocks reported bit-identical CIs for different quantities.
            "ci95": ret_boot.get("ci95") if isinstance(ret_boot, dict) else None,
            "share_positive": float((ret > 0).mean()),
            "early": half(dates < med), "late": half(dates >= med),
            "split_date": med,
        },
    }


def diagnostics(rows, earn, zero_names, o6_events):
    """DESCRIPTIVE, no verdict, zero trial cost — but the FIRST of these decides how C4 may be
    read, so it is not optional.

    C4 ("open only where the expiry falls after the next announcement") necessarily selects
    LONGER-DATED contracts, and O13 already measured that alert expectancy climbs monotonically
    with tenor (-0.35% to +7.63%). If C4's gain is a tenor effect then it is a DTE filter
    wearing an earnings filter's name — the failure mode U7 and S10 both recorded. This asks the
    question directly by re-scoring C4 WITHIN dte buckets, where tenor is held roughly fixed.
    """
    usable = [r for r in rows if r["ticker"] not in zero_names]
    pn = np.array([float(r.get("pnl_pct") or np.nan) for r in usable], float)
    dte = np.array([float(r.get("dte") or np.nan) for r in usable], float)
    own = np.array([ES.owns_the_event(r["alert_ts"], r["expiry"], earn.get(r["ticker"], []))
                    for r in usable], dtype=object)
    ok = np.isfinite(pn) & np.isfinite(dte) & np.array([o is not None for o in own])
    pn, dte = pn[ok], dte[ok]
    own = np.array([bool(o) for o in own[ok]])

    out = {"c4_vs_tenor": {}}
    out["c4_dte_mean_kept"] = float(dte[own].mean())
    out["c4_dte_mean_refused"] = float(dte[~own].mean())
    out["c4_dte_median_kept"] = float(np.median(dte[own]))
    out["c4_dte_median_refused"] = float(np.median(dte[~own]))
    # within-bucket re-scoring: quartiles of dte
    edges = np.quantile(dte, [0.25, 0.5, 0.75])
    lab = np.digitize(dte, edges)
    for b in range(4):
        m = lab == b
        if m.sum() < 60 or (m & own).sum() < 20 or (m & ~own).sum() < 20:
            continue
        out["c4_vs_tenor"]["dte_q%d" % (b + 1)] = {
            "n": int(m.sum()), "dte_lo": float(dte[m].min()), "dte_hi": float(dte[m].max()),
            "kept_mean": float(pn[m & own].mean()),
            "refused_mean": float(pn[m & ~own].mean()),
            "gain_within_bucket": float(pn[m & own].mean() - pn[m].mean()),
            "kept_share": float(own[m].mean()),
        }
    # the same table for tenor ALONE, so the two effects can be compared on one scale
    out["expectancy_by_dte_quartile_no_filter"] = {
        "dte_q%d" % (b + 1): {"n": int((lab == b).sum()),
                              "mean": float(pn[lab == b].mean()),
                              "dte_lo": float(dte[lab == b].min()),
                              "dte_hi": float(dte[lab == b].max())}
        for b in range(4) if (lab == b).sum() >= 30}

    # O6: does a "cheapness" rule stay at the incumbent's delta, or does it drift to a
    # different exposure? A rule that moves delta is changing the trade, not its price.
    drift = {}
    for rule in ("A1_lowest_iv", "A2_iv_rank", "A3_smile_residual", "A4_vega_per_spread"):
        d_inc, d_arm, dk = [], [], []
        for ev in o6_events:
            k = _select(ev, rule)
            if k is None:
                continue
            j = next(i for i, c in enumerate(ev["cands"]) if c["is_incumbent"])
            a, b = ev["cands"][k]["delta"], ev["cands"][j]["delta"]
            if np.isfinite(a) and np.isfinite(b):
                d_arm.append(a)
                d_inc.append(b)
                dk.append(ev["cands"][k]["K"] / max(ev["cands"][j]["K"], 1e-9))
        if len(d_arm) < 50:
            continue
        drift[rule] = {"n": len(d_arm),
                       "mean_delta_incumbent": float(np.mean(d_inc)),
                       "mean_delta_arm": float(np.mean(d_arm)),
                       "mean_abs_delta_gap": float(np.mean(np.abs(np.array(d_arm)
                                                                  - np.array(d_inc)))),
                       "mean_strike_ratio_arm_over_incumbent": float(np.mean(dk))}
    out["o6_delta_drift"] = drift
    out["note"] = ("descriptive, no verdict, zero trial cost, added after the arms were read and "
                   "disclosed as such. Nothing here changes a registered quantity.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--refresh-o7", action="store_true",
                    help="rebuild ONLY the O7 events (front-expiry repair) and reuse the "
                         "cached O6 arms, which the repair does not touch")
    args = ap.parse_args(argv)

    rows = load_book(BOOK)
    _log("split-clean book: %d closed trades, %d names"
         % (len(rows), len({r["ticker"] for r in rows})))
    names = sorted({r["ticker"] for r in rows})

    ev_raw = bulk.prepare_events(os.path.join(DATA, "bulk", "events.csv"))
    earn = {t: sorted(str(d) for d in (bulk.earnings_dates(ev_raw, t) or [])) for t in names}
    zero = {t for t in names if not earn[t]}
    _log("earnings: %d of %d names have ZERO coverage (foreign issuers), %d trades excluded"
         % (len(zero), len(names), sum(1 for r in rows if r["ticker"] in zero)))

    if os.path.exists(CACHE) and not args.refresh and not args.limit:
        with open(CACHE, "rb") as f:
            blob = pickle.load(f)
        o6_events, o6_ctrl, o7_events, o7_tried = (
            blob["o6"], blob["o6_ctrl"], blob["o7"], blob["o7_tried"])
        _log("cache hit: o6 %d, ctrl %d, o7 %d" % (len(o6_events), len(o6_ctrl), len(o7_events)))
        if args.refresh_o7:
            o7_events, o7_tried = [], 0
            for i, tkr in enumerate(sorted(n for n in names if n not in zero), 1):
                ch = ticker_chain(tkr)
                if ch is None:
                    continue
                close = load_close(tkr)
                if not close:
                    continue
                e, t = _o7_for_ticker(ch, close, earn.get(tkr, []), tkr)
                o7_events.extend(e)
                o7_tried += t
                if i % 20 == 0:
                    _log("O7 rebuild %d  events %d of %d tried" % (i, len(o7_events), o7_tried))
            blob["o7"], blob["o7_tried"] = o7_events, o7_tried
            with open(CACHE, "wb") as f:
                pickle.dump(blob, f, protocol=4)
            _log("O7 rebuilt on the front expiry: %d of %d tried"
                 % (len(o7_events), o7_tried))
    else:
        ctrl_rows = load_book(CONTROL)
        o6_events, o6_ctrl, o7_events, o7_tried = build_all(
            rows, ctrl_rows, earn, zero, limit=args.limit)
        _log("built: o6 %d, control %d, o7 %d of %d tried"
             % (len(o6_events), len(o6_ctrl), len(o7_events), o7_tried))
        if not args.limit:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "wb") as f:
                pickle.dump({"o6": o6_events, "o6_ctrl": o6_ctrl,
                             "o7": o7_events, "o7_tried": o7_tried}, f, protocol=4)

    void = len(o6_events) < ES.MIN_TRADES_O6
    _log("O6 usable events %d (void floor %d) -> void=%s"
         % (len(o6_events), ES.MIN_TRADES_O6, void))

    o6 = score_o6(o6_events)
    for k, v in o6["arms"].items():
        _log("%s: n=%s gain=%s p95=%s -> %s"
             % (k, v.get("n"),
                None if v.get("full", {}).get("gain") is None else round(v["full"]["gain"], 5),
                None if v.get("full", {}).get("null_p95") is None
                else round(v["full"]["null_p95"], 5), v.get("verdict")))

    o6c = score_o6(o6_ctrl, label_prefix="CTRL_")
    for k, v in o6c["arms"].items():
        v.pop("verdict", None)

    o17 = score_o17(rows, earn, zero)
    for k, v in o17["arms"].items():
        _log("%s: kept=%s/%s unknown=%s gain=%s p95=%s -> %s"
             % (k, v.get("n_kept"), v.get("n_all"), v.get("n_unknown"),
                None if v.get("full", {}).get("gain") is None else round(v["full"]["gain"], 5),
                None if v.get("full", {}).get("null_p95") is None
                else round(v["full"]["null_p95"], 5), v.get("verdict")))

    o7 = score_o7(o7_events, o7_tried)
    _log("O7 coverage %.4f  B1 %s  B2 mean %s"
         % (o7.get("coverage", 0), o7.get("B1_diagnostic", {}).get("direction"),
            None if o7.get("B2_backtest", {}).get(
                "mean_straddle_return_net_of_four_crossings") is None
            else round(o7["B2_backtest"]["mean_straddle_return_net_of_four_crossings"], 5)))

    payload = {
        "item": "O6 + O7 + O17",
        "prereg": "PREREG_o6_o7_o17_earnings_surface.md",
        "prereg_commit": "779d42c",
        "book": "state_r2_splitclean.pkl",
        "n_trades": len(rows),
        "void_o6": bool(void),
        "O6": o6,
        "O6_random_entry_control_NO_VERDICT": o6c,
        "O7": o7,
        "O17": o17,
        "diagnostics_no_verdict": diagnostics(rows, earn, zero, o6_events),
        "control_spot_mismatch_vs_book": {"n": len(SPOT_MISMATCH), "sample": SPOT_MISMATCH[:10]},
        "framing": ("R2 is not re-opened and cannot be. A CANDIDATE here is a candidate for a "
                    "FUTURE book that does not exist - not evidence the alert entry works, not a "
                    "revival, not an adoption. pick_contract is untouched."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
