# VALQUO — master roadmap (single ordered source of truth)

> **SUPERSEDED 2026-08-03 by the external edge audit.** The canonical plan is now `VALQUO_EDGE_AUDIT.md`
> (the "Bible") + `VALQUO_ACTION_PLAN.md` (the execution layer that maps it to agents + the product track).
> The CURRENT-STATE block below is STALE: the audit re-opens the options verdict (a price-basis bug, B1) and
> the equity-alpha claim (never risk-adjusted, R1), and flags the live product running a rejected config (B7)
> and the paper track running with four comparability defects (B5). Read `VALQUO_ACTION_PLAN.md` first; treat
> everything below as historical context.

Consolidates APP_FIXES, OPTIONS_BOT_INTEGRATION, OPTIONS_DATA_SOURCES, and the research levers into one
priority-ordered list. Detailed specs live in those sub-docs; this is the order to execute.

## CURRENT STATE — 2026-08-03 (READ FIRST; supersedes the dated bullets below)

**The research phase is essentially CLOSED. The honest verdict:**
- **STOCK fundamental model = the one validated edge** — top-decile ~+11.8%/yr, PBO 6.7%, Deflated Sharpe
  ~100%, survives costs. In-sample-confident, out-of-sample-unproven (one 18y panel); the forward track is the
  real test.
- **Every stock bolt-on REJECTED through the held-out gate:** sector-neutral (twice), EV/Sales, lazy-prices
  (language-change), PEAD. The existing themes ARE the edge — nothing overfit shipped. (EV point-in-time bug
  fixed along the way.)
- **OPTIONS single-leg = long-vol BETA, not a timing signal.** The trade autopsy found nothing beyond
  `term_slope` separates winners from losers at entry (64 features), and the 187-name universe backtest found a
  **random-entry control (+13.22%/trade) BEATS the signal (+5.14%)** — the scream-buy picks worse-than-random
  entry days (z -5.24). The edge halves on breadth and the whole gap is the spread. VRP / spreads / GEX / skew
  / iv_rank all rejected. (`HANDOFF_universe_backtest.md`, `HANDOFF_trade_autopsy.md`)

**LIVE NOW — the validation clock started (2026-08-03):**
- Forward paper-track (options scream-buy book + Valquo Index vs SPY) runs server-side on Tradier **sandbox**;
  honest Discord daily/weekly recaps post automatically (first session: Index +1.73% vs SPY +1.42%; labeled
  "paper, thin, not yet a result — 1 of ~126 sessions"). CONFIRMED working end-to-end.
