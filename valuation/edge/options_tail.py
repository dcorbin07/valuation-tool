"""
ARCHIVED (master audit MA59, 2026-08-15) - a CLOSED study, kept so its
result stays reproducible. It is NOT reachable from the live product and
`tests/test_ma59_quarantine.py` fails if that ever changes.
Still imported by: nothing in the tree.
Do not extend this module; a new question needs a new register.

Tail-dependence analysis + the "scream-buy+" conviction fingerprint — PRE-SPECIFIED GATE,
committed results-free BEFORE the winners were inspected.

Phase 1 found that 15 of 1,540 trades are 98% of the dollar profit. That single fact decides
whether any of this is sizeable, so it is analysed before anything else is built.

--------------------------------------------------------------------------------------------
THE QUESTION, AND THE TWO ANSWERS THAT LEAD TO OPPOSITE ACTIONS.

  (a) "Occasionally catch a moonshot in a momentum blowup." The edge IS the tail, the base is
      dead money, and the strategy is unsizeable because you cannot know in advance which
      signal becomes the moonshot.

  (b) "A few big winners is the normal shape of convex long-option payoffs and the rest roughly
      break even." That is the EXPECTED shape, not a defect, and the strategy is sizeable with
      discipline.

The discriminator is pre-registered: **expectancy with the top 15 winners removed.** Negative
means (a). Modestly positive means (b) — the tail is upside on a real base.

Phase 1 already computed the percentage form of this and it is worth stating up front because
it splits the answer: dropping the top 1% takes expectancy from +10.4% to +9.0% per trade, but
cumulative dollars from $143,723 to $2,767. Percentage-wise the base survives; dollar-wise it
does not. The gap is an artefact of buying ONE CONTRACT per signal, so expensive contracts
dominate dollars. Both numbers are reported; neither alone is the answer.

--------------------------------------------------------------------------------------------
THE CONVICTION FINGERPRINT — and the trap it is designed to avoid.

If ~15 trades are the whole dollar edge, the valuable thing is recognising those setups when
they recur. But 15 in-sample points can be fitted perfectly by any sufficiently detailed rule,
and such a rule is worthless. So:

  * The fingerprint is derived ONLY on the FIRST time half.
  * It is then applied, unchanged, to the SECOND half, which did not inform it.
  * It ships ONLY if it clears the gate below on that held-out half.

If it does not replicate, the finding is "THE TAIL IS UNPREDICTABLE", and that is reported as a
result rather than papered over — because it directly caps how much anyone should size this. A
false conviction tier would be worse than none: it would invite exactly the aggressive sizing
the phase-1 verdict warns against.

--------------------------------------------------------------------------------------------
PRE-COMMITTED GATE for shipping a "scream-buy+" conviction tier:

  1. LIFT: among held-out trades the fingerprint flags, the rate of outsized winners must be at
     least MIN_LIFT times the unflagged base rate. A coin-flip rule has lift 1.0.
  2. SAMPLE: at least MIN_FLAGGED flagged trades in the held-out half. Below that, any lift is
     noise - the same reasoning as MIN_CLOSED_PER_BUCKET.
  3. EXPECTANCY GAP: flagged trades must beat unflagged by at least MIN_EXPECTANCY_GAP in
     expectancy per trade. Flagging winners is useless if the flagged set is not more profitable.
  4. NOT A SIZE PROXY: the fingerprint must beat a trivial control that flags the same NUMBER of
     held-out trades at random. Reported alongside, so a rule that merely selects more trades
     cannot look like skill.

An "outsized winner" is fixed in advance as a trade returning >= BIG_WIN_PCT, rather than "the
top N", so the definition does not move with the sample.

================================ RESULT (run after the above was committed) =================

ANSWER: (b), AND THE PREMISE OF THE QUESTION WAS PARTLY WRONG.

1. THE BASE SURVIVES WITHOUT THE TAIL. Excluding the top 15 dollar winners:

       all 1,540 trades   expectancy +10.42%/trade   cum $143,723   pf 1.30
       ex-top-15 (1,525)  expectancy  +8.96%/trade   cum   $2,767   pf 1.26

   Expectancy per trade barely moves. So the tail is upside on a real base, not the base
   itself - the pre-registered discriminator says (b), sizeable with discipline.

2. BIG WINNERS ARE NOT RARE. 473 of 1,540 trades (30.7%) returned >= +100%. The "15 trades"
   framing describes which trades produced DOLLARS, not which produced returns. Nearly a third
   of all trades doubled.

3. THE DOLLAR CONCENTRATION IS A POSITION-SIZING ARTEFACT, and this is the finding that
   changes the recommendation. Entry premium per contract spans 1,076x ($13 to $13,985). Buying
   ONE CONTRACT of a pre-split $3,000 AMZN next to one contract of a $40 bank guarantees that a
   handful of expensive names dominate the dollars regardless of signal quality. Re-weighting
   every trade to a fixed $1,000 of risk:

                              total     top-15 share   profit ex-top-15   top-3 names
       1 contract each     $143,723         98.1%            $2,767           76%
       fixed $1,000 risk   $160,461         42.0%           $92,998           34%

   Fixed-dollar sizing removes most of the concentration AND earns more. The phase-1 conclusion
   "too tail-dependent to size aggressively" was substantially an artefact of the 1-contract
   reporting convention, not a property of the strategy.

4. THE TAIL ITSELF IS UNPREDICTABLE - NO CONVICTION TIER SHIPS. The fingerprint was fitted on
   the first half (score >= 83.0, IV >= 21.6%, DTE >= 59) and applied to the held-out half:

       flagged big-win rate    28.07%
       unflagged base rate     29.05%
       random control          29.04%
       lift                     0.966   (gate: >= 2.0)     FAIL
       expectancy gap          -2.09pp  (gate: >= +20pp)   FAIL

   The rule performed slightly WORSE than both the unflagged base and a random control that
   flags the same number of trades. It fails every arm of the gate. No "scream-buy+" tier is
   built. Reporting this rather than shipping a plausible-looking tier is the whole point of
   fitting on one half: an in-sample fingerprint over 15 points would have looked convincing.

   Context for why it cannot work: 9 of the top 15 came from 2020 and the names are AMZN (5),
   GOOGL (5), TSLA (3). That is one regime and a few high-priced names, not a repeatable setup.

WHAT THIS MEANS FOR SIZING. The honest phase-1 line was "too tail-dependent to size
aggressively". The corrected line is: **size by fixed dollar risk, not by contract count.** Doing
so is what makes the edge broad rather than tail-dependent. Sizing by contracts is what created
the fragility, and it is also how a real account would accidentally take a 50x larger position
in AMZN than in BAC.

STILL TRUE, AND STILL LIMITING: expectancy decays +16.4% -> +4.4% across the held-out halves,
and 2022, 2023 and 2025 are negative. Robustness improves the fragility finding; it does not
make the edge strong.

"""
from __future__ import annotations

