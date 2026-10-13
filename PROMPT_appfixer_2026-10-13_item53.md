# PROMPT — app fixer — 2026-10-13 — item 53: Index links, news and earnings, clearer numbers

Read `DECISIONS.md` first. The "The valuation page" section now exists (it had not been pushed
when you built item 52, as you correctly reported); its fourth ruling queues this item.

1. **Index rows link to each name's valuation.** `_renderValquoIndex` renders `<b>${p.ticker}</b>`
   with no link, while Hot Stocks and four other tables use `gotoValue`. Per `git log -S` the
   Index rows have had no link since `c0c6fef` (2026-07-31, when Hot Stocks and the Index were
   unified). Link them, and add the same "why?" breakdown the Hot tab has (`attributionPanel`).
   A holding not in today's scan says so instead of an empty panel.
2. **Recent earnings and headlines.** On the valuation page: the last reported quarter (date and,
   where a free source has them, revenue and EPS against estimates) beside the next date already
   shown, plus 3 to 5 recent headlines with source, date and link from a free source (titles and
   links only, no article text; check the source's terms). Feed both to the AI analysis, which must
   say which headline it relies on when it uses one. Keep them in the AI's daily per-ticker cache.
3. **The discount rate, made visible.** Beside the headline, show the base value the same model
   gives at an ordinary discount rate: beta 1.0, everything else unchanged ("At an average-risk
   discount rate of X%, the base value would be $Y"). NVDA is discounted at 16.3% and TSLA at
   14.7% because their vendor betas are about 2. Presentation only: the headline, the sub-scores
   and every recorded number stay as they are.
4. **Plain definitions on hover** for DCF, discount rate (WACC), base value, Rule of 40, reverse
   DCF / "what the price assumes", hot score and the sub-scores. One module owns the wording,
   pinned by test, the `score_confidence.py` pattern.
5. **Serve today's cached AI analysis to every visitor.** Public visitors currently get 403 on
   `/api/ai-analysis` (correctly: they must not start a paid call). A cached analysis costs
   nothing to show again, so serve it to anyone, and keep new paid calls owner-only under the
   unchanged 30-a-day cap.
6. **Copy:** "Priced 1527% above our base value" (TSLA) is right and unreadable. Above 100%, say
   "about 16 times our base value".
7. **Find out why the live scan is missing themes, and do NOT ship a scoring change.** You measured
   that NVDA and KO have null growth and momentum, and only 47 of the 100 served rows carry all
   five themes. Momentum needs only a year of prices, so a null on NVDA looks like a pipeline
   defect rather than a data limit. Diagnose it and measure how many hot scores and ranks would
   move if it were repaired. If the repair changes live hot scores, STOP and route it to Don: the
   2026-08-11 theme restoration was treated as an adopted change and opened a vintage, so this may
   be one too. Report it with the numbers, plus what it means for the 2026-10-22 rebalance.

Paper only, no real trades, `.env` untouched, the admin token never printed. Done means on
origin/main and verified live (screenshots of NVDA, TSLA and the Index tab), with a plain-words
summary for Don.
