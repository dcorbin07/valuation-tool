# SEARCH_DOCTRINE.md — where this project searches next, and where it stops
## Frontier Scout, 2026-08-27. **Zero trials. No outcome statistic computed anywhere in this file.**
## Every number below is either published in the record or arithmetic on published numbers.

**Counters, live:** equity **245** (hurdle **3.3170**), options **310** (**3.3872**), infra 20.
*(`RESEARCH_LOG`'s last quoted figures read 242/308 — mid-session reads that lag, `MA37`'s
recurring rule. The lane that landed DC-1 re-read 245 after merging and that is the figure.)*

**THE WIDTH AUDIT HAS NOW RUN — `WIDTH_AUDIT.md`, 2026-08-28 — and it CORRECTS this file in three
places.** Per `B7` (do not maintain the same argument twice), the folded-in correction-class
material in §1.2 and §3 is **superseded by that file**, and these three corrections are owed here:

1. **The counters above are UNVERIFIED.** The ledger's last append reads **equity 242** (hurdle
   **3.313287710464241**), **options 305**, infra 20. Neither 245 nor 310 appears anywhere in
   `VALQUO_LEDGER.md`, `CLAUDE.md` or `RESEARCH_LOG.md`. **I published a counter I had not verified
   against the file that owns it.** See `WIDTH_AUDIT` §0.4; every hurdle below moves by less than
   0.004 and no argument here turns on it, but **no trial may be booked until the counter is
   re-read.**
2. **§1.2's and §1.4's absolute MDEs are too small.** `MB18`'s 0.4274 SD is published **at
   `crit` 2.71**, not at the HLZ hurdle; inverting at the hurdle understated `se`. The corrected
   basis-six `se` is **0.120394 SD**, which puts the unpaired 80%-power MDE at **0.5002 SD**.
   **The paired GAIN ratios (2.2× / 3.2× / 5.0×) are unaffected — they are ratios and cancel `se`.**
   **And §1.4's headline gets STRONGER: 0.5002 SD is 115% of `z_fcf_margin`'s 0.4346 SD, so the
   cross-section cannot reliably detect even the best signal it already contains.**
3. **`MB12` is four items in the R² 0.027–0.145 band, with a fifth at 0.2926 / 0.2936** — not
   "five bodies" as §1.6 and §3 say.

*`WIDTH_AUDIT` §3's entry-#1 justification supersedes §3's here; read that file for the Total Q
argument rather than this one.*

---

# PART 1 — THE META-PATTERNS, MEASURED

## 1.1 THE HEADLINE, AND NOBODY HAS WRITTEN IT DOWN: the register era has produced ZERO return discoveries

Every result that survived the register era is about **method, risk, or cost**. Not one is a new
source of return:

| survivor | what it actually established | class |
|---|---|---|
| `S14` + `S14-WIDTH` — **the record's ONE adoption** | a no-trade band, adopted on **net** alpha | **COST** |
| `MA28-CARD` — passes all three legs | flagged names crash at **3.0422×** | **RISK** |
| `V6-B` M1 | healthy dips fall further **10.8pp less often** | **RISK (survival)** |
| `THEME-RESTORE` / `FIDELITY-2` | three dead themes restored — **gated on FIDELITY, not alpha** | **CONSTRUCTION** |
| `R3`, `R9`, `R10`, `X1`, `X5`, `MB21`, `MB23`, `SC-1b`, `MB22` | inference, benchmarks, nulls, power, calibration | **METHOD** |

**The composite itself — the only return edge the project owns — predates the register era.**
Two hundred and forty-five equity trials and three hundred and ten options trials have not
produced a single new source of return. **They have produced a great deal else, and the doctrine
below is built on taking that seriously rather than treating it as a run of bad luck.**

## 1.2 ADDITIONS: the count is worse than 0-for-6 — and the correction claim needs correcting

**Additions (a new column, tested incrementally against the incumbents) are 0-for-9 distinct
registers**, not six: `U2`, `MA31`/`MA32`, `MA58-SEAS`, `MB18`, `E-2`, `E-3`, `E-6`, `S2`, `S19`
— plus `S17`, which carried **ten arms inside one register and returned ten nulls**, and `E-1`,
which never reached an outcome because its own size-sort kill fired first. **Not one has cleared.**

**But the claim that "corrections to incumbents have never been tried once" is FALSE, and the true
version is sharper.** Corrections have been tried at least seven times:

