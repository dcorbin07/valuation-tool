# OPTIONS_DEEP_RESEARCH.md — the final "no stones unturned" sweep (2026-08-03)

A comprehensive, literature-grounded catalog of every remaining candidate edge for the options book (priority)
plus a stock cross-over. **Rule: adopt only what clears the held-out gate net of realistic spreads. Expect most
to reject — that's this project's pattern — but these are the genuinely under-tested corners.** Work top-down,
one thread per session, own handoff per thread.

## The reframe that makes this worth doing
The scream-buy ENTRY loses to a random-entry control (+13.22% random vs +5.14% signal). `term_slope` is the one
surviving filter. So an options edge, if one exists, is NOT in a better entry SIGNAL — the autopsy killed that.
It's in one of the three corners we've barely tested: **the EXIT, the SIZING, or the CROSS-SECTION of which
options** — or in a different strategy family (VRP / earnings / carry). That's where to dig.

## ALREADY REJECTED — do NOT re-open without a new reason
scream-buy entry timing · VRP put-credit-spreads (as implemented) · GEX · skew-as-filter · iv_rank-as-filter ·
conviction tier · DTE band · robust z-scores · higher-order greeks as entry features · momentum+institutional
consolidation. (Stock: sector-neutral, EV/Sales, lazy-prices, PEAD.)

## THE SWEEP — priority order

### 1. EXIT optimization — **DONE 2026-08-03. REJECT, but it found a real bug.** `HANDOFF_deep_exits.md`
Full run: 278 names, 3,119 signal entries + 5,986 random entries, 21 policies, aggression 1.0.
- **A SIMULATOR BUG WAS FOUND AND FIXED — read this before any thread that holds positions longer.**
  The production simulator marks a position that outlives its contract's last usable quote at THAT
  STALE QUOTE, and a contract stops being quotable exactly when it is dying. For the hold-to-expiry
  policy 44.6% of trades land there, the last quote is a MEDIAN OF 10 DAYS before expiry, it is
  higher than true settlement in 94.7% of cases, and 86.1% carry a positive mark on a contract that
  expired worthless. The bias scales with holding period, so it manufactures a fake reward for
  holding longer (+6.45pp on that policy). **The shipped exit hits it on 0.9% of trades, so 22b/22c
  and every earlier result are essentially unaffected** — but threads #3 (VRP), #4 (earnings) and
  #5 (calendars) all hold longer and MUST use honest settlement (`settle="intrinsic"`), now the
  default in `options_exitlab.apply_policy` and pinned by a test.
- **Verdict REJECT**: nothing clears the +10pp bar. The best policy, `tp200`, is +3.26pp on signal
  entries and +3.34pp on random.
- **The direction is real, small, and replicates on RANDOM entries** (so it is an EXIT property, not
  an entry one): cutting winners early is costly (+50% target −3.6pp) and stopping out tight is
  costly (−30% stop −2.6pp, 25% trailing stop −4.1pp). The optimum target sits nearer **+150–200%**
  than the shipped +100%; the −50% stop is on the costly side.
