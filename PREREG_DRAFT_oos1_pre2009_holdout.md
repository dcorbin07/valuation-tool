# PREREG DRAFT — OOS1, THE PRE-2009 LOCKED HOLDOUT FOR THE FROZEN MODEL

**DRAFT. Frontier Scout, 2026-10-03. Design only — no measurement, no pull, ZERO trials.**
Charter clause 4, layer 3. **This is the only locked holdout the program has, it is opened ONCE,
and opening it to choose between constructions destroys it.**

---

## 0. WHAT IT IS FOR, AND THE ORDER OF OPERATIONS

The record's own count is that nearly every figure was tuned **and** measured on the same
**2009–2026** panel. Only `X8`'s international replication and a two-month forward track are
genuinely out of sample. A pre-2009 US period is the one large, clean, untouched sample available
on data we are entitled to.

**It is therefore opened LAST.** The order is binding: freeze a construction → publish it → record
the construction's hash and the date → **then** open the holdout and read it once. Reading it to
pick between candidates converts it into a second training set and there is no third.

## 0b. AMENDED BY DON'S ADDITION 2 (2026-10-03) — TWO ERAS, A 1972 START, AND A FACTOR SANITY CHECK

**The holdout is now TWO eras, each read ONCE: US ~1972–1989 and 1990–2008.** That is the single
most consequential change, and it is an improvement: two independent reads replace one, so a result
that holds in both is far stronger than one that holds in a single 46-year block, and a result that
holds in only one is `NOT_REPLICATED` rather than ambiguous.

**Benchmark: S&P 500 TOTAL RETURN before SPY exists.** SPY began trading in **1993**, so the
1972–1989 era and most of 1990–2008's first years have no SPY. **A backfilled SPY may never be
quoted**; the register names the splice date and reports the benchmark actually used per era.

**Why 1972 and not 1963.** Early Compustat carries a **backfill / survivor bias** that is the
best-documented data defect in this literature: Compustat added firms retroactively through the
late 1960s and early 1970s, and it added them **with history**, so the early cross-section
over-represents firms that survived long enough to be worth adding. The standard handling is
threefold and all three belong in the register:

1. **Start late enough.** 1972 is the conventional compromise — late enough that the retroactive
   additions are mostly behind the sample, early enough to be a genuinely different regime from
   2009–2026.
2. **Require a minimum Compustat history before a firm is eligible** (two years is conventional),
   so a firm newly backfilled cannot enter on its first retroactive row.
3. **Report the eligible-name count per year and the share of names entering with backfilled
   history**, so the bias is visible as a number rather than asserted away. **If the early years'
   name count rises implausibly fast, that IS the backfill and the era's start must move — which
   is a pre-committed response, not a post-hoc one.**

**A fourth, cheap and decisive check that this project's own history demands.** `B6` voided an
entire era of results because the panel's first third had an **inverted universe** — every name
present at an early cross-section was one that had already stopped trading. **The pre-2009 eras
must be tested for the same signature before anything is scored**, using a **matched** forward
window (`MC12` failed 13 of 14 years for want of one).

**FACTOR-LEVEL SANITY VIA KEN FRENCH'S LIBRARY, back to 1926-07, free.** Before the five-theme book
is scored, the register reproduces the standard factor returns (Mkt-RF, SMB, HML, RMW, CMA, MOM)
on the CRSP/Compustat build and compares them to French's published series per era.

* **This is an INSTRUMENT check, not a result.** If our SMB and HML do not track French's over
  1972–1989, the build is wrong and the era must not be scored — exactly the role `MC12`'s
  instrument validation played, and `MB15`'s rule that the instrument comes before the hypothesis.
* **LICENCE, and it binds**: French's library is free for research and is **factor-level**.
  `CLAUDE.md` already records the ruling for the analogous case — *"Kenneth French international
  factors are free but permission-gated and factor-level … never a magnitude claim"* — and
  `RUN_RULES` 0.2 makes a data constraint travel with any number derived from it. **French's series
  may validate our build and may never appear in a product figure.**

**`crsp.dsp500list` is ENTITLED and NOT banked**, and it is needed here for two distinct purposes:
the S&P 500 membership history that defines the pre-SPY benchmark's constituents, and the
add/delete event dates Part C's index-event thread needs. It is small — a membership table, not a
price file — and should be pulled in the same session as `fundq`.

---

