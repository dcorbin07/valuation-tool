# PRE-REGISTRATION — `P1S0-CONTROL`: was P1S0's dead early half a PERIOD or a UNIVERSE?

**Committed ALONE, markdown only, before any measurement code exists.** A strict git ancestor of
every measurement commit; `MA60`'s convention check enforces it.

**Domain:** equity. **Trial cost: 1**, booked in `RESEARCH_LOG.md` before the run.
**Equity `N` 231 → 232**; the HLZ hurdle moves **3.29921739523839 → 3.30052643427266**, 0.0013 of
a *t*, which changes no verdict anywhere.

---

## 0. THIS IS NOT A RE-RUN OF P1S0, AND IT MAY NOT BECOME ONE

`P1S0` closed the options-expression family on a pre-registered both-halves failure. **That verdict
is not under test here and nothing in this register can move it.** No arm of `P1S0` is re-scored,
its placebo is not recomputed, and `P1S0_GATE.json` is not written to — **every optionable figure
quoted below is READ from that shipped artifact.** Re-measuring a landed result is how two lanes
come to publish two numbers for one question.

**The family is NOT reopened in this session, whatever this returns.** If the answer is the
unfavourable one it is a finding about **the gate**, not a licence — a reopen would need its own
register, its own trials and its own blind commitment.

---

## 1. The question — the only one this register asks

`P1S0` measured, on the point-in-time optionable universe (`pit_liquid`, 619 names, 11,946 rows):

| horizon | full sample | early half | late half |
|---|---|---|---|
| H=63 (power anchor) | cum α **+0.03511**, ann **+14.045%/yr**, HAC *t* **3.3731** vs floor 1.4822 → **PASS** | ann **+2.818%/yr**, HAC *t* **0.8352** vs floor 1.6974 → **FAIL** | ann **+24.308%/yr**, HAC *t* **4.1471** → PASS |
| H=252 | cum α +0.12023, *t* 2.3787 | cum α **−0.00082**, *t* −0.0379 | cum α +0.22781, *t* 2.8778 |
| H=504 | cum α +0.11564, *t* 1.7840 | cum α +0.01033, *t* 0.4570 | cum α +0.22576, *t* 1.9351 |

The early window is **2016-01-20 → 2020-10-20** at the power anchor. It is not weak; it is absent.

**THE QUESTION: is 2016–2020 weak because those are OPTIONABLE names, or because it is a weak
PERIOD?**

Nothing else is asked. No new signal, no new instrument, no reopening.

---

## 2. Why the existing artifact cannot answer it

`P1S0` already ships `reference_full_panel_same_dates` — the full panel's top-decile cumulative
alpha over exactly these dates. **It carries `full` ONLY** (H=63 **+0.02378**, H=252 +0.09391,
H=504 +0.13112). **The early/late split of the full panel on those dates was never computed**, and
that split is the entire question. This register computes exactly that and nothing else.

---

## 3. Construction — the same object, the same dates, the same code

**Panel:** `data/free_analysis/panel_s22_h504.pkl` — the full **69-date, 2,531-name, 113,945-row**
panel, the identical file `P1S0` loaded.

