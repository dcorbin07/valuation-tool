# PROMPT — app fixer — 2026-10-13 — item 55: more headline sources, conclusions yes, narrative no

Do this after item 54. Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy may be out of date) (2026-10-13, the headline ruling) first.

Item 53 ships headlines from SEC EDGAR and name-filtered Yahoo RSS only. Don's ruling widens that:
any verifiable, trustworthy source is allowed, as long as the item is not a narrative piece.

1. **Add sources that meet a stated standard,** written down in one module and pinned by test: a
   named publisher accountable for what it prints (wire services, established financial and general
   news outlets, company press-release wires, regulators and exchanges), a link to the original, and
   terms that allow showing a title and link. Candidates to check, not assume: company
   press-release wires, Nasdaq's per-symbol feed, major outlets' public RSS, and regulator feeds
   (FDA, FTC, DOJ) where they name the company. Measure each one's yield on NVDA, TSLA, KO and two
   small names the same way item 53 did (how many items actually name the company), and keep only
   sources that earn their place. No paid source, no key, no scraping a site whose terms forbid it.
2. **The line is conclusion versus narrative.** ALLOWED: a reported fact or a conclusion attributed
   to someone — company guidance, an analyst's rating or target change, a regulator's decision, a
   lawsuit filed, a contract won. EXCLUDED: opinion and promotional formats — "should you buy",
   "N reasons it will soar", listicles, price-prediction hype, sponsored or paid-promotion content,
   and unattributed claims. Implement it as a stated, tested rule (source allowlist plus a headline
   filter), with examples of both kinds in the tests. When an item is excluded, count it, so the
   page can say "N headlines found, M shown" as it does now.
3. **Every headline shows its source and date and links to the original;** titles and links only,
   never article text. The AI analysis keeps naming any headline it relies on.

Done means on origin/main, verified live on NVDA and TSLA, with a plain-words summary for Don that
lists the sources kept and the yield of each.
