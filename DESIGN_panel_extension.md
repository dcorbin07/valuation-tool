# DESIGN — THE PANEL-EXTENSION AUDIT

**Should the 69-date panel be rebuilt from Compustat/CRSP back to 1961 (or 1926 for prices)?**

**Date: 2026-08-26. ZERO TRIALS.** No hypothesis, no bar, no verdict against one, no outcome
statistic computed anywhere. Every number below is a fact about what data exists, what fields
are populated, and what the recorded MDEs already say — the `S25` / `MB15` / `W-14` class, where
a data question is answered by measuring the data rather than by running an arm.

---

## VERDICT

**NOT WORTH IT as scoped — a full-panel rebuild to 1961 or 1926.** Five independent measured
reasons, any one of which is close to sufficient, and they do not trade off against each other.

**WORTH A NARROW VERSION, and it is not the one the framing implies.** The narrow version is
**not** "more power for the underpowered family" — measured, that fails. It is the **drawdown /
crash family, on a 1985-or-1976 start, built as a SEPARATE INSTRUMENT and never spliced into the
69-date panel.** That is the one family where the current panel is *structurally incapable*
rather than merely underpowered.

**AND THE NARROW VERSION IS ITSELF GATED** on a cheap probe that must run first and can kill it:
whether a **DATED** `gvkey ↔ permno` link can be built on this account at all. If it cannot, the
answer collapses to a flat NOT WORTH IT and nothing further should be spent.

---

## 0. THE ONE-PARAGRAPH ANSWER

Compustat's 1961 start is **nominal**: measured on the fields our signals actually need, there
are **zero** usable firms in 1961, **four** in 1969 and 2,431 in 1973, so an extension buys
nothing before ~1973 and the cell-count gain **saturates at 2.84x**. That gain is worth
**1.69x on the MDE, not the ~2x a dates-only view suggests**, and it moves **three of twelve**
recorded underpowered nulls across their own detection threshold — two of them by under 10%,
and **none of the headline ones.** Meanwhile the standard CRSP–Compustat link is **DENIED** on
this account, and the substitute route attaches the wrong company's fundamentals to **43.39%**
of our tickers over a 1976-start window while looking perfectly clean from the side you would
check. Two of the seven weighted themes do not extend at all. And the window being added is the
window in which essentially every signal we use was **discovered** — while the genuinely
out-of-sample evidence the extension is supposed to buy has **already been bought, for free, by
X8.**

---

## 1. FIELD MAPPING

### 1.1 The load-bearing set is 24 columns, not 53

`NUMBER_THEME` carries **53** signals, but the seven **weighted** themes (0.125 each:
`value`, `quality`, `momentum`, `insider`, `capital_discipline`, `size`, `institutional`;
`low_risk`, `sentiment` and `growth` carry **zero**) take their means over **24 distinct
z-columns** — reproducing `E-1`'s AST-derived census exactly:

| theme | inputs actually averaged |
|---|---|
| value | earnings_yield, fcf_yield, ebit_ev, book_to_price, neg_ev_sales, neg_ev_ebitda, neg_ps |
| quality | roic, roe, op_margin, gross_margin, neg_leverage, gp_on_capital, fcf_margin, accruals_q, interest_cov, f_score |
| momentum | ret_12_1, ret_6_1, high_prox |
| capital_discipline | neg_issuance |
| size | neg_log_mktcap |
| institutional | inst_accum, sm_breadth |
| insider | insider_score |

The other 29 signals are **measured but unweighted**, so their availability changes no published
composite figure. Everything below is about the 24.

### 1.2 BUILDABLE FROM COMPUSTAT — and the first year each one actually is

Measured on `comp.co_ifndq` (the entitled point-in-time quarterly, 66 year-files 1961→2026,
2,467,490 rows already pulled to `D:\wrds\comp_pit`). First year every field a signal needs
clears **70% non-null**:

| first year | signals |
|---|---|
| 1961 | earnings_yield |
| 1962 | neg_ps |
| 1971 | neg_issuance |
| 1972 | book_to_price, roe |
| **1976** | **ebit_ev, gp_on_capital, gross_margin, interest_cov, neg_ev_sales, neg_leverage, op_margin, roic** |
| 1978 | neg_ev_ebitda |
| 1986 | accruals_q (binding field: `dpq` at 0.70) |

