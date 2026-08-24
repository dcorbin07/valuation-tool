# PREREG — S3-I1: THE FLEET HARNESS (accepted register)
## Executor: options-live lane, 2026-08-23. Draft: Frontier Scout, `PREREG_DRAFT_fleet_harness.md`.

**VERDICT ON THE DRAFT: ACCEPTED.** Its convention is right and the convention IS the
deliverable. It is reproduced **VERBATIM** below the rule, byte-for-byte, at
`sha256 5654d8187be2af666cf07690c531b513ccd2a94aba0728cb2a6fc19beb871621` (5,719 bytes, 88
lines), taken from `origin/worktree-scout-brainstorm`. **Nothing below the rule is edited.**

**This block is ADDITIVE and every item in it is declared BEFORE any code is written, any
declaration is validated and any fill is recorded.** `SC-1`'s pattern, and `MB1`'s discipline:
a register is run AS WRITTEN and its defects are REPORTED rather than quietly repaired — except
where running it as written would record something false, which §E2 below is.

**This register ADOPTS NOTHING, TRADES NOTHING, and LICENSES NO REAL MONEY.** It is an
instrument. No outcome statistic is computed anywhere in it or in what it builds.

---

## E0. Non-blindness, stated rather than discovered

Before accepting I read `index_mark.append_row`, `track_meter.boundary`/`meter`, `paper_track`,
`paper_broker` and `scripts/slippage_report.py` to establish **whether the named machinery
exists and fits**. That is a structural read of code, not a measurement: no book exists, no
fill exists, no outcome relationship was computed, and there is nothing here whose sign could
have been known in advance. **§E2 is what that read found**, and it is declared here rather
than presented later as a discovery.

## E1. TRIALS: ZERO, against the draft's own "1 infra trial (20 -> 21)"

The draft's own **§2** fixes the rule: *one trial per book, charged at FIRST VERDICT READ.*
Applied to the harness itself, the harness **states no hypothesis, sets no bar, returns no
verdict and computes no outcome relationship** — so under its own convention it charges
nothing. The precedent is direct and recent: **`I-2` and `I-3` were each priced at 1 infra
trial in `IDEAS_LEDGER.md` and logged at ZERO**, on `MA5` (a consolidation is a correctness
repair) and `S25`/`MB15`/`MB3` (a census is a fact about what data exists). Infra `N` gates no
published claim either way.

**The counter-argument, stated because it is not frivolous:** the harness fixes a convention
that every future fleet verdict inherits, which is arguably a design degree of freedom. Against
it, `MB1-SEL` governs — machinery that can only ever **BLOCK or RECORD**, never produce a
finding, adds no degree of freedom to any published claim. If a later reader disagrees the row
is there to amend. Note the direction: **overstating `N` is the safe direction** (`MA6`), so
this departure runs the *unsafe* way and is therefore stated loudly rather than assumed.

**Proof obligation, fixed now:** `by_domain` must be **bit-identical** across the log append
(equity 242, options 305, infra 20) and `rows_fixed_not_counted` must rise by **exactly 1**.
Anything else means the row was mis-filed.

## E2. THE NAMED MACHINERY DOES NOT FIT THE NAMED USE — the defect that changes the build

**§1.2 says records go "on the PT-WRITER machinery, reused not rebuilt" and names `MA4`'s
atomic append. Measured: `index_mark.append_row` is keyed on `date` and is idempotent per
date.** With `append_only=True` a duplicate date is a **NO-OP returning the row already on
disk**; in the default mode it is a **REPLACEMENT**. A fleet book records **many orders per
day**.

**So reusing it verbatim would silently drop every fill after the first each day** — and it
would fail in the direction that reads as a quiet book rather than as an error, which is this
record's worst failure shape.

"Reuse, do not reimplement" is therefore honoured by **EXTRACTION AND DELEGATION**, which is
`B7`'s lesson and the `MA5`/`I-3` pattern already run twice on this record: the append-only
rules move into **one key-generic implementation**; `index_mark.append_row` **delegates** to it
with `key="date"`; the fleet recorder calls the same code with its own key. A second write
implementation is refused explicitly — `append_row`'s own docstring names that *"the B7 split
this module already warns about"*.