**Dates:** taken from the optionable partition so the comparison is same-dates by construction —
`scorable_dates(restrict(panel, part, "pit_liquid"), h)`, then `halves()`, both **imported** from
`scripts/p1s0_optionable_gate.py` and `valuation/studies/optionable_universe.py`. Not re-typed
(audit `B7`'s class). This uses `restrict` only to obtain a **date list**; it scores no restricted
arm.

| horizon | dates | early | embargoed boundary | late |
|---|---|---|---|---|
| 63 | 40 | **20: 2016-01-20 → 2020-10-20** | 2021-01-21 | 19: 2021-04-22 → 2025-10-27 |
| 252 | 38 | **19: 2016-01-20 → 2020-07-22** | 2020-10-20 | 18: 2021-01-21 → 2025-04-28 |
| 504 | 34 | 17: 2016-01-20 → 2020-01-22 | 2020-04-22 | 16: 2020-07-22 → 2024-04-24 |

**Statistic:** `scripts.term_structure.arm(full_panel, h, dates=window)` — the same shipped
function `P1S0` scored with, reporting `cum_alpha`, `alpha_ann` and `alpha_t_hac`.

**Bar:** a **full-panel** `fixed_weights_null` placebo, computed with the same shipped
`placebo_floors` machinery on the same dates and windows: **200 draws, seeds 7100–7299**, matching
`P1S0`'s seed sequence so seed choice is not a free parameter. Computed for **H=63 and H=252**,
the two horizons the decision rule reads.

**A FULL-PANEL STATISTIC MAY NOT BE COMPARED WITH P1S0's RESTRICTED-UNIVERSE FLOORS.** Those were
calibrated on 619 names; this is 2,531. Quoting 1.4822 or 1.6974 against a full-panel *t* is the
extrapolation error `U2` avoided by declining and this record warns about most. **Doing it is a
void condition (§6).** `S22`'s rider travels too: `fixed_weights_null` is a different and less
conservative null than X7's, so its percentiles may never be compared with 2.2837 / 2.2913.

---

## 4. The decision rule — fixed before any measurement

Two legs, both on the **full panel's EARLY window**:

* **Leg 1 — the power anchor.** `alpha_t_hac` at **H=63** against the full panel's **own**
  `early_p95` placebo floor.
* **Leg 2 — the horizon where the optionable early half read −0.08%.** `cum_alpha` at **H=252**,
  against **zero**.

| outcome | requires | reading |
|---|---|---|
| **UNIVERSE** | Leg 1 **clears** its own early_p95 **AND** Leg 2 **> 0** | the full panel is healthy over 2016–2020 while the optionable subset is dead ⇒ **`P1S0`'s failure is about optionable names and the family closed correctly. It stays closed.** |
| **PERIOD** | Leg 1 **fails** its own early_p95 **AND** Leg 2 **≤ 0** | the full panel is weak over that window too ⇒ **`P1S0`'s early half was measuring a period, not a universe, and the family closed on an artifact.** A finding about **the gate**, not a licence to reopen. |
| **NULL** | the two legs disagree | ambiguous against the rule is a **NULL** (`RUN_RULES` A6), never a judgement call |

**Reported with NO verdict attached:** H=504; both late halves; the early/late ratios; and the
optionable-versus-full early gap. None of these can move the outcome above.

---

## 5. My prior, stated before measuring

**I lean PERIOD, at roughly 55/45** — against the brief's own framing, which cites `R1` as
reporting the headline passing every subperiod.

The reason is that `R1`'s own fragility work already found the exposure: *"a ~10-year rolling window
centred on 2009-2019 shows alpha of only **+1.66% (t 1.39)**"*, and **8 of 70 rolling windows are
not significant**. `X4` separately measured that the margin over what a user can actually buy is
**not demonstrable since 2014**. The window under test, 2016–2020, sits inside both of those. So
"the headline passes every subperiod" is true of `R1`'s own coarse thirds and halves and is **not**
a claim about this specific five-year window.

**Two things that cut the other way**, stated so the prior is not a one-sided argument: the full
panel's full-sample cum α over these same 40 dates is already published at **+0.02378 (≈ +9.5%/yr)**
so the panel is clearly alive across the whole window; and the optionable subset was *stronger*
full-sample (+14.0%/yr), which is `P1S0`'s own headline.

**A NULL is a live outcome**, not a formality: the two legs are different horizons and can
disagree, and I put that at ~20%.

---

## 6. Non-blindness, disclosed

**Known before writing this** and quoted above: every `P1S0` optionable figure, and the full
panel's **full-sample** cum α on the same dates at all three horizons.

**Genuinely blind:** the full panel's **early and late halves** on those dates — the entire object
of this register — and every placebo floor computed on the full panel. None has ever been computed.

---

## 7. Void conditions

The item is **VOID** — no verdict may be quoted — if any of these occurs:

1. **Any `P1S0` arm, placebo or verdict is recomputed**, or `P1S0_GATE.json` is written to.
2. **The options-expression family is reopened in this session**, whatever the outcome.
3. **A full-panel statistic is compared with `P1S0`'s restricted-universe placebo floors.**
4. **Any threshold, date set, horizon or window in §3–§4 changes after a measurement**, or the
   decision rule is restated once a number is known.
5. **A third leg is added**, or H=504 is promoted from diagnostic to decisive.
6. **`.github/` is touched** (MA11's land policy refuses it by design).

---

## 8. Trial accounting

**1 trial, equity.** One comparison, one pre-committed rule, one verdict against a bar. It is
charged rather than treated as a free control on the `O21` precedent — *"it had a pre-committed bar
and returned a verdict against it, so it is a trial — corrected upward, against my own result."*
Charged to **equity** on the `U2`/`MA31`/`P1S0` precedent: the statistic is the underlying's
forward return.

**Equity `N` 231 → 232.** Options 294 and infra 15 untouched. `BACKTEST_RESULTS.json` needs no
re-run; per `MA21` the artifact may legitimately LAG the log and may never LEAD it.
