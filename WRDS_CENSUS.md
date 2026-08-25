# WRDS CENSUS — what THIS account can actually reach

**Measured 2026-08-24. Zero trials — facts about what exists, not a research result.**
Account: the `WRDS_USERNAME` in `.env` (never printed; credentials are materialised into libpq's
pgpass file programmatically and nothing in this lane returns a password).

Reproduce: `python -m scripts.wrds_census` → `WRDS_CENSUS.md` + `D:\wrds\WRDS_CENSUS.json`.
Raw payload lives under **`D:\wrds`** (sibling of `D:\thetadata`) and **is never committed,
never mirrored into the repo, and never rendered on a public surface.** What leaves this lane is
derived statistics: row counts, spans, byte sizes, sha256.

---

> **PHASE 2, 2026-08-24 — TWO PROBES CHANGED WHAT THIS ACCOUNT IS WORTH.** The headline below
> stands: OptionMetrics is not entitled. But Compustat carries **`co_hgic`, a genuinely DATED
> GICS history** (45,836 rows, `indfrom` 1999-06-30 →, **30.2% of firms reclassified**, **94.9%
> of our panel**) — which **reopens `S25`**, the oldest permanently-closed row in the ledger, and
> makes the valuation path's one look-ahead input repairable. And `crsp_a_stock.dsf` gives a
> **$ADV at 89.7% of the universe against the current path's 19.8%**, unparking `B13` and `S7`'s
> fourth interaction on 64 of 69 dates. Both are written up in full at the end of this file,
> with their taxonomy and date-scoping caveats attached.
>
> **RE-PROBE, SAME DAY, AND IT CORRECTS THIS CENSUS RATHER THAN EXTENDING IT.** Don supplied the
> official WRDS subscription list. **This census's Thomson verdict was wrong** — not the
> measurement, which reproduces, but the conclusion drawn from it: WRDS's own 13F
> (**103,984,958 rows, 1987→2025**) and insider (**10,083,927 Form 4 rows**) products are
> ENTITLED under `wrdssec_*`, and this file said the data was unobtainable. **And the repair
> everyone expected from that does NOT happen: 13F buys the panel exactly ONE extra rebalance
> date, because the table steps from 71 filing managers in 2012 to 3,457 in 2013.** Full
> corrections section at the end of this file; read it before quoting the tables above.

## THE HEADLINE: THE BIGGEST ITEM ON THE PULL PLAN IS NOT AVAILABLE

**OptionMetrics IvyDB — priority (a), described in the brief as "the single biggest upgrade
available" — is NOT ENTITLED on this account.** It exists in the catalogue only as the WRDS
*sample*:

| what we hoped for | what is actually there |
|---|---|
| `optionm` / `optionm_all` — IvyDB back to 1996 | **absent from this account's catalogue** |
| standardised surfaces, greeks, 1996→present | `optionmsamp_us` — **12 tables, year-suffixed 2014** |
| | `vsurfd2014`, `opprcd2014`, `stdopd2014`, `hvold2014` |
| | span **2014-03-03 → 2014-03-14 — TEN TRADING DAYS** |
| | `vsurfd2014` holds **2,600 rows**; `opprcd2014` **36,786** |

**The table names are the proof.** A production IvyDB library is not suffixed with a single
year, and a surface file covering 1996–2026 does not contain 2,600 rows. This is a demonstration
extract.

**Nothing was pulled from it**, and that is the correct outcome rather than a shortfall: ten days
of 2014 cannot support any question our own 2016+ ThetaData cache cannot already answer better.

### What entitlement WOULD have re-opened — stated because it is the case for buying it

Recorded so the value is legible if Don ever prices the subscription, and so nobody re-derives
it. **All of this remains CLOSED, not deferred-with-a-plan:**

* **A pre-2016 options history at all.** Our chain store starts 2016 and the ThetaData Pro window
  closed 2026-09-01. IvyDB reaches 1996, which is the only route to the 2000-02 and 2008 regimes —
  the two the options book has never seen. `B-13`'s alert-density regime register and every
  "does this survive a crisis" question are gated on exactly that.
* **Standardised surfaces.** `stdopd` gives fixed 30/60/91-day constant-maturity points, which is
  what makes an IV level comparable across names and dates without re-fitting a smile per
  cross-section. `O6`'s smile machinery exists because we do not have this.
* **Vendor greeks and IV on one methodology**, removing the `blackscholes.py`-vs-vendor
  reconciliation that `O2` closed by choosing an implementation.
* **`I-1`'s RND instrument** would gain a 20-year backdrop instead of a 10-year one.

**It does not unblock the tenor axis** — that was Tier E's job and it is already banked.

---

## ENTITLEMENT, MEASURED PER TABLE

A library appearing in `list_libraries()` is **not** evidence of entitlement — the catalogue is
broader than the grant, and **221 libraries are visible** to this account. Every target below was
probed with a real `SELECT`. Five states, and the distinctions matter: `DENIED` means the table
exists and we may not read it; `ABSENT` means it is not there under that name; `EMPTY` means we
read it and it holds nothing. A plan that confuses them wastes a window.

