# PRODUCT_SPEC.md — what each surface is, and how often it changes

**ONE PAGE, AND IT IS BINDING.** `tests/test_product_spec.py` parses this file and fails if a
surface shows a different object from the one named here, or if a public page states a cadence
that contradicts it.

**WHY IT EXISTS.** On 2026-10-02 an end-to-end scrub found the Index tab showing a 25-name book
rebuilt from each day's scan while the forward record beneath it tracked an 86-name quarterly
book — and `PAPER_TRACK_CONTRACT.md` §5 defines the tracked book as *"the Valquo Index exactly as
the site shows it"*, so the contract's own premise was false. The same scrub found a backtest of
one construction printed beside the live curve of another, on three surfaces, and eleven
statements of cadence or mechanism that were wrong. Every one of those is a surface disagreeing
with another surface about what object it is showing. **This file is the one place that says.**

---

## THE OBJECTS

| object | what it is | how often it changes | authority |
|---|---|---|---|
| **Hot Stocks** | the full ranked screen, every scored name in order | **every trading day**, after the close | the latest scan snapshot |
| **Options signals** | alert-day option picks | **every trading day** an alert fires | the alert log |
| **The Valquo Index** | **ONE FIXED BOOK** — the holdings formed at the last quarterly rebalance, held unchanged until the next one | **only at a quarterly rebalance** | `data/valquo_track.json` plus its rebalance events, read through `screener/index_in_force.book_in_force` |
| **The forward record** | that same book, marked daily from closing prices, against SPY and SPMO | a new mark each trading day; the **book** does not change | `data/valquo_track_history.csv`, read through `screener/index_track` |
| **The backtest beside it** | the backtest of **the book the Index actually serves** — the $10B large-cap tier, score-weighted, 8% cap, 0.30 no-trade band — shown in **two tax treatments of that one book** | only when the measurement is re-run | **`screener/index_book_measured`**, from `INDEX-BOOK` (`ceffd04`) |
| **The research decile** | the all-cap **equal-weighted** decile. A real published measurement, and **NOT the Index** | when the panel is rebuilt | `index_book_measured.research_block`; `/proof` only |

### ONE BOOK, TWO TAX TREATMENTS — AND THE INDEX IS A ROTH PRODUCT (18-AMEND, Don 2026-10-03)

The **roth top-25 config is retired from every surface.** Code may keep it for research; nothing
public reaches it.

**THE FIGURES ARE THE SERVED BOOK'S, MEASURED.** Until 2026-10-03 this block was
`book_configs.taxable` recomputed off the banked panel — the **all-cap, EQUAL-WEIGHTED** decile,
publishing **+26.15% gross and +19.35% net for a book nobody holds**, beside a live curve of the
book they do. `INDEX-BOOK` (r1, 2026-10-02, `ceffd04`) measured the served construction on the
same machinery and it is materially lower.

**Every figure leads with the Roth/IRA treatment**, because the Index is a Roth product. The
taxable figure sits beside it, labelled *for a regular brokerage account, shown for transparency*.

| treatment | basis | return /yr | Sharpe |
|---|---|---|---|
| **in a Roth/IRA** (the headline) | net of modelled trading costs, **no tax** | **+17.1619%** | 1.0318 |
| **for a regular brokerage account** | **after tax**, FIFO at 40.8% short / 23.8% long | **+12.2033%** | 0.7595 |
| **the cost of taxes** | one lot path, rates the only knob | **−4.9586 pp/yr** | — |

**AFTER TAX THE BOOK LANDS 3.03 pp A YEAR BELOW SPY (+15.23%).** That sentence ships with the
figure. The driver is measured: **84.08% of realised gains are short-term**, because a quarterly
book turning over 2.44× a year realises almost everything inside a year. The no-dividend caveat
runs **against** the taxable arm and travels with it.

### BOTH ALPHA SENTENCES ARE TRUE AND NEITHER MAY TRAVEL ALONE

`INDEX-BOOK`'s own void condition, and the spec binds it:

| benchmark | alpha /yr | early half | late half |
|---|---|---|---|
| an equal-weighted basket of **the same large-cap tier** | **+4.1209 pp** | +4.0615 | +4.1746 |
| **the all-cap equal-weighted universe** (what older figures used) | **−0.0576 pp** | — | — |
| **SPY** | **+1.9488 pp** | **+3.7202** | **+0.2702** |

