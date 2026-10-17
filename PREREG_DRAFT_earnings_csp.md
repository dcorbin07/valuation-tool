# PREREG DRAFT — EARNINGS-CSP — selling the earnings premium, not buying it

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no option is priced, no trial is
booked. A register is committed **ALONE** by the executor (markdown only, zero `.py`, a strict git
ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**LEVEL 2 CLEAN.** A cash-secured put is on Don's Alpaca IRA permission list (long calls and puts,
cash-secured puts, covered calls). **No spread, no other broker, no new agreement.** That is a
deliberate design constraint and not a coincidence — `SELL-PREMIUM-3` needs Fidelity, Schwab or
tastytrade and Don's account cannot hold it.

---

## 0. WHAT HAS ALREADY BEEN SEEN, DECLARED FIRST

**THE MOTIVATION IS AN IN-SAMPLE READ OF THE WHOLE WINDOW, AND THAT IS A REAL COST.** `O7`
measured earnings options rich over **2016–2025** — the build quadrant **and** the check window —
on **6,013 events** of the 186-name megacap options book. So the fact that motivates this draft was
established on data that includes the window any confirmation would use.

**WHAT IS NEVERTHELESS BLIND:** `O7` measured the **straddle BUYER** on a **different universe**
(the alert book, not the point-in-time $10B tier) at a **different tenor** and with **four
crossings**. **The put-selling side has never been measured at any tenor on any universe.** So:

* the **staged ladder stands** — build quadrant (2016–2019 × ticker half 0), then **one** check
  read, then a forward paper book (`DECISIONS.md` 2026-10-13, three rungs because no options data
  exists before 2016);
* **a stage-2 pass is recorded `ELIGIBLE-BUT-UNRESOLVED (MOTIVATION WINDOW PREVIOUSLY SEEN)`** and
  never a blind confirmation. `SELL-PREMIUM-3`'s register set that precedent and its clause cost
  nothing because stage 1 did not pass; **this draft expects to pay it.**

---

## 1. SEPARATION FROM WHAT IS CLOSED — AND ONE OF THE KILLS IS AIMED STRAIGHT AT THIS

**`O-SEED-5` KILLED AN EARNINGS SHORT-VOL STRUCTURE AND ITS WORDING NAMES THIS DRAFT'S OWN
EVIDENCE.** Quoted in full because it is the obstacle:

> *"**O-SEED-5 — calendar spreads around earnings: KILLED.** The front leg's profit *is* the closed
> short-vol family's edge: `O7`-B1 measured the market overpricing the event move (implied 5.4512%
> vs realized 4.7773%) and that richness is exactly what a short front-month monetises — `O9`
> closed the family and `V6-OPT` re-killed it on mechanism … a two-leg single-name structure pays
> `D9`'s 4.7–12.6%-of-premium costs TWICE on a differential (implied−realized ≈ 0.67% of spot) that
> is smaller than the double spread."*

**THREE SEPARATIONS, AND THE FIRST IS MEASURED RATHER THAN ARGUED.**

1. **"`O9` CLOSED THE FAMILY" HAS BEEN OVERTURNED BY MEASUREMENT SINCE `O-SEED-5` WAS WRITTEN.**
   `SELL-PREMIUM-2` then passed **every clause** of Don's rule on the build quadrant —
   **+0.6709%/trade on secured cash**, both halves, **87.47% wins**, beating its random-day twin at
   **z +9.9485** — which is the strongest single-name premium-selling result in the record.
   **`O9`'s own object was IV rank as sell-timing on SPY / QQQ / IWM** — **index** vol, whose effect
   *"flips sign across SPY/QQQ/IWM"* — and a closure of index vol-timing is not a closure of
   single-name premium selling. **`O-SEED-5`'s inference was reasonable when written and is now
   contradicted by a landed result.**
