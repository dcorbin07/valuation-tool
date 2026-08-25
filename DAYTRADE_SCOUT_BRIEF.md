# DAYTRADE_SCOUT_BRIEF.md — breadth for the intraday sibling project
## Prepared by the Valquo Frontier Scout, 2026-08-25, for Don to relay.
## **Every entry is a candidate for THEIR register process. Nothing here is a recommendation,
## a direction, or a finding about their data.**

---

## 0. THE FENCE — non-negotiable, and stated first because it governs everything below

* **METHODS, LITERATURE, PATTERNS and Valquo's FINDINGS cross freely.** This is the TIDEMARK
  precedent applied in the other direction: *method crosses, data does not.* Everything in §1 is
  a finding about **Valquo's** book, offered as evidence they cannot otherwise buy.
* **Valquo's LICENSED DATA never crosses** — no Sharadar export, no ThetaData chain, no WRDS row,
  no tick cache. Not a sample, not an aggregate derived from a licensed row that would let one be
  reconstructed. **Their repo touches none of it.**
* **TRIAL COUNTERS never cross. Their N is theirs and starts at zero.** Valquo's hurdles
  (equity 3.3133, options ~3.38) are properties of Valquo's search and mean nothing in their
  register. Quoting ours at them would be an error in the *punitive* direction, which is the
  only reason it is worth saying twice.
* **I do not direct that project and do not touch its ledger.** Their mentor owns it. I am a
  supplier of breadth. If an entry here conflicts with their charter, their charter wins without
  discussion.
* **No outcome statistic was computed on anyone's data — theirs or ours — anywhere in this file.**

---

## 1. WHAT VALQUO'S GRAVEYARD ALREADY SAYS ABOUT SHORT HORIZONS
### ~550 pre-registered trials, one adoption. This is the part nobody else can give them.

**Tags: TRANSFERS · PARTIAL · DOES-NOT-TRANSFER · UNKNOWN · HANDOFF.**

### 1a. The toll — the most valuable thing in this document

| finding | what it closed | what it did NOT close | tag |
|---|---|---|---|
| **`O18`: ρ = 0.6743** — a real trade pays **~67% of the quoted half-spread**, CI95 [0.6617, 0.6871] | that "assume the mid" and "assume the full spread" are both wrong, by a measured amount | it was measured on **~60-DTE, 35-delta options**, not equities. The *number* is an extrapolation off-asset; the *method* (measure your own ρ from your own fills before trusting any cost assumption) is the transfer | **TRANSFERS (method), UNKNOWN (level)** |
| **`O13`: `entry_spread_pct` q5 = −7.41%** — the widest-spread quintile of entries lost most, by a wide margin | any design that treats spread as a cost to subtract afterwards rather than a **screen to apply first** | it does not say *where* the cutoff belongs — that is theirs to census | **TRANSFERS** |
| **`D9`/`B11`: equity book 37bps measured cost against a 236bps breakeven — a 6.4× cushion at quarterly rebalance** | nothing — it is the reference point | **the cushion is a function of turnover and it inverts at intraday frequency.** Same cost, ~60× the trades, a far smaller per-trade edge | **TRANSFERS as the governing arithmetic (§4)** |
| **`O11`: expectancy −4.51% in quiet weeks vs +14.28% above the 90th-percentile week; 51.5% of trades in >10-alert weeks; a cap-10 $50k book ends BELOW its start** | the assumption that a positive-expectancy signal is a tradeable one | it is about **capacity refusing the cluster** — signals arrive bunched and limited buying power declines exactly the best ones. Intraday signals cluster harder, not less | **TRANSFERS, and it is the most under-appreciated entry here** |

### 1b. The data-integrity kills — every one of these bit a real result

