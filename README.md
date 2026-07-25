# Adaptive DCF Valuation Tool

A live-data discounted cash flow engine that values **any ticker** you type in, adapts its assumptions to the kind of company it is (mature compounder, fast grower, cash-burning start-up, cyclical), and returns a fair value with **bull / base / bear** cases, a **Monte Carlo** distribution, a **reverse-DCF** reality check, a **comps** cross-check, and a transparent **1–100 opportunity score** — plus an optional AI layer that writes the qualitative analysis and critiques the model's own assumptions.

It grew out of, and generalizes, my hand-built [Nike DCF](../nike-dcf-valuation): instead of one company in a spreadsheet, it's an engine that rebuilds that analysis for anything, from live data, in a couple of seconds.

> **Educational tool, not investment advice.** Fair value is a *model output*, not a price target. Automated assumptions are estimates — verify against primary filings before acting on anything.

---

## What it does

- **Any ticker, live data.** Pulls financial statements, market data and the current 10-year Treasury with no API key required (Yahoo Finance + SEC EDGAR).
- **Adaptive DCF.** Classifies the company and picks an appropriate model: a 5-year forecast for a mature name, a 10-year path-to-profitability with margin convergence for a cash-burning grower, mid-cycle normalization for a cyclical.
- **Scenarios.** Bull / base / bear, with the cone of outcomes widening automatically for less predictable businesses.
- **Monte Carlo.** 10,000 trials perturbing growth, margins, WACC and terminal growth → a full distribution of fair value and **P(undervalued)**, the share of trials worth more than today's price.
- **Reverse DCF.** Solves for the growth and margins the *current price* implies, so you can judge whether the market is pricing in something realistic.
- **Comps cross-check.** Implies a value from sector-typical multiples (or real peer medians if you supply peers) as a second opinion on the DCF.
- **1–100 opportunity score.** A regime-aware blend of valuation, quality (ROIC vs WACC), growth (with a Rule-of-40 check), financial health (leverage + cash runway) and momentum — every sub-score and weight is shown, never a black box.
- **Optional AI analysis.** With an Anthropic (or OpenAI) key, Claude writes the moat read, risks, catalysts, bull/bear theses and a critique of the tool's auto-generated assumptions. Without a key, a transparent rule-based fallback produces the same structure.
- **Exports.** A live, formula-driven Excel model (mirrors the Nike workbook: DCF / WACC / Sensitivity tabs) and a clean one-page PDF tearsheet.
- **Watchlist.** Score and rank a whole list of tickers 1–100 side by side.
- **🔥 Whole-market hot-stocks screener.** Scans the market and ranks every name 1–100 on a cross-sectional value · quality · growth · momentum composite (two buckets, self-calibrating z-scores), with sector-attractiveness and a one-click portfolio builder.
- **📊 Point-in-time backtest.** Tests whether the ranking actually predicts forward returns — Information Coefficient, quantile spread after costs, equity curve vs benchmark, out-of-sample split — with honest survivorship caveats.
- **Insider signals (Form 4)** and a **daily auto-scan** you can schedule.
- **⚡ Intraday Signals (Premium):** an always-running scanner over liquid S&P-500 names that blends reputable technicals (RSI, MACD, 50/200 MA crosses, breakouts, volume) with options context (put/call, IV) into a ranked buy-setup score, with Claude-written reasoning on the top 10. Real-time via Tradier, or free delayed data. Educational — not a proven edge, not an autotrader.

---

## Quick start

### Windows (one click)
Double-click **`run.bat`**. It creates a virtual environment, installs dependencies the first time, and opens the dashboard in your browser.

### macOS / Linux
```bash
./run.sh
```

