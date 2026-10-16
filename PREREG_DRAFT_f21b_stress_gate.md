# PREREG DRAFT — F-21b — a stress gate for put selling, frozen now and judged forward

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no fill is placed, no trial is booked.

**AND IT IS NOT THE KIND OF DRAFT THE OTHERS ARE.** §3's arithmetic says this question **cannot
reach statistical resolution in any horizon Don will wait for**, so a register promising a verdict
would be dishonest. **What this draft delivers is a rule frozen before the fills exist, plus a
reporting obligation — and the decision at the end is Don's judgement on a measured cost, not a
*p*-value.** `R1-VAR` is the governing precedent: *"a Sharpe or volatility gain bought with alpha
is not worth having unless the Sharpe itself is bad"* — so what must be measured is **the gate's
cost**, and only Don can price it.

**LEVEL 2 CLEAN.** It gates a cash-secured put book. No spread, no other broker.

---

## 0. WHY FORWARD IS THE ONLY ROUTE — AND IT IS NOT A PREFERENCE

**`SELL-PREMIUM-2`'s ONE CHECK READ IS SPENT, AND THE THING A GATE WOULD BE TUNED TO AVOID IS
INSIDE IT.** §87b, the corrected read (§87's figures are void and may not be quoted):

| expiry year | mean return per trade |
|---|---|
| **2020** | **−2.7788%** (n 1,220, **33.52%** assigned) |
| 2021 | −0.3830% |
| 2022 | +0.5109% |
| 2023 | +0.5998% |
| 2024 | +0.3660% |
| 2025 | +0.7575% |
| 2026 | +1.1999% |

> **THE WHOLE LOSS IS COVID. Clause (a) failed only because the early half contains it, and the
> full-sample −0.4258% at *t* −0.725 against an 80%-power MDE of 2.4896 is NOT SEPARABLE FROM
> ZERO.** The honest sentence `SELL-PREMIUM-2` wrote for itself is *"could not be shown
> profitable"*, never *"loses money"*.

**SO THE OBVIOUS IDEA — STAND ASIDE IN A CRASH — IS EXACTLY THE IDEA THAT CANNOT BE TESTED ON THIS
DATA**, because the only window containing a crash has been read, twice, and the second read is the
one that revealed the shape above. **A gate fitted on 2016–2026 and confirmed on 2016–2026 is
circular, and there is no third window: options data begins in 2016** (`DECISIONS.md` 2026-10-13,
three rungs *"because no options data exists before 2016"*).

**THE CONTAMINATION I CANNOT REMOVE, DECLARED RATHER THAN MANAGED: I KNOW 2020 HAPPENED.** Any
crash-avoidance rule I propose is chosen by someone who knows a crash is in the sample. **The only
defences available are structural and both are used:** the rule has **zero free parameters** and
comes from a **publication that predates the data**, and §6 makes computing what it would have done
on 2016–2026 a **void condition**. **Those are weaker than blindness and they are what exists.**

---

## 1. THE RULE — AND MECHANISM AND FEASIBILITY POINT AT DIFFERENT ANSWERS

**TWO CANDIDATES, both published, both with zero free parameters:**

| | **SPY below its 200-day SMA** | **VIX / VIX3M ≥ 1.00** |
|---|---|---|
| source | **Faber (2007)**, *A Quantitative Approach to Tactical Asset Allocation*, J. Wealth Mgmt — the 10-month / 200-day rule | **Johnson (2017)**, *Risk Premia and the VIX Term Structure*, JFQA 52(6) — the term-structure slope prices VIX futures returns |
| free parameters | **none** — the average is the threshold | **none** — 1.00 is the contango/backwardation boundary |
| mechanism | a **trend proxy** for the vol regime; **lags by construction** | a **volatility** measure gating a **volatility** book; **contemporaneous** |
| data | **`data/full2009/backtest/prices/SPY.csv`, already on disk, 7,234 rows from 1997-12-31**; and SPY is priced every cycle forward | **NOT ON DISK. Measured: no VIX or VIX3M series exists anywhere in this repo** — only `DVIXQ` and `VIXL` (an ETN) appear in the events spine |

> **MECHANISM FAVOURS THE VIX TERM STRUCTURE AND FEASIBILITY DECIDES FOR THE 200-DAY SMA, SO THE
> SMA IS THE PRIMARY AND THE REASON IS A MEASURED DATA ABSENCE RATHER THAN A PREFERENCE.** The VIX
> rule needs a daily feed this project does not have and would have to build and schedule — and
> Don's own constraint is *"as long as it isn't super expensive"*. **The VIX/VIX3M rule is declared
> here as the alternative preferred on mechanism and BLOCKED on a data dependency**, named so a
> successor can take it up if that feed is ever built. Choosing it later would then be choosing a
> rule after seeing the SMA's result, so **if both are ever wanted they must be frozen together.**

**THE RULE, FROZEN:** on the entry session, compute SPY's **200-session simple moving average** of
the adjusted close. **The gate is ON (stand aside) when SPY's close is below it; OFF otherwise.**
Nothing else — no confirmation period, no buffer, no second condition. **Every one of those would
be a free parameter and this draft has none.**

---

## 2. WHAT THE RECORD ALREADY SAYS THE GATE WILL COST — AND IT IS NOT FLATTERING

**THE GATE HAS TWO JOBS AND THE RECORD SUGGESTS IT PASSES ONE AND FAILS THE OTHER.** Combining two
already-published facts, neither of which is a look at the gate:

* SPY was below its 200-day average for **most of 2022** — a matter of public record;
* and §87b measures the book earning **+0.5109%** in 2022 and **+0.5998%** in 2023.

> **SO A RULE THAT STANDS ASIDE IN 2020 ALSO PLAUSIBLY STANDS ASIDE THROUGH ONE OR TWO OF THE
> BOOK'S BEST YEARS. THE GATE'S VALUE IS THEREFORE NOT OBVIOUS, WHICH IS PRECISELY WHY IT MUST BE
> MEASURED RATHER THAN ASSUMED — AND IT IS THE STRONGEST ARGUMENT I CAN MAKE AGAINST MY OWN
> DRAFT.**

**STATED PRECISELY, BECAUSE IT SITS CLOSE TO THE VOID CONDITION: that paragraph combines SPY's
public price path with two published per-year returns. It does NOT compute the gated book's return,
and §6 forbids doing so.** The distinction is that noticing a tension between two published facts
is analysis; computing the gated series is the look.

---

## 3. THE POWER ARITHMETIC, WHICH IS WHY THIS IS NOT A TESTABLE CLAIM

The cheapest possible form of the question is a **partition of F-21's own forward fills** into
gate-on and gate-off, which needs no second book. Even that does not resolve:

* The gap to detect is roughly **3.3pp/trade** — 2020's **−2.7788%** against the later years'
  **+0.37% to +1.20%** — which is a large effect by this project's standards.
* At `SELL-PREMIUM-2`'s measured per-trade SD of **5.047pp** and the derived options hurdle
  (`N` = 323 ⇒ **3.3993094**), a two-group difference needs **≈ 84 fills in EACH arm.**
* Gate-on sessions are a minority of calendar time, so **≈ 420 total fills** are needed to
  accumulate 84 gate-on ones.
* **F-21's declared rate is 2.0 fills/month**, so **≈ 17.5 years.**

> **AND THAT IS THE CHEAP VERSION.** A separate gated twin (a true F-21b book) would need its own
> `fills_needed` — F-21's own derivation is **933 fills ≈ 38.9 years** at its declared minimum
> effect — and the gated twin takes **fewer** fills than F-21 by construction, so its horizon is
> **longer**.

**CONSEQUENTLY THE DELIVERABLE IS A FROZEN RULE AND A REPORTING OBLIGATION, NOT AN ARM.** Any
register claiming this gate will be confirmed is claiming something the arithmetic forbids, and
`V6`/`S19`'s rule applies: **quote the MDE with the verdict or do not quote the verdict.**

---

## 4. THE DESIGN THAT COSTS ALMOST NOTHING — AND WHY IT NEEDS NO NEW BOOK

**THE RULE IS DEFINED ON A PUBLIC, RECONSTRUCTIBLE SERIES, SO NOTHING HAS TO BE RECORDED FORWARD.**
SPY's 200-day average on any past date is computable from the price series at any time, so the gate
state of every F-21 fill can be reconstructed **at the verdict read** from the fill timestamp alone.

> **THAT IS THE WHOLE TRICK AND IT IS WORTH STATING PLAINLY: A GATE ON A RECONSTRUCTIBLE PUBLIC
> SERIES NEEDS NO FORWARD RECORDING, NO NEW DECLARATION, NO RE-CERTIFICATION AND NO SECOND BOOK.
> What has to exist before the fills is the FROZEN RULE, and that is what a committed register
> is.**

**STAGE A — freeze the rule, report the partition. COST: 1 options trial at F-21's first verdict
read** (priced at 1 rather than 0 because it adds a statistic to an existing book's read, and
`MA6`'s rule is that overstating `N` is the safe direction; a reader who thinks it should be 0 has
the row to amend). **No new book, no new fills, no change to F-21, no re-certification.**
Deliverables at the read, all required:
1. the gate-off and gate-on mean per-trade return, with **n in each**;
2. the **share of F-21's fills** that were gate-on;
3. the **measured MDE of the difference**, beside it, so nobody reads a thin partition as a result
   (`MB22`: the 80%-power figure is `(crit + 0.84)·se`);
4. **the cost leg: what the gate would have given up**, i.e. the gate-on fills' aggregate return —
   because `R1-VAR` makes that the number Don decides on.

**STAGE B — a true F-21b gated twin — IS DECLARED ONLY IF STAGE A's PARTITION DISCRIMINATES**, and
is not drafted here. **The distinction is real and worth keeping: Stage A tests whether the gate
SEPARATES; a twin tests whether a book that USES it does better, including the opportunity cost of
standing aside.** Those are different questions and the second is only worth a book's horizon if
the first says yes.

**ONE DEPENDENCY THAT MUST BE VERIFIED BEFORE ANY OF THIS IS WORTH WRITING.** §85 measured that
**F-21's declared entry population was recorded nowhere** — *"`dip_rejects` is the COMPLEMENT of
F-21's entry population … F-21 enters on the names the screen KEPT; the only dip series records the
ones it THREW OUT"* — and that the dip screen runs **weekly, not daily**, so the 6-against-24 day
counts were a cadence mismatch rather than a fault. §88 reports both books armed. **The register's
first act is to confirm F-21 is actually recording fills on its declared population**, because a
partition of an empty book is `RULE_ARMED_NEVER_FIRES` wearing a finding's clothes — the harness's
own phrase is *"indistinguishable in the records from a quiet market."*

---

## 5. WHAT A SUCCESSOR MAY AND MAY NOT CONCLUDE

**IF THE PARTITION DISCRIMINATES**, that is evidence the gate separates — **not** that a gated book
earns more, because standing aside has an opportunity cost the partition does not measure.
**IF IT DOES NOT**, at the MDEs of §3 that is almost certainly a power statement and not a null, and
it must be reported as `CANNOT-TELL(horizon)` — the fleet's own third verdict word.
**AND IF THE GATE-ON SET IS EMPTY** because no crash occurred, the report reads **VACUOUS, never
PASSING** (`O21-D2`'s `C5`, and `MB21`'s `C1` where a control scored a perfect zero by comparing
nothing).

---

## 6. VOID CONDITIONS, EXPECTATIONS, AND WHAT THIS DOES NOT SAY

**VOID CONDITIONS.** (1) **Computing the gate's effect on 2016–2026 — the historical window — in
any form.** That is the circularity this draft exists to avoid and it is the one rule that makes
the forward reading worth anything. (2) Adding any parameter to the rule: no buffer, no
confirmation window, no second condition, no alternative lookback. (3) Switching to the VIX/VIX3M
rule after seeing the SMA's partition (§1). (4) Reading a thin partition as a verdict without its
MDE. (5) Reading an empty gate-on set as a pass. (6) Claiming the partition measures a gated
book's return.

**EXPECTATIONS.**
1. **Stage A ever reaches 84 gate-on fills: 15%**, on F-21's declared rate and a 17.5-year
   horizon. **This is the honest headline and it is why the draft is framed as a reporting
   obligation.**
2. **The partition, if ever read, shows gate-on worse: 75/25** — §0's year table is one crash's
   worth of evidence that it would, and that is exactly the evidence that cannot confirm it.
3. **A gated book would beat the ungated one net of the opportunity cost: 40/60** — §2 is why I
   price this below a coin flip despite expectation 2.
4. **Don adopts the gate: 25%**, and it would be a judgement on the reported cost rather than on a
   statistic.

**WHAT THIS DOES NOT SAY.** It is **not** a finding that stress gating works. It does **not**
re-open `SELL-PREMIUM-2`, whose check read is spent and whose `NOT CONFIRMED` stands. It does
**not** claim the 2020 loss was avoidable — **`SELL-PREMIUM-2`'s own `K3` cleared at 3.4170 years
against the 6.0 bar and the crash then produced the worst year in the book**, which is the record's
sharpest warning that crash arithmetic is not crash survival, and a gate is a second attempt at the
same problem by a different route. And it proposes **no trade**: `O11` binds, and the forward book
this rides on **cannot accrue until the fleet is on Alpaca** (`DECISIONS.md` 2026-10-16, which puts
that first).

**NOT DONE:** no register committed, no rule applied, no partition computed, no trial booked, and
**F-21's own recording of its declared entry population is unverified here** (§4).