2. **THE COST HALF OF THE KILL DOES NOT TRANSFER, AND THE ARITHMETIC IS THE POINT.** Its kill is
   explicitly about **a two-leg structure paying costs TWICE** on a **0.67%-of-spot** differential.
   **A cash-secured put held to expiry pays ONE crossing** — `SELL-PREMIUM-2`'s measured mean
   half-spread is **0.2127% of strike** — so the cost is **about a third of the differential rather
   than twice it.** `MA46`: an expiring option is never sold.
3. **`V6-OPT`'s MECHANISM KILL IS ABOUT RISK DISCRIMINATION, NOT ABOUT WHETHER PREMIUM PAYS.** It
   measured that a **delta target equalises assignment by construction** (25.303% healthy against
   25.727% unhealthy), so a *risk signal* cannot pay through it. **This draft carries no risk
   signal** — the conditioning is a scheduled calendar event — so the mechanism has nothing to
   neutralise. `SELL-PREMIUM-2`'s `A4` confirmed that autopsy at 25 delta and it was the prediction.

**AND THE OTHER NEIGHBOURS, each separated on a stated axis:**

| item | what it is | why this is not it |
|---|---|---|
| **`O9`** | IV rank as sell-timing on **SPY/QQQ/IWM** | index vol, effect flips sign across the three; this is single-name and calendar-conditioned |
| **`F-4`** | a fleet book that **deliberately avoids events** | its rule requires the next earnings date **KNOWN and OUTSIDE** `[today, expiry+5 sessions]`, skipping and counting unknowns. **F-4 is the complement of this draft**, which makes the pair a clean contrast rather than a duplication |
| **`F-10`** | clean CSPs, **no event filter**, events *ambient* | 52 DTE, so `EVOWN` applies (below) — its events arrive by accident, not by selection |
| **`O17C4`** | owning the event with **CALLS** | measured **real** (+4.79pp against random entry, both halves, z +2.054) — **so event ownership pays on the LONG side and this tests the SHORT side of the same event** |
| **`EVOWN`** | owning the event at the engine's **45–75 DTE** band | **spanning is VACUOUS there — 4,769 of 4,769 at K=5** — and the DTE-matched control was **61.9% spanning anyway**. **At ~15 DTE spanning becomes a CHOICE, and this is the first design where it is one** |

**THAT LAST ROW IS THE STRUCTURAL ARGUMENT FOR THE SHORT TENOR AND IT IS `EVOWN`'s OWN FINDING
READ FORWARD:** at 45–75 DTE a contract cannot avoid an announcement, so "owning the event" is not
a design choice; at ~15 DTE it is.

---

## 2. THE DESIGN

**ENTRY.** On the session **5 trading days before** a scheduled announcement, sell **one
cash-secured put** nearest **25 delta** (solved on the put leg, `SELL-PREMIUM-2`'s convention, no
moneyness band — `T3` measured that a band deletes 37.47% of picks and systematically the
closest-to-the-money ones). **Expiry: the nearest listed expiry 1–15 calendar days AFTER the
announcement.** **Hold to expiry. No management.**

**THE EVENT SPINE** is `valuation/edge/event_spine.py` on the **code-22** dates
(`bulk.earnings_dates`), whose identification `bulk.py:265-278` records by two independent
signatures. **Density is measured, not assumed:** `bulk.py` warns ~2.83 code-22 dates per
ticker-year repo-wide while `O6`/`O7`/`O17` measured **median 3.96 / mean 4.14** on the megacap
book; this draft's own 2018 sample reads **4.83 per name-year**.

**THE 29 FOREIGN PRIVATE ISSUERS HAVE NO EARNINGS DATES AND MUST BE DROPPED AND COUNTED, NEVER
READ AS "NO ANNOUNCEMENT".** `O7` measured them at **388 trades, 10.0% of its book**, every one a
20-F/6-K filer. `event_spine.refuse_within` and `owns_the_event` return **`None` for UNKNOWN** and
the caller must drop — a filter that reads `None` as "no event" **fails open on a non-random tenth
of the book**, which is the mode `O6`/`O7`/`O17` refused once already.

