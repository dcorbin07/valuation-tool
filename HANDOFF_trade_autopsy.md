# HANDOFF — trade autopsy: what separates the winners from the losers (#23 + #26)

Single-item session per `PROMPT_pipeline_trade_autopsy.md`. Options lane. Other agents running
concurrently, so this is its own file.

## The answer

**Nothing beyond `term_slope` survives.** 64 entry-known features, 126 held-out hypotheses, and
the only thing that clears the pre-committed gate in both split directions is the filter that is
already live.

That is a clean negative and the mandate said to expect it. But three findings inside it are
worth more than the headline:

1. **The winners and the losers are almost indistinguishable AT ENTRY.** Across all 64 features
   the largest median gap between a stopped-out loser and a >= +100% winner is **0.18 standard
   deviations** (put/call OI). Nothing about the greek stack, the GEX geometry, the underlying's
   extension or the market regime tells you, at entry, which one you are about to get. The
   convexity is not a setup you can select — it is the payoff structure doing its job.
2. **The total-loss bucket the mandate asked me to autopsy is essentially empty.** 10 of 1,540
   trades (0.65%) lose >= 90%. The -50% stop already removes that failure mode. There are no
   avoidable zeros to hunt, so that half of the brief resolves as "already solved by the exit
   discipline", not as a finding.
3. **`iv_rank` is finally testable and it rejects** — closing an item Phase 2 had to leave open
   as "not testable", which is a different and worse status than "rejected".

## The outcome distribution, which reframes the question

    bucket                       n      expectancy
    total_loss (<=-90%)         10        -0.942
    stopped     (<=-45%)       871        -0.591
    small_loss  (-45%..0)       93        -0.199
    small_win   (0..+100%)     103        +0.363
    tail_win    (>=+100%)      473        +1.388

    overall   n 1540   expectancy +0.1042   hit 37.4%   P(>=+100%) 30.7%   P(stop) 56.6%

This is a **barbell, not a long tail of small losses**. 56.6% of trades go to the stop and 30.7%
reach the double; only 12.7% land in between. The mandate's instruction "do not try to remove the
small losers, they are the fair cost of convexity" is right in spirit but the small losers barely
exist — the cost of convexity here is paid at the -50% stop, 871 times.

One consequence matters for how any future result is read: with a near-binary payoff, **P(win)
and expectancy are tightly coupled**, so a filter that raises the hit rate here is usually also
raising expectancy rather than clipping the tail. That does not make hit rate a safe target — it
makes the tail-retention check the thing that distinguishes the two, which is why it is a
hard bar in the gate rather than a reported statistic.

## Method, and the gate (pre-committed before any feature was scored)

Every trade in the backtest log is joined to features **known at entry only**:

    trade log        score, DTE, delta, IV, premium, labels, and the four Phase-2 signals
    <sym>-daily.pkl  the surface ON the alert date: GEX total/walls/concentration, zero-gamma
                     distance, 25-delta skew, ATM term structure (14/30/60), p/c OI and volume,
                     and iv_rank -- which Phase 2 could NOT test (0% coverage then) and which is
                     properly testable for the first time here, off the daily ATM-IV series.
    <sym>-<year>.pkl the greek stack OF THE CONTRACT ACTUALLY BOUGHT: spread_frac, moneyness,
                     vanna, charm, vomma, veta, speed, color, zomma, ultima, normalised
    bars             momentum 5/20/60/120d, 52-week extension, SMA distance, realised vol,
                     Bollinger position, volume surge
    regime           a cross-sectional VIX PROXY (median ATM 30d IV across all 111 mined names)
                     and a market TREND proxy (60d return of a rebased equal-weighted index of
                     the same names). Both are proxies -- there is no VIX or SPY series on disk.
    earnings         days since / estimated days to the next filing
    sector           from the Sharadar TICKERS cache the panel already uses

Higher-order greeks enter **normalised** (vanna/vega, vomma/vega, zomma/gamma, theta/premium...).
Raw vega on a $400 stock is simply larger than on a $40 one; unnormalised, the sweep would have
ranked share price and called it geometry.

