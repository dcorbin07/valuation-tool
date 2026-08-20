# PREREG — E-4: the market-tail crash flag beside the accounting card

**Season 2, register `E-4` (`IDEAS_LEDGER.md`, S-SEED-5), option-implied half.** Written and
committed **ALONE**, markdown only, zero `.py`, before any instrument for this item exists and
before any relationship between an option-implied quantity and a crash has been computed.

**1 EQUITY TRIAL**, booked in its own commit before the runner is written. **ADOPTS NOTHING.**
No file under `valuation/` that the live product imports will change; no product copy changes.

---

## 0. WHAT I ALREADY KNEW, DISCLOSED RATHER THAN DISCOVERED

A register that claims blindness it does not have is worse than one that states its priors. Two
pieces of prior knowledge bear directly on choices below, and both are disclosed here.

**0a. `E-5`/`INV-A` measured WHEN the accounting flag's crashes arrive, and it is not
front-loaded.** Landed 2026-08-20, same season, same panel: the two-quarter share of the
four-quarter excess is **0.5701** against the proposal's 60% bar, **the single largest quarter
is the SECOND**, and **quarters three and four together carry about 43%**. Its own standing
note reads *"FOR O-1: THIS DOES NOT SUPPORT A SHORT TENOR."*

This is horizon-relevant and I am not blind to it. **The horizon is pre-committed in §3 with
that citation, and the reasoning runs the other way from the obvious one** — see §3.3.

**0b. My own `I-1` handoff binds the tail construction.** The RND builder
(`valuation/studies/rnd.py`, landed 2026-08-20, this lane) does **not** implement NY Fed SR-677
literally. SR-677 as written produced **0 usable slices of 387** on equity chains, for two
measured structural reasons, and the two departures are:

* **abscissa** — log-moneyness, not delta. `K(delta)` is not invertible on a steep equity skew
  (7 folding steps measured on AAPL 2025-07-07 at delta 0.0059–0.0074), and de-duplicating a
  folded map silently drops a branch.
* **wings** — C¹ smooth-pasting `σ(x) = σ_e + slope_e·L·(1 − exp(−abs(x − x_e)/L))`, not flat
  extrapolation. A flat clamp puts a *step* in `σ′`, which is a *delta function* in `σ″`, and
  the density carries `C_σ·σ″` — a guaranteed negative spike at both seams, by arithmetic.

**And the caveat that decides §3.2: `Q(S_T ≤ 0.50·S_0)` is an EXTRAPOLATION on 80.48% of usable
slices**, against 46.06% at 0.70 and 27.74% at 0.80. That census is `I-1`'s, pre-outcome, and it
is the whole reason the primary threshold below is not the one that matches the crash event.

---

## 1. THE OBJECT

**Question.** Does option-implied left-tail mass — the market's own risk-neutral probability of a
large fall — flag names that go on to crash, and specifically does it flag crashes that
`MA28`'s accounting flags MISS?

**The verdict object is a CRASH RATE. Never alpha.** `MA28-CARD`'s gate style, and `S10`'s
corpse is the reason: `S10` ran a valuation-band exclusion as a *screen*, failed on the
portfolio-drawdown leg, and its own mechanism arm found the excluded names crashed at **half**
the rate of the names kept. This is a **card candidate**, not a screen. No return statistic, no
alpha, no long-short, no IC is computed anywhere in the arm path. A test will pin that.

**The instrument is I-3** (`valuation/studies/crash_gate.py`), imported and not re-implemented.
Every bar below is passed to it explicitly; it has no defaults and refuses without them.

---

## 2. COVERAGE, MEASURED BEFORE THIS REGISTER WAS WRITTEN

The `COVERAGE RULE` is hard and these numbers are pre-outcome. Every one is a fact about what is
on disk. **None involves a flag, and the only outcome quantity is the unconditional base rate,
which `RUN_RULES` PART A rule 11 requires a register to print before it runs.**

Panel: `data/free_analysis/panel_r5r6.pkl` — 113,945 rows, 69 dates, 2,531 names,
2009-01-15 → 2026-01-28. The same object `E-5` scored.

Chains: the **PINNED** freeze only, via `chain_store.resolve_chains`, which raises rather than
falling back. `D:\thetadata\freeze_options_2026-08-17\options`, `pinned: True`,
`manifest_sha256 dc8e9b35…`, 1,000 ticker directories, 5,063 payload units. **The mutable
`data/options` store is never opened**, pinned by test.

