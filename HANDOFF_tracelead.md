# `TRACELEAD` — **the bond candidate is NOT killed and its headline coverage claim does not survive: 81–98% is not a coverage rate, and the comparable figure is 34%**

**2026-10-19, r1 lane. ZERO TRIALS, `FIXED`-class.** Equity `N` stays **307**. **NO REGISTER WAS
COMMITTED, NO ARM RAN, NO FORWARD RETURN WAS LOADED** — pinned by test. **ADOPTS NOTHING.** No app
file, no live path, no change to the Index or the 2026-10-22 rebalance.

Executes `PREREG_DRAFT_tracelead.md`'s §3 free pre-outcome kills, which the draft itself says may
run before the register is committed (`MB1-SEL`: a control can only ever BLOCK, so it costs no
trial). **`K1` does not resolve, so under §6's void condition 3 — `W-28`'s rule that a
pre-committed bar may not be relaxed after it is read — the arm does not run and no trial is
spent.**

---

## 1. THE ONE CONNECTION, AND WHAT IT BOUGHT

`DECISIONS.md` 2026-10-04 permits **one connection attempt per session**, and the brief restates it.
The scout's round-3 session lost its 13F census to `column "mgrno" does not exist` — Thomson's `s34`
column applied to WRDS's **own** 13F product — so this session's collection pass is built the other
way round: **every table's columns are probed before anything is aggregated**, every query is
wrapped, and each step is written to disk as it completes. One attempt, **four steps, all
completed**, 240 seconds.

| probe | result |
|---|---|
| `trace.trace_enhanced` | **PRESENT**, 42 columns |
| `wrdssec_all.wrds_13f_holdings` | **PRESENT**, 18 columns — **and the manager column is `cik`, not `mgrno`** |
| `crsp.stocknames` | **PRESENT**, 16 columns |
| **`frb.rates_daily`** | **PRESENT, 83 columns — A NEW UNLOCK.** The H.15 constant-maturity Treasury curve the spread construction needs for maturity matching |
| `crsp.tfz_dly_ft` | **ABSENT** |

**`frb.rates_daily` matters and the map did not have it:** §2 of the draft needs a maturity-matched
Treasury yield per bond per day, and until now no table was known to carry the curve. It is present.
And the **live** rung needs no licence for it either — the Fed publishes H.15 free.

---

## 2. A DECLARED DEVIATION: THE `D:` VOLUME DOES NOT EXIST

The brief says raw WRDS rows stay in `D:\wrds` **because the repo is public**. Measured today,
`Get-PSDrive` shows **C: only** — the external volume is not connected — so that path is
unavailable, **and round 3's `stocknames.pkl` and `WRDS_CENSUS3.json` are gone with the drive.**

Payload is written under **`C:\wrds_local`**, which is **outside the repository tree entirely**, so
it cannot be committed even by accident — a stronger guarantee than the `.gitignore` that protects
`data/`. **The rule's stated purpose is fully preserved and only its location moves**, payload is
minimised by answering every question that can be answered with a server-side aggregate, and this is
**reported rather than decided silently**. Pinned by a test that the raw root is not under the repo.

---

## 3. THE CORRECTION — AND IT IS TO THE ONE MEASUREMENT THAT RANKED THIS CANDIDATE FIRST

`EDGE_DATA_MAP.md` ranks bonds **#1** on a single fact: *"BEST-IN-CLASS: coverage RISES with size —
81–98% of the tier"*, from a table reading **"our issuers 426 | tier that year 436 | ours ÷ tier
97.7%"**.

**THAT RATIO DIVIDES A NUMERATOR COUNTED OVER ONE POPULATION BY A DENOMINATOR COUNTED OVER ANOTHER,
so it is not a coverage rate.** Reconstructed from the map's and round 3's own published figures:

| | |
|---|---|
| numerator — issuers trading in 2013 Q1 | **426** |
| the tier's **cusip universe**, round 3's own figure | **1,247** |
| **426 ÷ 1,247 — the comparable figure** | **34.2%** |
| the map's denominator — tier **names at one date** | 436 |
| 426 ÷ 436 — the map's ratio | 97.7% |

The denominator is one date's name count; the numerator is drawn from an eleven-year cusip universe.
**Independently corroborated against the panel: the whole tier carries 442–486 names at the four
2013 dates**, which is the 436-shaped number, while its cusip universe is 1,247.

