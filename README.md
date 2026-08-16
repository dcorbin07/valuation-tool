# Valquo

**A stock-analysis toolkit built around a research lab whose job is to disprove it.**

Valquo is a Flask application with two halves. The first is a **valuation engine**: type any
ticker and get an adaptive DCF with scenarios, a Monte Carlo distribution, a reverse-DCF check,
comps and a transparent 1–100 score. The second is an **Edge Lab**: a point-in-time backtest,
pre-registered and placebo-calibrated, that exists to falsify the first half's screener.

Most of what the Edge Lab has produced are **rejections and nulls**. That is the honest headline,
and it is the main reason to trust anything else here.

> **Educational tool, not investment advice.** Fair value is a *model output*, not a price target.
> Nothing here executes trades or manages money.

> 🧭 **Working on the repo, or checking what has actually been measured?** Read
> **[START_HERE.md](START_HERE.md)** — clone-to-green-suites in five minutes and the state of the
> evidence. **[VALQUO_LEDGER.md](VALQUO_LEDGER.md)** is the contractual answer to "is X done?".

---

## What Valquo is, and what each part actually claims

Five surfaces share one codebase. **They do not carry equal evidence, and the difference matters
more than any individual number:**

| surface | what it does | evidential status |
|---|---|---|
| **Valuation engine** | Adaptive DCF for any ticker from live data, no API key | **A model, not a claim.** Its output is an estimate under stated assumptions; it has never been backtested as a return signal. |
| **Hot-stocks screener** | Ranks the market 1–100 on a 9-theme cross-sectional composite | **The one measured claim** — see the evidence section below. |
| **Valquo Index** | A published, pre-registered forward paper track of the screener's picks | **Running, not yet evidence.** No verdict before **2031**. |
| **Dip Detector** | Flags names well below their recent high that pass quality/health floors | **A screen, with a split verdict** — the *return* claim is NULL, the *risk* claim is measured. |
| **Options / intraday signals** | Options context, technicals, alerts | **A screen. The entry signal is measured and it does not work** — see "What is not claimed". |

### The screener's evidence, in the record's own numbers

Measured on **2,531 names over 69 quarterly rebalances (2009–2026)**, one panel, point-in-time,
survivorship-free. Every figure ships in `BACKTEST_RESULTS.json` and is reproduced here from it:

| | |
|---|---|
| Top-decile alpha vs the equal-weighted universe | **+7.17%/yr**, gross of costs |
| …after measured trading costs | **+6.07%/yr** (breakeven 134.1 bps one-way vs a measured 33.4 bps; 261%/yr turnover) |
| …vs SPY total return over the same windows | **+9.99%/yr** |
| Long-short spread | +11.04%/yr, HAC *t* **2.62** |
| Decile ordering (−1.0 is perfect) | **−0.89** |

**What that does and does not survive — quote both halves or neither:**

- ✅ **Its own noise floor.** Thresholds here are not conventions; they are *calibrated* by pushing
  100 shuffled-signal panels through the real pipeline. The long-short HAC *t* of 2.62 clears the
  calibrated floor of **2.2837**. (The same exercise found the usual "*t* > 2" bar is cleared by
  pure noise 8% of the time, and that PBO < 50% is not a bar at all — noise sits at 46.7%.)
- ✅ **Costs**, with a ~4× margin.
- ✅ **Factor models.** FF5+MOM leaves **+6.99%/yr** unexplained (NW *t* 3.98).
- ✅ **A split by name**, which has no regime confound: across 400 half-universe books, **not one
  came back negative**.
- ✅ **International, out-of-sample.** The untuned composite mapped onto independent data
  replicates in Japan (*t* 3.85) and developed Europe (*t* 4.30) — and the **USA is the weakest
  region tested**, so the structure is not a US artifact. It corroborates that the premia are
  real; it does **not** corroborate Valquo's magnitude.
- ❌ **The Harvey–Liu–Zhu hurdle.** Counting all **224** pre-registered equity trials the research
  log has ever charged gives a hurdle of **3.29**, and 2.62 falls short by 0.67.
- ❌ **The conventional Deflated Sharpe bar** (0.79 against a >0.95 convention), though it clears
  the placebo-calibrated 0.66.

