#!/usr/bin/env python3
"""o17c4_arms.py — A1 (the strategy) and A2 (the same rule on RANDOM ENTRY).

Split out of `o17c4_own_the_event.py` so the bars pass cannot import it, which is what makes
"the bar was derived before the arm" a structural fact rather than a claim about ordering.

Executes PREREG_o17c4_own_the_event.md sections 2, 4 and 5.
"""
from __future__ import annotations

import datetime as dt
import math
import os
from collections import defaultdict

import numpy as np

HALF_SPLIT = dt.date(2021, 1, 1)


def _d(x):
    if x is None:
        return None
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _pnl(rows):
    v = [float(r["pnl_pct"]) for r in rows
         if r.get("pnl_pct") is not None and math.isfinite(float(r["pnl_pct"]))]
    return np.asarray(v, dtype=float)


def _mean(rows):
    v = _pnl(rows)
    return float(v.mean()) if len(v) else None


def _half(rows, late):
    out = []
    for r in rows:
        d = _d(r.get("alert_ts"))
        if d is None:
            continue
        if (d >= HALF_SPLIT) == late:
            out.append(r)
    return out


def sign_test_by_name_year(a_rows, b_rows):
    """C-SIGN — the paired name-year sign test, which carries the verdict.

    R2 established the paired t is the WRONG statistic on a barbell payoff (never significant
    even pooled, -1.227, p 0.22) while this reaches z -4.9612 on the same data. Cells are
    (ticker, year); a cell counts only when BOTH sides have trades in it.
    """
    def cells(rows):
        g = defaultdict(list)
        for r in rows:
            d = _d(r.get("alert_ts"))
            if d is None or r.get("pnl_pct") is None:
                continue
            g[(r.get("ticker"), d.year)].append(float(r["pnl_pct"]))
        return {k: float(np.mean(v)) for k, v in g.items() if v}

    A, B = cells(a_rows), cells(b_rows)
    shared = sorted(set(A) & set(B))
    if not shared:
        return {"n_cells": 0, "z": None, "p": None}
    wins = sum(1 for k in shared if A[k] > B[k])
    n = len(shared)
    z = (wins - n / 2.0) / math.sqrt(n / 4.0) if n else None
    p = (math.erfc(abs(z) / math.sqrt(2.0)) if z is not None else None)
    return {"n_cells": n, "wins": wins, "win_rate": round(wins / n, 4),
            "z": (round(z, 4) if z is not None else None),
            "p": (round(p, 8) if p is not None else None)}


def dte_quartile_table(spans, nots):
    """C-DTE — O13 measured expectancy climbing monotonically with tenor, and a contract that
    spans the next announcement is MECHANICALLY longer-dated. If the gain vanishes once tenor
    is held fixed, this is a tenor filter wearing an earnings filter's name (U7/S10's mode,
    and MA54-4's explicit warning about O6)."""
    allr = [r for r in (spans + nots) if r.get("dte") is not None]
    if len(allr) < 40:
        return {"status": "too few rows with dte"}
    q = np.percentile([float(r["dte"]) for r in allr], [25, 50, 75])
    out = {"cuts": [float(x) for x in q], "quartiles": []}
    for i in range(4):
        lo = -np.inf if i == 0 else q[i - 1]
        hi = np.inf if i == 3 else q[i]
        s = [r for r in spans if r.get("dte") is not None and lo < float(r["dte"]) <= hi]
        n = [r for r in nots if r.get("dte") is not None and lo < float(r["dte"]) <= hi]
        ms, mn = _mean(s), _mean(n)
        out["quartiles"].append({
            "q": i + 1, "n_spans": len(s), "n_not": len(n),
            "spans_mean": ms, "not_mean": mn,
            "gain": (None if ms is None or mn is None else ms - mn)})
    return out


def _matched_diffs(spans, nots, tol):
    by_name = defaultdict(list)
    for r in nots:
        if r.get("dte") is not None and r.get("pnl_pct") is not None:
            by_name[r.get("ticker")].append(r)
    diffs = []
    for r in spans:
        if r.get("dte") is None or r.get("pnl_pct") is None:
            continue
        cand = [x for x in by_name.get(r.get("ticker"), [])
                if abs(float(x["dte"]) - float(r["dte"])) <= tol]
        if not cand:
            continue
        diffs.append(float(r["pnl_pct"]) - float(np.mean([float(x["pnl_pct"]) for x in cand])))
    return np.asarray(diffs, dtype=float)


