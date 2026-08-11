# PREREG — M2 (clustered inference as the default) and M6 (results-file schema assertion)

Committed **alone**, before any implementing code exists, as a strict git ancestor of the
change commit. This is a **scope registration**, not a hypothesis test: neither item produces a
verdict, so no threshold is being fixed. What is fixed in advance is **which call sites change,
which deliberately do not, and what may not move as a result.**

The reason this needs a register at all is stated in `RUN_RULES` A6's spirit and in this
project's own history: M2 touches the statistic that **every pre-committed gate reads**. A
scoping decision made after seeing which way the numbers moved would be indistinguishable from
choosing the inference method that gives the preferred answer.

---

## 0. WHICH M2 AND M6 — THE ID COLLISION IS REAL

`VALQUO_LEDGER.md` warns about id collisions and this pair is one. There are **two** documents
with an M2 and an M6:

* **`SECURITY_AUDIT.md`** — M2/M6 are web-security items (LLM output escaped before
  `innerHTML`, etc.), **already fixed** at `96fd8bf` per `HANDOFF_security_fixes.md`.
* **`VALQUO_EDGE_AUDIT.md`** — M2 §1507 "Clustered and block inference as the default,
  everywhere" and M6 §1557 "Fix the results file's silent-failure mode, and its date ranges".

**This register covers the `VALQUO_EDGE_AUDIT.md` pair only.** The ledger rows at
`VALQUO_LEDGER.md:332` (M2, OPEN) and `:336` (M6, OPEN) are the edge-audit ones.

---

## 1. WHAT IS ALREADY DONE — measured, not assumed

Both items are **partly closed already**, and scoping them as if they were untouched would
re-do landed work and overstate this session's contribution.

### M2 — the trade-level (options) half is DONE

`R3` (2026-08-05, `valuation/edge/options_stats.py`) delivered essentially all of M2's
trade-level paragraph: a **date-block bootstrap** resampling calendar months together
(`date_block_bootstrap:210`), **purge and embargo for the CSCV splits** (`purged_split:363`),
the **paired name-year sign test**, and **`n_eff`** — reported as *two* estimates
(`n_eff_icc`, `n_eff_conservative`) with the explicit rule that neither is presented alone,
gated on `clustering_measurable` against a **shuffled null**.

R3's discipline is the precedent this register adopts on the equity side: **a raw design
effect is not evidence of clustering** — 600 independent draws in 12 blocks report a design
effect near 1.8 purely from sampling error, because the ratio is F(k−1, n−k). Any design
effect reported here ships with its own null or it does not ship.

### M6 — the block-level half is DONE

`B22` delivered `RESULT_BLOCKS` (`fundamental_panel.py:4458`), per-block stamping via
`out.setdefault(_k, {"status": f"error: {e}"})`, and `missing_result_blocks()` called as a
schema check before the file is written. `M3`'s guard census then gave it a behavioural test.

**The options-bot lane already reported the correct remaining scope** and declined to change
another lane's row (`HANDOFF_optionsbot.md:1280-1295`): *"the FIELD-level half does not exist
at all, and that is the half the R9 loss actually came through."* This register accepts that
finding and closes exactly that half.

---

## 2. M2 — THE CONSTRAINT THAT GOVERNS EVERYTHING BELOW

**Nothing in the published record may move, and no pre-committed gate may silently change its
basis.**

This is not caution for its own sake. `long_short_tstat` — the **naive** i.i.d. statistic — is
the key read by:

* `holdout_compare_panels` (`fundamental_panel.py:3683-3696`) — the shipped gate that decided
  `SECTOR-NEUTRAL-B6`, `S20`, `S21`, and whose margins (**+0.25 t** AND **+100bps alpha, both
  halves**) were committed against *that* statistic;
* `holdout_theme_validate` (`:3793`) — `low_risk`, `insider`;
* `ablation.py:154`, `ev_multiples_study.py:294`.

