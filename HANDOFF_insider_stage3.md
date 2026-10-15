# HANDOFF — `INSIDER-STAGE3`: the older-data rung is **NOT REACHABLE on free data**, F-23 is declared and **cannot fill**, and `test_valreads.py`'s Windows-only failure is fixed

**Date:** 2026-10-14 · **Branch:** `worktree-r1-insider-stage3` · **Lane:** r1
**ZERO TRIALS.** No hypothesis, no bar against an outcome, no forward return loaded anywhere —
`FACTS` and `FIXED` class. **ADOPTS NOTHING.** No file under `valuation/` changed.
**Declaration:** `DECL_f23_insider_cluster_shares.md`, committed **ALONE at `5ad68c2`** (one file,
181 lines), `validate_declaration` **ok with zero refusals**, sha `e965d656`.

Inputs: `DECISIONS.md` 2026-10-14 *"CLUSTERED INSIDER BUYING GOES TO THE 1999-2008 CHECK AND A
PAPER BOOK"*; `RESEARCH_CHARTER.md` §5 Stage 3; `HANDOFF_insider_cluster_wide.md`.

---

## 1. THE OLDER-DATA RUNG — two corrections to the brief, and the rung is not reachable

### 1a. The gap, confirmed on the file that GOVERNS rather than the one the brief measured

The brief's counts come from `data/backtest/insiders.csv`. The construction reads
`insider_cluster.sf2_zip()` → the **freeze's** raw SF2, a different file (`INSIDER-CLUSTER`
measured `data/backtest`'s top-3,000-by-today's-cap selection costing **4.17×** the open-market
purchase rows). Re-measured on the governing file: **11,570,121 rows, 682,435 with code `P`,
3,404,501 with no code at all** (counted and skipped, never read as not-a-purchase).

**Filing dates run 2008-01-02 → 2026-10-02.** The brief's 2008 P-count is 32,794; the freeze's is
**108,320** — 3.3×, consistent with that selection cost. **The gap is confirmed.**

### 1b. **CORRECTION 1: the first emittable year is 2008, not "about 2010", and the reason is that two different date columns bind**

The brief reasons that the two-prior-year rule pushes the first usable event to ~2010. Measured in
the shipped source:

* an event is **dated at the LAST FILING**, so none can precede the first `filingdate` — **2008**;
* `prior_year_presence` keys on **`transactiondate`** years (`insider_cluster.py:178`), and
  **transaction dates reach back to 1988-08-08**.

So the answer is `max(first_filing_year, first_transaction_year + 2)` = **2008**, and **the
FILING floor binds, not the `+2` condition**. The `+2` itself is read off the shipped predicate
with a positive probe and a **gap** negative control, both passing. **One usable year inside the
charter's ten-year proxy window.**

### 1c. The events, and the power — **31 events, 6.3% power**

The frozen construction emits **31 events, ALL in 2008, over 15 tickers** (2008-01-04 →
2008-12-17). From the governing cell's own realised clustered `se`, scaled to `n` = 31 and carrying
`INSIDER-WIDE` §5d's **measured ~1.5× era correction**: `se` **8.63pp**, **MDE80 24.52pp**,
**gross power 6.3%**. **Against a +3.49pp effect that is about seven-fold short.**

**And the mechanism is the useful part: 2008 has 4.15× the recent filing volume** (108,320 P-rows
against a 2020-2025 average of 26,092/yr) **and still emits only 31 events**, because the rule needs
two prior years of *each pair's own* history and 2006/2007 hold just **1,010** and **3,863**
transaction-year rows — late filings, not coverage. **A source starting in year Y cannot emit until
Y+2 however rich year Y is.**

### 1d. The SEC's own free data — **the curated set buys NOTHING**, and that is the decisive finding

Read from the SEC's own pages:

| route | structured from | first emittable | gain |
|---|---|---|---|
| **Insider Transactions Data Sets** (curated quarterly TSVs) | **2006 Q1** (page header: Jan 2006 – Sep 2026) | **2008** | **ZERO** |
| **raw Form 4 XML on EDGAR** | **2003-06-30**, the mandate's effective date | **2006** | 2006 and 2007 |

**The curated route lands on exactly the 2008 owned data already reaches.** Release **33-8230**
(issued 2003-05-07, effective **2003-06-30**) mandated electronic Forms 3/4/5 under Sarbanes-Oxley
§403 and records only **~8%** filed electronically in June 2002 — so **1999-2002 is not in EDGAR in
structured form at all**, for anybody, at any price on SEC data. **The charter's 1999-2008 window
is at best 2006-2008 — three of ten years — all adjacent to the build window and dominated by the
GFC.**

### 1e. The build's size, **measured from EDGAR's own index rather than estimated**

| part | why it is needed | Form 4 filings |
|---|---|---|
| 2004-2005 | the prior-year history the strict rule needs before 2006 can emit | **950,387** |
| 2006-2007 | the two years gained | **954,721** |
| **total to fetch** | | **1,905,108** |