- Hands-off infra: the auto-merge Action; every agent writes its full report to `HANDOFF_<name>.md`; the miner
  runs locally via `mine.bat` (~370 names cached — ThetaData is a local gateway, can't go server-side).

**STILL RUNNING (the last research):** the options **entry-fix** (can the worse-than-random timing be
salvaged — is it chasing pumped IV? `HANDOFF_entry_fix.md`) · **Phase-9 UX** (why-this-score, live-track hero,
unified view).

**OPEN / what we could do further (priority order):**
1. **Let the forward track accumulate** — THE decisive out-of-sample test for both the stock model and the
   options long-vol book. Needs ~126 sessions; nothing to do but let it run.
2. **Estimate revisions (WRDS/IBES)** — the one untapped signal lever left; a well-documented equity alpha.
   BLOCKED on Don setting up WRDS access; then it's a prompt.
3. **Pivot research -> product / launch:** build around the validated stock model + the transparent live track
   (Phase-9 UX, honest options framing as long-vol not a signal). The honesty + public track IS the moat.
4. **Autotrade via Tradier — LAST, gated on the forward track proving out.** Route real trades at the **Roth
   account number** (one token, account-selected); IRA = long options only, no naked / margin. Options are 100%
   short-term taxed -> the Roth is the correct home.
5. Minor: gated auto-apply of learned weights (#121); social OG-image tags.

**DON ACTIONS (operational gates):** Render env must hold `TRADIER_PAPER_TOKEN`, `TRADIER_PAPER_ACCOUNT_ID`,
`ADMIN_TOKEN`, `DISCORD_WEBHOOK_URL` — CONFIRMED working (the 2026-08-03 recap posted). Paid data: **buy nothing
new** — the autopsy proved flow / GEX / skew don't help; only WRDS/IBES (near-free) is worth pursuing.

---

## STATUS — 2026-08-02 (read first)

**Full narrative status + edge assessment + the generational product plan: see `WHERE_WE_STAND.md`.**
(Site "break" 2026-08-02 was a browser-cached mid-deploy snapshot — live CSS serves 200; hard-refresh fixes.)

- **Merges are HANDS-OFF now.** The GitHub Action (`.github/workflows/land-agent-branch.yml`) auto-merges every
  `worktree-*` push into `main` behind the `test_edge.py` gate; Render auto-deploys. VERIFIED — a3-vrp,
  growth-valuation, and app-display-fixes all landed on `origin/main` + deployed with zero manual merge. If a
  local checkout looks behind `origin/main`, it just needs `git pull`.
- **A3 / VRP credit-spread arm -> REJECTED** (item 19). 2,496 trades, -7.99%/trade, PF 0.28, negative 9/10
  yrs. Correlation with the single-leg arm is +0.036 in its down months — genuinely uncorrelated, but the arm
  LOSES, so it drains the book instead of smoothing it; even a perfect mid-fill is only break-even and still
  lowers combined Sharpe. **Book stays single-leg long-vol only.** (OPTIONS_VRP_RESULTS.md / HANDOFF_vrp.md)
- **7b growth / pre-profit valuation -> DONE.** RKLB $2.63 -> $6.88 (range $0.95-$20.37), implied-growth
  headline, low confidence; screener now gives it $9.06 (was nothing). Method-correct + honest, NOT backtested
  -> validate it next (growth-calibration task). (HANDOFF_growth_valuation.md)
- **App display — market cap (7), names + sectors (9) -> DONE** (app-fixer; landed with the growth branch).
- **WAVE DONE (2026-08-02) — 6 landed on main:** options live-scan (**term_slope DOES transfer** — live
  retention 41.8-45.5% vs backtested 40.6%; two live bugs fixed) · greeks/GEX layer (82 names, 66.3M
  contract-days priced, gated #23 NOT started) · Lazy-Prices dataset (195 filers, 7,095 pairs, 0 failures) ·
  Sharadar freeze (all 10 tables clean -> `data/backtest_freeze_2026-08/`, runs with no API key) · security
  audit (no secret ever committed — but see URGENT) · app-fixer Index tab (chart, backtested-vs-live alpha,
  staleness, methodology, watchdog).
- **URGENT (Don + security-fix agent):** audit finding **C1 — the password-reset link is returned in the HTTP
  response whenever SMTP is unset/failing = account-takeover on ANY account incl. the owner's** (owner unlocks
  `/api/edge/*`). Don: confirm SMTP is configured on Render (10-sec check). Fix agent hardens it + closes H2
  (23 handlers still leak raw error text to anonymous callers).
- **NEXT / firing now:** security fixes (freed pipeline terminal, `PROMPT_security_fixes.md`) · broker-
  fundamentals free route (app-fixer, `PROMPT_broker_fundamentals.md`) · paper-track (launch now — Tradier env
  is in) · sector-neutral (relaunch — didn't land). PARKED/done: greeks (re-run as the miner grows),
  lazy-prices (#28 gated research later), freeze (done), miner (still mining).
- **Forward paper-track (#12) — BUILT + LANDED (paper tracker), now needs to RUN.** `paper_broker.py` +
  `paper_track.py` + `scripts/paper_track_run.py` + `/admin/run-paper-track`; submit(ask)->mark->close(bid) at
  the punishing DEFAULT_AGGRESSION=1.0 so it's comparable to the backtest; closes on each alert's own exit
  policy via the existing `record_outcome`; Index-vs-SPY book; 343 tests green (22 new). **To go live:** (1)
  Don adds `TRADIER_PAPER_TOKEN` + `TRADIER_PAPER_ACCOUNT_ID` + admin token to **Render**; (2) one-time
  `python scripts/paper_track_run.py --health`; (3) daily schedule after close (Cowork task or Render cron).
  Settles both the options book AND the growth 252d signal — the only test on unseen data.
- **Trade autopsy (pipeline builder) — FIRING:** what separates the ~37% winners from the ~63% losers on
  features known at ENTRY (roadmap #23+#26), expectancy-not-hit-rate, held-out, loser/total-loss autopsy.
  `PROMPT_pipeline_trade_autopsy.md`.
- **Growth calibration DONE — honest NULL:** the fair-value gap does NOT predict returns (IC t +0.99); the one
  "significant" figure is a size effect and the 252d version dies on non-overlapping windows. Striking
  by-product: a plain **EV/Sales sort out-ranks the entire blended valuation engine, and even size.** Verdict:
  valuation = a framing tool, not alpha (UI wording already right, no change needed).
- **SEQUENCED (shared files):** promote EV/Sales to a weighted panel value factor (after sector-neutral — same
  file) · PEAD from EVENTS (#24, same panel) · broker-fundamentals fallback -> app-fixer · test-hardening.
- **Don actions:** (1) FMP is on the FREE Basic tier (never paid) — free can't power the 800-name fundamental
  scan (250 calls/day, no full fundamentals). Test broker (Robinhood/Tradier) fundamentals first; only if
  insufficient, FMP **Starter $29/mo** is the entry (annual fundamentals + 300/min), Premium $69 only for
  quarterly/full ratios + earnings calendars, Ultimate unneeded (13F already via Sharadar). (2) rotate the FMP
  key — it nearly leaked via the public `/api/hotstocks` health block (caught + redacted pre-deploy).

---

## PHASE 0 — DONE (2026-08-02): options backtest phases 1+2
0. **Full 55-name scream-buy backtest COMPLETE** — +10.4%/trade, PF 1.30, positive in BOTH held-out halves,
   1,540 trades net of punishing fills. **The "too tail-dependent" scare was a SIZING ARTIFACT:** size by
   fixed $ risk (not 1 contract/signal) and it's broad — **+8.96%/trade even excluding the top 15 winners;
   30.7% of ALL trades ≥ +100%.** Big winners are common, not rare. **Single-leg calls confirmed; spreads
   REJECTED** (−4.46% vs +12.33% — they cap the upside where the edge lives). **No conviction tier** (the
   home-run fingerprint doesn't predict OOS — top 15 were mostly 2020 tech, a regime not a setup). Real
   remaining caveat = **FADING** (+16.4% early → +4.4% late; 2022/23/25 negative). Refinements found:
   **65–75 DTE beats 45–55 (+17% vs +7.8%)**, 35-delta already optimal. **Adopt fixed-$-risk sizing.**
   Merge is AUTOMATIC now — the GitHub Action lands every `worktree-*` push on `main` behind the test gate
   and Render deploys (verified 2026-08-02). No manual merge, no Vim, no git_push.bat.
   **PHASE 3/3b:** whole-contract sizing adopted (honest P&L $55–84k); 65–75 DTE rejected; **`term_slope`
   (term structure) ADOPTED — nearly TRIPLES the late-half expectancy (+4.76%→+12.88%), repairs 2022/2023,
   discards ~60% of alerts (a real filter, not universal).** skew/VRP/gex rejected; **iv_rank + tick flow
   still UNTESTED** (iv_rank needs a daily ATM-IV series). So the fade is largely arrestable.
   STILL OUTSTANDING (→ Phase 5): wire term_slope live, test iv_rank/tick-flow, §4 VRP arm, §5 fold-in,
   §6 live engine + per-alert confidence/sizing.

## PHASE 1 — the moment the run lands (gates everything else)
1. **Commit + merge to `main`.** Land the options work off the worktree, and land the stranded +10 p24
   research commits. Don't leave work on a branch.
2. **Apply the held-out gate to the full-55 result** → the real options verdict (not the 5-name preview).
   Also report it as an **annualized net-of-cost AND after-tax account-level return** (not just per-trade
   expectancy) so it's directly comparable to the stock index (roth +17.4% / taxable +4.86% after-tax).
   Options are 100% short-term-taxed, so the after-tax figure is the honest one for a taxable comparison.
3. **Audit the `closeadj` vs `closeunadj` split at EVERY price-usage site** — a partial fix reintroduces the
   split-adjustment bug (same way the currency fix first missed `neg_ps`). Raw for option math, adjusted for
   technicals, everywhere.

## PHASE 2 — Sharadar runway (time-sensitive: ~1 month of access left)
4. **Final fresh Sharadar bulk download -> ACTIVE (freeze agent, PROMPT_sharadar_freeze.md).** Freeze the
   freshest SF1/SEP/SF3/DAILY/ACTIONS/EVENTS + refreshed TICKERS into a dated read-only snapshot before the sub
   lapses (~1mo left), verified vs known checkpoints (AAPL 2015Q2 $722.6B, ~197,265 rows, ~2,710 names). NOTE:
   `tickers.pkl` already on disk -> sector-neutral (#13) is now DATA-unblocked, wiring only.
5. **Remove Sharadar from the LIVE path** — live prices → broker (Robinhood/Tradier), live fundamentals →
   FMP; grep the scan path for any Sharadar/Nasdaq call and remove it. Sharadar = backtest-only thereafter.
6. **Back up now + schedule it** — run `backup_to_D.bat`, add the daily scheduled task (keys + data live
   only on C: otherwise).

## PHASE 3 — live app: data integrity (site currently looks half-built)
7. **Fix market cap $0.0B** — source from broker/FMP in the live book path.
7b. **Fix growth / pre-profit valuation** (RKLB shows fair value $2.63 / −96% vs a $65 price; scenarios go
   negative). Root cause (confirmed in `fairvalue.py` + the engine): valuation uses only earnings/FCF
   multiples and **deliberately excludes EV/Sales** (no net debt per row), so pre-profit growth names have
   nothing valid to value on. Fix:
   - Carry **net debt per row** so **EV/Sales** (and EV/EBITDA) can bridge enterprise → per-share value.
   - Value growth names on **revenue multiples scaled to the growth rate** (and peers), not profit.
   - Blend DCF ↔ growth **continuously, weighted by a maturity score** (deep-growth/pre-profit → ~100%
     revenue+implied-growth; established → ~DCF+earnings multiples; banks → book/ROE) — not a hard switch.
   - Make the **headline for growth names the reverse-DCF / implied-growth** read ("price implies ~94%
     growth vs our ~34% base") rather than a false-precise point value.
   - Fix the **bear/base/bull scenario cards** to use the same method as the headline (they currently show
     the excluded negative DCF). Growth valuation is inherently uncertain → present a **range + low
     confidence**, not false precision.
8. **Widen the live universe -> DONE (2026-08-02, app-fixer): 191->800 names, 154->794 scored; Index is now a
   decile of 668 (67 positions, 10 sectors), display coverage ~100%.** Root cause was NOT quota — FMPProvider's
   fallback hard-coded the 191 "bundled" list for every scope; fixed + added a free Tradier universe (7,113
   NYSE/Nasdaq names, dollar-liquidity ranked) so the app no longer needs FMP's screener. FMP itself diagnosed
   as a LAPSED/allowlisted subscription (see Don actions above), and a near-leak of the FMP key via the public
   health block was caught + redacted.
9. **Populate company names** (blank today) and **sectors** (show "unknown") + a sector-diversification view.
10. **Consistent number formatting** ($B, %) across tables.

## PHASE 4 — live app: trust + launch enablers
11. **Dynamic net alpha/Sharpe** — show backtested + live-since-inception side by side; promote live to
    headline only once it's past the noisy early weeks. (This IS the forward paper-track — the #1 validation.)
12. **Index gets its own tab** — index-vs-S&P chart + holdings.
13. **"As of / last updated" staleness stamp**; **risk disclaimer** on Index/signals; **"How it works /
    methodology" page** (PIT, survivorship-free, costs, caveats — the credibility moat).
14. **Mobile responsiveness check**; **scan-failure alerting** (Discord) so stale data is never served silently.
15. **Launch stock tracking** — Index live, tracked vs SPY from inception; generate the top-25 order sheet
    when cash settles.

## PHASE 5 — options build (after Phase 1 verdict; reuse the cached ThetaData history)
16. **Deconstruct the copied options-bot** (keep/relocate/delete per OPTIONS_BOT_INTEGRATION.md).
17. **Phase A — harden the backtest**: fold in `bs_pricing` (+ computed gamma), stop-gap-through fills, the
    no-edge self-test, `AsOfHistory` look-ahead guard, `occ_symbol`.
18. **Wipe the old screaming-buy options data + retire the underlying-return view** (bundle here).
19. **Phase B — VRP credit-spread arm -> REJECTED (2026-08-02).** 2,496 trades, -7.99%/trade, PF 0.28,
    negative 9/10 yrs; genuinely uncorrelated with single-leg (+0.036 in its down months) but loses money, so
    it drains the book; even a perfect mid-fill is only break-even. Ran on cached history through the same
    gate + a Ledoit-Wolf portfolio/correlation layer. **Book stays single-leg long-vol only.** See
    OPTIONS_VRP_RESULTS.md / HANDOFF_vrp.md.
20. **Phase C-alt — intraday convex-ticket arm** — gated behind a spread-aware intraday backtest, index/ETF
    first, run as a small capped sleeve.
21. **DONE (2026-08-02) — Wired the winners into Valquo LIVE (landed bad0ac4): single-leg edge off the broker
    chain, term_slope gating (~60% fewer alerts, revertible via OPTIONS_TERM_FILTER), fade-discounted
    confidence, whole-contract sizing, scoreable paper book; all suites green.** Follow-ups: live-scan
    threshold-transfer (pipeline agent) + `record_outcome` wiring (Cowork). Original scope — sharper alert engine + tracked options book + expectancy scorecard,
    PLUS **per-alert confidence + whole-contract sizing suggestion**: confidence from the backtest bucket's
    expectancy + sample size (capped "low/thin" under 30 trades, **down-weighted for the 2021–2025 fade**,
    framed as expectancy-confidence NOT a win-probability — hit rate is ~37%); sizing = whole contracts to
    a $ risk budget, confidence-scaled, skip-if-one-contract-exceeds-budget; a suggestion, never auto-traded.

## PHASE 6 — enhancements / new signals (each pre-committed, through the gate; expect most to reject)
22. **IV-regime switch** — buy vol (single-leg) when IV rank is low, sell vol (spreads) when rich; unifies
    the two arms. Highest-value construction idea.
22b. **Expand the options universe beyond the 55 megacaps to liquid small/mid caps.** Megacap moves are
    muted by size; small/mid caps have the explosive moves single-leg calls need, and more names = more +
    potentially less-concentrated winners — a direct attack on the 15-trade tail problem. **But test it net
    of REALISTIC fills:** small/mid-cap option SPREADS are the widest (the #1 edge-killer) and their IV is
    higher (pricier premium already prices the move in), so this could help OR get eaten. Filter on **OPTION
    liquidity** (min OI/volume, max spread %), not just underlying market cap — an illiquid option is
    untradeable no matter how much the stock moves. Requires a new ThetaData pull for the added names.
    Re-run through the same gate + tail analysis; keep only if the net-of-spread edge survives AND
    de-concentrates.
23. **DIY options flow + GEX + skew + IV-rank + higher-order greeks** — test as filters/enhancers on the
    scream-buy expectancy. **PREP IN PROGRESS (greeks agent):** the mined cache is slim (bid/ask/vol/OI only —
    no IV/greeks), so a dedicated agent derives IV (Black-Scholes inversion of the mid), 1st/2nd/3rd-order
    greeks, GEX, and skew into `data/options_derived/` — done-mined names only, read-only on the miner cache,
    ZERO ThetaData calls. That layer is pure prep; the gated keep/reject testing runs when Don is back.
24. **Earnings / IV-crush** — options-native signal (distinct from the rejected stock PEAD).
25. **Curated paid options data — only if DIY proves the signal:** Unusual Whales (flow/dark-pool/
    congressional), SpotGamma (refined GEX), Ortex (borrow/squeeze). Defer until earned.
26. **Options ML combiner** — later, strict gate; options may have the nonlinear structure the stock ML
    combiner lacked (flow × IV × momentum). Re-open only after linear signals are proven.

## PHASE 7 — research levers (ongoing, gated)
27. **WRDS/IBES estimate revisions** — the #1 remaining STOCK lever; free via William & Mary; already
    partially wired. Set up WRDS as the free successor to Sharadar for research.
28. **LLM-as-analyst on filings** — "Lazy Prices" YoY 10-K/10-Q language-change signal; novel, cheap now,
    untried.

## PHASE 8 — autotrade (last; gated on a validated edge + forward track)
29. **Autotrade via Tradier** (official API, IRA-capable — not Robinhood, no official equity API). Reuse the
    options-bot orchestrator: preview → paper → live, risk caps, kill switch, journal. Live only after a
    forward paper track. Mind the PDT rule (<$25k margin = 3 day-trades/5 days) — throttles the intraday arm.

## PHASE 9 — Product & UX (the generational layer; details in WHERE_WE_STAND.md)
30. **Live forward track = the hero of the site** once it has a few weeks — a public daily curve vs SPY.
    "We run this in public." The real moat in a category full of hype.
31. **Landing shows, not tells** — render a live sample valuation (e.g. AAPL) on arrival so a visitor sees the
    gauge + bull/base/bear range + implied-growth read in 2 seconds, not a wall of intro copy.
32. **Per-name "why this score" attribution** — which themes drove it; turn the number into an explanation.
33. **Unify stock + options into one "what would I do" view**; surface per-alert confidence + whole-contract
    sizing prominently, always framed as expectancy (convex, ~37% hit), NEVER as win-probability.
34. **Alerts off-page** — email / push / Discord, not just on the page.
35. **Rigor in plain language** — "we tried to disprove our own edge": the out-of-sample test, the costs, and
    the weaknesses, shown accessibly. The honesty is the marketing.
36. **Perceived speed + mobile polish** — skeleton loaders, cached first paint, Index-tab-on-a-phone.
