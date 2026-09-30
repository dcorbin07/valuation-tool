# PREREG — MC12, PANEL EXTENSION STAGE-1 CENSUS

**Audit session: AUDIT 6. Item: MC12 / `PANEL-EXT-CENSUS`. Class: FACTS (zero trials).**

This register is committed **ALONE**, markdown only, zero `.py`, before
`scripts/panel_ext_census.py` exists. It is a strict git ancestor of every commit that
computes any figure it declares.

---

## 0. WHAT THIS IS, AND WHAT IT CANNOT BECOME

A **census**: facts about what data exists, per theme and per calendar year, on two candidate
routes to a pre-2009 panel. It is the `WRDS-CENSUS` / `W-28-PULL` / `S25` class.

**It has no hypothesis, no arm, no bar on any outcome, and computes no forward return.**
`by_domain` must be **bit-identical** before and after, re-read from `research_log.detail()`
rather than quoted. Measured at this register's commit:

```
by_domain = {'equity': 248, 'options': 310, 'unified': 0, 'infra': 20}
rows_fixed_not_counted = 84 ; rows_domain_unresolved = 0 ; rows_malformed = 0
```

A kill firing here means **the successor register is not attempted on that route/start year**.
No kill scores an outcome, and nothing here licenses the extension as a trial — the manager's
§6 already closed that (at n≈110 the headline has 49% power at the hurdle; independently
reproduced in §4 below at **49.5%**).

---

## 1. DECLARED DEVIATION — THE RECONCILIATION SUBSTITUTE

The task says *"Reconcile every pulled chunk against the server's `count(*)`."* **The WRDS
login is not usable at this register's commit**: `wrds-pgdata.wharton.upenn.edu:9737` accepts
the socket and completes TLS, the host is allowlisted (a `dbname=postgres` probe returns
`no pg_hba.conf entry for host …, user "dcorbin"`, which proves recognition), and the
credential is **byte-identical** to the one in `%APPDATA%\postgresql\pgpass.conf` written
2026-08-28 when WRDS demonstrably worked — yet PAM now rejects it in **~1 second with no MFA
challenge**. That is a server-side credential or lockout state, not a fault of this lane.

**Every table this census needs is already banked on `D:\wrds` and no live query is required.**
So the reconciliation is against **`D:\wrds\manifest.jsonl`** — which records `rows`, `bytes`,
`sha256` and `status` per chunk, captured at pull time against the server — and the manifest's
counts are themselves verified against the on-disk frames. This substitution is **declared, not
glossed**: it establishes that the file on disk is the file the server returned, and it does
**not** re-establish that the server's table has not changed since 2026-08-28.

Verified before this register was committed:

| object | on disk | brief declares | verdict |
|---|---|---|---|
| `crsp_a_stock.dsedelist` | 38,872 | 38,872 | **MATCHES** |
| `crsp_a_stock.dsenames` | 117,859 | 117,859 | **MATCHES** |
| `crsp.stocknames` | 83,280 | — | present, dated |
| `comp.security` | 77,546 | — | present |
| `comp.co_ifndq` | 66 year-files, 1961→2026 | 1961→ | present |
| `crsp.dsf` | **2008→2024 only (17 chunks)** | sized, not pulled | see §2.3 |

All pickles are **gzip-compressed despite a bare `.pkl` extension**, so `pd.read_pickle` must be
called with `compression="gzip"` — it infers none from the extension and fails with
`UnpicklingError: invalid load key, '\x1f'`.

---

## 2. SCOPE (fixed now)

### 2.1 The load-bearing set

The seven **weighted** themes (0.125 each): `value`, `quality`, `momentum`, `insider`,
`capital_discipline`, `size`, `institutional`. `low_risk`, `sentiment` and `growth` carry zero
weight and are **out of scope** — their availability changes no published composite figure.

The z-column set is **DERIVED from the theme means by AST** in STEP 1, not retyped, and the
derived count is **printed and asserted**. It is not taken from `DESIGN_panel_extension.md`
§1.1, because that section is internally inconsistent — see §6.1.

### 2.2 ROUTE S — the Sharadar freeze (same vendor as the shipped panel)

`data/backtest_freeze_2026-08`: `sf1` ARQ with **earliest-`datekey`** point-in-time selection,
`sep`, `daily`, `actions`, and the **RAW bulk** layer (including delisted tickers) — explicitly
not only the 3,735-name derived export. This is the route `DESIGN_panel_extension.md` never
considers (§6.2).

### 2.3 ROUTE W — CRSP/Compustat

