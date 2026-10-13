# DECL — F-22: THE RANDOM-DAY TWIN OF F-21 (short book)

**DECLARED, NOT ARMED. NO FILL IS PLACED AND NO TRIAL IS BOOKED** — the harness charges at the
**first verdict read**. Committed **ALONE** before any fill exists. **Paper only; `O11` binds.**

**ACCEPTED from the Frontier Scout's `DECL_DRAFT_f22_dip_csp_random_twin.md` (`91ffd54`) with two
executor amendments, both made BEFORE any fill.** The draft's reasoning is adopted whole: this
book exists because **`DECISIONS.md` 2026-10-12 clause (b) is a REQUIREMENT and not a robustness
check** — without a twin, F-21 can only ever report *"the trade made money"*, which `R2`
established is a different claim from *"the timing mattered"*, having measured a book with
**positive expectancy** losing to random entry by **−5.0640pp/trade**.

---

## THE TWO AMENDMENTS

**B1 — THE TWIN INHERITS F-21's CLOCK, BECAUSE A TWIN ON A DIFFERENT CLOCK IS NOT THE SAME
TRADE.** F-21 enters at the cadence of the recorded `dip_healthy` series, which today is **weekly
rather than daily** (the fleet cycle deliberately does not run the dip screen). **So this book's
draw is evaluated on exactly the sessions F-21's source was recorded on, and on no others.**
Drawing daily while the arm can only enter weekly would hand the twin roughly **five times** the
entry opportunities and make its fills a **biased superset** of the arm's — which is precisely the
coverage-mismatch defect **`MB1-SEL` was VOIDED for**, where the confound ran **twice the size of
the effect and in the same direction**.

**B2 — THE SAME REFUSAL, SO THE TWIN CANNOT DRIFT AHEAD OF THE ARM.** The draw refuses whenever
F-21's entry rule refuses — fewer than **20** recorded rows, or a latest row more than **5**
sessions stale. **Neither book's verdict may be read without the other's, and that is now enforced
at the SOURCE rather than at read time.**

Everything else is the draft's and unchanged: the deterministic salted draw, the wider name pool,
the threshold calibrated to F-21's own fill rate and re-stated with it, the accepted-and-measured
contamination, and the delta argument carried **verbatim** from F-21 because a twin arguing
differently about its own strike rule would not be the same trade.

---

## MACHINE-CHECKABLE DECLARATION

