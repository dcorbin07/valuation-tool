"""
Lazy prices — does the language-change signal predict returns? (roadmap #28, the gate)

`lazy_prices.py` BUILT the dataset (195 filers, 7,095 scored 10-K/10-Q pairs). This module
decides whether it is ALPHA or just a tidy dataset, using the same measurements every other
signal in this project has to clear: coverage first, then rank-IC + t, decile spread,
monotonicity, a held-out time split in both directions, and orthogonality to the existing
themes.

PRE-REGISTERED DIRECTION (fixed before any return was joined, and stated in the dataset's own
commit message a day earlier): **HIGHER similarity = "lazy" = BULLISH.** A negative result is a
REJECTION, not an invitation to flip the sign. Nothing in this file negates the measure.

Point-in-time, in three places:
  1. A score is usable only from its EDGAR FILING date. The panel requires
     `available_from < rebalance_date` — strictly earlier, so a filing that lands on the
     rebalance date itself (often after the close) is never traded on that day.
  2. Forward returns run from the rebalance date's close forward, never backwards.
  3. The similarity numbers themselves were computed with a point-in-time IDF corpus — see
     `lazy_prices.py`. Nothing here re-fits anything on the full sample.

WHAT THIS IS MEASURED ON, and why the verdict is weaker than the project's usual bar:
  * 194 survivor large caps (today's large-cap tier), NOT the survivorship-free 2,710-name
    Sharadar panel. That is the dataset that exists; it flatters results the same way the
    800-name runs did, so the METHODOLOGY RULE's "full universe" verdict is NOT available
    here and any number below must be read as a large-cap survivors' number.
  * ~10 years (2016-2026), not 18.
  * ~15-19 names per decile. The decile spread is the noisiest statistic in this file.

Overlapping windows are handled: with a monthly rebalance and a 63-day hold, consecutive
observations share two thirds of their forward window, so every t-stat is reported BOTH
plain and Newey-West corrected. Quote the Newey-West one.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------- config

DEFAULT_SCORES = os.path.join("data", "filings", "lazy_prices.csv")
DEFAULT_DATA_DIR = os.path.join("data", "backtest")
DEFAULT_OUT = os.path.join("data", "filings", "lazy_prices_ic.json")

# Whole-document measures first — they are corpus-free and were right the first time. The
# section measures rest on a heading heuristic that has already been wrong once (cross-
# references read as headings), so they are secondary evidence by construction.
MEASURES = ("cosine_tf", "jaccard", "cosine_tfidf",
            "mdna_cosine_tf", "mdna_jaccard", "risk_cosine_tf", "risk_jaccard")
PRIMARY_MEASURE = "cosine_tf"

HORIZONS = (21, 63, 126, 252)          # trading days ≈ 1 / 3 / 6 / 12 months
PRIMARY_HORIZON = 63                   # matches the panel's horizon and the paper's hold

MAX_STALE_DAYS = 120                   # a filing is "current" for one quarter + slack
MIN_DOC_WORDS = 2000                   # drop stub registrant filings (they score ~1.0 for
                                       # reasons unrelated to the paper's mechanism)
MAX_FFILL_DAYS = 10                    # a name quiet longer than this is not investable
MIN_NAMES = 20                         # smallest cross-section that gets an IC
MIN_DATES = 12
N_QUANTILES = 10


# ---------------------------------------------------------------------------- stats

def _rankdata(x):
    order = np.asarray(x, dtype=float).argsort()
    ranks = np.empty(len(order), dtype=float)
    ranks[order] = np.arange(len(order), dtype=float)
    return ranks


def spearman(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = ~(np.isnan(a) | np.isnan(b))
    if int(m.sum()) < 5:
        return float("nan")
    ar, br = _rankdata(a[m]), _rankdata(b[m])
    ar -= ar.mean(); br -= br.mean()
    den = math.sqrt(float((ar * ar).sum()) * float((br * br).sum()))
    return float((ar * br).sum() / den) if den > 0 else float("nan")


def tstat(x):
    """Plain t-stat of a mean. Valid only if the observations are independent."""
    a = np.asarray([v for v in x if v == v], dtype=float)
    if len(a) < 3:
        return None
    sd = float(a.std(ddof=1))
    return float(a.mean() / (sd / math.sqrt(len(a)))) if sd > 0 else None


def nw_tstat(x, lag):
    """Newey-West t-stat. With a monthly rebalance and an H-day hold, consecutive
    observations share (H/21 - 1) months of forward window; the plain t-stat treats those
    as independent draws and overstates significance by roughly sqrt(overlap). Report this
    one."""
    a = np.asarray([v for v in x if v == v], dtype=float)
    n = len(a)
    if n < 3:
        return None
    lag = int(max(0, min(lag, n - 2)))
    e = a - a.mean()
    var = float((e * e).sum()) / n
    for l in range(1, lag + 1):
        cov = float((e[l:] * e[:-l]).sum()) / n
        var += 2.0 * (1.0 - l / (lag + 1.0)) * cov
    if var <= 0:
        return None
    return float(a.mean() / math.sqrt(var / n))


def nw_lag_for(horizon_days, rebalance_months=1):
    """Months of overlap between consecutive observations, minus one."""
    months = max(1, int(round(horizon_days / 21.0)))
    return max(0, months - rebalance_months)


# ---------------------------------------------------------------------------- loading

def load_scores(path=DEFAULT_SCORES, min_words=MIN_DOC_WORDS, primary_only=True):
    """The built dataset, with the two dirty edges the coverage report flagged removed.

    Returns (frame, drops) — drops is the audit trail, because a filter that silently
    removes rows is how a 'clean' result gets manufactured.
    """
    df = pd.read_csv(path)
    drops = {"rows_in": int(len(df))}
    if primary_only and "doc_source" in df.columns:
        n = len(df)
        df = df[(df["doc_source"] == "primary") & (df["prior_doc_source"] == "primary")]
        drops["not_primary_document"] = int(n - len(df))
    if min_words:
        n = len(df)
        df = df[(df["n_words"] >= min_words) & (df["prior_n_words"] >= min_words)]
        drops["stub_filings_under_%d_words" % min_words] = int(n - len(df))
    df = df.copy()
    df["available_from"] = pd.to_datetime(df["available_from"])
    df = df.sort_values(["ticker", "available_from"]).reset_index(drop=True)
    drops["rows_kept"] = int(len(df))
    return df, drops


def load_prices(tickers, data_dir=DEFAULT_DATA_DIR):
    """Close frame on a union calendar. Sharadar SEP is already split-adjusted."""
    pdir = os.path.join(data_dir, "prices")
    series, missing = {}, []
    for t in tickers:
        fp = os.path.join(pdir, f"{t}.csv")
        if not os.path.exists(fp):
            missing.append(t)
            continue
        d = pd.read_csv(fp)
        if "date" not in d.columns or "close" not in d.columns or d.empty:
            missing.append(t)
            continue
        s = pd.Series(d["close"].astype(float).values, index=pd.to_datetime(d["date"]))
        series[t] = s[~s.index.duplicated(keep="last")].sort_index()
    if not series:
        return pd.DataFrame(), tickers
    frame = pd.DataFrame(series).sort_index()
    # A gap of a few days is a data hole; a long one means the name stopped trading, and
    # forward-filling through that would invent a flat return where there was a delisting.
    frame = frame.ffill(limit=MAX_FFILL_DAYS)
    return frame, missing


def month_end_dates(calendar):
    """Last trading day of each month present in the calendar."""
    cal = pd.DatetimeIndex(sorted(pd.DatetimeIndex(calendar).unique()))
    ser = pd.Series(cal, index=cal)
    return list(ser.groupby([cal.year, cal.month]).last().values)


# ---------------------------------------------------------------------------- panel

def build_panel(scores, closes, measure=PRIMARY_MEASURE, horizon=PRIMARY_HORIZON,
                max_stale_days=MAX_STALE_DAYS, within_form=False, dates=None):
    """(date, ticker) panel of the most recent usable similarity score + forward return.

    The signal at date D for ticker T is T's most recently FILED score with
    `available_from < D` — strictly earlier, never same-day — and only if that filing is
    less than `max_stale_days` old. Everything else about the row (the forward return) is
    measured from D forward.

    within_form=True z-scores the signal inside its form (10-K vs 10-Q) before ranking. A
    10-K and a 10-Q have different similarity distributions, and at any month-end the
    cross-section mixes both, so the raw ranking partly ranks FORM rather than laziness.
    """
    if closes.empty or scores.empty:
        return pd.DataFrame()
    cal = closes.index
    grid = list(dates) if dates is not None else month_end_dates(cal)
    pos = {d: i for i, d in enumerate(cal)}
    vals = closes.values
    col = {t: j for j, t in enumerate(closes.columns)}
    day = np.timedelta64(1, "D")
    # Per-ticker arrays sorted by filing date, so "the most recent filing strictly before D"
    # is a searchsorted instead of a per-cell frame filter (the naive version cost 97s a
    # pass, which made the measure x horizon grid impractical).
    prep = {}
    for t, g in scores.groupby("ticker"):
        if t not in col or measure not in g.columns:
            continue
        g = g.sort_values("available_from")
        prep[t] = (g["available_from"].values.astype("datetime64[ns]"),
                   g[measure].values.astype(float),
                   g["form"].values if "form" in g.columns else np.array([""] * len(g)),
                   col[t])
    rows = []
    for d in grid:
        ts = pd.Timestamp(d)
        i = pos.get(ts)
        if i is None or i + horizon >= len(cal):
            continue
        d64 = np.datetime64(ts)
        for t, (af, mv, fm, j) in prep.items():
            k = int(np.searchsorted(af, d64, side="left")) - 1   # strictly EARLIER only
            if k < 0:
                continue
            age = int((d64 - af[k]) / day)
            if age > max_stale_days:
                continue
            sig = mv[k]
            if sig != sig:
                continue
            p0, p1 = vals[i, j], vals[i + horizon, j]
            if not (p0 == p0 and p1 == p1 and p0 > 0):
                continue
            rows.append({"date": ts, "ticker": t, "signal": float(sig),
                         "form": str(fm[k]), "age_days": age,
                         "fwd_ret": float(p1 / p0 - 1.0)})
    panel = pd.DataFrame(rows)
    if panel.empty:
        return panel
    if within_form:
        grp = panel.groupby(["date", "form"])["signal"]
        mu, sd = grp.transform("mean"), grp.transform("std", ddof=0)
        panel["signal"] = np.where(sd.values > 0,
                                   (panel["signal"].values - mu.values)
                                   / np.where(sd.values > 0, sd.values, 1.0), 0.0)
    return panel.sort_values(["date", "ticker"]).reset_index(drop=True)


# ---------------------------------------------------------------------------- metrics

def ic_by_date(panel, min_names=MIN_NAMES):
    """Per-date rank-IC of the signal against the forward return, sign as pre-registered:
    positive IC = higher similarity earned more = the paper's claim."""
    out = []
    for d, sub in panel.groupby("date"):
        s = sub.dropna(subset=["signal", "fwd_ret"])
        if len(s) < min_names:
            continue
        ic = spearman(s["signal"].values, s["fwd_ret"].values)
        if ic == ic:
            out.append({"date": d, "ic": float(ic), "n": int(len(s))})
    return pd.DataFrame(out)