`comp.co_ifndq` for fundamentals; `crsp.stocknames` **DATED** intervals → cusip8 →
`comp.security` → gvkey, exactly as `W-28` built it, with the last CRSP interval treated as
`OPEN_END` past the 2024-12-31 cut. The **naive undated ticker route is reported BESIDE the
dated one as the contaminated control** (`W-28`'s shape) and **never as coverage**.

**Route W's price leg is SIZED, never measured, and its verdict is CONDITIONAL on a pull that
has not happened.** `co_ifndq` carries **no price column** (`prccq` absent), so every
price-dependent theme — `size`, all of `value`'s ratios, both `momentum` columns — needs
`crsp.dsf`, which is banked **only for 2008→2024**. The 1994–2007 `dsf` requirement is
therefore sized by extrapolation from the **real 2008 year-chunk** already on disk, as the task
directs. Any Route W statement about a price-dependent theme before 2008 is a **size estimate,
not a coverage measurement**, and must be labelled so in the artifact.

### 2.4 Grid

Per weighted theme × per calendar year **1995–2008**, both routes. PASS/FAIL is reported per
route per candidate start year **1995, 1999, 2000**.

---

## 3. KILLS — written now, bars set from the SHIPPED panel's own distribution, never relaxed

The shipped 69-date panel's own facts, which are where every bar below comes from:
cross-sections **1,471–1,954**; `institutional` coverage **71.7%**; the project's **70%
non-null** rule; and the panel's own later-delisting share, **measured from ACTIONS in STEP 1
and printed** (a property of the incumbent, not of the extension, so measuring it does not
read extension data).

**K1 — names per rebalance date.** An extension date must carry **≥ 1,030 scoreable names**,
derived as 70% of the shipped panel's own **minimum** cross-section (1,471 × 0.70 = 1,029.7,
rounded up). Consequence: a year whose dates fall below this is not offered as a start year on
that route.

**K2 — per-theme non-null share per year, on LINKED names only.** Each weighted theme must
clear **70%** non-null in a year to count as available that year. A theme failing K2 is
**absent from the extension composite for that year**, and the register states in advance that
this is itself a finding: a pre-2009 composite missing a theme is **not the seven-theme shipped
composite**, so an extension built on it is not a clean extension of the published figure.
`institutional` and `insider` are expected to fail early (§5).

**K3 — universe survivorship.** For each extension date, the share of names that **later
delist** must lie within **[0.5×, 2.0×]** of the shipped 69-date panel's own measured share.
**Both tails fail**: above 2.0× is the inverted-universe (`B6`) signature — the defect that
voided the old 110-date panel — and below 0.5× is survivor-only. Consequence: a failing year is
not offered as a start year on that route.

**K4 — PIT provenance.** *On Route S*: the share of SF1 rows per year whose **earliest
`datekey`** precedes `reportperiod + 120d`, compared against the same statistic computed on
**2009–2013** rows. A shortfall of more than **10 percentage points** against the 2009–2013
reference fails, because that is what vendor backfill looks like. *On Route W the same test
cannot be run and that is a finding, not an omission*: `co_ifndq`'s only date-like column is
**`datadate`** (the fiscal period end) — there is no `rdq`, no `srcdate`, no vintage of any
kind — so the table records **no date at which a row became available**. Its point-in-time-ness
is carried by `datafmt` (`STD` vs `PRE_AMENDS`) and `consol` (`C`/`P`/`R`) instead, which
distinguishes as-first-reported from restated **without dating either**. Route W's K4 therefore
reports the `datafmt`/`consol` composition per year and **explicitly records that no
publication lag is verifiable from this table**; a fixed assumed lag is not a substitute and is
not adopted.

---

## 4. POWER LINE (A11) — derived, not retyped

For the **successor** this census gates, at `effect = 0.11038` (the **shipped post-2009**
top-decile figure, used as an **optimistic bound** — this census sets no bar on it) and
`se = 0.04213 × sqrt(69/n)`, via `power_gate.state(..., n_trials=248)` at the HLZ hurdle and at
the current LS-HAC placebo floor **2.056680** (N=247, `W-1`):

| n | se | HLZ 3.3207: 50% / 80% | power @ effect | floor 2.0567: 50% / 80% | power @ effect |
|---|---|---|---|---|---|
| 69 | 0.042130 | 0.139900 / 0.175289 | 24.2% | 0.086648 / 0.122037 | 71.3% |
| 105 | 0.034152 | 0.113409 / 0.142097 | 46.5% | 0.070241 / 0.098929 | 88.0% |
| 110 | 0.033367 | 0.110801 / 0.138830 | **49.5%** | 0.068626 / 0.096654 | 89.5% |
| 125 | 0.031301 | 0.103941 / 0.130234 | 58.1% | 0.064377 / 0.090670 | 92.9% |
| 140 | 0.029577 | 0.098215 / 0.123060 | 66.0% | 0.060830 / 0.085675 | 95.3% |

`hlz_hurdle(248) = 3.3206712412`, reproducing the brief's 3.3207. The n=110 HLZ power of
**49.5%** independently reproduces the manager's own §6 arithmetic ("at n≈110 the headline has
49% power at the hurdle") from a different route, which is the control on this table.

**Read the two bars as what they are.** At the hurdle the successor is a coin flip even if the
pre-2009 effect equals the post-2009 one. At the placebo floor it looks well powered — but that
floor is calibrated for the **69-date** panel and becomes an **extrapolation** at any other n,
needing its own ~5–7 h sweep. No number in this table licenses the extension.

---

