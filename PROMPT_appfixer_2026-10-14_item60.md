# PROMPT — app fixer — 2026-10-14 — item 60: a valuation-verdict headline, and the page ordered from most to least relevant

Run this after item 58b. Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact
path), the 2026-10-14 "valuation page headline" entry, first.

**Don's ruling (chat, 2026-10-14).** Someone looking quickly should get the most useful read
first; someone interested should be able to go deeper. Don chose a **valuation verdict, not a
Buy/Hold/Sell call.** No buy, sell or target-price language appears anywhere. That stays
consistent with his 2026-10-13 removal of Buy/Hold/Reduce and with the site being educational.

## 1. The headline card, shown first once the analysis has run

- **The company name, price and verdict**, set by where the price sits against the model's own
  bear/base/bull range:
  - price below the bear value: **"Undervalued vs our model"**;
  - price between bear and bull: **"Fairly valued vs our model"**, plus how far it sits above or
    below the base value;
  - price above the bull value: **"Overvalued vs our model"**.

  Show the rule in one plain sentence on the card.
- **The fair-value range**, bear to bull with the base value named, e.g. "$248–$425 (base $324)".
- **Confidence**: the model's own confidence label, with what it means in a few words.
- **The two reads**, one line each: business quality and price against the model.
- **What the price assumes**: the existing sentence, plus the story-stock or DCF-reliability
  warning when one applies.
- **When the model withholds or flags its value as unreliable** (for example a low-reliability
  company type), the headline says plainly that there is **no valuation verdict** for this name,
  and why.

The wording lives in one module, the `score_confidence` pattern, and a test asserts it against
the **rendered** payload. That test bans "buy", "sell", "target", "will rise/fall", "upside
target" and any instruction to act.

## 2. Everything else, ordered from most to least relevant

Use this as a starting order and move things only for a stated reason:

1. the headline card;
2. the bear/base/bull range bar against the price;
3. what the company does: description, market cap, revenue, growth, margin;
4. business quality: the score bars and their drivers;
5. the AI analysis;
6. the latest earnings, the company's own announcements, and headlines;
7. the hot list and "what the tool does with this name", with the hot score's limits;
8. the cash-flow projection and Monte Carlo charts;
9. comps and multiples, the reverse-DCF detail, and the sensitivity table;
10. the assumptions editor, notes, warnings, sources and export.

Items 8–10 sit behind a "Show the full model" control that remembers its state. Nothing is
removed, and nothing in the valuation math changes; this is layout and wording only.

## 3. Check it

- Check it on AAPL, MSFT, NVDA, TSLA, KO, KNSL, JPM and APLD, in light and dark mode, on desktop
  and phone width.
- Confirm the verdict for each one against its own numbers.
- MSFT today should read **"Overvalued vs our model · $248–$425 (base $324) · confidence
  high"**.
- KNSL should read "no valuation verdict" with the reason.

Tests that fail on the old order and on any banned word. Done means on origin/main, verified live,
with a plain-words summary for Don and a screenshot description of the new top of the page.
