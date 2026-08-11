# HANDOFF — PARKED POSITIVES: an inventory and an evidence-shopping list

**Lane:** r1 · **Date:** 2026-08-10 · **Type:** read-only sweep. **No code was written, no test
was run, no number was re-measured.** Every figure below is quoted from the record as recorded,
with its source line, so any of it can be checked in one step.

**What this is for.** The project has a long list of things it REJECTED or called NULL. Some of
those were negative on their own numbers — the point estimate had the wrong sign, and re-opening
them would be re-litigating a settled loss. **Others were positive and were not adopted anyway**,
for reasons that are all defensible individually: the confidence interval crossed zero, the bar
was set higher than the effect, a stability arm killed a large margin, or the harm that sank it
was never in the pre-registration. This file separates the second group from the first and says,
for each, **exactly what evidence would move it** and **whether we already own that evidence.**

**What this is NOT.** No retests. No verdicts. No recommendation to adopt anything. Nothing here
changes a shipped number, and **no item below is quotable as a result** — a parked positive is
precisely a thing that has not cleared its bar. The sole output is a shopping list, so Don can
choose which confirmations to fund rather than having the choice made by whichever question a
future session happens to find interesting.

**Method.** Combed `VALQUO_LEDGER.md` (186 rows; 33 carry a REJECTED / NULL / INCONCLUSIVE /
DEFERRED / BLOCKED / IMMATERIAL status or verdict), the registers (`RESEARCH_LOG.md`,
`PREREG_*.md`, `VALQUO_EXTENSIONS.md`, `VALQUO_LIVE_AUDIT.md`, `PARAMETER_SEARCH.md`) and all **41
`HANDOFF_*.md` files that existed before this one**. Inclusion rule, applied consistently: **the recorded point estimate favours
the change, and the change was not made.** Items whose point estimate had the wrong sign are
listed in §11 as explicitly excluded, so the exclusions are checkable too.

---

## 1 · The inventory at a glance

Ordered by what I judge the strength of the recorded positive, not by cost.

