# Claude Code — Phase 4 (LARGE): finish the options track, then clear the live-app backlog

**Assumes phases 1–3b are merged to `main`** (Don runs the merge manually: `git checkout main && git merge
worktree-p24-shortinterest && python tests/test_edge.py && .\git_push.bat`). Work **top-to-bottom**,
pre-commit each gate results-free, and **commit each item to `main`** so partial progress lands while
unattended. Get as far as you can.

**Phase 3b context:** term structure (`term_slope`) ADOPTED — nearly triples the fading late-half
expectancy (+4.76%→+12.88%), repairs 2022/2023, worsens 2025, discards ~60% of alerts. skew/VRP/gex
rejected; iv_rank + tick flow still UNTESTED.

## PART A — finish the options track (primary)
**A1. Wire `term_slope` as a standing live filter.** Only fire (or mark full-confidence) in contango;
suppress/flag in backwardation. Account for the ~60% alert reduction in sizing. Config flag, reversible.
**A2. Make iv_rank testable + test tick flow.** Build a **daily ATM-IV series per name across all trading
days** from cached ThetaData (iv_rank had ~28 obs → 0% coverage), then test iv_rank on the 2021–2025 fade.
Test tick flow if the feed is available. Each pre-committed; keep only what lifts the late half.
**A3. §4 — VRP / credit-spread arm + correlation.** Port options-bot strategy/risk/earnings; run the
put-credit-spread backtest on cached history through the gate + a portfolio/correlation layer (Ledoit-Wolf
vol targeting). Report tail, hit rate, drawdown, and — key — **return correlation with the single-leg
arm**, especially in 2022/23/25. Low/negative correlation that smooths the book is the prize.
**A4. §5 — options-bot engine fold-in + deconstruct** (unblocked by the merge). Per
OPTIONS_BOT_INTEGRATION.md: reconcile bs_pricing with local greeks; fold in stop-gap-through fills, the
no-edge self-test, AsOfHistory, occ_symbol; deconstruct the copied options-bot (keep/relocate/delete);
retire the old underlying-return "screaming-buy" data + UI.
**A5. §6 — live engine + tracked book + per-alert confidence + sizing.** Wire surviving signals (single-leg
+ term_slope + anything from A2) into the live scan + expectancy scorecard + a tracked options book
(whole-contract sizing, moderate sleeve, annualized net-of-cost + after-tax returns vs the index). Per
alert: **confidence** (backtest bucket expectancy + sample; capped "thin" under 30 closed; down-weighted
for the fade; framed as expectancy-confidence, NOT a win probability — hit rate ~37%) and **suggested
whole-contract sizing** (floor(budget/(premium×100)), confidence-scaled, skip if one contract > budget; a
suggestion, never auto-traded).

## PART B — clear the live-app backlog (after Part A; from APP_FIXES / master roadmap)
**B1. Data integrity:** market cap $0 (source broker/FMP), company names (blank), sectors (unknown) + a
sector-diversification view, consistent $B/% formatting.
**B2. Widen the live universe to the full large-cap tier (~861)** — confirm FMP free-quota vs config; FMP
paid tier if needed. The book picks from 861, not 77.
**B3. Remove Sharadar from the LIVE path** — live prices → broker (Robinhood/Tradier), live fundamentals →
FMP; grep the scan path for any Sharadar/Nasdaq call and remove it. Sharadar = backtest-only.
**B4. Dynamic net alpha** (backtested + live-since-inception side by side; promote live only past the noisy
early weeks) + **Index in its own tab** (chart + holdings).
**B5. Trust:** "as of" staleness stamp, risk disclaimer on Index/signals, a "How it works" methodology page.
**B6. Reliability:** mobile responsiveness check; scan-failure alerting (Discord) instead of silently
serving stale data.

## PART C — growth/pre-profit valuation fix (RKLB shows $2.63 vs $65)
Carry **net debt per row** → enable **EV/Sales**; value growth names on revenue multiples scaled to growth;
blend DCF↔growth **continuously by a maturity score** (deep-growth → revenue + implied-growth; established →
DCF; banks → book/ROE); make the headline for growth names the **reverse-DCF / implied-growth** read; fix
the bear/base/bull scenario cards to use the same method as the headline (they show the excluded negative
DCF today).

## Close-out
**Fix the one failing edge test first:** `test_thetadata_provider_is_optional_and_dedupes` is
environment-sensitive — 88/88 in the agent env, 87/88 locally once `THETADATA_API_KEY` is set / the
`thetadata` library state differs. Make it **mock the ThetaData client** so it passes regardless of whether
the key or library is present; a test must not depend on local env. (Backtest-only; does not affect the
live site.)
Coverage guard + sanity + costs on every options run; keep tests green; regenerate
OPTIONS_BACKTEST_RESULTS + HANDOFF_STATUS + the master roadmap; **commit to `main` per item.** Do NOT
re-open rejected items (spreads for the long arm, conviction tier, 65–75 DTE, skew/VRP/gex, ML combiner,
PEAD, the rejected alt-data). Small/mid-cap options expansion (roadmap 22b) is the NEXT iteration — needs a
fresh ThetaData pull; note it, don't start it here.
