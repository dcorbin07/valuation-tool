# Quant Trading System — Full Handoff for Claude Cowork

This document is a complete migration brief. It captures everything built across
multiple sessions so a fresh Claude (in Cowork) can take over with full context.
Read it end to end before touching anything. It covers: who the user is, the four
trading bots, the stock screener, the backtesting tools, the live deployment on
Oracle Cloud, every important design decision and gotcha, the honest caveats, and
the concrete open threads / next steps.

**Codename for continuity across chats: "porkbelly."** If the user says it, they're
referencing this project's history.

---

## 0. TL;DR — current state in five bullets

- **Four trading bots** (options, trend, momentum, mean-reversion) are **built,
  tested, and running live in SIM mode** on an Oracle Cloud free-tier VM. They
  wake on schedule each market day, make simulated decisions, and log equity
  curves. They survive reboots and restart on crash.
- **A separate stock screener** (value/quality/momentum/insider composite with
  Claude deep-dives) is **built and code-complete** but its live I/O layer is
  **not yet validated** and it is **not yet deployed**.
- **Backtesting**: a free options-strategy backtest (index proxy) is built. The
  user is about to buy the **Sharadar Core US Equities bundle** to enable proper
  survivorship-bias-free backtesting of the two stock bots + the screener.
- **The immediate next job** the user wants: wire in Sharadar-based backtesting +
  a (carefully overfitting-guarded) optimization layer, then redeploy.
- **Capital reality**: ~$4k liquid. Everything is SIM/paper. The honest framing
  (below) is that this is primarily a *learning + portfolio* project, not yet a
  live-money operation.

---

## 1. The user (Don / Donovan Corbin)

- Universal Banker at Atlantic Union Bank, Richmond VA. Physics degree (JMU).
  Google Data Analytics cert. Admitted to William & Mary MSF (starts Fall 2026).
  GitHub: **dcorbin07**. Windows machine, PowerShell.
- **Career context**: transitioning toward analytical finance / quant. This
  project doubles as a portfolio piece for the MSF and finance career.
- **How he works / what he values**: directness, honest probability assessments,
  evidence-based reasoning, and *pushback over agreement*. He explicitly wants to
  be told when an idea is wrong, when something isn't worth it, and when the data
  doesn't support a claim. Do NOT flatter or rubber-stamp. He appreciates being
  walked through *why*, not just *what*.
- **Skill level**: strong quantitative intuition, learning the finance and
  software specifics as he goes. Explain finance concepts when they come up. He
  can follow detailed technical reasoning but is not a professional developer —
  keep deployment steps explicit and one-at-a-time.
- **A recurring practical habit**: he sometimes deletes/re-extracts folders,
  which has wiped venvs and, once, test files. Assume local state can be lost;
  keep the repo/zip authoritative.

### Communication notes that matter
- He runs commands on the Oracle box via Oracle Cloud Shell (browser terminal).
  He has hit the SAME operational gotchas repeatedly — see §7. Always give
  commands **one at a time**, warn about the bracketed-paste issue, and remind
  him to **unzip from `~`** not from inside the project folder.
- Capital is ~$4k. Be honest that live trading any of this at that size is below
  the viability floor. Don't hype returns.

---

## 2. The big picture — what this system is

Four **independent, uncorrelated (or mildly-negatively-correlated) trading
strategies**, each running as its own bot, plus a **separate stock-idea
screener**, plus **backtesting/optimization tooling**. The eventual goal is an
**allocation overlay** that combines the four bots' returns using measured
correlations — but that's deferred until there's real data.

The design philosophy throughout: **each strategy is a separate "pod" with its
own simulated book**, so they can be measured independently. This is deliberate —
it's the prerequisite for ever combining them intelligently (you can't compute
allocation weights if the strategies' P&L is tangled in one account).

### The four edges (why they're distinct, not overlapping)
1. **Options bot** — sells put credit spreads. Edge = **volatility risk premium**
   (option buyers overpay for protection). Wins in calm/rising markets. Negatively
   skewed: many small wins, occasional big loss in a vol spike.
