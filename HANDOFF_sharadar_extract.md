# HANDOFF — Sharadar extraction + freeze verification

**Session:** 2026-08-03 · **Branch:** `worktree-sharadar-extract` · **Audit items:** 0c · D10 · C5
**Deliverable:** `SHARADAR_REFERENCE.md` (committed — the answers, so they survive the lapse)

Read-only on Sharadar throughout. No key printed, logged or committed. No `data/` committed.
Did not touch `options_universe.py`, `options_backtest.py`, `fundamental_panel.py`, `factors.py`,
`screen.py` or `paper_track.py` — the main edge-audit agent's correction files.

---

## One line

**The key was live and everything was extracted in time.** The schema questions are all settled
and written to `SHARADAR_REFERENCE.md`. **The freeze runs the entire backtest with no API key —
proven end to end — but it is NOT a byte-for-byte reproduction of the live working set, and it
silently zeroes five signals** because six non-Sharadar auxiliary caches were never copied into
it. None of those five is threatened by the lapse; details and the fix are below.

---

## Guardrail first: was the key actually live?

**Yes.** A missing or unentitled Nasdaq Data Link key returns *sample* data rather than an error,
so this was checked before anything was trusted:

| check | result |
|---|---|
| AAPL PIT market cap 2015-06-30 (DAILY) | **$722,571.4M = $722.57B** vs expected ≈$722.6B ✅ |
| SEP most recent bar | **2026-08-03** — that day, not a stale demo window ✅ |
| Bundle tables reachable | SEP, SFP, SF1, SF2, SF3, SF3A, SF3B, TICKERS, DAILY, ACTIONS, EVENTS, SP500, INDICATORS ✅ |

---

## Task 1 — does the freeze reproduce? **Runs: YES. Reproduces exactly: NO (expected).**

Method: two full-universe backtests launched **simultaneously on identical code**, one sourced
from `data/backtest_freeze_2026-08/backtest`, one from the live `data/backtest`. Running them
together is what separates *data* drift from *code* drift — comparing the freeze against the
recorded `last_result.json` alone would have confounded the two.

### The checkpoints

| checkpoint | live working set | freeze | verdict |
|---|---|---|---|
| AAPL 2015-06-30 PIT market cap | $722,571.4M | **$722,571.4M** (read from the freeze's own `daily.pkl`, no key) | ✅ identical |
| fundamentals rows | 197,265 | **230,488** | drift — expected |
| usable universe | **2,710** names | **2,875** names | drift — expected |
| price files | 2,998 | 3,735 | drift — expected |
| rebalance dates | 110 | 110 | ✅ identical |

The row/name drift is **not a defect**. The freeze is a *fresher and larger* pull (through
2026-08-01) than the live export, so it legitimately has more data. The `~197,265 / ~2,710`
figures in CLAUDE.md describe the live export, and the live re-run reproduced them exactly
(2,710 usable tickers). A freeze that matched them would mean the freeze had pulled *less* data.

### Headline numbers

| metric | FREEZE | LIVE (re-run today) | recorded `last_result.json` |
|---|---:|---:|---:|
| long-short t | **4.104** | **3.520** | 3.396 |
| top-decile alpha | **+13.59%** | **+11.88%** | +11.82% |
| long-short ann | +20.45% | +17.58% | +17.16% |
| equal-weight ann | +16.52% | +16.55% | +16.55% |
| monotonicity | **−1.000** | −0.952 | −0.952 |
| CPCV PBO | **26.7%** | **6.7%** | 6.7% |
| Deflated Sharpe | 0.99995 | 0.99999 | 0.99999 |
| CPCV adopt | False | False | False |
| breakeven one-way | **260.9 bps** | **234.5 bps** | 236 bps |
| hold-until-exit CAGR | +30.48% | +27.15% | +26.47% |

**The live re-run reproduces CLAUDE.md's current stated headline exactly** (LS t 3.520,
alpha +11.88%, breakeven ~236bps). The gap to `last_result.json` (3.396 → 3.520) is precisely the
EV point-in-time fix that CLAUDE.md already records as shipped — that file predates it. So the
code baseline is confirmed sound, and the freeze/live difference is genuinely about data.

**Do not read the freeze's better headline as good news.** It differs from the live run on
**three axes at once** — a larger and fresher universe, a later end date, and five missing signals
(below) — so the +0.58 t-stat cannot be attributed to any one of them. The honest reading is that
the two panels are not comparable at that precision. The one number that moved the *wrong* way is
**PBO 6.7% → 26.7%**: a 4× higher probability of backtest overfitting, still comfortably under the
50% bar, but worth knowing.

