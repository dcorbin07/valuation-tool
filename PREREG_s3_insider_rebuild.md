# PRE-REGISTRATION — S3: rebuild the insider score

**Committed before any variant has been scored.** Written after a premise check against the code
and the banked corrected panel (§1), which is reported here in full because two of its findings
contradict the audit and one contradicts my own starting hypothesis. No variant's IC, alpha or
gate result exists at this commit.

Ledger row `S3`, `src=auto` — *"a lead, not a fact"*. S21 is the precedent: an `auto` row
proposed behaviour the code already shipped, so the first job is to check the item against the
code rather than to believe it.

---

## 0. Scope, and what is NOT in this register

This register covers **S3 only**.

`S25` (point-in-time sector map) was also worked this session and is **deliberately register-free
and charged zero trials**. Everything it returns is a fact about what data exists and what the
code reads — obtainability, consumption sites, and the numeric spread of two sector-keyed
constants. None of it is a hypothesis tested against a threshold, so on session 8's precedent
(declining to run a test that cannot resolve keeps the denominator) it charges nothing. Its
findings are in `HANDOFF_edge_audit.md` session 29 §1.

---

## 1. PREMISE CHECK — what the shipped construction actually does

Five facts, all measured before this register was written. **Three of them were not known to the
audit and one refutes my own opening hypothesis.**

**(a) One of the audit's own items is ALREADY FIXED, by B26.** The audit says
`_insider_score_at` uses `searchsorted(dts, hi, "right")`, so a Form 4 dated exactly `as_of` is
usable at that day's close. The shipped code is `side="left"`
(`fundamental_panel.py:794-795`) with a comment naming B26 as the fix. **That half of S3 is
closed and is not re-tested here.**

**(b) THE FORMULA IS DUPLICATED.** It appears at `fundamental_panel.py:737` (`_insider_score`,
the row-iterating fallback) and at `:800` (`_insider_score_at`, the prepped fast path). The two
are character-identical today, and the B26 comment in each explicitly says the paths must agree.
**Any variant must change BOTH or the fallback silently scores a different book** — this is the
B7 defect class, and it is the single most likely way this item ships a bug.

**(c) `insider` IS NOT Z-SCORED.** It is the one theme built as a fixed affine map,
`(insider_score - 50) / 25` (`factors.py:281-282`), documented as a deliberate asymmetry at
`factors.py:84`. Every other theme is a mean of cross-sectional z-scores. **So the tanh's
saturation is not normalised away per date, and the audit's saturation complaint is at least
structurally coherent** — which it would not be for a z-scored theme, where a monotone transform
cannot move a rank IC at all.

**(d) MY OWN OPENING HYPOTHESIS IS REFUTED, AND IT IS RECORDED BECAUSE IT WOULD HAVE FRAMED THE
WHOLE ITEM WRONGLY.** From (c) I expected the affine map to leave `insider` with a
cross-sectional dispersion well below the z-scored themes' 1.0, making its EFFECTIVE weight far
below the nominal 0.125. **Measured on the banked corrected panel (113,945 rows, 69 dates), the
opposite is true:**

| theme | mean per-date sd | coverage |
|---|---|---|
| quality | 0.5020 | 97.9% |
| value | 0.7282 | 100.0% |
| momentum | 0.8497 | 98.3% |
| institutional | 0.8972 | 71.7% |
| **insider** | **0.9600** | **83.1%** |
| size | 1.0003 | 100.0% |
| capital_discipline | 1.0003 | 96.8% |

`insider` sits at **0.9600 against 0.8296 averaged over the other six**, i.e. about **116% of its
nominal weight, not less**. The multi-input themes are the compressed ones, because a mean of
imperfectly-correlated z-scores has sd below 1 (`quality`, ten inputs, is the most compressed at
0.50). **`insider` is not an under-weighted theme and no part of this register may claim it is.**

**(e) `insider` IS THE ONLY THEME WITH A MATERIALLY NON-ZERO MEAN: −0.1031**, against ~0.000 for
every other theme. That is the affine map showing through — net selling dominates, so the typical
name scores below 50. Combined with **83.1% coverage** and the composite's present-weight
renormalisation (the B7 fix), a name that HAS an insider score receives a small systematic
negative tilt that a name WITHOUT one does not. **This is a data-availability effect wearing a
signal's name — S10's failure mode exactly — and it is measured as a diagnostic in §5, not
assumed.**

---

## 2. THE INSTRUMENT — the three variants, exactly