def summarize_ic(ics, horizon=PRIMARY_HORIZON):
    if ics is None or ics.empty or len(ics) < MIN_DATES:
        return {"status": "insufficient dates", "n_dates": 0 if ics is None else int(len(ics))}
    a = ics["ic"].values.astype(float)
    lag = nw_lag_for(horizon)
    return {"n_dates": int(len(a)),
            "mean_names": float(ics["n"].mean()),
            "mean_ic": float(a.mean()),
            "median_ic": float(np.median(a)),
            "ic_tstat": tstat(a),
            "ic_tstat_nw": nw_tstat(a, lag),
            "nw_lag": lag,
            "positive_fraction": float(np.mean(a > 0))}


def quantile_stats(panel, n_q=N_QUANTILES, horizon=PRIMARY_HORIZON):
    """Deciles, long-short and monotonicity — same conventions as the panel's
    `quantile_backtest`, deliberately, so the numbers are comparable.

    Buckets are ordered by argsort(-signal): bucket 0 is the HIGHEST similarity, i.e. the
    PREDICTED BEST under the pre-registered direction. So `monotonicity` is -1.0 when the
    signal is perfectly ordered and +1.0 when it is exactly backwards. (This project has
    read that sign backwards before; it is pinned by a test here too.)
    """
    q_rets = [[] for _ in range(n_q)]
    ls, ew, dates = [], [], []
    for d, sub in panel.groupby("date"):
        s = sub.dropna(subset=["signal", "fwd_ret"])
        if len(s) < n_q * 3:
            continue
        sig = s["signal"].values.astype(float)
        fwd = s["fwd_ret"].values.astype(float)
        order = np.argsort(-sig)
        buckets = np.array_split(order, n_q)
        for qi, b in enumerate(buckets):
            if len(b):
                q_rets[qi].append(float(np.mean(fwd[b])))
        ls.append(float(np.mean(fwd[buckets[0]]) - np.mean(fwd[buckets[-1]])))
        ew.append(float(np.mean(fwd)))
        dates.append(d)
    if len(ls) < MIN_DATES:
        return {"status": "insufficient periods", "n_periods": len(ls)}
    ppy = 252.0 / horizon
    lag = nw_lag_for(horizon)
    decile = [float(np.mean(q) * ppy) if q else None for q in q_rets]
    ew_ann = float(np.mean(ew) * ppy)
    mono = spearman(np.arange(n_q, dtype=float),
                    np.array([np.mean(q) if q else np.nan for q in q_rets]))
    return {"n_periods": len(ls), "n_quantiles": n_q, "horizon": horizon,
            "decile_ann_return": decile, "equal_weight_ann": ew_ann,
            "long_short_ann": float(np.mean(ls) * ppy),
            "long_short_tstat": tstat(ls),
            "long_short_tstat_nw": nw_tstat(ls, lag),
            "long_short_hit": float(np.mean([1.0 if x > 0 else 0.0 for x in ls])),
            "top_decile_alpha": (decile[0] - ew_ann) if decile[0] is not None else None,
            "bottom_decile_alpha": (decile[-1] - ew_ann) if decile[-1] is not None else None,
            "monotonicity": None if mono != mono else float(mono),
            "first_date": str(pd.Timestamp(dates[0]).date()),
            "last_date": str(pd.Timestamp(dates[-1]).date())}


