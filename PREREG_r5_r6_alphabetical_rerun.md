# PRE-REGISTRATION — R5 + R6: the two re-derivations B12 voided

**Registered 2026-08-13, blind.** Committed **ALONE** — one `.md`, zero `.py` — and a strict git
ancestor of every commit that measures anything.

**One register, two ledger rows, six signals, six trials.**

---

## 0. THE B12 LESSON, STATED UP FRONT — AND IT IS WORSE IN THE CODE THAN IN THE LEDGER

Audit **B12** established that `WRDSProvider.universe` returned `sorted(keys)[:limit]`, so **every
"800 largest names" result in this project's history was names beginning with roughly A through C**
— an arbitrary alphabetical third, not a large-cap tier. `CLAUDE.md` lists the consequences and
names these exact items among them.

**The standing rule this register operates under: every 800-era number is UNVERIFIED until
re-measured, and a marginal rejection carried on a voided universe is precisely what B12 exists to
force a re-run of.**

**Four live sites still present voided figures as current evidence. Located before writing this,
and this is the part the ledger did not have:**

| site | what it says | why it is void |
|---|---|---|
| `settings.py:222-224` | the three anomalies are *"all wrong-signed here"*, median IC −0.014 / −0.072 / −0.025, **"400 names, 12y, 110 rebalances"** | **DOUBLY void — 400 names is below even the 800 tier, and 110 rebalances is the pre-B6 inverted-universe panel** |
| `settings.py:243-251` | `sm_breadth` +2.37, `sm_avg_position` +1.26, `sm_holders` +1.57, `sm_conviction` +1.25, *"800 large caps / 110 rebalances"* | alphabetical universe **and** the void panel |
| `factors.py:294-296` | the anomalies *"REJECTED — every one carried the wrong sign"* | same 400-name measurement |
| **`factors.py:314-316`** | **`sm_breadth` replaces `inst_breadth` in the LIVE institutional theme mean, justified by *"IC t +2.37 vs +1.48 on 800 large caps"*** | **A LIVE SCORING DECISION RESTING ON A VOIDED NUMBER** |

**The fourth is the serious one.** `df["institutional"] = df[["z_inst_accum", "z_sm_breadth"]]` is
what the product scores today, and the recorded reason for choosing `sm_breadth` over `inst_breadth`
is a figure B12 voided. `sm_breadth`'s corrected-panel value is **+1.73** (recorded at
`settings.py:280`), and **`inst_breadth`'s corrected-panel value has never been put beside it**.
This register measures both — see §4 — at **zero trial cost**, because both are already registered
and already carry a `z_` column.

---

## 1. SCOPE — SIX SIGNALS, NOT NINE, AND THE TASK'S FRAMING IS CORRECTED IN BOTH DIRECTIONS

### 1a. R5 is THREE anomalies, not four

The task names four: short-term reversal, idio-vol, MAX, **low-vol**. **Low-vol needs no re-test.**
`neg_vol` is registered at `settings.py:212`, sits **inside** the live `low_risk` theme mean
(`factors.py:297`), and has a corrected-panel measurement already (the `low_risk` theme reads IC
**+0.46** on the 69-date panel). Re-testing a signal that is already measured on the corrected
universe would charge a trial for a number the project already has.

**R5's arms are the three that carry NO `z_` column, NO coverage entry and NO IC on any universe
this project's methodology rule permits deciding on:** `neg_ret_1m`, `neg_max_ret`, `neg_idio_vol`.
**Verified, not assumed:** the banked corrected panel `panel_corrected_69d.pkl` (69 dates, 2,531
names, 46 `z_` columns) contains `z_neg_vol` and does **not** contain `z_neg_ret_1m`,
`z_neg_max_ret` or `z_neg_idio_vol`.

### 1b. R6 is THREE conviction signals, not five — and the task's premise about `sm_breadth` is wrong

The task says *"`sm_breadth`'s t 2.37 was 800-era, unverified on full"*. **It has been verified on
full: t +1.73**, recorded at `settings.py:280` inside the `sm_elite_conviction` note. And
`sm_elite_conviction` itself was measured and rejected at **+1.32** on 2026-08-01.

**R6's arms are the three that were never re-run:** `sm_conviction`, `sm_holders`,
`sm_avg_position` — computed into the frame at `factors.py:199-202` but absent from `NUMBER_THEME`,
so they carry no `z_` column and no IC. Confirmed absent from the banked panel.

**A routing fact, not a verdict:** both family members that HAVE been measured on the corrected
universe came back weak (+1.73, +1.32). **That lowers the prior and does not substitute for the
measurement** — which is the whole of B12's argument.

---

## 2. Method

### 2.1 Registration is MEASUREMENT, not SCORING — and that is verified, not asserted

The six are added to `NUMBER_THEME` in `settings.py`. **This is the S2 `cash_op_prof` pattern**
(`settings.py:227-242`), which the record already describes and verified: registering a number
there gives it a `z_` column, a coverage entry and a per-signal IC row, **but it only SCORES if
`factors.py` names it in a theme mean.**

