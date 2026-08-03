# HANDOFF — live app (app-fixer lane)

Own lane: live scan / universe / display. Does not touch `valuation/edge/` options work, the
ThetaData miner, or `fairvalue.py`.

---

# Session 4 — 2026-08-02 — Broker fundamentals, the free route (PROMPT_broker_fundamentals.md)

## The verdict up front: NO, you do not need to pay for FMP

Tradier — which you already pay for — carries Morningstar fundamentals at
`beta/markets/fundamentals`, **100 symbols per call**. The whole 800-name universe now costs
about **24 calls** against a feed with no daily quota, versus FMP's ~2,400 metered per-name
calls. It covers market cap, enterprise value, the full valuation-ratio set, ROE, beta,
sector, and shares outstanding at **~99% of liquid names**.

What it does **not** carry is an income statement or a balance sheet. That is the honest
limit, and it is stated precisely in the gap table below.

**Recommendation: do not buy FMP Premium.** The one thing paid FMP would add that nothing free
covers is the growth theme, and there is a caveat on that below that matters more than the
price. If you ever do pay, the reason should be revenue growth, not "better data" generally.

## What is actually in the broker feed (measured, not assumed)

Measured on **200 liquid names, 2026-08-02**. Tradier returns a large envelope in which most
tables are null; I counted per-field fill rates rather than trusting the shape:

| Field | Broker source | Coverage |
|---|---|---|
| market cap, enterprise value, shares outstanding | `share_class_profile` | 99% |
| book value/share, P/S | `valuation_ratios` | 99% / 98.5% |
| P/B, P/E, EV/EBITDA | `valuation_ratios` | 91.5% / 88% / 83.5% |
| ROE, ROA, debt/equity | `operation_ratios` | 89.5% / 95.5% / 87.5% |
| beta (36/48/60-month) | `alpha_beta` | 99% |
| sector | `historical_asset_classification` | 99% |
| EPS (3M/9M/12M) | `earning_reports` | 98.5% |
| 13F + insider ownership tallies | `ownership_summary` | 99% |

**Null for every symbol, at every tier we can reach:** `financial_statements_restate`,
`segmentation`, `earning_reports_restate`, `historical_returns`, `operation_ratios_restate`,
`earning_ratios_restate`, `trailing_returns`, `asset_classification`.

Several absolutes are **derived** rather than reported — `revenue = mktcap / P/S`,
`net income = mktcap / P/E`, `equity = BVPS x shares`, `EBITDA = EV / EV-EBITDA`,
`net debt = EV - mktcap`. These are arithmetic identities, not estimates, but they inherit the
ratio's month-end as-of date while market cap is same-day, so a fast-moving name's derived
revenue can be a few percent off the filed figure. A **reported** value from the free stack
always beats a derived one (`broker_fundamentals.merge`).

### The fields with NO free source anywhere — the real "would need paid data" list

`operating_income`, `gross_profit`, `fcf`, `interest_expense`, `op_margin`, `gross_margin`,
`fcf_yield`, `ebit_ev`, `roic`, `revenue_growth`.

These come only from the slow per-name free stack (yfinance/EDGAR). They feed **growth** and
about half of **quality**. Locally the free stack supplies them fine; from a cloud IP it is
rate-limited, and that is the real exposure.

## Coverage: before vs after (100 liquid names, same universe, cold cache)

| | Before | After (broker + free) | Broker ONLY |
|---|---|---|---|
| Names scored | 99/100 | 99/100 | **97/100** |
| Wall clock | 244s | 230s / 189s (2 runs) | **15s / 16s** |
| growth theme coverage | **0.76** | **1.00** | 0.00 |
| quality / value / momentum / size | 1.00 | 1.00 | 0.94 / 1.00 / 1.00 / 1.00 |
| low_risk (beta) | 1.00 | 1.00 | 0.92 |

Be careful with the middle column's timing: the shipped path still makes the same slow
per-name free call, so **it is not meaningfully faster** — 244s vs 230s/189s is network noise
across three runs, not an improvement. The speed result is the third column.

