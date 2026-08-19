# VALQUO_MASTER_AUDIT_ULTIMATE.md — the merged master audit (#3 + independent second pass)

**Auditors:** two cold passes, no history with this codebase. Pass A = the Opus session
(`VALQUO_MASTER_AUDIT.md`, MA1–MA35). Pass B = an independent seven-lane re-audit run **blind to
Pass A**, then reconciled against it. **Date:** 2026-08-14. **Tree:** `origin/main`
(Pass A @ `67f995e`; Pass B @ `3893d6b`, four commits later — no material code delta between them).
**Method:** strictly read-only. Every finding is quoted code, a measured command, or is marked
HYPOTHESIS / UNCHECKABLE. Pass B verified each of its own new items against the code before it was
admitted here.

> **What this document is.** The commission was run once by an Opus session, which produced a
> strong 35-item audit. This session was asked to *"go through the whole audit before looking at
> what the Opus session created, then compare and add anything and make an ultimate audit."* That
> is exactly what happened: seven independent lanes (research record, backtest engine, live
> product + security, forward track + continuity, options subsystem, factory/process, external
> literature) ran blind, and only then were diffed against Pass A. **This file is the union.** It
> does not reproduce Pass A's 35 items — those stand as written in `VALQUO_MASTER_AUDIT.md` and
> are referenced by ID. It records (1) which of them the independent pass **corroborated**, (2)
> **25 new verified items MA36–MA60**, and (3) two **severity/labelling corrections** to Pass A.
> The merged machine-readable set (`valquo_master_audit_ultimate_items.json`) carries all 60.

---

## 0. The gate — re-confirmed independently

Board quiet: no ledger row carries a live `IN PROGRESS` (the one string match, `B13`, reads
`PARTIAL - BLOCKED ON DATA`, and its own cell says *"NOT IN PROGRESS"*). Every remote
`worktree-*` branch is an ancestor of `origin/main`. `worktree-audit3-master` (Pass A's own
branch) is 514 commits ahead of the local checkout and 1 behind `origin/main`'s tip — i.e. Pass A
landed cleanly. The local checkout `C:\Users\donni\Downloads\valuation-tool` is **514 commits
behind `origin/main` with one unpushed commit `41d7b12`** (the dated `PT-WRITER` refusal note,
stranded since 2026-08-10). Pass A measured 508; four days and a few landings later it is 514.
**This is Pass A's MA20, re-measured and worse, and it remains the single most important
operational finding in the audit.** Both passes audited `origin/main`, not the stale local tree.

I also cleared a stray `.git/index.lock` the restricted bridge shell created merely by running
`git status` (renamed to `_to_delete/`, since the bridge cannot unlink) — itself a small instance
of Pass A's MA20/factory concern that the shared checkout is fragile under concurrent tooling.

---

## 1. Honest one-page summary

### The three most valuable things in the merged audit

**1. The strongest gate in the project protects the number nobody trades; the weakest gate
protects the number every user sees — and the plumbing around it leaks in both directions.**
This is Pass A's central thesis (MA1–MA3: a monthly cron can re-tune the *live* composite through
an uncalibrated 1.64σ gate that never compares to the incumbent, with no vintage closed and no
register). The independent pass did not touch the learner but arrived at the *same seam from the
other end*: the forward paper track that is supposed to adjudicate the live product **has recorded
zero rows on run #2, ever** (MA18, and Pass B argues it is under-rated at MEDIUM — see the
correction below), and the live options record **blends a formally-retired pre-B1 era into the
expectancy every user sees** (MA37, new). The verification effort has been aimed at the research
programme; the product and its evidence trail are where the leaks are. Two independent cold passes
converging on this is the finding.

**2. Two irreplaceable data assets sit outside the backup, and two live records can be silently
corrupted without anyone noticing.** Pass A: `data/options_ticks` (4.72 GB, not lawfully
re-purchasable) and `data/free_analysis` (the per-draw evidence for ~40 studies) are outside the
backup allowlist (MA15/MA16); `N`, the denominator of every significance claim, has no
tamper-evidence (MA13); the contract-bound history is rewritten non-atomically and drops unknown
columns (MA4). Pass B adds the mechanism by which the *published* record silently drifts: a
worthless-expired options position is **censored out of the live track forever** (MA36, new), and
`/api/hotstocks?top=-1` **defeats the per-tier paywall** via a negative SQL `LIMIT` (MA50, new).

**3. Every calibrated bar was calibrated at N=84 and last checked at N=129; N is 224 today, the
project's own curve says the null has moved, and the arithmetic that would re-check it depends on
the one directory the backup skips.** Pass A's MA19/MA20 staleness map, unchanged and
corroborated. Pass B adds that the same "computed-but-never-read" disease now has fresh instances
in the *engine that produces the record* (MA39: the degraded-run scanner watches 6 of 13 result
blocks; MA40: two whole result blocks reach no reader), so the instruments meant to catch a broken
run are themselves partially blind.

### Overall state, in one paragraph

The two passes agree almost entirely, which is itself evidence: this is the most rigorously
self-audited codebase either auditor has read, its statistical reasoning is not where the failures
live, and its research record is genuinely excellent (the trial counter reads 224 equity trials
against a shipped artifact that reads 224; `sum(by_domain)` = `trials` exactly; PBO 0.7333 and DSR
0.7863 are reported honestly against their "want" thresholds; the record already retired its own
over-claims). Every failure of consequence is in the **seam between a correct in-process
computation and the thing that ships, records, or protects it** — Pass A's generalisation ("every
guard is correct in-process and blind at its output boundary"), which the independent pass
confirmed and then extended with nine new instances of the exact same shape in the engine, the
options tree, and the live API. The single most important *operational* fact is unchanged by
either pass: the local checkout is 514 commits behind, the forward track is not being written, and
the contract's clock is running anyway.

