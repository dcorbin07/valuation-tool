# PRE-REGISTRATION — D6/D7: THE ANALYST ESTIMATE-REVISION REGISTER
## Does a per-analyst, point-in-time EPS revision signal carry incremental information the seven incumbent themes do not already have?

**Registered 2026-08-25. Committed ALONE, markdown only, zero `.py`, a strict git ancestor of
every commit that computes an outcome statistic. 1 equity trial, booked in its own commit BEFORE
any runner exists: equity `N` 242 -> 243, hurdle 3.3132877 -> 3.3145321.** Counters re-read from
`research_log.detail()` at registration rather than quoted. **ADOPTS NOTHING** — adoption is a
vintage event and Don's decision.

`D6` and `D7` are ONE decision, as the ledger records. `D6` has been PARKED since 2026-08-06 on
*"no retail point-in-time revisions exist at any price; the path is IBES via WRDS"*. `WRDS-CENSUS`
opened that path and `W-3b` proved the join. This register is what the park was waiting for.

---

## 0. NON-BLINDNESS, DISCLOSED HERE RATHER THAN DISCOVERED LATER (`V6-OPT` §0.5's shape)

**This register is blind to the OUTCOME and is NOT blind to the CONTROLS, deliberately, and the
task required exactly that.** Two things were measured before a word of this file was written:

1. **The coverage census** (§4). The `COVERAGE RULE` requires it, and `O-1` returned **0.19%
   power** three days ago because a coverage figure measured on one population was applied to
   another. A power section written from an assumed coverage is worthless.
2. **The costume kill** (§5, K1). The task's own instruction is that a price-momentum costume
   *"must be killed by a pre-outcome correlation kill, not discovered afterwards"*. A kill that
   runs after the arm is not a kill.

**What follows from that, and it binds:** the K1 bar of **0.60 is NOT chosen by me.** It is this
record's standing costume bar, used verbatim by `E-1`'s K2 (which **withdrew** an arm at 0.6114),
`E-3`'s K2 and `MB18`'s C2. Re-using a pre-existing bar rather than picking one with the estimate
in view is `MB1-SEL`'s discipline. **Expectation (2) in §8 is recorded UNSCORABLE for the same
reason** — I already know the answer, so predicting it is worth nothing.

**No IC, no correlation with `fwd_ret`, no return relationship of any kind has been computed.**
The candidate has never been scored against an outcome.

---

## 1. THE OBJECT, DECLARED PRECISELY. NO SWEEP, NO GRID, NO VARIANTS

The grid is the failure this record has paid for most often — `S23` refused one, `MA58-SEAS`'s
C-DEPTH showed a two-point sweep telling opposite stories, and the param-search precedent went
**+8.43%/yr in-search to −0.04%/yr on the locked hold-out**. Every choice below is fixed here and
**may not be moved after any outcome is seen.**

**Source pair — and the ledger's own warning is why this is stated first.** `ibes.det_epsus`
(**split-ADJUSTED** detail estimates) with `ibes.act_epsus` (**split-ADJUSTED** actuals). The D6
row records that the pull it licensed committed the exact error it warned against, pairing
ADJUSTED estimates with UNADJUSTED actuals — *"an adjusted estimate against an unadjusted actual
is a units error that reads as a surprise"*. **Both pairs are on disk, so the right choice is
possible and not automatic. This register uses the ADJUSTED pair and nothing else**, and the
unadjusted files are not opened.

**Filters, all three declared because a naive `SELECT` mixes horizons:** `measure = 'EPS'`,
`usfirm = '1'`, and **`fpi = '1'` (FY1, the next unreported annual period)**. `fpi` is the
horizon code; the sample carries at least 1, 2, 6, 7, 8 and 9, and pooling them measures a
different object on every row.

