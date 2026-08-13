"""O14 — the tick-flow signal studies. The last open row in the O-series.

Executes PREREG_o14_tickflow_signals.md, committed ALONE at ea48f6b before this file existed.
Frozen book, no re-mine, no live code path changed, nothing adopted.

    python -m scripts.o14_tickflow_signals [--limit N] [--refresh]
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

from valuation.edge import tickflow_signals as TS      # noqa: E402
from valuation.edge import surface_xsec as SX          # noqa: E402
from valuation.edge import tickflow as TF              # noqa: E402


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
TICKS = os.path.join(DATA, "options_ticks")
CHAINS = os.path.join(DATA, "options")
CACHE = os.path.join(DATA, "free_analysis", "O14_FEATURES.pkl")
OUT = os.path.join(DATA, "free_analysis", "O14_TICKFLOW_SIGNALS.json")

T0 = time.time()


def _log(m):
    print("[O14] %s  %.0fs" % (m, time.time() - T0), flush=True)


def load_book():
    with open(BOOK, "rb") as f:
        blob = pickle.load(f)
    rows = blob["rows"] if isinstance(blob, dict) else blob
    return [r for r in rows if r.get("status") == "closed"]


def tick_path(tkr, day):
    return os.path.join(TICKS, tkr, "%s-%s.pkl" % (tkr, day))


def day_features(tkr, day, traded=None):
    """The four tick-derived features for one alert-day's whole chain.

    `traded` is (expiry, strike) for the contract the book actually bought, used ONLY by the
    look-ahead control: the last prevailing ask on THAT contract is what `entry_premium` should
    match. The first cut took the last ask of whatever contract printed last anywhere in the
    chain, which compared the traded contract's premium against an unrelated instrument and read
    a median relative error of 1.57 - a control measuring the wrong thing is worse than none.
    """
    p = tick_path(tkr, day)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            blob = pickle.load(f)
    except Exception:
        return None
    df = blob.get("rows")
    if not isinstance(df, pd.DataFrame) or not len(df):
        return None

    # eligibility: single-leg condition codes, imported from session 26 rather than restated
    cond = df["condition"].to_numpy()
    elig = np.isin(cond, np.asarray(TF.SINGLE_LEG_CODES))
    if not elig.any():
        return None
    d = df.loc[elig]
    if len(d) < 20:
        return None

    price = d["price"].to_numpy(np.float64)
    bid = d["bid"].to_numpy(np.float64)
    ask = d["ask"].to_numpy(np.float64)
    size = d["size"].to_numpy(np.float64)
    right = d["right"].astype(str).to_numpy()
    exch = d["exchange"].to_numpy()
    strike = d["strike"].to_numpy(np.float64)
    expiry = d["expiration"].astype(str).to_numpy()
    cid = np.array(["%s|%s|%s" % (e, k, r) for e, k, r in zip(expiry, strike, right)])
    ts = pd.to_datetime(d["trade_timestamp"], utc=True, errors="coerce")
    tms = (ts.astype("int64") // 10 ** 6).to_numpy(np.float64)

    # Lee-Ready is applied PER CONTRACT in time order: the tick test compares against the
    # previous different price in the SAME contract, so classifying across the whole chain at
    # once would compare a call print against an unrelated put print.
    # ONE lexsort by (contract, time) and contiguous group slices. Masking the whole array once
    # per contract was O(contracts x prints) - 565 x 32k on one AAPL day - and dominated the run.
    sides = np.zeros(len(d), dtype=np.int8)
    _u, codes = np.unique(cid, return_inverse=True)
    order = np.lexsort((tms, codes))
    gc = codes[order]
    bounds = np.flatnonzero(np.r_[True, gc[1:] != gc[:-1], True])
    for gi in range(bounds.size - 1):
        idx = order[bounds[gi]:bounds[gi + 1]]
        if idx.size:
            sides[idx] = TS.classify_side(price[idx], bid[idx], ask[idx])
    order = np.argsort(tms, kind="stable")

    n_class = int((sides != 0).sum())
    return {
        "n_prints": int(len(d)),
        "n_classified": n_class,
        "classified_rate": n_class / max(len(d), 1),
        "signed_volume": TS.signed_volume(sides, size),
        "pc_flow_imbalance": TS.pc_flow_imbalance(sides, size, price, right),
        "sweep_share": TS.sweep_share(sides, size, price, cid, tms, exch),
        "block_share": TS.block_share(sides, size, price, cid),
        # control for §0.5: the last prevailing ask on the CONTRACT THE BOOK BOUGHT
        "last_ask": _last_ask_of_traded(traded, expiry, strike, right, ask, order),
    }


def _last_ask_of_traded(traded, expiry, strike, right, ask, order):
    if not traded:
        return None
    exp, k = traded
    m = (expiry == str(exp)) & (np.abs(strike - float(k)) < 1e-6) & (right == "C")
    idx = [i for i in order if m[i]]
    if not idx:
        return None
    return float(ask[idx[-1]])


def unusual_volume_for(tkr, row, chain_cache):
    """A5 from the EOD chain: alert-day volume over the contract's trailing 20-session median."""
    ch = chain_cache.get(tkr, "MISS")
    if ch is None:
        return None
    if isinstance(ch, str):
        import scripts.o6_o7_o17_earnings as EO
        ch = EO.ticker_chain(tkr)
        chain_cache[tkr] = ch
        if ch is None:
            return None
    a = str(row["alert_ts"])
    m = ((ch["es"] == str(row["expiry"])) & (np.abs(ch["K"] - float(row["strike"])) < 1e-6)
         & (ch["rt"] == "C") & (ch["ds"] <= a))
    sub = ch.loc[m]
    if not len(sub) or "volume" not in sub.columns:
        return None
    sub = sub.sort_values("ds")
    vols = sub["volume"].to_numpy(np.float64)
    if len(vols) < 6 or str(sub["ds"].iloc[-1]) != a:
        return None
    return TS.unusual_volume(vols[-1], vols[:-1].tolist())