### What could NOT be checked (both passes)

Production state (Render env, the `learned_config` table, whether MA1 has ever *fired*); the
licensed `data/` directory in any form (no export, no options cache, no `free_analysis` present in
either worktree — every study number is quoted from the record, not re-measured); the D: drive's
actual contents; and any re-adjudication of a research verdict (out of scope, and neither pass did
it). Pass B additionally could make no network requests, so every live-API finding (MA50–MA53) is
a code trace, not a live probe.

---

## 2. Reconciliation with Pass A (MA1–MA35)

### 2.1 Independently corroborated (raises confidence — these were found twice, blind)

| Pass A item | Independent lane that re-derived it | note |
|---|---|---|
| **MA7** `/api/value` + `/api/rank` uncapped vendor spend | security lane (N1) | same files, same 25×-fanout reasoning, independently |
| **MA9 / MA10** demo token on a public page; one `ADMIN_TOKEN` over product *and* record, bypasses the limiter | security lane (N2, N6) | Pass B adds MA52/MA54 as adjacent gaps |
| **MA11 / MA12** auto-land = unreviewed code execution to `main`; unpinned deps | security + factory lanes (N5) | corroborated |
| **MA14** fail-closed covers absence, nothing covers wrong-but-plausible on the live path | security lane (N3, N9) | independently, with the beta-drift precedent |
| **MA18** the bound forward track has no writer and the clock is running | continuity lane (F1) | **Pass B disputes the severity — see 2.3** |
| **MA19 / MA20** X7 floors stale at N; shared checkout drift | (staleness given as evidence; factory lane F6) | re-measured at 514 |
| **MA22 / MA23** `CLAUDE.md` outgrown its job; `edge/` mixes engine + finished studies | factory lane (F8, X6) | corroborated; Pass B's deletion list is more granular (MA59) |
| **MA24 / §12** very few wrong rejections; the "stop looking" list | research + external lanes | the external lane independently reached the *same* stop-list (ML combiner, regime/vol overlays, VRP) from the 2023–2026 literature |
| **MA25** a liquidity measure exists in `bars/`, contra `B13`/`S7` | (not contradicted by any lane) | accepted as a correct correction to the record |
| **MA31** Cremers–Weinbaum matched-strike parity is the largest un-run item | external + research lanes | independently nominated as the #2 highest-EV untested item |

That ten of Pass A's items were re-derived blind by a differently-organised second pass is the
strongest evidence that Pass A is sound. **Pass B found no factual error in any MA1–MA35 item it
could check.**

### 2.2 New items the independent pass adds — MA36–MA60 (§3–§8 below)

25 verified items across six mandates. Every one carries a `file:line`, a measured or quoted
evidence line, and (where Pass B could run it) a one-line verification.

### 2.3 Two corrections to Pass A

**Correction 1 — MA18 is under-rated at MEDIUM; the evidence supports HIGH.** Pass A files
"the bound track has no writer" as MEDIUM and notes the clock is running. The continuity lane
established three facts that, together, make it HIGH: (a) **run #2 has recorded zero rows across
its entire life** — vintage register reads v1 VOID 2-of-6, v2 0-of-0, v3 0-of-1 (missed
2026-08-12), v4 OPEN 0-of-0; (b) the writer PT-WRITER **failed its one real attempt** on
2026-08-10 (`41d7b12`) and that failure note is the *unpushed* commit on the diverged local main,
so the fix that landed 2026-08-14 (`index_mark.contract_row`) **does not exist on the machine
PT-WRITER runs on**; (c) a single voided August (one missed row uncured within 3 trading days of
month-end) is 16.7% of elapsed months at the 2027-02 gate, above the 10% ceiling at which the
meter refuses to render its own first datapoint. A blocked row on a five-year clock is a decaying
asset, and it is the only finding in this audit that **cannot be recovered later**. Severity: HIGH.

**Correction 2 — Pass A's MA26-C ("withhold state is information") is correct that the state is
not testable point-in-time, but it stops one step short.** The *withhold state* is forward-only,
yes — but the **valuation engine's continuous outputs** (the PIT fair-value gap `ln(fv/price)` and
the lens-disagreement width) **are** on the exact 69-date S23 panel (108,241 rows, 93.9%
coverage, offline), and have never entered a cross-sectional signal test as a *ranking* signal —
only as an exit trigger (S23, NULL) and an entry veto (S10, rejected). That is a testable
combination and a concrete equation candidate (MA55, new), distinct from Pass A's KNS-ridge
proposal (MA27).

---

## 3. MANDATE 2 — CODE (new items)

### MA36 — HIGH — The forward paper track strands worthless-expired options open forever; the −100% tail is censored from the live record
**File:** `valuation/edge/paper_track.py:619-625` · **Class:** guard-blind / one-sided record ·
**Regression from:** B5-lesser.