| register | what it corrected | outcome |
|---|---|---|
| `S1` | value theme inputs — drop `book_to_price`, swap `neg_ev_ebitda` | **both arms REJECTED** |
| `S3` | the insider score, three rebuilds | **all three REJECTED** |
| `S16` | net issuance decomposed | **all four arms REJECTED** |
| `S20`/`S21` | the standardisers (rank; winsorisation) | REJECTED / NOT-REPLICATED |
| `S27` | recency weighting | premise false — already shipped |
| `LOO` | leave-one-out theme ablation | NULL, 4 of 7 arms flip sign across halves |
| `THEME-RESTORE`/`FIDELITY-2` | three dead themes restored | **PASSED — and gated on fidelity, not alpha** |

**Read those two rows together and the pattern is not "additions fail, corrections work." It is:
every correction that was RE-ARRANGEMENT of data we already held failed on the alpha gate, and
the one correction that PASSED was judged on a different object.** That is §1.3 arriving early,
and it is a stronger finding than the one the commission proposed.

**So the genuinely untried class is narrower than "corrections" and it is this:**

> **RE-MEASUREMENT — the incumbent captures the right economic construct with a known-defective
> proxy, and a better-measured version of THE SAME construct exists outside our data.**

`S1` swapped one owned ratio for another. `S3` rebuilt a score from raw rows we already had.
`S16` decomposed a field we already had. **None imported a better instrument for a construct the
composite already bets on.** Peters–Taylor Total Q — intangible-inclusive capital — is exactly
that for every book-value denominator in the value and capital-discipline themes.

**And there is a mechanism for why this class should behave differently, which is what keeps it
off the orthogonality wall:** measurement error **attenuates** an IC toward zero. Fixing the
proxy **de-attenuates the same bet** rather than adding a new one — so the register is not
claiming orthogonal information (the motivation that has failed five times), it is claiming the
incumbent is being measured badly.

**The power consequence is large and it is the strongest quantitative argument in this document.**
An addition is tested as an **incremental IC against a residualised basis**; a re-measurement is
tested as a **PAIRED comparison of two proxies of one construct on the same names and dates**.
Using `MB18`'s own published 80%-power figure of **0.4274 SD** as the unpaired scale, and
`SE_paired ∝ √(2(1−ρ))` where ρ is the correlation of the two proxies' per-date IC series:

| ρ between old and new proxy | paired 80%-power MDE | improvement over an addition test |
|---|---|---|
| 0.90 | ≈ **0.19 SD** | **2.2×** |
| 0.95 | ≈ **0.14 SD** | **3.2×** |
| 0.98 | ≈ **0.085 SD** | **5.0×** |

**A re-measurement register can see effects two to five times smaller than any addition register
run on this panel — on the same 69 dates, with no new power and no new data beyond the proxy.**
That is where the next ten trials should point, and §3 points them there.

## 1.3 THE VERDICT OBJECT MATTERS MORE THAN THE SIGNAL

`MA28`'s flags **failed** the alpha gate as an exclusion screen (`S10-ACCT`) and **failed again**
as a sizing haircut (`MB8`, which additionally measured them nearly disjoint from the book) — and
**passed** when the question became crash rate. Same data, same flags, three registers, one win,
and the win is the one whose verdict object matched the mechanism. `E-4` and `E-5` partially
repeated it (full sample clears at 3.19×; hazard decays monotonically 9 of 9).

**The rule this implies is not "try more verdict objects until one clears" — that is p-hacking at
the family level. It is: choose the verdict object the MECHANISM predicts, before the run.**
`MA28`'s flags measure distress; distress predicts crashes; crash rate was the right object all
along and it took three registers to ask it.

**Verdict objects that have never had a register:**