| priority | product | status | span | rows |
|---|---|---|---|---|
| **b** | `ibes.det_epsus` — detail estimates | **ENTITLED** | 1980-01-28 → 2026-05-14 | **34,540,574** |
| **b** | `ibes.detu_epsus` — detail, unadjusted | **ENTITLED** | 1980-01-28 → 2026-05-14 | 34,523,713 |
| **b** | `ibes.statsum_epsus` — summary | **ENTITLED** | 1976-01-15 → 2026-05-14 | 15,029,492 |
| **b** | `ibes.actu_epsus` — actuals | **ENTITLED** | 1976-01-15 → 2026-05-14 | 1,323,271 |
| **b** | `ibes.id` — identifier bridge | **ENTITLED** | — | 308,801 |
| b | `ibes.det_guidance` | **DENIED** | — | — |
| **c** | `crsp_a_stock.dsedelist` — delisting returns | **ENTITLED** | 1926-02-24 → 2024-12-31 | **38,872** |
| **c** | `crsp_a_stock.msedelist` | **ENTITLED** | 1926-02-24 → 2024-12-31 | 38,843 |
| **c** | `crsp_a_stock.dsenames` — name history | **ENTITLED** | — | 117,859 |
| c | `crsp_a_stock.dsf` — daily stock file | **ENTITLED** | 1925-12-31 → 2024-12-31 | (not counted) |
| **d** | `comp.co_ifndq` — point-in-time quarterly | **ENTITLED** | 1961-03-31 → 2026-07-31 | **2,114,571** |
| d | `comp.fundq` — quarterly fundamentals | **ENTITLED** | 1961-03-31 → 2026-07-31 | 2,134,745 |
| **e** | `tfn.s34`, `s34type1`, `s34type3` — 13F | **DENIED** — but see RE-PROBE | — | — |
| **e** | `tfn.table1`, `table2` — insiders | **DENIED** — but see RE-PROBE | — | — |
| **e** | `tfn.form144`, `rule10b5` | **DENIED** — but see RE-PROBE | — | — |
| **f** | US short-interest history | **ABSENT** | — | — |
| f | `wrds_shortvolume_samp` (sample) | ENTITLED | — | 15,883 |
| f | `wrdsapps_eushort` (European) | listed | — | — |
| **a** | OptionMetrics IvyDB | **ABSENT** | — | — |
| a | `optionmsamp_us` (sample) | ENTITLED | 2014-03-03 → 2014-03-14 | 2,600 / 36,786 |
| **g** | TAQ full | **ABSENT** | — | — |
| g | `taqsamp` / `taqmsamp` (samples) | listed | 2008-01-07..11, 2009-02-13, 2021-10-04..05 | — |

**CRSP ends 2024-12-31.** Not a defect — it is the vintage this account's CRSP is cut at — but it
means CRSP cannot cross-check anything in 2025 or 2026, which is exactly the window the forward
paper track lives in.

### Three products the brief assumed, that do not exist here

* **~~(e) Thomson insider + 13F — DENIED on all seven tables probed.~~ WRONG, AND CORRECTED IN
  THE RE-PROBE SECTION AT THE END OF THIS FILE (2026-08-24).** The denial is real and reproduces
  on eight fresh connections — but `tfn` is a legacy shell, and WRDS's own SEC-derived equivalents
  are **ENTITLED**: `wrdssec_all.wrds_13f_holdings` (103,984,958 rows, 1987→2025) and
  `wrdssec_insiders.table1` (10,083,927 Form 4 transactions). **The sentence "the intra-quarter
  filing detail is not obtainable on this account" was an inference from a denied table name, not
  a measurement, and it was false.** Read the RE-PROBE before quoting anything in this section.
* **(f) Short interest pre-2018 — ABSENT.** The only US short object is a *sample*
  (`wrds_shortvolume_samp`, 15,883 rows), and that is short VOLUME rather than short INTEREST —
  a different measurement. The S18 cache cannot be extended backward from here.
* **(g) TAQ — the brief's instruction was "flag size only, do not bulk-pull (terabytes)". THE
  PREMISE IS VOID: there is nothing terabyte-scale to avoid.** Only `taqsamp`/`taqmsamp` are
  present, containing a handful of named days (2008-01-07..11, 2009-02-13, 2021-10-04..05). The
  sampling recipe the brief asked for is moot, and the day-trading sibling project should be told
  that this account is not a TAQ source — before it plans around one.

---

## WHAT WAS PULLED, AND HOW IT WAS SIZED

Sizes are **measured on a real chunk and scaled**, never assumed. The chain harvest scored two
projections — a 3-name sample missed by **+339%**, a 393-pair measurement landed within **7.4%** —
and the method transferred here: pull one year, write it exactly as the real pull writes it, scale
from observed bytes.

**Measured on `ibes.det_epsus` year 2015:** 1,413,647 rows · fetch **108.2 s** · gzip-pickle write
57.1 s · **20.6 MB** (14.6 B/row compressed).
**Projected full product: ~503 MB and ~44 min of fetch** across 1980–2026.

Chunking is **by year** for the large products. Not arbitrary: WRDS enforces query limits, and a
34.5M-row single `SELECT` is the kind of request that gets killed server-side an hour in — the
most expensive way to discover a limit.

