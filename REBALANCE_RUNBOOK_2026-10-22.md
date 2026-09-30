# REBALANCE RUNBOOK — 2026-10-22

**For Don.** Two paths, because `D9` came back **NO-GO** (`bb4b4fc`, 2026-09-30). Path **A** is
the free live route and runs **only** if a same-date D9 re-check reads **GO**. Path **B** is the
Sharadar route and is the fallback D9 routed.

**NEITHER BOOK IS BUILT.** This file is commands and gates. Nothing here has been run, no book
has been written, and the bound record is untouched.

**THE DATE.** 63 trading days from the 2026-07-24 scan is **Thursday 2026-10-22**. The disabled
task's "Oct 1" is a *calendar-quarter* convention — a different rule, not different arithmetic.
Three weeks apart, so it is a real choice and it is Don's. **The rebalance is late either way**;
log it as a delay with its reason rather than let it read as a book that silently stopped.

---

## 0. THE VINTAGE CALL, PER PATH — READ THIS FIRST

`PAPER_TRACK_CONTRACT.md` §5a, verbatim:

> any **ADOPTED** change to scoring, weights, or construction closes the current vintage and
> opens the next … **Rebalancing under unchanged rules is NOT a vintage event.**

| | verdict | why |
|---|---|---|
| **Path B — Sharadar** | **NOT a vintage event** | Same vendor the book in force was built on, same construction (decile of the large-cap tier, score-weighted, 8% cap, 30% band), same flat weights. This is *rebalancing under unchanged rules*, which §5a names explicitly. |
| **Path A — free live** | **VINTAGE EVENT — opens vintage 5** | Not a judgement call: on §5a's own wording it changes **weights** and **scoring**. |

**PATH A IS A VINTAGE EVENT ON THE RULE'S OWN WORDING, AND THE ARGUMENT DOES NOT REST ON THE
VENDOR.** Two of the three named triggers are hit outright:

* **weights** — the live composite uses **bucket-specific weights**; the panel the record was
  built on uses **flat 1/7**. That is D9's own premise correction, made before any cross-vendor
  number was read, and it is why its primary had to be reconstructed like-for-like.
* **scoring** — the live path serves **five** of the seven weighted themes. `institutional` and
  `insider` reach no live score (`theme_contributing` 0.0 / 0.0 on the 2026-09-29 scan), so the
  book would be selected by a different composite from the one the record measures.

**A GO FROM D9 WOULD NOT CHANGE THAT, AND THIS IS THE THING MOST LIKELY TO BE MISREAD.** D9 asks
whether the live path *ranks the large-cap tier closely enough* — a question about the resulting
**ranking**, not about whether the **rules** are the same. A GO says the vendor switch is
survivable; it does not make the weights flat or restore two themes. **So Path A opens vintage 5
whether D9 reads GO or NO-GO.**

**AND IF MC1'S THEME CACHE IS IN FORCE BY OCT 22, PATH A IS STILL A VINTAGE EVENT — A DIFFERENT
ONE.** That cache restores `institutional` and `insider`, making the live book **seven**-theme.
That is a scoring change too, so the vintage opens either way; what changes is *what vintage 5
is a vintage of*. Record which, because "vintage 5" with no statement of the theme set in force
is not a record of anything. (`HANDOFF_appfixes.md` session 60, MC1 follow-up 1: restoring the
banked reference to run `--fidelity` flips the seven-theme book on for every local scan for up
to 120 days — an unannounced vintage change arrived at by putting a file somewhere. The
reference has its own name now and a test pins it, but the *deliberate* version of that switch
is still a vintage event.)

**RULE 6 IS THE PRICE — AND A CORRECTION TO THIS FILE'S OWN FIRST VERSION, MEASURED
2026-09-30.** It said *"Path A spends all of it, Path B spends none."* That is right about the
**60-month statistical clock** and wrong about the **6-month operational gate**, and the
difference decides how the two paths really compare.

**THE OPERATIONAL GATE IS ALREADY OWED A RESTART, UNDER EITHER PATH.** Measured on
`/api/index-track`: vintage 4 is **43 trading days old with 24 recorded — 19 missing, 44%**, and
the contract's own gate row reads `passed: false` with the reason *"it cannot [pass], until the
bound series has a verified automated daily writer (§7.2)"*. §3's gate is a test of **recording,
not returns** — *"daily rows with no gaps"* — and §3 says **"if the gate fails, the clock
restarts from the repair"**. So that clock restarts from the day the writer is fixed, for reasons
that have nothing to do with the rebalance and that neither path changes.