Roughly **70%** of the gap between the first two rows is the small-cap premium a large-cap tier
declines to hold — not the ranking failing in large caps. Both readings are honest; quoting the
+4.12 alone is not.

**THE vs-SPY HALVES ARE SHOWN, NOT AVERAGED.** +3.72 early against +0.27 late: the average
describes neither half, and the late half is where a reader lives.

### WHAT THE FIVE-YEAR FORWARD TEST CAN AND CANNOT SHOW

Each arm is scored at **its own** measured tracking error (`MB8`: an `se` may not be borrowed
across constructions).

| | net edge vs SPY | own tracking error | months to detect |
|---|---|---|---|
| **the served book (the Index)** | **+1.9488 pp** | **8.4381** | **4,383** (~365 years) |
| the research decile | +8.0564 pp | 11.3878 | 385 (~32 years) |
| what §2 used BEFORE Amendment 2 | +9.9864 pp — **wrong book AND gross** | 11.40 | 242 |

So the forward test **can** show whether the Index is being recorded honestly and whether its
costs and turnover behave as modelled. It **cannot** show whether the Index beats SPY: no
five-year result, in either direction, would settle that.

**THE SIGNED CONTRACT NOW CARRIES THIS CORRECTION — Don accepted it on 2026-10-04 as
AMENDMENT 2** (`PAPER_TRACK_CONTRACT.md` §5a-2, with the paragraph appended to §2). The last row
is therefore what §2 used **before** the amendment, kept because the correction is only legible
beside the figure it replaced.

**σ IS UNCHANGED AT 11.40.** §6.5 forbids revising it downward — at 1.5× the assumed volatility
the false-crossing rate is 20% — and the amendment does not ask to: the arm-specific tracking
error is reported **beside** σ, never substituted for it. **The amendment makes the contract's
stated power WORSE, not better**; nobody gains from it, and no threshold, clock or meter parameter
moved. `PREREG_DRAFT_contract_amendment_2.md` is kept as the record of what was proposed and
when.

### WHEN THESE NUMBERS CHANGE

`r1`'s **INDEX-BEST** may measure alternative constructions. If Don adopts one, the Index's
numbers switch to it — and that is an ADOPTED construction change, i.e. a **vintage event**.

### The one rule that was broken

**THE HOLDINGS, THE CURVE AND THE BACKTEST ARE ALL THE SAME BOOK.** A surface may show any of
the three; it may not show one and label it another. The Index is not a daily pick, and the
account-type constructions describe how the **next** rebalance would be built — never what is in
force.

---

## CADENCE, STATED ONCE

* **The live list re-ranks after every market close.** The **backtest** re-ranked **quarterly**.
  Both are true of different things, and a sentence that gives one cadence for both is wrong.
* **The Index changes only at a rebalance.** The next one is **derived**, not pinned: 63 trading
  days from the book's own `scan_date` (`index_in_force.REBALANCE_TRADING_DAYS`), which for the
  2026-07-24 scan is **2026-10-22**, matching `REBALANCE_RUNBOOK_2026-10-22.md`.
* **A holding's weight moves between rebalances only on a corporate exit**, pro-rata across
  survivors, and only for an exit **declared** in `index_in_force.EXITS` with its provenance.

---

## WHAT IS PAPER, AND IN WHICH WAY

Two different kinds, and conflating them is its own defect class:

* **The Valquo Index forward record is in NO broker account.** It is a model book marked from
  closing prices. No fills, no slippage beyond the modelled cost table, no tax.
* **The options paper book runs in a broker sandbox** on a paper account with no real money.

**The recorded Index series is GROSS of costs** (`PAPER_TRACK_CONTRACT.md` §7 item 6). The
evidence meter subtracts **0.14529 pp per month** when it forms a verdict; the chart does not.

---

## THRESHOLDS, EACH STATED ONCE

| gate | value | what it governs |
|---|---|---|
| `index_track.MIN_LIVE_DAYS` | 60 trading days | when the live figure may become the headline, **and** when annualised figures and the Sharpe are published |
| `track_meter` operational gate | the contract's own row | the other half of the headline gate |
| `index_in_force.REBALANCE_TRADING_DAYS` | 63 trading days | when the book changes |

