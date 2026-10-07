# PREREG — `TIERED-POOL`: include smaller companies only if they clear a stricter bar

**Committed ALONE, markdown only, zero `.py`, BEFORE any runner for either arm exists. Every
threshold, every band boundary, every construction choice and the pass rule below are fixed here,
before a single figure is read.**

Don's idea, 2026-10-06: *"include smaller companies only if they clear a stricter bar than large
ones."* `UNIVERSE-BIAS` has just established that a flat wider pool **loses** on the corrected
universe (the advantage reverses from +7.24pp to −3.26pp) and that the widest book is 63.3%
micro-cap by weight. So the live question is no longer *"is wider better"* — it is **"can a
stricter bar at the small end buy back what width destroys?"**

---

## 0. Trial charge

**TWO equity trials, one per arm, booked in a separate commit BEFORE any runner exists.**
Equity `N` **262 → 264**. Hurdles **derived, never typed**:
`hlz_hurdle(262) = 3.3371678123106414`, `hlz_hurdle(264) = 3.3394457932855612`.

Don's instruction is *"one equity trial per arm"*, and that is what is charged. **The case for
THREE is stated rather than hidden:** `POOL-SIZE` charged its 1999-2008 proxy as its own trial,
on the reasoning that a separate measurement on a separately-built panel read once is a separate
search. The distinction taken here is that **§1's pass rule is a CONJUNCTION across both
periods** — an arm cannot pass on one period alone — so each arm yields exactly **one** verdict
and is one search. `MA6` holds that overstating `N` is the safe direction, so this reading is the
*less* conservative one and is flagged as such; a later reader who disagrees should amend upward.

**ZERO for the size-neutral diagnostic** (§3) and **ZERO for the coverage kill** (§2c): a census
and a control, which under `MB1-SEL` can only ever BLOCK and never produce.

`MB31`: the next adopt-set flip is seed **1017 at equity `N` = 688**, so **no permutation floor
can move** and this register compares nothing to one.

---

## 1. The pass rule, fixed before any number

**Don's words, verbatim:** *"an arm passes only if it beats the incumbent on net Roth return in
BOTH periods AND in both halves of 2009-2026, with max drawdown no more than 3pp worse than the
incumbent's in either period."*

Made precise now, because each clause has a way of going wrong:

1. **`beats` is STRICT and carries NO tolerance.** `arm_roth > incumbent_roth`, exactly. A tie
   fails. (`POOL-SIZE` §1's rule, reused.)
2. **Four return comparisons, all required:** 2009-2026 full, 2009-2026 early half, 2009-2026
   late half, and the 1999-2008 proxy.
3. **The drawdown test is written out WITH ITS SIGN, because drawdowns are negative and `S10`'s
   first cut once reported a 2.61pp WORSENING as an improvement:**
   `arm_mdd >= incumbent_mdd - 0.03`. Both periods, each against **that period's own**
   incumbent.
4. **The halves are the panel's own EMBARGOED halves**, as `POOL-SIZE` and `INDEX-CHOICE` use —
   not a fresh split, and the boundary date is reported.
5. **The rule CAN fail both arms, and that outcome is as reachable as any other.** It can also
   pass an arm whose advantage is not statistically separable from the incumbent's; it is a
   PREFERENCE rule, not a significance test, and **no arm will be called significant.** Every
   margin ships with its own MDE at 50% and 80% power (`MB22`, `RUN_RULES` A11) and **every
   critical value is LABELLED UNCALIBRATED** — `V2G` and `R1-VAR`: no calibrated floor exists for
   a paired within-panel difference, and **no X7 floor is quoted anywhere**.

---

## 2. The arms

**Everything except the selection rule is the incumbent's, unchanged:** the shipped composite at
flat 1/7 over the seven deployed themes, **score** weighting, the **8%** position cap, the
**0.30** no-trade band, **quarterly** rebalance, and the shipped size-aware measured cost model.
`served_index_book.book_fn` / `valquo_index.build_index` are **called, never re-implemented**
(`B7`).

### Arm A — stricter-by-size hurdle

Bands by **point-in-time market cap**, half-open so a name at exactly a boundary is in the
**higher** band:

| band | selection |
|---|---|
| `cap >= $10B` | top **10%** of that band, that date |
| `$2B <= cap < $10B` | top **5%** |
| `$300M <= cap < $2B` | top **2.5%** |
| `cap < $300M` | **excluded** |

**The percentile is WITHIN BAND AND WITHIN DATE.** That is the whole content of "a stricter bar
than large ones": a $1B name must be in the top 2.5% of $1B-ish names, not the top 2.5% of
everything. Ranking across the whole cross-section would make the three numbers a single global
cutoff in disguise.

**The book is the UNION of the three band selections**, then score-weighted with the 8% cap. **The
no-trade band is applied WITHIN each band** at the shipped `BAND_WIDTH`, which is the faithful
generalisation of a single-pool band; applying it to the union would let a name hold its place by
drifting into a different band, which is a different rule.

**Pre-committed floors, so a thin band is reported rather than silently producing a one-name
tier:** `MIN_PER_BAND = 5`. Dates where any band selects fewer are **counted and reported**, and
the count ships in the artifact. The book is also reported against the contract's
`CONTRACT_MIN_POSITIONS`, as `INDEX-BEST` and `N1` do.

### Arm B — arm A plus a junk filter on the two smaller bands

Don's framing, after Asness–Frazzini–Israel–Moskowitz–Pedersen (2018), *"Size Matters, If You
Control Your Junk"*. **The filter applies to the two bands below $10B only**; the `>= $10B` band
is arm A's unchanged. A name below $10B must ALSO satisfy all three:

1. **positive TTM net income** — `_ttm(rows, as_of, ("netinc",)) > 0`
2. **positive TTM free cash flow** — `_ttm(rows, as_of, ("fcf",)) > 0`
3. **leverage not in the worst third of its date's cross-section** — see the direction note below

**`_ttm` is the SHIPPED point-in-time accessor and is CALLED, not re-implemented** (`B7`). That
matters for more than tidiness: it already collapses restatements (`D10-a` — a restatement
APPENDS an ARQ row, and 3.15% of `(ticker, reportperiod)` groups carry more than one `datekey`),
requires four distinct quarters, and refuses a window spanning more than `TTM_MAX_SPAN_DAYS`. A
hand-rolled sum would silently understate a flow and **read as a junk company**, which is the
exact direction that would flatter this arm.

**Leverage is a STOCK and is therefore point-in-time at a filing**, so it is taken from
`fundamentals_pit` as `debt / equity` on the same as-of row.

**THE CURRENCY TRAP DOES NOT BITE HERE, AND THE REASON IS STATED BECAUSE `P7` IS THIS PROJECT'S
MOST EXPENSIVE BUG.** Raw line items are in the **reporting** currency while market cap is USD.
All three conditions are currency-invariant: `fxusd > 0`, so the SIGN of `netinc` and `fcf` is
unchanged by conversion, and `debt / equity` is a ratio of two same-currency quantities. **No
conversion is applied, and none is needed.** A fourth condition mixing a local flow with a USD
cap would need one, and no such condition is registered.

### 2a. The leverage DIRECTION, resolved here on an external anchor, before any number

Don's words are *"leverage not in the bottom third of its date's cross-section."* **Read
literally that excludes the LEAST levered third**, which inverts the cited paper: AFIMP's junk is
*low* profitability and *high* leverage, and their finding is that the size premium strengthens
once junk is controlled. Excluding the least-levered names would control junk **backwards**.

**Resolution: the filter requires leverage NOT to be in the WORST (most-levered) third** — i.e.
`debt/equity` must be at or below its date's 2/3 quantile among the rows the filter can evaluate.

**This is a reading of Don's wording and is declared as one.** It is resolved on the **paper's own
direction**, an anchor that exists independently of this panel and predates the register — which
is `E-6`'s discipline, where a contaminated choice was settled on an external anchor rather than
on which reading flattered the arm. **The counterfactual is recorded: had the paper's direction
been the other way, the literal reading would have been taken.** The inverted variant is **NOT
run** and carries no verdict; running both would be a two-cell grid on a clause Don stated once.

### 2b. Known construction facts, established before registering

Recorded so the register cannot be read as having assumed them:

* **The panel carries NO raw values.** `UNIVERSE_BIAS_PANEL_full.pkl` holds themes,
  `market_cap`, `sector`, `fwd_ret`, `bench_ret` and nothing else, and `keep_numbers=True` adds
  only the **z-scored** `z_*` columns plus a few diagnostics. **A z-score loses the zero point**,
  so conditions 1 and 2 are NOT recoverable from any panel the shipped builder produces — which
  is why arm B reads the provider directly through `_ttm`.
* **`netinc`, `fcf`, `debt` and `equity` are all present** in the export's `fundamentals.csv` and
  in `WRDSProvider._KEEP`, verified on the full-universe export before this register was written.
* **Both periods are run on the CORRECTED universe**, never on `data/backtest`, whose universe
  `UNIVERSE-BIAS` measured to be selected on 2026 market cap — 80.61% of the names that were
  under $300M in 2009 and later died are missing from it. **A tiered-pool arm is a claim about
  the small end, so running it on that universe would be measuring the defect.**

### 2c. The coverage kill — PRE-COMMITTED, read BEFORE arm B is scored

Arm B's filter can only be applied where its inputs resolve. A name whose TTM cannot be formed
must **fail the filter** (the conservative direction), but if that happens on too many rows the
arm stops being a junk filter and becomes a **data-availability screen wearing one's name** —
`S10`'s failure mode, and `W-28`'s: *"it silently becomes that input's removal arm."*

**KILL: the three conditions must be jointly evaluable on at least 70% of the sub-$10B rows arm A
selects from.** Below that, **arm B does not run, is reported NOT-RUN, and no figure from it is
quoted.** The 70% is **inherited, not chosen**: it is the panel's own `theme_coverage` rule,
quoted at 0.70 in `PANEL-EXT-CENSUS`. **Measured and read in its own pass, before any arm-B
return exists.**

---

## 3. The size-neutral diagnostic — NO VERDICT, and it cannot acquire one

Rank within each band and select the same count per band as arm A, **ignoring the composite's
cross-band level** — i.e. a pure within-band sort. Reported with **no pass rule, no comparison to
Don's bar, and no verdict**, so nobody can pick it after seeing it.

**Pinned by test:** the diagnostic's figures may not appear in any `decide`/pass-rule input, and
the artifact's verdict field for it is the literal `NO-VERDICT`. This is `E-3`'s treatment of its
own degenerate kill and `MB21`'s of a diagnostic: **a number computed after the fact that could
be promoted on sight is a number that will be.**

---

## 4. Part (b) — 1999-2008, a LABELLED five-theme PROXY, read ONCE

The same two arms on 1999-2008, built from the freeze's **full raw** SEP/SF1/SFP through the
shipped builder — **never `data/backtest`**.

**It tests the TIERING, not the shipped composite, and must say so wherever it is quoted.**
`PANEL-EXT-CENSUS` established that two of the seven themes have **no pre-2009 source**
(`institutional` has zero, `insider` cannot reach the 70% rule before 2008), so this is a
**five-theme** proxy. Its **LEVELS are not comparable** to part (a)'s and quoting them side by
side as if they were is a **void condition**.

**Read ONCE.** No second reading, no re-cut, no re-threshold after seeing it.

**Disclosed before the run:** it spends the **late portion** of `RESEARCH_CHARTER` §4a's
1990-2008 era, leaving 1990-1998 a stub of an era meant to be read whole, out of the charter's
own era order. `POOL-SIZE` made the same disclosure for the same window.

---

## 5. Required reporting — a size bet must not be mistaken for selection

For **every** arm and both periods, and an arm's verdict is **VOID** if any of these is omitted:

* **net Roth return**, full and both halves, and max drawdown;
* **the share of book weight below $2B**, and below $300M (which arm A excludes, so it should be
  zero — reported as a check on the construction rather than as a result);
* **the SMB loading** and the **intercept** from FF5+MOM at `R1`'s `LAG = 1`, with `R1`'s own
  SPY-on-MKT alignment control reported beside them;
* turnover and realised one-way cost from the shipped model;
* book size min/median/max, dates below `MIN_PER_BAND`, dates below `CONTRACT_MIN_POSITIONS`;
* for arm B, the coverage figure from §2c and **how many names each condition removes
  separately**, so a three-condition filter is not credited to whichever condition is cheapest.

**NO ALPHA CLAIM.** `INDEX-CHOICE` forbade one in advance and `POOL-SIZE` inherited the
prohibition; this inherits it again. **An intercept here is a DECOMPOSITION.** And
`UNIVERSE-BIAS` part 2 sharpened why it matters: on the corrected universe **not one** pool rung
had an intercept separable from zero, while the SMB ladder was essentially unchanged — so a
tiered arm that looks better is a size-exposure question until the intercept says otherwise.

---

## 6. Void conditions

1. Quoting part (b)'s **levels** beside part (a)'s as comparable, or describing part (b) as a
   test of the shipped seven-theme composite.
2. Changing any band boundary, percentile, the `MIN_PER_BAND` floor, the 70% coverage kill, or
   the pass rule **after any return is read**. `W-28`: a pre-committed bar may not be relaxed
   after watching it fail.
3. Adding a third arm, a percentile grid, or a second leverage direction.
4. Promoting the §3 diagnostic to a verdict, or comparing it to Don's bar.
5. Running either arm on `data/backtest` for either period.
6. Reporting arm B without its §2c coverage figure, or reporting it at all if the kill fires.
7. Calling any arm **significant**, or comparing any figure to an X7 floor.
8. **Adopting anything.** The pool choice is a vintage event and Don's; **the 2026-10-22
   rebalance stays on the incumbent** whatever this returns.

---

## 7. Expectations, recorded before any number so they can be scored

1. **Arm A FAILS the rule, 65/35.** `UNIVERSE-BIAS` measured the corrected ladder essentially
   flat from the incumbent to 1,500 (18.02 / 17.83 / 18.17 / 17.76) with the damage concentrated
   in the full pool, which suggests the small end has little to give at any strictness.
2. **Arm B beats arm A on return, 60/40** — if the junk filter does anything, this is the
   direction AFIMP predicts.
3. **Arm B still fails the rule, 55/45**, mostly on the drawdown clause rather than on return.
4. **The §2c coverage kill does NOT fire, 75/25**: `netinc` and `fcf` are core SF1 fields.
5. **Both arms carry a LARGER SMB loading than the incumbent's +0.219**, 80/20 — they hold
   smaller names by construction.
6. **No intercept is separable from zero on either arm**, 85/15, following part 2's finding.
7. **The 1999-2008 proxy is KINDER to the tiered arms than 2009-2026**, 55/45, because that
   decade's small-cap premium was large and the dot-com crash punished junk specifically.

---

## 8. Not done, named so it is not mistaken for done

No percentile sweep; no fourth band; no alternative junk definition (profitability, volatility
and distress are all AFIMP junk markers and **none is registered**); no inverted leverage
direction; no sector control; **no adoption**; and **no claim about 1990-1998**, which stays
blind.

---

*`TIERED-POOL`. Register committed alone; trials booked separately before any runner exists.
Nothing below this line is edited after a number is read.*