**SO THE LIKE-FOR-LIKE COMPARISON IS NARROWER THAN IT LOOKS:**

| | 60-month statistical clock | 6-month operational gate | money |
|---|---|---|---|
| **Path B** | **preserved** (vintage 4, inception 2026-08-13) | restarts from the writer repair | one month of Sharadar |
| **Path A** | **restarts** (vintage 5) | restarts from the writer repair | none |

**The thing Path B actually buys is the 60-month clock**, which is the expensive one — not "ten
weeks of record", because those ten weeks are 44% unrecorded and the gate that reads them cannot
pass as things stand.

---

## 1. THE DECISION GATE — A SAME-DATE D9 RE-CHECK

D9's NO-GO was measured on a **2026-08-08** live snapshot against a **2026-07-31** Sharadar
freeze — a six-trading-day gap, and a snapshot that **predates the MC1 theme cache built
2026-09-30**. So it measures a *weaker* free path than Oct 22 would use. That is the one caveat
that runs in the free route's favour and it is why a re-check is worth running rather than
assuming the old verdict.

**It is also why the re-check must be SAME-DATE.** Comparing a fresh live scan against a stale
Sharadar freeze re-introduces exactly the drift the bars exist to exclude: D9 measured the
Sharadar panel against *itself* at 63 trading days reading **0.4971**, i.e. below its own B1 bar
of 0.80. **A cross-vendor comparison across a gap cannot pass and cannot fail informatively.**

```
# Requires a RENEWED Sharadar export, so this gate is only reachable on Path B's data anyway.
python -m scripts.d9_fidelity --sharadar     # score the Sharadar side
python -m scripts.d9_fidelity --compare      # read B1/B2/B3 against the bars
```

