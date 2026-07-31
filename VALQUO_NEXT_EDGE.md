# VALQUO_NEXT_EDGE.md — where the next edge comes from (2026-07-31)

Written after the foundation audit + P7–P11. The model is now **clean, validated, tradeable**
(PBO ~7%, Deflated Sharpe >99.9%, long-short t 3.4, top-decile alpha ~+11.8% gross / ~+11.4%
net-of-cost). This doc is the prioritized menu for pulling *further* ahead of the S&P.

## The honest frame (don't skip this)
Most new signals are weak or crowded. The win is **testing many cheap, orthogonal ideas through
the same gate** (CPCV + Deflated Sharpe + the held-out margin) and keeping the handful that
survive. And the number that actually compounds is **net-of-cost, net-of-tax** — so return
*engineering* (turnover, tax, sizing) is worth as much as any new signal. We just learned the
taxable-account edge is ~3× smaller than gross; that makes construction work first-class.

Already tried and REJECTED (do not re-open without a new reason): TTM ROE/ROIC, robust/MAD
z-scores, momentum+institutional merge, sector-neutral ranking, short-term reversal / MAX /
idio-vol, zeroing insider. Parked: analyst estimate revisions (needs WRDS/IBES).

---

## TIER 1 — highest ROI, do first

**1. No-trade band (turnover reduction). ← the single highest-value change.**
Today a name is sold the instant it exits the top decile. Add hysteresis: buy into the top 10%,
only sell when it falls out of the top ~15–20%. Turnover (~249%/yr) should drop sharply, which
directly lifts **net** return — critical after the tax finding — for minimal alpha loss. Test the
alpha-vs-turnover tradeoff across band widths; pick the knee.

**2. ML tree combiner (P13).** Gradient-boosted trees over the currency-correct signals capture
nonlinear interactions the linear composite can't ("value matters more when quality is high",
"momentum only in low-vol regimes"). Validate strictly under CPCV / Deflated Sharpe; keep only if
it beats the linear book out-of-sample. Optional sklearn import so it never breaks a run. Biggest
untried upside lever.

**3. Elite-manager 13F conviction (data we already own).** We use `sm_breadth` (holder-count
growth) but exposed and shelved `sm_conviction` / `sm_avg_position`. Build a proper "smart money"
signal: weight 13F accumulation by the *quality* of the buyer (historical fund performance),
position size ÷ fund AUM, and new *initiations* by top managers. Following the best funds beats
following the crowd average.

**4. LLM-as-analyst on filings (novel, cheap now).** Documented alpha in *language change*:
companies that quietly rewrite their 10-K/10-Q risk factors underperform ("Lazy Prices",
Cohen-Malloy-Nguyen). Run an LLM over EDGAR MD&A + risk-factor sections for YoY tone/█ change and
a "guidance sentiment" score. Was impossible/expensive pre-LLM; nobody at our scale does it.

---

## TIER 2 — cheap, orthogonal signals to test through the gate

- **FINRA short interest** (free, bi-monthly): short-interest ratio, days-to-cover — crowding /
  squeeze-risk signal, genuinely orthogonal to everything we have.
- **SEC EDGAR mining** (free): 13D/13G activist stakes (entry → drift), 8-K material events
  (catalysts), S-1/424B issuance and NT (late-filing) as red flags.
- **PEAD (post-earnings drift)** — unblock by pulling Sharadar's EVENTS earnings-code legend
  (`bulk.EARNINGS_CODES`), then build surprise + drift; test through the holdout gate.
- **Quiver congressional trades + USAspending government contracts** (free / ~$25): uncrowded;
  directly relevant to defense/gov names.
- **Dividend initiations + buyback announcements from ACTIONS** (already on disk): initiation and
  buyback-announcement drift are classic, cheap to build.
- **Downside / avoid filter:** Beneish M-Score (earnings-manipulation), Altman Z (distress),
  high external financing, high accruals — *exclude* flagged names even when they score well.
  Protects the book from blowups; cheap from SF1 we already have.

---

## TIER 3 — construction & portfolio (returns without new signals)

- **Regime-conditional weights:** use FRED (yield-curve slope, credit spreads) + realized vol to
  tilt theme weights by regime (defensive/quality in stress, value/size in recovery). Conditional
  models beat static ones in the literature; we have most ingredients already.
- **Signal-decay-aware weighting:** we measured 13F decays (peaks Q-1, dead Q-3); weight fresher
  signals more via an explicit freshness multiplier.
- **Volatility-targeted position sizing** within the book (vs pure score-weighting): smoother
  ride, usually better Sharpe and smaller drawdowns.
- **Concentration tuning:** top-25 has higher gross alpha (+20.7%) but is noisiest; sweep top
  25 → 40 → decile for the best risk-adjusted, net-of-cost point.
- **Tax-aware rebalancing** (for the *product's* taxable users; moot in Don's Roth): hold winners
  past 1yr for LTCG, harvest losses. High value given the 3× after-tax gap.

---

## TIER 4 — the compounding moat (start/keep now, harvest later)

Keep the live archive recording every scan: **Tradier options chains / IV / skew, FINRA short
interest, analyst grades/targets, news+social sentiment, and our own picks' realized outcomes.**
In 6–12 months this is a proprietary point-in-time dataset that lets us backtest what we *can't*
today — the options-exit logic above all. Cost is basically disk; it compounds.

---

## Data sources — free / cheap, at a glance
| source | cost | gives | orthogonal? |
|---|---|---|---|
| FINRA short interest | free | crowding, squeeze | high |
| SEC EDGAR (13D/8-K/S-1/MD&A) | free | activism, catalysts, issuance, tone | high |
| Sharadar EVENTS/ACTIONS (owned) | owned | PEAD, dividends, buybacks | med-high |
| Quiver (congress + gov contracts) | free/~$25 | insider-adjacent, gov revenue | high |
| FRED macro | free | regime conditioning | n/a (overlay) |
| GDELT / Google Trends / Wikipedia | free | attention, news sentiment | med |
| Tradier options (owned) | owned | IV, skew, flow | high (needs archive) |
| WRDS/IBES estimate revisions | licensed | the one big missing orthogonal signal | high |

---

## Recommended sequence
1. **Merge `worktree-p11-tax` to main** (P11 + after-tax + signup-gate are stranded).
2. **No-trade band** (Tier 1.1) — biggest net-return lever, cheap.
3. **ML tree combiner** (Tier 1.2) — biggest upside lever.
4. **Unblock PEAD** + **elite-manager 13F** (owned data, no new cost).
5. **FINRA short interest + EDGAR 13D/8-K** (free, orthogonal).
6. Keep the archive running for the Tier-4 harvest.

Reality check: expect most of Tier 2 to come back weak. That's fine — the point is running the
cheap, orthogonal ones through the honest gate and keeping the few that clear it.
