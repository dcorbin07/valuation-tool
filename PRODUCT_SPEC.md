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
| what the contract's arithmetic uses today | +9.9864 pp — **wrong book AND gross** | 11.40 | 242 |

So the forward test **can** show whether the Index is being recorded honestly and whether its
costs and turnover behave as modelled. It **cannot** show whether the Index beats SPY: no
five-year result, in either direction, would settle that.

**THE SIGNED CONTRACT IS NOT EDITED.** `PAPER_TRACK_CONTRACT.md` §2's arithmetic rests on the
figure in the last row, and σ may never be revised downward (the contract's own rule — at 1.5×
the assumed volatility the false-crossing rate is 20%). The correction is drafted as a proposed
amendment in **`PREREG_DRAFT_contract_amendment_2.md`** for Don, not applied here.

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

## WHAT THIS FILE DOES NOT GOVERN

**The rebalance BUILD path.** `python -m valuation.edge.valquo_index --config taxable`, used by
`REBALANCE_RUNBOOK_2026-10-22.md`, builds the next book and is deliberately out of scope here:
this spec governs what surfaces SHOW, and nothing in it may change how a book is BUILT. Nor does
it govern scoring, weights or any recorded figure.
