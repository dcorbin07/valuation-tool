# PROMPT — r1 — 2026-10-22 — EODHD: census, harvest everything useful while the subscription is live, and the cross-vendor check before Sharadar lapses

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.**

## What Don bought

The **EODHD "Fundamentals Data Feed"**, a PERSONAL plan, bought 2026-10-22, about one month.
Measured from eodhd.com/pricing on 2026-10-22:

**Included:**

- fundamentals for global stocks and ETFs, back to 1985 for major US companies;
- insider transactions (SEC Form 4, US);
- historical market cap (US);
- corporate calendar (earnings, IPOs, splits);
- news and sentiment;
- macro data, interest rates, US Treasury;
- credit and sovereign risk, including US corporate.

**Not included:** end-of-day prices, dividends and splits, intraday, the screener, and **bulk**
fundamentals (that needs the Extended plan).

**Limits:**

- 100,000 calls a day and 1,000 a minute;
- one fundamentals request costs 10 calls, so about 10,000 tickers a day at most;
- the allowance resets at midnight GMT.

## The key

Don puts it in `C:\Users\donni\Downloads\valuation-tool\.env` as `EODHD_API_KEY`.

- Read it from the environment.
- Never print, log or commit it.
- If it is absent, stop and say so in one line.
- **It does not go on Render or GitHub.**

## The licence fence — read this before anything else

The personal plan permits storing and analysing the data for **private, non-commercial** use. It
**prohibits displaying, redistributing or granting access to it, "in its original or repackaged
form."**

So:

- **Nothing from EODHD reaches valquo.co, the public repo, `data_export/`, or any public page.**
- Raw rows live only under `D:\eodhd\` (D: is attached), and never in git.
- Research artifacts may carry derived statistics (an IC, a *t*, an overlap rate), never per-name
  values.
- Wiring EODHD into the live site would need a commercial licence. That is Don's decision and is
  not part of this item.

## Work, in priority order (the time-critical ones first)

### 1. Census, day 1

Measure; do not assume. Write `EODHD_CENSUS.md` in the style of `WRDS_CENSUS.md`. Cover:

- **Coverage** of the corrected 9,645-name universe and of the $10B tier, with tickers matched on
  a dated identifier, never an undated join.
- **Point-in-time or restated?** Do the statements carry a real `filing_date`? Check a known
  restatement: does history show the original or the restated figure?
- **Delisted companies:** are dead companies' fundamentals there?
- **How far back** history really goes, per field.
- **The other feeds:**
  - insider (Form 4) against what the project already has;
  - historical market cap against Sharadar DAILY;
  - the earnings calendar: does it carry FORWARD dates? The options lane's F-4 and F-10 are
    blocked on exactly that;
  - corporate credit-risk history (is it a live input for `tracelead`?);
  - how far back news sentiment goes.

### 2. Harvest, days 1–3

Pull everything a future test could need into a dated freeze under `D:\eodhd\`, with a checksum
manifest, so it stays usable after the subscription ends:

- full fundamentals for every US name in the corrected universe, including delisted names;
- insider history;
- historical market cap;
- the earnings-calendar history;
- the credit-risk history.

Stay within the daily budget. Resume across days rather than restarting.

### 3. Cross-vendor check, before Sharadar lapses about 2026-11-03

This must finish while both vendors are live; it cannot be done afterwards.

- Score the $10B tier as of **2026-10-22** with EODHD fundamentals and the project's existing
  prices.
- Compare it with the Sharadar-built 10-22 book: name overlap, per-theme rank correlation, and
  which themes disagree and why.
- Reuse `PREREG_d9_free_route_fidelity.md`'s pre-committed GO bar **verbatim**.

The question it answers: could future rebalances run on EODHD instead of renting Sharadar? Zero
trials, FIXED-class.

**Limits:**

- No construction change.
- Not a vintage event.
- Nothing adopted: whether to switch vendors is Don's decision.
- Note in the result that a switch on a personal plan would also need the licence question
  answered, because the Index is published.

### 4. A second-vendor replication of the backtest, only if the census shows real filing dates

- Draft a blind register, committed ALONE with trials booked first, that re-runs the deployed
  composite on EODHD data.
- Include the 1999–2008 era as the untouched out-of-sample read that Don's 2026-10-04 ruling
  names.
- A vendor-independent replication is the strongest evidence this project could add. If filing
  dates are not real, say so and stop at the census; a restated history would only re-measure the
  look-ahead.

### 5. Hand-offs, reported, not done here

- To the options lane: whether the forward earnings calendar unblocks F-4 and F-10, with the same
  licence fence.
- To the scout: any feed in the census worth a register.

## Rules

- One key, read from the environment and never printed.
- No trades.
- Nothing on Render.
- Nothing in `.github`.
- Raw rows only on `D:\eodhd\`.
- Plain-words summary for Don after each numbered step lands, starting with the census.
