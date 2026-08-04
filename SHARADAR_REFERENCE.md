# SHARADAR_REFERENCE.md — the schema answers, frozen before the subscription lapses

**Captured 2026-08-03 against a CONFIRMED-LIVE key.** Audit items **0c / D10 / C5**.

The Sharadar subscription is ending. Everything in this file was extracted from the live API
and the `data/backtest_freeze_2026-08/` snapshot while both were still available, so that after
the lapse nobody has to guess at an enum, a unit, or a point-in-time rule. **Nothing here is
copied from documentation or memory** — every value was read out of the data or out of
Sharadar's own machine-readable `INDICATORS` table. Where a claim rests on a sample rather than
the population, it says so.

Companion: `HANDOFF_sharadar_extract.md` (what was run, the freeze-reproduction result).

---

## 0. Provenance — how each answer was obtained

| Source | What it settles |
|---|---|
| `SHARADAR/INDICATORS` (live API, 373 rows) | The authoritative legends: `EVENTCODES` (37), `ACTIONTYPES` (19), per-column `unittype` for all 112 SF1 fields, and table descriptions. **Not present in any bulk download** — it must be pulled from the API, which is why it is transcribed in full below. |
| `data/backtest_freeze_2026-08/bulk/*.csv` | Population-level observed enums and coverage: ACTIONS 671,781 rows, EVENTS 2,537,722 rows, TICKERS 78,881 rows, SF1 3,203,836 rows. |
| `options-bot/quant_bots/scripts/verify_sharadar.py` | Entitlement, SEP columns, live unit spot-checks. Run against the real key for the first time on 2026-08-03. |

**Key liveness was confirmed before anything else was trusted.** A missing or unentitled Nasdaq
Data Link key returns *sample* data rather than an error, so the check was the project's standing
checkpoint: AAPL point-in-time market cap on 2015-06-30 came back **$722,571.4M = $722.57B**
against the expected ≈$722.6B, and SEP returned rows through **2026-08-03** (that day). Live.

To re-pull the legend while the key still works:

```
GET https://data.nasdaq.com/api/v3/datatables/SHARADAR/INDICATORS?qopts.export=true
    (auth via the x-api-token header)
```

---

## 1. Entitlement — what this key actually reaches

All eight tables `verify_sharadar.py` probes are reachable, plus the four the freeze pulled:

`SEP` · `SFP` · `SF1` · `SF2` · `SF3` · `SF3A` · `SF3B` · `TICKERS` · `DAILY` · `ACTIONS` ·
`EVENTS` · `SP500` · `INDICATORS`

`SFP` returned 0 rows for the AAPL probe, which is correct rather than a permission problem —
AAPL is not a fund. The freeze pulled a 1.1 GB `sfp.csv`, so the entitlement is real. **This
settles the long-standing "is SFP inside SFA?" question: yes, it is included.**

---

## 2. EVENTS — the `eventcodes` legend (audit 0c, needed for S17 / earnings work)

**This is the answer the project has been missing.** `bulk.py` decoded code 22 empirically in
August 2026 because "Sharadar ships no legend with the EVENTS download". That is true of the
download, but the legend *is* published through `SHARADAR/INDICATORS?table=EVENTCODES`. It is
reproduced here in full, alongside how often each code actually occurs in the freeze.

**The empirical decode was right: code 22 = "Results of Operations and Financial Condition"** —
the Form 8-K item companies file their earnings release under. `EARNINGS_CODES = {"22"}` in
`valuation/edge/bulk.py` is confirmed correct, and is no longer an inference.

