# CLAUDE.md — Valquo project brief (read every session)

> **FIRST: read `RUN_RULES.md` (repo root) before starting any work. It is short and
> non-negotiable — it governs pushing, handoffs, bug reporting, pre-committed thresholds, and
> never silencing a check. Every agent, every run, no exceptions.**

You are picking up **Valquo** (valquo.co), a Python/Flask stock-analysis SaaS owned by Don
(donniecorbin6@gmail.com). Be honest, concise, and never oversell. Architecture is under
**"Core file"** below (CORRECTED 2026-08-07, claims audit: this used to say "section 4 below" —
there are no numbered sections in this file and never have been, so the pointer led nowhere);
the optimization/data research roadmap is in `OPTIMIZATION_RESEARCH.md` — read it once for detail.

## What it is
Hot-stocks screener (9-theme "hot score") + options/intraday signals + a point-in-time fundamental
**backtest / Edge Lab** that proves-or-disproves the edge and tunes the screener weights. A monthly,
purely-statistical, out-of-sample-gated self-learning loop re-tunes weights.

## How to run (you can run these directly — Don cannot / will not)
- Full backtest: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --json data/backtest/last_result.json` (or `run_backtest.bat`). Reads licensed Sharadar exports in `data/backtest`. Takes 20-40 min.
- 13F due-diligence: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --validate-institutional` (or `validate_13f.bat`).
- Tests (keep green, **currently 249/249**): `python tests/test_edge.py`. **CORRECTED 2026-08-07
  (claims audit): this line read "currently 16/16" — measured today it is 249/249, exit 0.** It is
  also not the whole gate: `tests/` holds **24** suites and the auto-land Action runs EVERY one of
  them (audit C7), so verify with a loop over `tests/test_*.py` before pushing, not with
  `test_edge.py` alone.
- Deploy: Don runs `git_push.bat` himself (pushes to GitHub -> Render; Actions run the scans).

## HARD RULES (do not violate)
- **Never commit/push `data/`** (licensed Sharadar exports; gitignored) or `*.db`.
- **`.env` holds real secrets** (SHARADAR_API_KEY, ANTHROPIC_API_KEY, TRADIER_TOKEN, SECRET_KEY) — never print, commit, or overwrite.
- **Do NOT execute trades or move money** — a Robinhood connector exists (Cowork side); produce target/rebalance lists, Don executes.
- **Ignore Don's resume files entirely.**
- Repo is private; keep it clean. Keep `tests/test_edge.py` passing after every change.

## Core file: `valuation/edge/fundamental_panel.py` (the backtest engine)
- `build_fundamental_panel()` — builds the 9 themes point-in-time (reuses the live `build_frame`). `_yoy()` computes revenue/asset-growth/issuance -> `growth` + `capital_discipline`. `inst_lag_days` param stress-tests the 13F lag.
- 8 weight schemes (`_weight_schemes`), incl. `max-ir-decorr` (Sigma^-1*mu).
- Selection/validation: `walk_forward` (single-path, params) and **`cpcv_validate`** (Combinatorial Purged CV — the AUTHORITY for weights; reports PBO + Deflated Sharpe). If CPCV runs and rejects, keep defaults — do NOT fall back to walk-forward.
- `quantile_backtest` (decile / long-short), `regime_split` (edge by market-cap tier), `institutional_dependence`, `validate_institutional`.

## CURRENT STATE — the honest findings (do not oversell)
Rewritten 2026-07-30 after P5. Everything below is measured on the **full 2,710-name × 110-date
universe** (~18y, gross of costs). Several long-standing claims here were WRONG, not merely
stale — they are corrected in place and the corrections are called out, because this file is
the project's memory and the old versions had been repeated for months.

- **THE "8% CAP VIOLATION" NEVER EXISTED — `PT-SPLIT` IS CLOSED, AND THE DIAGNOSIS THIS FILE
  CARRIED FOR TWO SESSIONS WAS WRONG (2026-08-10, session 16).** The bullets below say the
  sandbox engine holds *"10 names, equal-weighted at 10% each — which the contract's own 8% cap
  forbids"*. **It forbids no such thing.** `valquo_index.build_index` sets
  `cap = max(MAX_WEIGHT, 1/len(picks))` with a comment saying why — **ten names at 8% sum to
  80%**, so on a small book the cap must relax to equal weight or the redistribution loop never
  terminates — and the payload has always self-reported `effective_max_weight`. **The weights
  were correct for the book they described.**
  * **THE REAL DIVERGENCE IS BOOK SIZE, AND IT IS ONE CONSTRUCTION FED TWO INPUTS.**
    `n = max(MIN_NAMES, round(len(large) × TOP_DECILE))` with `MIN_NAMES = 10`, so a 10-name book
    means the eligible large-cap tier held **fewer than 100 names**; the published 86 implies a
    tier of ~860. **`/admin/run-paper-track` reads `data/valquo_index.json` when it exists and
    SILENTLY REBUILDS FROM THE STORE'S LATEST SCAN when it does not** — and that scan is a top-N
    hot list. The engine was never pointed at a different strategy; it was handed a truncated one
    with no label. That is how `PT-OUTBOUND` shipped an engine figure as an Index claim.
  * **WHY THE WRONG FRAMING WAS EXPENSIVE, not merely untidy: the fix it implies is "lower a
    cap", and the cap was already right.** The actual defect would have survived the repair.
    Same lesson as the stale-figure and wrong-file-name corrections elsewhere in this file —
    **re-derive a diagnosis from the code before acting on a repeated one.**
  * **RESOLVED BOTH WAYS AT ONCE, per Don's "no third state":** `paper_track.seed_book` now
    **refuses** to seed a book that is not the Index (**≥ `CONTRACT_MIN_POSITIONS` = 50 names AND
    the 8% cap actually binding**), loudly and non-destructively — it never liquidates, because
    doing so on a conformance rule would be worse than the split. `experiment=True` is the only
    other door and it **stamps every holding row** (on the row, not in a return value: the old
    code *did* label its fallback and no surface rendered the label). The **four recorded days
    are registered in `PAPER_TRACK_CONTRACT.md` §5b** as a separate experiment, **kept not
    deleted** — its *fills* are real evidence about execution, its *return series* is evidence
    about nothing the contract binds.
  * **STILL OPEN, and it is the app lane's:** this stops the engine *adding* to a wrong book; it
    does not make it start recording the right one. That needs a conforming
    `data/valquo_index.json` on the Render disk when the cycle runs. **No vintage opened or
    closed** — the engine's series was never the bound series.
- **THE FORWARD OPTIONS BOOK WAS RUNNING EXIT LEVELS NO BACKTEST DESCRIBES, AND HELD A NAME THE
  ALERT ITSELF REFUSED (2026-08-10, session 16, `PT-BUG12`).** Both routed in by the options-bot
  lane off the first three REAL fills, both fixed in `paper_track.py`, all expected values
  pre-committed in `PREREG_session16_paper_track_repair.md` before any code changed.
  * **`_place_entry` anchors target/stop to the SUBMIT price and `mark_open` overwrote
    `entry_premium` with the FILL without recomputing either.** Systematic, not occasional:
    `auto-scan.yml` runs the cycle after the close, so the limit comes from a post-close quote and
    the day order fills at the next open. **2 of 3 open positions were off spec** (TGT +150.7%
    target against +100%; MET −46.7% stop against −50%). Levels now derive from the fill on the
    **alert's own** policy, and an idempotent repair pass fixes already-open rows every cycle.
    **All five pre-committed criteria held exactly** — TGT 8.90 → 7.1000 / 2.225 → 1.7750, MET
    9.80 → 9.2000 / 2.450 → 2.3000, **ETN bit-identical** because its fill equalled its limit.
  * **THE REPAIR RUNS IN THE FLATTERING DIRECTION AND THAT MUST TRAVEL WITH IT.** The bug made
    targets harder and stops tighter; correcting it makes them easier and looser. Right fix
    either way — the levels were wrong against the specification — but **"we fixed a bug and the
    book improved" is the easiest way for a forward test to flatter itself.** Concretely: **MET
    sat 10.2% above a stop level no backtest ever specified**, days from recording a stop-out the
    strategy under test would not have taken.
  * **A REPAIR MAY NOT EXECUTE A TRADE.** If a corrected level is already crossed, the write is
    **deferred and reported**, never auto-exited. Untaken today (no row crosses), pinned by test.
  * **`_eligible` never read `features.sizing`**, so ETN was bought on `skip: true` / *"one
    contract costs $1,610, above the $1,000 budget"* and became the **largest position in the
    book**. The veto is now honoured; **the sizing QUANTITY deliberately is not** (that would
    change construction), pinned as a non-change. **The open ETN position is NOT unwound** —
    that gate applies to new entries, and closing a live position to tidy the record is a trade
    decision.
  * **A THIRD DEFECT, same family, found while fixing the first:** the resume branch called
    `_exit_policy` on a `paper_option_orders` row, and **that table has no `features` column**, so
    the policy silently collapsed to the DEFAULTS. **Audit B5c's own comment claims that branch
    "rebuilds … the exit policy the same way the fresh path does" — the fresh path reads the
    ALERT.** It has never fired only because all three live alerts use the default policy. **A
    defect neutralised by a coincidence in the data is not handled**, so it is pinned with a
    policy that differs.
  * `options_summary.level_conformance` now reports off-spec live rows **read-only on every
    request** — it stays after the fix precisely because the first time this book was inspected,
    2 of 3 positions were off spec and nothing anywhere said so.
