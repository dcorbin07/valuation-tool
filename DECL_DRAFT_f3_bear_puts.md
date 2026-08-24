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
