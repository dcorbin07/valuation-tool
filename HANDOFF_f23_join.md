# `F23-JOIN` — the SEC ticker join was broken, repairing it moves the arm fivefold, and the verdict does not move

**2026-10-15, r1 lane. ZERO TRIALS, `FIXED`-class.** Equity `N` stays **307**, options 323, infra
20. **ADOPTS NOTHING** — no file under `valuation/web/`, `valuation/saas/` or `valuation/screener/`
changes, no order is placed, no broker code is edited, nothing is purchased.

`F23-SECID` reported its own SF2 gap as *"a **JOIN** problem and not a coverage hole … It needs its
own work and it is not what this register tested."* This is that work, plus the re-run its own
reasoning implied.

---

## 1. THE DIAGNOSIS — `ISSUERTRADINGSYMBOL` IS FREE TEXT, AND THEN THE SAME FILER USES SEVERAL SPELLINGS

Two independent defects, both measured on the 2009-2019 build era before anything was repaired.

**(a) The field is not a symbol field.** It carries 10,361 distinct values of which only **46.0%**
match the corrected panel, and the misses are mostly punctuation rather than unknown companies:

    '"NHF"'   '( EPG )'   '("SPAR")'   '(CALX)'   '(KO)'   '(NYSE:FBC)'   '(NONE)'   'N O G'

**774 of 5,595 missing values are non-alphabetic.** And the obvious cheap fix does **not** work: a
separator-insensitive key rescues **3 of 5,595**, so normalising punctuation is not the repair — the
symbol has to be **extracted** from the text.

**(b) One filer, several spellings — which is why the repair is keyed on the CIK.** **8,542 of
47,141 build-era CIKs (18.1%) file under more than one symbol**, covering **52.9% of rows**; of
those, 6,601 have *some* symbol in the panel and only 2,581 have *all* of them in it. A per-filing
symbol cannot repair that. A **CIK** can.

---

## 2. THE REPAIR — `valuation/studies/sec_ticker_join.py`

For a filing on date `d` by CIK `c`: the as-filed symbol if it resolves; otherwise the most recent
symbol `c` filed under **at or before `d`** that resolves; otherwise **nothing, counted**.

**THREE DESIGN DECISIONS, AND EACH ONE IS A REFUSAL.**

* **EDGAR's `company_tickers.json` IS NOT USED.** It is a **current** snapshot, so applying it to a
  2009 filing is look-ahead, and it omits every delisted name — which are exactly the rows an event
  study must keep (`E-5`). The map is built from the SEC's **own quarterly submissions**, so the
  symbol history is **dated by construction** and no external snapshot is consulted. `S25`'s
  measured lesson about a snapshot wearing a date.
* **`clean_symbol` REFUSES RATHER THAN GUESSES.** A value that does not look like a symbol comes
  back empty and is **counted as unresolved**, never as a plausible-looking wrong ticker — `MA31`'s
  direction, where a clean confident wrong number is worse than a missing one. `ACME CORPORATION`,
  `SEE EXHIBIT 99` and `TOOLONGSYMBOL` all resolve to nothing, and the welding that turns `N O G`
  into `NOG` is restricted to single letters so `FOO BAR CORP` is never welded into a symbol.
* **AN UNRESOLVED ROW KEEPS THE SYMBOL AS FILED.** Not `""`. That is what makes the before/after
  comparable: an unresolved row keeps exactly the value the first read gave it and is filtered out
  downstream exactly as it was, so **the only rows that move are the ones the repair newly
  resolves.** Dropping them would have changed the row set and the key at once and neither could
  then be attributed — the confound `F23-SECID`'s own §1 was written to avoid.

The builder **REFUSES** if the repair ever resolves *fewer* rows, since it can only add a mapping.

---

## 3. BEFORE AND AFTER — the same definition on both sides

