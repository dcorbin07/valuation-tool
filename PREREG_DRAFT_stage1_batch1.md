# PREREG DRAFT — STAGE-1 BATCH 1 — twelve arms on the build quadrant

**THIS IS A DRAFT AND NOT A REGISTER. ZERO TRIALS. Nothing here is committed as a
pre-registration, nothing is measured, no arm is run, and no trial is booked.** A register is a
separate file committed **ALONE** (markdown only, zero `.py`, a strict git ancestor of every
measurement commit). Drafting is design; the register is the commitment. `RESEARCH_CHARTER.md` §3.

**The protocol is `RESEARCH_CHARTER.md` §5 as amended by Don's ruling of 2026-10-06
(`DECISIONS.md`): no cap on tests.** This is the first Stage-1 batch under it.

---

## 0. WHAT A STAGE-1 ARM IS, AND THE THREE THINGS THAT ARE FIXED BEFORE ANY ARM RUNS

* **PANEL — the corrected full raw universe**:
  `data/free_analysis/UNIVERSE_BIAS_PANEL_full.pkl`, exported by `scripts/universe_bias_prep.py`
  from `data/backtest_freeze_2026-10/raw`. **NEVER `data/backtest`** — that directory is the top
  3,000 by **2026** `scalemarketcap`, i.e. selection on a present-day property, and
  `UNIVERSE-BIAS` measured the cost at a **sign reversal, +7.24pp to −4.14pp**.
* **QUADRANT — build only**: **2009–2019 × `sha1(ticker) % 2`**, one fixed half. The check
  quadrant (2020–2026 × the other half) is **not looked at in Stage 1 at all**, and looking at it
  to choose among these twelve would spend it with no replacement.
* **BOTH HALVES INSIDE THE BUILD QUADRANT**: 2009–2014 / 2015–2019, boundary embargoed. An arm
  clearing one half is `NOT_REPLICATED` and does not reach Stage 2.

### 0a. THE BATCH IS TWELVE ARMS AND ITS MEMBERSHIP IS FIXED HERE

**Benjamini-Hochberg at q = 0.10 across `k` = 12.** The *i*-th smallest *p* is compared against
*i* · 0.10 / 12:

| i | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| threshold | .00833 | .01667 | .02500 | .03333 | .04167 | .05000 | .05833 | .06667 | .07500 | .08333 | .09167 | .10000 |

**Membership is fixed in this draft and carried verbatim into the register, because choosing
afterwards which arms "were in the batch" is how BH is gamed.** An arm that cannot be built is
reported as **NOT RUN** and `k` **stays 12** — shrinking `k` after a build failure makes every
surviving threshold easier, which is the same gaming in a different direction.

### 0b. AND BH DOES NOT APPLY TO EVERY ARM, WHICH THE CHARTER REQUIRES BE DECLARED

**This project's bars are mostly MARGINS, not *p*-values.** §6 forbids inventing a *p* so a
method applies, and `R1-VAR` is the precedent: X7's calibrated figure is a **detection**
threshold and was used as a **preference** threshold, which is a category error. So:

* **IN THE BH SET** — the arms whose primary statistic is an incremental information coefficient
  with a *t* and a defensible two-sided *p*: **A1, A2a, A2b, A3, A6, A7, A9, A10, A11**. Nine.
* **EXCLUDED FROM THE BH SET, JUDGED ON A PRE-COMMITTED MARGIN ALONE, EXCLUSION DECLARED
  HERE** — **A4** (a filter, gated on a crash-rate *ratio* in both halves per `MA28-CARD`),
  **A5** (blocked, see §5), **A8** (an event-time drift arm whose bar is its own permutation
  p95). Three.
* `k` **= 12 for the honest reason**: all twelve are *tests* and all twelve are booked in the
  research log, so all twelve raise the Harvey-Liu-Zhu hurdle and the Deflated Sharpe denominator
  whether or not BH can score them. **Counting and BH are different instruments; removing the cap
  removed a budget, not the counter.** BH is applied to the nine it can score and the ladder above
  is computed on `k` = 12, which is the conservative direction.

---

