# HANDOFF — `INSIDER-WIDE`: the one check-quadrant read — **the governing `$500M` cell CONFIRMS at +3.49pp gross / +2.91pp net, carried by ONE cap band and almost entirely by 2020-2022**

**Date:** 2026-10-13 · **Branch:** `worktree-r1-insider-wide` · **Lane:** r1
**Register:** `PREREG_insider_cluster_wide.md`, committed **ALONE at `1cc8b7e`** (markdown only,
zero `.py`, 270 lines, a strict git ancestor of every commit that computes a check-quadrant
outcome) · **Trials:** 3 equity, booked at **`dfbccc4`** (equity 303 → 306) **before any read
runner existed** · **Instrument:** `709290d`, also before the read
**Stage 1:** `PREREG_insider_cluster.md` `fd87870`, Amendment 1 `826d0b5`, arm `4db197a` —
**none edited, and its `cap ≥ $10B` `UNDERPOWERED-BY-CONSTRUCTION` label stands as written.**

**ADOPTS NOTHING.** No file under `valuation/` changed. **If it confirms, the next rung is a
forward paper book in SHARES, which is Don's decision and not this lane's.**

---

## 0. What this is

Don's ruling of 2026-10-13 (`DECISIONS.md`): clustered insider buying goes to a **wider-tier**
test, with a **new register** and **realistic size-tiered trading costs**, written **before** the
one check-quadrant read.

Stage 1 cleared every clause on the **full corrected universe** in the build quadrant at `h`=63
(**+2.0926pp** market-adjusted, **+1.8077pp** over its null mean, *t* 5.009 / 4.888 over 4,072
events) while its governing `cap ≥ $10B` tier was `UNDERPOWERED-BY-CONSTRUCTION` at 151 events —
so it **stopped** rather than advancing, and the check quadrant was left unspent.

**The charter rations the CELL, not the question.** One pass over 2020-2026 × ticker half 1 is one
read, and there is no second one, so every population, bar, horizon and cost was fixed in the
register first.

---

## 1. WHAT IS UNCHANGED FROM STAGE 1 — all of it

The cluster definition verbatim (`k` = 2 or more **distinct** `ownername` filing an
**opportunistic** open-market purchase, `transactioncode == "P"`, a missing code **counted and
skipped**, inside a 30-calendar-day window, dated at the **last** filing, one event per cluster
under a full-window cooldown, with the **strict** condition that the pair traded in each of the
two prior calendar years). The **market-adjusted leg only**. The within-date permutation null at
500 draws. Both halves, same sign, each against its own null. Both clusterings — event **date**
and **ticker** — required. Benjamini-Hochberg. Terminal-vs-censored per `E-5`.

**The own-normal leg stays out for a MEASURED reason, not a preference:** `ar_own = fwd − h × mu`
subtracts a trailing mean daily return, insiders buy **after declines**, so a negative trailing
drift is extrapolated forward for a quarter. It read **+11.46pp** at `h`=63 against the market
leg's +2.09pp, with its **own permutation null centred at +1.17pp rather than zero**. A leg whose
null is not centred on zero is a biased benchmark, measured.

**The only new things are the governing population, the cost treatment, and that this reads the
CHECK cell.**

---

## 2. THE TIER CHOICE, AND THE DISJOINT BANDS ARE THE FINDING

Chosen from the **build** quadrant, which is what the build cell is for, with the cells that argue
*against* the choice printed beside it.

| band (disjoint) | events | tickers | gross | *t* (date/ticker) | round-trip cost | **NET** |
|---|---|---|---|---|---|---|
| `$10B+` | 141 | 78 | +3.0138pp | 2.58 / 2.51 | 0.186pp | **+2.83pp** |
| `$2B–$10B` | 470 | 238 | **−0.6869pp** | −0.94 / −0.90 | 0.400pp | **−1.09pp** |
| `$500M–$2B` | 767 | 337 | +1.9004pp | 2.23 / 2.51 | 0.800pp | **+1.10pp** |
| `$100M–$500M` | 1,354 | 495 | +2.0188pp | 3.19 / 2.96 | 1.600pp | **+0.42pp** |
| `< $100M` | 845 | 316 | +1.8557pp | 1.68 / 1.59 | 3.000pp | **−1.14pp** |

