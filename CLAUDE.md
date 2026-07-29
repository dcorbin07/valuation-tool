# CLAUDE.md — Valquo project brief (read every session)

You are picking up **Valquo** (valquo.co), a Python/Flask stock-analysis SaaS owned by Don
(donniecorbin6@gmail.com). Be honest, concise, and never oversell. Architecture is in section 4 below;
the optimization/data research roadmap is in `OPTIMIZATION_RESEARCH.md` — read it once for detail.

## What it is
Hot-stocks screener (9-theme "hot score") + options/intraday signals + a point-in-time fundamental
**backtest / Edge Lab** that proves-or-disproves the edge and tunes the screener weights. A monthly,
purely-statistical, out-of-sample-gated self-learning loop re-tunes weights.

## How to run (you can run these directly — Don cannot / will not)
- Full backtest: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --json data/backtest/last_result.json` (or `run_backtest.bat`). Reads licensed Sharadar exports in `data/backtest`. Takes 20-40 min.
- 13F due-diligence: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --validate-institutional` (or `validate_13f.bat`).
- Tests (keep green, currently 16/16): `python tests/test_edge.py`.
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
On the fair 3,000-name universe (~18y, gross of costs):
- **The edge is NOT statistically credible yet: Deflated Sharpe ~18% (want >95%), PBO ~80%** (weight-tuning is mostly overfitting).
- **On CPCV, no weighting beats the defaults** — the earlier `max-ir-decorr` "win" was an artifact of the weaker single-split test.
- **The entire edge is the institutional (13F) theme.** Remove it and the long-short t-stat goes 1.31 -> -0.01, top-decile alpha +3.9% -> +1.5%. ~40% weight sits on one lagged quarterly signal.
- Edge is strongest in **large caps** (regime IC highest there). Concentrated top-25 loses; broad top-decile is the only thing that beats equal-weight.
- **13F is NOT a look-ahead artifact (settled July 2026, 800 names).** Feeding it *fresher, not-yet-filed*
  data at a 15d lag makes it WEAKER, not stronger (t 1.49 -> 0.66, Deflated Sharpe 84% -> 44%) — the
  opposite of the artifact signature. The panel's effective lag is already ~111 days (an April rebalance
  uses the December quarter, public since mid-February), i.e. more conservative than the 45d deadline.
- **But 13F is still not tradeable standalone:** best case t=1.49 (want >2), Deflated Sharpe 84% (want >95%),
  and **monotonicity is negative at every lag** (-0.68 at best) — the deciles aren't cleanly ordered.
  Decay curve is real and sensible though: peaks at Q-1, alive at Q-2 (t 1.36), dead by Q-3 (t -0.04).
- **Coverage gap:** the institutional theme is **empty before 2014** (13F data starts 2013-06-30) — non-null
  in only ~55% of panel rows. "The whole edge is 13F" rests on a factor absent from the first ~14 of 18 years.
  Worth a separate look: re-check the no-13F comparison on the 2014+ window only.
- Conclusion: more tuning = chasing noise (proven). The levers are **new orthogonal data** — not more
  optimization, and not more 13F work; that signal has now been fairly tested and is real but too weak alone.

## IMMEDIATE NEXT TASKS (in order)
1. ~~**Re-run `validate_13f.bat`, then interpret it.**~~ **DONE (July 2026)** — see CURRENT STATE above.
   Verdict: 13F is real-but-weak, **not** a look-ahead artifact. Two bugs found and fixed en route:
   (a) the old `(45, 60, 90)` lag grid was **structurally inert** — rebalance dates land 11-21 days past a
   quarter start and 13F rows are stamped quarter-END, so all three lags resolved to the SAME filed quarter
   and always printed three identical rows (>111d is needed to cross a boundary). Now `INST_LAG_GRID =
   (15, 45, 135, 225)`, guarded by `test_inst_lag_grid_crosses_quarter_boundary`. The earlier "500-name
   check shows the edge FADING HARD" note was wrong — that difference cannot exist on this grid; disregard it.
   (b) printing to a **redirected** stdout crashed with `UnicodeEncodeError` (cp1252 vs the `→`/`—` chars),
   so the `.bat` wrappers reported "failed" on successful runs; `main()` now reconfigures stdout to UTF-8.
2. **Estimate-revisions signal** (Don chose this) — integrate analyst estimate revisions/dispersion (FMP or Intrinio; needs Don's API key) to fill the empty `sentiment` theme. Point-in-time history required.
3. **ML tree combiner** — a regularized gradient-boosted-tree scheme (scikit-learn, make the import OPTIONAL so it never breaks Don's run), validated under CPCV/Deflated Sharpe; adopt only if it honestly wins.
4. **Gated auto-apply** — `/admin/adopt-backtest-weights` should consume `recommended_weights_full` (only set when CPCV/walk-forward adopt). Hold the first live flip until #2 checks out (#1 is done and did NOT clear the bar).
5. **Tracked "Valquo Index" vs SPY** (Cowork side) — broad top-decile, large-cap-tilted paper book; keep the user hot list short.

## END OF EVERY SESSION: update `HANDOFF_STATUS.md`
Overwrite `HANDOFF_STATUS.md` in the repo root before you finish — what you did, concrete
numbers (test counts, PBO / Deflated Sharpe / IC / t-stats / alpha, row counts, adopt-or-reject
verdicts), what's blocked and why, and the recommended next step. Plain markdown, no colour
codes, factual. The Cowork agent reads that file directly instead of screenshots.

## Working with Don
Concise, direct, honest. He is non-technical but sharp and rightly skeptical — show reasoning and caveats, don't inflate. Unlike the Cowork agent, you (Claude Code) can run commands yourself, so run the backtest/tests directly rather than handing him `.bat` files.

## Tool routing — Claude Code vs Cowork (IMPORTANT: tell Don when to switch)
Don runs TWO agents on this project. They do not talk live; they sync through this shared git repo/folder
(both see the same files). Each agent should explicitly tell Don to switch when a task is in the other's lane.

- **You (Claude Code)** own: running the backtest / `validate_13f.bat` / tests, editing this codebase, git,
  quant research, anything that needs to execute code locally. Do these yourself.
- **Cowork** owns: the Robinhood connector (read-only account data + producing rebalance lists — NEVER
  execute trades), the tracked "Valquo Index vs SPY", scheduled scans/tasks, and phone/mobile sessions.

When a task needs Cowork, say so plainly, e.g.: **"→ Take this to the Cowork chat — it needs the Robinhood
connector, which I don't have here."** Cowork will likewise send Don back here for heavy backtests/code.
After you commit changes, the Cowork agent sees them in the same folder next time Don opens it.

Current handoff state (July 2026): task #1 is **done** — the 13F signal has been fairly tested and is real
but too weak to trade alone (details in CURRENT STATE). The ball is now on **task #2, estimate revisions**,
which needs an API key from Don (FMP or Intrinio). Do not spend more effort tuning or re-testing 13F.
