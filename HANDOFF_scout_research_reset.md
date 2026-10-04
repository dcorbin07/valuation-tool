# HANDOFF — Frontier Scout / RESEARCH RESET

**2026-10-03. Design only. ZERO trials, no measurement, no pull, no register committed.**
`by_domain` untouched — equity **252**, options **310**, unified **0**, infra **20**, re-read from
`research_log.detail()`. Nothing under `valuation/`, `scripts/`, `tests/` or `data/` is changed;
nothing in `D:\wrds` is written.

**Derived this session rather than quoted, because `CLAUDE.md` records both rotting:** equity
hurdle **3.3254862** at `N` = 252, and the live vintage — **vintage 4, OPEN, opened 2026-08-13**,
label *"no-trade band, width 0.30"*. Read from `track_meter.VINTAGES`. **Never quote a vintage
from a handoff, including this one.**

---

## A. THE CHARTER — `RESEARCH_CHARTER.md`

One page, seven clauses, binding on every future register. The metric is **net-of-trading-cost
return of a book the live scan can build, held in a Roth, against SPY, out of sample**; everything
else is a diagnostic that may block a claim and never establish one. It adds the **locked pre-2009
holdout** as a third inference layer behind both-halves, caps the program at **twelve further
equity arms**, and forbids any number reaching the site, a resume or a conversation without naming
its exact book.

**The clause worth arguing about is the cap**, so the reason is stated plainly in it: **252 arms
produced one measured product result — +1.95pp/yr vs SPY, +0.27pp in the recent half.** More arms
on the same seventeen years buy hurdle, not knowledge.

## B. THE TRUE OUT-OF-SAMPLE PERIOD — `PREREG_DRAFT_oos1_pre2009_holdout.md`

**The five-theme restriction is FORCED, and the two drops have different reasons that must not be
conflated.** `institutional` is **ABSENT** — Sharadar `sf3` has zero rows before 2009 (`MC12`
established it positively) and WRDS `tfn.s34` is **DENIED**. `insider` is **PRESENT AND UNUSABLE** —
the export runs back to **1980-11-25** but coverage is **0.001 in 1995 rising only to 0.307 by
2008** against a 70% rule, because electronic Form 4 filing began in 2003; `tfn.table1/table2`
are **DENIED** too.

The frozen model is specified column by column: **22 AST-derived z-columns across five themes at
0.2 each** — which is not a new weight but the deployed 0.125 renormalised by present mass, the
identity `V2G` proved at max |dev| **0.000e+00**, and whose cost `V2G` priced at **−1.3133pp/yr,
IMMATERIAL**.

**Census — what is banked versus what must be pulled.** Banked: `comp.co_ifndq` 2,114,571 rows
(578 MB, 1961–2026), `comp_security` 77,546, `crsp_stocknames` 83,280, `crsp_dsenames` 117,859,
`crsp_delist` 38,872, `crsp_msedelist` 38,843, `crsp_dsf_panel` **2008–2024 only and
panel-restricted**, IBES `det` **34,540,574** / `statsum` **15,029,492** / `act` 1,323,271 /
`id` 308,801 (all 1976–2026), `totalq` 485,746. **Row totals are deduped by chunk** — summing every
manifest entry double-counts `co_ifndq` by exactly **352,919**.

**Must be pulled, and only two things:**

1. **`comp.fundq` — ENTITLED, 1961-03-31 → 2026-07-31, 2,134,745 rows, NOT banked.** This is the
   whole reason the holdout needs a pull: **`co_ifndq` carries no availability date** (only
   `datadate` — no `rdq`, no `srcdate`, no vintage) and is **essentially 100% restated**, with just
   **53 `PRE_AMENDS` rows against 652,462 `STD`** in 1995–2008 and zero in 9 of 14 years.
   `fundq` carries **`rdq`**, which is the availability date. **Size ≈ 580 MB / ~66 chunks**, by
   pairing against `co_ifndq`'s banked 2.11M rows at 578 MB.