# ---------------------------------------------------------------------------- held out

def holdout_split(panel, horizon=PRIMARY_HORIZON, min_dates=MIN_DATES):
    """Split the dates in half by TIME, embargo the boundary, and report each half's full
    statistics — then state whether the half that did NOT inform anything agrees.

    The direction here was pre-registered (high similarity = bullish) before any return was
    joined, so unlike the `low_risk` case there is no in-sample decision to confirm. What
    this tests is whether the relationship is STABLE: a signal that only works in one half
    of a ten-year window is noise dressed as an edge. Both directions are reported so no
    conclusion rests on one arbitrary split.
    """
    dates = sorted(panel["date"].unique())
    if len(dates) < 2 * min_dates:
        return {"status": f"only {len(dates)} dates"}
    mid = len(dates) // 2
    embargo = max(1, int(round(horizon / 21.0)))       # months of forward window to drop
    early = dates[:max(0, mid - embargo)]
    late = dates[mid:]
    out = {"embargo_periods": embargo,
           "pre_registered_direction": "positive IC (higher similarity = higher return)"}
    for name, ds in (("early", early), ("late", late)):
        sub = panel[panel["date"].isin(ds)]
        ics = ic_by_date(sub)
        out[name] = {"first_date": str(pd.Timestamp(ds[0]).date()),
                     "last_date": str(pd.Timestamp(ds[-1]).date()),
                     "ic": summarize_ic(ics, horizon),
                     "quantiles": quantile_stats(sub, horizon=horizon)}
    e, l = out["early"]["ic"], out["late"]["ic"]
    if "mean_ic" in e and "mean_ic" in l:
        agree = (e["mean_ic"] > 0) and (l["mean_ic"] > 0)
        out["both_halves_positive"] = bool(agree)
        out["confirmed"] = bool(agree and (l["ic_tstat_nw"] or 0) > 1.0
                                and (e["ic_tstat_nw"] or 0) > 1.0)
    return out