- **V1 SHADOW VINTAGES IS REGISTERED, BLIND, WITH NO MEASUREMENT — AND ITS POWER TABLE IS THE
  FINDING (2026-08-10, session 16).** Rule 6 (below) says an adopted change resets the whole
  five-year clock and buys nothing statistically — which, alone, means **the model can never be
  improved again without paying five years.** V1 is the escape: the closing vintage keeps being
  scored in shadow on the same dates and the two books are compared **PAIRED**, so the market
  risk that dominates a vs-SPY test **cancels**.
  * **THE GAIN IS REAL AND THE LIMIT IS STRUCTURAL, both computed before any pair exists.** At a
    between-book tracking error of 2.0 pp/yr the 60-month detectable difference is **3.34 pp/yr
    against the vs-SPY meter's 19.01** — four-fold. **But σ is small exactly when the adoption
    changed little, and an adoption big enough to matter raises σ.** No design escapes that. **A
    shadow pair that has not crossed is the EXPECTED outcome and is NOT evidence the adoption was
    worthless** — `verdict()` carries that sentence in its own output.
  * **THE CONTROL IS EXACT:** fed the contract meter's own 11.40 pp/yr TE it reproduces
    **σ 3.9847** and **~19 pp/yr at 60 months** to the digit, because it **imports**
    `track_meter.boundary` rather than re-implementing it. ρ and α are imported too and a test
    fails if they are ever copied — one boundary function in the project.
  * **BLINDER THAN ANY PREVIOUS REGISTER HERE: no vintage pair exists.** Vintage 2 opened
    2026-08-10 with no successor, so no parameter could have been tuned to a comparison even in
    principle. Vintage 2's parameters are **pinned now, in a tracked file** (`params_id
    0060c5ef3dda`), so the shadow runs a **snapshot, never a reconstruction**.
  * **No sign branch** (AST-pinned; flipping a whole series flips the verdict and moves nothing
    else), so **HARMED is exactly as reachable as CONFIRMED-LIVE**. **Research-only and fenced off
    every public surface by a test, BEFORE it has numbers to leak** — `PT-OUTBOUND` is why that
    fence is built in advance. **It does not weaken Rule 6:** it measures the price of an
    adoption, it does not refund it.
  * `valuation/edge/shadow_vintage.py`, `PREREG_v1_shadow_vintages.md`, 26 tests.
    **Equity `N` stays 131** (infra `n = 1`); the first shadow PAIR is charged when it opens.
- **AMENDMENT 1: RUN #1 IS VOID, RUN #2 IS THE LIVE TEST, AND THE PROJECT NOW HAS A VINTAGE
  RULE (2026-08-09, session 15).** Don voided run #1 (inception 2026-07-30, ~6 days, 2 rows)
  because it measured a model that has since materially changed — growth-input fix, score fix,
  universe rebuild. **Run #2: inception 2026-08-10, gate 2027-02-10, verdict 2031-08-10, with
  ZERO accrued days.** Recorded openly in `PAPER_TRACK_CONTRACT.md` **§5a**, never as a silent
  edit, and nothing above §5a was deleted.
  * **THE VINTAGE RULE.** Any **ADOPTED** change to scoring, weights or construction closes the
    current vintage and opens the next ("adopted" = ships in the live scoring path).
    **Rebalancing under unchanged rules is NOT a vintage event.** Each vintage carries its own
    clock; **the gate and the meter attach to the CURRENT vintage**, so a verdict is a statement
    *about a vintage* and must name it. The cross-vintage chain is kept and published as **"the
    system as operated"** — the honest answer to what a user would have experienced — and is
    **explicitly not the object of a verdict**, because it mixes models.
  * **RULE 6 IS THE BRAKE, AND IT IS THE PART TO REMEMBER BEFORE SHIPPING A SCORING CHANGE: a
    vintage change resets the whole accrued clock and buys nothing statistically.** §2's
    arithmetic is unchanged — 60 months at 49% power. A vintage that closes at month 30 has
    spent 30 months for no evidence.
  * **THE AMENDMENT MOVED THE CLOCK, NOT THE STATISTICS.** σ 3.9847, ρ 3, α 0.05, the cost drag
    and the SUPPORTED/UNSUPPORTED bars are **all unchanged**, so §3's *whole-run* void clause
    (which triggers on a threshold change) is not engaged; only the window-void clause is.
    Pinned by `test_the_amendment_moved_the_clock_and_not_the_statistics`. **σ was re-checked
    against the changed model rather than assumed to survive it: the current backtest still gives
    SPY excess +9.99%/yr at implied TE 11.401 pp/yr and IR 0.8759/yr** — the figures σ came from.
  * **THE DISCLOSURE THAT MUST TRAVEL WITH IT: the voided window was KNOWN to be −2.85pp.**
    Discarding a stretch that went against the strategy is the flattering direction. Three
    answers, each checkable: the cause (a model change) is independent of the outcome and its
    clause pre-existed the run; **run #2 accrues ZERO days**, so no window's sign could inform
    the new start date; and the voided rows are **kept**, visible in `as_operated()`. §5a
    forbids the thing this must never become — voiding a vintage for a change *chosen* after
    seeing the vintage go badly.
  * **Equity `N` 130 → 131** (`PT-AMEND1`), **Deflated Sharpe 0.8547 → 0.8539,
    √(2·ln 131) = 3.1226**, and `BACKTEST_RESULTS.json` was re-run from a clean tree so the
    artifact matches (14 leaves moved, five the DSR chain, four provenance, five 0.000% float;
    every headline bit-identical). Charged because void-and-restart is a degree of freedom: each
    vintage is another chance at the same hypothesis.
  * **THE METER NOW HAS A CALLER (session 15's own item).** `track_meter.detail()` ships as
    `summary()["contract_track"]` on **`/api/track`** — before this it was a tested library
    nothing called. It names **every missing trading day** on every request, is **not vacuously
    green** before the vintage starts (`recording_ok: None`, not `true`), is labelled a different
    object from the sandbox engine, and is **reconciled against `index_track.vs_spy_claim()`**,
    the one authority for a vs-SPY claim (measured −2.8468 vs −2.8468).
  * **`PT-WRITER` IS REPORTED CLOSED AND I COULD NOT VERIFY IT — the gate stays `pending`.** The
    writer is described as Cowork task `valquo-daily-track-write`, weekdays 20:01. **No such task
    is in this machine's Task Scheduler** (413 enumerate; three Valquo tasks, none this one) and
    the name is nowhere in the repo — but **no run was due yet either**, so that is evidence, not
    proof. **THE TEST IS MECHANICAL: inception 2026-08-10 is day 0, the first row due is
    2026-08-11, so from 2026-08-12 `/api/track` answers it.** Read that block before doing
    anything else with the track.
- **THE PAPER-TRACK CONTRACT IS SIGNED AND IN FORCE — OPTION E, 2026-08-09 (session 14). THE
  PROJECT NOW HAS A PRE-REGISTERED FORWARD TEST, AND TWO RECORDERS THAT DISAGREE ABOUT WHAT IT
  IS RECORDING.** Don signed: keep inception **2026-07-30** including the accrued negative days,
  **6-month operational gate (2027-01-30)**, **60-month verdict vs SPY (2031-07-30)**, the
  ~36-month costed equal-weight-basket secondary *if it is ever built*, plus a pre-registered
  anytime-valid evidence meter first rendered at the gate and monthly thereafter, whatever it
  says. `PAPER_TRACK_CONTRACT.md` §5 is the register; §6 freezes the meter.
  * **THE REGISTER BINDS THE PUBLISHED VALQUO INDEX, NOT THE SANDBOX ENGINE — because they are
    recording DIFFERENT BOOKS.** This is the session's material finding. The Index
    (`data/valquo_track.json` + `valquo_track_history.csv`, read by `index_track.py`) is **86
    names, score-weighted, max weight 2.3%, inception 2026-07-30**. The Tradier sandbox engine
    (`paper_index_track` → `data_export/paper_track_*`) is **10 names, equal-weighted at 10%
    each — which the contract's own 8% cap forbids — inception 2026-08-03.** They are not one
    track recorded twice. **Never quote an engine figure as evidence under the contract**, and
    a B7-class split stands until the engine is re-pointed or its outputs are labelled a
    different object everywhere they surface.
  * **~~The engine has never been fed (0 rows)~~ — CORRECTED 2026-08-09 (session 14): THAT WAS
    MEASURED ON THE LOCAL DEV DATABASE.** On the live Render service the engine holds **4 index
    days, 10 holdings and 3 paper option orders**, and the weekly `track-backup` Action has been
    committing them to `data_export/` all along. The rest of this bullet's session-13 findings
    stand; this one did not.
  * **THE REAL BLOCKER IS THAT NOTHING IN THIS REPOSITORY WRITES THE BOUND SERIES.** Not a
    scheduler fault, not a crash, not a conditional write — **there is no writer.**
    `index_track.py` only ever *reads* `valquo_track_history.csv`; the rows are produced by hand
    on the Cowork side, which is exactly why **four of six due rows are missing (33.3%
    coverage)**. **The operational gate cannot pass until an automated daily write exists**, and
    that is the Cowork lane's. `valuation/edge/track_meter.py:gap_report` now names every
    missing day so the failure is dated rather than discovered at the gate.
  * **THE METER IS HONEST AND WEAK, AND THE SECOND HALF MUST TRAVEL WITH THE FIRST.** A Robbins
    normal-mixture anytime-valid confidence sequence, σ **3.9847 pp/month** (the backtest's own
    11.40pp/yr tracking error inflated by R9's AR(1) design effect **1.4661**), **ρ = 3**,
    **α = 0.05 two-sided**, cost drag **0.14529 pp/month**. Measured over 40k AR(1) paths:
    false-crossing **1.5%** against a nominal 5%, but **power at the backtested +9.99%/yr edge is
    just 13.3% by 60 months and 30.7% by 120**, needing **~19 pp/yr to cross at 60 months**.
    **A meter that has not crossed is the EXPECTED outcome and is NOT evidence against the
    strategy.** The AR(1) inflation is load-bearing, not decoration: without it the false-crossing
    rate is **6.7%**, i.e. the naive version breaks its own guarantee. **σ may never be revised
    downward** — at 1.5× the assumed volatility the false-crossing rate is **20%**.
  * **GENUINELY BLIND, which is the whole point:** at the signing commit the bound series held
    **two daily rows and ZERO complete calendar months**, so no meter parameter could have been
    tuned to the outcome even in principle. Pinned by `tests/test_track_meter.py` (20 tests,
    every constant a literal), including one that fails if the AR(1) inflation is removed and one
    that pins the render decision as invariant to flipping the sign of the entire series.
  * **THE DATED AUTO-FLIP IS CLOSED, BY THE ENGINE LANE, THE SAME DAY (`126c137`).**
    `MIN_LIVE_DAYS = 60` no longer promotes the track on its own. `index_track.gate_state()`
    parses the **`Operational gate passed` row of `PAPER_TRACK_CONTRACT.md` §5** on every
    request, and `headline` requires **both** the day count **and** that row — so at any day
    count, indefinitely, the headline stays `"backtested"` until the contract says otherwise.
    **Every unrecognised outcome is not-passed** (missing file, missing row, malformed table,
    two rows disagreeing), so the failure direction is "still backtested", never "now live".
    Session 14 filled the row as `pending` and verified the parser returns `passed: false`.
    **On gate day, set that ONE row and nothing else anywhere:**
    `| Operational gate passed | YES - 2027-01-30 |`.
  * **Equity `N` 129 → 130** (the register is charged as a trial; understating `N` overstates
    significance). **Deflated Sharpe 0.8556 → 0.8547, √(2·ln 130) = 3.1201**, and
    `BACKTEST_RESULTS.json` was re-run so the artifact matches the record rather than going
    stale on the denominator again.
- **THE FORWARD PAPER TRACK CANNOT DELIVER A VERDICT FOR ~5 YEARS (2026-08-08, session 13).
  Roadmap #12's status line was wrong.** That item says the track is built and *"what remains is
  elapsed time and reading the track, not building it."* The arithmetic below is why that is
  false, and it is unchanged by the session-14 bullet above.
  * **THE ARITHMETIC IS THE FINDING, and it is not escapable by choosing a better statistic.**
    From `benchmarks.spy` the top decile beats SPY by **+9.99%/yr at a tracking error of
    11.4pp/yr** — an **information ratio of 0.88/yr**, and that is the IN-SAMPLE figure. Since
    t grows as √time, **t = 2.0 arrives at 5.2 years** (7.6 once R9's lag-1 +0.189 is applied as
    an n_eff haircut). **At 12 months the power is 18% and the minimum detectable edge is
    +34pp/yr — over three times what the project claims.** If the strategy is exactly as good as
    backtested, a one-year forward test reports "no evidence" **82% of the time**.
  * **REFUTATION TAKES EXACTLY AS LONG AS CONFIRMATION** — the test is symmetric. There is no
    horizon at which bad news is cheap. Nobody may say a short track disproved this either.
  * **THE TRACK CANNOT PRODUCE THE SERIES A VERDICT NEEDS, IN EITHER SOURCE.**
    `paper_index_track` stores a **snapshot of currently-open holdings** measured from each
    name's own entry, not a chained series — differencing two points is not a monthly return, and
    a departed name stops contributing. `paper_track.py:735-740` says so, and says chaining
    closed stints in *"is a construction change, not a bug fix, and was not made."* The Cowork
    file chains correctly but is **missing days** (two rows exist where five were due). **The
    verdict is not computable at any horizon until one source produces a chained series.**
    **PARTLY CLOSED 2026-08-09 (session 14): the snapshot objection was about the ENGINE, and
    the engine is not the bound source.** The Index series stores cumulative-since-inception
    levels, and `track_meter.monthly_excess` chains them into calendar months — a construction
    **robust to an interior missing day**, since a month needs only its two endpoints (pinned by
    `test_an_interior_missing_day_does_not_corrupt_a_monthly_return`). A month whose *month-end*
    mark is missing or >3 trading days stale is **voided**, never silently averaged over. **What
    remains is the missing writer, not the construction.**
  * ~~**THE INCEPTION DATE EXISTS ONLY IN A GITIGNORED FILE.**~~ **CLOSED 2026-08-09 (session
    14).** `2026-07-30` is now in **tracked** files — `PAPER_TRACK_CONTRACT.md` §5 and
    `track_meter.INCEPTION`, pinned by a test. The pre-registration can now be produced by
    anyone with the repo, which is what makes it one.
  * **THE SITE PROMOTES THE TRACK TO ITS HEADLINE BY ITSELF, ON A FIXED DATE, WITH NO APPROVAL
    STEP — THE ONE ITEM HERE WITH A DEADLINE.** `index_track.py:223-224` is
    `thin = days < MIN_LIVE_DAYS` then `headline = "backtested" if thin else "live"`, and
    `MIN_LIVE_DAYS = 60`. At day 60 the *"too early to judge"* pill (`index.html:114`)
    disappears and the headline flips to **live**. **The track is on day 5: this fires ~55
    trading days out, late October 2026, at 13% power (minimum detectable edge +49pp/yr).** The
    **CLOSED 2026-08-09 (`126c137`, engine lane) — see the session-14 bullet above: the flip now
    requires the contract's `Operational gate passed` row as well as the day count, and that row
    reads `pending`.** The rest of this sub-bullet is the record of what the defect was. The
    constant was never pre-committed, does not derive from power, and disagrees 2× with
    `paper_track.MIN_DAYS_FOR_MEANING = 126` governing the same track. ~~Both sit in
    `valuation/screener/index_track.py` — outside the edge lane; it needs assigning.~~
    **CORRECTED 2026-08-09 (session 14): THEY SIT IN DIFFERENT FILES AND DIFFERENT LANES, and
    this sentence was the one assigning the work, so the wrong file name pointed the fix at the
    wrong lane.** `MIN_LIVE_DAYS` is `valuation/screener/index_track.py:44` (engine lane, fixed);
    `MIN_DAYS_FOR_MEANING` is **`valuation/edge/paper_track.py:70`** — the edge lane's, and it
    was a **second ungated door**: `hero` falls back to `paper_track.index_summary()` when the
    Cowork files are absent, which is the fresh-deploy case, and that read a pure day count.
    **Both are now gated on the contract's one row; `index_summary` delegates to
    `index_track.gate_state()` rather than parsing the contract twice, and fails closed.**
  * **STATE, as of this bullet: the track is BEHIND — inception 2026-07-30, five days, Valquo
    +0.78% vs SPY +3.62%, excess −2.85pp.** That is −1.8 SD of a five-day window (p ≈ 0.08),
    i.e. an ordinary bad week that means nothing about the strategy — **but it means the start
    date is being chosen with the sign of the accrued period known**, so discarding those days
    is the flattering direction. `PAPER_TRACK_CONTRACT.md` is a **DRAFT awaiting Don**; zero
    trial cost, equity `N` stays 129, and the trial is charged on sign-off.
- **X8 REPLICATED ON 2026-08-04 AND THIS FILE NEVER RECORDED IT — the single strongest piece of
  external evidence the project has, missing from its own memory for three days (found
  2026-08-07, session 8).** Before this bullet, `CLAUDE.md` contained the words "JKP" and "Japan"
  **zero times**, and `HANDOFF_STATUS.md` likewise; the only trace was the phrase "X8's
  international replication is the out-of-sample evidence, R1 is not", which reads as *future*
  work. **It is not future work.** The omission demonstrably misled: session 8's own prompt
  instructed the agent to "scope X8 … make that actionable instead of aspirational" — for a test
  that had already run and passed. Result, from `HANDOFF_free_analysis.md` (2026-08-04, verdict
  **REPLICATES**, threshold committed first): the untuned 5-theme equal-weighted composite,
  mapped 1:1 onto Global Factor Data with **no tuning of any kind**, monthly `vw_cap`,
  1999-01 → 2025-12, NW(12):
  * **Japan +2.05%/yr (t 3.85)** and **developed Europe +3.36%/yr (t 4.30)** — both clear the
    pre-committed t > 2.0. World ex-US +3.37% (t 5.03). **All 15 European countries positive,
    12 of 15 clear t > 2.**
  * **THE CONTROL IS THE POINT: the USA is the WEAKEST region tested (t 2.35)** — weaker than
    Japan, Europe, developed and world-ex-US. The theme structure is **not** a US artifact, and
    it is out-of-sample in vendor, country, construction and period simultaneously.
  * **REPORTED, NOT BURIED: the composite replicates while its COMPOSITION does not.** Japan's
    result is carried by value (t +2.27) and size (+1.81); **quality (−0.12) and momentum
    (+0.88) contribute nothing there**, the mirror image of the US profile (quality +3.03).
    Momentum failing in Japan is a documented stylised fact, which is evidence the data is real.
    Two of five mapped themes do not generalise to Japan.
  * **IT DOES NOT CORROBORATE VALQUO'S MAGNITUDE, AND MUST NEVER BE QUOTED AS IF IT DOES.** JKP
    earns **+2% to +3.4%/yr long-short at `vw_cap`**; Valquo's long-short is **+20.4%/yr** — a
    factor of six, on a different instrument (capped value-weighted broad factors vs an
    equal-weighted concentrated decile book). **X8 establishes that the premia are real and
    general; X4 says the margin over what a user can buy is not demonstrable since 2014.**
    Together: strong evidence for genuine factor exposure, weak evidence for implementation
    alpha. Only 5 of 7 themes map — `insider` and `institutional` have no analogue, and they are
    the same two X4 found have no retail ETF analogue.
  * **LICENCE: CC BY-NC 4.0, RESEARCH ONLY.** It validates the model and can **never ship in the
    product**. Data lives in `data/factors/research_only/jkp/` (2.1 MB, 17 regions × 324 months,
    already on disk). Reproduce with `python -m scripts.jkp_replication`.
- **WHICH SELECTION RULE PICKS A THEME TO DROP IS NOT ANSWERABLE ON THIS PANEL, AND THE TEST WAS
  DELIBERATELY NOT RUN (2026-08-07, session 8). This is a result, not a skipped task.** Session 7
  ended by nominating a pre-registered test of the *selection rule* (the decide-half argmax picked
  `momentum` and `capital_discipline`, both of which flip sign across halves, while `quality` —
  stable on both halves — was never selected). The answerability question was settled **before**
  anything was run, on the already-published session-7 arm table, so it cost **zero trials**:
  * **A three-block design on 69 dates gives 22-date blocks, and the noise on a 22-date block is
    σ = 1.57pp against a pre-committed margin of 1.00pp.** Pure noise clears that margin **26.1%**
    of the time; power under the record's own best estimates is **50.6%** — a coin flip in both
    directions. A positive result and a negative result would have been equally uninterpretable.
  * **THE DESIGN CANNOT SEPARATE THE TWO RULES EVEN IN PRINCIPLE.** Monte Carlo over the design:
    the stability rule and the incumbent argmax rule **select the same arm 90% of the time** and
    reach a **different verdict on only 5.1% of panels**. The experiment is not merely
    underpowered — it is the wrong shape, because "which rule is better" is a property of the
    distribution over panels and one panel yields one draw.
  * **THE DECISIVE FACT, and it needs no variance estimate: with one panel the paired sign test
    has n = 1, whose smallest achievable p-value is 0.50. No threshold reaches significance, so
    no possible outcome could have been quotable.**
  * **DECLINING KEPT THE DENOMINATOR: equity `N` stays 116** (Deflated Sharpe **0.8674**,
    √(2·ln 116) = **3.083**). Running the 7-arm sweep would have made it 123 → DSR 0.8609,
    √(2·ln 123) = 3.102, purchasing a coin flip with a real haircut. **Not running a test that
    cannot resolve is the cheaper action, not the lazier one.**
  * **~~IT IS ANSWERABLE ON X8's DATA~~ — VOID, REFUTED BY MEASUREMENT 2026-08-07 (session 9).
    THE WORD "INDEPENDENT" WAS AN ASSUMPTION AND IT IS FALSE.** This bullet used to say "16
    held-out countries give 16 independent draws instead of 1; a paired sign test then reaches
    α 3.84% at ≥12/16, with 80% power…". Session 9 built the gate and measured it: see the
    next bullet. **Every number in that sentence is void — the 3.84%, the 80% and the 8.5%.**
- **16 CO-MOVING COUNTRIES ARE WORTH 2 TO 4 INDEPENDENT DRAWS, NOT 16 — SO A "REPLICATES IN N
  COUNTRIES" COUNT IS WORTH FAR LESS THAN ITS N SUGGESTS (2026-08-07, session 9, SELRULE).**
  The cross-country selection-rule test session 8 pre-registered was executed in full. The
  clustering gate (`valuation/edge/cross_country.py`) was built, tested and committed BEFORE the
  measure set was touched; it re-points X7's design-effect-vs-shuffled-null machinery so the
  block is the MONTH and the observations inside it are the COUNTRIES, making the measured ICC
  the average pairwise co-movement. **Two independent kills:**
  * **THE DESIGN CANNOT RETURN A POSITIVE VERDICT AT ALL. Clustering is measurable on 10 of 10
    arm-pairs** (design effects 3.97–8.27 against a shuffled-null p95 of ~1.13), **ρ 0.198–0.484,
    n_eff 1.94–4.03 countries out of 16.** The calibrated critical count is **17 of 16** at the
    pre-committed max ρ, and **even a unanimous 16/16 gives p = 0.0546** (400k draws, se 0.0004).
    At the *median* ρ the bar is 16 of 16 — unanimity or nothing. **The rejection region is
    empty; the design's power at α 5% is zero.**
  * **THE PRE-REGISTERED 12/16 BAR CARRIES A TRUE α OF 28.7%, NOT 3.84% — a 7.5×
    UNDERSTATEMENT.** Building the gate first is the only reason this session did not quote a
    "3.84%" result that was really a 29% one. **That is what the gate is for, and any future
    claim of the form "it replicates in N countries" must now pass it.**
  * **SEPARATELY: `NO CONTRAST` — both rules select `size` on `usa`**, so every paired
    difference is identically zero. Pre-registered as an outcome before the run. **Not a NULL,
    not a tie.** Four of five arms are same-sign across both `usa` halves, so the stability
    constraint does not bind. **HYPOTHESIS ONLY, generated on the decide set: the instability
    that motivated this whole question (4 of 7 arms flip on Sharadar) may be a property of the
    69-date panel's thinness, not of the selection rule** — 324 monthly observations vs 69.
  * **X8's OWN HEADLINE IS UNAFFECTED.** X8 tests each region's premium separately with NW(12)
    errors and never pooled countries into a count, so it never made the independence assumption
    this refutes. **The gate constrains what is built ON TOP of X8, not X8.**
  * **THE SELECTION-RULE QUESTION IS NOW CLOSED ON BOTH AVAILABLE DATASETS.** One panel gives
    n = 1 (session 8); 16 co-moving countries give n_eff ≈ 2–4. That is not an engineering
    defect — it is the amount of independent evidence that exists. **Do not re-open it without
    new data.** Equity `N` 116 → **121** (5 arms, paid as pre-committed): **Deflated Sharpe
    0.8628, √(2·ln 121) = 3.097.** Reproduce with
    `python -m scripts.selection_rule_crosscountry`; `data/free_analysis/SELRULE_CROSSCOUNTRY.json`.
- **THE ML TREE COMBINER IS REJECTED, AND ITS DECILES RUN BACKWARDS OUT OF SAMPLE (2026-08-08,
  session 11, roadmap #16). The register was executed unmodified.** `PREREG_ml_combiner.md` was
  committed blind at `ec6c01d` a session before it ran: seven deployed theme z-scores,
  rank-of-`fwd_ret` target, 63d, the corrected 69-date panel, a FROZEN 8-point
  `HistGradientBoostingRegressor` grid, all selection confined to a decide half via CPCV, one
  measurement per direction, both directions.
  * **WORSE ON ALPHA IN BOTH DIRECTIONS, so REJECTED by the registered rule.** decide-early →
    measure-late: tree **+1.88%** vs linear **+11.58%**, **Δ −9.70pp**, ΔHAC t −2.118.
    decide-late → measure-early: tree **−2.66%** vs linear **+2.82%**, **Δ −5.48pp**,
    ΔHAC t −2.877. All three ADOPT criteria fail in both directions.
  * **THE FINDING IS STRONGER THAN THE VERDICT: the tree's monotonicity is +0.382 and +0.842**
    — remember **negative is well-ordered** — so its top decile underperforms its bottom decile
    out of sample. **The run contains its own control:** the linear arm scored on the IDENTICAL
    rows through the IDENTICAL `quantile_backtest` call is well-ordered (−0.903, −0.855), and the
    equal-weight benchmark matches between arms to four decimals. **It is the model, not the
    harness.**
  * **IT IS NOT A FITTING FAILURE. All 16 grid × direction cells had a POSITIVE decide-half CPCV
    out-of-sample rank IC (+0.011 to +0.024).** The model generalises across 15 purged CPCV paths
    *inside* the decide half and then **reverses across the boundary**. It learns half-specific
    structure strong enough to invert a ranking rather than merely dilute it.
  * **THE TWO DIRECTIONS SELECTED OPPOSITE ENDS OF THE GRID, monotonically.** decide-early ranks
    capacity best-to-worst (most complex wins); decide-late ranks it worst-to-best (least complex
    wins). **Whether model capacity helps is a property of which half you look at, not of the
    problem.** Same shape as session 7's LOO.
  * **QUOTE IT WITH THE PARAM-SEARCH PRECEDENT: +8.43%/yr in-search → −0.04%/yr locked hold-out.**
    The combiner is that phenomenon with a sharper edge. **Selection on this panel does not merely
    fail to generalise; it can generalise backwards.**
  * **WHAT IT DOES NOT SAY:** it does not vindicate the flat 1/7 linear form, it does not close
    roadmap #16 (a raw-signal or different-model-class variant is a NEW pre-registration, and it
    inherits this reversal as its prior), and it changes nothing in the live product.
  * **Trial cost paid as registered: equity `N` 121 → 129, Deflated Sharpe 0.8628 → 0.8556,
    √(2·ln 129) = 3.118.** Every equity claim after this is charged N = 129.
    `data/free_analysis/ML_COMBINER.json`; reproduce with `python -m scripts.ml_combiner`.
- **`N` MOVES THE LONG-SHORT t, AND THEREFORE MOVES THE CALIBRATED FLOORS. THE X7 8%-vs-7%
  DISCREPANCY IS CLOSED — IT IS ONE DRAW, SEED 1005 (2026-08-08, session 12).** Two sessions
  called it undiagnosable because X7's raw draws were never retained. The cause is a coupling
  nothing in the record described: `cpcv_validate`'s adopt gate is
  `margin > _trials_haircut(len(names)) · se`, and `_trials_haircut` (`fundamental_panel.py:2097`)
  is **floored at the research log's `N`** (audit M1); `scripts/placebo.py` then feeds the
  **adopted** weights to `quantile_backtest`. **Adoption is monotone decreasing in `N`, so raising
  `N` re-scores a draw under different weights.**
  * **X7 ran at N = 84 (haircut 2.97685); session 10 ran at N = 121 (haircut 3.09703).** Seed
    1005's margin is **0.00287097** against `se` **0.00094470**: it clears the N = 84 bar
    (0.0028122) and fails the N = 121 bar (0.0029257). Scored under the challenger's weights its
    naive `ls_t` is **2.1273**; under base weights, **1.0454**. Session 10's retained artifact
    records **1.0453572947436582** — identical to the recomputation to sixteen digits.
  * **SEED 1005 IS THE ONLY FLIP IN 100 DRAWS**, which is checkable because the gate's other two
    conditions do not depend on `N`, so adoption is monotone and the search set is the draws that
    did not adopt at N = 121.
  * **IT REPRODUCES EVERY RECORDED NUMBER ON BOTH SIDES.** Substituting the adopted value into
    session 10's 100 draws gives **exactly 8** at `t ≥ 2.0` — X7's figure. And the naive **p95
    stays 2.1437, max stays 3.436** — which is precisely why session 10's control reproduced X7's
    percentiles *to the digit* while missing one draw: **2.1273 lands just below the 95th
    percentile.** One fact explains both halves of what looked like a contradiction.
  * **THE ADOPT CURVE REPRODUCES TWO HISTORICALLY RECORDED RATES THE SCRIPT NEVER SAW.** With
    `(margin, se)` banked, adoption at any `N` is arithmetic: **N = 8 → 27 draws adopt** (X7's
    recorded **27%**), **N = 84 → 21** (M1's recorded **21%**), **N = 116/121/129 → 20**
    (session 10's artifact: **20**), N = 200 → 18, N = 400 → 17. Monotone throughout, and
    **27 → 21 is six draws stopping with none starting** — exactly the one-directional move this
    file records for M1, recovered independently from the margins.
  * **CHECKED, NOT ASSUMED: today's N = 129 still gives 20 adopters, the same as session 10's
    121, so session 10's published floors (naive 2.1437, HAC 2.2837) are still the floors at the
    current `N`.**
  * **IT ALSO EXPLAINS WHY IT LOOKED UNDIAGNOSABLE.** Session 10 reasoned that no draw sat near
    2.0 so it could not be a boundary effect. Correct — seed 1005 did not *drift* across the
    boundary, it **jumped 1.08 of a t** because its weights changed. A knife-edge crossing was
    the wrong thing to look for.
  * **THE CONSEQUENCE THAT OUTLIVES THE DISCREPANCY: A CALIBRATED PLACEBO FLOOR IS A FUNCTION OF
    `N`.** The floor is a percentile of the null `ls_t` distribution, and `N` moves individual
    draws within it. **Here the floors did not move** (2.1437 naive, 2.2837 HAC at both `N`)
    because the one affected draw landed below the percentile — **that is luck, not design.**
    Every sweep must record the `N` it ran at, and **a floor may not be compared across sweeps
    run at different `N` without checking.**
  * **THE SHIPPED STRATEGY IS UNAFFECTED, for a reason already in the record: it does not adopt,
    it keeps `current-default`,** so no haircut touches its `ls_t`. The exposure is entirely to
    the *calibration*, not the headline. Same family as X7's post-hoc "CPCV adoption manufactures
    ~+1.4 of long-short t" — now a demonstrated mechanism on a named draw rather than a split.
  * `cpcv_validate` now banks **`adopt_detail`** (margin, se, haircut, `n_trials_used`) and
    **`challenger_weights_cols`** — the challenger's weights whether or not adopted — so "what
    would this run have scored one haircut lower" is arithmetic. **Zero trial cost**; equity `N`
    stays 129. `data/free_analysis/X7_RECONCILE.json`; `python -m scripts.x7_reconcile`.
- **THE TRIAL COUNTER HAD A REAL DEFECT THAT NEVER FIRED, AND `N` DOES NOT MOVE (2026-08-08,
  session 12).** `research_log._parse` tested `\bFIXED\b` against **every cell of a row joined
  together**, so a row whose hypothesis, threshold, source or note merely contained the word
  "fixed" was dropped from `N` even where its verdict read `REJECTED`. Understating `N`
  **overstates** the significance of every DSR-gated claim — M1's own error, inside M1's own
  parser, carried three sessions. Two sibling defects of the same class were fixed with it: the
  `n=<k>` grid multiplier was grepped from the **whole line**, and the domain came from the first
  cell matching any domain name rather than the domain column.
  * **THE RECOUNT MOVES NOTHING. Equity `N` 129 → 129**, options 164, infra 3, total 296, 57 rows
    counted and 18 dropped (merged log) — identical against the **shipped module itself** and
    against **all fifteen historical revisions** of `RESEARCH_LOG.md`. No `fix*` word appears
    outside a verdict cell in any of the 72 data rows as they stood at the recount; **zero
    near-misses. No published `N` was ever wrong.** Deflated Sharpe stays **0.8556**,
    √(2·ln 129) stays **3.1176**, and all four DSR figures in this file
    (N = 84 → 0.899659, 116 → 0.867360, 121 → 0.862756, 129 → 0.855608) reproduce to six decimals.
  * **THE REPAIR NEARLY SHIPPED THE ERROR IT WAS FIXING, AND THAT IS THE MOST USEFUL THING HERE.**
    Merging `origin/main` mid-session brought in **O16**, which writes
    `|Spearman(term_slope, atm_front)|` — an absolute value — **inside a markdown table cell**.
    The unescaped `|` gives that row **11 cells against a 9-cell header**, shifting every column
    after the metric; the first-cut column parser read `n` off prose and charged it **1 trial
    instead of 5, understating options `N` by 4** — the same harmful direction, in a different
    column, and **the whole-line grep it replaced was accidentally immune**. It was caught only
    because merging and re-running the recount was written into the procedure rather than left to
    the end. Misaligned rows now resolve toward a **larger** `N` and are listed in
    `rows_malformed`. **The O16 row is NOT edited** (the register forbids it); **its pipes want
    escaping as `\|` by the lane that owns them** — it is the only malformed row in 74.
  * **WHY IT NEVER FIRED IS NOT REASSURING.** Sessions 9-11 knew about the defect and dodged it
    by choosing synonyms; the earlier rows avoid the word by luck. **A denominator protected by
    authors' word choice is not protected.** The repair is pinned by a fixture the old parser
    fails (3 real trials, of which it counts 1), and `detail()` ships
    `rows_rescued_by_parser_fix` so a silent revert would be loud.
  * The pre-registered expectation (`N` rises, 60/40) was **WRONG** — five wrong directional calls
    to one right. Procedure committed at `21069ac` before the parser was touched, including the
    rule that **no row's text may be edited to change `N`**: `PREREG_session12_recount.md`.
- **THE COMPOSITE'S COMPLEXITY IS NOT DEMONSTRATED, AND THEME IC DOES NOT PREDICT WHICH THEME
  MATTERS (2026-08-06, session 6, X3 RE-RUN). The 2026-08-03 "EARNS ITS COMPLEXITY" verdict is
  VOID — it ran on the pre-B6 110-date panel and against a 1.0pp bar that sits BELOW X7's
  1.95pp noise floor.** Re-run on the corrected 69-date panel against the calibrated bars,
  8 pre-registered arms, flat weights:
  * **The full seven-theme composite beats its own best single signal (`gp_on_capital`) by
    +4.51%/yr, CI95 [−0.14%, +9.12%] — INCLUDES ZERO, so by the pre-registered rule this is a
    NULL.** A near miss is a null. **But "decoration" is the WRONG word and must not be used:**
    `gp_on_capital` alone posts long-short *t* **0.413** against the composite's **2.836** and
    clears none of X7's bars but the alpha margin. Quote both halves: *"the seven-theme
    composite is the only arm that clears the calibrated long-short bar of 2.14, and its
    top-decile alpha advantage over the best single signal is +4.5pp/yr but not separable from
    zero on 69 periods."*
  * **THE CURVE DOES NOT FLATTEN — IT IS NOT A CURVE.** Alpha by cumulative arm (themes added
    in descending IC order): +1.12 → +0.96 → +3.77 → +4.05 → +3.22 → +4.10 → **+7.17%**. Two
    prefixes have POSITIVE monotonicity, i.e. their deciles run backwards. **Only the full arm
    clears the long-short bar; the best prefix reaches t 1.02.**
  * **THE FINDING TO CARRY: `size` has the WORST theme IC (−0.30) and carries the composite's
    entire statistical significance.** Adding it last takes alpha +4.10% → +7.17% and LS *t*
    1.02 → 2.84. **Ranking themes by IC and adding greedily measures the wrong thing** when a
    theme's value is its orthogonality. This is the P6 lesson ("a signal's IC can be flat while
    the composite built from it moves a lot") in a far starker form.
  * **EXPLORATORY leave-one-out, NO VERDICT, do not act on it:** dropping `capital_discipline`
    (2nd-best IC, one of only two clearing X7's bar) *raises* alpha to +8.54% and LS *t* to
    3.352; dropping `size` costs 3.08pp/yr. Seven correlated comparisons reported for their
    extremes. **Nothing was changed on it.** A pre-registered, held-out LOO is Session 7's
    first item.
  * **THE TRIAL COUNT ROSE AND THE HEADLINE PAID FOR IT. Equity N 84 → 104** (8 new arms plus
    12 from the void run, which had never been logged). **Deflated Sharpe 0.8997 → 0.8789;
    √(2·ln N) 2.977 → 3.048, past the Harvey–Liu–Zhu hurdle of 3.0 for the first time.** Still
    above X7's calibrated floor of 0.72. `BACKTEST_RESULTS.json` picks this up automatically on
    the next full run.
- **THE EQUITY COMPOSITE IS USELESS AS AN OPTIONS VETO, AND THE REASON IS THAT ON THIS UNIVERSE
  IT IS MOSTLY A SIZE SORT (2026-08-06, session 6, U7 — REJECTED).** Join built and pinned
  (most recent rebalance date **strictly ≤** the alert date, tested against its own look-ahead
  variant). **Coverage measured before any verdict: 98.1% of 3,885 alerts, 97.8% of 186 names.**
  * **The bottom decile — the one a veto exists to remove — is the THIRD MOST PROFITABLE
    (+10.64%).** Expectancy by composite decile is U-shaped, not monotone: D1 +18.74%,
    D2 +14.78%, middle −0.46% to +4.9%, D10 +10.64%.
  * **All three pre-registered cells go the wrong way:** bottom-decile veto lift **−0.57pp**
    (CI [−1.49, +0.32], retention 92.7%), bottom-quintile −1.04pp, within-universe decile
    −0.44pp. Retention was never the binding constraint. **It does not demonstrably HURT
    either — every CI straddles zero. The honest sentence is that the composite's bottom decile
    carries no information about which alerts to refuse.**
  * **NO INTERACTION WITH THE ALERT AT ALL.** The identical veto on the five-seed random-entry
    control lifts by −0.49pp; real minus control is **−0.08pp** [−1.02, +0.82]. The composite
    describes the UNDERLYING, not the alert.
  * **MECHANISM:** median market cap rises monotonically across deciles, **$62.7B (D1) →
    $133.5B (D9)** — inside 187 megacaps the other themes are compressed and `size` dominates,
    so the "veto" vetoes a cap bucket, which is a property of the underlying. (D10 sits at
    $106.0B and breaks the pattern; no claim is made about why.)
  * **CONSEQUENCE: DO NOT RUN U1 (composite → options ENTRY) AS WRITTEN.** The audit's own
    argument is that the veto is "strictly the easier bar". The easier bar failed *with a
    mechanism*. Reopen only with a composite built WITHIN the options universe, or with size
    neutralised.
  * **THE PROJECT'S EXPECTATION WAS WRONG AGAIN — FOURTH IN A ROW.** The pre-commitment said
    "I expect the veto to HELP, 60/40". R10, O20, the spread toll and now U7. **Do not reason
    about the direction of an effect in this project; measure it. Writing the expectation down
    first is worth doing precisely because it keeps being wrong.**
- **X8 HAS LANDED AND IT REPLICATES — THE PROJECT'S ONLY OUT-OF-SAMPLE EVIDENCE, AND THIS FILE
  RECORDED IT NOWHERE UNTIL NOW (added 2026-08-07 by the claims audit; landed 2026-08-04,
  `7edf594`, ledger X8 DONE, write-up in `HANDOFF_free_analysis.md`).** Two bullets below still
  say "still ONE panel; **X8's international replication is the out-of-sample evidence, R1 is
  not**" — written as though X8 were pending. It ran. Untuned 5-theme equal-weighted composite,
  themes mapped 1:1 with **no tuning**, on Global Factor Data (JKP), monthly `vw_cap`, matched
  window 1999-01 → 2026-04, bar committed in writing first (NW t > 2.0, 12 lags, in **both**
  Japan and developed Europe):
  * **VERDICT: REPLICATES. Japan +2.05%/yr (NW t 3.85), developed Europe +3.36%/yr (t 4.30),
    world ex-US +3.37% (t 5.03).** Europe is not one country: **all 15 positive, 12 of 15 clear
    t > 2**.
  * **THE STRIKING PART IS THE CONTROL: the USA is the WEAKEST region tested (t 2.35)** — weaker
    than Japan, Europe and world-ex-US. Whatever else is true, **the theme structure is not a US
    artefact.** It is out-of-sample in vendor, country, construction and period simultaneously.
  * **WHAT IT DOES NOT ESTABLISH — carry this with it: MAGNITUDE.** The JKP composite earns
    **+2% to +3.4%/yr** long-short at `vw_cap`; Valquo's own long-short is **+11.04%/yr**
    (`construction.long_short_ann`, corrected panel). Not comparable instruments (capped
    value-weighted broad factors vs an equal-weighted concentrated decile book), but the gap is
    a factor of 3-5 and **nothing in X8 corroborates it.** *(The X8 write-up states the gap as
    "a factor of six" against a Valquo long-short of +20.4%/yr; that figure does not match the
    landed corrected panel, which reads 11.04%. Quoted here from the artifact, not the handoff —
    the direction of the caveat is unchanged either way. Flagged for the free-analysis lane.)*
  * **The composite replicates while its COMPOSITION does not.** Japan is carried by value
    (+2.27) and size (+1.81); quality is **−0.12** and momentum +0.88 there. The US control is
    nearly the mirror image (quality +3.03, momentum +1.69, value +1.01, size +0.87). Momentum
    failing in Japan is a documented stylised fact, which is evidence the data is real rather
    than a defect. An equal-weighted blend is the right structure for that world — a quiet
    vindication of the untuned flat weights.
  * Secondary arm, reported as measured: JKP publishes **terciles**, not deciles, so monotonicity
    is across 3 points and is weaker than the pre-registration promised. 5/5 correct-sign in the
    US, 4/5 in Japan (the exception is `qmj`, consistent with quality's t there).
- **THE THRESHOLDS ARE NOW CALIBRATED — READ THIS BEFORE QUOTING ANY t, IC OR PBO
  (2026-08-05, audit X7). Every bar in this project was a CONVENTION until this run; three of
  the four are too low, and one is at the noise level.** `scripts/placebo.py` shuffles the
  signal within each rebalance date (block permutation: per-date distribution, missingness
  pattern and cross-theme correlation all preserved exactly; `fwd_ret`/`marketcap`/`sector`
  untouched) and pushes 100 draws through the REAL pipeline — CPCV, weight selection,
  quantile backtest, theme ICs, the held-out gate. The harness reproduces the shipped run
  exactly (t 2.83606, alpha 0.071741, PBO 0.73333) before any draw, and the equal-weight
  benchmark is +18.14% on all 100 draws (sd 0.00004), which is the control.

  | bar | as used | CALIBRATED (placebo p95) | how often pure noise clears the OLD bar |
  |---|---|---|---|
  | theme IC t | 2.0 | **2.71** (noise max 3.93) | **39%** |
  | long-short t (naive) | 2.0 | **2.14** (noise max 3.44) | 8% |
  | **long-short t (HAC — the one to quote)** | 2.0 | **2.28** (noise max 3.78) | 8% |
  | top-decile alpha margin | 1.0pp | **1.95pp** | 18% |
  | PBO | <50% | **<19.7%** (placebo p5; noise MEDIAN is 46.7%) | **55%** |
  | Deflated Sharpe | >0.95 | **STANDS** (noise median 0.28) | 2% |

  **THE DEFLATED SHARPE ROW IS CONFIRMED AT THE TRUE N (2026-08-06, session 5). The
  PROVISIONAL marking is LIFTED.** The placebo was re-run at `N = 84` on the identical panel
  and identical seeds. **The statistic is MORE discriminating at the honest denominator, not
  less: 0 of 100 noise draws clear 0.95, against 2 at N = 8**, and the calibrated bar (placebo
  p95) falls 0.8567 → **0.7216**. Every OTHER rate in this table is identical to the last digit
  across the two sweeps (holdout 6%, ls_t≥2 8%, maxIC_t≥2 39%, PBO<50 55%), which is the
  harness-reproduction check — so no other calibrated bar was ever in question.
  **BOTH M1 AND X7 ARE RIGHT AND THEY NEVER CONFLICTED.** The edge's 0.8997 fails the >0.95
  convention (M1) **and sits above ALL 100 placebo draws** (max 0.8649, empirical p ≤ 0.01),
  because at the honest N the 0.95 convention is STRICTER than the noise floor requires.
  **Quote it whole or not at all:** *"Deflated Sharpe 0.8997 at N = 84 — fails the conventional
  >0.95 bar, while sitting above all 100 placebo draws (calibrated bar 0.72)."* It is the one
  bar where this strategy is distinguishable from noise and still fails its threshold.
  **M1 also made the adoption gate harder for noise to pass, as a free side effect:** CPCV
  adopts on **27% → 21%** of pure-noise draws, one-directional (six draws stopped adopting,
  none started). ~~because the adopt gate reads the Deflated Sharpe~~ — **THE MECHANISM WAS
  BACKWARDS; CORRECTED 2026-08-08 (session 12). The direction and the magnitude are right and
  the mechanism was not.** The adopt gate cannot read the Deflated Sharpe: adoption is decided
  at `fundamental_panel.py:2729` and `_dsr_detail` is computed at `:2744`, **downstream of it**,
  on the returns of whichever scheme adoption just chose. What M1 actually changed is
  `_trials_haircut` (`:2097`), which is **floored at the research log's `N`** — and the adopt
  gate multiplies `se` by that haircut. Both the haircut and the DSR read `_trial_N()`; neither
  reads the other. **This matters beyond pedantry, because it means `N` MOVES `ls_t`** — see the
  session-12 bullet below. **This is NOT the run-to-run
  non-reproducibility** — that remains open; it was briefly mistaken for it before the
  one-directional pattern was checked.

  **Use these numbers, not the old ones.** They are floors for THIS panel/universe/69 dates,
  not universal constants — re-measure if the panel changes materially. Three consequences
  that are easy to get wrong: **(a)** 39% of noise draws produce at least one theme at IC
  t ≥ 2.0, because EIGHT themes are tested and the bar is applied to whichever looks best —
  the project has always read that bar as if one theme were being tested; **(b)** the
  **held-out gate (`holdout_theme_validate`) has a measured ~6% false-positive rate**, and
  `low_risk` — the theme actually zeroed on its verdict — turned up among the false confirms
  once in 100 draws, so that decision is not overturned but must be quoted with the rate;
  **(c)** the real headline is outside the placebo's [2.5, 97.5] interval on alpha (clearly),
  Deflated Sharpe, monotonicity, max theme IC t (narrowly) and long-short t (narrowly) — and
  **INSIDE it on PBO**, which is therefore not distinguishable from noise.
- **THE OPTIONS ENTRY SIGNAL IS DEAD, ON CORRECTED DATA (2026-08-05, audit session 5 / R2). The
  project's most consequential negative finding was re-derived after five defects were repaired,
  and it SURVIVED — the gap moved 0.61pp.** Every number in `HANDOFF_universe_backtest.md` was
  computed against a mis-stated underlying price (B1) plus B2/B3/B4/B15, and that file is now
  banner-marked SUPERSEDED. Re-run on the identical pinned 187-name universe:
  **real +3.41%/trade vs a random-entry control's +10.06%, gap −6.65pp, date-block CI95
  [−11.92pp, −2.13pp], paired sign-test z −4.903 (p < 1e−5)** over 1,334 name-year cells (5
  control seeds, 29,785 control trades — see the seed note below). The
  alert's day-selection subtracts value. **Do not describe the live options alert as a
  day-selection edge; it is an alert-generation mechanism.**
  * **THE BREADTH CLAIM IS VOID.** "The edge survives breadth but roughly halves" is false. The
    133 new names are now **−0.47%/trade (PF 0.988)**; all of the book's positive expectancy is
    the original 54 megacaps (**+9.37%**). It is a megacap phenomenon that a corrupted price
    basis made look broader.
  * **B1's signature, for the record:** trades ROSE 3,042 → 3,885 because `no_contract_in_band`
    rejects fell 2,911 → 1,729 — an adjusted spot against as-traded strikes was throwing the
    0.90–1.20 moneyness prefilter, silently discarding 1,182 alerts. Median entry IV
    **1.4200 → 0.2497** at 100% coverage (was 75.3%). 142% was never a vol.
  * **A SINGLE CONTROL SEED CAN FLIP THIS VERDICT — RUN FIVE, AND READ THE SIGN TEST.** The
    control's own mean ranges **+6.46% to +15.34%** across five draws. Seed 0 alone reads
    INCONCLUSIVE and is the most favourable of the five; **all five point estimates are
    negative and four of five are negative at significance.** A random-day book's mean on a
    barbell payoff is set by a few +600% trades. **More control draws SHARPEN the test** (2-seed
    z −2.907 → 5-seed z −4.903), because each name-year cell's control mean averages more draws.
    The paired *t* ranges +0.162 to −1.835 and is never significant even pooled (−1.227, p 0.22)
    — it is the wrong statistic here. **Standing rule: five seeds minimum, sign test carries the
    verdict.**
  * **`term_slope` is REJECTED on the arm that matters (R7).** Its +8.89pp out-of-sample
    replication was an artefact; corrected, the filter makes its own out-of-sample book WORSE
    (gain **−1.12pp** against a +5.00pp bar) and is no longer tail-enriching. It PASSES the
    re-committed retention floor (G3a 95.6 alerts/yr, G3b 96.2% of names and 98.2% of months,
    G3c 35.9%) — so the old 40% constant WAS rejecting a genuinely broad filter, and the
    rejection now rests on economics instead of on an underived number.
  * **Deflated Sharpe fell below 95% on both books:** unfiltered 88.13% → **49.59%**,
    term_slope-filtered 95.69% → **80.63%**. The autopsy re-confirms: 64 features, 127
    hypotheses, **zero survivors**.
- **OPTIONS STATISTICS ARE CLUSTERED, BUT LESS THAN THE AUDIT PREDICTED (2026-08-05, audit R3).**
  Every options interval ever published resampled TRADES and is optimistically narrow.
  `valuation/edge/options_stats.py` adds a date-block bootstrap (calendar months resampled
  together), `n_eff`, the paired name-year sign test and paired *t*, purge/embargo for the CSCV
  splits, and the Deflated Sharpe at `n_eff`. **CORRECTED 2026-08-06 (session-5 closeout): the
  clustering factor is 2.212, NOT 1.85, and it is INSIDE the audit's predicted 2–4 — the record
  said the audit over-predicted and the record was wrong.** The 1.848 (null p95 1.266) was
  measured on the PRE-CORRECTION 3,042-trade book and never updated; the corrected 3,885-trade
  book gives **design effect 2.2121 against null p95 1.2037**, which is what
  `UNIVERSE_RESULTS.json` has always shipped — the artifact was right, the prose was stale.
  **Every options *t* shrinks by √2.212 = 1.487×, not 1.36×**, and **no verdict changes** (checked,
  not assumed: R2 rests on the name-year sign test, the date-block intervals embed clustering by
  construction rather than applying the design effect as a haircut, and
  `deflated_sharpe_clustered` ships alongside the raw figure rather than replacing it).
  * **R3.3 is the one that mattered:** the paired sign test and paired *t* the entire options
    conclusion rested on existed in NO shipped file. They now reproduce the record exactly
    (441 of 1,052 cells, z −5.185 against the recorded −5.24; seed-0 paired t −2.6701 against
    −2.67), pinned by a test.
  * **A RAW DESIGN EFFECT IS NOT EVIDENCE OF CLUSTERING.** Found by a failing test: 600
    independent draws in 12 blocks of 50 report a design effect near 1.8 — pure sampling error
    in MSB/MSW, since that ratio is F(k−1, n−k). Applying it as a haircut would manufacture a
    correction out of noise. The design effect is now scored against its own shuffled null (the
    X7 method) and `clustering_measurable` gates it; the real book passes clearly (**corrected
    book: deff 2.2121 vs null p95 1.2037**; the pre-correction book's 1.848 vs 1.266 is what the
    record used to quote here). **Never quote a design effect without its null — and never
    without its BOOK: that is exactly how the 1.85 figure travelled out of scope.**
- **POINT-IN-TIME LIQUIDITY RAISES THE OPTIONS HEADLINE — the audit expected it to fall
  (2026-08-05, audit O20).** Applying the miner's own screen at each entry date instead of to the
  name's first cached year: **PIT-liquid 3,359 trades at +4.82% vs PIT-illiquid 495 at −7.84%**,
  coverage 99.2%. **But it does NOT rescue the signal** — the control is screened by the same
  rule and benefits too, so on the liquid subset the real book loses to random entry MORE
  decisively (z −3.475, p 0.0005). The headline stays the whole book at aggression 1.0.
  **The audit's premise is half wrong and this is the correction:** names were ranked into the
  mining pool by TODAY's market cap (true), but the liquidity screen was already applied to the
  FIRST CACHED YEAR, not to a present-day chain (`mine_options_cache.py:160`). So O20 is an
  UPPER BOUND on the repair — names that would have failed in 2016 were never mined and no
  evaluation-time filter recovers them.
  **THE PATTERN WORTH KEEPING:** this is the third time in two sessions (R10, then O20) that a
  bias the record assumed ran in the strategy's favour ran the other way. **This project's
  expectations about the direction of its own biases have been wrong more often than right.
  Measure them; do not reason about them.**
- **THE EDGE DOES NOT CLEAR THE DEFLATED SHARPE BAR (2026-08-05, audit M1). The last bar the
  project claimed to clear fails once the denominator is honest.** Every multiple-testing claim
  was computed against `N = 8` — the eight weight schemes. `RESEARCH_LOG.md` is now populated and
  `valuation/edge/research_log.py` feeds the real count into `_deflated_sharpe` and
  `_trials_haircut`. Trial counts **as of this bullet**: equity 84, options 139, infra 1, total 224
  (session 5 added 4 options rows), against the audit's ~146 estimate; `FIXED` correctness rows
  correctly do NOT count. **CORRECTED 2026-08-07 (claims audit): those counts are STALE — measured
  today `research_log.detail()` reads equity 116, options 155, infra 1, total 272 (51 rows counted,
  17 `FIXED` rows not counted). `N` is a project quantity that keeps rising; quote the equity 116
  and the 0.8674 from the session-7 bullet below, not the 84 in the table that follows.** The table
  is kept as the record of what M1 measured on the day it landed.

  | | N = 8 (as shipped) | **N = 84 (measured)** |
  |---|---|---|
  | Deflated Sharpe | 0.9970 | **0.8997** — FAILS the >0.95 bar |
  | `sr0_benchmark` | 0.242 | **0.406** |
  | `metric` self-report | `probabilistic_sharpe_ratio_UNDEFLATED` | **`deflated_sharpe_ratio`** |
  | `_trials_haircut` | 2.04 | **2.977** |

  **There is a real win inside the failure: audit B9 is RESOLVED by measurement.** B9 argued the
  statistic was an undeflated PSR because `sr0` collapsed. With a real `N` it does not collapse —
  `sr0` rises to 0.406 against a per-period Sharpe of 0.550, deflating away 74% of it, and the
  statistic self-reports as a genuine Deflated Sharpe **for the first time**. The price of fixing
  it is that the bar is no longer cleared. That trade was pre-committed before the run.
  Also: **√(2·ln 84) = 2.977**, i.e. the multiple-testing haircut at the real `N` lands within
  0.03 of the Harvey–Liu–Zhu hurdle of 3.0 — exactly as the audit predicted.
  **`N` is domain-scoped** (the equity composite is charged the 84 equity trials, not the 218
  project-wide ones — the options autopsy is a different search for a different product), and a
  missing log degrades to `N = 8`, i.e. to the OLD behaviour, never to an unpenalised one.
- **THE HEADLINE NOW HAS A t, AND THE LONG-SHORT t IS 2.620 NOT 2.836 (2026-08-05, audit R9).**
  `top_decile_alpha` — the number on the front of the product — shipped with **no significance
  statistic of any kind**. It now carries **t +4.517, HAC t +4.376, hit rate 71.0%**. The
  long-short's naive i.i.d. t is joined by **HAC t +2.620** and a Ljung–Box diagnostic.
  **Ljung–Box rejects independence at p = 0.036** (lag-1 autocorrelation +0.189), so per the
  pre-commitment **the Newey–West t is now the number this project quotes** and the naive t is a
  diagnostic only. The 63d windows genuinely do not overlap — that dimension was fine — but
  factor spreads are autocorrelated and nothing anywhere measured it. Note the long-ONLY object
  is far better measured (t 4.38) than the long-short the project has always led with.
  ~~Comparing 2.620 to X7's calibrated floor of 2.14 is apples-to-oranges~~ — **CLOSED
  2026-08-07 (session 10). The floor is now measured on the HAC statistic: 2.28, and the
  headline clears it.** See the next bullet; quote **2.620 vs 2.28**, never 2.620 vs 2.14.
- **THE LONG-SHORT FLOOR IS NOW CALIBRATED ON THE STATISTIC THE PROJECT ACTUALLY QUOTES —
  THE HEADLINE STILL CLEARS, AND THE MARGIN ROUGHLY HALVES (2026-08-07, session 10).** X7
  calibrated 2.14 on the *naive* t; R9 then made the *HAC* t the number quoted, and the two had
  been compared to each other ever since. Re-run of X7's placebo — **same panel, same seeds
  1000–1099, same instrument, n = 100, costs measured; the only change is that the recorder now
  stores the HAC statistic `quantile_backtest` had been computing on every draw since R9 and the
  writer was silently dropping.**
  * **CALIBRATED HAC FLOOR (placebo p95) = 2.2837** (noise median 0.121, max 3.783).
    **Shipped HAC t = 2.61991 → CLEARS**, empirical p **0.03** (3 of 100 noise draws exceed it).
  * **BOTH MOVES GO AGAINST THE STRATEGY AND THE CUSHION HALVES.** The HAC floor is *higher*
    than the naive floor (2.28 vs 2.14) while the real HAC t is *lower* than the real naive t
    (2.620 vs 2.836), so the margin over the floor falls **0.692 → 0.336**. It clears; it clears
    by less than the record implied.
  * **THE OLD MISMATCH WAS MILD, NOT WILD: pure noise clears 2.14 on the HAC statistic 6% of
    the time** against the 5% the bar intends. Worth closing, not a scandal.
  * **THE CONTROL REPRODUCES X7 TO THE DIGIT:** naive p95 **2.1437** → X7's 2.14, noise max
    **3.4360** → X7's 3.44. **One discrepancy, reported not buried:** the `ls_t ≥ 2.0` rate comes
    back **7%** against the recorded **8%** — a single draw, with no draw anywhere near the 2.0
    boundary (nearest 1.885 and 2.067), so it is not rounding. **It cannot be reconciled because
    X7's raw draws were never saved.** This sweep saves all 100.
  * **FREE BY-PRODUCT, and it is the stronger number: the top-decile alpha HAC t now has a floor
    too — 2.2913 — and the shipped +4.376 sits ABOVE ALL 100 NOISE DRAWS (empirical p 0.00).**
    The long-ONLY book remains far better measured than the long-short the project leads with.
  * **R9's autocorrelation finding is corroborated:** Ljung–Box on noise draws has median
    p 0.406 and rejects at 7%, i.e. near nominal — so the real series' p 0.036 is a property of
    the real series, not an artefact the pipeline manufactures.
  * Artifact `data/free_analysis/PLACEBO_HAC.json` (all 100 draws retained); procedure
    pre-committed in `PREREG_session10_hac_floor.md`; **zero trial cost** — a calibration
    searches nothing, equity `N` stays 121.
- **THE UNINVESTABLE BENCHMARK WAS THE HARDEST ONE — the expectation was WRONG in the strategy's
  favour (2026-08-05, audit R10).** Alpha had only ever been measured against an equal-weighted
  average of every name in the panel, charged zero trading cost while the strategy pays. Both the
  audit and this session's own pre-commitment predicted that flattered the product. It does not:

  | benchmark | benchmark /yr | top-decile EXCESS /yr | HAC t |
  |---|---|---|---|
  | equal-weight universe (incumbent, cost-free) | +18.14% | **+7.17%** | +4.376 |
  | equal-weight, charged the strategy's own costs | +16.10% | +9.21% | +5.685 |
  | cap-weighted panel average | +14.85% | +10.46% | +4.292 |
  | **SPY total return** | +15.32% | **+9.99%** | +3.770 |

  Over 2009-01 → 2026-01 the equal-weighted panel returned **+18.14%/yr vs SPY's +15.32%** — a
  ~1,500-name equal-weighted book beat the cap-weighted index over a window starting at the
  post-GFC bottom. So the incumbent benchmark is uninvestable in the direction of being **too
  demanding**. **Keep publishing +7.17% as the headline** — it is the most conservative and the
  one every historical figure used, so changing it would break comparability for a number that
  only moves the flattering way. The edge now also survives an INVESTABLE benchmark: +9.99% over
  SPY (HAC t 3.77). Charging the equal-weight book the strategy's own cost table costs it
  2.04pp/yr, a genuine thumb on the scale that had sat in the strategy's favour and is now gone.
  All four ship in the `benchmarks` block on every run.
- **CPCV WEIGHT ADOPTION MANUFACTURES ~+1.4 OF LONG-SHORT t OUT OF NOTHING (X7, post-hoc —
  treat as a strong hypothesis, not a settled result).** Splitting the 100 placebo draws on
  whether CPCV adopted: when it did NOT (73 draws) mean long-short t is **−0.065** (se 0.119),
  a textbook null; when it DID (27 draws) mean t is **+1.343** (se 0.184) and mean alpha
  +0.82pp. It fires on **27% of pure-noise draws**. Mechanism: the adopted weights are chosen
  on the same panel the headline is then measured on. **The shipped strategy is UNAFFECTED —
  it does not adopt, it keeps `current-default`** — which is measured support for the existing
  rule that a CPCV rejection means keep the defaults. But any future run that DOES adopt a
  CPCV scheme has an optimistically biased headline unless measurement moves off the
  selection panel. Not pre-registered; wants a pre-registered replication.
- **CORRECTED 2026-08-03 (audit B9) — TWO OF THE THREE "statistical bars" MEASURE SOMETHING
  NARROWER THAN THE CLAIM THEY SUPPORT. Lead with the long-short t of 3.52 against the
  Harvey–Liu–Zhu hurdle of 3.0. That one is real.** The other two:
  * **The Deflated Sharpe IS deflating — the audit's mechanism for this one is REFUTED by
    measurement, and only half of its criticism survives.** The audit argued that the eight
    weight schemes are indistinguishable (out-of-sample median ICs spanning +0.061 to +0.062),
    so the cross-trial VARIANCE of Sharpes is ~0, `SR₀ ≈ 0`, and the statistic degenerates to
    Φ(SR·√(n−1)). **Measured on the full-universe run: `var_sr_across_trials` = 0.0276 (sd
    0.166, not ~0) and `sr0_benchmark` = 0.242 against a per-period Sharpe of 0.606** — the
    benchmark is deflating away 40% of the Sharpe. The audit inferred near-identical trial
    SHARPES from near-identical median ICs; those are different quantities, and the Sharpes are
    genuinely dispersed. It saturates because a per-period Sharpe of 0.61 over 110 periods is
    a large z, not because nothing is deflated. Every run now ships
    `deflated_sharpe_detail` (`sr0_benchmark`, `var_sr_across_trials`, `n_trials`) plus a
    `metric` field that reads `probabilistic_sharpe_ratio_UNDEFLATED` **if** `sr0` ever does
    collapse — so this is now a measured property of each run rather than an assumption in
    either direction.
  * **What DOES survive: `N = 8` is not the number of trials this project has run.** The
    ledger records of the order of 146 pre-registered tests. That criticism is untouched by
    the above and is the real one. Until a genuine trial counter exists (audit M1,
    `RESEARCH_LOG.md`, started but deliberately not wired), the deflated figure is computed
    against a denominator that is roughly 18x too small.
  * **PBO 6.7% scores the WEIGHT-SCHEME SELECTION STEP ONLY** — "the best of eight nearly
    identical weightings generalises". It says nothing about the ~146 signal-inclusion,
    theme-membership, universe, standardisation and construction decisions in the ledger, and
    the shipped strategy keeps `current-default` anyway, so the selection being scored is one
    the model never makes. Now shipped as `pbo_scope`.
  * The honest version of both needs a real trial counter (audit M1, the append-only research
    log). **Not done.** At N ≈ 100+, √(2·ln N) ≈ 3.0 — about the Harvey–Liu–Zhu hurdle.
- **B8 IS FIXED (2026-08-06, session 7), AND `low_risk` SURVIVES IT ON HALF THE EVIDENCE THE
  RECORD CLAIMED.** `holdout_theme_validate`'s docstring described a clean protocol — flag a
  theme on one half with a pre-specified rule, then measure removal ONLY on the other half — and
  the code never implemented step 2: `rule_fired` was computed and never read. (Line cite, current
  2026-08-07: it is set at `fundamental_panel.py:3576` and now READ at `:3594`, which is the fix.
  This bullet said `:3545` and the long-cited `:3048` had drifted into an unrelated function —
  **line numbers in this file rot within days; re-resolve before trusting one.**) Two verdicts now
  ship, named for what they are:
  * **`verdicts` / `stability_verdicts` — SEMANTICS DELIBERATELY FROZEN.** This is the
    both-halves check every shipped decision actually rested on, and **X7's measured ~6%
    false-positive rate was calibrated against this exact object** (`scripts/placebo.py:108`
    reads this key). Redefining it in place would have left that 6% describing a gate that no
    longer exists — the same class of error as the stale theme IC table.
  * **`oos_verdicts` — the documented rule enforced.** A direction counts only if its decide
    half flagged the theme. `oos_directions_tested = 0` means **no out-of-sample test was run
    at all**, which is a different statement from a negative result.
  * **NEITHER SHIPPED DECISION CHANGES:** `low_risk` `confirmed_oos`, `insider` `rejected_oos`.
    **But `low_risk` is confirmed in ONE of two directions, not two** — the rule fires only on
    the early half. Quote it whole: *"zeroing `low_risk` is confirmed out-of-sample in one of
    two split directions, and passes a both-halves stability check in both."*
  * **THE PART THAT GENERALISES: three themes (`quality`, `capital_discipline`,
    `institutional`) are `not_flagged` in both directions**, because the rule is `median IC ≤ 0`
    and their ICs are positive. `capital_discipline` is precisely the theme session 6's
    exploratory LOO nominated for dropping. **An IC-gated rule cannot express a
    marginal-contribution hypothesis** — X3's whole finding is that theme IC does not predict
    marginal contribution. Do not reach for `holdout_theme_validate` to adjudicate an ablation.
- **THE FULL-SAMPLE LEAVE-ONE-OUT DOES NOT SURVIVE A TIME SPLIT — SESSION 6'S EXPLORATORY
  RESULT IS NOT A PROPERTY OF THE PANEL (2026-08-06, session 7, LOO — NULL).** Pre-registered
  at `5a27ea1` before any number existed: select the best of seven leave-one-out arms on a
  decide half, measure only that arm on the held-out half, both directions, against the
  MIN_HOLDOUT margins committed before P6 (100bps alpha, 0.25 t).
  * **Direction 1 selects dropping `momentum` (decide +3.68%) → measure −1.30%, LS t −0.706.
    Direction 2 selects dropping `capital_discipline` (decide +2.20%) → measure +0.20%,
    LS t −0.201. Neither clears either margin; different themes selected. VERDICT NULL.**
  * **FOUR OF SEVEN ARMS CHANGE SIGN BETWEEN HALVES** (`momentum`, `insider`, `value`, and
    `capital_discipline` moves 3rd → 1st). Session 6's "+8.54% from dropping
    `capital_discipline`" is the average of +0.20% and +2.20% — carried by the late half.
    **Do not quote a full-sample ablation arm as a finding.**
  * **`size` IS CORROBORATED: it is the WORST arm to drop in BOTH halves independently
    (−2.64%, −3.46%)** — the only theme whose LOO effect is both large and stable. Stated with
    its limit: `size` was never *selected* (the rule takes the maximum), so this is the most
    stable cell in a table that carries no verdict, not a pre-registered result. Enough to say
    **"do not drop `size`, and stop treating its low IC as evidence against it."**
  * **NOT CLAIMED, DELIBERATELY:** `quality` clears both margins on both halves and was
    selected in neither direction, because the pre-registered rule takes the maximum and the
    maximum is the statistic most inflated by noise. Promoting that now would be selecting the
    RULE on the results — session 6's error one level up. Session 8 pre-registers it or nobody
    quotes it.
  * **The expectation was written down first and was RIGHT** (NULL at 70/30), breaking a
    four-run streak of wrong directional calls. One correct call after four wrong ones does not
    license reasoning about direction; keep measuring.
  * **Equity `N` 104 → 111 from this session's 7 arms, then → 116 once a concurrent lane's 5
    equity trials merged. QUOTE 116: Deflated Sharpe 0.8674, √(2·ln 116) = 3.083** (still far
    above X7's 0.7216 floor, still below the 0.95 convention). **`N` is a PROJECT quantity, not
    a session one** — it is now two sessions running that the realised count overshot its own
    pre-commitment, for a different reason each time. Also settled this session:
    **`SUPERSEDED` rows DO count toward `N`** — the schema prose said otherwise and
    `research_log.py` never implemented it; the counter is right and the prose is fixed.
- **SUPERSEDED 2026-08-04 (audit session 2, B6) — EVERY NUMBER IN THE NEXT TWO BULLETS WAS
  MEASURED ON A PANEL WHOSE FIRST THIRD HAD AN INVERTED UNIVERSE. The corrected numbers are
  WORSE and TWO OF THE THREE BARS NOW FAIL. Read the "CORRECTED PANEL" bullet below first;
  the two bullets that follow are kept only as the record of what the defect was producing.**
- **CURRENT FULL-UNIVERSE NUMBERS (2026-08-04, after the audit's Part I corrections):
  long-short t 3.884, top-decile alpha +11.78%, monotonicity −0.988, PBO 13.3%.** Measured
  against a clean pre-audit baseline re-run on identical data (t 3.520, alpha +11.88%,
  monotonicity −0.952, PBO 6.7%): the composite sorts BETTER, top-decile alpha is a rounding
  change, PBO doubles off a low base. The equal-weight benchmark did not move (+16.55% in every
  run), which is the control. **Thirteen corrections and NOT ONE held-out verdict changed** —
  the record's decisions were not resting on the defects, and the defects were not hiding a
  different model. The sanity layer's flag count fell 5 → 2 (the three negative-multiple sign
  flags cleared). Full A/B in `HANDOFF_edge_audit.md` Part 2.
- **The edge clears PBO 13.3% (want <50%), long-short t 3.851 (want >2), top-decile alpha
  +11.69%.** The single biggest driver was zeroing `low_risk`, which passed the both-halves test
  described above (decide on one half, measure on the other, both directions). On the
  pre-registered direction the rule fires on the early half (median IC −0.0308) and, measured
  on the later half, **long-short t goes 0.97 → 2.56 and top-decile alpha +6.09% → +9.30%**; the
  reverse direction agrees more strongly (t 0.55 → 2.57, alpha +6.63% → +14.49%). Do not treat
  the edge as settled — caveats at the end.
- **CORRECTED PANEL, 2026-08-04 (audit session 2, B6+B7+B13) — THESE ARE THE LIVE NUMBERS.
  Long-short t 2.836, top-decile alpha +7.17%, monotonicity −0.891, PBO 73.3%, over 69
  rebalance dates on a genuine 18.5-year window (2008-01-16 → 2026-07-24).** The equal-weight
  benchmark moved +16.55% → +18.14%, which is the control and confirms the universe itself
  changed. **CORRECTED 2026-08-05 (audit session 3, X2+X7) — THE "TWO OF THREE BARS FAIL"
  READING WAS WRONG, IN BOTH DIRECTIONS, AND BOTH ERRORS CAME FROM UNCALIBRATED BARS MEASURED
  ON ONE ARBITRARY GRID.** It used to say: "t 2.836 is BELOW the Harvey–Liu–Zhu hurdle of 3.0
  it used to clear, and PBO 73.3% is far above the <50% bar." Both halves are now retired:
  * **t 2.836 vs the 3.0 hurdle is a GRID ARTEFACT.** X2 re-ran the whole backtest on seven
    equally valid rebalance grids (offsets 0/5/10/20/30/40/50 trading days; the grid always
    started at a hard-coded TD=252 and 62 other grids existed that nobody had ever looked at).
    All seven keep 69 dates over the identical window. **Long-short t ranges 2.703 → 3.517,
    median 2.926, and CLEARS 3.0 on three of the seven.** Quote **"t 2.7–3.5 depending on
    grid, straddling the hurdle"** — never one side of 3.0 as a fact.
  * **PBO <50% IS NOT A BAR AT ALL.** X7's placebo puts the MEDIAN PBO on a definitionally
    worthless signal at **46.7%**, i.e. the "<50%" bar sits exactly at the noise level and has
    almost no power. Calibrated bar is the placebo 5th percentile, **19.7%**. PBO is
    uninformative here in either direction — do not cite it as a pass or a fail.
  * **Top-decile alpha is the one headline that PASSED its robustness test:** spread across
    the seven grids is only **1.30pp** (median **+7.52%**, range +6.84% to +8.14%), against an
    equal-weight benchmark that itself moved 2.08pp across the same grids. The signal-driven
    number is steadier than the market-driven one it is measured against.
  Only the Deflated Sharpe still passes as originally stated — and X7 now DEFENDS it
  (see the calibrated-thresholds bullet below); per B9 the surviving criticism of it is the
  trial denominator, not the statistic.
  **ATTRIBUTED, one change per run, on the full universe — B6 IS ESSENTIALLY THE WHOLE DROP:**
  reverting B6 alone (B7+B13 still fixed) restores t 3.733, alpha +11.36%, PBO 26.7% at 110
  dates, so **B6 costs t −0.897, alpha −4.18pp and PBO +46.7pp — 100% of the PBO blow-out, 88%
  of the t drop, 89% of the alpha drop.** **B7 alone is NULL on the headline** (t −0.010, alpha
  +0.01pp, PBO and equal-weight unchanged to the digit) — a correctness fix with no performance
  consequence, which is the ideal outcome for one. **B13 alone is small and points both ways**
  (t +0.122, alpha −0.51pp, EW −0.24pp): dropping 384 penny names helps the long-short and costs
  the long-only book, consistent with penny names contributing at both ends of the ranking.
  **What this means: roughly 40% of the top-decile alpha was coming from the 41 early rebalance
  dates at which every name present was one that had already stopped trading.** State it as a
  hypothesis, not a finding — a repair's effect on a fitted statistic is not evidence about the
  repair. Costs still clear comfortably: breakeven 134 bps one-way against a **measured** 33.4
  bps realised (B11 — the old "37 bps" was an assumption quoted as a measurement). **No shipped
  decision changed:** `low_risk` still `confirmed` in both split directions, `insider` still
  `rejected`. Full three-way A/B in `HANDOFF_edge_audit.md` Part 3.
- **R1 RE-RUN, DONE 2026-08-05 (audit session 4) — THE THRESHOLD IS CLEARED AGAIN ON THE
  CORRECTED PANEL, AT A LOWER LEVEL AND WITH A DIFFERENT MECHANISM. CLAIM A STILL APPLIES.**
  The pre-commitment in `HANDOFF_r1.md` section 1 was honoured unchanged ("alpha" only if the
  FF5+MOM intercept is positive with NW t > 2.0; ambiguous is a NULL). Re-run on the corrected
  69-date panel → **68 non-overlapping 63d windows, 2009-01-15 → 2025-10-27**, deployed flat
  1/7 weights, NW lag 1. Alignment check passes (SPY on MKT: beta 0.933, R² 0.988).
  * **FF5+MOM alpha +6.99%/yr, NW t +3.984, R² 0.308** on the primary object (`top − ew`).
    **ALL SIX pre-registered specs are positive with t > 2.0** — compound/sum × full/first
    half/second half, spanning **+5.08% to +10.85%**. No disagreement, so the pre-registered
    NULL veto is not triggered. **QUOTE +6.99%/yr (range +5.1% to +10.9%)**; the conservative
    single number is the first half's +5.19%.
  * **THE OLD +8.81%/yr AND THE +6.6%–8.8% RANGE ARE VOID. Do not quote them anywhere.**
  * **THE MECHANISM REVERSED ON TWO OF ITS THREE LEGS — this is the part to re-read.** Now
    loading: **HML +0.251 (t +2.93)** and **UMD +0.205 (t +3.65)**. NOT loading: **SMB +0.208
    (t +1.39)** and **RMW +0.092 (t +0.90)**, both of which loaded strongly in the void run
    (SMB t 3.84, RMW t 4.49). So the old story — "`size`, `quality`, `momentum` ARE the
    standard premia; `value` and `capital_discipline` are not what FF measures" — is
    **backwards on size and profitability** and must not be repeated. Current honest reading:
    momentum is a genuine standard-premium exposure, the book now carries a real VALUE tilt,
    and the size/profitability exposures that dominated the old story were largely an artefact
    of the inverted-universe window B6 removed. R² fell 0.465 → 0.308 — the factor models
    explain LESS of this series than of the void one.
  * The unhedged small-cap tilt caveat WEAKENS for the spread (SMB +0.208, t 1.39, vs +0.885
    before) but SURVIVES for the long-only book (SMB +0.691, t 3.89).
  * Other objects: long-only book in excess of RF **+9.33%/yr (t 4.97)**; long-short
    **+14.86%/yr (t 4.18)**; the equal-weight universe's own unexplained excess +2.34% (t 2.92).
  * **CAVEAT THAT MUST TRAVEL: the secondary q-factor model does NOT clear on the first half**
    (q4 +3.17%, t 1.712; q5 +1.56%, t 0.702), though it clears on the full sample (+6.72%,
    t 3.19) and the second half (+11.49%, t 3.84). The pre-registered threshold is stated on
    FF5+MOM so this does not veto, but the early-period result is model-dependent.
  * Against X7's floor: raw top-decile alpha +7.13% is far outside the placebo null
    [−1.33pp, +2.38pp], so R1 is decomposing something real. **X7 does NOT calibrate a
    factor-regression intercept** — no placebo floor exists for R1's own t, and none was
    invented. Still ONE panel; **X8's international replication is the out-of-sample evidence,
    R1 is not.** Full entry: `HANDOFF_edge_audit.md` Part 5.
- **SUPERSEDED 2026-08-05 by the R1 RE-RUN above. Every number in the next bullet was measured
  on the pre-B6/B7 panel over a window that no longer exists, with a composite no shipped code
  path uses. Kept only as the record of what was claimed. DO NOT QUOTE IT.**
- **SETTLED 2026-08-04 (audit R1) — THE HEADLINE IS NOT MERELY FACTOR EXPOSURE. The word
  "alpha" is now permitted, as a RANGE and with caveats.** `top_decile_alpha` is still
  `4 × (mean top-decile 63d return − mean equal-weighted universe 63d return)` with no risk
  adjustment in it, but that object has now been regressed on the factors it was suspected of
  merely re-assembling. On the full 2,710-name universe, 109 non-overlapping 63-trading-day
  windows (1998-12-31 → 2026-01-21), deployed flat 1/7 weights: **FF5+MOM alpha +8.81%/yr,
  Newey–West(1) t +5.742, R² 0.465**; Hou–Xue–Zhang **q4 +9.14% (t +5.23)**, q5 +8.33%
  (t +4.37); long-short **+12.12% (t +4.14)**. Raw was +12.13%, so **the factor models absorb
  about 27% of the headline and leave the rest** — the opposite of the pre-registered
  expectation. It passes all four pre-registered specs (compound/sum × full/ex-B6), every
  subperiod, every NW lag 0–8, **net of costs (+7.85%, t 5.16)**, and a spanning test adding the
  EW universe's own excess return (+8.25%, t 5.88; universe loading t 0.63, insignificant).
  **QUOTE THE RANGE +6.6% to +8.8%/yr** — +6.6% (t 4.41) is the value after dropping the 37
  B6-contaminated early dates, and is the right single number when only one is wanted.
  **Mechanism:** SMB +0.39 (t 3.84), RMW +0.30 (t 4.49), UMD +0.18 (t 3.49) all load — `size`,
  `quality`, `momentum` ARE the standard premia — but **HML (t 1.08) and CMA (t 1.08) do not**,
  so `value` (six ratios, EV re-priced at the rebalance date) and `capital_discipline`
  (issuance/accruals) are not what FF measures. Not a benchmark artifact: alpha is linear, so
  α(top−ew) = 14.60 − 5.80 = 8.81 exactly and the +5.80% (t 5.41) that FF5+MOM fails to explain
  about the EW universe itself **cancels out of the spread**. **CAVEATS THAT MUST TRAVEL WITH
  IT:** it is still ONE panel — a regression is a control, not new data, and **X8's international
  replication is the out-of-sample evidence, R1 is not**; **t 5.74 is NOT multiplicity-corrected**
  (audit M1 still open), though the deployed weights are flat 1/7 and were never tuned; FF5+MOM
  is a poor description of this universe so read loadings as approximate; the book carries an
  unhedged SMB +0.885 small-cap tilt with borrow/impact/capacity unmodelled; and the benchmark
  is still uninvestable (audit R10). Reconciles with X4 rather than contradicting it — over X4's
  own 2014+ window R1 gets +6.06% (t 3.16) where X4 got t 1.10, because X4 differences two
  high-variance total-return series (low power) while R1 removes that variance first (high
  power). Full write-up and the pre-commitment (written before any number) in `HANDOFF_r1.md`;
  reproduce with `python -m scripts.factor_alpha`, pinned by `tests/test_factor_alpha.py`.
- **R1 FRAGILITY (2026-08-04, same lane) — the result SURVIVED a deliberate attempt to break it,
  but it is WINDOW-DEPENDENT and has a WEAK DECADE, and it is PROVISIONAL until re-run.** Four
  criteria were committed before any cut ran; all four passed. **(1) Stable-universe window
  (≥2008, the closest available preview of what B6 will do): alpha +6.24%, t +3.986, n 73 —
  DOWN 2.57pp, about 29% of the alpha.** The discarded early period is where the raw spread is
  biggest (first third raw +21.89%/yr vs +3.53% and +11.02%), exactly the inverted-universe
  signature. **Expect the post-B6 headline near +6%, not +8.8% — quote ~+6% when one number is
  wanted.** (2) No sign flip: halves +8.98% (t 3.38) / +5.48% (t 3.12); thirds +13.51 (t 3.59) /
  **+4.33 (t 2.412, the weakest cell in the study)** / +8.10 (t 3.82). (3) **Not concentrated:**
  the best 5 of 109 periods carry 23.0% of the alpha (38.0% on the stable window, the criterion
  that came closest to tripping); dropping the best 5 leaves +7.28% (t 5.19), dropping the worst
  5 gives +10.07% — nearly symmetric, and the best 5 are spread across four regimes. (4) **Not
  specification-dependent:** CAPM +12.99%, FF3 +12.28%, FF5-no-MOM +10.03%, FF5+MOM +8.81%,
  q4 +9.14%, q5 +8.33% — all t > 2 on BOTH windows, and **FF5+MOM is nearly the most conservative
  of the six**, so the headline is quoted from the most demanding pre-registered model, not the
  most flattering. **THE ONE THING THAT LOOKS BAD: a ~10-year rolling window centred on 2009-2019
  shows alpha of only +1.66% (t 1.39).** Alpha is positive in 70 of 70 rolling windows and never
  reverses, but 8 of 70 are not significant — the full-sample t 5.742 averages a weak decade in
  with strong ones. Windows confirmed **genuinely non-overlapping** (all exactly 63 factor days,
  zero shared days), so no inference correction is needed. **BINDING: R1 MUST be re-run after B6
  and B7 land** — B6 is expected to lower alpha to +5.5-7.0%; B7's direction is unknown; a
  post-re-run alpha < +4%/yr or full-sample t ≤ 3.0 is a MATERIAL REVISION that requires
  rewriting the headline, and a stable-window t ≤ 2.0 withdraws the word "alpha" entirely. Full
  contract and every cut in `HANDOFF_r1.md` §6-8; reproduce with
  `python -m scripts.factor_alpha_fragility`, pinned by `tests/test_factor_alpha_fragility.py`.
- **Zeroing `insider` was tested the same way and REJECTED — it stays at 0.125.** It helped one
  split direction by a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample
  t-stat is not a stable property. Same reasoning as `low_risk`, opposite outcome — which is
  why every theme change now has to clear `holdout_theme_validate()` before it ships.
- **CORRECTED — "the entire edge is the institutional (13F) theme" is OBSOLETE.** Strip the
  institutional theme now and top-decile alpha is still **+10.6%** with long-short t **2.86**
  (it used to collapse to 0.71). That finding was an artifact of `quality` and `low_risk`
  running on half their inputs. 13F is a contributor, not the whole edge.
- **CORRECTED — `monotonicity`'s SIGN WAS BEING READ BACKWARDS everywhere.** Deciles are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal) and +1.0 = backwards.**
  The old bullet "monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
  cleanly ordered" said the opposite of the truth: −0.68 meant they *were* well ordered.
  Current value −0.939. Pinned by `test_monotonicity_sign_convention`.
- **CORRECTED — `low_risk` does NOT have pooled IC −0.048.** With both its inputs finally
  populated it is **−0.0014 (t +0.71)** on the full universe: indistinguishable from zero.
  It was dead weight, not actively harmful. It is **−0.352 correlated with `size`** — the
  strongest anticorrelation in the theme matrix — so it was cancelling the small-cap tilt,
  which is why removing it helped so much despite having no signal of its own.
- **CORRECTED AGAIN 2026-08-07 (claims audit) — `institutional` coverage is 71.7%, and `insider`
  is 83.1%.** This bullet read "**`institutional` coverage is 61.4%**, not the 81.7% previously
  recorded". 61.4% was measured on the P6-era 110-date panel (that file reads 0.6140 in the same
  field); the current run reads **0.7172**. It rose for a mechanical reason worth knowing: B6
  dropped the 41 pre-2008 dates, and the theme is **empty before 2013-06-30**, so removing empty
  dates raises its coverage without adding any data. Same check on `insider`: **85.0% → 83.1%**
  (0.8504 → 0.8308). Any early-period comparison involving `institutional` is still uninformative
  rather than negative.
- **THEME ICs — CORRECTED 2026-08-06 (session 6, X3 re-run). THE TABLE THAT SAT HERE WAS A
  PRE-B6 MEASUREMENT MISLABELLED "CURRENT", AND `size` IS THE ENTRY THAT MOVED MOST.** It read
  "quality +3.57, momentum +2.62, capital_discipline +2.25, institutional +1.81, size +1.68,
  value +1.52, growth +1.45, low_risk +0.71, insider −0.43". **Proven stale, not inferred
  stale:** re-running `theme_ic` on the old 110-date panel reproduces that list to the digit
  (momentum +2.62, capital_discipline +2.25, institutional +1.81, size +1.68, growth +1.45,
  low_risk +0.71), so it was measured before the B6/B7/B13 corrections of 2026-08-04 and
  carried forward with a date that made it look newer than the panel it came from.

  | theme | void (110 dates) | **CORRECTED (69 dates)** | move |
  |---|---|---|---|
  | quality | +3.57 | **+3.10** | −0.47 |
  | capital_discipline | +2.25 | **+2.76** | **+0.51 — the only riser** |
  | institutional | +1.81 | **+1.55** | −0.26 |
  | momentum | +2.62 | **+1.31** | −1.31 |
  | value | +1.52 | **+0.84** | −0.68 |
  | growth | +1.45 | **+0.75** | −0.70 |
  | low_risk | +0.71 | **+0.46** | −0.25 |
  | insider | −0.43 | **−0.24** | +0.19 |
  | **size** | **+1.68** | **−0.30** | **−1.98** |

  **Against X7's calibrated bar of 2.71, TWO of nine themes clear: `quality` and
  `capital_discipline`.** Under the retired 2.0 convention the void table showed three, and
  X7 measured that 39% of pure-noise draws produce at least one theme at t ≥ 2.0. **`size` is
  now the WORST-ranked theme and the one whose removal costs the most** — see the X3 bullet
  below. sentiment still empty.
- **A FULL BACKTEST IS NOT REPRODUCIBLE RUN TO RUN, AND THE INSIDER THEME IS WHERE IT SHOWS.
  Found 2026-08-04; unexplained; do not build on any single run's insider number.** Three
  full-universe runs on identical data gave `insider` median IC **−0.00335 (t −0.34)**,
  **+0.01551 (t +2.69)** and **−0.00339 (t −0.43)** at unchanged 85.0% coverage. The first and
  third bracket the second and agree to four decimals, so the middle run is the anomaly and
  **audit B26 (the same-day-filing exclusion) is NOT the cause** — an earlier note in this file
  said it was, and that was wrong. B26's effect was measured directly on 22,975 (ticker, date)
  score pairs: it alters **3.96% of scores at a level correlation of 0.9975**, consistent with
  the ~0 IC change between the runs that bracket it. Every other theme is stable to ±0.01 across
  all three runs. **What this means: `insider`'s IC sits so close to zero that its t-statistic is
  not a measurable quantity**, which is exactly why zeroing it came back `not_replicated`
  (Δt +0.08 one direction, −0.09 the other). It is also a reproducibility problem in its own
  right — a project whose memory is its results files needs its results files to be
  deterministic. **Next session: find the nondeterminism before trusting any marginal IC.**
  Audit item **S3** (the `+min(10, 2·buys)` bonus is unconditionally additive; `tanh(net/5e6)`
  saturates regardless of company size) is the thread that might make this theme measurable.
- **Historical note:** `insider` is the only negative theme, and still carries 12.5% weight — but
  zeroing it **did NOT replicate** out-of-sample, so it was deliberately left alone.
- **Theme ICs are NOT stable across time.** `low_risk` flips −0.031 → +0.041 between halves and
  `size` flips t +3.17 → −0.67 (the small-cap premium worked pre-2012, not after). Treat any
  single-period theme IC as weak evidence; the held-out split is what settles a decision.
- **13F is NOT a look-ahead artifact (settled July 2026, 800 names).** Feeding it *fresher,
  not-yet-filed* data at a 15d lag makes it WEAKER, not stronger (t 1.49 -> 0.66, Deflated
  Sharpe 84% -> 44%) — the opposite of the artifact signature. The panel's effective lag is
  already ~111 days (an April rebalance uses the December quarter, public since mid-February),
  i.e. more conservative than the 45d deadline. Its decay curve is sensible: peaks at Q-1,
  alive at Q-2 (t 1.36), dead by Q-3 (t -0.04).
- Edge is strongest in **large caps** (regime IC highest there).
- **P6: THE EDGE SURVIVES TRADING COSTS — BUT ITS COST PROFILE IS STALE. CORRECTED 2026-08-07
  (claims audit).** It read: *"Top-decile breakeven is **236 bps one-way** against a
  **37 bps** actual cost profile (~6.4x margin); net alpha **+11.41%/yr** after costs on 249%
  annual turnover."* On the corrected 69-date panel the `costs` block reads **breakeven 134.1 bps
  one-way against a measured 33.4 bps (4.0x margin), net top-decile alpha +6.07%/yr on 261%
  annual turnover.** (The corrected-panel bullet above already fixed breakeven and the "37 bps was
  an assumption, not a measurement" point (B11); the net alpha and turnover here were never
  updated.) **The conclusion is unchanged — a 4.0x margin still clears comfortably.** The
  bottom-decile figures in the next sentence are P6-era and were NOT re-measured by the claims
  audit — treat them as unverified, not as corrected. The short
  side does not break it either — the BOTTOM decile is *larger*-cap
  than the top ($4.50B vs $1.95B median, 29.8 vs 37 bps), so the long-short t does not rest on
  unborrowable micro-caps. Borrow cost is not modelled (affects the long-short statistic, not
  the long-only book). Quote the BREAKEVEN, not the net alpha — it needs no belief in any
  particular cost calibration. Measured on every run now (`costs` block).
- **P6: three plausible refinements were tested and ALL THREE REJECTED.** Do not re-open them
  without a new reason: **(a) TTM ROE/ROIC is WORSE than quarterly** (roe t +2.84 vs +2.01,
  roic +3.38 vs +2.57) — recency beats smoothing, and the earlier note calling quarterly a
  "wart" was wrong; **(b) median/MAD robust z-scores HALVE the long-short t** (3.485 -> 1.721);
  **(c) consolidating momentum+institutional loses** (LS t 3.48 -> 2.53) — +0.50 correlated but
  complementary, both earn a full weight.
- **P6 lesson worth keeping: a signal's IC can be flat while the composite built from it moves
  a lot.** Robust z-scores left every theme IC essentially unchanged (quality +3.39 -> +3.35)
  while halving the long-short t. Rank-IC is INVARIANT to a monotone rescaling; the composite
  is a weighted SUM of z-scores and is very much scale-sensitive. **Never judge a
  standardization or scaling change by per-signal IC.**
- **CORRECTED — `sector_neutral` WAS silently inert; it is now wired, TESTED, and REJECTED.**
  The old text ("no sector column anywhere on disk ... BLOCKED until TICKERS is downloaded") is
  obsolete: TICKERS was downloaded in P10 and the panel populates `metrics["sector"]` from it.
  Sector coverage is **100.0% of panel rows** (2,710/2,710 names, 11 sectors), so the toggle
  genuinely changes every z-scored theme instead of grouping on a constant. It was then measured
  on the full universe and **rejected in both held-out directions, twice** (P10, and an
  independent re-run 2026-08-02 on a panel that had since gained several signals). Under the
  DEPLOYED weights it raises long-short t 3.396 → 3.896 but COSTS top-decile alpha
  +11.82% → +10.24%, worsens monotonicity −0.952 → −0.915 and nearly doubles PBO 26.7% → 46.7%;
  the later half is worse on both metrics. `sector_neutral` stays **OFF**. Full numbers in
  `HANDOFF_sector_neutral.md`; wiring pinned by `tests/test_sector_neutral.py` so it cannot
  silently go inert again. TICKERS gives TODAY's classification, so applying it to 1998 rows is
  a mild look-ahead — the one non-point-in-time input in the panel, which is a reason to be MORE
  sceptical of a positive sector result, not less. It rejected anyway, so nothing rests on it.
- **P7: THE VALUE THEME WAS CURRENCY-CORRUPTED and is now fixed.** `marketcap`/`ev` are USD but
  the raw line items are in the REPORTING currency, so every value ratio was wrong for the 4.1%
  of rows that report abroad — SK Telecom's `book_to_price` computed to **892 vs a true 0.589**.
  All six value inputs improved after the fix (**value theme t +1.34 → +1.46**), **PBO halved
  13.3% → 6.7%**, monotonicity −0.939 → −0.952, top-decile alpha +11.77% → +11.82%. Foreign
  over-representation in the top decile went **1.35x → 0.56x**; in the live book, foreign names
  fell from 21 of 86 positions (28.3% of weight) to 11 (10.7%).
- **`fxusd` IS A DIVISOR, NOT A MULTIPLIER** — local units per USD (SKM 1514.2 won/USD). Using
  it as a multiplier squares the error. There is **no `netincusd`** column; use `netinccmnusd`.
  `total_equity` must stay LOCAL — `gp_on_capital` divides local gross profit by it.
- **ENTERPRISE VALUE IS NOW PRICED AT THE REBALANCE DATE (2026-08-03, shipped ON).** Sharadar's
  `ev` embeds the FILING-date market cap, so `ebit_ev`/`ev_sales`/`ev_ebitda` measured cheapness
  against a ~111-day-old quote while `earnings_yield`/`fcf_yield`/`book_to_price` used the fresh
  one. `_pit_ev()` re-prices the EQUITY leg to the PIT market cap and holds the DEBT leg at its
  last filed value (net debt is only observable at a filing — that IS point-in-time). Net debt
  must be **currency-converted before it is added** — P7 in a second costume. Re-pricing moves EV
  a **median 5.1%** (26.7% of rows >10%), and `neg_ev_sales` median IC goes **+0.0214 → +0.0363**.
  The BOOK is a wash (LS t 3.396 → 3.520, alpha +11.82% → +11.88%, PBO/monotonicity unchanged,
  net top-decile alpha slightly worse) — **it ships on correctness, not performance.** Stale, not
  look-ahead, so no past result is invalidated upward. New **`ev_freshness`** block (100.0% fresh)
  makes a silent revert loud; `EDGE_EV_POINT_IN_TIME=false` reverts. `HANDOFF_ev_fix.md`.
  STILL OPEN: negative EV (net cash > market cap, 0.70% of rows) is read as maximally cheap by
  `neg_ev_sales` and as expensive by `ebit_ev` — a live sign inconsistency, deliberately not
  bundled into this change.
- **P8: a SANITY layer now runs every backtest** (`sanity_check` block): range / subgroup-pegging
  / market-cap divergence. Coverage says a factor is PRESENT, this says it is SANE — the
  currency bug filled every column and coverage was blind to it. Verified it WOULD have caught
  P7 (foreign names sat at the 86th percentile of book_to_price and earnings_yield pre-fix).
  It legitimately fires twice on corrected data (foreign names really are large caps; 1.45% of
  rows have a >3x market-cap divergence, AIV 71x / EQC 53x). **Do not silence a flag to make the
  run green** — investigate it or record why it is expected.
- **CODE_AUDIT.md's M2 (SanDisk/WDC ~10x) does NOT reproduce.** DAILY cap and shares x price
  agree to 1.6x, the share count is plausible, and the price ran 29.6x over 17 months with zero
  discontinuities (WDC 10.3x, MU 8.5x — the whole storage complex). If it is wrong the error is
  upstream in the PRICE, which both estimates share. Unresolved, not fixed.
- **Standing caveats, do not drop them — TWO OF THEM WERE RETIRED BY MEASUREMENT AND ARE
  CORRECTED HERE 2026-08-07 (claims audit). This bullet says "do not drop them", so both wrong
  caveats were being propagated on purpose; that is why they are corrected rather than deleted.**
  * **The Deflated Sharpe caveat WAS WRONG.** It read: *"Deflated Sharpe is a saturated
    0.9999991 and, per the B9 correction at the top of this section, it is an **undeflated PSR**
    — not a proof of anything."* Both halves are void since M1 (2026-08-05): the shipped run is
    **0.8997 at N = 84 and 0.8674 at the current N = 116** — not saturated — and it self-reports
    `metric = deflated_sharpe_ratio` with `is_effectively_undeflated = false` (`sr0` 0.406
    against a per-period Sharpe of 0.550). **The live caveat is the opposite one:** it is a
    genuine Deflated Sharpe that **FAILS** the >0.95 convention while sitting above all 100
    placebo draws (X7 floor 0.72). Quote it whole, per the M1 bullet.
  * **The B8 caveat is STALE.** It read: *"the test is a **both-halves stability check rather
    than an out-of-sample confirmation** (B8)"*. B8 was fixed in session 7: `oos_verdicts` now
    enforces the documented rule alongside the frozen `stability_verdicts`, and `low_risk` reads
    `confirmed_oos`. The surviving caveat is narrower and is stated in the B8 bullet above —
    **`low_risk` is confirmed out-of-sample in ONE of two split directions, not two.**
  * Still true, unchanged: both halves come from the same panel and universe, and the
    size-cancellation mechanism was hypothesised on the full sample — so neither the decision nor
    the hypothesis generation is out-of-sample in the strict sense. The concentrated top-25 book
    is the noisiest number in the file, and per audit **B17** it holds up to FIFTY names (it sells
    only below `exit_rank = top_n × 2`) and pays neither costs nor taxes, unlike every other book
    in the results file — so it is also mislabelled. Weight-tuning itself remains noise-chasing:
    CPCV still adopts no weighting over the defaults. (All three re-verified 2026-08-07:
    `exit_rank = top_n * 2` at `fundamental_panel.py:1710`, which also ships a `label_warning`
    saying the realised book size is ~`exit_rank`, not `top_n`; `cpcv.adopt = false`.)
- **FIXED 2026-08-04 (audit session 2). The panel is now a genuine 18.5-year window,
  2008-01-16 → 2026-07-24, 69 rebalance dates, cross-sections 1,471–1,954.** `days=None` means
  the whole series and the shared calendar is cut ONCE, before the ffill. Each run ships
  `panel_window` (available vs retained range, the cut, per-date cross-section sizes) so the
  two-blocks-disagree-about-their-window failure cannot recur silently. **41 of the 110 dates
  were dropped and the headline fell with them — see the CORRECTED PANEL bullet above; this was
  the most expensive correction in the audit.** The description below is what the defect WAS:
- **The panel is 27 YEARS long, not 18, and its first third has an INVERTED universe (audit
  B6, FIXED — see above).** `WRDSProvider.price_history` truncates with `.tail(4659)`, so each
  ticker keeps its OWN last 18.5 years and the calendar is the union: 1998-12-31 → 2026-04-22,
  110 rebalance dates over 27.3 years. At a 2001 cross-section every name present is one that
  stopped trading by roughly 2019 — the inverse of classic survivorship bias, and it makes
  roughly the first 37 of 110 periods uninterpretable. Those same 37 dates have no benchmark,
  which is why `construction.n_periods` reads 110 while `portfolio.n_periods` reads 73 in the
  same JSON over undisclosed windows. Direction of the bias is genuinely unclear.
- **FIXED 2026-08-04 (audit session 2, B7/G). There is now ONE composite**, used by selection,
  measurement and live, and it renormalises by the present-weight mass — the convention
  SELECTION already used, so the deployed weights were chosen under it. `CONFIG.sector_neutral`
  and `CONFIG.residual_momentum` now default **false**. **Live and backtest score identically**
  (max abs difference 0.0), pinned by
  `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`. Measured effect on the
  headline: **NULL** (t −0.010, alpha +0.01pp) — the disagreement was real in mechanism but
  small in magnitude on this panel. The description below is what the defect WAS:
- **The LIVE product does not score names the way the backtest does (audit B7/G, FIXED — see
  above).** `screen.py:256` (now **`screen.py:232`**, re-resolved 2026-08-07) calls
  `build_frame(metrics)` with no keyword arguments — it still does, which is now CORRECT because
  the CONFIG defaults are false; at the time it inherited
  `CONFIG.sector_neutral` (default **true**) and `CONFIG.residual_momentum` (default **true**),
  while the backtest forces both `False`. Sector-neutral ranking was tested on the full universe
  and rejected in both held-out directions, twice. **Unless `SCREENER_SECTOR_NEUTRAL=false` is
  set in the environment, the hot list users see is scored under the intervention the research
  eliminated.** There are also three different composite functions in the tree (selection
  renormalises by present-weight mass, measurement does not, live renormalises AND adds the two
  interventions), so **no shipped code path reproduces the backtested composite exactly.**

**HISTORICAL — P5 era, 2026-07-30. DO NOT READ THIS FIRST; MOST OF IT IS SUPERSEDED BY THE
BULLETS ABOVE.** **CORRECTED 2026-08-07 (claims audit): this header used to read "LATEST
(2026-07-30) — SUPERSEDES much of CURRENT STATE above. Read this first." That was true when
written and is now backwards** — `CURRENT STATE` above carries material through 2026-08-06, so
the old instruction sent a cold reader to the OLDEST numbers in the file and told them they
superseded the newest. In particular the "CLEARS both bars for the first time" bullet below
(PBO 13.3%, Deflated Sharpe ~100%, long-short t 3.485, top-decile alpha +11.77%) is **void** —
it was measured on the pre-B6 110-date panel. The live numbers are t 2.836 / alpha +7.17% /
PBO 73.3% / DS 0.8674. The three era headers read newest-to-oldest: **CURRENT STATE (through
2026-08-06) → this section (2026-07-30) → PREVIOUS (2026-07-29).**
- **Five wired factors were SILENTLY EMPTY in every run this project has ever done.** The
  Sharadar export is ARQ-only and Sharadar fills its ratio/averaged columns only in ART/ARY:
  `roe`, `roic`, `assetturnover` are non-null in **0 of 197,265 rows**. `beta` was hard-coded
  `None`. `growth_accel` was overwritten with all-NaN by `build_frame`. So `quality` averaged
  **8 of its 10** inputs, `low_risk` **1 of 2**, `growth` **1 of 2** — with no error, ever.
  All four are now derived from line items that were present all along. `_f()` also returned
  NaN instead of None, which made `_f_score` count MISSING tests as FAILED ones.
- **A coverage guard now exists and would have caught every one of them**: `signal_coverage()`
  warns on any wired signal under 5% coverage and ships a `signal_coverage` block in
  BACKTEST_RESULTS.json. **Never trust a factor's IC without checking its coverage first.**
- **roic (t +3.38) and roe (t +2.84) are the 4th and 6th strongest signals in the panel** and
  were contributing nothing. `quality` is now the strongest theme (t +3.39).
- **`monotonicity`'s SIGN HAS BEEN READ BACKWARDS throughout these notes.** Buckets are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal), +1.0 = backwards.**
  The "monotonicity is negative ... the deciles aren't cleanly ordered" line above is WRONG,
  and P4's "−0.782 → −0.855, slightly worse" was an improvement. Now pinned by a test.
- **`low_risk` zeroed (live, reversible).** Its real full-universe IC is −0.0014 (t +0.71),
  NOT the −0.048 claimed below — dead weight, not harmful. It is **−0.352 correlated with
  `size`**, the strongest anticorrelation in the theme matrix: low-beta/low-vol names ARE
  large caps, so it was cancelling the small-cap tilt. `neg_asset_growth` also dropped
  (t −0.70, wrong sign).
- **The full-universe verdict CLEARS both bars for the first time: PBO 13.3%, Deflated Sharpe
  ~100% (saturated), long-short t 3.485, top-decile alpha +11.77%.** BUT the biggest
  contributor (zeroing low_risk) was chosen by looking at this same panel, so it is
  **in-sample-informed and needs out-of-sample confirmation** — HANDOFF_STATUS.md §5.
- **"The entire edge is 13F" is now OBSOLETE.** Without the institutional theme, top-decile
  alpha is still +10.6% and long-short t 2.86 (was 0.71). That finding was an artifact of
  quality/low_risk running on half their inputs.
- **`insider` is the only negative theme (t −0.34, now −0.43) and still carries 12.5% weight** —
  the obvious next candidate, deliberately NOT changed. **See the reproducibility note above:
  one of three identical-data runs returned +2.69, so this theme's t is not a measurable
  quantity in either direction. The held-out verdict is `rejected` in all three runs.**
- Real full-universe coverage: `institutional` **61.4%** (not the 81.7% below), `insider`
  85.0%. F-Score is **t +2.74** on the full universe, not +5.66.

**PREVIOUS (2026-07-29) — several claims below are corrected above:**
- **800-name large-cap run:** PBO 13%, Deflated Sharpe 77%, first CPCV "adopt" (`ic-ir`), top-decile
  +4.1%/yr vs equal-weight. BUT it's the friendlier large-cap universe (not the fair 3,000), still
  <95%, still ~1/3 13F-dependent. **The full 2,827-name run has STILL never completed** (scoring loop slow).
- **F-Score is the strongest new signal** (IC t +5.66), wired into quality; accruals + 13F-holder-breadth
  also kept. Classic anomalies (reversal, idio-vol, MAX, low-vol) did NOT replicate here.
- **`low_risk` theme has NEGATIVE pooled IC (-0.048)** and CPCV zeroed it — a live factor that's hurting;
  not yet changed (Don's call).
- **`assets` was silently dropped by the loader**, so `capital_discipline` was half-empty in every prior
  run — fixed; treat past capital_discipline conclusions as unreliable.
- **Bulk data loaded fast+safe** via `valuation/edge/bulk.py` (raw zips in `data/raw/`, extracts in
  `data/bulk/`, caches in `data/bulk/prepared/`): SF3 per-manager conviction, DAILY point-in-time
  marketcap+ratios, ACTIONS splits/delistings, EVENTS raw codes.
- **Now CONSUMED by the panel (2026-07-29 s3):** point-in-time market cap from DAILY (replaces the buggy
  shares×price path; AAPL 2015Q2 $722.6B verified), survivorship-free returns via the ACTIONS delisting
  mask (SEP is ALREADY split-adjusted, so split ratios deliberately NOT re-applied — don't "fix" that),
  SF3 conviction exposed as inputs (`sm_conviction/holders/breadth`, not yet in a theme). `institutional`
  coverage 70.5%→81.7%. STILL PENDING: scoring loop unvectorized; **full 2,827-name run has never completed.**

## METHODOLOGY RULE (hard — do not violate)
**CORRECTED 2026-08-07 (claims audit): THE FULL UNIVERSE IS ~2,531 NAMES, NOT ~2,710. This rule
used to name 2,710 and an agent seeing 2,531 could reasonably think it was looking at a subset
and withhold a verdict.** 2,710 was the P6-era 110-date panel (`git show b0f70b6:BACKTEST_RESULTS.json`
= 2,710 names / 110 dates); every run since the B6/B13 corrections of 2026-08-04 reads
**`universe.n_names` 2,531, `n_dates` 69, `label` "full"**. The rule itself is unchanged and the
code enforces it: `WRDSProvider.universe` returns the whole export when `limit` is None or >= its
size, and prints a "SMOKE-TEST SUBSET, not a verdict" banner otherwise (`data_providers.py:388-409`).
Read "~2,710" as "~2,531" wherever it still appears below.

**Report verdicts ONLY from the full ~2,531-name universe.** 400/800-name subsets systematically
flatter results (PBO 13% on 800 → 53% on full; `sm_breadth` t 2.37 on 800 is unverified on full).
**CORRECTED 2026-08-03 (audit B12): the 800-name era was an ALPHABETICAL slice, not the 800
largest.** `WRDSProvider.universe` returned `sorted(keys)[:limit]`, so those runs were names
beginning with roughly A through C. "PBO 13% on 800 → 53% on full" was therefore never measuring
how much a large-cap tier flatters results — it was measuring how much an ARBITRARY 30%
alphabetical subsample does. The function is fixed (ranked by market cap, sort key printed in the
banner, subsets labelled smoke tests), but **every 800-name-era figure needs a full-universe
re-run before it is cited again**: the first CPCV "adopt", PBO 13%, Deflated Sharpe 77%,
`f_score` t +5.66, `sm_breadth` t 2.37, the 13F look-ahead stress test, and the four
classic-anomaly rejections (short-term reversal, idio-vol, MAX, low-vol).
Small samples are dev smoke-tests only ("does it compute / not crash") and MUST be labeled as such —
never the number a keep/reject/adopt decision rests on. The full run is now fast (~75s load + ~11s
score), so there is no performance excuse to judge on a subset. If you must screen small first, say
"smoke test" explicitly and re-run the survivor on the full universe before reporting a verdict.

## IMMEDIATE NEXT TASKS (in order) — item statuses re-checked 2026-08-07 (claims audit)
> **This list is the least trustworthy section in the file. Of the three OPEN items checked
> against the tree on 2026-08-07, TWO were already closed** — #16 rejected with numbers on
> 2026-07-31, #18 shipped — **and #12 had been built in this repo while still routed to Cowork.**
> The list was stamped "updated 2026-07-30" and has taken landings from several sessions since.
> **Check `VALQUO_LEDGER.md` and the tree before starting any item here.**
1. ~~Wire the bulk caches into `build_fundamental_panel`~~ **DONE (2026-07-29 s3)** — PIT market cap from
   DAILY, ACTIONS delisting mask (splits NOT re-applied; SEP already adjusted), SF3 conviction exposed as
   inputs. (Coverage figure in that note was wrong: `institutional` is **61.4%** on the full universe.)
2. ~~**Add unit tests for `bulk.py`**~~ **DONE** — 12 tests.
3. ~~**Speed up scoring + complete the full 2,827-name run**~~ **DONE** — the full run now takes ~12 min
   end to end, and one duplicate full panel build was removed from it (2026-07-30).
4. ~~**P3 — SF3 smart-money conviction**~~ **DONE (P4 commit)** — `sm_breadth` kept, the rest rejected.
5. ~~**Fix hurting factors**~~ **DONE (2026-07-30)** — but only after discovering the factors were EMPTY;
   see LATEST. `neg_asset_growth` dropped (t −0.70), `low_risk` zeroed (IC −0.0014, −0.352 corr with size).
6. ~~**Confirm the `low_risk` removal out-of-sample**~~ **DONE (2026-07-30) — CONFIRMED.** Held-out
   time split, both directions: long-short t +1.59 / +2.02, top-decile alpha +3.21pp / +7.86pp on
   data that did not inform the decision. Now a PERMANENT check: `holdout_theme_validate()` runs on
   every backtest and ships a `holdout_validation` block in BACKTEST_RESULTS.json.
7. ~~**Test zeroing `insider`**~~ **DONE — REJECTED, left at 0.125.** Helped one split direction by
   a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample t is not stable.
8. ~~**TTM ROE/ROIC**~~ **DONE — REJECTED (P6.2).** Quarterly is BETTER (roe t +2.84 vs +2.01,
   roic +3.38 vs +2.57). Recency beats smoothing. Don't re-open without a new reason.
9. ~~**turnover/cost-aware construction**~~ **DONE (P6.1) — THE EDGE SURVIVES COSTS.** Breakeven
   236bps one-way vs ~37bps actual; net top-decile alpha +11.41%/yr. Measured on every run.
10. ~~**median/MAD robust z-scores**~~ **DONE — REJECTED (P6.3).** Halves the long-short t.
11. ~~**Consolidate momentum/institutional**~~ **DONE — REJECTED (P6.4).** Both earn full weight.

**OPEN, in priority order:**

12. ~~**Forward paper-track vs SPY**~~ **BUILT IN THIS REPO — CORRECTED 2026-08-07 (claims
    audit).** This item used to read "the top priority … → **Cowork's lane**. Tell Don to take it
    there." **Do not tell Don that.** It was built in this lane and it is here:
    `valuation/edge/paper_track.py` (its own docstring: "roadmap #12, the project's #1 remaining
    validation"), plus `paper_broker.py` (refuses any non-sandbox endpoint), `options_tracker.py`,
    `track_export.py`, and `tests/test_paper_track.py`. First landed at `cde1579`. The RATIONALE
    is unchanged and still the strongest open argument in the project — the edge has only ever
    seen this one Sharadar panel, and a forward track is the only thing that tests it on data
    nobody has looked at. What remains is elapsed time and reading the track, not building it.
13. ~~**Industry-relative ranking**~~ **DONE — unblocked (P10), then REJECTED and re-confirmed
    2026-08-02.** Sector is wired from TICKERS at 100% coverage and pinned by
    `tests/test_sector_neutral.py`; sector-neutral ranking fails the held-out gate in both
    directions under both flat and deployed weights (it buys long-short t and sells top-decile
    alpha — the wrong trade for a long-only book). Stays OFF. `HANDOFF_sector_neutral.md`.
    A NARROWER variant (sector-relative on the value theme alone) is now cheap to test and is
    the only version worth re-opening.
14. **Watch live behaviour after the P5 deploy.** `low_risk` 12.5% → 0 tilts the hot list
    smaller-cap. Intended, but eyeball the first scans; revert is one line in `settings.py`.
15. ~~**PEAD from EVENTS**~~ **DONE — REJECTED (2026-08-01, independently re-verified
    2026-08-03).** EVENTS code 22 was decoded, so it was finally testable. `pead_car` clears
    the standalone bar (median IC +0.0100, **t +2.215**, coverage 82.3%) but earns no weight;
    `pead_drift` fails outright (t −0.473, coverage 25.1% under the 30% floor). Two reasons the
    reject is solid, both stronger than the IC: **(a)** residualized on the three momentum
    inputs, pead_car's incremental IC t is **+0.020** — 89% of it is orthogonal to momentum and
    that 89% predicts nothing; **(b)** the book gain it does produce is beaten by a control
    using NO earnings data (counting `ret_6_1` twice: +0.83pp alpha vs pead_car's +0.52pp). It
    correlates most with the strongest momentum input and least with the weakest, so it acts as
    an implicit REWEIGHTING, not a new signal. Also **not actually PEAD**: theory says drift is
    strongest right after the announcement, but the recent-only window scores t −0.473 against
    the all-ages +2.215 — backwards. **Held-out deltas for PEAD are CONSTRUCTION-SENSITIVE and
    even flip sign** between the full composite and a restricted-universe book — never quote one
    without naming the book. Both variants stay MEASURED but score in no theme. Point-in-time is
    pinned by `tests/test_pead.py` (12 tests, incl. a tampering test). `HANDOFF_pead.md`.
    Re-open only with real point-in-time earnings surprises (IBES, parked — same blocker as #20).
16. ~~**ML tree combiner**~~ **DONE — TESTED AND REJECTED 2026-07-31. CORRECTED 2026-08-07
    (claims audit): this sat in the OPEN list reading "clearly worthwhile now", one day after it
    had already been rejected with numbers.** Pre-registered results-free at `620e0a5`
    (`valuation/edge/ml_combiner.py`, protocol and adoption bar fixed before any run), then
    rejected at `f53b248` — "TESTED AND REJECTED on every criterion". Numbers (`CODE_AUDIT.md:15`):
    **median OOS IC +0.0531 linear vs +0.0393 GBM; net alpha −8.2pp roth / −4.0pp taxable; fails
    in BOTH halves.** Judged on the same CPCV paths as the linear candidates. **Closed, not
    pending — re-open only with materially more data, not a different model.**
17. **Re-read every past "monotonicity" conclusion with the sign flipped** (see LATEST).
18. ~~**Social preview:** Open Graph + Twitter Card meta tags~~ **SHIPPED — CORRECTED 2026-08-07
    (claims audit).** `valuation/web/templates/_saas_base.html:34-44` carries `og:title`,
    `og:image` (+ `secure_url`, `type`, **1200×630**, `alt`) and `twitter:card=summary_large_image`,
    with a comment that `og:image` must be an ABSOLUTE https URL or LinkedIn/Slack/X silently skip
    it. Only the manual step is left: re-scrape via LinkedIn Post Inspector after a deploy.
19. **Later:** gated auto-apply of adopted weights.
20. **Estimate-revisions sentiment: PARKED** until WRDS/IBES (FMP has no point-in-time revisions at any tier;
    the free `stable/grades` workaround is real but weak and quota-starved). Don't fight the FMP free quota.

## COVERAGE RULE (hard — learned the expensive way 2026-07-30)
**Before reporting or acting on any factor's IC, check its coverage.** Five wired factors were empty
for this project's entire history and nothing surfaced it: an empty column contributes nothing to a
theme mean, raises no error, and the run completes normally. `signal_coverage()` now warns under 5%
and writes `signal_coverage.below_floor` into BACKTEST_RESULTS.json — **read that block first.**
The same class of bug has now bitten four times (`assets` in the loader allowlist, the SF3
positional-arg bug, these five, and `invcap`/`taxexp`/`ebt` missing from `_KEEP`). When adding any
signal, add its source columns to `WRDSProvider._KEEP` and confirm coverage in the next run.

## END OF EVERY SESSION: update `HANDOFF_STATUS.md`
Overwrite `HANDOFF_STATUS.md` in the repo root before you finish — what you did, concrete
numbers (test counts, PBO / Deflated Sharpe / IC / t-stats / alpha, row counts, adopt-or-reject
verdicts), what's blocked and why, and the recommended next step. Plain markdown, no colour
codes, factual. The Cowork agent reads that file directly instead of screenshots.

**Write your full end-of-session report — the complete recap you'd show Don (what shipped,
concrete numbers/verdicts, blockers, the recommended next step) — to your OWN
`HANDOFF_<name>.md`.** The Cowork agent reads that file directly, so Don never has to
screenshot. `HANDOFF_STATUS.md` stays the shared project state; `HANDOFF_<name>.md` is your
session's own full write-up, and parallel agents each own a separate file so they never
clobber each other.

## Working with Don
Concise, direct, honest. He is non-technical but sharp and rightly skeptical — show reasoning and caveats, don't inflate. Unlike the Cowork agent, you (Claude Code) can run commands yourself, so run the backtest/tests directly rather than handing him `.bat` files.

## Tool routing — Claude Code vs Cowork (IMPORTANT: tell Don when to switch)
Don runs TWO agents on this project. They do not talk live; they sync through this shared git repo/folder
(both see the same files). Each agent should explicitly tell Don to switch when a task is in the other's lane.

- **You (Claude Code)** own: running the backtest / `validate_13f.bat` / tests, editing this codebase, git,
  quant research, anything that needs to execute code locally. Do these yourself.
- **Cowork** owns: the Robinhood connector (read-only account data + producing rebalance lists — NEVER
  execute trades), the tracked "Valquo Index vs SPY", scheduled scans/tasks, and phone/mobile sessions.

**Git handoff — CORRECTED 2026-08-07 (claims audit). MERGING IS AUTOMATIC. DO NOT MERGE `main`
BY HAND.** This paragraph used to say: *"Commit directly to `main` in the primary checkout. If your
harness forces a git worktree, you MUST land the work on `main` before ending the session
(`git checkout main && git merge --ff-only <branch>`) … Don deploys from `main` with `git_push.bat`."*
**That instruction is now wrong and acting on it is dangerous** — several agents share the primary
checkout, `main` moves under you mid-session, and a hand-merge there can clobber another lane.
It also contradicted `RUN_RULES.md:76` — the file this brief's own header calls non-negotiable —
which says *"Merging is automatic — the GitHub Action lands any pushed `worktree-*` branch behind
the test gate."* `.github/workflows/land-agent-branch.yml` states the same in its header: *"No local
merge, no Vim, no git_push.bat, no you in the loop."*

**The actual close-out is:** commit in your worktree → `git push -u origin worktree-<name>` →
**verify it landed** (`git fetch origin main -q` then
`git merge-base --is-ancestor HEAD origin/main`). The Action installs deps and runs all 24 suites,
so allow time; if it never lands, the gate failed or the merge conflicted and `main` is
deliberately untouched — do not merge by hand, fix the branch. The original lesson still stands
and is the reason the Action exists: **do not strand work on an unpushed branch** (twice the P5 +
held-out work sat unmerged while `main` stayed on P4). On Windows PowerShell, paste commands on
SEPARATE lines — its old shell rejects `&&`.

When a task needs Cowork, say so plainly, e.g.: **"→ Take this to the Cowork chat — it needs the Robinhood
connector, which I don't have here."** Cowork will likewise send Don back here for heavy backtests/code.
After you commit changes, the Cowork agent sees them in the same folder next time Don opens it.

Current handoff state (July 2026): task #1 is **done** — the 13F signal has been fairly tested and is real
but too weak to trade alone (details in CURRENT STATE). Do not spend more effort tuning or re-testing 13F.

**CORRECTED 2026-08-07 (claims audit): the rest of this paragraph said "The ball is now on task #2,
estimate revisions, which needs an API key from Don (FMP or Intrinio)." Do NOT ask Don to buy that
key.** It contradicts roadmap item **#20** in this same file, which is the researched conclusion:
**FMP has no point-in-time revisions at ANY tier**, so a paid FMP key would not unblock it; the real
source is IBES, i.e. WRDS. `HANDOFF_data_spend.md` reaches the same verdict independently ("no
purchasable retail option exists at any price"). The item is **PARKED**, not waiting on a purchase.
Note also that this paragraph's numbering ("task #2") is its own, and does not match the numbered
roadmap above — estimate revisions is **#20** there.