Resume discipline is the harvest's, inherited whole: one unit = one (product, chunk); payload
written atomically **before** its fsynced manifest line; a re-run re-does any unit whose payload
is absent or disagrees with its record.

---

## THE REVISED PULL PLAN — what the census actually licenses

The brief's a→g order assumed entitlements this account does not have. The measured order is:

| # | product | status | why it is where it is |
|---|---|---|---|
| 1 | **IBES** (`id`, `actu`, `statsum`, `det_epsus`) | **PULLING** | The only item that unparks a ledger row. `det_epsus` carries `anndats`, `revdats`, `actdats`, `analys`, `estimator`, `fpedats` — **per-analyst revision dates, point-in-time**, which is exactly D6's stated blocker |
| 2 | **CRSP delisting + names** | **DONE / PULLING** | 38,872 rows, trivial cost, and it is a *cross-check* rather than a new signal — any disagreement with our ACTIONS mask is a finding either way |
| 3 | **Compustat PIT** (`co_ifndq`) | **PULLING** | 2.1M rows; `_dc` data-code companions confirm it is the unrestated as-first-reported file |
| — | OptionMetrics / Thomson / short interest / TAQ | **BLOCKED** | Not entitled. Recorded above with evidence, not retried |

**D6 is unparked by (1) and the ledger row should say so.** `RESEARCH_LOG.md` is untouched and no
published `N` moves — a collection run charges no trials.

---

## STANDING CAVEATS

* **Entitlement can change under us.** This census is a measurement dated 2026-08-24, not a
  contract. Re-run `scripts/wrds_census.py` before planning anything on a product not pulled.
* **`ibes.det_epsus` vs `detu_epsus` is adjusted vs unadjusted for splits.** They are near-equal
  in size (34.54M vs 34.52M) and are **not interchangeable**: an adjusted estimate compared with
  an unadjusted actual is a units error that looks like a surprise. Whichever a register uses
  must be named in the register.
* **IBES is quarterly-and-annual across `fpi` codes** — a naive `SELECT *` mixes horizons. Any
  consumer must filter `fpi` and say which it took.
* **Nothing here has been analysed.** No IC, no arm, no verdict. The data exists on `D:` and is
  described here; that is the whole deliverable.

---

# PHASE 2 — the two probes the census made worth running

**Measured 2026-08-24. Zero trials.** Both are facts about what exists; neither is an arm, a
verdict, or a licence to quote anything. Artifacts: `D:\wrds\GICS_PROBE.json`,
`GICS_COVERAGE.json`, `ADV_PROBE.json`.

---

## (a) HISTORICAL GICS — IT IS THERE, IT IS DATED, AND IT IS REAL

**`comp.co_hgic` is ENTITLED.** 45,836 rows over 32,012 gvkeys, carrying `gsector`, `ggroup`,
`gind`, `gsubind` with **`indfrom` / `indthru` date ranges**. `indfrom` spans
**1999-06-30 → 2026-08-24**.

**It is a HISTORY, not a snapshot wearing a date** — which is the distinction S25 turned on, so
it was measured rather than assumed:

| | |
|---|---|
| rows per gvkey | **1.432** |
| gvkeys with **more than one** dated row | **9,679 of 32,012 = 30.2%** |
| distribution | 1 row: 22,333 · 2: 6,874 · 3: 1,867 · 4: 637 · 5: 225 · 6: 58 · 7: 13 · 8: 3 |
| open-ended rows (`indthru` null, i.e. current) | 12,099 |

**Coverage of OUR universe — 2,403 of 2,531 panel names = 94.9%.** Linked
`ticker → gvkey` through **`comp.security.tic`**, because `crsp.ccmxpf_lnkhist` — the standard
CRSP-Compustat link — is **DENIED** on this account, and `comp.company` carries no `tic` at all
on this account (it has `fic`/`sic`; the first attempt raised `UndefinedColumn` and the route was
corrected rather than guessed at again).

**AND THE LOOK-AHEAD IT REPAIRS IS MATERIAL RATHER THAN THEORETICAL: 1,007 of our 2,403 covered
names — 41.9% — were reclassified at least once.** Those are precisely the names for which
today's sector is the wrong sector for a 2009 row.

### The honest taxonomy answer: both are 11 sectors and they are NOT the same 11

| | |
|---|---|
| `co_hgic` | 11 GICS codes: **10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60** |
| our panel | 11 strings: Basic Materials · Communication Services · Consumer Cyclical · Consumer Defensive · Energy · Financial Services · Healthcare · Industrials · Real Estate · Technology · Utilities |

The panel's values are **Yahoo/Morningstar-style, not GICS.** The counts match at 11 and the
boundaries do not: GICS splits Consumer Discretionary (25) from Consumer Staples (30) on
different lines than Cyclical/Defensive, and GICS's Information Technology (45) excludes names
Yahoo files under Technology. **A crosswalk is possible and is a CHOICE, not a lookup** — whoever
writes it owns it, and it belongs in the register that uses it.

### THE TRAP THAT WOULD OTHERWISE BE DISCOVERED AS A FINDING

