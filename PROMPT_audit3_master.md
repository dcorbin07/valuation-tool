# COMMISSION — Master audit #3: everything, end to end, no stone unturned

You are a cold auditor with no history in this codebase — that is your entire value. Work in
`C:\Users\donni\Downloads\valuation-tool`. **STRICTLY READ-ONLY**: you change nothing, fix nothing,
run no backtest, adopt nothing. Your only outputs are the three deliverable files at the end.

**DO NOT START unless the board is quiet:** `VALQUO_LEDGER.md` shows no `IN PROGRESS` rows and
`git log` shows no lane mid-session. Auditing a moving target voids the audit (the project learned
this as item O16). If the board is not quiet, say so and stop.

## What you are walking into — read these before anything else

1. `VALQUO_LEDGER.md` — ~185 adjudicated items. The index of everything.
2. `RUN_RULES.md`, `CLAUDE.md` — the operating rules and the project memory (memory has been wrong
   before; it is claims, not facts).
3. `VALQUO_EDGE_AUDIT.md` (audit #1, the backtest tree) and `VALQUO_LIVE_AUDIT.md` (audit #2, the
   live product) — your predecessors. Do not re-produce them; you inherit them.
4. The registers: every `PREREG_*.md`, `PAPER_TRACK_CONTRACT.md`, `RESEARCH_LOG.md` (N ≈ 202),
   `VALQUO_EXTENSIONS.md`, the `HANDOFF_*.md` corpus.
5. Practical: licensed data (`data/`) is gitignored — its absence from git is CORRECT, not a
   finding. Check whether the unanchored `data/` gitignore still bites ripgrep before trusting any
   clean grep.

The project's state: an 18-year backtest with calibrated bars (long-short HAC floor 2.2837, theme
IC t 2.71, DSR 0.72 at honest N), a live product that withholds what it cannot defend, a signed
forward-track contract (verdict 2031, meter first render 2027-01-30), vintage-tracked adoptions
with shadow books, and a research record where almost everything tested came back NULL or
REJECTED — which is what made the survivors believable.

## The four mandates

### 1 — TRADE LOGIC: what was thrown out wrongly, what was never tried, what combines

Audit the RESEARCH RECORD itself, not just the code:

- **Wrong rejections.** Read the registers and verdicts for: bars that were unreasonable for the
  effect size sought; designs that could not have detected the effect they tested (the project's
  own S19 wrote "the design could not have caught the effect" — find every verdict with that
  shape); near-misses recorded honestly (S21 missed by 17bps, S11's A2 by 18bps) where a
  DIFFERENT pre-registerable design — not a re-run — could give a real answer. You may propose a
  re-examination list; each entry must name NEW evidence or a NEW design, never "run it again."
  Re-runs of unchanged designs on the same panel are p-hacking and will be discarded.
- **Untested combinations.** Numbers computed in one subsystem that could inform another: the
  valuation engine's outputs as panel signals, the terminal-share and provenance flags as risk
  conditioners, the withholding states as information, tenure/decay statistics in construction,
  anything where a measured quantity sits unused. For each: the hypothesis, the mechanism, the
  register it would need, its trial cost at the current N, and the incremental-IC-vs-incumbents
  control (the PEAD/U2 template) as the mandatory gate.
- **Equation candidates.** Where combining existing measured quantities into one predictor has a
  MECHANISM (not just "more inputs") — state the construction exactly, note that the tree
  combiner REVERSED out of sample and five weighting schemes were rejected, and say why your
  candidate is not those in a costume.

### 2 — CODE: bugs, inconsistencies, inefficiencies, anything broken

Both prior audits' domains, current tree. Hunt the recurring classes first (units, silent-empties,
two recorders, guards-that-cannot-see, fixed field lists, positional reads, clamps disguising
garbage, time-bombed tests, boundary/date-gating defects) — then what nobody has named. Every
finding: file:line, evidence (quoted or measured, never inferred), blast radius, cheapest
verification, severity. Include performance only where it changes behavior or cost (B23 exists;
do not duplicate it).

### 3 — NEW FEATURES: the Dip Detector class of idea

Deliberately creative, clearly fenced: product ideas the data already supports that nobody has
proposed. The Dip Detector is the template — a screen built from measured pieces, whose claim
gets registered before it is spoken. For each idea: what it shows, which existing measured pieces
power it, what claim it would tempt the product to make, and the register that claim would need.
Mark ALL of this section HYPOTHESIS. Posture rules bind: no performance claims, no per-name
precision (V3), withholding honoured, raw vendor data never.

### 4 — EXTERNAL RESEARCH: what the field knows that this project has not absorbed

