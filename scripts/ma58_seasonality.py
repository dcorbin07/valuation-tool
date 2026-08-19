"""MA58 - cross-sectional return seasonality (Heston-Sadka 2008; Keloharju-Linnainmaa-Nyberg 2016).

Executes PREREG_ma58_return_seasonality.md, committed ALONE at 6f998fc, a strict git ancestor of
this file. Trial budget booked at eb85ca7 BEFORE this ran (equity N 232 -> 234).

TWO PASSES, AND THE SPLIT IS THE POINT (session 26's defect, MA31/MA32's repair):

    python -m scripts.ma58_seasonality --controls-only    # C1..C6 + power; exits before any arm
    python -m scripts.ma58_seasonality --arms             # REFUSES without a passing artifact

A gating control computed in the same pass as the outcomes is not a gate.

THE LAG STRUCTURE IS THE HYPOTHESIS and is fixed in the register (section 2.1). The constants
below are that structure; changing any of them voids the item.

  SEASONAL     mean return over [t - k years, +3mo]                   k = 1..10
  NON-SEASONAL mean return over [t - k years + m months, +3mo]        k = 1..10, m in {3,6,9}

Both legs ask SORTING questions. There is no LEVEL leg and adding one is a void condition
(register section 2.5 - the P1S0-CONTROL lesson).

ADOPTS NOTHING. No file under valuation/ changes; settings.NUMBER_THEME is untouched.
"""
import argparse
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _data_root(repo):
    """`data/` is gitignored, so a WORKTREE has none of it. Resolve up to the checkout that owns
    the licensed export rather than creating a junction (S17's pattern and its reasoning)."""
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isdir(env):
        return env
    here = os.path.join(repo, "data")
    if os.path.isdir(os.path.join(here, "backtest", "prices")):
        return here
    p = repo
    for _ in range(6):
        p = os.path.dirname(p)
        cand = os.path.join(p, "data")
        if os.path.isdir(os.path.join(cand, "backtest", "prices")):
            return cand
    return here


DATA = _data_root(REPO)
PANEL = os.path.join(DATA, "free_analysis", "panel_corrected_69d.pkl")
PRICES_PKL = os.path.join(DATA, "free_analysis", "S17_PRICES.pkl")
PRICES_DIR = os.path.join(DATA, "backtest", "prices")
OUT_CTL = os.path.join(DATA, "free_analysis", "MA58_CONTROLS.json")
OUT_ARM = os.path.join(DATA, "free_analysis", "MA58_SEASONALITY.json")

# ---------------------------------------------------------------------------- #
#  REGISTERED CONSTANTS - changing any of these voids the item (register s8)
# ---------------------------------------------------------------------------- #
K_PRIMARY = 10                      # deepest whole decade uniformly available (register s2.1)
K_CONTROL = 5                       # C-DEPTH. CARRIES NO VERDICT.
WINDOW_MONTHS = 3                   # every window spans one quarter
NONSEAS_MONTHS = (3, 6, 9)          # the other three quarters of the same years
SNAP_TOL_DAYS = 10                  # a wider gap makes the window uncomputable, never imputed
INCUMBENTS = ("value", "quality", "momentum", "insider",
              "capital_discipline", "size", "institutional")
MIN_NAMES = 20                      # per-date minimum for the cross-sectional OLS
IC_BAR = 2.71                       # X7's calibrated theme-IC p95. A MILD EXTRAPOLATION here.
N_PERM = 500
PERM_SEED = 20260818
POWER_CONTROLS = ("z_gp_on_capital", "z_ret_6_1")
POWER_BAR = 2.0
DEGENERATE_RHO = 0.90               # C5: |rho(seas, nonseas)| above this flags the contrast
C1_RECORD = {                       # the published record, to seventeen significant figures
    "top_decile_alpha": 0.07174142332098163,
    "long_short_tstat": 2.8360640685320595,
    "monotonicity": -0.8909090909090909,
    "equal_weight_ann": 0.18137118752419476,
    "long_short_ann": 0.11038184616720666,
}
C2_EXPECT = {"eligible_frac": 0.7613, "min_per_date": 1199, "dates_below_100": 0}