2. **Trend bot** — cross-asset time-series momentum (long what's rising, short
   what's falling across ~26 ETFs: stocks, bonds, gold, commodities). Edge =
   **trend-following / crisis alpha**. Wins in sustained moves and crashes; bleeds
   in choppy markets.
3. **Momentum bot** — cross-sectional relative momentum (long top-ranked stocks,
   short bottom, on 12-1 month ranking). Edge = **the momentum factor**. Vulnerable
   to "momentum crashes" at sharp market bottoms (junk rallies).
4. **Mean-reversion bot** — short-horizon reversal (buy oversold, short overbought
   on ~1-month z-score). Edge = **short-term overreaction**. Structurally the
   OPPOSITE of trend/momentum — thrives in chop when they get whipsawed. Has the
   worst left tail (the "falling knife that doesn't bounce").

**Key correlation insight** (the user asked about this specifically): mean-reversion
is *mildly* negatively correlated to trend/momentum (~-0.1 to -0.3 in returns),
NOT strongly negative. Strong negative (-0.8+) would be useless (cancels out).
Mild negative is the sweet spot — the strategies mostly earn independently, with a
slight tendency for one to do well when another struggles, so the blend is smoother.
IMPORTANT caveat: in a real crash, correlations across everything spike toward 1.0,
so diversification helps in *normal* bad patches, NOT systemic collapse.

---

## 3. Repository structure — `quant_bots/`

The monorepo. On the Oracle box it lives at `/home/ubuntu/quant_bots/`. Local
Windows path was `C:\Users\donni\Downloads\quant_bots` (varies).

```
quant_bots/
├── core/                      # shared infrastructure used by all bots
│   ├── tradier.py             # Tradier API client (equity + option orders, quotes,
│   │                          #   history, rate-limit handling, 429 backoff)
│   ├── calendar.py            # market calendar / trading-day logic (EASTERN tz)
│   ├── trading_mode.py        # PREVIEW_ONLY / SIM / PAPER / LIVE enum + guardrails,
│   │                          #   is_sim(), places_real_orders(), mode_from_env()
│   ├── journal.py             # TradeJournal — append-only JSONL trade/event log
│   ├── discord.py             # DiscordNotifier (send, send_embed, notify_job_result)
│   ├── account_state.py       # AccountState — daily P&L tracking for kill switch
│   ├── occ_symbol.py          # OCC option symbol construction
│   ├── universe_builder.py    # builds stock/ETF universe (include_etfs flag,
│   │                          #   filters: >$20, >$2B cap, >500k volume)
│   ├── sim_portfolio.py       # equity SimPortfolio/SimHolding (trend/momentum/reversion)
│   ├── sim_execution.py       # apply_orders_to_sim/finalize_sim/load_sim/sim_paths
│   ├── daily_summary.py       # end-of-day Discord digest (build_summaries, post_end_of_day)
│   ├── regime.py              # RegimeFilter — SPY vs 200-day MA → RISK_ON/RISK_OFF
│   └── backtest.py            # Backtester/BacktestConfig/PriceHistory for trend+momentum
│                              #   (Tradier-history based; superseded by Sharadar work — see §6)
├── trend/                     # Bot #2
│   ├── universe.py            # ~26 cross-asset ETFs
│   ├── signals.py             # time-series momentum + vol. NOW blends 3/6/12mo lookbacks
│   │                          #   (SignalConfig.momentum_lookback_days_list = (63,126,252))
│   ├── strategy.py            # inverse-vol target weights
│   ├── risk.py                # vol-targeting (10% target), gross/net/per-name caps,
│   │                          #   kill switch. NOTE: uses naive weighted-avg vol
│   │                          #   (ignores correlation → conservative, under-deploys)
│   ├── portfolio.py           # build_rebalance_plan (has current_override param for SIM)
│   └── orchestrator.py        # daily rebalance 10:30 ET, SIM-wired, per-bot state+journal
├── momentum/                  # Bot #3 — REUSES trend's risk + portfolio
│   ├── signals.py             # 12-1 cross-sectional ranking (skip recent 21d),
│   │                          #   long_count/short_count=30
│   ├── strategy.py            # inverse-vol
│   └── orchestrator.py        # rebalance 10:45 ET, SIM-wired, REGIME GATE (suppress
│                              #   shorts when SPY risk-on), per-bot state+journal
├── reversion/                 # Bot #4 (newest) — REUSES trend's risk + portfolio
│   ├── signals.py             # short-horizon z-score reversal (oversold long,
│   │                          #   overbought short), ma_window ~21d, min |z| 1.0
│   ├── strategy.py            # inverse-vol
│   └── orchestrator.py        # rebalance 11:00 ET, SIM-wired, REGIME GATE, per-bot state
├── options/                   # Bot #1 — self-contained put-credit-spread bot (168+ tests)
│   ├── broker/tradier.py      # its own Tradier client
│   ├── orchestrator/
│   │   ├── config.py          # own TradingMode enum (incl SIM), is_sim property
│   │   ├── jobs.py            # prep/open/manage jobs, SIM branches (open in sim book,
│   │   │                      #   _manage_job_sim prices legs + applies exits)
│   │   └── journal.py         # TradeJournal (record_open/record_close/record_job)
│   ├── strategy/strategy.py   # 20-delta short put, $5 width, 35 DTE (25-50), 0.95×mid
│   ├── portfolio/
│   │   ├── portfolio.py       # spread pairing, exit decisions
│   │   └── sim_portfolio.py   # OptionsSimPortfolio/SimSpread (spread-level sim)
│   ├── risk/risk.py           # 2% risk/trade, 10 concurrent, 1/ticker, ≤50% deployed,
│   │                          #   NOW vol-scaled sizing (smaller at extreme IV)
│   ├── screener/              # candidate screener (find spreads) — config has the
│   │                          #   delta/DTE/credit targets
│   ├── notify/advisor.py      # LLM advisory (flag-and-log binary-event check via
│   │                          #   Claude + web_search; ADVISORY_MODEL configurable)
│   └── scripts/run_bot.py     # entry point (reads parent quant_bots/.env too)
├── scripts/                   # runner + analysis scripts
│   ├── run_trend_bot.py
│   ├── run_momentum_bot.py
│   ├── run_reversion_bot.py
│   ├── correlation_tracker.py # reads all bots' sim curves → returns/vol/Sharpe +
│   │                          #   correlation matrix. Warns on <20 overlapping days
│   │                          #   AND on non-overlapping date ranges (backtest-vs-live guard)
│   ├── weekly_report.py       # writes self-explanatory data/reports/correlation_*.md
│   │                          #   (human-readable + raw JSON for uploading to Claude)
│   ├── end_of_day_summary.py  # posts the daily Discord digest
│   └── run_backtest.py        # trend+momentum backtest over Tradier history (single
│                              #   shared window; superseded by Sharadar plan)
├── deploy/                    # systemd units + one-command installer
│   ├── trend-bot.service, momentum-bot.service, options-bot.service,
│   │   reversion-bot.service
│   ├── daily-summary.service + .timer   (Mon-Fri 21:30 UTC — after close in EST+EDT)
│   ├── weekly-report.service + .timer   (Sun 17:00 UTC)
│   ├── install_services.sh    # copies units, daemon-reload, enable+start all 4 bots
│   │                          #   + both timers. SAFE TO RE-RUN. One command rebuild.
│   └── README.md
├── tests/                     # 82 tests (core + trend + momentum + reversion + sim +
│                              #   daily_summary). options/ has its own 172.
├── requirements.txt           # requests, python-dotenv, apscheduler, anthropic (optional)
├── .env.example               # combined template for all 4 bots (see §5)
└── README.md
```

**Test counts (verify these after any change):**
- Monorepo: `cd quant_bots && python -m unittest discover tests` → **82 tests**
- Options: `cd quant_bots/options && python -m unittest discover` → **172 tests**

If you see 77/168 or 73/159, an OLD version is present — the current build is 82/172.

---

## 4. The exact strategies (as the CODE defines them — simulate these, not templates)

### Bot #1 — Options (put credit spreads)
- **Entry**: sell the ~**0.20-delta** put, buy the put **$5 below** (fixed $5 width),
  target **35 DTE** (accept 25-50). Take credit at **0.95 × mid**. Skip if credit
  < **$0.20**. Skip any name with **earnings before expiration**.
- **Exits** (whichever first): **50% profit** / **2× credit stop** / **21-DTE** time
  exit / expiration.
- **Sizing**: risk **~2%** of account per trade, **max 10 concurrent**, **1 per
  ticker**, **≤50% deployed**. NOW also **vol-scaled**: shrink size toward a 40%
  floor as ATM IV rises past 40% toward 100%+ (extreme IV = likely priced binary
  event; pull capital toward cleaner premium).
- **Universe**: liquid names (>$20, >$2B cap, >500k vol) + major ETFs.

### Bot #2 — Trend (cross-asset time-series momentum)
- ~26 ETFs. Signal = trailing return, now **blended across 3/6/12-month** lookbacks
  (was single 12mo). Long positive-trend, short negative-trend. Inverse-vol weights.
- Risk: **vol-target 10%**, gross/net/per-name caps, kill switch. Rebalance **10:30 ET**.
- NOTE: the regime gate is deliberately **NOT** applied here (see §8, decision #2).

### Bot #3 — Momentum (cross-sectional)
- Stock universe (ETFs off). **12-1 month** ranking (skip most recent 21 days).
  Long top **30**, short bottom **30**. Inverse-vol. Reuses trend's risk+portfolio.
- **REGIME GATE**: suppresses shorts when SPY is above its 200-day MA (avoid shorting
  into a rising market). Rebalance **10:45 ET**.

### Bot #4 — Mean-reversion (short-horizon)
- Stock universe. **z-score** of price vs recent ~21-day mean. Buy most oversold
  (neg z), short most overbought (pos z). Only act on |z| ≥ 1.0. Long/short 20 each.
  Inverse-vol. Reuses trend's risk+portfolio.
- **REGIME GATE** (same as momentum). Rebalance **11:00 ET**.
- Risk controlled by **breadth (many small names), NOT tight stops** — evidence is
  clear that stops HURT mean-reversion. Do not add stops here.

**Staggered timing is intentional** (10:30/10:45/11:00, options prep 9am/open 10am/
manage every 30min) — spreads Tradier API load instead of hammering it at once.

---

## 5. Configuration & secrets (.env)

**ONE combined `.env` at `quant_bots/.env` serves all four bots.** The options bot
reads the parent `.env` too. For the **SIM pilot**, the same Tradier **sandbox**
token/account can go in every field (SIM only needs quotes). `.env.example` is the
template. Structure:

```
# Bot #1 Options
TRADIER_TOKEN= / TRADIER_ACCOUNT_ID= / TRADIER_SANDBOX=true
ANTHROPIC_API_KEY=          # optional — enables options advisor (flag-and-log only)
ADVISORY_MODEL=             # optional — defaults to claude-sonnet-4-6
# Bot #2 Trend
TREND_TRADIER_TOKEN= / TREND_TRADIER_ACCOUNT_ID= / TREND_TRADIER_SANDBOX=true
# Bot #3 Momentum
MOMENTUM_TRADIER_TOKEN= / MOMENTUM_TRADIER_ACCOUNT_ID= / MOMENTUM_TRADIER_SANDBOX=true
# Bot #4 Mean-reversion (falls back to shared TRADIER_TOKEN if blank — SIM-safe)
REVERSION_TRADIER_TOKEN= / REVERSION_TRADIER_ACCOUNT_ID= / REVERSION_TRADIER_SANDBOX=true
# Shared
DISCORD_WEBHOOK_URL=        # blank = log instead of send
BOT_MODE=sim                # preview_only | sim | paper | live
# BOT_ALLOW_LIVE=YES_I_UNDERSTAND   # only for real live
```

**CRITICAL SECURITY**: `.env` NEVER goes in a zip, repo, or anywhere shared. All
zips exclude it (`-x '*/.env'`). The GitHub repos have a `.gitignore` excluding it.
`.env.example` (blank template) is safe and SHOULD be shared. A leaked Anthropic or
Tradier key is real money / real account exposure — a leaked key must be rotated
immediately. The user knows this; reinforce it.

**Model strings** (verified current as of this project): `claude-opus-4-8` ($5/$25
per MTok), `claude-sonnet-4-6` ($3/$15 per MTok). Use versioned strings, never
aliases, in production.

---

## 6. Backtesting — what exists and the Sharadar plan (THE ACTIVE NEXT JOB)

### What exists now
1. **`quant_bots/scripts/run_backtest.py`** — replays trend + momentum over Tradier
   daily history, single shared window, writes `<bot>_backtest` curves in SIM format
   so `correlation_tracker.py` reads them unchanged. **Limitation**: Tradier history
   is only a few years and has **survivorship bias** (uses today's universe). Good
   for a rough two-way trend/momentum correlation, not for precise returns.

2. **Standalone options backtest** (`options_backtest.zip`) — an honest, free,
   **index-ETF-proxy** backtest of the options strategy. Key points:
   - Uses **Black-Scholes** to find the 20-delta strike and reprice spreads daily.
   - Uses **real historical implied vol from the VIX family** (VIX→SPY, VXN→QQQ,
     RVX→IWM) — because the edge IS the implied-vs-realized vol gap, so you must NOT
     substitute realized vol (that bakes in zero premium by construction).
   - Models **conservative slippage + commissions + STOP GAP-THROUGH** (a 2× stop
     doesn't fill at 2× in a vol spike — it gaps through; naive backtests cap the
     loss and lie about the exact tail that matters).
   - Fetches free data from **stooq.com** (needs internet; won't run in a sandbox).
   - **Honest limitation**: only tests the index ETFs. It does NOT test single stocks
     (their historical IV isn't free). A pass is NECESSARY but not SUFFICIENT for the
     single-stock names. And it does nothing for the options bot's stock universe.
   - Run: `pip install requests; python run_options_backtest.py --etf SPY --start
     2018-01-01 --end 2025-12-31` (then QQQ, IWM).

### The Sharadar plan (what the user is buying and wants wired in)
The user is purchasing the **Sharadar Core US Equities Bundle** (Nasdaq Data Link /
data.nasdaq.com/databases/SFA, from ~$79/mo). It contains five Sharadar products:
Core US Fundamentals (SF1), Institutional Investors (SF3), Core US Insiders (SF2),
Equity Prices (SEP), Fund Prices (SFP), plus Actions/Tickers/Metrics/Events. History
back to ~1998. 21,000+ companies, 7,000 funds, 10,000 investors. Daily delivery.

**What it unlocks (be precise with the user):**
- **Survivorship-bias-free backtesting** for the **momentum and reversion bots** —
  includes delisted companies, so the historical universe is real. This is the big
  fix over the Tradier approach.
- **Point-in-time fundamentals (SF1)** — enables backtesting the **screener's** value/
  quality scoring WITHOUT look-ahead bias (Sharadar timestamps when data was known).
- **Insider data (SF2)** — feeds the screener's insider-quality score; can validate
  whether insider buying predicted returns.
- **Deep multi-cycle history** (dot-com, 2008, 2020, 2022).

**What it does NOT unlock (SAY THIS CLEARLY):**
- **NO historical options implied vol.** It's an *equities* bundle. The **options
  bot still cannot be backtested** with it — it stays on the VIX-family index proxy,
  or needs a separate expensive options-data sub (ORATS/LiveVol). If the user's goal
  were the options bot, this would be the wrong purchase. It's right for the STOCK
  bots + SCREENER.

**The build plan the user approved (do this next):**
1. **Sharadar data adapter** — module to fetch/read the bundle (via Nasdaq Data Link
   API with the user's key, or bulk CSV) and serve **point-in-time** price +
   fundamental slices, matching how the existing backtest engines consume data.
2. **Rewire momentum/reversion backtest** to pull from Sharadar (survivorship-free)
   instead of Tradier.
3. **Build a screener backtest** (NEW capability) — replay the screener's scoring over
   history using PIT SF1 + SF2, measure whether top-ranked names actually outperformed.
   The screener already has a `backtest_engine.py` stub to build on.
4. **Optimization layer** — sweep key params (lookbacks, delta targets, score weights)
   over history, **with strict overfitting guards: walk-forward / out-of-sample
   validation.** See the warning below.
5. **Combine with paper/SIM data** — backtest = what worked historically; live SIM =
   what's executing now. Keep them METHODOLOGICALLY SEPARATE (never correlate across
   the two — the tracker already warns on this). Use both to decide what to redeploy.

**⚠️ THE OVERFITTING WARNING — the single most dangerous phase.** The moment there's
rich historical data + an optimizer, the temptation is to tune parameters until the
backtest looks amazing — which is EXACTLY how people build strategies that crush
history and lose money live. Build optimization with walk-forward/out-of-sample
discipline baked in from the start. Be the voice that pushes back when a result looks
too good. The user was explicitly warned and agreed. Hold that line.


---

## 7. Live deployment — Oracle Cloud (all four bots running in SIM)

### The box
- **Provider**: Oracle Cloud Infrastructure, **Always Free** tier.
- **Instance**: `quant-bots`, Ubuntu 24.04, shape **VM.Standard.E2.1.Micro**
  (1 OCPU, 1GB RAM — free-eligible).
- **Public IP**: `141.148.45.115` (ephemeral, tied to the instance; changes only if
  the instance is terminated/recreated).
- **SSH key**: `~/ssh-key-2026-05-29.key` (private key, 2KB, `chmod 600`). Lives in
  the user's Oracle Cloud Shell home dir (and downloaded locally at
  `C:\Users\donni\Downloads\oracle_keys\`).
- **The $2/mo "estimate"** shown at creation is boot-volume list price, covered by
  the 200GB free block-storage allowance → actual cost ~$0.
- Default user: `ubuntu`. Project at `/home/ubuntu/quant_bots/`. Shared venv at
  `/home/ubuntu/quant_bots/venv/`.

### How the user connects
Oracle Cloud Shell (browser terminal at cloud.oracle.com, the `>_` icon), then:
```
ssh -i ~/ssh-key-2026-05-29.key ubuntu@141.148.45.115
```

### What's running
All four bots as **systemd services** (start on boot, restart on crash), in SIM mode.
Plus two **systemd timers**: daily-summary (Mon-Fri 21:30 UTC) and weekly-report
(Sun 17:00 UTC). Managed by `deploy/install_services.sh` (one command, safe to re-run).

### Deploy / redeploy sequence (the user knows this flow but it's error-prone)
1. On Windows: delete old `quant_bots*.zip` from Downloads, download the fresh one.
   **Verify size** (~225KB — a 7MB file is the wrong one with a stray venv).
2. Cloud Shell: `rm -f ~/quant_bots.zip`, then Upload via the Cloud Shell menu,
   then `ls -la ~/quant_bots.zip` to confirm size.
3. `scp -i ~/ssh-key-2026-05-29.key ~/quant_bots.zip ubuntu@141.148.45.115:~/`
4. `ssh -i ~/ssh-key-2026-05-29.key ubuntu@141.148.45.115`
5. On box: `bind 'set enable-bracketed-paste off'` (type by hand)
6. `sudo systemctl stop trend-bot momentum-bot options-bot reversion-bot`
7. `cd ~` then `unzip -o ~/quant_bots.zip`  **← unzip from HOME, never from inside
   quant_bots/ (nests as quant_bots/quant_bots/)**
8. `cd ~/quant_bots && source venv/bin/activate && pip install -r requirements.txt`
9. `python -m unittest discover tests` (want **82**), `cd options && python -m
   unittest discover` (want **172**), `cd ..`
10. `cat .env` to confirm secrets survived (they're not in the zip, so unzip -o
    doesn't touch them)
11. `bash deploy/install_services.sh`  (installs/enables/starts all 4 bots + timers)
12. `systemctl is-active trend-bot momentum-bot options-bot reversion-bot` (want 4×
    `active`), then `tail -n 8 ~/quant_bots/<bot>_service.log` to confirm clean start.

### Checking status / pulling results
- Alive? `systemctl is-active trend-bot momentum-bot options-bot reversion-bot`
- **The payoff** — correlations: `cd ~/quant_bots && source venv/bin/activate &&
  python scripts/correlation_tracker.py --bots trend momentum options reversion`
- Days of data per bot: `for b in trend momentum options reversion; do echo -n
  "$b: "; wc -l < ~/quant_bots/data/sim/$b/equity_curve.jsonl 2>/dev/null || echo
  none; done`
- Weekly report file: `cat ~/quant_bots/data/reports/correlation_<date>.md`
- Logs: `tail -n 20 ~/quant_bots/<bot>_service.log`

### To rebuild the box from scratch (if it ever dies)
Get code onto box → `cd ~/quant_bots && python3 -m venv venv && source venv/bin/
activate && pip install -r requirements.txt` → create `.env` with keys →
`bash deploy/install_services.sh`. That's the whole deployment.

---

## 8. Key design decisions & why (do NOT undo these without cause)

1. **Pure SIM mode = fills assumed at quoted mid, real quotes for marking.** Sidesteps
   the flaky Tradier sandbox fills (which gave ~1-in-5 fills live). Each bot tracks
   its own book in `data/sim/<bot>/` (portfolio.json + equity_curve.jsonl, identical
   format across all four so the tracker/summary work unchanged). This is how pod
   shops measure separate strategy pods without separate broker accounts.

2. **Regime gate is on momentum + reversion, NOT trend.** The stock bots short
   individual names, and shorting into a broad rally is their worst case → the SPY-vs-
   200d gate helps. But the TREND bot holds bonds/gold/commodities and responds to
   each instrument's OWN trend; gating it on SPY would suppress exactly the non-equity
   crisis-alpha positions you want when stocks fall. A broad-equity gate there would
   HURT. This was a deliberate, evidence-based call — don't "fix" it by adding the gate.

3. **No tight stop-losses anywhere.** Evidence shows stops don't add value in mean-
   reversion OR trend-following. The defined-risk structures (options long put, vol-
   targeting) are the right controls. Do not bolt on stops.

4. **Each bot has SEPARATE credentials, no shared fallback** (except reversion falls
   back to the shared TRADIER_TOKEN for SIM convenience). Each has its own _SANDBOX
   flag. Unconfigured bot exits cleanly (code 0).

5. **Per-bot state files + per-bot journals.** (Bug fixed this session — see §9.) The
   three equity bots each have their own `data/state/<bot>_account_state.json` and
   `data/journal/<bot>/`. Never share these across bots.

6. **The allocation overlay (combining all 4) is DEFERRED.** It needs real correlation
   data, which needs months of SIM. Building it now = fitting to noise. It's a thin
   layer ABOVE the bots (risk-parity weights from measured vol/correlation), built LAST.

7. **Diversification reduces VOLATILITY, not TAIL RISK, and does NOT lower the capital
   floor.** The combined system needs MORE total capital (~$50-100k to run properly),
   not less. Minimum is set by cost/granularity, not smoothness. Trend has the lowest
   single-bot floor (~$3-5k, ETF-based); options ~$10-25k; momentum/reversion ~$25k+
   each (breadth-dependent + shorting).

8. **Never correlate a backtest curve against a live-SIM curve** (different timeframes).
   The tracker warns on <20 overlapping days AND on non-overlapping date ranges.

---

## 9. Bugs found & fixed this session (so you know the history)

1. **Options SIM unit bug** — first options SIM test showed a -$31,792 "loss" that
   should've been a profit. Cause: per-share vs per-spread-dollar unit mismatch
   (credit stored per-share, close cost computed per-spread-dollar). Fixed throughout
   OptionsSimPortfolio; verified a half-credit close → small profit and a deep-profit
   mark → fires close_profit. **Lesson: this is exactly why we test — a silent unit
   bug would have corrupted correlation data.**
2. **Kill switch dead in SIM** — the kill switch read daily P&L from the real broker
   account (which barely moves in SIM), not each bot's simulated book. Fixed: in SIM,
   account_state is now built from the SIM equity, so the kill switch actually watches
   the right account. Verified it fires on a simulated -6% day.
3. **Shared state/journal clobbering** — all three equity bots wrote to ONE
   account_state.json and ONE journal dir, stomping each other. Fixed: per-bot files.
4. **Stale Opus pricing in screener** — cost guard had Opus at $15/$75 (3× too high;
   real is $5/$25). Fixed the rate + the EST_COST_PER_DIVE estimate ($0.30 → $0.12).
   (Conservative error — it over-estimated spend, so it was safe but wrong.)

---

## 10. The screener — separate system (`screener.zip`)

A **daily stock-screening pipeline** (NOT a trading bot — it surfaces ideas for the
user to research). ~1,300+ lines. Ranks small/mid-cap stocks on a composite of
value / quality / momentum / insider signals, deep-dives NEW top names with Claude
(Opus + web search), and posts to Discord.

### Structure
```
screener/
├── config.py           # ALL knobs centralized: model strings, evidence-based score
│                        #   weights, cost guard, universe filters, DTE/delta targets
│                        #   (min_dte 25, max_dte 50, target_dte 35, target_short_delta
│                        #   0.20, min_atm_iv 0.25), risk (2%/10 concurrent)
├── scoring.py          # THE BRAIN — sub-scores + composite. Two buckets:
│                        #   "established" (value/quality/momentum/insider) and
│                        #   "speculative" (value/growth/momentum/insider). Insider
│                        #   score: log-scaled size, role weighting, clustering bonus,
│                        #   tanh squash. Neutral fallbacks when data missing. TESTED.
├── decisions.py        # decision logic + COST GUARD ($5/day breaker on Claude spend)
├── store.py            # persistence (which names already deep-dived, etc.)
├── edgar.py            # SEC EDGAR filings fetch          ⏳ needs live validation
├── prices.py           # price feed                        ⏳ needs live validation
├── claude_analyst.py   # Claude deep-dive calls (Opus)     ⏳ needs live validation
├── discord_alerts.py   # Discord posting                   ⏳ needs live validation
├── pipeline.py         # orchestrates the daily run        ⏳ needs live validation
├── cross_sectional.py  # (newer) cross-sectional ranking
├── insider_poller.py   # (newer) insider polling
├── pit_data.py         # (newer) point-in-time data handling
├── backtest_engine.py  # (newer) STUB to build the screener backtest on (Sharadar)
├── run_backtest.py     # (newer) backtest runner stub
└── requirements.txt    # anthropic, requests, pandas, numpy, python-dotenv
```

### Status
- The 4 "brain" modules (config, scoring, decisions, store) are built + were verified
  working (scoring produces sane buckets/composites; junk gates out; cost guard intact).
- The **I/O layer is code-complete but NOT live-validated** (EDGAR, prices, Claude,
  Discord, pipeline) — can't test without network. First real run WILL surface wiring
  issues; deploy expecting to debug it, not expecting flawless first run.
- **NOT deployed yet.** When deployed it'd be its own systemd service + its own `.env`
  (it NEEDS ANTHROPIC_API_KEY — deep-dives are core, not optional) + own daily schedule.
- **It costs real money** (~$0.12/dive, capped $5/day) — ~$10-30/mo. Unlike the SIM
  bots (free), this has an ongoing bill. Honest "is it worth it" call for the user.
- **Test files were NOT in the uploaded zips** — the user deleted them locally. Offer
  to write a fresh test suite for scoring/decisions/store (the code is well-understood).

---

## 11. Honest assessment — is any of this worth it? (the user asked; hold this line)

Told to the user directly and he accepted it:

- **At ~$4k in a taxable account, as a pure wealth play, buy-and-hold S&P 500 is
  very likely the better choice.** Active strategies trade frequently → mostly
  SHORT-TERM cap gains (taxed ~28-30% for him: ordinary income + VA state), vs
  buy-and-hold deferring tax for decades then paying ~15% long-term. The tax drag
  roughly DOUBLES against the active approach. Plus ~80-90% of professional active
  managers underperform their benchmark over 15 years. The honest prior is that these
  bots, at retail scale, are MORE likely to underperform the S&P than beat it.
- **What this project IS genuinely worth**: (a) deep practical education in quant
  finance, risk, and deployment — directly relevant to his MSF/career; (b) a portfolio
  piece; (c) an OPTION — a ready system for a small uncorrelated sleeve alongside a
  passive core, ideally in a Roth (which erases the short-term-gains problem).
- The sound framing: majority in low-cost index funds in tax-advantaged accounts as
  the real wealth engine; the four-bot system as a small experimental sleeve + skills
  asset, sized so underperformance doesn't matter much. Don't let him conflate "better
  investment than the index" (probably not) with "becoming someone who understands
  markets deeply" (absolutely).

### On leverage (he asked about levering the combined blend)
- Volatility drag (variance drain): geometric return ≈ arithmetic − vol²/2. Leverage
  L multiplies arithmetic return by L but drag by L². There's a growth-optimal L*
  ≈ excess_return / vol² (~2x in theory for the blend) — but the PRACTICAL sweet spot
  is a FRACTION of that (~1.2-1.3x), because: the curve is flat near the top but the
  downside is steep; L* is computed from ESTIMATED inputs that are wrong (crisis vol
  is always higher); and L* ignores ruin/path. Over 10-30yr horizons, UNLEVERED (or
  ~1.2x) wins because longer horizons GUARANTEE you meet the bad tail, and one deep
  levered drawdown permanently impairs compounding + risks ruin. Leverage must be
  DYNAMIC (scale down as vol rises) if used at all. Don't let him lever significantly
  on the theory that "a crash isn't near" — that's the exact false-security that wipes
  people out (crashes cluster; second legs are common).

---

## 12. GitHub state

- User is uploading both repos via the **GitHub website** (drag-and-drop, NOT the
  desktop app / CLI — he finds those confusing). Same method he used for a DCF model.
- `quant_bots` → `github.com/dcorbin07/quant_bots` (was being uploaded; needed to
  verify `.env.example` present, no plain `.env`, folders intact). Likely **private**
  to start, flip to public later.
- `screener` → its own repo, same method, not yet done.
- Website-upload gotcha: drag the folder's CONTENTS (or the folder — GitHub preserves
  structure) but NEVER a real `.env`. Windows shows dotfiles as "hidden" — that's
  cosmetic; `.env.example` still uploads and GitHub shows it in the repo list. Empty
  `data/` folder won't upload (git ignores empty dirs) — that's correct.
- Each repo has a `.gitignore` excluding `.env`, `__pycache__`, `data/` runtime dirs,
  logs, `*.db`. (The `.gitignore` does nothing during website upload — it matters only
  if he later uses git CLI.)

---

## 13. Open threads / immediate next steps (priority order)

1. **[ACTIVE] Wire in Sharadar backtesting + optimization** once the user has the
   bundle + API key. See §6 for the full plan. Start with the data adapter. HOLD THE
   OVERFITTING LINE (§6 warning).
2. **Run the options index-proxy backtest** (SPY/QQQ/IWM) and interpret — does the
   variance premium survive costs + stress? Already built; just needs running.
3. **Check on the live SIM data** — pull the correlation tracker (§7). If <20
   overlapping days, correlations aren't meaningful yet; that's expected, not a bug.
4. **Deploy the screener** (if the user decides the ~$20/mo is worth it) — own service,
   own `.env` with ANTHROPIC_API_KEY, own schedule. Expect to debug the live I/O.
5. **Write fresh screener test files** (user deleted the originals; not in the zips).
6. **Finish the GitHub uploads** (screener repo; verify quant_bots repo is clean).
7. **[LATER] Build the allocation overlay** — only after ~1-2 months of real SIM data.
8. **[COSMETIC] Tradier sandbox** has a leftover SLV put credit spread from an early
   real-order test. Doesn't affect the SIM bots (they only pull quotes). Close it
   during market hours (buy-to-close the short $61 put, sell-to-close the long $56 put;
   use limit orders or wait for regular hours — market orders reject postmarket) if he
   wants clean Discord numbers, or ignore it.

---

## 14. Working style reminders for Cowork

- **Be honest and push back.** The user explicitly values this. Tell him when an idea
  is wrong, redundant, or not worth it. Several times this session the right answer was
  "don't build that" (covered calls = correlated duplicate; vol selling = catastrophic
  tail; more bots now = diversification theater; optimize-now = overfitting risk).
- **Test before trusting.** Every non-trivial change gets tests. The unit bug that
  would have silently corrupted data was caught precisely because we tested.
- **Explain the finance.** He's learning; the "why" matters as much as the "what."
- **Deployment: one command at a time, warn about the paste/unzip gotchas** (§7).
- **Keep the repo/zip authoritative** — local state can be lost.
- **Never put secrets in anything shared.** Reinforce the `.env` discipline.
- **The highest-value input right now is TIME + DATA, not more code.** The bots need
  to accumulate SIM data before correlations/allocation mean anything. Don't
  over-build; the system is mature. The Sharadar work is the one genuinely additive
  new thing on the table.

---

## 15. File manifest (what's in this handoff / in outputs)

- `quant_bots.zip` — the four-bot monorepo, current (82/172 tests). Deploy target.
- `screener.zip` — the stock screener, current (Opus pricing fixed). Not yet deployed.
- `options_backtest.zip` — standalone options index-proxy backtest (run locally).
- `options_bot.zip` — standalone copy of just the options bot (kept synced with the
  monorepo's options/ — historical; the monorepo is authoritative).
- `HANDOFF.md` — this document.

**End of handoff. Everything above reflects the state at migration time. When in
doubt, the code in the zips is authoritative over any summary here.**
