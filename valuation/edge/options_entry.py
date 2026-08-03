"""
Roadmap 22c — the scream-buy alert picks WORSE-THAN-RANDOM entry days. Diagnose it, then try to
fix it.

PRE-SPECIFIED. Everything from here to the "RESULT" banner was written and committed BEFORE any
arm was run. That matters more here than in any previous options study, because this session
searches over NINE entry rules on a heavy-tailed payoff. A gate chosen after seeing nine sets of
numbers is not a gate, it is a ranking.

--------------------------------------------------------------------------------------------
THE FINDING THIS EXISTS TO EXPLAIN.

22b ran the first placebo this project has ever had on the options book: same ticker, same
calendar year, identical contract rule, fill model and exit discipline — RANDOM ENTRY DAY. On
187 names it beat the alert:

    alert-day book      +5.14%/trade        random-day book     +13.22%/trade
    the alert book won 441 of 1,052 name-year cells (41.9%), sign-test z = -5.24, two seeds.

Holding name and year fixed removes "this name compounded over the decade" and "2020 was a good
year" from the comparison. What is left is day selection, and day selection is NEGATIVE. The
contracts are near-identical (DTE 58 vs 58, delta 0.355 vs 0.351, premium $4.85 vs $4.50), so
this is not a contract-selection artifact either.

That is not "no edge". A signal with no information picks average days. This one picks BAD days,
which is information — IF it is real, stable, and invertible. All three of those are open
questions and this module is about answering them, not assuming them.

--------------------------------------------------------------------------------------------
THE MECHANISM HYPOTHESIS, STATED BEFORE IT IS TESTED.

The scream-buy score is 0.70 * technical + 0.30 * options-flow, and the technical half requires
a strong, extended, high-momentum tape. So the alert fires AFTER the move, on the excitement.
Two things are true of such a day and both hurt a long-premium buyer:

  1. IV IS ALREADY PUMPED. The move that triggered the alert also bid up the options. You pay
     for a move that has largely happened, and then eat the vol normalisation.
  2. THE UNDERLYING IS EXTENDED. Buying the top of a run means the mean-reversion is in front of
     you rather than behind you.

If that is the mechanism, the alert's NAME selection may still be fine — the control only ever
proved the DAY is bad — and the fix is to keep the setup and change the timing.

The hypothesis is FALSIFIABLE and may well be wrong. If alert days do not carry richer IV and
more run-up than random days in the same name-year, it is rejected and the -5.24 is something
else (or noise), and this module says so.

--------------------------------------------------------------------------------------------
THE NINE ARMS. Every parameter below is fixed HERE, before the run, and none is tuned.

All arms share the SAME alert list, the SAME contract rule (~35 delta, 45-75 DTE), the SAME
NBBO fills at aggression 1.0 and the SAME exits (+100% / -50% / half-DTE). Exactly one thing
varies: which day you enter.

    signal          the alert day.                                       (the baseline)
    delay3/5/10     N trading days after the alert.                      (does the pump decay?)
    pullback        within WAIT_WINDOW days, the first close <= alert close * (1 - PULLBACK_PCT);
                    no pullback -> no trade.                             (buy the dip, not the rip)
    pullback_or_w   as above but enter at day WAIT_WINDOW anyway, so the book keeps its size and
                    the comparison is not a selection effect wearing a timing label.
    iv_wait         within WAIT_WINDOW days, the first day ~60-DTE ATM IV falls to <= alert-day
                    IV * (1 - IV_DROP); never -> no trade.               (wait for vol to normalise)
    iv_cheap        the alert day, but ONLY when the alert did NOT arrive with an IV pop:
                    IV <= IV_POP_MAX * its own mean over the IV_BASE_WINDOW sessions BEFORE the
                    alert. Deliberately a POP measure, not a level: blunt iv_rank was already
                    tested as a global filter and rejected on its merits (A2), and the mandate
                    asks for something entry-timing-specific rather than another blanket screen.
    fade_put        the alert day, but buy the ~35-delta PUT. The literal reading of "is the
                    anti-tilt exploitable" — if the alert marks a local top, this is what should
                    make money. Included precisely because it is the tempting answer and is
                    usually wrong.

    control         random day, same name, same calendar year. The 22b placebo, rebuilt here so
                    it carries the same entry-context features as every other arm.

--------------------------------------------------------------------------------------------
PRE-COMMITTED GATE. A verdict is one of FIXED / IMPROVED-BUT-SHORT-OF-BAR / NOT SALVAGEABLE.

  E1  AN ARM IS ADOPTED only if ALL of the following hold at aggression 1.0, measured on the
      MATCHED SUBSET (alerts where both it and the signal arm produced a trade — otherwise a
      dropping arm gets credit for a selection effect):
        (a) it beats the SIGNAL arm's expectancy by >= MIN_EXPECTANCY_GAIN. Imported from
            options_backtest, where it is the standing bar for adopting any construction or
            filter change, so this session cannot quietly run an easier race than the ones
            before it;
        (b) it beats the RANDOM-ENTRY CONTROL — expectancy difference > 0 with a bootstrap CI
            excluding zero. This is the new bar 22b forces on everything downstream: beating a
            broken baseline is not evidence;
        (c) it is positive in BOTH held-out halves (2016-2020, 2021-2025);
        (d) it has >= MIN_CLOSED_PER_BUCKET closed trades;
        (e) its paired name-year advantage over the signal arm survives BH-FDR at FDR_Q across
            all arms tested. Pooled expectancy on a heavy tail is moved by single trades; the
            paired sign test is the distribution-free read and is the one that must hold.

  E2  THE MECHANISM ("the alert chases pumped IV") is CONFIRMED only if alert days show BOTH
        (a) higher entry IV than random days in the same name-year, paired, CI excluding zero,
            AND
        (b) higher trailing run-up on the same paired basis.
      One without the other is a PARTIAL confirmation and is reported as such, not rounded up.
      Each half is decided by a MAJORITY of its named proxies, not by any single one. (This was
      tightened from "any one proxy" after a three-name smoke test — explicitly labelled a smoke
      test, no verdict read off it — showed a lone proxy could carry the whole mechanism claim
      while the other three pointed the other way. The change makes the bar strictly harder and
      was made before the full run; it is recorded here rather than left as a silent edit.)

  E3  THE ANTI-TILT IS EXPLOITABLE only if `fade_put` is positive outright AND clears E1(b),
      (c) and (d). Note it is exempt from E1(a): it is a different trade, not an improvement to
      the same one, so "beat the long-call book by 10pp" is the wrong question to ask of it.

  E4  THE HEADLINE IS ALWAYS THE AGGRESSION = 1.0 NUMBER. Mid fills are a diagnostic of how much
      of any improvement is spread rather than timing, and are never the result. This matters
      more than usual here: every delayed arm enters on a DIFFERENT day with a DIFFERENT spread,
      so an apparent timing gain could be a fill gain. Entry spread is reported per arm for
      exactly that reason.

  E5  MULTIPLICITY IS PAID FOR, NOT MENTIONED. Nine arms are a search. So:
        * the Deflated Sharpe uses n_trials = the number of arms actually run;
        * arm-vs-signal p-values go through BH-FDR together;
        * and the PRIMARY out-of-sample read is CHOOSE-ON-ONE-HALF, MEASURE-ON-THE-OTHER, run in
          BOTH directions — the same holdout discipline the fundamental panel uses for theme
          changes. An arm that wins the full sample but loses the half that did not pick it has
          not been validated, however good its pooled number looks.

  E6  A DROPPING ARM (pullback, iv_wait, iv_cheap) MUST ALSO BEAT A RANDOM DROP that keeps the
      same number of trades. Removing trades at random from a heavy-tailed distribution moves
      expectancy on its own; this is arm 4 of the §2 signal gate, applied here for the same
      reason.

  E7  SAME-DAY CONTEXT GATES (CONTEXT_FILTERS) are judged by the §2 filter gate, IMPORTED and
      unchanged: threshold fitted on 2016-2020 only, applied unchanged to 2021-2025, and made to
      clear MIN_LATE_GAIN, MIN_RETAINED, MIN_TRADES, a same-sized random filter, and a positive
      early half. Their direction ("low extension and low vol are the friendly states") is fixed
      by the hypothesis before the run, not read off the data. They cost no new simulation, so
      they are the cheapest form of the mandate's IV-cheap gate — and they are counted in the
      multiplicity, not treated as free.

A clean "the timing cannot be salvaged" is a valid and valuable outcome, and is the outcome to
expect: the trade autopsy has already searched 64 entry features across 127 hypotheses on this
exact book and found ZERO survivors. Nothing here should be forced past the bars.

--------------------------------------------------------------------------------------------
WHAT THIS CANNOT SEE, and one thing it deliberately does not do.

  * The alert list is FROZEN from the signal arm's occupancy rule (one position per name at a
    time). Arms therefore share an alert set instead of each re-deriving one. A delayed entry can
    in principle overlap the previous trade in its own arm; the overlap rate is measured and
    reported rather than assumed away. Re-deriving occupancy per arm would change WHICH alerts
    fire and stop the comparison being like-for-like, which is the worse trade.
  * Entry is capped at ENTRY_END for every arm, so a delayed entry can never buy itself extra
    cached history that the baseline did not have.
  * IV here is the ~60-DTE ATM call IV — the tenor actually traded. The front-expiry `iv` field
    on the 22b rows is NOT used: it is often solved days from expiry, reads a median of 1.28-1.57
    across tiers, and no conclusion in this project should rest on it.
  * The IV series is built from the cached chain with one Black-Scholes solve per trading day.
    Days where the nearest usable quote will not solve are absent, not zero-filled.
  * Borrow, assignment and early exercise are unmodelled; `fade_put` is a long put, so none bind.
  * The control shares the universe with the real book, so both carry the same today's-liquidity
    selection bias. That is WHY the comparison is valid — the bias cancels — and it is also why
    neither book's absolute level should be read as an investable return.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import pickle
from typing import Optional

from . import options_backtest as OB
from . import options_fill as F
from . import options_universe as U
# Imported, never re-declared: the bars this session must clear are the ones the project
# already committed to elsewhere.
from .options_backtest import MIN_EXPECTANCY_GAIN
from .options_autopsy import FDR_Q, bh_fdr, deflated_sharpe
from .options_signals_v2 import LATE_START
from .options_tracker import MIN_CLOSED_PER_BUCKET, _stats

# ---- window: inherited from 22b so the two studies are directly comparable ------------------
ENTRY_START = U.ENTRY_START
ENTRY_END = U.ENTRY_END

# ---- the implied-vol series -----------------------------------------------------------------
IV_TENOR_DTE = 60          # the tenor actually traded, not the front expiry
IV_RANK_WINDOW = 252       # trailing sessions for a percentile, matching the A2 recipe
IV_BASE_WINDOW = 20        # the PRE-alert baseline the "did IV just pop" measure compares to
IV_MIN_HISTORY = 10        # sessions of prior IV needed before a pop measure means anything

# ---- the corrected-entry arms, fixed before the run ------------------------------------------
WAIT_WINDOW = 10           # trading days a corrected entry is allowed to wait
DELAYS = (3, 5, 10)
PULLBACK_PCT = 0.03        # a 3% retrace from the alert close
IV_DROP = 0.05             # IV must come in 5% from its alert-day level
IV_POP_MAX = 1.05          # alert-day IV no more than 5% above its own 20-session baseline

ARMS = ("signal", "delay3", "delay5", "delay10", "pullback", "pullback_or_w",
        "iv_wait", "iv_cheap", "fade_put")
DROPPING_ARMS = ("pullback", "iv_wait", "iv_cheap")
# `iv_cheap` buys on the ALERT DAY. On the alerts it shares with the signal arm it is therefore
# the IDENTICAL trade, and its matched difference is exactly zero by construction — E1(a) would
# be unattainable, not failed. A pure filter is judged on the POOLED book instead, with E6's
# same-sized random drop doing the work of separating a real selection from a lucky one. That is
# how the §2 signal gate judges filters, and it is the right question to ask of one.
FILTER_ARMS = ("iv_cheap",)
BOOTSTRAP_DRAWS = U.BOOTSTRAP_DRAWS
RANDOM_DROP_DRAWS = 400

# ---- the entry-context features, computed identically for every arm and the control ---------
RUNUP_LOOKBACKS = (1, 5, 21, 63)
CONTEXT_FEATURES = (
    "ret_1d", "ret_5d", "ret_21d", "ret_63d",
    "pct_from_52w_high", "ext_sma20", "ext_sma50", "up_frac_21", "run_age_63",
    "rv30", "rv10", "vol_expansion",
    "atm_iv_60d", "iv_rank_252", "iv_pop_20", "iv_vs_rv",
    "entry_spread_pct",
)
# The subset E2 is decided on. Named here so the mechanism verdict cannot be re-pointed at
# whichever feature happened to separate.
IV_MECHANISM_FEATURES = ("atm_iv_60d", "iv_rank_252", "iv_pop_20", "iv_vs_rv")
RUNUP_MECHANISM_FEATURES = ("ret_21d", "ext_sma50", "pct_from_52w_high")

# ---- same-day context gates, tested through the §2 filter gate UNCHANGED ---------------------
# These need no new simulation — they are the signal arm's own trades, screened on what was
# knowable at entry — so they are cheap, and they are the most direct form of the mandate's
# "IV-cheap entry gate". The DIRECTION is fixed by the hypothesis, not by the data: if the alert
# fires late into an extended move with pumped vol, then LOW extension and LOW vol are the
# friendly states. Each is therefore negated to satisfy the §2 higher-is-better convention and
# handed to `options_signals_v2.evaluate`, so the threshold is fitted on 2016-2020 only, applied
# unchanged to 2021-2025, and judged against the same pre-committed bars (late gain, retention,
# minimum trades, a same-sized random filter, and a positive early half) that term_slope had to
# clear. Reusing that gate rather than writing a new one is deliberate: it cannot be softened
# here without softening the one term_slope was adopted under.
CONTEXT_FILTERS = ("ret_21d", "ext_sma50", "run_age_63", "iv_pop_20", "iv_rank_252", "iv_vs_rv")

OUT_DIR = os.path.join("data", "options_entry")
IV_DIR = os.path.join(OUT_DIR, "iv_series")


def _log(m):
    print(f"[optentry] {m}", flush=True)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _median(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def _mean(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


# ================================ the daily ~60-DTE ATM IV series ===========================
def atm_iv_on(chain, spot: float, as_of: dt.date, tenor: int = IV_TENOR_DTE) -> Optional[float]:
    """ATM call IV at the ~`tenor`-DTE expiry. ONE solve, on the strike nearest the money.

    Deliberately not the front expiry. The front contract is frequently days from expiry, where
    a small mid error explodes into an implausible vol, and the 22b `iv` field — which is the
    front expiry — reads a median of 1.28-1.57 for exactly that reason. The 45-75 DTE band is
    what this strategy buys, so that is the tenor whose vol matters.
    """
    import pandas as pd

    from . import blackscholes as BS

    if chain is None or len(chain) == 0 or not spot or spot <= 0:
        return None
    exp = pd.to_datetime(chain["expiration"]).dt.date
    future = sorted({e for e in exp if e > as_of})
    if not future:
        return None
    tgt = min(future, key=lambda e: abs((e - as_of).days - tenor))
    f = chain[(exp == tgt) & (chain["right"].astype(str).str[0].str.upper() == "C")].copy()
    if not len(f):
        return None
    f["_d"] = (f["strike"].astype(float) - float(spot)).abs()
    T = (tgt - as_of).days / 365.0
    if T <= 0:
        return None
    r_free = BS.risk_free_rate(as_of)
    # Walk out a few strikes: the single nearest quote is sometimes crossed or one-sided.
    for _, row in f.sort_values("_d").head(4).iterrows():
        bid, ask = _f(row.get("bid")), _f(row.get("ask"))
        if bid is None or ask is None or ask <= 0 or ask < bid:
            continue
        v = BS.implied_vol((bid + ask) / 2.0, float(spot), float(row["strike"]), T, r_free, "C")
        if v and 0.01 < float(v) < 5.0:
            return float(v)
    return None


def build_iv_series(prov, ticker: str, bars: dict, start: str = ENTRY_START,
                    end: str = ENTRY_END, tenor: int = IV_TENOR_DTE) -> dict:
    """{date: atm_iv} across every trading day in the window. The expensive pass, done once.

    Uses raw (as-traded) closes as the spot, because strikes are never retro-adjusted — the
    split trap that silently broke ATM IV on every pre-split date the first time round.
    """
    px = bars.get("raw_close") or bars["close"]
    out = {}
    for i, d in enumerate(bars["date"]):
        if not (start <= d <= end):
            continue
        spot = _f(px[i])
        if spot is None or spot <= 0:
            continue
        day = dt.date.fromisoformat(d)
        chain = prov.chain_on(ticker, day)
        if chain is None or len(chain) == 0:
            continue
        v = atm_iv_on(chain, spot, day, tenor)
        if v is not None:
            out[d] = v
    return out


def iv_series_path(ticker: str, out_dir: str = IV_DIR) -> str:
    return os.path.join(out_dir, f"{ticker.upper()}.pkl")


def load_iv_series(ticker: str, out_dir: str = IV_DIR) -> dict:
    p = iv_series_path(ticker, out_dir)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "rb") as f:
            return pickle.load(f)
    except (OSError, pickle.UnpicklingError):
        return {}


def save_iv_series(ticker: str, series: dict, out_dir: str = IV_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    p = iv_series_path(ticker, out_dir)
    tmp = p + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(series, f, protocol=5)
    os.replace(tmp, p)
    return p


# ================================ entry context =============================================
def iv_features(series: dict, dates: list, as_of: str) -> dict:
    """IV level, rank and POP as of `as_of`, using STRICTLY PRIOR days for both windows.

    Including the day's own value in its own percentile leaks the observation into its baseline —
    the bug A2 had to fix before iv_rank could be tested at all.
    """
    out = {}
    v = series.get(as_of)
    if v is None:
        return out
    out["atm_iv_60d"] = v
    prior = [series[d] for d in dates if d < as_of and d in series]
    if len(prior) >= 60:
        w = prior[-IV_RANK_WINDOW:]
        out["iv_rank_252"] = sum(1 for x in w if x < v) / len(w)
    if len(prior) >= IV_MIN_HISTORY:
        base = _mean(prior[-IV_BASE_WINDOW:])
        if base and base > 0:
            out["iv_pop_20"] = v / base
    return out


def bar_features(bars: dict, as_of: str) -> dict:
    """Run-up, extension and realised vol from ADJUSTED closes — a split is not a move."""
    w = OB.bars_asof(bars, as_of)
    if not w:
        return {}
    c = [x for x in w["close"] if x and x > 0]
    if len(c) < 70:
        return {}
    out = {}
    for n in RUNUP_LOOKBACKS:
        if len(c) > n and c[-1 - n] > 0:
            out[f"ret_{n}d"] = c[-1] / c[-1 - n] - 1.0
    hi = max(c[-min(len(c), 252):])
    if hi > 0:
        out["pct_from_52w_high"] = c[-1] / hi - 1.0
    for n in (20, 50):
        m = _mean(c[-n:])
        if m:
            out[f"ext_sma{n}"] = c[-1] / m - 1.0
    last21 = c[-22:]
    if len(last21) >= 22:
        out["up_frac_21"] = sum(1 for i in range(1, len(last21))
                                if last21[i] > last21[i - 1]) / (len(last21) - 1)
    # How far INTO the move the entry sits: sessions since the trailing 63-day low. A big
    # number means the run is old and the alert is late to it.
    tail = c[-63:]
    if len(tail) >= 20:
        out["run_age_63"] = float(len(tail) - 1 - tail.index(min(tail)))
    rv30 = U._realized_vol(c, 30)
    rv10 = U._realized_vol(c, 10)
    if rv30:
        out["rv30"] = rv30
    if rv10:
        out["rv10"] = rv10
    if rv30 and rv10 and rv30 > 0:
        out["vol_expansion"] = rv10 / rv30
    return out


def entry_context(bars: dict, series: dict, dates: list, as_of: str) -> dict:
    """Everything known about the entry day BEFORE the trade — the alert-vs-random comparison."""
    ctx = bar_features(bars, as_of)
    ctx.update(iv_features(series, dates, as_of))
    iv, rv = ctx.get("atm_iv_60d"), ctx.get("rv30")
    if iv and rv and rv > 0:
        ctx["iv_vs_rv"] = iv / rv
    return ctx


def annotate(rows: list, bars: dict, series: dict) -> int:
    """Attach `ctx_*` features to a banked book in place. Returns how many got a context."""
    dates = sorted(series)
    n = 0
    for r in rows:
        d = str(r.get("alert_ts"))[:10]
        ctx = entry_context(bars, series, dates, d)
        if not ctx:
            continue
        for k, v in ctx.items():
            r[f"ctx_{k}"] = v
        if r.get("entry_spread_pct") is not None:
            r["ctx_entry_spread_pct"] = r["entry_spread_pct"]
        n += 1
    return n


# ================================ paired name-year statistics ===============================
def _cell(r):
    return (str(r.get("ticker") or "?"), str(r.get("alert_ts"))[:4])


def paired_cells(a_rows, b_rows, key: str = "pnl_pct") -> dict:
    """Mean(`key`) per (name, year) in A minus the same cell in B.

    The unit of comparison this study leans on. Pooled expectancy on a heavy tail is moved by
    single trades and by however many trades each name happens to contribute; a paired cell
    average removes both, and the SIGN TEST on the cells is distribution-free — it does not care
    that options returns are skewed, which the t-statistic very much does.
    """
    import statistics as st

    def group(rs):
        g = {}
        for r in rs:
            v = _f(r.get(key))
            if v is not None:
                g.setdefault(_cell(r), []).append(v)
        return g

    ga, gb = group(a_rows), group(b_rows)
    both = sorted(set(ga) & set(gb))
    if len(both) < 10:
        return {"ok": False, "reason": f"only {len(both)} paired cells", "n_cells": len(both)}
    diffs = [st.mean(ga[c]) - st.mean(gb[c]) for c in both]
    n = len(diffs)
    mean = st.mean(diffs)
    sd = st.stdev(diffs) if n > 1 else None
    t = (mean / (sd / math.sqrt(n))) if sd and sd > 0 else None
    wins = sum(1 for d in diffs if d > 0)
    ties = sum(1 for d in diffs if d == 0)
    eff = n - ties
    z = ((wins - eff / 2) / (math.sqrt(eff) / 2)) if eff > 0 else None
    return {"ok": True, "n_cells": n, "mean_diff": mean, "median_diff": st.median(diffs),
            "t": t, "win_rate": wins / n, "n_wins": wins, "sign_z": z,
            "p_sign": _two_sided_p(z) if z is not None else None,
            "note": "paired by (ticker, calendar year); the sign test is the primary read and "
                    "the t is reported for continuity with earlier sessions."}


def _two_sided_p(z: float) -> float:
    return math.erfc(abs(float(z)) / math.sqrt(2.0))


def bootstrap_expectancy_diff(a_rows, b_rows, seed: int = 0,
                              draws: int = BOOTSTRAP_DRAWS) -> dict:
    return U.bootstrap_diff(a_rows, b_rows, "expectancy_pct", draws=draws, seed=seed)


# ================================ alert list + the arms =====================================
def simulate_on(prov, ticker: str, bars: dict, day_str: str, right: str,
                aggression: float, memo: Optional[dict] = None):
    """(contract, trade) for one name on one day — memoised per name.

    Nine arms over one alert list land on the same day-and-right constantly: `iv_cheap` always
    coincides with `signal`, `pullback` with `pullback_or_w` whenever the pullback hits, and the
    delays collide with each other. The pick and the simulation are deterministic given the day
    and the right, so a memo removes roughly a third of the work and can change nothing.
    """
    key = (day_str, right)
    if memo is not None and key in memo:
        return memo[key]
    got = None
    w = OB.bars_asof(bars, day_str)
    if w:
        day = dt.date.fromisoformat(day_str)
        chain = prov.chain_on(ticker, day)
        if chain is not None and len(chain):
            row = OB.pick_contract(chain, w["close"][-1], day, right=right)
            if row is None:
                got = ("no_contract_in_band", None)
            else:
                tr = OB.simulate_trade(prov, ticker, row, day, bars, aggression=aggression)
                got = ((row, tr) if tr and tr.get("ok")
                       else ((tr or {}).get("reason", "sim_failed"), None))
        else:
            got = ("no_chain", None)
    else:
        got = ("no_bar_window", None)
    if memo is not None:
        memo[key] = got
    return got


def alerts_for_name(prov, ticker: str, bars: dict, caps: dict,
                    start: str = ENTRY_START, end: str = ENTRY_END,
                    aggression: float = F.DEFAULT_AGGRESSION,
                    memo: Optional[dict] = None) -> dict:
    """The signal arm, plus the frozen alert list every other arm is applied to.

    This is `options_universe.run_name` with the alert days retained even when the baseline
    could not open a trade — an alert whose contract was unfillable on the alert day may well be
    fillable three days later, and dropping it here would quietly hand the delayed arms an
    easier alert set than the baseline had.
    """
    from valuation.intraday.signals import evaluate as sig_evaluate
    from valuation.intraday.technical import technical_signals
    from valuation.saas.notify import _BULL

    rows, alerts, rejects = [], [], {}
    n_cand = 0
    open_until = None
    for d in bars["date"]:
        if not (start <= d <= end):
            continue
        if open_until and d <= open_until:
            continue
        w = OB.bars_asof(bars, d)
        if not w:
            continue
        ts = technical_signals(w).get("score")
        if ts is None or ts < OB.PREFILTER_TECH:
            continue
        n_cand += 1
        day = dt.date.fromisoformat(d)
        chain = prov.chain_on(ticker, day)
        if chain is None or len(chain) == 0:
            rejects["no_chain"] = rejects.get("no_chain", 0) + 1
            continue
        und = w["close"][-1]
        summ = OB.chain_summary(chain, und, day)
        ev = sig_evaluate(w, summ, horizon=OB.HORIZON)
        sc, labels = ev.get("score"), ev.get("labels") or []
        if sc is None or sc < OB.ALERT_MIN_SCORE:
            continue
        if not any(any(bl in l for bl in _BULL) for l in labels):
            continue
        alerts.append({"date": d, "score": sc, "labels": labels})
        row, tr = simulate_on(prov, ticker, bars, d, "C", aggression, memo)
        if tr is None:
            rejects[str(row)] = rejects.get(str(row), 0) + 1
            continue
        r = _row(ticker, day, row, tr, sc, labels, caps, "signal", d)
        r["entry_rule"] = "alert_day"
        r["entry_lag_sessions"] = 0
        rows.append(r)
        open_until = tr.get("exit_date")
    return {"ticker": ticker, "alerts": alerts, "signal_rows": rows,
            "n_cand": n_cand, "n_alert": len(alerts), "rejects": rejects}


def _row(ticker, day, contract, trade, score, labels, caps, arm, alert_date) -> dict:
    r = OB.to_alert_row(ticker, day, contract, trade, score, labels, None, None)
    r["entry_spread_pct"] = trade.get("entry_spread_pct")
    r["settled_at_intrinsic"] = trade.get("settled_at_intrinsic")
    mc = U.cap_at(caps or {}, ticker, day.isoformat())
    r["marketcap_musd"] = mc
    r["cap_tier"] = U.tier_of(mc)
    r["arm"] = arm
    # The ALERT day, kept separately from the entry day. Every paired comparison keys on the
    # alert so a delayed arm is matched to the alert it came from, not to the day it bought.
    r["alert_date"] = alert_date
    r["entry_date"] = day.isoformat()
    r["entry_lag_sessions"] = None
    return r


def arm_entry_day(arm: str, bars: dict, series: dict, dates: list, alert_date: str,
                  end: str = ENTRY_END) -> dict:
    """Which day does this arm buy on? Returns {'date': str|None, 'reason': str, 'lag': int}.

    Forward-looking ONLY within the alert's own wait window, and only on information that would
    have been available on the day it acts: a pullback arm sees each day's close as it arrives,
    an IV arm sees each day's IV as it arrives. Nothing consults the outcome.
    """
    ds = bars["date"]
    try:
        i0 = ds.index(alert_date)
    except ValueError:
        return {"date": None, "reason": "alert_day_not_in_bars", "lag": None}
    px = bars["close"]                       # adjusted: a split is not a pullback

    def ok(j):
        return 0 <= j < len(ds) and ds[j] <= end

    if arm == "signal" or arm == "fade_put":
        return {"date": alert_date, "reason": "alert_day", "lag": 0}

    if arm.startswith("delay"):
        n = int(arm[5:])
        j = i0 + n
        if not ok(j):
            return {"date": None, "reason": "past_window", "lag": None}
        return {"date": ds[j], "reason": f"delay{n}", "lag": n}

    if arm in ("pullback", "pullback_or_w"):
        ref = _f(px[i0])
        if ref is None or ref <= 0:
            return {"date": None, "reason": "no_reference_close", "lag": None}
        for k in range(1, WAIT_WINDOW + 1):
            j = i0 + k
            if not ok(j):
                return {"date": None, "reason": "past_window", "lag": None}
            v = _f(px[j])
            if v is not None and v <= ref * (1.0 - PULLBACK_PCT):
                return {"date": ds[j], "reason": "pullback_hit", "lag": k}
        if arm == "pullback_or_w":
            j = i0 + WAIT_WINDOW
            if not ok(j):
                return {"date": None, "reason": "past_window", "lag": None}
            return {"date": ds[j], "reason": "no_pullback_entered_anyway", "lag": WAIT_WINDOW}
        return {"date": None, "reason": "no_pullback", "lag": None}

    if arm == "iv_wait":
        iv0 = series.get(alert_date)
        if iv0 is None:
            return {"date": None, "reason": "no_alert_day_iv", "lag": None}
        for k in range(1, WAIT_WINDOW + 1):
            j = i0 + k
            if not ok(j):
                return {"date": None, "reason": "past_window", "lag": None}
            v = series.get(ds[j])
            if v is not None and v <= iv0 * (1.0 - IV_DROP):
                return {"date": ds[j], "reason": "iv_normalised", "lag": k}
        return {"date": None, "reason": "iv_never_normalised", "lag": None}

    if arm == "iv_cheap":
        f = iv_features(series, dates, alert_date)
        pop = f.get("iv_pop_20")
        if pop is None:
            return {"date": None, "reason": "no_iv_baseline", "lag": None}
        if pop > IV_POP_MAX:
            return {"date": None, "reason": "iv_popped", "lag": None}
        return {"date": alert_date, "reason": "iv_not_popped", "lag": 0}

    return {"date": None, "reason": f"unknown_arm:{arm}", "lag": None}


def run_arms(prov, ticker: str, bars: dict, series: dict, alerts: list, caps: dict,
             arms=ARMS, aggression: float = F.DEFAULT_AGGRESSION,
             end: str = ENTRY_END, memo: Optional[dict] = None) -> dict:
    """Every arm, over the SAME frozen alert list. One contract pick + one simulation per arm."""
    dates = sorted(series)
    memo = {} if memo is None else memo
    out = {a: [] for a in arms}
    why = {a: {} for a in arms}
    overlap = {a: 0 for a in arms}
    last_exit = {a: None for a in arms}
    for al in alerts:
        ad = al["date"]
        for arm in arms:
            sel = arm_entry_day(arm, bars, series, dates, ad, end=end)
            d = sel["date"]
            if d is None:
                why[arm][sel["reason"]] = why[arm].get(sel["reason"], 0) + 1
                continue
            right = "P" if arm == "fade_put" else "C"
            row, tr = simulate_on(prov, ticker, bars, d, right, aggression, memo)
            if tr is None:
                why[arm][str(row)] = why[arm].get(str(row), 0) + 1
                continue
            day = dt.date.fromisoformat(d)
            r = _row(ticker, day, row, tr, al.get("score"), al.get("labels"), caps, arm, ad)
            r["entry_lag_sessions"] = sel["lag"]
            r["entry_rule"] = sel["reason"]
            # Occupancy is frozen from the signal arm, so a delayed arm can in principle enter
            # while its own previous trade is still open. Counted, never hidden.
            if last_exit[arm] and d <= last_exit[arm]:
                overlap[arm] += 1
                r["overlapped_previous"] = True
            last_exit[arm] = tr.get("exit_date")
            out[arm].append(r)
    return {"ticker": ticker, "arms": out, "no_entry": why, "overlaps": overlap}


def random_entry_control(prov, ticker: str, bars: dict, alerts: list, caps: dict,
                         draws: int = 2, seed: int = 0,
                         aggression: float = F.DEFAULT_AGGRESSION,
                         end: str = ENTRY_END, memo: Optional[dict] = None) -> list:
    """The 22b placebo, rebuilt against the frozen alert list so it matches the arms exactly."""
    import random

    rnd = random.Random(f"{seed}:{ticker}")
    by_year = {}
    for d in bars["date"]:
        if ENTRY_START <= d <= end:
            by_year.setdefault(d[:4], []).append(d)
    out = []
    for al in alerts:
        pool = by_year.get(al["date"][:4]) or []
        if len(pool) < 20:
            continue
        for _ in range(draws):
            d = pool[rnd.randrange(len(pool))]
            row, tr = simulate_on(prov, ticker, bars, d, "C", aggression, memo)
            if tr is None:
                continue
            r = _row(ticker, dt.date.fromisoformat(d), row, tr, None, [], caps, "control",
                     al["date"])
            r["entry_rule"] = "random_day"
            out.append(r)
    return out


# ================================ mechanism (E2) ============================================
def characterize(real_rows, ctrl_rows, seed: int = 0,
                 features=CONTEXT_FEATURES) -> dict:
    """Alert days vs random days on every entry-context feature. Test 1 of the mandate.

    Both a pooled comparison (medians, for readability) and the PAIRED name-year one (which is
    what the verdict uses). Pooling across names would mostly measure which names alert often.
    """
    out = {}
    for feat in features:
        k = f"ctx_{feat}"
        a = [r for r in real_rows if _f(r.get(k)) is not None]
        b = [r for r in ctrl_rows if _f(r.get(k)) is not None]
        if len(a) < MIN_CLOSED_PER_BUCKET or len(b) < MIN_CLOSED_PER_BUCKET:
            out[feat] = {"ok": False, "reason": "coverage", "n_real": len(a), "n_ctrl": len(b)}
            continue
        pr = paired_cells(a, b, key=k)
        out[feat] = {
            "ok": True,
            "coverage_real": len(a) / len(real_rows) if real_rows else None,
            "coverage_ctrl": len(b) / len(ctrl_rows) if ctrl_rows else None,
            "median_alert": _median([_f(r.get(k)) for r in a]),
            "median_random": _median([_f(r.get(k)) for r in b]),
            "mean_alert": _mean([_f(r.get(k)) for r in a]),
            "mean_random": _mean([_f(r.get(k)) for r in b]),
            "paired": pr,
        }
    return out


def mechanism_verdict(chars: dict) -> dict:
    """E2, applied mechanically. IV richer AND tape more extended, or it is not the mechanism."""
    def fired(names, direction=1):
        hits = []
        for f in names:
            d = chars.get(f) or {}
            p = (d.get("paired") or {})
            if not (d.get("ok") and p.get("ok")):
                continue
            md, z = p.get("mean_diff"), p.get("sign_z")
            if md is None or z is None:
                continue
            # "Alert days are higher" = positive mean diff and a sign test that agrees at 5%.
            if md * direction > 0 and abs(z) >= 1.96 and (z * direction) > 0:
                hits.append(f)
        return hits

    iv_hits = fired(IV_MECHANISM_FEATURES)
    run_hits = fired(RUNUP_MECHANISM_FEATURES)
    # A MAJORITY of each group, not any single proxy: with four IV measures and three run-up
    # measures, "one of them fired" is a cherry-pick dressed as a mechanism.
    iv_ok = len(iv_hits) * 2 >= len(IV_MECHANISM_FEATURES)
    run_ok = len(run_hits) * 2 >= len(RUNUP_MECHANISM_FEATURES)
    both = bool(iv_ok and run_ok)
    if both:
        label = "CONFIRMED"
    elif iv_ok or run_ok:
        label = "PARTIAL"
    else:
        label = "REJECTED"
    return {"iv_features_confirming": iv_hits, "runup_features_confirming": run_hits,
            "iv_half_confirmed": iv_ok, "runup_half_confirmed": run_ok,
            "E2_mechanism": both, "label": label,
            "note": "each half needs a MAJORITY of its named proxies, each with a positive "
                    "paired name-year difference AND a sign test agreeing at 5%."}


# ================================ is the tilt itself stable? ================================
def control_stability(signal_rows, ctrl_rows) -> dict:
    """Does the alert lose to a random day in BOTH halves, and in every tier?

    The whole session rests on the -5.24 being a property of the signal rather than of one
    period. If the alert only underperforms in, say, 2021-2025, the honest statement is that the
    strategy decayed — which this project already knows — not that entry timing is anti-predictive.
    """
    out = {}
    for lbl, pred in (("early", lambda d: d < LATE_START), ("late", lambda d: d >= LATE_START)):
        a = [r for r in signal_rows if pred(str(r.get("alert_date")
                                                or r.get("alert_ts"))[:10])]
        b = [r for r in ctrl_rows if pred(str(r.get("alert_date")
                                              or r.get("alert_ts"))[:10])]
        if len(a) < MIN_CLOSED_PER_BUCKET or len(b) < MIN_CLOSED_PER_BUCKET:
            out[lbl] = {"ok": False, "n_signal": len(a), "n_control": len(b)}
            continue
        out[lbl] = {"ok": True, "n_signal": len(a), "n_control": len(b),
                    "signal_expectancy": _stats(a)["expectancy_pct"],
                    "control_expectancy": _stats(b)["expectancy_pct"],
                    "diff": (_stats(a)["expectancy_pct"] or 0) - (_stats(b)["expectancy_pct"] or 0),
                    "paired": paired_cells(a, b)}
    tiers = {}
    for t in U.TIER_ORDER:
        a = [r for r in signal_rows if r.get("cap_tier") == t]
        b = [r for r in ctrl_rows if r.get("cap_tier") == t]
        if len(a) >= MIN_CLOSED_PER_BUCKET and len(b) >= MIN_CLOSED_PER_BUCKET:
            tiers[t] = {"n_signal": len(a), "n_control": len(b),
                        "diff": ((_stats(a)["expectancy_pct"] or 0)
                                 - (_stats(b)["expectancy_pct"] or 0)),
                        "paired": paired_cells(a, b)}
    halves = [v for v in out.values() if v.get("ok")]
    return {"by_half": out, "by_tier": tiers,
            "negative_in_both_halves": bool(len(halves) == 2
                                            and all((v["diff"] or 0) < 0 for v in halves)),
            "note": "a tilt that lives in one half is a decaying strategy, not an "
                    "anti-predictive signal."}


def tilt_decomposition(signal_rows, ctrl_rows, n_bands: int = 4) -> dict:
    """WHERE the alert loses to random: by score band, by trailing run-up, by which labels fired.

    This is the decomposition 22b's handoff named as the cheap next test — is the damage in the
    technical run-up requirement or in the options-flow half of the score? Both are reported;
    neither is a filter until it clears a gate.
    """
    out = {}

    def band_table(rows, key, label):
        vals = sorted(v for v in (_f(r.get(key)) for r in rows) if v is not None)
        if len(vals) < n_bands * MIN_CLOSED_PER_BUCKET:
            return {"ok": False, "reason": "coverage", "n": len(vals)}
        cuts = [vals[int(len(vals) * i / n_bands)] for i in range(1, n_bands)]

        def which(v):
            for i, c in enumerate(cuts):
                if v < c:
                    return i
            return n_bands - 1

        groups = {}
        for r in rows:
            v = _f(r.get(key))
            if v is not None:
                groups.setdefault(which(v), []).append(r)
        return {"ok": True, "label": label, "cuts": cuts,
                "bands": {str(i): {"n": len(rs),
                                   "expectancy_pct": _stats(rs)["expectancy_pct"],
                                   "median_feature": _median([_f(r.get(key)) for r in rs])}
                          for i, rs in sorted(groups.items())}}

    out["by_score"] = band_table(signal_rows, "score", "alert score")
    out["by_runup_21d"] = band_table(signal_rows, "ctx_ret_21d", "trailing 21d return")
    out["by_iv_pop"] = band_table(signal_rows, "ctx_iv_pop_20", "IV vs its 20d baseline")
    # The control has no score, so a like-for-like band comparison is only possible on the
    # context features, which both books carry.
    for key in ("ctx_ret_21d", "ctx_iv_pop_20"):
        a = band_table(signal_rows, key, key)
        b = band_table(ctrl_rows, key, key)
        if a.get("ok") and b.get("ok"):
            out[f"{key}_vs_control"] = {
                str(i): {"signal": a["bands"].get(str(i), {}).get("expectancy_pct"),
                         "control": b["bands"].get(str(i), {}).get("expectancy_pct"),
                         "diff": ((a["bands"].get(str(i), {}).get("expectancy_pct") or 0)
                                  - (b["bands"].get(str(i), {}).get("expectancy_pct") or 0))}
                for i in range(n_bands)}
    labels = {}
    for r in signal_rows:
        for l in (r.get("labels") or []):
            # Live labels embed their own reading — "Call-heavy flow (P/C 0.23)", "Volume surge
            # 1.7x" — so keying on the raw string splits ONE label into sixty buckets of ~40
            # trades each and every one of them looks like a signal. Group on the label itself.
            labels.setdefault(_label_family(str(l)), []).append(r)
    out["by_label"] = {l: {"n": len(rs), "expectancy_pct": _stats(rs)["expectancy_pct"],
                           "p_tail_win": U.tail_stats(rs)["p_tail_win"]}
                       for l, rs in sorted(labels.items())
                       if len(rs) >= MIN_CLOSED_PER_BUCKET}
    return out


def _label_family(label: str) -> str:
    """'Call-heavy flow (P/C 0.23)' -> 'Call-heavy flow'; 'Volume surge 1.7x' -> 'Volume surge'."""
    import re

    s = re.sub(r"\s*\([^)]*\)", "", str(label))
    s = re.sub(r"\s+[\d.]+x?$", "", s)
    return s.strip()


def context_filters(signal_rows, filters=CONTEXT_FILTERS, seed: int = 0) -> dict:
    """Same-day entry gates through the §2 filter gate, UNCHANGED. See CONTEXT_FILTERS."""
    from . import options_signals_v2 as S2

    rows = [dict(r) for r in signal_rows]
    for r in rows:
        for feat in filters:
            v = _f(r.get(f"ctx_{feat}"))
            # Negated so "cheap / unextended is good" satisfies the gate's higher-is-better
            # convention — the same transform §2 applies to vrp, for the same reason.
            r[f"neg_{feat}"] = (-v) if v is not None else None
    out = {}
    for feat in filters:
        res = S2.evaluate(rows, f"neg_{feat}", seed=seed)
        res["feature"] = feat
        res["direction"] = "low is good (negated for the gate's higher-is-better convention)"
        out[feat] = res
    return out


# ================================ arm evaluation (E1, E6) ===================================
def matched(a_rows, b_rows) -> tuple:
    """Both books restricted to the alerts they BOTH traded — keyed on (ticker, alert_date).

    Without this, a dropping arm is compared against a baseline that includes the very alerts it
    declined, so the comparison rewards the selection and calls it timing.
    """
    def key(r):
        return (str(r.get("ticker")), str(r.get("alert_date") or r.get("alert_ts"))[:10])

    ka = {key(r) for r in a_rows}
    kb = {key(r) for r in b_rows}
    both = ka & kb
    return ([r for r in a_rows if key(r) in both],
            [r for r in b_rows if key(r) in both])


def random_drop_control(base_rows, keep_n: int, seed: int = 0,
                        draws: int = RANDOM_DROP_DRAWS) -> Optional[float]:
    """Mean expectancy of `draws` random subsets of size keep_n. E6's benchmark."""
    import random

    if not base_rows or keep_n <= 0 or keep_n > len(base_rows):
        return None
    rnd = random.Random(seed)
    vals = []
    for _ in range(draws):
        s = rnd.sample(base_rows, keep_n)
        v = _stats(s)["expectancy_pct"]
        if v is not None:
            vals.append(v)
    return _mean(vals)