**TWO SPINE FACTS THAT BIND THIS DESIGN, AND THE SECOND BLOCKS THE FORWARD RUNG.**

1. **THE EVENTS DATE IS THE FILING DATE, NOT THE EVENT DATE** (`SHARADAR_REFERENCE.md:123`), and
   code 22 is SEC Form 8-K **Item 2.02, "Results of Operations and Financial Condition"** — *"not
   literally 'earnings announcement'"*. For 8-K 2.02 the filing is normally same-day or next-day,
   **but "5 sessions before the announcement" is 5 sessions before a FILING STAMP**, and the
   register must measure the filing-to-move lag rather than assume it. **`O7`'s own author fell
   into the adjacent trap and recorded it:** its first cut took the first expiry at DTE ≥ 7, which
   *"prices the move TO EXPIRY (often 30+ days) while the realised move is measured over ~4 days
   … inflated the mean implied move to 20.19% against a realised 5.27% and manufactured a RICH
   reading by construction."* **The 1–15-day expiry rule above exists because of that correction**,
   and the same discipline applies to the entry offset.
2. **THE SPINE HOLDS NO FORWARD DATES — 385,426 code-22 rows, latest 2026-07-29, none forward** —
   and that is exactly why `F-4` *"as declared enters nothing, ever"* and earned the harness state
   `RULE_ARMED_NEVER_FIRES`. **So the backtest rungs work and the FORWARD PAPER BOOK DOES NOT,
   without a forward earnings calendar this project does not have.** Stated here rather than
   discovered at the fleet: **EARNINGS-CSP can complete stage 1 and stage 2 and cannot complete
   stage 3 on today's data.** A forward calendar is a free-data question (several vendors publish
   one) and it is **a prerequisite, not a detail**. Earnings events also **do not exist before
   2004-08-23** (`SHARADAR_REFERENCE.md:108`), which is irrelevant here only because the options
   era starts in 2016.

