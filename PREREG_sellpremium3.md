# PRE-REGISTRATION — SELL-PREMIUM-3 — the dip entries as a 25-delta put credit spread

**COMMITTED ALONE, MARKDOWN ONLY, ZERO `.py`, AND A STRICT GIT ANCESTOR OF EVERY MEASUREMENT
COMMIT.** `RESEARCH_CHARTER.md` §3. Executes the Frontier Scout's `PREREG_DRAFT_sellpremium3.md`
(`a1d37ff`) under `DECISIONS.md` 2026-10-14, *"SELL-PREMIUM-3 IS TESTED AS DRAFTED … Its
construction is frozen at the draft `a1d37ff`, which predates every check-quadrant read."*

**Paper only. `O11` binds. Nothing here licenses a real order, and adoption is Don's and is a
vintage event.**

---

## 0. THE DISCLOSURE, FIRST, BECAUSE IT CHANGES WHAT A PASS WOULD MEAN

> **THE CHECK QUADRANT IS NOT BLIND TO THIS BOOK.** `SELL-PREMIUM-2`'s corrected stage 2 has
> already read **the same entries' short legs on the same 2020-2026 × ticker-half-1
> population**. Those figures are on the record: **−0.4258%/trade** (date-clustered *t* −0.725),
> the loss sitting in **2020** with 2021 slightly negative and **2022-2026 positive**, and the
> random-day twin beaten on the paired name-year sign test at **z +12.5336**.

**THE CONSTRUCTION NEVERTHELESS PREDATES THAT READ, AND IT IS VERIFIABLE FROM GIT RATHER THAN
ASSERTED:**

| commit | timestamp | what it is |
|---|---|---|
| `a1d37ff` | **2026-10-13 18:18:05 −04:00** | the draft that freezes this construction |
| `a525fa6` | **2026-10-13 20:05:43 −04:00** | the FIRST stage-2 commit (the void run) |
| `6feddad` | **2026-10-14 00:05:09 −04:00** | the CORRECTED stage-2 read quoted above |

The draft precedes the first stage-2 commit by **1 hour 47 minutes 38 seconds**, and the
corrected read — whose numbers §0 quotes — by **5 hours 47 minutes**. So **no parameter of this
construction can have been chosen on any check-quadrant outcome**, and `DECISIONS.md`'s *"no
amendment may be informed by that read"* is honoured by the amendments in §2, each of which is
justified below **without reference to any check-quadrant figure**.

**WHAT FOLLOWS, STATED NOW SO IT CANNOT BE SOFTENED AFTERWARDS: A STAGE-2 PASS HERE WOULD BE
CONSISTENT WITH THE DRAFT AND WOULD NOT BE A BLIND CONFIRMATION.** A capped-loss version of a
book whose only loss sat in one already-known crash is **predictable** from what is already on
the record — the cap truncates exactly the episode that produced the loss. A stage-2 pass must
therefore be reported as **ELIGIBLE-BUT-UNRESOLVED (CHECK WINDOW PREVIOUSLY SEEN)** and may
never be described as an out-of-sample confirmation. **A stage-2 FAILURE carries its full
weight**, because nothing about the prior read predicts a failure here. The asymmetry is
declared before the run.

---

## 1. THE OBJECT, FROZEN

The **same dip entries** as `SELL-PREMIUM-2` and `DIP-CALL-2`, expressed as a **put credit
spread**:

* **EVENT** — `DIP-CALL-2`'s, verbatim: a daily return at or below **−2.5×** the name's own
  trailing 60-session return volatility taken `shift(1)`, on the **point-in-time $10B tier** at
  the event date, never ever-in-tier.
* **SHORT LEG** — the put nearest **25 delta**, solved on the put leg, **no moneyness band**.
* **LONG LEG** — the nearest listed strike **at or below `K_short − 0.075 × spot`**, **REFUSED**
  if the realised width falls outside **[5%, 12.5%]** of spot. **One width. No grid.**
* **TENOR** — **20-60 DTE**, the predecessor's band.
* **EXIT** — **hold to expiry, no management.** Any exit rule is a void condition.
* **ASSIGNMENT BAND** — short assigned and long worthless: **the shares are SOLD**, at this
  project's measured **33.4 bps** one way on the short-strike notional. **Exercising the long
  put instead is REFUSED BY NAME** — it locks the full width even when `S > K_long`.