# ---------------------------------------------------------------------------- coverage

def coverage_report(scores, panel, drops, missing_prices, universe_size=None):
    """COVERAGE FIRST — the project rule. An empty or thin column produces a confident
    number and no error, which is how five factors ran empty here for a year."""
    cov = {"scored_pairs": int(len(scores)),
           "tickers": int(scores["ticker"].nunique()),
           "filters": drops,
           "tickers_without_price_history": missing_prices,
           "first_available": str(scores["available_from"].min().date()),
           "last_available": str(scores["available_from"].max().date())}
    if panel is not None and not panel.empty:
        per_date = panel.groupby("date").size()
        cov.update({"panel_rows": int(len(panel)),
                    "rebalance_dates": int(len(per_date)),
                    "names_per_date_median": float(per_date.median()),
                    "names_per_date_min": int(per_date.min()),
                    "names_per_date_max": int(per_date.max()),
                    "signal_age_days_median": float(panel["age_days"].median()),
                    "signal_age_days_p95": float(panel["age_days"].quantile(0.95)),
                    "form_mix": {str(k): int(v) for k, v in
                                 panel["form"].value_counts().items()},
                    "first_rebalance": str(panel["date"].min().date()),
                    "last_rebalance": str(panel["date"].max().date())})
    if universe_size:
        cov["share_of_sharadar_universe"] = round(cov["tickers"] / float(universe_size), 4)
    return cov


