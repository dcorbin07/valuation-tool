# VALQUO — Action Plan (execution layer over the Bible, rev 2)

**The Bible is `VALQUO_EDGE_AUDIT.md`** (rev 2, 108 items: B1-26 / R1-10 / X1-8 / S1-28 / O1-26 / U1-8 /
C1-7 / P1-5 / D1-10 / M1-6). **The executing briefing is `PROMPT_edge_audit_execution.md`** — the auditor
wrote it, it carries the pre-commitments + Step 0 + the 8-session order + the write-back format. Do NOT
duplicate either. This doc does what neither does: the **foundation reconciliation**, the **agent/lane map**,
the **one parallel bot** worth running, the **product track**, and what is **superseded**.

Load-bearing order, restated: **Part I corrections → Part II re-derivations → everything else.** Running new
tests on the current measurement layer wastes the runs.

---

## STEP 0 — the foundation, before a single correction (this is the blocker)

**0a · Reconcile the tree — DON, on your machine, first.** The tree is 332 files modified, 35 untracked, 16
commits behind `origin/main`. Part I edits `options_universe.py`, `options_backtest.py`, `fundamental_panel.py`,
`factors.py`, `screen.py`, `paper_track.py` — all in that modified set. Starting on it produces a merge mess
that looks like a bug. In PowerShell, in `valuation-tool`:

```
git fetch origin
git reset --hard origin/main
git status
```

The 332 "modified" are line-ending/stale-checkout artifacts (an earlier `git diff` showed zero real content
change) — `reset --hard` clears them and does NOT touch the gitignored audit/prompt files. If `git status`
still shows a wall of modified files afterward, it's a `core.autocrlf` config issue — tell me and I'll fix it.

**0b · Widen the CI gate (C7) — the main agent's FIRST landed change.** `land-agent-branch.yml` auto-merges
`worktree-*` behind `tests/test_edge.py` ONLY; 14 of 15 suites don't gate a deploy, and Part I touches files
that suite doesn't cover. This must land before any correction (or any parallel bot) auto-lands, or a broken
change ships green.

**0c · Sharadar extraction — parallel bot, time-limited (see below).** The subscription is lapsing; the
EVENTS legend / restatement behaviour / freeze-reproduction can only be captured while the key is live.

**Don, out of band:** **D1** — check your Nasdaq Data Link bill against Sharadar's new direct **$29/mo bundle**
(likely saves money and kills the access-ending problem; confirm the licence covers a commercial SaaS).

---

## POSTURE — PRIVATE / PERSONAL USE ONLY (Don, 2026-08-03)

**Valquo is a personal research tool for Don alone. It is not a commercial product and must not present as
one.** Reason: ThetaData Individual is "personal use only, no redistribution or business use" (Business is
$1,600/mo) and Sharadar's individual terms are similar. One user, no commercial activity, no ambiguity.

Implications for the plan:
- Public site, signup, Stripe/billing, pricing and "Premium" framing are **gated off** behind a reversible
  `private_mode` flag (`PROMPT_appfixer_private.md`). Nothing deleted — flipping back is one setting.
- **The forward paper track keeps running privately.** The "public live track record" moat is DEFERRED, not
  lost: the track accumulates now, and can be published on day one if Valquo ever goes commercial with the
  right licences. That is better sequencing than publishing a two-week curve.
- **Phase 9 / P-series product items are DEFERRED** (landing page for visitors, U4 one-decision-object as a
  customer surface, capacity/crowding). Research, corrections and the track are unaffected — they are for Don.
- Data rule going forward: no raw ThetaData or Sharadar data on any user-visible surface. Derived statistics
  are a separate category; report them honestly but keep them behind the owner gate while private.

## NO-SKIP RULE (Don, 2026-08-04) — HARD

**Every one of the 134 catalogue items gets run.** Nothing is closed on a manager's judgement that it is
"probably low value." Worst case we spend time and learn nothing; best case we find real value. Time is not
the constraint. Cowork proposed formally closing most of the O-series after five independent options
rejections — **that proposal is overruled and must not be re-raised.**

**The one thing this makes MORE important, not less:** running ~134 pre-registered tests guarantees some will
look positive by chance. That is exactly what audit item **M1** (the append-only research log with a real
trial counter) exists to control, feeding the true `N` into the Deflated Sharpe and the Harvey-Liu-Zhu
hurdle. **Running everything raises M1 from housekeeping to a requirement.** Schedule it before the long
tail of S- and O-series items, not after.

