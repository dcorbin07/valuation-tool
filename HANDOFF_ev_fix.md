# HANDOFF — Enterprise value is now priced at the rebalance date

Session: 2026-08-03, Claude Code (growth valuation lane). Task: `PROMPT_growth_evfix.md`.
All numbers below are the **full 2,710-name x 110-date universe** (136,478 rows, ~18y),
measured on two complete backtest runs that differ in nothing but the EV treatment.

**VERDICT: SHIPPED, default ON.** It is a *correctness* fix, not a performance one. The book
is roughly a wash; the reason to ship is that there was no defensible version of the panel in
which half the value ratios were priced at the rebalance date and half at a ~111-day-old quote.

---

## 1. What was stale

Sharadar's `ev` is exactly `marketcap + debt - cashneq`, and the `marketcap` inside it is the
one from the **filing date**. Years ago the panel replaced its buggy shares x price market cap
with a point-in-time figure from DAILY — but `ev` was left behind. The result was a panel that
priced cheapness two different ways at once:

| ratio | priced at |
|---|---|
| `earnings_yield`, `fcf_yield`, `book_to_price` | the **rebalance date** |
| `ebit_ev`, `ev_sales`, `ev_ebitda` | a quote ~**111 days** old |

It was **stale, not look-ahead** — the embedded price is always older than the rebalance,
never newer — so the bias was conservative and no past result is invalidated upward.

**Measured scale of the defect, now shipped on every run:** re-pricing EV to the rebalance date
moves it by a **median 5.1%**, mean 9.9%, p90 19.6%. **26.7% of rows move more than 10%** and
6.4% move more than 25%. That is not a rounding detail on a value ratio.

---

## 2. The fix

`_pit_ev()` re-prices the **equity leg** of EV to the point-in-time market cap and holds the
**debt leg** at its last reported value. Net debt is only observable when a company files, so
holding it *is* the point-in-time answer rather than an approximation of one; the equity leg is
the only part that goes stale between filings, and it is the part this refreshes.

Two routes, because one route leaves rows behind and a row left behind silently keeps the old
stale value — this project's most-repeated bug class:

| route | formula | coverage | note |
|---|---|---|---|
| A (primary) | `mc + (debt - cashneq)/fx` | 99.95% of ARQ rows | needs the currency conversion |
| B (fallback) | `mc + (ev - marketcap)` | 98.29%, and 82 rows A cannot do | both terms already USD, no fx |
| — | filing's stale `ev` | last resort | counted and surfaced, never silent |

**Currency:** `debt`/`cashneq` are REPORTING-currency line items and `mc` is USD, so net debt
must be converted *before* it is added. Adding raw won to a USD market cap is the P7 currency
bug wearing a different hat. Pinned by a test that gives a foreign filer and its USD twin
identical multiples.

**One correction to the prompt.** It specified market cap from "the PIT price x shares".
CLAUDE.md records shares x price as the *buggy* path that the DAILY point-in-time figure
replaced, so I used DAILY's. Note this makes the cap a month-end value on or before the
rebalance, not a same-day one — fresher than 111 days by a wide margin, and still strictly
backward-looking.

### Why the two routes agreeing matters

Where both are available they agree to a **p99 of 0.001% of market cap** across 193,811 rows.
Two things fall out of that, neither of them trivia:

- Both routes are in **raw dollars**. Route A is dollars by construction, so the agreement
  proves SF1's `ev`/`marketcap` are dollars too, not millions. Mixing scales inside one
  cross-section would corrupt it silently.
- On the **8,071 foreign-reporter rows**, route A converts and route B does not — and they
  still agree. A wrong `fxusd` would blow them apart on exactly those rows. This is an
  independent re-validation of the P7 currency handling.

---

## 3. The new guard: `ev_freshness`

Coverage says a factor is PRESENT. Sanity says its values are BELIEVABLE. Neither can see a
rebuild that has quietly reverted to the filing value — same columns, same coverage, no error.
So `ev_freshness()` ships its own block reporting what fraction of rows carry a rebalance-date
EV, by which route, and how far re-pricing moved them.

**On the shipped run: 100.0% fresh** — 136,436 rows via route A, 42 via route B, **zero stale**.

It also warns loudly when `ev_point_in_time` is off, which the stale arm duly did:

```
[ev_freshness] WARNING: ev_point_in_time is OFF for 136,478 rows — EV ratios are
priced at the filing date, not the rebalance date
```

