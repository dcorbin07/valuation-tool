# HANDOFF — live-app display fixes (PROMPT_app_fixes.md)

Session date: 2026-08-02. Branch: `worktree-app-display-fixes`.
Scope was the four cosmetic/data-display items in `PROMPT_app_fixes.md`. Nothing in the
options data cache, the backtests or Sharadar was touched. All four are done.

## What was actually wrong (the prompt's diagnosis was partly off — corrected here)

I probed the live site before changing anything (`valquo.co/api/hotstocks`,
`/api/valquo-index`) rather than working from the symptom description. Findings:

- **Company names and sectors are NOT missing on the live scan.** `DELL` comes back as
  `"name": "Dell Technologies Inc."`, `"sector": "Technology"`, and the live index payload
  reports `sector_data_available: true`. They were missing from the **UI** — the Index table
  had only `# / Ticker / Weight / Hot score / Market cap` columns, no Company and no Sector —
  and from the **exported book** `data/valquo_index.json`, which is produced by the Sharadar
  full-universe path and carries neither field (that file is what showed `"name": ""` and
  `sector_data_available: false`).
- **The $0.00 market cap was a unit bug, not missing data.** `market_cap` was arriving in
  **millions** (`275844.66` for Dell) while every consumer assumes **dollars**. The UI renders
  `market_cap / 1e9`, so $275.8B printed as `$0.0B`.

Root cause of the unit bug: `CompanyData.market_cap` is in millions by its own contract
(`data/models.py`), so `company_to_metrics` emitted millions, while `_fmp_to_metrics` emitted
FMP's dollars. Both feed the same scan. Two consequences beyond the display:

1. `valquo_index` keeps names above a `10e9` **dollar** large-cap floor. With millions, nothing
   cleared it, so the book silently degraded to `tilt: "largest half (too few names above the
   large-cap floor)"` — live right now. The Index has not been a large-cap book.
2. `prefilter`'s nano-cap floor compared a dollar figure against `MIN_MARKET_CAP_MM = 50`, i.e.
   `$50`. Under FMP it was inert; the junk filter was not doing its job.

## What changed

**1. One unit convention: USD dollars** (`valuation/screener/providers.py`)
- `METRICS_UNITS = "usd"`; every metrics dict is stamped with `units`.
- `company_to_metrics` scales the 11 absolute currency fields by 1e6 **after** the ratios are
  computed, so `earnings_yield` / `pe` / `ps` / margins are bit-for-bit unchanged. Verified in
  `test_metrics_are_in_usd_dollars_not_millions`.
- Cached fundamentals without a `units` stamp are discarded (`_usable_cache`) — a millions-era
  cache entry must not be mixed into a dollars-denominated cross-section.
- `prefilter` now compares `MIN_MARKET_CAP_MM * 1e6`. **This is a no-op for the backtest
  panel**, which already applies the same floor at `fundamental_panel.py:903` and `:1137`
  before its metrics reach `prefilter` at `:1199`. I checked this specifically.
- Fixed a real bug found on the way: `_fmp_to_metrics` had `return {...}` followed by
  unreachable code, so FMP rows were never stamped and would have been refetched every scan.

**2. Names and sectors sourced from the live feed**
- `run_scan` now backfills `name` / `sector` / `industry` / `market_cap` from the universe
  listing when the per-name fetch didn't supply them (`_fill_from_universe`). A `name` equal to
  the ticker counts as missing — that is Yahoo's fallback when `.info` is throttled, which it
  routinely is from cloud IPs. A real fetched value always wins.
- New `valuation/screener/profiles.py`: ticker → name/sector/industry from, in order, the
  store's own live-scan data (free — already fetched), the SEC filer list (keyless, one call),
  the bundled sector map, then FMP's profile endpoint hard-capped at 60 calls so a big book
  can't burn the free-tier quota. Results persist in the store's previously-unused `universe`
  table.
- `valquo_index.export()` decorates the **finished book** (tens of names, not the 1,800-row
  scored universe) and recomputes the sector block, so `data/valquo_index.json` now ships real
  names and a real sector breakdown instead of `"unknown": 1.0`.
- Explicitly **not** wired into the backtest panel: applying today's sector to a 1998 row is
  look-ahead. This only decorates an already-built book, where sector feeds no score.