### Manual (any OS)
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                        # opens http://127.0.0.1:5000
```

Then type a ticker (e.g. `AAPL`, `NVDA`, `KO`) and hit **Analyze**.

### Command line / batch
```bash
python cli.py AAPL                   # value one ticker
python cli.py AAPL --excel --pdf     # also write the Excel model + PDF report
python cli.py AAPL MSFT NVDA KO --rank   # score & rank a watchlist
python cli.py AAPL --ai              # include AI qualitative analysis
```

---

## How it works

### 1. Data (free, no key)
`yfinance` provides the income statement, balance sheet, cash-flow statement, price, shares, and beta; **SEC EDGAR** fills gaps and cross-checks US fundamentals; the live 10-year Treasury (`^TNX`) sets the risk-free rate. Every field is looked up defensively with fallbacks and any data-quality issues are surfaced in the UI. Fundamentals use the most recent reported fiscal year (like the Nike model's FY2025 base year); market data is live.

### 2. Classification
The company is sorted into a regime — *mature, growth, hypergrowth, cyclical,* or *financial* — from its growth rate, cash-flow profile and sector. This drives everything downstream, including how much to trust the DCF (flagged explicitly; financials get a "low" reliability flag because unlevered-FCF DCF is the wrong tool for a bank).

### 3. The DCF engine (FCFF, reinvestment-based)
Unlevered free cash flow to the firm, built the way growth companies actually need to be valued:
- **Reinvestment is tied to growth** through a sales-to-capital ratio (`reinvestment = ΔRevenue ÷ sales-to-capital`) instead of fixed capex/D&A percentages that break when a company is scaling.
- **Operating margins converge** from where they are today to a sustainable target — this is what lets the same engine value a turnaround (Nike, 8% → 13%) and a pre-profit SaaS company (−10% → 27%).
- **Early losses accrue an NOL balance** that shields future taxes, so cash-burners are taxed realistically.
- **The terminal value uses a reinvestment rate consistent with terminal ROIC** (`reinvestment = g ÷ ROIC`), so perpetual growth is paid for rather than assumed free.

### 4. WACC
CAPM cost of equity from the live risk-free rate, beta and a ~5% equity risk premium; cost of debt from the company's own interest/debt or, when that's unreliable, a synthetic credit spread inferred from interest coverage (Damodaran's method); weighted by market values.

### 5. Cross-checks & the score
Monte Carlo, reverse DCF, comps and a WACC × terminal-growth sensitivity grid all triangulate the point estimate. The **1–100 score** then blends five transparent sub-scores with **regime-dependent weights** — a hypergrowth cash-burner leans on growth quality and cash runway (its DCF is down-weighted), a mature compounder leans on valuation and returns on capital.

### 6. Optional AI layer
The full quantitative result is handed to Claude, which returns structured JSON (moat, risks, catalysts, bull/bear, assumption critique, overall take). It's explicitly prompted to be skeptical and to flag where the tool's automated assumptions look aggressive. No key? The rule-based fallback derives the same commentary from the numbers.

---

## Whole-market screener & backtest

The 🔥 **Hot stocks** tab ranks the market 1–100 and the 📊 **Backtest** tab checks whether that ranking has ever paid. It's built in the spirit of my [equity factor screener](../screener): two buckets (profitable "established" vs unprofitable "speculative"), each factor standardized *cross-sectionally* per scan (winsorized z-score, so "good" is relative to that day's peers), combined by weight, then converted to a 1–100 percentile. The top names get the full adaptive DCF for a fair-value gap; sectors are aggregated into an attractiveness ranking; and a portfolio builder turns the winners into a sector-capped, score-weighted basket.

The backtest ports the same discipline: it only calls something an "edge" when the Information Coefficient is significant, the score quintiles are monotonic, the top-minus-bottom spread survives costs, *and* it holds out-of-sample — so a lucky equity curve doesn't pass. It's honest about **survivorship bias** (free feeds drop delisted losers) and about the fact that a fully survivorship-free *fundamental* backtest needs point-in-time filings (the EDGAR reconstruction in the screener project).

Run a scan, then read it in the dashboard:
```bash
python -m valuation.screener.scan                 # fast bundled universe
python -m valuation.screener.scan --whole-market  # every US filer (slow on free feed)
```
Data is **free by default** (SEC EDGAR + Stooq + Yahoo). Set an `FMP_API_KEY` to make whole-market scans fast. **See [RUNBOOK.md](RUNBOOK.md) for the full go-live checklist** — scheduling the weekly scan, verifying live data, insider signals, and the backtest.

## Optional AI setup
Copy `.env.example` to `.env` and add a key:
```
ANTHROPIC_API_KEY=sk-ant-...
```
The tool auto-detects the provider. OpenAI is supported too (`OPENAI_API_KEY`). Everything works without any key.

---

## Project structure
```
valuation-tool/
├── run.py / run.bat / run.sh      # launchers
├── cli.py                          # command-line / batch mode
├── requirements.txt
├── valuation/
│   ├── config.py                   # settings & keys (all optional)
│   ├── data/                       # yahoo, edgar, macro, fetcher, models
│   ├── engine/                     # classify, assumptions, wacc, dcf,
│   │                               #   scenarios, montecarlo, reverse_dcf,
│   │                               #   comps, sensitivity, scoring, pipeline
│   ├── ai/analyst.py               # optional LLM qualitative layer
│   ├── report/                     # excel + pdf exporters
│   └── web/                        # Flask app, dashboard (HTML/CSS/JS)
└── tests/                          # offline engine tests + fixtures
```

Run the tests with `python tests/test_engine.py` (no pytest needed) or `python -m pytest tests/`.

---

## Run it as a subscription service (optional)
A full hosted SaaS layer is included: accounts, a marketing landing + pricing page, **Free / Pro / Premium** tiers with feature gating, **Stripe** billing (checkout + webhooks + customer portal), a weekly server-side scan worker, and email digests — plus Docker/gunicorn/Procfile for one-command deploy.
```bash
python run_saas.py         # local: landing → register → gated dashboard at /app
```
**[SAAS_RUNBOOK.md](SAAS_RUNBOOK.md)** is the go-live checklist (Stripe, hosting, domain, email) and — importantly — a **compliance** section: charging for stock signals can trigger securities regulation, so talk to a securities attorney before launch. *(Not legal advice.)*

## Honest limitations
I'd rather state these plainly than oversell the tool:

- **A DCF is only as good as its inputs.** The assumption engine is a sensible starting point, not gospel — use the "tweak & re-run" panel and the reverse-DCF check, and lean on comps where DCF reliability is flagged low.
- **The 1–100 score is a transparent heuristic, not a proven alpha signal.** It's designed to be explainable and sensible, but I have *not* yet run a point-in-time backtest establishing that it predicts forward returns (in the same spirit as my equity-screener project, I'd rather build the honest test than claim an edge I haven't measured). That backtest is the top item on the roadmap.
- **Financials (banks/insurers) don't fit an unlevered-FCF DCF** and are flagged accordingly; treat their output as multiples-only.
- **Comps use sector-benchmark multiples by default** — a rough cross-check, not a curated peer set (supply your own peers for precision).
- **`yfinance` scrapes Yahoo** and can occasionally be rate-limited or change labels; SEC EDGAR backstops US names.
- **Not investment advice.**

## Roadmap
- Point-in-time backtest of the score's predictive power (information coefficient, quantile spreads, out-of-sample).
- Real peer-set selection for comps.
- Segment-level revenue builds and explicit NWC modeling.
- Persisted watchlists and historical snapshots.

---

*Built by Donovan Corbin. Extends the [Nike (NKE) DCF](../nike-dcf-valuation) into a general-purpose valuation engine.*
