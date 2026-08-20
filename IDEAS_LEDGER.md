# IDEAS_LEDGER.md — the Frontier Scout's standing record

**Lane: Frontier Scout (Cowork), commissioned by `PROMPT_frontier_scout.md`. First session
2026-08-20.** This lane runs no tests, charges no trials, writes no verdicts, and owns exactly
three files: this one, `PREREG_DRAFT_*.md`, and `HANDOFF_scout.md`. Everything below is a
**proposal or a record of one** — nothing here moves a ledger row, a counter, or a claim.

**Status vocabulary:** `PROPOSED` (in a ranked batch, priced, awaiting Don) / `DRAFTED` (full
PREREG draft exists) / `SENT` / `EXECUTED-BY-LANE` (outcome relayed back, one line) /
`KILLED-BY-ME` (died at my desk, reason recorded) / `PARKED` (alive but not proposable today,
with the un-parking condition named).

**Counters at this writing, freshly read (not quoted from an audit):** equity **234** (HLZ
hurdle **3.3031**), options **305 reported / 301 distinct** (hurdle **3.3824** at 305 — the
reported figure is the stricter bar and is the one quoted, per the safe-direction rule; the
dedup defect is `MB16`'s reported finding and another lane's decision), infra **17** (gates no
published claim). One adoption in the record: `S14`. Newest commit read: `8792762`
(MB34+MB35, 2026-08-19). Nothing has landed 2026-08-20 before this session.

---

## BATCH 1 — ranked, 2026-08-20

EV-ranked as audit #4 ranks: value × P(survival) ÷ trial cost, zero-cost items on value alone.
Every entry carries mechanism, not-a-costume, data, price, power, kill condition, prior, and
verdict grammar. **#1 carries a full PREREG draft** (`PREREG_DRAFT_scout1_prior_calibration.md`).

---

### SC-1 — Score the record's own stated priors: the register-calibration study — `DRAFTED`

**Territory (a) + (d). Trials: 1, infra (17 → 18; infra gates no published claim).
Prior: 80/20 that the extraction yields an interpretable calibration verdict; my point
expectation is OVERCONFIDENT-in-the-optimistic-direction on the priors and a shrinkage
median well below 1.**

**MECHANISM.** This project has done something almost no research shop does: it wrote a
numeric prior on the register *before* each run — 63 of 71 `PREREG_*.md` files carry an
expectations section, 36 carry odds in `NN/MM` form, audit #4 alone carries 13 `Prior: ~`
lines, and 22 write-ups already self-score as `Expectations N right, M wrong` — and then it
adjudicated every one. ~550 trials with priors, verdicts, effect sizes, halves, and MDEs is a
calibration dataset that took four months and ~$0 of extra cost to create, and **nobody has
ever aggregated it.** Scoring it (Brier + Murphy decomposition, reliability curve in three
pre-fixed bins) converts a folk practice ("state the prior, expect NULL") into a measured
instrument: every future register writes its prior against a known base rate and a known
personal bias direction. The same extraction yields the project's own replication crisis,
measured — the distribution of held-out-half effect ÷ full-sample effect across every trial
that banked both — which is the number rule-11 power statements should be shrinking expected
effects by, and currently aren't.

**NOT-A-COSTUME.** Nearest dead/done neighbours, by ID: `PARKED-POS` (read-only sweep over the
same archive — but an *inventory*, no statistic, no scoring); `MA34` (writes a decay *prior
into* the contract — SC-1 *scores* priors already written); `MA13`/`M1` (the N counter's
integrity — SC-1 consumes N, never edits it); `MB33` (artifact–log drift, a freshness fact);
`X7RECON` (a one-cell diagnosis on banked draws — the class SC-1 generalises). No ledger row
has ever scored the expectation statements. The commission's own territory (a) names this as
virgin, and the check confirms it: `grep -l 'Brier' PREREG_*.md VALQUO_*.md CLAUDE.md` returns
nothing relevant.