## SEQUENCING RULE — HARD. Cowork violated this once (R1 in Session 2); it does not happen again.

**Before handing out ANY prompt, state these three things in the message to Don:**
1. **Which audit session the item belongs to** (Part XV session table).
2. **Whether the PREVIOUS session is complete** — verified against `HANDOFF_edge_audit.md`, not assumed.
3. **The item's `needs first` list** from `VALQUO_AUDIT_DEPENDENCY_MAP.md`, and whether each has landed.

**If the previous session is not complete, the item does not run.** No exceptions for "it looks unblocked."

**`check_lanes.py` answers ONE question: will two agents collide on files?** It does NOT answer "are this
item's inputs correct yet?" Collision-safe is not dependency-ready. Conflating those two is exactly the
error that put R1 on an uncorrected panel.

**Out-of-band work** (live production bugs, product/UX, data pulls) is allowed outside the session order —
but it must be *named as out-of-band* when handed over, so it is never mistaken for progress through the
catalogue.

## AGENT LIFECYCLE RULES (Cowork decides; Don just executes)

### Reuse the agent (paste a prompt into the existing terminal)
- Idle, and the next task is the **same lane** it just worked.
- A direct continuation of a multi-session program (e.g. the edge-audit sessions, resumable mining).
- Nothing about the project's premises has changed since that session started.

### Kill it and start FRESH
- It finished a whole **wave or program** — natural boundary, handoff written, state has served its purpose.
- **Project premises shifted under it.** (2026-08-03 example: B1 fixed re-opened the options verdict; the
  private-use decision; the 2012 small-cap story disconfirmed. A session started before those carries stale
  assumptions.)
- Session is very long / spans several unrelated tasks — accumulated drift.
- Next task is in a **different lane** — fresh context beats re-pointing a loaded one.
- It errored, got confused, or behaved oddly.
- **Never mid-task.** A session part-way through an item holds reasoning the handoff doesn't capture.

### Reuse an EXISTING prompt file vs write a NEW one
- **Existing:** the file already covers it — multi-session programs (`PROMPT_edge_audit_execution.md`),
  standing resumable jobs (`PROMPT_mine_data.md`, `PROMPT_greeks_enrich.md`, `PROMPT_miner_remine.md`).
- **New:** no file covers it; OR results changed what should happen next; OR the item needs thresholds
  pre-committed in writing before the run (every gated test).

### Consult the CURRENT auditor vs commission a NEW one
- **Current auditor** — it knows all 134 items, the dependency map and the tooling. Use it for: what an item
  means, sequencing questions, threshold intent, updating `valquo_audit_items.json` / `check_lanes.py` /
  the map as things land, and scoring its own predictions against results.
- **NEW auditor** — **its value as a *cold* reader is spent.** It now knows the project, which is exactly the
  bias the first audit existed to defeat. A genuine re-audit (code against record, fresh eyes) needs someone
  with no context. Commission one **after Part I + Part II land** — that is the wave boundary the auditor
  itself specified — and again before anything real-money.

## Standing decision principle (Don, 2026-08-03)

At every fork — data source, contract choice, architecture, product — default to the option that makes Valquo
the **best** version, not the cheapest or the fastest. **Time is never the constraint; money can be.** Pause to
discuss only when it is a *marginal* edge for a *real* cost (e.g. a paid data upgrade); otherwise always choose
best. This governs the whole catalogue, especially the D-series data calls (ORATS on O2/O6 hit, re-mine past 90
DTE for O15, etc.).

## Lane discipline — VERIFIED, not inferred (2026-08-03)

The auditor shipped `VALQUO_AUDIT_DEPENDENCY_MAP.md` + `valquo_audit_items.json` + **`check_lanes.py`**, built
from the real import graph. **Before assigning any two items to different agents, run
`python check_lanes.py <ID> <ID> ...`.** Do not reason about it by hand — my hand-derived model was wrong:

- **Textual disjointness is NOT sufficient.** B1 and B2 share zero files, merge cleanly, and can still break —
  `options_universe.py` imports both `options_backtest.py` and `options_fill.py`. B1 changes what
  `chain_summary`/`pick_contract` receive; B2 changes what they do with it. Nothing flags that.
- **`fundamental_panel.py` is the bottleneck: 46 of 134 items touch it.** It is single-owner, always. PANEL and
  FACTORS are NOT independent lanes (the panel imports `factors.py`, `settings.py`, `cross_sectional.py`).
