# HANDOFF — the FREE lane (`free analysis`), session of 2026-08-03

Five items: **D3, R7, X6, X3, O2**. Thresholds for all five were committed in
`PREREG_free_analysis.md` **before** any run; nothing below was renegotiated after a number
appeared. Lane safety verified against the live tree, not inferred:

```
$ python check_lanes.py D3 R7 X6 X3 O2
SAFE — disjoint write sets, no import coupling, all dependencies met.
```

**The lane's hard rule held: no existing file was modified.** `git diff --name-only HEAD` is
empty. Six new files, listed at the end.

## Scoreboard

| item | verdict | one line |
|---|---|---|
| **D3** | **COMPLETE** | FF5+MOM+q5 landed and verified; **R1 is unblocked**. Caught a stale-URL trap that would have handed R1 a factor model ending in 2018. |
| **R7** | **COMMITTED** | Percentage floor retired; replaced by a derived power arm (**k ≥ 383 trades**) + a product arm. Binding cluster is **calendar month (deff 2.24)**, not ticker. |
| **X3** | **EARNS ITS COMPLEXITY** | Composite +11.88% vs best single signal +3.36%. But the curve **plateaus at five themes**, and themes 8–9 are actively destructive. |
| **X6** | **NULL** (9/10 series) | Only `size` breaks, and it **fails multiplicity**. Its endogenous date is **2006, not 2012** — the project's 2012 story is not confirmed. |
| **O2** | **REJECT** (audit of another lane) | Already executed on `worktree-options-live`. Fails all four pre-registered arms. Forecloses **D5 (ORATS)**. |

---

## D3 — fetch the free factor datasets → **COMPLETE**

**Committed bar (written first):** all of FF5 daily, momentum daily, q5 daily present; each
covering ≥ 1998-01-01 → 2025-12-31 with no interior gap > 5 trading days *within that span*;
script idempotent from a cold cache; manifest recording URL, SHA-256, rows, range, licence and
commercial usability; factor series compound to the 63-day grid without look-ahead. OSAP is a
*should*, not a *must* — R1 needs only Ken French and q-factors.

**Run.** `python scripts/fetch_factors.py` (and `--verify` for the idempotency check).

```
  [    ok     ] ff5_daily           15,854 rows  1963-07-01 -> 2026-06-30
  [    ok     ] mom_daily           26,173 rows  1926-11-03 -> 2026-06-30
  [    ok     ] q5_daily            14,848 rows  1967-01-03 -> 2025-12-31
  [    ok     ] ff5_monthly            756 rows  1963-07-01 -> 2026-06-01
  [    ok     ] q5_monthly             708 rows  1967-01-01 -> 2025-12-01
  [    ok     ] osap_signal_docs       331 rows  (Chen-Zimmermann signal documentation)
  [NOT FETCHED] jkp_global_factors  CC BY-NC 4.0 — NON-COMMERCIAL ONLY
D3 COMPLETE — every dataset R1 requires is present and verified.
```

Re-run is fully idempotent: every dataset reports `(cache)`, identical SHA-256s, same manifest.

**Compounding to the panel's 63-trading-day grid** (113 windows, each exactly 63 days,
1998-01-02 → 2026-04-23) gives numbers consistent with the literature, which is the real check
that the parsing is right:

| factor | ann. 1998–2026 | | factor | ann. |
|---|---|---|---|---|
| Mkt-RF | **+7.19%** | | q: R_MKT | **+7.14%** |
| SMB | +0.62% | | q: R_ME | +1.05% |
| HML | +0.70% | | q: R_IA | +0.96% |
| RMW | **+3.24%** | | q: R_ROE | +3.95% |
| CMA | +1.65% | | q: R_EG | +6.13% |

FF's market premium and the q-model's agree to 5bp, as they must. Weak HML and near-zero SMB
post-1998 are exactly the well-known post-publication pattern. The no-look-ahead guard passes:
each window **excludes** its own start date, so a factor return earned before the portfolio was
formed can never be credited to it.

### Two traps caught — the first is the reason this item was worth doing properly

1. **`.../q5_factors_daily.csv` (no year suffix) still returns HTTP 200 — and is a 2018
   snapshot.** It parses cleanly, looks perfectly healthy, and **ends seven years before the
   panel does.** Had R1 used it, the q-factor arm of the single most important test in the audit
   would have silently regressed the last seven years of returns against nothing. The live file
   is year-suffixed (`q5_factors_daily_2025.csv`); the script now resolves the current year from
   the listing page and falls back loudly. **This is the same failure class as the five silently
   empty factors** — an input that raises no error and is simply wrong.