def _log(m):
    print(m, flush=True)


# ---------------------------------------------------------------------------- #
#  FEATURES
# ---------------------------------------------------------------------------- #
def _offsets(k_max):
    """(years_back, months_forward). months 0 == same calendar quarter == ANNUAL LAG."""
    return [(k, m) for k in range(1, k_max + 1) for m in (0,) + NONSEAS_MONTHS]


def build_features(panel, px, k_max=K_PRIMARY):
    """Per (date, ticker): the seasonal and non-seasonal means, plus eligibility.

    A row is eligible only if ALL k annual and ALL 3k non-annual windows are computable, so both
    arms land on IDENTICAL rows -- which is what makes the section 4.2 contrast a comparison
    rather than two different samples (register s2.3, control C4).
    """
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    di = {d: i for i, d in enumerate(dates)}
    offs = _offsets(k_max)
    seas_cols = [j for j, (_k, m) in enumerate(offs) if m == 0]
    non_cols = [j for j, (_k, m) in enumerate(offs) if m != 0]
    tol = np.timedelta64(SNAP_TOL_DAYS, "D")

    A0 = np.empty((len(dates), len(offs)), dtype="datetime64[D]")
    A1 = np.empty_like(A0)
    for j, (yy, mm) in enumerate(offs):
        a = dates - pd.DateOffset(years=yy) + pd.DateOffset(months=mm)
        b = a + pd.DateOffset(months=WINDOW_MONTHS)
        A0[:, j] = a.values.astype("datetime64[D]")
        A1[:, j] = b.values.astype("datetime64[D]")

    # C3: no window may end after t.
    t_as = dates.values.astype("datetime64[D]")[:, None]
    c3_violations = int((A1 > t_as).sum())

    out = {"date": [], "ticker": [], "seas": [], "nonseas": [], "eligible": []}
    for t, g in panel.groupby("ticker", sort=False):
        if t not in px:
            continue
        d, c = px[t]
        if len(d) < 2:
            continue
        gd = pd.DatetimeIndex(g["date"].values)
        rows = np.array([di[x] for x in gd])
        s0, s1 = A0[rows], A1[rows]
        px0 = np.empty(s0.shape); px1 = np.empty(s0.shape)
        ok = np.ones(s0.shape, dtype=bool)
        for arr, dest in ((s0, px0), (s1, px1)):
            idx = np.searchsorted(d, arr.ravel(), side="right") - 1
            good = idx >= 0
            ic = np.clip(idx, 0, len(d) - 1)
            vals = c[ic]
            good &= (np.abs(arr.ravel() - d[ic]) <= tol)
            good &= np.isfinite(vals) & (vals > 0)
            dest[...] = vals.reshape(arr.shape)
            ok &= good.reshape(arr.shape)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = px1 / px0 - 1.0
        r[~ok] = np.nan
        elig = ok.all(axis=1)
        out["date"].append(gd.values)
        out["ticker"].append(np.repeat(t, len(gd)))
        out["seas"].append(np.where(elig, np.nanmean(r[:, seas_cols], axis=1), np.nan))
        out["nonseas"].append(np.where(elig, np.nanmean(r[:, non_cols], axis=1), np.nan))
        out["eligible"].append(elig)

    f = pd.DataFrame({k: np.concatenate(v) for k, v in out.items()})
    f["date"] = pd.to_datetime(f["date"])
    return f, c3_violations


