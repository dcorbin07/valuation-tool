# DECL DRAFT — F-3: BEAR-SCANNER PUTS (fleet book #2)
## The live bearish engine's first options arm. Tag: [VIRGIN — no register has ever consumed the bear scanner]

**To be committed ALONE by the options-bot lane before first fill.**

**Hypothesis:** the live product's bearish-signal verdicts (computed daily, consumed by
nothing) identify names whose forward path pays a put. Declared long-vol, long-direction-down
— it faces no short-vol closure; its nearest corpses are `R2` (a DIFFERENT engine's alerts
failed as long-call entries — cited, not inherited: this is a different signal, opposite
side) and `U1` (score→calls — the bear engine is not the composite).

**Entry rule (frozen):** each trading day, take the scanner's top-N bearish verdicts (N=3)
among optionable names not already held by this book; skip names with a scheduled event
inside the holding window ONLY if the scanner's own signal names the event (no silent event
filtering — `F-4` owns event-avoidance; this book takes the signal as it comes).

**Structure:** buy the listed put nearest **0.85× as-traded spot** (moneyness-fixed;
`V6-OPT`-autopsy honored), expiry nearest **60 DTE**; hold to expiry or scanner-reversal
(the reversal exit is part of the frozen rule: exit if the scanner flips the name to
non-bearish for 3 consecutive sessions). Entry at ask via the F-1 randomizer.

**Universe/sizing:** optionable scanner hits; equal premium per position; concurrency cap
10; cash never exceeds the sandbox book's allocation. `O11` binds; sandbox only.

**Records:** scanner score and rank at entry, the full quote pair, the event-flag state,
exit reason. Schema per the harness.

**Verdict horizon:** est. 10–20 qualifying signals/month (descriptive projection from the
scanner's recent firing rate — re-stated at launch from a 30-day count); **30 fills ≈ one
quarter**. Meter: mean per-trade return on premium vs 0, anytime-valid; minimum effect of
interest fixed now at **+15pp/trade** (long-OTM-put books bleed theta — anything smaller is
indistinguishable from a slow bleed with lucky timing, and the declaration says so with the
`power_gate` line at both vocabularies filled at commit time).

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon), with the D9 cost caveat quoted.

**Trial:** 1, options, at first verdict read.

**Void:** delta-targeted strikes; discretionary exits; any real-money echo.

---

## MACHINE-CHECKABLE DECLARATION — added at ACCEPTANCE by the options-bot lane, 2026-08-24

**The prose above is the scout's, preserved verbatim.** It carries the citations and the
corpses this book must out-select, and none of it is edited. What follows is the same book in
the form `valuation/edge/fleet.py` can ENFORCE: prose cannot be validated, and the harness
refuses a declaration it cannot read. Converting is part of acceptance, not a rewrite.

**TWO FIELDS DIFFER FROM THE DRAFT, DELIBERATELY, AND BOTH ARE HARDER.**

1. **`fills_needed` IS DERIVED, AND IT IS NOT 30.** Every draft wrote "30 fills". Thirty is a
   round number, not a derivation. The figure below is the smallest `n` at which
   `track_meter.boundary(n, sigma, rho, alpha)/n` falls to this book's OWN declared minimum
   effect — the boundary the harness actually uses. Across the fleet it runs **93 to 4,563**,
   so the drafts were optimistic by 3x to 40x. The runbook's §3 exists for exactly this:
   *"the number goes on the declaration so nobody reads a six-month book at six weeks."*
2. **`sigma` is a PRIOR unless it says MEASURED**, and `track_meter`'s rule binds: it may only
   ever be **RAISED**, never lowered. `book_meter` reports `sigma_breach` when realised
   volatility exceeds it, and a breach means the band was too narrow, not that the book did
   well.

