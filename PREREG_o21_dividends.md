# PRE-REGISTRATION — O21, dividends and early exercise

**Committed before any measurement code for this item exists.** This file and
`PREREG_o26_bucket_floor.md` are the only files in their commit; no `.py` accompanies them, so
the ordering is provable with `git show --name-only --format= <commit>`.

Item **O21** in `VALQUO_LEDGER.md` (`OPEN`, src=auto, "no mention anywhere in the corpus"), so
the scope below is derived rather than inherited. Options domain.

---

## 1 · State of knowledge when this was written, disclosed

Measured today, **before** this register existed:

* **`blackscholes.bs_price`, `implied_vol` and `greeks` all ALREADY take a `q` (continuous
  dividend yield) parameter and handle it correctly** — `exp(-qT)` on the spot leg, `(r − q)` in
  `d1`. The defect is **not** a missing model. **It is that every caller uses the default
  `q = 0.0`.** `enrich_chain(df, underlying, as_of, q=0.0)` is called in exactly two places and
  neither passes `q`: `options_backtest.pick_contract:313` and `optvrp_run.py:250`.
* **Dividend data EXISTS and is usable**: `data/bulk/prepared/actions.pkl` carries per-ticker
  `dividends` as `(ex_date, amount)` pairs — **13,505 of 31,937 tickers** have at least one, and
  every large payer checked is present and dense (AAPL 56 rows, JNJ 114, XOM 115, back to 1998).
* **The frozen chains are FULL chains, not just the banked contracts**: 2,870,811 rows carrying
  every strike and both rights per symbol-date (~450-500 call rows, 60-95 distinct strikes and
  7-11 expiries at a sampled entry date). **Contract re-selection under a corrected pricer is
  therefore possible without any re-mine.**
* The path study registered `delta85` as *"ties to O21"* and found it nearly inert — it fires on
  **2.4%** of trades, because the −50% option stop always fires first.

**Not known:** any dividend yield actually applicable to these trades, any re-selected contract,
any early-exercise loss, any greek shift. Those are what this register commits to.

## 2 · THE SCOPING FACT THAT DECIDES WHAT CAN MOVE

**The banked book's P&L comes from QUOTED bid/ask in the frozen chains, never from a model
price.** So a pricer that ignores dividends **cannot move the recorded P&L directly**. It reaches
the book through exactly three doors, and this register measures all three separately because
they have different strengths:

| door | mechanism | can it move P&L? |
|---|---|---|
| **D1 · early exercise** | the sim always SELLS at the bid; a deep-ITM American call near ex-div can be worth more exercised than sold | **yes**, and model-free |
| **D2 · contract selection** | `pick_contract` picks the contract whose \|delta\| is nearest 0.35, and delta is computed at `q = 0` | **yes** — a different contract is a different trade |
| **D3 · stored derived fields** | `iv` and `target_delta` are banked on every row and feed O13's arms and `delta85` | no, but it moves derived studies |

**Anyone reading "the pricer ignores dividends" as "the headline expectancy is wrong" is reading
it wrong**, and D1/D2 are the only routes by which it could become right.

## 3 · Data and definitions, fixed now

Split-clean banked books only (`state_r2_splitclean.pkl`, n 3,870, and the five control seeds).
No re-mine. The exit policy is untouched.

**Dividend yield, two definitions, both fixed now:**

* **`q_trailing` (PRIMARY, strictly point-in-time):** sum of dividend amounts with ex-date in the
  365 days **before** the entry date, divided by `underlying_entry`. Uses only information
  available at entry, so no arm resting on it can be accused of look-ahead.
* **`q_scheduled` (SECONDARY):** sum of dividends with ex-date in `(entry, expiry]`, divided by
  `underlying_entry`, annualised by dividing by `T`. A dividend's ex-date and amount are
  announced weeks ahead, so this is realistic rather than clairvoyant — **but it is labelled
  secondary and may not carry a verdict**, because it reads the future of the contract's life.

**Early exercise is measured MODEL-FREE and that is deliberate.** The classic condition compares
the dividend to remaining time value, which needs a model and would make the answer a function
of the very pricer under test. Instead: a holder who could sell at `bid` but exercise for
`S − K` left money on the table whenever **`bid < S − K`**. That inequality needs no vol, no
rate and no dividend estimate. Dividend dates enter only to say *when* the situation arises.