On any exit trigger, `if not (bid and bid > 0):` the loop records `"{reason} deferred: no bid …"`
and `continue`s. `_exit_decision` keeps returning `"expiry"` after expiry, but **no path in the
file settles a past-expiry position at intrinsic** (measured: `grep -c intrinsic paper_track.py`
→ **0**). A long option that decays to no-bid — precisely the worthless case — is deferred every
cycle until the contract ceases to exist, then sits `state='open'` forever. `_stats`/`paper_report`
count only `status='closed'`, so **winners and quoted losers are scored and total losses are
dropped** — the opposite of the backtest it validates (`options_backtest.py:29`: "expire worthless
settle at intrinsic and post −100%. They are not dropped."). The B5-lesser repair, correctly
refusing an unmodelled market-order fill, stopped one line short of settling the no-bid case at
intrinsic. **Blast radius:** the project's #1 remaining validation, and every backtest-vs-live
comparison built on it, is optimistically biased. **Verify:** stub broker returning `{}` for a
past-expiry OCC; the row never leaves `open`, `record_outcome` never fires. **Fix shape:** on
`reason=="expiry"` with no bid and expiry past, settle at `intrinsic(right, strike, underlying)`.

### MA37 — HIGH — The 2026-08-13 options record reset is invisible to every statistical consumer except the scream-track tab
**Files:** `valuation/edge/options_tracker.py:227` (`scorecard`), `options_paper.py:63`
(`paper_report`), `options_tracker.py` `tuning_candidates` · **Class:** two-recorder / epoch-blind.

`record_epoch` is stamped on every row (`options_tracker.py:96`) and the reset created a new epoch
`reset-…`, but only `scream_log.records()` filters on it (`scream_log.py:144`). `scorecard` runs
`SELECT * FROM option_alerts WHERE status='closed'` with **no epoch filter**, and `tuning_candidates`
+ `paper_report` (`live_since = min(alert_ts)` over all rows) inherit the blend. The reset's own
register says the archived era "predates the corrected alert stack (B1 price basis, C-series
fixes)" — yet it still drives `/api/options-scorecard`, `web/hero.py`, `web/unified.py`, and the
tuning loop. **A tuning loop is learning from a record the project formally retired.** Every
expectancy Don sees outside the scream-track tab blends two eras. **Verify:** log+close an alert,
`SL.reset_record()`, log+close a second → `scorecard` reports n_closed 2 (blend). **Fix:** add
`WHERE record_epoch = current_epoch(store)` to scorecard/paper_report/tuning, as scream_log does.

### MA38 — HIGH — `chain_summary` ships an OI coverage fraction that no consumer reads, so the "unusual volume" alert inflates in the exact spans B4 degraded
**Files:** `valuation/edge/options_backtest.py:251-255` (producer) · `valuation/intraday/options.py:33`
(consumer) · **Class:** fixed-output-not-consumed / guard leaks at the boundary.

The B4 repair correctly sums `call_oi`/`put_oi` over known-OI rows only and ships
`call_oi_known_frac` — but `known_frac` appears **only in `options_backtest.py`** (measured: grep
across `valuation/` + `scripts/` finds no other reader). Meanwhile `intraday/options.py:33`
computes `cv/coi > 0.5 → +8 "Unusual call volume vs OI"` where `cv` sums **every** contract and
`coi` only the known ones. In the 11.4% of cache rows B4 degraded (106/111 names), the ratio is
inflated by ≈1/coverage, so the reconstruction fires alerts the module's own docstring
("reconstruction is STRICTER … fires fewer, never more") says it cannot. **Blast radius:** which
alerts the 22b/R2 books contain in degraded spans (divergence in both directions — AAPL 2020 zeroes
out and under-fires). **Fix:** scale `coi` by `1/known_frac`, or suppress the OI bonus when
`known_frac < ~0.9`.

### MA39 — HIGH — The degraded-run detector watches 6 of 13 result blocks, and `build_payload` never reads the error string the run recorded
**File:** `valuation/edge/results_file.py:138-149` · **Class:** guard-blind / fixed field list.

The scan iterates exactly six keys (`hold_until_exit, construction, walk_forward, cpcv, regime,
institutional_dependence`) — but B22 stamps **all 13** `RESULT_BLOCKS` with an error status on a
mid-diagnostics exception, and `build_payload` builds `payload["errors"]` **from scratch** (line
138) rather than reading `res["errors"]`. So an exception inside `costs`, `holdout_validation`,
`after_tax`, `benchmarks`, `book_configs`, `no_trade_band` or `factors_used` ships a canonical
`BACKTEST_RESULTS.json` with `errors: []` — which the file's own contract ("non-empty means
DEGRADED") reads as an active claim of health. The `"INCOMPLETE RUN —"` string main() builds is
silently discarded. **Verify:** `build_payload` on a `res` whose `costs` block carries
`status:"error: boom"` → `errors == []`. **Fix:** iterate all of `RESULT_BLOCKS`, and fold
`res.get("errors")` into the payload.

### MA40 — MEDIUM — B21's `sector_caps` block and the `walk_forward` parameter sweep are computed every run and reach no reader; the M6 tripwire is structurally blind to both
**Files:** `valuation/edge/fundamental_panel.py:4937` · `payload_schema.py:55-99` · **Class:** M6
recurrence (computed field dropped) introduced by an audit fix.

`sector_caps` (B21, comment: "measures it and ships the numbers") is absent from `results_file.py`,
`BLOCK_SPEC`, `RESULT_BLOCKS`, and the shipped JSON (measured: `'sector_caps' in json` → False).
`walk_forward` returns `{n_folds, param_folds, weights, params}` but the artifact carries only
`{adopt, candidates, n_folds, recommend, recommended_weights, verdict}` — the entire trade-parameter
sweep with its per-parameter adopt verdicts is dropped (measured). `BLOCK_SPEC` guards 7 of ~17
payload blocks, so the exact tripwire M6 built for these cannot fire. **Fix:** add both to
`BLOCK_SPEC`, or drop the computation.

