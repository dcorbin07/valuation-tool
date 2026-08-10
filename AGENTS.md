# AGENTS — which terminal runs what

Maps each of your Claude Code terminals to its lane, current status, and the prompt to paste next.
New prompts are named `PROMPT_<agent>_<task>.md` going forward so the target terminal is obvious.

## THE SIX REAL TERMINALS — use these names, they are what exists

Verified against Don's client 2026-08-06. **There is no "edge" terminal — `pipeline builder` is that
lane.** A previous version of this file proposed renames and then referred to the new names as though
they were terminals. They are not. Renaming is Don's to do in his client; until he does, **these are
the only valid targets:**

| Terminal | Owns | Notes |
|---|---|---|
| **pipeline builder** | `valuation/edge/**` | Owns the `VALQUO_EDGE_AUDIT.md` session order. Only one terminal may ever hold this lane. |
| **data miner** | `theta_bulk.py`, `oi_remine.py`, `oi_coverage_audit.py`, `data/options/**` | Only one terminal may hold `data/options/**`. |
| **greeks agent** | `valuation/engine/**`, `valuation/data/**`, `valuation/screener/**`, `screen.py` | Name is historical; it is the valuation-engine lane. |
| **app fixer** | `valuation/web/**`, `valuation/report/**`, `valuation/saas/**` | |
| **options bot** | its audit lane (C1–C6, O8, O9) is complete | free |
| **r1** | `scripts/factor_alpha.py`, `tests/test_factor_alpha.py` | free, but its open items (R4–R8, B8, M1's re-run) are all in `valuation/edge/**` — **blocked until pipeline builder frees that lane.** |

**Mining in parallel — what is and is not supported.** `oi_remine.py --shard i/n` is sharded and its own
help says **run at most 3** (ThetaData's concurrency ceiling). Two terminals on two shards is safe.
`prefetch` (breadth mining) has **no shard parameter** — it uses in-process thread workers, so two
terminals running the same breadth command duplicate work and race on the same files. Shard the re-mine;
keep breadth on one terminal unless the symbol list is split by hand.

**Mining in parallel — what is and is not supported.** `oi_remine.py --shard i/n` is sharded and its own
help says **run at most 3** (ThetaData's concurrency ceiling). Two terminals on two shards is safe.
`prefetch` (breadth mining) has **no shard parameter** — it uses in-process thread workers, so two
terminals running the same breadth command duplicate work and race on the same files. Shard the re-mine;
keep breadth on one terminal unless the symbol list is split by hand.

## LIVE ASSIGNMENTS — 2026-08-05 (paste these now)

| Terminal | Paste this | What it is |
|---|---|---|
| **greeks agent** | `Read PROMPT_consolidate_publication.md and execute it.` | **CONSOLIDATE-1.** Root cause, not a bug fix. One publication decision, computed once; `screen.py` records the refusal instead of erasing it. |
| **options bot** | `Read PROMPT_build_the_ledger.md and execute it.` | Builds `VALQUO_LEDGER.md` — one row per audit item. New files only; collides with nothing. |
| **app fixer** | `Read PROMPT_web_stale_cache.md and execute it.` | Small, and labelled small: `_LAST` untimed cache means an export's "As of" can disagree with the page. Then the lane is clear. |
| **pipeline builder** | *(working)* — hold `PROMPT_edge_session5_closeout.md` | Give it the closeout when it reports done. Session 6 does not open until Session 5's five open items are closed. |
| **data miner** | **DO NOT PASTE — WAIT.** | PID 35664 healthy, 58/100, ~6h left, rescan → depth report → handoff already queued. `PROMPT_miner_audit_then_breadth.md` waits for the pull to exit; only its breadth half is new. |
| **r1** | **nothing — idle on purpose** | Every open item in its lane is inside `valuation/edge/**`, which pipeline builder holds. Idle beats invented work. |

**CONSOLIDATE-2 (the composite: three scoring functions, none reproducing the backtest) is next, and it
is BLOCKED** — it touches `fundamental_panel.py`, `factors.py`, `settings.py`, `screen.py`, i.e. the edge
lane. It goes to whichever terminal is free once pipeline builder lands Session 5's closeout.

### Done 2026-08-05 (landed on origin/main)
- `PROMPT_scenario_cards_follow_headline.md` → app fixer, `c5df3e6`. Seven surfaces were republishing
  the withheld valuation, incl. the 93/100 gauge. All refuse; figures stripped server-side.
- `PROMPT_dcf_terminal_degeneracy.md` → greeks, `50c22d7`. **NULL** on all pre-registered candidates;
  found the real cause (contaminated analyst growth input) and fixed that instead.
- `PROMPT_growth_input_and_score_contamination.md` → greeks, `ad0ee6c`. **194 names were silently
  using an earnings growth rate as a revenue growth rate.** Score no longer eats withheld valuations
  (KSPI 93 → 50). Candidate A shipped on coherence.
- `PROMPT_appfixer_exports_and_index_tab.md` → app fixer, `c935c94`. Exports refuse in-document;
  Index tab stays owner-only and is relabelled. **Found the public fair-value leak.**
- **Session 5 (R2, R3, R7, O20)** → pipeline builder, `0fb22a8`. The options entry signal is dead and
  the finding survived the correction. Open: run the control at ≥5 seeds (a single seed flips it).

Both are **OUT-OF-BAND** (not `VALQUO_EDGE_AUDIT.md` catalogue items) and touch live product code only —
`valuation/web/**` and `valuation/engine/**` respectively. Neither collides with the edge-audit lane
(`fundamental_panel.py`, `factors.py`, `settings.py`, `screen.py`) or with each other. Run both at **high**.

Either prompt can be run by any free terminal — each names its own required reading — but the greeks
agent already ran `PROMPT_live_data_bugs.md`, which is where the DCF evidence came from.

**The table below is as of 2026-08-02 and its statuses are stale.** Confirm against `git log` and the
`HANDOFF_*.md` files before trusting any row in it.

| Terminal (your name) | Lane (files it owns) | Status | Paste next |
|---|---|---|---|
| **paper tracker** | forward paper-track vs SPY, Tradier **sandbox** fills, `record_outcome` | RUNNING | `PROMPT_paper_track.md` |
| **sector neutral** | sector-neutral wiring in `fundamental_panel.py` + re-backtest | RUNNING | `PROMPT_sector_neutral.md` |
| **security** | secret-exposure audit (done) → now the FIXES | ▶ RUN NEXT | `PROMPT_security_fixes.md` |
| **app fixer** | live web app: universe / display / Index | ▶ RUN NEXT | `PROMPT_broker_fundamentals.md` |
| **data miner** | ThetaData options cache (`data/options/`) toward ~1,000 names | RESUMABLE | `PROMPT_mine_data.md` (re-run to continue if idle) |
| **greeks agent** | options greeks/GEX derived layer (`data/options_derived/`) | DONE for 82 names | `PROMPT_greeks_enrich.md` (re-run as the miner grows) |
| **pipeline builder** | options edge: signals / live scan / backtest | PARKED | 22b small/mid single-leg backtest — data-gated on the miner |
| **growth valuation** | fair-value engine (`valuation/engine`, `fairvalue.py`) | PARKED | promote EV/Sales to a panel factor — after sector-neutral lands (same file) |
| **lazy prices** | 10-K/10-Q language-change dataset (`data/filings/`) | DONE | #28 does-it-predict test — gated research, when Don's back |
| **sharadar freeze** | final Sharadar data freeze (`data/backtest_freeze_2026-08/`) | DONE | — |

## Notes
- **paper tracker** and **sector neutral** are already running (Don launched them).
- **pipeline builder** and **growth valuation** are free but intentionally parked — their next tasks
  are blocked (one on more mined data, one on the sector-neutral file), not on effort. Don't invent
  make-work; pick them up when unblocked.
- Every agent writes its full end-of-session report to its own `HANDOFF_<name>.md` — Cowork reads those
  directly, so Don never screenshots. (Being made a standing rule in CLAUDE.md by the security agent.)