**A gap I found and closed while wiring it.** `run_backtests` putting a block in its own dict
is *not* enough to ship it: `results_file.build_payload` assembles a curated payload and
silently drops anything it does not name. The block was reaching the `--json` dump but would
never have reached `BACKTEST_RESULTS.json`, the file Don and Cowork actually read. It is now in
both, plus a line in `BACKTEST_RESULTS.md`, at **schema_version 4**. Two tests pin that —
exercising the real payload builder and the real renderer, not grepping for a source line.

---

## 4. Before / after on the full universe

The stale arm reproduces the committed baseline **exactly** (long-short t 3.3957 vs 3.3957,
top-decile alpha 0.11819 vs 0.11819, PBO 6.67%), so the two arms differ in the EV treatment
and nothing else.

| metric | stale EV | rebalance-date EV | |
|---|---|---|---|
| long-short t | 3.3957 | **3.5202** | better |
| long-short /yr | +17.16% | **+17.58%** | better |
| long-short hit rate | 64.55% | **65.45%** | better |
| top-decile alpha | +11.82% | **+11.88%** | better |
| monotonicity | −0.9515 | −0.9515 | unchanged |
| PBO | 6.67% | 6.67% | unchanged |
| Deflated Sharpe | 0.9999984 | 0.9999986 | unchanged |
| top-decile net alpha after costs | **+11.44%** | +11.40% | slightly worse |
| top-decile net Sharpe | **1.1126** | 1.1098 | slightly worse |
| top-25 net alpha | +14.99% | **+15.12%** | better |

**Read it as a wash.** The gross book improves slightly, the net top-decile figure degrades
slightly, and the two gates that actually decide things (PBO, Deflated Sharpe) do not move.

### The EV signals themselves — the direct evidence the staleness was real

Measured against **returns**, which is what makes this evidence rather than bookkeeping:

| signal | stale medIC | PIT medIC | stale IC t | PIT IC t |
|---|---|---|---|---|
| `neg_ev_sales` | +0.0214 | **+0.0363** (+70%) | 2.113 | 2.050 |
| `neg_ev_ebitda` | +0.0236 | **+0.0289** | 1.906 | **1.985** |
| `ebit_ev` | +0.0219 | +0.0194 | 2.295 | **2.358** |

**Honest wrinkle, not cherry-picked:** median IC and IC t-stat disagree in direction for two of
the three. `neg_ev_sales` gains 70% of median IC while its t-stat slips slightly; `ebit_ev` does
the reverse. The IC distribution across dates got both stronger and more dispersed. The fair
summary is "the EV signals get better, not uniformly on every statistic".

### Surgical, verified row by row

Exactly **9 columns changed** on identical `(date, ticker)` keys: the 3 raw EV ratios, their 3
z-scores, the downstream `value`, and the 2 new diagnostics. Every other theme and signal is
**bit-identical** — quality, momentum, size, growth, capital_discipline, institutional,
low_risk, insider, `earnings_yield`, `fcf_yield`, `book_to_price`, `neg_ps` all show a delta of
exactly 0.0000.

### Subperiod stability

| half | Δ long-short t | Δ top-decile alpha |
|---|---|---|
| early (2008–2012) | +0.147 | +0.18% |
| late (2012–2026) | −0.015 | −0.09% |

Helps the early half slightly, neutral-to-marginally-negative on the late half — reproducing
last session's measurement to three decimals.

**This is a stability check, not a held-out gate.** The gate exists to stop a change chosen *by
looking at the data* from being adopted on noise. This change was not chosen by looking at
returns at all, so there is no decision-half to hold out from. What matters here is only that
it does not break either subperiod, and it does not.

---

## 5. Did any shipped number move? Yes — one.

I traced every consumer rather than assuming.

**NOT affected — the live web screener.** It builds `ebit_ev` / `ev_sales` in `providers.py`
and `broker_fundamentals.py` from the provider's own current EV. Those were never stale, so the
hot list and the site are untouched by this change.

**Affected — the Valquo Index paper track.** `valquo_index.py` → `score_universe_now` →
`_sf1_to_metrics` is the one live artifact scoring through this path. Built both ways on the
current universe (as of 2026-07-24, 1,809 eligible names):

| | stale | fixed |
|---|---|---|
| book size | 86 | 86 |
| overlap | 85 of 87 distinct names | |
| position change | **RF out, BP in** | |
| one-way weight turnover | **1.81%** | |
| largest single weight move | KGC +0.24pp | |

So: one swap out of 86 and under 2% weight turnover. Real, but small — worth telling Cowork
about so the paper track's next rebalance is not mistaken for drift.
**→ Take that note to the Cowork chat; the index lives in that lane.**