2. **My own gap check was mis-specified** and failed `mom_daily` for holes in the 1920s–30s.
   The bar was "no interior gap within the panel's span"; the check now runs over 1998+ only.
   Fixed against the pre-registered wording, not the wording adjusted to the result.

**Licence discipline.** Output is split into `data/factors/parsed/` (usable) and
`data/factors/research_only/` (not). **JKP / Global Factor Data is registered as a deliberate
non-fetch** — CC BY-NC 4.0, research-only, never shippable — so the licence is on the record
rather than forgotten when X8 eventually wants it. Ken French and global-q state no explicit
commercial grant, so both are recorded `commercial_ok: null` (*unestablished*), not `true`.
Per the pre-registration, unestablished is treated as not-commercially-usable until someone
confirms it in writing. **Don should get that confirmed before any factor series reaches
product copy.**

**Unblocks: R1** (and X4, X8).

---

## R7 — the `term_slope` retention floor → **COMMITTED, results-free**

Full argument in **`R7_term_slope_retention_floor.md`**. **R2 must cite that file by name.**

**Disclosure, made up front:** I set this floor already knowing the incumbent is 40% and the
observed retention is 36.4% — unavoidable, since the item exists because of that gap. The
defence is that the floor is a function of four quantities, none of which is a retention figure:
`n`, `σ`, `deff`, and the adoption-time effect `D`. σ and deff were computed from the banked
broad log **without ever conditioning on the `term_slope` column**, which is present in that
file. The retention-versus-gain curve was not consulted. **The resulting floor is looser in
percentage terms than the 40% it replaces, and I flag that rather than bury it.**

**The argument.** The 40% conflates three worries and serves none:

- **Cherry-picking** — the real risk is selection among many thresholds, and that is controlled
  by *freezing* the threshold, which this filter already does (`+0.0105`, fitted on 55 names,
  applied unchanged to 133 that never informed it). **Once a threshold is frozen out of sample,
  36% vs 40% adds no cherry-pick risk at all.** A percentage was never the instrument for this.
- **Power** — real, but scales with the *count* retained. The percentage bar gets this
  backwards: the 55-name run cleared 40.6%; the 187-name run retains **more trades** at 36.4%.
  **The filter got statistically stronger and the bar called it weaker.**
- **Deployability** — real, a count, and a *product* decision, not a research threshold.

**Measured inputs** (unconditional, n = 3,042 closed trades, 185 names, 2016-01-19 → 2025-10-15):

| quantity | value |
|---|---|
| σ per-trade return sd | 0.8354 |
| **deff (calendar month)** | **2.24** — the binding cluster |
| deff (ticker) | 1.29 |
| deff (ticker × month) | 1.00 |
| **n_eff** | **≈ 1,360** of 3,042 |
| D (adoption-time, fixed) | 0.13670 |

**The clustering result is itself worth keeping:** the dependent unit is the *calendar month*,
not the *name*. A market-wide vol regime moves every open long call together, so 3,042 trades
carry the information of about 1,360. Any floor ignoring this is overstated by ~50%. This is
the same disease as audit finding **G** (correlated megacap long calls treated as independent)
and it is now quantified.

> **Arm A (research, binding): k ≥ 383 retained trades** — the count at which the adoption-time
> effect would be detectable at t ≥ 2.0 under month-clustered inference. For any other universe
> the floor is the **formula**, re-solved with that run's own n, σ, deff, and **D held fixed**.
>
> **Arm B (product, reported not gated): ≥ 3 average concurrent positions** (≥ 60 alerts/yr).

**A product fact Don should see plainly:** the repo commits to `MAX_CONCURRENT = 10`
(`options_vrp.py:211`). Filling a 10-position single-leg book needs **63.9%** retention — far
more than `term_slope` keeps, *or has ever kept, including at its 40.6% adoption*. **No version
of this filter has ever produced a 10-position single-leg book.** That is why Arm B sits at 3,
and Arm B's 3 is a judgement call where Arm A's 383 is derived.

**This item scores nothing.** R2 does the re-scoring, and **R2 is still gated on B1** (corrupted
spot). Committing the bar while the result is still unknowable is exactly the right order.
One trap flagged for R2: the strict out-of-sample slice has its own n = 1,132, not 3,042 —
apply the formula to the universe actually scored and say which n was used.

---

## X3 — ablate to the best single signal → **EARNS ITS COMPLEXITY**