2. **`crsp.dsf` for the window** — ENTITLED to 1925; banked only 2008–2024 and **panel-restricted**
   (1,607 permno, four columns). **Size it from a real PRE-2009 year-chunk, not the banked 2008
   one**, because scaling across the time axis is where sizing goes wrong. Order **0.4–1 GB**
   against **341.6 GB free**. `crsp.msf` is the ~1/21 fallback but makes `high_prox` a 12-month
   approximation, **which voids "frozen" for one of 22 columns**.

**Linking.** CCM is **DENIED**. `crsp.stocknames`' **dated** intervals are the spine (import
`adv.py::ticker_permno_intervals`/`permno_on`, do not reimplement); `comp.security.tic` → gvkey is
94.9% but **UNDATED**, which is `W-3b`'s 17.7% contamination and `W-28`'s 54 wrong-company names, so
it is used **only via cusip**; and **`ncusip` (historical) must be used, never `cusip` (current)**.
**The pre-2009 route is easier than the modern one** because the universe comes from CRSP `permno`
directly, so `W-6`'s Sharadar suffix mismatch (179 of 199 unmatched names carrying `1`/`Q`
suffixes) cannot arise.

**Two design problems I would not have predicted and which the draft settles:**

* **The $10B threshold is NOMINAL** (`INDEX-BOOK`) and the tier therefore **widens over time** —
  eligible 227 / 542 / 822, book 23 / 54 / 82, already below `CONTRACT_MIN_POSITIONS` on **25 of
  69 dates**. Run backwards it **collapses**, and a holdout that degenerates to the `MIN_NAMES`
  fallback measures the fallback. **Primary declared now: a constant PERCENTILE tier**, with the
  nominal arm reported beside it carrying no verdict.
* **A VENDOR TRANSLATION CONTROL THAT COSTS NO LOOK, and it is the most important thing in the
  draft.** The holdout changes **vendor** as well as **period**, so the Compustat-built five-theme
  composite must first reproduce the banked Sharadar panel **on the 2009–2026 overlap** at mean
  per-date Spearman **≥ 0.90** — a bar inside the range `FIDELITY-2` (+0.9190 / +0.8726) and
  `THEME-RESTORE` (+0.8421) already treat as fidelity. **Below it the holdout is NOT opened**,
  because the result would measure the translation.

**Traps already measured, so nobody pays twice:** Compustat quarterly cash flows are **year-to-date**
(`oancfy`, `capxy`) and using them raw inflates Q4 ~4×; **`gpq` is 0.00% non-null** so gross profit
must be `revtq − cogsq`; **`xintq` 0.67 and `xsgaq` 0.69 sit below the 70% rule every year**;
CRSP's last interval must be **OPEN-ENDED** (`W-28` read the 2024-12-31 cut as a coverage gap);
delisting is a **terminal value** and censoring is not (`E-5`); survivorship must use a **matched**
forward window (`MC12` failed 13 of 14 years for want of one).

**WRDS restoration — what Don must check.** The rejection is PAM in **~1 second with no MFA
challenge**, against a credential **byte-identical** to the pgpass that worked 2026-08-28, on a
host that demonstrably recognises the account. **A connection waiting on Duo blocks for tens of
seconds, so no push is being sent and no retry will help.** In order: (1) log in at
`wrds-www.wharton.upenn.edu` as `dcorbin` — a forced change or expiry shows only there; (2) check
the account's **annual institutional re-validation**; (3) reset the password and update
**`WRDS_PASSWORD` in `.env`**, which is the only place, since pgpass is rewritten from it every
connect; (4) if web works and pgdata still fails, **ask support to clear a failed-login lockout**,
telling them an automated client made roughly **ten** failed attempts on 2026-09-30 during
diagnosis; (5) confirm **pgdata entitlement separately** from web access — this account's grant is
demonstrably partial (CCM, `tfn.s34`, `tfn.table1` all denied).

## B2. DON'S ADDITION 2 (2026-10-03) — WHAT IT CHANGED, AND A CORRECTION TO MY OWN RANKING

Addition 2 arrived while this was being written. It changed three things and **it exposed one
error of mine that matters more than anything else in this handoff.**