**GICS ITSELF CHANGED DURING THIS WINDOW, so not every one of the 30.2% "reclassifications" is a
company event.** Real Estate (60) was separated from Financials in 2016; Communication Services
(50) was created in 2018 by moving names out of Information Technology and Consumer
Discretionary. Those revisions move **every firm in a group on one date** and will read, in a
naive event study, as a wave of simultaneous sector changes.

**A consumer must separate taxonomy revisions from firm-level reclassifications before treating
`indfrom` as an event date.** This is the codes-34/35 sunset lesson from `I-4` in a new place: a
vendor-side definitional change that looks like data.

### What it unlocks, and what it does not

* **`S25` REOPENS — the first time a permanently-closed ledger row has had its named condition
  met.** Its closure was `UNOBTAINABLE-WITHOUT-NEW-DATA` and its route back was *"a historical
  GICS snapshot, not sold as history"*. This is that, dated, at 94.9% coverage.
* **The valuation path's one look-ahead input is repairable.** `calibration.py` passes **today's**
  TICKERS sector into `pit_company`, which selects `SECTOR_TARGET_MARGIN` (0.100 → 0.270, a 2.70×
  spread) and `SECTOR_MULTIPLES` for a 1999 or 2009 valuation. With a dated map that becomes a
  point-in-time lookup.
* **IT DOES NOT REACH BEFORE 1999-06-30.** GICS launched in 1999, so `co_hgic` cannot date a
  sector for the early rows `S23`'s valuation path values. Our 69-date panel starts 2009-01-15
  and is fully covered; anything earlier is not.
* **Sector-neutral ranking is NOT thereby reopened.** `SECTOR-NEUTRAL-B6` was rejected on
  measurement in both held-out directions, twice, and `S25` was only one of its two named routes
  back. A dated map removes the data objection; it does not touch the rejection.

---

## (b) CRSP DAILY VOLUME — a $ADV IS BUILDABLE, AND THE CUT COSTS THE LAST FIVE DATES

**`crsp_a_stock.dsf` is ENTITLED and carries every column a $ADV needs:** `permno`, `date`,
`vol`, `prc`, `shrout`, `cfacpr`, `cfacshr`. Span **1925-12-31 → 2024-12-31**.

| | |
|---|---|
| panel tickers linked `ticker → permno` (via `dsenames`) | **2,271 of 2,531 = 89.7%** |
| rows over the panel window for those permnos | **6,628,742** |
| rows with NULL volume | 38,347 = **0.58%** |

**Against the existing path this is a 4.5× improvement.** `B13` and `S7` are blocked because the
only volume on this path is `data/bulk/prepared/bars`, which covers **502 names = 19.8%** of the
universe. CRSP reaches **89.7%**. That does not make a liquidity prefilter universal — **~10% of
names still have no measure**, so `B13`'s "cannot bind universally" objection survives in reduced
form — but it moves the question from *unbuildable* to *buildable with a stated hole*.

### What CRSP's 2024-12-31 cut costs, exactly

**5 of the 69 rebalance dates have no CRSP data at all:** 2025-01-27, 2025-04-28, 2025-07-29,
2025-10-27, 2026-01-28 — **9,367 panel rows of 113,945 = 8.2%.**

So a CRSP-based $ADV covers **64 of 69 dates**. For a backtest that is a truncation to disclose;
for anything touching the **forward paper track**, which lives entirely after the cut, CRSP is
useless. Both statements are true at once and neither substitutes for the other.

### THE JOIN MUST BE DATE-SCOPED, AND THIS IS S3-I5 RECURRING

**1,053 of the 2,271 matched tickers map to MORE THAN ONE permno.** `dsenames` is a dated name
history (`namedt` / `nameendt`) covering a century, and a `ticker → permno` dict that ignores
those dates inherits **exactly** the ticker-reuse contamination `S3-I5` just adjudicated for the
option chains — SNOW, SNDK, SN and the rest, in a new table.

The ambiguity is inflated by CRSP's full 1925-2024 span and a date-scoped join resolves most of
it. **But it must BE date-scoped**, and a consumer that builds the obvious dictionary will not
notice. Recorded here rather than left to be rediscovered.

---

## LEDGER CONSEQUENCES

| row | before | after this phase |
|---|---|---|
| **D6** estimate revisions | PARKED — *"Path is IBES via WRDS"* | **UNPARKED.** IBES entitled and pulled: 34,540,574 detail rows with `anndats`/`revdats`/`analys` |
| **B13** liquidity prefilter | blocked — no liquidity measure on this path | **UNPARKS at 89.7% coverage**, 64 of 69 dates, ~10% of names still unmeasured |
| **S7** 4th interaction (`size × liquidity`) | not buildable | **UNPARKS on the same measure**, same caveats |
| **S25** point-in-time sector map | **CLOSED — unobtainable without new data** | **REOPENS.** `co_hgic` is dated, 94.9% coverage, 41.9% of our names reclassified — but the taxonomy is GICS, not the panel's, and the crosswalk is a choice a register must own |

**None of these is a result.** Each is a statement that the data now exists; every one still
needs its own register, its own trials and its own blind pre-registration before a number is
quoted.

---