| code | meaning | occurrences | tickers | first | last |
|---|---|---:|---:|---|---|
| 11 | Entry into a Material Definitive Agreement | 217,101 | 11,553 | 2004-08-23 | 2026-07-31 |
| 12 | Termination of a Material Definitive Agreement | 20,658 | 7,236 | 2004-08-23 | 2026-07-31 |
| 13 | Bankruptcy or Receivership | 3,490 | 1,882 | 1994-01-05 | 2026-07-15 |
| 14 | Mine Safety - Reporting of Shutdowns and Patterns of Violations | 263 | 73 | 2011-10-17 | 2026-07-31 |
| 15 | Receipt of an Attorney's Written Notice Pursuant to 17 CFR 205.3(d) | 5 | 5 | 2003-08-07 | 2004-08-18 |
| 21 | Completion of Acquisition or Disposition of Assets | 70,109 | 11,999 | 1994-01-04 | 2026-07-31 |
| **22** | **Results of Operations and Financial Condition** ← earnings | **385,896** | **10,149** | **2004-08-23** | **2026-07-31** |
| 23 | Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant | 66,150 | 8,463 | 2004-08-24 | 2026-07-31 |
| 24 | Triggering Events That Accelerate or Increase a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement | 3,415 | 1,946 | 2004-08-26 | 2026-07-31 |
| 25 | Cost Associated with Exit or Disposal Activities | 7,832 | 3,031 | 2004-08-24 | 2026-07-31 |
| 26 | Material Impairments | 3,275 | 1,751 | 2004-08-25 | 2026-07-31 |
| 31 | Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing | 25,614 | 7,908 | 2004-08-24 | 2026-07-31 |
| 32 | Unregistered Sales of Equity Securities | 39,452 | 7,459 | 2004-08-23 | 2026-07-31 |
| 33 | Material Modifications to Rights of Security Holders | 17,889 | 7,358 | 2004-08-23 | 2026-07-31 |
| 34 | Schedule 13G Filing | 496,655 | 16,065 | 1994-01-04 | 2024-12-17 |
| 35 | Schedule 13D Filing | 147,289 | 13,255 | 1993-11-08 | 2025-05-16 |
| 36 | Notice under Rule 12b25 of inability to timely file all or part of a Form 10-K or 10-Q | **0** | 0 | — | — |
| 37 | Tender Offer Statement under Section 14(d)(1) or 13(e)(1) of the Securities Exchange Act of 1934 | 34,681 | 3,882 | 2000-01-24 | 2026-07-28 |
| 40 | Changes in Registrant's Certifying Accountant | 7,145 | 3,727 | 1994-01-13 | 2004-08-20 |
| 41 | Changes in Registrant's Certifying Accountant | 11,021 | 5,113 | 2004-08-23 | 2026-07-29 |
| 42 | Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review | 5,320 | 3,338 | 2004-08-24 | 2026-07-30 |
| 51 | Changes in Control of Registrant | 12,227 | 7,008 | 1994-01-04 | 2026-07-31 |
| 52 | Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers | 242,932 | 11,364 | 1994-02-24 | 2026-07-31 |
| 53 | Amendments to Articles of Incorporation or Bylaws; and/or Change in Fiscal Year | 47,445 | 10,527 | 1994-01-11 | 2026-07-31 |
| 54 | Temporary Suspension of Trading Under Registrant's Employee Benefit Plans | 1,532 | 866 | 2003-07-28 | 2026-06-16 |
| 55 | Amendments to the Registrant's Code of Ethics; or Waiver of a Provision of the Code of Ethics | 2,407 | 1,807 | 2003-07-30 | 2026-07-30 |
| 56 | Change in Shell Company Status | 800 | 703 | 2005-11-10 | 2026-07-23 |
| 57 | Submission of Matters to a Vote of Security Holders | 80,239 | 8,849 | 2010-03-01 | 2026-07-31 |
| 58 | Shareholder Nominations Pursuant to Exchange Act Rule 14a-11 | 1,240 | 791 | 2011-12-19 | 2026-07-30 |
| 61 | ABS Informational and Computational Material | **0** | 0 | — | — |
| 62 | Change of Servicer or Trustee | 8 | 7 | 2008-04-03 | 2017-01-11 |
| 63 | Change in Credit Enhancement or Other External Support | 11 | 10 | 2005-07-01 | 2011-11-17 |
| 64 | Failure to Make a Required Distribution | 3 | 3 | 2008-06-20 | 2013-09-12 |
| 65 | Securities Act Updating Disclosure | 12 | 12 | 2006-08-04 | 2013-04-30 |
| 71 | Regulation FD Disclosure | 302,265 | 11,572 | 1996-04-26 | 2026-07-31 |
| 81 | Other Events | 844,250 | 17,542 | 1994-01-04 | 2026-07-31 |
| 91 | Financial Statements and Exhibits | 1,144,738 | 15,602 | 1994-01-04 | 2026-07-31 |

