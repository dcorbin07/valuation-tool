# The FMP seam — measured 2026-10-08

**Item 40. Nothing was enabled. `PRICES_ALLOW_FMP` is still unset everywhere, and this
measurement never called the shipped gate.** Reproduce with
`python -m scripts.fmp_seam --probe` / `--pull` / `--analyse`.

---

## The short answer for Don

**No — do not enable FMP as a third price rung today.** Not because its data is wrong. Where it
answers, it agrees with Yahoo **to the cent**. The problem is that it barely answers.

Three reasons, in the order that decides it:

1. **The URL we're configured to use is dead.** FMP retired its `/api/v3/` API. Every call to it
   now returns *"Legacy Endpoint — no longer supported."* So setting `PRICES_ALLOW_FMP=1` today
   would add a rung that fails for **every single name**. It would change nothing except adding
   failures to the log.
2. **The subscription only covers about one name in nine.** Of the names we actually asked for,
   **14 of 121 came back; 106 were refused** with *"this value set for 'symbol' is not available
   under your current subscription."* That includes **0 of 16 REITs** and **0 of 10 regulated
   utilities** — the two kinds of company the Dip Detector's new group is entirely about.
3. **The daily allowance is about 250 requests, and there's no bulk option.** Asking for two
   names in one call is refused. The scan's universe is ~1,492 names. So FMP could serve roughly
   **5% of one day's scan** before it stops answering. We hit *"Limit Reach"* after ~185 requests
   while measuring.

**Where it does answer, it is excellent** — see the numbers below. If you ever upgrade the plan,
re-run this measurement and the answer could flip. The script exists for exactly that.

---

## What the data looks like where FMP answers

Same window, same dates, Yahoo against FMP, today's (part-formed) bar excluded from everything.

| what | result |
|---|---|
| as-traded daily closes, 14 names × ~1,250 sessions | **median disagreement 0.0000%** |
| worst single session, any name | **0.0871%** (SONY) |
| 52-week high, as-traded | **0.0000% on 14 of 14** — identical to the cent |
| 52-week high, dividend-adjusted | within **0.0022%** (5 payers) |
| splits, across a named split date | **6 of 6 agree** to four decimals |

So the seam itself is clean. FMP also does something Yahoo does not: it serves the two bases as
**two separate endpoints** (`historical-price-eod/full` for as-traded,
`historical-price-eod/dividend-adjusted` for adjusted). That would let us label its basis as
**verified** instead of the `unverified` the code has to say today — which matters, because item
39 measured that mixing the two bases understates a REIT's drawdown by ~3%.

---

## What this key can and cannot reach

| endpoint | result |
|---|---|
| `api/v3/historical-price-full` — **what `prices.py` is configured to call** | **403 Legacy, dead** |
| `api/v3/profile` — **what `sector_resolve.py` calls** | **403 Legacy, dead** |
| `stable/historical-price-eod/full` | 200 for ~12% of names, **402** for the rest |
| `stable/historical-price-eod/dividend-adjusted` | same pattern |
| `stable/historical-price-eod/full?symbol=A,B` (bulk) | **402** — no bulk on this plan |
| `stable/company-screener` | **402 Payment Required** |
| `stable/profile`, `stable/quote`, `stable/search-symbol` | 200 (tested on AAPL only) |
| daily allowance | **~250 requests**, measured by hitting it; no limit header on any response |

**The key itself works.** It is the plan that is thin — this behaves like a free tier.

**One thing I could not measure and it is cheap to settle:** whether the 402 is about the
**symbol** (this plan covers ~12% of names on every endpoint) or about the **endpoint**
(historical prices are premium, profile/quote are not). Two requests tomorrow answer it, and it
decides whether the sector repair below is worth anything. I ran out of allowance.

---

## Two things worth knowing that came out of this

**1. `sector_resolve.py` has been calling a dead endpoint on every scan.** Its FMP rung is
`api/v3/profile`, which is the 403 above — that is the `sector: the FMP rung failed for X
(HTTPError)` line that appears all through the scan log. In the 2026-10-08 scan, **507 names came
back "UNRESOLVED on every source"**, and each of those gets `regime UNKNOWN` and **its valuation
withheld**. Repointing that one URL to `stable/profile` is a small change that might recover a
chunk of them.

**I did not do it, for a measured reason:** 507 names × 1 request is twice the daily allowance,
so it would exhaust FMP every scan and then starve the S&P-500 constituent call that
`universe.py` makes. And at ~12% symbol coverage it would mostly 402 anyway. **The dead URL is
currently protecting the quota by failing fast.** Worth fixing only alongside a plan decision.

**2. Today's hot scan spent zero FMP calls, and now I know why.** The log reads
`api budget: 0 calls used (uncapped)` because its very first FMP call —
`stable/company-screener` — is **402**, so the provider switches itself off and the scan runs
entirely on the free stack. That also means **my measurement did not endanger tonight's scan**,
which was a real worry going in: the allowance is shared with the scan's own account.

---

## If it is ever enabled, what it must never feed

**Nothing append-only.** Specifically:

- **the forward track record** (`data/valquo_track_history.csv` and the bound Index series) —
  `prices.py`'s own docstring is right that *"a row priced from an unvalidated vendor is a
  permanent entry in an append-only record"*, and there is no un-writing one;
- **the paper-track fills** and the recorded index marks;
- **F-11's dip-reject series**.

Those are permanent and are the project's evidence about itself. A vendor that serves 12% of
names must never decide what a recorded row says — not because it is inaccurate (it is not) but
because **which names it covers is not random**, so it would quietly re-weight the record toward
whatever its plan happens to include.

**Where it would be safe, if the plan improved:** the Dip Detector's 52-week high and the live
screen — read-only surfaces that are recomputed on every scan, where a missing name is already
reported as `n_unmeasured` rather than guessed at.

---

## Reproducing this

```
python -m scripts.fmp_seam --probe                     # which endpoints answer (~8 calls)
python -m scripts.fmp_seam --pull --out <path>         # the sample, both vendors, stored
python -m scripts.fmp_seam --analyse --out <path>      # the seam, from the stored pull
```

The pull **stops on the first quota-shaped response** and says where, because a measurement that
exhausts a shared allowance has broken its own subject. The raw pull is stored so the analysis
can be re-run without spending anything. **The key is never printed** — it travels in FMP's query
string, so every status line and error body is scrubbed first.

**The sample is stated, not "whatever came back":** 222 names — today's hot list and dip screen
(152) plus named blocks of 16 banks, 16 REITs, 16 ADRs, 10 regulated utilities and 12 recent
splitters, each splitter with its split and date so "split handling agrees" is checkable rather
than asserted. `/api/hotstocks` serves the top 100 only, and a random 200 from a megacap-tilted
hot list does not reliably contain a REIT — and the REITs are where the answer was.