**3. Diversification view + the missing columns** (`valuation/web/static/app.js`)
- Index table gains **Company** and **Sector** columns; Hot Stocks gains **Market cap**; the
  portfolio table gains **Company**.
- New sector-breakdown block above the Index table: weight bars per sector, sector count,
  largest sector, and "effective sectors" (inverse Herfindahl). When
  `sector_data_available` is false it says the data is missing rather than drawing one
  100% "unknown" bar.
- New `esc()` — company names and sectors are third-party strings going into `innerHTML`.

**4. Consistent formatting**
- New `mcap()`: `$B` by default, `$T` above a trillion, `$M` below a billion, two decimals,
  used everywhere market cap appears. (I added the T tier on top of the requested `$B` —
  `$3,502.14B` for a mega-cap reads badly. Say the word and it's one line to drop.)
- Removed two local `pct`/`num` shadows in the options scorecard that used a different decimal
  convention than the globals; added `spct()` for signed percentages. Percentages are now 1
  decimal everywhere, ratios 2, weights 2 in the Index and 1 in the portfolio.

**5. Visibility (small, related)**
- `run_scan`'s health block now carries `display_coverage` (name / sector / market_cap) and
  `universe_note`. A blank name is invisible to every scoring check — that is exactly how this
  sat on the live site unnoticed. The Hot Stocks tab warns when either is degraded.
- `FMPProvider` records **why** a universe call fell back instead of swallowing the exception.

## Tests

All suites green, run individually:

| suite | before | after |
|---|---|---|
| `tests/test_edge.py` | 89/89 | 91/91 (2 added) |
| `tests/test_screener.py` | 13/13 | 19/19 (6 added) |
| `tests/test_saas.py` | 20/20 | 20/20 |
| `tests/test_intraday.py` | 18/18 | 18/18 |
| `tests/test_engine.py` | 19/19 | 19/19 |
| `tests/test_bulk.py` | 14/14 | 14/14 |

`tests/screener_fixtures.py` was updated to emit dollars — it was the old millions convention,
so leaving it would have meant the tests passed against a contract nothing else used.

New tests worth knowing about:
- `test_valquo_index_market_caps_are_dollars_not_millions` — feeds the book millions-denominated
  caps and asserts the tilt does **not** claim "large-cap only". This is the regression pin.
- `test_valquo_index_export_fills_blank_names_and_sectors` — Sharadar-shaped rows (blank name
  and sector) in, populated book and `sector_data_available: true` out.
- `test_nano_cap_floor_is_applied_in_dollars`, `test_cache_written_before_the_usd_normalization_is_discarded`.

End-to-end smoke on a synthetic 154-name scan: `tilt: large-cap only` (was the degraded
fallback), `display_coverage {name: 1.0, sector: 1.0, market_cap: 1.0}`, caps rendering as
`$32.82B` etc.

## What Don needs to know

1. **The fix lands on the next scan, not on deploy.** The market caps already in the live DB are
   millions; the snapshot is rewritten by the scheduled scan (22:23 UTC / ~5:23pm ET, weekdays).
   Until then the Index still shows `$0.0B`. To see it immediately: GitHub → Actions →
   "Auto scans (free-tier bridge)" → Run workflow → kind `hot`.
2. **Add `FMP_API_KEY` as a GitHub Actions secret.** I added the env line to `auto-scan.yml`; the
   secret itself I cannot set. It is empty-safe today (the free EDGAR+Yahoo path still runs).
3. **Unrelated but worth your attention — the live scan is only covering ~191 names.** FMP's
   `company-screener` call is failing and falling back to the bundled list; the live universe is
   191 names, of which 154 score, so the "top decile" Index is a decile of 154. That is a real
   product problem, it is **not** in this prompt's scope, and I did not fix it. What I did do is
   make it visible: the failure reason is now recorded and shown in the Hot Stocks tab instead
   of being swallowed. Next session should read that message and fix the endpoint/params.
4. `valuation/edge/archive.py` records `market_cap` into the append-only archive. Rows written
   from today are dollars; rows before today are millions. Nothing computes on that column, but
   don't compare across the boundary without scaling.

## Recommended next step

Run the hot scan manually (item 1) and eyeball the Index tab — that is the whole payoff of this
session. Then take the FMP universe failure (item 3) as its own task; a 191-name universe caps
how good the book can be no matter how well the ranking works.