## 1. THE FROZEN MODEL IS FIVE THEMES, AND BOTH DROPS ARE FORCED RATHER THAN CHOSEN

The deployed composite is seven weighted themes at 0.125 each. Two cannot be built before 2009,
**for two different reasons that must not be conflated**:

* **`institutional` is ABSENT.** Sharadar `sf3` carries **ZERO rows dated before 2009** — `MC12`
  established that positively by scanning the file for 1990s and 2000–2008 dates and finding none,
  not by inferring it from an empty filter. The WRDS substitute is **`tfn.s34`, which is DENIED on
  this account**. There is no route.
* **`insider` is PRESENT AND UNUSABLE.** The licensed export spans **1980-11-25 → 2026-07-24**
  (5,636,964 rows, `MA57`), so the data exists — but `MC12` measured coverage on the panel at
  **0.001 in 1995 rising only to 0.307 by 2008**, against the project's **70%** non-null rule,
  because electronic Form 4 filing became mandatory only in 2003. WRDS `tfn.table1/table2` are
  **DENIED** too. So it is dropped on **coverage**, not absence.

**The frozen five-theme model, stated exactly so it cannot drift:**

| theme | weight | z-columns (AST-derived, `E-1`'s census) |
|---|---|---|
| `value` | 0.2 | `earnings_yield` `fcf_yield` `ebit_ev` `book_to_price` `neg_ev_sales` `neg_ev_ebitda` `neg_ps` |
| `quality` | 0.2 | `roic` `roe` `op_margin` `gross_margin` `neg_leverage` `gp_on_capital` `fcf_margin` `accruals_q` `interest_cov` `f_score` |
| `momentum` | 0.2 | `ret_12_1` `ret_6_1` `high_prox` |
| `capital_discipline` | 0.2 | `neg_issuance` |
| `size` | 0.2 | `neg_log_mktcap` |

**22 z-columns.** `low_risk`, `sentiment` and `growth` carry zero weight and are out of scope.
**0.2 is not a new weight** — it is the deployed 0.125 renormalised by present-weight mass, which
is what `composite_from_frame` already does, and `V2G` proved that identity at max |dev|
**0.000e+00** over all 113,945 rows. `V2G` also priced the cost of dropping themes this way: its
four-theme book cost **−1.3133pp/yr**, **IMMATERIAL** at paired HAC *t* −1.4040. **So the
five-theme restriction is a measured-small change, not an unknown one.**

**Plus the served construction's knobs**, because charter clause 1 says the metric is a book the
scan can build: the **$10B tier**, **score-weighted**, **8% cap**, **0.30 no-trade band**, quarterly
63-day rebalance, costs charged, Roth (no tax).

### 1a. THE $10B THRESHOLD IS THE DESIGN'S HARDEST PROBLEM AND IT MUST BE SETTLED FIRST

`INDEX-BOOK` records that **$10B is NOMINAL exactly as live, with no inflation adjustment**, and
that the tier therefore **WIDENS over time**: eligible **227 / 542 / 822** and book **23 / 54 / 82**
across the 2009–2026 panel, with the book already below `CONTRACT_MIN_POSITIONS` = 50 on **25 of
69 dates, all early**.

**Run backwards, a nominal $10B threshold collapses the book.** In the early 1990s very few US
firms exceeded $10B, so the pre-2009 book would be a handful of names or would sit permanently on
the `MIN_NAMES` fallback — which `INDEX-BOOK` notes never fired once on the modern panel. **A
holdout that degenerates to a 10-name fallback book is measuring the fallback, not the model.**

**PRIMARY, declared now: hold the tier at a constant PERCENTILE of the CRSP cross-section**, set so
it reproduces the live rule's own realised eligible counts on the overlap period. That keeps the
economic rule constant, needs no external price index, and is the only version that is the *same
rule* in 1990 and 2026.

**Reported beside it, carrying no verdict:** the nominal $10B arm, **with its book sizes printed on
every date**, so the degeneracy is visible rather than argued; and a CPI-deflated arm as a
sensitivity if a price series is obtained. **Choosing among these three after reading the holdout
is a void condition** — the percentile version is the primary, fixed here, before any pull.

## 2. THE DATA — EXACTLY WHAT IS BANKED AND WHAT MUST BE PULLED

### Banked on `D:\wrds` today (censused read-only, 2026-10-03)

| directory | rows (manifest, deduped) | span | size |
|---|---|---|---|
| `comp_pit` (`comp.co_ifndq`) | **2,114,571** | 1961–2026 | 578 MB |
| `comp_security` | 77,546 | — (UNDATED) | 2 MB |
| `crsp_stocknames` | 83,280 | — (DATED intervals) | 2 MB |
| `crsp_dsenames` | 117,859 | — | 3 MB |
| `crsp_delist` (`dsedelist`) | **38,872** | — | 1 MB |
| `crsp_msedelist` | **38,843** | 1926–2024 | 1 MB |
| `crsp_dsf_panel` | — | **2008–2024 only** | 45 MB |
| `ibes_det_epsus` | **34,540,574** | 1980–2026 | 505 MB |
| `ibes_statsum_epsus` | **15,029,492** | 1976–2026 | 156 MB |
| `ibes_act_epsus` / `actu_epsus` | 1,323,271 each | 1976–2026 | 17 / 16 MB |
| `ibes_id` | 308,801 | — | 3 MB |
| `totalq_total_q` | 485,746 | 1950–2025 | 14 MB |

**The row totals are deduped by chunk.** Six `co_ifndq` years (2021–2026) were re-pulled with
identical counts, so summing every manifest entry double-counts by exactly **352,919** and gives
`DESIGN_panel_extension.md`'s 2,467,490 instead of the correct 2,114,571 (`MC12`).

### What must be pulled

1. **`comp.fundq` — THE ONE THAT MATTERS. ENTITLED, 1961-03-31 → 2026-07-31, 2,134,745 rows,
   NOT BANKED.** This is the standard academic route and it is the reason `co_ifndq` cannot be
   used: **`MC12` measured that `co_ifndq` carries NO availability date** — its only date-like
   column is `datadate`, there is no `rdq`, no `srcdate`, no vintage — and it is **essentially
   100% `STD` (restated basis)**, with only **53 `PRE_AMENDS` rows against 652,462 `STD`** across
   1995–2008 and **zero in 9 of the 14 years**. A panel built on it would score history against
   *restated* fundamentals. **`fundq` carries `rdq`, the earnings announcement date, which is the
   availability date the holdout needs.**
   **Size: ~2.13M rows ≈ `co_ifndq`'s 2.11M, which is 578 MB in 66 gzipped year-chunks — so
   expect ~580 MB and ~66 chunks.**
2. **`crsp.dsf` for the holdout window. ENTITLED 1925-12-31 → 2024-12-31; banked only 2008–2024
   AND panel-restricted** (the banked `dsf_2008` is **1,607 permno** over 253 dates in **four
   columns**, i.e. `dsf` narrowed to the shipped panel's names, not a CRSP year).
   **SIZE IT FROM ONE REAL PRE-2009 YEAR-CHUNK, NOT FROM THE BANKED 2008 ONE.** Scaling across the
   time axis is exactly where sizing goes wrong — a cross-section count differs by era, and the
   record's own lesson is that pairing beats sampling. The banked chunk gives the unit
   (**6.20 bytes/row** on disk); a full-CRSP year is several times 1,607 names, so the order is
   **0.4–1 GB** for ~45 years. `D:` has **341.6 GB free**, so cost is a pull window, not space.
   **FALLBACK, and its price: `crsp.msf` (monthly) is ~1/21 the size and is sufficient for
   quarterly returns and for `ret_12_1`/`ret_6_1` — but NOT for `high_prox`, which is proximity to
   a 252-day DAILY high. Taking msf makes one of 22 z-columns a 12-month-high approximation, which
   is a construction deviation and VOIDS the word "frozen" for that column.** State which was
   pulled.
3. **Nothing else.** Delisting returns are banked (`dsedelist` daily, `msedelist` monthly, both
   38.8k rows). Name history is banked. IBES is banked and is **not** used by the five-theme model
   — it belongs to Part C.

### Linking — CCM is DENIED, and the pre-2009 route is EASIER than the modern one

`crsp.ccmxpf_lnkhist` is **DENIED on this account**, so the standard link is unavailable. The
substitutes, in the order the holdout should use them:

* **`crsp.stocknames` — DATED intervals** (`namedt` / `nameenddt`, `permno`, `ticker`, `ncusip`,
  `cusip`). This is the spine. `W-3b`'s scoping is already implemented as
  `valuation/edge/adv.py::ticker_permno_intervals` / `permno_on` and must be **imported, not
  reimplemented** (`B7`).
* **`comp.security.tic` → `gvkey`** at **94.9%** of panel names (`WRDS_CENSUS`) — **but UNDATED**,
  which is `W-3b`'s lease hazard at **17.7% contamination** and `W-28`'s measured failure of
  assigning a gvkey CRSP dates to a **different company on 54 names**. **So it is used only via
  cusip, never via ticker.**
* **USE `ncusip` (the HISTORICAL cusip), NEVER `cusip` (the CURRENT one).** Linking on the current
  cusip attributes a company's modern identity to its historical rows and is a silent
  misattribution of exactly `W-28`'s shape.

**The pre-2009 holdout avoids the hardest part of the modern linking problem entirely**, because
the universe is built from CRSP `permno` directly and never from a Sharadar ticker — so the
vendor-suffix mismatch that cost `W-6` its first answer (109 trailing-digit and 70 trailing-`Q`
tickers CRSP does not use, 179 of 199 unmatched names) **cannot arise here.**

## 3. TRAPS THAT ARE ALREADY MEASURED, SO NOBODY PAYS FOR THEM TWICE

* **Compustat quarterly cash-flow items are YEAR-TO-DATE, not quarterly** (`oancfy`, `capxy`, and
  the `…y` family). Q1 is the YTD value; Q2–Q4 need `YTD_t − YTD_{t−1}`. Using the raw YTD figure
  silently inflates Q4 by roughly 4× and corrupts `fcf_yield`, `fcf_margin` and `accruals_q`.
  **Pin it with a test that a Q4 row differs from its Q3 row.**
* **`gpq` is 0.00% non-null throughout 1995–2008** (`MC12`), so `gross_margin` and `gp_on_capital`
  must be derived from `revtq − cogsq`. `DESIGN_panel_extension.md` §1.2's "first year 1976" for
  those two is reachable only by the derived route.
* **`xintq` (~0.67) and `xsgaq` (~0.69) sit BELOW the 70% rule in every year 1995–2008** (`MC12`),
  so `interest_cov` is at risk on this route independently of anything else, and the register must
  report the theme's non-null share rather than assume it.
* **CRSP's last name interval must be treated as OPEN-ENDED.** `W-28` read the vendor's
  2024-12-31 cut as a coverage gap, saw per-date coverage of exactly zero on 2025–26 rows, and had
  to repair its instrument mid-item. `adv.py`'s `OPEN_END` handling already does this.
* **Delisting returns must be applied, and censoring is not delisting.** `E-5` measured the
  distinction: a delisted name has a **terminal value** (its last close), while an administrative
  end of data **censors** — and conflating them silently deleted 16 crashes, 5 of them flagged.
  Both delisting files are banked; use them.
* **Survivorship, on a MATCHED forward window.** `MC12` paid for this: comparing a cohort's
  unbounded later-delisting share against the panel's ever-delisting share put a ~29-year window
  against a ~17-year one and "failed" 13 of 14 years for that reason alone.

## 4. THE CONTROL THAT MUST PASS BEFORE THE HOLDOUT IS OPENED — AND IT COSTS NO LOOK

**Build the Compustat/CRSP version of the five-theme model on the OVERLAP period (2009–2026) and
require it to reproduce the banked Sharadar panel.** The holdout is a different **vendor** as well
as a different **period**, and a translation of 22 z-columns into Compustat's field names is a
construction change wearing a data change's clothes.

**Bar, pre-committed: mean per-date Spearman between the Compustat-built composite and the banked
Sharadar composite ≥ 0.90 on the overlap, with the per-date minimum reported.** Below that, **the
holdout is not opened**, because a failing translation means the pre-2009 result would measure the
translation and not the model. This control is **free of the holdout** — it reads only the overlap,
which is already training data — and it is the single most important thing in this design.

Reference points for the bar: `FIDELITY-2` cleared theme rebuilds at Spearman **+0.9190** and
**+0.8726**; `THEME-RESTORE` cleared at **+0.8421**; `MC10` measured score-weighted vs
equal-weighted at **rho 0.9968**. So 0.90 is inside the range this project already treats as
fidelity and is not a bar invented for convenience.

## 5. BAR, MDE AND WHAT THE HOLDOUT CAN ACTUALLY RESOLVE

**The metric is charter clause 1: net-of-cost return of the five-theme served-construction book vs
SPY, long-only, Roth.** Not alpha against the equal-weighted universe; not long-short.

**MDE, and it is the number that decides whether this is worth doing.** The served book's
measured vs-SPY edge is **+1.9488pp/yr** full-sample and **+0.2702pp** in the recent half, at a
tracking error the forward contract measured as **11.401 pp/yr** implying an information ratio of
**~0.88/yr** at the published decile and far less at the served book. **At a 2pp/yr edge and
~11pp/yr tracking error, a *t* of 2 needs roughly 30 years.** A 1963–2008 holdout is **46 years**,
which is the first design in this project's history that is *long enough*.

**So the honest pre-commitment is that the holdout can resolve an edge of about 2pp/yr and
cannot resolve one of 0.5pp/yr**, and the register must print the arithmetic from the realised
pre-era tracking error before reading the verdict.

**Per Addition 2 the benchmark is S&P 500 TOTAL RETURN before SPY exists** (SPY began 1993),
built from `crsp.dsp500list` membership plus CRSP returns, with the splice date named and the
benchmark used reported **per era**. A backfilled SPY may never be quoted. **And splitting 37
years into two eras of ~18 each costs power**: each era alone resolves roughly 2.8–3pp/yr rather
than the ~2pp a single 37-year block would, so **the two-era design buys replication at the price
of per-era resolution** — a trade worth making, and one the register must state rather than
discover.

## 6. KILLS, ALL FREE OF THE HOLDOUT

* **K1.** The overlap fidelity control of §4 fails → **the holdout is not opened.**
* **K2.** The percentile tier cannot reproduce the live rule's realised eligible counts on the
  overlap → the tier definition is wrong and must be settled before any pull.
* **K3.** `fundq`'s `rdq` coverage in the holdout window falls below a pre-committed floor → fall
  back to a **fixed filing lag** declared in advance (`datadate` + one quarter), and **report
  which rows used which**, because a mixed-availability panel is two panels.
* **K4.** Cross-sections below the shipped panel's own **1,471–1,954** range, or a book that sits
  on the `MIN_NAMES` fallback on more than a pre-committed share of dates → the construction
  degenerates and the result is about the fallback.
* **K5.** The 22 z-columns' non-null shares, per year, against the 70% rule. `interest_cov` is the
  known risk (§3).

## 7. WHAT DON MUST CHECK TO RESTORE WRDS

`MC12` recorded the login rejected by **PAM in about one second with no MFA challenge**, against a
credential **byte-identical** to the one in `%APPDATA%\postgresql\pgpass.conf` written 2026-08-28
when WRDS demonstrably worked. The host is reachable and allowlisted — a `dbname=postgres` probe
returns `no pg_hba.conf entry for host …, user "dcorbin"`, which proves the server recognises the
account. **A connection genuinely waiting on Duo blocks for tens of seconds, so a 1-second
rejection means no push was ever issued and no retry can fix it.**

In order:

1. **Log in at `wrds-www.wharton.upenn.edu` with username `dcorbin`.** A forced password change or
   an expiry notice appears there and nowhere else.
2. **Check the account's annual re-validation.** WRDS accounts lapse when the subscribing
   institution's validation expires; the web login will say so.
3. **Reset the password**, then update **`WRDS_PASSWORD` in `.env`** (13 characters today). The
   `pgpass` file is rewritten from `.env` on every connect, so `.env` is the only place to change.
4. **If the web login works and pgdata still rejects, ask WRDS support to clear a failed-login
   lockout** — and tell them the truth: an automated client made roughly **ten** failed attempts
   on 2026-09-30 while being diagnosed, which may itself have tripped it.
5. **Confirm pgdata entitlement specifically.** Web access and `wrds-pgdata` access are separate
   grants; the census's own denials (`tfn.s34`, CCM) show this account's grant is partial.

**Nothing in Part B can be pulled until this is restored. Everything in §1–§6 is designable
without it, which is why this draft exists now.**

## 8. VINTAGE AND SCOPE

**No vintage consequence** — this measures a frozen model on a historical period and adopts
nothing. It cannot adopt: the model being tested is *already* the shipped one minus two themes
that do not exist pre-2009.

**NOT DONE:** no pull, no build, no measurement, no look at the holdout. The holdout remains
**UNOPENED**, which is its value.
