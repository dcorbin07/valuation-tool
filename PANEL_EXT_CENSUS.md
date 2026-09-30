# PANEL_EXT_CENSUS — MC12 Stage-1 census (zero trials, FACTS class)

Register: `PREREG_panel_ext_census.md`. Generated `2026-09-30T05:12:38+00:00`.

**No forward return, price return, IC or *t* is computed anywhere in this census** — pinned over the module's own syntax tree by `tests/test_panel_ext_census.py`. A PASS below means only *"a successor register on this route and start year is not blocked by data availability"*.

Data root resolved to `C:\Users\donni\Downloads\valuation-tool\data` (a worktree carries `data/` empty).

## The load-bearing set

**24 distinct z-columns, derived by AST** from the theme means rather than retyped.

`insider` contributes ZERO z-columns because factors.py maps it as a fixed affine (insider_score-50)/25, not a z-score. DESIGN 1.1's prose count of 24 is CORRECT and its table's 25th row is not a z-column.

| theme | z-columns |
|---|---|
| `capital_discipline` | `z_neg_issuance` |
| `insider` | *none* |
| `institutional` | `z_inst_accum`, `z_sm_breadth` |
| `momentum` | `z_high_prox`, `z_ret_12_1`, `z_ret_6_1` |
| `quality` | `z_accruals_q`, `z_f_score`, `z_fcf_margin`, `z_gp_on_capital`, `z_gross_margin`, `z_interest_cov`, `z_neg_leverage`, `z_op_margin`, `z_roe`, `z_roic` |
| `size` | `z_neg_log_mktcap` |
| `value` | `z_book_to_price`, `z_earnings_yield`, `z_ebit_ev`, `z_fcf_yield`, `z_neg_ev_ebitda`, `z_neg_ev_sales`, `z_neg_ps` |

## ROUTE S — the Sharadar freeze

`sf1` rows read **3,203,836**; ARQ rows kept at earliest-`datekey` **392,340**.

| year | names | K1 | failing themes (K2) | later-delist | timely `datekey` |
|---|---|---|---|---|---|
| 1995 | 965 | **FAIL** | `capital_discipline`, `insider`, `institutional`, `momentum` | 0.096 | 0.990 |
| 1996 | 2,718 | PASS | `capital_discipline`, `insider`, `institutional`, `momentum` | 0.239 | 0.985 |
| 1997 | 6,947 | PASS | `capital_discipline`, `insider`, `institutional`, `momentum` | 0.388 | 0.986 |
| 1998 | 7,797 | PASS | `insider`, `institutional` | 0.372 | 0.994 |
| 1999 | 7,936 | PASS | `insider`, `institutional` | 0.334 | 0.994 |
| 2000 | 7,536 | PASS | `insider`, `institutional` | 0.296 | 0.994 |
| 2001 | 6,899 | PASS | `insider`, `institutional` | 0.266 | 0.995 |
| 2002 | 6,432 | PASS | `insider`, `institutional` | 0.277 | 0.992 |
| 2003 | 6,177 | PASS | `insider`, `institutional` | 0.279 | 0.990 |
| 2004 | 6,081 | PASS | `insider`, `institutional` | 0.272 | 0.988 |
| 2005 | 6,064 | PASS | `insider`, `institutional` | 0.271 | 0.985 |
| 2006 | 5,972 | PASS | `insider`, `institutional` | 0.267 | 0.985 |
| 2007 | 5,866 | PASS | `insider`, `institutional` | 0.252 | 0.990 |
| 2008 | 5,555 | PASS | `insider`, `institutional` | 0.248 | 0.992 |

Shipped panel's own delisting reference, on MATCHED forward windows: **{'within_3y': 0.071065, 'within_3y_years_used': [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023], 'within_3y_n_years': 15, 'within_5y': 0.116189, 'within_5y_years_used': [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021], 'within_5y_n_years': 13, 'within_10y': 0.22072, 'within_10y_years_used': [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016], 'within_10y_n_years': 8}**.

### Verdict per candidate start year — Route S

