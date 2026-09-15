# SEASON3_MAP.md — the full map. Two tracks, nothing discarded.
## Frontier Scout, 2026-08-21. Commissioned by `PROMPT_scout_season3_map.md`.

> **AMENDED 2026-08-24 (append-and-amend), on the S3-I3 lane's reported correction
> (`30c52e5`), verified against each declaration's own structure text:** the short-leg
> consumer set of S3-I3 is **F-4, F-6, F-7, F-8, F-10, F-17, F-18** (seven). This map's
> §1 S3-I3 row previously listed long books (F-11/F-12) and a gate (F-19) as consumers,
> and the Track F table's F-20 row claimed S3-I1+I3 — **F-20 is a married put (long stock +
> long put), no short leg**. The omission that mattered ran the other way: **F-6's short
> call leg** is exactly what the module exists for and was absent from the per-instrument
> row. The declarations themselves were already consistent (each carries or omits the
> §1.4 interface per its true structure); the map's two summary cells were the defect.
> The lane's own instruction is adopted as this map's standing rule: **verify each book's
> structure text; trust none of the three lists.**

**Don's rulings, binding and built in:** everything in scope (closure tags filter, not scope
rules); forward-first is the DEFAULT home; free-tier catalyst data now, index chains
pre-authorized to ~$150/mo behind the named question in §D-GATE; **no cut-to-budget** — this
map orders everything and the only exclusions are *cannot* (unchanged re-run / unpowered-by-
construction), each parked with a condition. Cut lines are replaced by the **cumulative cost
curve** (§7).