**1976 is the natural floor.** Before it the panel is a two-signal object: in 1961 `atq` is 1.3%
non-null, `ceqq` 0.4%, `cogsq` 0.0%, `dlcq` 0.0%, `lctq` 0.0%, `actq` 0.0%, `xintq` 0.0%. Only
`ibq` (76.7%), `revtq` (69.6%) and `txtq` (67.4%) are meaningfully present. **In 1966 `actq`,
`lctq` and `txpq` are still at 0.0% and `cogsq` at 3.0%.**

### 1.3 NOT BUILDABLE from the point-in-time table at all

**`oancfq`, `capxq` and `prccq` are absent from `co_ifndq` entirely.** Consequences:

* **`fcf_yield`, `fcf_margin` and `f_score` cannot be built from the PIT table.** They need
  `comp.fundq` — also entitled, also pulled-able, and **a different object**: `fundq` is the
  standard restated file. Mixing them means some signals are as-first-reported and others carry
  restatements, i.e. **a silent look-ahead in exactly the three fields that are hardest to get.**
* And on **any** route those three carry a hard floor unrelated to vendors: the statement of
  cash flows is **SFAS 95, effective 1987**. Before that the filing is a statement of changes in
  financial position and an operating-cash-flow series is a reconstruction, not a read.
* `prccq` is immaterial — `neg_log_mktcap` takes its price from CRSP, which is entitled to 1925.

### 1.4 DOES NOT EXTEND AT ALL — two of the seven weighted themes

* **`institutional` (12.5% of the weight).** `wrdssec_all.wrds_13f_holdings` is entitled and
  spans 1987→2025 with 103,984,958 rows, **and the census already measured that the span is a
  mirage**: the filing-manager count steps from **71 in 2012 to 3,457 in 2013** — a 49-fold
  step at the SEC's structured-XML mandate. Report dates carrying ≥1,000 managers: **50, the
  first being 2013-06-30.** An institutional-breadth signal is a statistic *about managers*; a
  date carrying ten managers cannot support one. **This theme is dead before 2013 in every
  product on this account, and no extension changes that.**
* **`insider` (12.5% of the weight).** Form 4 electronic filing became mandatory **June 2003**.
  Before that the record is paper.

**So a pre-2003 segment is a FIVE-theme composite and a pre-2013 segment is a SIX-theme one.**
Neither is the object any published figure describes — see §5.3, where that stops being a
caveat and becomes the structural argument.

### 1.5 THE DANGEROUS CLASS — silently a different signal under a different vendor

This is the class the brief correctly singles out, and it is the one that would not announce
itself. Each of these keeps its column name, computes cleanly, and answers a different question
on either side of the join date:

| signal | the substitution | why it is a different object |
|---|---|---|
| `accruals_q` | balance-sheet accruals (forced, since `oancfq` is absent) vs the cash-flow construction we ship | Sloan's two definitions disagree in sign on a material minority of firm-quarters. The PIT route **forces** the balance-sheet version; the modern panel uses the other. **Same name, two constructions, split exactly at the splice date.** |
| `neg_leverage`, `interest_cov` | Compustat `dlcq + dlttq` vs the modern `liabilities` | Operating leases entered the balance sheet at **ASC 842 (2019)**. Debt measured before and after is not the same quantity, and the break sits *inside* the current panel as well as at the splice. |
| `roic` | `icaptq` (Compustat invested capital) vs Sharadar `invcap` | Two vendor constructions of "invested capital" with different minority-interest and deferred-tax treatment. |
| `gross_margin`, `gp_on_capital` | Compustat `cogsq` vs Sharadar COGS | Vendors standardise cost of goods differently for firms that report a single expense line — which is most financials and many service firms. |
| EV components | `cheq` (cash **and short-term investments**) vs `cashneq` | A different numerator in every EV multiple. |
| `neg_issuance` | `cshoq` as-reported vs a split-adjusted share count | `U1-SPLIT` measured what an as-traded/adjusted mismatch costs elsewhere in this project: a fabricated **+31,921%** on one GE trade. |

