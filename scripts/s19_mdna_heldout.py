"""S19 - the MD&A anomaly, re-tested on names that did not inform the observation.

Executes PREREG_s17_s19_events_mdna.md sections 1d, 1e and 3.

    python -m scripts.s19_mdna_heldout --json data/free_analysis/S19_MDNA.json

THE SIGN IS COMMITTED IN THE REGISTER AND IS NOT FITTED HERE: more MD&A change -> outperform,
so the change score (1 - similarity) is expected POSITIVELY related to forward return. A
significant NEGATIVE is a REJECT, never a discovery (register section 6.5).

Only two cells are tested - A1 `mdna_cosine_tf` at 21 days and A2 `mdna_jaccard` at 63 days,
the two the original study flagged. The original was a 28-cell grid; re-sweeping it is what the
register forbids.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from scripts.s17_event_codes import DATA, hac_t, load_prices  # noqa: E402

# --------------------------- REGISTERED CONSTANTS ---------------------------- #
ARMS = (("A1", "mdna_cosine_tf", 21), ("A2", "mdna_jaccard", 63))
THEMES = ["value", "quality", "growth", "momentum", "insider", "low_risk",
          "capital_discipline", "sentiment", "size", "institutional"]
MIN_DOC_WORDS = 2000          # the original study's own floor
MAX_STALE_DAYS = 120          # the original study's own staleness cap
MIN_NAMES_PER_DATE = 30       # register section 6.4
MIN_COVERED_DATES = 24        # register section 6.4
MIN_HELDOUT_NAMES = 100       # register section 6.4
C6_TARGET_IC = 0.00960710146449202
C6_TARGET_T = 0.6463239752818024
C6_TOL_IC = 0.002
C6_TOL_T = 0.15

ORIG_SCORES = os.path.join(DATA, "filings", "lazy_prices.csv")
NEW_SCORES = os.path.join(DATA, "filings_s19", "lazy_prices.csv")
PANEL_VOID = os.path.join(DATA, "free_analysis", "panel.pkl")
PANEL_CORR = os.path.join(DATA, "free_analysis", "panel_corrected_69d.pkl")


def _log(m):
    print(f"[s19] {m}", flush=True)


def load_scores(path: str) -> pd.DataFrame:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ("cosine_tf", "jaccard", "cosine_tfidf", "mdna_cosine_tf", "mdna_jaccard",
              "mdna_words", "n_words"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ticker"] = df["ticker"].str.upper()
    return df


def usable_scores(df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """The original study's own filters: primary document, >= 2,000 words, measure present."""
    d = df[(df.get("doc_source") == "primary") & (df["n_words"] >= MIN_DOC_WORDS)]
    d = d[np.isfinite(d[measure])]
    return d[["ticker", "available_from", measure]].sort_values("available_from")


def load_panel(path: str) -> pd.DataFrame:
    with open(path, "rb") as f:
        p = pickle.load(f)
    return p if isinstance(p, pd.DataFrame) else p.get("panel", p)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 5:
        return float("nan")
    # `.to_numpy()` can hand back a READ-ONLY view, and the in-place centring below then
    # raises. Caught by test_s19_change_ic_is_exactly_minus_similarity_ic before this ever
    # ran on real data.
    ra = np.array(pd.Series(a).rank(), dtype=float, copy=True)
    rb = np.array(pd.Series(b).rank(), dtype=float, copy=True)
    ra -= ra.mean()
    rb -= rb.mean()
    d = math.sqrt(float(ra @ ra) * float(rb @ rb))
    return float(ra @ rb) / d if d > 0 else float("nan")


