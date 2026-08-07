# HANDOFF — live app (app-fixer lane)

Own lane: live scan / universe / display. Does not touch `valuation/edge/` options work, the
ThetaData miner, or `fairvalue.py`.

---

# Session 17 — 2026-08-06 — The leak is NOT closed. The stopgap stays up.
(PROMPT_web_verify_the_leak_is_closed.md)

Verification, not construction, and it took about an hour because the answer was no.

**THE HEADLINE: CONSOLIDATE-1 is correct and it does not reach production. All three names are
still served on the public hot list with fair values today, and there are TWO independent
reasons, not one.** The disclosure sentence stays up because the condition it describes still
holds — removing it would have been the worst available outcome.

## 1. WHAT THE THREE NAMES RENDER TODAY (production, signed out, 2026-08-06)

`GET https://valquo.co/api/hotstocks?top=500`, scan 2026-08-06, 500 rows served:

| name | price | fair value ON THE PUBLIC HOT LIST | ratio | method | rank | `fair_value_withheld` |
|---|---|---|---|---|---|---|
| KSPI | $92.19 | **$299.16** | 3.24x | blended | 3 | **None** |
| STLA | $5.63 | **$21.09** | 3.75x | blended | 468 | **None** |
| CHTR | $153.17 | **$370.33** | 2.42x | multiples | 225 | **None** |

`GET /api/whatdo?ticker=…` serves the identical numbers **plus an upside**: KSPI **+224%**,
STLA **+275%**, CHTR **+142%**, all with `fair_value_withheld: false`.

And the valuation engine, run today on live data, **refuses all three**:

| name | price | model | ratio | verdict |
|---|---|---|---|---|
| KSPI | $91.80 | $1,032.49 | **11.2x** | REFUSED |
| STLA | $5.55 | $35.57 | **6.4x** | REFUSED |
| CHTR | $157.44 | $1,237.96 | **7.9x** | REFUSED |

So the disagreement Session 14 found is intact, unchanged in kind, and live.

## 2. WHY — AND IT IS TWO BUGS, WHICH IS THE PART WORTH READING

**CONSOLIDATE-1 itself is right.** `screen.py::_enrich_with_dcf` now calls
`publication.record_refusal(r, reason)`, which sets `fair_value_withheld` / `_reason` — the
exact keys `web/withhold.py` honours — and `fairvalue.estimate_fair_values` skips a row
carrying that flag. Verified by running the serve path with the flag in memory: the row comes
out `fair_value=None, method="withheld"`. **That half works.**

### BUG A — the refusal does not survive the snapshot

`store.save_snapshot` writes a **fixed 18-column INSERT** (`scan_date, ticker, name, sector,
bucket, price, market_cap, hot_score, composite, rank, z_*, fair_value, upside, extra`).
**`fair_value_withheld` and `fair_value_withheld_reason` are not among them, and the
`snapshot_rows` table has no column for them.** The scan records the refusal; the database
throws it away; `load_snapshot` returns `fair_value=None` with no flag; `estimate_fair_values`
— which runs at **serve** time, in `web/app.py:494`, on the rows read back — reads that as "no
DCF yet" and substitutes the peer estimate. **The original leak, one layer further down.**

Reproduced on the **real 500 production rows**, same `Store`, same serve path:

```
after record_refusal:  KSPI withheld=True  fair_value=None

A: serve WITHOUT the snapshot round-trip   -> fair_value=None  method=withheld   (correct)
B: serve THROUGH the snapshot, as prod does -> after round-trip: withheld=None
                                            -> fair_value=299.15505668088286
                                               method=blended  ratio 3.24x
```

**That is production's number to the last digit** — `$299.15505668088286` is exactly what
valquo.co serves. The mechanism is not inferred.

### BUG B — two of the three names never get a DCF at all

`_enrich_with_dcf` only runs on `rows[:run_dcf_top]`, and production runs **`dcf_top=12`**
(`scripts/ci_scan.py:83`, `SCAN_DCF_TOP` default 12). **KSPI is rank 3 — inside. CHTR is rank
225 and STLA rank 468 — outside.** Those two are never valued during the scan, so no refusal
is ever *recorded* for them, and fixing Bug A alone would still leave them on the list.

**This is the more structural of the two.** For the ~488 served names that never get a DCF, the
public hot list publishes a peer estimate with no check against the valuation page's refusal at
all — only the 5x band guard, which by construction cannot see this class (a refused 11x model
is replaced by a 3.2x peer estimate, comfortably under the band).

## 3. THE CATCH-ALL — GREEN, AND THAT IS NOT REASSURING

`test_no_public_api_response_carries_a_fair_value_past_the_band` passes, walking
`/api/hotstocks` and three `/api/whatdo` shapes. Full suite: **24 suites, all exit 0**
(`test_withhold` 29/29 incl. one new xfail; `test_edge` 243/243).

**The catch-all cannot catch this leak and never could.** It walks *ratios*, and every name in
this class sits under the band. It was built for the AEG case (5.25x) and it still guards that.
Saying so plainly matters more than the green tick: **this leak was found by probing production
both times, and a passing catch-all is not evidence it is closed.**

So the catch-all is now paired with a test that asserts the other property —
`test_a_refusal_recorded_by_the_scan_survives_to_the_public_surface`, using a **real `Store` on
a temp file** rather than the fake (a fake that carries the dict through would prove the exact
opposite of the truth). It is marked `known_failure`, the same mechanism `tests/test_guards.py`
uses, so it reports **XFAIL** with the owning lane named and does **not** turn the gate red —
the repair is `screener/store.py`, another lane's file, and the gate auto-merges to main for
everyone. It flips to a loud XPASS the day that lane fixes it.

## 4. THE STOPGAP STAYS UP

**Not removed, because it is still true.** `app.js:964` still reads *"Known inconsistency,
stated rather than hidden … when they disagree, the Single-valuation page's refusal is the one
to believe"*, and it names Kaspi, which is precisely the case still live. A stopgap removed
while the condition it describes still holds is worse than the stopgap — so nothing was
touched. **It comes down in the same commit that fixes Bug A and Bug B, not before.**

## 5. TODAY'S REFUSED SET — STILL EXACTLY THREE

Measured today against live data, not carried forward:

| refused | published |
|---|---|
| **KSPI (11.2x), STLA (6.4x), CHTR (7.9x)** | GILD 1.20x, CI 3.64x, JD 3.30x |

Unchanged from Session 15's three. GILD, CI and JD are still out of the set.
**Any figure quoting a fixed count is stale by construction** — this set moves whenever the
engine changes, it has been five and then three inside a week, and the sweep above is bounded:
it re-checked the six known candidates, not all 500 names. A name that entered the set today
without ever having been in it would not appear here. The cheap enumeration is not available
either — a refused row is only distinguishable by `fair_value_method="withheld"`, and Bug A
means no row ever carries it.

**CI is worth one line:** still published at **3.64x — $1,002.42 against a $275.25 price**,
under the band and therefore untouched by every guard in this lane. That is the "+275% at HIGH
confidence" item already routed to the engine/DCF lane; it has not moved.

## 6. SIDE EFFECTS ON OTHER SURFACES — NONE FOUND

Checked every public surface that consumes a fair value or a score: `/api/hotstocks`,
`/api/whatdo` (three shapes), `/api/rank` (reads `base_fair_value`, unaffected), `/api/regime`,
`/api/health`, the exports, the partial-score render, the Watchlist cell and the Index tab —
all still behave as Sessions 13–15 left them, and all 24 suites are green. **The two
consolidations changed the engine and the scan; they did not move anything else on the web
side.**

## BUGS FOUND

1. **`store.save_snapshot` silently discards `fair_value_withheld` / `_reason`** — the fixed
   column list has no place for them and `snapshot_rows` has no column. This is what keeps the
   public leak open for KSPI. **→ screener lane.** One row-shaped fix: add the two columns, or
   stash both keys inside the `extra` JSON blob that is already persisted and rehydrated.
   Encoded as an XFAIL in `tests/test_withhold.py` so it is visible on every run.
2. **`dcf_top=12` means a refusal can only ever be recorded for twelve names.** CHTR (rank 225)
   and STLA (rank 468) are outside it, so Bug A's fix does not reach them. **→ screener /
   engine lanes**, and it is a policy question, not a typo: either the hot list stops publishing
   a peer estimate for names the DCF has not vetted, or the refusal has to be derivable without
   running a full DCF on 500 names.
3. **A passing catch-all was read as evidence the surface was safe.** It was mine, from
   Session 14, and it walks ratios only — so it is structurally blind to a refusal replaced by
   an in-band estimate. Now paired with the round-trip test above. Recorded because the lesson
   generalises: *this suite's green tick covers the band, not the refusal.*

## LEDGER

**No row updated, and that is not an omission.** `VALQUO_LEDGER.md` is one row per external-audit
item from `valquo_audit_items.json`; this work came from a PROMPT file and has no audit id
(grep for leak / fair value / publication / consolidate returns nothing). Inventing a row would
break the file's own contract. My last audit row, **P3**, was updated in Session 16 and is
unchanged.

---

# Session 16 — 2026-08-06 — P3: designing for a 37% hit rate
(PROMPT_p3_design_for_a_37pct_hit_rate.md)

Audit item **P3**. The product disclosed the hit rate and did not design for it. Disclosure
tells a reader that losses are common; it does not tell them whether **their** run of losses is
common, and that difference is the whole item. New module `valuation/web/payoff.py`, wired into
four surfaces, pinned by `tests/test_payoff.py` (30 tests).

---

## 1. THE DISTRIBUTION, MEASURED FIRST — BEFORE ANY DESIGN

Source: `data/options_universe/UNIVERSE_RESULTS.json`, the **B1-corrected 187-name book, 3,885
closed trades, 2016-01 to 2025-10**. No backtest was run for this session; every figure is read
off banked artifacts. The superseded 3,042-trade pre-correction book is quoted nowhere.

### The shape

| outcome | share of all trades |
|---|---|
| lost almost everything (worse than −90%) | **1.4%** |
| hit the stop (−45% to −90%) | **58.2%** |
| small loss (0 to −45%) | 5.0% |
| small win (up to +100%) | 10.3% |
| **at least doubled (+100% or better)** | **25.0%** |

| statistic | value |
|---|---|
| hit rate | **35.3%** |
| average win | +114.6% |
| average loss | −57.3% |
| **median trade** | **−52.2%** |
| expectancy / trade | +3.4% |
| profit factor | 1.09 |
| **share of ALL winnings made by the ≥+100% trades** | **86.8%** |

The single most useful line for a user: **the middle trade loses more than half the premium, and
seven eighths of everything the winners made came from the quarter of trades that doubled.**

### The two hit rates reconcile by UNIVERSE, and this was worth checking

The live confidence tables quote **37.4%** (55-name book) while the broad corrected book says
**35.3%**. The obvious worry is that the older figure is pre-B1 and wrong. **It is not.** The
corrected book splits cleanly and the megacap half reproduces the published number almost
exactly:

| slice | n | hit rate | expectancy |
|---|---|---|---|
| 54 original megacaps | 1,532 | **37.27%** | +9.37% |
| 132 names added by the breadth run | 2,353 | 34.04% | −0.47% |
| whole book | 3,885 | **35.32%** | +3.41% |

So the endpoints mean something specific — 37% is the megacap book, 35% is the broad one — and
`HIT_RATE_RANGE = "35-37%"` is a measurement, not a hedge. Every surface now quotes the range.
This also closes a defect I would otherwise have filed: two surfaces of one product quoting hit
rates 2.1pp apart with nothing on either saying why.

### WHAT DOES NOT EXIST, STATED RATHER THAN ESTIMATED

**The corrected book's per-trade SEQUENCE is not banked.** `HANDOFF_edge_audit.md:3041` names it
`r2_state.pkl`; it was a temp file and it is gone. `data/options_universe/state.pkl` holds only
the superseded 3,042-trade pre-correction rows. **So a streak table measured on the real alert
sequence cannot be computed from anything on disk**, and I did not estimate one.

What IS banked from the corrected era is the **seed-0 random-entry control**
(`control_rows.pkl`, 6,032 trades, written 2026-08-05, carrying the O20 point-in-time liquidity
fields that date it to the corrected run). The streak table is measured on that, and the
substitution is stated on every surface that shows it. **It is conservative in a direction worth
spelling out: the control hits 37.2% against the book's 35.3%, and a higher hit rate means
SHORTER losing runs — so this table understates the real book's streaks.** The interface will
therefore call a genuinely ordinary run unusual slightly too often and never the reverse, which
is the direction an honest design errs in.

### How long is an ordinary losing run

Measured on that sequence, sliding windows, longest losing run inside each stretch:

| stretch | median | p75 | p90 | p95 | worst | disjoint stretches |
|---|---|---|---|---|---|---|
| 10 trades | 4 | 5 | 7 | 9 | 10 | 603 |
| **20 trades** | **5** | **7** | **10** | **12** | **20** | 301 |
| 30 trades | 6 | 9 | 12 | 15 | 27 | 201 |
| 50 trades | 7 | 10 | 15 | 17 | 27 | 120 |

P(some losing run of at least k), by stretch:

| stretch | k=4 | k=5 | **k=6** | k=8 | k=10 |
|---|---|---|---|---|---|
| 10 | 54% | 36% | **23%** | 9% | 4% |
| **20** | 78% | 60% | **44%** | 23% | 14% |
| 30 | 88% | 74% | **57%** | 33% | 22% |
| 50 | 97% | 88% | **74%** | 47% | 34% |

**The audit's premise checks out and is if anything understated.** It said six straight losses
"happens routinely" at roughly 6% — that is the per-position probability (measured 7.3% at
35.3%). Over a 20-trade stretch, **44% of stretches contain a run of six or worse.** A user who
sees six losses in a row has seen the median-ish outcome of taking twenty trades.

### OUTCOMES CLUSTER, AND THE COMFORTABLE ARITHMETIC IS THE ONE THAT CRIES WOLF

Losing runs are **longer** than independence predicts, because trades opened near each other in
time share a market. Scored against its own shuffled null (the X7/R3 method — this project does
not quote a design effect without one), 1,000 shuffles holding calendar structure fixed:

| statistic | observed | null median | null p95 | p(null ≥ obs) |
|---|---|---|---|---|
| monthly design effect | **2.667** | 0.984 | 1.244 | **< 0.001** |
| longest losing run | 27 | 17 | 23 | 0.007 |
| runs of ≥ 6 losses | 172 | 137 | 150 | < 0.001 |
| **runs of ≥ 10 losses** | **58** | **21** | 28 | **< 0.001** |

It clears its null decisively. The consequence drives the design: at 20 trades, **independence
puts the 95th percentile of the worst run at 10 and the measurement puts it at 12.** Using the
tidy Bernoulli formula would have labelled a run of 11 or 12 "worse than 19 stretches in 20"
when the record says it is ordinary. **`test_the_shipped_percentile_is_the_measured_one_and_it_is_the_looser_one`
fails the suite if that ever inverts.**

---

## 2. WHAT WAS BUILT, AND WHERE IT APPEARS

`valuation/web/payoff.py` — a pure module, no Flask import, the same policy-as-function pattern
as `saas/private.py`, `saas/surfaces.py` and `web/withhold.py`, so the rules are unit-testable
without a request. It holds the transcribed constants, `outcome_buckets()`, `streak_verdict()`,
`longest_loss_run()`, `expectation_line()` and `payoff_summary()`.

| surface | who sees it | what it now shows |
|---|---|---|
| `/api/whatdo` → the **Single tab panel** | **public**, incl. the options-withheld branch | the stacked distribution bar, the shape in one sentence, the streak expectation, and the refusal |
| **`/methodology`** | **public** | a full section: the five buckets worst-first, the median trade, the tail share, the streak table, the clustering vs its null, and that the alerts were tested and do not work |
| **Signals tab** (`payoffCard`) | owner | the same distribution, rendered **above** the alert table and above the scorecard |
| **Options scorecard** (`streak`) | owner | the realized longest losing run judged against the banked distribution, plus the run currently open |
| **Daily + weekly Discord recap** | owner | the streak line when there is a verdict, and the expectation in the footer of **every** post |

**Placement is the substance, not decoration.** The payoff card renders *before* the alerts and
the expectation sits in the footer of every recap, because an explanation of losing streaks that
appears only once someone is down reads as an excuse. The same sentence beforehand is an
expectation. That is P3's item 3 and it is the reason the card is not simply attached to the
scorecard.

**One thing the withheld branch does deliberately:** a visitor who is told an alert exists but
not what it is has the least context of anyone and is the most likely to read "options signal"
as "likely winner". The contract stays hidden; the payoff **shape** does not. A distribution
from a historical simulation is not a live pick and not a performance claim.

---

## 3. THE "IS THIS STREAK NORMAL" RULE, DERIVED

Read off the measured percentiles for the stretch the reader has actually taken:

| condition | verdict |
|---|---|
| fewer than 10 closed trades | **`too_few`** — no verdict at all |
| run ≤ median | `ordinary` |
| run ≤ p90 | `ordinary` (inside the usual range) |
| p90 < run ≤ p95 | **`unusual`** — longer than 9 stretches in 10 |
| p95 < run ≤ worst measured | **`rare`** — longer than 19 in 20, and it has happened |
| longer than anything measured | **`beyond_record`** |

Three deliberate properties:

* **It can say no.** `unusual`, `rare` and `beyond_record` are reachable on real inputs and are
  reached in the end-to-end check below. A design that can only ever say "this is fine" is the
  failure mode this task was most likely to produce, and
  `test_the_design_is_not_only_capable_of_reassurance` pins that both halves are reachable.
* **Under ten closed trades it refuses.** Three losses gets "too few to say", not a comforting
  number. The floor is the smallest stretch the table measures, not a round number.
* **The bracket never borrows a longer stretch than the reader has taken.** Judging 12 trades
  against the 30-trade column would import that column's longer runs and excuse a streak the
  record does not excuse. The cost is stated in the code: it is discontinuous and errs toward
  **alarm** (19 trades is judged against 10-trade stretches, so a run of 10 reads `rare` for
  them and `ordinary` one trade later). That is the direction to err in, and the sentence names
  the stretch it used so the reader can see it happening.

---

## 4. BEFORE / AFTER, AS RENDERED

**Before** — the entire treatment of a 35% hit rate, one sentence, identical on every surface:

```
Options here are CONVEX, not high-probability: the backtest hits 37% of the time — most
trades lose a little and a few win big. A hit rate on its own says nothing about whether
this works.
```

**After** — the same slot, `/api/whatdo` and the recap footer:

```
Options here are CONVEX, not high-probability: the backtest hits 35-37% of the time — most
trades lose a little and a few win big. A hit rate on its own says nothing about whether
this works. Expect losing streaks. Over 20 trades the typical worst run is 5 in a row, 44%
of stretches contain a run of 6 or worse, and the record's worst at this scale is 20.
```

**After** — the scorecard, run end-to-end against a real sqlite table (all four verdicts
reachable):

```
3 losses, brand new book
  too_few    3 closed trade(s) is too few to say whether a losing run is unusual. The record
             only measures stretches of 10 trades and up.

20 trades, worst run 5
  ordinary   5 losses in a row over 20 closed trades: the typical worst run over 20 trades
             is 5, measured against 20 trades. 60% of measured stretches contain a run this
             long.

20 trades, worst run 11
  unusual    11 losses in a row over 20 closed trades: longer than 9 stretches in 10; the
             95th percentile is 12, measured against 20 trades. 9% of measured stretches
             contain a run this long.

20 trades, worst run 14
  rare       14 losses in a row over 20 closed trades: longer than 19 stretches in 20 - it
             does happen, and the worst in the record at this scale is 20, measured against
             20 trades. 3% of measured stretches contain a run this long.
```

**After** — the public methodology page (rendered, tags stripped):

