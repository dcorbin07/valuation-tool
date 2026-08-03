# HANDOFF — forward paper track (roadmap #12)

Built 2026-08-02. Branch `worktree-paper-track`. All suites green: **343 tests** (123 edge, 32
screener, 28 engine, 28 lazy-prices, 23 calibration, 22 SaaS, 22 **new** paper-track, 20
options-greeks, 18 intraday, 14 bulk, 13 freeze).

## What this is

Roadmap #12, the project's #1 remaining validation. Every number in `BACKTEST_RESULTS.md` comes
from one 18-year Sharadar panel that has been looked at many times; the options edge comes from
one reconstructed alert history. A forward track starting today is the only thing that tests
either on data nobody had seen when the rules were fixed.

The pipeline agent built `record_outcome` and a paper book, but **nothing ever fed it marks**, so
it sat all-open and produced no closed trades. This wires the whole loop against Tradier's
sandbox, so the book now opens, marks and closes positions on its own.

## What places and marks orders

| File | Role |
|---|---|
| `valuation/edge/paper_broker.py` | **new.** Sandbox-only Tradier account client: quotes, option/equity orders, order status, positions, balances. |
| `valuation/edge/paper_track.py` | **new.** The cycle: submit → mark → close, plus the Index-vs-SPY book and the read model. |
| `scripts/paper_track_run.py` | **new.** Local CLI runner (`--health`, `--dry-run`, `--place-equity`). |
| `tests/test_paper_track.py` | **new.** 22 offline tests against a fake broker. |
| `valuation/intraday/providers.py` | `TradierProvider.__init__` takes optional `base`/`token`. Purely additive — passing neither reproduces the old constructor exactly. |
| `valuation/config.py` | `tradier_paper_token`, `tradier_paper_account_id`, `paper_contracts_per_trade`. |
| `valuation/saas/app_saas.py` | `POST /admin/run-paper-track` (X-Admin-Token). |
| `valuation/web/app.py` | `/api/track` now carries a `paper_sandbox` block. |

**Options book.** Every new scream-buy alert the app logs *with a real contract* (the
`options_live` work already resolves those) gets a paper `buy_to_open`, **limit at the ask**.
It is marked daily from the sandbox chain and closed on the alert's **own** exit policy — +100%
target / −50% stop / half-DTE time stop, read off the `features.exit_policy` the alert was
logged with — selling **limit at the bid**. Ask-in/bid-out is deliberate: it is
`options_fill.DEFAULT_AGGRESSION = 1.0`, the punishing convention every validated options number
in this repo is net of. Marking the forward book at the mid would beat the backtest for a reason
that has nothing to do with the signal.

The close calls the **existing** `options_tracker.record_outcome` with the paper fill. Nothing
here recomputes P&L, re-picks contracts, or duplicates the scorecard — `record_outcome` derives
P&L from the stored entry premium, so the forward scorecard cannot disagree with the prices the
alert was logged against. `/api/options-paper` (`options_paper.paper_report`) reads
`option_alerts` directly and therefore picks these closes up **with no change to that file**.

**Stock book.** The exported Valquo Index is held and marked from sandbox quotes, each name
against SPY over **its own window** — the identical construction `edge/track.py` uses for the
hot-list track, so the two records mean the same thing. Equity orders are opt-in
(`--place-equity` / `{"place_equity": true}`), off by default: the Index is a weights-and-returns
claim, and whole-share rounding on an 8%-capped book adds tracking error that tests nothing.

## The sandbox-only guard

`PaperBroker.__init__` fails loudly unless **all three** hold:

1. **The base URL is the sandbox host.** Parsed with `urlparse` and compared on hostname —
   not `"sandbox" in url`, which `https://api.tradier.com/v1?x=sandbox` would satisfy.
2. **The token is the dedicated paper token.** Empty → refuse. Equal to the production
   `TRADIER_TOKEN` → refuse. There is **no fallback** to the production token.
3. **Nothing in the module can reach production.** `_url()` rebuilds every request path from the
   base validated at construction; a caller cannot supply a host.

`TRADIER_ENV` / `TRADIER_TOKEN` are untouched and still point at the production feed the live app
reads — the two run side by side. `dry_run=True` sends Tradier's own `preview=true`, which runs
full broker-side order validation and creates nothing.

Four tests pin this: production URL, lookalike host, `http://`, empty string, crossed
credentials, and a missing paper token are each rejected.

## Daily cadence

Once a day, just after the close. The exit rules are daily-mark rules, so intraday runs would add
broker calls without adding information.

* **Render** (`render.yaml`): new `paper-track` cron, weekdays **20:45 UTC** (~4:45pm ET).
* **GitHub Actions** (`auto-scan.yml`): new `paper` job, weekdays **20:47 UTC**, also runnable
  from `workflow_dispatch` with kind `paper`.

