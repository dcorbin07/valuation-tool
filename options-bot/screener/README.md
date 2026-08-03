# Daily Stock Screener — Architecture, Status & Deployment

A daily automated screener that ranks small/mid-cap U.S. stocks on an
evidence-based composite (value · quality/growth · momentum · insider-quality),
splits them into two risk buckets, deep-dives new top names with Claude, posts
to Discord, logs everything for an honest benchmark-relative track record, and
periodically asks Claude (advisory only) how to improve without overfitting.

**Cost:** $0 data (SEC EDGAR + free price feed) · $0 host (Oracle free tier) ·
a few $/mo Claude (Opus dives on *new* top names only, hard $5/day cap). Under $30 all-in.

---

## Design decisions (locked)

- **Two buckets.** *Established* (profitable): DCF-gap value + quality + momentum +
  insider. *Speculative* (unprofitable): EV/Sales-vs-peers + revenue growth/acceleration +
  momentum + insider. **Profitability is irrelevant in the Speculative bucket**, so an
  unprofitable gem is never crowded out by mature profitable names.
- **Universe:** U.S. common equity under $10B, with an override letting larger names
  through only on a top-3 composite or an insider open-market cluster. Fundamentals are
  cached and refreshed quarterly; membership/price recomputed daily.
- **Deep dives:** Opus 4.8 on *new* top entrants only. A name dropping out and returning
  within 30 days reuses its analysis. Staleness re-dive at 90 days. **Any major event
  overrides this** and re-dives + alerts, even for a known name.
- **Alerts (separate Discord channels):** `daily_list`, `insider_flags`,
  `improvement_suggestions`. Throttled to 3/name/week.
- **Self-review:** weekly/monthly, **advisory only** — Claude proposes, you approve.
  Sample-aware (no conclusions below ~40 logged picks), mechanism-driven not curve-fit,
  strict point-in-time.
- **Guards:** $5/day cost breaker, data-health check (skip+alert if the feed looks broken),
  liquidity floor, ticker hygiene, paper/dry-run mode.

---

## Module status — all built

| Module | Purpose | Status |
|---|---|---|
| `config.py` | every tunable knob | ✅ built |
| `scoring.py` | two-bucket scoring, insider-quality weighting, gates | ✅ built + unit-tested |
| `decisions.py` | dive eligibility, event detection, throttle, cost/health guards | ✅ built + unit-tested |
| `store.py` | SQLite: universe cache, dive memory, picks, track record, spend | ✅ built + unit-tested |
| `edgar.py` | fundamentals (XBRL), Form 4 insiders, 8-K items, Form-4 firehose | ✅ built · validate live |
| `prices.py` | free price/volume (Stooq primary, yfinance fallback) | ✅ built · validate live |
| `claude_analyst.py` | Opus deep dive + advisory self-review | ✅ built |
| `discord_alerts.py` | webhook posting to the 3 channels, batched embeds | ✅ built |
| `pipeline.py` | daily orchestration (cached fundamentals + candidate-pool insider) | ✅ built + flow-tested |
| `insider_poller.py` | intraday EDGAR Form-4 feed → real-time flags | ✅ built · validate live |

