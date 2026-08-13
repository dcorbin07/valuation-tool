#!/usr/bin/env python3
"""V6 — the Dip Detector's testable claim.

Executes `PREREG_v6_dip_detector.md` unmodified. ONE panel build with
`extra_horizons=(126,)`, so 63d and 126d share dates, names and scores exactly.

The claim: a QUALITY-CONDITIONED drawdown recovers better than the market.

Run:  python -m scripts.v6_dip_detector --data-dir data/backtest
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import types

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG as CFG                    # noqa: E402
from valuation.edge import fundamental_panel as FP            # noqa: E402
from valuation.edge import statistics as ST                   # noqa: E402
from valuation.edge.data_providers import WRDSProvider        # noqa: E402
# The health mapping is the SHIPPED one, CALLED - never a retyped copy of its
# breakpoints. Re-implementing a shipped mapping is audit B7's defect class.
from valuation.engine.scoring import _health_score            # noqa: E402

# ---- everything below is PRE-COMMITTED in the register; nothing is swept -----------
THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
DEPTHS = (0.20, 0.30)          # register 3.4 - the tab's default, plus the one other arm
HORIZONS = (63, 126)           # register 3.4
TRAIL_DAYS = 252               # register 9 - the 52-week convention, NOT swept
TRAIL_MIN = 126                # a trailing high needs half a window to mean anything
QUALITY_FLOOR = 0.0            # register 3.3 - the cross-sectional midpoint
HEALTH_FLOOR = 50.0            # register 3.3 - the shipped 0-100 scale's midpoint
N_PERM = 500                   # register 3.6
MIN_NAMES_PER_DATE = 10        # register 3.7
MIN_DATES_PER_HALF = 24        # register 3.7
SEED = 20260813

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

ARMS = [(f"A{i+1}", d, h) for i, (d, h) in enumerate(
    [(dd, hh) for dd in DEPTHS for hh in HORIZONS])]


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------
# the drawdown feature
# ---------------------------------------------------------------------------------
def trailing_drawdown(price_dir: str, tickers, dates) -> pd.DataFrame:
    """drawdown = close(d)/max(close over the 252 rows ENDING AT d) - 1.

    POINT-IN-TIME: only rows with date <= d are ever read (register 3.2, C3).
    SPLIT BASIS: `close` in these files is SEP's split-ADJUSTED close. A raw series
    would read a 2-for-1 split as a -50% drawdown and flag exactly the names that
    rose (register 3.2, C5).
    NO PER-TICKER TAIL: the whole series is read, then indexed by date (audit B6, C6).
    """
    dts = np.array([np.datetime64(str(d)[:10]) for d in dates])
    rows = []
    for tk in tickers:
        p = os.path.join(price_dir, f"{tk.upper()}.csv")
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_csv(p, usecols=["date", "close"])
        except Exception:
            continue
        df = df.dropna()
        if len(df) < TRAIL_MIN:
            continue
        df = df.sort_values("date")
        a = df["date"].to_numpy(dtype="datetime64[D]")
        c = df["close"].to_numpy(dtype=float)
        # STRICTLY <= d: searchsorted 'right' gives the count of rows dated <= d.
        hi_i = np.searchsorted(a, dts, side="right")
        for d, j in zip(dates, hi_i):
            if j < TRAIL_MIN:
                continue
            lo = max(0, j - TRAIL_DAYS)
            win = c[lo:j]
            if win.size < TRAIL_MIN:
                continue
            mx = float(win.max())
            if not np.isfinite(mx) or mx <= 0:
                continue
            rows.append((d, tk, float(c[j - 1]) / mx - 1.0))
    return pd.DataFrame(rows, columns=["date", "ticker", "drawdown"])


# ---------------------------------------------------------------------------------
# the point-in-time financial-health score
# ---------------------------------------------------------------------------------
def health_panel(data_dir: str, tickers, dates) -> pd.DataFrame:
    """The SHIPPED `_health_score` on point-in-time SF1 inputs.

    `roic`/`roe` are 0.0% populated in the ARQ export (register 1c) and are NEVER read
    here. The cash-burner branch needs `cash_runway_years`, a live-engine quantity, so
    every row takes the non-burner branch and C4 reports how many rows that is.
    """
    use = ["ticker", "datekey", "debt", "cashneq", "ebitda", "intexp", "ebit", "fcf"]
    sf = pd.read_csv(os.path.join(data_dir, "fundamentals.csv"),
                     usecols=lambda c: c in use, low_memory=False)
    sf = sf[sf["ticker"].isin(set(tickers))].dropna(subset=["datekey"])
    sf = sf.sort_values("datekey")

    nd = sf["debt"] - sf["cashneq"]
    sf["_nde"] = nd / sf["ebitda"].where(sf["ebitda"] > 0)
    sf["_cov"] = sf["ebit"] / sf["intexp"].where(sf["intexp"] > 0)
    sf["_fcf"] = sf["fcf"]
    sf["_dk"] = sf["datekey"].astype(str).str[:10]

    out = []
    for d in dates:
        ds = str(d)[:10]
        cur = sf[sf["_dk"] <= ds]
        if cur.empty:
            continue
        cur = cur.groupby("ticker", sort=False).tail(1)
        for tk, nde, cov, fcf in zip(cur["ticker"], cur["_nde"], cur["_cov"], cur["_fcf"]):
            cd = types.SimpleNamespace(
                net_debt_to_ebitda=(None if pd.isna(nde) else float(nde)),
                interest_coverage=(None if pd.isna(cov) else float(cov)),
                cash_runway_years=None,
                fcf=(None if pd.isna(fcf) else float(fcf)))
            cls = types.SimpleNamespace(is_cash_burning=False)
            s, _ = _health_score(cd, cls)
            if s is not None:
                out.append((d, tk, float(s)))
    return pd.DataFrame(out, columns=["date", "ticker", "health"])


# ---------------------------------------------------------------------------------
# the two legs
# ---------------------------------------------------------------------------------
def _per_date(g, fwd_col):
    """(fwd, dip_mask, cond_mask) arrays for one date, finite fwd only."""
    f = pd.to_numeric(g[fwd_col], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(f)
    return f[ok], g["_dip"].to_numpy(dtype=bool)[ok], g["_cond"].to_numpy(dtype=bool)[ok]


def legs_for_date(f, dip, cond):
    """L1 = cond - universe;  L2 = cond - unconditioned dipped."""
    if cond.sum() < MIN_NAMES_PER_DATE or dip.sum() < MIN_NAMES_PER_DATE:
        return None, None, int(cond.sum()), int(dip.sum()), int(f.size)
    mc = float(f[cond].mean())
    return (mc - float(f.mean()), mc - float(f[dip].mean()),
            int(cond.sum()), int(dip.sum()), int(f.size))


def _t_of(series):
    r = ST.mean_inference(list(series))
    if not r:
        return None
    return r


def _perm_t(cells, rng, leg):
    """One permutation draw's t.

    L1's null shuffles the CONDITIONED flag among ALL names on the date.
    L2's null shuffles the quality/health label among the DIPPED names only - it asks
    whether the label adds anything beyond having dipped (register 3.6).
    """
    vals = []
    for f, dip, cond in cells:
        n_c = int(cond.sum())
        if leg == "L1":
            # `choice(n, k, replace=False)` is the SAME object as taking the first k of a
            # full permutation - a uniformly random size-k subset - and is far cheaper on a
            # 1,650-name cross-section. The scheme is unchanged; only the cost is.
            idx = rng.choice(f.size, size=n_c, replace=False)
            mc = float(f[idx].mean())
            vals.append(mc - float(f.mean()))
        else:
            di = np.flatnonzero(dip)
            if di.size < n_c or n_c == 0:
                return None
            pick = rng.choice(di.size, size=n_c, replace=False)
            mc = float(f[di[pick]].mean())
            vals.append(mc - float(f[di].mean()))
    if len(vals) < 3:
        return None
    r = ST.mean_inference(vals)
    # A degenerate draw (every permuted mean identical -> zero variance) makes the HAC t
    # UNDEFINED, and `mean_inference` returns t=None for it. Coercing that to a float
    # raises mid-run; treating it as 0.0 would silently pad the null with fake draws and
    # LOWER the p95, i.e. make the bar easier. It is dropped, and the count of surviving
    # draws is reported as `n_perm_ok`. Same family as the zero-variance guards this
    # project has already paid for twice (`zscore`'s sd == 0, `theme_ic`'s sd > 0).
    if not r or r.get("t") is None or not np.isfinite(r["t"]):
        return None
    return float(r["t"])


def score_arm(panel, depth, horizon, rng):
    fwd_col = "fwd_ret" if horizon == 63 else f"fwd_ret_h{horizon}"
    p = panel.copy()
    p["_dip"] = pd.to_numeric(p["drawdown"], errors="coerce") <= -depth
    p["_cond"] = (p["_dip"]
                  & (pd.to_numeric(p["quality"], errors="coerce") > QUALITY_FLOOR)
                  & (pd.to_numeric(p["health"], errors="coerce") >= HEALTH_FLOOR))

    dates, L1, L2, cov, cells = [], [], [], [], []
    for d, g in p.groupby("date", sort=True):
        f, dip, cond = _per_date(g, fwd_col)
        if f.size < 50:
            continue
        l1, l2, n_c, n_d, n_t = legs_for_date(f, dip, cond)
        cov.append({"date": str(d)[:10], "n_cond": n_c, "n_dip": n_d, "n_total": n_t})
        if l1 is None:
            continue
        dates.append(d)
        L1.append(l1)
        L2.append(l2)
        cells.append((f, dip, cond))

    n = len(dates)
    if n == 0:
        return {"verdict": "VOID - NO COVERED DATES", "coverage": cov, "n_dates": 0}

    mid = n // 2                      # boundary date embargoed
    halves = {"early": (0, mid), "late": (mid + 1, n)}

    res = {"depth": depth, "horizon": horizon, "fwd_col": fwd_col, "n_dates": n,
           "coverage": {"per_date": cov,
                        "n_cond_median": float(np.median([c["n_cond"] for c in cov])),
                        "n_dip_median": float(np.median([c["n_dip"] for c in cov])),
                        "n_total_median": float(np.median([c["n_total"] for c in cov])),
                        "dates_below_floor": int(sum(1 for c in cov
                                                     if c["n_cond"] < MIN_NAMES_PER_DATE))},
           "legs": {}}

    enough = all((b - a) >= MIN_DATES_PER_HALF for a, b in halves.values())
    res["enough_dates_per_half"] = bool(enough)

    for leg, series in (("L1", L1), ("L2", L2)):
        blk = {}
        for tag, (a, b) in [("full", (0, n))] + list(halves.items()):
            s = series[a:b]
            c = cells[a:b]
            if len(s) < 3:
                blk[tag] = {"n": len(s)}
                continue
            r = _t_of(s)
            nulls = [x for x in (_perm_t(c, rng, leg) for _ in range(N_PERM))
                     if x is not None]
            p95 = float(np.percentile(nulls, 95)) if nulls else None
            p5 = float(np.percentile(nulls, 5)) if nulls else None
            # `mean_inference` ships no `se`. Deriving it as mean/t is EXACT and keeps the
            # MDE on the SHIPPED HAC arithmetic instead of re-implementing a HAC variance.
            mu = float(np.mean(s))
            tt = float(r["t"]) if (r and r.get("t") is not None
                                   and np.isfinite(r["t"])) else None
            se = (abs(mu / tt) if (tt not in (None, 0.0) and mu != 0.0) else None)
            blk[tag] = {
                "n": len(s), "mean": mu,
                "ann_pp": mu * (252.0 / horizon) * 100.0,
                "t": tt,
                "se": se, "n_eff": (float(r.get("n_eff")) if r else None),
                # V2G/S19: a null quoted without its MDE is being misquoted.
                "mde_at_t2": (2.0 * se if se is not None else None),
                "mde_ann_pp": ((2.0 * se) * (252.0 / horizon) * 100.0
                               if se is not None else None),
                "perm_p95": p95, "perm_p5": p5, "n_perm_ok": len(nulls),
                "clears_p95": bool(tt is not None and p95 is not None and tt > p95),
                "below_p5": bool(tt is not None and p5 is not None and tt < p5),
                "perm_draws": [round(x, 6) for x in nulls],   # RUN_RULES A9
            }
        e, l = blk.get("early", {}), blk.get("late", {})
        blk["both_halves_clear"] = bool(e.get("clears_p95") and l.get("clears_p95"))
        blk["both_halves_below_p5"] = bool(e.get("below_p5") and l.get("below_p5"))
        blk["halves_same_sign"] = bool(
            e.get("t") is not None and l.get("t") is not None
            and np.sign(e["t"]) == np.sign(l["t"]))
        res["legs"][leg] = blk

    res["verdict"] = verdict_of(res["legs"]["L1"], res["legs"]["L2"], enough)
    return res


def verdict_of(l1b, l2b, enough) -> str:
    """Register 3.5, kept in ONE place so it can be pinned by test.

    Clearing L1 while failing L2 is NOT a pass: it means the DIP is doing the work and
    the quality conditioning - which is the whole of the tab's claim - is not.
    """
    if not enough:
        return "VOID - UNDERPOWERED BY CONSTRUCTION"
    if l2b["both_halves_below_p5"] and l2b["halves_same_sign"]:
        return "REJECTED - SIGN REVERSED"
    if (l1b["both_halves_clear"] and l2b["both_halves_clear"]
            and l1b["halves_same_sign"] and l2b["halves_same_sign"]):
        return "POSITIVE"
    if l1b["both_halves_clear"] and not l2b["both_halves_clear"]:
        return "NULL - THE DIP DOES THE WORK"
    return "NULL"


# ---------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_v6.pkl")
    ap.add_argument("--json", default="data/free_analysis/V6_DIP_DETECTOR.json")
    ap.add_argument("--controls-only", action="store_true")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        _log(f"[v6] loading banked panel {args.panel_cache}")
        panel = pickle.load(open(args.panel_cache, "rb"))
    else:
        _log("[v6] building the panel ONCE with extra_horizons=(126,)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        panel = FP.build_fundamental_panel(
            prov, prov.universe(None), rebalance_days=63,
            lookback_years=CFG.backtest_lookback_years, horizon=63,
            extra_horizons=(126,))
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        pickle.dump(panel, open(args.panel_cache, "wb"))
        _log(f"[v6] banked {args.panel_cache}")

    n_d, n_t = panel["date"].nunique(), panel["ticker"].nunique()
    _log(f"[v6] panel {panel.shape}, {n_d} dates, {n_t} names")
    out = {"item": "V6", "register": "PREREG_v6_dip_detector.md",
           "n_rows": int(len(panel)), "n_dates": int(n_d), "n_names": int(n_t),
           "depths": list(DEPTHS), "horizons": list(HORIZONS),
           "trail_days": TRAIL_DAYS, "quality_floor": QUALITY_FLOOR,
           "health_floor": HEALTH_FLOOR, "n_perm": N_PERM, "seed": SEED,
           "controls": {}, "arms": {}}

    # ---- C2 (GATING): canonical panel shape, asserted not warned ----
    c2 = {"n_dates": int(n_d), "n_names": int(n_t),
          "ok": bool(n_d >= 60 and n_t >= 2400)}
    out["controls"]["C2_canonical_panel"] = c2
    _log(f"[C2] canonical panel: {c2['ok']}  ({n_d} dates, {n_t} names)")
    if not c2["ok"]:
        out["ABORTED"] = "C2 failed - SMOKE-TEST PANEL, no verdict permitted"
        _w(args.json, out)
        return 2

    # ---- C1 (GATING): reproduces the shipped record, in its OWN pass ----
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(abs(got.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": got,
                                               "expected": REC}
    _log(f"[C1] reproduces the record: {ok1}  {got}")
    if not ok1:
        out["ABORTED"] = ("C1 FAILED - the harness does not reproduce the shipped record. "
                          "Every V6 arm is VOID per register 6.6. Aborting before any arm.")
        _w(args.json, out)
        return 2

    if args.controls_only:
        _w(args.json, out)
        _log("[v6] controls-only pass complete; arms NOT scored")
        return 0

    # ---- features ----
    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())
    _log(f"[v6] drawdown over {len(tickers)} names x {len(dates)} dates")
    dd = trailing_drawdown(os.path.join(args.data_dir, "prices"), tickers, dates)
    _log(f"[v6] drawdown rows {len(dd)}")
    hp = health_panel(args.data_dir, tickers, dates)
    _log(f"[v6] health rows {len(hp)}")

    p = panel.merge(dd, on=["date", "ticker"], how="left")
    p = p.merge(hp, on=["date", "ticker"], how="left")

    out["controls"]["C4_coverage"] = {
        "drawdown_non_null": float(p["drawdown"].notna().mean()),
        "health_non_null": float(p["health"].notna().mean()),
        "quality_non_null": float(pd.to_numeric(p["quality"], errors="coerce").notna().mean()),
        "both_non_null": float((p["drawdown"].notna() & p["health"].notna()).mean()),
        "health_median": float(pd.to_numeric(p["health"], errors="coerce").median()),
        "drawdown_median": float(pd.to_numeric(p["drawdown"], errors="coerce").median()),
        "cash_burner_rows_routed": 0,
        "cash_burner_note": ("every row takes the NON-burner branch; cash_runway_years is a "
                             "live-engine quantity and is not derivable point-in-time here"),
        "roic_roe_read": False,
        "roic_roe_note": "roic/roe are 0.0% populated in ARQ and are never read (register 1c)",
    }
    _log(f"[C4] drawdown cov {p['drawdown'].notna().mean():.4f}  "
         f"health cov {p['health'].notna().mean():.4f}")

    # ---- C7: drawdown vs momentum - the "different object" claim, measured ----
    c7 = {}
    for col in ("momentum", "ret_6_1", "ret_12_1", "ret_1_0"):
        if col in p.columns:
            a = pd.to_numeric(p["drawdown"], errors="coerce")
            b = pd.to_numeric(p[col], errors="coerce")
            m = a.notna() & b.notna()
            if m.sum() > 1000:
                c7[col] = round(float(a[m].corr(b[m], method="spearman")), 4)
    out["controls"]["C7_drawdown_vs_momentum_spearman"] = c7
    _log(f"[C7] drawdown vs momentum: {c7}")

    # ---- arms ----
    rng = np.random.default_rng(SEED)
    for tag, depth, horizon in ARMS:
        _log(f"[{tag}] depth {depth:.0%} horizon {horizon}d")
        r = score_arm(p, depth, horizon, rng)
        out["arms"][tag] = r
        l1 = r.get("legs", {}).get("L1", {}).get("full", {})
        l2 = r.get("legs", {}).get("L2", {}).get("full", {})
        _log(f"[{tag}] {r['verdict']}   L1 t {l1.get('t')} vs p95 {l1.get('perm_p95')} | "
             f"L2 t {l2.get('t')} vs p95 {l2.get('perm_p95')}")

    # ---- C8: characteristic tilt - a size sort must not read as a quality finding ----
    c8 = {}
    for tag, depth, horizon in ARMS:
        if horizon != HORIZONS[0]:
            continue
        q = pd.to_numeric(p["quality"], errors="coerce")
        h = pd.to_numeric(p["health"], errors="coerce")
        dip = pd.to_numeric(p["drawdown"], errors="coerce") <= -depth
        cond = dip & (q > QUALITY_FLOOR) & (h >= HEALTH_FLOOR)
        sz = pd.to_numeric(p.get("size"), errors="coerce")
        mc = pd.to_numeric(p.get("marketcap"), errors="coerce")
        c8[f"depth_{int(depth*100)}"] = {
            "mean_size_z_cond": (float(sz[cond].mean()) if sz is not None else None),
            "mean_size_z_dip": (float(sz[dip].mean()) if sz is not None else None),
            "mean_size_z_universe": (float(sz.mean()) if sz is not None else None),
            "median_mcap_cond": (float(mc[cond].median()) if mc is not None else None),
            "median_mcap_dip": (float(mc[dip].median()) if mc is not None else None),
            "cond_share_of_dipped": float(cond.sum() / max(1, dip.sum())),
        }
    out["controls"]["C8_characteristic_tilt"] = c8
    _log(f"[C8] tilt: {json.dumps(c8, default=float)[:300]}")

    _w(args.json, out)
    _log(f"[v6] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
