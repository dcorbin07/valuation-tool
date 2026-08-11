# PREREG — Item A: the take-profit raise, and the bar it is measured against

**Lane:** options bot · **Date:** 2026-08-10 · **Type:** decision memo, written as a
pre-registration. **No policy is changed by this document and none may be changed on the strength
of it.** It ends at Don's choice, exactly as `PAPER_TRACK_CONTRACT.md` did.

`HANDOFF_parked_positives.md` item A is the only entry on that list whose missing input is a
judgement rather than data: raising the take-profit from +100% to +150/200% is measured, twice,
and was refused by a bar of **+10pp per trade**. What follows reconciles every look we have,
argues from the distribution what that bar should have been, and stops.

---

## 0. THE CAVEAT THAT ATTACHES TO ALL THREE OPTIONS BELOW, NOT JUST THE ONES DON DECLINES

**The options entry signal is dead.** R2: the alert book returns **+3.41%/trade against a
five-seed random-entry control's +10.06%**, gap −6.65pp, paired sign test **z −4.903**. The path
study reproduced both figures to the digit on 2026-08-10.

Everything below therefore concerns **how a paper book exits**, never whether the alert is worth
trading. Raising a take-profit on a book with no entry edge moves a negative number toward zero;
it does not create an edge. **No option in §5 — including "adopt" — makes this book tradeable,
and none may be quoted as evidence that it is.** The reason to care at all is that the exit logic
is shared with whatever eventually replaces the entry.

---

## 1. The three looks, reconciled — and they are not three independent replications

| # | run | trade set | baseline | `tp150` | `tp200` |
|---|---|---|---|---|---|
| 1 | deep-research thread, 2026-08-03 | 3,119 signal / 5,986 random, 278 names | +4.708%/trade | **+2.11pp** | **+3.26pp** |
| 2 | O1 exit sweep off the freeze, 2026-08-08 | **3,885** signal / **29,785** random, 5 seeds | +3.410%/trade | **+3.19pp** | **+3.82pp** |
| 3 | path study F-family, 2026-08-10 | **the same 3,885** | +3.410%/trade | *(not an arm)* | *(not an arm)* |

**Look 3 did not test a raised target directly**, because its families were path-*conditional*.
What it did test leans the same way and lands in the same range: `escalate_fast` (hit +100% early
→ trail instead of closing) **+2.40pp**, `clean_runner` (never below −10% by half DTE → target
+150%) **+1.50pp**, and from family A, `trail50_after100` **+3.60pp**. None cleared.

**THE INDEPENDENCE CLAIM IN THE INVENTORY IS TOO STRONG AND IS CORRECTED HERE.** Item A reads
*"replicated in two independent runs"*. Measured: look 1's 3,119 trades and look 2's 3,885 share
**1,099 trades — 35.2% of look 1 and 28.3% of look 2**. And **look 3 runs on look 2's book
exactly**, so it shares 100% of it. What we own is therefore **two partially-overlapping trade
sets and three analyses**, not three independent confirmations. The direction has never
disagreed — five separate measurements of a raised or extended target, on two books and two entry
sets, all positive — but the sample is one option-data corpus looked at three times.

**One reconciliation detail worth keeping.** The inventory's `+3.19 / +3.82` come from look 2;
look 1's own artifact reads `+2.11 / +3.26`. Both are correct for their own book. Anyone quoting
item A should say which.

**The mapping of look 1 onto `EXITLAB_RESULTS.json` is verified, not assumed** — three
independent facts agree: that artifact carries `n_entries {signal: 3119, random: 5986}` and
`n_universe: 278`, matching the inventory's description of look 1 exactly; its `tp200` gain is
**+3.26pp**, the figure the record quotes verbatim; and its `tp150` gain of **+2.11pp** is the
lower end of the record's quoted *"+2.1 to +3.3pp"* range. `EXITLAB_FROZEN_2026-08-08.json` is
the separate 3,885/29,785 run. Two files, two books, one of them easy to quote as the other.

---

## 2. Why **+10pp** is the wrong bar for a per-trade expectancy — argued from the distribution

### 2a. It is not scaled to the object it gates

`MIN_EXPECTANCY_GAIN = 0.10` was set in `options_backtest` to adopt a **construction** change.
The book's *entire* per-trade expectancy is **+3.41pp**. Applied to an exit parameter, the bar
asks a single threshold tweak to add **2.9× the whole book's edge**. That is a provenance
argument, and on its own it is weak — a bar being inherited does not make it wrong.

### 2b. Attainability, measured across every exit arm ever scored on this book

Thirty-three distinct non-baseline exit arms have now been scored on the 3,885-trade book
(O1's twenty, the path study's thirteen). **Exactly one clears +10pp:**

