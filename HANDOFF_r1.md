# HANDOFF_r1 — Factor-adjusted alpha (audit item R1)

Session `r1`, 2026-08-04. Cold session: opened `PROMPT_r1.md` and the R1 entry in
`VALQUO_EDGE_AUDIT.md`, and deliberately did not read the conclusions of the sessions that
produced the inputs (X4, D3, X8) until my own numbers were final.

---

## 1. PRE-COMMITMENT — written before any regression was run

*Everything in this section was written and saved before a single number was computed. It is not
revised below. Timestamp: the commit that first added this file.*

> **The word "alpha" is permitted only if the FF5+MOM intercept is positive with Newey–West
> t > 2.0.** If the intercept is not distinguishable from zero, the honest framing is
> **efficient factor exposure** — a real thing, just a different thing.
>
> **An ambiguous result against that threshold is a NULL, not a judgement call.** t = 1.9 is a
> null. t = 2.05 with a different-but-defensible aggregation choice is a null. There is no
> "directionally positive" verdict available here.

### 1a. The two claims, both written in advance

**CLAIM A — if the FF5+MOM intercept is positive with NW t > 2.0:**

> "Valquo's top decile has produced returns that the standard five Fama–French factors plus
> momentum do not explain. After controlling for market, size, value, profitability, investment
> and momentum exposure, the model's selection adds an annualised intercept of X% (t = Y) over
> 1998–2026. That residual is what the model is actually for: it is not reachable by holding a
> factor blend, and its most likely source is the `institutional` (13F) theme, which has no
> Fama–French analogue, plus the interaction structure of combining seven themes rather than
> sorting on one."

**CLAIM B — if the intercept is not distinguishable from zero (NW t ≤ 2.0), or is negative:**

> "Valquo delivers diversified, well-documented exposure to the standard equity risk premia —
> value, quality, momentum, size, investment discipline — efficiently and transparently, with a
> public forward track. Its returns are explained by factor exposure rather than by security
> selection the factors miss. That is a legitimate product and it is stated plainly here rather
> than dressed up: the category is full of tools claiming secret alpha, and a tool that tells you
> exactly which known premia you are buying, and proves it with a regression, is more defensible
> than the alternative. **The word 'alpha' does not appear in product copy.** The remaining edge
> is in construction, cost, tax and capacity — not in finding more signals."

### 1b. Pre-registered specification (fixed before running)

- **Primary object:** the headline's own series, `top − ew` = top-decile 63d return minus
  equal-weighted-universe 63d return, per rebalance date. `top_decile_alpha` is exactly
  `4 × mean(top − ew)`, so this is the number under audit and nothing else.
- **Secondary objects:** (i) top decile in excess of the risk-free rate — the long-only *book*, the
  thing a user actually holds; (ii) top-decile minus bottom-decile — the cleaner statistical object,
  per R1 method step 6.
- **Primary model:** `r_t = α + β₁MKT + β₂SMB + β₃HML + β₄RMW + β₅CMA + β₆UMD + ε`.
- **Secondary model:** Hou–Xue–Zhang q-factor — `MKT, ME, I/A, ROE` (q4, as the audit specifies).
  q5's `EG` reported as an appendix only; it is not the pre-registered model.
- **Inference:** Newey–West HAC, **lag 1**, as the audit specifies. Windows are adjacent and
  non-overlapping, but factor spreads are autocorrelated.
- **Aggregation:** daily factors compounded to the panel's own 63-trading-day windows, on the
  panel's own date grid, `(d_i, d_{i+1}]`. No look-ahead: every factor day used lies strictly
  inside the window whose return it is being matched to.
- **Robustness that will be reported whatever it says:** simple-sum aggregation instead of
  compounding, and the sample excluding the first 37 rebalance dates (audit **B6**: the panel's
  first third has an inverted universe). If the verdict differs between the pre-registered
  specification and either robustness cut, **the result is a null** — the pre-registered spec does
  not get to win a disagreement.

### 1c. Expected outcome, recorded in advance

Most of the +11.9% will not survive. RMW should absorb much of `quality` (the strongest theme),
SMB should absorb `size`, CMA should absorb `capital_discipline` (net issuance). What survives, if
anything, most likely comes from `institutional` and from the interaction structure of combining
seven themes.

---

## 2. Result

*(written after section 1 was committed; see below)*
