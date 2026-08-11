# PREREG — V2G: free live sources for the three dead themes, MEASURED ONLY

Committed **alone, before any source-fetching or measurement code exists**, so the git history
proves the construction, the join key, the coverage definition, the floors and the predictions
were all fixed before a single number came back. Same discipline as `PREREG_v2f_live_coverage.md`.

Follow-up to `HANDOFF_live_data_bugs.md` **Part 12**, which measured on 500 real served rows that
**three themes carrying 42.9% of the deployed weight reach no live score**:

| theme | deployed weight | live state measured in Part 12 |
|---|---|---|
| `capital_discipline` | 0.125 | **null on 500/500 rows** |
| `institutional` | 0.125 | **null on 500/500 rows** |
| `insider` | 0.125 | **100% non-null, ONE distinct value** (the constant 0.0) |

---

## 1. WHAT THIS IS, AND — MORE IMPORTANTLY — WHAT IT IS NOT

This builds **measurement instruments**, not product. Nothing here changes what the site scores.

* **No composite change.** Not one file under `valuation/**` is edited. The columns are computed
  in a new script and reported; they are never handed to `build_frame`, `_decompose`, or any
  shipped path. This is stricter than "no composite change" and it is what makes the claim
  testable — see §6 B5.
* **No weight flip.** `settings.FACTOR_WEIGHTS` is not touched.
* **No vintage event.** Under **Amendment 1** (`PAPER_TRACK_CONTRACT.md` §5a) a vintage closes on
  an **ADOPTED** change — one that ships in the live scoring path. Nothing here ships in it, so
  vintage 2 (opened 2026-08-10, `params_id 0060c5ef3dda`) stays open and its clock does not reset.

**ADOPTION IS A SEPARATE, LATER, MORE EXPENSIVE DECISION AND MUST NOT BE SHORTCUT FROM HERE.**
Coverage is a *necessary* condition, not a sufficient one. Before any of these can enter the
composite it needs, at minimum: (a) the pipeline builder's cost measurement on the added fetch
load, (b) the held-out gate (`holdout_theme_validate` / `holdout_compare_panels`) at the standing
margins — **100 bps alpha and 0.25 long-short t in BOTH split directions**, and (c) acceptance
that under **Rule 6** the adoption **closes vintage 2, resets the entire accrued forward clock to
zero, and buys nothing statistically** (`PAPER_TRACK_CONTRACT.md` §2: 60 months at 49% power). A
theme that is merely *present* is not a theme that is *worth* five years. Anyone reading a green
coverage number here as a licence to wire it in has misread this section.

## 2. THE BRIEF'S THIRD ITEM IS RIGHT ABOUT THE DEFECT AND WRONG ABOUT ONE DESTINATION — recorded
##    BEFORE the run, in the V2F tradition of correcting the premise in the register itself

The brief asks for `capital_discipline` to be sourced from *"net issuance from shares-outstanding
history **and accruals from statements**"*. Both are worth building and both are built here, but
**accruals does not live in `capital_discipline` in the shipped construction.** `factors.py:254`
is `capital_discipline = mean(z_neg_issuance)` — issuance **alone**; `neg_asset_growth` was
deliberately dropped (median IC −0.0141, t −0.70, wrong sign). `accruals_q` is a **`quality`**
input (`factors.py:227`), and `quality` is one of the four themes that already works live.

So the honest accounting, fixed here in advance: **net issuance is the only input that can revive
`capital_discipline`; accruals can only improve a theme that is not dead.** Accruals is still
built and its coverage still reported, labelled against `quality`, not against
`capital_discipline`. No number is moved between themes to make a total look better.

## 3. SOURCES — all free, all public, no licensed data

**None of this touches `data/backtest` (licensed Sharadar).** The distinction the brief draws is
real and is the reason this is buildable: SF3 is a licensed *aggregation*, the underlying filings
are public record.

| theme input | source | endpoint |
|---|---|---|
| `inst_breadth`, `sm_breadth`, `inst_accum` | SEC Form 13F structured data sets | `sec.gov/files/structureddata/data/form-13f-data-sets/<window>_form13f.zip` |
| `share_issuance` (→ `neg_issuance`) | SEC XBRL company facts | `data.sec.gov/api/xbrl/companyfacts/CIK<10>.json` |
| `accruals_q` (→ `quality`) | SEC XBRL company facts | same |
| `insider_score` (→ `insider`) | SEC Form 4, via the repo's **existing fixed** scraper | `valuation/screener/insider.py::insider_detail` (imported read-only) |
| CUSIP join key | the company's own SC 13D/G filings | `data.sec.gov/submissions/CIK<10>.json` + the filing document |

## 4. CONSTRUCTION — fixed here, in full, before anything is fetched

### 4.1 Universe
The **500 served rows** already captured at `data/live_cache/snapshot_2026-08-08.json`
(`scan_date 2026-08-08`, provider FMP, 0 synthetic), i.e. the exact population Part 12 measured.
Pinned before fetching; not re-captured, not re-ranked, not filtered.

