# REBALANCE RUNBOOK — 2027-01-25

**For Don.** One path, five commands, no workarounds. This replaces
`REBALANCE_RUNBOOK_2026-10-22.md`, which is kept as the record of what that night needed.

**NOTHING HERE HAS BEEN RUN.** No book is built, nothing is appended, the bound record is
untouched. This is commands and gates.

**THE DATE IS DERIVED, NOT CHOSEN.** 63 trading days after **2026-10-22** — holidays included,
through the package's one calendar (`market_session`) — is **Monday 2027-01-25**, which is also
what the recorded event's own `next_rebalance` field says. Check it rather than trust this file:

```
python -c "from valuation.screener.index_in_force import next_rebalance; print(next_rebalance('2026-10-22'))"
```

---

## 0. THE ONE THING THAT NEEDS A DECISION, AND IT NEEDS IT BEFORE JANUARY

**SHARADAR ACCESS ENDS AROUND 2026-11-03.** It was renewed on 2026-10-04 for one month. From
early November the pull in step 1 fails with an authorisation error — which is correct behaviour,
not a bug — and nothing in this runbook past step 1 can run on fresh data.

**SO A 2027-01-25 REBALANCE NEEDS SHARADAR RENEWED BEFORE IT, AND THAT IS A PURCHASE. IT IS
DON'S DECISION AND NOBODY ELSE'S.** It is not a technical blocker to be worked around on the
night: without a current export the market caps and fundamentals the book is ranked on would be
three months old, and §2's refusal will stop the build rather than let that through.

What the frozen data under `data\backtest_freeze_*` can and cannot do, so the decision is made
on facts rather than on hope:

| | with Sharadar renewed | without it |
|---|---|---|
| research and backtests | unchanged | **unchanged** — the freezes are permanent and nothing needs re-pulling |
| a **2027-01-25 rebalance** | runs, as below | **cannot be built honestly.** The newest close on disk would be 2026-10-23, three months stale |
| the forward record | continues | the book in force stays in force, unrebalanced, and that should be logged as a delay with its reason rather than left to read as a book that silently stopped |

**There is no third option.** Building the January book on October data and dating it January is
the one thing this runbook exists to prevent, and §2 refuses it in code.

---

## 1. THE REFRESH — A DOUBLE-CLICK, AND IT NOW REFRESHES THE CACHES TOO

**Run `refresh_sharadar.bat` on the evening of Monday 2027-01-25**, after the close has
published, from the `valuation-tool` folder. Double-click it; nothing to type. Roughly 20–40
minutes.

It ends with **one line**:

* `SUCCESS: data\backtest now holds the latest close.` → go to step 2.
* anything starting `FAILURE:` → **stop.** The line says which of four things happened. None of
  them should be worked around by hand on the night of a rebalance; that is what cost the
  October night.

**WHAT CHANGED SINCE OCTOBER, AND IT IS THE REASON THIS RUNBOOK EXISTS.** The build reads two
different things: the per-ticker export in `data\backtest`, which this script refreshed, and the
prepared **bulk caches** — point-in-time market cap and 13F — which it did not. Those caches had
not moved since **July**, so the October build was about to rank the universe on **three-month-old
market caps**, which is the single number that decides which names clear the $10 billion floor.

It was caught by hand on the night and patched by hand on the night. Three separate faults are
now fixed, and each of them would have been enough on its own:

1. **The caches were never refreshed at all.** The script updated `data\backtest` and nothing
   ever rebuilt `data\bulk\prepared`. Those July caches must NOT be rebuilt in place — every
   banked research figure on this project is pinned to them — so the fresh ones live in the
   dated freeze folder the pull already writes, and the build is pointed at them (step 2).
2. **A second refresh in the same month silently kept the first one's caches.** Measured the
   morning after: in `data\backtest_freeze_2026-10`, every downloaded file was stamped
   **2026-10-23** and every prepared cache **2026-10-04**, because the preparation step reuses a
   cache it finds rather than rebuilding it. So even the patched build scored its market caps
   from **2026-10-02**, twenty days behind the session it was labelled as. A cache whose source
   file is newer than itself is now rebuilt automatically, and the refresh prints the date the
   market caps reach.
3. **Month-end down-sampling threw the right day away.** The cache kept one row per
   ticker-month, so a fresh export taken on the evening of the 23rd made October's only row the
   23rd — *later* than an as-of of the 22nd — and the build fell back to **09-30**. The cache now
   also keeps each ticker's most recent five weeks of sessions, so an as-of lands on an exact
   row. It can only ever make an answer more precise.

