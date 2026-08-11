# PREREG — LA1 and LA3 repair (cold audit `VALQUO_LIVE_AUDIT.md`)

Committed **before any code changes**, so the diagnosis, the detection rules, the two new
constants and the expected values are all fixed in the git history before anything moved.
Same discipline as `PREREG_v2f_live_coverage.md` and `PREREG_v2g_live_theme_sources.md`.

---

## 1. LA1 — DIAGNOSIS, ESTABLISHED BEFORE THE FIX

**The observable, verified live 2026-08-10 against `https://valquo.co/api/hotstocks?top=3`:**

```
scan_date 2026-08-08 · scored 594
KSPI  price 90.30  fair_value 274.13  method "blended"  withheld None   ratio 3.04x
SYF   price 78.59  fair_value 204.38  method "dcf"      withheld None   ratio 2.60x
STT   price 184.68 fair_value 220.21  method "dcf"      withheld None   ratio 1.19x
```

**THE DECISIVE FACT IS THAT RANKS 2 AND 3 ARE `dcf`.** The DCF pass ran, reached the network,
and wrote a real valuation for its neighbours. It produced **nothing at all** for rank 1 — not a
value, not a refusal. So the candidate explanations in the brief can be discriminated without
guessing:

* **NOT a stale snapshot predating the Bug A/B fix.** The fix is present in this scan's own
  output: two of the top three rows carry `fair_value_method: "dcf"`, which only
  `_enrich_with_dcf` writes.
* **NOT deploy lag.** Same reason — the fixed code demonstrably ran on this scan.
* **NOT a scan route that skips `record_refusal`.** The route that produced ranks 2 and 3 is the
  same single call, `_enrich_with_dcf(rows[:run_dcf_top], cfg)`.