The engine (scoring/decisions/store) is unit-tested and the full `pipeline` flow is
tested end-to-end on synthetic data. The EDGAR/price/Discord I/O must still be validated
against live endpoints on your box (it can't be exercised from a sandbox).

---

## Review fixes (Jun 2026)

This build incorporates a code-review pass:

- **Pricing bug fixed.** `MODEL_RATES` for `claude-opus-4-8` was $15/$75 (3× too high);
  corrected to the actual **$5/$25** per MTok. This had been inflating recorded spend 3×
  and would have tripped the cost breaker far too early.
- **Daily EDGAR load cut ~100×.** Fundamentals are now cached (`FUNDAMENTALS_TTL_DAYS`,
  default 90) and reused; only price is refreshed daily. The expensive insider Form-4 pull
  now runs **only for the candidate pool** (`CANDIDATE_POOL_PER_BUCKET`, default 40/bucket),
  not the whole universe. (Verified: a 2nd run refetches 0 fundamentals; insider pulls stay
  bounded to the pool.)
- **yfinance fallback fixed.** It used an invalid `"400d"` period that silently returned
  empty; now uses a valid period and trims.
- **Day-over-day fixed.** "New/dropped/climbing" now compares against the actual last run
  date (handles weekends/holidays), not a naive `today − 1`.
- **Deprecation + robustness.** `datetime.utcnow()` → timezone-aware; safer ticker handling.
- **Modeling precision.** EBITDA now adds back D&A (real EBITDA, not operating income); ROE is
  computed (net income / shareholders' equity) and now drives the quality score; EV/Sales
  cheapness percentile is computed **within sector** (thin sectors fall back to the whole cohort).
- **Renamed `--paper` → `--dry-run`.** This tool posts research, it does not trade, so "paper"
  was misleading. `--dry-run` runs the full pipeline but prints instead of posting to Discord.

---

## The universe question (read this before scaling up)

The default `universe_tickers()` scans every EDGAR filer (~13k). Even with fundamentals
cached, that's a large daily **price** pull and a slow first run. The recommended approach:
seed the universe from the **holdings of IWM (Russell 2000) + IJR (S&P SmallCap 600)** —
those ETFs *are* the liquid sub-$10B universe this screener targets (~2,600 names), they
match the benchmarks already in config, and they keep the daily pull tractable. Until you
wire that in, set `UNIVERSE_LIMIT` in config to bound the first runs.

---

## Deploy (Oracle Cloud free tier, or any always-on Linux box)

1. **Get the code on the box** and install deps:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure secrets:** `cp .env.example .env` and fill in:
   - `ANTHROPIC_API_KEY`
   - `EDGAR_USER_AGENT` — `"Your Name you@email.com"` (EDGAR *requires* a real identifier)
   - `DISCORD_WEBHOOK_DAILY`, `DISCORD_WEBHOOK_INSIDER`, `DISCORD_WEBHOOK_IMPROVE`
3. **Validate without posting** (prints to console instead of Discord):
   ```bash
   python pipeline.py --dry-run
   ```
   Watch for: a reasonable universe size (health gate needs ≥ 500), sane scores, and that
   EDGAR fundamentals/insider parsing actually returns data. The XBRL concept lists and the
   Form-4 parser are the most likely things to need tuning on first contact with real data.
4. **Go live + schedule (cron):**
   ```cron
   # daily run ~30 min after the close (note: cron uses the box's timezone; UTC shown)
   30 21 * * 1-5  cd /path/to/screener && /usr/bin/python3 pipeline.py >> run.log 2>&1
   # intraday insider poller, every 45 min during market hours
   */45 13-20 * * 1-5  cd /path/to/screener && /usr/bin/python3 insider_poller.py >> poller.log 2>&1
   # weekly advisory self-review (Sundays)
   0 14 * * 0  cd /path/to/screener && /usr/bin/python3 pipeline.py --review >> review.log 2>&1
   ```

---

## Honest status & expectations

The brain is done and verified; the live plumbing is built and must be proven against live
data on your box. This is an **advisory research tool**, not an autotrader — it surfaces and
explains candidates and tracks picks against small-cap benchmarks; it does not place orders.

## Edge validation — prove the score predicts returns BEFORE trusting it

Two modules added to test whether the composite has any real predictive power (it has never
been shown to — until now it was a plausible-looking formula):

- **`cross_sectional.py`** — self-calibrating scoring. Each factor is standardized across the
  universe (winsorized z-score) per date and combined by weight, replacing the old absolute
  thresholds. "Good" is relative to peers that day, not a hard-coded number.
- **`backtest_engine.py`** — consumes a point-in-time panel (name × rebalance date, with the
  composite and realized forward return) and reports the Information Coefficient (rank
  correlation of score vs. forward return), per-factor IC, quantile spread after costs,
  long-top-vs-benchmark, and an out-of-sample split. It calls "edge" only when the IC is
  significant, the quantiles are monotonic, the spread survives costs, AND it holds
  out-of-sample — so a lucky equity curve doesn't pass. (Unit-tested on synthetic data:
  detects a real embedded signal; rejects pure noise even when the top quintile happened to
  beat the benchmark.)

**Still needed: the point-in-time panel builder (the data layer).** To feed the engine you
need each name's factors *as known on each historical date* (filings filed on/before that
date, originally-reported values) plus forward prices.

> **Survivorship caveat.** Free price feeds (Stooq/yfinance) only carry names that still
> trade, so delisted losers are missing — any edge will look better than reality. A free
> first pass is a screen, not proof. If it's promising, confirm on a survivorship-free
> point-in-time dataset (e.g. Sharadar SF1/SEP via Nasdaq Data Link) before trusting it.

**The data layer is now built (free first pass):**
- **`pit_data.py`** — reconstructs each name's factors *as known on each rebalance date* (only
  filings filed on/before that date, values as reported then) and pairs them with the realized
  forward return. (Unit-tested: future filings are correctly hidden — no look-ahead.)
- **`run_backtest.py`** — fetches EDGAR fundamentals + free prices, builds the panel, scores
  each cross-section (sector-relative value + quality + momentum + growth), and prints the
  verdict. **No Discord, no Opus/AI calls, no cost** — one console report.

Run it:
```bash
python run_backtest.py          # only EDGAR_USER_AGENT needed in .env; edit CONFIG at top
```
It's slow on the first run (per-name EDGAR + price pulls) and excludes the most recent dates
(no forward window yet). Read the `vs-random`-style verdict, but remember the survivorship
caveat above: a positive result means "confirm on survivorship-free data," not "deploy."
