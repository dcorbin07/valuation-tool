# PREREG DRAFT — IC1, THE REBALANCE GRID ALIGNED TO DATA ARRIVAL

**DRAFT. Frontier Scout. No measurement, no arm, ZERO trials. Not a register until an executor
commits it ALONE.** Ranked **1 of 6** for expected value per trial.

**NOT r1's item.** `REBAL-CADENCE` asks how OFTEN to rebalance (quarterly / semi-annual /
annual / staggered). This asks, at an unchanged quarterly cadence, **on which day of the quarter**
— and the two are orthogonal: every cadence r1 tests has to pick a phase, and this is the phase.

---

## 1. MECHANISM

The panel's grid starts at a hard-coded `TD = 252` and steps 63 trading days. **That offset was
inherited, never chosen.** The 13F theme's information arrives on a fixed calendar — a 45-day
filing deadline after each quarter end — and the panel's effective lag is already **~111 days**,
so an April rebalance is scored on the December quarter. Earnings arrive in a four-to-six-week
bulge after each quarter end. A grid whose dates sit **just after** those two arrivals scores the
freshest cross-section the vendor can supply; a grid sitting just before them scores one that is
about to be superseded wholesale.

**ARM: one grid, pre-committed before it is scored** — the first trading day on or after the 13F
deadline plus a stated settling lag, with the lag fixed in the register from the filing calendar
and never tuned. One arm. No sweep over offsets: `X2` already swept offsets and that sweep is the
reference distribution, not the arm.

## 2. THE RECORD'S EVIDENCE *FOR*

* **`X2` measured that the grid is load-bearing and never explained why.** Seven equally valid
  grids (offsets 0/5/10/20/30/40/50 trading days), all keeping 69 dates over the identical
  window, give long-short *t* of **2.703 / 2.836 / 2.850 / 2.926 / 3.374 / 3.410 / 3.517** —
  a spread of **0.814 of a *t*** on the project's headline statistic. `CLAUDE.md` records the
  consequence as *"quote t 2.7–3.5 depending on grid, straddling the hurdle"* and offers **no
  mechanism**. This draft proposes the one mechanism that is calendar-shaped.
* **`S8`'s central finding is the argument FOR this arm, not against it.** `S8` measured
  `days_since_13f` taking a mean of **1.25 distinct values per date** (within-date sd **2.054
  days**), because 13F quarter-ends are **common calendar dates** — at any rebalance every name's
  13F is the same age. Its own conclusion: *"13F staleness is common across names, not
  cross-sectional — so decaying it cannot re-rank anything."* **A common-mode exposure cannot be
  touched by a cross-sectional weight and can only be touched by moving the DATE.** `S8` closed
  the cross-sectional lever and, in doing so, named this one.
* **The decay is measured and steep.** 13F peaks at Q−1, is alive at Q−2 (*t* 1.36) and **dead by
  Q−3** (*t* −0.04). `institutional` carries 0.125 of the weight at **71.7%** coverage and a theme
  IC *t* of **+1.55**. So a phase shift that moves the book from a Q−2 to a Q−1 read is moving a
  live theme across most of its own half-life.
* **The operational path already exists.** `REBAL-FRESH` (2026-09-30) shipped
  `REBALANCE_MAX_STALE_DAYS = 2` **trading** days and made `append_rebalance` read *the book's own
  as-of date against the event date*. The live pipeline therefore already distinguishes the two,
  so an adopted phase change is a configuration of machinery that exists.

## 3. THE RECORD'S EVIDENCE *AGAINST*

* **`S9`'s freshness gradient is absent, and that is the strongest counter.** Top-decile forward
  return by filing-age quartile: **Q1 +6.15% @38d, Q2 +6.12% @66d, Q3 +6.66% @71d, Q4 +6.35%
  @88d** — not monotone, whole spread about half a point on a 6.3% base, and **Q1 − Q4 = −0.78%/yr,
  i.e. the STALEST quartile very slightly outperformed the freshest.** If fundamental freshness
  carries nothing cross-sectionally, a date shift that buys freshness may buy nothing.
  **The distinction this draft rests on, stated plainly: `S9` measured FUNDAMENTAL filing age,
  which varies 86.81 distinct values per date, and found no gradient. It did NOT measure the
  13F axis, which has 1.25 distinct values per date and therefore cannot show a gradient at all.**
  A successor must not read `S9` as having closed the 13F phase question; it is structurally
  incapable of answering it.
* **`X2`'s spread may be noise.** Seven draws is a thin distribution and nothing established that
  the ordering is anything but sampling error on 69 overlapping quarterly observations. **This is
  why the bar below is a percentile of `X2`'s own grids and not an absolute *t*.**
