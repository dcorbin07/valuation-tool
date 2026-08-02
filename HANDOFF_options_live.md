# HANDOFF — the validated single-leg options edge, wired LIVE (roadmap #21, 2026-08-02)

Single-item session per `PROMPT_options_live.md`. Written to this file rather than
`HANDOFF_STATUS.md` because other agents were running concurrently on the same repo.

## What changed, in one line

The scream-buy alert stops being a DESCRIPTOR ("~35Δ call, ~60 DTE") and becomes a **real
contract off the live broker chain**, with the term-structure filter actually applied, a
per-alert expectancy-confidence, a whole-contract size against a dollar risk budget, and a
paper book that can finally be scored.

## The one property that matters most

**There is no second implementation of the strategy.** `options_live.pick_live_contract`
normalises the broker chain into the frame shape `options_backtest` already consumes and then
calls `options_backtest.pick_contract` — the actual function, with the constants imported rather
than restated. `test_live_engine_reuses_the_backtested_selector_rather_than_copying_it` asserts
the constants are the *same objects* and spies on the call, so a future "live version" of the
selector fails the suite instead of drifting quietly.

Three consequences that were choices, not accidents:

* **Delta is re-solved from the mid by Black-Scholes**, not taken from Tradier's `greeks.delta`.
  The 35-delta target is defined in terms of the BS-from-mid estimator the backtest used (phase 1
  validated it against ThetaData at 98.96% agreement). The broker's delta is still recorded as
  `broker_delta` with a `delta_source_gap`, so a divergence surfaces as data.
* **The liquidity gate is the backtest's** (`options_fill.quote_reject_reason`), so a live alert
  cannot be issued on a contract the backtest would have refused.
* **Entry premium is the ASK, not the mid.** Every validated number is net of the punishing fill.
  Sizing off the mid would deploy more contracts than the tested book and quote an entry nobody
  gets.

## Behavioural change to production — Don should know about this one

`options_term_filter` now defaults to **`suppress`** (was `flag`), so backwardation alerts are
**dropped, not labelled**. That is roughly a **60% cut in alert volume**. It is the change the
task asked for and it is the right one — an unapplied filter leaves the live alerts carrying the
full fade it was adopted to arrest — but it will be visible immediately as "far fewer alerts".

Reverting is one env var: `OPTIONS_TERM_FILTER=flag`.

The fail-open property is untouched and is what makes suppression safe: **missing term data is
`None`, never `False`**, so a quote-feed outage cannot masquerade as backwardation and silently
halt alerting.

## The honest caveat on the filter, and the instrument that will detect it

The threshold (0.0105, ~1 vol point) was fitted on **IV solved from the mid by bisection** on
ThetaData. Live, a broker serves its own smoothed surface. **A threshold that small need not
transfer between IV estimators**, and if it doesn't, the live filter is not the filter that was
tested.

Two things guard it:

1. `options_live.term_read` prefers the **chain** and solves IV the fitted way, falling back to
   the broker's published IV only when no chain is at hand — and it reports which in `source`.
2. `term_filter_stats` compares **live retention against the backtested 40.6%** and says so in
   words: "consistent … appears to have transferred", or "**DIVERGES** … investigate before
   trusting the filter live", or "too thin" under 30 readable alerts.

**Action for whoever watches the first weeks: read that note.** A live retention near 40% is
evidence the threshold transferred. 5% or 90% is evidence it did not, and the filter should be
distrusted until that is explained.

## Per-alert confidence — and the two things it deliberately refuses to be

It is **expectancy-confidence**, from the backtest's bucket tables (IV regime / DTE / delta /
term structure, transcribed as committed constants because `data/` is gitignored).

* **It is not a win probability, and says so on every result.** The backtested hit rate is
  **37.4%** — most single-leg trades lose a little and a minority win big. `is_win_probability`
  is a machine-readable `False` and `disclaimer` ships on every payload, so a UI cannot omit it
  by accident. The Discord and email bodies carry the same caveat wherever a level appears.
* **It is fade-discounted, not full-sample.** Every bucket is a full-sample number dominated by
  2016-2020 (+16.4% early vs +4.4% late). Each is multiplied by `FADE_FACTOR = 0.044/0.104 ≈
  0.423` before display. The term bucket is exempt because it was already measured on the late
  half only; discounting it too would count the fade twice.

**A derived number, flagged as derived.** phase 3b never printed the backwardation expectancy,
but it is pinned by the two figures it did print: `(0.0476 − 0.406×0.1288)/0.594 = **−0.79%**`.
That is the honest case for gating rather than garnishing. It ships as
`TERM_BUCKETS["backwardation"]` with `derived: True` so nobody later cites it as measured.
`test_confidence_backwardation_bucket_is_the_arithmetic_complement` pins the derivation.