`MIN_SHARPE_DAYS` **defers to `MIN_LIVE_DAYS`**. It used to be 20, so the card published a Sharpe
on 26 recorded days beside its own sentence withholding annualised figures — two gates on one
card, and a reader could not tell which governed the number in front of them.

---

## NUMBERS A PAGE MUST READ, NEVER STATE

Trial counts and the universe size are **read live** (`web/live_facts.py`), because a figure
typed into a template is right on the day it is typed and wrong afterwards — and differs between
branches, so no single literal can be correct. `~800 names` was on three public surfaces against
a scan that ranks 1,500; `248 by 2026-09-29` was on two against a log that had moved on.

---

## EVERY SCREEN MUST SHOW IT MEASURED SOMETHING (ITEM 19, 2026-10-03)

**THE RULE.** A screen whose eligible count is non-zero must demonstrate, on a path that
includes its real wiring, that it measured at least one name and produced the quantity it
screens on. A screen that measures nothing may not render a sentence about the market.

**WHY IT IS A RULE AND NOT A TEST.** The Dip Detector measured **zero names from the day it
shipped (2026-08-13) until 2026-10-03** and **46 of its own tests passed throughout**.
`dip.engine_measure` was handed `web/app._get_or_compute`, which returns a `resultcache.Entry`
and had done since `42597e2` — **a week before the screen was built** — so
`getattr(result, "company")` returned `None`, no drawdown was computed, and every name was
counted unmeasured. Measured on the service: `n_eligible` **241**, `n_measured` **12**,
`n_unmeasured` **12**, with the page saying *"No name cleared a 20% fall"*.

**WHY THE TESTS DID NOT CATCH IT, which is the part that generalises.**
`dip.measurement_from`'s docstring states the design: *"Pure — no network, no cache — so the
mapping from a valuation to a screened row is testable against a stub result, which is where the
interesting mistakes live."* The stub was result-SHAPED, so the MAPPING was tested exhaustively
and the WIRING was never tested at all. **A pure function tested only against a hand-built input
cannot catch a caller passing the wrong type.** Injecting `get_result` to make the path testable
with a dict is exactly what left the real path untested.

**WHAT A SCREEN OWES, THEREFORE:**

1. **An end-to-end test through the real injected dependency**, with only the outermost vendor
   call stubbed — `tests/test_dip_wiring.py` drives `screen_snapshot` through the real
   `_get_or_compute` and asserts `n_measured > 0`, `n_unmeasured < n_measured`, and a value for
   the screened quantity on every surviving row.
2. **A wiring error must be LOUD.** `engine_measure`'s `except Exception` is right for one name
   failing to value and is how 229 identical wiring errors read as a data gap, so
   `dip.DipWiringError` is a distinct type and is re-raised rather than swallowed.
3. **An empty screen states which of the two things it means.** "Nothing qualified" and "nothing
   was measured" are opposites a reader cannot distinguish, so the copy branches on
   `n_measured == 0 || n_unmeasured >= n_measured` and the surviving "no name cleared" sentence
   is scoped to the names that could be measured.
4. **A recorded series never takes an artefact as an observation.** `f11_live_rejects` returns
   `None` — not `[]` — when the screen measured nothing, which is audit #5 `H2`'s own
   distinction (`[]` = ran and rejected nobody; `None` = nothing consulted) extended to the
   route H2 did not cover.

**THE RECORDS ALREADY WRITTEN ARE MARKED, NEVER DELETED.** `fleet_history.invalidate` appends an
invalidation record and never touches the series, and `f11_first_appearances` skips invalidated
rows — so marking the span neutralises it without destroying a record.

---

## A RESEARCH FIGURE MAY NOT APPEAR PUBLICLY WITHOUT NAMING ITS BOOK (ITEM 22, 2026-10-03)

Item 18 corrected the Index tab. Item 22's survey of the live site found the same figures still
presented as the product in three more places, each **correct about its arithmetic and silent
about its object**:

| surface | figure | what it is |
|---|---|---|
| landing page, `/methodology` | "beat the equal-weighted universe by about **6.6%** annualized" | S22's registered sentence about the research decile |
| `/methodology`, the portfolio page | factor intercept **+6.99%/yr (t = 3.98)** | R1's regression of the research decile's spread |
| `/proof` | the decile ladder, the quarterly distribution | research decile; only the benchmarks table was labelled |

None of them is a wrong number. All of them are the **research decile** — the ranking across
all ~2,500 companies, equally weighted, top 10% — and `INDEX-BOOK` measured how differently the
served book earns: **+4.1209pp** against an equal-weighted basket of its own large-cap tier and
**MINUS 0.0576pp** against the all-cap equal-weighted universe those figures are measured
against. A reader lifting one of them as the Index's is out by most of it.

**THE RULE.** If a public surface quotes a research-decile figure, that surface must also say
which book it is. Pinned by
`tests/test_product_spec.py::NoPublicSurfaceQuotesAResearchFigureUnlabelled`.

Four properties, each of which a mutation walked through before it was added:

1. **PAGE LEVEL, NOT SENTENCE LEVEL.** A sentence-level rule would require the clause beside
   every figure — four hand-maintained copies of one fact, which is the `B7` disease this
   project has paid for more than once. The scope is also genuinely the page's.
2. **RENDERED TEXT, NOT SOURCE TEXT.** The first cut searched the raw file, and the change had
   added a comment to each template *explaining* the rule — which quotes the label. Deleting
   the visible label left the comment and the guard passed; three of seven mutations walked
   through. This is the project's most repeated test defect **inverted**: not a ban tripped by
   prose, but a positive assertion satisfied by prose.
3. **NO DEEPER THAN THE SECTIONS IT COVERS.** `/proof`'s only label used to sit inside
   `{% if p.benchmarks %}`, one level deeper than the decile ladder and the distribution, so a
   payload missing that one section would have printed research figures with the label gone.
   The guard compares `{% if %}` nesting depth. It is a RELATIVE property, not
   unconditionality: the whole page legitimately sits in the `{% else %}` of
   `{% if not p.available %}`, because when the evidence file cannot be read the page shows
   nothing rather than numbers from memory.
4. **THE REGISTERED RESEARCH SENTENCE IS NOT REWRITTEN.** `hold_horizon.DEFENSIBLE` is quoted
   verbatim from the handoff and pinned by `tests/test_hold_horizon.py`. The label is
   **appended** through the mandatory `caveat()`, never spliced in — editing it to fix a
   product problem would silently restate a research claim. `NOT_A_HOLD_RULE` set that
   precedent and this follows it.

**THE DROPDOWN SENTENCE IS GONE.** `backtest_card`'s `basis_note` explained which book a reader
was looking at by pointing at "the one this dropdown selected" — a control session 74 removed.
It names the account-type construction now, which is what actually selects the book and travels
in the payload beside it.

### TWO CLAIMS DON HAS RULED OUT BY NAME

Pinned by `tests/test_product_spec.py::DonsStandingRulesOnWhatMayBeClaimed` across every public
template and `app.js`. Both were reachable from figures that are individually true, which is
why they are a rule rather than a judgement.

- **No "+32%".** Not on any surface, in any spelling.
- **No "the Index beats SPY"**, nor "outperforms SPY", nor "beats the S&P".

**The honest line, which is what a surface may say:** about **2 points a year ahead of SPY in a
Roth over 2009-2026, almost all of it in the first half**. Dated, halved and qualified by
account type. `index_book_measured.card()["halves_note"]` is its source, so a writer reaching
for the qualification does not have to reconstruct it — a refused claim with no permitted
version available is how the refused one gets written anyway.

## A SCREEN SAYS HOW MANY IT CHECKED, NOT JUST HOW MANY IT FOUND (ITEM 23, 2026-10-03)

Item 19 made the Dip Detector measure something. Item 23 found it was measuring **12 of 242
eligible names** and reporting the result as coverage of a market.

**THE CAUSE IS A NUMBER COMPUTED IN EVERY SCAN AND THROWN AWAY.** `prices.py` and
`broker_universe.py` both compute `high_prox = price / 52-week high`; `screen.py` persisted only
its WITHIN-DATE Z-SCORE. **A z-score can ORDER names by drawdown and cannot state one**, so the
screen could rank 242 names for free and had to buy a full valuation to learn any single depth.
`1 - high_prox` IS the drawdown.