The artifact ships the tension rather than resolving it: HLZ prices *the best of N draws*, and the
deployed composite is flat 1/7 weights that were never tuned — `cpcv.adopt` is `false` on every
run — so those 224 trials are overwhelmingly *rejected alternatives to it* rather than candidates
it beat. Reasonable people can read that either way. **It is one panel, and it is not a forward
test.**

---

## How the evidence is produced

The unusual part of this repo is the protocol, not the model.

- **Pre-registration.** A hypothesis, its threshold and its kill conditions are written to a
  `PREREG_*.md` file and committed **before** the measurement code exists — 53 of the 59 registers
  on disk were committed in a markdown-only commit, and a test now enforces that for new ones.
- **A trial counter that costs something.** Every test charges the research log, and the count
  feeds the Deflated Sharpe and the HLZ hurdle. Searching harder makes the bar harder. `N` = 224
  for equity, 292 for options.
- **Calibrated thresholds.** Bars come from a placebo, not convention (see above).
- **Three independent cold audits**, ~250 adjudicated items in `VALQUO_LEDGER.md`, each row
  carrying its verdict, commit and write-up.
- **Corrections stay in the record.** When a published number turns out to be wrong it is
  corrected *in place*, with the old value quoted and dated. `CLAUDE.md` is that record. It is why
  the numbers here can be trusted even though the project has been wrong many times.

Findings that came back **NULL or REJECTED** include: sector-neutral ranking (twice), an ML tree
combiner (its deciles ran *backwards* out of sample), five alternative weighting schemes,
short-term reversal, the options entry signal, cash-secured puts on healthy dips, and most of the
interaction and freshness families. The rejections are the product.

---

## The forward paper track — paper, and years from a verdict

`PAPER_TRACK_CONTRACT.md` is a **signed pre-registration** of a live forward test of the Valquo
Index. Its terms were fixed before the data existed:

- **Paper only.** No real money, no execution, no broker.
- **Operational gate 2027-02-13. Verdict 2031-08-13.** Nothing before those dates is a verdict,
  in either direction.
- **It is deliberately weak, and says so.** At the backtested edge, power is ~13% at one year.
  A track that has not crossed its threshold is the *expected* outcome and is **not** evidence
  against the strategy.
- **An adopted change to scoring resets the clock.** The track is on its 4th vintage
  (inception 2026-08-13); improving the model costs elapsed evidence, on purpose.
- **It is currently not recording.** The bound series has a known writer gap
  (`recording_ok: false`), tracked as ledger row `PT-WRITER`. The operational gate cannot pass
  while that is true, and the meter reports it rather than hiding it.

---

## What is **not** claimed

Stated plainly, because each of these is something a reader could reasonably assume:

- **The options entry signal does not work.** Measured against a five-seed random-entry control on
  the same universe, the alert book earns **+3.27%/trade against the control's +8.33%** — a
  **−5.06pp** gap, significant on a paired name-year sign test. Picking the *day* subtracts value.
  The options surfaces are context and education, not a demonstrated edge.
- **The Dip Detector does not claim returns.** Four arms, four nulls. What *is* measured is a
  **risk** result: among names already down 20%, those passing the quality/health floors fell a
  further 20% about **25% less often** (32.5% vs 43.4%). That effect is real and replicated, but
  it is about *falling further*, not about recovering — and it is **weakest in megacaps**, which
  is where the live book is concentrated.
- **The valuation engine's fair value is not a forecast**, and financials (banks/insurers) are
  flagged low-reliability because unlevered-FCF DCF is the wrong tool for them.
- **Nothing is auto-tuned into production.** Live weights are flat 1/7 and were never fitted.
- **No verdict exists from live trading**, because there is none.

---

## Data, and an important licence limit

The product runs on **free data** — Yahoo Finance, SEC EDGAR, Stooq — with no API key required.

The **research** is different, and this constrains what anyone can do with it. The backtest panel
is built from **licensed Sharadar exports** which are gitignored and never published here.
Sharadar's terms are **personal-use only and forbid commercial use of the data "or any
derivation"**. So the headline figures are reproducible only by someone holding their own licence,
and that licence would not let them publish what they derived. The international replication data
(JKP Global Factor Data) is **CC BY-NC 4.0, research-only**, and may never ship in the product.

`BACKTEST_RUNBOOK.md` documents the rebuild; `DATA_AND_METHODS.md` explains why point-in-time,
survivorship-free data is the thing that decides whether a backtest means anything.