| constraint | value |
|---|---|
| freeze tickers ∩ panel names | **906** |
| panel dates inside the freeze's years (2016–2025) | **40 of 69** — 2016-01-20 … 2025-10-27 |
| panel rows reachable at file level | **19,203** |
| …independently: `P1S0_OPTIONABLE_PARTITION.pkl`, same 40 dates | **19,083** (0.6% apart) |
| …also requiring an as-traded `raw_close` series (`bars`, 502 files) | **17,558**, 486 names |
| sampled usable-RND rate, 220 name-days, 4 dates, band [50,140] | **55.3%** |
| **projected rows carrying a usable RND** | **≈ 9,710** |

**The 29 uncovered dates are ALL early** — this is `U2`/`MA31`/`MA32`'s geometry for the fourth
time, and it is an impossibility rather than a power caveat: the derived options layer starts
2016 and the panel starts 2009. **Every split below is of the COVERED subsample.**

**Base rates, measured, flag-free:**

| population | rows | crashes (`fwd_ret ≤ −0.50`) | rate |
|---|---|---|---|
| full panel | 113,945 | 1,113 | **0.9768%** |
| the same 40 dates, ALL panel names | 68,906 | 913 | **1.3250%** |
| **reachable / optionable** | 19,203 | **81** | **0.4218%** |

**The optionable subset crashes at 0.4218% against 1.3250% on the same dates — 3.14× lower —
and that is a UNIVERSE effect, not a period effect, because the same-dates row controls for
period.** It is `MA28`'s own size gradient (kept rate falling 14.5× from the smallest quintile
to megacaps) reproduced on a different partition. **Every figure this register produces is
conditioned on the optionable universe and none of it generalises to the panel.**

