# HANDOFF — first live-scan validation of term_slope (2026-08-02)

Single-item session per `PROMPT_options_livescan.md`. Own file, other agents running concurrently.

## The answer

**The threshold transferred. No re-fit was needed.** But that verdict only became visible after
fixing **two live bugs**, either of which would have been reported as "it does not transfer".

    live retention (fitted estimator)   45.5%    95% CI [32.3%, 58.6%]
    live retention (broker surface)     41.8%    95% CI [28.8%, 54.9%]
    backtested retention                40.6%    -- inside both intervals

Run: 55 names (the backtest's own pool), Tradier `live`, quotes of 2026-07-31, all 55 chains
fetched, 55/55 contracts resolved. Raw output in `data/options/LIVE_TERM_CHECK.json` (gitignored),
reproducible with `python optlive_check.py`.

## Distributions

    series                                     n     median     mean      sd     >=thr
    backtest alerts 2016-2025 (ThetaData)    1540   +0.0019  -0.0295  0.1359   43.3%
    live, BS-from-mid (the FITTED estimator)   55   +0.0078  +0.0174  0.0782   45.5%
    live, Tradier published greeks             55   +0.0036  +0.0090  0.0740   41.8%

The two live estimators agree on the **gate decision for 45 of 55 names (81.8%)**, and their
medians sit within half a vol point of each other. That is the direct answer to the question the
threshold posed: a constant fitted on mid-solved IV is not invalidated by a broker's smoothed
surface.

**The live distribution is TIGHTER (sd 0.078 vs 0.136) and centred slightly higher.** Both are
expected and neither is evidence of a broken estimator:
  * one calm Friday against ten years that include 2018, 2020 and 2022 — the backtest's fat
    negative tail (p10 −0.129) is vol events, which a single quiet snapshot cannot contain;
  * the backtest rows are **alert days** (a scream-buy actually fired), this samples all 55 names
    unconditionally, and term structure on a breakout day need not match a random Friday.

## What this test could and could not detect

It had power to rule out **gross** non-transfer — a threshold landing at the 5th or 95th
percentile of the live distribution, which is what a genuine estimator mismatch looks like. With
n=55 on one day it **cannot** distinguish 40.6% from 45.5%; the CI is ±13pp. Read it as "the gate
is doing roughly what it did in the backtest", not as a precise agreement.

**Must be re-confirmed on a moving market Monday.** These are Friday's closing quotes.

## Bug 1 — the ATM IV was read off the wrong strike (severe, pre-existing, live)

`TradierProvider.get_option_summary` ranked contracts by
`abs(strike - (o.get("underlying_price") or 0))`. **Tradier option rows do not contain
`underlying_price`** — the field simply is not in the payload. `.get()` returned None, `or 0`
collapsed it to zero, and "nearest strike to zero" is the *lowest strike on the board*.

    AAPL @ $308.91    atm_iv 1.4917   atm_iv_60d 2.2997   (read off the $50 strike)
    true ATM                                    ~0.256

Every name was affected, and the consequent term slopes were nonsense at a scale that swamped the
0.0105 threshold by two orders of magnitude:

    AAPL +0.808    MSFT -0.933    KO -1.023    XOM -0.598    JPM -0.814

So the term gate shipped in #21 was **suppressing alerts essentially at random** — 4 of those 5
names would have been discarded for no real reason. The same corrupted `atm_iv` also feeds the
options component of every live intraday score, so the blast radius is wider than the gate.

**Fix:** ATM is now located by `|delta| → 0.50`, which is what at-the-money *means* and needs no
underlying price — so it cannot silently degrade when a field is absent, which is exactly how the
original failed. An implausible `mid_iv` (outside 2%–150%) now **loses** to the smoothed
`smv_vol` rather than beating it; the old code preferred the raw solve. After the fix the same
five names read 0.32/0.26/0.20/0.31/0.21 — plausible, and slopes in the ±0.07 range.

## Bug 2 — the clock, which nearly produced a false negative

Time to expiry enters Black-Scholes under a square root, so an as-of error scales solved IV by
`sqrt(T_true / T_assumed)`. Negligible on the 45–75 DTE contract the strategy trades; **enormous
on the ~3-DTE front leg that `term_slope` differences against.**

Reading Friday's quotes on a Sunday — a one-day error out of three — gave:

    as_of = today (Sun)      front T=1d   BS IV 0.4711   slope -0.1979
    as_of = quote date (Fri) front T=3d   BS IV 0.2756   slope -0.0079
    broker's own IV                              0.2683

The first row is pure artefact. Across the first five names it produced slopes of −0.11 to −0.30
against broker readings of −0.04 to +0.06, and I was one step from writing it up as the transfer
failure this task was sent to find. **It is not a weekend curiosity** — it fires on any scan run
against a stale feed: pre-open, holidays, or after a feed stall.

**Fix:** `options_live.chain_as_of` derives the date from the quotes themselves
(`greeks.updated_at`, `trade_date`) and `resolve_as_of` is used everywhere instead of
`date.today()`. During market hours the two agree and behaviour is unchanged.

A hypothesis I checked and **discarded** rather than assuming: that the expiry calendar densified
(1-DTE expiries today vs monthlies in 2016) making the front leg incomparable across eras. The
cached ThetaData chains say otherwise — AAPL's front-expiry DTE is median 3 (min 1, max 8) in
2016, 2020 *and* 2025 alike. The backtest's front leg was just as short-dated. The problem was
the clock, not the calendar.

## Fix 3 — the gate was deciding on the wrong estimator (ordering)

The gate ran inside `screaming_buys`, on the cheap whole-universe summary, **before** any chain
was fetched — so the better chain-derived read computed moments later in `build_alerts` was
decorative, and Bug 1 could suppress alerts silently. The authority now sits in
`options_live.apply_term_gate`, applied after the chain fetch on the estimator the threshold was
fitted to. `run_alerts` passes MODE_FLAG to the cheap pass and gates afterwards. Fail-open is
unchanged: `term_ok is None` is never suppressed.

Suppressed names are still marked alerted for the day, or every later scan would re-evaluate and
re-suppress them.

## Live output sanity, on real chains (task item 3)

    contracts resolved     55/55
    quote date resolved    2026-07-31 on every name (front leg 3 or 7 DTE)
    delta                  median 0.354  (target 0.35), range 0.267-0.440
    DTE                    49 on every name, band 45-75, none out of band
    BS vs broker delta     median gap 0.0078, max 0.0334
    quote integrity        0 crossed/locked quotes; entry premium == ask on all 55
    sizing                 42/55 sized; 13 skipped, ALL "one contract exceeds budget"
                           (MSFT $11.00 ask = $1,100 vs a $1,000 budget) - the intended rule
    confidence             33 low / 22 moderate / 0 high - the scale discriminates
    actionable             18 (contango AND sizeable)

The delta spread (0.267–0.440) is the strike ladder, not a selector fault: coarse ladders on
cheaper names have no contract nearer 0.35. Every name resolving to the same 49-DTE expiry is the
September monthly being the only well-populated expiry in the band right now — worth knowing,
because it means the `65-75 DTE` confidence bucket is currently unreachable in practice.

A chain-fetch failure still degrades to thin/not-actionable rather than raising: verified in the
run (an exception path is counted in `stats["chain_failures"]`) and pinned by
`test_live_alert_degrades_honestly_when_the_chain_is_unavailable`.

## Files

    optlive_check.py                    the live-vs-backtest comparison (re-runnable)
    valuation/intraday/providers.py     atm_iv_from_chain() - Bug 1
    valuation/edge/options_live.py      chain_as_of/resolve_as_of - Bug 2; apply_term_gate
    valuation/saas/notify.py            gate moved after the chain fetch
    tests/test_edge.py                  4 new regression tests

## Tests

**123/123 edge**, 20/20 saas, 18/18 intraday, 14/14 bulk, 28/28 engine, 27/27 screener.
Four new: the missing-`underlying_price` ATM bug, the quote-date resolution, the stale-quote
front-leg inflation (built on a FLAT term structure so any material slope is the artefact), and
the relocated gate's fail-open behaviour.

## Recommended next step

1. **Re-run `python optlive_check.py` on Monday during market hours.** Same command; the only
   thing it needs is a moving market. Compare retention against the 40.6% and the 45.5% recorded
   here. That converts a weekend snapshot into a real reading.
2. **Bug 1 corrupted the options component of the live intraday SCORE, not just the gate.** Every
   scan before today ranked names using ATM IVs that were 5-10x too high. Worth a look at whether
   any historical live scan output or archived `opt_atm_iv` in `edge/archive` needs discarding —
   I did not touch the archive, and it is outside this task's lane.
3. Unchanged and still Cowork's: wire `record_outcome` so the paper book can close a trade.