## 5. EXPECTATIONS, WITH ODDS

1. **Route S clears K1 for 1999 and 2000 and fails it for 1995** — 70/30. The freeze's `sep`
   starts 1997-12-31 and `daily` 1998-12-01, so 1995 has no price layer on this route at all.
2. **`institutional` fails K2 in every year 1995–2008 on both routes** — 90/10. Sharadar SF3
   13F coverage begins ~2013 and `co_ifndq` carries no ownership at all.
3. **`insider` fails K2 in every year before 2003** — 75/25. Electronic Form 4 filing became
   mandatory in 2003.
4. **K4 fires on Route S for at least one year in 1995–1999** — 60/40. Early SF1 history is the
   most likely place for vendor backfill.
5. **Route W's dated link clears 80% of panel names** — 65/35, inherited from `W-28`'s measured
   94.9% on `comp.security.tic` and `W-3b`'s dated-interval work.
6. **THE ONE I EXPECT TO BE WRONG: K3 passes on both routes for 2000** — 40/60. I expect the
   raw bulk layer to be survivor-tilted enough to fail the lower tail, because a vendor's
   historical file is assembled from names it still tracks. If it passes, the delisted-ticker
   bulk layer is doing more work than I credit it with.

---

## 6. PREMISE CORRECTIONS FOUND BEFORE THIS REGISTER WAS COMMITTED

**6.1 `DESIGN_panel_extension.md` §1.1 says "24 distinct z-columns" and its own table lists 25,
with no duplicates.** Counted: value 7, quality 10, momentum 3, `capital_discipline` 1, `size`
1, `institutional` 2, `insider` 1 = **25 listed, 25 distinct**. One of the two figures is
wrong. This census therefore **derives the set by AST from the theme means** and asserts the
count it derives, rather than trusting either number. Reported, not edited — the memo is not
this lane's file.

**6.2 The `co_ifndq` row-count discrepancy in the manager's §7.3 is SETTLED, and it settles
against `DESIGN`.** `DESIGN` quotes **2,467,490**; `WRDS_CENSUS.md` quotes **2,114,571**. The
manifest holds **74 `co_ifndq` chunk entries for 66 year-files**, because six years (2021–2026)
were re-pulled, each time returning an **identical** row count. Summing all 74 entries gives
**2,467,490** — `DESIGN`'s figure — and summing the **last pull per year** gives **2,114,571**,
exactly the census figure. The difference is **352,919**, entirely re-pulled years.
**`WRDS_CENSUS.md`'s 2,114,571 is correct; `DESIGN`'s 2,467,490 double-counts the re-pulls.**
Verified against the frames themselves: 6 of 6 sampled years (1961, 1995, 2000, 2008, 2022,
2026) match the manifest's recorded rows exactly, so the manifest is the on-disk truth.
`DESIGN`'s own sentence pairs the correct **file** count (66) with the double-counted **row**
count in one clause, which is how it went unnoticed.

**6.3 Two line items sit below the 70% rule in 2000 on Route W**, measured before any bar was
set: `xsgaq` **69.35%** and `xintq` **67.04%** non-null. `interest_cov` depends on `xintq`, so
that quality input is at risk on Route W independently of anything K2 finds about the theme
mean. Also `gpq` is **0.00%** non-null in 2000, so `gross_margin` and `gp_on_capital` cannot be
taken from it and must be derived from `revtq − cogsq`; `DESIGN` §1.2's "first year 1976" for
those two signals is only reachable by the derived route.

---

## 7. VOID CONDITIONS

This item is void, and nothing in it may be quoted, if any of the following happens:

1. Any `fwd_ret`, price return, information coefficient or *t*-statistic is computed anywhere
   in the census path. **Pinned by an AST test** over `scripts/panel_ext_census.py`.
2. Any row of `BACKTEST_RESULTS.json` is touched.
3. Any raw row leaves `D:\wrds` or `data/` — no licensed row is committed, and neither
   `data/`, `*.pkl` nor anything under `D:\wrds` is added to git.
4. Any published verdict is re-read or re-derived.
5. `scripts/placebo.py`, the backtest, or any sweep is run.
6. A kill bar declared in §3 is relaxed after reading the data it applies to (`W-28`'s closing
   lesson), or a start year is offered on a route whose kill fired.
7. `by_domain` is not bit-identical before and after.

---

## 8. WHAT THIS DOES NOT DO

It does not build a panel, adopt anything, or license the extension as a trial. It offers no
verdict on whether the pre-2009 edge exists — **no outcome is computed**. A PASS here means
only *"a successor register on this route and start year is not blocked by data availability"*,
and a successor still needs its own blind register, its own trial charge, and — per the
manager's §6 — an answer to the fact that every X7 floor becomes an extrapolation off 69 dates.

Deliverables: `scripts/panel_ext_census.py` → `PANEL_EXT_CENSUS.md` (tracked) and
`D:\wrds\PANEL_EXT_CENSUS.json` (per-row banked, rule 9). Ledger row `PANEL-EXT-CENSUS`,
zero trials, FACTS class.
