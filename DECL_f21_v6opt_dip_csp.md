# DECL — F-21: THE V6-OPT PUT-SELLING BOOK (short book)

**DECLARED, NOT ARMED. NO FILL IS PLACED AND NO TRIAL IS BOOKED** — the harness charges at the
**first verdict read**, and this file reads nothing. Committed **ALONE** (exactly one file in its
commit, `declaration_commit`'s own rule) before any fill exists. **Paper only; `O11` binds;
nothing here licenses real money.**

**ACCEPTED from the Frontier Scout's `DECL_DRAFT_f21_v6opt_dip_csp.md` (`8e7d4c7`) with three
executor amendments, all made BEFORE any fill.** Everything not named below is the draft's and is
not restated: the delta argument (conceded, not dodged), the sizing and crash arithmetic, the
horizon derivation and its `fills_needed` of 933, and Don's 2026-10-12 pass rule.

---

## THE THREE AMENDMENTS

**A1 — THE ENTRY SOURCE DID NOT EXIST, AND THAT IS MEASURED RATHER THAN SUSPECTED.** The draft
enters on *"the live dip detector's HEALTHY list"*. `fleet_history.SERIES` held exactly three
streams — `iv60_atm`, `dip_rejects`, `alert_count` — and **`dip_rejects` is the COMPLEMENT of this
book's entry population.** So the names F-21 enters on were recorded **nowhere**, and *"first
appearance on that list this quarter"* could not be evaluated against anything. **The book would
have armed and qualified nobody** — `RULE_ARMED_NEVER_FIRES`, which the harness itself calls
*"indistinguishable in the records from a quiet market"*. A **`dip_healthy`** series is added and
recorded from the **same screen the two existing callers already pay for**; no new screen runs
anywhere.

**A2 — THE CADENCE IS THE BINDING CONSTRAINT AND IT EXPLAINS THE SCOUT'S OWN MEASUREMENT.** The
fleet cycle **deliberately does not run the dip screen** (its own comment prices it against the
runner budget), so the only callers are `scan_worker.run_weekly` and
`POST /admin/record-dip-rejects`. **That is why `dip_rejects` reads 6 days against `alert_count`
and `iv60_atm` at 24 — roughly the weekly-to-daily ratio.** It is a **cadence mismatch between the
recorder and the consumer**, not an intermittent fault, and no amount of arming fixes it.
Consequently the draft's *"within 2 sessions of first appearance"* **is not achievable today** and
is replaced by first appearance evaluated **at the series' own cadence**.

**A3 — DECLARED AND NOT ARMED, WITH THE PRECONDITION MECHANICAL RATHER THAN REMEMBERED.** The
entry rule **refuses by name** on a series carrying fewer than **20** rows or whose latest row is
more than **5** sessions stale, and records the reason. **A thin or stale source is then reported
as a thin or stale source and never as a quiet market** — which is the whole of the scout's
correction, enforced in code instead of in a footnote.

**AND F-2 AND F-19 ARE FOLDED IN AS RECORDED FIELDS**, per the fleet review: both declarations say
they are conventions rather than books, and their per-trade meters imply 47.5- and 21.2-year
horizons for objects that hold no positions. `menu_depth` and `density_percentile` ride on every
fill here instead. None of the four schema entries collides with the 30 base `RECORD_COLUMNS`.

---

## MACHINE-CHECKABLE DECLARATION

```json
{
  "assignment_model": "at expiry per moneyness, S3-I3 assignment_at_expiry",
  "book": "f21_v6opt_dip_csp",
  "concurrency_cap": 10,
  "domain": "options",
  "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
  "entry_rule": "On each fleet cycle, read the RECORDED dip-detector HEALTHY series `fleet_history.read('dip_healthy')` -- the names the live screen KEPT, published by `valuation.web.dip.screen_snapshot` and READ here, never recomputed (F-11's convention). A name QUALIFIES on the first recorded row of the current calendar quarter in which it appears and did not appear in the immediately preceding recorded row; that is FIRST APPEARANCE evaluated at the cadence the series actually has. Restrict to names whose market cap is >= $10B at the entry date (point-in-time, never ever-in-tier) and that are optionable. Skip any name already held, or already entered this quarter. If more qualify than the cap allows, take the largest by market cap; alphabetical tie-break. THE RULE REFUSES RATHER THAN STARVES: if the series carries fewer than MIN_HEALTHY_ROWS recorded rows, or its most recent row is older than MAX_STALE_SESSIONS sessions, the book enters NOTHING and records the reason -- so a thin or stale source is reported as a thin or stale source and never as a quiet market.",
  "hypothesis_class": "edge",
  "margin_method": "cash_secured_put",
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money.",
  "records_schema": [
    "menu_depth",
    "density_percentile",
    "healthy_series_rows",
    "healthy_series_last_date"
  ],
  "return_denominator": "secured_cash",
  "sells_premium": true,
  "side": "short",
  "sizing": "equal secured cash per position; the skip reason is recorded so an affordability skip is never read as a concurrency skip (MB3)",
  "spot_basis": "as_traded",
  "structure": {
    "arming_amendment": "ARMING AMENDMENT, 2026-10-13, BEFORE ANY FILL. This book IS NOW ARMED, and the precondition above is NOT weakened - it is enforced in CODE instead of by withholding the entry rule. Don's instruction of 2026-10-13 permits arming before the series is ready ON ONE CONDITION: that a refusal for a thin source is recorded as its own state and can never read as a quiet market. That condition is met and tested: `fleet_books._f21_source_gate` writes a named refusal row onto this book's own stream - DIP_HEALTHY_ABSENT when the stream does not exist, DIP_HEALTHY_UNFIT when it is thinner than `min_healthy_rows` or staler than `max_stale_sessions` - and returns no candidates. THAT IS STRICTLY MORE VISIBLE THAN THE PREVIOUS ARRANGEMENT: an unarmed book reports ARMED_NO_ENTRY_RULE and writes NOTHING, so the day the data became ready nobody would have been told. Armed, the book starts BY ITSELF on that day with no further human action. `min_healthy_rows` 20 and `max_stale_sessions` 5 are UNCHANGED, as is every other field; what changed is who enforces them. Measured at the time of amendment: the `dip_healthy` series carries ZERO rows, so this book cannot select anybody today.",
    "arming_precondition": "DECLARED AND NOT ARMED. This book may not be armed until the `dip_healthy` series carries at least 20 recorded rows with no gap longer than 5 sessions, which is what makes 'first appearance this quarter' resolvable. Until then the entry rule refuses by name. The precondition is a property of the DATA and not of the book, and it is Don's to clear by scheduling the recorder; nothing in this declaration arms anything.",
    "crash_label": "RECORDED, never an entry or exit rule: any calendar month in which this book's own equal-secured-cash equity curve falls >= 10%, OR any 32-session SPY return <= -20%. A PAYS verdict on a window containing zero labelled crash months is recorded PAYS(NO-CRASH-SEEN) and may not be quoted without that qualifier. BLEEDS needs no qualifier -- V6-OPT's declared asymmetry, inherited.",
    "delta": 0.25,
    "delta_leg": "solved on the PUT leg, V6-OPT's convention",
    "dte": 37,
    "dte_rule": "nearest 37, restricted to 30-45; ties -> longer",
    "entry_source_amendment": "EXECUTOR AMENDMENT, 2026-10-13, BEFORE ANY FILL. The draft entered on 'the live dip detector's HEALTHY list' read daily. MEASURED: no such series existed. `fleet_history.SERIES` held exactly three streams -- `iv60_atm`, `dip_rejects`, `alert_count` -- and `dip_rejects` is the COMPLEMENT of this book's entry population, so the names this book enters on were recorded NOWHERE and 'first appearance this quarter' could not be evaluated against anything. The book would have armed and qualified nobody, which the harness reports as RULE_ARMED_NEVER_FIRES and which is 'indistinguishable in the records from a quiet market'. A `dip_healthy` series was added and is recorded from the SAME screen the two existing callers already pay for (no new screen is run anywhere). AND THE CADENCE IS THE BINDING CONSTRAINT, NAMED RATHER THAN ASSUMED: the fleet cycle deliberately does NOT run the dip screen, and the only callers that do are `scan_worker.run_weekly` and `POST /admin/record-dip-rejects`. That is why the scout measured `dip_rejects` at 6 days against `alert_count` and `iv60_atm` at 24 -- roughly the weekly-to-daily ratio, a cadence mismatch rather than an intermittent fault. The draft's 'within 2 sessions of first appearance' is therefore NOT achievable today and has been replaced by first appearance evaluated at the series' own cadence.",
    "exit": "hold to expiry, no exits",
    "max_stale_sessions": 5,
    "min_healthy_rows": 20,
    "records_schema_note": "F-2 (menu gate) and F-19 (density gate) are FIELDS and not books -- their own declarations say so ('fleet-wide convention, not a book'; 'A LABELING GATE, refuses nothing') -- so the menu depth and the density percentile are recorded on every fill here rather than carried as separate streams with 47.5- and 21.2-year horizons. None of the four collides with the 30 base RECORD_COLUMNS. The two series fields make the source's own thinness visible on the fill that used it.",
    "right": "put",
    "strike_selection": "delta",
    "v6opt_argument": "CONCEDED, NOT DODGED. V6-OPT's autopsy is correct: a delta target sets the strike from the name's own volatility and so equalises assignment by construction -- it measured 25.303% assignment on healthy dips against 25.727% on unhealthy, a 0.43pp gap, where V6-B had measured a real further-20%-drawdown difference of 2.797pp on those same covered rows and 10.84pp on the full panel. A RISK SIGNAL CANNOT PAY THROUGH A DELTA-TARGETED STRIKE. This book carries no risk signal and is not asked to: DECISIONS.md 2026-10-12 judges an options strategy as its own system, and its three pass clauses -- profitable net of real costs on the capital tied up in both halves, beats the same trade on random days in the same names, survives O11 sizing and the pre-committed crash stress -- are each unobstructed by a delta target. The only condition it obstructed has been withdrawn by the owner. Three further measured reasons. (1) IT IS THE ONLY STRIKE RULE WITH A MEASURED PRIOR: +1.1342%/trade on secured cash, both halves positive, 84.39% wins, 25.30% assignment, z +7.2506 against a random-day twin, all at 25 delta. (2) THE ALTERNATIVE IS MEASURED TO BE WORSE ON A GATE THIS BOOK MUST PASS: SELL-PREMIUM ran fixed 0.90 moneyness and its K3 fired at 8.900816 years of premium against a 6.0 bar, because that strike collects 0.7778% of strike at a median 44 DTE = 4.4545%/yr against V6-OPT's 2.550% at a median 32 DTE -- the moneyness rule surrenders most of the income, and the income is the crash gate's denominator. (3) A DELTA TARGET IS INVARIANT TO THE VOLATILITY REGIME AND A MONEYNESS TARGET IS NOT, which is a safety property for a forward book facing an unknown regime: at a fixed 0.90 moneyness the premium runs 0.272% of strike at IV 0.25 and 5.359% at IV 0.80, a twenty-fold swing in position size driven by nothing but the regime and scaling UP exactly when vol is highest. V6-OPT was a backtest over a known history and never had to weigh that. THE LIMITATION IS INHERITED AND STATED: this book cannot distinguish a safe dip from a dangerous one. It is a premium-selling book that happens to enter on dips, not a book that selects the safe ones."
  },
  "trial": {
    "charged_at": "first_verdict_read",
    "domain": "options"
  },
  "universe": "optionable names on the live dip detector's HEALTHY list with point-in-time market cap >= $10B at the entry date",
  "verdict_grammar": [
    "PAYS",
    "PAYS(NO-CRASH-SEEN)",
    "BLEEDS",
    "CANNOT-TELL(horizon)"
  ],
  "verdict_horizon": {
    "alpha": 0.05,
    "earliest_honest_read": "About 38.9 years at the declared 2.0 fills/month (933 fills). THAT IS THE POINT OF THIS FIELD, not a reason to shrink it. The meter is ANYTIME-VALID, so fills_needed is where the boundary falls to the DECLARED MINIMUM and not where a verdict becomes possible: at V6-OPT's MEASURED +1.1342 the boundary falls at 206 fills, about 8.6 years at the declared rate. THIS BOOK IS A RECORDER, NOT THE TEST -- the answer should come from SELL-PREMIUM-2's 2,557 already banked priceable events. What the paper book uniquely supplies is a forward series nobody can tune to, which is worth starting today precisely because it takes so long.",
    "expected_fills_per_month": 2.0,
    "expected_fills_provenance": "CONSERVATIVE PRIOR, re-stated at launch from a trailing-90-day count of the live healthy-dip list (F-11's convention). V6-OPT carried 1,631 healthy covered dip rows over 40 quarterly dates, ~41 names per quarter in the STATE, while this book enters on FIRST APPEARANCE only. Starving is data, not failure.",
    "fills_needed": 933,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED. The same derivation reproduces F-10's declared 306 and F-11's declared 138 exactly from their own declared fields, which is the instrument check before use (MB15). Fixed-n analogue at crit 1.96: n = ((1.96+0.84)*sigma/mei)^2 = 621.",
    "min_effect": 0.5671,
    "min_effect_derivation": "DERIVED, not chosen: DECISIONS.md 2026-10-06 requires a candidate's expected return to be quoted at HALF its backtested size (McLean-Pontiff), and half of V6-OPT's measured +1.1342 pp/trade is 0.5671. A book that can only see the effect at full backtested size cannot see the effect Don's own adoption rule expects it to deliver.",
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n. Both vocabularies are on the face above. No X7 or CORRECTED-FLOORS floor is quoted -- none is calibrated for a per-trade return on secured cash (V2G, R1-VAR), and every critical value this book ever reports is LABELLED UNCALIBRATED.",
    "rho": 3.0,
    "sigma": 5.047,
    "sigma_may_only_be_raised": true,
    "sigma_provenance": "MEASURED. V6OPT_STAGE2.json arms/A_healthy_csp/sd = 0.05047445127155545 on 660 trades, i.e. 5.047 pp per trade on secured cash. It is THIS structure's own SD, not borrowed across structures (MB8). May only ever be RAISED.",
    "years_to_horizon_at_projected_rate": 38.88
  }
}
```
