# Data & Methods — how to actually prove (or disprove) an edge

Short version: **the data is where edges are won or lost, and most "edges" are
statistical illusions.** Free feeds (yfinance/Stooq) are fine for a live product
but wrong for research — they drop delisted losers (survivorship bias) and carry
no point-in-time fundamentals, so they *manufacture* fake edge. To find a real one
you need survivorship-free, point-in-time data plus a protocol built to reject
flukes. Here's the whole picture.

---

## 1. The data you actually need
Three properties, in order of importance:

1. **Survivorship-bias-free with delisting returns.** Include companies that went
   to zero, got acquired, or delisted — *with the terminal return*. Omitting them
   is the single biggest source of fake backtest edge.
2. **Point-in-time fundamentals ("as reported, as known on the date").** Use the
   numbers as they were filed on each historical date, not today's restated values.
   (Your screener's `pit_data.py` does this from EDGAR filing dates — the right idea.)
3. **Historical index membership + corporate-action-adjusted prices** (splits,
   dividends, spin-offs).

### Where to get it (solo-builder tier)
| Source | What it gives | Rough cost | Notes |
|---|---|---|---|
| **CRSP + Compustat via WRDS** | The academic gold standard: survivorship-free prices with delisting returns + point-in-time fundamentals | **Free to you** *if* William & Mary grants WRDS access (most business grad programs do) | **Ask the Mason School — this is your best path by far.** |
| **Sharadar (via Nasdaq Data Link)** | SF1 point-in-time fundamentals, ~21k active + delisted tickers back to 1998, historical S&P 500 membership, insiders | tens of $/mo | The standard affordable "institutional-quality" retail choice |
| **Norgate Data** | Survivorship-free US prices incl. delisted, historical index constituents | ~$ tens/mo | Great for price/technical backtests (your Signals strategy) |
| **EODHD** | Fundamentals feed | ~€60/mo (all-in-one ~€100/mo) | Cheaper; verify PIT quality before trusting factor tests |
| **Tiingo** | Prices + some fundamentals | free tier / <$30/mo | Budget option; lighter PIT coverage |

**My recommendation for you:** (1) chase **WRDS through William & Mary** first (free,
best), and (2) if that's unavailable or slow, **Sharadar SF1** is the highest-ROI
paid upgrade for the fundamental composite, and **Norgate** for the price/technical
Signals strategy. There is **no credible free survivorship-free fundamentals source.**

---

## 2. The methods that are actually reputable and repeatable
The academic record is humbling, and you should internalize it:

- **Most published anomalies don't replicate.** Hou, Xue & Zhang, *Replicating
  Anomalies* (2020): under proper methods the large majority of ~450 anomalies are
  insignificant. Harvey, Liu & Zhu (2016): a genuinely new factor needs a
  **t-statistic > 3** (not 2) to survive multiple testing; 27–53% of published
  factors are likely false discoveries.
- **Edges decay after publication.** McLean & Pontiff (2016): factor returns fall
  ~30–58% out-of-sample once a strategy is known (arbitrage + overfitting).

So don't chase exotic signals. Lean on the **handful of factors with the strongest,
most-replicated evidence**, which are also the ones the tool already uses:

- **Value** (cheapness), **Momentum** (12-1 month; Jegadeesh-Titman, Carhart),
  **Quality/Profitability** (Novy-Marx gross profitability; AQR "Quality Minus
  Junk"), **Investment/asset-growth**, **Low-risk / betting-against-beta**, and
  weakly **Size**. These anchor the Fama-French 5-factor and Hou-Xue-Zhang q-factor
  models. That's your "reputable and repeatable" toolkit — resist adding more.

---

## 3. The protocol (this is what makes a result trustworthy)
1. **Survivorship-free + point-in-time data** (§1). Everything else is secondary.
2. **Include delisting returns** (set delisted-to-zero where appropriate).
3. **Realistic costs + slippage + turnover control** (we subtract round-trip costs;
   tighten per your broker).
4. **Cross-sectional standardized factors → IC + quantile spread** (we do this).
5. **Walk-forward / expanding-window out-of-sample** — never a single in-sample fit
   (the Edge Lab does this).
6. **Multiple-testing correction** — the part most people skip:
   - **Harvey-Liu-Zhu t > 3** gate for "new" factors (`edge/statistics.hlz_significant`).
   - **Deflated Sharpe Ratio** (Bailey & López de Prado): deflates a backtest Sharpe
     for the *number of variants you tried*, sample length, skew and kurtosis, and
     returns the probability the edge is real. **Now built in** — the Edge Lab's
     `optimize` reports it (e.g., "searched 70 weightings → 8% probability the best
     is a real edge"). This is the single best guard against fooling yourself.
7. **Confirm out-of-sample and forward.** The live track record (survivorship-free
   going forward) is the ultimate arbiter.

---

## 4. What's already built vs. what to add
**Built (reputable, working today):** cross-sectional z-scores, IC, quantile spread
after costs, walk-forward optimization, sample-awareness, the Claude advisor judged
on a holdout, and now the **Deflated Sharpe Ratio + HLZ t>3 gate**. The price-factor
(momentum/technical) research runs on free data now.

**To add (needs the data above):**
- A **survivorship-free data adapter** — drop-in interface so the backtest consumes
  Sharadar/Norgate/WRDS instead of Stooq. (I can build the adapter the moment you
  pick a provider; the panel/engine already accept any factor set.)
- **Point-in-time fundamentals** into `edge/panel.py` (port your `pit_data.py`
  EDGAR reconstruction, or use Sharadar SF1) to optimize the *fundamental composite*,
  not just price factors.
- **Delisting-return handling** in the panel once delisted names are available.

---

## The honest bottom line
With good data and this protocol you'll get a *trustworthy* answer — which may well
be "no reliable edge after costs," exactly as your screener found. That's not a
failure; it's the point. The tool is built to find an edge if it exists and to tell
you plainly when it doesn't, so you never bet real money on a curve fit.

*Educational tooling and research methodology — not investment advice.*

### Sources
- Bailey & López de Prado, "The Deflated Sharpe Ratio" (SSRN 2460551).
- Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns."
- Hou, Xue & Zhang (2020), "Replicating Anomalies" (NBER w23394).
- McLean & Pontiff (2016), out-of-sample decay of predictors.
- Sharadar / Nasdaq Data Link; Norgate Data; CRSP; EODHD; Tiingo (data vendors).
