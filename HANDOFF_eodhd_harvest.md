# HANDOFF — EODHD steps 2, 3 and 4 (2026-10-22)

**ZERO TRIALS, `FIXED`-class throughout.** No hypothesis about returns, no bar of its own, nothing
adopted, no construction change, not a vintage event. Raw rows live under `D:\eodhd` and never in
git; everything committed here carries counts, rates and field names and never a per-name value.

**STATUS: STEP 2 IS HALF DONE AND THE REASON IS A MEASURED COST, NOT A FAULT.** Earnings, insider
and market cap are harvested and verified. **Fundamentals got ZERO names**, because the day's
allowance was already gone — see §1. The harvest resumes at the midnight-GMT reset and the manifest
is the resume point. Steps 3 and 4 are **built and gated** and read the freeze, so they cost no
further calls once fundamentals land.

---

## 1. THE COST MODEL WAS WRONG, AND IT COST A WHOLE DAY'S ALLOWANCE

I assumed only `fundamentals` cost 10 calls. **Measured: `historical-market-cap` costs 10 too.**
7,500 units moved consumption **26,541 → 99,991**, i.e. **9.79 calls each**. So market cap ate
**73%** of the day and fundamentals — the one product steps 3 and 4 actually need — got nothing.

| product | measured cost | units done | status |
|---|---|---|---|
| `earnings` | 1 | 120 quarters | **complete** |
| `insider` | 1 | 539 windows | **complete** |
| `mktcap` | **10** | 5,491 of 9,645 | stopped at the reserve |
| `fundamentals` | 10 | **0 of 9,705** | **pending the reset** |
| credit | — | — | **not harvestable, 403** |

**THE FIX IS AN ORDERING, NOT A BIGGER BUDGET.** A full fundamentals pass is 96,450 of 100,000, so
it needs a day to itself and cannot share one. But the two questions waiting on it need a fraction:
step 3 scores the **835-name** `$10B` tier (~8,350 calls) and step 4's gate needs **120** names
(~1,200). `fundamentals_order()` now puts both inside the first ~10,000 calls, so one day answers
both and the remaining 8,755 names accumulate behind them. It **falls back to plain sorted order and
says so** if the banked scores or the CRSP spine are unreadable — a silent degrade would look
identical and simply fail to unblock step 3.

**ALSO FIXED ON THE WAY: the insider windows were silently truncating.** 25 of 465 came back at
exactly the 1,000-row cap on an endpoint that cannot be paged. `_insider_window` now halves
recursively down to a single day; **25 windows became 74 sub-windows and recovered 46,865 rows with
zero truncated days.** A one-day window still at the cap would be recorded `TRUNCATED` rather than
accepted, because a named hole beats a silent one.

**FREEZE VERIFIED:** `D:\eodhd\freeze_2026-10-22`, **6,150 of 6,150 units, 0 mismatched, 0 absent,
648 MB**, size and sha256 per unit in `manifest.jsonl`.

---

## 2. TWO CORRECTIONS TO MY OWN CENSUS, BOTH FOUND BY READING THE HARVEST

**(a) `ownerCik` IS NOT UNIFORMLY EMPTY — IT IS ERA-DEPENDENT, AND THE CENSUS PROBED THE ONE ERA
WHERE IT IS ZERO.** Measured across all **137,297** harvested insider rows:

| period | `ownerCik` non-null |
|---|---|
| 2010–2011 | **1.0000** |
| 2012 | 0.6060 |
| 2013–2022 | 0.12 – 0.43 |
| **2023 onward** | **0.0000** |
| overall | **0.1338** |

The census measured `0.0000` on 500 **recent, unfiltered** rows and stated it as a property of the
feed. That is the `O-1` family in my own census — a coverage figure from one population applied to
another. **THE CONCLUSION SURVIVES AND THE STATED REASON DOES NOT:** at 13.4% overall and **zero
since 2023** the identifier is unusable for anything current and partial historically, so EODHD is
still not a route to insider identity and `F-23` still needs the SEC's own free feed. The honest
sentence is "empty where it matters", not "empty".