Incumbent (unchanged, both sites):

```
score = clip( 50 + 40*tanh(net / 5e6) + min(10, 2*buys),  0, 100 )
```

where `net` is the signed sum of `transactionshares * transactionpricepershare` (falling back to
`transactionvalue`) over the trailing 90 days by filing date, and `buys` counts positive rows.

* **S3a — DROP THE BONUS.** `score = clip( 50 + 40*tanh(net / 5e6), 0, 100 )`.
* **S3b — SCALE BY MARKET CAP.** `score = clip( 50 + 40*tanh( (net / marketcap) / 0.001 ), 0, 100 )`,
  i.e. net insider dollars as a fraction of market cap, with 10 bps as the tanh scale. **The scale
  constant 0.001 is a convention and is fixed here, before any measurement.** It cannot change the
  variant's cross-sectional ORDERING (any positive scale gives a strictly monotone map of
  `net/marketcap`); it changes only how quickly the map saturates, which is what reaches the
  composite. A row with missing or non-positive `marketcap` yields **None**, the same as any other
  name with no computable score — never 50, never 0.
* **S3c — SPLIT INTO TWO INPUTS.** The theme becomes the mean of the z-scores of two inputs:
  `insider_net = tanh(net / 5e6)` and `insider_breadth = buys`. This makes `insider` a
  multi-input, genuinely z-scored theme like the others, so per (d) it will almost certainly
  DISPERSE DIFFERENTLY from the incumbent; that is a property of the change, not a defect.

**A name with no insider rows scores `None` in every arm, exactly as today.** No arm may impute a
neutral 50 for missing data — that would convert an availability gap into a signal, which is (e)'s
failure mode deliberately introduced.

---

## 3. THE GATE — the shipped one, at the already-committed margins

Primary: **`holdout_compare_panels`**, the same shipped gate at the same pre-committed margins
used by `SECTOR-NEUTRAL-B6`, `S20` and `S21` — **B beats A by ≥ +0.25 long-short *t* AND
≥ +100 bps top-decile alpha, in BOTH split directions, boundary date embargoed.**

* **ONE weighting: the deployed flat 1/7.** No grid, no sweep. The in-search +8.43%/yr →
  locked hold-out −0.04%/yr failure has been paid for once and is not being re-bought.
* **ONE panel build, four scorings, provably identical rows.** The variants are functions of the
  same prepped insider arrays, so all four scores are computed in the same pass and the arms
  differ in nothing else. A control asserts identical `(date, ticker)` key sets across arms.
* Verdict per variant: **ADOPT-ELIGIBLE** iff it clears both margins in both directions;
  otherwise **REJECTED**. Ambiguous is a **NULL** (`RUN_RULES` A6).

### 3.1 Why the audit's own threshold is NOT the primary

The audit's bar is *"theme IC t clears +1.0 AND the composite improves through
`holdout_compare_panels` in both directions"*. The second half is adopted verbatim. **The first
half is recorded as a diagnostic and may never carry a verdict, for two independent reasons fixed
here in advance:**

1. **+1.0 is far below the calibrated floor.** X7 calibrates the theme IC *t* bar at **2.71**, and
   measured that **39% of pure-noise draws** produce at least one theme at *t* ≥ 2.0 — because
   eight themes are tested and the bar is applied to whichever looks best. A variant clearing
   +1.0 is not evidence of anything.
2. **Theme IC is the wrong instrument for a construction change, by this project's own repeated
   finding.** P6.3 (robust z-scores halved the long-short *t* while every theme IC stayed flat),
   X3 (theme IC does not predict marginal contribution — `size` has the worst IC and carries the
   composite's significance) and S20/S21 (two arms moved alpha by −3.49pp and +2.43pp while no
   theme IC moved as much as 0.4 of a *t*). **S3 is a construction change. The standing rule
   applies.**

---

## 4. WHAT ADOPTION WOULD COST, fixed before the result

Adoption is a **VINTAGE EVENT** — it changes the composite users receive and therefore closes the
current vintage and opens the next, resetting the five-year forward clock for zero statistical
gain (Rule 6). **The current vintage is DERIVED, never assumed** (`PT-GAPDUE`): as of this
commit `track_meter.current_vintage()` returns **vintage 3, opened 2026-08-11**, so an adoption
here would open **vintage 4**.

Therefore, exactly as S20/S21 fixed in advance: **an eligible arm is recorded ELIGIBLE, not
adopted.** Nothing in `settings.py`, `factors.py` or the live scoring path changes on this
register's result. Whether to spend a vintage is Don's call on the evidence.