**Committed bars (written first):** earns its complexity iff full-composite top-decile alpha
beats the best single signal by ≥ 2.0pp **and** the best 3-theme prefix by ≥ 1.0pp; flat-after-
three iff the latter < 1.0pp; decoration iff the former < 2.0pp. Anything between = null.

**Run.** `python -m scripts.ablation --panel data/free_analysis/panel.pkl` on the **full
2,710-name × 110-date universe** (136,478 rows, 1998-12-31 → 2026-04-22), 63-day horizon,
deciles. **Not a smoke test.**

**Validation that the panel is the right one:** the deployed composite reproduces the project's
documented post-EV-fix configuration **exactly** — LS t **3.520**, alpha **+11.88%** — matching
CLAUDE.md's "LS t 3.396 → 3.520, alpha +11.82% → +11.88%". The machinery is measuring the thing
the project thinks it deploys.

```
       full composite  +11.88%   |  best single (gp_on_capital)  +3.36%   |  best 3-prefix  +7.12%
       gain vs single  +8.52pp  (bar +2.00pp)     gain vs 3-prefix  +4.76pp  (bar +1.00pp)
```

Both bars cleared decisively. **The seven-theme architecture is not decoration.**

### The curve is the real result — and it is not monotone

| k | theme added | alpha | marginal |
|---|---|---|---|
| 1 | quality | +0.96% | — |
| 2 | momentum | +7.12% | **+6.16pp** |
| 3 | capital_discipline | +5.04% | −2.08pp |
| 4 | institutional | +6.08% | +1.04pp |
| 5 | **size** | **+12.26%** | **+6.18pp** |
| 6 | value | +12.01% | −0.25pp |
| 7 | growth | +11.53% | −0.48pp |
| 8 | **low_risk** | +6.12% | **−5.41pp** |
| 9 | insider | +6.61% | +0.49pp |

Three things follow, and only the first was the pre-registered question:

1. **The architecture earns its complexity vs 1 and 3 themes — but the plateau starts at five.**
   Themes 6 and 7 add nothing (−0.25pp, −0.48pp). The top-5 equal-weighted book actually beats
   the deployed composite on top-decile alpha (**+12.26% vs +11.88%**) and monotonicity
   (**−0.988 vs −0.952**), while losing on long-short t (3.168 vs 3.520). Reported as a fact,
   **not** as a recommendation — the ordering is in-sample-informed (see caveat).
2. **`low_risk` costs −5.41pp, the largest single negative in the curve.** This independently
   corroborates the project's live decision to zero it, on a *different construction* (equal-
   weighted ablation) from the one that made the original call.
3. **The strongest theme by IC produces almost no book.** `quality` has the highest theme IC
   (t +3.39) and its decile book is worthless: alpha +0.96%, monotonicity −0.067, and its
   **worst** decile earned the most (21.0% vs 17.5% for the best). `gp_on_capital` alone
   (+3.36%) beats the entire quality theme it belongs to.

### Mechanism — one story explains the whole curve

Quality's IC is real but thin and evenly spread (median +0.036; still +0.014, t +2.65, with the
top and bottom deciles removed). A decile book needs the top 10% specifically, and there quality
is a **large-cap tilt**: the top-quality decile is **1.66×** the universe's median market cap.
Theme correlations with `size` on this panel:

```
  low_risk −0.365    quality −0.268    capital_discipline −0.216    momentum −0.207
```

The first four themes in the curve are all size-anticorrelated, so the prefix accumulates a
large-cap tilt with nothing offsetting it — and the benchmark is an *equal-weighted* universe
that enjoys the small-cap premium. Adding `size` at k=5 releases that tilt (**+6.18pp**); adding
`low_risk` at k=8 — the most size-anticorrelated theme in the matrix — cancels it again
(**−5.41pp**). The −0.365 independently reproduces CLAUDE.md's documented −0.352.

**So the composite's alpha is substantially a size-tilt-management story, not a stack of
independent edges.** That is a direct input to **R1**: if the alpha is a managed SMB exposure,
FF5's SMB should absorb a large share of it. **X3 and R1 should be read together.**

**Pre-registered caveat, honoured:** the ordering is by full-sample theme IC and is therefore
in-sample-informed, which flatters early steps and biases the test *toward* "architecture
unnecessary". The result went the *other* way, which is the more trustworthy direction — stated
in advance for exactly this reason. But it also means the curve's non-monotonicity is partly an
artifact of ordering by a statistic (IC) that demonstrably does not predict book value.

