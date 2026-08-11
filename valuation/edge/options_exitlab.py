"""
OPTIONS_DEEP_RESEARCH thread #1 — EXIT optimization. The biggest untested lever in the book.

PRE-SPECIFIED. Everything above the "RESULT" banner was written and committed BEFORE any policy
was scored. Twenty-one exit policies on a heavy-tailed payoff is a search, and a grid scored first
and judged afterwards produces a winner by construction.

--------------------------------------------------------------------------------------------
WHY THIS THREAD IS FIRST.

Every options result this project has ever produced uses ONE exit: +100% target, -50% stop,
half-DTE time stop. It was never chosen — it was inherited from `options_tracker`'s defaults and
has been held fixed through the 55-name backtest, the §2 signal gate, the trade autopsy, the 22b
breadth run and the 22c entry study. Meanwhile:

  * the ENTRY signal is dead. 22b showed the scream-buy alert loses to a random-entry control
    (+11.07% random vs +5.14% signal on 187 names), and 22c showed that finding is stable in both
    held-out halves, that the mechanism is extension rather than pumped vol, and that fifteen
    corrected entries all fail. The autopsy's 127 hypotheses over 64 entry features found zero
    survivors.
  * so if an options edge exists, it is not in a better entry. It is in the EXIT, the SIZING, or
    the CROSS-SECTION — and the exit is the one a long-option payoff is most sensitive to, because
    a convex position's P&L is dominated by when you let go of it.

--------------------------------------------------------------------------------------------
THE KEY TEST, AND WHY IT IS THE RANDOM ENTRIES THAT MATTER.

The mandate names it explicitly: run every exit policy on RANDOM entries as well as signal
entries. The logic is clean.

  * An exit rule that beats the shipped exit on BOTH entry sets is a property of the exit. That is
    a real, entry-independent finding and it would be the first thing this project has found in
    the options book that does not depend on a signal it no longer believes in.
  * An exit rule that beats it only on the SIGNAL entries is entry-conditional. Given that the
    signal's day-selection is measurably negative, an exit that "works" only there is far more
    likely to be an interaction with one book's particular path shapes than an edge. It is
    reported separately and labelled as such — never merged into the headline.

--------------------------------------------------------------------------------------------
ONE DATA PASS, TWENTY-ONE POLICIES. THIS IS WHAT MAKES THE THREAD AFFORDABLE AND EXACT.

A contract's whole life is one cached quote path. Every exit policy is a different reading of the
SAME path, so the expensive part — pulling each contract's daily history — is done once per entry
and every policy is evaluated against it. Two consequences worth stating:

  1. The comparison is EXACTLY matched. Policy A and policy B see the identical entry, the
     identical fills and the identical quotes. Nothing differs except when the position is closed.
  2. The baseline policy must reproduce the shipped simulator bit for bit, and that is asserted
     rather than assumed — `replay_matches_shipped()` re-derives the 22b/22c trade log from the
     paths and fails loudly on any mismatch. A rebuilt evaluator that quietly differs from the
     production one would make every number here incomparable to the rest of the project.

--------------------------------------------------------------------------------------------
THE TWENTY-ONE POLICIES. Fixed here, before the run. Each family varies ONE dimension from the
shipped exit; the two composites are declared in advance rather than assembled from the winners.

    shipped                 +100% / -50% / half-DTE                        (the baseline)
    tp50 tp75 tp150 tp200 tp_none      take-profit level, everything else held
    sl30 sl70 sl_none                  stop level, everything else held
    time25 time75 time100              time stop as a fraction of the original DTE
    dte21 dte14 dte7                   close when this many days to expiry remain
    trail25 trail35 trail50            trailing drawdown from the high-water mark REPLACES the stop
    ratchet35               fixed stop until +50%, then a 35% trail
    run_winners             no take-profit, ratcheting trail, hold to expiry
    tp100_only              take-profit only: no stop, no time stop

Within a day the checks fire in a fixed order — TARGET, then fixed STOP, then TRAIL, then TIME —
matching the shipped simulator, which evaluates the target first when a single day clears both.
That ordering flatters the target slightly and it is held constant across every policy, so no
policy gains from it relative to another.

--------------------------------------------------------------------------------------------
PRE-COMMITTED GATE. A verdict is one of ADOPT / SIGNAL-ONLY / REJECT.

  X1  A POLICY IS ADOPTED as a general exit improvement only if ALL hold, at aggression 1.0,
      on the SAME entries the shipped exit sees:
        (a) it beats the shipped exit's expectancy by >= MIN_EXPECTANCY_GAIN on the SIGNAL
            entries — imported from options_backtest, the standing bar for adopting any
            construction change, so this thread cannot run an easier race than the ones before it;
        (b) it ALSO beats the shipped exit on the RANDOM entries. The key test. An exit that only
            works behind a dead signal is not an exit edge;
        (c) it is positive in BOTH held-out halves on both entry sets;
        (d) >= MIN_CLOSED_PER_BUCKET trades;
        (e) its paired name-year advantage over the shipped exit survives BH-FDR at FDR_Q across
            all policies. Pooled expectancy on this payoff is moved by single trades; the paired
            sign test is distribution-free and is the one that has to hold.

  X2  SIGNAL-ONLY is recorded when (a), (c), (d) and (e) hold on the signal entries but (b) fails.
      Reported as an entry-conditional result, never as an exit edge.

  X3  MULTIPLICITY IS PAID FOR. Twenty-one policies is the whole point of the thread and also its
      main hazard:
        * Deflated Sharpe uses n_trials = the number of policies;
        * paired p-values go through BH-FDR together;
        * PBO is computed by CSCV over the POLICY x TIME-BLOCK matrix — the textbook application
          of the method, and the one thing that directly measures "is the best policy in-sample
          still good out-of-sample". PBO must be < MAX_PBO.

  X4  THE PRIMARY OUT-OF-SAMPLE READ is choose-the-best-policy-on-one-half, measure-it-on-the-
      other, in BOTH directions — the same discipline the fundamental panel uses for theme
      changes and 22c used for entry arms.

  X5  THE HEADLINE IS THE AGGRESSION = 1.0 NUMBER, and expectancy is reported per trade AND per
      day held. An exit that closes in half the time is not comparable per trade: it frees the
      capital sooner and turns over twice as fast. Both readings ship, with the caveat that the
      per-day figure assumes instant redeployment, which no real book gets.

  X6  THE TAIL IS WATCHED EXPLICITLY. 83.7% of the shipped book's gross winnings come from trades
      that made >= +100%. A take-profit at +50% mechanically removes that tail and will raise the
      hit rate while doing it. Any policy that improves expectancy while collapsing the tail is a
      DIFFERENT STRATEGY, not a better exit, and is flagged as one.

Expect rejection. The shipped exit was never tuned, so it is a fair baseline rather than an
overfitted one, and "the arbitrary exit we inherited is not beatable" is a perfectly good answer —
it would close the largest remaining hole in the options work.

--------------------------------------------------------------------------------------------
WHAT THIS CANNOT SEE.

  * DAILY closes only. An intraday spike through a target or a trailing stop that closes back
    inside is not seen. This is the same conservatism the whole options lane runs under, and it
    bites the TRAILING policies hardest — a real trailing stop would be hit more often than this
    measures, so trailing results here are, if anything, optimistic.
  * NO TRUE ATR. The cached Sharadar bars carry date/close/volume only — no high or low — so an
    ATR-based trail is not computable and is not attempted. The trails here are drawdowns from the
    option's own high-water mark, which is the more natural formulation for a long-premium book
    anyway, and its absence is recorded rather than quietly substituted.
  * NO EARLY EXERCISE, assignment or borrow. Long calls only; none bind.
  * The universe is the miner's cache, chosen by TODAY's liquidity and already screened for
    spread. Both biases run toward the edge surviving and neither can be removed here.
  * Per-day expectancy is not a portfolio return. Sizing is thread #7 and nothing here answers it.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
from typing import Optional

from . import options_backtest as OB
from . import options_fill as F
from . import options_universe as U
from .options_autopsy import FDR_Q, bh_fdr, deflated_sharpe
from .options_backtest import MIN_EXPECTANCY_GAIN
from .options_entry import paired_cells
from .options_signals_v2 import LATE_START
from .options_tracker import MIN_CLOSED_PER_BUCKET, _stats

ENTRY_START = U.ENTRY_START
ENTRY_END = U.ENTRY_END

MAX_PBO = 0.50                  # CSCV probability of backtest overfitting
CSCV_BLOCKS = 10                # time blocks; C(10,5) = 252 in/out splits
TAIL_WIN = U.TAIL_WIN

# ---- the twenty-one policies, fixed before the run -------------------------------------------
# tp / sl        : take-profit and stop, as a return on the entry fill. None = not used.
# time_frac      : time stop at this fraction of the ORIGINAL DTE, in calendar days.
# dte_exit       : close when this many days to expiry remain.
# trail          : drawdown from the high-water mark of the sell-side mark.
# trail_after    : the trail only arms once the position has been up by this much.
SHIPPED = {"tp": 1.00, "sl": -0.50, "time_frac": 0.50}
POLICIES = (
    ("shipped", dict(SHIPPED)),
    ("tp50", {"tp": 0.50, "sl": -0.50, "time_frac": 0.50}),
    ("tp75", {"tp": 0.75, "sl": -0.50, "time_frac": 0.50}),
    ("tp150", {"tp": 1.50, "sl": -0.50, "time_frac": 0.50}),
    ("tp200", {"tp": 2.00, "sl": -0.50, "time_frac": 0.50}),
    ("tp_none", {"tp": None, "sl": -0.50, "time_frac": 0.50}),
    ("sl30", {"tp": 1.00, "sl": -0.30, "time_frac": 0.50}),
    ("sl70", {"tp": 1.00, "sl": -0.70, "time_frac": 0.50}),
    ("sl_none", {"tp": 1.00, "sl": None, "time_frac": 0.50}),
    ("time25", {"tp": 1.00, "sl": -0.50, "time_frac": 0.25}),
    ("time75", {"tp": 1.00, "sl": -0.50, "time_frac": 0.75}),
    ("time100", {"tp": 1.00, "sl": -0.50, "time_frac": 1.00}),
    ("dte21", {"tp": 1.00, "sl": -0.50, "time_frac": None, "dte_exit": 21}),
    ("dte14", {"tp": 1.00, "sl": -0.50, "time_frac": None, "dte_exit": 14}),
    ("dte7", {"tp": 1.00, "sl": -0.50, "time_frac": None, "dte_exit": 7}),
    ("trail25", {"tp": 1.00, "sl": None, "time_frac": 0.50, "trail": 0.25}),
    ("trail35", {"tp": 1.00, "sl": None, "time_frac": 0.50, "trail": 0.35}),
    ("trail50", {"tp": 1.00, "sl": None, "time_frac": 0.50, "trail": 0.50}),
    ("ratchet35", {"tp": 1.00, "sl": -0.50, "time_frac": 0.50, "trail": 0.35,
                   "trail_after": 0.50}),
    ("run_winners", {"tp": None, "sl": -0.50, "time_frac": 1.00, "trail": 0.35,
                     "trail_after": 0.50}),
    ("tp100_only", {"tp": 1.00, "sl": None, "time_frac": 1.00}),
)
POLICY_NAMES = tuple(n for n, _ in POLICIES)
BASELINE = "shipped"
ENTRY_SETS = ("signal", "random")

OUT_DIR = os.path.join("data", "options_exitlab")


def _log(m):
    print(f"[exitlab] {m}", flush=True)


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


# ================================ the path =================================================
def capture_path(provider, ticker: str, entry_row, entry_date: dt.date, bars: dict) -> Optional[dict]:
    """One entry's whole contract life, as data. Every policy reads this and nothing else.

    Deliberately stores the RAW quotes rather than any derived return, so a policy can be
    evaluated with the project's own `round_trip` — including its commission and its
    settle-at-intrinsic path — instead of a reimplementation that drifts from it.
    """
    import pandas as pd

    strike = float(entry_row["strike"])
    right = str(entry_row["right"])
    expiry = pd.Timestamp(entry_row["expiration"]).date()
    entry_q = F.Quote(bid=entry_row.get("bid"), ask=entry_row.get("ask"),
                      oi=entry_row.get("open_interest"), volume=entry_row.get("volume"))
    if F.quote_reject_reason(entry_q):
        return None
    entry_fill = F.fill_price(entry_q, "buy", 1.0)
    if not entry_fill or entry_fill <= 0:
        return None

    hist = provider.contract_history(ticker, expiry, strike, right, entry_date, expiry)
    days = []
    if hist is not None and len(hist):
        for _, row in hist.iterrows():
            day = row["date"]
            if day <= entry_date:
                continue
            q = F.Quote(bid=row.get("bid"), ask=row.get("ask"))
            # AUDIT B2, APPLIED HERE 2026-08-08 (O1). This line read
            # `quote_reject_reason(q, check_liquidity=False)` -- the PRE-B2 rule -- while
            # `options_backtest.simulate_trade:367`, which built every banked book, was moved to
            # `exit_reject_reason` when B2 landed. This module was missed.
            #
            # The consequence is exactly what B2's own docstring predicts: a wide or thin quote
            # is a bad price, not an absent one, and dropping the day deletes it from the
            # trade's history. Losers that decay through the -50% stop on a wide-quote day are
            # never stopped and ride on to a worse outcome. MEASURED on the R2 book: the
            # shipped policy replayed from the freeze reproduced the banked book on only
            # 86.950% of 3,885 trades, `held_days(replay) - held_days(book)` was NEVER negative
            # (3,363 exact, every other trade held LONGER), and one ABBV contract kept 7 of its
            # 34 quote days. Entry fills matched 3,885/3,885, which is what localised it here.
            if F.exit_reject_reason(q) is not None:
                continue
            days.append((day.isoformat(), _f(row.get("bid")), _f(row.get("ask"))))

    # As-traded close at or before expiry: strikes are never retro-adjusted.
    und = None
    px = bars.get("raw_close") or bars["close"]
    for i, ds in enumerate(bars["date"]):
        if ds <= expiry.isoformat():
            und = px[i]
    return {"ticker": ticker, "entry_date": entry_date.isoformat(),
            "expiry": expiry.isoformat(), "strike": strike, "right": right,
            "entry_bid": _f(entry_row.get("bid")), "entry_ask": _f(entry_row.get("ask")),
            "entry_oi": _f(entry_row.get("open_interest")),
            "entry_volume": _f(entry_row.get("volume")),
            "entry_fill": entry_fill, "dte0": (expiry - entry_date).days,
            "days": days, "settle_underlying": und,
            "entry_spread_pct": entry_q.spread_pct}


def _entry_quote(path) -> F.Quote:
    return F.Quote(bid=path["entry_bid"], ask=path["entry_ask"],
                   oi=path["entry_oi"], volume=path["entry_volume"])


def apply_policy(path: dict, policy: dict, aggression: float = 1.0,
                 settle: str = "intrinsic") -> Optional[dict]:
    """Evaluate ONE exit policy against ONE captured path.

    A line-for-line re-reading of `options_backtest.simulate_trade`'s loop with the exit
    conditions generalised. The baseline policy must therefore reproduce it exactly, which
    `replay_matches_shipped` asserts on the real trade log rather than on a fixture.

    `settle` decides what happens when a policy holds PAST the last quote the contract still had:

      "last_quote"  what the production simulator does — mark at the last usable quote.
      "intrinsic"   what actually happens — the position is settled against the underlying at
                    expiry.  THE DEFAULT, and the only honest basis for comparing exits.

    THIS DISTINCTION IS NOT COSMETIC AND IT IS THE MAIN FINDING OF THIS THREAD. A contract stops
    being quotable when its bid goes to zero or its spread blows out, which is precisely when it
    is dying. Marking it at the last day it was still quotable therefore books a price from BEFORE
    the final decay. Measured on this run: for the hold-to-expiry policy, 44.6% of trades land in
    that fall-through, their last usable quote is a MEDIAN OF 10 DAYS before expiry, the stale mark
    is higher than the true settlement in 94.7% of cases, and 86.1% of them carry a positive mark
    on a contract that expires worthless. Mean marked return -77.8% against a true -92.2%.

    The bias scales with how long a policy holds, so it does not merely add noise — it manufactures
    a monotone "reward" for holding longer. Every earlier options result in this project uses the
    shipped exit, which reaches this fall-through on 0.9% of trades, so those results are
    essentially unaffected; the moment a hold-longer policy is tested, they are not.
    """
    entry_q = _entry_quote(path)
    entry_fill = path["entry_fill"]
    entry_date = dt.date.fromisoformat(path["entry_date"])
    expiry = dt.date.fromisoformat(path["expiry"])
    right, strike = path["right"], path["strike"]

    tp, sl = policy.get("tp"), policy.get("sl")
    time_frac = policy.get("time_frac")
    dte_exit = policy.get("dte_exit")
    trail, trail_after = policy.get("trail"), policy.get("trail_after")

    time_stop_date = (entry_date + dt.timedelta(days=int(round(path["dte0"] * time_frac)))
                      if time_frac is not None else None)
    peak = None
    armed = trail is not None and trail_after is None
    last_q = None
    for ds, bid, ask in path["days"]:
        day = dt.date.fromisoformat(ds)
        q = F.Quote(bid=bid, ask=ask)
        last_q = q
        mark = F.fill_price(q, "sell", aggression)
        if mark is None:
            continue
        ret = mark / entry_fill - 1.0
        peak = mark if peak is None else max(peak, mark)
        if trail is not None and not armed and trail_after is not None and ret >= trail_after:
            armed = True

        hit_target = tp is not None and ret >= tp
        hit_stop = sl is not None and ret <= sl
        hit_trail = bool(trail is not None and armed and peak and mark <= peak * (1.0 - trail))
        hit_time = bool(time_stop_date is not None and day >= time_stop_date)
        hit_dte = bool(dte_exit is not None and (expiry - day).days <= dte_exit)

        if hit_target or hit_stop or hit_trail or hit_time or hit_dte:
            t = F.round_trip(entry_q, q, right=right, strike=strike, aggression=aggression)
            if not t.get("ok"):
                continue
            t.update({"exit_date": ds, "held_days": (day - entry_date).days,
                      "exit_reason": ("target" if hit_target else
                                      "stop" if hit_stop else
                                      "trail" if hit_trail else
                                      "time_stop" if hit_time else "dte_exit")})
            return t
    # Held past the last quote the contract had. `settle` decides how that is priced.
    und = path.get("settle_underlying")
    use_intrinsic = (settle == "intrinsic" and und is not None)
    # AUDIT B3 landed the intrinsic-at-expiry rule inside `round_trip` itself, defaulted ON.
    # The `last_quote` mode here exists ONLY to reproduce the old, buggy production behaviour for
    # the parity check, so it must be able to opt out — otherwise the demonstration of the bug
    # silently becomes a demonstration of the fix and the comparison measures nothing.
    t = F.round_trip(entry_q, None if use_intrinsic else last_q, right=right, strike=strike,
                     exit_underlying=und, aggression=aggression, expired=True,
                     force_intrinsic_at_expiry=use_intrinsic)
    if t.get("ok"):
        t.update({"exit_date": path["expiry"], "held_days": (expiry - entry_date).days,
                  "exit_reason": "expiry",
                  # Flagged so a policy that leans on this path can never hide in an average.
                  "stale_mark_used": bool(not use_intrinsic and last_q is not None),
                  "no_settle_price": bool(settle == "intrinsic" and und is None)})
    return t


def score_paths(paths: list, policy_name: str, policy: dict, aggression: float = 1.0,
                settle: str = "intrinsic") -> list:
    """One policy over a whole entry set -> rows in the shape `options_tracker._stats` scores."""
    out = []
    for p in paths:
        t = apply_policy(p, policy, aggression=aggression, settle=settle)
        if not t or not t.get("ok"):
            continue
        out.append({
            "alert_ts": p.get("alert_date") or p["entry_date"],
            "alert_date": p.get("alert_date") or p["entry_date"],
            "entry_date": p["entry_date"], "ticker": p["ticker"],
            "opt_right": "call" if str(p["right"]).upper().startswith("C") else "put",
            "strike": p["strike"], "expiry": p["expiry"],
            "entry_premium": t.get("entry_fill"), "exit_premium": t.get("exit_fill"),
            "pnl_pct": t.get("return_pct"), "pnl_dollars": t.get("net_pnl"),
            "exit_reason": t.get("exit_reason"), "held_days": t.get("held_days"),
            "dte0": p["dte0"], "cap_tier": p.get("cap_tier"),
            "entry_spread_pct": p.get("entry_spread_pct"),
            "settled_at_intrinsic": t.get("settled_at_intrinsic"),
            "stale_mark_used": t.get("stale_mark_used"),
            "policy": policy_name, "status": "closed"})
    return out


def replay_matches_shipped(paths: list, shipped_rows: list) -> dict:
    """The correctness gate: the baseline policy re-derived from the paths must equal the log the
    production simulator produced. Any mismatch and every number in this thread is incomparable
    to the rest of the project, so it fails loudly rather than warning.

    Runs on `settle="last_quote"` deliberately: the point is to prove the evaluator reproduces
    PRODUCTION, and production marks the fall-through at the last usable quote. The honest
    settlement is what every policy comparison uses; this is the parity check, not the headline.
    """
    got = {(r["ticker"], r["entry_date"]): r for r in
           score_paths(paths, BASELINE, dict(SHIPPED), settle="last_quote")}
    want = {(r["ticker"], str(r.get("entry_date") or r["alert_ts"])[:10]): r
            for r in shipped_rows}
    shared = set(got) & set(want)
    bad = [k for k in shared
           if abs((_f(got[k].get("pnl_pct")) or 0) - (_f(want[k].get("pnl_pct")) or 0)) > 1e-9]
    return {"ok": not bad and len(shared) > 0,
            "n_paths": len(got), "n_shipped": len(want), "n_shared": len(shared),
            "n_mismatched": len(bad), "examples": bad[:5],
            "only_in_paths": len(set(got) - set(want)),
            "only_in_shipped": len(set(want) - set(got))}


# ================================ per-policy statistics ====================================
def policy_stats(rows) -> dict:
    """Per trade AND per day held (X5), plus the tail watch (X6)."""
    p = [v for v in (_f(r.get("pnl_pct")) for r in rows) if v is not None]
    if not p:
        return {"n": 0}
    s = _stats(rows)
    held = [_f(r.get("held_days")) for r in rows]
    mh = _mean(held)
    wins = [v for v in p if v > 0]
    return {
        "n": len(p),
        "expectancy_pct": s["expectancy_pct"], "profit_factor": s["profit_factor"],
        "hit_rate": s["hit_rate"], "avg_win_pct": s["avg_win_pct"],
        "avg_loss_pct": s["avg_loss_pct"], "median_pct": sorted(p)[len(p) // 2],
        "p_tail_win": sum(1 for v in p if v >= TAIL_WIN) / len(p),
        "tail_share_of_gross_win": (sum(v for v in p if v >= TAIL_WIN) / sum(wins))
        if wins else None,
        "p_total_loss": sum(1 for v in p if v <= -0.90) / len(p),
        "mean_held_days": mh, "median_held_days": _median(held),
        # X5: an exit that closes twice as fast is not comparable per trade. Reported alongside,
        # with the standing caveat that it assumes capital redeploys the same day, which it does
        # not — this is a comparability aid, not a portfolio return.
        "expectancy_per_day_held": ((s["expectancy_pct"] / mh) if mh else None),
        "exit_mix": _mix(rows),
    }


def _mix(rows) -> dict:
    d = {}
    for r in rows:
        k = str(r.get("exit_reason") or "?")
        d[k] = d.get(k, 0) + 1
    n = len(rows) or 1
    return {k: v / n for k, v in sorted(d.items())}


def held_out(rows) -> dict:
    early = [r for r in rows if str(r.get("alert_date") or r["alert_ts"])[:10] < LATE_START]
    late = [r for r in rows if str(r.get("alert_date") or r["alert_ts"])[:10] >= LATE_START]
    return {"early_n": len(early), "late_n": len(late),
            "early": _stats(early)["expectancy_pct"] if early else None,
            "late": _stats(late)["expectancy_pct"] if late else None,
            "both_positive": bool(early and late
                                  and (_stats(early)["expectancy_pct"] or 0) > 0
                                  and (_stats(late)["expectancy_pct"] or 0) > 0)}


def by_year(rows) -> dict:
    g = {}
    for r in rows:
        g.setdefault(str(r.get("alert_date") or r["alert_ts"])[:4], []).append(r)
    return {y: {"n": len(rs), "expectancy_pct": _stats(rs)["expectancy_pct"]}
            for y, rs in sorted(g.items())}


# ================================ CSCV / PBO over policies =================================
def pbo_cscv_policies(rows_by_policy: dict, n_blocks: int = CSCV_BLOCKS) -> dict:
    """Probability of Backtest Overfitting across the POLICY grid (X3).

    This is the textbook use of CSCV, and a better fit here than anywhere else in the project:
    N configurations of ONE strategy, ranked in-sample, then checked out-of-sample. Time is cut
    into `n_blocks` contiguous blocks; every balanced split of the blocks into an in-sample and
    an out-of-sample half is enumerated; the in-sample best policy's out-of-sample RANK is
    recorded. PBO is the share of splits where that winner lands in the bottom half out of
    sample — i.e. how often picking the best backtest would have been a mistake.
    """
    from itertools import combinations

    # Declared policies first, in their declared order, then anything else the caller passed.
    # Filtering to POLICY_NAMES alone would silently drop a policy that was added to the grid but
    # not to the constant — the same class of silent-omission bug this project keeps hitting.
    names = ([n for n in POLICY_NAMES if n in rows_by_policy]
             + [n for n in sorted(rows_by_policy) if n not in POLICY_NAMES])
    if len(names) < 3:
        return {"ok": False, "reason": "too few policies"}
    dates = sorted({str(r.get("alert_date") or r["alert_ts"])[:10]
                    for n in names for r in rows_by_policy[n]})
    if len(dates) < n_blocks * 5:
        return {"ok": False, "reason": "too few dates"}
    cuts = [dates[int(len(dates) * i / n_blocks)] for i in range(1, n_blocks)]

    def block_of(d):
        for i, c in enumerate(cuts):
            if d < c:
                return i
        return n_blocks - 1

    # per policy, per block: the per-trade Sharpe inside that block
    perf = {}
    for n in names:
        buckets = {}
        for r in rows_by_policy[n]:
            v = _f(r.get("pnl_pct"))
            if v is not None:
                buckets.setdefault(block_of(str(r.get("alert_date") or r["alert_ts"])[:10]),
                                   []).append(v)
        perf[n] = buckets

    def sharpe(vals):
        if len(vals) < 5:
            return None
        m = sum(vals) / len(vals)
        var = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
        sd = math.sqrt(var)
        return (m / sd) if sd > 0 else None

    half = n_blocks // 2
    logits, below = [], 0
    total = 0
    for is_blocks in combinations(range(n_blocks), half):
        oos_blocks = [b for b in range(n_blocks) if b not in is_blocks]
        is_s, oos_s = {}, {}
        for n in names:
            a = [v for b in is_blocks for v in perf[n].get(b, [])]
            o = [v for b in oos_blocks for v in perf[n].get(b, [])]
            si, so = sharpe(a), sharpe(o)
            if si is not None and so is not None:
                is_s[n], oos_s[n] = si, so
        if len(is_s) < 3:
            continue
        best = max(is_s, key=lambda k: is_s[k])
        ranked = sorted(oos_s, key=lambda k: oos_s[k])          # worst -> best
        rank = ranked.index(best) + 1
        w = rank / (len(ranked) + 1.0)
        total += 1
        if w <= 0.5:
            below += 1
        w = min(max(w, 1e-6), 1 - 1e-6)
        logits.append(math.log(w / (1 - w)))
    if not total:
        return {"ok": False, "reason": "no usable splits"}
    return {"ok": True, "n_splits": total, "pbo": below / total,
            "median_logit": _median(logits), "n_policies": len(names),
            "n_blocks": n_blocks,
            "passes": bool(below / total < MAX_PBO),
            "note": "CSCV over the policy grid; PBO is the share of splits where the "
                    "in-sample best policy ranked in the bottom half out of sample."}


# ================================ comparison + gate ========================================
def compare(rows_by_policy: dict, seed: int = 0) -> dict:
    """Every policy against the shipped baseline, on ONE entry set."""
    base = rows_by_policy.get(BASELINE) or []
    out = {}
    for name in POLICY_NAMES:
        rows = rows_by_policy.get(name)
        if not rows:
            continue
        st = policy_stats(rows)
        d = {"stats": st, "held_out": held_out(rows), "by_year": by_year(rows)}
        if name != BASELINE and base:
            # Exactly matched: policy and baseline see the same entries by construction, so the
            # paired test is over identical trades and differs only in the exit.
            d["vs_shipped"] = {
                "expectancy_diff": (st["expectancy_pct"] or 0)
                - (_stats(base)["expectancy_pct"] or 0),
                "per_day_diff": ((st.get("expectancy_per_day_held") or 0)
                                 - (policy_stats(base).get("expectancy_per_day_held") or 0)),
                "paired": paired_cells(rows, base),
                "tail_share_change": ((st.get("tail_share_of_gross_win") or 0)
                                      - (policy_stats(base).get("tail_share_of_gross_win") or 0)),
            }
        out[name] = d
    return out


def gate(cmp_signal: dict, cmp_random: dict, fdr: dict) -> dict:
    """X1 / X2, applied mechanically."""
    res = {}
    for name in POLICY_NAMES:
        if name == BASELINE:
            continue
        s = cmp_signal.get(name)
        r = cmp_random.get(name)
        if not s:
            continue
        vs = s.get("vs_shipped") or {}
        gain = vs.get("expectancy_diff")
        beats_signal = bool(gain is not None and gain >= MIN_EXPECTANCY_GAIN)
        rvs = (r or {}).get("vs_shipped") or {}
        beats_random = bool((rvs.get("expectancy_diff") or 0) > 0)
        halves = bool(s["held_out"]["both_positive"]
                      and (not r or r["held_out"]["both_positive"]))
        enough = bool((s["stats"].get("n") or 0) >= MIN_CLOSED_PER_BUCKET)
        disc = bool((fdr.get(name) or {}).get("discovery"))
        adopt = bool(beats_signal and beats_random and halves and enough and disc)
        signal_only = bool(beats_signal and not beats_random and halves and enough and disc)
        res[name] = {
            "expectancy_gain_vs_shipped_signal": gain, "bar": MIN_EXPECTANCY_GAIN,
            "beats_shipped_on_signal_by_bar": beats_signal,
            "expectancy_gain_vs_shipped_random": rvs.get("expectancy_diff"),
            "beats_shipped_on_random": beats_random,
            "both_halves_positive": halves, "enough_trades": enough,
            "paired_survives_fdr": disc,
            "X1_adopt": adopt, "X2_signal_only": signal_only,
            "tail_share_change": vs.get("tail_share_change"),
        }
    return res


def holdout_policy_select(rows_by_policy: dict) -> dict:
    """X4 — choose the best policy on one half, measure it on the other. Both directions."""
    def half(rows, which):
        return [r for r in rows
                if (str(r.get("alert_date") or r["alert_ts"])[:10] < LATE_START)
                == (which == "early")]

    base = rows_by_policy.get(BASELINE) or []
    out = {}
    for decide, measure in (("early", "late"), ("late", "early")):
        scores = {}
        bd = half(base, decide)
        if len(bd) < MIN_CLOSED_PER_BUCKET:
            out[f"decide_{decide}"] = {"ok": False, "reason": "baseline half too small"}
            continue
        b0 = _stats(bd)["expectancy_pct"] or 0
        for name, rows in rows_by_policy.items():
            if name == BASELINE:
                continue
            h = half(rows, decide)
            if len(h) < MIN_CLOSED_PER_BUCKET:
                continue
            scores[name] = (_stats(h)["expectancy_pct"] or 0) - b0
        if not scores:
            out[f"decide_{decide}"] = {"ok": False, "reason": "no policy has enough trades"}
            continue
        best = max(scores, key=lambda k: scores[k])
        hm = half(rows_by_policy[best], measure)
        bm = half(base, measure)
        gain = ((_stats(hm)["expectancy_pct"] or 0) - (_stats(bm)["expectancy_pct"] or 0)) \
            if hm and bm else None
        out[f"decide_{decide}"] = {
            "ok": True, "chosen_policy": best, "gain_on_decide_half": scores[best],
            "ranking_on_decide_half": dict(sorted(scores.items(), key=lambda kv: -kv[1])[:5]),
            "measure_half": measure, "n_measured": len(hm),
            "policy_expectancy": _stats(hm)["expectancy_pct"] if hm else None,
            "shipped_expectancy": _stats(bm)["expectancy_pct"] if bm else None,
            "gain_on_measure_half": gain}
    ok = [v for v in out.values() if v.get("ok")]
    out["survives_both_directions"] = bool(len(ok) == 2
                                           and all((v.get("gain_on_measure_half") or 0) > 0
                                                   for v in ok))
    return out


# ================================ orchestration ============================================
def analyse(paths_by_set: dict, shipped_rows: Optional[list] = None, seed: int = 0) -> dict:
    """Score every policy on every entry set and put it all through the gate."""
    scored, stale = {}, {}
    for es, paths in paths_by_set.items():
        scored[es] = {n: score_paths(paths, n, p) for n, p in POLICIES}
        # The SAME grid on production's stale-quote settlement, so the size of the artifact is a
        # reported number per policy rather than a caveat in prose. Nothing is judged on it.
        legacy = {n: score_paths(paths, n, p, settle="last_quote") for n, p in POLICIES}
        stale[es] = {}
        for n in scored[es]:
            hon, leg = scored[es][n], legacy[n]
            used = sum(1 for r in leg if r.get("stale_mark_used"))
            stale[es][n] = {
                "expectancy_honest": _stats(hon)["expectancy_pct"],
                "expectancy_stale_mark": _stats(leg)["expectancy_pct"],
                "overstatement": ((_stats(leg)["expectancy_pct"] or 0)
                                  - (_stats(hon)["expectancy_pct"] or 0)),
                "share_marked_stale": used / len(leg) if leg else None,
                "mean_held_days": _mean([_f(r.get("held_days")) for r in hon])}

    cmp_signal = compare(scored.get("signal") or {}, seed=seed)
    cmp_random = compare(scored.get("random") or {}, seed=seed)

    # BH-FDR over the paired signal-entry tests, one-sided: only a policy that is BETTER than
    # the shipped exit can be a discovery.
    pvals, order = [], []
    for name in POLICY_NAMES:
        if name == BASELINE or name not in cmp_signal:
            continue
        pr = (cmp_signal[name].get("vs_shipped") or {}).get("paired") or {}
        p, z = pr.get("p_sign"), pr.get("sign_z")
        if p is not None:
            # The direction MUST come from the sign test itself, not from the mean. A policy can
            # have a positive mean difference and a significantly NEGATIVE sign test — a big
            # average carried by a few cells while losing in most of them — and screening on the
            # mean would hand it a tiny two-sided p and call it a discovery in the wrong
            # direction. Measured here: sl70's mean is +0.0200 but it wins only 23.8% of cells
            # (z = -7.50), and the mean-screened version flagged it.
            pvals.append(p if (z or 0) > 0 else 1.0)
            order.append(name)
    flags = bh_fdr(pvals, FDR_Q) if pvals else []
    fdr = {n: {"p_sign": pvals[i], "discovery": bool(flags[i]) if i < len(flags) else False}
           for i, n in enumerate(order)}

    n_trials = max(1, len(POLICY_NAMES))
    dsr = {}
    for es in scored:
        dsr[es] = {}
        for n, rows in scored[es].items():
            ret = [v for v in (_f(r.get("pnl_pct")) for r in rows) if v is not None]
            if len(ret) >= MIN_CLOSED_PER_BUCKET:
                dsr[es][n] = deflated_sharpe(ret, n_trials=n_trials)

    out = {
        "n_entries": {es: len(p) for es, p in paths_by_set.items()},
        "signal": cmp_signal,
        "random": cmp_random,
        "fdr": fdr,
        "gate": gate(cmp_signal, cmp_random, fdr),
        "pbo_signal": pbo_cscv_policies(scored.get("signal") or {}),
        "pbo_random": pbo_cscv_policies(scored.get("random") or {}),
        "holdout_signal": holdout_policy_select(scored.get("signal") or {}),
        "holdout_random": holdout_policy_select(scored.get("random") or {}),
        "deflated_sharpe": dsr,
        "stale_mark_artifact": stale,
        "settlement": {"headline": "intrinsic", "parity_check": "last_quote",
                       "why": "a contract stops being quotable when its bid hits zero, i.e. "
                              "exactly when it is dying, so marking the fall-through at the last "
                              "usable quote books a price from before the final decay and "
                              "rewards any policy that holds longer."},
        "params": {"policies": {n: p for n, p in POLICIES}, "baseline": BASELINE,
                   "n_policies": len(POLICIES), "MAX_PBO": MAX_PBO,
                   "MIN_EXPECTANCY_GAIN": MIN_EXPECTANCY_GAIN,
                   "MIN_CLOSED_PER_BUCKET": MIN_CLOSED_PER_BUCKET, "FDR_Q": FDR_Q,
                   "CSCV_BLOCKS": CSCV_BLOCKS, "window": [ENTRY_START, ENTRY_END]},
    }
    if shipped_rows is not None and paths_by_set.get("signal"):
        out["replay_check"] = replay_matches_shipped(paths_by_set["signal"], shipped_rows)
    out["verdict"] = verdict(out)
    return out


def verdict(res: dict) -> dict:
    g = res.get("gate") or {}
    adopted = sorted(n for n, d in g.items() if d.get("X1_adopt"))
    signal_only = sorted(n for n, d in g.items() if d.get("X2_signal_only"))
    pbo = (res.get("pbo_signal") or {}).get("pbo")
    ho = (res.get("holdout_signal") or {}).get("survives_both_directions")
    if adopted and (pbo is not None and pbo < MAX_PBO) and ho:
        label = "ADOPT"
    elif adopted or signal_only:
        label = "SIGNAL-ONLY / SHORT OF BAR"
    else:
        label = "REJECT — the inherited exit is not beaten"
    return {"label": label, "X1_adopted": adopted, "X2_signal_only": signal_only,
            "pbo_signal": pbo, "pbo_passes": (res.get("pbo_signal") or {}).get("passes"),
            "X4_holdout_survives_both_directions": ho,
            "note": "ADOPT needs a policy that clears the bar on BOTH entry sets, a PBO under "
                    "the ceiling, and survival of choose-on-one-half / measure-on-the-other."}


def save(res: dict, out_dir: str = OUT_DIR, name: str = "EXITLAB_RESULTS.json") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return path
