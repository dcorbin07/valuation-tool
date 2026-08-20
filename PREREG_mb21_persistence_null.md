# PREREG — MB21: the persistence-preserving null for S22

**Registered 2026-08-19. Committed ALONE, markdown only, as a strict git ancestor of every
measurement commit.** Executes `VALQUO_MASTER_AUDIT_4.md` item `MB21`, which the audit ranks
highest-EV in the document.

**This register may end with copy coming OFF the product.** The kill condition in §6 is
pre-committed in both directions and is written down before the number it turns on is read.

---

## 0. What is being tested, and what is NOT

`S22` measured the term structure of the equity composite's edge and classified it
**CONSTANT-RATE**: annualised top-decile alpha essentially flat from one quarter to two years,
cumulative alpha reaching **+10.1994%** at eight quarters, alpha HAC *t* never below 3.16 and
**3.8301 at H=504**. Every horizon beyond H=63 was scored against a per-horizon
`fixed_weights_null` built from `fundamental_panel.placebo_panel`, whose own docstring states the
method: *"Within each rebalance date, permute the signal columns AS A BLOCK across the names
present."*

**A within-date permutation destroys the signal's time-series persistence completely.**
Boudoukh–Richardson–Whitelaw (RFS 2008) is that a *persistent* regressor combined with
*overlapping* long-horizon returns makes long-horizon β and R² rise **mechanically under a
no-predictability null**. `S22`'s null therefore cannot generate the one artifact its own headline
shape most requires excluding, and the shortfall grows with horizon — the axis the headline lives
on.

**This register builds a null that remembers, and re-scores `S22` against it.**

**It is NOT** a re-run of `S22`, not a new hypothesis, and not a search. No arm of `S22` is
recomputed for the purpose of moving it: every observed value the kill condition reads is **read
from the shipped `data/free_analysis/TERM_STRUCTURE.json`**, pinned in §5 below, so the target
cannot move once the floors are known.

---

## 1. The premise, MEASURED before this register was written (read-only, zero trials)

On `panel_corrected_69d.pkl` / `panel_s22_h504.pkl`, deployed flat 1/8 over the seven weighted
themes, per-name rank autocorrelation of the composite across rebalances:

| lag (quarters) | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| **real composite (shipped `composite_from_frame`)** | **0.5677** | 0.4709 | 0.4433 | **0.3983** |
| **within-date `placebo_panel`**, seeds 1000 / 1001 / 1002 | −0.0016 / +0.0010 / +0.0016 | — | — | — |

68 date pairs at lag 1, median 1,548 matched names.

Per theme at lag 1: **`size` 0.9915**, `capital_discipline` 0.8882, `value` 0.6981,
`quality` 0.6786, `momentum` 0.6414, `insider` 0.3152, `institutional` 0.1181.
**Every one of these seven reproduces the audit's own table to four decimals.**

### 1a. A CORRECTION TO THE AUDIT, made before any verdict and immaterial to it

The audit reports the **composite** at lag 1 **0.5802** (median 0.5718, min 0.4073, max 0.7109)
and lag 8 **0.4099**. Measured with the **shipped** composite — `composite_from_frame`, which
renormalises by the present-weight mass, the convention audit `B7` established as *the* composite
— it is **0.5677 / 0.3983** (median 0.5668, min 0.4372, max 0.6794).

The gap is diagnosed rather than asserted: a raw 0.125-weighted sum with **no renormalisation**
reproduces the audit at **0.5796 / 0.4134** (median 0.5733). 16.3% of rows on a mid-panel date are
missing at least one of the seven, so the two conventions genuinely differ. **The audit measured
persistence on a composite that is not the one `S22` scores.**

**This changes nothing about `MB21`.** The premise is 0.57 against 0.00, and it is 0.57 against
0.00 under either convention. **The register uses the SHIPPED composite throughout**, because the
null must resemble the object `S22` actually measured. Recorded because the audit's numbers will
otherwise be quoted as reproduced when they are reproduced only approximately.