### 4.2 Periods
Two consecutive 13F reporting periods so that *change* inputs exist: **`31-DEC-2025`** and
**`31-MAR-2026`**. The `01jun2026-31aug2026` window is **not published** (Q2-2026 13Fs are due
2026-08-14, after today), so these are the two most recent complete quarters. Recorded because
"the latest quarter" must mean a named date, not whatever was on the server.

### 4.3 The 13F aggregation
From `INFOTABLE.tsv` joined to `SUBMISSION.tsv` on `ACCESSION_NUMBER`:

* Keep `SUBMISSIONTYPE` in `13F-HR`, `13F-HR/A`; keep the target `PERIODOFREPORT`.
* **Drop `PUTCALL` non-empty** (option positions are not share ownership) and keep
  `SSHPRNAMTTYPE == "SH"` (drop `PRN`, which is principal amount, i.e. debt).
* **Amendments, pre-committed:** group by filer `CIK`. Include the original plus any
  `AMENDMENTTYPE = NEW HOLDINGS` amendment (additive by definition); if a `RESTATEMENT`
  amendment exists, use **only the latest-filed** accession for that filer. Measured shape for
  `31-DEC-2025`: 10,676 filings, 10,524 distinct filers, **147 (1.4%) with more than one
  accession**; 290 restatements and 97 new-holdings amendments project-wide.
* **`inst_breadth` counts DISTINCT filer CIKs**, so it is invariant to the accession rule
  entirely; only the value aggregate is exposed to it. Stated because it means the weakest part
  of this construction cannot touch the breadth term.

Per (CUSIP, period): `holders` = distinct filer CIKs, `value_usd` = summed `VALUE`,
`shares` = summed `SSHPRNAMT`. Then

```
inst_breadth = holders(2026-03-31)
sm_breadth   = holders(2026-03-31) / holders(2025-12-31) - 1      # growth in holder count
inst_accum   = shares(2026-03-31)  / shares(2025-12-31)  - 1      # accumulation, share-based
```

`inst_accum` is built on **shares, not dollars**, deliberately: a dollar change over a quarter is
mostly the stock's own price move, which would make the "13F accumulation" signal a momentum
signal wearing a 13F label. Fixed here so it cannot be chosen later.

`institutional = mean(z(inst_accum), z(sm_breadth))`, matching `factors.py:267` exactly.

### 4.4 The join key — authoritative first, fuzzy second, and an anchor over both
13F identifies issuers by **CUSIP**; the served universe identifies them by **ticker**. There is
no free CUSIP master, so the key is built in this fixed order and the rung used is **recorded per
name**, exactly like the beta ladder:

1. **`cusip_13g` (authoritative).** Resolve ticker → CIK from `sec.gov/files/company_tickers.json`,
   read the company's own `SC 13D`/`SC 13G` filings from its submissions JSON, strip HTML, and
   extract CUSIP-shaped tokens. **Every candidate must pass the CUSIP mod-10 check digit**, which
   makes a false positive essentially impossible; the **modal** validated CUSIP across up to
   `MAX_13G_DOCS = 6` filings wins. This is a hard key, not a fuzzy one.
2. **`name_exact` (fallback).** Normalised exact match of the served `name` — and, failing that,
   the EDGAR `title` — against `NAMEOFISSUER`. Normalisation is fixed here: uppercase, drop
   punctuation, collapse whitespace, strip a trailing corporate suffix from
   `{INC, CORP, CORPORATION, CO, COMPANY, LTD, LIMITED, PLC, SA, NV, AG, LP, HOLDINGS, GROUP, THE}`.
   A name matching **more than one** CUSIP is a **failure, not a coin flip** — recorded as
   `ambiguous`, never resolved by picking the bigger one.
3. Nothing else. **The matcher is not tuned after seeing coverage.** If coverage is poor, that is
   the reported result and the unmatched names are listed for a later lane; iterating the rules
   against the served universe would be selecting the instrument on the answer.

**THE ANCHOR, over both rungs.** For every matched name compute
`inst_own_frac = value_usd(2026-03-31) / market_cap`. A join that landed on the wrong issuer
produces an absurd ratio. Pre-committed admissible band: **`0 < inst_own_frac <= 1.50`** (above 1.0
is possible and not rare — 13F values are quarter-end while the served market cap is 2026-08-08,
and multi-class issuers report one CUSIP against one class). A name outside the band is
**excluded from coverage and listed as `anchor_failed`** — never silently kept.

### 4.5 `capital_discipline` and the `quality` by-product, from XBRL company facts
Annual (`10-K`, `FY`) series, recent-first, using the same concept-preference approach as
`valuation/data/edgar.py`:

```
shares    : dei:EntityCommonStockSharesOutstanding
            -> us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding (fallback)
share_issuance = shares(t) / shares(t-1) - 1          # needs TWO annual points
neg_issuance   = -share_issuance                      # higher = better, as factors.py:161
capital_discipline = z(neg_issuance)                  # factors.py:254, single input

ni     : us-gaap:NetIncomeLoss
cfo    : us-gaap:NetCashProvidedByUsedInOperatingActivities
                -> ...ContinuingOperations (fallback)
assets : us-gaap:Assets
accruals_q = -((ni - cfo) / assets)                   # Sloan, sign as fundamental_panel
```
All three of `ni`, `cfo`, `assets` must share the same fiscal `end` date or the row is missing,
not approximated.