def arm_report(arm: str, arm_rows, signal_rows, ctrl_rows, seed: int = 0) -> dict:
    """One arm, against BOTH baselines, pooled and matched, with the paired tests."""
    d = {"arm": arm, "n": len(arm_rows), "stats": U.tail_stats(arm_rows),
         "held_out": U.held_out(arm_rows), "by_year": U.by_year(arm_rows),
         "median_entry_spread_pct": _median([_f(r.get("entry_spread_pct")) for r in arm_rows]),
         "median_entry_lag": _median([_f(r.get("entry_lag_sessions")) for r in arm_rows]),
         "n_overlapped": sum(1 for r in arm_rows if r.get("overlapped_previous")),
         "entry_rules": {}}
    for r in arm_rows:
        k = str(r.get("entry_rule") or "?")
        d["entry_rules"][k] = d["entry_rules"].get(k, 0) + 1

    ma, ms = matched(arm_rows, signal_rows)
    d["vs_signal_matched"] = {
        "n_matched": len(ma),
        "arm": U.tail_stats(ma), "signal": U.tail_stats(ms),
        "expectancy_diff": ((_stats(ma)["expectancy_pct"] or 0)
                            - (_stats(ms)["expectancy_pct"] or 0)) if ma and ms else None,
        "bootstrap": bootstrap_expectancy_diff(ma, ms, seed=seed) if ma and ms else None,
        "paired": paired_cells(ma, ms) if ma and ms else None,
    }
    d["vs_signal_pooled"] = {
        "expectancy_diff": ((_stats(arm_rows)["expectancy_pct"] or 0)
                            - (_stats(signal_rows)["expectancy_pct"] or 0))
        if arm_rows and signal_rows else None,
        "paired": paired_cells(arm_rows, signal_rows) if arm_rows and signal_rows else None,
    }
    if ctrl_rows:
        d["vs_control"] = {
            "control": U.tail_stats(ctrl_rows),
            "bootstrap": bootstrap_expectancy_diff(arm_rows, ctrl_rows, seed=seed),
            "paired": paired_cells(arm_rows, ctrl_rows),
        }
    if arm in DROPPING_ARMS and signal_rows:
        # The benchmark must be drawn from the FULL signal book. Sampling from the matched
        # subset would draw len(ma) trades out of len(ma) and "drop" nothing at all.
        keep = min(len(arm_rows), len(signal_rows))
        rc = random_drop_control(signal_rows, keep, seed=seed)
        d["random_drop_control"] = {
            "keep_n": keep, "n_signal_pool": len(signal_rows), "random_expectancy": rc,
            "arm_expectancy": _stats(arm_rows)["expectancy_pct"] if arm_rows else None,
            "beats_random_drop": bool(rc is not None and arm_rows
                                      and (_stats(arm_rows)["expectancy_pct"] or 0) > rc),
            "note": "E6 — dropping trades at random from a heavy tail moves expectancy on its "
                    "own, so a selective arm must beat a same-sized random drop of the signal "
                    "book.",
        }
    return d


