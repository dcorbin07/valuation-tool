# PRE-REGISTRATION — O26, raise the per-bucket floor

**Committed before any measurement code for this item exists**, in the same commit as
`PREREG_o21_dividends.md` and no `.py`.

Item **O26** in `VALQUO_LEDGER.md` (`OPEN`, src=auto, "no mention anywhere in the corpus"), so
the scope below is derived rather than inherited. Options domain.

---

## 1 · What the floor is, and what it is for

`options_tracker.MIN_CLOSED_PER_BUCKET = 30` is a **hard gate before any criterion may be tuned
on a bucket**. `options_universe.py` imports it and uses it in four places — `tier_report`'s
`enough_to_judge` (`:626`) and three subgroup/split gates (`:870`, `:876`, `:913`, `:930`).

**Its own comment states the justification, and that is what makes this item testable:**

> *"Options outcomes are noisy and heavy-tailed: with ten trades a single triple-up decides the
> sign of every statistic. 30 is not a magic number, it is 'enough that one lucky contract cannot
> flip the verdict'."*

**So the floor has a stated purpose and has never been measured against it.** This register does
not ask "is 30 aesthetically low"; it asks **at what bucket size the floor's own stated property
actually holds**. That is the whole design, and it is why the primary statistic below is a
sign-flip probability rather than a correlation.

## 2 · State of knowledge when this was written, disclosed

* The constant is **30**, defined at `options_tracker.py:37`.
* The live bucketings gated by it are **cap tier** (`mega`/`large`/`mid`/`small`) and, adjacently,
  **entry year**.
* Nothing else. **No sign-flip probability, no half-split, no candidate floor has been computed.**
* From O12, measured yesterday and relevant here: the per-trade distribution is a barbell —
  median **−52.22%**, mean **+3.27%**, max **+782%** — which is exactly the shape the floor's
  comment is worried about.

## 3 · The primary statistic, fixed now

For a bucket of `n` trades with per-trade returns `R`:

> **`P_flip(n)` = the probability that removing the SINGLE most extreme trade flips the sign of
> the bucket's mean expectancy.**

"Most extreme" is `argmax |R_i − mean|`, chosen **before** looking at which direction it moves
the mean, so the statistic cannot be steered. This is the literal operationalisation of *"one
lucky contract cannot flip the verdict"*.

Estimated by drawing buckets of size `n` **with replacement from the split-clean alert book**,
**5,000 draws per `n`**, over the candidate grid

> **`n ∈ {10, 20, 30, 40, 50, 75, 100, 150, 200, 300}`** — fixed now, not extended after seeing
> the curve.

**Secondary, and independent of the primary:** half-to-half **sign agreement** of bucket
expectancy — split each drawn bucket by calendar median and ask whether the two halves agree in
sign. A floor that passes the primary but not this is reported as passing one and not the other.

## 4 · The bar and the verdict rule, fixed now

> **`FLOOR* = the smallest n on the grid with P_flip(n) ≤ 0.05`.**

5% is chosen to match the conventional α this project already uses for its calibrated bars, and
is committed here before the curve exists.

| verdict | condition |
|---|---|
| **RAISE to `FLOOR*`** | `FLOOR*` computed independently on the early and late calendar halves agrees to **within one grid step**, and `FLOOR* > 30` |
| **KEEP 30** | `FLOOR* ≤ 30` on both halves |
| **NULL** | the halves disagree by more than one grid step, or either half has no `n` on the grid clearing 0.05 |

**Both halves are required because a verdict is claimed** — this is the user's constraint and
session 7's rule. **Ambiguous is a NULL and a near miss is a NULL.**

**A NULL means the constant stays at 30.** The failure direction is "keep the shipped value",
never "adopt an unvalidated one".

## 5 · What this may and may not change

* It may change **`MIN_CLOSED_PER_BUCKET`**, a research gate that decides whether a subgroup is
  *reported as judgeable*.
* **It may NOT change any live trading behaviour, any exit policy, or any scoring path.** Raising
  the floor makes the project **more** conservative about which subgroups it will read — it
  cannot make a book trade differently.
* **It does not re-open any verdict.** If raising the floor would newly disqualify a subgroup the
  record has already quoted, **that must be reported explicitly** rather than silently applied —
  a floor change that retroactively unpublishes a finding is a finding in its own right.

## 6 · Expectations, written before any of it runs

* **E1 — `FLOOR*` is materially above 30, in the 75-150 range. 70/30.** With a median of −52% and
  a maximum of +782%, one contract dominating a 30-trade mean seems very likely.
* **E2 — the verdict is RAISE rather than NULL. 60/40.** The two halves should give similar
  curves because both are drawn from the same heavy-tailed shape.
* **E3 — at least one currently-reported bucket loses `enough_to_judge` at `FLOOR*`. 65/35.**
* **E4 — `P_flip(30) > 0.15`.** A directional call on the shipped value specifically, 70/30.
* **E5 — the secondary half-agreement criterion is WEAKER (needs a larger n) than the primary.
  55/45.** Genuinely uncertain, and if it is much weaker that is the more important number.

## 7 · Trial cost

**One hypothesis with one statistic**, measured over a pre-committed grid and on two halves. The
grid is the *resolution* of a single estimate, not a set of competing arms — the same treatment
S22 gave its eight horizons is **not** claimed here, because those were eight separate questions;
this is one curve read at one threshold.

**Options `N` +1.** The secondary criterion is a robustness read on the same hypothesis and is
charged **zero**.

## 8 · What would make this register void

* Extending or shifting the `n` grid after seeing the curve.
* Changing the 0.05 bar, the "one grid step" agreement rule, or the definition of "most extreme".
* Using any book other than the split-clean banked one.
* Applying a raised floor to retroactively unpublish a result without reporting that it did so.