# ---------------------------------------------------------------------------- orthogonality

def theme_panel(tickers, data_dir=DEFAULT_DATA_DIR, rebalance_days=63, horizon=63,
                lookback_years=13):
    """The live panel's theme columns for these tickers. Read-only use of the production
    builder — this module imports the panel, the panel does not import this module (there
    is a test that keeps it that way)."""
    from ..edge.fundamental_panel import build_fundamental_panel
    from ..edge.data_providers import WRDSProvider

    class _Cfg:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_Cfg())
    return build_fundamental_panel(prov, list(tickers), rebalance_days=rebalance_days,
                                   lookback_years=lookback_years, horizon=horizon)


def attach_signal(tp, scores, measure=PRIMARY_MEASURE, max_stale_days=MAX_STALE_DAYS):
    """Same point-in-time rule as build_panel, applied to the theme panel's own dates."""
    if tp is None or tp.empty:
        return tp
    tp = tp.copy()
    tp["date_ts"] = pd.to_datetime(tp["date"])
    by_ticker = {t: g for t, g in scores.groupby("ticker")}
    sig, age = [], []
    for t, d in zip(tp["ticker"].values, tp["date_ts"].values):
        g = by_ticker.get(t)
        v, a = np.nan, np.nan
        if g is not None:
            usable = g[g["available_from"] < pd.Timestamp(d)]
            if not usable.empty:
                last = usable.iloc[-1]
                a = (pd.Timestamp(d) - last["available_from"]).days
                if a <= max_stale_days:
                    x = last.get(measure)
                    v = float(x) if x == x else np.nan
                else:
                    a = np.nan
        sig.append(v); age.append(a)
    tp["lazy"] = sig
    tp["lazy_age_days"] = age
    return tp


def _zscore(v):
    v = np.asarray(v, dtype=float)
    m = np.isfinite(v)
    out = np.full(len(v), np.nan)
    if m.sum() >= 3:
        x = v[m]
        sd = x.std(ddof=0)
        out[m] = (x - x.mean()) / sd if sd > 0 else 0.0
    return out


