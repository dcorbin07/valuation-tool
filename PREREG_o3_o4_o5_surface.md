# PRE-REGISTRATION — O3 + O4 + O5, the surface-anomaly family

**One register, three arms, committed ALONE before any measurement code exists.** Ledger rows
`O3` (delta-hedged returns vs idiosyncratic vol), `O4` (expected idiosyncratic skewness), `O5`
(vol-of-vol), all `OPEN`, all *"held until R1 returned — R1 has now returned, UNBLOCKED"*.

---

## §0 THE SCOPE FACT THAT COMES FIRST: THESE ITEMS HAVE ALREADY BEEN TESTED ONCE, AND REJECTED

**This is not a fresh question and this register may not be read as one.** `64955ef`
(`worktree-options-live`, now **on `main`**) shipped `valuation/edge/options_xsection.py` and
`data/options_xsection/XSECTION_RESULTS.json`, which tested **all three characteristics with the
published sign declared before any sort**. `HANDOFF_deep_xsection.md` records the verdict:
**REJECT — nothing clears the gate, one characteristic sorts backwards.** `HANDOFF_free_analysis.md`
audited that run against the catalogue's own bar and concluded **O3, O4, O5 "should be considered
answered by that same run, not re-opened separately."**

**So the burden here is to justify re-opening at all.** The justification is one sentence in the
prior lane's own write-up, which declared the deviation up front and did not close it:

> *"Straddle, not Cao–Han's delta-hedged call. Stated as a deviation up front: their instrument
> needs roughly a million IV solves. A straddle is delta-neutral at inception, which is the
> property the test needs."*

and the free-analysis lane's reading of the one suggestive result:

> *"A straddle is only an approximation of Cao–Han's delta-hedged call, so this is suggestive,
> not a refutation."*

**THIS REGISTER CHANGES THE INSTRUMENT AND NOTHING ELSE THAT CAN BE HELD FIXED.** A straddle is
delta-neutral **only at inception**; it accumulates directional exposure immediately, and its
return variance is dominated by the underlying's move — which is precisely the variance
Cao–Han's daily-rebalanced hedge removes. **The re-test is therefore better powered on the same
data, and that is the whole argument for running it.** It is a **second look at an already-rejected
hypothesis** and is charged as such.

## §1 A SECOND SCOPE FACT, MEASURED: THE FROZEN CHAINS CANNOT DO THIS

The task named the frozen chains as the instrument. **They cannot support a cross-section, and
this was measured before the register was written.** `R2_CORRECTED_2026-08-08/chains.pkl.gz` holds
2,870,811 rows over 2,498 dates and 186 symbols, but it stores a **full chain only on the banked
book's ENTRY dates** and a single tracked contract thereafter (O21 established the same fact from
the other side). Per date, counting names with ≥50 chain rows:

| names with a full chain on the same date | dates |
|---|---|
| ≥ 5 | 190 of 2,498 |
| ≥ 10 | 15 of 2,498 |
| **≥ 20** | **0 of 2,498** |
| month-ends with ≥ 20 | **0 of 120** |

Median **1** full-chain name per date, maximum 17. **A quintile sort needs roughly 20+ names on a
common formation date, and the freeze never once has 20.** The substitution is therefore forced
and is disclosed rather than quietly made: **the panel is built from the EOD option cache**
(`data/options/<TKR>/<TKR>-<YEAR>.pkl`, daily NBBO plus volume and open interest for the whole
chain), which is the same source the prior lane used, and the greeks come from
`blackscholes.greeks`. The freeze is used for nothing here.

## §2 DISCLOSED PRIOR KNOWLEDGE

Seen before this register was fixed. **No outcome of the new instrument has been computed.**

* The prior lane's panel: **3,373 formation events, 242 names, 117 months, 2016-02 → 2025-10**,
  median **25** names per formation date, 71 dates with ≥20 names.
* Its verdict: REJECT on all four gate arms; `iv_rv` long-short **t = 0.143**; deflated Sharpe
  0.020; `illiq` (a mechanical control that can never be a discovery) the only characteristic with
  |t| > 2, at 2.46.