And the **calibrated placebo floors are statistic-specific and configuration-specific**:
naive **2.1437**, HAC **2.2837**, alpha HAC **2.2913**, all at *the full-universe decile book,
69 dates, H = 63, **lag 1***. Session 10 exists precisely because X7 calibrated 2.14 on the
naive statistic and R9 then made the HAC statistic the quoted one, and the two were compared
to each other for two sessions.

**Therefore, fixed in advance:**

1. **Every existing key keeps its exact current meaning and value.** `long_short_tstat` stays
   naive. `long_short_tstat_nw` stays HAC **at lag 1**.
2. **Every gate keeps reading the statistic it was calibrated against.** Switching a gate to
   clustered inference would re-quote every verdict that gate has ever produced. That is a
   separate decision, needs its own register, and is **not made here.**
3. **A re-run of the artifact must be bit-identical on every existing leaf** except additive
   new keys. This is the falsifiable control (§6, C1).

"Clustered is the default" is therefore implemented as: **the shared function every site now
calls returns the clustered figure as its unqualified `t`, the naive figure is carried beside
it explicitly labelled a diagnostic, and the two sites that today have no clustered figure at
all gain one.** It is not implemented by redefining keys that records and gates depend on.

---

## 3. M2 — THE CALL-SITE LIST (this is the part being pre-registered)

### 3a. CHANGED — routed through one shared definition

A single function, `valuation/edge/statistics.py::mean_inference`, becomes **the** cross-date
inference definition. Clustered by default. Every site below calls it.

| # | site | file:line | statistic | today | after |
|---|---|---|---|---|---|
| 1 | `quantile_backtest` long-short | `fundamental_panel.py:2510` | `long_short_tstat` | naive (local `tstat`) + HAC lag 1 | **unchanged keys** + new `long_short_inference` |
| 2 | `quantile_backtest` top-decile alpha | `:2521` | `top_decile_alpha_tstat` | naive + HAC lag 1 | **unchanged keys** + new `top_decile_alpha_inference` |
| 3 | `benchmark_panel` excess | `:2595` | `excess_tstat` | naive + HAC lag 1 | **unchanged keys** + new `excess_inference` |
| 4 | `per_signal_ic` | `:3075` | `ic_tstat` | **naive only — NO clustered figure exists** | unchanged key + new `ic_inference` |
| 5 | `theme_ic` | `:3112` | `ic_tstat` | **naive only — NO clustered figure exists** | unchanged key + new `ic_inference` |

**Sites 4 and 5 are the substantive M2 gap on the equity side, and they are worth stating
plainly: the theme IC *t* — the statistic carrying X7's calibrated bar of 2.71, the bar
`quality` and `capital_discipline` are said to clear — has never had a clustered variant
computed at all.** An IC series indexed by rebalance date is exactly the object R9 showed is
serially correlated for the long-short spread. Whether it *is* correlated here is an open
measurement, not an assumption; §6 C4 records it either way.

Adding `ic_inference` does **not** re-quote the 2.71 bar or the theme table: the existing
`ic_tstat` values are untouched, and the new clustered figure is a **new** statistic with **no
calibrated floor**, labelled as such. Nobody may compare a clustered theme IC *t* to 2.71.

### 3b. NOT CHANGED — deliberately, with reasons

