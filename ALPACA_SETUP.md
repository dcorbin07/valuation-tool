# Replacing Tradier's market data — what Don does, and what happens after

**Nothing is switched to Alpaca until you have seen the numbers.** This file is the setup Don
does himself, plus exactly what gets measured once the key exists. No lane ever sees a key.

## Why Alpaca, and why not Robinhood

**Robinhood is not an option, and this is a fact about their API rather than a preference.** Its
official developer API is **crypto-only** — there is no official market-data API for US equities
or options. The routes people use for stock data are unofficial clients that log in as you with
your username, password and MFA, and **this project never stores Don's login for anything**; it
would also put a brokerage account with real money behind a scraped session. So it is out.

**Alpaca's free tier is the candidate** because it gives, at no cost and with a key Don owns:

- real-time **IEX** stock quotes and bars (IEX only — see the honest limit below);
- an **indicative** options feed with chains, and greeks/IV;
- **paper trading**, which is what the fleet books need;
- documented rate limits (200 requests/minute on the free plan) rather than discovered ones.

## What Don does — four steps, about five minutes

1. Go to **alpaca.markets** and create a free account. **Do not fund it.** Nothing here needs a
   funded account, and the Tradier lesson is that a market-data entitlement can die with the
   brokerage relationship — a key on an unfunded paper account cannot be killed that way.
2. In the dashboard, switch to **Paper Trading**, then **generate an API key**. You get two
   strings: a **Key ID** and a **Secret Key**. The secret is shown **once** — copy both now.
3. Put them in GitHub, under **exactly** these names:
   *GitHub → the repo → Settings → Secrets and variables → Actions → New repository secret.*
   | Secret name | What goes in it |
   |---|---|
   | `ALPACA_PAPER_KEY_ID` | the Key ID |
   | `ALPACA_PAPER_SECRET_KEY` | the Secret Key |
4. Put the same two in Render, under the same names:
   *Render → the valquo service → Environment → Add environment variable → Save.* Render
   restarts the service by itself.

**The names matter, AND THEY CHANGED ON 2026-10-14 (item 58).** They are now
`ALPACA_PAPER_KEY_ID` and `ALPACA_PAPER_SECRET_KEY` — with `PAPER_` in them — because a second
set of slots now exists for the real-money §8 path (`ALPACA_ACCOUNT_<n>_KEY_ID` and
`ALPACA_ACCOUNT_<n>_SECRET_KEY`), and two credentials one word apart with no word saying which
is which is how a live key comes to serve a paper book. `valuation/config.py` reads exactly
`ALPACA_PAPER_KEY_ID` and `ALPACA_PAPER_SECRET_KEY`; a secret called `ALPACA_API_KEY` is a secret nothing reads, and that
failure looks identical to a dead key. **Nothing else needs setting** — no base URL, no env
flag. Paper vs live is chosen in code, and this project only ever uses the paper/data host.

**Never paste a key into chat, a prompt file, or a commit.** If one ever does get pasted
anywhere, regenerate it in the Alpaca dashboard — that invalidates the old one — and nothing
else needs doing.

## What happens next, and in what order

Once both secrets exist, a lane runs the seam measurement **the same way the FMP seam was
measured** (`FMP_SEAM.md`), on the **same stated 222-name sample** — banks, REITs, utilities,
ADRs and recent splitters — so the three vendors are comparable on one population rather than
three convenient ones:

1. **Bars.** Daily closes against the recorded series and against yfinance: agreement rate,
   the worst disagreements by name, and whether closes are as-traded or adjusted (the
   split-trap question that cost items 36 and 39).
2. **The 52-week high on each basis**, which is the number the Dip Detector is about.
3. **Option chains**: coverage, and whether IV and greeks are present per contract.
4. **Coverage on the 222**, reported as a share of names AND of the hot-list universe — item
   40's FMP measurement died on coverage (~12%, zero REITs, zero utilities), so this is the
   leg most likely to decide it.
5. **Rate limits**, read from the response headers where Alpaca publishes them rather than
   discovered by hitting them.
6. **What "indicative" means for fill realism** — the one that matters most and is explained
   below.

## The honest limits, stated before anything depends on them

- **IEX IS NOT THE WHOLE MARKET.** The free stock feed is IEX only, which is roughly 2% of
  consolidated US volume. For a *daily close* that is usually immaterial; for an *intraday
  quote* it can differ from the consolidated best bid/offer, and the Signals scan reads
  intraday quotes. The paid SIP feed is the consolidated one. **This is the measurement that
  decides whether Signals can use it**, and it is not answerable from the documentation.
