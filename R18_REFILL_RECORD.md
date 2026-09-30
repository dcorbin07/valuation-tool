# R18 EMERGENCY REFILL — the truncated chain store
## **ZERO TRIALS. Collection only.** 2026-08-31, the last day of the Pro window.

**THE WINDOW WAS OPEN.** Probed first, because a dead window is a fact and would have ended this
in one line: `MSFT` 2024-01-16 returned **3,156 rows in 1.3 s**. The data exists at the vendor;
only our store is short.

**A NEW FREEZE, NEVER A MUTATION.** `D:\thetadata\chains` and its pinned freezes are untouched —
the refill lands in `D:\thetadata\freeze_r18_refill_2026-08-31`. The truncated census is a
faithful record of what the store WAS and stays true.

---

## 1. THE ENUMERATION — FROM FILES, WHICH IS THE WHOLE POINT

A top-level `ls` shows a symbol directory for the full alphabet and looks complete. **That is
exactly what hid this.** The years live in the FILENAMES.

| | |
|---|---|
| symbol directories | **789** |
| per-year FILES | **2,850** |
| **missing (symbol, year) pairs, 2019-2026** | **5,655** |

Confirmed by hand: `MSFT` holds 2016, 2017, 2018 and nothing else; `AAPL` runs to 2025 but is
missing 2022.

`.empty` and `.exhausted` markers are honoured — a unit the vendor was already ASKED for and had
nothing on is not re-asked, because a window that closes tomorrow may not be spent re-learning a
known absence.

---

## 2. THE BRIEF'S MECHANISM IS REAL, AND ITS SCALE IS MUCH LARGER THAN "BEYOND M"

The brief describes files *"missing beyond ~M"*. Measured as a RATE — raw counts are confounded,
because A simply has more names than Z — **the alphabetical skew is real:**

| | symbols | with any 2019+ file | rate |
|---|---|---|---|
| **A-M** | 491 | 143 | **29.1%** |
| **N-Z** | 298 | 35 | **11.7%** |

**A 2.5× gradient, which corroborates R18's economic argument**: if N-Z is systematically thinner
and N-Z spreads run wider (R18: 3.41% vs 3.05% median), every spread statistic built on the store
is biased, and not by noise.

**BUT THE STORE IS NOT "COMPLETE THROUGH M".** A-M is itself only 29.1% covered for 2019+, and
the per-year census shows why:

| year | symbols holding it |
|---|---|
| 2016 | 718 |
| 2017 | 725 |
| 2018 | **750** |
| 2019 | **65** |
| 2020 | 66 |
| 2021 | 86 |
| 2022 | 49 |
| 2023 | 67 |
| 2024 | 85 |
| 2025 | 154 |

**The store is a 2016-2018 harvest with a thin, alphabetically-skewed 2019+ tail.** So the
correct statement is not *"N-Z was truncated"* but ***"2019+ was barely harvested at all, and what
little exists leans A-M."*** Repairing only N-Z would leave A-M 71% missing for those years and
would not make the store whole — it would only make it evenly incomplete.

---

## 3. SIZED ON MEASURED UNITS, AND THE WINDOW DOES NOT FIT THE GAP

Measured on real units rather than assumed (the harvest's own +339% / −7.4% lesson):

| | |
|---|---|
| per unit | **~150-300 s**, 14-18 MB, **290,000-370,000 rows** |
| observed rate over the first units | **~5 min/unit** |
| **5,655 units at that rate** | **~390 hours** |

**THE WINDOW CANNOT FIT THE GAP AND IT IS NOT CLOSE — roughly 150 units are reachable in the time
remaining, against 5,655 missing.** So this is explicitly a **priority pull**, and the manifest is
the deliverable.

**PRIORITY ORDER, fixed before the pull started:** the names `R18` named and the most
option-active N-Z names first (`MSFT`, `NVDA`, `TSLA`, `WMT`, `XOM`, `ZTS`, then `META`, `NFLX`,
`ORCL`, `PG`, `PEP`, `PFE`, `QCOM`, `T`, `UNH`, `V`, `VZ`, `WFC`, `TXN`, `TMO`, `SPY`, `QQQ` and
the rest), then by how much 2016-2018 depth the store already carries for a name — because a name
the store already holds deeply is the one the rest of the project is most likely reading.

---

## 4. A DEFECT IN MY OWN PULLER, CAUGHT BY DISBELIEVING THE NUMBERS

The first two units recorded **`rows` = 2 on a 14.7 MB payload.**

`theta_bulk._fetch_span` and `_fetch_year` both return a **`(frame, failed)` TUPLE**, and the
first cut pickled the tuple. `len()` of a 2-tuple is 2. **It wrote 14.7 MB of real data under a
row count that was arithmetic on the wrong object, and nothing raised** — every later census
would have read the refill as two rows a year. `MA31`'s failure mode: a clean, plausible number
from a lookup that answered a different question.

Repaired by unpacking, and by switching to **`_fetch_year`** — which is what the original harvest
used, assembles a year from adaptive chunks and remembers the working chunk size per name, so a
wide-ladder name (BKNG: 396,240 rows a quarter) does not fail the same way every run.

**The `failed` half of that tuple is now honoured too: a year assembled from chunks where some
chunk failed records `ok_partial`, never `ok`.** The original harvest carried 145 such years, and
collapsing them into `ok` is how a short year comes to look complete to every later reader.

**The two tuple-shaped payloads were deleted and the freeze reset** — it was minutes old and mine,
so resetting cost two units and left no half-correct records behind.

---

## 5. DISCIPLINE

* **Resume by unit**, with four states: `ok`, `ok_partial`, `empty_vendor`, `fault`. Only the
  first three are skipped on re-run — **"the vendor had nothing" and "we never reached this unit
  before the window closed" must never read the same**, which is the entire value of the manifest
  if the clock beats the pull.
* **Payload written atomically BEFORE its fsynced manifest line**; a torn final line costs that
  unit and not the file; `_replace_retry` for the Windows scanner race.
* **New freeze, never a mutation**, and the existing store and its pinned freezes are untouched.
* **Zero trials** — `by_domain` unchanged at equity 245, options 310, infra 20.

---

## 6. WHAT A SUCCESSOR INHERITS

**The manifest is the deliverable.** `--report` prints, at any moment: units captured, units empty
at the vendor, units still missing, and a sample of exactly which. **A successor with a fresh
subscription re-runs `python -m scripts.r18_refill` and it resumes** — nothing already captured is
re-fetched, and the priority order means the highest-value units are the ones already in hand.

**And the honest bound: after this pull the store is still overwhelmingly a 2016-2018 harvest.**
Any statistic computed across 2019+ on it remains thin and alphabetically skewed, and **R18's
warning about spread statistics stands for every name this pull did not reach.** The refill
narrows the bias on the names it captured; it does not remove it.

`scripts/r18_refill.py`; `D:\thetadata\R18_MISSING.json`, `R18_ALPHA_TEST.json`;
freeze `D:\thetadata\freeze_r18_refill_2026-08-31`.
