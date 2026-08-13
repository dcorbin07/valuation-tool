# Scream-buy options track record — reset of 2026-08-13

**Status: IN FORCE.** This is the register note for a deliberate, dated reset of the
scream-buy options track record. It exists so that the reset is a recorded decision with a
stated reason, rather than something a reader has to reconstruct later from a gap in a table.

The surface renders the one-line form of this note in the tab footer
(`valuation/web/scream_track.py::RESET_NOTE`), and the constants below are the ones the code
actually reads — not a transcription of them.

---

## 1. What was decided, and by whom

Don, 2026-08-13: *"the options scream buys track record wiped, and include target sale, price
bought in, and current price, same as our paper account tracks."*

| | |
|---|---|
| Reset date | **2026-08-13** |
| Effect | Alerts stamped on or after that date form the displayed record |
| Prior record | **Archived, not deleted** — see §3 |
| Archive path | `data_export/paper_track_history.json` |
| Code | `valuation/web/scream_track.py` (`RESET_DATE`, `ARCHIVE_PATH`, `RESET_NOTE`) |

## 2. Why — and the reason is not performance

The prior record predates the corrected alert stack, and the corrections were not cosmetic:

* **B1 — the price basis.** Every underlying price the options book was measured against was
  mis-stated: an adjusted spot was being compared against as-traded strikes. Repairing it
  moved the trade count 3,042 → 3,885, because a moneyness prefilter had been silently
  discarding 1,182 alerts, and moved median entry IV **1.4200 → 0.2497**. 142% was never a
  volatility.
* **U1-SPLIT (2026-08-11).** Option chains are as-traded and unadjusted for splits while bars
  are adjusted, and nothing in the options lane consulted the split table. One GE contract
  booked **+31,921%** against a true value of zero. This accounted for 24% of the published
  R2 gap.
* **The fields Don actually asked about.** The old rows carried no target, no stop and no
  current mark, so the record could not answer "what was it bought at, what is it worth now,
  and where does it get sold?" — which is the complaint that prompted the reset.

**The disclosure that has to travel with any reset:** discarding a stretch of a track record
is the flattering direction by default, so the reason has to be independent of the outcome,
and a reader has to be able to check that for themselves. Both conditions are met here — the
cause is a set of dated code corrections that landed before this decision, and the archive
path is on the surface, not merely in this file. This is the same standard `PAPER_TRACK_CONTRACT.md`
§5a set when Amendment 1 voided run #1 while it sat −2.85pp: *the cause was independent of the
outcome, its clause pre-existed the run, and the voided rows were kept and stayed visible.*

## 3. Nothing was deleted, and that is checkable

The word "wipe" describes what the reader sees, not what happened to the data. The prior
record survives in two independent places:

1. **The database.** No row was deleted, updated or hidden at the source.
   `valuation/web/scream_track.py` is a reader — it contains no SQL that writes, and a test
   pins that. The reset is a display epoch implemented as a date comparison.
2. **The committed archive.** `data_export/paper_track_history.json` carries the full
   `option_alerts` and `paper_option_orders` tables and is written by the weekly
   `track-backup` GitHub Action. It was already an archive before this decision — the reset
   neither created it nor depends on it continuing to run.

An **undated** row counts as archived rather than current. The alternative — treating "no
date" as "after the reset" — would let the old record leak into the new one through exactly
the rows whose provenance is least clear.

## 4. What the rebuilt record shows, and where each number comes from

Every figure is **read** from a stored column, never recomputed:

| Display | Column | Notes |
|---|---|---|
| Price bought in | `paper_option_orders.entry_premium` | the **fill**, not the submit price |
| Target sale | `paper_option_orders.target_premium` | the alert's own policy; **+100%** by default |
| Stop level | `paper_option_orders.stop_premium` | **−50%** by default |
| Current price | `paper_option_orders.last_mark` | stale-marked from `last_mark_ts` |
| DTE remaining | derived from `expiry` | negative means past, and is shown as such |
| Status | `state` + `exit_reason` | LIVE / HIT TARGET / STOPPED / TIME-STOPPED / EXPIRED |

**Why "read, not recomputed" is a correctness rule and not a style preference.** Session 16
found that `_place_entry` anchored target and stop to the *submit* price while `mark_open`
overwrote `entry_premium` with the *fill* — so **2 of 3 open positions were trading to levels
no backtest describes**, and MET sat 10.2% above a stop the strategy would never have taken. A
display that re-derived `entry × 2.0` would have agreed with the repaired code by coincidence
and stopped agreeing the first time an alert carried a non-default policy.

## 5. What this record still does not claim

The R2 context line renders with the table and is quoted from `web/payoff.py`, the one module
that owns it, rather than restated here. In short: measured against random entry on the same
names, this book's day-selection **subtracted** value (−5.06pp per trade, sign test p < 1e-5).
The alerts are an idea generator, not a demonstrated edge, and a run of losses is the texture
of a convex payoff rather than a fault in it.

A reset does not change any of that. It changes which rows are on the screen.
