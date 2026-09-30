# PREREG — W-6, CRSP DELISTING CROSS-CHECK OF THE SURVIVORSHIP MASK

**Audit session: AUDIT 6. Item: MC13 / `W-6`. Class: CONTROL (zero trials, zero dollars).**

Committed **ALONE**, markdown only, zero `.py`, before any comparison exists. A strict git
ancestor of every commit that computes an agreement rate.

`W-6` has **no ledger row and has never run**. `WRDS-CENSUS` and `W-3b` are DONE and pushed.

---

## 0. WHAT THIS IS

A **control**, not a hypothesis. It asks whether the survivorship mask the panel is built on
agrees with CRSP's own delisting record for the same securities. Under `MB1-SEL` a control can
only ever **BLOCK** a finding, never produce one, so it **charges zero trials** and
**ADOPTS NOTHING**. A failing bar licenses a NEW correction register with its own charge and
Don's decision; it does not authorise a repair here.

`by_domain` at this commit, re-read from `research_log.detail()`:

```
{'equity': 248, 'options': 310, 'unified': 0, 'infra': 20}   rows_fixed_not_counted = 85
```

**AGREEMENT IS NOT PROOF, AND THIS IS STATED FIRST BECAUSE IT BOUNDS EVERY POSITIVE RESULT
BELOW.** Sharadar's ACTIONS layer and CRSP's `dsedelist` both ultimately derive from the same
exchange and regulator notices. Two vendors reading one upstream source and reaching the same
answer establishes that **neither has mangled the transcription**; it does not establish that
the underlying notice was right, nor that a delisting absent from both actually did not happen.
So a PASS here means *"the mask is not independently contradicted"* and never *"the mask is
correct"*.

---

## 1. THE OBJECT, FIXED NOW

For **every panel name carrying an ACTIONS delisting event dated 2009-01-15 → 2024-12-31**, the
CRSP `dlstcd`, `dlstdt` and `dlret` for the same security.

**CRSP is cut at 2024-12-31 on this account.** The panel runs to 2026-01-28, and the five
rebalance dates beyond the cut are **UNVERIFIABLE BY CONSTRUCTION** and are **listed, never
scored** — measured from the panel before this register was written:

```
2025-01-27   2025-04-28   2025-07-29   2025-10-27   2026-01-28
```

Reporting them as agreement or as disagreement would both be wrong. **`W-28` paid for exactly
this**: it read a vendor cut-off as a coverage gap, saw per-date coverage of exactly zero on
2025-26 rows, and had to repair the instrument mid-item. The cut is honoured here in advance.

Panel shape, measured: **113,945 rows, 2,531 names, 69 dates, 2009-01-15 → 2026-01-28.**

## 2. THE JOIN — DATED, NEVER A DICTIONARY

`ticker → permno` scoped **BY DATE**, through CRSP's own dated name history, by **IMPORTING
`W-3b`'s interval scoping** (`valuation/edge/adv.py::ticker_permno_intervals` and `permno_on`)
rather than reimplementing it — `B7`, and the function's own docstring carries the reason:
**1,053 of our 2,271 matched tickers map to more than one permno**, so an undated
`{ticker: permno}` dictionary attributes one company's record to another **silently**.

The last interval is treated as **OPEN-ENDED**, which is `adv.py`'s own `OPEN_END` behaviour and
is what stops CRSP's 2024-12-31 cut reading as a name that stopped existing.

## 3. THE BARS, FIXED NOW AND NOT RELAXABLE

* **V1 — flag agreement.** A panel name flagged delisted by ACTIONS must also carry a CRSP
  delisting record: **≥ 95% of matched names.**
* **V2 — date agreement.** `dlstdt` within **±3 calendar days** of the ACTIONS event date, on
  **≥ 95% of matched events.**
* **V3 — terminal-return agreement.** Within **±0.01 absolute on the return**, on **≥ 90% of
  matched events.**

  **The tolerance is named with its reason, as the task requires, and the reason is measured on
  the incumbent rather than chosen.** The panel's own **median absolute 63-day forward return is
  0.107761** (p25 0.048450, p75 0.202013). ±0.01 is therefore **9.3% of a typical quarterly
  move** — an order of magnitude below it — so a disagreement exceeding it is economically
  meaningful rather than a convention artefact. It has to be a tolerance and not equality
  because the two quantities are **constructed differently**: CRSP's `dlret` is an adjusted
  delisting return that can include a final liquidating distribution, while the panel's terminal
  value is a last traded close (`E-5`: *"a DELISTED name has a TERMINAL value"*). Exact agreement
  is not expected and requiring it would manufacture a failure.

