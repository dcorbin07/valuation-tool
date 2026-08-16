"""
Honest parameter search — how to tune Valquo without fooling ourselves.

The existing pipeline already does the two things most retail backtests skip: Combinatorial
Purged CV and a Deflated Sharpe. This module closes the remaining gaps, which are the ones
that actually let noise through:

  1. LOCKED HOLD-OUT. The most recent slice of history is carved off BEFORE any search and
     touched exactly once, at the end. Nothing else in the codebase has an untouched set.
  2. ONE DECLARED SEARCH SPACE. Weights and trade parameters are currently tuned in separate
     passes (weights under CPCV, trade params under the weaker single-path walk-forward). A
     multiple-testing correction is only meaningful if you know the total number of trials, so
     here every tunable — weight scheme, top_n, exit band, min hold, cap tier — is enumerated
     as ONE joint space and every config is scored on the IDENTICAL CPCV paths.
  3. THE DEPLOYED OBJECTIVE, NET OF COSTS. Selection currently maximizes IC but the book earns
     top-decile alpha. Optimizing a proxy and reporting the target is a silent mismatch, and an
     un-penalized objective always drifts toward high-turnover configs.
  4. ROBUST SELECTION, NOT argmax. Three changes that matter more than any optimizer:
       - rank by a LOWER CONFIDENCE BOUND across paths (mean - z*SE), not the mean, so a config
         that wins on average but is wild across paths loses to a steadier one;
       - PLATEAU SMOOTHING: average each config's score with its neighbours along the ORDERED
         parameter axes, so we pick the middle of a broad hill rather than a lone spike. A spike
         is noise; a plateau is signal. Cheapest anti-overfit win available.
       - INTERIORITY: a setting sitting at the edge of the tested grid is unverified on one
         side, so it cannot be called the centre of a plateau. Only interior configs are
         adoptable; a boundary winner is reported as "widen the grid and re-run" instead.
  5. A MULTIPLE-TESTING TEST THAT KNOWS THE CONFIGS ARE CORRELATED. The sqrt(2*ln N) haircut
     assumes N independent trials; our configs overlap heavily, so it is simultaneously too
     harsh (they aren't independent) and too lax (it ignores the joint distribution). White's
     (2000) Bootstrap Reality Check and Hansen's (2005) SPA test bootstrap the whole set
     jointly and return a family-wise p-value for "the best config really beats the baseline".
  6. A TRIALS LEDGER THAT DOES NOT RESET. The Deflated Sharpe is only honest if `n_trials`
     counts every config we have EVER looked at, across every run, not the 8 in the current
     call. We persist the running count and feed that.
  7. A PERMUTATION NULL. Shuffle forward returns within each date (killing all signal, keeping
     the structure) and re-run the ENTIRE selection procedure. The distribution of "best config
     found" under the null is the empirical noise floor, and gives a p-value that assumes
     nothing. It is also the only check that catches leakage the theory can't see.

Adoption requires ALL gates to pass. The expected and correct outcome of an honest search on a
weak signal is "keep the defaults" — this module is built to say that loudly.

References: Bailey & Lopez de Prado (2014) Deflated Sharpe; Bailey et al. (2017) PBO/CSCV;
White (2000) Reality Check; Hansen (2005) SPA; Politis & Romano (1994) stationary bootstrap;
Pardo (2008) on plateau selection.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os

import numpy as np
import pandas as pd

from ..edge import fundamental_panel as FP

# --------------------------------------------------------------------------------------
# Search space
#
# Each axis declares whether it is ORDERED (neighbouring values are genuinely adjacent, so
# plateau smoothing is meaningful) and whether each end of the range is an ARBITRARY TRUNCATION
# ("open") or a NATURAL LIMIT ("closed"). We refuse to adopt a config that sits on an open end,
# because we have not tested what lies beyond it. `min_hold=1` (no minimum) and `cap_tier=all`
# (the whole universe) are natural limits — nothing exists past them — so those are closed.
# --------------------------------------------------------------------------------------

AXES = {
    "scheme": {"values": ["current-default", "equal-weight", "ic-shrunk-50", "ic-proportional",
                          "ic-ir", "risk-parity", "max-ir-decorr", "positive-equal"],
               "ordered": False},
    # top_n runs to 50 and min_hold to 4 because a first pass put the leaders at top40/hold3 —
    # i.e. on the edge of the old grid, where interiority (correctly) refused to adopt them.
    # Widening until the winners sit inside the tested range is the required response to that.
    "top_n": {"values": [10, 15, 20, 25, 30, 40, 50], "ordered": True,
              "open_left": True, "open_right": True},
    "exit_band": {"values": [1.5, 2.0, 3.0, 4.0], "ordered": True, "open_left": True, "open_right": True},
    "min_hold": {"values": [1, 2, 3, 4], "ordered": True, "open_left": False, "open_right": True},
    "cap_tier": {"values": ["all", "top66", "top33", "top10"], "ordered": True,
                 "open_left": False, "open_right": True},
}

# A coarser space for a quick look. Every OPEN-ended axis still needs at least three values,
# otherwise no config is interior and nothing is adoptable at all.
FAST_AXES = {
    "scheme": {"values": ["current-default", "equal-weight", "ic-shrunk-50", "ic-ir", "max-ir-decorr"],
               "ordered": False},
    "top_n": {"values": [15, 25, 40], "ordered": True, "open_left": True, "open_right": True},
    "exit_band": {"values": [1.5, 2.0, 3.0], "ordered": True, "open_left": True, "open_right": True},
    "min_hold": {"values": [1, 2, 3], "ordered": True, "open_left": False, "open_right": True},
    "cap_tier": {"values": ["all", "top33", "top10"], "ordered": True, "open_left": False, "open_right": True},
}

# The incumbent — what is live today. Must exist inside whatever axes are used, or the whole
# comparison is meaningless. The incumbent is always eligible regardless of interiority: it is
# not something we "found", it is what we already run.
BASELINE = {"scheme": "current-default", "top_n": 25, "exit_band": 2.0, "min_hold": 2,
            "cap_tier": "all"}

CAP_FRACTION = {"all": 1.0, "top80": 0.80, "top66": 0.66, "top33": 0.33, "top10": 0.10}


def build_space(axes):
    keys = list(axes.keys())
    return [dict(zip(keys, vals)) for vals in itertools.product(*[axes[k]["values"] for k in keys])]


def check_axes(axes):
    """An OPEN-ended axis needs at least three values or no config on it can ever be interior,
    and the search would have nothing it is allowed to adopt."""
    bad = []
    for ax, spec in axes.items():
        if not spec.get("ordered"):
            continue
        need = 1 + int(bool(spec.get("open_left"))) + int(bool(spec.get("open_right")))
        if len(spec["values"]) < need:
            bad.append(f"{ax} has {len(spec['values'])} values but needs >= {need} "
                       f"(open ends: {'left ' if spec.get('open_left') else ''}"
                       f"{'right' if spec.get('open_right') else ''})")
    return bad


def cfg_key(cfg):
    return "|".join(f"{k}={cfg[k]}" for k in sorted(cfg))


def is_interior(cfg, axes):
    """True when no parameter sits on an OPEN end of its tested range. A config that fails this
    may still be the highest scorer — but the honest response is to widen the grid and re-run,
    not to adopt a setting we have only tested from one side."""
    for ax, spec in axes.items():
        if not spec.get("ordered"):
            continue
        vals = spec["values"]
        i = vals.index(cfg[ax])
        if i == 0 and spec.get("open_left"):
            return False
        if i == len(vals) - 1 and spec.get("open_right"):
            return False
    return True


def boundary_axes(cfg, axes):
    out = []
    for ax, spec in axes.items():
        if not spec.get("ordered"):
            continue
        vals = spec["values"]
        i = vals.index(cfg[ax])
        if (i == 0 and spec.get("open_left")) or (i == len(vals) - 1 and spec.get("open_right")):
            out.append(ax)
    return out


# --------------------------------------------------------------------------------------
# Panel preparation — z-scores computed ONCE, then everything is array math
# --------------------------------------------------------------------------------------

def prepare(panel, cols):
    """Precompute, per rebalance date: the z-scored theme matrix, a presence mask, forward
    returns and a global ticker id. Every config evaluation afterwards is pure numpy, which is
    what makes a 2,000-config x 15-path x 20-permutation search finish in minutes, not days."""
    from ..screener.cross_sectional import zscore

    tickers = sorted(panel["ticker"].unique())
    tid = {t: i for i, t in enumerate(tickers)}
    dates = sorted(panel["date"].unique())
    prep = []
    for d in dates:
        sub = panel[panel["date"] == d]
        Z = np.column_stack([zscore(sub[c]).values.astype(float) for c in cols])
        mask = np.isfinite(Z)
        mcap = sub["market_cap"].values.astype(float) if "market_cap" in sub else np.full(len(sub), np.nan)
        prep.append({
            "date": d,
            "ids": np.asarray([tid[t] for t in sub["ticker"].values], dtype=np.int64),
            "Z": np.where(mask, Z, 0.0),
            "mask": mask.astype(float),
            "fwd": sub["fwd_ret"].values.astype(float),
            "caps": {tier: _cap_mask(mcap, tier) for tier in CAP_FRACTION},
        })
    return {"dates": dates, "prep": prep, "n_tickers": len(tickers), "cols": list(cols)}


CAP_MIN_FINITE = 30        # below this a tier cannot be formed; the date is EXCLUDED, not widened


def _cap_mask(mc, tier):
    """Point-in-time market-cap tier mask: the largest `frac` of names BY THAT DATE'S caps, so
    the universe definition itself carries no look-ahead.

    AUDIT MA49(e) — A STARVED DATE IS NOW EMPTY, NOT UNIVERSAL. This used to
    `return np.ones(len(mc), dtype=bool)` when fewer than 30 names had a finite cap, i.e. a
    date on which the tier could not be formed silently contributed EVERY name — including the
    names whose cap was missing, since `ones` is wider even than `ok`. The label said
    "megacap" and the rows were "all". Mixing two universes under one label is the B12 defect
    (an alphabetical slice read as the largest N) in a different column, and it fails in the
    direction that looks like more data rather than less.

    The safe direction is to CONTRIBUTE NOTHING: a tier that cannot be formed has no opinion,
    and an empty mask makes the date drop out of that tier's series where a full mask made it
    dominate. `tier == "all"` is untouched — there the full universe IS the definition.
    """
    if tier == "all":
        return np.ones(len(mc), dtype=bool)
    ok = np.isfinite(mc)
    if ok.sum() < CAP_MIN_FINITE:
        return np.zeros(len(mc), dtype=bool)
    thresh = np.quantile(mc[ok], 1.0 - CAP_FRACTION[tier])
    return ok & (mc >= thresh)


def _composite(P, wv, sel):
    """Weighted mean of the present z-scores (missing themes neutralised, weights renormalised)
    — identical semantics to the live screener's combine step."""
    num = P["Z"][sel] @ wv
    den = P["mask"][sel] @ wv
    return np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)


