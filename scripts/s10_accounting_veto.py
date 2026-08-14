#!/usr/bin/env python3
"""S10-ACCT — the accounting red-flag veto, on three of the audit's four legs.

Executes the S10-ACCT section of `PREREG_x5_m4_b23_s10acct.md` unmodified.

Beneish M-score, Altman Z-score and external financing, each at its PUBLISHED threshold.
Exclude any name flagged by two or more, re-run the decile backtest on the survivors, and
report the alpha change, the drawdown change, and the crash rate among excluded vs kept.

NT filings are unbuildable from anything we own, so this is "two or more of THREE" - which
makes the veto NARROWER than the audit's four-flag rule, not stricter (register 0b).

Run:  python -m scripts.s10_accounting_veto
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP            # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
BENEISH_FLAG_ABOVE = -1.78        # published
ALTMAN_FLAG_BELOW = 1.81          # published distress zone
EXTFIN_TOP_DECILE = 0.90          # top decile of issuance within date
MIN_FLAGS_TO_VETO = 2             # "two or more" - of THREE, not four
MIN_COVERAGE = 0.30
CRASH = -0.50

DD_IMPROVE_PP = 2.0               # the audit's own bar - UNCALIBRATED (X7 has no DD floor)
ALPHA_GIVE_UP_PP = 1.0            # BELOW X7's 1.95pp margin - a NON-INFERIORITY allowance

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

SF1_COLS = ["ticker", "datekey", "dimension", "revenue", "cor", "receivables", "assetsc",
            "ppnenet", "assets", "depamor", "sgna", "liabilities", "ncfo", "netinc",
            "workingcapital", "retearn", "ebit", "marketcap", "ncfcommon", "ncfdebt", "debt"]


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


def _safe(a, b):
    """a/b with a None on any degenerate denominator - never a silent inf."""
    if a is None or b is None:
        return None
    a, b = float(a), float(b)
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return None
    v = a / b
    return v if np.isfinite(v) else None


def _req(d, *keys):
    """Every key present and finite, or None.

    NOT `x or 0`. A missing `ncfo` under `or 0` becomes ZERO operating cash flow, which
    inflates TATA and manufactures a manipulation flag out of an absent number; a missing
    `cor` makes the gross margin exactly 1.0. **A missing input is missing, not zero** — and
    the first cut of this function got that wrong on six of the eight terms, caught by the
    test written to pin the docstring's own claim.
    """
    out = []
    for k in keys:
        v = d.get(k)
        if v is None:
            return None
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        if v != v:
            return None
        out.append(v)
    return out


def beneish_m(cur, pri):
    """The eight-variable Beneish M-score, published coefficients.

    A missing component makes the whole score None rather than defaulting to a neutral value:
    an index built from partial inputs is not the published index.
    """
    dsri = _safe(_safe(cur.get("receivables"), cur.get("revenue")),
                 _safe(pri.get("receivables"), pri.get("revenue")))
    _c = _req(cur, "revenue", "cor")
    _p = _req(pri, "revenue", "cor")
    gm_c = _safe(_c[0] - _c[1], _c[0]) if _c else None
    gm_p = _safe(_p[0] - _p[1], _p[0]) if _p else None
    gmi = _safe(gm_p, gm_c)
    _ac = _req(cur, "assetsc", "ppnenet", "assets")
    _ap = _req(pri, "assetsc", "ppnenet", "assets")
    aqi_c = _safe(_ac[0] + _ac[1], _ac[2]) if _ac else None
    aqi_p = _safe(_ap[0] + _ap[1], _ap[2]) if _ap else None
    aqi = (_safe(1.0 - aqi_c, 1.0 - aqi_p)
           if (aqi_c is not None and aqi_p is not None and (1.0 - aqi_p) != 0) else None)
    sgi = _safe(cur.get("revenue"), pri.get("revenue"))
    _dc = _req(cur, "depamor", "ppnenet")
    _dp = _req(pri, "depamor", "ppnenet")
    dr_c = _safe(_dc[0], _dc[0] + _dc[1]) if _dc else None
    dr_p = _safe(_dp[0], _dp[0] + _dp[1]) if _dp else None
    depi = _safe(dr_p, dr_c)
    sgai = _safe(_safe(cur.get("sgna"), cur.get("revenue")),
                 _safe(pri.get("sgna"), pri.get("revenue")))
    lv_c = _safe(cur.get("liabilities"), cur.get("assets"))
    lv_p = _safe(pri.get("liabilities"), pri.get("assets"))
    lvgi = _safe(lv_c, lv_p)
    _t = _req(cur, "netinc", "ncfo", "assets")
    tata = _safe(_t[0] - _t[1], _t[2]) if _t else None
    parts = (dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata)
    if any(p is None for p in parts):
        return None
    return (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
            + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)


def altman_z(cur):
    """Altman Z, the manufacturing five-variable form, published coefficients."""
    ta = cur.get("assets")
    x1 = _safe(cur.get("workingcapital"), ta)
    x2 = _safe(cur.get("retearn"), ta)
    x3 = _safe(cur.get("ebit"), ta)
    x4 = _safe(cur.get("marketcap"), cur.get("liabilities"))
    x5 = _safe(cur.get("revenue"), ta)
    if any(v is None for v in (x1, x2, x3, x4, x5)):
        return None
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


def build_flags(data_dir, tickers, dates):
    """Point-in-time flags per (date, ticker): the latest SF1 row with datekey <= date, and
    the row four quarters before it for the Beneish year-over-year terms."""
    sf = pd.read_csv(os.path.join(data_dir, "fundamentals.csv"),
                     usecols=lambda c: c in SF1_COLS, low_memory=False)
    if "dimension" in sf.columns:
        sf = sf[sf["dimension"] == "ARQ"]
    sf = sf[sf["ticker"].isin(set(tickers))].dropna(subset=["datekey"])
    sf["_dk"] = sf["datekey"].astype(str).str[:10]
    sf = sf.sort_values(["ticker", "_dk"])
    by = {t: g.to_dict("records") for t, g in sf.groupby("ticker", sort=False)}

    rows = []
    for d in dates:
        ds = str(d)[:10]
        for t, recs in by.items():
            i = None
            for j in range(len(recs) - 1, -1, -1):
                if recs[j]["_dk"] <= ds:
                    i = j
                    break
            if i is None:
                continue
            cur = recs[i]
            pri = recs[i - 4] if i >= 4 else None
            m = beneish_m(cur, pri) if pri else None
            z = altman_z(cur)
            ext = _safe((cur.get("ncfcommon") or 0) + (cur.get("ncfdebt") or 0),
                        cur.get("assets"))
            rows.append((d, t, m, z, ext))
    f = pd.DataFrame(rows, columns=["date", "ticker", "beneish_m", "altman_z", "extfin"])
    # external financing flags the TOP DECILE within each date - a cross-sectional rule, so
    # it is computed per date rather than on a pooled threshold.
    f["extfin_flag"] = False
    for d, g in f.groupby("date"):
        v = pd.to_numeric(g["extfin"], errors="coerce")
        if v.notna().sum() < 50:
            continue
        thr = float(v.quantile(EXTFIN_TOP_DECILE))
        f.loc[g.index, "extfin_flag"] = (v > thr).fillna(False)
    f["beneish_flag"] = pd.to_numeric(f["beneish_m"], errors="coerce") > BENEISH_FLAG_ABOVE
    f["altman_flag"] = pd.to_numeric(f["altman_z"], errors="coerce") < ALTMAN_FLAG_BELOW
    f["n_flags"] = (f["beneish_flag"].astype(int) + f["altman_flag"].astype(int)
                    + f["extfin_flag"].astype(int))
    f["vetoed"] = f["n_flags"] >= MIN_FLAGS_TO_VETO
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_r5r6.pkl")
    ap.add_argument("--json", default="data/free_analysis/S10_ACCOUNTING.json")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel_cache, "rb"))
    _log(f"[s10a] panel {panel.shape}, {panel['date'].nunique()} dates, "
         f"{panel['ticker'].nunique()} names")
    out = {"item": "S10-ACCT", "register": "PREREG_x5_m4_b23_s10acct.md",
           "beneish_flag_above": BENEISH_FLAG_ABOVE, "altman_flag_below": ALTMAN_FLAG_BELOW,
           "min_flags_to_veto": MIN_FLAGS_TO_VETO,
           "deviation": ("NT filings are unbuildable, so this is two-or-more of THREE, not "
                         "four. That makes the veto NARROWER than the audit's rule - a name "
                         "flagged by NT plus one other is NOT excluded here - so a null does "
                         "not close the four-flag rule."),
           "controls": {}, "arms": {}}

    # ---- C1 (GATING) ----
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(got.get(k) == v for k, v in REC.items())
    out["controls"]["C1_full_universe_headline"] = {"ok": bool(ok1), "measured": got}
    _log(f"[C1] headline reproduces: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 FAILED"
        _w(args.json, out)
        return 2

    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())
    _log("[s10a] building the three flags from SF1 (point-in-time)")
    flags = build_flags(args.data_dir, tickers, dates)
    _log(f"[s10a] flag rows {len(flags)}")
    p = panel.merge(flags, on=["date", "ticker"], how="left")
    p["vetoed"] = p["vetoed"].fillna(False)

    # ---- C4: coverage FIRST ----
    cov = {
        "rows": int(len(p)),
        "beneish_computable": float(pd.to_numeric(p["beneish_m"], errors="coerce").notna().mean()),
        "altman_computable": float(pd.to_numeric(p["altman_z"], errors="coerce").notna().mean()),
        "extfin_computable": float(pd.to_numeric(p["extfin"], errors="coerce").notna().mean()),
        "beneish_flagged": float(p["beneish_flag"].fillna(False).mean()),
        "altman_flagged": float(p["altman_flag"].fillna(False).mean()),
        "extfin_flagged": float(p["extfin_flag"].fillna(False).mean()),
        "vetoed_share": float(p["vetoed"].mean()),
        "vetoed_rows": int(p["vetoed"].sum()),
    }
    out["controls"]["C4_coverage"] = cov
    _log(f"[C4] {json.dumps(cov, default=float)}")
    below = [k for k in ("beneish_computable", "altman_computable", "extfin_computable")
             if cov[k] < MIN_COVERAGE]
    if below:
        out["arms"]["A1_veto"] = {"verdict": "VOID - UNDERPOWERED BY CONSTRUCTION",
                                  "below_floor": below}
        _w(args.json, out)
        _log(f"[A1] VOID - coverage below floor: {below}")
        return 0

    # ---- A1: the veto ----
    # `quantile_backtest` returns no drawdown, so the top-decile RETURN series is taken from
    # its opt-in `return_series` (alpha + equal_weight, the two it banks) and passed to the
    # SHIPPED `_risk_stats`. Re-implementing a drawdown here would be audit B7's class.
    def _dd_of(frame):
        r = FP.quantile_backtest(frame, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63,
                                 return_series=True)
        s = r.get("series") or {}
        book = [a + e for a, e in zip(s.get("alpha") or [], s.get("equal_weight") or [])
                if a == a and e == e]
        return r, FP.risk_stats(book, 252.0 / 63.0).get("max_drawdown")

    base_s, b_dd = _dd_of(panel)
    surv = p[~p["vetoed"]]
    arm, a_dd = _dd_of(surv)
    b_al, a_al = base_s.get("top_decile_alpha"), arm.get("top_decile_alpha")
    # SIGN: max_drawdown is NEGATIVE, so an arm IMPROVES it by being LESS negative and the
    # gain is arm - base. S10's first cut computed base - arm and reported a 2.61pp WORSENING
    # as a 2.61pp IMPROVEMENT.
    dd_gain_pp = ((float(a_dd) - float(b_dd)) * 100.0
                  if (a_dd is not None and b_dd is not None) else None)
    alpha_change_pp = ((float(a_al) - float(b_al)) * 100.0
                       if (a_al is not None and b_al is not None) else None)
    ok_dd = dd_gain_pp is not None and dd_gain_pp > DD_IMPROVE_PP
    ok_al = alpha_change_pp is not None and alpha_change_pp > -ALPHA_GIVE_UP_PP
    out["arms"]["A1_veto"] = {
        "base": {**{k: base_s.get(k) for k in ("top_decile_alpha", "long_short_tstat_nw", "monotonicity")}, "max_drawdown": b_dd},
        "arm": {**{k: arm.get(k) for k in ("top_decile_alpha", "long_short_tstat_nw", "monotonicity")}, "max_drawdown": a_dd},
        "drawdown_gain_pp": dd_gain_pp, "alpha_change_pp": alpha_change_pp,
        "drawdown_bar_pp": DD_IMPROVE_PP, "alpha_allowance_pp": ALPHA_GIVE_UP_PP,
        "clears_drawdown": bool(ok_dd), "clears_alpha": bool(ok_al),
        "verdict": ("ADOPT-ELIGIBLE" if (ok_dd and ok_al) else "REJECTED"),
        "caveats": [
            "max_drawdown is NEGATIVE: the gain is arm - base (S10's first cut inverted it).",
            "X7 calibrates NO drawdown floor, so the 2.0pp bar is UNCALIBRATED.",
            "the 1.0pp alpha allowance is BELOW X7's 1.95pp margin, so a pass means 'no loss "
            "detectable at this resolution', NEVER 'the loss is under 1pp'.",
        ],
    }
    _log(f"[A1] {out['arms']['A1_veto']['verdict']}  dd_gain {dd_gain_pp}pp  "
         f"alpha {alpha_change_pp}pp")

    # ---- A2: the crash rate, the audit's "number that matters most" ----
    fwd = pd.to_numeric(p["fwd_ret"], errors="coerce")
    v = p["vetoed"].to_numpy(dtype=bool)
    ok = fwd.notna().to_numpy()
    crash = (fwd <= CRASH).to_numpy()
    n_v, n_k = int((v & ok).sum()), int((~v & ok).sum())
    r_v = float(crash[v & ok].mean()) if n_v else None
    r_k = float(crash[~v & ok].mean()) if n_k else None
    out["arms"]["A2_crash_rate"] = {
        "threshold": CRASH,
        "vetoed_rows": n_v, "kept_rows": n_k,
        "crash_rate_vetoed": r_v, "crash_rate_kept": r_k,
        "n_crashes_vetoed": int(crash[v & ok].sum()) if n_v else 0,
        "n_crashes_kept": int(crash[~v & ok].sum()) if n_k else 0,
        "ratio_vetoed_over_kept": (r_v / r_k if (r_v is not None and r_k) else None),
        "STATUS": "MEASUREMENT - no calibrated floor exists for this (register 2)",
    }
    _log(f"[A2] crash rate vetoed {r_v} vs kept {r_k}")

    _w(args.json, out)
    _log(f"[s10a] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
