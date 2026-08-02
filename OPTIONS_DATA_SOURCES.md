# OPTIONS_DATA_SOURCES.md — the orthogonal-data map for the scream-buy edge (2026-08)

The stock book is saturated at its ~2-month horizon. Options is **short-horizon (days)** — which is
exactly where new data can still create edge. This is the map of what to tap, free or paid, to build
a clean options edge — with the same honest discipline (pre-committed gate, held-out test, expectancy
scorecard) that validated the stock model.

## The one strategic move that matters most
**Get a *historical* options feed so we can BACKTEST options signals, not just archive-and-hope.**
ThetaData carries up to 8–12 years of per-contract prices/greeks/IV/**quotes**; Massive 4–5yr; ORATS to
2007. For a *short-horizon* signal ~4–8 years is plenty — it just has to span multiple vol regimes, and
the feed must carry **bid/ask quotes** so we can model the spread (options edges die on spread). That one
spend converts the options side from "run it live and pray" into "validate it like we validated stocks."
Do this first; everything else is a signal to test *through* it.

APIs > dashboards for us — we ingest programmatically, so favor sources with a real API.

---

## Tier 0 — the backtest-able feed (do this first)
| source | gives | history | cost | notes |
|---|---|---|---|---|
| **ThetaData** ⭐ | tick trades + quotes, OI, IV, 1st-order greeks, full chains (2nd/3rd-order + trade-greeks = Pro) | Value 1-min→2020 / **Standard tick→2016 (~10yr)** / Pro tick→2012 (~14yr) | free (30d EOD) → $40 Value (1-min) → **$80 Standard (tick, 2016, IV+1st-order greeks)** → $160 Pro (2012, all greeks + trade-greeks) | Best value for us. Standard = tick trades+quotes+IV+1st-order greeks to 2016; **compute gamma for GEX from IV** (Standard omits 2nd-order greeks). Cloud-direct via Python lib (no Terminal). |
| **Massive** (ex-Polygon.io) | trades, quotes, greeks, IV, OI; equity too | 2yr → 4yr → 5+yr | ~$29 Starter (2yr, **NO trades**) → ~$79 Developer (4yr + Trades) → ~$199 Advanced (5+yr, RT, **Quotes**) | Pure cloud REST, unified stocks+options. Quotes only at $199. |
| **Databento** | OPRA trades + NBBO (all 17 exchanges), OHLCV, greeks | 10+ yr | **pay-as-you-go** historical (no monthly min) / $199/mo Standard live | Best for a ONE-TIME bulk historical pull — pay for volume once, no subscription. |
| **ORATS** | IV surface, skew, IV rank/percentile, earnings-effect IV, term structure | to 2007 | contact (~mid-hundreds/mo) | Derivable from a raw feed for us. Skip unless we want their proprietary IV forecast. |
| **Tradier** (already wired) | live chains, IV, greeks | live only | have it | Covers LIVE signal generation for free; no deep history. |

**Pick:** **ThetaData Standard (~$80) — verified against the subscription page and the competitive field.
Lock it in.** Tick-level history back to **2016 (~10yr)** with trades, quotes, OI, IV and 1st-order
greeks. Model the **spread** from quotes (the #1 options-edge killer); DIY flow from trades; DIY GEX by
computing **gamma from IV** (Standard omits 2nd-order greeks, but gamma is a Black-Scholes function of the
IV it does give + a risk-free rate — pull that **free from FRED** (treasury curve + SOFR); **don't pay for
ThetaData's ~$30 interest-rate add-on**, and gamma is barely rate-sensitive for short-dated options anyway).

**Pro ($160) is NOT needed day one** — it only adds pre-computed higher-order/trade-greeks (we compute
those), 2012-vs-2016 history (2016 already spans 2018 / 2020 / 2022), 8-vs-4 concurrency, and the
full-firehose stream (we don't ingest the whole market). Upgrade to Pro later only if per-trade greeks
prove to sharpen the flow signal.

**Nothing beats Standard at ~$80:** EODHD has only ~2.5yr of options history, marketdata.app is shallow,
FlashAlpha is ~$239/mo, Intrinio is $1k+/mo, IVolatility is enterprise-priced, DeltaNeutral is EOD-only
flat files. ThetaData is the sweet spot — deepest history + tick granularity + full IV/greeks + cheapest,
cloud-direct via the Python library. **Alternatives if ever needed:** Databento pay-as-you-go for a
one-time bulk pull; Massive Developer for one cloud API across stocks+options. Skip ORATS/SpotGamma/UW
until a DIY signal proves out.

## Tier 1 — the orthogonal signal sources (what to test through the feed)
| source | edge it carries | cost | API? |
|---|---|---|---|
| **Unusual Whales** | options **flow** — sweeps, blocks, net premium, dark-pool prints, congressional | Platform (dashboard) $50/$75/$120 is **API-LESS**; **API = Whale Bundle from $149/mo; historical full-market trades $250/mo** | API only on bundle. Core flow is DIY-able from Massive Trades; unique = dark-pool + congressional (congressional is free elsewhere). |
| **SpotGamma** | **dealer gamma / GEX**, key levels, vanna — predicts pinning & volatility regime | $99/mo Essential / $299 Alpha (no free; free SPX GEX chart) | limited |
| **Ortex / S3** | **short-borrow fee & utilization** — squeeze setups (stronger than the short-interest ratio we already rejected) | Ortex ~$25–100/mo | yes |
| **IV skew / term structure** | put-call skew, front-vs-back IV — documented return predictor | via Polygon/ORATS (Tier 0) | — |

## Tier 2 — sentiment & catalyst (short-horizon, moves fast)
| source | edge | cost |
|---|---|---|
| **StockTwits API** | retail sentiment, message volume spikes | free-ish |
| **Reddit / WallStreetBets** | retail squeeze/mania detection | free (Reddit API) |
| **Benzinga Pro** | real-time news, squawk, rating/PT changes — catalysts | ~$99–199/mo |
| **Alpha Vantage news sentiment / GDELT** | news tone, event detection | free tiers |
| **Google Trends / Wikipedia views** | retail attention spikes | free |
| **Biotech FDA / catalyst calendars** | binary events (options love these) | BioPharmaCatalyst free-ish |
| **Earnings + expected move** | earnings straddles | we have earnings dates; expected move from IV |

## Tier 3 — free, start recording today (the compounding archive)
CBOE put/call ratios; VIX & VIX term structure; StockTwits/Reddit sentiment; GDELT news; Google
Trends; FINRA short interest (already pulled); SEC 8-K real-time (already have EDGAR). Snapshot these
every scan now — in months it's a proprietary point-in-time archive for signals we can't buy history for.

---

## Honest caveats (same discipline as the stock side)
- **Options flow is crowded.** Unusual-Whales-style flow is watched by everyone; expect it to be weak
  or already-priced. Test it, don't assume it.
- **Wide spreads eat edge.** Options bid/ask is far wider than stocks — a signal has to clear a much
  bigger cost hurdle. The expectancy scorecard already charges real entry/exit premiums.
- **Short horizon = more noise.** More signals will reject, not fewer.
- **Every source still clears the gate** — pre-committed, held-out (or forward, via the scorecard).
  The win is the one or two that survive, not the whole list.

## Budget-tiered recommendation
- **$0 (start now):** Tier 3 archive + Tradier we have. Learn forward via the scorecard. No backtest.
- **~$80/mo (recommended — the whole foundation):** **ThetaData Standard** alone. 8yr history + tick
  trades + **bid/ask quotes** + greeks/IV/OI. One feed covers backtest (with realistic spreads) + DIY
  flow + DIY GEX. (Or Databento pay-as-you-go for a one-time history pull; Massive Developer $79 if you
  want unified stocks+options in one cloud API.)
- **+$149–250/mo (only if flow proves out):** **Unusual Whales API** for curated flow + dark-pool +
  congressional. Defer until our DIY flow shows edge. (Congressional is free elsewhere.)
- **+$99–299/mo (defer):** **SpotGamma** — DIY GEX from the raw OI+greeks first.
- **Skip:** **ORATS** unless we want their proprietary IV forecast.

**My recommendation: ThetaData Standard (~$80/mo), one subscription** — 8yr backtest-able history WITH
quotes (so we can model the spread), tick trades (DIY flow), OI+greeks (DIY GEX). Only pay for Unusual
Whales / SpotGamma / ORATS if the DIY version proves a signal worth the polished one.