# --------------------------------------------------------------------------------------
# Weight schemes — fit on TRAIN dates only, reusing the existing scheme menu verbatim
# --------------------------------------------------------------------------------------

def _ic_stats(prepd, idx, halflife_days):
    """Recency-weighted mean IC, IC vol and the cross-theme IC covariance, over `idx` dates."""
    prep, cols = prepd["prep"], prepd["cols"]
    n = len(cols)
    if not idx:
        return np.zeros(n), np.ones(n), np.eye(n)
    ref = pd.to_datetime(prep[max(idx)]["date"])
    rows, wts = [], []
    for i in idx:
        P = prep[i]
        fwd = P["fwd"]
        rows.append([FP._spearman(np.where(P["mask"][:, j] > 0, P["Z"][:, j], np.nan), fwd)
                     for j in range(n)])
        wts.append(0.5 ** ((ref - pd.to_datetime(P["date"])).days / max(1.0, halflife_days)))
    M = np.asarray(rows, dtype=float)
    w = np.asarray(wts, dtype=float)
    w = w / (w.sum() or 1.0)
    mu = np.zeros(n)
    for j in range(n):
        col = M[:, j]
        ok = ~np.isnan(col)
        mu[j] = float(np.sum(w[ok] * col[ok]) / (w[ok].sum() or 1.0)) if ok.any() else 0.0
    X = np.where(np.isnan(M), mu[None, :], M)
    Xc = X - mu[None, :]
    vol = np.sqrt(np.maximum((w[:, None] * Xc * Xc).sum(axis=0), 1e-12))
    Sigma = (Xc * w[:, None]).T @ Xc
    return np.nan_to_num(mu), vol, Sigma


def fit_schemes(prepd, train_idx, base, halflife_days=1260, fwd_override=None):
    """The weighting schemes, fit on the training dates of one path. Reuses
    fundamental_panel._weight_schemes so this search and the existing CPCV can never disagree
    about what 'max-ir-decorr' means."""
    cols = prepd["cols"]
    eq = {c: 1.0 / len(cols) for c in cols}
    if fwd_override is not None:                       # permutation null: refit on shuffled labels
        saved = [P["fwd"] for P in prepd["prep"]]
        for P, f in zip(prepd["prep"], fwd_override):
            P["fwd"] = f
        try:
            mu, vol, Sigma = _ic_stats(prepd, train_idx, halflife_days)
        finally:
            for P, f in zip(prepd["prep"], saved):
                P["fwd"] = f
    else:
        mu, vol, Sigma = _ic_stats(prepd, train_idx, halflife_days)
    return FP._weight_schemes(mu, vol, Sigma, cols, eq, base)


# --------------------------------------------------------------------------------------
# The deployed strategy, simulated fast and NET OF COSTS
#
# The expensive part of a simulation (compositing + sorting the cross-section) depends ONLY on
# the weight scheme and the cap tier — not on top_n / exit band / min hold. So we rank once per
# (path, scheme, cap tier) and replay the cheap holdings bookkeeping for every trade-parameter
# combination. That is the difference between a 5-minute and a 6-hour search.
# --------------------------------------------------------------------------------------