| site | why not |
|---|---|
| `holdout_compare_panels`, `holdout_theme_validate` gates | Their margins were committed against the naive statistic. Changing the basis re-quotes every verdict they produced. Needs its own register. |
| **The shipped HAC lag (1)** | M2 asks for the lag to come from the autocorrelation rather than convention. The auto lag is **computed and reported as a diagnostic** (§4) but **not adopted**: at n = 69 the Schwert rule gives lag 3, which would move the published HAC *t* of 2.6199 *and* invalidate the 2.2837 floor calibrated at lag 1. Adopting it is a re-quote and a re-calibration, not a refactor. |
| **CPCV embargo from max feature lookback** (M2's last paragraph) | `ret_12_1` reaches back 252 trading days = four rebalance periods against a one-period embargo. This is a real and probably material defect — but changing it moves PBO, the Deflated Sharpe and the adopt gate. It is a **results change**, out of scope here, and is recorded as still-open. |
| `valuation/engine/calibration.py:737` | A **fourth** hand-rolled naive t-stat, byte-identical in shape to `quantile_backtest`'s local one. **Engine lane**, not mine. Reported as a bug (§8), not touched. |
| `valuation/edge/ev_multiples_study.py:135` | Parked study; its `ic_tstat` feeds no shipped decision. |
| `valuation/research/lazy_prices_ic.py:90,99` | Already carries both `tstat` and `nw_tstat`. Research lane. |
| `options_stats.py` | M2's trade-level half, delivered by R3. Nothing to do. |

---

## 4. M2 — WHAT `mean_inference` RETURNS, fixed now

Clustered first, naive labelled, and **`n_eff` beside `n` wherever a *t* appears** (M2's third
requirement, and the one nothing in the equity lane does today).

```
t              HAC/Newey-West at `lag` — THE DEFAULT, the unqualified "t"
method         "newey_west_hac"
lag            the lag actually used (1 unless a caller overrides)
lag_source     "fixed" | "auto_schwert"
n              number of usable periods
n_eff          AR(1) effective sample size, n·(1−rho)/(1+rho), clipped to [1, n]
autocorr_lag1  rho, the estimate n_eff is built from
t_naive        the i.i.d. statistic — DIAGNOSTIC ONLY
naive_note     why it is a diagnostic
ljung_box      {q, df, p_value, acf} — whether the naive t was ever entitled to be believed
auto_lag       floor(4·(n/100)^(2/9)) — REPORTED, NOT ADOPTED
t_auto_lag     HAC at auto_lag — REPORTED, NOT ADOPTED
```

`n_eff` uses the AR(1) form the project already uses in `track_meter` (design effect 1.4661
there), so the two lanes report the same kind of quantity. It is an **estimate off one
autocorrelation coefficient**, not a measurement with a null behind it, and is labelled that
way — R3's rule about design effects applies to it.

---

## 5. M6 — FIELD-LEVEL SCHEMA ASSERTION

### The class, and the two times it has bitten

A **hand-written fixed list of field names** projects a producer's dict into a consumer's
payload, and anything the producer computes that is not on the list is dropped **silently**.
Both instances were caught by a human reading two files side by side.

1. **A computed t-stat.** `quantile_backtest` computed
   `top_decile_alpha_tstat = 4.517421601141459` correctly on the first full run;
   `results_file.build_payload` whitelists what it writes, so the canonical file recorded
   `None` beside it. Nothing raised. (`HANDOFF_edge_audit.md:1966-1972`,
   `HANDOFF_optionsbot.md:1203-1211`.)
2. **A refusal flag.** `archive.py::archive_scan:96-101` names **ten** keys explicitly and
   stores `fair_value` but **not** the refusal flag or reason, so the permanent archive cannot
   distinguish *"refused"* from *"not computed"*. Reported by the live-data lane and marked
   **"edge lane, not mine"** (`HANDOFF_live_data_bugs.md:1498`, `:1567`) — i.e. mine.

Measured today and quoted by the options-bot lane:
`build_payload({"construction": {"a_brand_new_metric": 1.23}})` returns a `construction` block
with no such key **and no complaint.**

### What is built

`valuation/edge/payload_schema.py` — one guard, enumerating **from the source of truth**
(the keys the producer actually computed), never from a registry of expected fields. That
direction is the whole point: M3's census showed that a guard reading a registry *cannot see
the thing it exists to catch*, because an unregistered field is invisible to it.

```
dropped_fields(source, projected, allow) -> [ {block, field}, ... ]
```

* Applied to every **projected** (hand-whitelisted) block in `build_payload`:
  `construction`, `portfolio`, `cpcv`, `institutional_dependence`, `regime`, `ev_freshness`,
  `signal_coverage`, `per_horizon`.
* Pass-through blocks (`benchmarks`, `costs`, `after_tax`, `holdout_validation`, …) carry the
  producer's dict whole and cannot drop a field by this mechanism. They are **not** exempt from
  the block-level check that already exists.
* Legitimate drops are declared in an **explicit, commented allowlist** — the only sanctioned
  way to drop a field. An allowlist entry is a decision somebody wrote down; a silent drop is
  not.

### Failure behaviour — fixed now, because this is where a check gets quietly softened

* The findings are stamped into the payload's **`errors`** block, which already renders as a
  loud `DEGRADED RUN` banner in `BACKTEST_RESULTS.md` and is the established mechanism.
* **Both files are written first, then the run raises.** Writing first is deliberate: a
  40-minute run must not lose its output, and the evidence has to be *on disk* to be
  actionable. Raising after is what makes it "fail the run" rather than a warning nobody reads.
* **No environment-variable escape hatch is built.** `RUN_RULES` A5 — never silence a check.
  The allowlist is the legitimate door and it leaves a diff.

`archive_scan`'s ten-key list is fixed in the same change (it is the second incident, and
fixing the guard while leaving a known live instance of the bug would be indefensible).

