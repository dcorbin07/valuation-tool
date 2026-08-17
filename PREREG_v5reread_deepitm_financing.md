# PRE-REGISTRATION — V5 re-read (NOT re-run), and the deep-ITM financing COST test

Written 2026-08-17, before any measurement code for item 2 exists. Committed **alone**, markdown
only, zero `.py`, as a strict git ancestor of every measurement commit.

Two items were briefed. **Only one of them is a measurement.** Item 1 is declined, with the
reasons measured rather than argued, at **zero trial cost**. Item 2 is registered in full and
charges trials. Both are recorded here so that declining is visible in the record rather than
looking like a skipped task.

---

## 0 · Summary of what this register does and does not do

| item | action | trials |
|---|---|---|
| 1 · V5 measured slippage | **NOT RE-RUN.** Already live and already answered. Re-read, and one new fact recorded. | **0** |
| 2 · deep-ITM financing cost | **REGISTERED AND MEASURED.** | **3 (options)** |

**ADOPTS NOTHING. Issues no trade recommendation in either direction.** No file under
`valuation/` changes. `.github/` is not touched. The mutable `data/options` store is not read;
everything banked comes from the **freeze**.

---

## 1 · ITEM 1 — V5 IS ALREADY DONE, AND THE BRIEF'S PREMISE IS REFUTED

### 1.1 It exists, it is pre-registered, and it has a verdict rule

V5 landed **2026-08-09**. On disk right now:

* `scripts/slippage_report.py` (36,566 bytes)
* `PREREG_v5_slippage.md` (10,651 bytes)
* `tests/test_slippage_report.py` (21,679 bytes, 57 tests)
* ledger row in **`VALQUO_EXTENSIONS.md` line 14** — *not* in `VALQUO_LEDGER.md`, which is why a
  ledger grep for "V5" finds nothing and why this item can look un-run.

Its verdict rule was pre-committed and is quoted verbatim from `PREREG_v5_slippage.md` §4:

| condition | verdict |
|---|---|
| n < 30 | **INSUFFICIENT** — no aggregate printed |
| 90% CI excludes 410.0 and lies ABOVE it | DIVERGENT-COSTLIER |
| 90% CI excludes 410.0 and lies BELOW it | DIVERGENT-CHEAPER |
| 90% CI contains 410.0 | CONSISTENT |

### 1.2 Re-read today on the shipped instrument, unchanged

`python scripts/slippage_report.py --from-export data_export/paper_track_history.json`:

* **3 entry fills, 0 exit fills.**
* **M3, the pre-registered headline (exit half-spread vs mid): n = 0.**
* M2 entry-vs-limit: n = 3, printed as raw values only and explicitly `NOT QUOTABLE (n=3 < 30)`.
* Verdict **INSUFFICIENT**, exactly as V5's own §6 expected it at 90/10.

### 1.3 THE BRIEF'S PREMISE IS REFUTED BY THE DATES

The brief states the sandbox *"has been accruing fills since session 14"*. Measured: the three
fills are stamped **2026-08-04, 2026-08-07 and 2026-08-07**. Session 14 is **2026-08-09**.
**All three predate session 14 and zero have accrued since.** The book has not been accruing.

### 1.4 THE BRIEF'S BAR IS A CATEGORY ERROR, AND V5 ALREADY FOUND IT

The brief asks for slippage *"vs the modelled 33.4bps"*. Audit **B11's 33.4 bps is one-way cost
in basis points of STOCK NOTIONAL on the equity fundamental panel.** An options book pays basis
points of **PREMIUM**. `scripts/slippage_report.py:567-571` already prints this on every run and
keeps the constant only under the name `EQUITY_ONE_WAY_BPS_NOT_APPLICABLE`; the ratio is **~12×**
and the two are not the same currency. V5's actual, measured bar is **410.0 bps of premium
(mean) / 333.3 (median)** over 3,885 banked trades.

### 1.5 WHY IT IS NOT RE-REGISTERED

Writing a second register for a hypothesis that already carries a live one creates **two
definitions of one bar** — the B7 defect class this project warns about most, and the reason
`statistics.hlz_hurdle` exists. The instrument is unchanged, the data is unchanged, and the
verdict rule is already committed. Re-running would charge trials to reproduce a banked
`INSUFFICIENT`. **Declining keeps the denominator** (session 8's precedent, where not running an
unresolvable test was recorded as the cheaper action rather than the lazier one).

### 1.6 WHAT IS NEW, RECORDED AT ZERO COST — THE REFRESH PATH IS BROKEN

The local export is a snapshot (`generated_at 2026-08-09`, committed 2026-08-10). The only
mechanism that refreshes it is the weekly `track-backup` Action.

**It FAILED on 2026-08-16** — run `31932667751`, 3 seconds, annotation verbatim: *"The job was
not started because recent account payments have failed or your spending limit needs to be
increased."* Last success **2026-08-09**.

So **no fresher read of the live book exists on any surface this lane can reach**, and V5 cannot
be re-read until that is fixed. This is recorded because it dates the gap rather than leaving it
to be discovered later — `track_meter`'s own not-yet-due-versus-due-and-missing distinction.

