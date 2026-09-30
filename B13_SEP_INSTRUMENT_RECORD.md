# `MC9` — THE SEP $ADV / OHLC INSTRUMENT

**AUDIT 6, item MC9. 2026-09-29. ZERO TRIALS** — equity `N` stays **248**, options **310**, infra
**20**; `sqrt(2 ln 248)` = **3.3206712412296953**, options **3.3872030637324335**. No hypothesis,
no bar, no verdict against a threshold, and **no arm ran in this pass** (`MB15`'s ordering,
enforced by an AST test rather than promised).

**NOTHING IS ADOPTED.** `MIN_AVG_DOLLAR_VOLUME` is not wired, `prefilter_adv_wired` is still
`False` at `fundamental_panel.py:1641`, the B13 arm did not run, and **no tracked file under
`valuation/` was modified** — the instrument is a new module and the OHLCV is emitted BESIDE the
shipped price files, so every default panel payload is bit-identical (`C3`).

---

## 1. THE PREMISE, VERIFIED

| claim | measured |
|---|---|
| `data/backtest_freeze_2026-08/bulk/sep.csv` exists, 3.2 GB | **3,223,156,161 bytes**, read-only |
| header | **`ticker,date,open,high,low,close,volume,closeadj,closeunadj,lastupdated`** — exact |
| `data/backtest/prices/<T>.csv` carry `date,close` only | **confirmed** |

## 2. THE TWO CONTRARY CLAIMS — `B13` IS TRUE, `P1` IS FALSE

* **`B13`'s ledger row** names its re-open condition as **"SEP volume reaches the loader"**, and
  says `MIN_AVG_DOLLAR_VOLUME` cannot bind *"because the price export on disk carries date and
  close ONLY"*. That is a claim that **SEP volume EXISTS and is merely not plumbed**.
* **`HANDOFF_free_analysis.md:548-551`** (`P1`) says *"**SEP is not on disk in any form**; the
  bulk extracts are ACTIONS, DAILY, EVENTS and SF3, none carrying volume"*, and on that basis
  filled **45.3% of capacity positions** with a market-cap proxy
  (`log(ADV) = -8.72 + 1.186*log(mktcap)`, R² 0.704).

**`B13` IS TRUE. `P1` IS FALSE, AND IT WAS ALREADY FALSE WHEN IT WAS WRITTEN.**

| | |
|---|---|
| `sep.csv` mtime | **2026-08-02 17:14** (freeze root 18:25; every bulk CSV 17:08–17:18) |
| `P1` landed | **2026-08-04**, commit `7edf594` |

**THE MECHANISM IS EXACT, AND IT IS THE PORTABLE PART.** `data/bulk/` contains precisely
`actions.csv`, `daily.csv`, `events.csv`, `sf3.csv` — **the four `P1` enumerated, and nothing
else**. The freeze at `data/backtest_freeze_2026-08/bulk/` contains those **plus** `sep.csv`,
`sf1.csv`, `sf2.csv`, `sf3a.csv`. **`P1` enumerated ONE directory correctly and generalised to
"in any form".** It is `DEEPITM-FIN`'s existence-is-not-population defect with the quantifier
inverted: there a directory existed and was empty, here a file existed and the search did not
reach it.

**WHAT IT COST, STATED PLAINLY AND NOT OVERSTATED:** `P1`'s ~$23M capacity figure rests on a
proxy for 45.3% of positions that did not need to be a proxy. **This item does not re-derive it**
— that is `P1`'s to re-run, and it is routed, not taken.

## 3. THE CONSTRUCTION

`valuation/edge/adv_sep.py`. The window is **`adv.ADV_WINDOW_SESSIONS`, IMPORTED** — there is no
second `60` here, because `MIN_AVG_DOLLAR_VOLUME` is calibrated against `prices.py:243`'s mean
and two copies of a calibrated constant is `MA5`'s frozen-hurdle family. The roll **DELEGATES**
to `adv.adv_series` (`B7`), so the SEP and CRSP series cannot drift apart in what they mean, and
the window **ends on the PRIOR session**.

