# Claude Code — Options phase 3: land it, adopt sizing, arrest the fade, add the VRP arm

**Phase 2 result:** scream-buy single-leg is validated — +10.4%/trade, PF 1.30, positive in both held-out
halves, and **broad, not tail-dependent** (+8.96%/trade excluding the top 15; 30.7% of trades ≥ +100%) once
sized by **fixed dollar risk, not 1 contract/signal**. Single-leg beats spreads (+12.33% vs −4.46%); no
conviction tier (the tail is unpredictable). **The one real caveat is FADING: +16.4% (2016–2020) → +4.4%
(2021–2025), with 2022/23/25 negative.**

**So this phase is about durability, not more confirmation:** land what's done, adopt the sizing fix, and
find out whether new signals or a second (short-vol) arm can arrest the fade. Pre-commit each gate
results-free before running; expect most §5 signals to reject; keep only what helps. Reuse the cached
ThetaData history (2016–2025, 55 names).

## 0. Land phase 2 first — don't strand it
Phase-2 work is committed on the worktree but **not on `main`** (main is pre-phase-2). Merge it to `main`
(git_push.bat auto-FF, or manual), confirm tests green (88/88), so it's on GitHub before building further.

## 1. Sizing — WHOLE CONTRACTS to a dollar-risk target (correct the idealized fixed-$ from phase 2)
Options trade in **whole contracts only** — no fractional contracts — so phase-2's "fixed dollar risk"
number was idealized and overstates the de-concentration. Size realistically:
**contracts = floor(risk_budget / (premium × 100)), minimum 0**, and **skip any trade whose single
contract exceeds the budget.** For a ~$3.3k account that naturally excludes the $1,000+/contract names
(pre-split AMZN, etc.) that dominated the raw P&L — which is the correct outcome, not a workaround, and it
dovetails with the small/mid-cap idea (cheaper contracts → affordable → more positions).
Re-measure dollar P&L and tail-concentration on THIS whole-contract basis; the true figure sits between
the 1-contract (98% concentrated) and the idealized fixed-$ (42%) versions.
**Keep the percentage-expectancy metrics as the primary "is the edge broad" evidence — they're
sizing-independent** (a +150% trade is +150% regardless of contract count), so +8.96%/trade ex-top-15 and
30.7% of trades ≥ +100% stand no matter how sizing shakes out. Make whole-contract-to-budget the default
in backtest, scorecard, and live.

## 2. §5 — new signals, aimed squarely at ARRESTING THE FADE (each pre-committed, through the gate)
DIY from the cached ThetaData (tick trades + OI + IV; gamma from Black-Scholes): IV rank/percentile,
variance risk premium (IV vs realized), term structure, skew, tick flow (sweeps/blocks/net premium/
aggressor), GEX (OI + gamma-by-strike).
- **Judge each on the RECENT half (2021–2025), where the edge is fading.** A signal that lifts the
  *late-half* expectancy or filters out the 2022/23/25 losing years is worth far more than one that only
  helps the already-strong early half. Keep only what improves the fade, through the held-out gate.

## 3. §4b — the 65–75 DTE refinement (cheap, found in phase 2)
65–75 DTE more than doubled 45–55 DTE (+17% vs +7.8%) but was never gated. Run it through the held-out
gate; if it holds, adopt the longer DTE. (35-delta is already confirmed optimal — leave it.)

## 4. VRP / credit-spread arm — the counter-cyclical complement
Long-vol single-leg is fading; a short-vol arm may carry when it doesn't. Port the options-bot
strategy/risk/earnings; run the put-credit-spread backtest on the cached history through the same gate + a
**portfolio/correlation layer** (reuse the options-bot's Ledoit-Wolf vol targeting). Report its
tail-dependence, hit rate, drawdown, and — the key number — **its return correlation with the single-leg
arm.** The value is a low/negative correlation that smooths the combined book, especially in the years
single-leg was negative (2022/23/25).

## 5. Fold in the options-bot engine (Phase A) + deconstruct
Per OPTIONS_BOT_INTEGRATION.md: reconcile bs_pricing with the local greeks already built, fold in
stop-gap-through fills, the no-edge self-test, AsOfHistory, occ_symbol; deconstruct the copied options-bot
(keep/relocate/delete). Retire the old underlying-return "screaming-buy" data + UI here.

## 6. §6 — live engine + tracked options book (size to the verdict)
Wire the surviving signals into the live scream-buy scan + expectancy scorecard; emit a tracked options
book on **fixed-$-risk sizing**, sized as a **moderate convex sleeve** (real + broad but fading → not
aggressive). Report an **annualized net-of-cost AND after-tax account return** so it's comparable to the
stock index (roth +17.4% / taxable +4.86%).

## Close-out
Coverage guard + sanity + costs on every run; keep tests green; regenerate OPTIONS_BACKTEST_RESULTS +
HANDOFF_STATUS + the master roadmap; **commit to `main`** (don't strand). Do NOT re-open rejected items
(spreads for the long arm, the conviction tier, the rejected stock signals). The **small/mid-cap universe
expansion (roadmap 22b)** is the NEXT iteration after this — it needs a fresh ThetaData pull, so note it,
don't start it here unless everything above lands cleanly.
