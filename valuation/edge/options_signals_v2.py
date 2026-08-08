"""
§2 — new ThetaData-derived option signals, judged ON THE FADE. PRE-SPECIFIED GATE, committed
results-free before any of them were computed.

--------------------------------------------------------------------------------------------
WHAT THIS IS ACTUALLY TESTING, AND WHY THE USUAL TEST WOULD BE THE WRONG ONE.

The scream-buy edge is not weak on average - it is DECAYING: +16.4%/trade over 2016-2020 and
+4.4% over 2021-2025, with 2022, 2023 and 2025 negative. A signal that lifts full-sample
expectancy is therefore close to worthless here: the full sample is dominated by the early
period that already works. Phase 3 made that concrete twice - the 65-75 DTE band gained +11.55pp
on the early half and +1.19pp on the late one, and was rejected.

So every signal below is judged on ONE question: **does it improve the 2021-2025 half?**

--------------------------------------------------------------------------------------------
HOW LOOK-AHEAD IS AVOIDED IN A TEST THAT TARGETS THE LATE PERIOD.

Aiming at the late half creates an obvious trap: tune a threshold until the late half looks
good, and the result is guaranteed and meaningless. So the split is strict and one-directional:

    THRESHOLD IS FITTED ON 2016-2020 ONLY.  It is the median of the signal among PROFITABLE
    early-half trades - a fixed, untuned recipe ("look like the early winners looked"), not a
    search over cutoffs.

    IT IS THEN APPLIED UNCHANGED TO 2021-2025, which never informed it.

No threshold is ever selected by looking at late-half outcomes. A signal that needed such tuning
is exactly what this design refuses to let through.

--------------------------------------------------------------------------------------------
THE SIGNALS - all computed from the CACHED chain, no new data pull.

  iv_rank        ATM IV percentile against that name's own trailing year. "Is vol rich or cheap
                 FOR THIS STOCK", which raw IV cannot say (a 40% IV is cheap for TSLA, rich for KO).
  vrp            ATM IV minus trailing 30-day realised vol. Positive = options priced above
                 what the stock has actually been doing, i.e. you are overpaying for the move.
                 For a LONG option buyer a NEGATIVE VRP should be the friendly state, so the
                 signal is negated to keep the "higher is better" convention.
  term_slope     ~60-DTE ATM IV minus front-expiry ATM IV. Backwardation (negative) marks stress
                 or a pending event; contango is the calm default.
  skew_25d       25-delta put IV minus 25-delta call IV. Rising put skew is the market paying up
                 for downside protection.
  gex_proxy      sum over strikes of open_interest * gamma, calls minus puts, scaled by spot.
                 A dealer-positioning proxy: large positive = pinning/mean-reverting, large
                 negative = moves get amplified. Gamma is computed from IV by Black-Scholes, as
                 the mandate specifies, because the vendor does not serve it cheaply.

NOT INCLUDED: tick-level flow (sweeps, blocks, aggressor side). It needs the tick trade feed,
which is not in the cached EOD history and would be a fresh multi-hour pull. Its absence is
recorded rather than quietly skipped, because "we tested the flow signals" would be false.

--------------------------------------------------------------------------------------------
PRE-COMMITTED GATE - a signal is adopted as a live filter only if ALL hold:

  1. LATE-HALF LIFT: filtered expectancy over 2021-2025 beats unfiltered by >= MIN_LATE_GAIN.
  2. IT KEEPS A BOOK: it retains at least MIN_RETAINED of late-half trades. A filter that keeps
     8% of signals has not fixed the strategy, it has replaced it with a much smaller one, and
     its apparent edge is a small-sample artefact.
  3. SAMPLE: at least MIN_TRADES filtered trades in the late half.
  4. NOT MERELY SELECTIVE: it must beat a random filter that keeps the SAME NUMBER of late-half
     trades. Reported alongside every result, because dropping trades at random from a
     heavy-tailed distribution moves expectancy on its own.
  5. NO CHERRY-PICKING ACROSS SIGNALS: with several signals tested at once, the best of them
     will look good by chance. Any winner must ALSO be positive in the early half - not because
     the early half matters for adoption, but because a signal that only ever helps the period
     it was aimed at is indistinguishable from noise that happened to land there.

Expect rejections. These are the most-watched derived quantities in options, and the fade may
simply be the strategy decaying rather than something a filter can rescue.

================================ RESULT (run after the above was committed) =================

ONE OF FIVE ADOPTED. One was not testable and is reported as such, not as a rejection.

    signal       thr      kept (late)     late exp -> filtered    gain     early    verdict
    term_slope  +0.011   307/756 (40.6%)   +4.76% -> +12.88%    +8.12pp   +5.80pp   ADOPT
    skew_25d    +0.036   266/605 (44.0%)   +5.33% ->  +6.43%    +1.10pp   +1.36pp   reject
    vrp         -0.027   424/756 (56.1%)   +4.76% ->  +5.30%    +0.54pp   -3.11pp   reject
    gex_proxy   +0.048   366/729 (50.2%)   +4.65% ->  +4.00%    -0.65pp   +1.17pp   reject
    iv_rank        -           -                 -                  -         -     NOT TESTABLE

TERM STRUCTURE IS THE ONE THING THAT ARRESTS THE FADE. Requiring contango - ~60-DTE IV above
front-expiry IV - nearly triples late-half expectancy, clears every arm of the gate, and is
economically coherent: backwardation means the market is pricing near-term stress or a pending
event, which is a bad moment to pay up for a 45-75 day call.

Its effect on the years that were LOSING, which is what it was aimed at:

    2022   -11.41% -> +19.78%   (+31.19pp)   fixed
    2023    -4.61% ->  +7.30%   (+11.91pp)   fixed
    2025    -0.05% ->  -5.90%   ( -5.84pp)   MADE WORSE

Two of three losing years repaired, the third not. Across all ten years it helps six and hurts
four (2019 -8.18pp and 2021 -5.44pp are the others). A real filter, not a universal one, and it
should not be described as fixing the fade outright.

ROBUST, NOT A KNIFE-EDGE. Varying the threshold over a 3x range changes almost nothing:

    thr x0.50  kept 44.3%  gain +7.71pp        thr x1.25  kept 39.3%  gain +8.96pp
    thr x0.75  kept 42.5%  gain +8.87pp        thr x1.50  kept 37.7%  gain +8.15pp
    thr x1.00  kept 40.6%  gain +8.12pp

That matters more than the headline: a result surviving a 3x move in its only free parameter is
not a fitted cutoff. NOTE the retention floor is only just cleared (40.6% vs a 40% bar), so the
filter discards ~60% of alerts - a materially smaller book, and that belongs in sizing.

A BUG THAT INVALIDATED skew_25d'S FIRST TEST. 288 of 1,540 skew values were NaN (not None), so
they passed the `is not None` filter, `median` returned NaN, and every `>= threshold` comparison
was False - the filter kept ZERO trades while the coverage guard reported 100%. The reported
reason was wrong too ("no late-half coverage"). Both fixed: NaN excluded explicitly and the two
failure modes now distinguished. skew_25d then tested fairly on 605 late rows and rejected on
its merits (+1.10pp).

iv_rank IS NOT TESTABLE AS BUILT, not rejected. It needs 60 prior ATM-IV observations for a name
before a percentile means anything, but IV history was accumulated only from that name's own
alerts (~28 on average), so coverage was 0%. Testing it properly needs a daily ATM-IV series per
name across all trading days - a straightforward extension of the cached chain, but a fresh
compute pass. Calling it "rejected" would misrepresent an untested signal.

TICK FLOW remains untested: it needs the tick trade feed, which is not in the cached EOD history.


--------------------------------------------------------------------------------------------
A2 FOLLOW-UP (2026-08-02): iv_rank MADE TESTABLE, THEN REJECTED ON ITS MERITS.

Phase 3b could not test iv_rank at all: IV history was accumulated only from a name's own
alerts (~28), so the 60-observation minimum was never met and coverage was 0%. That was
reported as NOT TESTABLE rather than as a rejection, which was the right call - and this is the
follow-through.

A daily ATM-IV series was built across ALL trading days from the cached chains: 137,418
observations over 55 names, median 2,514 per name. iv_rank is then the percentile of the day's
ATM IV within that name's trailing 252 days, using STRICTLY PRIOR days - including the day's own
value would leak the observation into its own percentile.

    coverage   0.0%  ->  99.0%   (1,525 of 1,540 alerts)

Through the same pre-committed gate, it fails every arm:

    threshold (fit 2016-2020)   0.3968
    late-half kept              302/756 (39.9%)      bar >=40%      FAIL
    late expectancy             +4.76% -> +3.83%
    gain                        -0.93pp              bar >=+5pp     FAIL
    random control              +4.84%  (better than the filter)    FAIL
    early-half gain             -1.25pp              bar >0         FAIL

By year it is wildly inconsistent - it helps 2024 (+16.84% -> +22.48%) and 2025 (-0.05% ->
+5.50%) but destroys 2021 (+6.02% -> -19.45%) and 2023 (-4.61% -> -22.25%). Buying when vol is
already rich for the name is not a durable filter for a long-premium strategy, which is the
economically sensible reading.

REJECTED, and now on evidence rather than absence of it. The ATM-IV series is cached at
data/options/atm_iv_series.pkl and is reusable for anything else needing a vol-regime read.

TICK FLOW IS INFEASIBLE AT THIS SCALE, measured rather than assumed. option_history_trade
returns 6,259 rows in 5.0s for ONE expiry-day; across 55 names x ~2,500 days x ~8 expiries that
is 1,537-1,957 HOURS. option_history_trade_quote pairs each trade with the prevailing quote,
which is exactly what aggressor-side classification needs, so the signal is CONSTRUCTIBLE - just
not affordable historically. A restricted version (alert days only, ~1,841 x 6.4s ~ 3.3 hours)
would be feasible and is the sensible way to test it if anyone wants to.

"""
from __future__ import annotations