# RE-PROBE, 2026-08-24 — the census above was written from a brief's guesses and it was wrong

**Zero trials. Facts about what exists.** Don supplied the OFFICIAL WRDS subscription list, which
contradicted this census in one place and named nine products the original brief never mentioned.
Everything below is a real `SELECT`; artifacts `D:\wrds\LIB_DISCOVERY.json`,
`TABLE_DISCOVERY.json`, `ENTITLE_REPROBE{,2,3}.json`, `FINAL_PROBE.json`,
`THIRTEENF_{PROBE,COVERAGE,MANAGERS,GAIN}.json`.

## WHAT THE FIRST CENSUS GOT WRONG, PLAINLY

### 1. THE THOMSON VERDICT. The observation was right; the inference was wrong, and it hid the largest readable dataset on this account.

The census recorded *"(e) Thomson insider + 13F — DENIED on all seven tables probed ... the
intra-quarter filing detail is not obtainable on this account."* **The denial is real** — re-probed
on **eight consecutive FRESH connections**, one per table, specifically to rule out a shared
poisoned session, and all eight returned `permission denied`. `tfn` is a legacy shell this login
cannot read.

**But "these seven table names are denied" is not "this product is unobtainable", and the census
wrote the second sentence while having measured only the first.** WRDS builds its own 13F and
insider products directly from SEC filings, in different libraries, and **both are ENTITLED:**

| | rows | span |
|---|---|---|
| `wrdssec_all.wrds_13f_holdings` | **103,984,958** | 1987-03-31 → 2025-09-30 |
| `wrdssec_all.wrds_13f_summary` | 465,435 | 1987-03-31 → 2025-09-30 |
| `wrdssec_all.wrds_13f_link` | 4,826 | — |
| `wrdssec_insiders.table1` (Form 4 transactions) | **10,083,927** | — |
| `wrdssec_insiders.nonderivatives` | 10,083,927 | — |
| `wrdssec_insiders.table2` (derivatives) | 4,904,737 | — |
| `wrdssec_insiders.reporting_owners` | 4,898,144 | — |

**THE PORTABLE PART, because this census is the thing that will be quoted: a census that probes
the names in a brief measures the brief.** Nothing was wrong with the probe; the target list came
from the brief's vocabulary (`tfn`), and the correct target was discoverable by enumerating
libraries rather than by asking whether a guessed name answered. The re-probe enumerates first.

### 2. "OptionMetrics is not entitled" — CONFIRMED, and Cboe does not replace it

Don's list confirms OptionMetrics absent, so the headline at the top of this file stands. The
`cboe` library **looks** like a replacement — it carries `optprice_1998` … `optprice_2026` and
`ivlisted_1998` … `ivlisted_2026`, exactly the shape of a 28-year options history with implied
vols, which is the thing this census called the biggest missing item.

**It is DENIED.** Every production table probed — `optprice_2010`, `optprice_2016`,
`ivlisted_2010`, `eqmaster`, `optcontract`, `wrds_eq_opt_merged` — returns `permission denied`.
Only `cboe_sample.optprice` reads, at **75,126 rows**.

**THIS IS A DISAGREEMENT BETWEEN THE SUBSCRIPTION PAGE AND THE GRANT, AND IT IS DON'S TO RAISE
WITH WRDS, NOT MINE TO RESOLVE.** The page lists Cboe Options as subscribed; this login cannot
read it. That is precisely the entitlement-versus-catalogue gap this census exists to measure, and
it now runs in both directions: the page over-promises on Cboe exactly as the brief under-promised
on Thomson. **Do not plan a pre-2016 options history on `cboe` until a real SELECT succeeds.**

### 3. TAQ — confirmed absent, and the "terabytes" premise stays void

Don's list confirms it. `taqsamp`/`taqmsamp` remain the only TAQ objects. The day-trading sibling
project should still be told this account is not a TAQ source.

### 4. Two products on the official list have NO library on this account under any spelling

Searched all **221** visible library names: **Intraday Indicators by WRDS** and **Historical
SPDJI** are not present. Reported as measured rather than as concluded — a name I cannot find is
weaker evidence than a table that returns `permission denied`, and the honest state is
ABSENT-ON-THIS-LOGIN rather than proven unavailable.

**Consequence for `B13`/`S7`: the hoped-for TAQ-derived daily liquidity file does not exist here,
so PHASE 2's CRSP `dsf` route remains the answer for a $ADV, at the 89.7 pct coverage and the
64-of-69 dates recorded there.** Nothing about that finding changes.

For index membership the readable substitute is **`crsp_a_indexes.dsp500list` — 2,064 dated
membership spells, 1925-12-31 → 2024-12-31** (plus `dsp500list_v2` 2,084 and
`stkindmembership_ind` 2,947,788). That is S&P 500 only, from CRSP rather than SPDJI, and it
inherits CRSP's 2024-12-31 cut.

### 5. THE LINK THIS ACCOUNT DOES NOT HAVE, and it constrains everything above

**`crsp.ccmxpf_lnkhist`, `crsp.ccmxpf_linktable`, `crsp.ccm_lookup` and `wrdsapps.id_ccm` are all
DENIED.** The standard CRSP-Compustat link — the thing "Linking Queries / CCM" refers to — is not
readable, so **every join in this account is done through a substitute and each one must be
declared:**

