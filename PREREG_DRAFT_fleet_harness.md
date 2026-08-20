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
