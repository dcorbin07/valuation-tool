# COMMISSION — Master audit #4: the frontier audit. Where does anything new live?

You are a cold auditor with no history in this codebase — that is your entire value. Work in
`C:\Users\donni\Downloads\valuation-tool`. **STRICTLY READ-ONLY**: change nothing, fix nothing,
run no backtest, adopt nothing, charge zero trials. Your outputs are the three deliverable files
at the end and nothing else.

**DO NOT START unless the board is quiet:** `VALQUO_LEDGER.md` shows no IN PROGRESS rows and no
lane is mid-session on any `origin/worktree-*` branch. Auditing a moving target voids the audit
(item O16). If the board is not quiet, say so and stop.

## What makes this audit different from its three predecessors

Audit #1 read the backtest and found it broken in places. Audit #2 read the live product. Audit
#3 read everything and closed 60/60. **You inherit all three executed** — do not re-produce a
single finding from them. Your commission is the question the project has earned after ~250
equity trials, 297 options trials, and one adoption: **given that the ground is thoroughly
mapped, where is there genuinely NEW ground — and what would it cost to walk it?**

The bar for this audit is higher than "find problems." Problems have been found, adjudicated,
and closed. Your deliverable is a ranked frontier: hypotheses, combinations, instruments and
designs that are (a) new to this project, (b) mechanistically motivated, (c) priced in trials,
and (d) equipped with a kill condition. **An idea without a kill condition is not a proposal.**

## Read first, in this order

1. `VALQUO_LEDGER.md` — ~271 rows, the contractual record. Nothing else counts as "done."
2. `CLAUDE.md` — the findings memory. Claims, not facts; it has been wrong and corrected before.
3. `RUN_RULES.md` — the operating law, including the trial counter and the register discipline.
4. `VALQUO_MASTER_AUDIT_ULTIMATE.md`, `VALQUO_EDGE_AUDIT.md`, `VALQUO_LIVE_AUDIT.md`,
   `VALQUO_OPTIONS_FRONTIER.md`, `HANDOFF_options_reopen_list.md` — your predecessors. You may
   cite them; you may not repeat them.
5. `HANDOFF_data_mining.md` + the D11 row — the harvest census: what data now exists, what is
   empty-in-principle, what was skipped and priced.
