# HANDOFF — Sharadar extraction + freeze verification

**Session:** 2026-08-03 · **Branch:** `worktree-sharadar-extract` · **Audit items:** 0c · D10 · C5
**Deliverable:** `SHARADAR_REFERENCE.md` (committed — the answers, so they survive the lapse)

Read-only on Sharadar throughout. No key printed, logged or committed. No `data/` committed.
Did not touch `options_universe.py`, `options_backtest.py`, `fundamental_panel.py`, `factors.py`,
`screen.py` or `paper_track.py` — the main edge-audit agent's correction files.

> **See the ADDENDUM at the end of this file (2026-08-04)** — the freeze has since been completed
> (six caches copied; `signal_coverage` now matches live) and audit item **B6** is answered
> (price history is FULL DEPTH; no Sharadar pull needed). The addendum also **corrects** one claim
> made below: the missing caches had **zero** effect on any backtest number, not the limited effect
> the "five signals" section originally states.

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

---
---

# ADDENDUM — 2026-08-04: freeze completed, and the B6 price-depth question answered

Two follow-ups requested after the session above. Both done; evidence below.

---

## A. The freeze is now a true standalone replacement

**Six auxiliary caches copied into `data/backtest_freeze_2026-08/bulk/prepared/`, each verified
sha256-identical to its source, and the freeze re-run now matches the live run's coverage exactly.**

Scope was decided by grepping which modules actually read each cache, not by copying everything
present:

| cache | size | feeds | sha256 (first 16) |
|---|---:|---|---|
| `short_interest.pkl` | 166.8 MB | `neg_days_to_cover`, `neg_short_interest_chg` | `88e0880b62850fde` |
| `edgar13d.pkl` | 9.4 MB | `activist_13d`, `passive_13g` | `1e107f34807eee83` |
| `elite_conv.pkl` | 7.0 MB | `sm_elite_conviction` | `68c6a48a2b4e1eb7` |
| `congress.pkl` | 1.1 MB | `congress_net_buy`, `congress_activity` | `0c65f3e181c85b08` |
| `usaspending.pkl` | 235 KB | `govt_award_momentum`, `govt_award_level` | `074abab1b38eb66e` |
| `cik_ticker.json` | 151 KB | EDGAR CIK-to-ticker map | `d3a4a2aefd30eb0d` |

**Deliberately NOT copied**, and this is a standing boundary, not an oversight:
`bars/` (68 MB), `theta/` (28 MB), `dgs3mo.csv`, `sec_names.json`. These belong to the options and
screener lanes — ThetaData is a **separate vendor on its own lifecycle**, and its cache already
lives independently under `data/options/`. This freeze exists because the *Sharadar* subscription
is lapsing. Mixing vendors would make "what is this snapshot" ambiguous later. **If ThetaData ever
needs a freeze, it gets its own.**

### Verification: `signal_coverage.below_floor` now matches live

| run | signals below the 5% floor |
|---|---|
| freeze, before the copy | **7** — `sm_elite_conviction` 0.0, `neg_days_to_cover` 0.0, `neg_short_interest_chg` 0.0, `activist_13d` 0.0, `passive_13g` 0.0, `govt_award_momentum` 0.0, `govt_award_level` 0.0 |
| **freeze, after the copy** | **2** — `govt_award_momentum` 3.36%, `govt_award_level` 3.61% |
| live | **2** — `govt_award_momentum` 4.03%, `govt_award_level` 4.34% |

**Set-identical to the live run.** All five previously-zeroed signals are populated. The two that
remain are below the floor in the live run too — a known pre-existing gap, not a freeze defect
(slightly lower on the freeze only because its universe is larger, which dilutes coverage).

### CORRECTION to the main report above

The section "The real defect: the freeze silently zeroes five signals" said the practical impact
was "confined to `sm_elite_conviction` inside the `institutional` theme (weight 0.143)".
**That was wrong. The impact on the backtest was exactly ZERO.**

The re-run is **bit-identical** to the pre-copy run on every headline number:

| metric | freeze BEFORE copy | freeze AFTER copy | live |
|---|---:|---:|---:|
| long-short t | 4.10447 | **4.10447** | 3.52024 |
| top-decile alpha | 0.13588 | **0.13588** | 0.11879 |
| monotonicity | -1.00000 | **-1.00000** | -0.95152 |
| CPCV PBO | 0.26667 | **0.26667** | 0.06667 |
| Deflated Sharpe | 0.99995 | **0.99995** | 1.00000 |

The reason is in `valuation/screener/settings.py`, which says it outright for each signal:
**"Measured, not scored."** `NUMBER_THEME` governs z-scoring and measurement; theme membership for
the composite is decided separately in `factors.py`, and all five were **tested and rejected by the
project's own gates** — `sm_elite_conviction` t +1.32 against a 2.0 bar and below both signals
already in the theme; short interest t +1.04 / +0.42; `activist_13d` t -0.69; `passive_13g` and
`govt_award_level` are **declared placebos**. Two of them additionally sit in `low_risk`, which
carries weight 0.0.