The legend has 37 codes; **35 occur in the data.** Codes **36** (Rule 12b-25 late-filing notice)
and **61** (ABS material) never appear in 2.5M rows — do not build anything on them. No code
appears in the data that is absent from the legend, so the enum is **closed**.

### Four things about this table that will bite you

1. **Earnings events do not exist before 2004-08-23.** Code 22's first occurrence is exactly
   2004-08-23 — the day the SEC's amended Form 8-K (Release 33-8400) took effect and introduced
   the current item numbering. Ten other codes start on precisely that date, and code 40 stops on
   2004-08-20 and is replaced by code 41 with an identical title. **Any earnings-conditioned study
   is structurally limited to 2004-08-23 onward**, which is roughly the back half of the panel.
   This is a hard boundary in the data, not a coverage gap that better cleaning could fix.
2. **Coverage is partial even after 2004.** Code 22 runs 1.65 events per ticker per year against
   the ~4 a full quarterly calendar implies. `bulk.py` already warns about this; the population
   figure confirms it. **Treat a missing earnings date as unknown, never as "no announcement".**
3. **Codes 34 and 35 are not 8-K items at all** — they are Schedule 13G and 13D filings. That is
   why they predate 2004 and why 34 is the third most common code overall. Sharadar's own table
   description ("material corporate events as reported to the SEC via form 8-K") is therefore
   incomplete. Both stop early (2024-12-17 and 2025-05-16) — they appear to have been
   discontinued, so do not use them near the end of the sample.
4. **`date` is the FILING date**, per the INDICATORS legend for the EVENTS table (`date` →
   "Filing Date"), not the event date. For code 22 those are usually the same day, but they are
   not the same field.

---

## 3. ACTIONS — the complete `action` enum (audit C5)

19 values in the legend, **19 observed in 671,781 rows — an exact match, so the enum is closed.**

| action | meaning | rows | first | last | `value` populated |
|---|---|---:|---|---|---:|
| `dividend` | Cash Dividend | 549,076 | 1997-12-31 | 2026-07-31 | 100.0% |
| `listed` | Newly Listed | 23,296 | 1997-12-31 | 2026-07-29 | 0.0% |
| `delisted` | Delisted | 19,208 | 1997-12-31 | 2026-07-29 | 63.8% |
| `tickerchangeto` | Ticker Change To | 13,435 | 1998-01-02 | 2026-07-29 | 0.0% |
| `tickerchangefrom` | Ticker Change From | 13,435 | 1998-01-02 | 2026-07-29 | 0.0% |
| `split` | Stock Split or Stock Dividend | 12,907 | 1997-12-31 | 2026-07-31 | 100.0% |
| `relation` | Relation | 8,608 | 1997-12-31 | 2026-07-31 | 0.0% |
| `initiated` | Coverage Initiated | 8,409 | 1997-12-31 | 1997-12-31 | 0.0% |
| `acquisitionof` | Acquisition Of | 8,248 | 1998-01-07 | 2026-07-24 | 99.9% |
| `acquisitionby` | Acquisition By | 8,248 | 1998-01-07 | 2026-07-24 | 99.9% |
| `bankruptcyliquidation` | Bankruptcy and/or Liquidation | 3,347 | 1998-01-06 | 2026-07-07 | 99.9% |
| `regulatorydelisting` | Regulatory Delisting | 884 | 1997-12-31 | 2026-07-27 | 99.2% |
| `spinoff` | Spinoff Ratio | 565 | 1998-01-02 | 2026-07-07 | 100.0% |
| `spunofffrom` | Spunoff From | 565 | 1998-01-02 | 2026-07-07 | 100.0% |
| `spinoffdividend` | Spinoff Dividend | 521 | 1997-12-31 | 2026-07-07 | 100.0% |
| `adrratiosplit` | ADR Ratio Split | 385 | 2000-03-21 | 2026-07-14 | 100.0% |
| `voluntarydelisting` | Voluntary Delisting | 376 | 1998-03-16 | 2026-07-01 | 98.9% |
| `mergerto` | Merger To | 134 | 1998-06-26 | 2026-03-30 | 100.0% |
| `mergerfrom` | Merger From | 134 | 1998-06-26 | 2026-03-30 | 100.0% |

