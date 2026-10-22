# EODHD_CENSUS.md — what the EODHD Fundamentals feed actually carries — 2026-10-22

**Measured 2026-10-22 by the r1 lane. ZERO TRIALS** — entitlement and coverage facts, no hypothesis,
no bar, no forward return, nothing adopted. Every line below is a **real request**; a product named
on the pricing page is not evidence it answers, and this census found three places where it does not.

**Reproduce:** `python -m scripts.eodhd_census --probe`, `python -m scripts.eodhd_coverage
--sample 150`, `python -m scripts.eodhd_restated --names 60`. Raw payload stays on
`D:\eodhd`; the artifacts under `data/free_analysis/` carry derived statistics only.

> **THE LICENCE FENCE, FIRST.** The EODHD **personal** plan permits storing and analysing the data
> for private, non-commercial use and **forbids displaying, redistributing or granting access to it
> "in its original or repackaged form"** (`DECISIONS.md` 2026-10-22). This repo is **public and
> MIT**. So **nothing from EODHD reaches valquo.co, the public repo, `data_export/` or any page**;
> raw rows live only under `D:\eodhd`; **this file and every committed artifact carry rates, counts,
> spans and field names — never a per-name financial value**, which a test asserts. Wiring EODHD
> into the live site would need a **commercial** licence and is Don's decision, not part of this
> item.

**Budget:** `/api/user` reports **100,000 calls a day** (plus an `extraLimit` of 500) and is read
rather than assumed. **The entire census cost 3,023 calls** — 3.0% of one day — because fundamentals
cost 10 calls each and everything else costs 1.

---

## 1. THE ENDPOINT CENSUS — 11 ANSWER, 2 ARE FORBIDDEN, 3 ANSWER AND DO NOT MEAN WHAT THEY SAY

| endpoint | status | shape | what it unlocks |
|---|---|---|---|
| `user` | **200** | 12 fields | the plan and the day's consumption |
| `fundamentals/{T}.US` | **200** | 13 top-level blocks | statements, `General`, `Earnings`, `Holders`, `outstandingShares` |
| `exchange-symbol-list/US` | **200** | **50,962** symbols | the live US ticker list (Common Stock 17,783; FUND 20,801; ETF 5,948) |
| `calendar/earnings` | **200** | 9 fields/row | **FORWARD earnings dates — see §5** |
| `calendar/ipos` | **200** | 12 fields/row | IPO calendar |
| `calendar/splits` | **200** | 5 fields/row | splits calendar |
| `sentiments` | **200** | per-symbol series | news sentiment, **back to 2016-02-19** |
| `news` | **200** | per-article + `sentiment` | headlines with a sentiment block |
| `macro-indicator/USA` | **200** | 65 rows | macro series incl. `real_interest_rate` (61 rows) |
| `historical-market-cap/{T}.US` | **200** | **262 weekly points** | **5 years only — see §4** |
| `insider-transactions` | **200** | 14 fields/row | **and it does not filter — see §3** |
| **`bond-fundamentals/{ISIN}`** | **403 FORBIDDEN** | — | **the corporate-credit feed is NOT on this plan** |
| `eod/{T}.US` | **403 FORBIDDEN** | — | end-of-day prices, as the pricing page says |
| `bonds-fundamentals`, `credit-risk/US`, `sovereign-risk/USA` | **404** | — | these names do not exist |

**A PREMISE CORRECTION, AND IT KILLS ONE OF THE BRIEF'S OWN QUESTIONS.** The pricing page lists
*"credit and sovereign risk, including US corporate"* as included. **Measured, `bond-fundamentals`
returns 403 Forbidden on two different ISINs — one corporate, one Treasury — and the three
alternative names return 404.** So **corporate credit history is not available on this plan**, and
the brief's question *"is it a live input for `tracelead`?"* is answered **no**. Following `W-14`'s
rule, a 403 under one name is weaker evidence than a 404 under several; here both were probed, so
the finding is **FORBIDDEN by entitlement** rather than absent by name.

---

## 2. POINT-IN-TIME OR RESTATED? — **REAL FILING DATES, AND THE PLACEHOLDERS ARE ALL IN THE OLD HISTORY**

This is the question that decides whether a second-vendor replication is possible, so it was
measured two independent ways.

### (a) `filing_date` is present on every period, and ~21% of them are placeholders

`filing_date` is **100.0% non-null** on all three statements, yearly and quarterly. But **a filing
date equal to the period-end date is impossible for a real filing**, so those are placeholders.
Across 8 large names and 1,314 quarterly periods:

| period-end decade | real filing dates | placeholders | **real share** |
|---|---|---|---|
| 1980s | 0 | 143 | **0.0000** |
| 1990s | 194 | 126 | 0.6062 |
| **2000s** | 319 | 1 | **0.9969** |
| **2010s** | 316 | 4 | **0.9875** |
| **2020s** | 211 | 0 | **1.0000** |

**THE PLACEHOLDERS ARE A PRE-EDGAR ARTEFACT, NOT A VENDOR HABIT — AND THE EVIDENCE IS THE DATE
ITSELF.** The **first period carrying a real filing date is 1993-12-31 for seven of the eight names
probed** (WMT 1995-01-31), which is when EDGAR electronic filing began. A vendor inventing dates
would not place its boundary there.

**AND THE LOOK-AHEAD CHECK PASSES OUTRIGHT: ZERO negative lags over 1,040 real periods.** No filing
date precedes its own period end. Median lag **29–43 days** by name, which is the right magnitude
for a 10-Q.

### (b) Against Sharadar's as-reported quarterly: the same object on ~89% of pairs

`data/backtest/fundamentals.csv` is Sharadar's **ARQ** dimension — as-first-reported — so it is the
control the project already owns. **15,429 `(ticker, period, field)` pairs over 60 $10B-tier names,
agreement at a 0.5% tolerance:**

| field | pairs | **agreement** | median relative difference |
|---|---|---|---|
| `totalAssets` | 3,938 | **0.9817** | **0.0** |
| `totalStockholderEquity` | 3,924 | **0.9353** | **0.0** |
| `netIncome` | 3,790 | **0.9166** | **0.0** |
| `totalRevenue` | 3,777 | **0.7180** | **0.0** |
| **overall** | **15,429** | **0.8894** | **0.0** |

**THE MEDIAN RELATIVE DIFFERENCE IS EXACTLY ZERO ON EVERY FIELD**, so the typical pair is
bit-identical and the two vendors are substantially the **same object** — which is what a
replication needs. **Revenue is the weak field at 0.7180**, and that is where restatements and
discontinued-operations reclassifications land, so it is the field a replication must watch.

> **HOW TO READ IT, STATED BECAUSE IT IS EASY TO OVERCLAIM:** agreement does **not** prove either
> vendor carries the as-reported figure — both could carry the same restatement. It proves they are
> the same object. **Disagreement is the informative direction**, and 11.06% of pairs disagree.

**CONSEQUENCE: step 4 of the brief is LIVE.** Filing dates are real at **98.75% in the 2010s** and
**99.69% in the 2000s**, so a genuine point-in-time construction is buildable on EODHD for both the
build era and the **1999–2008 out-of-sample era** that Don's 2026-10-04 ruling names. The brief's
own stopping condition — *"if filing dates are not real, say so and stop at the census"* — **does
not fire.**

---

## 3. THE INSIDER FEED — **IT ANSWERS, AND IT CANNOT BE ASKED ABOUT A COMPANY**

This is the most dangerous finding in the census, because every failure mode here is **silent**.

| probe | result |
|---|---|
| `code=AAPL.US` | **200 with ZERO rows** |
| `symbol=AAPL.US` | 200, rows |
| `symbol=MSFT.US` | 200, **the identical rows** |
| no symbol at all | 200, **the identical rows** |
| `offset=50` | **the identical rows** — page 1 and the offset page overlap **50 of 50** |
| `from`/`to` | **honoured** (a 2024Q1 window returns 2024 dates) |

**SO `symbol=` IS ACCEPTED AND IGNORED.** `AAPL.US`, `MSFT.US` and no symbol at all return the same
200 rows — same 118 distinct tickers, same top counts, same date span. **A study that filtered by
symbol would be reading market-wide rows as one company's, and nothing would raise.** And `code=`,
the name the documentation shape suggests, returns an **empty 200** — the wrong-parameter failure
that spent the scout's whole WRDS session on `mgrno` three days ago, in a second vendor.

**AND THREE FIELDS ARE PRESENT AND EMPTY** — the COVERAGE RULE's own trap, measured on 500 rows:

| field | non-null |
|---|---|
| `ownerName`, `ownerTitle`, `transactionCode`, `transactionDate`, `reportDate` | **1.0000** |
| `transactionAmount` | 0.9980 |
| **`ownerCik`** | **0.0000** |
| **`ownerRelationship`** | **0.0000** |
| **`postTransactionAmount`** | **0.0000** |

> **THIS SETTLES A QUESTION F-23 HAS BEEN BLOCKED ON, IN THE NEGATIVE.** `F23-SECID` needed a
> **distinct insider ID** because the licensed SF2 file carries names only. EODHD's schema has
> `ownerCik` — and it is **empty on every row measured**. **So EODHD is not a solution to the
> insider-identity problem.** The SEC's own free Form 4 feed, which this project already uses and
> where `RPTOWNERCIK` is 100% populated, remains the only route.