**DATA.** Entirely the record itself: `RESEARCH_LOG.md` (214 trial rows at this reading),
`VALQUO_LEDGER.md` (289 rows), the 71 `PREREG_*.md`, the four audits' item priors, the scored
`Expectations` lines in `CLAUDE.md`/handoffs, and the banked per-draw artifacts under
`data/free_analysis/` (rule 9 is why the shrinkage arm is possible). **No market data is
touched, no panel is opened, no forward return is read** — every input is a sentence or a
banked summary the record already published. Census facts verified this session: 63/71
expectation sections, 36/71 numeric odds, 22 scored statements, 13 audit-#4 priors.

**PRICE.** 1 infra trial (the `R4` precedent: accounting over existing measurements searches no
new data, and charging it to equity would double-count the very trials it studies). Equity and
options counters untouched; no DSR/HLZ bar moves.

**POWER** (rule 11 form, arithmetic in the draft §5): with ~36–76 scoreable (prior, outcome)
pairs, the detectable Brier gap vs the base-rate forecaster at |t|≥2 is ≈0.10 at n=36 (50%
power; 0.14 at 80%) and ≈0.07 at n=76 — coarse, and stated before anyone runs. It resolves
"materially overconfident" vs "roughly calibrated"; it cannot resolve fine-grained bin shapes,
and the register says so. The shrinkage arm is distributional (bootstrap CI over trials) and
carries no bar.

**KILL CONDITION** (pre-outcome, MB15's pattern): stage-0 extraction is double-entered on a 20%
sample by two independent passes; if reader disagreement on the scoreable pairs exceeds 15%, or
fewer than 25 scoreable pairs exist, the calibration leg is **CANNOT-TELL by construction** and
only the descriptive extraction table ships (still useful, zero further cost). Post-outcome:
none needed — every branch (calibrated / overconfident / cannot-tell) is a deliverable.

**VERDICT GRAMMAR** (three states minimum): CALIBRATED / MISCALIBRATED (direction named) /
CANNOT-TELL. Plus one pre-committed *rule* consequence rather than a claim: if the shrinkage
median is below 0.5, future rule-11 power lines must state power against the *shrunk* effect
beside the raw one.

**PRIOR.** 80/20 the study returns an interpretable verdict. Directional expectation, written
now so it can be scored later: priors on "arm clears its own bar" were **overconfident** —
the realized clear-rate is far below the ~15–50% priors the audits wrote (odds ~70/30) — and
the shrinkage median lands in [0.3, 0.7] (odds ~60/40).

**Novelty check (web, this session):** the replication-forecasting literature scores *crowds*
predicting *other people's* studies (Dreber et al. PNAS 2015; Camerer et al. 2016/2018; Forsell
et al. 2019; PLOS ONE 2020 "Probabilistic forecasting of replication studies"). A single
project scoring its own per-trial pre-registered priors across ~550 adjudicated trials appears
to be unpublished territory. Citations in the draft.

→ Full register: **`PREREG_DRAFT_scout1_prior_calibration.md`**.

---

### SC-2 — S17's legend has been in the tree since 2026-08-03, and S17 closed ten days later saying it didn't exist — `PROPOSED` (zero-cost record correction + a conditional successor)

**Territory (c). Trials: 0 for the correction and the coverage read; 2, equity, ONLY if the
conditional successor's pre-outcome gate passes. Prior on the successor changing anything:
~12%.**

**THE FINDING (this session, verified against commits, not prose).** `S17` (equity, closed
2026-08-13) tested the EVENTS codes *by number*, recorded *"Sharadar ships no legend with the
EVENTS download and D10 records the docs were never extracted"*, and closed with **"DO NOT
RE-RUN WITHOUT THE LEGEND."** But `SHARADAR_REFERENCE.md` — committed **`47cb189`,
2026-08-03, ten days before S17 ran** — carries the complete 37-code EVENTCODES legend pulled
from `SHARADAR/INDICATORS?table=EVENTCODES`, in a section headed *"needed for S17"*. The
legend S17's closure demanded predates S17, in-tree, uncited by it. This is `C6`'s lesson
verbatim: *"'the only copy is on machine X' is a claim about where you looked."* (`CLAUDE.md`
references `SHARADAR_REFERENCE.md` zero times, which is presumably how it was missed.)