**GO requires ALL of** (fixed in `PREREG_d9_free_route_fidelity.md` §4 before any number existed,
and **may not be relaxed after watching them fail** — §6's own rule):

| | bar | 2026-09-30 reading |
|---|---|---|
| **B1** like-for-like composite Spearman | ≥ 0.80 | **0.4321** (0.6610 repaired) — FAIL |
| **B2** top-decile overlap | ≥ 0.60 | **0.2326** (0.3721 repaired) — FAIL |
| **B3** per-theme Spearman, each of value/quality/momentum/size | ≥ 0.70 | value 0.7869 ✓, momentum 0.9651 ✓, size 0.9840 ✓, **quality 0.6256 — FAIL** |

**Ambiguous against a bar is NO-GO** (`RUN_RULES` A6).

**THE CATCH WORTH SAYING OUT LOUD: the re-check needs a renewed Sharadar export to run at all.**
There is no Sharadar side to compare against without one. So the sequence is *renew first, then
decide* — and once renewed, **Path B is available and costs no vintage**, which is the cheaper
answer unless the re-check reads GO *and* Don wants to spend the clock.

---

## 2. PATH A — THE FREE LIVE ROUTE (only if the re-check reads GO)

**Vintage event. Opens vintage 5.** Do not run this without deciding to spend the clock.

```
# 1. A fresh full scan on the live route (800-name universe unless SCAN_LIMIT is raised).
python -m valuation.screener.scan

# 2. Build the book from the saved snapshot, with the CONTRACT construction.
#    --config taxable is the decile book: score-weighted, 8% cap, 30% no-trade band.
#    --out MUST be the book in force (see §4 — this is how `held` is supplied).
python -m valuation.edge.valquo_index --config taxable --out data/valquo_index.json

# 3. Freshness gate (§5) — refuse to proceed unless it reads fresh for 2026-10-22.

# 4. Write the 2026-10-22 row FIRST, then append the event dated 2026-10-22 (§3).
```

---

## 3. PATH B — THE SHARADAR ROUTE (the fallback D9 routed)

**Not a vintage event.** Same vendor, same rules, same construction as the book in force.

**Requires a one-month Sharadar renewal** — the entitlement lapsed in August. That is the whole
cost, and it is the only thing that puts both sides on the same date *and* compares against the
post-MC1 build.

```
# 1. Refresh the export with the renewed entitlement (the normal bulk pull), then build
#    DIRECTLY from it -- --full-universe reads the export rather than a live scan snapshot.
python -m valuation.edge.valquo_index --full-universe data/backtest \
       --config taxable --out data/valquo_index.json

#    `--config taxable` sets: top decile of the large-cap tier, score-weighted,
#    8% cap, exit_frac 0.30. Verify the printed line says "no-trade band 30%".

# 2. Freshness gate (§5).

# 3. Write the 2026-10-22 row FIRST, then append the event dated 2026-10-22 (§4).
```

---

## 4. THE APPEND — THE SAME FOR BOTH PATHS, AND THE ORDER MATTERS

**Write R's row first, then append the event dated R.** `index_mark.append_rebalance` **refuses
an unanchored date** — a rebalance dated on a day the track never marked. That refusal is the
point: an anchor off by one session shifts every subsequent row by a constant nobody can find.

```
# dry run first -- without --send this sends nothing
python -m scripts.seed_track --rebalance data/valquo_index.json \
       --rebalance-date 2026-10-22 --pull

# then, once the dry run reads clean:
python -m scripts.seed_track --rebalance data/valquo_index.json \
       --rebalance-date 2026-10-22 --pull --send
```

`--pull` pulls the service's recorded series first and **refuses to upload unless the local one
is a superset of it, cell for cell**. The HTTP door `POST /admin/track-rebalance` and this CLI
both delegate to `index_mark.append_rebalance`, so they cannot drift into two ideas of a legal
event. **Re-sending the identical event is a no-op, not an error**, so a retried command cannot
corrupt anything.

Refused, by the library: not the contract-bound Index, dated on or before the last event, a
rewrite of an existing event, an unanchored date, or on/before inception.

---

## 5. THE FRESHNESS GATE — BOTH PATHS

The book's own payload carries it. Refuse to append unless, for `2026-10-22`:

* `freshness.as_of` == **2026-10-22** and `as_of_is_trading_day` is **true**
* `freshness.stale` is **false**
* `contract_conformance.conforms` is **true**

**`conforms: false` is the live state today and it is not a bug** — `/api/valquo-index` serves
the **roth** preview (25 positions) against the contract's floor of 50. **`roth` is NOT the
contract book.** Build with `--config taxable` or the conformance gate will refuse, correctly.

---

## 6. THREE THINGS THAT WOULD SILENTLY PRODUCE THE WRONG BOOK

**1. THE 30% BAND APPLIES ONLY IF THE PREVIOUS BOOK IS AT `--out`.** `export()` supplies `held`
from `_previous_book(path)`; `build_index` needs **both** `held` and `exit_frac` and does nothing
without either. Measured on the live endpoint right now:
`no_trade_band: {"applied": false, "note": "no previous book supplied"}`. **Point `--out` at the
book in force** (or copy it there first) and then **check the emitted payload says
`applied: true` with a non-empty `band_retained`**. A silently band-less rebalance is a
construction change — it turns the book over harder than the adopted rule does — and it would
look like an ordinary rebalance in every surface.

**2. THE CLI HELP STRING IS STALE AND UNDERSTATES THE BAND.** `--config`'s help reads
*"'taxable' (decile, quarterly, **20%** band)"*; the shipped `BOOK_CONFIGS["taxable"]["exit_frac"]`
is **0.3**, matching `no_trade_band.BAND_WIDTH = 0.30` and S14's adopted width. **The code is
right and the help is wrong.** Reported, not edited here — it is a one-line fix in
`valuation/edge/valquo_index.py` and it belongs with whoever next touches that file. Trust the
printed `no-trade band 30%` line, not the `--help` text.

**3. THE FIRST BANDED REBALANCE CANNOT SHOW A BAND EFFECT.** With no previous book there is
nothing to hold, so the band's effect begins at the **second** rebalance. If Oct 22 is the first
one after the band shipped, `band_retained` being small is expected and is not evidence the band
is broken.

---

## 7. WHAT THIS RUNBOOK DOES NOT DO

* **It builds neither book**, as instructed.
* **It does not renew Sharadar** and does not spend money.
* **It does not decide the date** (2026-10-22 vs Oct 1) — that is Don's, and both are defensible.
* **It does not decide the path.** Path B is cheaper on the contract (no vintage) and costs a
  month of Sharadar; Path A costs the accrued clock and is free. That trade is Don's.
* **It does not re-run D9.** The re-check is listed because it is a precondition of Path A, not
  because it has been done — and it is unreachable until an export exists.
