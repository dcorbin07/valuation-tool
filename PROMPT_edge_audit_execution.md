# PROMPT — Execute the external edge audit

**Owner:** research/pipeline terminal · **Handoff file:** `HANDOFF_edge_audit.md` (create it) · **Source:** `VALQUO_EDGE_AUDIT.md`

---

## What this is

An outside session with read-only repo access audited the whole programme on 2026-08-03 and produced a
134-item catalogue: `VALQUO_EDGE_AUDIT.md` (markdown, read this one) and
`Valquo_Edge_Audit_and_Test_Catalogue.pdf` (same content, for Don). Both are gitignored — they live in
the working folder only.

It is **not** project memory. It is an outside review, and **where it contradicts the record, the
contradiction is the point**. Several items assert that a number in `CLAUDE.md`, `HANDOFF_STATUS.md` or
`BACKTEST_RESULTS.json` measures something other than its label. Your job is to check those claims
against the code and settle them — not to defend the record and not to accept the audit on faith.

Every finding in it is a **code-reading** finding. Nothing was executed. Magnitudes, directions and
outcomes are all unverified. Treat each item as a hypothesis with a file:line citation attached.

---

## Step 0 — before you touch anything

**0a. Reconcile the tree.** As of the audit: local `main` was **16 commits behind `origin/main`**, with
**332 modified files and 35 untracked** — including `CLAUDE.md`, `BACKTEST_RESULTS.json`, both GitHub
workflow files, and never-committed docs (`AGENTS.md`, `OPTIONS_DEEP_RESEARCH.md`, most `PROMPT_*.md`).
Part I edits `options_universe.py`, `options_backtest.py`, `fundamental_panel.py`, `factors.py`,
`screen.py`, `paper_track.py` — all in that modified set. Pull, reconcile, and confirm a clean tree
before the first edit. Do not start corrections on top of that.

**0b. Widen the CI gate (item C7).** `land-agent-branch.yml` auto-merges every `worktree-*` push behind
**`tests/test_edge.py` only** — 14 of 15 suites do not gate a deploy, and this catalogue touches files
that suite does not cover. Add the other suites *before* any Part I edit can auto-land.

**0c. Sharadar is time-limited (items D10, C5).** Run one full backtest from
`data/backtest_freeze_2026-08/` and confirm it reproduces the current numbers. Extract, while the
subscription is live: the EVENTS `eventcode` legend, the ACTIONS action enum, the exhaustive
`TICKERS.category` values, whether SF1 `%` fields arrive as `0.15` or `15.0`, and — highest value —
**whether a restatement appends a new ARQ row** (`scripts/verify_sharadar.py` was written for exactly
this and has never been run against the real key). This window closes and does not reopen.

---

## The pre-commitments — write these down before you read the results

The failure mode of handing an audit to the audited is motivated reading. Record the following in
`HANDOFF_edge_audit.md` **before** running anything, and do not revise them afterwards.

1. **R1 (factor-adjusted alpha).** Commit now: the product uses the word *alpha* only if the FF5+MOM
   intercept is positive with *t* > 2.0. If it is not, the framing becomes *efficient factor exposure*
   and item P5's second product claim ships. Write both versions of the claim before you see the number.
2. **R2 (corrected options re-run).** Commit now: if the corrected real-versus-control gap stays
   negative at significance under a **date-block** bootstrap (R3), the entry signal is dead and the
   record says so. If the gap closes to within its confidence interval, the verdict is **inconclusive**,
   not vindicated.
3. **R7 (`term_slope` retention floor).** Argue and commit an appropriate floor for a 187-name universe
   **before** re-scoring the banked log. Do not pick it after seeing the retention figure.
4. **Every other item** carries its own pre-registered threshold in the catalogue. Confirm each in
   writing before its run; do not re-derive one after results land.

If a result is ambiguous against its own committed threshold it is a **null**, not a judgement call.

---

## Order of work

Follow the sequencing in Part XV of the catalogue. Summarised:

| Session | Work | Why this order |
|---|---|---|
| 1 | Cheap corrections: B1, B3, B10, B12, B14, B15, B16, B18, B19, B20, B24, B26, B9 relabel | All XS. Kick off the **B1** re-run overnight at the end |
| 2 | B2, B4, B5, B7, B11, B13, B17, B21, B22, B23, B25; begin B6 | The corrections that need thought |
| 3 | **X7** (placebo through the full pipeline) + **X2** (grid-offset sensitivity) | Establishes the noise floor. Every threshold in the project is currently uncalibrated against it |
| 4 | **R1** + **X4**, alone and carefully. Then R9, R10 | The test that decides the story. **Do not start Parts III–V until it returns** |
| 5 | R2 + R3 together, R7 committed first, **O20** folded in | The honest verdict on the options entry signal |
| 6 | **U7** + **X3** | One-line probes that can kill or promote much larger items |
| 7 | U2, then U1, then U6 | The unification. U2 first — it feeds the programme that works |
| 8+ | O1, S20, S21, X1, S2, S19, X8, O2, O6, S1, S10, O15, C1–C4, P1, **P4**, S5 | Descending value |