MAX_TOP_N = 64


def rank_dates(prepd, idx, wv, cap_tier, fwd_override=None):
    """Per-date ranking payload, computed once and replayed across trade parameters."""
    prep, N = prepd["prep"], prepd["n_tickers"]
    out = {}
    for i in idx:
        P = prep[i]
        sel = P["caps"][cap_tier]
        ids = P["ids"][sel]
        if len(ids) < 25:                     # too thin a cross-section to rank meaningfully
            continue
        fwd = (P["fwd"] if fwd_override is None else fwd_override[i])[sel]
        comp = _composite(P, wv, sel)
        score = np.where(np.isfinite(comp), comp, -np.inf)
        order = np.argsort(-score, kind="stable")
        rank_by_id = np.full(N, np.inf)
        rank_by_id[ids[order]] = np.arange(1, len(order) + 1, dtype=np.float64)
        fwd_by_id = np.full(N, np.nan)
        fwd_by_id[ids] = fwd
        ew = float(np.nanmean(fwd)) if np.isfinite(fwd).any() else np.nan
        if not np.isfinite(ew):
            continue
        out[i] = {"top": ids[order[:MAX_TOP_N]], "rank": rank_by_id, "fwd": fwd_by_id, "ew": ew}
    return out


def simulate(ranked, runs, top_n, exit_rank, min_hold, cost_bps=25.0):
    """Event-driven hold-until-it-drops-out simulation (mirrors the live sell logic), returning
    per-period alpha vs the equal-weight universe both NET and GROSS of turnover cost.

    Both are needed, and for different jobs. NET is the deployed objective, so it is what we
    SELECT on. GROSS is what the multiple-testing tests run on, because cost differences between
    configs are systematic rather than statistical: on data with no signal at all, a config that
    simply trades less genuinely beats a config that churns, so a significance test run on net
    performance reports "an edge" that is really just a lower commission bill.

    `runs` is a list of contiguous index runs. CPCV test sets are non-contiguous, so a position
    is not carried across a gap — each run starts flat. That is the conservative reading: we
    never credit a hold through periods we did not actually observe."""
    cost = cost_bps / 10000.0
    alphas, gross, dates = [], [], []
    for run in runs:
        held = np.empty(0, dtype=np.int64)
        entry = np.empty(0, dtype=np.int64)
        for step, i in enumerate(run):
            R = ranked.get(i)
            if R is None:
                continue
            # ---- SELL: out of the hysteresis band, past the minimum hold -----------------
            n_sold = 0
            if len(held):
                r = R["rank"][held]
                keep = ~((r > exit_rank) & ((step - entry) >= min_hold))
                n_sold = int((~keep).sum())
                held, entry = held[keep], entry[keep]
            # ---- BUY: top-N not already held ---------------------------------------------
            want = R["top"][:top_n]
            new = want[~np.isin(want, held)]
            if len(new):
                held = np.concatenate([held, new])
                entry = np.concatenate([entry, np.full(len(new), step, dtype=np.int64)])
            if not len(held):
                continue
            fr = R["fwd"][held]
            ok = np.isfinite(fr)
            if not ok.any():
                continue
            turnover = (len(new) + n_sold) / max(1, len(held))
            raw = float(fr[ok].mean()) - R["ew"]
            gross.append(raw)
            alphas.append(raw - turnover * cost)
            dates.append(i)
    return (np.asarray(alphas, dtype=float), np.asarray(gross, dtype=float),
            np.asarray(dates, dtype=int))


def _runs(idx):
    """Split a sorted index list into contiguous runs."""
    idx = sorted(idx)
    if not idx:
        return []
    runs, cur = [], [idx[0]]
    for a, b in zip(idx, idx[1:]):
        if b == a + 1:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    runs.append(cur)
    return runs


# --------------------------------------------------------------------------------------
# CPCV paths over indices
# --------------------------------------------------------------------------------------

def cpcv_index_paths(n, n_groups=6, k_test=2, embargo=1):
    """Same construction as fundamental_panel._cpcv_paths but over positional indices, so the
    contiguous-run logic above is straightforward. Train periods within `embargo` of any test
    period are purged — with rebalance == horizon, one period of embargo is exactly the span of
    a forward-return label, which is the leakage that needs cutting."""
    if n < 12:
        return []
    n_groups = max(3, min(n_groups, n // 3))
    if k_test >= n_groups:
        k_test = max(1, n_groups - 1)
    groups = [list(g) for g in np.array_split(range(n), n_groups)]
    paths = []
    for combo in itertools.combinations(range(n_groups), k_test):
        test = sorted(set(i for gi in combo for i in groups[gi]))
        tset = set(test)
        train = [i for i in range(n) if i not in tset and not any(abs(i - j) <= embargo for j in tset)]
        if len(train) >= 8 and len(test) >= 4:
            paths.append((train, test))
    return paths


# --------------------------------------------------------------------------------------
# Stationary bootstrap + White Reality Check / Hansen SPA
# --------------------------------------------------------------------------------------

def _stationary_bootstrap_idx(T, mean_block, rng):
    """Politis-Romano stationary bootstrap: geometric block lengths, wrapping. Preserves the
    serial dependence of the alpha series, which an iid bootstrap would destroy (and thereby
    understate the p-value)."""
    p = 1.0 / max(1.0, float(mean_block))
    idx = np.empty(T, dtype=np.int64)
    i = int(rng.integers(0, T))
    for t in range(T):
        idx[t] = i
        i = int(rng.integers(0, T)) if rng.random() < p else (i + 1) % T
    return idx


def reality_check(D, n_boot=2000, mean_block=3, seed=0):
    """White's Bootstrap Reality Check and Hansen's SPA test.

    D is [T x K]: the per-period performance DIFFERENTIAL of each of the K configs against the
    baseline. Both ask the family-wise question — "given that I searched all K of these, how
    likely is a best-of-K this good under the null that none beats the baseline?" — and because
    they bootstrap the K series jointly, they account for our configs being heavily correlated.
    That is exactly what the sqrt(2*ln N) haircut cannot do.

    Read SPA: the Reality Check is dragged toward 1 by every hopeless config in the space,
    whereas SPA recentres those out."""
    D = np.asarray(D, dtype=float)
    if D.ndim != 2:
        return {"status": "differential matrix must be 2-D"}
    T, K = D.shape
    if T < 8 or K < 1:
        return {"status": f"too few observations for a bootstrap reality check (T={T}, K={K})"}
    rng = np.random.default_rng(seed)
    dbar = D.mean(axis=0)

    boots = np.empty((n_boot, K), dtype=float)
    for b in range(n_boot):
        boots[b] = D[_stationary_bootstrap_idx(T, mean_block, rng)].mean(axis=0)

    rtT = math.sqrt(T)
    V = float(np.max(rtT * dbar))                                          # White RC statistic
    p_rc = float(np.mean(np.max(rtT * (boots - dbar[None, :]), axis=1) >= V))

    omega = np.std(rtT * boots, axis=0, ddof=1)
    omega = np.where(omega > 1e-12, omega, np.inf)                         # a dead series cannot win
    T_spa = float(max(0.0, np.max(rtT * dbar / omega)))
    A = (omega / rtT) * math.sqrt(2.0 * math.log(max(math.e, math.log(max(3, T)))))
    g = np.where(dbar >= -A, dbar, 0.0)                     # recentre only the not-hopeless rules
    Z = np.max(rtT * (boots - g[None, :]) / omega[None, :], axis=1)
    p_spa = float(np.mean(np.maximum(0.0, Z) >= T_spa))

    return {"n_obs": T, "n_configs": K, "n_boot": n_boot, "mean_block": mean_block,
            "best_mean_diff": float(np.max(dbar)), "rc_pvalue": p_rc, "spa_pvalue": p_spa,
            "note": "p < 0.05 = the best config's edge over the baseline survives the fact that "
                    "we searched all of them. SPA is the sharper of the two."}


# --------------------------------------------------------------------------------------
# Persistent trials ledger — the Deflated Sharpe is a lie if this resets each run
# --------------------------------------------------------------------------------------

class TrialsLedger:
    """Every distinct config we have ever evaluated, persisted. The Deflated Sharpe's `n_trials`
    should be the size of the RESEARCH PROGRAM, not of the current call — otherwise re-running a
    search with a tweaked space quietly launders away the multiple-testing penalty."""

    def __init__(self, path):
        self.path = path
        self.seen = {}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.seen = json.load(f).get("configs", {})
            except Exception:
                self.seen = {}

    def register(self, cfgs, tag=""):
        for c in cfgs:
            e = self.seen.setdefault(cfg_key(c), {"count": 0, "tag": tag})
            e["count"] += 1
        return self.n_trials

    @property
    def n_trials(self):
        return max(2, len(self.seen))

    def save(self):
        if not self.path:
            return
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"configs": self.seen, "distinct": len(self.seen)}, f, indent=2)