---

## 6. CONTROLS — committed before the code exists

* **C1 — nothing moved.** Re-running `build_payload` on a recorded `res` reproduces every
  existing leaf **bit-identically**; the only diffs are additive new keys. This is the
  falsifiable form of §2. If C1 fails, the change is wrong, not the control.
* **C2 — the guard fires on the real historical bug.** A fixture reproducing R9's exact
  shape (`construction` computing `top_decile_alpha_tstat` while the projection omits it)
  must be **reported**. This is M3's known-bad-fixture standard: the guard's *wiring* is under
  test, not just its arithmetic.
* **C3 — the guard fires on the second incident.** A `archive_scan` row carrying a refusal
  flag that the projection drops must be reported.
* **C4 — clustered vs naive, measured not assumed.** Report, for the long-short spread and for
  the theme ICs, `rho`, `n_eff`, and the naive/HAC gap. **Reported whichever way it comes out**,
  including the outcome that theme IC series are *not* materially autocorrelated and site 4/5's
  new figure is uninteresting.
* **C5 — the guard is not vacuous.** It must pass on today's real payload. A guard that fires
  on everything is as useless as one that fires on nothing.
* **C6 — no new naive t-stat can be added silently.** A test pinning that the edge lane's
  cross-date sites delegate to `mean_inference`.

---

## 7. EXPECTATIONS, written down first

This project's directional expectations have been wrong far more often than right, which is
exactly why they are recorded before the run.

1. The long-short spread's `rho` reproduces R9's **+0.189** and `n_eff` lands near **47** of
   69. *Confidence 80/20.*
2. **Theme IC series ARE meaningfully autocorrelated**, so the clustered theme IC *t* comes in
   **below** the naive one for most themes. *Confidence 60/40 — and if it is wrong, the "no
   clustered figure exists" gap in §3a is a smaller finding than it looks.*
3. The auto (Schwert) lag at n = 69 is **3**. *Confidence 90/10 — arithmetic.*
4. C1 passes with zero moved leaves. *Confidence 85/15.*
5. The field-level guard finds **at least one further live drop** beyond the two known
   incidents, somewhere in `build_payload`'s eight projected blocks. *Confidence 55/45.*

## 8. BUGS TO REPORT REGARDLESS OF OUTCOME (RUN_RULES A3)

* `valuation/engine/calibration.py:737` — a fourth duplicate naive t-stat. **Engine lane.**
* The CPCV **one-period embargo vs a 252-day feature lookback** (M2's own last paragraph).
  Still open, materially affects PBO/DSR, needs its own register.
* Anything C5/the guard turns up in the other six projected blocks.

## 9. WHAT THIS DOES NOT DO (RUN_RULES A4)

* Does not re-quote, re-run or re-calibrate **any** published figure.
* Does not change any gate, threshold, weight, or `CONFIG` value.
* Does not adopt the autocorrelation-derived lag.
* Does not fix the CPCV embargo.
* Does not touch the options lane, the engine lane, or the research lane.
* **Charges zero trials.** Neither item searches anything or tests a hypothesis, so equity `N`
  stays at **155**. A refactor and a guard are not trials, and inflating `N` would understate
  every future claim's significance as surely as deflating it overstates them.