### 1.7 Re-open condition, so the next session does not have to re-derive it

**V5 becomes answerable when the export shows n ≥ 30 CLOSED legs** (M3 needs exits, and there
are none). Until then every re-run returns `INSUFFICIENT` by construction.

---

## 2 · ITEM 2 — THE DEEP-ITM FINANCING COST TEST (`DEEPITM-FIN`)

### 2.1 The question, as a cost identity — not an alpha claim

Is the all-in annual cost of controlling \$1 of a name through a **60–90 DTE, delta 0.85–0.95
call** lower than the all-in annual cost of holding \$1 of the stock **on margin**?

```
option_route_bps_yr = (r* − rf) + roll_cost_bps × (365 / DTE)
margin_route_bps_yr = (margin_rate − rf)
```

`r*` is the rate the option market implicitly lends at, recovered from put–call parity. Both
sides are expressed as a **spread over the contemporaneous risk-free rate**, so the comparison
does not depend on the level of rates.

### 2.2 PRIOR, WRITTEN FIRST — AND IT CONTRADICTS THE BRIEF

The brief expects *"cheaper than margin, with caveats."* **I expect the opposite at this tenor,
at 80/20**, and the frontier's own arithmetic is why. Its §2c puts a deep-ITM round trip at
**~53 bps of notional** and annualises it to **~97 bps/yr at 200 DTE**, concluding the financing
case *"only becomes clearly positive at a tenor we do not own"* (730 DTE).

**60–90 DTE is the SHORTEST tenor and therefore the WORST case for roll cost.** At a 75-day
midpoint you roll 365/75 = **4.87×/yr**, so the same 53 bps becomes **~258 bps/yr** — which
swamps a ~43 bps financing edge several times over.

Registered predictions:

| comparison | prediction | odds |
|---|---|---|
| vs Robinhood Gold (~5.75% flat ≈ rf + 145 bps in 2025) | option route **MORE EXPENSIVE** | 80/20 |
| vs Robinhood standard (~11–12% ≈ rf + 600–670 bps) | option route **CHEAPER** | 85/15 |
| the answer depends on WHICH margin rate | **yes** | 85/15 |
| median (r* − rf) at mids lands in [0, +150] bps | yes | 90/10 |

So the brief's expected direction is predicted to hold **only against expensive margin**. If both
comparisons come back "cheaper", my prior is wrong in the informative direction and I say so.

### 2.3 Data — the freeze, and nothing mutable

* **Chains:** `data/options_freeze/R2_CORRECTED_2026-08-08/chains.pkl.gz` — measured
  **2,870,811 rows, 186 names, 2016-01-19 → 2025-12-19**, columns
  `expiration, strike, right, date, bid, ask, volume, open_interest, symbol`.
  The mutable `data/options` and `data/options_derived` stores are **not read**.
* **Spot:** `data/bulk/prepared/bars/<SYM>.pkl` → **`raw_close`**, the as-traded series.
  **Never `close`.** `close` is split- and dividend-adjusted and matching an as-traded strike
  against it is the U1-SPLIT / O6-O7-O17 defect (NVDA 2012: 0.27 against a raw 11.97, a 43×
  ratio) that fails **silently**. All 186 freeze names have bars.
* **Risk-free:** `blackscholes.risk_free_rate` (FRED DGS3MO), **imported, never re-typed**.
* **Dividends:** `data/bulk/prepared/actions.pkl`, per-ticker `dividends` as `(date, amount)`.

### 2.4 COVERAGE FIRST — AND IT REFRAMES THE QUESTION BEFORE ANY NUMBER

**11 of the 86 Valquo Index names are in the freeze — 12.8%**: ASML, BNS, EOG, FDX, HON, MU, SU,
TD, TTE, VRT, WDC.

**Consequence, fixed now rather than after seeing results:** *"Index names"* is **not answerable
at Index scope on owned data.** The headline is measured on the **186-name freeze universe** and
labelled as such throughout. The 11 Index names are reported as a **separate, explicitly
underpowered cell** carrying no verdict. **Quoting an Index-scope claim from the 186-name
universe is a void condition** (§2.9). This is U6's blocker in a new place, and it is stated
before the run for the same reason.

Feasibility, already measured: **83,698 matched two-sided call/put pairs at 60–90 DTE**, across
186 names and 2,891 (symbol, date) chain slices. The design is not coverage-bound at the
universe level; it is bound at the *Index* level.

### 2.5 Construction

Matched `(symbol, date, expiration, strike)` call/put pairs where:

1. **both legs pass `blackscholes.usable_quote(bid, ask)`** — the shared MA45 rule, imported,
   not re-typed. A one-sided or crossed quote is excluded, not repaired.
2. `60 ≤ DTE ≤ 90`.
3. `0.85 ≤ delta_call ≤ 0.95`.

**Delta is computed, not proxied by moneyness.** Implied vol is solved on the **PUT** leg — which
is out-of-the-money at this corner and therefore well-conditioned, where a deep-ITM call's vega
is near zero and the solve is unstable — via `blackscholes.implied_vol`, then
`blackscholes.greeks` gives the call delta at the same vol. Both imported.

