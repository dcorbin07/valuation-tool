# PRE-REGISTRATION — `POOL-SIZE`: does a wider pool keep helping, and where does it start to hurt?

**Committed ALONE, markdown only, zero `.py`, before any runner exists. A strict git ancestor of
every commit that computes a figure this register declares.**

Don's question. `INDEX-BEST` compared four constructions and `INDEX-CHOICE` compared three; neither
traced the **curve**. This register fixes the decision rule and the arms before any number is read.

---

## 0. Counter and the trial charge

`by_domain` at writing: **equity 259, options 310, unified 0, infra 20**;
`rows_fixed_not_counted` **93**, `rows_malformed` **empty**. HLZ hurdle at 259 is
**3.3337150633**; at 262 it is **3.3371678123** — derived, never typed.

**THREE EQUITY TRIALS. Equity 259 → 262.**

* **1 for the return/drawdown ladder (part a).** It is **one** hypothesis with **one**
  pre-committed rule applied across a ladder, not one search per rung — and the rule reads
  *return* and *drawdown* as a pair, so they are one statistic for this purpose. `R1`'s precedent
  is 1 trial for a decomposition spanning many objects; `INDEX-CHOICE`'s is per **statistic**, not
  per arm.
* **1 for the FF5+MOM decomposition (part a).** `R1` charged exactly 1 for a full factor model
  across several objects.
* **1 for part (b), the 1999-2008 proxy.** A separate measurement on a separately-built panel,
  and it is read **ONCE**.
* **0 for the diagnostics** — the under-$300M share, the missing-input rate and the sanity-flag
  rate by size bucket are **censuses**: facts about what the data contains, with no hypothesis and
  no bar (`S25` / `MB3` / `W-28-PULL` class). They can only BLOCK an interpretation, never produce
  one.

**THE CASE FOR FEWER IS REAL AND IS STATED: three of the seven rungs are ALREADY BANKED** by
`INDEX-BEST` (the incumbent, the 1,500 and the full panel), so only four rungs are new. I charge
the ladder as one search anyway because the *curve* and its decision rule are the new object.
`MA6`: overstating `N` is the safe direction.

`MB31`: the next adopt-set flip is seed **1017 at equity `N` = 688**, so **no permutation floor
can move**, and this register compares nothing to one.

---

## 1. THE DECISION RULE, FIXED NOW

Don's words, and the rule of record:

> the recommended pool is the LARGEST one whose net Roth return is not lower than the
> next-smaller pool's and whose max drawdown is not more than 3pp worse.

Made precise, because each clause has a reading that must not be chosen later:

* **The ladder is ordered by POOL SIZE ascending**, and the pool is the set of names
  `build_index` is allowed to see — not the book. Rung positions are measured, not assumed.
* **"not lower than the next-smaller pool's"** → `net_roth_ann(k) >= net_roth_ann(k-1)`,
  **exactly**, with **no tolerance**. A tolerance here would be an invented bar, and
  `V2G`/`R1-VAR` establish there is no calibrated floor for a paired within-panel difference.
* **"not more than 3pp worse"** → compared with **the same next-smaller rung**, by symmetry with
  the first clause. Drawdowns are **negative**, so the test is
  `max_drawdown(k) >= max_drawdown(k-1) - 0.03`. **The sign is written down now because reading
  it backwards is this record's own documented defect** (`S10`'s first cut reported a 2.61pp
  worsening as an improvement).
* **"the LARGEST one whose ..."** → scan from the largest rung downward and take the first that
  satisfies **both** clauses **against its own immediate predecessor**. That is the literal
  reading and it is the **PRIMARY**.
* **A SECOND READING EXISTS AND IS PRE-COMMITTED AS A SENSITIVITY, NOT AS A FALLBACK.** The rule
  could instead require both clauses to hold at **every** step up to the chosen rung
  (cumulative). If the two readings agree, the ambiguity is moot and that is reported. **If they
  disagree, BOTH are reported and the literal one is the answer** — choosing the reading after
  seeing which is kinder is exactly what this section exists to prevent.

**THE RULE CAN RECOMMEND THE INCUMBENT**, and that outcome is as reachable as any other: if no
larger rung clears both clauses against its predecessor, the scan falls through to the smallest.

---

## 2. THE ARMS — one construction, seven pools

Every rung is the **same construction**: top decile by the shipped composite, **score-weighted**,
**8% cap**, **0.30 no-trade band**, **quarterly**, flat 1/7 weights, net of the **shipped
size-aware market-cap cost table**. The pool is the only thing that changes.

| # | pool | how it is formed |
|---|---|---|
| 1 | incumbent $10B tier | `large_cap_min = 1e10` |
| 2 | 500 largest | `universe_rank = 500` |
| 3 | 1,000 largest | `universe_rank = 1000` |
| 4 | **1,500 largest** | `universe_rank = 1500` — **already banked** as `INDEX-BEST` arm 2 |
| 5 | 2,000 largest | `universe_rank = 2000` |
| 6 | **full panel** | `large_cap_min = 0`, no rank — **already banked** as arm 4 |
| 7 | full panel, **penny/nano floor removed** | a panel built with `EDGE_AUDIT_B13_PREFILTER=off` |

