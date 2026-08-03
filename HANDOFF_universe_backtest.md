# HANDOFF — Roadmap 22b: the options edge on the expanded universe

Session of 2026-08-03. Options lane. Everything below is the full 187-name run at
**aggression 1.0 (buy the ask, sell the bid)**, window 2016-01-01 to 2025-10-15.

---

## THE ANSWER, IN ONE PARAGRAPH

The edge **survives breadth but roughly halves**: +12.33%/trade on 55 megacaps becomes
**+5.14%/trade on 187 names**, and it clears the pre-committed bars (positive expectancy,
profit factor 1.16, both held-out halves positive). Mid/small caps are not the problem — they
are the *best* tier, and the entire old-vs-new gap turns out to be the **spread**, not the
signal: marked at the mid the two cohorts are identical (+11.99% vs +11.56%), and crossing the
spread costs 6.59pp, more than half the surviving edge. But a control this project had never run
before changes what all of that means: **buying the same contract in the same name and the same
year on a RANDOM day returned +13.22%, against the alert book's +5.14%.** The alert book wins
only 41.9% of 1,052 name-year cells (sign-test z = −5.24). On this universe, over this decade,
the scream-buy signal picked *worse* entry days than chance. The strategy is profitable; the
*signal* is not what makes it profitable. That is the finding, and it outranks every other
number here.

---

## WHAT WAS RUN

| | |
|---|---|
| Universe | **187 names** the miner marked `complete` with all 10 cached years present |
| of which | 54 of the original 55 (PYPL is not `complete` in the cache), **133 new** |
| Window | 2016-01-01 .. **2025-10-15** — the cutoff clears a full 75-day max-DTE contract life inside the cached history, so no exit path runs off the end of the data |
| Trades | **3,042** closed, from 5,953 alerts on 35,603 candidate days |
| Fills | NBBO at aggression 1.0 throughout. No result in this file is a mid-fill number |
| Strategy | Nothing re-tuned. Alert rule, contract rule (~35Δ, 45-75 DTE), exit discipline (+100% / −50% / half-DTE), fill model and the term_slope threshold are all imported or hard-quoted from the 55-name work |

The gate (B1-B5) was written into `valuation/edge/options_universe.py`'s docstring and committed
**before** the run. It is quoted there in full and is not restated here.

**The 55-name baseline is re-scored inside this same run**, not quoted from its published
figure. The published +12.33% covers a longer window (through 2026-06-30) and includes PYPL;
comparing against it directly would confound breadth with period. The like-for-like partition
is one run, one window, split by whether the name was in the old pool.

---

## 1. DOES THE EDGE HOLD? — B1: YES, MECHANICALLY. HALVED.

```
                     n      exp/trade    PF      hit     P(>=+100%)   P(total loss)
broad, 187 names    3042      +5.14%    1.16    38.8%      23.2%         0.69%
  54 old names      1241      +6.95%    1.22    39.2%      23.9%
  133 new names     1801      +3.90%    1.12    38.5%      22.7%
published 55-name   1540     +12.33%    1.36    38.0%         -             -
```

Held-out halves, broad book: early **+5.57%**, late **+4.86%**. Both positive → B1 passes and
the label is HOLDS rather than WEAKENS. Four of ten years are negative (2016, 2018, 2022, 2023);
the 55-name run had three.

**Read this as a real weakening, not a pass.** The new names earn 3.90% against the old names'
6.95% on the identical window — and the old names' own number is down from the published 12.33%
purely from shortening the window, which is itself a warning about how much period matters here.

**But the old-vs-new gap is ENTIRELY the spread — see §2a.** Marked at the mid, the two cohorts
are indistinguishable (+11.99% vs +11.56%). Breadth does not dilute the gross edge at all; it
dilutes the net edge, and only by costing more to trade.

Deflated Sharpe on the broad book, deflated by the 64-feature search:
**88.13% unfiltered — below the 95% bar** (55-name: 98.62%), and **95.69% on the
term_slope-filtered book** (55-name: 99.66%), which clears it only just. The statistical
comfort the 55-name result carried is largely gone.

---

## 2. THE MARKET-CAP TIER BREAKDOWN — mid/small are the BEST tier, not the worst

Point-in-time market cap at the last month-end on or before entry, fixed dollar boundaries.

```
tier     n    names   exp/trade    PF     hit    P(>=+100%)  avg win  avg loss  median spread
mega    852     61      +6.21%    1.19   38.8%     24.1%      +99.0%   -52.7%       3.68%
large  1590    166      +2.31%    1.07   37.5%     22.1%      +92.9%   -52.0%       5.04%
mid     567     86      +9.80%    1.34   41.4%     24.3%      +93.6%   -49.5%       6.25%
small    33     10     +34.36%    2.61   51.5%     30.3%     +108.1%   -44.0%       8.28%
```