def arm_gate(rep: dict, arm: str, p_adjusted: Optional[bool] = None) -> dict:
    """E1 (or E3 for fade_put), applied mechanically to one arm's report."""
    ms = rep.get("vs_signal_matched") or {}
    arm_stats = ms.get("arm") or {}
    # A pure filter enters on the alert day, so its matched difference is zero by construction;
    # the pooled difference is the only one that carries any information about it. See
    # FILTER_ARMS. Every other arm is judged matched, where the selection cannot flatter it.
    diff = (rep.get("vs_signal_pooled") or {}).get("expectancy_diff") if arm in FILTER_ARMS \
        else ms.get("expectancy_diff")
    bt = rep.get("vs_control") or {}
    bc = bt.get("bootstrap") or {}
    ho = rep.get("held_out") or {}
    n = rep.get("n") or 0

    beats_signal = bool(diff is not None and diff >= MIN_EXPECTANCY_GAIN)
    beats_ctrl = bool(bc.get("ok") and (bc.get("diff") or 0) > 0 and bc.get("excludes_zero"))
    both_halves = bool(ho.get("both_positive"))
    enough = bool(n >= MIN_CLOSED_PER_BUCKET)
    paired_ok = bool(p_adjusted) if p_adjusted is not None else None

    if arm == "fade_put":
        positive = bool((arm_stats.get("expectancy_pct") or (rep.get("stats") or {})
                         .get("expectancy_pct") or 0) > 0)
        passed = bool(positive and beats_ctrl and both_halves and enough)
        return {"gate": "E3", "positive": positive, "beats_control": beats_ctrl,
                "both_halves_positive": both_halves, "enough_trades": enough,
                "passed": passed,
                "note": "exempt from E1(a): a long put is a different trade, not an improved "
                        "version of the long call."}
    passed = bool(beats_signal and beats_ctrl and both_halves and enough
                  and (paired_ok is not False))
    d = rep.get("random_drop_control")
    if d is not None:
        passed = bool(passed and d.get("beats_random_drop"))
    return {"gate": "E1", "beats_signal_by_bar": beats_signal,
            "basis": "pooled" if arm in FILTER_ARMS else "matched",
            "expectancy_gain_vs_signal": diff, "bar": MIN_EXPECTANCY_GAIN,
            "beats_control": beats_ctrl, "both_halves_positive": both_halves,
            "enough_trades": enough, "paired_survives_fdr": paired_ok,
            "beats_random_drop": (d or {}).get("beats_random_drop"),
            "passed": passed}


