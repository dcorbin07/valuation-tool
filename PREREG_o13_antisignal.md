# PRE-REGISTRATION — O13, anti-signal decomposition

**Committed before any measurement code for this item exists.** This file and
`PREREG_o12_kelly_ruin.md` are the only files in their commit; no `.py` accompanies them. The
commit is a strict git ancestor of every measurement commit that follows. Verify with
`git show --name-only --format= <this commit>`.

Item **O13** in `VALQUO_LEDGER.md` (`OPEN`, src=auto, "prose mentions only, no section, no
commit"). Options domain.

---

## 0 · What is being characterised, and what is NOT being re-opened

R2's verdict stands and is **not** re-opened. Split-clean (U1-SPLIT, 2026-08-11) the alert book
earns **+3.2702%/trade** (n 3,870) against a pooled five-seed random-entry control's
**+8.3342%** (n 29,654) — gap **−5.0640pp**, paired name-year sign test **z −4.9612**. The
day-selection subtracts value. The path study then measured the same thing a different way: at
**every** touch level and on **both** recovery measures — eight cells of eight — the control
recovers more often than the signal book, while the drawdowns themselves are identical.

**This item characterises the corpse.** It asks *where* the anti-signal lives, *how* it is
distributed, and whether the inverse of it is information or noise. No result here can revive
the entry signal, and none may be quoted as if it could.

## 1 · State of knowledge at the moment this register was written

Disclosed rather than implied, because some of it was measured today, before this file existed:

* R2's split-clean figures above (published, U1-SPLIT).
* The path study §2e recovery table (published).
* **The banked-book schema**, measured today: alert rows carry 5 alert features
  (`score`, `iv`, `labels`, `flow_read`, plus surface fields `skew_25d`/`term_slope`/`vrp`/
  `gex_proxy`) at ~100% and control rows carry them at **0.0%**; 9 structural fields
  (`dte`, `target_delta`, `cap_tier`, `marketcap_musd`, `entry_spread_pct`, `pit_atm_oi`,
  `pit_median_spread_pct`, `opt_right`, `horizon`) are ~100% on **both**.
* **`iv_rank` is 0.0% on BOTH books** — a wired, always-empty field. Reported as a bug in its
  own right (COVERAGE RULE class). It is excluded from every arm below because it has no values,
  not because of anything it scored.
* **The `_control_for` join works**: 29,564 of 29,654 control rows (99.7%) map to exactly one
  alert, **zero ambiguous**. The 90 orphans are control rows whose parent alert was removed by
  the U1-SPLIT filter.
* The alert book's unconditional return distribution (mean, median, hit rate, quantiles) — see
  `PREREG_o12_kelly_ruin.md` §1, which needs it as an input.

**Not known:** any feature-conditional gap, any concentration statistic, any inverse-rule result.
Those are what this register commits to.

## 2 · Data, fixed now

Split-clean books only: `state_r2_splitclean.pkl` (3,870) and `control_r2_splitclean_seed{0..4}.pkl`
(29,654 pooled). Aggression 1.0. No re-mine; no new frozen data is fetched. The exit policy is
the shipped one and is **not** varied — S23 and the path study both say do not touch it.

**Two tracks, forced by the availability measured in §1:**

* **Track S (structural, 9 features).** Both books carry their own values. Direct matched
  comparison inside a feature bin.
* **Track A (alert, 4 features: `score`, `iv`, `flow_read`, `labels`).** The control has no
  values of its own, so each control row inherits its **parent alert's** feature value through
  the `_control_for` join. The comparison is then "on alerts that looked like *this*, did the
  alert's chosen day beat random days on the same name?" — which is the R2 question conditioned
  on what the alert saw. **Restricted to the 99.7% of control rows that join.** That exclusion
  is keyed on the parent alert's survival of a split filter, never on a return.
* **Surface fields (`skew_25d`, `term_slope`, `vrp`, `gex_proxy`) join the same way** and are
  counted in Track A, giving 8 Track-A features.

## 3 · Binning, fixed now

* Numeric features: **quintiles**, breakpoints computed on the **alert book** and applied
  unchanged to the control, so both books are cut at identical thresholds.
* Categorical (`cap_tier`, `horizon`, `opt_right`, `flow_read`): levels with **≥100 alert
  trades**; everything else pooled into `OTHER`.
* `labels` is a list; it becomes indicator features for each label appearing on ≥100 alert
  trades, each a 2-level categorical (present / absent).

## 4 · The three questions and the statistics that answer them

**Q1 — where does the anti-signal live?** For feature *F* with bins *b*:
`gap_b = mean(alert ∈ b) − mean(control ∈ b)`, and the bin's contribution to the total gap is
`w_b · gap_b` with `w_b` the alert-book share of bin *b*. By construction `Σ_b w_b·gap_b` is
**not** exactly the total gap unless the control is re-weighted to the alert's bin mix, so both
are reported: the **rate** component (alert mix, within-bin gaps) and the **mix** component
(what the control's different bin mix contributes). Standard mix-vs-rate; both reported for
every feature.

**Q2 — concentrated or diffuse?** Pre-committed statistic, the share of the gap carried by the
single worst bin:

> `S_worst(F) = (w_b* · gap_b*) / Σ_b w_b·gap_b`, for `b*` the bin minimising `w_b · gap_b`.

Perfectly diffuse across 5 quintiles → `S_worst = 0.20`; perfectly concentrated → `1.00`.

**CALIBRATED BAR (the X7 method, pointed at a concentration statistic).** Null: hold every row's
`(book, return)` pair fixed and **permute the feature values across rows within book**. This
preserves each book's feature marginal, each book's return distribution, and the total gap
**exactly**, while destroying any feature↔return association. 2,000 draws per feature; the bar
is that draw distribution's **p95**. A feature *carries* the anti-signal only if its observed
`S_worst` exceeds **its own** p95 — each feature is calibrated against its own null, because
bin count and bin sizes differ between features and a shared bar would not be comparable.

**Q3 — does the INVERSE carry information, or is it noise plus costs?** Two sub-tests:

* **(a) Selection inverse — the verdict-bearing one, both-halves.** Split the alert book at its
  median calendar date. On the **decide** half, rank bins by `gap_b` and mark as REFUSE the bins
  whose `gap_b` is most negative, up to at most 30% of decide-half alert trades. On the
  **measure** half — untouched during selection — apply that refusal set and compute the gap of
  the surviving alert trades against the control restricted to the same bins. **Both directions**
  (early→late, late→early). Margin pre-committed in §5.
* **(b) Instrument inverse — arithmetic, NO verdict.** Whether the anti-signal is *tradeable*
  by reversing the position. Reported as a bound, not a simulated book, because a short's exit
  policy is not the shipped one and inventing one here would be an unregistered arm. The inputs
  are the alert book's absolute expectancy and the measured round-trip spread.

## 5 · Bars and the verdict rule, fixed now

| question | verdict | condition |
|---|---|---|
| Q2 | **CONCENTRATED** | ≥1 feature clears its own calibrated p95 **in both halves independently** |
| Q2 | **DIFFUSE** | no feature clears in both halves |
| Q3a | **INVERSE CARRIES INFORMATION** | measure-half gap improves by **≥ +1.50pp** in **BOTH** directions, and the refused bins' own measure-half gap is negative in both |
| Q3a | **NULL** | anything else, including a one-direction pass |

The +1.50pp margin is set against R2's own −5.06pp gap: a refusal rule that recovers less than
~30% of the gap out-of-sample is not worth a construction change. **Ambiguous is a NULL** and a
near miss is a NULL.

**Full-sample-only results carry NO verdict** — session 7's rule, and session 6's LOO is why.
Anything measured on the full sample is labelled EXPLORATORY.

## 6 · Expectations, written before any of it runs

Recorded because this project's directional calls keep being wrong and writing them down first
is the only thing that makes that visible.

* **E1 — the anti-signal is DIFFUSE; no feature clears in both halves. 65/35.** R2's gap is a
  *timing* effect, and the path study found the drawdowns identical with only recovery differing
  — a broad property, not a feature-specific one.
* **E2 — if any feature does carry it, it is `iv`. 55/45 conditional on E1 being wrong.** The
  alert fires on breakouts and volume surges, which is when IV is already bid.
* **E3 — the inverse does NOT carry information out-of-sample. 70/30.** It fails in at least one
  direction, the same shape as session 7's LOO and session 11's ML combiner.
* **E4 — every feature bin has POSITIVE alert expectancy; no cut of the alert book loses money
  outright. 55/45.** Genuinely uncertain and the one I would most like to be wrong about,
  because a negative cut is the only thing that could make Q3b interesting.
* **E5 — the instrument inverse is arithmetically negative.** Charged as arithmetic, **not**
  scored as a prediction, because the alert book's absolute expectancy is already published as
  positive and reversing a positive-expectancy book is not a forecast.

## 7 · Trial cost

Arms: **8 Track-A + 9 Track-S = 17** feature arms for Q1/Q2, plus **1** inverse-rule hypothesis
(two directions of one rule is one hypothesis, as in session 7's LOO). The half-split
calibration and the permutation nulls are **calibrations, not searches**, and are charged zero —
consistent with session 10's HAC floor.

**Options `N` 210 → 228** (17 + 1), logged in `RESEARCH_LOG.md` with this file as source.
Equity `N` is untouched; the domain is options.

## 9 · AMENDMENTS, made after the first run and before any verdict was read

Appended, never rewritten — §1-§8 above stand as committed at `b0f287d`. **None of the three
consults a measure-half number or any verdict.** A1 and A3 are arm counts and bin counts; A2 is
evaluated on a **decide half only**, which is exactly where selection is permitted. Each is
checkable against the artifact.

**A1 — the label vocabulary is PARAMETERISED, so `labels` expands to 16 arms, not 1.** §3 says
each label on ≥100 alert trades becomes an indicator. The alert labels turn out to embed their
own threshold in the text: `Low IV 14%`, `Low IV 15%` … `Volume surge 1.5x`, `1.6x` … So one
concept becomes many near-duplicate arms. The registered definition is **kept unchanged** — a
normalised vocabulary would be a different feature set and choosing it now would be a
post-hoc degree of freedom — but the **trial count is corrected upward**:

> **Arms are 32, not 17** (8 Track-A expanding to 23, plus 9 Track-S), so O13 costs **33** trials
> (32 + the inverse hypothesis), not 18. **Options `N` 210 → 243** for O13, and **246** including
> O12's 3. Understating `N` overstates the significance of every bar in the project, so the
> correction runs against this register's own result.

A normalised-label version is a NEW registration and may not be run as a re-run of this one.

**A2 — Q3a's feature must be able to EXPRESS a refusal.** §4(a) caps the refusal at 30% of
decide-half alert trades but does not say which feature is ranked. Two structural facts
interact badly: `s_worst` is mechanically ≈1.0 for a lopsided two-bin feature, and one alert
label (`Uptrend (>50 & >200 DMA)`) sits on **98.5%** of the book. So an unrestricted "highest
`s_worst`" selection lands on a feature whose only negative-gap bin has weight 0.985, larger
than the cap — and refuses nothing, necessarily. The first run did exactly that in both
directions and returned an improvement of +0.0000pp, which is an artefact of the statistic, not
a null result about the data.

> Q3a's selection pool is therefore restricted to features that are **not degenerate** and that
> yield a **non-empty refusal set on the decide half**.

**The second condition reads decide-half gaps, and an earlier draft of this amendment claimed it
read bin weights alone. That was wrong and a test caught it before any verdict was read.** The
live failure is not "every bin is too big" — it is "the only bin with a *negative gap* is too
big", and a weights-only predicate cannot tell those apart (the 1.5% bin *is* small enough to
refuse; it simply has a positive gap and is therefore not a candidate). Reading decide-half gaps
during selection is legitimate — that is what a decide half is for. **The measure half is never
consulted**, which is the property the verdict actually depends on.

**A3 — two structural features are CONSTANT and are flagged, not scored.** `opt_right` and
`horizon` have exactly one bin each: **the banked book is 100% calls and 100% `swing`**. Their
`s_worst` is exactly 1.0 and so is every null draw, so they can never clear — which is correct,
but "did not clear" would read as evidence about calls versus puts when the book contains no
puts at all. They are reported as `degenerate` and excluded from the Q2 verdict. They remain in
the charged arm count.

## 8 · What would make this register void

* Any change to the exit policy, the fill model, or the frozen chains.
* Re-mining. This runs on the banked split-clean books only.
* Reading any measure-half number before the decide-half refusal set is fixed.
* Adding a feature not listed in §2 after seeing a result.