### Gotchas

- **`contraticker` and `contraname` hold the literal string `"N/A"`, not an empty field**, when
  there is no counterparty. `if row["contraticker"]:` is TRUE for every one of the 549,076
  dividend rows. Test `not in ("", "N/A")`.
- **Delisting is spread across three actions.** `delisted` (19,208) is the general one, but
  `regulatorydelisting` (884) and `voluntarydelisting` (376) are separate values. A survivorship
  mask that only matches `delisted` misses 1,260 events. `bankruptcyliquidation` is separate again.
- **Every `initiated` row is dated 1997-12-31** — it is the dataset's start-of-coverage marker,
  not a real corporate action. Exclude it from any event study.
- **Pair rows are duplicated by design**: `tickerchangeto`/`tickerchangefrom`,
  `acquisitionof`/`acquisitionby`, `spinoff`/`spunofffrom`, `mergerto`/`mergerfrom` come in
  matched pairs with identical counts. Counting "corporate actions" naively double-counts.

---

## 4. TICKERS.category — the exhaustive value list (audit C5)

**25 distinct values** across 78,881 rows. Previous work only ever enumerated the `SEP` subset
(15 values); this is all of them, with the table each belongs to.

| category | rows | tables it appears in |
|---|---:|---|
| Domestic Common Stock | 40,001 | SEP, SF1, SF2 |
| Institutional Investor | 13,148 | SF3B |
| ETF | 7,590 | SFP |
| Domestic Common Stock Primary Class | 6,441 | SEP, SF1, SF2 |
| ADR Common Stock | 4,292 | SEP, SF1, SF2 |
| Domestic Common Stock Secondary Class | 1,312 | SEP, SF2 |
| Domestic Preferred Stock | 1,145 | SEP, SF2 |
| CEF | 1,076 | SFP |
| Domestic Common Stock Warrant | 921 | SEP |
| Canadian Common Stock | 741 | SEP, SF1, SF2 |
| ADR Common Stock Primary Class | 727 | SEP, SF1, SF2 |
| ETD | 494 | SFP |
| ETN | 414 | SFP |
| ADR Common Stock Secondary Class | 159 | SEP |
| ADR Common Stock Warrant | 116 | SEP |
| ADR Preferred Stock | 92 | SEP |
| CEF Preferred | 76 | SFP |
| CEF Warrant | 50 | SFP |
| Canadian Common Stock Primary Class | 30 | SEP, SF1, SF2 |
| UNIT | 24 | SFP |
| ETMF | 18 | SFP |
| IDX | 5 | SFP |
| Canadian Common Stock Secondary Class | 3 | SEP |
| Canadian Common Stock Warrant | 3 | SEP |
| Canadian Preferred Stock | 3 | SEP |

Equity categories live on `SEP`/`SF1`/`SF2` rows; fund categories (`ETF`, `CEF`, `ETD`, `ETN`,
`UNIT`, `ETMF`, `IDX`, and the CEF variants) live only on `SFP` rows; `Institutional Investor`
only on `SF3B`. **Filtering on `category` without also filtering on `table` mixes stocks, funds
and 13F filers.**

**`core/pit_universe.py` currently excludes 9 of the 15 SEP categories** (`verify_sharadar.py`
flags this): Domestic Preferred Stock (1,137), Domestic Common Stock Warrant (921), Canadian
Common Stock (382), ADR Common Stock Warrant (116), ADR Preferred Stock (92), and four tiny
Canadian classes. Excluding preferreds and warrants is correct. **Excluding the 382 Canadian
Common Stock names is a judgement call, not an obvious one** — they are ordinary common equity,
and 316 of them carry SF1 fundamentals. Flagged, not changed.