# --------------------------------------------------------------------------------------
# Scoring one full search pass (used for the real data AND for each permutation null)
# --------------------------------------------------------------------------------------

def _score_space(prepd, space, paths, base, halflife_days, cost_bps, fwd_override=None,
                 need_series=False, need_is=True):
    """Evaluate EVERY config on EVERY CPCV path. Weight schemes are fit on the path's training
    dates only; trade parameters carry no fit. Returns per-config OOS alpha across paths and,
    optionally, the path-averaged per-date alpha series (leak-free and time-aligned) that the
    bootstrap tests consume."""
    cols = prepd["cols"]
    n_dates = len(prepd["prep"])
    keys = [cfg_key(c) for c in space]
    kidx = {k: i for i, k in enumerate(keys)}
    per_path = {k: [] for k in keys}
    per_path_gross = {k: [] for k in keys}
    is_mat, oos_mat = [], []
    ser_sum = np.zeros((len(space), n_dates)) if need_series else None
    ser_cnt = np.zeros((len(space), n_dates)) if need_series else None
    gro_sum = np.zeros((len(space), n_dates)) if need_series else None

    # group the trade-parameter combos under each (scheme, cap_tier) so ranking is done once
    groups = {}
    for cfg in space:
        groups.setdefault((cfg["scheme"], cfg["cap_tier"]), []).append(cfg)

    for train, test in paths:
        cands = fit_schemes(prepd, train, base, halflife_days, fwd_override=fwd_override)
        tr_runs, te_runs = _runs(train), _runs(test)
        is_row = [np.nan] * len(space)
        oos_row = [np.nan] * len(space)
        for (scheme, tier), cfgs in groups.items():
            wv = np.asarray([cands[scheme][c] for c in cols], dtype=float)
            # The in-sample leg is only consumed by PBO. The permutation null does not compute
            # PBO, so skipping it there roughly halves the cost of the whole null.
            r_tr = rank_dates(prepd, train, wv, tier, fwd_override) if need_is else {}
            r_te = rank_dates(prepd, test, wv, tier, fwd_override)
            for cfg in cfgs:
                er = max(cfg["top_n"] + 1, int(round(cfg["top_n"] * cfg["exit_band"])))
                kw = dict(top_n=cfg["top_n"], exit_rank=er, min_hold=cfg["min_hold"], cost_bps=cost_bps)
                ci = kidx[cfg_key(cfg)]
                if need_is:
                    a_tr, _, _ = simulate(r_tr, tr_runs, **kw)
                    if len(a_tr):
                        is_row[ci] = float(a_tr.mean())
                a_te, g_te, d_te = simulate(r_te, te_runs, **kw)
                if len(a_te):
                    m = float(a_te.mean())
                    oos_row[ci] = m
                    per_path[keys[ci]].append(m)
                    per_path_gross[keys[ci]].append(float(g_te.mean()))
                    if need_series:
                        np.add.at(ser_sum[ci], d_te, a_te)
                        np.add.at(gro_sum[ci], d_te, g_te)
                        np.add.at(ser_cnt[ci], d_te, 1.0)
        is_mat.append(is_row)
        oos_mat.append(oos_row)

    series = series_gross = None
    if need_series:
        with np.errstate(invalid="ignore", divide="ignore"):
            series = np.where(ser_cnt > 0, ser_sum / np.maximum(ser_cnt, 1e-9), np.nan)
            series_gross = np.where(ser_cnt > 0, gro_sum / np.maximum(ser_cnt, 1e-9), np.nan)
    return {"per_path": per_path, "per_path_gross": per_path_gross, "is_mat": is_mat,
            "oos_mat": oos_mat, "keys": keys, "series": series, "series_gross": series_gross}


