# HANDOFF_ledger.md — refreshing VALQUO_LEDGER.md after the session 10-11 burst

**r1 lane, 2026-08-08.** Task: run `scripts/build_ledger.py`, reconcile its proposals against the
hand-verified rows, fold in the last two days of landings, publish counts by series and status,
list disagreements. One commit.

<!-- ledger:ignore -->

## 0. Bottom line

**The refresh itself moved one cell. Getting to the point where it could be run safely was the
work.** `--write` had never been executed since the out-of-band rows were added, and running it as
shipped would have **deleted eight hand-verified rows** — Sessions 7–11 and the public fair-value
leak closure — plus the entire "Ledger accuracy" prose section, plus the `FIXED` verdicts on `B8`
and `P4`.

**Counts: 72 of 134 audit items DONE (53.7%)**, 56 OPEN, 5 BLOCKED, 1 IN PROGRESS, 0 SUPERSEDED.
Hand-verified 91/134. Plus 8 out-of-band rows (7 DONE, 1 PRE-REGISTERED), counted separately.

**21 disagreements between the mechanical proposal and the human rows. All 21 resolve in favour of
the human row; no status changed.** Two of them are previously-unrecorded failure modes.

## 1. What I did NOT do

* **I did not run `--write` first and inspect afterwards.** The simulation ran against a copy. Had
  I done it in the obvious order, the eight rows would have been gone and the diff would have been
  a 29-line deletion inside a 142-row file — the kind of thing that survives review.
* **I did not fix traps 5 and 6** (below). Both are real, both would need a guess about
  commit-subject grammar, and the human row already wins. Recorded, not patched.
* **I did not touch `R3`'s stale note.** Not this lane's row; flagged for the second refresh
  running.
* **I did not re-adjudicate rows the proposal agrees with.** 113 of 134 rows are uncontested and I
  took them as they stand.

## 2. Three defects in `build_ledger.py`, all one signature

The script's own docstring promises *"It never silently overwrites a human-verified row."* It
broke that promise three ways, each of them the script curating content it did not write.

| # | defect | what it destroyed |
|---|---|---|
| 1 | `render()` iterated the 134 audit ids | **8 rows**: `OOB1`, `OOB2`, `OOB3`, `LOO`, `SELRULE`, `HACFLOOR`, `MLPREREG`, `MLCOMB` |
| 2 | preserve check was `src == "human"` exactly | **7 rows** signed `src=pipeline builder` rewritten from the proposal; `B8` and `P4` lost `FIXED` |
| 3 | `render()` emitted the hard-coded `LEDGER_HEADER` | all prose under the header — R3's stale-figure note, the C6 lesson |

**Defect 1 was already known and had been written into the data rather than fixed.** `OOB1`'s note
ends: *"NOTE: build_ledger.py regenerates from the 134 audit ids only and will DROP this row."* A
warning stored in the row it warns about is deleted by the same operation it warns about.

**My first fix for defect 3 introduced a fourth bug, caught by my own round-trip test.**
`existing_header()` split at the first line starting with `|` — which, once I added a
counts-by-series table to the prose, truncated the header there and dropped every section below
it. The boundary is now the table's exact `COLS` header line. The first version of the test passed
anyway (it only asserted the header was non-empty and contained no table rows — both true of a
truncated header), so **the test was strengthened to compare the whole prose block byte-for-byte**,
which is what actually catches this class.

Pinned by `tests/test_build_ledger.py` — **20 assertions, 20 passing**, including a round-trip of
the real file and an idempotency-relevant check that prose may contain its own markdown tables.

## 3. Counts by series and status — 134 audit items