**THE RULE:** where a screen's expensive test is gated by a cheap one, the cheap one runs on
EVERY eligible name and the budget is spent on the names that pass it — and the page states
**qualified against checked**. Pinned by `tests/test_dip_preselect.py`.

Three properties, each of which a mutation walked through before it was added:

1. **THE PRESELECTOR IS LOOSE, AND THAT IS WHY IT IS SAFE.** The free drawdown is the
   SNAPSHOT's and the rendered one is the valuation's own as-traded price, so they differ by
   however much the name moved since the scan. `PRESELECT_SLACK = 0.05` is wider than a day's
   move and far narrower than any row this screen has rendered (the shallowest ever shown is
   51% down), so it is a NECESSARY condition that costs nothing while **the measured drawdown
   stays the authority** for what is displayed.
2. **UNKNOWN IS NOT SHALLOW.** A row with no ratio is KEPT. Mid-migration a strict rule would
   delete exactly the names nobody can rank, which is the failure the coverage rule exists for.
3. **THE DEGRADED CASE SAYS SO.** An older snapshot carries no ratio; the screen then behaves
   exactly as before and the page states that depth could not be read without a valuation.

**THE DIAGNOSTIC THAT DECIDED THE DESIGN, taken on the service rather than assumed:** of the 12
names valued, six were 51-66% down and **five of those six were rejected on HEALTH**. The 12
were the DEEPEST 12 — the sort is exact — **so the cap was not hiding anything deeper. It was
hiding everything between the threshold and ~51%.**

### F-11'S FABRICATED ROWS ARE LABELLED, NOT DELETED

`fleet_history.invalidate_unmeasured_dip_span` appends an invalidation over 2026-08-06
(`42597e2`, the cache-wrapper commit, a week BEFORE the screen was built) through a `through`
date the caller supplies. **It is a SEPARATE function from audit #5's
`invalidate_fabricated_span`, deliberately:** that reason describes *a screen that does not
exist in this repository* and freezes its span at first application, because its series start
accruing real rows the moment its caller is fixed. This span has an explicit END, so inferring
it from everything on disk would swallow the good rows already sitting after it. Same shape,
opposite inference — sharing the implementation would give one function two meanings and let
the record claim `H2` had covered this.

**IT MUST BE RUN ON THE SERVICE.** The rows live under gitignored `data/` and exist nowhere in
this repository, so it can be written, tested and shipped here and applied only there.

---

## AN OUTCOME RECORD SCORES ITSELF (ITEM 24, 2026-10-03)

`option_alerts` could only be closed by `paper_track`, which closes a position the PAPER BROKER
bought. `options_tracker`'s own docstring named the source — *"an external scheduled process
(Cowork) writes `exit_*` back"* — and **that process no longer exists**. So an alert the broker
declined, usually on the $1,000 sizing veto, could never be scored.

| | live, 2026-10-03 |
|---|---|
| open | 26 |
| closed | 7 |
| of the open, with no contract at all | 8 |
| ELV alert 14, past its own −50% stop | **−75%**, unscored |
| HCA alert 7, past its own −50% stop AND nine days past its time stop | **−62%**, unscored |

**THE RULE:** a record that reports an expectancy must be able to close its own trades, against
its own logged policy, without depending on anything outside this repository. And a row that was
never scoreable gets its own status — neither `open` (it is not a position awaiting an outcome)
nor `closed` (it has no return to put in a hit rate).

**WHY IT MATTERS MORE THAN A MISSING NUMBER: THE CENSORING IS ONE-SIDED AND CORRELATES WITH
PREMIUM.** Affordability excludes the EXPENSIVE contracts, so the dropped trades are
systematically a particular kind. `MA36` found the same shape one layer down with expiry as the
filter: *"winners and quoted losers are scored and the −100% tail is dropped, which is the
opposite of the backtest this book exists to validate."*

**THE PAPER BOOK STAYS A SEPARATE OBJECT.** It answers what a $1,000-budget account actually
got, fills and sizing included, and is the only measurement this project has of real execution.
Two books, two questions; the self-scorer writes only to `option_alerts`.