**UNIVERSE.** The **point-in-time** $10B tier at the entry date, never ever-in-tier; optionable.
**PRICE BASES, both directions:** the **as-traded** series for strikes, moneyness and settlement
(`O-1`'s MNST 3-for-1 booked a fake **+1453%**); the adjusted series for any return on the
underlying (`V6`'s `C5`). **RAW chain layer only** — `options_derived` is two-sided on **1.0000**
of its rows **by construction** (`MB21`'s `C1`).

---

## 3. THE FREE PRE-OUTCOME KILL, AND IT IS THE BEST PART OF THIS DRAFT

**THE WHOLE DESIGN TURNS ON ONE UNMEASURED QUANTITY: THE PAYOFF RATIO OVER AN EARNINGS EVENT** —
`E_physical[payoff] / price` for the put being sold. `SELL-PREMIUM-2` **measured 0.4910 on dip
events** (expected payoff 0.008523 of strike against a market mid of 0.017358), i.e. the seller
keeps 50.9%. **Nobody has measured it over earnings**, and the design's power is a function of it:

| payoff ratio | edge at IV 0.35 | **IV 0.45** | IV 0.55 | IV 0.70 |
|---|---|---|---|---|
| **0.4910** (dip-event, MEASURED) | +0.3716% | **+0.5557%** | +0.7475% | +1.0499% |
| 0.70 | +0.1317% | **+0.2402%** | +0.3532% | +0.5315% |
| 0.80 | +0.0169% | **+0.0892%** | +0.1646% | +0.2834% |

*(25-delta put, 15 calendar DTE, net of ONE crossing at the measured 0.2127% of strike, as a
fraction of strike.)* **Against an 80%-power MDE of 0.5524pp at n = 1,500** (§4), the edge runs
from **1.0× down to 0.16× of its own detection threshold** across that range. **At a ratio of 0.70
or worse the arm is underpowered by construction and must not run** — `DIP-CALL`'s failure mode,
and the one this project pays for most often.

**`K1` — MEASURE THE RATIO FIRST, ON `O7`'s OWN 6,013 BANKED EVENTS, FOR FREE.** `O7` already
holds the implied move and the realised move per event. For a put struck where 25 delta sits, the
risk-neutral price follows from the implied and the physical payoff from the realised settle, so
**the ratio is computable from banked columns with no new data, no option quote, and no forward
return beyond the one `O7` already read.** `DC-1`'s shape — a kill that tests the register's
**premise** rather than its hypothesis — and `DC-1` booked **zero trials** for exactly that.

> **PRE-COMMITTED: the arm runs only if the measured earnings payoff ratio is ≤ 0.65. Above it, the
> register STOPS and reports the ratio.** That is a cheap, decisive, honest outcome and it is the
> most likely one.

**AND THE DIRECTIONAL PRIOR IS STATED, WITH ITS FRAGILITY.** `V6-OPT` measured dip-event implied
**0.430** against realised **0.389** — a vol ratio of **0.905** — which produced a payoff ratio of
**0.4910**. Extrapolating that convexity (`0.905^x = 0.4910` ⇒ `x ≈ 7.1`) to `O7`'s earnings vol
ratio of **0.8764** would give **≈ 0.39**, i.e. *better* than the dip book. **That extrapolation is
a power law fitted to ONE point and an earnings move is a JUMP rather than diffusion**, so it is
offered as the reason the kill is worth running and **not** as a forecast. It is also why §8 prices
`K1` as a coin flip rather than a formality.

---

## 4. COVERAGE AND POWER — MEASURED ON A BOUNDED SAMPLE, AND THE REGISTER RE-MEASURES IT

**FEASIBILITY IS ESTABLISHED, which was not obvious: a put expiring just after an announcement
usually exists.** On a 12-name random sample of the build-quadrant $10B tier with 2018 chains:
**53 scoreable code-22 dates, of which 26 — 49.06% — carry a usable two-sided put expiring 1–15
days after the announcement** inside a 0.85–0.99 moneyness band. **That is 2.9× the 17.1% a
25–45 DTE / 0.85–0.95 filter returned on the same year** (`SELL-PREMIUM`'s funnel), because short
weeklies are more densely listed near the money.

**THE EVENT-COUNT ESTIMATE: 187 of 459 build-tier half-0 names have both a 2018 chain and an
events row; at ~4.8 code-22 dates per name-year over four years and 49% coverage that is roughly
1,760 priceable events — call it 1,200 to 1,800**, since 2016–2018 carry the `oi_degraded` markers
and 2019 does not. **`K2` re-measures it on the register's own rule with a floor of 900 events and
250 covered days**, below which the register stops (`O-1`'s lesson: coverage on the arm's own
population, never inherited).

**POWER, hurdle DERIVED not quoted** — options `N` is **323**, so `sqrt(2 ln N)` is **3.3993094**
today and will have moved:

| n | MDE80 | | effect | n needed at 80% |
|---|---|---|---|---|
| 1,200 | 0.6176pp | | +1.0000pp | 458 |
| **1,500** | **0.5524pp** | | **+0.6709pp** | **1,017** |
| 1,800 | 0.5043pp | | +0.5000pp | 1,831 |

**THE SD IS BORROWED AND THE DIRECTION OF THE ERROR IS NAMED.** 5.047pp is `SELL-PREMIUM-2`'s
measured per-trade SD at **37 DTE on dip events**. An earnings-spanning put is **shorter** (less
premium, lower SD) but **spans a jump** (fatter tail, higher SD), and **which dominates is not in
the record**. `MB8` forbids borrowing an se across constructions, so **the register measures its
own and reports its own MDE** — and if the realised SD is materially above 5.047 the power table
above is optimistic.

---

## 5. THE GAP STRESS, NAMED — AND IT IS WHY THIS EVENT IS BETTER THAN THE DIP EVENT

**THE SINGLE-NAME GAP IS THE OBVIOUS RISK AND IT IS NOT THE DANGEROUS ONE.** An earnings
disappointment can gap a name 20–30% overnight, which is exactly what the put seller is paid for.
**`GAP-1`, pre-committed:** report the realised per-trade return at the **p01, p05 and worst**
observed outcome, the share of trades assigned, and the **worst single-name loss in dollars at the
offered account sizes.** No bar — it is a disclosure, because a one-sided bar on an order statistic
is `R1-VAR`'s `n = 1` problem.

**THE DANGEROUS RISK IS THE ONE THAT KILLED `SELL-PREMIUM-2`'s CHECK READ, AND THIS EVENT IS
STRUCTURALLY BETTER ON IT.** The corrected stage 2 (§87b) found **the whole loss was COVID** —
**2020 −2.7788%** on 1,220 trades at 33.52% assignment, 2021 −0.3830, and **2022–2026 all positive
(+0.5109, +0.5998, +0.3660, +0.7575, +1.1999)** — failing clause (a) only because the early half
contains the crash. **The mechanism is that a dip-conditioned entry fires on drops, so the book is
fully loaded going into a crash**: at k = 2.5 the worst ten days carry **14.05%** of all dip events.

> **AN EARNINGS DATE IS SET BY A COMPANY'S FISCAL CALENDAR AND IS NOT CONDITIONED ON MARKET STRESS.
> THAT IS THIS DRAFT'S STRONGEST STRUCTURAL CLAIM: THE ENTRY RULE CANNOT LOAD THE BOOK INTO A
> CRASH, BECAUSE IT DOES NOT KNOW WHERE THE MARKET IS.**

**AND THE HONEST OTHER HALF, BECAUSE THE CLAIM IS NOT UNCONDITIONAL: earnings cluster in four
reporting seasons, and a market-wide crash can land inside one** — Q1 2020's season ran through
April 2020, immediately after the −32.61% 32-session SPY move. **So the diversification is against
STRESS-CONDITIONING, not against calendar concentration.** `GAP-2`, pre-committed: report the
**maximum number of concurrently open positions** and the **book's worst calendar month**, with the
share of events falling in the worst single week — the dip census's own statistic, computed on this
event set so the two are comparable.

---

## 6. THE TWIN — Don's clause (b), on the same names at the same tenor

**`A2`: the identical structure on a RANDOM day in the same name-year, matched on tenor.** Five
seeds minimum (`R2`: one seed flipped that verdict), paired **name-year** sign test as the verdict
statistic, as `SELL-PREMIUM-2` and `R2` both rest on.

**THE TENOR MATCH IS LOAD-BEARING HERE IN A WAY IT WAS NOT FOR THE DIP BOOK.** `O13` measured
expectancy rising with tenor on **both** the alert book and the random-day control, so **a twin at
a different tenor would measure tenor rather than timing.** The twin therefore draws its expiry by
the same 1–15-days-after rule applied to a random pseudo-date, giving the same DTE distribution.

**AND THE TWIN IS WHERE THE `F-4` CONTRAST LIVES.** `F-4` is the same trade **deliberately avoiding
events**. If `A2` clears and the realised edge is concentrated in the event window, that is the
same fact `F-4` was built to measure from the other side — **and `F-4` has never filled**, so no
contrast is available from it today.

---

## 7. ARMS, BARS, TRIAL COUNT

**3 OPTIONS TRIALS, BH AT q = 0.10 ACROSS k = 3** — thresholds **0.0333 / 0.0667 / 0.10**,
membership fixed here before any arm runs. **Every critical value LABELLED UNCALIBRATED** (`V2G`,
`R1-VAR`). Halves of the **covered subsample** with the boundary embargoed (`S18`, `U2`, `U3`,
`V6-OPT`, `SELL-PREMIUM-2` — the same substitution, five times, because the cache begins in 2016).

| arm | question | bar |
|---|---|---|
| **`A1`** | profitable net of **one** crossing on secured cash, **in both halves**? | **> 0 in both halves** — Don's clause (a) |
| **`A2`** | beats the **same tenor** on random days in the same names? | paired name-year sign test, five seeds — clause (b) |
| **`A3`** | survives `O11` sizing and concurrency? | all cells reported; **the offered configuration must not lose money** — clause (c), and `SELL-PREMIUM-3`'s $10k row is why this is explicit |

**`K1` AND `K2` RUN FIRST, IN THEIR OWN PASS**, with the arm runner **refusing** without a passing
artifact (`O10`'s process defect: the gate and the outcomes computed in one pass cannot be claimed
to have been read in order).

**NO `K3`-STYLE CRASH-ARITHMETIC BAR, AND REFUSING ONE IS DELIBERATE.** `SELL-PREMIUM-2`'s stage 2
is the reason: its `K3` **cleared at 3.4170 years against the 6.0 bar — better than stage 1 — and
the crash then produced the worst year in the book.** Its own void condition 7 had said so in
advance (*"`K3` is a stress ARITHMETIC, not an outcome"*), and §87 records that it *"earned its keep
in the most expensive way available"*: a single-episode loss divided by annual income **cannot see
serial losses, assignment compounding, or a book that is fully loaded going in.** **So this register
replaces it with the two measured disclosures of §5 and claims no crash bar at all** — which is
weaker and honest, rather than a number that passed and meant nothing.

---

## 8. VOID CONDITIONS, EXPECTATIONS, AND WHAT THIS DOES NOT SAY

**VOID CONDITIONS.** (1) No grid: one entry offset (5 sessions before), one strike rule (25 delta),
one expiry rule (nearest 1–15 days after), one tenor. (2) Reading `None` from the event spine as
"no announcement". (3) Running the arm with a measured payoff ratio above 0.65. (4) A twin at a
different tenor. (5) Quoting `O7`'s straddle figures as this register's own — different structure,
different universe, four crossings against one. (6) Any exit management. (7) Claiming a crash bar.
(8) Reading a stage-2 pass as a blind confirmation (§0).

**EXPECTATIONS, priced now so they can be scored.**
1. **`K1`'s ratio comes in at or below 0.65: 50/50.** The convexity extrapolation says 0.39 and it
   is a one-point fit on a diffusion model applied to a jump. **This is the coin flip the whole
   draft rests on, and it is cheap to resolve.**
2. **`K2` clears its 900-event floor: 75/25.** The 49.06% sample coverage is well above what the
   dip book got and the floor is deliberately half the estimate.
3. **`A1` clears both halves: 40/60.** `SELL-PREMIUM-2` cleared stage 1 and then failed its check
   on one crash; an event that cannot load into a crash should do better, **but the edge per trade
   is thinner and the tail is a jump.**
4. **`A2` clears: 55/45.** The event is scheduled and public, which is an argument *against* a
   timing edge — the market knows the date. **What is being sold is the vol premium, not surprise**,
   and `O7` measured the premium over the whole window.
5. **The whole register passes every leg: 20%.**
6. **Don adopts it: 10%.**

**WHAT THIS DOES NOT SAY.** It is **not** a finding that selling earnings premium works — no arm
has run. It does **not** re-open `O9`, whose object was index vol-timing. It does **not** claim
`O-SEED-5` was wrong **when written**: its inference from `O9` was reasonable and has since been
contradicted by `SELL-PREMIUM-2`'s stage-1 pass, and its cost arithmetic remains correct **for a
two-leg structure**. It does **not** re-open the alert entry, which `DECISIONS.md` 2026-10-16
closes (*"it loses to random days in every score band and at every threshold"*) and which appears
nowhere in this design. And it proposes **no trade**: `O11` binds, nothing here licenses real money,
**adoption is Don's and is a vintage event**, and the last rung is a forward paper book that
**cannot start until the fleet is on Alpaca** (`DECISIONS.md` 2026-10-16).

**NOT DONE:** no register committed, no arm run, no option priced, no trial booked, no
check-quadrant read, **`K1`'s ratio — the number the design turns on — is unmeasured**, and
**stage 3 is blocked on a forward earnings calendar that does not exist in this project** (§2).
