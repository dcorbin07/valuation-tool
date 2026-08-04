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