**52.9 hours** at the SEC's documented 10 requests/second ceiling, **105.8 hours** at a polite 5/s.
Power of the window that buys: **58.8% gross / 44.3% net** at the recent-era event rate (n≈937), or
**99.4% / 96.2%** if 2008's 4.15× filing volume holds (n≈3,889). **80% gross power needs n≈1,560.**
The spread is real and unresolvable without building it, which is why it ships as a range.

**CORRECTION 2, AGAINST MY OWN FIRST FRAMING: the curated route is TRIVIAL in size** — ~84
quarterly ZIPs at **8.66 MB** each, ~700 MB, minutes of downloading. The 1.9M-filing figure is the
**raw** route's and only the raw route gains anything. Both numbers are right and quoting the
1.9M against the curated route would overstate it by orders of magnitude.

### 1f. **OUTCOME: report the size and stop.** A free source *can* supply a window, so the prompt's
second branch applies — **Don decides whether to pay for it and this lane did NOT build it.**

**WHAT IT DOES NOT SAY:** it is **not** a finding that clustered insider buying fails before 2009.
The construction cannot emit events there, so the hypothesis is **UNTESTED** in that era rather
than rejected. `scripts/insider_stage3_feasibility.py`, `insider_stage3_sec_size.py`;
`INSIDER_STAGE3_FEASIBILITY.json`, `INSIDER_STAGE3_SEC_SIZE.json`.

---

## 2. F-23 — the forward paper book, DECLARED and **UNABLE TO FILL**

`DECL_f23_insider_cluster_shares.md`, **ALONE at `5ad68c2`**. The construction is frozen from
`PREREG_insider_cluster_wide.md`: the cluster rule verbatim, `cap >= $500M` at **point-in-time**
cap, `h`=63, the **filing** clock. `h`=126 is not traded.

### 2a. **THE FEED IS NOT VALIDATED, AND THE CAUSE IS ISOLATED TO ONE FIELD**

`sf2_zip()` is a **frozen export ending 2026-10-02**, so a forward book cannot run on it. The SEC's
free data is declared instead — EDGAR's **daily index** for the live leg, the quarterly **Insider
Transactions Data Sets** (one 8.66 MB ZIP) as the validation instrument. **Bars declared before the
comparison ran:** row recall **0.95**, event Jaccard **0.90**, on 2026-07-01..2026-09-30.

**BOTH FAIL** — 0.8465 recall and 0.6956 Jaccard on all tickers; **0.8698 / 0.8257** on the book's
own universe.

| key | recall | precision |
|---|---|---|
| ticker only | **1.0000** | 1.0000 |
| ticker + filing date | **0.9791** | 0.9915 |
| **+ owner name** | **0.8850** | 0.7748 |
| + owner name, **sorted tokens** | 0.8850 | 0.7748 |

**The two feeds agree on WHICH NAMES BOUGHT AND WHEN to 98-99% and disagree on WHO THE INSIDER
IS.** Sorting the tokens changes nothing, so it is not word order. **And it cannot be fixed with a
join key: SF2 has 24 columns and not one is an owner identifier** — only `ownername`, a string —
while the SEC supplies `RPTOWNERCIK`. Owner identity can therefore only ever be matched by
spelling, and the vendors spell differently (`FLORNESS DANIEL L` against
`Conifer Management, L.L.C.`).

**THAT IS THE TRIGGER ITSELF.** The rule fires on **`k` >= 2 DISTINCT `ownername`**, so a feed that
disagrees about owner identity disagrees about how many distinct buyers a cluster has. **A 98%
agreement on which names bought is not sufficient for a rule that counts people.**

**SO THE BOOK REFUSES RATHER THAN WORKING AROUND IT** — lowering a watched bar is what `W-28`
forbids. Two routes forward, **both Don's call**: run end-to-end on the SEC's own `RPTOWNERCIK`
identities (exact, and a **different event set** from the one that confirmed — ~83% overlap), or
wait for an SF2 refresh and accept a quarterly feed.

**A SECOND, INDEPENDENT BLOCK, AND IT IS THE HARNESS'S RATHER THAN MINE:** `fleet.may_fill` returns
`SELFCHECK_ABSENT` — Don's ruling that no book fills until the harness passes its own day-1
verification. So the book is blocked twice over.

### 2b. The horizon is derived, and **the cap is the interesting number**

`fills_needed` = **1,111** — the smallest `n` at which `track_meter.boundary`/`n` falls to the
book's own **NET** `min_effect` of **2.9122pp**, with `sigma` **MEASURED** at **28.0842pp** on the
governing cell's 1,093 banked rows. At 310 events/year that is **3.58 years**.

**But a 63-session hold on 310 events/year implies 77.5 expected concurrent positions, so at the
fleet's customary cap of 10 the book is throughput-limited to 40 fills/year and the horizon becomes
27.8 YEARS.** Hence **cap 100**: a lower cap would **refuse events**, and the register's result is
measured on **all** events, so **a binding cap would make this book a different construction from
the one that confirmed.** No round number appears anywhere in the horizon, and the power note
carries `INSIDER-WIDE`'s own measured **1.41×-1.63×** optimism warning.

### 2c. The late-half caveat is **inside the declaration**

