# PROMPT — scout — 2026-10-18 — new information for the $10B Index: what to read, what to pull, what to test next

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path). **Do not edit
  `DECISIONS.md`.**
- `WRDS_CENSUS.md`, `WRDS_UNLOCK_MAP.md`, `WIDTH_AUDIT.md`, and your own ideas ledger.

## Why

Don wants the Index's edge bigger and better supported. Today it is **+2.22 points a year over SPY,
after costs, at t ≈ 1.1**. Most published ideas the project has tested came back null, and the
literature says anomalies are weakest in large stocks and after costs.

So more reading is not the bottleneck. **New information that large-cap investors don't already
price** is. Rank every candidate on four things:

1. **Is it new** relative to the seven themes? Check the costume tests against each theme.
2. **Does it plausibly work in $10B+ names?** Cite the paper's own large-cap or size-split result
   where one exists.
3. **Can the LIVE Index legally get it?** WRDS is licensed for academic research only. A
   WRDS-only input can show whether an idea works, but cannot feed the live score or a public
   page. Name the live source and what it costs:
   - free: SEC EDGAR, FINRA, Sharadar (already rented);
   - paid: the vendor and its price;
   - none.
4. **What it would cost** to research and to run.

## Tasks

No forward return is computed anywhere in this item. You map and draft; r1 executes registers.

**A. The 209 published signals (Open Source Asset Pricing, Chen & Zimmermann, October 2025
release, free).**

- Only the signal documentation was ever downloaded (`data/factors/raw/osap_signal_docs.csv`). The
  firm-level signals were never pulled. Pull them; raw files stay out of git.
- Join them to the $10B tier by CRSP permno through the **dated** `crsp.stocknames` route. CCM is
  denied, and an undated join is `W-28`'s contamination.
- For every signal, report:
  - coverage of the $10B tier per date, and in both halves;
  - its largest correlation with the seven themes;
  - whether this project already tested it, with the ledger id;
  - whether it can be rebuilt live from Sharadar or EDGAR.
- Propose ONE batch register for the survivors: one trial per signal, booked first; BH across the
  batch; both halves; the deployed 1/7 book. State its power at today's `N`.

**B. Analyst long-term-growth optimism (Bordalo, Gennaioli, La Porta & Shleifer, JF 2019).**

- IBES is entitled; the LTG forecast is in `statsum_epsus` with `fpi = '0'`. Link through
  `wrdsapps_link_crsp_ibes.ibcrsphist`.
- Census its coverage on the $10B tier.
- Say how it differs from `MB18` (market-implied growth, null) and `D6` (revisions, null).
- Name any live LTG source and its price.

**C. Corporate bonds (TRACE, entitled, 455M trades, never used).**

- `W-19` drafted a crash-flag version. Scope the **return** version too: do bond spread changes
  lead the company's stock?
- Report:
  - how many $10B names have a liquid bond on each date;
  - the live source (FINRA's free delayed data) and its limits;
  - the strongest paper for and against.

**D. Per-manager 13F (WRDS, 7,000–8,000 managers a quarter from 2013).**

- The shipped theme counts holders. Scope "**which** managers are buying": skill-weighted or
  crowding measures.
- Only 2013 onward is usable, per the census.
- The live source is SEC EDGAR (free).

**E. WRDS census, round 3.**

- One connection attempt only. Real `SELECT`s, recorded as ENTITLED, DENIED or ABSENT.
- Probe each of these:
  - IBES recommendations;
  - Compustat segment customers (Cohen-Frazzini customer momentum);
  - Capital IQ transcripts and key developments;
  - RavenPack;
  - ISS;
  - BoardEx;
  - JKP firm characteristics;
  - any point-in-time Compustat snapshot.
- Add a line to the census for each.

**F. Reading.**

- Use the free scholarly APIs: OpenAlex, Semantic Scholar, arXiv, NBER, and the authors' SSRN
  pages. Most top-journal papers have a free working-paper version.
- Write `LIT_LARGECAP.md`, one row per idea that survives in the largest stocks after costs:
  - the original paper;
  - its large-cap result;
  - post-publication evidence;
  - a free PDF link.
- Quote under 15 words from any source, and summarise in your own words.

## Rules

- Raw WRDS rows stay in `D:\wrds` and are never committed; the repo is public.
- No key, login or token printed.
- No outcome statistic.
- Nothing adopted.

## Done

- `EDGE_DATA_MAP.md`: every candidate ranked on the four tests above.
- `PREREG_DRAFT_*` files for the top three.
- `LIT_LARGECAP.md`.
- The census lines.
- A plain-words summary for Don, giving for each of the top three:
  - what it is;
  - why it might work in big companies;
  - whether the live Index could use it, and what that would cost;
  - its honest chance.

Landed on origin/main.