**Do not adopt the top-5 book off this run.** It is in-sample-informed and must clear
`holdout_theme_validate()` first — the same gate that killed `insider` and `sector_neutral`.

**Informs:** S5 (hierarchical shrinkage), S7 (interactions), S4 (growth carries zero weight),
and the honest product description.

---

## X6 — structural-break test → **NULL** (and the 2012 story is not confirmed)

**Committed bars (written first):** BREAK iff supF(1|0) exceeds its bootstrap 95th percentile
**and** the break-date 90% CI ≤ ⅓ of the sample; DRIFT if the first passes and the second fails;
NULL otherwise; significance after **Holm–Bonferroni** across the ten series. Stated in advance:
*power is low and a null is the expected outcome for most themes; a null means keep the full
sample, not "nothing changed".*

**Run.** `python -m scripts.breaks --panel data/free_analysis/panel.pkl`, 110 rebalance dates,
1998-12-31 → 2026-04-22, ε = 0.15, 5,000 bootstrap reps.

```
series                  supF  crit95    boot   param       p    holm  verdict   break date
value                  7.131  12.270  12.270   8.669  0.2336   1.000    NULL   2020-10-13
quality                3.304  10.361  10.361   8.733  0.5822   1.000    NULL   2021-01-13
growth                 2.302   9.086   9.086   8.720  0.7076   1.000    NULL   2020-10-13
momentum               3.328   8.479   7.203   8.479  0.3530   1.000    NULL   2003-04-08
insider                3.004   8.716   8.716   8.624  0.5356   1.000    NULL   2017-04-12
low_risk               1.453   8.376   7.367   8.376  0.8404   1.000    NULL   2021-04-15
capital_discipline     7.543  13.510  13.510   8.350  0.2452   1.000    NULL   2020-10-13
size                  12.384  10.664  10.664   8.480  0.0274   0.274   BREAK   2006-04-07
institutional          4.444   8.943   8.081   8.943  0.2512   1.000    NULL   2019-01-14
__composite           10.002  14.249  14.249   8.947  0.1248   1.000    NULL   2003-01-07
sentiment            — empty (0 dates)
```

**Nine of ten series: NULL. The one candidate — `size` — fails multiplicity (Holm p = 0.274).
X6 returns a NULL overall.** Per the pre-registration that means **keep the full sample**; it
does *not* mean nothing changed.

### The `size` result, stated carefully

Uncorrected it is a localised break at **2006-04-07**, with mean IC falling from **+0.0912
before to −0.0041 after** — economically large, the small-cap premium going from strong to
nothing. But:

- **The date is 2006, not 2012.** The project's belief that `size` flipped "around 2012" came
  from splitting the sample at its midpoint. Given the chance to choose its own date, the data
  picks 2006. **The 2012 story is not confirmed.**
- The 90% CI on the date runs **2003-10-07 → 2012-01-09** — over eight years wide. It met the
  ≤⅓-of-sample bar (0.300), but 2012 sits at its extreme upper edge, so the CI does not exclude
  the old story either. **The honest statement is that the date is barely identified at all.**
- It does not survive correction for having tested ten series.

### Methodology note worth keeping

The pre-registration required a bootstrapped null rather than the published Bai–Perron table,
and that decision paid for itself twice:

- **The implementation was validated**: fed i.i.d. normal data the statistic returns a 95th
  percentile of 8.77 at n=110, converging to 8.18 by n=500, against Bai–Perron's published
  **8.58**. It is the textbook statistic.
- **The block bootstrap alone was measured to be anti-conservative** (6.31 on i.i.d. data vs the
  correct ~8.8), so the critical value used is `max(block-bootstrap, parametric i.i.d.)`. The
  block bootstrap then correctly *raised* the bar above that floor for the autocorrelated series
  (value 12.27, capital_discipline 13.51, composite 14.25 — lag-1 autocorrelations +0.21, +0.25,
  +0.20; n_eff 72, 67, 73 against n = 110).
- **This prevented a false positive.** At the naive published 8.58 the **composite** IC series
  (supF 10.002) would have been declared a structural break. Against its own bootstrapped null
  of 14.25 it is a clear NULL.

**What it unblocks / forecloses.** **S27** (weight recent observations more) was gated on this
and is **not supported**: the test cannot distinguish break from drift, so neither remedy —
excluding pre-2006 data nor exponential down-weighting — has an evidential basis. If `size` is
pursued, test it *directly* against the held-out gate rather than inferring a remedy from a
break test this sample cannot resolve. Note X3 found `size` contributes the single largest
positive marginal (+6.18pp), so it is worth pursuing — just not via S27 on this evidence.