**P4 is urgent out of band.** The forward track's `seed_book` never sells names that leave the book, so
it only ever adds — a track that silently drops losers is worse than no track. Combined with the four
defects in **B5** (mid-vs-bid exit, dry-run burning alerts, resumed entries becoming market orders with
NULL target/stop, P&L booked against the alert-time ask rather than the fill), every session that
accumulates under the current rules has to be thrown away. Fix before the track grows.

---

## Parallel lanes — before dispatching more than one agent

`VALQUO_AUDIT_DEPENDENCY_MAP.md` + `valquo_audit_items.json` + `check_lanes.py` give the write-set,
dependencies and collision class for every item. Run the validator before any concurrent dispatch:

```bash
python check_lanes.py B1 C4 X3 P1      # can these run concurrently?  exit 0 = safe
python check_lanes.py --lanes          # the lane assignment
python check_lanes.py --ready B1 B3    # what unblocks once these land
python check_lanes.py --file B14       # who else touches this item's files
```

Three things that are not obvious and will cost a merge if guessed:

- **B1 and B2 look disjoint and are not.** Different files, but `options_universe.py` imports
  `options_backtest.py` and `options_fill.py`. Clean merge, untested combination.
- **PANEL and FACTORS are not independent lanes** — `fundamental_panel.py` imports `factors.py`,
  `settings.py` and `cross_sectional.py`. Only specific pairs are safe; ask the validator.
- **The free parallelism is in the 37 items that modify no existing file**, plus `options-bot/**`
  (8 items, shares nothing with the main tree), plus the miner, plus infra. Four to six live lanes
  without ever contending for `fundamental_panel.py`.

If a session solves an item differently from the audit's proposed implementation, update its entry in
`valquo_audit_items.json` — the map is a working file, not a fixed artefact.

---

## Hard rules

- **Full universe only.** Verdicts come from the ~2,710-name equity panel and the full mined options
  universe. Subsets are smoke tests and must be labelled as such. Note that item **B12** shows every
  historical "800 largest names" result was an *alphabetical* slice — re-check any figure you inherit
  from that era before citing it.
- **One change per run.** Several catalogue items are A/B panel comparisons that differ in exactly one
  column. Keep it that way.
- **Report the null.** A clean rejection is the deliverable. The project's hit rate is roughly one
  adoption in eight and that is fine.
- **Do not re-open** anything on the do-not-reopen list in Part XV without a new mechanism or new data.
  A different parameterisation is not a new reason.
- **No new paid data** until the free tests that would justify it have run. The gating logic is in
  Part VI; **D1** (Sharadar direct at $29/mo — check the current Nasdaq Data Link bill) is the one
  action that likely *saves* money and should be checked regardless.

---

## What to write back

Create `HANDOFF_edge_audit.md` and append per item, in the project's existing style:

```
## <ID> — <title>
Committed threshold (written before the run): ...
What was run: exact command, universe, date range, n and n_eff
Result: the numbers
Verdict: ADOPTED / REJECTED / NULL / INCONCLUSIVE (underpowered) / SUPERSEDED
Why: mechanism, not just the number
Follow-on: what this unblocks or forecloses
```

Cite the catalogue ID in every commit message and every result so the ledger stays traceable.

Then update, in the same pass:

- **`CLAUDE.md`** — any claim the audit shows to be unsupported. Specifically: the `low_risk`
  "confirmed out-of-sample" language (item **B8**), the Deflated Sharpe framing (**B9**), and the
  headline metric's description (**R1**) once it has an answer.
- **`BACKTEST_RESULTS.json`** — stamp the actual date range, period count and universe size on every
  block (**B22**, **M6**). Two blocks currently disagree about what window they cover with no marker.
- **`VALQUO_MASTER_ROADMAP.md`** — the "research phase is essentially CLOSED" verdict is contingent on
  results the audit reopens. Revise it when R1, R2 and X7 land, not before.

---

## Start a research log (item M1)

One append-only file, one row per pre-registered test: date, domain, hypothesis, universe, metric,
threshold, verdict, source doc, stable ID. Populate it retrospectively from the handoff corpus — the
audit's own ledger reconstructed ~146 prior tests and section A of that work is most of the way there.
Then wire the row count into `_deflated_sharpe` as `N` and into `_trials_haircut`.

Without it, every multiple-testing claim in the project is computed against a denominator of 8.

---

## When you are done with a wave

Hand back to a **fresh session with no project context** for a cold re-audit — code against record, the
same way this one was produced. That distance is what found these items; a session that has been living
inside the project's self-description is the least likely thing to catch the next one.
