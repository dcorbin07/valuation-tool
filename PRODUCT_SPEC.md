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
| **The backtest beside it** | the backtest of **the construction the Index uses** — decile, quarterly, 30% no-trade band (`BOOK_CONFIGS["taxable"]`), shown in **two tax treatments of that one book** | when the panel is rebuilt | `index_track.TRACKED_CONFIG`, read through `settings.measured` |

### ONE BOOK, TWO TAX TREATMENTS (17-AMEND, Don 2026-10-02)

The **roth top-25 config is retired from every surface.** Code may keep it for research; nothing
public reaches it.

Beside the forward track, the SAME book is shown in two tax treatments, so the cost of taxes is a
number rather than an inference:

| treatment | basis | from |
|---|---|---|
| **in a Roth/IRA** | net of modelled costs, **no tax** | `measured.net_alpha` / `net_sharpe` |
| **in a taxable account** | **after tax**, via the shipped FIFO lot-level engine | `measured.after_tax_alpha` / `after_tax_sharpe` |

The difference is reported as `tax_cost_pp`. **"Roth/IRA" is now a TAX WRAPPER, not a
construction** — it used to name the 25-name book, which is exactly what put a 25-name backtest
beside a decile record.

**PROVISIONAL AND LABELLED:** both treatments use `book_configs.taxable` until **r1's INDEX-BOOK**
measurement of the exact large-cap-tier construction lands, then both switch to it.

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

## WHAT THIS FILE DOES NOT GOVERN

**The rebalance BUILD path.** `python -m valuation.edge.valquo_index --config taxable`, used by
`REBALANCE_RUNBOOK_2026-10-22.md`, builds the next book and is deliberately out of scope here:
this spec governs what surfaces SHOW, and nothing in it may change how a book is BUILT. Nor does
it govern scoring, weights or any recorded figure.