**The honest reading: six of the twenty-four load-bearing columns would change definition at the
splice date, in ways that produce a clean number and no error.** That is `MA31`'s failure mode —
*a lookup computes cleanly and answers a different question* — reproduced six times, and it is
the reason a spliced panel is worse than two separate ones.

---

## 2. WHAT RE-DERIVES, PRICED

A new panel is not a longer version of this one; it is a new instrument, and **every bar
calibrated on the old one is void.**

**The six X7-calibrated floors, all of them.** Theme IC *t* 2.7072 · long-short *t* naive
2.1437 · long-short *t* HAC 2.2837 · top-decile alpha margin 1.8629pp · alpha HAC *t* 2.0540 ·
PBO p5 19.667%. Every one is a p95/p5 over **100 placebo draws pushed through the REAL pipeline**
(CPCV + weight selection + `quantile_backtest`) on *this* panel at 69 dates, H=63, lag 1.
Session 10's re-sweep of that machinery is the cost precedent, and it scales with cells.

**Everything built on those draws.** `MB31`'s staleness map is arithmetic on X7's banked
`(margin, se)` rows — void. The floor-flip trigger at equity `N` = 247 is defined against them —
void. `S22`'s eight per-horizon `fixed_weights_null` floors — void. `MB21`'s persistence null —
void. `X1`'s and `X5`'s bootstrap distributions — re-run.

**The canonical artifact.** `BACKTEST_RESULTS.json` carries **2,567 numeric leaves across 29
blocks**. Not all are headline, but `construction`, `portfolio`, `costs`, `benchmarks`,
`per_theme`, `per_signal`, `cpcv`, `multiple_testing`, `regime`, `holdout_validation` and
`walk_forward` all move.

**The record.** 325 `DONE` ledger rows and 100 committed registers. Not all rest on the panel —
the options family does not — but every equity verdict was scored against a bar in the list
above, so each needs triage for whether its verdict survives a moved floor.

**The one thing that does NOT move:** the Harvey–Liu–Zhu hurdle `sqrt(2 ln N)` is a function of
**trials**, not dates. It stays 3.3145 at equity `N` = 243 and the headline goes on failing it.

**Data acquisition, on top of analysis.** `comp.fundq` for the cash-flow fields (the `co_ifndq`
pull was 127 chunks / 0.68 GB; `fundq` is comparable). `crsp_a_stock.dsf` for 1973–2008 — the
existing pull holds **2008 onward only, 17 year-files**, so this is ~35 further years of daily
data across a 5,000–8,000-name tape. And **CRSP ends 2024-12-31 on this account** while the panel
runs to 2026-01-28, so an extended panel cannot reach the present without a second splice at the
*recent* end.

---

## 3. THE POWER GAIN, WITH MB22 ARITHMETIC — AND IT SATURATES

### 3.1 The gain is in name-date CELLS, not dates

For a per-date IC, `sd(IC) ~ 1/sqrt(n_names)` and the *t* over dates carries `sqrt(n_dates)`, so
`t ~ effect * sqrt(n_names * n_dates)`. **The MDE scales with `1/sqrt(CELLS)`.** A dates-only
view overstates the gain, because the early cross-sections are thin. Measured — firms with a
complete 1976-era core in `co_ifndq`:

```
1961      0        1973   2431        1993   8945        2013   9018
1965      0        1977   2840        1997  10777        2017   7978
1969      4        1985   7317        2005   9403        2021   7931
```

Applying our own selection share (113,945 cells / 69 dates = **1,651 names/date**, which is
**19.3%** of the 8,565 firms with a complete core in 2009):

| start | dates | names/date | total cells | x cells | **MDE80** | improvement |
|---|---|---|---|---|---|---|
| 2009 (today) | 69 | 1,651 | 113,945 | 1.00 | **0.4274** | — |
| 1985 | 165 | 1,788 | 285,584 | 2.51 | **0.2700** | 1.58x |
| 1976 | 201 | 1,524 | 315,150 | 2.77 | **0.2570** | 1.66x |
| 1971 | 221 | 1,383 | 324,149 | 2.84 | **0.2534** | 1.69x |
| **1961** | **261** | **1,095** | **324,163** | **2.84** | **0.2534** | **1.69x** |