### 4.6 `insider`
`insider.insider_detail(ticker, days=90)` **imported and called unmodified** — the already-fixed
scraper, including its refusal contract (`score = None` when filings were found and none could be
read, which is *not* a neutral 50). Then, exactly as `factors.py:271`:
`insider = (insider_score - 50) / 25`.

**Pre-committed truncation:** at most `MAX_FORM4_PER_NAME = 40` Form 4 documents per name inside
the 90-day window, most recent first. Mega-caps file more than that and fetching all of them for
500 names is not affordable at SEC's rate. Truncation is **recorded per name** (`form4_truncated`)
and the count of truncated names is reported beside every insider figure. It biases the
*magnitude* of `pressure`, not its sign.

## 5. COVERAGE DEFINITION AND THE FLOORS

A name **counts as covered for a theme** only when the theme's value for that name is
**non-null AND finite** after the construction above — for `institutional`, additionally after
the §4.4 anchor. Coverage is reported as a fraction of the **500 served rows**, never of the
subset that happened to fetch.

**PRESENT IS NOT USABLE — the Part 12 lesson, applied to my own instrument.** Every theme also
reports **`distinct_values`**. A theme with coverage 1.00 and `distinct_values == 1` is
**DEGENERATE and is reported as dead**, not as covered; that is exactly the state `insider` is in
today and exactly the hole this register's author had left open in `scripts/theme_health.py`
before Part 12 closed it.

Floors, both pre-existing project constants, applied unchanged:

| floor | value | source | meaning here |
|---|---|---|---|
| `COVERAGE_FLOOR` | **0.05** | `fundamental_panel.py:3833` | below this the signal is *effectively empty* |
| `MIN_COVERAGE` | **0.30** | `pead.py:121`, `elite13f.py:90` | the **adoption-relevant** bar |
| `MIN_DISTINCT` | **2** | `theme_health.MIN_DISTINCT_VALUES` | below this it carries no ranking information |

## 6. BOUNDS — committed before any of them can be evaluated

* **B1 — the institutional source is viable.** `institutional` coverage **≥ 0.30** of the 500.
* **B2 — the join is not making things up.** Of names matched to a CUSIP, **≥ 95%** pass the
  §4.4 anchor band.
* **B3 — external validity of the 13F aggregate, and it is falsifiable.** Holder breadth must
  behave like real institutional ownership: the most-held served name carries **≥ 2,000 distinct
  filers**, and **Spearman(`inst_breadth`, log market cap) > +0.30** across covered names. A
  mis-built aggregate would fail this even with perfect nominal coverage.
* **B4 — `capital_discipline` is revivable.** `capital_discipline` coverage **≥ 0.30** of the 500,
  with **`distinct_values` ≥ 2**.
* **B5 — nothing shipped changed.** `git diff --stat origin/main` for this run touches **zero**
  files under `valuation/`; asserted by a test that reads the repository, not by assertion in
  prose.
* **B6 — `insider` stops being a constant.** `insider` `distinct_values` **≥ 10** across the
  covered names. Coverage alone cannot satisfy this; the constant it replaces is 100% "covered".

An ambiguous result against any bound is a **NULL** for that bound, per RUN_RULES 6.

## 7. PREDICTIONS — written down first, because this project's directional calls keep being wrong

| # | prediction | confidence |
|---|---|---|
| P1 | `institutional` clears B1, coverage in **0.70–0.95** | 70/30 |
| P2 | The **authoritative** CUSIP rung carries most of the join; name-matching adds < 15pp | 65/35 |
| P3 | `capital_discipline` coverage is **LOWER** than `institutional` — ADRs and foreign private issuers file 20-F/6-K and are thin in `dei:EntityCommonStockSharesOutstanding` | 60/40 |
| P4 | `insider` clears B6 easily, **but ≥ 50% of covered names score exactly 50.0** (genuinely quiet), so the live theme will be a spike-at-neutral distribution rather than a spread one | 70/30 |
| P5 | Anchor failures concentrate in **multi-class and ADR** names | 60/40 |

The register's own track record is why these are here: P-predictions in this project have been
wrong more often than right, and V2F's was wrong again (fallback share predicted higher, measured
4.4%).

## 8. WHAT VOIDS THIS RUN

* Editing the matcher, the anchor band, the floors or the bounds **after** seeing any coverage
  number. Tightening is permitted and must be recorded in place; loosening is not.
* Reporting coverage over the fetched subset rather than all 500.
* Any edit under `valuation/**` (B5 is the test).
* Substituting a different served snapshot after §4.1 pinned this one.

## 9. TRIAL COST

**ZERO.** No hypothesis about returns is tested, no arm is selected, no weight is chosen. This is
a coverage census of data sources. Equity `N` stays **131** and the Deflated Sharpe chain is
untouched. A trial is charged if and when one of these columns is ever *selected into* the
composite — and that, per §1, is a different decision with a five-year price tag.