from typing import Optional

# Pre-committed gate.
MIN_LATE_GAIN = 0.05        # +5pp of expectancy on the 2021-2025 half
MIN_RETAINED = 0.40         # must keep >=40% of late-half trades
MIN_TRADES = 60             # filtered late-half trades
LATE_START = "2021-01-01"

SIGNALS = ("iv_rank", "vrp", "term_slope", "skew_25d", "gex_proxy")


# ==========================================================================================
#  O16 + O24 — WHAT IS `term_slope` ACTUALLY MEASURING?  PRE-REGISTRATION.
#  Committed BEFORE any number was computed. Nothing below was chosen with a result in view.
# ==========================================================================================
#
# `term_slope` = atm_mid (~60-DTE ATM IV) − atm_front (front-expiry ATM IV). It was the
# strongest single feature in the signal stack. The entry signal is measured dead (R2) and
# NOTHING here re-opens that; this is a characterisation of the FEATURE, which still feeds the
# live Signals surface and is the prerequisite for U2 (options surface → stock signals).
#
#   O16 — is it a front-IV LEVEL in disguise? A steep slope may just mean the front leg is
#         elevated. If so, every place both are used double-counts one exposure.
#   O24 — is it an EARNINGS CALENDAR in disguise? Front IV inflates mechanically before
#         earnings. If so its information is a date offset, not a vol-surface read.
#
# TEMPLATE, reused rather than reinvented: the PEAD rejection. Residualise on the incumbent,
# ask whether the orthogonal remainder predicts anything, and check whether a control using NO
# new data replicates the gain.
#
# DATA (banked; no new mining). `data/options_universe/state_r2_corrected.pkl` — the R2
# CORRECTED book, 3,885 trades / 186 names / 118 calendar months, term_slope coverage 100%.
# Explicitly NOT `state.pkl`, which is the void 3,042-trade pre-B1 book.
# Outcome variable: `pnl_pct` per trade.
#
# INFERENCE (the options lane's standing method). Date-block bootstrap, block = calendar
# month, via `options_stats.date_block_bootstrap`; 2,000 draws, seed 0. Clustering is reported
# with `effective_n`, i.e. the design effect ALWAYS beside its own shuffled null — per R3, a
# raw design effect is not evidence of clustering.
#
# THE NULL-VS-NULL TRAP, ruled on in advance. R2 measured the entry signal dead, so
# `term_slope`'s own IC may not be separable from zero on this book. If the RAW feature's IC
# has a date-block CI95 spanning zero, then comparing "raw IC" with "residual IC" cannot
# discriminate — two nulls are indistinguishable no matter which hypothesis is true. In that
# case the PREDICTIVE arm is declared UNINFORMATIVE and carries NO verdict weight, and the
# IDENTITY arm (correlation + variance decomposition) decides. Committed now precisely because
# it would be tempting later to read a null residual as "the confound explains it".
#
# ---- O16 protocol -----------------------------------------------------------------------
# 1. REPRODUCTION GATE, first and blocking. Recompute atm_front / atm_mid at every alert from
#    the banked chains through THIS module's own `compute_signals` path. The recomputed
#    `term_slope` must match the banked value within O16_REPRO_TOL for at least
#    O16_REPRO_MIN_FRAC of rows. If it does not, STOP and report — a decomposition of a
#    quantity we cannot reproduce is not evidence about anything.
# 2. IDENTITY: Pearson and Spearman of term_slope against atm_front and against atm_mid, plus
#    the variance decomposition var(ts) = var(mid) + var(front) − 2cov(mid, front).
# 3. RESIDUAL: OLS term_slope ~ a + b·atm_front; keep the residual.
# 4. PREDICTIVE: Spearman IC vs pnl_pct for term_slope, for −atm_front, and for the residual,
#    each with a date-block CI95.
# 5. NO-NEW-DATA CONTROL: rank alerts by −atm_front alone, keep the top O16_CONTROL_RETAIN
#    (term_slope's own shipped retention), and compare the mean-pnl uplift against the
#    term_slope filter at its shipped threshold, via `date_block_diff`.
#
# VERDICT RULE O16 — evaluated in this order, first match wins, no tie-breaks afterwards:
#   IS THE LEVEL  if |Spearman(ts, atm_front)| >= O16_LEVEL_RHO
#                 AND var(atm_front)/var(ts) >= O16_LEVEL_VAR_SHARE
#   IS DISTINCT   if |Spearman(ts, atm_front)| <  O16_DISTINCT_RHO
#                 OR  var(atm_mid)/var(ts) >= var(atm_front)/var(ts)
#   otherwise NULL (ambiguous is a NULL, it is not a lean).
#
# ---- O24 protocol -----------------------------------------------------------------------
# 1. days-to-next-earnings from EVENTS code 22 (`data_providers.earnings_dates`), the same
#    point-in-time source the PEAD study used.
# 2. ELIGIBILITY, committed before any outcome was seen: an alert counts only if its next
#    earnings date is within O24_MAX_DAYS. EVENTS coverage is PARTIAL (~2.8-3.2 dates/yr
#    against a true ~4), and the scoping pass found a maximum apparent gap of 3,004 days —
#    that is a hole in the calendar, not an eight-year earnings drought. Treating those as
#    "far from earnings" would load the test toward "not a calendar", i.e. toward the answer
#    this lane would find more convenient. Excluded as UNKNOWN and the count is reported.
# 3. Bucket by O24_BUCKETS and report mean/median term_slope per bucket with counts.
# 4. MODEL: OLS term_slope ~ bucket dummies. Statistic: R², the share of term_slope's variance
#    the earnings calendar alone can reconstruct.
# 5. DIRECTION, pre-committed: the mechanism REQUIRES term_slope to be most negative closest
#    to earnings, i.e. Spearman(term_slope, days_to_earnings) > 0. A significant slope of the
#    WRONG sign refutes the mechanism whatever R² says, and is recorded as such.
# 6. NO-NEW-DATA CONTROL: a filter that keeps only alerts more than 30 days from earnings —
#    does it replicate the term_slope filter's book gain?
#
# VERDICT RULE O24 — evaluated in this order, first match wins:
#   IS THE CALENDAR if R² >= O24_CALENDAR_R2 AND Spearman(ts, days) > 0 with a date-block
#                   CI95 excluding zero
#   IS DISTINCT     if R² <  O24_DISTINCT_R2
#   otherwise NULL.
#
# WHAT NO OUTCOME HERE CAN DO: none of this revives the entry signal (R2 stands), and none of
# it is a claim about live trading. A confirmed confound means the feature is redundant with
# something cheaper; a distinct verdict means U2 may use it as its own read.
# ==========================================================================================

