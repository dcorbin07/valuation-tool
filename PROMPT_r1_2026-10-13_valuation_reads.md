# PROMPT — r1 — 2026-10-13 — record the valuation page's reads forward, test registered first

Read `DECISIONS.md` ("The valuation page", 2026-10-13), `RUN_RULES.md` PART 0 and item 52's
handoff (`HANDOFF_appfixes.md`, the new `business_quality`, `price_vs_model` and
`price_assumes.py` reads).

**Why.** The valuation page's Buy/Hold/Reduce labels were never tested against returns and are now
gone. Its new reads (business quality, price vs our model, what the price assumes, the DCF warning)
will not be tested either unless they are recorded: V6 established that the live sub-scores
cannot be rebuilt point-in-time, so a forward record is the only route. Today's archive
(`valuation/edge/archive.py`) keeps only the top 100 hot names a day and none of these reads, so it
says nothing about a name like NVDA at rank 1,262.

1. **Register the future test blind, committed ALONE, before the first row exists.** Name the
   reads under test, the statistic (for example the cross-sectional rank IC of each read against
   the forward 3-, 6- and 12-month return), the population, the both-halves rule, the floors and
   how they are calibrated, the read schedule (when the first verdict may be read, and that it is
   read once), and the trial count, charged at the first verdict read. Say what a NULL would mean
   and what power the design has at each read date — an honest "unlikely to resolve before year
   N" is a finding, not a reason to skip.
2. **Build the recorder.** Every name in the weekly scan (or, if measured cost forbids it, a
   population fixed in the register before recording starts — never chosen afterwards): ticker,
   date, price, market cap, regime, DCF reliability, the five sub-scores, business quality, price
   vs model, base value and range, price-implied growth, the business's growth, the warning flag
   and which rule fired, hot score and rank. Append-only, recorded fresh each week, never
   backfilled, and backed up the way the forward Index record is. Measure what one weekly run costs
   in time and vendor calls first. A new workflow goes through `data/pending_workflows/` plus
   `install_workflows.bat`; no paid cron.
3. **Self-check on day one:** a row round-trips unchanged, a refused valuation records as refused
   (not as a blank), and nothing in the recorder reads a forward return.

No verdict is read and nothing is adopted. Check landing once after each push; no wait loops.
Done means on origin/main, the recorder scheduled or its workflow pending for Don, with a
plain-words summary for Don.
