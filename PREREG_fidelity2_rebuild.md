# PRE-REGISTRATION — FIDELITY-2: the two failed themes, rebuilt to the panel's definition

**Committed alone, before any rebuild code exists and before any FIDELITY-2 number has been
seen.** The bar is not re-derived: it is the one already registered in
`PREREG_theme_restoration.md` (`1d12822`) and already computed.

`institutional` scored **ρ +0.1706** and `insider` **ρ +0.3596** against a **0.60** bar. This
document says why each diverges — diagnosed at code level, not guessed — what "mirror the panel"
means concretely for each, and what a second failure closes.

---

## 1 · DIAGNOSIS — why each live column is a different quantity

### 1.1 `institutional` — the FORMULA matches and both INPUTS diverge

The theme is `mean(z_inst_accum, z_sm_breadth)` in both builds. `sm_breadth` (growth in holder
count) already matches. Two divergences, both in `inst_accum`:

**(a) DOLLARS vs SHARES — and I chose shares on purpose.** The panel's `_inst_accum`
(`fundamental_panel.py:738`) reads `_f(r, "totalvalue", "value", "sharesheld", "shares")`, i.e.
**dollar value first**, and returns `cur/prev − 1`. My V2G build computes
`rec["shares"] / p["shares"] − 1`, and `tests/test_live_theme_sources.py` pins that choice with
the reasoning *"Otherwise a quarter's price move would make this a momentum signal in a 13F
coat."* **That argument is sound and it is exactly why the column does not match**: the panel's
quantity deliberately CONTAINS the price move, and mine deliberately removes it. I built a better
signal and a different one. Fidelity is not a contest about which is better.

**(b) THE QUARTERS ARE TWO PERIODS APART.** The panel uses only quarters whose filing was public
by the scoring date, at a 45-day lag. At its last cross-section (2026-01-28) the usable pair is
therefore **2025-09-30 vs 2025-06-30**. My V2G build used **31-MAR-2026 vs 31-DEC-2025** — the
most recent complete periods as of *today*. Those windows do not overlap at all.

### 1.2 `insider` — a DIFFERENT ESTIMATOR, plus a fabricated neutral

**(a) THE STATISTIC IS NOT A NOISY VERSION OF THE PANEL'S, IT IS A DIFFERENT FUNCTION.**

| | panel (`_insider_score_at`) | live (`screener/insider.py`) |
|---|---|---|
| magnitude | `net = Σ signed transaction value (USD)` | `pressure = Σ code_weight × role_mult × **√value**` |
| weighting | none | per-transaction **code** weight and **role** multiplier |
| cluster bonus | `min(10, 2 × count of positive transactions)` | `min(10, 3 × (distinct buying FILINGS − 1))` |
| scale | `tanh(net / 5e6)` | `tanh(pressure / 4000)` |

The square root alone is monotone and would not move a rank correlation much. **The code and role
weighting is not a monotone transform of raw net**, and the cluster term counts a different thing.
These are two different estimators built from the same filings.

**(b) A FABRICATED NEUTRAL WHERE THE PANEL HAS NO OPINION.** The panel returns **`None`** when no
transaction falls in the window (`if b <= a: return None`). The live scraper returns **50.0** —
*"genuinely quiet (or no Form 4s in the window)"*. That is an honest choice for a product and a
fatal one for a rank correlation: **179 of 500 served names (35.8%) sit at exactly 50.0**, a
single enormous tie block against panel values that are absent entirely.

**(c) THE WINDOWS ARE DISJOINT** — mine is the last 90 days; the panel's is the 90 days ending at
its own cross-section.

---

## 2 · THE REBUILD — mirror the panel, as closely as public sources allow

**Nothing here is a re-derivation of the gate. Only the COLUMNS change.**

### 2.1 `institutional`
1. `inst_accum` = **dollar** value ratio, `value_cur / value_prior − 1`, mirroring the panel's
   field order. *(Free: the aggregate already carries `value`.)*
2. Periods realigned to the pair the panel would have used at its cross-section: **30-SEP-2025
   (current) vs 30-JUN-2025 (prior)**, requiring the two SEC 13F datasets covering those filing
   windows.
3. `sm_breadth` unchanged — it already mirrors the panel.
4. The join, anchor and `MIN_HOLDERS` floor are unchanged: they decide WHICH ISSUER a row is, not
   what is measured, and they were never the suspect.

### 2.2 `insider`
1. **`None` when no transaction falls in the window**, exactly as the panel does. No fabricated
   neutral.