## 4 · Arms and bars, fixed now

**Q1 — early exercise (D1).** Over the banked book: how many trades EXIT at a price strictly
below intrinsic, and what is the total and per-trade expectancy understatement if each such exit
had instead been an exercise at `S − K`? Reported for the alert book and, as a control, the
pooled five-seed random-entry book. Also descriptive: how many trades hold an ITM call across an
ex-dividend date.

**Q2 — contract selection (D2).** Re-run `pick_contract` on the **same frozen chain rows** for
every banked entry, twice: once at `q = 0` and once at `q = q_trailing`. Count how often a
**different contract** is selected, and re-simulate the changed trades through the **shipped**
exit policy to get the P&L difference.

> **CONTROL, and the rest is not quotable without it: the `q = 0` arm must reproduce the banked
> contract.** If re-selection at `q = 0` does not return the contract the book actually holds, the
> harness is wrong and no difference it reports means anything. Reported as a reproduction rate
> before any difference is quoted.

**Q3 — derived fields (D3).** Recompute `iv` and `delta` at `q_trailing` for every banked
contract at entry; report the distribution of shifts, and whether `delta85`'s 2.4% firing rate
moves.

**MATERIALITY BAR, fixed now.** The pricer is **FIXED** if either:

* **(a)** the combined Q1 + Q2 effect on per-trade expectancy is **≥ 1.00pp** in absolute value; or
* **(b)** any published verdict's relationship to its bar changes — *this clause governs even if
  (a) fails*, and it is the one that matters.

Below both, the finding is **IMMATERIAL** and the pricer is left alone with the measurement
recorded. **A near miss is IMMATERIAL, not a fix.**

**If the pricer is fixed**, derived data is re-stamped with the **autopsy-comparability
discipline** already used by `U1-SPLIT`: corrected outputs go to **NEW files**, originals are
**never overwritten** because they are the record of what was published, and a sha256 manifest
records both sides.

## 5 · Both halves

Q1 and Q2 are **descriptive measurements of a defect's size**, not hypothesis tests, so they
carry no half-split requirement — a bug's cost is what it is. **If the materiality bar is
cleared and a fix changes a verdict, that changed verdict is re-derived on both halves**, because
at that point a claim is being made rather than a cost being counted.

## 6 · Expectations, written before any of it runs

* **E1 — IMMATERIAL. 70/30.** The book is 45-75 DTE at ~0.35 delta, i.e. deliberately OTM, and
  early exercise is a **deep-ITM** phenomenon. Most trades should never be near the boundary.
* **E2 — fewer than 2% of exits occur below intrinsic. 65/35.**
* **E3 — contract selection changes on fewer than 10% of entries. 55/45.** Genuinely uncertain:
  a ~0.35-delta target on a dividend payer could easily sit one strike away, and this is the arm
  most likely to surprise.
* **E4 — the `q = 0` control reproduces the banked contract on > 99% of entries.** Charged as a
  harness check, **not** scored as a prediction.
* **E5 — the IV shift is small and NEGATIVE in sign** (ignoring dividends overstates a call's
  model price, so the solved IV must come in lower to match the market). Direction is arithmetic;
  **magnitude** is the open question and is scored.
* **E6 — `delta85`'s firing rate moves by less than 1pp. 75/25.**

## 7 · Trial cost

Q1, Q2 and Q3 are **measurements of a known defect's magnitude against a pre-committed
materiality bar**, not searches over the data for an effect. Under this project's own convention
a correctness investigation is a `FIXED`-class row and **does not count toward `N`** — inflating
the denominator with bug fixes would understate the evidence rather than overstate it.

**Options `N` unchanged by O21.** If the fix changes a published verdict, that re-derivation is
logged separately and charged then.

## 8 · What would make this register void

* Re-mining, or using any book other than the split-clean banked one.
* Changing the exit policy, the fill model, or the moneyness/DTE bands.
* Letting `q_scheduled` carry a verdict.
* Quoting a Q2 difference without first reporting the `q = 0` reproduction rate.
* Overwriting any original artifact rather than writing a new one.