---

## 2. The instrument — fixed here, before it is written

**`persistence_panel(panel, seed)`: draw ONE permutation π of the name list and apply it at EVERY
date.** Row `(date d, name i)` takes its signal columns from row `(d, π(i))`. Where `π(i)` is not
present at `d`, the signal goes NaN and the row drops out of that date's cross-section.

That is the audit's literal specification — *"permute each name's whole signal time series"* —
and it is the single change from `placebo_panel`: **one permutation for the whole panel instead of
an independent permutation per date.**

Permuted columns are exactly `placebo_signal_cols(panel)`, the same set `placebo_panel` uses.
`fwd_ret*`, `marketcap`, `sector` and `bench_ret` **do not move**.

What it preserves, and why each matters:

* **per-name persistence** — a name inherits a *real* name's whole path, so the autocorrelation is
  the real one by construction. **This is the property the incumbent null lacks and BRW requires.**
* **cross-theme correlation** — whole rows move together, so Σ is a real Σ.
* **the per-date value distribution**, up to the surviving subset.
* **signal ⊥ return** — name *i*'s returns are paired with name π(*i*)'s signal. This is the null.

### 2a. The cost, stated in advance rather than discovered

A name survives a date only if its donor is present that date, so **coverage falls: ~66% of rows
kept, per-date cross-section ~1,557 → ~950.** This is real and it is the instrument's one genuine
weakness. It is controlled by `C5` (§4) and its attribution is fixed in §7.

### 2b. The coverage-preserving variant is DISQUALIFIED, on measurement, before the run

The obvious way to avoid that cost is to permute **within exact presence-pattern strata** (986 of
2,531 names are present on all 69 dates). It keeps 96.7% of rows. **It is not a null and it is
rejected here rather than after seeing whether it flattered the result.** Measured over three
seeds: ~170 names per draw are paired with **themselves**, and the residual association with
forward returns is live — H=504 median rank IC **+0.01067 at *t* +4.106**, H=63 *t* +1.630 /
+2.039 / +3.029. Pairing within a lifespan stratum pairs a name with a name of similar era and
size, and `size` is both the most persistent theme (0.9915) and, per `X3`, the carrier of the
composite's entire significance.

**Stratifying to protect coverage smuggles the signal back in. Coverage is not the property a null
has to have; independence is.**

---

## 3. Design — every number fixed now

* **Panel**: `data/free_analysis/panel_s22_h504.pkl`, unchanged, no rebuild.
* **Dates**: `S22`'s own `common` set — **62 dates, 2009-01-15 → 2024-04-24** — restricted BEFORE
  permuting, exactly as `S22`'s placebo does. Like-for-like or nothing.
* **Weights**: `S22`'s `DEPLOYED`, flat 0.125 over the seven weighted themes.
* **Horizons**: 63, 126, 189, 252, 315, 378, 441, 504. HAC lag `max(1, h//63 − 1)`, `S22`'s rule.
* **Draws**: **200**, seeds **3000–3199**. 200 matches `S22`'s null exactly; the seed base differs
  so no reader can mistake one instrument's rows for the other's.
* **Scoring**: the **shipped** `quantile_backtest` at `n_q=10` with `return_series=True`, through
  `S22`'s own `arm()` shape. Nothing is reimplemented.
* **Floors**: the p95 across draws of `alpha_t_hac`, `ls_t_hac`, `alpha_t_naive`, `ls_t_naive` at
  each horizon — the same four statistics and the same percentile `S22` published.
* **Artifact**: `data/free_analysis/MB21_PERSISTENCE_NULL.json`, labelled
  `instrument: "persistence_preserving_null"`, carrying `not_comparable_with` naming both the
  X7/session-10 floors (those include CPCV adoption) and `S22`'s `fixed_weights_null`.

**`S22`'s own artifact is never written to.** `TERM_STRUCTURE.json` is opened read-only.

---

## 4. Controls — C1–C4 GATING, computed and READ in their own pass before any floor is read

