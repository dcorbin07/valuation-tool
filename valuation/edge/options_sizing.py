"""
Fixed-dollar-risk position sizing — ADOPTED (phase 2 proved it), plus the 65-75 DTE gate.

--------------------------------------------------------------------------------------------
WHY FIXED DOLLAR RISK IS NOW THE DEFAULT EVERYWHERE.

Phase 1 reported the scream-buy book on a "1 contract per signal" convention and concluded it
was too tail-dependent to size. Phase 2 showed that conclusion was an artefact of the convention
itself. Entry premium per contract spans 1,076x across this universe ($13 to $13,985), so one
contract of a pre-split $3,000 AMZN sits alongside one contract of a $40 bank: the expensive
names dominate the dollars no matter what the signal does.

Re-weighting every trade to the same dollar risk:

                          total      top-15 share   profit ex-top-15   top-3 names
    1 contract each     $143,723         98.1%           $2,767            76%
    fixed $1,000 risk   $160,461         42.0%          $92,998            34%

Concentration collapses, breadth improves, and total profit RISES. This is not a tuning choice;
it is the difference between measuring the strategy and measuring the price of the underlying.
A real account sizing by contract count would accidentally take a 50x larger position in AMZN
than in BAC for the same signal.

RISK_PER_TRADE is the dollar amount put at risk per signal. For a long option the maximum loss
is the premium, so contracts = risk_budget / (premium * 100), floored at 1. The floor matters:
if a single contract costs more than the budget, the trade is either skipped (strict) or taken
at one contract (permissive) - `contracts_for` returns 0 so the CALLER decides, because silently
taking an oversized position is how a risk rule becomes decorative.

--------------------------------------------------------------------------------------------
THE 65-75 DTE REFINEMENT — PRE-COMMITTED GATE, written before it was run.

Phase 2 observed +17.0% expectancy for 65-75 DTE against +7.8% for 45-55, on the full sample.
That was an OBSERVATION on data already seen, not a finding, and the live band stays 45-75 until
it clears a held-out test.

  1. The 65-75 subset must beat the full 45-75 band by at least MIN_DTE_GAIN in expectancy per
     trade, in BOTH held-out halves. One half is noise - the same rule every other change here
     has faced.
  2. Both halves need at least MIN_DTE_TRADES trades in the subset, or the comparison is not
     measurable.
  3. The comparison is made on FIXED-DOLLAR-RISK expectancy, since that is now the reporting
     basis; percentage expectancy per trade is unaffected by sizing, so this is the same number.

A narrower DTE band also means FEWER alerts (a contract must exist in the tighter window), so a
higher expectancy on many fewer trades is not automatically better for the book. Trade count is
reported alongside so that trade-off is visible rather than hidden behind a percentage.

================================ RESULT (run after the above was committed) =================

§1 SIZING - ADOPTED, but the phase-2 headline figure was IDEALISED and is corrected here.

Phase 2 reported that fixed-dollar sizing cuts the top-15 share to 42.0%. That computation
deployed exactly $1,000 per trade, i.e. FRACTIONAL CONTRACTS, which do not exist. With whole
contracts the achievable range is worse:

    basis                                  n      exp      cum        top-15   ex-top-15
    1 contract each (phase 1)          1,540   +10.42%   $143,723     98.1%      $2,767
    idealised fractional (phase 2)     1,540   +10.42%   $160,461     42.0%     $92,998
    whole contracts, min 1             1,540   +10.42%   $226,082     62.9%     $83,986
    whole contracts, skip too-costly   1,340    +9.54%   $110,318     50.3%     $54,853

200 of 1,540 signals (13.0%) have a single contract costing more than a $1,000 budget, so they
are either skipped or taken oversized - there is no way to size them correctly at that budget.

THE CONCLUSION SURVIVES, THE NUMBER DOES NOT. Fixed-dollar sizing takes concentration from 98.1%
to roughly 45-63% and lifts profit ex-tail from $2,767 to $55k-$93k. It does NOT reach 42%
in any tradeable form, and phase 2 should have said so.

BUDGET SENSITIVITY - a larger budget is better on every axis, because it is what lets an
expensive name be sized correctly relative to a cheap one:

    $1,000   1,340 trades (87.0% of signals)   exp  +9.54%   top-15 50.3%
    $2,500   1,480 trades (96.1%)              exp  +9.70%   top-15 47.8%
    $5,000   1,515 trades (98.4%)              exp +10.16%   top-15 44.5%

Note percentage expectancy is IDENTICAL across sizing schemes at full coverage (+10.42%) - as it
must be, since sizing cannot change a per-trade return. Only the dollars and the concentration
move. That invariance is the check that the re-weighting was done correctly.

--------------------------------------------------------------------------------------------
§3 65-75 DTE REFINEMENT - REJECTED.

    half     all trades              65-75 DTE subset          gain
    first    n=770  +16.43%          n=242  +27.97%          +11.55pp   PASS
    second   n=770   +4.41%          n=231   +5.60%           +1.19pp   FAIL

It clears the bar spectacularly on the early half and essentially vanishes on the recent one.
That is the SAME fade that afflicts the strategy overall, so the refinement does not arrest the
fade - it inherits it. Phase 2's +17.0% vs +7.8% was a full-sample observation dominated by the
early period. The live band stays 45-75.

This is exactly why the observation was not adopted when it was noticed: a 9pp full-sample gap
looked like an easy win and is worth nothing on the half that matters.

"""
from __future__ import annotations

