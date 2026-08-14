# PRE-REGISTRATION — V6-B: the dip branch reframed as a RISK question

**Registered 2026-08-13, blind.** Committed **ALONE** — one `.md`, zero `.py` — and a strict git
ancestor of every commit that measures anything. V6's four nulls are official and landed
(`c2b8cd4`); this asks a different question of the same population.

**Three arms. Arm 1 is the primary and it is a RISK claim, not an alpha claim.**

---

## 0. What V6 settled, and why that does not settle this

V6 asked whether a quality-conditioned drawdown **outperforms**. All four arms came back NULL, and
the register is closed. **It never asked whether such a name is less likely to be destroyed**, and
those are different questions with different decision consequences: a screen that does not raise
return can still be worth shipping if it lowers the chance of a catastrophic outcome, and the tab's
honest sentence would then be *"historically, dips like this died less often"* rather than a return
claim.

**V6's floors are reused UNCHANGED and are not re-tuned**: `quality` theme z-score `> 0` **and**
point-in-time `health >= 50`, both scale midpoints, imported from `scripts/v6_dip_detector.py`
rather than restated. **Re-tuning them here would make this a second look at V6's own search
space**, which is the in-search → hold-out collapse this project has already paid for. **A changed
floor is void condition 6.3.**

---

## 1. Premise findings — measured BEFORE this register, none of them an outcome

**The V6 lesson is applied literally: every control column was verified to EXIST before a word of
this was written.** V6's C8 was pointed at `marketcap` when the panel's column is `market_cap`, and
a `.get()` would have returned `None` — reading as *"no size tilt"* rather than *"this control never
ran"*.

### 1a. THE HEADLINE PREMISE, AND IT REWRITES THE TASK'S OWN SECOND METRIC: ON THIS UNIVERSE, DELISTING IS OVERWHELMINGLY ACQUISITION, NOT DEATH

The task asks for *"P(delisting/distress within 252d, ACTIONS mask)"*. Measured on the panel's own
2,531 names over 2009-2026:

| ACTIONS code | tickers | what it is |
|---|---|---|
| `delisted` | **708** | the UMBRELLA — every reason code below is also flagged this |
| `acquisitionby` + `mergerto` | **585** | **82.63% of all delistings. A takeover premium is a GOOD outcome.** |
| `bankruptcyliquidation` | **97** | distress |
| `regulatorydelisting` | **13** | distress |
| `voluntarydelisting` | 10 | ambiguous — going private can be either |
| delisted with NO reason code | **3 (0.42%)** | genuinely unclassifiable |

**So a naive `P(delisted within 252d)` would principally measure TAKEOVER PROBABILITY, and it would
run against the healthy set if acquirers prefer good businesses — which is the obvious prior.** It
would have produced a confident, backwards answer that looked like a risk measurement.

**DISTRESS is therefore defined as `bankruptcyliquidation ∪ regulatorydelisting` and NOTHING
else.** Acquisitions are counted, reported beside it, and **never** added to it. `voluntarydelisting`
(10 names) is reported as its own row and is in neither.

**A note on generality, because the same probe says something different off this universe:** across
all 19,207 delisted tickers in ACTIONS, **36.2% carry no reason code**. On *this* panel it is 0.42%.
The classification is nearly complete here and would not be elsewhere — **the clean split is a
property of the megacap-tilted panel, not of the ACTIONS file.**

### 1b. DISTRESS IS RARE, SO THE DISTRESS LEG IS POWER-GATED IN ADVANCE

**110 distressed names in total** (97 + 13), across 17 years and 2,531 names — **4.3% of the
universe, ever**. Split across dip cohorts × healthy/unhealthy × two halves, the per-cell counts
will be small.

**This is registered now, before any count is read: the distress leg is SECONDARY and carries a
power floor.** It needs **≥ 30 distress events among dipped rows in EACH half**; below that it is
**VOID — UNDERPOWERED BY CONSTRUCTION**, reported as such and explicitly **NOT** as a null. S18's
and U2's class, and V6's own §3.7.

### 1c. THE INSIDER SIGNAL MUST BE BUILT FROM TRANSACTION CODES, NOT FROM THE SHIPPED NET

Measured on all 5,636,964 rows of `insiders.csv`:

* **`transactionvalue` is UNSIGNED** — 2,608,419 positive, **ZERO negative**, 775 zero — and only
  **46.29%** covered. It cannot express a sale.
