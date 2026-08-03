# Options Bot — Put Credit Spreads

Systematic put credit spread bot built on the Tradier API.

This is **V1-V9 + the completed daily cycle**. The bot runs fully autonomously:
a pre-market **prep job** builds the universe and screens candidates, the
**open job** places risk-sized spreads and confirms their fills, and **manage
jobs** handle exits through the session — all on a schedule, with a durable
trade journal, a startup self-check, order-fill confirmation, Discord
notifications, and an optional LLM advisory pass (flag-only). Three-way
preview/paper/live safety switch with hard guardrails; default is
preview-only. The only deferred piece is V7 (backtest), which needs paid
historical-IV data — paper trading validates the strategy for free.

## Strategy (for context, not yet implemented)

Sells defined-risk put credit spreads on liquid optionable stocks/ETFs to
collect the volatility risk premium. Approximate parameters:

- Short put at ~20–30 delta, long put $5 below
- 30–45 days to expiration
- Underlyings filtered for IV rank > 30, no earnings within DTE window,
  tight bid-ask spreads, sufficient liquidity
- Profit target: 50% of credit received
- Stop loss: 2× credit received
- Time exit: 21 DTE if neither target hit

## Project layout

```
options_bot/
├── README.md
├── requirements.txt
├── .env.example              -> copy to .env and fill in real values
├── .gitignore
├── broker/
│   ├── __init__.py
│   ├── occ_symbol.py         OCC option symbol build/parse
│   └── tradier.py            Tradier REST API client
├── data/
│   ├── __init__.py
│   ├── universe.py           Daily universe builder
│   ├── earnings.py           yfinance earnings calendar
│   └── cache/                Persisted snapshots (created on first build)
├── screener/
│   ├── __init__.py
│   └── screener.py           Daily candidate screener
├── strategy/
│   ├── __init__.py
│   └── strategy.py           Put credit spread order construction
├── risk/
│   ├── __init__.py
│   ├── risk.py              Position sizing + concentration + kill switches
│   └── state.py             Daily account equity snapshot
├── portfolio/
│   ├── __init__.py
│   └── portfolio.py         Position sync, P&L, exit decisions
├── orchestrator/
│   ├── __init__.py
│   ├── calendar.py          Market hours + US holiday guard
│   ├── config.py            Trading-mode switch + safety guardrails
│   ├── jobs.py              Prep job + open job + manage job
│   ├── scheduler.py         APScheduler autonomous loop
│   ├── journal.py           Durable append-only trade journal
│   └── startup.py           Startup self-check (dirs, creds, config)
├── notify/
│   ├── __init__.py
│   ├── discord.py           Discord webhook notifier
│   └── advisor.py           LLM advisory layer (flag-and-log only)
├── scripts/
│   ├── smoke_test.py         End-to-end Tradier check
│   ├── build_universe.py     Run the universe builder
│   ├── screen.py             Run the screener
│   └── build_orders.py       Build & preview orders from candidates
└── tests/
    ├── test_occ_symbol.py    Broker unit tests
    ├── test_universe.py      Universe builder unit tests
    ├── test_screener.py      Screener unit tests
    ├── test_strategy.py      Strategy unit tests
    └── test_risk.py          Risk manager unit tests
```

## Setup