## Two real design flaws my own tests and smoke run caught

Recording these because both would have shipped something that looked fine.

1. **An alert with NO CONTRACT could score "high".** With the chain down there is no contract,
   so DTE and delta are unknown — but IV regime and term structure alone still produced a
   confident-looking estimate. Every bucket in those tables was measured on trades that *had* a
   35-delta 45-75 DTE contract, so that is borrowed authority for a trade nobody can place.
   Fixed by requiring ≥3 calibrated dimensions, which is exactly the condition "a contract
   resolved". A chainless alert is now capped at **thin**.

2. **The confidence badge would have read "high" on essentially every alert.** With the gate on,
   every displayed alert is contango, so the term bucket (+12.88%, a quarter of the mean) is
   effectively constant and the estimate can only range over **0.0511 … 0.0812**. The intuitive
   "high above +5%" cut fires on all of it — a decorative badge. The cuts are now set from the
   reachable span (high ≥ 0.072, moderate ≥ 0.058), and
   `test_confidence_scale_actually_discriminates_among_the_alerts_users_see` pins that the best
   and worst contango fingerprints land on different levels and that the cuts sit inside the
   span. This is a **display calibration** — it changes no alert (the term gate decides that)
   and only moves suggested size within the capped 0.5–1.0 range.

## Sizing — a suggestion, and two rules that are easy to get wrong

`contracts = floor(risk_budget / (premium × 100))`, whole contracts only, confidence-scaled.

* **Skip, do not round up.** If one contract already costs more than the budget the alert is
  skipped rather than taken oversized — 13.0% of backtested signals fall here at $1,000. Taking
  one anyway is how a risk rule becomes decorative.
* **The affordability test uses the FULL budget, not the confidence-scaled one.** Otherwise a
  moderate-confidence alert would be dropped for cost rather than conviction, and the confidence
  scale would quietly become a second liquidity filter.

Budget is `OPTIONS_RISK_PER_TRADE` (default $1,000). Nothing is routed to a broker anywhere in
this task.

## The paper book — and the one thing blocking it

`options_paper.paper_report` reports live realized expectancy against **the reference it is
actually comparable to**. That reference is *not* the +10.4% headline: the live book runs behind
the term gate, so the fair comparison is the **gated late-half +12.88% (n=307)**. The full-sample
and ungated-late figures ship alongside, each labelled with what it includes, because quoting the
wrong one would flatter or damn the live book for a reason unrelated to it.

The headline stays **backtested** until the live sample clears 30 closed trades — same rule as
the stock index — and the label reads `live since <date>, thin (N closed of M logged)`.

**BLOCKING DEPENDENCY → Cowork.** This app writes the alert and its contract; it cannot reach a
broker to see fills. **Nothing ever closes unless the external Robinhood job calls
`options_tracker.record_outcome`.** Until it does, the book accumulates open alerts forever and
the forward track — the single most important validation the edge has left — never starts.
That job now has something worth filling in: rows carry a real strike, expiry and entry premium,
so they are scoreable, which they were not before.

## Files

    valuation/edge/options_live.py         live contract pick, term read, sizing, alert assembly
    valuation/edge/options_confidence.py   bucket tables + fade discount + the caps
    valuation/edge/options_paper.py        forward book vs the gated reference
    valuation/intraday/providers.py        get_option_chain() on Tradier + yfinance
    valuation/intraday/term_filter.py      default -> suppress; apply_with_stats()
    valuation/saas/notify.py               live contracts in the alert path, Discord + email
    valuation/config.py                    options_term_filter default; options_risk_per_trade
    valuation/web/app.py                   /api/options-alerts, /api/options-paper

`app.js` and the templates were **not touched** — the app-fixer owns those. The work is exposed
as two self-contained endpoints for whoever wires the UI.

## Tests

**119/119 edge, 20/20 saas, 18/18 intraday, 14/14 bulk, 28/28 engine, 22/22 screener.**
Eighteen new, plus one existing test updated: `test_live_term_structure_filter` used to assert
`DEFAULT_MODE == MODE_FLAG` ("default must annotate, not suppress"). That assertion was correct
when written and is now inverted deliberately; the docstring records why rather than deleting the
old reasoning.

## Recommended next step

1. **Run one live scan with a Tradier token and read `term_filter.note`.** Everything else here
   is tested offline against synthetic chains; the one thing that cannot be tested offline is
   whether the threshold transfers to a real broker's IV surface. That is a five-minute check
   with a real answer.
2. **→ Cowork: wire `record_outcome`.** Without it the paper book never closes a trade and #21
   delivers alerts but no forward track.
3. The standing top priority is unchanged: **a forward paper track vs SPY**. Both options arms
   and the stock index have still only ever seen historical data.