---

## 5. CONTROLS — all read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record.** The incumbent arm must return
  `top_decile_alpha` 0.07174142332098163, `long_short_tstat` 2.8360640685320595, HAC
  2.6199121240414884 and `monotonicity` −0.8909090909090909. **The run ABORTS before any variant
  is read if it does not.**
* **C2 — identical rows.** All four arms share one `(date, ticker)` key set, asserted, not assumed.
* **C3 — the incumbent's insider column is bit-identical to the banked panel** over the shared
  keys, proving the rebuild reproduced the shipped construction before any variant is trusted.
* **C4 — no arm is inert.** Each variant's cross-sectional rank correlation against the incumbent
  is reported; an arm correlating ~1.000 changes nothing and its verdict is meaningless.
* **C5 — BOTH FORMULA SITES AGREE.** `_insider_score` and `_insider_score_at` must return the same
  value for the same input in every arm, over a randomised fixture. This is premise-check (b), and
  it is a control because the fallback path is the one nobody exercises.
* **C6 — coverage first, per the COVERAGE RULE.** Each arm's insider coverage is reported before
  its verdict. S3b can only LOSE coverage relative to the incumbent (it additionally needs
  `marketcap`), and if it loses materially its comparison is partly a universe change.
* **C7 — THE AVAILABILITY DIAGNOSTIC, from premise (e).** The forward-return IC of the pure
  INDICATOR *"this name has an insider score at all"* is measured and reported. **If the indicator
  alone predicts returns, then part of every arm's measured effect — incumbent included — is a
  data-availability artefact rather than an insider signal.** Reported whatever it says;
  exploratory, no verdict.

---

## 6. EXPECTATIONS, written before any arm was scored

Recorded because this project's directional calls keep being wrong, which is exactly why they are
written down first.

1. **No variant clears the gate in both directions — 70/30.** Every construction change put
   through this gate since B6 has failed it, and the theme's own IC is not distinguishable from
   zero in either direction.
2. **S3b is the best of the three — 60/40.** The audit says so and the literature agrees; scaling
   by size is the only variant that changes what the score MEANS rather than trimming a term.
3. **S3a moves the composite least — 65/35.** The `min(10, 2*buys)` term is bounded at 10 points
   against the tanh's ±40, so dropping it is a small perturbation of the same ordering.
4. **The availability indicator (C7) has a non-zero IC — 55/45.** Insider filings cluster in names
   with more coverage and more liquidity. Low confidence, and it is the finding I most want to be
   wrong about.
5. **At least one arm's theme IC *t* clears the audit's +1.0 while its gate verdict is REJECT —
   60/40.** That dissociation is the point of §3.1 and would demonstrate the bar's uselessness on
   this panel rather than merely asserting it.
6. **No arm's rank correlation against the incumbent falls below 0.90 for S3a — 70/30**, and
   **S3b's falls below 0.90 — 65/35.**

---

## 7. TRIAL COST

**Three arms, one weighting, no grid: equity `N` 158 → 161.** Charged whatever the verdicts are,
including if all three reject — running and failing does not refund the search (session 26's
precedent, where a voided verdict was still charged in full).

The premise checks in §1, the C7 diagnostic and the S25 work charge **nothing**: they measure what
the code and the data already are, and test no hypothesis against a threshold.

`BACKTEST_RESULTS.json` is re-run from a clean tree so the artifact carries the honest
denominator, per the standing rule that leaving it stale flatters the Deflated Sharpe.

---

## 8. WHAT THIS REGISTER DOES NOT DO

* It does **not** re-open zeroing `insider`. That was tested and came back `not_replicated`, and
  the audit's own note is that a theme covering 83% of rows with no Fama–French analogue deserves
  one honest attempt at repair before deletion. **If all three variants reject, zeroing becomes a
  live proposal again — but it is a separate register with its own trial charge, not a fallback
  conclusion of this one.**
* It does **not** touch the `bulk.prepare_insiders` sign-precedence hazard the audit names
  (`transactionvalue` first, which mis-signs every sale if that column is unsigned). The panel uses
  the safe path. **It is verified as still unused and reported, not repaired** — switching loaders
  would silently invert the theme, and that is a change nobody should make inside a register about
  something else.
* It does **not** change `min(10, 2*buys)`'s cap, the 90-day lookback, or the 5e6 scale in the
  incumbent arm. Those are the incumbent; varying them too would be the grid this register forbids.
