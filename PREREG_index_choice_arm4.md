# PRE-REGISTRATION — `INDEX-CHOICE-ARM4`: the ceiling arm's own robustness checks

**Committed ALONE, markdown only, zero `.py`, before any arm-4 runner exists. A strict git
ancestor of every commit that computes a figure this register declares.**

Don asked for *"arm 4's checks on 2009-2026 — the same 200 name-splits, halves, factors and
buildability that `INDEX-CHOICE` gave arms 2 and 3."* That is an instruction to run an **existing
registered method on one more object**, and this register exists to fix two things before any
number is read: **what is charged**, and **what the result may and may not be used for**.

---

## 0. Counter and the trial charge, argued from this project's own precedent

`by_domain` at writing: **equity 258, options 310, unified 0, infra 20**;
`rows_fixed_not_counted` 92, `rows_malformed` empty.

**ONE EQUITY TRIAL, and the honest position is that a serious case exists for ZERO. Both are
stated, because the one I am not taking is the one a later reader may prefer.**

**THE CASE FOR ZERO, which is not frivolous:**

* **`INDEX-CHOICE` charged PER STATISTIC, NOT PER ARM, and said so in writing.** Its §0 reads
  *"Two statistics, two trials, **across all three arms**"* for the name split, and *"One
  hypothesis, one trial, **across both arms**"* for the factor decomposition. On its own wording
  a fourth arm consumes no further statistic.
* **`R1` charged exactly 1 for a decomposition spanning the long-only book, the long-short
  series and several subperiods** — adding an object to an already-booked decomposition is what
  that precedent describes.
* **Arm 4's own trial is ALREADY PAID.** `INDEX-BEST` booked one equity trial per challenger
  before its runner existed, and `4_all_cap_ceiling` was one of those challengers; its
  `roth_net_ann` of **0.24950546311372124** is banked in `INDEX_BEST.json`. This register scores
  no new arm.
* **Buildability is a CONTROL under `MB1-SEL`** — it can only ever BLOCK arm 4 from being
  servable, never produce a finding — and `INDEX-CHOICE` charged it 0 for exactly that reason.

**WHY I AM CHARGING 1 ANYWAY.** The four points above are about *degrees of freedom in the
statistic*. The thing they do not cover is that running these checks on a fourth arm **widens the
set of constructions Don could end up choosing from by one**, and a favourable result would
license a sentence nobody has paid for (*"all four beat the incumbent on every half-book"*).
**`MA6`'s rule is that overstating `N` is the safe direction**, and `E-1`'s is that un-booking
after seeing how a result landed is the shape this record warns against hardest. One trial is the
smallest honest non-zero charge. **If a later reader prefers zero, the row is there to amend, and
the error runs the safe way.**

Equity **258 → 259**. `MB31`: the next adopt-set flip is seed **1017 at equity `N` = 688**, so
**no permutation floor can move**, and this register reads none of them in any case.

---

## 1. WHAT ARM 4 IS, AND THE ONE PRE-COMMITMENT THAT MATTERS MOST

Arm 4 is `INDEX-BEST`'s **`4_all_cap_ceiling`** — the top decile of the *whole* research panel,
score-weighted, 8% cap, quarterly, 30% band, flat 1/7, net of the same size-aware measured cost
model as the other three. `INDEX-BEST` ran it **as a labelled CEILING**: a measurement of how
much return sits in the panel at the widest possible pool, *not* an investable candidate.

**PRE-COMMITTED, BEFORE ANY ARM-4 FIGURE IS READ: ARM 4 REMAINS A CEILING AND IS NOT A FOURTH
OPTION FOR 2026-10-22, WHATEVER THESE CHECKS RETURN.** A good name split does not promote it; a
bad one does not demote it below the label it already has. **Re-labelling a ceiling as a candidate
after watching it do well is choosing the design on the outcome**, which is the single thing this
register exists to forbid. Its reasons for not being servable are structural and were known
before: it has no liquidity screen at all, so it holds names no account can transact, and
`INDEX-BEST` reported its capacity on that basis.

**VOID CONDITIONS.** The item is void if any of these happens: a figure from it is quoted as
making arm 4 servable; the method is changed from `INDEX-CHOICE`'s (see §2); a fifth arm is
added; or `DECISION_index_choice.md`'s three-option table is rewritten to four options.

---

## 2. METHOD — INHERITED VERBATIM, NOT CHOSEN

