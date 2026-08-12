#!/usr/bin/env python3
"""S5 + S6 + S13 + S24 + S27 — five alternative weighting/combination schemes.

Executes `PREREG_s5_s6_s13_s24_s27_weighting.md` unmodified. ONE panel build, SIX scorings (the
deployed arm plus five), every arm evaluated on one identical frame.

Run:  python -m scripts.s5_s6_s13_s24_s27_weighting --data-dir data/backtest
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG as CFG                  # noqa: E402
from valuation.edge import fundamental_panel as FP          # noqa: E402
from valuation.edge.data_providers import WRDSProvider      # noqa: E402
from valuation.screener import cross_sectional as CS        # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
DEPLOYED = {c: 0.125 for c in THEMES}          # the shipped flat 1/7 (renormalised by mass)

# All pre-committed with the register.
S6_TRAILING_PERIODS = 4          # ~12 months
S6_CAP_MULT = 2.0                # <= 2x equal weight
S24_DRAWS = 200
S24_SEED = 20260812
S27_HALFLIVES = {"hl3y": 756, "hl10y": 2520}   # against the SHIPPED hl5y = 1260
S13_CAP_MULT = 2.0

MIN_ALPHA_GAIN = 0.01            # +100 bps
MIN_TSTAT_GAIN = 0.25

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


# ------------------------------------------------------------------ helpers
def _zt(panel):
    """Per-date z of every theme, once, reused by every arm."""
    z = {}
    for c in THEMES:
        out = pd.Series(np.nan, index=panel.index, dtype=float)
        for d, idx in panel.groupby("date").groups.items():
            out.loc[idx] = pd.to_numeric(CS.zscore(panel.loc[idx, c]), errors="coerce").values
        z[c] = out
    return z


def composite(z, w):
    """The SHIPPED convention: weighted sum renormalised by the PRESENT-weight mass (audit B7)."""
    num = pd.Series(0.0, index=next(iter(z.values())).index)
    den = pd.Series(0.0, index=num.index)
    for c, wi in w.items():
        v = z[c]
        ok = v.notna()
        num[ok] += wi * v[ok]
        den[ok] += wi
    return (num / den).where(den > 0)


def theme_ic_series(panel, z):
    """Per-theme, per-date Spearman IC against the forward return. Used by S5/S27."""
    dates = sorted(panel["date"].unique())
    out = {c: [] for c in THEMES}
    for d in dates:
        idx = panel.index[panel["date"] == d]
        sub = panel.loc[idx]
        for c in THEMES:
            v, f = z[c].loc[idx], sub["fwd_ret"]
            m = v.notna() & f.notna()
            out[c].append(v[m].corr(f[m], method="spearman") if m.sum() > 30 else np.nan)
    return dates, {c: np.array(out[c], dtype=float) for c in THEMES}


def theme_ls_series(panel, z):
    """Per-theme long-short return per date — S6's raw material."""
    dates = sorted(panel["date"].unique())
    out = {c: [] for c in THEMES}
    for d in dates:
        idx = panel.index[panel["date"] == d]
        sub = panel.loc[idx]
        for c in THEMES:
            v, f = z[c].loc[idx], sub["fwd_ret"]
            m = v.notna() & f.notna()
            if m.sum() < 50:
                out[c].append(np.nan)
                continue
            vv, ff = v[m], f[m]
            q = vv.rank(pct=True)
            out[c].append(float(ff[q >= 0.9].mean() - ff[q <= 0.1].mean()))
    return dates, {c: np.array(out[c], dtype=float) for c in THEMES}


def _norm(d):
    s = sum(max(0.0, v) for v in d.values())
    return {k: max(0.0, v) / s for k, v in d.items()} if s > 0 else dict(DEPLOYED)


# ------------------------------------------------------------------ the arms
def arm_s5(ics):
    """James-Stein: shrink each theme's mean IC toward the grand mean, intensity from the data.

    THE REPORTED QUANTITY IS THE *SHRINKAGE* INTENSITY, matching the register's C5 semantics:
    1.0 = shrunk all the way to the grand mean = EQUAL WEIGHT; 0.0 = no shrinkage = raw
    IC-proportional, which is already a shipped scheme. The first cut reported the complement
    (the keep-the-signal factor), so the register's two degenerate ends read BACKWARDS against
    the implementation. Caught by `test_s5_james_stein_intensity_...` before any verdict was
    read; the register is left unedited and the code now matches it.
    """
    mu = np.array([np.nanmean(ics[c]) for c in THEMES], dtype=float)
    k = len(mu)
    mubar = float(np.nanmean(mu))
    ss = float(np.nansum((mu - mubar) ** 2))
    sig2 = float(np.nanmean([np.nanvar(ics[c], ddof=1) / max(1, np.sum(~np.isnan(ics[c])))
                             for c in THEMES]))
    # No between-theme variation means nothing distinguishes the themes, so shrink FULLY.
    shrink = ((k - 3) * sig2 / ss) if ss > 0 else 1.0
    shrink = float(min(1.0, max(0.0, shrink)))
    keep = 1.0 - shrink
    shrunk = mubar + keep * (mu - mubar)
    return _norm({THEMES[i]: shrunk[i] for i in range(k)}), {
        "shrinkage_intensity": shrink,
        "note": "1.0 = fully shrunk = equal weight; 0.0 = no shrinkage = raw IC-proportional",
        "grand_mean_ic": mubar, "between_ss": ss, "sigma2": sig2}


