# PRE-REGISTRATION — O10, the passive-limit fill model

**Committed together with `PREREG_o18_spread_cost.md`, and ALONE, before any measurement code for
either item exists.** Ledger row `O10`, `src=auto`, *"no mention anywhere in the corpus"*.

The question: the options book charges `DEFAULT_AGGRESSION = 1.0` — buy the ask, sell the bid — at
both ends of every trade. That constant was pre-committed results-free and has never been checked
against what real orders actually pay. O14 has now banked tick flow with the prevailing NBBO on
essentially every alert-day, so for the first time the assumption is measurable.

---

## §0 SCOPE — THREE FACTS MEASURED BEFORE THIS REGISTER WAS WRITTEN, AND WHAT THEY RULE OUT

These were established by reading the cache and the book only. **No outcome quantity — no P&L, no
expectancy, no fill advantage — was computed before this register was committed.** Every number
below is a property of quotes, prints and file coverage.

**S0.1 — THE CACHE IS EXACTLY THE ALERT-DAYS AND NOTHING ELSE.** 3,884 cached symbol-days against
3,885 book alert-days. For the 3,870 split-clean banked entries: **the immediate next trading
session is cached for 0 of 3,870 (0.0%)**, and the **exit day is cached for 0 of 3,870 (0.0%)**.

**S0.2 — THEREFORE THE LIVE ORDER-WORKING QUESTION IS NOT ANSWERABLE, AND NO VERDICT WILL BE
ISSUED ABOUT IT.** `auto-scan.yml` runs the cycle after the close, so the live bot submits on the
alert day's close and its order works on **D+1** (this is recorded in `CLAUDE.md` as the
mechanism behind `PT-BUG12`). D+1 is not in this cache for a single banked entry. **Anyone who
reads this item as "we measured what the live bot's limit orders fill at" has misread it.**

**S0.3 — ONLY THE ENTRY LEG IS COVERABLE; THE ROUND TRIP CHARGES THE SPREAD TWICE.** With zero
exit-day coverage, any statement about round-trip cost is an extrapolation. Extrapolations will
be labelled as such and will never be the headline.

**Consequence for what this item IS.** O10 does **not** re-simulate the book and will **not**
report a re-banked P&L. It measures the **execution environment** of the exact contracts the book
traded, on the day it traded them, quote-relatively — a property of the tape, requiring no
decision time and therefore carrying no look-ahead. That environment is what a cost line should be
calibrated to. Whether the book's *timing* can capture it is a separate question this cache cannot
answer, and §5 fixes the routing accordingly.

---

## §1 DISCLOSED PRIOR KNOWLEDGE

Written down because it was seen before the register was fixed, and because a register that hides
what its author already knows is worthless.

| fact | measured on | value |
|---|---|---|
| alert-days with a tick file | all 3,870 book rows | 3,869; **one missing: `BUD` 2024-01-10** |
| book rows lost to that day | — | **exactly 1** → usable n = **3,869** |
| `entry_premium` vs tape's last prevailing **ask** | 250 random entries | median rel. error **0.01887** |
| `entry_premium` vs tape's last prevailing **mid** | 250 random entries | median rel. error **0.03264** |
| tape spread% at print times vs book EOD spread% | 250 random entries | **0.04066** vs **0.06250** |
| prints inside the NBBO / at ask / at bid | 12,355 prints, 120 entries | **0.539 / 0.227 / 0.212** |
| contracts with ≥10 prints on their alert-day | 250 random entries | **0.800** (≥30 prints: 0.516) |
| book median entry premium / entry spread% | full book | **$2.57** / **0.06667** |
| implied median half-spread | full book | **$8.57/contract = 3.33% of premium** |

The `entry_premium` reconciliation is the reason the tape can be joined to the book at all: it
sits far closer to the **ask** than to the mid, which is what `aggression = 1.0` says it should be.

**The condition-code population, measured on 12,355 prints across 120 entries:**

