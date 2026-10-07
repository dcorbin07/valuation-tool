# PREREG — STAGE-1 BATCH 1 — the scout's twelve arms, on the build quadrant only

**Committed ALONE, markdown only, zero `.py`, BEFORE any runner for any arm exists.** Executor
pass on `PREREG_DRAFT_stage1_batch1.md` under `RESEARCH_CHARTER.md` §5's three-stage protocol, as
amended by Don's ruling of **2026-10-06** (`DECISIONS.md`: **no cap on tests**).

**THE DRAFT IS ACCEPTED, WITH FOUR AMENDMENTS, ALL MADE BEFORE ANY OUTCOME EXISTS AND ALL STATED
WITH THEIR REASONS.** Its design is adopted essentially whole: the quadrant, the both-halves rule
inside it, the BH ladder at `k` = 12, the per-arm free kills, the no-interaction choice on A3, the
fallback-to-incumbent rule on A1, and §12's refusal to draft volatility-managed exposure are all
carried verbatim.

---

## 0. The quadrant, and the draft's census reproduces EXACTLY

**PANEL** — `data/free_analysis/UNIVERSE_BIAS_PANEL_full.pkl`, the corrected full raw universe.
**NEVER `data/backtest`**, whose universe is selected on a present-day property.

**BUILD QUADRANT** — **2009-2019 × `stable_key_half(ticker) == 0`**, where
`stable_key_half` is **`scripts/r4_x1_accounting_universe.py`'s own function, CALLED and never
re-implemented** (`B7`): `int(sha1(ticker).hexdigest(), 16) % 2`, no seed, no row order.

**Re-measured here rather than taken on trust, and it agrees with the draft to the row:**

| | rows | dates | names | names/date min / median / max |
|---|---|---|---|---|
| **BUILD** 2009-2019 × half 0 | **87,436** | **44** | **3,545** | **1,679 / 2,009 / 2,132** |
| CHECK 2020-2026 × half 1 — **NOT READ** | 57,792 | 25 | 3,498 | — |

Span 2009-03-27 → 2019-12-31. **Both halves inside the build quadrant: 24 early / 20 late**, both
above the shipped `min_dates = 16` — **but 20 is only four above it**, which is `S18`'s situation,
so a thin-half null here means *"could not be separated at this resolution"* and nothing stronger.

**THE CHECK QUADRANT IS NOT OPENED IN THIS ITEM AT ALL.** Looking at it to choose among these
arms would spend it with no replacement.