Outcome coverage is **1.0** on both populations (`crash_gate.coverage`), so `crash_flag`'s
fail-open on a NaN forward return never fires here — reported because a filter that cannot fire
and a filter that fires and finds nothing must not read the same (`O21-D2`'s `C5`).

**The panel's own shipped `fwd_ret` is used and no forward path is reconstructed.** `E-5` found
a survivorship defect in exactly that reconstruction — a 63-trading-day path has nothing for the
591 rows whose ticker stops trading inside the window — and verified the panel's column already
implements the correct rule at max abs delta 0.000e+00. Not repeating it.

---

## 3. THE FLAG, THE THRESHOLD, AND THE HORIZON

### 3.1 The flag
`market_flag` = the **worst quintile, within date**, of option-implied left-tail mass. The
quintile is the ledger's own choice for E-4 and is adopted verbatim rather than re-chosen. A
date needs **≥ 50 usable names** to form quintiles — `MA28`'s own `extfin` floor, reused.

Within-date, so it is a cross-sectional rule like `MA28`'s external-financing leg, and the
flagged share is **0.20 by construction** on every qualifying date.

### 3.2 The threshold — PRIMARY 0.70, and why it is not 0.50
`tail_mass` = **`Q(S_T ≤ 0.70·S_0)`** from the I-1 RND, `S_0` the **as-traded `raw_close`**
(`U1-SPLIT`: strikes are as-traded and `close` is adjusted; NVDA 2012 reads 0.27 against a raw
11.97, and the mismatch fails **silently**).

**0.50 is the risk-neutral analogue of `MA28`'s crash event and it is NOT the primary, because
80.48% of its readings are wing extrapolation** (§0b). At 0.70 that falls to 46.06%, so a
majority of readings rest on quoted strikes. **This choice is made on a PRE-OUTCOME coverage
statistic from my own instrument's census and on nothing else** — no relationship between any
threshold and any crash has been computed.

`Q(≤0.50)`, `Q(≤0.60)`, `Q(≤0.80)` and `Q(≤0.90)` are reported as **SENSITIVITY, carrying NO
verdict**. Quoting a sensitivity cell as the result voids this register (§8).

### 3.3 The horizon — PRE-COMMITTED at MA28's own 63-trading-day window, citing E-5
Crash event: **`fwd_ret ≤ −0.50` over the panel's 63-trading-day window** — `MA28`'s registered
threshold and window, verbatim. RND tenor: the expiry **nearest 92 calendar days** (63 trading
days) within **[50, 140]**.

**The band was chosen on coverage alone, before this register, and it sits on a plateau:**
[60,120] finds an expiry on 68.7% of name-days and yields 42.4% usable; **[50,140] gives 93.5%
and 55.3%; [45,150] is IDENTICAL to [50,140] on both**, so the choice is not at an edge.
[30,200] reaches 60.8% and is rejected — a 6.7× tenor range inside one cross-section is a tenor
confound, and `C-TENOR` (§6) exists because even 2.8× is not nothing.

**Why not a longer window, given `E-5` (§0a).** E-5 measured the accounting flag's excess spread
across four quarters with Q2 largest, so a 2- or 4-quarter window would materially **improve the
accounting arm**. That is exactly why it is not taken: E-5 has already told me the *direction*
that change moves the comparator, and extending the window would also force the RND tenor out to
180–365 days, where my own coverage census thins and the band would have to widen far past its
plateau. **Changing both arms in a direction I already know is choosing the design with part of
the answer in hand.** The 2×2 needs ONE window for both arms or it is not a 2×2, and `MA28`'s
published 3.0422× is defined at this one.

**The asymmetry this creates is stated here rather than discovered later, and it FAVOURS the
market flag.** The RND at ~92 days forecasts exactly the window it is scored on. The accounting
flag is scored over the first of four quarters in which E-5 showed it works — under ~29% of its
four-quarter excess, since Q1+Q2 = 57.01% and Q2 is the larger. **So the 2×2 compares a flag
measured over its whole horizon against a flag measured over part of its own.** Any reading of
the 2×2 must carry that sentence.

### 3.4 Sign, declared before the run
**POSITIVE**: higher option-implied left-tail mass → **higher** subsequent crash rate. A
negative result in the flagged bucket is a FAIL, never a re-read as "the market fades crashes".

---

## 4. THE GATE — MA28's OWN BARS, REUSED VERBATIM

Via `crash_gate.window_result`, every bar passed explicitly:

| bar | value | source |
|---|---|---|
| B1 | mean per-date difference > its own within-date permutation p95 | `MA28` §4 |
| B2 | pooled ratio ≥ **2.0×** | `MA28` `RATIO_FLOOR` |
| B3 | mean per-date difference ≥ **0.50 pp** | `MA28` `ABS_FLOOR_PP` |
| `n_perm` / `perm_seed` | **500** / **20260816** | `MA28` |
| `min_flagged_per_date` / `min_kept_per_date` | **30** / **100** | `MA28` |
| `min_events` for a quotable ratio | **10** | declared here — below 10 the Poisson relative se exceeds 32%, so a ratio built on it is a count (`MB8`) |
| crash threshold | **−0.50** | `MA28` |

**Not one bar is re-chosen.** Reusing the incumbent's bars is the point: this register asks
whether a *different* flag clears the bar the accounting flag cleared, and a new bar would make
the two incomparable. My projected sample sits at ~49 flagged and ~194 kept per date, both above
`MA28`'s per-date floors.

**Required in the FULL SAMPLE and BOTH HALVES**, halves via `crash_gate.halves` on the **covered**
dates (20/20 of 40). Full sample alone is not a pass.

---

## 5. POWER — BOTH VOCABULARIES, BEFORE THE RUN

`RUN_RULES` PART A rule 11. Two routes, computed from the §2 census at the projected 9,710 rows,
40 dates, s = 0.20, base rate 0.4218%. **They disagree, and the disagreement is itself declared.**

**Route 1 — pooled two-proportion (`crash_gate.required_rows`, allocation-aware):**

| target ratio | crit | rows needed | have ≈ 9,710 |
|---|---|---|---|
| 2.0× (the registered floor) | 3.3083 (`N` = 238) | 45,567 | **UNDERPOWERED** |
| 2.0× | 2.0 | 21,366 | **UNDERPOWERED** |
| 3.0422× (`MA28`'s own effect) | 3.3083 | 15,919 | **UNDERPOWERED** |
| 3.0422× | 2.0 | 7,464 | POWERED |

**MDE RATIO at ~9,710 rows: 3.947× at the project hurdle, 2.695× at the |t| = 2 convention.**

**Route 2 — the per-date difference (B1/B3's actual statistic, 40 date blocks).** Binomial se of
the mean per-date difference = **0.1638 pp**:

> MDE at |t| > 3.3083 (N = 238): detection threshold **0.00542011** (50% power); **0.00679634**
> at 80% power. Power against a `MA28`-size effect (0.008614) is **97.4%**; against the
> registered 2.0× floor (0.004218) it is **23.2%**.

> MDE at |t| > 2.0000: detection threshold **0.00327672** (50% power); **0.00465295** at 80%
> power. Power against 0.008614 is **99.9%**; against 0.004218 it is **71.7%**.

**Route 1 is the binding constraint and is what this register quotes.** Route 2 assumes
binomial independence within date and zero correlation across dates, and both are false here —
`MA28` measured the base rate moving 4× between halves around COVID 2020Q1, which `S10`
separately measured to be the single quarter that decides this book's drawdown. **The realised
per-date sd will be measured after the run and the MDE re-stated on it**; if the realised figure
contradicts the pre-run one, the pre-run one stays on the page and the correction goes beside it.

**THE HONEST PRE-RUN STATEMENT: this design cannot detect an effect the size of the accounting
flag's own 3.0422× at the project's own hurdle, and cannot detect the registered 2.0× floor at
either bar.** That is why §5.1 exists.

### 5.1 THREE-STATE VERDICT GRAMMAR, all three reachable (`P1S0`'s precedent)
* **PASS** — B1 ∧ B2 ∧ B3 in the full sample and both halves.
* **FAIL** — not PASS, **and** the observed effect exceeds the design's own 80%-power MDE, so
  the design could have seen an effect of the size it saw.
* **UNDERPOWERED** — not PASS, and the observed effect sits **below** that MDE. This means *"not
  separable at this resolution"* and **never** *"absent"*. `V6`/`S19`'s rule: quote the MDE with
  the verdict or do not quote the verdict.

The state is decided by the arithmetic above, not by judgement. Ambiguous is UNDERPOWERED, not a
close call (`RUN_RULES` A6).

---

## 6. KILLS AND CONTROLS — all pre-outcome, all read BEFORE any arm is scored

The arm runner **REFUSES** to run without a passing controls artifact on disk, and the controls
run in **their own pass** — `O10`'s process defect, not repeated.

**`K-OVERLAP` — the ledger's own kill, run AS WRITTEN, plus the arithmetic it needs.** The
ledger's condition is *"flag-overlap census vs accounting flags > 70% → withdrawn"*.

**Stated before running it: as literally written against my flagged rows, that kill CANNOT
FIRE, and the arithmetic is one multiplication.** `MA28` flags 5.74% of the panel; this flag
flags 20.00% by construction; so `P(accounting | market)` is bounded above by 5.74/20 =
**28.7%** and can never exceed 70%. **This is `MB8`'s failure exactly** — that audit set a 20%
bar and a 0.5× haircut without multiplying them together — and it applies to the ledger's own
Hill-index proposal too, since that flag is also a quintile.

So the census is reported in **both directions**, and the kill is taken on the one that can
reach its bar:
* reported: `P(accounting-flagged | market-flagged)`, ceiling 28.7%;
* **KILL: `P(market-flagged | accounting-flagged) > 0.70`** — more than 70% of accounting-flagged
  rows falling inside the worst market quintile. Ceiling 1.0, so reachable. This is the ledger's
  own 70%, applied to the direction that can attain it, and it tests the same thing: whether the
  market flag is the accounting flag in a costume.
* also reported, no bar: Cohen's κ and the co-firing odds ratio.

**`C-VOL` — the costume that actually threatens this item.** RND left-tail mass rises with the
whole implied-vol level, and high-vol names crash more, so a positive result is at real risk of
being *"implied volatility predicts crashes"*. Mean per-date Spearman of `tail_mass` against ATM
implied vol. **Pre-committed: at |ρ| ≥ 0.90 the flag MUST be described as an implied-vol sort
and may not be described as a tail-shape finding**, in the write-up, the ledger row and any
downstream copy. Not a kill — a mandatory relabelling.

**`C-SIZE` — `MA28`'s C4, and `U7`/`S10`'s failure mode.** Median market cap flagged vs kept,
and the crash-rate comparison **within market-cap quintile**. Reported whatever it shows;
`MA28`'s own C4 was registered as the likely killer and passed 5 of 5 with the gradient
inverted, so no direction is assumed.

**`C-TENOR`** — mean per-date Spearman of `tail_mass` against DTE. The band is 2.8× wide and a
tenor sort would be a confound; reported with the tenor dispersion per date.

**`C-INSTRUMENT`** — the RND fit diagnostics travel with every row: `integral`, `negative_mass`,
the CDF two-route gap, and `threshold_extrapolated` at 0.70. Slices failing I-1's own gates are
**excluded and counted**, never silently dropped.

**`C-PIN`** — the census reproduces `P1S0_OPTIONABLE_PARTITION.pkl`'s 40 dates exactly, and the
store provenance is asserted `pinned: True` before anything is read.

---

## 7. THE DELIVERABLE — the 2×2, which survives an UNDERPOWERED verdict

This is what the item exists to produce and it is **descriptive**: cell counts and crash rates
need no gate. Reported whatever §5.1 returns.

| | accounting-flagged | accounting-clean |
|---|---|---|
| **market-flagged** | n, crashes, rate | n, crashes, rate |
| **market-clean** | n, crashes, rate | n, crashes, rate |

Plus the two incremental readings, each through `crash_gate.quotable(min_events=10)` so a ratio
on too few crashes is **withheld with a stated reason** rather than emitted:
* **on accounting-CLEAN rows only** — does the market flag separate? (E-4's actual question)
* **on market-CLEAN rows only** — does the accounting flag separate?

**PRE-STATED, so it is not read as a finding when it appears: the accounting arm of this 2×2 is
expected to be TOO THIN TO CARRY A RATIO.** `MA28` flags 5.74% of the panel and `MB8` measured
3.56% of the top-decile book; at ~4% of 9,710 rows that is ~390 rows, and at this subset's
0.4218% base rate scaled by `MA28`'s 3.04× that is **~5 expected crashes** — below the declared
`min_events` of 10. **If that is what happens, the "vice versa" half of the comparison is
UNANSWERABLE on this universe and will be reported as unanswerable**, not as a null.

---

## 8. VOID CONDITIONS

1. Quoting any **sensitivity** threshold (0.50/0.60/0.80/0.90) as the verdict.
2. Computing **any** relationship between an RND quantity and a forward RETURN — alpha, IC,
   long-short, expectancy. Crash **rates** only. Pinned by an AST test over the arm path.
3. Reading the **mutable** `data/options` store, or any store whose provenance is not
   `pinned: True`.
4. Changing any bar in §4, the threshold in §3.2, the band in §3.3 or the flag width in §3.1
   after any outcome statistic is read.
5. Re-running with a different threshold, band or flag width until something clears. A re-open
   needs a materially different construction, its own register and its own trial.
6. Reporting a PASS on the full sample alone.
7. Quoting any figure here as a statement about the **panel** or the **book**. This is the
   optionable subset, 40 late dates, 486 names.
8. Adopting anything. Adoption is a **vintage event** and is Don's, and no arm here is eligible.

---

## 9. PRIOR AND EXPECTATIONS

**Prior on PASS: ~20%.** The ledger prices the Hill-index half at ~12%; I price the
option-implied half higher and state the reason on both sides.

*Higher, because:* the RND left tail is a **direct forward-looking market forecast of the exact
event being scored**, where a Hill index is a backward-looking estimator of a different quantity.
If the market has any skill at all, the within-date rank should carry.

*But not much higher, because:* the literature on RND crash-content is **mixed-to-contested**
(J. Empirical Finance 2018, imported by I-1's own entry as a hypothesis and never as a claim);
this project has failed to reproduce a published options sign **three times** (`O7`, `U2`,
`MA31`/`MA32`); and **`MA31`/`MA32` measured that on precisely this options-listed
sub-population the panel's own best-known signals cannot be separated from zero** —
`z_gp_on_capital` falling +3.6745 → +0.9919 and `quality` +3.1015 → −0.0594 on the arm rows.
That is the single most discouraging fact available about this universe, and §5 says the design
is underpowered against the registered floor regardless.

**Scored expectations, written before the run:**
1. The verdict is **UNDERPOWERED** rather than FAIL or PASS — **60/40**.
2. `K-OVERLAP` does **not** fire; `P(market | accounting)` lands **below 0.40** — **75/25**.
3. `C-VOL` reads |ρ| **≥ 0.70** — the flag is largely an implied-vol sort — **70/30**.
4. `C-SIZE` shows flagged names **smaller** than kept — **65/35**.
5. The accounting arm of the 2×2 is **withheld** for thin events — **70/30**.
6. The pooled ratio is **> 1.0** (right sign) even if it fails the 2.0× floor — **65/35**.
7. The realised per-date sd **exceeds** the binomial estimate of 0.1638 pp — **80/20**.

---

## 10. TRIALS, AND WHAT THIS CHANGES

**1 EQUITY trial**, booked in its own commit before the runner exists. Live `by_domain` read
after merging `origin/main`: **equity 238, options 305, infra 19** — re-read rather than quoted
(`MA37`'s rule, and `MB31` proves no permutation floor can move below equity `N` = 247, so the
booking does not disturb any calibrated bar).

One arm, one flag, one threshold, one band, one horizon. The sensitivities carry no verdict and
charge nothing; the controls can only block a finding and never produce one (`MB1-SEL`'s
distinction), so they charge nothing.

**ADOPTS NOTHING. No card is built** — `MA28-CARD`'s deliverable was the *sentence* and shipping
a surface is the app lane's, with the `BANNED` phrase tuple asserted against the **rendered**
payload. **`MA28` is not re-opened, re-scored or weakened by anything here.** `O-1` is not run
and is not designed here; it charges its own trials and needs its own blind register.
