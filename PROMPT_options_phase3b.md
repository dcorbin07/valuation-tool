# Claude Code — Options phase 3 (continuation): unblock, arrest the fade, VRP arm, live confidence + sizing

**Status:** phase 3 adopted whole-contract sizing (honest P&L $55–84k, 50–63% concentration) and REJECTED
65–75 DTE (it inherited the fade). **The core research is still undone and §0 (landing on `main`) is
BLOCKED.** This prompt finishes the mandate. Reuse the cached ThetaData (2016–2025, 55 names). Pre-commit
each gate results-free; keep only what helps; commit to `main` at the end.

## 0. Unblock and LAND first — do not start new research until this is done
§0 is blocked: the options work (phases 1–3) is not cleanly on `main` (risk of stranding on the worktree).
Diagnose the blocker (likely worktree/main divergence), resolve it, land phases 1–3 on `main`, tests green.
If it can't fast-forward, do a real merge and **regenerate** BACKTEST/HANDOFF rather than hand-resolve.

## 1. §2 — new ThetaData signals, judged on the 2021–2025 FADE (the make-or-break research)
DIY from cached data (tick trades + OI + IV; gamma from Black-Scholes): IV rank/percentile, variance risk
premium (IV vs realized), term structure, skew, tick flow (sweeps/blocks/net premium/aggressor), GEX
(OI + gamma-by-strike). **Judge each specifically on the recent half (2021–2025), where the edge fades** —
a signal only earns its place if it lifts the LATE-half expectancy or filters the 2022/23/25 losing years.
Through the held-out gate; expect most to reject. This decides whether the edge is durable or just decaying.

## 2. §4 — VRP / credit-spread arm + correlation with the long arm
Port the options-bot strategy/risk/earnings; run the put-credit-spread backtest on the cached history
through the same gate + a portfolio/correlation layer (reuse the options-bot Ledoit-Wolf vol targeting).
Report its tail-dependence, hit rate, drawdown, and — the key number — **its return correlation with the
single-leg arm**, especially in single-leg's negative years (2022/23/25). Low/negative correlation that
smooths the combined book is the whole point.

## 3. §5 — options-bot engine fold-in + deconstruct
Per OPTIONS_BOT_INTEGRATION.md: reconcile bs_pricing with the local greeks, fold in stop-gap-through fills,
the no-edge self-test, AsOfHistory, occ_symbol; deconstruct the copied options-bot (keep/relocate/delete);
retire the old underlying-return "screaming-buy" data + UI.

## 4. §6 — live engine + tracked book, with per-alert CONFIDENCE + SIZING (new)
Wire surviving signals into the live scan + expectancy scorecard + a tracked options book (whole-contract
sizing, moderate convex sleeve, report annualized net-of-cost AND after-tax returns vs the index). AND, per
alert, add two fields:
- **Confidence level** — data-driven from the backtest bucket matching this alert's fingerprint (score band
  × IV regime × delta × DTE): its expectancy AND closed-trade count. Grey/"low confidence — thin sample"
  under the 30-trade floor, and **down-weight for the recent-half fade** (the edge is weaker 2021–2025, so
  confidence must reflect that, not the full-sample flatter). **Frame it honestly: confidence = "positive-
  expectancy bucket with adequate sample," NOT a win probability** — the hit rate is only ~37%, so it must
  never read as "this will go up."
- **Suggested sizing** — **whole contracts** at the user's dollar-risk budget:
  `contracts = floor(budget / (premium × 100))`, scaled by confidence (higher → toward top of budget, lower
  → smaller), and **skip if one contract exceeds the budget**. Display "suggested: N contracts (~$X)" — a
  suggestion the user executes, never auto-traded.

## Close-out
Coverage guard + sanity + costs every run; tests green; regenerate OPTIONS_BACKTEST_RESULTS + HANDOFF +
master roadmap; **commit to `main`**. Do NOT re-open rejected items (spreads for the long arm, the
conviction tier, 65–75 DTE). Small/mid-cap expansion (roadmap 22b) is the next iteration — needs a fresh
pull; note it, don't start it here.