## 1. A1 — INTANGIBLE-ADJUSTED VALUE *(Eisfeldt-Kim-Papanikolaou 2022; Peters-Taylor 2017)*

**Mechanism.** Book equity omits internally generated intangible capital, so a research- or
brand-intensive firm looks expensive on `book_to_price` when it is not. Capitalise it and the
value theme sorts on a less mismeasured denominator.

**Construction.** Peters-Taylor perpetual inventory on **Sharadar SF1**, which matters:
`rnd` and `sgna` are **both already in `WRDSProvider._KEEP["fundamentals"]`** (verified in
`valuation/edge/data_providers.py`), so **no panel rebuild and no new source column**.
`K_int = K_know + K_org`, where `K_know` accumulates `rnd` at δ = 15% and `K_org` accumulates
**30% of `sgna`** at δ = 20%, both annual, with a burn-in before a name is scoreable. Adjusted
book = `equity + K_int`; the arm replaces **`z_book_to_price`** inside the value theme.

**WHY SHARADAR AND NOT COMPUSTAT, AND THIS IS THE WHOLE REASON THE CANDIDATE IS LIVE.** `W-28`
died on its `K1`: a **90% DATED Compustat-linkage bar is not reachable on this account** —
**81.54% of cells / 88.34% of names**, with **57 of 69 dates below the bar and the best date not
reaching it** — while the undated route that *would* have cleared at 97.01% assigns one `gvkey`
another company's dates on **54 names**. Building from SF1 means **there is no linkage to clear**.

**THE TRAP `W-28` LEFT FOR EXACTLY THIS ARM, AND IT IS MANDATORY.** The value theme is
`df[cols].mean(axis=1)` and **pandas skips NaN**, so a row whose replacement column is absent
averages **three inputs instead of four** — *demonstrably identical to the theme with
`book_to_price` DROPPED, which is `S1`'s removal arm, which `S1` measured as making the composite
WORSE (−0.207 alpha / −0.079 *t*)*. Unhandled, the arm is a **mixture of re-measurement and
removal, contaminating toward a negative result**. **So where `K_int` is unavailable the row falls
back to the INCUMBENT `book_to_price`**, which makes the paired difference exactly zero there,
leaves the population unchanged, and makes the identity
`composite_new − composite_old = w · (z_adj − z_inc)` hold **exactly** rather than conditionally.