**THE SPLIT PAIRING WAS MEASURED, NOT ASSUMED.** CMG the session before its 50:1 split
(2024-06-20): `close` **64.288** against `closeunadj` **3214.42** — ratio exactly **50.0** — with
`volume` **42,188,400**. `close × volume` = **$2.71bn**, plausible; `closeunadj × volume` =
**$135bn**, not. **So SEP's `volume` is split-ADJUSTED to match `close`**, and dollar volume is
split-INVARIANT provided both legs share a basis.

Accumulated split factors (`closeunadj / close`), all reproducing `B13`'s own recorded table:
**CMG 50.02 · AAPL 28.00 (7×4) · WMT 3.00 · MSTR 10.00 · SIRI 0.0995 (1:10 reverse) · JPM 1.0**
(the unsplit control).

`dollar_volume` deliberately does **not** reuse `adv.dollar_volume`: that applies `abs()` for
CRSP's negative bid/ask-midpoint convention, which SEP does not have, and borrowing it would
hide a negative close instead of surfacing it. **Measured: 0 negative closes and 0 null-volume
rows in 8,185,668 kept rows**, so the choice is inert and the inertness is a measurement rather
than an assumption.

Scan census: **46,248,674 rows read · 8,185,668 kept · 2,531 of 2,531 panel tickers found ·
13,121 non-positive-volume rows COUNTED and excluded** (a zero dollar volume sits below every
floor, so admitting it would convert *"we cannot see this session"* into *"this name did not
trade"*).

## 4. COVERAGE, ON THE PANEL'S OWN CELLS, BEFORE ANY FIDELITY COMPARISON

| | SEP | CRSP (`B13`) | bars (`MA25`) |
|---|---|---|---|
| panel cells with a PIT ADV | **113,583 / 113,945 = 99.68%** | 90,025 = 79.01% | — |
| universe names reached | **2,531 = 100%** | 2,271 = 89.7% | 502 = 19.8% |
| dates with ≥ 20 covered | **69 of 69** | 64 of 69 | — |

Per-date: **min 0.9723 · median 0.9981 · max 1.0000**. Halves at 2017-01-19: early **0.9983**,
late **0.9958**. Non-positive-volume share of kept rows **0.160%**.

**THE FIVE POST-CRSP DATES, WHICH ARE THE POINT.** CRSP on this account is cut at 2024-12-31 and
covers **none** of them; SEP covers all five: 2025-01-27 **0.9979**, 2025-04-28 **0.9979**,
2025-07-29 **1.0000**, 2025-10-27 **1.0000**, 2026-01-28 **1.0000**.

## 5. `B7` FIDELITY — the two comparisons go opposite ways, which is what makes them a test

**vs CRSP** — both pairings internally consistent, so they must AGREE, and they do. 90,005 of
CRSP's 90,025 cells overlap (**99.98%**): **median ratio 0.99886**, p05 0.9578, p95 1.0269,
**2.15% more than 25% apart**. By size decile the median ratio runs **0.9967 → 0.9994**, flat;
dispersion is largest in the smallest decile (3.53% apart) and smallest in the largest (1.06%),
which is the expected direction for thin names.

**vs `adv_from_bars`** — expected to resolve AGAINST bars, and it does, exactly.

| rows | n | median ratio bars / SEP | > 25% apart |
|---|---|---|---|
| no split intervening | **1,696,861** | **1.0000** | **0.001%** |
| split-affected | 313,705 | 2.9999 | 97.6% |

**The correlation between the bars/SEP ratio and the accumulated split factor is 1.0** — the
disagreement *is* the split factor, not merely correlated with it. Per name: **CMG 50.0 ·
AAPL 27.998 · WMT 3.0 · MSTR 10.0 · SIRI 0.1** against split factors 50.0, 27.998, 3.0, 10.0,
0.1; **JPM has no split-affected rows and reads exactly 1.0**.

This confirms `B13_ADV_BARS_DEFECT.json` independently: **bars pairs an AS-TRADED `raw_close`
with a SPLIT-ADJUSTED `volume`**, so `adv_from_bars` overstates dollar volume by the split factor
on every pre-split row. It is a live defect in `scripts/capacity.py:69` — **reported, not fixed**,
because `P1`'s capacity figure rests on it and repairing it moves a published number.

## 6. THE TWO QUESTIONS THE BRIEF ASKS, ANSWERED

* **Does SEP dissolve "cannot bind universally"? YES.** `B13`'s row says
  `MIN_AVG_DOLLAR_VOLUME` *"structurally cannot bind on this path"* because the export carries
  no volume. A point-in-time dollar ADV now exists for **99.68% of panel cells on 69 of 69
  dates**, which is not "universally" in the strict sense — 362 cells have none — but it is a
  different statement from the one in the row, and the 0.32% is a measured remainder rather than
  a structural absence.
* **Does it reach the paper-track era? YES.** CRSP stops at 2024-12-31 and the forward track
  lives entirely after it. SEP covers all five post-cut rebalance dates at **99.8–100%**.

## 7. NOT DONE, named so it is not mistaken for done

* **The B13 arm did not run.** No ranking, no filtering, no scoring in this pass — pinned by an
  AST test over the module and both runners that fails if `fwd_ret`, `MIN_AVG_DOLLAR_VOLUME`,
  `quantile_backtest`, `holdout_compare_panels` or `top_decile_alpha` is referenced.
* **`MIN_AVG_DOLLAR_VOLUME` is NOT wired and `prefilter_adv_wired` stays `False`.**
* **`P1`'s ~$23M capacity figure is NOT re-derived**, and `adv_from_bars` is NOT repaired. Both
  are routed to the lanes that own them.
* **No claim is made that a liquidity filter would help.** That is `B13`'s arm and it needs its
  own register and its own trials.

## 8. TESTS

**15 tests, 5 of 5 mutations caught with sources restored byte-for-byte.** They pin the imported
window (with an AST reading of `prices.py`'s own `min(60, n)` call, because the existing pin at
`tests/test_adv.py:124` asserts a SUBSTRING that would also pass inside a comment), the
delegation, the prior-session rule, that a missing export RAISES rather than reading as "no
volume", the split invariance, the `MB15` ordering, and that the sidecars land beside the price
files.

**A DEFECT IN MY OWN TEST, AND IT IS THE FAMILY THIS RECORD NAMES MOST OFTEN:** the first cut of
the `abs()` ban asserted the SUBSTRING `"abs("` was absent from the function and **fired on the
docstring explaining why `abs()` is not used** — written minutes after the same family was
recorded twice in `PKG-MB20`. It reads call nodes now, with a positive control against
`adv.dollar_volume`, which does call `abs`.

**A DEFECT IN MY OWN DIAGNOSTIC, FOUND BY THE CONTROL NAME BEHAVING ODDLY:** the split-affected
cut was one-sided (`factor > 1.01`), so **SIRI's 1:10 REVERSE split — factor 0.0995 — was
misfiled as UNSPLIT** and contaminated the control bucket with the very disagreement it exists to
exclude. Corrected to a distance-from-1 cut in either direction, which moved the unsplit bucket's
"more than 25% apart" share from **2.51% to 0.001%** and put SIRI's 0.1 where it belongs.

`valuation/edge/adv_sep.py`, `scripts/mc9_adv_sep.py`, `scripts/mc9_fidelity.py`,
`tests/test_mc9_adv_sep.py`; `data/free_analysis/MC9_SEP_INSTRUMENT.json`, `MC9_FIDELITY.json`,
`MC9_SEP_ADV.pkl`; per-ticker OHLCV in `data/backtest/ohlcv/` (2,531 files). Raw SEP stays in the
frozen export and never reaches the repo.