# ---------------------------------------------------------------------------- #
#  THE VERDICT STATISTIC - incremental IC (PEAD/U2 template, register s2.4)
# ---------------------------------------------------------------------------- #
def _prep_dates(df, cand, ycol="fwd_ret"):
    """Per date: QR of the incumbent design, the candidate z, and the forward-return ranks.

    The residual projection depends only on X, so it is factorised once per date and reused for
    every permutation draw -- the permutation permutes y, never X.
    """
    from valuation.edge.fundamental_panel import _rankdata
    from valuation.screener.cross_sectional import zscore

    per = []
    for d, sub in df.groupby("date", sort=True):
        ss = sub.dropna(subset=[cand, ycol] + list(INCUMBENTS))
        if len(ss) < MIN_NAMES:
            continue
        z = zscore(ss[cand].astype(float))
        m = z.notna().values
        if int(m.sum()) < MIN_NAMES:
            continue
        X = np.column_stack([np.ones(int(m.sum()))] +
                            [ss[c].astype(float).values[m] for c in INCUMBENTS])
        Q, _ = np.linalg.qr(X)
        br = _rankdata(ss[ycol].astype(float).values[m])
        br = br - br.mean()
        per.append({"date": d, "z": z.values[m], "Q": Q, "br": br,
                    "bden": float(np.sqrt((br * br).sum())), "n": int(m.sum())})
    return per


def _ic_series(per, zs=None):
    """One incremental IC per date. `zs` overrides the candidate (permutation draws)."""
    from valuation.edge.fundamental_panel import _rankdata
    ics = []
    for i, p in enumerate(per):
        y = p["z"] if zs is None else zs[i]
        resid = y - p["Q"] @ (p["Q"].T @ y)
        ar = _rankdata(resid)
        ar = ar - ar.mean()
        den = np.sqrt((ar * ar).sum()) * p["bden"]
        ics.append(float((ar * p["br"]).sum() / den) if den > 0 else np.nan)
    return np.asarray(ics, dtype=float)


def _raw_ic_series(per):
    from valuation.edge.fundamental_panel import _rankdata
    ics = []
    for p in per:
        ar = _rankdata(p["z"]); ar = ar - ar.mean()
        den = np.sqrt((ar * ar).sum()) * p["bden"]
        ics.append(float((ar * p["br"]).sum() / den) if den > 0 else np.nan)
    return np.asarray(ics, dtype=float)


# C-DEGEN. `theme_ic`'s shipped guard is `sd > 0`, and whether a CONSTANT series has an exactly
# zero floating-point sd is VALUE- AND LENGTH-DEPENDENT (U2's finding). Measured here:
# [0.1, 0.1, 0.1] has sd 5.8e-17, passes `sd > 0`, and returns t = 1.019e16; the same list with a
# FOURTH element returns exactly 0.0. So `sd > 0` alone cannot keep an absurd t out of a verdict,
# and the register promised a degeneracy check that could (register s5, C-DEGEN).
#
# The replacement is a RELATIVE floor. It is deliberately inert on any real IC series -- those run
# sd ~ 0.05 against a mean ~ 0.02 -- and is PROVED inert rather than asserted so: re-running the
# arms across this change moved no cell (max |delta| 0.000e+00). The shipped `theme_ic` itself is
# NOT touched; changing it would make this lane's copy stop being the arithmetic X7's 2.71 bar was
# calibrated on, which is the defect this guard exists to avoid.
_SD_REL_FLOOR = 1e-12


def _tstat(a):
    """The SHIPPED `theme_ic` arithmetic plus C-DEGEN's relative floor. Returns (t, n, median)."""
    a = np.asarray([x for x in a if x == x], dtype=float)
    if len(a) < 2:
        return None, 0, None
    sd = float(a.std(ddof=1))
    degenerate = sd <= _SD_REL_FLOOR * max(1.0, abs(float(a.mean())))
    t = 0.0 if degenerate else float(a.mean() / (sd / (len(a) ** 0.5)))
    return t, len(a), float(np.median(a))


def _r2_on_incumbents(per):
    out = []
    for p in per:
        y = p["z"]
        resid = y - p["Q"] @ (p["Q"].T @ y)
        yc = y - y.mean()
        ss = float((yc * yc).sum())
        out.append(1.0 - float((resid * resid).sum()) / ss if ss > 0 else np.nan)
    return float(np.nanmean(out))