Reassuringly, `holdout_validation` returns **`low_risk: confirmed`** on both panels — the deployed
zeroing decision replicates on the freeze independently.

### The real defect: the freeze silently zeroes five signals

`signal_coverage.below_floor` differs sharply between the two runs:

| signal | theme | freeze coverage | live coverage |
|---|---|---:|---:|
| `sm_elite_conviction` | institutional | **0.0%** | ok |
| `activist_13d` | institutional | **0.0%** | ok |
| `passive_13g` | institutional | **0.0%** | ok |
| `neg_days_to_cover` | low_risk | **0.0%** | ok |
| `neg_short_interest_chg` | low_risk | **0.0%** | ok |
| `govt_award_momentum` | growth | 0.0% | 4.03% (already below the 5% floor) |
| `govt_award_level` | growth | 0.0% | 4.34% (already below the 5% floor) |

**Cause:** the freeze snapshotted only the five *Sharadar-derived* prepared caches
(`actions/daily/events/sf3/tickers.pkl`). The live `data/bulk/prepared/` holds **six more** that
were built Aug 1–3 and never copied: `elite_conv.pkl`, `edgar13d.pkl`, `short_interest.pkl`,
`usaspending.pkl`, `congress.pkl`, plus `cik_ticker.json` / `sec_names.json` / `dgs3mo.csv`.

This is exactly the failure mode CLAUDE.md's COVERAGE RULE describes — the run completed normally,
raised nothing, and two themes quietly ran on fewer inputs. The coverage guard caught it, which is
the guard doing its job.

**Good news, and the reason this is not urgent:** *none of these is Sharadar data*, so the lapse
does not threaten any of them.

- `elite_conv.pkl` ← derived from the **SF3 bulk file**, which IS in the freeze (2.9 GB) → rebuildable from the freeze itself
- `edgar13d.pkl` ← SEC EDGAR (free)
- `short_interest.pkl` ← FINRA (free)
- `usaspending.pkl` / `congress.pkl` ← USAspending API + SEC (free)

Also note two of the five are already-rejected or placebo signals by the project's own gates
(`activist_13d` t −0.69 rejected; `passive_13g` is a declared placebo), and the two `low_risk`
signals feed a theme that is **weighted zero**. So the practical impact is confined to
`sm_elite_conviction` inside the `institutional` theme (weight 0.143).

**Recommended fix (one command, no re-pull):** copy the six caches into
`data/backtest_freeze_2026-08/bulk/prepared/`. That makes the freeze a genuine standalone
replacement. Left undone deliberately — the freeze is the other bot's lane and its files carry the
Windows read-only bit.

---

## Task 2 — `scripts/verify_sharadar.py` against the live key (first time ever)

Script lives at `options-bot/quant_bots/scripts/verify_sharadar.py` (not top-level `scripts/`).
It reads `NASDAQ_DATA_LINK_API_KEY`; the project's key is `SHARADAR_API_KEY` in the root `.env` —
same key, different variable name. Full output preserved in the session log.

All answers are written up in **`SHARADAR_REFERENCE.md`**. Summary of each:

### (a) EVENTS `eventcode` legend — **obtained, and it is authoritative**

The legend is **not** in the bulk download (as `bulk.py` correctly notes), but it **is** published
via `SHARADAR/INDICATORS?table=EVENTCODES`. All **37 codes** are now transcribed in the reference
file with their observed frequencies.

**It confirms the empirical decode: code 22 = "Results of Operations and Financial Condition."**
`EARNINGS_CODES = {"22"}` in `valuation/edge/bulk.py` is correct and is no longer an inference.
The August 2026 decode-by-signature work stands.

Three things the legend reveals that matter for S17 / earnings work:

1. **Earnings events do not exist before 2004-08-23** — code 22's first occurrence is exactly the
   day the SEC's amended Form 8-K took effect. Ten other codes start on that same date, and code
   40 stops 2004-08-20 and is replaced by an identically-titled code 41. **This is a hard
   structural floor**, not a coverage gap better cleaning could close. Any earnings-conditioned
   study is limited to roughly the back half of the panel.
2. **Coverage is partial even after 2004** — code 22 runs 1.65 events per ticker per year against
   the ~4 a full quarterly calendar implies, confirming `bulk.py`'s existing caveat at population
   scale.
3. **Codes 34 and 35 are Schedule 13G and 13D filings, not 8-K items** — which is why they predate
   2004 and why 34 is the third most common code overall. Both appear discontinued (last seen
   2024-12-17 and 2025-05-16); do not use them near the end of the sample.

35 of the 37 codes occur in the data; **36** and **61** never appear in 2.5M rows. No code occurs
that is absent from the legend — **the enum is closed.**

### (b) ACTIONS action enum — **complete and closed**