| arm | gain | verdict |
|---|---|---|
| `tp100_only` (no stop, no time stop, hold for the target) | **+10.78pp** | **fails paired-cell FDR**; raises tail concentration 86.75% → **92.75%**; and per inventory item J it fails the name-year sign test on the alert book at **z −5.76** while passing on random at **z +10.55** |
| `sl_none` | +4.43pp | — |
| `tp_none` | +3.93pp | — |
| `tp200` | +3.82pp | FDR discovery on both sets, both halves positive |
| `trail50_after100` (path study) | +3.60pp | CI straddles zero |

So the bar's rejection region over this family contains **one point in thirty-three**, and it is
occupied by the one arm the record already refuses on independent grounds. **A bar that only a
discredited arm can clear is not selecting for quality — on this family it is selecting for
removing the stop.** That is the substantive case against +10pp, and it is measured rather than
asserted.

### 2c. The deeper problem is the UNIT, and lowering the number does not fix it

Per-trade expectancy on this book is a **tail statistic**:

| | |
|---|---|
| hit rate | **35.3%** |
| median trade | **−52.2%** |
| share of gross winnings from the tail | **86.75%** |
| P(total loss) | 1.39% |

And the *gains* are more tail-concentrated than the book is. Measured directly on the four best
path-study arms, over the per-trade differences against shipped:

| arm | trades whose outcome changes | top-5 trades' share of the whole gain | **top-1%'s share** |
|---|---|---|---|
| `trail50_after100` | 1,030 | 32% | **149%** |
| `escalate_fast` | 629 | 48% | **210%** |
| `clean_runner` | 428 | 29% | **106%** |
| `half_at_100` | 1,047 | 30% | **139%** |

A top-1% share above 100% means **the other 99% of trades are collectively negative** and the
entire gain — and more — comes from a few dozen contracts. So "+3.82pp of expectancy" is a claim
about the tail, whichever level the bar is set at. **Moving 10pp to 3pp changes which
tail-determined number we accept; it does not make the statistic less tail-determined.** Any
serious bar has to add a condition that does not run through the mean.

### 2d. The obvious fix — "use a relative bar, the payoff is multiplicative" — is REFUTED by measurement