def _perm_null(per, n_perm=N_PERM, seed=PERM_SEED):
    """Within-date permutation of the CANDIDATE column (the within-column scheme -- `placebo_panel`
    is exactly invariant on a composite and would return a null equal to the real book)."""
    rng = np.random.default_rng(seed)
    ts = []
    for _ in range(n_perm):
        zs = [rng.permutation(p["z"]) for p in per]
        t, _n, _m = _tstat(_ic_series(per, zs))
        if t is not None:
            ts.append(t)
    return np.asarray(ts, dtype=float)


def _windows(dates):
    d = list(pd.DatetimeIndex(sorted(dates)))
    h = len(d) // 2
    return {"full": d, "early": d[:h], "late": d[h + 1:], "embargoed": d[h]}


def _cell(per, dates_keep, with_null=True, seed=PERM_SEED):
    sub = [p for p in per if p["date"] in dates_keep]
    ic = _ic_series(sub)
    t, n, med = _tstat(ic)
    raw_t, _, raw_med = _tstat(_raw_ic_series(sub))
    out = {"ic_tstat": t, "n_dates": n, "median_ic": med,
           "raw_ic_tstat": raw_t, "raw_median_ic": raw_med,
           "mean_r2_on_incumbents": _r2_on_incumbents(sub),
           "mean_names_per_date": float(np.mean([p["n"] for p in sub])) if sub else None}
    if with_null and sub:
        null = _perm_null(sub, seed=seed)
        out["perm_p95"] = float(np.percentile(null, 95))
        out["perm_p5"] = float(np.percentile(null, 5))
        out["perm_max"] = float(null.max())
        out["perm_n"] = int(len(null))
        out["clears_own_null"] = bool(t is not None and t >= out["perm_p95"])
    out["clears_2_71"] = bool(t is not None and t >= IC_BAR)
    return out