# ================================ the primary OOS read (E5) =================================
def holdout_arm_select(arms_rows: dict, signal_rows, ctrl_rows) -> dict:
    """Choose the best arm on ONE half, then measure it on the OTHER. Both directions.

    With nine arms on a heavy tail, the best full-sample arm is partly the luckiest arm. This is
    the only read here that is not contaminated by that, and it is the one the verdict leans on.
    It is the same holdout discipline `holdout_theme_validate` applies to the fundamental panel.
    """
    def half(rows, which):
        return [r for r in rows
                if (str(r.get("alert_date") or r.get("alert_ts"))[:10] < LATE_START)
                == (which == "early")]

    out = {}
    for decide, measure in (("early", "late"), ("late", "early")):
        scores = {}
        for arm, rows in arms_rows.items():
            if arm == "signal":
                continue
            dh = half(rows, decide)
            if len(dh) < MIN_CLOSED_PER_BUCKET:
                continue
            sig_d = half(signal_rows, decide)
            ma, ms = matched(dh, sig_d)
            if len(ma) < MIN_CLOSED_PER_BUCKET:
                continue
            scores[arm] = (_stats(ma)["expectancy_pct"] or 0) - (_stats(ms)["expectancy_pct"] or 0)
        if not scores:
            out[f"decide_{decide}"] = {"ok": False, "reason": "no arm has enough trades"}
            continue
        best = max(scores, key=lambda a: scores[a])
        mh = half(arms_rows[best], measure)
        sig_m = half(signal_rows, measure)
        ma, ms = matched(mh, sig_m)
        ctl = half(ctrl_rows, measure) if ctrl_rows else []
        out[f"decide_{decide}"] = {
            "ok": True, "chosen_arm": best,
            "gain_on_decide_half": scores[best],
            "ranking_on_decide_half": dict(sorted(scores.items(), key=lambda kv: -kv[1])),
            "measure_half": measure, "n_measured": len(ma),
            "arm_expectancy": _stats(ma)["expectancy_pct"] if ma else None,
            "signal_expectancy": _stats(ms)["expectancy_pct"] if ms else None,
            "gain_on_measure_half": ((_stats(ma)["expectancy_pct"] or 0)
                                     - (_stats(ms)["expectancy_pct"] or 0)) if ma and ms else None,
            "control_expectancy": _stats(ctl)["expectancy_pct"] if ctl else None,
            "beats_control_on_measure_half": bool(
                ma and ctl and (_stats(ma)["expectancy_pct"] or 0)
                > (_stats(ctl)["expectancy_pct"] or 0)),
            "paired_vs_signal_on_measure_half": paired_cells(ma, ms) if ma and ms else None,
        }
    both = [v for v in out.values() if v.get("ok")]
    out["survives_both_directions"] = bool(
        len(both) == 2 and all((v.get("gain_on_measure_half") or 0) > 0
                               and v.get("beats_control_on_measure_half") for v in both))
    out["note"] = ("the arm is CHOSEN on the half it is not judged on; a positive gain on the "
                   "measure half in both directions is the only unconditioned evidence here.")
    return out