**The engine's verdict for KSPI reproduces deterministically today** (`value_ticker('KSPI',
CONFIG)`): price 94.00, financial currency KZT, `fx_rate` 0.0021434847731143236,
`fx_unresolved` False, `blend.value` None, `withheld_value` 530.2319195351978,
`base_fair_value` None, **`decide(...)` → publish False, ratio 5.640765101438275, reason set**.
So `record_refusal` *would* fire, and did not.

**THE PATH, and it is the one the audit predicted: `_enrich_with_dcf`'s documented fail-open
(`except Exception: continue`, `screen.py:395`) swallowed a raise for this row and left no
trace.** KSPI is the top-ranked name that needs an extra network hop its neighbours do not — a
KZT→USD rate — and the upstream feed is free and rate-limited. `estimate_fair_values` then read
the untouched `fair_value: None` as "no DCF computed yet" and substituted a peer estimate,
tagging it `blended`.

**A SECOND, DISTINCT HOLE IS RECORDED HERE BECAUSE IT IS REACHED BY THE SAME ROW SHAPE AND IS NOT
AN EXCEPTION AT ALL.** `publication.decide(None, price)` returns `publish=False` with an
**empty reason** — deliberately, "*Not a refusal — there is simply nothing to publish*". So a
name whose model yields no value **and** raises nothing also silently falls through to an
unchecked peer estimate. Both holes share one signature, and that signature is what §2 detects.

## 2. THE DETECTION — fixed here, before it is written

Two rules, evaluated on **every scan**, over the rows the product can actually serve.

**D1 — THE SIGNATURE OF LA1: `asked_but_silent`.** A row inside the DCF window that carries
**no `fair_value`, no `fair_value_withheld`, and no engine error recorded** was asked and
answered nothing. That is KSPI's exact state, and it is detectable without knowing why.

**D2 — THE BAND INVARIANT the audit says is missing: `band_breach`.** A **served** row with
`fair_value / price > FV_BAND_HIGH` (5.0) and `fair_value_withheld` falsy. Nothing the product
publishes may exceed the band unwithheld, whatever produced it.

**D2 WOULD NOT HAVE CAUGHT KSPI AND THAT IS STATED HERE RATHER THAN DISCOVERED LATER.** KSPI's
*served* ratio is 274.13/90.30 = **3.04x, comfortably inside the 5.0 band** — the audit says so
itself. D2 closes a different, real hole (an implausible number reaching the public surface); D1
is the one that closes LA1. Reporting D2 alone as "the detection for LA1" would be false.

**Both are LOUD BY DEFAULT and neither may be silenced to make a run green** (RUN_RULES 5):
they ship in `health.publication_audit`, they print in the scan log, and `scripts/ci_scan.py`
prints an explicit `LEAK` banner naming every offending ticker. **The scan is NOT aborted** — a
detector that stops the daily scan would take the product down over a data-quality signal, which
is a worse failure than the one it reports.

**Expected values, committed before the run.** On the current production snapshot as re-scanned:
`band_breach` = **0** (nothing served today exceeds 5.0x unwithheld), `asked_but_silent` ≥ **1**
and includes **KSPI** if and only if the fail-open recurs; after the §3 repair, KSPI must appear
in neither list and must serve `fair_value_withheld: true`.

## 3. THE LA1 REPAIR — three changes, each with a stated direction

1. **Count the fail-opens.** `_enrich_with_dcf` records an `errors` tally and the exception type
   per ticker; `_screen_refusals` reports `errors` beside `screened` and `refused`. Nothing about
   the fail-open policy changes — a fetch failure still may not blank hundreds of fair values —
   but it stops being invisible.
2. **Retry a raise once, then re-ask.** A transient fetch failure is exactly what a single retry
   is for. Rows in the DCF window that still yield nothing are then put through the
   refusal-only screen, which is the cheap pass that exists for precisely this question.
3. **Close the counter hole.** `_screen_refusals` currently runs on `rows[run_dcf_top:...]`, so
   the top `SCAN_DCF_TOP=12` rows — the most-read on the site — are excluded from the counter by
   construction. The screen is extended to cover any row in the DCF window that came back
   silent. It is NOT extended to rows that already hold a good DCF value: re-fetching those buys
   nothing and doubles their cost.

**The `fair_value` a non-refused row already holds is never changed by any of this.** This is a
leak fix, not a product change.

## 4. LA3 — THE DENOMINATOR

`summarize()` sets `days = len(series)` — rows written, not trading days elapsed — and uses it
as the annualisation exponent (`index_track.py:492-493`). `_daily_returns` chains
cumulative-since-inception levels, so a missing day yields a multi-day "daily" return.

**THE FIX: annualise on ELAPSED TRADING DAYS.**
`elapsed = |{trading days d : inception < d <= last_recorded_date}|`, falling back to
`|{trading days d : first_row_date <= d <= last_row_date}|` when no inception is recorded. Both
definitions coincide, and both equal `len(series)`, on a gapless series — so **the clean case is
bit-identical and that is a pre-committed check, not a hope.**

**THE GATE DELIBERATELY STAYS ON RECORDED ROWS.** `MIN_LIVE_DAYS` and `MIN_SHARPE_DAYS` continue
to count rows. Moving them to elapsed time would let a gappy track reach the floor **sooner** —
the flattering direction, and it would advance the public "backtested → live" posture on the
strength of days nobody recorded. Rows are the conservative denominator for a gate and the wrong
one for an exponent; those are different jobs and the fix separates them.

**SHARPE.** Each chained observation spans `elapsed / n_obs` trading days on average, so the
annualisation factor becomes `sqrt(TRADING_DAYS · n_obs / elapsed)` in place of
`sqrt(TRADING_DAYS)`. On a gapless series the ratio is exactly 1 and the figure is unchanged.

**NEW CONSTANT, COMMITTED HERE: `MIN_COVERAGE_FOR_SHARPE = 0.5`.** Below half the expected
trading days recorded, the chained series is mostly multi-day and the i.i.d. rescaling above is
doing more work than the data supports, so **the Sharpe is withheld (`None`) rather than
corrected**. Chosen structurally — at coverage < 0.5 the typical observation spans more than two
trading days, i.e. the "daily" series is no longer daily — not tuned to any observed value. The
annualised alpha is **not** subject to this floor: it rests on two cumulative endpoints and a
known elapsed window, which a gap does not corrupt.

`coverage` and `elapsed_trading_days` ship in the payload beside the figures, so a reader can see
the denominator rather than trust it.

## 5. EXPECTED VALUES FOR LA3, COMMITTED BEFORE MEASURING

Reproducing the audit's own construction — one synthetic year, identical underlying daily
returns, identical final cumulative levels, thinned three ways:

| series | audit's reported `ann_alpha` | audit's `sharpe` | **expected after the fix** |
|---|---|---|---|
| complete, 252 rows | 11.08% | 0.54 | **bit-identical: 11.08% / 0.54** |
| every 2nd day (126 rows) | 24.05% | 0.83 | ann_alpha ≈ **11.08%**; sharpe ≈ 0.54 |
| every 3rd day (84 rows) | 39.21% | 1.03 | ann_alpha ≈ **11.08%**; sharpe ≈ 0.54 |

**The alpha rows are an EQUALITY and the Sharpe rows are an APPROXIMATION, and the difference is
not cosmetic.** All three thinnings end at the same cumulative level over the same elapsed
window, so the corrected exponent must reproduce the complete series' alpha **exactly**. The
Sharpe cannot: thinning changes which returns are realised, so the corrected figure is expected
to be close but not equal, and any residual gap is reported rather than tuned away.

**PASS/FAIL, pre-committed:** the corrected `ann_alpha` must match the complete series to within
**1e-9** on both thinnings. The corrected `sharpe` must land within **±0.15** of 0.54, against
errors of +0.29 and +0.49 today. A miss on either is reported as a miss.

## 6. WHAT VOIDS THIS

* Changing `MIN_COVERAGE_FOR_SHARPE`, the D1/D2 rules or the §5 tolerances after seeing a number.
* Moving `MIN_LIVE_DAYS` or `MIN_SHARPE_DAYS` onto elapsed time (§4) — that is the flattering
  direction and is out of scope here.
* Silencing D1 or D2 to make a scan green.

## 7. TRIAL COST

**ZERO.** No hypothesis about returns is tested and no arm is selected — these are correctness
repairs to a published statistic and a leak detector. Equity `N` stays **135**. LA3 changes the
*value* of a figure that is currently withheld (`days = 2`, far below the floor), so no published
number moves today; it moves the number that would otherwise have been published later.