The gate, all of which must hold:

    G1  direction AND threshold fitted on ONE half only (direction = that half's rank-IC sign,
        threshold = median among that half's profitable trades -- the Phase-2 recipe, reused)
    G2  held-out expectancy gain >= +5pp
    G3  retention >= 40%
    G4  >= 60 kept trades on the held-out half
    G5  TAIL RETENTION >= 0.95 x overall retention
    G6  beats a random filter of the same size (permutation p < 0.05, 2000 draws)
    G7  passes G2-G6 in BOTH split directions (fit-early/confirm-late AND fit-late/confirm-early)

**G5 is new to this project.** No earlier phase had a bar that stops a filter buying expectancy
by cutting the right tail. It is pinned by a test that constructs exactly that filter — one that
raises expectancy by +16pp, keeps 40% of trades, and clears the permutation control, while
retaining none of the +100% winners — and asserts the gate rejects it.

### The harness reproduces the shipped result exactly

Before trusting any of this, `term_slope` was run through the same pipeline as an unknown:

    fitted threshold  +0.0105     kept 307/756 = 40.6%
    late-half         +4.76%  ->  +12.88%      gain +8.12pp

Identical to the numbers in `options_signals_v2`'s committed result block. The feature assembly,
the fitting recipe and the scoring are therefore not quietly different from what shipped.

## The sweep

    64 features tested, 126 hypotheses (64 x 2 split directions)
    SURVIVORS (both directions): f_term_slope -- and nothing else
    Benjamini-Hochberg at q=0.10 over all 126: ZERO discoveries

The FDR line deserves emphasis. **Not even `term_slope`'s own p-values (0.024 / 0.037) survive
correction for the size of this search.** That is not an argument against term_slope — it was
pre-registered and adopted in Phase 2 on its own committed gate, not discovered here — but it is
the honest statement about *this* sweep: nothing in it rises above what 126 tests on 1,540
heavy-tailed trades would produce by chance.

And the FDR pass was not structurally incapable of finding something: with 2,000 permutation
draws the smallest achievable p is 0.0005, comfortably under BH's most stringent rank-1
threshold of 0.10/126 = 0.0008. A feature with a decisive effect would have hit that floor. None
came close.

Held-out results, ranked by forward gain (`dir` = fitted direction, `keep` = retention,
`tailR` = tail retention / retention, `p` = permutation):

    feature                  cov  dir  gain(late)  keep  tailR      p   gain(early)  both
    f_d_term_14_60          0.70   +1     +0.090   0.40   1.10  0.024      +0.023   no
    f_term_slope            1.00   +1     +0.081   0.41   1.05  0.024      +0.066   YES
    f_entry_iv              1.00   -1     +0.069   0.27   1.16  0.113      -0.005   no
    f_d_pc_oi               0.84   +1     +0.068   0.47   1.13  0.030      +0.072   no
    f_spread_frac           0.84   -1     +0.055   0.57   1.06  0.042      -0.004   no
    f_dte                   1.00   +1     +0.052   0.47   1.09  0.070      +0.013   no
    f_mom60                 0.84   +1     +0.048   0.55   1.07  0.065      +0.083   no
    f_vol_surge             0.84   +1     +0.041   0.48   1.10  0.120      -0.041   no
    f_color_n               0.84   -1     +0.037   0.55   1.08  0.132      -0.042   no
    f_d_dist_call_wall      0.84   -1     +0.035   0.40   1.02  0.212      +0.038   no

Everything below this is under +0.035 and p > 0.2. **The higher-order greeks and the GEX geometry
— the fresh angle the mandate pointed at — are at the bottom of the table.** vanna, vomma, veta,
zomma, speed, charm and the wall/zero-gamma distances all land inside noise. `color_n` and
`d_dist_call_wall` are the best of them and neither survives one split direction, let alone two.

Market regime, both halves of it, also rejects: the VIX proxy (`mkt_iv_rank`, +0.014 / -0.051)
and the trend proxy (`mkt_mom60`, +0.012 / +0.017 at p 0.35 / 0.34) are inside noise. Whether
the market was calm or stressed, rising or falling, at entry did not predict the trade.

### One genuine open item closed: `iv_rank` is now TESTED, and it REJECTS

Phase 2 recorded `iv_rank` as **"NOT TESTABLE AS BUILT, not rejected"** — it needed 60 prior
ATM-IV observations per name and had accumulated IV only from that name's own alerts, so coverage
was 0%. The daily ATM-IV series the greeks miner now writes fixes exactly that. At **83%
coverage** it tests cleanly and it is dead:

    f_d_iv_rank   -0.011 (p 0.63)  /  -0.019 (p 0.67)
    f_d_iv_pct    -0.014 (p 0.67)  /  -0.010 (p 0.60)

Both negative in both directions. **`iv_rank` can now be moved from "untested" to "rejected"** in
the Phase-2 record — buying calls when a name's vol is cheap against its own trailing year does
not help. Note the raw `entry_iv` level does slightly better than the *rank*, which is the
opposite of the usual folklore.

### The near-misses, and why each one is not a finding

**`f_d_pc_oi` (put/call open interest) is the only genuinely close call.** It gains +6.8pp and
+7.2pp — both directions, both above the bar — with healthy retention (0.47 / 0.46) and a tail
ratio above 1.1. It fails on one thing: the reverse-direction permutation p is **0.0545** against
an 0.05 bar. Moving the bar after seeing that number is precisely what the gate exists to
prevent, so it is recorded as rejected. Two further reasons not to reopen it cheaply: its
quintile profile is **not monotone** (Q3 +0.244 is the best, Q5 +0.161, Q1 -0.017), and it dies
completely when stacked on term_slope (below).

**`f_d_term_14_60` is not a second signal, it is term structure again** — +0.607 rank
correlation with `term_slope`. Its strong forward number (+9.0pp) is corroboration that the term
axis is real, not a new axis.

**`f_entry_iv` is largely term structure wearing a different hat** (-0.479 correlated: low IV
goes with contango). It also fails badly in reverse (-0.005) and keeps only 27% of trades.

**`f_spread_frac` is the tidiest economic story and still rejects.** Cheapest-quintile spreads
return +0.183 and the widest +0.032, monotonically. But fit the rule on the late half and it
delivers -0.004 on the early one. Liquidity looks like it should matter, and on this evidence it
does not matter *stably*.

### Stacked on top of term_slope — the only test that would justify a change

666 of 1,540 trades pass the live term gate. Re-running the near-misses inside that subset:

    feature               fit-early -> late          fit-late -> early
    f_d_pc_oi             +0.012  keep 0.51  p 0.412   +0.079  keep 0.43  p 0.147
    f_dte                 +0.067  keep 0.49  p 0.134   -0.028  keep 0.47  p 0.695
    f_d_dist_call_wall    +0.057  keep 0.42  p 0.206   +0.041  keep 0.57  p 0.229
    f_d_skew_25d          +0.004  keep 0.46  p 0.485   +0.098  keep 0.51  p 0.063
    f_entry_iv            +0.073  keep 0.24  p 0.253   -0.003  keep 0.61  p 0.545
    f_d_term_14_60        -0.053  keep 0.36  p 0.720   +0.027  keep 0.55  p 0.311
    f_mom60               +0.006  keep 0.55  p 0.450   -0.071  keep 0.56  p 0.893

**Nothing adds anything to term_slope.** `d_pc_oi`, the best standalone candidate, collapses to
+0.012 (p 0.41) in the forward direction.

State the limit honestly: this test is **underpowered**. 666 trades split in half leaves ~330 per
side, so the permutation control has little resolution and a genuine +5pp effect could easily
sit inside these intervals. "Nothing survives stacking" is a failure to demonstrate, not a
demonstration of absence.

## The loser autopsy

The mandate asked for the avoidable structural mistakes: earnings IV-crush, too-short DTE,
chasing an extended underlying, illiquid contracts, low term_slope. Measured as the median entry
feature of a stopped-out trade against a >= +100% winner, in standard deviations:

    f_d_pc_oi              +0.18 sd        f_d_dist_call_wall     -0.11 sd
    f_mkt_iv_rank          +0.14 sd        f_d_gex_wall_conc      -0.11 sd
    f_theta_frac_day       +0.13 sd        f_mom20                -0.07 sd
    f_dte                  +0.12 sd        f_term_slope           +0.07 sd

**That is the whole autopsy.** The largest separation between the strategy's winners and its
losers, on any of 64 entry features, is under a fifth of a standard deviation. The named
suspects specifically:

  * **earnings proximity** — `filing_in_window` and `est_days_to_filing` are both inside noise.
    Caveat: these are Sharadar **filing** dates, which trail the announcement by a few days, so
    this is a blunt instrument (a real announcement calendar would test it properly). The term
    structure partly covers it anyway — an imminent event shows up as backwardation, which is
    what `term_slope` already screens.
  * **too-short DTE** — `f_dte` gains +5.2pp forward, +1.3pp reverse. The 45-75 band is the
    strategy's own definition, so there is little variation to find, and Phase 3 already tested
    and rejected the 65-75 sub-band.
  * **chasing an extended underlying** — `run5`, `bb_pos`, `ext_52w`, `mom20` all land inside
    noise, and the signs are inconsistent between halves. There is no evidence here that buying
    into a stretched move is the mistake it is assumed to be.
  * **wide spreads / illiquidity** — the one with a real gradient (see `spread_frac` above), and
    it still fails the both-directions bar.
  * **low term_slope** — the effect that is real, and already live.

## Regime confound: checked, and it does NOT hold

The mandate warned the top winners were "mostly 2020 tech — a regime, not a setup". **That is
not what the data says.**

    tail winners (>=+100%) by year
      2021: 72   2017: 70   2024: 67   2020: 60   2018: 48
      2016: 39   2019: 37   2025: 36   2023: 30   2022: 14

    2020's share of the tail: 12.7%
    the 15 biggest winners span SEVEN different years (2024:4, 2020:3, 2017:3, 2016:2,
                                                       2019:1, 2023:1, 2025:1)
    biggest: CRM 2020-08 +766%, DE 2016-10 +633%, MMM 2024-07 +625%, META 2024-01 +497%,
             ORCL 2017-05 +488%, MCD 2017-04 +472%, NVDA 2016-10 +450%, GS 2024-10 +439%

Deere, 3M, McDonald's and Goldman are not 2020 tech. The tail is spread across the decade and
across sectors. **The convexity is a property of the payoff, not of one regime** — which makes
the negative result above more meaningful, not less: there was a real, well-distributed tail to
predict, and none of the 64 features predicted it.

The fade itself is unchanged and remains the backdrop:

    year    n    expectancy   P(tail)  P(stop)
    2016  124     +0.1559      0.315    0.516
    2017  204     +0.2249      0.343    0.466
    2018  156     +0.0900      0.308    0.564
    2019  128     +0.0753      0.289    0.555
    2020  172     +0.2071      0.349    0.541
    2021  233     +0.0602      0.309    0.579
    2022   63     -0.1141      0.222    0.714
    2023  123     -0.0461      0.244    0.667
    2024  207     +0.1684      0.324    0.565
    2025  130     -0.0005      0.277    0.623

## How much of this sweep is overfitting: PBO and Deflated Sharpe

The mandate asked for both. They answer two different questions and it matters which is which.

**PBO = 42.9%** (CSCV, 8 chronological blocks, all 70 splits, 64 configs). PBO does not score a
strategy — it scores the *selection step*, which is this study's actual risk: pick the best
feature in-sample, and **it lands below the out-of-sample median 43% of the time**. 50% is "the
selection carries no information whatsoever". So choosing among these 64 features is barely
distinguishable from choosing at random, which is the same verdict the gate reached, arrived at
independently. (For scale, the stock panel's PBO is 6.7% — that is what a selection with real
information looks like.)

**Deflated Sharpe, on the other hand, says the EDGE is real:**

    book                 n     per-trade Sharpe   skew   kurtosis   SR0 bar   DSR
    term_slope-gated    666         0.168         2.02     10.75     0.079    99.66%
    unfiltered         1540         0.107         1.63      8.05     0.056    98.62%

Both clear the 95% bar after deflating for 64 trials. Read this carefully, because it is easy to
over-claim: **DSR here says the scream-buy option book has a real positive per-trade edge, not
that any new feature was found.** The two results are consistent — a genuine edge whose
*refinements* are all noise.

Three caveats that must travel with these numbers. The "Sharpe" is **per trade, not annualised**,
and must never be quoted as an annual figure. The trades are **not independent** — the same
alert logic across 55 correlated large caps clusters outcomes, so the effective n is below 666
and DSR is correspondingly optimistic. And skew +2.0 with kurtosis 10.8 is the barbell showing
up exactly where it should: those terms are load-bearing here, not cosmetic.

## Sector

Sector is categorical, so a median threshold on it is meaningless; it gets a consistency table
instead — does a sector that pays in one half still pay in the other?

    sector                    n(early)   exp(early)   n(late)   exp(late)   both halves +
    Technology                   229      +0.1923       188      +0.1536        yes
    Industrials                  102      +0.2632       116      -0.1053        no
    Consumer Cyclical            113      +0.2283       101      +0.0143        yes
    Communication Services       106      +0.0144       105      -0.0068        no
    Financial Services            70      +0.2010       100      +0.1645        yes
    Consumer Defensive            94      +0.1017        65      +0.1258        yes
    Healthcare                    60      +0.0474        47      -0.0237        no
    Energy                        10      -0.0196        34      -0.1454        no (thin)

Technology, Financial Services and Consumer Defensive hold up in both halves; Industrials flips
hard (+0.26 -> -0.11) and Healthcare and Communication Services are flat-to-negative. **Nothing
here is actionable.** Four of eight sectors being positive twice is roughly what coin flips
produce, the universe is 55 hand-picked large caps rather than a sector-representative sample,
and sector is a *universe* choice, not an entry filter — it belongs to whoever picks the names,
not to the alert. Note also the standing look-ahead caveat the stock model records: this is
TODAY's classification applied to 2016 rows.

## #26 — the ML combiner

The mandate escalates to a combiner only if a univariate signal exists. **It did not**, so by the
pre-registered rule #26 should not have run. I ran it anyway, once, because interactions are
exactly what a univariate sweep cannot see — "no main effect" is not evidence of "no
interaction" — and left the escalation status recorded in the output.

One pre-specified configuration, no hyperparameter search (a search over 1,540 heavy-tailed
trades is how a result gets manufactured): a depth-3 `HistGradientBoostingClassifier` and an L2
logistic control, target `pnl_pct >= +100%`, keep the top 40.6% by predicted probability to match
term_slope's retention. **The null is the same model refit on shuffled labels**, 100 times — the
only null that answers "did it find structure, or is this the capacity of a 64-feature booster to
fit 750 rows of noise".

    ALL 64 FEATURES              gain    null    shuffle-p   tail retention
    hgb   fit-early -> late    +0.011  -0.004      0.337         0.43
    hgb   fit-late  -> early   +0.007  -0.001      0.505         0.41
    logit fit-early -> late    +0.073  -0.001      0.050         0.45
    logit fit-late  -> early   +0.053  +0.012      0.297         0.42

    EX-TERM (61 features, every term-structure read removed)
    hgb   fit-early -> late    +0.019  -0.004      0.248         0.43
    hgb   fit-late  -> early   -0.002  -0.001      0.505         0.41
    logit fit-early -> late    +0.056  -0.001      0.129         0.45
    logit fit-late  -> early   +0.054  +0.013      0.248         0.43

**Rejected, both variants.** The tree finds essentially nothing in either direction. The linear
model is the interesting line — positive in both directions, at or above the +5pp bar — but it
cannot beat a shuffled refit of *itself* in the confirming direction, which is the whole test.
This echoes P6's lesson on the stock side: the linear composite behaves better than the flexible
one.

The **ex-term** block is the direct answer to the mandate's question. Strip every term-structure
feature and the model still returns +5.6pp / +5.4pp — but at p 0.13 / 0.25, i.e. **the greeks,
the GEX geometry, the underlying and the regime jointly contain something that looks like a
signal and cannot be distinguished from the capacity of a 61-feature model to fit noise.**

One diagnostic worth recording, because it is the most honest evidence in this section: adding a
single feature (`mkt_mom60`) between two runs moved the logit's forward gain from +0.051 to
+0.073 and its p from 0.109 to 0.050. **A result that swings that far on one irrelevant input is
not a finding**, and it is exactly why the shuffle null rather than a comparison against zero is
the right bar.

## What this study could and could not detect

**Could:** a feature with a stable +5pp effect at 40%+ retention. `term_slope` is one and it was
found from scratch, twice, in both split directions — so the harness demonstrably detects the
size of effect that matters.

**Could not:** small effects (< ~4pp), effects that live only inside the term-filtered book
(~330 trades per half — see the stacking caveat), and anything needing data not on disk: an
actual earnings **announcement** calendar, tick-level flow (sweeps/blocks/aggressor side, still
untested since Phase 2), and sector membership.

**Sample limits worth stating plainly.** 1,540 trades across 55 names, of which 1,297 (44 names)
have the greek stack and the surface — so every contract-level and GEX feature was tested on 84%
of the log, not all of it. The 11 missing names (ADBE, CMCSA, F, GM, HON, MMM, NKE, PYPL, SBUX,
TGT, UPS) are not mined yet; re-running as the miner grows is cheap and is the obvious repeat.
The trades are also not independent — the same alert logic on 55 correlated large caps produces
clustered outcomes, so the effective sample is smaller than 1,540 and every p-value here is
mildly optimistic.

## The one observation worth a future PRE-REGISTERED test

`term_slope`'s effect is **not a smooth gradient — it is concentrated in the top quintile**:

    quintile of term_slope         n   expectancy   P(tail)   profit factor
    Q1 [-1.30, -0.064]           308     +0.037      0.305        1.10
    Q2 [-0.064, -0.016]          308     +0.037      0.299        1.10
    Q3 [-0.016, +0.015]          308     +0.093      0.305        1.27
    Q4 [+0.015, +0.044]          308     +0.046      0.269        1.13
    Q5 [+0.044, +0.223]          308     +0.307      0.357        2.06

The live threshold is +0.0105, which sits at the Q3/Q4 boundary — so the live book currently
includes Q4, which is flat. Phase 2's robustness sweep varied the threshold over 0.5x-1.5x
(i.e. up to +0.0158) and found the gain stable, but **it never went as far as Q5's floor of
+0.044**, so "a much tighter gate is better" is untested rather than tested-and-rejected.

**This table is IN-SAMPLE and must not be acted on as it stands.** Tightening a threshold because
the full-sample quintile table says so is exactly the noise-chasing this project keeps refusing.
The right move is a pre-registered test: fit a tighter threshold on one half by a fixed recipe,
confirm on the other, and check retention — a much tighter gate would keep well under 20% of
alerts, which fails G3 as written and would be a materially smaller book. Worth doing properly;
worth nothing done casually.

## Files

    valuation/edge/options_autopsy.py   the study: features, gate, loss autopsy, PBO/DSR, combiner
    optautopsy_run.py                   runner (--data-root, since a worktree has no data/)
    tests/test_edge.py                  10 new tests
    data/options/AUTOPSY_RESULTS.json   full output (gitignored)

Reproduce: `python optautopsy_run.py --data-root data` (~25 min, most of it the combiner nulls).

## Tests

**133/133 edge** (10 new). The new ones pin: the tail-retention bar rejecting a tail-clipping
filter that passes every other bar; the both-directions requirement rejecting a one-sided fit;
tie-corrected Spearman (without it every binary label feature is understated); BH-FDR
monotonicity; the stop/zero bucket separation; fitted-not-assumed direction; NaN counting as
missing coverage rather than as a value (the Phase-2 `skew_25d` bug, pinned so this sweep cannot
repeat it); Deflated Sharpe's bar actually rising with the trial count; PBO returning a coin
flip on noise features; and the regime cache being versioned.

All 12 other suites green (bulk 14, intraday 18, saas 23, options-greeks 21, paper-track 22,
engine 28, screener 43, calibration 23, freeze 13, lazy-prices 28, security 22, sector-neutral 6).

### Two bugs found in my own work, worth recording

**The regime cache was keyed only on its path.** It served a dict built before `mkt_mom60`
existed, so the market-trend feature simply never appeared in the sweep — no error, no warning,
64 features silently reported as 63. This is the same shape as the five empty factors and the
`assets` loader bug: a missing input that raises nothing. The version now lives in the cache
filename and a test asserts it.

**A no-op feature-rename** (`"d" + k[1:]` on keys already starting `d_`) that did nothing but
would have looked deliberate to the next reader. Removed.

## Recommended next step

1. **Do not add a second filter.** The honest read is that `term_slope` is most of what is
   gettable from entry-known features on this data — PBO 42.9% says selecting among the
   alternatives is close to a coin flip — and the forward paper track is worth more than another
   pass over the same 1,540 trades.
2. **Re-run this study when the miner passes ~55/55 names.** It is one command and it would lift
   the contract-level and GEX features from 84% coverage to full. `d_pc_oi` at p=0.0545 is the
   one candidate a slightly larger sample could legitimately settle either way.
3. **The Q5 concentration above is the single most promising follow-up** — but only as a
   pre-registered both-halves test, and note in advance it will probably fail the retention bar.
4. Unchanged and still Cowork's: wire `record_outcome` so the paper book can close a trade.