* **`idio_vol` was monotone at 0.9 but in the direction CONTRADICTING Cao–Han**, flagged by their
  own machinery as `contradicts_published_sign`.
* Its stated further deviations: the market proxy is the equal-weighted universe return (no ETFs
  in the Sharadar export), and `vol_of_vol` was computed on the **60-DTE** ATM-IV series while the
  instrument was **~30 DTE**.
* Structural feasibility of the new instrument, measured on 40 panel events: **35 have a usable
  daily contract life**, median **16** contract-days; a worked example solved IV on 17 of 20 days
  and produced a normalised delta-hedged gain of −0.06955. **IV does not solve at T = 0**, which is
  a treatment this register must fix in advance (§3).

## §3 THE INSTRUMENT — FIXED HERE

**Cao–Han's normalised delta-hedged call gain, rebalanced daily.** For a call held from formation
`t0` over the days `i = 0 … n-1`:

```
Pi = C_last - C_0  -  SUM_i  Delta_i * (S_{i+1} - S_i)  -  SUM_i r * (C_i - Delta_i * S_i) * dt_i
DH = Pi / | Delta_0 * S_0 - C_0 |          <- Cao-Han's normalisation
```

* **Contract:** the call nearest the money with DTE in **[20, 45]** on the formation date — the
  same selection the prior panel used, so the contract is not a new degree of freedom.
* **Entry at the ASK, exit at the BID**, matching `DEFAULT_AGGRESSION = 1.0`. Interior marks use
  the **mid**, because they are marks and not trades. A mid-to-mid variant is a **diagnostic only**.
* **`Delta_i`** from `blackscholes.greeks` at the IV solved from that day's **mid**, `r = 0.03`,
  **`q = 0`**. `q = 0` is chosen for comparability with every other options figure in this project
  and because O21 measured its effect: it understates solved IV by a median 0.00617 and overstates
  |delta| by 0.00668 — small, disclosed, and identical across all three arms, so it cannot create a
  cross-sectional ordering.
* **Hedge trades are charged 5 bps one-way on the notional traded.** This is an assumption, not a
  measurement, and is labelled as one; a 0 bps arm is a diagnostic. Charging nothing would flatter
  the instrument, so the primary charges.
* **Terminal day:** IV is unsolvable at `T = 0`, so the hedge is carried at the **last solvable
  delta** and the position is closed at the last available bid. Events with fewer than **10**
  solvable contract-days are **excluded**, and the exclusion count is reported.

## §4 THE THREE ARMS

Signs are the published ones and are declared **now**. Every sign is *"high characteristic predicts
LOWER delta-hedged returns"*, so **Q1 (low characteristic) should earn the most**. A study that
picks which end to go long after seeing the numbers wins half the time by construction.

| arm | characteristic | source | definition |
|---|---|---|---|
| **A1 — O3** | `idio_vol` | Cao–Han (2013) | **unchanged from the prior lane's function**, so A1 differs from the published rejection in the INSTRUMENT ALONE |
| **A2 — O4** | `exp_idio_skew` | Boyer–Vorkink (2010) | **expected**, not realised, idiosyncratic skewness: at each formation date, a cross-sectional OLS of realised idio skew on lagged `idio_skew`, `idio_vol` and 6-month momentum, fitted on data available at that date, and the FITTED value is the characteristic |
| **A3 — O5** | `vol_of_vol` | vol-of-vol risk premium | stdev of daily log changes in the name's own ATM IV over 63 sessions, **computed on the tenor the instrument actually trades** rather than the prior lane's 60-DTE series |

**A2 and A3 change the characteristic as well as the instrument, and that is stated plainly:** the
prior lane used *realised* skew where Boyer–Vorkink specify an *expected* one, and computed
vol-of-vol at a tenor its instrument did not trade. **A1 is the clean instrument-only comparison
and is therefore the arm that carries the most weight.** The prior lane's realised-skew and
60-DTE arms are re-reported on the new instrument as **disclosed comparisons carrying no verdict**.

Boyer–Vorkink's own construction uses a larger predictor set and industry effects; **this is a
simplification, is labelled one, and its predictors are fixed here before any fit is run.**