### A REFERENCE A STUDY HAS REJECTED MAY NOT BE A SURFACE'S PRIMARY ONE

`/api/options-paper` headlined **+12.88%** as *"the only reference that matches how the live book
trades"*. That is the term-structure filter's late-half expectancy, and **`R7` rejected the
filter on corrected data** — its +8.89pp out-of-sample replication was a `B1` price-basis
artefact, and split-clean it makes its own out-of-sample book WORSE at **−1.12pp against a
+5.00pp bar**. So the surface was comparing the live book against a book nobody runs.

The reference is now the corrected alert book itself, **+3.2702%/trade** (`U1-SPLIT`, n 3,870),
**with `R2`'s control beside it**: five-seed random entry earns **+8.3342%**, so the alert's
day-selection subtracts **5.0640pp** at a paired name-year sign test of z −4.9612.

**THE HONEST REFERENCE CARRIES A NEGATIVE RESULT, WHICH IS WHY IT IS THE RIGHT ONE.** Comparing
the live book against a rejected filter asks whether it keeps up with something we do not run;
the question that matters is whether the alert adds anything, and the measured answer is no.

**RETIRED, NOT DELETED.** Both superseded figures ship in `retired_references` with the study
that retired them and the reason. Deleted, a reader who saw +12.88% could not find out what
happened to it; kept unlabelled, it gets quoted again.

## A LENS THAT CANNOT APPLY IS REFUSED, NOT DOWN-WEIGHTED (ITEM 25, 2026-10-03)

Measured on the live service before any edit:

| ticker | industry | regime it got | fair value | price |
|---|---|---|---|---|
| O | `REIT - Retail` | `growth`, reliability **high** | **$9.46** | $54.13 |
| PLD | `REIT - Industrial` | `mature`, reliability **high** | **$20.39** | $128.91 |
| NEE | `Utilities - Regulated Electric` | `growth`, **confidence high** | **$15.89** | $76.83 |
| DUK | `Utilities - Regulated Electric` | `mature`, *"~0.1 yrs of runway"* | **$43.50** | $114.13 |

**THE RULE.** Where capex IS the business — a property trust's acquisitions, a utility's rate
base — unlevered free cash flow after capex is near zero or negative for a HEALTHY company, so
the FCFF lens is **refused**, not given a low weight. `DCF_QUALITY` at `dcf_reliability: "low"`
is 0.35, which would still leave a $0.75-a-share figure about a third of the blend.
**"Unreliable" and "inapplicable" are different states and a weight vector can only express the
first.** Pinned by `tests/test_valuation_routing.py`.

Four properties:

1. **THE SECTOR IS TESTED BEFORE THE GROWTH BRANCHES.** A REIT growing at 11% is still a REIT.
   Testing it after is exactly how O got `growth` and PLD got `mature` — one cause, two
   wrong answers, decided by which side of an unrelated threshold each fell.
2. **NO MULTIPLE MEANS NOT VALUABLE**, not valued by the lens that does not apply. `UNKNOWN`'s
   principle one layer along: publishing nothing is a claim about our own knowledge, and
   publishing $9.46 is a claim about Realty Income.
3. **CONFIDENCE IS NEVER HIGH** on these regimes. FFO/AFFO and an allowed-return model are the
   right lenses and are not built here, so a multiples-only figure is the best available rather
   than a good one. That is the sentence NEE's `confidence: high` was missing.
4. **`lens_applicability` NEEDED NO CHANGE** and now reports `fcff_applies: False`, because it
   READS the blend's weights. It was answering `True` for a REIT only because the blend had
   given the DCF 75%. The gate was working; it was being fed the wrong weights.

**A MATCHER MAY NOT CONTAIN A TYPOGRAPHIC CHARACTER.** The REIT hint was `"reit—"` with a
U+2014 EM DASH, against live data reading `"REIT - Retail"` with a hyphen-minus, so it had
**never matched anything**. A typographic character in a predicate matched against vendor data
is not a typo, it is a test that cannot fire — and it fails SILENTLY, because the fall-through
produces a confident number rather than an error. The suite bans em dash, en dash and minus sign
from every industry matcher, with a positive control that an ordinary industry is not caught.