# What counts as a home run - fixed in advance, not "the top N of whatever we found".
BIG_WIN_PCT = 1.00          # >= +100% on the premium (the live target is +100%)

# Pre-committed gate for shipping a conviction tier.
MIN_LIFT = 2.0              # flagged big-win rate vs unflagged base rate
MIN_FLAGGED = 25            # held-out flagged trades needed before any lift is believable
MIN_EXPECTANCY_GAP = 0.20   # flagged must beat unflagged by 20pp of expectancy per trade


def big_win(row) -> bool:
    r = row.get("pnl_pct")
    return r is not None and r >= BIG_WIN_PCT


def summarize_tail(rows, top_n: int = 15) -> dict:
    """Where the dollar profit actually comes from, and what survives without it."""
    from .options_tracker import _stats

    ok = [r for r in rows if r.get("pnl_pct") is not None]
    by_dollar = sorted(ok, key=lambda r: r.get("pnl_dollars") or 0.0, reverse=True)
    top = by_dollar[:top_n]
    rest = by_dollar[top_n:]
    tot = sum((r.get("pnl_dollars") or 0.0) for r in ok)
    top_sum = sum((r.get("pnl_dollars") or 0.0) for r in top)
    return {
        "n": len(ok),
        "total_dollars": tot,
        "top_n": top_n,
        "top_n_dollars": top_sum,
        "top_n_share": (top_sum / tot) if tot else None,
        "overall": _stats(ok),
        "excluding_top_n": _stats(rest),          # THE discriminator
        "top_trades": [{"ticker": r["ticker"], "date": r["alert_ts"], "pnl_pct": r["pnl_pct"],
                        "pnl_dollars": r["pnl_dollars"], "score": r.get("score"),
                        "iv": r.get("iv"), "dte": r.get("dte"),
                        "delta": r.get("target_delta"), "exit": r.get("exit_reason")}
                       for r in top],
    }