# ================================ the verdict ===============================================
def verdict(arm_reports: dict, gates: dict, mech: dict, holdout: dict,
            cfilters: Optional[dict] = None) -> dict:
    adopted = [a for a, g in gates.items() if g.get("passed") and a != "fade_put"]
    improved = [a for a, g in gates.items()
                if a != "fade_put" and not g.get("passed")
                and (g.get("expectancy_gain_vs_signal") or 0) > 0
                and g.get("beats_control")]
    passed_filters = sorted(f for f, d in (cfilters or {}).items() if d.get("passed"))
    fade = gates.get("fade_put") or {}
    if adopted and holdout.get("survives_both_directions"):
        label = "FIXED"
    elif adopted or improved or fade.get("passed") or passed_filters:
        label = "IMPROVED-BUT-SHORT-OF-BAR"
    else:
        label = "NOT SALVAGEABLE"
    return {"label": label,
            "E1_adopted_arms": adopted,
            "context_filters_passing_the_section2_gate": passed_filters,
            "arms_beating_both_baselines_below_bar": improved,
            "E2_mechanism": mech.get("label"),
            "E3_anti_tilt_exploitable": bool(fade.get("passed")),
            "E5_holdout_survives_both_directions": bool(
                holdout.get("survives_both_directions")),
            "note": "FIXED requires an adopted arm that ALSO survives choose-on-one-half / "
                    "measure-on-the-other in both directions. Anything less is reported as an "
                    "improvement short of the bar, never as a fix."}


