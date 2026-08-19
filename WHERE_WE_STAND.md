# Valquo — Where We Stand (2026-08-02)

An honest, in-depth read of the whole project: what's real, what's proven, what's still unproven, and
what would make this a generational tool rather than another hype screener. Nothing here is inflated —
where a number is in-sample or thin, it says so.

---

## TL;DR

- **The website is fine.** The unstyled page was a browser-cached snapshot from a mid-deploy moment; the
  live CSS serves correctly (verified). Hard-refresh fixes it.
- **The options edge is real, and now validated three independent ways** (broad backtest, held-out split,
  and — new today — a live broker-surface check). It is a **convex, long-vol profile**: ~37% of trades win,
  the winners are big, and the average trade is strongly positive. It is NOT a high-win-rate strategy, and
  the true forward return is still being measured (paper-track now running).
- **The stock edge clears every statistical bar** but has still only seen one 18-year panel; the forward
  track is the real test.
- **The single biggest thing left is the forward paper-track** — the only test on data nobody has looked at.
  It's now wired to your Tradier sandbox and running.
- **The differentiator is honesty + rigor.** In a category full of hype, a tool that shows its work, eats its
  own cooking with a live public track, and tells you when it *can't* value something is rare and defensible.

---

## 1. Is the options bot showing a TRUE edge? And expected returns?

**Yes — a real, measured edge, with honest limits.** Here is the full evidence chain, strongest to weakest:

**The backtest (full 55-name ThetaData panel, 2016–2025, net of punishing fills):**
- **+10.4% average per trade**, profit factor **1.30**, across **1,540 trades**.
- **Positive in BOTH held-out halves** (decide on one, measure on the other) — not a single-period fluke.
- **Broad, not a tail artifact:** +8.96%/trade *even after removing the top 15 winners*, and **30.7% of ALL
  trades returned ≥ +100%.** Big winners are common, not rare. (An earlier "too tail-dependent" scare turned
  out to be a sizing artifact — fixed with whole-contract, fixed-dollar-risk sizing.)
- **Survives realistic costs** (honest NBBO fills, buy-the-ask/sell-the-bid).

**The known weakness — and its fix:**
- The edge is **fading**: +16.4%/trade in the early years → +4.4% late. This is the one real caveat.
- **`term_slope` (options term-structure) arrests most of the fade** — it roughly triples late-half
  expectancy and repairs the 2022/2023 weak patches, at the cost of discarding ~60% of alerts (a real
  filter, not a universal one).