`--floors` **refuses to run** without a controls artifact whose `all_gating_pass` is true. This is
the two-pass design session 26's defect forced and `MA31`/`MA32` and `DEEPITM-FIN` have since
made standard; running a gating control in the same pass as the outcome it gates is what this
avoids.

* **C1 — HARNESS IDENTITY (gating).** Re-run the **within-date** `placebo_panel` at `S22`'s own
  seeds **2000–2004** and reproduce its stored `alpha_t_hac` and `ls_t_hac` at all eight horizons
  to `< 1e-9`. If my scoring path is not bit-for-bit `S22`'s, every comparison below is between
  two different instruments and nothing may be read. **This is the strongest control available and
  it costs five draws.**
* **C2 — PERSISTENCE RETAINED (gating).** Over 20 sampled draws, the placebo composite's per-name
  lag-*k* rank autocorrelation must sit within **±0.05** of the real composite's at *k* = 1, 2, 4,
  8 (real: 0.5677 / 0.4709 / 0.4433 / 0.3983). A null that does not actually remember is not the
  null this register claims to build.
* **C3 — ASSOCIATION NIL (gating).** The mean across 200 draws of each draw's median rank IC
  against that horizon's own forward return must lie within **±0.003** of zero at H=63 and H=504.
  This is the check that killed the stratified variant in §2b and it must be applied to the
  primary with equal force.
* **C4 — THE NULL IS CENTRED (gating).** `|median alpha_t_hac|` across the 200 draws must be
  **< 0.5** at every horizon. `S22`'s own C4; a null centred away from zero is a broken
  instrument, not a hard bar.
* **C5 — THE THINNING CONTROL (diagnostic, NOT gating, and NOT a rescue).** 200 **within-date**
  draws under the **same donor-absence mask** as the primary, seeds 3000–3199. Isolates how much
  of any floor movement is coverage rather than memory. **See §7 for the rule that governs it.**
* **C6 — FIXED POINTS COUNTED.** Names paired with themselves per draw (expectation ≈ 1 of 2,531
  under a uniform permutation). Reported; flagged if the mean exceeds 5.
* **C7 — NO FORWARD RETURN IS EVER PERMUTED.** `S22`'s own assertion, kept verbatim: the run
  raises if any `fwd_ret*` column appears in the permuted set.