| finding | the lesson, in their language | tag |
|---|---|---|
| **`B2` — exit-path quote censoring: stop days were censored EXACTLY when the stop fires** | **The single most important entry for a day-trading project.** Stops are the core intraday control, and the data was missing precisely on the days the stop mattered. *Prove your bar data exists on the bars your stops trigger on, before you trust one stop result.* | **TRANSFERS** |
| `B6` — panel truncation, the largest single correction in the audit | date-range bugs beat signal bugs for total damage | **TRANSFERS** |
| `B12` — the universe was an **alphabetical slice** for an entire era | every result from that era measured a slice, not the market — see 1d, it is why one "kill" below is not a kill | **TRANSFERS** |
| `B1`/`U1-SPLIT` — as-traded vs adjusted prices; **raw_close for anything touching a strike** | intraday bar vendors differ on split/dividend adjustment, silently. Pick one convention per use and pin it | **TRANSFERS** |
| `B3` — stale-quote expiry marks; `LA7` — a **Saturday** returned as "fresh" | session/calendar hygiene: half-days, holidays, DST, auction windows, and the difference between "no data" and "no trading" | **TRANSFERS** |
| `B5` — four paper-track defects, **every one flattered the track**; `MA36` — a settlement convention that was right for longs and wrong by a sign for shorts | your paper track's bugs will not be randomly signed. Assume flattery until each is checked | **TRANSFERS** |
| `B15`/`B19` — commission inside `return_pct`; Sharpe at rf = 0 | accounting conventions decide headline numbers; state each once, in one place | **TRANSFERS** |

### 1c. The method imports — cheap, and the most durable things Valquo built

| instrument | why it matters at intraday frequency | tag |
|---|---|---|
| **`MB22` — state your MDE before running, at BOTH 50% and 80% power** (`(crit+0.84)×se` is 1.42× `crit×se`) | Valquo published only 50%-power figures for years and called them MDEs; `S19`, `V6`, `MA58-SEAS` all returned nulls their designs could not have distinguished from real effects. **Intraday n is large, so their MDEs will be small — which makes the discipline cheap to adopt and expensive to skip** | **TRANSFERS** |
| **`MB21` — persistence-preserving nulls.** Valquo's placebo permuted within dates and had **zero** autocorrelation against a real signal at **0.5677** | Intraday data has strong autocorrelation *and* U-shaped seasonality in volume and volatility. **A null that destroys time-of-day structure cannot generate the artifact it most needs to exclude** — this is the trap most intraday backtests fall into | **TRANSFERS, with force** |
| **`X7` — calibrate your own floors.** Three of four of Valquo's thresholds were uncalibrated; the conventional t = 2.0 measured **2.14** on their data | inherited conventions are not floors. Permute, measure, then set the bar | **TRANSFERS** |
| **`M1` — book the trial counter from trial #1.** Valquo shipped a denominator of 8 while the honest count was 84, then 129, then 242 | **Their N starts at zero, which is a real advantage** — √(2 ln N) is ≈2.15 at N=10 and ≈3.03 at N=100. Retrofitting a denominator is painful and permanent; starting one is free today | **TRANSFERS — the single cheapest thing they can do this week** |
| `P3` — designing for a **35.3% hit rate** from a *measured* streak table, not the Bernoulli formula | intraday hit rates are low and payoffs skewed; derive drawdown/streak expectations from the realised sequence | **TRANSFERS** |
| **`MB3`/`O17C4`/`MB1` — mean vs median decides answers.** An effect was +4.79pp on means and **+0.40pp** on medians; a register once chose the one statistic already shown blind to its own effect | intraday P&L is skewed by construction. **Choose the statistic before the run and justify it against the payoff shape** | **TRANSFERS** |
| `O12` — Kelly `f*` = 0.0403 with a CI including zero → **NOT USABLE** | a point estimate of optimal size is not a size | **TRANSFERS** |
| `SC-1b` — stated priors came back **calibrated in the large** | writing a numeric prior per register costs nothing and is checkable later | **TRANSFERS** |

### 1d. The short-horizon "kills" — and what each one does NOT close