**THE 1961 ROW IS IDENTICAL TO THE 1971 ROW.** Going back the further decade adds **14 cells**,
because Compustat has essentially no usable firms before 1973. **The brief's "CRSP reaches 1926,
Compustat 1961" is a catalogue fact, not a data fact.**

### 3.2 Which recorded nulls actually become interpretable

`ratio = observed effect / that item's own recorded MDE80`. A null becomes a detection when the
ratio reaches 1.00.

| item | domain | now | @1985 | @1976 | @1961 |
|---|---|---|---|---|---|
| E-6 temporal axis | panel | 0.01x | 0.02x | 0.02x | 0.02x |
| E-3 theme dispersion | panel | 0.05x | 0.08x | 0.08x | 0.08x |
| E-3 (basis seven) | panel | 0.31x | 0.49x | 0.51x | 0.52x |
| MB18 expectations gap | panel | 0.19x | 0.29x | 0.31x | 0.31x |
| D6 analyst revisions | panel | 0.20x | 0.32x | 0.34x | 0.34x |
| D6 (basis seven) | panel | 0.22x | 0.36x | 0.37x | 0.38x |
| **E-2 delta composite** | panel | 0.75x | **1.19x** | **1.25x** | **1.26x** |
| **V6 dip detector** | panel | 0.63x | 0.99x | **1.04x** | **1.05x** |
| **E-5 hazard, early half** | panel | 0.64x | **1.02x** | **1.07x** | **1.09x** |
| O-1 long puts | options | 0.22x | — | — | — |
| O-1 secondary | options | 0.38x | — | — | — |
| MB16 VPIN | options | 0.87x | — | — | — |

**Three of twelve cross at a 1976 start, and two of those three cross by under 10%** — inside
the sampling error of the MDE estimate itself, so they would arrive as *marginal* rather than as
resolved. **Not one of the headline nulls moves anywhere near**: D6 reaches 0.34x, MB18 0.31x,
E-3 0.08x, E-6 0.02x. Those items are not underpowered by a factor a longer panel can supply;
they are three to fifty times below detection.

**Every options null gains exactly nothing.** OptionMetrics is DENIED (`W-14` confirmed it, and
confirmed Cboe does not replace it), and our own chain caches begin in 2016. `O-1`'s 0.19% power
and `MB16`'s 0.87x are untouched by any Compustat/CRSP work at any price.

### 3.3 The family the record calls hopeless stays hopeless

`R1-VAR` / `RISK_PRIMARY_MAP`: Sharpe-primary needs **87 independent years** against the panel's
**14.7 effective from 18 calendar** — a measured 0.8167 effective years per calendar year.

| start | calendar | effective | vs 87 |
|---|---|---|---|
| 2009 | 18 | 14.7 | short by 5.9x |
| 1985 | 42 | 34.3 | short by 2.5x |
| 1976 | 51 | 41.6 | **short by 2.1x** |
| 1961 | 66 | 53.9 | short by 1.6x |
| 1926 | 101 | 82.5 | **still short by 1.1x** |

**The single most-repeated "underpowered by construction" complaint in the record is not fixed
by any feasible extension — not even by a hypothetical 1926 start that the data does not
support.** It is short at the theoretical maximum.

---

## 4. THE LINK — THE BINDING CONSTRAINT, AND IT IS MEASURED

**`crsp.ccmxpf_lnkhist` — the standard CRSP–Compustat link — is DENIED on this account.** So a
Compustat→CRSP join must go:

```
gvkey --( comp.security.tic , UNDATED )--> ticker --( crsp dsenames , DATED )--> permno
```

The undated leg is the weak one, and the damage grows with the window. Measured on the CRSP
name history (117,859 rows, 35,645 tickers, 37,860 permnos) against our own 2,317-ticker
Compustat link:

| window | our tickers seen in CRSP | naming **more than one company** | share |
|---|---|---|---|
| 2009–2024 | 2,171 | 218 | **10.04%** |
| **1976–2024** | 2,180 | **946** | **43.39%** |
| 1926–2024 | 2,180 | 1,013 | 46.47% |