| group | codes | share | at-touch | inside NBBO |
|---|---|---|---|---|
| touch-seeking | 0, 18, 35, 95, 106 | 0.676 | 0.439 – 0.871 | 0.087 – 0.546 |
| package-like | 125, 130, 131 | 0.315 | **0.056 – 0.185** | **0.809 – 0.927** |

**The OPRA meaning of these codes is NOT documented anywhere in this repository and is NOT
asserted here.** The split above is behavioural, not semantic: one population seeks the touch, the
other almost never reaches it and prints overwhelmingly inside the quote, which is what a
package/multi-leg print does. That is enough to fix the primary set without claiming to know what
any code is called.

---

## §2 DEFINITIONS — FIXED HERE, NOT ADJUSTABLE AFTER THE RUN

**Unit of observation: the contract-day** — one banked entry's exact `(ticker, alert_ts, expiry,
strike, right)`. Statistics are computed per contract-day and then averaged **equally across
contract-days**, one vote per banked entry, matching how the book's own expectancy is computed.

**Eligible print.** A print on the traded contract, on the alert day, with `bid > 0`, `ask > 0`,
`ask >= bid`, `half > 0`, and `condition ∈ SINGLE_LEG_CODES = (0, 18, 35, 95, 106)`.

* `mid = (bid+ask)/2`, `half = (ask-bid)/2`, and the **signed aggression** `e = (price-mid)/half`,
  so `e=+1` is a print at the ask and `e=-1` at the bid.
* **The package-like codes are EXCLUDED from the primary and reported separately.** This is the
  conservative direction and that is why it is primary: crediting a single-leg resting order with
  fills against package liquidity would **overstate** fillability, i.e. flatter the result. The
  all-codes arm is a sensitivity and carries **no verdict**.

**MIN_PRINTS = 10** eligible prints for a contract-day to enter the primary. Coverage will be
reported, and the excluded set's spread/premium/liquidity profile characterised, because those
will be the illiquid contracts and that is a selection.

**The limit level `λ`.** A resting BUY limit is priced `L = mid + λ·half`, so `λ=+1` is the ask
(marketable — the incumbent), `λ=0` the mid, `λ=-1` the bid. This extends the shipped `aggression`
scale, which spans mid→ask only, downward into genuinely passive territory.

**GRID, FIXED, NO OTHERS:** `λ ∈ {+1.0, +0.5, 0.0, -0.5, -1.0}`, horizons
`H ∈ {5, 15, 30, 60 min, rest-of-session}`.

**The fill rule.** From each eligible print `i` as a reference moment `τ_i` with its prevailing
quote, set `L_i`. A fill occurs iff some eligible print `j` with `τ_j ∈ (τ_i, τ_i+H]` has
`price_j ≤ L_i`. **The fill price is `L_i`** — your own limit, with no price improvement credited,
again the conservative direction. Reference points whose horizon runs past the session close are
dropped, not silently truncated.

**The two components, and why the naive answer is wrong.** A marketable order fills at *every*
reference point; a passive order fills only on the subset `S(λ,H)`. Writing `Δ_i = mid_{i,H} -
mid_i` for the contract's own drift over the horizon:

```
NPA(λ,H) = ( E_S[mid_H - L] ) - ( E_all[mid_H - (mid + half)] )
         = (1-λ)·E_S[half]        <- gross saving, per filled contract
         + ( E_S[Δ] - E_all[Δ] )  <- adverse selection, negative when fills precede declines
