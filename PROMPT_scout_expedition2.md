# COMMISSION — SCOUT EXPEDITION 2: new statistics, new objects, the deep scrub

You are the Frontier Scout, and this is your second, much larger commission. Don's brief,
verbatim in spirit: *turn the options and stocks logic into something we haven't even touched.
Full creativity. Make our own statistics. Push past everything, including past this prompt.*

Your charter (`PROMPT_frontier_scout.md`) still binds every word of this: **you run no tests,
charge no trials, compute no outcome statistic on market data.** Full creativity in DESIGN, full
discipline in TESTING — that combination is the only reason anything this project finds is real.
Descriptive censuses (coverage, counts, spans, input-correlations) remain allowed and are your
instrument. You own `IDEAS_LEDGER.md`, `PREREG_DRAFT_*.md`, `HANDOFF_scout.md` — and this time
**you end the session with `git add`/`commit`/`push` of your own files and verify the land**;
batch 1 sat unpushed until Don rescued it.

Before anything: re-read the newest `CLAUDE.md` bullets and `git log` since your last handoff.
MB18 landed (REJECTED — which un-defers your S23-trajectory entry), MB1-SEL voided MB1's
selection reading, the event-ownership register is IN FLIGHT with options bot, and SC-1/SC-2/
SC-3/SC-4 are routed. Re-read counters fresh; every price below assumes them stale.

---

## PART 1 — SEEDS. Beat these, kill these, or build past these.

These are hypotheses I (the manager) am handing you with their nearest graveyard neighbours
already named. They are a floor, not a ceiling: your charter §2 quality bar applies to every one
(mechanism, NOT-A-COSTUME with row citations, data, price, MB22 power line at both 50% and 80%,
kill condition, prior, verdict grammar). Kill any of them with reasons and it counts as work.

### Stocks — objects the panel has never contained

**S-SEED-1: The conviction statistic — theme DISPERSION per name.** The composite is a weighted
MEAN of theme z-scores; the VARIANCE across themes for a given name has never been an object.
Does a name all seven themes agree on behave differently from one with the same mean and huge
disagreement? Mechanism: consensus vs contested information. Neighbours to argue past: MA55
(lens-disagreement — the valuation-engine cousin, design-recorded), the weighting family
(REJECTED — but this is a NEW COLUMN, not a re-weighting). Gate: incremental-IC under MB7's
repaired specification, with effective-date coverage printed.

**S-SEED-2: The TIDEMARK transform — every signal vs its OWN history.** The entire panel is
cross-sectional: AAPL is cheap vs the market, never vs AAPL. TIDEMARK's expanding-percentile
engine (no look-ahead, burn-in, publication lag — all solved problems with tests) applied at
name level gives a temporal axis the panel has literally never had. Neighbours: S20/S21 (rank
and winsor as REPLACEMENT standardisers — rejected; this is an ADDITIONAL axis, not a swap),
MB24 (this is METHOD flowing from TIDEMARK, which is licensed — no TIDEMARK data crosses).
Burn-in arithmetic is the likely killer: state what fraction of the panel survives a 10-year
name-level burn-in before pricing anything.

**S-SEED-3: Fundamental momentum — Δcomposite.** Has the CHANGE in a name's composite score
ever been tested as a signal? I believe not — verify. A name whose score is improving vs one
whose level is high. Neighbours: the momentum theme (price momentum — different object), PEAD
(earnings surprise — different object). Cheap: one derived column on the existing panel.

**S-SEED-4: The graveyard votes — one combined statistic across all rejected signals.** 53
signals exist; most are individually null/rejected. ONE pre-registered combination (Stouffer
across per-signal ICs, published-sign-oriented, weights fixed in advance) asks: is there diffuse
information the per-signal bars could not see? ONE trial, ONE number, no fitting. Neighbours:
MLCOMB (REVERSED — but that FIT a combiner; this fixes everything in advance), the flat
composite itself (7 themes — this is all-53 with no theme structure). If it clears, it does NOT
license mining WHICH signals carried it — that would be the next register and you say so.

**S-SEED-5: Market-based tail flags beside the accounting card.** MA28's crash card is
accounting-based and gated on CRASH RATE, never alpha — a gate style now proven. An EVT tail
statistic (e.g., Hill index on daily returns) or option-implied left tail as a SECOND crash
flag: does it discriminate crashes the accounting flags miss, on the same crash-count gate?
Neighbours: neg_idio_vol/MAX (tested for RETURNS, null — this is tested for CRASH RATES, a
different verdict object), V6-B (survival machinery exists and is reusable).

**S-SEED-6: Peer residuals without sectors.** Sector data is look-ahead-poisoned (S25) — but
fundamental-similarity peers (nearest neighbours in the 53-signal space, point-in-time) are
computable from owned data. A name's return vs its peers' as a residual object; peer-group
lead-lag. Neighbours: sector-neutral (REJECTED twice — that was TODAY'S sectors; this is PIT
similarity, a different partition and the register must prove it differs, e.g. overlap stats
vs the sector map). Expensive to build; price it honestly.

### Options — the untested half of the book

