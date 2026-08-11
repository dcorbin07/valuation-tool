#!/usr/bin/env python3
"""track_meter.py — the pre-registered evidence meter for the forward paper track.

WHY THIS EXISTS. `PAPER_TRACK_CONTRACT.md` went IN FORCE on 2026-08-09 as **Option E**: keep
the 2026-07-30 inception including the accrued negative days, a 6-month operational gate, a
60-month statistical verdict against SPY, and -- the part this module is -- a pre-registered
anytime-valid evidence meter that runs from inception but first renders at the operational
gate and monthly thereafter, whatever it says.

THE POINT OF AN ANYTIME-VALID BOUND. The contract's verdict is a fixed-horizon test read once,
at 60 months. But a track that nobody may look at for five years is a track nobody will keep,
and a track that IS looked at monthly with a fixed-horizon statistic is a multiple-testing
machine: 60 monthly peeks at a t-test with a 5% bar produce a "significant" result far more
than 5% of the time under the null. A confidence sequence is the object that fixes this. It is
valid at EVERY n simultaneously, so looking every month costs nothing and no correction has to
be invented later. The price is paid up front, in width.

THE CONSTRUCTION, FIXED AND NOT REVISABLE. A Robbins normal-mixture confidence sequence on the
running sum of monthly excess returns. For observations with sub-Gaussian parameter `sigma`,

    boundary(n) = sigma * sqrt( (n + rho) * ln( (n + rho) / (rho * alpha^2) ) )

bounds |sum of (x_i - mu)| for all n at once with probability >= 1 - alpha. The sequence
crosses when the running sum leaves +/- boundary(n); crossing UP is SUPPORTED-EARLY, crossing
DOWN is UNSUPPORTED-EARLY, and both are valid conclusions precisely because the boundary was
fixed before any monthly observation existed.

EVERY PARAMETER WAS CHOSEN WITH ZERO MONTHLY DATA IN HAND, WHICH IS WHY THIS IS A GENUINE
PRE-REGISTRATION. At the commit that fixed them the track held five DAILY rows and **no
complete calendar month**, so there was no monthly series to tune against even in principle.

  * `sigma` is NOT estimated from the track. It is the backtest's own measured tracking error
    against SPY, 11.40pp/yr -> 3.2909pp/month, inflated by the AR(1) design effect implied by
    R9's measured lag-1 autocorrelation of +0.189: (1+r)/(1-r) = 1.4661, sqrt = 1.2108. That
    inflation is not decoration. Measured by Monte Carlo below: with it the false-crossing rate
    under the null is 1.5%; WITHOUT it, on the same autocorrelated data, 6.7% -- i.e. the naive
    version silently breaks its own 5% guarantee.
  * `rho` = 3 minimises the detectable edge averaged over the 12/24/36/60-month horizons, the
    range where an early conclusion would actually be actionable. The curve is flat between
    rho = 2 and rho = 6 (28.9 to 29.5 pp/yr), so the choice is not delicate.
  * `alpha` = 0.05 TWO-SIDED, i.e. 2.5% per direction.

WHAT IT ACTUALLY DELIVERS, STATED PLAINLY BECAUSE IT IS NOT FLATTERING. Measured, not asserted
(40k Monte Carlo paths with the AR(1) structure in them):

    false crossing under the null   1.5% by 60 months, 1.9% by 120   (nominal 5% -- conservative)
    power at the backtested edge    13.3% by 60 months, 30.7% by 120
    power at twice that edge        65.8% by 60 months

    mean excess needed to cross:  6m 63.7  12m 42.5  24m 29.6  36m 24.3  60m 19.0  120m 13.8 pp/yr

**So the meter will most likely never cross, even if the strategy is exactly as good as the
backtest says.** At 60 months it needs ~19 pp/yr against a claimed +9.99. That is the correct
and intended behaviour of an honest anytime-valid bound, and it is the reason the meter does
NOT replace the 60-month fixed-horizon verdict: the meter can only ever end the run EARLY, and
only for an effect far larger than the one claimed. Anyone who reads a non-crossing meter as
evidence against the strategy has made exactly the error the contract exists to prevent.

TWO RULES THAT ARE ANTI-GAMING, NOT STATISTICS:

  1. **`sigma` may never be revised DOWNWARD.** A smaller sigma narrows the band and makes
     crossing easier, so a downward revision is indistinguishable from buying a result. If
     realised volatility comes in ABOVE the plug-in the bound is anti-conservative and sigma
     must be raised (measured: at 1.5x the assumed sd the false-crossing rate is 20%, a 4x
     breach), which is why `meter()` reports `sigma_breach` on every call.
  2. **There is no sign-dependent branch anywhere in this file.** The render decision is a
     function of the DATE and the data's integrity only. Suppressing an unfavourable month
     voids the whole run under the contract's abort rule, and `test_meter_has_no_sign_branch`
     pins that the rendering decision is invariant to flipping the sign of every observation.

WHICH SERIES THIS BINDS. The published Valquo Index track -- `valquo_track.json` plus
`valquo_track_history.csv`, the source `valuation/screener/index_track.py` reads, whose book is
the 86-name score-weighted Index the contract names. It does NOT bind the Tradier sandbox
engine in `paper_track.py`: that engine records a DIFFERENT book -- 10 names against the
published 86 -- from a DIFFERENT inception (2026-08-03).

CORRECTED 2026-08-11 (cold audit LA11). That last sentence used to give the reason as "10
names, equal-weighted at 10%, WHICH THE CONTRACT'S OWN 8% CAP FORBIDS". It forbids no such
thing, and the project retracted the diagnosis in session 16 (`PT-SPLIT`):
`valquo_index.build_index` sets `cap = max(MAX_WEIGHT, 1/len(picks))` deliberately, because ten
names at 8% sum to 80% and the redistribution loop would otherwise never terminate -- and the
payload has always self-reported `effective_max_weight`. The weights were right for the book;
the BOOK was wrong. The CONCLUSION is unchanged and now rests on book SIZE, the ground that
holds. The retracted reason was worse than no reason at all: a reader who checks the cap finds
it correct and may conclude the whole separation was mistaken.

See `gap_report` and the session-14 handoff -- the divergence is recorded, not resolved here.
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Dict, List, Optional, Sequence

from valuation.screener.market_session import is_trading_day

# ---------------------------------------------------------------------------
# FROZEN by the contract's commit. Derivations are shown so they are auditable,
# then pinned to literals by tests. Changing any of these after 2026-08-09 voids
# the run under the contract's abort rule -- it is not a code change, it is a
# breach of a pre-registration.
# ---------------------------------------------------------------------------

CONTRACT_VERSION = "option-E-2026-08-09+amendment-1"

# --- VINTAGES (contract §5a, Amendment 1, 2026-08-09) ------------------------
# An ADOPTED change to scoring, weights or construction closes the current vintage and opens the
# next. Rebalancing under unchanged rules is NOT a vintage event. Each vintage carries its own
# clock, and the gate and the meter attach to the CURRENT one -- a verdict is a statement about
# a vintage and must name it. Voided vintages are kept, never deleted: they still appear in
# `as_operated()`, which is the honest "what a user would have experienced" series and is
# explicitly NOT the object of a contract verdict, because it mixes models.
VINTAGES = (
    {"vintage": 1, "run": 1, "opened": _dt.date(2026, 7, 30), "closed": _dt.date(2026, 8, 9),
     "status": "VOID", "label": "growth-input and score fixes, universe rebuild",
     "reason": "growth-input fix, score fix, universe rebuild - the measured model no longer "
               "exists. Voided by Amendment 1 under §3's 'any change to how the Index is "
               "constructed'. The voided window was known to be -2.85pp; see §5a's disclosure."},
    {"vintage": 2, "run": 2, "opened": _dt.date(2026, 8, 10),
     "closed": _dt.date(2026, 8, 11), "status": "CLOSED",
     "label": "opened by Amendment 1",
     "reason": "opened by Amendment 1, with ZERO accrued days - so no window's sign could have "
               "informed this start date. CLOSED 2026-08-11 by the theme restoration: "
               "capital_discipline reached a live score for the first time, which changes the "
               "composite users receive and is therefore an ADOPTED change. It accrued ONE day."},
    # VINTAGE 3 - opened 2026-08-11 by the theme restoration.
    #
    # THE PRICE IS PAID IN FULL AND IS THE POINT OF RECORDING IT HERE. Rule 6: a vintage change
    # resets the whole accrued clock and buys nothing statistically. Vintage 2 accrued one day,
    # so the reset costs almost nothing THIS time - which is exactly why this was the moment to
    # do it, and why doing it later would have been far more expensive.
    #
    # THE ARGUMENT THAT THIS IS A BUG FIX RATHER THAN A VINTAGE EVENT, AND WHY IT LOSES:
    # vintage 2's pinned snapshot already DECLARED all seven themes at 0.125, so restoring one
    # could be read as bringing live into conformance with what vintage 2 always claimed. It
    # loses because Amendment 1 defines "adopted" as SHIPS IN THE LIVE SCORING PATH, and the
    # book users receive changes materially. Whatever the track accrued, it accrued while
    # recording a FOUR-theme book; that record cannot be carried forward as evidence about a
    # five-theme one.
    {"vintage": 3, "run": 2, "opened": _dt.date(2026, 8, 11), "closed": None, "status": "OPEN",
     "label": "capital_discipline restored",
     "reason": "opened by the theme restoration - capital_discipline reaches a live score from "
               "free SEC XBRL company facts, after clearing a pre-registered fidelity gate at "
               "Spearman +0.8421 against the panel's own theme. institutional (+0.1706) and "
               "insider (+0.3596) FAILED that gate and are deliberately still absent. No weight "
               "or construction parameter changed."},
)


def current_vintage() -> dict:
    """The one open vintage. Exactly one may be open; anything else is a defect, not a default."""
    live = [v for v in VINTAGES if v["status"] == "OPEN"]
    if len(live) != 1:
        raise RuntimeError(f"expected exactly one OPEN vintage, found {len(live)}")
    return live[0]


def vintage_label() -> dict:
    """How the OPERATED RECORD names itself, computed from the register above.

    WHY THIS IS DERIVED AND NOT A STRING SOMEBODY TYPES
    ---------------------------------------------------
    §5a Rule 4: "a verdict is a statement about a vintage, and must name it." A surface showing
    a forward track is showing exactly such a statement, so it has to say WHICH vintage -- and
    the moment that name is hand-written on a page it starts drifting from the register. This
    session is the proof: the work was commissioned as "vintage 2 since 2026-08-11, vintage 1 in
    shadow", and the register says the live vintage is 3 and the shadowed one is 2. The theme
    restoration had already opened a vintage that the request had not caught up with. Deriving
    the label means the page cannot be wrong about this even for a day.

    That is also why the test pins the DERIVATION and not the number. `test_track_meter.py`
    already learned this the hard way -- it used to assert "it is vintage 2", and a legitimate
    vintage event then failed a test that exists to catch two vintages being open at once.

    THE SHADOW HALF, AND WHY IT IS COMPUTED HERE RATHER THAN IMPORTED
    ----------------------------------------------------------------
    The predecessor is the highest-numbered vintage below the open one -- a fact about THIS
    register. `shadow_vintage.open_pairs()` answers the neighbouring question of whether that
    predecessor can actually be SCORED (it needs a pinned parameter snapshot), and importing it
    here would invert this module's dependency direction for a number it already holds.
    The two are cross-checked by `tests/test_vintage_label.py`, which may import both.

    NOTHING MEASURED CROSSES THIS FUNCTION. It returns bookkeeping -- which vintage, opened
    when, what opened it -- and no return, excess or paired difference. That distinction is what
    keeps `V1`'s outbound fence meaningful: PT-OUTBOUND leaked a research FIGURE, and the fence
    exists to stop that, not to make the vintage's existence a secret from its own owner.
    """
    cur = current_vintage()
    n = int(cur["vintage"])
    earlier = [int(v["vintage"]) for v in VINTAGES if int(v["vintage"]) < n]
    shadow = max(earlier) if earlier else None
    since = cur["opened"].isoformat()
    reason = (cur.get("label") or "").strip()

    # "Book vintage 3 since 2026-08-11 (capital_discipline restored)" -- then the shadow clause
    # only when there IS a predecessor. Vintage 1 had none, and a trailing "; None runs in
    # shadow" is exactly the kind of stub that reads as a bug on the one surface nobody revisits.
    head = f"Book vintage {n} since {since}"
    if reason:
        head += f" ({reason})"
    phrase = head if shadow is None else f"{head}; vintage {shadow} runs in shadow"

    return {
        "vintage": n,
        "since": since,
        "label": reason,
        "shadow_vintage": shadow,
        "phrase": phrase,
        # The contract's own words for what this record is and is not. Carried WITH the label
        # so a surface cannot show the vintage name while dropping the reason it matters.
        "rule": ("An adopted change to scoring, weights or construction closes the current "
                 "vintage and opens the next. Each vintage carries its own clock, and a verdict "
                 "is a statement about a vintage, not about the system as a whole."),
    }


def _months_after(d: _dt.date, n: int) -> _dt.date:
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return _dt.date(y, m, day)


GATE_MONTHS = 6
VERDICT_MONTHS = 60

INCEPTION = current_vintage()["opened"]                       # 2026-08-10 (vintage 2)
OPERATIONAL_GATE = _months_after(INCEPTION, GATE_MONTHS)      # 2027-02-10; also FIRST RENDER
FIRST_RENDER = OPERATIONAL_GATE
VERDICT_DATE = _months_after(INCEPTION, VERDICT_MONTHS)       # 2031-08-10

# sigma: the backtest's own tracking error vs SPY, inflated for autocorrelation.
_TRACKING_ERROR_ANNUAL_PP = 11.40             # benchmarks.spy, corrected 69-date panel
_LAG1_AUTOCORR = 0.189                        # audit R9, the project's only measurement of it
_DESIGN_EFFECT = (1.0 + _LAG1_AUTOCORR) / (1.0 - _LAG1_AUTOCORR)          # 1.466091
SIGMA_MONTHLY_PP = (_TRACKING_ERROR_ANNUAL_PP / math.sqrt(12.0)) * math.sqrt(_DESIGN_EFFECT)

RHO = 3.0
ALPHA = 0.05                                  # two-sided; 2.5% per direction

# Modelled cost drag, subtracted from every monthly excess. The recorded series is GROSS, and
# the contract promises the verdict net of the costs the backtest charges. Derived from the
# backtest's own figures the way its breakeven is derived -- 261% annual turnover at a measured
# 33.4 bps one-way, charged both legs: 2 * 2.61 * 0.334pp = 1.7435 pp/yr. That is the LARGER of
# the two readings available in the record, i.e. the one that counts against the strategy, and
# it is a constant, so it shifts the series by a fixed amount and cannot interact with outcome.
_ANNUAL_TURNOVER = 2.61
_ONE_WAY_COST_PP = 0.334
COST_DRAG_PP_PER_MONTH = (2.0 * _ANNUAL_TURNOVER * _ONE_WAY_COST_PP) / 12.0

# A month's mark is the last row on or before its final trading day. If that row is staler than
# this, the month is VOIDED rather than measured against a mark from the wrong window.
MARK_STALENESS_LIMIT_TD = 3

# If more than this fraction of elapsed months are voided for missing data, the series is not
# trustworthy enough to carry a verdict and the meter says so instead of quietly averaging.
MAX_VOIDED_FRACTION = 0.10


def boundary(n: int, sigma: float = None, rho: float = None, alpha: float = None) -> float:
    """Robbins normal-mixture boundary on the running SUM of centred observations.

    Defaults are the frozen contract parameters. The arguments exist so the Monte Carlo
    calibration can probe other values -- NOT so a caller can retune the live meter.
    """
    sigma = SIGMA_MONTHLY_PP if sigma is None else sigma
    rho = RHO if rho is None else rho
    alpha = ALPHA if alpha is None else alpha
    if n < 1:
        raise ValueError("n must be >= 1")
    v = n + rho
    return sigma * math.sqrt(v * math.log(v / (rho * alpha * alpha)))


def detectable_edge_pp_per_year(n: int) -> float:
    """The mean excess a run must sustain for `n` months to cross. The honest headline."""
    return boundary(n) / n * 12.0


# ---------------------------------------------------------------------------
# Series handling
# ---------------------------------------------------------------------------

def _d(x) -> Optional[_dt.date]:
    if isinstance(x, _dt.date):
        return x
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def _trading_days(start: _dt.date, end: _dt.date) -> List[_dt.date]:
    out, d = [], start
    while d <= end:
        if is_trading_day(d):
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def _month_end_trading_day(year: int, month: int) -> _dt.date:
    if month == 12:
        nxt = _dt.date(year + 1, 1, 1)
    else:
        nxt = _dt.date(year, month + 1, 1)
    d = nxt - _dt.timedelta(days=1)
    while not is_trading_day(d):
        d -= _dt.timedelta(days=1)
    return d


def gap_report(series: Sequence[dict], as_of: _dt.date = None,
               inception: _dt.date = None) -> Dict:
    """Every trading day that should have a row and does not. LOUD BY DESIGN.

    The contract's abort rule distinguishes "missed a day and filled it the same week" from
    "missing", and neither can be told apart from the other unless the misses are enumerated at
    the time. So this returns the actual dates, not a count -- a count cannot be audited later.

    This is the operational gate's checklist, not a statistical object: an interior gap does NOT
    corrupt a monthly return, because the series stores cumulative-since-inception levels and a
    month's return only needs its two endpoints. `monthly_excess` handles that separately.
    """
    inception = inception or INCEPTION
    as_of = as_of or _dt.date.today()
    have = {_d(r.get("date")) for r in series}
    have.discard(None)
    # Inception is day 0: cumulative return is 0 there by definition and the recorded series
    # starts at day 1. Counting the inception date itself as a missing row would report a
    # permanent, uncloseable gap -- the guard has to be right about what it demands.
    expected = [d for d in _trading_days(inception, as_of) if d > inception]
    missing = [d for d in expected if d not in have]
    # A row on a non-trading day is its own defect: it means something marked the book when
    # there was no close, which is the failure auto-scan's session guard exists to prevent.
    unexpected = sorted(d for d in have if d and d >= inception and not is_trading_day(d))
    return {
        "inception": inception.isoformat(),
        "as_of": as_of.isoformat(),
        "expected_trading_days": len(expected),
        "present": len([d for d in expected if d in have]),
        "missing_count": len(missing),
        "missing_dates": [d.isoformat() for d in missing],
        "unexpected_dates": [d.isoformat() for d in unexpected],
        "complete": not missing and not unexpected,
        "coverage": (len(expected) - len(missing)) / len(expected) if expected else None,
    }


def monthly_excess(series: Sequence[dict], as_of: _dt.date = None,
                   inception: _dt.date = None) -> Dict:
    """Chain the cumulative daily series into COMPLETE calendar months of excess return.

    The rows hold cumulative-since-inception percentages, so month m's return is
    (1+cum_end/100)/(1+cum_prev/100) - 1 -- the same chaining `index_track._daily_returns` uses,
    and the reason an interior missing day is survivable while a missing month-end is not.

    A month is VOIDED (never silently averaged over) when its mark is missing or staler than
    MARK_STALENESS_LIMIT_TD trading days. Voids are returned with their reason so the contract's
    "recorded at the time it is found, not at the horizon" rule can actually be honoured.
    """
    inception = inception or INCEPTION
    as_of = as_of or _dt.date.today()
    rows = []
    for r in series:
        d = _d(r.get("date"))
        v, s = r.get("valquo"), r.get("spy")
        if d is None or v is None or s is None:
            continue
        rows.append((d, float(v), float(s)))
    rows.sort(key=lambda t: t[0])

    months, voided = [], []
    # BASELINE AT THE VINTAGE'S OPENING LEVEL, NOT AT ZERO. The recorded series holds cumulative
    # return since the ORIGINAL inception, and Amendment 1 opened vintage 2 partway through it.
    # Baselining a later vintage at 0 would fold the earlier vintage's drift into its first
    # month. Taking the level at the vintage's opening date is correct whether the writer resets
    # its cumulative on a vintage change or carries it forward, so this does not depend on a
    # behaviour of the Cowork writer that nobody here controls.
    base = [t for t in rows if t[0] <= inception]
    prev_v, prev_s = (base[-1][1], base[-1][2]) if base else (0.0, 0.0)
    prev_mark = inception

    # THE STUB MONTH IS MERGED FORWARD, NOT COUNTED. Inception is 2026-07-30, so the calendar
    # month it falls in contains a single trading day of exposure. Admitting that as a monthly
    # observation would feed the confidence sequence a draw with ~1/21 of a month's variance --
    # the bound assumes every observation has variance sigma^2, and a one-day "month" does not.
    # So unless inception falls on or before its month's first trading day, the stub runs on
    # into the next month and the first observation covers inception -> that month's end.
    y, m = inception.year, inception.month
    _first_td = min(_trading_days(_dt.date(y, m, 1), _month_end_trading_day(y, m)))
    if inception > _first_td:
        m += 1
        if m == 13:
            y, m = y + 1, 1
    while True:
        mend = _month_end_trading_day(y, m)
        if mend > as_of:
            break
        # The last row on or before this month's final trading day.
        cand = [t for t in rows if t[0] <= mend]
        label = f"{y:04d}-{m:02d}"
        if not cand or cand[-1][0] <= prev_mark:
            voided.append({"month": label, "reason": "no mark in the month"})
        else:
            d, v, s = cand[-1]
            stale = len(_trading_days(d, mend)) - 1      # trading days from mark to month end
            if stale > MARK_STALENESS_LIMIT_TD:
                voided.append({"month": label, "reason": f"mark {stale} trading days stale",
                               "mark_date": d.isoformat()})
            else:
                rv = (1.0 + v / 100.0) / (1.0 + prev_v / 100.0) - 1.0
                rs = (1.0 + s / 100.0) / (1.0 + prev_s / 100.0) - 1.0
                months.append({
                    "month": label, "mark_date": d.isoformat(), "stale_trading_days": stale,
                    "valquo_ret_pp": rv * 100.0, "spy_ret_pp": rs * 100.0,
                    "excess_gross_pp": (rv - rs) * 100.0,
                    "excess_pp": (rv - rs) * 100.0 - COST_DRAG_PP_PER_MONTH,
                })
                prev_v, prev_s, prev_mark = v, s, d
        m += 1
        if m == 13:
            y, m = y + 1, 1

    elapsed = len(months) + len(voided)
    return {
        "months": months, "voided": voided,
        "n_months": len(months), "n_voided": len(voided), "n_elapsed": elapsed,
        "voided_fraction": (len(voided) / elapsed) if elapsed else 0.0,
        "cost_drag_pp_per_month": COST_DRAG_PP_PER_MONTH,
    }


def meter(series: Sequence[dict], as_of: _dt.date = None,
          inception: _dt.date = None) -> Dict:
    """The full pre-registered meter. Computed from inception; RENDERED from FIRST_RENDER.

    `rendered` is a function of the date and the series' integrity ONLY. It never consults the
    sign of the result -- see the module docstring's rule 2 and the test that pins it.
    """
    as_of = as_of or _dt.date.today()
    inception = inception or INCEPTION

    gaps = gap_report(series, as_of=as_of, inception=inception)
    mx = monthly_excess(series, as_of=as_of, inception=inception)
    xs = [mo["excess_pp"] for mo in mx["months"]]
    n = len(xs)

    vin = current_vintage() if inception == INCEPTION else None
    out = {
        "contract_version": CONTRACT_VERSION,
        "as_of": as_of.isoformat(),
        "inception": inception.isoformat(),
        "vintage": vin["vintage"] if vin else None,
        "run": vin["run"] if vin else None,
        "first_render": FIRST_RENDER.isoformat(),
        "verdict_date": VERDICT_DATE.isoformat(),
        "params": {"sigma_monthly_pp": SIGMA_MONTHLY_PP, "rho": RHO, "alpha": ALPHA,
                   "cost_drag_pp_per_month": COST_DRAG_PP_PER_MONTH},
        "n_months": n, "gaps": gaps, "voided": mx["voided"],
        "voided_fraction": mx["voided_fraction"],
    }

    # Display gate. Both conditions are date/integrity only.
    too_early = as_of < FIRST_RENDER
    untrustworthy = mx["voided_fraction"] > MAX_VOIDED_FRACTION
    out["rendered"] = (not too_early) and n >= 1 and not untrustworthy
    out["render_blocked_reason"] = (
        "before the contract's first-render date" if too_early else
        "no complete month yet" if n < 1 else
        f"{mx['n_voided']} of {mx['n_elapsed']} months voided for missing data" if untrustworthy
        else None)

    if n < 1:
        out["computable"] = False
        return out

    s = sum(xs)
    b = boundary(n)
    out.update({
        "computable": True,
        "sum_excess_pp": s,
        "mean_excess_pp_per_month": s / n,
        "mean_excess_pp_per_year": s / n * 12.0,
        "boundary_sum_pp": b,
        "ci_lower_pp_per_month": (s - b) / n,
        "ci_upper_pp_per_month": (s + b) / n,
        "detectable_edge_pp_per_year": detectable_edge_pp_per_year(n),
        "crossed": "up" if s >= b else ("down" if s <= -b else None),
        "state": "SUPPORTED-EARLY" if s >= b else ("UNSUPPORTED-EARLY" if s <= -b
                                                   else "NO CONCLUSION"),
    })

    # Anti-conservatism guard: the bound assumes sigma. If realised volatility exceeds it the
    # band is too narrow and sigma must be RAISED (never lowered) with the change logged.
    if n >= 2:
        mu = s / n
        sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))
        out["realised_sd_pp_per_month"] = sd
        out["sigma_breach"] = sd > SIGMA_MONTHLY_PP
    else:
        out["realised_sd_pp_per_month"] = None
        out["sigma_breach"] = False
    return out


def as_operated(series: Sequence[dict], as_of: _dt.date = None) -> Dict:
    """The cross-vintage record — "the system as operated" (contract §5a rule 5).

    Every vintage chained end to end, INCLUDING voided ones. This is the honest answer to "what
    would a user actually have experienced", and it is deliberately a different object from the
    meter: it mixes models, so **no §5 verdict may be read from it**. It is reported beside the
    meter, never instead of it, and the returned dict says so in `not_a_verdict`.
    """
    as_of = as_of or _dt.date.today()
    rows = []
    for r in series:
        d, v_, s_ = _d(r.get("date")), r.get("valquo"), r.get("spy")
        if d is not None and v_ is not None and s_ is not None:
            rows.append((d, float(v_), float(s_)))
    rows.sort(key=lambda t: t[0])

    legs, cum_v, cum_s = [], 1.0, 1.0
    for v in VINTAGES:
        start = v["opened"]
        end = min(v["closed"] or as_of, as_of)
        if end < start:
            continue
        # RAW ENDPOINTS, NOT COMPLETE MONTHS. "What a user experienced" is not a monthly object:
        # vintage 1 ran six days and holds no complete calendar month, so a month-based leg would
        # report it as 0.0% when it actually moved -2.85pp. The meter is monthly because its
        # statistic requires it; this series is not the meter and must not borrow its granularity.
        base = [t for t in rows if t[0] <= start]
        upto = [t for t in rows if t[0] <= end]
        b_v, b_s = (base[-1][1], base[-1][2]) if base else (0.0, 0.0)
        if not upto or upto[-1][0] <= start:
            rv = rs = 1.0
            n_rows = 0
        else:
            e_v, e_s = upto[-1][1], upto[-1][2]
            rv = (1.0 + e_v / 100.0) / (1.0 + b_v / 100.0)
            rs = (1.0 + e_s / 100.0) / (1.0 + b_s / 100.0)
            n_rows = len([t for t in rows if start < t[0] <= end])
        cum_v *= rv
        cum_s *= rs
        legs.append({"vintage": v["vintage"], "run": v["run"], "status": v["status"],
                     "opened": start.isoformat(),
                     "closed": (v["closed"].isoformat() if v["closed"] else None),
                     "n_rows": n_rows,
                     "valquo_ret_pp": (rv - 1.0) * 100.0, "spy_ret_pp": (rs - 1.0) * 100.0,
                     "excess_pp": (rv - rs) * 100.0})
    return {
        "label": "the system as operated",
        "not_a_verdict": ("chains across vintages and therefore across MODELS; the contract's "
                          "verdict is read on the current vintage alone (§5a rule 5)"),
        "legs": legs,
        "n_vintages": len(legs),
        "cumulative_valquo_pp": (cum_v - 1.0) * 100.0,
        "cumulative_spy_pp": (cum_s - 1.0) * 100.0,
        "cumulative_excess_pp": (cum_v - cum_s) * 100.0,
    }


def _authoritative_claim(meta_path=None, history_path=None) -> Dict:
    """The bound recorder's OWN Index-vs-SPY figure — the one authority for that claim."""
    try:
        from ..screener.index_track import vs_spy_claim
        return vs_spy_claim(meta_path=meta_path, history_path=history_path) or {
            "available": False, "reason": "vs_spy_claim returned nothing"}
    except Exception as e:                                   # noqa: BLE001
        return {"available": False, "reason": f"authority unreadable: {type(e).__name__}"}


