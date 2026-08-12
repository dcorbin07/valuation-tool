# PRE-REGISTRATION — S8 + S9: signal freshness and data staleness

**One register, both items, committed before any arm has been scored.** They share machinery — the
age of a row's inputs at a rebalance — so they are registered together and the ages are computed
once.

Both rows are `src=auto`. §1 is the premise check.

---

## 0. THE FRAMING — and this one is genuinely uncertain

**Unlike the weighting-scheme family, these have a MECHANISM argument**, and the register says so
before running rather than after.

**FOR a real effect:**

* **The 13F decay curve is MEASURED, in this project, and it is steep.** The institutional signal
  peaks at Q−1, is still alive at Q−2 (*t* 1.36) and is **dead by Q−3 (*t* −0.04)**. That
  measurement exists and **is currently used for nothing** — every signal enters the composite at
  full strength however stale it is. A decay multiplier is the direct application of a number the
  project already trusts.
* **The story is mechanical, not statistical.** A signal computed from an 89-day-old filing is
  genuinely less informative about today than one computed from a 3-day-old filing, and the market
  has had 89 days to price it. That is a reason, not a correlation.
* **It is orthogonal to every theme by construction** — filing dates are a function of fiscal
  calendars, not of value, quality or momentum.

**AGAINST:**

* **The base rate.** Every combination- and weighting-flavoured item in this catalogue has been
  rejected, most recently five weighting schemes where CPCV's best challenger missed its bar by
  **79×**, and six interactions.
* **`days_since_filing` at a fixed quarterly grid is partly a proxy for FISCAL-YEAR-END**, which
  correlates with industry. A staleness gradient could be a sector effect wearing a freshness
  label — U7's failure mode, and S10's.
* **Shrinking a theme toward zero is not the same as removing it.** The composite renormalises by
  present-weight mass, so a decayed theme still occupies its weight; the arm is a *shrink*, not a
  *drop*, and its effect is correspondingly smaller than intuition suggests.

**THE ARGUMENT THAT LOOKS SUPPORTIVE AND IS NOT THE SAME HYPOTHESIS — stated here so it is not
leaned on afterwards.** P6 measured that **quarterly ROE/ROIC beats TTM** (roe *t* +2.84 vs +2.01,
roic +3.38 vs +2.57) and the record summarises it as *"recency beats smoothing"*. **That is a
result about the WINDOW a number is measured over, not about the AGE of the observation.** A
quarterly figure filed 89 days ago is still quarterly. S8/S9 ask a different question, and
treating P6 as evidence for them would be the same category error as reading a mean for an order
statistic. Likewise **S27**, rejected last session, weighted *dates* in the time series; S8/S9
weight *names* within a date. Three different senses of "recency", and only one of them has been
tested.