The "Broker ONLY" column is the one that matters: I forced the free stack to fail outright,
simulating a throttled cloud IP. **97 of 100 names still scored, in 15 seconds instead of 230**
— with value, quality, momentum, size and low-risk intact and **growth gone**.

That is the resilience win, and it is the concrete answer to "what happens when Yahoo throttles
us". Before this change a failed per-name fetch returned nothing and the name was **dropped
from the scan entirely** ("no data"). Now the name survives on the broker's half. A throttled
Yahoo costs the scan some quality per name instead of costing it the name.

## Two bugs found and fixed on the way

**1. Enterprise value is `0` for banks — a "not applicable" sentinel, not a number.** Of 200
liquid names, 11 carry `ev == 0` and **all eleven are Financial Services** (JPM, BAC, WFC, GS,
MS, C, SCHW, AXP, COF, NU, SOFI); no other sector has one and none is negative. Taken
literally it sets `net_debt = -market_cap` (JPM: **-$935B**) and `ev_sales = 0` — i.e. it would
hand every large bank the cheapest possible EV/Sales in the universe and **peg the entire
sector to the top of the value theme**. Now treated as missing, so banks are ranked on earnings
yield / book / sales, which is how a bank should be valued anyway. Pinned by a test.

**2. The `insider` theme is inert in the live scan, and coverage was reporting it as 100%.**
No `insider_score` ever reaches `build_frame` in the live path (only the backtest panel and a
post-scan decoration set it), so the column is the constant `0.0`. A constant has zero
variance, `zscore()` returns all-NaN, and `composite_score` renormalizes its **12.5% weight
away**. But `theme_coverage` measures *presence*, so it read `insider: 1.0` — a dead theme
reported as perfectly healthy. This is the same class of bug as the five silently-empty factors
in CLAUDE.md.

I did **not** change the scoring. I added `theme_contributing` to the health block, which
measures each theme *after* standardization, and pointed the UI warning at it. Present and
usable are now separate numbers.

Measured live, only **4 of 9 themes actually drive the score**: value, quality, momentum, size.
`low_risk` is deliberately weighted 0; `insider`, `capital_discipline`, `sentiment` and
`institutional` are all inert. Worth knowing before reading any live ranking.

## What I did NOT wire, on purpose

The broker carries **13F and insider ownership at 99% coverage** — holder counts, shares
bought/sold, insider buys/sells. That is exactly the input the `institutional` theme
(12.5% weight, currently empty live) and the `insider` theme want, and it is tempting.

I left it unwired because **populating an empty theme changes every ranking**: `composite_score`
renormalizes over whichever themes are present, so a name that was scored on 4 themes would
suddenly be scored on 5 or 6. CLAUDE.md's rule is that a theme change has to clear
`holdout_theme_validate()` first, and I cannot run that here — this is a live-only snapshot
feed with no history, and Morningstar's aggregate 13F summary is a different construction from
the point-in-time Sharadar SF3 data the backtest validated. Wiring it would be an unvalidated
scoring change dressed as a data fix.

**This is the highest-value follow-up and it is Don's call, not mine.** Fields are
`ownership_summary.{13_f_holder_number, 13_f_shares_bought, 13_f_shares_sold, 13_f_shares_held,
insider_shares_bought, insider_shares_sold, number_of_insider_buys, number_of_insider_sellers}`.

## Changed

- **NEW `valuation/screener/broker_fundamentals.py`** — batched fetch, the field map, the
  sector-code map, `merge()` (reported beats derived) and `coverage()`.
- `providers.py` — `FreeProvider.prefetch()` bulk-loads the universe; `get_metrics` merges
  broker + free and no longer drops a name when the free fetch fails. `FMPProvider` delegates
  prefetch to the free stack behind it (on the current FMP tier the fallback IS the hot path).
  Added `METRICS_SCHEMA`, so cache rows written before the merge are discarded rather than
  served — a stale row missing `sector` is indistinguishable from a name that has none.
- `screen.py` — calls `prefetch()` when the provider supports it (optional by contract);
  ships a `fundamentals` health block (per-field fill rates, per-source counts) and
  `theme_contributing`; carries `extra.source` per name.
