# Valquo — Signal & Data Roadmap (brainstorm)

_July 2026. Ideas for widening the edge. Honest framing up front: we proved the lever is **data, not
math**. Every item below is a **hypothesis to test cheaply**, not guaranteed alpha — most public/alt
signals are weak and crowded. Each must clear the same bar as everything else: **CPCV + Deflated
Sharpe + de-correlation**. The goal is to test *many cheap, orthogonal* ideas and keep the few that
survive. Prioritize: **free + point-in-time + orthogonal**._

---

## 1. Data we ALREADY have but underuse (zero new cost — do these first)

**Sharadar (already downloaded in `data/backtest`):**
- **SF3 detailed 13F (per-manager holdings)** — we only use SF3A (aggregate quarterly change), and that
  aggregate 13F signal came back *real but weak*. The per-manager detail is a different animal: build a
  **"smart-money conviction"** signal — new/initiated positions by high-quality managers, position size
  vs the fund's AUM, breadth of ownership change, initiations vs adds. Following the *best* funds is far
  stronger than the crowd average. **→ First action: check whether SF3 (detailed) is in your bundle. If
  it is, this is probably the single biggest underused asset we own.**
- **Fundamental composites we're not computing (all from SF1 we already have):** Piotroski **F-Score**
  (9-pt fundamental momentum), **Altman Z** (distress), **Beneish M-Score** (earnings-manipulation flag),
  **cash-based operating profitability** (Ball et al. — beats accrual profitability), total accruals /
  net operating assets (Sloan), R&D intensity, total external financing. Cheap, well-documented, mostly
  orthogonal to what we have.
- **Insider (SF2) richness:** cluster buying (2+ insiders at once = stronger), role-weighting (CEO/CFO >
  director), buy/sell-ratio trends, transaction size vs holdings. We currently use only net buying.
- **Price/volume anomalies (from SEP):** short-term **1-month reversal**, **idiosyncratic-vol** (low
  idio-vol effect), **MAX effect** (avoid lottery stocks), Amihud illiquidity, downside beta,
  accumulation/volume trends. All orthogonal to our 12-1 momentum.

**The app's own accruing data (proprietary, look-ahead-free):**
- **The live paper track record** — every pick's real forward return is a growing, un-buyable,
  proprietary dataset. Systematically analyze it; over time it's the *real* out-of-sample proof, better
  than any historical backtest.
- **Monthly theme-IC history** from the self-learning loop — watch which signals decay vs strengthen.

---

## 2. Free / low-cost NEW data sources (test cheaply)

- **FINRA short interest** (free, bi-monthly) — short interest, days-to-cover, squeeze risk. Genuinely
  orthogonal; short-side and risk signal.
- **SEC EDGAR — mine it deeper (we already fetch from it):** 8-K material events, **13D/13G** activist
  stakes, S-1/424B issuance, NT filings (late = red flag), and NLP on **10-K/10-Q MD&A tone** + YoY
  **risk-factor language changes** (documented signals, free).
- **Quiver Quantitative** (free tier / ~$25 mo, API) — **congressional trading**, **government
  contracts** (directly relevant to defense names like RCAT), lobbying, social activity. Uncrowded-ish.
- **Analyst price targets** (FMP, free, dated → point-in-time like grades) — target-vs-price implied
  upside + target revisions. A *second* sentiment input alongside grades, ~free.
- **Earnings-call transcript tone** (FMP transcripts) — NLP sentiment of management + Q&A.
- **Retail attention** — Google Trends, Wikipedia page views (both free).
- **News/social sentiment** — Alpha Vantage (free tier), GDELT (free), Tiingo news, Paradox Intelligence
  (Google/TikTok/Amazon/Wikipedia/news mapped to tickers; has an MCP server).
- **FRED macro** (free) — yield curve, credit spreads, unemployment → regime conditioning.
- **USPTO patents / USAspending gov contracts** (free) — innovation + gov-revenue for specific sectors.

---

## 3. Methods to squeeze more from the signals we have

- **ML tree combiner** (Gu/Kelly/Xiu) — captures nonlinear interactions linear weights miss; validate
  strictly under CPCV/Deflated Sharpe. (Optional scikit-learn import so it never breaks Don's run.)
- **Regime-conditional weights** — different theme weights in bull/bear/high-vol regimes (from FRED/vol).
- **Signal-decay-aware weighting** — we saw 13F decays and grades have *no lag*; measure each signal's
  decay curve and weight fresher signals more.
- **Industry-relative ranking** — extend the sector-neutral toggle to full within-industry ranking.
- **Conditional/interaction signals** — "cheap AND improving estimates AND insider buying" (hand-crafted,
  or let the tree model find them).
- **Event studies** — earnings, insider clusters, 13D filings → short-horizon event alpha (feeds the
  options/Signals side).
- **Ensemble/stacking** — combine linear + tree once we have more than one real signal.

---

## 4. The meta-move: start ARCHIVING live data NOW (a compounding, un-buyable asset)

We can't cheaply *buy* deep history for options/IV, short interest, or sentiment. But we can **record
them live every scan** and build our own point-in-time archive. In 6–12 months we'll have proprietary
history to backtest things we currently can't — especially the **options-exit logic** (needs IV/chain
history we lack today). Turn the daily scan into a data-hoarding engine now:
- Snapshot Tradier **options chains / IV / skew** each run.
- Snapshot **FINRA short interest**, **analyst grades/targets**, **news/social sentiment**.
- Keep logging **our own picks' realized outcomes**.
This is the highest-leverage, lowest-cost move — cost is basically disk, and it compounds.

---

## 5. Prioritized to-do

**Quick wins (free, data we already have):**
1. Check if **SF3 detailed 13F** is in the Sharadar bundle → build the smart-money conviction signal
   (likely the biggest single upgrade).
2. Add **F-Score / accruals / cash-profitability / 1-month reversal / idio-vol** from existing data.
3. **Start the live data archive** (options/IV, short interest, sentiment) — cheap, compounds.

**Test-next (free / very cheap):**
4. FINRA short-interest theme.
5. Analyst **price-target** revisions (adds to grades sentiment).
6. Quiver **government-contracts + congressional** signals.
7. EDGAR **8-K / 13D / MD&A-tone** mining.

**Bigger bets (after a few real signals accumulate):**
8. ML tree combiner + ensemble.
9. Regime-conditional weighting.
10. Options history → real options-exit backtesting.

_Reality check: expect most of these to be weak or crowded. The win is running the cheap, orthogonal
ones through the honest gate and keeping the handful that clear it — same discipline as the 13F and
grades tests._
