# quant_bots

A small portfolio of systematic trading bots that share a common core. Built to
run on uncorrelated edges side-by-side, so the combination is smoother than any
single strategy — the same principle multi-strategy funds use.

## Status

- **`trend/` — Bot #2: trend-following (DONE, T1–T8).** Time-series momentum
  (12-month) on a cross-asset ETF basket, long/short, volatility-targeted
  sizing, daily rebalance. Runs autonomously with a preview/paper/live mode
  switch. This is the "crisis alpha" complement to the options bot — it tends
  to profit in the sharp selloffs where short-volatility strategies suffer.
- **`momentum/` — Bot #3: cross-sectional momentum (DONE).** Ranks a liquid
  stock universe by 12-1 momentum (trailing 12-month return, skipping the most
  recent month), holds the top winners long and bottom losers short, sized
  inverse-volatility, rebalanced daily. Reuses the trend bot's risk and
  portfolio machinery wholesale — only the universe and signal differ. A third,
  distinct return driver (relative momentum) alongside the options bot
  (volatility premium) and trend bot (time-series momentum / crisis alpha).
- The options bot (Bot #1) is now co-located here at `options/` — the full,
  self-contained project (159 tests), running exactly as it does standalone. It
  keeps its own copies of the shared-style modules rather than importing
  `core/`; truly unifying it to share `core/` is an optional later refactor
  with no functional benefit, just tidiness. For now all three bots live in one
  folder.

## Optional integrations degrade gracefully

Nothing in `.env` is mandatory beyond a bot's own broker credentials:

- **No `DISCORD_WEBHOOK_URL`** → notifications are logged instead of sent. No error.
- **No `ANTHROPIC_API_KEY`** (options bot advisor) → the advisor stays disabled;
  the bot trades normally without news-event flagging. No error.
- **No broker credentials for a given bot** → that bot prints a one-line
  "not configured, skipping" message and exits cleanly (code 0). It does not
  crash, and it does not affect the other bots, which run as separate processes.

Each bot uses ONLY its own credentials — there is no shared fallback. The trend
bot reads `TREND_TRADIER_*`, the momentum bot reads `MOMENTUM_TRADIER_*`, and
the options bot has its own `.env` in `options/`. The three trade fully
independent accounts so their track records never mix. You can configure and
run them one at a time; the others simply decline to start until given their
own credentials.

## Layout

```
quant_bots/
├── core/                    Shared infrastructure (used by all bots)
│   ├── tradier.py           Broker client — equity + option orders
│   ├── calendar.py          Market hours + US holiday guard
│   ├── trading_mode.py      preview/paper/live switch + guardrails
│   ├── journal.py           Durable append-only trade journal
│   ├── discord.py           Notifications
│   ├── account_state.py     Daily equity snapshot (kill-switch input)
│   └── occ_symbol.py        Option symbol helpers (for option positions)
├── trend/                   Bot #2: trend-following
│   ├── universe.py          Cross-asset ETF basket (26 instruments)
│   ├── signals.py           Time-series momentum + volatility
│   ├── strategy.py          Inverse-vol target weights
│   ├── risk.py              Vol-targeted sizing + exposure caps + kill switch
│   ├── portfolio.py         Current-vs-target diff → rebalance orders
│   └── orchestrator.py      Daily rebalance job + scheduler
├── momentum/                Bot #3: cross-sectional momentum
│   ├── signals.py           12-1 ranking across a stock universe
│   ├── strategy.py          Inverse-vol target weights (top winners / bottom losers)
│   └── orchestrator.py      Daily rebalance (reuses trend's risk + portfolio)
├── options/                 Bot #1: put-credit-spread bot (self-contained, 159 tests)
│   ├── broker/ screener/ strategy/ risk/ portfolio/ orchestrator/ notify/
│   └── scripts/run_bot.py   Its own entry point (run from within options/)
├── scripts/
│   ├── run_trend_bot.py     Bot #2 entry point
│   └── run_momentum_bot.py  Bot #3 entry point
└── tests/                   52 tests (trend + momentum); options has its own 159
```

## Running the trend bot

```bash
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1   |   mac/linux: source venv/bin/activate
pip install -r requirements.txt
python -m unittest discover tests        # expect OK

# One rebalance, preview only (safe), during market hours:
python scripts/run_trend_bot.py --once

# Paper mode, one rebalance:
#   Windows: $env:BOT_MODE="paper"; python scripts/run_trend_bot.py --once
#   mac/linux: BOT_MODE=paper python scripts/run_trend_bot.py --once

# Autonomous (daily rebalance on a schedule, runs until Ctrl-C):
python scripts/run_trend_bot.py
```

Live trading requires three independent settings to agree: `BOT_MODE=live`,
`BOT_ALLOW_LIVE=YES_I_UNDERSTAND`, and `TRADIER_SANDBOX=false`. Default is
preview-only. Long/short needs a margin account; in a cash-only account the
shorts will be rejected (long-only still works).

## Running the momentum bot (Bot #3)

```bash
# One rebalance, preview only, during market hours:
python scripts/run_momentum_bot.py --once

# Autonomous (daily rebalance, runs until Ctrl-C):
python scripts/run_momentum_bot.py
```

Set `MOMENTUM_TRADIER_TOKEN` / `MOMENTUM_TRADIER_ACCOUNT_ID` for its own paper
account (recommended — keeps each bot's track record independent), else it
falls back to the shared `TRADIER_*` vars. Same preview/paper/live switch as
the other bots. Its first run builds a stock universe (~30-60s) before ranking.

## The strategy in one paragraph

Each trading day, for every instrument in the basket, compute its trailing
12-month return. Go long the ones trending up, short the ones trending down.
Size each position inversely to its volatility (calm instruments get bigger
positions) so every holding contributes comparable risk, then scale the whole
book to a target volatility and cap gross/net/per-name exposure. Rebalance
toward that target once a day. Because 12-month momentum moves slowly, turnover
is low — most days only a few instruments trade.

## Running the options bot (Bot #1)

It's self-contained — run it from within its own folder:

```bash
cd options
python -m unittest discover          # 159 tests
python scripts/run_bot.py            # scheduler, preview mode
python scripts/run_bot.py --once open    # single job
```

Same `BOT_MODE` preview/paper/live switch. Its `.env` lives in `options/.env`
(or it reads the parent environment). See `options/README.md` for its full
prep → open → manage daily cycle.

## SIM mode + measuring the strategies (Option 3)

Each bot can run in **SIM mode** — pure simulation. It uses one Tradier sandbox
only for real quotes, assumes fills at those quoted prices, and tracks its own
independent paper account in `data/sim/<bot>/`:

- `portfolio.json` — current simulated holdings + cash + realized P&L
- `equity_curve.jsonl` — one daily mark-to-market snapshot per line

No separate broker accounts needed — each bot keeps its own book in software,
which is how multi-strategy shops actually measure separate strategy "pods".

```bash
# Run each bot once in sim mode (during market hours, for live quotes):
$env:BOT_MODE="sim"; python scripts/run_trend_bot.py --once
$env:BOT_MODE="sim"; python scripts/run_momentum_bot.py --once

# After a few weeks of daily runs, see how they performed and correlate:
python scripts/correlation_tracker.py
```

The correlation tracker reports each strategy's return/vol/Sharpe and the
correlation matrix between them — the input you need to decide how to weight
them in a combined portfolio. Low/negative correlations mean the combination is
smoother than any single strategy.

`data/sim/` is excluded from the packaged zip, so your accumulated track record
survives re-extracting an updated build.

## Backtesting (fast path to correlation data)

The trend and momentum bots can be backtested against historical daily prices —
fetched through your existing Tradier connection (no new data source or paid
subscription). This replays the REAL strategy pipelines day-by-day and writes
equity curves in the same format as live SIM, so the correlation tracker works
on them directly.

```bash
# Backtest both over the last 3 years:
python scripts/run_backtest.py --bots trend momentum --years 3

# Or a specific window:
python scripts/run_backtest.py --bots trend --start 2022-01-01 --end 2024-12-31

# Then compare the backtested curves:
python scripts/correlation_tracker.py --bots trend_backtest momentum_backtest
```

This is the fast way to get correlation/allocation data: years of daily returns
across multiple market regimes in minutes, instead of waiting months for live
SIM to accumulate. Caveats: Tradier free history goes back a few years (not
decades); the momentum stock universe is today's (survivorship bias); fills are
assumed at the daily close. Good for estimating how the strategies correlate;
not for precise absolute-return claims. The options bot isn't backtested here —
its options-chain history needs paid IV data, so live SIM remains its validator.

## End-of-day Discord summary

A daily heartbeat across all bots — posts each strategy's equity, today's move,
total return, and position count to Discord (or logs it if Discord isn't set).
Works for sim, paper, and live.

```bash
python scripts/end_of_day_summary.py
```

Run it once after market close. On the Oracle box, schedule it (cron, ~4:30pm
ET) right after the bots' last run so you get a daily digest on your phone
without touching the machine. Only the human-readable summary leaves the box;
all data stays local with the bots.

## All three bots now run in SIM

The options bot now supports SIM mode too (it tracks open spreads in its own
OptionsSimPortfolio, marks them to market each manage cycle, and closes on the
same profit/stop/time rules — writing an equity curve in the identical format).
So all three bots can run consistently with BOT_MODE=sim, producing comparable
equity curves for valid three-way correlation:

    data/sim/options/equity_curve.jsonl
    data/sim/trend/equity_curve.jsonl
    data/sim/momentum/equity_curve.jsonl

    python scripts/correlation_tracker.py --bots options trend momentum

## Weekly correlation report (readable file)

`scripts/weekly_report.py` writes a self-explanatory report to
`data/reports/correlation_YYYY-MM-DD.md`. Unlike the terminal-only correlation
tracker, this file explains every number inline (returns, volatility, Sharpe,
and the correlation matrix) so you can read it on its own — and it bundles the
raw stats as JSON at the bottom so you can upload the whole file to Claude for
deeper interpretation.

```bash
python scripts/weekly_report.py
# → data/reports/correlation_2026-06-05.md
```

It also posts a short Discord heads-up pointing to the file. Run it manually, or
on a weekly systemd timer (see deployment notes). The correlations only become
meaningful after ~20+ overlapping trading days, so early reports will flag that.

## Bot #4: mean-reversion + improvements (added)

**Mean-reversion bot** (`reversion/`): the 4th strategy and the one genuinely
uncorrelated new edge. Short-horizon (z-score reversal) — buys oversold names,
shorts overbought ones, on a ~1-month window. This is the structural opposite of
the momentum bot (continuation over 3-12mo) and fills the short-horizon reversal
regime the other three miss. Reuses the shared risk/portfolio machinery; runs in
SIM like the others (`data/sim/reversion/`). Risk is controlled by breadth (many
small names), NOT tight stops — the evidence is clear that stops hurt
mean-reversion. Run: `BOT_MODE=sim python scripts/run_reversion_bot.py --once`.

**Improvements to existing bots:**
- *Multi-lookback blending (trend):* the trend signal now blends 3/6/12-month
  horizons instead of a single 12-month lookback — a robustness gain so the
  strategy doesn't hinge on one arbitrary window.
- *Regime gate (momentum + reversion):* both cross-sectional stock bots now
  suppress SHORTS when the broad market (SPY vs its 200-day MA) is in an
  uptrend — avoiding the worst case of shorting individual names into a rally.
  (Deliberately NOT applied to the trend bot: it holds non-equity assets and
  responds to each instrument's own trend, so a broad-equity gate there would
  suppress exactly the crisis-alpha positions you want.)
- *Vol-scaled sizing (options):* the options bot now sizes DOWN when a
  candidate's ATM IV is extreme (likely a priced binary event) and normally
  when IV is moderate — pulling capital toward cleaner volatility premium.

All four bots install as services via `bash deploy/install_services.sh`.
