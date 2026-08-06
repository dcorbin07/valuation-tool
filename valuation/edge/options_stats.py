"""options_stats.py — clustered inference for the options book.  [AUDIT R3]

Every options statistic this project has published treats trades as independent. They are not,
and the dependence is not subtle: the alert fires on a technical run-up, run-ups cluster in time,
and the universe is 187 highly-correlated US equities. A volatility event in March 2020 puts
dozens of trades on the book inside a fortnight, all long calls, all on names that move together.
Resampling those trades individually — which is what `options_universe.bootstrap_diff` does —
treats each as a fresh draw from the population and produces a confidence interval that is
optimistically narrow by roughly the square root of the clustering factor.

WHAT THIS MODULE ADDS, and none of it existed before:

  1. `date_block_bootstrap` — resample CALENDAR MONTHS with replacement, keeping every trade
     inside a sampled month together. The block is the unit of independence; the trade is not.
  2. `effective_n` — two estimates, reported side by side rather than one presented as fact:
     the number of distinct entry months (the conservative, assumption-free count) and the
     design-effect estimate `n / (1 + (m̄ − 1)·ρ̄)` from the measured within-block correlation.
  3. `paired_name_year` — the paired name-year sign test and paired *t* that the whole options
     conclusion rests on, IN THE REPOSITORY for the first time. `HANDOFF_universe_backtest.md`
     quotes "441 of 1,052 cells, z = −5.24, paired t = −2.18" and no shipped code computes any
     of it; the numbers exist only in a session's scratch. That is not reproducible, and R3.3
     exists to fix it.
  4. `purged_blocks` — purge and embargo for the CSCV splits. A trade entered in an in-sample
     block is open for up to 75 days into the adjacent out-of-sample block, and performance is
     attributed by ENTRY date, so the two sides of every split share the market days that
     resolve the boundary trades.

WHY THE PAIRED TEST IS THE ONE TO LEAN ON. The pooled gap between the real book and the
random-entry control mixes two things: whether the signal picks better days, and which names and
years each book happens to weight. Pairing by (name, year) cell holds both fixed, so the only
surviving difference is day selection — which is the question. The sign test is then preferred
over the paired *t* because the per-trade payoff is a barbell with a fat right tail: a single
+600% trade moves a mean and moves no median. The handoff already found the *t* unstable across
seeds (−2.67, −1.56, −2.18) while the sign test held (45.7%, 44.2%, 41.9%). Both ship here; the
sign test is the one the verdict reads.

WHAT THIS MODULE DELIBERATELY DOES NOT DO. It does not re-weight, winsorise or trim anything.
Every function here changes the INFERENCE about a book, never the book. A statistic that only
survives its own confidence interval after the tail is clipped is not a finding.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

# The maximum a single trade can stay open: DTE_RANGE tops out at 75 days and the time stop
# fires at half of it, so 75 calendar days bounds the label window. Used as the embargo.
MAX_HOLD_DAYS = 75

# Blocks are calendar months by default. A month is long enough to contain a full volatility
# episode (the thing that clusters entries) and short enough to leave ~120 blocks over a decade,
# which is enough for a percentile bootstrap to mean something.
DEFAULT_BLOCK = "month"

BOOTSTRAP_DRAWS = 4000


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def block_of(row, block: str = DEFAULT_BLOCK) -> Optional[str]:
    """The clustering key for one trade. Entry date, because that is how performance is
    attributed everywhere else in this codebase — changing the attribution here would make the
    inference describe a different book from the one being reported."""
    d = str(row.get("alert_ts") or "")[:10]
    if len(d) < 7:
        return None
    if block == "month":
        return d[:7]
    if block == "week":
        try:
            import datetime as dt
            y, w, _ = dt.date.fromisoformat(d).isocalendar()
            return f"{y}-W{w:02d}"
        except ValueError:
            return None
    if block == "year":
        return d[:4]
    return d


def group_by_block(rows, block: str = DEFAULT_BLOCK) -> dict:
    out = {}
    for r in rows:
        b = block_of(r, block)
        if b is not None and _f(r.get("pnl_pct")) is not None:
            out.setdefault(b, []).append(r)
    return out


def mean_pnl(rows) -> Optional[float]:
    """Expectancy per trade, identical to `options_tracker._stats['expectancy_pct']` but without
    the surrounding dict — this is called several thousand times per bootstrap."""
    v = [_f(r.get("pnl_pct")) for r in rows]
    v = [x for x in v if x is not None]
    return (sum(v) / len(v)) if v else None


# ================================ effective sample size =====================================
def _icc_deff(vals_by_block) -> tuple:
    """One-way random-effects ANOVA intraclass correlation and the design effect it implies.

    Returns (icc_raw, design_effect, n, k). Split out from `effective_n` so the null band can
    call it several hundred times without re-deriving anything.
    """
    n = sum(len(v) for v in vals_by_block)
    k = len(vals_by_block)
    if n < 2 or k < 2 or n == k:
        return None, None, n, k
    grand = sum(sum(v) for v in vals_by_block) / n
    sizes = [len(v) for v in vals_by_block]
    m_bar = n / k
    ss_b = sum(len(v) * (sum(v) / len(v) - grand) ** 2 for v in vals_by_block)
    ss_w = sum((x - sum(v) / len(v)) ** 2 for v in vals_by_block for x in v)
    df_b, df_w = k - 1, n - k
    if df_b <= 0 or df_w <= 0:
        return None, None, n, k
    ms_b, ms_w = ss_b / df_b, ss_w / df_w
    # The unbalanced-design correction: m0, not m_bar, is the right divisor when sizes vary.
    m0 = (n - sum(s * s for s in sizes) / n) / df_b
    den = ms_b + (m0 - 1) * ms_w
    icc_raw = ((ms_b - ms_w) / den) if den > 0 else 0.0
    deff = 1.0 + (m_bar - 1.0) * max(0.0, icc_raw)
    return float(icc_raw), float(deff), n, k


def effective_n(rows, block: str = DEFAULT_BLOCK, null_draws: int = 200,
                seed: int = 0) -> dict:
    """How many independent observations this book really contains.

    THE ICC ESTIMATOR HAS ITS OWN NOISE, AND AT THIS BLOCK SIZE THE NOISE IS LARGER THAN THE
    EFFECT IT IS MEASURING. Found by a failing test, not by reasoning: a book of 600 draws from
    a single distribution, assigned to 12 blocks of 50 with NO block structure whatsoever, comes
    back with a design effect near 1.8 — i.e. an apparent 45% loss of sample size that is purely
    sampling error in the ratio MSB/MSW. With `k` blocks the ratio is F(k−1, n−k), whose spread
    is roughly sqrt(2/(k−1)); multiplied by a mean block size of 25-50, a 2% wobble in the ICC
    becomes a 2x design effect.

    So a raw design effect is not evidence of clustering, and applying it as a haircut would
    manufacture a correction out of noise — the mirror image of the error R3 exists to fix, and
    just as dishonest. The book is therefore measured against ITS OWN NULL, using the project's
    established method (X7): the returns are shuffled across blocks, preserving every block size
    exactly and destroying only the association between block and outcome, and the design effect
    is recomputed. `clustering_measurable` is true only when the observed design effect exceeds
    the 95th percentile of that null.

    TWO ESTIMATES OF n_eff ARE REPORTED AND NEITHER IS PRESENTED ALONE:
      * `n_blocks` — the count of distinct entry months. Assumption-free and conservative.
      * `n_eff_icc` — the design-effect estimate `n / (1 + (m̄ − 1)·ρ̄)`. Uses the data, and
        must be read together with `clustering_measurable`.

    `ρ̄` is clamped at 0 from below: a negative ICC is a small-sample artefact, not evidence that
    clustering IMPROVES precision, and letting it inflate `n_eff` above `n` would turn a
    correction into a licence.
    """
    import random

    g = group_by_block(rows, block)
    vals_by_block = [[_f(r.get("pnl_pct")) for r in v
                      if _f(r.get("pnl_pct")) is not None] for v in g.values()]
    vals_by_block = [v for v in vals_by_block if v]
    icc_raw, deff, n, k = _icc_deff(vals_by_block)
    if icc_raw is None:
        return {"ok": False, "n": n, "n_blocks": k}
    icc = max(0.0, icc_raw)
    n_eff = n / deff if deff > 0 else float(n)

    # The null band. Shuffle outcomes across blocks; sizes are preserved exactly.
    rnd = random.Random(seed)
    flat = [x for v in vals_by_block for x in v]
    sizes = [len(v) for v in vals_by_block]
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
    p95 = (null_deff[int(0.95 * len(null_deff))] if len(null_deff) >= 20 else None)
    p50 = (null_deff[len(null_deff) // 2] if len(null_deff) >= 20 else None)
    measurable = (bool(deff > p95) if p95 is not None else None)

    return {"ok": True, "n": n, "n_blocks": k, "block": block,
            "mean_trades_per_block": n / k,
            "icc": icc, "icc_raw": icc_raw,
            "design_effect": deff,
            "design_effect_null_p50": p50, "design_effect_null_p95": p95,
            "clustering_measurable": measurable, "null_draws": len(null_deff),
            "n_eff_icc": float(n_eff),
            "n_eff_conservative": float(k),
            "clustering_factor": (n / n_eff) if n_eff > 0 else None,
            "note": "n_blocks is the assumption-free floor; n_eff_icc uses the measured "
                    "within-block correlation and must be read with `clustering_measurable`, "
                    "which compares the design effect against a shuffled null. At these block "
                    "sizes the ICC estimator's own noise produces a design effect near 1.8 on a "
                    "book with no clustering at all, so a raw figure proves nothing."}



# ================================ the date-block bootstrap ==================================
def date_block_bootstrap(rows, stat: Callable = mean_pnl, block: str = DEFAULT_BLOCK,
                         draws: int = BOOTSTRAP_DRAWS, seed: int = 0) -> dict:
    """Percentile CI on `stat(rows)` by resampling BLOCKS with replacement.

    Every trade inside a drawn block travels with it, so the resample preserves whatever
    within-month dependence exists instead of averaging it away. The resampled book has a
    varying trade count by construction — that variation is real and is part of what the
    interval is measuring.
    """
    import random

    g = group_by_block(rows, block)
    keys = sorted(g)
    point = stat(rows)
    if point is None or len(keys) < 2:
        return {"ok": False, "reason": f"{len(keys)} blocks"}
    rnd = random.Random(seed)
    vals = []
    for _ in range(draws):
        samp = []
        for _ in range(len(keys)):
            samp.extend(g[keys[rnd.randrange(len(keys))]])
        v = stat(samp)
        if v is not None:
            vals.append(v)
    if len(vals) < 100:
        return {"ok": False, "reason": "too few usable draws"}
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[min(len(vals) - 1, int(0.975 * len(vals)))]
    return {"ok": True, "point": point, "ci95": [lo, hi], "draws": len(vals),
            "n_blocks": len(keys), "block": block,
            "excludes_zero": bool(lo > 0 or hi < 0),
            "se": _sd(vals),
            "note": "blocks resampled with replacement; trades within a block stay together."}


def date_block_diff(a_rows, b_rows, stat: Callable = mean_pnl, block: str = DEFAULT_BLOCK,
                    draws: int = BOOTSTRAP_DRAWS, seed: int = 0) -> dict:
    """CI on stat(a) − stat(b), resampling the SAME blocks on both sides.

    Drawing a month pulls that month's trades out of BOTH books at once. This is the correct
    construction for a real-versus-control comparison whose two arms are generated over the same
    calendar: it removes the common calendar variance from the difference, exactly as pairing
    does, instead of treating March 2020's contribution to each arm as two independent draws.
    """
    import random

    ga, gb = group_by_block(a_rows, block), group_by_block(b_rows, block)
    keys = sorted(set(ga) & set(gb))
    pa, pb = stat(a_rows), stat(b_rows)
    if pa is None or pb is None or len(keys) < 2:
        return {"ok": False, "reason": f"{len(keys)} shared blocks"}
    rnd = random.Random(seed)
    diffs = []
    for _ in range(draws):
        sa, sb = [], []
        for _ in range(len(keys)):
            k = keys[rnd.randrange(len(keys))]
            sa.extend(ga[k])
            sb.extend(gb[k])
        va, vb = stat(sa), stat(sb)
        if va is not None and vb is not None:
            diffs.append(va - vb)
    if len(diffs) < 100:
        return {"ok": False, "reason": "too few usable draws"}
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
    return {"ok": True, "a": pa, "b": pb, "diff": pa - pb, "ci95": [lo, hi],
            "draws": len(diffs), "n_blocks": len(keys), "block": block,
            "excludes_zero": bool(lo > 0 or hi < 0),
            "negative_at_significance": bool(hi < 0),
            "positive_at_significance": bool(lo > 0),
            "se": _sd(diffs),
            "note": "paired block bootstrap: a drawn month contributes to BOTH arms."}


def _sd(v):
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


# ================================ the paired name-year test =================================
def paired_name_year(real_rows, ctrl_rows, min_per_cell: int = 1) -> dict:
    """The paired (ticker, year) sign test and paired *t*.  [AUDIT R3.3]

    THIS IS THE NUMBER THE WHOLE OPTIONS CONCLUSION RESTS ON, and until now it lived in a
    session's scratch rather than in the repository. `HANDOFF_universe_backtest.md` §4 reports
    "the alert book wins in 441 of 1,052 cells = 41.9%, sign-test z = −5.24" with no shipped
    code that computes it. Anything a verdict rests on has to be re-derivable.

    Construction: for each (ticker, calendar-year) cell present in BOTH books, take the mean
    per-trade return of the real book's trades and of the control's, and difference them. Name
    and year are held fixed, so "this name compounded over the decade" and "2020 was a good
    year" cannot contribute — the only surviving difference is which days were chosen.

    Reported together and never separately:
      * the SIGN TEST on the share of cells the real book wins, with the exact-null normal
        approximation z. Distribution-free, and the right test for a barbell payoff.
      * the PAIRED t on the cell differences, which is more powerful when the differences are
        near-normal and much less trustworthy when they are not. The handoff already measured it
        swinging −2.67 / −1.56 / −2.18 across seeds while the sign test barely moved.
    """
    def cells(rows):
        out = {}
        for r in rows:
            t = str(r.get("ticker") or "").upper()
            y = str(r.get("alert_ts") or "")[:4]
            v = _f(r.get("pnl_pct"))
            if t and len(y) == 4 and v is not None:
                out.setdefault((t, y), []).append(v)
        return out

    ca, cb = cells(real_rows), cells(ctrl_rows)
    keys = sorted(k for k in (set(ca) & set(cb))
                  if len(ca[k]) >= min_per_cell and len(cb[k]) >= min_per_cell)
    if len(keys) < 10:
        return {"ok": False, "reason": f"{len(keys)} paired cells"}

    diffs = [sum(ca[k]) / len(ca[k]) - sum(cb[k]) / len(cb[k]) for k in keys]
    n = len(diffs)
    wins = sum(1 for d in diffs if d > 0)
    ties = sum(1 for d in diffs if d == 0)
    # Ties are excluded from the sign test's denominator, the standard treatment: a cell where
    # the two books earned exactly the same is evidence for neither side.
    n_signed = n - ties
    z = ((wins - n_signed / 2.0) / math.sqrt(n_signed / 4.0)) if n_signed > 0 else None

    m = sum(diffs) / n
    sd = _sd(diffs)
    t = (m / (sd / math.sqrt(n))) if sd and sd > 0 else None
    srt = sorted(diffs)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0

    return {"ok": True, "n_cells": n, "n_wins": wins, "n_ties": ties,
            "win_rate": wins / n_signed if n_signed else None,
            "sign_test_z": z, "sign_test_p": (_two_sided_p(z) if z is not None else None),
            "mean_diff": m, "median_diff": med, "paired_t": t,
            "paired_p": (_two_sided_p(t) if t is not None else None),
            "note": "cells are (ticker, calendar year) present in BOTH books. The sign test is "
                    "the statistic to lean on; the paired t is unstable under a fat right tail."}


def _two_sided_p(z) -> float:
    """Two-sided normal tail. The paired `t` is read against the normal because these cell
    counts are in the hundreds, where the difference from a t-distribution is immaterial."""
    return math.erfc(abs(float(z)) / math.sqrt(2.0))


# ================================ purge and embargo =========================================
def purged_split(dates, is_idx, os_idx, blocks, embargo_days: int = MAX_HOLD_DAYS) -> tuple:
    """Drop the dates on either side of an IS/OS boundary whose label windows overlap.

    A trade is stamped with its ENTRY date and resolves up to `embargo_days` later. So a trade
    entered on the last day of an in-sample block is still open — and being resolved by the same
    market — well inside the following out-of-sample block. CSCV assumes the two halves are
    independent samples; without purging they share their boundary weeks.

    Symmetric by construction: a date is dropped from whichever side it is on if any date on the
    OTHER side falls within its forward label window. That handles the combinatorial splits,
    where the two sides interleave and "which one comes first" has no answer.
    """
    import datetime as dt

    is_dates = set().union(*[blocks[i] for i in is_idx]) if is_idx else set()
    os_dates = set().union(*[blocks[i] for i in os_idx]) if os_idx else set()

    def _d(s):
        return dt.date.fromisoformat(str(s)[:10])

    import bisect

    def purge(keep, other):
        # Bisect, not a linear scan: CSCV runs C(8,4) = 70 splits over ~2,500 dates, and the
        # naive membership test is O(n^2) per split — minutes of pure overhead on a function
        # that is supposed to be a cheap correction.
        oth = sorted(_d(x) for x in other)
        out = set()
        for s in keep:
            d0 = _d(s)
            # Any other-side date strictly after d0 and within the label window contaminates it.
            i = bisect.bisect_right(oth, d0)
            if i >= len(oth) or oth[i] > d0 + dt.timedelta(days=embargo_days):
                out.add(s)
        return out

    return purge(is_dates, os_dates), purge(os_dates, is_dates)


def deflated_sharpe_clustered(returns, n_trials: int, rows=None,
                              block: str = DEFAULT_BLOCK, trial_sharpes=None) -> dict:
    """Deflated Sharpe recomputed at the EFFECTIVE sample size.  [AUDIT R3.5]

    `options_autopsy.deflated_sharpe` divides by `n − 1`, the raw trade count, which assumes
    every trade is an independent draw. The test statistic scales with `sqrt(n − 1)`, so an
    inflated `n` inflates the statistic by exactly the square root of the clustering factor.
    Substituting `n_eff` is the whole correction and it is a shrinkage, never an improvement.

    Both figures ship. The raw one is what every historical options number was computed at, and
    dropping it would break comparability with the record.
    """
    from .options_autopsy import deflated_sharpe

    raw = deflated_sharpe(returns, n_trials, trial_sharpes=trial_sharpes)
    if not raw.get("ok"):
        return {"ok": False, "raw": raw}
    eff = effective_n(rows if rows is not None else [], block)
    if not eff.get("ok"):
        return {"ok": True, "raw": raw, "clustered": None,
                "reason": "no rows supplied for the clustering estimate"}
    n, n_eff = raw["n"], eff["n_eff_icc"]
    if n_eff >= n or n_eff < 2:
        return {"ok": True, "raw": raw, "effective_n": eff, "clustered": raw,
                "note": "measured clustering was nil; the raw statistic already applies."}
    # The statistic is (sr − sr0) / sqrt(var_sr) with var_sr ∝ 1/(n − 1). Rescaling to n_eff is
    # therefore an exact multiplication by sqrt((n_eff − 1)/(n − 1)) — no re-derivation needed.
    scale = math.sqrt((n_eff - 1.0) / (n - 1.0))
    stat_raw = _inv_phi(raw["deflated_sharpe"])
    stat_eff = stat_raw * scale
    return {"ok": True, "raw": raw, "effective_n": eff,
            "deflated_sharpe_raw": raw["deflated_sharpe"],
            "deflated_sharpe_clustered": _phi(stat_eff),
            "shrink_factor": scale,
            "n_used": n_eff, "n_raw": n,
            # Carried up so nobody quotes a haircut that is estimator noise. When this is False
            # the clustered figure is a CONSERVATIVE BOUND, not a measurement.
            "clustering_measurable": eff.get("clustering_measurable"),
            "note": "the DSR statistic scales with sqrt(n − 1); substituting n_eff is exact. "
                    "Read `clustering_measurable` first: when it is False the design effect is "
                    "inside its own shuffled null and the clustered figure is a bound only."}


def _phi(z) -> float:
    return 0.5 * (1.0 + math.erf(float(z) / math.sqrt(2.0)))


def _inv_phi(p) -> float:
    """Acklam's inverse normal CDF, matching `options_autopsy.deflated_sharpe`'s own `ppf` so the
    round trip through Φ and Φ⁻¹ is exact to the precision that function already carries."""
    p = min(max(float(p), 1e-12), 1 - 1e-12)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - pl:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