**The point-in-time gate is `actdats`, the IBES activation date** — the date the estimate was
available *in the database*. `anndats` (when the analyst issued it) is the looser alternative and
is **not** used: an estimate can be announced before it is retrievable, and a signal built on
`anndats` would be usable only by someone who was not reading IBES. `revdats` is IBES's *review*
date — the date the estimate was last confirmed **still current**, not the date it changed — and
using it as a revision date is a known error. **It is not used.** A revision's date is the
`actdats` of the estimate that superseded the previous one.

**A REVISION** is a pair of consecutive estimates by the **same `(analys, estimator)`** for the
**same `(ticker, fpedats)`**, ordered by `actdats`, whose `value` **changes**. Its **sign** is the
sign of the change. Unchanged re-confirmations are not revisions. *This construction is the whole
reason the item needs `det_epsus`: a consensus change is available from `statsum` and does not
require per-analyst timing at all.*

**THE SIGNAL, one line:** for name *i* at rebalance date *t*, over revisions with
`t − 91 calendar days < actdats <= t`,

> `rev_ratio(i,t) = (U − D) / (U + D)`, defined only where `U + D >= 3`.

**91 days** is one quarterly rebalance interval, matched to the panel's own frequency, not tuned.
**The floor of 3** is declared here; §4 reports what coverage costs at 1, 2, 3, 5 and 10 so a
reader can see the price, and **the arm uses 3 and nothing else.**

**Declared sign: POSITIVE** — upward revisions predict higher forward returns. This is the
published direction (Chan–Jegadeesh–Lakonishok 1996; Gleason–Lee 2003) and is fixed before any
measurement.

---

## 2. THE GRAVEYARD, ARGUED PAST IN WRITING

### 2a. PEAD — a different object, and the difference is structural rather than rhetorical

Earnings **surprise** is the gap between a realised announcement and what was expected. Estimate
**revision** is a change in the forward expectation itself. Three concrete separations:

* **Different information event.** PEAD's event is the *company's* announcement; a revision's
  event is an *analyst's* opinion change. They do not happen on the same days.
* **Different frequency, measured.** An announcement occurs about four times a year. **69.1% of
  our panel cells carry three or more revisions inside a single quarter** (§4) — the revision
  process runs continuously between announcements, where PEAD is silent by construction.
* **No realised outcome enters.** `rev_ratio` never touches an actual. `act_epsus` is declared in
  §1 only because a surprise-based successor would need it and the pair must be named; **the arm
  as registered does not read it**, and an AST test will pin that.

**And it is checked rather than argued: the panel already ships `z_pead_car` and `z_pead_drift`,
and K2 gates on them.**

### 2b. Momentum — killed pre-outcome, not afterwards

Prices rise when analysts revise upward, so a revision signal is a live candidate to be price
momentum wearing a fundamental name — and momentum is **already an incumbent**, so a costume
would be re-ranking the product. **K1 (§5) is the kill and it ran BEFORE this file existed.**

### 2c. The four "structurally orthogonal" items — and if that were my mechanism I would kill this now

`U2`, `MA31`/`MA32`, `MA58` and `MB18` were each motivated by being structurally orthogonal to
the incumbents. All four were **confirmed orthogonal** (mean R² 0.027–0.145) and **not one
cleared its bar.** `CLAUDE.md` already names that motivation as one nobody should run again.

**My mechanism is NOT orthogonality, and I state the consequence in advance so it cannot be
claimed afterwards: a LOW R² on the incumbents would be NO evidence for this item.** The
mechanism claimed here is specific and economic — **analyst underreaction / gradual information
diffusion**, the documented reason revisions predict. If this register's defence ever reduces to
*"but the signal is new information"*, it has failed and the four corpses above are the reason.
The R² is reported in §6 as a **diagnostic carrying no verdict.**

---

## 3. PRIMARY STATISTIC, BASES, AND THE BAR

**Primary: the incremental information coefficient** — the per-date Spearman IC of `rev_ratio`
against `fwd_ret` after residualising the candidate on the incumbent themes, i.e. the shipped
`U2`/`MB18` template via `valuation/studies/incremental_ic.py`.

