# PREREG DRAFT — IC5, BOOK BREADTH AT THE MEASURED CROWDING POINT

**DRAFT. Frontier Scout. No measurement, no arm, ZERO trials.** Ranked **5 of 6**.

**Seed idea (3), KEPT but reduced from a grid to ONE arm.** The seed asks for *"top 5% vs decile
vs quintile"*. Three cuts is a grid, the brief forbids grids, and at equity N **248** each arm
raises the hurdle for everything else. **So the register takes ONE breadth, pre-committed, chosen
by the capacity arithmetic the record has already banked — not by whichever reads best.**

---

## 1. MECHANISM

A narrower book holds more of the signal per name and less of the diluted tail; a wider one holds
more capacity and less cost per dollar deployed. The published object is the **decile**, and that
choice was inherited rather than optimised against the book's own measured capacity.

**ARM: the top QUINTILE of the large-cap tier — ONE arm, wider than the incumbent, not narrower.**

**Why wider, and the direction is the pre-commitment that makes this one arm rather than three.**
`P2` measured the served large-cap book's crowding point at a **$5.1B cohort**, and `P1` measured
**87 bps at $1M** on the top-25 all-cap book. Narrowing the book moves *toward* the crowding
point and *away* from capacity; it also moves toward `B17`'s object, the concentrated top-25 book
that `CLAUDE.md` calls **the noisiest number in the results file** and that `B17` showed is
**mislabelled** — it holds up to **FIFTY** names, since it sells only below `exit_rank = top_n × 2`,
and it pays **neither costs nor taxes** unlike every other book in the file. **So the narrow
direction is already represented in the record by its least trustworthy number, and widening is
the direction nobody has measured.**

## 2. THE RECORD'S EVIDENCE *FOR*

* **The cost curve is banked, so the net comparison needs no new cost measurement**: breakeven
  **134.1 bps** one-way against a measured **33.4 bps** (a 4.0× margin), and net top-decile alpha
  by cost **6.57% @25 bps, 5.04% @50, 2.02% @100, −0.94% @150**.
* **Capacity is measured, not assumed** — `P1` 87 bps at $1M on the top-25 all-cap book, `P2` the
  $5.1B crowding cohort for the served large-cap book.
* **`S22` makes the dilution question concrete.** The top decile holds a median **156** names per
  date; a quintile roughly doubles that. And `S22` measured alpha still accruing at two years with
  rank IC **rising** with horizon, so a wider book is not obviously holding dead weight.
* **`X1` is the strongest positive result in the record and it is about breadth's cousin.**
  Halving the **universe** left the centre unmoved — **200 of 200 half-books positive**, median
  half-book alpha **+0.07233** against the full universe's **+0.07174**, minimum **+0.04382** — so
  the effect is broad and uniform across names rather than carried by a few. **A broad, uniform
  effect is the shape that survives widening**, and that is the single best reason to run this arm.

## 3. THE RECORD'S EVIDENCE *AGAINST*

* **It changes the referent of the published headline.** `+7.17%/yr` *is* the top-decile alpha.
  An adopted breadth change makes every historical figure in `CLAUDE.md` describe a different
  object, and comparability across the record is worth more than a marginal alpha improvement.
  **That is a reason to keep the decile as the published object even if the quintile wins**, and
  the register must say so before it runs.
* **`MC10` already closed the adjacent question and its arithmetic transfers as a warning.**
  Score-weighted vs equal-weight *"can never be a hurdle claim"*: at the **3.3207** hurdle the 80%
  MDE is **≥ 1.01pp** against a **0.83pp gross ceiling**. A breadth change is a similarly
  mechanical re-cut of the same panel, and the register must check its own ceiling against its own
  MDE **before** running or it risks being unanswerable by construction in the same way.
* **No calibrated floor exists for the paired difference** (`V2G`, `R1-VAR`), so the comparison
  cannot be scored against `X7`'s levels.
