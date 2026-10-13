# PROMPT — app fixer — 2026-10-13 — item 52: the valuation page gives context, not a Buy label

Read `DECISIONS.md` first: three rulings dated 2026-10-13 under "The valuation page" govern this.

## What Don saw, measured live on valquo.co today (`/api/value`, `/api/whatdo`)

| | price | base FV | upside | 1-100 | label | regime / DCF reliability | price implies | model base growth | hot score |
|---|---|---|---|---|---|---|---|---|---|
| NVDA | 226.32 | 145.44 | −36% | 79 | Buy | hypergrowth / medium | 37.9%/yr | 34.35% | 13 (1,262 of 1,440) |
| APLD | 23.25 | 20.33 (range 0.39–74.08) | −13% | 32 | Reduce | hypergrowth / low | 49.4%/yr | 34.35% | 67 (477 of 1,440) |
| TSLA | 378.03 | 23.23 | −94% | 36 | Reduce | mature / **high** | 64.9%/yr | 4.9% | 4 (1,395 of 1,440) |

NVDA's 79 is valuation 15.9 × 0.20 + quality 97.2 × 0.15 + growth 100 × 0.30 + health 97.4 × 0.25 +
momentum 70.2 × 0.10. That is a business-quality grade wearing a "Buy" label, and no study in this
project has ever tested the Buy/Hold/Reduce labels against returns. TSLA's "DCF reliability: high"
tells a reader to trust a $23 fair value on a stock whose price is mostly a bet on things not in its
financials. The page carries no description of the company at all.

## What to build

1. **Drop the Buy / Strong Buy / Hold / Reduce / Avoid labels everywhere the 1-100 score appears.**
   Census every surface first (`grep -n "recommendation\|Strong Buy"` finds ~31 files: the gauge,
   the compare table in `app.js`, the PDF and Excel exports, notify emails, the AI prompt, landing,
   methodology, terms, portfolio, research and the rest) and change them consistently. Replace the
   single gauge with two reads in plain words:
   - **Business quality** — from the quality, growth, health and momentum sub-scores, with a plain
     phrase (e.g. "Outstanding business").
   - **Price vs our model** — from the valuation sub-score, said as a sentence ("priced 36% above
     our base value").
   The sub-scores and their arithmetic do NOT change. This is presentation only, so no number any
   study, the Index, the hot list or the forward track reads may move. Confirm by test that
   `compute_score` still has exactly one caller and that no research path reads the label.
   If dropping the label leaves anything empty, say so rather than filling it.
2. **Lead every name with what the price assumes**, from the reverse DCF the engine already
   computes: "The price assumes about X% a year growth; the business grew Y% over the last year
   and the model's base case uses Z%." For a financial, use the matching question
   (the implied ROE), as the reverse box already does.
3. **The DCF warning.** For hypergrowth, cash-burning, growth-led or low-reliability names, and for
   story stocks, put a plain note at the top: do not use the DCF fair value to decide on this
   company, and why (its value is mostly future growth a cash-flow model can't pin down). You must
   define "story stock" with a rule stated on the page — for example, the price assumes more than
   15 points a year more growth than the business shows. This is page copy, not a research claim,
   but write the rule down and test it on NVDA, APLD, TSLA and two mature names (e.g. KO, JNJ),
   which must NOT get the warning. When the warning fires, the "DCF reliability: high" badge must
   not read as trust in the fair value (rename it to what it measures, or suppress it).
4. **Show the hot score beside these reads**, near the top, with its drivers (the existing
   attribution) and its limits, in `score_confidence.py`'s calibrated words: the evidence is about
   the top decile as a group, not one name's position, and the size theme marks megacaps down by
   design. A name outside today's scan says "not in today's scan" rather than a blank.
5. **Open the page with a plain description of the company** from the market-data profile
   (yfinance `longBusinessSummary` or the equivalent free field), plus the key facts a reader needs:
   market cap, revenue, growth this year and over three years, the operating margin trend. Say
   where it comes from. Add the source column to the fetch path and confirm it is populated for
   NVDA, APLD and TSLA (the COVERAGE RULE: an empty field must show as missing, not vanish).
6. **The AI analysis runs automatically.** Fire it in the background after the numbers paint (it
   took 36 s on TSLA today, so it must never block the page), saved per ticker per day so a second
   visitor gets it instantly. Before turning it on, measure the cost of one call from the response's
   token usage and the model's published price, and report it. Daily cap: 30 new analyses until
   Don sets a number; when the cap is reached, the page offers the button instead of showing nothing.
   Update the prompt: give it the hot score and its drivers, the what-the-price-assumes read and the
   two new reads; remove "reference the score and the recommendation"; forbid any buy or sell
   recommendation. Label the panel: written by AI from the numbers on this page, not from news, and
   can be wrong. Never print or log the key.
7. **Check two things the numbers above raise, and report them:**
   - NVDA's hot-score explanation lists no momentum or growth theme (APLD's lists eight themes,
     NVDA's six). Find out whether those inputs are missing for NVDA in the scan. If they are, that
     is a data gap to report, not an explanation to write.
   - The model's base growth path averages 34.35% for BOTH NVDA and APLD, whose growth inputs are
     77% and 100%. If every hypergrowth name gets the same capped path, the page must say so
     (otherwise "the model uses 34%" reads like a company-specific forecast).

Screenshot NVDA, APLD and TSLA on the live service after deploy and include them in the handoff.
Paper only, no real trades, `.env` untouched. Done means on origin/main, verified on the live
service, with a plain-words summary for Don.