**THE GROSS EFFECT IS ROUGHLY +1.9pp IN EVERY BAND EXCEPT TWO, and the exceptions are the
finding.** `$10B+` is **larger** (+3.01pp) and **`$2B–$10B` is NEGATIVE** (−0.69pp at *t* −0.94 —
noise-consistent, but certainly not +1.9pp). **The effect is NOT monotone in size and a successor
must not model it as such.** It is also why a cumulative-floor table is unreadable alone: a
`$500M` floor contains the dead `$2B–$10B` band, which drags its cumulative reading from the
band's +1.90pp down to +1.13pp.

**AND COST, NOT SIGNAL, DECIDES THE FLOOR: the round trip roughly DOUBLES at each rung down while
the gross effect stays flat.** Net of cost only `$10B+` and `$500M–$2B` are clearly positive;
`$100M–$500M` nets +0.42pp with cost at **79%** of gross; and `< $100M` is **negative** at
−1.14pp, because the model charges 150 bps one-way there.

**`cap ≥ $500M` governs** — 20× wider in cap than stage 1 and 1,120 check events against 151 —
because it is the lowest rung at which the round trip stays **below half** the gross band effect
(42%, against 79% and then over 100%), and the lowest that does not rest a *tradability* verdict
on the band the cost model's own comment disclaims as *"often untradeable in size at all"*.
**It was not chosen by maximising:** `$100M` and the full universe have **higher** gross effects
and far more check power, and `$10B+` has a higher net effect.

---

## 3. COSTS — size-tiered, per event, and stage 1's single floor is SUPERSEDED

Every event is charged `2 × one_way_cost_bps(its own point-in-time market cap) / 100`, from
**this project's own shipped model**, called and never re-implemented (`B7`), reproduced against
the shipped function at five band edges with **no bps value from the table retyped**.

**Stage 1's single 0.67pp floor is superseded, and the correction matters:** it is 2× `B11`'s
**realised BOOK-WEIGHTED** 33.4 bps on a megacap-tilted decile book — not a cost for the name in
front of you. It **understates a sub-$100M name by 4.5×** and **overstates a megacap by 8×**.

**A spread-only variant is deliberately NOT built**, even though Don's 2026-10-04 Roth ruling would
justify a smaller impact term, because this project owns no equity spread data and inventing a
cheaper cost model to help a result pass is the flattering direction. **The asymmetry is declared
instead: the charged cost is an UPPER BOUND at personal size**, so a net pass clears comfortably
and a net failure may still be tradeable.

---

## 4. POWER, STATED BEFORE THE READ — and one leg declared unanswerable