`r*` solves, per pair:

```
S − PV(D) − (C − P) = K · exp(−r* · T)
```

**Two price conventions, BOTH reported, and the primary is fixed now:**

| convention | C | P | role |
|---|---|---|---|
| **MID** | (bid+ask)/2 | (bid+ask)/2 | comparable to the frontier's §2c; **secondary** |
| **EXECUTABLE** | ask | bid | what an account actually pays; **PRIMARY for the cost verdict** |

The frontier used mids and said so, noting it is *"a lower bound on the embedded rate and an
upper bound on the saving."* A **cost** question must be answered at executable prices, so
EXECUTABLE is primary here and the divergence between the two is itself reported.

### 2.6 Floors — n beside every estimate

**No aggregate is printed below n = 30.** This reuses V5's own floor deliberately rather than
inventing a second one. Per-name figures require n ≥ 30 **for that name**; names below it are
listed as below-floor, never silently pooled. Every printed statistic carries its n.

### 2.7 Controls

**GATING — the run aborts and no arm is scored if these fail:**

* **C1 · instrument sanity against the frontier.** On a comparable construction (MID prices,
  non-payers) the median `(r* − rf)` must land in **[0, +150] bps**. Outside that the parity
  solve is wrong and nothing downstream is interpretable. This is a sanity band, *not* a
  reproduction target — the populations differ (freeze's 186 names vs the frontier's 15).
* **C2 · spot fidelity.** Fewer than 5% of pairs may have `|K/S − 1| > 1`. A nonsense moneyness
  distribution is the split-adjustment signature and must stop the run rather than be averaged
  over.

**REPORTED — no verdict attaches:**

* **C3 · PV(D) and the frontier's own bias detector.** The frontier *dropped* dividend payers
  because omitting PV(D) biases `r*` downward by an amount growing with T. Here PV(D) is carried
  **explicitly**, so payers are **kept**, and payers/non-payers are reported separately. The
  frontier's DTE-bucket gradient is reproduced as the check that PV(D) is working: a residual
  gradient means it is not.
* **C4 · American exercise, uncorrected and stated.** Equity options are American, so parity is
  an inequality. The bias is **smallest exactly at this corner** (the matched put is deep OTM,
  where early exercise is worth little). Not corrected; declared.
* **C5 · O18's ρ = 0.6743.** Real trades print at ~67% of the quoted half-spread — but that was
  measured on **35-delta, ~60 DTE** contracts, so applying it to deep-ITM is an **extrapolation**.
  Totals are reported **both** at quoted spread (primary, conservative) and ρ-adjusted.
* **C6 · commissions** imported from `options_fill.COMMISSION_PER_CONTRACT`, never re-typed.
* **C7 · roll realism.** The financing benefit **requires rolling**: exercising a deep-ITM call
  means paying the strike in cash, which defeats the purpose. So a roll pays the full round trip
  each time, and that is why tenor drives this result. Stated as a modelling assumption.

### 2.8 Margin-rate assumptions, stated as the brief requires

All three reported side by side, each as a spread over contemporaneous rf:

| route | assumed rate | ≈ spread over rf (2025) |
|---|---|---|
| Robinhood Gold | 5.75% flat | rf + 145 bps |
| Robinhood standard | 11–12% | rf + 600–670 bps |
| IBKR Pro (tiered) | ~rf + 150 bps | rf + 150 bps |

These are **assumptions, not measurements** — they are published retail rates, not something this
repository owns — and every output says so.

### 2.9 Void conditions

1. **No trade recommendation** is issued in either direction, whatever the result.
2. **Nothing is adopted**; no file under `valuation/` changes.
3. Adding a **fourth price convention**, a **different DTE band**, or a **different delta band**
   after seeing any number voids the run.
4. Quoting an **Index-scope** claim from the 186-name universe voids the result (§2.4).
5. Reading the **mutable** `data/options` / `data/options_derived` store voids it — the freeze is
   the banked source.
6. Any use of `close` rather than `raw_close` for spot voids it (§2.3).

### 2.10 Trial charge

**Options domain, 3 trials**, charged whatever the outcome:

* **A1** — the embedded financing spread `(r* − rf)` at MID.
* **A2** — the same at EXECUTABLE prices.
* **A3** — the all-in annualised cost comparison against the three margin routes.

A3 is largely deterministic given A1/A2, so charging it separately **overstates** `N`, which is
the safe direction (M6's rule: understating `N` overstates significance).

---

## 3 · What neither item can see, stated in advance

* **V5** cannot see the entry half-spread at all — `paper_option_orders` stores no bid/ask/mid at
  submit. Routed in V5's own §7, not fixed here.
* **DEEPITM-FIN** measures a **cost**, not a return. It says nothing about whether owning these
  names is a good idea; P1 Stage 0 already closed the options-expression family on the return
  side, and this does not reopen it.
* Neither item bears on **capacity**. A sandbox has no book to move and the freeze has no fills.
