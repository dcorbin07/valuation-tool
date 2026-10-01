# PREREG DRAFT — IC3, THE RE-ENTRY COOLDOWN (A SYMMETRIC BAND)

**DRAFT. Frontier Scout. No measurement, no arm, ZERO trials.** Ranked **3 of 6**.

**This is NOT `S14` again, and the difference is one-sided-ness.** The shipped band is
**asymmetric**: a held name is kept until it falls out of the top 30% (`BAND_WIDTH = 0.30`, wired
live at vintage 4), and there is **no corresponding delay on the BUY side** — a name that left the
book last quarter is re-bought the instant it re-enters the top 10%. `S14` and `S14-WIDTH` swept
the EXIT threshold and closed it (interior optimum at 0.30, third extension forbidden). **Neither
touched entry hysteresis.** This draft adds the missing side.

---

## 1. MECHANISM

A name that has just been sold is re-bought only after a pre-committed cooldown of **one
rebalance**. The claim is that the book pays round-trip cost to re-acquire names it sold a quarter
earlier, and that the sell-then-rebuy pair is mostly rank noise around the band's edge rather than
information.

**ARM: one cooldown length — ONE rebalance. No grid.** One is the smallest value that can have any
effect and is therefore the only value that does not require choosing; anything longer is the
hold-out family and is measured (§3).

## 2. THE RECORD'S EVIDENCE *FOR*

* **`S22` measured that re-entry is the norm, and it is the reason to look.** **74% of names have
  more than one spell**, and persistence-with-gaps **plateaus at ~19–24% out to eight rebalances
  instead of decaying to zero** — i.e. a substantial share of the book is names coming back. That
  plateau is `S22`'s own phrase for it: *"re-entry is the norm."*
* **The churn it would prevent is priced.** Turnover **261%/yr** at a measured **33.4 bps**
  one-way, breakeven **134.1 bps**, with the net-alpha-vs-cost curve banked. A round trip avoided
  is two crossings avoided.
* **`S14` is the existence proof that hysteresis on this book pays**, and that it is **not only a
  cost saving** — its gross alpha improved **+1.02pp / +0.77pp**, so holding through rank noise
  carried information. Entry hysteresis is the same idea applied to the other edge of the same
  band.
* **`S22`'s tenure numbers say the effect is reachable rather than marginal**: median spell ONE
  rebalance, **70.6% of spells exactly one**, one-period retention **36.6%**. A book that mostly
  holds names for a single quarter and then takes many of them back is exactly the book a cooldown
  bites on.

## 3. THE RECORD'S EVIDENCE *AGAINST*

* **A cooldown deliberately refuses a name the ranking says to buy.** That is the `S23` exit-rule
  family in mirror image, and `S23` found **nothing beats the incumbent** — four challengers all
  inside 0.4pp/yr, **three of four flipping sign between halves**.
* **It can only make the book staler.** `S23`'s `C-NEVER` is the limit of that direction:
  **−10.89pp/yr**, alpha against the equal-weighted universe collapsing **15.48% → 3.37%** by
  dilution. A cooldown is a small step along a path whose end is measured and bad.
* **`S14-WIDTH` already discharged the band's grid-boundary caveat and forbade a third
  extension.** A reader may fairly call this a fourth bite. **The register must carry that
  objection in its own §1 rather than answer it in a handoff** — the defence is that the swept
  parameter was the EXIT rank and this is the ENTRY delay, which the sweep never varied, and that
  claim is checkable against `S14-WIDTH`'s own grid.
* **`S11`'s warning transfers.** The horizon ensemble bought a real turnover reduction
  (**0.6352 → 0.4976**, ~55pp of book per year) and gave up **205–422 bps of alpha** to get it —
  the record prices that trade as running **11× to 23× against**. A turnover saving is worth about
  **18 bps/yr** at this book's cost; **any arm that gives up more than that much alpha loses, and
  the register must state the 18 bps figure as the thing to beat rather than discovering it.**

## 4. BAR AND MDE

Gate: the shipped `holdout_compare_panels`, verbatim, both halves, both weightings.

**AND a stated arithmetic floor, derived before the run:** the arm must not give up more alpha
than the turnover it saves is worth. From the banked cost curve and `S14`'s own measured turnover
response, that is on the order of **18 bps/yr** — so an arm that clears the gate while losing more
than that is **winning the wrong comparison**, which is `S11`'s exact failure recorded as a number.

**MDE.** Paired within-panel → **no calibrated floor** (`V2G`, `R1-VAR`); measure the arm's **own**
paired HAC SE (`MB8`). Equity N **248**, hurdle **3.3206712** (derived). A one-quarter cooldown is
a **small** perturbation — it changes a minority of entries, not the ranking — so the honest prior
is near `MB8`'s **0.1106pp**, i.e. an 80%-power MDE around **0.31pp** at crit 2.0 (UNCALIBRATED)
and **0.46pp** at the hurdle. **That is the same order as the 18 bps the saving is worth, so this
design is close to unable to separate its own prize from zero — and the register must say so
BEFORE running, because a null here would otherwise be read as "no effect" when it means "no
effect this design could see".**

## 5. KILLS, FREE AND READ FIRST

* **K1 (FREE, zero trials). The bite census.** From banked membership across the 69 dates, count
  the entries the cooldown would refuse. If it refuses **< 5%** of entries the arm is inert and
  closes at zero trials; `S22`'s 74%-multi-spell figure predicts it bites well above that, so this
  kill is a check rather than an expected stop.
* **K2 (free).** The refused entries must be measurably **marginal** — concentrated near the band
  edge rather than spread through the decile. If the cooldown is refusing names that re-enter at
  the TOP of the ranking, the mechanism is wrong and the arm is a quality filter in disguise.
* **K3 (free).** Book size must be held fixed, as `S14`'s own `_band_select` does (`S14-WIDTH`
  measured book size **identical at every width**, 154.1 / 175.6 names). A cooldown that shrinks
  the book confounds hysteresis with concentration and would be measuring `IC5` instead.
* **K4.** Turnover must fall. If it does not, the stated mechanism is absent.

## 6. VINTAGE CONSEQUENCE

**On adoption: a VINTAGE EVENT** — it changes live membership. Derive the vintage from
`track_meter.VINTAGES`, never quote it; derived today, **vintage 4 OPEN since 2026-08-13** (the
S14 band at 0.30), ~48 days accrued. **There is a particular awkwardness worth naming: the open
vintage IS the band adoption, so adopting the band's other side would close a vintage barely
seven weeks old and opened by the same mechanism.** Rule 6 — the reset buys nothing statistically.
**ELIGIBLE, NOT ADOPTED**, routed to Don.

## 7. CAN OWNED DATA TEST IT?

**Yes, no purchase and no rebuild.** Banked panel, shipped `_band_select`, banked cost curve.
K1–K3 are all free and come from membership already reproducible name-for-name on all 69 dates.