| join | route used | measured coverage of our 2,531 names |
|---|---|---|
| ticker → gvkey (Compustat) | `comp.security.tic` | **2,403 = 94.9 pct** |
| ticker → permno (CRSP) | `crsp_a_stock.dsenames` (DATED) | **2,271 = 89.7 pct** |
| ticker → cusip (for 13F) | `crsp.stocknames` (DATED, 83,280 rows) | **2,271 = 89.7 pct** |
| ticker → IBES | `wrdsapps_link_crsp_ibes.ibcrsphist` (37,662) | not yet measured |

**`crsp.stocknames` and `dsenames` are DATED and the dates are load-bearing** — 1,053 of the 2,271
matched tickers map to more than one permno, which is `S3-I5`'s reuse problem in a new table.

---

## THE 13F RESULT IS THE OPPOSITE OF THE HYPOTHESIS, AND IT IS THE MOST IMPORTANT THING HERE

The re-probe was commissioned on the hypothesis that a readable 13F history *"repairs the panel's
pre-2013 institutional hole — the root cause of MA58's 49-of-69-dates template defect"*.

**MEASURED, IT DOES NOT. IT BUYS EXACTLY ONE REBALANCE DATE.**

The issuer count says otherwise and that is the trap: on pre-2013 report dates the table touches
**~1,000 of our names**, which reads as ample coverage. **The manager count says those rows come
from a handful of filers:**

| year | median managers filing | max | rows |
|---|---|---|---|
| 2008 | 9.5 | 12 | 5,543 |
| 2010 | 24.5 | 39 | 27,421 |
| 2012 | **71** | 136 | 152,962 |
| **2013** | **3,456.5** | 3,807 | **4,415,249** |
| 2016 | 4,292 | 4,472 | 6,636,155 |
| 2024 | 7,470 | 8,156 | 11,868,425 |

**A 49-fold step between 2012 and 2013**, which is the SEC's structured-XML mandate for 13F, not a
change in who invests. Before it, the table is the early voluntary filers.

**An institutional-breadth signal is a statistic ABOUT MANAGERS** — how many hold a name, how
concentrated they are, how that moved. A date carrying ten managers cannot support one however
many issuers those ten touch. So:

* report dates carrying a real cross-section (**≥1,000 managers**): **50, first `2013-06-30`**
* the shipped `institutional` theme's first date with ≥20 scored names: **`2014-01-17`**, covering
  **49 of 69** rebalance dates — reproducing `MA58`'s figure exactly, from the panel rather than
  from the write-up
* at the 45-day filing deadline, rebalance dates that would **GAIN** a real 13F cross-section:
  **ONE — `2013-10-17`.** 49 → 50 of 69.

**`MA58`'s defect is NOT repaired, and the reason is structural rather than an entitlement
problem: the data does not exist before 2013 in any product on this account, because it was not
filed in a machine-readable form.** Anyone re-opening the incremental-IC template on the strength
of "we now have 13F back to 1987" would be building on 103,984,958 rows of which the pre-2013
portion cannot carry the statistic it would be used for.

**WHAT THE 13F TABLE IS STILL GOOD FOR, so this does not read as a rejection of the product:** it
is a full-detail, per-manager, per-holding record from 2013 with **7,000-8,000 managers per
quarter** — far richer than Sharadar SF3's derived aggregates — and it is the natural source for
any question about manager identity, concentration, or intra-quarter change **within the window
the shipped theme already covers**. That is a real capability. It is simply not a time-extension.

---

## ENTITLEMENT, RE-MEASURED — every row a real SELECT

**ENTITLED**

| product | library.table | rows | span |
|---|---|---|---|
| WRDS 13F holdings | `wrdssec_all.wrds_13f_holdings` | 103,984,958 | 1987-03-31 → 2025-09-30 |
| WRDS 13F summary | `wrdssec_all.wrds_13f_summary` | 465,435 | 1987-03-31 → 2025-09-30 |
| WRDS 13F manager link | `wrdssec_all.wrds_13f_link` | 4,826 | — |
| WRDS insiders (Form 4) | `wrdssec_insiders.table1` | 10,083,927 | — |
| WRDS insiders derivatives | `wrdssec_insiders.table2` | 4,904,737 | — |
| WRDS insiders owners | `wrdssec_insiders.reporting_owners` | 4,898,144 | — |
| SEC filing index | `wrdssec_all.wrds_forms` | 27,153,366 | 1980-01-02 → 2026-08-21 |
| SEC document forms | `wrdssec_all.dforms` | 43,606,006 | — |
| SEC 8-K items | `wrdssec_all.items8k` | 4,460,047 | — |
| SEC Analytics bag-of-words | `wrdssec_secsa.bow_2015` | 465,659,715 (ONE year) | — |
| SEC Analytics NLP | `wrdssec_secsa.wrds_nlpsa` | 27,136,348 | — |
| Compustat historical GICS | `comp.co_hgic` | 45,836 | `indfrom` 1999-06-30 → 2026-08-24 |
| Compustat security / company | `comp.security` / `comp.company` | 77,497 / 58,325 | — |
| CRSP stock names (dated) | `crsp.stocknames` | 83,280 | — |
| S&P 500 membership | `crsp_a_indexes.dsp500list` | 2,064 spells | 1925-12-31 → 2024-12-31 |
| index membership (CRSP) | `crsp_a_indexes.stkindmembership_ind` | 2,947,788 | — |
| TRACE enhanced | `trace_enhanced.trace_enhanced` | 455,675,242 | — |
| TRACE standard | `trace_standard.trace` | 318,892,226 | — |
| CRSP-IBES link | `wrdsapps_link_crsp_ibes.ibcrsphist` | 37,662 | — |
| WRDS id | `wrdsapps.id` | 45,920 | — |
| OTC end of day | `otc_endofday.endofday` | 76,400,454 | — |
| MIDAS | `midas.security` | 21,149,699 | — |
| PHLX options | `phlx.coph` | 450,203 | — |
| block trades | `block.block` | 20,975 | — |
| WRDS world indices | `wrdsapps_windices.dwcountryreturns` | 298,845 | — |
| Cboe **SAMPLE** only | `cboe_sample.optprice` | 75,126 | — |

