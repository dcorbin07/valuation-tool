# PREREG — E-1 / S-SEED-4: the graveyard votes

## EXECUTOR'S ACCEPTANCE — 2026-08-20

**ACCEPTED.** `PREREG_DRAFT_s4_graveyard_stouffer.md` (Frontier Scout lane, landed on `main`
inside a multi-file batch and therefore *not* a register) is adopted **verbatim** as this
register. **Everything from the horizontal rule below is the draft's text, byte-identical** — no
bar, rule, statistic, kill, void condition, prior or expectation has been altered, added or
removed. This block is **additive disclosure only**.

**COMMITTED ALONE, markdown only, zero `.py`, as a strict git ancestor of every measurement
commit.**

**COUNTERS RE-READ from `research_log.detail()` at acceptance, not quoted from the draft:**
equity **236**, options **305**, infra **19**. The draft's stated charge of "235 → 236" is
**stale** — `MB8` booked an equity trial while the draft sat. **This register charges equity
236 → 237**, and the Harvey-Liu-Zhu hurdle moves **3.3057016819506297 → 3.3069805385381787**.
Options and infra are untouched.

### 0.5 NON-BLINDNESS DISCLOSURE — K3's census was run BEFORE this register was committed

Declared here rather than discovered later, on `U3`'s §0.5 precedent. The draft delegates the
signal enumeration to the executor (*"the executor enumerates from `settings`/`NUMBER_THEME` at
run time and banks the list"*), and I ran that enumeration **before accepting**, to establish
whether the register is executable at all.

**It touches no outcome.** `fwd_ret` was never read; the census counts entries in a settings
dict and measures the presence and coverage of signal columns. No IC, no return, no verdict, and
nothing about the hypothesis was learned. **No bar, kill or rule has been changed after seeing
it** — in particular K3's floor of 25 stands exactly as drafted, and moving it now would be
`MA58`'s void condition 5.

What was seen, stated in full so the sequence is auditable: **29 non-incumbent registered
signals**, of which **26** carry any coverage on the panel and **25** exceed 5%. **K3 does not
fire** (29 ≥ 25). The margin is four signals, and on a coverage-filtered reading it is zero —
**this register is accepted knowing its kill passes narrowly**, which is disclosed because a
reader is entitled to know the census preceded the commitment.

### Three defects in the draft, declared BEFORE any outcome is read

Reported rather than repaired, on this project's own precedent: `MB1` ran a kill verbatim from
its audit and reported that the rule did not follow; `O17C4` ran three registered bars and
reported that two did not measure what they were written to measure; `MB23` ported a criterion's
correction and kept the committed version beside it. **Running a register as written is what
surfaces its defects.**

**D1 — §1's "expected ≈40+" is wrong; the graveyard holds 29.** The panel carries **53** `z_`
columns and `NUMBER_THEME` registers **exactly** those 53 — zero extra, zero missing, so the
registry and the panel are the same object and there is no wider set to appeal to. But the seven
weighted theme means use far fewer columns than `NUMBER_THEME` *assigns* to them: `institutional`
uses **2 of 9**, `quality` **10 of 13**, `momentum` **3 of 5**, `capital_discipline` **1 of 2**,
`value` 7 of 7, `size` 1 of 1, and `insider` is built from `insider_score` rather than from any
`z_` column at all. **Distinct inputs to the seven weighted themes: 24.** So the graveyard is
`53 − 24 = 29`, not "≈40+", and the draft's estimate is high by about 40%.

**The direction matters and is why this is declared rather than shrugged at:** the draft set
K3's floor at 25 while expecting 40+, i.e. expecting a comfortable margin. The true margin is
**four**. A register whose pre-outcome kill was calibrated against a signal count 40% too high is
a register whose kill is far closer to firing than its author believed.

**D2 — §1 requires a "published sign as recorded at its own registration", and NO SUCH REGISTRY
EXISTS for the equity panel.** `PUBLISHED_SIGNS` is options-lane machinery (`optxs_run.py`, the
options autopsy); nothing under `valuation/screener` or `valuation/edge` records a per-signal
published direction for these 53.

Read at its most literal, §1's next sentence — *"a signal with no recorded published sign is
EXCLUDED and counted"* — would exclude **all 29** and fire K3 at zero. **That reading is
rejected, and the reason is the clause's own stated purpose:** it exists because *"signing from
this panel's data would be in-sample orientation and voids the register."*

**THE ORIENTATION RECORD THIS PANEL ACTUALLY HAS IS THE COLUMN CONSTRUCTION, and it satisfies
that purpose exactly.** Every `z_` column is built oriented so that a higher value is the
direction predicted to outperform, with the flip carried in the name and applied at build time —
`neg_issuance`, `neg_vol`, `neg_beta`, `neg_max_ret`, `neg_ret_1m`, `neg_idio_vol`,
`neg_asset_growth`, `neg_days_to_cover`, `neg_short_interest_chg`, `neg_rating_disp`,
`neg_ev_sales`, `neg_ps`, `neg_leverage`, `neg_log_mktcap`. That orientation is in **tracked
source**, predates this register by months, and is **not derived from this panel's outcomes** —
which is the whole of what §1 is protecting against.

**DECLARED IN WRITING, BEFORE THE RUN: the sign record for this register is the shipped `z_`
construction convention, taken as-is.** No signal is re-oriented, no sign is inferred from data,
and the arm applies **no sign flips of its own** — the graveyard column is the flat mean of the
oriented `z_` columns exactly as they ship. A test pins that the arm path contains no negation of
any input.

**D3 — three of the 29 are structurally EMPTY and the set keeps them anyway.** `earn_rev`,
`rating_rev` and `neg_rating_disp` (all `sentiment`) carry **0.0000** coverage on the panel —
`CLAUDE.md` records the theme as empty and this confirms it at the column level.
`govt_award_momentum` sits at **0.0475**. Per §1 the set is **all 29**, banked before the arm;
the `B7` convention drops a NaN from the mean, so an empty column contributes nothing, and §1's
own eligibility rule (**≥ half the set computable**, i.e. ≥ 15 of 29) governs which rows score.
Keeping the empties in the denominator makes eligibility **stricter**, which is the conservative
direction. The full partition ships in the artifact.

### `RUN_RULES` PART A rule 11 — the power line, exact rather than approximate

From `power_gate` at the X7-calibrated `crit` 2.71, on the draft's own two bases:

| basis | dates | MDE at 80% power | MDE at 50% power |
|---|---|---|---|
| six-theme | 69 | **0.4274 SD** | 0.3262 SD |
| seven-theme | 49 | **0.5071 SD** | 0.3871 SD |

The draft's "≈0.43 / ≈0.51" and "≈0.30 / 0.36" reproduce; the 50%-power figures are 0.3262 and
0.3871 rather than 0.30 and 0.36. Realized-coverage figures are printed by the arm from
`power_gate.state()` **before the verdict is read**. The strongest raw anchor this panel has ever
carried is **0.4346 SD**, so §3's sentence binds and travels with any null.

### Run-as-written commitment

Every bar, kill, void condition and verdict rule below is executed **exactly as drafted**. The
three defects above are reported beside the result and repaired **nowhere in this register**.

---

# PREREG DRAFT — S-SEED-4: the graveyard votes
## One pre-committed combination of every signal the incumbents don't already use

**DRAFT, Frontier Scout lane, 2026-08-20.** Commit ALONE, markdown only, counters re-read
first. **Trials: 1, equity** (235 → 236 at this writing; hurdle 3.3044 → 3.3057).

## 0. The question and the wall it stands against

Most of the ~53 registered signals are individually null or rejected against per-signal bars.
The genomics analogue is exact: many true-but-subthreshold effects can aggregate into one
detectable statistic (the polygenic logic; Zaykin's optimally-weighted Z is the canonical
form). Finance has its own version — Stambaugh–Yuan's mispricing score averages 11 anomaly
ranks and works where singles are noisy. **The wall:** this record has now put FIVE bodies
under "orthogonal/more-inputs" motivations (`U2`, `MA31`/`MA32`, `MA58`, `MB18`), and the
combiner family is closed where fitting was involved (`MLCOMB` reversed out of sample; five
weight schemes rejected). This register survives the wall only because **nothing is fitted**:
signs are the *published* directions recorded at registration, weights are flat, and the
whole object is one pre-committed column. If it clears, it does NOT license asking *which*
signals carried it — that is a second register and this one says so.

## 1. The object, fixed exactly

* **Signal set:** every registered signal in the panel's registry that is **not an input to
  any of the seven weighted themes** (the executor enumerates from `settings`/`NUMBER_THEME`
  at run time and banks the list; expected ≈40+). Excluding incumbent inputs is structural
  costume-proofing: the graveyard composite may not contain the live composite's parts.
* **Orientation:** each signal enters at its **published sign as recorded at its own
  registration**. A signal with no recorded published sign is EXCLUDED and counted — signing
  from this panel's data would be in-sample orientation and voids the register.
* **The column:** flat equal-weight mean of the oriented z-columns, per name-date, missing
  themes handled exactly as the shipped composite handles them (`B7` convention), eligibility
  ≥ half the set computable (partition reported).

## 2. Statistic, bars, halves

Primary: **incremental IC** on the seven incumbents under `MB7`'s repaired gate — **both
bases co-primary** (`MB18`'s convention: six-theme basis, 69 effective dates; seven-theme,
49 dates from 2014-01-17), `split_used="effective"` declared, effective coverage printed
(RUN_RULES A-10). Sign: **two-sided** (the components' published signs orient the column;
the diffuse-aggregate hypothesis does not privilege a direction against incumbents).
Bar: the X7-calibrated incremental threshold (2.71 at current calibration; re-read at run).
Both halves must clear for CONFIRMED; ambiguous-against-bar is NULL (`RUN_RULES` A-6).
**Declared secondary, same trial:** the Stouffer form — per-date Z combining per-signal ICs
with flat weights and an input-correlation-matrix denominator (correlation of SIGNAL VALUES,
computed once, banked; inputs only, no outcomes) — reported beside the primary, no verdict of
its own (the `MA26-A` one-hypothesis-one-trial collapse).

## 3. Power (RUN_RULES A-11, both numbers)

Same design class as `MB18`, so the same detection scale governs: **≈0.43 SD (basis six) /
≈0.51 SD (basis seven) at 80% power; ≈0.30/0.36 at 50%** — against a panel whose strongest
raw anchor ever is 0.4346 SD. The executor prints exact figures from `power_gate.state()` on
realized coverage before the verdict is read. **A NULL here therefore means "no diffuse
aggregate at least as large as the best single signal the panel has carried" — the register
quotes that sentence with any null.**

## 4. Pre-outcome kills (separate pass, read before the arm)

* K1: |per-date mean Spearman| of the graveyard column vs the **shipped composite** > 0.60 →
  WITHDRAWN (it is the composite in costume despite the input exclusion — shared underlying
  accounting drivers can do this; `MB18`'s C2 convention and bar).
* K2: vs the **size** theme > 0.60 → WITHDRAWN (`R6`'s autopsy: the last "conviction"
  aggregate decomposed into a size sort).
* K3: signal-set census — if fewer than **25** signals survive the published-sign and
  non-incumbent rules, the "diffuse aggregate" premise is gone: WITHDRAWN, zero cost beyond
  the census.

## 5. Void conditions

1. Any weight other than flat; any sign not traceable to a registration-time record.
2. Any post-hoc subsetting of the signal list after K3's census is banked.
3. Reading the secondary as a verdict, or the arm licensing a which-signal follow-up without
   its own register.
4. Skipping the effective-date split or the A-11 line.

## 6. Prior and expectations

Prior: **~8%** CONFIRMED — the five-body wall points down; the no-fitting design and the
polygenic mechanism are what keep it off zero; it is the cheapest genuinely-new equity
question left (one derived column on an existing panel). Expectations: (1) K1 fires — 45/55
*against* (the exclusion should hold |rho| under 0.6, barely); (2) verdict NULL — 85/15;
(3) the Stouffer secondary agrees in sign with the primary — 70/30; (4) K3 census ≥ 25
signals — 80/20; (5) one number contradicts this list — 60/40.

## 7. What it does not do

No component-level claims, no weighting family re-entry, no theme-membership change, no
product copy. One column, one bar, one number, and the register closes whichever way it goes.