**What the feed IS good for:** market-wide insider windows with `transactionCode`, `transactionDate`
and `reportDate`, harvestable by walking narrow date ranges. **Each window is capped by `limit` and
cannot be paged**, so a harvest must shrink its windows until the returned count is below the cap —
otherwise rows are lost silently.

---

## 4. HISTORICAL MARKET CAP — **FIVE YEARS, WEEKLY; SHARADAR DAILY GOES BACK TO 1998**

| | EODHD | the project's panel (Sharadar DAILY) |
|---|---|---|
| points | **262** | daily |
| span | **2021-09-03 → 2026-09-04** | 1998 onward (panel dates 2009-03-27 → 2026-04-09) |
| spacing | **~7.0 days** | 1 day |

**The `from`/`to` filter silently returns an EMPTY DICT for a window before 2021** — a 2015 request
answers 200 with nothing, which is the same empty-200 trap as §3. The payload is also a **dict keyed
`"0".."261"`, not a list**, so a consumer expecting a list gets nothing and raises nothing.

**Agreement on the overlap, 409 paired observations over 33 tier names and 21 panel dates:**

| | |
|---|---|
| **Spearman rank correlation** | **0.9973** |
| median \|relative difference\| | **1.98%** |
| p90 \|relative difference\| | 9.22% |
| within 1% | 30.1% |
| within 5% | 75.8% |

**THE RANKING AGREES ALMOST PERFECTLY AND THE LEVELS DO NOT**, and part of that 1.98% is **not a
vendor disagreement at all**: a weekly series matched to a quarterly panel date is up to six days
stale by construction. **So for a cross-sectional use — the `size` theme, or $10B-tier membership —
EODHD's market cap is interchangeable in RANK; for a level, it is not.** And **only 19 of the
panel's 69 dates fall inside its five-year window**, so it **cannot support a historical tier
definition at all.** A replication must take market cap from the existing Sharadar-derived panel,
not from EODHD.

---

## 5. THE EARNINGS CALENDAR — **IT CARRIES FORWARD DATES, AND THAT UNBLOCKS THE OPTIONS LANE**

| window | US rows | span |
|---|---|---|
| 2026-10-23 → 2026-11-30 | **4,503** | all **after** today |
| 2026-10-23 → 2027-01-31 | 4,783 | → 2027-01-28 |
| 2026-10-23 → 2027-06-30 | 4,896 | → 2027-05-19 |
| 2026-10-23 → 2027-12-31 | **4,898** | **→ 2027-11-19** |

Fields: `code`, `report_date`, `date`, `before_after_market`, `estimate`, `actual`, `difference`,
`percent`, `currency`. **`before_after_market` is the field an options entry rule needs** and the
project's existing Yahoo route does not reliably carry.

**And the history is deep too:** 15,489 US rows in 2015Q1, 5,719 in 2009Q1, **2,668 in 2000Q1** — so
the calendar supports both a forward entry rule and a historical event spine.

> **HAND-OFF TO THE OPTIONS LANE (reported, not done here).** `DECISIONS.md` 2026-10-16 records
> **F-4 and F-10 as not re-declared because "the event spine holds no forward dates"**, and
> 2026-10-17 records Yahoo giving future dates for **91% of 487 optionable names with drift of up to
> about a week**. **EODHD carries 4,898 US forward rows reaching 13 months out, with a
> before/after-market flag.** Whether that clears F-4's own buffer rule is the options lane's call,
> **and the licence fence travels with it: the forward calendar may inform a PAPER book's entry
> rule, and may not be displayed or redistributed.**

---

## 6. COVERAGE OF THE CORRECTED UNIVERSE — **TWO FIGURES, AND THE WEAKER ONE IS LABELLED**

`W-28` measured an **undated** identifier join assigning one company's dates to a **different
company on 54 names**, and `TRACELEAD` (three days ago) found a published coverage ratio dividing a
numerator from one population by a denominator from another. So both figures are reported, with the
usable one named.

### (a) The undated ticker match — an UPPER BOUND, and not a coverage figure

| | matched | of | rate |
|---|---|---|---|
| corrected universe | 5,175 | 9,645 | **0.5365** |
| **$10B tier** | 1,101 | 1,361 | **0.8090** |

**A ticker string matching proves nothing about whether the data behind it belongs to the company
the panel means on that date.** It is also biased **downward** for a different reason: the symbol
list holds **live** names, so **delisted companies are missing from it while their fundamentals
still answer** — see (b), where 98% answered against 87% listed. **Two biases in opposite
directions, which is why this figure is quoted as neither.**