**No bar, floor or MDE from the 2,531-name panel transfers.** The corrected universe is 9,645
names and `UNIVERSE-BIAS` part 2 measured that the headline alpha itself falls from +7.17% to
+2.83% on it. **No X7 floor is quoted anywhere in this item**, and every critical value is
**LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`).

---

## 1. Trial charge

**TEN equity trials**, one per arm actually registered to run: **A1, A2a, A2b, A3, A6, A7, A8,
A9, A10, A11**. Equity **264 → 274**. Hurdles **derived, never typed**:
`hlz_hurdle(264) = 3.3394457932855612`, `hlz_hurdle(274) = 3.35056058186927`.

**ZERO for A4 and A5, and the counter-argument is stated rather than hidden.** Neither searches
anything on this panel: **A5** is excluded by a **loader-allowlist fact** established before the
register (its columns are absent, so it cannot be built without a rebuild), and **A4** is
**withdrawn by the draft's own scope condition** (below). That follows `DC-1`, `W-14`, `MB15` and
`PANEL-EXT-RECHECK`, all logged at zero trials for items that never ran. **The counter-argument
is `E-1`**, which kept its trial after `K2` fired, and **`MA6` holds that overstating `N` is the
safe direction — so this reading is the LESS conservative one and a later reader should amend
upward rather than downward.**

**BH stays at `k` = 12 regardless**, per the draft's §0b: shrinking `k` after a build failure
makes every surviving threshold easier. **Trials and BH are different instruments and are
declared separately**, which is the conservative combination.

`MB31`: the next adopt-set flip is seed **1017 at equity `N` = 688**, so **no permutation floor
can move** and this register compares nothing to one.

---

## 2. AMENDMENT 1 — **A4 IS WITHDRAWN**, by the draft's own condition, and there is a second independent reason

The draft's §4 says: *"if r1's register already names a junk filter, **this arm is withdrawn
rather than run alongside it** — two lanes publishing two junk filters is how one question comes
to have two answers."*

**`PREREG_tiered_pool.md` §2 names one** — positive TTM net income, positive TTM free cash flow,
and leverage not in the worst third — and it has been **run and reported** (`TIERED-POOL`,
2026-10-06, both arms failing Don's rule). **So A4 is withdrawn as written.** The condition is
honoured rather than reinterpreted: CHS's probability is a *different* junk definition from
`TIERED-POOL`'s three conditions, and that is precisely the argument a reader could use to run it
anyway — **relaxing a withdrawal condition after watching it fire is `W-28`'s rule in reverse**,
so it is not taken.

**AND IT WOULD HAVE BEEN BLOCKED ANYWAY, which is recorded because it changes what a successor
needs.** CHS's `TLMTA` is total liabilities over market cap, and **`liabilities` is ABSENT from
`WRDSProvider._KEEP["fundamentals"]`** — verified before this register. So A4 needs a **panel
rebuild with new source columns**, which is **exactly A5's scoping kill**. A CHS register remains
available later and should be **batched with A5**, since both pay the same rebuild.

---

## 3. AMENDMENT 2 — the panel carries **no `z_*` columns**, so four arms need one shared rebuild

The draft treats A7 (`z_neg_issuance`) and A11 (`z_high_prox`) as cheap because those inputs
already exist. **They exist in the BUILDER, not in the artifact.** Measured: the corrected panel's
columns are the seven themes plus `growth`, `low_risk`, `sentiment`, `market_cap`, `sector`,
`fwd_ret`, `bench_ret`, `date`, `ticker` — **and nothing else**. `keep_numbers=True` adds the
`z_*` columns; without it there is no `z_neg_issuance` and no `z_high_prox` to score, and **A1
cannot replace `z_book_to_price` either.**

**So ONE rebuild of the corrected full-universe panel at `keep_numbers=True` serves A1, A7, A11
and A2a**, and it must be the **same universe and the same 2026-10 vintage** as the panel above or
the comparison stops being a comparison. **A2a additionally needs `residual_momentum=True`**,
which is a **build-time** flag (`factors.py:285-292`), so it is a **second** build of the same
universe differing in that flag alone — the `S25-REPAIR` discipline of one build per toggle, so
the arm and its base differ in the toggle and nothing else.

**This is a build cost, not a design change**, and no bar moves because of it.

---

## 4. AMENDMENT 3 — **A6 gets its own pre-outcome coverage kill, and the record says it will fire**

The draft fixes A6's bands to be **relative percentiles** rather than the census's absolute
$5B / $5M, citing `INDEX-CHOICE-ARM4`: an absolute-rank filter is not invariant to subsampling the
universe. **That repairs invariance and does nothing about coverage**, and coverage is the binding
constraint here.

**Measured, and published in `UNIVERSE-BIAS` part 3 before this register: the ADV inputs cover
2,524 of 9,645 corrected-universe names — a name share of 0.2617 — against 0.8278 on the
restricted universe, because `MC9_SEP_ADV.pkl` and `B13_ADV_PANEL.pkl` were built on
`data/backtest`.** And **the CRSP cell overlap is ZERO** on a re-gridded panel.

**A name with NO ADV observation fails an ADV floor exactly as a genuinely illiquid name does**,
so without a kill A6's band would quietly become *"small AND present in the old ADV input"* —
the incumbent universe wearing the corrected universe's name.

**A6 `K0` (NEW, pre-outcome, free):** the share of build-quadrant rows with a computable
point-in-time ADV must be **≥ 0.70** — the project's own non-null rule, inherited and not chosen
here. **On the figure above this kill is expected to FIRE, and it is registered at 0.70 anyway
rather than at a number chosen to let the arm through** (`W-28`: a pre-committed bar may not be
relaxed after watching it fail). If it fires, A6 is reported **NOT RUN on coverage**, its trial
is **still charged** (`E-1`), and the honest statement is a **data cost**: extending the ADV
inputs to the corrected universe is a prep job, not an analysis.

---

## 5. AMENDMENT 4 — A2b's market leg, and A10's sector map, are pinned to this project's own data

Both are the draft's own intent; they are written into the register so they cannot drift.

* **A2b** uses the **panel's own value-weighted market return**, built from the panel's prices.
  **Ken French's library is used nowhere in A2b** — `AUDIT6_MANAGER_BRIEF.md` records it as
  *"free but permission-gated and factor-level — never a magnitude claim"*, and a signal whose
  construction depends on it could validate a build and could never ship. Declared as a
  **one-factor** residual, a deviation from the paper's three.
* **A10** uses **`S25`'s DATED GICS map** (`valuation/edge/sector_map.py`), **not** the panel's
  `sector` column, which is today's classification applied to historical rows — the look-ahead
  `S25` exists to repair. A date before a name's first classification must return `NOT_COVERED`
  and **never** the first span, which is the property `S25` pinned. A10 therefore also carries a
  **coverage kill at 0.70** on the build quadrant's own rows.

---

## 6. The arms, as registered

Each is scored as an **incremental information coefficient** on the build quadrant — the signal
residualised on the seven deployed themes, per-date Spearman against `fwd_ret`, HAC *t* over the
quadrant's 44 dates — **except A4 (withdrawn), A5 (not run) and A8 (event time, own permutation
p95)**. Every arm must clear **both halves inside the build quadrant** or it is `NOT_REPLICATED`
and does not reach Stage 2.

| arm | signal | free pre-outcome kill, and its bar |
|---|---|---|
| **A1** | intangible-adjusted `book_to_price` (Peters-Taylor on SF1 `rnd`/`sgna`, δ 15%/20%, 30% of SG&A), replacing `z_book_to_price` inside `value`; **where `K_int` is absent the row falls back to the INCUMBENT column** | `K1` share with computable `K_int` after burn-in **≥ 0.70**, measured on the ARM's own rows, reported as **three** numbers — truly non-null, structurally zero, absent — with the bar read on `non-null + structural zero` |
| **A2a** | the SHIPPED `residual_momentum=True` toggle (beta-neutralised momentum THEME) | must not be **INERT**: per-date rank correlation of toggled vs untoggled composite **< 0.995** |
| **A2b** | Blitz-Huij-Martens residual momentum, 36m formation, one-factor, *t*-scaled, skip-one-month | momentum costume: mean per-date \|ρ\| vs the `momentum` theme **< 0.60** |
| **A3** | information discreteness `sign(PRET) × (%neg − %pos)` over 12m daily returns, **standalone column, NOT an interaction** | `K1` share of rows with **≥ 200** daily observations in the window **≥ 0.70**, with a `MIN_PLAUSIBLE_SESSIONS` floor so a short trading year cannot read as a coverage hole (`MC12`) |
| ~~A4~~ | ~~CHS distress as a junk filter~~ | **WITHDRAWN** — §2 |
| ~~A5~~ | ~~net payout yield~~ | **NOT RUN** — scoping kill, `ncfdiv`/`ncfcommon` absent from `_KEEP` |
| **A6** | N1 small/mid core, bands as **relative percentiles** | **`K0` (new):** point-in-time ADV computable on **≥ 0.70** of build-quadrant rows — §4, expected to fire |
| **A7** | net issuance (`z_neg_issuance`) as its own arm, **winsorisation declared BEFORE the look**: the shipped `zscore`'s 2% clip, unchanged | coverage `z_neg_issuance` non-null **≥ 0.70** on the quadrant's own rows |
| **A8** | earnings-surprise drift in **event time**, bar is its **own within-date permutation p95** | spine coverage **≥ 0.70** and announcements per ticker-year within **[3.0, 5.0]** of the ~4 expected |
| **A9** | analyst neglect from IBES `numest`, **dated** link via `ibes_id.sdates` | **`K2` costume kill runs FIRST:** mean per-date \|ρ\| vs the `size` theme **< 0.60**. `E-1` died at 0.6114 and `R6`'s conviction signals read −0.815 to −0.854 — **a neglect proxy is a size proxy until measured otherwise** |
| **A10** | industry momentum on `S25`'s **dated** GICS map | momentum costume **< 0.60**, plus a **sector-map coverage kill ≥ 0.70** (§5) |
| **A11** | 52-week-high proximity (`z_high_prox`) | **pre-committed as a NEAR-DUPLICATE:** \|ρ\| vs `momentum` is already measured at **0.7596**, so a pass is read as *momentum measured differently* **unless the incremental IC survives residualising on `momentum` alone**, which is registered as a required second reading |

---

## 7. Void conditions

1. Opening the **check quadrant** (2020-2026 × half 1) anywhere in this item.
2. Reading the **1999-2008 proxy** here.
3. Changing any bar, band, percentile, kill threshold or the BH ladder **after any outcome is
   read**, or shrinking `k` below 12.
4. Quoting an **X7 floor**, or any bar measured on the 2,531-name panel, as if it transferred.
5. Running A4, or running A5 without the rebuild its scoping kill names.
6. Reporting an arm that cleared **one** half as anything but `NOT_REPLICATED`.
7. Scoring A3 as an **interaction**, or A11 without its momentum-residualised second reading.
8. Using **Ken French** data anywhere in A2b's construction.
9. Using the panel's **`sector`** column for A10 instead of `S25`'s dated map.
10. **Adopting anything.** Adoption is Don's, is a vintage event, and quotes the expected return
    at **half** the backtested size (McLean-Pontiff, `DECISIONS.md` 2026-10-06).

---

## 8. Expectations, recorded before any number

1. **A6's `K0` fires**, 90/10 — the ADV coverage is already published at 0.2617.
2. **A9's `K2` fires** (neglect is a size proxy), 60/40.
3. **At least one of A2a's inertness kill and A10's sector-coverage kill fires**, 55/45.
4. **Zero arms survive BH at q = 0.10 across `k` = 12**, 70/30. The record's base rate is the
   argument: five items motivated by structural orthogonality all confirmed orthogonal and not
   one cleared, and `UNIVERSE-BIAS` has just measured that this universe's own headline is not
   separable from zero.
5. **A8 is the arm most likely to survive**, 55/45 — it is the only one designed in event time,
   where the draft's own MDE arithmetic is ~1.66pp at `n_eff` 400 against 0.43-0.51 SD on the
   cross-section.
6. **A11 clears raw and fails the momentum-residualised second reading**, 65/35.
7. **A1's `K1` passes** (`rnd`/`sgna` are core SF1 fields), 80/20.

---

## 9. Not done

No Stage-2 look, no Stage-3 look, no 1972-1998 era (`OOS1`'s Gate B reads 0.837303 against a
pre-committed 0.90), no volatility-managed exposure (§12 of the draft, and `R1-VAR` governs), no
interaction arm, no percentile sweep on any kill, and **nothing adopted**.

---

*`STAGE1-BATCH1`. Register committed alone; trials booked separately before any runner exists.
Nothing below this line is edited after a number is read.*
