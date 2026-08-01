# Valquo — handoff status

Written at the end of every Claude Code session. Overwritten each time, so this is always
the current state, not a log. Plain text, no colour codes — the Cowork agent reads this
file directly.

**Session date:** 2026-07-31 (P7 currency, P8 sanity, P9b headless book, P10 sectors)
**Branch:** `worktree-p10-sectors` (P7/P8 merged to `main` at 2f0110e)

> **Scope:** P9b + P10 first, then P7/P8, then earlier sessions. Canonical numbers in
> `BACKTEST_RESULTS.json`; per-finding status in `CODE_AUDIT.md`.

---

## Hot Stocks ⇄ Valquo Index unified, with a Roth/Taxable toggle — AND the UI is finally VERIFIED

**The blocker is gone.** `pip install flask werkzeug jinja2 openpyxl reportlab` (all already in
`requirements.txt` — it was purely a missing local env) means the app now imports, renders and
serves in tests. Everything shipped blind in earlier sessions is confirmed working:

| previously unverified | now |
|---|---|
| OG/Twitter meta tags | `GET /` → **200**, `og:image` present and **absolute** |
| signup/pricing gating | `/register` → 302, `/pricing` → 302, no signup CTA in the HTML |
| options endpoints | `/api/option-alerts/open` without a token → **401** |
| **`test_saas` suite** | **20/20 passing** — unrunnable for this entire project until now |

### One ranking, two views (no second index)

`/api/valquo-index?config=roth|taxable` builds the book from **the same snapshot the Hot Stocks
tab reads**, so the Index is a disciplined *slice* of the ranking rather than a competing
screen. A test pins that: the roth 25-name book is exactly the first 25 of the taxable decile,
and the Index never reorders the ranking.

The Hot Stocks tab now carries an **account-type toggle** (roth = top-25 / ~2-month / no band;
taxable = decile / quarterly / 20% band) and both blurbs — *Hot Stocks is the full ranked screen
(discovery)*, *Valquo Index is the disciplined, backtested book you would hold and track*.

**Gating fix found by a failing test:** `/api/valquo-index` was login-walled while
`/api/hotstocks` is a public read. Login-walling one view of a ranking while the other is open
makes no sense, so it is now public too — the endpoint, not the test, was wrong.

### What is NOT done, and the decision it needs

The scan still **sources Hot Stocks from the FMP snapshot**, not `score_universe_now`. Both
views now share one ranking, but that ranking is still the live-scan one. Pointing the scan at
the Sharadar full universe is a one-function change — the blocker is a real trade-off only Don
can settle:

* **Sharadar** is point-in-time and full-universe (2,827 names, the thing that was validated),
  but the export is a **static file, currently as-of 2026-07-24** — Hot Stocks would go stale
  between manual re-exports.
* **FMP** is live and daily, but is a smaller universe and is not point-in-time.

Recommendation: keep Hot Stocks on the live FMP scan for **discovery** (users expect current
data) and drive the **Index** off a periodic Sharadar scoring, since a book rebalanced every
~2 months does not care about a week of staleness. That keeps both honest without pretending a
weekly-stale screen is live.

---

## PEAD — built and REJECTED (the decode that unblocked it stands regardless)

Gate committed results-free in `9323a08`. Signal = cumulative abnormal return over [t−1, t+1]
around the most recent announcement vs the benchmark (the surprise measured by the market's own
reaction, since we have no point-in-time estimates), plus a recent-only "drift" variant.

| signal | median IC | IC t | coverage | standalone gate |
|---|---|---|---|---|
| `pead_car` | +0.0100 | **+2.21** | 82.3% | PASS |
| `pead_drift` | −0.0020 | −0.47 | 25.1% | FAIL |

`pead_car` clears standalone but **fails the held-out margin in both directions** — early
+0.03 t / −0.08% alpha, late −0.09 t / −0.35% alpha. **REJECTED.**

**Two diagnostics that matter more than the verdict:**

1. **The drift variant has no signal.** PEAD theory says drift is *strongest* right after the
   announcement, yet the ≤63-day window scores **t −0.47** while the all-ages CAR scores +2.21.
   That is backwards — whatever `pead_car` measures, **it is not post-earnings drift**, so its
   +2.21 must not be read as evidence for PEAD.
2. **It is partly momentum we already own.** Within-date correlation **+0.286 with `ret_6_1`**,
   +0.241 with `high_prox`, +0.200 with `ret_12_1`. An earnings CAR from months ago is largely
   "this stock has been rising", which `ret_6_1` already captures at **t +3.40** — nearly double.
   Adding it dilutes a stronger signal with a weaker correlated one, exactly as the held-out
   numbers show.

Both variants stay **measured but score in no theme**, so the negative result is permanent and
re-testing is one line. A cleaner PEAD needs a real earnings *surprise* (reported vs expected),
which requires point-in-time estimates — IBES, still parked.

---

## EVENTS earnings-code legend DECODED — PEAD unblocked after being stuck since P2

Sharadar ships no legend with the EVENTS download, and the earlier guess (codes 11-17) was
wrong, so `bulk.EARNINGS_CODES` sat deliberately empty and `earnings_dates()` returned `[]`.
Rather than guess again, code **22** was identified by two INDEPENDENT signatures:

**1. Timing against the SF1 filing date.** Code 22 sits a median of **3 days BEFORE** the
filing with 46.4% of occurrences within ±3 days — the announce-then-file pattern a real
earnings release has. No other code comes close.

**2. Information content — the decisive test**, and the property PEAD actually needs. Median
absolute return on the event day, 372 tickers:

| code | events | \|ret\| on day | baseline | ratio |
|---|---|---|---|---|
| **22** | 17,996 | **2.121%** | 1.292% | **1.64×** |
| 91 | 48,207 | 1.482% | 1.293% | 1.15× |
| 71 | 14,258 | 1.459% | 1.288% | 1.13× |
| 81 / 52 / 11 / 34 / 57 | — | — | — | 0.84–0.98× |

Every other candidate is indistinguishable from a random day. `earnings_dates()` now returns
real dates (AAPL: 93 of them, cleanly quarterly — 2025-07-31, 2025-10-30, 2026-01-29,
2026-04-30).

**Coverage caveat, stated not buried:** code 22 appears ~2.83×/ticker/year, not the ~4 a full
quarterly calendar would give — EVENTS coverage of earnings is **partial**. Treat a missing
earnings date as *unknown*, never as "no announcement".

An existing test asserted `earnings_dates() == []` ("deliberately inert"). That behaviour was
correct while the legend was unknown and is now obsolete; the test was updated to assert the
new behaviour, and to check the OLD wrong guess (code 11) does *not* qualify.

---

## ML tree combiner — TESTED AND REJECTED on every criterion

Gate committed results-free in `620e0a5` before running. GBM over the 31 currency-correct
z-scored signals, target = cross-sectional rank of forward return, judged on the **same purged
CPCV paths** the linear weights face.

| metric | linear | GBM | delta |
|---|---|---|---|
| median OOS IC (15 paths) | **+0.0531** | +0.0393 | **−0.0138** |
| paths where GBM wins | — | **33%** | worse 2 in 3 |
| roth top-25 net alpha | **+10.27%** | +2.04% | **−8.23pp** |
| taxable decile net alpha | **+6.70%** | +2.66% | **−4.04pp** |
| roth net Sharpe | **0.99** | 0.68 | |

Both halves agree; the late half is brutal (roth **+16.31% → −4.48%**, −20.79pp). The one cell
where GBM wins — roth, early half, +3.86pp — is the classic signature of structure found in one
regime that does not survive into the next.

**The useful interpretation:** trees can *express* "value only pays when quality is high"; they
cannot *learn* it reliably from 110 dates of 8 themes. The linear composite is not leaving money
on the table — it is the right amount of structure for the evidence available. **Do not re-open
with a different model.** Re-open only with materially more data: longer history, higher
rebalance frequency, or genuinely new orthogonal features.

