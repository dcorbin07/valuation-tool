# What I need from you

**Tests: 148 (quant_bots) / 181 (options). Both green from a clean zip extract.**

Everything below is written and tested. Three things are blocked on you, and one of them is time-sensitive.

---

## 1. Deploy — the only genuinely urgent item

The Oracle box is still running code where momentum and reversion never close positions and the options bot ignores every risk cap. Every trading day that passes adds more unusable data to curves you'll eventually want to analyse.

`FIXES.md` has the sequence. `DEPLOYMENT.md` has the better version — do the git-pull conversion *as* the deploy, same 20 minutes, and every future deploy becomes one command.

**Expect the test counts to have changed again: 148 and 181.** If you see 124/181 or 106/181, an older build is on the box.

Then reset the curves:

```bash
python scripts/reset_sim_curves.py --bots momentum reversion options --dry-run
python scripts/reset_sim_curves.py --bots momentum reversion options
```

It archives, never deletes. Leave trend alone — it was never affected and it's your only continuous history.

## 2. Oracle → Pay As You Go

Five minutes, stays free, removes the idle-reclamation exposure documented in `DEPLOYMENT.md`.

## 3. Run the Sharadar verification script

```bash
cd quant_bots
# add to .env (gitignored):  NASDAQ_DATA_LINK_API_KEY=your_key_here
python scripts/verify_sharadar.py
```

**Paste the whole output back.** It prints no key material, so it's safe to share anywhere.

It answers six things I could not settle from documentation, and one of them genuinely changes the code:

**Does a restatement APPEND a new AR row?** If Sharadar adds a second row for the same fiscal quarter when a company files a 10-K/A, then the obvious query — latest `datekey` per `reportperiod` — silently returns the RESTATED figure. That's look-ahead bias in a backtest you'd believe was clean, with no symptom. I've written `pit_fundamental()` to take the *earliest* datekey, which is correct under both behaviours. The script tells us whether that defensive choice costs anything.

