# PREREG — S23: the exit rule for the equity book

**Committed BEFORE any measurement code exists.** This file is committed ALONE, in a commit that
is a strict git ancestor of the commit introducing `scripts/exit_rule.py`. That ordering is what
makes "pre-registered" checkable rather than asserted — the same discipline V2G used at `6d8750a`
and S22 at `6b187dd`.

Ledger item **S23** ("Exit rule for the equity book", status OPEN, *"only forward references —
mentioned as a dependency, never written up"*). Routed to this lane as unblocked.

**Nothing here is adopted by running it.** Under `PAPER_TRACK_CONTRACT.md`'s vintage rule, an
adopted change to construction **closes the current vintage and opens the next**, resetting the
whole five-year clock for zero statistical gain (Rule 6). Adoption is Don's call, made on this
evidence, not a consequence of a number clearing a bar.

---

## 1. The question, and the prior it has to beat

The live book buys the top 25 by composite and holds each name until it falls out of the top 50,
subject to a two-period minimum hold. Nobody has ever tested that exit against an alternative. It
is an inherited rule, like the 63-day horizon S22 found was never a measured optimum.

**S22 is the prior, and it is a strong one.** On the record as of 2026-08-10: annualized top-decile
alpha is **flat from three months to two years** (+6.59% → +5.10%), cumulative alpha reaching
+10.20% at eight quarters, alpha HAC *t* never below 3.16, median rank IC **rising** with horizon
(+0.034 → ~+0.072). **An edge that is still accruing at two years argues against selling early on
price.** A take-profit truncates exactly the right tail S22 says keeps paying; a stop-loss sells a
name whose composite still ranks it a buy.

**So this register expects the incumbent to win, and says so in §8 before running.** The value of
running it anyway is that the project's directional expectations have been wrong more often than
right, and because "we never tested the exit" is a live hole in the story regardless of which way
it falls.

---

## 2. The arms — one buy rule, five exits, and no grid

**Every arm shares the identical BUY rule** (top 25 by composite at each rebalance) and the
identical **`min_hold = 2`**. Only the exit differs, so any difference is attributable to the exit
and not to selection or to churn protection.

| arm | exit |
|---|---|
| **A0 INCUMBENT** | falls out of the top **50** (`exit_rank = 2N`) |
| **A1 FV-POINT** | rank-exit **OR** price ≥ the point-in-time blended fair value (`gap ≤ 0`) |
| **A2 FV-LENSBAND** | rank-exit **OR** price ≥ the **lowest available lens** of the same valuation |
| **A3 TPSL-ONEIL** | rank-exit **OR** cumulative return since entry ≥ **+25%** or ≤ **−8%** |
| **A4 TPSL-2TO1** | rank-exit **OR** cumulative return since entry ≥ **+20%** or ≤ **−10%** |
| **C-NEVER** | **CONTROL** — never sells; holds until the name leaves the panel |

### 2a. Why the challengers ADD to the rank exit rather than replace it

The product question is *"should a price-based exit be added?"*, and adding keeps the book size
bounded and comparable. A pure replacement — price rule only — lets a permanently-cheap name sit
forever and turns the book into a different object, so it answers a different question. **The
replacement family is deliberately NOT run**, and that is recorded here in advance rather than
discovered as an omission.

`C-NEVER` is the one exception and is **a control, not a candidate**: it is the "hold forever"
extreme S22's prior points at, and its book **grows without bound**, so its book size is not
comparable to the others. That is stated now so no result of the form "the control won" can later
be quoted as if it were an adoptable strategy.

### 2b. The TP/SL pairs come from convention and are NEVER tuned

**This is the param-search trap and it is closed by naming the numbers here, before any run.**
`sweep_hold_params` already exists and sweeps `trailing_stop` over `[None, 0.20, 0.30, 0.40]`;
picking the best cell of any such grid is exactly the "in-search +8.43%/yr → locked hold-out
−0.04%/yr" failure this project has already paid for.

* **A3 = +25% / −8%** — O'Neil / CANSLIM's published rule ("cut every loss at 8%, take most gains
  at 20–25%"). A widely-taught, externally-fixed convention this project did not invent.
* **A4 = +20% / −10%** — the textbook **2:1 reward-to-risk** ratio.

**No other TP/SL pair will be scored, no grid will be swept, and neither pair will be adjusted
after seeing a result.** If both fail, the finding is "these two conventional pairs fail", not "a
better pair might exist" — and finding that better pair is a search this register forbids.

### 2c. The fair-value band, also parameter-free

Two variants, both with **zero free parameters**, because a band width would be one more thing to
tune:

* **A1 FV-POINT** — the degenerate band at fair value itself: sell when `gap = ln(fv/price) ≤ 0`,
  i.e. the price has reached the blended point estimate.
* **A2 FV-LENSBAND** — the band is **the engine's own disagreement**: sell when the price reaches
  the *lowest* of the lenses actually available for that name (`dcf_ps`, `comps_fv`, `growth_ps`).
  This is the conservative edge of the range the engine itself produces, not a number chosen here.

A name with no usable fair value (`valuable = false`) **cannot** trigger a valuation exit and is
held on the incumbent rule alone. Coverage of the fair value is reported **before** any verdict,
per the COVERAGE RULE.

---

## 3. Point-in-time, and the two defects that must be fixed to make it so

Fair values are rebuilt through the **live engine** — `calibration.pit_company` +
`calibration.lean_fair_value`, the path pinned by `test_lean_path_matches_the_full_pipeline` —
never re-implemented. Two things measured **before this register was written** stand between that
harness and an honest point-in-time number, and both are recorded here so the fix is not mistaken
for a result:

* **`build_valuation_panel` still carries the B6 defect.** It calls
  `provider.price_history(t, days=TD*lookback_years + horizon + 60)`, taking the **per-ticker
  tail** that `data_providers.py:352` says in its own comment "is never the panel's route now".
  Measured on a 25-name probe it yields **110 rebalance dates starting 1998-12-31** — the
  inverted-universe window B6 removed — against the corrected panel's **69 dates from 2008-01-16**.
  **S23 will not use it.** The S23 builder mirrors `build_fundamental_panel`'s calendar
  (`days=None`, one shared cut) so the two panels align exactly, pinned by control **C1**.
* **The PIT valuation reaches out to LIVE Yahoo prices, which is a hindsight leak.**
  `wacc._resolve_beta` rung 3 calls `data.beta.compute_beta(cd.ticker)` — which fetches
  `yf.Ticker(...).history(period=...)`, i.e. **today's** prices — whenever the point-in-time beta
  is missing, `> 3.0`, or `≤ 0.25`. On the 25-name probe it fired **157 times over 1,122 rows**.
  Valuing a 1999 date with a beta regressed on 2021-2026 returns is look-ahead, and it is also a
  network dependency and a rate-limit hazard.
  **S23 runs the ladder in a no-network mode**: rungs 1 → (2 or 4), never 3. Where the
  point-in-time beta is unusable the engine's own **stated constant** (`BETA_FALLBACK = 1.0`,
  rung 4) is used — the value the ladder itself reaches when corroboration cannot run. The share
  of rows taking the constant is **reported**, and control **C2** asserts **zero** network calls
  during the build.

Both are reported as **BUGS FOUND** against the owning module whether or not S23 adopts anything.

---

## 4. Costs are charged, and the formula is fixed now

`_backtest_hold` charges nothing today. Every arm here is scored **gross and net**, and **the net
figure carries the verdict**, because an exit rule's whole cost is turnover and comparing exit
rules gross would flatter whichever one trades most.

Per period, on an equal-weighted book:

> `drag = BPS_ONE_WAY × (n_bought + n_sold) / n_held`

with **`BPS_ONE_WAY = 33.4`** — the project's **measured** realised one-way cost (B11), not the
older assumed 37 bps. Each name traded pays its own weight's worth of cost, which is exact for an
equal-weighted book. Borrow, impact and taxes are **not** modelled and none of these arms shorts.

---

## 5. Statistics and bars

**PRIMARY: the paired per-period difference** of net book return, challenger − incumbent, over the
dates both arms scored, annualized, with a **HAC(lag 1)** *t*. Paired because every arm is scored
on the same panel and the same dates, so the market move that dominates each level cancels — the
V2G construction.

**NO CALIBRATED FLOOR EXISTS FOR THIS OBJECT, AND ONE IS BUILT RATHER THAN BORROWED.** X7 and
session 10 calibrate `quantile_backtest` statistics on the full-universe decile book;
`_backtest_hold` is a different object (concentrated top-25, event-driven, variable book size), and
S22 has already recorded that a floor may not be quoted outside the configuration it was
calibrated in. So:

* the conventional **2.0** is used only as a labelled **UNCALIBRATED** reference, and is marked so
  everywhere it appears; and
* a **per-arm placebo floor is measured**: the shipped `placebo_panel` block permutation, **200
  draws, seeds 3000–3199**, pushed through the identical arms. Under a permuted signal the exit
  rules still differ from one another, so the p95 of `|paired HAC t|` across draws is the honest
  answer to "how big a difference between two exit rules does no signal at all produce?" It is
  labelled `fixed_weights_null` and, like S22's, may **never** be compared with 2.2837 or 2.2913.

**Decision rule, fixed now.** A challenger **BEATS** the incumbent only if its paired net
difference is **positive** AND its paired HAC *t* clears **its own placebo floor** AND it does so
**in both halves with the same sign**. Anything else is **NO IMPROVEMENT**. A challenger is
**WORSE** if the difference is negative and clears the floor in absolute value. **Ambiguous is a
NULL, not a judgement call** (RUN_RULES A6).

**Both halves**: first 34 / last 35 rebalance dates, the split point used by V2G and S22.

**Reported for every arm regardless of verdict**, because an exit rule is not a single number:
net and gross CAGR, alpha vs the equal-weighted universe, realised **average book size** and
**average holding period**, turnover, the cost drag itself, and the count of exits by **reason**
(rank / valuation / take-profit / stop-loss).

### 5a. The limitation that must travel with the TP/SL arms

**The panel has no intra-quarter path.** A cumulative return since entry is observable only at
rebalance marks, so a name that touches +40% mid-quarter and gives it back is never seen to hit a
+25% take-profit. **Every TP/SL arm therefore triggers LESS often than a true path-dependent rule
would**, which makes each behave more like buy-and-hold than its real-world counterpart.

**The direction is stated now: this biases the measurement IN FAVOUR of the TP/SL arms**, since
§8 expects triggering to hurt. So a TP/SL arm that loses here would lose by more in practice, and
that asymmetry is a reason to trust a negative result and to distrust a positive one.

---

## 6. Controls, committed in advance

* **C1 — the two panels are the same panel.** The S23 valuation panel's rebalance dates must equal
  the factor panel's **exactly** (69 dates, 2009-01-15 → 2026-01-28 as scored), and its
  (date, ticker) keys must be a subset. If the calendars differ the register is void.
* **C2 — no network, no hindsight.** Zero outbound calls during the valuation build, asserted by
  failing the run if `data.beta.compute_beta` is reached.
* **C3 — the incumbent reproduces its own record.** A0 run through the new harness with costs OFF
  must equal today's `_backtest_hold` output exactly.
* **C4 — the arms differ only in exits.** Every arm must buy the identical names on the identical
  dates; the count of buys per date must match A0 for all arms.
* **C5 — the placebo destroys what it claims to.** The median paired difference across draws must
  be near zero for every arm.
* **C6 — costs bite in the right direction.** Net ≤ gross for every arm, and the arm with the
  highest turnover must take the largest drag.

---

## 7. Trial cost

**Five scored arms plus the control: equity `N` 143 → 149.** A0 is the incumbent and is charged
because a race from which a winner *could* be quoted is a search over the whole field.

**Charged at zero:** the placebo calibration (a calibration searches nothing — session 10's
precedent), the half-splits (same arms on subsets — session 7's precedent), and the coverage and
book-size diagnostics (descriptive).

`BACKTEST_RESULTS.json` is regenerated from a clean tree so its Deflated Sharpe is computed at
`N = 149` — **re-run, never hand-patched.**

---

## 8. Expectations, written down first

**The task asks which way I expect it, and S22's finding is the reason.** An edge that is still
accruing at two years argues against early price-based exits, so:

| # | expectation | odds |
|---|---|---|
| 1 | **No challenger beats the incumbent** — verdict NO IMPROVEMENT across the board | 75/25 |
| 2 | **All four price-based exits are NEGATIVE** against the incumbent on the paired net difference | 70/30 |
| 3 | The **TP/SL** arms are worse than the **fair-value** arms (a hard stop is blind to value, and a stop-loss sells a name the composite still ranks a buy) | 60/40 |
| 4 | **C-NEVER beats the incumbent GROSS** but the margin shrinks or reverses net, because its book dilutes | 55/45 |
| 5 | The **stop-loss** does more damage than the **take-profit**, since S22 shows the long leg keeps paying | 55/45 |
| 6 | Fair-value coverage is **below 90%** of held name-periods | 60/40 |

---

## 9. What voids this register

* **C1** fails — the valuation panel is not on the factor panel's calendar.
* **C2** fails — any network call is made during the valuation build.
* **C3** fails — the incumbent does not reproduce `_backtest_hold`'s current output.
* The panel is not the corrected **2,531-name / 69-date** universe.
* Any TP/SL threshold, band definition, `min_hold` or `top_n` is changed after a number is seen.
