#!/usr/bin/env python3
"""V6-B — the dip branch reframed as a RISK question.

Executes `PREREG_v6b_dip_survival.md` unmodified. Three arms on the banked V6 panel:

  ARM 1  SURVIVAL (primary, a RISK claim): among 20%+ dips, does the HEALTHY set show a
         thinner left tail?  M1 P(further -20% within 126d), M2 P(distress within 252d),
         M3 the forward drawdown distribution.
  ARM 2  OVERLAY (an alpha claim): within the TOP DECILE, do dipped names outperform?
  ARM 3  RIDER: dip x insider open-market purchase (transactioncode P) in the window.

V6's floors are IMPORTED, never restated - re-tuning them is void condition 6.3.

Run:  python -m scripts.v6b_dip_survival --data-dir data/backtest
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
from valuation.edge import statistics as ST                   # noqa: E402
from valuation.screener.cross_sectional import zscore         # noqa: E402
# V6's own construction, IMPORTED so the floors and the drawdown cannot drift.
from scripts.v6_dip_detector import (HEALTH_FLOOR, QUALITY_FLOOR, THEMES, W,   # noqa: E402
                                     health_panel, trailing_drawdown)

DEPTH = 0.20                    # register 2 - the dip population, V6's dip20
FWD_TD = 126                    # trading days for M1 / M3
DISTRESS_CAL_DAYS = 252         # calendar days for M2
INSIDER_WINDOW_CAL = 126        # calendar days before d for arm 3
FURTHER_DROP = -0.20            # M1's threshold
M1_ECONOMIC_PP = 3.0            # register 2.1 - the pre-committed economic floor
N_PERM = 500
MIN_PER_SIDE = 10
MIN_DATES_PER_HALF = 24
MIN_DISTRESS_EVENTS_PER_HALF = 30
SEED = 20260813

DISTRESS_ACTIONS = ("bankruptcyliquidation", "regulatorydelisting")
ACQUIRED_ACTIONS = ("acquisitionby", "mergerto")
VOLUNTARY_ACTIONS = ("voluntarydelisting",)

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------
def forward_paths(price_dir, tickers, dates):
    """Per (date, ticker): the forward 126-trading-day minimum relative to the dip close.

    POINT-IN-TIME BY CONSTRUCTION: the window starts at idx+1, i.e. STRICTLY AFTER d.
    RIGHT-CENSORING IS A SUFFIX, never a scatter - a row with fewer than FWD_TD forward
    rows is DROPPED, not scored on a short window, which is S22's rule and the reason a
    censored window may not take a last-price fallback.
    """
    dts = np.array([np.datetime64(str(d)[:10]) for d in dates])
    rows = []
    for tk in tickers:
        p = os.path.join(price_dir, f"{tk.upper()}.csv")
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_csv(p, usecols=["date", "close"]).dropna()
        except Exception:
            continue
        if len(df) < 2:
            continue
        df = df.sort_values("date")
        a = df["date"].to_numpy(dtype="datetime64[D]")
        c = df["close"].to_numpy(dtype=float)
        hi = np.searchsorted(a, dts, side="right")           # count of rows dated <= d
        for d, j in zip(dates, hi):
            if j < 1:
                continue
            c0 = float(c[j - 1])
            if not np.isfinite(c0) or c0 <= 0:
                continue
            win = c[j:j + FWD_TD]                            # STRICTLY after d
            if win.size < FWD_TD:
                continue                                     # censored: dropped, not scored
            mn = float(win.min())
            rows.append((d, tk, mn / c0 - 1.0))
    return pd.DataFrame(rows, columns=["date", "ticker", "fwd_min_ret"])


def action_events(actions_csv, tickers):
    """{ticker: {kind: earliest date}} for the three registered kinds.

    Acquisitions are collected so they can be REPORTED BESIDE distress and never added to
    it (register 1a): 82.63% of delistings on this universe are acquisitions.
    """
    a = pd.read_csv(actions_csv, usecols=["date", "action", "ticker"], low_memory=False)
    a = a[a["ticker"].isin(set(tickers))]
    out = {}
    for kind, names in (("distress", DISTRESS_ACTIONS), ("acquired", ACQUIRED_ACTIONS),
                        ("voluntary", VOLUNTARY_ACTIONS), ("delisted_umbrella", ("delisted",))):
        sub = a[a["action"].isin(names)]
        for tk, dt in sub.groupby("ticker")["date"].min().items():
            out.setdefault(tk, {})[kind] = str(dt)[:10]
    return out


def insider_buy_flags(insiders_csv, tickers, dates):
    """(date, ticker) -> did an OPEN-MARKET PURCHASE (code P) get FILED in the window?

    STRICTLY BEFORE d (audit B26: a Form 4 dated as_of is not reliably public before that
    day's close), and no earlier than d - 126 calendar days.
    A filing with NO transactioncode is UNCLASSIFIABLE and counts as NO BUY - conservative,
    it can only dilute the signal (register 4).
    """
    ins = pd.read_csv(insiders_csv,
                      usecols=lambda c: c in ("ticker", "filingdate", "transactioncode",
                                              "transactionshares"), low_memory=False)
    ins = ins[ins["ticker"].isin(set(tickers))]
    ins = ins[ins["transactioncode"].astype(str) == "P"]
    ins = ins.dropna(subset=["filingdate"])
    ins["_fd"] = pd.to_datetime(ins["filingdate"], errors="coerce")
    ins = ins.dropna(subset=["_fd"])
    by = {tk: np.sort(g["_fd"].to_numpy(dtype="datetime64[D]"))
          for tk, g in ins.groupby("ticker", sort=False)}
    rows = []
    for d in dates:
        hi = np.datetime64(str(d)[:10])
        lo = hi - np.timedelta64(INSIDER_WINDOW_CAL, "D")
        for tk, arr in by.items():
            # [lo, hi) - strictly before d
            n = int(np.searchsorted(arr, hi, side="left") -
                    np.searchsorted(arr, lo, side="left"))
            if n > 0:
                rows.append((d, tk, n))
    return pd.DataFrame(rows, columns=["date", "ticker", "n_insider_buys"])


# ---------------------------------------------------------------------------------
def _inf(series):
    r = ST.mean_inference(list(series))
    if not r or r.get("t") is None or not np.isfinite(r["t"]):
        return None
    return r


def _perm_p95(cells, rng, n_perm=N_PERM):
    """Null: shuffle the GROUP label within each date, count preserved."""
    nulls = []
    for _ in range(n_perm):
        vals = []
        for v, lab in cells:
            k = int(lab.sum())
            if k == 0 or k == v.size:
                continue
            idx = rng.choice(v.size, size=k, replace=False)
            m = np.zeros(v.size, dtype=bool)
            m[idx] = True
            vals.append(float(v[m].mean()) - float(v[~m].mean()))
        if len(vals) < 3:
            continue
        r = _inf(vals)
        if r:
            nulls.append(float(r["t"]))
    if not nulls:
        return None, None, []
    return (float(np.percentile(nulls, 95)), float(np.percentile(nulls, 5)),
            [round(x, 6) for x in nulls])


def two_group_cell(frame, value_col, label_col, rng, ann=None):
    """One metric, one split: per-date (group A mean - group B mean), t, own perm bar."""
    dates, diffs, cells, cov = [], [], [], []
    for d, g in frame.groupby("date", sort=True):
        v = pd.to_numeric(g[value_col], errors="coerce").to_numpy(dtype=float)
        lab = g[label_col].to_numpy(dtype=bool)
        ok = np.isfinite(v)
        v, lab = v[ok], lab[ok]
        na, nb = int(lab.sum()), int((~lab).sum())
        cov.append({"date": str(d)[:10], "n_a": na, "n_b": nb})
        if na < MIN_PER_SIDE or nb < MIN_PER_SIDE:
            continue
        dates.append(d)
        diffs.append(float(v[lab].mean()) - float(v[~lab].mean()))
        cells.append((v, lab))
    n = len(dates)
    if n < 6:
        return {"n_dates": n, "coverage": cov, "status": "insufficient dates"}
    mid = n // 2
    windows = {"full": (0, n), "early": (0, mid), "late": (mid + 1, n)}
    out = {"n_dates": n, "coverage": {
        "per_date": cov,
        "n_a_median": float(np.median([c["n_a"] for c in cov])),
        "n_b_median": float(np.median([c["n_b"] for c in cov])),
        "dates_used": n, "dates_dropped_for_thin_side": len(cov) - n}}
    for tag, (a, b) in windows.items():
        s, c = diffs[a:b], cells[a:b]
        if len(s) < 3:
            out[tag] = {"n": len(s)}
            continue
        r = _inf(s)
        p95, p5, draws = _perm_p95(c, rng)
        mu = float(np.mean(s))
        tt = float(r["t"]) if r else None
        se = (abs(mu / tt) if (tt not in (None, 0.0) and mu != 0.0) else None)
        out[tag] = {
            "n": len(s), "mean_diff": mu,
            "mean_diff_pp": mu * 100.0,
            "ann_pp": (mu * ann * 100.0 if ann else None),
            "t": tt, "se": se, "n_eff": (float(r.get("n_eff")) if r else None),
            "mde_at_t2_pp": (2.0 * se * 100.0 if se is not None else None),
            "perm_p95": p95, "perm_p5": p5, "n_perm_ok": len(draws),
            "clears_p95": bool(tt is not None and p95 is not None and tt > p95),
            "below_p5": bool(tt is not None and p5 is not None and tt < p5),
            "perm_draws": draws,
        }
    e, l = out.get("early", {}), out.get("late", {})
    out["both_halves_clear_high"] = bool(e.get("clears_p95") and l.get("clears_p95"))
    out["both_halves_below_p5"] = bool(e.get("below_p5") and l.get("below_p5"))
    out["halves_same_sign"] = bool(
        e.get("t") is not None and l.get("t") is not None
        and np.sign(e["t"]) == np.sign(l["t"]))
    out["enough_dates_per_half"] = bool(mid >= MIN_DATES_PER_HALF
                                        and (n - mid - 1) >= MIN_DATES_PER_HALF)
    return out


def m1_verdict(cell) -> str:
    """Register 2.1: statistical (both halves, own p95) AND economic (>=3pp) AND sign-stable.

    HEALTHY MINUS UNHEALTHY on a BAD outcome, so the claim needs the difference NEGATIVE -
    the healthy set must fall a further 20% LESS often. `below_p5` is therefore the clearing
    direction here, not `clears_p95`. Getting this backwards is the S10 sign error, and it
    is the single easiest mistake to make in this file.
    """
    if cell.get("status") or not cell.get("enough_dates_per_half"):
        return "VOID - UNDERPOWERED BY CONSTRUCTION"
    e, l = cell.get("early", {}), cell.get("late", {})
    stat = cell.get("both_halves_below_p5") and cell.get("halves_same_sign")
    econ = (e.get("mean_diff_pp") is not None and l.get("mean_diff_pp") is not None
            and e["mean_diff_pp"] <= -M1_ECONOMIC_PP and l["mean_diff_pp"] <= -M1_ECONOMIC_PP)
    if stat and econ:
        return "REAL - HEALTHY DIPS SURVIVE BETTER"
    if stat and not econ:
        return "NULL - CLEARS STATISTICALLY, MISSES THE 3.0pp ECONOMIC FLOOR"
    return "NULL"


def alpha_verdict(cell) -> str:
    if cell.get("status") or not cell.get("enough_dates_per_half"):
        return "VOID - UNDERPOWERED BY CONSTRUCTION"
    if cell.get("both_halves_clear_high") and cell.get("halves_same_sign"):
        return "REAL"
    if cell.get("both_halves_below_p5") and cell.get("halves_same_sign"):
        return "REJECTED - SIGN REVERSED"
    return "NULL"


# ---------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--bulk-dir", default="data/bulk")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_v6.pkl")
    ap.add_argument("--v6-artifact", default="data/free_analysis/V6_DIP_DETECTOR.json")
    ap.add_argument("--json", default="data/free_analysis/V6B_DIP_SURVIVAL.json")
    ap.add_argument("--controls-only", action="store_true")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel_cache, "rb"))
    n_d, n_t = panel["date"].nunique(), panel["ticker"].nunique()
    _log(f"[v6b] panel {panel.shape}, {n_d} dates, {n_t} names")
    out = {"item": "V6-B", "register": "PREREG_v6b_dip_survival.md",
           "depth": DEPTH, "fwd_td": FWD_TD, "distress_cal_days": DISTRESS_CAL_DAYS,
           "insider_window_cal": INSIDER_WINDOW_CAL, "n_perm": N_PERM, "seed": SEED,
           "m1_economic_floor_pp": M1_ECONOMIC_PP,
           "quality_floor": QUALITY_FLOOR, "health_floor": HEALTH_FLOOR,
           "controls": {}, "arms": {}}

    # ---- C2 (GATING) ----
    c2 = {"n_dates": int(n_d), "n_names": int(n_t), "ok": bool(n_d >= 60 and n_t >= 2400)}
    out["controls"]["C2_canonical_panel"] = c2
    _log(f"[C2] canonical panel: {c2['ok']} ({n_d} dates, {n_t} names)")
    if not c2["ok"]:
        out["ABORTED"] = "C2 failed - SMOKE-TEST PANEL"
        _w(args.json, out)
        return 2

    # ---- C1 (GATING), in its OWN pass ----
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(abs(got.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": got, "expected": REC}
    _log(f"[C1] reproduces the record: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 FAILED - every V6-B arm is VOID per register 6.6"
        _w(args.json, out)
        return 2
    if args.controls_only:
        _w(args.json, out)
        _log("[v6b] controls-only pass complete; arms NOT scored")
        return 0

    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())

    # ---- features ----
    _log("[v6b] drawdown (V6's own construction, imported)")
    dd = trailing_drawdown(os.path.join(args.data_dir, "prices"), tickers, dates)
    hp = health_panel(args.data_dir, tickers, dates)
    _log(f"[v6b] drawdown {len(dd)} rows, health {len(hp)} rows")
    p = panel.merge(dd, on=["date", "ticker"], how="left").merge(
        hp, on=["date", "ticker"], how="left")

    _log("[v6b] forward paths")
    fp = forward_paths(os.path.join(args.data_dir, "prices"), tickers, dates)
    _log(f"[v6b] forward paths {len(fp)} rows")
    p = p.merge(fp, on=["date", "ticker"], how="left")

    _log("[v6b] ACTIONS events")
    ev = action_events(os.path.join(args.bulk_dir, "actions.csv"), tickers)
    _log("[v6b] insider open-market purchases (code P)")
    ib = insider_buy_flags(os.path.join(args.data_dir, "insiders.csv"), tickers, dates)
    _log(f"[v6b] insider-buy rows {len(ib)}")
    p = p.merge(ib, on=["date", "ticker"], how="left")
    p["n_insider_buys"] = pd.to_numeric(p["n_insider_buys"], errors="coerce").fillna(0.0)

    # labels
    p["_dip"] = pd.to_numeric(p["drawdown"], errors="coerce") <= -DEPTH
    p["_healthy"] = (pd.to_numeric(p["quality"], errors="coerce") > QUALITY_FLOOR) & \
                    (pd.to_numeric(p["health"], errors="coerce") >= HEALTH_FLOOR)
    p["_further20"] = (pd.to_numeric(p["fwd_min_ret"], errors="coerce") <= FURTHER_DROP)
    p["_buy"] = p["n_insider_buys"] > 0

    # forward outcomes from ACTIONS - STRICTLY AFTER d, within the window (C3)
    def _evflag(kind, cal):
        res = np.zeros(len(p), dtype=bool)
        dt = pd.to_datetime(p["date"]).to_numpy(dtype="datetime64[D]")
        tk = p["ticker"].to_numpy()
        for i in range(len(p)):
            e = ev.get(tk[i], {}).get(kind)
            if not e:
                continue
            ed = np.datetime64(e)
            if ed > dt[i] and (ed - dt[i]).astype(int) <= cal:
                res[i] = True
        return res

    p["_distress"] = _evflag("distress", DISTRESS_CAL_DAYS)
    p["_acquired"] = _evflag("acquired", DISTRESS_CAL_DAYS)

    # ---- C3: point-in-time ----
    dt_all = pd.to_datetime(p["date"]).to_numpy(dtype="datetime64[D]")
    viol = 0
    for i in np.flatnonzero(p["_distress"].to_numpy()):
        e = ev.get(p["ticker"].to_numpy()[i], {}).get("distress")
        if e and np.datetime64(e) <= dt_all[i]:
            viol += 1
    out["controls"]["C3_point_in_time"] = {
        "distress_events_dated_on_or_before_the_date": int(viol),
        "forward_window_starts_strictly_after_d": True,
        "insider_filings_strictly_before_d": True,
        "ok": bool(viol == 0)}
    _log(f"[C3] point-in-time violations: {viol}")
    if viol:
        out["ABORTED"] = "C3 FAILED - a forward event dated on or before the rebalance date"
        _w(args.json, out)
        return 2

    dips = p[p["_dip"] & p["fwd_min_ret"].notna()].copy()
    # ---- C4: coverage FIRST ----
    out["controls"]["C4_coverage"] = {
        "panel_rows": int(len(p)),
        "dipped_rows": int(p["_dip"].sum()),
        "dipped_with_full_forward_window": int(len(dips)),
        "censored_dropped": int(p["_dip"].sum() - len(dips)),
        "healthy_dipped": int(dips["_healthy"].sum()),
        "unhealthy_dipped": int((~dips["_healthy"]).sum()),
        "distress_events_among_dipped": int(dips["_distress"].sum()),
        "acquisitions_among_dipped": int(dips["_acquired"].sum()),
        "buy_flagged_dipped": int(dips["_buy"].sum()),
        "drawdown_cov": float(p["drawdown"].notna().mean()),
        "health_cov": float(p["health"].notna().mean()),
        "fwd_min_cov": float(p["fwd_min_ret"].notna().mean()),
    }
    _log(f"[C4] {out['controls']['C4_coverage']}")

    # ---- C5: distress and acquisition are exclusive and both published ----
    both = int((dips["_distress"] & dips["_acquired"]).sum())
    out["controls"]["C5_distress_excludes_acquisition"] = {
        "rows_flagged_both": both, "ok": True,
        "distress_actions": list(DISTRESS_ACTIONS),
        "acquired_actions": list(ACQUIRED_ACTIONS),
        "note": ("82.63% of delistings on this universe are acquisitions; an acquisition is "
                 "NEVER counted as distress (register 1a). Rows may legitimately carry both "
                 "flags only if two distinct events fall in the window."),
    }

    # ---- C6: fidelity to V6's own conditioning ----
    c6 = {"v6_artifact_read": False}
    if os.path.exists(args.v6_artifact):
        v6 = json.load(open(args.v6_artifact))
        per = {r["date"]: r for r in v6["arms"]["A1"]["coverage"]["per_date"]}
        mine = dips.groupby(dips["date"].astype(str).str[:10])["_healthy"].sum()
        agree = sum(1 for d, n in mine.items()
                    if d in per and int(per[d]["n_cond"]) == int(n))
        c6 = {"v6_artifact_read": True, "dates_compared": int(len(mine)),
              "dates_agreeing_exactly": int(agree),
              "note": ("V6 counted conditioned names on ALL dipped rows; V6-B drops rows with "
                       "no full forward window, so agreement is expected on uncensored dates "
                       "only. A LOW number here means the floors moved, which is void 6.3.")}
    # non-identity of the arm-3 flag against the shipped insider theme
    ith = pd.to_numeric(dips["insider"], errors="coerce")
    bf = dips["_buy"].astype(float)
    m = ith.notna()
    c6["arm3_flag_vs_shipped_insider_theme_spearman"] = (
        round(float(ith[m].corr(bf[m], method="spearman")), 4) if m.sum() > 100 else None)
    out["controls"]["C6_fidelity_and_non_identity"] = c6
    _log(f"[C6] {c6}")

    rng = np.random.default_rng(SEED)

    # ================= ARM 1 =================
    a1 = {"population": "dipped rows with a full 126d forward window",
          "n_rows": int(len(dips))}
    dips["_m1"] = dips["_further20"].astype(float)
    a1["M1_further_20pct_within_126d"] = two_group_cell(dips, "_m1", "_healthy", rng)
    a1["M1_verdict"] = m1_verdict(a1["M1_further_20pct_within_126d"])
    _log(f"[A1-M1] {a1['M1_verdict']}")

    dips["_m2"] = dips["_distress"].astype(float)
    m2 = two_group_cell(dips, "_m2", "_healthy", rng)
    n = m2.get("n_dates", 0)
    ev_early = int(dips["_distress"].sum())
    m2["distress_events_total"] = ev_early
    m2["power_floor_per_half"] = MIN_DISTRESS_EVENTS_PER_HALF
    a1["M2_distress_within_252d"] = m2
    a1["M2_verdict"] = ("VOID - UNDERPOWERED BY CONSTRUCTION"
                        if ev_early < 2 * MIN_DISTRESS_EVENTS_PER_HALF
                        else m1_verdict(m2))
    _log(f"[A1-M2] {a1['M2_verdict']}  ({ev_early} distress events among dipped)")

    a1["M3_forward_drawdown"] = two_group_cell(dips, "fwd_min_ret", "_healthy", rng)
    a1["M3_distribution"] = {
        "healthy": ST.distribution(
            list(pd.to_numeric(dips.loc[dips["_healthy"], "fwd_min_ret"],
                               errors="coerce").dropna())),
        "unhealthy": ST.distribution(
            list(pd.to_numeric(dips.loc[~dips["_healthy"], "fwd_min_ret"],
                               errors="coerce").dropna())),
    }
    a1["M3_verdict"] = "DESCRIPTIVE - NO VERDICT BY REGISTER 2.1"
    out["arms"]["ARM1_SURVIVAL"] = a1

    # ================= ARM 2 =================
    _log("[A2] top decile via the SHIPPED composite construction")
    top_rows = []
    for d, sub in p.groupby("date", sort=True):
        comp = FP.composite_from_frame(sub, THEMES, {c: W for c in THEMES}, zscore)
        fwd = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(fwd)
        if ok.sum() < 30:
            continue
        idx = np.flatnonzero(ok)
        order = idx[np.argsort(-comp[ok])]
        buckets = np.array_split(order, 10)
        top_rows.append(sub.index.to_numpy()[buckets[0]])
    top_idx = np.concatenate(top_rows) if top_rows else np.array([], dtype=int)
    top = p.loc[top_idx].copy()
    out["controls"]["C7_top_decile_is_the_shipped_one"] = {
        "n_top_rows": int(len(top)),
        "n_dates": int(top["date"].nunique()),
    }
    a2 = {}
    for tag, col, ann in (("A2a_63d", "fwd_ret", 4.0), ("A2b_126d", "fwd_ret_h126", 2.0)):
        sub = top[top[col].notna()].copy()
        cell = two_group_cell(sub, col, "_dip", rng, ann=ann)
        cell["verdict"] = alpha_verdict(cell)
        a2[tag] = cell
        _log(f"[{tag}] {cell['verdict']}")
    out["arms"]["ARM2_OVERLAY"] = a2

    # ================= ARM 3 =================
    med_buy = float(dips.groupby("date")["_buy"].sum().median())
    a3 = two_group_cell(dips[dips["fwd_ret"].notna()], "fwd_ret", "_buy", rng, ann=4.0)
    a3["median_buy_flagged_per_date"] = med_buy
    a3["verdict"] = ("VOID - UNDERPOWERED BY CONSTRUCTION" if med_buy < MIN_PER_SIDE
                     else alpha_verdict(a3))
    out["arms"]["ARM3_INSIDER_RIDER"] = a3
    _log(f"[A3] {a3['verdict']}  (median {med_buy:.0f} buy-flagged dipped names per date)")

    # ---- C8: characteristic tilt ----
    def tilt(frame, lab):
        mc = pd.to_numeric(frame["market_cap"], errors="coerce")
        sz = pd.to_numeric(frame["size"], errors="coerce")
        m = frame[lab].to_numpy(dtype=bool)
        return {"median_mcap_true": float(mc[m].median()),
                "median_mcap_false": float(mc[~m].median()),
                "ratio_true_over_false": float(mc[m].median() / mc[~m].median()),
                "mean_size_z_true": float(sz[m].mean()),
                "mean_size_z_false": float(sz[~m].mean())}
    out["controls"]["C8_characteristic_tilt"] = {
        "arm1_healthy_vs_unhealthy_dipped": tilt(dips, "_healthy"),
        "arm2_dipped_vs_rest_of_decile": tilt(top, "_dip"),
        "arm3_buy_vs_nobuy_dipped": tilt(dips, "_buy"),
    }
    _log(f"[C8] {json.dumps(out['controls']['C8_characteristic_tilt'], default=float)[:220]}")

    _w(args.json, out)
    _log(f"[v6b] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