def orthogonality(tp, themes, horizon=63, weight=0.125, min_names=MIN_NAMES):
    """Does it add anything the existing themes don't already have?

    Three questions, three answers:
      1. correlation — mean per-date Spearman with each theme;
      2. residual IC — regress the signal on ALL theme z-scores each date and take the IC of
         what's left. If the residual IC dies, the signal was a repackaging;
      3. incremental — equal-weight composite of the themes, with and without the signal at
         one theme's weight. The only question that matters for adoption.
    """
    if tp is None or tp.empty or "lazy" not in tp.columns:
        return {"status": "no panel"}
    cols = [c for c in themes if c in tp.columns]
    corr = {c: [] for c in cols}
    raw_ic, res_ic, base_ls, with_ls, base_top, with_top = [], [], [], [], [], []
    n_dates = 0
    for d, sub in tp.groupby("date"):
        s = sub.dropna(subset=["lazy", "fwd_ret"])
        if len(s) < min_names:
            continue
        n_dates += 1
        lz = _zscore(s["lazy"].values)
        fwd = s["fwd_ret"].values.astype(float)
        raw_ic.append(spearman(lz, fwd))
        X, used = [], []
        for c in cols:
            z = _zscore(s[c].values)
            if np.isfinite(z).sum() >= min_names:
                corr[c].append(spearman(lz, z))
                X.append(np.where(np.isfinite(z), z, 0.0)); used.append(c)
        if X:
            A = np.column_stack([np.ones(len(s))] + X)
            beta, *_ = np.linalg.lstsq(A, np.where(np.isfinite(lz), lz, 0.0), rcond=None)
            res_ic.append(spearman(np.where(np.isfinite(lz), lz, 0.0) - A @ beta, fwd))
            comp = np.mean(np.column_stack(X), axis=1)
            comp_w = (comp * len(X) + np.where(np.isfinite(lz), lz, 0.0) * (len(X) * weight)) \
                / (len(X) * (1.0 + weight))
            for series, dst_ls, dst_top in ((comp, base_ls, base_top),
                                            (comp_w, with_ls, with_top)):
                order = np.argsort(-series)
                b = np.array_split(order, N_QUANTILES)
                dst_ls.append(float(np.mean(fwd[b[0]]) - np.mean(fwd[b[-1]])))
                dst_top.append(float(np.mean(fwd[b[0]]) - np.mean(fwd)))
    if n_dates < MIN_DATES:
        return {"status": f"only {n_dates} usable dates"}
    ppy = 252.0 / horizon
    lag = nw_lag_for(horizon, rebalance_months=max(1, int(round(horizon / 21.0))))

    def _ann(x):
        return float(np.mean(x) * ppy) if x else None

    return {"n_dates": n_dates,
            "theme_correlation": {c: (float(np.nanmean(v)) if v else None)
                                  for c, v in corr.items()},
            "max_abs_correlation": max(
                ((abs(float(np.nanmean(v))), c) for c, v in corr.items() if v),
                default=(None, None))[1],
            "raw_ic_mean": float(np.nanmean(raw_ic)),
            "raw_ic_tstat": tstat(raw_ic),
            "residual_ic_mean": float(np.nanmean(res_ic)) if res_ic else None,
            "residual_ic_tstat": tstat(res_ic),
            "themes_used": cols,
            "weight_tested": weight,
            "base_long_short_ann": _ann(base_ls),
            "with_signal_long_short_ann": _ann(with_ls),
            "base_long_short_tstat": tstat(base_ls),
            "with_signal_long_short_tstat": tstat(with_ls),
            "base_long_short_tstat_nw": nw_tstat(base_ls, lag),
            "with_signal_long_short_tstat_nw": nw_tstat(with_ls, lag),
            "base_top_decile_alpha": _ann(base_top),
            "with_signal_top_decile_alpha": _ann(with_top)}


# ---------------------------------------------------------------------------- verdict

def verdict(primary_ic, primary_q, hold, orth, cells_tested=None):
    """Adopt only if the signal is significant, stable across both halves, and adds
    something the themes don't already carry. Stated as a rule so it cannot be
    reverse-engineered after seeing the numbers."""
    reasons = []
    t = (primary_ic or {}).get("ic_tstat_nw")
    ls_t = (primary_q or {}).get("long_short_tstat_nw")
    mono = (primary_q or {}).get("monotonicity")
    sig = (t is not None and t > 2.0)
    reasons.append(f"IC t (Newey-West) {t if t is None else round(t, 3)} "
                   f"{'>' if sig else 'does not exceed'} 2.0")
    ls_ok = (ls_t is not None and ls_t > 2.0)
    reasons.append(f"long-short t (NW) {ls_t if ls_t is None else round(ls_t, 3)} "
                   f"{'>' if ls_ok else 'does not exceed'} 2.0")
    stable = bool((hold or {}).get("both_halves_positive"))
    reasons.append(("both halves positive" if stable else
                    "the two time halves do NOT agree in sign"))
    if mono is not None:
        reasons.append(f"monotonicity {round(mono, 3)} "
                       f"({'ordered' if mono < -0.3 else 'not cleanly ordered'}; "
                       f"-1.0 is ideal)")
    inc = None
    if orth and "with_signal_long_short_tstat_nw" in orth:
        b = orth.get("base_long_short_tstat_nw")
        w = orth.get("with_signal_long_short_tstat_nw")
        if b is not None and w is not None:
            inc = w - b
            reasons.append(f"adding it to the theme composite moves long-short t by "
                           f"{inc:+.3f}")
    if cells_tested:
        reasons.append(f"{cells_tested} measure x horizon cells were measured, so ~"
                       f"{0.05 * cells_tested:.1f} would clear |t|>2 on noise alone")
    adopt = bool(sig and ls_ok and stable and (inc is None or inc > 0.1))
    return {"adopt": adopt,
            "decision": "ADOPT" if adopt else "REJECT",
            "rule": ("adopt only if IC t(NW) > 2 AND long-short t(NW) > 2 AND both time "
                     "halves agree in the pre-registered direction AND it improves the "
                     "theme composite's long-short t by > 0.1"),
            "reasons": reasons}


