# PREREG DRAFT — O-SEED-1: long puts on accounting-flagged names
## The untested half of the book, gated by a pricing kill that runs before any arm

**DRAFT, Frontier Scout lane, 2026-08-20.** An executing lane that adopts it commits it ALONE
(markdown, zero `.py`), a strict ancestor of every measurement commit, counters re-read first.
**Trials: 2, options** (at this writing 305-reported → 307; hurdle 3.3824 → 3.3843 — the
reported count is the stricter bar and is the one to quote while the `MB16` dedup finding is
undecided). **Depends on instrument I-1 (the RND builder) — this register may not run until
I-1's validation suite is green.**

## 0. The load-bearing premise, verified before drafting

**The banked alert book is 100% long calls.** `optbt` calls `pick_contract(chain, und, day,
right="C")` at both entry sites, and `MB1`'s menu census reproduces it structurally (864 raw →
**432 calls** → the in-band menu). Every short-put result in the record (`A3`'s spreads,
`V6-OPT`'s CSPs) is the *other side*; `U3`'s overlay was index calls. **No register has ever
bought a single-name put.** The mechanism carrier: `MA28-CARD` measured names tripping ≥2 of
{Beneish M > −1.78, Altman Z < 1.81, top-decile external financing} crash (>50% quarterly fall)
at **3.0422× the base rate** (2.6597% vs 0.8743%), replicating 3.42×/2.93× by half, beyond the
max of 500 permutation draws in every window, **strengthening with size to 5.169× in megacaps**
— which is exactly where options coverage lives. A long put is the instrument whose payoff is
the event the flag predicts.

## 1. Mechanism, and the two graveyard walls it must clear

**Not `V6-OPT` re-skinned:** that register SOLD puts on *healthy* dips and died because
delta-targeting made the strike spend the risk difference (assignment 25.30% vs 25.73% — the
market repriced via IV, and delta chased it). This register (a) takes the **long** side, and
(b) **bans delta-targeting structurally** — strikes are MONEYNESS-targeted (§3), the exact
re-opening `V6-OPT`'s own close-out named, applied on the side its mechanism favours.
**Not `O9`/short-vol:** long vega, opposite family. **Not `U3`:** single-name puts on flagged
names, not an index overlay on the whole book; `U3`'s "leverage, not insurance" verdict was
about payoff shape at the book level and its register never saw a name-level flag.
**Not `R2`'s entry:** entries here are quarterly panel dates + a fundamental flag — no alert,
no options-flow signal; `O17C4`'s within-stratum standard is inherited via controls, not
re-litigated.

**The headwind, stated as the prior's denominator:** buying options pays the variance risk
premium; `D9` puts retail options costs at 4.7–12.6% of premium; `O7`-B1 measured this book's
market OVERpricing event moves (implied 5.45% vs realized 4.78%). Long-put books bleed by
default. The only reason this register exists is that the flag's 3.04× crash discrimination is
measured, replicated, and (per the kill below) possibly not priced.

## 2. Stage 0 — the pricing kill (pre-outcome; descriptive on INPUTS; fires before any arm)

Built on **I-1**: Breeden–Litzenberger risk-neutral densities from the **frozen** chains
(`freeze_options_2026-08-17` / `freeze_rawpull_2026-08-18` only; the mutable store is `O16`'s
defect and may not serve a register).

* **K1 — instrument validation (I-1's own suite, re-asserted here):** per chain-date, RND
  integrates to 1 ± 0.02; CDF monotone; forward from put–call parity reproduces the as-traded
  spot within its own quoted-spread band on ≥95% of used chains (`U1-SPLIT`: as-traded prices
  everywhere a strike is touched). Chains failing K1 are excluded and counted.
* **K2 — does the market already price the flag?** On every eligible entry (§3), compute
  RND-implied `Q(S_T ≤ 0.5·S_0)` — the risk-neutral analogue of `MA28`'s crash event — and
  compare **flagged vs unflagged medians as a ratio** `ρ_RND`. This is a statement about
  option PRICES at entry (inputs), not about outcomes. Pre-committed reading, fixed now:
  - `ρ_RND ≥ 3.04` (the physical ratio): the market prices the flag fully or more —
    **VOID before any arm runs**, the whole family closes, and the finding ships as a
    disclosure candidate ("the market already charges for these flags"), which is itself
    `MB39`-class product material.
  - `ρ_RND ≤ 1.5`: the flag is materially underpriced — proceed, prior upgraded (§6).
  - otherwise: proceed at the base prior.
* **K3 — the EV bound, from descriptive inputs only:** median ask premium (as % of strike) of
  the §3 target put on flagged entries, against the bound
  `premium > ρ_phys-implied payoff ceiling` — i.e., if the put's cost per quarter exceeds the
  physical crash rate × the maximum payoff the crash definition can deliver at that strike,
  the arm cannot be positive-EV even at the measured crash rate: **VOID**. All three kills run
  and are read in a pass that completes before the arm code exists (`O10`'s process rule).

## 3. The arm (stage 1 — the 2 booked trials)

* **Entries:** every panel rebalance date with chain coverage (expected ≈40 of 69, the
  `V6-OPT` window; effective coverage printed per RUN_RULES A-10), every name with ≥2 of 3
  flags at `MA28`'s published thresholds (never re-fit). `pre_panel_history` filtered
  wherever a 2016–18 chain is touched (the harvest handoff's precondition).
* **Contract:** the listed put with strike nearest **0.70× as-traded spot** (moneyness-
  targeted; **any delta-targeted selection voids the register** — pinned by AST) and expiry
  nearest **91 DTE at or beyond the next quarter-end**, bought at the **ask**, held to
  expiry, settled on the as-traded spot. No early exit and no exit rule — `S23`/`O1` closed
  exit tuning and this register does not reopen it.
* **Primary statistic:** mean per-trade return on premium, flagged arm. **The discriminator
  decides** (`V6-OPT`'s C-A pattern): the identical structure on **unflagged** names, matched
  on entry date; CONFIRMED requires the flagged arm to beat the unflagged arm in **both
  halves** AND beat matched random-entry puts (5 seeds, name-year paired sign test) AND
  survive `O11`'s cap-10/$50k survivability leg with terminal equity above start. Costs at
  quoted spread primary; ρ-adjusted (0.6743) beside it, declared an extrapolation from
  35-delta/60-DTE calls.
* **Floors:** a half with <30 settled flagged legs is UNDERPOWERED, never null (`O26`/`V6-B`
  M2). MDE line printed from `power_gate.state()` on the realized leg count at 50% and 80%
  power before the verdict is read (RUN_RULES A-11); the register expects the discriminator
  spread to need ≥ high-single-digit pp/trade at 80% power on ~hundreds of legs — if the
  realized MDE exceeds 25pp/trade, the arm is UNPOWERED-BY-CONSTRUCTION and stops.

## 4. Controls

C1: flag counts reproduce `MA28-CARD`'s banked flag rates exactly on shared dates (abort
otherwise). C2: zero point-in-time violations on flag inputs (imported test). C3: entries
where the put's quote fails two-sided usability are excluded and counted (`MA31`'s warning).
C4: the unflagged arm's name-count and cap-structure summary must overlap the flagged arm's
(composition check, `MB1`'s menu-depth convention). C5: no chain read outside the freezes,
pinned by test.

## 5. Void conditions

1. Running any arm before I-1's suite and K1–K3 are green and banked.
2. Delta-targeted strikes anywhere (AST-pinned).
3. Reading `realized` crash outcomes in stage 0 (stage 0 is prices only).
4. Early-exit rules, take-profits, or stop-losses in any form.
5. Quoting the mean without the O26-floor and the MDE line beside it.
6. Any re-fit of the three thresholds — published values only (`MA28`'s rule).

## 6. Prior and expectations, written before anything runs

Base prior: **~10%** CONFIRMED (the VRP headwind against a real, replicated, size-favoured
flag); upgraded to ~20% if K2 returns ≤1.5, and 0 (void) if K2 ≥ 3.04. Expectations to score:
(1) K1 passes on ≥95% of chains — 75/25. (2) K2 lands in the middle band — 55/45 (the market
partially prices accounting distress; Beneish/Altman are public). (3) If the arm runs, the
flagged−unflagged spread is positive full-sample — 60/40 — but fails a half — 65/35.
(4) The survivability leg (`O11` cap-10) is the binding failure if any — 60/40.
(5) At least one number contradicts this list — 60/40.

## 7. Verdict grammar and what this register does NOT do

CONFIRMED / REFUTED / CANNOT-TELL(-UNDERPOWERED) / VOID(K2/K3), all reachable. It does not
test market timing, does not touch the alert book's entry signal (`R2` stands), does not
license a live book (`O11` binds; any live wiring is a separate product decision), makes no
short-vol claim, and its stage-0 finding — priced or unpriced — ships as a record fact either
way, which is why the kill is worth the build even if it kills the star.