Every tier is positive in both held-out halves. Spreads widen monotonically with falling cap
exactly as predicted — and the edge does **not** fall with them. Don's "spreads eat it"
half-thesis is not what happens.

**Where the spread actually bites is upstream of the fill: alerts that never become trades.**
Only 51.1% of alerts produced a tradable contract. The rejects are 2,911 `no_contract_in_band`
and 1,401 `no_chain` — and `no_contract_in_band` is where the liquidity screen hides, because
`pick_contract` applies the fill filter (max 25% spread, min 100 OI, min 10 volume) internally
and returns nothing rather than substituting a worse contract. So wider spreads cost this
strategy *opportunities*, not *fills*. The trades that happen already passed the screen.

**The `small` tier is 33 trades on 10 names and must not be quoted as a finding.** It is above
the 30-trade floor by three. See §5 — it is the most contaminated cell in the study.

---

## 2a. HOW MUCH OF THIS IS THE SPREAD? — a full second pass at mid fills

The whole run was repeated at aggression 0.0 (mark at the mid) on the **same pinned 187 names**,
so exactly one variable changes. Mid fills are a diagnostic and never a headline — this is the
decomposition, not a result.

```
slice                touch (a=1.0)    mid (a=0.0)    spread toll    median entry spread
ALL                      +5.14%         +11.73%        -6.59pp            4.78%
  mega                   +6.21%         +11.58%        -5.37pp            3.68%
  large                  +2.31%          +8.46%        -6.15pp            5.04%
  mid                    +9.80%         +19.18%        -9.39pp            6.25%
  small                 +34.36%         +45.32%       -10.96pp            8.28%
  54 old names           +6.95%         +11.99%        -5.04pp            3.62%
  133 new names          +3.90%         +11.56%        -7.66pp            5.92%
```

Three things fall out, and they answer the mandate's central question directly.

1. **Crossing the spread costs 6.59pp — more than half of the surviving 5.14% edge.** The
   strategy's gross edge is roughly +11.7%/trade and the market takes 56% of it at the touch.
   This is why every number in this file is quoted at aggression 1.0.
2. **The old-vs-new gap is 100% spread.** At the mid the two cohorts are +11.99% and +11.56% —
   a 0.43pp difference on 3,010 trades. At the touch they are +6.95% and +3.90%. The new names
   have the *same* gross edge and simply pay 5.92% spread against 3.62%. **Breadth does not
   dilute the signal; it dilutes the fill.**
3. **Don's "spreads eat it" thesis is half-right, and the half that is right is measurable.**
   Mid and small caps pay roughly double the toll of megacaps (−9.4pp and −11.0pp vs −5.4pp) —
   the tier ordering of the toll tracks the tier ordering of the spread exactly. But they start
   from a gross edge so much higher (+19.2% and +45.3% vs +11.6%) that they still finish ahead
   net. The spread eats *more* of the mid/small edge; it does not eat *all* of it.

Note this understates the true cost of breadth, because the miner already excluded 55 names as
too thin to trade. Those are where the toll would have exceeded the edge.

---

## 3. THE HOME-RUN THESIS — B4: NOT UPHELD

Do mid/small caps produce more frequent big winners?

```
P(>=+100%)   mid/small 24.7%  vs  mega/large 22.8%   diff +1.86pp   CI95 [-1.88, +5.85]
```

The interval spans zero. **More frequent home runs: not demonstrated.** What *is* significant
is expectancy: mid/small +11.15% vs mega/large +3.67%, diff +7.48pp, CI95 [+0.24, +14.97].
The mid/small advantage is in the *size and shape* of outcomes (higher hit rate 41-52%, smaller
average loss), not in the frequency of the tail.

### De-concentration — B3(b) passes, but the bar was weak and I am flagging it

```
                        tail winners   names   tail HHI   effective names   top-5 share
all 187 names               705         168     0.0096         104.4          10.8%
mega+large only             557         145     0.0114          87.8          12.7%
mid/small only              148          64     0.0240          41.6          20.9%
```

The whole-book HHI does fall (0.0114 → 0.0096), which is what B3(b) asked. But that is close to
mechanical — adding 133 names to a book lowers a Herfindahl almost regardless of what they
contain. The more informative number is the third row: **the mid/small tier is on its own the
most concentrated slice in the study**, 2.5x the mega/large HHI. I wrote that bar and it was
too easy. Read B3(b) as "passed, on a weak test".

