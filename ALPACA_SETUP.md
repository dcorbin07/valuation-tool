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

### The one command — POWERSHELL

**THE BASH VERSION THAT USED TO BE HERE IS KEPT BELOW, AND IT IS THE WRONG SHELL FOR THIS
MACHINE.** `read -rs` is not a PowerShell command, so the first line failed and the token would
have had to go into the URL — which puts it in the shell history and in the service's own access
log. PowerShell's own masked prompt does the same job properly.

```powershell
# 1. paste the token into a masked prompt. Nothing echoes and nothing reaches the history.
$sec = Read-Host -AsSecureString "Admin token"
$tok = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
         [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))

# 2. run the measurement. FOUR TIMES at the default budget -- see below.
1..4 | ForEach-Object {
  $r = Invoke-RestMethod -Method POST -Uri "https://valquo.co/admin/alpaca-seam?run=1" `
         -Headers @{ "X-Admin-Token" = $tok } -TimeoutSec 300
  "run {0}: complete={1} alpaca={2} owed={3}" -f $_, $r.pull.complete, $r.pull.n_alpaca,
      $r.pull.owed.Count
  $r.rerun_note
  if (-not $r.rerun_helps) { "STOPPING: re-running will not help." ; break }
}

# 3. forget it again
Remove-Variable tok, sec
```

**HOW MANY RUNS A FULL PULL NEEDS: FOUR.** The stated sample is **227 names** (the 222-name
comparison set plus the seven named gaps) and the door pulls **60 new names per call** by default,
so 227 / 60 rounds up to four. `?budget=120` halves that to **two runs**; 120 is the cap, because
a larger budget risks the request timing out mid-pull — which is survivable (the pull is stored
and resumable) but wastes the work already done in that call.

**THE LOOP STOPS ITSELF IF RE-RUNNING WOULD NOT HELP.** That is the whole of item 64's part 1:
the reply now carries `rerun_helps`, and when a call achieves nothing it says
*"RE-RUNNING WILL NOT HELP"* and names the cause. Don ran the previous version **ten times**
against a request that could never succeed, because the old reply said *"run it again until
complete"* in every state.

<details><summary>the bash version, kept for a non-Windows shell</summary>

```bash
read -rs ADMIN_TOKEN            # paste it; nothing echoes
curl -sS -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  "https://valquo.co/admin/alpaca-seam?run=1"
unset ADMIN_TOKEN
```

</details>

### Why the first ten runs all failed, and what changed (item 64, 2026-10-16)

Every one returned `"pull":{"complete":false,"n_alpaca":0,"requests":1}` with the reason
*"subscription does not permit querying recent SIP data (HTTP 403)"* over a window of
`2025-09-11` to `2026-10-16`.

**The free plan serves the consolidated (SIP) tape only once it is more than 15 minutes old, and
it refuses a too-recent window IN FULL rather than trimming it** — so asking for a window ending
*today* killed the whole request at the first chunk. Item 62 was right to declare the window
explicitly (leaving it to the vendor's default is what produced three bars on one day); this is
the other half of that repair. **The end of a free-tier historical window is not "now" — it is
the latest timestamp the entitlement covers**, which is now computed as *the latest date whose
session close is more than the delay in the past*.

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

### AND IT STILL 403'd IN THE EVENING — the end was a DATE where Alpaca wants an INSTANT (item 65 part 5)

Don ran it again at about **22:00Z on 2026-10-16**, after the fix above had deployed. The new code
worked — its own *"RE-RUNNING WILL NOT HELP"* note came back — and the pull still got nothing,
over the window `2025-09-11` to **`2026-10-16`**, which is **today**.

**THE DATE WAS CORRECT AND THE WIRE VALUE WAS NOT.** `sip_safe_end` returns a *date*, and at
22:00Z it correctly returns today: today's close was more than sixteen minutes earlier. But
**Alpaca's rule is about an instant** — its own FAQ: *"For historical queries, the `end`
parameter must be at least 15 minutes old to query SIP data without a subscription"* — and the
refusal is `{"code":42210000,"message":"subscription does not permit querying recent SIP
data"}`, exactly what came back.

**WHAT THE EXPANSION OF A BARE DATE IS, IS NOT DOCUMENTED AND IS NOT ESTABLISHED HERE.** Alpaca's
docs show bare dates in examples and say nothing about whether `2026-10-16` becomes 00:00:00 or
23:59:59. What the observation settles is narrower and enough: a bare `end` equal to **today** is
refused at 22:00Z, so it is not read as an instant fifteen minutes old. (An unrelated codebase hit
the same error by sending an explicit `date + time.max`, which fits end-of-day — corroboration of
the consequence, not proof of the mechanism.)

**SO THE FIX DOES NOT RELY ON KNOWING WHICH.** The end now goes on the wire as an explicit
RFC-3339 instant — the earlier of that session's close and *now minus the delay* — and an explicit
past instant is past under every reading. The window's own `end` stays a date, because that is the
right description of the period a reader is looking at; `end_param` is what the request carries.

**IT PREDICTS ITS OWN HISTORY, which is why the diagnosis is credible:** the old code works
whenever the end rolls back to a finished day — before about 21:16Z on a weekday, and all weekend.
Every in-session run during item 64 was inside that window, which is exactly why nobody saw it.

**AND WHY THE TESTS MISSED IT IS THE PART WORTH KEEPING.** Item 64 verified the window *"at every
quarter-hour of a week against the rule's own definition"* — that the end's session close is more
than the delay in the past. **That test could not fail, because it asserted the rule against
itself.** It never asked what the rule's output means to the vendor, which is the only thing that
decides whether the request is served. There is now a fixture that implements Alpaca's documented
rule and refuses accordingly, and the evening case is tested against **that** rather than against
ours — under both candidate readings of a bare date.



---

## THE OPTIONS FLEET NEEDS A SECOND PAPER ACCOUNT (item 66, 2026-10-16)

**Why a second one rather than sharing the first.** Alpaca lets you have **up to three paper
accounts**, each with its own keys. The Index paper book is deployed at **100%** of its account,
and a cash-secured put needs **cash** - so if the fleet shares that account, one book silently
starves the other, and the starved one records a refusal that reads like a market fact rather
than a plumbing one. Separate accounts is the cheap fix.

**Right now, with no second account, the fleet is split:**

| book | what it does | today |
|---|---|---|
| F-3 bear puts, F-11 dip-reject puts | **buys** puts - needs no cash beyond the premium | **can trade on the existing key** |
| F-8, F-21, F-22 | **sells** premium - needs cash | refuses with `SHARED_ACCOUNT_WOULD_COLLIDE` |

### Four steps, about three minutes

1. In the Alpaca dashboard, create a **second paper account** (Paper -> account selector -> new).
   **Paper accounts get options Level 3 automatically** - there is nothing to apply for.
2. Generate an **API key** for that account. Copy both halves once; the secret is shown once.
3. In Render -> the service -> **Environment**, add two variables:
   - `ALPACA_FLEET_PAPER_KEY_ID`
   - `ALPACA_FLEET_PAPER_SECRET_KEY`
4. Save. Render redeploys. The three short books start by themselves on the next scheduled
   cycle - nothing else has to be switched on.

**Never paste a key into chat, a prompt file, or a commit.** If one ever does get pasted
anywhere, regenerate it in the Alpaca dashboard. No lane ever sees a key.

### How to check it worked

The same masked-token shape as the measurement above, against the fleet door:

```powershell
$t = Read-Host "admin token" -AsSecureString
$h = @{ "X-Admin-Token" = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($t)) }
Invoke-RestMethod -Uri "https://valquo.co/admin/fleet-cycle" -Method POST -Headers $h |
  ConvertTo-Json -Depth 6
Remove-Variable t, h
```

Each book reports either a fill or a **named refusal**. What to look for:

- `BROKER_UNAVAILABLE` - no Alpaca credentials at all reached the service. Check step 3.
- `SHARED_ACCOUNT_WOULD_COLLIDE` - the fleet keys are still missing; it is using the Index
  slot and correctly refusing to let a short book compete with it for cash.
- An order id and a fill price - it worked.

### The limit that travels with every number this produces

**The free options feed is `indicative`, not OPRA** - Alpaca's own words are that the quotes
are *"not actual OPRA quotes but indicative derivatives"*, and the trade feed is delayed 15
minutes. **How Alpaca paper fills an option order is not documented anywhere.** So a fill here
is evidence that **the machinery runs end to end**, and it is **not** evidence about execution
quality. This project already measured the real thing: a live options trade pays about **two
thirds** of the quoted half-spread (`O18`, rho 0.6743), and resting at the mid gives back
**74%** of the gross saving to adverse selection (`O10`). Those are the numbers to use for
cost; the paper fills are for checking the plumbing.


## SETTLEMENT AND FRACTIONAL SHARES — what Alpaca publishes, quoted (item 67, 2026-10-17)

Don asked for two things: wait for cash to settle before buying, and check whether fractional
shares work in the IRA. Both turn on what Alpaca's own documentation says, so it is quoted here
rather than paraphrased — three earlier items in this file were caused by a paraphrase.

### THE ACCOUNT'S BUYING-POWER FIELDS ARE NOT INTERCHANGEABLE

`GET /v2/account`, Alpaca's own words:

| field | what Alpaca says | used here? |
|---|---|---|
| **`non_marginable_buying_power`** | *"Current available non-margin dollar buying power"* | **YES — the primary** |
| `buying_power` | *"If multiplier = 4, this is your daytrade buying power …; If multiplier = 2, buying_power = max(equity - initial_margin,0) * 2; **If multiplier = 1, buying_power = cash**"* | only as `min(cash, buying_power)` |
| `regt_buying_power` | *"Your buying power under Regulation T"* | **never** — levered by definition |
| `cash` | *"Cash Balance"* | as the fallback, and as the bound on the one above |
| `multiplier` | *"1 (standard limited margin account with 1x buying power), 2 (reg T margin account …), 4 (PDT account …)"* | reported, never relied on |

**`daytrading_buying_power` and `cash_withdrawable` are NOT in that schema.** A design reaching
for either is reaching for a field that does not exist.

**WHY `min(cash, buying_power)` IS THE RIGHT FALLBACK AND A MULTIPLIER BRANCH IS NOT.** Buying
power equals cash only at `multiplier` 1. Taking the minimum is safe at every multiplier, so an
unreported or wrong multiplier cannot widen the budget — whereas `if multiplier == 1: use
buying_power` trusts a field to be right about itself.

### THE IRA PROBABLY NEVER WAITS, AND THAT IS WHY THE CODE ASKS RATHER THAN MODELS

Alpaca's IRA documentation: accounts are *"by default setup with limited margin (1x margin)"*;
limited margin *"allows you to avoid certain Federal Reserve Board Regulation T settlement
periods"* and *"permits the purchase of securities with the use of unsettled funds"*; it *"does
not allow for borrowing of funds, creating a margin debit, short selling, or selling naked
options"*; and *"Alpaca will not extend any credit or margin in the Alpaca IRA."*

**So a sell-then-buy rebalance may never wait at all.** The code models no settlement calendar: it
asks the broker what is spendable without borrowing and sizes to that. An account whose proceeds
are immediately spendable is simply never deferred. **The wait is built for the case where it
does, not predicted.**

### FRACTIONAL SHARES — THREE DIFFERENT QUESTIONS, AND ONLY ONE IS ANSWERED YET

1. **Does the API accept a fractional order?** YES, measured: 85 accepted on the paper account on
   2026-10-16. A fractional quantity requires `time_in_force=day` — Alpaca permits no other.
2. **Will Alpaca trade THIS NAME fractionally?** Per-asset, and readable: `GET /v2/assets` carries
   **`fractionable`** and **`tradable`**. Alpaca's eligibility rule is roughly exchange-listed
   stocks above $1 with 10,000+ average daily volume, plus some ADRs — so **the answer moves with
   price and volume and a census taken once is wrong later.** The cycle records it every run.
3. **May THIS ACCOUNT trade fractionally?** `GET /v2/account/configurations` documents
   **`fractional_trading`** — *"If true, account is able to participate in fractional trading"*.
   **For the IRA this is UNMEASURED until its keys are on Render and one live-mode cycle runs.**
   The report says *"NOT REPORTED by the API"* rather than guessing, because item 65 is a fresh
   demonstration that the documentation and the wire can disagree. **The definitive test is a $1
   buy placed by hand in Alpaca's own app, and no lane places one.**

**AND A NAME THAT IS NOT FRACTIONABLE COSTS MORE THAN THAT NAME, EVENTUALLY.** One cycle: the
order is rejected and every other name trades. Over several days: its target is never met, the
event is retried, and the no-progress ceiling stops the **whole** event after five trading days
with an alert — including the names that would have traded. **The remedy is a choice: leave it,
round that name to whole shares, or skip it. The last two are construction changes.**

### WHERE THESE ARE READ FROM — AND IT IS NOT A DOOR

`/admin/live-slots?check=fractional` reports both, and **constructs no client**. The reads happen
inside the cycle, because two invariants forbid a door doing it: a live client is constructed in
exactly one gated place, and the status door builds nothing at all. So both answers are as fresh
as the last cycle, and each carries the time it was read.


## THE ADJUSTED-CLOSE SEAM IS CORPORATE ACTIONS, AND BOTH VENDORS MISS SOME (item 68, 2026-10-17)

The measurement completed: 217 names, 58,318 bars, coverage 95.5%. **Daily closes on Alpaca's
`all` basis agree with yfinance's `auto_adjust` on 0.9020 of bars against a declared 0.98 — and
the AS-TRADED leg agrees on 0.9915.** That asymmetry is the diagnosis: the as-traded close is the
same number on both sides, so the gap is entirely in the adjustment.

**THE TWO BASES WERE NEVER THE SAME THING, AND THIS REPO ALREADY SAID SO.** yfinance's
`auto_adjust=True` applies **splits and dividends**; Alpaca's `all` applies **splits, dividends
and spin-offs**. `prices.VENDOR_ADJUSTMENT`'s own comment states it.

**AND NEITHER VENDOR APPLIES IT CONSISTENTLY**, measured on four named events against the
companies' own filings:

| name | event | yfinance | Alpaca |
|---|---|---|---|
| CTVA | Vylor spin-off 1:1, 2026-10-01 | restated (6.665) | **did not** |
| AZN | ADS → 0.5 ordinary, 2026-02-02 | restated (0.5) | **did not** |
| APTV | Versigent spin-off 1-for-3, 2026-04-01 | **left a −10.6% cliff** | restated |
| UL | Magnum demerger 1-for-5, 2025-12-08 | **left a −7.0% cliff** | restated |

**yfinance ENCODES A SPIN-OFF AS A "STOCK SPLIT"**, which is why a reader sees a factor of 6.665
on Corteva and goes looking for a split that never happened. The factor is the separation.

**THE NUMBER TO REMEMBER: 0.9020 IS ABOUT 21 NAMES OF 215, NOT A THIN SPREAD ACROSS 58,318
BARS.** One corporate action poisons every bar before it for that name, and at 271 bars a name ~21
affected names produce exactly that rate. The as-traded leg's 494 disagreeing bars is ~1.8 names.

**WHAT IT MEANS FOR THE RECORD, WHICH IS NARROWER THAN THE HEADLINE.** The bound Index record is
cumulative from **2026-07-30** and is priced on yfinance. A restatement before that date changes
only bars the record never reads — and **of the four events above, only Corteva's falls after
inception.** On that one the incumbent is the vendor that got it right, so a switch would have
carried a 6.665× error into that holding if CTVA is in the book, against a measured
yfinance-to-FMP seam of about 0.02pp.

**SO THE DAILY-CLOSES LEG IS ANSWERING A QUESTION THE RECORD DOES NOT ASK.** The question a switch
turns on is whether the two vendors agree **since inception, on the book's names** — a few hundred
bars, every one of which the record uses. That is a new, separately declared measurement and is
Don's to authorise; it is not a relaxation of the 0.98 bar, which is unchanged.