| series | OPEN | IN PROGRESS | DONE | BLOCKED | SUPERSEDED | total |
|---|---|---|---|---|---|---|
| S | 24 | 0 | 4 | 0 | 0 | 28 |
| B | 1 | 1 | 24 | 0 | 0 | 26 |
| O | 19 | 0 | 6 | 1 | 0 | 26 |
| R | 0 | 0 | 6 | 4 | 0 | 10 |
| D | 1 | 0 | 9 | 0 | 0 | 10 |
| X | 2 | 0 | 6 | 0 | 0 | 8 |
| U | 6 | 0 | 2 | 0 | 0 | 8 |
| C | 0 | 0 | 7 | 0 | 0 | 7 |
| M | 3 | 0 | 3 | 0 | 0 | 6 |
| P | 0 | 0 | 5 | 0 | 0 | 5 |
| **ALL** | **56** | **1** | **72** | **5** | **0** | **134** |

**All 43 remaining `src=auto` rows are OPEN** (S 24, O 14, U 2, M 2, D 1). No `DONE` row anywhere
rests on machine evidence alone — worth stating, because `auto` means "not yet read by a person".

**The completion picture by series is lopsided and the counts make it legible.** `B` (24/26),
`C` (7/7), `D` (9/10) and `P` (5/5) are essentially finished; `S` is 4 of 28 and `O` is 6 of 26.
Those two series hold **43 of the 56 OPEN items** — the backlog is overwhelmingly signal ideas and
options studies, not corrections. The remaining 13 OPEN items are spread thinly across `U` (6),
`M` (3), `X` (2), `B` (1) and `D` (1).

## 4. The last two days: every landing was already recorded

Checked individually against the row, not assumed:

| landing | row | status |
|---|---|---|
| Session 10 (HAC long-short floor) | `HACFLOOR` | DONE — clears, 2.620 vs 2.2837 |
| Session 11 (ML tree combiner) | `MLPREREG` + `MLCOMB` | PRE-REGISTERED + DONE/REJECTED |
| O16 (term_slope a front-IV level?) | `O16` | BLOCKED/INCONCLUSIVE — stopped at its reproduction gate |
| O24 (term_slope an earnings calendar?) | `O24` | DONE/NULL |
| P2 (user crowding) | `P2` | DONE |
| C6 (three undeployed fixes) | `C6` | DONE/ADOPTED |
| public fair-value leak | `OOB1` | DONE/FIXED |

**Contract rule 1 is being followed** — every lane wrote its own row as part of its handoff, so
there was nothing to fold in. That is the ledger working as designed, and it is the reason this
task was a verification rather than a reconstruction.

## 5. Two new traps, added to the file's list

Both were found by reading disagreements rather than by looking for them.

**Trap 5 — a multi-item commit subject donates one item's verdict to every id in it.**
`275e9af` reads *"O16/O24 RESULTS: O24 is a NULL; O16 stopped at its own reproduction gate"*.
`NULL` is O24's verdict. Because the subject names both ids, the proposal marks **O16 DONE** — an
item that deliberately returned **no verdict at all** and is BLOCKED pending pinned chains. The
subject is accurate; the parser is per-subject, not per-clause.

**Trap 6 — `DEFERRED` sits in the DONE vocabulary, so "deliberately deferred" reads as finished.**
`B23`'s heading is `## B23 — DEFERRED, deliberately`; its body opens *"Not done, and not
forgotten."* `DEFERRED` is a legitimate verdict for a measured item, which is why it is in
`DONE_CUES` — but a deferred item is by definition not done. The proposal says DONE.

Both are the same shape as the four already documented: **a real English sentence that a
substring rule reads backwards.**

## 6. The 21 disagreements

Proposal is mechanical; its asymmetry is deliberate (wrongly-OPEN costs a re-check, wrongly-DONE
stops work). All checked against the write-up. **No status changed.**

**A. Proposal says DONE, item is not done — the dangerous direction, 3 items, all false.**
`B13` ("PARTIALLY FIXED and labelled so" — `MIN_AVG_DOLLAR_VOLUME` still cannot bind),
`B23` (trap 6), `O16` (trap 5).

**B. Proposal says IN PROGRESS, item is DONE — 6 items.** `B9`, `O2`, `U5`, `D8`, `D9`, `M5`.
Cause is a vocabulary gap: these write-ups conclude in words outside `DONE_CUES` — `RELABELLED`,
`adopted: []`, "Protocol WRITTEN". Not a status question.