### (b) The dated check — the figure a study may use

150 `(date, ticker)` tier cells, seed 20261022. A cell counts only if the ticker sits inside a
`crsp.stocknames` **name interval covering that date** *and* EODHD carries a statement **filed
before** it:

| leg | rate |
|---|---|
| EODHD answered `fundamentals` | **0.9800** |
| …carrying a period **filed before** the cell date | **0.9400** |
| ticker inside a CRSP dated name interval | **0.7600** |
| **BOTH dated legs — the usable figure** | **0.7400** |

**THE BINDING LEG IS THE PROJECT'S OWN IDENTIFIER SPINE, NOT EODHD.** EODHD answers 94–98%; the
CRSP name-interval check is 76%, and the joint figure is 74%. **So 0.7400 is a statement about this
project's join, and a better spine would raise it** — which matters, because reading 0.74 as
"EODHD's coverage" would understate the vendor by about twenty points.

**Identifiers, measured on the 147 answering cells:**

| identifier | present |
|---|---|
| **`CIK`** | **0.9932** |
| `CUSIP` | 0.1020 |
| `ISIN` | 0.0816 |

**CIK is the join key.** A CUSIP or ISIN route is not available — they are null on about 90% of
names, including AAPL.

---

## 7. HOW FAR BACK, PER FIELD

Measured on AAPL; the field counts are schema facts and hold for every US name probed.

| block | periods | span | fields |
|---|---|---|---|
| `Balance_Sheet` yearly | **41** | **1985-09-30 → 2025-09-30** | 64 |
| `Balance_Sheet` quarterly | **164** | 1985-09-30 → 2026-06-30 | 64 |
| `Income_Statement` yearly | 41 | 1985-09-30 → 2025-09-30 | 34 |
| `Income_Statement` quarterly | 164 | 1985-09-30 → 2026-06-30 | 34 |
| `Cash_Flow` yearly | **37** | **1989-09-30** → 2025-09-30 | 32 |
| `Cash_Flow` quarterly | 147 | 1989-12-31 → 2026-06-30 | 32 |
| `Earnings.History` | 132 | 1993-12-31 → 2026-09-30 | — |
| news sentiment | — | **2016-02-19** → present | 3 |
| historical market cap | 262 | **2021-09-03** → 2026-09-04 | 2 |

**Cash flow starts four years later than the balance sheet**, so any construction using capex,
operating cash flow or buybacks loses 1985–1988.

---

## 8. DELISTED COMPANIES — **PRESENT, AND NOT UNIFORMLY**

`General.IsDelisted` is a real flag, and **10.67% of sampled tier cells carry it true**, so dead
companies are represented rather than silently dropped.

| probe | `IsDelisted` | yearly income periods | span |
|---|---|---|---|
| SVB Financial | True | **38** | 1985-12-31 → 2022-12-31 |
| Frontier Communications | True | 26 | 1994-12-31 → 2019-12-31 |
| Sears Holdings | True | 19 | 2000-01-31 → 2018-01-31 |
| Bed Bath & Beyond | True | 4 | 2020-02-29 → 2023-02-28 |
| **Enron** | True | **0** | **financials EMPTY** |
| **Lehman Brothers** | True | **0** | **financials EMPTY** |

**THE TWO EMPTY ONES ARE BOTH PRE-2009 FAILURES, AND THE PATTERN MATTERS FOR SURVIVORSHIP.** The
`General` block exists for Enron and Lehman — so the ticker is known — and the statements are empty.
**A replication on the 1999–2008 era must measure how widespread that is before trusting it**, since
the names missing from that era are exactly the ones that died in it. **Not measured here; named as
the first thing step 4 must check.**

---

## 9. WHAT THIS CENSUS DOES NOT SAY

It does **not** claim EODHD reproduces the project's book — that is step 3 and it has not run. It
does **not** adopt anything, change any construction, or touch the Index or the 2026-10-22
rebalance. It does **not** establish that the corporate-credit product is unavailable **at EODHD** —
only that it is **403 on this plan under the documented name**, which `W-14`'s rule makes a
statement about the entitlement rather than the product. It does **not** measure the 1999–2008
delisted-coverage hole (§8). And it does **not** license any EODHD figure on a public surface: the
personal plan forbids it, and the Index is published.

**HAND-OFFS, reported not done:**

- **options lane** — the forward earnings calendar (§5), with the licence fence attached;
- **scout** — the three feeds worth a register are the **forward calendar**, the **news sentiment
  back to 2016** (untested here as a signal), and a **second-vendor replication of the composite**
  (§2 shows it is buildable). The **insider feed is NOT worth a register** (§3) and the
  **credit feed is not available** (§1).