**Checked in the code rather than trusted from the comment:** every theme mean is an **explicit
column list** — `df["low_risk"] = df[["z_neg_beta","z_neg_vol"]].mean(axis=1)` and
`df["institutional"] = df[["z_inst_accum","z_sm_breadth"]].mean(axis=1)`. `NUMBER_THEME` feeds
`NUMBERS_ALL` (what gets z-scored) and the reporting layer; **`BUCKET_FACTORS` and the explicit
lists drive scoring.** So registration cannot move the composite.

**C1 GATES ON THAT BEING TRUE.** `long_short_tstat` must come back **exactly**
`2.8360640685320595`. **This is NOT a vintage event** — no scored quantity changes — and if C1
fails, it is, and the run aborts.

### 2.2 One panel build

`build_fundamental_panel(..., lookback_years=CONFIG.backtest_lookback_years, horizon=63,
keep_numbers=True)` on the **full universe**. One build, all six signals plus every incumbent
`z_` column on the same rows, so no arm's IC can differ from another's because of a date set.

### 2.3 The statistic, and the SHIPPED function

Per-signal IC via **`fundamental_panel.per_signal_ic`** — the shipped function, imported not
re-implemented, which is *"the same measurement used to accept or reject a signal"*. Per-date
Spearman of the standardized number against `fwd_ret`, then the median and a *t* across dates.

**SIGN CONVENTION, PINNED BY TEST BECAUSE IT DECIDES EVERY VERDICT:** all three R5 signals arrive
**pre-negated** from `_price_extras` (`neg_ret_1m = −(1-month return)`, `neg_max_ret = −max(daily
return)`, `neg_idio_vol = −idio_vol`). **A POSITIVE IC therefore means the published anomaly
REPRODUCES; a NEGATIVE IC means it runs BACKWARDS on this universe.** The R6 three are not negated
and higher = more smart-money interest, so **positive** is again the confirming direction.

### 2.4 Bars

**Each signal's OWN within-date permutation p95 on the IC *t*** — the signal's `z_` column shuffled
within each rebalance date, 500 draws, every draw banked. This is the within-column scheme; the
`placebo_panel` machinery is not used, because it is exactly invariant on a composite and cannot
calibrate a column-shaped object.

**Both halves**, boundary embargoed, **and sign-stable**.

**Two reference bars are reported and NEITHER is the verdict:** X7's calibrated **2.71** was
calibrated on the **maximum theme IC across nine themes**, not on a named per-signal IC, so quoting
it here is an extrapolation and is labelled one; the historical **2.0** is the convention the
settings comments used and is carried only so the new numbers sit beside the old ones on the same
scale.

### 2.5 Verdict rule, fixed now

> **REPLICATES** iff the median IC is **positive** AND the IC *t* clears the signal's **own**
> permutation p95 in **BOTH** halves with the **same sign** in both.
>
> **CONTRADICTS-PUBLISHED-SIGN** iff the IC *t* is below its own permutation **p5** in both halves —
> i.e. the anomaly reproduces **backwards** at significance. This is a real possible outcome (the
> 400-name comment claims exactly this) and it is reported as its own verdict, never folded into
> "rejected". O3/O4/O5's treatment.
>
> Anything else, including ambiguity against any bar, is a **NULL** (`RUN_RULES` A6).

**Coverage floor:** a signal covering fewer than **30%** of panel rows, or scoring fewer than **24
dates per half**, is **VOID — UNDERPOWERED BY CONSTRUCTION**, not NULL. 30% is the floor
`pead_drift` was rejected under (25.1% against a 30% floor), so it is this project's own precedent
and not a number chosen here.

---

## 3. Kill conditions

* **R5.** A signal that returns NULL or CONTRADICTS is dead. **There is no re-cut at another
  horizon, another window length, or with a size or liquidity screen** — that would be searching
  the space the audit's own rejection already covered.
* **R6.** Same. And **if all three return NULL, the SF3 conviction family is CLOSED** — five of five
  members will then have been measured on the corrected universe with none clearing, and the ledger
  row says so rather than leaving it open.
* **Neither row may be closed on this register's evidence if C1 fails.**

---

## 4. Free by-products — measured, reported, and charged NOTHING

These are **already-registered numbers already carrying a `z_` column**. Reading their IC off the
same frame is not a new search over the data and charges no trial (session 8's precedent: declining
to search keeps the denominator).

1. **`neg_vol` and `neg_beta`** — the low-volatility anomaly as it is actually deployed, on the
   corrected universe. This is what makes R5's scope correction checkable rather than asserted.
2. **`sm_breadth` vs `inst_breadth`, head to head, on the corrected panel.** **This is the number
   that matters most in the whole register**, because `factors.py:316` swapped the second for the
   first in the LIVE institutional theme on the strength of *"+2.37 vs +1.48 on 800 large caps"* —
   a comparison B12 voided. **If the ordering reverses on the corrected universe, a live scoring
   decision is resting on a voided number**, and that is a finding to route, **not** a change to
   make here: swapping a theme input is a construction change and a **vintage event**, and it needs
   its own register.
3. **`sm_elite_conviction`** at +1.32, re-read from the same frame for continuity.

**No by-product carries a verdict**, and none may be quoted as a pre-registered result.