def build(rows, limit=0):
    by_t = {}
    for r in rows:
        by_t.setdefault(r["ticker"], []).append(r)
    names = sorted(by_t)
    if limit:
        names = names[:limit]
    chain_cache = {}
    out, missing = [], []
    for i, tkr in enumerate(names, 1):
        for r in by_t[tkr]:
            day = str(r["alert_ts"])
            f = day_features(tkr, day, traded=(str(r["expiry"]), float(r["strike"])))
            if f is None:
                missing.append((tkr, day))
                continue
            f = dict(f)
            f["unusual_volume"] = unusual_volume_for(tkr, r, chain_cache)
            f.update({"ticker": tkr, "date": day, "month": day[:7],
                      "pnl_pct": r.get("pnl_pct"),
                      "entry_premium": r.get("entry_premium")})
            out.append(f)
        chain_cache[tkr] = None          # free the chain, keep the miss marker semantics
        if i % 10 == 0:
            _log("tickers %d/%d  rows %d  missing %d" % (i, len(names), len(out), len(missing)))
    return out, missing


def score_arm(recs, key):
    good = [r for r in recs
            if r.get(key) is not None and np.isfinite(float(r[key]))
            and r.get("pnl_pct") is not None and np.isfinite(float(r["pnl_pct"]))]
    if len(good) < 200:
        return {"verdict": "NULL", "why": "fewer than 200 usable rows", "n": len(good)}
    vals = np.array([float(r[key]) for r in good], float)
    rets = np.array([float(r["pnl_pct"]) for r in good], float)
    months = np.array([r["month"] for r in good])

    lab = SX.quintiles_within_date(vals, months)
    days, ls, q = SX.long_short_series(rets, lab, months)
    if not len(days):
        return {"verdict": "NULL", "why": "no month carried both a Q1 and a Q5", "n": len(good)}
    full = SX.month_block_t(ls, days)
    null = TS.perm_null_abs_t(rets, lab, months)
    t_full = full.get("t")

    med = sorted(set(months.tolist()))[len(set(months.tolist())) // 2]
    halves = {}
    for nm, m in (("early", months < med), ("late", months >= med)):
        if m.sum() < 100:
            halves[nm] = None
            continue
        l2 = SX.quintiles_within_date(vals[m], months[m])
        d2, ls2, _ = SX.long_short_series(rets[m], l2, months[m])
        st = SX.month_block_t(ls2, d2)
        nl = TS.perm_null_abs_t(rets[m], l2, months[m], draws=400)
        halves[nm] = {"n": int(m.sum()), "n_months": len(d2),
                      "ls_mean": st.get("mean"), "t": st.get("t"),
                      "abs_t": None if st.get("t") is None else abs(float(st["t"])),
                      "null_p95_abs_t": nl.get("p95")}
    return {
        "n": len(good), "n_months": len(days), "split_month": med,
        "quintile_means": [float(np.nanmean(q[:, j])) for j in range(q.shape[1])],
        "ls_mean": full.get("mean"), "t": t_full,
        "abs_t": None if t_full is None else abs(float(t_full)),
        "ci95": full.get("ci95"),
        "null_p95_abs_t": null.get("p95"), "null_median_abs_t": null.get("median"),
        "halves": halves,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)

    rows = load_book()
    _log("book: %d closed trades, %d names" % (len(rows), len({r["ticker"] for r in rows})))

    if os.path.exists(CACHE) and not args.refresh and not args.limit:
        with open(CACHE, "rb") as f:
            blob = pickle.load(f)
        recs, missing = blob["recs"], blob["missing"]
        _log("cache hit: %d rows, %d missing" % (len(recs), len(missing)))
    else:
        recs, missing = build(rows, limit=args.limit)
        if not args.limit:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "wb") as f:
                pickle.dump({"recs": recs, "missing": missing}, f, protocol=4)
        _log("built: %d rows, %d missing" % (len(recs), len(missing)))

    # ---- control §0.5: no look-ahead. entry_premium is struck at the alert-day close, so the
    # whole tape precedes it. Re-measured here before any arm is read.
    rel = []
    for r in recs:
        e, la = r.get("entry_premium"), r.get("last_ask")
        if e and la and float(la) > 0:
            rel.append(abs(float(e) / float(la) - 1.0))
    look = {"n": len(rel),
            "median_rel_err_entry_vs_last_ask": float(np.median(rel)) if rel else None,
            "note": ("entry_premium is struck at the alert-day close, so the whole alert-day "
                     "tape precedes entry - no look-ahead")}
    _log("control: entry vs tape's last ask, median rel err %s over %d rows"
         % (None if look["median_rel_err_entry_vs_last_ask"] is None
            else round(look["median_rel_err_entry_vs_last_ask"], 4), look["n"]))

    cr = [r["classified_rate"] for r in recs if r.get("classified_rate") is not None]
    _log("Lee-Ready classified rate: median %.4f" % (float(np.median(cr)) if cr else float("nan")))

    arms = {}
    for key in TS.ARMS:
        arms[key] = score_arm(recs, key)
        a = arms[key]
        _log("%s: n=%s months=%s t=%s |t| vs p95 %s"
             % (key, a.get("n"), a.get("n_months"),
                None if a.get("t") is None else round(a["t"], 4),
                None if a.get("null_p95_abs_t") is None else round(a["null_p95_abs_t"], 4)))

    # ---- Benjamini-Hochberg across all five, as the audit requires.
    # BH needs a p-value per arm, not just a pass/fail against a p95, so the permutation null is
    # re-run RETAINING its draws and the two-sided p is read off them directly.
    pvals = [None] * len(TS.ARMS)
    for i, key in enumerate(TS.ARMS):
        a = arms[key]
        if a.get("abs_t") is None or a.get("n") is None or a.get("n") < 200:
            continue
        good = [r for r in recs
                if r.get(key) is not None and np.isfinite(float(r[key]))
                and r.get("pnl_pct") is not None and np.isfinite(float(r["pnl_pct"]))]
        vals = np.array([float(r[key]) for r in good], float)
        rets = np.array([float(r["pnl_pct"]) for r in good], float)
        months = np.array([r["month"] for r in good])
        lab = SX.quintiles_within_date(vals, months)
        draws = []
        rng = np.random.default_rng(TS.SEED)
        for _ in range(400):
            perm = lab.copy()
            for m in np.unique(months):
                idx = np.where(months == m)[0]
                if idx.size > 1:
                    perm[idx] = lab[idx][rng.permutation(idx.size)]
            d2, ls2, _ = SX.long_short_series(rets, perm, months)
            if not len(d2):
                continue
            st = SX.month_block_t(ls2, d2, draws=200, seed=TS.SEED)
            if st.get("t") is not None and np.isfinite(st["t"]):
                draws.append(abs(float(st["t"])))
        pvals[i] = TS.permutation_p_two_sided(a["abs_t"], draws)
        arms[key]["perm_p_two_sided"] = pvals[i]
        _log("%s: permutation p (two-sided) = %s"
             % (key, None if pvals[i] is None else round(pvals[i], 5)))

    bh = TS.benjamini_hochberg(pvals, q=TS.BH_Q)
    for i, key in enumerate(TS.ARMS):
        a = arms[key]
        a["bh_survives"] = bool(bh[i])
        e, l = (a.get("halves") or {}).get("early"), (a.get("halves") or {}).get("late")
        a["verdict"] = TS.arm_verdict(
            (e or {}).get("abs_t"), (e or {}).get("null_p95_abs_t"),
            None if (e or {}).get("ls_mean") is None else np.sign((e or {})["ls_mean"]),
            (l or {}).get("abs_t"), (l or {}).get("null_p95_abs_t"),
            None if (l or {}).get("ls_mean") is None else np.sign((l or {})["ls_mean"]),
            bool(bh[i])) if (e and l) else "NULL"
        _log("%s -> %s (BH %s)" % (key, a["verdict"], a["bh_survives"]))

    n_months = len({r["month"] for r in recs})
    void = (n_months < TS.MIN_MONTHS) or (len(recs) < TS.MIN_TRADES)

    payload = {
        "item": "O14 - the tick-flow signal studies",
        "prereg": "PREREG_o14_tickflow_signals.md",
        "prereg_commit": "ea48f6b",
        "book": "state_r2_splitclean.pkl",
        "n_book": len(rows), "n_rows_with_features": len(recs),
        "n_months": n_months, "void": bool(void),
        "missing_alert_days": [list(x) for x in missing],
        "lee_ready_classified_rate_median": float(np.median(cr)) if cr else None,
        "look_ahead_control": look,
        "two_sided": ("no sign can be declared - the audit's own literature note says signed "
                      "flow follows if institutional and fades if retail, and public tick data "
                      "cannot separate them. Two-sided costs power; it is the honest price."),
        "bh_q": TS.BH_Q,
        "arms": arms,
        "framing": ("R2 stands. A CANDIDATE here is a candidate for a FUTURE book that does not "
                    "exist - never evidence the alert entry works, never an adoption."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