19 values in the legend, **19 observed in 671,781 rows — exact match.** Full table with row counts
and date ranges in the reference file. Three gotchas found:

- **`contraticker`/`contraname` hold the literal string `"N/A"`, not an empty field.** A truthiness
  test is TRUE for all 549,076 dividend rows.
- **Delisting is spread across four actions** — `delisted` (19,208), `regulatorydelisting` (884),
  `voluntarydelisting` (376), `bankruptcyliquidation` (3,347). A mask matching only `delisted`
  misses 1,260 events.
- **Every `initiated` row is dated 1997-12-31** — a start-of-coverage marker, not a real action.

### (c) TICKERS.category — **exhaustive, 25 values**

Previous work only ever enumerated the SEP subset (15). All 25 are now recorded with the table
each belongs to. Equity categories live on SEP/SF1/SF2, fund categories only on SFP,
`Institutional Investor` only on SF3B — **filtering on `category` without also filtering on
`table` mixes stocks, funds and 13F filers.**

Flagged, not changed: `core/pit_universe.py` excludes 9 of the 15 SEP categories. Excluding
preferreds and warrants is right; excluding the **382 Canadian Common Stock** names (316 of which
carry SF1 fundamentals) is a judgement call worth a look.

### (d) SF1 `%` fields — **fractions (`0.15`), not `15.0`. No 100× risk anywhere.**

Settled three independent ways: `INDICATORS` gives `unittype = ratio` for every such column (there
is **no** `percent` unittype in the table at all); ART `roe` has median **0.0730** / p90 0.3050
across 200,000 rows; the live AAPL FY2025 sample returned `roe 1.64`, `roa 0.328`.