from typing import Optional

# Adopted default. A moderate convex sleeve, not a core allocation - the edge is real and broad
# but fading, so the sizing reflects that rather than the best-case reading.
RISK_PER_TRADE = 1000.0
CONTRACT_MULTIPLIER = 100

# Pre-committed gate for the DTE refinement.
MIN_DTE_GAIN = 0.05        # 5pp of expectancy per trade, in BOTH halves
MIN_DTE_TRADES = 50        # per half, in the narrowed subset
DTE_NARROW = (65, 75)
DTE_CURRENT = (45, 75)


def contracts_for(premium: float, risk_budget: float = RISK_PER_TRADE) -> int:
    """How many contracts equal `risk_budget` of premium at risk. 0 means 'too expensive'.

    Returns 0 rather than silently rounding up to 1, so the caller decides whether to skip the
    trade or accept an oversized position. A risk rule that quietly exceeds itself is decorative.
    """
    try:
        p = float(premium)
    except (TypeError, ValueError):
        return 0
    if p <= 0:
        return 0
    cost = p * CONTRACT_MULTIPLIER
    return int(risk_budget // cost)


def size_trade(row, risk_budget: float = RISK_PER_TRADE, allow_single: bool = True) -> dict:
    """Re-express one backtest row at fixed dollar risk.

    `pnl_pct` is invariant to sizing; only the dollars change. Both are returned so a reader can
    see that the percentage figure was not quietly altered.
    """
    prem = row.get("entry_premium")
    n = contracts_for(prem, risk_budget)
    if n == 0:
        if not allow_single:
            return {"skipped": True, "reason": "premium exceeds risk budget"}
        n = 1
    pct = row.get("pnl_pct")
    deployed = (float(prem) * CONTRACT_MULTIPLIER * n) if prem else 0.0
    return {"skipped": False, "contracts": n, "deployed": deployed,
            "pnl_pct": pct,
            "pnl_dollars": (pct * deployed) if pct is not None else None}


def resize_all(rows, risk_budget: float = RISK_PER_TRADE) -> list:
    """Whole book at fixed dollar risk. Shape stays compatible with options_tracker._stats."""
    out = []
    for r in rows:
        s = size_trade(r, risk_budget)
        if s.get("skipped"):
            continue
        out.append({**r, "contracts": s["contracts"], "deployed": s["deployed"],
                    "pnl_dollars": s["pnl_dollars"]})
    return out


def dte_gate(rows, narrow=DTE_NARROW, min_gain: float = MIN_DTE_GAIN,
             min_trades: int = MIN_DTE_TRADES) -> dict:
    """Held-out test of the narrower DTE band against the current one, both halves."""
    from .options_tracker import _stats

    ok = [r for r in rows if r.get("pnl_pct") is not None and r.get("dte") is not None]
    ok.sort(key=lambda r: r["alert_ts"])
    mid = len(ok) // 2
    halves = {"first": ok[:mid], "second": ok[mid:]}
    res = {"narrow": list(narrow), "gate": {"min_gain": min_gain, "min_trades": min_trades},
           "halves": {}}
    passes = []
    for name, sl in halves.items():
        sub = [r for r in sl if narrow[0] <= r["dte"] <= narrow[1]]
        all_s, sub_s = _stats(sl), _stats(sub)
        gain = ((sub_s["expectancy_pct"] or 0) - (all_s["expectancy_pct"] or 0))
        enough = sub_s["n_closed"] >= min_trades
        res["halves"][name] = {
            "n_all": all_s["n_closed"], "exp_all": all_s["expectancy_pct"],
            "n_narrow": sub_s["n_closed"], "exp_narrow": sub_s["expectancy_pct"],
            "gain": gain, "enough_trades": enough,
            "passes": bool(enough and gain >= min_gain),
        }
        passes.append(res["halves"][name]["passes"])
    res["passed"] = all(passes)
    return res