- `app.js` — per-name `p` marker for broker-only rows, a fundamentals-source line, and the
  theme warning now reads `theme_contributing`.
- `tests/test_screener.py` — 32 -> 43 tests.

Morningstar's 11 sector codes map **exactly** onto the sector names `engine/comps` already
uses, so a broker sector lands straight in the fair-value peer medians instead of falling
through to the generic default. A test pins that — a near-miss like "Financials" would fail
silently.

## Caveats — do not drop these

- Coverage is measured on **200 liquid large caps**. Thinner names will have worse ratio
  coverage; the 83.5% EV/EBITDA figure is the weakest link and will be lower down-cap.
- The derived absolutes carry the ratio's month-end as-of date, not today's filing.
- I could not test the throttled-cloud-IP case for real — I simulated it by forcing the free
  fetch to raise. The 97/100 survival number is from that simulation, not from production.
- The broker feed is a **snapshot**, not point-in-time. It is fine for live ranking and must
  never be fed to the backtest panel.

---

# Session 3 — 2026-08-02 — Index tab, dynamic alpha, trust enablers (PROMPT_appfixes_index.md)

## Shipped — all five items, including the "if time" one

**1. The Valquo Index has its own tab.** Moved out of the bottom of Hot Stocks (Hot Stocks now
links across to it). The tab carries: a cumulative Index-vs-SPY chart, the backtested-vs-live
performance pair, the sector-diversification view, and the full holdings table with Company /
Sector / Weight / Market cap / Hot score populated. Verified by actually running the app and
driving it in a browser — screenshots of both the long-track and the real 1-day state.

**2. Dynamic net alpha — backtested and live, side by side, never blended.** Two cards. The
server decides which one may be the headline; the UI never picks based on which number looks
better. Rules encoded in `valuation/screener/index_track.py`:
- Live cannot be the headline until **60 trading days** (`MIN_LIVE_DAYS`). Before that the
  card is badged `thin — Nd` and the backtest keeps the border.
- **Annualised alpha and Sharpe are withheld** (served as `null`, rendered "—" with the
  reason) until there is enough history. Compounding 1 day of drift into a yearly rate
  manufactures a number nobody should believe. Cumulative-since-inception *is* shown from
  day one, because that one is honest at any length.
- Sharpe is also suppressed above **6.0**. A near-constant excess series drives the
  denominator to zero; I hit exactly this in testing and got "Sharpe 444", which on a live
  page would discredit every other number on it.
- Right now the real state is **1 day (2026-07-31): Index +0.41% vs SPY +0.69%, −0.28pp**.
  Thin, shown, not the headline. That is the correct display, not a bug.

**3. Trust enablers.**
- **Staleness stamp** (`valuation/screener/freshness.py`) on the Index, Hot Stocks and
  Signals. Age is in **trading days**, so a Friday scan read on Sunday is correctly "fresh" —
  crying wolf across a weekend is how staleness badges get ignored. 2 days warns, 3+ shows a
  red "the scheduled update has not run. Do not treat it as current."
- **Risk disclaimer** as one shared string (`RISK_DISCLAIMER` in `web/app.py`) served with
  the Index and Signals payloads, so the wording cannot drift between surfaces.
- **`/methodology`** — point-in-time, survivorship, the 236bps-breakeven cost framing, CPCV /
  PBO / Deflated Sharpe, held-out confirmation, full-universe-only. Plus a "where it is weak"
  section that keeps the uncomfortable parts: one 18-year dataset the model was tuned on, a
  saturated Deflated Sharpe, dormant themes, and the degraded data feed. A test asserts those
  weaknesses stay on the page, so it cannot quietly become marketing. Linked from both
  footers and from the Index and Signals tabs.

**4. Scan-failure alerting.** Two layers:
- `scripts/ci_scan.py` posts to Discord if the scan crashes or exits non-zero.
- `scripts/check_staleness.py` — a **separate** `watchdog` job on its own cron (13:15 UTC
  weekdays, before the open). It runs separately on purpose: a check bolted onto the end of
  the scan cannot fire when the scan is the thing that died, which is exactly the July
  failure. It hits the public API from outside, and alerts on a stale scan **or a collapsed
  universe**. Exits non-zero so the Actions run goes red too.
  Run against the live site right now it already fires: *"the last scan only scored **154**
  names — the universe has collapsed"*.