| | as filed | repaired |
|---|---|---|
| build-era purchase rows resolving a panel ticker | **61.60%** | **72.54%** |
| build-cell events (name-keyed) | 2,277 | **2,332** |
| distinct build-cell tickers | 608 | **594** |
| events resolving a point-in-time market cap | **48.09%** | **54.85%** |
| events at the `$500M+` floor | 326 | **379** |
| tickers shared with SF2 (of SF2's 1,344) | **335** | **352** |

**THE BEFORE COLUMN REPRODUCES `F23-SECID`'s PUBLISHED 48.1% EXACTLY**, which is what licenses
reading the after column as the same measurement rather than a kinder one.

**THE TICKER COUNT GOES *DOWN*, AND THAT IS THE REPAIR WORKING.** 608 → 594: aliases of one issuer
collapse into one panel ticker. A repair that raised every count would be suspicious.

**AND THE CIK HISTORY DOES THE WORK, NOT THE TEXT CLEAN** — measured by attribution: cleaning the
text alone resolves 360,632 rows against the as-filed join's 360,019, i.e. **+613**; adding the
dated CIK history takes it to 423,997, i.e. **+58,146**. Which is the right way round, since (b) is
the larger defect.

**A DECLARED SENSITIVITY, reported so the price is visible rather than assumed zero:** a variant
that ignores the filing date and uses the CIK's whole symbol history resolves **21,877 more rows**.
That is the cost of insisting on a backward-looking map, and it is paid deliberately.

---

## 4. THE RE-RUN — the same registered read, one instrument fixed

**NO NEW TRIAL.** Same arms, same bar, same null, same halves, same clusterings, same size-tiered
costs, same BH; the **BUILD quadrant only**, with the check quadrant still spent and unread. That
is the `U1-SPLIT` and `SELL-PREMIUM-2` precedent — a correctness repair of one read, not a second
look — so the `F23-SECID` **research-log cell is edited IN PLACE** rather than a second row being
appended (`MB16`: `research_log._parse` has no dedup by id, so appending would charge the trial
twice).

| | first read, broken join | **repaired** |
|---|---|---|
| scored events | 317 / 318 | **363 / 363** |
| ARM B (ID) mean | +0.1551pp | **+0.8679pp** |
| ARM B *t*, date / ticker | +0.168 / +0.142 | **+0.943 / +0.807** |
| ARM B net of cost | −0.4919pp | **+0.2218pp** |
| ARM A (name, reference) mean | +0.1920pp | **+0.9105pp** |
| A1 sign / A4 economic | fail / fail | **PASS / PASS** |
| A2 own null + both halves | fail | fail |
| A3 *t* over 2.0 both clusterings | fail | fail |
| **verdict** | DOES NOT CLEAR | **DOES NOT CLEAR** |

**IT MOVES THE ARM A LOT AND THE VERDICT NOT AT ALL.** The mean rises nearly fivefold and the net
flips positive, so **A1 and A4 now pass where they did not** — and A2 and A3 still fail. *t* 0.94
against a bar of 2.0 is not a near miss, and **the halves disagree in sign**: +2.750pp on 166 early
events against **−0.718pp** on 197 late ones. That is `INSIDER-WIDE`'s measured late-half decay on
a third instrument, and it is not something a larger sample fixes. Two-sided *p* **0.4196**, so BH
at k=1 does not survive either.

---

**ONE CONSEQUENCE WORTH NAMING BEFORE SOMEBODY ASKS IT: `stable_key_half` HASHES THE TICKER, SO
REPAIRING THE KEY CAN MOVE A NAME BETWEEN HALVES.** A row that read `(KO)` and now reads `KO` is
hashed differently, so the build cell's membership shifts — which is **correct**, since the half is
a property of the name and the name was wrong. **It is not a check-quadrant read and it is not
contamination:** the one rationed read was **2020-2026 × half 1**, the cell scored here is
**2009-2019 × half 0**, and a name that moved into half 0 brings its *build-era* rows, whose
outcomes have never been looked at. The eras are disjoint, so no previously-read outcome enters
this cell.

---

## 5. THE REGISTERED FINDING IS UNCHANGED AND IS NOW BETTER EVIDENCED

**THE IDENTITY KEY WAS NEVER THE OBSTACLE — and the repair is what shows how badly it was never the
obstacle.** The join moved the mean by **0.72pp**; changing how insiders are counted moves it by
**0.0426pp** and the *t* by 0.05. **The join is worth about seventeen times the key.** The two event
sets share **2,322 of 2,332 at Jaccard 0.9877** (10 unique to name, 19 to ID).

**THE CENSUS STILL ANSWERS DON'S QUESTION THE SAME WAY, and the repair sharpened it.** Within a
ticker — the unit the rule counts in — **284 ticker-CIK pairs appear under more than one name
against 13 ticker-name pairs carrying more than one CIK, about 22 to 1.** So **yes, names do count
one person twice**, the name rule **OVER-counts** distinct insiders, and it can fire a cluster that
was really one insider filing under two spellings. That is the **false-trigger** direction and the
more serious one for a book. **And it still barely matters:** 10 of 2,332 name-keyed build-cell
events — **0.43%** — vanish under the ID key.

---

## 6. WHAT THE REPAIR SETTLES ABOUT THE SF2 GAP, AND WHAT IT DELIBERATELY DOES NOT

`F23-SECID` reported the gap and refused to attribute it. **The join half is now confirmed rather
than asserted:** SF2 reads **+1.1319pp** on the same cell; the repaired SEC name arm reads
**+0.9105pp** against a first read of +0.1920pp, so **repairing the join closes 76.4% of the
gross-mean gap.**

**THE RESIDUAL IS SAMPLE SIZE AND IS STILL NOT ATTRIBUTED:** 363 events against 1,378, 352 shared
tickers against SF2's 1,344, cap resolution 54.85% against 83.3%.

**A ROW-COUNT COMPARISON ACROSS THE TWO FEEDS IS NOT MADE HERE, AND THAT IS A DEFECT OF MY OWN
CAUGHT BEFORE IT REACHED THE WRITE-UP.** I measured one — on the 964 shared tickers the SEC appeared
to carry 6.4× SF2's purchase rows — and then checked it: SF2's **top** build-cell event tickers
`NBBC` and `SBBX` have **zero** purchase rows in `data/backtest/insiders.csv`, which is impossible
for its own event tickers. The cause is that the SF2 event set is built from **the freeze's raw
SF2** (`insider_cluster.load_sf2`) and not from the pruned `data/backtest` export — whose own
sibling module warns about exactly that. **The figure is dropped rather than reported.** Comparing
against the wrong file is how a mechanism gets invented, and this one would have been quotable and
wrong.

---

## 7. THE POWER STILL TRAVELS WITH THE VERDICT, and it is still the binding limitation

Declared **50.3%** on the gross leg and **14.7%** on the net, before the run. Realised **11.9%** and
**5.0%**, on a worst-clustering `se` of **1.0754pp** against the declared **0.5641**, so the
realised MDE80 is **3.0558pp**. The `se` is still about **1.9×** the declared figure, because the
cell carries 363 events where the declaration assumed 1,378.

**So a cell this weakly powered cannot establish that the ID key is WORSE. It does establish that
the ID key does not RESCUE the cell, which is the question that was asked.**

---

## 8. CONSEQUENCE, AND WHAT IS NOT DONE

**F-23 STAYS DECLARED AND UNFILLED.** No amendment is made, no `F-23b` is declared, and the
live-feed check on the ID rule was **not** run because the register made it conditional on clearing.
**NO VARIANT IS SEARCHED FOR** — a second key, a different `k`, tier or horizon would be a new
register with its own trial, and none is proposed.

Not done, named so it is not mistaken for done: the **check quadrant is not read again**; stage 1
(`PREREG_insider_cluster.md`) and stage 2 (`PREREG_insider_cluster_wide.md`) are **not edited** and
their verdicts do not move; the residual SF2 shortfall is **not** diagnosed; no app file is touched.

**17 tests, 4 of 4 mutations caught with the source restored byte-for-byte** — including the
decisive one that turns the repair back into the as-filed join, which is the pin the brief asked
for. `valuation/studies/sec_ticker_join.py`, `scripts/f23_join_repair.py`,
`tests/test_sec_ticker_join.py`; `data/free_analysis/F23_JOIN_REPAIR.json`, `F23_SECID_ARM.json`,
`F23_SECID_EVENTS.json`.
