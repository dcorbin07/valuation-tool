# THE $ADV INSTRUMENT — B13 / S7-4's liquidity measure
## **ZERO TRIALS. INSTRUMENT ONLY — no arm ran in this pass.** 2026-08-26.

Built and validated **before** the register that will use it (`MB15`'s ordering), and **no
ranking, filtering or scoring touched it**. The register is `PREREG_b13_s7d_liquidity.md`,
committed alone and afterwards.

---

## 1. WHAT IT UNBLOCKS, AND WHAT IT DOES NOT

`B13` (`MIN_AVG_DOLLAR_VOLUME` *"structurally cannot bind on this path"*) and `S7`'s fourth
interaction (*"the one that cannot be built at all"*) both rest on one fact: the project's only
volume source reaches **502 of 2,531 names = 19.8%**. CRSP `dsf` reaches **2,271 = 89.7%**.

**That is a coverage unblock and nothing more.** Neither arm has been run and this file contains
no result about either.

---

## 2. THE DEFINITION IS MATCHED, NOT CHOSEN

`valuation/screener/prices.py:243` computes the live `avg_dollar_volume` as the mean of
`close × volume` over the trailing **~60 sessions** on the **as-traded** close. `B13`'s
`MIN_AVG_DOLLAR_VOLUME = 500_000` is calibrated against *that* quantity, so the panel instrument
reproduces it — **choosing a different window would silently re-scale a threshold the two
surfaces share**, which is `MA5`'s frozen-constant family one level up. Pinned by a test that
fails if the live screen's window moves.

The window ends on the **prior** session. A liquidity screen that reads the selection day's own
tape is a look-ahead on the series most correlated with that day's news.

---

## 3. COVERAGE, ON THE POPULATION THE ARMS WILL TEST

| | |
|---|---|
| panel cells | 113,945 |
| with a point-in-time ADV | **90,025 = 79.01%** |
| excluding the 5 dates after CRSP's cut | 90,025 of 104,578 = **86.08%** |
| dates with ≥20 covered names | **64 of 69** |
| halves of the covered subsample | **32 / 32**, boundary **2017-01-19** |
| per-date coverage | min 78.3%, median 85.5%, max 96.2% |

**THE 89.7% IS NAME-LEVEL AND THE ARMS ARE SCORED ON CELLS — the honest figure is 79.01%.** A
name can resolve to a permno and still have no usable ADV on a date. Quoting the name-level
number for a cell-level arm is the population mismatch `MB8` and `V6-OPT` both paid for.

**Coverage RISES through the sample, 78.6% → 96.2%**, so the early half sits on a thinner
cross-section than the late half. Declared now because a coverage trend that tracks time will
surface in any both-halves gate, and finding it after a split disagrees is how an artefact
becomes a finding.

Unlike `S18`'s 16/16, the halves here are **32/32** against the shipped `min_dates=16` floor.

### What CRSP cannot cover
Cut at **2024-12-31**: five panel dates fall after it — 2025-01-27, 2025-04-28, 2025-07-29,
2025-10-27, 2026-01-28 — **9,367 of 113,945 rows = 8.22%**. Nothing built on this instrument may
say anything about 2025 or 2026, and the forward paper track lives entirely after the cut.

---

## 4. TWO TRAPS, BOTH MEASURED

**`prc` IS NEGATIVE WHEN CRSP SUBSTITUTES A BID/ASK MIDPOINT** — its convention for a close that
did not trade, **28,283 rows = 0.404%**. A naive `prc × vol` goes negative on exactly the least
liquid rows, and a negative ADV sits below any floor, so a filter would appear to work while
working for the wrong reason.

**THE JOIN IS DATE-SCOPED. 1,053 of 2,271 matched tickers map to more than one permno** —
`S3-I5`'s reuse problem in a **third** table, after the option chains and the IBES actuals. A gap
between two holders resolves to **nothing**, never to the nearest one.

---

## 5. B7 FIDELITY — AND IT FOUND A DEFECT IN THE INCUMBENT ROUTE

Against `scripts/capacity.py:adv_from_bars` on the **24,586 cells both can price**: median ratio
**1.0002**, **flat across every size decile** (1.0001–1.0004). Same quantity.

**16.0% of cells disagree by more than 25%, and it is the incumbent that is wrong.** My first
hypothesis — reuse in the bars cache — was **REFUTED** (16.6% vs 15.4%, a 1.08× lift). The
disagreement is systematic per name, and against the vendor columns directly:

| | volume, bars ÷ CRSP (early) | (late) | price, bars ÷ CRSP |
|---|---|---|---|
| CMG (50:1) | **50.0000** | 0.9962 | 1.0000 |
| AAPL (4:1, 7:1) | **27.9950** | 0.9958 | 1.0000 |
| WMT (3:1) | **3.0000** | 0.9937 | 1.0000 |
| MSTR (10:1) | **10.0015** | 1.0097 | 1.0000 |
| SIRI (1:10 **reverse**) | **0.1000** | 0.1016 | 1.0000 |
| **JPM (no split — control)** | **1.0000** | 0.9882 | 1.0000 |

**`data/bulk/prepared/bars` pairs an AS-TRADED `raw_close` with a SPLIT-ADJUSTED `volume`**, so
`adv_from_bars` overstates dollar volume by the cumulative forward-split factor — **up to 50×** —
and understates it on reverse splits. The price leg is 1.0000 everywhere, so it is the volume leg
alone. `U1-SPLIT`'s defect with the legs swapped.

**Direction, and it is the one that matters here: it makes split names look MORE liquid than they
were, so a floor built on the incumbent route UNDER-filters.**

**REPORTED OUTSIDE THIS LANE (`RUN_RULES` rule 3), NOT FIXED.** `adv_from_bars`' only consumer is
`capacity.py`'s own run; repairing it would move a published capacity figure. `fundamental_panel`'s
`prefilter_adv_partial_source` block cites that function and inherits the caveat.

---

## 6. WHAT IS NOT DONE

**No arm is run and none may be run in a pass that builds or changes this instrument.** The
prefilter is not applied to the panel; `MIN_AVG_DOLLAR_VOLUME` is unchanged and unwired;
`prefilter_adv_wired` still reads `false`; no interaction column exists; no verdict moves; and
`adv_from_bars` is left as found.

**14 tests, 8 of 8 mutations caught with sources restored byte-for-byte** — including the
negative-price convention dropped, the window reading the selection day, the last interval closed
at CRSP's cut, and the join snapping to the nearest holder across a gap. **One was MISSED on the
first pass and is worth recording: the short-history test passed `min_sessions` explicitly, so it
kept passing against a module whose DEFAULT had been dropped to 1 — and the default is what every
caller gets. A guard that only holds when the caller restates it is not a guard.**

`valuation/edge/adv.py`, `scripts/b13_adv_build.py`;
`data/free_analysis/B13_ADV_COVERAGE.json`, `B13_ADV_PANEL.pkl`, `B13_ADV_FIDELITY.json`,
`B13_ADV_TAIL.json`, `B13_ADV_SPLIT_DIAG.json`, `B13_ADV_BARS_DEFECT.json`,
`B13_ADV_PER_DATE.json`. Raw CRSP daily rows stay on `D:\wrds\crsp_dsf_panel`.
