# PREREG — the path study (options bot, 2026-08-10)

Committed **before any table was computed**. Stage 2's arm set is committed here too, before
Stage 1's numbers exist, so the arms cannot be chosen to suit them.

---

## 0. What this is, and the caveat that travels with every line of it

**The options ENTRY signal is dead.** R2 measured the real book at **+3.41%/trade against a
five-seed random-entry control's +10.06%** — gap **−6.65pp**, date-block CI95
[−11.92pp, −2.13pp], paired name-year sign test **z −4.903**. That verdict stands and nothing
here reopens it.

So **nothing found in this study is a tradeable-edge claim.** An exit rule cannot rescue an
entry that subtracts value; the most a better exit can do is lose less of what the *underlying*
was going to do anyway, and O23 already measured that **half of any exit's P&L difference is
just the underlying**. What this study can legitimately produce is two things:

1. **Paper-book policy.** The paper track has to exit on *some* rule; if the paths say the
   inherited one is structurally bad, changing it on the PAPER book is a housekeeping decision,
   not a claim.
2. **Structural knowledge.** How these contracts actually behave — how deep they dig before they
   die, whether a −40% option comes back, how long a winner takes. That is worth knowing whether
   or not anything is ever traded on it.

Any sentence from this study that reads as "we found an edge" is a misquote of it.

## 1. The book, and its provenance

* **Signal book:** `data/options_universe/state_r2_corrected.pkl` — the R2-corrected book,
  **3,885 trades / 186 names**, banked 2026-08-05. The `state.pkl` book is the void
  pre-correction 3,042-trade one and is not used.