**Every key, seed and count is IMPORTED from the scripts `INDEX-CHOICE` already landed, never
retyped** (`B7`, `MA5`). Nothing here is a new design decision:

| check | source of the method | what changes |
|---|---|---|
| name split | `scripts/index_choice_split.py` — `stable_key_half`, `SEED = 20260813`, `K_SPLITS = 100`, `_assert_split`, `MIN_NAMES_PER_HALF = 400` | arm 4 added to `CHOICE` |
| halves | `scripts/index_best.py`'s own boundary, embargoed as there | nothing |
| factors | `scripts/index_choice_factors.py` — `factor_alpha`'s `ols_nw`, `regress`, `factor_windows`, `FF_MODEL`, `LAG = 1` | arm 4 added |
| buildability | `scripts/index_choice_buildable.py` — `D9_BAR = 0.60`, `D9_PUBLISHED_DECILE_OVERLAP` | arm 4's book size |

**A CONTROL THAT GATES EVERYTHING ELSE (`C1`).** Before any arm-4 statistic is read, the runner
must reproduce `INDEX_BEST.json`'s banked `4_all_cap_ceiling` figures — `roth_net_ann`,
`annual_turnover`, `realised_one_way_bps` — at **max |delta| 0.000e+00**. **The count of compared
leaves is GATED and must be non-zero**, because `MB21`'s `C1` once scored a perfect zero on an
empty frame by comparing nothing. If `C1` fails, nothing is scored and the failure is the report.

**THE MDE IS STATED BEFORE THE MARGIN (`MB22`, `RUN_RULES` A11).** Every paired comparison ships
its own measured paired HAC se and both `MDE_50% = crit × se` and `MDE_80% = (crit + 0.84) × se`.
**Every critical value is LABELLED UNCALIBRATED**: `V2G` established and `R1-VAR` re-confirmed
that **no calibrated floor exists for a paired within-panel difference**, and X7 calibrates
LEVELS. No figure here is compared to 2.2837, 2.0540, 2.7072 or any other X7 floor.

---

## 3. WHAT WOULD BE A FINDING, AND WHAT WOULD NOT

* **A name split that holds** is a statement that the ceiling is not an artefact of *which names*
  are in the panel. It is **not** a statement about *which period* — all 200 half-books use the
  same 69 dates, and `INDEX-BEST` found every arm's advantage concentrated in the late half. That
  limitation is `INDEX-CHOICE`'s and is inherited verbatim.
* **A name split that fails** would be the more interesting outcome, because it would mean the
  widest pool's extra return rests on particular names — which is the thing a ceiling is supposed
  to bound from above.
* **A factor decomposition is a DECOMPOSITION, NOT AN ALPHA CLAIM.** `INDEX-CHOICE` forbade an
  alpha claim in advance because the arms are not separable from each other and the whole effect
  is late-half. **That prohibition is inherited and is not re-argued here.**
* **Buildability can only BLOCK.** Arm 4 has no liquidity screen, so a poor overlap is expected
  and is not news; a good overlap would **not** make it servable (§1).

---

## 4. EXPECTATIONS, recorded so they can be scored against

1. **`C1` reproduces at 0.000e+00** — 90/10. The driver is the one `INDEX-BEST` already ran.
2. **Arm 4 beats the incumbent on 200 of 200 half-books** — 75/25. Arms 2 and 3 both did, and
   arm 4's full-sample net return (+24.95%) sits between them.
3. **Arm 4's half-book spread is WIDER than arm 2's and NARROWER than arm 3's** — 60/40. Its book
   is larger than arm 3's 25 names, so it should be less mechanically noisy, but its universe is
   the widest.
4. **Arm 4 carries the largest SMB loading of the four** — 65/35. It is the only arm with no size
   floor of any kind, and `N1`'s band book already read SMB **+1.13** on a narrower small-cap cut.
5. **Buildability fails its 0.60 bar** — 85/15. `D9` measured 0.2326 at a decile on a far more
   favourable universe.

---

## 5. WHAT THIS REGISTER DOES NOT DO

* **It adopts nothing**, changes no default, and writes nothing to the bound record.
* **It does not re-open `INDEX-BEST`'s pick**, which stands on its own registered rule.
* **It does not add an option to `DECISION_index_choice.md`'s table** (§1 void condition).
* **It spends no holdout.** Everything here is on 2009-2026, the panel these arms were built on.
  The pre-2009 eras stay blind, and `PANEL-EXT-RECHECK` has already recorded that the Sharadar
  route to them is closed.