Currency distribution (78,881 rows): USD 77,864 · CNY 228 · CAD 223 · EUR 166 · BRL 55 · JPY 47 ·
GBP 40 · HKD 31 · AUD 28 · MXN 26 · SGD 20 · ILS 19. The ~1.3% non-USD tail is the population
that the P7 currency bug corrupted.

---

## 5. SF1 units — the 100× question, settled (audit D10)

**SF1 percentage-style fields arrive as FRACTIONS (`0.15` = 15%), never as `15.0`.**
Three independent confirmations:

1. **Authoritative:** `INDICATORS` gives `unittype` for all 112 SF1 columns. `roe`, `roa`, `roic`,
   `ros`, `netmargin`, `grossmargin`, `ebitdamargin`, `divyield`, `payoutratio` are all
   **`ratio`**. There is no `percent` unittype anywhere in the table — the only unittypes used are
   `currency` (63), `ratio` (21), `USD` (9), `currency/share` (5), `date` (5), `USD/share` (4),
   `units` (3), `text` (2).
2. **Population:** across 200,000 ART rows, `roe` has median **0.0730** and p90 **0.3050**; ARY
   median **0.0650**, p90 **0.3070**. A percentage convention would put the median near 7, not 0.07.
3. **Live spot-check:** AAPL FY2025 ARY returned `roe 1.64`, `roa 0.328`, `netmargin 0.269`,
   `grossmargin 0.469`.

