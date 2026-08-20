# PREREG DRAFT — S-SEED-3: fundamental momentum — the CHANGE in a name's composite
## Δcomposite as a signal, with the two costumes it must not be killed for wearing later

**DRAFT, Frontier Scout lane, 2026-08-20.** Commit ALONE, markdown only, counters re-read
first. **Trials: 1, equity** (235 → 236 at this writing; hurdle 3.3044 → 3.3057).

## 0. Premise, verified

No row among the 289 in `VALQUO_LEDGER.md` and no item in the 134-item audit set tests a
change-in-score signal: `S8`/`S9` weighted by *staleness* (rejected), `S20`/`S21` changed the
*standardiser* (rejected), the momentum theme is *price* momentum, and PEAD — the earnings-
surprise cousin — was **built, gated and rejected on this panel** (pre-specified at `9323a08`,
result `2f75d60`; it overlapped price momentum and the overlap was demonstrated, not
observed). **The level of the composite is the product; its first difference has never been an
object.**

## 1. Mechanism, with its literature and the literature's status

Underreaction to fundamental *improvement*: Novy-Marx (NBER w20984) argues price momentum is
substantially fundamental momentum — scoring firms on earnings-surprise trajectories subsumes
much of the price effect. Status: published, widely cited, **contested in degree** (later work
finds price momentum retains independent content) — treated here as a hypothesis, per the
standing rule that this project has killed published results before. The local translation:
a name whose *whole fundamental picture* (7-theme composite) is improving may outperform a
name with the same level and a flat or decaying picture, if the market prices levels faster
than trajectories.

## 2. The object, fixed exactly

`Δc(i,t) = c(i,t) − c(i,t−1)` on consecutive rebalance dates (63 trading days), where `c` is
the **shipped** composite under deployed weights (`composite_from_frame`, `B7` convention —
the renormalised object `MB21` identified as the one `S22` actually scores). Requires presence
at both dates: the coverage cost and its survivor tilt are printed, not assumed (expected high
— the panel's median cross-section is stable — but *printed*). One column; nothing else moves.

## 3. Statistic, bars, halves

Primary: **incremental IC** on the seven incumbents, `MB7` gate, **both bases co-primary**
(69-date six-basis / 49-date seven-basis), `split_used="effective"`, coverage printed.
**Declared sign: POSITIVE** (improvement → outperformance). Bar: the X7-calibrated incremental
threshold (re-read at run; 2.71 at current calibration), both halves, ambiguous = NULL.

## 4. Pre-outcome kills (separate pass, read before the arm)

* K1: |per-date mean Spearman| of `Δc` vs the **momentum theme** > 0.60 → WITHDRAWN. The
  composite's inputs move with price (value mechanically de-rates as price rises), so `Δc`
  has a plausible *anti*-momentum or momentum loading either way — the kill is two-sided on
  the absolute value.
* K2: |rho| vs the **banked PEAD column** (`pead.py`, already in-tree) > 0.60 → WITHDRAWN —
  PEAD is rejected on this panel and this register may not resurrect it in a costume.
* K3: |rho| vs the composite **level** > 0.60 → WITHDRAWN (a change that just re-ranks the
  level adds nothing and would re-litigate the product).

## 5. Power (A-11, both numbers)

`MB18`'s design class governs: **≈0.43 SD / 0.51 SD at 80% power (≈0.30 / 0.36 at 50%)** on
the two bases; exact figures from `power_gate.state()` on realized coverage, printed before
the verdict. A NULL means "no trajectory effect as large as the panel's best-ever single
anchor," and is quoted with that sentence.

## 6. Void conditions

1. Any smoothing, lookback longer than one rebalance, or multi-horizon Δ — those are a grid,
   and a grid is a different register with a different price.
2. Reading K1–K3 in the same pass as the arm (`O10`'s process rule).
3. Quoting the IC without the A-11 line; skipping either co-primary basis (`MA58` void-5).
4. Any use of `Δc` in product copy before an ADOPTED verdict — this is research only.

## 7. Prior and expectations

Prior: **~10%** CONFIRMED — the mechanism has literature legs and the object is genuinely
new here, but PEAD's local rejection and the five-body orthogonality wall both point down.
Expectations: (1) K1 does not fire but |rho| lands 0.3–0.6 — 60/40; (2) K2 does not fire —
70/30; (3) verdict NULL — 80/20; (4) if any cell clears, it is the six-basis late half —
55/45; (5) one number contradicts this list — 60/40.

## 8. What it does not do

No weighting change, no theme membership change, no product surface, no holding-period claim
(`S22`/`S23` own those), and no earnings-window claim (the event spine and `X-SEED-2` own
event-time). One column, one bar, both bases, and the record gets the answer either way.