**(1) The holdout is now TWO eras, each read once** — US ~1972–1989 and 1990–2008 — **plus** a 2×2
build/check grid for new research (**2009–2019 × a fixed ticker half**, checked once on
**2020–2026 × the other half**, survivors getting one final pre-2009 look). The ticker half is
`X1`'s published `sha1(ticker) % 2` at **1266 / 1265**, which is sound precisely because `X1` is
the record's strongest positive result — halving the universe moved the centre not at all (200 of
200 half-books positive, minimum +0.04382). **Two eras buy replication at the price of per-era
resolution**: ~18 years each resolves ~2.8–3pp/yr rather than the ~2pp a single 37-year block would.
**Benchmark is S&P 500 TOTAL RETURN before SPY (1993); a backfilled SPY may never be quoted.**

**(2) A 1972 start needs backfill-bias handling, and `crsp.dsp500list` joins the pull list.** Early
Compustat added firms **retroactively, with history**, so the early cross-section over-represents
survivors. Three standard handlings are now in the draft — start at 1972, require a minimum
Compustat history before eligibility, and **report the eligible-name count per year and the share
entering with backfilled history so the bias is a number**. Plus `B6`'s inverted-universe signature
tested explicitly on both eras with a **matched** forward window. **Ken French's library (free,
factor-level, back to 1926-07) validates the build**: if our SMB/HML do not track French's over
1972–1989 the build is wrong and the era is not scored. **Licence binds — `CLAUDE.md` already ruled
French's series factor-level and "never a magnitude claim", so it may validate and may never appear
in a product figure.**

**(3) THE CORRECTION, AND IT IS MINE.** I ranked Part C with cross-sectional tilts first and
event-driven signals last. **`SEARCH_DOCTRINE.md` §1.4 — which was already in the repo and which I
should have read before ranking — says that is backwards.** It tabulates the searchable spaces:

| space | effective n | 80%-power MDE |
|---|---|---|
| equity panel cross-section | 69 → **58.65** | **0.4274–0.5071 SD** |
| **event time on the same panel** | **100s–1,000s** | **1.66pp at n_eff 400** |
| forward fleet | unbounded in time | ~60 paired fills ≈ 1–2 months |

Its own conclusion: *"the 80%-power MDE is approximately equal to the largest effect the panel has
ever contained. That space can essentially only detect signals as strong as the best signal already
in it. A merely good new signal is invisible there BY CONSTRUCTION"* — **and 245 of the equity
trials were spent there.**

**So the charter now carries clause 4b: every register separates "is the signal real" (event time,
high power) from "is the book worth holding" (charter clause 1, irreducibly weak), and says which
it answered.** The Part C ranking below is rebuilt on that basis.

## C. THE NICHE EDGES — RANKED, AFTER THE CORRECTION

**The thesis, in one line:** `INDEX-BOOK` decomposed the tier step and found **−4.1785pp/yr** of it
is *"the small-cap premium the tier declines to hold"* — the product forgoes it for **capacity**,
and a Roth book has no capacity problem (`P2`'s **$5.1B crowding cohort** is not binding at Don's
size).

**The thesis is unchanged and is measured:** `INDEX-BOOK` found **−4.1785pp/yr** of the tier step is
*"the small-cap premium the tier declines to hold"* — forgone for **capacity**, which a Roth book
does not have (`P2`'s **$5.1B** crowding cohort is not binding at Don's size).

**EVENT-TIME ARMS FIRST — the high-power space, MDE ~1.66pp at n_eff 400:**