# ---------------------------------------------------------------------------- run

ORTH_MEASURES = (PRIMARY_MEASURE, "mdna_cosine_tf")


def run(scores_path=DEFAULT_SCORES, data_dir=DEFAULT_DATA_DIR, measures=MEASURES,
        horizons=HORIZONS, do_orthogonality=True, out=DEFAULT_OUT, log=print,
        orth_measures=ORTH_MEASURES):
    scores, drops = load_scores(scores_path)
    tickers = sorted(scores["ticker"].unique())
    log(f"[ic] {len(scores):,} scored pairs over {len(tickers)} tickers "
        f"(after filters: {drops})")
    closes, missing = load_prices(tickers, data_dir)
    if closes.empty:
        return {"status": "no price history"}
    log(f"[ic] prices: {closes.shape[1]} tickers, {closes.shape[0]:,} days, "
        f"missing {missing}")

    panel = build_panel(scores, closes, PRIMARY_MEASURE, PRIMARY_HORIZON)
    res = {"config": {"scores": scores_path, "data_dir": data_dir,
                      "primary_measure": PRIMARY_MEASURE,
                      "primary_horizon_days": PRIMARY_HORIZON,
                      "rebalance": "month-end",
                      "max_stale_days": MAX_STALE_DAYS,
                      "min_doc_words": MIN_DOC_WORDS,
                      "pre_registered_direction": "higher similarity = bullish"},
           "coverage": coverage_report(scores, panel, drops, missing)}
    log("[ic] coverage: " + json.dumps({k: v for k, v in res["coverage"].items()
                                        if k not in ("filters",)}, default=str))

    # --- every measure x every horizon, so a single flattering cell can't be quoted alone
    grid = {}
    for meas in measures:
        if meas not in scores.columns:
            continue
        for h in horizons:
            p = build_panel(scores, closes, meas, h)
            if p.empty:
                continue
            ics = ic_by_date(p)
            grid[f"{meas}@{h}"] = {"ic": summarize_ic(ics, h),
                                   "quantiles": quantile_stats(p, horizon=h)}
            s = grid[f"{meas}@{h}"]
            log(f"[ic] {meas:>16s} h={h:3d}  IC {s['ic'].get('mean_ic')!s:.8s} "
                f"t(NW) {s['ic'].get('ic_tstat_nw')!s:.6s}  "
                f"LS ann {s['quantiles'].get('long_short_ann')!s:.8s} "
                f"t(NW) {s['quantiles'].get('long_short_tstat_nw')!s:.6s}")
    res["grid"] = grid

    # 28 cells means ~1.4 of them clear |t| > 2 by chance alone. Rather than let a reader
    # (or a later session) quote whichever one looks best, every cell that clears the bar is
    # re-tested on the two time halves automatically, and the expected false-positive count
    # is reported next to it.
    flagged = {}
    for key, s in grid.items():
        ict = s["ic"].get("ic_tstat_nw")
        lst = s["quantiles"].get("long_short_tstat_nw")
        if not ((ict is not None and abs(ict) > 2.0) or (lst is not None and abs(lst) > 2.0)):
            continue
        meas, h = key.split("@")
        p = build_panel(scores, closes, meas, int(h))
        wrong_sign = (ict is not None and ict < 0) or (lst is not None and lst < 0)
        flagged[key] = {"ic_tstat_nw": ict, "long_short_tstat_nw": lst,
                        "direction": ("OPPOSITE to the pre-registered one (high similarity "
                                      "UNDERperformed)" if wrong_sign else "as pre-registered"),
                        "holdout": holdout_split(p, int(h))}
    res["flagged_cells"] = {
        "cells_tested": len(grid),
        "expected_false_positives_at_abs_t_over_2": round(0.05 * len(grid), 1),
        "flagged": flagged,
        "note": ("A wrong-signed cell is NOT an inverted trading rule. The direction was "
                 "pre-registered; reading a negative result backwards is a new hypothesis "
                 "that would need its own out-of-sample test, not a rescue of this one.")}
    if flagged:
        log(f"[ic] {len(flagged)} of {len(grid)} cells cleared |t|>2 "
            f"(~{0.05 * len(grid):.1f} expected by chance): {sorted(flagged)}")

    ics = ic_by_date(panel)
    res["primary"] = {"ic": summarize_ic(ics, PRIMARY_HORIZON),
                      "quantiles": quantile_stats(panel, horizon=PRIMARY_HORIZON)}
    res["holdout"] = holdout_split(panel, PRIMARY_HORIZON)

    # form-mix control: does the raw ranking rank laziness, or 10-K vs 10-Q?
    wf = build_panel(scores, closes, PRIMARY_MEASURE, PRIMARY_HORIZON, within_form=True)
    res["within_form"] = {"ic": summarize_ic(ic_by_date(wf), PRIMARY_HORIZON),
                          "quantiles": quantile_stats(wf, horizon=PRIMARY_HORIZON)}

    if do_orthogonality:
        log("[ic] building the theme panel (this loads the Sharadar exports — minutes)")
        # Every measure is attached to ONE panel build. The build is the expensive part, and
        # the second measure here is the section score, which is the only place this dataset
        # showed anything with a stable sign (in the WRONG direction) — "is that just growth
        # or momentum wearing a different hat?" is the first question it invites.
        try:
            tp = theme_panel(tickers, data_dir, horizon=PRIMARY_HORIZON)
            if tp is None or tp.empty:
                res["orthogonality"] = {"status": "theme panel empty"}
            else:
                from ..screener import settings as S
                by_measure = {}                      # NOT `out` — that is the JSON path
                for meas in orth_measures:
                    if meas not in scores.columns:
                        continue
                    tpm = attach_signal(tp, scores, measure=meas)
                    by_measure[meas] = orthogonality(tpm, list(S.FACTORS_ALL),
                                                     horizon=PRIMARY_HORIZON)
                    by_measure[meas]["theme_panel_rows"] = int(len(tpm))
                    by_measure[meas]["theme_panel_dates"] = int(tpm["date"].nunique())
                res["orthogonality_by_measure"] = by_measure
                res["orthogonality"] = by_measure.get(PRIMARY_MEASURE,
                                                      {"status": "not run"})
        except Exception as e:                                   # noqa: BLE001
            res["orthogonality"] = {"status": f"failed: {type(e).__name__}: {e}"}
        log("[ic] orthogonality: " + json.dumps(res["orthogonality"], default=str)[:400])

    res["verdict"] = verdict(res["primary"]["ic"], res["primary"]["quantiles"],
                             res["holdout"], res.get("orthogonality"),
                             cells_tested=len(grid))
    log(f"[ic] VERDICT {res['verdict']['decision']}: "
        + "; ".join(res["verdict"]["reasons"]))
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, default=str)
        log(f"[ic] wrote {out}")
    return res


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Lazy prices — does it predict returns?")
    ap.add_argument("--scores", default=DEFAULT_SCORES)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--json", default=DEFAULT_OUT)
    ap.add_argument("--no-orthogonality", action="store_true",
                    help="skip the theme panel (fast; loses the incremental-IR test)")
    a = ap.parse_args(argv)
    r = run(a.scores, a.data_dir, out=a.json, do_orthogonality=not a.no_orthogonality)
    return 0 if r else 1


if __name__ == "__main__":
    sys.exit(main())