---

## O2 — cross-sectional VRP (Goyal–Saretto) → **REJECT** (audit, not an independent test)

**⚠ Scope change, reported rather than worked around.** O2 **has already been executed by
another lane.** `worktree-options-live` commit `64955ef` ("Deep research #2: pre-specify the
cross-section, signs declared before any sort") ships `options_xsection.py` and
`data/options_xsection/XSECTION_RESULTS.json`, covering Goyal–Saretto `iv_rv` **plus** Cao–Han
(**O3**), Boyer–Vorkink (**O4**) and vol-of-vol (**O5**). **That branch is not merged to `main`.**

I did **not** rebuild it. Doing so would have created a competing `opt_xsec.py` against a
committed `options_xsection.py` — precisely the collision this lane exists to avoid. Instead I
scored the existing result against **the audit's own pre-registered thresholds, quoted verbatim**:

> *Quintile monotonicity in the correct direction; long-short t > 2.0 under a date-block
> bootstrap; positive in both held-out halves. And — this is the one that will bind — the effect
> must survive the spread.*

**Disclosure:** I read the numbers before scoring them, which is why the bar is copied verbatim
from the catalogue rather than restated by me. This is an **audit of another lane's result**, not
an independent pre-registered test of my own.

| arm | result | pass? |
|---|---|---|
| quintile monotonicity, right direction | 0.2 (their own bar 0.6); quintile returns **[+3.9%, +1.7%, +9.1%, +15.7%, +3.0%]** — peak in Q4, no ordering | **FAIL** |
| long-short t > 2.0 | **0.143** | **FAIL** |
| positive in both held-out halves | early +0.34, late **−0.95** → `both_positive: false` | **FAIL** |
| survives the spread | already priced at the ask on both legs; long-only Q1 excess **−2.72%, t −0.692** | **FAIL** |

Supporting: deflated Sharpe **0.020**, FDR p = 1.0, no discovery. The other lane's own verdict is
*"SUGGESTIVE — nothing clears the gate"*, `adopted: []`.

**Verdict: REJECT on all four arms.** Not merely underpowered — the point estimate is *negative*
and there is no quintile ordering. n = 71 months (46 dates dropped as thin) is a real power
limit, but underpowering explains an insignificant positive, not a negative with no monotonicity.

**Two things worth carrying forward from that lane's run:**
- `idio_vol` (Cao–Han, **O3**) is monotone at **0.9** but in the direction **contradicting** the
  published sign — flagged by their own machinery as `contradicts_published_sign`. A straddle is
  only an approximation of Cao–Han's delta-hedged call, so this is suggestive, not a refutation.
- `illiq` — included as a **mechanical control that can never be a discovery** — is the only
  characteristic with LS t > 2 (2.46). That is the correct way to read a control firing: it
  says the panel has an illiquidity gradient, not that an edge was found.

**Forecloses D5 (ORATS procurement), which the audit explicitly gated on O2.** Do not buy the
ORATS surface on the strength of the cross-section: the cross-section is not there. **O3, O4, O5
and O6 were all gated on O2 and should be considered answered by that same run**, not re-opened
separately.

---

## Files (all new — no existing file modified)

| file | item |
|---|---|
| `PREREG_free_analysis.md` | thresholds for all five, written first |
| `R7_term_slope_retention_floor.md` | **R7 deliverable — R2 must cite this** |
| `scripts/fetch_factors.py` | D3 |
| `scripts/dump_panel.py` | shared X3/X6 input (one build, reused) |
| `scripts/ablation.py` | X3 |
| `scripts/breaks.py` | X6 |
| `data/free_analysis/{panel.pkl, ABLATION_RESULTS.json, BREAKS_RESULTS.json, BREAKS_RESULTS_ic_series.csv}` | outputs (gitignored) |
| `data/factors/**` + `MANIFEST.json` | D3 datasets (gitignored) |

**`HANDOFF_STATUS.md` was deliberately NOT updated.** CLAUDE.md asks for it, but it is an
existing file and this lane's defining property is that it modifies none — with six agents live
on the tree, editing the shared status file is exactly the clobber CLAUDE.md's own
"parallel agents each own a separate `HANDOFF_<name>.md`" rule exists to prevent. **Don or a
single-owner session should fold this file's scoreboard into `HANDOFF_STATUS.md`.**

## Recommended next step

**Run R1.** It is the single most important test in the audit, it was blocked only on D3, and D3
is now done and verified. X3 sharpened the prior considerably: the composite's alpha looks
substantially like managed size exposure, so **SMB should absorb a large share of the 11.88%**.
Run it against both FF5+MOM and the q-factors, report the intercept with its Newey–West t, and
hold to P5's pre-committed language rule — "alpha" only if the FF5+MOM intercept clears t > 2.0,
otherwise the honest framing is *efficient factor exposure*.

---
---

# Round 2 — X4, S26, P1 (2026-08-04)

Thresholds committed in `PREREG_free_analysis.md` **before** each run. Lane re-validated:
`python check_lanes.py X4 S26 P1` → **SAFE**. Still **no existing file modified**.
Per the audit's own gate, U7 / O7 / O3–O5 are **held until R1 returns**.

| item | verdict | one line |
|---|---|---|
| **X4** | **NULL** on the primary blend | +9.21pp margin vs the 4-factor blend, but **t = 1.10** and negative in the first half. Real-looking, not demonstrable. |
| **S26** | pattern found, **then partly refuted** | The worst 20 are small, volatile, deep-value, crisis-clustered — but the book beats the universe *more* in drawdowns. What survives is that `low_risk`'s IC **flips sign by regime**. |
| **P1** | **capacity ≈ $23M** (upper bound) | Valquo cannot be a managed vehicle. It is a research tool users implement themselves. Don's own account is unaffected. |

---

## X4 — benchmark against what a user could actually buy → **NULL**

**Committed bar:** net excess over the matched blend **≥ +2.0pp annualised AND positive in both
halves**; 0 to +2.0pp → NULL; negative → the product's claim must change.

**Run.** `python -m scripts.etf_benchmark`. Blend = **VTV / QUAL / MTUM / IWM**, equal-weighted,
rebalanced on the panel's own 63-day grid. ETF adjusted closes are **already net of expense
ratios**, so the blend is measured net of fees — stricter than the audit asked. The strategy is
charged the project's own market-cap-keyed cost model at its measured turnover.

### Primary: matched 4-factor blend, 2014-01-10 to 2026-04-22, n = 50

```
  strategy gross +22.75%   net +21.87%   (cost drag 0.89%)
  blend    +12.65%     SPY +14.11%     equal-weight universe +13.40%
    IWM +9.37%   MTUM +15.29%   QUAL +13.59%   VTV +11.59%
  EXCESS vs blend  +9.21%   halves  -6.40% / +27.08%   both positive = FALSE
  -> NULL, margin not demonstrated
```

**The margin is large and the stability arm kills it, which is exactly what that arm is for.**
Supporting evidence, all pointing the same way:

- quarterly excess vs the blend: **mean +2.46%, median +1.98%, t = 1.10** — indistinguishable
  from zero
- **hit rate 27/50 = 54%** — barely better than a coin
- **four losing years**: 2014 -3.5pp, 2015 -12.2pp, 2017 -1.8pp, 2018 -14.5pp
- worst quarter **-40.1pp** (the window opening 2020-01-14, COVID hitting the small-cap tilt),
  best **+53.1pp** (2025-04-21)

### Secondary: long-history 2-factor blend (IWD + IWM), 2000-09-29 to 2026-04-22, n = 103

```
  strategy net +24.07%   blend +8.20%   SPY +8.28%   EW universe +12.70%
  EXCESS +15.87%   halves +19.59% / +12.19%   both positive = TRUE  -> BEATS
```

**This passes, and it is the weaker test**, so it does not rescue the primary: it is only value
and size (no quality, no momentum), IWD/IWM are cruder instruments, and its window includes the
pre-2006 era where **X6 found `size` had a real premium that has since broken**. Reported for
context, not as the verdict.

### Two facts that reframe the question

1. **The cheap factor blend lost to plain SPY over its own lifetime** — +12.65% vs +14.11%.
   "Just buy factor ETFs" was itself a losing trade over 2014-2026, so beating the blend is a
   weaker claim than it sounds.
2. **Versus SPY, the strategy's edge is significant full-sample and not in the last decade:**

| window | strategy net | SPY | excess | t | hit |
|---|---|---|---|---|---|
| 1999-2026 (n=109) | +27.42% | +8.52% | **+18.90pp** | **3.07** | 61% |
| 2014-2026 (n=50) | +21.87% | +14.11% | +7.76pp | **0.95** | 54% |

**Honest reading, stated both ways.** Over the last twelve years the strategy's advantage over
*every* investable benchmark tested — the factor blend and SPY alike — is a large point estimate
with a t-statistic near 1. That is **not** evidence of no edge: 50 quarterly observations is low
power and the confidence interval is wide. But it is also not the demonstrated margin the product
would need to claim one. The pre-registered answer is NULL, and NULL is what is reported.

**Also shipped:** `ETF_BENCHMARK_RESULTS_strategy_series.csv` — the per-rebalance top-decile and
equal-weight return series. **This is exactly the object R1 needs** ("already exists inside
`quantile_backtest` as `q_rets[0]` and `ewb`; it just needs to be shipped"), now available
without touching the panel module.

---

## S26 — read the twenty worst holdings → pattern named, then **partly refuted**

**Committed discipline:** name the pattern first, then test it; a pattern in 20 hand-read cases
is a hypothesis, never a finding; report the 20 against the book's own loss distribution.

### Context first — freak events or the ordinary left tail?

Top-decile holdings: **13,600 name-dates** over 110 rebalances. Forward 63-day returns: mean
+6.25%, median +3.70%, **sd 31.54%**, **40.7% negative**, p05 -29.5%, p01 -47.6%, worst -91.7%.
**The worst 20 run -67% to -92%, past the 1st percentile — genuine tail events, not the ordinary
left end.** Losing 40.7% of the time is normal for this book and is not a defect.

### The pattern, named before testing

The 20 worst versus the whole top-decile book:

| theme | worst 20 | book | diff |
|---|---|---|---|
| low_risk | -1.126 | -0.119 | **-1.006** |
| growth | -0.712 | +0.111 | **-0.823** |
| momentum | +0.056 | +0.640 | -0.584 |
| value | +1.013 | +0.542 | **+0.470** |
| size | +1.215 | +0.608 | **+0.608** |

Median market cap **$402M vs $1,900M — 0.21x, five times smaller.** Dates cluster hard:
2008-01, 2008-07, 2008-10, 2009-01, 2020-01, 2020-04, plus 2000-03.

> **Named hypothesis: the model's failure mode is the deep-value small-cap distress trap in a
> market-wide drawdown** — cheap, small, high-volatility, low-growth, low-momentum names, which
> is precisely what a crisis destroys.

The individual cases are vivid. **FNMA, 2008-07-10, composite +0.347** — the model bought Fannie
Mae two months before conservatorship on `book_to_price` +3.14 and `earnings_yield` **-4.34**,
the textbook value trap. Three of the twenty carry bankruptcy ticker suffixes (RELYQ, EBIXQ,
DBDQQ) — names that later filed. WFRD 2020-04 entered on a **`book_to_price` of +4.29** and
essentially nothing else.

### The test — and it refutes the interesting half of the hypothesis

Within the top decile only, per-date cross-sectional IC of each theme against forward return,
split by whether the universe return that quarter was negative (37 dates) or positive (73):

| signal | median IC | t | IC in DOWN quarters | IC in UP quarters |
|---|---|---|---|---|
| **low_risk** | -0.0289 | -0.58 | **+0.1200** | **-0.1038** |
| size | +0.0082 | +0.55 | -0.0254 | +0.0192 |
| value | -0.0246 | -1.53 | -0.0298 | -0.0240 |
| growth | +0.0358 | +1.47 | +0.0560 | +0.0160 |
| momentum | +0.0174 | +1.52 | +0.0193 | +0.0155 |

**The book is NOT crisis-fragile — it beats the universe MORE in drawdowns than in rallies:**
excess **+3.54%** in down quarters versus **+2.74%** in up quarters. So the crisis clustering of
the worst 20 is largely the mechanical consequence of dispersion being enormous in those
quarters, not evidence that the strategy breaks in a crisis. The vivid reading was wrong and is
retracted here rather than left standing.

**What survives, and it is more useful than the original hypothesis:**

> **`low_risk`'s information coefficient flips sign with the regime — +0.120 in down quarters,
> -0.104 in up quarters — and averages to the near-zero that got it zeroed.**

The project zeroed `low_risk` on an unconditional IC of -0.0014 (t +0.71), reading it as dead
weight. This says it may instead be **two real and opposite effects cancelling**. That is a
materially different diagnosis, and it fits the X3 mechanism (`low_risk` is the most
size-anticorrelated theme, -0.365): it behaves as a drawdown hedge that costs you the small-cap
premium in rallies.

**The honest limitation, which blocks immediate use:** the conditioning variable is the
*contemporaneous* universe return, which is **not observable at entry**. So this is not a
tradeable rule as measured. A tradeable version must condition on something knowable at
rebalance — the project already has `regime.py` and `valuation_regime.py` for exactly this.

**Feeds S10** (downside-exclusion screen) directly. Per the pre-registration, this hypothesis
must clear `holdout_theme_validate()` before it touches a weight.

---

## P1 — estimate capacity → **approximately $23M, and that is an upper bound**

**Data finding first, because it changed the method.** The audit states *"The ADV data is in SEP,
already on disk."* **It is not.** SEP is not on disk in any form; the bulk extracts are ACTIONS,
DAILY, EVENTS and SF3, none carrying volume, and the per-ticker price CSVs are `date,close` only.
The only volume on disk is `data/bulk/prepared/bars/` — **32 of the book's 918 names (3.5%)**.

**ADV assembled as pre-registered:** local bars (32 names) + yfinance (540 more) = **572/918
names, 62.3%**, covering **1,505/2,750 positions (54.7%)**. The remainder is filled by a
calibrated proxy, `log(ADV) = -8.72 + 1.186*log(mktcap)`, **R^2 = 0.704** on n = 1,505.

Book profile: **median dollar ADV $8.3M, median market cap $1.0B.**

### Participation and modelled cost (lambda = 1.0)

| AUM | position | median participation | >5% ADV | >10% ADV | mean cost | vs 234.5bps |
|---|---|---|---|---|---|---|
| $1M | $40K | 0.48% | 9.5% | 4.5% | **87 bps** | under |
| $10M | $400K | 4.82% | 49.0% | 33.7% | **171 bps** | under |
| $50M | $2.0M | 24.12% | 81.0% | 68.3% | **323 bps** | **OVER** |
| $250M | $10M | 120.59% | 97.7% | 92.9% | 662 bps | **OVER** |
| $1B | $40M | 482.37% | 99.6% | 99.3% | 1276 bps | **OVER** |

### Capacity — the AUM where modelled one-way cost crosses the measured 234.5bps breakeven

| lambda | capacity |
|---|---|
| 0.5 | $91.8M |
| **1.0 (headline)** | **$23.0M** |
| 2.0 | $5.7M |

### What this means, stated plainly

**Valquo cannot be a managed vehicle of meaningful size.** At $50M the book is already paying
323bps against a 234bps breakeven, and 81% of positions would exceed 5% of a day's volume. The
strategic answer the audit asked for is therefore: **it must remain a research tool that users
implement themselves** — which is also the positioning that avoids the regulatory posture of a
managed product.

**Don's own account is unaffected.** At $1M the modelled cost is 87bps against a 234bps
breakeven, with only 4.5% of positions above 10% of ADV. The strategy works fine at the size it
is actually run.

**Four caveats, none of which should be dropped:**

1. **Every number is an UPPER BOUND.** ADV comes from survivors; the 346 of 918 names that could
   not be fetched are disproportionately the delisted, illiquid ones. True capacity is lower.
2. **lambda is an assumption, not a measurement**, and the capacity range spans **16x**
   ($5.7M to $91.8M). The headline is the middle of a wide band.
3. **The 234.5bps breakeven was measured on the top-DECILE book (~271 names), but capacity is
   computed on the 25-name product book**, which is more concentrated and smaller-cap. Using the
   decile's breakeven is generous to capacity.
4. 45% of positions use the market-cap proxy rather than observed volume.

**Unblocks P2** (model user crowding) — and P1's answer sharpens it: at $23M total capacity, it
does not take many users to become the crowding mechanism.

---

## Files added in round 2

| file | item |
|---|---|
| `scripts/etf_benchmark.py` | X4 (also ships the per-period series R1 needs) |
| `scripts/failure_cases.py` | S26 |
| `scripts/capacity.py` | P1 |
| `data/free_analysis/{ETF_BENCHMARK_RESULTS.json, ETF_BENCHMARK_RESULTS_strategy_series.csv, FAILURE_CASES.json, CAPACITY_RESULTS.json}` | outputs (gitignored) |

## Recommended next step, unchanged and now sharper

**Run R1.** D3 unblocked it; X4 has now made its answer interpretable in advance. The two
questions are complementary, and X4 has already supplied half the answer: over 2014-2026 the
strategy does not demonstrably beat cheap factor ETFs *or* SPY (t 1.10 and 0.95). If R1's FF5+MOM
intercept also comes back short of t > 2.0, the two results agree and the honest product framing
is **efficient factor exposure**, per P5's pre-committed language rule. If R1's intercept is
strong while X4 is null, that gap — regression alpha a retail ETF blend cannot capture — is the
actual product, and X4's window says how much of it is currently demonstrable.