**Because `index_mark.append_row` writes the one file this project calls un-re-derivable, the
refactor is gated BEFORE anything new uses it (`MB15`'s ordering):**

1. Reproduce the **pre-refactor source restored from git**, bit-identical, over a randomised
   case sweep covering every branch — first write, duplicate date, backward date, header
   widening, ragged file, missing file, ignored fields, replacement.
2. Reproduce the **byte-level prefix guarantee** the shipped Action verifies.
3. `tests/test_index_mark.py` passes **unchanged**, with no edit to any expectation.

**If any of the three fails, the refactor is REVERTED and the fleet gets its own writer with
the split declared in the handoff.** Stated now so the fallback is not chosen after seeing
which way a failure fell.

## E3. THE HASH CHAIN IS OVERSTATED IN §4, and the bound ships with it

§4 claims *"a tampered row is DETECTED (hash chain over append order — `MA13`'s
committed-literal idiom applied to records)"*. **`MA13`'s idiom is a literal committed in a
TEST, and fleet records live under `data/`, which is gitignored** — so no committed literal can
track a growing record stream, and the analogy does not carry.

**What the chain actually buys, stated as the bound rather than as the claim:** each row
carries the hash of the row before it, so **reordering, an interior deletion, a truncation and
any edit by anything that does not recompute the chain are DETECTED**. It is **NOT tamper-proof
against a writer that recomputes the chain.** What *is* committed is the **declaration**, so
the chain's genesis is anchored to the declaration's own content hash — the strongest anchor
available without putting records into git. The bound ships in the module and in the artifact,
never as something a reader has to infer.

## E4. §2's PEEK RULE IS AN HONOUR SYSTEM UNLESS THE PEEK IS RECORDED

*"A book whose meter is peeked at before the horizon has been read: the peek IS the verdict
read and books the trial"* is unenforceable if nothing records the peek. **Every meter read is
therefore itself an append-only record on the book's own stream**, so "first verdict read" is a
dated fact rather than a memory. Additive to the draft; it is what makes the draft's own §2
auditable instead of aspirational.

## E5. DON'S FLEET RULING SUPERSEDES EXPECTATION (1), which is UNSCORABLE

§6(1) prices *"≥6 books declared within two weeks of the harness landing — 70/30"*. **Don's
ruling is that all ~18 declarations commit TOGETHER once the harness exists, and fills begin
for every book the moment day-1 self-verification passes.** An expectation about staging cannot
be scored against a ruling that removes the staging. Recorded **VOID-BY-RULING** — neither
right nor wrong. §6(2), (3) and (4) stand and stay scorable.

## E6. DAY-1 SELF-VERIFICATION — required by Don's ruling, absent from the draft

Don's ruling makes fills conditional on the harness passing its own first-day check, and the
draft designs none. Fixed now, the **run-#6 pattern**: a declared book's fills **round-trip** —
declaration validated, fills recorded, records read back and compared **bit-identical**, chain
verified, and a tampered copy REFUSED. It exits non-zero on any failure, and **the recorder
refuses every fill while the last self-check on record is absent, stale against the current
harness, or failing.** No book fills before it passes. No other staging.

## E7. S3-I3 IS r1's — this defines the INTERFACE and builds no assignment model

§1.4 requires the recorder to REFUSE a short book with no assignment module. That module
(`S3-I3`) is being built in parallel, so the refusal keys on two things the harness owns: the
declaration **declaring** the required fields, and a **registered provider** satisfying a named
interface. **With no provider registered every short book is REFUSED** — the safe direction —
and the refusal **names the interface** rather than crashing on an absent import. The interface
is frozen here so r1 has a fixed target; the harness computes no assignment and no margin.

## E8. "COMMITTED ALONE BEFORE FIRST FILL" HAD NO MECHANICAL ENFORCEMENT IN THE DRAFT