O16_REPRO_TOL = 1e-6            # |recomputed − banked| term_slope
O16_REPRO_MIN_FRAC = 0.99       # fraction of rows that must reproduce, else STOP
O16_LEVEL_RHO = 0.80            # |rho(ts, atm_front)| at or above this => "is the level"
O16_LEVEL_VAR_SHARE = 0.60      # var(atm_front)/var(ts) at or above this => "is the level"
O16_DISTINCT_RHO = 0.60         # |rho| strictly below this => "distinct"
O16_CONTROL_RETAIN = 0.406      # term_slope's shipped retention, for a like-for-like control

O24_MAX_DAYS = 120              # next-earnings beyond this = UNKNOWN, excluded
O24_BUCKETS = ((0, 7), (8, 14), (15, 30), (31, 60), (61, 120))
O24_CALENDAR_R2 = 0.25          # R2 at or above this => "is the calendar"
O24_DISTINCT_R2 = 0.10          # R2 strictly below this => "distinct"

DECOMP_BLOCK = "month"          # date-block unit for every interval below
DECOMP_DRAWS = 2000
DECOMP_SEED = 0


# ------------------------------------------------------------------------------------------
#  Small statistics used by the O16/O24 decomposition.
#
#  Hand-rolled rather than pulled from scipy: this module is imported by the live signal path
#  and by the miner, and adding a scipy import there to serve a one-off study would be a poor
#  trade. Every one of these is pinned by tests/test_term_slope_decomp.py against worked
#  examples, including the tie cases that a naive rank implementation gets wrong.
# ------------------------------------------------------------------------------------------