---

## 4. THE FINDING THAT REFRAMES THE REST — the random-entry control

Nothing in this project's options work had ever compared the alert book against an
unconditional baseline. Placebos exist elsewhere in the codebase (`congress.py`, `edgar13d.py`)
but the options lane had none, so "+12.33% per trade" had never been asked the obvious question:
**compared to what?**

The control: for every real trade, draw a random trading day for the **same ticker in the same
calendar year** and run the identical contract rule, fill model and exit discipline. Holding
name and year fixed removes "this name went up over the decade" and "2020 was a good year".
The only remaining difference is whether the scream-buy signal chose the day.

```
                        real book              random-day control        difference
overall            n=3042  +5.14%  PF 1.16    n=8417  +13.22%  PF 1.44      -8.08pp
  mega              n=852  +6.21%             n=2867  +11.61%              -5.40pp
  large            n=1590  +2.31%             n=4200  +10.42%              -8.11pp
  mid               n=567  +9.80%             n=1273  +24.35%             -14.55pp
  small              n=33 +34.36%               n=77  +42.43%              -8.07pp

paired by name-year cell (1,052 cells):  mean -4.71pp   median -7.69pp   t = -2.18
alert book wins in 441 of 1,052 cells = 41.9%           sign-test z = -5.24
```

The alert book loses to its own control in every tier, in 9 of 10 years, and in 58% of
name-year cells. Contract characteristics are near-identical, so this is not a selection
artifact of what gets bought: median DTE 58 vs 58, median delta 0.355 vs 0.351, median premium
$4.85 vs $4.50, median entry spread 4.78% vs 4.32%. The difference is entirely in outcomes —
targets hit 23.2% vs 28.3%, stops hit 48.7% vs 46.4%.

**Robustness.** Two independent seeds. Pooled gap −8.51pp (seed 0) and −7.64pp (seed 1): the
headline replicates. The *paired t* is less stable — −2.67 on seed 0, −1.56 on seed 1, −2.18
pooled — so I would not lean on the t-statistic. **Lean on the sign test**: 45.7%, 44.2% and
41.9% of cells won across the three, all far below 50%, z = −5.24 pooled, and it makes no
distributional assumption about a heavy tail.

**The economically coherent reading**, which is also the failure mode the trade autopsy brief
named in advance: the alert requires a strong technical run-up to have *already happened*. It
is a momentum-chasing entry that buys an extended underlying into elevated short-dated IV. Over
2016-2025, on these names, that was worse than picking a day out of a hat.

### What this control does and does not establish

- **It does establish** that the alert's day-selection subtracts value on this universe and
  window, and that the profitability of the book comes from something other than the signal.
- **It does NOT establish** that random call-buying is a good strategy. The control is *equally*
  contaminated by the universe's selection (below), carries no position-sizing or capital
  constraint, and enters on days the real book was already holding. It is a benchmark, not an
  alternative. The comparison is valid precisely because both sides share the same
  contamination.

---

## 5. THE UNIVERSE IS SELECTED, AND THE BIAS RUNS TOWARD THE EDGE

Two selection effects are baked into the cache and cannot be removed by anything done here.

**(a) The miner skipped thin names on purpose.** Of **245 names evaluated**, 187 are complete,
**55 were skipped as thin** by median spread and ATM open interest, and 3 are partial. The thin
skips are exactly the names where wide fills would eat the edge, so the broad universe arrives
already spread-filtered. This is counted in the shipped result (`selection.by_status`), not left
in a comment. The selection snapshot is frozen into the run's state file, because the miner
keeps adding names and an un-frozen count would drift between runs.

**(b) Today's liquidity chose the names, so the small-cap tier is future winners in their small
days.** This is the more serious one and it is quantified:

```
tier    median (today's cap / cap at entry)
mega              1.53x
large             1.49x
mid               3.25x
small            14.78x     <- AMD, SHOP, NET, HOOD, MRVL, VRT, CDNS, FTNT, AEM, KKR
```

The `small` tier is not "small-cap stocks". It is a handful of names caught in 2016-2017 that
went on to compound 15x, and they are in this cache *because* they compounded. That is why its
+34.36% must not be read as a cap effect.

**Splitting each tier by that hindsight growth is the diagnostic**, and it is uncomfortable:

```
tier    low-growth half                high-growth half
mega    n=426   -0.46%  PF 0.99        n=426  +12.87%  PF 1.43
large   n=795   -3.76%  PF 0.89        n=795   +8.37%  PF 1.27
mid     n=284   +6.65%  PF 1.22        n=283  +12.96%  PF 1.46
small   too few to split (33)
```