§1.1 makes the commit the tamper-evidence and then pins only the short-book **schema**
validation. The enforcement is therefore built here and keys on **git**: the declaration's
commit must exist, must be an **ancestor of HEAD**, and must touch **exactly one file** — that
declaration. A fill is REFUSED otherwise, and the refusal is a record.

**The honest limit, stated because a reader will assume more:** this proves the declaration
landed before the fill was **RECORDED**, on the harness's own clock. **It cannot prove an order
was not placed at a broker beforehand.** The record stream is the evidence; the broker is not.

## E9. V5-GRADE MEANS THE TWO COLUMNS V5 ROUTED AND NOBODY TOOK

`scripts/slippage_report.py` states its own binding gap: *"`paper_option_orders` stores no bid,
ask or mid at submit time ... The fix is two columns written in `_place_entry` (`entry_bid`,
`entry_ask`); V5 is scoped to new files only, so this is ROUTED."* **Nobody took it.** A fleet
fill record therefore stores **bid, ask and mid at submission** as first-class fields — exactly
the object V5 could not recover and `F-1` is built to read.

**And V5's sandbox caveat travels with every fleet fill, stamped by the recorder rather than
remembered:** Tradier sandbox quotes are delayed ~15 minutes and its fills are simulated
against them, so **a measured cost BELOW the model is the direction the measurement error
already points and is weak evidence; a measured cost ABOVE the model runs against the bias.**

## E10. Void conditions ADDED to the draft's §5

6. Quoting any figure the harness produces as a **result**. It records; it does not measure.
7. Recording a fill for a book whose declaration is not a landed, alone, ancestor commit — or
   while the day-1 self-verification is absent, stale or failing.
8. Editing a fleet record file by any route other than the shared append-only writer.
9. Reporting a `NO CONCLUSION` meter state as evidence of absence. Each declaration's minimum
   effect and horizon are what bound it, and both must be quoted with it.

## E11. What this register does NOT do, named so it is not mistaken for done