From the **build cell's own REALISED** cluster-robust `se` scaled by `sqrt(n_build / n_check)`
(`MB8`: this construction's own `se`, never borrowed), rather than the `sqrt(n/G)` worst-case
bound — `BETA-FORECAST` measured that bound landing about **6×** from reality.

| cell | check n | `se` | MDE80 | GROSS | **power GROSS** | NET | exp. *t* NET | **power NET** |
|---|---|---|---|---|---|---|---|---|
| **`$500M` (GOVERNS)** | 1,120 | 0.626pp | 1.778pp | +1.132pp | **42.4%** | +0.531pp | +0.85 | **12.7%** |
| FULL universe | 2,669 | 0.529pp | 1.503pp | +2.093pp | **97.5%** | +0.370pp | +0.70 | 10.0% |
| `$10B` | 151 | 1.159pp | 3.292pp | +3.014pp | 72.6% | +2.828pp | +2.44 | **67.0%** |
| `$2B` (no verdict) | 540 | 0.694pp | 1.972pp | +0.167pp | 5.2% | −0.183pp | −0.26 | 0% |
| `$100M` (no verdict) | 2,020 | 0.501pp | 1.424pp | +1.571pp | 87.2% | +0.476pp | +0.95 | 14.8% |

1. **The GOVERNING cell's gross leg is powered at 42.4% — below half**, so `cap ≥ $500M` is
   **pre-declared to return UNDERPOWERED on a null**, and only a positive result there is
   informative. A real limitation of a tier chosen on cost realism rather than on power.
2. **The NET-OF-COST question is UNANSWERABLE AT EVERY WIDE TIER** — 10% to 15% power, expected
   *t* 0.70 to 0.95. **A wide-tier net null is invisible rather than absent** and may not be read
   as evidence the strategy does not pay.
3. **Only two cells can resolve anything:** the **full universe** on the GROSS phenomenon (97.5%)
   and **`$10B+`** on the NET economics (67.0%). Those two are why the read is worth taking.

**AND A CORRECTION TO STAGE 1'S OWN FRAMING, made before the read.** Stage 1 declared the `$10B`
tier `UNDERPOWERED` at **7.4%**, computed against the *literature's* hypothesised 1.23pp. The
build quadrant then **measured +3.01pp** there, and against its own measured effect the check read
has **67.0%** net power. **Both are right and they are different statements:** a stage-1 screen
cannot power against an effect it has not yet measured without circularity, while a stage-2
confirmation's correct target *is* the measured build effect. **Stage 1's label stands as written,
and `$10B+` is nevertheless the best-powered economic cell here** — which is why it is read.

---

## 5. THE READ — **the governing cell CONFIRMS, and the two surprises are in opposite directions**

**ONE pass over 2020-2026 × ticker half 1. 2,669 events, 1,059 tickers, market built over 4,847
half-1 names and 1,697 sessions. `h`=63 governs; `h`=126 is reported only.**

| cell | n | gross | *t* date/ticker | own null p95 | cost | **NET** | BH *p* | **VERDICT** |
|---|---|---|---|---|---|---|---|---|
| **`$500M` (GOVERNS)** | 1,093 | **+3.4888pp** | **+3.601 / +4.036** | 0.6998 | 0.577 | **+2.9122pp** | 3.17e-04 ✓ | **CONFIRMED** |
| FULL universe | 2,511 | +2.2764pp | +3.043 / +3.156 | 1.5418 | 1.426 | +0.8506pp | 2.34e-03 ✓ | **NOT CONFIRMED** |
| `$10B` | 147 | +1.3574pp | +0.732 / +0.738 | 0.6588 | 0.181 | +1.1761pp | 0.464 ✗ | **NOT CONFIRMED** |
| `$2B` (no verdict) | 530 | +1.6880pp | +1.490 / +1.691 | 0.4597 | 0.339 | +1.3487pp | — | REPORTED, NO VERDICT |
| `$100M` (no verdict) | 1,966 | +2.9078pp | +3.660 / +3.948 | 0.8838 | 1.031 | +1.8767pp | — | REPORTED, NO VERDICT |

**THE GOVERNING CELL CLEARS ALL FOUR CLAUSES AND BH.** `cap ≥ $500M` at `h`=63: positive, above
its own within-date permutation p95 on the full sample **and in both halves with the same sign**,
cluster-robust *t* over 2.0 under **both** clusterings, and above its own event-weighted
size-tiered round-trip cost. Its excess over the null **mean** is **+4.1242pp** — larger than the
raw +3.49pp, because in 2020-2026 the *average* name **lagged** a cap-weighted market by 0.64pp,
so the null runs in the arm's favour here rather than against it (the mirror of stage 1, where it
ran the other way).

### 5a. THE CAVEAT THAT MATTERS MOST FOR A FORWARD BOOK: **the late half nets NEGATIVE in every cell**

| cell | early (2020-22) | late (2023-26) | cost | **late NET** |
|---|---|---|---|---|
| **`$500M` (GOVERNS)** | **+6.7352pp** | **+0.5319pp** | 0.577 | **−0.0447pp** |
| FULL universe | +4.9410pp | −0.4073pp | 1.426 | −1.8331pp |
| `$10B` | +4.8495pp | −1.4881pp | 0.181 | −1.6693pp |
| `$2B` | +4.1508pp | −0.6657pp | 0.339 | −1.0051pp |
| `$100M` | +5.1579pp | +0.5879pp | 1.031 | −0.4432pp |