In mega and large — 2,442 of 3,042 trades — **the entire edge lives in the names that later
grew, and the other half is flat to negative.** Only the mid tier is positive on both sides.

This split conditions on the outcome, so it is partly circular: a call on a stock that rose 5x
makes money whether or not the entry was skilful, and it can never be used as a filter. It is
still the right diagnostic, and combined with §4 the honest conclusion is that **this cache
cannot separate the strategy's edge from the universe's upward selection.** A forward track can.

---

## 6. term_slope OUT OF SAMPLE — the gain replicates, the retention arm fails

The threshold (+0.0105) was fitted on the 55-name 2016-2020 half. The 133 new names never
informed it, so applying it unchanged is a genuine out-of-sample test.

```
                              kept              exp: all -> filtered      gain
new names, late half      412/1132 (36.4%)      +4.64%  ->  +13.54%     +8.89pp
new names, full sample    630/1695 (37.2%)      +3.98%  ->  +11.27%     +7.29pp
whole broad book, late    656/1759 (37.3%)      +4.90%  ->  +12.41%     +7.51pp
(for comparison, the 55-name result that adopted it)                    +8.12pp
```

**The economic effect replicates almost exactly** — +8.89pp out of sample against the +8.12pp
that got it adopted. And it is not buying that by clipping the tail: it retains 41.2% of the
≥+100% winners while keeping 37.3% of trades, so it is mildly tail-*enriching*.

**But B2 FAILS**, on one arm: retention is 36.4%, below the pre-committed 40% floor. That floor
was already only just cleared on the 55 names (40.6%). On a broader book the filter is more
selective and drops under it.

I am reporting this as **FAIL**, because that is what the pre-committed gate says and the whole
value of a pre-committed gate is that it is not renegotiated after the fact. The honest summary
is: *term_slope's economic effect generalises to names it never saw; the filter now keeps too
small a share of a broader book to clear the bar as written.* Whether a 40% floor is the right
bar for a 187-name universe is a legitimate question — but it must be argued and re-committed
before a run, not after this one.

---

## 7. THE AUTOPSY HEADLINE RE-CONFIRMS — nothing beyond term_slope, on the wider set

The #23 gate was re-run **unchanged** on the broad log (the sweep was not re-implemented; `run()`
took a `trades` override so the two results stay comparable).

```
features tested            64            (same as the 55-name run; 0 dropped for coverage)
held-out hypotheses       127
SURVIVORS                   0            (55-name run: 1, term_slope itself)
BH-FDR discoveries          0
PBO (CSCV)              35.7%            (55-name: 42.9%)
combiner escalation      not warranted; logit and HGB both reject, all p >= 0.36
```

Feature coverage is genuinely lower here — 2,030 of 3,042 trades carry the contract-level greek
stack and 2,071 the daily surface, because `data/options_derived/` covers 111 of the 187 names.
So the greek/GEX features are tested on ~2/3 of the book. Everything still rejects, and nothing
came close.

**Mid/small caps do not surface a feature that separates winners from losers.** The answer to
the mandate's item 5 is the same as it was on 55 names, now on 3,042 trades.

---

## 8. SANITY AND COVERAGE — clean, zero flags

```
settled at intrinsic       0.07%    (exit paths come from real quotes, not bar settlement)
max single-name share       1.6%    (185 names carry trades, median 15 each)
entry spread              median 4.78%, p90 13.3%; ZERO trades above the 25% ceiling
exit mix                  stop 48.7% | time-stop 27.2% | target 23.2% | expiry 0.9%
signal coverage           term_slope 92.6% | vrp 99.7% | gex_proxy 95.8% | skew_25d 52.9%
                          entry_spread_pct 100% | iv 75.3%
```

**One number I do not trust and did not use:** the `iv` field is front-expiry ATM IV, often
solved on a contract days from expiry, and its median reads 1.28-1.57 across tiers. That is
implausible as a real ATM vol and it is unstable by construction. It is descriptive only —
no verdict in this file rests on it — but nobody should quote "median IV by tier" from the
shipped JSON. The reliable vol read is `term_slope`, which is a *difference* of two solves on
the same surface and is far better behaved.

---

## 9. VERDICT AGAINST THE PRE-COMMITTED BARS