| object | which owned signal it would suit | why nobody asked |
|---|---|---|
| **Drawdown CONTRIBUTION** (which names carry the book's drawdown) | the composite itself; `MA28`; `E-4` | `S10` measured the book's drawdown is one market-wide quarter and everyone stopped — but *contribution within* that quarter was never decomposed |
| **Tail hazard / time-to-event** | `MA28`, `E-4` | `E-5` began it and returned UNRESOLVED on a conjunctive bar |
| **Turnover induced** (does a signal make the book trade more?) | every candidate signal | `S14` won on net alpha, which bundles it; turnover has never been the primary |
| **Fill quality / realised spread** | every options entry | `F-1` tests it forward; no backtest register has ever had it as a verdict |
| **Assignment frequency** | short-side structures | `V6-OPT` measured 25.30% vs 25.73% **descriptively** and gated on return instead |
| **Capacity** | the whole book | `P1`/`P2`/`O22` measured it; never a pass/fail |
| **Concentration of P&L** (top-k share) | the options book | `P3` measured the distribution; never gated |
| **Time-to-recovery** | `V6`/`V6-B`'s dip population | `V6` measured calendar return instead — `DC-1` is the first register to re-clock anything |

**Every one of these is answerable on data already owned, and each is cheap: the signal exists,
only the question is new.**

## 1.4 POWER IS DESTINY — and the trials were spent in the weakest space

| searchable space | raw size | **unit of independence** | effective n | 80%-power MDE, in its own units |
|---|---|---|---|---|
| **Equity panel cross-section** | 113,945 cells | **the DATE** | 69 → **58.65** (deff 1.177) | **0.4274–0.5071 SD** (`MB18`, published) |
| Tick cache | 70.3 M prints | **the MONTH** (median 2 names/date; **zero** dates reach 20) | ~115 months | **13.7pp/trade** (`MB16`'s banked SE 0.04817) |
| Options alert book | 3,870 trades | name-year cluster (`R3` deff 2.19) | ~1,770 | `R2` saw −5.06pp; entry closed |
| **Event-time on the panel** | staggered events | **the EVENT**, if within-episode residual correlation is low | **100s–1,000s** | **1.66pp at n_eff 400** (`DC-1` §7) |
| **Forward fleet** | fills, accruing | **the FILL** | **unbounded in time** — 18 books live | `F-1` resolves at ~60 paired fills ≈ 1–2 months |
| Deep chain freeze | 353.7 M rows | contract-day, heavily clustered | unmeasured | unknown — nobody has computed it |

**Now put the first row beside the record's own strongest measurement.** `MB18` established that
the panel's 80%-power detection threshold is **0.4274 SD**, and that the largest raw anchor the
panel has ever carried is `z_fcf_margin` at **0.4346 SD**.

> **On the 69-date cross-section, the 80%-power MDE is approximately equal to the largest effect
> the panel has ever contained. That space can essentially only detect signals as strong as the
> best signal already in it. A merely good new signal is invisible there BY CONSTRUCTION.**

**Two hundred and forty-five equity trials were spent in that space.** The event-time space —
where the same panel yields MDEs an order of magnitude smaller — has **one drafted register**
(`DC-1`). The forward space has one season of books, launched this month. **That misallocation is
the single most consequential thing this record can now tell us about itself.**

## 1.5 FORWARD-FIRST, PRICED — and the scarce resource is not trials

**What a backtest trial actually costs**, at equity N = 245 (`hurdle = √(2 ln N)`):

| after | N | hurdle | Δ |
|---|---|---|---|
| today | 245 | 3.31700 | — |
| +1 | 246 | 3.31823 | +0.00123 |
| **+2** | **247** | **3.31946** | **★ `MB31`'s flip: seed 1003 at 3.319188 is crossed — a bounded floor re-derivation becomes OWED** |
| +5 | 250 | 3.32309 | +0.0061 |
| +10 | 255 | 3.32904 | +0.0120 |

**Ten trials cost 0.012 of a t.** Against a headline long-short of 2.6199 that is not the binding
cost — **the binding cost is at N = 247, two trials away, where a floor re-derivation is triggered
by arithmetic.** Price the season in that unit and not in vague caution.

**And a forward book charges its trial at FIRST VERDICT READ, years out, with the option to
abandon uncharged.** So its trial cost is deferred and conditional. **The fleet is live — 18 books
accruing records, the shelf rendering commit, date, days accrued, fills, and state.**

**Which means the scarce resource has changed and nobody has said so.** With forward books nearly
free in trials, **the binding constraint becomes CALENDAR TIME TO A DECISION.** A backtest answers
in a session; a forward book answers in one to six quarters, and `F-16` honestly in six. **An
optimal season therefore maximises information per QUARTER, not information per trial** — which
inverts the allocation rule the project has used for a year.

**The allocation rule that follows:** launch forward books early and in parallel (their clocks run
concurrently and cost nothing until they speak); **spend backtest trials only on questions that
(a) only the freeze can answer, or (b) GATE a forward book's design.** Everything else waits for
its own clock.

## 1.6 THE COMBINATION AXIS — closed at the weights level, nearly closed at the structure level

The edge came from combining seven weak themes; the weighting family is rejected five schemes
deep plus `MLCOMB`, which **reversed out of sample** (+1.88% tree against +11.58% linear).
`S24` (ensemble across draws) came back rank-correlated **0.9907** with the incumbent. `S20`/`S21`
changed the standardisers and failed. `LOO` ablated and returned NULL.

**Is the STRUCTURE level open?** The one distinction that survives is **conjunctive versus
compensatory** aggregation: a weighted mean lets a strong value score compensate for weak quality;
a conjunctive rule ("all seven above median") cannot be expressed by any weight vector.

**And the argument against it is strong enough that I will state it rather than sell past it: a
decision tree IS conjunctive, `MLCOMB` fitted one, and it reversed.** The surviving distinction is
narrow — **`MLCOMB` *fitted* the conjunction; a pre-committed conjunctive rule fits nothing** —
which is exactly `E-1`'s argument form, and `E-1` died on a size-sort kill rather than on that
argument. **Verdict: worth exactly one trial, ranked low, carrying two hostile priors. If Don
prefers to drop the thread, dropping it is defensible and this file will not argue.**

## 1.7 EXOGENOUS SIGNALS — reachable, but the options book's problem is not data

`W-14` died on entitlement, not on the idea. Reachable exogenous classes on data owned or
subscribed: insider clusters (owned), 13F breadth (owned), `MA28` flag transitions (owned), index
membership (Historical SPDJI), earnings actuals and revisions (IBES), delistings (CRSP),
blockholders, patents, TRACE, plus free forward catalyst calendars (`S3-I2`, built).

**But the honest constraint is not supply.** An exogenous signal can only enter the options book
as an **entry** signal, and entry is precisely where `R2` killed everything (−5.06pp against
random) with `MB1` putting ~79% of the loss in the **day**. **So exogenous signals should enter
the options book through a verdict object OTHER than entry** — which contract, when to *avoid*,
what to refuse — or through the forward fleet where the book is new. `F-9`, `F-15` and `F-16` do
exactly that. Nothing on the freeze does.

## 1.8 TWO PATTERNS THE COMMISSION DID NOT NAME

**(a) Pre-outcome kills are the highest-yield instrument this project ever built.** `MB15` (void
before any arm), `MB1-SEL` (gating control fired, arm never ran), `E-1` (withdrawn on K2), `MB9`
(refused as stated), plus `O-1`'s and `DC-1`'s designed-in kills. **Roughly a third of recent
registers died free** — each would otherwise have cost one to two trials and a session.
**Doctrine: invest MORE in kills, and design each one to be free and to fire before the arm.**

**(b) This project is measurably better at finding its own errors than at finding market
inefficiencies.** The `B` series closed 24 of 26; the `MA` series repaired dozens; nearly every
register confesses a defect in its own instrument. **That is a comparative advantage, not a
weakness** — and it is why the two things this project has shipped that nobody else has are
`MB38`'s published denominator and `SC-1b`'s measured prior calibration. **The most defensible
product this project owns may be the METHOD, not the edge.**

---

# PART 2 — THE DOCTRINE

**Premise, from §1.1: the register era has produced zero new sources of return and a great deal of
method, risk and cost. Search accordingly — not because return is impossible, but because the
record says return is where this panel is weakest and cost/risk is where it has actually won.**

### WHERE WE SEARCH

1. **RE-MEASUREMENT before addition.** Improve the proxy for a construct the composite already
   bets on. *Why:* additions are 0-for-9; the only correction that passed was gated differently;
   and a paired re-measurement test sees effects **2–5× smaller** than any addition test (§1.2).
2. **VERDICT OBJECTS MATCHED TO MECHANISMS.** Before proposing a signal, ask what the mechanism
   actually predicts and gate on that. *Why:* the record's cleanest win came from changing the
   question, not the data (§1.3).
3. **HIGH-POWER SPACES FIRST — event-time and forward.** *Why:* the cross-section's 80%-power MDE
   ≈ the best effect it has ever held; event-time and forward spaces are an order of magnitude
   better and hold one register between them (§1.4).
4. **COST AND EXECUTION.** *Why:* the only adoption in 245 trials was a cost change, and cost
   improvements compound identically to edge while requiring no forecast (§1.1, `S14`).
5. **KILLS BEFORE ARMS, AND FREE.** *Why:* a third of recent registers died free (§1.8a).
6. **METHOD AS PRODUCT.** *Why:* it is the project's measured comparative advantage (§1.8b).

### WHERE WE DELIBERATELY STOP

1. **New orthogonal columns on the panel.** 0-for-9, and the space cannot see a merely-good signal.
2. **Weighting and combination.** Five schemes, `MLCOMB` reversed, `S24` rank-identical, `LOO` null.
   *(One exception, ranked low: §1.6's pre-committed conjunctive rule.)*
3. **Regime conditioning.** `MB13`: 34.2 years per side against 17.3 owned. Arithmetic, not taste.
4. **Sharpe- or drawdown-PRIMARY gates.** `R-1`'s arithmetic, and Don's economic ruling on top.
5. **Alert-conditioned flow features.** Six NULLs on a cache with no cross-section (§1.4).
6. **Any register whose 80%-power MDE is not computed BEFORE the arm.** Not a topic — a procedure.
7. **The options ENTRY question.** `R2` stands; exogenous signals enter through other objects.

### STOP-RULES — what closes a direction, and what reopens it

| direction | CLOSES when | REOPENS only on |
|---|---|---|
| **Additions** | already closed on 0-for-9 | a candidate whose paired ρ against an incumbent exceeds 0.6 — i.e. it is a re-measurement wearing an addition's name, and should be re-framed |
| **Re-measurement** | three consecutive paired re-measurements fail at ρ ≥ 0.9 (where power is best) | a new external instrument for a construct not yet re-measured |
| **Verdict objects** | a mechanism-matched object fails on the signal whose mechanism it matches | a new signal with a mechanism no existing object tests |
| **Event-time** | `DC-1`'s K1 fires, or measured within-episode correlation is high enough that `n_eff` ≈ episode count | a second event class with staggered dates |
| **Forward fleet** | a book reaches its declared horizon and its meter resolves | new books are always admissible; they cost nothing until they speak |
| **Cost/execution** | `F-1` resolves NO-MATERIAL-DIFFERENCE **and** a daily-OHLC cost model shows the band is already optimal | a change in broker, venue routing, or size |
| **Combination structure** | the one conjunctive trial fails | nothing — that would close it permanently |

**And the standing rule that outranks all of the above:** *a direction is closed by ARITHMETIC or
by a MECHANISM, never by a run of nulls alone.* `MB13` closed regime conditioning with a number.
`R-1` closed Sharpe gates with a number. Those closures are durable. A direction closed only
because three registers failed is a direction resting on a small sample, and it says so.

---

# PART 3 — THE SEARCH, DERIVED

## 3a. The ranked ten backtest trials — cost curve attached

*Ranked by (doctrine fit × mechanism strength × power) ÷ trials. Every entry needs a blind
register, coverage measured on its own population, kills before arms.*

| # | register | class | mechanism / graveyard tag | trials | N after | hurdle |
|---|---|---|---|---|---|---|
| **1** | **Total-Q re-measurement** (sibling audit's object) — intangible-inclusive capital replacing book denominators in value / capital-discipline | **RE-MEASUREMENT** | attenuation: the same bet, measured better. Tags: `S1` (swaps failed), `MB18` (additions failed), `MB12` (orthogonality is not a motivation — **and this register explicitly claims NON-orthogonality**) | 1 eq | 246 | 3.3182 |
| **2** | **W-1 / `S25` sector re-run** — the confirmed unlock, `SECTOR-NEUTRAL-B6` re-run verbatim on the PIT map | RE-MEASUREMENT | today's map applied backward is attenuating noise; `co_hgic` is dated history (94.9%, 30.2% multi-row). Tag: `S15`, `S25` | 2 eq | **248 ★ crosses 247** | 3.3207 |
| **3** | **`MB20`** insider routine-vs-opportunistic | RE-MEASUREMENT (reconstruction of an incumbent theme) | CMP's split is the construction `S3` never built; `S3` itself measured that "has a score at all" beats the theme's direction. Tag: `S3` ×3 | 1 eq | 249 | 3.3219 |
| **4** | **`DC-1`** dip-confirmation in event time | **HIGH-POWER SPACE** | narrative falsified at a dated event; K1 can kill it free. Tags: `V6`, `V6-B`, PEAD, value | 1 eq | 250 | 3.3231 |
| **5** | **Drawdown CONTRIBUTION** — decompose the book's one bad quarter by name and by flag | **VERDICT OBJECT** | `S10` closed the *screen* question and never decomposed the quarter; mechanism-matched to `MA28`/`E-4` | 1 eq | 251 | 3.3243 |
| **6** | **`B13`+`S7` liquidity** on CRSP `dsf` (89.7% vs 19.8%) | **CORRECTION** (a filter that structurally cannot bind is a defect) | `B13` PARTIAL-BLOCKED; `S7`'s fourth interaction "NOT BUILDABLE" — it was never rejected, only impossible | 1 eq | 252 | 3.3255 |
| **7** | **`MB14`** three-state regime diagnostic | **CLOSURE PURCHASE** | buys a dated, powered refusal of the project's largest open wound; `MB13` predicts CANNOT-TELL and the register pre-commits that this closes regime work permanently | 1 eq | 253 | 3.3267 |
| **8** | **`MB19`** lens-disagreement width | addition (ranked below its class-mates deliberately) | `MA55` design-recorded; `w_floor` is the whole design and a free-parameter verdict is VOID | 1 eq | 254 | 3.3279 |
| **9** | **Tail-hazard register** — `E-5`'s UNRESOLVED conjunction re-specified on a single pre-named statistic | **VERDICT OBJECT** | the hazard decayed 9 of 9 steps and the bar was conjunctive; one statistic, one bar | 1 eq | 255 | 3.3290 |
| **10** | **Conjunctive composite**, pre-committed, unfitted | combination structure | §1.6 — one trial, low prior, two hostile priors (`MLCOMB` reversed; `E-1`'s size kill) | 1 eq | 256 | 3.3302 |

**Cost of the full ten: hurdle 3.3170 → 3.3302, i.e. +0.0132 of a t — and one floor
re-derivation, owed at entry #2 where N crosses 247.** That is the whole price, stated once so
Don can see it rather than approve a cap he cannot picture.

**Options trials are deliberately absent from this ten.** The entry question is closed (`R2`),
the flow space is structurally blind (§1.4), and the two live options questions — fill quality
and menu breadth — **are forward books already running.** Spending options trials on the freeze
today would be spending them in the space the doctrine says to leave.

## 3b. The next wave of declared forward books — near-free, launched in parallel

*Each: 1 trial charged at first verdict read, abandonable uncharged. All inherit the fleet
harness, `S3-I3`'s assignment module where short, and the amendments filed in session 9.*

| book | mechanism in a phrase | verdict object | tag |
|---|---|---|---|
| **G-1 · Cost ledger** | record realised-vs-quoted spread on every fleet fill and fit a daily-OHLC cost model against it | **fill quality** | `O18` ρ=0.6743; `F-1` is its A/B sibling |
| **G-2 · Assignment-frequency book** | short structures recorded solely to measure assignment rates against `V6-OPT`'s descriptive 25.30/25.73 | **assignment frequency** | `V6-OPT` measured it and gated on return instead |
| **G-3 · Turnover ledger** | the live book's induced turnover per signal change, priced at G-1's cost model | **turnover** | `S14` bundles it; nobody has isolated it |
| **G-4 · Flag-transition watch** | `MA28` transitions recorded forward with no position — a pure base-rate accrual | **tail hazard** | `F-9` trades it; this one only measures it |
| **G-5 · Index-membership events** | SPDJI add/delete dates recorded forward, no position | **event base rates** | decayed-effect prior stated up front |
| **G-6 · Capacity meter** | the paper book's own fills against `O22`'s depth measure, accruing | **capacity** | `P1`/`P2`/`O22` measured once, never tracked |

**Why these six and not more signal books:** every one has a **verdict object the record has never
gated on** (§1.3), every one accrues in the **highest-power space** (§1.4), and **four of the six
hold no position at all** — they are measurement instruments wearing a book's clothes, and they
cost a trial only if someone reads a verdict. **That is the cheapest evidence this project can
buy, and it is available this quarter.**

## 3c. What I would do first if it were mine to decide (and it is not)

**Run the sibling width audit before spending trial #1.** Everything above ranks Total-Q
re-measurement first, and that ranking rests on a class argument I folded in from a commission
that has not run. **If the width audit finds no external instrument for any incumbent construct,
entry #1 evaporates and the ranking changes** — which is exactly the kind of dependency that
should be resolved for free before a trial is charged.

---

**Batched questions for Don:** (1) Does the allocation rule in §1.5 — *backtest trials only for
what only the freeze can answer or what gates a forward book* — become standing policy? (2) The
conjunctive thread (§1.6, entry #10): keep at one trial or drop? (3) Entry #7 buys a permanent
closure rather than a discovery — is that a use of a trial you want? (4) The six G-books hold no
position in four cases; confirm that measurement-only books are welcome in the fleet.
