# PREREG — F-21b — a stress gate for put selling, frozen now and judged forward

**COMMITTED ALONE, MARKDOWN ONLY, ZERO `.py`.** Accepted from the Frontier Scout's draft
`PREREG_DRAFT_f21b_stress_gate.md` at `da616fc`, which is a strict ancestor of this file.

**AND THIS REGISTER PROMISES NO VERDICT, WHICH IS THE POINT OF COMMITTING IT.** §3's arithmetic
says the question **cannot reach statistical resolution in any horizon Don will wait for — about
17.5 years** — so a register claiming the gate will be confirmed would be claiming something the
arithmetic forbids. **What it delivers is a RULE FROZEN BEFORE THE FILLS EXIST and a REPORTING
OBLIGATION. What it reports is the gate's COST, and the decision at the end is Don's judgement on
that cost rather than a *p*-value.** `R1-VAR` governs: *"a Sharpe or volatility gain bought with
alpha is not worth having unless the Sharpe itself is bad."*

**TRIAL COST: 1 OPTIONS TRIAL, BOOKED NOW.** The draft prices Stage A at 1 options trial charged
*at F-21's first verdict read*. It is booked **now** instead, on `MA6`'s rule that overstating `N`
is the safe direction and on this project's standing practice of booking before any runner exists.
Nothing is measured here, so the charge is purely conservative; **a reader who thinks it should be
zero has the row to amend.**

**LEVEL 2 CLEAN.** It gates a cash-secured put book. No spread, no second broker.

---

## 0. WHY FORWARD IS THE ONLY ROUTE, AND THE CONTAMINATION I CANNOT REMOVE

