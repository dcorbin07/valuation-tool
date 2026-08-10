# PRE-REGISTRATION — V1, shadow vintages (forward paired A/B of every adoption)

**Written 2026-08-10, session 16, and this is the whole point of the timing: NO VINTAGE PAIR
EXISTS.** Vintage 2 opened on 2026-08-10 under Amendment 1 and has no successor. There is
nothing to compare, so not one parameter below could have been chosen to make any comparison
come out a particular way — not even in principle, and not even accidentally.

Owner: pipeline builder, `valuation/edge/**`. Register: `VALQUO_EXTENSIONS.md` V1.
Machinery: `valuation/edge/shadow_vintage.py`. Report: `HANDOFF_edge_audit.md`.

**No parameter in this file may be revisited after this commit.** Same rule as the contract's
meter (§6), for the same reason.

---

## 1 · What this instrument is for, and the problem it exists to solve

Amendment 1 gave the project a vintage rule, and with it **Rule 6: a vintage change resets the
whole accrued clock and buys nothing statistically.** Ship a scoring change at month 30 and 30
months of forward evidence are spent for nothing. That is a correct rule and it is a brutal one:
taken alone it says the project may never improve the model again without paying five years.

The escape is not to weaken Rule 6. It is to measure the *change itself*, forward and paired.
When vintage N+1 opens, vintage N keeps being scored in shadow on the same dates by the same code
path with its parameters pinned. The comparison is then **within-day and paired**, so the market
risk that dominates a vs-SPY test cancels.

**How much that buys, computed before any pair exists** (same Robbins boundary, ρ = 3, α = 0.05
two-sided, the same AR(1) design-effect inflation of 1.4661):

| annualised TE between the two books | σ (pp/month) | detectable at 12m | 36m | **60m** |
|---|---|---|---|---|
| 2.0 pp/yr (near-identical books) | 0.6991 | 7.46 pp/yr | 4.26 | **3.34** |
| 4.0 pp/yr | 1.3981 | 14.93 | 8.51 | **6.67** |
| 6.0 pp/yr | 2.0972 | 22.39 | 12.77 | **10.01** |
| **11.40 pp/yr — the vs-SPY meter's own TE** | **3.9847** | 42.55 | 24.26 | **19.01** |

**The bottom row is the control, and it is exact.** Fed the tracking error the contract's meter
runs on, this machinery reproduces the contract's published σ of **3.9847** and its published
"~19 pp/yr to cross at 60 months" — because it is the same boundary function, imported rather
than re-implemented. If a future edit breaks that agreement, one of the two meters has drifted.

## 2 · The finding this register commits to IN ADVANCE, because it is not flattering

**The tension is structural and no design choice escapes it.** σ is small exactly when the two
books overlap heavily — that is, when the adoption changed almost nothing. An adoption large
enough to be worth shipping also moves the books apart and raises σ. There is no configuration
in which this instrument is powerful *and* the change under test is small.

So: **a shadow pair that has not crossed is the EXPECTED outcome, and it is NOT evidence that the
adoption was worthless.** Every quotation of a NULL verdict must carry the detectable difference
beside it, and `verdict()` puts that sentence in its own `why` field so it cannot be dropped in
transit.

It is still a four-fold improvement on the alternative (3.34 vs 19.01 pp/yr at 60 months for
similar books), and the alternative is not "a better test" — it is **no forward evidence about
adoptions at all, forever**. That is the comparison this is judged against.

## 3 · Construction, fixed

**The shadow book.** Same code path, parameters pinned — `shadow_vintage.PINNED` holds vintage 2's
snapshot as of this commit (`params_id 0060c5ef3dda`). A snapshot covers `PARAM_KEYS` only:
theme weights, `sector_neutral`, `residual_momentum`, `ev_point_in_time`, `large_cap_min`,
`top_decile`, `max_weight`, `weighting`, `top_n`. **Adding a key to `PARAM_KEYS` is itself a
construction change and needs its own register row** — it silently redefines what "the same
model" means.

**Re-derivation is forbidden.** The shadow must be scored from the pinned snapshot, never from
"what the config used to be" reconstructed from git or memory. The whole claim of a shadow is
that it is the old model; a reconstruction is a new model that resembles it.

**The observation.** One value per completed calendar month:

    d_i = (live vintage's excess return in month i) − (shadow vintage's excess return in month i)