| # | draft | why here | free kill likely to fire? |
|---|---|---|---|
| **1** | `N3` earnings-surprise drift, small caps, **IBES SUE in event time** | the high-power space; **`W-3b` already fixed the date hole** (IBES merged into `I-4`'s spine, 29 of 29 foreign issuers recovered, 186 of 186 covered, every date carrying a `date_sources` stamp); IBES banked **1976–2026** so it reaches **both** pre-2009 eras | no — the old 29% hole is largely dissolved; the new kill is spine coverage **inside the band**, which `W-3b` measured on the options universe only |
| **2** | `N8` **spin-offs** in event time | the only Part C arm whose result **cannot be restated as a factor loading** — a forced-seller event, not a tilt; events are **owned, dated and paired** (`spinoff` 565 / `spunofffrom` 565 / `spinoffdividend` 521, censused from ACTIONS) | **YES, probably fatal** — 565 is the ceiling across **all** history; the panel-window, in-band, usable count is unmeasured and event time's reference is n_eff 400 |
| **3** | `N4` clustered opportunistic insider buying | each cluster is a dated event, and `MB20`'s classifier is **already built and validated** (0.48715 against a published 0.4872) | **yes, more likely than not** — three restrictions on a 124,181-row purchase population |
| — | **`W-17` index add/delete** | **ALREADY DRAFTED 2026-08-28 and NEVER ADJUDICATED** — event time, declared a **closure purchase** with a pre-committed *"a null CLOSES this thread permanently"* and a self-declared **LOW** prior | **adjudicate W-17 as it stands; do NOT rewrite it.** I deliberately did not duplicate it |

**CROSS-SECTIONAL ARMS — the weak space where 245 trials already went. `N1` is the exception
because it is a BOOK question, not a signal-detection question, so the 0.4274 SD MDE does not
govern it:**

| # | draft | why here | free kill likely to fire? |
|---|---|---|---|
| **4** | `N1` small/mid-cap core + liquidity floor | its prize is **already measured** (−4.1785pp) and it asks a book question, not an incremental-IC question; `MC9` just built the $ADV instrument it needs | no — but buildability is real (served book < 50 names on **25 of 69** dates) |
| **5** | `N2` net issuance in small caps | `capital_discipline` is **one of only two themes clearing `X7`'s calibrated 2.7072**, at **+2.76**, and `S16`'s rank identity **does not bind a universe restriction** | no |
| **6** | `N5` **analyst neglect / low coverage** | the purest statement of the capacity thesis — the edge exists *because* institutions are not looking; `numest` from banked `statsum_epsus` (15.0M rows, 1976–2026) reaches both eras; **nobody has used the IBES COUNT**, only estimates | no — but `K2` is the **size costume** at `R6`'s own 0.60 bar, which `R6` itself withdrew on |
| **7** | `N6` **industry momentum** | a **point-in-time** industry route now exists for **both** periods — `co_hgic` from 1999 (`S25`) and, newly identified here, **CRSP's own `siccd` INSIDE the dated name intervals** for 1972–1998, free and already banked | no — but `K2` is the momentum costume at `E-1`'s 0.60 bar |
| **8** | `N7` **52-week-high proximity** | **`high_prox` is ALREADY one of the three shipped `momentum` z-columns**, so this is not a new signal on this panel — it is a decomposition question, and the weakest design in the list (no event, and it is the one arm that genuinely needs the **daily** CRSP pull) | no, but `P6`'s rule has five demonstrations against it |

**DISCARDED: estimate-revision drift in small caps.** `D6-REG` ran on the pulled IBES and was
rejected on both bases at **0.0867 SD against an MDE80 of 0.4274** — about **0.2× detection** on
what `CLAUDE.md` calls *"the best-covered incremental register ever run"*. **Restricting to small
caps cuts `n` and worsens IBES coverage, so the successor is strictly LESS powered than the test
that already failed.** There is no version of this that gets more resolvable by getting smaller.
`CLAUDE.md:7546-7547`'s "STAY PARKED … path is IBES via WRDS" is stale and `D6-REG` answered it.

**Two honest warnings about Part C as a whole, which I would not want lost:**

* **The "it was tested POOLED, the effect is in a subgroup" argument is correct AND it is exactly
  the argument that can excuse re-running anything until something clears.** It is the reason the
  charter's twelve-arm cap exists, and the reason every draft carries a free kill that is read
  first.
* **Three of the four are mostly BETA, not alpha.** The −4.1785pp is a size premium, and `R1`'s
  re-run found SMB **not significant** on the corrected panel (**+0.208, *t* +1.39**) for the
  long-short though the long-only book does load (**+0.691, *t* 3.89**). Each register must report
  the factor loading beside the return so a tilt is never published as an edge.

## D. THE PRIOR — `PRIOR_FOR_DON.md`

Plain words, for Don, no jargon: **a long-only book of US stocks, after cost, plausibly earns 0 to
2 percentage points a year over SPY — not five, not ten.** Success is **+1 to +2pp/yr net, on a
buildable book, surviving the pre-2009 holdout and continuing forward**; failure is the holdout at
or below the market, or the recent half's **+0.27pp** persisting. **A real 2pp edge needs ~30 years
to reach *t* = 2 against SPY**, the forward meter has **13.3% power at 60 months**, and the 46-year
pre-2009 holdout is the only sample long enough — which is why it is opened once.

## C2. THE CAP — HOW THE TWELVE ARMS SHOULD BE SPENT

Addition 2 asks for a cap as well as a ranking. The charter sets **twelve further equity arms**;
here is the proposed allocation, and **the point of writing it down is that four of the eight
candidates are expected to close for NOTHING.**

| allocation | arms | note |
|---|---|---|
| free kills first, on **all eight** | **0** | `N8`, `N4`, and the coverage legs of `N3` and `N5` may close at zero trials. Run every free kill before spending anything |
| event-time arms that survive their kill | **≤ 3** | `N3`, then `N8`/`N4` only if their censuses clear |
| `W-17`, adjudicated as drafted | **1** | already designed; it is a closure purchase, so its null is worth a trial |
| cross-sectional book arms | **≤ 3** | `N1` first (its prize is measured), then at most two of `N2`/`N5`/`N6` |
| `N7` | **0 for now** | it is a decomposition of a shipped column in the weakest space; hold it in reserve |
| **reserve** | **≥ 5** | kept for the frozen construction's own fidelity work and for whatever the free kills turn up |

**Spending fewer than twelve is the good outcome.** `SEARCH_DOCTRINE`'s complaint is that 245 arms
went into the space where *"a merely good new signal is invisible BY CONSTRUCTION"*; the way not to
repeat that is to let the free kills do the work and to stop.

## E. RECOMMENDED ORDER OF WORK

1. **Restore WRDS** (Part B §7) — nothing in Part B can move without it, and everything in Part B
   is designable without it, which is why the draft exists now.
2. **Run the FREE KILLS on all eight candidates.** Zero trials, no WRDS, no pull. On the arithmetic
   above, `N8` and `N4` probably close here, and that is the cheapest good outcome available.
3. **Adjudicate `W-17`**, which has been drafted and unexamined since 2026-08-28.
4. **Validate `MC9`'s $ADV instrument**, which has never been wired. `MB15`'s rule: the instrument
   before the hypothesis.
5. **Then `N3` in event time** — the high-power space, on an IBES SUE, with `W-3b`'s spine filtered
   to `date_sources` in {`ibes`, `both`} so the 23.3% of name-years where code 22 is broader than
   earnings do not contaminate it.
6. **Then `N1`'s book question**, against the charter's metric.
7. **Pull `comp.fundq` + `crsp.dsf`/`msf` + `crsp.dsp500list`**, build the pre-2009 eras, and run
   the **French factor sanity check** and the **vendor-translation control** — both of which cost
   **no holdout look**.
8. **The eras last, in order, each read once**, after a construction is frozen and published.

## F. NOT DONE

No measurement of any kind. No pull. No register committed — every `PREREG_DRAFT_*` is a draft and
an executor must commit one **ALONE** before it becomes one. **No free kill was run, including the
ones I expect to fire.** The holdout is **UNOPENED**, which is its entire value. `IDEAS_LEDGER.md`,
`SEASON3_MAP.md` and `CLAUDE.md` are **not edited**; no trial is booked; `by_domain` is untouched at
equity **252**.

**Two things I could not establish and am not asserting:** whether `fundq`'s `rdq` coverage is
adequate in the holdout window (it is `K3` in Part B and needs the pull), and whether `MC9`'s $ADV
instrument is correct (it has never been wired, which is why validating it is step 3 and not an
assumption).

## G. FILES

`RESEARCH_CHARTER.md` (amended by Addition 2) · `PREREG_DRAFT_oos1_pre2009_holdout.md` (amended) ·
`PREREG_DRAFT_n3_smallcap_pead.md` (amended, promoted to rank 1) · `PREREG_DRAFT_n8_spinoffs.md` ·
`PREREG_DRAFT_n4_smallcap_insider_cluster.md` · `PREREG_DRAFT_n1_smallcap_core.md` ·
`PREREG_DRAFT_n2_smallcap_issuance.md` · `PREREG_DRAFT_n5_analyst_neglect.md` ·
`PREREG_DRAFT_n6_industry_momentum.md` · `PREREG_DRAFT_n7_52week_high.md` ·
`PRIOR_FOR_DON.md` · this handoff.

**NOT written, deliberately:** a draft for S&P 500 additions/deletions —
`PREREG_DRAFT_w17_spdji_index_events.md` already covers it in event time and has never been
adjudicated. Rewriting it would be duplication.

---

# OOS1 PREPARATION — WRDS RESTORED, DATA PULLED, THE TWO GATES BUILT (2026-10-04)

**ZERO TRIALS. No register committed, no arm run, no construction scored, and the 1972-1998
holdout is UNOPENED.** `by_domain` untouched. Don's instruction was the preparation steps that
cost no holdout look, plus the two gates, and nothing beyond that was taken.

## 0. ONE CONNECTION ATTEMPT, AS INSTRUCTED — IT SUCCEEDED

Connected as `dcorbin` in **5 seconds**, and that single session was used for every sizing query
rather than opening a second. The account is healthy: the PAM rejection `MC12` recorded is
resolved by Don's reset and MFA login of 2026-10-04.

**Server-side counts, measured rather than estimated:**

| object | rows |
|---|---|
| `comp.fundq`, all | 2,145,041 |
| `comp.fundq`, 1972-2008 | 1,234,665 |
| `comp.fundq`, 1972-2008 with non-null `rdq` | 835,478 (**67.67%**) |
| `crsp_a_stock.dsf`, 1972-2008 | 62,672,078 |
| `crsp_a_indexes.dsp500list` | 2,064 |

## 1. `dsf` RATHER THAN `msf`, AND THE REASON IS THAT THE FROZEN MODEL STOPS BEING FROZEN

Sized from a REAL pre-2009 year-chunk rather than extrapolated, as instructed: **1995 is
2,113,712 rows at 18.272 bytes/row compressed**, so 1972-2008 is **~1.07 GB** — affordable.

`msf` was the sanctioned fallback and is **declined on a construction argument, not on size**:
`high_prox` is proximity to a **252-day DAILY high**. On monthly data it degrades to a 12-month
approximation, which makes that column a different column — and a frozen model whose columns are
redefined for the holdout is not frozen. The fallback is recorded as available and unused.

## 2. `dsp500list` CONFIRMS W-17's K1 AT SOURCE

Banked: **2,064 rows carrying exactly `start`, `ending`, `permno`.** Effective dates and **no
announcement date**. That is precisely `W-17`'s K1 firing condition, now confirmed at the source
rather than inferred — an index-event study in announcement time is **not buildable from this
table**, and a successor needs an announcement-date source this account does not have.

## 3. A PROVIDER, NOT A SECOND BUILDER — AND THAT CHOICE IS WHAT MAKES GATE B MEAN ANYTHING

`valuation/edge/compustat_provider.py` implements the provider interface and maps `comp.fundq` +
`crsp.dsf` onto the field names the **shipped** `build_fundamental_panel` already reads, so the
22 z-columns are computed by the shipped formulas.

Re-implementing those formulas against Compustat names would have been a second definition of
the composite — **`B7`'s defect** — and it would have made the gate **uninterpretable**: a low
rank correlation could then be a vendor difference OR my arithmetic, with no way to separate
them. **The only surface that can be wrong is the field mapping, and Gate B measures exactly
that.**

`roe`, `roic`, `assetturnover` and `beta` are deliberately left **ABSENT** so the builder derives
them, because supplying a vendor value would mean the holdout arm and the training arm used two
different definitions of one signal — a `B7` split inside the very comparison meant to detect one.

## 4. THE AVAILABILITY RULE IS DECLARED IN ADVANCE, AND THE HOLDOUT-ERA NUMBER IS WORSE THAN THE DRAFT ASSUMED

`rdq` is the announcement date — the thing `co_ifndq` has none of and the reason `fundq` had to be
pulled at all. **Measured on the banked file, USD + INDL/STD/C/D, per era:**

| era | rows | `rdq` non-null | clears the 70% rule? |
|---|---|---|---|
| **holdout 1972-1998** | 741,543 | **0.5899** | **NO** |
| r1's Sharadar window 1999-2008 | 401,411 | 0.8321 | yes |
| overlap 2009-2026 | 693,029 | 0.6568 | no |

**The 1972-2008 figure of 67.67% understated the problem for the era that matters: inside the
holdout it is 58.99%**, so the fallback governs more than 40% of rows. It is declared **before
any outcome exists**: a null `rdq` becomes usable at `datadate + 90 days`, and every row carries
`datekey_source`, so the two populations can never be mixed silently. An `rdq` **preceding its own
period end** is treated as a vendor error rather than an early filing (536 such rows in the
holdout era) — taking it would be a look-ahead of up to a quarter on exactly those rows.

### 4a. THE SHAPE OF THE SHORTFALL IS THE FINDING, AND IT IS A CONFOUND TO DECLARE

| block | rows | `rdq` |
|---|---|---|
| 1970-74 | 34,660 | 0.7718 |
| 1975-79 | 58,373 | **0.8942** |
| 1980-84 | 116,960 | **0.5271** |
| 1985-89 | 166,488 | 0.5076 |
| 1990-94 | 185,093 | 0.5392 |
| 1995-99 | 179,969 | 0.6253 |

**Coverage is BEST in the 1970s and collapses in 1980-84 as the row count doubles.** That is not
a vendor improving over time — it is the opposite, and it coincides with Compustat's coverage
expanding to many more small firms. **So the hypothesis — and it is a hypothesis, not a
measurement — is that the `rdq`-versus-fallback split is correlated with FIRM SIZE.** That
matters because `X3` measured `size` as carrying the composite's entire statistical significance,
so a size-correlated availability split is a confound OOS1 must report, not a nuisance. **It is
not measured here and must not be quoted as if it were.**

## 5. A PREMISE CORRECTION AGAINST MY OWN FIRST READING OF THE CENSUS

Five fields sit below the 70% rule in the holdout era: `xrdq` **0.1726**, `oancfy` 0.4017,
`prstkcy` 0.5350, `capxy` 0.5464, `sstky` 0.5471.

My first reading was that `sstky`/`prstkcy` at ~0.54 might cost `capital_discipline` — **a whole
theme at 0.2 weight.** **Refuted by reading the source rather than inferring:** `share_issuance`
is derived in `_yoy()` from **`sharesbas` year-over-year**, which maps to `cshoq` at **0.8709** in
the holdout era, the second-best-covered field. `sstky`/`prstkcy` feed nothing in the five-theme
model. **`capital_discipline` is buildable pre-1999.**

What the shortfall does touch: `oancfy`/`capxy` → `fcf`, `fcf_margin`, `accruals_q`, three of
`quality`'s ten inputs; and `xrdq` → `rnd`, which enters operating profit as
`op = rev - cor - sgna - rnd` **with an `or 0.0` default that OVERSTATES operating profit when R&D
is missing.** At 17% coverage that default governs 83% of holdout rows. The z-scoring is
within-date, so a bias common to every name on a date cancels; it bites only to the extent
R&D-reporting differs across names within a date, which it does. **Gate B is the instrument that
detects it, because Compustat `xrdq` is only 0.3085 in the overlap era too.**

### 5a. AND THESE ROW-LEVEL FIGURES ARE NOT PANEL-CELL COVERAGE — THE TELL IS THAT THEY RUN BACKWARDS

For most fields the **2009-2026** era reads LOWER coverage than **1972-1998** (`atq` 0.6641 vs
0.8150). Coverage cannot plausibly have got worse, so these row-level shares are **diluted by
rows the panel never scores** — the panel takes one row per firm per rebalance date.

That is `O-1`'s measured lesson, which applied a 75% alert-book figure to the panel and was
**~17x wrong**, and `W-1`'s rule that coverage must be measured on the population the arm is
scored on. **So no figure in §4 or §5 may be quoted as the model's coverage.** The real figure
comes from the built panel and is reported with the gates.

## 6. GATE A — VALIDATED ON THE REAL ERA, AND THE UNIVERSE FILTER IS PART OF IT

Scope declared rather than implied: **A1** the value-weighted market return against French's
`Mkt-RF + RF`; **A2** a size-sorted spread against `SMB`. **HML/RMW/CMA are NOT replicated**,
because a disagreement there would be ambiguous between our build and our replication of French's
method, whereas A1 and A2 are not: if the market return or the size sort disagrees, the prices,
returns, market cap or universe are wrong and nothing built on them is worth running.

**The universe filter is part of the gate, not a refinement.** French's market factor is ordinary
common shares (`shrcd` 10/11) on NYSE/AMEX/Nasdaq (`exchcd` 1/2/3), dated through the CRSP name
history. Raw `dsf` carries ADRs, REITs and closed-end funds, and A1 would then disagree **for a
reason that is not a defect in the build** — reading as a failure of the data when it was a
failure of the comparison. Routed through the provider so the gate and the holdout build share
ONE universe definition (`B7`).

**Measured on the banked early chunks:**

| window | months | A1 correlation | A1 mean abs diff | A2 corr vs SMB |
|---|---|---|---|---|
| 1971-1972 | 23 | **0.999998** | **0.000045** (4.5 bp/month) | **0.974455** |
| 1995 | 11 | 0.999998 | 0.000035 (3.5 bp/month) | 0.826454 |

**The CRSP market return reproduces French's to within a few basis points a month in the holdout
era.** A2's median split is not French's 2x3 NYSE-breakpoint construction, so its level is not
expected to match and the correlation is the check; it is stronger on 23 months than on 11, as a
noisier short window should be.

One month per window is lost by construction: the market weight is the **prior** month's cap,
because weighting by the same month's cap is a look-ahead that mechanically overweights whatever
rose. The full run recovers it from the preceding year.

## 7. A DEFECT OF MY OWN, AND ITS DIRECTION IS THE REASON IT MATTERS

The French loader divided by 100, because French's website publishes percent. But
`scripts/fetch_factors.py` **had already converted** — the parsed CSV stores `-0.0039` — so the
second division made the **1995 market return 0.03%/yr against a true ~37%.**

Gate A then read **correlation 0.999998 beside a 2.86pp mean absolute difference**, and the
honest reading of that pair is not "it nearly passes": **it would have reported a level failure of
a CRSP build that is correct, blaming the data for my arithmetic.** Caught by disbelieving a
number — a 0.03% market return in a year the index rose 37% — rather than by anything raising.

**The conversion is replaced by a REFUSAL.** Guessing the units is what went wrong, and both
guesses produce a clean, plausible, confidently wrong number; a loader that cannot tell percent
from decimal should stop. Pinned **non-vacuously in both directions**: the real decimal file must
be ACCEPTED and a percent-scaled copy of it must be REFUSED.

## 8. WHAT IS READY, AND WHAT REMAINS

**READY:** WRDS access; `comp_fundq` banked (**56 chunks, 0.27 GB, 2,085,986 rows, 16 min**),
including `piq` and `xrdq`, which a first pass omitted and which feed `roic`'s effective tax rate
and operating profit — a missing input would have made Gate B uninterpretable, so the pull was
re-run rather than patched; `crsp_dsp500list` banked; `crsp_stocknames` already banked (83,280
rows, 38,872 permnos, 1925-2024, dated `ncusip` 93.46%); the provider, both gates, **54 tests, 4
of 4 mutations caught with sources restored byte-for-byte**; Gate A validated on the real era.

**RUNNING:** `crsp_dsf` 1971-2024. **Gate A's full run and Gate B both wait on it** — Gate B
needs the 2009-2024 years to build the overlap panel. Resume with
`python -m scripts.oos1_gates --gate both`.

**THE ONE FURTHER PULL OOS1 NEEDS, named so it is not discovered later:**
**`crsp_a_stock.dsi`**, which carries `vwretd` and `sprtrn` — the charter's **S&P 500 total
return** benchmark for the pre-SPY era. It is a small table and is **NOT banked.** The
value-weighted index the provider builds from `dsf` is a **build-internal stand-in that no gate
statistic reads**, present only so the builder can run; **using it as the holdout benchmark would
be a deviation**, and that is stated in its own docstring and pinned by test.

**NOT DONE, named so it is not mistaken for done:** no register committed; no arm; **no
construction scored on 1972-1998**; the $10B threshold question OOS1 §1a calls its hardest
problem is untouched; the panel-cell coverage figures of §5a are not yet measured; and the
size-correlation hypothesis of §4a is a hypothesis.