**BOTH BASES ARE CO-PRIMARY AND THE ARM MUST CLEAR BOTH** (`MB18`'s rule; taking whichever is
kinder is `MA58`'s void condition 5, choosing the design to buy power):

* **basis six** — the six full-window incumbents, `institutional` dropped. **69 effective dates.**
* **basis seven** — all seven. **49 effective dates**, first 2014-01-17, i.e. a post-2014 test.

**BAR: `|t| > 2.71`** — `X7`'s **calibrated** theme-IC floor, which `MB31` proves unmoved at every
equity `N` below 247 (we register at 243). The retired 2.0 convention is **not** used: `X7`
measured **39% of pure-noise draws** producing at least one theme at 2.0 or better.

**Both halves must clear, on the EFFECTIVE dates, and the signs must agree.** Measured splits:
basis six **34/34** at boundary 2017-07-20; basis seven **24/24** at 2020-01-22; both report
`ok = True` against the shipped `MIN_DATES` floor. Splitting raw dates where the statistic scores
effective ones is the defect `MB7` exists to catch.

**Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6), never a judgement.

---

## 4. COVERAGE AND POWER — MEASURED ON OUR PANEL, MB22 AT BOTH VOCABULARIES

**Population: the corrected panel — 113,945 cells, 2,531 names, 69 quarterly dates,
2009-01-15 to 2026-01-28.** Measured here, from the pulled IBES files, joined through CRSP
**dated** name intervals with `MaskedCusip` (`W-3b`'s route, imported and not re-implemented):

| quantity | measured |
|---|---|
| CRSP intervals reach | **2,271 of 2,531 panel names (89.7%)** — a ceiling before IBES is consulted |
| IBES FY1 EPS rows in window | 3,282,483 over 14,501 distinct cusips (931 masked) |
| rows mapped INTO our universe | 1,712,698 over 2,232 names |
| **revisions** | **1,314,963 over 2,229 names** |
| cells with >= 1 revision | 90,429 (**79.36%**) |
| cells with >= 2 | 84,392 (74.06%) |
| **cells with >= 3 (the declared floor)** | **78,723 (69.09%)** |
| cells with >= 5 | 67,539 (59.27%) |
| cells with >= 10 | 45,628 (40.04%) |
| distinct names ever covered | 2,214 of 2,531 (**87.48%**) |
| **dates with any coverage** | **69 of 69** |
| per-date covered cells | min 970, median 1,258, max 1,731 |

**THE COVERAGE IS UNIFORM ACROSS THE WINDOW, AND THAT IS THE FACT THAT MAKES THIS REGISTER
DIFFERENT FROM ITS NEIGHBOURS.** 1,088 covered cells on the first date and 1,657 on the last.
There is **no era hole** — unlike `institutional` (starts 2014), `S18`'s short interest (32 of 69
dates, every one late), `U2`'s options surface (29 dates empty, all early) or `S19`'s MD&A (41
dates, all late). **A full both-halves gate is available on basis six, not a covered-subsample
substitute.**

**After the template's complete-case rule:**

| basis | effective dates | effective rows | frac of raw | first effective date |
|---|---|---|---|---|
| six | **69** | 66,255 | 0.8416 | 2009-01-15 |
| seven | **49** | 49,575 | 0.6297 | 2014-01-17 |

**MB22 POWER, BOTH VOCABULARIES, PRINTED BEFORE ANY FLOOR IS READ** (`RUN_RULES` A-11), at
`crit = 2.71`, in units of the per-date IC's own standard deviation:

| basis | 50%-power (`crit x se`) | **80%-power (`(crit + 0.84) x se`)** |
|---|---|---|
| six (69 dates) | 0.3262 SD | **0.4274 SD** |
| seven (49 dates) | 0.3871 SD | **0.5071 SD** |

