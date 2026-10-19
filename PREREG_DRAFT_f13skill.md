# PREREG_DRAFT_f13skill.md — *which* managers are buying, not how many — 2026-10-18

**A DRAFT, NOT A REGISTER. ZERO TRIALS.** No arm has run and no coverage census exists — **the
census that should have opened this item FAILED, and that is my own defect, recorded in §3.** A
register exists only once this file is committed **ALONE**, markdown only, zero `.py`, as a strict
ancestor of every measurement commit.

**Ranked #2 in `EDGE_DATA_MAP.md`.** Free live source (SEC EDGAR), genuinely new object — and the
hardest costume problem on the board.

---

## 1. THE HYPOTHESIS

The shipped `institutional` theme counts **how many** 13F managers hold a name (`inst_breadth`,
`sm_breadth`, `sm_holders`). **It does not know which ones.** A dollar from a manager whose past
positions outperformed is different information from a dollar from an index fund, and the project
has never separated them.

**Two candidate constructions, and the register must declare ONE:**

- **`skill_weight`** — each manager's weight is their own **past** out-of-sample performance on
  their **prior** disclosed holdings, computed strictly backward-looking; the signal is the
  skill-weighted change in a name's institutional ownership.
- **`crowding`** — the Herfindahl concentration of a name's institutional ownership, declared sign
  **NEGATIVE** (a crowded name unwinds badly).

**`skill_weight` IS THE DECLARED PRIMARY and `crowding` is NOT RUN in this register.** Running both
is a two-arm search; and `crowding` is the weaker of the two against `R6`, because a concentration
measure of ownership is nearer still to a size sort.

---

## 2. THE FAMILY IS RECORDED CLOSED, AND THAT IS THE ARGUMENT THIS DRAFT MUST ANSWER FIRST

**Five members have been measured and the record closes the family:**

| id | what it tested | verdict |
|---|---|---|
| `P3` | SF3 per-manager conviction (`sm_conviction`/`holders`/`breadth`) | **REJECTED** — on the alphabetical slice |
| **`R6`** | the same three on the corrected panel | **ALL NULL, and the mechanism measured: a market-cap sort, −0.815 to −0.854 against `size`** |
| `13F-LAG` | is the 13F edge a look-ahead artefact? | **REJECTED** — it is **not**; fresher data makes it *weaker* |
| `13F-DEP` | is the institutional theme the whole edge? | **REJECTED** |
| **`S8`** | decaying 13F by staleness | **REJECTED, and it cannot work by construction** — `days_since_13f` takes a mean of **1.25 distinct values per date**, because 13F quarter-ends are common calendar dates, so staleness is **common across names** and cannot re-rank anything |

> **SO `R6` IS THE OBSTACLE, AND A SKILL WEIGHTING IS EXACTLY THE KIND OF THING THAT WOULD FAIL IT
> AGAIN.** A manager-skill weighting is a **different weighting of the same holdings**, and `R6`
> measured that aggregates of those holdings are a size sort. `E-1` died the same death: a flat
> aggregate of 29 non-incumbent signals, **withdrawn at 0.6114 against `size`**, with 13 of its 29
> coming from two families already measured to be size proxies — **six of them institutional
> conviction signals at −0.815 to −0.854.**

**THEREFORE THE `size` CORRELATION IS A PRE-OUTCOME KILL IN THIS REGISTER, NOT A DIAGNOSTIC.** `R6`
measured its size correlation **after** scoring; `E-1` made it a kill and was withdrawn before
spending its arm. **This register follows `E-1`.**

---

## 3. THE CENSUS THAT MUST RUN FIRST — AND IT FAILED THIS SESSION, ON MY OWN ERROR

**`wrdssec_all.wrds_13f_holdings` is ENTITLED** (round-2 census). The query I ran on 2026-10-18 was:

> `select rdate, count(distinct mgrno) ... from wrdssec_all.wrds_13f_holdings`

and it returned **`column "mgrno" does not exist`**. **The one WRDS connection permitted per session
was spent, so this item's coverage census is UNMEASURED.**

**THE CAUSE IS A FAMILY THIS RECORD ALREADY NAMES.** `mgrno` is **Thomson's** `s34` column —
`WRDS_UNLOCK_MAP.md:125` uses it in exactly that context — and I applied it to **WRDS's own** 13F
product. **The wrong-object family.** Round 2 had recorded this table's **row count and span** and
never its **COLUMNS**, and I skipped the column probe *because entitlement was already known*.

> **THE PORTABLE RULE, AND IT COSTS ONE QUERY: ENTITLEMENT IS NOT SCHEMA.** Run
> `select * from <table> limit 1` and read the column list **before** aggregating. This is now in
> `WRDS_CENSUS.md` round 3 and in the project's memory.

**THE REGISTER'S FIRST ACT, in this order:**

1. `select * … limit 1` — read the real column names.
2. **`K0` MANAGER COUNT BY QUARTER.** The census records the table stepping from **71 filing
   managers in 2012 to 3,457 in 2013**, so **only 2013 onward is usable** — about **52 of 69 panel
   dates**, and **the pre-2013 half is unavailable entirely.**
3. **`K1` TIER COVERAGE per date**, on the arm's own population — never inherited (`O-1` applied an
   alert-book coverage figure to the panel and was ~17× wrong).

---

## 4. THE KILLS — all free, all read before any arm, in their own pass