**DENIED** (table exists, this login may not read it)

`tfn.s34`, `s34type1`, `s34type3`, `s34names`, `table1`, `table2`, `form144`, `rule10b5` ·
`cboe.optprice_2010`, `optprice_2016`, `ivlisted_2010`, `eqmaster`, `optcontract`,
`wrds_eq_opt_merged` · `crsp.ccmxpf_lnkhist`, `ccmxpf_linktable`, `ccm_lookup` · `wrdsapps.id_ccm`

**ABSENT** (no such object on this account)

`wrdsapps_link_crsp_taq.taqmclink` · `wrdssec_common.forms` · Intraday Indicators by WRDS (no
library) · Historical SPDJI (no library) · OptionMetrics · TAQ production

**FOUR PRODUCTS NOBODY'S BRIEF MENTIONED AND THIS ACCOUNT CARRIES:** `phlx` (PHLX options,
450,203 rows), `block` (block trades), `otc_endofday` (76.4M rows), `midas` (21.1M rows). None is
measured against our universe and none is proposed; they are recorded so the next reader does not
have to rediscover them.

---

## WHAT THIS CHANGES IN THE LEDGER

| row | before | after the re-probe |
|---|---|---|
| Thomson 13F / insiders | recorded unobtainable | **AVAILABLE under `wrdssec_*`** — full per-manager detail from 2013 |
| `MA58` template defect | hoped repairable by 13F history | **NOT REPAIRED.** 49 → 50 of 69 dates. Structural, not entitlement |
| `MA57` insider classification | needs `ownername`/`transactioncode`, already on disk | unchanged — `wrdssec_insiders` is an ALTERNATIVE source, not a prerequisite |
| `B13` / `S7` | unparked on CRSP `dsf` (PHASE 2) | unchanged — Intraday Indicators does not exist here |
| `S25` | re-opened on `comp.co_hgic` (PHASE 2) | unchanged and confirmed |
| `D6` | unparked on IBES (PHASE 1) | unchanged |
| Cboe / `D4` | declined as a purchase | **still not available** — production DENIED, sample only |

**Nothing here is a result.** Every line is a statement about what data exists. Each downstream
use needs its own register, its own trials and its own blind pre-registration.

---

## A SILENT HOLE IN THE PULL ITSELF, FOUND THE SAME DAY AND CLOSED

**`ibes.actu_epsus` was short by 102,213 rows and every integrity check said it was fine.**
Every chunk reported `ok`, every sha256 verified, every byte count matched. The chunk predicate
is `>= Jan 1 AND < Jan 1`, and **a NULL date satisfies neither, so a row with no `anndats`
belongs to no chunk and is dropped by all of them.**

* found by **reconciling the summed chunk rows against the table's own `count(*)`** — 1,221,058
  against 1,323,271 — not by anything raising
* the gap is **exactly** the 102,213 rows where `anndats IS NULL`
* **confirmed by control rather than assumed:** `det_epsus` and `statsum_epsus` reconcile exactly
  and carry **zero** nulls on their own chunk columns, so the mechanism is the nulls and not the
  chunking in general

**THE PORTABLE PART: file-level integrity checks confirm that what was written is intact and
cannot see what was never fetched.** A hash proves the bytes on disk match the bytes recorded; it
says nothing about rows the query never selected. Completeness has to be checked against the
SOURCE, so `wrds_pull.py --reconcile` now does, and a `nulldate` chunk is emitted for any product
that actually has such rows.

**ALL NINE PRODUCTS NOW RECONCILE TO THE ROW** — `comp_pit` 2,114,571; `crsp_delist` 38,872;
`crsp_dsenames` 117,859; `crsp_msedelist` 38,843; `ibes_act_epsus` 1,323,271;
`ibes_actu_epsus` 1,323,271; `ibes_det_epsus` 34,540,574; `ibes_id` 308,801;
`ibes_statsum_epsus` 15,029,492. **54,835,554 rows, 1.279 GB.**