This is the fix the record itself proposes (`HANDOFF_deep_exits.md`: *"whether an absolute pp bar
is the right instrument for a proportional improvement is a real question"*), and it is the one I
expected to endorse. It does not survive the two books we have:

| | absolute gain | drift L1 → L2 | relative gain | drift L1 → L2 |
|---|---|---|---|---|
| `tp150` | +2.11pp → +3.19pp | **+52%** | +44.7% → +93.7% | **+109%** |
| `tp200` | +3.26pp → +3.82pp | **+17%** | +69.2% → +112.1% | **+62%** |

The baseline expectancy fell **−27.6%** between the two books (+4.708% → +3.410%), so dividing by
it *amplifies* the disagreement. **Across the only two trade sets that exist, the ABSOLUTE gain is
two to four times the more stable of the two units.** Switching to a relative bar would trade a
badly-calibrated stable statistic for a badly-calibrated unstable one.

**Reported because it cuts against the case for adopting**, and because it was the argument I
went looking for.

### 2e. The bar is also nowhere near the design's own resolution

Month-block clustered standard errors on the paired gain, measured on this book, run from
**0.29pp** (`time_cond25`) to **2.10pp** (`trail50_after100`) depending on how many trades the arm
touches. The design therefore resolves roughly **0.6–4.2pp** at |t| = 2. A 10pp bar is not
"conservative given the noise"; it sits an order of magnitude away from the noise, in a region
this family of rules never visits.

---

## 3. PRE-REGISTERED: what a bar for a paper-book policy change should require

**First, what such a bar is FOR — because that is what fixes its shape.** A bar on a live-money
change is an *economic* instrument: it asks "is this worth the cost and risk of doing?", and a
large absolute threshold is reasonable because small edges do not survive frictions. A bar on a
**paper-book** change is an *epistemic* instrument. No money moves; the change is reversible in
one constant; §4 shows it currently breaks no forward-record continuity either. So the cost of
adopting a small *true* improvement is very close to zero, and essentially the whole downside is
the other error: **adopting something that is an artefact of having looked at the same 3,885
trades three times, and thereby making the forward options record measure a rule chosen by
hindsight.**

That asymmetry says the bar should not be sized to *materiality* at all — it should be sized to
**separation from noise**, and it should carry a condition that survives the fact that the
statistic being gated is a tail average. A large absolute pp threshold does neither: it is a
materiality test wearing a significance test's clothes. That, and not its level, is why +10pp was
the wrong instrument.

**Second, the level must be calibrated, not chosen — including by me, in this document.** X7 is the
project's precedent and its lesson is exact: all four research bars were conventions and three
were set wrong, one of them (PBO < 50%) sitting *at* the noise median. The way to fix a bar here
is the way X7 fixed those: **measure what the null produces and take a percentile of it.** Any
number I argued for in prose would be a number chosen after seeing which arms pass.

So this document deliberately **does not name a replacement level**. It pre-registers the
procedure that would produce one, and the conditions that must accompany it:

**C1 — CALIBRATED LEVEL.** Build a null for "expectancy gain vs shipped" by the X7 method applied
to exits: score the shipped policy against **randomly perturbed exit parameters** drawn from the
same family (target, stop and time-stop levels jittered within their tested ranges), n = 100
draws, seeds 1000–1099 as the project's convention, on the identical frozen paths, scored through
the identical `apply_arm`. **The bar is the p95 of that null.** Committed in advance: whatever it
comes out as, including if it comes out above +3.82pp and refuses `tp200` again.

**C2 — A CONDITION THAT DOES NOT RUN THROUGH THE MEAN**, because §2c shows the mean is a tail
statistic. The gain must remain **positive after winsorising the top 1% of per-trade differences**
at the 99th percentile. On today's numbers this is a real test, not a formality: three of the four
arms in §2c would have to survive losing more than 100% of their measured gain.

**C3 — ENTRY-INDEPENDENCE, already satisfied and kept as a standing requirement.** The gain must
hold on the five pooled random-entry seeds. `tp150`/`tp200` pass (+2.60pp / +3.90pp on random
against +3.19 / +3.82 on signal), and the path study measured the general fact: across 13 arms the
effect on a random book tracks the effect on the alert book at **r 0.967, slope 0.990**. An exit
rule is a property of options, not of the entry — which is exactly why it is legitimate to adopt
one on a book whose entry is dead.

**C4 — THE EXISTING GATES STAY.** Paired-cell FDR at q = 0.1 (this is what refuses `tp100_only`),
both split directions positive, both entry sets positive, PBO under its calibrated bar.

**Nothing in C1–C4 requires new market data.** Every input is on disk in the freeze.

---

## 4. What the decision costs right now, which is the part most likely to be assumed wrong

**The paper options book has three positions — TGT, ETN, MET — all OPEN, and ZERO closed trades.**
Verified today against the committed `data_export/paper_track_history.json`.

So a policy change made now breaks **no** forward-record continuity: there is no realised options
exit anywhere in the live record for a new rule to be inconsistent with. It is the cheapest moment
this decision will ever have, and that is an argument about *timing*, not about *merit* — it makes
"adopt" cheap, not right. It also expires: the first closed trade ends it.

Two things it does **not** cost. No money moves — paper book, and `paper_broker` refuses any
non-sandbox endpoint. And **no vintage closes**: `PAPER_TRACK_CONTRACT.md` states in terms that
*"the register binds the published Valquo Index"*, and Amendment 1's vintage rule fires on
*"any ADOPTED change to scoring, weights, or construction"* of that Index. The options paper book
is a different object — §5b registers the sandbox as a separate experiment precisely so the two
cannot be confused. **Checked rather than assumed, because getting this backwards would mean
quietly spending a five-year clock on an options exit tweak.**

---

## 5. Don's options — in plain terms

**All three carry §0: the entry is dead, and none of these makes the options alert tradeable.**

### Option 1 — ADOPT `tp150` on the PAPER book now

Raise the take-profit from +100% to +150% on the paper options book only.

* **What it implies.** You are accepting a **+3.19pp** measured gain against a bar you have
  decided was mis-specified, on the strength of two overlapping looks, without the calibration in
  §3. The honest description of the evidence is "positive five times out of five, on one option
  corpus looked at three times".
* **What you give up.** The right to say the change cleared a pre-committed bar — because it did
  not, and the bar was revised after seeing the numbers. That is precisely the move this project's
  discipline exists to prevent, and doing it knowingly is different from doing it accidentally,
  but the record must say so in those words.
* **Why `tp150` and not `tp200`.** `tp200` is the larger gain (+3.82pp) and the worse trade in
  every other column: the hit rate falls 35.3% → **31.3%**, target exits fall 27.1% → **13.4%**,
  time-stop exits nearly double to 25.0%, and the mean hold lengthens 14.5 → 17.1 days. `tp150`
  buys most of the gain for less of that.
* **Cost:** zero trials — the measurement exists. Reversible in one constant.

### Option 2 — REQUIRE ONE MORE CONFIRMATION (the §3 procedure), then decide

Run C1–C4 as pre-registered above, then adopt or refuse on the calibrated bar.

* **What it implies.** The decision gets made against a bar that was *measured* rather than
  chosen, which is the only version of "we changed the bar" that survives being read back in six
  months. C2 in particular is a genuine hazard to the result, not a rubber stamp.
* **What it costs.** No new data. One session's compute on the freeze. **Trial cost: the placebo
  calibration searches nothing and is charged zero** (X7 and the session-10 HAC floor are the
  precedent); the winsorised re-scores of `tp150`/`tp200` are **2 arms** charged to options `N`
  (205 → 207).
* **The honest risk.** It may return a bar above +3.82pp and refuse the change — in which case
  item A closes as REFUSED on a calibrated bar, which is a better outcome than either adopting or
  leaving it parked, and is the single most likely result (§6).

### Option 3 — LEAVE IT

Keep +100%, and let item A stay on the parked list.

* **What it implies.** The shipped policy stands on evidence the path study strengthened
  considerably: closing at +100% is not leaving free money on the table — **83.2%** of early
  winners give the +100% back and **58.0%** eventually go below zero if held. The inherited rule
  is defensible on its own merits, not merely unrefuted.
* **What you give up.** A small, repeatedly-measured, entry-independent improvement, and the
  cheapest moment to make it (§4).
* **Cost:** zero.

---

## 6. Pre-registered expectation, written down before C1–C4 are run

Because this project's directional guesses have been wrong more often than right, and writing
them down is the only thing that keeps that measurable:

* If Option 2 runs, the calibrated p95 bar lands **between +1pp and +4pp**, i.e. in the same range
  as the effect — **60/40**. A null built by jittering exit parameters should produce gains of the
  same order as real ones, because §2c says both are tail draws.
* Conditional on that, `tp150` **clears** the calibrated bar — **55/45**. Barely, and that is the
  point: a bar calibrated to this family will not clear it comfortably.
* `tp200` clears but **fails C2** (winsorised gain) where `tp150` passes — **50/50**, stated
  because I genuinely do not know.
* My own recommendation, recorded so it can be scored later: **Option 2.** The change is small
  enough that adopting it without calibration buys very little and spends the project's main
  asset, which is that its bars were fixed before its numbers.

---

## 7. Trial accounting for THIS document

**Zero.** No arm was scored, no hypothesis tested, no bar applied. Every figure above is a re-cut
of already-banked artifacts (`EXITLAB_RESULTS.json`, `EXITLAB_FROZEN_2026-08-08.json`,
`PATHSTUDY_ARMS_SIGNAL.json`, `PATHSTUDY_STAGE2.json`) plus one read of the committed paper-track
export. Options `N` stays **205**; equity `N` stays **135**. If Don picks Option 2, that run is
charged **2** on landing, as committed in §5.

---

## 8. C1 RESULT — THE BAR, FIXED BEFORE ANY ARM WAS SCORED AGAINST IT

**Don chose Option 2 on 2026-08-11.** This section records C1 and *only* C1. It is committed in
its own commit, with the scoring code not yet written, so the ordering the memo demanded —
**bar first, arm second** — is visible in the git history rather than merely asserted.

Reproduce: `python -m scripts.tp_bar --calibrate`. The artifact
(`data/options_pathstudy/TPBAR_NULL.json`, all 100 draws retained) is **gitignored like every
other licensed-data output**, so the figures are transcribed here; every draw is recoverable from
its seed alone.

### The bar

| quantity | value |
|---|---|
| **CALIBRATED BAR (p95 of the null)** | **+5.0812 pp** |
| null minimum | −6.786 pp |
| null p5 | −4.570 pp |
| null median | **+0.803 pp** |
| null maximum | +8.111 pp |
| draws beating `shipped` | **53 of 100** |
| draws | 100, seeds 1000–1099, each paired on all **3,885** trades |

**The harness control passes before the bar means anything:** the `shipped` arm scored through
this path re-build returns **+3.4103%/trade**, which is R2's published headline to the digit, and
every draw is paired on the *same* 3,885 trades (`n_paired` 3885–3885 with no variation), so no
draw can move its gain through the denominator.

### Two things this null says that were not known before it was run

**The shipped exit is slightly BELOW the median of its own family.** The median jitter beats it by
+0.803pp and 53 of 100 do. The inherited +100%/−50%/half-DTE is not a local optimum on this book —
it is an ordinary member of its family.

**The family's good region is coherent, not noise.** The five best draws are all the same shape —
target 1.29–1.94, stop −0.53 to −0.69, time-stop fraction 0.70–0.90, i.e. *wider stop, higher
target, hold longer*. A null whose tail is structured rather than scattered is exactly what makes
a p95 from it a demanding bar, and it is why the bar landed where it did.

### What the bar is, stated so it cannot be over-read later

This is **not a no-effect null**. Every draw is a real policy on real paths, and this record
already says raised targets tend to help on this book, so the null *contains* the effect. The p95
therefore answers the selection question — **is a given arm distinguished within its own family?**
— which is the actual hazard item A carries after three looks at one corpus. It does **not**
answer "does raising the target do anything at all", and a failure against it must never be
quoted as if it did. §9 will say which arms clear it; this section was written before that was
computed.