**(b) THE INSIDER FEED IS FAR THINNER THAN IT LOOKED, AND THAT DECIDES A DESIGN CHOICE.** 137,297
rows over 2009-01-01 → 2026-10-22 against the licensed file's **5,636,964** — about **2.4%** — and
it is wildly uneven: **50,900 rows in 2025 and 23,116 in 2026 against roughly 5,000 a year through
2013–2020.** So it cannot carry the `insider` theme, which is why step 3 composes both sides on four
themes (§3). This is **not** a correction to anything the census claimed; it is a quantity the
census never measured.

---

## 3. STEP 3 IS BUILT, WITH THREE DEVIATIONS DECLARED BEFORE ANY NUMBER WAS READ

**THE BARS ARE `D9`'s, IMPORTED AND NOT RETYPED** — `B1` composite Spearman ≥ 0.80, `B2` top-decile
overlap ≥ 0.60, `B3` ≥ 0.70 on **each** of value / quality / momentum / size, `B4` cited from
`FIDELITY-2`, **ambiguous against a bar is NO-GO**. Re-choosing a bar with a cross-vendor number in
hand is what `PREREG_d9_free_route_fidelity.md`'s own void conditions forbid, and a retyped bar is
how one copy freezes while the other moves (`MA5`). Pinned by a test that fails if `0.80`, `0.60` or
`0.70` appears as a literal in the script.

**(i) THE DATE IS 2026-10-02, NOT THE BRIEF'S 2026-10-22.** Both Sharadar stores end **2026-10-02**
(`data/backtest/prices/AAPL.csv` and the `backtest_freeze_2026-10` copy agree) and
`score_universe_now` **refuses** an as-of it cannot honour exactly, so a Sharadar 10-22 book cannot
be built without a fresh licensed pull. 10-02 is the newest date **both** vendors can be read at —
and it is the better experiment: EODHD's filing dates are real, so its side is cut point-in-time at
the same date and **there is no vendor-gap to confound the reading**. A 10-22 EODHD book against a
10-02 Sharadar book would have mixed ~14 trading days of drift into every disagreement, which
`D9`'s own noise ceiling says is not small.

> **THE DEADLINE IS ALREADY RETIRED.** The brief wanted this finished before the licence lapses
> ~2026-11-03 because a Sharadar book would then be unbuildable. **The Sharadar side is already
> banked** — `D9_SHARADAR_SCORES_SAMEDATE.pkl`, 2,037 rows, **835 in the tier** — so nothing in
> step 3 needs Sharadar live. A fresh pull would only be needed to move the comparison date later,
> which §(i) argues against anyway.

**(ii) `B1` IS COMPUTED ON FOUR THEMES WHERE `D9` USED FIVE.** `D9`'s `LIKE_FOR_LIKE` includes
`insider` and the EODHD side cannot carry it (§2b). A five-theme incumbent against a four-theme
challenger is not like-for-like, so **both sides are composed on the same four** — the four that
carry a `B3` bar — and `insider` is cited under `B4` exactly as `D9` already treats it.
**So this `B1` and `D9`'s `B1` are NOT the same statistic** and may not be compared with each other,
though they share the 0.80 bar. Pinned: a mutation that composes the two sides on different theme
sets turns the suite red.

**(iii) BOTH SIDES RUN THROUGH THE SHIPPED `score_universe_now`.** `D9` compared a Sharadar book
against a **served** composite out of a scan JSON — two code paths as well as two vendors, so a
disagreement could not be attributed to either, and its same-date reading was `B1` **0.2410**.
`valuation/studies/eodhd_provider.py` makes EODHD a provider instead, so winsorisation, the bucket
split, the theme means and the composite are **identical by construction** and what is left is the
data. `price_history` **delegates** to the existing Sharadar provider, which is the brief's own
instruction and also the right experiment: holding prices fixed makes a `momentum` disagreement
attributable rather than confounded with a second price vendor.

