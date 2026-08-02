# HANDOFF — lazy prices (roadmap #28), 2026-08-02

**Done: the dataset exists.** 195 filers, **7,095 scored filing pairs**, 7,843 filings
downloaded from free SEC EDGAR with **zero fetch failures**, covering **2016-08-10 to
2026-07-31**. 90.5% of parsed filings got a score; the other 9.5% are each ticker's first
year, which cannot pair with a prior year by construction. Full detail in
`LAZY_PRICES_COVERAGE.md`; the dataset is `data/filings/lazy_prices.csv` (gitignored).

Nothing here is wired into the panel and no IC was computed — that was the instruction, and
a test enforces it (`test_module_is_not_imported_by_the_live_panel`).

## What to run

    python -m valuation.research.lazy_prices --limit 250 --since 2016-01-01   # or run_lazy_prices.bat
    python -m valuation.research.lazy_prices --score-only                     # re-score, no network
    python tests/test_lazy_prices.py                                          # 28 tests

Resumable: per-ticker caches flush every 20 documents, so a kill costs nothing. A full
re-run from a warm cache is ~5 minutes; the cold build took ~70 minutes at ~1 doc/sec.

## The four things worth knowing

1. **Point-in-time is real, not asserted.** Rows are dated by the later filing's FILING date;
   pairs are the same fiscal quarter 270-450 days back; and the TF-IDF corpus is walked in
   filing-date order so a pair scored on date D sees document frequencies only from filings
   before D. Fitting one vectorizer over the whole download would leak the future into every
   historical row and would show up as a *better* backtest, not an error. Two tests pin it.
   Verified on the real data: 0 rows where the prior filing is not strictly earlier.

2. **Four separate coverage bugs were found and fixed, three of them silent.**
   - `XOM` returned **zero** filings: SEC's ticker map points at a post-reorganization
     successor CIK with no 10-K history while 42 filings sit under the predecessor.
   - `BLK` returned **7 of ~42** for the same reason — the dangerous version, because seven
     looks like a working ticker. `MRVL` (23 of 44) and `APO` (17 of 42) too.
   - 17 of the "top 250 large caps" were **long-delisted** names (TWX last quoted 2018, RAI
     2017): the market-cap ranking had no recency check.
   - The MD&A/Risk section splitter read **cross-references as headings**, so `risk_*` was a
     near-duplicate of `mdna_*` on filings like AAPL's 10-Q.
   A short-history detector now flags any ticker under 60% of the universe median every run
   (12 flagged today, all verified as genuine recent IPOs/spinoffs). **Read that list.**

3. **Two known dirty edges, both reported rather than silently cleaned.** 5 rows come from
   sub-2,000-word stub filings (all BNS) that score ~1.0 against last year's boilerplate;
   filter on `n_words`. 10-Q risk sections are often just "no material changes"; filter on
   `risk_words`. Section isolation succeeded on 92.5% (MD&A) / 79.0% (Risk) of pairs.

4. **The universe is survivor-only** — today's large caps, not the survivorship-free Sharadar
   panel. Any first-pass IC on this is a survivors' IC and must be labelled as such.

## Recommended next step

Run the gated IC test on `data/filings/lazy_prices.csv`: join `available_from` to forward
returns, rank cross-sectionally per date, and put it through CPCV / the held-out split like
any other candidate. Use `cosine_tf` and `jaccard` (corpus-free, no IDF assumptions) as the
primary measures and treat the section measures as secondary. Orientation is already fixed in
the code and in git history: **higher similarity = lazy = bullish**, not negated anywhere —
so a negative result is a rejection, not a sign-flip opportunity.

If it looks promising, the next data step is breadth: 195 large caps is a thin cross-section
for an IC, and the fetch scales linearly (another 250 names is about another hour).

Not touched: `HANDOFF_STATUS.md`, `fundamental_panel.py`, `bulk.py`, the options code, the
engine and the web app — parallel agents own those. `test_edge.py` still passes 119/119.