**A real bug found en route (kept):** sklearn's binner raised `window shape cannot be larger
than input array shape` because the 13F signals are empty before 2013-06-30, so an early CPCV
fold hands it an all-NaN column. The whole-panel coverage check passes *precisely because* the
later folds have data — the filter has to be **per-fold** (`_usable_features`). sklearn stays an
optional import (it is not in `requirements.txt`); a missing import returns a status dict.

---

## Valuation-regime overlay — REJECTED, harder than the trend filter

Rule + bar committed results-free in `f567d01` before running. Primary rule (**one** rule, not
three): market-cap-weighted earnings yield `sum(NI)/sum(mktcap)` per rebalance — summed, not
averaged, so one freak micro-cap cannot move it and loss-makers net off — risk-off when it sits
at or below its **20th percentile over all PRIOR dates** (expanding window, min 20 dates). An
absolute multiple would be hindsight: "over 20x is expensive" is a fact about the last 20 years
nobody knew in 1998. Median P/E and PEG were computed as **diagnostics only, explicitly not
alternative rules** — three rules would be three chances to get lucky on one episode.

| config | net ann | Sharpe | max DD | flips | invested |
|---|---|---|---|---|---|
| no overlay | +30.69% | 1.13 | −57.0% | — | — |
| off = 0% | +26.58% | 1.05 | **−57.0%** | 8 | 94% |
| off = 50% | +28.75% | 1.11 | **−57.0%** | 8 | 94% |

**Max drawdown does not move at all** — identical to three decimals in every configuration. The
rule fires on only 10 of 165 rebalances and never during the actual crash. Sharpe is worse in
**both** halves (early −0.07/−0.01, late −0.10/−0.04), and drawdown improves in neither.

**The mechanism is the failure the spec predicted:** while risk-off, the book returned
**+10.02% per period (+77.3% annualized)**. It sat out the *best* periods, not the worst.
*Expensive* and *about to fall* are different things, and an aggregate valuation percentile
picks up the former with no information about the latter. Unlike the trend filter there is not
even a tempting full-sample story to argue about.

**NOT ADOPTED.** `settings.VALUATION_REGIME_OVERLAY`, default off.

Two caveats on the reported levels (they do not affect the rule — a percentile against its own
history is invariant to a constant basis): the aggregate yield uses the panel's **quarterly**
ARQ net income, so the implied "P/E ~96x" is a quarterly-flow artifact (×4 ⇒ ~24x annualized,
which is plausible) and should not be quoted as a market P/E; and aggregate **PEG came back NaN**
because revenue growth is not persisted on panel rows — reported as unavailable rather than
approximated.

---

## Regime risk-off overlay — REJECTED, and the best argument yet for pre-commitment

The rule and its adoption bar were written and **committed in isolation (`bfbde7e`) before it
was run**, so the git history proves nothing was tuned to the outcome. Classic 200-day trend
filter: at each rebalance, benchmark close vs its own trailing 200-trading-day SMA (strictly
past closes); above → fully invested, at/below → risk-off exposure. Cash credited **0%**, which
is deliberately harsh — real bills paid 2–5% over this window, so the return give-up shown is
an overestimate.

**On the full sample it looks like an obvious adopt** (top-25, 42d, 165 rebalances):

| config | net ann | Sharpe | max DD | flips | invested |
|---|---|---|---|---|---|
| no overlay | +30.69% | 1.13 | −57.0% | — | — |
| off = 0% | +24.48% | 1.08 | −36.9% | 24 | 77% |
| **off = 50%** | +27.98% | **1.17** | **−37.0%** | 24 | 77% |

At 50% risk-off: drawdown **−57.0% → −37.0%** (20pp better), return give-up only **2.70pp**,
and Sharpe **improves** 1.13 → 1.17. **Both numeric criteria PASS.** I would have adopted it.

**The held-out criterion kills it:**

| half | base maxDD | off=50% | improvement | Sharpe Δ |
|---|---|---|---|---|
| early (has 2008) | −57.0% | −37.0% | **+20.0pp** | +0.18 |
| late | −34.8% | −34.8% | **+0.0pp** | **−0.08** |

**The entire benefit is one episode.** In the recent half it does nothing for drawdown and
*costs* Sharpe. That is exactly what criterion 3 ("must improve in BOTH halves — a rule that
only works in the half containing 2008 fits one episode") was written to catch, before any
number existed.

**Verdict: NOT ADOPTED.** Shipped as `settings.REGIME_OVERLAY`, **default `None` (off)** —
available to anyone who wants crash insurance and accepts paying for it the other ~90% of the
time. Whipsaw for the record: 24 flips over 165 rebalances (~15%), out of the market 23% of the
time.

**The transferable lesson:** a full-sample result that improves drawdown 20pp, costs almost no
return, AND raises Sharpe is exactly the shape of thing that gets adopted on sight. It took a
pre-committed out-of-sample rule to see that it was one crash wearing a strategy's clothes.

---

## Sector concentration cap — TESTED and REJECTED

A max-per-sector weight on the Roth top-25 (a concentration RISK control — **not** the
sector-NEUTRAL *ranking* rejected in P10, which re-scored every name against its sector peers;
this only skips a name once its sector is full and keeps composite order otherwise).

| cap | net α | Sharpe | max DD | Δ Sharpe | Δ maxDD | Δ α |
|---|---|---|---|---|---|---|
| none | +17.37% | 1.17 | −56.8% | — | — | — |
| 35% | +16.64% | 1.15 | −56.6% | −0.02 | +0.2pp | **−0.73pp** |
| 25% | +16.45% | 1.15 | −56.4% | −0.01 | +0.4pp | **−0.92pp** |

**REJECTED** — it costs 0.73–0.92pp of return and buys 0.2–0.4pp of drawdown and *negative*
Sharpe. No help in either half (none 1.12/1.20 · 35% 1.13/1.15 · 25% 1.11/1.18).

Two reasons *why*, which are more useful than the null: **the book is already diversified**
(mean max single-sector weight 27%, median 24%, above 35% on only 12% of dates, so the cap
rarely binds), and **the −56.8% drawdown is a market event** (2008–09), not a sector-
concentration event — capping sectors cannot help when everything falls together. If drawdown
is the worry, the lever is market exposure, not sector mix.

Sector is now persisted on panel rows and `max_sector_w` is a live parameter on both
backtests, so this is re-testable in one line if the book ever gets more concentrated.

---

## Options outcome API — the Cowork filler is unblocked

Two token-guarded endpoints (`X-Admin-Token`, same as the learning hook — the caller is a
scheduled process, not a browser):

- `GET /api/option-alerts/open?limit=N` → the work list of alerts awaiting outcomes.
- `POST /api/option-alerts/outcome` → one object or a list of
  `{alert_id | (ticker, alert_ts) | (occ_symbol, alert_ts), exit_premium, exit_ts, exit_reason,
  contracts}`. Returns `{written, failed, failures}` — an unmatched or already-closed alert is
  **reported, not silently dropped**, so the filler knows a write did not land.

**P&L is recomputed from the STORED entry premium**, never taken from the caller, so the
scorecard can never disagree with the prices the alert was logged against.

**Bug caught while writing it:** `store` inside `create_saas_app` is the **UserStore**
(accounts DB); `option_alerts` lives in the **screener** Store. My first version queried the
wrong database entirely. Both endpoints now construct the screener `Store()` explicitly, and a
test pins that source-level fact (flask is not installed here, so the routes cannot be
exercised at runtime — the endpoints are **runtime-unverified**, worth one curl after deploy).

---

## `roth` ADOPTED as the default book — and a cadence LABEL correction

`DEFAULT_BOOK_CONFIG = "roth"` (Don trades in a Roth, so no tax drag). The headless CLI takes
`--config roth` / `--config taxable`, which fixes width, cadence and band together so an
emitted book cannot drift from the construction that was validated:

```
python -m valuation.edge.valquo_index --full-universe data/backtest --config roth
  -> 25 of 861 eligible (1809 scored), rebalance every 42 trading days (~2.0 months), no band
