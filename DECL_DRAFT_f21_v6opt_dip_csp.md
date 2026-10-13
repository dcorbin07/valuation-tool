# DECL DRAFT — F-21: THE V6-OPT PUT-SELLING BOOK (short book)
## Tag: [V6-OPT arm A, carried forward AS MEASURED — its rejection was on condition 2, the health discriminator, which `DECISIONS.md` 2026-10-12 removes from the pass rule + A3-hostile (the corpse quoted in full: its gross level at perfect mid fills is +0.13% of max risk, "there is no premium") + SELL-PREMIUM's K2 (the naked single-name premium is POSITIVE in all three IV-rank bands) and K3 (the 0.90-moneyness alternative fires the crash gate at 8.90 years)]

**A DRAFT. NO FILL IS PLACED AND NO TRIAL IS BOOKED** — the harness charges at the **first verdict
read**, and this file reads nothing. The declaration below is committed **ALONE** (exactly one file
in its commit, `declaration_commit`'s own rule) before any fill exists.

**WHAT IS BEING PAPER-TRADED AND WHY IT IS THIS AND NOT SOMETHING NEARBY.** `V6-OPT` measured a
cash-secured **25-delta put, 30–45 DTE, held to expiry**, entered on a **healthy dip**, at
**+1.1342%/trade on secured cash** — positive in **both halves** (+1.1348 early, +1.1178 late),
**84.39% wins**, **25.30% assignment**, and beating a random-day twin at a paired name-year sign
test of **z +7.2506, p 4.1e-13 on 306 of 457 cells**. It was **REJECTED on condition 2 alone**: the
identical trade on *unhealthy* dips earned **more** (+1.2651%), so the health floor did not
discriminate. **`DECISIONS.md` 2026-10-12 removes that condition from the pass rule**, so the
measured construction goes forward unaltered. **Every field below is `V6-OPT`'s, not a nearby
variant**, because a forward book exists to test what was measured.

---

## THE DELTA ARGUMENT — required by the harness, and the autopsy is CONCEDED not dodged

`fleet.py:308` refuses `strike_selection: "delta"` unless `structure.v6opt_argument` is non-empty,
and its comment states why: *"a delta-targeted rule NEUTRALISING the very risk difference the trade
was built to exploit. Silence is not an argument."* **The autopsy is correct and this book does not
dispute a word of it.** `V6-OPT` measured assignment at **25.303% healthy against 25.727%
unhealthy — a 0.43pp gap** where `V6-B` had measured a real risk difference of **2.797pp on those
same covered rows** (10.84pp on the full panel). A delta target sets the strike from the name's own
volatility and so equalises assignment by construction. **A risk signal cannot pay through it.**

**THE ARGUMENT IS THAT THIS BOOK CARRIES NO RISK SIGNAL AND IS NOT ASKED TO.** Don's 2026-10-12
pass rule has three clauses — profitable net of real costs on the capital tied up in both halves;
beats the same trade on random days in the same names; survives `O11` sizing and the crash stress —
**and a delta target obstructs none of them.** It obstructed only the fourth condition, which has
been withdrawn. Three further measured reasons, in order of weight:

1. **IT IS THE ONLY STRIKE RULE HERE WITH A MEASURED PRIOR.** The five figures in the paragraph
   above are all 25-delta figures. A forward book at any other strike rule would be testing
   something this project has never measured.
2. **THE ALTERNATIVE HAS BEEN PRICED AND IT IS WORSE ON A GATE THIS BOOK MUST PASS.**
   `SELL-PREMIUM` ran the fixed-0.90-moneyness version and its `K3` **fired at 8.900816 years of
   premium against a 6.0 bar**, because that strike collects **0.7778% of strike at a median 44
   DTE = 4.4545%/yr** against `V6-OPT`'s **2.550% at a median 32 DTE**. **The moneyness rule is not
   merely different; it is measured to surrender most of the income, and the income is the crash
   gate's denominator.**
3. **A DELTA TARGET IS INVARIANT TO THE VOLATILITY REGIME AND A MONEYNESS TARGET IS NOT — and for
   a FORWARD book facing an unknown regime that is a safety property, which is the exact inversion
   of the autopsy's complaint.** At a fixed 0.90 moneyness the premium collected runs **0.272% of
   strike at IV 0.25 and 5.359% at IV 0.80**: a twenty-fold swing in position size driven by
   nothing but the regime, and it scales UP precisely when vol is highest. A delta target holds the
   per-position assignment probability roughly fixed. **`V6-OPT` was a backtest over a known
   history and never had to weigh that; a book that must survive a crash it cannot see does.**

**THE LIMITATION, STATED PLAINLY AND INHERITED RATHER THAN ARGUED AWAY: this book cannot
distinguish a safe dip from a dangerous one.** It is a premium-selling book that happens to enter
on dips, not a book that selects the safe ones. That is `V6-OPT`'s finding and the price of the
strike rule. **Anyone who wants the risk-selecting version is back at fixed moneyness and back at
`K3`, which is a measured dead end rather than an open question.**

---

## SIZING, CONCURRENCY, AND WHAT A CRASH DOES

**THE DENOMINATOR IS THE STRIKE, NOT THE PREMIUM.** `V6-OPT` recorded that `options_sizing` gets
this wrong for a short — *"quoting a short on premium overstates it ~40x on this book"* — so
`return_denominator` is `secured_cash` and every figure this book ever reports is a return on the
cash the position ties up.

**MEASURED, on the 187 tier names with both a price series and a chain** (median close 2016–2019):
a 0.925-strike contract ties up **$4,411 at the median share price of $49.01**, **$7,432 at p75**,
and **$14,458 at the p95 name of $160.64**. So **cap 10 needs about $44,100 at the median name and
$144,576 at the p95 name**, and `MB3`'s wall binds on the **tail, not the median**. The recorder
stores the skip **reason** so an affordability skip is never read as a concurrency skip.

**WHAT COUNTS AS A CRASH, FROZEN HERE:** any calendar month in which the book's own
equal-secured-cash equity curve falls by **10% or more**, OR any 32-session SPY return at or below
**−20%** (SPY's own worst by year: 2018 **−14.31%**, 2022 **−16.53%**, 2025 **−17.32%**, 2020
**−32.61%**). **The crash is a RECORDED LABEL on the window, never an entry or exit rule** — the
book does not stop selling in a crash, because a rule that stands aside in crashes is a different
book and could not be tested against what was measured.

**AND THE HORIZON HANDLES A CRASH BY NOT BEING ALLOWED TO END BEFORE ONE.** `V6-OPT`
pre-committed, verbatim: *"A decisive REJECT is therefore available … while a decisive ADOPT is
not, because a short-vol book's whole risk is concentrated in crash quarters and this sample
contains one. A clearing arm is recorded `ELIGIBLE-BUT-UNRESOLVED`, never `ADOPTED`."* **That
clause is inherited and made mechanical: a `PAYS` verdict on a window containing ZERO labelled
crash months is recorded `PAYS(NO-CRASH-SEEN)` and may not be quoted without that qualifier.**
A `BLEEDS` verdict needs no such qualifier — the asymmetry is the point.

**THE MECHANICAL EXPECTATION, so nobody is surprised by the first one** (public index arithmetic, a
0.925 strike, `1 − (1 − x)/m`): a 2020-style **−32.61%** month costs **27.15% of secured cash** and
a 1.4× single-name version **−45.68%** costs **41.24%**. Against the measured income that is
roughly **2 to 6 years of premium**, depending on the regime's own vol. **Because the entry rule
fires on drops, the book is fully loaded going in — and because the cap refuses the rest, the loss
is bounded at about one book-width however many names qualify.** That is `O11`'s clustering
mechanism inverted: there the edge lived in the crowded weeks and the cap refused it; here the
**risk** lives in the crowded weeks and the cap refuses it.

---

## DON'S PASS RULE, VERBATIM, AND THE TWIN THAT CLAUSE (b) REQUIRES

`DECISIONS.md` 2026-10-12: it passes if **(a)** it is *"profitable net of realistic costs on the
capital it ties up, in both halves"*; **(b)** it *"beats the same trade placed on random days in
the same names (so the timing is shown to matter)"*; **(c)** it *"survives realistic sizing and
concurrency (O11) and the pre-committed crash stress"*. *"The comparison with simply buying the
shares is REPORTED for context and carries no verdict."*

**CLAUSE (b) IS A SECOND BOOK AND IT IS DECLARED SEPARATELY** — `DECL_DRAFT_f22_dip_csp_random_twin.md`,
same structure, same universe, same cap, entry timing drawn from a deterministic salted schedule
with no reference to the dip signal. **Neither book's verdict may be read without the other's**,
and the paired comparison is **by (name, calendar quarter)**, which is `V6-OPT`'s own unit.

**THE SHARES ROW IS RECORDED AND CARRIES NO VERDICT.** `V6-OPT` measured the stock at
**+3.4269%/trade** against the put's **+1.1342%**; a regression of the put's return on the stock's
over its 660 banked trades gives a realised exposure of **0.2131** and an option-specific intercept
of **+0.4040pp** (*t* 2.55 pooled, ≈1.73 after `R3`'s measured options design effect of 2.21 — no
verdict there either). Reported, labelled, not a bar.

---

## THE HORIZON IS THE HARDEST FACT IN THIS FILE AND IT IS NOT HIDDEN

**`fills_needed` IS DERIVED FROM `track_meter.boundary`, AND THE DERIVATION WAS VALIDATED BEFORE
USE** (`MB15`): the same function reproduces **F-10's declared 306 and F-11's declared 138
exactly** from their own declared sigma and `min_effect`.

* **`sigma` = 5.047 pp, MEASURED** — `V6OPT_STAGE2.json` `arms/A_healthy_csp/sd`. **It is this
  structure's own SD, not borrowed across structures** (`MB8`), and under `track_meter`'s rule it
  may only ever be **RAISED**.
* **`min_effect` = 0.5671 pp, and it is DERIVED rather than chosen.** `DECISIONS.md` 2026-10-06
  requires a candidate's expected return to be quoted at **HALF its backtested size**
  (McLean-Pontiff). Half of the measured +1.1342 is **0.5671**. **A book that can only see the
  effect at full backtested size cannot see the effect Don's own adoption rule expects it to
  deliver**, so the MEI is the half.
* **`fills_needed` = 933.** Fixed-*n* analogue at crit 1.96: **621**.

**AT THE DECLARED 2.0 FILLS/MONTH THAT IS ABOUT 38.9 YEARS, AND SAYING SO IS THE WHOLE POINT OF THE
FIELD.** The runbook's §3 exists for exactly this: *"the number goes on the declaration so nobody
reads a six-month book at six weeks."* **Three things make the declaration honest rather than
absurd:**

1. **THE METER IS ANYTIME-VALID, SO `fills_needed` IS WHERE THE BOUNDARY FALLS TO THE DECLARED
   MINIMUM — NOT WHERE A VERDICT BECOMES POSSIBLE.** A larger effect crosses earlier: at the
   **measured** +1.1342 the boundary falls at **206 fills**, about **8.6 years** at the declared
   rate. If the effect is real at the size measured, the book speaks a quarter of the way in.
2. **THE FILL RATE IS THE MARKET'S TO GIVE AND IS RE-STATED AT LAUNCH** from a trailing-90-day
   count of the live healthy-dip list (F-11's convention). The declared 2.0/month is deliberately
   **conservative**: `V6-OPT` carried **1,631 healthy covered dip rows over 40 quarterly dates**,
   ~41 names per quarter in the *state*, while this book enters on **first appearance** only.
   **Starving is data, not failure, and the fill count prints on every read.**
3. **THE HONEST RECOMMENDATION, WRITTEN INTO THE DECLARATION SO IT CANNOT BE FORGOTTEN: THIS BOOK
   IS A RECORDER, NOT THE TEST.** The answer should come from `SELL-PREMIUM-2`'s **2,557 already
   banked priceable events**, not from this paper book. What the paper book uniquely supplies is a
   forward series **nobody can tune to** — and that is worth starting today precisely because it
   takes so long.

**Verdict grammar:** `PAYS` / `BLEEDS` / `CANNOT-TELL(horizon)`, with `PAYS(NO-CRASH-SEEN)` as the
qualified form above. **Trial:** 1, options, charged at the first verdict read.
**Void:** any exit rule other than hold-to-expiry; standing aside in a crash; re-entering a name
inside a quarter; changing the strike rule, the tenor band or the cap after any fill; reading this
book's verdict without F-22's.

---

## MACHINE-CHECKABLE DECLARATION

**THE FENCE BELOW READS `jsonc` AND NOT `json`, DELIBERATELY, AND THE REASON IS A GAP THIS FILE
FOUND BY FALLING INTO IT.** `fleet_export_declarations.py` globs **every** `DECL_*.md`, strips the
`DECL_` prefix, and treats **anything that parses as a book** — the `DRAFT_` prefix does **not**
exempt it. The three existing drafts (`f7`, `f9`, `f16`) are skipped only because they are
**prose-only**: *"does not parse: no fenced ```json declaration block"*. **So there has never been
a PARSEABLE DRAFT, and the first one turned
`tests/test_audit5_remediation.py::test_the_committed_manifest_equals_a_fresh_build` red** — a
fresh build saw **20** books against the shipped manifest's 18, under the ids
`DRAFT_f21_v6opt_dip_csp` and `DRAFT_f22_dip_csp_random_twin`, which would also have refused as
`BOOK_ID_DOES_NOT_MATCH_FILENAME`. **A red land gate blocks every other lane**, so it is fixed here
rather than left.

**`parse_declaration`'s pattern is `` ```json\s*\n ``, which `jsonc` does not match** — verified
both ways — so the exporter skips this file exactly as it skips the other three, and **no
unaccepted draft is registered as a live book.** Registering one would be *accepting* it, which is
the options-bot lane's call and not the scout's.

**EVERY FIELD BELOW IS FINAL. With the fence set to `json` this declaration returns
`validate_declaration(...)["ok"] = True` with ZERO refusals** once `assignment.register()` is
called — measured, with `DECL_f10_clean_csp.md` and `DECL_f8_csp_entry_financing.md` as the control
(both return the identical `SHORT_BOOK_WITHOUT_ASSIGNMENT` without the provider).

**ACCEPTANCE IS THREE MECHANICAL STEPS AND NO EDIT TO THE DECLARATION:** rename
`DECL_DRAFT_f21_v6opt_dip_csp.md` → `DECL_f21_v6opt_dip_csp.md` **alone** in its own commit
(`declaration_commit` requires exactly one file), change `jsonc` → `json`, and re-run
`scripts/fleet_export_declarations.py` so the manifest matches a fresh build again.

```jsonc
{
  "book": "f21_v6opt_dip_csp",
  "domain": "options",
  "hypothesis_class": "edge",
  "side": "short",
  "sells_premium": true,
  "entry_rule": "Daily: the live dip detector's HEALTHY list -- names down >=20% from the 252-session high that PASS the shipped health floors, read from valuation.web.dip.screen's own published output and never recomputed. Restrict to names whose market cap is >= $10B at the entry date (point-in-time, never ever-in-tier) and that are optionable. Enter within 2 sessions of a name's FIRST appearance on that list this quarter; skip any name already held or already entered this quarter. If more qualify than the cap allows, take the largest by market cap; alphabetical tie-break.",
  "structure": {
    "strike_selection": "delta",
    "delta": 0.25,
    "delta_leg": "solved on the PUT leg, V6-OPT's convention",
    "right": "put",
    "dte": 37,
    "dte_rule": "nearest 37, restricted to 30-45; ties -> longer",
    "exit": "hold to expiry, no exits",
    "v6opt_argument": "CONCEDED, NOT DODGED. V6-OPT's autopsy is correct: a delta target sets the strike from the name's own volatility and so equalises assignment by construction -- it measured 25.303% assignment on healthy dips against 25.727% on unhealthy, a 0.43pp gap, where V6-B had measured a real further-20%-drawdown difference of 2.797pp on those same covered rows and 10.84pp on the full panel. A RISK SIGNAL CANNOT PAY THROUGH A DELTA-TARGETED STRIKE. This book carries no risk signal and is not asked to: DECISIONS.md 2026-10-12 judges an options strategy as its own system, and its three pass clauses -- profitable net of real costs on the capital tied up in both halves, beats the same trade on random days in the same names, survives O11 sizing and the pre-committed crash stress -- are each unobstructed by a delta target. The only condition it obstructed has been withdrawn by the owner. Three further measured reasons. (1) IT IS THE ONLY STRIKE RULE WITH A MEASURED PRIOR: +1.1342%/trade on secured cash, both halves positive, 84.39% wins, 25.30% assignment, z +7.2506 against a random-day twin, all at 25 delta. (2) THE ALTERNATIVE IS MEASURED TO BE WORSE ON A GATE THIS BOOK MUST PASS: SELL-PREMIUM ran fixed 0.90 moneyness and its K3 fired at 8.900816 years of premium against a 6.0 bar, because that strike collects 0.7778% of strike at a median 44 DTE = 4.4545%/yr against V6-OPT's 2.550% at a median 32 DTE -- the moneyness rule surrenders most of the income, and the income is the crash gate's denominator. (3) A DELTA TARGET IS INVARIANT TO THE VOLATILITY REGIME AND A MONEYNESS TARGET IS NOT, which is a safety property for a forward book facing an unknown regime: at a fixed 0.90 moneyness the premium runs 0.272% of strike at IV 0.25 and 5.359% at IV 0.80, a twenty-fold swing in position size driven by nothing but the regime and scaling UP exactly when vol is highest. V6-OPT was a backtest over a known history and never had to weigh that. THE LIMITATION IS INHERITED AND STATED: this book cannot distinguish a safe dip from a dangerous one. It is a premium-selling book that happens to enter on dips, not a book that selects the safe ones.",
    "crash_label": "RECORDED, never an entry or exit rule: any calendar month in which this book's own equal-secured-cash equity curve falls >= 10%, OR any 32-session SPY return <= -20%. A PAYS verdict on a window containing zero labelled crash months is recorded PAYS(NO-CRASH-SEEN) and may not be quoted without that qualifier. BLEEDS needs no qualifier -- V6-OPT's declared asymmetry, inherited."
  },
  "universe": "optionable names on the live dip detector's HEALTHY list with point-in-time market cap >= $10B at the entry date",
  "sizing": "equal secured cash per position; the skip reason is recorded so an affordability skip is never read as a concurrency skip (MB3)",
  "concurrency_cap": 10,
  "assignment_model": "at expiry per moneyness, S3-I3 assignment_at_expiry",
  "margin_method": "cash_secured_put",
  "spot_basis": "as_traded",
  "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
  "return_denominator": "secured_cash",
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 2.0,
    "expected_fills_provenance": "CONSERVATIVE PRIOR, re-stated at launch from a trailing-90-day count of the live healthy-dip list (F-11's convention). V6-OPT carried 1,631 healthy covered dip rows over 40 quarterly dates, ~41 names per quarter in the STATE, while this book enters on FIRST APPEARANCE only. Starving is data, not failure.",
    "min_effect": 0.5671,
    "min_effect_derivation": "DERIVED, not chosen: DECISIONS.md 2026-10-06 requires a candidate's expected return to be quoted at HALF its backtested size (McLean-Pontiff), and half of V6-OPT's measured +1.1342 pp/trade is 0.5671. A book that can only see the effect at full backtested size cannot see the effect Don's own adoption rule expects it to deliver.",
    "sigma": 5.047,
    "sigma_provenance": "MEASURED. V6OPT_STAGE2.json arms/A_healthy_csp/sd = 0.05047445127155545 on 660 trades, i.e. 5.047 pp per trade on secured cash. It is THIS structure's own SD, not borrowed across structures (MB8). May only ever be RAISED.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 933,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED. The same derivation reproduces F-10's declared 306 and F-11's declared 138 exactly from their own declared fields, which is the instrument check before use (MB15). Fixed-n analogue at crit 1.96: n = ((1.96+0.84)*sigma/mei)^2 = 621.",
    "earliest_honest_read": "About 38.9 years at the declared 2.0 fills/month (933 fills). THAT IS THE POINT OF THIS FIELD, not a reason to shrink it. The meter is ANYTIME-VALID, so fills_needed is where the boundary falls to the DECLARED MINIMUM and not where a verdict becomes possible: at V6-OPT's MEASURED +1.1342 the boundary falls at 206 fills, about 8.6 years at the declared rate. THIS BOOK IS A RECORDER, NOT THE TEST -- the answer should come from SELL-PREMIUM-2's 2,557 already banked priceable events. What the paper book uniquely supplies is a forward series nobody can tune to, which is worth starting today precisely because it takes so long.",
    "years_to_horizon_at_projected_rate": 38.88,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n. Both vocabularies are on the face above. No X7 or CORRECTED-FLOORS floor is quoted -- none is calibrated for a per-trade return on secured cash (V2G, R1-VAR), and every critical value this book ever reports is LABELLED UNCALIBRATED."
  },
  "verdict_grammar": [
    "PAYS",
    "PAYS(NO-CRASH-SEEN)",
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