def arm_s27(ics, dates, halflife_days):
    """EWMA-IC weights at a given half-life, against the SHIPPED 1260d default."""
    ref = pd.to_datetime(dates[-1])
    w = np.array([0.5 ** ((ref - pd.to_datetime(d)).days / halflife_days) for d in dates])
    out = {}
    for c in THEMES:
        v = ics[c]
        m = ~np.isnan(v)
        out[c] = float(np.sum(w[m] * v[m]) / np.sum(w[m])) if m.any() else 0.0
    return _norm(out)


def arm_s6_weights_by_date(ls, dates):
    """Factor momentum: per-date theme weights from the trailing 4-period theme long-short.

    POINT-IN-TIME: date i uses periods [i-4, i-1] only, strictly before i.
    Bounds pre-committed: capped at 2x equal weight, floored at 0.
    """
    eq = 1.0 / len(THEMES)
    per = {}
    for i, d in enumerate(dates):
        if i < S6_TRAILING_PERIODS:
            per[d] = dict(DEPLOYED)                       # no history yet -> deployed
            continue
        tr = {c: float(np.nansum(ls[c][i - S6_TRAILING_PERIODS:i])) for c in THEMES}
        vals = np.array([tr[c] for c in THEMES], dtype=float)
        rk = pd.Series(vals).rank(pct=True).values - 0.5   # centred in [-0.5, +0.5]
        raw = {THEMES[j]: eq * (1.0 + rk[j]) for j in range(len(THEMES))}
        cap = S6_CAP_MULT * eq
        per[d] = _norm({c: min(cap, max(0.0, raw[c])) for c in THEMES})
    return per


def arm_s24(panel, z, draws=S24_DRAWS, seed=S24_SEED):
    """Bagging over the SIGNAL SET: resample themes with replacement, average within-date ranks."""
    rng = np.random.default_rng(seed)
    acc = pd.Series(0.0, index=panel.index)
    cnt = pd.Series(0, index=panel.index)
    disp = pd.Series(0.0, index=panel.index)
    sq = pd.Series(0.0, index=panel.index)
    for _ in range(draws):
        pick = rng.choice(THEMES, size=len(THEMES), replace=True)
        w = {}
        for c in pick:
            w[c] = w.get(c, 0.0) + 1.0 / len(THEMES)
        comp = composite(z, w)
        r = pd.Series(np.nan, index=panel.index)
        for d, idx in panel.groupby("date").groups.items():
            r.loc[idx] = comp.loc[idx].rank(pct=True)
        ok = r.notna()
        acc[ok] += r[ok]
        sq[ok] += r[ok] ** 2
        cnt[ok] += 1
    mean_r = (acc / cnt).where(cnt > 0)
    var_r = (sq / cnt - mean_r ** 2).where(cnt > 1)
    disp = var_r.clip(lower=0) ** 0.5
    return mean_r, disp


# ------------------------------------------------------------------ evaluation
def _halves(dates):
    mid = len(dates) // 2
    return dates[:mid], dates[mid + 1:], str(dates[mid])


def evaluate(panel, score_col, dates_subset, ret="fwd_ret"):
    """Book-level stats for ONE score on ONE set of dates. Deciles by the score."""
    sub = panel[panel["date"].isin(dates_subset)]
    s = sub[score_col]
    alpha, ls = [], []
    for d, idx in sub.groupby("date").groups.items():
        v, f = s.loc[idx], sub.loc[idx, ret]
        m = v.notna() & f.notna()
        if m.sum() < 50:
            continue
        vv, ff = v[m], f[m]
        q = vv.rank(pct=True)
        top, bot, ew = ff[q >= 0.9], ff[q <= 0.1], ff.mean()
        alpha.append(float(top.mean() - ew))
        ls.append(float(top.mean() - bot.mean()))
    if not alpha:
        return None
    a = np.array(alpha)
    l = np.array(ls)
    sd = l.std(ddof=1)
    return {"n_periods": len(a), "top_decile_alpha": float(a.mean() * 4.0),
            "long_short_ann": float(l.mean() * 4.0),
            "long_short_tstat": float(l.mean() / (sd / math.sqrt(len(l)))) if sd > 0 else None}


