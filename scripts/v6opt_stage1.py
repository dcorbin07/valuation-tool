#!/usr/bin/env python3
"""V6-OPT stage 1 — DESCRIPTIVE. Executes `PREREG_v6opt_csp.md` sections 2, 3 and 5.

    python -m scripts.v6opt_stage1

Registered ALONE at `88685c9` before `valuation/edge/csp_surface.py` existed.

NO ARM IS SCORED HERE. Stage 1 returns six descriptions and ONE gate decision (register 3),
whose three bars are UNCALIBRATED and say so in the artifact. Stage 2 runs only if the gate
opens, and its design is already fixed in the register so it cannot be chosen on these numbers.

The controls run in their OWN pass and are READ before any description is computed - session 26
shipped a gating control and its outcomes in one pass and could not then claim the control was
read first. C1 and C3 abort the run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import csp_surface as CS                       # noqa: E402
# V6-B's own forward-path construction, IMPORTED so M1 cannot drift when it is re-measured.
from scripts.v6b_dip_survival import forward_paths                 # noqa: E402

ROOT = r"C:/Users/donni/Downloads/valuation-tool"
DERIVED = os.path.join(ROOT, "data/options_derived")
CHAINS = os.path.join(ROOT, "data/options")
DIPS = os.path.join(ROOT, "data/free_analysis/V6OPT_DIPS.pkl")
PRICES = os.path.join(ROOT, "data/backtest/prices")
OUT = os.path.join(ROOT, "data/free_analysis/V6OPT_STAGE1.json")
EVENTS = os.path.join(ROOT, "data/free_analysis/V6OPT_STAGE1_EVENTS.pkl")

# register 1c - the premise counts this run must reproduce or abort.
EXPECT = {"dip_rows": 37982, "covered": 4855, "healthy_covered": 1631,
          "unhealthy_covered": 3224, "dates_with_covered": 40}
M1_THRESHOLD = -0.20          # V6-B's M1: a FURTHER -20%


def _log(m):
    print(m, flush=True)


def _covered_dips():
    p = pd.read_pickle(DIPS)
    dips = p[p["_dip"]].copy()
    dips["_year"] = dips["date"].astype(str).str[:4]
    have = {}
    for t in sorted(os.listdir(DERIVED)):
        d = os.path.join(DERIVED, t)
        if os.path.isdir(d):
            have[t] = {f.rsplit("-", 1)[-1].split(".")[0]
                       for f in os.listdir(d) if f.endswith(".pkl")}
    dips["_covered"] = [bool(str(tk) in have and yr in have[str(tk)])
                        for tk, yr in zip(dips["ticker"], dips["_year"])]
    return dips, dips[dips["_covered"]].copy()


def _forward_closes(price_dir, ticker, d, n=CS.FORWARD_DAYS):
    """The n closes STRICTLY AFTER d. Right-censoring drops the row (S22's rule)."""
    p = os.path.join(price_dir, f"{str(ticker).upper()}.csv")
    if not os.path.exists(p):
        return None
    try:
        df = pd.read_csv(p, usecols=["date", "close"]).dropna().sort_values("date")
    except Exception:
        return None
    a = df["date"].to_numpy(dtype="datetime64[D]")
    c = df["close"].to_numpy(dtype=float)
    j = int(np.searchsorted(a, np.datetime64(str(d)[:10]), side="right"))
    if j < 1:
        return None
    win = c[j - 1:j + n]                      # include the dip close as the path's origin
    return win.tolist() if win.size >= n + 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data/backtest"))
    a = ap.parse_args()

    art = {"item": "V6-OPT", "stage": 1, "register": "PREREG_v6opt_csp.md",
           "register_commit": "88685c9", "adopts": "NOTHING",
           "controls": {}, "descriptions": {}, "gate": {}}

    # ================================================================ CONTROLS (own pass)
    _log("[stage1] C1 - reproducing the register's premise counts")
    dips_all, dips = _covered_dips()
    c1 = {"dip_rows": int(len(dips_all[dips_all["_dip"]])) if "_dip" in dips_all else None,
          "covered": int(len(dips)),
          "healthy_covered": int(dips["_healthy"].sum()),
          "unhealthy_covered": int((~dips["_healthy"]).sum()),
          "dates_with_covered": int(dips["date"].nunique())}
    c1["dip_rows"] = int(dips_all["_dip"].sum())
    c1["matches_register"] = all(c1[k] == v for k, v in EXPECT.items())
    art["controls"]["C1_premise_counts"] = {**c1, "expected": EXPECT}
    _log(f"    {c1}")
    if not c1["matches_register"]:
        art["controls"]["C1_premise_counts"]["ABORT"] = True
        with open(OUT, "w") as f:
            json.dump(art, f, indent=2, default=float)
        raise CS.RegisterViolation(f"C1 failed: {c1} vs {EXPECT}")

    dates = sorted(pd.Timestamp(str(d)[:10]) for d in pd.unique(dips["date"]))
    early, late, boundary = CS.halves(dates)
    art["controls"]["C1_halves"] = {"n_dates": len(dates), "early": len(early),
                                    "late": len(late), "boundary_embargoed": str(boundary.date())}
    _log(f"    halves {len(early)}/{len(late)}, boundary {boundary.date()} embargoed")

    # ---- load every surface once ------------------------------------------------------
    tickers = sorted(set(dips["ticker"].astype(str)))
    _log(f"[stage1] loading {len(tickers)} daily surfaces")
    surf = {}
    for t in tickers:
        d = CS.load_daily(DERIVED, t)
        if d is not None:
            surf[t] = d
    _log(f"    loaded {len(surf)}")

    # ---- C3: skew_25d IS iv_put_25d - iv_call_25d (register 1b) -----------------------
    _log("[stage1] C3 - skew_25d identity")
    worst, n_ck = 0.0, 0
    for t, d in surf.items():
        if not {"skew_25d", "iv_put_25d", "iv_call_25d"} <= set(d.columns):
            continue
        v = (pd.to_numeric(d["skew_25d"], errors="coerce")
             - (pd.to_numeric(d["iv_put_25d"], errors="coerce")
                - pd.to_numeric(d["iv_call_25d"], errors="coerce"))).abs()
        v = v.dropna()
        if len(v):
            worst = max(worst, float(v.max()))
            n_ck += int(len(v))
    art["controls"]["C3_skew_identity"] = {"rows_checked": n_ck, "max_abs_diff": worst,
                                           "note": ("skew_25d and the put-minus-call spread are "
                                                    "ONE column, never two pieces of evidence.")}
    _log(f"    max |skew_25d - (put-call)| = {worst:.3e} over {n_ck:,} rows")
    if worst > 1e-9:
        art["controls"]["C3_skew_identity"]["ABORT"] = True
        with open(OUT, "w") as f:
            json.dump(art, f, indent=2, default=float)
        raise CS.RegisterViolation(f"C3 failed: max diff {worst}")

    # ---- C-QUOTE: the reconstructed bid/ask against the RAW chain's own -----------------
    _log("[stage1] C-QUOTE - reconstructed bid/ask vs the raw chain")
    rng = np.random.default_rng(20260813)
    pairs = sorted({(str(t), str(y)) for t, y in zip(dips["ticker"], dips["_year"])})
    probe = [pairs[i] for i in rng.choice(len(pairs), size=min(8, len(pairs)), replace=False)]
    qerr, qn = 0.0, 0
    for t, y in probe:
        rp = os.path.join(CHAINS, t, f"{t}-{y}.pkl")
        dp = os.path.join(DERIVED, t, f"{t}-{y}.pkl")
        if not (os.path.exists(rp) and os.path.exists(dp)):
            continue
        raw = pd.read_pickle(rp)
        der = pd.read_pickle(dp)
        raw["date"] = pd.to_datetime(raw["date"])
        der["date"] = pd.to_datetime(der["date"])
        key = ["date", "expiration", "strike", "right"]
        raw["expiration"] = pd.to_datetime(raw["expiration"])
        der["expiration"] = pd.to_datetime(der["expiration"])
        m = der.merge(raw[key + ["bid", "ask"]], on=key, how="inner")
        if not len(m):
            continue
        m = m[(pd.to_numeric(m["mid"], errors="coerce") > 0)].head(40000)
        rb = pd.to_numeric(m["mid"]) * (1 - 0.5 * pd.to_numeric(m["spread_frac"]))
        e = (rb - pd.to_numeric(m["bid"])).abs().dropna()
        if len(e):
            qerr = max(qerr, float(e.max()))
            qn += int(len(e))
    art["controls"]["C_QUOTE_reconstruction"] = {"rows_checked": qn, "max_abs_err": qerr}
    _log(f"    max |reconstructed bid - raw bid| = {qerr:.3e} over {qn:,} rows")

    # ---- C5: M1 RE-MEASURED on the covered rows (register 1d) --------------------------
    _log("[stage1] C5 - re-measuring M1 on the COVERED subsample")
    fp = forward_paths(PRICES, tickers, dates)
    # Both sides normalised to ns before the join: `dips` carries datetime64[us] from the
    # panel while `forward_paths` echoes back whatever it was handed. A silent dtype mismatch
    # here is the join returning ZERO rows, which would read as "M1 is absent on the covered
    # subsample" - the exact headline C5 exists to report.
    fp["date"] = pd.to_datetime(fp["date"])
    dips["date"] = pd.to_datetime(dips["date"])
    cov = dips.merge(fp, on=["date", "ticker"], how="inner")
    if not len(cov):
        raise CS.RegisterViolation("C5 join produced ZERO rows - a dtype or key mismatch, "
                                   "not a measurement")
    def _m1(fr):
        v = pd.to_numeric(fr["fwd_min_ret"], errors="coerce").dropna()
        return (float((v <= M1_THRESHOLD).mean()), int(len(v))) if len(v) else (None, 0)
    hh, nh = _m1(cov[cov["_healthy"]])
    uu, nu = _m1(cov[~cov["_healthy"]])
    art["controls"]["C5_M1_on_covered"] = {
        "healthy_p": hh, "healthy_n": nh, "unhealthy_p": uu, "unhealthy_n": nu,
        "separation_pp": (None if hh is None or uu is None else (hh - uu) * 100.0),
        "v6b_full_panel_pp": -10.84, "v6b_megacap_quintile_pp": -3.787,
        "note": ("Register 1d/C5. A stage-2 result must be quoted against THIS number, never "
                 "against V6-B's -10.84pp (void condition 7).")}
    _log(f"    M1 covered: healthy {hh} (n {nh}) vs unhealthy {uu} (n {nu}) -> "
         f"{art['controls']['C5_M1_on_covered']['separation_pp']}")

    # ---- C6: is an IV gap really a size or sector gap? ---------------------------------
    mc = pd.to_numeric(dips.get("market_cap"), errors="coerce")
    c6 = {"median_mcap_healthy": float(mc[dips["_healthy"]].median()),
          "median_mcap_unhealthy": float(mc[~dips["_healthy"]].median())}
    c6["ratio"] = (c6["median_mcap_healthy"] / c6["median_mcap_unhealthy"]
                   if c6["median_mcap_unhealthy"] else None)
    if "sector" in dips.columns:
        hs = dips[dips["_healthy"]]["sector"].value_counts(normalize=True).head(6).to_dict()
        us = dips[~dips["_healthy"]]["sector"].value_counts(normalize=True).head(6).to_dict()
        c6["sector_share_healthy"] = {str(k): float(v) for k, v in hs.items()}
        c6["sector_share_unhealthy"] = {str(k): float(v) for k, v in us.items()}
    art["controls"]["C6_size_sector"] = c6
    _log(f"    C6 mcap healthy/unhealthy ratio {c6['ratio']}")

    # ================================================================ DESCRIPTIONS
    _log("[stage1] D1/D2/D3/D6 - surface descriptions")
    rows = []
    pit_violations = 0
    for d, tk, healthy in zip(dips["date"], dips["ticker"], dips["_healthy"]):
        t = str(tk)
        sd = surf.get(t)
        if sd is None:
            continue
        r = CS.as_of(sd, d)
        if r is None:
            continue
        if pd.Timestamp(r["date"]) > pd.Timestamp(str(d)[:10]):
            pit_violations += 1
            continue
        iv = pd.to_numeric(pd.Series([r.get("atm_iv_30")]), errors="coerce").iloc[0]
        iv = float(iv) if np.isfinite(iv) else None
        base = CS.baseline(sd, d, "atm_iv_30")
        sk = pd.to_numeric(pd.Series([r.get("skew_25d")]), errors="coerce").iloc[0]
        sk = float(sk) if np.isfinite(sk) else None
        skb = CS.baseline(sd, d, "skew_25d")
        ivr = pd.to_numeric(pd.Series([r.get("iv_rank")]), errors="coerce").iloc[0]
        path = CS.forward_path(sd, d, "atm_iv_30", CS.FORWARD_DAYS)
        closes = _forward_closes(PRICES, t, d)
        rv = CS.realised_vol(closes) if closes else None
        rows.append({
            "date": pd.Timestamp(str(d)[:10]), "ticker": t, "healthy": bool(healthy),
            "iv": iv, "iv_baseline": base, "elevation": CS.elevation(iv, base),
            "iv_rank": (float(ivr) if np.isfinite(ivr) else None),
            "skew": sk, "skew_baseline": skb, "skew_elevation": CS.elevation(sk, skb),
            "skew_minus_baseline": (None if sk is None or skb is None else sk - skb),
            "realised_vol_30d": rv, "vrp": CS.vrp(iv, rv),
            "iv_fwd_5": path[4], "iv_fwd_10": path[9], "iv_fwd_20": path[19],
            "iv_fwd_30": path[29],
        })
    ev = pd.DataFrame(rows)
    art["controls"]["C2_point_in_time"] = {"violations": int(pit_violations),
                                           "events": int(len(ev))}
    _log(f"    events {len(ev):,}; point-in-time violations {pit_violations}")

    # ---- D4: the real contract, grouped by (ticker, year) so each file loads once -------
    _log("[stage1] D4 - selecting the real 25-delta put per event")
    byfile = defaultdict(list)
    for i, (d, t) in enumerate(zip(ev["date"], ev["ticker"])):
        byfile[(t, str(d)[:4])].append(i)
    sel = {}
    reject = defaultdict(int)
    done = 0
    for (t, y), idxs in sorted(byfile.items()):
        p = os.path.join(DERIVED, t, f"{t}-{y}.pkl")
        done += 1
        if done % 200 == 0:
            _log(f"    ... {done}/{len(byfile)} (ticker,year) groups")
        if not os.path.exists(p):
            reject["no_file"] += len(idxs)
            continue
        try:
            ch = pd.read_pickle(p)
        except Exception:
            reject["unreadable"] += len(idxs)
            continue
        ch["date"] = pd.to_datetime(ch["date"])
        g = {k: v for k, v in ch.groupby("date")}
        keys = np.array(sorted(g.keys()), dtype="datetime64[ns]")
        for i in idxs:
            d = np.datetime64(pd.Timestamp(ev["date"].iloc[i]), "ns")
            j = int(np.searchsorted(keys, d, side="right"))
            if j <= 0:
                reject["no_chain_day"] += 1
                continue
            day = g[pd.Timestamp(keys[j - 1])]
            r = CS.pick_csp(day)
            if r is None:
                reject["no_qualifying_contract"] += 1
                continue
            sel[i] = r
    _log(f"    selected {len(sel):,} of {len(ev):,}; rejects {dict(reject)}")

    # `expiration` and `mid` are banked even though stage 1 never reads them: stage 2 settles on
    # them, and a banked dict that omits what the next stage needs is M6's finding - "banking a
    # number into a dict nobody serialises is not banking it".
    for k in ("strike", "dte", "delta", "credit", "credit_frac_strike", "spread_frac",
              "open_interest", "credit_rho", "expiration", "mid"):
        ev[k] = [sel.get(i, {}).get(k) for i in range(len(ev))]
    ev["credit_ann"] = [CS.annualise_credit(c, t) if c is not None and t else None
                        for c, t in zip(ev["credit_frac_strike"], ev["dte"])]
    ev["credit_rho_frac"] = [(r / s if r is not None and s else None)
                             for r, s in zip(ev["credit_rho"], ev["strike"])]

    # ---- C4: did the selected contract stay at the registered exposure? -----------------
    dl = pd.to_numeric(ev["delta"], errors="coerce").dropna()
    c4 = {"n": int(len(dl)), "median_delta": float(dl.median()) if len(dl) else None,
          "mean_abs_gap": float((dl - CS.TARGET_DELTA).abs().mean()) if len(dl) else None,
          "frac_within_tolerance": float(((dl - CS.TARGET_DELTA).abs()
                                          <= CS.DELTA_TOLERANCE).mean()) if len(dl) else None,
          "tolerance": CS.DELTA_TOLERANCE}
    dte = pd.to_numeric(ev["dte"], errors="coerce").dropna()
    c4["dte_min"] = int(dte.min()) if len(dte) else None
    c4["dte_max"] = int(dte.max()) if len(dte) else None
    c4["dte_in_band"] = float(((dte >= CS.DTE_LO) & (dte <= CS.DTE_HI)).mean()) if len(dte) else None
    art["controls"]["C4_exposure"] = c4
    _log(f"    C4 median delta {c4['median_delta']}, within tol {c4['frac_within_tolerance']}")

    art["controls"]["D4_selection"] = {"selected": int(len(sel)), "events": int(len(ev)),
                                       "rejects": {k: int(v) for k, v in reject.items()},
                                       "selection_rate": float(len(sel) / len(ev)) if len(ev) else None}

    # ================================================================ SUMMARIES + GATE
    def block(fr):
        return {
            "n": int(len(fr)),
            "D1_elevation": CS.summarise(fr["elevation"]),
            "D1_iv_level": CS.summarise(fr["iv"]),
            "D1_iv_baseline": CS.summarise(fr["iv_baseline"]),
            "D1_iv_rank": CS.summarise(fr["iv_rank"]),
            "D3_skew": CS.summarise(fr["skew"]),
            "D3_skew_minus_baseline": CS.summarise(fr["skew_minus_baseline"]),
            "D4_credit_frac_strike": CS.summarise(fr["credit_frac_strike"]),
            "D4_credit_annualised": CS.summarise(fr["credit_ann"]),
            "D4_spread_frac": CS.summarise(fr["spread_frac"]),
            "D4_credit_frac_rho_DIAGNOSTIC": CS.summarise(fr["credit_rho_frac"]),
            "D6_realised_vol_30d": CS.summarise(fr["realised_vol_30d"]),
            "D6_vrp": CS.summarise(fr["vrp"]),
            "D2_decay": {f"t+{k}": CS.summarise(
                [(a / b - 1.0) if (a is not None and b not in (None, 0)
                                   and np.isfinite(a) and np.isfinite(b)) else None
                 for a, b in zip(fr[f"iv_fwd_{k}"], fr["iv"])])
                for k in (5, 10, 20, 30)},
        }

    ev["_half"] = np.where(ev["date"] <= early[-1], "early",
                           np.where(ev["date"] >= late[0], "late", "boundary"))
    desc = {"full": {"healthy": block(ev[ev["healthy"]]),
                     "unhealthy": block(ev[~ev["healthy"]])}}
    for h in ("early", "late"):
        f = ev[ev["_half"] == h]
        desc[h] = {"healthy": block(f[f["healthy"]]), "unhealthy": block(f[~f["healthy"]])}
    art["descriptions"] = desc

    def _gate_for(d):
        return CS.gate(d["healthy"]["D4_credit_frac_strike"]["median"],
                       d["healthy"]["D1_elevation"]["median"],
                       d["unhealthy"]["D1_elevation"]["median"],
                       d["healthy"]["D6_vrp"]["median"])
    g = {k: _gate_for(desc[k]) for k in ("full", "early", "late")}
    g["OPEN_both_halves"] = bool(g["early"]["open"] and g["late"]["open"])
    g["decision"] = "GATE OPEN - stage 2 runs" if g["OPEN_both_halves"] else \
                    "GATE CLOSED - stage 2 does NOT run (register 3)"
    art["gate"] = g
    _log(f"[stage1] {g['decision']}")
    for k in ("full", "early", "late"):
        _log(f"    {k}: G1 {g[k]['G1_credit']}  G2 {g[k]['G2_not_priced']} "
             f"(ratio {g[k]['elevation_ratio']})  G3 {g[k]['G3_vrp']}")

    ev.to_pickle(EVENTS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(art, f, indent=2, default=float)
    _log(f"[stage1] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