2. The panel's statistic verbatim: `net = Σ signed value`, `buys = count of positive
   transactions`, `score = clip(50 + 40·tanh(net/5e6) + min(10, 2·buys), 0, 100)`. **No code
   weight, no role multiplier, no square root** — those are the live product's improvements and
   they are what makes it a different column.
3. **Window realigned** to the 90 days ending at the panel's cross-section, from a date-aligned
   Form 4 crawl. Sized before writing this: **5,639 filings across 358 names**, and 499 of 500
   cached submission indexes already reach back far enough, so the crawl is documents only.
4. The panel's same-day exclusion (audit B26) is mirrored: a filing dated the scoring day itself
   is not usable.

**THE DATE CONFOUND IS REMOVED BY THIS REBUILD.** `PREREG_theme_restoration.md` §2.3 warned that
the first gate was *conservative for a pass and ambiguous for a fail* because the windows differed.
Both themes are now measured on the panel's own window, so **a second failure is attributable to
the SOURCE**, which is what makes an UNRESTORABLE verdict meaningful rather than a shrug.

---

## 3 · THE GATE — unchanged, and not re-derived

Same statistic (Spearman vs the panel's own theme, same cross-section), same supporting conditions
(`n ≥ 100`, ρ > 0, p < 0.01), and the **same bar**:

    FIDELITY_BAR = max(0.60, P95 of |ρ| between DIFFERENT panel themes) = 0.60

Already computed at `1d12822` and **not recomputed to suit this run**. Coverage floors unchanged
(`COVERAGE_FLOOR` 0.05, `MIN_COVERAGE` 0.30, `MIN_DISTINCT` 2).

---

## 4 · THE VINTAGE INTERPRETATION — the registers are SILENT, so it is registered here, first

Searched before writing: `PREREG_v1_shadow_vintages.md`, `PAPER_TRACK_CONTRACT.md` and `CLAUDE.md`
contain **no rule for staged restoration** — no "staged", no "partial restoration", no "amend a
vintage". Amendment 1 says only that *any* ADOPTED change closes the current vintage and opens the
next. Read literally, each theme restored on its own day costs its own vintage and its own clock
reset, and a three-stage restoration would reset the clock three times.

**REGISTERED INTERPRETATION, fixed now, before any FIDELITY-2 number exists:**

> **An adopted change made while the current vintage has accrued ZERO complete days AMENDS that
> vintage instead of opening the next.** The vintage record is updated in place — its parameter
> snapshot, its `themes_scored_live` and its note — and its opening date does not move.

**Why this is the faithful reading rather than a convenience:**

* **Rule 6 protects a CLOCK, and there is no clock to protect.** Vintage 3 opened 2026-08-11 and
  has accrued zero complete days. Closing it would reset a clock already at zero — the penalty is
  identically nothing — while leaving a permanently empty vintage in the register.
* **The shadow comparison is unaffected.** The predecessor being shadowed stays **vintage 2**, the
  four-theme composite, which is the book the comparison is actually about. Opening vintage 4
  would shadow vintage 3 — a book that never ran for a single day — which is worse evidence, not
  better.
* **It cannot become a loophole, because it is bounded by a fact, not by judgement.** The moment
  vintage 3 has accrued one complete day, this clause stops applying and Amendment 1's ordinary
  rule resumes. There is no discretion in "zero complete days".

**If nothing passes, no amendment occurs and the vintage record is untouched.**

---

## 5 · WHAT A SECOND FAILURE CLOSES

A theme that fails the same bar after being rebuilt to the panel's own definition, on the panel's
own window, closes as **UNRESTORABLE-FROM-PUBLIC-SOURCES**, and the record must name **the missing
ingredient** — the specific thing the public source does not contain — precisely enough that a
D-series data-purchase decision can be priced against it. "It did not correlate" is not an answer.

---

## 6 · EXPECTATION, WRITTEN DOWN FIRST

* **`institutional` passes — 55/45.** Both diagnosed divergences are removable and the join was
  never the suspect. Against it: SF3 is a cleaned aggregation and raw INFOTABLE is not, and that
  residue is not removable here.
* **`insider` passes — 35/65.** The fabricated-neutral fix and the window alignment are real
  improvements, but the panel's SF2 transaction set and a Form 4 crawl are not the same universe:
  SF2 covers issuers my crawl reaches only through their own filings, and derivative/10b5-1
  handling may differ.
* **At least one passes — 65/35.**

*(This project's directional calls have been wrong more often than right.)*

---

## 7 · WHAT VOIDS THIS RUN

* Any change to the bar, the statistic, or the coverage floors.
* Comparing against anything other than the panel's own theme columns on the same cross-section.
* Restoring a theme that did not clear the bar.
* Amending a vintage that has accrued a complete day.

## 8 · TRIAL COST

**Zero. Equity `N` does not move.** Rebuilding a column to match a definition and re-scoring it
against an already-fixed bar searches nothing: no parameter is chosen and no arm is selected. The
rebuild is specified by the panel's code, not by which version scores better — and this document
fixes it before the score exists.