**The confirmation is carried by 2020-2022.** The governing cell's late half is **+0.53pp gross
against a 0.577pp cost — essentially zero net**, and it satisfies the both-halves clause because
each half is scored against **its own** null and the late null's p95 is itself **negative**
(−0.2420). That is the rule as registered and it is honoured; it is also not the same thing as
"the late half pays". **A forward book trades the future, and the future looks like the late
half.** This is the single sentence Don should weigh against the headline.

### 5b. WHY THE BEST-POWERED CELL FAILED — a SIGN disagreement, not a weak effect

The FULL universe clears A1, A3 and A4 and **fails only `halves_same_sign`**: early **+4.9410pp**
(*t* 4.181), late **−0.4073pp**. Both halves clear their own nulls; the signs disagree. So the
cell declared able to resolve the gross phenomenon at 97.5% power returned **NOT CONFIRMED on a
stability clause rather than on strength** — its full-sample *t* is +3.04 and it survives BH.

**`$10B` NOT CONFIRMED fails A3 outright** (*t* 0.73) and its halves disagree too. **The tier the
Index actually trades still cannot show this effect, now on a second independent cell** — stage 1
could not tell at 151 events, and the check cell says *not confirmed* at 147.

### 5c. THE BAND DECOMPOSITION — **ONE band carries it, and it is the only band significant in BOTH quadrants**