**AND MEASURED DIRECTLY ON ONE CONSISTENT POPULATION — the $10B build-quadrant tier, 459 names,
428 resolvable cusip6 — the issuer-level figure is 39.5% to 56.3%:**

| year | tier issuers trading any bond | of 428 | bonds | trades | with a yield |
|---|---|---|---|---|---|
| 2009 | 169 | **39.5%** | 1,147 | 2,009,392 | 95.8% |
| 2013 | 200 | **46.7%** | 1,377 | 1,809,771 | 88.0% |
| 2016 | 225 | **52.6%** | 1,780 | 2,801,128 | 85.9% |
| 2019 | 241 | **56.3%** | 2,151 | 3,873,108 | 92.6% |

**THIS IS THE `O-1` FAMILY, AND THE MAP ITSELF NAMED IT** — *"`O-1` lost ~17× of power by applying a
coverage figure measured on one population to another"* — which is why the draft's own void condition
6 forbids quoting the 81–98% as the arm's coverage. **What is corrected is the RATIO, not the
numerator: 426 issuers really did trade.** And whether coverage rises **with cap inside the tier** is
**UNMEASURED** here — the per-year rise above is a *time* trend, not a size trend, and the two must
not be conflated.

---

## 4. `K1` IS UNRESOLVED, AND THE BOUND IS WHY THAT IS A REAL ANSWER RATHER THAN A SHRUG

`K1`'s exact form needs the per-**window** issuer lists; the one connection returned per-**year**
counts. But **an issuer trading no bond in a whole year cannot be trading one inside a 63-session
window inside that year**, so the per-year figure bounds the per-window one from above. The bound is
computed by giving the data **every possible benefit** — assuming the `N` issuers that traded are
exactly the `N` tier names appearing in the **most cells** that year, which **no real assignment can
beat**, proved exhaustively on a small case rather than argued.

| year | issuer coverage | **cell-coverage UPPER BOUND** | per-date min bound |
|---|---|---|---|
| 2009 | 0.395 | 1.0000 | 1.0000 |
| 2013 | 0.467 | 0.8909 | 0.8264 |
| 2016 | 0.526 | 0.8555 | 0.8396 |
| 2017 | 0.537 | 0.7764 | 0.7256 |
| 2018 | 0.554 | 0.7453 | 0.7182 |
| **2019** | 0.563 | **0.7325** | **0.7047** |

**THE BOUND CLEARS THE 0.70 BAR IN EVERY YEAR, SO `K1` DOES NOT FIRE — AND A CLEARING BOUND IS NOT A
PASS.** It is `UNRESOLVED`, and the artifact says so in a closed two-word vocabulary so nobody can
read an upper bound as a measurement. **The margin is thin where it counts:** by 2019 the bound sits
**0.0325 above the bar**, and the bound is loose exactly where it looks best (1.0000 in 2009–2010,
because the tier then held fewer names than there were covered issuers).

**So the honest position is: the candidate is NOT killed, and it is NOT cleared either.** Settling
`K1` needs one more WRDS connection in a later session — the per-window issuer lists, which is one
query on an already-probed schema.

---

## 5. WHAT IS NOT DONE, named so it is not mistaken for done

**No register is committed. No trial is booked. No arm ran. `K2`, `K3` and `K4` were NOT reached** —
they are costume and reproduction kills that only matter if `K1` resolves. **The literature leg is
still INCOMPLETE**: Kwan (1996, JFE) and the 2026 replication are *still* unread, and the draft makes
reading them the register's first non-data act — so that obligation carries forward untouched. **No
spread was constructed**, no Treasury curve was pulled, and **nothing was read from the FINRA free
feed**, whose two limits (delay/aggregation and large-trade dissemination caps) remain facts to
verify rather than assumptions.

**`W-19` is not re-opened** — its crash-flag version is a different hypothesis and keeps its verdict.

**20 tests.** `scripts/edge_drafts_collect.py`, `scripts/tracelead_k1_bound.py`;
`C:\wrds_local\EDGE_DRAFTS_COLLECT.json` (licensed, outside the repo),
`data/free_analysis/TRACELEAD_K1_BOUND.json`.