| Bar | Result |
|---|---|
| **B1** edge holds (exp>0, PF>1, both halves) | **PASS** — label HOLDS, but halved and DSR now 88% unfiltered |
| **B2** term_slope generalises out of sample | **FAIL** — on retention (36.4% vs 40%); the +8.89pp gain arm replicates |
| **B3** keep the mid/small tier | **PASS** — +11.15% on 600 trades, HHI falls — but on a weak de-concentration test |
| **B4** home-run thesis | **NOT UPHELD** — P(tail) difference +1.86pp, CI spans zero |
| **B5** headline at aggression 1.0 | held throughout; mid fills reported only as the §2a decomposition, where they cost 6.59pp |

**And the bar I had not pre-committed, because this project had never run it:** the alert book
loses to a random-entry control by 8.08pp, in every tier, in 9 of 10 years, in 58% of name-year
cells. Had that been a bar, it would be the one that failed.

---

## 10. HONEST FRAMING — this is expanded but still PARTIAL

- 187 names is 3.4x the old universe and still not the liquid universe. The miner is running;
  re-run when it finishes. It is one command.
- Everything here is one 10-year window on one vendor's cache, selected by today's liquidity.
- The `small` tier (33 trades, 10 names) is below any standard I would defend. Ignore it.
- Borrow, assignment and early exercise are not modelled (long calls — none bind).
- Exits walk daily closes; an intraday spike through the target that closes back below is
  recorded as a miss. Conservative, and consistent with the 55-name run.
- 2026 is excluded by the entry cutoff, so this says nothing about the current year.

---

## 11. RECOMMENDED NEXT STEP

**Do not ship a change to the live options alert on the strength of this run — and do not
quietly keep quoting +12.33%/trade.** The two things worth doing, in order:

1. **Settle the control finding before anything else.** If the scream-buy alert genuinely picks
   worse-than-random days, that is the single most important fact about the options lane, and it
   is a bigger deal than any filter. The cheap next test is to decompose it: is it the *technical
   run-up requirement* (buying extension) or the *options-flow component* of the score? Run the
   control against alerts split by score band and by which labels fired. That is a one-command
   re-run over the banked log plus one more control pass.
2. **The forward paper track is now the priority it always was**, and for a sharper reason than
   before: §5 shows this cache cannot separate the strategy from its universe's upward
   selection, and §4 shows the signal is not carrying the result. Only out-of-sample time fixes
   either. → **Cowork's lane** (tracked "Valquo Index vs SPY").

Explicitly **not** recommended: re-tuning term_slope's retention floor to make B2 pass, or
promoting the mid/small tier on the strength of §2 before §5 is resolved.

---

## FILES

| Path | What |
|---|---|
| `valuation/edge/options_universe.py` | the study — gate, tiers, concentration, control, survivorship probe, sanity |
| `optuniv_run.py` | resumable runner; `--control`, `--autopsy`, `--analyse-only`, `--aggression`, `--universe-from` (pins the name list to an earlier run so a second pass varies one thing, not two — the miner keeps growing the cache mid-flight) |
| `valuation/edge/options_autopsy.py` | one change: `run()` takes a `trades` override so the #23 gate runs unchanged on a different log |
| `data/options_universe/` (gitignored) | `state.pkl` (headline, a=1.0), `state_mid.pkl` (a=0.0 diagnostic, same pinned names), `control_rows.pkl` + `control_rows_seed1.pkl`, `UNIVERSE_RESULTS.json`, `AUTOPSY_BROAD_RESULTS.json` |

`data/options/` was **read-only** throughout; the miner's 55-name `AUTOPSY_RESULTS.json` is
untouched, and the broad autopsy went to a separate file.

**Tests: 142/142 edge (9 new), and all 14 other suites green.** The new tests pin the bars that
would otherwise rot: point-in-time cap tiering, the de-concentration bar rejecting a book that
still rests on one name, the home-run CI, term_slope being *applied* and never re-fitted,
WEAKENS-not-HOLDS when one half is negative, total-loss vs stop-out separation, the entry window
clearing max DTE, and the headline being the ask rather than the mid.

### Two bugs I introduced and caught

1. **The universe silently excluded every post-2016 IPO.** My first pass required a `.pkl` for
   all 10 years, but a pre-IPO year is a `.empty` marker, not a frame. That dropped ABNB, DASH,
   HOOD, CVNA, ARM, CRWD and 19 others — 25 names, exactly the younger and smaller cohort this
   study exists to add, biasing the universe back toward megacaps. The run was killed and
   relaunched. Caught because the count printed 162 when the manifest said 184.
2. **A test that could not fail.** The first de-concentration test built a megacap book whose
   tail was already single-name, so *any* addition lowered the Herfindahl and the assertion
   passed for the wrong reason. Rebuilt so mega starts diversified and the added tier is the
   concentrated one; it now fails without the bar.
