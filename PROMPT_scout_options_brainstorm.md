# COMMISSION — SCOUT DIVERGENT SESSION: the options brainstorm. Breadth, not depth.

Don's brief, verbatim in spirit: *"I refuse to not find an options edge. Make a massive list of
everything that could work — including things we tried and killed that have hope we glossed
over. No execution design. Raw brainstorming."*

This is a DIVERGENT session and its rules differ from your normal mode. **Suspended for this
session:** the full quality bar (no per-idea register design, no kill conditions, no MDE lines,
no trial pricing). **Not suspended, ever:** (1) you compute NO outcome statistic on market data
— an idea list that peeked at returns is a pile of unregistered trials; (2) every idea carries a
one-line GRAVEYARD TAG naming its nearest dead ledger row, or the tag `VIRGIN` — without tags
the list is costumes all the way down and worth nothing. Descriptive facts (coverage, counts,
what data exists) remain allowed and useful.

You own a NEW file for this: `OPTIONS_BRAINSTORM.md`. Target: **the largest honest list you can
produce** — a hundred entries beats thirty, but a tagged fifty beats an untagged five hundred.
Format per entry: one to three lines — the idea, the mechanism in a phrase, the data it needs
(exists / needs collection / impossible), the graveyard tag. Group into the sections below, add
sections I did not think of, and end with your BATCHED shortlist: the 10 entries you would
develop first if Don says go, ranked, with one sentence each on why.

## Section A — THE RE-GLOSS PASS: every kill, re-read for what its closure did NOT cover

Walk EVERY options-family kill in the ledger and ask two questions: what exactly did the closure
close, and what adjacent thing looks closed but was never tested? Known examples to seed you —
verify each and find the rest:

- **V6-OPT** killed CSPs on healthy dips because the HEALTH floors did not discriminate. MA28's
  accounting flags DO discriminate (3.04x, 5/5 quintiles) — selling puts on UNFLAGGED names was
  never tested. Does the closure's own reasoning reopen the inverse?
- **U6** (covered calls / CSP book) was blocked on 1.81% chain coverage of decile names. The
  harvest since added Tier C/D/E — 435 more names, holding-period chains at 99.9%. Is the
  coverage blocker still true? Measure the coverage fact (allowed), report whether the blocker
  dissolved.
- **O7** found earnings options RICH (implied 5.45% vs realized 4.78%). That is itself a signal
  — for the SELLING side. What exactly did O9/A3 close: short vol as a family, or the specific
  constructions tried? Read the closures' own scope lines and say which.
- **EVOWN** just found event ownership is AMBIENT at 45-75 DTE. Inverted: SHORT-dated contracts
  (under ~40 DTE) are the only ones that can NOT own an event — is there any question that
  lives specifically in the event-free short tenor?
- **O25** killed wing-SELLING after a win. Wing-BUYING, collars, and defined-risk conversions
  were never arms.
- **MB2/the grid** is parked, not dead — and Don's original single-cell version (60-90 DTE,
  one pre-named cell, 1 trial) was the auditor's own suggested alternative.
- Continue through EVERY closed row: O1..O26, U-series, A3, P1S0, DEEPITM-FIN, MB-options,
  EVOWN. The deliverable is the complete table: closure | what it actually closed | adjacent
  untested thing | worth a second look YES/NO and why.

## Section B — DON'S FOUR DIRECTIONS, taken seriously

1. **Leveraging high-conviction Valquo names.** U1/P1S0 closed score→calls translation. What
   survives: options as EXPRESSION on names you already hold for other reasons (collars around
   the index book, protective puts on concentrated positions, stock-replacement where the
   financing math works at YOUR margin rate per DEEPITM-FIN's cards). Not alpha — utility.
   List every utility-shaped idea; tag which need no edge at all to be worth having.
2. **"About to explode."** The market overprices known explosions (O7). So the honest versions
   are: explosions the market does NOT have on its calendar (non-earnings catalysts: FDA dates,
   litigation, index adds, guidance patterns — what data would each need?), or being LONG the
   overpricing (selling the crush — scope per Section A), or finding names where implied moves
   are LOW vs the name's own realized history (the inverse screen — cheap convexity rather
   than predicted explosions).
3. **Puts.** O-1 is queued. Beyond it: puts as the bear-scanner's expression (the bearish
   signal engine EXISTS in the live product and has never had an options arm), puts on
   dip-detector REJECTS (names down big that fail the health screen — V6-B measured they fall
   further), index-proxy puts as book insurance done at the right price (U3 killed the CALL
   overlay; a put overlay priced off the RND builder was never an arm).
4. **Completely different signal classes.** Nothing exogenous has ever fed the options book.
   Brainstorm freely: insider-cluster events, 13F breadth surges, MA28 flag TRANSITIONS (the
   moment a name becomes flagged), the S23 panel's fair-value gap crossings, seasonality of IV
   (OpEx cycles, month-end, index rebalance dates — never touched), dividend-capture-adjacent
   structures, share-count events (buyback announcements/splits), the tick cache's condition
   codes (MB15's named successor axis), TIDEMARK-class own-history percentiles applied to IV
   (is this name's vol cheap vs ITS OWN history — I-2 exists and has never touched vol).

## Section C — THE FORWARD-FIRST CLASS: strategies that need no backtest

The frozen panel is converged — 307 trials say so. But the project owns a LIVE paper apparatus
(Tradier sandbox, V5's fill recorder, the daily scan) that can test FORWARD at near-zero cost,
where the multiple-testing debt is tiny because hypotheses are declared before data exists.
List every idea whose honest home is a forward paper book rather than a backtest: live IV-cheap
screens, live menu-breadth-filtered entries (O-2's rule run forward), the utility structures
from B1 papered live, short-tenor event-free constructions. For each: what the live apparatus
would need that it lacks today (descriptive, allowed).

## Section D — DATA WE DO NOT OWN, priced as questions

What signal classes would need new data, what data, roughly what it costs, and what single
question would justify it. (The D-series bought nothing for good reasons — the bar is a named
question, not a wish. But list them: index options for dispersion/VRP, higher-frequency
surfaces, borrow rates, catalyst calendars, 13F intra-quarter feeds.)

## Section E — WILDCARDS

Anything that fits nowhere: cross-asset (VIX-complex-adjacent constructions from owned equity
data), structure zoo entries never named in any register (calendars-of-strikes, ratio spreads,
risk reversals), options ON the paper book's own rebalance dates, selling covered calls only in
the composite's measured-dead windows. No filter except the graveyard tag and no-outcomes rule.

## Discipline for this session, in one line each

Read the ledger's options rows FIRST so the tags are real. Web search freely for signal classes
and catalyst-data sources — cite, mark replication status where known. No outcome statistics,
no execution design, no register drafts — breadth is the deliverable. End with the ranked
top-10 shortlist, your one-paragraph honest read of where an options edge most plausibly hides
given everything, the batched questions for Don, and the push ritual: add, commit, push
`OPTIONS_BRAINSTORM.md` + updated `HANDOFF_scout.md`, verify the land.