---

## 5. Controls

| id | control | gating? |
|---|---|---|
| **C1** | **The composite is BIT-IDENTICAL with the six registered**: `long_short_tstat` exactly 2.8360640685320595, plus `top_decile_alpha` 0.07174142332098163, HAC 2.6199121240414884, monotonicity −0.8909090909090909. Runs in its **OWN pass** and aborts before any signal is read. | **YES** |
| **C2** | Canonical panel: 69 dates, ~2,531 names, label `full`, and `keep_numbers` actually produced the six `z_` columns — asserted, not warned. | **YES** |
| **C3** | **Coverage first** (COVERAGE RULE): per-signal coverage and date count **before** any IC is read. A signal below the §2.5 floor is VOID. | no |
| **C4** | The sign convention of §2.3, pinned by a test on a synthetic frame where a known-direction signal must produce a known-sign IC. | no |
| **C5** | The four stale sites of §0 are quoted verbatim in the artifact, so the correction is checkable against what was there. | no |
| **C6** | Redundancy: each new signal's within-date rank correlation against every incumbent theme and against the other five. A signal that is an incumbent under a new name is reported as such. | no |
| **C7** | **R5's own earlier pre-registration still binds**: *a positive result on the two volatility cousins needs the size-interaction check, because `low_risk` was zeroed for cancelling the small-cap tilt.* If `neg_max_ret` or `neg_idio_vol` REPLICATES, its correlation with `size` and its IC within size quintiles are reported before any adoption language is used. | no |

**Every permutation draw is banked** (`RUN_RULES` A9).

---

## 6. Void conditions

1. Any `.py` in this file's commit, or this file not being a strict ancestor of every measurement
   commit.
2. Any signal beyond the six named in §1.
3. Any change to `factors.py`'s theme means, or any other edit that makes a registered number
   SCORE. Registration is measurement-only.
4. A failing **C1** or **C2** with any signal's IC nevertheless read or reported.
5. Substituting X7's 2.71 or the 2.0 convention for the per-signal permutation bars.
6. Re-cutting a dead signal at another horizon or under a screen (§3).
7. Editing this register after any result exists.

---

## 7. Expectations, with odds, written before any result

1. **All three R5 anomalies come back NULL or CONTRADICTS — none replicates.** 70/30. The
   literature's short-horizon anomalies are documented to have decayed post-2000, and this panel is
   large-cap tilted where they were always weakest.
2. **At least one R5 signal is CONTRADICTS-PUBLISHED-SIGN**, not merely null. 55/45 — the 400-name
   comment claims all three were wrong-signed, and while that universe was void, a sign is a
   coarser thing than a *t* and may survive the universe change.
3. **`neg_idio_vol` is the closest to replicating of the three.** 50/50. O3 measured `idio_vol`
   sorting in the *confirming* direction on the options panel (+2.5158), which is weak evidence but
   is this project's own.
4. **All three R6 conviction signals come back NULL.** 80/30 — the two measured family members
   read +1.73 and +1.32, and these three were the weakest of the five even on the flattering
   alphabetical universe.
5. **The SF3 family closes**, i.e. all three null. 75/25.
6. **`inst_breadth` does NOT overtake `sm_breadth` on the corrected panel**, so the live swap
   survives its voided justification. 60/40 — and I hold this one weakly, because the original gap
   (+2.37 vs +1.48) was measured on the universe B12 voided and `sm_breadth` has already fallen to
   +1.73.
7. **At least one of the six is below the 30% coverage floor and returns VOID.** 45/55 — the SF3
   detail is thinner than the aggregate 13F.
8. **C1 holds and the composite is bit-identical.** 90/10 — the theme means are explicit lists and
   S2 already demonstrated it once.

---

## 8. Trial cost

**Six equity trials — three for R5, three for R6.** **Equity `N` 212 → 218**, re-measured from
`research_log.detail()` after this session's merge rather than quoted from `CLAUDE.md`. The haircut
moves **√(2·ln 212) = 3.2731 → √(2·ln 218) = 3.2816**, under 0.009 of a *t*: the ledger's own
"trial cost is now negligible" argument, restated at today's `N`.

Options 287 and infra 11 are untouched. The `n` column is written as the literal **`n=6`** form
`research_log._parse` requires.

`BACKTEST_RESULTS.json` is refreshed from a clean tree at the new denominator — and this run's
refresh additionally carries the six new signals into the per-signal IC table for the first time.

---

## 9. What this register does NOT do

* **It does not change any score.** Registration is measurement-only (§2.1), the composite is
  gated bit-identical, and no theme mean is touched. **Not a vintage event.**
* **It does not re-test low-vol, `sm_breadth` or `sm_elite_conviction`** — all three are already
  measured on the corrected universe (§1) and are reported as by-products.
* **It does not repair the four stale comment sites' underlying decisions.** The comments are
  corrected to say what is now measured; the **live swap of `inst_breadth` for `sm_breadth` is
  ROUTED, not changed** (§4.2), because that is a construction change and a vintage event.
* **It does not search for a better version of any signal** — no alternative windows, no screens,
  no interactions beyond C7's conditional check.
