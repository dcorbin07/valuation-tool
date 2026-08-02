# Claude Code — Options phase 2: robustness (§4–§6 + tail analysis + engine fold-in)

**Verdict from phase 1:** the 55-name single-leg scream-buy backtest is validated — **+10.4%/trade net of
spread, positive in both held-out halves** — BUT **15 trades = 98% of dollar profit**, so the honest read
is "positive but thin, fading, too tail-dependent to size aggressively." The edge is real but fragile.

**Goal of this phase: robustness, not more confirmation.** Find a construction or signal that trades some
of that fragile tail for consistency, and size to the honesty of the edge. Reuse the cached ThetaData
history (2016–2025, 55 names). Pre-commit each test's gate results-free before running, as before. Expect
most §5 signals to reject — the wins are the tail analysis, the construction comparison, and the 1–2
filters that de-concentrate the profit.

## 1. Tail-dependence analysis — do this FIRST; it decides whether any of this is sizeable
- Identify the 15 trades that are 98% of dollar profit: which names, dates/regimes, score/IV/DTE buckets,
  and what setup they shared.
- Is the edge "occasionally catch a moonshot in a momentum blowup" (unsizeable), or "a few big winners is
  the normal shape of convex options and the rest roughly break even" (expected, sizeable with discipline)?
- **Re-report expectancy with the top-15 winners EXCLUDED.** If it goes negative, the edge *is* the tail;
  if it stays modestly positive, the tail is upside on a real base. This is the single most important
  number for tradeability.
- **Home-run fingerprint → a high-conviction "scream-buy+" tier (priority feature).** Since ~15 trades are
  the whole edge, the payoff is recognizing those setups when they recur. Characterize what the 15 shared
  (score, IV rank, momentum/technical, DTE, delta, flow, regime) on ONE half, then **test whether that
  fingerprint flags the outsized winners in the HELD-OUT half.** If it replicates → build a distinct
  top-tier **conviction** alert (visually louder + a larger sizing multiple than the routine scream-buy),
  so the rare big ones are unmistakable and sized up. If it does NOT replicate → report that the tail is
  unpredictable and do NOT build false emphasis (that itself caps how much anyone should size this). Must
  clear the held-out gate — do not curve-fit an alert to 15 in-sample points.

## 2. §4 — single-leg vs vertical debit spread (built, never run)
- Run the matched vertical-spread version of every signal. Compare expectancy, hit rate, profit factor,
  max drawdown, AND **tail-dependence** (what % of profit is the top 15 trades?), overall and by IV-rank
  regime.
- The question: does the spread trade the fragile tail for a steadier, sizeable edge? Given the single-leg
  verdict, a more robust (even if lower) spread edge may be the better product.

## 3. §5 — new signals as filters/enhancers (each pre-committed, through the gate)
DIY from the cached ThetaData (Standard = tick trades + OI + IV; gamma computed from IV):
IV rank/percentile, variance risk premium (IV vs realized), term structure, skew, tick flow
(sweeps/blocks/net premium/aggressor), GEX (OI + gamma-by-strike).
- **Keep only what improves expectancy AND reduces tail-dependence.** A signal that raises the hit rate or
  de-concentrates the profit is worth more here than one that just lifts raw expectancy.

## 4. VRP / credit-spread arm (Phase B — now higher priority given the fragile single-leg)
The short-vol VRP arm (put credit spreads from the options-bot) is the natural robustness complement —
inherently higher hit rate, more consistent. Port the options-bot strategy/risk/earnings; run its
single-stock backtest on the cached history through the same gate + a **portfolio/correlation layer**
(reuse the options-bot's correlation-aware vol targeting). Compare its robustness (tail-dependence, hit
rate, drawdown) head-to-head with single-leg and spreads.

## 5. Fold in the options-bot engine (Phase A) — while you're in this code
Deconstruct the copied options-bot per OPTIONS_BOT_INTEGRATION.md (keep/relocate/delete). Fold in
`bs_pricing` (+ computed gamma), stop-gap-through fills, the no-edge self-test, the `AsOfHistory`
look-ahead guard, `occ_symbol`. Retire the old underlying-return "screaming-buy" data/UI here.

## 6. §6 — live engine + tracked options book (size to the verdict)
Wire the winners into the live scream-buy scan + expectancy scorecard; emit a tracked options book.
**Size it to the honesty of the edge:** "too tail-dependent to size aggressively" → a small capped convex
sleeve, not a core allocation; reflect that in sizing and the UI framing. Report an **annualized
net-of-cost AND after-tax account return** so it's comparable to the stock index (roth +17.4% / taxable
+4.86%).

## Close-out
Coverage guard + sanity + costs on every run; keep tests green; regenerate OPTIONS_BACKTEST_RESULTS +
HANDOFF_STATUS + the master roadmap. Commit to `main` (don't strand on a worktree). Do NOT re-open the
rejected stock items.