* **`R1-VAR`'s standing ruling binds the likeliest winning shape.** A wider book will probably
  improve Sharpe and reduce drawdown while giving up gross alpha — and Don's ruling is that **a
  Sharpe or volatility gain bought with alpha is not worth having unless the Sharpe itself is
  bad.** The book runs Sharpe **0.5866** at IR **~0.88/yr**, so **the antecedent does not fire**
  and an arm that wins on Sharpe alone is **not adoptable**. The register must declare in advance
  that the verdict is on **alpha**, with Sharpe reported beside it carrying no verdict.
* **`S13` is the worked example of exactly that trap**: inverse-vol capped improved Sharpe
  **0.5866 → 0.6261** and left drawdown flat while giving up **1.76pp** of return — and was
  rejected. `R1-VAR` then noted `S13`'s 1.76pp sits *inside* `X7`'s 1.8629pp margin, so it would
  have PASSED a non-inferiority leg. **A breadth arm must not be scored on a non-inferiority
  margin for the same reason.**

## 4. BAR AND MDE

Gate: the shipped `holdout_compare_panels`, verdict on **top-decile-equivalent alpha**, both
halves, both weightings. **The arm must WIN on alpha, not merely fail to lose it** — `R1-VAR`'s
ruling and `S10`'s precedent both forbid a non-inferiority framing here.

**MDE, and this is the leg most likely to kill the item before it runs.** Paired within-panel → no
calibrated floor; measure the arm's own paired HAC SE (`MB8`). Equity N **248**, hurdle
**3.3206712** (derived). **The register must compute its own gross ceiling the way `MC10` did and
compare it to its own MDE in §4 rather than in a handoff.** If the achievable alpha difference
between a decile and a quintile on this panel is smaller than the 80%-power MDE at the hurdle,
**the item is unanswerable and should not be run** — closing it at zero trials, which is the
cheapest good outcome.

## 5. KILLS, FREE AND READ FIRST

* **K1 (FREE, and it may close the item at zero trials). The ceiling-vs-MDE check**, computed from
  banked per-decile returns exactly as `MC10` computed its 0.83pp ceiling. Unanswerable → STOP.
* **K2 (FREE).** Book size must be reported, not assumed: `S14-WIDTH` measured book size
  **identical at every band width** (154.1 early, 175.6 late), so the incumbent's realised size is
  known and the arm's must be stated beside it.
* **K3 (FREE).** The arm must respect `P2`'s measured crowding point — a breadth that pushes the
  implied position size past the **$5.1B cohort** finding is reporting a book that cannot be
  bought, which is `P1`/`P2`'s whole subject.
* **K4.** Fidelity: the decile arm must reproduce the published record at max |Δ| **0.000e+00**
  (0.07174142332098163 / 2.8360640685320595 / 2.6199121240414884 / −0.8909090909090909).
  **ABORT if not.**

## 6. VINTAGE CONSEQUENCE

**On adoption: a VINTAGE EVENT, and the heaviest of the six on the product side** — it changes how
many names the Index holds, so it changes the **bound** track's constituent set as well as the
score. Derive the vintage from `track_meter.VINTAGES`, never quote it; derived today, **vintage 4
OPEN since 2026-08-13**, ~48 days accrued. Rule 6: the reset buys nothing statistically, and the
contract's meter has **13.3% power at 60 months**. **ELIGIBLE, NOT ADOPTED**, routed to Don — and
the register should note that the research answer and the published-object decision are separate,
since the decile may be worth keeping as the quoted object regardless of which breadth wins.

## 7. CAN OWNED DATA TEST IT?

**Yes, with no purchase and no rebuild.** `quantile_backtest` already takes `n_q`, the banked panel
carries every date and name, the cost curve is banked, and `P1`/`P2`'s capacity figures are banked.
K1 is pure arithmetic on banked per-decile returns.