**What the legend changes, read off S17's own banked numbers at zero cost:**

1. **The arms get names.** S17's strongest arm — code **34**, annualized +3.2 to +4.9% over 328
   month-ends — is the **Schedule 13G filing** (passive >5% institutional ownership), not an
   8-K item at all; code 35 is the 13D. The two strongest arms being *ownership-disclosure*
   events, not corporate-news events, is interpretable for the first time.
2. **The era-concentration may be partly mechanical.** The legend's own coverage table shows
   codes **34 and 35 stop on 2024-12-17 and 2025-05-16** — the feed appears discontinued — so
   any 34/35 arm's late window has a dying input, which is `S18`'s coverage-bound class, not a
   market fact. S17's verdict was "era-concentrated rather than inert"; whether the
   concentration coincides with the input's death is decidable by reading banked coverage, no
   re-scoring.
3. **The record sentence "codes remain unlabelled" is now false** and should be amended by
   whichever lane owns S17's row (not this one), citing `SHARADAR_REFERENCE.md` §2 — the `MB5`
   pattern: one sentence, no re-run.

**NOT-A-COSTUME.** This *is* S17's own named re-open, carrying exactly the evidence the closure
demanded (the legend). It is not `MA33` (the monthly-panel rebuild, whose S19-buyback claim was
refuted — untouched here) and not a re-run of an unchanged design (the successor, if any, is
legend-informed: era boundary at the input's death date, arms named in advance).

**DATA.** `SHARADAR_REFERENCE.md` §2 (in-tree legend, 37 codes, per-code first/last dates);
S17's banked arm outputs; the EVENTS file already owned. Flags that bind: earnings code 22
exists only from 2004-08-23 (irrelevant on a 2009+ panel); codes 34/35 end mid-panel (the
point); `MIN_DATES`/rule-10 basis rules apply to any successor.

**PRICE.** Correction + coverage read: 0 trials (the `S25`/`OPT-REOPEN` read-only class).
Successor, only if gated in: 2 equity trials (234 → 236; hurdle 3.3031 → 3.3057).

**POWER.** The successor inherits S17's own cells (median cross-section 1,649 names, 328
month-ends full-sample) truncated at the input death date — the register must print effective
coverage per rule 10 and run `power_gate.state()` on the truncated window before charging; if
the truncated window's MDE exceeds the banked full-sample effect (+3.2–4.9%/yr for code 34),
the successor is UNPOWERED-BY-CONSTRUCTION and dies free.

**KILL CONDITION** (pre-outcome, decides the successor before any trial): read S17's banked
per-half coverage — if the era-concentration sits in the **early** half (pre-2021), the
discontinuation explanation is refuted and only the naming correction ships. Post-outcome for
the successor: S17's own bars travel unchanged.

**VERDICT GRAMMAR.** Correction: FIXED-class, no verdict. Successor: works / fails /
cannot-tell against S17's imported bars.

**PRIOR.** The correction is a certainty (the finding is verified). The successor changing any
verdict: ~12% — S17's arms failed both-halves for a reason that may survive the relabelling,
and 8-of-10 was never eight independent findings (five signals × two horizons, codes
correlated to 0.42).

---

### SC-4 — "The record this week": the honest-research changelog as a product surface — `EXECUTED 2026-08-19`

*(Shipped on `/work/research`. The kill condition was run first and passes; the exemption widening it required was measured rather than argued. Ledger row `SC-4`; `HANDOFF_appfixes.md` session 44.)*

*(Ranked above SC-3 on the zero-cost-items-rank-on-value rule.)*