### And the pull was internally inconsistent, in the exact way this project had already written down

**It paired an ADJUSTED estimate file with an UNADJUSTED actuals file.** IBES ships each twice —
`det_epsus`/`act_epsus` split-adjusted, `detu_epsus`/`actu_epsus` unadjusted — and the pull took
**`det_epsus` (adjusted)** and **`actu_epsus` (unadjusted)**.

**The `D6` ledger row had already warned about precisely this pairing, in its own words:** *"an
adjusted estimate against an unadjusted actual is a units error that reads as a surprise"*. The
warning was written, and then the warned-against combination was pulled — because the four file
names differ by **one letter** and only one of them carries the `u`.

**Nothing is retracted, because nothing has been computed from it.** But a surprise built from the
pull as it stood would have been wrong by every split in the sample, silently, in a direction that
varies by name. `ibes_act_epsus` (**1,323,271 rows, the same count**) is now pulled as the
counterpart `det_epsus` needs; `actu_epsus` is kept because it is the counterpart `detu_epsus`
would need. **A register must still DECLARE which pair it uses** — having both on disk makes the
right choice possible, not automatic.

**A written-down hazard does not defend against itself.** This one survived a census, a sizing
pass, a pull and a reconciliation, and was caught only by asking what the two file names on the
manifest actually meant.

---

## THE WRDS INSIDERS TABLE, MEASURED AGAINST `MA57` — a real upgrade and a real staleness

`MA57` is the routine-versus-opportunistic insider classification, and this project already
measured that Sharadar's export on disk carries what it needs (`ownername`, `transactiondate`,
`transactioncode`, zero missing on 124,181 open-market purchase rows). So `wrdssec_insiders` is
only worth anything if it **adds** something.

**IT DOES, AND THE ADDITIONS ARE THE ONES THE LITERATURE USES.** `wrdssec_insiders.table1` (59
columns) carries **`rptownercik` — a STABLE PERSON IDENTIFIER** rather than a name string, which
is what a routine/opportunistic classification keys on and is exactly where a name-matching
approach silently merges two people or splits one; plus the role flags **`isdirector`,
`isofficer`, `officertitle`, `istenpercentowner`**, which Sharadar does not carry at all; plus
`issuertradingsymbol`, so it joins to us without CUSIP.

**AND THE MOST TEMPTING COLUMN ON IT IS NOT A HISTORY. `aff10b5one` — the Rule 10b5-1 plan
affirmation — is 100.0% NULL in every year from 2003 to 2022, and 45.0% null in 2023.** A
pre-scheduled-plan flag is the thing a routine/opportunistic proxy is *proxying for*, so it looks
like it would replace the classification outright. It cannot: the SEC only made that checkbox
mandatory in its **December 2022** Form 4 amendments, so it is a **post-2023 instrument, not a
history**, and the "existence is not population" rule applies in full.

**AND THE TABLE IS THREE YEARS STALE — `fdate` runs 2003-05-05 → 2023-10-30**, against a Sharadar
export reaching 2026-07-24. **So on recency Sharadar WINS, and the honest statement is that WRDS
adds identity and role for 2003–2023 while losing the last three years.** `transactiondate` also
runs 1980-03-01 → **2050-05-10**, i.e. it contains filer typos and must be bounded by the filing
date rather than trusted.

**`MA57` is therefore NOT unblocked by this — it was never blocked** (the record already shows the
`_KEEP` allowlist, not the export, is why those columns read as absent). What changes is that a
future `MA57` register may **choose** a richer source, and it must then declare the 2023 cut and
which of the two identifier schemes it uses. Nothing here is measured against a bar.

**A NAMING PRECISION, because the brief's "17 tables" points at the wrong object:**
`wrds_insiders_samp` has **17** tables and is the SAMPLE (`wrds_table_1` reads 1,539 rows);
the production library is **`wrdssec_insiders`, 9 tables**. Both are readable, and only the
second is the data.

### Three further defects in the puller, all measured, all fixed

1. **A poisoned transaction condemned every later chunk.** After one chunk failed at the file
   layer, the rest returned *"Can't reconnect until invalid transaction is rolled back"* — a
   different spelling of "the session is gone" that the retry rule did not match, so three chunks
   failed for a reason none of them caused. Same shape as the original one-connection defect. The
   handle is now replaced after ANY chunk gives up, so one failure costs one chunk.
2. **Two pullers ran on one product at once — my error, not the machine's.** Both computed the
   same work list and raced on the same `.tmp`, producing `WinError 32` and `WinError 2`. **Those
   symptoms read as antivirus and were briefly written up as antivirus in a code comment, which
   was a cause asserted rather than measured.** Nothing was corrupted, by luck: the loser of the
   race could equally have replaced a truncated file. `_acquire_lock` now refuses the second
   process by name.
3. **A dead needle in the retry rule.** Two entries were capitalised while the haystack is
   lowercased, so `"SSL connection has been closed"` could never match. It was live for as long
   as it took the new two-directional test to run — the guard-that-cannot-fire family again.

**5 of 5 mutations caught with the source restored byte-for-byte; 18 tests in
`tests/test_wrds_client.py`.**