Both **curl the same endpoint**; neither runs the cycle itself. That is deliberate: the alerts,
the paper order state and the index holdings all live in the web service's database on Render's
persistent disk. A GitHub runner gets an empty database every run — it would find no alerts,
submit nothing, and lose the state that makes the cycle idempotent. Both firing is harmless: the
cycle is idempotent (claim row per alert, PK on the day's index point).

**Idempotent and resumable.** `paper_option_orders.alert_id` is a PRIMARY KEY and every alert is
*claimed* before any order is sent, so two concurrent runs cannot both submit one alert. If a run
dies between placing and recording, the next run finds a claimed row with no order id and
**adopts** the live broker order for that contract rather than sending a second one. Tested.

**No back-filling.** Alerts older than `MAX_ALERT_AGE_DAYS = 3` are skipped with the reason
recorded. The track's only claim is that it was recorded before the outcome was known; buying a
three-week-old signal at today's price would quietly destroy that, and it is the easiest way to
fake this record. Tested.

## How to read the track

`GET /api/track` → `paper_sandbox`:

* `options.label` / `index.label` — e.g. `paper (Tradier sandbox), since 2026-08-02, thin - not
  yet a result`.
* `options.scorecard` — the existing expectancy scorecard (hit rate, avg win/loss, profit factor,
  expectancy), never hit rate alone.
* `index.index_ret` / `bench_ret` / `active_ret` — weight-averaged per-name return vs SPY over the
  same window, plus up to 260 days of history.
* `headline` — while thin, it says in words that **backtested expectancy remains the headline**.
* `data_caveat` — sandbox quotes are ~15 min delayed, so fills and marks are approximate.

Thresholds for "meaningful": **30 closed options trades** (`MIN_CLOSED_PER_BUCKET`, the same floor
the scorecard already refuses to tune below) and **126 days** of index history. Below either, the
track is an anecdote and says so. A name priced on only one leg is dropped from **both** legs of
the index, so a missing quote cannot manufacture alpha — tested.

Locally: `python scripts/paper_track_run.py --health` / `--dry-run`.

## Verified

Against the **real** sandbox account (~$199k paper cash), 2026-08-02:

* `--health` — reachable, balances read.
* Options leg end to end with a real contract (`AAPL260918C00310000`): live quote fetched, entry
  priced at the **ask** 12.30, target 24.60 / stop 6.15 / time stop 2026-08-26 (half of 47 DTE)
  computed correctly, and **Tradier previewed and accepted the order**.
* Index leg end to end: 3-name book seeded from live sandbox quotes, 3/3 priced, point written.
* `POST /admin/run-paper-track` end to end through the Flask test client: `configured: true`,
  health ok, both legs ran, no errors.
* 22 offline tests cover the guards, idempotency, resume-without-double-submit, ask/bid fills,
  exit precedence, both-legs-or-neither index pricing, and the honest labelling.

**Not verified:** a real (non-preview) order placement, and therefore a real fill → close →
`record_outcome` round trip on live sandbox data. The session's tooling blocked the actual
order-submission call, so placement was only exercised through Tradier's `preview=true`
validation and through the fake broker in tests. The code path is the same one `preview` runs;
the first scheduled run is what will confirm it. **Watch the first run's output.**

## Don — one thing to do

Add these to **Render → valuation-tool → Environment** (they are read server-side by the
endpoint, so they are *not* needed as GitHub Actions secrets):

```
TRADIER_PAPER_TOKEN        (from your Tradier sandbox account → API Access)
TRADIER_PAPER_ACCOUNT_ID   (the VA... number on that same Tradier page)
```

Both are already in your local `.env` and are declared `sync: false` in `render.yaml`. Until they
are set, `/admin/run-paper-track` answers `{"configured": false}` and does nothing — so the crons
are safe to land first.

## Next

1. **Watch the first scheduled run.** Confirm a real order places, fills, and closes through
   `record_outcome`. Until that round trip is seen, the track is wired but unproven.
2. **Seed the Index book from the real export**, not a smoke book:
   `python -m valuation.edge.valquo_index --full-universe --config taxable` first, then the runner
   picks up `data/valquo_index.json`.
3. **Rebalance is not automated.** `seed_book` adds new names and never resets an existing entry
   price; it does not sell names that leave the book. At the quarterly rebalance that has to be
   decided deliberately — a track that silently drops losers is worthless.
4. Sandbox fills can be optimistic on illiquid contracts. Once there are closed trades, compare
   the paper entry premium against the alert's logged `entry_premium` — a systematic gap is worth
   knowing about before the sample is quoted anywhere.