in percentage points, both measured against the same benchmark over the same window, both charged
the same modelled costs. **Positive `d` means the adoption HELPED.** Months are chained by the
same `track_meter.monthly_excess` rules the contract already uses, including its month-end
staleness void — a month voided for one book is voided for the pair.

**σ.** Estimated **once**, at pair open, by scoring both parameter sets over the historical
backtest panel and taking the annualised standard deviation of the difference in their top-decile
returns; then `σ = TE/√12 × √1.466091`. The estimator is frozen here; the input is measured then.

**σ MAY NEVER BE REVISED DOWNWARD** — contract §6.5 binds identically. A later measurement
showing the books track more closely than first estimated is precisely the circumstance in which
lowering σ would manufacture a crossing.

**The boundary.** `track_meter.boundary`, imported. One boundary function in the project.

## 4 · The decision rule, fixed

Let `S = Σ d_i` over `n` complete months and `B(n) = σ√((n+ρ)·ln((n+ρ)/(ρα²)))`.

| verdict | condition |
|---|---|
| **NOT-COMPARABLE** | weight overlap < **0.20** at the latest rebalance. Checked FIRST — a paired difference between two books that share almost nothing does not measure the adoption, it measures two portfolios. |
| **INSUFFICIENT** | `n < 6` complete months. No verdict is available and none is implied. |
| **CONFIRMED-LIVE** | `S > B(n)` |
| **HARMED** | `S < −B(n)` |
| **NULL** | otherwise, reported with the detectable difference beside it |

**The rule is symmetric by construction.** CONFIRMED-LIVE and HARMED are reached by the same
arithmetic against the same boundary; there is no sign branch anywhere in `verdict()`. Pinned by
a test that flips the sign of an entire series and requires the verdict to flip with it and
nothing else to move.

**Anytime-valid, so it may be read at any time** without an alpha penalty — that is what the
Robbins construction buys and it is why continuous monitoring is legitimate here. Reported
monthly, alongside the contract meter.

**Horizon.** The pair's verdict horizon is the contract's **60 months**. A pair whose own vintage
closes before then closes with it: comparing a live book to a parameter set nothing has run for
years is not a live A/B.

**Divergence is reported per rebalance regardless of verdict** — names in each book, shared names,
and weight overlap — because a verdict computed on a pair that quietly drifted apart is the
failure mode this instrument is most exposed to.

## 5 · Scope — hard limits

**RESEARCH INSTRUMENTATION. The shadow never reaches any public surface, ever.** Not the site,
not Discord, not email, not `/api/track`. V1's brief says so and the project has already shipped
one false claim by letting a research object reach an outbound surface (`PT-OUTBOUND`: a Discord
recap quoted the sandbox engine's +0.18pp while the bound recorder read −2.85pp). This is fenced
by an AST test over the outbound modules **before** it has any numbers to leak, rather than after.

**It does not touch the contract.** A shadow verdict is not a vs-SPY verdict, cannot pass the
operational gate, and has no bearing on the meter in §6. It answers one question — *did this
adoption help, live?* — and nothing else.

**It does not license shipping changes.** Rule 6 is unchanged: an adoption still resets the
vintage clock and still costs the accrued window. This measures the price; it does not refund it.

## 6 · Trial accounting

**Zero.** A registered instrument that has produced no measurement searches nothing and selects
nothing — the same treatment as HACFLOOR, CHAINFREEZE and the meter itself. **Equity `N` stays
131**; charged to infra at `n = 1`. The **first shadow pair** is a trial and is charged when it
opens, not now.

## 7 · Expectations, written down to be scored

The project's standing rule is that its directional guesses keep being wrong, so they get written
down anyway:

- **The first pair's verdict at its 60-month horizon will be NULL: 80/20.** Adoptions that pass
  this project's held-out gates are small, and small is what this instrument cannot see.
- **The binding constraint will turn out to be weight overlap, not σ: 40/60.** Stated because
  it is the failure I would not otherwise be looking for.
- **σ measured at the first pair open will exceed 2.0 pp/yr TE: 65/35.**

## 8 · What would make this register a failure

Any of: σ revised downward after a pair opens; a verdict quoted without its detectable
difference; a shadow number appearing on any public surface; `PARAM_KEYS` widened without a
register row; or a NULL described as evidence that an adoption did not work.