**THE MACHINERY IS CALLED, NOT REBUILT** (`B7`, `MA5`): `served_index_book.book_fn` /
`run`, `valquo_index.trim_universe`, `no_trade_band.BAND_WIDTH`, and `factor_alpha`'s own
`ols_nw` / `regress` / `factor_windows` / `FF_MODEL` at `LAG = 1`.

### 2a. A PREMISE CORRECTION, MADE BEFORE ANY NUMBER: THE LADDER IS CAP-RANKED, NOT LIQUIDITY-RANKED

The task says *"the 500, 1,000, 1,500 and 2,000 most liquid"*, and
`DECISION_index_choice.md` calls arm 2 *"liquid top 10%"*. **The shipped trim is neither.**
`valquo_index.trim_universe`'s default `rank_key` is **point-in-time market cap**, and the
runbook's own §3b describes arm 2 as *"the top 1500 by point-in-time market cap"*. So "most
liquid" is this project's loose label for a **cap** rank, and that is what these rungs are.

**IT IS FORCED RATHER THAN PREFERRED, and the measurement is why.** A genuine ADV-ranked ladder
is **not constructible** on owned data: `B13_ADV_PANEL.pkl` carries ADV for **64 of 69 dates
(2009-01-15 … 2024-10-23)** at a median of **1,332 names per date and a maximum of 1,832** — so
it reaches neither the last five rebalance dates nor **2,000 names on any date at all**. A
2,000-name liquidity rung cannot be formed. Second reason, independent: the 1,500 rung **is** the
construction Don may adopt, so changing the rank key would make this ladder measure a different
boundary from the one in the memo.

**A TRUE ADV-RANKED LADDER IS NAMED AS NOT-DONE.** It needs ADV rebuilt from the freeze's SEP for
every panel name and date, which is a data build, not an analysis.

### 2b. ARM 7 IS REPORTED AS A PAIRED DELTA, NOT AS A RUNG LEVEL

The penny/nano floor is applied at **panel build** time (`factors.prefilter`, via
`EDGE_AUDIT_B13_PREFILTER`), so arm 7 needs **its own panel**. Any panel built today lands on the
**2026-10 export**, whose universe is **3,049 names against the banked panel's 2,531** — the
confound `SHARADAR-REFRESH` measured. Comparing arm 7's level against rungs 1-6 would therefore
conflate removing the floor with a wider export and a rolled window.

**So arm 7 ships as a PAIRED DIFFERENCE measured on ONE vintage**: two panels built from the
**same** source with the prefilter ON and OFF, and the reported figure is
`net_roth_ann(off) − net_roth_ann(on)` plus the same difference in drawdown. **Its LEVEL is not
placed on the main ladder**, and quoting it as a rung is a void condition.

---

## 3. WHAT PART (a) REPORTS, 2009-2026

Per rung: **net Roth return**, **early/late halves** (the boundary embargoed as `INDEX-BEST`
does), **max drawdown**, **annual turnover**, **realised one-way cost in bps** from the shipped
market-cap table, **FF5+MOM loadings**, **the share of the book in names under $300M**, and
**the missing-input and sanity-flag rate by size bucket** so data quality at the small end is
measured rather than assumed.

**`C1` GATES EVERYTHING AND IS A THREE-POINT REPRODUCTION.** Before any new rung is read, the
runner must reproduce `INDEX_BEST.json`'s banked figures at **max absolute deviation 0.000e+00**:

| rung | `roth_net_ann` | `roth_max_drawdown` | `annual_turnover` | `realised_one_way_bps` |
|---|---|---|---|---|
| incumbent | 0.1716188056513155 | −0.23028569279336075 | 2.437245082733814 | 9.584461976204357 |
| 1,500 | 0.2294646167705674 | −0.27600090292443336 | 1.9268114715770899 | 29.344051612262923 |
| full panel | 0.24950546311372124 | −0.2780650330457006 | 1.8590714732972382 | 35.60466789248458 |

**The count of compared leaves is GATED non-zero** — `MB21`'s `C1` once scored a perfect zero on
an empty frame by comparing nothing. If `C1` fails, nothing is scored and the failure is the
report.

**EVERY MDE IS STATED BEFORE ITS MARGIN** (`MB22`, `RUN_RULES` A11): each paired rung-to-rung
difference ships its own measured paired HAC se with `MDE_50% = crit × se` and
`MDE_80% = (crit + 0.84) × se`. **Every critical value is LABELLED UNCALIBRATED** — `V2G`
established and `R1-VAR` re-confirmed that no calibrated floor exists for a paired within-panel
difference, and X7 calibrates **levels**. No figure here is compared to 2.2837, 2.0540, 2.7072 or
any other X7 floor.

