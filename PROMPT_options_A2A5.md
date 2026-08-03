# Claude Code — Automate the merge, then FINISH the options track (A2–A5)

Tighter scope than the last prompt (which was too big for one session). Do item 0 first, then A2–A5 in
order, commit each. Pre-commit each research gate results-free. Reuse the cached ThetaData (55 names,
2016–2025). Detailed specs for A2–A5 are in `PROMPT_phase4_big.md`; this is the completable slice.

## 0. (Removed) — merge automation is OFF your plate
Do NOT touch `git_push.bat`. Your harness can't invoke `cmd.exe` to actually test a Windows script, and an
unverified deploy script is worse than a manual merge (the v2 attempt already introduced LF line endings
that would make the `.bat` non-executable). Don handles the merge with `git merge --no-edit`; the durable
automation will live in a GitHub Action, not a local `.bat`. **Focus this session entirely on A2–A5**, and
push your worktree branch to origin as usual so Don (or the future Action) can land it.

## 1. A2 — make iv_rank testable + test tick flow
Build a **daily ATM-IV series per name across all trading days** from the cached ThetaData (iv_rank had
only ~28 obs from alerts → 0% coverage). Then test iv_rank on the 2021–2025 fade like the other §2 signals.
Test tick flow if the feed is available. Each pre-committed; keep only what lifts the LATE half.

## 2. A3 — VRP / credit-spread arm + correlation with the long arm
Port the options-bot strategy/risk/earnings; run the put-credit-spread backtest on the cached history
through the same gate + a portfolio/correlation layer (Ledoit-Wolf vol targeting). Report tail-dependence,
hit rate, drawdown, and — the key number — **return correlation with the single-leg arm**, especially in
single-leg's negative years (2022/23/25). Low/negative correlation that smooths the combined book is the prize.

## 3. A4 — options-bot engine fold-in + deconstruct
Per OPTIONS_BOT_INTEGRATION.md: reconcile `bs_pricing` with the local greeks, fold in stop-gap-through
fills, the no-edge self-test, AsOfHistory, occ_symbol; deconstruct the copied options-bot
(keep/relocate/delete); retire the old underlying-return "screaming-buy" data + UI.

## 4. A5 — live engine + tracked book + per-alert confidence + sizing
Wire the surviving signals (single-leg + term_slope + anything from A2) into the live scan + expectancy
scorecard + a tracked options book (whole-contract sizing, moderate convex sleeve, annualized net-of-cost
AND after-tax returns vs the index). Per alert: **confidence** (backtest bucket expectancy + sample size;
capped "thin" under 30 closed; down-weighted for the fade; framed as expectancy-confidence, NOT a win
probability — hit rate ~37%) and **suggested whole-contract sizing** (floor(budget/(premium×100)),
confidence-scaled, skip if one contract > budget; a suggestion, never auto-traded).

## Close-out
Coverage guard + sanity + costs every options run; tests green; regenerate OPTIONS_BACKTEST_RESULTS +
HANDOFF_STATUS + master roadmap; commit each item. Do NOT re-open rejected items (spreads for the long arm,
conviction tier, 65–75 DTE, skew/VRP/gex signals, ML combiner, PEAD, rejected alt-data).
**Parts B (app fixes) and C (growth valuation) are the NEXT prompt — not this one.** Small/mid-cap
expansion (22b) needs a fresh ThetaData pull — later.