Requires Python 3.10 or newer.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up credentials
cp .env.example .env
# Then edit .env with your real Tradier token and account ID
```

Get your Tradier API credentials from the API Access page after logging in to
your Tradier account. You want the **sandbox** token + sandbox account ID for
development. Production credentials should not be added until you've finished
paper trading and are ready to deploy real capital.

## Verifying it works

### Unit tests (no API access needed)

```bash
python -m unittest tests.test_occ_symbol -v
```

This validates the OCC symbol construction logic. All 21 tests should pass.

### Build the universe (requires sandbox token + ~1 minute)

```bash
python scripts/build_universe.py
```

Pulls all NASDAQ/NYSE listings, applies price ($20+), market cap ($2B+), and
average daily volume (500k+) filters, adds the major liquid ETFs, and writes
the result to `data/cache/universe_<YYYY-MM-DD>.json`. Should yield 800-1000
tickers depending on the day. Re-running on the same day is a no-op unless
`--force` is passed.

Override filters at the command line:

```bash
python scripts/build_universe.py --min-market-cap 5e9 --min-avg-volume 1000000
python scripts/build_universe.py --top 50            # show top 50 in summary
python scripts/build_universe.py --no-etfs           # equities only
```

### Build orders from candidates (requires today's candidates, ~30 sec)

```bash
python scripts/build_orders.py
```

Loads today's screener output, constructs put credit spread orders (with
spread width selected by underlying price: $5 wide below $300, $10 wide
above), and previews each one via Tradier. Saves results to
`data/cache/orders_<YYYY-MM-DD>.json` including the Tradier preview responses
(margin impact, commission estimate, validation status).

**Preview-only is hard-coded.** This script cannot place real orders. When
V8 (orchestrator) exists it will have an explicit paper/live switch.

```bash
python scripts/build_orders.py --top 10           # only top 10 candidates
python scripts/build_orders.py --no-preview-api   # skip Tradier, just print
```

### Run the screener (requires today's universe + ~5-20 minutes)

```bash
python scripts/screen.py
```

Loads today's universe snapshot and applies the strategy filters: target
expiration in 25-50 DTE, no earnings in the window, 20-delta short put with
tight bid-ask and decent open interest, $5-wide long put available, ATM IV
above 25%. Survivors are sorted by ATM IV descending and saved to
`data/cache/candidates_<YYYY-MM-DD>.json`.

This is the slow step. ~1100 universe tickers × 2-3 API calls each + a
yfinance earnings lookup per ticker = ~5-20 minutes depending on rate limits.
Run it pre-market.

Common overrides:

```bash
python scripts/screen.py --limit 50           # screen only first 50 tickers (quick smoke test)
python scripts/screen.py --no-earnings-filter # skip yfinance, much faster
python scripts/screen.py --no-iv-filter       # skip the ATM IV threshold
python scripts/screen.py --top 50             # show top 50 candidates in the table
```

### Smoke test (requires a working sandbox token)

```bash
python scripts/smoke_test.py
```

This walks through the full Tradier API surface in order:

1. Authenticates with your token
2. Reads account balances
3. Pulls a SPY quote
4. Lists upcoming SPY option expirations
5. Pulls a 30–45 DTE option chain with greeks
6. **Previews** (does not place) a put credit spread order

The order step uses Tradier's `preview=true` flag, which validates the order
without executing it. No real positions are opened by this script.

## Safety defaults

- `TradierConfig.sandbox` defaults to `True`. You must explicitly set it to
  `False` to talk to production.
- `place_multileg_order(preview=True)` is the default. You must explicitly pass
  `preview=False` to actually submit an order.
- `.env` is in `.gitignore`. Your tokens never enter version control.

## What's next

Future modules to add (in roughly this order):

1. ~~**Universe builder** — daily pull of liquid optionable equities/ETFs.~~ Done in V2.
2. ~~**Screener** — IV/earnings/liquidity filters, per-day ranking.~~ Done in V3.
3. ~~**Strategy** — order construction from candidates, target credit calculation,
   idempotency.~~ Done in V4.
4. ~~**Risk** — position sizing (2% per trade), concentration limits, buying
   power gates.~~ Done in V5.
5. ~~**Portfolio** — sync local position state against Tradier, compute P&L,
   decide exits (profit target / stop / time).~~ Done in V6.
6. **Backtest** — historical replay against saved chain snapshots. Requires
   a real options data source with historical IV (Polygon, ORATS, etc.).
   DEFERRED — paper trading serves the same validation purpose for free.
7. ~~**Orchestrator** — APScheduler runner, market-hours/holiday guard,
   three-way preview/paper/live mode switch with safety guardrails.~~ Done in V8.
8. ~~**Notifier** — Discord webhook for trade/error events + optional LLM
   advisory layer (flag-and-log, no veto authority yet).~~ Done in V9.

The bot is functionally complete. V7 (backtest) remains deferred until there's
a reason to pay for historical options data; paper trading validates the
strategy for free in the meantime.

### Promoting the LLM advisory from flag-to-veto (future)

The advisor currently only flags concerns — it never blocks a trade. After
you've run it for 30-60 trades and judged whether its flags are trustworthy,
you could promote it to actually veto specific event types (halts, M&A, FDA).
That's a deliberate, separate code change in `notify/advisor.py` and
`orchestrator/jobs.py` — it does not happen automatically.

## Running the bot

The autonomous entry point is `scripts/run_bot.py`. When started with no
arguments it runs a startup self-check (creates data dirs, verifies Tradier,
reports config) and then starts the scheduler, which runs the full daily cycle
on weekdays:

- **prep_job** at 09:00 ET — builds the universe and screens candidates
- **open_job** at 10:00 ET — places risk-sized opening spreads
- **manage_job** every 30 min, 10:00–16:00 ET — handles exits

Every placed open/close and every job run is recorded in the trade journal at
`data/journal/journal_<YYYY-MM>.jsonl`.

Trading mode is set via `BOT_MODE` (default preview_only):

```bash
# Run the full autonomous loop (preview-only, safe)
python scripts/run_bot.py

# Run a single job once and exit, for testing:
python scripts/run_bot.py --once prep      # build universe + candidates
python scripts/run_bot.py --once open      # place opening orders
python scripts/run_bot.py --once manage    # handle exits

# Paper trading (requires TRADIER_SANDBOX=true):
#   Windows PowerShell:
$env:BOT_MODE="paper"; python scripts/run_bot.py
```

**Live trading requires three independent settings to all agree** — a
deliberate safety mechanism:
- `BOT_MODE=live`
- `BOT_ALLOW_LIVE=YES_I_UNDERSTAND`
- `TRADIER_SANDBOX=false` (with production credentials)

Missing any one of these blocks live trading with a clear error. Do not enable
live mode until the strategy has proven itself on paper for months AND your
account is past the ~$25k viability threshold.