* **`S8`/`S9` rejected all four freshness arms**, and this is the fifth member of that family. The
  family's prior is poor and should be stated as such.
* **`prepare_daily` staleness (`S8`'s own by-product).** The point-in-time market cap is
  down-sampled to one row per ticker-month and can be **up to 31 days stale** against a same-day
  price. Moving the grid date moves that staleness too, in an uncontrolled direction — so part of
  any measured effect is a `size` artefact rather than an information-arrival effect. **A control
  must hold it: score the arm with `size` dropped and report both.**

## 4. BAR AND MDE

**Primary gate: the shipped `holdout_compare_panels`, verbatim** — margins **> +0.25** long-short
*t* **AND > +100 bps** top-decile alpha, in **BOTH** halves, boundary embargoed, under **BOTH**
weightings. That is the gate `SECTOR-NEUTRAL-B6`, `S14`, `S15`, `S3`, `S16`, `W-1` and `MB20` all
used; reusing it verbatim is what stops a bar being chosen after the fact.

**Secondary, and it is the cheap part: the arm's long-short HAC *t* must exceed the 75th
percentile of `X2`'s seven banked grids.** Those grids are an empirical distribution of
*arbitrary* phase choices, so a data-aligned grid landing in the top quartile of it is evidence
that phase carries information, and landing mid-pack is evidence it does not. **With n = 7 the
resolution is poor and the register must say so** — this leg cannot carry a verdict alone and is
stated as a direction, not a threshold to be quoted.

**MDE.** A phase change is a **paired within-panel difference**, and `V2G` established and
`R1-VAR` re-confirmed that **no calibrated floor exists for one** — `X7` calibrates LEVELS. So the
register must (i) measure **its own** paired HAC SE, because `MB8` forbids borrowing one across
perturbation sizes, and (ii) print the 80%-power MDE at the conventional crit 2.0 **labelled
UNCALIBRATED** and at the honest hurdle, derived not typed (equity N **248**, hurdle
**3.3206712**, derived this session). For scale, the record's two measured paired SEs bracket the
likely answer: `MB8`'s **0.1106pp** (a small perturbation) and `V2G`'s **0.9354pp** (a whole-theme
swap), giving an 80%-power MDE between roughly **0.31pp and 2.66pp** at crit 2.0 and **0.46pp to
3.88pp** at the hurdle. A phase shift re-ranks the whole cross-section, so the honest prior is the
**upper** half of that bracket — which means **this design may well not be able to resolve its own
effect, and the register must derive its MDE before scoring rather than after.**

## 5. KILLS, FREE AND READ FIRST

* **K1 (free, no trial).** The data-aligned grid must keep **≥ 69 dates** over the same window and
  must not coincide with one of `X2`'s seven offsets. If it lands on an existing offset the
  question is already answered and the item closes at zero trials.
* **K2 (free).** Per-date cross-sections on the new grid must stay inside the shipped panel's own
  **1,471–1,954** range. A phase that lands on a thin cross-section is measuring coverage.
* **K3 (free).** The 13F age the new grid actually buys must be **measured and reported before any
  outcome**: if the mean `days_since_13f` does not fall by at least a full quarter's worth of the
  measured decay, the arm is inert on its own stated mechanism and closes at zero trials.
* **K4.** `size` dropped as the `prepare_daily` control of §3. Reported either way; it cannot
  rescue a failing arm, only block a passing one.

## 6. VINTAGE CONSEQUENCE

**Research-side: none.** Re-phasing the research grid changes no live score.

**On adoption: a VINTAGE EVENT.** It changes when the live book rebalances, so it closes the open
vintage and opens the next. **DERIVE the vintage from `track_meter.VINTAGES`; never quote one** —
`CLAUDE.md` records three resets in four days and a stale date in this file. Derived today:
**vintage 4, OPEN, opened 2026-08-13** on the S14 band at 0.30, with ~48 days accrued. **Rule 6 is
the brake**: a reset discards the accrued clock and buys nothing statistically, and the contract's
meter has **13.3% power at 60 months**. So an eligible result is recorded **ELIGIBLE, NOT ADOPTED**
and routed to Don.

## 7. CAN OWNED DATA TEST IT?

**Yes, with no purchase and no rebuild.** `build_fundamental_panel` already takes the date grid;
the 13F deadline is a calendar fact; `datekey` in the freeze's raw `sf1` dates earnings arrival to
the day (and `MC12` has just re-measured its timeliness at **0.985–0.995** of rows inside
`reportperiod + 120d`, so the arrival date is trustworthy). Cost is one panel build per arm, the
same ~20 minutes `X2` paid seven times.
