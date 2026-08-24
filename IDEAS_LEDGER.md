# IDEAS_LEDGER.md — the Frontier Scout's standing record

**Lane: Frontier Scout (Cowork), commissioned by `PROMPT_frontier_scout.md`; Season 2
commissioned by `PROMPT_scout_expedition2.md`. Sessions: 2026-08-20 (batch 1), 2026-08-20
(season 2).** This lane runs no tests, charges no trials, writes no verdicts, and owns exactly
`IDEAS_LEDGER.md`, `PREREG_DRAFT_*.md`, `HANDOFF_scout.md`. Everything below is a proposal or
a record of one.

**Status vocabulary:** `PROPOSED` / `DRAFTED` (full PREREG draft exists) / `SENT` /
`EXECUTED-BY-LANE` / `KILLED-BY-ME` / `PARKED` (un-parking condition named) /
`DESIGN-RECORDED` (dependencies named, no charge until they resolve).

**Counters at this writing, freshly read from origin/main (not quoted from any audit):**
equity **235** (HLZ hurdle **3.3044**), options **305 reported / 301 distinct** (hurdle
**3.3824** at 305 — reported is stricter and is the quoted bar while `MB16`'s dedup finding
awaits its decision), infra **19**. One adoption in ~555: `S14`. Newest commit read:
`2e623e2` (origin/main; local checkout 11 behind — `MA20`'s drift, reported to Don).
`MB31`'s dated trigger: the next permutation-floor flip is at **equity N = 247** — 12 trials
of headroom, and the season budget below is sized to stay inside it.

---

## BATCH 1 (2026-08-20) — statuses

* **SC-1 (prior calibration)** — `EXECUTED-BY-LANE`, **CANNOT-TELL** by its own §3.1 rule:
  gap −0.0500, cluster CI95 half-width 0.1917 > 0.15 ceiling. The binding constraint was
  **clusters, not pairs** (43 OUTCOME pairs cleared the 25 bar; only 3 clusters — the scoring
  tables live in three handoffs). Informative anyway: Brier 0.1548, **skill +0.266** over the
  base rate, and the sign ran **mildly pessimistic** (mean prior 0.6477 vs base 0.6977) —
  refuting my 70/30 OVERCONFIDENT-OPTIMISTIC expectation. Successor: SC-1b, parked below.
* **SC-2 (S17 legend)** — `EXECUTED-BY-LANE`, zero trials: S17's row and `CLAUDE.md`
  corrected in place; codes 34/35's 2024-12/2025-05 sunset recorded as a **lead limited to at
  most one of five arms** (91/71/81/52 run to 2026-07-31); the gated successor **not
  licensed**. Closed as this lane hoped — a record correction, not a re-open.
* **SC-3 (TIER-E-FIN)** — `SENT` (routed; carried in the season budget below).
* **SC-4 (record-this-week surface)** — `EXECUTED 2026-08-19` (shipped on `/work/research`; kill condition run first and passed, the exemption widening it required was measured rather than argued. Ledger row `SC-4`; `HANDOFF_appfixes.md` session 44. Status carried across the expedition-2 merge — the branch predated the landing).
* Batch-1 kills and parks are carried in the cumulative sections at the bottom.

---

# SEASON 2 — the deep scrub (all entries below written 2026-08-20)

**Order of work honored:** the blind EO rubric (`PREREG_DRAFT_eo_reopen_rubric.md`) was
written FIRST, before the in-flight event-ownership register landed, from commit-subject
evidence only. Its blindness proof is its commit date.

## PART 3 FIRST IN EXECUTION ORDER — the instruments (all infra; infra gates no claim)

* **I-1 — the RND builder** (Breeden–Litzenberger risk-neutral densities from the FROZEN
  chains). Owner: options-bot lane. 1 infra trial. Validation fixed in the consuming
  registers: integrate to 1 ± 0.02, monotone CDF, parity-forward reproduces as-traded spot
  within quoted-spread band on ≥95% of chains (`U1-SPLIT` travels). **Unblocks O-1 (its
  stage-0 kill), E-8, E-4's option-implied half, and every future tail question.** Literature:
  BL 1978; NY Fed SR-677 gives the standard stable implementation; RND crash-content is
  mixed-to-contested in the literature (J. Empirical Finance 2018) — imported here as an
  INSTRUMENT, not as a signal claim.
* **I-2 — the name-level percentile engine** (TIDEMARK's expanding-percentile port: burn-in,
  publication lag, no look-ahead — all solved with tests there; METHOD crosses, no TIDEMARK
  data crosses, `MB24` untouched). Owner: edge lane. 1 infra trial. **Unblocks E-6.** Ships
  with the burn-in census (below) so the survivorship cost is a printed fact before any arm.
* **I-3 — the crash-count gate as a library** (`MA28-CARD`'s verdict machinery extracted so
  every crash-flag register reuses ONE implementation — `B7`'s nine-call-sites lesson).
  Owner: edge lane. 1 infra trial. Validation: reproduces `MA28-CARD`'s banked verdict
  bit-identical. **Unblocks E-4, E-8, INV-A, O-1's C1.**
* **I-4 — the event spine** (one canonical PIT earnings-date table from EVENTS code 22 +
  the in-tree legend, coverage-labelled per name-quarter; missing = unknown, never "none" —
  the legend's own rule). Owner: edge lane. 1 infra trial. Validation: reproduces `O6`/`O7`'s
  banked earnings joins. **Unblocks E-7, O-4/O-5's designs, and every EO-family follow-on.**

## THE SEASON PORTFOLIO — EV-ranked within book

### Equity (committed: E-1…E-6 = 6 trials, 235 → 241; reserve: E-7, E-8 = 2 more, max 243)

* **E-1 · S-SEED-4 — the graveyard votes** — `DRAFTED`
  (`PREREG_DRAFT_s4_graveyard_stouffer.md`). One pre-committed, unfitted, published-sign
  composite of every registered signal that is NOT an incumbent input; incremental-IC under
  `MB7`'s gate, both bases co-primary. Mechanism: polygenic aggregation of subthreshold truths
  (Zaykin's weighted-Z; Stambaugh–Yuan's 11-anomaly average is the finance analog). NOT-A-
  COSTUME: `MLCOMB` fit and reversed — this fits nothing; the incumbent-input exclusion is
  structural. Kills: rho vs composite/size > 0.60; census < 25 eligible signals. Power: the
  `MB18` design class — **0.43/0.51 SD at 80%, 0.30/0.36 at 50%**. Prior **~8%** (the
  orthogonality wall is now 5-for-5 and this file says so out loud). Verdict grammar:
  CONFIRMED / NULL / WITHDRAWN(K1–K3), which-signal mining explicitly unlicensed.
* **E-2 · S-SEED-3 — Δcomposite (fundamental momentum)** — `DRAFTED`
  (`PREREG_DRAFT_s3_delta_composite.md`). First difference of the shipped composite; sign
  POSITIVE declared; kills vs momentum theme, banked PEAD column, and level (all 0.60,
  separate pass). Verified never tested (289 rows, 134 items); PEAD's local rejection is the
  named hostile prior; Novy-Marx w20984 is the mechanism's citation, status contested-in-
  degree. Power: 0.43/0.51 SD at 80%. Prior **~10%**. 1 trial.
* **E-3 · S-SEED-1 — theme dispersion (the conviction statistic)** — `DRAFTED`
  (`PREREG_DRAFT_s1_theme_dispersion.md`). Cross-theme std per name, ≥4-theme eligibility
  (`C7`'s 22.01% floor), sign NEGATIVE declared (DMS mechanism, status weakened-post-2000s);
  triple-locked against `R6`'s autopsy (size), mechanical extremity (|composite|), and
  coverage-in-costume (theme count). Power: 0.43/0.51 SD at 80%. Prior **~10%**. 1 trial.
* **E-4 · S-SEED-5 — the market-tail crash flag beside the accounting card** — `PROPOSED`.
  Object: Hill tail index on trailing 252d daily returns (owned closes; k fixed at the top 5%
  order statistics), worst-quintile flag; **verdict object is CRASH RATE via I-3, never
  alpha** (`MA28`'s proven gate style; `S10`'s exclusion-screen corpse avoided — this is a
  card candidate, not a screen). The question: does it catch crashes the accounting flags
  MISS (incremental crash-capture on accounting-clean names)? NOT-A-COSTUME: neg-idio-vol/MAX
  nulls were RETURN verdicts — different object; kill: flag-overlap census vs accounting
  flags > 70% (descriptive, pre-outcome) → withdrawn. Literature: Kelly–Jiang (NBER w19375)
  tail loadings; Bali et al. hybrid tail risk — mixed replication, imported as hypothesis.
  Power: via I-3's hook on clean-subset base rate 0.87%/qtr; the register prints required-n
  before running. Prior **~12%**. 1 trial. Depends: I-3.
* **E-5 · INV-A — the hazard curve of flagged names (scout invention)** — `PROPOSED`.
  WHEN do 2-of-3-flagged names crash — a survival curve (V6-B's machinery reused) over the
  four quarters post-flag, with one pre-committed claim: hazard is front-loaded (≥60% of
  excess crashes inside 2 quarters). Feeds O-1's tenor choice and the card's honesty copy
  ("flags decay"); nearest rows: `MA28-CARD` (rate, not timing), `V6-B` (dip survival —
  different conditioning event), `S22` (term-structure convention travels). Kill: if the
  quarterly crash base is too thin for the KM CI to separate front from flat (power hook
  printed first), UNPOWERED and stops. Prior **~40%** on the shape claim — it is a shape
  question, not an edge question, and is priced accordingly. 1 trial. Depends: I-3.
* **E-6 · S-SEED-2 — the temporal axis (TIDEMARK transform)** — `PROPOSED`, gated on I-2 +
  census. One arm only, no grid: the **value theme vs the name's own 5-year expanding
  history** (temporal value), sign POSITIVE declared; burn-in pre-committed at 5y (a 10y
  burn-in leaves ~28 dates and dies at `S18`'s floor — the seed's own suspicion, confirmed by
  arithmetic: first usable date ≈2014, the basis-seven world, coverage printed). Pre-outcome
  kill: burn-in census must leave ≥60% of panel rows eligible, else UNPOWERED-BY-CONSTRUCTION
  and the engine ships without an arm. NOT-A-COSTUME: `S20`/`S21` swapped the cross-sectional
  standardiser — this ADDS a temporal column and swaps nothing; incremental-IC gate handles
  the value-overlap by construction. Power: 0.43/0.51 SD class. Prior **~10%**. 1 trial.
* **E-7 · X-SEED-2 — event-time as a coordinate system** — `PROPOSED (reserve)`. Stage A
  (zero trials, needs I-4): the descriptive event-time census — composite IC by
  days-since-earnings bucket, coverage-partitioned (code 22 runs ~1.65 events/ticker-yr;
  missing = unknown). Stage B (1 reserve trial): only if stage A shows structure, a blind
  register on ONE pre-named question (IC conditional on event-window bucket), bars written
  before stage A is re-read — the `S9` sequencing discipline, declared here in advance.
  NOT-A-COSTUME: PEAD-the-signal is rejected; the FRAME is the new object. Prior of stage B
  ever charging: ~30%.
* **E-8 · X-SEED-1 — where accounting flags and option prices disagree** — `PROPOSED
  (reserve)`, gated on I-1 + O-1's stage-0 census. Object: flagged names whose RND left tail
  is thin vs fat; verdict: crash-rate ratio (I-3 gate) of the two cells — does the market's
  disagreement identify false flags, or does it miss real ones? Charged to EQUITY (predicts
  the underlying — `P1S0` precedent). Genuinely-new bridge object; the mechanism is
  mispricing, not orthogonality, and the register must say which cell is the claim. Prior
  **~10%**. 1 reserve trial.

### Options (committed: O-1, O-2, SC-3 = 5 trials, 305 → 310; reserve: rubric + O-4 = 3 more, max 313)

* **O-1 · O-SEED-1 — long puts on accounting-flagged names (the star)** — `DRAFTED`
  (`PREREG_DRAFT_o1_flagged_puts.md`). Premise verified this session: **the banked book is
  100% calls** (`pick_contract(right="C")` at both entry sites; `MB1`'s 864→432-calls menu).
  Mechanism-backed (MA28's 3.04× crash discrimination, strongest in megacaps where chains
  live), moneyness-targeted strikes (the V6-OPT-named re-opening applied on the side its
  mechanism favours), and **killed-before-charged if the market already prices the flag** —
  the RND pricing kill (K2) compares risk-neutral crash mass flagged-vs-unflagged against the
  physical 3.04× BEFORE any arm. 2 trials, gated on I-1. Prior **~10%** (→ ~20% if K2 shows
  underpricing; → VOID at ≥3.04). Either K2 branch ships as record/product material.
* **O-2 · O-SEED-3 — menu breadth as a refusal rule, for the LIVE book** — `PROPOSED`.
  The fillable-menu census exists (`MB1`: median 5 of 864); `O10` measured liquid vs thin at
  +5.82%/−3.11%; `MB1-SEL`'s C-RANGE then measured coverage gradients in BOTH books (alert
  +1.94pp, control +4.48pp) — so menu-thinness conditions absolute outcomes everywhere, and
  the honest consumer is the LIVE paper options book (which trades), not the dead alert
  entry. Register: banked-book counterfactual (kept-vs-refused expectancy, cluster CI) + the
  `O11` survivability leg re-run under refusal; the alert-RELATIVE caveat is stated in the
  register (covered entries are where the alert does relatively WORST — refusal fixes cost,
  not edge; `R2` stands regardless). Must cite `O13` Q3a (its refusal pool "refused nothing")
  and say why menu-level differs from contract-level: the menu is a pre-trade fact about the
  CHAIN, not a post-hoc feature of the pick. 1 trial. Prior **~15%** on the counterfactual
  clearing; the live wiring is a product decision either way.
* **O-3 · the EO re-open rubric** — `DRAFTED BLIND` (`PREREG_DRAFT_eo_reopen_rubric.md`),
  written before the EO register landed; classifies all ~40 options-book verdicts into
  EO-SENSITIVE (7 families, priority-ordered, SIZING-A's regroup first at 1 reserve trial) /
  EO-INSENSITIVE (with `O17C4` as the already-answered template) / UNPOWERED-IF-STRATIFIED
  (the MB22 arithmetic: at s ≈ 0.3 the spanning cell's 80%-power MDE is ~1.7× pooled — above
  everything the flow features ever showed). Self-closing on an EO null.
* **O-4 · O-SEED-2 — the spanning × liquidity 2×2** — `DESIGN-RECORDED (reserve)`,
  dependent on EO confirming (filed with the dependency named, Don's standing rule). Four
  cells from two measured splits (`MB3`'s $130,855-vs-$24,391 terminal wealth; `O10`'s
  +5.82/−3.11); all four reported, `O26`-floor per cell, ACTIONABLE requires `O11`'s leg 4.
  2 reserve trials. Prior ~15% that the spanning×liquid cell is the diluted-verdict story.
* **O-5 · O-SEED-4 — multi-event LEAPS** — `DESIGN-RECORDED`, 0 trials this season. Doubly
  gated: EO must confirm AND the Tier-E reuse adjudication (26 symbols) must land first (the
  harvest handoff's own precondition). Design banked now: hold-through-k-events on 2016–18
  LEAPS, theta-between-events vs event-jump compounding, `DEEPITM-FIN`'s cost frame. Prices
  when its gates open.
* **SC-3 · TIER-E-FIN** — `SENT` (batch 1; 2 trials carried in this season's options budget).

## SEASON 2 PLAN — the block for Don

**The block: 15 committed trials (4 infra + 6 equity + 5 options) and 5 named reserves
(2 equity conditional, 3 options conditional).** What it does to the bars, computed at
today's counters and quoted at both ends:

| counter | now | committed lands | with full reserve | hurdle now → committed → max |
|---|---|---|---|---|
| equity | 235 | 241 | 243 | 3.3044 → 3.3128 → 3.3145 |
| options | 305 | 310 | 313 | 3.3824 → 3.3872 → 3.3900 |
| infra | 19 | 23 | 23 | gates no claim |

Equity stays **under the N = 247 floor-flip trigger** (`MB31`'s seed-1003) with 4 trials of
headroom even at full reserve — no recalibration is forced by this season, and any in-season
surprise that would cross 247 goes to Don first. The Deflated Sharpe's `sr0` rises at every
landing (stale-by-construction, `MB31`); the artifact refresh at season end re-derives it
once rather than per-trial (`MA21`'s lag rule).

**Execution order (dependencies before dependents):**
1. I-1…I-4 (instruments; parallelizable across lanes; nothing downstream runs early).
2. E-1, E-2, E-3 (independent singles on the existing panel — the cheap core).
3. O-1 stage 0 (the RND kill decides the star's fate before its trials are spent); O-2.
4. E-4, E-5 (I-3-dependent); E-6 (I-2-dependent, census first).
5. E-7 stage A (descriptive); E-8 and O-4 and the rubric's SIZING-A only as their gates
   resolve (EO landing; K2 census).
6. Season close: artifact refresh, MB31 map re-run, outcomes back into this ledger.

**Cut lines, in the order they drop if Don trims (and what each cut costs):**
1. **O-4** (2 reserve) — conditional anyway; cutting it pre-answers nothing.
2. **E-8** (1 reserve) — double-gated; the disagreement census still exists inside O-1's K2.
3. **E-7 stage B** (1 reserve) — keep the free descriptive; the frame survives.
4. **E-6's arm** (1) — keep I-2 the instrument; the temporal axis waits a season.
5. **O-2** (1) — the menu census stands; the live book keeps trading unfiltered.
6. **E-4 or E-5** (1 each) — the card family narrows to accounting-only for now.
**The floor that is not cut without killing the season: I-1 + E-1/E-2/E-3 + O-1.** That
minimal expedition is 4 infra + 3 equity + 2 options = 9 trials and still touches every
territory the commission names.

**Top-5 executor-ready drafts shipped this session:**
`PREREG_DRAFT_eo_reopen_rubric.md` (blind, do-not-edit-after-EO),
`PREREG_DRAFT_o1_flagged_puts.md`, `PREREG_DRAFT_s4_graveyard_stouffer.md`,
`PREREG_DRAFT_s3_delta_composite.md`, `PREREG_DRAFT_s1_theme_dispersion.md`.

---

## KILLED-BY-ME — cumulative, with reasons, so no successor re-derives them

**Season 2 kills (including two of the manager's seeds, as invited):**

* **O-SEED-5 — calendar spreads around earnings: KILLED.** The front leg's profit *is* the
  closed short-vol family's edge: `O7`-B1 measured the market overpricing the event move
  (implied 5.4512% vs realized 4.7773%) and that richness is exactly what a short front-month
  monetises — `O9` closed the family and `V6-OPT` re-killed it on mechanism. "Net-vega-
  positive" does not separate it: the structure's event-window P&L driver is the front-leg
  crush, and a two-leg single-name structure pays `D9`'s 4.7–12.6%-of-premium costs TWICE on
  a differential (implied−realized ≈ 0.67% of spot) that is smaller than the double spread.
  I could not separate it from the closed family; per the commission, killed by its own
  author's rule.
* **S-SEED-6a — peer residuals (fundamental-similarity neutralization): KILLED.**
  `S15`'s closure is explicit — *"with S25 closed as unobtainable, sector-neutral in every
  form is finished"* — and a PIT-similarity peer group residualization is a generalized
  neutralization: the same intervention (rank within a peer partition) with a fancier
  partition. `SECTOR-NEUTRAL-B6` additionally measured that the trade-off the family's case
  rested on "does not exist on this panel." A different partition does not carry the specific
  re-open evidence the closure named (none was named — it says *finished*). The lead-lag
  HALF of the seed survives separately as a park (below).
* **S23-TRAJECTORY — Δ(implied-growth gap): KILLED** (was parked batch 1, un-deferred by
  `MB18`'s landing, and the landing is what kills it). The LEVEL is rejected with a tight
  bound (largest |t| 1.5617 vs 2.71; effect −0.08 SD, 5.4× under detection), the sign lives
  in the solver's CENSORING (`implied_bounded`, 30% of rows), and the first difference of a
  reverse-DCF gap is mechanically price-driven — a momentum costume on a dead parent, under
  an orthogonality wall now 5-for-5. Nothing here carries re-open evidence.
* **INV-C — the options-implied borrow rate (r*) as a cross-sectional stock signal:
  KILLED at my own desk before proposing.** r* from deep-ITM parity IS the put–call parity
  deviation in rate form — `MA31` ran the Cremers–Weinbaum deviation properly (matched
  strikes, registered sign) and got NULL-and-uninterpretable with the published sign
  unreproduced. A rate re-parameterisation of a null is the same trial in different units.

**Batch-1 kills, standing:** knockoffs/stability selection on the 53 signals (weight-scheme
family in costume; `MLCOMB` reversed OOS; `X3`); Cox/AFT tenure models (no consumer:
`S22`/`S23`/`MA30` own tenure and exits); "obtain the EVENTS legend" (already in-tree,
became SC-2); live-vs-panel drift study (covered by `V2*`/`MB33`/`MB28`); regime/seasonality/
orthogonality anything (`MB13`'s 34.2-years arithmetic; `MA58-SEAS`; the wall, now 5 bodies).

## PARKED — cumulative, un-parking conditions named

* **S-SEED-6b — peer momentum via PIT similarity (the lead-lag half).** Cohen–Frazzini
  (JF 2008) economic-links momentum and Ali–Hirshleifer's shared-analyst version are robust
  literature — but both run on LINK data (customer lists, analyst coverage) this project
  does not own, and a 53-signal-similarity proxy for economic links is unvalidated: the
  register would test the proxy and the effect jointly, which is two hypotheses in one trial.
  Un-parks if a real link dataset is ever owned, or if someone designs a proxy validation
  that is itself pre-registerable at zero outcome risk.
* **MB15-SLIM** — unchanged from batch 1: UNPOWERED-BY-CONSTRUCTION at the standard design
  (post-2019 cache ≈2,446 units → 80% MDE ≈17pp vs a book where no flow feature ever showed
  9pp). Un-park: a new statistic class, years more alert-days, or a live book that gives
  flow features a consumer.
* **JKP-S22 term-structure replication** — **un-parked by `MB21`'s landing** (S22 stands
  against the persistence-preserving null; the instrument now exists) and immediately
  re-parked as SECOND WAVE: it needs the persistence-null rebuilt on a foreign monthly panel
  (a build, not a rerun) and the season's equity budget is spent better on virgin objects.
  First candidate for Season 3; licence flag travels (JKP research-only, product never).
* **SC-1b — prior calibration, item-clustered successor.** SC-1's CANNOT-TELL was a cluster
  problem (3 handoff-clusters), not a pairs problem (43). A successor clustering by ITEM with
  the adjudication universe widened to ledger verdict cells is a legitimate new design; the
  result would be informative (SC-1's point estimates: skill +0.266, sign mildly
  pessimistic). Un-parks whenever Don wants 1 infra trial spent on self-knowledge; not
  season-critical.
* **Conformal fair-value bands** — unchanged (posture conflict with `V3`; un-parks only on a
  product decision to prefer bands over labels).

## OUTCOMES RELAYED

* 2026-08-20: SC-1 CANNOT-TELL (clusters); SC-2 landed (correction only, successor not
  licensed); MB18 REJECTED (kills S23-TRAJECTORY); MB1-SEL VOID pre-arm (C-RANGE confound
  2× the residual — selection stays OPEN, `MB2` PARKED BY DON); MB21: S22 STANDS, LS-leg
  boundary hardened to one year, `placebo_panel` confirmed too easy by +0.1–0.25 t at long
  horizons (any close call against it is unsafe — noted for all future long-horizon
  registers).

## AMENDED 2026-08-20, MID-SESSION (append-and-amend, never silently rewritten)

**`MB8` landed while this file was being written: KILLED — the crash-flag sizing haircut is
dead, and the finding is that the flags are NEARLY DISJOINT FROM THE BOOK** (equity `N`
235 → **236**; hurdle now **3.3057**). Consequences absorbed here rather than left to rot:

* **The season table shifts one trial:** equity 236 → committed 242 (hurdle **3.3133**) →
  full-reserve 244 (**3.3158**), leaving **3 trials of headroom** under the N = 247
  floor-flip instead of 4. The budget still fits; an in-season surprise now goes to Don one
  trial sooner.
* **O-1 (flagged puts) is strengthened in framing, unchanged in design:** the flags being
  nearly disjoint from the top-decile book means a flagged-put book is an INDEPENDENT book,
  not a hedge on the equity book — the register already made no hedge claim, and now must
  not (the disjointness is measured).
* **E-4/E-5 unaffected in mechanism** (they gate on PANEL crash rates, not book membership)
  — but `MB8`'s disjointness number belongs in both registers' coverage prints, and the
  crash-gate library (I-3) inherits `MB8`'s implementation as prior art to reuse, not
  rebuild.