**And the Compustat side reports 0.00% ambiguity — every one of the 2,317 tickers maps to exactly
one gvkey — because it is a snapshot with no date columns.** The contamination is therefore
**invisible from the side you would check.** A 1976-start join would attach one company's
fundamentals to a ticker that named a different company for part of the window, on roughly two
names in five, silently.

**And the project has already established that changing identifier column does not escape it.**
`ibes_events`, measuring the same failure on IBES: *"ESCAPING REUSE NEEDS A DATE, NOT A DIFFERENT
COLUMN. The first CUSIP-based fix collected every cusip CRSP had ever associated with a ticker
and re-imported the same contamination through another door."* It measured **17.7% of the rows
`oftic` offers belong to a different company** over a far shorter window.

This is the gate. Everything downstream is conditional on it.

---

## 5. THE TRAP, ARGUED

### 5.1 The extension window IS the discovery window

Our composite is not a novel signal. It is a **flat 1/7 blend of seven documented anomaly
families**, never tuned, and `R1` measured the book loading on the published factors (HML +0.251,
*t* +2.93; UMD +0.205, *t* +3.65). Every load-bearing column traces to a paper whose sample sits
inside the window an extension would add:

| signal family | canonical source | its sample |
|---|---|---|
| size | Banz 1981 | **1936–1975** |
| earnings yield | Basu 1977, 1983 | 1957–1971 |
| book-to-price | Rosenberg–Reid–Lanstein 1985; Fama–French 1992 | 1973–1984; 1963–1990 |
| momentum (12-1, 6-1) | Jegadeesh–Titman 1993 | 1965–1989 |
| 52-week high | George–Hwang 2004 | 1963–2001 |
| gross profitability | Novy-Marx 2013 | 1963–2010 |
| accruals | Sloan 1996 | 1962–1991 |
| F-score | Piotroski 2000 | **1976–1996** |
| net issuance | Loughran–Ritter 1995; Daniel–Titman 2006 | 1970–1990; 1968–2003 |
| asset growth | Cooper–Gulen–Schill 2008 | 1968–2003 |
| profitability / quality complex | Haugen–Baker 1996; Fama–French 2015; AFP QMJ | 1979–1993; 1963–2013; 1957–2016 |
| low beta | Black–Jensen–Scholes 1972; Frazzini–Pedersen 2014 | 1931–1965; 1926–2012 |

**The overlap with 1976–2008 is close to total.** Piotroski's sample *is* 1976–1996.

### 5.2 So what does a "confirmation" there actually mean

**A pass is very close to a tautology.** It would establish that our implementation reproduces,
in the data the papers were written from, effects the papers reported from that data. That is a
**fidelity check on our code** — genuinely valuable, and exactly what `M4`'s live-vs-backtest
replay is for — but it is **not evidence about the edge**, because the alternative hypothesis it
rejects ("these anomalies were absent in their own discovery sample") is one nobody holds.

**A fail would be informative, and about the wrong thing.** It would say our construction differs
from the published one — a statement about our vendor mapping and our 24 columns, not about
whether the edge is real.

**The asymmetry is the point, and this record has a name for it.** `V6-OPT` declared in advance
that its sample held one crash, so *"a decisive REJECT was available and a decisive ADOPT was
not."* Here it is inverted: **a decisive PASS is available and nearly worthless; a decisive FAIL
is available and answers a different question.** A design whose good outcome cannot inform you
should not be run for that outcome.

### 5.3 And the out-of-sample evidence has already been bought, for free

`X8` mapped the untuned composite 1:1 onto Global Factor Data with **no tuning of any kind** and
measured: **Japan +2.05%/yr (*t* 3.85)**, **developed Europe +3.36%/yr (*t* 4.30)**, world ex-US
+3.37% (*t* 5.03), **all 15 European countries positive and 12 of 15 clearing *t* > 2** — and the
control that makes it worth anything, **the USA is the WEAKEST region tested (*t* 2.35).**

That is out-of-sample in **vendor, country, construction and universe simultaneously**, and it
cost a CC BY-NC download.