**Territory (e). Trials: 0. Lane if routed: app-fixer (`valuation/web/`). Prior: ~75% it ships
without tripping the posture guard, because every element is an already-cleared class.**

**MECHANISM.** `MB38` shipped the denominator — N, the derived hurdle, the verdict word — and
established that `withhold()` passes counts, hurdles, and verdict words while refusing
performance figures. The record moves fast (this week alone: five MB items landed, options N
moved 300→305, the infra counter took MB22/MB23, one closure was found unsound); none of that
motion is visible anywhere except to someone who reads `CLAUDE.md`. A dated, machine-derived
"what changed this week" block — trials charged by domain, the hurdle each implies (before →
after), verdicts landed as verdict-words with register links, vintage events, floors newly DUE
per `MB31`'s map — is the denominator page made temporal. It is the one product surface whose
*content is the discipline itself*, which for this project's actual audience (Don + recruiters,
per `MB40`'s own reasoning) is the product. Internal dual use: it is also Don's Monday-morning
board.

**NOT-A-COSTUME.** `V4` (`/research`) lists registers, static; `MB38` states the denominator,
current-state; `MB27`/`board_state.py` is internal git-state, never shipped; `MB29` is prompt
receipts. No shipped or proposed surface renders the record's *diff over time*. Checked:
`grep -l 'changelog\|what changed this week' valuation/web/*.py PREREG_*.md VALQUO_*.md` — no
matches.

**DATA.** `research_log.detail()` (counts by domain, dated rows), `statistics.hlz_hurdle`
(imported, never re-derived — `MA5`), `VALQUO_LEDGER.md` verdict cells (via `build_ledger`'s
reader, not a second parser), `MB31`'s staleness-map script, vintage records
(`track_meter.VINTAGES`). All owned, all already machine-readable; no vendor rows anywhere near
the payload.

**PRICE.** 0 trials. ~1 session of the app-fixer lane.

**POWER.** n/a — no hypothesis, no threshold, no verdict (the `S28`/`MA29`/`MA30`
reporting-infrastructure class, and the copy must say so).

**KILL CONDITION** (inherited verbatim from `MB38`): if `withhold()` cannot pass a dated diff
of counts/hurdles/verdict-words without also passing a performance figure, **do not ship** —
and the banned-phrase test runs against the **rendered** payload (`MA28-CARD-UI`'s rule:
rendering is where copy leaks). One structural rule pinned by test: the page may state that a
verdict landed and the word; it may never state an effect size, a t, or a comparison — the
`MB26` two-denominators rule applies whenever a week contains items from both books, so every
count renders beside its own domain and hurdle.

**VERDICT GRAMMAR.** n/a (reporting only); the ship/no-ship gate is the kill condition above.

**PRIOR.** ~75% ships clean. The risk is copy drift under summarisation, which the rendered-
payload test exists to catch.

---

### SC-3 — TIER-E-FIN: the financing term structure, priced once, on the only long-tenor data this project will ever own — `PROPOSED`

**Territory (c) + the record's own named re-open. Trials: 2, options (305 → 307 reported;
hurdle 3.3824 → 3.3843). Prior: ~25% that any owned tenor beats Robinhood Gold's ≈rf+420bps;
~5% it beats IBKR Pro's ≈rf+150. The deliverable is the curve either way, and the curve closes
the tenor family permanently.**

**MECHANISM.** `DEEPITM-FIN` priced the deep-ITM call as leverage at the **worst-case tenor**
— its own register says so: at 60–90 DTE you roll ~4.9×/yr, so a ~53bps round trip becomes
~258bps/yr of the 702bps all-in. The frontier's §2c had already concluded the financing case
*"only becomes clearly positive at a tenor we do not own"* (730 DTE) — and `MB4` closed the
"financing improves with tenor" row **"as unownable"** because the cache stopped at 200 DTE.
**That premise is now false for 2016–2018:** Tier E landed 2026-08-18 (836/836 units, 331
symbols, 0 failed, 818/818 overlap-agree) with **14,278,981 rows beyond 200 DTE to a maximum
858 DTE** — rows in no other store, from a feed that no longer serves them. At ~794 DTE the
roll count is ~0.46×/yr: the roll term nearly vanishes and the question becomes whether the
embedded financing spread r*−rf (put–call parity at matched deep-ITM strikes, `DEEPITM-FIN`'s
own instrument) widens with tenor faster than the roll term shrinks. Nobody has ever measured
an r*−rf term structure on this data; the answer is a permanent number.