---

## 6. Independent cross-check — and what it does *not* prove

Sharadar's DAILY file carries its own point-in-time `evebitda`, which the panel reads for
market cap and otherwise discards. Comparing per-date cross-sectional rank agreement:

| arm | mean rank-corr vs Sharadar PIT |
|---|---|
| stale | 0.8248 |
| fixed | **0.8501** |

Better on **100% of dates**, mean +0.0253, t 4.52.

**Do not over-read it.** Both my rebuilt EV and Sharadar's `evebitda` draw on the *same* DAILY
market cap, so this confirms the rebuild is **assembled** correctly — right scale, right
currency, right net-debt convention — rather than independently proving fresher prices predict
returns better. Only 6 of 110 dates matched, because DAILY is month-end and rebalance dates
rarely land there. The evidence for the staleness being a real handicap is the IC table in
section 4, measured against returns.

---

## 7. Tests

**12 new** (34 in `test_ev_multiples.py`, up from 22). All 15 suites green: **464 tests**.

The one the prompt asked for, `test_ev_tracks_market_cap_across_rebalances_from_one_filing`:
one filing scored at three rebalance dates must produce an EV that moves **dollar-for-dollar**
with the point-in-time market cap, with implied net debt constant. It also asserts the old
behaviour produces a *constant* — so it fails if the rebuild silently stops running, which is
the actual regression risk.

Also pinned: every EV ratio re-prices together (`ebit_ev` is the deployed one); the route-B
recovery path; the two routes agreeing; the route tag on every row; no-market-cap not silently
producing a debt-only EV; and five `ev_freshness` behaviours including a stale run being
visible in the markdown.

**A test I changed, flagged because "the test failed so I changed the test" deserves scrutiny.**
`test_ev_ebitda_is_converted_to_usd_for_a_foreign_reporter` failed — but because the *fixture*
converted only the field under test to won and left net debt in dollars. That is not a foreign
filer; it is a chimera, and it broke the moment a check touched a second field. I added a
`_sf1_foreign()` helper that converts every line item, which makes the test strictly stronger.
Two hard-coded EV constants in `test_edge.py` also moved, because EV is now rebuilt; the
currency-invariance property they sit inside is unchanged and still passes.

---

## 8. Open, deliberately not fixed here

**Negative enterprise value is treated inconsistently.** When net cash exceeds market cap, EV
goes negative — 909 rows (0.67%) before, **950 (0.70%) after**. `neg_ev_sales` then reads as
maximally cheap while `ebit_ev` reads as expensive, from the same underlying fact. It is the
same sign trap the EV/EBITDA guard already closes, left open on the other two ratios.

`neg_ev_sales` is **live** in the speculative value branch, so this is a real if small
mis-ranking. I did not fix it here: it is pre-existing, unrelated to staleness, and bundling it
would have confounded this change's before/after — the project's own rule about changes riding
along with each other. It wants its own held-out A/B.

**A diagnostic that did not work, reported rather than dropped.** I tried to show the defect on
real AAPL data by checking how often `ev_sales` changes between rebalances. It does not
discriminate — 98.6% of rebalances in *both* arms. The reason: rebalances are ~63 trading days
and filings are quarterly, so a new filing lands at almost every rebalance and the stale EV
refreshes at nearly the same cadence, just anchored to the wrong price. The defect is the 5.1%
median price gap, not a frozen number. The unit test catches it because it isolates one filing
across several rebalances; the real-data version structurally cannot.

---

## 9. Caveats

- The fix is a **wash on performance** and is justified on correctness. If you want a reason to
  keep it beyond consistency, it is the +70% median IC on `neg_ev_sales` — not the book.
- The market cap is DAILY's **month-end** figure on or before the rebalance, so EV is fresh to
  within a month, not to the day. Far better than 111 days; not zero.
- Both subperiod halves come from the same 18-year panel and universe.
- `EDGE_EV_POINT_IN_TIME=false` restores the old behaviour in one environment variable, and the
  run will then say so loudly in both results files.

---

## 10. Recommended next step

Nothing here is blocked. In priority order:

1. **Tell Cowork the index book moved** (RF → BP, 1.8% weight turnover) so the next paper-track
   rebalance is not read as drift.
2. **The negative-EV sign inconsistency** (section 8) is now the cheapest real defect left in
   the value theme — one guard, one held-out A/B.
3. Unchanged from the standing list: the forward paper-track vs SPY is still the top priority
   overall (CLAUDE.md #12), and the ML tree combiner (#16) is still the most promising new work.