```
The options side wins about a third of the time, and that is the design

  1.4%  lost almost everything (worse than -90%)
 58.2%  hit the stop (-45% to -90%)
  5.0%  small loss (0 to -45%)
 10.3%  small win (up to +100%)
 25.0%  at least doubled (+100% or better)

The middle trade loses 52% of the premium. The trades that at least doubled are 87% of
everything the winners made... How long is an ordinary bad run? Expect losing streaks. Over
20 trades the typical worst run is 5 in a row, 44% of stretches contain a run of 6 or worse,
and the record's worst at this scale is 20... the clustering measures 2.667 against a
shuffled null whose 95th percentile is 1.244 (1,000 shuffles, p < 0.001). Assuming
independence would put the 95th-percentile worst run at 10 instead of the measured 12 — so
the tidy arithmetic is the one that would cry wolf.

None of that says the options alerts work — they were tested and they do not. Measured
against random entry on the same names and dates, the alert's choice of day subtracted
value: -6.65 percentage points per trade, paired sign test p < 0.00001.
```

---

## 5. WHAT I CHOSE **NOT** TO SHOW, AND WHY

* **No cumulative equity curve of the backtested options book, and no "$143,723 on one
  contract".** It is the most persuasive figure available and it is the one that would most
  read as a performance claim on a free educational site. The distribution answers the user's
  actual question ("is my run normal?"); a P&L curve answers "how much would I have made",
  which is a question this product does not answer for a strategy it has measured as dead.
* **No forward-looking streak prediction.** The table describes stretches that happened. It
  does not say "expect 5 more losses". A number that looks like a forecast on a payoff this
  noisy would be the same overreach the confidence badge was already corrected for once.
* **No per-name streak.** `unified.options_for` still reports a per-ticker record as a COUNT.
  Two of three winners on one name is not a rate and is not a streak either.
* **No position-sizing recommendation.** The audit's P3 text asks for O12's sizing to be made
  prominent, since sizing is the real defence against a 37% hit rate. **I did not do that half**
  — O12 is not in this lane's record and I could not find a banked sizing result to render, and
  inventing one to fill a section is exactly what this project's rules forbid. `options_sizing`
  already returns whole contracts against a fixed risk budget and the whatdo panel already
  states "0 contracts is a real answer". **Routed: if O12 has a banked recommendation, wiring
  it next to this payoff card is a small follow-up.**
* **The confidence badge was left alone.** It lives in `valuation/edge/options_confidence.py`,
  out of lane, and it was already corrected once to frame expectancy rather than win
  probability. Nothing here needed it changed.

---

## BUGS FOUND

**1. `/methodology` publishes research numbers this project's own record marks VOID.** Not
mine to have introduced, and found while adding the options section to the same page. Three,
all public:

| the page says | the record says |
|---|---|
| FF5+MOM alpha **+8.81%/yr, t 5.74**, 109 windows, 1998–2026 | **VOID.** `CLAUDE.md`: "THE OLD +8.81%/yr AND THE +6.6%–8.8% RANGE ARE VOID. Do not quote them anywhere." Corrected R1 re-run: **+6.99%/yr, NW t +3.984**, 68 windows, 2009-01 → 2025-10 |
| breakeven **236 bps** one-way vs a **37 bps** cost profile | B11: breakeven **134 bps** against a **measured 33.4 bps**; the old 37 bps "was an assumption quoted as a measurement" |
| the Deflated Sharpe "is an **undeflated** one… saturates at >99.9% because it is deflating nothing" | B9's mechanism was **refuted by measurement** and M1 superseded it: at the real N = 84 the statistic self-reports as a genuine Deflated Sharpe of **0.8997**, which **fails** the >0.95 bar while sitting above all 100 placebo draws |

The third is the one to be careful with — its honest current form is "fails the conventional bar
**and** clears the noise floor", and half of that sentence on a public page is worse than the
stale version. **Deliberately not bundled into the P3 commit**; it is a rewrite of equity
research claims and it wants the edge lane's sign-off on wording, not a display fix smuggled in
beside an options feature. Flagged here as the highest-priority item this lane found.