def fit_fingerprint(rows) -> dict:
    """Derive a conviction rule from ONE half only. Deliberately coarse: three thresholds.

    A richer rule would fit the in-sample winners better and generalise worse, which is exactly
    the failure this is guarding against. Thresholds are medians of the big winners, so the rule
    is 'looks like the winners did' rather than a tuned boundary.
    """
    import statistics as st

    wins = [r for r in rows if big_win(r)]
    if len(wins) < 10:
        return {}

    def med(key):
        vals = [r.get(key) for r in wins if r.get(key) is not None]
        return st.median(vals) if vals else None

    return {"min_score": med("score"), "min_iv": med("iv"), "min_dte": med("dte")}


def matches(row, fp: dict) -> bool:
    """Apply the fingerprint. Missing inputs fail closed - never flag on absent evidence."""
    if not fp:
        return False
    for key, field in (("min_score", "score"), ("min_iv", "iv"), ("min_dte", "dte")):
        thresh = fp.get(key)
        if thresh is None:
            continue
        v = row.get(field)
        if v is None or v < thresh:
            return False
    return True


def evaluate_fingerprint(train_rows, test_rows, seed: int = 0) -> dict:
    """Fit on train, judge ONLY on test, against the pre-committed gate."""
    import random

    from .options_tracker import _stats

    fp = fit_fingerprint(train_rows)
    if not fp:
        return {"ok": False, "reason": "too few big winners in the training half"}

    flagged = [r for r in test_rows if matches(r, fp)]
    unflagged = [r for r in test_rows if not matches(r, fp)]
    if not flagged or not unflagged:
        return {"ok": False, "reason": "fingerprint flagged everything or nothing", "fingerprint": fp}

    f_rate = sum(big_win(r) for r in flagged) / len(flagged)
    u_rate = sum(big_win(r) for r in unflagged) / len(unflagged)
    lift = (f_rate / u_rate) if u_rate > 0 else None
    f_stats, u_stats = _stats(flagged), _stats(unflagged)
    gap = ((f_stats["expectancy_pct"] or 0) - (u_stats["expectancy_pct"] or 0))

    # Control: flag the same NUMBER of test trades at random, so "selects more trades" cannot
    # masquerade as skill.
    rnd = random.Random(seed)
    ctrl_rates = []
    for _ in range(200):
        samp = rnd.sample(test_rows, min(len(flagged), len(test_rows)))
        ctrl_rates.append(sum(big_win(r) for r in samp) / max(len(samp), 1))
    ctrl = sum(ctrl_rates) / len(ctrl_rates)

    passed = (lift is not None and lift >= MIN_LIFT
              and len(flagged) >= MIN_FLAGGED
              and gap >= MIN_EXPECTANCY_GAP
              and f_rate > ctrl)
    return {
        "ok": True, "fingerprint": fp,
        "n_flagged": len(flagged), "n_unflagged": len(unflagged),
        "flagged_big_win_rate": f_rate, "unflagged_big_win_rate": u_rate,
        "random_control_rate": ctrl, "lift": lift,
        "flagged_expectancy": f_stats["expectancy_pct"],
        "unflagged_expectancy": u_stats["expectancy_pct"],
        "expectancy_gap": gap,
        "gate": {"min_lift": MIN_LIFT, "min_flagged": MIN_FLAGGED,
                 "min_expectancy_gap": MIN_EXPECTANCY_GAP},
        "passed": passed,
    }