### MA41 — MEDIUM — `walkforward.py` has no purge/embargo — the only splitter in the tree without one — and it feeds a live "Adopt" verdict
**File:** `valuation/edge/walkforward.py:36-58` (measured: `grep -c embargo` → **0**) · **Class:**
lookahead in a live-facing gate; compounds MA2/MA3.

Trains on `folds[:k]`, tests on `folds[k]` with adjacent dates, so the last training date's 63-day
`fwd_ret` overlaps the test window and `walk_oos_ic_optimized` is inflated; `adopt = walk_opt >
walk_base` has no SE and no haircut. Every sibling splitter embargoes (`_wf_folds embargo=1`,
`_cpcv_paths`, `loo_holdout.split`, `param_search.cpcv_index_paths`). Live caller `lab.py:88`
(`run_optimize`) prints "Adopt: adaptive weights beat baseline out-of-sample" and returns weights
refit on all data — the same live-weight surface as Pass A's MA1/MA3. **Fix:** embargo one fold, or
route through `_cpcv_paths`.

### MA42 — MEDIUM — `shadow_vintage.detail()` reads `months_paired` before anything writes it, so the shadow-pair status is frozen at 0 months forever
**File:** `valuation/edge/shadow_vintage.py:431-433` (verified: `out` built at 402-413 never sets
the key). `months = int(out.get("months_paired") or 0)` is always 0, the
`months >= MIN_MONTHS_FOR_ANY_VERDICT` branch is unreachable, and years into the live 4-over-3
pair the status will still say "0 complete paired month(s)." The function's docstring says it
exists to avoid a vacuous status; this is the vacuous failure inverted (vacuously stuck). **Fix:**
compute `months_paired` from `open_pairs()` before the read. Latent (the pair needs many months
before rendering) but silent.

### MA43 — MEDIUM — `ablation.paired_diff` pairs by position and silently truncates, while its docstring promises "the SAME periods"
**File:** `valuation/edge/ablation.py:87-90` (verified: `n=min(len(a),len(b)); a,b=a[:n],b[:n]`,
no dates). `alpha_series` returns `dates` precisely so alignment is checkable; `paired_diff` never
takes them. If a mid-series date drops from the 6-theme arm but not the 7-theme arm, every later
element pairs against the wrong quarter — with equal lengths there is **no symptom**, and the
pairing's whole point ("a good-market quarter cancels") fails silently. `construction_rerun.py:185`
already does this keyed by date. **Fix:** key on `dates`. Used by `scripts/x3_ablation_rerun.py`.

### MA44 — MEDIUM — Live vs reconstruction disagree on the front expiry on 0DTE days, and the docstring claims they match
**File:** `valuation/edge/options_backtest.py:228-237`. Docstring: "Uses the FRONT expiry, matching
the live provider which reads `expirations[0]`", but the code filters `e > asof` (strictly future),
while live `get_option_summary` takes `dl[0]` (`intraday/providers.py:168`) — on an expiry day
Tradier lists *today*, so live P/C volume, P/C OI and delta-picked `atm_iv` come from the dying
0DTE chain while the reconstruction reads the next expiry. Every Friday for weekly names.
**Blast radius:** alert-firing parity on Fridays (0.30 weight of the alert bar). Code asymmetry
CONFIRMED; live magnitude HYPOTHESIS (Tradier intraday behaviour). **Verify:** log
`expiry == today` occurrences in one Friday scan.

### MA45 — MEDIUM — `blackscholes.enrich_chain` solves IV from an unvalidated `mid = (bid+ask)/2`, biasing the term-slope gate
**File:** `valuation/edge/blackscholes.py:226-233` (no `bid>0`/crossed check, contrast
`options_greeks.enrich_frame:374-378`). A zero-bid ATM front row yields an IV from `ask/2`.
`chain_summary`'s ATM-IV walk and `options_live._atm_iv_bs → term_read` take the first solving
contract; the shipped term threshold is 0.0105 (one vol point), and an `ask/2` mid on a thin
pre-open front-expiry ATM quote moves front IV far more than that → term_slope biased positive →
the gate passes alerts it should suppress. Code-trace CONFIRMED; live frequency HYPOTHESIS.
**Fix:** reject `no_quote`/`crossed` rows before solving, as the greeks path does.

### MA46 — MEDIUM — Post-B15 the two options recorders define `pnl_pct` differently: forward track gross of commission, backtest net
**File:** `valuation/edge/options_tracker.py:151-152` (`pnl_pct = ex/entry - 1`, no commission)
vs B15's net `return_pct` in `options_fill.py:292`. Every future re-run of the reference
(`GATED_LATE_HALF_EXPECTANCY`) is net while live rows stay gross — a ~0.27pp/trade construction gap
on the live-vs-backtest axis, plus the paper broker's real sandbox commissions never enter recorded
P&L. **Fix:** subtract `2×COMMISSION_PER_CONTRACT×contracts` in `record_outcome`, or record both.

### MA47 — MEDIUM — `param_search.cached_panel`'s cache key uses `len(tickers)` for ticker identity — the B12 collision, re-encoded, against its own docstring
**File:** `valuation/edge/param_search.py:872-874`. Key =
`f"{len(tickers)}_{rebalance_days}_{lookback_years}_{horizon}_{inst_lag_days}"`; the docstring
promises it "covers everything that changes the panel." Not in the key: which tickers (the B12
alphabetical→by-cap collision at the same `limit`), the data vintage, and every panel-shaping env
toggle (`EDGE_GRID_OFFSET`, `EDGE_EV_POINT_IN_TIME`, `EDGE_AUDIT_B6_LEGACY_TRUNCATION`). No in-tree
caller today (latent), but this is the designated cache for the honest-search lane and the
docstring is a live false guarantee. **Fix:** hash the ticker set + vintage + toggles into the key.