def _ranks(vals):
    """Average ranks, ties sharing the mean of the positions they span (1-based)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(xs, ys) -> Optional[float]:
    """Pearson correlation. None if fewer than 3 usable pairs or either side is constant."""
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    n = len(pairs)
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    sxx = sum((a - mx) ** 2 for a, _ in pairs)
    syy = sum((b - my) ** 2 for _, b in pairs)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / (sxx ** 0.5 * syy ** 0.5)


def spearman(xs, ys) -> Optional[float]:
    """Spearman rank correlation, tie-corrected via average ranks."""
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    rx = _ranks([a for a, _ in pairs])
    ry = _ranks([b for _, b in pairs])
    return pearson(rx, ry)


def ols_fit(ys, xs):
    """Simple linear regression y = a + b*x. Returns (a, b) or None."""
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    n = len(pairs)
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    sxx = sum((a - mx) ** 2 for a, _ in pairs)
    if sxx <= 0:
        return None
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    b = sxy / sxx
    return (my - b * mx, b)


def ols_residuals(ys, xs):
    """Residuals of y on x, aligned with the inputs; None wherever either input is None."""
    fit = ols_fit(ys, xs)
    if fit is None:
        return [None] * len(ys)
    a, b = fit
    return [None if (x is None or y is None) else (y - (a + b * x))
            for x, y in zip(xs, ys)]


def group_mean_r2(ys, groups) -> Optional[float]:
    """R^2 of the group-mean model — the share of var(y) a categorical alone reconstructs.

    This IS the R^2 of an OLS on a full set of group dummies; computing it as 1 - SSE/SST over
    group means avoids building a design matrix for what is a one-way layout.
    """
    pairs = [(g, y) for g, y in zip(groups, ys) if g is not None and y is not None]
    if len(pairs) < 3:
        return None
    n = len(pairs)
    gm = sum(y for _, y in pairs) / n
    sst = sum((y - gm) ** 2 for _, y in pairs)
    if sst <= 0:
        return None
    by = {}
    for g, y in pairs:
        by.setdefault(g, []).append(y)
    sse = 0.0
    for g, vs in by.items():
        m = sum(vs) / len(vs)
        sse += sum((v - m) ** 2 for v in vs)
    return 1.0 - sse / sst


def variance_decomposition(mid, front) -> Optional[dict]:
    """var(term_slope) = var(mid) + var(front) - 2*cov(mid, front), and each leg's share.

    The shares do NOT sum to 1: the covariance term is the remainder, and it is reported
    rather than folded into either leg, because 'which leg carries the slope' is exactly the
    question and hiding the cross term would answer it by construction.
    """
    pairs = [(m, f) for m, f in zip(mid, front) if m is not None and f is not None]
    if len(pairs) < 3:
        return None
    n = len(pairs)
    mm = sum(m for m, _ in pairs) / n
    mf = sum(f for _, f in pairs) / n
    vm = sum((m - mm) ** 2 for m, _ in pairs) / (n - 1)
    vf = sum((f - mf) ** 2 for _, f in pairs) / (n - 1)
    cov = sum((m - mm) * (f - mf) for m, f in pairs) / (n - 1)
    vts = vm + vf - 2 * cov
    if vts <= 0:
        return None
    return {"n": n, "var_term_slope": vts, "var_atm_mid": vm, "var_atm_front": vf,
            "cov": cov, "share_atm_mid": vm / vts, "share_atm_front": vf / vts,
            "share_minus_2cov": (-2 * cov) / vts}


def o16_verdict(rho_front: Optional[float], share_front: Optional[float],
                share_mid: Optional[float]) -> str:
    """The committed O16 rule. First match wins; ambiguous is a NULL, not a lean."""
    if rho_front is None or share_front is None or share_mid is None:
        return "UNDECIDABLE (missing inputs)"
    if abs(rho_front) >= O16_LEVEL_RHO and share_front >= O16_LEVEL_VAR_SHARE:
        return "IS THE LEVEL"
    if abs(rho_front) < O16_DISTINCT_RHO or share_mid >= share_front:
        return "IS DISTINCT"
    return "NULL"


def o24_verdict(r2: Optional[float], rho_days: Optional[float],
                ci_excludes_zero: bool) -> str:
    """The committed O24 rule. First match wins; ambiguous is a NULL, not a lean."""
    if r2 is None or rho_days is None:
        return "UNDECIDABLE (missing inputs)"
    if r2 >= O24_CALENDAR_R2 and rho_days > 0 and ci_excludes_zero:
        return "IS THE CALENDAR"
    if r2 < O24_DISTINCT_R2:
        return "IS DISTINCT"
    return "NULL"


def reproduction_gate(banked, recomputed, tol: float = None,
                      min_frac: float = None) -> dict:
    """The committed O16 gate: can we still reproduce the quantity we are about to decompose?

    Executable rather than prose, for the same reason the verdict rules are: a gate that lives
    only in a runner script is a gate that gets skipped. It fired for real on 2026-08-07 — the
    banked options book was 86.4% reproducible, not 99%, because the chain store had been
    re-mined underneath it. `passed` false means STOP; a decomposition of a quantity we cannot
    reproduce is not evidence about anything.
    """
    tol = O16_REPRO_TOL if tol is None else tol
    min_frac = O16_REPRO_MIN_FRAC if min_frac is None else min_frac
    pairs = [(b, r) for b, r in zip(banked, recomputed) if b is not None and r is not None]
    if not pairs:
        return {"ok": False, "passed": False, "reason": "nothing comparable",
                "n": 0, "matched": 0, "frac": 0.0}
    diffs = sorted(abs(r - b) for b, r in pairs)
    matched = sum(1 for d in diffs if d <= tol)
    frac = matched / len(pairs)
    return {"ok": True, "passed": bool(frac >= min_frac), "n": len(pairs),
            "matched": matched, "frac": frac, "tol": tol, "min_frac": min_frac,
            "max_abs_diff": diffs[-1], "median_abs_diff": diffs[len(diffs) // 2]}


def earnings_bucket(days: Optional[int]) -> Optional[str]:
    """Bucket label for days-to-next-earnings, or None if outside the eligible window."""
    if days is None or days < 0 or days > O24_MAX_DAYS:
        return None
    for lo, hi in O24_BUCKETS:
        if lo <= days <= hi:
            return f"{lo}-{hi}d"
    return None


def _iv_at_delta(enr, target_delta: float, right: str) -> Optional[float]:
    """IV of the contract closest to a target delta on one expiry. None if nothing qualifies."""
    cand = [r for _, r in enr.iterrows()
            if str(r.get("right", ""))[:1].upper() == right[:1].upper()
            and r.get("delta") is not None and r.get("iv") is not None]
    if not cand:
        return None
    best = min(cand, key=lambda r: abs(abs(float(r["delta"])) - target_delta))
    return float(best["iv"])


def compute_signals(chain, underlying: float, as_of, iv_history=None,
                    realized_vol: Optional[float] = None) -> dict:
    """All five signals for one name on one date, from the cached chain. Missing -> absent.

    Absent rather than defaulted: a fabricated zero would be indistinguishable from a real
    neutral reading, and would flow into every downstream average.
    """
    import datetime as dt

    import pandas as pd

    from . import blackscholes as BS

    if chain is None or len(chain) == 0:
        return {}
    asof = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    exp = pd.to_datetime(chain["expiration"]).dt.date
    future = sorted({e for e in exp if e > asof})
    if not future:
        return {}
    out = {}

    front = future[0]
    enr_front = BS.enrich_chain(chain[exp == front], underlying, asof)
    atm_front = None
    if enr_front is not None and len(enr_front):
        near = enr_front.dropna(subset=["iv"]).copy()
        if len(near):
            near["_d"] = (near["strike"].astype(float) - underlying).abs()
            atm_front = float(near.sort_values("_d")["iv"].iloc[0])

    # ~60-DTE expiry for term structure and skew (the band we actually trade).
    mid_exp = min(future, key=lambda e: abs((e - asof).days - 60))
    enr_mid = BS.enrich_chain(chain[exp == mid_exp], underlying, asof)
    atm_mid = None
    if enr_mid is not None and len(enr_mid):
        near = enr_mid.dropna(subset=["iv"]).copy()
        if len(near):
            near["_d"] = (near["strike"].astype(float) - underlying).abs()
            atm_mid = float(near.sort_values("_d")["iv"].iloc[0])

    # AUDIT O16 — ship the two LEGS, not just their difference. `term_slope` is
    # `atm_mid - atm_front`, and every book ever banked kept only the difference, so the
    # question "is the slope just the front leg moving?" could not be asked of the stored data
    # at all — it needed a full re-derivation from the chains. Emitting both costs nothing (they
    # are already computed above) and makes the decomposition a lookup next time. Additive only:
    # no existing key changes, so no banked result moves.
    if atm_front is not None:
        out["atm_front"] = atm_front
    if atm_mid is not None:
        out["atm_mid"] = atm_mid

    if atm_front is not None and atm_mid is not None:
        out["term_slope"] = atm_mid - atm_front

    if enr_mid is not None and len(enr_mid):
        pv = _iv_at_delta(enr_mid, 0.25, "P")
        cv = _iv_at_delta(enr_mid, 0.25, "C")
        if pv is not None and cv is not None:
            out["skew_25d"] = pv - cv

    if atm_mid is not None:
        if realized_vol is not None and realized_vol > 0:
            # Negated: a long buyer wants IV BELOW realised, so cheaper = higher score.
            out["vrp"] = -(atm_mid - realized_vol)
        if iv_history:
            hist = [v for v in iv_history if v is not None]
            if len(hist) >= 60:
                out["iv_rank"] = sum(1 for v in hist if v < atm_mid) / len(hist)

    # GEX proxy: net dealer gamma across the near expiries we can price.
    if enr_mid is not None and len(enr_mid):
        g = enr_mid.dropna(subset=["gamma"])
        tot = 0.0
        for _, r in g.iterrows():
            oi = r.get("open_interest")
            if oi is None or oi < 0:
                continue
            sign = 1.0 if str(r.get("right", ""))[:1].upper() == "C" else -1.0
            tot += sign * float(oi) * float(r["gamma"])
        if tot:
            out["gex_proxy"] = tot * underlying / 1e6
    return out


def fit_threshold(early_rows, signal: str) -> Optional[float]:
    """Median of the signal among PROFITABLE early-half trades. Untuned by construction."""
    import statistics as st

    # NaN must be excluded explicitly: it is not None, so a naive filter lets it through and
    # st.median returns NaN, after which every `>= threshold` comparison is False and the signal
    # silently "keeps nothing" while appearing to have full coverage. That happened to skew_25d.
    vals = [v for v in (r.get(signal) for r in early_rows
                        if (r.get("pnl_pct") or 0) > 0)
            if v is not None and v == v]
    if len(vals) < 30:
        return None
    return st.median(vals)


def evaluate(rows, signal: str, seed: int = 0) -> dict:
    """Fit on 2016-2020, judge on 2021-2025, against the pre-committed gate."""
    import random

    from .options_tracker import _stats

    early = [r for r in rows if r["alert_ts"] < LATE_START]
    late = [r for r in rows if r["alert_ts"] >= LATE_START]
    thr = fit_threshold(early, signal)
    if thr is None:
        return {"signal": signal, "ok": False, "reason": "too few early-half values"}

    late_has = [r for r in late if r.get(signal) is not None and r[signal] == r[signal]]
    keep = [r for r in late_has if r[signal] >= thr]
    if not keep or not late_has:
        why = ("no late-half rows carry this signal" if not late_has
               else "filter kept ZERO late-half trades")
        return {"signal": signal, "ok": False, "reason": why, "threshold": thr}

    base, filt = _stats(late_has), _stats(keep)
    gain = (filt["expectancy_pct"] or 0) - (base["expectancy_pct"] or 0)
    retained = len(keep) / len(late_has)

    rnd = random.Random(seed)
    ctrl = []
    for _ in range(300):
        s = rnd.sample(late_has, min(len(keep), len(late_has)))
        ctrl.append(_stats(s)["expectancy_pct"] or 0)
    ctrl_mean = sum(ctrl) / len(ctrl)

    early_has = [r for r in early if r.get(signal) is not None and r[signal] == r[signal]]
    early_keep = [r for r in early_has if r[signal] >= thr]
    early_gain = ((_stats(early_keep)["expectancy_pct"] or 0)
                  - (_stats(early_has)["expectancy_pct"] or 0)) if early_keep else None

    passed = (gain >= MIN_LATE_GAIN and retained >= MIN_RETAINED
              and filt["n_closed"] >= MIN_TRADES
              and (filt["expectancy_pct"] or 0) > ctrl_mean
              and early_gain is not None and early_gain > 0)
    return {"signal": signal, "ok": True, "threshold": thr,
            "late_n_all": base["n_closed"], "late_n_kept": filt["n_closed"],
            "retained": retained,
            "late_exp_all": base["expectancy_pct"], "late_exp_filtered": filt["expectancy_pct"],
            "late_gain": gain, "random_control_exp": ctrl_mean,
            "early_gain": early_gain, "passed": passed}