* **`R2` — the options alert's entry was WORSE THAN RANDOM (−5.06pp/trade), and `MB1`'s
  decomposition put ~79% of the loss in the DAY and ~21% in contract selection.** *What it
  closed:* that specific day-selection signal (unusual option volume vs open interest + low IV),
  on 186 optionable names, expressed as long calls. *What it did NOT close:* day-selection in
  general, any equity intraday signal, or any signal on a different universe. **But treat it as a
  strong prior that day-selection signals are weaker than they look**, because this one was
  worse than a coin flip against matched random entry. → **PARTIAL**
* **Short-term reversal.** Relayed as tested and rejected — **and `B12` means any result from
  that era ran on an alphabetical slice of the universe, not the universe.** A rejection measured
  on a slice is weak evidence, not a closure. **They should treat short-term reversal as OPEN and
  re-derive it themselves**, at daily horizon, with costs first (§2-C1). → **UNKNOWN — do not
  inherit this kill**
* **`O14` + `MB16` — six order-flow features (signed volume, sweep share, block share, P/C
  imbalance, unusual volume, quote-classified VPIN), all NULL.** *What it closed:* those features
  **on Valquo's own alert-day options tick cache** — 3,884 units, 186 symbols, median **2 names
  per date**, selected by the alert screen itself. *What it did NOT close:* equity order flow, at
  any horizon, on an unconditioned sample. The conditioning is the whole caveat and `MB15`'s own
  scope note says the sample is *"selected toward the retail-heavy tail... does not generalise to
  ordinary days."* → **DOES-NOT-TRANSFER (result) · TRANSFERS (method: `MB16` validated its
  classifier against a banked benchmark to 16 digits before testing anything)**
* **`MB15` — the venue axis died, and IT INVERTS FOR EQUITIES.** In options there is no
  off-exchange execution: wholesaler internalisation surfaces as an on-exchange price-improvement
  auction, and ThetaData's TRF venue codes (57/58/59) appeared in **zero of 70,288,482 prints**.
  **In equities the off-exchange TRF print is the standard retail identifier** — so the axis that
  is structurally dead in options is the live one in their asset class. **This is the most
  valuable inversion in the document.** → **HANDOFF**
* **`MB41` — intraday momentum, marked NOT-TESTABLE-HERE.** Valquo owns no equity tape and no
  index chain, so Gao–Han–Li–Zhou's first-half-hour → last-half-hour result could not be examined
  at all. **The question is passed to them intact, with its literature and its replication
  status** (§2-B1). → **HANDOFF**
* **`S22`/`S23`/the composite** — every horizon result is at **≥63 days**; the exit study found no
  conventional exit beats never-selling. Silent on intraday, and should be quoted at nothing.
  → **DOES-NOT-TRANSFER**

---

## 2. THE INTRADAY IDEA LIST
*idea · mechanism in a phrase · data · graveyard tag or VIRGIN. Cost verdict in §4, reachability
in §3. Literature is offered as **hypotheses** — this project has killed published results.*

### A · Overnight vs intraday decomposition (the richest vein reachable with daily data)
1. **Overnight-return persistence.** Firms' returns separate into an overnight and an intraday
   component with different signs across characteristics — Lou–Polk–Skouras, *A Tug of War*
   (JFE 2019). **Replication: well established; the decomposition itself is robust, the
   tradeable version is where costs bite.** Data: **CRSP daily (open/close) — testable now**.
   [VIRGIN for them · `MB41`-adjacent]
2. **Overnight momentum vs intraday reversal within the same name** — clientele/inventory story:
   overnight is retail- and news-driven, intraday is dealer-inventory-driven. Data: CRSP daily.
   [VIRGIN]