The other five: which of the 12 bundle tables your key actually reaches (Nasdaq's help centre and the datasheet disagree about whether fund prices are included); the real SEP column list; the exhaustive `TICKERS.category` values, so the universe filter isn't guessing which strings mean "common stock"; whether SF1 percentages arrive as `0.15` or `15.0` (getting this wrong scales a factor by 100x, silently); and confirmation that delisted price history is genuinely retained.

Then, once that looks right:

```bash
python scripts/sharadar_sync.py --tables TICKERS DAILY SEP SF1 --full
```

SEP is a few million rows — expect this to take a while. After that it's incremental.

---

# What got built

## The Sharadar stack

**`core/sharadar.py`** — REST client, sqlite-backed local mirror, and a duck-typed history adapter.

**Zero new dependencies.** Stdlib only: `urllib` + `csv` + `sqlite3`. The bots run on a 1GB free-tier VM and `requirements.txt` stays at four packages. This also sidesteps the official Python client's hard 1,000,000-row ceiling, which SEP and SF1 both exceed — and which *raises* rather than returning a partial frame, so you'd get nothing.

The design bet that paid off: every signal generator in this codebase holds an untyped `self.tradier` and calls exactly one method on it. So `SharadarHistory` implements that one method and drops into all five call sites. Verified — the momentum and reversion generators run on Sharadar data with **not one line of strategy code changed**.

**`AsOfHistory`** is the look-ahead backstop. A backtest that accidentally passes `end=today` doesn't crash; it produces a beautiful, worthless equity curve with no symptom. Wrapping the source in an object that structurally *cannot* return a bar after the simulated date makes that class of bug impossible rather than something you have to remember.

Three adjustment rules encoded and tested, because getting them wrong is silent:

- `closeadj` for **returns** — split *and* dividend adjusted. Using plain `close` understates total return by the entire dividend yield.
- `closeunadj` for **price levels** — `closeadj` is back-adjusted, so a stock that later split 4:1 appears to have traded at a quarter of its real price and fails a $20 screen it actually passed.
- `AR*` dimensions only. `MR*` is restated with hindsight *and* sets `datekey` to the period end, typically 30-90 days before the data existed. Two independent look-ahead traps in one column. Asking for `MRQ` now raises.

## The point-in-time universe — the actual fix

**`core/pit_universe.py`.** The old builder called a live screener with no as-of concept at all. A 2021-2024 momentum backtest traded the 150 largest companies *as of today*, filtered on *today's* price and cap, sorted by *today's* size — on every day of the window. That's not a mild flatter; you've pre-selected the winners of the period you're measuring.

The new one rebuilds membership from `firstpricedate <= D <= lastpricedate`, so companies that have since delisted are present in their own era and companies that hadn't listed yet are absent. It reports how many names in each historical universe are invisible to a live screener today — that number *is* the bias the old results carried.

It deliberately refuses to filter on `scalemarketcap`/`scalerevenue`. Those look convenient but are based on the **maximum observed value over the issuer's entire life** — a company that became a mega-cap in 2024 is labelled mega-cap in 2005. Filtering on them leaks look-ahead into a universe you believe is clean. It uses `DAILY.marketcap` as of the date instead.

## Backtest plumbing

`closes_up_to` and `price_on` were O(n) linear scans called per symbol per simulated day — roughly 10⁸ operations for a 150-symbol, 3-year run before any signal maths. Both now bisect a pre-sorted date list. Plus `load_panel()` / `from_store()` so a Sharadar-backed run loads the whole panel from local sqlite instead of one HTTP call per symbol.

The backtest now also runs the **kill switch** (it was called without `today_pnl_pct`, so the −5% daily stop could never fire) and the **regime gate** (absent entirely from the momentum backtest, though live momentum suppresses all shorts in risk-on regimes). The docstring's claim that "the backtest tests the same code that trades" was false; it's closer to true now, and the docstring lists what's still missing.

Curves now write to a temp file and move on success. Truncating in place meant a crashed run left a partial curve indistinguishable from a complete one — you'd compute a Sharpe over half a backtest and never know.

**`scripts/run_sharadar_backtest.py`** ties it together: rebuilds the universe at every rebalance, loads the union of prices once, runs momentum/reversion/trend, and prints the survivorship gap. Verified end-to-end on a synthetic 30-name mirror where 8 names delist mid-window.

---

## Still not done

Honestly, in rough value order:

- **Screener** — only the value score landed. `pit_data`'s quarterly/annual mixing still corrupts 3 of 6 factors; the backtest still scores a different model than production; the tracking loop is unwired; the health gate still aborts on a single feed error; insider scoring still spans [25,75] instead of [0,100] and collapses unnamed filers into one buyer. **Still zero tests.** Worth doing the `pit_data` fix as part of the Sharadar screener work rather than twice — `ART` solves the quarterly/annual problem for free.
- **Options bot tail** — the equity curve is still written 12×/day rather than daily, which will distort any correlation computed against the other three bots. Plus the ATM-distance cap and the README drift.
- **README drift everywhere** — parameters documented that the code doesn't use.
- **`data/` still lives inside the repo tree.** It's gitignored, but `git clean -fdx` deletes ignored files and that's exactly what you reach for when a pull goes wrong.

One thing I want to flag rather than bury: the parallel agents doing the earlier bug-fix pass hit your account's monthly spend limit and were killed mid-edit. I recovered and repaired everything — but if that recurs, the safest response is a smaller, single-threaded pass rather than another fan-out.

## And the standing warning

You now have decades of history and the plumbing to sweep parameters over it. That combination is how people build strategies that crush the past and lose money live.

`run_sharadar_backtest.py` deliberately ships with **no optimizer**. When one is added it has to be walk-forward from the first commit — parameters chosen in-sample, evaluated out-of-sample once, with the number of configurations tried reported next to every result. A backtest that looks too good is evidence of a bug or of overfitting far more often than it is evidence of edge, and I'll say so when it happens.

---

## Update — screener second pass

See `SCREENER_FIXES.md`. Six defects fixed, and the screener now has **36 tests
where it had zero**.

The headline: **the health gate aborted every run.** `if feed_errors > 0`
across ~13,000 tickers x 2 external feeds — zero errors over 26,000 network
calls is not achievable, so the screener could not have completed a single
successful run. It's now a rate.

Also fixed: recent IPOs silently lost their growth history (`_annual_series`
keyed on the filing's fiscal year rather than the data's, collapsing three
years of comparatives into one); point-in-time factors shifted 4x whenever a
10-Q landed, and differed 4x *within* a cross-section because filers have
staggered fiscal calendars; the insider score used half its nominal weight and
saturated at ~$1M; missing data was scored as bad data; and the new value
score was still wired to nothing in `pipeline.py`.

Run it with: `cd screener && python -m unittest discover tests`

Still outstanding on the screener — the forward-return tracking loop, the
backtest's model and universe, and the insider poller. All listed at the end
of `SCREENER_FIXES.md`.