```

**LABEL CORRECTION — the config is ~2 months, not 6 weeks.** `rebalance_days` is in TRADING
days, so 42d is ~8.4 calendar weeks. I had called it "6-week" in the previous handoff. Having
noticed, I measured the genuine 6-week point (30 trading days), which was never tested:

| cadence | Sharpe (full/early/late) | net α | turnover | cost drag |
|---|---|---|---|---|
| monthly (21d) | 1.09 (1.19/1.01) | +13.70% | 523% | 6.03% |
| 6-week (30d) | 1.11 (1.09/1.13) | +14.51% | 437% | 5.04% |
| **2-month (42d)** | **1.17** (1.12/**1.20**) | **+17.37%** | 379% | 4.40% |
| quarterly (63d) | 1.12 (1.17/1.06) | +14.99% | 300% | 3.35% |

**The construction Don adopted is still the right one** — 42d has the best Sharpe overall and in
the recent half. But a true 6-week cadence is *worse* than both its neighbours (1.11), so the
name mattered: anyone implementing "6 weeks" from the old note would have traded a worse book.
`taxable` is unchanged (decile / quarterly / 20% band).

---

## SCREAM-BUY OPTIONS: expectancy loop replacing the success-rate tracker

`options_exit.py` measured the UNDERLYING's move under an exit discipline. That answers the
wrong question twice: an option's P&L is not the stock's move (premium, theta and vega sit in
between), and a bare **"success rate" is meaningless for an asymmetric payoff** — a 40%-hit
setup whose winners triple beats a 70%-hit one that gives it all back on the losers.

New `valuation/edge/options_tracker.py` + an `option_alerts` store table:

1. **Log the CONTRACT and the fingerprint.** ticker, right, strike, expiry, entry premium,
   timestamp, plus what fired it: score, momentum/technical scores, IV and IV rank, horizon,
   target delta, DTE, options-flow read, labels, and a JSON `features` blob so a new feature
   never needs a migration. Deduped on (ticker, alert_ts, OCC symbol). Missing chain detail is
   allowed — the fingerprint is what the tuning loop learns from, so an alert with no strike is
   still worth recording.
2. **Score EXPECTANCY, never a bare hit rate:** hit rate *alongside* avg win, avg loss, profit
   factor, expectancy per trade, and cumulative P&L on a fixed 1-contract (100-share) basis.
   Profit factor with no losers reports **None, not infinity** — an undefined ratio must read as
   "no evidence", never as a spectacular score.
3. **Accrual-then-tune, hard-gated.** `MIN_CLOSED_PER_BUCKET = 30` on **both sides** of any
   comparison before a criterion may change. `tuning_candidates()` returns suggestions and never
   applies them, and lists what is `blocked` for want of trades. Options outcomes are
   heavy-tailed: with ten trades one triple-up decides the sign of every statistic.
4. **Surfaced on the Signals tab** (`/api/options-scorecard`), with thin buckets greyed and
   flagged, and an explicit "not enough closed trades to tune" line when below the floor.

**Cowork's half:** real fills and contract marks come from the Robinhood connector, which the
web app cannot reach. This app writes the alert; an external scheduled job calls
`record_outcome(...)` to fill `exit_ts / exit_premium / exit_reason`, and P&L is computed
**here** from the stored premiums so the scorecard can never disagree with them. Everything is
built to be useful while outcomes are still missing — an open alert is a complete record of the
setup, and the scorecard reports honestly how few closed trades exist.
→ **Take the outcome-filling job to the Cowork chat.**

---

## TWO SHIPPED BOOK CONFIGS — concentration chosen on Sharpe, not return

`settings.BOOK_CONFIGS` now carries two tuned constructions, and the run measures both
(`book_configs` in BACKTEST_RESULTS.json).

### Why risk-adjusted, in one table

| width | net α | net Sharpe (full / early / late) | max DD | turnover |
|---|---|---|---|---|
| top 5 | +7.20% | 0.68 / 0.92 / 0.54 | −50.2% | 336% |
| top 10 | **+20.19%** | 1.12 / 1.35 / 0.93 | −24.5% | 322% |
| **top 25** | +14.99% | **1.12 / 1.17 / 1.06** | −38.6% | 300% |
| top 40 | +12.85% | 1.10 / 1.14 / 1.05 | −37.0% | 286% |
| decile | +11.44% | 1.11 / 1.19 / 1.02 | −41.7% | 251% |

Ranking on raw alpha would have picked **top 10 (+20.19%)** by a mile — its Sharpe is a dead
tie with top 25. And **top 5 is the clean lesson**: worst return *and* worst risk.

**top 25 chosen over top 10** on stability: top 10 swings 1.35 → 0.93 across halves (gap 0.42)
vs top 25's 1.17 → 1.06 (gap 0.11), and top 25 **wins the recent half outright**. top 10's
better max drawdown is real in both halves and is the tighter alternative if wanted — but a
10-name book over 110 periods is a thin basis for a drawdown claim.

### `roth` — tax-free, Sharpe-optimal, full rotation
**top 25, 6-week rebalance, no band.** Net alpha **+17.37%**, net Sharpe **1.17**, turnover 379%.

Frequency swept (top 25, net of cost): monthly **1.09** (1.19/1.01) · 6-week **1.17**
(1.12/**1.20**) · quarterly **1.12** (1.17/1.06). Faster *does* pay — but only to a point:
monthly's 6.03% cost drag overwhelms the benefit. 6-week is best on the full sample **and** in
the recent half, with the smallest early/late gap.

Note: **fundamentals only update quarterly**, so a 6-week rebalance re-ranks on fresh prices
(momentum, market cap) over stale fundamentals. That it still wins says the price-based
components carry real short-horizon information.

**Correction worth carrying: max drawdown is NOT comparable across frequencies.** A quarterly
grid observes the equity curve 110 times vs monthly's 330, so a coarser grid systematically
UNDERSTATES drawdown. Quarterly's −38.6% vs 6-week's −56.8% is substantially a sampling
artifact — do not read it as lower risk.

### `taxable` — after-tax-optimal, decile + 20% band
**decile, quarterly, 20% no-trade band.** After-tax alpha **+4.86%**, after-tax Sharpe **0.89**
(vs 0.84 unbanded), turnover 172%.

Tax drag (7.8%/yr) is over 3× the trading cost, so this optimizes after-tax Sharpe, which
favours breadth plus the band. **The band failed the pre-committed held-out margin in one half
(see below), so it is enabled HERE — for the account where it actually matters — rather than
made the global default.**

**Method bug I caught mid-sweep:** my first band sweep silently applied the band *only* to the
decile row — `exit_frac` is a fraction of the UNIVERSE and is meaningless for a fixed-N book, so
every fixed-N "with band" row was a duplicate of its no-band row. Added `exit_mult` (band as a
multiple of book size) so fixed-N books can be banded too. With it: decile+2.5× **0.89**,
decile+20% **0.89**, top-25+2.5× 0.88.

---

## git_push.bat now auto-lands finished agent branches (no more manual merge)

Claude Code works on `worktree-*` branches because its harness will not push to `main`, so every
session ended with a hand merge. `git_push.bat` now merges them itself before committing:
**fast-forward ONLY**, and only where `main` is already the branch's ancestor — which cannot
conflict and cannot rewrite history. Anything not a clean FF prints `[skip] <branch>` and is left
for you. One `.\git_push.bat` now lands and deploys.

Verified in a scratch repo, not just eyeballed — which mattered: **the first two versions were
broken** (`--format` paren escaping, then nested quotes inside `for /f '...'` needing `usebackq`)
and both of my first two *test setups* were wrong too. Final form merges the FF branch and leaves
a diverged one untouched.

---

## No-trade band — measured, and it FAILS the pre-committed gate (kept OFF, but read this)

Today a name is sold the instant it leaves the top decile. A band enters on the top 10% and
holds until the name falls past X. Full universe, 110 dates:

| exit band | turnover | gross α | net-of-cost α | **after-tax α** | cost drag | tax drag |
|---|---|---|---|---|---|---|
| none (10%) | 251% | +13.76% | +11.44% | +3.63% | 2.32% | 7.81% |
| 12% | 232% | +13.66% | +11.51% | +3.83% | 2.15% | 7.68% |
| 15% | 206% | +12.77% | +10.86% | +3.78% | 1.91% | 7.08% |
| **20%** | **172%** | +13.32% | **+11.69%** | **+4.86%** | 1.62% | 6.83% |
| 25% | 148% | +11.93% | +10.52% | +4.40% | 1.41% | 6.12% |
| 30% | 129% | +11.97% | +10.72% | +4.70% | 1.25% | 6.02% |

**20% is the knee**: turnover −31%, gross alpha −0.45pp, net-of-cost **+0.25pp**, after-tax
**+1.23pp (a 34% relative gain)**. Long-short t is unchanged by construction (3.396) — it
measures the whole cross-section, not the book.

**Held out, it does not clear the margin.** Applying the same split discipline to the metric that
actually moves (after-tax alpha, since `quantile_backtest` cannot see turnover):

| half | no band | 20% band | Δ | |
|---|---|---|---|---|
| early | +6.82% | +7.42% | **+0.60%** | fail (< 1% margin) |
| late | +0.88% | +2.76% | **+1.88%** | pass |

**Verdict by the pre-committed rule: `not_replicated`. Left OFF.**

**But it differs from every other rejection this project has made, and that is worth weighing:**
it is **positive in both halves** and never hurts — sector-neutral and zeroing `insider` each hurt
in one direction. And the turnover reduction (251%→172%) is **mechanical, not estimated**: it is
an arithmetic property of the rule, so the cost saving is deterministic in a way a signal's IC
never is. The margin it fails was calibrated for *signals*.

I did not flip it on, because quietly re-reasoning past my own gate is the failure mode the gate
exists to prevent. **Recommendation: adopt at 20%** — `exit_frac=0.20` in `turnover_and_costs` /
`after_tax_backtest`, and the band sweep now ships in `BACKTEST_RESULTS.json` under
`no_trade_band` every run. Your call.

**Caveat on the width:** the surface is noisy — 15% is worse than both 12% and 20% on gross alpha,
which should not happen on a smooth tradeoff. Do not over-trust the exact number; 20% is the best
point measured, not a precisely located optimum.

---

## Signup + Pricing hidden behind a flag (no paid tier exists yet)

The site was still showing "Sign up" and "Pricing" with nothing to sell. Both are now gated on
**`CONFIG.signup_enabled`** — a flag, not a deletion. Every route, template and Stripe path is
intact.

It **reuses the existing free-mode flag** rather than inventing a parallel one:
`signup_enabled` defaults to `not OPEN_ACCESS` (open/free product → nothing to sign up for),
with **`FEATURE_BILLING`** as an explicit override in either direction.

| config | signup/pricing visible | Stripe checkout |
|---|---|---|
| `OPEN_ACCESS=true` (today) | **no** | no |
| `OPEN_ACCESS=true`, `FEATURE_BILLING=on` | yes | no |
| `OPEN_ACCESS=false` | yes | needs a Stripe key |

**To re-enable later: set `OPEN_ACCESS=false` (or `FEATURE_BILLING=on`) in the environment.
No code change.**

Gated at the **route** as well as in the templates — `/register` redirects to `/app` and
`/pricing` to `/`. Hiding a button leaves the URL reachable from a bookmark, a stale link or a
search result, and a half-gated signup would create accounts the product no longer expects.

Surfaces changed: nav Pricing link and "Get started" CTA, footer Pricing link, both landing
CTAs, the beta banner's "Create free account", the login page's "No account?" line, and the
account page's "Upgrade" button.

**Deliberately NOT gated: login.** Existing accounts (including Don's) must still be able to
sign in when new signups are hidden. Anonymous visitors get **"Open the app"** instead, which is
accurate — `OPEN_ACCESS` already means no account is required for anything.

Two tests pin it: the flag truth table, and a sweep asserting no template carries an ungated
`/register` or `/pricing` link (an ungated button would now silently bounce a visitor, since the
routes redirect).

---

## P9b — headless book generation (`--full-universe`)

`python -m valuation.edge.valquo_index --full-universe [DATA_DIR]` now builds the book by
scoring the **whole Sharadar universe point-in-time** instead of the last live-scan snapshot.
The store path is what produced the degraded book: a few hundred scanned names means a "top
decile" collapses to the 10-name `MIN_NAMES` floor — ten mega-caps wearing a decile's label.

Verified end-to-end: **86 positions from 861 eligible large caps, 1,809 scored, as of
2026-07-24**, no live API needed, so the Cowork quarterly rebalance can run unattended. The CLI
also warns when `n_scored < 200` and prints any names excluded for unverifiable market cap
(this run: FFAI 5x, IQMX 0x, LESL 8x).

---

## P10 — sector data unblocked, and industry-relative ranking REJECTED on its merits

**The download worked.** Sharadar TICKERS, one paged API call, cached like the bulk tables:
**48,925 tickers**, 11 sectors, plus country/exchange/category. **Sector coverage is 100.0%
(2,826 of 2,827) of the panel universe**, so `sector_neutral` — which had been grouping on a
constant `""` and was therefore INERT in every backtest ever run — is now functional.

**Then it failed the test.** Sector-neutral scoring rebuilds every z-score, so it is not a
weight change and `holdout_theme_validate` cannot express it; `holdout_compare_panels()` applies
the same discipline in the right shape (split by time, embargo the boundary, require the
**already-committed** `MIN_HOLDOUT_*` margin in BOTH directions):

| split | long-short t | top-decile alpha | |
|---|---|---|---|
| early half | 0.56 → **0.97** (+0.41) | +6.69% → +6.53% (**−0.16%**) | fail |
| late half | 0.83 → **0.61** (−0.22) | +5.06% → +4.44% (**−0.62%**) | fail |

**Verdict: REJECT.** It never clears the margin, and in the later half it is worse on both
metrics. `sector_neutral` stays **off**. The capability is now real and re-testable — a future
change (e.g. sector-relative applied to only the value theme) can be tried without re-doing the
data work.

**Look-ahead caveat, stated not hidden:** TICKERS carries *today's* classification, so applying
it to a 1998 row assumes the company was in the same sector then. Reclassification is rare and
not return-predictive, so this is normally considered benign — but it is **the one non-PIT input
in an otherwise strictly point-in-time panel**, and that is a reason to be *more* sceptical of a
positive sector result, not less. It rejected anyway, so nothing rests on it.

### The remaining ADRs in the book are genuinely cheap — not residual artifacts

With country/exchange/category finally available: ADRs are **270 of 2,827 (9.6%) of the universe
and 9 of 86 book positions (12.4% of weight)** — 1.3x representation, against 28.3% before the
currency fix. Measured against the 1,164-name large-cap cohort:

| name | book_to_price | earnings_yield | ps |
|---|---|---|---|
| WDS (Woodside) | 0.98 (97th pct) | — | — |
| SKM (SK Telecom) | 0.71 (91st) | 0.017 (80th) | 4.29 (12th) |
| TTE (TotalEnergies) | 0.75 (92nd) | 0.032 (96th) | 2.98 (8th) |
| VOD (Vodafone) | 1.85 (99th) | — | — |
| IX (Orix) | 0.66 (88th) | 0.008 (48th) | 7.42 (25th) |
| ZTO | 0.53 (81st) | 0.018 (82nd) | 8.89 (31st) |

Cheap on book, earnings AND sales simultaneously — real value names. **One exception: TSEM is
expensive on all three** (24th / 18th / 95th percentile) and is in the book on other themes, not
value. Worth an eye, but it is a single ~1% position.

---

## P7 — CURRENCY FIX. The value theme was corrupt for foreign names; fixing it IMPROVED the model.

`marketcap` and `ev` are USD, but the raw line items are in the company's REPORTING currency.
Every value ratio dividing one by the other was wrong for the 4.1% of panel rows reporting in a
foreign currency — and all were pushed the SAME way, toward fake cheapness: SK Telecom's
`book_to_price` computed to **892 against a true 0.589** (~1,500x).

### Full 2,710-name universe, before vs after

| metric | BEFORE | AFTER | |
|---|---|---|---|
| **PBO** | 13.33% | **6.67%** | halved |
| Deflated Sharpe | >99.9% | >99.9% | saturated, unchanged |
| **Top-decile alpha** | +11.77% | **+11.82%** | +0.05pp |
| **Monotonicity** | −0.9394 | **−0.9515** | better-ordered |
| Net alpha (after costs) | +11.41% | +11.44% | +0.03pp |
| Long-short t | 3.485 | 3.396 | −0.09 |
| Breakeven | 235.6bps | 235.4bps | flat |

**All six value inputs improved** — book_to_price +0.07→+0.15, earnings_yield +2.33→+2.41,
fcf_yield +3.16→+3.17, ebit_ev +2.24→+2.29, neg_ev_sales +2.00→+2.11, neg_ps +1.40→+1.51 —
lifting the **value theme t from +1.34 to +1.46**. Six for six in the same direction is a
coherent pattern, not noise, and confirms the audit's hypothesis that contamination was part of
value's weakness.

The headline barely moves because value is 1 of 7 weighted themes and only 4.1% of rows were
affected. The real wins are PBO halving and the foreign distortion disappearing.

### Foreign-name share of the top decile

| | share of top decile | universe | over-representation |
|---|---|---|---|
| BEFORE | 4.79% | 3.54% | **1.35x** |
| AFTER | 1.98% | 3.54% | **0.56x** |

From 35% over-represented to 44% under-represented — what correct ratios imply, since these
names are expensive on real numbers (TSM PE 34.8, SKM PE 61.5).

**In the live book the effect is far larger** (large-cap AND value-tilted, so it concentrated
the distortion): foreign names fell from **21 of 86 positions / 28.3% of weight to 11 / 10.7%**,
and the top 10 went from **7 ADRs to 1**.

### Two corrections to CODE_AUDIT.md itself

1. **`neg_ps` is broken too — the audit marked it "ok".** It assumed `ps` came from Sharadar's
   ratio column; the panel computes `ps = market_cap / revenue` itself (USD/local). SKM's `ps`
   was **0.00 against a correct 5.13**. Fixed. Outside the letter of the task, inside its
   intent — leaving one value input corrupt defeats the purpose.
2. **`fxusd` is a DIVISOR, not a multiplier.** It is LOCAL UNITS PER USD (SKM 1514.2 won/USD).
   The audit's suggested `fcf × fx` would have SQUARED the error (~2.3 million x for SKM).
   Verified `equityusd/equity == revenueusd/revenue == ebitusd/ebit == 1/fxusd` exactly. Also
   there is **no `netincusd` column** — `netinccmnusd` (income to COMMON) is the right numerator
   against market cap anyway.

`total_equity` deliberately stays local: `gp_on_capital` divides local gross profit by it and is
only correct while both sides share a currency. `book_to_price` is now computed in the panel in
USD, with `build_frame` preferring the supplied value.

---

## P8 — SANITY LAYER. Coverage says a factor is PRESENT; this says it is SANE.

Four foundation bugs have now shipped with one signature: the run completes, raises nothing, a
factor is silently wrong. `signal_coverage` catches only the two that left a column EMPTY. The
currency bug filled every column and was simply incorrect.

`sanity_check()` ships a `sanity_check` block in BACKTEST_RESULTS.json: **range** (ratio factors
inside a plausible band), **subgroup** (does an identifiable subgroup systematically peg a
factor), **market_cap** (DAILY vs shares × price divergence).

### Validated against the bug it was built for

On PRE-fix values the subgroup check flags `book_to_price` and `earnings_yield` — foreign
reporters sat at the **86th percentile** of both. Post-fix every value factor lands in
**0.49–0.61**. **P8 would have caught P7 on its first run.**

Bands were CALIBRATED against known-bad vs known-good values on the same rows, not guessed. My
first attempt flagged 6.1% of good rows because **negative book equity is legitimate**.
`ev_sales`/`ps` are exempt from range checks — their tails are real near-zero-revenue companies
and the band flagged identical shares before and after the fix, a pure no-op. The subgroup check
covers them.

### It fires twice on CORRECTED data. Both true; neither a currency bug.

1. **`neg_log_mktcap`, foreign reporters at the 20th percentile** — real and expected, foreign
   companies with US listings are large. A true subgroup tilt, not a defect. **Left flagged
   rather than exempted:** silencing a guard after seeing it fire is how it becomes decoration.
2. **1.45% of rows with DAILY market cap >3x from shares × price** — AIV 71x, EQC 53x, genuine
   recycled-ticker cases (AIV/AIRC spun off 2020).

### The audit's M2 (SanDisk/WDC) does NOT reproduce

The task assumed this check would catch SNDK/WDC. **It does not, and that case appears not to be
this bug:**
- SNDK's DAILY cap ($336.7B) and shares × price ($212.7B) agree to **1.6x** — inside any sane
  band. WDC 1.2x.
- Its **148M share count is plausible**.
- Its price ran **48.60 → 1436.56 over 17 months with ZERO day-over-day discontinuities**; WDC
  10.3x and MU 8.5x over the same window — the whole storage complex moved together.

The figure is internally consistent. If still wrong, the error is upstream in the PRICE, which
both estimates share and **no cross-check between them can see**. Recorded as unresolved rather
than claimed as fixed: the audit asserted "~10x reality" from outside knowledge, and nothing in
the data marks it as an error.

**In the live book**, names diverging >3x are now DROPPED — a book is meant to be traded, and a
name whose size cannot be established should not be in it. 3 dropped: FFAI (5x), IQMX (0x), LESL
(8x). SNDK/WDC are not among them and remain. The BACKTEST keeps such rows and only flags them,
so validated history is never silently re-cut by a later guard.

---

## A full run was lost to my own bug, and the guard that followed

`sanity_check`'s warning path wrote to the `sys` MODULE instead of `sys.stderr`. That
`AttributeError` was swallowed by `run_backtests`' blanket `except`, skipping CPCV, construction,
walk-forward and regime — and the run still wrote a canonical BACKTEST_RESULTS.json with **every
metric null**, exit code 0. It reads as "ran, found nothing" rather than "broke": this project's
recurring failure signature, reproduced by me.

Hardened rather than merely fixed: an **`errors` block** in the JSON and a **DEGRADED RUN
banner** in the markdown whenever a validation block throws. Plus a test exercising the WARN
path — my tests all called `warn=False` and never touched the branch that raised.

**Tests: 121 passing** (edge 63, bulk 13, engine 19, intraday 13, screener 13).

---

## P6 — IS IT TRADEABLE? Yes. Three refinements tested, all three REJECTED.

**The headline: the edge survives realistic trading costs with a ~6x margin.** Everything
else in P6 was a proposed improvement, and none of them improved anything — which is a
useful result, because two of the three were my own recommendations.

### P6.1 — COSTS. The edge is tradeable. (KEPT: the measurement is now permanent.)

Every performance number in this project had been gross of costs, and zeroing `low_risk` in
P5 tilted the book smaller-cap, which is where costs bite hardest.

| book | annual turnover | gross alpha | net alpha | cost drag | **breakeven one-way** |
|---|---|---|---|---|---|
| top decile | 249% | +13.71% | **+11.41%** | 2.30%/yr | **236 bps** |
| top 25 | 296% | +20.69% | **+17.34%** | 3.35%/yr | **293 bps** |

The weighted-average one-way cost of what the book actually holds is **37 bps**, so breakeven
sits at a **~6.4x margin**. Even a punitive flat 100 bps still leaves +7.74% net alpha.
Turnover is high (~62% of the book per quarter) but nowhere near enough to eat the edge.

**The short side does not break it either** — the thing most likely to. The BOTTOM decile is
*larger*-cap than the top (median $4.50B vs $1.95B) and cheaper to trade (29.8 vs 37 bps), so
the long-short t = 3.49 is not resting on unborrowable micro-caps. Only 17% of the long book
sits under ~$500M.

Both method choices are deliberately unfavourable to the strategy: turnover counts weight
DRIFT between rebalances (not just entries/exits), and only the strategy is charged while the
equal-weight benchmark is left gross. **Borrow cost is NOT modelled** — it affects the
long-short statistic, not the long-only book, which is the thing anyone would actually trade.

Quote the **breakeven**, not the net alpha: it needs no belief in any particular cost
calibration. Runs on every backtest now, as a `costs` block and a Tradeability table.

*Annualization caveat:* these figures compound; `construction.*` annualizes arithmetically.
Same data, +13.7% vs +11.8% gross alpha. Compare cost numbers to cost numbers.

### P6.2 — TTM ROE/ROIC: REJECTED. The quarterly figure is BETTER.

Head-to-head on identical rows in one run:

| signal | median IC | IC t | coverage |
|---|---|---|---|
| **roe** (quarterly) | **+0.0439** | **+2.84** | 93.4% |
| roe_ttm | +0.0279 | +2.01 | 91.0% |
| **roic** (quarterly) | **+0.0420** | **+3.38** | 96.7% |
| roic_ttm | +0.0354 | +2.57 | 94.2% |

Smoothing over four quarters LOSES signal on both. The likely reason is **recency**: last
quarter's profitability predicts the next quarter better than a smoothed year does, and that
outweighs the fiscal-quarter seasonality TTM removes.

**This contradicts my own P5 recommendation**, which called quarterly ROE/ROIC a
methodological wart and TTM "the obvious next refinement". It isn't — the ARQ quarterly
figure is an advantage. Section 5.6 of the P5 notes below is superseded.

Both TTM variants stay MEASURED (in `NUMBER_THEME`, in the IC table) but do not score, so the
negative result is permanent and re-testing is one edit.

### P6.3 — median/MAD robust z-scores: REJECTED, and the reason matters more than the verdict.

| metric | classic (shipped) | robust |
|---|---|---|
| long-short t | **3.485** | 1.721 |
| long-short ann | **+17.58%** | +8.42% |
| top-decile alpha | **+11.77%** | +8.99% |
| monotonicity | **−0.939** | −0.624 |
| net alpha | **+11.41%** | +8.34% |
| PBO / DSR | 0.1333 / 1.0000 | identical |

The long-short t **halved** — while every individual theme IC stayed essentially unchanged
(quality +3.39 → +3.35, momentum +2.62 → +2.68, value +1.34 → **+1.68**).

**Why: rank-IC is invariant to a monotone rescaling; the composite is not.** Theme IC is a
Spearman correlation and literally cannot see this change. The composite is a weighted SUM of
z-scores and is very much scale-sensitive. MAD < SD for fat-tailed data, so dividing by the
smaller scale INFLATES the tails, and the top decile then gets selected by whoever has one
extreme factor reading rather than broad strength across themes. **Making the scale estimate
robust made the selection less robust.**

Generalizable lesson: **a signal's IC can be flat while the composite built from it moves a
lot.** Judging this change by per-signal IC would have called it harmless; it costs half the
long-short t. Kept behind `VALQUO_ROBUST_Z` (default off) so the result is re-testable.

### P6.3b — industry-relative ranking: BLOCKED, no sector data exists.

`fundamentals.csv` has **no sector / industry / SIC column**, and the panel hard-codes
`"sector": ""` on every row — so `build_frame`'s `sector_neutral` path has been **inert in
every backtest ever run** (it groups on a constant). The metadata lives in Sharadar's
**TICKERS** table, which is API-only and not among the four bulk tables on disk.

To unblock: one TICKERS download → a ticker→sector map → populate `metrics["sector"]` in
`_sf1_to_metrics`. Not fetched here because it is an outward-facing call on Don's paid
subscription. **Caveat to carry:** TICKERS gives *today's* classification, so applying it to
1998 rows is a mild look-ahead. Sector reclassification is rare and not return-predictive so
this is normally considered benign, but it should be stated rather than hidden.

### P6.4 — consolidating momentum + institutional: REJECTED. Both earn full weight.

They are +0.50 correlated, so the hypothesis was that we pay two theme weights for one
signal. Tested on the full sample and both halves (the composite is a weighted sum, so giving
the pair 0.0625 each IS a merged theme at 0.125 — no code change needed):

| config | full LS t | full top-decile | net alpha | early t | late t |
|---|---|---|---|---|---|
| **A current (.125 / .125)** | **3.48** | **+11.77%** | **+11.41%** | 2.57 | 2.56 |
| B consolidated (.0625 each) | 2.53 | +9.21% | +8.10% | 2.01 | 1.59 |
| C momentum only | 2.86 | +10.64% | +10.18% | 2.57 | 1.29 |
| D institutional only | 2.33 | +9.40% | +7.16% | 1.70 | 1.81 |

+0.50 correlation still leaves ~75% of variance unshared: they are **complementary, not
redundant.** A useful cross-check falls out — in the early half A and C are *byte-identical*,
because `institutional` has no data before 2013-06-30, independently confirming its 61.4%
coverage. In the late half, where it does have data, A beats both single-theme variants
decisively.

### P6.0 — the holdout threshold was pre-specified, and it changed two verdicts

`MIN_HOLDOUT_ALPHA_GAIN = 0.01` (100 bps/yr — an economic floor: an "improvement" smaller
than the cost of implementing it cannot be harvested) and `MIN_HOLDOUT_TSTAT_GAIN = 0.25` (a
noise floor). **Committed in isolation, before any P6 run** (commit `4de6e71`), so the git
history is the proof of when it was fixed. Disclosed honestly: I already knew the P5 numbers,
so this is a principled tightening rather than a blind pre-registration.

Effect, exactly as designed: `capital_discipline` went **confirmed → not_replicated** (it had
only ever passed on ΔLS t +0.01) and `insider` went **not_replicated → rejected**. `low_risk`
remains the only **confirmed** theme — the only one clearing a real margin in both directions.

### P6 net effect on the shipped model: NOTHING CHANGED

Three proposed improvements, three rejections. The model is byte-identical to the end of P5
(PBO 0.1333, DSR 0.999999, long-short t 3.485, top-decile +11.77%). What P6 added is
**knowledge**: the edge is tradeable, and three plausible refinements are now measured dead
ends rather than open questions. Two of the three were my own prior recommendations.

---

## 0. HEADLINE — five factors were silently empty, and fixing them changed the verdict

Every backtest this project has ever run scored on **8 of quality's 10 inputs, 1 of
low_risk's 2, and 1 of growth's 2.** No error was ever raised. The factors were wired, the
runs completed, and the columns were blank.

After fixing that and acting on what the corrected numbers said, on the **full 2,710-name ×
110-date universe** (identical universe in every run below — 136,478 rows, 63d validated
horizon, same 16.55%/yr equal-weight bar):

| metric | baseline (P4) | final | want |
|---|---|---|---|
| **PBO** | 40.0% | **13.3%** | <50% |
| **Deflated Sharpe** | 71.7% | **~100%** | >95% |
| **Long-short ann** | +8.13% | **+17.58%** | positive |
| **Long-short t** | 1.175 | **3.485** | >2 |
| Long-short hit rate | — | 66.4% | >50% |
| **Monotonicity** | −0.782 | **−0.939** | −1.0 is ideal (see §4) |
| **Top-decile alpha** | +5.11% | **+11.77%** | positive |
| Portfolio CAGR | +15.45% | +27.91% | — |
| Alpha vs equal-weight | +1.49% | +13.95% | — |

**This is the first time the project has cleared both statistical bars** (PBO < 50%,
Deflated Sharpe > 95%, long-short t > 2) — **and the biggest single contributor, zeroing
`low_risk`, has since been CONFIRMED on a held-out time split in both directions (§4b).**
Read §5 for what that does and does not establish.

Also: **the edge no longer collapses without 13F.** Strip the institutional theme and
top-decile alpha goes +11.77% → +10.64% with long-short t 3.48 → 2.86. At baseline the same
test collapsed the t to 0.71. The "the entire edge is 13F" finding in CLAUDE.md is now
**obsolete** — that was an artifact of quality and low_risk running on half their inputs.

**Every change was kept only after confirming it improves the full-universe combined edge**
(long-short t / Deflated Sharpe / PBO / top-decile alpha). The one change that did not pass
on first measurement — dropping `neg_asset_growth` — was re-tested head-to-head in the final
configuration and does pass (§3c). The derived inputs (§3a) are a **correctness fix, not an
optimization**: they cost 0.22 of long-short t while improving PBO, DSR and top-decile alpha,
and the alternative is knowingly scoring on 8 of 10 quality inputs.

**Tests: 107 passing** (edge 50, bulk 12, engine 19, intraday 13, screener 13). `test_saas`
(18) cannot run here — no `flask`/`werkzeug` installed in this environment, unrelated to
these changes and true before them.

---

## 1. The bugs — all five produced a completed run and no error

The export is **ARQ-only**, and Sharadar populates its averaged/ratio fields only in the
ART/ARY dimensions. Verified directly against `fundamentals.csv`: `roe`, `roic`,
`assetturnover`, `roa`, `ros`, `equityavg`, `assetsavg` are **non-null in 0 of 197,265
rows.** The raw ingredients were all present (`netinc` 97.7%, `equity` 99.9%, `invcap`
99.9%, `taxexp`/`ebt` 97.7%, `assets` 100%).

1. **`roe` empty** → derived as `netinc / equity` (requires equity > 0; a negative book value
   inverts the sign and would rank a wiped-out loss-maker as the highest quality name).
2. **`roic` empty** → derived as `ebit × (1 − effective tax) / invcap`, effective rate =
   `taxexp / ebt` clipped to [0, 0.60], falling back to the **date-aware** statutory rate
   (35% pre-2018, 21% after — the TCJA cut) when pre-tax income ≤ 0 makes the rate
   meaningless.
3. **`assetturnover` empty** → derived as `revenue / assets`. This made **F-Score test 9
   evaluable for the first time**; the `≥6 usable tests` guard had been absorbing its absence
   silently.
4. **`beta` hard-coded `None`** → `low_risk` was `neg_vol` alone. The regression that
   produces beta was *already running* inside `_price_extras` for `neg_idio_vol`; only its
   slope was being discarded. Now exposed.
5. **`growth_accel` clobbered** (not on the original list — the guard found it). The panel
   computes it correctly in `_yoy` from two prior-year point-in-time rows; `build_frame` then
   overwrote it with `revenue_growth − revenue_growth_prior`, and the panel never supplies
   `revenue_growth_prior`. All-NaN. `growth` was `revenue_growth` alone.

### 1a. The mechanism that hid three of them: `_f()` returned NaN, not None

`pandas` reads a blank CSV cell as `float('nan')`, and `_f()` returned it. That is not
`None`, so **every `if x is not None` guard in the panel silently accepted missing data.**

The damaging case was **`_f_score`**: `cr > cr_p if (cr is not None and cr_p is not None)` is
`True` when `cr` is NaN, and `NaN > NaN` is `False` — so a missing input was scored as a test
the company **FAILED**, *and* still counted toward the `≥6 usable` guard. Thin rows came back
as confident low scores instead of `None`. This affected `currentratio` (blank in 18.4% of
rows) and `debtnc` (18.3%). Fixing it moved `f_score` t from +2.80 to **+2.74** and its
coverage from 96.8% to 95.1% — very slightly *weaker*, because it is now honest.

Fixing `_f` also exposed a **latent crash** in `_yoy` (`None - float`) that NaN arithmetic had
been absorbing: the growth_accel branch tested `"revenue_growth" in m`, but the metrics dict
is pre-seeded with `revenue_growth=None`, so that key is *always* present.

---

## 2. THE CHEAP FIX THAT WOULD HAVE CAUGHT ALL OF THIS — coverage guard

`signal_coverage()` measures every wired number and theme, warns to stderr under 5%
coverage, and ships the result in `BACKTEST_RESULTS.json` under `signal_coverage`
(`below_floor` is the load-bearing part). Coverage is measured on the **standardized**
column, so a present-but-constant column correctly reads as unusable rather than covered.

Confirmed against the committed baseline: `roe`, `roic`, `neg_beta`, `growth_accel` were all
at **exactly 0.0%**. The guard would have flagged all four on day one.

- The floor is 5% — far below any plausible real coverage. The thinnest genuine theme,
  `institutional`, sits at 61.4%.
- Exemptions are an **explicit list** (`COVERAGE_EXEMPT_THEMES = {"sentiment"}`), not
  "any zero-weight theme". I initially inferred it from the weight and that immediately
  went wrong: zeroing `low_risk` (§3) silently disabled the guard for `neg_beta`. A theme
  zeroed because it was *measured and found wanting* still has data, and a plumbing bug in
  it must still be reported. Only genuinely source-less hooks belong on the list.
- Free performance win: `run_backtests` now builds the validated panel once with
  `keep_numbers=True` and derives coverage + per-signal IC from it, **removing a whole
  duplicate full panel build** from every run (`main()` used to rebuild it).

---

## 3. Decisions taken, and the evidence for each

### 3a. `roic` / `roe` — the two strongest signals nobody was using

| signal | median IC | IC t | coverage | rank in panel |
|---|---|---|---|---|
| **roic** | +0.0420 | **+3.38** | 96.7% | 4th of 32 |
| **roe** | +0.0439 | **+2.84** | 93.4% | 6th of 32 |

Both were contributing nothing. `quality` is now the strongest theme in the model
(+0.0363, t **+3.39**). Alone, these lifted PBO 40% → 26.7% and DSR 71.7% → 80.8%.

Correctness check worth recording: **every other signal's IC t-stat matched the baseline to
two decimals**, confirming the change perturbed nothing it shouldn't have.

### 3b. `neg_beta` — no standalone signal, but it helped the composite

`neg_beta` measures median IC **+0.0019, t −0.05** (coverage 88.0%). Betting-against-beta
does **not** replicate here as a standalone factor. Yet adding it moved DSR 80.8% → 92.9%,
long-short t 0.951 → 1.065 and top-decile alpha +5.68% → +6.20%. A zero-IC input can
legitimately help by decorrelating, but a 12-point DSR move from a t = −0.05 signal is a
large effect from a weak cause — treat as encouraging, not established.

### 3c. `neg_asset_growth` — DROPPED (wrong sign, confirmed on the full universe)

Median IC **−0.0141, t −0.70.** The investment factor says *low* asset growth should predict
high returns; here high asset growth did. Averaging it in was cancelling `neg_issuance`
(+0.0232, **t +2.25**), the one input in the theme that works. `capital_discipline` is now
issuance alone and measures **+0.0232 / t +2.25** as a theme.

It stays computed and listed in `NUMBER_THEME` so it keeps being measured — re-adding it is
one column in `factors.py`.

Measured *sequentially* (i.e. while `low_risk` was still at 0.125) the drop looked **mixed**:
PBO 26.7% → 20.0% and DSR 92.9% → 94.95%, but long-short t fell 1.065 → 0.916 and the
concentrated book gave back ~2pp.

**Re-tested in the FINAL configuration (`low_risk` = 0) and the ambiguity disappears.** Both
runs below are the full universe and differ *only* in whether `neg_asset_growth` is in the
theme:

| metric | dropped (shipped) | restored |
|---|---|---|
| PBO | 0.1333 | 0.1333 (tie) |
| Deflated Sharpe | 1.0000 | 0.9999 |
| **long-short t** | **3.485** | 3.298 |
| **top-decile alpha** | **+11.77%** | +11.52% |
| long-short ann | +17.58% | +17.39% |
| portfolio CAGR | +27.91% | +25.25% |
| monotonicity | −0.939 | **−0.976** |
| **`capital_discipline` theme IC** | **+0.0232 (t +2.25)** | +0.0062 (t +0.77) |

Dropping it wins on every criterion except monotonicity, and restoring it cuts the theme's own
IC by roughly 4×. **The earlier "mixed" verdict was an artifact of measuring the change while
`low_risk` was still scrambling the ranking** — a reminder that sequential attribution can
mislead when the factors interact. Confirmed keep.

### 3d. `low_risk` — set to ZERO weight. The single biggest change.

**Corrected finding first:** CLAUDE.md records `low_risk` as having pooled IC **−0.048**.
That does **not** replicate. On the full universe with *both* inputs finally populated the
theme measures **−0.0014 (t +0.71)** — indistinguishable from zero. It was **dead weight,
not actively harmful.** The −0.048 came from a smaller universe with `neg_beta` empty.

Zeroing its 12.5% weight produced by far the largest single improvement of the session:

| metric | with low_risk | low_risk = 0 |
|---|---|---|
| PBO | 20.0% | **13.3%** |
| Deflated Sharpe | 94.95% | **~100%** |
| Long-short ann | +6.63% | **+17.58%** |
| Long-short t | 0.916 | **3.485** |
| Monotonicity | −0.794 | **−0.939** |
| Top-decile alpha | +6.24% | **+11.77%** |

**Why a ~zero-IC theme mattered so much — verified, not assumed.** I measured the
average within-date Spearman correlation between all themes on the full panel.
**`low_risk` vs `size` = −0.352, the strongest anticorrelation in the entire matrix.**
Low-beta/low-vol names *are* large caps, and `size` is an explicit small-cap tilt
(`neg_log_mktcap`, t +1.68). At 12.5% each they were fighting each other, and `low_risk`
brought no signal of its own to the fight. Removing it let the working themes express: the
deciles went from badly scrambled to nearly monotone (D1 22.8% → 28.3%, D10 16.2% → 10.7%).

Two other correlations worth knowing: **`momentum` vs `institutional` = +0.50** (half
redundant — a candidate for consolidation), and `insider` vs `size` = +0.24.

**Applied live and reversible:** `WEIGHTS_ESTABLISHED`/`WEIGHTS_SPECULATIVE` now carry
`low_risk: 0.0`. Restore by setting it back to 0.125. The weights need not sum to 1 — the
backtest ranks on a weighted sum (scale-invariant) and the live scorer renormalizes per name.

---

## 4. `monotonicity` HAS BEEN READ BACKWARDS — correct the mental model

`quantile_backtest` orders buckets by `argsort(-comp)`, so **bucket 0 is the HIGHEST
composite**, and `monotonicity` is `Spearman(bucket index, bucket return)`. A working signal
therefore makes it **NEGATIVE**:

- **−1.0 = returns fall perfectly from D1 to D10 → perfectly ordered, the ideal**
- 0.0 = no ordering
- **+1.0 = returns RISE from D1 to D10 → the composite is exactly backwards**

Verified numerically against synthetic perfect and inverted decile series.

CLAUDE.md's *"monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
cleanly ordered"* is **inverted**: −0.68 means they *were* well ordered. So is the P4 table
logging −0.782 → −0.855 as *"slightly worse"* — that was an improvement. Every past
"monotonicity is bad" conclusion in this repo needs re-reading with the sign flipped.

Now documented in the `quantile_backtest` docstring, shipped as
`construction.monotonicity_want` in the JSON, labelled in the MD table, and pinned by
`test_monotonicity_sign_convention`.

---

## 4b. HELD-OUT CONFIRMATION — `low_risk` survives, `insider` does not

The one check CPCV and the Deflated Sharpe cannot provide: they correct for the trials inside
the *weight search*, not for a human looking at a theme's IC on the whole panel and then
dropping it. Now a permanent part of the backtest (`holdout_theme_validate()`, shipped as
`holdout_validation` in the results file), not a one-off script.

**Protocol, fixed before looking at any result.** Split the 110 dates in half by time
(early 1998-12-31..2012-07-10, late 2013-01-10..2026-04-22); **embargo the boundary date**
(2012-10-08), whose 63-day forward window is the only one that can straddle the split. Decide
on one half using a pre-specified rule — *flag a theme whose median IC on the decide half is
≤ 0* — then measure on the other half only. Run both directions.

| theme | verdict | ΔLS t (E→L) | Δtop-dec (E→L) | ΔLS t (L→E) | Δtop-dec (L→E) |
|---|---|---|---|---|---|
| **low_risk** | **confirmed** | **+1.59** | **+3.21%** | **+2.02** | **+7.86%** |
| capital_discipline | confirmed | +0.43 | +1.22% | +0.01 | +1.04% |
| quality | not_replicated | +0.39 | +1.21% | +0.17 | −1.06% |
| **insider** | **not_replicated** | +0.08 | +0.78% | −0.09 | −0.47% |
| value | rejected | +0.05 | −0.94% | +0.11 | −0.11% |
| momentum | rejected | −0.61 | −1.46% | +0.11 | −0.76% |
| size | rejected | −0.84 | −3.41% | −0.92 | −5.59% |
| institutional | rejected | −1.10 | −3.67% | 0.00 | 0.00% |

**`low_risk` = 0 is CONFIRMED.** On the pre-registered direction (decide early → measure late)
the rule fires on the early half (median IC −0.0308) *and* the effect holds on untouched data:
long-short t 0.97 → 2.56, top-decile alpha +6.09% → +9.30%. The reverse direction agrees more
strongly still. This is the largest effect in the table by a wide margin.

**`insider` = 0 is REJECTED — left at 0.125.** It helped one direction by a hair and hurt the
other. Its −0.34 full-sample t is not a stable property. This is precisely why it was tested
rather than dropped on the strength of one number.

### Two things this table reveals that are more important than the verdicts

1. **A theme's own IC does not replicate, but the benefit of removing `low_risk` does.**
   `low_risk` measures −0.0308 on the early half and **+0.0411** on the late half — it flips
   sign. So "low_risk has ~zero IC" is really "its IC is noise that averages to zero", and the
   §3d framing was too confident. The benefit survives anyway **because it never came from the
   theme's own predictive power** — it came from removing the −0.352 cancellation of `size`.
2. **That mechanism is now independently corroborated.** `size` also flips (t **+3.17** early,
   **−0.67** late: the small-cap premium worked pre-2012 and not after), and the gain from
   removing `low_risk` **tracks it** — +7.86pp in the early half where `size` is strong, only
   +3.21pp in the late half where it is dead. The effect is largest exactly where the
   mechanism predicts. That is a prediction the data could have falsified and did not.
   `size` is also the theme most damaged by zeroing (−0.84 / −0.92 t), confirming it is
   carrying real weight rather than being redundant.

**Do NOT act on the `capital_discipline` "confirmed" row.** It passes on a knife edge
(ΔLS t **+0.01** in one direction — noise), and the verdict rule only requires the sign to be
right in both directions, not the magnitude to be meaningful. That is a genuine weakness of
the rule, left un-retrofitted on purpose: changing the threshold after seeing results is the
exact sin this whole section exists to prevent. Read `confirmed` as "the sign held up twice",
not "this is worth doing". `capital_discipline` also has a healthy theme IC (+0.0232, t +2.25),
which makes the row look more like decile-metric noise than a real finding.

---

## 5. WHAT I DO NOT TRUST — read before acting on §0

1. **The held-out test confirms the DECISION, not the hypothesis generation.** Both halves come
   from the same 18-year panel, the same universe and the same data vendor, and the
   size-cancellation mechanism was hypothesised on the full sample before being checked on the
   splits. A truly clean test needs data this project has never touched. What §4b does rule out
   is the specific failure I was worried about — that zeroing `low_risk` was fitted to noise in
   the very periods it was then scored on. It was not.
2. **Deflated Sharpe "100%" is a saturated probability**, not a proof. Report it as
   ">99.9%" and do not treat the bar as permanently cleared.
3. **CPCV vs long-short disagree on magnitude.** Removing `low_risk` moved median OOS IC
   only +0.059 → +0.060 while long-short t moved 0.92 → 3.48. The gain is concentrated in
   the *tails* (deciles), where fewest names sit and noise is highest. The IC evidence for
   this change is far weaker than the decile evidence.
4. **The concentrated top-25 hold book (CAGR +27.9%, alpha vs EW +13.95%) is the noisiest
   number in the file.** CLAUDE.md records top-25 as previously *losing*. Do not quote it.
5. **Sequential attribution misled me once already** (§3c): `neg_asset_growth`'s drop looked
   mixed when measured with `low_risk` still weighted, and clearly correct once re-tested in
   the final configuration. Every "stage N vs stage N−1" comparison in this document carries
   that caveat — the factors interact, so only the final head-to-head is authoritative.
6. **Derived ROE/ROIC are quarterly rates, not annualized.** Harmless for ranking
   (everything is z-scored cross-sectionally) and consistent with how `earnings_yield` /
   `op_margin` already work here, but it lets **fiscal-quarter seasonality into the
   cross-section** — different names sit at different fiscal quarters on a given rebalance
   date. A TTM version is the obvious next refinement and I deliberately did not fold it in
   silently.
7. **`institutional` coverage is 61.4% on the full universe**, not the 81.7% recorded in
   CLAUDE.md (that figure came from a smaller universe). `insider` is 85.0%.

---

## 6. NEW finding not asked for: `insider` is the actually-negative theme

With the per-theme table finally available:

| theme | median IC | IC t | coverage |
|---|---|---|---|
| quality | +0.0363 | +3.39 | 98.0% |
| momentum | +0.0517 | +2.62 | 96.6% |
| capital_discipline | +0.0232 | +2.25 | 96.8% |
| institutional | +0.0297 | +1.81 | 61.4% |
| size | +0.0126 | +1.68 | 100% |
| growth | +0.0221 | +1.45 | 93.0% |
| value | +0.0123 | +1.34 | 100% |
| low_risk | −0.0014 | +0.71 | 99.7% |
| **insider** | **−0.0034** | **−0.34** | 85.0% |
| sentiment | n/a | n/a | 0.0% |

**`insider` is the only theme with a negative t-stat, and it still carries 12.5% weight.**
It has since been tested properly on the held-out split (§4b) and **zeroing it did NOT
replicate** — +0.08 long-short t one direction, −0.09 the other. **Left at 0.125.** Its
negative full-sample t is not a stable property, and this is the clearest illustration in the
session of why a single number is not a decision: by the same reasoning that justified zeroing
`low_risk`, `insider` looked like the obvious next cut, and it did not survive the test.

`growth_accel`, now measurable for the first time: +0.0062, **t +0.50** — no real signal.

---

## 7. What's blocked / not done

1. **CLAUDE.md's separate "P5 — robustness" item is NOT done.** Winsorization already
   existed (`zscore` clips at 2%); **median/MAD robust z-scores and industry-relative
   ranking remain untouched.**
2. **Out-of-sample confirmation of the `low_risk` removal** — the single most important
   outstanding item (§5.1).
3. `sentiment` still has no point-in-time source (grades parked; `grades.csv` is 58 bytes).
4. `bulk.EARNINGS_CODES` still unpopulated, so `earnings_dates()` returns `[]` and PEAD is
   still blocked.
5. Social preview (og:image) untouched.
6. `inst_breadth` remains in `NUMBER_THEME` (so it is measured, t +1.08) but no longer feeds
   the institutional theme — `sm_breadth` replaced it in P4. Harmless drift, but the
   "single source of truth" comment in `settings.py` overstates what `NUMBER_THEME` controls:
   `factors.py` hardcodes the theme means.

---

## 8. Recommended next step, in order

1. ~~Confirm the `low_risk` removal out-of-sample~~ **DONE — confirmed (§4b).**
2. ~~Test zeroing `insider`~~ **DONE — rejected, left at 0.125 (§4b).**
3. ~~TTM ROE/ROIC~~ **DONE — REJECTED (P6.2); quarterly is better.**
4. ~~median/MAD robust z-scores~~ **DONE — REJECTED (P6.3); costs half the long-short t.**
5. ~~Consolidate momentum/institutional~~ **DONE — REJECTED (P6.4); both earn full weight.**
6. ~~Pre-specify the holdout magnitude threshold~~ **DONE (P6.0, commit `4de6e71`).**
7. ~~Are the returns achievable net of costs?~~ **DONE — YES, breakeven 236bps vs ~37bps
   actual (P6.1).**

**Now, in order:**

1. **Get data this project has never touched.** This is now clearly the top item. The edge
   clears every internal bar and survives costs; what it has never faced is data outside this
   one 18-year Sharadar panel. A forward paper-track starting today is the cleanest and
   costs nothing but time — **and it is the natural Cowork task** (tracked "Valquo Index vs
   SPY"). → *Take the paper-track to the Cowork chat.*
2. **Unblock industry-relative ranking** (P6.3b) — one Sharadar TICKERS download. It is the
   only P6 item that could not be tested at all, and `sector_neutral` has been silently inert
   in every backtest to date, so this is also a latent-bug fix.
3. **Live-behaviour watch after the P5 deploy.** `low_risk` went 12.5% → 0, so the hot list
   will tilt smaller-cap than before. That is intended, but the first post-deploy scans should
   be eyeballed. Revert is one line in `settings.py`.
4. **PEAD from EVENTS** — still blocked on `bulk.EARNINGS_CODES` (needs Sharadar's EVENTS
   legend). This is now the most promising *new* signal, since the cheap refinements are all
   exhausted.
5. **ML tree combiner**, now clearly worthwhile — there are several genuinely real signals to
   combine, and P6 shows the linear composite is sensitive to how inputs are scaled.
6. **Re-read every past "monotonicity" conclusion with the sign flipped** (§4).
7. Social preview (og:image) — still untouched, independent of everything else.

---

## 9. Standing notes

- `data/` is gitignored, as are `*.zip` / `*.csv.gz` / `*.parquet`. Nothing licensed was
  committed; `BACKTEST_RESULTS.*` carries derived metrics only (IC, t-stats, returns,
  weights) — no raw rows, prices or per-name fundamentals.
- Bulk layout: raw zips in `data/raw/`, extracted CSVs in `data/bulk/`, caches in
  `data/bulk/prepared/`.
- `DERIVE` in `fundamental_panel.py` toggles each derived input, so a validation change can
  be attributed to one signal instead of a bundle. All four ship **on**, and
  `test_all_derived_inputs_ship_enabled` fails the suite if one is left off.
- Results-file schema is now **version 2** (adds `signal_coverage` and `per_theme`; purely
  additive).
- The most recent SF3 quarter is always incomplete (filings arrive over following weeks) —
  the 45-day `inst_lag_days` convention handles it.
- The live hot-list scan runs at 22:23 UTC and uses the FMP key.
