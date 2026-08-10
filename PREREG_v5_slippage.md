# PRE-REGISTRATION — V5: measured slippage vs modelled costs

**Owner:** options bot. **Register:** `VALQUO_EXTENSIONS.md` V5. **Date:** 2026-08-09.
**Committed BEFORE `scripts/slippage_report.py` existed and before any fill was read.**

The one thing computed before this file was written is the MODELLED side (section 2), from
already-banked artifacts. That is deliberate and it is the correct order: you must know the bar
before you measure against it, and a bar derived after seeing the measurement is not a bar. The
modelled figures are stated here as literals so a later run cannot quietly move them.

---

## 0 · What this is, and the one thing it is not

V5 builds an INSTRUMENT, not a result. The deliverable is a script that, as sandbox fills
accumulate, answers "is what the paper account actually pays what the backtest charged it?" —
with the sample size printed beside every number, and with a refusal to quote an aggregate that
is too small to mean anything.

**It is not a verdict on the options edge.** R2 stands: the entry signal is dead (real
+3.41%/trade vs a random-entry control's +10.06%, paired name-year sign test z −4.903). A cost
measurement cannot revive an entry signal and will not be quoted as if it could. What it CAN do
is tell us whether the cost model every options number in this repo is net of is right, which
matters for the capacity number and for any future book.

---

## 1 · The object of study

`paper_option_orders` in the screener store, written by `valuation/edge/paper_track.py` against
the Tradier sandbox. Two legs per trade:

* **ENTRY** — `submit_new_alerts` places a LIMIT `buy_to_open` at the current **ask**.
  The fill lands in `entry_premium` via `mark_open`, from the broker's `avg_fill_price`.
* **EXIT** — `close_matured` places a LIMIT `sell_to_close` at the current **bid**.
  The fill lands in `exit_premium`.

Both limits sit at the touch because `options_fill.DEFAULT_AGGRESSION = 1.0` — buy the ask, sell
the bid — is the fill convention every validated options number in this repo is net of.

**The equity mirror is out of scope and there is nothing to measure there anyway:**
`paper_track.seed_book(..., place_equity=False)` is the default and `scripts/paper_track_run.py`
only passes `--place-equity` on request, so no equity fills exist. V5's own text says the output
feeds S14's no-trade band and the capacity number; both of those are EQUITY constructs
(`fundamental_panel.no_trade_band`, `HANDOFF_crowding.md`), so option-leg slippage cannot feed
them. That is recorded as a limitation, not worked around.

---

## 2 · The MODELLED side — the bar, fixed here as literals

Measured on the authoritative R2-corrected book, `data/options_universe/state_r2_corrected.pkl`,
**3,885 trades, `entry_spread_pct` present on 3,885 of 3,885 (100.0%)**. Half-spread paid at
entry is `entry_spread_pct / 2` because `spread_pct = (ask − bid) / mid` and the fill is at the
ask, i.e. `(ask − mid) / mid`.

| modelled quantity | value |
|---|---|
| entry half-spread, mean | **410.0 bps of premium** |
| entry half-spread, median | **333.3 bps** |
| entry half-spread, p10 / p25 / p75 / p90 | 131.8 / 198.0 / 550.0 / 837.0 bps |
| entry half-spread, max | 1250.0 bps (= `MAX_SPREAD_PCT` 0.25 ÷ 2; the cap binds) |
| median entry premium | $2.58 |
| commission | $0.65/contract/leg, **$1.30 round trip** = **50.4 bps** of the median premium |

**THE 33.4 bps FIGURE IN V5'S BRIEF IS AN EQUITY NUMBER AND USING IT HERE WOULD BE A CATEGORY
ERROR OF ROUGHLY AN ORDER OF MAGNITUDE.** 33.4 bps one-way is audit B11's measured cost on the
fundamental panel — basis-points of STOCK NOTIONAL. The options book pays ~410 bps of PREMIUM per
side. The two are not the same currency and 410 / 33.4 ≈ 12×. The comparison this report makes is
against the 410.0 bps line above; the 33.4 bps figure is quoted only to say it does not apply.

---

## 3 · The four measures, and which one is the headline

Every measure is computed per leg and reported with its own `n`.

**M1 — fill vs the order's own limit price.** `avg_fill_price − order.price`, signed so positive
is worse. Requires a live broker read (`--broker`), because the limit is not stored.
**PRE-REGISTERED AS STRUCTURALLY BOUNDED AND THEREFORE NEVER THE HEADLINE:** a marketable limit
cannot fill worse than its limit, so M1 can only ever show zero or price improvement. A report
leading with "0 bps of slippage" would be vacuous. It is computed because price improvement is
real information, not because it tests anything.

**M2 — fill vs the touch, reconstructed offline.** No broker call.
* entry: submit ask = `target_premium / (1 + target_pct)`, exact to the 4-dp rounding
  `_place_entry` applies; `target_pct` from the alert's `features.exit_policy.target_pct`, else
  `options_tracker.DEFAULT_TARGET_PCT = 1.00`.
* exit: the touch is `last_mark`, which audit B5a made the **bid**.
Same bound as M1 in direction, but available with no network and on rows the sandbox has aged out.

**M3 — HALF-SPREAD PAID AT EXIT. THIS IS THE HEADLINE, and it is the only measure directly
comparable to the 410.0 bps bar.** `(last_mid − exit_premium) / last_mid`, in bps. `last_mid` is
the mid stored alongside `last_mark` by audit B5a. Sign convention: positive = the account gave
up that many bps to the mid, which is what a cost is.

> **THE ENTRY HALF-SPREAD IS NOT MEASURABLE FROM THE CURRENT SCHEMA AND THIS REGISTER SAYS SO
> BEFORE THE RUN RATHER THAN EXPLAINING IT AFTERWARDS.** `paper_option_orders` stores no
> bid/ask/mid at submit — only the derived `target_premium`/`stop_premium`, from which the ASK is
> recoverable and the MID is not. The exact fix is two columns (`entry_bid`, `entry_ask` written
> in `_place_entry`), and V5's scope is NEW FILES ONLY, so this report ROUTES that request and
> does not make it. Until it lands, M3 covers the exit leg only, and the report says which leg
> every number belongs to.

**M4 — the non-fill rate, which is the cost M1/M2 structurally cannot see.** A limit at the touch
buys a bounded fill price by accepting the risk of no fill at all. Counted from row state:
`rejected` (entry order ended canceled/rejected/expired without a fill), `still_working`,
`deferred_no_bid` (audit B5's refusal to send a market order), and `skipped` with its reason.
Reported as counts and as a fraction of alerts considered. **A book with excellent measured
slippage and a 40% non-fill rate is a worse book, not a better one**, and only M4 shows that.

**M5 — alert-to-fill drift, reported and explicitly LABELLED NOT SLIPPAGE.**
`paper_option_orders.entry_premium` (the broker fill) vs `option_alerts.entry_premium` (the ask
quoted when the alert fired). Those are different timestamps, so the difference is signal decay
plus execution latency plus spread movement, not execution quality. It is reported because it is
the number most likely to be mistaken for slippage by a reader, and naming it defuses that.

---

## 4 · Minimum n, inference, and the verdict rule

**MINIMUM SAMPLE: 30 filled legs of a given kind.** Below 30 the script prints the individual
rows and `NOT QUOTABLE (n=<k> < 30)` and computes no mean, no CI and no verdict. This threshold
is committed here and is not a suggestion the runner may relax with a flag.

**Inference: percentile bootstrap, 2,000 draws, seed 0, CLUSTERED BY CALENDAR WEEK.** Legs are
not independent — the same alert engine fires several names on one day and one name can appear
repeatedly — so a per-leg bootstrap would be optimistically narrow in exactly the way audit R3
found every earlier options interval was. Weeks are resampled with replacement and all legs in a
week travel together. The **90% CI** is the pre-registered interval (V5's own text).

**VERDICT RULE, on M3 (exit half-spread) against the modelled 410.0 bps mean:**

| condition | verdict |
|---|---|
| n < 30 | **INSUFFICIENT** — no aggregate printed |
| 90% CI excludes 410.0 and lies ABOVE it | **DIVERGENT-COSTLIER** — the model understates costs |
| 90% CI excludes 410.0 and lies BELOW it | **DIVERGENT-CHEAPER** — the model overstates costs |
| 90% CI contains 410.0 | **CONSISTENT** |

A DIVERGENT-CHEAPER verdict does **not** license lowering the modelled cost, for the reason in
section 5: sandbox fills are optimistic, so cheaper-than-modelled is the direction the
measurement error already points. Only DIVERGENT-COSTLIER is actionable on its own.

---

## 5 · The caveat that must appear in every output

**Tradier sandbox quotes are delayed ~15 minutes and sandbox fills are simulated against them, so
every fill here is optimistic relative to a live account.** `paper_broker.DATA_CAVEAT` says the
same and the script prints it on every run, in every mode, including `--json`. A measured cost
LOWER than modelled is therefore the expected direction of the bias and is weak evidence; a
measured cost HIGHER than modelled is evidence in the direction the bias runs against, and is
correspondingly stronger.

---

## 6 · Expectation, written down first

**Expected outcome: INSUFFICIENT, at 90/10.** The paper track's own tables have held zero rows in
every store this lane can reach, and the fills accrue on Render's disk behind
`/admin/run-paper-track`. The instrument is expected to land before the data does.

Conditional on ever reaching n ≥ 30: **DIVERGENT-CHEAPER at 60/40**, because a delayed-quote
sandbox fills at prices a real book would not get. Recorded because this project's directional
expectations have been wrong more often than right, and writing them down is the only thing that
makes that measurable.

---

## 7 · What this cannot see, stated in advance

* **The entry leg's half-spread** (section 3) — schema gap, routed not fixed.
* **Real-market impact.** A sandbox has no book to move. The capacity question needs live fills
  or a market-impact model; this measures neither.
* **Anything at the size the capacity number cares about.** `paper_contracts_per_trade` defaults
  to 1. A 1-lot fill says nothing about a 100-lot fill, and the report says so beside any number
  a reader might carry to the capacity discussion.
* **Whether the alert was worth taking.** That is R2, and it is answered: no.

---

## 8 · Trial accounting

This is instrumentation. It searches nothing and selects nothing, so it is charged to the
**infra** domain at `n=1` on the HACFLOOR / CHAINFREEZE precedent, and **the options trial count
stays 192 and the equity count stays 130**. No DSR-gated claim moves. Should the instrument later
produce a quoted verdict on costs, that verdict is a separate row and is charged then.
