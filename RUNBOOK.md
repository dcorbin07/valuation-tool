# Activation Runbook — what *you* need to do to go fully live

Everything is built and tested offline against synthetic fixtures. The pieces that
touch the live internet (Yahoo, SEC EDGAR, Stooq, FMP) can't be exercised in a
sandbox, so this is the checklist to prove them on your machine and switch on the
whole-market scanner, the weekly job, the backtest, insider signals, and AI.

Work top to bottom. Each step says what to run and what "working" looks like.

---

## 0. One-time setup (5 min)
1. Install **Python 3.10+** (check "Add Python to PATH").
2. Double-click **`run.bat`** (Windows) or run `./run.sh`. It makes a virtual env,
   installs `requirements.txt`, and opens the dashboard at http://127.0.0.1:5000.
3. **Smoke test the valuation engine:** type `AAPL` → Analyze. You should get a
   fair value, score, scenarios, Monte Carlo, and AI/rule-based analysis. If this
   works, the Yahoo + EDGAR + Treasury data path is live. ✅

---

## 1. First hot-stocks scan (free, no key)
The dashboard's 🔥 Hot stocks tab reads a **saved snapshot**. Create one:

```bash
# fast: ~180 bundled liquid names
python -m valuation.screener.scan

# or a broader slice of the market (slow on the free feed — see step 2)
python -m valuation.screener.scan --whole-market --limit 800 --dcf-top 12
```
Then in the dashboard → 🔥 Hot stocks → **Load latest**. You'll see the ranked
1–100 list, sector attractiveness, and a built portfolio. ✅

> The free feed fetches each name from Yahoo/Stooq, so a few hundred names takes a
> few minutes and thousands takes a while. That's exactly why step 2 exists.

---

## 2. Whole US market — pick your data path
You chose *free-first, FMP-ready*. Two options:

**A) Free (SEC EDGAR + Stooq).** `--whole-market` pulls the full EDGAR filer list
(~10k names) and scores them from free data. It works but is slow and best run as
the **weekly job** (step 3), not interactively. Start with `--limit 1500` and grow.

**B) FMP (fast, ~$22/mo Starter).** Get a key at financialmodelingprep.com, then in
`.env`:
```
FMP_API_KEY=your_key_here
```
The tool auto-detects it and switches the provider to FMP — the universe then comes
from one screener call and scanning the whole market is fast.

> **Verify FMP field names on first run.** FMP occasionally renames TTM fields per
> plan. Run `python -m valuation.screener.scan --whole-market --limit 50` and check
> the top rows have sane value/quality/growth numbers. If a factor is all blank,
> open `valuation/screener/providers.py` → `_fmp_to_metrics` and adjust the field
> keys to match your plan's payload (the code already tries common aliases).

---

## 3. Schedule the weekly "hot stocks of the week" (Windows Task Scheduler)
`run_weekly_scan.bat` runs the scan and saves a fresh snapshot. Schedule it for,
say, **Monday 6:00 AM**:

```bat
schtasks /create /tn "HotStocksWeeklyScan" ^
  /tr "%CD%\run_weekly_scan.bat" /sc weekly /d MON /st 06:00 /f
```
(Run that from the project folder in `cmd`. On macOS/Linux use `cron`:
`0 6 * * 1  /path/to/valuation-tool/run.sh` style, calling the scan module.)

Each Monday you'll have a new dated snapshot; the dashboard shows the latest and
keeps history. Edit the batch file to drop `--limit` once you're on FMP.

---

## 4. Backtest — does the hot list actually beat the market?
Dashboard → 📊 Backtest → **Run backtest** (Source = *Latest hot list*), or:
```bash
python -c "from valuation.backtest.run import run_from_store, print_verdict; from valuation.screener.store import Store; print_verdict(run_from_store(Store(), top=50, horizon_days=21))"
```
Read the verdict the way your screener taught: a real edge needs a **significant
positive IC**, **monotonic quantiles**, a **top-minus-bottom spread that survives
costs**, and it must **hold out-of-sample**. The engine won't call a lucky equity
curve "edge."

**Two honesty caveats you already know:**
- **Survivorship bias.** Free price feeds only carry names still listed today, so
  delisted losers are missing and any edge is overstated. Treat a positive free-data
  result as "worth confirming," not proof.
- **Point-in-time fundamentals.** The built-in free backtest scores names on a
  *momentum* factor that is genuinely point-in-time from prices. Backtesting the
  *full fundamental composite* survivorship-free needs fundamentals as-known-on-each-
  date — that's the EDGAR filing-date reconstruction your `pit_data.py` already does.
  Port that in as the `score_fn` argument to `build_price_panel` (hook is there), or
  use a survivorship-free vendor. This is the one piece that needs your data work.

---

## 5. Insider (Form 4) signals
Free via EDGAR. Add them to the top names of a scan:
```bash
python -m valuation.screener.scan --insider
```
Set a descriptive SEC User-Agent in `.env` (they ask for contact info):
```
SEC_USER_AGENT=Donovan Corbin donovanicorbin@gmail.com
```
Verify one name returns a non-neutral score when you know there's been recent
insider buying (e.g., a name from OpenInsider). The parser handles the common Form-4
XML layout; exotic filings fall back to neutral (50).

---

## 6. AI qualitative layer (optional)
Add to `.env` to unlock Claude-written analysis + assumption critiques:
```
ANTHROPIC_API_KEY=sk-ant-...
```
Without it, everything still works with the rule-based fallback.

---

## Live-I/O modules to prove on your box
These are written defensively but were validated only against synthetic data here:

| Module | Proves | How to check |
|---|---|---|
| `data/yahoo.py`, `data/edgar.py` | single-name fundamentals/price | value `AAPL` in the app |
| `screener/prices.py` | Stooq/yfinance history | scan runs; momentum column populated |
| `screener/providers.py` (FMP) | whole-market data | step 2 verify |
| `screener/insider.py` | Form-4 parsing | step 5 verify |
| `backtest/panel.py` | price panel builds | step 4 runs without "empty panel" |

---

## Cost summary
- **$0** to run everything on free data (SEC EDGAR + Stooq + Yahoo).
- **~$22/mo** if you add FMP Starter for fast whole-market scans + cleaner history.
- **A few $/mo** if you enable the Claude AI layer (only fires when you ask for it).

## The one bigger project (roadmap)
A fully survivorship-free, point-in-time **fundamental** backtest of the composite.
The engine, panel interface, and momentum-PIT path are done; what remains is feeding
it as-reported fundamentals by filing date (your `pit_data.py` approach) or a
survivorship-free vendor. That's the difference between "this looks promising" and
"this is a validated edge" — and it's worth doing before sizing real capital.