- **Do not be fooled by `tp100_only`** (+6.71pp per trade, the grid's biggest number): per DAY of
  capital committed it is *worse* than the shipped exit on both entry sets, it holds 2.5x longer,
  its paired direction flips between entry sets, and it carries 21.5% total losses vs 0.67%.
- PBO 0.075 (signal) / 0.000 (random) over 252 CSCV splits — the grid is not overfit, there is just
  not much in it. Deflated Sharpe at n_trials=21: tp200 99.8%.
- Two open questions recorded for whoever picks this up: whether an ABSOLUTE +10pp bar is the right
  instrument for a proportional improvement (tp200 is a ~69% relative lift on a +4.71% book), and
  whether requiring both a mean gain and a cell-win majority is self-defeating on a convex payoff.
- Re-scoring any NEW exit policy is now minutes, not a re-collection: the contract paths are banked
  in `data/options_exitlab/paths.pkl`.

### 1b. EXIT optimization — the original brief, kept for the record
Every result to date uses ONE fixed exit (+100% / −50% / half-DTE). For a convex long-option payoff the exit
often IS the edge. Test whether a smart exit beats fixed **even on the current/random entries**:
- Take-profit levels (+50 / 75 / 100 / 150 / 200%) — does banking early beat letting it run, or clip the fat
  tail that carries the book?
- Stop levels + **trailing stops** (by % or ATR) vs fixed.
- Time-based exits (close at N DTE to dodge the theta/gamma cliff).
- KEY TEST: random-entry + each exit rule vs random-entry + the current fixed exit. If an exit rule wins even
  on random entries, the edge is in the EXIT.
Basis: optimal-stopping / convexity literature; the well-known asymmetry that long-option P&L is dominated by
exit discipline, not entry.

### 2. Cross-sectional option returns — HIGH (the most "published research" of the lot)
We've never run a pure cross-sectional study of WHICH names' options are systematically cheap/rich. Replicate
the real documented edges on our ~370-name × decade cache:
- **Variance risk premium cross-section** (Goyal–Saretto 2009): sort on (IV − realized vol); rich-IV names have
  lower option returns.
- **Idiosyncratic vol** (Cao–Han 2013): delta-hedged option returns fall with idio-vol.
- **Expected idiosyncratic skewness** (Boyer–Vorkink): high-skew "lottery" options are overpriced.
- **Vol-of-vol**, slope of the smile, option-illiquidity premium.
Each as a cross-sectional sort (long cheap / short rich, or long-only cheap), held-out, net of spread.

### 3. The VRP done RIGHT — HIGH (most robust options edge; our one rejection may be the wrong implementation)
We rejected 20-delta put-credit spreads — but the variance risk premium itself (implied > realized on average)
is the most robust edge in the options literature. Test other harvests, IRA-compatible (defined risk, no
naked): short premium ONLY when IV-rank is high (never tested as a SELL-timing rule); iron condors / defined
strangles; shorter-dated premium. Honest: short vol carries the negative skew that drained our arm — adopt only
if the tail is modeled and it clears the gate.

### 4. Earnings / IV-crush — MEDIUM-HIGH (options-native, distinct from the rejected stock PEAD)
Use ThetaData IV to compute the IMPLIED move (ATM straddle) vs the REALIZED move around each earnings date
(EVENTS code 22). Published: implied earnings moves are, on average, slightly OVER-priced. Test: is the implied
move rich/cheap on our names; an earnings-aware entry rule (never BUY into the IV-crush the loser-autopsy
flagged); a defined-risk short-premium-into-earnings sleeve.

### 5. Term-structure / calendar carry — MEDIUM
`term_slope` predicts, so the vol term structure carries information — test TRADING it (calendars: sell
short-dated, buy long-dated when steep/inverted). Basis: vol term-structure carry.

### 6. Delta / moneyness surface — MEDIUM
Confirm the optimal delta on the BROAD universe (not just the 55 megacaps): deep-OTM lottery (max convexity) vs
ATM vs ITM (more delta). A real, unrun cross-check now that we have breadth.

### 7. Position sizing for a convex payoff — MEDIUM (maximizes edge, doesn't create it)
Fractional-Kelly / risk-of-ruin on the actual 37%-hit, fat-tailed distribution. The right sizing is the
difference between compounding the long-vol exposure and bleeding out.

### 8. Options-implied STOCK signals — the cross-over (bonus, feeds the strong stock model)
Use the mined options data to predict the STOCK, not the option — the "options market leads the stock market"
literature: put-call ratio, IV skew, vol-of-vol as cross-sectional STOCK-return predictors. Novel here, uses
data we now have.

## STOCK side (lower priority — the model is validated)
The only real untested lever is **estimate revisions (WRDS/IBES)** — blocked on Don setting up WRDS access.
Everything else on the stock side has been tested and rejected.

## The honest contract
Most threads will REJECT — and a clean reject IS the deliverable: it settles the options question for good and
lets us commit fully to the stock model + the honest long-vol framing. But #1 (exit), #2 (cross-section), and
#3 (VRP-done-right) are genuinely under-tested and literature-backed — if an unturned stone exists, that's
where it is. No forcing; every thread through the same held-out gate, net of spread.