* **PRICE BASES** — the EVENT on the adjusted series (`V6`'s `C5`); the **STRIKES, moneyness and
  settlement** on the **as-traded** (`O-1`). **RAW chain layer only** (`MB21`'s `C1`).

---

## 2. AMENDMENTS — CORRECTNESS ONLY, EACH NAMED AND EACH JUSTIFIED WITHOUT A CHECK-QUADRANT FIGURE

**A1 — THE REPAIRED SETTLEMENT, ON BOTH LEGS.** `settlement_spot` is called with the required
`max_stale_days`, and `spot_maps` is built from **the years the trades span**, never an era
constant. **Justification is a defect, not an outcome:** the void stage-2 run settled **73.02%**
of its book at each ticker's 2020-12-31 close because it imported a 2016-2020 map, and a
two-legged book inherits that exposure twice over. **Refusals are COUNTED.** A test must fail on
the old era-import code.

**A2 — THE HURDLE IS DERIVED FROM THE LIVE OPTIONS `N` AT RUN TIME, NEVER THE DRAFT'S 319.**
`MA19`'s rule. The draft's own §9 says the figure *"will have moved"*, and it has: `N` is **319**
before this register's booking and **323** after it, so the hurdle moves **3.3956416 →
3.3993094**. Nothing may quote a hurdle it did not derive.

**A3 — MEASURED WHERE THE DRAFT FORECAST.** The draft's own **void condition 6** already
forbids computing `K3` from its §3 Black-Scholes table, and the draft names three reasons its
own forecast flatters the spread (BS at the median IV; the long leg priced at the short leg's IV
despite put skew; the long leg's physical tail scaled by the short leg's haircut). **Every
return and both crash bars come from the MEASURED net credit at the measured strikes.**

**A4 — THE CAPITAL DENOMINATOR IS REPORTED TWICE, AND THE REGISTERED ONE IS THE DRAFT'S.**
The draft defines spread capital as `(width − credit) × 100`. **Fidelity — the only custodian
whose rule §8 could settle from a primary page — publishes the credit-spread requirement as the
GREATER of the strike difference and the premium difference, i.e. the FULL width with no credit
netted.** The registered statistic stays the draft's (this register tests the draft); the
**account-size table of §6 carries BOTH columns**, because that table is the one a reader would
act on. **This is a broker-rule fact and is independent of every outcome.**

**NOTHING ELSE MOVES.** One width, 25 delta, the tenor band, hold to expiry, shares sold in the
middle band, `K3-POS` at **6.0** with the synthetic single-name row, `K3-ACCT` at **35%**, and
the expectations scored exactly as the draft wrote them.

---

## 3. §8 ANSWERED FIRST, FROM THE BROKERS' OWN PUBLISHED PAGES — **RESOLVED: YES**

The draft makes this a **free kill**: *"if no broker Don can use permits spreads in his Roth at
his account size, the whole program is unbuildable."* **It does not fire.** Read 2026-10-14;
**Tradier and Robinhood are excluded by `DECISIONS.md` 2026-10-08 and were not consulted.**

* **FIDELITY — PERMITS IT, and is the one whose numbers could be read from a primary page.**
  `https://www.fidelity.com/webcontent/ap002390-mlo-content/18.04/help/learn_trading_options.shtml`
  and `https://www.fidelity.com/options-trading/faqs`: spreads up to four legs are listed as an
  IRA strategy and require **Tier 2** plus a **Spreads Agreement**. The **Cash Spreads Reserve
  Requirement is $2,000**, and the page states it is *"a one-time assessment and must be
  maintained while you hold spreads in your retirement account"* — **PER ACCOUNT, not per
  spread**, which is the distinction that decides whether this strategy is fundable at all.
  *"Credit spread requirements can be met by the minimum cash reserve up to $2,000. If the
  spread requirements are greater than $2,000 you must have the available cash."* The credit
  requirement itself is the greater of the strike difference and the premium difference, times
  contracts times 100.
* **SCHWAB — PERMITS IT.** Schwab publishes a document titled **"Supplemental Application and
  Agreement for Limited Margin and Trading Option Spreads in Your IRA Account"**
  (`https://www.schwab.com/resource/supplemental-application-and-agreement-for-margin-and-option-spreads-in-ira`);
  **the title is itself the answer.** IRAs are capped at **Level 2**, which includes spreads.
  The body could not be fetched (Schwab returns an authorisation error to an automated reader),
  so the level and the application are recorded and **no Schwab dollar figure is quoted.**
* **TASTYTRADE — PERMITS IT, approval not guaranteed.** Its published account material states
  IRAs are provisioned as **limited margin** accounts *"to allow suitable investors to trade
  defined-risk options trades"*, with approval required.

**THE HONEST LIMIT: only Fidelity's dollar figures were obtainable from a primary page**, and
**no broker's rule was confirmed against Don's own account**, which is a conversation with a
custodian rather than a measurement. **What §8 establishes is that the program is BUILDABLE** —
the gate was *"if EVERY candidate clearly refuses"*, and none does.

**AND THE FORWARD-BOOK ROUTE REMAINS BLOCKED SEPARATELY**, as the draft says: the fleet's
sandbox is Tradier's, and Tradier is closed. **A pass here cannot be paper-traded by the fleet
as it stands.**

---

## 4. ARMS AND BARS — **4 OPTIONS TRIALS, BOOKED BEFORE ANY RUNNER EXISTS**

Benjamini-Hochberg at **q = 0.10 across k = 4**, thresholds **0.025 / 0.05 / 0.075 / 0.10**,
membership fixed here. **Every critical value is LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`).
Halves of the **covered subsample** with the boundary **embargoed** (`S18`, `U2`, `U3`,
`V6-OPT`). Standard errors clustered on **event date AND ticker**, clearing required under both.
**Every verdict travels with its 80%-power MDE, computed as `(crit + 0.84) × se` from the arm's
OWN measured se** (`MB22`, `MB8` — never a borrowed one).

| arm | question | bar |
|---|---|---|
| **`B1`** | profitable net of **both** entry crossings **and** the assignment-band equity round trip, on capital at risk, **in both halves**? | **> 0 in both halves** — Don's clause (a) |
| **`B2`** | beats the **SPREAD twin** at the identical width rule on random days in the same names? | paired name-year sign test on **DOLLARS**, five seeds, **pooled means reported beside it** — clause (b) |
| **`B3`** | does the spread beat the **naked** book per dollar of capital on the identical events? | paired difference, **own se measured**, MDE80 reported |
| **`B4`** | is the realised edge positive across **5%-12.5%**? | **SENSITIVITY, NO VERDICT** — a width sweep is a grid and the declared rule is 7.5% |

**THE THREE-STATE VOCABULARY IS THE CHARTER'S AND IS FIXED HERE: `CLEARS` / `NOT CONFIRMED` /
`UNDERPOWERED`.** An arm whose observed effect sits below its own 80%-power MDE and whose
interval straddles zero is **UNDERPOWERED**, never a null (`V6`, `S19`).

---

## 5. THE KILLS, IN THEIR OWN PASS, READ BEFORE ANY ARM

**`K1` — COVERAGE ON THIS REGISTER'S OWN TWO-LEG RULE.** A spread needs a usable two-sided quote
on **TWO** legs, so its coverage is **strictly worse** than the short leg's and `O-1`'s lesson
forbids inheriting `SELL-PREMIUM-2`'s 2,610. **Floor: 1,200 priceable events AND 300 covered
days. Below either, the register STOPS and no arm runs.**

**`K3-POS` — 6.0 years of premium, UNRELAXED, synthetic single-name row RETAINED.**

**`K3-ACCT` — the account-level loss in a 32.6% month may not exceed 35% of the account.** 35%
is **inherited and not chosen**: it is `SELL-PREMIUM-2`'s own measured exposure at $25k.

**The deployment cap is 35% of account equity at risk across all open spreads**, enforced at
order time, with the refusal recorded as its own reason (`MB3`: affordability is never ruin).
**`O11`'s concurrency caps of 10 and 50 stay as a second, independent limit** — whichever binds
first.

**THE ARM RUNNER REFUSES TO START WITHOUT A PASSING KILLS ARTIFACT** (`O10`'s process defect).

---

## 6. THE ACCOUNT-SIZE TABLE IS A REQUIRED LEG

**$10k, $25k and $50k**, on the **one repaired current-equity sizing loop** (sized from CURRENT
equity, stopping at ruin, with RUINED recorded as its own state). **Both capital denominators
per A4.** **ONLY the 35%-cap rows are offered configurations; the 100%-deployment rows are shown
IN ORDER TO BE REFUSED**, and quoting one as an offered configuration is a void condition.

---

## 7. VOID CONDITIONS

1. No grid: one width rule, one strike rule, one tenor band, one `k`.
2. `K3-POS`'s 6.0 and the synthetic row may not be relaxed; `K3-ACCT`'s 35% may not be raised.
3. No exit management of any kind.
4. Exercising the long put on assignment instead of selling the shares.
5. A fixed **dollar** width.
6. `K3` or any return computed from the draft's §3 forecast table rather than measured credit.
7. Comparing this register's coverage to `SELL-PREMIUM-2`'s 2,610 without saying one is a
   two-leg filter and the other one-leg.
8. Reporting the twin comparison on return-on-capital alone.
9. Quoting any 100%-deployment row as an offered configuration.
10. **Describing a stage-2 pass as a blind out-of-sample confirmation** (§0).
11. Quoting a hurdle that was not derived at run time (A2).

---

## 8. EXPECTATIONS, SCORED EXACTLY AS THE DRAFT WROTE THEM

1. `B1` clears in both halves: **60/40**.
2. `B2` clears: **50/50**.
3. `B3` shows the spread beating the naked book per dollar of capital: **85/15**.
4. `K3-ACCT` clears at the declared 35% cap: **90/10** (near-tautological, scored low-information).
5. `K1` clears its 1,200-event floor: **55/45**.
6. The whole register passes every leg: **30%**.
7. Don adopts it: **10%**.

---

## 9. WHAT THIS DOES NOT SAY

It is **not** a finding that spreads work — no arm has run, and **`A3`'s level still stands**: a
managed 20-delta credit spread returned **+0.13% of max risk, PF 1.02**, negative in its first
half. This register's answer to `A3` is that it had **no dip timing** and **four crossings with
a stop** where this has two and none; **it is not that `A3` was wrong.** It does **not** re-open
`SELL-PREMIUM-2`, whose corrected stage 2 is **NOT CONFIRMED** and stands. It makes **no claim
about index spreads**. And it proposes **no trade**.