def _reconcile(ao: Dict, claim: Dict, tol_pp: float = 0.01):
    """Does the cross-vintage chain agree with the authority's since-inception figure?

    `None` when the authority has nothing to say (a normal state on a fresh deploy). A False
    here is not cosmetic: it means two derivations of the same object disagree, which is exactly
    the state that let a wrong number ship on 2026-08-05.
    """
    if not claim.get("available") or claim.get("excess_pp") is None:
        return None
    return abs(float(ao["cumulative_excess_pp"]) - float(claim["excess_pp"])) <= tol_pp


def detail(series: Sequence[dict] = None, as_of: _dt.date = None,
           meta_path: str = None, history_path: str = None) -> Dict:
    """The block the running path surfaces on every request (roadmap: session 15's first item).

    Two things have to be visible continuously rather than discovered at the operational gate:
    whether the track is being RECORDED at all, and what the (withheld) meter currently says.
    Before Amendment 1 the recording failure was only findable by someone going to look; a gate
    that fails in January because nobody noticed in August is a gate that cost five months.

    Reads the BOUND source (the published Valquo Index) itself when no series is passed, so a
    caller cannot accidentally point it at the sandbox engine, which records a different book.
    Never raises: an unreadable track is a normal state and must degrade to "not started", not
    to a 500 on a page that has nothing to do with it.
    """
    as_of = as_of or _dt.date.today()
    if series is None:
        try:
            from ..screener.index_track import load
            series = (load(meta_path, history_path) or {}).get("series") or []
        except Exception as e:                               # noqa: BLE001
            return {"available": False, "reason": f"track unreadable: {type(e).__name__}",
                    "contract_version": CONTRACT_VERSION}
    try:
        v = current_vintage()
        m = meter(series, as_of=as_of)
        gaps = m["gaps"]
        out = {
            "available": True,
            "contract_version": CONTRACT_VERSION,
            "source": "published Valquo Index (valquo_track_history.csv)",
            "not_the_sandbox_engine": True,
            "vintage": v["vintage"], "run": v["run"],
            # The register's own rendering of itself. `vintage` above is the number a caller
            # computes with; this is the sentence a surface prints, and it exists so that
            # printing one never means re-deriving the other by hand.
            "vintage_label": vintage_label(),
            "inception": v["opened"].isoformat(),
            "operational_gate_date": OPERATIONAL_GATE.isoformat(),
            "verdict_date": VERDICT_DATE.isoformat(),
            "meter": m,
            "as_operated": as_operated(series, as_of=as_of),
        }
        # THE AUTHORITY FOR ANY vs-SPY NUMBER A PERSON RECEIVES IS `vs_spy_claim`, NOT THIS
        # MODULE (ledger PT-OUTBOUND: the Discord recap once printed the sandbox engine's
        # +0.18pp as the Index while the bound recorder read -0.28pp). This module legitimately
        # computes its own excess -- the meter's statistic is monthly, per-vintage and net of a
        # modelled cost drag, so it is a DIFFERENT object and would be wrong to read off the
        # claim. But `as_operated` is the same kind of object as the claim, so it is reconciled
        # against it here and any disagreement is reported rather than left to be discovered.
        out["vs_spy_claim"] = _authoritative_claim(meta_path, history_path)
        out["as_operated_agrees_with_authority"] = _reconcile(
            out["as_operated"], out["vs_spy_claim"])
        # The one line a human should read. Deliberately blunt about the failure mode -- and
        # NOT VACUOUSLY GREEN: before the vintage's first trading day there are zero expected
        # rows, so `complete` is trivially true and reporting "every trading day recorded" would
        # be a pass that means nothing. A bound that cannot fail yet must say so.
        started = gaps["expected_trading_days"] > 0
        out["started"] = started
        out["recording_ok"] = bool(gaps["complete"]) if started else None
        out["recording_note"] = (
            f"vintage {v['vintage']} has not started - inception {v['opened'].isoformat()}, "
            f"no trading day due yet, so nothing is verified either way" if not started else
            f"every one of {gaps['expected_trading_days']} trading days recorded"
            if gaps["complete"] else
            f"{gaps['missing_count']} of {gaps['expected_trading_days']} trading days MISSING "
            f"since inception - the operational gate cannot pass while this is true")
        return out
    except Exception as e:                                   # noqa: BLE001
        return {"available": False, "reason": f"meter failed: {type(e).__name__}: {e}",
                "contract_version": CONTRACT_VERSION}