**THE PROBE GATES IT AND IS READ IN ITS OWN PASS.** `--probe` reports every mapped field's non-null
rate **on the tier itself**, names any field that never appeared, measures the **capex sign**
convention rather than assuming it, and **refuses** if a required column is missing. Five wired
factors were once empty in every run of this project's history without raising, so an unmeasured
vendor mapping is not evidence about the vendor. `--compare` exits non-zero without a passing probe.
**A period with no filing date is DROPPED and the drop is reported** — falling back to the period
end would place an unpublished figure at its period end, the exact look-ahead this design removes,
and that fallback is forbidden structurally and mutation-tested.

---

## 4. STEP 4's GATE: THE 1999–2008 ERA IS NOT REACHABLE FROM THIS UNIVERSE

The brief's instruction was to check the delisted hole first, because a replication on survivors is
worthless. **There are two holes on opposite sides of the join, and the one on OUR side is decisive
by itself and needed no vendor call.**

**OURS.** The corrected universe *is* the panel, and the panel runs **2009-03-27 → 2026-04-09 with
ZERO rows before 2009**: all 9,645 names are present in 2009 or later, so the list is
survivors-to-2009 **by construction**. CRSP's own spine prices that: **13,787 permnos were alive at
some point in 1999–2008 and 6,898 of them — 0.5003 — were gone before 2009.** Scoring that era off
this list would omit half the era's names and precisely the dead half. **Repairing it is a panel
rebuild, not an analysis**, and it is Don's call whether that is worth buying.

**THEIRS, measured next and against a control.** The census found Enron and Lehman present in
`General` and empty in `Financials`, and recorded that two probes is not a rate. The gate samples
**60 pre-2009-dead names beside 60 survivors**, seeded, measured by identical code — because a bare
empty-statement rate cannot distinguish "thin on dead companies" from "thin on everything this
old". Costs 1,200 calls and runs with the fundamentals harvest.

**AND IT NEEDED A GUARD THE CENSUS DID NOT ANTICIPATE: TEMPORAL TICKER REUSE.** A dead company's
last ticker is often reassigned, and `fundamentals/{T}.US` answers for whoever holds the symbol
**today**. Measured: **797 of 5,445 dead tickers — 14.64% — are also live panel tickers**, so about
one dead name in seven would have been scored against a going concern and counted as "statements
present" — biasing the hole toward **zero**, the flattering direction. `S25` recorded this hazard as
unobservable on a snapshot route. Colliding names are dropped and the count reported; a name the
spine says died that the vendor reports as still listed is flagged `reuse_suspected` and excluded
from **both** sides of the rate.

---

## 5. NOT DONE, NAMED SO IT IS NOT MISTAKEN FOR DONE

* **The fundamentals harvest** — 0 of 9,705 names. Resumes at the GMT reset; `--verify` after.
* **Step 3's reading** — the machinery is built and gated and **no `B1`, `B2` or `B3` has been
  computed**. Nothing is known yet about whether EODHD can stand in.
* **Step 4's vendor half** — the 120-name probe has not run. The our-side finding blocks the era
  replication regardless, but whether a *rebuilt* point-in-time universe would also hit an
  empty-statement hole is unmeasured.
* **The market-cap remainder** — 4,154 names, and the census already showed the feed is 5 years of
  weekly points, so it cannot define a historical tier anyway.
* **No register, no trial, nothing adopted.** A replication needs its own blind register with its
  trials booked first, and on §4's evidence its out-of-sample era is not available as specified.
* **Hand-offs are REPORTED, not done** — the forward earnings calendar for the options lane
  (`F-4`/`F-10`), and for the scout the forward calendar, news sentiment, and the replication
  question. The insider feed is **not** worth a register (§2b); the credit feed is unavailable.
* **Nothing reaches valquo.co, the public repo, `data_export/` or any public page.** A switch of
  vendor on a personal plan would also need the licence question answered, because the Index is
  published — Don's decision, not a lane's.