`scripts/insider_wide_bands.py`, `INSIDER_WIDE_BANDS.json`. **DIAGNOSTIC, NO VERDICT** — no band
was declared, so none may be promoted (§2c's rule applied to myself).

| band | n | gross | *t* date/ticker | cost | NET | late half |
|---|---|---|---|---|---|---|
| `$10B+` | 147 | +1.3574pp | +0.73 / +0.74 | 0.181 | +1.18pp | −1.49pp |
| `$2B–$10B` | 383 | +1.8149pp | +1.35 / +1.57 | 0.400 | +1.41pp | −0.32pp |
| **`$500M–$2B`** | 563 | **+5.1841pp** | **+3.90 / +3.62** | 0.800 | **+4.38pp** | **+1.61pp** |
| `$100M–$500M` | 873 | +2.1802pp | +1.74 / +1.68 | 1.600 | +0.58pp | +0.67pp |
| `< $100M` | 493 | +1.6568pp | +0.84 / +0.80 | 3.000 | **−1.34pp** | −1.92pp |

1. **The effect is concentrated in `$500M–$2B`.** Every other band reads +1.4 to +2.2pp and none
   is significant under either clustering.
2. **`$500M–$2B` is the ONLY band significant in BOTH quadrants** (build +1.9004pp at *t*
   2.23/2.51; check +5.1841pp at 3.90/3.62). `$10B+` and `$100M–$500M` were significant in the
   build cell and are not here. **For a forward book that is the most useful line in this
   document.**
3. **AND THE LATE-HALF DECAY IS A LARGE-CAP PHENOMENON, which is the opposite of the natural
   story.** Inside the governing cell the late half is `$500M–$2B` **+1.61pp**, `$2B–$10B`
   −0.32pp, `$10B+` **−1.49pp**. The small-mid band holds up in 2023-2026; it is the large caps
   that are dead. So "a small-cap anomaly decaying as it gets crowded" is **not** what this shows.
4. **The build quadrant's negative `$2B–$10B` band was NOISE.** It read −0.6869pp there and
   **+1.8149pp** here, so the register's own warning not to model the effect as monotone in size
   stands, and the specific dead band does not replicate. Expectation 6, right.
5. **`< $100M` is negative net of cost (−1.34pp) in the check cell too**, which is the second
   independent reason §2's floor did not rest on that rung.

### 5d. THE REALISED `se` IS 1.4× TO 1.6× THE PREDICTED ONE IN EVERY CELL — so §5's power table was optimistic

| cell | predicted `se` | realised `se` | ratio | declared power | **realised power** |
|---|---|---|---|---|---|
| FULL universe | 0.529pp | 0.748pp | 1.41× | 97.5% | 85.1% |
| `$10B` | 1.159pp | 1.855pp | 1.60× | 72.6% | **10.5%** |
| `$2B` | 0.694pp | 1.133pp | 1.63× | — | 30.5% |
| **`$500M`** | 0.626pp | 0.969pp | 1.55× | **42.4%** | **94.5%** |
| `$100M` | 0.501pp | 0.795pp | 1.59× | — | 95.1% |

**Scaling a build `se` by `sqrt(n_build / n_check)` assumes the same within-cluster correlation
structure, and 2020-2026 is more dispersed than 2009-2019** — COVID and the 2022 drawdown. The
error is systematic, in one direction, in all five cells. **Any successor scaling an `se` across
eras should expect ~1.5× and say so in advance.**

**TWO CONSEQUENCES, and the second is the one to be careful about.**

* **The governing cell's realised power is 94.5%, not the declared 42.4%** — because its realised
  *effect* (+3.49pp) is three times the build figure the power was computed against. The two
  errors ran in opposite directions and the cell is far better resolved than declared.
* **`$10B`'s realised power is 10.5%, not the declared 72.6%** — its effect collapsed *and* its
  `se` widened. **The verdict label stays `NOT CONFIRMED`, because the register pins the label to
  the DECLARED power and a test enforces that** — otherwise the label would be chosen on the
  outcome it is meant to qualify. **But it must be READ with 10.5% beside it: on realised power
  that cell is far closer to "could not tell" than to "it is not there."** Stage 1 said the same
  thing about the same tier, and this is the second cell to say it.

### 5e. `h`=126 — REPORTED ONLY, no verdict, and it agrees with stage 1

FULL +1.2947pp (*t* 0.98), `$500M` +0.6714pp (*t* 0.51), `$100M` +1.9914pp (*t* 1.42), `$10B`
**−1.9820pp**, `$2B` **−3.0529pp** (*t* −2.19/−2.44). **Nothing survives to two quarters**, which
corroborates stage 1's `h`=126 NULL on an independent cell. Carries no verdict by §2b, and
promoting the `$2B` negative would be exactly the horizon-shopping §2b forbids.

### 5f. `$100M` WOULD HAVE CONFIRMED, AND IT CARRIES NO VERDICT — reported because a reader would otherwise find it

`cap ≥ $100M` clears **all four clauses** (+2.9078pp, *t* 3.660/3.948, both halves same sign, net
+1.8767pp) at *p* 2.53e-04. §2c declared it **no-verdict before the read**, so it stays one — the
register working rather than a result withheld. **The useful part is the direction: the
confirmation is not knife-edge at `$500M`.** Two adjacent populations pass every clause and the
declared one is not the only one that would have.

### 5g. Expectations — **2 right, 4 wrong**, and the misses share one cause

| # | expectation | prior | outcome |
|---|---|---|---|
| 1 | the FULL universe's gross leg CONFIRMS | 65/35 | **WRONG** — NOT CONFIRMED, on a sign disagreement |
| 2 | the GOVERNING cell returns UNDERPOWERED | 55/45 | **WRONG** — it CONFIRMED |
| 3 | no cell clears A4 except `$10B+` | 70/30 | **WRONG** — all five `h`=63 cells clear A4 |
| 4 | `$10B+` confirms net of cost | 50/50 | **WRONG** — *t* 0.73 |
| 5 | at least one cell's halves disagree in sign | 60/40 | **RIGHT** — three do |
| 6 | the `$2B–$10B` dead band reappears | 40/60 | **RIGHT** — it does not; it was noise |

**FOUR WRONG OF SIX, AND THREE OF THE FOUR HAVE ONE CAUSE: I TRUSTED MY OWN POWER TABLE.** 1, 2
and 4 all follow from expecting the realised figures to track §5's predicted `se`, and the `se`
moved by ~1.5× in every cell while the effects moved too. **Expectation 3 is a different and
cheaper error — I read the build cell's cumulative-floor costs rather than noticing that four of
five cells sit at caps where the cost is well under a 2-3pp gross effect.**

---

## 6. DEFECTS IN MY OWN WORK — four, three caught by gates written to catch them

**(a) `C1` FIRED AGAINST MY OWN INSTRUMENT, BEFORE THE READ, AND THE LESSON IS PORTABLE.** The
first cut of `score` kept a row on `isfinite(ar_mkt)` alone — because §1 drops the own-normal leg
from the **statistic**, and I dropped it from the **population filter** as well. Stage 1 keeps a
row only where **both** legs are finite, so the two instruments disagreed by **2 events, 4,074
against 4,072**, and the build mean by **+0.0008pp**. **In a two-leg construction the discarded
leg is also a FILTER, so scoring one leg silently WIDENS the population.** The drift ran in the
arm's favour, which is the direction a gate exists for; at the one unrepeatable look a 2-row
population change is still a construction change. Restored, and pinned by a test asserting
`ar_own` appears **exactly twice** in `score` — the unpack and the filter.

**(b) THE SUBSTRING-BAN FAMILY, TWICE IN ONE TEST, IN THE SUITE THAT BANS IT.** The cost-floor
test first banned the **substring** `0.67` and failed against the **correct** tree, because the
arm's own docstring says stage 1's 0.67pp floor is SUPERSEDED — prose documenting a rule quotes
what the rule forbids, the **tenth** instance in this record. Its AST replacement then banned the
**value** `0.67` anywhere in the tree and **also failed**, because §5's declared power for the
`$10B` cell is **0.670** — a probability nested in a declaration table, with nothing to do with a
cost bar. **BAN THE ROLE, NOT THE NUMBER.** It now checks module-level assignment **shape**, with
a positive control that still bites on `COST_FLOOR_PP = 0.67` and two negative controls pinning
the exact prose and the exact power figure that broke the first two forms.

**(c) `POWER_DECLARED` WAS HAND-TYPED AND FOUR OF TEN FIGURES WERE WRONG.** `$2B` gross read 0.337
against a banked **0.0518**, and `$500M`/`$100M` had their NET figures swapped. These numbers
decide whether a null reads **UNDERPOWERED** or **NOT CONFIRMED**, i.e. a label, so they are now
**derived** from the banked tier-choice artifact with the register's published table as a
committed-literal cross-check — and the derivation **refuses** rather than relabelling if the two
ever disagree. `BETA-FORECAST` shipped a hand-typed `HLZ` hurdle wrong in its fourth decimal three
items ago. **No verdict moved** — every cell sits the same side of 0.50 under both — **which is
luck rather than design**, and is exactly what `X7RECON` says not to lean on.

**(d) A test asserted the register CITES `W-28`.** It does not and does not need to: §8.4 voids
the item if stage 1's floor is substituted or a cheaper cost model invented. **Asking for a
citation asks about provenance; the property is what binds.**

---

## 7. NOT DONE, named so it is not mistaken for done

* **Nothing is adopted.** No file under `valuation/` changed; no book is declared; no trade is
  licensed. **If it confirms, the next rung is a forward paper book in SHARES — Don's decision.**
* **The pre-2009 era is NOT read.** It is the charter's third and final look and needs its own
  register.
* **`h` = 126 carries NO verdict**, and neither do `cap ≥ $2B` and `cap ≥ $100M` (§2c, declared
  before the read).
* **The own-normal leg is quoted nowhere as a result** (§8.5).
* **`k` = 3 is not re-run**, no second window, no alternative cluster size, no sell-side arm.
* **The `$2B–$10B` dead band is UNEXPLAINED.** That it is negative is measured; why is not, and
  would need its own register.
* **Nothing here is evidence the strategy does not pay at a wide tier** — §5 declared that
  question unanswerable at 10–15% power before the read, and the governing cell's realised power
  turned out to be 94.5% rather than 42.4%, so on *that* cell the net question **was** answerable
  and is answered positively. The declaration still binds `$2B` and `$100M`.
* **THE LATE HALF IS NOT A VERDICT AND IS NOT DISMISSED EITHER.** §5a is a split of a cell the
  register scored whole; no half carries its own verdict, and the registered A2 clause — each half
  against its own null, same sign — is satisfied. **What it is: a reason to read the headline with
  the 2023-2026 figure beside it, because a forward book trades the late half.**
* **The `$500M–$2B` concentration is DIAGNOSTIC and may not be traded as a narrower rule.** It is
  the honest answer to *where does this come from*, and a register that governs on that band needs
  its own blind pre-registration and its own trials — and would have no unspent cell of this
  construction to confirm in.