### MA48 — MEDIUM — A current-year theta cache freezes at its mine date and `needs_pull` refuses to refresh it
**File:** `valuation/edge/theta_bulk.py:517,759`. `year_end = min(date(year,12,31), today)` clamps,
and `if os.path.exists(path): return …` treats a partial current-year file as cached forever (no
`.partial`/`.span` sidecar). Any study whose window extends into the mining year gets empty
`chain_on` slices for post-mine dates, uncounted. `ENTRY_END=2025-10-15` shields the shipped books
today; the trap arms the moment anyone mines into 2026. **Fix:** a `.span` sidecar + refresh when
`span_end < requested_end`. (Its sibling `thetadata_provider.chain_on` caches a transient feed
failure as a permanently-empty chain, `:158-163` — the "sticky missing" defect `theta_bulk`
documents fixing on its own side; near-dead, see MA59.)

### MA49 — LOW — A cluster of latent time-bombs and clamp-hides-garbage defects (bundled)
Five, each cheap, none live today: (a) `scripts/fetch_factors.py:299-303` hardcodes
`covers_through_2025` — from 2026 on a year-stale factor file passes the "pre-registered bar" and
`factor_alpha.factor_windows` silently drops the trailing panel dates (a verification bar that never
moves). (b) `valuation/edge/statistics.py:27` filters `None` but not NaN (contrast `_clean` at
:129), so a NaN return renders the DSR as a NaN "verdict"; `:76` `trial_sharpes and len(...) > 1`
raises on an ndarray. (c) `scripts/x7_reconcile.py:75` hardcodes `n_names = 9` where
`cpcv_validate`'s scheme list has 8 (double-counts `current-default`), so the reconciliation's
`n=8` curve point uses √(2·ln 9) not √(2·ln 8). (d) `scripts/factor_alpha.py:387` computes
`ex_b6_first_37` positionally regardless of `--corrected-panel`, mislabelling 37 healthy dates as
a B6 cut in the JSON. (e) `param_search._cap_mask:190-195` returns the full universe when a cap
tier has <30 finite caps, mixing universes across dates under one label. **Fix:** individually
trivial; grouped because none changes a shipped number today.

---

## 4. MANDATE 6 — ADVERSARIAL (new items)

### MA50 — HIGH — `/api/hotstocks?top=-1` defeats the per-tier row cap via a negative SQL LIMIT
**Files:** `valuation/web/app.py:519` · `valuation/screener/store.py:273`. `top = min(int(
request.args.get("top",100)), cap)` → `min(-1, 500) == -1`, and `store.load_snapshot` does
`q += f" LIMIT {int(top)}"` → `LIMIT -1`, which SQLite treats as **unlimited** (verified). The
per-tier cap (`g.hotstocks_cap`, free=10/premium=500) is the paywall, and a negative `top` defeats
it. Masked today only because `OPEN_ACCESS=true` makes everyone premium; the moment
`OPEN_ACCESS=false` a free/anonymous visitor gets the full ~594-row list instead of 10.
`/api/signals` shares the pattern (owner-only, lower impact). **Fix:** `top = min(max(1,
int(...)), cap)`.

### MA51 — MEDIUM — Open redirect on `/login?next=<absolute URL>`
**File:** `valuation/saas/auth.py:99` — `return redirect(request.args.get("next") or "/app")`,
raw, no same-origin check (verified). `/login?next=https://evil.example` redirects the victim
there after a legitimate login on a real, trusted page — a phishing primitive. Only `login` honours
arbitrary `next`. **Fix:** accept only `next` values beginning with a single `/` (not `//`).

### MA52 — MEDIUM — `DEMO_DENIED_VENDOR_ROWS` is an empty frozenset, so the only structural guard against a future vendor-backed read route leaking under the demo/public tier is a human remembering to list it
**File:** `valuation/screener/surfaces.py:232` — `DEMO_DENIED_VENDOR_ROWS = frozenset()`.
Complements Pass A's MA9: after `PUBLIC_FULL_VIEW=false` the demo tier still reads every owner
surface, and the one named backstop for the licence boundary is empty. **Fix:** populate/enforce
it, and add a test that fails when a new `/api/*` read route is not classified.

### MA53 — LOW — Inherited LA12 is STILL LIVE, and two public endpoints 500 on a malformed numeric param
**Files:** `valuation/web/app.py:536,550`, `:519,672`. Verified: `sector_attractiveness(all_rows)`
(line 550) still runs on the full population while `estimate_fair_values(rows,…)` (line 536) touches
only the sliced `rows`, so LA12's `median_upside` population-mix is unfixed in the current tree — a
status correction to inherited audit #2. Separately, `/api/hotstocks` and `/api/tickers` wrap no
try/except around `int(request.args.get(...))`, so `?top=abc` raises an unhandled 500 (contrast
`/api/dip`, which catches). **Fix:** clamp/parse defensively (also closes MA50).

---

## 5. MANDATE 1 — TRADE LOGIC (new re-examination + one equation)