**These reproduce `MB18`'s and `E-3`'s published design class to four decimals**, which is the
check that the arithmetic is this record's own rather than a plausible re-derivation.

**THE SENTENCE THAT MUST TRAVEL WITH ANY NULL, AND IT IS NOT A HEDGE:** the strongest **RAW**
anchor ever measured on rows of this shape is `z_fcf_margin` at **0.4346 SD**. The 80%-power MDE
on basis six is **0.4274 SD**. **So a NULL here means "no incremental effect as large as the best
single thing this panel has ever carried" — never "no effect".** Any verdict quoted without its
MDE is a void condition (§7).

---

## 5. PRE-OUTCOME KILLS. All read BEFORE the arm, in their own pass (`O10`'s process defect)

**K1 — MOMENTUM COSTUME. Bar: mean per-date |Spearman| against ANY incumbent theme < 0.60.**
This is the record's standing bar, quoted in §0. **MEASURED, and reported here because §0 says it
was:**

| against | mean rho | mean abs rho | max abs rho |
|---|---|---|---|
| **momentum** | **+0.3652** | **0.3652** | 0.4730 |
| quality | +0.1851 | 0.1853 | 0.3461 |
| insider | −0.1605 | 0.1605 | 0.2973 |
| institutional | +0.1535 | 0.1535 | 0.2678 |
| value | −0.0719 | 0.0961 | 0.2316 |
| size | −0.0697 | 0.0747 | 0.1820 |
| capital_discipline | +0.0133 | 0.0481 | 0.2348 |

**K1 DOES NOT FIRE.** Momentum is unambiguously the nearest neighbour — as the mechanism predicts,
since prices move when analysts revise — and 0.3652 sits well inside the bar that **withdrew**
`E-1` at 0.6114 and that `MB18` survived at 0.3062. **The honest reading: this is not a momentum
costume, and it is more momentum-adjacent than any candidate this record has recently registered.
The gate residualises on momentum, so what is tested is the revision-specific remainder.**

**K2 — PEAD COSTUME. Bar: mean per-date |Spearman| against `z_pead_car` or `z_pead_drift` < 0.60.
Measured: 0.2997 and 0.2672. DOES NOT FIRE.**

**K3 — DEGENERACY, and it must be checked because `U2` found the shipped IC arithmetic returns a
*t* of ~1e16 on a constant series.** If `rev_ratio` is constant within any scored date, or if the
non-null share on effective rows falls below 30%, the arm is **VOID**, not scored.

**K4 — LOOK-AHEAD. Zero tolerance.** No estimate with `actdats > t` may enter the signal at `t`.
Pinned two ways: an AST test asserting the arm path never references `anndats`, `revdats`,
`actual`, `actdats_act` or `anndats_act`; and a synthetic fixture in which an estimate dated after
`t` must move nothing. **A single violation voids the register.**

---

## 6. CONTROLS (own pass, banked and read before the arm)

**C1 — FIDELITY.** The panel reproduces the published record before anything is joined:
`top_decile_alpha` 0.071741..., long-short naive *t* 2.8360..., HAC *t* 2.6199..., monotonicity
−0.8909. **The run ABORTS before any arm if it does not.** `MB8`'s C1 and `MA28`'s C1 both fired
in real life; this is not decorative.

**C2 — THE JOIN IS `W-3b`'s AND NOT A LOOKALIKE.** `MaskedCusip` is **imported**, never
re-implemented (`B7`). The three traps `W-3b` measured are inherited rather than re-discovered:
`oftic` is a lease (17.7% contamination), escaping reuse needs a **date** not a different column,
and IBES's `X` mask needs a **positional** wildcard (a 7-char prefix rule merges 328 distinct
cusips). A test asserts no prefix match and no `oftic` join anywhere in the arm path.

**C3 — COUNT-GATED, because `MB21`'s C1 scored a perfect 0.000e+00 on an empty frame by comparing
nothing.** Every reproduction control asserts the number of cells it compared.