* **C8 — EFFECTIVE COVERAGE IS PRINTED, NOT ASSUMED (`MB7`'s rule, ported).** `MB7` and
  `RUN_RULES` PART A rule 10 require a register to print the coverage the statistic is **actually**
  measured on rather than the coverage it appears to have. Ported here: the artifact carries, per
  horizon, the **effective** rows, dates and per-date cross-section the null scores on, beside the
  real panel's. The run **refuses** if a placebo date's cross-section falls below **100 names**
  (10 × `n_q`), or if the scored date count differs from `S22`'s 62.

---

## 5. The observed values, PINNED — read from the shipped artifact, never recomputed for the kill

`data/free_analysis/TERM_STRUCTURE.json`, `primary_common_dates`, all at `n_periods` 62:

| H | quarters | `cum_alpha` | `alpha_t_hac` | `ls_t_hac` | S22's within-date `alpha_t_hac_p95` |
|---|---|---|---|---|---|
| 63 | 1 | 0.016464 | 3.769517 | 2.716742 | 1.515082 |
| 126 | 2 | 0.033350 | 4.383563 | 2.711050 | 1.310095 |
| 189 | 3 | 0.045202 | 3.291237 | 2.144602 | 1.533467 |
| 252 | 4 | 0.061403 | 3.160784 | 1.856050 | 1.488439 |
| 315 | 5 | 0.077910 | 3.423956 | 1.649534 | 1.561426 |
| 378 | 6 | 0.086024 | 3.388747 | 1.163233 | 1.555306 |
| 441 | 7 | 0.088639 | 3.418033 | 0.661859 | 1.553847 |
| **504** | **8** | **0.101994** | **3.830087** | 0.684638 | **1.671991** |

For reference and not as a bar: the within-date null's **maximum** `alpha_t_hac` over 200 draws at
H=504 is **3.039150**, i.e. the observed 3.830087 exceeds every draw of the incumbent null.

---

## 6. THE KILL CONDITION — pre-committed in both directions

**The decisive cell is H=504, `alpha_t_hac`, and it is read FIRST.**

> **If the persistence-preserving null's H=504 `alpha_t_hac_p95` lies BELOW 3.830087**, `S22`
> stands, the null upgrade is recorded as a **confirmation** that strengthens the record, and the
> item closes. No product copy changes.
>
> **If it lies AT OR ABOVE 3.830087**, `S22`'s two-year claim is **NOT SUPPORTED against the null
> its own shape requires**, and **`S22-DISPLAY`'s two-year copy is WITHDRAWN OR RE-SCOPED.**

Named exactly, so the withdrawal cannot later be negotiated down to a footnote — all in
`valuation/web/hold_horizon.py`, rendered by `app.py` into `index.html` and `/methodology`, pinned
by `tests/test_hold_horizon.py`:

* `DEFENSIBLE` — the sentence *"…and was still ahead by about 5.1% annualized two years later…"*
* `ALPHA_ANN_TWO_YEARS = 5.1`
* `RANK_IC_TWO_YEARS = 0.0655` and the rank-IC-rises-with-horizon corroboration, **which is the
  exact statistic BRW's null predicts under no predictability** and therefore falls with it
* the `VERDICT = "CONSTANT-RATE"` classification as displayed

**THE PRODUCT EDIT IS ROUTED, NOT MADE HERE.** This lane writes the finding, the ledger row and
the handoff; changing shipped copy is the app lane's, against `hold_horizon.py`'s own
`BANNED`-tuple-against-the-rendered-payload discipline. **Routing is not deferral: the register
commits to the withdrawal, and the row stays open until the copy is gone.**

**Ambiguity resolves against the claim.** If the floor lands within ±0.05 of 3.830087, that is
**NOT SUPPORTED** and the copy comes off (`RUN_RULES` A6 — ambiguous against a pre-committed
threshold is never a judgement call, and the burden of proof sits on the claim, not on the null).

### 6a. The other horizons, decided now so they cannot be chosen later

* H=63 through H=441 are **reported with their own new floors** and each is marked clears / does
  not clear. **They do not trigger the §6 withdrawal**, which is scoped to the two-year copy
  because that is the copy on the product.
* **If H=63's floor crosses its observed 3.769517**, that is a **material finding in its own
  right** — it would touch the headline rather than the term structure — and it is recorded as
  `HEADLINE-EXPOSED`, routed to its own register, and **explicitly NOT acted on here**. It is not
  in this register's power to withdraw the headline, and pretending otherwise would be a scope
  grab.
* **No horizon's result may be substituted for H=504's** in reporting the verdict.

---

## 7. Attribution — fixed now, and explicitly NOT a rescue

The decomposition that will be reported:

```
S22 published floor   (within-date, full coverage)      = baseline
C5                    (within-date, THINNED)            = baseline + coverage
PRIMARY               (persistence,  THINNED)           = baseline + coverage + memory
memory effect         = PRIMARY - C5
```

**THE KILL IN §6 FIRES ON THE PRIMARY FLOOR, WHOLE, AND ON NOTHING ELSE.** If C5 shows the rise is
mostly coverage rather than memory, that is recorded as **a limitation of this instrument
requiring a better one** — and **the withdrawal still happens**, because a claim that cannot be
shown to clear a defensible null does not get to sit on the product while a nicer null is built.

This clause exists because the audit named the exact failure mode: *"without that clause this
becomes an invitation to reinterpret."* **The decomposition is a diagnosis, never a defence.**

---

## 8. My prior, stated before the run

The audit's is *"~55% that at least one horizon crosses"*. Mine, per cell:

| prediction | odds |
|---|---|
| the new floors rise at **every** horizon | 90/10 |
| **H=504's floor crosses 3.830087 — the kill fires** | **45/55** |
| the rise is broadly monotone in horizon | 65/35 |
| H=63's floor rises **least** of the eight | 70/30 |
| the long-short floors rise proportionally more than the alpha floors | 60/40 |
| C5 shows coverage is NOT the main driver (C5 within +0.30 *t* of S22's published floors) | 70/30 |
| C1 reproduces `S22`'s stored draws exactly | 90/10 |

**I am marginally below the audit on the kill, and the reason is arithmetic rather than
instinct:** 3.830087 is a high bar — the observed H=504 alpha *t* is the **largest of the eight**,
above H=252's 3.160784 — so the floor must rise **2.29×** from 1.671991 to reach it. I expect a
large rise; I am close to even on whether it is that large.

**Two mechanisms are at work and only one is BRW's**, which is why I expect movement at H=63 too
rather than none: (a) BRW's overlap artifact, which requires overlapping windows and so is absent
at H=63 where horizon equals rebalance; and (b) a persistent signal selecting a **near-fixed
random portfolio**, so 62 windows deliver far fewer than 62 independent portfolio draws — which
bites at **every** horizon. **I did not register "H=63 must not move" as a falsification test,
because mechanism (b) predicts it will, and a bar I cannot justify is worse than no bar.**

---

## 9. Trial accounting — decided before running, not after

**1 trial, INFRA.** Constructing and validating a null is infrastructure, on the `HACFLOOR` /
`X7RECON` precedent, and **infra `N` gates no published claim**. Infra 15 → 16.

**Re-scoring `S22` against it charges nothing further.** The discipline permits a re-open on new
data, a new instrument, or a new design; this is a **new instrument** applied to a landed claim.
It is not a new search and must not be charged as one. **Equity `N` stays 234; options stays
302.** `by_domain` for equity and options must be **bit-identical** across this session's log
append, and that is asserted rather than assumed.

`BACKTEST_RESULTS.json` needs no re-run: the equity denominator does not move, so no HLZ hurdle
and no Deflated Sharpe changes.

---

## 10. Void conditions — any one of these voids the verdict

1. **The gating controls are not read in their own pass**, or `--floors` runs without a passing
   controls artifact.
2. **The kill threshold is restated** after any floor is read. 3.830087 is fixed in §5 and comes
   from the shipped artifact.
3. **A different statistic is substituted for `alpha_t_hac` at H=504** after the fact, or another
   horizon is reported as the verdict.
4. **The percentile is moved** off p95, or the draw count off 200.
5. **C5 is used to rescue a crossing** (§7).
6. **Any file under `valuation/` other than a new study module is changed** — this register adopts
   nothing and touches no live scoring path. `hold_horizon.py` is **not** edited by this lane.
7. **`TERM_STRUCTURE.json` is written to.**
8. **The stratified variant of §2b is promoted to primary** after seeing that it flatters the
   result.
9. **A floor is quoted against a bar it was not calibrated on** — these floors are
   `persistence_preserving_null` and may never be compared with X7's 2.2837 / 2.2913 / 1.8629,
   with `S22`'s `fixed_weights_null`, or with each other across horizons.
10. **Trials are charged to equity or options.**

---

## 11. What this register CANNOT establish, stated so it is not over-read

* **It cannot show `S22` is wrong.** A crossing shows the two-year claim is not separable from a
  null that remembers — never that the edge is absent. `NULL` means *"could not be separated at
  this resolution"*, this record's most repeated correction.
* **It cannot rescue the long-short leg**, which already fails its own within-date floor at H=315
  and beyond, and nothing here improves it.
* **It says nothing about H=63's headline** beyond the diagnostic in §6a.
* **It is one panel.** A better null on the same 62 dates is still the same 62 dates.
* **The instrument's coverage cost is genuine** (§2a) and the decomposition in §7 bounds it
  without eliminating it. A coverage-lossless persistence-preserving null on this panel is an open
  problem — §2b shows the obvious construction is not one.