**5. Mobile pass** (the "if time" item). Index tab verified at 390px: no horizontal page
overflow, stat rows and sector labels scaled down, wide tables scroll inside their own box
rather than the page.

## What Don needs to do

1. **Add `DISCORD_WEBHOOK_URL` as a GitHub Actions secret.** Everything in item 4 is wired and
   inert without it — the alerts fall back to "red run in the Actions tab", which is precisely
   what nobody noticed for four days in July.
2. **Point the Cowork tracker at the new ingest endpoint.** `data/` is gitignored, so the
   tracker's files never reach Render and the live column would be permanently empty in
   production while working fine on your laptop. `POST /admin/ingest-index-track` with
   `X-Admin-Token`, body `{"inception_date", "benchmark", "series": [{"date","valquo","spy"}]}`
   — percentages cumulative-since-inception, exactly as `valquo_track_history.csv` holds them.
   → **This is a Cowork-side task.**
3. The 60-trading-day promotion threshold is a judgement call, not a measured one. It is one
   constant (`index_track.MIN_LIVE_DAYS`) if you want it longer.

## Nothing slipped

All five items shipped. The prompt allowed item 5 to be dropped; it wasn't needed.

## Tests

Six suites green: **edge 119/119, screener 32/32 (+5), saas 22/22 (+2), intraday 18/18,
engine 28/28, bulk 14/14.**

New tests worth knowing: `test_live_track_never_annualizes_a_stub_or_leads_with_it` (5 days
must never lead and must never be annualised; 65 days must),
`test_live_track_suppresses_an_implausible_sharpe`,
`test_freshness_counts_trading_days_not_calendar_days` (pins the weekend behaviour and the
real 07-29 case), `test_methodology_page_is_public_and_states_the_weaknesses`,
`test_index_track_ingest_requires_the_admin_token`.

---

# Session 2 — 2026-08-02 — the live universe (PROMPT_appfixes_universe.md)

## Headline

**Universe: 191 names / 154 scored → 800 names / 794 scored**, sourced from a 7,113-name
broker-enumerated pool ranked by liquidity. The Index goes from a decile of 77 eligible names
to a decile of **668**. Verified end to end locally.

The `company-screener` failure is diagnosed and worked around, but the diagnosis is worse than
the prompt assumed and you have a decision to make. Read "The FMP problem" before anything
else. Also note the security item (6) — an API key was one commit away from being public.

## Step 1 — verification: the FMP key did NOT fix it

The live site is still serving the **2026-07-29** scan: 191 universe / 154 scored. There has
been **no successful scan since 07-29** — four days. So the re-run either did not fire or did
not land, and I could not verify from the site. I diagnosed against the live key directly.

## The FMP problem — it is not the screener endpoint, it is the whole subscription

Verified 2026-08-02 against the real key. Two separate restrictions:

**1. Every bulk/list endpoint is 402 Restricted.** Not a parameter problem — I tried the call
with and without `exchange`, `country`, `isActivelyTrading`, and at `limit=10`. All 402.

| endpoint | result |
|---|---|
| `company-screener` | 402 Restricted |
| `stock-list` | 402 Restricted |
| `sp500-constituent` / `nasdaq-constituent` / `dowjones-constituent` | 402 Restricted |
| `available-exchanges`, `batch-quote-short` | 402 Restricted |
| `profile`, `quote`, `key-metrics-ttm`, `ratios-ttm` | 200 OK |

**2. Worse — the per-symbol endpoints serve only an ALLOWLIST.** I sampled 30 names spread
across the liquidity ranking and asked for `key-metrics-ttm`: **29 of 30 came back 402**, with
a symbol-level message — *"Premium Query Parameter: 'Special Endpoint : This value set for
'symbol' is not available under your current subscription"*. Blocked names include FCX, NSC,
ELV, PRU, CLX, WDAY, TDG, HAS. AAPL/NVDA/AMD/GE/AMZN/CSCO still work.