**No 100× correction is needed anywhere.** Note that ~3.5% of `roe` values exceed |3| legitimately
(Apple's own ROE is 1.64 because buybacks have shrunk book equity) — a magnitude filter that
rejects `|roe| > 3` as "must be a percentage" would throw away real data.

### The units trap that IS live: SF1 vs DAILY differ by 1e6

| column | SF1 unittype | DAILY unittype |
|---|---|---|
| `marketcap` | **USD** | **USD millions** |
| `ev` | **USD** | **USD millions** |

Verified on AAPL: SF1 ARQ 2015-06-27 gives `marketcap = 714,094,848,840` (raw USD) while DAILY
2015-06-30 gives `marketcap = 722,571.4` (millions). **Same concept, same company, same week,
1,000,000× apart.** Any code that reads market cap from both sources and does not rescale is
wrong by six orders of magnitude. The panel takes point-in-time market cap from DAILY, so check
the scaling at the boundary before mixing in an SF1 value.

Also, unchanged and still true — **`fxusd` is a DIVISOR** (`ratio`, "Foreign Currency to USD
Exchange Rate", local units per USD). There is no `netincusd`; the USD net income field is
`netinccmnusd`. The nine `USD` columns are the only pre-converted ones; the 63 `currency` columns
are in the filer's reporting currency.

---

## 6. Restatements: **Sharadar APPENDS a new ARQ row.** (audit D10 — the important one)

Settled at population scale on the freeze, not on a handful of tickers.

> **`ORDER BY datekey DESC LIMIT 1` — "latest datekey per reportperiod" — is silent look-ahead.**
> `pit_fundamental()` takes the EARLIEST datekey. That choice is **required, not merely defensive.**

Across **652,337** distinct ARQ `(ticker, reportperiod)` keys over **17,021** tickers:

| measure | value |
|---|---|
| keys with more than one `datekey` | **23,211 (3.558%)** |
| tickers affected at least once | **9,427 (55.4%)** |
| datekeys per affected key | 2 → 21,113 · 3 → 1,650 · 4 → 299 · 5 → 90 · 6 → 33 · 7 → 14 · 8 → 11 · 9 → 1 |
| days between earliest and latest datekey | median **29**, p90 **86**, max **807** |
| within 30 days / beyond 180 days | 52.2% / 1.0% |

**And the appended row is not cosmetic — the numbers move:**

| field | differs between earliest and latest datekey | median \|Δ\| where it differs | \|Δ\| > 5% |
|---|---|---:|---:|
| `revenue` | 1,680 / 20,636 (8.1%) | 2.38% | 548 |
| `netinc` | 3,114 / 20,624 (15.1%) | **19.93%** | 2,125 |
| `assets` | 2,812 / 23,180 (12.1%) | 1.50% | 1,002 |
| `equity` | 3,248 / 23,174 (14.0%) | 3.85% | 1,518 |
| `eps` | 3,982 / 19,838 (20.1%) | **16.91%** | 2,790 |

Real examples where taking the latest datekey would have imported a number nobody could have
known at the time:

```
ABBNY 2018-12-31  datekeys 2019-02-28 -> 2019-03-28   revenue 7,395,000,000 -> 889,000,000
ABCWQ 2009-06-30  datekeys 2009-08-10 -> 2009-10-20   revenue 25,849,000 -> -25,925,000
                                                      netinc -11,753,000 -> -62,904,000
AAIIQ 2007-03-31  datekeys 2007-05-21 -> 2007-08-06   revenue 19,583,000 -> 50,810,000
```

### What the defensive choice actually costs — the question nobody had answered

**Almost nothing, and it is the right trade.** Taking the earliest datekey costs *no* timeliness:
the earliest datekey IS the first publication, which is exactly what was knowable. What you give
up is only ever the *corrected* figure, which by definition did not exist yet at the rebalance.

Two things temper the headline 3.6%:

- **About half of the duplicates are filing mechanics, not restatements.** 52.2% of affected keys
  have their second datekey within 30 days, and some are 1–2 days apart (`AAIC` 1998-08-13 →
  08-14 changes revenue by $1,000). Those are amended or re-transmitted filings.
- **The genuine late restatements are the 1.0% beyond 180 days** — and those are precisely the
  ones where using the latest datekey would be most damaging, because the correction lands a year
  after the rebalance that used it.

**Bottom line: 3.6% of the panel's cells could have been contaminated, ~1 in 6 of those by ~17–20%
on earnings-related fields. The earliest-datekey rule prevents this at zero cost. Do not
"optimise" it away.**

One caveat, stated rather than buried: a single snapshot can prove Sharadar **appends**, but it
cannot prove Sharadar never *also* rewrites a row in place — an in-place edit is invisible in one
download. Detecting that would need two snapshots of the same table taken months apart. The
freeze is now snapshot #1; the live export in `data/backtest` is derived rather than raw, so it
does not serve. If it matters later, this is the test.

---

## 7. Dimension coverage — why five factors were silently empty (audit D10, confirms P5)

Confirmed at population scale on all 3,203,836 SF1 rows. **Sharadar populates its ratio and
averaged columns ONLY in the T (trailing-twelve-month) and Y (annual) dimensions:**

| dimension | rows | roe | roa | roic | assetturnover | netmargin |
|---|---:|---:|---:|---:|---:|---:|
| MRT | 734,630 | 85.1% | 85.1% | 85.1% | 85.1% | 88.9% |
| **MRQ** | 715,611 | **0.0%** | **0.0%** | **0.0%** | **0.0%** | 91.4% |
| ART | 685,084 | 89.4% | 89.4% | 89.4% | 89.4% | 88.1% |
| **ARQ** | 678,341 | **0.0%** | **0.0%** | **0.0%** | **0.0%** | 91.0% |
| MRY | 203,421 | 86.1% | 86.1% | 86.1% | 86.1% | 94.7% |
| ARY | 186,749 | 90.7% | 90.7% | 90.7% | 90.7% | 94.7% |

The project's export is **ARQ-only**, which is why `roe` / `roic` / `assetturnover` were non-null
in 0 of 197,265 rows and `quality` silently averaged 8 of its 10 inputs for years. **This is a
property of Sharadar, not a bug in the export or a broken pull** — the columns are genuinely
empty in every quarterly dimension. Deriving them from line items (as `_sf1_to_metrics` now does)
is the only fix; there is no flag that would make ARQ return them.

`netmargin` is the exception: it IS populated in ARQ (91.0%), because it needs no averaged
denominator.

---

## 8. SEP — columns and adjustment semantics

Exactly **10 columns**, confirmed live: `ticker, date, open, high, low, close, closeadj,
closeunadj, volume, lastupdated`.

**There is NO `dividends` column** — published sources disagree on this; the key settles it.
Dividend amounts live in ACTIONS (`action = 'dividend'`, 549,076 rows).

Per the INDICATORS legend:

- `close` — "Close Price - **Split Adjusted**" (dividends NOT removed)
- `closeadj` — "Close Price - **Adjusted for Splits Dividends and Spinoffs**" → **use for returns**
- `closeunadj` — "Close Price - **Unadjusted**" → **use for point-in-time price screens**
- `open`/`high`/`low` are split-adjusted only; `volume` is "Volume - Split Adjusted"

Verified arithmetically: AAPL 2019-01-04 `close` 37.065, `closeunadj` 148.260 → ratio exactly
4.000, the Aug-2020 4:1 split. `closeadj` 35.178 < `close`, i.e. dividends have been
back-adjusted out of the historical level.

**`closeadj` is BACK-adjusted**, so it is rewritten whenever a new split or dividend lands and is
*not* a point-in-time price level. Using `close` for returns silently omits the entire dividend
yield. The project's existing rule — **SEP is already split-adjusted, so ACTIONS split ratios must
NOT be re-applied** — is consistent with this and should not be "fixed".

---

## 9. Survivorship — the property the subscription was bought for

| table | delisted tickers | retaining a full price range |
|---|---:|---:|
| SEP | 15,628 | **15,628 (100.0%)** |
| SF1 | 12,275 | 12,275 (100.0%) |
| SFP | 3,580 | 3,580 (100.0%) |
| SF2 | 7,104 | 6,602 (92.9%) |

**Every delisted equity retains its price history.** This is intact in the freeze, so the
survivorship-free property survives the lapse.

**API quirk:** `isdelisted` **cannot be used as a filter** — `HTTP 422 QESx08: You cannot use
isdelisted column as a filter`. This is why test 6 of `verify_sharadar.py` fails against a live
key; the script is wrong, not the entitlement. Request the column and filter locally instead.

---

## 10. Bulk-export schema conformance (supports D1 — the $29/mo direct bundle)

**The bulk export's SF1 schema matches Sharadar's own authoritative column list exactly: 112
columns, zero in the export that are missing from `INDICATORS`, zero in `INDICATORS` missing from
the export.** Every column `bulk.py` indexes by name (`investorname`, `securitytype`,
`calendardate`, `value`, `marketcap`, `pe`, `pb`, `ps`, `evebitda`, `eventcodes`, `action`,
`filingdate`, `transactionvalue`, …) is present. The freeze already runs the full backtest with no
API key, which is the practical proof. **Nothing in the loader assumes anything the direct bundle
would not also provide.**

One defect found while checking, reported not fixed (this bot writes docs only):

- **`ebitmargin` does not exist in SF1** — the column is `ebitdamargin` (with a D). It is listed in
  `WRDSProvider._KEEP` (`valuation/edge/data_providers.py:262`) and read at
  `valuation/edge/fundamental_panel.py:353` as the fallback for `op_margin`:
  `(ebit / rev) if (ebit is not None and rev) else _f(sf1, "ebitmargin")`. The primary path
  (`ebit / rev`) is fine, so this is **low severity** — but the fallback can never fire, and it is
  the same class of silent-missing-column bug that has now bitten this project five times.

---

## 11. API quirks worth keeping

- **Auth via the `x-api-token` header**, not an `api_key` query parameter — keeps the key out of
  proxy and server logs.
- **A page caps at 10,000 rows** and returns `meta.next_cursor_id`. Ignoring the cursor yields
  exactly 10,000 rows *and no error*, which is indistinguishable from a small result set. Never
  let a count of exactly 10000 pass unexamined. **Filters must be RESENT with the cursor.**
- **Results are unsorted by design.** Sort locally.
- `.gte`/`.lte` are inclusive, `.gt`/`.lt` exclusive; a bare `date=2024-01-02` is exact equality.
- **Incremental sync must key on `lastupdated`, not `date`** — Sharadar restates, and `date` never
  moves when a row is rewritten.
- **A missing or unentitled key returns SAMPLE DATA, not an error.** Always verify against a known
  checkpoint (AAPL 2015-06-30 PIT market cap = $722,571.4M) before trusting a pull.