**C4 — ORTHOGONALITY, DIAGNOSTIC ONLY, NO VERDICT.** Mean per-date R² of the candidate on the
incumbents, reported because four items before it reported one — and per §2c a low value is **not**
evidence for this register.

**C5 — SURVIVOR TILT PRINTED, NOT ASSUMED.** Median market cap of covered vs uncovered cells.
IBES follows larger names, so the covered set will tilt large and the size of that tilt must ship
with the verdict.

**C6 — THE CRSP CEILING IS REPORTED AS A LIMIT.** 260 of 2,531 panel names carry no CRSP interval
and are **unreachable by construction**; they are counted, listed and never read as zero coverage.

---

## 7. VOID CONDITIONS

1. Quoting any verdict **without its MDE** (§4).
2. Moving `fpi`, the 91-day window, the floor of 3, the `actdats` gate, the adjusted/unadjusted
   pair, or the declared POSITIVE sign after any outcome is seen.
3. Scoring **one** basis and reporting it as the result (§3).
4. Reading the arm before C1–C6 are banked and green.
5. Any look-ahead violation under K4.
6. Reporting a low R² as support (§2c).
7. Sweeping a variant — a second window, a second horizon, a magnitude-weighted version, or a
   consensus-change version — inside this register. Each is a **new hypothesis** with its own
   trial and its own blind register.
8. Adopting anything. This register measures.

---

## 8. THE HONEST PRIOR, AND EXPECTATIONS, WRITTEN BEFORE THE RUN

**PRIOR: ~20% CONFIRMED. Analyst estimate revisions are among the most widely traded effects in
existence, and post-publication decay is the base case.** McLean–Pontiff put the average
post-publication decay near 58%; this signal has been in every commercial quant stack for two
decades. **And this project has killed several published results on its own data** — Cremers–
Weinbaum's parity deviation (`MA31`), Xing–Zhang–Zhao's smirk (`U2`, sign not even reproduced),
Gao–Xing–Zhang's earnings straddle (`O7`, sign reversed on this universe). **A widely-traded
effect surviving an incremental gate on top of seven incumbents including momentum is the
exception, not the expectation.**

The prior is nonetheless the highest this lane has written for an equity candidate, for two
measured reasons rather than optimism: coverage is uniform across the whole window (§4), and the
signal is **not an input to any incumbent theme**, so its incremental IC is not structurally
suppressed the way `MB18`'s own power anchors were (they scored incremental *t* of +1.55 and
+0.26 precisely because they live inside `quality` and `momentum`).

**Expectations:**

1. The arm is **NULL on at least one basis** — **80/20**.
2. K1 does not fire — **UNSCORABLE**, already measured (§0).
3. Momentum is the largest incumbent correlate — **UNSCORABLE**, already measured (§0).
4. If any cell clears, it is **basis six** rather than seven (more dates, more power) — **70/30**.
5. Mean R² on the incumbents lands **below 0.25** — **75/25**. *Carries no evidential weight; see
   §2c.*
6. The covered set is **larger by median market cap** than the uncovered set — **85/15**.
7. At least one number here contradicts this list — **60/40**.

---

## 9. WHAT THIS REGISTER DOES NOT DO

It **adopts nothing**, touches no file under `valuation/screener`, `valuation/web` or
`valuation/engine`, changes no theme, and moves no published claim. It does **not** re-open `D7`
(WRDS is still not purchasable by an unaffiliated account — that verdict stands on its own
terms). It makes **no claim about the unadjusted pair**, no claim about any `fpi` other than 1, no
claim about quarterly horizons, no claim about revision **magnitude** as opposed to direction, and
no claim about the consensus-change construction that `statsum` would support. It licenses **no
product copy**: `V3` still forbids per-name precision language and `MB38`'s vocabulary governs any
public sentence. **A NULL here closes the construction registered above and nothing wider.**
