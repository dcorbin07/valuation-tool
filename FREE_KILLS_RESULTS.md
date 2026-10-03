# FREE KILLS — results for N1–N8 and W-17, plus MC9's validation

**2026-10-03. ZERO TRIALS. Read-only censuses: no register committed, no arm scored, no trial
booked, no WRDS pull.** `by_domain` untouched at equity **252** / options **310** / unified **0** /
infra **20**. Artifact `FREE_KILLS_CENSUS.json`; instrument `scripts/free_kills_census.py`, pinned
by `tests/test_free_kills_census.py` (10 tests) over its own syntax tree so no outcome column or
scorer is reachable from the census path.

**The band used for the per-draft censuses: market cap < $5B AND dollar ADV > $5M — 33,177 rows,
1,678 names.** Market cap and ADV are both in **dollars** (checked: panel median $5.0B, ADV median
$42.6M), and both join keys are normalised to `YYYY-MM-DD` strings because the panel's `date` is a
**str** while `B13_ADV_PANEL`'s is a **`datetime.date`** — unnormalised that merge matches zero
rows in silence.

---

## THE TABLE

| draft | kill | fired? | the number it rests on |
|---|---|---|---|
| **N3** earnings drift | spine coverage inside the band | **NO** | band covered share **1.0000** — **0 of 1,678** names FAIL_CLOSED — and **4.1215** announcements per ticker-year in the band (panel 4.1182) against **~4.0 expected** |
| **N8** spin-offs | usable event census | **no on the close bar, YES on power** | **165** usable in-band events (`spinoff` 114 + `spunofffrom` 51) against a close bar of **100** and a power reference of **400** |
| **N4** insider clusters | cluster census | **FIRED** | median **30.0** names per date with ≥2 distinct opportunistic buyers (min 18, max 137) against the **50**-name `CONTRACT_MIN_POSITIONS` floor |
| **W-17** index add/delete | K1 · CLOCK | **FIRED** | `dsp500list` is **2,064 dated membership SPELLS**, 1925-12-31 → 2024-12-31 — **effective dates only, no announcement date** |
| **N1** small/mid core | buildability | **NO** | median **506.5** eligible names at cap<$5B / ADV>$5M (min **437**, **0** dates below 50); **8 of 9** bands buildable |
| **N2** net issuance | coverage + dispersion | **NO** | `z_neg_issuance` non-null median **0.9821** (min 0.8291) against the **0.70** rule |
| **N5** analyst neglect | `numest` + a dated link | **NO** (K1 only) | `numest` present in `statsum` (51 chunks); `ibes_id` carries **`sdates`**, so the link is dated. **K2 NOT RUN** |
| **N6** industry momentum | momentum costume + groups | **NO** | mean per-date \|rho\| vs the `momentum` theme **0.2604** (max 0.4419) against the **0.60** bar |
| **N7** 52-week high | disclosure + non-identity | **NO** (it is a disclosure) | \|rho\| vs `momentum` **0.7596** (max 0.9502); vs the composite **0.3933**; not identical |

## WHAT EACH RESULT MEANS FOR THE TWELVE-ARM BUDGET

**Two closed for nothing. One is effectively closed on power. Zero trials spent.**

* **N4 — CLOSED at zero trials.** A cluster book cannot reach the contract's own 50-name floor; the
  median date offers **30**. It is not below the hard floor of 20, so the mechanism is not absent —
  it is **unbuildable as a diversified book**. And the census settles the mechanism question too:
  the opportunistic filter removes only **8.04%** of open-market purchases (163,766 rows → 150,592
  opportunistic), so *"opportunistic"* does almost no work and the arm was a **cluster** arm all
  along, exactly as the draft's K2 predicted. **My draft cited 2.72% from `MB20`; measured on this
  population it is 8.04%** — the conclusion is unchanged and the number is corrected.
* **W-17 — CLOSED at zero trials, and its own author predicted this.** Its K1 fires on the record's
  own census with no pull: a membership **spell** is an effective-date interval and carries no
  announcement date, so the event is mis-clocked and the draft's entire `√W/k` power argument
  evaporates. K2 and K4 are **BLOCKED** on the pull rather than cleared. The draft declared itself
  a closure purchase and called K1 *"the most likely kill"* — it was right.
