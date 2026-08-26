# PREREG — B13 + S7-4: THE LIQUIDITY UNPARK
## Two arms, both gated on a $ADV that did not exist until now.
## **BLIND. Committed ALONE, markdown only, zero `.py`.** 2026-08-26.

**No arm has been run.** The instrument was built and validated in a separate pass at **zero
trials** (`MB15`'s ordering), and **no ranking, filtering or scoring of any kind has touched it**.
Every number in section 2 is a coverage or fidelity fact; every number the arms will produce is
absent from this file because it does not exist yet.

**TRIAL COST: 2 EQUITY TRIALS**, one per arm, **booked before the runner exists**. Equity `N` is
**243** today, so the charge takes it to 245 — and `MB31`'s derivation says the calibrated
placebo floors cannot move below **`N` = 247**, so **this register's own charge cannot move the
bar it is judged against.** Stated because that is not generally true and is the kind of thing
that has to be checked rather than hoped for.

---

## 1. WHAT WAS BLOCKED, AND WHAT UNBLOCKS IT

`B13` reads **PARTIAL — BLOCKED ON DATA**: `MIN_AVG_DOLLAR_VOLUME` *"structurally cannot bind on
this path"*. `S7`'s fourth interaction, `size × liquidity`, is recorded as *"the one that cannot
be built at all"* and charged **no trial** on session 8's precedent that a test which cannot run
keeps the denominator.

Both rest on one fact: the only volume in the project reaches **502 of 2,531 names = 19.8%**.
CRSP `dsf` reaches **2,271 = 89.7%**. That is the unblock, and **it is a coverage unblock only —
it says nothing about whether either arm will clear.**

---

## 2. THE INSTRUMENT, AND ITS COVERAGE ON THE POPULATION THE ARMS WILL TEST

`valuation/edge/adv.py`, built and validated at zero trials before this register was written.

### 2.1 The definition is MATCHED to the live screen, not chosen

`valuation/screener/prices.py:243` computes the live `avg_dollar_volume` as the mean of
`close × volume` over the trailing **~60 sessions** on the **as-traded** close. That is the
quantity `MIN_AVG_DOLLAR_VOLUME = 500_000` is calibrated against, so the panel instrument
reproduces it. **Choosing a different window would silently re-scale the threshold and make a
panel filter that shares a constant with the live screen mean something else** — `MA5`'s
frozen-constant family one level up. The window ends on the **prior** session, because a
liquidity screen that reads the selection day's own tape is a look-ahead on the axis most
correlated with that day's news.

### 2.2 COVERAGE, STATED BEFORE THE ARM

| | |
|---|---|
| panel cells | **113,945** |
| cells with a point-in-time ADV | **90,025 = 79.01%** |
| excluding the 5 dates after CRSP's cut | **90,025 of 104,578 = 86.08%** |
| dates with ≥20 covered names | **64 of 69** |
| **halves of the COVERED subsample** | **32 / 32, boundary 2017-01-19** |
| per-date coverage | min **78.3%**, median **85.5%**, max **96.2%** |

**THE 89.7% IN THE BRIEF IS A NAME-LEVEL FIGURE AND THE ARMS ARE SCORED ON CELLS: the honest
number is 79.01%.** A name can resolve to a permno and still have no usable ADV on a given date —
too few sessions in the window, or the date is past the cut. Quoting the name-level figure for a
cell-level arm is exactly the population mismatch `MB8` and `V6-OPT` both paid for.

**COVERAGE RISES THROUGH THE SAMPLE — 78.6% on the first date to 96.2% on the last — so the early
half is measured on a systematically thinner cross-section than the late half.** Declared here
because a coverage trend that correlates with time will show up in any both-halves gate, and
discovering it after a split disagrees is how a data artefact becomes a finding.

Unlike `S18`, the halves are **32/32 against `holdout_compare_panels`' `min_dates=16` floor**, so
this is a full-strength split and not the thinnest the gate accepts.

### 2.3 What CRSP cannot cover

CRSP on this account is cut at **2024-12-31**. Five panel dates fall after it — 2025-01-27,
2025-04-28, 2025-07-29, 2025-10-27, 2026-01-28 — which is **9,367 of 113,945 rows = 8.22%**.
**Both arms run on 64 of 69 dates and neither may be quoted as a statement about 2025 or 2026.**
The forward paper track lives entirely after the cut and this instrument is useless to it.

### 2.4 Two traps, measured

**`prc` IS NEGATIVE WHEN CRSP SUBSTITUTES A BID/ASK MIDPOINT** — its own convention for a close
that did not trade. **28,283 rows = 0.404%.** A naive `prc × vol` goes negative on precisely the
least liquid rows, and a negative ADV sits below any floor, so the filter would appear to work
while working for the wrong reason. `abs()` is applied and the share is reported.

**THE TICKER → PERMNO JOIN IS DATE-SCOPED. 1,053 of 2,271 matched tickers map to more than one
permno** — `S3-I5`'s reuse problem in a third table, after the option chains and the IBES
actuals. An undated dictionary attributes one company's volume to another, silently, and reused
tickers concentrate in small and delisted names, which is again the population a liquidity screen
is about.

### 2.5 B7 FIDELITY — and it found a defect in the INCUMBENT route

The existing definition is `scripts/capacity.py:adv_from_bars`. On the **24,586 cells both routes
can price**, the CRSP series agrees at a **median ratio of 1.0002, flat across every size decile**
(1.0001–1.0004). So the central tendency is the same quantity.

**But 16.0% of cells disagree by more than 25%, and the cause is a defect in the incumbent, not
in CRSP.** My first hypothesis — ticker reuse in the bars cache — was **REFUTED** (16.6% vs 15.4%,
a 1.08× lift). The disagreement is **systematic per name**: FAST, HON, WMT, CMG and APH disagree
on ~64 of ~69 cells each. Measured against the vendor columns directly:

| | volume, bars ÷ CRSP (early) | (late) | price, bars ÷ CRSP |
|---|---|---|---|
| CMG (50:1, Jun-2024) | **50.0000** | 0.9962 | 1.0000 |
| AAPL (4:1 2020, 7:1 2014) | **27.9950** | 0.9958 | 1.0000 |
| WMT (3:1, Feb-2024) | **3.0000** | 0.9937 | 1.0000 |
| MSTR (10:1, Aug-2024) | **10.0015** | 1.0097 | 1.0000 |
| SIRI (1:10 **reverse**) | **0.1000** | 0.1016 | 1.0000 |
| **JPM (no split — the control)** | **1.0000** | 0.9882 | 1.0000 |

**`data/bulk/prepared/bars` stores an AS-TRADED `raw_close` beside a SPLIT-ADJUSTED `volume`, so
`adv_from_bars` overstates dollar volume by the cumulative forward-split factor — up to 50× — and
understates it on reverse splits.** The price ratio is 1.0000 for every name, so it is the volume
leg alone. `U1-SPLIT`'s defect with the legs swapped.

**THE DIRECTION MATTERS FOR THIS REGISTER: it makes split names look MORE liquid than they were,
so a floor built on the incumbent route UNDER-filters.** **REPORTED OUTSIDE THIS LANE
(`RUN_RULES` rule 3) AND NOT FIXED HERE**: `adv_from_bars`' only consumer is `capacity.py`'s own
run, and repairing it would move a published capacity figure. `fundamental_panel`'s
`prefilter_adv_partial_source` block cites that function and inherits the caveat.

---

## 3. ARM 1 — `B13`. A CREDIBILITY CLAIM, NOT AN ALPHA ONE

**Apply `MIN_AVG_DOLLAR_VOLUME = 500_000` — the shipped constant, imported, never retyped — as a
point-in-time prefilter on the panel, and measure what the book does.**

### 3.1 THE EXPECTED OUTCOME IS A SMALL ALPHA LOSS, AND IT IS NOT A FAILURE

**Declared in advance, because it is the whole reason this arm cannot use the ordinary gate.**
Dropping illiquid names removes the part of the cross-section where measured returns are largest
and least tradeable. **A prefilter that IMPROVED alpha would be the surprising outcome.** The
claim `B13` makes is that the book is *investable*, not that it is *better*: a backtest that
holds names nobody could have bought at size is not wrong about its arithmetic, it is wrong about
what it is a backtest OF.

**So a small alpha loss is a PASS.** Reporting it as a failure would be scoring a credibility
claim on an alpha bar — the category error `V5-REREAD` caught when a cost figure was compared to
an equity-notional constant.

### 3.2 The gate: NON-INFERIORITY, at X7's own calibrated margin

**`B13` PASSES iff the prefiltered book's top-decile alpha is worse than the unfiltered book's by
LESS than X7's calibrated non-inferiority margin, in BOTH halves of the covered subsample.**

The margin is **X7's alpha margin, DERIVED at the run's own `N` and never typed** — 1.8629pp at
`N` = 224 per `MA19`, and `MB31` proves it unmoved below `N` = 247. The same margin `MB8` used
for the same shape of question. **A loss LARGER than the margin is a REJECT**: at that point the
filter is not buying credibility, it is destroying the result.

**Reported beside the verdict, always:** turnover, the number and share of names removed per
date, and the removed names' median market cap. **A filter that removes 40% of the universe buys
different credibility from one that removes 2%**, and the alpha number alone cannot tell them
apart.

### 3.3 UNMEASURED NAMES ARE KEPT, NEVER FILTERED

**A name with no ADV is UNKNOWN and stays in the book.** Dropping it would make this a
data-availability screen wearing a liquidity screen's name — `S10`'s exact defect, and here it
would correlate with era (coverage runs 78.6% → 96.2%), with size and with delisting. The count
of kept-because-unmeasured names ships with the verdict, and `adv.CoverageError` exists so that a
missing measure cannot silently become a zero, which would sit below every floor.

---

## 4. ARM 2 — `S7`-4. THE FOURTH INTERACTION, ON S7's OWN GATE VERBATIM

**`size × liquidity`, built as `S7` built its other three: ONE added column, `z(z_size ×
z_liquidity)`, entering at 0.125 like any other input.** Liquidity is `log(ADV)`, standardised
within date; the log because dollar volume spans six orders of magnitude and an unlogged column
would make the interaction a megacap indicator.

**THE GATE IS `S7`'s, QUOTED RATHER THAN RESTATED:** *"≥ +100 bps top-decile alpha AND ≥ +0.25
long-short *t*, in BOTH halves, boundary embargoed … ADOPT-ELIGIBLE iff it clears both margins in
both halves; otherwise REJECTED; ambiguous is a NULL (`RUN_RULES` A6)."*

**Inherited with it:** `S7`'s labelling rule, so a clearing arm is recorded
**`ELIGIBLE — UNREPLICATED, 1 OF 7 SIBLING ARMS`** (S7's six plus this one) and never "adopted";
and `S7`'s refusal to apply the audit's Bonferroni prescription, because this project's gate is a
**margin** gate whose floors X7 calibrated against a placebo, and converting a p-value bar into a
margin bar invents a correspondence nobody has calibrated.

**`S7`'s C7 dilution control is inherited too**: an eighth input moves every theme's relative
weight from 1/7 to 1/8, so the arm is a compound change, and a constant eighth column isolates
it. `S7` measured that at +0.000173 / +0.000146 — essentially nil — and this arm must reproduce
that control rather than assume it carries over to a different column.

**The two arms are scored SEPARATELY and neither gates the other.** `B13` is a filter on the
universe; `S7`-4 is a column in the composite. A reader who conflates them will read a
credibility result as an alpha one.

---

## 5. VOID CONDITIONS

1. Either arm run without the coverage census of §2.2 stated first.
2. `B13` scored on the ordinary `+100bps` margin gate, or its alpha loss reported as a failure.
3. A name dropped for having no ADV measure.
4. Either arm quoted as a statement about any date after **2024-12-31**.
5. The ADV window changed from the live screen's 60 sessions, or `MIN_AVG_DOLLAR_VOLUME` retyped
   rather than imported.
6. The name-level 89.7% quoted as the arms' coverage in place of the cell-level 79.01%.
7. A ranking arm run in the same pass that builds or modifies the instrument.
8. `adv_from_bars` repaired inside this register — it is another lane's and moving it moves a
   published capacity figure.

---

## 6. EXPECTATIONS, priced before any result

1. **`B13` passes non-inferiority** — the alpha loss lands inside the margin. **70/30.**
2. **The alpha loss is NEGATIVE (a real loss) rather than a gain** — i.e. the filter costs
   something. **80/20.** *If it comes back positive, that is a flag to check the filter is
   binding at all, not a win.*
3. **`MIN_AVG_DOLLAR_VOLUME` removes under 15% of covered cells** at $500k, because the panel is
   already a large-cap-tilted universe. **60/40.**
4. **`S7`-4 is REJECTED**, like `S7`'s other three. **75/25** — five of the last six
   orthogonality-motivated candidates predicted nothing, and an interaction of two incumbents is
   a weaker prior than a new signal.
5. **The removed names' median market cap is under a fifth of the kept names'.** **70/30.**
6. **Coverage on the arms' population lands nearer 79% than 89.7%** — already measured, so this
   is not scored as a forecast; it is here to make the distinction explicit.