def residualise(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """OLS residual of y on X (with intercept), NaN-safe by column-mean fill."""
    if X.size == 0:
        return y - y.mean()
    Z = np.column_stack([np.ones(len(y)), X])
    try:
        beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
        return y - Z @ beta
    except np.linalg.LinAlgError:
        return y - y.mean()


def build_cells(scores: pd.DataFrame, measure: str, panel: pd.DataFrame,
                prices: dict, horizon: int, names: set) -> list:
    """Per panel-date cross-sections: measure, themes, and a forward return at `horizon`."""
    by_tk = {}
    for tk, g in scores.groupby("ticker"):
        if tk in names:
            by_tk[tk] = (g["available_from"].to_numpy(),
                         g[measure].to_numpy(dtype=float))
    out = []
    for date, gp in panel.groupby("date"):
        d64 = np.datetime64(str(date)[:10], "D")
        rows = []
        for tk, th in zip(gp["ticker"].to_numpy(), gp[THEMES].to_numpy(dtype=float)):
            s = by_tk.get(tk)
            if s is None:
                continue
            # STRICTLY before the rebalance date - EDGAR filings land after the close, so
            # same-day use is a free look-ahead (the original study's own rule).
            i = int(np.searchsorted(s[0], str(date)[:10], side="left")) - 1
            if i < 0:
                continue
            age = (d64 - np.datetime64(s[0][i], "D")).astype(int)
            if age < 0 or age > MAX_STALE_DAYS:
                continue
            pr = prices.get(tk)
            if pr is None:
                continue
            ds, cs = pr
            j = int(np.searchsorted(ds, d64, side="right")) - 1
            if j < 0 or (d64 - ds[j]).astype(int) > 10 or j + horizon >= len(cs):
                continue
            fwd = float(cs[j + horizon]) / float(cs[j]) - 1.0
            rows.append((tk, float(s[1][i]), th, fwd, age))
        if len(rows) >= MIN_NAMES_PER_DATE:
            out.append((str(date)[:10], rows))
    return out


def score_cells(cells: list) -> dict:
    """Raw and residual IC per date, in BOTH conventions, plus NW t over dates."""
    raw_sim, res_sim, ages, ns = [], [], [], []
    r2s = []
    for _, rows in cells:
        sim = np.array([r[1] for r in rows], dtype=float)
        fwd = np.array([r[3] for r in rows], dtype=float)
        X = np.array([r[2] for r in rows], dtype=float)
        keep = np.isfinite(sim) & np.isfinite(fwd)
        if keep.sum() < MIN_NAMES_PER_DATE:
            continue
        sim, fwd, X = sim[keep], fwd[keep], X[keep]
        good = [k for k in range(X.shape[1]) if np.isfinite(X[:, k]).mean() > 0.5]
        Xg = X[:, good]
        col_mean = np.nanmean(Xg, axis=0)
        idx = np.where(~np.isfinite(Xg))
        Xg = Xg.copy()
        Xg[idx] = np.take(col_mean, idx[1])
        Xg = Xg[:, np.isfinite(col_mean)]
        resid = residualise(sim, Xg)
        ss = float(((sim - sim.mean()) ** 2).sum())
        r2s.append(1.0 - float((resid ** 2).sum()) / ss if ss > 0 else float("nan"))
        raw_sim.append(spearman(sim, fwd))
        res_sim.append(spearman(resid, fwd))
        ages.append(np.mean([r[4] for r in rows]))
        ns.append(len(sim))
    lag = 2
    t_raw = hac_t(np.array(raw_sim), lag)
    t_res = hac_t(np.array(res_sim), lag)
    return {
        "n_dates": len(res_sim),
        "mean_names": float(np.mean(ns)) if ns else None,
        "mean_signal_age_days": float(np.mean(ages)) if ages else None,
        "mean_residualisation_r2": float(np.nanmean(r2s)) if r2s else None,
        # SIMILARITY convention - what the original reported, used by control C6
        "raw_ic_similarity": t_raw[1], "raw_ic_t_similarity": t_raw[0],
        "residual_ic_similarity": t_res[1], "residual_ic_t_similarity": t_res[0],
        # CHANGE convention - the register's committed direction (change = 1 - similarity)
        "raw_ic_change": -t_raw[1] if np.isfinite(t_raw[1]) else None,
        "raw_ic_t_change": -t_raw[0] if np.isfinite(t_raw[0]) else None,
        "residual_ic_change": -t_res[1] if np.isfinite(t_res[1]) else None,
        "residual_ic_t_change": -t_res[0] if np.isfinite(t_res[0]) else None,
        "_per_date_residual_sim": res_sim,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DATA, "free_analysis", "S19_MDNA.json"))
    a = ap.parse_args()

    _log("loading prices")
    prices = load_prices()
    orig = load_scores(ORIG_SCORES)
    orig_names = set(orig["ticker"])
    _log(f"original study: {len(orig_names)} tickers, {len(orig):,} filing pairs")

    payload = {"item": "S19", "register": "PREREG_s17_s19_events_mdna.md",
               "arms": {}, "controls": {}}

    # ---------------- C6 FIRST: does my instrument reproduce the ORIGINAL number? -------
    _log("C6: reproducing the original study's published residual IC")
    c6 = {"target_residual_ic": C6_TARGET_IC, "target_t": C6_TARGET_T,
          "note": ("The original's orthogonality was built from data/backtest on 2026-08-03, "
                   "i.e. on the PRE-B6 panel the project has since declared void (its own "
                   "artifact records theme_panel_dates 49). A reproduction must therefore use "
                   "the original's own inputs; the VERDICT below runs on the corrected panel.")}
    for label, ppath in (("void_pre_b6_panel", PANEL_VOID),
                         ("corrected_69d_panel", PANEL_CORR)):
        if not os.path.exists(ppath):
            c6[label] = {"error": "panel missing"}
            continue
        pan = load_panel(ppath)
        pan = pan[[c for c in ("date", "ticker", *THEMES, "fwd_ret") if c in pan.columns]]
        sc = usable_scores(orig, "mdna_cosine_tf")
        cells = build_cells(sc, "mdna_cosine_tf", pan, prices, 63, orig_names)
        r = score_cells(cells)
        r.pop("_per_date_residual_sim", None)
        c6[label] = r
        _log(f"  {label}: residual IC(sim) {r['residual_ic_similarity']:+.6f} "
             f"t {r['residual_ic_t_similarity']:+.4f} over {r['n_dates']} dates")
    best = None
    for label in ("void_pre_b6_panel", "corrected_69d_panel"):
        r = c6.get(label) or {}
        if (r.get("residual_ic_similarity") is not None
                and abs(r["residual_ic_similarity"] - C6_TARGET_IC) <= C6_TOL_IC
                and abs(r["residual_ic_t_similarity"] - C6_TARGET_T) <= C6_TOL_T):
            best = label
    c6["reproduced_on"] = best
    c6["ok"] = best is not None
    payload["controls"]["C6_reproduces_original"] = c6
    _log(f"  C6 {'PASSED on ' + best if best else 'DID NOT REPRODUCE'}")

    # ---------------- the held-out arms -------------------------------------------------
    if not os.path.exists(NEW_SCORES):
        payload["verdict"] = "NO VERDICT - collection produced no scores file"
        payload["controls"]["C5_disjoint"] = {"ok": None}
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        _log("held-out scores absent - NO VERDICT")
        return 3

    new = load_scores(NEW_SCORES)
    new_names = set(new["ticker"])
    inter = sorted(new_names & orig_names)
    payload["controls"]["C5_disjoint_from_original"] = {
        "n_heldout_tickers": len(new_names), "n_original": len(orig_names),
        "intersection": inter, "ok": len(inter) == 0}
    _log(f"held-out: {len(new_names)} tickers with filings, "
         f"intersection with original = {len(inter)}")

    pan = load_panel(PANEL_CORR)
    pan = pan[[c for c in ("date", "ticker", *THEMES, "fwd_ret") if c in pan.columns]]

    underpowered = len(new_names) < MIN_HELDOUT_NAMES
    for tag, measure, horizon in ARMS:
        _log(f"arm {tag}: {measure} @ {horizon}d, held-out names only")
        sc = usable_scores(new, measure)
        cells = build_cells(sc, measure, pan, prices, horizon, new_names)
        full = score_cells(cells)
        per_date = full.pop("_per_date_residual_sim")
        half = len(cells) // 2
        halves = {}
        for hn, sub in (("early_half", cells[:half]), ("late_half", cells[half:])):
            r = score_cells(sub)
            r.pop("_per_date_residual_sim", None)
            halves[hn] = r
        ok_dates = full["n_dates"] >= MIN_COVERED_DATES
        # committed direction: change-IC POSITIVE, i.e. similarity-IC NEGATIVE
        t_change = full.get("residual_ic_t_change")
        clears = bool(t_change is not None and np.isfinite(t_change) and t_change > 2.0)
        signs = [halves[h].get("residual_ic_change") for h in ("early_half", "late_half")]
        same_sign = bool(all(s is not None and np.isfinite(s) for s in signs)
                         and np.sign(signs[0]) == np.sign(signs[1]))
        verdict = ("NO VERDICT - UNDERPOWERED" if (underpowered or not ok_dates)
                   else "POSITIVE" if (clears and same_sign and signs[0] > 0)
                   else "REJECTED" if (t_change is not None and np.isfinite(t_change)
                                       and t_change < -2.0)
                   else "NULL")
        payload["arms"][tag] = {
            "measure": measure, "horizon_days": horizon,
            "committed_direction": "change POSITIVE (more MD&A change -> outperform)",
            "full_sample": full, "halves": halves,
            "clears_nw_t_2_in_committed_direction": clears,
            "halves_same_sign": same_sign,
            "enough_dates": bool(ok_dates), "verdict": verdict}
        _log(f"  residual IC(change) {full['residual_ic_change']:+.6f} "
             f"t {t_change:+.4f} over {full['n_dates']} dates -> {verdict}")

    payload["underpowered"] = bool(underpowered)
    payload["min_thresholds"] = {"min_heldout_names": MIN_HELDOUT_NAMES,
                                 "min_covered_dates": MIN_COVERED_DATES,
                                 "min_names_per_date": MIN_NAMES_PER_DATE}
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    _log(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