### MA54 — Re-examination list beyond Pass A's MA24/MA26 — four rejections whose failing leg was an instrument the arm could not move, each with a NEW pre-registerable design (never a re-run)
1. **S10-ACCT (accounting veto)** — REJECTED on the portfolio-drawdown leg (−0.11pp vs a +2.0pp
   bar) while it *improved* top-decile alpha (+0.20pp), LS HAC t (2.6199→2.7080) and monotonicity
   (−0.89→−0.98), and flagged names crash >50% at **3.04×** the base rate (2.660% vs 0.874% on
   113,945 rows). The design could not detect it because this book's max drawdown is one
   market-wide quarter (COVID 2020Q1) that no name-level veto can move, and X7 calibrates **no**
   drawdown floor. **New design:** judge it on the V6-B M1 left-tail instrument (per-date name-level
   P(further −50%), within-date permutation p5, pre-committed economic floor) — the exact
   instrument that made M1 the record's one clean risk positive. The 3.04× is the pilot. (This is
   the same effect Pass A files as MA26-A/MA28; Pass B supplies the register shape.)
2. **O17-C4 "own the event"** — +4.686pp/trade, positive in both halves, clearing its own
   calibrated null in both, positive in every DTE quartile — NULL **solely** because retention
   0.5706 < a 0.70 floor set for a product reason. **New design:** register it as its own book (an
   entry rule, not a filter), judged on book expectancy vs matched random entries — the retention
   floor then does not exist by construction. Caveat: behind R2's dead entry.