## §5 STATISTICS, CALIBRATION AND THE VERDICT RULE

* **Unit:** one formation event. Quintiles cut **within each formation date**, so the sort is
  cross-sectional and never compares across regimes.
* **Portfolio:** equal-weighted Q1 and Q5 per date; the long-short series is Q1 − Q5.
* **Clustering:** the long-short **t** uses a **calendar-month date-block bootstrap** (R3's standing
  rule, 2,000 draws). A trade-level t is never quoted.
* **Calibrated bar:** the raw long-short **t** is scored against a **within-date label permutation
  null** — quintile labels permuted inside each formation date, holding every return and every bin
  size fixed, 2,000 draws, seed 20260812. **The bar is that null's p95**, not the conventional 2.0.
  A raw dispersion is not evidence of anything; R3 recorded that error once and O13/O18 both use
  this instrument.
* **Both halves:** split at the panel's median formation date.

**An arm is a CANDIDATE iff, in BOTH halves:**

1. quintile monotonicity is in the **published direction** and at least **0.6** in absolute Spearman
   terms (the catalogue's own bar, quoted rather than restated by me), **and**
2. the long-short **t** exceeds that arm's **own permutation p95**, **and**
3. the long-short mean is **positive** — i.e. Q1 beats Q5 in the published direction.

Otherwise **NULL**. Ambiguous against a bar is a NULL (`RUN_RULES` A6). An arm that **clears with
the sign reversed** is reported as **CONTRADICTS-PUBLISHED-SIGN** and is explicitly **not** a
candidate, because the sign was declared first.

## §6 WHAT A POSITIVE WOULD AND WOULD NOT MEAN — FIXED BEFORE THE RESULT

**R2 is not re-opened and cannot be re-opened by this item.** The options *entry* signal is dead;
these are **cross-sectional characteristics of the option surface**, a different object. Therefore:

* A CANDIDATE verdict here is a **candidate for a FUTURE book that does not yet exist**. It is
  **not** a revival of the alert book, **not** evidence the alert signal works, and **not** an
  adoption.
* **Nothing is adopted in this session whatever the result.** No live path, no constant, no book.
  A candidate is written up and **routed to Don**.
* The instrument is **delta-hedged**, so it is not the product the project sells; any book built
  on it would need a daily hedge, which the paper track has no mechanism for. That is a
  construction question, not a signal question, and it is out of scope here.

## §7 EXPECTATIONS — WRITTEN DOWN FIRST

| # | expectation | confidence |
|---|---|---|
| E1 | No arm reaches CANDIDATE | 70/30 |
| E2 | The delta-hedged long-short **t** is LARGER in absolute value than the straddle's, on the same panel — the power argument for running this at all | 75/25 |
| E3 | `idio_vol` (A1) again sorts against the published sign | 60/40 |
| E4 | A2's expected-skew arm is weaker than the prior lane's realised-skew arm | 55/45 |
| E5 | Tenor-aligning vol-of-vol (A3) moves it materially versus the 60-DTE version | 50/50 |
| E6 | Delta-hedged return dispersion is well under half the straddle's | 80/20 |

## §8 TRIAL COST

**3 options trials**, one per arm. Diagnostics (mid-to-mid, 0 bps hedge, the prior lane's
definitions re-run on the new instrument) are charged at zero: they search nothing and carry no
verdict. Options `N` **258 → 261**. **Equity `N` untouched at 155.**

Charged even though these hypotheses were rejected once already — a second look at the same
hypothesis with a better instrument is another chance for the same hypothesis to clear, which is
exactly what the counter exists to price.

## §9 VOID CONDITIONS

1. Fewer than **50** formation dates survive the ≥10-solvable-contract-days rule, or fewer than
   **15** names per date on median — a quintile sort needs a cross-section.
2. Any change to the sign declarations, the quintile cut, the instrument formula, the contract
   selection, the predictor set in A2, the null construction, the seed, the draw count, or the
   three verdict conditions after any outcome number has been read.
3. Adding a fourth arm after seeing the first three.
4. Quoting any arm as an adoption, or as evidence about the options ENTRY signal.