**This is a change, not a long-standing state.** FCX, ELV and MU are all present in the live
07-29 snapshot — FMP served them four days ago and refuses them today. That points at the
subscription lapsing or being downgraded around 2026-07-29, which is also exactly when the
daily scans stopped appearing. **Worth checking your FMP account first — this may be a billing
problem rather than a code problem.**

So: no code change can restore FMP-sourced fundamentals for the large-cap tier. That is the
honest answer the prompt asked for.

## What I built anyway, so the product is not dead in the meantime

**1. Universe from the broker (Tradier) — the name-list fix the prompt asked for.**
New `valuation/screener/broker_universe.py`. Tradier has no bulk restriction and you already
pay for it:
- `markets/lookup`, 26 calls (one per letter) → **7,113 distinct NYSE/Nasdaq common stocks**
  with company names, in ~9s.
- `markets/quotes`, batched 200 at a time → last price, average volume, 52-week high.
- Ranked by **average dollar volume** and cut to a limit. The broker does not publish market
  cap; liquidity is what actually decides tradeability and is a tight proxy for size. Market
  cap still comes from the fundamentals feed per name, so the large-cap gate is unchanged.
- Whole universe costs ~50 free calls and ~4s. ETFs excluded; sub-$1 and illiquid names
  dropped; class shares normalised (`BRK/B` → `BRK-B`, which otherwise fail every downstream
  lookup — that quietly dropped some of the largest companies in the market).

**2. Fixed the actual code bug that capped the universe at 191.** `FMPProvider`'s fallback
hardcoded `"bundled"` regardless of the scope requested. So a `whole_market` scan silently
became a 191-name scan the moment the screener 402'd. It now falls back **for the scope that
was asked for**, through broker → EDGAR → bundled.

**3. Per-symbol fallback to the free stack.** When FMP refuses a symbol, that name is served
by the existing yfinance/EDGAR path instead of being dropped. A circuit breaker stops asking
FMP after 12 consecutive failures, so a refusing subscription costs 36 wasted requests per
scan rather than 2,400. The per-source split ships in the health block — a book built from two
fundamentals feeds should never be a silent fact.

**4. FMP spend ceiling.** `FMP_MAX_CALLS` bounds requests per scan. It caps what we *spend*,
not what we *rank*: names past the budget go to the free path.

**5. Persistent scan cache in CI.** `ci_scan.py` now writes to `.scan-cache/screener.db` and
the workflow restores it with `actions/cache`. Without this every CI run started from a cold
cache and re-paid for every name. With it, a run only pays for entries past the 30-day TTL.

**6. SECURITY — an API key was about to be published.** `requests` puts the full request URL,
query string included, in its `HTTPError` text. My first version of the universe note stored
that verbatim, and the health block is served publicly by `/api/hotstocks` — so the live FMP
key would have been on the open internet. Everything reaching that block now goes through
`_redact()`. Pinned by `test_api_keys_never_reach_the_health_block`. **If you want to be
careful, rotate the FMP key** — it was never actually deployed, but it was one commit away.

## Measured results

Local end-to-end runs (temp DB, live site untouched):

Local end-to-end runs (temp DB, live site untouched):

| run | universe | scored | notes |
|---|---|---|---|
| **before** (live, 07-29) | **191** | **154** | bundled fallback |
| 250-name broker universe | 250 | 247 | 6 via FMP, 244 via free fallback |
| **after** — 800-name broker universe | **800** | **794** | the configured production size, 22 min |

The 800-name run in full: 99.3% scored; display coverage name 99.9% / sector 99.9% /
market cap 100%; only 6 names dropped (3 no market cap, 2 nano-cap, 1 illiquid). Theme
coverage value/quality/momentum/low_risk/size 1.00, growth 0.98. Index:

> `tilt: large-cap only` · **668 eligible** · **67 positions** · **10 sectors**
> (Financials 30.8%, Healthcare 23.1%, Technology 19.4%, Energy 10.9%, …)

Compare the old book: 77 eligible, 25 positions, 5 sectors. **This is a genuinely different
book** — a decile of 668 large caps rather than a decile of 154 mostly-mega-caps, so the
holdings will look unfamiliar (NLY, ARWR, APGE, QXO, SYF at $10–25B rather than DELL/BA/AMD).
That is the intended consequence of ranking the actual tier, but eyeball the first live one.