6. `RESEARCH_LOG.md` — the honest N. Every bar you quote must be quoted at the CURRENT N.
7. `C:\Users\donni\Downloads\Market Rotation\tidemark\` — a SIBLING project (read-only): its
   `CHARTER.md`, `LEDGER.md`, `POWER_GATE.md` and handoffs. It matters to mandates 5 and 6.

## The state you are walking into (verify, don't trust)

An 18-year equity backtest with calibrated placebo bars, whose composite sorts strongly
full-sample and **does not sort at all over 2016–2020** (deciles run backwards; P1S0-CONTROL).
An options record of 297 trials with zero entry edges and several closed families — but a
**newly pinned instrument nobody has analyzed**: 2.7M alternative contracts, 99.9% holding-period
chain coverage, 420 freshly pulled 2016–18 small-cap names (`pre_panel_history` flags must be
filtered), and a 70M-print tick cache asked only five questions ever. A forward paper track that
now records itself daily (gate 2027-02-13, verdict 2031-08-13). One shipped positive product
card (MA28: accounting flags → 3.04× crash rate, replicated, strongest in megacaps). A sibling
project (TIDEMARK) that measured cross-asset rotation as unanswerable at effective n=3 and built
an uncertainty-first dashboard. A site that is now a personal/portfolio instrument — public,
free, no monetization pressure — which changes what "product risk" means.

## Late-breaking context — landed AFTER this commission was drafted, and it changes two mandates

1. **MA58 returned UNINTERPRETABLE and its portable finding indicts the incremental-IC
   template itself** (commit 80a103e): complete-case residualisation on the seven weighted
   incumbents silently restricts the panel to **49 of 69 dates — a post-2014 test** — because
   `institutional` coverage starts late. U2, MA31 and MA32 all ran this template and none
   reported it. **Any proposal in mandates 2–4 that uses the incremental-IC gate must state its
   effective date coverage**, and auditing which prior template verdicts this recolours is
   in-scope for mandate 8.
2. **The tenor axis is now owned** (commit d6c943c): Tier E banked 14.3M option rows beyond
   200 DTE (max observed 858) for 2016–2018, which exist in no other store. The frontier's
   "only clearly positive at a tenor we do not own" caveat is now testable in principle.
   **The P1/options-expression family remains CLOSED** — this data does not reopen it by
   existing; mandate 1 may only propose designs that meet the closure's own re-open terms.

## The mandates

### 1 — THE OPTIONS EDGE, RELOCATED: stop asking "does the alert work"

That question is closed (R2: worse than random). The live questions have a different shape, and
your job is to design them, not re-litigate the dead ones:

- **The alternatives axis.** Every prior study scored the contract the book HELD. The pinned
  freeze now holds ~636 alternatives per entry date. What questions become askable only now —
  contract-selection rules evaluated against the full menu rather than one pick, the O21-D2
  template generalized, selection-vs-timing decompositions? For each: mechanism, register
  design, trial price, kill condition. Note what O6 already killed (cheapness rules that
  silently change delta) so you do not propose it in a costume.
- **The DTE × delta grid, done honestly.** Don has pre-committed interest in 60–90 DTE. Design
  the full-grid register: every cell booked as a trial before running, multiplicity priced at
  the current options N, the survivorship rule stated in advance. Say what result would make
  any cell ACTIONABLE rather than merely significant — O11's survivability finding binds.
- **Event ownership without a vehicle.** O17C4 measured a real effect — calls spanning
  earnings beat random entry by +4.79pp, both halves, z 2.05 — that survives its alert's death
  and currently has NOWHERE TO LIVE (the family closed on P1S0's gate; the median trade is
  still a near-total loss). Is there an honest design for it as its own strategy family, or is
  the correct verdict "real, mean-driven, untradeable"? Argue it either way with the record.
- **Expression and financing as the product.** DEEPITM-FIN priced deep-ITM financing at
  executable rf+342 all-in ~702bps/yr. The audit's question: is there ANY expression question
  left where options beat shares for this operator (collateral, tax, defined-risk sizing), or
  does the corpus close expression entirely? A closed door, argued from measurements, is a
  legitimate deliverable.

### 2 — COMBINATIONS AND AMPLIFIERS: measured quantities that could multiply

The record holds many measured objects that have never been crossed. For each proposed cross:
the mechanism (not "more inputs"), the incremental-IC-vs-incumbents gate (the PEAD/U2
template), the trial price, and why it is not a rejected item in a costume (the tree combiner
REVERSED out of sample; five weighting schemes died; interactions S7/S18 died):

- MA28's crash flags × anything: as an options-entry veto on the short-put side, as a
  position-sizing haircut, as a bear-scanner input. The card's gate was crash-rate, NOT alpha —
  keep that distinction or the proposal is void.
- V6-B's survival gradient (healthy dips fall further 25% less often, strongest in SMALL caps)
  × the book's construction — the claim is strongest exactly where the product is not; is there
  an honest small-cap surface or sizing use?
- The optionable-universe partition (P1S0: optionable names BETTER post-2021, worse before) as
  a REPORTED diagnostic rather than a signal.
- MA58's seasonality if it lands between commissioning and your read — check the ledger.
- Anything you find that nobody named. This is the mandate where creativity pays; every idea
  still carries mechanism + price + kill condition.

### 3 — THE 2016–2020 PROBLEM: the composite's dead half

The panel's single most consequential open finding: over 2016–2020 the full 2,531-name
composite does not sort (monotonicity positive at all three horizons, long-short t negative),
and it reverses late. R1's fragility work, X4's investability window and P1S0-CONTROL all point
at the same years. The naive fix — regime-conditioning — is the p-hacking minefield the record
warns about most. Your job: **is there a pre-registerable design that answers "when does this
composite work" without fitting the regime to the answer?** Constraints: regime definitions
must come from literature or from data OUTSIDE the panel (rates regime, dispersion, factor-spread
states — cite sources), committed blind; the verdict grammar must be three-state (works/fails/
cannot-tell); and you must state what the product may honestly DO with a regime verdict, given
V3's no-per-name-precision rule. If the honest answer is "not answerable without another decade
of data," say that — TIDEMARK's power-gate method (mandate 5) is the instrument for saying it
rigorously.

### 4 — UNTOUCHED INSTRUMENTS: what we own and have never read

- **The tick cache**: 70,288,482 prints, 3,884 alert days. Five features tested (O14), all
  null. Survey the microstructure literature for what else a print tape supports — order-flow
  toxicity/VPIN-class measures, trade-size clustering, quote-fade, intraday momentum — with
  replication status and the honest caveat that the cache is ALERT-DAYS-ONLY (a conditioned
  sample; name what that conditioning does to each candidate).
- **Tier C's 420 small caps, 2016–18**: never touched by any analysis. What is uniquely
  answerable there (the composite's dead window × small caps × options existence), and what
  the `pre_panel_history` ticker-reuse flags require.
- **The valuation engine's interior**: MA55's lens-disagreement width sits design-recorded;
  the S23 panel holds per-name fair-value trajectories nobody has mined for anything but
  exclusion screens. One page: what else lives in there?
- **The insider file's unused columns** (MA57: ownername, transactioncode — blocker refuted,
  change declined for having no consumer). Does any proposal here CREATE the consumer that
  justifies the one-line change?

### 5 — CROSS-POLLINATION FROM TIDEMARK: methods, not data

TIDEMARK built three instruments Valquo lacks: an effective-n/design-effect gate measured
against a shuffled null PER SERIES (its power gate refused Phase 2 at n=3 — the project's most
disciplined "no"); the Boudoukh-Richardson-Whitelaw check (R² rising with horizon is what the
null predicts — DIRECTLY relevant to S22's term-structure claims, which have never faced that
null); and a Hodrick estimator verified against published tables to fixed tolerances. Audit
which Valquo claims would change status under each instrument, and what porting each costs.
This is methods flowing between siblings — legitimate and free. **Data flowing is not free**:
if you propose ANY TIDEMARK series conditioning ANY Valquo quantity, you must design the fusion
register — trial charged in BOTH counters, the barred-list inherited, the display-vs-feed line
stated — or mark it out of scope.

### 6 — TIDEMARK AS A SURFACE: the integration design

Don wants the TIDEMARK dashboard reachable from valquo.co. Design it as a PRODUCT item:
display-only tab or linked page, derived statistics only (percentile, episode count, band — no
raw licensed series: Case-Shiller values, Ken French factors and NAREIT levels are restricted
even though the site is free), the uncertainty-first captions preserved verbatim, and the
explicit copy stating the rotation question was asked and came back unanswerable. Name the
lane, the files, and the one test that pins "no raw series reaches the payload."

### 7 — THE FACTORY, ROUND 2: what audit #3's process mandate missed

New evidence since: three stranded-work incidents in one week (a refusal note unpushed four
days; two "done" reports with nothing on origin); a six-day-stale `.git` lock silently breaking
a checkout; the manager's own roadmap listing a lane as in-flight on an intention rather than a
pasted prompt; prompts crossing mid-interrupt. The pattern: **the board's state lives in human
relay, and the relay drops packets.** Propose mechanization with teeth — a board-state
derivation from git itself (branch tips × handoff mtimes × ledger IN PROGRESS rows), a
staleness monitor for the shared checkout, a "prompt receipt" convention — each priced in
build-cost and false-alarm risk (the cry-wolf rule: MA21 declined a warning for firing on 41
legitimate rows; do not propose its sibling).

### 8 — INSTRUMENT CALIBRATION AGE, ROUND 2

Every bar was calibrated at a moment; N has moved again (equity 232+, options 297+). MA19
proved the floors are step functions of N with steps at the tail. Audit each calibrated
instrument's age against current N, name which recalibrations are due, which are provably
insensitive, and which comparisons in CLAUDE.md now quote a bar at the wrong N. Do not
recalibrate — that is registered work; deliver the staleness map.

### 9 — SIMPLIFICATION, ROUND 2, and the PIONEER page

The tree grew through the audit era: 30+ PROMPT_*.md files, PROPOSED_* leftovers, superseded
handoffs, the studies/ quarantine, dead worktrees. Propose deletions/archival with evidence of
deadness and a safety argument each. Then — the one page where you are EXPLICITLY licensed to
be speculative, labelled HYPOTHESIS throughout: **what could this project pioneer?** Candidates
you should evaluate and may reject: publishing the register method itself (a ~250-trial,
one-adoption, pre-registration-enforced retail research record is itself a novel artifact — and
for a personal/portfolio site, possibly the single highest-value page it could ship); the
disclosure-card family MA28 opened (published-threshold risk cards as a product class, distinct
from alpha products); an open effective-n calculator for retail backtests (TIDEMARK's method as
a tool). For each: what exists in the world already (search), what would be genuinely new, and
the cheapest first artifact.

## Discipline binding every mandate

- **Verify against the ledger, not prose.** The src=auto note has been wrong repeatedly.
- **Every proposal carries**: trials charged and to WHICH counter, effect on the DSR bar at the
  new N, the register it needs, the kill condition, and your stated prior (the record's authors
  predict REJECTED and are usually right — calibrate to that).
- **Re-runs of unchanged designs on the same panel are p-hacking and will be discarded.** A
  re-open needs new data, a new instrument, or a new design — cite which.
- **Closed families stay closed** unless you present the specific evidence class their closure
  named as a re-open condition.
- **Web search is available and expected** for mandates 1, 3, 4, 5 and 9 — cite, and mark each
  source's replication status. Literature is hypotheses, not facts; this project has killed
  published results before (O3/O4/O5, O7, MA31).
- **Questions for Don are batched** in one section, never blocking.
- Severity/EV-ranked within mandates. Anything unverifiable is marked HYPOTHESIS or
  UNCHECKABLE. Depth beats bulk; length earns itself.

## Deliverables (the only files you create)

1. `VALQUO_MASTER_AUDIT_4.md` — items IDed **MB1, MB2, …** (MA is taken), grouped by mandate,
   EV-ranked within group. Open with the honest one-page summary: the three most valuable
   frontiers, the one-paragraph state of the project, and what you could not check.
2. `valquo_master_audit_4_items.json` — one entry per item: id, mandate, title, EV class,
   trial cost + counter, data/register needed, kill condition — same shape the execution
   machinery consumed for audits #1–#3.
3. `VALQUO_MASTER_AUDIT_4.pdf` — the readable version.

End with the batched questions, and one paragraph answering the question this commission
actually asks: **after ~550 trials across two books, where does the next real edge most
plausibly live, where should nobody ever look again — and what is the single cheapest
experiment that could surprise us?**