**THE DECISION RULE IS A PREFERENCE RULE, NOT A SIGNIFICANCE TEST, AND THAT IS SAID NOW.** It
compares point estimates because Don asked a preference question. The MDEs travel beside it so a
reader can see that adjacent rungs are almost certainly **not** separable — and a rule that
cannot separate its rungs statistically can still be the right way to choose between them, as
long as nobody calls the winner significant. **No arm is called significant anywhere.**

---

## 4. PART (b) — 1999-2008, A LABELLED PROXY, READ ONCE

**WHAT IT IS AND IS NOT.** It tests **POOL WIDTH** out of sample. It does **NOT** test the
shipped seven-theme composite and may never be quoted as doing so: `PANEL-EXT-CENSUS` measured
that `institutional` has **zero** pre-2009 source (Sharadar `sf3` starts 2013-06-30) and
`insider` reaches only **0.307** by 2008 against the **70%** rule, which `PANEL-EXT-RECHECK`
re-confirmed on the renewed export. **So the pre-2009 composite is FIVE themes** — value,
quality, momentum, size, capital_discipline — and every figure in part (b) carries that label.

**IT IS BUILT FROM THE FREEZE'S FULL RAW TABLES, NOT FROM `data/backtest`.** That path is
selected on **2026** size — `sharadar_freeze._fresh_universe` ranks the TICKERS snapshot by
today's `scalemarketcap` and takes the top 3,000 — which `PANEL-EXT-RECHECK` measured at **3,747
price files, only 1,697 spanning 1999, and just 10.68% ending before 2009**. Using it would be
`B6`'s inverted universe in a new costume and would flatter any wider-pool result.

**CONSTRUCTION RULES, fixed now:**

* **ONE SHARED CALENDAR CUT, never a per-ticker tail** — `B6`'s defect, which voided the old
  110-date panel.
* **Delisted names are carried to a TERMINAL VALUE** from `ACTIONS`, never dropped and never
  forward-filled; a last close is the value of a security that ceased to exist (`E-5`'s rule),
  while an administrative end of data still censors.
* **Point-in-time market cap from `DAILY`**, which the freeze carries from **1998-12-01**.
* **Publication lag honoured on `SF1`** exactly as the live panel does.
* **READ ONCE.** The pool-size curve is computed once and reported. No second cut, no re-ranked
  ladder, no sweep. A failure to build correctly is reported as a failure, not worked around.

**WHAT IT SPENDS.** `RESEARCH_CHARTER` §4(a) names the eras as **1972-1989** and **1990-2008**,
read once each — so the boundary is **1990, not 1998**, and this spends the **late portion of the
second era**, leaving 1990-1998 as a stub of an era meant to be read whole, out of the charter's
own era order. **That is disclosed, not minimised.** It is licensed here because Don asked for it
explicitly and because what it tests — pool width on five themes — is *not* the shipped
construction, so the seven-theme question those eras exist for is **not** consumed. SPY began
trading in 1993, so a 1999-2008 benchmark may legitimately use SPY.

---

## 5. VOID CONDITIONS

1. **The decision rule is not restated after a number is read**, and the 3pp allowance is not
   moved (`W-28`: a pre-committed bar may not be relaxed after watching it fail).
2. **Arm 7's level is not placed on the main ladder** (§2b).
3. **No rung is called statistically significant**, and no figure is compared to an X7 floor.
4. **Part (b) is never quoted as a test of the shipped composite**, and never without the
   five-theme label.
5. **Nothing is adopted.** No live constant, no contract constant, no `CONFIG` change. A winner
   is **routed to Don** as a vintage event, exactly as `INDEX-BEST` was.
6. **`INDEX-BEST`'s pick and `INDEX-CHOICE`'s memo are not re-opened**; this adds a curve, it does
   not re-run a decision.

---

## 6. EXPECTATIONS, recorded now

1. **`C1` reproduces all three banked rungs at 0.000e+00** — 90/10.
2. **Return rises monotonically from the incumbent to the full panel** — 70/30. Three of the
   seven points are already banked and already rise (17.16% → 22.95% → 24.95%).
3. **The rule recommends the FULL PANEL rather than an interior rung** — 55/45. The drawdown
   step from 1,500 to full is only **0.21pp**, well inside 3pp, so the binding clause will
   probably be return rather than drawdown.
4. **Removing the penny/nano floor HURTS** (arm 7's paired delta is negative) — 70/30. `B13`
   measured dropping 384 penny names as helping the long-short and costing the long-only book, so
   the direction is genuinely uncertain, but the small end is where data quality is worst.
5. **The under-$300M share is below 5% even on the full panel** — 60/40. The top decile is
   quality- and size-tilted, so the composite should decline most micro-caps on its own.
6. **Part (b)'s curve is FLATTER than part (a)'s** — 60/40. Two themes are missing, and the two
   that remain strongest pre-2009 are the ones least dependent on pool width.
