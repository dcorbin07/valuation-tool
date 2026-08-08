#!/usr/bin/env python3
"""cross_country.py — the clustering gate for a verdict counted across COUNTRIES.

WHY THIS EXISTS. Session 8 pre-registered the only answerable form of the selection-rule
question: run the selection on `usa`, measure on 16 held-out countries, and let a paired sign
test carry the verdict. A sign test over 16 countries has an exact one-sided alpha of 3.84% at
12/16 -- *if the 16 countries are independent draws*. Developed European equity markets are
emphatically not independent, so that 3.84% is a floor and the true false-positive rate is
higher. Quoting 12/16 without measuring the co-movement would be the same error R3 exists to
fix, one dimension over.

THE ESTIMATOR HAS ITS OWN NOISE AND IS SCORED AGAINST ITS OWN NULL (the X7 method, exactly as
`options_stats.effective_n` does it for calendar months). A raw design effect proves nothing:
`options_stats` found by a failing test that 600 independent draws in 12 blocks come back with
a design effect near 1.8 out of pure sampling error in MSB/MSW. So the observed statistic here
is compared against a shuffled null that preserves every block size exactly and destroys only
the association between month and outcome, and `clustering_measurable` is true only when the
observation exceeds the null's 95th percentile. NEVER QUOTE A DESIGN EFFECT WITHOUT ITS NULL.

THE RE-POINTING, STATED PRECISELY. `options_stats` blocks TRADES within a calendar month. Here
the roles swap: the block is the MONTH and the observations inside it are the COUNTRIES. That
makes the measured intraclass correlation the average pairwise co-movement of the countries,
which is the quantity that erodes a cross-country sign test. `_icc_deff` is reused unchanged --
it is a one-way random-effects ANOVA and does not care what the blocks mean -- so the two gates
cannot drift apart.

WHAT THE GATE IS FOR. The design effect is not applied as a haircut. It feeds
`sign_test_critical`, which re-derives the critical count by simulating the sign test's own null
with the measured correlation in it. That is a calibrated bar in the X7 sense rather than an
adjustment to a statistic, and it must be computed BEFORE the measure set's signs are inspected.

BLINDNESS. Every function here is a property of the co-movement structure and is invariant to
which arm any selection rule picks: `rho` is symmetric in the countries and unchanged by
flipping the sign of any country's series. Calibrating on the measure set therefore does not
unblind the verdict -- but the ORDER still matters and the caller must enforce it, because a
threshold chosen after seeing the count is not a threshold.
"""
from __future__ import annotations

import random
from typing import Dict, Optional, Sequence

from valuation.edge.options_stats import _icc_deff

DEFAULT_NULL_DRAWS = 400
DEFAULT_SIM_DRAWS = 40000


# ------------------------------------------------------------------ helpers
def _standardize(vals: Sequence[float]) -> Optional[list]:
    """Zero mean, unit sd. Without this the ANOVA reads a loud country as a common factor."""
    v = [float(x) for x in vals if x is not None and x == x]
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    var = sum((x - m) ** 2 for x in v) / (len(v) - 1)
    if var <= 0:
        return None
    sd = var ** 0.5
    return [(x - m) / sd for x in v]


def align_by_date(series_by_key: Dict[str, Dict]) -> tuple:
    """-> (dates, {key: [value per date]}) over the dates present in EVERY key.

    Inner-joining is deliberate: a month one country is missing is not a month in which that
    country failed to co-move, and padding it would put a constant into the ANOVA.
    """
    keys = sorted(series_by_key)
    if not keys:
        return [], {}
    common = None
    for k in keys:
        d = set(series_by_key[k].keys())
        common = d if common is None else (common & d)
    dates = sorted(common or [])
    return dates, {k: [series_by_key[k][d] for d in dates] for k in keys}