- **Global events, never parallel tasks:** `statistics.py` (10 importers across both research lanes) and
  `options_tracker.py` (18 refs / 10 importers; B5 and B15 both change it).
- The catalogue is **134 items**, not 108.

**Where the parallelism actually is:** 37 FREE items (modify no existing file), the whole `options-bot/**`
codebase (8 items, zero shared files), the miner (2, long jobs), infra (4), LIVE (4), datasets (3).

## The lanes

- **Main research agent** (pipeline/research terminal) → runs `PROMPT_edge_audit_execution.md` end to end,
  sequentially. This is deliberately **one traceable owner** for the corrections + re-derivations — accuracy
  and a clean ledger beat speed here, and the auditor designed it that way (it even hands back to a fresh cold
  session between waves). First: 0b (C7). Then the urgent paper-track fix (B5 + P4) before the track grows.
  Then Sessions 1-8.
- **Sharadar/data bot** (parallel, `PROMPT_sharadar_extract.md`) → 0c + D10 + C5. Disjoint from every Part I
  file, and time-critical, so it's the one thing worth parallelizing now. Its commits are docs/reports, low
  risk even before C7.
- **App-fixer** (product lane) → continues the product track below; it does NOT touch the correction files.

**Recommendation: keep the corrections single-owner** (main agent) + the Sharadar bot in parallel. Do not fan
the Part I corrections across agents — they edit overlapping core files and the whole point of Step 0 is to
avoid a merge mess.

---

## Order of work (from the execution prompt / audit Part XV)

| Session | Work |
|---|---|
| 0 | 0a reconcile (Don) · 0b C7 CI gate · **B5+P4 paper-track (urgent)** · kick off the Sharadar bot |
| 1 | Cheap corrections: B1, B3, B10, B12, B14, B15, B16, B18, B19, B20, B24, B26, B9-relabel — B1 re-run overnight |
| 2 | B2, B4, B7, B11, B13, B17, B21, B22, B23, B25; begin B6 (panel truncation) |
| 3 | **X7 placebo + X2 grid-offset** — establishes the noise floor every threshold is currently uncalibrated against |
| 4 | **R1 factor-adjusted alpha + X4**, alone. Then R9, R10. **Do NOT start Parts III-V until R1 returns** |
| 5 | R2 + R3 (corrected options re-run under clustered inference), R7 committed first, O20 folded in |
| 6 | U7 + X3 — one-line probes that kill or promote bigger items |
| 7 | **U2 (options→stock), then U1 (stock→options), then U6** — the unification |
| 8+ | O1, S20, S21, X1, S2, S19, X8, O2, O6, S1, S10, O15, C1-C4, P1, P4, S5 — descending value |

The two decisions that reshape everything: **R1** (is the equity edge alpha or factor exposure) and
**B1→R2** (is the options entry really worse than random or was that the price bug). Nothing new is worth
building until those two return.

---

## Product / launch / ops track (parallel, app-fixer; the audit's P-series + our roadmap)

- **B5 + P4 paper-track fix is the exception — it's urgent and I've put it at the front of the main agent**
  (the track drops losers and measures on the wrong basis; every day uncorrected is discarded).
- **U5 tax-aware allocation** — already measured (Roth +17.4% vs taxable +4.86%; a 3.6× lever). XS to decide.
- **U4 one decision object** (roadmap #33) — gate on U1/U2, don't ship over two disconnected engines.
- Phase-9 UX continues; options copy stays "convex ~37%-hit = expectancy, never win-probability."
- **Autotrade (Tradier, Roth) — last, gated on the corrected forward track.**

---

## Superseded / retired

- `OPTIONS_DEEP_RESEARCH.md` + the entry-fix → folded into audit Part IV (O1/O13), and blocked on B1.
- `VALQUO_MASTER_ROADMAP.md` "research is closed" CURRENT-STATE → wrong; corrections re-open it. Roadmap now
  points here; revise its verdict only after R1/R2/X7 land.
- "WRDS is the #1 lever" → dead end (D7); **U2 replaces it**.
- Do-not-reopen list: audit Part XV (unchanged mechanisms).

---

## What Cowork (me) can and cannot do here, honestly

The code corrections run through Code agents on a **reconciled** tree — I will NOT hand-edit the primary
checkout, because git writes from this side are what produced the line-ending artifacts inside those 332
"modified" files in the first place. What I own: this plan, the roadmap integration, the parallel-bot briefs,
the Discord/track monitoring, and translating each returned handoff into the next move.