def _summarise(space, keys, per_path, z=1.0):
    """Per-config: mean OOS alpha, its standard error across paths, the LOWER CONFIDENCE BOUND
    we actually rank on, and the fraction of paths where it was positive."""
    rows = {}
    for cfg, k in zip(space, keys):
        arr = np.asarray(per_path[k], dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            rows[k] = {"cfg": cfg, "n": 0, "mean": None, "se": None, "lcb": None, "pos": None}
            continue
        m = float(arr.mean())
        se = float(arr.std(ddof=1) / math.sqrt(len(arr))) if len(arr) > 1 else float("inf")
        rows[k] = {"cfg": cfg, "n": int(len(arr)), "mean": m, "se": (se if np.isfinite(se) else None),
                   "lcb": (m - z * se) if np.isfinite(se) else m, "pos": float(np.mean(arr > 0))}
    return rows


def plateau_smooth(space, rows, axes):
    """Replace each config's score with the average over itself and its neighbours along the
    ORDERED axes (categorical axes such as the weighting scheme have no meaningful adjacency, so
    smoothing never crosses them). A lone peak gets pulled toward its surroundings; the centre of
    a broad, gently-sloping region survives. Picking the middle of a plateau instead of the
    global max is the classic — and still the most reliable — defence against tuning to noise."""
    ordered = [k for k, spec in axes.items() if spec.get("ordered")]
    pos = {k: {v: i for i, v in enumerate(axes[k]["values"])} for k in ordered}
    have = {cfg_key(c) for c in space}
    out = {}
    for c in space:
        k0 = cfg_key(c)
        own = rows[k0]["lcb"]
        if own is None:
            out[k0] = None
            continue
        vals = [own]
        for ax in ordered:
            i = pos[ax][c[ax]]
            for j in (i - 1, i + 1):
                if 0 <= j < len(axes[ax]["values"]):
                    nb = dict(c)
                    nb[ax] = axes[ax]["values"][j]
                    nk = cfg_key(nb)
                    if nk in have and rows[nk]["lcb"] is not None:
                        vals.append(rows[nk]["lcb"])
        out[k0] = float(np.mean(vals))
    return out


def _select(space, keys, rows, axes, baseline_key):
    """The selection rule: among INTERIOR configs (plus the incumbent), take the highest
    plateau-smoothed lower confidence bound."""
    smooth = plateau_smooth(space, rows, axes)
    eligible = [k for k, c in zip(keys, space)
                if smooth.get(k) is not None and k != baseline_key and is_interior(c, axes)]
    best = max(eligible, key=lambda k: smooth[k]) if eligible else None
    return smooth, best, eligible


# --------------------------------------------------------------------------------------
# The protocol
# --------------------------------------------------------------------------------------

def honest_search(panel, cols, base, axes=None, holdout_frac=0.2, n_groups=6, k_test=2,
                  halflife_days=1260, horizon=63, cost_bps=25.0, n_perm=20, n_boot=2000,
                  ledger_path=None, seed=0, progress=None):
    """Run the full protocol and return a verdict. The ordering of the stages below IS the
    protocol; see the module docstring for why each one is there."""
    log = progress or (lambda *a, **k: None)
    axes = axes or AXES
    bad = check_axes(axes)
    if bad:
        return {"status": "unusable search space: " + "; ".join(bad)}
    space = build_space(axes)
    ann = 252.0 / max(1, horizon)                         # per-period alpha -> annualised

    all_dates = sorted(panel["date"].unique())
    n_all = len(all_dates)
    if n_all < 20:
        return {"status": f"need >=20 rebalance dates for the full protocol, have {n_all}"}

    # --- Stage 0: lock the hold-out BEFORE anything else looks at the data ----------------
    n_hold = max(4, int(round(n_all * holdout_frac)))
    n_search = n_all - n_hold
    if n_search < 16:
        return {"status": "not enough history to both search and hold out"}
    search_dates, hold_dates = all_dates[:n_search], all_dates[n_search:]
    log(f"  locked hold-out: last {n_hold} rebalances ({hold_dates[0]} -> {hold_dates[-1]}) "
        f"untouched until the final check")

    panel_s = panel[panel["date"].isin(set(search_dates))]
    panel_h = panel[panel["date"].isin(set(hold_dates))]
    prepd = prepare(panel_s, cols)

    # --- Stages 1-3: one declared space, identical CPCV paths, cost-aware deployed objective
    paths = cpcv_index_paths(n_search, n_groups=n_groups, k_test=k_test)
    if not paths:
        return {"status": "insufficient dates for CPCV paths"}
    log(f"  search space: {len(space)} configs x {len(paths)} CPCV paths "
        f"= {len(space) * len(paths):,} out-of-sample evaluations")

    res = _score_space(prepd, space, paths, base, halflife_days, cost_bps, need_series=True)
    keys = res["keys"]
    rows = _summarise(space, keys, res["per_path"])

    bkey = cfg_key(BASELINE)
    if bkey not in rows:
        return {"status": f"baseline config {BASELINE} is not inside the declared space"}

    # --- Stage 4: robust selection (LCB + plateau smoothing + interiority) ----------------
    smooth, best_key, eligible = _select(space, keys, rows, axes, bkey)
    scored = [k for k in keys if rows[k]["mean"] is not None]
    argmax_key = max(scored, key=lambda k: rows[k]["mean"]) if scored else None
    unrestricted = max([k for k in keys if smooth.get(k) is not None], key=lambda k: smooth[k],
                       default=None)
    if best_key is None:
        return {"status": "no interior configs could be scored"}
    best, baseline = rows[best_key], rows[bkey]
    log(f"  selected (interior, plateau-smoothed LCB): {best['cfg']}")

    # --- Where did the improvement come from? --------------------------------------------
    # With turnover cost inside the objective, "trade less" beats the incumbent even when the
    # signal is worthless — a real economic gain, but NOT evidence of better stock selection.
    # simulate() already returned the gross leg alongside the net one, so splitting the two apart
    # costs nothing extra.
    grows = _summarise(space, keys, res["per_path_gross"])
    g_sel, g_base = grows[best_key]["mean"], grows[bkey]["mean"]
    net_edge = (best["mean"] - baseline["mean"]) if (best["mean"] is not None
                                                     and baseline["mean"] is not None) else None
    gross_edge = (g_sel - g_base) if (g_sel is not None and g_base is not None) else None
    decomp = {"net_edge_ann": (None if net_edge is None else net_edge * ann),
              "gross_edge_ann": (None if gross_edge is None else gross_edge * ann),
              "cost_saving_ann": (None if (net_edge is None or gross_edge is None)
                                  else (net_edge - gross_edge) * ann),
              "note": "gross_edge is better stock SELECTION; cost_saving is merely trading less. "
                      "An 'improvement' that is all cost_saving is a turnover finding, not alpha."}

    # --- Stage 5: family-wise significance across the WHOLE search ------------------------
    # The bootstrap tests run on the GROSS series. Cost differences between configs are
    # systematic, not statistical: measured on signal-free data, a config that simply trades less
    # beats the incumbent with a t-stat near 4 purely on commissions. A significance test fed net
    # performance therefore reports "a highly significant edge" that is nothing but a smaller
    # commission bill. Gross differentials isolate the only thing worth testing for — whether any
    # config is genuinely better at PICKING the stocks. The cost dimension is judged separately,
    # by the decomposition above and its own gate.
    series = res["series_gross"]
    bi = keys.index(bkey)
    # A config that could not be evaluated on most dates (e.g. a cap tier that leaves too thin a
    # cross-section) was never a real candidate — drop it from the family rather than throwing
    # away every date it is missing, which would otherwise starve the bootstrap of observations.
    coverage = np.isfinite(series).mean(axis=1)
    keep = [i for i in range(len(keys)) if i != bi and coverage[i] >= 0.90]
    rc = {"status": "not enough dates common to the candidate family"}
    if keep:
        rowsok = np.isfinite(series[keep + [bi]]).all(axis=0)
        valid_t = np.where(rowsok)[0]
        if len(valid_t) >= 8:
            D = (series[np.ix_(keep, valid_t)] - series[bi, valid_t][None, :]).T   # [T x K]
            rc = reality_check(D, n_boot=n_boot, mean_block=3, seed=seed)
            if not rc.get("status"):
                rc["best_config_by_diff"] = space[keep[int(np.argmax(D.mean(axis=0)))]]
                rc["n_configs_dropped_for_coverage"] = len(keys) - 1 - len(keep)
    log(f"  bootstrap reality check: SPA p = {rc.get('spa_pvalue')}")

    pbo = FP._pbo(res["is_mat"], res["oos_mat"], keys)

    # Deflated Sharpe on the SELECTED config's leak-free OOS series, with n_trials from the
    # persistent ledger (this run's configs included).
    ledger = TrialsLedger(ledger_path) if ledger_path else None
    n_trials = len(space)
    if ledger:
        n_trials = ledger.register(space, tag="honest_search")
        ledger.save()
    # The Deflated Sharpe is about the DEPLOYED strategy standing on its own, so it runs on the
    # net series — unlike the reality check, which compares configs and must strip costs out.
    series_net = res["series"]
    sr_all = []
    for i in range(len(keys)):
        s = series_net[i][np.isfinite(series_net[i])]
        sr_all.append(float(s.mean() / s.std(ddof=1)) if len(s) > 2 and s.std(ddof=1) > 0 else None)
    ok_sr = [x for x in sr_all if x is not None]
    sel_series = series_net[keys.index(best_key)]
    sel_series = sel_series[np.isfinite(sel_series)]
    from ..edge.statistics import deflated_sharpe_ratio
    dsr = deflated_sharpe_ratio(sel_series.tolist(), n_trials=n_trials,
                                var_trials=(float(np.var(ok_sr, ddof=1)) if len(ok_sr) > 1 else None))

    # --- Stage 6: permutation null — re-run the ENTIRE selection on signal-free data -------
    perm = {"status": "skipped"}
    if n_perm and n_perm > 0:
        if n_perm < 20:
            log(f"  WARNING: {n_perm} permutations cannot resolve p < 0.05 (the smallest attainable "
                f"p is 1/{n_perm + 1} = {1.0 / (n_perm + 1):.3f}), so that gate will fail by "
                f"construction. Use 20 or more for a decisive run.")
        rng = np.random.default_rng(seed + 991)
        nulls = []
        for p in range(n_perm):
            override = []
            for P in prepd["prep"]:
                f = P["fwd"].copy()
                rng.shuffle(f)                            # break the name<->return link only
                override.append(f)
            r = _score_space(prepd, space, paths, base, halflife_days, cost_bps,
                             fwd_override=override, need_series=False, need_is=False)
            rr = _summarise(space, r["keys"], r["per_path"])
            _, nb, _ = _select(space, r["keys"], rr, axes, bkey)
            if nb is not None:
                sm = plateau_smooth(space, rr, axes)
                nulls.append(sm[nb] - (rr[bkey]["lcb"] if rr[bkey]["lcb"] is not None else 0.0))
                log(f"    permutation {p + 1}/{n_perm}: best null edge over baseline "
                    f"{nulls[-1] * ann:+.2%}/yr")
        if nulls:
            obs = smooth[best_key] - (rows[bkey]["lcb"] or 0.0)
            perm = {"n_perm": len(nulls), "observed_edge": obs,
                    "null_edge_mean": float(np.mean(nulls)),
                    "null_edge_p95": float(np.percentile(nulls, 95)),
                    "pvalue": float((np.sum(np.asarray(nulls) >= obs) + 1) / (len(nulls) + 1)),
                    "min_achievable_pvalue": float(1.0 / (len(nulls) + 1)),
                    "note": "fraction of signal-free re-runs whose BEST config beat the baseline by "
                            "at least as much as ours did. High = we are harvesting search luck."}

    # --- Stage 7: the hold-out, touched exactly once --------------------------------------
    hold = {"status": "not evaluated"}
    if panel_h["date"].nunique() >= 4:
        prepd_h = prepare(panel_h, cols)
        fitted = fit_schemes(prepd, list(range(n_search)), base, halflife_days)   # SEARCH window only
        hr = _runs(list(range(len(prepd_h["prep"]))))

        def _ho(cfg):
            wv = np.asarray([fitted[cfg["scheme"]][c] for c in prepd_h["cols"]], dtype=float)
            er = max(cfg["top_n"] + 1, int(round(cfg["top_n"] * cfg["exit_band"])))
            rk = rank_dates(prepd_h, list(range(len(prepd_h["prep"]))), wv, cfg["cap_tier"])
            a, _, _ = simulate(rk, hr, top_n=cfg["top_n"], exit_rank=er, min_hold=cfg["min_hold"],
                               cost_bps=cost_bps)
            return (float(a.mean()) if len(a) else None), int(len(a))

        sa, sn = _ho(rows[best_key]["cfg"])
        ba, _ = _ho(BASELINE)
        hold = {"n_periods": sn, "selected_alpha_ann": (None if sa is None else sa * ann),
                "baseline_alpha_ann": (None if ba is None else ba * ann),
                "selected_beats_baseline": (None if (sa is None or ba is None) else bool(sa > ba)),
                "note": "evaluated ONCE, after selection was final, with weights fit on the search "
                        "window only. A sanity check — not a further selection step."}

    # --- The gate: every check must pass ---------------------------------------------------
    #
    # The White/Hansen p-values are deliberately NOT gates, and that is a measured decision, not
    # a preference. Run this whole protocol on 20 independent signal-free panels and the SPA test
    # returns p < 0.05 on ~35% of them. It is not a broken implementation — hand it the same
    # differentials with each column demeaned (so the null is true by construction) and it returns
    # p ~ 1.0 every time, i.e. it is conservative when its null actually holds. The problem is
    # that its null ("no config beats the benchmark") is compared against ONE realisation of the
    # benchmark, and when that realisation is unlucky, essentially the whole family beats it and
    # the test correctly rejects — for a reason that has nothing to do with predictive skill.
    #
    # The permutation null has no such weakness: it re-runs this exact procedure on data whose
    # true answer is known to be "no edge", so the baseline's own luck is resampled along with
    # everything else. It is the multiple-testing gate; SPA and RC are reported as diagnostics.
    gates = {
        "pbo_lt_0.50": bool(pbo is not None and pbo < 0.50),
        "deflated_sharpe_gt_0.95": bool((dsr or {}).get("deflated_sharpe") is not None
                                        and dsr["deflated_sharpe"] > 0.95),
        "positive_in_60pct_of_paths": bool((best["pos"] or 0) >= 0.60),
        "improvement_is_not_just_lower_turnover": bool(decomp["gross_edge_ann"] is not None
                                                       and decomp["gross_edge_ann"] > 0),
        "permutation_pvalue_lt_0.05": bool(perm.get("pvalue") is not None and perm["pvalue"] < 0.05),
        "beats_baseline_on_holdout": bool(hold.get("selected_beats_baseline")),
    }
    rc["calibration_warning"] = (
        "Diagnostic only, NOT a gate. Measured on 20 signal-free panels through this same "
        "pipeline, SPA returns p<0.05 about 35% of the time, because its null compares against a "
        "single realisation of the baseline. Do not read p=0.03 here as '3% chance of luck'. The "
        "permutation null is the gate.")
    adopt = all(gates.values())
    failed = [k for k, v in gates.items() if not v]
    verdict = ("ADOPT the selected config — it cleared every gate."
               if adopt else "KEEP THE DEFAULTS — the search did not clear: " + ", ".join(failed))

    top = sorted([k for k in keys if smooth.get(k) is not None],
                 key=lambda k: smooth[k], reverse=True)[:12]
    ub = rows[unrestricted]["cfg"] if unrestricted else None
    return {
        "n_dates_total": n_all, "n_dates_search": n_search, "n_dates_holdout": n_hold,
        "holdout_window": [hold_dates[0], hold_dates[-1]],
        "n_configs": len(space), "n_interior_configs": len(eligible), "n_paths": len(paths),
        "cost_bps": cost_bps, "annualisation": ann,
        "baseline": {"cfg": BASELINE,
                     "mean_ann": (None if baseline["mean"] is None else baseline["mean"] * ann),
                     "lcb_ann": (None if baseline["lcb"] is None else baseline["lcb"] * ann),
                     "pos": baseline["pos"]},
        "selected": {"cfg": best["cfg"],
                     "mean_ann": (None if best["mean"] is None else best["mean"] * ann),
                     "lcb_ann": (None if best["lcb"] is None else best["lcb"] * ann),
                     "plateau_score_ann": smooth[best_key] * ann, "pos": best["pos"],
                     "n_paths": best["n"]},
        "naive_argmax": {"cfg": rows[argmax_key]["cfg"] if argmax_key else None,
                         "mean_ann": (None if not argmax_key or rows[argmax_key]["mean"] is None
                                      else rows[argmax_key]["mean"] * ann),
                         "note": "what a plain 'pick the highest number' search would have chosen — "
                                 "shown so the cost of robust selection is visible, not hidden."},
        "best_including_boundary": {"cfg": ub, "on_boundary": (boundary_axes(ub, axes) if ub else []),
                                    "note": "if this beats the selected config, the grid is too "
                                            "narrow on the listed axes — widen it and re-run."},
        "leaderboard": [{"cfg": rows[k]["cfg"], "mean_ann": rows[k]["mean"] * ann,
                         "lcb_ann": rows[k]["lcb"] * ann, "plateau_ann": smooth[k] * ann,
                         "pos": rows[k]["pos"], "n": rows[k]["n"],
                         "interior": is_interior(rows[k]["cfg"], axes)} for k in top],
        "edge_decomposition": decomp,
        "reality_check": rc, "pbo": pbo, "deflated_sharpe": dsr, "n_trials_ledger": n_trials,
        "permutation_null": perm, "holdout": hold,
        "gates": gates, "adopt": adopt, "verdict": verdict,
    }


# --------------------------------------------------------------------------------------
# Panel cache — the panel build is the 20-40 minute part; the search itself is minutes
# --------------------------------------------------------------------------------------

#  MA47 — THE KEY USED `len(tickers)` FOR TICKER IDENTITY, WHICH IS THE B12 COLLISION AGAIN.
#
#  The old key was `f"{len(tickers)}_{rebalance_days}_{lookback_years}_{horizon}_{inst_lag_days}"`
#  under a docstring promising it "covers everything that changes the panel, so a stale cache
#  cannot silently be used for different settings". Three classes of difference were not in it:
#
#    * WHICH TICKERS. B12 is precisely this: the 800-name era took `sorted(keys)[:limit]` (an
#      alphabetical A-C slice) where a later reader assumed the 800 largest. Both are 800 names,
#      so both hash to the same `800_...` key and the second silently reads the first's panel.
#      A count is not an identity, and this is the second time that has cost something here.
#    * THE DATA VINTAGE. The Sharadar export is refreshed in place; the same tickers and the
#      same parameters against a newer export are a different panel.
#    * THREE PANEL-SHAPING ENV TOGGLES, each verified live in the tree rather than taken from
#      the audit's list: `EDGE_EV_POINT_IN_TIME` (`config.py:187` — re-prices the EV equity leg,
#      moving every EV-based value ratio a median 5.1%), `EDGE_GRID_OFFSET`
#      (`fundamental_panel.py:1056` — X2's rebalance grid, which moved the long-short t 2.703 to
#      3.517 across seven offsets), and `EDGE_AUDIT_B6_LEGACY_TRUNCATION` (`:1095` — restores the
#      per-ticker tail that made the first third of the panel an inverted universe).
#
#  WHY A SIDECAR AND NOT A LONGER FILENAME. A hash in a filename tells you a cache missed; it
#  cannot tell you WHY, and an opaque 16-hex name is unauditable by the person whose 40-minute
#  build it just invalidated. The provenance is written beside the pickle in full, and the read
#  path COMPARES it rather than trusting the name. That also fixes the failure direction: a
#  legacy cache file has no sidecar, so it is REFUSED and rebuilt rather than silently reused.
#
#  THE DATA VINTAGE IS FINGERPRINTED, NOT ASSUMED, AND ITS LIMIT IS STATED. It is
#  (name, size, mtime) over the provider's export directory — enough to catch a refreshed export,
#  and NOT a content hash, so a byte-identical re-copy with a new mtime reads as a new vintage
#  (a spurious rebuild, the safe direction). If the provider exposes no directory the vintage
#  records `"unavailable"` and the cache still works on the other keys; it does not pretend to
#  cover something it could not measure.
#
#  LATENT TODAY: `cached_panel` has ZERO in-tree callers (measured). It is the designated cache
#  for the honest-search lane, and the docstring was a live false guarantee waiting for its
#  first caller — which is exactly when a silent wrong-panel read would be least visible.

def _data_vintage(provider) -> dict:
    """Fingerprint the export the panel would be built from. See the note above for its limit."""
    d = getattr(provider, "dir", None)
    if not d or not os.path.isdir(d):
        return {"vintage": "unavailable",
                "why": "provider exposes no readable export directory"}
    parts = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if not os.path.isfile(p):
            continue
        st = os.stat(p)
        parts.append(f"{name}:{st.st_size}:{int(st.st_mtime)}")
    if not parts:
        return {"vintage": "unavailable", "why": f"no files in {d}"}
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return {"vintage": h, "n_files": len(parts)}


def _panel_provenance(provider, tickers, rebalance_days, lookback_years, horizon,
                      inst_lag_days) -> dict:
    """Everything that changes the panel, in one comparable object."""
    tick = sorted(str(t).upper() for t in tickers)
    return {
        "schema": 1,
        "n_tickers": len(tick),
        # sorted, so ticker ORDER does not spuriously miss; hashed, so ticker IDENTITY cannot
        # collide the way a bare count does.
        "tickers_sha256": hashlib.sha256("\n".join(tick).encode("utf-8")).hexdigest(),
        "rebalance_days": int(rebalance_days),
        "lookback_years": int(lookback_years),
        "horizon": int(horizon),
        "inst_lag_days": int(inst_lag_days),
        "env": {k: os.environ.get(k, "") for k in
                ("EDGE_EV_POINT_IN_TIME", "EDGE_GRID_OFFSET",
                 "EDGE_AUDIT_B6_LEGACY_TRUNCATION")},
        "data": _data_vintage(provider),
    }


def _provenance_key(prov: dict) -> str:
    blob = json.dumps(prov, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cached_panel(provider, tickers, cache_dir, rebalance_days=63, lookback_years=18, horizon=63,
                 inst_lag_days=45, refresh=False, progress=None):
    """Build the point-in-time panel once and reuse it.

    A cached panel is reused ONLY when a provenance sidecar sits beside it and matches the
    current call exactly — ticker identity, the four parameters, the three panel-shaping env
    toggles and the export's vintage fingerprint. Anything else rebuilds. See the block comment
    above for what each component is and what the vintage fingerprint does not cover.
    """
    log = progress or (lambda *a, **k: None)
    prov = _panel_provenance(provider, tickers, rebalance_days, lookback_years, horizon,
                             inst_lag_days)
    key = _provenance_key(prov)
    path = os.path.join(cache_dir, f"panel_cache_{key}.pkl")
    meta_path = path[:-4] + ".meta.json"

    if os.path.exists(path) and not refresh:
        why = None
        if not os.path.exists(meta_path):
            why = "no provenance sidecar (legacy cache file) — refusing rather than guessing"
        else:
            try:
                with open(meta_path, "r", encoding="utf-8") as fh:
                    banked = json.load(fh)
            except Exception as e:
                banked, why = None, f"sidecar unreadable: {type(e).__name__}"
            if why is None and banked != prov:
                diff = sorted(k for k in set(banked) | set(prov)
                              if banked.get(k) != prov.get(k))
                why = f"provenance differs on {diff}"
        if why is None:
            try:
                p = pd.read_pickle(path)
                log(f"  reusing cached panel: {p['date'].nunique()} dates, {len(p):,} rows "
                    f"({path})")
                return p
            except Exception as e:
                log(f"  cached panel unreadable ({type(e).__name__}); rebuilding")
        else:
            log(f"  NOT reusing {path}: {why}")

    log("  building the point-in-time panel (this is the slow part) ...")
    p = FP.build_fundamental_panel(provider, tickers, rebalance_days=rebalance_days,
                                   lookback_years=lookback_years, horizon=horizon,
                                   inst_lag_days=inst_lag_days)
    if not p.empty:
        os.makedirs(cache_dir, exist_ok=True)
        p.to_pickle(path)
        # The sidecar is written AFTER the pickle, so an interrupted write leaves a pickle with
        # no sidecar — which the read path refuses. The failure direction is "rebuild", never
        # "reuse something we cannot vouch for".
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(prov, fh, sort_keys=True, indent=1)
        log(f"  cached panel -> {path}")
    return p


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

def print_report(r):
    _p = lambda x, f="+.2%": "n/a" if x is None else format(x, f)
    if r.get("status"):
        print(f"Parameter search: {r['status']}")
        return
    print("\n=== HONEST PARAMETER SEARCH ===")
    print(f"  {r['n_dates_search']} rebalances searched · {r['n_dates_holdout']} locked away "
          f"({r['holdout_window'][0]} -> {r['holdout_window'][1]})")
    print(f"  {r['n_configs']} configs ({r['n_interior_configs']} interior/adoptable) x "
          f"{r['n_paths']} CPCV paths")
    print(f"  objective: top-N hold alpha vs the equal-weight universe, net of "
          f"{r['cost_bps']:.0f}bps turnover cost")

    print("\n  Leaderboard — ranked by plateau-smoothed lower confidence bound (annualised):")
    print("    plateau     LCB    mean   pos  int  config")
    for row in r["leaderboard"]:
        c = row["cfg"]
        print(f"    {_p(row['plateau_ann']):>7} {_p(row['lcb_ann']):>7} {_p(row['mean_ann']):>7}  "
              f"{_p(row['pos'], '.0%'):>4}  {'y' if row['interior'] else 'n'}   "
              f"{c['scheme']}, top{c['top_n']}, band{c['exit_band']}x, hold{c['min_hold']}, {c['cap_tier']}")

    b, s, nx = r["baseline"], r["selected"], r["naive_argmax"]
    print(f"\n  baseline  {b['cfg']}")
    print(f"            mean {_p(b['mean_ann'])}/yr · LCB {_p(b['lcb_ann'])}/yr · "
          f"positive in {_p(b['pos'], '.0%')} of paths")
    print(f"  selected  {s['cfg']}")
    print(f"            mean {_p(s['mean_ann'])}/yr · LCB {_p(s['lcb_ann'])}/yr · "
          f"positive in {_p(s['pos'], '.0%')} of paths")
    print(f"  (a naive argmax would have picked {nx['cfg']} at {_p(nx['mean_ann'])}/yr)")
    ed = r.get("edge_decomposition") or {}
    if ed.get("net_edge_ann") is not None:
        print(f"  improvement over baseline: {_p(ed['net_edge_ann'])}/yr total = "
              f"{_p(ed['gross_edge_ann'])}/yr better SELECTION + {_p(ed['cost_saving_ann'])}/yr "
              f"lower turnover cost")
    bb = r.get("best_including_boundary") or {}
    if bb.get("on_boundary"):
        print(f"  note: the unrestricted best sits on the edge of the grid for "
              f"{', '.join(bb['on_boundary'])} — widen those axes and re-run before trusting it")

    rc = r.get("reality_check") or {}
    print("\n  Multiple-testing tests across the WHOLE search (on GROSS alpha, so this measures")
    print("  stock-picking skill only — a cheaper commission bill cannot register as an edge):")
    if rc.get("status"):
        print(f"    {rc['status']}")
    else:
        print(f"    [diagnostic only] White Reality Check p = {_p(rc.get('rc_pvalue'), '.3f')}   "
              f"Hansen SPA p = {_p(rc.get('spa_pvalue'), '.3f')}")
        print("      ^ NOT a gate: measured against signal-free data this test fires ~35% of the")
        print("        time, so a small p here is not evidence. The permutation null is the gate.")
    print(f"    Probability of Backtest Overfitting = {_p(r.get('pbo'), '.0%')}   (want < 50%)")
    d = r.get("deflated_sharpe") or {}
    print(f"    Deflated Sharpe = {_p(d.get('deflated_sharpe'), '.0%')} on "
          f"{r.get('n_trials_ledger')} cumulative trials   (want > 95%)")
    pm = r.get("permutation_null") or {}
    if pm.get("pvalue") is not None:
        print(f"    Permutation null: p = {pm['pvalue']:.3f} over {pm['n_perm']} signal-free re-runs "
              f"(null best beat the baseline by {_p(pm['null_edge_mean'] * r['annualisation'])}/yr "
              f"on average purely by search luck)")
    ho = r.get("holdout") or {}
    if ho.get("selected_alpha_ann") is not None:
        print(f"    Locked hold-out ({ho.get('n_periods')} periods): selected "
              f"{_p(ho['selected_alpha_ann'])}/yr vs baseline {_p(ho['baseline_alpha_ann'])}/yr")

    print("\n  Gates:")
    for k, v in (r.get("gates") or {}).items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\n  -> {r.get('verdict')}")