3. **O14 `sweep_share`** — the one options arm to survive Benjamini-Hochberg, sign-stable across
   halves, NULL only because the late half missed its own bar by 0.16 of a t. **New design:** the
   cache is alert-days-only, so a same-design re-run is impossible anyway — collect Lee-Ready
   sweep-share on **new dates** (the optionable equity panel's rebalance dates) as an equity-side
   conditioner under the incremental-IC gate. New data, priced accordingly (~4.7 GB pull).
4. **Instrument-mismatch family** — **S13** inverse-vol sizing (REJECTED on alpha, *improved*
   Sharpe exactly as pre-registered; no Sharpe floor exists) and **O6** cheapness selection (the
   rules *changed the delta* rather than holding exposure fixed, so cheapness-at-fixed-exposure
   was never tested). **New design:** build the missing calibrated risk floors with the placebo
   machinery that already seeds per-arm floors (S22/S23), then re-register on risk statistics; for
   O6, score on the non-delta residual via O23's Greek attribution or delta-matched pairs.

### MA55 — Equation candidate — confidence-weighted mispricing (distinct from Pass A's MA27 KNS ridge)
`G = z_date( ln(fv/price) / max(w, w_floor) )`, where `w` = lens-disagreement width
`(max−min lens)/blend` (or `(bull−bear)/base`), residualized on the seven themes per date.
**Mechanism, measured not conjectured:** S23's A2 arm already used the lens *low* as a bound and
was the register's only positive full-sample arm; S10 showed the *unscaled* gap is
momentum-contaminated (engine-expensive names carry z-momentum +0.95 vs +0.67) — the width term is
the precision weight that separates "cheap by a confident model" from "cheap because the model
disagrees with itself." One closed-form column entering at 0.125 with present-weight renormalisation
(S7's own construction), **not** a re-weighting of themes and **not** the reversed tree combiner.
**Gate:** incremental IC ≥ the theme bar in both halves + the holdout gate. **Price:** ~2 trials on
the S23 valuation panel (already on disk, offline, network-tripwired). **Kill:** rejected if it
fails the calibrated alpha margin in either half, or its within-date rank-corr vs the deployed
composite exceeds 0.97 (then it is the incumbent with extra steps). This is the concrete instance
of Pass B's correction 2: the valuation engine is the largest measured-but-unwired subsystem, and
its gap-as-signal is testable where its withhold-state (Pass A MA26-C) is not.

### MA56 — Residual term-slope — already measured to beat its parent, with no consumer (record it for the next options entry, do not run today)
O16-REFROZEN measured `ts_resid = ts − β̂·atm_front` predicting option P&L **better than raw** (IC
+0.0703 [+0.0287,+0.1131] vs +0.0567) while `atm_front` alone predicts nothing. It has nowhere to
live until an options entry exists that is not R2's dead alert — so it is the feature any future
entry register should carry, not a trial to run now. Logged so it is not lost.

---

## 6. MANDATE 4 — EXTERNAL RESEARCH (new, beyond Pass A's MA31–MA34)

### MA57 — Routine-vs-opportunistic insider classification — the literature's precise answer to the project's own puzzle
**Paper:** Cohen–Malloy–Pomorski, *Decoding Inside Information*, JF 2012 (replicated; industry
standard). Only *opportunistic* (non-calendar-routine) insider trades predict; the aggregate is
noise. **The local puzzle it answers:** `insider` is the one **negative** theme (t ≈ −0.23/−0.34)
still carrying **12.5%** weight, and S3's three rebuilds all changed the *aggregation* (drop-buys
bonus, mcap-scale, two-input) and **never the classification**. **Testable here, needs one data
step:** `ownername` and `transactioncode` are **not** in `_KEEP["insiders"]`
(`valuation/edge/data_providers.py:248-249` — verified: the list is
`ticker, filingdate, date, transactionshares, transactionpricepershare, transactionvalue`), so the
routine/opportunistic split cannot be built without adding them and re-exporting **while the
Sharadar entitlement is live**. **Register:** an S-row, +1–2 trials, standard held-out gate; it is a
different *axis* from the three S3 rebuilds, not a fourth aggregation. Highest-EV untested equity
item in either pass.

### MA58 — Cross-sectional return seasonality — replicated, orthogonal, data-owned, and mentioned nowhere in the corpus
**Papers:** Heston–Sadka (JFE 2008, international evidence); Keloharju–Linnainmaa–Nyberg (JF 2016).
Same-calendar-month/quarter past returns predict the cross-section; replicated internationally and
across asset classes; survives in the JKP cluster. **Zero mentions in the entire Valquo corpus**
(grep-confirmed by the external lane). **Testable from owned daily closes alone** — the annual-lag
same-quarter return plus its seasonal-reversal complement fit the quarterly rebalance natively.
+1–2 trials, standard gate. One of the last replicated, orthogonal, no-new-data signals untried
here.

*(Corroboration of Pass A's external mandate, not new: the external lane independently confirmed
Pass A's MA34 decay-prior idea and its §12 "stop-carrying" list — ML combiner, regime/vol overlays,
short-vol/VRP — each against a specific 2023–2026 rebuttal paper. It also confirmed that on five
separate literatures the panel's verdicts match the *contested/post-publication* side of the
field, which is the project's strongest external validation.)*

---

## 7. MANDATE 8 — SIMPLIFICATION (new granularity beyond Pass A's MA23)

### MA59 — Deletion candidates with import-graph deadness evidence — archive, do not delete; and the load-bearing traps to leave alone
Pass A's MA23 established the principle (studies mixed into the shipped package). Pass B's options
and factory lanes supply the specific list, from a full `from`/`import` grep across
`valuation/` + `scripts/` + `tests/` + root runners:

**Dead in the tree (only importer is a closed study's own script/test) — archive with a banner
(the B16 pattern), keep the pin test as the quarantine proof:** `options_tail`, `options_exitreplay`,
`options_xsection`, the `ThetaProvider` class (keep `_api_key`), `tickflow` + `tickflow_signals` +
`surface_xsec`, and the block `kelly` / `dividends` / `convex_overlay` / `bucket_floor` /
`antisignal` / `earnings_surface` / `surface_stock`. `options_vrp` is archivable but **keep
`options_vrp_portfolio`** (O11 plans to apply it to the live arm). `ev_multiples_study.py` (425
lines) has **zero importers** and its verdict already ships OFF.

**Factory-side, safe to remove or tombstone:** the `options-bot/` tree (its Oracle deploy target is
decommissioned — `C6` row — yet the staged `NEXT.md` still tells Don to deploy to it; **preserve
`options-bot/.gitignore`'s `!handoff/*.zip` line**, which recovered the only copy of its sources);
`WHERE_WE_STAND.md` (retired from git 2026-08-09, still in the Cowork folder, and it asserts "the
options edge is real, validated three ways" — flatly contradicted by the current record); the
rejected-config env flags `SCREENER_SECTOR_NEUTRAL` / `SCREENER_RESIDUAL_MOMENTUM` /
`VALQUO_ROBUST_Z` (each a one-env-var path back to a twice-rejected intervention — delete the
override or make it warn in the health block); and the dead `AGENT_LOG.md` mailbox (3 entries, all
2026-07-28, git-excluded).

**Looks dead, is LOAD-BEARING — name loudly (both passes agree):** `deprecated_options_exit.py`
(B16 quarantine, the test proves it holds); the `autolearn → backtest.optimize.optimize_weights`
chain (that is Pass A's MA1 live-weight path — retire it *deliberately*, not by deletion);
`valuation/data/yahoo.py` (the free-stack provider the CI scan depends on); the D-series alt-data
modules (`congress/usaspending/edgar13d/short_interest`, inert-by-default but wired into the panel —
freeze with a comment, deleting them changes past `BACKTEST_RESULTS.json` reproductions).

---

## 8. MANDATE 5 — PROCESS (new, beyond Pass A's MA20–MA22)

### MA60 — The register machinery is honesty-dependent in three specific, mechanisable places, and its own builder was a data-destroyer
Pass A's MA21 named the class; Pass B's factory lane supplies the specifics, each with a check that
would convert "an agent chooses to be honest" into "an agent cannot be silently wrong":

- **`build_ledger.py --write` broke its own "never silently overwrites a human-verified row"
  docstring three ways** — it dropped all 8 out-of-band rows, rewrote lane-signed rows on an exact
  `src == "human"` match (B8/P4 lost `FIXED`), and deleted all prose under a hardcoded header
  (including OOB1's own *"build_ledger.py will DROP this row"* warning — a warning deleted by the
  operation it warns about). Traps 5/6 (multi-item commit subjects donate verdicts; `DEFERRED`
  reads as DONE) remain "NOT encoded … re-check on every refresh" — a permanent manual tax.
- **The auto-land gate now runs 77 `test_*.py` suites** (from the ~24 its own livelock arithmetic
  assumed), and every closed experiment's pin test runs on every land forever. **Split** product
  suites (on land) from register-pin suites (nightly).
- **`check_lanes.py`'s import graph is a hand-typed dict** with admitted gaps (it reported
  "(nobody)" for `config.py`/`screen.py` while a lane was live in both) while the dependency map
  brags its edges come from a real grep — **derive the dict, don't type it.**
- **CI enforces zero of the factory's conventions.** Handoff-before-done, thresholds-before-run
  (the phrase "strict git ancestor" appears 25× as *hand-verified* evidence — `git merge-base
  --is-ancestor` is one line), ledger-row-per-landing, and the canonical-artifact-not-stale check
  (compare `BACKTEST_RESULTS.json`'s `n_trials` against `research_log.detail()` — this drifted
  twice in a week) are all prose that a touch-check could enforce. This is the one-liner that would
  retire Pass A's MA13 tamper-evidence gap and MA5's two-HLZ-bars drift at the same time.

*(Corroborated from Pass A: MA20 shared-checkout drift, MA22 CLAUDE.md size — both re-measured. The
worktree/branch sprawl — 11 worktrees, 8 prunable, ~40 branches — that stranded the governance
layer until 2026-08-14 is the systemic instance of the same class.)*

---

## 9. Merged severity index (all 60 items)

**CRITICAL (2):** MA1, MA2 (Pass A — the live-weight learner and its uncalibrated gate).

**HIGH (14):** MA3, MA4, MA9, MA10, MA15, MA16, MA19, MA20 (Pass A) · **MA18 (re-rated HIGH by
Pass B)** · **MA36, MA37, MA38, MA39 (new — options/engine record integrity)** · **MA50 (new —
paywall bypass)**.

**MEDIUM (28):** MA5, MA6, MA7, MA8, MA11, MA12, MA13, MA14, MA17, MA21, MA22, MA23, MA35 (Pass A) ·
MA40, MA41, MA42, MA43, MA44, MA45, MA46, MA47, MA48 (new — engine/options) · MA51, MA52 (new —
adversarial) · MA54, MA55, MA59, MA60 (new — trade logic / simplification / process).

**LOW (4):** MA33-adjacent low notes, MA49, MA53, MA56 (new).

**HYPOTHESIS / research proposals (not defects — 8):** MA24, MA25, MA26, MA27, MA28, MA29, MA30,
MA31–MA34 (Pass A) plus MA57, MA58 (new external), carried as proposals with kill conditions.

The ordering that matters for action is unchanged from Pass A and reinforced by Pass B: **the
top two are MA1 (does the learner ever fire?) and MA18 (is the forward row being written?)** — one
is a question only Don's production can answer, the other is a clock running down today.

---

## 10. Batched questions for Don (merged; the first two decide the two top findings)

1. **Have you ever received an email subject *"🧠 Valquo self-learning — weights updated"*** (vs
   *"— monthly check (no change)"*)? If yes, MA1 is CRITICAL-fired, not CRITICAL-armed. If *neither*
   subject has ever arrived, the monthly job is failing silently — its own finding.
2. **Is `LEARN_ENABLED` set to anything on Render?** Undocumented, defaults on. *(Assumed unset →
   enabled.)*
3. **Is the bound forward row going to be written tonight (2026-08-14) and every close after?**
   Run #2 has recorded zero rows; the fix (`scripts/track_row --append`) exists on `origin/main`
   but **not on the laptop** (514 behind). This is MA18, re-rated HIGH.
4. **When you regate `PUBLIC_FULL_VIEW`, may the next lane also rotate `DEMO_ACCESS_TOKEN`?** Per
   MA9 the regate does nothing without it — the token is printed on `/work`.
5. **Is `data\options_ticks` (~4.7 GB) on the D: drive?** The backup names it in neither list
   (MA15).
6. **Who owns `ADMIN_TOKEN` rotation, and has it ever rotated?** It lives in GitHub Actions secrets
   *and* Render env and must move in both within one window (MA10).
7. **May I have the primary checkout synced?** 514 behind, 1 ahead; the one ahead is the
   `PT-WRITER` answer. Needs `sync.bat` (its `--ff-only` merge will fail on the diverged main — the
   real command is `git fetch origin && git merge --no-edit origin/main`); no agent may push `main`.

---

## 11. Where the next real improvement most plausibly lives — and where nobody should look again

**Nobody should look again at** (both passes agree, and the external literature agrees a third
time): weight tuning in any form (the best CPCV challenger missed by ~79×; five schemes rejected in
one session; Nagel 2025 and Avramov et al. 2023 close the ML/complexity re-open the roadmap still
lists as "biggest upside lever"); sector-neutral ranking (three rejections, both named routes back
now shut); the SF3 conviction family and the four classic anomalies (a market-cap sort at ρ ≈ −0.84
to `size`; closed on the corrected universe); regime/vol-timing overlays (S6 + S13 locally,
Cederburg 2020 + Detzel-NMV 2023 externally); short-vol/VRP income (the premium has measurably
declined — Chicago Fed 2025 — and every local arm landed null-to-negative with the mechanism
identified); and any re-run of S21 or S12-A2 on this panel. That list is the most valuable thing the
project owns — it is the reason to believe the survivors.

**The next real improvement is not a signal — it is closing the gap between the research programme
and the thing that ships.** Both passes reached this independently. MA1 is the proof the gap is
real: the most carefully gated number in the project is one nobody trades, while the number every
user sees can be re-tuned by a monthly cron on an uncalibrated bar that never compares to the
incumbent, without closing a vintage. Pass B's MA36/MA37/MA39 show the same gap in the record
itself — a worthless option censored from the live track, a retired era blended into live
expectancy, a broken run that ships asserting health. Fixing this class costs no trials, moves no
published claim, and removes the largest way this project could quietly stop being true.

**Second, tied to it: the forward track is the only data nobody has looked at, and it is not being
written.** Every internal bar has been cleared or honestly failed on one 18-year panel; X1 spent
the last untested independence axis inside the sample. There is nothing left inside. The clock has
reset three times in four days and vintage 4 has recorded zero rows — and unlike everything else in
this audit, a missed day cannot be recovered later.

**If those two land, the third is the monthly-panel rebuild (Pass A's MA33 / the S19 unlock),
because it is the one change that opens a whole blocked class** — every text- and LLM-derived signal,
and S19 with it — rather than buying one more arm. And if a single equity arm is run at all, the
two with the best outside evidence and lowest cost are **MA57** (routine-vs-opportunistic insider,
which directly targets the one negative theme still carrying 12.5% weight) and **MA31** (the
Cremers–Weinbaum matched-strike parity deviation, the largest un-run item either audit named, now
unblocked because the chain cache is known to hold the puts) — each pre-committed with the kill
conditions stated above.