**A US pre-1990 extension is out-of-sample in none of those dimensions.** Same country, same
vendor lineage — CRSP/Compustat is literally what the papers used — and the discovery period.
**Its marginal evidential value is strictly dominated by a route the project has already taken.**

The one genuinely un-mined slice is **1926–1956 for price-only signals**, and even that is
partly spoken for (Frazzini–Pedersen's BAB sample is 1926–2012; Banz starts 1936). It carries no
fundamentals at all, so it can speak only to momentum, size and low-risk — one of which is
weighted at zero.

---

## 6. REGIME — IS A 1965 CROSS-SECTION THE SAME OBJECT?

**No, and the sharpest form is arithmetic rather than argument.**

### 6.1 The tick alone exceeds the cost model

The minimum tick was **1/8 until June 1997** and **1/16 until April 2001**. A 1/8 tick implies a
minimum half-spread of $0.0625 — a floor of **625/P bps one-way**, before any spread, impact or
commission:

| price | min one-way | vs our **measured** 33.4 bps |
|---|---|---|
| $5 | 125.0 bps | 3.74x |
| $10 | 62.5 bps | 1.87x |
| $15 | 41.7 bps | 1.25x |
| $20 | 31.2 bps | 0.94x |

**The tick alone equals the entire 33.4 bps cost model at P = $18.71, and equals the 134.1 bps
top-decile breakeven at P = $4.66.** The book turns over **261%/yr** and pays it every time.

**And the added dates are mostly in that regime: 75.8% of the dates a 1976 start ADDS are
pre-decimalisation** (100 of 132), which is 49.8% of the resulting panel. At a 1961 start it is
83.3% of the added dates.

### 6.2 The information structure is different, and it is different for our signals specifically

* **Reg FD, 2000-10-23.** Selective disclosure was legal before it. Every earnings-, estimate-
  and analyst-derived signal — `pead_car`, `pead_drift`, `earn_rev`, `rating_rev` — is measuring
  a different diffusion process on either side of that date.
* **SOX, 2002.** Sloan's accrual anomaly is documented to have weakened afterwards; `accruals_q`
  is a weighted `quality` input.
* **The uptick rule, repealed 2007.** The long-short leg's short side was mechanically
  constrained for the whole added window.

### 6.3 The decisive structural point: it is not the same composite

Because `institutional` dies before 2013 and `insider` before 2003 (§1.4), and `fcf_yield`,
`fcf_margin` and `f_score` before ~1987 (§1.3):

* a **1976–2002 segment** is a **five-theme** composite, with `value` at 5 or 6 of 7 inputs and
  `quality` at 7 of 10;
* a **2003–2012 segment** is a six-theme composite;
* only **2013 onward** is the seven-theme object every published figure describes.

**`V2G` already measured what a restricted composite is worth, and the finding is not that it is
similar.** The four-theme live book gives up 1.31pp of alpha — *"not separable from zero"* — but
**fails the calibrated long-short floor at HAC *t* 1.8811 against 2.2837**, where the seven-theme
book clears at 2.6199.

**So a pooled 1976–2026 test does not measure a longer-run edge. It measures a composition change
confounded with a regime change, and reports it as one number.** That is the strongest single
reason not to splice, and it is independent of the link, independent of power, and independent of
the discovery trap.

---

## 7. THE NARROW VERSION

### 7.1 What it is

**One question: does the composite's drawdown and crash behaviour survive a multi-recession
sample?** Built as a **separate, named instrument** — its own placebo calibration, its own
floors, its own register — and **never spliced into the 69-date panel.**

**Why this one and not the others.** It is the only family where the current panel is
*structurally incapable* rather than underpowered:

* `S10` measured the book's worst peak-to-trough as spanning **exactly one 63-day period on
  every arm, at the same trough index 44 of 69 — COVID 2020Q1.** A name-level screen cannot move
  a market-wide quarter, and no amount of power fixes a sample with one event in it.
* `U3` had to declare its asymmetry in advance for the same reason.
* `MB8`, `E-5` and `V6-B` all touch crash behaviour and all are bounded by the same single event.
* **The panel begins 2009-01-15 — 53 days before the 2009-03-09 bottom — so it contains the
  final leg of the GFC decline and the entire recovery, and not the decline.**

A 1976 start adds **five NBER recessions** (1980, 1981–82, 1990–91, 2001, 2007–09) and three
genuine crashes (1987, 2000–02, 2008–09). A 1985 start adds four and all three crashes.

**And this is the one question the discovery trap does not touch.** Nobody published our
composite's drawdown profile in 1980s data; it is a property of this specific book, not a
documented anomaly. §5's argument simply does not apply here.

### 7.2 What it is explicitly NOT for

* **Not the incremental-IC family.** Measured: 3 of 12 cross, two by under 10%, and the four
  headline nulls reach 0.02x–0.34x. `D6`, `MB18`, `E-3` and `E-6` stay null and stay bounded.
* **Not the risk / Sharpe-primary family.** Measured: still 2.1x short at 1976 and 1.1x short at
  a 1926 start the data cannot supply.
* **Not options, at any price.** OptionMetrics denied; our caches start 2016.
* **Not a re-run of any landed equity verdict.** Every one was scored against an X7 floor
  calibrated on the current panel; re-scoring on a new instrument is a new claim needing a new
  register, not a confirmation.

### 7.3 The gate that must run first

**Can a DATED `gvkey ↔ permno` link be built on this account?** Zero trials, data-availability
class, roughly a day:

1. Probe `comp.security` / `comp.names` for **any** date column and for `cusip`.
2. Probe `crsp.stocknames` — **DATED, 83,280 rows**, already used by the 13F work at 89.7%
   coverage of our names.
3. On **2009–2024, where both routes are checkable**, measure the disagreement rate between the
   ticker route and any dated route on our own 2,531 names. That window is the positive control:
   a dated route that cannot reproduce the modern join is not one.
4. **Honour `ibes_events`' finding rather than re-learning it**: a CUSIP swap without dates
   re-imports the same contamination. The gate passes only on a route that is dated on **both**
   legs.

**PASS →** the narrow version is buildable and should be pre-registered on its own terms, with a
declared start (1985 is the better default than 1976: it gives 2.51x cells against 2.77x, loses
one recession, and buys a materially cleaner accounting and disclosure regime).
**FAIL →** flat NOT WORTH IT, and nothing further is spent.

---

## 8. WHAT THIS MEMO DOES NOT SAY

* **It does not say the data is unavailable.** Compustat 1961→2026, CRSP 1925→2024, IBES
  1976→2026 and 13F 1987→2025 are all entitled and mostly already pulled. **The blockers are the
  LINK, the FIELDS and the MEANING — not access.**
* **It does not say a longer panel would show nothing.** It says the specific gains claimed for
  it are measurably smaller than assumed, that the largest single claim (the risk family) is
  unreachable, and that the added window is the worst available window for confirmation.
* **It computes no outcome statistic and proposes no hypothesis.** Nothing here is a finding
  about returns, and the narrow version is a *scoped candidate* gated on a probe — not a
  register, and not a recommendation to run one.
* **It does not revisit the three DECISION items from Audit #5** (the fleet export door, the
  gates staleness bar, the test-book in the declared set), which remain Don's and remain open.

---

## 9. THE ONE THING TO CARRY FORWARD

**Power is a function of name-date cells, and this project has been reading it as a function of
dates.** The panel's 113,945 cells are 69 dates × 1,651 names. The largest honest extension
available reaches 324,163 cells — **2.84x, saturating in 1971** — which is worth **1.69x on the
MDE**. That moves three of twelve recorded nulls, two of them marginally.

Set against that: a 43% identifier contamination that is invisible from the side you would
check, two of seven themes that do not extend, six of twenty-four columns that change meaning at
the splice, three quarters of the added dates in a tick regime whose *floor* exceeds our entire
cost model, and a window that is the discovery sample of essentially every signal we use.

**The nulls in this record are not mostly a sample-size problem. They are mostly a
signal-strength problem** — `D6` at 0.20x of its own threshold, `E-3` at 0.05x, `E-6` at 0.01x —
**and a bigger panel does not fix a signal that is fifty times below detection.** The one place
the panel is genuinely too short rather than too weak is the crash sample, which holds one event.
That is the narrow version, and it is the whole of it.