# ---------------------------------------------------------------------------- #
#  LOAD
# ---------------------------------------------------------------------------- #
def load():
    """The panel stores `date` as an ISO STRING. It is normalised to datetime64 here so the
    feature merge has one key type. ISO strings sort identically to their timestamps, so every
    groupby-date ordering is unchanged -- and C1 is the gate that proves it rather than this
    comment: if the conversion disturbed anything, the record no longer reproduces."""
    panel = pd.read_pickle(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    px = pd.read_pickle(PRICES_PKL)
    return panel, px


def _merge(panel, feats):
    df = panel.merge(feats, on=["date", "ticker"], how="left")
    return df[df["eligible"].fillna(False)].copy()


# ---------------------------------------------------------------------------- #
#  CONTROLS PASS
# ---------------------------------------------------------------------------- #
def controls():
    from valuation.edge.fundamental_panel import quantile_backtest
    from valuation.screener import cross_sectional as CS

    panel, px = load()
    out = {"item": "MA58", "generated": dt.datetime.now().isoformat(timespec="seconds"),
           "register": "PREREG_ma58_return_seasonality.md",
           "register_commit": "6f998fc", "budget_commit": "eb85ca7",
           "k_primary": K_PRIMARY, "adopts": None}

    # --- C-ROBUST: the shipped zscore must not be in robust mode (P6.3 rejected robust z)
    out["c_robust_z_off"] = (CS.USE_ROBUST_Z is False)

    # --- C1 GATE: the panel reproduces the published record
    W = {c: 0.125 for c in INCUMBENTS}
    r = quantile_backtest(panel, list(INCUMBENTS), W)
    c1 = {k: {"got": r.get(k), "record": v, "exact": r.get(k) == v}
          for k, v in C1_RECORD.items()}
    out["C1_record_reproduction"] = c1
    out["C1_pass"] = all(v["exact"] for v in c1.values())

    # --- features
    feats, c3 = build_features(panel, px, K_PRIMARY)
    df = _merge(panel, feats)

    # --- C2 GATE: eligibility reproduces the register's table
    per_date = df.groupby("date").size()
    panel_rows = len(panel)
    out["C2_eligibility"] = {
        "eligible_rows": int(len(df)), "panel_rows": int(panel_rows),
        "eligible_frac": round(len(df) / panel_rows, 4),
        "min_per_date": int(per_date.min()), "median_per_date": int(per_date.median()),
        "n_dates": int(per_date.size), "dates_below_100": int((per_date < 100).sum()),
        "first_date_n": int(per_date.iloc[0]), "last_date_n": int(per_date.iloc[-1]),
        "expected": C2_EXPECT}
    out["C2_pass"] = bool(
        abs(out["C2_eligibility"]["eligible_frac"] - C2_EXPECT["eligible_frac"]) <= 0.005
        and out["C2_eligibility"]["min_per_date"] == C2_EXPECT["min_per_date"]
        and out["C2_eligibility"]["dates_below_100"] == C2_EXPECT["dates_below_100"]
        and out["C2_eligibility"]["n_dates"] == 69)

    # --- C3 GATE: no window ends after t
    out["C3_windows_ending_after_t"] = int(c3)
    out["C3_pass"] = (c3 == 0)

    # --- C4: identical row sets
    a = set(map(tuple, df.loc[df["seas"].notna(), ["date", "ticker"]].values))
    b = set(map(tuple, df.loc[df["nonseas"].notna(), ["date", "ticker"]].values))
    out["C4_identical_rows"] = {"seas_rows": len(a), "nonseas_rows": len(b),
                                "identical": a == b}

    # --- C5: the two arms are not one column
    rhos = []
    for _d, sub in df.groupby("date"):
        s = sub[["seas", "nonseas"]].dropna()
        if len(s) >= MIN_NAMES:
            rhos.append(s["seas"].corr(s["nonseas"], method="spearman"))
    mr = float(np.nanmean(rhos))
    out["C5_seas_vs_nonseas"] = {"mean_per_date_spearman": mr,
                                 "degenerate": bool(abs(mr) > DEGENERATE_RHO),
                                 "bar": DEGENERATE_RHO}

    # --- C6: correlation against every theme column
    themes = [c for c in ("value", "quality", "growth", "momentum", "insider", "low_risk",
                          "capital_discipline", "sentiment", "size", "institutional")
              if c in df.columns]
    c6 = {}
    for arm in ("seas", "nonseas"):
        c6[arm] = {}
        for th in themes:
            v = []
            for _d, sub in df.groupby("date"):
                s = sub[[arm, th]].dropna()
                if len(s) >= MIN_NAMES:
                    v.append(s[arm].corr(s[th], method="spearman"))
            c6[arm][th] = float(np.nanmean(v)) if v else None
    out["C6_theme_correlations"] = c6

    # --- POWER CONTROLS on the identical eligible rows
    pw = {}
    for col in POWER_CONTROLS:
        if col not in df.columns:
            pw[col] = {"present": False}
            continue
        per = _prep_dates(df, col)
        raw_t, n, med = _tstat(_raw_ic_series(per))
        inc_t, _, _ = _tstat(_ic_series(per))
        pw[col] = {"present": True, "raw_ic_tstat": raw_t, "incremental_ic_tstat": inc_t,
                   "median_raw_ic": med, "n_dates": n,
                   "clears_2_0_raw": bool(raw_t is not None and abs(raw_t) >= POWER_BAR)}
    out["power_controls"] = pw
    out["power_pass"] = any(v.get("clears_2_0_raw") for v in pw.values())
    out["interpretation_note"] = (
        "If power_pass is false every null in this item is UNINTERPRETABLE - "
        "'could not be separated at this resolution' - and NOT a negative result."
        if not out["power_pass"] else
        "At least one known-real signal clears 2.0 raw on the eligible rows, so a null here "
        "is interpretable as a null rather than as low power.")

    w = _windows(df["date"].unique())
    out["windows"] = {"n_dates": len(w["full"]),
                      "early": [str(w["early"][0].date()), str(w["early"][-1].date())],
                      "embargoed": str(w["embargoed"].date()),
                      "late": [str(w["late"][0].date()), str(w["late"][-1].date())]}

    out["GATES_PASS"] = bool(out["C1_pass"] and out["C2_pass"] and out["C3_pass"]
                             and out["C4_identical_rows"]["identical"]
                             and out["c_robust_z_off"])
    os.makedirs(os.path.dirname(OUT_CTL), exist_ok=True)
    json.dump(out, open(OUT_CTL, "w"), indent=2, default=str)
    _log("[controls] C1 %s  C2 %s  C3 %s  C4 %s  robust-z-off %s  ->  GATES %s"
         % (out["C1_pass"], out["C2_pass"], out["C3_pass"],
            out["C4_identical_rows"]["identical"], out["c_robust_z_off"], out["GATES_PASS"]))
    _log("[controls] power: " + ", ".join(
        "%s raw t %s" % (k, None if not v.get("present") else round(v["raw_ic_tstat"], 4))
        for k, v in pw.items()))
    _log("[controls] wrote %s" % OUT_CTL)
    return out


# ---------------------------------------------------------------------------- #
#  ARMS PASS
# ---------------------------------------------------------------------------- #
def arms():
    if not os.path.exists(OUT_CTL):
        raise SystemExit("REFUSING: no controls artifact. Run --controls-only first.")
    ctl = json.load(open(OUT_CTL))
    if not ctl.get("GATES_PASS"):
        raise SystemExit("REFUSING: controls artifact does not pass its gates.")
    _log("[arms] controls artifact read and passing; proceeding.")

    panel, px = load()
    out = {"item": "MA58", "generated": dt.datetime.now().isoformat(timespec="seconds"),
           "register": "PREREG_ma58_return_seasonality.md",
           "register_commit": "6f998fc", "budget_commit": "eb85ca7",
           "trials_charged": 2, "equity_N_after": 234, "adopts": None,
           "controls": {"GATES_PASS": True, "power_pass": ctl["power_pass"],
                        "C2_eligible_frac": ctl["C2_eligibility"]["eligible_frac"],
                        "C5_mean_rho": ctl["C5_seas_vs_nonseas"]["mean_per_date_spearman"]},
           "bar_note": ("2.71 is X7's calibrated theme-IC p95, a MILD EXTRAPOLATION here: same 69 "
                        "dates and same h63 horizon, narrower cross-section (~76% of panel rows). "
                        "Not re-calibrated on this subsample - doing that after seeing the arms is "
                        "the error this project has already paid for twice.")}

    for label, K in (("primary_K%d" % K_PRIMARY, K_PRIMARY),
                     ("C_DEPTH_K%d" % K_CONTROL, K_CONTROL)):
        feats, _ = build_features(panel, px, K)
        df = _merge(panel, feats)
        w = _windows(df["date"].unique())
        block = {"k": K, "eligible_rows": int(len(df)),
                 "carries_verdict": (K == K_PRIMARY)}
        pers = {}
        for arm in ("seas", "nonseas"):
            per = _prep_dates(df, arm)
            pers[arm] = per
            block[arm] = {win: _cell(per, set(w[win]), seed=PERM_SEED + i)
                          for i, win in enumerate(("full", "early", "late"))}
            _log("[arms] %s %-8s full t %s  early t %s  late t %s" % (
                label, arm,
                None if block[arm]["full"]["ic_tstat"] is None else round(block[arm]["full"]["ic_tstat"], 4),
                None if block[arm]["early"]["ic_tstat"] is None else round(block[arm]["early"]["ic_tstat"], 4),
                None if block[arm]["late"]["ic_tstat"] is None else round(block[arm]["late"]["ic_tstat"], 4)))

        # --- CONTRAST: paired per-date IC difference, with its own within-date null
        block["contrast"] = _contrast(pers["seas"], pers["nonseas"], w)
        out[label] = block

    out["verdict"] = _verdict(out["primary_K%d" % K_PRIMARY], ctl)
    json.dump(out, open(OUT_ARM, "w"), indent=2, default=str)
    _log("[arms] VERDICT %s" % out["verdict"]["verdict"])
    _log("[arms] wrote %s" % OUT_ARM)
    return out


def _contrast(per_s, per_n, w, n_perm=N_PERM, seed=PERM_SEED + 77):
    """Paired per-date IC(seas) - IC(nonseas), against its own permutation null.

    SORTING vs SORTING: a difference of two rank statistics. No level quantity enters.
    """
    ds = [p["date"] for p in per_s]
    dn = {p["date"]: p for p in per_n}
    keep = [d for d in ds if d in dn]
    ps = [p for p in per_s if p["date"] in dn]
    pn = [dn[d] for d in keep]
    ic_s, ic_n = _ic_series(ps), _ic_series(pn)
    diff = ic_s - ic_n
    rng = np.random.default_rng(seed)
    out = {}
    for win in ("full", "early", "late"):
        keepset = set(w[win])
        m = np.array([d in keepset for d in keep])
        if m.sum() < 2:
            out[win] = {"mean_diff": None}
            continue
        t, n, med = _tstat(diff[m])
        sub_s = [p for p, k in zip(ps, m) if k]
        sub_n = [p for p, k in zip(pn, m) if k]
        null = []
        for _ in range(n_perm):
            zs = [rng.permutation(p["z"]) for p in sub_s]
            zn = [rng.permutation(p["z"]) for p in sub_n]
            dd = _ic_series(sub_s, zs) - _ic_series(sub_n, zn)
            tt, _a, _b = _tstat(dd)
            if tt is not None:
                null.append(tt)
        null = np.asarray(null, dtype=float)
        p95 = float(np.percentile(null, 95))
        out[win] = {"mean_diff": float(np.nanmean(diff[m])), "diff_tstat": t,
                    "median_diff": med, "n_dates": n, "perm_p95": p95,
                    "clears": bool(t is not None and t >= p95)}
    return out


def _verdict(block, ctl):
    """Register section 4.2, applied mechanically. No judgement call is available here."""
    if not ctl.get("power_pass"):
        return {"verdict": "UNINTERPRETABLE",
                "why": "Neither power control cleared raw ic_tstat 2.0 on the eligible rows, so "
                       "a null here means 'could not be separated at this resolution', not "
                       "'absent'. Fixed in the register before the controls ran."}
    a1 = block["seas"]
    legs = {w: bool(a1[w]["clears_2_71"] and a1[w].get("clears_own_null"))
            for w in ("full", "early", "late")}
    a1_clears = all(legs.values())
    con = block["contrast"]
    con_clears = bool(con["early"].get("clears") and con["late"].get("clears"))
    if not a1_clears:
        v, why = "REJECTED", (
            "A1 (annual-lag) fails the conjunction of X7's 2.71 and its own permutation p95 in "
            "at least one window. Legs: %s" % legs)
    elif con_clears:
        v, why = "REPLICATED", "A1 clears both bars in both halves and the contrast clears."
    else:
        v, why = "NOT-SEASONAL", (
            "A1 clears, but the non-annual windows predict as well - so the information is in "
            "PAST RETURNS GENERALLY, not in the season. This is a materially different claim "
            "from the paper's and may not be reported as MA58 replicating.")
    return {"verdict": v, "why": why, "a1_legs": legs, "contrast_clears": con_clears,
            "kind": "every leg is a SORTING question; no LEVEL statistic enters this rule "
                    "(register s2.5, the P1S0-CONTROL lesson)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    if a.controls_only:
        controls()
    elif a.arms:
        arms()
    else:
        ap.error("pass --controls-only or --arms")


if __name__ == "__main__":
    main()