So the corrected reading: **no past or present backtest number was ever affected by the missing
caches.** What the gap actually cost was (a) a misleading `signal_coverage` block that flagged
seven failures where the live panel has two, and (b) the ability to re-test any of those five
signals from the freeze at all. Both are now fixed. The coverage guard did its job — it reported a
real absence — but the absence was of already-rejected signals.

---

## B. Audit B6 — is the freeze's price history full-depth, or truncated?

**VERDICT: FULL DEPTH. B6 is fixable from the freeze alone. No fresh Sharadar pull is required,
and Don does not need to buy a subscription for this item.**

### The truncation is at READ time, not in the data

`WRDSProvider.price_history` (`valuation/edge/data_providers.py:325`) ends with:

```python
df = df.sort_values("date").tail(days)
```

`build_fundamental_panel(lookback_years=18, horizon=63)` calls it as
`price_history(t, days=TD * lookback_years + horizon + 60)` = `252*18 + 63 + 60` = **4,659**.
That confirms the 4,659 figure exactly. It keeps the last N rows **per ticker**, so each ticker's
window floats relative to *its own* final bar — which is precisely the B6 complaint (truncate the
CALENDAR, not each ticker's series).

### What is actually on disk — per-ticker earliest-date distribution, SEP

Measured over all **3,735** per-ticker files in `backtest_freeze_2026-08/backtest/prices/`:

```
rows/ticker:  min 7   p10 695   median 3,524   p90 7,189   max 7,189
```

| earliest date | tickers |
|---|---:|
| **1997** | **1,647** |
| 1998-1999 | 204 |
| 2000-2004 | 312 |
| 2005-2009 | 234 |
| 2010-2014 | 279 |
| 2015-2019 | 306 |
| 2020-2021 | 501 |
| 2022-2026 | 252 |

- earliest date: **min 1997-12-31**, p25 1997-12-31, **median 2000-03-28**, p75 2017-04-27, max 2026-06-04
- last date: median and max **2026-07-31**
- **1,647 tickers (44.1%) begin at the very first bar available** (on or before 1998-01-02)

**1997-12-31 is SEP's own start-of-coverage**, not a truncation — the raw table begins there too.
No pull, at any price, could produce earlier data.

### How much the read-time cap actually discards

- **1,564 of 3,735 tickers (41.9%)** hold more than 4,659 bars, so they *are* truncated at read time
- **3,024,857 of 14,502,282 daily bars (20.9%)** are thrown away by the `.tail(4,659)` call

That is the size of the prize for fixing B6: a fifth of the price history already on disk is
currently discarded before it reaches the panel.

### Is the derived export itself lossy? No.

Cross-checked the per-ticker export against the raw **3.2 GB `bulk/sep.csv`**
(46,248,674 rows over 21,938 tickers, spanning 1997-12-31 to 2026-07-31):

| check | result |
|---|---|
| tickers present in both | 3,734 |
| tickers where the export has FEWER rows than raw | **0** |
| tickers whose RAW history starts EARLIER than the export | **0** |

**The export preserved every available bar for every ticker in the universe.** Nothing was lost at
export time; the freeze carries the full depth twice over (derived + raw).

### What this means for B6

1. **Fixable from the freeze alone.** The fix is to slice by calendar date instead of
   `.tail(days)` — a read-side change in `price_history`. Every bar it needs is already on disk.
2. **No subscription needed for this item.** Neither for depth (already complete to SEP's own
   1997-12-31 origin) nor for breadth.
3. **One precision point:** the derived export covers 3,735 tickers, while raw SEP holds 21,938.
   That difference is a **universe choice**, not a depth truncation. If a future B6 fix wants names
   outside the exported universe, the raw `bulk/sep.csv` in the freeze has all 21,938 — still no
   pull required.

**Caveat, stated rather than buried:** this establishes the *data* is sufficient. It does not
measure what fixing B6 does to any result. Restoring 20.9% more history — disproportionately the
oldest bars and the delisted names — will move the momentum and reversal inputs and could move the
headline in either direction. That is a research question for whoever takes B6, and it should go
through `holdout_theme_validate()` like any other change.

---

## Housekeeping

- `BACKTEST_RESULTS.json` / `.md` were clobbered by both re-runs (the panel always writes them to
  the repo root) and have been **restored to the canonical `long_short_tstat = 3.5202358069482473`,
  `top_decile_alpha = 0.11879`**. Tracked tree verified clean.
- The freeze copies were left writable rather than marked read-only like the original freeze files,
  so `bulk.py` can refresh them in place if a cache is ever rebuilt.