**C. Proposal says OPEN, item is DONE — 8 items.** `P2`, `P3`, `P5`, `D1`, `D2`, `D5`, `D6`, `D7`.
The collision guards firing as designed. Two distinct causes worth separating:
* `P` is a colliding series, so a heading needs an audit cue. `P2` **has** two headings
  (`HANDOFF_crowding.md:1`, `HANDOFF_STATUS.md:53`) and neither carries one, so both are discarded.
* `D1`/`D2`/`D5`–`D7` are written up as **table rows** in `HANDOFF_data_spend.md`
  (`| **D1 · Sharadar direct** | Bundle **$29/mo** …`), not as headings. There is no HEADER
  evidence to find, and the D-series decile guard suppresses the rest.

**D. Proposal says OPEN, item is BLOCKED — 4 items.** `R4`, `R5`, `R6`, `R8`. Blocked on **lane
ownership**, not evidence: they sit in `valuation/edge/**`, which `AGENTS.md` assigns to the
pipeline-builder lane. The script cannot see an ownership boundary. Genuinely defensible either
way; kept BLOCKED because that is the fact a reader needs.

## 7. The one substantive change to a row

`D4`'s note: `no mention anywhere in the corpus` → `prose mentions only, no section, no commit`.
Status unchanged (OPEN). The genuine mention is `HANDOFF_data_spend.md:161` (*"D4 (Cboe
Open-Close) — not in this task's list, still unpriced, still gated on O14"*).

**Reported because it is half wrong:** D4's second "prose" hit is
`HANDOFF_edge_audit.md:3279  | D4 | 314 | $90.4B | +4.92% | 36.0% |` — a **decile table row**. The
`DECILE_CONTEXT` guard is line-local and matches on words like "decile" or "long-short", which a
bare table row does not contain. Left alone: D4 is OPEN either way, and tightening the guard on
one example risks suppressing real evidence.

## 8. Known limits of this refresh

* **`VALQUO_LEDGER.md` is not in the scanned corpus** (`HANDOFF_*.md` plus `CLAUDE.md`,
  `RUN_RULES.md`, `VALQUO_ACTION_PLAN.md`, `AGENTS.md`), so nothing published in it feeds back.
  **This file IS scanned**, which is why its id-listing sections are wrapped in
  `<!-- ledger:ignore -->`.
* **Prose below the table is still not preserved.** `render()` appends the table last. Keep
  narrative above it.
* **The counts are of rows, not of work.** A DONE row means a write-up exists and was
  hand-verified against it — not that the finding is correct or still current. `R3`'s stale
  `1.36x` note is a DONE row carrying a wrong number right now.
* **Traps 5 and 6 are unencoded**, so the same two disagreements will reappear on every refresh
  until someone fixes the parser or the commit subjects.

## 9. Trial cost: none, and no threshold was pre-committed

**No `RESEARCH_LOG.md` row is owed and equity `N` stays at 129** (session 11's MLCOMB left it
there). Nothing here searched a hypothesis space, fitted anything, or selected among arms — it is
bookkeeping plus three code fixes. Adding a row would overstate `N` and understate the headline's
Deflated Sharpe for no reason.

**No threshold was pre-committed, because there is no verdict here.** Per `RUN_RULES.md` that
would make a *result* provisional; this task produces counts and a reconciliation, not a
measurement. The counts are reproducible from the tree at any time by re-running the script.

## 10. Recommended next step

**`R3`'s note has now survived two refreshes with a known-wrong figure in it** (`1.36x`; correct is
`√2.212 = 1.487×`). It is a one-line edit that nobody owns. Either the pipeline-builder lane takes
it, or the "not this lane's row" convention should give way to "any lane may correct a figure that
is already corrected elsewhere in the project" — the current convention is preserving a known
error out of politeness.

<!-- /ledger:ignore -->

## Reproduce

    python scripts/build_ledger.py              # proposal + counts + disagreements, no writes
    python scripts/build_ledger.py --write      # refresh src=auto rows only (now idempotent)
    python scripts/build_ledger.py --evidence O16
    python tests/test_build_ledger.py           # 20 assertions