* **N8 — survives the close bar and is UNDERPOWERED BY CONSTRUCTION.** 565 events across all
  history become **386** in the panel window, **236** on panel names and **114** in the band, plus
  51 parent-side; **165** usable against event time's **400** reference. The draft pre-committed
  this branch (`O-1`'s shape: *"the honest outcome is UNDERPOWERED and the trial still charges"*).
  **Recommendation: do not spend a trial on it.** A trial that cannot be decisive buys hurdle for
  everything else and nothing for itself.

**Six survive and the budget is untouched at zero of twelve.**

## THE ONE RESULT THAT REFUTES MY OWN DRAFT

**N3's coverage objection is wrong, and it was my objection.** My draft said the earnings-date hole
was *"probably WORSE in small caps"*, reasoning from `W-3b`'s measured ~2.83 announcements per
ticker-year. Measured on the equity panel: **4.1215 per ticker-year in the band, 4.1182 on the
panel, zero FAIL_CLOSED names of 1,678.** The 2.83 is specific to the **186-name options
universe**, whose shortfall `W-3b` itself traced to 29 foreign private issuers — **a composition
fact about that book, not a coverage fact about the equity panel.** That is the same
population-substitution error `O-1` paid ~17× for, and I made it from the same kind of borrowed
figure.

**Consequence: N3 does not even need the IBES merge for coverage.** It needs IBES for the *surprise
measure* (actual vs consensus), not for the dates.

## ONE DEFECT IN THIS CENSUS, CAUGHT BY DISBELIEVING AN IDENTICAL COUNT

The first run of N1 reported **`min_eligible = 0` and "5 dates below 50" in eight of nine grid
cells.** An identical figure across thresholds that share no boundary is one cause, not eight
coincidences. Measured: **`B13_ADV_PANEL` is CRSP-built and ends 2024-10-23** while the panel runs
to 2026-01-28, so the five rebalance dates past the cut — **2025-01-27, 2025-04-28, 2025-07-29,
2025-10-27, 2026-01-28** — have **zero** ADV coverage and every band read empty on them.

**That is `W-28`'s vendor-cut-as-coverage-gap defect, and it is the same five dates
`PREREG_DRAFT_oos1` had already declared UNVERIFIABLE by construction — my own draft's warning,
tripping my own census.** Repaired by scoring the **64 effective dates** and **listing** the five,
with the exclusion **derived from coverage rather than hard-coded** so it moves when the vendor
does (pinned by test). ADV covers **86.08%** of effective cells.

**And it is a measured argument for MC9's instrument existing at all: MC9's SEP-derived ADV runs
to 2026 where CRSP stops at 2024-10-23**, so it covers exactly the five dates that broke this
census.

## MC9 — THE $ADV INSTRUMENT IS VALIDATED

**First, a correction to my own handoff.** I wrote that MC9 *"has never been wired"* and
recommended validating it. `MC9_FIDELITY.json` is a **`B7` fidelity record that already validated
it against CRSP.** The ledger's *"NOTHING WIRED"* means **no consumer reads it**, not that it was
unchecked. So what follows is an **independent reproduction**, not a first validation.

| metric | this reproduction | banked `MC9_FIDELITY` |
|---|---|---|
| CRSP cells | **90,025** | 90,025 |
| overlapping cells | **89,998** | 90,005 |
| SEP covers CRSP cells | **0.99970** | 0.99978 |
| **median ratio SEP / CRSP** | **0.99980** | 0.99886 |
| p05 / p95 | **0.96464 / 1.00730** | 0.95783 / 1.02692 |
| share >25% apart | **0.02042** | 0.02152 |

**Verdict: VALIDATED.** The SEP-derived ADV agrees with the clean CRSP panel to **0.02% at the
median** over **89,998** overlapping cells, covering **99.97%** of CRSP's cells, with **2.04%** of
cells more than 25% apart. The two independent computations agree to within **0.001** on the
headline; the widest gap is **p95 at 0.020**, and my cell count is **7 lower** because I required
`adv > 0`. **The instrument under test is `adv_sep.adv_series`** — MC9's artifact is raw SEP bars
(`{ticker: [(date, o, h, l, c, volume, closeadj)]}`, 8,185,668 kept rows over 2,531 tickers), not a
precomputed column, so validating it meant running it rather than reading it.

## DISCLOSURES THAT ARE NOT KILLS, REPORTED SO THEY ARE NOT DISCOVERED LATER

* **N2's dispersion is concentrated**: the top 5% of band names by absolute `z_neg_issuance` carry
  **31.74%** of the absolute mass (uniform would be 5%). **My draft declared a concentration kill
  but never fixed a number, so it CANNOT fire** — `W-28`'s rule forbids setting a bar after seeing
  the data. It is reported as a disclosure and any successor must pre-commit the bar.
* **N6's industry groups are thin**: the median date's **smallest** industry holds **11** names
  (minimum 9) across **11** sectors. An industry return on nine names is noisy, and the draft's K4
  bar was likewise never numbered. Also: this census used the panel's **`sector`**, which is
  **today's** classification — **it measures group sizes and the costume, NOT a point-in-time map.**
* **N7 is substantially the momentum theme**: \|rho\| **0.7596**, above the 0.60 bar that kills a
  *costume* elsewhere. The draft declared K1 a disclosure rather than a kill, so it does not fire —
  but **0.76 against an incumbent theme is the reason it stays last.**
* **N5's K2 — the size costume — is NOT RUN**, and it is the kill most likely to fire. It needs
  `numest` joined to the panel through the dated `ibes_id` link, which is the arm's own first build
  step. **K1 establishes the link is buildable and dated; nothing here establishes that coverage is
  not a size proxy.**

## UPDATED RANKING OF WHAT SURVIVES

| # | draft | standing after the census |
|---|---|---|
| **1** | **N3** earnings-surprise drift, IBES SUE, event time | **promoted** — its only serious objection is refuted by measurement, it sits in the high-power space, and IBES spans 1976–2026 so it reaches both pre-2009 eras |
| **2** | **N1** small/mid core | **buildable and clean** — median 506 eligible names, zero thin dates, and its prize (−4.1785pp) is the one measured opportunity in the record |
| **3** | **N2** net issuance | coverage 98.2%; the only reservation is a tail that no pre-committed bar can judge |
| **4** | **N6** industry momentum | **cleared the kill most likely to fire** (0.26 vs 0.60); residual risks are thin groups and the point-in-time map |
| **5** | **N5** analyst neglect | link buildable and dated; **its costume kill is unrun** |
| **6** | **N7** 52-week high | survives, and is 0.76 of the momentum theme — hold in reserve |
| — | **N8** spin-offs | **UNDERPOWERED by construction** (165 vs 400). Do not spend a trial |
| — | **N4** insider clusters | **CLOSED, zero trials** (median 30 vs 50) |
| — | **W-17** index events | **CLOSED, zero trials** (mis-clocked; K2/K4 blocked on the pull) |

## THE FIRST REGISTER I WOULD HAND AN EXECUTOR

**Not a register — an `INDEX-BOOK`-class DESCRIPTION of N1's band book, at ZERO trials, first.**

`INDEX-BOOK` measured the served construction last week and charged **zero trials** on the explicit
reasoning that *"re-measuring a KNOWN construction on a KNOWN panel selects nothing"* — no
hypothesis, no bar, no second arm that could have come back the other way. **N1's band book is the
same shape**: one construction, fixed by the census above, with the knobs already frozen
(cap<$5B, ADV>$5M, score-weighted, 8% cap, 0.30 band, quarterly). Run as a **description** — report
its net-of-cost return vs SPY, its turnover, its realised cost, its factor loadings, and **no
verdict** — it costs nothing and it answers Don's actual question: *is the −4.1785pp the tier
forgoes reachable at Roth size, after cost?*

Everything needed is validated and on disk: the panel, `build_index`, the cost machinery, and now
the ADV instrument. **No WRDS, no pull, no new instrument.**

**Then, as the first true register: `N3`.** It is in the high-power space, its objection is
refuted, and it spans both holdout eras. Its prerequisite is the **dated IBES link** (`ibes_id`
`sdates` + cusip), which `N5` also needs — **so build that link once, as shared infrastructure,
and validate it before any hypothesis** (`MB15`). That link is the single most useful piece of
unbuilt machinery the program has.

**Why N1-as-description before N3:** it is free, it needs nothing new, and if the band book does
not beat SPY net of cost then the entire small-cap thesis behind N2, N5, N6 and N7 is worth less —
so it is the cheapest thing that could change the ranking.