```json
{
  "assignment_model": "at expiry per moneyness, S3-I3 assignment_at_expiry",
  "book": "f22_dip_csp_random_twin",
  "concurrency_cap": 10,
  "domain": "options",
  "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
  "entry_rule": "On each session for which F-21's `dip_healthy` series carries a recorded row, and on no others, draw deterministically: enter name T if sha256(F22_SALT || book || ticker || session_date) mod 10**9 < p * 10**9, where p is the threshold declared below and re-stated at launch alongside F-21's own fill rate. THE DRAW READS THE CALENDAR AND THE TICKER AND NOTHING ELSE - no drawdown, no health score, no volatility, no price-derived quantity of any kind - so the timing is uncorrelated with the dip signal by construction and any reader can reproduce every entry this book ever made from this declaration alone. The name pool is the whole optionable point-in-time $10B tier, deliberately WIDER than F-21's healthy list so there is something to pair with. Skip any name already held or already entered this quarter. A draw that lands on a day the name IS in a healthy dip is NOT excluded - excluding it would make this a non-dip book and turn the comparison into dip-versus-no-dip rather than dip-timing-versus-random-timing - and the share of fills that did so is a REQUIRED reported field. The rule REFUSES on a thin or stale `dip_healthy` series exactly as F-21 does.",
  "hypothesis_class": "cost",
  "margin_method": "cash_secured_put",
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money.",
  "records_schema": [
    "menu_depth",
    "density_percentile",
    "landed_on_healthy_dip_day",
    "healthy_series_rows",
    "healthy_series_last_date"
  ],
  "return_denominator": "secured_cash",
  "sells_premium": true,
  "side": "short",
  "sizing": "equal secured cash per position, identical to F-21; the skip reason is recorded so an affordability skip is never read as a concurrency skip (MB3)",
  "spot_basis": "as_traded",
  "structure": {
    "arming_precondition": "DECLARED AND NOT ARMED, on F-21's precondition and not a weaker one. The draw refuses whenever F-21's entry rule refuses - fewer than 20 recorded `dip_healthy` rows, or a latest row more than 5 sessions stale - so the twin can never accrue fills the arm had no chance to accrue. Neither book's verdict may be read without the other's, and that is enforced at the source rather than at read time.",
    "cadence_amendment": "EXECUTOR AMENDMENT, 2026-10-13, BEFORE ANY FILL, AND IT IS F-21's A2 CARRIED ACROSS BECAUSE A TWIN THAT RAN ON A DIFFERENT CLOCK WOULD NOT BE THE SAME TRADE. F-21 enters at the cadence of the recorded `dip_healthy` series, which today is weekly rather than daily because the fleet cycle deliberately does not run the dip screen. THIS BOOK'S DRAW IS EVALUATED ON THE SAME SESSIONS F-21's SOURCE WAS RECORDED ON, and on no others. Drawing daily while the arm can only enter weekly would hand the twin five times the entry opportunities and make its fills a biased superset of the arm's - which is the coverage-mismatch defect MB1-SEL was VOIDED for, where the confound ran twice the size of the effect and in the same direction.",
    "delta": 0.25,
    "delta_leg": "solved on the PUT leg, V6-OPT's convention",
    "dte": 37,
    "dte_rule": "nearest 37, restricted to 30-45; ties -> longer",
    "exit": "hold to expiry, no exits",
    "max_stale_sessions": 5,
    "min_healthy_rows": 20,
    "pairing": "At read time the clause-(b) statistic uses only (name, calendar-quarter) cells in which BOTH F-21 and F-22 hold a fill -- V6-OPT's (name, year) matching done forward at a finer grain. Unmatched fills on both sides are COUNTED AND REPORTED and excluded from the paired statistic. Reporting unpaired means as the comparison is a void condition.",
    "records_schema_note": "`landed_on_healthy_dip_day` is the contamination this book accepts rather than filters, measured per fill. F-2 and F-19 ride as recorded fields per the fleet review. None of the five collides with the 30 base RECORD_COLUMNS.",
    "right": "put",
    "strike_selection": "delta",
    "v6opt_argument": "CARRIED VERBATIM FROM F-21, because a twin that argued differently about its own strike rule would not be the same trade and the comparison would measure the difference in the argument. CONCEDED, NOT DODGED: V6-OPT's autopsy is correct that a delta target sets the strike from the name's own volatility and so equalises assignment by construction -- 25.303% assignment on healthy dips against 25.727% on unhealthy, a 0.43pp gap, where V6-B had measured a real further-20% difference of 2.797pp on those same covered rows. A RISK SIGNAL CANNOT PAY THROUGH A DELTA-TARGETED STRIKE. Neither book carries a risk signal. DECISIONS.md 2026-10-12 judges an options strategy as its own system and its three pass clauses are each unobstructed by a delta target; the only condition it obstructed has been withdrawn by the owner. For THIS book the argument is stronger still: its entry timing reads nothing price-derived at all, so there is no risk signal present even in principle for a strike rule to neutralise. And the alternative is measured to be worse on a gate the pair must pass -- SELL-PREMIUM's K3 fired at 8.900816 years of premium against a 6.0 bar on a fixed 0.90-moneyness rule, which collects 0.7778% of strike at a median 44 DTE = 4.4545%/yr against V6-OPT's 2.550% at a median 32 DTE."
  },
  "trial": {
    "charged_at": "first_verdict_read",
    "domain": "options"
  },
  "universe": "the whole optionable point-in-time $10B tier -- deliberately WIDER than F-21's healthy-dip list so that pairable cells exist; the pairing at read time discards the rest",
  "verdict_grammar": [
    "PAYS",
    "BLEEDS",
    "CANNOT-TELL(horizon)"
  ],
  "verdict_horizon": {
    "alpha": 0.05,
    "earliest_honest_read": "About 68.8 years at 2.0 fills/month (1652 fills) FOR THIS BOOK'S OWN STANDALONE METER -- which is NOT the horizon of Don's clause (b), and conflating the two would be a real error. Clause (b) is a PAIRED comparison between two books holding the same structure on overlapping names, and MB8 measured a paired se of 0.1106pp where an unpaired difference between two different books was 0.9354pp, 8.5x tighter. So clause (b) may resolve long before either standalone meter. THE PAIRED se IS MEASURED AT READ TIME AND NEVER BORROWED -- not from MB8, not from F-21, not from V6-OPT (MB8's own rule: an se may not travel across perturbation sizes). The read reports the measured paired se and its 80%-power MDE as (crit + 0.84) * se (MB22). AND THE FIVE-SEED FLOOR IS NOT AVAILABLE FORWARD: one live twin is one draw, R2 showed a single control seed can flip a verdict, so the forward comparison is structurally weaker than V6-OPT's backtested five-seed control on exactly that axis, and the paired sign test across many (name, quarter) cells is what partly replaces it.",
    "expected_fills_per_month": 2.0,
    "expected_fills_provenance": "MATCHED TO F-21 BY CONSTRUCTION and re-stated with it at launch. A twin that fills ten times as often is not the same trade sampled differently; it is a different book whose paired cells are a biased subset of its own fills.",
    "fills_needed": 1652,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED; the same derivation reproduces F-10's declared 306 and F-11's declared 138 exactly (MB15). Fixed-n analogue at crit 1.96: 1050.",
    "min_effect": 0.5671,
    "min_effect_derivation": "F-21's, derived the same way: DECISIONS.md 2026-10-06 quotes a candidate's expected return at HALF its backtested size (McLean-Pontiff), and half of V6-OPT's measured +1.1342 pp/trade is 0.5671. Identical on both books so the two standalone meters are commensurable.",
    "power_gate_note": "Anytime-valid, so the boundary IS the threshold at every n and fills_needed is where it falls to the declared minimum rather than where a verdict becomes possible. Both vocabularies are on the face. No X7 or CORRECTED-FLOORS floor is quoted -- none is calibrated for a per-trade return on secured cash, nor for a paired within-book difference (V2G, R1-VAR) -- and every critical value either book reports is LABELLED UNCALIBRATED.",
    "rho": 3.0,
    "sigma": 6.5633,
    "sigma_may_only_be_raised": true,
    "sigma_provenance": "MEASURED, and it is the MAXIMUM across V6-OPT's five C-C control seeds (5.8881 / 6.0043 / 5.4852 / 6.5633 / 6.0772 pp). The maximum rather than the mean because track_meter's rule is that sigma may only ever be RAISED. It is THIS structure's own control SD and NOT F-21's 5.047 -- borrowing that would be the MB8 error, and the measurement says random-timing is genuinely noisier.",
    "years_to_horizon_at_projected_rate": 68.83
  }
}
```