Throughput ~1.6s/name on a cold cache. The workflow's `timeout-minutes` went 30 → 60 and
`SCAN_LIMIT` 1500 → **800** to fit that honestly. With `actions/cache` warm it will be far
quicker, and 800 can be raised.

Note the 800-name run served **0 names via FMP** — by then my diagnostics had tripped FMP's
**429 rate limit**, the circuit breaker fired, and the free stack carried all 800. That is the
degraded mode working exactly as designed, and it is also a preview of what every scan looks
like until the subscription is sorted.

## The decision you need to make

**Option A — fix the FMP subscription (~$22/mo Starter).** Restores `company-screener` (one
call for the whole market with sector and market cap) and, more importantly, per-symbol access
to the whole universe. Cleanest, and the code already prefers FMP whenever it answers.

**Option B — stay on the free stack.** It works: the 250-name run scored 98.8% of names with
essentially no FMP. But it is yfinance, so it is slower (~25 min for 800), rate-limited from
cloud IPs, and occasionally returns nothing for a name.

My recommendation: **check whether the FMP plan lapsed first** — if this is an expired card
rather than a deliberate downgrade, that is the whole fix. The code works either way.

## Not done (step 3)

The Index-in-its-own-tab with a cumulative-vs-S&P chart, and dynamic net alpha, were step 3
"only if there's time". Step 2 took the session. Left for next time.

## Tests

All six suites green: **edge 91/91, screener 24/24 (+5), saas 20/20, intraday 18/18,
engine 19/19, bulk 14/14.**

New: `test_api_keys_never_reach_the_health_block`,
`test_fmp_universe_falls_back_for_the_scope_that_was_asked_for`,
`test_fmp_budget_and_circuit_breaker_fall_back_instead_of_dropping_names`,
`test_broker_universe_normalizes_class_share_symbols`,
`test_broker_universe_ranks_by_liquidity_and_drops_junk`.

## One cost I incurred

Diagnosing this spent roughly 400–500 FMP requests off your daily allowance (endpoint probes,
a 30-symbol allowlist sample, and end-to-end scans) — enough that FMP was returning **429 Too
Many Requests** by the end. If tonight's scan looks quota-thin, that is why; it resets daily,
and the circuit breaker means the scan still completes off the free stack either way.

To be precise about the allowlist evidence, since the 429s came later and could muddy it: at a
single moment, with the same key and no rate limiting in play, `AAPL` returned **200** while
`FCX` and `NSC` returned **402** with a *symbol-scoped* message. A rate limit does not
discriminate by symbol. The allowlist is real and separate from the quota.

---

# Session 1 — 2026-08-02 — display fixes (PROMPT_app_fixes.md)

Landed on `main` as b459d9a. Summary retained for continuity:

- **$0.00 market caps were a unit bug.** `CompanyData` carries millions, FMP's profile carries
  dollars, both fed the same scan; the UI renders `market_cap/1e9`. The screener's metrics
  contract is now USD dollars everywhere, stamped with `units` so a millions-era cache entry is
  discarded. Ratios computed before scaling, so `earnings_yield`/`pe`/`ps`/margins are unchanged.
  Fell out of it: `prefilter`'s nano-cap floor was comparing dollars against `50`, and the Index
  had silently degraded to "largest half" because nothing cleared the $10B floor.
- **Company names** were present in the data but absent from the UI — the Index table had no
  Company column. Added there and in the portfolio table.
- **Sectors + a diversification view**: new `screener/profiles.py` resolves name/sector from the
  live feed (store → SEC filer list → bundled map → FMP profile, capped); `valquo_index.export()`
  decorates the finished book; new sector-weight breakdown above the Index table with sector
  count, largest sector and effective sectors.
- **Formatting**: one `mcap()` ($B/$T/$M, 2dp) everywhere; removed two local `pct`/`num` shadows;
  added `spct()` and `esc()`.
- Scan health gained `display_coverage` and a recorded reason for universe fallbacks.
