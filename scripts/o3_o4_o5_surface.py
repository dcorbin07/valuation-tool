"""O3 + O4 + O5 — the surface-anomaly cross-section on a TRUE delta-hedged instrument.

    python -m scripts.o3_o4_o5_surface              # full run
    python -m scripts.o3_o4_o5_surface --limit 300  # smoke test, NOT a verdict

Pre-registered in `PREREG_o3_o4_o5_surface.md`, committed ALONE at d2aa5f9 before this file
existed. Nothing is adopted; a CANDIDATE is routed to Don.

The formation events, their strikes and their expiries are taken UNCHANGED from the prior lane's
panel, so the contract is not a new degree of freedom and `A1` differs from the published
rejection in the INSTRUMENT ALONE.
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

from valuation.edge import surface_xsec as SX        # noqa: E402
from valuation.edge import blackscholes as BS        # noqa: E402
from valuation.edge import options_backtest as OB    # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_xsection")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
PANEL = os.path.join(DATA, "options_xsection", "panel.pkl")
CHAINS = os.path.join(DATA, "options")
BARS = os.path.join(DATA, "bulk", "prepared", "bars")
CACHE = os.path.join(DATA, "free_analysis", "O3O4O5_EVENTS.pkl")
OUT = os.path.join(DATA, "free_analysis", "O3_O4_O5_SURFACE.json")


def _log(m):
    print("[O3/O4/O5] %s" % m, flush=True)


def load_panel() -> list:
    with open(PANEL, "rb") as f:
        return pickle.load(f)["rows"]


def ticker_chain(tkr: str) -> "pd.DataFrame":
    frames = []
    d = os.path.join(CHAINS, tkr)
    if not os.path.isdir(d):
        return None
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
    out["mid"] = (out["bid"].astype(np.float64) + out["ask"].astype(np.float64)) / 2.0
    return out


def atm_iv_series(ch: "pd.DataFrame", spot: dict) -> dict:
    """Daily ATM implied vol at the tenor the instrument actually trades (DTE in [20,45]).

    The prior lane computed vol-of-vol on a 60-DTE series while its instrument was ~30 DTE and
    said so; this aligns them, which is the only characteristic change in A3.
    """
    c = ch[(ch["rt"] == "C") & (ch["mid"] > 0)]
    if not len(c):
        return {}
    out = {}
    for ds, g in c.groupby("ds", sort=True):
        S = spot.get(ds)
        if not S or S <= 0:
            continue
        d0 = dt.date.fromisoformat(ds)
        dte = np.array([(dt.date.fromisoformat(e) - d0).days for e in g["es"].to_numpy()])
        m = (dte >= SX.DTE_LO) & (dte <= SX.DTE_HI)
        if not m.any():
            continue
        gg = g[m]
        j = int(np.argmin(np.abs(gg["K"].to_numpy() - S)))
        row = gg.iloc[j]
        T = max((dt.date.fromisoformat(row["es"]) - d0).days, 0) / 365.0
        if T <= 0:
            continue
        iv = BS.implied_vol(float(row["mid"]), float(S), float(row["K"]), T,
                            SX.RATE, "C", q=SX.DIV_YIELD)
        if iv and iv > 0:
            out[ds] = float(iv)
    return out


def contract_life(ch, expiry: str, strike: float, d0: str) -> "pd.DataFrame":
    m = ((ch["es"] == expiry) & (np.abs(ch["K"] - strike) < 1e-6) & (ch["rt"] == "C")
         & (ch["ds"] >= d0) & (ch["ds"] <= expiry))
    return ch.loc[m].sort_values("ds")


def build_events(rows, limit=0) -> list:
    by_tkr = {}
    for i, r in enumerate(rows):
        if limit and i >= limit:
            break
        by_tkr.setdefault(r["ticker"], []).append((i, r))
    out = []
    t0 = time.time()
    for n, (tkr, evs) in enumerate(sorted(by_tkr.items())):
        ch = ticker_chain(tkr)
        if ch is None:
            for i, r in evs:
                out.append({"row": i, "ok": False, "why": "no_chain"})
            continue
        bars = OB.load_bars(tkr, cache_dir=BARS)
        if not bars or not bars.get("date"):
            for i, r in evs:
                out.append({"row": i, "ok": False, "why": "no_bars"})
            continue
        px = bars.get("raw_close") or bars.get("close")
        spot = {d: p for d, p in zip(bars["date"], px) if p and p > 0}
        bdates = sorted(spot)
        bidx = {d: k for k, d in enumerate(bdates)}
        ivs = atm_iv_series(ch, spot)
        for i, r in evs:
            d0 = str(r["date"])[:10]
            exp = str(r["expiry"])[:10]
            K = float(r["strike"])
            life = contract_life(ch, exp, K, d0)
            if len(life) < 2:
                out.append({"row": i, "ok": False, "why": "no_life"})
                continue
            days = []
            ds_list = life["ds"].to_numpy()
            for j in range(len(life)):
                ds = ds_list[j]
                S = spot.get(ds)
                if S is None:
                    continue
                row = life.iloc[j]
                mid = float(row["mid"])
                T = max((dt.date.fromisoformat(exp) - dt.date.fromisoformat(ds)).days, 0) / 365.0
                iv = (BS.implied_vol(mid, S, K, T, SX.RATE, "C", q=SX.DIV_YIELD)
                      if (mid > 0 and T > 0) else None)
                dl = (BS.greeks(S, K, T, SX.RATE, iv, "C", q=SX.DIV_YIELD)["delta"]
                      if iv else None)
                nxt = ds_list[j + 1] if j + 1 < len(ds_list) else ds
                days.append({"s": float(S), "mark": mid, "delta": dl,
                             "dt": SX.year_fraction(ds, nxt),
                             "entry_px": float(row["ask"]) if j == 0 else None,
                             "exit_px": float(row["bid"]) if j == len(life) - 1 else None})
            dh = SX.delta_hedged_return(days)
            dh0 = SX.delta_hedged_return(days, hedge_bps=0.0)
            dhm = SX.delta_hedged_return([dict(x, entry_px=None, exit_px=None) for x in days])
            if dh is None:
                out.append({"row": i, "ok": False, "why": "unpriceable"})
                continue
            k = bidx.get(d0)
            mom6 = None
            if k is not None and k >= 126:
                a, b = spot[bdates[k - 126]], spot[bdates[k]]
                if a and a > 0:
                    mom6 = b / a - 1.0
            out.append({
                "row": i, "ok": True, "ticker": tkr, "date": d0,
                "dh": dh["dh"], "dh_nohedgecost": (dh0 or {}).get("dh"),
                "dh_midmid": (dhm or {}).get("dh"),
                "n_days": dh["n_days"], "n_solvable": dh["n_solvable"],
                "idio_vol": r.get("idio_vol"), "idio_skew": r.get("idio_skew"),
                "vov_60dte_prior": r.get("vol_of_vol"),
                "vol_of_vol": SX.vol_of_vol_from_series(ivs, d0),
                "mom6": mom6, "straddle_ret": r.get("return_pct"),
            })
        if (n + 1) % 10 == 0:
            _log("tickers %d/%d  %.0fs" % (n + 1, len(by_tkr), time.time() - t0))
    _log("events built: %d, %.0fs" % (len(out), time.time() - t0))
    return out


def attach_expected_skew(ev: list) -> int:
    """Expanding-window Boyer-Vorkink fit. Training pairs are (predictors at event k, realised
    idio skew at the SAME name's next event); at each formation date only pairs whose TARGET was
    already observed are used, so nothing reads the future."""
    ok = [e for e in ev if e.get("ok")]
    by_t = {}
    for e in ok:
        by_t.setdefault(e["ticker"], []).append(e)
    pairs = []
    for t, es in by_t.items():
        es.sort(key=lambda x: x["date"])
        for a, b in zip(es, es[1:]):
            if b.get("idio_skew") is None:
                continue
            pairs.append({"date_known": b["date"], "idio_skew": a.get("idio_skew"),
                          "idio_vol": a.get("idio_vol"), "mom6": a.get("mom6"),
                          "target": b.get("idio_skew")})
    n = 0
    for day in sorted({e["date"] for e in ok}):
        train = [p for p in pairs if p["date_known"] < day]
        beta = SX.fit_expected_skew(train)
        for e in ok:
            if e["date"] != day:
                continue
            e["exp_idio_skew"] = SX.predict_expected_skew(beta, e)
            if e["exp_idio_skew"] is not None:
                n += 1
    return n


def score_arm(ev, key, label) -> dict:
    ok = [e for e in ev if e.get("ok") and e.get(key) is not None
          and np.isfinite(e.get(key)) and e.get("dh") is not None and np.isfinite(e["dh"])]
    if not ok:
        return {"arm": label, "verdict": "NULL", "why": "empty"}
    vals = np.array([e[key] for e in ok], dtype=np.float64)
    rets = np.array([e["dh"] for e in ok], dtype=np.float64)
    dates = np.array([e["date"] for e in ok])
    lb = SX.quintiles_within_date(vals, dates)
    days, ls, q = SX.long_short_series(rets, lb, dates)
    if not len(days) or q.ndim != 2 or q.shape[0] == 0:
        return {"arm": label, "characteristic": key, "verdict": "NULL",
                "why": "no formation date carried both a Q1 and a Q5",
                "n_events": len(ok), "n_dates": 0}
    full = SX.month_block_t(ls, days)
    null = SX.perm_null_ls_t(rets, lb, dates)
    res = {"arm": label, "characteristic": key, "published_sign": SX.PUBLISHED_SIGNS.get(key),
           "n_events": len(ok), "n_dates": len(days),
           "quintile_means": [float(np.nanmean(q[:, j])) for j in range(q.shape[1])],
           "monotonicity": SX.monotonicity(q),
           "ls_mean": full.get("mean"), "ls_t": full.get("t"), "ls_ci95": full.get("ci95"),
           "n_month_blocks": full.get("n_blocks"),
           "null_p95": null.get("p95"), "null_median": null.get("median")}
    med = sorted({str(d) for d in dates})[len(set(dates)) // 2]
    halves = {}
    for nm, mask in (("early", dates < med), ("late", dates >= med)):
        if mask.sum() < SX.N_QUANTILES * 5:
            halves[nm] = None
            continue
        v2, r2, d2 = vals[mask], rets[mask], dates[mask]
        l2 = SX.quintiles_within_date(v2, d2)
        dd, ls2, q2 = SX.long_short_series(r2, l2, d2)
        st = SX.month_block_t(ls2, dd)
        nl = SX.perm_null_ls_t(r2, l2, d2, draws=500)
        halves[nm] = {"n_events": int(mask.sum()), "n_dates": len(dd),
                      "monotonicity": SX.monotonicity(q2), "ls_mean": st.get("mean"),
                      "ls_t": st.get("t"), "null_p95": nl.get("p95")}
    res["split_date"] = med
    res["halves"] = halves
    e, l = halves.get("early"), halves.get("late")
    # A verdict exists only for the three REGISTERED arms. The disclosed comparisons carry no
    # published sign of their own here, so no verdict is computed for them at all — rather than
    # defaulting a sign and then discarding the answer, which would leave a scored-then-hidden
    # arm in the code.
    if key not in SX.PUBLISHED_SIGNS:
        res["verdict"] = None
    else:
        res["verdict"] = (SX.arm_verdict(
            (e or {}).get("monotonicity"), (e or {}).get("ls_t"), (e or {}).get("null_p95"),
            (e or {}).get("ls_mean"),
            (l or {}).get("monotonicity"), (l or {}).get("ls_t"), (l or {}).get("null_p95"),
            (l or {}).get("ls_mean"), sign=SX.PUBLISHED_SIGNS[key]) if (e and l) else "NULL")
    return res


def diagnostics(ev, rows) -> dict:
    """DESCRIPTIVE ONLY — no verdict, no bar, zero trial cost.

    Added AFTER the three registered arms were read, and disclosed as such. It touches no
    registered quantity: the arms reproduce bit-identically with and without it, which is the
    control that proves the addition is inert.

    It exists because the three arms share a shape the register did not anticipate — Q5 is the
    worst delta-hedged bucket in ALL THREE — and the first question that shape raises is whether
    the three arms are one effect wearing three names, or whether Q5 is simply the illiquid
    corner of the book. Both are answered WITHOUT running a fourth arm, which §9.3 forbids:
    nothing here sorts on returns.
    """
    from scipy.stats import spearmanr

    ok = [e for e in ev if e.get("ok")]
    keys = ("idio_vol", "exp_idio_skew", "vol_of_vol")

    def _within_date_rho(pairs_by_date):
        rs = []
        for _d, pairs in pairs_by_date.items():
            if len(pairs) < 8:
                continue
            r = spearmanr(np.array([p[0] for p in pairs], float),
                          np.array([p[1] for p in pairs], float)).statistic
            if np.isfinite(r):
                rs.append(r)
        return (float(np.mean(rs)) if rs else None), len(rs)

    cols = {k: {(e["date"], e["ticker"]): e.get(k) for e in ok if e.get(k) is not None}
            for k in keys}

    cross = {}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            by_date = {}
            for (d, t), v in cols[a].items():
                if (d, t) in cols[b]:
                    by_date.setdefault(d, []).append((v, cols[b][(d, t)]))
            rho, nd = _within_date_rho(by_date)
            cross["%s|%s" % (a, b)] = {"within_date_rho": rho, "n_dates": nd}

    lab = {}
    for k in keys:
        items = [(d, t, v) for (d, t), v in cols[k].items()]
        vals = np.array([x[2] for x in items], float)
        dates = np.array([x[0] for x in items])
        q = SX.quintiles_within_date(vals, dates)
        lab[k] = {(items[i][0], items[i][1]): int(q[i]) for i in range(len(items))}

    top = SX.N_QUANTILES - 1
    overlap = {}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            shared = [k for k in lab[a] if k in lab[b]]
            a5 = {k for k in shared if lab[a][k] == top}
            b5 = {k for k in shared if lab[b][k] == top}
            both = len(a5 & b5)
            overlap["%s|%s" % (a, b)] = {
                "a_q5": len(a5), "b_q5": len(b5), "overlap": both,
                "share_of_smaller": (both / min(len(a5), len(b5))) if min(len(a5), len(b5)) else None}

    controls = {}
    for ctrl in ("illiq", "spread_pct", "atm_iv"):
        per_key = {}
        for k in keys:
            items = [(e["date"], e[k], rows[e["row"]].get(ctrl)) for e in ok
                     if e.get(k) is not None and rows[e["row"]].get(ctrl) is not None]
            if not items:
                continue
            by_date = {}
            for d, v, c in items:
                by_date.setdefault(d, []).append((v, c))
            rho, _nd = _within_date_rho(by_date)
            vals = np.array([x[1] for x in items], float)
            dates = np.array([x[0] for x in items])
            cv = np.array([x[2] for x in items], float)
            q = SX.quintiles_within_date(vals, dates)
            per_key[k] = {"within_date_rho": rho,
                          "control_mean_by_quintile":
                              [float(np.nanmean(cv[q == j])) for j in range(SX.N_QUANTILES)]}
        controls[ctrl] = per_key

    n_same = sum(1 for r in rows if r.get("illiq") == r.get("spread_pct"))
    return {
        "note": ("descriptive, no verdict, zero trial cost; added after the arms were read and "
                 "disclosed as such. Nothing here sorts on returns, so it is not a fourth arm."),
        "cross_characteristic": cross,
        "q5_membership_overlap": overlap,
        "controls": controls,
        "prior_lane_panel_defect": {
            "claim": "in the prior lane's panel.pkl, 'illiq' and 'spread_pct' are the SAME column",
            "rows_identical": n_same, "rows_total": len(rows),
            "why_it_matters": ("their 'illiq' was the only characteristic in the published "
                               "XSECTION run with |t| > 2 (2.46) and is described as a mechanical "
                               "liquidity control; it is the option's quoted spread percentage "
                               "under a second name. Reported, not repaired - not this lane's file."),
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3 + O4 + O5 - surface anomalies, delta-hedged")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)

    rows = load_panel()
    _log("panel formation events: %d" % len(rows))

    if os.path.exists(CACHE) and not args.refresh and not args.limit:
        with open(CACHE, "rb") as f:
            ev = pickle.load(f)
        _log("events loaded from cache: %d" % len(ev))
    else:
        ev = build_events(rows, limit=args.limit)
        if not args.limit:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "wb") as f:
                pickle.dump(ev, f, protocol=4)

    ok = [e for e in ev if e.get("ok")]
    why = {}
    for e in ev:
        if not e.get("ok"):
            why[e.get("why")] = why.get(e.get("why"), 0) + 1
    _log("priceable delta-hedged events: %d of %d   refusals: %s" % (len(ok), len(ev), why))

    n_exp = attach_expected_skew(ev)
    _log("expected-skew fitted on %d events" % n_exp)

    dates = sorted({e["date"] for e in ok})
    per_date = {}
    for e in ok:
        per_date[e["date"]] = per_date.get(e["date"], 0) + 1
    med_names = float(np.median(list(per_date.values()))) if per_date else 0.0
    void = (len(dates) < SX.MIN_DATES) or (med_names < SX.MIN_NAMES_PER_DATE)
    _log("formation dates %d, median names/date %.1f -> void=%s" % (len(dates), med_names, void))

    dh = np.array([e["dh"] for e in ok], dtype=np.float64)
    st = np.array([e["straddle_ret"] for e in ok if e.get("straddle_ret") is not None],
                  dtype=np.float64)
    disp = {"dh_sd": float(dh.std()), "dh_mean": float(dh.mean()),
            "dh_median": float(np.median(dh)),
            "straddle_sd": float(st.std()) if len(st) else None,
            "straddle_mean": float(st.mean()) if len(st) else None,
            "ratio_sd": (float(dh.std() / st.std()) if len(st) and st.std() > 0 else None)}
    _log("dispersion: dh sd %.4f vs straddle sd %s" % (disp["dh_sd"], disp["straddle_sd"]))

    arms = {}
    for key, label in (("idio_vol", "A1_O3_idio_vol"),
                       ("exp_idio_skew", "A2_O4_expected_idio_skew"),
                       ("vol_of_vol", "A3_O5_vol_of_vol")):
        arms[label] = score_arm(ev, key, label)
        a = arms[label]
        _log("%s: n=%s mono=%s ls_t=%s p95=%s -> %s" % (
            label, a.get("n_events"),
            None if a.get("monotonicity") is None else round(a["monotonicity"], 4),
            None if a.get("ls_t") is None else round(a["ls_t"], 4),
            None if a.get("null_p95") is None else round(a["null_p95"], 4), a.get("verdict")))

    # disclosed comparisons, NO verdict
    comps = {}
    for key, label in (("idio_skew", "prior_lane_realised_skew"),
                       ("vov_60dte_prior", "prior_lane_vol_of_vol_60dte")):
        c = score_arm(ev, key, label)
        c.pop("verdict", None)
        comps[label] = c

    payload = {
        "item": "O3 + O4 + O5",
        "prereg": "PREREG_o3_o4_o5_surface.md",
        "prereg_commit": "d2aa5f9",
        "instrument": "Cao-Han normalised delta-hedged call, rebalanced daily",
        "panel_source": "data/options_xsection/panel.pkl (prior lane); freeze cannot do a cross-section",
        "n_formation_events": len(rows),
        "n_priceable": len(ok),
        "refusals": why,
        "n_dates": len(dates),
        "median_names_per_date": med_names,
        "void": bool(void),
        "dispersion": disp,
        "arms": arms,
        "disclosed_comparisons_no_verdict": comps,
        "diagnostics_no_verdict": diagnostics(ev, rows),
        "prior_verdict": ("64955ef tested all three on a STRADDLE and REJECTED them; idio_vol was "
                          "monotone 0.9 CONTRADICTING the published sign. This is a second look "
                          "with a better instrument, charged as such."),
        "framing": ("a CANDIDATE is a candidate for a FUTURE book that does not exist; it is not "
                    "a revival of the options entry signal, not evidence R2 was wrong, and not "
                    "an adoption. Nothing is adopted in this session."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