§1 of the declaration, not a handoff footnote: the governing cell's **2023-2026** half is
**+0.5319pp gross against 0.5766pp of cost — −0.045pp NET** — and it satisfied the both-halves
clause only because each half is scored against **its own** null and the late null's p95 is itself
**negative**. **A forward book trades the future and the future looks like the late half**, so
`BLEEDS` would be **consistent with the register rather than a contradiction of it**. The
declaration also records that the book **knowingly holds names the no-verdict band decomposition
says contribute nothing**, because narrowing to `$500M-$2B` would be a construction chosen on a
diagnostic.

### 2d. Reported, not edited (`RUN_RULES` rule 3)

**THIS IS THE FLEET'S FIRST EQUITY BOOK** — no existing `DECL_` declares `domain: equity` — and
`validate_declaration` **requires** `structure.strike_selection` from an option-shaped vocabulary
(`moneyness`/`fixed`/`delta`). A shares book has no strike, so `fixed` is declared as the only
value asserting nothing about an option, **with the reason in the field beside it**. `fleet.py` is
the `S3-I1` lane's.

---

## 3. `tests/test_valreads.py` — the Windows-only failure, fixed and PROVED on both trees

Reported by the options lane (`HANDOFF_optionsbot.md` §87b). One mutation needle spans a newline
and was written with **LF**; `core.autocrlf` is `true`, so on a fresh **Windows** checkout the
module is **CRLF on disk**, the needle never matched, and the harness's own *"mutation point moved"*
assertion fired. **CI stayed green** because the stored blob is LF.

**AND THE SUITE PASSING IN THIS WORKTREE WAS NOT EVIDENCE EITHER** — measured: the local copy sat
at **512 bare LF, zero CRLF**, because the lane *wrote* it and git never re-checked it out.
**A guard whose behaviour depends on how a file arrived on disk is not testing the module.**

**THE FIX IS THE NEEDLE'S, NOT THE MODULE'S.** `_mutate` now measures the file's own line ending
and translates the needle to it, so the same case bites on either tree; the restore still writes
`orig` back verbatim, so the byte-for-byte guarantee is untouched. A needle carrying a stray `\r`
is **refused** rather than double-translated.

**PROVED ON BOTH TREES, BLOBS MATERIALISED RATHER THAN `git archive`** (which applies the CRLF
filter on Windows — `git-archive-is-not-a-CI-simulation`, already paid for once). 1,614 files
written from their stored blobs per tree:

| tree | test file | result | |
|---|---|---|---|
| LF | **fixed** | **PASS** | |
| CRLF | **fixed** | **PASS** | the repair |
| LF | pre-fix | PASS | so the old needle was not broken everywhere |
| CRLF | pre-fix | **FAIL** | **the reported defect, reproduced** |

The last two are the non-vacuity half: without them a passing fixed case is consistent with the bug
never having existed. `scripts/valreads_eol_proof.py`, `VALREADS_EOL_PROOF.json`.
`tests/test_valreads.py` **51 tests, OK**; `valuation/edge/valreads.py` unchanged against `HEAD`.

---

## 4. Defects of my own — two, both caught by disbelieving a number

**(a) THE SEC SIZE COUNTER REPORTED ZERO FORM 4 FILINGS ACROSS FOUR YEARS AND SAID SO.**
`form.idx` is **fixed-width**; `master.idx` is pipe-delimited with the form type in **field 3**.
The first cut read `form.zip` and skipped every line lacking a `|`, counting **0** — impossible,
since Form 4 is the most-filed type on EDGAR. **Caught by disbelieving the number, not by anything
raising** — the `blank-code counter` family, and **a zero there would have argued that the SEC
build is free.** Repointed at `master.idx` and **gated on a positive control**: a quarter whose
`8-K` or `10-Q` count is zero is returned as `PARSER FAILED`, never as a number.

**(b) THE FIRST-EMITTABLE PROBE INVENTED A SIGNATURE FOR THE SHIPPED PREDICATE.** It called
`prior_year_presence(years, y, strict=True)`; the real signature takes a **DataFrame** and keys on
transaction years. Rewritten to exercise the real function with a positive probe **and** a gap
negative control — which is also what surfaced correction 1b.

---

## 5. Not done, named so it is not mistaken for done

* **Nothing is adopted**, no file under `valuation/` changed, **no order placed and no broker
  touched**, no percentage set by this lane.
* **THE OLDER-DATA BUILD IS NOT BUILT.** The size is reported and the decision is Don's.
* **F-23 HAS NO FILL AND ITS CLOCK HAS NOT STARTED.** It is blocked twice — the feed bars and the
  harness's `SELFCHECK_ABSENT`.
* **No `RPTOWNERCIK`-native variant is built.** It is a different event set (~83% overlap) and
  therefore a different construction; it needs Don's decision and, if taken mid-record, a dated
  amendment of the kind `VALREADS` requires.
* **The 1999-2005 era is not merely unbuilt, it is structurally absent** from SEC data — the
  filings were on paper. Whether a paid vendor reaches earlier is a **different question** and
  `WRDS_CENSUS.md` is where it would be answered; nothing here claims it cannot.