**FREE PRE-OUTCOME KILL (`K1`).** On the build quadrant's own scoreable rows, the share with a
computable `K_int` after burn-in must be **≥ 0.70** (the project's non-null rule), and
**coverage is measured on the arm's own population, not on the panel** — `O-1` applied an
alert-book figure to the panel and was **~17× wrong**.

**AND THE KILL MUST SEPARATE ABSENT FROM ZERO, WHICH IS THIS CANDIDATE'S OWN HAZARD.** R&D is
**legitimately zero** for most firms, not missing. Counting a true zero as missing understates
coverage and sends the arm to the fallback for firms whose intangible capital really is ~0;
counting missing as zero silently asserts a fact. **`K1` therefore reports three numbers — truly
non-null, structurally zero, and absent — and the 0.70 bar is read on `non-null + structural
zero`.** A single "coverage" figure here would be the wrong object.

---

## 2. A2 — RESIDUAL MOMENTUM *(Blitz-Huij-Martens 2011)* — **TWO ARMS, AND THE REASON IS A PREMISE CORRECTION**

**The brief notes that `CONFIG.residual_momentum` exists with no recorded test. It exists, and it
is NOT the paper's construction.** Read at `valuation/screener/factors.py:285-292`: the shipped
toggle regresses the **momentum THEME z-score** on **beta**, **cross-sectionally, within one
date**, and keeps the residual. That is **beta-neutralisation of a composite theme**.
Blitz-Huij-Martens is a **time-series** regression of each stock's own returns on factor returns
over a formation window, taking the momentum of the **residual return series**, scaled by
residual volatility. **Different objects, and a register testing one must not be read as having
tested the other.** So both are registered, separately labelled:

* **A2a — THE SHIPPED TOGGLE.** `residual_momentum=True`. Costs nothing to build; it is a live
  code path that has never been scored, and leaving an untested toggle in a shipped scorer is its
  own small defect. **Free kill:** it must not be inert — the per-date rank correlation between
  the toggled and untoggled composite must be **< 0.995**, or the arm is reported `INERT` and
  carries no verdict. (`SECTOR-NEUTRAL-B6`'s inertness check, and `S15` which was *"nearly
  inert"* at 0.9879 and told us almost nothing.)
* **A2b — THE PAPER'S CONSTRUCTION.** 36-month formation window, residual of each name's monthly
  return on the **panel's OWN value-weighted market return**, built from the panel's prices; the
  signal is the *t*-statistic-scaled cumulative residual, skipping the most recent month.
  **Deliberately a ONE-factor residual, declared as a deviation from the paper's three.**
  **WHY: `AUDIT6_MANAGER_BRIEF.md` records that Ken French's library is "free but permission-gated
  and factor-level — never a magnitude claim", with `RUN_RULES` 0.2 governing.** A signal whose
  construction *depends* on French factors could validate a build and could never ship in a
  product figure, so the market leg is built from this project's own data and French is used
  nowhere in A2b.
  **Free kill:** the momentum-costume bar — mean per-date |ρ| against the shipped `momentum`
  theme must be **< 0.60** (`N6`'s bar, which `N6` itself cleared at 0.2604).

---

## 3. A3 — INFORMATION DISCRETENESS / "FROG IN THE PAN" *(Da-Gurun-Warachka 2014)*

**Mechanism.** Identical cumulative returns arriving in many small steps are under-reacted to
relative to the same return arriving in a few large jumps, so continuous information predicts
stronger drift.

**Construction.** Over the 12-month formation window,
`ID = sign(PRET) × (%neg_days − %pos_days)`, on daily returns, with `PRET` the window's
cumulative return. Entered as its own standardised column, **not** as an interaction.

**AND "NOT AS AN INTERACTION" IS A DESIGN DECISION WITH THE RECORD BEHIND IT.** The paper's
effect is an interaction with momentum, and `S7` registered **four** interactions and
**rejected all of them**, with `momentum × short_interest` the only cell to clear one half.
`S7`'s `C7` also measured that adding an eighth input moves every theme's relative weight 1/7 →
1/8, so an interaction arm is a **compound** change — and it measured that dilution at
**+0.000173 / +0.000146 of alpha, essentially nil**, which is the one piece of good news here.
**A standalone column is the cleaner first question; if it carries nothing, the interaction is a
second register and not a rescue of this one.**

**FREE PRE-OUTCOME KILL (`K1`).** Daily-return coverage over the formation window on the build
quadrant: the share of scoreable rows with **≥ 200 daily observations** in the window must be
**≥ 0.70**. A year-relative bar, not an absolute one — `MC12` read exactly **0.000** on 2001
against a fixed ≥250 bar because the NYSE closed after 9/11 and the year held 248 sessions, and
the year-relative replacement then went **vacuous on 1997** until a `MIN_PLAUSIBLE_SESSIONS`
floor was added.

---

## 4. A4 — CAMPBELL-HILSCHER-SZILAGYI (2008) DISTRESS PROBABILITY, AS A JUNK **FILTER**

**Scope, so this does not collide with r1.** Don's ruling of 2026-10-06 assigns the **tiered
pool** (stricter score hurdle for smaller names, with and without a junk filter) to **r1** under
its own blind register. **This arm does not duplicate r1's arms**: it registers the **CHS
probability itself as the filter definition**, and if r1's register already names a junk filter,
**this arm is withdrawn rather than run alongside it** — two lanes publishing two junk filters is
how one question comes to have two answers.

**Construction.** The eight CHS inputs built from SF1 + prices: `NIMTA`, `TLMTA`, `EXRETAVG`,
`SIGMA`, `RSIZE`, `CASHMTA`, `MB`, `PRICE`, with the paper's published coefficients — **not
re-fitted**, because fitting the filter on this panel and then scoring it on this panel is the
in-search-to-hold-out collapse the record already paid for (+8.43%/yr in-search → −0.04%/yr
locked hold-out).

**THE GATE IS A CRASH-RATE RATIO IN BOTH HALVES, NOT ALPHA AND NOT DRAWDOWN, AND THAT IS FORCED
BY MEASUREMENT.** `S10` measured this book's maximum drawdown as spanning **exactly ONE 63-day
period on every arm, at the same trough index 44 of 69 — COVID 2020Q1** — which **no name-level
screen can move**, and `S10-ACCT` then failed precisely on that leg while *improving* alpha by
+0.1970pp. **X7 calibrates no drawdown floor anywhere**, so a drawdown bar here would be
uncalibrated (§6). `MA28-CARD` is the design that worked on this exact shape: gate on the
**crash-rate replication in both halves** against the flag's own permutation null.

**FREE PRE-OUTCOME KILL (`K1`).** The filter must **bite without emptying the book**: the share
of build-quadrant top-decile rows it removes must fall in **[0.02, 0.25]**, and the book after
filtering must still clear **`CONTRACT_MIN_POSITIONS` = 50** names on **every** date. Below 2%
it cannot matter; above 25% it is a different universe wearing a filter's name. **`N4` died on
exactly this class of bar** — median 30 names per date against the 50 floor.

---

## 5. A5 — NET PAYOUT YIELD *(Boudoukh-Michaely-Richardson-Roberts 2007)* — **BLOCKED BEFORE IT STARTS**

**Mechanism.** Total payout — dividends **plus** net repurchases — over market cap, on the
argument that repurchases substituted for dividends after the 1980s so dividend yield alone
measures a shrinking share of what is returned.

**ITS FREE KILL IS A SCOPING KILL AND IT FIRES NOW, AT ZERO COST.** Dividends and repurchases are
**not in the loader's allowlist**: `WRDSProvider._KEEP["fundamentals"]` carries `ncfo`, `fcf`,
`debt`, `equity` and the rest, and **neither `ncfdiv` nor `ncfcommon` is present** (verified in
`valuation/edge/data_providers.py`). So the arm needs **new source columns, which forces a panel
rebuild** — and that is the precise reason `S17`/`S19` **excluded `S10`'s accounting half**:
eight columns absent from `_KEEP` forced a rebuild where its siblings needed none.

**So A5 is registered as NOT RUN, `k` stays 12, and the honest statement is a cost rather than a
verdict:** it is buildable, it needs a rebuild of the corrected full-universe panel, and it
should be batched with any **other** arm that also needs new columns rather than paying that cost
alone.

**AND ITS OVERLAP WITH THE SHIPPED SIGNAL NEEDS STATING NOW, BECAUSE IT IS THE REASON TO BE
SCEPTICAL EVEN AFTER A REBUILD.** `capital_discipline` is `neg_issuance`, derived in `_yoy()` from
`sharesbas` year-over-year. **`S16` measured the governing hazard on this exact pair: splitting
net issuance into buyback and dilution legs is a RANK IDENTITY — within-date rank correlation
`1.000000000000` on all 69 dates — because `max(0, −net)` and `−max(0, net)` are both
non-increasing in `net`.** Net payout yield is **not** that identity (it adds dividends and
rescales by market cap), but **the register must prove non-identity by measurement before scoring
it**, not assume it from the construction.

---

## 6–11. THE SURVIVING FREE-KILLS CANDIDATES

`FREE_KILLS_RESULTS.md` ran the zero-trial pre-outcome kill for N1–N8 and `W-17`. **`N4` and
`W-17` are CLOSED at zero trials; `N8` is UNDERPOWERED by construction (165 usable in-band events
against a power reference of 400) and is not in this batch.** The six survivors enter with the
kill they already passed, and **a passed kill is not a licence** — each still needs its Stage-1
arm scored and its both-halves reading.

| arm | candidate | the kill it already passed, with its number | what remains |
|---|---|---|---|
| **A6** | **N1** small/mid core | buildability: median **506.5** eligible names at cap < $5B / ADV > $5M, min **437**, **0** dates below 50; 8 of 9 bands buildable | **the bands must be RELATIVE** (percentiles), not the absolute $5B/$5M used for the census — `INDEX-CHOICE-ARM4`'s rule, since an absolute cut is not invariant to the ticker half |
| **A7** | **N2** net issuance | coverage + dispersion: `z_neg_issuance` non-null median **0.9821** (min 0.8291) against the **0.70** rule | its reservation is a **tail no pre-committed bar can judge**; the register must state the winsorisation it uses **before** the look, because `S21` showed removing the clip moves alpha +2.43pp/yr and is the *fragile* estimator |
| **A8** | **N3** earnings-surprise drift | spine coverage inside the band **1.0000** — **0 of 1,678** names FAIL_CLOSED — and **4.1215** announcements per ticker-year against ~4.0 expected | **the strongest candidate, and the only one designed in the POWERFUL space.** Event time: §4b's MDE is **1.66pp at n_eff 400** against **0.4274–0.5071 SD** on the cross-section. Bar is its own within-date permutation p95 |
| **A9** | **N5** analyst neglect | `numest` present in `statsum` (51 chunks) and `ibes_id` carries **`sdates`**, so the link is **dated** | **its costume kill was NOT RUN.** `K2` must run first: |ρ| against the `size` theme, bar **0.60**. `E-1` died at **0.6114** against `size` and `R6`'s conviction signals read **−0.815 to −0.854** — a neglect proxy is a size proxy until measured otherwise |
| **A10** | **N6** industry momentum | momentum costume: mean per-date |ρ| vs `momentum` **0.2604** (max 0.4419) against **0.60** | residual risks are **thin industry groups** and the **point-in-time sector map**. `S25` built a dated GICS map; `S25-REPAIR` measured that wiring it moves the fair value on **every row it touches** and flips the regime on **57%**. The register must use the dated map and say so |
| **A11** | **N7** 52-week-high proximity | disclosure + non-identity: |ρ| vs `momentum` **0.7596** (max 0.9502), vs the composite **0.3933** — not identical | **0.76 of the momentum theme is a high number and the register must treat it as a near-duplicate**, pre-committing that a pass is read as *momentum measured differently* unless the incremental IC survives residualising on `momentum` alone |

---

## 12. NOTED, NOT DRAFTED — VOLATILITY-MANAGED EXPOSURE

**Moreira-Muir (2017)** scale exposure by the inverse of recent realised variance;
**Cederburg, O'Doherty, Wang and Yan (2020)** find the strategy fails out of sample for most
factors and that its gains concentrate in the market factor and in periods of extreme volatility.
**It is a RISK OVERLAY, not a signal**, so it belongs to a later batch and to a different
question — and `R1-VAR` already carries Don's standing ruling on that family: **a Sharpe or
volatility gain bought with alpha is not worth having unless the Sharpe itself is bad**, and the
book runs Sharpe **0.5866** at an IR of ~0.88/yr, so the antecedent does not fire. **Not drafted,
and anyone drafting it must clear `R1-VAR` first.**

---

## 13. WHAT THIS DRAFT DOES NOT DO

* **No register is committed, no arm is run, no trial is booked, nothing is measured.** `k` = 12
  is a *plan*; the research log is untouched.
* **No Stage-2 look.** The check quadrant (2020–2026 × the other half) is not read, and reading
  it to pick among these twelve would spend it permanently.
* **No Stage-3 look.** The 1999–2008 proxy is not read here, and when it is, charter §5 binds:
  it may test a new signal's **increment** on a five-theme base and may **not** validate the
  shipped seven-theme construction, with `POOL-SIZE`'s prior read disclosed.
* **The 1972–1998 WRDS era stays closed** — `OOS1`'s Gate B reads **0.837303** against its
  pre-committed **0.90**.
* **Nothing is adopted.** Adoption is Don's, is a vintage event, and quotes the expected return at
  **half** the backtested size (McLean-Pontiff).
* **A5 is reported NOT RUN rather than dropped**, and `k` stays 12 — see §0a.
* **A4 is withdrawn if r1's tiered-pool register already names a junk filter.**