* **Controls:** `control_r2_seed{0..4}.pkl`, the five random-entry seeds. Pooled wherever a
  control comparison is drawn (R2's standing rule: five seeds minimum).
* **Marks:** the frozen chains, `data/options_freeze/R2_CORRECTED_2026-08-08/chains.pkl.gz`
  (2,870,811 rows, manifest `n_trades: 3885`) and `R2_CONTROLS_2026-08-08/` for the seeds.
  Frozen 2026-08-08 against the book banked 2026-08-05, so the marks cannot drift under the
  study.
* **NOT USED, and why:** `data/options_exitlab/paths.pkl` (O1's captured paths) covers only
  **1,099 of the 3,885 banked trades — 28.3%** — and carries 2,020 paths the book does not.
  It is a different trade set. Rebuilding from the freeze is what makes this study about the
  frozen book rather than about a 28% slice of it.

## 2. Definitions, fixed before computing

Taken from `options_exitlab.apply_policy` rather than re-derived, so a path level means exactly
what the shipped simulator means by it:

* **mark(day)** = `options_fill.fill_price(Quote(bid, ask), "sell", aggression=1.0)` — the
  sell-side fill. This is the price a stop would actually get, and it is what the simulator
  tests its levels against. Not mid.
* **ret(day)** = `mark / entry_fill − 1`, with `entry_fill` = the banked `entry_premium`.
  Gross of commission, premium-relative — the same unit as "+100% target / −50% stop".
* **Days kept:** every frozen quote day strictly after the alert date and on or before expiry
  for which `options_fill.exit_reject_reason(q) is None`. This is the post-B2 rule the banked
  book was built under; using the pre-B2 rule would silently delete bad-quote days and let
  losers ride.
* **Final outcome** = the banked trade's `exit_reason` and `pnl_pct`. Not a re-simulation.
* **MAE** = the minimum `ret` over days from entry **up to and including the banked exit date**.
* **Touch of −X%** = the first day with `ret ≤ −X`.
* **Recovery** is reported as TWO separate quantities, because they answer different questions
  and conflating them is how a recovery rate gets overstated:
  * `P(back to ≥ 0 | touched −X%)` — did it ever get back to breakeven, and
  * `P(reach +100% | touched −X%)` — did it go on to make the target.
  Both measured on the **full contract life, ignoring the shipped exit**, which is the
  counterfactual the question is asking about.
* **DTE remaining at the touch** = `(expiry − touch_date).days`, bucketed
  `≤7 / 8–21 / 22–45 / >45`.
* **Time to target** = days from entry to the first day with `ret ≥ 1.0`, reported in calendar
  days and as a fraction of `dte0`.
* **Post-target continuation** = for trades whose full path reaches +100% with **more than half
  of `dte0` still remaining at that moment**, the subsequent path: max further `ret`, whether it
  reached +200%, and whether it fell back below +100% and below 0.

**THE COUNTERFACTUAL IS HYPOTHETICAL AND MUST BE LABELLED.** A trade the shipped policy stopped
at −50% did not actually continue; the post-exit marks say what the *contract* did, not what a
*position* did. That is exactly the question being asked, but it is not a realised P&L.

**SETTLEMENT.** A contract stops being quotable when its bid hits zero, which is precisely when
it is dying, so marking it at its last usable quote books a price from before the final decay —
O1 measured that on hold-to-expiry the stale mark is higher than true settlement in **94.7%** of
cases. This study therefore reports, for every continuation statistic, the share of paths that
fall through to unquotable, and never averages a stale mark into a continuation figure without
saying so.

## 3. Stage 1 is descriptive. It has no verdict and no arms.

No rule is scored, no parameter is chosen, nothing is compared to a bar. Tables only.
**Zero trials; options `N` does not move for Stage 1.**

**STOP RULE, committed now:** if Stage 1 shows no structure — no touch level whose recovery rate
separates materially from the base rate, no DTE dependence, no post-target continuation
asymmetry — **the tables are published and Stage 2 does not run.** A descriptive null is a
complete answer. "Material" is fixed here as: some cell of the recovery table differing from the
pooled base rate by **≥ 10 percentage points on ≥ 100 trades**, or the post-target continuation
showing **≥ 10pp** difference between "kept going" and "gave it back".

## 4. Stage 2 arms — committed now, before Stage 1's numbers exist

Runs ONLY if Stage 1 clears §3. Every arm is diffed against O1's tested set
(`shipped, tp50, tp75, tp150, tp200, tp_none, sl30, sl70, sl_none, time25, time75, time100,
dte21, dte14, dte7, trail25, trail35, trail50, ratchet35, run_winners, tp100_only`) and **no
rejected arm re-runs**. Conventional parameters, no tuning, no grid.

| arm | family | definition | not already tested because |
|---|---|---|---|
| `be50` | A | stop to breakeven (`sl = 0`) once `ret ≥ +0.5`; else shipped | `ratchet35` trails 35%, never moves the stop to entry |
| `trail50_after100` | A | shipped, plus trail 50% once `ret ≥ +1.0` instead of closing | `trail50` has no arming threshold; `run_winners` arms at +50% and drops the stop |
| `step50` | A | ratchet the stop up one +50% step behind the peak | no stepped arm exists |
| `sl_by_dte` | B | stop −40% while DTE > 21, −60% at DTE ≤ 21; shipped otherwise | all O1 stops are constant |
| `time_cond25` | B | at the half-DTE time stop, close ONLY if `ret < +0.25`; else hold to expiry | `time25/75/100` are unconditional |
| `extrinsic20` | C | exit when extrinsic value < 20% of current premium | no state-based arm tested |
| `delta85` | C | exit when `\|delta\| > 0.85` (ties to O21) | as above |
| `ivcrush30` | C | exit when IV falls > 30% day-over-day | as above |
| `stock_stop` | D | close when the UNDERLYING is −8% from its entry close | O23 measured the decomposition, tested no rule |
| `gap_open` | D | close on the open after an overnight underlying gap beyond ±5% | as above; V5 recorded a −20% gap fill |
| `half_at_100` | E | sell half at +100%, remainder rides with the stop at entry | O1 has no partial-exit arm |
| `escalate_fast` | F | `ret ≥ +1.0` before 25% of `dte0` elapsed → trail 35% instead of closing | `run_winners` has no elapsed-time condition |
| `clean_runner` | F | never below −10% by half DTE → raise the target to +150% | no path-conditional target exists |

**Excluded by scope, routed not run:** earnings-timing arms → **O17**; sizing → **O12**.
Observations about either are reported, never tested here.

**Cost:** 13 arms, charged to **options `N`** on landing, whatever the verdicts.

## 5. The wall

* **Selection half / measurement half.** The book is split by date at its median alert date.
  Hypotheses — which arms look promising — may be inspected only on the DECIDE half; every
  published verdict is measured on the other half. Both directions are run
  (decide-early/measure-late and decide-late/measure-early) and **a disagreement between
  directions is a NULL**, per session 7's LOO precedent.
* **Random-entry control, five seeds, pooled.** Every arm is scored on the control books too. An
  arm that improves the control as much as the signal has found something about *options*, not
  about *this book* — which is O1's own gate and the reason O1 rejected everything.
* **Date-block clustered inference.** Calendar months resampled together
  (`options_stats`), never trade-level bootstrap: R3 measured the design effect at **2.2121**
  against a shuffled-null p95 of 1.2037, so trade-level intervals are optimistically narrow by
  **√2.2121 = 1.487×**.
* **The calibrated bars, not the conventions.** X7's floors where they apply; O1's own
  `MIN_EXPECTANCY_GAIN = 0.10` and `MAX_PBO = 0.5` for policy comparison, plus FDR at q = 0.1
  across the arm family.
* **Ambiguous = NULL.** Stated before the run, as always.

## 6. Pre-registered expectation, written down before Stage 1 ran

Because this project's record is that its directional guesses are wrong more often than right,
and writing them down is the only thing that keeps that measurable:

* Stage 1 **shows structure**, 75/25 — specifically that recovery from a −50% touch is *low*
  and falls further as DTE shrinks. If so the shipped stop is roughly in the right place.
* Stage 2, if it runs, **rejects every arm**, 70/30 — the same outcome as O1, for the same
  reason O23 gave: the underlying dominates and the entry is dead.
* The single most likely survivor, if any: `time_cond25`, 20% — the unconditional half-DTE time
  stop is the crudest part of the inherited policy.