| kill | measures | bar | source of the bar |
|---|---|---|---|
| **`K0`** | distinct filing managers per quarter | **≥ 1,000 from the first scored date** | the census's own 71 → 3,457 step; a "per-manager" signal on 71 managers is not the hypothesis |
| **`K1`** | tier cells with ≥ 20 identified managers, per date | **≥ 0.70 of cells, no date below 0.50** | the arm needs a cross-section of managers per name, not merely a holder count |
| **`K2`** | mean per-date \|Spearman\| of the signal against **`size`** | **< 0.60 or WITHDRAWN** | **`E-1`'s own bar, reused verbatim** so it cannot be chosen after seeing the number |
| **`K3`** | the same against the shipped **`institutional`** theme | **< 0.60 or WITHDRAWN** | if it correlates with the holder *count* above 0.60 it is `R6` renamed |
| **`K4`** | **look-ahead**: every manager's skill weight uses only filings dated **strictly before** *t* | **ZERO violations, with a positive control** | `E-6`/`S25`'s rule — a guard that passes by refusing everything is not a guard |
| **`K5`** | composite reproduction, gated on a non-zero cell count | **max \|Δ\| 0.000e+00** | `MB21`'s `C1` |

**`K4` IS THE ONE THAT MOST EASILY GOES WRONG AND IT IS WHY THE SKILL WEIGHT IS DEFINED BACKWARD.**
A manager's "skill" estimated on the full sample and then applied at every date is **look-ahead
wearing a weighting's clothes** — and it would produce a clean, large, plausible number. The weight
at date *t* may read only filings **and realised returns** strictly before *t*, so early dates carry
a short skill history and that is a cost rather than a bug.

---

## 5. THE ARM, AND THE CONSTRAINT THAT MAKES IT UNUSUAL

One arm, charter §1a — incremental against **the deployed composite as a single control** — build
quadrant, both halves agreeing in sign, scored on both populations with the **$10B tier governing**.

> **BUT THE BOTH-HALVES RULE HAS TO BE SATISFIED INSIDE 2013-2026, AND THAT IS DECLARED NOW RATHER
> THAN DISCOVERED.** The data begins in 2013; the build quadrant is 2009-2019. **So roughly 2013-2019
> is the build window and its two halves are each about three years.** A register must either accept
> halves that thin — and say so, with the MDE — or declare the item **NOT ASSESSABLE on the charter's
> own split** and stop. **The draft's recommendation is to measure `K1` first and decide the split in
> the register, before any outcome**, because choosing a split after seeing a result is `MA58`'s void
> condition 5.

**MDE, derived and not borrowed (`MB8`):** on ~14 build-quadrant dates in the 2013-2019 window the
80%-power MDE is far worse than the ~0.637 SD the full 44 dates give — **roughly 1.1 SD**, against
a best-ever raw anchor of **0.4346 SD**. **So on the charter's split this arm is underpowered by
construction, and the register must say which of the two honest responses it is taking:** report
`UNDERPOWERED` in advance (the `E-4` precedent, declined by name) or widen the window and lose the
charter's protection. **It may not quietly do the second.**

---

## 6. TRIALS

**1 equity trial**, booked before any runner exists. All six kills charge **zero** under `MB1-SEL`.
**Equity `N` 307 → 308**, hurdle **derived** at booking.

---

## 7. VOID CONDITIONS

1. **Running `crowding` as well as `skill_weight`.** Two arms, two trials, two registers.
2. **Estimating manager skill on any data at or after the scoring date.** `K4`.
3. **Widening the window past the charter's build quadrant without declaring it first.**
4. **Quoting the WRDS 13F file as the live source.** The live source is **SEC EDGAR**; the WRDS copy
   is academic-only and may never feed the score.
5. **Relaxing `K0`, `K1`, `K2` or `K3` after reading them.**
6. **Reading the check quadrant.**

---

## 8. THE LIVE ROUTE

**SEC EDGAR, free.** 13F-HR filings are public, and `sec_ticker_join.repair` already exists in this
project for the Form 4 lineage (cap resolution 48.09% → 54.85%), so **the identifier-join machinery
is partly built.** The 13F join is `cusip → ticker`, which is a different join from Form 4's, and
**the register must not assume the existing repair transfers.**

**Running cost: free in data.** It changes the score, not the turnover.

---

## 9. EXPECTATIONS

| # | expectation | odds |
|---|---|---|
| 1 | `K0` passes (≥ 1,000 managers from the first scored date) | 90/10 |
| 2 | **`K2` FIRES — the signal correlates with `size` above 0.60 and the arm is WITHDRAWN** | **50/50** |
| 3 | `K3` passes (it is not the holder count renamed) | 60/40 |
| 4 | the arm, if it runs, is **NULL or UNDERPOWERED** | **80/20** |
| 5 | **the register reports NOT ASSESSABLE on the charter's split** before scoring anything | **45/55** |

**EXPECTATION 2 AT A COIN FLIP IS THE REASON THIS IS RANKED SECOND AND NOT FIRST**, and it is the
cheapest thing on the board: **a withdrawal at `K2` costs zero trials and closes the
per-manager question with a measured reason**, which is what `E-1` bought for the graveyard
aggregate. **The modal good outcome here is a free kill, not a discovery.**

---

## 10. WHAT THIS DRAFT DOES NOT CLAIM

It does **not** claim manager identity predicts returns — no arm has run and **no coverage census
exists.** It does **not** reopen `R6`, `P3`, `S8`, `13F-LAG` or `13F-DEP`; it proposes a different
object and accepts `R6`'s bar as a kill. It does **not** claim the 13F coverage census will pass —
**it is unmeasured because of my own column-name error**, stated in §3 rather than worked around. And
**its literature leg is INCOMPLETE**: Gompers & Metrick (QJE 2001), the explicitly large-cap paper on
institutional holdings, was **identified by name and not read**, because the surveying agent died on
a session limit. **The register's first non-data act is to read it.**