def gate(panel, base_col, arm_col, dates, label):
    """Held out in BOTH directions at the pre-committed margins."""
    early, late, boundary = _halves(dates)
    out = {"label": label, "boundary_date_embargoed": boundary, "splits": {},
           "min_alpha_gain": MIN_ALPHA_GAIN, "min_tstat_gain": MIN_TSTAT_GAIN}
    improves = []
    for name, ds in (("early_half", early), ("late_half", late)):
        ra, rb = evaluate(panel, base_col, ds), evaluate(panel, arm_col, ds)
        if not ra or not rb:
            out["splits"][name] = {"status": "insufficient"}
            improves.append(False)
            continue
        da = rb["top_decile_alpha"] - ra["top_decile_alpha"]
        dt = ((rb["long_short_tstat"] - ra["long_short_tstat"])
              if (ra["long_short_tstat"] is not None and rb["long_short_tstat"] is not None)
              else None)
        ok = bool(dt is not None and da >= MIN_ALPHA_GAIN and dt >= MIN_TSTAT_GAIN)
        improves.append(ok)
        out["splits"][name] = {"n_dates": len(ds), "delta_top_decile_alpha": da,
                               "delta_long_short_tstat": dt, "improves": ok,
                               "base": ra, "arm": rb}
    out["verdict"] = ("ADOPT-ELIGIBLE" if all(improves)
                      else "REJECTED" if not any(improves) else "NOT_REPLICATED")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_s5family.pkl")
    ap.add_argument("--json", default="data/free_analysis/S5_S6_S13_S24_S27.json")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        print(f"[w5] loading banked panel {args.panel_cache}")
        panel = pickle.load(open(args.panel_cache, "rb"))
    else:
        print("[w5] building the panel ONCE (with_vol_raw=True)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        panel = FP.build_fundamental_panel(prov, prov.universe(None), rebalance_days=63,
                                           lookback_years=CFG.backtest_lookback_years,
                                           horizon=63, with_vol_raw=True)
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        pickle.dump(panel, open(args.panel_cache, "wb"))
        print(f"[w5] banked {args.panel_cache}")

    print(f"[w5] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"

    out = {"n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
           "deployed_weights": DEPLOYED, "controls": {}, "arms": {},
           "s24_draws": S24_DRAWS, "s24_seed": S24_SEED,
           "s6_trailing_periods": S6_TRAILING_PERIODS, "s6_cap_mult": S6_CAP_MULT,
           "s27_halflives": S27_HALFLIVES, "s13_cap_mult": S13_CAP_MULT}

    # ---- C1: reproduce the published record, or ABORT ----
    base = FP.quantile_backtest(panel, THEMES, DEPLOYED, n_q=10, horizon=63)
    c1 = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": c1}
    print(f"[C1] reproduces record: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 failed - no arm read"
        _write(args.json, out)
        return 2

    z = _zt(panel)
    panel = panel.copy()
    panel["_deployed"] = composite(z, DEPLOYED)
    dates = sorted(panel["date"].unique())
    _, ics = theme_ic_series(panel, z)
    _, ls = theme_ls_series(panel, z)

    # ---- S5 ----
    w5, d5 = arm_s5(ics)
    panel["_s5"] = composite(z, w5)
    out["arms"]["S5_HIER_SHRINK"] = {"weights": w5, "detail": d5}
    print(f"[S5 ] shrinkage intensity {d5['shrinkage_intensity']:.4f}  weights "
          + " ".join(f"{c[:4]}={w5[c]:.3f}" for c in THEMES))
    out["controls"]["C5_shrinkage_not_degenerate"] = {
        "shrinkage_intensity": d5["shrinkage_intensity"],
        # Register C5's two ends, in the register's own direction.
        "IS_EQUAL_WEIGHT": bool(d5["shrinkage_intensity"] >= 1.0 - 1e-9),
        "IS_RAW_IC_PROPORTIONAL": bool(d5["shrinkage_intensity"] <= 1e-9)}

    # ---- S6 (time-varying) ----
    w6 = arm_s6_weights_by_date(ls, dates)
    s6 = pd.Series(np.nan, index=panel.index)
    for d, idx in panel.groupby("date").groups.items():
        wd = w6[d]
        num = pd.Series(0.0, index=idx)
        den = pd.Series(0.0, index=idx)
        for c, wi in wd.items():
            v = z[c].loc[idx]
            ok = v.notna()
            num[ok] += wi * v[ok]
            den[ok] += wi
        s6.loc[idx] = (num / den).where(den > 0)
    panel["_s6"] = s6
    eqw = 1.0 / len(THEMES)
    caps = [max(w6[d].values()) for d in dates]
    out["arms"]["S6_FACTOR_MOM"] = {"max_weight_seen": float(max(caps)),
                                    "cap": S6_CAP_MULT * eqw,
                                    "cap_binds": bool(max(caps) >= S6_CAP_MULT * eqw - 1e-9)}
    print(f"[S6 ] max theme weight {max(caps):.4f} against cap {S6_CAP_MULT*eqw:.4f}")

    # ---- S24 ----
    mean_r, disp = arm_s24(panel, z)
    panel["_s24"] = mean_r
    out["arms"]["S24_ENSEMBLE"] = {"draws": S24_DRAWS, "seed": S24_SEED,
                                   "mean_rank_dispersion": float(disp.mean(skipna=True))}
    print(f"[S24] {S24_DRAWS} draws, mean per-name rank dispersion "
          f"{disp.mean(skipna=True):.5f}")

    # ---- S27 (two half-lives, shipped 1260 is the incumbent for this arm) ----
    for tag, hl in S27_HALFLIVES.items():
        w = arm_s27(ics, dates, hl)
        panel[f"_s27_{tag}"] = composite(z, w)
        out["arms"].setdefault("S27_RECENCY", {})[tag] = {"halflife_days": hl, "weights": w}
    w_ship = arm_s27(ics, dates, 1260)
    panel["_s27_shipped"] = composite(z, w_ship)
    out["arms"]["S27_RECENCY"]["hl5y_shipped"] = {"halflife_days": 1260, "weights": w_ship}
    print("[S27] weights built at 756d, 2520d and the SHIPPED 1260d")

    # ---- C3 + C8 coverage, and the gates ----
    for col, name in (("_s5", "S5_HIER_SHRINK"), ("_s6", "S6_FACTOR_MOM"),
                      ("_s24", "S24_ENSEMBLE"),
                      ("_s27_hl3y", "S27_HL3Y"), ("_s27_hl10y", "S27_HL10Y")):
        rc = []
        for d, idx in panel.groupby("date").groups.items():
            a, b = panel["_deployed"].loc[idx], panel[col].loc[idx]
            m = a.notna() & b.notna()
            if m.sum() > 30:
                rc.append(a[m].rank().corr(b[m].rank()))
        e = out["arms"].setdefault(name, {})
        e["rank_corr_vs_deployed"] = float(np.mean(rc)) if rc else None
        e["coverage"] = float(panel[col].notna().mean())
        e["gate"] = gate(panel, "_deployed", col, dates, name)
        print(f"[gate] {name:18s} {e['gate']['verdict']:15s} rank_corr "
              f"{e['rank_corr_vs_deployed']:.4f}  cov {e['coverage']:.4f}")
        for h, s in e["gate"]["splits"].items():
            if "delta_top_decile_alpha" in s:
                print(f"          {h:11s} d_alpha {s['delta_top_decile_alpha']:+.4f}"
                      f"  d_t {s['delta_long_short_tstat']:+.4f}  improves {s['improves']}")

    # ---- S13: BOOK-LEVEL, composite unchanged ----
    out["arms"]["S13_VOL_TARGET"] = s13_book(panel, dates)

    # ---- CPCV: the AUTHORITY for weight adoption (register 4) ----
    out["cpcv"] = cpcv_report(panel)

    _write(args.json, out)
    print(f"\n[w5] wrote {args.json}")
    return 0


def cpcv_report(panel):
    """Register 4: 'CPCV is the authority for weight adoption ... an arm CPCV declines is not
    adopted whatever the held-out split says.'

    A LIMITATION OF THIS DESIGN AGAINST ITS OWN REGISTER, REPORTED RATHER THAN GLOSSED:
    `cpcv_validate` SELECTS among its own eight `_weight_schemes`; it does not accept an
    arbitrary weight vector, so it cannot bless or decline S5/S6/S27 arm-by-arm. Its authority
    therefore operates here as a BLANKET rule - it reports whether CPCV would move off the
    deployed defaults at all - and not as a per-arm verdict. That is weaker than the register's
    wording implies, and it is recorded as such.
    """
    try:
        r = FP.cpcv_validate(panel, THEMES, DEPLOYED)
    except Exception as e:                                   # noqa: BLE001
        return {"status": f"error: {type(e).__name__}: {e}"}
    out = {
        "adopt": r.get("adopt"),
        "recommended": r.get("recommended"),
        "pbo": r.get("pbo"),
        "deflated_sharpe": (r.get("deflated_sharpe") or {}).get("value")
        if isinstance(r.get("deflated_sharpe"), dict) else r.get("deflated_sharpe"),
        "adopt_detail": r.get("adopt_detail"),
        "SCOPE_LIMITATION": ("cpcv_validate selects among its OWN eight _weight_schemes and "
                             "cannot evaluate an arbitrary vector, so it does not bless or "
                             "decline S5/S6/S27 individually. Reported as a blanket "
                             "keep-the-defaults authority, which is weaker than the register's "
                             "wording implies."),
    }
    print(f"[CPCV] adopt={out['adopt']}  recommended={out['recommended']}  pbo={out['pbo']}")
    return out



def s13_book(panel, dates):
    """Inverse-vol sizing INSIDE the top decile. The composite and therefore the MEMBERSHIP is
    unchanged (control C7), so the long-short leg is unchanged BY CONSTRUCTION."""
    res = {"note": "composite unchanged; only weights INSIDE the top decile move",
           "long_short_tstat_margin": "N/A - unchanged by construction, never a pass"}
    have_vol = "realized_vol" in panel.columns
    res["has_realized_vol"] = bool(have_vol)
    if not have_vol:
        res["status"] = "realized_vol not on the panel - arm not evaluable"
        return res

    eqr, ivr, cpr, fb, mem_ok = [], [], [], 0, True
    n_rows = 0
    for d, idx in panel.groupby("date").groups.items():
        sub = panel.loc[idx]
        s, f = sub["_deployed"], sub["fwd_ret"]
        m = s.notna() & f.notna()
        if m.sum() < 50:
            continue
        q = s[m].rank(pct=True)
        top = m[m].index[q >= 0.9]
        if len(top) < 5:
            continue
        fr = panel.loc[top, "fwd_ret"].astype(float)
        vol = pd.to_numeric(panel.loc[top, "realized_vol"], errors="coerce")
        n_rows += len(top)
        bad = vol.isna() | (vol <= 0)
        fb += int(bad.sum())
        v = vol.copy()
        v[bad] = vol[~bad].median() if (~bad).any() else 1.0     # fallback = equal-ish
        w = 1.0 / v
        w = w / w.sum()
        eq = np.repeat(1.0 / len(top), len(top))
        cap = S13_CAP_MULT / len(top)
        wc = np.minimum(w.values, cap)
        wc = wc / wc.sum()
        eqr.append(float(np.dot(eq, fr.values)))
        ivr.append(float(np.dot(w.values, fr.values)))
        cpr.append(float(np.dot(wc, fr.values)))

    def stats(x):
        a = np.array(x, dtype=float)
        sd = a.std(ddof=1)
        return {"ann_return": float(a.mean() * 4.0),
                "sharpe_per_period": float(a.mean() / sd) if sd > 0 else None,
                "worst_period": float(a.min()), "n": len(a),
                "max_drawdown": float(_dd(a))}

    res["equal_weight"] = stats(eqr)
    res["inverse_vol"] = stats(ivr)
    res["inverse_vol_capped_PRIMARY"] = stats(cpr)
    res["fallback_rate"] = fb / max(1, n_rows)
    res["C7_membership_identical"] = True   # by construction: one score selects the decile
    res["delta_alpha_capped_vs_equal"] = (res["inverse_vol_capped_PRIMARY"]["ann_return"]
                                          - res["equal_weight"]["ann_return"])
    print(f"[S13] equal ann {res['equal_weight']['ann_return']:+.4f} sharpe "
          f"{res['equal_weight']['sharpe_per_period']:.4f} maxDD "
          f"{res['equal_weight']['max_drawdown']:+.4f}")
    print(f"[S13] capped ann {res['inverse_vol_capped_PRIMARY']['ann_return']:+.4f} sharpe "
          f"{res['inverse_vol_capped_PRIMARY']['sharpe_per_period']:.4f} maxDD "
          f"{res['inverse_vol_capped_PRIMARY']['max_drawdown']:+.4f}  "
          f"fallback {res['fallback_rate']:.4f}")
    return res


def _dd(a):
    """Max drawdown of the compounded series. NEGATIVE; improvement is arm - base (S10)."""
    lvl = np.cumprod(1.0 + a)
    peak = np.maximum.accumulate(lvl)
    return float((lvl / peak - 1.0).min())


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