**O-SEED-1 (the star): LONG PUTS have never been tested. The entire O-series book is 100%
calls.** Verify that claim first — it is load-bearing. The cache holds 1.29M puts; Tier C/D/E
are frozen; MA28's flags discriminate crashes at 3x, 5-of-5 size quintiles. "Buy puts on
2-of-3-flagged names" is mechanism-backed (the flag predicts the crash the put pays on),
data-ready, and untouched. Neighbours to argue past, and they are serious: A3/O9 (short-vol —
this is LONG vol, opposite side), U3 (the overlay was leverage-not-insurance — that was INDEX-
level calls on the whole book; this is single-name puts on FLAGGED names), V6-OPT (SOLD puts on
healthy dips, killed because health floors did not discriminate — MA28's flags DO, 5/5). The
kill that must run FIRST, pre-outcome: do option prices already know? Build the risk-neutral
left tail from the frozen chains (Breeden-Litzenberger on the alternatives menu — an INSTRUMENT,
see Part 3) and check whether flagged names' tails are already priced fatter. If the market
prices the flag, the edge is dead before an arm runs and you will have saved the trials.

**O-SEED-2: The 2×2 nobody crossed — spanning × liquidity.** MB3 split the book by earnings-
spanning (terminal wealth $130,855 vs $24,391); O10 split it by chain liquidity (+5.82% vs
−3.11% expectancy). The CROSS has never been measured. Four cells, one register, and the
spanning×liquid cell is plausibly where every prior pooled verdict was diluted. Depends on the
EO register in flight — file with the dependency named (Don's standing preference).

**O-SEED-3: Menu breadth as a refusal rule.** O10's liquidity split and O13's
entry_spread_pct q5 (−7.41%) both point at one un-registered rule: refuse entries whose MENU
(not whose contract) is tape-thin. The alternatives freeze makes menu-level liquidity a
computable pre-trade fact. Neighbours: O13 (its Q3a prior discourages single-feature refusal
rules — cite it and say why menu-level differs from contract-level).

**O-SEED-4: Multi-event LEAPS.** Tier E owns tenor to 858 DTE for 2016–18. If event ownership
confirms, a long-dated call spans MULTIPLE earnings — does the effect compound, or does theta
between events eat it? Purely dependent on the EO register; design it now, file with dependency.

**O-SEED-5: Calendar structure around events.** Long back-month / short front-month into
announcements monetises the crush differential. It must argue past the short-vol closure (O9)
since the front leg is short vol — the honest framing is net-vega-positive with a defined-risk
structure, and if you cannot separate it from the closed family, kill it yourself.

### Cross-cutting

**X-SEED-1: The market-vs-accounting mispricing test.** Where MA28's flags and the option-
implied tail DISAGREE (flagged but tails priced thin; clean but tails priced fat) is a
mispricing object bridging both books. This is the "combine to amplify" Don asked for, with a
mechanism rather than a hope. Builds on O-SEED-1's instrument.

**X-SEED-2: Event-time as a coordinate system.** Re-index panel returns to days-since-earnings
rather than calendar. PEAD exists as a signal; event-time RESTRUCTURING as the analysis frame
is new. Descriptive first (zero trials): what does the composite's IC look like in event-time?
If structure appears, the register follows.

## PART 2 — THE BLIND TASK, do this FIRST while you are still uncontaminated

**Draft the event-ownership re-open rubric NOW, before the EO register lands.** If EO confirms,
every prior options verdict pooled across spanning/non-spanning becomes a candidate for
stratified re-reading — and a re-open list written after the stratified numbers exist is a list
of results someone liked. You have not seen any stratified number (none exists). Classify every
options-book verdict: EO-SENSITIVE (mechanism for interaction, e.g. exits O1/O23/O25, sizing
O12/O26, flow O14/MB16) / EO-INSENSITIVE (R2 already survived within-stratum via O17C4 — cite
it as the template) / UNPOWERED-IF-STRATIFIED (state the MB22 arithmetic: stratification halves
n). File as `PREREG_DRAFT_eo_reopen_rubric.md`. If EO comes back null, the rubric costs nothing
and closes itself.

## PART 3 — INSTRUMENTS: zero-trial builds that many registers reuse

Propose (not build) the shared instruments the seeds above need, each as an infra item with an
owner lane: the **RND builder** (Breeden-Litzenberger from frozen chains — feeds O-SEED-1,
X-SEED-1, and any future tail question), the **name-level percentile engine** (TIDEMARK's port —
feeds S-SEED-2), the **crash-count gate generalised** (MA28's verdict machinery as a library so
every crash-flag register reuses one implementation — B7's lesson), the **peer-similarity
index** (feeds S-SEED-6). An instrument built once and reused is how this project's costs stay
sane; say which registers each unblocks.

## PART 4 — SEASON 2: the deliverable that makes this an expedition

End with a **season plan for Don to approve as a block**: your full ranked portfolio (seeds
above, your own inventions beyond them, and survivors from batch 1), with — per entry — trials
and counter, MDE at both powers, dependencies, and lane routing; a **proposed total trial
budget for the season** (state what it does to both hurdles and the DSR bar at the new N);
the recommended execution ORDER (instruments first, dependents after their gates); and the
**top 3–5 as full PREREG drafts**, executor-ready. EV-rank ruthlessly: a season is not a
backlog, it is the best 10–20 trials the record can currently justify. Expect Don to cut it;
give him the cut lines (what drops first and why).

## Discipline, renewed once

Graveyard first — nothing leaves your desk without its nearest dead neighbours cited by row.
Web search expected: every seed gets a literature check with replication status (the project
has killed published results before — treat literature as hypotheses). No outcome statistics.
Descriptive censuses labelled as such. Both power numbers on every line (MB22's correction:
historical "MDEs" here are 50%-power figures; quote 80% too). File ideas with dependencies
named rather than holding them (Don's standing rule). Kill your own seeds freely — including
mine; a reasoned kill of a manager's seed is worth more than a polite pass. Batch questions
for Don at the end. Push your files and verify the land before saying done.