# ------------------------------------------------- the design effect and its null
def country_design_effect(series_by_key: Dict[str, Dict], null_draws: int = DEFAULT_NULL_DRAWS,
                          seed: int = 0, standardize: bool = True) -> dict:
    """Co-movement of a per-country monthly series, scored against its own shuffled null.

    `series_by_key` maps country -> {date: value}. Blocks are months, observations are the
    countries within a month -- the transpose of the options book's blocking.

    `rho` is clamped at 0 from below. A negative ICC is a small-sample artefact, and letting it
    LOWER the sign test's critical count would turn a correction into a licence -- the same
    reasoning that clamps the ICC in `options_stats.effective_n`.
    """
    dates, cols = align_by_date(series_by_key)
    keys = sorted(cols)
    if len(keys) < 2 or len(dates) < 2:
        return {"ok": False, "n_countries": len(keys), "n_dates": len(dates)}

    series = {}
    for k in keys:
        v = _standardize(cols[k]) if standardize else [float(x) for x in cols[k]]
        if v is None:
            return {"ok": False, "reason": f"degenerate series for {k}",
                    "n_countries": len(keys), "n_dates": len(dates)}
        series[k] = v

    # blocks = months, observations = countries
    vals_by_block = [[series[k][i] for k in keys] for i in range(len(dates))]
    icc_raw, deff, n, k_blocks = _icc_deff(vals_by_block)
    if icc_raw is None:
        return {"ok": False, "n_countries": len(keys), "n_dates": len(dates)}
    rho = max(0.0, icc_raw)

    # A direct cross-check that does not go through the ANOVA at all: the mean off-diagonal
    # correlation. Two estimators of one quantity; if they disagree, do not quote either.
    m = len(dates)
    pair_sum, pair_n = 0.0, 0
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            xa, xb = series[keys[a]], series[keys[b]]
            if standardize:
                r = sum(xa[i] * xb[i] for i in range(m)) / (m - 1)
            else:
                ma, mb = sum(xa) / m, sum(xb) / m
                cov = sum((xa[i] - ma) * (xb[i] - mb) for i in range(m)) / (m - 1)
                va = sum((x - ma) ** 2 for x in xa) / (m - 1)
                vb = sum((x - mb) ** 2 for x in xb) / (m - 1)
                r = cov / ((va * vb) ** 0.5) if va > 0 and vb > 0 else 0.0
            pair_sum += r
            pair_n += 1
    mean_pair_corr = pair_sum / pair_n if pair_n else None

    # THE NULL. Shuffle values across months, preserving every block size exactly. This destroys
    # the common-month factor -- which IS the clustering -- and nothing else.
    rnd = random.Random(seed)
    flat = [x for blk in vals_by_block for x in blk]
    sizes = [len(b) for b in vals_by_block]
    null_deff = []
    for _ in range(max(0, int(null_draws))):
        rnd.shuffle(flat)
        i, parts = 0, []
        for s in sizes:
            parts.append(flat[i:i + s])
            i += s
        _, d0, _, _ = _icc_deff(parts)
        if d0 is not None:
            null_deff.append(d0)
    null_deff.sort()
    p95 = null_deff[int(0.95 * len(null_deff))] if len(null_deff) >= 20 else None
    p50 = null_deff[len(null_deff) // 2] if len(null_deff) >= 20 else None
    measurable = bool(deff > p95) if p95 is not None else None

    return {
        "ok": True, "countries": keys, "n_countries": len(keys), "n_dates": len(dates),
        "block": "month", "observations_per_block": len(keys),
        "icc_raw": float(icc_raw), "rho": float(rho),
        "mean_pairwise_corr": (float(mean_pair_corr) if mean_pair_corr is not None else None),
        "design_effect": float(deff),
        "design_effect_null_p50": p50, "design_effect_null_p95": p95,
        "clustering_measurable": measurable, "null_draws": len(null_deff),
        "n_eff_countries": float(len(keys) / deff) if deff and deff > 0 else float(len(keys)),
        "standardized": bool(standardize),
        "note": "Blocks are MONTHS and observations are COUNTRIES -- the transpose of the "
                "options book's blocking, so `rho` is the average pairwise co-movement. Read "
                "`clustering_measurable` FIRST: when it is False the design effect sits inside "
                "its own shuffled null and n_eff_countries is a bound, not a measurement. The "
                "design effect is NOT applied as a haircut here; it calibrates the sign test's "
                "critical count via `sign_test_critical`.",
    }


# ------------------------------------------------------ the calibrated sign test
def _equicorrelated_positive_counts(n: int, rho: float, draws: int, seed: int) -> list:
    """Counts of positive signs under an equicorrelated Gaussian null with zero true effect.

    z_c = sqrt(rho)*F + sqrt(1-rho)*e_c. One common factor F is exactly the structure the ANOVA
    measures, so the simulated null carries the SAME rho the gate reported -- the two halves of
    this module agree by construction rather than by assumption.
    """
    rho = min(max(float(rho), 0.0), 0.999)
    a, b = rho ** 0.5, (1.0 - rho) ** 0.5
    rnd = random.Random(seed)
    out = []
    for _ in range(int(draws)):
        f = rnd.gauss(0.0, 1.0)
        out.append(sum(1 for _ in range(n) if a * f + b * rnd.gauss(0.0, 1.0) > 0.0))
    return out


def sign_test_critical(n: int, rho: float, alpha: float = 0.05,
                       draws: int = DEFAULT_SIM_DRAWS, seed: int = 0) -> dict:
    """Smallest k with simulated P(count >= k) <= alpha, under the measured correlation.

    At rho = 0 this reproduces the exact binomial critical value; the test suite pins that, so
    the simulation cannot silently drift away from the arithmetic it generalises.
    """
    counts = _equicorrelated_positive_counts(n, rho, draws, seed)
    d = len(counts)
    tail = {k: sum(1 for c in counts if c >= k) / d for k in range(n + 1)}
    crit = next((k for k in range(n + 1) if tail[k] <= alpha), n + 1)
    return {"n": n, "rho": float(min(max(rho, 0.0), 0.999)), "alpha": alpha, "draws": d,
            "critical_k": crit,
            "achieved_alpha": (tail.get(crit) if crit <= n else 0.0),
            "alpha_at_naive_binomial_k": None, "tail": tail}


def sign_test_p(k: int, n: int, rho: float, draws: int = DEFAULT_SIM_DRAWS,
                seed: int = 0) -> float:
    """One-sided P(count >= k) under the equicorrelated null."""
    counts = _equicorrelated_positive_counts(n, rho, draws, seed)
    return sum(1 for c in counts if c >= k) / len(counts)


def exact_binomial_tail(k: int, n: int) -> float:
    """P(X >= k) for X ~ Bin(n, 0.5). The independent-countries reference point."""
    from math import comb
    return sum(comb(n, i) for i in range(k, n + 1)) / (2 ** n)