**`SELL-PREMIUM-2`'s ONE CHECK READ IS SPENT, AND THE THING A GATE WOULD BE TUNED TO AVOID IS
INSIDE IT.** The corrected read (`HANDOFF_optionsbot.md` §87b; §87's figures are void):

| expiry year | mean return per trade |
|---|---|
| **2020** | **-2.7788%** (n 1,220, **33.52%** assigned) |
| 2021 | -0.3830% |
| 2022 | +0.5109% |
| 2023 | +0.5998% |
| 2024 | +0.3660% |
| 2025 | +0.7575% |
| 2026 | +1.1999% |

**THE WHOLE LOSS IS COVID**, and the full-sample **-0.4258%** at *t* **-0.725** against an
80%-power MDE of **2.4896** is not separable from zero — so the honest sentence is *"could not be
shown profitable"*, never *"loses money"*.

**SO THE OBVIOUS IDEA — STAND ASIDE IN A CRASH — IS EXACTLY THE IDEA THIS DATA CANNOT TEST.** The
only window containing a crash has been read, twice, and **options data begins in 2016**, so there
is no third window. A gate fitted on 2016-2026 and confirmed on 2016-2026 is circular.

**DECLARED RATHER THAN MANAGED: I KNOW 2020 HAPPENED.** Any crash-avoidance rule proposed by
someone who has seen the sample is contaminated. **The only defences available are structural and
both are used** — the rule has **zero free parameters** and comes from a **publication predating
the data**, and §5 makes computing what it would have done on 2016-2026 a **void condition**.
**Those are weaker than blindness, and they are what exists.**

---

## 1. THE RULE, FROZEN

On the entry session, compute SPY's **200-session simple moving average of the adjusted close**.
**The gate is ON (stand aside) when SPY's close is below it, and OFF otherwise.** Nothing else:
no confirmation period, no buffer, no second condition, no alternative lookback. **Each of those
would be a free parameter and this register has none.**

Source: **Faber (2007)**, *A Quantitative Approach to Tactical Asset Allocation*, J. Wealth Mgmt —
the 10-month / 200-day rule, published nine years before the first options row.
Series: `data/full2009/backtest/prices/SPY.csv`, already on disk, and SPY is priced every cycle
forward.

**THE ALTERNATIVE IS NAMED AND BLOCKED, AND THE REASON IS A MEASURED DATA ABSENCE RATHER THAN A
PREFERENCE.** **VIX / VIX3M >= 1.00** (Johnson 2017, *JFQA* 52(6)) is preferred **on mechanism** —
it is a volatility measure gating a volatility book, and it is contemporaneous where a trend proxy
lags by construction. It is blocked because **no VIX or VIX3M series exists anywhere in this
repository** (only `DVIXQ` and the ETN `VIXL` appear, in the events spine). **If that feed is ever
built, the two rules must be frozen TOGETHER**: choosing the VIX rule after seeing the SMA's
partition is choosing a rule on its outcome, and §5 voids it.

---

## 2. WHAT THE RECORD ALREADY SUGGESTS THE GATE WILL COST

Two already-published facts, neither of them a look at the gate: **SPY was below its 200-day
average for most of 2022**, a matter of public record; and §87b measures the book earning
**+0.5109%** in 2022 and **+0.5998%** in 2023.

> **A RULE THAT STANDS ASIDE IN 2020 PLAUSIBLY ALSO STANDS ASIDE THROUGH ONE OR TWO OF THE BOOK'S
> BEST YEARS. THE GATE'S VALUE IS THEREFORE NOT OBVIOUS**, which is why it must be measured rather
> than assumed — and it is the strongest argument available against this register.

**STATED PRECISELY, BECAUSE IT SITS CLOSE TO THE VOID CONDITION:** that paragraph combines SPY's
public price path with two published per-year returns. **It does NOT compute the gated book's
return, and §5 forbids doing so.** Noticing a tension between two published facts is analysis;
computing the gated series is the look.

---

## 3. THE POWER ARITHMETIC, WHICH IS WHY THIS IS NOT A TESTABLE CLAIM

The cheapest form is a **partition of F-21's own forward fills** into gate-on and gate-off, needing
no second book. Even that does not resolve:

* the gap to detect is roughly **3.3pp/trade** (2020's -2.7788% against the later years' +0.37% to
  +1.20%), which is large by this project's standards;
* at `SELL-PREMIUM-2`'s measured per-trade SD of **5.047pp** and the derived options hurdle, a
  two-group difference needs **about 84 fills in EACH arm**;
* gate-on sessions are a minority of calendar time, so **about 420 total fills** are needed to
  accumulate 84 gate-on ones;
* **F-21's declared rate is 2.0 fills/month**, so **about 17.5 years.**

**AND THAT IS THE CHEAP VERSION.** A separate gated twin would need its own `fills_needed` —
F-21's own derivation is **933 fills, about 38.9 years** — and a gated twin takes **fewer** fills
than F-21 by construction, so its horizon is **longer**.

**THE HURDLE IS DERIVED AT THE READ AND IS NOT QUOTED HERE AS A CONSTANT.** The draft's 3.3993094
was correct at options `N` = 323 and `N` only rises; `MA19`'s lesson is that a bar quoted from a
document rots, so the read re-derives it from `research_log.detail()`. The 17.5-year figure moves
with it and is an estimate, not a promise.

---

## 4. THE DESIGN, AND WHY IT NEEDS NO NEW BOOK

**THE RULE IS DEFINED ON A PUBLIC, RECONSTRUCTIBLE SERIES, SO NOTHING HAS TO BE RECORDED FORWARD.**
SPY's 200-day average on any past date is computable from the price series at any time, so the gate
state of every F-21 fill can be reconstructed **at the verdict read from the fill timestamp alone**.

> **A GATE ON A RECONSTRUCTIBLE PUBLIC SERIES NEEDS NO FORWARD RECORDING, NO NEW DECLARATION, NO
> RE-CERTIFICATION AND NO SECOND BOOK. What must exist before the fills is the FROZEN RULE, and
> that is what this committed register is.**

**STAGE A — freeze the rule, report the partition.** No new book, no new fills, no change to F-21.
Deliverables at the read, **all four required**:

1. the gate-off and gate-on mean per-trade return, **with `n` in each**;
2. the **share of F-21's fills** that were gate-on;
3. the **measured MDE of the difference**, beside it, so a thin partition cannot read as a result
   (`MB22`: the 80%-power figure is `(crit + 0.84) * se`);
4. **the cost leg — what the gate would have given up**, i.e. the gate-on fills' aggregate return,
   because `R1-VAR` makes that the number Don decides on.

**STAGE B — a true gated twin — IS DECLARED ONLY IF STAGE A's PARTITION DISCRIMINATES**, and is not
drafted here. **Stage A tests whether the gate SEPARATES; a twin tests whether a book that USES it
does better, including the opportunity cost of standing aside.** Different questions, and the
second is worth a book's horizon only if the first says yes.

**THE DEPENDENCY §4 OF THE DRAFT REQUIRES, VERIFIED HERE AND NEGATIVE SO FAR.** *"The register's
first act is to confirm F-21 is actually recording fills on its declared population"*, because a
partition of an empty book is `RULE_ARMED_NEVER_FIRES` wearing a finding's clothes. **Measured on
`data_export/fleet_records/` as of the 2026-10-04 backup: F-21 and F-22 have NO record stream at
all — not an empty one, none — and the only book with fills is `f3_bear_puts` at 72, every one
`fate=working` with no `broker_order_id`.** That backup **predates their arming** (§88), so this is
evidence that the partition is not yet readable and **not** evidence that the entry rule never
fires. **The read may not be taken until F-21's stream exists and carries fills**, and the first
deliverable above is `n`, so an empty partition reports itself.

---

## 5. VOID CONDITIONS

1. **Computing the gate's effect on 2016-2026 — the historical window — in any form.** That is the
   circularity this register exists to avoid and it is the one rule that makes the forward reading
   worth anything.
2. Adding any parameter to the rule: no buffer, no confirmation window, no second condition, no
   alternative lookback.
3. Switching to the VIX/VIX3M rule after seeing the SMA's partition (§1).
4. Reading a thin partition as a verdict without its MDE.
5. Reading an empty gate-on set as a pass. **It reports VACUOUS, never PASSING** (`O21-D2`'s `C5`,
   and `MB21`'s `C1`, where a control scored a perfect zero by comparing nothing).
6. Claiming the partition measures a gated book's return.

---

## 6. WHAT A SUCCESSOR MAY AND MAY NOT CONCLUDE

**IF THE PARTITION DISCRIMINATES**, that is evidence the gate **separates** — not that a gated book
earns more, because standing aside has an opportunity cost the partition does not measure.
**IF IT DOES NOT**, at the MDEs of §3 that is almost certainly a power statement rather than a
null, and it must be reported as **`CANNOT-TELL(horizon)`**, the fleet's own third verdict word.
**IF THE GATE-ON SET IS EMPTY** because no crash occurred, the report reads **VACUOUS**.

---

## 7. EXPECTATIONS

1. **Stage A ever reaches 84 gate-on fills: 15%**, on F-21's declared rate and a 17.5-year horizon.
   **This is the honest headline and it is why this is a reporting obligation rather than an arm.**
2. **The partition, if ever read, shows gate-on worse: 75/25.** §0's year table is one crash's worth
   of evidence that it would, and that is exactly the evidence that cannot confirm it.
3. **A gated book would beat the ungated one net of the opportunity cost: 40/60** — §2 is why this
   sits below a coin flip despite expectation 2.
4. **Don adopts the gate: 25%**, and it would be a judgement on the reported cost rather than on a
   statistic.

---

## 8. WHAT THIS DOES NOT SAY

It is **not** a finding that stress gating works. It does **not** re-open `SELL-PREMIUM-2`, whose
check read is spent and whose `NOT CONFIRMED` stands. It does **not** claim the 2020 loss was
avoidable — **`SELL-PREMIUM-2`'s own `K3` cleared at 3.4170 years against the 6.0 bar and the crash
then produced the worst year in the book**, which is this record's sharpest warning that crash
arithmetic is not crash survival, and a gate is a second attempt at the same problem by a different
route. And it proposes **no trade**: `O11` binds, and the forward book this rides on **cannot
accrue until the fleet is actually filling on Alpaca**.

**NOT DONE:** no rule applied, no partition computed, no historical series touched, no change to
F-21's declaration, and **Stage B is not drafted.**