**It never prints the API key.** The key is read from `.env` by the Python tool. If `.env` is
missing it says so immediately instead of failing twenty minutes into a download.

**Note the folder name.** The freeze folder is `data\backtest_freeze_YYYY-MM`, so a January pull
writes `data\backtest_freeze_2027-01`. Write that path down — step 2 needs it.

---

## 2. THE BUILD — ONE COMMAND, AND IT REFUSES RATHER THAN GUESSES

```
python -m valuation.edge.valquo_index --full-universe data/backtest ^
       --config taxable --as-of 2027-01-25 ^
       --bulk-overlay data/backtest_freeze_2027-01/bulk/prepared ^
       --out data/valquo_index.json
```

(One line in a `cmd` window; the `^` are line continuations. In PowerShell use a backtick.)

**EVERY ARGUMENT IS LOAD-BEARING. What each one is for, and what happens without it:**

| | why |
|---|---|
| `--full-universe data/backtest` | scores the export point-in-time instead of a live scan snapshot. Without it the "top decile" is a decile of whatever the last live scan happened to cover — about 0.23 overlap with this book on `D9`'s own measurement. |
| `--config taxable` | **the contract construction**: top decile of the large-cap tier, score-weighted, 8% cap, 30% no-trade band. `roth` is a 25-name preview and is **not** the contract book; building it fails the conformance gate, correctly. |
| `--as-of 2027-01-25` | the export will very likely carry a later close than the session being rebalanced. Without this the book is scored as of the export's newest close and appended as the event for the 25th — a look-ahead the event itself could never reveal. Honoured exactly or refused. |
| `--bulk-overlay …\bulk\prepared` | takes the market-cap and 13F caches from **January's** export instead of the pinned July ones. **This is the fix for the October night.** |
| `--out data/valquo_index.json` | the book in force. This is how the 30% band gets the previous book — `held` comes from whatever is at `--out`. Point it anywhere else and the rebalance is silently band-less, which turns the book over harder than the adopted rule does and looks like an ordinary rebalance everywhere. |

**`--limit` IS NO LONGER NEEDED AND THAT IS A CHANGE OF DEFAULT.** October's runbook carried
`--limit 4000` in bold, because the old default of 3,000 had quietly become a market-cap-ranked
*subset* of a 3,520-name export. The default is now **the whole export, unranked**. For the
record: the one-off script that built the recorded October book did not pass the flag, so the
book in force was scored on **1,835 names** rather than the export's ~2,038. That is not a
filter on the edges of the book — the composite is a cross-sectional z-score, so the number of
names scored moves the decile boundary, and item 75 measured nine of about eighty-five names
changing. **If you would rather keep the old behaviour, type `--limit 3000`; it still works and
still prints its own "SMOKE-TEST SUBSET, not a verdict" banner.**

### What the first lines of output must say

```
[cache] actions        not used  …\data\bulk\prepared (31,937 entries)
[cache] daily          USED      …\backtest_freeze_2027-01\bulk\prepared (…)
[cache] events         not used  …\data\bulk\prepared (17,779 entries)
[cache] sf3            USED      …\backtest_freeze_2027-01\bulk\prepared (…)
[cache] tickers        not used  …\data\bulk\prepared (48,925 entries)
[cache] market caps from …\backtest_freeze_2027-01\bulk\prepared, newest row 2027-01-25 (… tickers)
```

**READ THE LAST LINE. It is the number the October night got wrong three different ways.** It
must be the rebalance date or within a few sessions of it. If it reads a date from months back,
stop — the refresh did not take, and nothing further is worth running.

**`actions` AND `tickers` ARE DELIBERATELY NOT OVERLAID, and the reason is measured rather than
cautious.** A freeze carries five caches and `data\bulk\prepared` carries nine, so pointing the
whole directory at the freeze would silently empty four of them and every consumer would read
"no data" without raising. And of the five it does carry, `daily`, `sf3` and `events` all gain
names in a fresher export, while **`actions` is missing 1,181 names and `tickers` 5,234** —
overlaying those two would narrow the universe the book is drawn from, which is a construction
change wearing a data refresh's clothes. They are reported as *not used* on every build so the
omission is visible rather than silent. `--bulk-overlay-names daily,sf3,events` extends the set
deliberately if a later session decides to.

### If the build refuses

It is designed to. Every refusal names the remedy:

* **"the daily market-cap cache … ends 2026-07-29, which is 60 trading days before the requested
  as-of"** → the overlay is missing or pointing at the wrong folder. This is the October defect,
  and it now stops the build in about ten seconds instead of producing a book nobody could tell
  was wrong. The bar is **5 trading days**, about a calendar week.
* **"--bulk-overlay needs --full-universe"** → the live-scan path reads no bulk cache, so the
  flag would change nothing.
* **"--as-of … is not a date"** → a typo, caught in a second rather than after the load.
* **"holds no daily cache"** → the path is wrong, or the refresh did not get as far as preparing.

---

## 3. THE FRESHNESS GATE — READ THE PAYLOAD BEFORE APPENDING

The book's own payload carries it. Do not append unless, for `2027-01-25`:

* `freshness.as_of` == **2027-01-25** and `as_of_is_trading_day` is **true**
* `freshness.stale` is **false**
* `contract_conformance.conforms` is **true**
* `no_trade_band.applied` is **true** with a non-empty `band_retained`

```
python -c "import json;d=json.load(open('data/valquo_index.json'));print(d['data_as_of'],d['n_positions'],d['contract_conformance']['conforms'],d['no_trade_band']['applied'])"
```

The printed summary says the same things: `as of 2027-01-25`, `no-trade band 30%`, and the
position count.

**The door enforces the dangerous half of this independently**, so skipping the gate cannot let
a look-ahead through: `append_rebalance` refuses any book whose as-of is later than its event
date, and names `--as-of <event date>` as the remedy.

---

## 4. THE APPEND — DRY RUN FIRST, AND THE ORDER MATTERS

**The 2027-01-25 track row must exist before the event dated 2027-01-25 is appended.** The door
refuses an unanchored date — a rebalance dated on a day the track never marked — and that
refusal is the point: an anchor off by one session shifts every later row by a constant nobody
can find.

```
rem dry run -- without --send this sends nothing
python -m scripts.seed_track --rebalance data/valquo_index.json ^
       --rebalance-date 2027-01-25 --pull

rem then, once the dry run reads clean:
python -m scripts.seed_track --rebalance data/valquo_index.json ^
       --rebalance-date 2027-01-25 --pull --send
```

**THE DRY RUN IS NOT OPTIONAL AND IT EARNED THAT ON 2026-10-23**, where it caught both door
bugs before anything was written. It prints the kept/added/dropped counts and the conformance
verdict without touching the service.

`--pull` pulls the service's recorded series first and refuses to upload unless the local one is
a superset of it, cell for cell. **Re-sending the identical event is a no-op, not an error**, so
a retried command cannot corrupt anything.

Refused, by the library: a book that is not the contract-bound Index, a date on or before the
last event, a rewrite of an existing event, an unanchored date, or a date on or before
inception.

---

## 5. THE VINTAGE — NOT AN EVENT, AND CHECK IT RATHER THAN TRUST THIS FILE

`PAPER_TRACK_CONTRACT.md` §5a: *"any **ADOPTED** change to scoring, weights, or construction
closes the current vintage and opens the next … **Rebalancing under unchanged rules is NOT a
vintage event.**"*

This rebalance is **not a vintage event**: same vendor, same construction (decile of the
large-cap tier, score-weighted, 8% cap, 30% band), same flat weights. Nothing in this runbook
changes a scoring rule. **Two things that are not scoring changes and should not be mistaken for
them:** refreshing the caches to a current export, and the `--limit` default now meaning the
whole export — the first is data, the second is the universe the ranking is computed over.
Record the second in the notes for the quarter anyway, because it moves which names are in the
book even though it changes no rule.

Derive the live vintage; never quote one from a document:

```
python -c "from valuation.edge import track_meter as T;print(T.detail()['vintage'])"
```

---

## 6. WHAT THIS RUNBOOK DOES NOT DO

* **It builds no book** and appends nothing.
* **It does not renew Sharadar and does not spend money.** §0 is a decision for Don.
* **It does not decide the construction.** Arm 2 (`--candidate liquid-decile`) is still built
  and still switched off; adopting it IS a vintage event. See the October runbook §3b, which
  remains current on that question.
* **It does not re-run `D9`** and does not revisit the free live route. That route is a vintage
  event on §5a's own wording, independently of any fidelity measurement.
* **It does not change the recorded October book.** That book was scored on 2026-10-02 market
  caps and a 1,835-name universe; it is in force, it is recorded, and it is not re-derived here.
  The three defects behind those numbers are fixed for January.