* **`transactionshares` is signed and 100% covered** (1,860,396 positive / 2,216,036 negative).
* **`transactionpricepershare` is 61.28% covered**, and the shipped `_insider_score` computes
  `shares × price` with an unsigned `transactionvalue` fallback. **The fallback is effectively
  dead — it fires on 2 rows of 5.6M — but 2,182,601 rows (38.7%) have NEITHER and are silently
  SKIPPED.** So the shipped `insider` theme is computed on about 61% of filings. Reported, not
  repaired: it is on the shipped path and cannot be valued without a price.
* **`transactioncode` is 72.6% covered, 18 distinct values.** `P` = open-market purchase
  (**124,181** rows, **2.2%** of the file), `S` = sale (1,002,158), `A` = grant (1,113,289),
  `M` = option exercise (993,120), `F` = tax withholding (461,748).

**So "insider net buying" computed over ALL transactions is dominated by grants, option exercises
and tax withholding — none of which is a decision to buy.** Arm 3 uses **code `P` only**, which is
unambiguous: **123,236 P rows have positive shares and ZERO have negative shares**, and 98.39% take
the signed path. It needs no price coverage because it is a **count**, not a dollar total.

**A CORRECTION TO MY OWN PROBE, recorded because the error is the instructive part:** its first cut
reported `transactioncode` coverage as **1.0** by testing `astype(str) != "nan"`. The direct
`notna()` measure is **0.726**. The 27.4% of filings with no code **cannot be classified as
purchases or anything else**, and that is a real limit on Arm 3, not a rounding detail.

### 1d. Everything Arm 2 needs is already banked, and was checked rather than assumed

`data/free_analysis/panel_v6.pkl` — **69 dates, 2,531 names, 113,945 rows** — carries all twelve
columns the arms read, with **zero absent**: `date`, `ticker`, `fwd_ret`, `fwd_ret_h126`, `quality`,
`value`, `momentum`, `size`, `insider`, `capital_discipline`, `institutional`, **`market_cap`**.
Price files exist for **400 of 400** sampled panel names, so the forward paths Arm 1 needs are
available. **No panel rebuild.**

---

## 2. ARM 1 — SURVIVAL (PRIMARY). Do healthy dips have a thinner left tail?

**Population:** every `(date, ticker)` panel row whose drawdown is **≤ −20%** (V6's `dip20`, same
252-day trailing-high construction, same split-adjusted basis, same strictly-`<= d` rule).

**Split:** `HEALTHY` = V6's floors unchanged; `UNHEALTHY` = the complement **within the dipped
set**. This is a within-dip comparison throughout — the market is not the comparator here.

**The three metrics, fixed now:**

| id | metric | direction that supports the claim |
|---|---|---|
| **M1** | `P(a further −20% within 126 trading days)`, measured from the dip date's close | healthy **LOWER** |
| **M2** | `P(DISTRESS within 252 calendar days)` — bankruptcy ∪ regulatory only (§1a) | healthy **LOWER** |
| **M3** | forward drawdown distribution over 126 trading days: `min(close_t)/close_0 − 1` | healthy **less negative** at the mean, median and **p05** |

M3 ships through the **shipped `statistics.distribution()`** (S28), so the tail statistics are the
same arithmetic the results file already publishes, and its units travel with it.

### 2.1 What counts as real — committed before looking

An arm cell is **REAL** only if **all three** hold:

1. **STATISTICAL.** The per-date healthy-minus-unhealthy difference clears **that metric's own
   within-date permutation p95** (500 draws, the healthy label shuffled among that date's dipped
   names, count preserved) — **in BOTH halves**, boundary embargoed.
2. **ECONOMIC.** For **M1**, an absolute reduction of **≥ 3.0 percentage points** in both halves.
   Fixed now, not tuned: on a plausible 20–30% base rate that is a ~10–15% relative reduction, which
   is the smallest effect that would justify the sentence the tab wants to say.
3. **SIGN-STABLE.** Same sign in both halves. A sign flip is this project's most repeated failure
   and is disqualifying on its own.

**M1 is the deciding metric.** M2 is secondary and power-gated (§1b). M3 is descriptive and
**carries no verdict on its own** — a distribution is not a threshold — but a **contradiction**
between M3's tail and M1 must be reported rather than resolved in the claim's favour.

**Ambiguous against any bar is a NULL** (`RUN_RULES` A6).

### 2.2 KILL CONDITION (the task's own, made explicit)

> **If M1 does not separate — healthy not lower in both halves — the dip branch CLOSES at two
> sessions total.** No third register, no re-cut with different floors, no "try 30%". Recorded as
> closed in the ledger and in `VALQUO_EXTENSIONS.md`.