**WHICH WAY I LEAN, since the task asks:** I lean toward **the S9 gradient being real but the
weighted arms failing the gate** — because a conditioning variable showing a gradient and a
conditioning variable surviving conversion into a weight are different things, and this project
has separated them before (U7's composite decile was U-shaped and still useless as a veto).
**Confidence is deliberately lower than the weighting family's** — 65/35 rather than 80/20 —
because the mechanism argument is real. **Of the four arms, A4 (13F decay) is the one I most
expect to show something**, because its half-life is the only one taken from a measured decay
curve rather than a convention.

---

## 1. PREMISE CHECK

**(a) S9's PORT IS REAL: `days_since_filing` IS NOT ON THE EQUITY PANEL.** It exists only in
`options_autopsy.py:514`. The equity panel already picks its SF1 row point-in-time (`_pit`, latest
`datekey` on or before `as_of`) — **the row's AGE was simply never carried.** So the item is
buildable and the audit's "port it" is accurate. Added here as an **opt-in** emission
(`with_freshness`), so the default panel is untouched.

**(b) S8's "RELATED DEFECT" IS REAL AND CONFIRMED, AND IT IS STALENESS RATHER THAN LOOK-AHEAD.**
`bulk.prepare_daily` down-samples DAILY to **one row per ticker-month** — its own docstring says
so — so the point-in-time market cap and the re-priced EV equity leg can be **up to ~31 days
stale**, while the price feeding `_price_factors` is same-day. **But the same docstring is careful
that it keeps the last date actually present and never a future one, so this is a PRECISION
defect, not a correctness one.** It is **reported, not fixed here**: changing it would move
`size`, every EV-based value ratio and therefore the published headline, which is a results change
needing its own register. It is also **not name-specific in the way filing dates are** — it adds
roughly uniform noise rather than a cross-sectional gradient — so it does not confound these arms.

**(c) THE 13F AGE IS COMPUTED FROM THE SAME WINDOW THE SIGNAL USES.** `_inst_age_at` repeats
`_inst_accum_at`'s cutoff arithmetic exactly and returns `None` on precisely the inputs that make
the signal `None`, so the age describes the observation the signal is built from rather than a
differently-chosen one.

---

## 2. THE INSTRUMENT

One panel build with `with_freshness=True`; every arm a column on that one frame, so arms differ
in the freshness rule and nothing else. Identical `(date, ticker)` key sets, asserted.

**Ages, both in calendar days, both point-in-time by construction:**
`days_since_filing = as_of − SF1.datekey` (the row the panel already chose) and
`days_since_13f = as_of − quarter_end_used`.

**NO HALF-LIFE IS FITTED.** The audit asks for *"a half-life estimated per signal from its own
measured decay curve"*; **estimating a half-life on this panel and then scoring on it is the
in-sample selection this project has paid for repeatedly** (+8.43%/yr in-search → −0.04%/yr on the
locked hold-out). Both half-lives are therefore **fixed here, before any arm runs**:

* **Fundamentals: 90 days**, one reporting quarter. A convention, and labelled one.
* **13F: 180 days**, taken from **the project's own measured decay** — alive at Q−2 (*t* 1.36),
  dead by Q−3 (*t* −0.04) — so the signal dies somewhere between 180 and 270 days and 180 is the
  conservative end. **This is the one half-life with empirical backing, and it is backing that
  pre-dates this register.**

**WHICH THEMES CARRY WHICH AGE, fixed now:** the fundamental decay applies to **`value`,
`quality` and `capital_discipline`** — the themes built from SF1 line items. It does **not** apply
to `momentum` or `size` (price-based, same-day), to `insider` (Form 4 dates, a different clock) or
to `institutional` (13F, which is A4's job).

**BOOK-LEVEL VERDICTS ONLY.** No arm may be promoted on a per-signal or per-theme IC — now
demonstrated seven times.

---

## 3. THE ARMS

* **A1 — S9 DIAGNOSTIC (no verdict, charges nothing).** Top-decile forward return by
  `days_since_filing` **quartile**, exactly as the audit's method asks, plus the same split for
  `days_since_13f`. **This is a measurement with no threshold**, and per the audit's own
  sequencing it is what tells us whether a gradient exists *before* anything is turned into a
  weight.
* **A2 — S9 FRESHNESS AS AN INPUT.** `z(−days_since_filing)` added as an eighth input at 0.125,
  the same construction S7 used. Fresher = higher score.
* **A3 — S8 FUNDAMENTAL DECAY.** `value`, `quality`, `capital_discipline` each multiplied by
  `exp(−days_since_filing / 90)` before the composite.
* **A4 — S8 13F DECAY.** `institutional` multiplied by `exp(−days_since_13f / 180)`.
* **A5 — S8 COMBINED.** A3 and A4 together.

A row with no computable age is **left undecayed and undropped** — never assigned a punitive age.
Imputing staleness would convert an availability gap into a signal, which is S10's failure mode.

---

## 4. THE GATE

The shipped margins: **≥ +100 bps top-decile alpha AND ≥ +0.25 long-short *t*, in BOTH halves,
boundary embargoed** — as used by `SECTOR-NEUTRAL-B6`, `S20`, `S21`, `S3`, `S16`, the five-scheme
family and `S7`/`S18`. **ADOPT-ELIGIBLE** iff both margins clear in both halves; otherwise
**REJECTED**; ambiguous is a **NULL** (`RUN_RULES` A6).

**FAMILY-WISE:** four verdict arms against one bar. A single clearing arm is recorded
**`ELIGIBLE — UNREPLICATED, 1 OF 4 SIBLING ARMS`**, never "adopted", and that label travels with
the figure. At-least-one-clears is roughly an **18%** event under independence; the arms are
positively correlated (A5 contains A3 and A4), so that is an upper bound.

---

## 5. CONTROLS — read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record** (alpha 0.07174142332098163, LS *t*
  2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909). **ABORTS**
  otherwise.
* **C2 — identical rows** across arms.
* **C3 — no arm is inert**: within-date rank correlation against the deployed composite.
* **C4 — COVERAGE FIRST.** Both ages' non-null rates reported before any verdict.
* **C5 — THE AGES ARE SANE, AND THIS IS THE ONE THAT COULD INVALIDATE EVERYTHING.** No age may be
  **negative** (that would be a look-ahead: a filing dated after the scoring date), and
  `days_since_filing` should sit mostly within a reporting cycle. The distribution is reported, and
  **any negative age aborts the arm.**
* **C6 — THE STALENESS GRADIENT IS NOT A SECTOR GRADIENT.** The freshness quartiles' sector
  composition is reported. **If one sector dominates the stale quartile, A1's gradient is partly a
  sector bet** — U7's failure mode, and S10's — and must be labelled as such rather than read as a
  freshness effect.
* **C7 — the decay actually bites.** The mean and range of `exp(−age/HL)` per arm is reported. A
  multiplier concentrated near 1.0 changes nothing and its arm's verdict is meaningless.

---

## 6. ADOPTION

Any arm is a **VINTAGE EVENT**. The current vintage is **DERIVED, never assumed** (`PT-GAPDUE`) at
run time. **No arm is adopted by this register**; an eligible arm is recorded ELIGIBLE with the
§4 label. Nothing in the live scoring path changes.

---

## 7. EXPECTATIONS, per arm, before any arm was scored

1. **A1's gradient EXISTS but is modest — 55/45**, and I expect it **monotone in the fresh
   direction** if it exists at all. This is the arm I am least sure about, which is the point of
   measuring it first.
2. **A2 (freshness as an input) fails — 70/30.** A conditioning variable that shows a gradient
   rarely survives being made a signal; U7 is the precedent, where a U-shaped decile structure was
   useless as a veto.
3. **A3 (fundamental decay, 90d) fails — 70/30.** The half-life is a convention, and shrinking
   three themes toward zero for stale names is a small perturbation once the composite
   renormalises.
4. **A4 (13F decay, 180d) fails — 60/40, and it is the arm I most expect to surprise me**, because
   its half-life comes from a measured decay curve rather than a convention. If any arm clears,
   this is it.
5. **A5 (combined) fails — 70/30**, and I expect it to land **between** A3 and A4 rather than
   beyond either, because the two decays touch disjoint themes.
6. **At least one of the four clears at least one half — 50/50.** A statement about noise across
   four correlated arms, not about an effect.
7. **C6 shows a NON-TRIVIAL sector skew in the stale quartile — 60/40.** Fiscal-year-ends cluster
   by industry, so I expect the gradient to be at least partly compositional. If so, that caveat
   travels with A1 permanently.

---

## 8. TRIAL COST

**Four verdict arms: equity `N` 176 → 180.** **A1 charges nothing** — it is a measurement with no
threshold and no adopt/reject, the same treatment the C7 dilution control got in S7. The premise
checks charge nothing.

`BACKTEST_RESULTS.json` is re-run **from a clean tree**.

---

## 9. WHAT THIS REGISTER DOES NOT DO

* It does **not** fix the DAILY month-end down-sampling (§1b). That moves `size`, every EV-based
  ratio and the published headline — a results change needing its own register.
* It does **not** fit any half-life (§2).
* It does **not** apply a freshness decay to `momentum`, `size` or `insider`.
* It does **not** put a per-name "data from N days ago" qualifier on the product surface. The
  audit notes it would be good positioning; that is the web lane's and needs its own decision.
* It does **not** re-open S27, which weighted dates rather than names (§0).