def frozen_parameters() -> Dict:
    """Everything the contract fixed, in one auditable dict."""
    return {
        "contract_version": CONTRACT_VERSION,
        "vintages": [{**v, "opened": v["opened"].isoformat(),
                      "closed": v["closed"].isoformat() if v["closed"] else None}
                     for v in VINTAGES],
        "current_vintage": current_vintage()["vintage"],
        "inception": INCEPTION.isoformat(),
        "operational_gate": OPERATIONAL_GATE.isoformat(),
        "first_render": FIRST_RENDER.isoformat(),
        "verdict_date": VERDICT_DATE.isoformat(),
        "sigma_monthly_pp": SIGMA_MONTHLY_PP,
        "sigma_derivation": {"tracking_error_annual_pp": _TRACKING_ERROR_ANNUAL_PP,
                             "lag1_autocorr": _LAG1_AUTOCORR, "design_effect": _DESIGN_EFFECT},
        "rho": RHO, "alpha": ALPHA,
        "cost_drag_pp_per_month": COST_DRAG_PP_PER_MONTH,
        "mark_staleness_limit_td": MARK_STALENESS_LIMIT_TD,
        "max_voided_fraction": MAX_VOIDED_FRACTION,
        "detectable_edge_pp_per_year": {n: detectable_edge_pp_per_year(n)
                                        for n in (6, 12, 24, 36, 60, 120)},
    }