Caution recorded: ~3.5% of `roe` values legitimately exceed |3| (Apple's own is 1.64), so a
magnitude filter rejecting `|roe| > 3` as "must be a percentage" would discard real data.

**A different units trap IS live, and it is worse:** `marketcap` and `ev` are **raw USD in SF1**
but **USD *millions* in DAILY**. Verified on AAPL — SF1 gives `714,094,848,840`, DAILY gives
`722,571.4` for the same week. **1,000,000× apart.** Any code mixing the two without rescaling is
wrong by six orders of magnitude.

### (e) **THE BIG ONE — does a restatement append a new ARQ row? YES.**

> **`ORDER BY datekey DESC LIMIT 1` is silent look-ahead. `pit_fundamental()`'s earliest-datekey
> rule is REQUIRED, not merely defensive.**

The script found this on 5 of 7 tickers. I then settled it at **population scale** on the freeze's
full 3.2M-row SF1, because a 7-ticker sample is not a basis for a rule this load-bearing:

| measure | value |
|---|---|
| ARQ `(ticker, reportperiod)` keys | 652,337 over 17,021 tickers |
| keys with >1 `datekey` | **23,211 (3.558%)** |
| tickers affected at least once | **9,427 (55.4%)** |
| max datekeys on one period | 9 |
| gap earliest→latest | median **29d**, p90 **86d**, max **807d** |

**And the appended row is not cosmetic:**

| field | differs | median \|Δ\| where it differs |
|---|---:|---:|
| `eps` | 20.1% | **16.91%** |
| `netinc` | 15.1% | **19.93%** |
| `equity` | 14.0% | 3.85% |
| `assets` | 12.1% | 1.50% |
| `revenue` | 8.1% | 2.38% |

Real example: `ABBNY 2018-12-31` revenue **7,395,000,000 → 889,000,000** between datekeys
2019-02-28 and 2019-03-28.

**What the defensive choice costs — the question nobody had answered: essentially nothing, and it
is the right trade.** The earliest datekey *is* the first publication, so there is no timeliness
penalty; all you forgo is the corrected figure, which did not exist at the rebalance. Two
tempering facts: ~52% of duplicates resolve within 30 days and look like filing mechanics rather
than restatements (some are 1–2 days apart and change revenue by $1,000), while the genuine late
restatements are the **1.0% beyond 180 days** — precisely the cases where using the latest datekey
would do the most damage.

**Verdict: keep the earliest-datekey rule. Do not "optimise" it away.**

Caveat stated rather than buried: one snapshot proves Sharadar **appends**; it cannot prove
Sharadar never *also* rewrites in place, which is invisible in a single download. The freeze is
now snapshot #1 if anyone wants to settle that later.

### (f) Bonus answers from the same run

- **SEP has exactly 10 columns and NO `dividends` column** (published sources disagree; the key
  settles it). Dividend amounts are in ACTIONS. `closeadj` = returns, `closeunadj` = price levels;
  AAPL 2019-01-04 `closeunadj/close` = exactly 4.000, the Aug-2020 split.
- **Survivorship is intact in the freeze**: 15,628 delisted SEP tickers, **100%** retaining a full
  price range.
- **`isdelisted` cannot be used as an API filter** — `HTTP 422 QESx08`. Test 6 of
  `verify_sharadar.py` fails against a *live* key for this reason; the script is wrong, not the
  entitlement. Request the column and filter locally.
- **SFP is inside the SFA bundle** — settles a question the script's own docstring flags as
  unresolved between Nasdaq's help centre and the datasheet.

### (g) Confirmed at population scale: why five factors were empty (D10)

Across all 3,203,836 SF1 rows, Sharadar populates `roe`/`roa`/`roic`/`assetturnover` **only** in
the T and Y dimensions:

| dimension | rows | roe / roa / roic / assetturnover |
|---|---:|---:|
| ART | 685,084 | 89.4% |
| ARY | 186,749 | 90.7% |
| MRT | 734,630 | 85.1% |
| **ARQ** | 678,341 | **0.0%** |
| **MRQ** | 715,611 | **0.0%** |

**This is a property of Sharadar, not a broken export or a bad pull.** There is no flag that makes
ARQ return them; deriving them from line items (as `_sf1_to_metrics` now does) is the only fix.
`netmargin` is the exception — populated in ARQ at 91.0%, because it needs no averaged denominator.

---

## Task 3 — direct-bundle schema conformance (supports D1, the $29/mo switch)

**Conforms.** The bulk export's SF1 schema matches Sharadar's own authoritative column list
**exactly — 112 columns, zero missing in either direction.** Every column `bulk.py` indexes by
name is present, and the freeze already runs the full backtest with no API key, which is the
practical proof. Nothing in the loader assumes anything the direct bundle would not also provide.

One defect found while checking, **reported not fixed** (this bot writes docs only):

- **`ebitmargin` does not exist in SF1** — the real column is `ebitdamargin`. It is listed in
  `WRDSProvider._KEEP` (`valuation/edge/data_providers.py:262`) and read at
  `valuation/edge/fundamental_panel.py:353` as the `op_margin` fallback. The primary path
  (`ebit / rev`) works, so severity is **low** — but the fallback can never fire, and this is the
  same silent-missing-column class that has now bitten the project five times.

---

## Gap worth acting on before the lapse

**Four entitled tables were never frozen: `SP500`, `SF3B`, `METRICS`, `INDICATORS`.** All are
small; all are permanently unavailable after the lapse. `SP500` (current + historical index
constituents) is the most valuable — it is the natural benchmark and a clean universe definition.

I preserved `INDICATORS` myself, since it is the source of every legend in the reference file and
the session scratch directory is deleted with the job:

```
data/sharadar_INDICATORS_2026-08-03.csv    (373 rows — gitignored, on disk)
```

**Recommend the freeze bot pull `SP500`, `SF3B` and `METRICS` into the freeze while the key
works.** Not done here — that is the freeze bot's lane, and the freeze directory is read-only.

---

## Test status

All green, run from the primary checkout on current `main` code:

```
tests/test_edge.py             166/166
tests/test_freeze.py            13/13
tests/test_bulk.py              14/14
tests/test_sector_neutral.py     6/6
tests/test_pead.py              12/12
                       total   211/211
```

This session added one markdown file and one gitignored CSV — no code changed, so nothing could
regress. Suites were run to confirm the tree is green, not because anything was touched.

---

## Recommended next steps, in order

1. **Copy the six missing auxiliary caches into the freeze's `bulk/prepared/`** so it is a true
   standalone replacement. Zero API calls; the freeze already has everything else. Until then,
   any backtest sourced from the freeze runs `institutional` on fewer inputs.
2. **Pull `SP500`, `SF3B`, `METRICS` into the freeze before the key dies.** Small, cheap, and the
   window does not reopen.
3. **Fix `ebitmargin` → `ebitdamargin`** in `_KEEP` and `fundamental_panel.py:353`, or drop the
   dead fallback. Low severity, trivial, but it is a live phantom column.
4. **S17 / earnings work can now proceed** — code 22 is confirmed authoritative. Design it around
   the **2004-08-23 floor** and the **1.65 events/ticker/year partial coverage** from the outset;
   both are properties of the data that no amount of cleaning will change.
5. Consider whether the **382 Canadian Common Stock** names should stay excluded from the PIT
   universe.

## What I deliberately did NOT do

- Did not modify the freeze (other bot's lane, read-only bits set).
- Did not fix `ebitmargin` or `pit_universe.py` — this bot writes docs and a reference file only,
  and both sit near the main agent's correction files.
- Did not re-open the earliest-datekey rule. The evidence says keep it.