**NOT-A-COSTUME.** `DEEPITM-FIN` measured **one tenor bucket**; this measures the curve on a
disjoint tenor range with the same instrument — its register's own §2.2 names 730 DTE as the
untested case. It is not `MB2` (a **return** grid, recommended against — this is a **cost**
measurement and may make no return claim, `DEEPITM-FIN`'s scope note travelling verbatim). It
is not `P1S0`-family (no expression claim, no alpha, no book). The one authorised approach to a
closed door: `MB4`'s table closed the tenor row on ownability, and ownability is the thing that
changed.

**DATA.** Tier E freeze (`D:\thetadata\freeze_rawpull_2026-08-18`, hash-verified), 2016–2018,
331 symbols. **Flags that bind, all pre-named:** (1) `pre_panel_history` — 17 Tier-E units
over 12 symbols carry another company's chains (SNOW-2016 is Intrawest; SNDK, SN…) — the
harvest handoff's own precondition stands: *filter the flag or adjudicate the 26 symbols
first*; the register filters, and says the over-flag costs coverage. (2) As-traded strikes
(`U1-SPLIT`'s rule — parity arithmetic touches strikes). (3) `MA31`'s pair-availability
warning: matched deep-ITM-call/deep-OTM-put quotes thin out with tenor; effective n per bucket
is printed before anything is priced. (4) 2016–2018 is a near-zero-rf regime — both sides are
spreads over contemporaneous rf (`DEEPITM-FIN`'s convention), and the register still marks the
curve HISTORICAL: it prices the tenor *mechanism*, not today's card.

**PRICE.** 2 options trials (one per arm: the r*−rf term structure; the all-in cost/yr per
tenor bucket including spread at quoted width, ρ-adjusted beside it as `DEEPITM-FIN` did,
with ρ's 35-delta provenance re-declared an extrapolation).

**POWER.** Per-bucket effective n printed pre-outcome (rule-10 style); a bucket with fewer
than a pre-committed floor of usable matched pairs in either half is UNDERPOWERED, never null
(`O26`/`V6-B` M2 precedent). The statistic is a median cost with a bootstrap CI over
name-months — the MDE line comes from the banked `DEEPITM-FIN` dispersion and goes in the
register before the run.

**KILL CONDITION.** Pre-committed: if **no** tenor bucket's all-in cost sits below rf+420bps
(Gold) at the CI's favourable end, the tenor family closes **permanently** — no fifth tenor,
no re-cut — and `MB4`'s table gains its measured row. A bucket beating Gold but not IBKR
closes it too, with the sentence "broker choice dominates instrument choice." Only a bucket
beating **IBKR Pro** on the full CI would open a (new, separate) financing question, and the
register pre-commits that opening it costs its own future register.

**VERDICT GRAMMAR.** cheaper-than-Gold / not-cheaper / cannot-tell(bucket-underpowered), per
bucket, with the curve shipped regardless.

**PRIOR.** ~25% / ~5% as above. Written expectation to score later: the curve *falls* with
tenor (roll dominates) but bottoms above Gold because the parity spread widens and quoted
spreads at 730+ DTE in 2016–18 single names are brutal — the likely verdict is "financing
improves with tenor and execution eats it," which is itself the permanent answer.

---

## SEEDBED — the record's own named successors (§3b), tracked

Pre-vetted by the record; not all proposable today. Each entry names its instrument status.

* **MB15-SLIM — the condition+size retail proxy, post-Nov-2019 — `PARKED (UNPOWERED-BY-CONSTRUCTION at the standard design)`.**
  The kill that voided `MB15` named the successor exactly: gate = `single-leg auction OR
  (auto-execution AND size < 5)`, period ≥ Nov 2019, share target stated per period, union
  deliberately never computed (AST-pinned). The instrument now exists (legend obtained,
  marginals censused: cond-125 15.34%, cond-18 55.12%, size<5 76.01%). **But the power
  arithmetic parks it:** the post-2019 cache is ~2,446 of 3,884 units (~74 of 115 months;
  counted this session from `data/options_ticks`), so `MB16`'s banked SE 0.048 scales to
  ≈0.060 → 50%-power MDE ≈12pp, 80% ≈17pp per trade — **~2× the largest spread any of the six
  flow features has ever shown on this book (VPIN's 8.35pp), on a cache where all six are
  NULL and `R2` stands.** This is the S19/MA31-32/MA58/V6/U2 lesson; the commission's
  instruction for it is PARK, not propose. **Un-parking condition:** a design whose statistic
  isn't the O14-class monthly sort (none identified), or years more alert-days, or a future
  book whose entries this would gate (none exists — `MB16`'s own words).
* **MB1-SEL — the selection residual, re-registered with the statistic MB1 should have used —
  `SEEDBED (design sketched, power-gated)`.** `MB1`'s kill fired and its closure is recorded
  NOT SOUND on three measurements: the residual −1.28pp exceeds the register's own 1.0pp bar,
  same sign both halves, and the registered median was the one statistic `O17C4` had already
  shown blind to this book's mean-carried effects. Named re-open evidence exists (the row says
  "must NOT be read as having closed contract selection"). The successor: mean-based residual
  with the paired name-year cluster CI committed **in** the register, decomposition identity
  (`pick_gap = menu_gap + selection_residual`) as the primary object. **Gate before charging:**
  the early-half cluster CI spanned 29.6pp around a −0.73pp estimate — `power_gate.state()` on
  the banked leg dumps decides whether ANY statistic on this data can resolve a ~1.3pp
  residual; if not, it dies free. My read of the banked intervals says it likely dies —
  propose only the power computation (0 trials), then the register only on a pass.
* **O21-D2 / MB2's one-cell carve-out — `WAITING ON DON (audit #4 Q3)`.** The tail-for-
  typicality shape was consistent-with-mechanism and unpowered (CI95 [−12.3, +5.1]pp on the
  mean, n=113 pairs). Audit #4 already scoped the only honest follow-up: the 60–90 DTE ×
  0.85–0.95 delta cell alone, 1 trial, framed as `DEEPITM-FIN`'s return-side companion, with
  failure closing the tenor question. Not mine to re-propose — it is priced and on Don's desk
  as audit #4's question 3. SC-3 (cost side) is deliberately disjoint from it (no return claim).
* **The alternatives menu, third question — `SEEDBED (no question worth a trial identified
  yet)`.** Two questions asked (`O21-D2`, `MB1`). The menu's premise correction (fillable menu
  median FIVE, not 636) shrinks what a third question could see. Candidates considered and
  held: menu-level tail-vs-typicality by delta bucket (= MB2's grid in costume, refused);
  menu spread-structure census (descriptive, zero-trial, feeds any future register's fill
  model — worth a lane's afternoon, not a trial).
* **Tier E beyond SC-3 — `SEEDBED`.** The tenor axis also uniquely holds: term-structure shape
  of IV (front vs 400+ DTE) on 2016–18 single names (no consumer identified — `O16`/`O24`
  closed term_slope questions on the alert book; a new consumer must name itself first), and
  the LEAPS quote-quality census (descriptive input to SC-3, runs inside its register).
* **EVENTS beyond SC-2 — `SEEDBED`.** The legend's own hard boundary (code 22 exists only from
  2004-08-23; ten codes renumbered that day) is a pre-named era line for any future
  events-conditioned design; codes 36/61 occur zero times in 2.5M rows (build nothing on
  them). Carried so no future register re-derives it.

---

## KILLED-BY-ME — died at this desk, with reasons, so no successor re-derives them

* **Knockoff filters (Barber–Candès) / stability selection on the 53-signal cross-section.**
  Correct import, wrong patient. FDR-controlled variable selection over the signal set is the
  **weight/scheme family in costume** — five schemes plus the tree combiner (`MLCOMB`,
  REVERSED out of sample) closed it, and `X3` already measured the composite beating its best
  single signal. A knockoff pass that "selects" a subset is a re-weighting proposal with a
  new p-value dress. The one non-costume use (FDR over *future* candidate signals as a
  pre-filter) has no candidates queued — the S-backlog is deliberately parked. Re-visit only
  if a genuinely new signal family (post-MB18) creates a multi-candidate selection problem.
* **Survival analysis beyond Kaplan–Meier for holding tenure (Cox/AFT).** No decision it would
  change: `S22` measured tenure (KM median one rebalance), `S23` measured that no exit rule
  beats never-sell minus 10.89%/yr, `MA30` shipped tenure as a disclosure. A better tenure
  model with no consumer is `MA57`'s _KEEP lesson: add the instrument when the decision that
  needs it exists.
* **"Obtain the EVENTS legend from the vendor."** Killed by its own success: the legend is
  already in-tree (`SHARADAR_REFERENCE.md` §2, commit `47cb189`). Became SC-2, which is the
  *consequences* of that fact, not the acquisition.
* **Live-vs-panel drift as a research object.** The useful parts exist: `V2`/`V2F`/`V2G`
  measured the live gap and its cost, `THEME-RESTORE`/`FIDELITY-2` gated restoration on
  fidelity, `MB33` states the artifact-lag rule, `V6B-HEALTHGAP` did the live-reachability
  pass. What remains is monitoring, which is `MB28`'s scheduled task (routed to Don), not a
  study.
* **Regime/seasonality/orthogonality anything.** Not entered: `MB13` (34.2 years per side
  against 17.3), `MA58-SEAS`, and the 0-for-4 orthogonality record (`U2`, `MA31/32`, `MA58`,
  `MB16`) are standing walls, listed here so the next scout reads them as walls.

---

## PARKED — alive, with the un-parking condition named

* **Conformal prediction for fair-value bands (territory d).** Honest distribution-free
  intervals on the DCF fair values, validated on the S23 panel's banked errors. Parked on a
  **posture conflict**: `V3`/`V3-COPY` removed per-name precision language from the product,
  and a per-name interval is a per-name precision claim in band form. Un-parks only if Don
  wants bands *instead of* labels someday, with `V3`'s verdict quoted in the register.
  (Citation ready: Vovk et al.; Angelopoulos & Bates 2021 tutorial.)
* **S22's term structure replicated on JKP regions (new data, permitted class).** X8 proved
  the composite ports; S22's *shape* on 17 regions would be the first out-of-panel evidence
  either way. Parked behind `MB21`: measuring a term structure against the current
  mis-specified null inherits the exact defect MB21 exists to fix. Un-parks the session
  MB21's persistence-preserving null lands. Licence flag: JKP is CC BY-NC research-only —
  analysis yes, product never.
* **Storey π₀ / local-FDR over the archive's banked t-stats (genomics import, m≫n).** The
  "how many of our 550 nulls hide true effects" number. Parked inside SC-1 as a declared
  exploratory arm — the archive's t-stats are heterogeneous objects (different bars,
  clustering, books) and pooling them into one π₀ without that structure would be a number
  that misleads precisely because it looks rigorous. SC-1's extraction table is the
  prerequisite; a π₀ register may follow it.

---

## OUTCOMES RELAYED BY DON

*(empty — first session)*