**No licence file is present, so default copyright applies** — all rights reserved. Ask before
reusing.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # NOT the .lock files - those are linux/CI only
python run.py                        # http://127.0.0.1:5000
```

Windows: double-click **`run.bat`**. macOS/Linux: `./run.sh`.

```bash
python cli.py AAPL                       # value one ticker
python cli.py AAPL --excel --pdf         # Excel model + PDF tearsheet
python cli.py AAPL MSFT NVDA KO --rank   # score and rank a watchlist
python -m valuation.screener.scan        # run a screener scan
```

Optional AI layer: copy `.env.example` to `.env` and add `ANTHROPIC_API_KEY` (or
`OPENAI_API_KEY`). Everything works without a key — a rule-based fallback produces the same
structure.

### Tests

No pytest needed, and **no `data/` directory required** — every suite runs from a clean clone,
which is what CI does on every merge:

```bash
python tests/test_engine.py                                          # one suite
for f in tests/test_*.py; do python "$f" || echo "FAILED $f"; done    # all of them
```

Judge a suite by its **exit code**, not by grepping for `OK`.

---

## How the valuation engine works

1. **Data (free, no key).** `yfinance` for statements, price, shares and beta; **SEC EDGAR**
   fills gaps and cross-checks US fundamentals; the live 10-year Treasury sets the risk-free rate.
2. **Classification** into *mature, growth, hypergrowth, cyclical* or *financial*, which drives
   everything downstream — including an explicit reliability flag.
3. **FCFF DCF.** Reinvestment tied to growth through a sales-to-capital ratio; operating margins
   converge to a sustainable target; early losses accrue an NOL balance that shields future taxes;
   terminal reinvestment consistent with terminal ROIC, so perpetual growth is paid for.
4. **WACC.** CAPM cost of equity from the live risk-free rate and beta; cost of debt from the
   company's own interest expense or a synthetic spread from interest coverage.
5. **Cross-checks.** Monte Carlo (10,000 trials → P(undervalued)), reverse DCF, comps, and a
   WACC × terminal-growth sensitivity grid.
6. **The 1–100 score.** Five sub-scores with regime-dependent weights, every weight shown.
7. **Optional AI layer.** The quantitative result is handed to Claude, prompted to be skeptical
   and to flag where the tool's own assumptions look aggressive.

---

## Project structure

```
valuation-tool/
├── run.py / run.bat / run.sh       # launchers
├── cli.py                          # command-line / batch mode
├── valuation/
│   ├── engine/                     # classify, assumptions, wacc, dcf, scenarios,
│   │                               #   montecarlo, reverse_dcf, comps, scoring
│   ├── data/                       # yahoo, edgar, macro, fetcher, models
│   ├── screener/                   # hot-stocks screener + the Valquo Index track
│   ├── intraday/                   # intraday + options signals
│   ├── edge/                       # the Edge Lab: point-in-time backtest, CPCV,
│   │                               #   placebo calibration, forward paper track
│   ├── ai/, report/, web/, saas/   # LLM layer, exports, Flask app, hosted tier
├── scripts/                        # research + maintenance entry points
└── tests/                          # offline suites, no data/ required
```

A hosted SaaS layer is included (accounts, tiers, Stripe billing, digests):
`python run_saas.py`. **[SAAS_RUNBOOK.md](SAAS_RUNBOOK.md)** covers go-live and, importantly, a
compliance section — charging for stock signals can trigger securities regulation. *(Not legal
advice.)*

---

## Honest limitations

- **A DCF is only as good as its inputs.** The assumption engine is a sensible starting point, not
  gospel. Use the tweak-and-re-run panel and the reverse-DCF check.
- **The screener's evidence is one panel and one 18-year window**, gross-of-cost figures quoted
  alongside net, and it fails the strictest multiple-testing bar. The forward test that would
  settle it does not report until 2031.
- **`yfinance` scrapes Yahoo** and can be rate-limited or change labels; EDGAR backstops US names.
- **Comps use sector-benchmark multiples by default** — a rough cross-check, not a curated peer set.
- **Not investment advice.**

---

*Built by Donovan Corbin. Extends the
[Nike (NKE) DCF](https://github.com/dcorbin07/nike-dcf-valuation) into a general-purpose
valuation engine, in the spirit of the
[equity factor screener](https://github.com/dcorbin07/stock_screener).*