- **"INDICATIVE" OPTIONS QUOTES ARE NOT EXECUTABLE QUOTES.** Alpaca's free options feed is
  indicative, meaning it is a reference price rather than a firm quote you could trade on. This
  project has already measured what that distinction costs: `O10`/`O18` found a real options
  trade pays about **two thirds of the quoted half-spread** (ρ = 0.6743) and that a passive fill
  loses **74% of its gross saving to adverse selection**. So an indicative feed may be fine for
  *scoring* an alert and is **not** adequate for *settling* one — which is exactly the
  distinction the forward options record turns on. Expect the measurement to say "scoring yes,
  settling no", and expect that to be a real constraint rather than a formality.
- **IT DOES NOT RESTORE THE OPTIONS RECORD BY ITSELF.** That record settles positions, and
  settling needs a firm quote.
- **A VENDOR SWAP IS A CONSTRUCTION CHANGE WHEREVER IT TOUCHES A RECORDED NUMBER.** The bound
  Index record prices through `screener/prices.py` and is **measured independent of Tradier**
  (a real mark contacts `stooq.com` only), so nothing about this is urgent for it — and
  changing what prices it is Don's call, not a lane's, because it is the one series that cannot
  be rebuilt.

---

## HOW TO RUN THE MEASUREMENT, AND WHAT ITS ANSWER MEANS (item 62, 2026-10-15)

**THE FIRST RUN SAID "PASSED" ON THREE BARS, SO READ THIS BEFORE TRUSTING THE WORD.** On
2026-10-15 at 22:27Z the door reported the daily-close leg passing at 100% agreement *"across 3
names"* — ET, GBTC and TSM, **one bar each, all dated that day**. It looked like a clean pass
and it was an empty one: the door asked Alpaca for no date window, so Alpaca chose one and
returned a single session, and 98% of three bars is three bars. Nothing was switched on, and
the bar has been rebuilt so that run cannot pass again.

### The one command

```bash
# 1. put the admin token in a variable, so it is never typed into a URL or a shell history line
read -rs ADMIN_TOKEN            # paste it; nothing echoes

# 2. run the measurement
curl -sS -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  "https://valquo.co/admin/alpaca-seam?run=1"

# 3. forget it again
unset ADMIN_TOKEN
```

**RUN IT MORE THAN ONCE — THAT IS NORMAL, NOT A FAILURE.** The full measurement is 250 trading
days across 222 names: about 55,000 Alpaca bars and 222 separate Yahoo history calls, which does
not finish inside one web request. Each call continues where the last one stopped and writes what
it got, so running it four or five times completes it. The reply carries `pull.complete`; while
that is `false` it also carries `pull.owed`, the names still outstanding, and **the measurement
refuses to report an agreement rate at all until the pull is finished**. A rate on a
half-finished pull is the defect this whole item exists to remove.

Everything it writes goes to `/app/data_export/ALPACA_SEAM.json` on the service. It places no
order, touches no key, and changes nothing about what prices anything.

### What a PASS would mean for the 2026-10-22 rebalance

A pass needs **four** things at once, and the two new ones are the point:

1. the daily closes agree with Yahoo's adjusted close on **98% of comparable bars**;
2. there are **enough bars for that to mean anything** — at least 200 names and at least 40,000
   comparable bars, declared in the code with their reason;
3. **every row of the bound Index record re-prices through Alpaca and comes back the same**, to
   within 5 basis points, computed by the record's own arithmetic rather than a copy of it; and
4. `PRICES_PRIMARY_ALPACA=1` is set on the service — **which is still your call and still a
   separate step.**

If all four hold, the honest reading is *"this vendor can price the Index without moving it."*
It does **not** mean the switch has happened. The switch would go in at the **2026-10-22
rebalance**, because a segment's base and its mark must come from one vendor on one basis, and
mid-segment is the one time it must not be done. Nothing about the rebalance itself changes: the
same names, the same weights, the same rules — only where the closing prices come from.

### What a FAIL would mean

**Nothing to do, and nothing to postpone.** A fail simply leaves prices where they are: Yahoo
first, then Stooq, then FMP, exactly as the record has always been priced. The 2026-10-22
rebalance goes ahead on the current vendor either way. **A fail is not a problem with the
rebalance; it is the measurement declining to license a vendor change**, and the only cost is
that the Alpaca key keeps earning nothing.

The two fails worth telling apart, because they point at different things:

- **UNMEASURED** — not enough evidence yet. Usually the pull is incomplete, so run the command
  again. This is the state the first run should have reported and did not.
- **FAILED** — enough evidence, and the vendors disagree. The reply names the worst offenders
  and the largest gap in basis points. If the `vs_recorded` leg is the one that failed, that is
  the serious one: it means substituting Alpaca would have changed numbers already published,
  and the answer is to leave the vendor alone.

