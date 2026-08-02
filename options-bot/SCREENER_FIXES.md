# Screener — second pass

**36 tests where there were zero.** `cd screener && python -m unittest discover tests`

The README described four modules as "built + unit-tested." There were no test
files anywhere in the project. Every bug below was live, produced no symptom,
and would have kept producing plausible-looking wrong numbers indefinitely.

---

## 1. The health gate aborted every run

`if feed_errors > 0`, evaluated across ~13,000 tickers x 2 external feeds
(SEC EDGAR + Stooq). Zero errors across 26,000 network calls is not an
achievable target — one timeout, one rate-limit, one delisted ticker, and the
whole day was skipped. With `UNIVERSE_LIMIT = None` by default it would have
fired on the very first live run and every run after it. **The screener could
not have run successfully even once.**

Now a RATE against tickers actually attempted, with an absolute floor so a
small universe can't trip on a handful of failures. The universe floor is a
rate too: the old hard `< 500` called a curated IWM+IJR seed "broken," which
is the exact configuration the README recommends.

Also fixed: `health_check(max_price_age_hours=24)` was passed the literal `24`
against a `> 48` threshold, so the staleness check was structurally incapable
of firing. It's now measured from the data.

## 2. Recent IPOs silently lost their growth history

`edgar._annual_series` keyed on `fy`/`fp`, which describe the FILING's fiscal
period rather than the DATA's. One 10-K carries three years of comparatives
and all three are tagged `fy=2023, fp="FY"` — so they collapsed into a single
entry. Verified: a filing containing 1000, 800 and 600 returned just
`[(2023, 1000)]`. `rev_hist` had one element, `latest_rev_growth` came back
None, and `growth_score` fell back to neutral 50 — on the 30%-weight component
of the bucket that exists to find newly-public companies.

Multi-year filers escaped by accident, because companyfacts happens to be
ordered by `end` ascending.

Now keyed on `end`, duration-filtered so quarterly values can't masquerade as
annual, and genuinely resolving restatements by latest `filed` (the old
comment claimed to do this; there was no `filed` comparison in the code).

## 3. Point-in-time factors were 4x out of scale, intermittently

`pit_data._pit_point` selected by `(end, filed)` and never filtered on period
duration. Flow concepts appear in companyfacts at 3, 6, 9 and 12-month
durations, so once a 10-Q landed the "most recent" operating income was a
QUARTER — divided by an ANNUAL revenue. Measured:

    as_of 2024-03-01 (only the FY2023 10-K known)   opm = 0.100
    as_of 2024-06-01 (Q1-2024 10-Q now known)       opm = 0.025

A 4x drop with no change in the business. And because filers have staggered
fiscal calendars, on any given rebalance date some names carried annual
figures while others carried quarterly ones — a 4x scale difference WITHIN a
single cross-section, which `cross_sectional.zscore` then dutifully
standardized as if it were signal. `ey`, `roe` and `opm` are three of the six
factors and 50% of the backtest weight, so any IC measured on them was
measuring fiscal-calendar timing.

Flow items now resolve to a true trailing-twelve-month figure — four
consecutive quarters where available, else the latest annual — so the window
is twelve months for every name on every date. After the fix the same
transition reads 0.100 -> 0.105, which is a real quarter of growth.

(Sharadar's `ART` dimension gives this for free. Worth doing the screener's
Sharadar migration rather than maintaining the EDGAR path indefinitely.)

## 4. Insider score used half its nominal weight

`50 + 25*tanh(raw/2)` cannot leave [25, 75], so the `np.clip(..., 0, 100)`
around it was a no-op and a component nominally worth 20-30% of the composite
delivered roughly half the cross-sectional dispersion of value, quality,
momentum and growth — all of which span the full range.

It also saturated almost immediately: one $250k CEO buy scored 67.6 and ten
$10M CEO buys scored 75.0, so the size and clustering machinery stopped
discriminating exactly where conviction was highest. And `size_w` barely
discriminated at all — a $1,000 buy earned 0.556 of the credit a $250,000 buy
earned, because `log1p` is very flat over that range.

Now spans 0-100 on a log-decade size scale. Measured: nothing 50.0, one $10k
director buy 59.3, one $250k CEO buy 66.1, four $1M CEO buys 83.5, ten $10M
CEO buys 97.1, ten $10M CEO sales 3.8.

Two clustering bugs fixed alongside:

- `t.get("person", id(t))` — `dict.get` returns the default only when the KEY
  IS ABSENT, and the Form-4 parser always sets `person`, sometimes to None. So
  every unnamed filer collapsed onto the single key `None` and a genuine
  four-person cluster registered as one buyer.
- Option exercises (code M) earned the same cluster bonus as open-market
  purchases — erasing the distinction the code weights exist to draw.

## 5. Missing data was punished instead of neutralized

`quality_score` had no None guard: `(op_margin or 0)` mapped missing to 0,
scoring a data gap as a bad company, while every other sub-score returned a
neutral 50. `growth_score` used `accel = 0.0` rather than the neutral 0.5 when
prior-year growth was unknown, capping short-history names at 70 — a 30-point
penalty for being newly public.

And `edgar.get_fundamentals` emitted `nd_ebitda = 0.0` when EBITDA was
negative or missing. `0.0` reads downstream as "zero net debt," which
`quality_score` rewards with FULL balance-sheet credit — so a loss-making
company scored a pristine balance sheet. It's now None, and the weight
renormalizes onto the factors that are measurable. (`pit_data` already handled
this correctly; the two modules disagreed and the live pipeline used the wrong
one.)

## 6. The new value score was wired to nothing

`dcf_upside` — the 35% value weight of the Established bucket — was never
computed by anything, so `value_score_established(None)` returned 50.0 for
every name, every day. It was replaced last pass with sector-relative earnings
yield and EBIT/EV percentiles, but `pipeline.py` still called its own local
`compute_ev_sales_percentiles`, which only ever set the SPECULATIVE bucket's
input. The new score would have been None -> neutral -> the same constant, by
a different route. Now wired to `scoring.compute_value_percentiles`, a strict
superset, and the dead local function is gone.

---

## Still outstanding

- The forward-return tracking loop is still unwired. `store.update_returns`,
  `prices.benchmark_return`, `config.BENCHMARKS` and `TRACK_HORIZONS_DAYS` all
  exist and nothing calls any of them, so `ret_7/ret_30/ret_90` stay NULL and
  `run_review` hands an all-NULL table to the LLM (its only guard is a ROW
  count — rows exist, values don't).
- `run_backtest.py` still scores with its own factor set instead of
  `scoring.py`, and still uses the ~300 LARGEST US companies as its universe —
  the exact inverse of the sub-$10B target.
- `insider_poller.py` alerts still carry no ticker, so every one reads `?`,
  and because the throttle keys on ticker with a 3-per-week cap the poller
  goes permanently silent after three alerts. Sharadar SF2 removes this whole
  code path.
- `claude_analyst._call`'s fallback is unguarded, so an API error kills the
  run mid-flight — after Established posts to Discord, before Speculative, and
  before spend is recorded.
- `yfinance` is still absent from requirements.txt despite being the
  documented price fallback; `prices.get_history_df` still has no rate limit.
- The deep-dive prompt still renders every figure in billions, so a
  $300M-revenue small-cap prints `$0.30B` and anything under $5M prints
  `$0.00B` — indistinguishable from missing.

Model IDs are fine: `claude-opus-4-8` and `claude-sonnet-4-6` are both valid
and Active with 2027 retirement dates. I was wrong about this in FINDINGS.md.