**No book is declared here** — the ~18 declarations are a separate commit under Don's ruling,
and the four `DECL_DRAFT_*` files on the scout branch are drafts, not declarations. **No fill
is placed.** **No assignment or margin model is built** (`S3-I3`, r1's). **No fleet dashboard**
(`S3-I7`, app lane). **No schedule** (Cowork's). **No meter is read**, so nothing here charges
a trial under §2. **`IDEAS_LEDGER.md` and `SEASON3_MAP.md` are NOT edited** — the scout lane
reserves them, and the trial-accounting departure in §E1 wants relaying into them.

---

# PREREG DRAFT — S3-I1: THE FLEET HARNESS
## One convention + one recorder for many concurrent declared forward paper books

**DRAFT, Frontier Scout lane, 2026-08-21.** Infra register — an executing lane commits it
ALONE, then builds. **1 infra trial (20 → 21 at this writing). Infra gates no published
claim.** Everything in Track F waits on this; it is the season's first instrument.

## 1. What a FLEET BOOK is — the convention, which is the deliverable

1. **A declaration file, `DECL_<book>.md`, committed ALONE before the book's first fill.**
   The commit is the tamper-evidence (the PREREG discipline applied forward — and the EO
   rubric's landing-order proof this season showed the mechanism working). The declaration
   freezes: entry rule (computable from data available at entry time, stated as code-level
   pseudocode), structure (strike selection by MONEYNESS or fixed rule — any delta-targeted
   strike must argue past `V6-OPT`'s autopsy in the declaration itself), universe, sizing and
   concurrency cap, the records schema, and the **verdict horizon** (§3).
2. **Append-only records on the PT-WRITER machinery, reused not rebuilt:** the Render
   service's POST door pattern (`174ecb7` lineage), `MA4`'s atomic append (temp-file +
   `os.replace`, header-union), the weekly git archive workflow, and `MA36`'s
   worthless-expiry settlement rules. One records file per book; a book's history is never
   edited, a correction is a new dated row (`PT-AMEND1`'s shape).
3. **Fill recording is V5-grade:** quote at order, order type, fill price, time-to-fill,
   unfilled fate — because `F-1` (the fill A/B) reads every book's fills, every book records
   as if it were the fills experiment.
4. **The short-book module (Don's ruling #1, mandatory):** any book that sells premium
   models **assignment** (at expiry per moneyness; early-assignment flagged via `O21`'s
   q-machinery) and **margin/cash-securing** (Reg-T cash-secured convention; the secured cash
   is the denominator of every return quoted) in the declaration, or the harness REFUSES the
   book — pinned by a validation the recorder runs on the declaration's schema.
5. **One ledger row per book** at declaration (status DECLARED, no verdict), amended at
   verdict — rule 3's append-and-amend.
6. **`O11` binds every book; sandbox only; nothing licenses real money.** Each declaration
   carries the sentence verbatim.

## 2. Trial accounting — the convention this register exists to fix in writing

**One trial per book, charged to the book's outcome domain, booked at FIRST VERDICT READ —
not at declaration.** Precedent: `MLPREREG` (registered, uncharged) → `MLCOMB` (executed,
charged); `PT-METER` registered with verdict pending. The anytime-valid meter (`PT-METER`'s
Robbins mixture, per book, parameters frozen in the declaration) is what makes ONE charge
honest under continuous monitoring — that is the entire point of anytime-valid machinery,
and the record already owns it. A book abandoned before its horizon with no verdict read
charges nothing and says so in its closing row. **A book whose meter is peeked at before the
horizon has been read: the peek IS the verdict read and books the trial** — peeking is not
free, it is early.

## 3. The verdict-horizon field — mandatory honesty about time

Every declaration states: expected fills/month (from the entry rule's own historical firing
rate, a descriptive count), the fills needed for its meter to resolve its pre-stated minimum
effect (both power vocabularies, `power_gate.state()`), and therefore the **earliest honest
read date**. V5 needed 30 fills and has 3 — the number goes on the declaration so nobody
reads a six-month book at six weeks. The fleet dashboard (S3-I7) renders horizon vs accrual
per book, no performance figures (`MB38`'s gate).

## 4. Validation (fixed before build)

* Round-trip: a synthetic book's declared schema → recorder → archive → reader reproduces
  bit-identical rows; a tampered row is DETECTED (hash chain over append order — `MA13`'s
  committed-literal idiom applied to records).
* Refusal tests: a short book without the assignment module is REFUSED; an entry outside the
  declared rule is REFUSED and logged (the refusal is a record, not a crash).
* The A/B randomizer (for `F-1`): deterministic per-order seed derived from
  (book, date, symbol) so assignment is reproducible and unriggable — pinned by test.
* Clock discipline: `LA4`'s lesson — every record stamps its clock at write, and the
  same-week late-write clause from the PT contract is inherited.

## 5. Void conditions

1. Any book trading before its declaration's landed commit exists.
2. Editing a declaration after first fill (append-only addendum, `PT-AMEND1` pattern).
3. Reading any cross-book aggregate as a verdict (each book has its own meter; a fleet-level
   "portfolio" reading is its own future register).
4. Charging fleet books at declaration (see §2) or double-charging a peeked book.
5. Real-money execution of anything, ever, from this machinery.

## 6. Expectations, scored later

(1) ≥6 books declared within two weeks of the harness landing — 70/30. (2) The refusal tests
catch at least one real declaration defect in the first wave — 60/40. (3) `F-1` reaches its
horizon before any directional book reaches its own — 80/20. (4) At least one book is
abandoned pre-horizon, correctly uncharged — 55/45.

## 7. Owner and routing

options-bot (recorder, records, meters) + edge (ledger rows, power lines) + app (S3-I7
shelf) + Cowork (schedules: the fleet heartbeat and K2's weekly census). Lane collisions per
the map §5: declarations are inert .md; the recorder is options-bot's file.