| # | item | the positive, as recorded | why not adopted | evidence obtainable with what we own? |
|---|---|---|---|---|
| A | ~~**Exit: raise take-profit +100% → +150/200%**~~ **CLOSED — REJECTED 2026-08-11** | **+3.19pp / +3.82pp per trade**, FDR discoveries on **both** entry sets; ~~replicated in two independent runs~~ **CORRECTED: the two runs share 1,099 trades (28.3% / 35.2%), so they are two partially-overlapping trade sets, not two independent replications** | ~~pre-committed bar was **+10pp**~~ **the +10pp bar was mis-specified in shape and was replaced by a CALIBRATED one; the arm fails that too** | **DONE.** Don chose Option 2 on 2026-08-11; C1–C4 run. **Calibrated bar +5.0812pp (p95 of the arm's own family); `tp150` gains +3.1948pp at the 82nd percentile — fails C1 and ONLY C1** (C2/C3/C4 all pass). Not re-parked; see `PREREG_A_take_profit_bar.md` §§8–9 |
| B | **Sector-neutral ranking (LS-t arm)** | long-short t **3.396 → 3.896**, hit rate 64.5% → 66.4% | costs top-decile alpha **−1.58pp**, and the book is long-only | **YES, and it needs re-running anyway** — both rejections ran on the **void pre-B6 panel** (§3) |
| C | **Reinvestment Arm B** | passes **all six** pre-registered bounds | rejected on harm **not in the register** (18 negative EVs) | **YES — entirely.** 241-name pickle on disk, no new data |
| D | **O20 PIT liquidity filter** | book **+3.41% → +4.82%**/trade, coverage 99.2%, both halves positive | "a filter that improves a result needs a second panel" | **PARTLY.** Frozen chains are the *same* book; a second panel needs new mining |
| E | **X3: the composite's margin over its best single signal** | **+4.51%/yr** | CI95 **[−0.14%, +9.12%]** includes zero | **PARTLY** — JKP can test the theme-count question, not this panel's margin |
| F | **X4: margin over buyable factor ETFs** | **+9.21pp/yr** vs the 4-factor blend | t **1.10**; first half **−6.40%** | **NO on this window.** Needs elapsed time or new instruments |
| G | **LOO: dropping `quality`** | **+1.06% / +1.30%** (mean **+1.18%/yr**), the **most stable** of seven arms | never *selected* — the rule takes the maximum | **PARTLY** — needs a **third** dataset by the record's own rule |
| H | **V2G: the three dead live themes** | live book is **−1.31pp** vs deployed, i.e. reviving them is worth up to that | not separable from zero at **55% power** | **NO as measurement; YES as engineering** (free EDGAR sources exist) |
| I | **O8: SPY index VRP** | excess Sharpe **+0.14** | bar was **0.50** | **YES** — existing backtest, but see §9 |
| J | **`tp100_only` on RANDOM entries** | **+17.86pp**, sign test z **+10.55**, stable across all 5 seeds | fails the same test on the **alert** book (z −5.76) | **YES — already on the freeze** |

**Two of these ten (B and C) need no new data at all.** One (A) needs no new data and no new
measurement — only a decision about whether its bar was right. That is the cheap end of the list
and it is where I would look first.

---

## 2 · A — the exit take-profit raise (**the strongest member, and the cheapest**)

> **CLOSED — REJECTED, 2026-08-11. Everything below is the record of the case as it stood; the
> verdict is in `PREREG_A_take_profit_bar.md` §§8–9 and nothing here was acted on.** Don chose
> Option 2 of that memo (calibrate the bar, then decide). The calibrated bar — the p95 of 100
> jittered draws from the arm's own family, fixed and committed at `e8e5505` before the arm was
> scored — is **+5.0812pp**. `tp150` gains **+3.1948pp**, the **82nd percentile** of its own
> family, and **fails C1 and only C1**: it passes C2 (winsorised +2.4511pp, so not tail-driven),
> C3 (+2.5969pp on the five pooled random seeds) and C4 (FDR discovery, both halves, both sets,
> PBO 0.00). **This is not a finding that raising the target does nothing** — it is a finding
> that the arm is not distinguished within a family where 53 of 100 arbitrary jitters also beat
> the shipped rule. **Two claims in this section are corrected by that work and are struck
> below: the "two independent runs" (they share 1,099 trades) and the framing of +10pp as merely
> the wrong *level* (it was the wrong *shape*).** Item A is closed, not re-parked. The paper book
> keeps +100%/−50%/half-DTE.

**Recorded numbers.** ~~Two independent runs~~ **two partially-overlapping runs (1,099 shared
trades — 35.2% of the first, 28.3% of the second)**, a week apart, on different collection
methods, agree:

| run | source | the effect |
|---|---|---|
| deep-research thread #1, 2026-08-03 (278 names, 3,119 signal + 5,986 random entries) | `HANDOFF_deep_exits.md:10-27` | raising TP from +100% to **+150–200%** is worth **+2.1 to +3.3 pp per trade** — *"a ~69% relative lift on a +4.71% book"* — *"better per trade, better per day of capital committed, better on signal entries and on random entries, positive in both held-out halves, and wins a majority of the name-year cells it changes at FDR 10%"* |
| O1 exit sweep, 2026-08-08 (3,885 alert trades + **29,785** control trades, 5 seeds, entirely off the chain freeze) | `VALQUO_LEDGER.md` row `O1` | *"tp150/tp200 are FDR discoveries on BOTH sets at **+3.19pp / +3.82pp**"* |

**Why it was not adopted.** The pre-committed gate was **+10pp per trade**. Both runs land around
+3pp. `HANDOFF_deep_exits.md:26-27` states it plainly: *"well short of the pre-committed +10pp bar,
so nothing is adopted."* That is the discipline working exactly as intended — the bar was fixed
before the numbers existed and was honoured after.

**What would change the answer. Not more data — and the run that produced the result already said
so, in writing, and routed the question to Don.** I framed this as my own observation on the first
pass and that was wrong: `HANDOFF_deep_exits.md:231-237` raises it directly, as the first of *"two
things the next session should settle"*:

> *"**Is the +10pp bar right for an exit tweak?** `MIN_EXPECTANCY_GAIN` was set in
> `options_backtest` for adopting a ***construction*** change. On a book earning +4.71%/trade,
> demanding +10pp demands a tripling. `tp200` delivers **+3.26pp, a ~69% relative lift**, on both
> entry sets, in both halves, with **DSR 99.8% and PBO 0.075**. I applied the bar as written and
> rejected it. Whether an *absolute* pp bar is the right instrument for a proportional improvement
> is a real question, and **it is the user's call, not mine to quietly change mid-thread.**"*

**So the bar's origin IS recorded** — it is `MIN_EXPECTANCY_GAIN`, and it was calibrated for a
different kind of decision (a construction change, not an exit parameter). That is the substance of
the question, and it has been sitting unanswered since 2026-08-03. **This item is not a research
gap; it is an open decision addressed to Don that no session has picked up.**

Precedent for taking it seriously: **X7 measured that all four of the project's research bars were
conventions, and three were set wrong** (`CLAUDE.md` — theme IC t 2.0 against a calibrated 2.71,
PBO <50% against a calibrated 19.7%, which sits *at* the noise median).

**A second, narrower question is parked in the same paragraph** (`:238-242`) and should be settled
with it: the pre-registered criterion X1(e) required **both** a mean gain **and** a cell-win
majority, and on a convex payoff *"the two criteria point in opposite directions almost by
construction"*. `tp150`/`tp200` satisfy both, so it is not unsatisfiable — but the conjunction
should be re-examined before another thread reuses it.

**The honest counter, which must travel with this item.** The effect is measured on a book whose
*entry* signal is dead — R2 established the alert loses to random entry by −6.65pp
(`CLAUDE.md`). Improving the exit of a book with no entry edge raises a negative number toward
zero; it does not create an edge. **The record already says this**: the effect *"replicates on
random entries with equal or larger size, whatever effect exists is a property of the exit, not
of the dead entry signal"* (`HANDOFF_deep_exits.md:26-28`). So the honest framing is *"a real,
small, replicated exit improvement on a book that should probably not be traded"* — which is
worth knowing precisely because the exit logic is shared with anything that replaces the entry.

**Obtainable:** the measurement is **done, twice**. Cost of resolving it is one pre-registration
arguing the bar, not a run. **This is the only item on the list where the missing input is a
judgement rather than data.**

---

## 3 · B — sector-neutral's long-short gain (**and a finding the sweep produced**)

**Recorded numbers** (`HANDOFF_sector_neutral.md:71-75`, deployed weights):

| metric | flat | sector-neutral | |
|---|---|---|---|
| long-short t | 3.396 | **3.896** | better |
| long-short hit rate | 64.5% | **66.4%** | better |
| long-short annualised | +17.16% | +15.25% | worse |
| **top-decile alpha** | **+11.82%** | +10.24% | **worse (−1.58pp)** |

**Why it was not adopted.** The reasoning is sound and I am not disputing it: *"it buys long-short
t-stat and sells top-decile alpha … **Valquo trades a long-only book**, so top-decile alpha is the
metric that pays"* (`:109-116`). Rejected in both held-out directions, twice independently
(P10, then this run).

**THE FINDING THIS SWEEP PRODUCED, AND IT IS THE MOST CONSEQUENTIAL THING IN THIS FILE.**
**Both sector-neutral rejections ran on the pre-B6 panel, which the project has since declared
void.** `HANDOFF_sector_neutral.md:58` records the universe as *"2,710 usable, 136,478 panel rows,
**110 rebalance dates**"*, dated **2026-08-02**. B6 landed **2026-08-04** and cut the panel to
**2,531 names / 69 dates**, because the first 41 dates had an **inverted universe** — every name
present at a 2001 cross-section was one that had already stopped trading.

That is not a quibble about staleness. `CLAUDE.md` records B6's measured cost to the headline:
**t −0.897, alpha −4.18pp, PBO +46.7pp** — *"B6 is essentially the whole drop"*. The
sector-neutral decision turned on a **−1.58pp** alpha difference measured inside a panel whose
alpha level moved by **−4.18pp** when the defect was removed. **Nothing here says the verdict was
wrong** — the arms were compared against each other on the same panel, which cancels a great deal.
But the trade-off it rests on has never been observed on the panel the project actually uses.

**What would change the answer.** Re-run both arms on the corrected 69-date panel. If the alpha
cost shrinks below the long-short gain's value, the trade-off inverts; if it holds, the rejection
is confirmed on live data and becomes much stronger than it is today.

**Obtainable: YES, entirely.** The panel is on disk (`data/backtest`, 937.8 MB), the wiring is
pinned by `tests/test_sector_neutral.py` so it cannot have gone inert, and sector coverage is
100%. This is a re-run, not a data project.

> ### CLOSED 2026-08-11 (session 20, `SECTOR-NEUTRAL-B6`) — **REJECTED, and the trade-off above
> no longer exists.** Pre-registered in `PREREG_sector_neutral_b6.md`, committed alone at
> `1bdb7e0`; re-run through the SAME `holdout_compare_panels` gate with the same already-committed
> margins, under both weightings, on one panel build whose two arms share the `metrics` list.
>
> **This paragraph's own prediction was right about the second branch and wrong about the first.**
> The alpha cost did not shrink below the long-short gain's value — *the long-short gain itself
> disappeared and reversed*. On the corrected panel sector-neutral is **worse on BOTH metrics**
> under both weightings (deployed: alpha **+7.17% → +6.09%**, Δ **−1.09pp**; long-short *t*
> **2.8361 → 2.3423**, Δ **−0.494**, against the void panel's **+0.500**), the gate fails in
> **both halves**, and the sector-neutral arm **drops below the calibrated long-short HAC floor**
> (2.1505 vs **2.2837**) while the shipped arm clears it at 2.6199.
>
> **So the rejection is no longer a judgement call.** It used to require preferring alpha to
> *t*-stat for a long-only book; it now requires nothing, because there is no gain to weigh
> against the cost. **The item is closed and may not be re-run as a re-run** — re-opening needs
> `S25` (a point-in-time sector map) or `S15` (sector-relative on the value theme alone), both
> still open and both untouched by this. Details in `HANDOFF_edge_audit.md` session 20.

**The narrower variant, never tested at all.** `HANDOFF_sector_neutral.md:167-172` nominates
**sector-relative on the VALUE theme alone** — *"value is where cross-sector distortion is most
defensible on theory (a 6% earnings yield means something different in utilities than in
software)"* — and notes *"everything needed is now on disk … a one-parameter experiment"*. It has
no ledger row and appears never to have been run. It is the cheapest untested idea I found.

**One thing this rejection does NOT touch**, recorded to prevent a future misreading: the sector
column is already used, and accepted, for the `max_sector_w` concentration cap. That is a risk
control, not a re-ranking (`:174-177`).

---

## 4 · C — reinvestment Arm B (**passed six bounds; the rejection is right and unregistered**)

**Recorded numbers** (`HANDOFF_live_data_bugs.md:1997-2005`, ledger `OOB3`). Arm B = persistent
reinvestment floor applied to explicit years **and** the terminal.

| bound | Arm B |
|---|---|
| H1 control bit-identical (116 names) | **HELD — 0 moved** |
| F1 flat-revenue within ±25% of net capex | HELD 8/8 |
| F2 names undercharged >5% of revenue ≤ 5 | HELD — 33 → **0** |
| F3 negative modelled reinvestment → 0 | HELD — **0** |
| F4 decisive-set terminal value ≤ −5% | HELD — **−67.4%** |
| H2 publish/withhold flips, 0 in control | HELD — 0 anywhere |
| H3 decisive-set median fair value falls | HELD — −10.5% |

**Why it was not adopted.** `:2023-2043`: *"Arm B passes ALL SIX pre-registered bounds and is
obviously unshippable … **the rejection rests on a criterion I did not pre-register**."* The harm:
**18 negative enterprise values, 16 negative terminal values, 14 DCFs pushed non-positive**. ORCL's
EV goes to **−884,065**. *"A negative enterprise value is not a conservative valuation, it is not a
valuation. My bounds asked whether the number moved in the right direction and never asked whether
it was still a number."*

**The rejection is correct.** This item is on the list not because Arm B should ship — it should
not — but because **a passed-six-bounds result sitting under an unregistered rejection is exactly
the state that decays into "we tested it and it worked" if nobody writes down why it didn't.**

### What a complete bound set would have been

The task asked for this explicitly. Reconstructed from the two failure modes the run exposed —
Arm A passing three year-one bounds while fixing nothing, and Arm B passing everything while
destroying the output. **Not pre-registered, not a verdict; a checklist for whoever re-opens it.**

**Group 1 — output validity (the missing group; every one of these is what Arm B failed).**
1. **Enterprise value stays positive** for ≥ 99% of names that had a positive EV before. *Arm B: 18 violations.*
2. **Terminal value stays positive** for every name whose pre-change TV was positive. *Arm B: 16.*
3. **DCF stays positive** for every name whose pre-change DCF was positive. *Arm B: 14.*
4. **No name's fair value moves UP** — a reinvestment *charge* that raises a valuation has
   double-counted somewhere. *Arm B: 9 moved up; Arm A: 4.* This one is diagnostic, not just a
   guard: `:2121` records the mechanism — `blend._usable` drops a non-positive lens and
   renormalises, so charging more reinvestment moved EQIX +121%, GM +92%, XEL +73% **up**.
5. **Bounded blast radius** — a pre-stated ceiling on names whose fair value changes at all
   (Arm A 49/241, Arm B 78/241). Without one, "it changed a lot" is unfalsifiable in both directions.

**Group 2 — the fix reaches where the defect lives (Arm A failed only this).**
6. **A terminal-value bound**, i.e. the existing F4. Keep it, and note *why*: `:2015-2021` records
   that three of the four original criteria were **year-one statistics**, and a fix that provably
   cannot touch the terminal passed all three. *"A success criterion that a known-inadequate
   candidate passes is not a success criterion."*
7. **Population-split bounds.** `:2044-2065` establishes that the 33-name decisive set is **two
   populations**: 14 genuine flat-revenue undercharges and 19 capex-boom names whose spend is
   growth capital already priced through the revenue path (ORCL's net capex is 68.8% of revenue
   while revenue grows 3.1×). **A complete bound set states its target on the 14 and requires the
   19 to be left alone** — a single pooled bound cannot distinguish a fix from a double-count.

**Group 3 — the controls that already worked. Keep both.**
8. Control group bit-identical (the gate *is* the control group — held perfectly for both arms).
9. Zero publish/withhold flips in the control.

**Obtainable: YES, entirely, and it needs no market data.** `:2050` records the run as *"measured
offline on the 241-name 2026-08-05 pickle, one process, deterministic"*. Every bound above is
computable from the same pickle. **The blocker is a pre-registration, not a dataset.**

**A live defect sits inside this item and is unfixed:** six names publish today with a
**non-positive DCF** (INTC −0.53 → $34.54, F −31.92 → $60.25, BA −24.97 → $94.27, SRE, CCI, IRM)
because the blend silently drops the bad lens and renormalises. *"Characterised and pinned, NOT
fixed"* (`:2119-2122`). It is not a parked positive and is listed here only because anyone
re-opening Arm B will meet it immediately.

---

## 5 · D — O20, the point-in-time liquidity filter

**Recorded numbers** (`HANDOFF_edge_audit.md:2347-2360`):

| slice | n | expectancy | PF |
|---|---|---|---|
| whole corrected book | 3,885 | +3.41% | 1.092 |
| **point-in-time LIQUID** | **3,359 (86.5%)** | **+4.82%** | **1.131** |
| point-in-time ILLIQUID | 495 (12.7%) | **−7.84%** | 0.800 |

Coverage **99.2%**; both held-out halves positive (**+6.56%** early, **+3.31%** late); the
mechanism is coherent (illiquid entries are where the spread is widest, on a long-premium book);
and it is **implementable**, since liquidity at the entry date is knowable at the entry date.

**Why it was not adopted into the headline.** Two reasons, both recorded, and the second is the
one that parks it:

1. *"O20 DOES NOT RESCUE THE SIGNAL"* — the random-entry control is screened by the same rule and
   benefits at least as much. On the liquid subset the real book loses to random entry **more**
   decisively (z −3.475, p 0.0005) than on the whole book. **The improvement is a universe effect,
   not a signal effect.**
2. *"the headline stays the whole book … because a filter that improves a result is exactly the
   kind that needs a second panel before it is believed"* (`:2392-2395`).

It **is** shipped, as `o20_point_in_time_liquidity`, a reported partition on every run — the
ledger's `ADOPTED` refers to that. **The parked thing is O20 as a live entry filter**, not as a
diagnostic. Keeping that distinction is the point of listing it.

**What would change the answer.** A second options panel — different names, or a different period,
or both — on which the liquid/illiquid split reproduces.

**Obtainable: PARTLY, and this is the item where owning the data does *not* help.** The chain
freeze on disk (`data/options_freeze/R2_CORRECTED_2026-08-08` and `R2_CONTROLS_2026-08-08`,
183.8 MB) is the *same* 3,885-trade book plus its 29,785 controls. Re-reading it answers nothing
new. Worse, there is a hard ceiling recorded at `:2380-2390`: the miner's liquidity screen was
applied to each name's **first cached year**, so *"the names that would have failed were never
mined, and no evaluation-time filter recovers data that is not on disk"* — **O20's own number is
an upper bound.** A genuine second panel needs **new ThetaData mining** (see §9 on cost).

---

## 6 · E and G — the two equity-panel positives that need a *third* dataset

### E — X3: does the seven-theme composite earn its complexity?

**Recorded** (`CLAUDE.md`; ledger `X3`): the full composite beats its best single signal
(`gp_on_capital`) by **+4.51%/yr, CI95 [−0.14%, +9.12%]** — *"INCLUDES ZERO, so by the
pre-registered rule this is a NULL."* A near miss is a null, and the record says so.

**But the record is equally clear the word "decoration" is wrong**, and both halves must travel
together: `gp_on_capital` alone posts long-short **t 0.413** against the composite's **2.836**,
and **only the full seven-theme arm clears X7's calibrated long-short bar of 2.14.**

**What would change the answer.** More independent cross-sections. The CI half-width is ~4.6pp on
69 dates; the point estimate would need roughly **4× the periods** to separate from zero at its
current magnitude — which this panel cannot supply, since 69 dates is the corrected maximum.

**Obtainable: PARTLY.** Not on Sharadar. The **JKP Global Factor Data** (`data/factors/
research_only/jkp`, 2 MB, 17 regions × 324 months, already on disk) can address the *general*
question — does a multi-theme composite beat its best constituent — on 324 monthly observations
instead of 69, in regions that are out-of-sample in vendor, country and construction. **Licence
constraint, and it is absolute: CC BY-NC 4.0, research only. It can validate the model; it can
never ship in the product** (`CLAUDE.md`). Only 5 of 7 themes map — `insider` and `institutional`
have no analogue — so it tests a 5-theme version of the question, not the shipped one.

### G — LOO: dropping `quality` is the most stable arm and was never claimed

**Recorded** (`HANDOFF_edge_audit.md:4257-4265`), Δalpha of *dropping* each theme:

| arm | early Δα | late Δα | mean | half-diff | sign |
|---|---|---|---|---|---|
| **quality** | **+1.06%** | **+1.30%** | **+1.18%** | **−0.12pp** | **same** |
| capital_discipline | +0.20% | +2.20% | +1.20% | −1.00pp | same |
| momentum | +3.68% | −1.30% | +1.19% | +2.49pp | FLIP |
| size | −2.64% | −3.46% | −3.05% | +0.41pp | same |

`quality` is the only arm that clears both MIN_HOLDOUT margins in **both** halves, and it has the
smallest half-difference of all seven (−0.12pp against σ(34 dates) = 1.26pp).

**Why it was not claimed** — and this is the most disciplined refusal in the record, quoted in
full because it is the reason the item is *parked* rather than *pending*:

> *"The `quality` observation was NOT promoted, and this is the most important omission …
> Acting on it — or switching to a stability-based selection rule — after seeing which rule would
> have worked is **selecting the rule on the results**. That is the same error as session 6's
> exploratory LOO, one level up. Session 8 pre-registers it or nobody quotes it."*
> (`HANDOFF_edge_audit.md:4117-4122`)

**Session 8 then declined to run it, and session 9 closed the question.** Not from neglect — from
measurement. Session 8 showed one panel gives a paired sign test with **n = 1**, whose smallest
achievable p-value is 0.50. Session 9 built a clustering gate and measured that 16 JKP countries
are worth **2–4 independent draws, not 16**: the calibrated critical count is **17 of 16**, so
*"the rejection region is empty; the design's power at α 5% is zero"*, and the pre-registered
12/16 bar carries a **true α of 28.7%, not 3.84%**. `CLAUDE.md`: *"**Do not re-open it without new
data.**"*

**Obtainable: NO with what we own.** Both available datasets have been measured and both are
answered. This is the one item on the list where the record has already **priced the confirmation
and found it unaffordable** — which is itself the finding, and is why it belongs in an inventory
rather than a backlog.

---

## 7 · F — X4, the margin over what a user can actually buy

**Recorded** (`HANDOFF_free_analysis.md:402-440`). Blend = VTV / QUAL / MTUM / IWM, equal-weighted
on the panel's own 63-day grid, ETF closes already net of expense ratios, strategy charged its own
cost model:

```
strategy net +21.87%   blend +12.65%   SPY +14.11%
EXCESS vs blend +9.21%   halves  -6.40% / +27.08%   both positive = FALSE  -> NULL
```

**Why it was not adopted:** the committed bar was *"≥ +2.0pp annualised **AND** positive in both
halves"*. The margin is more than 4× the bar; the stability arm kills it. Supporting evidence all
points the same way — quarterly excess **t = 1.10**, hit rate **27/50 = 54%**, four losing years,
worst quarter **−40.1pp**. *"The margin is large and the stability arm kills it, which is exactly
what that arm is for."*

**Two facts recorded alongside it that must travel with any future quote:** the cheap factor blend
**lost to plain SPY** over its own lifetime (+12.65% vs +14.11%), so beating the blend is a weaker
claim than it sounds; and the secondary long-history 2-factor blend (IWD + IWM, 2000→2026)
**passes** at +15.87pp with both halves positive — *"this passes, and it is the weaker test, so it
does not rescue the primary"*, and its window includes the pre-2006 era where X6 found `size` had a
premium that has since broken.

**What would change the answer:** first-half performance that isn't −6.40%, i.e. **elapsed time**,
or a differently-matched instrument set.

**Obtainable: NO.** The 2014-2026 window is fixed and its first half is history. The forward track
is the only instrument that accrues new evidence on this question, and §8 is why that is slow.
**Note the window is B6-safe** — X4's primary starts 2014, after the 41 inverted-universe dates —
so unlike §3 this result does not need re-running for that reason.

---

## 8 · H — V2G, the three dead live themes

**Recorded** (`HANDOFF_edge_audit.md:6499-6520`, ledger `V2G`): the live product scores a
**four-theme** book — `insider` is constant and `capital_discipline` and `institutional` are
absent on 100% of live rows, i.e. **42.9% of the composite weight is inert**.

| | A7 deployed | B4 live book | Δ |
|---|---|---|---|
| top-decile alpha | +7.17% | **+5.86%** | **−1.31pp** |
| long-short HAC t | 2.6199 | **1.8811** | |

**Verdict IMMATERIAL** against a pre-registered −1.95pp bar (paired HAC t −1.4040 over 69 paired
dates). **The positive is the mirror image: building live sources for the dead themes is worth up
to +1.31pp/yr.**

**Why it is parked, and the caveat that must travel with it** — the record states it itself:
*"the power to detect a **true** 1.95pp gap is only **55.0%** … IMMATERIAL here means the cost
could not be separated from zero at roughly a coin flip's power against its own bar — **not that
the cost was shown to be small**."*

**The second finding is the one that actually matters** and is not a parked positive at all: the
live four-theme book **fails the calibrated long-short floor** (HAC t 1.8811 against X7's 2.2837).
That is a live-product fact, not a research option.

**Obtainable: NO as a measurement, YES as engineering.** No amount of re-analysis raises 55%
power on 69 dates. But per `[[live-themes-have-free-edgar-sources]]`, all three themes have free
EDGAR sources (13F, issuance, Form 4) reachable without a licence — the hard part is the CUSIP
join. **So the route here is to build the sources and let the live book improve, not to fund a
confirmation.** Cost is engineering time, not data spend.

---

## 9 · I and J — the two options items where the freeze already holds the answer

**I — O8, index VRP.** SPY put credit spreads: **excess Sharpe +0.14 against a 0.50 bar →
INCONCLUSIVE**; QQQ and IWM outright REJECTED (ledger `O8`). The positive is small and one of
three arms. **What would change it:** a pre-registered argument for a Sharpe bar below 0.50, or
more index history. **Obtainable:** the backtest exists. Note `D5` (ORATS, $99–$399/mo) is
recorded **DEFERRED — "DON'T BUY YET"** with the explicit gate *"O2/O6 and neither has returned
anything"*; O8's +0.14 does not change that gate.

**J — `tp100_only` on random entries.** Ledger `O1`: the one policy that clears the +10pp bar
(**+10.78pp signal / +17.86pp random**) **fails** the paired name-year sign test on the alert book
(z −5.76, wins 41.7% of decided cells, median cell −5.79pp) *"because it turns 1.39% of trades
into 46.87% total losses while letting the winners run"* — **while genuinely winning on random
entries** (64.5% of cells, z **+10.55**, stable across all five seeds).

That split is the informative part and is a cleaner statement of §2's caveat: **the exit rule's
value depends on which entries it is applied to.** A future entry signal that is not the dead
scream-buy alert would meet a different answer here. **Obtainable: YES** — both books are on the
freeze and O1's harness re-scores the whole grid in minutes.

---

## 10 · The evidence-shopping list, priced by what it costs

**Free — no new data, no new measurement. Only a decision.**
* **A** — decide whether an **absolute** +10pp bar (`MIN_EXPECTANCY_GAIN`, calibrated for a
  *construction* change) is the right instrument for a **proportional** exit improvement. The
  measurement is done twice and agrees; the run that produced it **explicitly routed this to Don
  on 2026-08-03** and no session has picked it up. Settle X1(e)'s mean-gain-**and**-cell-majority
  conjunction at the same time. *This is the single cheapest item on the list, and it is the only
  one that is already addressed to Don rather than to a future agent.*

**Cheap — a re-run on data already on this disk.**
* **B** — sector-neutral, both arms, on the corrected 69-date panel. **Both existing rejections
  ran on the void pre-B6 panel.** (`data/backtest`, wiring pinned by tests.)
* **B′** — sector-relative on the **value theme alone**. Nominated as *"a one-parameter
  experiment"*, never run, no ledger row.
* **C** — reinvestment Arm B against the completed bound set in §4. Offline, deterministic,
  241-name pickle, no market data.
* **J** — re-read the `tp100_only` entry-set split off the frozen chains.

**Moderate — owned data, but a different dataset with a licence constraint.**
* **E** — the theme-count question on the JKP panel: 324 monthly observations vs 69, five of seven
  themes. **CC BY-NC 4.0, research only — validates, never ships.** And per session 9's clustering
  gate, **any "replicates in N countries" claim must pass that gate first**; 16 countries are worth
  2–4 independent draws.

**Expensive — needs data we do not own.**
* **D** — a genuine second options panel for O20. Needs new ThetaData mining; the freeze cannot
  answer it, and O20's own figure is an upper bound because the un-mined names are not recoverable.
* **I** — more index history for O8, gated behind `D5` (ORATS), which the record says do not buy.

**Not purchasable at any price — only time, or engineering.**
* **F** — X4's first half is history. Only the forward track accrues new evidence, and
  `PAPER_TRACK_CONTRACT.md` puts the verdict at **2031-08-10** with **13.3% power at 60 months**.
* **G** — the LOO `quality` arm. Both owned datasets are measured and answered; the record's own
  instruction is *"do not re-open it without new data."*
* **H** — the three dead live themes: build the free EDGAR sources. Engineering, not data spend.

---

## 11 · Explicitly EXCLUDED, so the exclusions are checkable

These were rejected or null **with the point estimate against them**, and re-opening them is
re-litigating a loss, not funding a confirmation:

* **Lazy prices** (roadmap #28) — rank-IC **−0.0156**, long-short **−5.0%/yr**, deciles run
  backwards. *"The point estimate has the wrong sign as well as no significance."*
* **ML tree combiner** (MLCOMB) — worse in **both** directions (Δ −9.70pp, −5.48pp), and its
  deciles run **backwards** out of sample (monotonicity +0.382, +0.842).
* **Cross-section of option returns** (deep research #2) — nothing clears the gate; one
  characteristic sorts backwards from the literature.
* **VRP put-credit-spread arm** (A3) — fails five of seven pre-committed gate arms by a wide margin.
* **The options entry signal** (R2) — −6.65pp vs random entry, sign-test z −4.903.
* **U7, composite as an options veto** — all three pre-registered cells go the wrong way.
* **Sector-neutral under FLAT weights** — worse on both metrics; only the *deployed*-weights arm
  produced the LS-t gain in §3.

**Two judgement calls I want visible rather than buried:**

* **PEAD's `pead_car`** looks like a member — it *passes* the standalone bar at IC **t +2.215**.
  I excluded it, for two compounding reasons. Its incremental IC once residualised on the three
  momentum inputs is **t +0.020**; and the 2.0 bar it passed is one **X7 later calibrated to
  2.71**, against which +2.215 fails. **It was rejected on a stronger test than the one it
  passed** — the opposite shape from everything in §1.
* **O23** (exits vs the underlying) is a genuine near-miss NULL — pooled R² **0.53304**, point
  clears the 0.50 bar, CI95 lower bound [0.48564] does not. Excluded because it is a *descriptive*
  claim about attribution, not an adoption candidate: nothing ships differently either way.

---

## 12 · What I did NOT do, and the limits of this file

* **No retests, no verdicts, no numbers of my own.** Every figure is quoted from the record with
  its source line. If a quoted figure is itself wrong, this file inherits the error — and
  `[[claudemd-numbers-trustworthy-instructions-not]]` records that the research figures verify to
  the digit while the file:line cites rot within days, so **I re-resolved every line cite in this
  file against the current tree**, but did not re-derive any measurement.
* **I did not re-measure whether the pre-B6 problem in §3 changes the sector-neutral verdict.**
  I established the panel it ran on and stopped. Saying which way it moves would require the run
  this file exists to *propose*.
* **No trial cost.** No `RESEARCH_LOG.md` row is owed; equity **`N` stays 131**. A read-only sweep
  searches no hypothesis space, fits nothing and selects among no arms.
* **Coverage limit, stated plainly.** I combed 41 handoffs, 186 ledger rows and the registers. The
  ledger's own contract warns **43 rows are still `src=auto`** — leads, not facts — and every one
  of those is OPEN. **A parked positive recorded only inside an auto row would not have surfaced
  here.** This is an inventory of the *documented* record, not proof the record is complete.
* **One structural gap:** `VALQUO_LIVE_AUDIT.md` (the cold live audit, 5 behavioural items) was
  swept, but it is an audit of the *live product*, not of research verdicts, so it contributed no
  members. If a future live audit produces measured-but-unadopted results, they belong here too.

## Recommended next step

**Answer the free one first, because it is already addressed to you.** Item **A** needs no data and
no run. On 2026-08-03 the exit thread asked, in writing, whether a +10pp absolute bar is the right
instrument for a proportional improvement on a book earning +4.71%/trade — and explicitly declined
to renegotiate its own bar mid-thread, calling it *"the user's call"*. **That question has been
open for a week and this sweep is the first thing to surface it since.** The measurement exists
twice, from two independent collection methods, and agrees.

**Then item B**, because it is the only member where the *existing* rejection may rest on a panel
the project has declared void — and unlike everything else on this list, re-running it either
strengthens a shipped decision or overturns it, both of which are worth more than the run costs.