```

**The second term is the whole point of the item.** A passive bid fills when sellers are
aggressive, which is not a random moment; "you save half the spread" is the answer that ignores
it. Both terms are reported separately and in pp of entry premium.

**Both halves.** Split on `alert_ts` at the book median, **2021-03-08**: early n=1,933, late
n=1,937.

**Intervals.** Month-block bootstrap (R3's standing clustering rule), 2,000 draws, never i.i.d.
over trades.

---

## §3 CONTROLS THAT RUN FIRST, AND CAN VOID THE ITEM

* **C1 — reconciliation.** Median relative error between `entry_premium` and the tape's last
  prevailing ask on the traded contract, full book. **If it exceeds 0.05 the item is VOID**, because
  the tape and the book would not be describing the same contract-day.
* **C2 — the condition split replicates.** The touch-seeking vs package-like separation of §1 must
  hold on the full book. If it does not, `SINGLE_LEG_CODES` is void and **only** the all-codes
  sensitivity is reported, with no verdict.
* **C3 — the marketable baseline is degenerate by construction.** At `λ=+1` the fill rate must be
  ~1.0 at every horizon. If it is not, the fill rule is misimplemented.
* **C4 — coverage.** Contract-days entering the primary, as a share of 3,869. Below 0.70 the
  verdict is marked RESTRICTED and the excluded set is characterised.
* **C5 — BUD 2024-01-10 is named and excluded**, one row, per O14's census.

---

## §4 THE VERDICT RULE — FIXED BEFORE ANY NUMBER EXISTS

**Primary cell: `λ = 0.0` (rest at the mid), `H = 30 min`.** One cell, chosen in advance. The rest
of the grid is reported as a **curve with no verdict** — picking the best cell after the fact is
the in-search → hold-out failure this project has already paid for once.

* **MATERIAL** iff, in **BOTH halves**: `NPA ≥ 1.00pp` of entry premium **AND** fill rate `≥ 0.50`.
* **PARTIAL** if `NPA` clears but the fill rate does not — reported, no policy recommendation,
  because an advantage you capture on a minority of intended entries is a different strategy.
* **NULL** otherwise. Ambiguous against the bar is a NULL (`RUN_RULES` A6).

**The 1.00pp bar** is ~30% of the maximum achievable saving (the full half-spread is 3.33pp of the
median premium), and is stated in pp of premium so it is directly comparable to the book's own
`+3.2702%/trade` expectancy.

**ROUTING, FIXED IN ADVANCE: a MATERIAL verdict changes NOTHING in this session.**
`DEFAULT_AGGRESSION` stays 1.0, no book is re-banked, no cost line is edited. It is written up and
**routed to Don as a policy change**, per the instruction that opened this work. Changing the fill
constant would re-price every options figure the project has ever published.

**AND THE MISREADING THAT MUST BE HEADED OFF: better fills DO NOT RESCUE R2.** The random-entry
control is filled by the identical rule, so a cheaper entry raises the alert book and its control
by the same amount and leaves the −5.0640pp gap where it is. This is arithmetic, not a prediction.

---

## §5 EXPECTATIONS — WRITTEN DOWN FIRST BECAUSE THEY KEEP BEING WRONG

| # | expectation | confidence |
|---|---|---|
| E1 | Effective half-spread is smaller than quoted half-spread | 80/20 (§1 already indicates it — disclosed) |
| E2 | `NPA` at the primary cell is MATERIAL (≥ 1.00pp) | 55/45 |
| E3 | Adverse selection eats ≥ 40% of the gross saving | 65/35 |
| E4 | Fill rate at the primary cell ≥ 0.50 | 60/40 |
| E5 | Fill rate rises monotonically in `λ` at every horizon | 85/15 |
| E6 | The package-like arm shows a HIGHER apparent fill rate than the primary | 75/25 |

---

## §6 TRIAL COST

**4 options trials** — the four non-incumbent `λ` levels `{+0.5, 0.0, -0.5, -1.0}` measured
against the bar. `λ=+1.0` is the shipped assumption, not a trial. Horizons, halves, controls and
the sensitivity arms are charged at zero: they search nothing.

Options `N` **248 → 252** by this item; `PREREG_o18_spread_cost.md` charges its own 6 on top.
**Equity `N` is untouched.** Understating `N` overstates significance, so where the charge is
arguable it is resolved upward.

---

## §7 VOID CONDITIONS

1. C1 fails (reconciliation > 0.05).
2. The fill rule fails C3.
3. Any change to `SINGLE_LEG_CODES`, `MIN_PRINTS`, the `λ` grid, the horizon grid, the primary
   cell, the 1.00pp bar or the 0.50 fill-rate bar after any outcome number has been read.
4. Reporting a cell other than the primary as the verdict.