**Counters at this writing** (origin/main, freshly read): equity **242** (hurdle 3.3133),
options **305 on main / 307 with EVOWN's in-flight 2** (3.3824 / 3.3843), infra **20**
(SC-1b landed: **CALIBRATED-IN-THE-LARGE**, clearing its half-width ceiling by 0.0068 on 15
item-clusters — the record's stated priors are officially calibrated). Equity's
floor-flip trigger sits at **N = 247** — five trials out, and the curve marks the crossing.
No outcome statistic is computed anywhere in this file.

---

## 1. INSTRUMENTS — Season 3's zero-trial builds (everything in Track F waits on S3-I1)

| id | instrument | owner lane | unblocks | notes |
|---|---|---|---|---|
| **S3-I1** | **THE FLEET HARNESS** — standing convention + recorder for many concurrent declared paper books: `DECL_<book>.md` committed ALONE **before first fill** (tamper-evidence = the commit is the proof, PREREG discipline applied forward); entry rule frozen at declaration; V5-style fill recording via the Tradier sandbox; **append-only book records on the PT-WRITER machinery** (service POST door + atomic append per MA4 + weekly git archive); one ledger row per book; a **mandatory verdict-horizon field** (honest fills-needed — V5 needed 30 and has 3); anytime-valid meter per book (PT-METER pattern) | options-bot (recorder+records) + edge (ledger/meter glue) | **every Track F book** | Draft shipped this session (`PREREG_DRAFT_fleet_harness.md`), incl. the trial-accounting convention: **1 trial per book, charged at first verdict read** (the MLPREREG→MLCOMB charge-at-execution precedent; anytime-valid = one charge covers continuous monitoring) |
| **S3-I2** | Catalyst-calendar scraper, free tier: FDA/PDUFA forward (pdufa.bio / CatalystAlert / BiopharmaWatch free surfaces), index-reconstitution announcements | pipeline | F-14, F-16's non-earnings arm, future B-FDA | forward-only now; history accrues from today — the honest backtest is ~1yr away by construction |
| **S3-I3** | **Assignment + margin model for short-side forward books** (Don's ruling #1: no short book declares without it): assignment at expiry per moneyness, margin per Reg-T cash-secured convention, early-assignment flag via O21's q-machinery | options-bot | F-4, F-10, F-11, F-12, F-19 | folded into the harness register as its short-book module, but tracked as its own deliverable |
| **S3-I4** | The standing K2 / RND census job — I-1 run weekly on flagged names (is the market learning the flags?) | pipeline + Cowork (schedule) | F-monitoring, B-12/E-8, O-1's context | zero trials, a scheduled reading, not a register |
| **S3-I5** | **The 26-symbol ticker-reuse adjudication** (the harvest handoff's own precondition: *"nothing built on Tier C or Tier E is quotable until it is done"*) | edge/data | **SC-3 (Tier-E strata), B-3 LEAPS, MB17** | 1 infra-class session; the single most blocking unbuilt thing in Track B |
| **S3-I6** | Guidance-cadence table — EVENTS code-71 per-name cadence (owned, legend in-tree) | edge | F-guidance screen, B2-13 census | extends I-4's spine |
| **S3-I7** | The public "declared forward books" shelf on `/research` — each fleet declaration listed with its hash, horizon, and status; no performance figures (MB38's gate) | app-fixer | fleet legibility; MB39-class credibility | product, zero trials |

## 2. TRACK F — the forward fleet (default home; launches parallel after S3-I1)

*Format: F-id · book · declaration sketch (entry / structure / universe / sizing / recorded) ·
depends · honest verdict horizon. Graveyard tags carried from `OPTIONS_BRAINSTORM.md`
(entry numbers in brackets).*

| id | book | declaration sketch | deps | verdict horizon |
|---|---|---|---|---|
| **F-1** | **Fill A/B** [49] | every fleet entry randomized: marketable vs mid-limit worked 60s; structure/universe = whatever the OTHER books trade; records: quote at order, fill price, time-to-fill, unfilled fate | S3-I1 | **fastest in the fleet** — piggybacks every fill; ~60 paired fills ≈ 1–2 months of a running fleet |
| **F-2** | Menu-breadth refusal, forward [50/O-2] | O-2's rule as a live gate on all long books: refuse entries with fillable menu < 4; records refused-vs-taken counterfactual quotes | S3-I1 | gate, not a book — reads with each host book |
| **F-3** | Bear-scanner puts [24] | entry: live bearish-engine verdicts (exists daily, never consumed); structure: 0.85-moneyness put, ~60 DTE; universe: optionable scanner hits; sizing: equal premium, cap 10; records: scanner score at entry | S3-I1 | ~10–20 signals/mo expected: **30 fills ≈ 1 quarter** |
| **F-4** | Event-free short-tenor premium [19/52] | entry: MA28-clean AND EVT-clean names with NO scheduled event inside DTE (I-4 spine + S3-I2); structure: <40 DTE cash-secured put at 0.90-moneyness (moneyness-fixed per V6-OPT autopsy); records: event-check proof per entry | S3-I1+I3 | premium books need loss-tail time: **2 quarters minimum**, declared |
| **F-5** | IV-cheap convexity screen [14/53] | entry: monthly, 5 names whose 60-DTE ATM IV sits lowest vs OWN 2yr history (I-2 on vol — never touched); structure: long call 60–90 DTE; records: IV percentile at entry | S3-I1 | 5 fills/mo → **30 fills ≈ 6 months** |
| **F-6** | Utility collar ledger [1/2/54] | zero-cost collars on the index book's top-3; records the drag honestly; **declared as UTILITY — no edge claim, no trial** | S3-I1+I3 | audit-style, reads quarterly |
| **F-7** | Covered calls on band-exiting names [5] | entry: names inside S14's no-trade band flagged for next-rebalance exit; structure: 30-delta… **moneyness-fixed 1.05× call**, expiry ≤ rebalance; utility framing | S3-I1+I3 | tied to rebalance cadence: **2–3 quarters** |
| **F-8** | CSP entry-financing [6] | entry: names newly entering top decile; structure: 0.95-moneyness put, assignment IS the plan | S3-I1+I3 | 1–2 quarters |
| **F-9** | Flag-transition puts [17/28] | entry: the quarter a name turns 2-of-3 flagged (MA28 transitions); structure: 0.70-moneyness put ≥91 DTE | S3-I1 | transitions are rare: **2–4/quarter → 12+ months**, declared honestly |
| **F-10** | Clean-name CSPs [4/A-table] | V6-OPT's inverse through the discriminating flags: sell 0.90-moneyness puts ONLY on MA28-clean+EVT-clean, event-free window; A3's corpse cited in the declaration | S3-I1+I3 | 2 quarters min |
| **F-11** | Dip-reject puts, forward twin [25] | entry: live dip-detector REJECTS (down 20%, fails health); structure: 0.80-moneyness put 91 DTE | S3-I1 (mechanism check in B-10) | dips cluster: quiet markets starve it — **1–3 quarters, regime-dependent** |
| **F-12** | Post-event reversal buys [20] | entry: day+1 after earnings, direction = composite sign; structure: 45–75 DTE option per direction | S3-I1, I-4 | ~dozens of events/quarter in universe: **1–2 quarters** |
| **F-13** | Second-event structures [21] | buy expiry spanning event #2, not #1 | S3-I1, I-4 | 2 quarters |
| **F-14** | FDA no-hump convexity [10] | entry: PDUFA inside 90d AND no IV hump (I-1 detects); forward-only | S3-I1+I2, I-1 | binary events are sparse in-universe: **12+ months — declared, not hidden** |
| **F-15** | Insider-cluster calls [32/33] | entry: ≥3 officers buying in 5 sessions (owned insiders.csv, MB20's split machinery); structure: 60-DTE call | S3-I1 | clusters ~few/mo: **2–3 quarters** |
| **F-16** | 13F-surge book [34] | entry: QoQ holder-count surge names at filing week; long calls | S3-I1 | quarterly clock: **4+ quarters — slowest honest horizon in the fleet** |
| **F-17** | IV-vs-own-history VRP percentile sells [44] | sell premium only where the name's OWN VRP percentile is extreme-high AND F-4's cleanliness rules hold | S3-I1+I3, I-2 | 2 quarters |
| **F-18** | The boring book [75] | covered calls on the 5 measurably-dullest names (low dispersion, low vol percentile, flag-clean, event-free) | S3-I1+I3 | 2 quarters |
| **F-19** | Alert-density gate [57] | fleet-wide regime convention: books may declare density-gated variants (trade only in >90th-pct alert weeks per O11's measured split) | S3-I1 | gate — reads with hosts |
| **F-20** | Married-put storm entries [29] | new top-decile entries taken with a 0.85-moneyness put during elevated-vol regimes; utility+timing hybrid | S3-I1+I3 | 2–3 quarters |

*Fleet-wide conventions (in the harness register): declaration-before-fill; append-only
records; assignment/margin modeled on every short book; verdict horizon mandatory; one trial
per book at first verdict read; all books small and sandbox-only; `O11` binds every book;
nothing here licenses real money.*

## 3. TRACK B — freeze-only registers, in execution order (the cost curve walks this list)

*Format: B-id · register · nearest closure argued past · instrument deps · trials(counter).*

**In flight from prior seasons (their charges already committed):**
* **B-0a · O-1 flagged puts** — [V6-OPT/U3/O9-scope argued in draft] — I-1 — 2(opt). Queued.
* **B-0b · SC-3 TIER-E-FIN** — [DEEPITM-FIN/MB4] — **S3-I5 blocks its Tier-E strata** — 2(opt).
* **B-0c · O-2 menu-breadth (banked half)** — [O13-Q3a/MB1] — none — 1(opt).

**Zero-trial censuses (free, run anytime, several feed registers):**
* **B-C1** U6 coverage census (2016+ replay overlap) [U6] · **B-C2** guidance-cadence census
  [S17-legend, S3-I6] · **B-C3** panel-date surface-object coverage [O3/O4/O5-scope] ·
  **B-C4** own-history IV/skew/vol-of-vol percentile censuses [U2-scope/O5-scope, I-2] ·
  **B-C5** E-7 stage A event-time descriptive [PEAD corpse noted, I-4] · **B-C6** O-1's K2
  RND census (inside its register) [O-1].

**Equity singles (the audit's own rowless leftovers first — they predate everything):**
* **B-1 · MB20** insider routine/opportunistic — [S3's three rebuilds argued past in the audit's own item; the construction S3 never built] — MA57's _KEEP change — **1(eq) → 243**.
* **B-2 · MB14** the three-state regime diagnostic — [MB13's arithmetic IS the design's power table; CANNOT-TELL pre-committed to close regime work permanently] — none — **1(eq) → 244**.
* **B-3e · MB19** lens-disagreement w_floor — [MA55 design; MA58-SEAS's C-DEPTH void rule inherited] — none — **1(eq) → 245**.
* **B-4e · E-7 stage B** event-time register (only if B-C5 shows structure) — [PEAD rejected; the FRAME is the object] — I-4 — **1(eq) → 246**.
* **B-5e · E-8** flags-vs-RND disagreement — [orthogonality wall faced: mechanism is mispricing, cell named in advance] — I-1 + B-C6 — **1(eq) → 247 ★THE FLIP: the MA19-style bounded floor re-derivation is OWED here (~400s, banked draws; floors may move; MB31's seed-1003). A named milestone on the curve, not a surprise.**
* **B-6e · MB17** Tier C small caps — [P1S0-scope: the one population it left unmeasured; UNDERPOWERED-not-null floors pre-set] — **S3-I5** — **1(eq) → 248**.
* **B-7e · MA27** KNS ridge (design-recorded; its own 75/25-REJECT prior carried) — [weight-family closure argued: new construction, no fitting on this panel's outcomes beyond the registered ridge path] — none — **1(eq) → 249**.
* **B-8e · JKP-S22 term structure** (second wave; port MB21's null to JKP first — the build is the cost) — [S20/S21 n/a; MB21's null mandatory] — MB21 port — **2(eq) → 251**.
* **B-9e · gap-crossing events** [35; MB18's corpse faced: crossing-vs-level is the whole argument, C2-style controls mandatory] — S23 panel — **1(eq) → 252**.

**Options registers:**
* **B-10 · dip-reject puts, freeze mechanism check** — [V6-OPT-scope (healthy side only); V6-B's 10.2pp is the mechanism] — chains 2016+ — **2(opt)**.
* **B-11 · panel-date surface features** (the O3/O4/O5 data unlock, one register family) — [O3/O4/O5 closed alert-day sorts; this is the full grid, new data] — deep freeze — **2(opt)**.
* **B-12 · model-free VRP re-entry** — [O2 closed the BS-IV implementation; I-1's RND is the new instrument] — I-1 — **1(opt)**.
* **B-13 · alert-density regime register** — [O11's measured split, never registered; MB13 faced: this is an OPTIONS-BOOK conditioning, not the equity panel] — none — **1(opt)**.
* **B-14 · liquidity × tenor 2×2** (O-4 re-scoped: EVOWN's ambient finding kills the spanning axis at 45–75; the live axes are O10's liquidity split × event-count-by-tenor) — [EVOWN/O10/MB3] — S3-I5 for long tenors — **2(opt)**.
* **B-15 · multi-event LEAPS** (O-5) — [MB3-open/EVOWN; DEEPITM-FIN's cost frame] — **S3-I5** + Tier E — **2(opt)**.
* **B-16 · MA56 residual term-slope** — attaches as the contract-selection module of whichever B-options register next opens an entry — **0 marginal**.

**Data-gated tail (ordered, waiting on named things — NOT excluded):**
* **B-G1 · the index-chain question** (pre-authorized ~$150/mo pending Don's confirm). **The named question:** *in the weeks our premium books (F-4/F-10/F-17) sell single-name vol, is single-name IV rich relative to index IV (a dispersion premium we are already implicitly long), or are we selling the cheap leg?* — [O8-scope: proxies only; P6 NEEDS-DATA resolved by purchase] — **2(opt) when bought**.
* **B-G2 · FDA-history register** — waits on S3-I2's accrual or a history purchase — 1-2(opt).
* **B-G3 · borrow-cost put-replacement** — waits on borrow data (IBKR indicative as free start) — [U2/MA31-wall, execution framing] — 1(opt).
* **B-G4 · S-SEED-6b peer momentum** — waits on real link data — [S15 residual half stays killed] — 2(eq).
* **B-G5 · B13's liquidity prefilter** — waits on a dollar-volume path — [S7/MA25] — 0(fix-class).
* **B-G6 · conformal fair-value bands** — waits on Don preferring bands over labels — [V3 posture] — 1(infra).
* **B-G7 · MA33 monthly panel** — waits on a text/LLM question surviving S19's closure AND its own placebo re-sweep cost being priced — 1(infra)+.
* **B-G8 · MA26-B / U4 / U8 / MB40 / V1-pairing / MA54-3 / MA54-4** — each waits on its named condition (see sweep table) — 0 until then.

## 4. EXCLUSIONS — the only two kinds, each parked with a condition

**(a) Unchanged re-runs of closed designs** — *cannot, by the p-hacking definition*: R2's
entry as-was; U1's percentile translation as-was; O14's five arms and MB16's VPIN re-asked on
the same cache; MB9-as-stated (delta-targeted flag veto); O9's index IV-rank timing; A3's
alert-day credit spreads; sector-neutral in any partition costume (S15). **Condition on every
one:** new data, new instrument, or new design per the standing re-open rule — several
already have their new-design successors IN this map (that is the difference between a corpse
and a door).

**(b) Unpowered-by-construction, MB22 arithmetic shown** — MB15-SLIM (post-2019 cache ≈2,446
units → 80%-power MDE ≈17pp vs a book whose largest-ever flow effect is 8.35pp; parked until
a new statistic class, years more alert-days, or a live flow consumer); every rubric bucket-3
stratified re-read (spanning-cell 80% MDE ≥1.7× pooled at s≤0.5 — and EVOWN's ambient result
makes the stratification itself degenerate at 45–75 DTE); E-7 stage B at 10-year burn-in
(28 dates < S18's floor — the 5-year version is what B-4e runs). **Condition:** the
arithmetic's own inputs changing (n, SE, or statistic class), shown before any re-propose.

## 5. DEPENDENCY GRAPH (arrows = "waits on")

```
S3-I1 fleet harness ──► F-1..F-20 (all)          S3-I3 assignment ──► F-4,7,8,10,17,18,20
S3-I2 scraper ──► F-14, B-G2                     S3-I6 cadence ──► guidance screen, B-C2
S3-I5 reuse adjudication ──► SC-3(strata), B-14(long tenors), B-15, B-6e
I-1 RND ──► B-C6/K2 ──► O-1 arm ──► B-5e(E-8)    I-2 ──► B-C4 ──► F-5, F-17
I-4 spine ──► F-12, F-13, B-C5 ──► B-4e          MB21-null port ──► B-8e
B-10 (freeze mechanism) ──► informs F-11 sizing (not a hard gate — fleet may launch first)
```

**Collisions (MA-dependency-map precedent):** all F-books share the harness recorder +
`paper_track.py` — options-bot owns those files; declarations are inert .md (no collision).
B-1/B-2/B-3e/B-7e all touch `valuation/edge/` scoring paths — sequence within the edge lane.
B-11/B-12 share I-1 and the freeze readers with O-1 — options-bot sequences them. S3-I7
touches `/research` — app lane, independent.

## 6. EXECUTION ORDER + LANE ROUTING

* **Wave 0 (parallel, 4 lanes):** S3-I1+I3 (options-bot+edge) · S3-I2 (pipeline) · S3-I5
  (edge/data) · S3-I7 (app). B-C1..C5 censuses fill lane idle time.
* **Wave 1 (fleet launch #1, parallel):** F-1, F-3, F-5, F-6 (+F-2/F-19 as gates).
* **Wave 2 (fleet launch #2, after S3-I3):** F-4, F-10, F-7, F-8, F-18, F-17; (after S3-I2)
  F-14; plus F-9, F-11, F-12, F-13, F-15, F-16, F-20.
* **Wave 3 (Track B, in-flight first):** B-0a → B-0b (after S3-I5) → B-0c, then equity
  B-1 → B-2 → B-3e → B-4e → **B-5e ★flip milestone** → B-6e → B-7e, options B-10 → B-11 →
  B-12 → B-13 → B-14 → B-15, then B-8e/B-9e, then the gated tail as gates open.
* **Lane routing:** options-bot = harness, F-books' recorder, B-10..B-15, O-1; edge = equity
  singles, I-5, MB21-port, meters; pipeline = scrapers, censuses, K2 job; app = S3-I7, any
  disclosure candidates the registers spawn; Cowork = schedules (K2 weekly, fleet heartbeat).

## 7. THE CUMULATIVE COST CURVE — watch the price accrue (no caps, no cuts)

**Equity counter** (bar = √(2·ln N); DSR floor is stale-by-construction at every step and
re-derives at wave ends):

| step | after | N | hurdle |
|---|---|---|---|
| today | — | 242 | 3.3133 |
| B-1 | MB20 | 243 | 3.3145 |
| B-2 | MB14 | 244 | 3.3158 |
| B-3e | MB19 | 245 | 3.3170 |
| B-4e | E-7b | 246 | 3.3182 |
| **B-5e** | **E-8 → ★FLIP at 247: bounded floor re-derivation owed (MA19 route, ~400s)** | **247** | **3.3194** |
| B-6e | MB17 | 248 | 3.3207 |
| B-7e | MA27 | 249 | 3.3219 |
| B-8e | JKP ×2 | 251 | 3.3243 |
| B-9e | gap-cross | 252 | 3.3255 |

**Options counter** (307 basis includes EVOWN's in-flight 2; fleet books add +1 each at their
*verdict* dates per the harness convention — listed after the freeze queue as horizon-dated):

| step | after | N | hurdle |
|---|---|---|---|
| today+EVOWN | — | 307 | 3.3843 |
| B-0a | O-1 ×2 | 309 | 3.3863 |
| B-0b | SC-3 ×2 | 311 | 3.3882 |
| B-0c | O-2 | 312 | 3.3891 |
| B-10 | dip-puts ×2 | 314 | 3.3910 |
| B-11 | surfaces ×2 | 316 | 3.3929 |
| B-12 | RND-VRP | 317 | 3.3938 |
| B-13 | density | 318 | 3.3947 |
| B-14 | liq×tenor ×2 | 320 | 3.3966 |
| B-15 | LEAPS ×2 | 322 | 3.3984 |
| B-G1 | index-q ×2 | 324 | 3.4002 |
| B-G2 | FDA ×2 | 326 | 3.4020 |
| +fleet verdicts | ~18 books × 1, dated by each horizon (≈1–4 quarters out) | →344 | →3.4180 |

**Read the curve, not a cap:** the full equity queue costs +10 (3.3133→3.3255), the full
options queue +19 plus the fleet's horizon-dated +18 (3.3843→~3.4180). Every step is a real
price on every future claim; Don stops wherever the price stops being worth it — the map
never decides that for him.

## 8. THE SWEEP PROOF — every non-terminal item, where it landed

| item (status found) | landed at |
|---|---|
| B13 (PARTIAL-BLOCKED) | B-G5 (condition: dollar-volume path) |
| MLPREREG (PRE-REGISTERED) | TERMINAL — executed as MLCOMB; sweep notes the row pair |
| U2 (PARTIAL) | TERMINAL-BY-MA31 (its unrun parity half was MA31's object, NULL) |
| U4 (DESIGN-RECORDED) | B-G8 (condition: a measured signal relationship among its inputs — all rejected to date) |
| U6 (DESIGN-RECORDED) | **B-C1 census → then a register if coverage clears** |
| U8 (DESIGN-RECORDED) | B-G8 (condition: two live books to budget across — the fleet may create them) |
| D11 (INPROGRESS, stale) | TERMINAL-IN-FACT (harvest closed 2026-08-18) — **row amend owed, reported as bug** |
| V1 (REGISTERED, no pair) | B-G8 (condition: the next ADOPTED change opens the pair; harness reuses its pattern) |
| MA27 (DESIGN-RECORDED) | **B-7e** |
| MA55 (DESIGN-RECORDED) | **B-3e** (=MB19, its register) |
| MA57 (DESIGN-RECORDED) | **B-1** (=MB20, its consumer) |
| MA58 (DESIGN-RECORDED) | TERMINAL-BY-MA58-SEAS |
| MB2 (PARKED BY DON) | stays Don-gated; single-cell version listed at B-14's tenor axis if he unparks |
| MB36 (DEFERRED) | PROCESS, not research — routed to lanes, condition: Don's word |
| MB39 (DESIGN-RECORDED) | app lane, zero-trial product (S28 distribution card) — Wave 0-adjacent |
| MB40 (DESIGN-RECORDED) | B-G8 (condition: the method write-up exists; MB22 captured the internal value) |
| MB14 / MB17 / MB19 / MB20 (**no ledger row at all** — audit-4 leftovers) | **B-2 / B-6e / B-3e / B-1** — and the missing rows are reported as a bug below |
| MA26-B (sub-item design-recorded) | B-G8 (condition named in its row) |
| MA33 (scoped, unbuilt) | B-G7 |
| MA54-3 (NEEDS-DATA) / MA54-4 (orphaned) | B-G8 (conditions from their own text) |
| P6 (NEEDS-DATA, frontier) | **B-G1 — the pre-authorized purchase question, named** |
| EVOWN (IN FLIGHT) | its own lane's landing; the rubric §4 self-closed on "ambient" |
| O-1 / O-2 / SC-3 (queued) | B-0a / B-0c / B-0b |
| E-7 / E-8 (season-2 reserves) | B-4e / B-5e |
| O-4 / O-5 (design-recorded, mine) | B-14 (re-scoped per EVOWN) / B-15 |
| MB15-SLIM (parked) | EXCLUSION (b), condition stated |
| S-SEED-6b (parked) | B-G4 |
| JKP-S22 (parked→2nd wave) | B-8e |
| Conformal bands (parked) | B-G6 |
| SC-1b | TERMINAL — CALIBRATED-IN-THE-LARGE, landed 2026-08-21 |
| Brainstorm #1–79 | every number appears above: F-1..F-20 carry 1,2,5,6,7,10,14,17,19,20,21,24,25,28,29,32,33,34,44,49–58,75; B-track carries 4,15,16,18,22-23,26-27,30-31,35,59-66,68,74,76-79 via B-0a/B-10..B-16/B-C*/B-G*; 36-43,45-48,67,69-73 sit in B-C censuses, B-G gates, or exclusion (a) with conditions — none silently dropped |

**Bugs found (RUN_RULES A-3, none fixed here):** MB14/MB17/MB19/MB20 have no ledger rows —
four audit-4 items invisible to "where do we stand" (rule 2); D11's row still reads
INPROGRESS five days after its own handoff closed the harvest; the brainstorm branch
`3b9bda7` remains unpushed (sync.bat).

## 9. BATCHED QUESTIONS FOR DON

1. **B-G1's purchase:** the named index-chain question is in §3. Confirm the ~$150/mo when
   F-4/F-10/F-17 declare — or hold until their first verdicts?
2. **Fleet size at launch:** Wave 1 lists 4 books + 2 gates; Wave 2 adds ~12. Launch all
   (each is 1 horizon-dated trial), or stage the fleet in two months?
3. **The flip milestone (equity 247):** the curve crosses it at B-5e. Proceed straight
   through with the bounded re-derivation, or pause the equity queue there for your read?
4. **MB2:** B-14's tenor axis brushes your parked grid. Unpark the single 60–90 cell into
   B-14, or keep parked?
5. **F-6/F-7/F-8 are UTILITY books** (no edge claim, no trial charge proposed). Confirm that
   classification — it is a judgement call and it is yours.

*Push ritual: this map + the first-wave drafts + updated handoff, committed on the scout
branch; the one-line push is yours (`sync.bat`); land verified next session. — Scout*