def dte_matched_gain(spans, nots, tol=5.0, null_draws=20, seed=99):
    """C-DTE, matched: each spanning trade against non-spanning trades of the SAME name within
    +/- tol days of DTE. Holds tenor fixed by construction rather than by stratum.

    THE MEDIAN OF THESE DIFFERENCES IS AN ARTIFACT AND IS NOT A FINDING — caught by running a
    shuffled-label null rather than by reasoning about it. Comparing ONE draw against the MEAN
    of a right-skewed set is biased low by construction: the mean of a barbell sits far above
    its median, so a typical draw falls below it whether or not any effect exists. Measured on
    the control book the NULL median is about -0.42 while the real is -0.36 — so the real
    median runs SLIGHTLY IN THE ARM'S FAVOUR, and quoting it as "the typical spanning trade
    does worse" would have been exactly backwards.

    So three things are returned and only two of them mean anything:
      * `gain` — the MEAN difference. Unbiased, and scored against the same shuffled null.
      * `median_vs_median` — median(spanning) - median(not), which compares like with like and
        is the honest answer to "what happens to a typical trade".
      * `median` — kept ONLY so the artifact is visible beside its null, never quoted alone.
    """
    a = _matched_diffs(spans, nots, tol)
    if not len(a):
        return {"n_matched": 0, "gain": None}
    sp = [float(r["pnl_pct"]) for r in spans if r.get("pnl_pct") is not None]
    nt = [float(r["pnl_pct"]) for r in nots if r.get("pnl_pct") is not None]

    pool = spans + nots
    k = len(spans)
    rng = np.random.default_rng(seed)
    nm, nmed = [], []
    for _ in range(null_draws):
        idx = rng.permutation(len(pool))
        d = _matched_diffs([pool[j] for j in idx[:k]], [pool[j] for j in idx[k:]], tol)
        if len(d):
            nm.append(float(d.mean()))
            nmed.append(float(np.median(d)))
    return {
        "n_matched": int(len(a)), "tol_days": tol,
        "gain": float(a.mean()),
        "null_mean_p95": (float(np.percentile(nm, 95)) if nm else None),
        "gain_clears_null": (bool(a.mean() > np.percentile(nm, 95)) if nm else None),
        "median_vs_median": (float(np.median(sp) - np.median(nt)) if sp and nt else None),
        "median_spanning": (float(np.median(sp)) if sp else None),
        "median_not": (float(np.median(nt)) if nt else None),
        "median_of_differences_ARTIFACT": float(np.median(a)),
        "median_of_differences_NULL": (float(np.median(nmed)) if nmed else None),
        "artifact_note": "median_of_differences is biased low by comparing one draw to a group "
                         "MEAN on a skewed payoff; its own null sits BELOW it. Never quote it "
                         "alone. Use gain (mean) and median_vs_median.",
    }


def arm(spans, nots, label):
    ms, mn = _mean(spans), _mean(nots)
    node = {"label": label, "n_spans": len(spans), "n_not": len(nots),
            "spans_mean": ms, "not_mean": mn,
            "gain": (None if ms is None or mn is None else ms - mn)}
    for nm, late in (("early", False), ("late", True)):
        s, n = _half(spans, late), _half(nots, late)
        a, b = _mean(s), _mean(n)
        node[nm] = {"n_spans": len(s), "n_not": len(n), "spans_mean": a, "not_mean": b,
                    "gain": (None if a is None or b is None else a - b)}
    node["sign_test_spans_vs_not"] = sign_test_by_name_year(spans, nots)
    return node


def run_arms(bars_artifact):
    from scripts.o17c4_own_the_event import load_books, earnings_map, tag

    alert, ctrl = load_books()
    names = sorted({r.get("ticker") for r in alert} | {r.get("ticker") for r in ctrl})
    earn = earnings_map(names)

    a_span, a_not, a_unk = tag(alert, earn)
    c_span, c_not, c_unk = tag(ctrl, earn)

    A1 = arm(a_span, a_not, "A1_alert_book")
    A2 = arm(c_span, c_not, "A2_random_entry")

    out = {
        "prereg": "PREREG_o17c4_own_the_event.md",
        "bars_artifact_read": True,
        "bars": bars_artifact.get("bars"),
        "all_bars_pass": bars_artifact.get("all_bars_pass"),
        "dropped_unknown": {"alert": len(a_unk), "control": len(c_unk),
                            "nonzero": bool(len(a_unk) > 0 and len(c_unk) > 0)},
        "A1": A1, "A2": A2,
        "A1_vs_A2_spanning": sign_test_by_name_year(a_span, c_span),
        "C_DTE_quartiles_alert": dte_quartile_table(a_span, a_not),
        "C_DTE_quartiles_random": dte_quartile_table(c_span, c_not),
        "C_DTE_matched_alert": dte_matched_gain(a_span, a_not),
        "C_DTE_matched_random": dte_matched_gain(c_span, c_not),
    }

    # prereg 5 — CANDIDATE needs all four. Ambiguous is NULL (RUN_RULES A6).
    def pos_both(a):
        return (a["early"]["gain"] is not None and a["early"]["gain"] > 0
                and a["late"]["gain"] is not None and a["late"]["gain"] > 0)

    c1 = pos_both(A1)
    c2 = pos_both(A2) and (A2["gain"] or 0) > 0
    c3 = bool(bars_artifact.get("all_bars_pass"))
    dm = out["C_DTE_matched_alert"].get("gain")
    c4 = bool(dm is not None and dm > 0)
    state = "CANDIDATE" if (c1 and c2 and c3 and c4) else "REJECTED"
    out["verdict"] = {
        "state": state,
        "c1_A1_positive_both_halves": bool(c1),
        "c2_A2_same_effect_on_random_entry": bool(c2),
        "c3_all_bars_pass": bool(c3),
        "c4_survives_dte_matching": bool(c4),
        "reading": ("the rule is a property of OWNING AN EARNINGS EVENT and is independent of "
                    "the dead alert" if c2 else
                    "the effect does NOT reproduce on random entry, so it is alert-specific "
                    "and dies with the alert"),
        "governing_caveat": "O11 — a positive per-trade expectancy on this corpus has already "
                            "been shown compatible with losing money at realistic size. "
                            "CANDIDATE is not ADOPT and licenses no trading.",
    }
    return out