* **1995 — FAIL** (failing: {1995: ['K1_names', 'K2_themes'], 1996: ['K2_themes', 'K3_survivorship'], 1997: ['K2_themes', 'K3_survivorship'], 1998: ['K2_themes', 'K3_survivorship'], 1999: ['K2_themes', 'K3_survivorship'], 2000: ['K2_themes', 'K3_survivorship'], 2001: ['K2_themes', 'K3_survivorship'], 2002: ['K2_themes', 'K3_survivorship'], 2003: ['K2_themes', 'K3_survivorship'], 2004: ['K2_themes', 'K3_survivorship'], 2005: ['K2_themes', 'K3_survivorship'], 2006: ['K2_themes', 'K3_survivorship'], 2007: ['K2_themes', 'K3_survivorship'], 2008: ['K2_themes', 'K3_survivorship']})
* **1999 — FAIL** (failing: {1999: ['K2_themes', 'K3_survivorship'], 2000: ['K2_themes', 'K3_survivorship'], 2001: ['K2_themes', 'K3_survivorship'], 2002: ['K2_themes', 'K3_survivorship'], 2003: ['K2_themes', 'K3_survivorship'], 2004: ['K2_themes', 'K3_survivorship'], 2005: ['K2_themes', 'K3_survivorship'], 2006: ['K2_themes', 'K3_survivorship'], 2007: ['K2_themes', 'K3_survivorship'], 2008: ['K2_themes', 'K3_survivorship']})
* **2000 — FAIL** (failing: {2000: ['K2_themes', 'K3_survivorship'], 2001: ['K2_themes', 'K3_survivorship'], 2002: ['K2_themes', 'K3_survivorship'], 2003: ['K2_themes', 'K3_survivorship'], 2004: ['K2_themes', 'K3_survivorship'], 2005: ['K2_themes', 'K3_survivorship'], 2006: ['K2_themes', 'K3_survivorship'], 2007: ['K2_themes', 'K3_survivorship'], 2008: ['K2_themes', 'K3_survivorship']})

## ROUTE W — CRSP / Compustat

`co_ifndq` manifest: **74 entries over 66 distinct chunks**, 0 non-ok, deduped rows **2,114,571**.

**co_ifndq has NO vintage column (only datadate), so no publication lag is verifiable and K4 cannot be run on this route. The datafmt/consol composition is reported instead.**

### The link

* `CONTAMINATED_CONTROL_undated_tic_to_gvkey` = 77461
* `comp_security_rows` = 77546
* `control_note` = the undated tic->gvkey route is W-28's contamination shape and is NEVER counted as coverage
* `cusip8_to_gvkey_pairs` = 71903
* `dated_intervals_with_gvkey` = 68767
* `dated_link_share` = 0.825732
* `stocknames_dated_rows` = 83280
* `stocknames_rows` = 83280

### `dsf` sizing — an estimate, never coverage

* `banked_years` = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
* `consequence` = every Route W statement about a price-dependent theme before 2008 is a SIZE ESTIMATE, not a coverage measurement
* `estimated_bytes_on_disk` = 34775888
* `estimated_rows` = 5606384
* `method` = linear extrapolation from ONE real year-chunk, as the task directs. The chunk is PANEL-RESTRICTED (1,607 permno, 4 columns), so two effects push the estimate opposite ways -- an extension needs names absent from today's panel (understates) while the pre-2008 cross-section is smaller than 2008's (overstates). NO DIRECTION IS CLAIMED.
* `reference_bytes_on_disk` = 2483992
* `reference_columns` = 4
* `reference_columns_names` = ['date', 'permno', 'prc', 'vol']
* `reference_distinct_dates` = 253
* `reference_distinct_permno` = 1607
* `reference_is_panel_restricted` = True
* `reference_rows` = 400456
* `reference_year` = 2008
* `years_required_and_ABSENT` = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007]

### Per-year `co_ifndq` line items below the 70% rule

| year | rows | gvkeys | below 70% |
|---|---|---|---|
| 1995 | 47,950 | 12,477 | `gpq`, `xintq`, `xsgaq` |
| 1996 | 48,578 | 12,516 | `gpq`, `xintq`, `xsgaq` |
| 1997 | 48,026 | 12,510 | `gpq`, `xintq`, `xsgaq` |
| 1998 | 50,065 | 13,117 | `gpq`, `xintq`, `xsgaq` |
| 1999 | 50,847 | 13,295 | `gpq`, `xintq`, `xsgaq` |
| 2000 | 49,728 | 12,979 | `gpq`, `xintq`, `xsgaq` |
| 2001 | 47,405 | 12,411 | `gpq`, `xintq`, `xsgaq` |
| 2002 | 45,774 | 11,913 | `gpq`, `xintq`, `xsgaq` |
| 2003 | 44,852 | 11,606 | `gpq`, `xintq` |
| 2004 | 44,128 | 11,441 | `gpq`, `xintq` |
| 2005 | 44,030 | 11,475 | `gpq`, `xintq`, `xsgaq` |
| 2006 | 43,844 | 11,449 | `gpq`, `xintq`, `xsgaq` |
| 2007 | 43,868 | 11,513 | `gpq`, `xintq`, `xsgaq` |
| 2008 | 43,420 | 11,346 | `gpq`, `xintq`, `xsgaq` |

## What this does not do

It builds no panel, adopts nothing, and licenses no trial. No outcome is computed, so no statement here bears on whether a pre-2009 edge exists.