3. **Overnight gap fade vs continuation, conditioned on gap size and prior-day close position.**
   Data: CRSP daily OHLC. [VIRGIN · related to C1's reversal family]
4. **The close-auction imbalance proxy** — end-of-day price pressure from index/ETF flows,
   proxied by close-vs-VWAP or close-vs-high/low position. Data: daily OHLC now; true imbalance
   needs exchange feeds. [VIRGIN]

### B · Time-of-day structure
5. **Intraday momentum (first half-hour → last half-hour).** Gao–Han–Li–Zhou (*JFE* 2018);
   stronger on high-volume, high-volatility and macro-release days. **Replication: published and
   widely cited; later work finds the effect period- and market-dependent — treat as contested.**
   Data: 30-minute bars. [`MB41` HANDOFF — Valquo could not test it]
6. **The lunch-hour liquidity trough** as a cost regime rather than a signal — trade timing, not
   direction. Data: intraday bars or Intraday Indicators. [VIRGIN]
7. **Opening-range breakout** (the retail classic). **Essentially untested in the peer-reviewed
   literature, heavily marketed** — treat the absence of literature as a warning, not a moat.
   Data: intraday bars. [VIRGIN · hostile prior]
8. **First-30-minute reversal for names with overnight gaps** — overreaction to overnight news.
   Data: intraday bars. [VIRGIN]

### C · Reversal and liquidity provision
9. **Short-term (1–5 day) reversal, rebuilt honestly.** Jegadeesh (1990), Lehmann (1990);
   Avramov–Chordia–Goyal show profits concentrate in **illiquid** names — which is where costs
   are worst. **Replication: the raw effect replicates; net-of-cost profitability is contested
   and frequently negative.** Data: CRSP daily — **testable now**. [`B12`-caveated UNKNOWN — do
   not inherit Valquo's rejection]
10. **Reversal conditioned on WHY the move happened** (news vs no-news). No-news moves revert
    more — the inventory story. Needs a news source; free ones are weak. [VIRGIN]
11. **Liquidity provision on high-spread days for liquid names** — get paid the spread rather
    than pay it. **This is the one family whose economics improve with wider spreads**, and it
    inverts §4's arithmetic. Needs realistic fill modelling — see `O10`'s void. [VIRGIN ·
    `O10` warning]
12. **Pairs / cointegration intraday.** Data: intraday bars. Classic, crowded, and cost-heavy.
    [VIRGIN · hostile prior]

### D · Event-timed intraday
13. **Post-earnings first-day drift, entered at the open after the announcement.** Data: **IBES
    actuals for announcement timestamps + daily/intraday bars**. [`F-12` is Valquo's own forward
    version of this shape · PEAD-adjacent]
14. **Earnings announcement TIME-OF-DAY effect** (before-open vs after-close reactions differ).
    Data: IBES `anndats` + `anntims`. [VIRGIN]
15. **Macro-release windows** (CPI/FOMC/NFP) as a volatility regime for sizing, not direction.
    Data: public calendars, free. [VIRGIN]
16. **Index add/delete around the effective date.** The classic index effect. **Replication: the
    effect has decayed substantially since ~2000 — well documented.** Data: **Historical SPDJI
    (PIT membership) — testable now**. [VIRGIN · decayed-effect prior]

### E · Cross-asset and lead-lag
17. **Futures/ETF lead-cash lead-lag at minute horizons.** Requires synchronised feeds; at retail
    latency the lead is likely already arbitraged. [VIRGIN · hostile prior]
18. **Sector-ETF flow as a component signal for constituents.** Data: ETF daily/intraday bars.
    [VIRGIN]
19. **VIX term-structure state as an intraday risk gate.** Free data. [VIRGIN]

### F · Execution as the edge (not a signal — a cost reduction, which compounds identically)
20. **Venue/route selection from Rule 605 execution-quality statistics.** Data: **SEC Order
    Execution (605/606) — testable now**. [`O18`/`F-1` — Valquo's fill A/B is the same question
    forward]
21. **Marketable vs worked-limit A/B on their own orders**, randomised. This is Valquo's `F-1`
    and it is the cheapest real experiment in either project. [`O10`'s open live question]
22. **Time-of-day execution scheduling** — trade the same signal at the cheapest minute.
    [VIRGIN · `O18`]

### G · Microstructure (listed for completeness; see §3 — mostly unreachable)
23. **Order-flow imbalance / Kyle's lambda.** Needs TAQ or a live depth feed. [`O14` DOES-NOT-
    TRANSFER but method applies]
24. **Retail identification via TRF prints** — the equity analogue of `MB15`, **and the axis that
    works in this asset class.** Needs TAQ-class data. [`MB15` HANDOFF/INVERTED]
25. **Quote-life / flickering-quote measures.** Needs full depth. [VIRGIN]

### H · Meta (zero-data, high value)
26. **The cost-first screen**: before any idea is registered, compute its required gross edge per
    round trip (§4) and kill it there if the number is implausible. [`D9`/`O13`]
27. **A frequency ladder for every candidate**: test the same effect daily / weekly / monthly and
    adopt at the **lowest** frequency that survives. **The toll scales with turnover; most
    effects do not.** [`S14` — Valquo's one adoption was a *turnover-reducing* no-trade band]

---

## 3. DATA REACHABILITY — be exact, because their scoping run depends on it

**Confirmed absent on this WRDS account: TAQ (no), OptionMetrics/IvyDB (samples only).**

### ⚠ CORRECTION ON "INTRADAY INDICATORS BY WRDS" — I got this wrong before; here it is right
From WRDS's own product page: *"Stock specific **daily and intraday (5 min, 15 min and 30 min)**
indicators created from the **TAQ** intraday dataset"* — stock/flow variables from trades and
quotes, **intraday volatility, spread, price impact** and other liquidity measures.

**Two corrections, and they cut opposite ways:**
1. **It is RICHER than I previously described.** I called it "daily per-name aggregates." It also
   ships **5/15/30-minute** indicators — so a 30-minute grid, which is the grid Gao et al.'s
   intraday-momentum result lives on (idea B5).
2. **AND THE PAGE STATES: "A subscription to the TAQ dataset is required to access WRDS Intraday
   Indicators."** This account has **no TAQ**. **UPDATE 2026-08-26 — this is now SETTLED, not
   open: treat Intraday Indicators as UNAVAILABLE on this grant.** A product listed as subscribed
   was gated behind one that is not. **Consequences, so their scoping run does not spend a day
   re-deriving them: ideas B5, B6 and G23–25 are NOT ANSWERABLE**, and §4's cost model falls back
   to the daily-OHLC estimators below — which is a real substitute, at lower resolution, with its
   estimator named.

### The reachability table

| route | what it gives | status |
|---|---|---|
| **CRSP daily** | open/high/low/close/volume, full universe, long history → **overnight vs intraday decomposition**, daily reversal, gap studies | **TESTABLE NOW** (and the phase-2 probe measured `crsp_a_stock.dsf` covering **2,271 of 2,531** Valquo names — a coverage precedent, not their data) |
| **Daily-data spread estimators** | **effective spreads from OHLC alone** — Ardia–Guidotti–Kroencke (*JFE* 2024); also Corwin–Schultz high-low and Holden (2009) | **TESTABLE NOW — and this is the cost model if Intraday Indicators is gated** |
| **SEC Order Execution (605/606)** | venue-level effective/quoted spread, price improvement, fill speed | **TESTABLE NOW** (ideas F20, and an external anchor for their own ρ) |
| **Historical SPDJI** | point-in-time index membership → add/delete dates | **TESTABLE NOW** (idea D16) |
| **IBES** | announcement dates **and times** (actuals) for event timing | **TESTABLE NOW** (D13, D14) |
| **WRDS Intraday Indicators** | 5/15/30-min + daily microstructure indicators | **NOT AVAILABLE — TAQ-gated on this grant (settled 2026-08-26)** |
| **Free / broker intraday bars** (broker APIs, public vendors) | minute/5-minute OHLCV, typically **recent history only**, adjustment conventions vary and are often undocumented | **TESTABLE NOW for FORWARD collection; historical depth is the constraint.** Start the recorder today — history cannot be built backwards (Valquo learned this twice) |
| **TAQ / full depth** | order-flow imbalance, TRF retail identification, quote life | **NOT ANSWERABLE on this account.** Priced separately if ever wanted; do not design against it |
| **News/sentiment (RavenPack etc.)** | event classification for D10 | **NOT SUBSCRIBED** — free substitutes are materially weaker |

**A recommendation they are free to ignore: start a forward intraday bar recorder this week,
whatever else is decided.** Valquo's `D11` harvest and `S3-I2`'s calendar both landed on the same
lesson — *the perishable thing is the data you are not yet recording* — and a recorder costs
nothing but disk.

---

## 4. THE COST ARITHMETIC FIRST — the screen every idea passes or dies on

**The rule: a round trip pays the spread roughly once** (two crossings × ~⅔ of the half-spread,
using `O18`'s measured ρ = 0.6743 as the shape). So:

> **round-trip cost ≈ 0.674 × quoted spread** (plus impact, plus borrow if short)

**Annual toll at one round trip per day (252/yr):**

| name class | typical quoted spread | round-trip cost | **annual toll at 1 RT/day** |
|---|---|---|---|
| mega-cap (top ~100) | ~1–2 bps | ~1.0 bps | **~2.5% / yr** |
| liquid large-cap | ~3–5 bps | ~2.7 bps | **~6.8% / yr** |
| mid-cap | ~10–20 bps | ~10 bps | **~25% / yr** |
| small-cap | ~30–100+ bps | ~34+ bps | **~85%+ / yr — dead on arrival** |

*(Spread ranges are order-of-magnitude context, not measurements of their data; their scoping run
should replace every one with a measured number from the estimators in §3.)*

**The three consequences, applied to §2's list:**

1. **The universe screen is the first design decision, not the last.** Anything trading intraday
   outside the most liquid decile is **DOA on cost**: ideas C9 (reversal is strongest exactly
   where costs are worst — this is the central tension of that family), C12, and any small-cap
   variant of A1–A4. **List them as DOA rather than passing them along** — that is what §4 is for.
2. **Required gross edge per trade is the number every register must state before running.** At a
   3 bps spread, an idea must clear **>2.7 bps per round trip gross** to be worth anything, and
   ~5+ bps to be worth the variance. **An idea whose plausible edge is 1–2 bps is dead on
   arrival** and should be recorded as such with its arithmetic, not tested.
3. **The frequency ladder beats the signal hunt** (idea H27). Toll scales with turnover; effects
   usually do not. Valquo's single adoption in ~550 trials was **`S14`, a no-trade band that
   reduced turnover** — it won by spending less, not by predicting better. **If one sentence from
   this brief survives contact with their register process, it should be that one.**

**Two families where the arithmetic inverts, and they are worth ranking first for exactly that
reason:** **execution work** (§2-F, F20–F22 — a cost reduction compounds identically to an edge
and needs no forecast at all) and **liquidity provision** (C11 — the only family that gets
*better* as spreads widen). Both are cheap, both are testable now, and neither requires
predicting a price.

---

## 5. WHAT I WOULD RANK FIRST IF ASKED (and I am not directing — their mentor decides)

1. **The trial counter, from trial #1** (§1c, `M1`) — free, permanent, and impossible to retrofit.
2. **The cost model from daily-data estimators** (§3, §4) — everything else is priced against it.
3. **The overnight/intraday decomposition** (A1–A3) — the deepest vein reachable with data they
   already have, on a well-replicated literature.
4. **Execution A/B on their own orders** (F21) — Valquo's `F-1`, the cheapest real experiment.
5. ~~Resolve the Intraday Indicators / TAQ-gating question~~ — **ANSWERED 2026-08-26: gated,
   unavailable.** The slot goes instead to **Historical SPDJI index-add events (D16)** — testable
   now, on a decayed-effect prior they should price before running.

**And the two Valquo findings I would put on their wall:** *a real trade pays about two-thirds of
the quoted half-spread*, and *the widest-spread quintile lost 7.41%*. Both are measured, both are
theirs to use, and together they explain more dead intraday strategies than any signal ever will.
