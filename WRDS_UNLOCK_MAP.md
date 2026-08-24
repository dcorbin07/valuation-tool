# WRDS_UNLOCK_MAP.md — what institutional data access dissolves, entry by entry
## Frontier Scout, 2026-08-24. Census-conditional throughout: every entry is
## "IF `WRDS_CENSUS.md` confirms <product, fields, span> THEN <what reopens>" — nothing
## here reopens anything by itself, and no outcome statistic was computed anywhere in it.

**Context, and the door this walks through:** `D7` closed WRDS as NOT PURCHASABLE, "every
one requiring affiliation with a subscribing institution" — **affiliation is the thing that
changed**, so D7 dissolves by its own text, and `D6` ("Path is IBES via WRDS, so D6 and D7
are ONE decision") unparks with it. The D-series' buy-nothing verdicts were priced against
retail dollars; the census now prices against entitlements.

**THE LICENSING FENCE (every sketch inherits it verbatim):** WRDS data is research-only
under the institution's subscription. It never ships in the product, never renders on any
public page (`/research`, `/tidemark`, the fleet shelf included), never feeds a live score.
**Raw rows never leave `D:\wrds`**; registers bank derived aggregates only; the repo is
PUBLIC, so `D:\wrds` paths join `.gitignore`'s licensed-data class and `DATA-HISTORY`'s
purge lesson applies in advance, not after. Where a claim is someday publishable, it is
publishable in `MB38`'s vocabulary (counts, hurdles, verdict words) — never as WRDS-derived
values.

**Interlock convention:** each entry's `CENSUS:` line names product → library.table →
fields → span → link path, in that order, so the data miner's `WRDS_CENSUS.md` can tick
them one-for-one.

---

## TIER 1 — REOPENS A PERMANENTLY CLOSED DOOR

### W-1 · The PIT sector map — S25's "unobtainable" becomes an entitlement question
**Graveyard: [S25 CLOSED-UNOBTAINABLE / S15 "sector-neutral in every form is finished" /
SECTOR-NEUTRAL-B6 rejected-on-the-panel-that-counts]**
The closure chain's own language is the unlock: S15's finality rests on S25, and S25's text
is *"no PIT sector map exists in anything we own"* with exactly two recorded routes back —
the EDGAR SIC build, or a historical GICS snapshot *"not sold as history."* **Compustat on
WRDS sells it as history**: the historical-GICS table carries `indfrom`/`indthru` validity
windows — assignments as they stood, not as they stand. Taxonomy matches the panel's need
(GICS 11-sector). PIT-ness is honest but must be censused, not assumed: the known caveat
class is backfill at coverage inception and sparse windows for dead names — **the census
must check dead-name coverage explicitly** (a PIT map that only covers survivors is today's
map in a costume).
**IF census confirms THEN:** S25 flips OBTAINED; the sector-neutral family's one named
re-open condition is met. The reopen must still argue past `SECTOR-NEUTRAL-B6`'s rejection
— the argument is instrument, not hope: that rejection ran on TODAY'S map applied backward,
whose misclassification of historical names is attenuating noise; the register's premise
census (descriptive) is the year-by-year agreement rate between the two maps, which
measures exactly how different the new instrument is before any arm runs.
**CENSUS:** Compustat North America → historical GICS (co_hgic or equivalent) →
gvkey, gsector, ggroup, indfrom, indthru → 2009-01→present INCLUDING delisted names →
link gvkey↔permno↔ticker via CCM + stocknames.
→ Full sketch §TOP-3 / W-1.

### W-2 · Index options via IvyDB — P6's NEEDS-DATA dissolves and the $150/mo question with it
**Graveyard: [P6 NEEDS-DATA (no index chain owned) / O8 INCONCLUSIVE-on-proxies / B-G1
(the pre-authorized purchase question)]**
OptionMetrics IvyDB covers index options (SPX complex) back to 1996. **IF census confirms
THEN:** the B-G1 dispersion question — *are our premium books selling the cheap leg of a
dispersion premium?* — becomes answerable **without the ~$150/mo vendor purchase**, and O8
gets the real instrument its INCONCLUSIVE always lacked. The purchase authorization goes
back in Don's pocket.
**CENSUS:** OptionMetrics IvyDB → secprd/opprcd + stdopd (standardized surface) for
SPX/SPY → IV surface, deltas, expiries → 1996→present → index secids enumerated.

### W-3 · IBES — the parked-at-any-price revisions class unparks by its own row
**Graveyard: [D6 "STAY PARKED... Path is IBES via WRDS" / D7 affiliation / PEAD's corpse
tagged in the sketch]**
**IF census confirms THEN:** D6 unparks outright — the one signal class the record priced
as unobtainable at retail. First register sketched at §TOP-3 / W-2 (revision breadth, not
level — and it must face PEAD's local rejection by name, since revisions and drift are
cousins).
**CENSUS:** IBES → det_epsus (detail) + statsum_epsus (summary) → estimate, statpers,
anndats, revision timestamps, analyst counts → 2009→present for panel names → link via
ibcrsphist (IBES↔CRSP).

### W-4 · TAQ — MB41's "no equity tape" dissolves, if and only if entitled
**Graveyard: [MB41 NOT-TESTABLE-HERE — "this project owns no index chain and no equity
tape"]**
TAQ is often a separate (and enormous) entitlement; the census answers it in one line.
**IF confirmed THEN** MB41's disqualifier is gone and Gao et al.'s intraday momentum
becomes testable on SPY minute bars — ranked here for honesty, not enthusiasm: it is a new
family with real storage costs, behind everything above.
**CENSUS:** TAQ (monthly/daily trades) → SPY minute bars sufficient → entitled? span?

## TIER 2 — REPAIRS A KNOWN DEFECT

### W-5 · Thomson s34 — the panel's most consequential coverage hole, repaired at the root
**Graveyard: [MB7's 49-of-69-dates complete-case defect / MA58-SEAS UNINTERPRETABLE-partly-
on-it / RUN_RULES A-10 exists because of it / THEME-RESTORE & FIDELITY-2 (the splice
precedent)]**
Our `institutional` column is empty before ~2013-06 (coverage 0.7172, first usable date
2014-01-17) — the root cause of every basis-seven residualization losing 20 of 69 dates.
s34 reaches back decades with `rdate`/`fdate` giving honest PIT lag. **IF census confirms
THEN** the ONE-column backfill becomes possible — priced honestly as what it is: **a
panel-change register, not a data drop.** It needs: a fidelity gate on the overlap window
(splice only if the s34-derived theme rank-correlates ≥0.60 with the shipped theme where
both exist — FIDELITY-2's bar, imported not re-derived), a declared splice date, and the
named consequence that **X7's floors are calibrated on THIS panel** — a materially changed
panel column owes the placebo re-sweep question an explicit answer in the register (MA33's
caution, now with a concrete trigger). → Full sketch §TOP-3 / W-3.
**CENSUS:** Thomson Reuters 13F → tr_13f.s34 → mgrno, cusip, shares, fdate, rdate →
2009-01→2014-06 coverage of panel names (the gap window) + overlap 2013-06→present →
link cusip↔permno.

### W-6 · CRSP delisting returns — the survivorship mask cross-checked by the canonical source
**Graveyard: [B14 (ACTIONS delisting mask "complete") / E-5's terminal-value rule / C5's
32.1%-invisible measurement]**
Zero-trial record-integrity class: reconcile our ACTIONS-based mask and E-5's terminal
handling against CRSP's dlret/dlstcd. **A disagreement is a finding either way** — ours
wrong = a correction with blast radius named; CRSP-confirmed = the mask gains an external
validation line. **CENSUS:** CRSP → dse/dsf delist events → dlret, dlstcd, dlstdt →
2009→present → permno↔ticker.

### W-7 · CRSP $ADV — B13 and S7's fourth interaction dissolve together
**Graveyard: [B13 PARTIAL-BLOCKED ("MIN_AVG_DOLLAR_VOLUME structurally cannot bind — the
price export carries date and close ONLY") / S7 ("size × liquidity IS NOT BUILDABLE") /
MA25 (capacity.py's 195-name partial) / B-G5 in the season map's gated tail]**
CRSP daily prc×vol gives dollar-ADV for the full universe over the full window. **IF
census confirms THEN** two blocked rows dissolve at once: B13's prefilter becomes bindable
(FIXED-class repair), and S7's one untestable interaction becomes buildable (1 equity
trial, arguing past S7's three *rejected* siblings by the closure's own "not buildable"
language — the fourth was never rejected, only impossible).
**CENSUS:** CRSP → dsf → prc, vol, shrout → 2009→present full panel → permno↔ticker
share-class handling stated.

### W-8 · IvyDB as clean instruments for already-queued work
**Graveyard: [O-1's K2 (BL-from-raw-chains), E-8/X-SEED-1, SC-3/DEEPITM-FIN, F-5/I-2-on-vol]**
Not reopens — upgrades: O-1's RND pricing kill on a standardized 1996→ surface instead of
raw-chain BL; E-8's market-vs-accounting disagreement cells on the same; SC-3's financing
term structure extended from one owned era (2016-18) to the whole modern record; F-5's
own-history IV percentile gets a real 25-year burn-in someday. Each consuming register
cites this entry rather than re-arguing entitlement.
**CENSUS:** IvyDB → opprcd/stdopd + secnmd → per-name surface, greeks, expiries →
1996→present → secid↔cusip link; note whether implied borrow / dividend fields ship.

## TIER 3 — MERELY EXTENDS (real, priced, behind the above)

### W-9 · The Compustat twin — and the one arithmetic it re-derives
**Graveyard: [X8 (JKP replication, international) / OOB2 (single-vendor fragility) /
MB13 NOT-PERMITTED — read carefully below]**
CRSP+Compustat can rebuild the seven themes on the SAME universe from a second vendor —
the strongest replication available (X8 was other countries; this is the same market,
independent pipes). And the deep version: Compustat reaches the 1960s, so a ~60-year twin
panel is constructible. **The honest statement about MB13:** its NOT-PERMITTED is "on this
panel" arithmetic (34.2 years/side against 17.3 owned) and is untouched as written; a
60-year object changes the inputs to that arithmetic (68 needed vs ~60 for the full-alpha
gap — still short; ~35 total for a 10pp gap — reachable). **New data does not void the
discipline: the MB22 gate re-runs on the new n and rules.** Priced honestly: this is the
largest build in the map (a second panel, its own placebo calibration, its own floors — a
season, not a session), and the twin's first register is the cheap headline replication,
not the regime question. **CENSUS:** CRSP dsf/msf + Compustat funda/fundq → the seven
themes' input fields enumerated one-for-one against `settings` → 1965→present → CCM link.

### W-10 · Short interest pre-2018 — S18's partial-sample gate completes
**Graveyard: [S18 rejected on 32-of-69 dates, all late]** Compustat's short-interest file
reaches decades back. IF confirmed, the both-halves gate exists for the first time — a
new-data re-measurement of decisively-rejected arms: low rank, 1 equity trial, listed
because nothing is discarded. **CENSUS:** Compustat → sec_shortint → shortint, datadate →
2009→2018 panel coverage.

### W-11 · Surface features at panel scale and era depth
**Graveyard: [O3/O4/O5 closed as alert-day monthly sorts / B-11 in the season map]**
B-11's data unlock (panel-date surface objects) upgrades from "2016→ deep freeze" to
"1996→ IvyDB" — same register family, more power, same tags. Rides W-8's census line.

### W-12 · MA31/MA32 — reopenable ONLY carrying the borrow-fee control
**Graveyard: [MA31/MA32 NULL-uninterpretable / U2 / the five-body orthogonality wall /
the 2026 JFE borrow-fee finding]**
The literature now says options-signal→stock predictability is substantially a borrow-fee
proxy. **The only honest reopen of this family is one that measures the borrow channel
explicitly** — via Markit securities lending IF entitled, or IvyDB-implied borrow —
as a registered control. Without that entitlement this family STAYS SHUT and this entry
is its tombstone-with-a-condition. **CENSUS:** Markit/other securities-lending on WRDS →
entitled at all? fee/utilization fields? span?

### W-13 · PIT-Compustat (as-first-reported) — flag robustness, someday
**Graveyard: [MA28-CARD (published-threshold flags on Sharadar's as-reported)]** If the
PIT/unrestated database is entitled, an as-first-reported robustness pass on the crash
flags is a cheap secondary someday. Low. **CENSUS:** Compustat PIT/snapshot entitled?

## THE ANTI-SEED — what WRDS does NOT touch (quote this list, not "we bought data")

* **Mechanism closures stay closed:** short-vol as richness-selling (`O9`/`A3`/`V6-OPT` —
  the strike spends the edge; no vendor changes that), the alert entry (`R2` — the alert
  doesn't exist pre-2016 and its defect is the signal, not the sample), `U1`, exit-rule
  tuning (`S23`/`O1`/`PATHSTUDY` — properties of this book), `O13`, `U7`, `MB8` (flags
  disjoint from the book is a book fact), weight/scheme tuning (`MLCOMB` reversed OOS),
  "orthogonal" as a motivation (five bodies), `MB9`-as-stated.
* **Time-bound arithmetic stays time-bound:** `S19`/`MA33`'s decay clock needs future
  months, not better history; `V1`'s shadow pairing needs an adoption event; every fleet
  verdict horizon needs fills, not files.
* **N-bound machinery is untouched:** the placebo floors, the HLZ hurdles, the DSR — they
  move on trials, not entitlements; `MB13` as written stands (W-9 changes its *inputs* on
  a *different object*, and says so rather than sneaking it).
* **The alert-cache power walls stand:** `MB15-SLIM` and every rubric bucket-3 item are
  bounded by alert-days, and WRDS sells no alert days.
* **The S-series' rejected arms are not individually re-run by the twin** (W-9 replicates
  the HEADLINE; re-running each dead arm on a second vendor is the unchanged-re-run
  exclusion wearing a lab coat).

## TOP-3 FULL SKETCHES (register-shaped; executor commits ALONE; counters re-read at run)

**W-1 · PREREG sketch — the PIT sector map and the one re-run it licenses.**
Stage 0 (descriptive, free): census + the two-map agreement table by year (today's-map vs
PIT-map sector per name-date; the disagreement rate IS the instrument-difference measure)
+ dead-name coverage rate (the costume check: a survivor-only map is refused here and the
register dies free). Stage 1 (2 equity trials, 242→244 at this writing; hurdle 3.3133→
3.3158): `SECTOR-NEUTRAL-B6`'s two pre-specified weightings re-run VERBATIM with only the
map swapped — no new arms, no new bars, its own thresholds imported. Kill pre-committed:
if stage-0 disagreement < 10% pooled, the maps are the same instrument and the arm is
WITHDRAWN (nothing to reopen). MDE: the B6 register's own banked dispersion governs;
design-class detection ≈0.43 SD at 80% / 0.30 at 50% on the incremental convention —
executor prints exact from banked draws via `power_gate.state()`. Verdict grammar:
REOPENED-AND-CLEARS / REOPENED-AND-REJECTED-AGAIN (S15's closure then stands on a clean
instrument, permanently) / WITHDRAWN(same-instrument). **Fence:** GICS assignments are
licensed content — the register banks agreement RATES and sector-relative aggregates,
never the map itself; nothing renders publicly.

**W-2 · PREREG sketch — IBES revision breadth, first contact.**
Object: per name-date, 3-month up-minus-down revision count over analyst coverage (breadth,
not level — level is a price cousin). Sign POSITIVE declared. Primary: incremental IC
under `MB7`'s gate, both bases co-primary, `split_used="effective"`, coverage printed
(IBES coverage of small caps will bind — the partition is reported, not pooled away).
Kills pre-outcome, separate pass: |rho| vs momentum theme > 0.60 (Chan-Jegadeesh-Lakonishok
overlap); vs the banked PEAD column > 0.60 (the corpse faced by name); coverage < 60% of
panel rows → UNPOWERED-BY-CONSTRUCTION, dies free. 1 equity trial (→243; 3.3145). MDE:
0.43/0.51 SD at 80% (bases six/seven), 0.30/0.36 at 50%. Verdict: works/fails/cannot-tell.
**Fence:** estimates are licensed rows; aggregates only; nothing public.

**W-3 · PREREG sketch — the s34 institutional backfill (a panel-change register).**
Stage 0 (descriptive): s34 coverage census on the gap window (2009→2014) for panel names;
lag structure (rdate−fdate distribution) — PIT honesty is the lag, and the register
inherits the shipped `inst_lag_days` convention. Stage 1 (fidelity gate, the FIDELITY-2
precedent imported): build the s34-derived theme on the OVERLAP window (2013-06→present);
splice licensed ONLY if rank-correlation with the shipped theme ≥ 0.60 per date, median
across dates. Stage 2 (the splice, 1 infra trial — a rebuild with no hypothesis): extend
the column, rebuild the panel object under a NEW name (never overwrite
`panel_corrected_69d.pkl` — the M4/B23 lesson), and print the before/after effective-
coverage table (69/69 expected on basis seven). **The named consequence, priced not
hidden:** X7's floors are calibrated on the old panel; any register that SCORES on the
extended panel owes a floor re-derivation first (the 3.4-hour-class sweep, or MA19's
banked-draw route where valid) — this register does not run it, it prices it and stops.
Verdict grammar: SPLICED / FIDELITY-REFUSED / COVERAGE-REFUSED. **Fence:** s34 holdings
are licensed; the panel stores derived theme z-scores only; the raw stays on `D:\wrds`.

## WHAT DATA MINER'S CENSUS MUST CONFIRM, in one block (the interlock checklist)

1. Compustat historical GICS: table, fields, span, **dead-name coverage** (W-1).
2. IvyDB: entitled? tables, span 1996→, index secids (W-2/W-8/W-11), borrow fields (W-12).
3. IBES: det+summary, revision timestamps, ibcrsphist link (W-3-sketch/W-2-tier1... the
   IBES entry), small-cap coverage rate vs our panel (the kill's input).
4. TAQ: entitled at all (W-4).
5. Thomson s34: gap-window coverage + rdate lag distribution (W-5).
6. CRSP: dsf fields incl. vol; delist dlret/dlstcd (W-6/W-7); msf for the twin (W-9).
7. Compustat short interest: pre-2018 span (W-10). 8. Compustat PIT: entitled (W-13).
9. Markit securities lending: entitled (W-12's gate).

*Zero trials charged by this file. Every reopen above still argues past its tag inside its
own register, and the census is the gate on all of it. — Scout*