**The new validation (today's live-scan):**
- The term_slope threshold was fitted on synthetic Black-Scholes chains, so the open question was whether it
  survives a real broker's smoothed IV surface. **It does.** Live retention 41.8–45.5% vs a backtested 40.6%
  — inside the confidence band, no re-fit needed (after two live bugs were found and fixed).

**What was REJECTED (so we don't chase dead ends again):** put-credit spreads / the VRP short-vol arm
(loses money, drains the book), a conviction tier, the 65–75 DTE band, robust z-scores, and skew / IV-rank /
GEX as entry filters. The book is **single-leg long calls/puts only.**

**Expected returns — the honest answer:** per-trade expectancy is strongly positive (~+10% gross, broad),
but that is *per trade*, not an annualized account return. The real number depends on trade frequency (lower
now that term_slope gates ~60% of alerts), position sizing, the ongoing fade, and taxes (single-stock options
are 100% short-term / ordinary-income — they belong in the Roth). **We deliberately do not promise an
annualized figure**, because the only honest source for it is the forward paper-track that just started. What
we can say: the profile is convex — expect many small losses and occasional large wins, with the average
trade positive. Treat it as an edge worth trading with disciplined sizing, not a guaranteed return.

**Bottom line:** real edge, independently validated, honestly caveated. The paper-track converts "real in
backtest" into "real in front of us."

---

## 2. Stock model — where it stands

The fundamental model clears every internal bar it's been held to: **top-decile alpha ~+11.8%/yr,
long-short t ~3.5, PBO 6.7% (want <50%), Deflated Sharpe ~100%,** and it **survives costs** (breakeven ~236
bps one-way vs a ~37 bps actual cost profile → net top-decile ~+11.4%/yr). The edge is strongest in large
caps. Several long-standing bugs were found and fixed along the way (five silently-empty factors, a
currency-corruption bug in the value theme, sign errors), so the current numbers rest on far cleaner data
than any prior version.

**The honest caveat:** it has still only ever seen this one 18-year Sharadar panel, and the biggest single
tuning decision was informed by that same panel. So it's *in-sample-confident, out-of-sample-unproven* — the
forward track is what settles it. Weight-tuning itself remains noise; the model runs on sensible defaults.

**New this build:**
- **Growth valuation was fixed** (RKLB no longer prints a nonsensical $2.63) — but calibration showed the
  fair-value gap is **not** predictive (a framing tool, not alpha). The striking by-product: a plain
  **EV/Sales sort out-ranks the entire blended valuation engine** — a genuine lead worth promoting into the
  factor set (queued).
- **Sector-neutral ranking** is finally unblocked (the sector table is now on disk) and being wired + tested.
- **Three new signal datasets are built and waiting for gated tests:** the greeks/GEX options layer, the
  Lazy-Prices 10-K/10-Q language-change dataset, and PEAD (earnings drift).

---

## 3. The live app — what's working, what's in flight

**Working:** live DCF + bull/base/bear + 1–100 opportunity score + AI analysis; Hot Stocks; the **Valquo
Index** in its own tab (cumulative-vs-SPY chart, backtested-vs-live alpha, sector diversification, holdings,
staleness stamps, a methodology page, and a scan-failure watchdog); Signals; Track Record; Watchlist. The
live universe was fixed from ~154 names to the full ~800 large-cap tier, and market caps / company names /
sectors now render. The site serves correctly (the "break" was a cache artifact).

**In flight:**
- **Security fixes** — the audit found no committed secrets ever, but flagged a password-reset link that
  could leak when email fails (C1) and 23 handlers that return raw errors (H2). SMTP is configured on Render,
  so you're not currently exposed via the main path; the fixes harden it regardless.
- **Broker-fundamentals fallback** — FMP is on the free tier (no fundamentals), so we're wiring live
  fundamentals from the broker to see if you can avoid paying FMP entirely.
- **Data miner** — expanding the options cache toward ~1,000 liquid names (at ~133, skipping illiquid ones).

---

## 4. What's DONE in this build-out

Options: full-universe scream-buy backtest + held-out validation, cost survival, term_slope adoption + live
transfer, VRP arm tested and rejected, whole-contract sizing, per-alert confidence, the live alert engine,
and the greeks/GEX derived layer. Stock: growth-valuation fix + calibration (EV/Sales lead), currency and
coverage bug fixes, the Sharadar data freeze (insurance before the license lapses). App: universe fix, Index
tab, display fixes, methodology/trust surfaces. Infra: hands-off auto-merge (GitHub Action), a resumable
ThetaData miner, the Lazy-Prices dataset, a full read-only security audit, and an `AGENTS.md` map so every
terminal's lane and next step is unambiguous.

---

## 5. What's LEFT — prioritized

1. **Forward paper-track vs SPY (running now).** The #1 validation — settles both the options edge and the
   stock model's 252-day signal on unseen data. Everything else is secondary to letting this accumulate.
2. **Security fixes (C1 + H2)** — in flight; finish and deploy.
3. **Broker-fundamentals fallback** — decide FMP once and for all (free route vs $69 Premium).
4. **Sector-neutral verdict** — in flight; keep or reject honestly.
5. **Miner → ~1,000 names**, then: the small/mid-cap single-leg backtest (does it give more frequent
   home-run setups?), the greeks/GEX signal tests (#23), Lazy-Prices IC, and PEAD.
6. **Promote EV/Sales** to a weighted value factor (after sector-neutral lands).
7. **Autotrade via Tradier — last, and only after the forward track proves out.** Paper → gated live, with
   caps and a kill switch. Never before the track earns it.

---

## 6. Making it generational — cosmetic, edge, UX, trust

The category is saturated with confident-sounding hype. Valquo's wedge is the opposite: **rigor you can
audit and a track record we publish on ourselves.** Concrete moves:

**Trust (the real moat):**
- Make the **live forward track the hero of the site** once it has a few weeks — "we run this money in public,
  here's the curve vs SPY, updated daily." Almost no competitor will do this honestly.
- Surface the rigor in plain language: "we tried to disprove our own edge — here's the out-of-sample test, the
  costs, and where it's weak." The honesty *is* the marketing.
- Keep the "this model can't value that" behavior (pre-profit names) front and center — admitting limits
  builds more trust than a fake number.

**Edge / product:**
- Unify stock + options into one "what would I actually do" view: the opportunity score, the scream-buy
  alert (with its convex, ~37%-hit framing and whole-contract sizing), and the paper-track outcome, together.
- Ship the per-alert **confidence + sizing suggestion** prominently, always framed as expectancy, never as
  win-probability.
- Alerts that reach the user where they are (email/push/Discord), not just on-page.

**Cosmetic / UX:**
- Landing should **show, not tell** — a live sample valuation (e.g. AAPL) rendered on arrival, so a new
  visitor sees the gauge, the bull/base/bear range, and the implied-growth read within two seconds instead of
  a wall of intro text.
- Tighten the intro copy into scannable value-props with the existing visual components as the proof.
- A per-name "why this score" attribution (which themes drove it) — turns a number into an explanation.
- Continue the mobile polish; the Index tab is the one people open on a phone.
- Perceived speed: skeleton loaders and cached first paint so it never feels like it's hanging.

**The vision:** a disciplined, transparent research desk in a browser — stocks and options, every claim
backed by an out-of-sample test and a public live track, honest about uncertainty, that a serious retail
investor trusts *because* it refuses to oversell. That's the generational version.

---

## 7. Standing caveats (never drop these)

Educational tool, not investment advice. The Deflated Sharpe is a saturated statistic, not a proof. Both
halves of every held-out test come from the same panels and universes, so decisions are confirmed
out-of-sample but hypothesis-generation is not. Options are 100% short-term taxed. Sandbox paper fills are
~15-min delayed, so the paper-track is a strong reality-check, not perfect fill-truth. The forward track is
the only thing that tests any of this on data nobody has seen — until it has months behind it, the backtest
numbers are evidence, not a promise.