**NEGATIVE FREE CASH FLOW IS NOT A BURN HERE.** DUK's *"~0.1 yrs of runway"* is a SOLVENCY CLAIM
about a company whose negative free cash flow is a regulatory asset. The fix is **narrower than
the `financial` branch**, deliberately: leverage and interest cover genuinely apply to both
regimes, so only the free-cash-flow term and the runway inference are dropped and their weight
goes to the two that work. Withholding the whole sub-score would throw away two valid
measurements to remove one invalid one. `is_cash_burning` still reports the measured fact: the
fact is true, only the INFERENCE does not follow.

**A WARNING MUST NAME THE RIGHT CAUSE.** The old text read *"almost certainly a data problem
(currency or share count), not a real opportunity. Verify the figures."* **The data was fine and
the model was wrong**, so the warning sent the reader to verify correct figures and the next
developer hunting a currency bug. A mis-attributed warning is worse than none. The original
message **survives for an ordinary company**, because a 0.2x ratio on an industrial really is
usually a currency or share-count problem.

### `mature` IS A DEFAULT, SO IT MAY NOT ASSERT STABILITY

MRNA at **−16.05%** revenue growth while burning cash was labelled *"Mature, stable profile:
standard 5-year FCFF DCF."* Being un-matched by four tests is not evidence of stability. Same
defect `UNKNOWN` exists for, one layer down — in the regime layer rather than the sector layer.
A `declining` regime now says what it is, and **changes no model**: a 5-year FCFF DCF on a
shrinking profitable business is structurally coherent in a way it is not for a REIT, so
inventing a decline model would be a construction change smuggled in behind a labelling fix.

**TSLA IS DELIBERATELY NOT RE-ROUTED, and this is the half of item 25 that is NOT a defect.**
Its inputs are right (**+7.84%** growth, FCF-positive, profitable) and its $23.42 against
$370.59 comes from ROIC 5% against a **WACC of 14%** — a high beta discounted at the real 5.28%
10-year yield, which is the model working as written. **Routing it out of `mature` to make its
number look better would be choosing the regime on the output.**

### A SYMBOL NOBODY COULD FIND GETS NO SCORE

`ZZZZQ` (nonexistent) and `BRK.B` (real, spelled with a dot) both answered **HTTP 200, score 40,
recommendation "Reduce"**. The 40 is `health: 40.0` standing alone after the valuation was
withheld and the weights renormalised — **one sub-score of a company nobody identified, rendered
as a verdict**. Every honest caveat downstream is about the VALUATION, and `partial_note` cannot
say there is no company.

Now a **404 with no score**, from an explicit `fetch_failed` flag. Three details that are the
rule rather than the implementation:

* **THE DETECTOR IS A CONJUNCTION** — price, revenue AND share count all absent, after every
  source has been asked. Any ONE present means something was found: a real company mid-halt
  still has revenue and shares, a fresh listing still has a price. A disjunction would refuse
  live companies.
* **IT IS NOT `cd is None`.** That was this change's own first cut, and it cannot be reached by
  the case it was written for: `yahoo.fetch` RETURNS a `CompanyData` for a nonexistent symbol,
  with ticker and name populated from the argument and everything else `None`.
* **REFUSED AT THE SURFACE, NOT IN THE ENGINE.** `value_from_company` is also the batch and
  offline entry point, and those callers build a `CompanyData` by hand with no such flag;
  raising there would change what the backtest does on a shape it has always accepted. And the
  result is **not cached**, or the refusal would depend on cache state.

**A SHARE CLASS WRITTEN WITH A DOT IS THE SAME COMPANY.** Normalised **before the first fetch**,
not as a retry on failure: a retry makes the hyphen form a FALLBACK, so the two spellings take
different code paths and only one is ever exercised. Narrow by design — one to five letters, a
dot, a SINGLE letter — because widening it to "any dot" would silently look up the WRONG company
rather than miss cleanly. The rewrite leaves a note on the row.

## WHAT THIS FILE DOES NOT GOVERN

**The rebalance BUILD path.** `python -m valuation.edge.valquo_index --config taxable`, used by
`REBALANCE_RUNBOOK_2026-10-22.md`, builds the next book and is deliberately out of scope here:
this spec governs what surfaces SHOW, and nothing in it may change how a book is BUILT. Nor does
it govern scoring, weights or any recorded figure.