```json
{
  "sells_premium": false,
  "side": "long",
  "book": "f3_bear_puts",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Each trading day: score the optionable universe with valuation.intraday.bearish.bearish_technical(bars) -- the shipped per-name bearish score -- and take the top 3 by score among names not already held. Skip a name only if the scanner's own signal names a scheduled event; no silent event filtering (F-4 owns event-avoidance).",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.85,
    "right": "put",
    "dte": 60,
    "exit": "hold to expiry, or exit if the scanner flips the name non-bearish for 3 consecutive sessions (frozen)"
  },
  "universe": "optionable names with >=50 sessions of bars",
  "sizing": "equal premium per position",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 15.0,
    "min_effect": 15.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 420,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "2.3 years at the projected 15.00 fills/month (420 fills). The draft said 30 fills; 30 is a round number and this is the derivation.",
    "years_to_horizon_at_projected_rate": 2.33,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 298, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "PAYS",
    "BLEEDS",
    "CANNOT-TELL(horizon)"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```

---

## AMENDMENTS — added at ARMING, 2026-08-24, options-live lane

**A NEW SECTION, NEVER AN EDIT** (`PT-AMEND1`). Everything above this line is untouched.
**They land before this book's first fill, which is mechanical rather than tidy:**
`verify_chain` anchors on the declaration's CONTENT hash, so amending a declaration that
already has records breaks its own chain at row 0 and reads as tampering. F-3 has zero
records.

### Amendment 1 — the tie-break was not stated

**The frozen rule says *"take the scanner's top-N bearish verdicts (N=3)"* and never says what
happens when two names score equally.** The bear score is rounded to one decimal, so ties are
ordinary rather than exotic. An unstated tie-break is a non-reproducible rule, and a
pre-registration cannot be one.

**Resolved: ALPHABETICAL, after score descending.** It is the fleet's own convention — F-4,
F-10, F-13, F-14, F-15, F-18 and F-20 all state it explicitly — so this imports a sibling's
stated rule rather than inventing one. Nothing about it depends on an outcome.

### Amendment 2 — "nearest 0.85× spot, expiry nearest 60 DTE" does not say which binds first

**The two orders pick different contracts, and not marginally.** Strike-first can land on an
expiry weeks away from 60 DTE because some far month happens to list a strike a few cents
closer to target; tenor is then whatever falls out.

**Resolved: EXPIRY FIRST, THEN STRIKE within that expiry.** The declared 60-DTE tenor is the
parameter this book's theta bleed is measured against — a long OTM put book's whole cost
structure is a function of tenor — so a rule that lets tenor drift to protect a few cents of
moneyness is measuring something the declaration did not register. **The strike target is
unchanged at 0.85× as-traded spot, and no delta is solved anywhere** (this book's own void
condition, honouring `V6-OPT`'s autopsy).

### Amendment 3 — "equal premium per position" has no denominator

**The declaration says *"equal premium per position; concurrency cap 10; cash never exceeds
the sandbox book's allocation"* and states NO allocation figure anywhere.** So the sizing rule
cannot be executed as written: there is no budget to divide.

**Resolved: ONE CONTRACT per position, recorded as such, until an allocation is declared.**
**This is measurement-neutral rather than a silent sizing choice, and that is checkable:** the
book's own verdict statistic is *"mean per-trade return on premium"*, which is invariant to
quantity. Sizing therefore cannot move this book's verdict in either direction. It would
matter to a survivability question, and `O11` already binds that — nothing here licenses one.

### NOT an amendment — the event-skip clause is inert, BY MEASUREMENT

The frozen rule skips a name *"ONLY if the scanner's own signal names the event"*. **Measured:
neither `bearish_technical` nor `signals.evaluate_bearish` emits any label naming a scheduled
event** — the vocabulary is trend, death cross, MACD, RSI, Bollinger, new-low and put-heavy
flow, and nothing else. **So the clause never fires, and that is the declaration working as
intended rather than a gap:** it exists to stop silent event filtering, and F-4 owns
event-avoidance.

This is pinned as a measurement rather than assumed. `tests/test_fleet_f3.py` derives the
label vocabulary from the two source files and fails if any of them ever begins naming an
event — at which point the clause becomes live and someone has to decide what it means,
rather than discovering years later that a filter had quietly switched itself on.