If M1 **does** separate, the tab earns *"historically, dips like this died less often"* — **with
§1a's caveat attached** — and **`V6-OPT` (the cash-secured-put branch) unlocks as a separately
registered item.** It is **not** unlocked by M2 or M3 alone.

---

## 3. ARM 2 — THE OVERLAY (an ALPHA claim, and it pays alpha rent)

**Population:** the **TOP DECILE ONLY**, by the shipped composite. Built with the shipped
`composite_from_frame` and the shipped `cross_sectional.zscore`, then `argsort(-comp)` and
`array_split(order, 10)` taking `buckets[0]` — **the identical construction `quantile_backtest`
uses**, so this decile is the same object the published `top_decile_alpha` is measured on. **C7
proves it by reproducing that number from my own membership.**

**Question:** within the top decile, do names currently in a **≤ −20% drawdown** outperform the rest
of the decile, forward?

**This is a different question from V6.** V6 conditioned on **health floors**; this conditions on
**the composite**. A name can be top-decile and unhealthy, or healthy and mid-decile.

**Two cells, each with its own verdict and each charged a trial:** **A2a** at **63d** (the deployed
rebalance horizon, primary) and **A2b** at **126d**.

**Statistic:** the per-date difference of equal-weighted mean forward returns, dipped-in-D1 minus
rest-of-D1, summarised by the shared **`statistics.mean_inference`** (M2's one definition), with
`n_eff` travelling alongside `n`.

**Bar:** the cell's **own** within-date permutation p95 (500 draws, the dip label shuffled among
that date's top-decile names), **in both halves**, sign-stable. **X7's 2.2837 and 1.95pp are NOT
quoted** — they calibrate a decile-book long-short *t* and a top-decile alpha margin, and this is a
within-decile subset difference, which is neither. Quoting them would be the uncalibrated
extrapolation X3 and session 10 both paid for.

**Coverage floor:** ≥ 10 dipped and ≥ 10 non-dipped names in the decile per date, and ≥ 24 usable
dates per half, else **VOID — UNDERPOWERED**, not NULL.

**KILL CONDITION:** a cell that fails is dead; there is no re-cut at another depth, another horizon,
or a signal-weighted book.

---

## 4. ARM 3 — RIDER: dip × insider open-market buying

**Population:** the dipped rows of Arm 1.

**Signal (event-conditioned, NOT a theme cross-product):** at least one insider **open-market
purchase** — `transactioncode == "P"` — **filed** during the drawdown window, defined as the **126
calendar days before the rebalance date**, with `filingdate` **strictly before** the rebalance date.
Strictly-before is **audit B26's** rule: a Form 4 dated `as_of` is not reliably public before that
day's close.

**Why a count of P and not the shipped `insider` theme:** §1c. The theme is a dollar net over all
transaction types on 61% of filings; this is a count of unambiguous conviction buys. **It is
deliberately a different object, and it is not the theme by another name** — C6 measures the
correlation between the two and reports it.

**Question:** among dipped names, do those with insider buying in the window outperform those
without, forward **63d**? One cell, one trial.

**Bar:** its own within-date permutation p95 (the buy label shuffled among that date's dipped
names), both halves, sign-stable.

**KILL / VOID:** `transactioncode` is only **72.6%** covered, so a filing with no code is
**unclassifiable and is counted as NO BUY** — a conservative direction that can only *dilute* the
signal, never manufacture it. If the median count of buy-flagged dipped names per date is **< 10**,
the arm is **VOID — UNDERPOWERED**, not NULL.

---

## 5. Controls

| id | control | gating? |
|---|---|---|
| **C1** | The harness reproduces the shipped record (`top_decile_alpha` 0.07174142332098163, LS naive 2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909) to ≥ 9 decimals. **Runs in its OWN pass and ABORTS before any arm.** Session 26's repaired defect. | **YES** |
| **C2** | Canonical panel: 69 dates, 2,531 names, label `full` — asserted, not warned. | **YES** |
| **C3** | Point-in-time, three ways: no price dated `> d` enters a trailing high; **no ACTIONS event dated `<= d` is counted as a forward outcome**; no insider filing dated `>= d` is read. Zero violations required. | **YES** |
| **C4** | **Coverage first** (COVERAGE RULE): per-date counts of dipped / healthy / unhealthy / top-decile-dipped / buy-flagged, plus the raw distress and acquisition event counts, **before any metric is read**. | no |
| **C5** | The distress/acquisition separation is real and exclusive: an acquired name is **never** counted as distress, asserted on the actual event sets, with both figures published side by side. | no |
| **C6** | **Fidelity to V6 and non-identity of Arm 3.** The healthy/unhealthy split reproduces V6's own per-date conditioned counts **exactly** (its artifact banks them), proving the floors were not re-tuned; and the Arm-3 buy flag is correlated against the shipped `insider` theme and reported, so it cannot be the theme wearing a new name. | no |
| **C7** | **Arm 2's top decile IS the shipped top decile**: `top_decile_alpha` recomputed from my own decile membership must reproduce the published 0.07174142332098163. | no |
| **C8** | Characteristic tilt (median market cap, mean `size` z) for every split in every arm — **a size sort must not be reportable as a health, composite or insider finding** (U7, S10, V6's own C8). Reads **`market_cap`**, the panel's real column name. | no |

**Every permutation draw is banked, not just the percentiles** (`RUN_RULES` A9).

---

## 6. Void conditions

1. Any `.py` in this file's commit, or this file not being a strict ancestor of every measurement
   commit.
2. Any arm, metric, depth, horizon or window beyond those named above.
3. **Any change to V6's floors**, or any sweep of them.
4. Substituting X7's calibrated floors for the per-cell permutation bars.
5. Counting an acquisition, merger or voluntary delisting as distress; or reporting a
   `P(delisted)` figure without its acquisition share attached.
6. A failing **C1**, **C2** or **C3** with any arm number nevertheless read or reported.
7. Editing this register after any arm result exists. Corrections go in the handoff, against the
   register.

---

## 7. Expectations, with odds, written before any result

1. **M1 separates — healthy dips fall a further 20% less often.** 60/40. This is the one directional
   call I hold with any confidence, because the floors select on leverage and coverage and a further
   −20% is mechanically easier for a levered balance sheet.
2. **M1 clears statistically but MISSES the 3.0pp economic floor.** 50/50, and it is the outcome I
   consider most likely to be misreported if it happens.
3. **M2 is VOID on power, not NULL.** 65/35 — 110 distressed names is very few once split four ways.
4. **The healthy set is ACQUIRED more often than the unhealthy set.** 70/30. If so, a naive
   `P(delisted)` would have shown healthy names "dying" MORE, which is §1a's whole point.
5. **Arm 2 is NULL.** 75/25. It is an alpha claim on a panel where essentially every alpha claim is
   null, and a dip inside the top decile is close to V6's question with a different conditioner.
6. **Arm 3 is VOID or NULL on coverage.** 60/40. Code `P` is 2.2% of a file that is 72.6% coded.
7. **The buy flag is only weakly correlated with the shipped `insider` theme (|ρ| < 0.3).** 65/35 —
   the theme is dominated by grants and exercises, which are not decisions.
8. **Healthy dipped names are LARGER** than unhealthy dipped ones. 75/25 — V6 already measured
   1.73×, and C8 exists so a size sort cannot be reported as a health finding.

---

## 8. Trial cost

**Six equity trials: Arm 1 three (M1, M2, M3 are three distinct pre-committed metrics, each of
which could independently be reported as a finding), Arm 2 two (63d, 126d), Arm 3 one.**

**Equity `N` 206 → 212.** The 206 is **re-measured from `research_log.detail()` after this session's
merge of `origin/main`**, not quoted from `CLAUDE.md`. Options 287 and infra 11 are untouched.

**Arm 1 is charged in full even though it is a RISK claim rather than an alpha claim.** The trial
counter is a search counter, not an alpha counter; understating `N` **overstates** significance on
every DSR-gated claim, and this session already caught one row that silently charged 1 instead of 4.
The `n` column is written as **`n=6`**, the literal form `research_log._parse` requires.

`BACKTEST_RESULTS.json` is refreshed from a clean tree at the new denominator.

---

## 9. What this register does NOT test — named so it is not mistaken for tested

* **Whether the dip screen predicts RETURN.** V6 answered that: no, on four arms. Arm 2 asks a
  narrower version of it inside the top decile and is not a re-run of V6.
* **Cash-secured puts (`V6-OPT`).** Explicitly downstream, unlocked only by Arm 1's M1, and needing
  its own register with its own trial charge.
* **Any floor other than V6's.** Not swept, not re-tuned.
* **Causes.** Nothing here reads news, flow or positioning; a drawdown is a fact about a price.
* **The 38.7% of insider filings with neither a price nor a value** (§1c). Reported as a property of
  the shipped theme, not repaired here.