Survey the literature and current practice relevant to each subsystem — factor construction and
combination, exits and holding periods, execution and capacity, vol surface and options flow,
text/alternative signals, regime detection, portfolio construction, inference under multiplicity.
Web search is available; use it. For each relevant finding: citation, its replication status in
the literature, and its mapping — ALREADY TESTED HERE (cite the ledger row; the project has
refuted published claims before — O3/O4/O5 note a published contradiction that did not survive
the instrument), TESTABLE HERE (name the register and data), or NOT TESTABLE HERE (name the
missing data and its D-series cost). Treat literature as hypotheses, not facts — this project's
data has killed published results before.

### 5 — THE PROCESS ITSELF: audit the factory, not just the product

The multi-agent workflow, RUN_RULES, the register conventions, CI, the ledger machinery — these
are now how everything gets made, and the record shows they fail in patterns: the `src=auto` note
wrong six times, a shared status file causing serial merge conflicts, stale assignment docs
routing work to terminals that did not exist, sessions dying mid-stream and resuming from memory
instead of artifacts. Read the prompts, handoffs and rules AS A SYSTEM and name: where the
process depends on an agent choosing to be honest rather than being unable to lie; which manual
steps recur enough to deserve automation; which conventions exist only in prose and could be
enforced by a check. The factory's defects become the product's defects with a one-session lag.

### 6 — ADVERSARIAL: security, abuse, and poisoning

The last security pass predates the public/free posture, the demo token, the research page, the
scheduled writers and the gh auth. Think like three attackers: a stranger (what does scraping,
replaying or hammering the public APIs and demo link expose or cost?), a leaked link (blast
radius of each token/secret, rotation reality), and a hostile data feed (a vendor returning
poisoned or subtly-shifted values — fail-closed covers absence; what covers WRONG-but-plausible?
the beta drift incident says this is real). Include the record's integrity: what could silently
alter a banked verdict, a frozen chain, the research log, and would anything notice?

### 7 — CONTINUITY: single points of failure and the bus test

Statistical rigor is now far ahead of operational resilience. Inventory every single point of
failure with its blast radius and recovery path: PT-WRITER lives in one desktop app that must be
open at 20:01; the Sharadar freeze exists on one laptop and one SSD; scheduled tasks, gh auth and
.env live on one machine; Render, FMP, Yahoo and Tradier can each change or die (the beta-field
disappearance is precedent). For each: what breaks, how loudly, what the contract says happens to
the record, and the cheapest hardening. Then the bus test: could a competent stranger, from the
repo and README alone, keep the system alive and reproduce its headline claims? Name every gap.

### 8 — SIMPLIFICATION: what should be deleted

Fast growth left scaffolding: rejected-arm code, dead flags, superseded docs, the decommissioned
options-bot tree, endpoints nothing calls, toggles the research eliminated. Complexity is where
the next bug lives — the audit record proves it (three composite functions, two recorders, nine
dropped fields). Propose deletions with evidence of deadness (no caller, no reader, superseded-by)
and a safety argument each; flag anything that LOOKS dead but is load-bearing. A smaller tree
that does the same thing is an improvement in every mandate at once.

### 9 — THE INSTRUMENTS' CALIBRATION AGE

Every bar was calibrated at a moment: X7's floors on a particular panel, the DSR at a particular
N regime, the cost table at particular measurements, the fidelity bar from 36 theme pairs. The
panel, N (~202) and the code have all moved since. Audit each instrument's calibration DATE
against what changed after it, and name which recalibrations are due, which are provably
insensitive (the adopt-curve precedent: N 116→129 left the floors unchanged), and which were
never valid for their current use. Do not recalibrate anything — that is registered work; your
deliverable is the staleness map.

## Discipline that binds every mandate

- **Verify against the ledger, not the prose.** A claim in CLAUDE.md or a handoff is a lead. The
  `src=auto` "no mention" note has been wrong six times; sections exist for things the ledger
  said had none.
- **Every proposed test carries its price**: arms, N impact on the DSR bar, and what result would
  kill it. An idea without a kill condition is not a proposal.
- **Questions to Don are welcome but batched**: collect them in one section of the report rather
  than blocking on answers. Where an assumption substitutes for an answer, state it.
- **Severity-ranked, evidence-cited, length earns itself.** Depth beats bulk. Anything you could
  not verify is marked HYPOTHESIS or UNCHECKABLE — an unverified claim promoted to fact is worse
  than a gap.

## Deliverables (the only files you create)

1. `VALQUO_MASTER_AUDIT.md` — findings and proposals IDed **MA1, MA2, …**, grouped by mandate,
   severity-ordered within group. Open with the honest one-page summary: the three most valuable
   things you found, the overall state of the project in one paragraph, and what you could not
   check.
2. `valquo_master_audit_items.json` — one entry per item: id, mandate, title, severity/value,
   files or registers touched, evidence-needed, trial cost where applicable — so the execution
   machinery that processed the first two audits can process this one.
3. `VALQUO_MASTER_AUDIT.pdf` — the readable version.

End with the batched questions for Don, and one paragraph answering the question this project has
earned the right to ask: **given everything tested and everything measured, where does the next
real improvement most plausibly live — and where should nobody look again?**