**Ambiguous against a pre-committed bar is a NULL** (`RUN_RULES` A6), never a judgement call.

## 4. THE DELIVERABLE IS THE DISAGREEMENT SET, EITHER WAY

Whatever the bars say, the disagreement set ships, **split by cause** on `W-3b`'s own taxonomy
(`W3B_EXECUTION_RECORD.md:137-145`), because a bare rate cannot distinguish two causes that
imply **opposite actions**:

| | meaning |
|---|---|
| **COVERAGE GAP** | CRSP has no dated interval or no record for that security at all, so there was never a counterpart to agree with |
| **REAL CONFLICT** | CRSP has a record and it disagrees |

And, separately: **the count of panel rows whose terminal return would CHANGE under CRSP's
`dlret`, reported BY HALF, on the EFFECTIVE dates** — effective meaning the dates that survive
the 2024-12-31 cut.

## 5. KILLS

**K1 (free, and read FIRST).** If the **dated link reaches fewer than 80%** of the panel names
carrying an ACTIONS delisting event, the item **STOPS** and reports the coverage figure as its
result. `W-28`'s closing lesson binds: a pre-committed bar may not be relaxed after watching it
fail.

**K2.** If the **late half holds fewer than 16 effective event-dates** after the cut, the
both-halves split is **UNAVAILABLE** and is reported as unavailable rather than computed on a
thin cell. 16 is the shipped `min_dates` floor, reused verbatim rather than chosen here.

## 6. CONTROLS — own pass, banked BEFORE the comparison

**C1 — fidelity, and it ABORTS.** The panel must reproduce the published record before anything
is joined to it: `top_decile_alpha` **0.071741**, long-short naive *t* **2.8360**, HAC *t*
**2.6199**, monotonicity **−0.8909**, via `quantile_backtest` under the deployed seven themes at
0.125 each. **If it does not reproduce, the item aborts and no agreement rate is computed** — a
cross-check against a panel that is not the published one measures nothing.

**C3 — every agreement rate asserts the number of events it compared** (`MB21`, whose own C1
once scored a perfect 0.000e+00 on an empty frame by comparing nothing). A rate over zero events
is reported **VACUOUS**, never PASSING.

**C6 — the panel names with no CRSP interval are counted and LISTED, never read as agreement.**
Silence is not consent: a name CRSP cannot locate is a coverage gap and belongs in §4's first
column.

## 7. POWER (A11)

**No MDE applies — no return statistic is computed; the pre-declared bars are agreement rates.
Equity N 248, hurdle 3.3207, unchanged by this file.** Effective coverage is printed anyway per
`RUN_RULES` PART A rule 10.

## 8. EXPECTATIONS, WITH ODDS

1. **V1 ≥ 95%** — 60/40.
2. **V2 ≥ 95%** — 55/45.
3. **The disagreement set is non-empty and contains at least one moved terminal return** —
   70/30.
4. **K1 does not fire** — 80/20.

## 9. VOID CONDITIONS

1. A bar in §3 or §5 is relaxed, or a second tolerance or second bar is introduced, after
   reading the data it applies to.
2. Any raw CRSP row leaves `D:\wrds` — nothing under it, and no `data/` or `*.pkl`, is
   committed.
3. The five post-cut rebalance dates are scored rather than listed.
4. An undated `{ticker: permno}` map is used anywhere in the join path.
5. Any agreement rate is reported without the event count it was computed over.
6. `by_domain` is not bit-identical before and after.
7. A sweep, `scripts/placebo.py`, or the backtest is run.

## 10. WHAT THIS DOES NOT DO

It adopts nothing, repairs nothing, and re-derives no published figure. `O11`-style: a control
licenses no change. If a bar fails, the consequence is a **new register**, with its own trial
charge and Don's decision — not an edit here.