**2. The corrected options book's per-trade rows were never banked.** `r2_state.pkl` was a temp
file; only aggregates survive in `UNIVERSE_RESULTS.json`. That is why this session's streak
table had to be measured on the control instead of the book. The Session-5 closeout added a
`BANK_MANIFEST.json` guard so the runner can no longer overwrite a banked book — but the guard
protects `data/options_universe/`, and this run wrote its state to a temp path outside it.
**A guard on the destination does not help when the run points somewhere else.** Anything that
wants the real alert sequence (U7's join, any future streak work) has to re-run the book.

**3. `test_the_constants_are_transcribed_from_the_banked_book_not_invented` silently asserted
nothing in a worktree, and I nearly shipped it that way.** `data/` is not present three levels
down, so the file check no-opped and the test still printed PASS. Fixed two ways: the search
path now also looks at the real checkout (`../../../data/…`, which is where an agent worktree's
data actually lives), and the constants are additionally frozen in the test file so the suite
asserts something everywhere. Same class as the `rule_fired` defect in B8 — a test that never
reaches its assertion is worse than no test.

---

## THIS ITEM IS DONE. WHAT REMAINS, AND WHOSE IT IS

* **P3's sizing half → whoever owns O12.** See section 5; not estimated, not faked.
* **The methodology page's void equity numbers → edge lane**, per BUG 1.
* Still open from Session 15, unchanged and re-confirmed: **the refusal erased by the scan**
  (`_enrich_with_dcf` writes `fair_value = None`, `estimate_fair_values` substitutes a peer
  estimate, so KSPI/STLA/CHTR carry fair values on the public hot list) → **engine lane**; the
  disclosure sentence at `app.js:958` is a stopgap and should come down in the same commit that
  fixes the scan. And **CI publishing +275% at HIGH confidence** with a comps lens implying 8.0x
  price → **engine/DCF lane**; a valuation problem, not a guard problem.

---

# Session 15 — 2026-08-06 — The untimed result cache behind the exports
(PROMPT_web_stale_cache.md)

One item, and it was small — stated as small rather than padded. **This lane is now clear;
what it is waiting on is at the bottom.**

## WHAT `_LAST` ACTUALLY DID WRONG (measured, not inferred)

`web/app.py:42` held `_LAST: dict`, a process-global result cache keyed by ticker, and
`/api/export/excel` + `/api/export/pdf` served from it through `_get_or_compute`. Nothing
else read it. Four defects, in order of how much they matter:

**1. The key was the COMPANY, not the QUESTION — and this is the one that bites without
anything having to go stale.** The cache ignored the assumptions a result was computed
under, so a visitor who re-ran a name in the assumptions panel left *their* valuation under
the bare ticker, and the next visitor's plain export was served it. Measured on the NKE
fixture, offline:

| | fair value | what the next visitor's workbook contained |
|---|---|---|
| default assumptions | **$40.15** | — |
| one visitor overrides `wacc=0.25` | **$22.97** | **$22.97 — a 42.8% error, in someone else's assumptions** |

No staleness required, no market movement required. It fires the moment two people look at
the same name and one of them touches the panel.

**2. Nothing was stamped, and nothing expired.** No `pop`, no `clear`, no `del`, no TTL, no
bound anywhere in the file — verified by scanning it. An entry lived until the worker
process restarted, which on Render means until the next deploy: **days**. Worse, the
document could not disclose this even in principle, because the only date on it is
`As of <cd.as_of>` — the **fundamentals** date, which on a live name reads as *today*
whether the numbers were made a minute ago or last Tuesday. **A stale document was
indistinguishable from a fresh one, and it asserted freshness.** The project already had
the right pattern in `data/macro.py:16` — a `ts` and a 600s TTL. The export cache had
neither.

**3. Two worker processes, so two independent caches — yes, it makes it worse.** Production
is `runtime: docker`, and the Dockerfile CMD is `--workers ${WEB_CONCURRENCY:-2} --threads 4`,
so **two** processes. (The `Procfile`'s `-w 4` is not what Render runs — worth knowing before
anyone reasons from it.) Confirmed directly: a second Python process importing
`valuation.web.app` sees `_LAST = {}` while the first holds an entry. So a visitor's page and
their download could be answered by different processes with different answers, and the four
threads per worker shared one dict with no lock around the read-modify-write.

**4. Unbounded.** Every ticker ever valued stayed resident for the life of the process.
Measured: ~**8,991 bytes** pickled per `ValuationResult`, so ~9 MB per worker per 1,000
distinct names, never freed, on a 512 MB box running two of them. Real, monotonic, and the
smallest of the four — said plainly rather than inflated.

### What production actually showed, including where it did NOT reproduce

Read-only probes against valquo.co (no POSTs, no overrides — GETs a visitor makes):

* **The cache is live and observable:** the first `/api/export/excel?ticker=KO` took **3.0s**,
  the next identical one **0.2s**.
* **Every workbook downloaded was stamped `As of 2026-08-06`** — today — with no indication
  anywhere of when its numbers were computed. That part reproduced exactly.
* **The document and the page agreed on all five names tested** (AAPL, MSFT, KO, JPM, XOM —
  export price vs `/api/value` price, 0.00% gap on each). The upstream quote did not move
  during the observation window, so **the defect was latent at that moment, not firing.**
  Recorded that way on purpose: I did not observe a live document-vs-page price disagreement
  and am not going to claim one. Defect 1 above needs no price movement and was measured
  directly instead.
* One thing seen and deliberately *not* filed as this bug: `/api/whatdo` reported AAPL at
  $303.42 while both the live page and the workbook said $311.00. That is the **daily scan
  snapshot** being older than a live quote — a different, already-labelled surface
  (`screener/freshness.py`), not the export cache.

## THE FIX

New `valuation/web/resultcache.py` — a plain object, no Flask import, so the policy is
testable without a request. `web/app.py` now holds `_RESULTS = resultcache.ResultCache()`.
Same idea as before (serve the page's own result rather than recomputing against a different
quote), with the three missing properties:

| | before | after |
|---|---|---|
| cache key | ticker | ticker + overrides + peer set (`request_key`) |
| visitor B's plain export, after A overrode | **A's $22.97 model** | **miss → B's own $40.15** |
| expiry | none — until the worker restarts | **TTL 900s**; served at +899s, recomputed at +901s |
| bound | none | **256 entries, LRU**; 1,000 names valued → 256 resident |
| on a miss (other worker / expired) | served whatever was there | **recomputes under the same assumptions** |
| compute time on the document | nowhere | `Computed 2026-08-06 11:52 UTC` on both formats |
| compute time on the page | nowhere | same stamp, from `/api/value`'s `computed_at` |
| thread safety | none (4 threads/worker) | `threading.Lock` around the LRU touch and eviction |

**The assumptions now travel with the download.** `app.js::exportUrl()` puts the overrides
the page was rendered with into the export query string, and the route rebuilds the same key.
Without that the export could only ever ask *"the last NKE anyone computed on this worker"*,
which is a different question from *"the NKE on my screen"* — the fix would have been
cosmetic. This is what makes a miss safe: the worst case is now a fresh computation, not
another visitor's answer.

**Why still per-process.** A shared cache means Redis or the database. For a document that
costs one vendor call to rebuild, that is a much larger change than the problem justifies —
and once a miss recomputes correctly, two caches are no longer a correctness issue. Stated
in the module docstring so nobody has to re-derive it.

**`build_workbook`/`build_pdf` take `computed_at=None`** and omit the line entirely when it
is absent — the CLI renders both formats with no request behind it, and stamping "computed
now" on numbers loaded from anywhere would be a false claim. Both callers in `cli.py` are
unchanged and still work.

## THE SECOND DISAGREEMENT, FOUND WHILE FIXING THE FIRST — AND FIXED

The same defect in another costume, and **my own change is what made it reliable**, so it
belongs in this commit rather than in a bug report.

`overrides["wacc"]` replaces the discount rate at `pipeline.py:217` **without touching the
`WACCResult`**, which keeps the CAPM build-up. Every discount cell in the exported model
points at `WACC!B23`, and B23 always held the build-up *formula* — so a visitor who set
WACC to 25% on the page saw **$22.97**, downloaded the workbook, and got a model that
repriced itself at the **9.13%** build-up. Measured on the NKE fixture:

| | page | workbook, before | workbook, after |
|---|---|---|---|
| discount rate | 25% (user's) | **9.13% (CAPM build-up)** | **25%**, labelled *WACC (overridden on the page)* |
| tearsheet "WACC" row | — | **9.13%** | **25.0% (overridden)** |

Before this session an overridden export was a coin flip on worker routing; now the
override always reaches the export, so this would have gone from intermittent to
**every time**. B23 becomes the literal rate that produced the page's number, with the
build-up left above it as reference and a note saying how to restore the formula. **With no
override it stays a live formula** — the point of shipping a model rather than a picture is
that beta can be edited, and that is pinned by its own test.

## THE TEST

**`tests/test_resultcache.py` — 22 tests, new suite.** The durable ones:

* `test_two_different_questions_never_share_one_answer` — the actual bug, at the cache level.
* `test_the_export_serves_the_assumptions_the_page_used_not_someone_elses` — the same thing
  end to end through the real Flask routes, checked on the workbook bytes the visitor gets.
* `test_a_miss_recomputes_under_the_requested_assumptions_rather_than_falling_back` — pins
  the multi-worker case, which is the one with no local reproduction.
* `test_the_export_stamps_the_document_with_the_cached_computation_time` — the route must
  pass the *entry's* stamp, not the wall clock, or a 14-minute-old document claims to be new.
* `test_the_bare_dict_cache_is_gone_for_good` — a plain dict was the failure mode, so
  reintroducing one fails a test rather than a review.
* `test_the_workbook_discounts_at_the_rate_the_page_actually_used` and
  `test_an_untouched_valuation_still_exports_a_live_wacc_formula` — the WACC pair above,
  including the half that protects everyone who did *not* override anything.

`tests/test_withhold.py` updated where it poked `_LAST` directly; its catch-all now strips
the compute stamp by exact shape (`\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC`) rather than by
loosening the number rule, so nothing shaped like a dollar figure can hide behind it.

**Suites 20 → 21, tests 709 → 731.** (The prompt's bar said 705; `main` had already moved to
709 before this session — baseline re-measured, not assumed.)

## BUGS FOUND

1. **`Procfile` and the `Dockerfile` disagree about worker count** — `-w 4` vs
   `--workers ${WEB_CONCURRENCY:-2}`. Render uses the Dockerfile, so the Procfile's number is
   inert, but anyone reasoning about concurrency from it gets the wrong answer. Not changed:
   the Dockerfile comment explains why 2, and 4 workers OOM'd on the 512 MB box. Left as a
   note rather than a silent edit.
2. **The exported model ignored a WACC override** — full write-up above. **Fixed here**
   (`report/**` is this lane's), in both formats, with tests. The underlying asymmetry —
   `overrides["wacc"]` sets the discount rate but leaves `WACCResult.wacc` at the CAPM
   build-up (`pipeline.py:217`) — is **left alone deliberately**: it is `engine/**`, it is
   arguably intended (the build-up is what the WACC sheet is *for*), and the reports now
   read `scenarios.base.wacc`, which is the rate that actually discounted the cash flows.
   Worth knowing before anyone reads `result.wacc.wacc` as "the rate this valuation used" —
   **it is not, whenever an override is in force.**
3. **`n_years` looked unbounded and is not** — recorded so the next person does not re-run
   the check. `assumptions.py:182` reads the override with no clamp, and the export now
   takes overrides on a public GET, so this was worth measuring rather than assuming:
   `n_years` of 200, 3,000 and 100,000 all resolve to **15**, and the workbook stays ~10 KB.
   No DoS, no clamp added.

## THIS LANE IS CLEAR. WAITING ON:

1. **The refusal erased by the pipeline — engine lane, owns `screener/**`.** Still open.
   `_enrich_with_dcf` writes `fair_value = None` on a refusal and records nothing else;
   `estimate_fair_values` reads that as "not computed yet" and substitutes a peer estimate.
   **KSPI, STLA and CHTR still sit on the public hot list with fair values while the
   valuation page refuses them outright.** The guard shipped in Session 14 already honours
   `fair_value_withheld` the moment the scan starts setting it, so **nothing further is needed
   on this side.**
   **The disclosure sentence on the hot list is a STOPGAP, not the fix.** It currently tells
   the reader the two surfaces disagree and to believe the refusal. **It should come down when
   the scan starts marking refusals** — otherwise the page will be explaining an inconsistency
   that no longer exists, which is its own kind of wrong. **Who checks: whoever lands the
   `_enrich_with_dcf` change**, in the same commit; if that lands elsewhere, this lane removes
   it on the next pass. The string is in `app.js`, in the hot-list note ("Known inconsistency,
   stated rather than hidden"), and it names Kaspi.
2. **CI publishes +275% at HIGH confidence** with a comps lens implying 8.0× price, tripping
   nothing. → **engine / DCF lane.** Not a guard problem — a valuation problem. Still open.

## THE WITHHELD SET IS THREE, NOT FIVE — AND IT MOVES

Recorded here because it is already stale in earlier notes: **GILD, CI and JD left the
withheld set after the DCF terminal work.** Today it is **KSPI, STLA, CHTR**. Anything quoting
"the five withheld names" is out of date. **The set is an output of the engine, so it changes
whenever the engine does** — do not hard-code it, and re-derive it (`withhold.is_withheld`
over the names in question) rather than trusting any list in a handoff, including this one.

---

# Session 14 — 2026-08-06 — The public leak is closed at this lane's call site; the score is
now shown as partial (PROMPT_appfixer_close_the_public_leak.md)

Both items shipped. **The real-snapshot measurement the last session could not get is in this
one** — and it turned up a second, larger leak that this lane cannot close, recorded with its
mechanism.

## ITEM 1 — the guard, and what it actually catches

**Where it sits:** `valuation/web/withhold.py::withhold_implausible_fair_values()`, called at
`web/app.py:411` immediately after `estimate_fair_values` on the rows `/api/hotstocks` is
about to serve, and at `web/unified.py:227` for `/api/whatdo` — the second public surface fed
by the same estimator, which would otherwise just move the leak one endpoint over.
`/api/rank` was already safe (it reads `base_fair_value`) but now carries the partial-score
flag, below.

**One number, one meaning.** The band is *imported* from `engine.pipeline.FV_BAND_HIGH`, not
restated — the two surfaces cannot drift into different definitions of "implausible", which
is exactly how this opened. Pinned by
`test_the_row_guard_uses_the_valuation_pages_own_band_not_its_own_number`.

**It says why.** The row gets `fair_value = None`, `upside = None`, `fair_value_withheld =
True` and a sentence: *"No fair value is published for this name: the estimate came out 5.3x
the price, past the 5x band at which this tool treats a valuation as a data problem (currency
or share count) rather than an opportunity. The ranking below does not depend on it."* The
cell renders **withheld**, not an em dash — a blank invites someone to fill it back in.

### THE REAL MEASUREMENT (production, 2026-08-06)

`/api/hotstocks` is public, so the live snapshot is readable without credentials — one GET, no
Render disk needed. Scan 2026-08-06, 800-name universe, 785 scored, 500 served:

| | before the guard | after |
|---|---|---|
| rows carrying a fair value | 499 | 498 |
| **max fair_value / price** | **5.25× — AEG** | **3.96× — CNC** |
| rows above the 5× band | **1** | 0 |
| rows above 20× | 0 | 0 |

The one name: **AEG (Aegon) — fair value $49.91 against a $9.50 price, tagged
`blended / medium`.** A leveraged insurer, which is the exact mechanism (`3 + 2 × net debt /
market cap`). Its **hot score 97.86 and rank 18 are untouched** — only the fair value is
withheld, because the ranking never used it.

So: thin today, unbounded by construction, and now closed on this side.

## ITEM 1b — THE BIGGER LEAK, WHICH THIS GUARD DOES NOT CATCH

Found while measuring, and it matters more than the band:

> **The three names the valuation page refuses outright are served on the public hot list
> with fair values, because their peer estimate lands *under* 5×.**
>
> | name | valuation page | public hot list, today |
> |---|---|---|
> | KSPI | **refuses** — "the model's $1,039.92 is 11.3× the $92.19 price" | **$299.16** (3.24×) |
> | STLA | **refuses** — 6.4× | **$21.09** (3.75×) |
> | CHTR | **refuses** — 8.1× | **$416.75** (2.72×) |

**Mechanism, exactly:** `screen.py::_enrich_with_dcf` runs the full valuation for the top
names and writes `r["fair_value"] = res.base_fair_value` — which is `None` when the
publication guard refuses. It records nothing else. `estimate_fair_values` then reads that
`None` as *"no DCF yet"* and substitutes a peer-relative estimate. **The refusal is erased by
the next step in the pipeline.**

**Not fixed here — `screener/**` is another lane's, and the fix is one line in theirs**
(record the refusal alongside the `None`). Two things were done instead:

1. **The guard already honours it.** `withhold_implausible_fair_values` withholds any row
   carrying `fair_value_withheld`, whatever its ratio — so the moment the scan starts marking
   refused names, this surface refuses them with no further change. Pinned by
   `test_a_row_already_marked_withheld_is_honoured_even_below_the_band`.
2. **The disagreement is stated on the hot list rather than hidden**, since it is live today:
   *"Known inconsistency, stated rather than hidden: these two surfaces can still disagree. A
   name whose full model is refused outright — Kaspi, for one, where the statements and the
   price are in different currencies — can carry a peer-relative estimate here, because a
   ratio of two same-currency figures survives the mismatch that breaks the valuation. When
   they disagree, the Single-valuation page's refusal is the one to believe."*

That last point is not spin: a peer multiple genuinely is currency-neutral, so the estimate
is not obviously wrong the way the DCF was. But the product must not answer the same question
two ways without saying so.

## ITEM 1c — the catch-all, extended (the durable part)

`test_no_public_api_response_carries_a_fair_value_past_the_band` walks **every `fair_value`
that sits next to a `price` anywhere in a public API response body**, recursively, across
`/api/hotstocks` and three `/api/whatdo` shapes, with a stubbed store containing both the real
AEG row and the constructed 33× one. A new public list surface fails this the day it starts
serving a fair value, without anyone remembering to add it anywhere. Session 12's catch-all
walked `/api/value`; this is the walk that would have caught the leak Session 13 only found by
reading arithmetic.

## ITEM 2 — the score is rendered as partial, and visibly so

The engine change (greeks lane) is in and measured on this machine: the whole valuation
sub-score is dropped and the >5× cap now falls back to `blend.withheld_value`. This lane's
"Not rated." was correct while the number was contaminated and became an understatement the
moment it was not, so the page now publishes the partial score — marked everywhere it appears.

**Rendered text, signed out, live data, all three names withheld today:**

| | KSPI | STLA | CHTR |
|---|---|---|---|
| dial | **PARTIAL / 50 / "/ 100 · 4 of 5 components"** | **PARTIAL / 18** | **PARTIAL / 47** |
| call | "Hold — partial" | "Avoid — partial" | "Hold — partial" |
| confidence | low | low | low |
| valuation bar | **withheld**, "weight 20% — dropped, not reassigned" | **withheld**, weight 40% | **withheld**, weight 40% |
| the other four | 91 / 86 / 100 / 78 | 8 / 29 / 28 / 13 | 71 / 29 / 46 / 24 |

STLA at 18 and CHTR at 47 are worth noting: **the >5× cap is a ceiling, not a floor** — a
partial score lands wherever the four surviving components put it.

The distinction is on the dial, not in a tooltip: a dashed amber inner ring, the word
**PARTIAL** above the number, "4 of 5 components" below it, "— partial" beside the call, the
missing bar reading **withheld** (not "n/a" — different words, and only one is true) with a
hatched track and "dropped, not reassigned", and the engine's own sentence printed in the
panel. The Watchlist marks it in the cell too, because a partial 50 sitting in a column beside
a full 50 asserts they mean the same thing.

**The caution the greeks lane routed here is carried in the copy**, not implied:
`SCORE_NOTE` ends *"It is not comparable to a full score at the same number."* Pinned by
`test_the_score_note_says_partial_and_says_it_is_not_comparable`.

**A regression this file caused in design and caught in test.** The driver filter matched on
keywords, and the two drivers a withheld name now legitimately carries are *"Valuation
withheld — no fair-value, **Monte Carlo** or comps term contributes…"* and *"⚠ **Model fair
value** is 11.3× the price… Capped and flagged unreliable"*. A keyword match deletes both —
the explanation the page is required to show, and the flag saying the number was capped. The
filter now matches on the sentence-initial prefixes `_valuation_score` actually writes, and
`test_the_engines_own_explanation_survives_this_filter` exists to keep it that way.

## Suites

**20 suites, 705 tests, all green** (main was at 696 when this session started). This adds
**+9 in `test_withhold.py`** (19 → 28).

## BUGS FOUND

1. **THE REFUSAL IS ERASED BY THE PIPELINE** — item 1b above. `_enrich_with_dcf` writes
   `fair_value = None` on a refusal and `estimate_fair_values` reads it as "not computed yet".
   KSPI, STLA and CHTR are on the public hot list with fair values today. → **screener lane;
   this surface already honours the flag the moment it is set.**
2. **CI publishes +275% at "high" confidence, and its comps lens implies 8.0× the price.**
   After the DCF-terminal fixes CI is no longer refused ($1,013.47 against $270.50 = 3.75×,
   under the band), so the whole page publishes: score **74 "Buy", confidence HIGH**, comps
   fair value **$2,153.27 (+696%)**, sensitivity cells to $3,851.90. Nothing here is withheld
   because nothing tripped the guard — the guard is not the problem, the valuation is.
   → **engine / DCF lane.**
3. **The withheld set is now three, not the five in the prompt.** GILD ($159.00, +21%), CI and
   JD ($108.74, 3.34×) are no longer refused after the DCF-terminal work. Any future note
   quoting "the five withheld names" is stale; the set moves whenever the engine changes.
4. Still open from Session 13: **`_LAST` is an untimed process-global result cache**
   (`web/app.py:40`) and `/api/export/*` serves from it, so a document's "As of" can disagree
   with the page's. → **app lane.**

## For Don

The hot list can no longer publish a fair value more than 5× the price — the same bar the
valuation page uses. On today's live scan that changes exactly one name: **AEG**, which was
showing $49.91 against a $9.50 price and now shows **withheld** with the reason on hover. Its
rank is unchanged, because the ranking never used that number.

The score on a refused name now reads **"PARTIAL — 50 / 100, 4 of 5 components"** instead of
"Not rated": the engine stopped feeding the withheld valuation into it, so the number that is
left is honest as far as it goes, and the page says exactly how far that is.

**One thing you should know is still true:** open KSPI on the Hot stocks tab and it shows a
fair value of about $299, while the Single-valuation page refuses to value it at all. That is
a real inconsistency, it is written on the hot list in plain words, and the fix belongs to the
scan — not to this surface. Believe the refusal.

---

# Session 13 — 2026-08-05 — Exports refuse in-document; the 5x/20x answer; the Index tab
(PROMPT_appfixer_exports_and_index_tab.md)

Three items. Item 1 shipped, item 2 is answered definitively and the answer is **worse than
the prompt supposed**, item 3 turned out to be already built — so what shipped there is the
decision, the labelling and the sanity check rather than the feature.

## ITEM 1 — the exports render the refusal now, and produce a real file

`/api/export/pdf` and `/api/export/excel` used to return **409** for a withheld name. They now
return **200 and a document that says the valuation is withheld, with the reason on it**. The
route-level refusal is gone entirely (`web/app.py`); the refusal lives in the documents.

**PDF** — `report/pdf.py::withheld_pdf_lines()` / `_build_withheld_pdf()`. Sample, generated
from the real KSPI result and read back out of the rendered file with `pypdf`:

> **Joint Stock Company Kaspi.kz (KSPI)** — Valuation withheld | As of 2026-08-05
> **No fair value is published for this name**
> Cannot value this name: the model's $1,289.93 is 14.0x the $92.19 price. That gap is a data
> problem (currency or share count), not an opportunity, so no fair value is published.
> This is not a formatting problem or a missing-data error. The model produced a figure,
> checked it against the market price, and refused to publish it. Everything downstream of
> that figure — the bear/base/bull cases, the sensitivity grid, the Monte Carlo distribution,
> the implied values from peer multiples and the opportunity score — is withheld with it…
> **What is shown** — Price $92.19 · Fair value *not published* · Upside *n/a* · Opportunity
> score *not rated* · Regime hypergrowth · DCF reliability medium
> **What would change it** — Most refusals are a currency or share-count mismatch… when the
> inputs reconcile, the valuation publishes on its own.

Numbers in the rendered PDF larger than 5× the price: **one — $1,289.93, inside the refusal
sentence.** No `Scenarios`, `Score Breakdown`, `Reverse DCF` or `vs Price` section exists.

**Excel** — the harder case, and it is not the model with holes in it. A blanked summary cell
would be pointless because **every cell in the normal workbook is a formula**: `C6` is
`=C41`, the sensitivity grid is 25 live `SUMPRODUCT` per-share formulas, so a "cleared"
workbook would recompute the withheld figure the moment it opened. So the model sheets are
**not built at all**. Measured on the generated file:

| | normal (AAPL) | withheld (KSPI) |
|---|---|---|
| sheets | DCF Model, Sensitivity, WACC | **Not valued** (one) |
| non-empty cells | 201 | 19 |
| **live formulas** | 88 | **0** |
| cells > 5× price | share counts / revenue / market cap (legitimate model inputs) | **none** |

The one place the withheld figure appears is inside the reason text in `A5`, as on the page.

**Tests** — `tests/test_withhold.py` is 16 → **19**, and the export tests are built on a REAL
withheld result: `value_from_company(NKE fixture with price=$2.00)` runs the actual
`publication_guard`, which fires at 37.5×. Offline, no network. `test_the_workbook_has_no_model_in_it`
walks **every cell** (not the summary) asserting no formulas and nothing above 5× price;
`test_the_pdf_renders_the_refusal_instead_of_erroring` reads the file back with `pypdf` and
walks every number in the extracted text; `test_the_export_routes_serve_the_refusal_document`
re-opens **the bytes the browser receives** and walks those. `test_a_publishable_name_still_
exports_the_whole_model` keeps the normal workbook at 3 sheets and >50 formulas.

`pypdf>=5.0` was added to `requirements.txt` (test-only, commented as such): CI installs that
file and nothing else, and checking the code that builds a document is not the same as
checking the document.

## ITEM 2 — the 5x/20x question. **YES, and the 20x is not the real ceiling.**

**A name can reach a public surface valued far above 5× its price, and it does not need an
exotic input.** Path, all of it live today:

1. `/api/hotstocks` is PUBLIC (`saas/surfaces.py::PUBLIC_API`).
2. `web/app.py:407-408` calls `estimate_fair_values(rows, peer_rows=all_rows)` on the rows it
   is about to serve.
3. `screener/fairvalue.py:154-165` — `_mature_value`'s EV bridge: `equity = ev*ratio - nd`
   with `ratio` capped at `MAX_RERATE = 3.0`, then `implied = price * equity / mc`.
4. `app.js::_fairValCell` renders it with the `(+N%)` chip. No cap anywhere downstream.

Since `ev = mc + nd`, that reduces exactly to

> **implied / price = 3 + 2 × (net debt / market cap)**

which I confirmed numerically through the real function — predicted and actual agree to the
cent at every leverage level:

| net debt / market cap | 0 | 0.5 | **1.0** | 1.5 | 2 | 3 | 4 | 8 | 15 |
|---|---|---|---|---|---|---|---|---|---|
| published fair value ÷ price | 3.0× | 4.0× | **5.0×** | 6.0× | 7.0× | 9.0× | 11.0× | 19.0× | **33.0×** |

So **any name with net debt above 1× its market cap that re-rates the full 3× exceeds the
valuation page's refusal band**, and the 5x–20x band is not even the limit — the constructed
case published **$330.00 against a $10.00 price (33×)** tagged `fair_value_method: "multiples"`,
`fair_value_confidence: "medium"`. Leveraged cable, telecom, utilities, REITs and airlines sit
in that range routinely; CHTR's own net debt is roughly 4× its market cap.

**The 20× cap does not apply to this.** `MAX_GROWTH_VALUE = 20.0` (`fairvalue.py:69`) is
checked at `fairvalue.py:222`, inside `_growth_value` only. **The multiples lens has no
absolute cap at all** — only a cap on the *re-rate*, which stops bounding the *per-share*
answer as soon as the net-debt bridge divides by a small market cap.

**Not changed, as instructed** — this is `screener/**`. Two things make it actionable rather
than theoretical: the call site (`web/app.py:407`) is in MY lane, so the guard can be added
without touching the screener the moment its owner picks the number; and the disagreement is
not 5 vs 20, it is 5 vs unbounded. I could not measure how often it fires in production: this
machine's `data/screener.db` holds only a synthetic test row (`TESTX`, scan_date 2099-01-01),
so the real snapshot lives on Render's disk. **The one-line check for whoever owns it:** on a
real snapshot, `max(r["fair_value"]/r["price"])` after `estimate_fair_values`.

## ITEM 3 — the Index tab was already built (2026-08-02, commit `5e48a4a`)

Verified rather than claimed: `tab-index`, the cumulative-vs-SPY chart (`indexChart`) and the
alpha figures already exist, and the live column is genuinely dynamic — `/api/index-track` →
`screener/index_track.py::summarize()` computes cumulative, excess, annualised alpha and
Sharpe from the stored series, withholding the annualised figures until `MIN_LIVE_DAYS`. The
backtested column reads `settings.BOOK_CONFIGS[cfg]["measured"]`, which is a *measured*
constant from the full-panel backtest and correctly labelled hypothetical. Nothing there was
a written-in performance figure, so there was nothing to replace.

What was genuinely open — and is what shipped:

**The split decision: the Index STAYS OWNER-ONLY.** Two independent reasons, either
sufficient: (1) it publishes names **with weights** as of today, which is an allocation rather
than an analysis — the exact line the split is drawn on; (2) the card above the holdings is a
cumulative-return chart against the S&P, which is a performance-claim *shape* whatever caption
sits under it, and the public posture is "no performance claims in public". The middle option
— publish the curve, withhold the holdings — was considered and **rejected**: it fails (2) on
its own, so it gives up the clarity of one rule and buys nothing. Reversal is one line in
`saas/surfaces.py` and is Don's call. Pinned by
`test_the_index_stays_owner_only_and_says_why_on_its_own_face`.

**The labelling, which was the real gap.** The copy read *"The book you would actually hold"*
and *"real money-less trading"* — an allocation instruction and a contradiction. Now, on the
surface itself and not only in the terms:

- tab header: **"A model portfolio — not a traded account, and not advice… No money is
  invested in it. Positions are marked at closing prices, so there are no fills, no slippage
  beyond the modelled cost and no tax — which is exactly why it is not a return anyone earned."**
- card title: "Performance — backtested vs live" → **"Model-portfolio performance — backtested
  vs forward"**; the live card's badge "Live since inception" → **"Forward, model portfolio"**.
- the **chart's own caption** now carries it, because a chart is the element most likely to be
  screenshotted away from every caveat around it: *"Cumulative return of the MODEL portfolio
  since inception vs SPY… no capital is invested — these are closing-price marks, not fills,
  and not a return anyone received."*
- the shared `RISK_DISCLAIMER` said the forward track "is real but short" — now **"is a model
  portfolio and a sandbox paper account — no money is invested in either, so no figure here is
  a return anyone received — and it is short."** That string is used on every surface that
  outputs something recommendation-shaped, so this is the widest-reaching line of the three.

Verified in a browser as the owner: the tab renders, all four framings appear, **no JS errors**.

**The book's sanity: shape confirmed, live names NOT confirmed — and I will not pretend
otherwise.** The construction was exercised read-only on a synthetic 800-name snapshot through
the real `build_index`: `roth` → 25 positions, weights sum to 1.000000, max 6.18% (under the 8%
cap), 11 sectors; `taxable` → 80 positions (the decile), max 2.25%, 11 sectors. That is the
shape the prompt describes and it is sane. **The live 67-position book with NLY / ARWR / APGE /
QXO / SYF cannot be checked from here** — the local store has no real scan, and
`/api/valquo-index` is owner-only in production. → **Don or Cowork: open the Index tab signed
in and eyeball the first post-800 book.** If a name looks wrong, the ranking is the place to
look, not the construction.

## Suites

**20 suites, 690 tests, all green.** `main` was at 686 when this session started (the prompt's
683 bar predates the DCF lane's +3 in `test_engine`). This session adds **+3 withhold**
(16→19) and **+1 public** (16→17). edge 221, screener 67, paper_track 40, engine 36, ev_multiples
34, private 30, saas 30, lazy_prices 28, lazy_prices_ic 24, options_greeks 22, security 22,
calibration 23, **withhold 19**, intraday 18, **public 17**, bulk 14, factor_alpha 14, freeze 13,
pead 12, sector_neutral 6.

## BUGS FOUND (noticed, not fixed — not this lane)

1. **The screener's multiples lens is unbounded on the public hot list.** Item 2 above:
   `implied/price = 3 + 2·(net debt / market cap)`, no absolute cap, `fairvalue.py:154-165`.
   The 20× `MAX_GROWTH_VALUE` guards only the growth lens. → **screener owner.** The public
   call site is `web/app.py:407` if the guard is better placed there.
2. **Two thresholds for one claim, still.** The valuation page refuses above 5×; the screener
   estimate has no ceiling. Whatever number is agreed, it should be one constant read by both.
3. **`_LAST` is a process-global result cache** (`web/app.py:40`) keyed by ticker with no TTL,
   and `/api/export/*` serves from it. On a long-lived Render process an export can therefore
   be built from a result computed hours earlier under different prices while the page shows a
   fresh one. Not a withholding leak (the guard travels with the cached result), but the
   document's "As of" and the page's can disagree. → **app lane, next session.**
4. Still open from Session 12 and unchanged: **MRK publishes +611% at 3.7×** (under the guard
   band — the DCF is the problem, not the band), and **`_valuation_score` re-imports the
   withheld valuation** at `scoring.py:83/86` with the >5× cap dead at `scoring.py:228`.
   → **engine lane.**

## For Don

Ask for a PDF or an Excel model of KSPI (or STLA, CHTR, GILD, CI, JD) and you now get a real
file that says the valuation is withheld and why, instead of an error — and the workbook has
no live formulas in it, so there is nothing for Excel to recalculate into the number the site
refused to show. The Index tab is unchanged in what it does and now says plainly, on itself,
that it is a model portfolio with no money in it. It stays behind your login; the reasoning
for that is above if you want to overrule it. **One thing needs your eyes:** the first
800-name book — open the Index tab signed in and check the holdings look sane.

---

# Session 12 — 2026-08-05 — When the model refuses to value a name, the whole page refuses
(PROMPT_scenario_cards_follow_headline.md)

The headline withheld KSPI's fair value and the card three inches below printed it anyway, at
+1299%. That was not one broken card. **Seven** surfaces republished the withheld valuation,
and the worst of them was the 93/100 "Strong Buy" gauge. All seven now refuse, the figures are
stripped from the API response rather than merely not drawn, and the refusal states its reason
where a number used to be.

## What rendered before, and what renders now — all seven withheld names

Measured through the real page (headless Chromium, signed out, live FMP data, 2026-08-05).
"Implausible tokens" = every `$…` string in the rendered DOM larger than 5× the price, which
is the guard's own threshold for refusing.

| Name | Price | BEFORE — scenario cards | Other leaks | Score shown | AFTER — implausible tokens on page |
|---|---|---|---|---|---|
| KSPI | $92.19 | $620.27 / **$1,289.60** / $2,888.15 (+573% / **+1299%** / +3033%) | MC median $2,335.73, p10–p90 $872.89–$6,340.11, "100% of trials above the price"; sensitivity to $8,632.67; comps implied $326.32 (+254%); reverse "expectations look cheap" | **93 Strong Buy** | **$1,288.94 only — inside the refusal sentence** |
| STLA | $5.63 | $8.03 / **$125.87** / $406.72 (+43% / **+2136%** / +7124%) | comps implied $73.12 (+1199%) | 45 Reduce | **$125.88 only — the refusal sentence** |
| CHTR | $153.17 | $1,202.45 / **$1,717.36** / $2,402.64 (+685% / **+1021%** / +1469%) | MC median $2,136.63; sensitivity to $7,876.76; comps $1,007.67 (+558%) | 69 Buy | **$1,717.36 only — the refusal sentence** |
| GILD | $131.76 | $453.96 / **$961.79** / $2,045.10 (+245% / **+630%** / +1452%) | MC median $2,063.46; sensitivity to $11,409.90 | **87 Strong Buy** | **$961.79 only — the refusal sentence** |
| CI | $270.50 | $1,008.07 / **$2,001.65** / $3,548.87 (+273% / **+640%** / +1212%) | MC median $1,786.34; comps $2,153.27 (+696%) | 71 Buy | **$2,001.65 only — the refusal sentence** |
| JD | $32.54 | $105.15 / **$228.10** / $430.43 (+223% / **+601%** / +1223%) | MC median $237.73; sensitivity to $1,331.86; comps $144.18 (+343%) | 79 Buy | **$227.70 only — the refusal sentence** |
| MRK | $128.33 | — | — | — | **NOT WITHHELD TODAY — see BUGS FOUND #1** |

The one surviving figure on each page is the guard's own sentence — *"the model's $1,288.94 is
14.0x the $92.19 price"*. That is the **evidence for withholding**, not a valuation, and it is
deliberately kept: a refusal with no stated cause is worse than the refusal.

Publishable names are untouched — verified on the same harness: AAPL renders cards
$100.48 / $122.01 / $148.20, the range bar, the Monte Carlo median $92.81, the full sensitivity
grid, comps implied values and a 51 Hold gauge, exactly as before.

## The 93/100 — it was NOT "everything except the DCF"

The prompt asked whether the score legitimately excludes the withheld DCF. **It does not, and
this is the more serious half of the bug.** Code path, measured on KSPI:

- `engine/pipeline.py:280` calls `compute_score(..., blend.value if blend.valuable else None, ...)`,
  so the margin-of-safety term **is** correctly dropped. That much the engine lane had right.
- `engine/scoring.py:83` then rebuilds it: `mc.prob_undervalued` carries **weight 0.30** of the
  valuation sub-score, and it is the share of Monte Carlo trials **of the withheld DCF** that
  beat the price — **1.00 on KSPI**.
- `engine/scoring.py:86` adds `comps.comps_fair_value` at **weight 0.15** — $326.32 against a
  $92.19 price, corrupted by the same KZT/USD mismatch that triggered the refusal.
- Result: the valuation sub-score printed **100.0 / 100** on a name the model had just declined
  to value, and the composite printed **93 "Strong Buy"**.

It is worse than a leak. `engine/scoring.py:228` holds a sanity cap — *"never surface a >5x fair
value as a strong buy"*, which forces the composite to 50 — and it is written `if base_fv and …`,
so **it cannot fire once the guard has set `base_fv = None`**. Publishing the bad number capped
KSPI at 50. Withholding it let KSPI print 93.

**This lane did not touch the score's definition** — that is the engine lane's, and the prompt
was explicit about not fixing a display problem by quietly redefining a number. What ships here
is a refusal to *publish* a figure that is demonstrably contaminated, plus the reason in plain
words on the page: the gauge reads **"Not rated."**, the valuation bar reads **"withheld"**
(not "n/a", which would claim it could not be computed), and the four sub-scores with no fair
value in them — quality, growth, health, momentum — still show.

## How it is enforced (two locks, because this bug was one lock failing)

1. **`valuation/web/withhold.py`** (new, pure) — `withhold_derived_figures(payload)` strips
   every DCF-derived figure from the `/api/value` response **before it reaches the browser**:
   the scenario cone, `dcf_per_share`, the per-share/equity values and FCF rows in `scenarios`,
   the blend's `lenses` / `value_low` / `value_high`, `growth_lens`, all of Monte Carlo
   including `prob_undervalued`, the sensitivity grid, the reverse-DCF read, comps `implied` +
   `comps_fair_value`, and the score + recommendation. So the numbers are not in view-source,
   not in the network tab, and not one console line from being republished.
   Ratios survive on purpose: **P/E, EV/EBITDA, P/S, EV/Sales are currency-neutral** (a ratio of
   two same-currency figures), while the per-share values implied *from* them are not — that
   step is exactly how a $92 stock showed a $326 implied value.
2. **`static/app.js`** — `render()` branches on the same `notValuable` test the headline uses;
   every call that draws a DCF-derived figure now sits in the else-branch, and `withheldCards()`
   writes the reason where each card was. It also **destroys the Chart.js canvases** — skipping
   a draw would have left the *previous* ticker's cone on screen, which is the same bug with an
   extra step.
3. **Downloads refuse too** (`/api/export/pdf`, `/api/export/excel` → **409** with the reason).
   `report/pdf.py:97` builds the same cone from `scenarios.*.per_share`, so without this the
   withheld number just left the building in a file instead of on a screen. Rendering the
   refusal *inside* the documents belongs to whoever owns `valuation/report/**`; this lane can
   only decline.
4. A misleading message was removed: `/api/value` used to append *"Could not compute a per-share
   value (missing shares/price). Check the ticker symbol."* whenever `base_fair_value` was None —
   which now includes deliberate refusals, where it is simply false.

## The test that pins it — `tests/test_withhold.py` (16 tests, offline)

The fixture is the **real KSPI payload with the real figures that shipped**, so a regression
reproduces the actual bug rather than a sanitised one. The load-bearing test is the catch-all:
`test_no_withheld_figure_survives_anywhere_in_the_valuation_blocks` walks **every number in
every valuation block** and requires it to be within 5× the price — so a card added next year
that starts republishing the DCF fails without anyone remembering to add it to a list. Around
it: the cone is gone; MC/sensitivity/reverse are gone; comps keep ratios and lose implied
dollars; the reason keeps its figure; the score is withheld with its note; a publishable name is
returned **byte-identical** (`out is payload`); the renderer's risky calls are all inside the
else-branch and each appears exactly once; the stale-chart path is closed; the live route's JSON
carries none of it; and both exports 409.

## Suites

**20 suites, 683 tests, all green** (was 667 — this adds 16). edge 221, screener 67, paper_track
40, ev_multiples 34, engine 33, private 30, saas 30, lazy_prices 28, lazy_prices_ic 24,
calibration 23, options_greeks 22, security 22, intraday 18, public 16, **withhold 16 (new)**,
bulk 14, factor_alpha 14, freeze 13, pead 12, sector_neutral 6.

## BUGS FOUND (noticed, not fixed — not this lane)

1. **MRK is no longer withheld, and that is the guard's threshold doing a defect's job.**
   Today MRK values at **$473.61 against a $128.33 price — 3.7×**, just under the 5× band, so
   everything publishes: cards **$243.37 / $473.61 / $911.94 (+90% / +269% / +611%)**, a
   sensitivity grid to **$1,660**, a Monte Carlo median **$896.19** with "100% of trials value it
   above today's price", and a **91 "Strong Buy"**. The model classifies **Merck as
   "hypergrowth"** with **~100% forward revenue growth** and **Rule of 40 = 119**. The refusal
   band is not the problem — the DCF is. → **engine lane** (`PROMPT_dcf_terminal_degeneracy.md`).
2. **`_valuation_score` re-imports the withheld valuation** (scoring.py:83/86) and the >5× cap
   at scoring.py:228 is dead whenever the guard fires (`if base_fv and …`). Full argument above.
   → **engine lane.** Until it is fixed, no composite score is published for a withheld name.
3. **The PDF and Excel exports build the DCF cone unconditionally** (`report/pdf.py:97-99`).
   Refused at the route here; the reports themselves should render the refusal instead of
   erroring out. → **whoever owns `valuation/report/**`.**
4. **The screener's own fair-value path is separate** and caps at 20× price
   (`screener/fairvalue.py:69`), where the page refuses at 5×. Two different bars for the same
   claim on two surfaces. The DCF-enriched rows use `res.base_fair_value`, which is correctly
   None for withheld names, so nothing leaks today — but the thresholds should agree.

## For Don

Nothing to do. Look up **KSPI** signed out: the headline still says it cannot value the name,
and now every card below it says the same thing and gives the reason, instead of printing
"$1,289.68 (+1299%)". The one dollar figure left on the page is inside the sentence explaining
why there is no dollar figure. The score reads **"Not rated"** rather than "93 Strong Buy" —
that is deliberate, and the page says why in a sentence.

---

# Session 11 — 2026-08-04 — Public + free, with a hidden owner view (PROMPT_appfixer_public_free.md)

Valquo is now **public and free to anyone, forever**, with the liability-shaped half held back
by an **owner split** instead of a locked door. Private mode is not deleted — it is one env var
away, and its whole test suite still runs.

## Flag states, and where each is read

| Flag | Was | Now | Read in |
|---|---|---|---|
| `PRIVATE_MODE` | **true** | **false** | `config.py` (derived properties) + `saas/private.py` (request policy) |
| `OWNER_SPLIT` | — | **true** (new) | `saas/surfaces.py` (request policy) + `_inject` → `may_see_owner` in every template |
| `BETA_MODE` | true | **false** | `Config.beta_banner_enabled` → `_beta_banner.html` |
| `OPEN_ACCESS` | true | true (unchanged) | `Config.public_access` |
| `PORTFOLIO_PAGE` / `PORTFOLIO_PATH` | true / `/work` | unchanged | `saas/private.py`, the route in `app_saas.py` |

Derived, and unchanged in value: `signup_enabled` **false** (no public signup — registration is
refused at the route, not just hidden), `billing_enabled` **false** (no payment can be
initiated even with Stripe keys set).

`PRIVATE_MODE` now parses as `== "true"` rather than `!= "false"`, so a typo or an empty value
comes up public-with-the-split rather than half-locked. `BETA_MODE` went off because its copy
("everything is unlocked free **while we build**") promises a paid product later; neither half
of that is true, and the header now states the real posture instead.

## Why this is still licence-clean — recorded so nobody re-litigates it

- **No commercial activity.** Free, no billing, no revenue, no customers → no "business use"
  trigger under ThetaData Individual or Sharadar's individual terms.
- **The live path is FMP + Tradier.** Sharadar and ThetaData are **backtest-only** and reach
  exactly one HTTP route between them (`/api/edge/*`, plus the ThetaData-derived reference
  figure inside `/api/options-paper`) — both **owner-only**.
- **Derived statistics Don computed are his; raw vendor rows are not.** That line did not move.
  It is why `/methodology` and `/work` may quote backtest statistics while no vendor row,
  price, fundamental or per-name panel value is served to anyone.

## The split — every surface, and the vendor behind it

**PUBLIC (no login, full render).** Analysis only.

| Surface | What it serves | Vendor |
|---|---|---|
| `/` landing | cached sample valuation + scan date | FMP |
| `/app` → Single valuation (`/api/value`, `/api/rank`, `/api/export/*`) | live DCF, bull/base/bear, score | FMP + SEC EDGAR + Treasury; AI commentary optional (Anthropic) |
| `/app` → Hot stocks (`/api/hotstocks`) | the daily ranking snapshot | FMP (yfinance fallback) |
| `/app` → Watchlist | scores a typed list | FMP |
| `/api/whatdo` | one name — **ranking half only** | FMP |
| `/api/tickers`, `/api/regime` | typeahead; 10Y / VIX / SPY-vs-200dma | local; Treasury + yfinance |
| `/methodology` | method + derived research statistics | derived from the Sharadar backtest (statistics, not rows) |
| `/work` | the portfolio page | none at runtime (static) |
| `/terms`, `/privacy` | prose | none |

**OWNER-ONLY (403 + `owner_only`).** Three reasons, named per entry in `saas/surfaces.py`:

| Surface | Why | Vendor |
|---|---|---|
| `/api/track`, `/api/index-track` | performance claim (forward record, equity curve) | Tradier **sandbox** + FMP marks |
| `/api/options-paper`, `/api/options-scorecard` | performance claim (paper option book, expectancy) | Tradier sandbox fills; **ThetaData**-derived reference |
| `/api/valquo-index` | actionable live pick (names **and weights**, today) | FMP |
| `/api/options-alerts` | actionable live pick (a contract, a size, a risk budget) | Tradier chains |
| `/api/signals`, `/api/signals/run` | actionable live pick (intraday feed) | Tradier / free stack + Anthropic |
| `/api/portfolio` | actionable live pick (an allocation) | FMP |
| `/api/backtest/run`, `/api/scan/run` | backtest internals; expensive vendor-quota triggers | FMP / yfinance |
| `/api/edge/*` | research bench + adopted weights + `fundamental_backtest` meta | **Sharadar**-derived |

**Judgement call worth flagging:** the **portfolio builder** is owner-only. A ranked list is
analysis, but "these fifteen names at these weights" is an allocation, and it was the most
recommendation-shaped output in the app. One line in `surfaces.py` moves it back if Don
disagrees.

In the UI the four owner tabs (Index, Signals, Track Record, Edge Lab), the live-track band
above every tab, the portfolio-builder card and the "Run scan now" control are **removed from
the DOM** for a visitor, not hidden with CSS — so their loaders never fire and no owner-only
endpoint is called for a visitor at all. `/api/whatdo` withholds the book/paper half and
**says so** rather than omitting the key (an absent field reads as "not in the book", which is
a different and false statement).

## Verified logged out

`/` `/app` `/methodology` `/terms` `/privacy` `/work` → **200**, fully rendered.
`/api/health` `/api/hotstocks` `/api/tickers` `/api/regime` `/api/value` → **200**.
All twelve owner-only paths → **403** with `owner_only`, and the refusal body carries none of
`cum_`, `excess`, `expectancy`, `holdings`, `occ_symbol`. `POST /register` with a valid CSRF
token → 302 and **no account created, no session**. Logged in as owner: all four tabs and every
owner endpoint return 200.

**Crons unaffected.** Every scheduled job hits `/admin/*` with `X-Admin-Token`; `/admin/` is not
in the split, and the guard bypasses the split for a valid admin token anyway. Re-verified that
`run-scan`, `run-intraday`, `run-paper-track`, `post-recap`, `export-track`, `run-learning` and
`ingest-snapshot` all still reach their token check (401 `unauthorized` on a wrong token, not a
403 from the split).

## Liability posture

- The not-advice line is now **on screen on every tab** (a strip above the tab content, not
  only in the footer), plus the header line, plus the footer — all three name: model output of
  general application, no recommendations, **no advisory relationship**, **no warranty**, **no
  duty to update or maintain**, risk of loss, do your own research.
- **`/terms` rewritten.** The old page described a paid subscription service, carried nine
  `[bracketed]` placeholders and a public "DRAFT — attorney review required" banner. All of
  that was wrong on a site with no fees, no subscriptions and no user accounts, and a public
  draft banner tells the reader the disclaimer above it is not meant seriously. It now covers:
  no advisory/fiduciary relationship · impersonal and general · backtests are a **historical
  simulation** · any forward record is a **broker sandbox paper account with no real money** ·
  no duty to maintain · **as is, no warranty of any kind** · limitation of liability (nothing
  is charged; residual cap $100) · acceptable use · Virginia law. **The attorney-review note is
  now shown to the owner only** — that is a deliberate call, flagged here rather than buried.
- **No performance claims in public**, enforced by a test that greps every public page.

## The one number the posture now permits

Audit **R1** cleared its pre-registered threshold, so the FF5+MOM result may be stated. It
appears on `/methodology` and `/work`, both times wearing its labels: **+8.81%/yr, NW t 5.74**,
with the passive-ETF placebo at **t 0.45**, described as a **historical simulation**, explicitly
**"not an expected return, not an achievable return, and not a return anyone earned"**, with
the +6.6% conservative figure, the missing multiplicity correction, and the fact that it does
**not** overturn X4's null against buyable factor ETFs. A test asserts that if `8.81` appears on
a public page, those labels appear with it.

Two stale claims were corrected on `/methodology` while it was open: the "Deflated Sharpe is
saturated" bullet now discloses that it is an **undeflated** PSR (audit B9), and the "sector
ranking is inert because the classification is not wired" bullet is replaced by the true state
— sector is wired at 100% coverage, sector-neutral ranking was **rejected**, and the live path
still inherits it on, which is a recorded open discrepancy (audit B7/G).

## How Don reaches the hidden login

**`valquo.co/login`**, or the small **"Owner login"** link in the footer of every page. There is
no "Sign in" in the nav — with exactly one account on the instance it would be a control that
does nothing for every visitor while competing with "Open the app". Registration is closed, so
that link is a door for one person.

**Not changed, and worth a decision:** `robots.txt` still says `Disallow: /` from the private-mode
era, so the public site is reachable by anyone with the link but **will not appear in search**.
The prompt did not ask for search visibility and turning it on is an outward-facing change, so
it was left alone — flip it to `Allow: /` in `app_saas.robots_txt` if Don wants traffic. `/work`
stays out of the index either way: it sends `X-Robots-Tag: noindex` on its own response.

## Suites

19 suites green, **628 tests**, including a new `tests/test_public.py` (**16**) that pins the
posture: the public half renders in full, every owner-only path refuses outright, every `/api`
route is knowingly on one side of the split (an unclassified new route fails the suite), the
split reverts with its flag, the Terms keep their four clauses, and no public page makes a
performance claim. `tests/test_private.py` (30) still runs the whole lockdown with
`PRIVATE_MODE=true`, which is what keeps "the flag restores the personal tool" a tested claim.

## Reversing this

- Lock it back down: `PRIVATE_MODE=true` (owner-only, nothing served to anyone else).
- Publish everything: `OWNER_SPLIT=false` — read the Terms first; it turns performance claims
  and live positions back on.
- Go commercial: `OPEN_ACCESS=false` (+ `FEATURE_BILLING=on`) restores signup, tiers and
  Stripe, all still tested — and the Terms would need rewriting for a paid service, with an
  attorney.

---

# Session 10 — 2026-08-04 — The recruiter page (PROMPT_recruiter_page.md)

One unlisted page Don can put on a résumé. It is the single deliberate exception to private
mode, it has **its own flag**, and it is **method-led**: the rejections and the bugs come
before anything that survived.

## The flag and the URL

| | |
|---|---|
| Flag | **`CONFIG.portfolio_page`** (env `PORTFOLIO_PAGE`, default **true**) |
| Path | **`CONFIG.portfolio_path`** (env `PORTFOLIO_PATH`, default **`/work`**) → **`https://valquo.co/work`** |
| Read in | `saas/private.portfolio_open()` (the request-level grant) and the route in `app_saas.py` |
| Template | `valuation/web/templates/portfolio.html` — standalone, does **not** extend `_saas_base.html` |
| Tests | `tests/test_private.py`, 8 new (30 total, all green) |

`PORTFOLIO_PATH` is **validated** (`Config.resolved_portfolio_path`): a leading slash is
added, a trailing one stripped, and `"/"`, empty, and every reserved prefix (`/api`, `/admin`,
`/static`, `/login`, `/app`, `/billing`, `/robots.txt` …) fall back to `/work`. That matters
because Flask keeps the **first** rule registered for a path, so a typo like `PORTFOLIO_PATH=/app`
would have shadowed the dashboard *silently* rather than raising. Both are declared in
`render.yaml` next to `PRIVATE_MODE` so they are flippable from the Render dashboard.

**The two flags are independent in both directions**, and a test asserts it: the page can be
open while the instance stays locked (its whole purpose), and `PORTFOLIO_PAGE=false` re-closes
the page without touching anything else. With the page off, private mode absorbs the URL and
returns the ordinary 401 holding page — indistinguishable from any other path, so it does not
confirm the URL means anything. On a **public** instance (`PRIVATE_MODE=false`) the route
itself 404s. Both branches are tested.

## Private mode is unaffected — verified logged out

Anonymous, with no session: `/work` → **200**. `/` → 401, `/app` → 401, `/methodology` → 401,
`/account` → 401, `/api/hotstocks` → 401, `/api/track` → 401, `/api/valquo-index` → 401. The
pre-existing sweep over the app's own URL map (every registered `/api/` route refuses an
anonymous caller) still passes unchanged, as do the cron-route tests — the admin endpoints
still reach their token check rather than being blocked by private mode.

The grant is **exact-match on one path**, never a prefix: `/work/secret`, `/work2`, `/works`
and `/work/api/hotstocks` are all still refused. The portfolio path is deliberately **not** in
`private.always_open()` — that list is unconditional, and putting it there would have let the
page survive `PORTFOLIO_PAGE=false`. A test pins that too.

## No vendor data — and it is checkable, not promised

The page is **static by construction**: the route passes one variable (`contact_email`), the
template reads no store, and there is no `<script>`, no `fetch`, no `/api/` string anywhere in
the rendered HTML. Two tests make that a property of the code — the response is asserted
**byte-identical across two requests** (so nothing live is feeding it) and swept for `/api/`,
`fetch(`, `sharadar`, `thetadata`, `tradier`. Every number on it is a summary statistic
computed in-house; no Sharadar or ThetaData row, price, holding or ticker score appears.

**Unlisted:** `noindex, nofollow` three ways — `<meta name="robots">`, an `X-Robots-Tag:
noindex, nofollow, noarchive, nosnippet` response header, and a new `/robots.txt` with a
blanket `Disallow: /`. It **names no paths on purpose** — robots.txt is world-readable, so a
file saying `Disallow: /work` would publish the URL it is hiding. `/robots.txt` was added to
`private.always_open()` (a crawler cannot log in to read the file that tells it to go away).

## What the page says, and where every number came from

Method first, numbers as illustration. Sections in order:

| Section | Claims | Source in this repo |
|---|---|---|
| **The method** | pre-registration protocol; ~146 recorded tests, ~1 adoption in 8 | `RESEARCH_LOG.md`, `VALQUO_EDGE_AUDIT.md` §1 |
| **What the evidence killed** | PEAD (standalone t +2.215, incremental t +0.020, control +0.83pp vs +0.52pp); lazy prices (7,095 pairs, 195 filers, IC −0.0156, NW t −1.07, LS −5.0%/yr); sector-neutral (LS t 3.40→3.90 but alpha +11.8%→+10.2%, PBO 26.7%→46.7%, rejected twice); put-credit spreads (fails 5 of 7 arms); exit sweep (+2.1–3.3pp vs a +10pp bar); option cross-section (nothing clears, one sign backwards); ETF benchmark (+9.21pp but t 1.10, halves −6.40%/+27.08%) | `HANDOFF_pead.md`, `HANDOFF_lazy_prices_ic.md`, `HANDOFF_sector_neutral.md` + `CLAUDE.md`, `HANDOFF_vrp.md`, `HANDOFF_deep_exits.md`, `HANDOFF_deep_xsection.md`, `HANDOFF_free_analysis.md` (X4) |
| **The uncomfortable one** | random-entry control beats the signal: +11.07% (5,919) vs +5.14% (3,042), paired −3.72pp, sign z −3.48, negative in both halves (−5.88 / −5.96pp); 15 corrected arms all fail — **plus the caveat that the control is a yardstick, not a tradable alternative** | `HANDOFF_entry_fix.md` |
| **Bugs, found and published** | price basis (adjusted close into option maths, 5 call sites); five empty factors (roe/roic/assetturnover 0 of 197,265 rows, beta hard-coded, growth_accel NaN'd); stale-quote settlement (44.6% fall-through, median 10 days early, 94.7% above settlement, 86.1% positive on worthless, −6.45pp); OI `-1` sentinel (106 names, median 12.2%, guard blind on 82 of 109); "800 largest" was alphabetical; currency-corrupted value ratios (892 vs 0.589, 4.1% of rows, 1.35×→0.56×) | `HANDOFF_edge_audit.md` (B1/B3/B12), `CLAUDE.md` LATEST, `HANDOFF_greeks.md`, `HANDOFF_deep_exits.md`, `CLAUDE.md` P7 |
| **The external audit** | 134 numbered items, read-only, dependency map + import-graph lane validator; the four claims it invalidated (undeflated PSR, stability-not-OOS, PBO scope, never tested as alpha) | `VALQUO_EDGE_AUDIT.md` (134 keys in `valquo_audit_items.json`), `VALQUO_AUDIT_DEPENDENCY_MAP.md`, `check_lanes.py` |
| **What survives** | LS t **3.52** vs the Harvey–Liu–Zhu 3.0 hurdle; costs breakeven **236 bps** one-way vs a **37 bps** profile at 249% turnover; international replication Japan +2.05%/**t 3.85**, developed Europe +3.36%/**t 4.30**, world ex-US t 5.03, **US control weakest at t 2.35**, 12 of 15 European countries clear t>2 — with Japan's quality/momentum failure reported | `CLAUDE.md`, `BACKTEST_RESULTS.json`, `HANDOFF_free_analysis.md` (X8) |
| **What is NOT claimed** | not established as alpha (FF5+MOM unrun, threshold pre-committed); first third of the panel has a distorted universe (B6); capacity ≈ **$23M** upper bound; one panel, looked at many times | `HANDOFF_edge_audit.md` (R1), `CLAUDE.md` (B6), `HANDOFF_free_analysis.md` (P1) |
| **The forward track** | labelled **broker sandbox, paper account, no real money**, days old — and **no number from it is quoted** | `HANDOFF_paper_track.md` |
| **How it is built** | CPCV + PBO, coverage/sanity/cost/freshness blocks, attribution panel, **597 tests across 17 suites** | measured this session |

Three things the page deliberately does **not** do: quote a headline return as the lead, show
any current holding or pick, or call anything "alpha". The word appears once, in the box
explaining why it is *not* used.

## Suites

All 17 green after the change: edge 191, screener 63, paper_track 40, ev_multiples 34,
saas 30, **private 30 (+8)**, engine 28, lazy_prices 28, lazy_prices_ic 24, calibration 23,
security 22, options_greeks 21, intraday 18, bulk 14, freeze 13, pead 12, sector_neutral 6 —
**597 total**.

## For Don

The URL is **valquo.co/work** once this deploys. Nothing links to it and it is excluded from
search; it only exists for someone you hand it to. To move it, set `PORTFOLIO_PATH` in Render
to anything unguessable (`/work/8f2c…`) — no code change, no redeploy of the image. To remove
it, `PORTFOLIO_PAGE=false`. Neither touches the lockdown on everything else.

---

# Session 9 — 2026-08-04 — Private mode: Valquo becomes a personal tool (PROMPT_appfixer_private.md)

All seven items shipped. Valquo is now owner-only behind one reversible flag, every commercial
surface is off, and the forward track — the one dataset here that cannot be rebuilt — is backed
up into git on a weekly schedule. Nothing in this session touches the options backtest, the
fundamental panel or the miner.

## The flag

**`PRIVATE_MODE`, default `true`** (`valuation/config.py`). Also declared in `render.yaml` so it
is visible and flippable in the Render dashboard rather than hidden in a code default.

It is read in exactly two kinds of place, which is what makes it auditable:

1. **Three derived properties on `Config`** — `public_access`, `signup_enabled`,
   `billing_enabled`, plus `beta_banner_enabled`. No template or route tests `private_mode`
   arithmetic itself; they read a named concept.
2. **`valuation/saas/private.py`** — the request-level policy, called from `app_saas._guard`
   before any other access decision. `check(path, user, cfg)` is a pure function returning
   `None` (allow) or a refusal dict, so "prove the lockdown holds" is a unit test rather than a
   browser session.

**It outranks every flag that would open the product**, and each is asserted separately:
`OPEN_ACCESS=true`, `BETA_ALL_PREMIUM=true`, an explicit `FEATURE_BILLING=on` and a configured
Stripe key all fail to re-open anything. A lockdown that another flag can quietly undo is not a
lockdown, and `FEATURE_BILLING=on` in particular used to be an explicit "force the pricing page
visible" override — it is now refused.

**Nothing is deleted.** Every tier, route, template and Stripe path is intact and still under
test. See "Reversing this" at the end.

## 1. Locked to the owner

`_guard` refuses everyone but the owner, ahead of the landing page, the tier caps and the
per-visitor rate limit — because all three implement the public product, and shaping a
stranger's request with "what may a visitor see" logic before asking whether there is supposed
to be a visitor is the wrong order.

- **Owner = a real signed-in account whose address is in `OWNER_EMAILS`.** A demo/preview
  session is explicitly *not* the owner even though `gating._active` grants it Premium.
- **Signed in but not the owner is refused too** — which is why the concept is `public_access`
  and not simply `open_access`.
- **The refusal is identical for anonymous and for signed-in-as-someone-else.** The difference
  is not information a stranger should have, and leaking it is a free account-enumeration
  oracle. Pinned by a test.
- **Anonymous gets a plain holding page** (`private_landing.html`), not a trimmed landing page:
  no sample valuation, no track, no screenshot, no feature list, no signup. Plus
  `noindex, nofollow` and no Open Graph card — a rich preview advertising "a whole-market
  screener" is the wrong public face for an instance nobody can use.
- **`/demo` (the recruiter link) is refused outright**, handled conservatively per the brief.
  It is the one route whose entire purpose is letting a third party read the tool without an
  account. `private.is_owner` separately refuses to honour a surviving demo cookie.

Five things stay open, each for a stated reason, and the allowlist is pinned by a test so it
cannot be widened by accident:

| Open | Why |
|---|---|
| `/api/health` | `render.yaml` health probe. Blocking it makes Render roll back every deploy — the lockdown would take the service *down* rather than lock it. Returns three config booleans, no market data. |
| `/login`, `/forgot`, `/reset/<token>` | Or the owner can never get in. |
| `/admin/*`, `/api/option-alerts/*` | The crons. This lets them REACH `_admin_ok`; it does not skip it. |
| `/alerts/unsubscribe/<token>` | An unsubscribe link that requires signing in first is not an unsubscribe link. |
| `/static/` | The login page needs its stylesheet. |

Everything else is denied, so forgetting a route fails as "the owner has to log in", never as
"a stranger reads the book". A test sweeps the app's own URL map — not a hand-written list — so
an `/api/` route added next month is covered the day it is added.

## 2. Commercial surfaces off

No payment can be initiated: `/billing/checkout` and `/billing/portal` return **403**, and they
say why rather than claiming a misconfiguration — "Billing isn't configured (set
STRIPE_SECRET_KEY)" would be a lie that invites someone to "fix" it by setting a key, which
would not in fact re-enable checkout. `/pricing` and `/register` redirect (route-level, not just
hidden buttons). The Stripe webhook no-ops. The beta strip — "you're exploring the full app,
everything unlocked, no sign-up needed" — is off; it addresses prospective users and there are
none. Nav and footer drop every link that now 401s, so a logged-out visitor never sees a row of
dead links.

## 3. Vendor audit — what each surface actually serves

**Confirmed: no raw ThetaData and no raw Sharadar rows are exposed on any page or API route.**
Traced by reading each route's imports through to the provider, not by assuming.

| Surface | Numbers come from | Category |
|---|---|---|
| `/app` dashboard shell, `/methodology` | nothing — static copy | — |
| Single valuation (`/api/value`) | yfinance + SEC EDGAR (+ FMP if keyed), live Treasury | live vendor, derived (DCF output) |
| Hot stocks (`/api/hotstocks`) | the daily scan snapshot → FMP / yfinance / SEC EDGAR | derived (z-scores, 1–100 rank) |
| Valquo Index (`/api/valquo-index`) | the **same** snapshot, top-sliced | derived |
| Index forward track (`/api/index-track`) | Valquo's own recorded series (+ ingested Cowork tracker) | Valquo's own record |
| Signals (`/api/signals`, `/api/options-alerts`) | Tradier quotes + option chains (yfinance delayed fallback) | live vendor, derived (scores, sizing) |
| Options scorecard (`/api/options-scorecard`) | Valquo's own `option_alerts` table | Valquo's own record |
| Options paper (`/api/options-paper`) | Valquo's own alert table vs a hard-coded backtest constant | Valquo's own record + derived constant |
| Regime (`/api/regime`) | 10Y yield, VIX, S&P vs 200-day | live public market data |
| `/api/whatdo` | stored state only; recomputes nothing | derived |
| Edge Lab (`/api/edge/*`) | **Sharadar/WRDS exports** | **derived only** — walk-forward folds, ICs, Sharpes, row counts. No vendor rows. Owner-only before this change; now private-gated as well. |

Two honest notes, since the brief asked for the distinction rather than an assumption:

- **Derived vs raw.** The screener's factor weights in `screener/settings.py` are committed
  constants *measured on* the Sharadar panel, and `options_paper.py` compares against a
  hard-coded expectancy figure derived from the ThetaData panel. These are statistics computed
  from licensed data, not the licensed data — the ordinary output of research, and the category
  the vendors sell the data to produce. Worth knowing they exist; not a redistribution of rows.
- **ThetaData appears in `valuation/edge/options_*` only as research modules and comments.** No
  web route imports a ThetaData provider. The live options path is Tradier.
- **The new `data_export/` backup** contains Valquo's own paper record — Tradier *sandbox*
  marks, timestamps and computed P&L. No Sharadar and no ThetaData content. A test scans the
  written files for credential-shaped strings on every run.

## 4. Framing copy

The visible surfaces under private mode are the holding page, the login page and the dashboard.
The holding page says what this is in two sentences and offers a login. The dashboard header
carries a standing line — *"Private research tool — personal use only. Vendor data under
individual licences; not for redistribution"* — which is not a disclaimer for anyone else's
benefit (there is nobody else) but a reminder that makes "share a screenshot of the hot list" a
decision rather than a reflex. "Send feedback" is gone; it addresses a user of a service.
`/terms` and `/privacy` are kept and marked **Not in force**, which is more honest than leaving
a service agreement sitting on an instance with no users. **The "educational only, not
investment advice" disclaimers are untouched** — they still apply to Don.

## 5. The crons still run

All six admin routes reach `_admin_ok` unchanged, verified end-to-end and pinned by a test that
uses a **wrong** token deliberately — a correct one would actually run a market scan, a broker
cycle or a Discord post. The discriminator is which layer refused: private mode answers
`{"private_mode": true}`, `_admin_ok` answers `{"error": "unauthorized"}`. Seeing the latter
proves the request got through. Covered: `run-scan`, `run-intraday`, `run-paper-track`,
`post-recap`, `ingest-snapshot`, `ingest-index-track`, `export-track`, `option-alerts/*`.

They were never at risk of a session wall — they authenticate with a token and no cookie — but
"never at risk" is exactly the assumption worth testing before locking the front door.

## 6. Track backup — the irreplaceable dataset

Everything else here can be rebuilt: the panel re-reads Sharadar, the backtest re-runs, the hot
list re-scans. **The forward track cannot.** It records what the model said on days that have
already happened, and its whole value is that nobody could have seen the outcome first.
Recreating it later from current data would produce a different object with the same column
names — worse than losing it, because it would look fine.

It lives in one place: the SQLite DB on the Render service's persistent disk.

**The delivery problem, and why it is solved this way.** Render cannot commit to git and GitHub
Actions cannot read Render's disk. So the backup crosses the gap over HTTP: the service exposes
`/admin/export-track` (admin token, pure read), and a new **weekly `track-backup` workflow**
pulls it, renders the files, and commits them. Committed means it is in git history *and* on
Don's machine after a `git pull`.

Written to `data_export/`: `paper_track_history.json` (the complete artifact),
`paper_track_index.csv` (daily Index vs SPY), `paper_track_trades.csv` (every trade, entry →
exit → P&L), `paper_track_holdings.csv`, and a README so a CSV found in this repo years from now
is not a mystery. Three CSVs rather than the one the brief suggested, because merging a daily
return series with per-contract trades needs a `record_type` column and a union of ~30 mostly-
null columns — unreadable in a spreadsheet, which is the only reason to have CSV here. The JSON
is the complete artifact.

Design points worth knowing:

- **Both forward records are captured** — the Tradier sandbox book *and* the ingested Cowork
  tracker series. Backing up only the one the hero happens to lead with would silently lose the
  other.
- **Rewrite-in-full, not append-only.** Append-only preserves a corrupted row forever; the
  database is the source of truth. Output is deterministic (stable sort, fixed float precision)
  so a quiet week produces no diff and a real change produces a readable one.
- **The workflow refuses to shrink.** The failure that would actually destroy the record is the
  service coming up on a fresh disk and a well-behaved backup faithfully committing nothing over
  months of history. If the new export has fewer index days than the committed one, the job
  fails loudly instead of committing. `curl -fsS` so an HTTP error fails the step rather than
  committing `{"error":"unauthorized"}` over a good backup. Failure posts to Discord.
- **Stored raw-ish, not summarised.** Column names match the table columns exactly, so it can be
  re-inserted. A summary cannot be un-summarised.
- **Committed empty as a placeholder.** This machine's dev database holds synthetic fixture rows,
  and a file whose entire job is to be the real record must not ship with fake data in it.

**How Don gets it locally:** `git pull`, then look in `data_export/`. To make one on demand:
`python -m valuation.edge.track_export`. To pull the live one by hand, run the workflow from the
Actions tab (`workflow_dispatch`) — worth doing **before** ever touching the Render service.

## Verification

`tests/test_private.py` — **22 new tests**. Beyond them, the lockdown was exercised end-to-end
through the real SaaS app against real databases: 21 gated paths anonymous, 3 signed-in as a
non-owner, 7 as the owner, the six cron routes, both billing routes, and `/demo`.

`tests/test_saas.py` and `tests/test_security.py` now set `private_mode = False` at module
level. That is not a workaround — those suites are what prove the **public** product still
works, which is exactly what `PRIVATE_MODE=false` promises to restore. If every suite ran in
private mode, "flipping the flag back brings the product back" would be an untested claim.
Between the three files, both sides of the flag are covered.

## Reversing this — when Valquo goes commercial

One setting, in this order:

1. Get the licences the commercial posture needs: **ThetaData Business** (~$1,600/mo vs
   Individual) and a Sharadar plan permitting redistribution. This is the actual constraint —
   the flag is downstream of it.
2. Set `PRIVATE_MODE=false` on Render (it is already in `render.yaml`).
3. Choose the public posture with the flags that were always there: `OPEN_ACCESS=true` for free
   and open, or `OPEN_ACCESS=false` for the paid, signup-required product. `FEATURE_BILLING=on`
   forces the pricing surfaces regardless.
4. Stripe keys were left configured, so no secrets need re-entering.
5. Optionally re-enable `/demo` by setting `DEMO_ACCESS_TOKEN`.

Nothing was deleted and nothing needs rebuilding. `tests/test_saas.py` and
`tests/test_security.py` are the regression suite for that restored product.

## Honest limits

- **Verified through the app, not a browser.** Real requests against real Flask and real
  databases — which catches routing, gating and status codes, but not "does the holding page
  look right on a phone". Worth a two-minute eyeball after deploy.
- **The backup has not yet run against Render.** The endpoint, the renderer and the shrink-guard
  are all tested locally, but the first real pull happens on the first workflow run (or a manual
  `workflow_dispatch`). **Do that once by hand before trusting it** — it needs `SITE_BASE_URL`
  and `ADMIN_TOKEN` as Actions secrets, which the auto-scan workflow already uses, so there is
  most likely nothing to add.
- **This is the first workflow in the repo that commits to `main`.** That is what "backed up in
  git history" requires, but it is a real change in how the repo operates and Don should know it.
- **The lockdown is an application-layer boundary.** Anyone with the `ADMIN_TOKEN`, the Render
  dashboard or the database file still has everything. That is the right scope for a licence
  posture; it is not a threat model against a determined attacker.
- **Carried forward, still outside my access:** `DISCORD_WEBHOOK_URL` on Render (Session 7);
  `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID` on Render (Session 6) — until those are set
  the paper track does not run, and a backup of an empty track is what it is.
- **Still awaiting a decision from Session 8:** the ~70 lines of dead custom-backtest JS.

---

# Session 8 — 2026-08-03 — Phase 9 UX round 2 (PROMPT_appfixer_phase9.md)

All four items in the prompt shipped, one commit each, all suites green. Nothing in this
session touches the options backtest, the fundamental panel or the miner.

## 1. "Why this score" — the hot score is no longer a black box

Every row in the Hot Stocks table now has a **"why?"** button. It opens a panel showing which
themes produced that name's 1–100: a diverging bar per theme (right = pushed the score up,
left = held it back), the size of each push, and each theme's share of everything that moved
the name. Plain-English labels, so "capital_discipline" reads as "Capital discipline — not
issuing shares to fund itself".

**The important part is that the explanation IS the score, not a story told next to it.**
`valuation/screener/attribution.py::decompose()` returns the composite *and* its per-theme
pieces from one calculation, and the scan's `_composites()` now delegates to it. The pieces
sum to the composite exactly, and a test asserts that on every scored row. A second test
recomputes the composite the old way, directly from `composite_score`, under both bucketing
modes, to prove the ranking itself did not move.

The old per-pick "why" was wrong in a way nobody would have noticed: it multiplied the stored
weight by the theme value *before* the second standardization, using whichever weight set the
hard bucket named. It ordered the themes roughly right, so it looked fine — but its numbers
added up to nothing in particular, and under soft bucketing it credited a weight set the name
was only partly scored under.

**Computed at scan time, deliberately.** `value` is scored on two different input sets
(earnings-based for profitable names, sales-based for loss-makers) and soft bucketing blends
both, so the single blended `value` column in a saved snapshot cannot be split back apart
afterwards. Re-deriving the attribution at read time would also explain the score using
whatever weights the learner has adopted *since*, not the ones the scan ranked on.

**Consequence for Don: the panel is blank until the next daily scan runs.** Rows saved by an
older scan say so ("it is written at scan time … it appears after the next daily scan")
rather than showing an approximation. One scan fixes it; no action needed.

Honesty constraints baked in: contributions are in composite units (standard deviations
versus that day's scan), **not** points of the 1–100, because the score is a percentile *rank*
of the composite — monotone but not linear. And shares are of the **absolute** push, so a name
whose themes nearly cancel can't produce shares in the hundreds of percent.

**Bug found along the way:** `.pos` and `.neg` had **never been defined in any stylesheet**,
while app.js applies them in about fifteen places — fair-value upside, track-record alpha,
paper P&L, the why-chips. Every one has been rendering as plain body text, so a −18% and a
+18% looked identical at a glance. Defined once; all of them are now green/red.

## 2. The live forward track leads the page

The one number in this product that nobody could have fitted was three clicks deep, inside the
Index tab, underneath a backtest. There is now a **band above every tab**: Valquo Index vs SPY
since inception, the excess, the day count, the paper options book's live/closed counts, and a
shared-axis sparkline.

**It is server-rendered**, so it is in the HTML the browser receives — no spinner, no layout
shift, no round trip before the most important evidence on the page appears. It is a Jinja
*callable* in the shared context processor rather than a value, so the renders that don't show
it (landing, pricing, error pages) don't pay for its database reads, and a failure returns the
not-started shape instead of 500-ing a page that would otherwise have been fine.

Leading is not boasting. The gates live in `valuation/web/hero.py`, not the template:

- **Paper, always**, labelled with its inception date — and the label comes from the track
  modules themselves (`paper_track._label`, `index_track.summarize`), so the hero cannot grade
  the track more generously than `/api/track` does.
- **Thin until the owning module says otherwise.** While thin the band turns amber, carries a
  "too early to judge" pill, and `may_lead` is False. A week of noise gets shown, not
  celebrated.
- **An expectancy below the 30-closed floor is withheld, not printed small** — a printed number
  gets quoted, a withheld one gets read. One closed winner shows "needs 30 closed".
- **No data means no band for a visitor.** A backtested curve under a "live" heading would be
  the most dishonest thing this page could show, and a "coming soon" strip is clutter. *You*
  (owner) see a muted "not started" line, so a track that quietly stops stays visible to the
  person who can fix it.

Two forward records exist — the ingested Cowork tracker and the Tradier sandbox book. The hero
prefers the one the Index tab leads with, falls back to the other, and **names which it drew**;
an unlabelled fallback would silently swap the meaning of the number between deploys. The
fractions-vs-percent difference between the two is pinned by a test.

Verified by rendering the real template in four states — thin, mature, no-data-visitor,
no-data-owner — 12 assertions, all passing.

## 3. Stock + options in one "what this tool does with this name" view

New card under the valuation hero, on the Single tab. For whatever ticker you just valued it
shows: rank in today's scan, whether the Valquo Index holds it and at what weight, whether the
paper account is in it, any scream-buy options alert with whole-contract sizing, and the same
"why this score" bars from item 1. The opportunity score, the alert and the tracked outcome
used to live on three tabs that never met.

`/api/whatdo` is a **read over stored state** — snapshot, constructed book, logged alerts,
paper positions. It recomputes nothing: every figure comes back from the module that owns it,
so the panel cannot disagree with the tab it summarizes, and it needs no network call. It is
fired *after* the valuation paints and never awaited, so a slow or broken response cannot
delay or break the page it decorates.

Each honesty rule is pinned by a test:

- **Never a per-ticker hit rate.** One name yields a handful of trades at most, so it reads
  "1 of 1 won (too few trades on one name to read as a rate)" — a count, never a percentage.
  The convexity line (~37% backtested hit rate, convex not likely) rides along with every
  options figure.
- **Whole contracts, and zero is a real answer.** A $25 premium against a $1,000 risk budget
  sizes to none, not to one: "one contract costs more than the risk budget — the honest size
  is zero, not one".
- **An absent name is absent, not bad** — "the screen covers a defined universe, so being
  absent says nothing about the company", with no score or rank invented for it.
- **Withheld ≠ empty.** The free tier does not read the options record, so it must not report
  an empty one; it says the contract is part of Signals, and still carries the convexity
  caveat. (Gating: the ranking half is public — it is the same ranking the Hot tab serves —
  while the specific contract follows the existing Signals feature flag.)
- **The action lines describe what the model is doing**, never what you should do, asserted
  against a list of recommendation phrasings.

## 4. Perceived speed + mobile

Hot, Index and Track read a snapshot that changes once a day, so waiting on the network before
painting anything meant staring at a spinner for data the browser already had. They now paint
the **last good copy immediately** and replace it when the fetch lands. A genuinely first visit
gets a **table-shaped skeleton**, so the real table arrives without the page jumping.

Two rules keep the cache from becoming a lie — the second was a bug in my own first version:

- A cached paint is **labelled** ("showing your last copy, loaded 3 hours ago — refreshing…"),
  and if the refresh fails the error says the ranking above is a saved copy, not a fresh one.
- The freshness verdict **inside** a cached payload was computed when it was cached, so a copy
  saved yesterday still said "ranking from today" — exactly the lie the freshness banner was
  built to prevent. It is now suppressed until the live fetch replaces it.

The cache hard-expires at 36 hours, and degrades to nothing under private mode, quota errors
or a corrupted entry (all three exercised).

Mobile: the hot table's min-width goes 560 → 620 now that it carries the "why?" column, or the
columns crush instead of scrolling; the attribution panel is stopped from inheriting that
minimum (it lives *inside* the scrolling table and would otherwise scroll sideways with the
row that opened it); the unified card stacks rather than squeezing four stats across a phone;
the hero sparkline goes full-width under the numbers. Skeletons honour
`prefers-reduced-motion`.

## A finding for Don to decide on

A new static wiring check (app.js writing to an element id that does not exist in the template
fails **silently** — the write lands on nothing and the panel just stays blank) surfaced
pre-existing dead code: the custom-backtest UI block in app.js — `runBacktest`,
`renderBacktest`, `eqChart`, `qChart`, `renderBtStats`, ~70 lines — references a form
(`btSource`, `btTickers`, `btLoader`, …) that is **no longer in index.html**, and nothing calls
it. The `/api/backtest/run` endpoint behind it is still live and still gated as a paid feature.

It is dead, not broken. I left it in place — deleting it is your call, not a UX round's — but
it is allowlisted in the test so it cannot grow, while the new surfaces are asserted by name.
**Say the word and I'll remove it**, or re-wire a UI for it if the feature is wanted back.

## Files changed

| File | What |
|---|---|
| `valuation/screener/attribution.py` | **new** — exact decomposition of the composite into per-theme contributions |
| `valuation/screener/screen.py` | `_composites` delegates to it; rows carry the real `why` + `why_composite` |
| `valuation/web/unified.py` | **new** — the per-name joined view (`name_view`) |
| `valuation/web/hero.py` | **new** — the live-track hero band, with its honesty gates |
| `valuation/web/app.py` | `/api/whatdo`; `live_hero` in the shared template context |
| `valuation/saas/app_saas.py` | per-tier `g.may_see_options` for the options half of the name view |
| `valuation/web/templates/index.html` | hero band, unified card, cache slots |
| `valuation/web/static/app.js` | attribution panel, unified view, skeletons, last-good cache |
| `valuation/web/static/style.css` | attribution bars, hero band, skeletons, cache bars, `.pos`/`.neg`, mobile |
| `tests/test_screener.py` | 51 → 63 (attribution sums, ranking unchanged, name-view honesty) |
| `tests/test_paper_track.py` | 34 → 40 (hero gates) |
| `tests/test_saas.py` | 28 → 30 (static UI wiring) |

## Verification

Every suite green: **edge 142, screener 63, saas 30, paper-track 40, intraday 18, engine 28,
bulk 14, security 22, sector-neutral 6, PEAD 12, calibration 23, EV-multiples 34, freeze 13,
lazy-prices 28, lazy-prices-IC 24, options-greeks 21.**

Beyond the unit tests: `/api/whatdo` exercised end-to-end through the real SaaS app against the
real screener DB (including the no-ticker 400 and an unknown ticker); `index.html` rendered
through the real Jinja environment in four hero states; the JS render helpers and the cache
exercised under a DOM shim in Node (expiry, corruption, blocked storage).

## Honest limits

- **The attribution panel is empty until the next daily scan.** By design — see item 1.
- **The hero shows nothing to visitors until the forward track reports.** It is currently
  gated on the same thing everything else is: the paper track actually running on Render,
  which still depends on `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID` being set there
  (Session 6's outstanding item) and `DISCORD_WEBHOOK_URL` for the recaps (Session 7's).
- **None of this was opened in a real browser.** It is verified by rendering the template, the
  JS helpers under a DOM shim, and static wiring checks — which catches typos, dead ids and
  wrong numbers, but not "does the band look right on an iPhone". Worth a two-minute eyeball
  after deploy.
- The per-name options record is genuinely thin and will stay thin for months. That is the
  point of the labels, not a defect to fix.

---

# Session 7 — 2026-08-03 — Daily + weekly Discord recap of the paper track (PROMPT_appfixer_discord_recap.md)

## What Don gets

Two automated Discord posts about the forward paper track, both server-side, both running with
his computer off:

- **Mon–Thu, ~5 min after the paper-track cycle** — a short daily: options open / opened today /
  closed today with each trade's P&L, expectancy to date against the backtest reference, then
  Index vs SPY for the session and since inception, holdings count and any additions.
- **Friday, same slot** — a fuller weekly: the week's closed trades and P&L for both books, hit
  rate and expectancy to date, best/worst trade, the index cumulative, and a health line.

**Friday posts the weekly INSTEAD of the daily, not as well as.** The weekly is a superset;
firing both a minute apart would just train him to skim past them. Every weekday still gets
exactly one post.

## The one thing Don must do

**Set `DISCORD_WEBHOOK_URL` on RENDER** (Dashboard → valuation-tool → Environment). It is now
declared in `render.yaml` with `sync: false`, so it appears as a blank to fill in.

This is *not* the same as the GitHub Actions secret of the same name. The Actions secret feeds
the scan-failure alert and the watchdog, which run on the runner. The recaps post from inside
the web service, so they read Render's copy. Until it is set the endpoint returns
`posted: false` with a reason and the Actions job emits a **warning, not a failure** — a
missing optional notification must not turn the pipeline red.

Same standing item as the last two sessions, now with a second reason to do it.

## The cron entries

| where | when (UTC) | posts |
|---|---|---|
| `auto-scan.yml` job `recap` | `58 20` **and** `58 21`, Mon–Thu | daily |
| `auto-scan.yml` job `recap` | `59 20` **and** `59 21`, Fri | weekly |
| `render.yaml` cron `paper-recap-daily` | `58 21`, Mon–Thu | daily |
| `render.yaml` cron `paper-recap-weekly` | `59 21`, Fri | weekly |

Two Actions crons per kind for the same DST reason as the paper track: a crontab cannot say
"after the 4pm Eastern close", so one entry is correct under EDT and the other under EST, and
`/admin/post-recap` applies the same `market_session` guard the paper track uses. Render gets a
single entry each at 21:5x UTC, which is after the close in both regimes.

Both land ~11–13 minutes behind the paper-track cron, so the recap describes a **finished**
cycle rather than the previous day's.

Manual run: Actions → "Auto scans" → Run workflow → kind `recap-daily` or `recap-weekly`.

## How it stays honest

The prompt's honesty rules are enforced in code and pinned by tests, not left to the wording:

- Every post carries `paper (Tradier sandbox), since <date>` and the `thin` flag **taken from
  `paper_track._label`** — the same string `/api/track` serves. The recap cannot grade the
  track more generously than the product does.
- **No closed trades → "No closed trades yet".** An empty scorecard printed as `0% hit rate,
  $0 expectancy` is not neutral; it looks like a measured result. Test:
  `test_recap_says_no_closed_trades_rather_than_reporting_zeros`.
- **A hit RATE is only quoted once the sample can carry one.** Below the 30-trade floor it
  reads `1 of 1 won (too few to read as a rate)`. "hit rate 100%" off a single winner was the
  most flattering untrue number available and is now impossible.
- Options are always framed as **convex** — "the backtest hits 37% of the time, most trades
  lose a little and a few win big" — so the hit rate can never be read as a win rate.
- The backtest is quoted as a **reference point, not a target and not a promise**: +10.4%/trade
  full-sample and +4.4% in the recent half, both shown, so the fade is visible.
- Every post ends with "Educational only, not investment advice" and the sandbox/delayed-quote
  caveat.

## Two bugs I fixed in my own first version

1. **Discord truncates at 1900 characters — from the END, where every caveat lives.** A busy
   day with six closed trades would have silently dropped "educational only, not investment
   advice" off the bottom. `_fit()` now trims the per-trade DETAIL lines instead, oldest first,
   leaves a visible "…detail trimmed" marker, and never touches the last lines. Pinned by
   `test_fit_drops_detail_not_caveats_and_says_that_it_did`.
2. **The health line cried wolf on a new track.** It counts recorded sessions against trading
   days in the window; a track that started yesterday reported "1/5 sessions" and warned about
   a hole every day of its first week. It now only counts sessions on or after inception. A
   watchdog that is wrong exactly when you are watching it teaches you to ignore it.

## It reads; it does not recompute

`recap.py` derives no P&L, expectancy or return of its own. It reads
`options_tracker.scorecard`, the `pnl_pct`/`pnl_dollars` that `record_outcome` already stored,
and `paper_track.index_summary`. `test_recap_prints_the_tracked_pnl_rather_than_recomputing_it`
writes a deliberately odd P&L straight into the table and asserts the post shows *that* number
— so a future divergence between the Discord post and the API fails the suite instead of
shipping. The one exception is documented: a trade closed with no entry premium is unscoreable,
so the recap falls back to the stored premiums rather than dropping the trade from the book.

## Idempotency

`post()` marks the day in the same `alerts_sent` table the scream-buy de-dupe uses, keyed
`__RECAP_DAILY__` / `__RECAP_WEEKLY__`. The two DST crons, the Render cron and any manual re-run
therefore produce exactly one post per kind per day. **A failed post is deliberately NOT
marked**, so a Discord outage at 20:58 is retried by the 21:58 cron rather than burning the
day's only slot on a message nobody received.

## Changed

- **NEW `valuation/saas/recap.py`** — collect / format / post, with the honesty rules in the
  module docstring.
- `valuation/saas/app_saas.py` — new `/admin/post-recap` (X-Admin-Token, validates `kind`,
  applies the market-session guard, returns 200 with a reason on every non-post path).
- `.github/workflows/auto-scan.yml` — four crons + the `recap` job + two dispatch options.
- `render.yaml` — `DISCORD_WEBHOOK_URL` declared on the web service; two recap crons.
- `ENV_REFERENCE.md` — says explicitly that the webhook must be on Render, and why.
- Tests: `tests/test_paper_track.py` 22 → **34**, `tests/test_saas.py` 27 → **28**.

## Verified

All seven suites green: **edge 142, screener 51, saas 28, intraday 18, engine 28, bulk 14,
paper-track 34.**

Beyond the unit tests I ran the real Flask route against the real screener database with a
local HTTP sink standing in for Discord: `POST /admin/post-recap` returned
`{"posted": true, "chars": 621}`, the sink received exactly one payload ending in the
disclaimer, and an immediate second POST returned `{"posted": false, "duplicate": true}`
without sending anything. I also eyeballed both posts rendered against a synthetic book with a
winning trade, an open position and two index sessions. The de-dupe row that run left in the
local dev DB has been deleted.

## Honest limits

- **The recaps will say "not started" until the paper track has actually run on Render.** The
  local database has no paper book, and production still needs `TRADIER_PAPER_TOKEN` /
  `TRADIER_PAPER_ACCOUNT_ID` confirmed (Session 6's open item). The recap infrastructure is
  correct and tested either way, but the first real post is gated on that.
- The options scorecard it quotes is `options_tracker.scorecard`, which counts **every** closed
  alert — including any the external Cowork/Robinhood filler closes, not only paper ones. That
  is the existing project-wide definition and `/api/track` already reports it that way; I did
  not fork a second definition just for Discord.
- Index holdings only ever get **added** (`seed_book` never drops a name), so "holdings changes"
  means additions. The post says "added today" rather than implying rotation.

---

# Session 6 — 2026-08-03 — Paper schedule confirmed + the landing now SHOWS (PROMPT_appfixer_landing.md)

## 1. Is the paper track actually scheduled? YES — here is exactly where

| where | when (UTC) | what it does |
|---|---|---|
| `.github/workflows/auto-scan.yml`, job `paper` | `47 20` **and** `47 21`, Mon–Fri | POSTs `/admin/run-paper-track` with `X-Admin-Token` |
| `render.yaml`, cron `paper-track` | `45 21`, Mon–Fri | same endpoint, same token |

Both are on `main`, which is what matters — GitHub only registers cron schedules from the
default branch. Two Actions crons because a crontab cannot express "4pm Eastern": one is
correct under EDT, the other under EST, and the endpoint's session guard turns the early one
into a no-op. The endpoint is deployed and token-gated in production right now (an
unauthenticated POST returns **401**).

**What I still cannot verify from here, and it is the one remaining risk:** whether Render
actually holds `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID`. `ADMIN_TOKEN` is not in the
local `.env`, so I cannot call the production admin route, and the endpoint fails closed — a
401 looks identical whether the token is wrong or the paper creds are missing. The local creds
authenticate fine (sandbox account VA35863695).

**One-click check for Don:** Actions → "Auto scans" → Run workflow → kind `paper`, `force`
true. The step now **fails loudly** with an explicit message if the Render credentials are
missing, instead of treating any 200 as success.

**New this session — the watchdog now covers the paper track too.** `scripts/check_staleness.py`
also reads `/api/index-track` and alerts if the track has stopped recording points. It
deliberately stays quiet before the first point (`available: false` is the correct state today,
and alerting on it would train the reader to ignore the channel — which is how the July outage
went unnoticed for four days). Verified against production just now:

```
  hot list: 2026-07-29 (2 trading days old), 154 scored
  paper track: not started yet (no live points) — not an alert
🔴 Valquo data pipeline problem
• the last scan only scored 154 names — the universe has collapsed
```

That hot-list line is last session's outage, still unfixed in production because the first
scheduled run under the fix had not happened yet — **Monday 2026-08-03 22:23 UTC is the test.**

## 2. The landing page now shows the product instead of describing it

Everything is **server-rendered from the store** (`valuation/web/showcase.py`), so the page
paints in one pass with no client fetch and no empty-then-populated flash on the first thing a
visitor ever sees.

**A real sample valuation in the hero.** Not a mock-up — a genuine run of the real engine on
real filings, stamped with the date it ran. Today's AAPL sample renders:

> **$308.91 → $119.65   −61.3%** · Opportunity score **51/100 · Hold · high confidence**
> Bear $99 · base $120 · bull $145, with today's price pinned past the end of the bar and
> labelled *"Today's price is above even the bull case."*
> *"To justify $308.91 you have to believe revenue compounds at **40% a year**. The model's
> base case is **6%**. That is the question, not the price."*

That the flagship demo says a mega-cap is 61% overvalued is the point — it shows the tool will
tell you something you did not want to hear.

**Why it is cached rather than computed per visit:** a full valuation is a multi-second,
network-heavy job. Running it inside the landing request would make every first-time visitor
wait, on the box least able to afford it — the exact opposite of demonstrating the product in
two seconds. CI already has the RAM and the network, so `ci_scan.py` computes it after each hot
scan and POSTs it to the new token-gated `/admin/ingest-sample`. That refresh is **non-fatal**:
the ranking is the product, a stale hero is cosmetic, and failing the job over it would turn a
cosmetic miss into a red run and a Discord alert that teaches people to ignore alerts.

**The forward track is a hero element, directly under the fold.** An inline SVG of Index vs S&P
500 on a **shared** y-axis (drawing each line to its own scale would make a line that lost look
like it won). Inline SVG rather than a chart library because the page must paint immediately
and the site's CSP blocks external scripts anyway.

The honesty rules are enforced by the same `index_track.summarize()` the Index tab uses, so the
landing can never disagree with the page it links to:
- Under 60 trading days it is badged **`paper · thin`** and says *"Far too short to mean
  anything yet — shown because hiding it until it looks good is how track records lie."*
- Past that it becomes **`paper · live`** and the caveat drops. Verified both states in a
  browser by seeding a 70-day series, then restoring the real data.
- With **no live points at all** — today's real state — it shows `not started`, states plainly
  that there is no live curve, and labels the backtested figures as *"a different and weaker
  kind of evidence"*. It never draws a backtested curve under a "live" heading.

**Copy tightened** from a paragraph to three scannable value-props. The beta banner,
"educational only, not investment advice", the footer disclaimer and the per-card "a model
output — an estimate, not a price target or advice" all stay.

**Fixed a pre-existing mobile bug while I was in there.** The three value-prop cards were a
hard-coded `repeat(3,1fr)` grid with no breakpoint, so at 390px the page ran **493px wide** and
each card became roughly one word per line. Now single-column below 860px; verified
`scrollWidth == 390`.

Verified by running the app and driving it in Chromium at 1280px and 390px — no console errors,
no horizontal overflow, screenshots read at both sizes and in both track states.

## Changed

- **NEW `valuation/web/showcase.py`** — cached sample, `range_bar()`, `sparkline()`,
  `landing_context()`. Every block independently optional.
- `valuation/web/templates/landing.html` — rebuilt.
- `valuation/saas/app_saas.py` — landing route passes the showcase context (and **logs** rather
  than silently swallowing a failure); new `/admin/ingest-sample`.
- `scripts/ci_scan.py` — refreshes the landing sample after the hot scan, non-fatally.
- `scripts/check_staleness.py` — watches the paper track.
- Tests: screener 47 → 50, saas 24 → 27.

## Caveats

- The sample is only as fresh as the last successful hot scan — and the hot scan has been down
  since 07-29. Until Monday's run lands there will be **no sample on production** and the
  landing falls back to the static value-props. That fallback is tested, but it means the new
  hero will not appear until the scan recovers.
- `SAMPLE_TICKER` env var overrides AAPL if you ever want a different demo name.
- The sample carries an `as_of` date and is labelled "not refreshed since" past 7 days rather
  than hidden — an old real valuation beats an empty hero, but it must not read as live.
- I did not touch the paper-track lane's files, the options backtest, the panel or the miner.

---

# Session 5 — 2026-08-02 — Paper track verified + scheduled server-side (PROMPT_appfixer_paper_schedule.md)

## READ THIS FIRST: the hot scan has been dead since 2026-07-29, and it is not the paper track

The live site is serving a **four-day-old hot list**. Verified against production just now:

| feed | as of | state |
|---|---|---|
| `/api/hotstocks` | **2026-07-29** | **stale (3 trading days), 154 scored, 191-name universe** |
| `/api/signals` (intraday) | 2026-07-31 | fresh — last run Fri 21:41, correct for a Sunday |
| `/api/index-track` | — | no live series yet (`available: false`) |

Intraday being **fresh** while hot is stale is the useful part: it rules out the boring
explanations. Actions minutes are not exhausted (intraday is the minute-hungry job and it is
running), the schedule is firing, Render is up, and the secrets exist.

**Diagnosis — the FMP lapse killed the hot scan on 07-30 and nothing announced it.** The
workflow was last edited 2026-07-25 and the last code change before today was 07-28, so on
07-30 and 07-31 the hot job ran *the same code that succeeded on 07-29* and failed. What
changed underneath it was FMP: session 2 established the subscription lapsed around 07-29
(FCX/ELV/MU are present in the 07-29 snapshot and 402 now). Under the **old** provider code a
402 made `get_metrics` return `None`, so every name was dropped, the scan produced zero rows,
and `/admin/ingest-snapshot` rejected the empty post with a 400. Red run, nothing ingested,
no notification. Intraday was untouched because it runs on Tradier, not FMP.

**It is already fixed — the fix just has not had a scheduled run yet.** Session 2's free-stack
fallback + circuit breaker and session 4's broker fundamentals both landed on main *today*
(16:30 and later). The first hot run under the fix is **Monday 2026-08-03, 22:23 UTC**. If
`/api/hotstocks` still says 07-29 on Tuesday morning, that hypothesis is wrong and the Actions
log is the next place to look — I could not read it from here (no `gh`, no GitHub token).

**One thing to actually do: set `DISCORD_WEBHOOK_URL` as an Actions secret.** The watchdog and
the scan-failure alert are both wired and both inert without it. A four-day outage that only
manifests as a red run in a tab nobody opens is exactly what it exists to prevent — and this
is now the second time.

## 1. Sandbox connection — verified, output verbatim

```
$ python scripts/paper_track_run.py --health
Tradier SANDBOX https://sandbox.tradier.com/v1  account VA35863695  ok
  paper equity $199,256.75  cash $199,256.75
```

```
$ python scripts/paper_track_run.py --dry-run
Tradier SANDBOX https://sandbox.tradier.com/v1  account VA35863695  ok
  paper equity $199,256.75  cash $199,256.75
  DRY RUN — orders are previewed at the broker, nothing is placed.
Options: 0 submitted, 0 skipped, 0 rejected | 0 newly filled, 0 marked | 0 closed (0 written to the scorecard)
Index: 0 held, 0 added (quote-marked)
  no point written: no index holdings seeded yet
```

**That dry run proves almost nothing, and I did not stop there.** Every number is zero because
the local database is a test fixture — `option_alerts: 0 rows`, one snapshot row, scan date
`2099-01-01`, and a `data/valquo_index.json` whose only holding is a fake ticker `TESTX` that
cannot be quoted. A clean exit with no work done is not a working order path.

So I exercised the real path against the sandbox with real symbols and a throwaway database:

- **equity quotes** — AAPL 308.91, MSFT 464.72, SPY 747.03
- **option chain** — 466 contracts for AAPL, 233 calls with a two-sided market
- **option quote by OCC symbol** — `AAPL261016C00360000` bid 1.97 / ask 2.25
- **option order PREVIEW** — `status: ok, result: true, commission 0.35` (nothing placed)
- **equity order PREVIEW** — `status: ok, result: true, cost 1.00` (nothing placed)
- **index seed + mark** — 2 positions added, 2/2 priced, `index_point` ok against SPY

So the broker, the quote path, the order path and the index mark all work. The zeros were the
fixture, not the plumbing.

## 2. The schedule — and the DST bug I found in it

The paper job already existed (landed in `cde1579` by the paper-track lane): a GitHub Actions
job at `47 20 * * 1-5` and a Render cron at `45 20 * * 1-5`. **Both were wrong for half the
year.**

A crontab cannot express "4pm Eastern". `20:45 UTC` is 4:45pm ET under EDT — but under **EST
it is 3:45pm ET, fifteen minutes BEFORE the close.** From the first weekend in November the
cycle would have started running mid-session every weekday: entering option positions and
marking the index book against *intraday* prices instead of closing prices. Nothing would
error. Every run would have looked completely normal. And the one record whose entire value is
being a clean out-of-sample forward track would have quietly stopped meaning what it says.

Fixed in three places:

1. **NEW `valuation/screener/market_session.py`** — `session_state()` answers "has today's
   session actually closed?" in real Eastern time, including weekends and market holidays
   (holidays are **computed**, not listed, so this does not expire in a year — Good Friday via
   the Easter algorithm, the floating Mondays, and the weekend-observed rule). Verified
   against the published NYSE calendars for 2024 and 2025: **exact match, both years.** There
   is a 15-minute settle after the bell so a mark cannot catch a half-formed close.
2. **The endpoint guards itself** — `/admin/run-paper-track` returns `{"skipped": true,
   "session": {...}}` and does nothing if the session has not closed. This is the part that
   matters: the guard is unit-tested, a crontab is not.
3. **The crons fire generously and let the guard decide** — Actions now has **both**
   `47 20` and `47 21` UTC (one is correct in each DST regime, the other no-ops), and the
   Render cron moved `45 20` -> **`45 21` UTC**, which is after the close in *both* regimes
   (5:45pm EDT / 4:45pm EST) since there is only one entry there.

The workflow step now also distinguishes the three outcomes instead of treating any 200 as
success: a skip logs a notice, `configured: false` **fails the job loudly**, and a real run
says so. A skip every single day would mean the guard never opens, and that must not read
green. `workflow_dispatch` gained a `force` input so the job can be tested outside the window.

Double-running is safe by construction and always was — claim rows are `INSERT OR IGNORE` on
the alert id, and the day's index point is keyed by date.

## 3. What runs server-side (and what does not)

**Server-side, no laptop involved** — GitHub Actions (`auto-scan.yml`), all triggering
token-protected endpoints on Render:

| job | schedule (UTC) | status |
|---|---|---|
| hot list | `23 22` + `41 23` backup, weekdays | scheduled; **failing since 07-30**, fix landed today |
| intraday | `*/30 13-20`, weekdays | **working** — verified fresh 07-31 |
| paper track | `47 20` + `47 21`, weekdays | scheduled; endpoint live (401 without a token) |
| watchdog | `15 13`, weekdays | working; **inert without `DISCORD_WEBHOOK_URL`** |
| self-learning | `0 12 1 * *` monthly | scheduled |

`render.yaml` defines its own equivalent crons, but the Actions workflow is the live path
today (the blueprint's comment says to disable the workflow only once the paid blueprint is
in use). Both hitting the same idempotent endpoints is harmless.

**Still laptop-dependent:**
- **ThetaData miner** — expected and correct; it is a local gateway. Leave it.
- **The Sharadar backtest** (`fundamental_panel`) — licensed local data, run on demand. Not a
  live-product dependency.
- **`scripts/paper_track_run.py`** — the local path only. The scheduled path is the endpoint,
  deliberately: a CI runner gets an empty database and would lose the order state that makes
  the cycle idempotent.
- Nothing the live product serves depends on Don's machine being on.

## Secrets Don must set

| where | key | status |
|---|---|---|
| GitHub Actions | `DISCORD_WEBHOOK_URL` | **missing — please set.** Alerting is wired and inert without it |
| GitHub Actions | `SITE_BASE_URL`, `ADMIN_TOKEN` | already set (the scans reach Render) |
| Render env | `TRADIER_PAPER_TOKEN`, `TRADIER_PAPER_ACCOUNT_ID` | Don says set; **I could not verify from here** |

I could not confirm the Render paper credentials because `ADMIN_TOKEN` is not in the local
`.env`, so I cannot call the production admin endpoint. The local creds authenticate fine
(account VA35863695), but Render holds its own copy. **One-click check:** Actions -> "Auto
scans" -> Run workflow -> kind `paper`, `force` true. It fails loudly with an explicit message
if the Render credentials are missing, and otherwise runs one cycle.

## Changed

- **NEW `valuation/screener/market_session.py`** + 4 tests.
- `valuation/saas/app_saas.py` — session guard on `/admin/run-paper-track` (+ `force` escape).
- `.github/workflows/auto-scan.yml` — second paper cron, `force` dispatch input, outcome-aware
  step that fails on `configured: false`.
- `render.yaml` — paper cron `45 20` -> `45 21` UTC.
- Tests: screener 43 -> 47, saas 22 -> 24.

Did **not** touch `paper_track.py` / `paper_broker.py` (the paper lane's files), the options
backtest, the panel or the miner.

## Caveats

- The session guard uses `zoneinfo`, which needs system tzdata (present on Linux/Render and
  here). It falls back to naive UTC if unavailable, which would make it conservative in
  summer, not permissive.
- Holiday computation covers the ten scheduled NYSE closures. Ad-hoc closures (mourning,
  weather) are not predictable; the cost of a run on one is a single duplicate-priced mark.
- The paper track has **never completed a real scheduled run**. Everything above verifies the
  parts. The first end-to-end proof is Monday's cron.
- Sandbox quotes are delayed ~15 min (the broker's own `data_caveat`), so paper fills are
  close to, but not, what a live account would have received.

---

# Session 4 — 2026-08-02 — Broker fundamentals, the free route (PROMPT_broker_fundamentals.md)

## The verdict up front: NO, you do not need to pay for FMP

Tradier — which you already pay for — carries Morningstar fundamentals at
`beta/markets/fundamentals`, **100 symbols per call**. The whole 800-name universe now costs
about **24 calls** against a feed with no daily quota, versus FMP's ~2,400 metered per-name
calls. It covers market cap, enterprise value, the full valuation-ratio set, ROE, beta,
sector, and shares outstanding at **~99% of liquid names**.

What it does **not** carry is an income statement or a balance sheet. That is the honest
limit, and it is stated precisely in the gap table below.

**Recommendation: do not buy FMP Premium.** The one thing paid FMP would add that nothing free
covers is the growth theme, and there is a caveat on that below that matters more than the
price. If you ever do pay, the reason should be revenue growth, not "better data" generally.

## What is actually in the broker feed (measured, not assumed)

Measured on **200 liquid names, 2026-08-02**. Tradier returns a large envelope in which most
tables are null; I counted per-field fill rates rather than trusting the shape:

| Field | Broker source | Coverage |
|---|---|---|
| market cap, enterprise value, shares outstanding | `share_class_profile` | 99% |
| book value/share, P/S | `valuation_ratios` | 99% / 98.5% |
| P/B, P/E, EV/EBITDA | `valuation_ratios` | 91.5% / 88% / 83.5% |
| ROE, ROA, debt/equity | `operation_ratios` | 89.5% / 95.5% / 87.5% |
| beta (36/48/60-month) | `alpha_beta` | 99% |
| sector | `historical_asset_classification` | 99% |
| EPS (3M/9M/12M) | `earning_reports` | 98.5% |
| 13F + insider ownership tallies | `ownership_summary` | 99% |

**Null for every symbol, at every tier we can reach:** `financial_statements_restate`,
`segmentation`, `earning_reports_restate`, `historical_returns`, `operation_ratios_restate`,
`earning_ratios_restate`, `trailing_returns`, `asset_classification`.

Several absolutes are **derived** rather than reported — `revenue = mktcap / P/S`,
`net income = mktcap / P/E`, `equity = BVPS x shares`, `EBITDA = EV / EV-EBITDA`,
`net debt = EV - mktcap`. These are arithmetic identities, not estimates, but they inherit the
ratio's month-end as-of date while market cap is same-day, so a fast-moving name's derived
revenue can be a few percent off the filed figure. A **reported** value from the free stack
always beats a derived one (`broker_fundamentals.merge`).

### The fields with NO free source anywhere — the real "would need paid data" list

`operating_income`, `gross_profit`, `fcf`, `interest_expense`, `op_margin`, `gross_margin`,
`fcf_yield`, `ebit_ev`, `roic`, `revenue_growth`.

These come only from the slow per-name free stack (yfinance/EDGAR). They feed **growth** and
about half of **quality**. Locally the free stack supplies them fine; from a cloud IP it is
rate-limited, and that is the real exposure.

## Coverage: before vs after (100 liquid names, same universe, cold cache)

| | Before | After (broker + free) | Broker ONLY |
|---|---|---|---|
| Names scored | 99/100 | 99/100 | **97/100** |
| Wall clock | 244s | 230s / 189s (2 runs) | **15s / 16s** |
| growth theme coverage | **0.76** | **1.00** | 0.00 |
| quality / value / momentum / size | 1.00 | 1.00 | 0.94 / 1.00 / 1.00 / 1.00 |
| low_risk (beta) | 1.00 | 1.00 | 0.92 |

Be careful with the middle column's timing: the shipped path still makes the same slow
per-name free call, so **it is not meaningfully faster** — 244s vs 230s/189s is network noise
across three runs, not an improvement. The speed result is the third column.

The "Broker ONLY" column is the one that matters: I forced the free stack to fail outright,
simulating a throttled cloud IP. **97 of 100 names still scored, in 15 seconds instead of 230**
— with value, quality, momentum, size and low-risk intact and **growth gone**.

That is the resilience win, and it is the concrete answer to "what happens when Yahoo throttles
us". Before this change a failed per-name fetch returned nothing and the name was **dropped
from the scan entirely** ("no data"). Now the name survives on the broker's half. A throttled
Yahoo costs the scan some quality per name instead of costing it the name.

## Two bugs found and fixed on the way

**1. Enterprise value is `0` for banks — a "not applicable" sentinel, not a number.** Of 200
liquid names, 11 carry `ev == 0` and **all eleven are Financial Services** (JPM, BAC, WFC, GS,
MS, C, SCHW, AXP, COF, NU, SOFI); no other sector has one and none is negative. Taken
literally it sets `net_debt = -market_cap` (JPM: **-$935B**) and `ev_sales = 0` — i.e. it would
hand every large bank the cheapest possible EV/Sales in the universe and **peg the entire
sector to the top of the value theme**. Now treated as missing, so banks are ranked on earnings
yield / book / sales, which is how a bank should be valued anyway. Pinned by a test.

**2. The `insider` theme is inert in the live scan, and coverage was reporting it as 100%.**
No `insider_score` ever reaches `build_frame` in the live path (only the backtest panel and a
post-scan decoration set it), so the column is the constant `0.0`. A constant has zero
variance, `zscore()` returns all-NaN, and `composite_score` renormalizes its **12.5% weight
away**. But `theme_coverage` measures *presence*, so it read `insider: 1.0` — a dead theme
reported as perfectly healthy. This is the same class of bug as the five silently-empty factors
in CLAUDE.md.

I did **not** change the scoring. I added `theme_contributing` to the health block, which
measures each theme *after* standardization, and pointed the UI warning at it. Present and
usable are now separate numbers.

Measured live, only **4 of 9 themes actually drive the score**: value, quality, momentum, size.
`low_risk` is deliberately weighted 0; `insider`, `capital_discipline`, `sentiment` and
`institutional` are all inert. Worth knowing before reading any live ranking.

## What I did NOT wire, on purpose

The broker carries **13F and insider ownership at 99% coverage** — holder counts, shares
bought/sold, insider buys/sells. That is exactly the input the `institutional` theme
(12.5% weight, currently empty live) and the `insider` theme want, and it is tempting.

I left it unwired because **populating an empty theme changes every ranking**: `composite_score`
renormalizes over whichever themes are present, so a name that was scored on 4 themes would
suddenly be scored on 5 or 6. CLAUDE.md's rule is that a theme change has to clear
`holdout_theme_validate()` first, and I cannot run that here — this is a live-only snapshot
feed with no history, and Morningstar's aggregate 13F summary is a different construction from
the point-in-time Sharadar SF3 data the backtest validated. Wiring it would be an unvalidated
scoring change dressed as a data fix.

**This is the highest-value follow-up and it is Don's call, not mine.** Fields are
`ownership_summary.{13_f_holder_number, 13_f_shares_bought, 13_f_shares_sold, 13_f_shares_held,
insider_shares_bought, insider_shares_sold, number_of_insider_buys, number_of_insider_sellers}`.

## Changed

- **NEW `valuation/screener/broker_fundamentals.py`** — batched fetch, the field map, the
  sector-code map, `merge()` (reported beats derived) and `coverage()`.
- `providers.py` — `FreeProvider.prefetch()` bulk-loads the universe; `get_metrics` merges
  broker + free and no longer drops a name when the free fetch fails. `FMPProvider` delegates
  prefetch to the free stack behind it (on the current FMP tier the fallback IS the hot path).
  Added `METRICS_SCHEMA`, so cache rows written before the merge are discarded rather than
  served — a stale row missing `sector` is indistinguishable from a name that has none.
- `screen.py` — calls `prefetch()` when the provider supports it (optional by contract);
  ships a `fundamentals` health block (per-field fill rates, per-source counts) and
  `theme_contributing`; carries `extra.source` per name.
- `app.js` — per-name `p` marker for broker-only rows, a fundamentals-source line, and the
  theme warning now reads `theme_contributing`.
- `tests/test_screener.py` — 32 -> 43 tests.

Morningstar's 11 sector codes map **exactly** onto the sector names `engine/comps` already
uses, so a broker sector lands straight in the fair-value peer medians instead of falling
through to the generic default. A test pins that — a near-miss like "Financials" would fail
silently.

## Two operational notes

**The next scan will be slow, once.** `METRICS_SCHEMA` went 1 -> 2, so every cached
fundamentals row is discarded and refetched. The Actions `.scan-cache` is effectively empty
for one run: at ~2.3s/name and `SCAN_LIMIT=800` that is roughly 30 minutes against a
`timeout-minutes: 60` budget. It should fit, but if that run goes red on a timeout this is
why, and it is self-correcting on the following run.

**There is a fast mode available and I did not switch it on.** Skipping the per-name free
fetch entirely gives a full scan in ~15s instead of ~230s, at the cost of the growth theme and
part of quality. I did not add a flag for it because nothing needs it today, but if the
scheduled scan ever starts timing out or Yahoo throttling gets worse, that is the lever — and
the measured trade-off is in the table above rather than a guess.

## Caveats — do not drop these

- Coverage is measured on **200 liquid large caps**. Thinner names will have worse ratio
  coverage; the 83.5% EV/EBITDA figure is the weakest link and will be lower down-cap.
- The derived absolutes carry the ratio's month-end as-of date, not today's filing.
- I could not test the throttled-cloud-IP case for real — I simulated it by forcing the free
  fetch to raise. The 97/100 survival number is from that simulation, not from production.
- The broker feed is a **snapshot**, not point-in-time. It is fine for live ranking and must
  never be fed to the backtest panel.

---

# Session 3 — 2026-08-02 — Index tab, dynamic alpha, trust enablers (PROMPT_appfixes_index.md)

## Shipped — all five items, including the "if time" one

**1. The Valquo Index has its own tab.** Moved out of the bottom of Hot Stocks (Hot Stocks now
links across to it). The tab carries: a cumulative Index-vs-SPY chart, the backtested-vs-live
performance pair, the sector-diversification view, and the full holdings table with Company /
Sector / Weight / Market cap / Hot score populated. Verified by actually running the app and
driving it in a browser — screenshots of both the long-track and the real 1-day state.

**2. Dynamic net alpha — backtested and live, side by side, never blended.** Two cards. The
server decides which one may be the headline; the UI never picks based on which number looks
better. Rules encoded in `valuation/screener/index_track.py`:
- Live cannot be the headline until **60 trading days** (`MIN_LIVE_DAYS`). Before that the
  card is badged `thin — Nd` and the backtest keeps the border.
- **Annualised alpha and Sharpe are withheld** (served as `null`, rendered "—" with the
  reason) until there is enough history. Compounding 1 day of drift into a yearly rate
  manufactures a number nobody should believe. Cumulative-since-inception *is* shown from
  day one, because that one is honest at any length.
- Sharpe is also suppressed above **6.0**. A near-constant excess series drives the
  denominator to zero; I hit exactly this in testing and got "Sharpe 444", which on a live
  page would discredit every other number on it.
- Right now the real state is **1 day (2026-07-31): Index +0.41% vs SPY +0.69%, −0.28pp**.
  Thin, shown, not the headline. That is the correct display, not a bug.

**3. Trust enablers.**
- **Staleness stamp** (`valuation/screener/freshness.py`) on the Index, Hot Stocks and
  Signals. Age is in **trading days**, so a Friday scan read on Sunday is correctly "fresh" —
  crying wolf across a weekend is how staleness badges get ignored. 2 days warns, 3+ shows a
  red "the scheduled update has not run. Do not treat it as current."
- **Risk disclaimer** as one shared string (`RISK_DISCLAIMER` in `web/app.py`) served with
  the Index and Signals payloads, so the wording cannot drift between surfaces.
- **`/methodology`** — point-in-time, survivorship, the 236bps-breakeven cost framing, CPCV /
  PBO / Deflated Sharpe, held-out confirmation, full-universe-only. Plus a "where it is weak"
  section that keeps the uncomfortable parts: one 18-year dataset the model was tuned on, a
  saturated Deflated Sharpe, dormant themes, and the degraded data feed. A test asserts those
  weaknesses stay on the page, so it cannot quietly become marketing. Linked from both
  footers and from the Index and Signals tabs.

**4. Scan-failure alerting.** Two layers:
- `scripts/ci_scan.py` posts to Discord if the scan crashes or exits non-zero.
- `scripts/check_staleness.py` — a **separate** `watchdog` job on its own cron (13:15 UTC
  weekdays, before the open). It runs separately on purpose: a check bolted onto the end of
  the scan cannot fire when the scan is the thing that died, which is exactly the July
  failure. It hits the public API from outside, and alerts on a stale scan **or a collapsed
  universe**. Exits non-zero so the Actions run goes red too.
  Run against the live site right now it already fires: *"the last scan only scored **154**
  names — the universe has collapsed"*.

**5. Mobile pass** (the "if time" item). Index tab verified at 390px: no horizontal page
overflow, stat rows and sector labels scaled down, wide tables scroll inside their own box
rather than the page.

## What Don needs to do

1. **Add `DISCORD_WEBHOOK_URL` as a GitHub Actions secret.** Everything in item 4 is wired and
   inert without it — the alerts fall back to "red run in the Actions tab", which is precisely
   what nobody noticed for four days in July.
2. **Point the Cowork tracker at the new ingest endpoint.** `data/` is gitignored, so the
   tracker's files never reach Render and the live column would be permanently empty in
   production while working fine on your laptop. `POST /admin/ingest-index-track` with
   `X-Admin-Token`, body `{"inception_date", "benchmark", "series": [{"date","valquo","spy"}]}`
   — percentages cumulative-since-inception, exactly as `valquo_track_history.csv` holds them.
   → **This is a Cowork-side task.**
3. The 60-trading-day promotion threshold is a judgement call, not a measured one. It is one
   constant (`index_track.MIN_LIVE_DAYS`) if you want it longer.

## Nothing slipped

All five items shipped. The prompt allowed item 5 to be dropped; it wasn't needed.

## Tests

Six suites green: **edge 119/119, screener 32/32 (+5), saas 22/22 (+2), intraday 18/18,
engine 28/28, bulk 14/14.**

New tests worth knowing: `test_live_track_never_annualizes_a_stub_or_leads_with_it` (5 days
must never lead and must never be annualised; 65 days must),
`test_live_track_suppresses_an_implausible_sharpe`,
`test_freshness_counts_trading_days_not_calendar_days` (pins the weekend behaviour and the
real 07-29 case), `test_methodology_page_is_public_and_states_the_weaknesses`,
`test_index_track_ingest_requires_the_admin_token`.

---

# Session 2 — 2026-08-02 — the live universe (PROMPT_appfixes_universe.md)

## Headline

**Universe: 191 names / 154 scored → 800 names / 794 scored**, sourced from a 7,113-name
broker-enumerated pool ranked by liquidity. The Index goes from a decile of 77 eligible names
to a decile of **668**. Verified end to end locally.

The `company-screener` failure is diagnosed and worked around, but the diagnosis is worse than
the prompt assumed and you have a decision to make. Read "The FMP problem" before anything
else. Also note the security item (6) — an API key was one commit away from being public.

## Step 1 — verification: the FMP key did NOT fix it

The live site is still serving the **2026-07-29** scan: 191 universe / 154 scored. There has
been **no successful scan since 07-29** — four days. So the re-run either did not fire or did
not land, and I could not verify from the site. I diagnosed against the live key directly.

## The FMP problem — it is not the screener endpoint, it is the whole subscription

Verified 2026-08-02 against the real key. Two separate restrictions:

**1. Every bulk/list endpoint is 402 Restricted.** Not a parameter problem — I tried the call
with and without `exchange`, `country`, `isActivelyTrading`, and at `limit=10`. All 402.

| endpoint | result |
|---|---|
| `company-screener` | 402 Restricted |
| `stock-list` | 402 Restricted |
| `sp500-constituent` / `nasdaq-constituent` / `dowjones-constituent` | 402 Restricted |
| `available-exchanges`, `batch-quote-short` | 402 Restricted |
| `profile`, `quote`, `key-metrics-ttm`, `ratios-ttm` | 200 OK |

**2. Worse — the per-symbol endpoints serve only an ALLOWLIST.** I sampled 30 names spread
across the liquidity ranking and asked for `key-metrics-ttm`: **29 of 30 came back 402**, with
a symbol-level message — *"Premium Query Parameter: 'Special Endpoint : This value set for
'symbol' is not available under your current subscription"*. Blocked names include FCX, NSC,
ELV, PRU, CLX, WDAY, TDG, HAS. AAPL/NVDA/AMD/GE/AMZN/CSCO still work.

**This is a change, not a long-standing state.** FCX, ELV and MU are all present in the live
07-29 snapshot — FMP served them four days ago and refuses them today. That points at the
subscription lapsing or being downgraded around 2026-07-29, which is also exactly when the
daily scans stopped appearing. **Worth checking your FMP account first — this may be a billing
problem rather than a code problem.**

So: no code change can restore FMP-sourced fundamentals for the large-cap tier. That is the
honest answer the prompt asked for.

## What I built anyway, so the product is not dead in the meantime

**1. Universe from the broker (Tradier) — the name-list fix the prompt asked for.**
New `valuation/screener/broker_universe.py`. Tradier has no bulk restriction and you already
pay for it:
- `markets/lookup`, 26 calls (one per letter) → **7,113 distinct NYSE/Nasdaq common stocks**
  with company names, in ~9s.
- `markets/quotes`, batched 200 at a time → last price, average volume, 52-week high.
- Ranked by **average dollar volume** and cut to a limit. The broker does not publish market
  cap; liquidity is what actually decides tradeability and is a tight proxy for size. Market
  cap still comes from the fundamentals feed per name, so the large-cap gate is unchanged.
- Whole universe costs ~50 free calls and ~4s. ETFs excluded; sub-$1 and illiquid names
  dropped; class shares normalised (`BRK/B` → `BRK-B`, which otherwise fail every downstream
  lookup — that quietly dropped some of the largest companies in the market).

**2. Fixed the actual code bug that capped the universe at 191.** `FMPProvider`'s fallback
hardcoded `"bundled"` regardless of the scope requested. So a `whole_market` scan silently
became a 191-name scan the moment the screener 402'd. It now falls back **for the scope that
was asked for**, through broker → EDGAR → bundled.

**3. Per-symbol fallback to the free stack.** When FMP refuses a symbol, that name is served
by the existing yfinance/EDGAR path instead of being dropped. A circuit breaker stops asking
FMP after 12 consecutive failures, so a refusing subscription costs 36 wasted requests per
scan rather than 2,400. The per-source split ships in the health block — a book built from two
fundamentals feeds should never be a silent fact.

**4. FMP spend ceiling.** `FMP_MAX_CALLS` bounds requests per scan. It caps what we *spend*,
not what we *rank*: names past the budget go to the free path.

**5. Persistent scan cache in CI.** `ci_scan.py` now writes to `.scan-cache/screener.db` and
the workflow restores it with `actions/cache`. Without this every CI run started from a cold
cache and re-paid for every name. With it, a run only pays for entries past the 30-day TTL.

**6. SECURITY — an API key was about to be published.** `requests` puts the full request URL,
query string included, in its `HTTPError` text. My first version of the universe note stored
that verbatim, and the health block is served publicly by `/api/hotstocks` — so the live FMP
key would have been on the open internet. Everything reaching that block now goes through
`_redact()`. Pinned by `test_api_keys_never_reach_the_health_block`. **If you want to be
careful, rotate the FMP key** — it was never actually deployed, but it was one commit away.

## Measured results

Local end-to-end runs (temp DB, live site untouched):

Local end-to-end runs (temp DB, live site untouched):

| run | universe | scored | notes |
|---|---|---|---|
| **before** (live, 07-29) | **191** | **154** | bundled fallback |
| 250-name broker universe | 250 | 247 | 6 via FMP, 244 via free fallback |
| **after** — 800-name broker universe | **800** | **794** | the configured production size, 22 min |

The 800-name run in full: 99.3% scored; display coverage name 99.9% / sector 99.9% /
market cap 100%; only 6 names dropped (3 no market cap, 2 nano-cap, 1 illiquid). Theme
coverage value/quality/momentum/low_risk/size 1.00, growth 0.98. Index:

> `tilt: large-cap only` · **668 eligible** · **67 positions** · **10 sectors**
> (Financials 30.8%, Healthcare 23.1%, Technology 19.4%, Energy 10.9%, …)

Compare the old book: 77 eligible, 25 positions, 5 sectors. **This is a genuinely different
book** — a decile of 668 large caps rather than a decile of 154 mostly-mega-caps, so the
holdings will look unfamiliar (NLY, ARWR, APGE, QXO, SYF at $10–25B rather than DELL/BA/AMD).
That is the intended consequence of ranking the actual tier, but eyeball the first live one.

Throughput ~1.6s/name on a cold cache. The workflow's `timeout-minutes` went 30 → 60 and
`SCAN_LIMIT` 1500 → **800** to fit that honestly. With `actions/cache` warm it will be far
quicker, and 800 can be raised.

Note the 800-name run served **0 names via FMP** — by then my diagnostics had tripped FMP's
**429 rate limit**, the circuit breaker fired, and the free stack carried all 800. That is the
degraded mode working exactly as designed, and it is also a preview of what every scan looks
like until the subscription is sorted.

## The decision you need to make

**Option A — fix the FMP subscription (~$22/mo Starter).** Restores `company-screener` (one
call for the whole market with sector and market cap) and, more importantly, per-symbol access
to the whole universe. Cleanest, and the code already prefers FMP whenever it answers.

**Option B — stay on the free stack.** It works: the 250-name run scored 98.8% of names with
essentially no FMP. But it is yfinance, so it is slower (~25 min for 800), rate-limited from
cloud IPs, and occasionally returns nothing for a name.

My recommendation: **check whether the FMP plan lapsed first** — if this is an expired card
rather than a deliberate downgrade, that is the whole fix. The code works either way.

## Not done (step 3)

The Index-in-its-own-tab with a cumulative-vs-S&P chart, and dynamic net alpha, were step 3
"only if there's time". Step 2 took the session. Left for next time.

## Tests

All six suites green: **edge 91/91, screener 24/24 (+5), saas 20/20, intraday 18/18,
engine 19/19, bulk 14/14.**

New: `test_api_keys_never_reach_the_health_block`,
`test_fmp_universe_falls_back_for_the_scope_that_was_asked_for`,
`test_fmp_budget_and_circuit_breaker_fall_back_instead_of_dropping_names`,
`test_broker_universe_normalizes_class_share_symbols`,
`test_broker_universe_ranks_by_liquidity_and_drops_junk`.

## One cost I incurred

Diagnosing this spent roughly 400–500 FMP requests off your daily allowance (endpoint probes,
a 30-symbol allowlist sample, and end-to-end scans) — enough that FMP was returning **429 Too
Many Requests** by the end. If tonight's scan looks quota-thin, that is why; it resets daily,
and the circuit breaker means the scan still completes off the free stack either way.

To be precise about the allowlist evidence, since the 429s came later and could muddy it: at a
single moment, with the same key and no rate limiting in play, `AAPL` returned **200** while
`FCX` and `NSC` returned **402** with a *symbol-scoped* message. A rate limit does not
discriminate by symbol. The allowlist is real and separate from the quota.

---

# Session 1 — 2026-08-02 — display fixes (PROMPT_app_fixes.md)

Landed on `main` as b459d9a. Summary retained for continuity:

- **$0.00 market caps were a unit bug.** `CompanyData` carries millions, FMP's profile carries
  dollars, both fed the same scan; the UI renders `market_cap/1e9`. The screener's metrics
  contract is now USD dollars everywhere, stamped with `units` so a millions-era cache entry is
  discarded. Ratios computed before scaling, so `earnings_yield`/`pe`/`ps`/margins are unchanged.
  Fell out of it: `prefilter`'s nano-cap floor was comparing dollars against `50`, and the Index
  had silently degraded to "largest half" because nothing cleared the $10B floor.
- **Company names** were present in the data but absent from the UI — the Index table had no
  Company column. Added there and in the portfolio table.
- **Sectors + a diversification view**: new `screener/profiles.py` resolves name/sector from the
  live feed (store → SEC filer list → bundled map → FMP profile, capped); `valquo_index.export()`
  decorates the finished book; new sector-weight breakdown above the Index table with sector
  count, largest sector and effective sectors.
- **Formatting**: one `mcap()` ($B/$T/$M, 2dp) everywhere; removed two local `pct`/`num` shadows;
  added `spct()` and `esc()`.
- Scan health gained `display_coverage` and a recorded reason for universe fallbacks.