# ================================ orchestration =============================================
def analyse(arms_rows: dict, ctrl_rows: list, meta: Optional[dict] = None,
            seed: int = 0) -> dict:
    """Everything the mandate asks for, from the banked arm books."""
    signal_rows = arms_rows.get("signal") or []
    chars = characterize(signal_rows, ctrl_rows, seed=seed)
    mech = mechanism_verdict(chars)

    reports, pvals, order = {}, [], []
    for arm in arms_rows:
        if arm == "signal":
            continue
        rep = arm_report(arm, arms_rows[arm], signal_rows, ctrl_rows, seed=seed)
        reports[arm] = rep
        # Same basis the gate uses: matched for timing arms, pooled for a pure filter whose
        # matched cells are identical trades and would produce a degenerate test.
        basis = "vs_signal_pooled" if arm in FILTER_ARMS else "vs_signal_matched"
        p = (((rep.get(basis) or {}).get("paired") or {}).get("p_sign"))
        # A one-sided reading: only an arm that is BETTER than the signal can be a discovery.
        md = (((rep.get(basis) or {}).get("paired") or {}).get("mean_diff"))
        if p is not None:
            pvals.append(p if (md or 0) > 0 else 1.0)
            order.append(arm)
    flags = bh_fdr(pvals, FDR_Q) if pvals else []
    fdr = {a: {"p_sign": pvals[i], "discovery": bool(flags[i]) if i < len(flags) else False}
           for i, a in enumerate(order)}

    gates = {arm: arm_gate(reports[arm], arm, (fdr.get(arm) or {}).get("discovery"))
             for arm in reports}
    holdout = holdout_arm_select(arms_rows, signal_rows, ctrl_rows)
    cfilters = context_filters(signal_rows, seed=seed)

    # Everything searched over, counted: the simulated arms AND the same-day context gates.
    # Deflating by the arms alone would understate the search that actually happened.
    n_arms = len([a for a in arms_rows if a != "signal"]) + len(CONTEXT_FILTERS)
    dsr = {}
    for arm, rows in arms_rows.items():
        ret = [v for v in (_f(r.get("pnl_pct")) for r in rows) if v is not None]
        if len(ret) >= MIN_CLOSED_PER_BUCKET:
            # n_trials = the arms searched over. The signal arm is quoted at the same deflation
            # so the two numbers are on the same footing.
            dsr[arm] = deflated_sharpe(ret, n_trials=max(1, n_arms))

    return {
        "signal_baseline": {"n": len(signal_rows), "stats": U.tail_stats(signal_rows),
                            "held_out": U.held_out(signal_rows),
                            "by_year": U.by_year(signal_rows),
                            "tiers": U.tier_report(signal_rows),
                            "median_entry_spread_pct":
                                _median([_f(r.get("entry_spread_pct")) for r in signal_rows])},
        "control": {"n": len(ctrl_rows), "stats": U.tail_stats(ctrl_rows),
                    "held_out": U.held_out(ctrl_rows),
                    "paired_vs_signal": paired_cells(signal_rows, ctrl_rows),
                    "median_entry_spread_pct":
                        _median([_f(r.get("entry_spread_pct")) for r in ctrl_rows])},
        "characterization": chars,
        "mechanism": mech,
        "control_stability": control_stability(signal_rows, ctrl_rows),
        "tilt_decomposition": tilt_decomposition(signal_rows, ctrl_rows),
        "context_filters": cfilters,
        "arms": reports,
        "fdr": fdr,
        "gates": gates,
        "holdout_arm_select": holdout,
        "deflated_sharpe": dsr,
        "sanity": {arm: U.sanity(rows) for arm, rows in arms_rows.items()
                   if len(rows) >= MIN_CLOSED_PER_BUCKET},
        # `U.sanity` checks the five §2 chain signals, which this study does not compute: the
        # vol read here is the ~60-DTE ATM IV SERIES, not a per-alert chain solve, and the
        # term_slope filter is not under test in 22c. So those five WILL flag at 0% coverage on
        # every arm. Recorded as expected rather than silenced — the project's rule is that a
        # sanity flag is explained or investigated, never suppressed to make a run look green.
        "sanity_expected_flags": {
            "empty_by_design": ["term_slope", "skew_25d", "vrp", "gex_proxy", "iv"],
            "why": "22c does not call options_signals_v2.compute_signals; entry vol comes from "
                   "the ATM IV series (atm_iv_60d / iv_rank_252 / iv_pop_20 / iv_vs_rv), whose "
                   "coverage IS reported in `characterization`.",
            "load_bearing_fields_present": ["entry_spread_pct", "cap_tier", "pnl_pct"]},
        "no_entry_reasons": (meta or {}).get("no_entry"),
        "overlaps": (meta or {}).get("overlaps"),
        "meta": meta,
        "verdict": verdict(reports, gates, mech, holdout, cfilters),
        "params": {"WAIT_WINDOW": WAIT_WINDOW, "DELAYS": list(DELAYS),
                   "CONTEXT_FILTERS": list(CONTEXT_FILTERS),
                   "PULLBACK_PCT": PULLBACK_PCT, "IV_DROP": IV_DROP,
                   "IV_POP_MAX": IV_POP_MAX, "IV_TENOR_DTE": IV_TENOR_DTE,
                   "MIN_EXPECTANCY_GAIN": MIN_EXPECTANCY_GAIN,
                   "MIN_CLOSED_PER_BUCKET": MIN_CLOSED_PER_BUCKET,
                   "FDR_Q": FDR_Q, "n_arms_tested": n_arms,
                   "window": [ENTRY_START, ENTRY_END]},
    }


def save(res: dict, out_dir: str = OUT_DIR, name: str = "ENTRY_RESULTS.json") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return path
