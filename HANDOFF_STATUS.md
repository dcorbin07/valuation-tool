# Valquo — handoff status

Written at the end of every Claude Code session. Overwritten each time, so this is always
the current state, not a log. Plain text, no colour codes — the Cowork agent reads this
file directly.

## 2026-08-11 — data-spend lane (D4): DON'T BUY the Cboe Open-Close Volume Summary — and a free six-month trial means you never had to pay to find out

**The last open D item is closed, so the D series is now complete.** Research only, **no code
changed, zero trials**. Memo in `HANDOFF_data_spend_d4.md`, in the `HANDOFF_data_spend.md` house
style; ledger row `D4` OPEN → DONE/REJECTED.

**It is priced, and the audit's figure understates it badly.** The product page shows no price but
points at fee schedules **filed with the SEC**. Verified: EOD subscription **$500/mo**; EOD ad-hoc
historical **$400 per request per month**, with **one request = one month of data** (quoted
verbatim); ten-minute intraday $1,000/mo; one-minute $6,000/mo. Fees are filed **per exchange**
(C1, C2, BZX, EDGX). The 94 purchasable months of this project's own alert window
(**2016-01-01 → 2025-10-15**) cost **$28,200–$37,600 for ONE exchange**. Against the audit's
indicative *"roughly $600/yr"*, stated on comparable bases: the **recurring** subscription is
**$6,000/yr per exchange (~10×)**, and the **one-time** history purchase has **no counterpart in
the audit's figure at all** — the two are deliberately not compressed into one multiple, because a
one-time cost divided by an annual rate means nothing. The audit's own caveat that its figure was
for a different product was right to be there.

**Three findings the audit did not have.**
1. **A six-month FREE TRIAL of ad-hoc historical EOD Open-Close data exists** (filed Dec 2025,
   clarified Jul 2026), open to *"both TPHs and non-TPHs who have not previously subscribed …
   or previously received a free trial."* **Don qualifies.** The audit's "one sales call" is
   obsolete — the correct action costs nothing. It is **one-shot**, so *when* it is spent matters.
2. **The licence forbids what Valquo is.** *"Raw data is licensed for internal use only and may not
   be redistributed externally in any form"*; external distribution of **derived** data is
   **$5,000/mo ($60,000/yr) plus approval**. A score shown on valquo.co is derived data distributed
   externally. Same shape as D1's Sharadar finding and JKP's research-only licence.
3. **Ad-hoc history starts January 2018**, so **24 of the book's 118 months (20.3%) are unavailable
   at any price — and they are the EARLY ones.** D4 cannot be tested by this project's own
   both-halves standard, in a programme whose signature failure is a result holding on one half and
   reversing on the other.

**The gate was never approached, and it points one series over.** `O14` (free alert-day tick flow,
**~7 hours on data already held**) is still OPEN and has never run. Of the twenty OPEN O and U
items only **two** are flow items and one is `O14` itself, so **D4 names exactly one open item that
is not its own gate: `U2`.** The audit filed D4 under options while its cited literature
(Pan–Poteshman 2006) predicts **stock** returns — and the options entry is dead (`R2`, −5.0640pp
split-clean) — so the only live route is `U2` into the equity composite, which `S22`'s flat
three-month-to-two-year alpha makes a ~60× horizon mismatch.

**Reported because it cuts toward running O14:** `O13` (yesterday) found the gap is entirely a
within-bin **rate** effect — the alert loses on the **day** it picks, uniformly — and flow is a
day-level feature. But `O13`'s own refusal rules made the other half **worse in both directions**,
and **you cannot short the gap**.

**Recommended next step: run `O14`, then `U2` — both free — and only then spend the trial. Do not
buy.** Five bugs reported, including the gate pointing at the wrong series and nobody having checked
the dataset's start date against the book's own window.

## 2026-08-11 — options-bot lane (O13 + O12): the anti-signal is DIFFUSE and un-tradeable, and the dead entry costs 2.75× in position size

Two ledger items closed, one session, frozen book, no re-mine, no live code path touched. Both
registers committed **together and ALONE** at `b0f287d` (two `.md`, **zero `.py`**), a strict git
ancestor of every measurement commit. **R2 is not re-opened** — this characterises the corpse.

**O13 — the primary finding is not the verdict, it is the decomposition. The −5.0640pp gap is
ENTIRELY a within-bin effect.** Across all 32 feature arms the *rate* component runs −4.23pp to
−5.79pp against a −5.0640pp total, while the largest *mix* (composition) component anywhere is
**0.7711pp — 15.2% of the gap**. **The alert does not lose by picking different contracts from
random entry; it loses inside every kind it picks.** That closes off a family of repairs:
"trade longer-dated / tighter spreads / bigger names" are all composition fixes, and composition
is not where the damage is.

**O13 verdicts: Q2 DIFFUSE, Q3 inverse NULL.** Nothing clears its own calibrated p95 in both
halves (4 of 32 clear full-sample vs ~1.6 expected at a 5% bar). The refusal rule fails in the
informative direction — early→`dte`/q2 gives **−0.0977pp** on the late half, late→`iv`/q3 gives
**−0.7774pp** on the early half; **both make the measure half worse and the two directions select
different features**, session 7's LOO pattern for the third time. **You cannot short the gap
either:** the anti-signal is *relative*, the alert book's own expectancy is **+3.27%**, so
reversing it is negative before costs.

**`dte` is the cell that looks like a finding and is not.** Alert expectancy climbs monotonically
with tenor (−0.35% → +7.63%) while the control stays flat, q2's gap is −10.84pp — and it **does
not clear its own calibrated bar** (0.472 vs p95 0.497). **Do not act on it.**

**O12 — NOT USABLE, and the halves agreed.** `f*` = **0.0403** on the empirical distribution;
early/late 0.0515/0.0293, ratio **1.758**, which *clears* the pre-committed 2.0 — but the
month-block bootstrap CI95 is **[0.0000, 0.1001]** with 8.0% of draws at exactly zero, so the CI
includes zero. **Right answer, wrong reason:** the predicted instability was not what killed it.

**The practical number: at full Kelly, P(drawdown > 50%) is 0.753 for a median +26.7%/yr.**
Half-Kelly 0.222, quarter-Kelly 0.006 while keeping most of the growth (1.114 vs 1.267). At
f = 0.10 — only 2.5× Kelly — **the median outcome is a LOSS on a positive-expectancy book**. If
any fraction is ever used it is a quarter or less.

**R2 restated in sizing terms, and it is new: the random-entry control supports `f*` 0.1110,
2.75× the alert book's.** The dead entry costs not only expectancy but the size the book can
carry. Live flat 1-contract sizing (median premium $2.57 → $257) equals `f*` at **$6,371** equity,
so the live book is under-sized above that and **over-sized below it**.

**Defects found and reported (none in the live product):** `iv_rank` is wired and **0.0% populated
on both books**; `opt_right` and `horizon` are **constant — the banked options book is 100% calls
and 100% swing**, so every options claim is about long calls only; the alert label vocabulary is
**parameterised** (`Low IV 14%`…`19%`), inflating 17 registered arms to 32 — the trial cost was
corrected **upward**, against my own result. A defect in my own repair was caught by a test before
any verdict was read and is recorded as an amendment.

**17 of 100 bins DO lose money outright** — the widest-spread, least liquid ones
(`entry_spread_pct` q5 **−7.41%**). That refuted my own pre-registered expectation and is the
**recommended next step: `entry_spread_pct` as its own pre-registered refusal rule.**

Full gate **57 suites, all green** on the merged tree (two new here: `test_antisignal.py` 35,
`test_kelly.py` 28).
Options `N` **210 → 246**; **equity `N` untouched at 155** and `BACKTEST_RESULTS.json` needs no
re-run — the trial counter is domain-scoped. Detail in `HANDOFF_optionsbot.md` §24–28.

## 2026-08-11 — CI lane (LA11): the retracted 8%-cap diagnosis is gone from the code, and COLD AUDIT #2 IS FULLY EXECUTED

**All fifteen cold-audit items (LA1–LA15) are now resolved** — LA6 is tracked as `V2F`/`V2G`
rather than as its own row. LA11 was the last one open.

`PT-SPLIT` retracted the claim that the sandbox engine's 10% weights breach the contract's 8% cap
(`build_index` sets `cap = max(MAX_WEIGHT, 1/len(picks))` on purpose — ten names at 8% sum to 80%).
The **conclusion** survives on book **size** (10 names vs the published 86); only the reason moved.
The retracted reason was still standing in prose, which is worse than no reason: check the cap,
find it correct, doubt the separation itself.

**The audit named three sites; there were eight.** The five extra were found by grepping the claim
instead of following the citations — `web/hero.py`, `edge/track_export.py` twice,
`.github/workflows/track-backup.yml`, and `PAPER_TRACK_CONTRACT.md` §0a.2. The `index_track.py`
cite had drifted 82 lines in a day.

**Two of them were worse than docstrings.** `track_export._README` is *emitted*, so the retracted
claim shipped as committed **data** in `data_export/README.md` — put there by the LA2 work of one
day earlier, i.e. this lane's own. And the **contract corrected itself in §5b while §0a.2 still
asserted the retracted clause**; §0a.2 is now struck in place with a dated pointer, original left
visible, **no threshold, date or parameter moved**.

**A test was pinning the wrong diagnosis into the artifact.** `tests/test_track_export.py` required
the README to state "the weight caps that tell the two books apart" — the caps are exactly what
does *not* tell them apart, so it would have failed had the README been fixed and the test left
alone. It now pins book size. A comment in `tests/test_paper_track.py` likewise contradicted a test
in its own module; the test was right.

Full gate **52 suites, all green**. Zero research trials — a documentation correction; equity `N`
unchanged at **151**. Detail in `HANDOFF_ci.md`. **Unchanged and still the real blocker:** nothing
ingests the bound series into the live store and there is **no automated daily writer** for it
(`PT-WRITER`, Cowork lane).
## 2026-08-11 — edge lane, session 21 (S20/S21): the standardiser is worth several points of alpha, and no theme IC can see it

**Both arms failed their gate and nothing is adopted — but the pair is the most useful thing
measured here in a while.** Two constructions that move top-decile alpha by **−3.49pp and +2.43pp
per year** change **no theme IC by as much as 0.4 of a *t***. If you judged either by per-signal or
per-theme IC you would call both harmless.

Ledger **S20** ("rank composite, not z-sum") and **S21** ("winsorise before standardising"), both
`OPEN`, both `src=auto`, neither ever run. `PREREG_s20_s21_construction.md` committed **alone at
`27af414`**, a strict ancestor of the measurement commit; the **shipped**
`holdout_compare_panels` at the **already-committed** margins (+100bps alpha AND +0.25 long-short
*t*, in **both** halves), corrected 69-date/2,531-name panel, two pre-specified weightings.
**One panel build, three scorings, 113,945 provably identical rows.**

**S20 (RANK) — REJECTED**, both halves, both weightings. Alpha **+7.17% → +3.68%**, long-short HAC
*t* **2.6199 → 2.0588** and alpha HAC **4.3762 → 2.0028**, so it **fails both calibrated floors**
(extrapolated for a challenger arm) where the shipped arm clears both. **It fails while making the
deciles BETTER ordered** (monotonicity −0.8909 → **−0.9515**): the ordering across deciles smooths
out while the **top** decile — the product — loses its edge, D1 25.31% → 21.82%.

**S21 — NOT REPLICATED, and its premise was wrong.** `zscore` **already winsorises at 2% before
standardising**, at both layers, so the arm actually run is winsorisation **OFF**. Full sample every
headline improves — alpha **+9.60%** (+2.43pp), long-short *t* **2.8361 → 4.9395** — **but the early
half misses the alpha bar by 17 basis points** (+0.83pp vs +1.00pp) while clearing the *t* margin,
and under **flat weights it rejects outright**, both halves negative. The paired difference reaches
HAC *t* +1.9170, below even the **uncalibrated** 2.0. Ambiguous against its own threshold is a
**NULL** (`RUN_RULES` A6).

**THE CAUTION THAT MUST TRAVEL WITH THAT +2.43pp:** the unclipped arm's most extreme composite
averages **7.14× its own 99th percentile** against **1.64×** for the shipped arm, and only **8 of
the shipped top 25 names** survive it. An unclipped z-score is a **fragile estimator**.
Winsorisation is also a **data-quality defence** — P7 shipped a currency bug computing
`book_to_price` **892 against a true 0.589**, and with no clip that row dominates the whole
cross-section.

**Controls: six pass, one falsified.** C1 reproduces the record to the digit; C5 measures
`max |ΔIC| = 0.000e+00` across 44 columns — Spearman IC is invariant to a strictly monotone
transform, so **the per-signal diagnostics are mathematically incapable of seeing S20**. **C7 is
FALSIFIED and corrected rather than dropped:** the register claimed a rank arm must be bit-identical
under winsorisation; it is not, because winsorisation is only **weakly** monotone and creates
**ties**. So S20 does **not** strictly subsume S21.

**Nothing adopted, by a clause fixed before the run.** Either adoption would be a **VINTAGE EVENT**,
and an eligible arm would have been recorded **ELIGIBLE** and **queued behind the theme
restoration's vintage** rather than spending a second five-year clock reset. `CONFIG`,
`settings.FACTOR_WEIGHTS` and `sector_neutral` untouched. Equity `N` **151 → 155**,
√(2·ln 155) = 3.1760, `BACKTEST_RESULTS.json` re-run from a clean tree.

**Next in this lane:** S21 is **not** closed as impossible — it is the strongest untested
construction lead in the project, and re-opening it needs **new evidence** (a placebo calibrated
under an unclipped composite, plus a defence against the outlier fragility), **never a plain
re-run**. Full write-up: `HANDOFF_edge_audit.md` session 21.

## 2026-08-11 — options bot, session 23b (U1-SPLIT): R2's published gap was 24% artifact, repaired at source, and NO VERDICT MOVED

**Quote R2 as −5.06pp, not −6.65pp.** That is the one thing to carry away.

A corporate-action defect found during U1's calibration has been repaired at source and every
figure it touched re-derived. Pre-registered in `PREREG_u1split_repair.md`, committed alone before
any repair code existed, naming the eight published figures that move and the expected direction
of each.

**The defect.** Option chains are as-traded and unadjusted for splits while Sharadar bars ARE
adjusted, and nothing in the options lane consulted the split table. GE's 1-for-8 reverse split
(2021-08-02) moved `raw_close` 12.95 → 100.60 while the strike stayed pre-split, so a $0.27 call
settled at `max(0, 100.47 − 14.00) = 86.47` — booking **+31,921%** against a true value of
**zero** (the OCC adjusts the deliverable to 12.5 shares and leaves the strike).

**The exposure was wider than first diagnosed.** 106 of 131 affected control rows never reach the
settlement line — they exit on target or stop, i.e. on post-split quotes, because a reverse split
keeps the strike and the history lookup matches on exact strike. So the guard rejects at ENTRY on
the contract life, decided before simulation and therefore outcome-independent, keyed on an
external table and a date and never on the size of a return.

**The headline moves, the verdict does not.**

| | as published | split-clean |
|---|---|---|
| alert book | +3.4103%/trade | +3.2702% |
| five-seed control | +10.0571%/trade | +8.3342% |
| gap | −6.6468pp | **−5.0640pp** |
| date-block CI95 | [−11.92, −2.13]pp | [−8.60, −1.53]pp |
| sign test z | −4.9027 | −4.9612 (p 7e−07) |

**24% of the published gap was an artifact.** The control is hit ~12× harder than the alert book,
so the defect had been making R2's negative verdict look WORSE than it is. Reported because it
cuts against the obvious reading: **the sign test does not weaken — it strengthens** (−4.9027 →
−4.9612), because the artifact lived in the control's right tail and the median name-year cell
never depended on it.

**TP-BAR was flagged in advance as the one figure that could reopen a closed item. It does not.**
Split-clean the C1 bar goes +5.0812 → +5.1302pp and tp150's gain +3.1948 → +3.1834pp, so both
arms still fail C1 and the margin WIDENS (1.8864 → 1.9468pp). **Item A stays closed.**

**Every as-published figure reproduces to the digit before any corrected one is quoted** — that
is the control that makes the correction checkable.

**Fingerprints re-stamped.** The freeze is untouched and verified rather than asserted: 1,429
symbol-years checked, 0 changed, so every banked replay pin still holds. Corrected books are NEW
files; originals are never overwritten. `U1SPLIT_MANIFEST.json` carries sha256 of both sides of
all six books.

**Corrected in place and dated**: CLAUDE.md, HANDOFF_parked_positives.md, HANDOFF_ci.md,
HANDOFF_edge_audit.md, and **live product copy in `valuation/web/payoff.py`, which was rendering
−6.65pp to users**. Also corrected: the breadth count is 132 names, not the 133 CLAUDE.md said.

**Still open, owned elsewhere.** O20's `z −3.475` does NOT reproduce — the construction that
reproduces every other O20 figure gives −4.8953 as published — and it appears in no shipped
artifact, so it is recorded as unreconciled rather than silently replaced. **Owner: the O20
lane.** Separately, the path study, O1/exitlab and the autopsy were NOT re-run split-clean; their
inputs move by the same 15 rows and no verdict of theirs rests on a margin that small, but
re-banking them is the owning lane's call.

**Accounting.** Zero trials — a correctness repair tests no hypothesis. Options `N` stays **210**.
Equity `N` is untouched *by this work* but is no longer 149: it read 143 when U1 opened, 149
mid-session, and **151** at close, because other lanes landed while this ran. **Always re-read it
from `research_log.detail()` rather than copying a number out of a handoff** — a stale `N`
overstates every DSR-gated claim, and this file has now watched it move twice in one day.
Expectations scored 6 right, 1 wrong. Test gate: 52 suites, 0 failing.

**Recommended next step.** U2 (options surface → stock signals) is now the only untested direction
of the unification, and it does not inherit U1's horizon mismatch.

## 2026-08-11 — options bot, session 23 (U1): the equity edge does NOT reach the options book, and a split defect moves R2 by 24%

**U1 is REJECTED.** It was the ledger's oldest blocked unification item and the first test of
whether the composite — the one thing here that survives calibration — is worth anything on the
options side. It is not, at this horizon.

**The ledger's reopen condition was met both ways at once.** `U1` said *reopen only with a
composite built WITHIN the options universe **or** with size neutralised*. This did both:
rankings are percentiles among the ~182 optionable names as of the same rebalance date, and the
primary null is drawn **matched on market-cap tier per date**.

**Design.** One grid mined once — 182 names × 39 rebalance dates, 6,811 cells → 5,186 trades —
with every arm and every null draw a **subset of it**, so arms cannot differ by fill, contract,
exit or calendar. Entry is the first trading day **strictly after** the rebalance (the U7
backward-looking join). The shipped +100/−50/half-DTE exit is called, not copied. Pre-registered
alone at `7d7c414`; bars committed at `e34dc9d` with the scorer not yet written.

**Result.** Against a grid earning +3.6516%/trade, the top decile (n=486) gains **−1.1892pp**,
sits at the **31st percentile** of its plain null and the **15th** of its cap-matched one, and
**fails all four** pre-registered conditions. Calibrated bars were +7.2870pp (plain) and
+9.4513pp (cap-matched), p95 of 200 shape-matched draws.

**The mechanism is cleaner than the verdict: every decile's MEDIAN trade is between −52.5% and
−54.3% — all ten.** The composite does not move the typical option trade at all; every decile
difference lives in a right tail that the bar calls noise. The top decile's mean is entirely
tail-carried (best five trades = 158.9% of it).

**On R2's standing statistic the top names are significantly WORSE**: paired name-year sign test
within (ticker, year), TOP10 wins 41.8% (z −2.7840, p 0.0054), TOP20 42.9% (z −3.1203, p 0.0018).
No calibrated bar exists for that statistic, so those p-values are conventional.

**The bottom decile clears both bars at the 99th percentile and is NOT a finding** — its
date-block CI includes zero, it is carried by the late half, and its sign test is 52.0% at
p 0.47: it does not win more often, it wins bigger. The decile table is **unordered, not
inverted** (D9 worst, D10 best). Do not act on it.

**BUG, cross-lane, and it moves a published number — `U1-SPLIT`.** Option chains are as-traded
and unadjusted for splits while bars are adjusted, and nothing in the options lane has ever
consulted the split table. GE's 1-for-8 reverse split (2021-08-02) turns a $0.27 call into a
+31,921% "winner" worth 6.28pp of the raw grid's 9.93% mean. Measured on the banked books:
**R2's gap goes −6.6468pp → −5.0640pp, so 24% of the published gap is a corporate-action
artifact.** The control is hit ~12× harder than the alert book, so **the defect has been making
R2 look worse than it is**. R2's sign and verdict are unchanged — the alert still loses
decisively — but **quote −5.06pp**. **The repair belongs upstream in the miner and is NOT DONE.**

**Nothing live changed.** No policy, no weight, no constant.

**Accounting.** Options `N` 207 → 210 (three scored arms; the mine and both calibrations charged
zero). **Equity `N` is 149, not 143** — S23 landed mid-session and a stale `N` overstates every
DSR-gated claim. Test gate: **46 suites, 0 failing.**

**Recommended next step.** Either (a) repair `U1-SPLIT` at source in the miner/replay path and
re-bank the affected options artifacts — it is the only open item that changes an already-quoted
number — or (b) take U2 (options surface → stock signals), which is now the only untested
direction of the unification and does not inherit U1's horizon mismatch.
## 2026-08-11 — greeks lane: the KSPI leak, fail-closed publication, and the one f-string that kept all of it off production

**Everything below had been finished, tested and pushed for a day, and NONE of it was live.** The
branch would not land, `main` took five other lanes past it, and every local check was green. The
cause was one line — and it is worth reading before the results, because the same trap is open to
every lane.

**THE BLOCKER: the tree did not parse on the CI Python.** `scripts/live_theme_sources.py:776` used
`f'{k} {v['fetched']}'` — an f-string reusing its own quote inside the expression. PEP 701
legalised that in **Python 3.12**; the land workflow pins **3.11**, where it is a hard
SyntaxError. The module could not be *imported* on the runner, so all 53 tests in its suite died
at collection while every other suite stayed green — which is why CI named exactly one file and
nothing else. **The pre-push check that missed it named a version it could not enforce:**
`ast.parse(src, feature_version=(3,11))` is best-effort and does not gate tokenizer-level changes.
A version claim needs a compiler of that version; the official 3.11 embeddable distribution needs
no install and no elevation. **A repo-wide guard now checks this in two halves** (compile under the
running interpreter, which fires on CI; plus a tokenizer scan that fires locally before a push).
Note the shared surface: the guard scans the **whole tree**, so another lane's 3.11-incompatible
file will now redden `tests/test_live_theme_sources.py`, with the offending file and line named.

**LA1 — the product's #1 name published a fair value its own engine refuses. FIXED AND VERIFIED ON
PRODUCTION.** KSPI served `fair_value 274.13` with `withheld: false` while the engine refuses it at
5.6x. It was **four names, not one** (KSPI, DB, CIB, EC — all foreign issuers needing an FX hop),
and the fail-open published up to **2.1x the model's own valuation** (DB 88.69 served against
42.25; CIB 167.42 against 90.93). Today's production scan serves **KSPI at rank 4 with
`fair_value: null`, `method: "withheld"`**, 5 withheld rows, 0 band breaches. **The finding
underneath is bigger than the bug: the refusal screen is Yahoo-quota-bound and had been degrading
silently since it shipped** — the 2026-08-08 scan recorded ZERO refusals across 500 names. It is
now counted and loud on every scan, not closed.

**FAIL CLOSED, adopted on Don's decision 2026-08-11.** A row whose data could not be fetched now
publishes **no** fair value. The two silences are different claims and no longer read as one:
`refused` is about the *valuation* and is stable; `unavailable` is about the *fetch* and is
**temporary** — the quota resets and the next scan retries it, which the reason text says out
loud. They render differently (`no data` vs `withheld`), and the kind survives the database in its
own column so they cannot converge on the way to the browser. Cost ~5% of served rows, accepted.
The per-scan withheld-for-no-data count is now in the scan health block, so quota degradation is a
number. The mop-up pass stays **OFF** — measured, it made things worse (no_data 13 → 32; the
binding constraint is cumulative quota, not concurrency).

**LA3 — the track annualised on row count while missing 71% of its days.** Now annualises on
**elapsed trading days**. On the audit's three-way thinning of one identical year, `ann_alpha` was
24.59% / 56.08% / 96.62% and is now **bit-identical at 24.5861%** across all three. The complete
series does not move. **The gate deliberately stays on recorded rows** — moving `MIN_LIVE_DAYS`
onto elapsed time would let a gappy track reach the floor sooner, which is the flattering
direction. Sharpe is rescaled by the true span and **withheld** below 50% coverage rather than
corrected.

**V2G — free live sources for the three dead themes. BUILT, MEASURED, NOT SHIPPED.** Part 12 found
42.9% of deployed composite weight reaches no live score. From free public data (13F structured
data sets, XBRL company facts, the repo's fixed Form 4 scraper): `institutional` 0 → **411/500**,
`capital_discipline` 0 → **456/500**, `insider` 1 distinct value → **297**. Deployed weight
reaching a live score: **56.5% → 95.5%**. All five pre-committed bounds held.
**NOTHING WAS ADOPTED AND A TEST ENFORCES IT** — no file under `valuation/` was touched. Under
Amendment 1 Rule 6, adopting these would **close vintage 2, open vintage 3 and reset the entire
accrued forward clock for no statistical gain**. Do not shortcut that from a green coverage number.

**THE SCREENER LA BATCH — LA4, LA5, LA7, LA9, LA12, LA14, all six verified against the code
first and all six real.** **LA4:** the snapshot was stamped AFTER the scan, and the 23:41 UTC
backup cron sits 19 minutes from UTC midnight — so a slow backup dated the snapshot the next day,
and because idempotency keys on `hot_processed_{scan_date}`, the "no-op" backup wrote a **second
forward-track pick row for the same close** and posted the Discord digest **twice**. **LA5:** the
scan's `health` and `filtered` blocks were computed, logged, and then dropped at the only boundary
that persists them — **this is why LA1 and LA6 were invisible**; a scan reporting zero refusals
across 500 names it could not reach had no way to say so. **LA7:** the staleness guard called a
Saturday "last close" and counted Christmas as a trading session, and its own docstring argued for
the opposite of what it did. **LA9 was marked HYPOTHESIS by the audit and is CONFIRMED TRUE:** the
scheduled hot scan passed no broker token, so it ran the EDGAR fallback universe — no price, no
market cap, no size ordering — while the job's comment claimed the broker's liquidity-ranked one.
Passing the token alone would have silently pointed it at the *sandbox*, so the env goes with it.
**LA12** and **LA14** are smaller: a sector median computed over 1–2 valued names beside a
full-sector count, and a holiday set containing a date from the previous year.

**Two of these were self-inflicted and are recorded as such.** LA7's fourth defect — two
`trading_days_between` functions with the same name in sibling modules returning different answers
— was created by this lane's own LA3 work days earlier. And while writing the ledger rows, an
unescaped `|` in a note split the row and made it **vanish** from `read_ledger`; chasing that found
that `--write` re-renders from that dict and would therefore have **deleted** it. Three rows are
affected today (`S23`, `M1-PARSE`, `V2G`) — all other lanes', **reported rather than rewritten**,
with a fail-closed guard now stopping the deletion.

**Cowork note:** nothing here needs you, but two items change what you will see. Scans dated a
non-trading day now carry a visible "not a trading session" note instead of a green badge, and the
next scheduled hot scan is the first to run on the broker universe — expect the served list to
change composition, and that is the fix working, not a regression.

**THE THEME RESTORATION — 1 OF 3 THEMES RESTORED, AND THE PROJECT'S FIRST VINTAGE EVENT.** The
live book scored 4 of 7 weighted themes and failed the calibrated long-short floor (1.8811 vs
2.2837) while the validated seven-theme composite clears it (2.6199). Adopted on COHERENCE — live
must run what was validated — but gated on FIDELITY first, because the live sources are raw-EDGAR
approximations of the panel's licensed themes and wiring a different theme under a validated
theme's name would have hidden the problem rather than fixed it.

**`capital_discipline` RESTORED at Spearman +0.8421** against the panel's own theme (n=416).
**`institutional` (+0.1706) and `insider` (+0.3596) FAILED and are deliberately still absent.**
The bar was max(0.60 floor, P95 of correlation between *different* panel themes = 0.3590).
**`institutional` scored below the median correlation between two different panel themes** — it is
statistically indistinguishable from a different theme, despite passing every one of its own
coverage bounds. Coverage was never the question. Both are recorded with exactly what would fix
them (an SF3 construction reconciliation; a date-aligned historical Form 4 crawl).

**VINTAGE 2 IS CLOSED. VINTAGE 3 IS OPEN, dated 2026-08-11.** Under Amendment 1 Rule 6 the accrued
forward clock resets and buys nothing statistically. Because `track_meter.INCEPTION` is derived
from the open vintage, the reset applied itself: **operational gate 2027-02-10 → 2027-02-11,
verdict date 2031-08-10 → 2031-08-11**. **It cost ONE DAY** — vintage 2 had accrued a single day —
which is the entire argument for doing this now rather than later. `PAPER_TRACK_CONTRACT.md` §5a
carries the new vintage row and the reset table; Amendment 1's own rows are NOT rewritten.

**V1's shadow machinery fires for the first time.** One pair — live vintage 3, shadowed by vintage
2's four-theme composite — opened 2026-08-11 with **0 complete paired months against a minimum of
6**. It is research-only and fenced off every public surface. **A shadow pair that has not crossed
is the EXPECTED outcome and is not evidence the adoption was worthless**; the module now says that
in its own output, which it did not before today.

**Cowork note:** the hot list's composite changes from today — `capital_discipline` now
contributes 12.5% of the weight where it previously renormalised away. Expect the ranking to move,
and that is the fix working. Nothing about the backtest's published figures changed; this changes
what LIVE computes.

**State: landed on `main` and deploying. Full gate 53 suites, 0 failures.** Detail in
`HANDOFF_live_data_bugs.md` Parts 13–17; ledger rows `THEME-RESTORE`, `V2G-SRC`, `LA1-LA3`, `CI-PY311`, `LA4`, `LA5`, `LA7`, `LA9`, `LA12`, `LA14`.

---
## 2026-08-11 — edge lane, session 20 (`SECTOR-NEUTRAL-B6`): rejected again, and the trade-off it rested on is gone

**Item B of `HANDOFF_parked_positives.md` is CLOSED — REJECTED on the panel the project actually
uses.** Sector-neutral ranking had been rejected twice (P10 2026-07-31, 2026-08-02), but **both
rejections ran on the pre-B6 110-date / 2,710-name panel the project has since declared void**:
the decision turned on a **−1.58pp alpha difference measured inside a panel whose alpha LEVEL
moved −4.18pp** when B6 removed the inverted universe. That was the parked-positives sweep's own
finding and the reason this needed no new data.

**`PREREG_sector_neutral_b6.md` was committed ALONE at `1bdb7e0`**, a strict git ancestor of the
measurement commit. The gate is **the shipped `holdout_compare_panels` with the margins already in
the repository** — +0.25 long-short *t* AND +100bps alpha, required in **BOTH** halves with the
boundary embargoed — under **two** pre-specified weightings and no others.

**REJECTED under both weightings, failing in both halves.** Deployed: top-decile alpha
**+7.1741% → +6.0852%** (−1.0890pp), long-short **+11.04% → +8.51%**, long-short *t*
**2.8361 → 2.3423**, HAC **2.6199 → 2.1505**, monotonicity −0.8909 → −0.8667. Early half
Δ*t* −0.0093 / Δalpha −0.1459pp; late half −0.4846 / −2.0144pp. Flat weights: same answer.

**THE FINDING IS NOT "IT FAILED AGAIN" — IT IS HOW.** On the void panel sector-neutral **BOUGHT
long-short *t*** (3.396 → 3.896, **+0.500**) and **sold alpha**, so the rejection was a *judgement*
that a long-only book should not make that trade — and anyone disagreeing with that preference
could have re-opened it. **On the corrected panel the gain is GONE AND REVERSED** (−0.4938
deployed, −0.3000 flat): worse on **both** metrics, under **both** weightings, in **both** halves,
so **there is no trade-off left to adjudicate.** The sector-neutral arm also **drops below the
calibrated long-short HAC floor (2.1505 vs 2.2837)** while the shipped arm clears it at 2.6199.

**Design improvement on both prior runs: ONE panel build, two arms, a provably identical row set.**
Each cross-section calls `build_frame` twice on the same `metrics` list, so the **`insider`
nondeterminism the project has recorded is common-mode and cancels** instead of landing inside the
difference. All seven controls pass, including **sector coverage RE-MEASURED on the corrected
panel — 100.0%, 11 sectors, smallest sector 50 names, ZERO singletons** (the 100% in the record was
measured on the void panel), and the flat arm reproducing the published record **to the digit**.

**A DEFECT FOUND, REPORTED, NOT REPAIRED — and it corrects a claim in the record.**
`cross_sectional.zscore` guards degeneracy with `sd == 0`, but whether a constant column has an
exactly-zero pandas variance is **value-dependent**: exact for 0.0 / 50.0 / 2.5 / 0.125, ~1e-16 for
**0.9 / 0.1 / ⅓ / 12.34**. When it misses, `zscore` returns **a fabricated pattern with max |z| = 1
built from floating-point residue, not NaN** — so a constant signal does not reliably neutralise
itself. **V2G's "a constant `insider` makes `zscore` return all-NaN" is true only because the live
`insider` is constant at exactly 0.0 (`(50−50)/25`); it is not a general property.**
**Exposure measured, not assumed: nil** — no theme column is degenerate on any of the 69 dates and
the smallest within-sector dispersion over 231 cells is 0.2209. **Not repaired because `zscore` is
on the live scoring path, so changing it is a scoring change and therefore a VINTAGE EVENT**; it is
pinned by a test that fails if it is ever silently corrected. **→ Owner: whoever takes a scoring
vintage next; it is not this register's to make.**

**CLOSED PERMANENTLY by a clause fixed before the run.** Full sector-neutral ranking may **not** be
re-run as a re-run. Re-opening requires **new data** — `S25`, a genuine point-in-time sector map
(TICKERS is *today's* classification, the one non-point-in-time input in the panel) — or **a
materially different construction** — `S15`, sector-relative on the **value theme alone**, never
tested at all. Both ledger rows were blank and are now scoped. **Nothing here touches the sector
column's ACCEPTED use for the `max_sector_w` concentration cap, which is a risk control rather than
a re-ranking.**

**Equity `N` 149 → 151**, √(2·ln 151) = 3.1677; `BACKTEST_RESULTS.json` re-run from a clean tree so
the artifact matches the denominator. **ADOPTS NOTHING — `CONFIG.sector_neutral` is untouched at
`false`**, and adoption is a vintage event and Don's call. Four of five pre-registered expectations
were right and one split. Suites green: `test_edge.py` **288/288**, `test_sector_neutral.py`
**8/8**, all 40 suites.

**Recommended next step for this lane:** nothing here needs a follow-up. `S15` (sector-relative on
value alone) is the cheapest untested idea left and now inherits this result as a prior against it;
it needs its own register, not a re-run.

## 2026-08-11 — options bot, session 22 (TP-BAR): Don chose Option 2, and item A closes REJECTED

**Don's decision, with its date: Option 2 of `PREREG_A_take_profit_bar.md`, taken 2026-08-11** —
decide the take-profit raise against a bar that is MEASURED rather than chosen. C1–C4 were run
exactly as pre-registered. **No policy changed. The paper options book keeps +100% target / −50%
stop / half-DTE time stop. Item A is CLOSED, not re-parked.**

**THE CALIBRATED BAR IS +5.0812pp** — the p95 of 100 jittered draws from the arm's own family
(target 0.50–2.00, stop −0.30 to −0.70, time fraction 0.25–1.00, endpoints read off
`options_exitlab.POLICIES`, seeds 1000–1099, identical frozen paths and scorer, every draw paired
on all 3,885 trades). Null min −6.786, p5 −4.570, median +0.803, max +8.111, **53 of 100 draws
beat the shipped exit**. **The bar was committed ALONE at `e8e5505` with the scoring module not
yet written**, so bar-before-arm is visible in the history rather than asserted.

**VERDICT REJECTED, and both arms fail C1 and ONLY C1.** `tp150` gains **+3.1948pp** and sits at
the **82nd percentile** of its own family; `tp200` +3.8238pp at the 87th. C2 passes against the
memo's own prediction that it would be the hazard — winsorising the top 1% of per-trade
differences caps 39 trades at +124.3pp and `tp150` still retains **77%** of its gain (+2.4511pp),
so the raised target is **not** tail-driven. C3 passes (+2.5969pp on the five pooled random
seeds). C4 passes (FDR discovery, paired sign z +7.93 signal / +8.09 random, both halves positive
on both books, PBO 0.00).

**THE HARNESS REPRODUCES THE RECORD INDEPENDENTLY:** this scorer was written for the path study,
not for O1, and returns shipped at **+3.410308%/trade** with gains of +3.1948 / +3.8238pp against
O1's banked `expectancy_diff` 0.031947661 / 0.038237652 — the same figures to four decimals from a
separately written path rebuild.

**WHAT THE REJECTION DOES NOT SAY, because it is easy to over-read:** it does **not** say raising
the take-profit does nothing. Every non-calibrated condition says the effect is real, broad and
entry-independent. It says the arm is **not distinguished within its own family** — 53 of 100
arbitrary jitters also beat the shipped rule, the best five by +5.2 to +8.1pp, all the same
wider-stop/higher-target/longer-hold shape. When a whole REGION looks good on one corpus, that
corpus cannot say where inside it the optimum is, and picking one point after five looks is
choosing by hindsight.

**BY-PRODUCT UNFLATTERING TO THE INHERITED RULE, reported because it cuts that way:** the shipped
+100%/−50%/half-DTE exit sits slightly **below** the median of its own family (beaten by 53 of
100, +0.803pp at the median). It is an ordinary member, not a local optimum — and it **cannot** be
acted on for exactly the reason `tp150` was refused, so this exercise must never be quoted as
having validated it.

**THE PRE-REGISTERED EXPECTATION WAS WRONG THREE TIMES OUT OF THREE** (bar called at +1 to +4pp,
landed +5.0812; `tp150` called to clear, failed; `tp200` called to fail C2, passed it).

**THE DEAD-ENTRY CAVEAT TRAVELS:** R2 stands — the alert book loses to random entry by −6.65pp —
and no exit rule makes it tradeable. **Charged 2 trials; options `N` 205 → 207.** The calibration
is charged zero (X7 / HAC-floor precedent). **Equity `N` untouched by this work but now reads 143,
not 135**, after S22 landed from another lane. `rows_malformed: []`.
`scripts/tp_bar.py`, `scripts/tp_bar_score.py`, `tests/test_tp_bar.py` (16),
`tests/test_tp_bar_score.py` (14); `PREREG_A_take_profit_bar.md` §§8–9.
## 2026-08-11 — edge lane, session 19 (S23): the exit rule raced, and nothing beats the incumbent

**Ledger S23, registered blind** in `PREREG_s23_exit_rule.md` at `6a73485`. One buy rule and an
identical `min_hold` across every arm; only the exit differs. Both TP/SL pairs named from
published convention **before any run**, and no grid swept.

**NO CHALLENGER BEATS THE INCUMBENT.** Fair-value point, fair-value lens band, O'Neil +25/−8 and
2:1 +20/−10 all move the book by **under 0.4pp/yr in either direction** net of costs on 69 paired
periods (|HAC *t*| ≤ 0.87), and **three of the four flip sign between halves** — including the only
positive one, which is exactly what the both-halves requirement exists to catch.

**The one measurable effect is the control: never selling costs 10.89pp/yr
at HAC *t* -3.801**, the book growing to 417 names as
alpha collapses 15.48% → 3.37%.
**That CONFIRMS S22 rather than contradicting it** — S22 measured one cohort over ~8 quarters,
while a never-sell book keeps buying and converges on the universe. **Dilution, not friction.**

**Three defects found and fixed**, each reported in its own right: `build_valuation_panel` still
carried the **B6 per-ticker tail** (110 dates from 1998-12-31 vs the corrected 69 — **any prior
calibration conclusion wants re-running**); the point-in-time valuation was **fetching live Yahoo
prices** through the beta ladder's corroboration rung (157 calls per 1,122 rows), now behind an
offline mode that asserts zero network calls; and `_backtest_hold` extracted a column **once per
name instead of once per date**, costing 61 of every 70 seconds — fixed, and **proved bit-identical
over 1,818 leaves**.

**Nothing adopted and no vintage opened.** Equity `N` 143 → 149.

## 2026-08-10 — edge lane, session 18 (S22): the edge does not decay over two years, but the long-short does

**Ledger S22, registered blind** in `PREREG_s22_term_structure.md` at `6b187dd` — committed alone,
a strict git ancestor of the measurement commit. Every **headline** figure this project publishes is
measured at a single 63-day forward window because the panel computes one `fwd_ret` and the
deployed rebalance equals it. (**The register's own premise overclaimed and is corrected in the
handoff §1b, not edited away:** a `per_horizon` block at 63/252/756 has always existed, but it
reports IC only and moves the rebalance period with the horizon — 69 dates vs 18 vs 6. Its
out-of-sample IC nonetheless **rises** with horizon, 0.0390 → 0.0582 → 0.0977, corroborating this
result from the project's own unread artifact.) Eight horizons (1–8 quarters) were scored from **ONE** panel build,
because the grid end is `len(cal) − horizon` and a build per horizon would have varied the horizon
**and** the date set **and** the cross-sections together.

**VERDICT CONSTANT-RATE.** Annualized top-decile alpha is **essentially flat from three months to
two years — +6.59% → +5.10%** — cumulative alpha reaching **+10.20%** at eight quarters,
`R(8) = 6.195` against a pre-registered ≥6.0 bar. The alpha HAC *t* **never drops below 3.16** at
the overlap-corrected lag, and median rank IC **rises** with horizon (+0.034 → ~+0.072).

**The constraint that must travel with it: the long-short spread decays and its significance
collapses** — HAC *t* **2.7167 → 0.6846**, cumulative spread peaking at Q5. **The persistence is
entirely in the LONG leg**, which is the leg the shipped long-only hot list actually delivers — but
**the long-short research statistic and the product statistic diverge with horizon**, and the
record has been quoting them side by side. No long-short figure may be quoted beyond about a year.

**Reported because it cuts against the verdict:** the classification clears its bar narrowly (6.195
vs 6.0) and **does not replicate across halves** (early 8.559, late 5.470). Both halves agree in
sign and both still show alpha accruing at two years, so **the persistence replicates and the label
does not**.

**Tenure: the top decile turns over almost completely every quarter.** Kaplan–Meier median spell is
**ONE rebalance (~3 months)**, **70.6% of spells last exactly one**, one-period retention **36.6%**
— inside the 20–50% band pre-committed from the shipped 261%/yr turnover, so tenure and the cost
model describe the same book. **Re-entry is the norm** (74% of names have more than one spell), and
**small caps stay longest**, the opposite of the pre-registration. A per-horizon placebo was built because X7's floors do not transfer across configurations (8 of 8 horizons clear their own alpha floor, 4 of 8 their own long-short floor); it is a deliberately less conservative null than X7's and is labelled so in the artifact.

**Nothing was adopted.** A rebalance-frequency change is **S23's** own register and a **vintage
event**; display is the **web lane's**. The defensible product sentence is written in
`HANDOFF_edge_audit.md` session 18 §6, with the caveats it may not be shown without.

Equity `N` 135 → 143. **40/40 suites green** (`test_edge.py` 275/275, +9 S22 tests).

## 2026-08-10 — r1 lane, cold-audit LA2: the track backup was backing up the wrong book

**FIXED.** The weekly `track-backup` workflow preserved 4 days of the Tradier **sandbox** engine
and **ZERO rows of the contract-bound Valquo Index** — the record `PAPER_TRACK_CONTRACT.md`
actually binds. Its anti-regression guard counted the sandbox file, so the bound series could go
from two rows to zero without tripping anything; **the job was green throughout**, because zero is
never fewer than zero.

The workflow now ingests the bound series from every place it can live and merges by date (an
empty source can never erase a populated one), writes it as its own `valquo_index_track.csv`,
guards on **its** row count plus an absolute presence check, and the emitted README no longer
labels the sandbox file "Valquo Index vs SPY" — the exact mislabel behind the false "Index beating
SPY" Discord post of 2026-08-05.

**The two bound rows are now committed to git** (2026-07-31 −0.2777pp, 2026-08-06 −2.8468pp, 86
names), so the record no longer exists on one laptop only. **`data/` is untouched and still
gitignored** — the licensed-Sharadar rule is not bent; the copy lives in the already-tracked
`data_export/`. It is a **backup, not a second recorder**: `index_track.load()` still reads `data/`
and only `data/`.

New `tests/test_track_export.py` (**18 tests**; the module had none), including a real restore that
reproduces the published −2.8468pp. **34/34 suites green.** Full write-up: `HANDOFF_ci.md`, LA2.

**NOTHING CHANGED ABOUT WHAT THE SITE SAYS OR WHAT THE CONTRACT BINDS.** And the gate's real
blocker is unmoved: **there is still no automated writer for the bound series** — LA2 does not
cover it. Trial cost none; equity `N` stays 131.

**Session date:** 2026-08-09 (external edge audit, **session 15** — **AMENDMENT 1**: run #1 is
VOID, **run #2 is the live test from 2026-08-10**, and the project now has a **VINTAGE RULE**.
The meter and gap report are wired into `/api/track`. **NO ACTION REQUIRED FROM DON, but one
thing needs confirming: the Cowork writer `valquo-daily-track-write` is NOT visible in this
machine's Task Scheduler.** It is checkable from 2026-08-12 with no further work.)
**Session date:** 2026-08-10 (edge lane, **session 17** — measured what the three dead live themes
cost: **IMMATERIAL on alpha (−1.31pp, not separable from zero), but the live four-theme book fails
the calibrated long-short floor**. **NO ACTION REQUIRED FROM DON.** One item still needs confirming
from 2026-08-12, unchanged from sessions 15 and 16: whether the Cowork writer
`valquo-daily-track-write` is actually running.)
**Branch:** `worktree-options-live`, auto-lands to `main` via CI

---

## GREEKS LANE — 2026-08-10 (V2G): the three dead themes now have free live sources, and nothing was shipped

**NO ACTION REQUIRED FROM DON.** Read `HANDOFF_live_data_bugs.md` **Part 13**.

Follow-up to Part 12, which found that **42.9% of the composite's deployed weight reaches no live
score**. This session built a **free, public** source for each of the three dead themes and
measured its coverage. Pre-registered alone at `66310e7` before any code existed.

**All three sources are free.** The brief's premise is right and it is what makes this possible:
**SF3 is a licensed aggregation of 13F — the underlying filings are public record.** Nothing here
touched the licensed Sharadar exports.

| theme | before | after (vs the same 500 served rows) |
|---|---|---|
| `institutional` | null on 500/500 | **411 / 500 = 82.2%**, 410 distinct values |
| `capital_discipline` | null on 500/500 | **456 / 500 = 91.2%**, 441 distinct values |
| `insider` | present but **1 distinct value** | **500 / 500**, **297 distinct values** |

**Share of deployed weight reaching a live score: 56.5% -> 95.5%** (mean over 500 names).
**All five pre-committed bounds held**, including the falsifiable external-validity one: the
most widely held served name is NVDA at **5,775 distinct institutional filers**, and holder
breadth correlates with size at Spearman **+0.539**.

**NOTHING WAS SHIPPED, AND THAT IS THE POINT.** Zero files under `valuation/` were touched — so
no composite change, no weight flip, and **no vintage event**: vintage 2's clock is untouched. A
test enforces it rather than prose promising it, so a later change that quietly wires one of
these in fails the suite.

**ADOPTION IS A SEPARATE AND EXPENSIVE DECISION, AND NOBODY SHOULD SHORTCUT IT FROM THESE
NUMBERS.** Coverage says the data exists; it says nothing about whether it predicts returns. That
needs the held-out gate at the standing margins in both directions, plus the pipeline builder's
cost measurement — and under Amendment 1 Rule 6 an adoption **closes vintage 2 and resets the
entire accrued forward clock for no statistical gain**. Vintage 2 is one day old, so that price
is at its cheapest today and rises every day the decision is deferred. That is an argument for
deciding soon, not for deciding casually.

**Found in my own instrument, and reported rather than smoothed over:** the pre-registered
ownership anchor was **one-sided** — it rejected implausibly high institutional ownership and
waved through implausibly low, passing **12 megacaps (CMCSA, RIO, BTI, HSBC and others) joined to
a CUSIP with a single reporting holder**. Fixed with a structural floor; both the pre-registered
(421) and tightened (411) figures are published rather than one replacing the other.

**Two corroborations worth carrying:** the live insider theme is overwhelmingly a *"who is
selling least"* sort (278 names below neutral against 43 above), and **16 names pin at exactly
the scorer's `tanh` floor** — audit item **S3**'s saturation mechanism, confirmed on live data.

**Tests: 38 suites, 0 failures.** Zero trial cost for this run; the denominator in force is
**`N` = 135** after the pipeline builder's parallel item. **5 bugs reported.**

**Read alongside the pipeline builder's session 17**, which landed while this was fetching and
priced the same gap: the return cost of the three dead themes is **immaterial by its own rule**
(Δ −1.31pp, paired HAC t −1.40) **but only at 55% power**, and the live four-theme book **fails
the calibrated long-short floor** while still clearing the long-only alpha floor. Their
exploratory decomposition reorders this work: **`institutional` (13F) is the one to build first**
— it is the only theme whose absence hurts in both halves — while `capital_discipline`, the
cheapest to wire and the best covered here at 91.2%, has the *least* evidence it helps.
**The reason to build these is claims integrity, not alpha:** the live product computes a
different composite from the one every published figure is measured against.

**Recommended next step, and it is not mine to take:** decide whether to adopt. If yes, it is a
scoring change and belongs to the screener/edge lanes with the held-out gate attached; V1 shadow
vintages is already registered and blind and is the instrument that would measure whether the
adoption helped.


---
## ITEM A / THE TAKE-PROFIT BAR (options-bot lane, 2026-08-10) — **A DECISION IS WAITING ON DON**

Memo: **`PREREG_A_take_profit_bar.md`**; ledger row `TP-BAR`; write-up in
`HANDOFF_optionsbot.md`. **It changes no policy and ends at Don's choice**, exactly as the
paper-track contract did. **The dead-entry caveat attaches to every option, including "adopt":
R2 stands, the alert loses to random entry by −6.65pp, and no exit rule makes this book
tradeable.**

Raising the take-profit +100% → +150/200% has been measured twice and refused by a **+10pp**
bar that was set for adopting a *construction* change. Reconciled: look 1 (2026-08-03) gives
+2.11/+3.26pp, look 2 (O1 off the freeze, 2026-08-08) gives **+3.19/+3.82pp**, and the path
study's same-direction arms (+1.50 to +3.60pp) lean the same way without clearing. **The
inventory's "two independent runs" is too strong** — the two books share 1,099 trades (28.3% of
the larger) and the path study runs on the larger one exactly.

**Why the bar was wrong, from the distribution:** of all **33** exit arms ever scored on this
book, exactly **one** clears +10pp — `tp100_only` — and it fails FDR, raises tail concentration
to 92.75%, and fails its own sign test on the alert book. The unit is the deeper problem: the
**top 1% of trades carry 106–210% of each arm's entire gain**, so the other 99% are collectively
negative. **And the obvious fix is refuted** — a *relative* bar drifts +62%/+109% between the two
books where the absolute gain drifts +17%/+52%, so absolute is the more stable unit.

**The memo pre-registers a procedure, not a number** (calibrate the level as X7 did; add a
condition that does not run through the mean), and notes the timing fact: the paper options book
has **three open positions and ZERO closed trades**, so a change now breaks no forward-record
continuity — which makes adopting *cheap*, not *right*, and expires with the first close.

**Don's three options are in `HANDOFF_optionsbot.md` §5.** Recommendation on record: **option 2**
— require one calibrated confirmation, then decide. Zero trials; options `N` stays 205.

---

## THE PATH STUDY (options-bot lane, 2026-08-10) — NOTHING CHANGES, AND THAT IS THE RESULT

Full write-up in `HANDOFF_optionsbot.md`; ledger row `PATHSTUDY`; pre-registration committed at
**`9d37241` before a single table existed**, stage-2 arm set included.

**THE CAVEAT IS LOAD-BEARING: the options entry signal is dead (R2, unchanged). Nothing here is
a tradeable-edge claim** — it is paper-book policy and structural knowledge.

**The harness reproduces the record twice**, which is what makes the rest quotable: paths rebuilt
for **3,885/3,885** banked trades and **29,783/29,785** control trades from the frozen chains,
and replaying the shipped policy reproduces the banked book on **3,885/3,885 exit reasons and
P&Ls to 1e-9**, at **+3.41%/trade** signal and **+10.06%/trade** control — both R2's figures to
the digit. (`data/options_exitlab/paths.pkl` covers only 28.3% of the book and is a different
trade set; it was not used.)

**STAGE 1 — the answers.** 80.2% of trades touch −50% at some point, and a −50% touch cuts the
chance of ever reaching +100% from **44.7% to 17.5%**, so the inherited stop sits at an
informative level. **Recovery depends far more on TIME than on level**: from a −50% touch,
9.2% get back to breakeven with under a week left against **41.6%** with more than 45 days.
Winners are fast — median **20 days**, a third of the DTE — and **67.6%** of targets arrive with
more than half the DTE unused, so the time stop is not cutting winners short. **After +100% it is
a barbell that vindicates closing there:** 67.5% of early winners double again, but **83.2% give
back the +100% and 58.0% end up below zero.**

**STAGE 2 — REJECT, 13 pre-registered arms.** Largest gain **+3.60pp against O1's own
pre-committed 10pp bar**; both split directions select the same arm and neither measured half
clears; both clustered CIs straddle zero. **The finding that outlives the verdict:** on the five
pooled random-entry seeds, every arm moves a book of RANDOM entries almost exactly as much as the
alert's — **r 0.967, slope 0.990, 13 of 13 same sign** — so an exit rule is a property of
*options*, not of the entry. That generalises O23 from "half" to essentially "all".

**DON: no action, and nothing was deployed.** The plain-English answers to the four questions are
in `HANDOFF_optionsbot.md` §4. Options `N` 192 → **205**; equity `N` unchanged at **135**.

---

## LA15 (options-bot lane, 2026-08-10) — THE TEST SUITE NO LONGER WRITES INTO THE REAL DATABASES

First executed item from `VALQUO_LIVE_AUDIT.md`. Full write-up in `HANDOFF_optionsbot.md`;
ledger row `LA15`. **Scope was `tests/**` only — no production module was edited.**

`tests/state_isolation.py` redirects the screener store, the accounts store, the dated scan
archive and the index-track files into a per-process temp directory, and **raises** on anything
still resolving inside the real `data/` — redirection alone fails silently, which is the failure
mode this item is about. `tests/test_state_isolation.py` (**29 tests**) pins the rule and fails
the gate if any suite can reach default state without importing the guard.

**The audit named one row; the measured blast radius is six, across five tables.** One run of
`tests/test_saas.py` also left an `alerts_sent` row for `__HOTDIGEST__` stamped with the **real
calendar day** — `notify.post_hot_digest` returns early on `alerted_today`, so a local test run
**suppresses that day's real Discord hot digest**. A fingerprint sweep around each of the 37
suites found **four** mutating, three unnamed by the audit: `test_security.py` → `data/app.db`,
`test_screener.py` → `data/archive/scans/<today>.json.gz`, `test_private.py` → opens the real
store. **Re-running the identical sweep after the fix: every suite `rc=0`, mutation list empty.**

**Two findings travel further than the repair:**

1. **The local scan archive is 100% test output and self-refreshing.** Every archived scan day —
   5 of 5 here, 3 of 3 in the primary checkout — is `provider: "synthetic (offline test)"`, one
   file per calendar day the suite ran. `scripts/theme_health.py` reads exactly that directory,
   so this is the **mechanism** behind V2's NOT-QUOTABLE theme-health verdict. → **greeks lane.**
2. **Two of the project's strongest guards fail on a developer box with messages that assert the
   opposite of what happened.** With the real track files present the pre-fix
   `test_paper_track.py` scores **65/70**; `test_hero_will_not_render_the_sandbox_book_as_the_index`
   reports *"the hero rendered the Tradier sandbox book as the Valquo Index"* while printing
   `source: 'index-track'` — the **contract-bound** recorder, read correctly. **Those local
   failures are not a B7 sandbox leak and must never be quoted as one.** Fixed suite: 70/70,
   which closes the long-standing "37/40 locally, don't chase it" note as diagnosed.

**DON: nothing was deleted, and one thing is worth knowing.** The primary checkout's
`data/screener.db` has `2099-01-01` as its **only** scan date, so the local app is serving the
test fixture on every scan-derived surface; `data/app.db` holds **34** test-created accounts.
Cleanup statements are in `HANDOFF_optionsbot.md` §8 — run them *after* this lands, or they come
straight back. **No action is required for the fix itself.**

`archive.DEFAULT_ROOT` is still a relative path (`valuation/edge/archive.py:35`) — reported and
routed to the screener lane, since this item's scope was tests only. `FIXED` row, so `N` does
not move: equity **135**, options 192, infra 6, total 333, `rows_malformed: []`.

---

## EDGE — WHAT THE THREE DEAD LIVE THEMES COST: IMMATERIAL ON ALPHA, BUT THE LIVE BOOK FAILS THE CALIBRATED LONG-SHORT FLOOR (2026-08-10, session 17, `V2G`)

Full write-up in `HANDOFF_edge_audit.md` **SESSION 17**; ledger row `V2G`; pre-registration
committed **alone at `6d8750a`** before `scripts/live_theme_cost.py` existed.

**THE QUESTION, ROUTED OUT-OF-BAND.** The greeks lane measured (Part 12.7) that `insider` is
**constant** and `capital_discipline` / `institutional` are **absent** on 100% of served rows —
**42.9% of the composite's weight mass reaches no live score** — and explicitly left the price of
that to a backtest. This is that backtest.

**THE ANSWER: −1.31pp/yr, and not separable from zero.** Top-decile alpha **+7.17% → +5.86%**,
paired HAC t **−1.4040** over 69 paired dates, against a pre-registered −1.95pp bar →
**IMMATERIAL**. Building live sources for the dead themes is **a nice-to-have, not the project's
highest-value work.**

**THE CAVEAT THAT MUST TRAVEL WITH THAT: power against its own bar is 55.0%.** The design resolves
1.87pp at |t| = 2, so the bar is well matched — but IMMATERIAL means *could not be separated from
zero*, **not** *shown to be small*.

**THE MORE SERIOUS FINDING: the live four-theme book does NOT clear the calibrated long-short
floor** — HAC t **1.8811** against **2.2837** — where the deployed seven-theme book clears at
2.6199. It **does** clear the top-decile alpha floor (**3.2087** vs 2.2913), and the shipped
product is a **long-only hot list**, so what users receive stays demonstrable while the long-short
statistic quoted beside it does not.

**AND THE PART MOST LIKELY TO BE MISQUOTED: an immaterial alpha cost is NOT a finding that the
live absence is acceptable.** The live product computes a **different composite** from the one
every published figure is measured on — the class of defect audit B7 exists to prevent. Either
build the sources or quote the headline for the book actually computed. **That is the screener
lane's call, not the edge lane's.**

**IF ONE SOURCE IS BUILT, IT IS 13F.** Exploratory and carrying no verdict by design: dropping
`institutional` is the only one of the three negative in **both** halves (−1.41% full); dropping
`capital_discipline` is **positive** in both halves despite its second-strongest panel IC (+2.76).

**Equity `N` 131 → 135; Deflated Sharpe 0.8539 → 0.8504; `BACKTEST_RESULTS.json` re-run from a
clean tree** (16 leaves moved — five the DSR chain, four provenance, seven 0.000% float; every
headline bit-identical).

---

## ENGINE/SCREENER — THE BETA LADDER NOW COVERS THE FULL SERVED UNIVERSE, AND THE BREADTH SHOWS 43% OF THE LIVE SCORE'S WEIGHT IS INERT (2026-08-10, greeks lane)

Full write-up in `HANDOFF_live_data_bugs.md` **Part 12**; ledger row `V2F`; pre-registration
committed alone at `1867a3f` before `scripts/live_cache.py` existed.

**WHAT SHIPPED.** `scripts/live_cache.py` + `tests/test_live_cache.py` (40 tests, none touching
the network). Four modes — `capture` pins the served universe, `fetch` pulls, `seed` replays a
capture into a dedicated store, `report` measures offline.

**BETA COVERAGE 46/403 (11.4%) -> 500/500 (100.0%), WITH ZERO THROTTLE EVENTS.** Runs 1 and 2 died
at 176 and 297 throttled calls. **What made it affordable is BATCHING, not patience:**
`yf.download` pulled 500 monthly close series in **13 requests in ~40 seconds**; only the vendor
`beta` field (`.info`) cannot be batched, so that leg is paced at 2.5s and took ~25 minutes.

**THE STRUCTURAL FIX IS THAT FETCH AND MEASUREMENT ARE NOW SEPARATE PROGRAMS.** `_resolve_beta`
makes the network call itself (`wacc.py:166`), so measuring coverage burned the quota coverage
depended on — that is why it kept failing. `report` now makes **zero** network calls and drives
the **real** ladder against the cache, so it is deterministic and re-runnable. Failed or throttled
units are **never recorded** (the miner's tri-state rule), so coverage cannot be inflated by
running into a quota wall.

**RUNG DISTRIBUTION over 500 names:** `vendor` 432 (86.4%), `vendor_corroborated` 31,
`fallback` 22 (4.4%), `computed` 14, `vendor_uncorroborated` 1.
**MY PRE-REGISTERED PREDICTION WAS WRONG (60/40):** I expected a *higher* fallback share at full
breadth than the 46-name sample's 10.9%; it is **lower, 4.4%**, because that sample was enriched
with problem names by construction. **B1 do-no-harm HELD on real data through an entirely
different fetch path:** GILD 0.305, CI 0.288, KSPI 0.886 (n=30), CHTR 0.669 all reproduce Part 7.6
exactly, and KSPI is still rejected for its 30 observations rather than its size.

**THE FINDING — 42.9% OF THE DEPLOYED WEIGHT REACHES NO LIVE SCORE.** Measured on 500 served rows:
`capital_discipline` and `institutional` are **null on 100% of rows**, and `insider` is 100%
non-null with **exactly one distinct value**. Each carries **0.125** deployed weight out of a
0.875 total. `composite_score` renormalises over what is present, so **the live hot list is a
four-theme book (value, quality, size, momentum) wearing the weights of a nine-theme one.**
`insider`'s deadness is documented at `screen.py:288`; the other two are not, and
`capital_discipline` has the **second-strongest backtest IC (+2.76)**. **No claim is made about
what this costs in return** — that is a backtest question and not this lane's.

**A DEFECT IN MY OWN V2 METER, IN THE DANGEROUS DIRECTION.** Every V2 coverage floor counts
NON-NULL ROWS, so a constant theme passed all seven — and **`_spearman` does not return NaN on a
constant predictor**, it returns an arbitrary number, and **exactly +1.0 against a monotone
target**. The meter would have banked those as genuine monthly observations and the anytime-valid
band would eventually have called it significant. **The absent themes always refused safely; this
one would have produced a verdict.** Fixed with a per-date degeneracy floor, recorded as a
tightening permitted by `PREREG_v2_theme_health.md` §10. `tests/test_theme_health.py` 23 -> 27.

**THE THEME RECORD IS REACHABLE FROM A CHECKOUT AFTER ALL, and Part 11 said it was not.** The
public, credential-free `/api/hotstocks` carries all ten per-name theme scores. Replayed through
the project's own `Store.save_snapshot` into a **dedicated** database (never `data/screener.db`),
the meter now reads **500 real rows at `scan_date 2026-08-08`, 0 synthetic**, up from 0 usable
rows. **Not one of the ten verdicts changed** — still zero closed 63-day windows — but seven
themes moved from *blocked by absent data* to *blocked by elapsed time*. At a 500-name
cross-section a live IC of **+0.0379 is detectable by month 60** against `quality`'s backtested
+0.0356, confirming V2's calibration from the other side. **The endpoint serves the LATEST scan
only**, so the record accrues **forward** one day per run and can never be backfilled — 9 real
dates exist on Render that this repo cannot reach.

**RECOMMENDED NEXT STEP, and it is cheap:** run `capture` + `seed` on a daily cron. Every day it
does not run is a day of the forward record that cannot be recovered. **Owner: Cowork/infra.**

**TESTS: 26 suites, 1199 tests, 0 failures.** Zero trial cost — equity `N` stays **129**.

**BUGS FOUND (5), four for other lanes:** (1) three themes carrying 42.9% of deployed weight
contribute nothing to any live score; (2) the served payload's `health` key is `null`, so
`theme_coverage`/`theme_contributing` — which `screen.py` computes precisely to surface (1) —
reach nobody; (3) nothing in the repository catches a rate-limit exception, so a throttled call is
indistinguishable from "no data" everywhere except `BetaEstimate.unavailable`; (4)
`BETA_HIGH_CAP = 3.0` sends 7 of 500 served names (ARM 3.909, ALAB, BE, AFRM, AGGI, COIN, CRDO) to
a beta of 1.0, escalating Part 7.7's open item from one name to a population; (5)
`tests/test_saas.py:200` still writes a 2099-01-01 row into the real `data/screener.db`.

## EDGE LANE, 2026-08-10 — session 16

**No action required from Don.** Everything below is landed and tested.

### 1. Two live bugs in the paper options book — FIXED

The forward options track was running exit levels **no backtest describes**, and holding a
position the alert itself had refused. Both were routed in by the options-bot lane off the first
three real fills.

* **The exit levels were anchored to the price the order was SUBMITTED at, not the price it
  FILLED at.** Systematic rather than occasional: the paper cycle runs after the close, so the
  limit comes from a post-close quote and the order fills at the next open. **2 of 3 open
  positions were off spec** — TGT was running a +150.7% target against an intended +100%, MET a
  −46.7% stop against −50%. Levels are now re-derived from the fill on the alert's own policy, and
  a repair pass fixes rows that were already open. Every expected value was **written down before
  the code changed** and all of them held exactly: TGT 8.90 → 7.10 and 2.225 → 1.775, MET 9.80 →
  9.20 and 2.45 → 2.30, ETN untouched because its fill equalled its limit.
* **DISCLOSED, because it matters: the repair moves the book in the FLATTERING direction.** The
  bug made targets harder and stops tighter, so correcting it makes them easier and looser. It is
  still the right fix — the levels were wrong against the specification either way — but "we fixed
  a bug and the book improved" is the easiest way for a forward test to flatter itself, so it is
  recorded everywhere the fix is. Concretely: **MET sat 10.2% above a stop level no backtest ever
  specified**, and was days from recording a stop-out the strategy under test would not have taken.
* **The book bought a name its own sizing refused.** ETN's alert carried *"one contract costs
  $1,610, above the $1,000 budget"* and `skip: true`, and the paper track bought it anyway — **it
  is the largest position in the book.** Now refused, with the alert's own reason recorded. **The
  existing ETN position is deliberately NOT unwound**: that gate applies to new entries, and
  closing a live position to tidy the record is a trade decision, not a bug fix.
* **A third defect found while fixing the first**, same family: the crash-resume path silently
  used DEFAULT exit levels instead of the alert's, because it read a table that does not carry
  them. It has never fired — every live alert happens to use the default policy — which is luck,
  not protection, so it is fixed and pinned with a policy that differs.

### 2. PT-SPLIT — closed, and MY OWN EARLIER DIAGNOSIS WAS WRONG

Sessions 14 and 15 (mine) reported the sandbox engine as *"10 names equal-weighted at 10%, which
the contract's own 8% cap forbids"*. **That is not a cap violation.** The code sets the cap to
`max(8%, 1/n)` on purpose, because ten names at 8% sum to 80%. **The weights were correct for the
book.**

**The real problem is book SIZE — 10 names against the published Index's 86 — and it is one
construction fed two different inputs.** The paper-track endpoint reads the published book file
when it exists and **silently rebuilds from the store's latest scan when it does not**, and that
scan is a top-100 hot list rather than the universe. Had I "fixed" the cap as I described it, the
actual defect would have survived untouched.

**Resolved both ways at once, which is what Don's "no third state" requires:** the engine is
**aligned going forward** — it now refuses to seed any book that is not the real Index, loudly and
without liquidating anything — and the **four days already recorded are registered as a separate
experiment** in `PAPER_TRACK_CONTRACT.md` §5b that may never be quoted as the Index. Those days
are **kept, not deleted**: erasing a record because it turned out to describe the wrong book is
the flattering direction. Its **fills** are still real evidence about execution; its **return
series** is evidence about nothing the contract binds.

**Still open, and it is the app lane's:** this stops the engine adding to a wrong book. Making it
record the *right* one needs the published book file present on the Render disk when the cycle
runs.

### 3. V1 shadow vintages — REGISTERED (no measurement, and that is the point)

Amendment 1's Rule 6 says a scoring change resets the whole five-year clock and buys nothing
statistically. Taken alone that means **the model can never be improved again without paying five
years**. V1 is the way out: when a change opens a new vintage, the old one keeps being scored in
shadow on the same dates, and the two are compared **paired** — both books see the same market, so
market risk cancels.

**How much that buys, and the honest limit, both computed before any pair exists:** for two
similar books the 60-month detectable difference is **3.34 pp/yr against the vs-SPY meter's
19.01** — a four-fold gain. **But the tension is structural:** the meter is sharp exactly when the
change was small, and a change big enough to matter blunts it. **So a shadow that has not crossed
is the expected outcome, and is NOT evidence that a change was worthless.** That sentence is built
into the code's own output, not left in a document.

**Registered completely blind: there is no vintage pair to compare.** Vintage 2 opened 2026-08-10
and has no successor, so not one parameter could have been chosen to suit a result, even in
principle. Vintage 2's parameters are pinned in a tracked file now, so the shadow will run a
frozen snapshot rather than a later reconstruction. It is research-only and fenced off every
public surface by a test, **before** it has any numbers to leak.

### Numbers

* **Equity `N` stays 131; Deflated Sharpe stays 0.8539.** Two correctness repairs do not count as
  trials, and a registered instrument with no measurement is charged to infra. **`BACKTEST_RESULTS.json`
  did not need re-running** — checked, not assumed.
* **Tests: every suite green.** `tests/test_paper_track.py` 70/70 (was 47 at session 15),
  `tests/test_shadow_vintage.py` 26/26 new.

---

## OPTIONS LANE, 2026-08-09 — VALQUO_EXTENSIONS **V5** (measured slippage vs modelled costs): **DONE**

**No action required from Don.** Two items are routed to the lane that owns
`valuation/edge/paper_track.py`.

`scripts/slippage_report.py` is built, pre-registered (`PREREG_v5_slippage.md`, committed at
`c06ac55` before the script existed), and pinned by 52 tests. Run it with
`python scripts/slippage_report.py --from-export data_export/paper_track_history.json`.

**Headline verdict INSUFFICIENT, which is the pre-registered outcome.** The paper book holds
**3 entry fills and 0 exits**, so the exit half-spread has n = 0 and no aggregate may be quoted
(the pre-registered minimum is 30 filled legs). The expectation written down first was
INSUFFICIENT at 90/10, and it was right.

**The modelled bar is measured, not assumed:** entry half-spread **mean 410.0 bps of premium**
(median 333.3) on **3,885 of 3,885** banked R2-corrected trades, against a $2.58 median premium
and $1.30 round-trip commission (50.4 bps). **The brief's "modelled 33.4bps" is audit B11's
EQUITY cost in bps of stock notional and does not apply here — the ratio is about 12x.**

**What three fills already show, quoted as raw values and no mean:** entry fill vs its own limit
is **−2022.5, −612.2 and 0.0 bps**. That is **NOT execution quality** — the timestamps say every
order waits **12.8–15.9 hours** and fills at **09:46–09:47 ET, the opening minutes**, because
`auto-scan.yml` runs the paper cycle **after the close** (20:47 UTC = 4:47pm ET). The limit is
set from a **post-close quote** and the day order fills at the **next open**, so the difference
is an **overnight gap**. Consequence: the paper book's entry basis is not the backtest's (TGT's
alert-day ask was 4.55; the paper book paid 3.55), which flatters the forward track on entry for
a reason the backtest does not model.

**TWO SHIPPED-CODE BUGS, found in those same three rows, reported not repaired (V5 is scoped
new-files-only):**
1. **Exit levels are derived from the SUBMIT price and never recomputed to the actual fill**, so
   TGT is running **+150.7% / −37.3%** and MET **+113.0% / −46.7%** against an intended
   +100% / −50%. **2 of 3 live positions are running a strategy no backtest describes**, in the
   book whose whole purpose is comparability. **Systematic, not occasional** — the after-close
   schedule guarantees the limit and the fill come from different sessions. Fix: recompute both
   levels in `mark_open`'s `filled` branch.
2. **The paper track buys names the alert's own sizing refused.** ETN carries
   `skip: true, contracts: 0, "one contract costs $1,610, above the $1,000 budget"` and was
   bought anyway — it is the largest position in the book. Fix: honour `features.sizing.skip`
   in `_eligible`.

**Also routed:** the ENTRY half-spread is not measurable at all, because `paper_option_orders`
stores no bid/ask/mid at submit. Fix is two columns in `_place_entry`.

**Correction to the project record:** `CLAUDE.md` still says `paper_option_orders` holds **0
rows** and "the engine has never been fed". Measured today from the committed Render backup:
**3 paper orders, 10 index holdings, 4 index-series rows.** Fed since 2026-08-04.

**Trials:** infra 4 -> **5**, **options N stays 192, equity N stays 130** — no DSR-gated claim
moves. Full write-up in `HANDOFF_optionsbot.md`; artifact
`data/options_slippage/V5_SLIPPAGE_2026-08-09.json`.

---

> **FIRST: `RUN_RULES.md` is in the repo root and CLAUDE.md points every session at it.
> Read it before starting work. Non-negotiable for all agents.**

---

## 2026-08-10 — r1 lane: V3 DONE. THE HOT SCORE'S RANKING IS NOT DISTINGUISHABLE FROM CHANCE AT A GIVEN RANK

Extension item **V3** (`VALQUO_EXTENSIONS.md`), pre-registered blind at `251c989`.
Full write-up: **`HANDOFF_extensions_v3.md`**. Artifacts `data/free_analysis/SCORE_CALIBRATION.json`
+ `.draws.csv` (7,900 draws banked). Tests `tests/test_score_calibration.py`, 13/13.

- **VERDICT: NOT DISTINGUISHABLE.** The pre-registered primary statistic — the composite at
  **rank 10** on the latest cross-section — is **1.0909** against a noise **p95 of 1.1117**,
  empirical **p 0.116**. Both halves of the registered bar agree, so there is no ambiguity.
  **It GENERALISES: the verdict holds on 45 of 69 dates**, against a pre-registered gate of 42.
  **Consequence, accepted in writing before the run: the product's confidence language must
  weaken.** A reader told the #10 name "scores 97/100" is being given a number that roughly one
  in nine chance-assembled universes reaches at that rank.
- **X7's PERMUTATION CANNOT CALIBRATE A SCORE, AND V3 ASKED FOR EXACTLY THAT.** X7 shuffles whole
  rows, so a name's theme vector and its renormalization denominator both travel intact and only
  the ticker label changes — **the sorted composite comes back identical, not approximately**
  (sd ratio 1.000000 over 500 draws; five seeds give one distinct value to full float precision).
  It shipped as the registered CONTROL with that no-op predicted in advance. The instrument built
  instead is a coverage-preserving within-column permutation that destroys cross-theme agreement
  and holds every row's denominator fixed. **Pinned by a test**, because a null built X7's way
  completes, prints percentiles, and looks exactly like a measurement.
- **THERE IS NO EXCESS CROSS-THEME AGREEMENT.** Real composite sd **0.3845** sits at the noise
  median (p 0.634) and above it on only 29 of 69 dates. Destroying every cross-theme agreement
  does not narrow the composite — it slightly widens it. A top name's high score is one or two
  themes far out, not many themes agreeing.
- **THE TOP OF THE BOOK IS THINNER ON DATA THAN CHANCE — the one fixable defect here.** Present
  weight **0.94798** in the real top decile vs **0.95730** for a noise top decile and **0.96324**
  for the universe; only **9 of 500** noise draws are that thin, **p 0.018**. The tilt is
  mechanical (renormalization makes a thin name's average noisier, so it lands at extremes more
  often) but the real book has MORE of it than chance. **A name can rank highly partly because it
  is missing a theme.**
- **The group-level result does NOT generalise.** The top-decile MEAN clears on the primary date
  (p 0.008) but on only **21 of 69** dates. Quote it as a property of recent cross-sections only.
- **My directional expectation was WRONG**, via the exact branch the pre-registration named as the
  risk. Recorded expectation: DISTINGUISHABLE at 70/30.
- **ZERO trial cost** — a calibration searches nothing (session-10 precedent); this run adds
  nothing to `N`. **`N` moved mid-session and NOT by me: equity 130 when the pre-registration was
  written, 131 after merging `origin/main` (Amendment 1, `509c45b`).** Nothing here is
  `N`-denominated — a permutation floor is not the CPCV adopt gate. **CLAUDE.md still says 129,
  now two behind.**
- **NOT DONE, and it is an open dependency:** the app's confidence language was not changed.
  `valuation/web/**` is the app-fixer's lane; V3 is scoped new-files-only. The replacement
  sentences are written and ready in `HANDOFF_extensions_v3.md`.
- **Recommended next:** the thin-coverage tilt (p 0.018), not the rank-precision finding. It is
  the only result here pointing at a fixable mechanism rather than at a limit of what a
  1,842-name cross-section can support, and a minimum-coverage floor is cheap to pre-register.

## 2026-08-09 — app-fixer lane: THE TWO-RECORDER SPLIT ALREADY REACHED DISCORD (ledger PT-OUTBOUND)

**Session 14 filed `PT-SPLIT` as a risk to be assigned. It had already fired, four days
earlier, on the one surface where a wrong number cannot be taken back.** On **2026-08-05** the
daily Discord recap posted, in bold:

> • Since inception 2026-08-03 (3 sessions): index +3.22%, SPY +3.05% → **+0.18 pp**

i.e. the Valquo Index beating SPY. **The contract-bound recorder reads −0.2777pp (2026-07-31)
and −2.8468pp (2026-08-06) — it was never above SPY on any recorded day.** Reproduced exactly
(not inferred) by seeding a store from the engine's own committed
`data_export/paper_track_index.csv` and re-running `recap.build(..., day="2026-08-05")`.

**Nothing was miscalculated. The recap read the wrong BOOK and the wrong WINDOW:**
`paper_track.index_summary`, the Tradier sandbox engine — 10 names equal-weighted at 10% each
(weights the contract's own **8% cap forbids**), inception 2026-08-03, three days later than the
bound inception and so skipping the accrued drawdown the contract deliberately keeps.

**FIXED STRUCTURALLY.** New `index_track.vs_spy_claim()` is the single authority for any
Index-vs-SPY statement: bound source only, **no fallback to any other recorder**, and it returns
the numbers with the **book** and the **window** welded into the same string. `summarize()` now
draws its excess from it, so two derivations that happened to agree became one that must.
`recap._delta()` (which took its own `index_ret − bench_ret`) is deleted.

**The site had the same defect and the label did not save it.** `hero.py` fell back to the
engine on every fresh deploy (`data/` is gitignored) with its own `(idx - bench) * 100`. It
honestly set `source: "paper-sandbox"` — and **no template ever rendered that field**. *A label
a surface can decline to show is not a safeguard*, so the wrong book is no longer reachable.

Pinned by 4 new tests, each **mutation-tested** to prove it fails when the bug is present
(including an AST scan that, run against the pre-fix `recap.py`, flags
`line 212: index_ret - bench_ret`). One older test was replaced by a strictly harder one.
**926 passed / 0 failed across 29 suites.**

**STILL OPEN, and not this lane's:** `PT-SPLIT` remains OPEN for its other half — re-pointing
the engine at the Index book, a live-Render construction change. `PT-WRITER` (Cowork) still has
no automated daily write of the bound series, so on most days the honest post is now
*"no Index-vs-SPY figure"*, which is what it says. **Nothing here can recall the 2026-08-05
post.**

> **Scope:** newest sections first — audit session 6 (this one), then session 5, then session 4, then session 3, then session 2,
> then R1's original run, then session 1, then deep research #2, then the EV staleness fix, then
> PEAD, then options 22b, then P9b/P10, then P7/P8. Canonical numbers in `BACKTEST_RESULTS.json`;
> per-finding status in `CODE_AUDIT.md`.


---

---

---

## ENGINE/SCREENER — V2's LIVE THEME-HEALTH METER IS BUILT, AND IT REPORTS THAT IT HAS NOTHING TO REPORT (2026-08-09, greeks lane)

Full write-up in `HANDOFF_live_data_bugs.md` **Part 11**; ledger row `V2`; pre-registration
committed alone at `25ba793` before any code existed. **First `VALQUO_EXTENSIONS.md` section
executed, so that register lands with this work per its own rule.**

**WHAT SHIPPED.** `scripts/theme_health.py` + `tests/test_theme_health.py` (23 tests). It reads
the live per-name snapshot record, computes each theme's realized forward 63-day rank-IC as
windows close at monthly cadence, and carries an anytime-valid band per theme. The IC is the
panel's own `_spearman` and the band is `track_meter.boundary`, **both imported read-only** —
`valuation/edge/**` is untouched, and the project keeps one definition of each rather than two
free to drift apart.

**VERDICT: NOT-QUOTABLE ON ALL TEN THEMES, ON ZERO USABLE ROWS.** Every one of the 7 archived
scan days is provider `"synthetic (offline test)"` with `SYN*` tickers, and the store's single
`snapshot_rows` entry is dated **2099-01-01** — a fixture left by `tests/test_saas.py:200`. The
refusal is the product: each theme prints its blocking reasons and **no IC is printed at all**,
because a number beside its own reason for being untrustworthy gets quoted without it.

**V2's STATED DATA SOURCE IS HALF FALSE AND THE FALSE HALF IS THE ONE AN EXECUTOR DEPENDS ON.**
The schema and writer exist (`screen.py:66` persists all ten themes into `extra["factors"]`), but
`auto-scan.yml` runs the scan on a GitHub runner and POSTs the result to the live site, so **a
checkout's store never receives a real scan.** The record accrues only on Render's persistent
disk. There is also no task #97 anywhere (index 97 is `O25`), so the citation cannot be followed.

**THE ESTIMATOR IS PROVED ANYWAY, BECAUSE THE LIVE DATA CANNOT PROVE IT.** Against panels with a
known planted IC: planted +0.5 recovers **median IC +0.4712** against a theoretical +0.4826 and
is labelled CONFIRMED-LIVE; planted −0.5 crosses DOWN and is labelled DEGRADED; **8 noise panels
× 10 themes = 80 theme-runs produced 0 crossings.** The control caught a defect in **itself**
first — the initial panel builder let one date's entry price double as an earlier date's mark,
attenuating the recovered IC to **+0.3575**, which is the 0.341 that `1/sqrt(2)` predicts. That
would have read as a broken estimator.

**THE FINDING WORTH ACTING ON IS THE CALIBRATION, AND IT IS ABOUT WHICH SOURCE FEEDS THE METER.**
20,000 Monte Carlo paths carrying the overlap structure the band assumes:

| | 100 names (top-100 archive) | 800 names (full-universe store) |
|---|---|---|
| power at `quality`'s +0.0356, 60m | **2.5%** | **80.3%** |
| power at `capital_discipline`'s +0.0297, 60m | 1.5% | **55.0%** |
| detectable mean IC by 60m | +0.0851 | **+0.0299** |

Same band, same horizon, same alpha; only the cross-section moves. **On the top-100 archive this
meter is very nearly powerless at the effect sizes the backtest claims — the same arithmetic that
gives the forward paper track 13%. So the full-universe snapshot history is the asset, and it
lives only on Render's disk.** The archive is doubly wrong here: its top 100 are selected on the
composite, which range-restricts the very scores being correlated. False crossing under the null
is 0.0010 against a nominal 0.005 — conservative, as a Robbins bound should be.

**TIMELINE:** first 63-day window closes ~3 months after real capture begins, plus the
pre-registered 6 monthly observations, so **the earliest possible first reading is ~9 months from
the day full-universe snapshots start being retained; the first reading with real power is ~5
years.** The pre-registered expectation (NOT-QUOTABLE everywhere, 95% confidence) is CONFIRMED.

**ZERO TRIAL COST** — a meter searches nothing. Equity `N` stays **129**, Deflated Sharpe 0.8556.

**NOT DONE, and stated:** production was not read (the real history sits behind admin endpoints
and `ADMIN_TOKEN`; `--db` / `--archive` take a path so pointing at a downloaded copy is one
flag); no scheduled job was added; nothing was surfaced publicly; and the `test_saas.py` fixture
leak was not fixed — another lane's file, and the meter now defends against it.

**BUGS FOUND (4), the first two for other lanes:** (1) `tests/test_saas.py:200` writes a
**2099-01-01** row into the real `data/screener.db`, and `store.latest_scan_date()` orders by
`scan_date DESC`, so **`load_snapshot()` with no argument returns that fixture** on any machine
that has run the suite; (2) `VALQUO_EXTENSIONS.md` V2's data-source claim and its "task #97"
citation, above; (3) `archive.py:84`'s `top=100` makes the scan archive unusable for theme
health and its docstring reads as an invitation to use it; (4) `insider` (backtest IC −0.0052,
inside the pre-committed `REF_MIN_IC` of 0.01) and `sentiment` (empty in the panel) can never
receive a directional verdict — both correctly return NO-REFERENCE rather than a fabricated one.


## ENGINE/SCREENER — THE SITE NO LONGER PROMOTES ITSELF TO "LIVE" ON A CALENDAR (2026-08-09, greeks lane)

Full write-up in `HANDOFF_live_data_bugs.md` **Part 10**; ledger row `OOB5`. Pre-commitment
committed alone at `4f2d61f` before any code. **SHIPPED — labels only; every number in the
payload is bit-identical and no tracked data file changed.**

**This closes the one item in `PAPER_TRACK_CONTRACT.md` §6.4 that had a deadline whether or not
anyone acted, and it needed assigning because it sits outside the edge lane.**

`index_track.py:223-224` decided the site's public posture with a single comparison,
`days < MIN_LIVE_DAYS` (= 60). On the 60th trading day of the forward track, three things flipped
at once with no approval step: `headline` `"backtested"` → `"live"`, the **"too early to judge"**
pill went down (`templates/index.html:114`, keyed on `hero.thin`), and `hero.may_lead` went true.
On the recorded inception of **2026-07-30** that fires in **late October 2026** — at **13% power**,
against a test the contract's own §2 shows cannot detect an edge below **+49pp/yr**.

**Now gated on the contract's 6-month OPERATIONAL GATE, with ONE authority: the contract's own
register row**, read by `index_track.gate_state()`. Not a `settings.py` constant, not an env var,
not a store key — a code flag would be a *second* record of the same fact, free to disagree with
the document Don signs, and there would be no way to tell which was right. **The edge lane sets
one row in `PAPER_TRACK_CONTRACT.md` §5 on gate day and nothing else, anywhere:** field cell
`Operational gate passed`, value beginning `YES` / `PASSED` / `TRUE`.

**Fail-closed exhaustively, each case a test:** missing file, missing row, `pending`, `no`, blank,
a bare date, a wrong field name, a malformed row, the row inside a fenced code block, and two rows
that disagree — all NOT PASSED. **Measured on the contract as it stands on `main`: reads
`'pending'`, so day 60 now returns `headline='backtested'`, `thin=True`.**

**All seven pre-committed bounds HELD.** The two that matter: **B5** — with the gate unpassed the
headline stays `"backtested"` at *every* day count, checked to 2,000; **B6** — with the gate
passed the day-count floor **still applies**, so a 3-day track cannot lead. The gate is an
additional condition, never a replacement; getting that backwards would have been worse than the
original bug.

**The pre-commitment said the value must "begin with" yes/passed/true, and its own test caught the
hole:** `yes-ish, mostly` parsed as a PASS — the same class of defect as `research_log._parse`
reading prose as a verdict. The rule is now the first **whole word**, i.e. **stricter than
pre-committed**, which is the only direction that cannot reach the harmful error.

Pinned by `test_day_count_alone_can_never_flip_the_headline` (60/61/300/2,000 days with no gate
all stay backtested, then the gate flips it so the assertion cannot pass vacuously). Five new
tests; **83/83 screener**, full gate green. **One existing test was pinning the defect** —
`test_live_track_never_annualizes_a_stub_or_leads_with_it` asserted `headline == "live"` at
`MIN_LIVE_DAYS + 5` — and was amended with the old line quoted inline.

**NOT done, and stated:** `MIN_LIVE_DAYS` stays **60**, because it now gates only *annualisation*,
which is a value and not a label; `valuation/web/**` untouched, since fixing the producer means
`app.py`, `hero.py` and `showcase.py` inherit it unedited; the contract is **not signed** by me —
one register row set to `pending` plus a note, no option, no date, no threshold.

**BUG FOR ANOTHER LANE, and it is the important one: THERE IS A SECOND, UNGATED DOOR.**
`hero.py:75-92` falls back to `paper_track.index_summary()` whenever the Cowork tracker has no
live data, and takes `thin` from that payload's `meaningful` flag — `len(rows) >= 126`
(`paper_track.py:799`) — which never consults the contract. With the Cowork file absent and the
sandbox book running, `may_lead` can still flip on elapsed time alone. **Fix is one line in the
edge lane: gate `meaningful` on the same `gate_state()`, do not add a second flag.** Related:
both `PAPER_TRACK_CONTRACT.md` §6.4 and `CLAUDE.md` say `MIN_DAYS_FOR_MEANING` lives in
`index_track.py` — it is in `valuation/edge/paper_track.py:70`, and that sentence is the one
assigning the work.


## 2026-08-08 — OPTIONS LANE: O1 + O23, the exits tested against random entries (REJECTED / NULL)

Register `PREREG_o1_o23_exits.md` committed at `dc2c486` before any policy was scored.
Full write-up in `HANDOFF_optionsbot.md`.

**O1 — the exit sweep: REJECTED. Nothing beats the inherited +100%/-50%/half-DTE exit.**
21 policies x {3,885 alert entries, 29,785 random entries over FIVE pooled seeds}. PBO 0.000 on
both sets; the held-out chooser survives in both directions on both sets; no policy clears the
pre-registered gate.

* **`tp100_only` clears the 10pp expectancy bar (+10.78pp signal, +17.86pp random) and FAILS the
  statistic that carries the verdict** — paired name-year sign z **-5.76**, winning **41.7% of
  1,217 decided cells**, median cell **-5.79pp**. It works by turning total losses from **1.39%
  of trades into 46.87%** while letting winners run (hold 14.5d -> 42.6d). The pre-registered
  direction rule assigned it p=1.0 rather than a small p, which is the guard firing as designed.
  On RANDOM entries the same rule genuinely wins (64.5% of cells, z +10.55, stable across all
  five seeds), so it is CONTROL-ONLY, not an exit effect.
* **What is BROAD is SMALL: `tp150`/`tp200` are FDR discoveries with positive sign tests on BOTH
  entry sets, worth only +3.19pp and +3.82pp.** `sl30` is the exact mirror — wins 69.9% of decided
  cells while LOSING 3.11pp. Mean and median disagree systematically on this payoff.

**O23 — exits vs the underlying: NULL, set-dependent.** Signal pooled R2 **0.53304**
CI95 [0.48564, 0.58428] (point clears 0.50, lower bound does not); random **0.55737**
CI95 [0.53112, 0.61686] clears as UNDERLYING-DRIVEN. Sets disagree, so the register downgrades to
NULL. **The pooled fit understates the per-policy picture** (slopes 6.36-17.45; per-policy median
R2 ~0.70, 17 of 20 above 0.50). Independent Greek attribution agrees: delta **50.70%**, gamma
15.57%, theta 14.07%, vega 13.25%, residual 6.41% of absolute mark movement — and the signed means
say it plainly, **gamma +0.85 and theta -0.77 nearly cancel, leaving delta +0.46**.

**THE FREEZE HELD AND IS NOW PROVEN SUFFICIENT.** First research to run entirely off it, with no
live-store fallback: 3,885/3,885 and 29,785/29,785 contract histories served from the frozen copy,
fingerprints 2,987/2,987 clean, and the shipped policy replayed from frozen bytes reproduces the
banked book at **100.000%** under honest settlement. It also independently reproduces R2's
published headline — **real +3.41%/trade vs control +10.06%**, control per-seed range **+6.46% to
+15.34%** — numbers the freeze did not write.

**BUG FOUND AND REPAIRED (`4170ad9`): `options_exitlab.capture_path` was never moved to audit
B2's exit tolerance.** It kept the strict entry filter, so wide-spread and thin-premium days were
DELETED from every trade's exit path and losers decayed through the -50% stop unstopped. Replay
fidelity **86.950% -> 99.820%** on one line. The drift hypothesis was tested first and refuted
(untouched 86.5% vs re-mined 88.7%) before the code was touched. **Consequence: the 2026-08-03
exit lab scored all 21 policies on paths with days missing, and the bias lands hardest on
stop-based rules — an independent reason its REJECT is not transferable.**

**Trials: options 169 -> 192** (O1 n=21, O23 n=2). **Equity `N` unchanged at 129, so no equity
claim moves** (Deflated Sharpe 0.8556). `rows_malformed: []`.

**For Don, in one line:** you win 35.3% of trades and 86.8% of your gains come from trades that
doubled; we tested 21 ways out against your alerts and against 29,785 random entries, and nothing
beat the exit you already have — about half of what any exit rule gains or loses is just the stock
moving, and the convexity you buy by holding longer is almost exactly cancelled by the decay you
pay for it.

---

## 📌 AMENDMENT 1 — RUN #1 VOIDED, RUN #2 LIVE, VINTAGE RULE ADOPTED (2026-08-09, session 15)

`PAPER_TRACK_CONTRACT.md` **§5a**, recorded openly per the contract's own void clause — never a
silent edit, and nothing above §5a was deleted.

| | |
|---|---|
| **Run #1** | **VOID** — inception 2026-07-30, ~6 days, 2 rows. It measured a model that has since materially changed (growth-input fix, score fix, universe rebuild) |
| **Run #2 — the live test** | inception **2026-08-10**, gate **2027-02-10**, verdict **2031-08-10**, **zero accrued days** |
| **Cost** | equity `N` 130 → **131**, Deflated Sharpe 0.8547 → **0.8539**, √(2·ln 131) = **3.1226** (artifact re-run to match) |

**THE VINTAGE RULE.** Any **ADOPTED** change to scoring, weights or construction closes the
current vintage and opens the next. **Rebalancing under unchanged rules is NOT a vintage event.**
Each vintage has its own clock; the gate and meter attach to the **current** vintage, so a verdict
names a vintage. The cross-vintage chain is kept and published as **"the system as operated"** and
is **never** the object of a verdict, because it mixes models.

**→ THE PART THAT MATTERS BEFORE SHIPPING ANY SCORING CHANGE (rule 6): a vintage change resets the
whole accrued clock and buys nothing statistically.** 60 months at 49% power is unchanged. A
vintage that closes at month 30 has spent 30 months for no evidence.

**The amendment moved the CLOCK, not the STATISTICS.** σ, ρ, α, the cost drag and the
SUPPORTED/UNSUPPORTED bars are unchanged — so the *whole-run* void clause is not engaged — and σ
was **re-checked against the changed model**: the current backtest still gives SPY excess
+9.99%/yr at implied TE **11.401 pp/yr**, the figure σ came from.

**Disclosed because it is the objection: the voided window was known to be −2.85pp**, so voiding
is the flattering direction. Three answers, each checkable — the cause is independent of the
outcome and its clause pre-existed; run #2 accrues **zero** days so no window's sign could inform
the new start date; and the voided rows are **kept**, visible in `as_operated()`.

**The meter now has a caller.** `track_meter.detail()` ships as `summary()["contract_track"]` on
`/api/track`. It names every missing trading day, is **not vacuously green** before the vintage
starts, and is reconciled against `index_track.vs_spy_claim()` (−2.8468 vs −2.8468).

**⚠️ ONE THING TO CONFIRM — `valquo-daily-track-write` is not visible here.** 413 scheduled tasks
enumerate on this machine; three are Valquo-related and **none is that one**, and the name is
nowhere in the repo. But **no run was due yet** (first weekday firing Monday 2026-08-10 20:01), so
this is evidence, not proof — it may be registered under another account or machine.
**THE TEST IS MECHANICAL AND NEEDS NO INVESTIGATION: inception 2026-08-10 is day 0, the first row
due is 2026-08-11, so from 2026-08-12 read `/api/track` → `contract_track.recording_ok`.** False
with `2026-08-11` named means the writer is not running.

---

## ✅ SIGNED — THE PAPER-TRACK CONTRACT IS IN FORCE, OPTION E (2026-08-09, edge audit session 14)

`PAPER_TRACK_CONTRACT.md` is **IN FORCE from commit time.** Don chose **OPTION E**: keep
inception **2026-07-30** including the accrued negative days, a **6-month operational gate
(2027-01-30)**, a **60-month verdict vs SPY (2031-07-30)**, the ~36-month costed
equal-weight-basket secondary *only if it is ever built and separately pre-registered*, plus a
**pre-registered anytime-valid evidence meter** first rendered at the gate and monthly
thereafter, whatever it says. §5 is the register; §6 freezes the meter. Full write-up in
`HANDOFF_edge_audit.md` § SESSION 14; ledger rows `PT-CONTRACT`, `PT-METER`, `PT-WRITER`,
`PT-SPLIT`.

**Equity `N` 129 → 130** (the register is charged as a trial): **Deflated Sharpe 0.8547,
√(2·ln 130) = 3.1201**, and `BACKTEST_RESULTS.json` was re-run to match — 11 leaves moved, five
of them the DSR chain, four provenance and two last-digit float; every headline bit-identical.

**THE MATERIAL FINDING: there are TWO live recorders and they record DIFFERENT BOOKS.**

| | **published Valquo Index — WHAT THE REGISTER BINDS** | Tradier sandbox engine |
|---|---|---|
| inception | **2026-07-30** | 2026-08-03 |
| book | **86 names, score-weighted, max weight 2.3%** | **10 names, equal-weighted at 10% each** |
| read by | `screener/index_track.py` — the number the site shows | `edge/paper_track.py` |

The engine's 10% weights **violate the contract's own 8% cap**. These are not one track recorded
twice — they are different objects whose numbers can be confused, which is a B7-class split.
**Never quote an engine figure as evidence under the contract.** Needs assigning (`PT-SPLIT`).

**THE ONE BLOCKING ITEM, AND IT IS NOT WHAT ANYONE THOUGHT: the bound series has no writer.**
Days 2–4 are not missing from a scheduler fault or a crash — **nothing in this repository writes
`data/valquo_track_history.csv` at all.** `index_track.py` only reads it; the rows are produced
by hand on the Cowork side. Measured 2026-08-09: **2 of 6 due rows, 33.3% coverage.**
**→ COWORK LANE: the 6-month operational gate cannot pass until an automated daily write of the
Index's cumulative Valquo and SPY levels exists on every trading day.** If it is still unbuilt by
roughly 2026-11, the gate fails on 2027-01-30 by construction.

**Corrected from session 13:** *"the engine has never been fed — 0 rows"* was measured on the
**local dev database**. The live Render service holds 4 index days, 10 holdings and 3 paper
orders, and the weekly `track-backup` Action has been committing them to `data_export/` all
along. A local read is not a measurement of production.

**The meter, and the half of it that must always travel with the other half.** Robbins
normal-mixture confidence sequence: σ **3.9847 pp/month** (the backtest's 11.40pp/yr tracking
error inflated by R9's AR(1) design effect **1.4661**), **ρ = 3**, **α = 0.05 two-sided**, cost
drag **0.14529 pp/month**. Measured over 40k AR(1) paths — false-crossing **1.5%** against a
nominal 5%, but **power at the backtested +9.99%/yr edge is only 13.3% by 60 months**, needing
**~19 pp/yr to cross**. **So a meter that has not crossed is the EXPECTED outcome and is NOT
evidence against the strategy.** The AR(1) inflation is load-bearing: without it the false-crossing
rate is 6.7%. **σ may never be revised downward** (at 1.5× the assumed vol the rate is 20%).
Genuinely blind: **zero complete calendar months existed** when the parameters were frozen.

**✅ THE DATED AUTO-FLIP IS CLOSED — the engine lane landed it the same day (`126c137`).**
`index_track.MIN_LIVE_DAYS = 60` used to promote the paper track to the site headline around late
October 2026 at 13% power with no approval step. It no longer can: `gate_state()` reads the
**`Operational gate passed` row of `PAPER_TRACK_CONTRACT.md` §5** on every request, and
`headline` requires **both** the day count **and** that row. At any day count, indefinitely, the
headline stays `"backtested"` until the contract says the gate passed, and every unrecognised
outcome (missing file, missing row, malformed table, two rows disagreeing) counts as not-passed —
the failure direction is "still backtested", never "now live". **This session filled that row as
`pending` and verified their parser agrees: `gate_state()` returns `passed: false`.** The code
and the contract now agree, with exactly one copy of the fact.

**→ On gate day, the edge lane sets that ONE row and nothing else, anywhere:**
`| Operational gate passed | YES - 2027-01-30 |`. It cannot be set today — see the missing
writer above.

## ENGINE — CONFIDENCE NOW KNOWS WHAT THE VALUATION IS MADE OF (2026-08-08, greeks/engine lane)

Full write-up in `HANDOFF_live_data_bugs.md` **Part 9**; ledger row `OOB4`. Pre-commitment
committed alone at `2e0730a` before any outcome existed. **ADOPTED — labels only, and every
published number is bit-identical.**

The confidence label described where the data came from and which lens carried the blend, and
never what the number was MADE OF. A DCF that is 93% terminal value is a claim about year
11-to-infinity wearing a ten-year model's clothes, and the engine stamped it "high".

**A HIGH TERMINAL SHARE IS NORMAL — the project had no number for it until now.** Across the 201
DCF-participating names of the 241-name universe: **median 77.7%, p90 87.4%, max 227.8%.** A 70%
threshold would flag 73% of the universe. Any future "the terminal is doing all the work" claim
needs that denominator.

**Bands, argued from the distribution and committed first:** `0.90` caps confidence at "medium"
(just past p90, where the histogram collapses 69 → 9); `1.00` caps at "low" and is **not a
calibrated number but a sign change** — TV > EV means the explicit forecast's PV is negative.
Verified as an exact set equality against the PV(explicit) < 0 names.

**All seven pre-registered criteria HELD**, including the three that matter: every fair value,
range and upside bit-identical across 241 names (exact float equality); every composite score,
recommendation and sub-score bit-identical; and the 40-name control group — names with no DCF lens
in the blend — untouched. As in Part 8, **the gate IS the control group** rather than a proxy for
one. The bands bound on exactly the 9 and 6 names predicted before the run.

**THE BRIEF'S EXEMPLAR DOES NOT REPRODUCE, for the third time in two parts.** CI was cited as
publishing +275% at HIGH confidence on a 93.5%-terminal number. Measured: **CI is WITHHELD, its
terminal share is 90.3%, and both labels already read `low`.** Had the band been tuned to catch
CI it would have achieved nothing — a cleaner argument for pre-committing than any written in
advance. Named exemplars in prompts rot within days; check before building to one.

**The real finding that replaces it: ten names publish `score.confidence = "high"` on a DCF more
than 90% terminal.** Worst is SNAP at **227.8%**. Twelve published names were re-labelled —
SNAP, WELL, CPNG, SNOW, KHC (to `low`), GM, WMT, KR, SYY, SLB, HAL, COST (to `medium`). Published
mix: `score.confidence` high **120 → 110**, `blend.confidence` high 96 → 95.

**All 12 moved on `score.confidence` and only 4 on `blend.confidence` — the two labels disagreed
on 5 names, and the optimistic one is the one printed beside the recommendation.** SNAP read
`low` on its fair value and `high` on its score simultaneously. Capped together now; the
divergence between the two definitions is untouched and is a real open item.

Only 3 of the 12 carry positive upside (**KR +75%, SYY +22%, HAL +7%**) — those are where the
label does work, since confidence is read on a buy.

**Labels-only is structural, not observed:** `terminal_share_cap` is a pure function of
`(label, share)`, invoked after every value and the score are final.
`test_the_cap_changes_labels_and_provably_not_values` runs one company with the bands at both
extremes and asserts the values are bit-identical while the labels differ — it fails the day
anyone routes confidence back into a number.

**NOT done, stated in advance:** `screener/fairvalue.py` (no DCF, no terminal value, already
capped at "medium"); no weighting of the cap by the DCF's share of the blend; and the six
non-positive-DCF names from Part 8 (INTC, F, BA, SRE, CCI, IRM) are still unfixed — the
recommended next engine item.
## 2026-08-08 — OPTIONS LANE: the chain store is frozen, and O16 finally has a verdict

**Instrument repair, promoted from O16's own finding.** `data/options` is a LIVE 26.98 GB store
that the miner rewrites in place, so **every banked options verdict was pinned to inputs that no
longer existed** — the authoritative book measured 86.435% reproducible against it.

- **Design chosen on a measurement the brief demanded first.** A frozen copy of the R2 book's
  consumed chain rows costs **157.88 MB / 27.44 MB gzipped (banked artifact: 23.30 MB)** against
  a **26.98 GB** store — **0.585%**. So copying is ADOPTED, not rejected: a book is *sparse* in
  the store, reading one day in ~250 per symbol-year. Fingerprinting adopted alongside it.
- **DRIFT IS PROGRESSIVE AND TRACKS AGE, NOT THE BOOK.** All ten banked books reconciled:
  everything banked 2026-08-03 is ~56% untouched, everything banked 2026-08-05 ~80%. Nothing is
  lost (0 absent symbol-years) and the store has been quiet since 2026-08-06 04:29.
- **Frozen:** R2 corrected (2,870,811 rows, 23.3 MB) + its five random-entry controls
  (21,877,728 rows, 168.9 MB), under `data/options_freeze/*_2026-08-08/`. Total 192.2 MB, i.e.
  **0.71% of the 26.98 GB store**. The R2 copy is validated end to end: 20/20 sampled alerts
  replay term_slope from the frozen copy alone. **Retired with annotation:** pre-correction, `state_mid`,
  entry lab, exit lab.
- **The gate is wired** at `theta_bulk._year_frame` (the single read choke point) and in all
  three banked-run runners. Descriptive at bank time, blocking only for replays.
- **BUG FOUND AND REPAIRED IN MY OWN GATE:** the `.sha256` sidecar cache is keyed by
  `(size, mtime_ns)`, so a same-size rewrite inside the timestamp granularity served a **stale
  hash** — a false negative in the very check built to catch drift. Blocking paths now bypass the
  cache; measured cost of doing so is 18.2s for all 1,429 symbol-years.

**O16 — VERDICT: IS DISTINCT** (register `ad66468`, unamended), on the refrozen book: 3,885/3,885
rows, 186 names, 118 months, 0 drift. Spearman(term_slope, atm_front) **−0.53966**, CI95
[−0.5740, −0.5022], below the committed 0.60 bar. **QUOTE IT WITH THIS OR NOT AT ALL: Pearson is
−0.82793, which clears the 0.80 level bar, so the same data under Pearson returns the OPPOSITE
verdict.** The register named Spearman in advance, which is the only reason the verdict is what
it is. The predictive arm corroborates: the residual of term_slope on front IV predicts *better*
(+0.0703) than term_slope itself (+0.0567) while front IV alone predicts nothing.

**O24 — NULL re-confirmed** on the refrozen feature: R² 0.21443 → 0.21555, CI [0.1840, 0.2498]
still wholly below the 0.25 bar; every bucket mean moves ≤0.0014. The refrozen book differs
materially **row by row** (13.6%) and **barely at all in aggregate**.

**Downstream:** the live Signals surface is unchanged. **U2 is unblocked on the question it was
queued behind**, with two conditions: it must not rest on a linear-only treatment (the verdict
flips under Pearson), and the clearance is for the live/refrozen feature, not the banked book.

**Trials:** options N 164 → **169** (O16 re-charged, because last cycle's exploratory read meant
the re-run was not blind). **Equity N unchanged at 129** — no equity claim moves.

---


## P2's CORRECTED FIGURES SWEPT OFF EVERY SURFACE (2026-08-08, app-fixer lane)

P2 corrected P1's capacity headline (~$23M → **~$4.9M**, overstated 4.72x because
`scripts/capacity.py` hard-codes the pre-B6 breakeven). This session swept every **rendered**
surface for the figures P2 corrected and fixed each one. Full detail and the before/after
table in `HANDOFF_appfixes.md` session 19; ledger row P2 amended.

**Fixed on the public `/work` and `/methodology` pages:** capacity $23M → **$4.9M**; breakeven
236 bps vs 37 bps → **134 bps vs a measured 33 bps** on 261% turnover; the FF5+MOM alpha
**+8.81%/yr, t 5.74, 109 windows, 1998–2026 → +6.99%/yr, NW t 3.98, 68 windows, 2009–2025**;
panel 2,710/110 → **2,531/69**; trial count "~146" → **116 equity (272 project-wide)**.
`/work` also claimed long-short **t 3.52, "above the 3.0 hurdle"** — corrected to **2.84
(NW 2.62), which is BELOW it**, with the 2.70–3.52 grid range stated. The Index `method`
payload (P2 bug 3) and the track export `basis` are corrected too.

**THE SWEEP FOUND WORSE THAN IT WAS SENT FOR, and P2 did not list it because it is not in a
template: the PUBLIC landing page rendered "Backtested net alpha +17.4%/yr"** — pre-B6 —
**against a corrected +11.6%**, and the taxable book's after-tax alpha was overstated
**sixfold (4.86% → 0.81%)**. Both come from `settings.BOOK_CONFIGS[...]["measured"]`, a config
dict that reaches the page via `index_track.summarize()`. Provenance was matched before
substituting (identical `label` strings, matching `rebalance_days`).

**The recruiter demo link is clean:** `index.html` — the dashboard, Track Record, Edge Lab and
Index tab — hard-codes no figures at all; it renders live API data. Verified by rendering
inside a real demo session.

**Deliberately NOT changed:** the Deflated Sharpe "undeflated / saturates" copy on both pages
is stale since M1, but correcting it would upgrade a disclaimed statistic into a real one (a
new performance claim) *and* `test_saas.py:414` pins the stale wording — copy and test must
move together, in a lane that intends it. The sector-neutral row's "+11.8% → +10.2%" was
**removed rather than replaced** (no corrected re-run exists; inventing one would be
fabrication). **`scripts/capacity.py` bugs 4–5 remain OPEN in the free-analysis lane — any
re-run still reproduces the $23M.**

**Gate:** 885 passed, 0 failed across 25 suites in the CI environment. Two test amendments,
both cited and both strictly stronger (one guard was keyed to the literal `8.81` and would
have gone silently vacuous when the figure was corrected). One unreproduced flake reported:
`test_portfolio_sector_cap_and_weights` failed once in a full sequential run, then passed 6/6
in isolation.
## LEDGER REFRESHED — 72/134 DONE, AND `--write` WAS DESTROYING EIGHT ROWS (2026-08-08, r1 lane)

Full write-up in `HANDOFF_ledger.md`. Counts and the disagreement table are published in
`VALQUO_LEDGER.md` itself, which is the place to read them.

**COUNTS: 72 of 134 audit items DONE (53.7%)**, 56 OPEN, 5 BLOCKED, 1 IN PROGRESS, 0 SUPERSEDED;
hand-verified 91/134. Plus **8 out-of-band rows** (7 DONE, 1 PRE-REGISTERED) counted separately so
that "of 134" keeps meaning what it always meant. The backlog is lopsided and the counts make it
legible: **`S` is 4/28 DONE and `O` is 6/26, and those two series hold 43 of the 56 OPEN items** —
what remains is signal ideas and options studies, not corrections. `B` 24/26, `C` 7/7, `D` 9/10
and `P` 5/5 are essentially finished.

**THE REFRESH ITSELF MOVED ONE CELL. THE WORK WAS MAKING IT SAFE TO RUN.** `build_ledger.py
--write` had never been executed since the out-of-band rows were added, and running it as shipped
would have **deleted eight hand-verified rows** — `OOB1`/`OOB2`/`OOB3` and the pre-registered
experiments `LOO`, `SELRULE`, `HACFLOOR`, `MLPREREG`, `MLCOMB`, i.e. **Sessions 7–11 and the
public fair-value leak closure** — plus all prose under the header (R3's stale-figure note, the C6
lesson) and the `FIXED` verdicts on `B8` and `P4`. Three defects, one signature: the script
curating content it did not write, against a docstring promising the opposite.

**DEFECT 1 WAS ALREADY KNOWN AND HAD BEEN WRITTEN INTO THE DATA INSTEAD OF FIXED.** `OOB1`'s note
ended *"NOTE: build_ledger.py regenerates from the 134 audit ids only and will DROP this row"* — a
warning stored in the row it warns about, deleted by the operation it warns about. Now fixed and
pinned by `tests/test_build_ledger.py` (20 assertions); `--write` is idempotent.

**ALL 21 DISAGREEMENTS RESOLVE IN FAVOUR OF THE HUMAN ROW; NO STATUS CHANGED.** Two previously
unrecorded traps were found and added to the file's list: **(5)** a multi-item commit subject
donates one item's verdict to every id in it — `275e9af` *"O16/O24 RESULTS: O24 is a NULL; O16
stopped at its own reproduction gate"* marks **O16 DONE** when O16 deliberately returned no
verdict; **(6)** `DEFERRED` is in the DONE vocabulary, so `## B23 — DEFERRED, deliberately` reads
as finished while its body says *"Not done, and not forgotten."* Both left unencoded on purpose —
the fix is a guess about commit-subject grammar and the human row already wins.

**EVERY LANDING OF THE LAST TWO DAYS WAS ALREADY RECORDED BY THE LANE THAT DID IT** (sessions 10
and 11, O16, O24, P2, C6, the leak closure), so there was nothing to fold in. Contract rule 1 is
being followed, and this task was a verification rather than a reconstruction.

**ONE ROW STILL WRONG AND NOBODY OWNS IT: `R3`'s note reads "Shrinks every options t ~1.36x"; the
corrected figure is √2.212 = 1.487× on the 3,885-trade book.** It has now survived two refreshes
because both flagged it as "not this lane's row". Recommended: let any lane correct a figure that
is already corrected elsewhere in the project.

---

## GREEKS — THE DERIVED LAYER GREW 315 → 502 NAMES (2026-08-08, greeks lane)

Full write-up in `HANDOFF_greeks.md`. Pure local compute: zero vendor option calls, and
`data/options/` verified untouched afterwards. Both suites green (252/252 edge, 22/22 greeks).

**502 names, 254,049,740 of 547,615,761 contract-days priced (46.4%), 1,131,698 name-dates,
27.5 GB.** Was 315 names / 349.0M in / 164.4M priced (47.1%) / 17.8 GB. Every one of the 502
names the miner marks `complete` now has a derived layer; none is missing.

**THE ONE THING OTHER LANES MUST KNOW: any autopsy PBO, feature p-value or Deflated Sharpe
computed after today is NOT comparable to any figure banked before today, and the difference is
NOT a finding.** `options_autopsy.py` reads this layer directly (`:150`, `:181`) and it feeds the
64-feature gate → `pbo_cscv` and `deflated_sharpe`. Precedent, from `derived_stamp`'s own
docstring: the layer going **111 → 317 names moved PBO 35.7% → 48.57% under identical trades and
identical code, and nothing warned.** Today's jump is comparable in size.

**"The autopsies stamp their fingerprint now, so growing the layer is safe" is half right.** The
stamp exists and works (`options_autopsy.py:538`, shipped as `derived_data` at `:964`), but it
**gates nothing** by design, `derived_comparable()` has **no production caller**,
`UNIVERSE_RESULTS.json` is **not stamped at all** while still shipping a Deflated Sharpe, and
**no stamped baseline has ever been written**. So the stamp makes the discontinuity *detectable
by a reader who checks the field*; it does not make it safe. **Recommended, cheap, and blocking
for anyone about to use this layer: run one autopsy purely to bank a stamped baseline.**

Two other findings worth carrying:
- **Only 187 of the 413 re-derived names were new.** 226 were re-done because their source
  year-files were **rewritten in place** by the OI re-mine (1,100 files, zero new years added).
  Skip-existing is signature-based, so this is correct — GEX consumes `open_interest` directly.
- **The six ticker-reuse names corroborate independently.** `COR`, `SN`, `FIG`, `SNDK`, `AXON`
  all price far below the 46.4% average (24–34%) and four carry a flag caused by the identity
  break, because the bars series belongs to the ticker's *current* occupant. **Do not use those
  six, plus `META`, `DD`, `DOW`, in options research until per-symbol validity windows ship.**
## P2 — USER CROWDING MODELLED (r1 lane, 2026-08-08) — memo only, no code

Full write-up: **`HANDOFF_crowding.md`**. Ledger rows P1 and P2 updated.

**The answer depends ~700x on which book is published, and the product is already on the safe
side — by a design choice whose written rationale is factually wrong.**

| book a cohort buys | cohort AUM where slippage cancels the +7.17% alpha | users @ $10k |
|---|---|---|
| live Valquo Index (86 names, large-cap, median cap $22.2B) | **$5.1B** | ~506,000 |
| all-cap top-25 (what P1 modelled) | **$7.4M** | ~740 |
| all-cap top-10 | **$1.6M** | ~160 |

- **P1's published capacity of ~$23M is overstated 4.72x — the true figure is ~$4.9M.**
  `scripts/capacity.py:36` hard-codes `BREAKEVEN_BPS = 234.505` (pre-B6); the live measured
  breakeven is **134.113**. Re-derived from P1's own published cells, which the closed form
  reproduces to zero residual. **P1's strategic conclusion is unchanged and strengthened.**
- **Three of P2's four premises are false.** The Index does **not** publish holdings — it is
  owner-only (`surfaces.py:80`) and pinned by a test. Not 25 names (86). Not small-cap
  (`LARGE_CAP_MIN = 10e9`).
- **Slippage is not the binding risk.** At 10,000 users the McLean–Pontiff decay channel is
  ~3x larger than impact and does not depend on user count at all. Not modellable from
  anything on disk; no number was invented for it.
- **Biggest lever after breadth: stagger entry.** Capacity is very nearly linear in days spread
  (measured 4.97x at 5 days, 20.9x at 21).

**BUGS FOUND (6, none fixed — other lanes).** Highest: the **public** `/work` page
(`portfolio.html:479-480`) still publishes the **void** `+8.81%/yr, t 5.74, 109 windows, 1998–2026`
(corrected: +6.99%, NW t 3.984, 68 windows); `valquo_index.py:129-133` ships a description string
quoting 2,710 names/110 dates/+11.8%/236bps into the live Index JSON; `capacity.py:36` and `:124`
carry a stale breakeven and the pre-B6 panel. Also: the large-cap floor is justified as "the
tier where the measured IC was strongest" — measured, large is the **weakest** by IC (0.0287 vs
small 0.0313), though strongest by long-short. **That floor is load-bearing for crowding, so a
wrong stated reason is a live risk of it being removed.**

**Equity `N` unchanged at 116** — nothing here searched the return signal, so no
`RESEARCH_LOG.md` row was added (recorded because the self-penalising direction is to add one).

---

## C6 CLOSED — Oracle box decommissioned; the "lost" sources were in a tracked zip (2026-08-07, options-bot lane)

Full write-up in `HANDOFF_optionsbot.md`. Bot subproject only; **nothing under `valuation/**`
was touched** and the main tree has **no executable dependency on the box** (checked: 0 imports
of bot packages across 218 main-tree Python files by AST, 0 references in all 3 `.github/`
workflow files, 0 service units, 0 state-path reads — every textual hit was prose).

* **The Oracle box `141.148.45.115` is DECOMMISSIONED. Never ssh or scp to it.**
* **C6's blocker never existed.** The record said `options/data/*.py` lived "only on the Oracle
  box" and needed Don to `scp` it. It was inside `options-bot/handoff/quant_bots.zip` — **tracked
  in git the whole time** — recovered byte-identical (sha256) against three other copies. No
  reconstruction, no judgement calls.
* **Gates:** options suite **53 collected / 14 errors → 181 passing**; core **172, OK**;
  `deploy/preflight.py` **exit 0** with all three FIXES.md fixes verified by symbol and behaviour;
  main tree **24/24 suites green**.
* **C6 closes on the RECORDED branch** of its own criterion — the service is gone, so "deployed"
  is permanently n/a, and "fixed in repo, not deployed" stops being a decaying state.
* State through 2026-07-31 (journals, sim portfolios, equity curves, 9 correlation reports)
  restored from `quant_data.tgz` into the **gitignored** `quant_bots/data/` tree of the primary
  checkout; all 24 files verified ignored so none can reach a commit.
* **Two commit hazards closed:** `quant_data.tgz` and `valuation-tool/options-bot2/` were each
  untracked *and* unignored — one `git add -A` from committing a state archive and a duplicate
  copy of the bot tree. Both now ignored.
* **Do not "tidy" `options-bot/.gitignore:34` (`!handoff/*.zip`).** That negation is the only
  reason the sources survived. It is now commented to say so.
## 2026-08-07 — greeks lane, OUT-OF-BAND: the reinvestment undercharge. BOTH CANDIDATES REJECTED

The engine charges reinvestment as `Δrevenue / sales_to_capital` — growth capital only — which
collapses when revenue is flat, so a capex-heavy name is charged almost nothing to stand still.
Two pre-chosen candidates were measured against thresholds committed alone at `4f99d8f`, offline
on the 241-name 2026-08-05 snapshot. **Both REJECTED. Nothing behavioural ships**
(`REINVESTMENT_FLOOR_MODE` defaults `"off"`).

- **The control bound held perfectly for both arms — 116 names, bit-identical.** The gate
  (`capex − D&A > 0`) *is* the control group, so this was true by construction.
- **Arm A** (floor decaying over the explicit forecast) passes three of four success criteria and
  fixes almost nothing: its terminal change is **+0.0%** because it cannot reach the terminal, and
  these names carry **80%+ of EV** there. **Three of my four criteria were year-one statistics
  that a terminal-blind fix passes trivially.**
- **Arm B** (persistent floor, terminal included) **passes ALL SIX pre-registered bounds and is
  still unshippable**: 18 negative enterprise values, 16 negative terminal values. **The rejection
  rests on a criterion I failed to pre-register** — the bounds asked whether the number moved in
  the right direction, never whether it was still a number.

**The finding that matters, and it corrects my own Part 4 statistic.** The 33-name decisive set is
**two populations**: 14 genuine flat-revenue undercharges, and 19 **capex-boom** names whose spend
IS growth capital the revenue path already prices — ORCL's net capex is **68.8% of revenue while
revenue grows 3.1×**, which is why flooring it drives EV to −884,065. **Part 4's "34 names
undercharged by >5% of revenue" overstated the defect; the honest count is ~14.** The mechanism
works exactly where the defect is real (8 of 8 flat-revenue names within ±25% of observed spend).
Separating the two populations is what a third candidate must do — **not attempted, because
choosing that gate on these results is the tuning the pre-commitment forbids.**

**A LIVE defect found on the way, unrelated to either arm: six names are published today with a
NON-POSITIVE DCF** — INTC (−0.53 → **$34.54**), F (−31.92 → **$60.25**), BA (−24.97 → **$94.27**),
SRE, CCI, IRM. `blend._usable` drops a non-positive lens and renormalises the rest, so **a company
whose cash-flow model collapses becomes more attractive**: charging MORE reinvestment moved
EQIX **+121%**, GM **+92%**, XEL **+73%** UP. Characterised and pinned by a test, **not fixed** —
it changes six published numbers and needs its own bound. **Recommended next task.**

Tests: 24 suites, **872 passing, 0 failures** (engine 56/56). Write-up: `HANDOFF_live_data_bugs.md`
Part 8. Ledger row `OOB3`.

---

## 2026-08-07 — app-fixer lane: the recruiter master-link now opens the full read-only view

Full write-up: `HANDOFF_appfixes.md` Session 18. Product decision out of
`PROMPT_recruiter_master_link.md` (Don's, recorded there verbatim); no audit item, ledger
unchanged.

- **The link did nothing before this.** Measured, not inferred: a valid `/demo/<token>`
  session saw **exactly** what an anonymous visitor saw — every owner surface refused it,
  because `saas/surfaces.py` put them behind *owner* and a demo session is not one. The only
  two differences in the whole probe were a friendlier beta banner and an empty `/account`.
- **Now a genuine three-way split: anonymous / demo / owner.** A valid demo session reads
  Track Record, the Index, Signals, the option scorecard and the Edge Lab's learning log, and
  **may change nothing**. `surfaces.DEMO_DENIED_PATHS` is the enforcement and is deliberately
  **not gated on `OWNER_SPLIT`** — that flag governs what strangers may READ and must not be
  able to hand a résumé link the scan trigger as a side effect.
- **The anonymous surface did not move.** Byte-diffed, not eyeballed: the anonymous `/app`
  differs from HEAD by **one whitespace line, 7 bytes, zero content**.
- **No raw vendor rows.** Every newly-visible payload was walked and its row shape printed —
  all derived (weights, ICs, expectancy, cumulative series, constructed positions). The three
  `/api/edge/` runners that would compute new ones are denied.
- **Delivery is a button on `/work`**, built from env server-side at render time. Rotating
  `DEMO_ACCESS_TOKEN` on Render re-points the button and kills every copied `/demo/<token>`
  link in one action; clearing it removes the button and shuts `/demo` off. **The résumé link
  is `https://valquo.co/work`** — the token never goes on the résumé.
- `test_public.py` **17/17 → 27/27**. The one test that pinned the old posture
  (`test_the_index_stays_owner_only_and_says_why_on_its_own_face`'s sibling
  `test_the_split_is_a_flag_that_actually_reverts`) was **amended with a comment citing the
  prompt and the date**, not deleted, and what replaced it is stricter: demo may read, is
  still not the owner, and still may not act.
- **Don must set `DEMO_ACCESS_TOKEN` in Render for the button to appear.** It is not set from
  this session and the token is not in the repo.
## 2026-08-07 — greeks lane, OUT-OF-BAND: a vanished vendor field can no longer rewrite a headline

**MRK went from "cannot value this name" to a published 91 "Strong Buy" because Yahoo stopped
returning one beta field and `wacc.py` silently substituted `1.10`** (WACC 5.53% → 9.31%). The
field is INTERMITTENT, not gone — it was back at 0.211 the same week. Shipped:

- **`valuation/data/beta.py`** — beta computed from the company's own prices, 5y monthly vs SPY.
  **A 1y-DAILY window was tried first and is WRONG**: it returns KO −0.286 and XOM −0.484.
- **A stated ladder in `wacc.py`** — override → an ordinary vendor beta accepted untouched (no
  extra call; this is the control group) → corroboration against the company's own prices → a
  stated constant of **1.0** (the market portfolio's beta by construction) replacing the
  underived `1.10`.
- **Rejection on HISTORY, not on value.** GILD 0.336, CI 0.321, CHTR 0.678, MRK 0.211 and XOM
  0.173 are all genuinely low-beta, so flooring the *value* would assert something false about
  them. Only KSPI's 0.080 is an artifact, and what makes it one is 30 monthly observations on a
  2024 ADR listing. The value decides who gets **checked**; the observation count decides who
  gets **rejected**.
- **`InputProvenance` stamps** on beta and the risk-free rate (source, as-of, n, vendor value,
  substituted), serialized out through `WACCResult.to_dict` → `PipelineResult.to_dict`.

**All four pre-registered bounds (committed alone at `04d9f12`) HELD** on a 46-name paced sample:
control group 37 names **0 moved**; **MRK's vendor-absent WACC swing 0.133pp against the old
code's 3.85pp** (which independently reproduces the reported incident); KSPI rejected at n=30<36,
i.e. for its history; **0** published/withheld flips. Trigger insensitive at 0.10/0.15/0.25 —
**0 betas differ**.

**TWO FULL-UNIVERSE RUNS WERE INVALIDATED BY THEIR OWN RATE LIMITING** (176 and 297 throttled
calls; run 2 had **302 of 403 names arrive with no vendor beta at all**), and in run 1 bounds 2
and 3 "passed" **vacuously** because both arms landed on the same constant. That exposed the real
defect: **the first ladder treated "the check failed" as "the history is thin" and pushed 178 of
402 names onto the constant** — the original bug with a new trigger, on exactly the 500-name burst
production scans. Corroboration is now best-effort with a failure mode of *no change*.

Two further defects found and fixed: **the plausibility band was applied to the vendor's beta but
not to our own** (PDD adopted a *computed* −0.039, clamping WACC to 4% and turning a $217.82 fair
value into a refusal), and **`.gitignore`'s bare `data/` also matched `valuation/data/`**, so the
new module was unaddable and would have shipped as a runtime `ModuleNotFoundError`.

**Caveats that must travel:** 46 names, not the 403 served. The fix cannot help a name whose
vendor beta is missing *and* uncomputable, so under a throttled feed the hole is **narrowed, not
closed**. And it moves fair values systematically **UP** for names formerly priced at 1.10 —
ARGX +83%, COP +69%, DTEGY +61% — which nobody should read as evidence it is right; **someone
should check whether those names now clear publication thresholds they previously failed.**

Tests: 24 suites, **859 passing, 0 failures** (engine 51/51). Full write-up:
`HANDOFF_live_data_bugs.md` Part 7. Ledger row `OOB2`.
## 2026-08-07 — r1 lane, OUT-OF-BAND: `worktree-ui-polish` triaged (read-only). Nine files, not fifty commits

Full write-up: **`HANDOFF_branch_triage.md`**. Nothing was merged, cherry-picked or deleted.

- **The branch is misnamed.** "UI polish" is 3 of its 50 commits; the rest is the project's early
  Edge Lab history. It stranded because that work was **squash-landed onto `main` as `8a8c2b8`**
  (2026-07-28 15:19) when a stray 138 MB licensed export blocked a normal push. `git cherry`
  shows all 50 as unmerged because a squash changes patch-ids — **that is a trap, not lost work.**
- **Exactly nine files are unique to the branch.** Four are the `param_search` module
  (locked hold-out, White/Hansen SPA, plateau+interiority selection) — **VALUABLE**, absent from
  `main`, and its four engine calls still match `main`'s signatures exactly. Five are a UI theme
  layer that `main` re-implemented inline eight hours later — **OBSOLETE**.
- **THE 13F INERT LAG GRID IS NOT LIVE ON `main` — the premise that it might be is wrong.**
  All three parts of `5da1473` are present: `INST_LAG_GRID = (15, 45, 135, 225)`
  (`fundamental_panel.py:2780`), the guard test (`tests/test_edge.py:404`), and the UTF-8 stdout
  reconfigure (`:3967`). No bug to file.
- **Do not merge it:** a dry-run gives **22 conflicted files**, incl. `add/add` on `CLAUDE.md`
  (10.6 KB on the branch vs 97 KB on `main` — it predates the whole claims audit).
- **Pruning must take BOTH refs.** `worktree-honest-param-search` is a strict *ancestor* of
  `ui-polish` and holds 47 of the 50 commits, including every valuable file.

**Routed to other lanes — decisions deliberately NOT made here:**
- **→ edge lane:** the parameter search ran **3,584 configs** and appears in `RESEARCH_LOG.md`
  nowhere (zero mentions). By this project's own precedents (grids expressible via `n_trials`;
  `SUPERSEDED` rows still count) it looks countable; the real counter-argument is that it searched
  *construction* params, not signal inclusion. Direction matters: counting them **lowers** the
  Deflated Sharpe, so it is the self-penalising choice. Currently `N = 116`, DS 0.8674.
- **→ app/security lane:** `/api/feedback` (table + route + allowlist entry) exists only on the
  branch. It **is** rate-limited, length-capped and parameterized — I checked. The open question
  is posture: whether an unauthenticated write endpoint belongs on the post-leak public allowlist.

**DISPOSITION EXECUTED, same session (`HANDOFF_branch_triage.md` PART 2):**
- **The four `param_search` files are on `main` as `ef4b7a3`** — clean additions, no conflicts,
  24/24 suites green. **Dormant: nothing imports it, no shipped behaviour changed.** Interface
  re-verified *after* landing from `origin/main`'s own tree.
- **Routing note added at `HANDOFF_edge_audit.md` §8.** The sharp point for Session 10:
  `PREREG_ml_combiner.md` §3 selects "the grid point with the highest mean out-of-sample rank IC"
  — **argmax of a mean, the exact selector that scored +8.43%/yr in-window and −0.04%/yr on the
  locked hold-out.** Three amendments proposed; plateau smoothing explicitly NOT recommended
  (only 8 grid points).
- **TRAP, FLAGGED NOT HIDDEN:** `param_search.bat` is now in the repo root and **will fail if
  double-clicked** — it calls `--param-search`, which does not exist until the CLI is wired.
  Landed verbatim rather than invented. **Wire it or delete it.**
- **THREE REFS DELETED** after the land verified: `worktree-ui-polish` (`f591961`),
  `worktree-honest-param-search` (`5da1473`), `worktree-p6-costs-and-robustness` (`428f4de`).
  SHAs recorded for recovery.
- **`worktree-p6`'s old prune rationale was WRONG.** It was flagged over a "stale
  `BACKTEST_RESULTS.json`"; **the commit does not touch that file at all.** Every code change in
  it (`score_universe_now`, `STALE_PRICE_MAX_DAYS`, the missing-sector guard, the numpy overflow
  clip now at `attribution.py:46`, both tests) is already on `main`. Its only unique content is
  **prose quoting the void pre-B6 numbers** (110 dates, +11.8%/yr, 236bps/37bps) inside a
  user-facing description string — right verdict, wrong reason, and the real failure mode is
  worse because stale prose in a shipped payload reads as current.
- **THE STRANDED-BRANCH SCAN IS CLEAN.** Every remote `worktree-*` ref is merged into `main`
  except `worktree-demo-link` (2 commits, 2026-08-07 20:46, merges cleanly) — another lane's live
  work, not stranded, untouched.
- **`VALQUO_LEDGER.md` deliberately not updated:** no audit item covers this housekeeping.

---

## 2026-08-07 — greeks lane, OUT-OF-BAND: the public fair-value leak is closed

Full write-up: `HANDOFF_live_data_bugs.md` Part 6. Ledger row `OOB1`. Landed on `main` as
`92d2ac8`; pre-commitment `1f6ad92` is a provable ancestor.

- **BUG A (live, now fixed).** `store.save_snapshot` wrote a fixed 18-column INSERT with no
  column for `fair_value_withheld`, so the scan recorded a refusal and the database threw it
  away. **Reproduced on the real 399-row production snapshot through a real database on disk:
  refusing the rank-1 name republished `$386.68083192601813` as "blended".** Fixed with two
  columns + an in-place migration. **Control bound HELD — all 399 rows bit-identical to what
  production served.**
- **BUG B (structural hole, measured EMPTY).** 387 of 399 served names never get a DCF, so
  nothing checks their peer estimate against the valuation page's verdict. Asked the real model
  about all 387: **0 genuine refusals, 0 errors, 3.0–3.8 min at 6 workers.** The fix therefore
  **removes no published number from today's list.** Chose a refusal-only screen over raising
  `dcf_top` — same cost, but raising it would REPLACE the published number on ~387 names, which
  is Don's call, not a bug fix's, and is one constant away (`SCAN_DCF_TOP`).
- **The find that matters most points the OTHER way.** `_enrich_with_dcf` treated *"the model
  cannot value this name"* as *"the model REFUSED it"*, suppressing ordinary peer estimates —
  **NVS $185.41, SAP $364.97, TD $79.73**. Found because my own first measurement made the
  identical mistake. The mislabelled population is **unstable run to run (17 vs 77 of the same
  387 names)** and grows when the free upstream feed throttles. Fixed.
- **Two limits that must travel.** KSPI, STLA and CHTR are **not in today's production list**,
  so the fix could not be re-probed on the three original names and no substitutes are offered
  as equivalent evidence. And the flag is written at **scan** time, so this reaches the public
  surface on the **next scheduled scan**, not on deploy. Status: fixed and verified locally
  against real production data; **unverified on the live site until that scan runs.**
- Suites **24 / 849 / 0 failures**. New: `test_a_recorded_refusal_survives_the_snapshot_round_trip`
  (the existing in-memory test was green for the whole leak; a ratio walk provably cannot catch
  this class), plus a migration test and `test_not_dcf_valuable_is_not_a_refusal`.

---

## EDGE AUDIT SESSION 12 (2026-08-08) — the trial counter is repaired, N does not move, and X7's discrepancy is closed

Full write-up: `HANDOFF_edge_audit.md` § SESSION 12. Artifacts: `PREREG_session12_recount.md`,
`scripts/x7_reconcile.py`, `data/free_analysis/X7_RECONCILE.json`. **The live product is unchanged.**

Pre-registered at `21069ac` **before the parser was touched** — a recount that changes `N` changes
the significance of every DSR-gated claim in the project, so the procedure, the definition of a
changed verdict, and the rule that **no row's text may be edited to change `N`** were all fixed in
writing first.

### 1. The parser defect is REAL, and it NEVER FIRED

`research_log._parse` tested `\bFIXED\b` against every cell of a row joined together, so a row whose
free text merely contained the word "fixed" was dropped from `N`. Understating `N` **overstates**
the significance of every DSR-gated claim. Two sibling defects of the same class were found by
reading and fixed with it: the `n=<k>` grid multiplier was grepped from the whole line, and the
domain was taken from the first cell matching any domain name rather than the domain column.

**RECOUNT: NOTHING MOVES.**

| scope | legacy | corrected |
|---|---|---|
| **equity** | **129** | **129** |
| options / infra / total | 164 / 3 / 296 | 164 / 3 / 296 |
| rows counted / dropped `FIXED` | 57 / 18 | 57 / 18 |

Verified against the **shipped module itself**, then against **all fifteen historical revisions**
of `RESEARCH_LOG.md` — identical at every one — and no `fix*` word appears outside a verdict cell
in any of the 72 data rows as they stood at the recount. **No published `N` was ever wrong.**
Deflated Sharpe stays **0.8556**, √(2·ln 129) stays **3.1176**. All six named claims re-checked
mechanically and reproduce to six decimals. The written expectation ("N rises, 60/40") was
**wrong**.

**THE REPAIR NEARLY SHIPPED THE ERROR IT WAS FIXING.** Merging `origin/main` brought in **O16**,
which writes `|Spearman(term_slope, atm_front)|` — an absolute value — **inside a markdown table
cell**. The unescaped `|` gives that row 11 cells against a 9-cell header, so every column after
the metric shifts; the first-cut column parser read `n` off prose and charged the row **1 trial
instead of 5, understating options `N` by 4**. The whole-line grep it replaced was accidentally
immune. Caught only because merging and re-running the recount was written into the procedure.
Misaligned rows now resolve toward a **larger** `N` and are reported in `rows_malformed`. **The
O16 row was not edited** (the register forbids it); **its pipes want escaping as `\|` by the lane
that owns it.**

**Why it never fired is not reassuring:** the last three sessions dodged the word deliberately, and
the earlier rows avoid it by luck. A denominator protected by authors' word choice is not
protected. The repair ships with a fixture the old parser fails (3 real trials, of which it counts
1) and `rows_rescued_by_parser_fix` in `detail()`, so a silent revert would be loud.

### 2. THE X7 7-vs-8 DISCREPANCY IS DIAGNOSED — one draw, seed 1005

Open and called "undiagnosable" for two sessions. **The two sweeps ran at different project trial
counts, and `N` moves `ls_t`.** `cpcv_validate`'s adopt gate multiplies `se` by `_trials_haircut`,
which is **floored at the research log's `N`** — and `scripts/placebo.py` feeds the *adopted*
weights to `quantile_backtest`. X7 ran at N = 84, session 10 at N = 121.

Seed 1005 (margin 0.00287097, se 0.00094470) clears the N = 84 bar and fails the N = 121 bar, so it
was scored at **naive `ls_t` 2.1273** under the challenger's weights and **1.0454** under base.
Session 10's retained artifact records **1.0453572947436582** — identical to this session's
recomputation to sixteen digits.

Substituting the adopted value into session 10's draws gives **exactly 8** at `t ≥ 2.0` (X7's
figure); the adopt count at N = 84 comes back **21** (M1's recorded 21%); the naive **p95 stays
2.1437 and max stays 3.436**, which is why session 10's control reproduced X7's percentiles to the
digit while missing one draw — 2.1273 lands just below the 95th percentile. **One fact explains
both halves.** It also explains why it looked undiagnosable: seed 1005 did not drift across 2.0, it
**jumped 1.08 of a t** because its weights changed, so "no draw near the boundary" was the wrong
thing to look for.

**THE CONSEQUENCE THAT OUTLIVES IT: the calibrated placebo floors are functions of `N`.** Here they
happened not to move, because the affected draw landed below the percentile — that is luck, not
design. Every future sweep must record the `N` it ran at, and a floor may not be compared across
sweeps run at different `N` without checking. **The shipped strategy is unaffected** — it does not
adopt, it keeps `current-default`, so no haircut touches its `ls_t`; the exposure is to the
*calibration*, not the headline.

### 3. Also this session

- **`RUN_RULES` Part A gains rule 9 — "store the draws, not just the summary"**, with the bill
  attached: X7's summary-only sweep cost a 3.4-hour re-run at M1 and two sessions of "undiagnosable".
- **`CLAUDE.md`'s mechanism for M1's effect on the adopt rate was BACKWARDS** and is corrected:
  adoption is decided at `fundamental_panel.py:2729`, the Deflated Sharpe computed at `:2744`
  *downstream* of it. Direction and magnitude were right. Getting the mechanism right is what made
  the seed-1005 diagnosis findable.
- **`cpcv_validate` now banks `adopt_detail` and `challenger_weights_cols`**, so "what would this
  run have scored one haircut lower" is arithmetic rather than a re-run.
- **Tests: 262/262 edge, 26/26 suites green by exit code** (the suite count rose from 24 — the
  merge brought `test_build_ledger.py` and `test_term_slope_decomp.py` from other lanes).
  Equity `N` **129**, DSR bar **0.8556**, HAC long-short floor **2.2837**.

### Recommended next: unchanged — task #12, the forward paper-track vs SPY

Nothing here weakens it and §2 mildly strengthens it: a fourth demonstration that in-panel
statistics move for reasons that have nothing to do with the market — here, literally the number of
rows in a markdown file. Still needs a start date, a pre-committed horizon and a comparison rule
from Don **before** the first print.

**One correction to guard against a wrong inference from §2:** the floors are `N`-dependent in
principle, but N = 116, 121 and 129 all give the same 20 adopters, so session 10's 2.1437 /
2.2837 **are** current and need no re-derivation. What is required is the discipline — record the
`N` a sweep ran at, and never compare floors across sweeps at different `N` without checking.

---

## EDGE AUDIT SESSION 11 (2026-08-08) — the ML combiner is REJECTED, and its deciles run BACKWARDS

Full write-up: `HANDOFF_edge_audit.md` § SESSION 11. Artifacts: `PREREG_session11_execution_protocol.md`,
`scripts/ml_combiner.py`, `data/free_analysis/ML_COMBINER.json`. **The live product is unchanged.**

**The register was executed unmodified.** `PREREG_ml_combiner.md` was committed blind at `ec6c01d`
a session before it ran. Seven deployed theme z-scores, rank-of-`fwd_ret` target, 63d, the
corrected 69-date panel, a frozen 8-point `HistGradientBoostingRegressor` grid, all selection
confined to a decide half via CPCV, **one measurement per direction**, both directions. No
deviations; three register ambiguities resolved in the *less* favourable direction and recorded
before first touch.

### VERDICT: REJECTED — worse on alpha in both directions

| | decide-early → late | decide-late → early |
|---|---|---|
| selected grid point | `d3/lr0.10/it300` (**most complex**) | `d2/lr0.03/it100` (**least complex**) |
| **tree** alpha | **+1.88%** | **−2.66%** |
| **linear** alpha | **+11.58%** | **+2.82%** |
| **Δ alpha** (need ≥ +1.95pp) | **−9.70pp** ✗ | **−5.48pp** ✗ |
| **Δ LS HAC *t*** (need ≥ +0.25) | **−2.118** ✗ | **−2.877** ✗ |
| **tree monotonicity** | **+0.382** | **+0.842** |
| **linear monotonicity** | −0.903 | −0.855 |

**THE FINDING IS STRONGER THAN THE VERDICT. Negative monotonicity is well-ordered, so the tree's
top decile UNDERPERFORMS its bottom decile out of sample, in both directions.** The run carries its
own control: the linear arm on the **identical rows through the identical function** is
well-ordered, and the equal-weight benchmark matches between arms to four decimals. **It is the
model, not the harness.**

**It is not a fitting failure either. All 16 grid × direction cells had a POSITIVE decide-half CPCV
out-of-sample rank IC (+0.011 to +0.024)** across 15 purged paths — the model generalises *inside*
the decide half and **reverses across the boundary**. Corroborating that: **the two directions
selected opposite ends of the grid, monotonically** — capacity helps in one half and hurts in the
other, so "does model complexity help" is a property of which half you look at, not of the problem.
Same shape as session 7's LOO.

**Quote it beside the param-search precedent (+8.43%/yr in-search → −0.04%/yr locked hold-out):
selection on this panel does not merely fail to generalise; it can generalise backwards.**

**What it does NOT say:** it does not vindicate the flat 1/7 linear form, it does not close roadmap
#16 (a raw-signal or different-model-class variant is a NEW pre-registration and inherits this
reversal as its prior), and it changes nothing live.

**Trial cost paid as registered: equity `N` 121 → 129, Deflated Sharpe 0.8628 → 0.8556,
√(2·ln 129) = 3.118.** Every equity claim after this is charged N = 129.

**Tests: 260/260 edge, 24/24 suites green by exit code.**

### Recommended next: task #12, the forward paper-track vs SPY

Three sessions running, the binding constraint has been *how little independent evidence this panel
contains* — session 8 (n = 1), session 9 (n_eff 2–4 across 16 countries), session 11 (structure
that reverses between halves of the same panel). **Every remaining in-panel question is competing
for the same exhausted evidence.** The paper track is the only test that manufactures new
observations by waiting. It needs a start date, a pre-committed horizon and a comparison rule from
Don **before** the first print — not an agent. The session-9 clustering discipline applies to it:
monthly excess returns against SPY are one series, not many.

## EDGE AUDIT SESSION 10 (2026-08-07) — the HAC floor is measured; the headline clears it by half the margin the record implied

Full write-up: `HANDOFF_edge_audit.md` § SESSION 10. Artifacts: `PREREG_session10_hac_floor.md`,
`PREREG_ml_combiner.md`, `data/free_analysis/PLACEBO_HAC.json` (all 100 draws retained).
Nothing shipped in the product changed.

### Item 1 — X7's long-short floor, re-derived on the statistic the project actually quotes

X7 calibrated the floor at **2.14** on the **naive** *t*. R9 then made the **HAC** *t* the number
quoted (Ljung–Box rejects independence at p 0.036), and the two had been compared to each other
ever since — `CLAUDE.md` carried it as a known open defect. **Closed.**

**The cause was a writer bug, not a scoring bug.** `quantile_backtest` has computed
`long_short_tstat_nw` on every placebo draw since R9; the recorder never stored it. The floor
could have been read off X7's own sweep except **X7's raw draws were never saved**, so all 100 had
to be run again. Same panel, same seeds 1000–1099, same instrument, costs measured, procedure
pre-committed before launch.

| statistic | calibrated floor (p95) | shipped | verdict |
|---|---|---|---|
| long-short *t*, naive (the sweep's own control) | **2.1437** → X7's 2.14 | 2.83606 | clears, emp. p 0.02 |
| **long-short *t*, HAC** | **2.2837** | **2.61991** | **CLEARS, emp. p 0.03** |
| **top-decile alpha *t*, HAC** (new, no floor existed) | **2.2913** | **4.37623** | **CLEARS, emp. p 0.00** |

**THE HEADLINE CLEARS — BY LESS THAN THE RECORD IMPLIED, AND BOTH MOVES GO AGAINST THE STRATEGY.**
The HAC floor is *higher* than the naive floor (2.28 vs 2.14) while the real HAC *t* is *lower*
than the real naive *t* (2.620 vs 2.836), so **the margin over the floor falls 0.692 → 0.336,
roughly half. Quote 2.620 against 2.28, never against 2.14.**

**The old mismatch was mild, not wild:** pure noise clears 2.14 on the HAC statistic **6%** of the
time against the 5% intended. **The by-product is the stronger number:** the top-decile alpha HAC
*t* — the statistic on the front of the product — now has a floor and sits **above all 100 noise
draws**. R9 is corroborated in passing: Ljung–Box on noise draws rejects at 7%, near nominal, so
the real series' autocorrelation is a property of that series and not something the pipeline
manufactures.

**Reported, not buried:** the control reproduces X7's p95 (2.14) and max (3.44) to the digit, but
the `ls_t ≥ 2.0` rate comes back **7% against the recorded 8%** — one draw, with nothing near the
2.0 boundary, so not rounding. **It cannot be reconciled: X7's raw draws do not exist.** It moves
no floor (every bar is a p95). **Trial cost zero** — a calibration searches nothing; equity `N`
stays **121**.

### Item 2 — the ML tree combiner is PRE-REGISTERED, and deliberately NOT run

`PREREG_ml_combiner.md`, committed blind at `ec6c01d` before any model was fit. Seven deployed
theme z-scores as features (**not** the 56 raw signals, **not** `low_risk`/`sentiment` — those
would be theme-membership changes smuggled in as features); cross-sectional **rank** of `fwd_ret`
as target; CPCV reused unchanged; **all eight grid points selected inside a decide half, the
single winner measured once on the held-out half, both directions** — the direct answer to X7's
finding that CPCV adoption manufactures ~+1.4 of long-short *t* when selection and measurement
share a panel.

**The grid is priced before registering, which is the item's entire risk:** 8 points → `N` 129,
DSR 0.8556; 128 → `N` 249, DSR 0.7716; **230 → `N` 351, DSR 0.7213, BELOW X7's calibrated floor of
0.7216.** A grid that size would not test the model, it would destroy the incumbent's evidence as
a side effect. Hence eight, costing 0.0072 of DSR. Ambiguous is NULL; no re-runs; expectation
recorded first as **NULL 70/30**.

### Recorded and NOT pursued

Session 9's hypothesis that the Sharadar panel's 69 dates explain the cross-half instability
implies a thicker panel / monthly rebalancing. **The rebalance grid is upstream of every published
statistic**, so it would need a full pre-registered re-run against re-derived bars, not a patch —
X2 already showed long-short *t* ranges 2.703–3.517 across seven equally valid grids. Queued as an
open design question; nobody should act on it from the hypothesis alone.

**Tests: 259/259 edge, 24/24 suites green by exit code.**

**Recommended next: execute `PREREG_ml_combiner.md` exactly as written** — it is committed, blind
and priced, and needs only a training loop. Alternative, and still the only test on data nobody
has looked at: **task #12, the forward paper-track vs SPY**, which needs a start date and a
pre-committed comparison rule from Don rather than an agent.

## EDGE AUDIT SESSION 9 (2026-08-07) — 16 countries are worth 2–4 draws, and the design dies

Full write-up: `HANDOFF_edge_audit.md` § SESSION 9. New code: `valuation/edge/cross_country.py`
and `scripts/selection_rule_crosscountry.py`. Nothing shipped in the product changed.

**Executed session 8's pre-registration in full, in the committed order.** The one blocker
session 8 named — a clustering gate for countries — was built, tested and committed **before**
the measure set was touched (`d9ae291`), so blindness is a matter of git history, not of trust.

**RESULT: two independent kills.**

1. **THE DESIGN COULD NEVER HAVE RETURNED A POSITIVE VERDICT.** Session 8 asserted "16 held-out
   countries give 16 **independent** draws". That word was an assumption, was never measured, and
   is false. Measured: clustering is measurable on **10 of 10 arm-pairs** (design effects
   3.97–8.27 against a shuffled-null p95 of ~1.13), **ρ 0.198–0.484**, **n_eff 1.94–4.03
   countries out of 16**. The calibrated critical count is **17 of 16**; even a unanimous
   **16/16 gives p = 0.0546** (400k draws, se 0.0004). The rejection region is empty and the
   design's power at α 5% is **zero**. At the *median* ρ the bar is 16 of 16 — unanimity or
   nothing — so this is not an artefact of the conservative max-ρ rule.
   * **The pre-registered 12/16 bar carries a true α of 28.7%, not 3.84% — a 7.5×
     understatement.** Building the gate first is the only reason this session did not publish a
     "3.84%" result that was really a 29% one.
2. **`NO CONTRAST` — both rules select `size` on `usa`**, so every paired difference is
   identically zero. Pre-registered as an outcome before the run; **not a NULL and not a tie**.
   Four of five arms are same-sign across both `usa` halves, so the stability constraint does not
   bind at all. **Hypothesis only, generated on the decide set:** the instability that motivated
   the whole question (4 of 7 arms flip on Sharadar) may be a property of the 69-date panel's
   thinness rather than of the rule — 324 monthly observations versus 69.

**X8's own headline is UNAFFECTED.** X8 tests each region's premium separately with NW(12)
errors and never pooled countries into a count, so it never made the independence assumption this
refutes. **The gate constrains what is built on top of X8, not X8.** Japan +2.05%/yr (t 3.85),
developed Europe +3.36% (t 4.30), USA the weakest region (t 2.35) — all unchanged.

**THE SELECTION-RULE QUESTION IS CLOSED ON BOTH AVAILABLE DATASETS.** One panel gives n = 1
(session 8, a paired sign test's minimum p is 0.50); 16 co-moving countries give n_eff ≈ 2–4.
That is not an engineering defect to route around — it is the amount of independent evidence that
exists. **Do not re-open without new data.**

**Trial cost, paid as pre-committed rather than renegotiated after the result:** equity `N`
116 → **121**, Deflated Sharpe 0.8674 → **0.8628**, √(2·ln N) 3.083 → **3.097**. Still far above
X7's calibrated floor of 0.7216, still below the 0.95 convention. Two `RESEARCH_LOG.md` rows.

**Tests: 258/258 edge, all suites green by exit code.** Five new tests pin the gate: at ρ = 0 it
reproduces the exact binomial k = 12; it does *not* flag independent countries (R3's lesson one
dimension over); it detects planted co-movement with both estimators agreeing; the bar is
monotone in ρ and can only move up; and the arm-pair difference is exactly a scaled two-theme
spread (verified to 2.1e-17), which is why the measured co-movement is credible rather than an
artefact of arm construction.

**Bug worth other lanes' attention:** `research_log.py` tests for a `FIXED` verdict by searching
the **whole row**, so any row whose free-text note contains the word "fixed" is silently dropped
from `N` — understating the trial count, which overstates significance. That is the exact error
M1 exists to prevent, inside M1's own parser. Worked around by wording; **not repaired**, because
changing the parse without re-verifying all 53 counted rows would be reckless.

**Recommended next: task #12, the forward paper-track vs SPY.** It is the only test that runs on
data nobody has looked at, and the only honest answer to "n_eff is small" that does not assume the
problem away — it manufactures independent observations by waiting. Needs a start date, a
pre-committed horizon and a comparison rule from Don **before** the first print. Note the same
gate applies: monthly excess returns against SPY are one series, not many.

## EDGE AUDIT SESSION 8 (2026-08-07) — a test declined, and X8's result restored to the record

Full write-up: `HANDOFF_edge_audit.md` § SESSION 8. Nothing under `valuation/**` changed — this
session shipped a decision and a correction, not code.

**1. X8 ALREADY REPLICATED, ON 2026-08-04, AND CLAUDE.md NEVER SAID SO.** Before this session
`CLAUDE.md` — the file every lane reads — contained the words "JKP" and "Japan" **zero times**,
and so did this file. X8's actual verdict, from `HANDOFF_free_analysis.md`: the untuned 5-theme
composite mapped 1:1 onto JKP Global Factor Data earns **Japan +2.05%/yr (t 3.85)** and
**developed Europe +3.36% (t 4.30)**, 12 of 15 European countries clear t > 2, and **the USA is
the weakest region tested (t 2.35)** — the theme structure is not a US artifact. It is the
strongest external evidence the project has. Now recorded in `CLAUDE.md`, with the unflattering
half attached: **quality and momentum do not generalise to Japan**, only 5 of 7 themes map, and
JKP's +2–3.4%/yr against Valquo's +20.4% means this corroborates **the premia, not the
magnitude**. Research-only licence; it can never ship in the product.

**Process bug for Don:** a result can be `DONE` in the ledger and written up in one lane's handoff
while being invisible to every other lane. This session's own prompt asked me to "scope X8 … make
it actionable instead of aspirational" for a test that had already passed. Suggested rule: *a
verdict is not `DONE` until it appears in `CLAUDE.md`.* I did not change the convention myself.

**2. THE SELECTION-RULE TEST WAS DECLINED, AND THAT IS THE RESULT.** Session 7 nominated it;
session 8 was told to decide answerability first and to treat "not answerable" as first-class.
It is **not answerable on the Sharadar panel**, settled before any run using only already-published
numbers, so at **zero trial cost**:

- a three-block split gives 22-date blocks where noise is **σ 1.57pp against a 1.00pp committed
  margin** — pure noise clears it **26.1%** of the time and power is **50.6%**;
- the stability rule and the incumbent argmax rule **pick the same arm 90% of the time** and
  differ in verdict on **5.1%** of panels, so the design cannot separate them even in principle;
- decisively and without any variance estimate: **one panel is one draw, and a paired sign test at
  n = 1 has a minimum achievable p of 0.50** — no outcome could ever have been quotable.

**Equity `N` therefore stays 116** (Deflated Sharpe **0.8674**, √(2·ln 116) = 3.083) rather than
123 (0.8609). Declining a test that cannot resolve is the cheaper action, not the lazier one.

**3. IT IS ANSWERABLE ON X8's DATA, WHICH IS ALREADY ON DISK.** 16 held-out countries give 16
independent draws; a paired sign test reaches α 3.84% at ≥12/16. Fully pre-registered and blind in
`HANDOFF_edge_audit.md` §2 — **no JKP arm return was computed**, deliberately. Honest limit stated
up front: power **79.8%** against a rule better in 80% of countries but only **8.5%** at 55%, so it
can settle "substantially better" and never "slightly better".

**Recommended next step:** execute that pre-registration (session 9's first item, with its `needs
first` table in §3). The one real piece of work is re-pointing the existing design-effect-vs-null
clustering gate at countries — European markets co-move, so the effective n is below 16 and the
threshold must be re-derived **before** unblinding. **Alternative, and arguably higher value:
task #12, the forward paper-track vs SPY** — still the only test on data nobody has looked at, and
P4 shipped its machinery last session.

**Suites green:** all suites pass by exit code. No code changed.

---

## CI — THE AUTO-LAND ACTION WAS SILENTLY DROPPING BRANCHES (2026-08-07, r1 lane)

Full write-up in `HANDOFF_ci.md`. Infrastructure lane; nothing under `valuation/**` touched.

**Two things every lane should know:**

1. **You no longer need to hand-resolve `HANDOFF_STATUS.md`.** The repo had no `.gitattributes` at
   all; there is one now, giving this file, `RESEARCH_LOG.md` and `HANDOFF_*.md` a **union merge**.
   Conflicting hunks keep BOTH sides automatically — the answer every one of these conflicts was
   resolved with by hand. Measured: this file took 29 commits from many lanes in three days and
   every lane prepends at the *same* lines, so the collisions were structural, not bad luck.
   **`VALQUO_LEDGER.md` and `CLAUDE.md` are deliberately NOT union** — the ledger is a keyed table
   where union would silently produce two rows with the same id, and CLAUDE.md's corrections are
   meant to *replace*, not sit beside the claim they correct. Reasoning is written into
   `.gitattributes` itself so nobody "tidies" them in later.

2. **`concurrency: land-main` was cancelling queued runs, and a cancelled queue slot looks exactly
   like nothing happening.** GitHub allows only ONE pending run per concurrency group; a third
   arrival cancels the pending one with no failure, no red X, no annotation. Every `worktree-*`
   push shared that one group. **If you have ever pushed and watched `main` not move for an hour,
   this is why.** Now scoped per branch, so one lane's push can never cancel another lane's queued
   run.

**The "auto-land Action is down repo-wide" note (`21fbe46`) is REFUTED — please do not repeat it.**
The Action was healthy the whole time and landed four other branches during the window it describes.
Exactly one branch was ever silently dropped (`worktree-r1` @`3fb0809`, 2h34m). The symptom was
real; the diagnosis was not. **Before recording an outage, check whether anything else landed.**

**Two consequences to expect, both self-healing:**
- Other lanes still carry `concurrency: land-main` in *their* copy of the workflow until they merge
  `main`, so they can still cancel each other's queued runs for a little longer.
- Lands may now take longer when contested. The gate is 24 suites (~20 min) while `main` moves
  every ~10, so the merge→test→push cycle retries up to 3 times. It **skips the gate when only
  markdown landed under us** (the code is then byte-identical to the tree that just passed), which
  is what keeps that from livelocking. A `.yml` counts as code and never skips.

**The gate is NOT weakened.** Every commit reaching `main` is still a tree whose code passed every
suite; conflicts still stop the land with `main` untouched.

**Also flagged (`HANDOFF_ci.md` → BUGS FOUND):** `param_search.py` — "an honest parameter-search
protocol", 47 commits on `worktree-honest-param-search` from 2026-07-28 — **does not exist anywhere
on `main`**. It predates the Action, so it is not a CI drop, but it looks like real research work
stranded in the manual-merge era. Someone should decide whether to rescue or delete it.

---

## AUDIT SESSION 7 (2026-08-06) — B8 FIXED, HELD-OUT LOO IS **NULL**, P4 SHIPPED

Full write-up: **`HANDOFF_edge_audit.md`**, "SESSION 7". Pre-commitment pushed in `5a27ea1`
**before any LOO number existed**, including the expected direction. **All 24 suites exit 0** (248/248 edge, 45/45 paper-track),
verified by exit code rather than by parsing output — see BUGS FOUND 7.

| item | verdict |
|---|---|
| **B8** — holdout rule vs documentation | **FIXED.** `rule_fired` was computed and never read. Both verdicts now ship, separately named. **Neither shipped decision changes.** |
| **LOO** — pre-registered held-out leave-one-out | **NULL.** Neither direction's selected arm clears either committed margin; different theme selected each way |
| **P4** — the paper track's rules | **FIXED.** Departed names are now sold, not held forever |

**B8, and why it was done first.** `holdout_theme_validate` computed `rule_fired` and no line
read it, so its verdict was a **both-halves stability check wearing the name of an out-of-sample
confirmation**. Fixed rather than renamed — but *not* by gating the existing key, because
`scripts/placebo.py` reads `verdicts` and **X7's ~6% false-positive rate was calibrated against
that exact object**. So `verdicts` keeps frozen semantics (alias `stability_verdicts`) and a new
`oos_verdicts` enforces the documented rule. **`low_risk` stays zeroed and `insider` stays at
0.125 — but `low_risk` is confirmed out-of-sample in ONE of two split directions, not two.**
Quote it whole from now on.

**LOO — NULL, and the reason is the finding.** Select the best of seven leave-one-out arms on a
decide half, measure only that arm on the held-out half, both directions:

* decide-early → drop `momentum` (decide +3.68%) → measure **−1.30%**, LS *t* **−0.706**
* decide-late → drop `capital_discipline` (decide +2.20%) → measure **+0.20%**, LS *t* **−0.201**

**Four of seven arms change sign between halves.** Session 6's exploratory "+8.54% from dropping
`capital_discipline`" is carried by the late half and is not a property of the panel. **Do not
quote a full-sample ablation arm as a finding.** One thing survives: **`size` is the worst arm to
drop in BOTH halves independently** (−2.64%, −3.46%) — corroborated, though it was never
*selected*, so it carries no verdict of its own. **`quality` clears both margins on both halves
and was selected in neither direction** — deliberately NOT promoted, because switching to the
rule that would have found it, after seeing that it works, is session 6's error one level up.

**P4 — the paper track was not tracking the index.** `seed_book` only ever inserted, so a name
entered once and was **held forever**; the paper index had become an ever-growing union of
everything the screener ever liked. Departed names are now **closed** into a new
`paper_index_closed` table — never deleted, because deleting them is reverse survivorship bias.
A truncated export closes nothing and says so. **The first live run will report `closed: N` for
however many names accumulated wrongly — that number is the size of the bug and is worth
reading.**

**Trial cost.** This session's 7 arms take equity `N` 104 → 111; a concurrent lane's 5 equity
trials merged at close-out take it to **116**. **Deflated Sharpe 0.8674, √(2·ln 116) = 3.083** —
still far above X7's calibrated 0.7216 floor, still below the 0.95 convention. Also settled:
**`SUPERSEDED` rows DO count toward `N`** (the schema prose said otherwise; `research_log.py`
never implemented it — the counter is right and the prose is fixed).

**Recommended next step:** **X8, the international replication.** Session 7's answer to "can the
theme-ordering question be settled on one panel?" is *probably not* — with only two halves,
"stable across halves" is measured on the same data that provides the measurement half. Session
8's nominal first item (pre-registering a stability-based selection rule) is written up, but it
is thin on one panel and says so.

---

## P3 DONE — THE OPTIONS PAYOFF IS NOW SHOWN, NOT JUST DISCLOSED (2026-08-06, app-fixer lane)

Full write-up: **`HANDOFF_appfixes.md`**, Session 16. Branch `worktree-p3-hitrate` (`52f523d`),
landing via CI. New `valuation/web/payoff.py` + `tests/test_payoff.py` (30 tests); **24 suites,
822/823 green** — the one non-pass is M3's own documented xfail in `test_guards.py`, not mine.
**Two things here are other lanes' business, so they are in this file and not only in mine.**

> **ON THE AUTO-LAND BLOCKER NOTED BELOW: it resolved, then bit this branch a second time for a
> different reason.** From this lane's polling, `main` advanced four times in ~40 minutes
> (`57f63b7` → `729d8dd` → `3fa9520` → `0312426`), so the Action is alive and landing branches.
> What kept THIS branch out on its second attempt was a genuine **conflict in
> `HANDOFF_STATUS.md`** — two lanes prepending a section at the same anchor — which makes the
> Action `git merge --abort` and leave `main` untouched, exactly as designed. **Check
> `git merge origin/main` locally before assuming the runner is down**; a clean
> `merge-tree` from an hour ago is not evidence about a `main` that has moved four times since.

**1. `/methodology` — a PUBLIC page — is publishing three equity numbers this project's own
record marks VOID. This is the highest-priority thing I found and it is not mine to fix.**

| the live public page says | the record says |
|---|---|
| FF5+MOM alpha **+8.81%/yr, t 5.74**, 109 windows, 1998–2026 | **VOID.** CLAUDE.md: "Do not quote them anywhere." Corrected R1: **+6.99%/yr, NW t +3.984**, 68 windows |
| breakeven **236 bps** vs a **37 bps** cost profile | B11: breakeven **134 bps** vs a **measured 33.4 bps**; the 37 bps "was an assumption quoted as a measurement" |
| the Deflated Sharpe "is an **undeflated** one … deflating nothing" | B9's mechanism was refuted and M1 superseded it: at N = 84 it self-reports as a genuine Deflated Sharpe of **0.8997**, which **fails** >0.95 while sitting above all 100 placebo draws |

I did **not** change them. The third one's honest form is "fails the conventional bar *and*
clears the noise floor", and half of that sentence on a public page is worse than the stale
version — it wants the edge lane's wording, not a display fix smuggled in beside an options
feature. **→ edge lane.**

**2. The corrected options book's PER-TRADE ROWS ARE GONE.** `r2_state.pkl` (the 3,885-trade
corrected 187-name book) was a temp file. `data/options_universe/state.pkl` holds only the
**superseded** 3,042-trade pre-correction rows; `UNIVERSE_RESULTS.json` has aggregates only.
Session 5's `BANK_MANIFEST.json` guard protects `data/options_universe/` — but that run wrote
its state outside it, and **a guard on the destination does not help when the run points
somewhere else.** Anything needing the real alert sequence (U7's join at the alert date, any
future streak or timing work) has to re-run the book. Stated now rather than discovered later.

**What P3 measured, for the record** (banked artifacts only, no new backtest): the corrected
book hits **35.3%**, the median trade loses **52.2%** of the premium, **25.0%** at least double
and those are **86.8%** of everything the winners made. Over 20 trades the typical worst losing
run is **5** and **44%** of stretches contain a run of 6 or worse. Outcomes **cluster** — monthly
design effect **2.667** against a shuffled null whose p95 is **1.244** (1,000 shuffles,
p < 0.001), runs of ≥10 losses appear **58** times against a null median of **21** — so the
shipped streak rule reads a measured table, not the Bernoulli formula, which at 20 trades would
put the 95th percentile at 10 against a measured 12 and would cry wolf on ordinary runs.

Also settled: the **37.4% and 35.3% hit rates are not a defect**, they are two universes. Inside
the corrected book the 54 original megacaps hit **37.27%** and the 132 added names **34.04%**.
Every surface now quotes "35–37%" from one source.

Nothing shipped implies the options alerts work; the measured **−6.65pp** gap against random
entry (R2) travels with every payload that carries the shape.
---
> **BLOCKER FOR EVERY LANE, NOT JUST THIS ONE (noticed 2026-08-06 ~19:30 ET): the auto-land
> Action has not merged anything to `main` in over six hours.** `origin/main` is still at
> `3213668` (13:19 ET) while **five** `worktree-*` branches have pushed since — options-live,
> p3-hitrate, optionsbot-lane, data-spend, r1 — and none landed. This is not a merge conflict
> and not a red test: `git merge-tree --write-tree HEAD origin/main` is clean for this branch,
> the workflow file is identical to `main`'s, and all 22 suites pass locally
> (`OVERALL_FAIL=0`). **Someone with the GitHub UI needs to look at the Actions tab** — most
> likely Actions minutes, a disabled workflow, or a stuck `land-main` concurrency group.
> Until it is fixed, nothing any agent produces reaches Render, and `main` is NOT the current
> state of the project. Per `RUN_RULES` and the standing note, do **not** merge by hand.

## AUDIT SESSION 6 (2026-08-06) — U7 and X3. **BOTH PROBES REJECTED/NULL. SESSION 7 MAY OPEN.**

Full write-up: **`HANDOFF_edge_audit.md`**, "SESSION 6". Pre-commitments pushed in `a727bea`
**before any run**, including the expected direction of both probes, so the record can say
whether the expectation was worth anything. It was not. **242/242 edge tests pass.**

| item | verdict |
|---|---|
| **U7** — equity composite as an options VETO | **REJECTED.** Lift −0.57pp (bar was ≥ +1.0pp) at 92.7% retention; all three pre-registered cells negative |
| **X3** — ablate to the best single signal | **NULL.** Full composite beats its best single signal by +4.51%/yr, CI95 [−0.14%, +9.12%] — includes zero |

**THE TWO THINGS DON WOULD WANT TO KNOW FIRST**

1. **The equity model is useless as an options filter, and now we know why.** Inside the
   187-name megacap options universe the composite decile is largely a **market-cap sort**
   (median cap $62.7B at D1 → $133.5B at D9). So the "veto" vetoes a cap bucket — a property of
   the underlying, not of the alert. Applying the identical veto to the five-seed random-entry
   control moves it by the same amount: **interaction −0.08pp**. The bottom decile, the one the
   veto exists to remove, is the **third most profitable** (+10.64%).
   **Consequence: do NOT run U1 (composite → options entry) as written.** The audit called the
   veto "strictly the easier bar"; it failed, with a mechanism.
2. **Two void records were found in the project's own memory and corrected.**
   * `CLAUDE.md`'s theme IC table was labelled "CURRENT 2026-08-04" but is a **pre-B6
     measurement** — proven by reproducing it exactly on the old 110-date panel. `size` moves
     **+1.68 → −0.30**. Against X7's calibrated bar of 2.71, **two of nine themes clear**.
   * **X3 had already been run** (2026-08-03) and the ledger recorded it DONE with "EARNS ITS
     COMPLEXITY" — measured on the pre-B6 panel and against a 1.0pp bar that sits *below* X7's
     1.95pp noise floor. Re-run, it is a NULL.

**THE STRUCTURAL FINDING WORTH CARRYING:** `size` has the **worst** theme IC on the corrected
panel (−0.30) and **carries the composite's entire statistical significance** — adding it last
takes top-decile alpha +4.10% → +7.17% and long-short *t* 1.02 → 2.84. Ranking themes by IC and
adding them greedily measures the wrong thing when a theme's value is its orthogonality. An
*exploratory* leave-one-out (no verdict, nothing changed on it) says dropping
`capital_discipline` would *raise* alpha to +8.54%. **Session 7's first item is a
pre-registered, held-out version of that test.**

**THE COST, PAID:** equity **N 84 → 104** (8 new arms plus 12 from the void run that had never
been logged). **Deflated Sharpe 0.8997 → 0.8789**, and √(2·ln N) **2.977 → 3.048** — past the
Harvey–Liu–Zhu hurdle of 3.0 for the first time. Still above X7's calibrated floor of 0.72.

**Fourth in a row:** the pre-committed expectation ("the veto will help, 60/40") was wrong, after
R10, O20 and the spread toll. Do not reason about the direction of an effect in this project.

**Nothing shipped to the live product.** No weight changed, no live behaviour changed.

---

## AUDIT SESSION 5 — CLOSEOUT (2026-08-06). **SESSION 5 IS CLOSED. SESSION 6 MAY OPEN.**

Full write-up: **`HANDOFF_edge_audit.md`**, "SESSION 5 CLOSEOUT". Pre-commitments pushed in
`416da4b` **before any code changed and before any run started**, including item 3's disposition
in both branches and item 5's multi-seed rule.

All five items in `PROMPT_edge_session5_closeout.md` are done, and both of session 5's open
`BUGS FOUND` are fixed and pinned by tests. **220/220 edge tests pass.**

| item | verdict |
|---|---|
| 1 · autopsy stamps its derived-data coverage | **DONE** — `derived_stamp()` + `derived_comparable()` |
| 2 · `optuniv_run.py` refuses to overwrite a banked result | **DONE** — verified on the real directory |
| 3 · mid-fill (aggression 0.0) decomposition | **DONE** — the void −6.59pp toll is **replaced by −8.28pp** |
| 4 · the four `compute_signals` features, individually | **DONE** — all four NOT informative |
| 5 · how far the seed instability reaches | **DONE** — it does not reach the bootstraps at all |

### The three findings worth carrying

1. **THE SPREAD TOLL IS BIGGER THAN THE RECORD SAID: −8.28pp, not −6.59pp.** The market takes
   **71% of the +11.69% gross edge** at the touch, not 56%. Paired on the 3,764 alerts present in
   both books: **−8.88pp, date-block CI95 [−9.99pp, −7.74pp], 78.8% of alerts worse at the
   touch.** B1 was understating the spread the strategy actually pays (median 4.78% → 6.67%).
   **`HANDOFF_universe_backtest.md` §2a is edited in place** and its claim that *"the old-vs-new
   gap is 100% spread"* is corrected: at the mid the cohorts are +13.60% and +10.43%, a 3.17pp
   gross gap, so **spread explains 68% of the gap, not 100% — breadth dilutes signal too.**
   Still a diagnostic; bar B5 stands and every headline remains at aggression 1.0.
2. **THE SEED INSTABILITY IS IN THE CONTROL DRAW, NOT THE BOOTSTRAP — and that is now measured
   rather than assumed.** Eight seeded statistics × five seeds: seven are single-seed-safe (CI
   endpoints move 1.9%–3.5% of the CI width) and **no published boolean flips on any seed**,
   including `negative_at_significance`. Hold the control fixed and the bootstrap seed is
   irrelevant; vary the control seed and the verdict flips (seed 0 alone: z −0.594, p 0.55;
   5-seed pool: z −4.903). **Session 5's "five control seeds minimum" is the right rule and the
   only place multi-seed changes a decision.** One statistic fires T2 — `effective_n`'s shuffled
   null band moves 35.5% of its width across seeds — and is now multi-seed by policy.
3. **THE CLUSTERING FACTOR OF 1.85 TRAVELLED OUT OF ITS SCOPE. It is 2.212 on the corrected
   book.** 1.848 was measured on the pre-correction 3,042-trade book; Part 6 said so, but the
   headline was quoted onward without the scope into `CLAUDE.md`. So **"below the audit's
   predicted 2–4" is false — 2.21 is inside it, the audit was right**, and every options *t*
   shrinks by **1.487×, not 1.36×**. `UNIVERSE_RESULTS.json` always shipped 2.2121; only the prose
   was wrong. **No verdict changes** (checked: R2 rests on the sign test, and the date-block
   intervals embed clustering by construction rather than applying the design effect as a
   haircut). Corrected in `CLAUDE.md` and in Part 6.

### Item 4 in one line

None of `f_term_slope` / `f_sig_skew_25d` / `f_sig_vrp` / `f_sig_gex_proxy` passes both split
directions. `f_sig_gex_proxy` is one of only **four FDR discoveries among 127 hypotheses** — but
in one direction only, and **the direction that passes SWAPS when B1 is repaired**, as does
`f_term_slope`'s. That is measured support for the both-directions gate: a single-direction gate
would have adopted the same feature twice for opposite reasons and called it replication.

### Item 1 in one line — and what it means for old numbers

**No autopsy figure in the record is comparable to any other, because none carries a stamp.** The
measured damage: the pre-correction book's PBO read **35.71% on 2026-08-03 and 48.57% on
2026-08-05 — same trades, same code path, a 12.9pp move caused only by the miner growing
111 → 315 names.** Treat every pre-2026-08-06 PBO, feature *p*-value, FDR set or feature-coverage
figure as a point-in-time observation quoted with its date, never as a difference against another
session's. Figures read only off the trade rows (item 4's four features) are exempt.

### SESSION 6 — first item and `needs first`

**U7** (the equity composite as an options **veto**) with **X3** (ablate to the best single
signal). Full dependency tables are in `HANDOFF_edge_audit.md`. The three that will bite:

- **the alert↔panel join does not exist yet**, and must take the most recent rebalance date **≤**
  the alert date or it is look-ahead;
- **coverage of the 187 options names inside the 2,710-name panel is UNVERIFIED** — measure it
  before any verdict;
- **X3 must be scored against X7's calibrated bars** (theme IC t 2.71, long-short t 2.14, alpha
  margin 1.95pp, PBO <19.7%), **and must write its arms into `RESEARCH_LOG.md`** — an 8-arm
  ablation takes N from 84 to 92 and lowers the Deflated Sharpe for everything after it. That
  cost is the point of M1.

**Standing items that outrank both if Don wants them to:** **P4** (`seed_book` never sells names
that leave the book) is the only genuinely urgent item — every session the paper track accumulates
under the wrong rules has to be thrown away — and **X8**, the international replication, is still
the only out-of-sample evidence available to either programme. The equity panel's run-to-run
non-reproducibility (the `insider` IC) also remains open and unexplained.

---

## MINER — SIX CACHED NAMES HOLD TWO COMPANIES EACH; MAY-2022 IS A NON-ISSUE (2026-08-07)

Full write-up: **`HANDOFF_miner_remine.md`**, items 6-8.
Lane: data miner (`theta_bulk.py`, `mine_options_cache.py`, `data/options/**`).

**The May-2022 source defect is CLOSED and cost nothing.** Verified with the miner stopped: it
no longer reproduces (22 of 22 probes succeed, including the two names that failed
deterministically twice the day before). It was a transient upstream outage, **not** a permanent
source limitation like the −1 open-interest problem, and the miner needed no repair — its
existing retry rule refilled every affected year unaided. **2022 now has 486 cached year-files,
more than 2021, exactly one interior hole, and every cached 2022 contains all 21 May trading
days.** Net permanent loss: zero. My own "~15 names affected" figure was inflated by stale
`.missing` markers left on years that had already recovered; that is fixed.

**→ GREEKS LANE, ACTION REQUIRED, and this now extends beyond WBD: re-derive AXON, COR and
SNOW.** `data/options_derived/` holds derived frames and blended `-daily.pkl` files for names
whose source cache contains **two different companies**. `COR` is CoreSite Realty until 2021 and
Cencora from 2023; `AXON`, `SNOW`, `SN`, `FIG` and `SNDK` are the same shape. Confirmed by
strike range (AXON steps 10.4 → 275.0 across its gap). Not deleted — another lane's outputs.
**`UNIVERSE_RESULTS.json` and `AUTOPSY_BROAD_RESULTS.json` are CLEAN (zero occurrences of all
nine names checked), so no shipped verdict rests on this.**

**Why it is not just more of the WBD bug, and why no alias table can fix it.** No alias is
involved: the miner asks the feed for a ticker and the feed answers for whoever HELD it that
year. `alias_overlap_conflicts()` is structurally blind to this, **and the fallback can never
repair it, because an alias only fires on an EMPTY span and a reused ticker returns the wrong
company's data instead of nothing.** `META` is the worst case and has no gap at all to catch it:
`META-2021` holds a ~$15 company's chains (9,398 rows, strikes 8-22) between years of 247k and
172k rows at strikes 130-350 — **Facebook's real 2021 was never fetched.** Two screens now ship
and print on every `mine_status.py` run; the fix (per-symbol validity windows) is the miner
lane's #1 next step.

**Also corrected: the "0 faults" reading, for a second reason.** `MINING_PROGRESS.txt` carries
only `[mine]` lines and has never contained a single `[theta-bulk]` line, so the statistic was
quoted from a stream that cannot report it. The real logs show **81 give-ups, 18 chunk halvings,
3 timeouts and 2 client rebuilds** — the run was not fault-free, and the detector was blind to
hangs specifically rather than broken (it fired twice on ordinary errors). The `CALL_TIMEOUT`
fix is confirmed against a live pull (65.3s call bounded to 10.0s with faults counted) but has
**never fired in production** — all three hangs predate it by one minute.

---

## MINER — ~1.00M ROWS OF AT&T OPTIONS WERE CACHED UNDER WBD (2026-08-06)

Full write-up: **`HANDOFF_miner_remine.md`**, item 5 section and BUGS FOUND #7-9.
Lane: data miner (`theta_bulk.py`, `mine_options_cache.py`, `data/options/**`).

**→ GREEKS LANE, ACTION REQUIRED: re-derive WBD.** `data/options_derived/WBD/WBD-2016..2022.pkl`
and `WBD-daily.pkl` were built from contaminated source frames, and `GREEKS_COVERAGE.json`
records WBD `rows_in 1,214,932` across 2016-2025 of which ~1.00M are AT&T's. I did NOT delete
them — they are another lane's outputs. **`UNIVERSE_RESULTS.json` and `AUTOPSY_BROAD_RESULTS.json`
are CLEAN (zero occurrences of WBD), so no shipped verdict rests on this.**

**What happened.** `ALIASES["WBD"] = ["T"]` treated Warner Bros Discovery as the continuation of
AT&T. It is not: WBD continues the DISCOVERY share line, while AT&T merely *distributed* WBD
shares and kept trading under `T`. The alias fallback fires on any empty span, so every WBD year
before the April 2022 listing was filled with AT&T's chains — **WBD 2016-2021 byte-identical to T
(966,790 rows: same keys, same bids), plus 33,964 more in 2022 Jan-Mar.** Corrected to
`WBD -> DISCA` (probed on the feed: DISCA has 2016-2021 and nothing after, WBD the mirror image —
disjoint, as a real rename must be); contaminated years purged and re-mined.

**Why it matters beyond WBD.** A wrong alias and a right one are **indistinguishable at the point
of use** — both return rows, the frames are well-formed, and coverage is high. Hand-checking
cannot be the control. `alias_overlap_conflicts()` now reports any mapping whose cached years
OVERLAP its successor's, which a genuine predecessor never does; it fires on the old mapping even
after the purge, so it would have caught this from the first WBD pull. Alias-supplied years also
write a `.alias` provenance sidecar, and `mine_status.py` prints both.

**Two further miner bugs, same session:** the probe year was hard-coded to 2024, so eight
tradeable names that listed later (CRWV, SNDK, VG, FER, CBRS, HONA, MDLN, SUNB) were filed as
"no data" permanently; and that verdict shared a status with "measured and too illiquid", which is
what let it hide. Both fixed; `no_data_in_range` is now its own status.

---

## D: BACKUP REBUILT — THE SCRIPT IS DONE, THE BACKUP DOES NOT EXIST, THE DRIVE IS DEAD (2026-08-06, r1 lane)

Full write-up in `HANDOFF_backup.md`. Housekeeping lane, nothing under `valuation/**` touched.

**Two claims, only the first is true: the rewrite is finished and 40/40 tested; the backup has NOT
run.** There is no writable target. **The D: drive is at end-of-life — hardware read-only at the
flash controller, not a software flag and not repairable.** `diskpart` reports
`Read-only : No` (attribute clear) alongside `Current Read-only State : Yes` (device enforcing it);
`attributes volume clear readonly` returns "not supported on removable media" and `chkdsk` cannot
run on a volume it cannot write to. **Do not spend more time trying to repair it.**

**ACTION REQUIRED FROM DON — attach a replacement.** An **external SSD**, **exFAT**, any drive
letter, **128 GB minimum** (256 GB comfortable — the miner projects ~199 GB for `data\options`).
Then change two lines at the top of `backup_to_D.ps1` (`$DST`, `$LOG`) and run
`.\backup_to_D.bat dryrun` then `.\backup_to_D.bat`. Nothing else is drive-specific.

**Until then there is no off-machine backup of `.env`, the freeze, or the paper track** — the copy
on D: is from before 02:00 on 2026-08-06, is readable but stale, and can never be updated. Keep the
old drive on a shelf until the replacement completes one successful run.

**Why the drive died, and why the rewrite matters beyond disk space:** `/MIR` over 55,934 files
twice a day is a write-cycle load a USB flash stick does not survive — consumer NAND has no
over-provisioning budget for that, and the controller locked the device read-only rather than lose
data silently. The new allowlist backup writes **20,418 files / 38.01 GB once a day** instead of
55,934 files / 112.04 GB twice — **~5.5× less write load** on the replacement.

**Cause of the disk filling — not what it looked like.** `/XD` is not broken (verified three
ways, including a controlled robocopy experiment). There were **two** backup scripts on **two**
schedules writing to the **same** destination with opposite policies: `backup_now.bat`
(`ValuationToolBackup`, 08:00) used `/E` so it never deleted, excluded only four directories, and
had no `/XJ` — so it followed the ten worktree `data` junctions and duplicated the whole 62 GB
`data\` tree, which is the **61.6 GB of `.claude`** on D:. `backup_to_D.bat` then could not clean
it up, because **`/MIR` does not purge a directory it is excluding** — it never enumerates that
tree at all.

**Fixed:** policy is now an allowlist (back up what cannot be recreated, not what is large),
`/XJ` everywhere, a free-space preflight and a writability probe that both abort in plain English
before copying, a per-run report of what was backed up and what was skipped with reasons, and
stray detection for directories that leave the allowlist. `backup_now.bat` is now a shim onto the
same engine so both scheduled tasks run one policy.

**Numbers:** repo 62.72 GB, `data/` 61.89 GB, backup set **38.01 GB** against a 116 GB drive
(~76 GB headroom). Biggest exclusion is `data\options_derived` at **16.57 GB** — pure arithmetic
over `data\options`, "ZERO vendor option calls". Biggest inclusions are `data\options` 17.40 GB
(45–55 h to re-mine) and `data\backtest_freeze_2026-08` 17.37 GB (the crown jewel: re-downloading
returns restated data). Three irreplaceable items the original brief missed are now backed up:
`data\archive` (our own past scans), `valquo_track*` (the live forward paper track, written by
Cowork, by nothing in this repo), and `app.db` (user/Stripe state).

**Before touching D: I verified it was pure redundancy:** 59,081 files compared path by path
against C: — exactly 2 distinct files existed only on D:, both rescued to
`data\_from_D_quarantine\`. Nothing on D: was deleted.

**Tests:** `tests/test_backup_to_D.ps1`, **40/40**. Windows/PowerShell, so the Linux CI job does
not run them — run by hand after touching the backup. Python suites unaffected: 14/14
factor-alpha, 13/13 fragility, 191/191 edge.

**Watch this:** the miner projects ~199 GB for a full 1,000-name `data\options`. That will not fit
on a 128 GB target and it is the next thing that breaks the backup. Also **format the replacement
exFAT, never FAT32** — FAT32's 4 GB per-file ceiling is already close (largest backed-up file is
`sep.csv` at 3.00 GB, and the next freeze will likely exceed 4 GB).

---

## AUDIT SESSION 5 — THE OPTIONS ENTRY SIGNAL IS DEAD, AND IT SURVIVED THE CORRECTION (2026-08-05)

Full write-up: **`HANDOFF_edge_audit.md` Part 6**. Pre-commitments and run design pushed in
`c64a6b1` **before any run started**; R2's and R7's bars were already written in Part 0 and were
quoted unchanged, not restated in altered form.

**Items completed: R2, R3, R7, O20.** `HANDOFF_universe_backtest.md` is now banner-marked
**SUPERSEDED — do not quote any number in it.**

### The verdict

The 187-name options study was re-run with the universe **pinned** to the previous run's frozen
name list, so the B1/B2/B3/B4/B15 corrections were the only variable.

| | pre-correction | **corrected** |
|---|---|---|
| real / control expectancy | +5.14% / +13.22% (2 seeds) | **+3.41% / +10.06% (5 seeds)** |
| gap | −8.08pp | **−6.65pp** |
| date-block CI95 on the gap | never computed | **[−11.92pp, −2.13pp]** |
| paired sign-test z | −5.185 | **−4.903 (p < 1e−5)** |
| paired *t* | −2.183 | −1.227 (p 0.220), not significant |

**The gap moved 0.61pp.** Five defects repaired, every level moved, the conclusion did not. Per
the pre-committed rule, the condition for "the entry signal is dead" is met. **The live options
alert must not be described as a day-selection edge — it is an alert-generation mechanism.**

### What DID change, and it is large

- **The breadth claim is VOID.** The 133 new names are now **−0.47%/trade (PF 0.988)**, against
  +3.90% before. All of the book's positive expectancy is the original 54 megacaps (+9.37%). The
  edge does **not** survive breadth; a corrupted price basis made it look broader.
- **B1's signature:** trades rose 3,042 → 3,885 because `no_contract_in_band` rejects fell
  2,911 → 1,729 — an adjusted spot against as-traded strikes was throwing the moneyness
  prefilter and silently discarding 1,182 alerts. **Median entry IV 1.4200 → 0.2497** at 100%
  coverage (was 75.3%). The 1.28–1.57 median that §8 of the old handoff recorded as an
  unexplained anomaly *was* the bug.
- **Deflated Sharpe fell below 95% on both books:** unfiltered 88.13% → 49.59%,
  term_slope-filtered 95.69% → 80.63%. Autopsy re-confirms: 64 features, 127 hypotheses, **zero
  survivors**.

### A SINGLE CONTROL SEED CAN FLIP THIS VERDICT — measured, then closed

The control's own mean ranges **+6.46% to +15.34%** across five draws. Seed 0 alone reads
INCONCLUSIVE and is the most favourable of the five. So the control was run at **five seeds**
rather than the record's two:

**All five point estimates are negative; four of five are negative at significance.** Pooled over
29,785 control trades the sign test is **z −4.903 (p < 1e−5)**, essentially the record's own
−5.24, reached on corrected data under clustered inference. **More control draws SHARPEN the
test** (2-seed z −2.907 → 5-seed −4.903) because each name-year cell's control mean averages more
draws. The paired *t* ranges +0.162 to −1.835 and is never significant even pooled — it is the
wrong statistic here. **Standing rule: five seeds minimum, and the sign test carries the
verdict.**

### R7 — the floor passes and the filter fails anyway

`term_slope`'s +8.89pp out-of-sample replication was an artefact. Corrected, the filter makes its
own out-of-sample book **worse**: gain **−1.12pp** against the +5.00pp bar, and it is no longer
tail-enriching. It **passes** the re-committed floor (G3a 95.6 alerts/yr, G3b 96.2% of names and
98.2% of months, G3c 35.9%), so the old 40% constant *was* rejecting a genuinely broad filter —
but the rejection now rests on economics rather than on an underived number. **REJECTED.**

### R3 — clustered inference, and a trap avoided

`valuation/edge/options_stats.py` adds the date-block bootstrap, `n_eff`, the paired sign test and
paired *t*, purge/embargo for CSCV, and the DSR at `n_eff`. **Measured clustering factor 1.85 —
below the audit's predicted 2–4** — so every options *t* shrinks ~1.36× and **no verdict changes.**

The paired sign test and paired *t* the whole options conclusion rested on **existed in no shipped
file**. They now reproduce the record exactly (441 of 1,052 cells, z −5.185 vs the recorded
−5.24), pinned by a test.

**A raw design effect is not evidence of clustering** — found by a failing test: 600 independent
draws in 12 blocks of 50 report a design effect near 1.8, pure sampling error. It is now scored
against its own shuffled null (the X7 method); the real book passes clearly (1.848 vs p95 1.266).
**Never quote a design effect without its null.**

### O20 — the audit expected the headline to fall; it rose

PIT-liquid 3,359 trades at **+4.82%** vs PIT-illiquid 495 at **−7.84%**, coverage 99.2%. **It does
not rescue the signal**: the control is screened by the same rule and benefits too, so on the
liquid subset the real book loses to random entry *more* decisively (z −3.475, p 0.0005). The
headline stays the whole book at aggression 1.0.

The audit's premise is half wrong: names were ranked into the mining pool by **today's market
cap** (true), but the liquidity screen was already applied to the **first cached year**, not to a
present-day chain. So O20 is an **upper bound** on the repair — names that would have failed in
2016 were never mined.

**THE PATTERN:** third time in two sessions (R10, then O20) that a bias assumed to run in the
strategy's favour ran the other way. **This project's expectations about the direction of its own
biases have been wrong more often than right. Measure them.**

### Open, in priority order

1. ~~X7's placebo at the true N = 84~~ **DONE — the row is CONFIRMED and the PROVISIONAL
   marking is LIFTED.** Re-run at N=84 on the identical panel and seeds: **0 of 100 noise draws
   clear 0.95** (was 2 at N=8) and the calibrated bar falls 0.8567 → **0.7216**. The edge's
   0.8997 fails the >0.95 convention **and exceeds all 100 placebo draws** (max 0.8649) — at the
   honest N that convention is stricter than the noise floor requires. Every other rate in X7's
   table is identical across the two sweeps. Free side effect: CPCV adopts on **27% → 21%** of
   noise draws. Full entry: `HANDOFF_edge_audit.md` Part 6.
2. **Find the run-to-run non-reproducibility.** `insider` median IC still varies across
   identical-data runs.
3. **P4 / `seed_book` never sells names that leave the book.** Out of band, live-product defect.
4. **X8** — the international replication. Still the only out-of-sample evidence available.
5. Remaining audit sessions: U7/X3, U2/U1/U6, O1 onward, B23.

---

## AUDIT SESSION 4 — THE WORD "ALPHA" SURVIVES; THE DEFLATED SHARPE DOES NOT (2026-08-05)

Full write-up: **`HANDOFF_edge_audit.md` Part 5**. Pre-commitments pushed in `4f41c9f` **before
any run started**; R1's own pre-commitment (`HANDOFF_r1.md` section 1) was honoured **unchanged**.

**Items completed: R1 (re-run), R9, R10, M1.** All four ship in `BACKTEST_RESULTS.json`.

### The headline, as it now stands

| quantity | value | notes |
|---|---|---|
| top-decile alpha | **+7.17%** | now with **t 4.517 / HAC t 4.376**, hit rate 71% (R9) |
| long-short t | **2.620 (HAC)** | naive 2.836; Ljung–Box p=0.036 rejects independence (R9) |
| FF5+MOM alpha | **+6.99%/yr, NW t 3.984** | range +5.1% to +10.9% across six specs (R1) |
| excess vs SPY | **+9.99%/yr, HAC t 3.770** | the investable benchmark (R10) |
| Deflated Sharpe | **0.8997 at N=84** | **FAILS the >0.95 bar** (M1) |
| PBO | 73.3% | uninformative — its bar sits at the noise level (session 3) |

### R1 — CLEARED AGAIN, at a lower level and with a REVERSED mechanism

The pre-registered threshold ("alpha" only if the FF5+MOM intercept is positive with NW t > 2.0)
is met by **all six** specs — compound/sum × full/first half/second half, spanning **+5.08% to
+10.85%**. No disagreement, so the NULL veto does not trigger. **CLAIM A applies; the word
"alpha" is permitted, as a range.**

**The old +8.81%/yr and the +6.6%–8.8% range are VOID and must not be quoted.**

**The mechanism reversed on two of three legs and this is the part to re-read.** Now loading:
**HML (t +2.93)** and **UMD (t +3.65)**. NOT loading: **SMB (t +1.39)** and **RMW (t +0.90)** —
both loaded strongly before (t 3.84, t 4.49). The old story "`size`, `quality`, `momentum` ARE
the standard premia" is backwards on size and profitability; the book now carries a real VALUE
tilt, and the size/profitability exposures that dominated the old story were largely an artefact
of the window B6 removed. R² fell 0.465 → 0.308.

**Caveat that must travel:** the secondary q-factor model does NOT clear on the first half
(q4 t 1.712, q5 t 0.702) though it clears on the full sample and second half.

### M1 — the last bar the project claimed to clear now fails

Trial counts measured from the populated `RESEARCH_LOG.md`: **equity 84, options 133, infra 1,
total 218** (audit estimated ~146; 15 `FIXED` correctness rows correctly do not count).

With `N = 84` instead of 8: **Deflated Sharpe 0.9970 → 0.8997**, `sr0` 0.242 → 0.406,
`_trials_haircut` 2.04 → **2.977** (within 0.03 of the Harvey–Liu–Zhu hurdle of 3.0, as the audit
predicted). **Pre-committed consequence fires: the edge does NOT clear the Deflated Sharpe bar.**

**Audit B9 is resolved by measurement, not argument.** It argued the statistic was an undeflated
PSR because `sr0` collapsed. With a real N it does not — the statistic self-reports as a genuine
`deflated_sharpe_ratio` for the first time. The price of fixing it is failing the bar.

`N` is **domain-scoped** (equity charged 84, not 218 — the options autopsy is a different search
for a different product). A missing log degrades to `N = 8`, the OLD behaviour, never to zero
penalty.

### R9 — the product's headline number finally has a significance statistic

`top_decile_alpha` shipped with none at all. Now **t 4.517, HAC t 4.376, 71% hit rate**. The
long-short gains **HAC t 2.620** and Ljung–Box. **Ljung–Box rejects at p = 0.036**, so the NW t is
now the number quoted and the naive 2.836 is a diagnostic. The long-ONLY object is far better
measured than the long-short the project has always led with.

### R10 — the expectation was wrong in the strategy's favour

Both the audit and this session's pre-commitment predicted the uninvestable equal-weight benchmark
was flattering the product. **It is the hardest of the four.** The equal-weighted panel returned
+18.14%/yr against SPY's +15.32% over 2009-2026, so excess vs SPY is **+9.99%**, higher than the
+7.17% published. **Keep publishing +7.17%** — most conservative, and comparable with history.

### Open, in priority order

1. **Re-run X7's placebo at the true N.** Pre-committed in Part 5 and NOT optional: X7's
   "Deflated Sharpe survives calibration" was measured with N=8 on both sides. The absolute claim
   is already dead; the relative comparison is untested. ~3 hours.
2. **Find the run-to-run non-reproducibility.** `insider` median IC still varies across
   identical-data runs. The headline path is deterministic; the per-theme path is not.
3. **R2** — the options re-run. B1/B2/B3/B4/B15 fixed and unmeasured.
3. **P4 / `seed_book` never sells names that leave the book.** Out of band, live-product defect.
4. **X8** — the international replication. This is the only out-of-sample evidence available;
   R1 is a control, not new data, and the project has still only ever seen one panel.
6. Remaining audit sessions: R3/R7, U7/X3, U2/U1/U6, O1 onward, and B23.

---


## AUDIT SESSION 3 — EVERY THRESHOLD IN THE PROJECT IS NOW CALIBRATED (2026-08-05)

Full write-up: **`HANDOFF_edge_audit.md` Part 4** (X7 and X2 entries + BUGS FOUND + what was
not done). Pre-commitments were written and pushed in `1276e4b` **before any run started**.

**Items completed: X7** (placebo through the full pipeline, N = 100) and **X2** (rebalance-grid
offset, 7 full-universe runs). **199 tests green** across the edge suite.

### The four calibrated numbers — use these, not the old conventions

| bar | as used | calibrated | pure noise clears the OLD bar |
|---|---|---|---|
| theme IC t | 2.0 | **2.71** | **39%** of draws |
| long-short t | 2.0 | **2.14** | 8% |
| top-decile alpha margin | 1.0pp | **1.95pp** | 18% |
| PBO | < 50% | **< 19.7%** | **55%** |
| Deflated Sharpe | > 0.95 | **stands** | 2% |
| held-out gate | — | **6% false-positive rate** | — |

Floors for THIS panel / universe / 69 dates. Not universal constants.

### Two shipped claims were WRONG and are corrected in CLAUDE.md

1. **"Long-short t 2.836 is below the Harvey–Liu–Zhu hurdle of 3.0" — a GRID ARTEFACT.** The
   rebalance grid always started at a hard-coded TD = 252; 62 other equally valid grids existed
   and none had ever been run. Across offsets 0/5/10/20/30/40/50 (all 69 dates, identical
   window): **t ranges 2.703 → 3.517, median 2.926, and clears 3.0 on three of seven.** Quote
   **"t 2.7–3.5 depending on grid, straddling the hurdle"** — never one side of 3.0 as a fact.
2. **"PBO 73.3% fails the < 50% bar" — the BAR is meaningless.** The placebo's MEDIAN PBO on a
   definitionally worthless signal is **46.7%**, so "< 50%" sits at the noise level. PBO is
   uninformative here in either direction. (It is, separately, above 50% on 7 of 7 grids, so
   Session 2's blow-out is a real property of the corrected panel — it just is not evidence.)

### What the headline IS entitled to claim

- **Top-decile alpha is the one headline that passed its robustness test outright:** spread
  across seven grids only **1.30pp** — median **+7.52%**, range **+6.84% to +8.14%** — against
  a placebo null of [−1.33pp, +2.38pp]. The equal-weight benchmark moved 2.08pp across the same
  grids, MORE than the alpha, which is what makes the stability credible rather than lucky.
- The real result is outside the placebo's [2.5, 97.5] interval on alpha (clearly), Deflated
  Sharpe, monotonicity, max theme IC t (narrowly) and long-short t (narrowly) — and **inside it
  on PBO**. On one grid of seven (offset 50, t 2.703) the long-short t is below the placebo's
  own p97.5 of 2.729.
- **The Deflated Sharpe SURVIVED calibration** (noise median 0.28, ≥ 0.95 in 2% of draws). That
  is a measured partial defence of the statistic item B9 attacked; B9's surviving criticism was
  the trial denominator, which this does not touch.

### The finding that most affects future runs

**On pure noise, CPCV adopting a weight scheme inflates the measured long-short t by ~+1.4.**
Draws where CPCV did not adopt (73): mean t **−0.065** (se 0.119), a textbook null. Draws where
it did (27): mean t **+1.343** (se 0.184), mean alpha +0.82pp. It fires on **27%** of noise
draws. Mechanism: adopted weights are chosen on the same panel the headline is measured on.
**The shipped strategy is unaffected — it does not adopt** — which is measured support for the
existing "CPCV rejects → keep defaults" rule. Post-hoc, not pre-registered; wants replication.

### Reproducibility

The offset-0 grid reproduced the Session-2 shipped numbers **to every digit** (t 2.8360640685,
alpha 0.0717414233, PBO 0.7333333, n 69). Given the project's known run-to-run
non-reproducibility this was not a formality — it is the first clean reproducibility PASS on the
corrected panel. It does **not** resolve the `insider` per-theme non-determinism.

### No shipped decision changed

`low_risk` stays zeroed, `insider` stays at 0.125, weights stay at defaults. What changed is the
size of the claims the record is entitled to make.

### Open, in priority order

1. **Re-run R1 on the corrected panel** — still the top task. It now has a partial floor: the
   raw alpha it decomposes is far outside the placebo null, so R1 is decomposing something real.
   X7 does **not** calibrate R1's own FF5+MOM intercept; if the re-run lands near its threshold,
   push the placebo series through `scripts.factor_alpha` first.
2. **Find the run-to-run non-reproducibility.** Three runs on identical data gave `insider`
   median IC −0.00335 / +0.01551 / −0.00339. The headline path is now shown deterministic; the
   per-theme path is not.
3. **R2** — the options re-run. B1/B2/B3/B4/B15 all fixed and unmeasured.
3. **P4 / `seed_book` never sells names that leave the book.** Out of band, live-product defect,
   still open, still urgent.
5. **B23** (speed) and the remaining audit sessions: R3/R7, U7/X3, U2/U1/U6, O1 onward.

---


## AUDIT SESSION 2 — THE HEADLINE FELL, AND B6 IS THE WHOLE REASON (2026-08-04)

Full write-up: **`HANDOFF_edge_audit.md` Part 3** (twelve per-item entries + BUGS FOUND).
Commits: `adcd85a` (the corrections) and `018ebc2` (the ledger, RUN_RULES.md, attribution
toggles). Both pushed and verified on `origin/worktree-options-live`.

**Items completed:** B2, B4, B5, B6, B7, B11, B13, B17, B21, B22, B25. **B23 deliberately
deferred** (speed item; changing panel construction in the same commit as the run validating a
change to panel construction is the wrong risk trade). **617 tests green across all 18 suites.**

### The headline, on the corrected panel

| | S1 final | **S2 corrected** |
|---|---|---|
| rebalance dates | 110 | **69** |
| long-short t | 3.851 | **2.836** |
| top-decile alpha | +11.69% | **+7.17%** |
| monotonicity | −0.988 | **−0.891** |
| PBO | 13.3% | **73.3%** |
| equal-weight benchmark | +16.55% | **+18.14%** |
| breakeven one-way | 236 bps | **134 bps** (vs 33.4 bps measured) |

**TWO OF THE THREE BARS NOW FAIL.** Long-short t 2.836 is BELOW the Harvey–Liu–Zhu hurdle of
3.0 it used to clear, and PBO 73.3% is far above the <50% bar. Only the Deflated Sharpe still
passes, and per B9 that is computed against N=8 when the ledger records ~146 trials — it was
never the bar to lead with. **Do not quote the old numbers. Do not describe the edge as
clearing its bars.**

### Attribution — one change per run, full universe

B6, B7 and B13 all move the panel and all landed in one commit, which broke the
one-change-per-run rule. Three toggles were added (`EDGE_AUDIT_B6_LEGACY_TRUNCATION`,
`EDGE_AUDIT_B7_LEGACY_COMPOSITE`, `EDGE_AUDIT_B13_PREFILTER`, each defaulting to the corrected
behaviour) and a full-universe sweep run to separate them.

| run | n | ls_t | alpha | PBO | EW bench |
|---|---|---|---|---|---|
| S1 final (all 3 defects present) | 110 | 3.851 | +11.69% | 13.3% | +16.55% |
| **A — B6 reverted** (B7+B13 fixed) | 110 | 3.733 | +11.36% | 26.7% | +16.26% |
| **B — B7 reverted** (B6+B13 fixed) | 69 | 2.846 | +7.17% | 73.3% | +18.14% |
| **C — B13 reverted** (B6+B7 fixed) | 69 | 2.715 | +7.68% | 73.3% | +18.38% |
| **S2 shipped** (all 3 fixed) | 69 | 2.836 | +7.17% | 73.3% | +18.14% |

- **B6 alone: t −0.897, alpha −4.18pp, PBO +46.7pp.** 100% of the PBO blow-out, 88% of the t
  drop, 89% of the alpha drop. It is the entire move and it is not close.
- **B7 alone: NULL** — t −0.010, alpha +0.01pp, PBO and equal-weight unchanged to the digit.
  A correctness fix with no performance consequence, which is the ideal outcome for one.
- **B13 alone: small, both directions** — t +0.122, alpha −0.51pp, EW −0.24pp. Dropping 384
  penny names helps the long-short and costs the long-only book.

**What B6 was.** `price_history` ended in `.tail(days)`, so every ticker kept its OWN last N
rows and the panel calendar was the UNION of those windows. At a 2001 cross-section every name
present was one that had already stopped trading by roughly 2019 — the inverse of classic
survivorship bias. The calendar is now cut ONCE, before the ffill. The panel went from a
27.3-year union to a genuine 18.5-year window: **2008-01-16 → 2026-07-24, 69 dates,
cross-sections 1,471–1,954**, shipped every run as `panel_window`. 41 dates dropped, against
the audit's estimate of 37.

**The honest reading:** roughly 40% of the top-decile alpha was coming from those 41
uninterpretable early dates. State it as a hypothesis, not a finding — a repair's effect on a
fitted statistic is not evidence about the repair.

**What did NOT change: any shipped decision.** `low_risk` is still `confirmed` in both split
directions (delta t +1.383 / +1.518), `insider` still `rejected`. Two non-adopted themes swapped
between two flavours of "no". The weights ship unchanged.

**`size` +1.68 → −0.30 is the documented mechanism, not a surprise** — the small-cap premium
worked pre-2012 and B6 deleted everything before 2009. **`insider` +2.69 → −0.24 is the
anomalous session-1 run reverting** to the other two runs' values (−0.34, −0.43); it is not
evidence about B6 or B7, and this theme's t remains unmeasurable.

### R1 IS NOW PROVISIONAL AND MUST BE RE-RUN — TOP PRIORITY

R1's +8.81%/yr FF5+MOM alpha was measured over "109 windows, 1998-12-31 → 2026-01-21" — the
pre-B6 union calendar, whose first third had the inverted universe. That panel no longer
exists, and the raw object R1 decomposed fell +11.69% → +7.17%. **Do not quote +8.81%/yr or the
+6.6%–8.8% range until `python -m scripts.factor_alpha` has been re-run on the corrected
panel.** The direction of R1's finding may survive — loadings are a separate question from the
level — but every number in it is provisional.

### Other session-2 outcomes worth carrying

- **B25: the audit was WRONG and it is recorded.** The two Deflated Sharpe implementations are
  algebraically identical in the test statistic and now agree to **exactly 0**. One real defect
  was underneath it — the autopsy approximated `sr0` with a sampling variance where
  Bailey–López de Prado specify the CROSS-TRIAL variance; the panel was right all along.
- **B11: the "37 bps actual cost" was never computed anywhere.** It was a model assumption
  quoted as a measurement. `realised_one_way_bps` is now measured: **33.4 bps against a 134 bps
  breakeven, a 4.0x margin.** The edge still survives costs comfortably.
- **B17: the "top-25" book is really a ~42-name book** (`held_median` 42, exit_rank 50) and
  pays neither costs nor taxes, unlike every other book in the file. Now labelled.
- **B21: sector caps are a clean NULL** — 5 bps of net alpha across none/25/30/40%. The book is
  not sector-concentrated enough for a cap to bind. Measured, not adopted; do not re-open.
- **B13: PARTIAL.** `prefilter` now runs in the backtest and rejects 384 penny names, but
  `MIN_AVG_DOLLAR_VOLUME` still cannot bind — the price export carries `date` + `close` only.
  Shipped as `prefilter_adv_wired: false` with the reason. Wiring SEP volume is open work.
- **B22: a failure inside `costs` used to discard four blocks with no marker** while `errors: []`
  stayed empty. All 12 blocks are stamped now, plus a pre-write schema check. Verified on the
  corrected run: `errors` absent, all 12 present.
- **B2/B4/B5 are options-side correctness fixes, none re-measured yet** — they fold into R2.
  B5's four paper-track defects ALL flattered the track, so its pre-fix history is not
  comparable to post-fix outcomes.

### Open, in priority order

1. **Re-run R1 on the corrected panel.** Everything else about the headline waits on this.
2. **Find the run-to-run non-reproducibility.** Still unexplained. Three runs on identical data
   gave `insider` median IC −0.00335 / +0.01551 / −0.00339. Until this is fixed no marginal IC
   is trustworthy, and the project's memory is its results files.
3. **R2** — the options re-run. B1/B2/B3/B4/B15 are all fixed and unmeasured; no absolute
   options number in the record is citable until it lands.
3. **P4 / `seed_book` never sells names that leave the book.** Out of band, live-product defect,
   still open, still urgent.
5. **B23** (speed) and the remaining audit sessions: X7/X2 noise floor, then R3/R7, U7/X3,
   U2/U1/U6, O1 onward.

---


## R1 SETTLED — THE HEADLINE IS NOT JUST FACTOR EXPOSURE (2026-08-04, `r1` lane)

Full write-up: **`HANDOFF_r1.md`** (pre-commitment in section 1, written before any number).
Prompt: `PROMPT_r1.md`. Audit item: **R1, "the single most important test in this document".**

**The pre-registered bar was: the word "alpha" is permitted only if the FF5+MOM intercept is
positive with Newey-West t > 2.0. It cleared it.**

- **`top - ew` (the headline's own object, = `top_decile_alpha` / 4): FF5+MOM alpha
  +8.81%/yr, NW(1) t = +5.742, R2 0.465, n = 109** non-overlapping 63-trading-day windows,
  1998-12-31 -> 2026-01-21, full 2,710-name universe, deployed flat 1/7 weights.
- **Hou-Xue-Zhang q4: +9.14%/yr (t +5.23). q5: +8.33%/yr (t +4.37). Long-short: FF5+MOM
  +12.12%/yr (t +4.14), q4 +12.99%/yr (t +3.20).**
- Raw unadjusted was +12.13%/yr, so **the factor models absorb roughly 27% of the headline and
  leave the rest.** That was NOT the pre-registered expectation, which said most would go.
- **Passes all four pre-registered specs** (compound/sum aggregation x full/ex-B6), every
  subperiod, every NW lag 0-8, **net of costs (+7.85%, t 5.16)**, and a spanning test that adds
  the equal-weighted universe's own excess return as a 7th regressor (+8.25%, t 5.88).
- **Quote the RANGE +6.6% to +8.8%/yr**, or the conservative **+6.6% (t 4.41)** — that is the
  figure after dropping the 37 B6-contaminated early dates.

**Mechanism.** SMB +0.39 (t 3.84), RMW +0.30 (t 4.49) and UMD +0.18 (t 3.49) all load
significantly — `size`, `quality` and `momentum` really are the standard premia and the factors
do absorb them. **HML (t 1.08) and CMA (t 1.08) do NOT load** — Valquo's `value` (six ratios,
EV re-priced at the rebalance date) and `capital_discipline` (issuance/accruals) are not what
FF's value and investment factors measure. MKT loading on the spread is +0.007: market-neutral
by construction.

**Not a benchmark artifact.** Alpha is linear: a(top - ew) = a(top) - a(ew) = 14.60 - 5.80 =
8.81 exactly, so the +5.80%/yr (t 5.41) that FF5+MOM fails to explain about the equal-weighted
universe **cancels out of the spread**. The spanning test confirms it (universe loading +0.10,
t 0.63, insignificant).

**Reconciles with X4 rather than contradicting it.** Over X4's own 2014+ window R1 gets alpha
+6.06% (t 3.16) where X4 got t 1.10 vs an ETF blend. Different tests: X4 differences two
high-variance total-return series (low power, practical question); R1 removes that variance
first (high power, statistical question). **X8 says the premia are real and general, R1 says
the headline is more than those premia, X4 says the retail-substitute margin is still
unproven. All three stand at once.**

**Caveats that must travel with the number.** (1) Still ONE panel — a regression is a control,
not new data; **X8's international replication is the out-of-sample evidence, R1 is not.**
(2) **t 5.74 is NOT multiplicity-corrected** — audit M1 is still open; mitigating, the deployed
weights are flat 1/7 and were never tuned. (3) FF5+MOM is a poor description of this universe
(+5.80% unexplained on the EW universe itself), so read every loading as approximate.
(4) SMB +0.885 on the book — small-cap tilt, unhedged; borrow/impact/capacity not modelled.
(5) `top - ew` is still measured against an uninvestable benchmark (audit R10).

**Note on "product copy":** the app went owner-only the same day (PRIVATE_MODE, section below),
so there is currently no public copy for this to govern. The claim discipline still applies to
how the project describes itself in `CLAUDE.md`, the roadmap and any future public write-up.

**Roadmap effect — opposite of what R1 anticipated.** The audit said a null would make further
signal hunting "close to worthless" and construction/cost/tax the entire remaining edge. The
pass says there is a residual worth understanding. Recommended next: **(1) attribute the
+8.81% across themes** by re-running this regression on each theme's own decile spread (cheap
now that the machinery exists; converts inferred mechanism into measured); **(2) M1, the trial
ledger** — now the largest unquantified threat to the headline; **(3) the forward paper-track
vs SPY remains the top overall priority (Cowork's lane)** — R1 adds no out-of-sample evidence.

**FRAGILITY (Part II, same lane, same day) — it SURVIVED a deliberate attempt to break it, on
all four criteria committed before any cut ran. But two things must travel with the number:**

- **It is WINDOW-DEPENDENT.** Stable-universe window (>=2008, the closest available preview of
  what B6 will do): **alpha +6.24%, t +3.986, n 73 — DOWN 2.57pp, ~29% of the alpha.** The
  discarded early period is where the raw spread is biggest (first third raw +21.89%/yr vs
  +3.53% and +11.02%) — the inverted-universe signature. **Expect the post-B6 headline near
  +6%. Quote ~+6% when a single number is wanted.**
- **There is a WEAK DECADE.** A ~10-year rolling window centred on **2009-2019 shows alpha of
  only +1.66% (t 1.39)**. Alpha is positive in **70 of 70** rolling windows and never reverses
  sign, but 8 of 70 are not significant. The full-sample t 5.742 averages that decade in with
  much stronger ones.

The other cuts: no sign flip (halves +8.98%/+5.48%; thirds +13.51/**+4.33 t 2.412, weakest cell
in the study**/+8.10, all t>2). **Not concentrated** — best 5 of 109 periods carry 23.0% of the
alpha (38.0% on the stable window, the closest any criterion came to tripping); dropping the
best 5 leaves +7.28% (t 5.19), dropping the worst 5 gives +10.07%, nearly symmetric, and the
best 5 span four regimes. **Not specification-dependent** — CAPM +12.99%, FF3 +12.28%,
FF5-no-MOM +10.03%, FF5+MOM +8.81%, q4 +9.14%, q5 +8.33%, all t>2 on both windows, and FF5+MOM
is nearly the most conservative of the six. Windows confirmed **genuinely non-overlapping**
(every one exactly 63 factor days, zero shared days) so no inference correction is needed.

**BINDING RE-RUN CONTRACT — R1 MUST be re-run after B6 and B7 land.** B6 is expected to lower
alpha to +5.5-7.0% (t 3.5-4.5); B7's direction is genuinely unknown and the two interact, so do
not attribute the combined change to either alone. **A post-re-run alpha < +4%/yr or full-sample
t <= 3.0 is a MATERIAL REVISION requiring the headline to be rewritten rather than annotated; a
stable-window t <= 2.0 withdraws the word "alpha" entirely and CLAIM B applies.** Re-run is
cheap: `python -m scripts.etf_benchmark` then `factor_alpha` then `factor_alpha_fragility`.
Full contract in `HANDOFF_r1.md` sections 6-8. Part II adds
`scripts/factor_alpha_fragility.py` + `tests/test_factor_alpha_fragility.py` (13/13).

New files only, panel untouched (Session 2 owns B6/B7): `scripts/factor_alpha.py`,
`tests/test_factor_alpha.py` (14/14), `HANDOFF_r1.md`, and output
`data/free_analysis/FACTOR_ALPHA_RESULTS.json`. The script asserts it reproduces X4's shipped
strategy series to 9.7e-17 and asserts an alignment check (SPY excess on MKT: beta 0.9562,
R2 0.9888, alpha +0.19%/yr t 0.45) so a future date-misalignment cannot pass silently.

---

## THE APP IS NOW PRIVATE — OWNER ONLY (2026-08-04, app-fixer lane)

Full write-up: **`HANDOFF_appfixes.md`** (Session 9). Prompt: `PROMPT_appfixer_private.md`.

**Valquo is now a personal research tool, not a product.** This is a deliberate LICENCE
posture: ThetaData's Individual plan and Sharadar's individual terms permit personal use and
forbid redistribution or business use. One user, no commercial activity, nobody else reading
vendor-derived numbers => those terms are cleanly satisfied.

- **One flag: `PRIVATE_MODE`, default `true`** (`valuation/config.py`, declared in
  `render.yaml`). Read in two places only: three derived `Config` properties, and
  `valuation/saas/private.py`, which owns the request policy and is called first in `_guard`.
- **It outranks `OPEN_ACCESS`, `BETA_ALL_PREMIUM`, `FEATURE_BILLING=on` and a configured
  Stripe key** — each asserted separately. Anonymous visitors and signed-in non-owners get a
  plain holding page or a 401; the recruiter `/demo` link is refused; no payment can be
  initiated (checkout/portal 403).
- **NOTHING DELETED.** Every tier, route, template and Stripe path is intact and still tested.
  `PRIVATE_MODE=false` restores the public product — `tests/test_saas.py` and
  `tests/test_security.py` now run with it off precisely to keep that a tested claim.
- **The crons are unaffected.** All `/admin/*` routes reach their `X-Admin-Token` check
  unchanged (they never used a session); pinned by a test that uses a deliberately wrong token
  so it cannot accidentally run a scan.
- **Vendor audit done.** No raw ThetaData and no raw Sharadar rows are exposed on any page or
  API route. Sharadar reaches the web only via owner-only `/api/edge/*`, which returns
  aggregate statistics (walk-forward folds, ICs, Sharpes, counts). Derived constants measured
  on licensed panels do exist in `screener/settings.py` and `edge/options_paper.py` — reported
  as the separate category they are. Per-surface table in `HANDOFF_appfixes.md`.
- **THE FORWARD TRACK IS NOW BACKED UP INTO GIT.** It was single-homed on one Render disk and
  is the only dataset in this project that cannot be re-derived. New weekly `track-backup`
  GitHub Actions workflow pulls `/admin/export-track` and commits `data_export/`
  (`paper_track_history.json` + three CSVs + a README). Rewrite-in-full and deterministic;
  **refuses to commit an export with fewer index days than the one already committed**, so a
  service that comes up on a fresh disk cannot silently erase months of record. Don gets it
  with `git pull`. **Run it once by hand from the Actions tab before ever touching Render.**
- Tests: **`tests/test_private.py`, 22 new.** All suites green.

**Not yet done / needs Don:** the workflow has never run against the live service (it needs
`SITE_BASE_URL` + `ADMIN_TOKEN` as Actions secrets, which auto-scan already uses); this is the
first workflow in the repo that commits to `main`; the paper track still does not run at all
until `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID` are set on Render (Session 6).

---

## READ FIRST — AN EXTERNAL AUDIT HAS INVALIDATED SEVERAL HEADLINE CLAIMS (2026-08-03)

Full ledger: **`HANDOFF_edge_audit.md`**. Source: `VALQUO_EDGE_AUDIT.md`, a 108-item
code-reading review by an outside session. Session 1 of 8 is done — step 0 plus thirteen
Part I corrections. **What follows is what changed about what the project believes it knows.**

**Three claims in `CLAUDE.md` were unsupported and are now corrected in place:**

1. **The Deflated Sharpe: the audit's MECHANISM is refuted, its COUNT criticism stands.** It
   argued the eight weight schemes are indistinguishable so `SR0` collapses to ~0 and nothing is
   deflated. **Measured on the corrected full-universe run: `var_sr_across_trials` = 0.0276 and
   `sr0_benchmark` = 0.242 against a per-period Sharpe of 0.606** — it deflates away 40% of the
   Sharpe. The audit inferred near-identical trial SHARPES from near-identical median ICs; those
   are different quantities. What DOES stand: **`N = 8` against a ledger of ~146 real trials**, a
   denominator roughly 18x too small. Every run now ships `deflated_sharpe_detail` so this is a
   measured property per run, not an assumption either way. PBO likewise scores **only the
   weight-scheme selection step** — a selection the shipped strategy never makes, since it keeps
   `current-default` (now shipped as `pbo_scope`). **Lead with the long-short t against the
   Harvey-Liu-Zhu hurdle of 3.0.** That bar is real and it is cleared.
2. **`low_risk` was NOT "confirmed out-of-sample."** Verified in the code:
   `holdout_theme_validate` computes `rule_fired` at `fundamental_panel.py:3048` and **never
   reads it**; the verdict is `all(improves)` across both split directions. That is a demanding
   both-halves stability test and a legitimate one — it is not out-of-sample confirmation. The
   measured numbers are unchanged and still stand; the word was the overstatement. Fixing the
   function is audit **B8** and is NOT yet done.
3. **Every "800 largest names" result was an ALPHABETICAL slice** (`sorted(keys)[:limit]`), i.e.
   names beginning with roughly A through C. So "PBO 13% on 800 -> 53% on full" never measured
   what a large-cap tier does — it measured what an arbitrary subsample does. The function is
   fixed; **the affected figures are not citable until re-run**: the first CPCV "adopt", PBO 13%,
   Deflated Sharpe 77%, `f_score` t +5.66, `sm_breadth` t 2.37, the 13F look-ahead stress test,
   and the four classic-anomaly rejections.

**The biggest open question, and it is cheap: the headline has never been tested as alpha.**
`top_decile_alpha` is `4 x (top-decile 63d return - equal-weight universe 63d return)` and
nothing else — no beta adjustment, no factor model anywhere in the tree, and no t-statistic on
the headline metric at all. The composite is nearly FF5+MOM by construction. Pre-registered
thresholds and **both versions of the product claim** are written down in `HANDOFF_edge_audit.md`
Part 0, before the number exists. Until that regression runs, **the word "alpha" should not
appear in product copy.**

**A second live-product finding, not yet fixed (audit B7/G):** `screen.py:256` calls
`build_frame(metrics)` with no keyword arguments, so it inherits `CONFIG.sector_neutral`
(default **true**) and `CONFIG.residual_momentum` (default **true**), while the backtest forces
both `False`. Sector-neutral ranking was tested on the full universe and rejected in both
held-out directions, twice. **Unless `SCREENER_SECTOR_NEUTRAL=false` is set in the environment,
the hot list users see is scored under the intervention the research eliminated.**

**THE FULL-UNIVERSE RE-RUN — clean A/B against a pre-audit baseline on identical data.**
A throwaway worktree at `b67b07d` was re-run because the committed `BACKTEST_RESULTS.json`
stamped its own provenance as `commit 7eb0046, branch worktree-growth-valuation, dirty: true`.
(It reproduced to four decimals, so the stored file was fine — but that was not knowable in
advance, and it is only knowable at all because the results file records its git state.)

| metric | BASELINE | CORRECTED | delta |
|---|---|---|---|
| long-short t | 3.5202 | **3.8838** | +0.364 |
| top-decile alpha | +11.88% | **+11.78%** | -0.10pp |
| monotonicity | -0.9515 | **-0.9879** | better |
| equal-weight benchmark | +16.55% | +16.55% | 0 (the control) |
| PBO | 6.7% | **13.3%** | +6.7pp, still far under 50% |

**THIRTEEN CORRECTIONS AND NOT ONE HELD-OUT VERDICT CHANGED.** Every theme returns the same
verdict in both runs. The record's decisions were not resting on the defects, and the defects
were not hiding a different model — what moved is what the numbers MEAN.

**Two measured surprises, both reported against the audit's own expectations:**

- **A FULL BACKTEST IS NOT REPRODUCIBLE RUN TO RUN — unexplained, and it needs finding.**
  THREE full-universe runs on identical data gave `insider` median IC **-0.00335 (t -0.34)**,
  **+0.01551 (t +2.69)** and **-0.00339 (t -0.43)**, at unchanged 85.0% coverage. The first and
  third bracket the second and agree to four decimals, so the middle run is the anomaly — and
  **B26 is NOT the cause**, which an earlier draft of this file said it was. B26's effect was
  measured directly on 22,975 score pairs: 3.96% of scores move, correlation 0.9975, consistent
  with the ~0 IC change between the runs that bracket it. Every OTHER theme is stable to +/-0.01
  across all three. Two conclusions: `insider`'s IC sits so close to zero that its t is not a
  measurable quantity in either direction (which is why zeroing it came back `not_replicated`),
  and **a project whose memory is its results files needs those files to be deterministic.**
  Find the nondeterminism before trusting any marginal IC. Audit **S3** (the insider score's
  construction) is the thread that might make the theme measurable at all.
- **B10 recovered the WORSE signal.** The audit called it "one of the cheapest genuine signal
  recoveries available." Head to head: `accruals_q` as FCF/NI reads **t +1.26**; as the Sloan
  measure it reads **t +0.27**, at coverage 0.75 -> 0.97. The overwrite was a real defect — the
  column did not contain what its name said — but the thing it overwrote with was the better of
  the two. Both columns now exist (`accruals_fcf_ni`), so switching back is a one-line A/B that
  belongs in front of the held-out gate.

**B14 delivered its first number: `ended_early_unmasked` = 0 of 2,710 tickers**, 887 series
masked (32.7%) from a 19,207-name delisting map. No name's prices stop early without an ACTIONS
row — the first direct evidence the survivorship mask is not silently missing delistings.

**The new B18 sign check fired on its first run and caught my own incomplete fix:** `ev_ebitda`
still admitted negative EV (414 rows, 0.36%). It also found that the `ev_sales`/`ps` negatives
are NOT negative EV but negative **revenue** — 538 rows (0.273%), in agency mortgage REITs and
financial guarantors (DX, NLY, AGNC, MBI, RWT, FNMA). All three now take the same convention:
missing, not extreme.

**Corrected this session (13 items + 1 new finding), all with regression guards:**
B1 price basis in the options universe (and four MORE sites, including in roadmap 22c and deep
research thread #1 — **both of those need re-running**); B3 stale marks at expiry; B9 DSR/PBO
relabel; B10 the `accruals_q` overwrite; B12 the alphabetical universe; B14 delisting-mask
coverage now shipped with an `ended_early_unmasked` counter; B15 commission in `return_pct`;
B16 the dead exit module quarantined; B18 one convention for negative EV; B19 the Sharpe label;
B20 the `earnings_yield` numerator; B24 duplicate sanity evaluation; B26 same-day filings.
Plus **C7**: the CI gate now runs all 16 suites, not one of sixteen — it auto-merges to `main`
and Render auto-deploys, so this needed to land before any other edit.

**D10-a, a NEW defect not in the audit,** found by running `verify_sharadar.py` against the live
key: Sharadar **appends** a new ARQ row on restatement (3.15% of ticker-reportperiod groups,
1,818 of 2,827 tickers), and `_ttm` de-duplicated on **datekey**, which two filings of one
quarter never share. Blast radius is small — only `roe_ttm`/`roic_ttm`, already rejected — but it
is the fifth instance of "a guard that cannot see the failure it was written for."

**Also settled from the live Sharadar key before it lapses (D10/C5):** all 8 bundle tables are
reachable including SFP; SEP has **no `dividends` column** and `closeadj` is dividend-back-
adjusted, i.e. **total return** — which means audit item **R8**'s premise ("dividends are on
disk and unused") has to be re-checked before R8 is run; `TICKERS.category` has 15 real values
and the options-bot's universe filter knows 6, silently excluding 382 Canadian common-stock
rows; SF1 percentage fields are fractions, not percents.

**Not yet done, in the audit's own order:** session 2 (B2, B4, B5, B7, B11, B13, B17, B21-B23,
B25, begin B6), then X7/X2 (the noise floor), then **R1** (factor-adjusted alpha — do not start
Parts III-V until it returns), then R2/R3/R7 (the corrected options re-run). **P4 is urgent out
of band**: the forward track's `seed_book` never sells names that leave the book, so it only ever
adds — a track that silently drops losers is worse than no track.

---

## DEEP RESEARCH THREAD #2 — CROSS-SECTIONAL OPTION RETURNS: REJECT (2026-08-03)

Full report: **`HANDOFF_deep_xsection.md`**.

3,373 one-month ATM straddles, 242 names, 117 months (2016-02 to 2025-10), full mined universe,
both legs bought at the **ask**, held to expiry and settled at intrinsic. Coverage 82-100%.

**Zero adoptions. Zero BH-FDR discoveries at q = 0.10** (smallest p 0.291). PBO 41.4%.

- **`iv_rv` — Goyal-Saretto does NOT replicate**: monotonicity **+0.20**, i.e. no ordering in
  either direction, on the characteristic with the strongest published prior. Q1 excess t -0.69.
- **`idio_vol` CONTRADICTS Cao-Han**: a clean **+0.90** sort running the WRONG way — high-idio-vol
  straddles earned MORE (+0.110 vs +0.033). Reported as a contradiction of the literature, never
  re-signed into a result; the sign was declared before the panel existed. Caveat: the instrument
  is a straddle, not a delta-hedged call, so this may be the instrument and not the market.
- `idio_skew` (t +0.68) and `illiq` (t +1.06) have the right sign and no magnitude against
  MIN_T = 2.0. `illiq` is a mechanical control and can never be adopted; that it sorts at all
  (mono -0.70, the cleanest in the table) is the evidence the panel measures what it claims to.
- The long-short Q1-Q5 gates nothing — its short leg is a naked short straddle.
- **Not affected by audit B1**: this module uses `raw_close` for every option calculation.

---

## ENTERPRISE VALUE IS NOW PRICED AT THE REBALANCE DATE (2026-08-03), landed on `main` at 3f688d4 — **SHIPPED ON**

Full report: **`HANDOFF_ev_fix.md`**.

Sharadar's `ev` embeds the **filing-date** market cap, so `ebit_ev` / `ev_sales` / `ev_ebitda`
measured cheapness against a ~111-day-old quote while `earnings_yield` / `fcf_yield` /
`book_to_price` used the fresh one. `_pit_ev()` now re-prices the **equity leg** to the
point-in-time market cap and holds the **debt leg** at its last filed value (net debt is only
observable at a filing — that *is* the point-in-time answer). Net debt must be
currency-converted before it is added, which is P7 in a second costume.

Re-pricing moves EV a **median 5.1%** (mean 9.9%, p90 19.6%); **26.7% of rows move >10%**. The
direct evidence the staleness was real: `neg_ev_sales` median IC **+0.0214 → +0.0363 (+70%)**.

**The book is a wash, so it ships on correctness, not performance.** Long-short t 3.3957 →
**3.5202**, top-decile alpha +11.82% → **+11.88%**, PBO **6.67% unchanged**, monotonicity
unchanged, and net top-decile alpha slightly *worse*. The A/B is clean: the stale arm
reproduced the committed baseline exactly, and the panel diff showed exactly 9 changed columns
on identical keys.

The bias was **stale, not look-ahead** — the embedded price is always older than the
rebalance, never newer — so **no past result is invalidated upward**.

- New **`ev_freshness`** block in `BACKTEST_RESULTS.json` (schema v4): **100.0% fresh**, zero
  stale rows. It makes a silent revert loud. `EDGE_EV_POINT_IN_TIME=false` reverts.
- Fixing this also closed a latent bug in `results_file.build_payload`, which **silently drops
  any block it does not explicitly name** — the new guard would never have reached the JSON.
- Tests 22 → **34** in `tests/test_ev_multiples.py`, pinned by a test asserting EV tracks
  market cap across rebalances from a single filing.
- **One shipped number moved:** the Valquo Index paper-track book swaps **RF out, BP in** —
  one position of 86, **1.81% one-way weight turnover**. → **Tell Cowork.** The live web
  screener is unaffected (provider EVs are already current).
- **Deliberately NOT fixed:** negative EV (net cash > market cap, 909 → 950 rows, 0.70%) is
  read as *maximally cheap* by `neg_ev_sales` and as *expensive* by `ebit_ev` — a live sign
  inconsistency, pre-existing and unrelated to staleness. Bundling it would have confounded
  the before/after. One guard plus one held-out A/B.

---

## PEAD — REJECTION INDEPENDENTLY RE-VERIFIED, and the control that explains it (2026-08-03), landed on `main` at d86af01

Full report: **`HANDOFF_pead.md`**. The verdict below **supersedes nothing** — it confirms the
earlier PEAD section further down this file and adds the diagnostic that was missing.

PEAD was already built and rejected (`9323a08`, `2f75d60`); what was missing was the report.
So this session re-measured every claim on a fresh full-universe run built on the
**post-EV-fix** panel, rather than re-running a settled experiment.

**Replicates essentially exactly:** `pead_car` median IC **+0.01004, t +2.215, coverage
82.33%**; `pead_drift` **−0.00201, t −0.473, coverage 25.06%** (below the pre-committed 30%
floor). Orthogonality within rounding: `ret_6_1` +0.301, `high_prox` +0.239, `ret_12_1` +0.208.

**The control that settles it — correlation alone would have flattered this signal.** Momentum
explains only **R² 11.2%** of `pead_car`'s variance, so 89% of it is orthogonal — which reads
like a promising near-independent factor. It is not: residualized, its IC t is **+0.020**. And
the book movement it does produce is reproducible with **no earnings data at all** — counting
`ret_6_1` twice in the momentum mean gives **+0.83pp** alpha against `pead_car`'s **+0.52pp**,
beating it in the early half by more than 4x. Adding `pead_car` is an implicit **reweighting**
toward the strongest momentum input, not new information.

**One correction worth flagging:** my held-out deltas came out **positive** where `pead.py`
records negative ones. Chased down rather than resolved by preference — the deltas are
**construction-sensitive and flip sign** between the full composite and a restricted-universe
book (restricting to rows where the signal exists reproduces the original magnitudes and its
−1.06pp early-half alpha). **Every construction fails the pre-registered margins, so the
reject is robust** — but never quote a held-out delta for PEAD without naming the book.

`pead.py` runs on every panel row and had **zero test coverage**; added `tests/test_pead.py`
(**12 tests**), including a tampering test that multiplies every price *after* the CAR window
by 5 and asserts the signal does not move. A CAR is a forward-looking window by construction,
so an off-by-one there would manufacture edge from future returns while raising no error and
denting no coverage metric.

**All 16 suites green on merged `main`: 485 tests.** With this closed, the cheap signal ideas
are exhausted — the honest next steps are the **forward paper-track vs SPY** (Cowork's lane)
and the **ML tree combiner**, not another factor.

---

## DEEP RESEARCH THREAD #1 — EXIT OPTIMIZATION — **REJECT, AND A SIMULATOR BUG FOUND** (2026-08-03)

Full report: **`HANDOFF_deep_exits.md`**. Gate committed results-free at `56268b6` before scoring.
Full run: **278 complete names**, 3,119 signal entries + 5,986 random entries, 21 exit policies,
aggression 1.0. Catalog updated in `OPTIONS_DEEP_RESEARCH.md`; next thread is **#2 cross-sectional
option returns**.

**READ THIS BEFORE ANY THREAD THAT HOLDS POSITIONS LONGER (VRP, earnings, calendars).** The
production simulator marks a position that outlives its contract's last usable quote at **that
stale quote** — and a contract stops being quotable exactly when it is dying. For the
hold-to-expiry policy **44.6%** of trades land in that fall-through, their last quote is a **median
of 10 days before expiry**, it is **higher than true settlement in 94.7%** of cases, and **86.1%**
carry a positive mark on a contract that expired worthless (mean marked −77.8% vs a true −92.2%).
The bias **scales with holding period**, so it manufactures a monotone fake reward for holding
longer — worth **+6.45pp** on that policy. **The shipped exit hits it on 0.9% of trades, so 22b,
22c and every earlier options result are essentially unaffected**, and all of them use the same
exit so their comparisons are unaffected too. Honest settlement (`settle="intrinsic"`) is now the
default in `options_exitlab.apply_policy` and is pinned by a test.

**Verdict REJECT — nothing clears the +10pp bar.** But the direction is real, small and consistent,
and it **replicates on RANDOM entries** with equal or larger size, so whatever effect exists is a
property of the **EXIT**, not of the dead entry signal — which is exactly what the mandate asked:
- **cutting winners early is costly**: +50% target −3.61pp, +75% −1.19pp, **+150% +2.11pp, +200%
  +3.26pp**;
- **stopping out tight is costly**: −30% stop −2.61pp, −70% +3.13pp, no stop +3.20pp; trailing stops
  are the worst family (25% trail −4.06pp);
- so the optimum target sits nearer **+150–200%** than the shipped +100%, and the −50% stop is on
  the costly side. `tp200` is the only policy better on **every** axis — per trade, per day held,
  both entry sets, both halves, majority of the cells it changes (FDR 10%), DSR 99.8%.

**Do NOT be fooled by `tp100_only`**, the grid's biggest per-trade number (+6.71pp): per DAY of
capital committed it is *worse* than the shipped exit on both entry sets (+0.00250 vs +0.00256),
it simply holds **2.5x longer**, its paired direction **flips sign between entry sets**, and it
carries **21.5% total losses vs 0.67%**.

**The barbell, measured in two numbers:** tightening the stop (sl30) **wins a majority of cells
(z +10.6) and loses 2.61pp of expectancy**; holding to expiry **earns +6.71pp and loses a majority
of cells (z −3.97)**. Mean improvement and win-rate point in opposite directions — the same lesson
the autopsy taught about hit rate.

PBO by CSCV over the policy grid: **0.075 signal / 0.000 random** over 252 splits — not overfit,
there is just not much in it. Tests **166/166** edge (10 new).

**Two questions left open, deliberately not renegotiated:** whether an ABSOLUTE +10pp bar is right
for a proportional improvement (tp200 is a ~69% relative lift on a +4.71% book), and whether
requiring both a mean gain and a cell-win majority is self-defeating on a convex payoff.

---

## OPTIONS ENTRY TIMING (roadmap 22c) — **THE ANTI-TILT IS REAL AND STABLE, AND NOT SALVAGEABLE** (2026-08-03)

Full report: **`HANDOFF_entry_fix.md`**. Gate committed results-free at `52a4658` before the run.

22b found the scream-buy alert picks worse-than-random entry days. 22c asks why, and whether a
corrected entry beats BOTH the signal and the random-entry control. Full run, 187 names,
aggression 1.0, 2016-01-01..2025-10-15. The signal arm reproduces the 22b book **trade for
trade** (3,042 trades, zero P&L differences).

**The finding replicates and is STABLE — it is a property of the signal, not of a period.**
Signal +5.14% vs control +11.07% (5,919 control trades); paired −3.72pp over 1,080 name-year
cells, sign z = −3.48. Negative in **both** halves (−5.88pp early z −2.20, −5.96pp late z −2.69)
and significant in the two tiers that carry the book (mega −5.03pp z −2.61, large −7.37pp z −2.26).

**The hypothesis was WRONG, with the sign reversed.** The mandate expected the alert to chase
pumped IV. It does not — alert days carry **CHEAPER** vol than a random day in the same name-year:
~60-DTE ATM IV 0.2428 vs 0.2577 (paired z −11.13, only 32.9% of cells higher), IV rank 0.345 vs
0.425 (z −9.89), IV pop 0.968 vs 0.991 (z −6.56). **Zero of four IV proxies confirm.** What alert
days do carry is EXTENSION: the median alert buys **0.24% below the 52-week high** after a +4.1%
five-day run, against −4.68% and +0.78% for a random day (z +29.45 and +27.92). Sustained advances
compress vol, so the alert buys strength cheaply and still does worse. **E2 verdict: PARTIAL.**

**All FIFTEEN corrections fail** (9 simulated arms + 6 same-day context gates, all counted in the
deflation, DSR at n_trials = 14):
- **Delaying makes it monotonically WORSE**: +6.36% / +4.36% / +3.59% at 3 / 5 / 10 sessions. Not
  a timing offset.
- **Fading loses outright**: buying the put instead returns **−10.54%/trade**, PF 0.743, negative
  in both halves. The anti-tilt does not invert.
- **`pullback` is the sharpest picture and still fails.** On the 867 alerts followed by a 3% dip
  the signal returns **−43.59%/trade** and buying the dip returns +3.19% — paired +46.07pp, z
  +11.64, p = 2.5e-31, the only BH-FDR discovery. It still loses to the control by 8.45pp, is
  negative early, and loses to a same-sized random drop (+2.62% vs +4.99%).
- **Context gates 0 of 6.** "Skip the most-extended alerts" (ret_21d) clears FOUR of the §2 gate's
  five arms — late gain +5.93pp, retention 44.7%, beats its random filter — and fails the fifth
  (early-half gain −0.83pp). Rejected on the pre-committed bar, not renegotiated.

**Why nothing works: the underperformance is UNIFORM.** The alert loses to its control in every
quartile of run-up (−7.5/−2.3/−10.8/−3.1pp) and every quartile of IV pop (−11.7/−0.9/−3.4/−7.9pp).
Within the alert book neither run-up nor the alert score itself orders the outcome — a HIGHER
scream-buy score does not mean a better trade (+2.33/+8.55/+4.11/+4.34% by score quartile). There
is no slice to condition on. Nor does any label: all nine label families with a real sample sit in
a +4.3% to +6.8% band around the book's +5.14%, and the OPTIONS-FLOW labels do not separate from
the TECHNICAL ones — which answers 22b's open question about which half of the score does the
damage: **neither, distinguishably.**

**Held-out arm selection, both directions:** the best arm beats the signal by +40 to +50pp on the
half that did NOT choose it — and still cannot beat buying on a random day.

**THE CAVEAT THAT MUST TRAVEL WITH THIS.** The control is a yardstick, not a tradable strategy: it
only trades name-years the alert selected, and it is buying weakness inside years that by
construction contained a strong advance. The correct statement is "within the years the alert
selects, the alert picks a below-average day." Whether the book beats SPY is **still unanswered**
— every options comparison in this project is internal. **That is the forward paper track, and it
is Cowork's lane.**

**Do not re-open:** delayed entries, IV-normalisation waits, IV-cheap gating, extension gating,
fading the alert. All measured, all in `data/options_entry/ENTRY_RESULTS.json`.

Tests **156/156** edge (14 new).

---

## OPTIONS ON THE EXPANDED UNIVERSE (roadmap 22b) — **THE EDGE HALVES, AND THE SIGNAL FAILS ITS FIRST PLACEBO** (2026-08-03), landed on `main` at 1a2f95f

Full report: **`HANDOFF_universe_backtest.md`**.

The single-leg scream-buy backtest was re-run across the whole cached universe — **187
complete names, 3,042 trades**, NBBO at aggression 1.0, 2016-01-01..2025-10-15, nothing
re-tuned. The gate was committed in the module docstring before the run.

**The edge survives breadth but roughly halves: +12.33%/trade on 55 megacaps -> +5.14% on
187.** Both held-out halves positive so it passes, but Deflated Sharpe falls **98.62% ->
88.13% unfiltered**, below the 95% bar (95.69% on the term_slope-filtered book, only just
clearing). Mid/small caps are the BEST tier (+9.80%), not the worst; the home-run thesis is
NOT upheld (P(>=+100%) +1.86pp, CI spans zero).

**A control this project had never run on the options book changes what all of that means.**
Same name, same calendar year, RANDOM entry day, identical contract/fill/exit rules:
**+13.22% against the alert book's +5.14%.** The alert book loses in every cap tier, in 9 of
10 years, and in **58% of 1,052 name-year cells (sign-test z = -5.24, two independent seeds)**.
Contract characteristics are near-identical (DTE 58 vs 58, delta 0.355 vs 0.351), so this is
day-selection, not what gets bought. The scream-buy alert picked WORSE days than chance. The
book is profitable; the signal is not what makes it profitable. **Do not ship an options
alert change, and stop quoting +12.33%/trade, until this is settled.**

**The old-vs-new gap is 100% spread, not signal.** A full second pass at mid fills on the same
pinned names: the two cohorts are +11.99% and +11.56% at the mid, versus +6.95% and +3.90% at
the touch. Crossing the spread costs **6.59pp — more than half the surviving edge**. Mid/small
pay roughly double the megacap toll (-9.4pp / -11.0pp vs -5.4pp) but start from a gross edge
high enough to finish ahead net. Don's "spreads eat it" thesis is half-right and now measured.

**Universe selection is not neutral and the bias runs TOWARD the edge:** the miner skipped 55
of 245 names as thin, and today's-liquidity selection makes the `small` tier future winners in
their small days (median **14.8x** cap growth to today). Splitting each tier by that hindsight
growth puts the ENTIRE mega/large edge in the names that later grew, with the other half flat
to negative. That split is partly circular and can never be a filter — but combined with the
control it means **this cache cannot separate the strategy from its universe's upward
selection.** Only a forward track can.

**term_slope:** the economic effect DOES generalise out of sample — **+8.89pp** on 133 names
that never informed its threshold, against the +8.12pp that got it adopted, and it is mildly
tail-ENRICHING (keeps 41.2% of >=+100% winners while keeping 37.3% of trades). **But B2 FAILS
on retention** (36.4% vs the pre-committed 40% floor, which the 55-name run cleared at only
40.6%). Reported as FAIL: a pre-committed gate is not renegotiated after the run.

**The #23 autopsy headline re-confirms on the wider set** — the gate was re-run *unchanged*
(`options_autopsy.run()` gained a `trades` override so the two stay comparable): 64 features,
127 hypotheses, **zero survivors, zero FDR discoveries, PBO 35.7%**, combiner rejects. Mid/small
caps surface nothing that separates winners from losers.

Sanity clean, zero flags. `data/options/` read-only throughout. Suites: `test_edge.py`
**142/142** (9 new) and all 14 other suites green. Recommended next: decompose the control
finding (is it the technical run-up requirement or the options-flow score?), then the forward
paper track -> **Cowork's lane**.

---

## LAZY PRICES (roadmap #28) — TESTED AND **REJECTED** (2026-08-03), landed on `main`

Full report: **`HANDOFF_lazy_prices_ic.md`**. Dataset build: `HANDOFF_lazy_prices.md`.

The 10-K/10-Q language-change signal was built (195 filers, 7,095 scored pairs, free SEC
EDGAR, 0 fetch failures) and then put through the gate. It does nothing: rank-IC **-0.0156**,
t(NW) **-1.07**, long-short **-5.0%/yr**, top-decile alpha **-2.9%/yr**, and the deciles run
BACKWARDS (monotonicity +0.709, where -1.0 is ideal). Both time halves negative. Across 28
measure x horizon cells nothing clears the bar in the pre-registered direction, and the one
cell that looked good (`jaccard@252`, IC t +3.88 early) collapses to +0.24 on the later half.
It is genuinely orthogonal to every existing theme (|r| < 0.07) and genuinely uninformative —
residual IC after regressing the themes out is -0.001 (t -0.06). **Nothing wired in; roadmap
#28 closes.** Do not spend the ~1hr/250-names fetch on extending it — see §8 of the report.

One finding was left deliberately unexploited and is written up in §5: the MD&A-section
measure has a *significant* spread in the WRONG direction (biggest rewriters +8.6pp), stable
in both halves, not explained by the growth or momentum themes. It was NOT flipped into a
signal — the direction was pre-registered before returns were joined, so reading it backwards
is a new hypothesis, not a rescue of this one.

Suites on the merged tree: `test_edge.py` 123/123, `test_lazy_prices.py` 28/28,
`test_lazy_prices_ic.py` 24/24. Research code lives in `valuation/research/` and a test
asserts no production module imports it.

---

## Data mining (ThetaData cache expansion)

Running in its own session; status and design notes are in **`HANDOFF_miner.md`**, not here.

## ITEM 0 SHIPPED + A2 COMPLETE (2026-08-02)

**Item 0 - `git_push.bat` is now genuinely one command, and it is VERIFIED.**
Real `git merge --no-edit` for any `worktree-*` branch ahead of main (divergence stops
mattering), conflict -> abort + report + BLOCK the push, tests run and a red suite refuses the
push, auto-land skipped unless HEAD is main.

Verified, not eyeballed - it broke twice more during this work, exactly as the prompt warned:
LF-only line endings (a .bat with LF does not execute on Windows) and `2^^>nul` double-caret
inside the for-loop. Last session's failure was the HARNESS, not the script: the script does
`cd /d "%~dp0"` itself, so invoking it by FULL PATH lands it in the scratch repo regardless of
the caller's cwd. All three scenarios now pass:

    diverged branch merges + pushes    PASS  (main 2 -> 5 commits, remote updated)
    red tests block the push           PASS
    conflict aborts, nothing pushed    PASS  (dirty=0, no MERGE_HEAD)

The harness ships as `verify_git_push.ps1` so this stays re-testable. **`.\git_push.bat` will
now land the outstanding options commits by itself.**

**A2 - iv_rank made testable, then REJECTED on merit.**
Built a daily ATM-IV series across ALL trading days from the cached chains: **137,418
observations, 55 names, median 2,514 each**. iv_rank coverage went **0.0% -> 99.0%**. Through the
same pre-committed gate it fails every arm: late gain -0.93pp (bar +5pp), worse than the random
control (+3.83% vs +4.84%), early gain -1.25pp, retention 39.9% (bar 40%). By year it is
erratic - helps 2024/2025, destroys 2021 (-19.45%) and 2023 (-22.25%). Buying when vol is
already rich for the name is not a durable long-premium filter.

Series cached at `data/options/atm_iv_series.pkl`, reusable for any vol-regime read.

**A2 - tick flow INFEASIBLE at this scale, measured.** `option_history_trade` = 6,259 rows in
5.0s for ONE expiry-day; across 55 names x 2,500 days x 8 expiries that is **1,537-1,957 HOURS**.
`option_history_trade_quote` pairs trades with the prevailing quote (exactly what aggressor-side
needs), so the signal is constructible but not affordable historically. **Feasible alternative:
alert days only, ~1,841 x 6.4s ~ 3.3 hours** - the sensible way to test it if wanted.

**Standing after A2:** the only adopted new signal remains `term_slope` (phase 3b, +8.12pp late).
skew / VRP / GEX / iv_rank all rejected on evidence; tick flow untested by cost.

**A3-A5 NOT STARTED** (VRP credit-spread arm + correlation; options-bot fold-in; live book with
per-alert confidence + sizing).

## A2-A5 SESSION - item 0 attempted and NOT LANDED (2026-08-02)

**Nothing shipped this session. `git_push.bat` is UNCHANGED and still the known-good version.**

I wrote the upgrade (real `merge --no-edit` instead of FF-only so a diverged main stops
mattering; abort + report on a genuine conflict; run tests and refuse to push when red) but
**could not verify it**, and the prompt was explicit: "this script has broken twice on batch
escaping; test it, don't eyeball it." The scratch-repo harness never managed to get cmd.exe to
actually invoke the script - every scenario produced zero output - so not one of the three
behaviours was ever exercised.

The attempt DID find one real bug, which is exactly the argument for not shipping unverified:
the file had been written with **LF-only line endings**, and a .bat with LF endings does not
execute on Windows. Trusting the code review instead of the test would have silently broken
Don's ONE deploy command.

So the upgrade is parked as **`git_push_v2_UNVERIFIED.bat`** with a banner listing what to test,
and `git_push.bat` was restored via `git checkout --`. Replacing a working deploy script with an
unverified one risks leaving the repo mid-merge - worse than the manual merge it was meant to
remove.

**To finish item 0:** copy v2 into a throwaway repo containing a diverged `worktree-*` branch and
confirm (a) the branch merges, (b) red tests block the push, (c) a conflicting branch aborts
cleanly leaving no MERGE_HEAD. A three-scenario harness exists at `C:/Users/donni/.claude/jobs/7819c8eb/tmp/verify_push.ps1` - its `RunScript`
function is the part that does not work.

**A2-A5 NOT STARTED.** Item 0 was ordered first and consumed the session.

**MERGE STILL OUTSTANDING** - phases 1-3b and phase 4 A1 are on `worktree-p24-shortinterest`,
not on main. Verified conflict-free (zero overlapping files):

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 89/89)
    .\git_push.bat

## PHASE 4 - test fix + A1 term-structure filter WIRED LIVE (2026-08-02)

**Close-out item done first, as instructed: the env-sensitive test is fixed.**
`test_thetadata_provider_is_optional_and_dedupes` asserted a keyless provider returns an empty
chain - but `chain_on` consults its DISK CACHE before checking availability, so on any machine
with a real `data/bulk/prepared/theta/AAPL/2023-03-01.pkl` the keyless provider returned live
cached data and the assertion failed. It also read THETADATA_API_KEY from the environment/.env.
That is exactly why it was 88/88 here and 87/88 on Don's machine. Now pinned to an empty temp
cache dir with an explicit `api_key=""`. **Verified 88/88 with the key set AND unset.**

**A1 DONE - `term_slope` wired as a standing, reversible live filter.**
Chain: TradierProvider now also fetches a ~60-DTE expiry's ATM IV (term_slope needs both legs)
-> `options_signals` carries `atm_iv_60d` -> `screaming_buys` annotates via
`intraday/term_filter.py`. Config flag `OPTIONS_TERM_FILTER` = flag | suppress | off.

Three deliberate design choices:
- **Default is FLAG, not suppress.** The filter removes ~60% of alerts; that is too large a
  product change to inherit silently from a backtest. Every alert still appears carrying
  `term_ok` + a reason, so the UI can show backwardation ones as reduced confidence.
  `OPTIONS_TERM_FILTER=suppress` is one env var away.
- **Fails OPEN.** Missing/malformed IV -> `term_ok=None` (unknown), never False. A quote-feed
  hiccup must not masquerade as backwardation and silently halt alerting.
- **Sizing compensates.** Contango alerts get a 1.5x multiplier, backwardation 0.5x, unknown
  1.0x - so filtering 60% of signals does not quietly shrink sleeve exposure by 60%. Capped,
  because "trade less often but much bigger" is how a modest edge becomes a concentrated bet.

Tests 89/89 (one added pinning fail-open, flag-by-default, and reversibility).

**NOT DONE - the bulk of phase 4.** A2 (daily ATM-IV series to make iv_rank testable; tick
flow), A3 (VRP/credit-spread arm + correlation with the long arm), A4 (options-bot fold-in),
A5 (tracked book + per-alert confidence + suggested sizing), and ALL of PART B (live-app
backlog: data integrity, 861-name universe, remove Sharadar from the live path, dynamic net
alpha, trust/reliability) and PART C (growth/pre-profit valuation, RKLB $2.63 vs $65).

**§0 STILL BLOCKED and phase 4 assumed it was done.** Phases 1-3b are NOT on `main`. Dry-run
merge confirms NO conflicts, ZERO overlapping files:

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 89/89)
    .\git_push.bat

## OPTIONS PHASE 3b §2 - term structure ADOPTED, arrests most of the fade (2026-08-02)

Five ThetaData-derived signals tested, each fitted on 2016-2020 and judged ONLY on 2021-2025
(where the edge fades). **One adopted, three rejected, one not testable.**

    term_slope  kept 40.6%  late +4.76% -> +12.88%   +8.12pp   ADOPT
    skew_25d    kept 44.0%  late +5.33% ->  +6.43%   +1.10pp   reject
    vrp         kept 56.1%  late +4.76% ->  +5.30%   +0.54pp   reject
    gex_proxy   kept 50.2%  late +4.65% ->  +4.00%   -0.65pp   reject
    iv_rank                        NOT TESTABLE (see below)

**TERM STRUCTURE (contango: ~60-DTE IV above front IV) nearly triples late-half expectancy** and
is economically coherent - backwardation prices near-term stress or a pending event, a bad moment
to buy a 45-75 day call. On the losing years: **2022 -11.41% -> +19.78%, 2023 -4.61% -> +7.30%,
but 2025 -0.05% -> -5.90%.** Two of three repaired, one worsened; across ten years it helps six
and hurts four. A real filter, not a universal one.

Robust to its only parameter: over a 3x threshold range the gain stays +7.7 to +9.0pp. But it
DISCARDS ~60% of alerts (retention 40.6% against a 40% floor), so the book gets materially
smaller - that belongs in any sizing decision.

**Bug worth knowing:** 288 skew values were NaN (not None), so they passed the not-None filter,
the median came back NaN, and every comparison was False - the filter kept ZERO trades while
coverage reported 100%. Fixed; skew then tested fairly and rejected on merit.

**iv_rank is NOT TESTABLE as built, not rejected.** It needs 60 prior ATM-IV observations per
name, but IV history came only from that name's alerts (~28 avg), so coverage was 0%. Needs a
daily ATM-IV series per name across all trading days - straightforward, but a fresh compute pass.
Tick flow also remains untested (needs the tick feed, not cached).

**§0 STILL BLOCKED - BUT VERIFIED SAFE.** A dry-run merge shows NO conflicts and ZERO overlapping
files (main adds 166 under options-bot/ + prompts; this branch changes 23 under valuation/,
tests/, docs). My harness forbids merging/pushing to main, so this needs one manual step:

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 88/88)
    .\git_push.bat

**NOT DONE:** §4 VRP/credit-spread arm + correlation with the long arm; §5 options-bot fold-in
(also blocked - that code is on main, not in this worktree); §6 live engine, tracked book,
per-alert confidence + suggested sizing. Roadmap 22b (small/mid-cap) is the next iteration and
needs a fresh ThetaData pull.

## OPTIONS PHASE 3 - sizing adopted, DTE rejected, §0 BLOCKED (2026-08-02)

**§0 IS BLOCKED AND NEEDS DON.** `main` has DIVERGED from the options branch: main took in the
whole `options-bot` tree (164 files, ~27k lines) plus the PROMPT files in two automated "Update"
commits, while 28 phase-1/2/3 commits sit on `worktree-p24-shortinterest`. Because it is no
longer a fast-forward, **`git_push.bat` will SKIP it** ("not a clean fast-forward, merge by
hand"). The changes do not overlap - main added `options-bot/`, the branch touched `valuation/`,
`tests/` and the docs - so the merge should be clean. My harness forbids merging or pushing to
main, so this needs one manual step:

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 88/88)
    .\git_push.bat

**§1 FIXED-DOLLAR SIZING ADOPTED - and a phase-2 number is CORRECTED.** Phase 2 said fixed-dollar
sizing cuts the top-15 share to 42.0%; that deployed exactly $1,000 per trade, i.e. FRACTIONAL
contracts, which do not exist. With whole contracts:

    1 contract each (phase 1)          top-15 98.1%   ex-top-15  $2,767
    idealised fractional (phase 2)            42.0%              $92,998
    whole contracts, min 1                    62.9%              $83,986
    whole contracts, skip too-costly          50.3%              $54,853  (drops 13% of signals)

200 of 1,540 signals cost more than a $1,000 budget for one contract, so they can only be
skipped or taken oversized. **The conclusion survives - 98.1% -> ~45-63%, ex-tail $2,767 ->
$55k-$93k - but 42% is not reachable in any tradeable form.** Larger budgets are better on every
axis ($5,000: 98.4% of signals, +10.16%, 44.5% concentration). Percentage expectancy is identical
across sizing schemes (+10.42%), which is the check the re-weighting is correct.

**§3 65-75 DTE REJECTED.** +11.55pp on the first half, **+1.19pp on the second** against a
required +5pp. It inherits the very fade it was meant to arrest. Phase 2's +17.0% vs +7.8% was a
full-sample figure dominated by the early period. Live band stays 45-75. 35-delta remains
confirmed optimal and untouched.

**NOT DONE:** §2 (new ThetaData signals judged on the 2021-2025 fade - the core remaining
research), §4 (VRP/credit-spread arm + correlation with the long arm), §5 (options-bot fold-in -
also blocked, the code is on main and not in this worktree), §6 (live engine + tracked book +
annualized net-of-cost/after-tax returns). Roadmap 22b (small/mid-cap expansion) is explicitly
the iteration after this and needs a fresh ThetaData pull.

## OPTIONS PHASE 2 - tail analysis + spread comparison (2026-08-02)

**The phase-1 "too tail-dependent to size" verdict is CORRECTED.** The dollar concentration was
a position-sizing artefact: entry premiums span 1,076x, so 1 contract of a pre-split $3,000 AMZN
next to 1 of a $40 bank guarantees a few names dominate. At fixed $1,000 risk per trade the
top-15 share falls 98.1% -> 42.0% (idealised; 44-63% with whole contracts - see phase 3), profit ex-top-15 goes $2,767 -> $92,998, top-3 name
concentration 76% -> 34%, and total profit RISES to $160,461. **Size by fixed dollar risk, not
contract count.** Excluding the top 15 winners entirely, expectancy is still +8.96%/trade, and
30.7% of all trades returned >= +100% - big winners are common, not rare.

**No conviction tier ships.** A fingerprint fit on half 1 scored a 28.07% big-win rate on the
held-out half vs a 29.05% base and 29.04% random control (lift 0.966 vs a required 2.0). Worse
than random; fails every arm of the gate. The tail is unpredictable - 9 of the top 15 were 2020
AMZN/GOOGL/TSLA. Building a louder "scream-buy+" alert would have been false emphasis.

**Section 4 REJECTED:** matched vertical debit spread scores -4.46%/trade vs single-leg +12.33%
on 1,313 matched pairs, worse in every IV regime and both halves, and no better hit rate. The
+100% target is measured on the debit but a debit spread's max value is the strike width, so
targets sit at the ceiling while the -50% stop fires normally.

**STILL NOT DONE (mandate sections 3-6 of phase 2):** the new ThetaData signals (IV rank, VRP,
term structure, skew, tick flow, GEX); the VRP/credit-spread arm; the options-bot fold-in
(OPTIONS_BOT_INTEGRATION.md); and the live-engine + tracked-book wiring with annualized
net-of-cost and after-tax returns. Nothing in the live product has been changed.

## OPTIONS TRACK - scream-buy validated on real ThetaData (2026-08-02)

Full detail in `OPTIONS_BACKTEST_RESULTS.md`. 55 names, 2016-2025, **1,540 closed trades**, all
net of spread + commission at the punishing fill (buy ask / sell bid).

    hit rate 37.4%   avg win +120.4%   avg loss -55.3%   PF 1.30
    EXPECTANCY +10.4%/trade   cum $143,723 (1 contract/trade)
    held-out split: +16.4% (2016-2020) vs +4.4% (2021-2025) - positive in BOTH, bar met
    positive in 7/10 years; 2022, 2023, 2025 negative
    37 of 55 names positive

**THE DECISIVE CAVEAT: dollar P&L is tail-driven. Drop the best 1% of trades (15 of 1,540) and
$143,723 becomes $2,767; drop 5% and it is -$151,760.** Percentage expectancy is far more robust
(+10.4% -> +9.0% dropping the top 1%), because the book buys ONE CONTRACT per signal so
expensive contracts dominate dollars. **Sizing by fixed dollar risk instead of fixed contract
count is the obvious next test.**

Verdict: positive expectancy, survives costs, clears the pre-committed bar - but thin, fading,
and too tail-dependent to size aggressively. NOT "the scream-buy engine works". Nothing in the
live product was changed on the basis of it.

Useful sub-findings: realised stop loss is -59.1% not -50% (daily-mark trigger, worse fill);
the live 35-delta pick is the best of three delta buckets; 65-75 DTE more than doubles 45-55
(+17.0% vs +7.8%) and is a testable refinement, not yet gated.

**Infrastructure now in place** (all committed, tests 88/88):
- `theta_bulk.py` - year-chunked bulk loader, 4 concurrent, quarterly chunks with
  retry/backoff/timeout, resumable atomic cache in `data/options/`. Per name the pull went from
  280-640 calls to ~22; a full year of compute went from "did not finish in 500s" to 0.6s.
- `options_fill.py` - fill/cost engine. Honest fill is the DEFAULT (mid-fills are a diagnostic
  only), bad quotes rejected with named reasons, expired-worthless posts -100%.
- `blackscholes.py` - local greeks, validated against the vendor (delta 98.96%, IV 100% in the
  tradable band).
- `options_backtest.py` - reconstruction that CALLS the live alert + live scorecard functions,
  so backtest and forward tracker cannot diverge.
- `optbt_status.py` - progress + partial verdict at any time; `optbt_run.py` - the runner.

**Four silent bugs found and fixed** (each would have produced a confident wrong answer):
split-adjusted prices meeting unadjusted strikes; a failed FRED fetch retried every call (60s);
11 of 30 year-pulls failing with no retry and no record; and ticker renames (META/FB) silently
dropping six years.

**NOT DONE - mandate sections 4-6:** single-leg vs vertical spread (arm is built and committed,
not run), the new ThetaData signals (IV rank, VRP, term structure, skew, tick flow, GEX), and
the live-engine / tracked-options-book updates. Premium selling (CSP/covered calls) remains
deferred by the mandate as a separate short-vol track.

## P24.3 / P24.4 - USAspending REJECTED, congressional trades INCONCLUSIVE (2026-08-01)

This closes the alt-data question opened in P24: four external sources tested, four gates
pre-committed to git before any number came back, nothing adopted.

### USAspending federal contract awards - REJECTED

    signal                     median IC    IC t   dates   avg names   coverage
    govt_award_momentum          +0.0044   +0.70      62          89      4.03%
    govt_award_level (PLACEBO)   +0.0007   -0.52      62          96      4.34%
    -- POWER CONTROLS on the same restricted subset --
    inst_accum                   +0.0412   +2.27      50          90
    quality                      +0.0290   +1.61      62          88
    ret_6_1                      +0.0114   +0.78      62          88

**The power control earned its keep.** The FIRST run mapped only 89 tickers and produced a
70-ticker subset on which ret_6_1 fell from t +3.40 (full panel) to +0.83, with no control
clearing 2.0. By the pre-committed rule that was INCONCLUSIVE, and it was not written up as a
rejection. Going deeper into the recipient list (top 2,000 -> top 6,000) lifted the mapping to
137 tickers and the subset to 102, at which point inst_accum reached +2.27 and the null became
interpretable. Without that rule the thin first run would have been reported as "federal award
momentum does not work" on evidence that could not support the claim.

Limits that survive the verdict: coverage is 4%, so even a real signal there could not move a
broad book (it would have been a gov-exposure sleeve, not a composite change); and the
subsidiary problem is unsolved - no parent-rollup endpoint exists (parent_recipient /
recipient_parent / parent_duns all 404), so Electric Boat is still not credited to General
Dynamics. That adds noise, which biases toward rejection, so it does not undermine this null.

### Congressional trades - INCONCLUSIVE, explicitly NOT a rejection

    signal                     median IC    IC t   dates   avg names   coverage
    congress_net_buy             +0.0020   +0.97      49         314     11.27%
    congress_activity (PLACEBO)  -0.0040   +0.02      49         314     11.27%
    -- POWER CONTROLS on the same restricted subset --
    ret_6_1                      +0.0484   +1.87      49         313
    inst_accum                   +0.0230   +1.80      49         313

The signal shows nothing (t +0.97, and it would have to more than double to clear the bar), but
the subset cannot certify a null - the best known-real control reaches only +1.87 against a
pre-committed 2.0. So no verdict is claimed.

**The limit is TIME, not cross-section**, which says what would fix it. Coverage is healthy
(1,157 tickers, ~314 names/date - wider than the USAspending test that DID reach power). The
binding constraint is that the data starts 2014, giving 49 rebalance dates over a decade in
which momentum itself was weak. More tickers cannot fix that; only more years, which do not
exist.

**Point-in-time, now quantified rather than asserted.** Of 47,455 transactions, 21.9% were filed
late; days from trade to filing have a median of 29, a 90th PERCENTILE OF 210, and a max of
4,049. Using transaction_date injects up to SEVEN MONTHS of look-ahead for a tenth of the
sample, precisely during the window a member's presumed advantage would play out. The loader
DISCARDS the transaction date entirely rather than merely declining to filter on it, so it
cannot be reached later. Pinned by `test_congress_never_stores_transaction_date`.

**Second finding worth keeping:** the originally intended source (House/Senate Stock Watcher) is
defunct - S3 403, site dead - and its surviving GitHub mirror is Senate-only, stops in 2019, and
carries `transaction_date` as its ONLY date field. A test built on the first free dataset to hand
could not have been correct, and no field would have warned anyone. Source used instead:
kadoa-org/congress-trading-monitor, built from the official House Clerk and Senate eFD feeds,
which carries filing_date separately. The GATE (thresholds, orientation, placebo, power control)
was unchanged by the source switch.

### Where the alt-data question now stands

    source                  verdict        why
    FINRA short interest    REJECTED       t +1.04 vs 2.0; controls on the same window +3.53
    SEC EDGAR 13D/13G       REJECTED       activist t -0.69; passive placebo beat it by 2.35
    USAspending awards      REJECTED       t +0.70; subset had power (inst_accum +2.27)
    Congressional trades    INCONCLUSIVE   t +0.97 but no control cleared 2.0 on 49 dates

Nothing adopted. Three clean rejections and one honest inconclusive. Combined with the P6/P10
rejections, the standing conclusion is unchanged and now better supported: **the signal set is
saturated for this dataset, and free public alt-data did not add to it.** All eight signals stay
MEASURED (per-signal IC table) and score in no theme, so re-testing any of them is one line in
factors.py.

Tests 81/81.

### Recommended next step

The internal-research avenue is exhausted for now. The top priority remains what it was before
P24: **a forward paper-track vs SPY** - the edge has still only ever seen this one 18-year
Sharadar panel, and a live track on data nobody has looked at is the only remaining honest test.
That is Cowork's lane ("Valquo Index vs SPY").

## P24.2 - SEC EDGAR 13D/13G: TESTED AND REJECTED (2026-08-01)

352,332 filings -> 6,632 tickers from EDGAR quarterly form indexes (112s for 2007-2026).

    signal                  median IC    IC t   nonzero   coverage
    activist_13d              -0.0055   -0.69     4.56%      58.5%
    passive_13g (PLACEBO)     +0.0159   +1.66    18.59%      58.5%
    inst_accum (in the book)  +0.0314   +1.88        --      61.4%

    gate: standalone t >= 2.0              FAIL (-0.69)
          13D beats 13G placebo by >= 1.0  FAIL (-2.35)

**The activist signal came out NEGATIVE** - opposite to the direction fixed in advance - and the
PASSIVE placebo (the box index funds tick mechanically) outscored it by 2.35 t. Measuring 13D
alone would have given a bland "weak, rejected"; the pre-committed placebo gives a sharper
verdict: whatever these filings carry at a quarterly horizon, it is not activism creating value.
It also forecloses chasing passive_13g's +1.66, very likely a coarser echo of inst_accum (+1.88)
that the institutional theme already owns.

**Two silent-failure bugs caught, both now pinned by tests:**
1. The SEC RENAMED the forms during 2024 ("SC 13D" -> "SCHEDULE 13D"). The old spelling returns
   ~30 filings/quarter for 2025-2026 vs ~15,000 - the most recent panel dates would have carried
   a structurally-zero signal while looking perfectly healthy.
2. form.idx is nominally fixed-width but the column offsets have MOVED over EDGAR's history; a
   fixed-width parse scored 0/200 rows on 2015. Parsed by structure instead (98.6-99.5% across
   1998/2015/2024).

Honest deviation: the docstring specifies absence -> 0.0, but the panel wiring skips tickers with
no filing history at all, so coverage is 58.5% not ~100%. That made the test EASIER (the
never-filed mass is excluded) and activist_13d still went negative, so the verdict stands.

Point-in-time: only `Date Filed` is read - the public disclosure date. The event date (crossing
5%, up to 10 days earlier) is never parsed. Tests 79/79.

**Next - P24 items 3 and 4 are UNTOUCHED:**
- USAspending.gov contract awards (use the award ACTION/entry date)
- Congressional trades (use the PTR DISCLOSURE date, NEVER the transaction date - it lags up to
  45 days, and using the trade date would be look-ahead)

## P24.1 — FINRA short interest: TESTED AND REJECTED (2026-08-01)

Downloaded FINRA's consolidated short interest: **3,866,270 rows -> 48,539 tickers** (1,294s,
cached to `data/bulk/prepared/short_interest.pkl`). Two signals wired, measured, rejected.

    signal                    median IC    IC t   n_dates   gate (t >= 2.0)
    neg_days_to_cover           +0.0147   +1.04        33   FAIL
    neg_short_interest_chg      +0.0133   +0.42        33   FAIL
    -- controls, SAME 34-date window --
    ret_6_1                     +0.0643   +3.53        34
    inst_accum                  +0.0669   +3.27        34

**The controls are the point.** The pre-committed caveat was that 34 dates might be too few to
detect anything. They are not — on this exact window ret_6_1 shows at t +3.53. The window has
ample power to see an effect of that size, so t +1.04 is an absence of SIGNAL, not an absence of
EVIDENCE. That is a real verdict, not an inconclusive one.

Both signs came out as pre-committed (both median ICs positive). The orthogonality premise was
also correct and did not save it: neg_days_to_cover correlates only +0.048 with ret_6_1 and
+0.034 with inst_accum — genuinely new information, simply not predictive. It is -0.311
correlated with size, so days-to-cover partly re-expresses a size effect the book already has.

POINT-IN-TIME: FINRA exposes `settlementDate` and no dissemination field, so using it directly
would inject ~2 weeks of look-ahead. Every observation is stamped `settlementDate + 15 days` and
the raw settlement date is never returned to callers. Pinned by a test.

Coverage 90.4% within the 2018+ window (plumbing works); 40.0% of the full 110-date panel — a
data-availability ceiling, as FINRA publishes nothing before 2018. Standalone gate not cleared,
so the held-out comparison was not run. Both signals stay MEASURED, scoring in no theme.

Tests 78/78. Downloader and publication-lag machinery kept — correct and reusable; only more
history would change the verdict, and FINRA does not publish it.

**Next:** P24 items 2-4 untouched — SEC EDGAR 13D/13G (use FILING date), USAspending (award
action date), congressional trades (PTR DISCLOSURE date, never transaction date).

## Hot Stocks ⇄ Valquo Index unified, with a Roth/Taxable toggle — AND the UI is finally VERIFIED

**The blocker is gone.** `pip install flask werkzeug jinja2 openpyxl reportlab` (all already in
`requirements.txt` — it was purely a missing local env) means the app now imports, renders and
serves in tests. Everything shipped blind in earlier sessions is confirmed working:

| previously unverified | now |
|---|---|
| OG/Twitter meta tags | `GET /` → **200**, `og:image` present and **absolute** |
| signup/pricing gating | `/register` → 302, `/pricing` → 302, no signup CTA in the HTML |
| options endpoints | `/api/option-alerts/open` without a token → **401** |
| **`test_saas` suite** | **20/20 passing** — unrunnable for this entire project until now |

### One ranking, two views (no second index)

`/api/valquo-index?config=roth|taxable` builds the book from **the same snapshot the Hot Stocks
tab reads**, so the Index is a disciplined *slice* of the ranking rather than a competing
screen. A test pins that: the roth 25-name book is exactly the first 25 of the taxable decile,
and the Index never reorders the ranking.

The Hot Stocks tab now carries an **account-type toggle** (roth = top-25 / ~2-month / no band;
taxable = decile / quarterly / 20% band) and both blurbs — *Hot Stocks is the full ranked screen
(discovery)*, *Valquo Index is the disciplined, backtested book you would hold and track*.

**Gating fix found by a failing test:** `/api/valquo-index` was login-walled while
`/api/hotstocks` is a public read. Login-walling one view of a ranking while the other is open
makes no sense, so it is now public too — the endpoint, not the test, was wrong.

### What is NOT done, and the decision it needs

The scan still **sources Hot Stocks from the FMP snapshot**, not `score_universe_now`. Both
views now share one ranking, but that ranking is still the live-scan one. Pointing the scan at
the Sharadar full universe is a one-function change — the blocker is a real trade-off only Don
can settle:

* **Sharadar** is point-in-time and full-universe (2,827 names, the thing that was validated),
  but the export is a **static file, currently as-of 2026-07-24** — Hot Stocks would go stale
  between manual re-exports.
* **FMP** is live and daily, but is a smaller universe and is not point-in-time.

Recommendation: keep Hot Stocks on the live FMP scan for **discovery** (users expect current
data) and drive the **Index** off a periodic Sharadar scoring, since a book rebalanced every
~2 months does not care about a week of staleness. That keeps both honest without pretending a
weekly-stale screen is live.

---

## RESEARCH TRACK CLOSED — all three items tested, all three REJECTED

Every item got a gate committed results-free BEFORE it ran, and every one failed honestly. The
shipped model is unchanged: **nothing was adopted, and nothing needed to be un-adopted.**

| item | gate commit | verdict | headline |
|---|---|---|---|
| ML tree combiner | `620e0a5` | REJECT | OOS IC +0.0531 linear vs **+0.0393** GBM; net alpha −8.2pp roth / −4.0pp taxable |
| PEAD | `9323a08` | REJECT | `pead_car` t +2.21 standalone but fails the held-out margin **both** ways |
| Elite-manager 13F | `5a3ccfb` | REJECT | t **+1.32** vs a 2.0 bar, and *below* both signals already in the theme |

### Elite-manager 13F — the last swing

Built from 282,487 manager-quarters of quality, 235,271 **point-in-time** skill scores (a
manager's score at quarter *q* uses only quarters strictly before *q*), elite conviction for
13,110 tickers, via two bounded streaming passes over the 2.9GB SF3 file.

| signal | median IC | IC t | coverage |
|---|---|---|---|
| `sm_elite_conviction` | +0.0274 | **+1.32** | 58.5% |
| `sm_breadth` (already in theme) | +0.0204 | +1.73 | 61.4% |
| `inst_accum` (already in theme) | +0.0314 | +1.88 | 61.4% |

Weighting by manager track record moved conviction from t ≈1.26 → **1.32**: noise. It still
scores **below both signals already in the institutional theme**. The hypothesis that manager
identity carries information the crowd average lacks is **not supported**.

**This is not a plumbing failure** — the skill scores are real and point-in-time, and coverage
(58.5%) is near the ~61% ceiling that 13F starting in 2013 imposes. If revisited, the lever is a
better *definition* of elite (concentration, turnover, persistence of edge), **not** more careful
weighting of trailing returns, which is what failed.

### What this closes, and what it means

The ML result said the only lever likely to help was **new orthogonal data**. Two new-data swings
followed and both missed. Taken together the picture is consistent and worth stating plainly:
**the signal set is saturated for this dataset.** Value/quality/momentum/size/institutional over
18 years of quarterly Sharadar is what there is; more model capacity (ML), more of the same data
re-cut (PEAD from prices, 13F re-weighted) does not add to it.

The remaining levers are genuinely different data — the ones in VALQUO_NEXT_EDGE Tier 2 that were
never started: FINRA short interest, SEC EDGAR 13D/8-K, congressional trades, and IBES estimate
revisions (still parked, and the one thing that would make a *real* PEAD possible).

---

## PEAD — built and REJECTED (the decode that unblocked it stands regardless)

Gate committed results-free in `9323a08`. Signal = cumulative abnormal return over [t−1, t+1]
around the most recent announcement vs the benchmark (the surprise measured by the market's own
reaction, since we have no point-in-time estimates), plus a recent-only "drift" variant.

| signal | median IC | IC t | coverage | standalone gate |
|---|---|---|---|---|
| `pead_car` | +0.0100 | **+2.21** | 82.3% | PASS |
| `pead_drift` | −0.0020 | −0.47 | 25.1% | FAIL |

`pead_car` clears standalone but **fails the held-out margin in both directions** — early
+0.03 t / −0.08% alpha, late −0.09 t / −0.35% alpha. **REJECTED.**

**Two diagnostics that matter more than the verdict:**

1. **The drift variant has no signal.** PEAD theory says drift is *strongest* right after the
   announcement, yet the ≤63-day window scores **t −0.47** while the all-ages CAR scores +2.21.
   That is backwards — whatever `pead_car` measures, **it is not post-earnings drift**, so its
   +2.21 must not be read as evidence for PEAD.
2. **It is partly momentum we already own.** Within-date correlation **+0.286 with `ret_6_1`**,
   +0.241 with `high_prox`, +0.200 with `ret_12_1`. An earnings CAR from months ago is largely
   "this stock has been rising", which `ret_6_1` already captures at **t +3.40** — nearly double.
   Adding it dilutes a stronger signal with a weaker correlated one, exactly as the held-out
   numbers show.

Both variants stay **measured but score in no theme**, so the negative result is permanent and
re-testing is one line. A cleaner PEAD needs a real earnings *surprise* (reported vs expected),
which requires point-in-time estimates — IBES, still parked.

---

## EVENTS earnings-code legend DECODED — PEAD unblocked after being stuck since P2

Sharadar ships no legend with the EVENTS download, and the earlier guess (codes 11-17) was
wrong, so `bulk.EARNINGS_CODES` sat deliberately empty and `earnings_dates()` returned `[]`.
Rather than guess again, code **22** was identified by two INDEPENDENT signatures:

**1. Timing against the SF1 filing date.** Code 22 sits a median of **3 days BEFORE** the
filing with 46.4% of occurrences within ±3 days — the announce-then-file pattern a real
earnings release has. No other code comes close.

**2. Information content — the decisive test**, and the property PEAD actually needs. Median
absolute return on the event day, 372 tickers:

| code | events | \|ret\| on day | baseline | ratio |
|---|---|---|---|---|
| **22** | 17,996 | **2.121%** | 1.292% | **1.64×** |
| 91 | 48,207 | 1.482% | 1.293% | 1.15× |
| 71 | 14,258 | 1.459% | 1.288% | 1.13× |
| 81 / 52 / 11 / 34 / 57 | — | — | — | 0.84–0.98× |

Every other candidate is indistinguishable from a random day. `earnings_dates()` now returns
real dates (AAPL: 93 of them, cleanly quarterly — 2025-07-31, 2025-10-30, 2026-01-29,
2026-04-30).

**Coverage caveat, stated not buried:** code 22 appears ~2.83×/ticker/year, not the ~4 a full
quarterly calendar would give — EVENTS coverage of earnings is **partial**. Treat a missing
earnings date as *unknown*, never as "no announcement".

An existing test asserted `earnings_dates() == []` ("deliberately inert"). That behaviour was
correct while the legend was unknown and is now obsolete; the test was updated to assert the
new behaviour, and to check the OLD wrong guess (code 11) does *not* qualify.

---

## ML tree combiner — TESTED AND REJECTED on every criterion

Gate committed results-free in `620e0a5` before running. GBM over the 31 currency-correct
z-scored signals, target = cross-sectional rank of forward return, judged on the **same purged
CPCV paths** the linear weights face.

| metric | linear | GBM | delta |
|---|---|---|---|
| median OOS IC (15 paths) | **+0.0531** | +0.0393 | **−0.0138** |
| paths where GBM wins | — | **33%** | worse 2 in 3 |
| roth top-25 net alpha | **+10.27%** | +2.04% | **−8.23pp** |
| taxable decile net alpha | **+6.70%** | +2.66% | **−4.04pp** |
| roth net Sharpe | **0.99** | 0.68 | |

Both halves agree; the late half is brutal (roth **+16.31% → −4.48%**, −20.79pp). The one cell
where GBM wins — roth, early half, +3.86pp — is the classic signature of structure found in one
regime that does not survive into the next.

**The useful interpretation:** trees can *express* "value only pays when quality is high"; they
cannot *learn* it reliably from 110 dates of 8 themes. The linear composite is not leaving money
on the table — it is the right amount of structure for the evidence available. **Do not re-open
with a different model.** Re-open only with materially more data: longer history, higher
rebalance frequency, or genuinely new orthogonal features.

**A real bug found en route (kept):** sklearn's binner raised `window shape cannot be larger
than input array shape` because the 13F signals are empty before 2013-06-30, so an early CPCV
fold hands it an all-NaN column. The whole-panel coverage check passes *precisely because* the
later folds have data — the filter has to be **per-fold** (`_usable_features`). sklearn stays an
optional import (it is not in `requirements.txt`); a missing import returns a status dict.

---

## Valuation-regime overlay — REJECTED, harder than the trend filter

Rule + bar committed results-free in `f567d01` before running. Primary rule (**one** rule, not
three): market-cap-weighted earnings yield `sum(NI)/sum(mktcap)` per rebalance — summed, not
averaged, so one freak micro-cap cannot move it and loss-makers net off — risk-off when it sits
at or below its **20th percentile over all PRIOR dates** (expanding window, min 20 dates). An
absolute multiple would be hindsight: "over 20x is expensive" is a fact about the last 20 years
nobody knew in 1998. Median P/E and PEG were computed as **diagnostics only, explicitly not
alternative rules** — three rules would be three chances to get lucky on one episode.

| config | net ann | Sharpe | max DD | flips | invested |
|---|---|---|---|---|---|
| no overlay | +30.69% | 1.13 | −57.0% | — | — |
| off = 0% | +26.58% | 1.05 | **−57.0%** | 8 | 94% |
| off = 50% | +28.75% | 1.11 | **−57.0%** | 8 | 94% |

**Max drawdown does not move at all** — identical to three decimals in every configuration. The
rule fires on only 10 of 165 rebalances and never during the actual crash. Sharpe is worse in
**both** halves (early −0.07/−0.01, late −0.10/−0.04), and drawdown improves in neither.

**The mechanism is the failure the spec predicted:** while risk-off, the book returned
**+10.02% per period (+77.3% annualized)**. It sat out the *best* periods, not the worst.
*Expensive* and *about to fall* are different things, and an aggregate valuation percentile
picks up the former with no information about the latter. Unlike the trend filter there is not
even a tempting full-sample story to argue about.

**NOT ADOPTED.** `settings.VALUATION_REGIME_OVERLAY`, default off.

Two caveats on the reported levels (they do not affect the rule — a percentile against its own
history is invariant to a constant basis): the aggregate yield uses the panel's **quarterly**
ARQ net income, so the implied "P/E ~96x" is a quarterly-flow artifact (×4 ⇒ ~24x annualized,
which is plausible) and should not be quoted as a market P/E; and aggregate **PEG came back NaN**
because revenue growth is not persisted on panel rows — reported as unavailable rather than
approximated.

---

## Regime risk-off overlay — REJECTED, and the best argument yet for pre-commitment

The rule and its adoption bar were written and **committed in isolation (`bfbde7e`) before it
was run**, so the git history proves nothing was tuned to the outcome. Classic 200-day trend
filter: at each rebalance, benchmark close vs its own trailing 200-trading-day SMA (strictly
past closes); above → fully invested, at/below → risk-off exposure. Cash credited **0%**, which
is deliberately harsh — real bills paid 2–5% over this window, so the return give-up shown is
an overestimate.

**On the full sample it looks like an obvious adopt** (top-25, 42d, 165 rebalances):

| config | net ann | Sharpe | max DD | flips | invested |
|---|---|---|---|---|---|
| no overlay | +30.69% | 1.13 | −57.0% | — | — |
| off = 0% | +24.48% | 1.08 | −36.9% | 24 | 77% |
| **off = 50%** | +27.98% | **1.17** | **−37.0%** | 24 | 77% |

At 50% risk-off: drawdown **−57.0% → −37.0%** (20pp better), return give-up only **2.70pp**,
and Sharpe **improves** 1.13 → 1.17. **Both numeric criteria PASS.** I would have adopted it.

**The held-out criterion kills it:**

| half | base maxDD | off=50% | improvement | Sharpe Δ |
|---|---|---|---|---|
| early (has 2008) | −57.0% | −37.0% | **+20.0pp** | +0.18 |
| late | −34.8% | −34.8% | **+0.0pp** | **−0.08** |

**The entire benefit is one episode.** In the recent half it does nothing for drawdown and
*costs* Sharpe. That is exactly what criterion 3 ("must improve in BOTH halves — a rule that
only works in the half containing 2008 fits one episode") was written to catch, before any
number existed.

**Verdict: NOT ADOPTED.** Shipped as `settings.REGIME_OVERLAY`, **default `None` (off)** —
available to anyone who wants crash insurance and accepts paying for it the other ~90% of the
time. Whipsaw for the record: 24 flips over 165 rebalances (~15%), out of the market 23% of the
time.

**The transferable lesson:** a full-sample result that improves drawdown 20pp, costs almost no
return, AND raises Sharpe is exactly the shape of thing that gets adopted on sight. It took a
pre-committed out-of-sample rule to see that it was one crash wearing a strategy's clothes.

---

## Sector concentration cap — TESTED and REJECTED

A max-per-sector weight on the Roth top-25 (a concentration RISK control — **not** the
sector-NEUTRAL *ranking* rejected in P10, which re-scored every name against its sector peers;
this only skips a name once its sector is full and keeps composite order otherwise).

| cap | net α | Sharpe | max DD | Δ Sharpe | Δ maxDD | Δ α |
|---|---|---|---|---|---|---|
| none | +17.37% | 1.17 | −56.8% | — | — | — |
| 35% | +16.64% | 1.15 | −56.6% | −0.02 | +0.2pp | **−0.73pp** |
| 25% | +16.45% | 1.15 | −56.4% | −0.01 | +0.4pp | **−0.92pp** |

**REJECTED** — it costs 0.73–0.92pp of return and buys 0.2–0.4pp of drawdown and *negative*
Sharpe. No help in either half (none 1.12/1.20 · 35% 1.13/1.15 · 25% 1.11/1.18).

Two reasons *why*, which are more useful than the null: **the book is already diversified**
(mean max single-sector weight 27%, median 24%, above 35% on only 12% of dates, so the cap
rarely binds), and **the −56.8% drawdown is a market event** (2008–09), not a sector-
concentration event — capping sectors cannot help when everything falls together. If drawdown
is the worry, the lever is market exposure, not sector mix.

Sector is now persisted on panel rows and `max_sector_w` is a live parameter on both
backtests, so this is re-testable in one line if the book ever gets more concentrated.

---

## Options outcome API — the Cowork filler is unblocked

Two token-guarded endpoints (`X-Admin-Token`, same as the learning hook — the caller is a
scheduled process, not a browser):

- `GET /api/option-alerts/open?limit=N` → the work list of alerts awaiting outcomes.
- `POST /api/option-alerts/outcome` → one object or a list of
  `{alert_id | (ticker, alert_ts) | (occ_symbol, alert_ts), exit_premium, exit_ts, exit_reason,
  contracts}`. Returns `{written, failed, failures}` — an unmatched or already-closed alert is
  **reported, not silently dropped**, so the filler knows a write did not land.

**P&L is recomputed from the STORED entry premium**, never taken from the caller, so the
scorecard can never disagree with the prices the alert was logged against.

**Bug caught while writing it:** `store` inside `create_saas_app` is the **UserStore**
(accounts DB); `option_alerts` lives in the **screener** Store. My first version queried the
wrong database entirely. Both endpoints now construct the screener `Store()` explicitly, and a
test pins that source-level fact (flask is not installed here, so the routes cannot be
exercised at runtime — the endpoints are **runtime-unverified**, worth one curl after deploy).

---

## `roth` ADOPTED as the default book — and a cadence LABEL correction

`DEFAULT_BOOK_CONFIG = "roth"` (Don trades in a Roth, so no tax drag). The headless CLI takes
`--config roth` / `--config taxable`, which fixes width, cadence and band together so an
emitted book cannot drift from the construction that was validated:

```
python -m valuation.edge.valquo_index --full-universe data/backtest --config roth
  -> 25 of 861 eligible (1809 scored), rebalance every 42 trading days (~2.0 months), no band
```

**LABEL CORRECTION — the config is ~2 months, not 6 weeks.** `rebalance_days` is in TRADING
days, so 42d is ~8.4 calendar weeks. I had called it "6-week" in the previous handoff. Having
noticed, I measured the genuine 6-week point (30 trading days), which was never tested:

| cadence | Sharpe (full/early/late) | net α | turnover | cost drag |
|---|---|---|---|---|
| monthly (21d) | 1.09 (1.19/1.01) | +13.70% | 523% | 6.03% |
| 6-week (30d) | 1.11 (1.09/1.13) | +14.51% | 437% | 5.04% |
| **2-month (42d)** | **1.17** (1.12/**1.20**) | **+17.37%** | 379% | 4.40% |
| quarterly (63d) | 1.12 (1.17/1.06) | +14.99% | 300% | 3.35% |

**The construction Don adopted is still the right one** — 42d has the best Sharpe overall and in
the recent half. But a true 6-week cadence is *worse* than both its neighbours (1.11), so the
name mattered: anyone implementing "6 weeks" from the old note would have traded a worse book.
`taxable` is unchanged (decile / quarterly / 20% band).

---

## SCREAM-BUY OPTIONS: expectancy loop replacing the success-rate tracker

`options_exit.py` measured the UNDERLYING's move under an exit discipline. That answers the
wrong question twice: an option's P&L is not the stock's move (premium, theta and vega sit in
between), and a bare **"success rate" is meaningless for an asymmetric payoff** — a 40%-hit
setup whose winners triple beats a 70%-hit one that gives it all back on the losers.

New `valuation/edge/options_tracker.py` + an `option_alerts` store table:

1. **Log the CONTRACT and the fingerprint.** ticker, right, strike, expiry, entry premium,
   timestamp, plus what fired it: score, momentum/technical scores, IV and IV rank, horizon,
   target delta, DTE, options-flow read, labels, and a JSON `features` blob so a new feature
   never needs a migration. Deduped on (ticker, alert_ts, OCC symbol). Missing chain detail is
   allowed — the fingerprint is what the tuning loop learns from, so an alert with no strike is
   still worth recording.
2. **Score EXPECTANCY, never a bare hit rate:** hit rate *alongside* avg win, avg loss, profit
   factor, expectancy per trade, and cumulative P&L on a fixed 1-contract (100-share) basis.
   Profit factor with no losers reports **None, not infinity** — an undefined ratio must read as
   "no evidence", never as a spectacular score.
3. **Accrual-then-tune, hard-gated.** `MIN_CLOSED_PER_BUCKET = 30` on **both sides** of any
   comparison before a criterion may change. `tuning_candidates()` returns suggestions and never
   applies them, and lists what is `blocked` for want of trades. Options outcomes are
   heavy-tailed: with ten trades one triple-up decides the sign of every statistic.
4. **Surfaced on the Signals tab** (`/api/options-scorecard`), with thin buckets greyed and
   flagged, and an explicit "not enough closed trades to tune" line when below the floor.

**Cowork's half:** real fills and contract marks come from the Robinhood connector, which the
web app cannot reach. This app writes the alert; an external scheduled job calls
`record_outcome(...)` to fill `exit_ts / exit_premium / exit_reason`, and P&L is computed
**here** from the stored premiums so the scorecard can never disagree with them. Everything is
built to be useful while outcomes are still missing — an open alert is a complete record of the
setup, and the scorecard reports honestly how few closed trades exist.
→ **Take the outcome-filling job to the Cowork chat.**

---

## TWO SHIPPED BOOK CONFIGS — concentration chosen on Sharpe, not return

`settings.BOOK_CONFIGS` now carries two tuned constructions, and the run measures both
(`book_configs` in BACKTEST_RESULTS.json).

### Why risk-adjusted, in one table

| width | net α | net Sharpe (full / early / late) | max DD | turnover |
|---|---|---|---|---|
| top 5 | +7.20% | 0.68 / 0.92 / 0.54 | −50.2% | 336% |
| top 10 | **+20.19%** | 1.12 / 1.35 / 0.93 | −24.5% | 322% |
| **top 25** | +14.99% | **1.12 / 1.17 / 1.06** | −38.6% | 300% |
| top 40 | +12.85% | 1.10 / 1.14 / 1.05 | −37.0% | 286% |
| decile | +11.44% | 1.11 / 1.19 / 1.02 | −41.7% | 251% |

Ranking on raw alpha would have picked **top 10 (+20.19%)** by a mile — its Sharpe is a dead
tie with top 25. And **top 5 is the clean lesson**: worst return *and* worst risk.

**top 25 chosen over top 10** on stability: top 10 swings 1.35 → 0.93 across halves (gap 0.42)
vs top 25's 1.17 → 1.06 (gap 0.11), and top 25 **wins the recent half outright**. top 10's
better max drawdown is real in both halves and is the tighter alternative if wanted — but a
10-name book over 110 periods is a thin basis for a drawdown claim.

### `roth` — tax-free, Sharpe-optimal, full rotation
**top 25, 6-week rebalance, no band.** Net alpha **+17.37%**, net Sharpe **1.17**, turnover 379%.

Frequency swept (top 25, net of cost): monthly **1.09** (1.19/1.01) · 6-week **1.17**
(1.12/**1.20**) · quarterly **1.12** (1.17/1.06). Faster *does* pay — but only to a point:
monthly's 6.03% cost drag overwhelms the benefit. 6-week is best on the full sample **and** in
the recent half, with the smallest early/late gap.

Note: **fundamentals only update quarterly**, so a 6-week rebalance re-ranks on fresh prices
(momentum, market cap) over stale fundamentals. That it still wins says the price-based
components carry real short-horizon information.

**Correction worth carrying: max drawdown is NOT comparable across frequencies.** A quarterly
grid observes the equity curve 110 times vs monthly's 330, so a coarser grid systematically
UNDERSTATES drawdown. Quarterly's −38.6% vs 6-week's −56.8% is substantially a sampling
artifact — do not read it as lower risk.

### `taxable` — after-tax-optimal, decile + 20% band
**decile, quarterly, 20% no-trade band.** After-tax alpha **+4.86%**, after-tax Sharpe **0.89**
(vs 0.84 unbanded), turnover 172%.

Tax drag (7.8%/yr) is over 3× the trading cost, so this optimizes after-tax Sharpe, which
favours breadth plus the band. **The band failed the pre-committed held-out margin in one half
(see below), so it is enabled HERE — for the account where it actually matters — rather than
made the global default.**

**Method bug I caught mid-sweep:** my first band sweep silently applied the band *only* to the
decile row — `exit_frac` is a fraction of the UNIVERSE and is meaningless for a fixed-N book, so
every fixed-N "with band" row was a duplicate of its no-band row. Added `exit_mult` (band as a
multiple of book size) so fixed-N books can be banded too. With it: decile+2.5× **0.89**,
decile+20% **0.89**, top-25+2.5× 0.88.

---

## git_push.bat now auto-lands finished agent branches (no more manual merge)

Claude Code works on `worktree-*` branches because its harness will not push to `main`, so every
session ended with a hand merge. `git_push.bat` now merges them itself before committing:
**fast-forward ONLY**, and only where `main` is already the branch's ancestor — which cannot
conflict and cannot rewrite history. Anything not a clean FF prints `[skip] <branch>` and is left
for you. One `.\git_push.bat` now lands and deploys.

Verified in a scratch repo, not just eyeballed — which mattered: **the first two versions were
broken** (`--format` paren escaping, then nested quotes inside `for /f '...'` needing `usebackq`)
and both of my first two *test setups* were wrong too. Final form merges the FF branch and leaves
a diverged one untouched.

---

## No-trade band — measured, and it FAILS the pre-committed gate (kept OFF, but read this)

Today a name is sold the instant it leaves the top decile. A band enters on the top 10% and
holds until the name falls past X. Full universe, 110 dates:

| exit band | turnover | gross α | net-of-cost α | **after-tax α** | cost drag | tax drag |
|---|---|---|---|---|---|---|
| none (10%) | 251% | +13.76% | +11.44% | +3.63% | 2.32% | 7.81% |
| 12% | 232% | +13.66% | +11.51% | +3.83% | 2.15% | 7.68% |
| 15% | 206% | +12.77% | +10.86% | +3.78% | 1.91% | 7.08% |
| **20%** | **172%** | +13.32% | **+11.69%** | **+4.86%** | 1.62% | 6.83% |
| 25% | 148% | +11.93% | +10.52% | +4.40% | 1.41% | 6.12% |
| 30% | 129% | +11.97% | +10.72% | +4.70% | 1.25% | 6.02% |

**20% is the knee**: turnover −31%, gross alpha −0.45pp, net-of-cost **+0.25pp**, after-tax
**+1.23pp (a 34% relative gain)**. Long-short t is unchanged by construction (3.396) — it
measures the whole cross-section, not the book.

**Held out, it does not clear the margin.** Applying the same split discipline to the metric that
actually moves (after-tax alpha, since `quantile_backtest` cannot see turnover):

| half | no band | 20% band | Δ | |
|---|---|---|---|---|
| early | +6.82% | +7.42% | **+0.60%** | fail (< 1% margin) |
| late | +0.88% | +2.76% | **+1.88%** | pass |

**Verdict by the pre-committed rule: `not_replicated`. Left OFF.**

**But it differs from every other rejection this project has made, and that is worth weighing:**
it is **positive in both halves** and never hurts — sector-neutral and zeroing `insider` each hurt
in one direction. And the turnover reduction (251%→172%) is **mechanical, not estimated**: it is
an arithmetic property of the rule, so the cost saving is deterministic in a way a signal's IC
never is. The margin it fails was calibrated for *signals*.

I did not flip it on, because quietly re-reasoning past my own gate is the failure mode the gate
exists to prevent. **Recommendation: adopt at 20%** — `exit_frac=0.20` in `turnover_and_costs` /
`after_tax_backtest`, and the band sweep now ships in `BACKTEST_RESULTS.json` under
`no_trade_band` every run. Your call.

**Caveat on the width:** the surface is noisy — 15% is worse than both 12% and 20% on gross alpha,
which should not happen on a smooth tradeoff. Do not over-trust the exact number; 20% is the best
point measured, not a precisely located optimum.

---

## Signup + Pricing hidden behind a flag (no paid tier exists yet)

The site was still showing "Sign up" and "Pricing" with nothing to sell. Both are now gated on
**`CONFIG.signup_enabled`** — a flag, not a deletion. Every route, template and Stripe path is
intact.

It **reuses the existing free-mode flag** rather than inventing a parallel one:
`signup_enabled` defaults to `not OPEN_ACCESS` (open/free product → nothing to sign up for),
with **`FEATURE_BILLING`** as an explicit override in either direction.

| config | signup/pricing visible | Stripe checkout |
|---|---|---|
| `OPEN_ACCESS=true` (today) | **no** | no |
| `OPEN_ACCESS=true`, `FEATURE_BILLING=on` | yes | no |
| `OPEN_ACCESS=false` | yes | needs a Stripe key |

**To re-enable later: set `OPEN_ACCESS=false` (or `FEATURE_BILLING=on`) in the environment.
No code change.**

Gated at the **route** as well as in the templates — `/register` redirects to `/app` and
`/pricing` to `/`. Hiding a button leaves the URL reachable from a bookmark, a stale link or a
search result, and a half-gated signup would create accounts the product no longer expects.

Surfaces changed: nav Pricing link and "Get started" CTA, footer Pricing link, both landing
CTAs, the beta banner's "Create free account", the login page's "No account?" line, and the
account page's "Upgrade" button.

**Deliberately NOT gated: login.** Existing accounts (including Don's) must still be able to
sign in when new signups are hidden. Anonymous visitors get **"Open the app"** instead, which is
accurate — `OPEN_ACCESS` already means no account is required for anything.

Two tests pin it: the flag truth table, and a sweep asserting no template carries an ungated
`/register` or `/pricing` link (an ungated button would now silently bounce a visitor, since the
routes redirect).

---

## P9b — headless book generation (`--full-universe`)

`python -m valuation.edge.valquo_index --full-universe [DATA_DIR]` now builds the book by
scoring the **whole Sharadar universe point-in-time** instead of the last live-scan snapshot.
The store path is what produced the degraded book: a few hundred scanned names means a "top
decile" collapses to the 10-name `MIN_NAMES` floor — ten mega-caps wearing a decile's label.

Verified end-to-end: **86 positions from 861 eligible large caps, 1,809 scored, as of
2026-07-24**, no live API needed, so the Cowork quarterly rebalance can run unattended. The CLI
also warns when `n_scored < 200` and prints any names excluded for unverifiable market cap
(this run: FFAI 5x, IQMX 0x, LESL 8x).

---

## P10 — sector data unblocked, and industry-relative ranking REJECTED on its merits

**The download worked.** Sharadar TICKERS, one paged API call, cached like the bulk tables:
**48,925 tickers**, 11 sectors, plus country/exchange/category. **Sector coverage is 100.0%
(2,826 of 2,827) of the panel universe**, so `sector_neutral` — which had been grouping on a
constant `""` and was therefore INERT in every backtest ever run — is now functional.

**Then it failed the test.** Sector-neutral scoring rebuilds every z-score, so it is not a
weight change and `holdout_theme_validate` cannot express it; `holdout_compare_panels()` applies
the same discipline in the right shape (split by time, embargo the boundary, require the
**already-committed** `MIN_HOLDOUT_*` margin in BOTH directions):

| split | long-short t | top-decile alpha | |
|---|---|---|---|
| early half | 0.56 → **0.97** (+0.41) | +6.69% → +6.53% (**−0.16%**) | fail |
| late half | 0.83 → **0.61** (−0.22) | +5.06% → +4.44% (**−0.62%**) | fail |

**Verdict: REJECT.** It never clears the margin, and in the later half it is worse on both
metrics. `sector_neutral` stays **off**. The capability is now real and re-testable — a future
change (e.g. sector-relative applied to only the value theme) can be tried without re-doing the
data work.

**Look-ahead caveat, stated not hidden:** TICKERS carries *today's* classification, so applying
it to a 1998 row assumes the company was in the same sector then. Reclassification is rare and
not return-predictive, so this is normally considered benign — but it is **the one non-PIT input
in an otherwise strictly point-in-time panel**, and that is a reason to be *more* sceptical of a
positive sector result, not less. It rejected anyway, so nothing rests on it.

### The remaining ADRs in the book are genuinely cheap — not residual artifacts

With country/exchange/category finally available: ADRs are **270 of 2,827 (9.6%) of the universe
and 9 of 86 book positions (12.4% of weight)** — 1.3x representation, against 28.3% before the
currency fix. Measured against the 1,164-name large-cap cohort:

| name | book_to_price | earnings_yield | ps |
|---|---|---|---|
| WDS (Woodside) | 0.98 (97th pct) | — | — |
| SKM (SK Telecom) | 0.71 (91st) | 0.017 (80th) | 4.29 (12th) |
| TTE (TotalEnergies) | 0.75 (92nd) | 0.032 (96th) | 2.98 (8th) |
| VOD (Vodafone) | 1.85 (99th) | — | — |
| IX (Orix) | 0.66 (88th) | 0.008 (48th) | 7.42 (25th) |
| ZTO | 0.53 (81st) | 0.018 (82nd) | 8.89 (31st) |

Cheap on book, earnings AND sales simultaneously — real value names. **One exception: TSEM is
expensive on all three** (24th / 18th / 95th percentile) and is in the book on other themes, not
value. Worth an eye, but it is a single ~1% position.

---

## P7 — CURRENCY FIX. The value theme was corrupt for foreign names; fixing it IMPROVED the model.

`marketcap` and `ev` are USD, but the raw line items are in the company's REPORTING currency.
Every value ratio dividing one by the other was wrong for the 4.1% of panel rows reporting in a
foreign currency — and all were pushed the SAME way, toward fake cheapness: SK Telecom's
`book_to_price` computed to **892 against a true 0.589** (~1,500x).

### Full 2,710-name universe, before vs after

| metric | BEFORE | AFTER | |
|---|---|---|---|
| **PBO** | 13.33% | **6.67%** | halved |
| Deflated Sharpe | >99.9% | >99.9% | saturated, unchanged |
| **Top-decile alpha** | +11.77% | **+11.82%** | +0.05pp |
| **Monotonicity** | −0.9394 | **−0.9515** | better-ordered |
| Net alpha (after costs) | +11.41% | +11.44% | +0.03pp |
| Long-short t | 3.485 | 3.396 | −0.09 |
| Breakeven | 235.6bps | 235.4bps | flat |

**All six value inputs improved** — book_to_price +0.07→+0.15, earnings_yield +2.33→+2.41,
fcf_yield +3.16→+3.17, ebit_ev +2.24→+2.29, neg_ev_sales +2.00→+2.11, neg_ps +1.40→+1.51 —
lifting the **value theme t from +1.34 to +1.46**. Six for six in the same direction is a
coherent pattern, not noise, and confirms the audit's hypothesis that contamination was part of
value's weakness.

The headline barely moves because value is 1 of 7 weighted themes and only 4.1% of rows were
affected. The real wins are PBO halving and the foreign distortion disappearing.

### Foreign-name share of the top decile

| | share of top decile | universe | over-representation |
|---|---|---|---|
| BEFORE | 4.79% | 3.54% | **1.35x** |
| AFTER | 1.98% | 3.54% | **0.56x** |

From 35% over-represented to 44% under-represented — what correct ratios imply, since these
names are expensive on real numbers (TSM PE 34.8, SKM PE 61.5).

**In the live book the effect is far larger** (large-cap AND value-tilted, so it concentrated
the distortion): foreign names fell from **21 of 86 positions / 28.3% of weight to 11 / 10.7%**,
and the top 10 went from **7 ADRs to 1**.

### Two corrections to CODE_AUDIT.md itself

1. **`neg_ps` is broken too — the audit marked it "ok".** It assumed `ps` came from Sharadar's
   ratio column; the panel computes `ps = market_cap / revenue` itself (USD/local). SKM's `ps`
   was **0.00 against a correct 5.13**. Fixed. Outside the letter of the task, inside its
   intent — leaving one value input corrupt defeats the purpose.
2. **`fxusd` is a DIVISOR, not a multiplier.** It is LOCAL UNITS PER USD (SKM 1514.2 won/USD).
   The audit's suggested `fcf × fx` would have SQUARED the error (~2.3 million x for SKM).
   Verified `equityusd/equity == revenueusd/revenue == ebitusd/ebit == 1/fxusd` exactly. Also
   there is **no `netincusd` column** — `netinccmnusd` (income to COMMON) is the right numerator
   against market cap anyway.

`total_equity` deliberately stays local: `gp_on_capital` divides local gross profit by it and is
only correct while both sides share a currency. `book_to_price` is now computed in the panel in
USD, with `build_frame` preferring the supplied value.

---

## P8 — SANITY LAYER. Coverage says a factor is PRESENT; this says it is SANE.

Four foundation bugs have now shipped with one signature: the run completes, raises nothing, a
factor is silently wrong. `signal_coverage` catches only the two that left a column EMPTY. The
currency bug filled every column and was simply incorrect.

`sanity_check()` ships a `sanity_check` block in BACKTEST_RESULTS.json: **range** (ratio factors
inside a plausible band), **subgroup** (does an identifiable subgroup systematically peg a
factor), **market_cap** (DAILY vs shares × price divergence).

### Validated against the bug it was built for

On PRE-fix values the subgroup check flags `book_to_price` and `earnings_yield` — foreign
reporters sat at the **86th percentile** of both. Post-fix every value factor lands in
**0.49–0.61**. **P8 would have caught P7 on its first run.**

Bands were CALIBRATED against known-bad vs known-good values on the same rows, not guessed. My
first attempt flagged 6.1% of good rows because **negative book equity is legitimate**.
`ev_sales`/`ps` are exempt from range checks — their tails are real near-zero-revenue companies
and the band flagged identical shares before and after the fix, a pure no-op. The subgroup check
covers them.

### It fires twice on CORRECTED data. Both true; neither a currency bug.

1. **`neg_log_mktcap`, foreign reporters at the 20th percentile** — real and expected, foreign
   companies with US listings are large. A true subgroup tilt, not a defect. **Left flagged
   rather than exempted:** silencing a guard after seeing it fire is how it becomes decoration.
2. **1.45% of rows with DAILY market cap >3x from shares × price** — AIV 71x, EQC 53x, genuine
   recycled-ticker cases (AIV/AIRC spun off 2020).

### The audit's M2 (SanDisk/WDC) does NOT reproduce

The task assumed this check would catch SNDK/WDC. **It does not, and that case appears not to be
this bug:**
- SNDK's DAILY cap ($336.7B) and shares × price ($212.7B) agree to **1.6x** — inside any sane
  band. WDC 1.2x.
- Its **148M share count is plausible**.
- Its price ran **48.60 → 1436.56 over 17 months with ZERO day-over-day discontinuities**; WDC
  10.3x and MU 8.5x over the same window — the whole storage complex moved together.

The figure is internally consistent. If still wrong, the error is upstream in the PRICE, which
both estimates share and **no cross-check between them can see**. Recorded as unresolved rather
than claimed as fixed: the audit asserted "~10x reality" from outside knowledge, and nothing in
the data marks it as an error.

**In the live book**, names diverging >3x are now DROPPED — a book is meant to be traded, and a
name whose size cannot be established should not be in it. 3 dropped: FFAI (5x), IQMX (0x), LESL
(8x). SNDK/WDC are not among them and remain. The BACKTEST keeps such rows and only flags them,
so validated history is never silently re-cut by a later guard.

---

## A full run was lost to my own bug, and the guard that followed

`sanity_check`'s warning path wrote to the `sys` MODULE instead of `sys.stderr`. That
`AttributeError` was swallowed by `run_backtests`' blanket `except`, skipping CPCV, construction,
walk-forward and regime — and the run still wrote a canonical BACKTEST_RESULTS.json with **every
metric null**, exit code 0. It reads as "ran, found nothing" rather than "broke": this project's
recurring failure signature, reproduced by me.

Hardened rather than merely fixed: an **`errors` block** in the JSON and a **DEGRADED RUN
banner** in the markdown whenever a validation block throws. Plus a test exercising the WARN
path — my tests all called `warn=False` and never touched the branch that raised.

**Tests: 121 passing** (edge 63, bulk 13, engine 19, intraday 13, screener 13).

---

## P6 — IS IT TRADEABLE? Yes. Three refinements tested, all three REJECTED.

**The headline: the edge survives realistic trading costs with a ~6x margin.** Everything
else in P6 was a proposed improvement, and none of them improved anything — which is a
useful result, because two of the three were my own recommendations.

### P6.1 — COSTS. The edge is tradeable. (KEPT: the measurement is now permanent.)

Every performance number in this project had been gross of costs, and zeroing `low_risk` in
P5 tilted the book smaller-cap, which is where costs bite hardest.

| book | annual turnover | gross alpha | net alpha | cost drag | **breakeven one-way** |
|---|---|---|---|---|---|
| top decile | 249% | +13.71% | **+11.41%** | 2.30%/yr | **236 bps** |
| top 25 | 296% | +20.69% | **+17.34%** | 3.35%/yr | **293 bps** |

The weighted-average one-way cost of what the book actually holds is **37 bps**, so breakeven
sits at a **~6.4x margin**. Even a punitive flat 100 bps still leaves +7.74% net alpha.
Turnover is high (~62% of the book per quarter) but nowhere near enough to eat the edge.

**The short side does not break it either** — the thing most likely to. The BOTTOM decile is
*larger*-cap than the top (median $4.50B vs $1.95B) and cheaper to trade (29.8 vs 37 bps), so
the long-short t = 3.49 is not resting on unborrowable micro-caps. Only 17% of the long book
sits under ~$500M.

Both method choices are deliberately unfavourable to the strategy: turnover counts weight
DRIFT between rebalances (not just entries/exits), and only the strategy is charged while the
equal-weight benchmark is left gross. **Borrow cost is NOT modelled** — it affects the
long-short statistic, not the long-only book, which is the thing anyone would actually trade.

Quote the **breakeven**, not the net alpha: it needs no belief in any particular cost
calibration. Runs on every backtest now, as a `costs` block and a Tradeability table.

*Annualization caveat:* these figures compound; `construction.*` annualizes arithmetically.
Same data, +13.7% vs +11.8% gross alpha. Compare cost numbers to cost numbers.

### P6.2 — TTM ROE/ROIC: REJECTED. The quarterly figure is BETTER.

Head-to-head on identical rows in one run:

| signal | median IC | IC t | coverage |
|---|---|---|---|
| **roe** (quarterly) | **+0.0439** | **+2.84** | 93.4% |
| roe_ttm | +0.0279 | +2.01 | 91.0% |
| **roic** (quarterly) | **+0.0420** | **+3.38** | 96.7% |
| roic_ttm | +0.0354 | +2.57 | 94.2% |

Smoothing over four quarters LOSES signal on both. The likely reason is **recency**: last
quarter's profitability predicts the next quarter better than a smoothed year does, and that
outweighs the fiscal-quarter seasonality TTM removes.

**This contradicts my own P5 recommendation**, which called quarterly ROE/ROIC a
methodological wart and TTM "the obvious next refinement". It isn't — the ARQ quarterly
figure is an advantage. Section 5.6 of the P5 notes below is superseded.

Both TTM variants stay MEASURED (in `NUMBER_THEME`, in the IC table) but do not score, so the
negative result is permanent and re-testing is one edit.

### P6.3 — median/MAD robust z-scores: REJECTED, and the reason matters more than the verdict.

| metric | classic (shipped) | robust |
|---|---|---|
| long-short t | **3.485** | 1.721 |
| long-short ann | **+17.58%** | +8.42% |
| top-decile alpha | **+11.77%** | +8.99% |
| monotonicity | **−0.939** | −0.624 |
| net alpha | **+11.41%** | +8.34% |
| PBO / DSR | 0.1333 / 1.0000 | identical |

The long-short t **halved** — while every individual theme IC stayed essentially unchanged
(quality +3.39 → +3.35, momentum +2.62 → +2.68, value +1.34 → **+1.68**).

**Why: rank-IC is invariant to a monotone rescaling; the composite is not.** Theme IC is a
Spearman correlation and literally cannot see this change. The composite is a weighted SUM of
z-scores and is very much scale-sensitive. MAD < SD for fat-tailed data, so dividing by the
smaller scale INFLATES the tails, and the top decile then gets selected by whoever has one
extreme factor reading rather than broad strength across themes. **Making the scale estimate
robust made the selection less robust.**

Generalizable lesson: **a signal's IC can be flat while the composite built from it moves a
lot.** Judging this change by per-signal IC would have called it harmless; it costs half the
long-short t. Kept behind `VALQUO_ROBUST_Z` (default off) so the result is re-testable.

### P6.3b — industry-relative ranking: BLOCKED, no sector data exists.

`fundamentals.csv` has **no sector / industry / SIC column**, and the panel hard-codes
`"sector": ""` on every row — so `build_frame`'s `sector_neutral` path has been **inert in
every backtest ever run** (it groups on a constant). The metadata lives in Sharadar's
**TICKERS** table, which is API-only and not among the four bulk tables on disk.

To unblock: one TICKERS download → a ticker→sector map → populate `metrics["sector"]` in
`_sf1_to_metrics`. Not fetched here because it is an outward-facing call on Don's paid
subscription. **Caveat to carry:** TICKERS gives *today's* classification, so applying it to
1998 rows is a mild look-ahead. Sector reclassification is rare and not return-predictive so
this is normally considered benign, but it should be stated rather than hidden.

### P6.4 — consolidating momentum + institutional: REJECTED. Both earn full weight.

They are +0.50 correlated, so the hypothesis was that we pay two theme weights for one
signal. Tested on the full sample and both halves (the composite is a weighted sum, so giving
the pair 0.0625 each IS a merged theme at 0.125 — no code change needed):

| config | full LS t | full top-decile | net alpha | early t | late t |
|---|---|---|---|---|---|
| **A current (.125 / .125)** | **3.48** | **+11.77%** | **+11.41%** | 2.57 | 2.56 |
| B consolidated (.0625 each) | 2.53 | +9.21% | +8.10% | 2.01 | 1.59 |
| C momentum only | 2.86 | +10.64% | +10.18% | 2.57 | 1.29 |
| D institutional only | 2.33 | +9.40% | +7.16% | 1.70 | 1.81 |

+0.50 correlation still leaves ~75% of variance unshared: they are **complementary, not
redundant.** A useful cross-check falls out — in the early half A and C are *byte-identical*,
because `institutional` has no data before 2013-06-30, independently confirming its 61.4%
coverage. In the late half, where it does have data, A beats both single-theme variants
decisively.

### P6.0 — the holdout threshold was pre-specified, and it changed two verdicts

`MIN_HOLDOUT_ALPHA_GAIN = 0.01` (100 bps/yr — an economic floor: an "improvement" smaller
than the cost of implementing it cannot be harvested) and `MIN_HOLDOUT_TSTAT_GAIN = 0.25` (a
noise floor). **Committed in isolation, before any P6 run** (commit `4de6e71`), so the git
history is the proof of when it was fixed. Disclosed honestly: I already knew the P5 numbers,
so this is a principled tightening rather than a blind pre-registration.

Effect, exactly as designed: `capital_discipline` went **confirmed → not_replicated** (it had
only ever passed on ΔLS t +0.01) and `insider` went **not_replicated → rejected**. `low_risk`
remains the only **confirmed** theme — the only one clearing a real margin in both directions.

### P6 net effect on the shipped model: NOTHING CHANGED

Three proposed improvements, three rejections. The model is byte-identical to the end of P5
(PBO 0.1333, DSR 0.999999, long-short t 3.485, top-decile +11.77%). What P6 added is
**knowledge**: the edge is tradeable, and three plausible refinements are now measured dead
ends rather than open questions. Two of the three were my own prior recommendations.

---

## 0. HEADLINE — five factors were silently empty, and fixing them changed the verdict

Every backtest this project has ever run scored on **8 of quality's 10 inputs, 1 of
low_risk's 2, and 1 of growth's 2.** No error was ever raised. The factors were wired, the
runs completed, and the columns were blank.

After fixing that and acting on what the corrected numbers said, on the **full 2,710-name ×
110-date universe** (identical universe in every run below — 136,478 rows, 63d validated
horizon, same 16.55%/yr equal-weight bar):

| metric | baseline (P4) | final | want |
|---|---|---|---|
| **PBO** | 40.0% | **13.3%** | <50% |
| **Deflated Sharpe** | 71.7% | **~100%** | >95% |
| **Long-short ann** | +8.13% | **+17.58%** | positive |
| **Long-short t** | 1.175 | **3.485** | >2 |
| Long-short hit rate | — | 66.4% | >50% |
| **Monotonicity** | −0.782 | **−0.939** | −1.0 is ideal (see §4) |
| **Top-decile alpha** | +5.11% | **+11.77%** | positive |
| Portfolio CAGR | +15.45% | +27.91% | — |
| Alpha vs equal-weight | +1.49% | +13.95% | — |

**This is the first time the project has cleared both statistical bars** (PBO < 50%,
Deflated Sharpe > 95%, long-short t > 2) — **and the biggest single contributor, zeroing
`low_risk`, has since been CONFIRMED on a held-out time split in both directions (§4b).**
Read §5 for what that does and does not establish.

Also: **the edge no longer collapses without 13F.** Strip the institutional theme and
top-decile alpha goes +11.77% → +10.64% with long-short t 3.48 → 2.86. At baseline the same
test collapsed the t to 0.71. The "the entire edge is 13F" finding in CLAUDE.md is now
**obsolete** — that was an artifact of quality and low_risk running on half their inputs.

**Every change was kept only after confirming it improves the full-universe combined edge**
(long-short t / Deflated Sharpe / PBO / top-decile alpha). The one change that did not pass
on first measurement — dropping `neg_asset_growth` — was re-tested head-to-head in the final
configuration and does pass (§3c). The derived inputs (§3a) are a **correctness fix, not an
optimization**: they cost 0.22 of long-short t while improving PBO, DSR and top-decile alpha,
and the alternative is knowingly scoring on 8 of 10 quality inputs.

**Tests: 107 passing** (edge 50, bulk 12, engine 19, intraday 13, screener 13). `test_saas`
(18) cannot run here — no `flask`/`werkzeug` installed in this environment, unrelated to
these changes and true before them.

---

## 1. The bugs — all five produced a completed run and no error

The export is **ARQ-only**, and Sharadar populates its averaged/ratio fields only in the
ART/ARY dimensions. Verified directly against `fundamentals.csv`: `roe`, `roic`,
`assetturnover`, `roa`, `ros`, `equityavg`, `assetsavg` are **non-null in 0 of 197,265
rows.** The raw ingredients were all present (`netinc` 97.7%, `equity` 99.9%, `invcap`
99.9%, `taxexp`/`ebt` 97.7%, `assets` 100%).

1. **`roe` empty** → derived as `netinc / equity` (requires equity > 0; a negative book value
   inverts the sign and would rank a wiped-out loss-maker as the highest quality name).
2. **`roic` empty** → derived as `ebit × (1 − effective tax) / invcap`, effective rate =
   `taxexp / ebt` clipped to [0, 0.60], falling back to the **date-aware** statutory rate
   (35% pre-2018, 21% after — the TCJA cut) when pre-tax income ≤ 0 makes the rate
   meaningless.
3. **`assetturnover` empty** → derived as `revenue / assets`. This made **F-Score test 9
   evaluable for the first time**; the `≥6 usable tests` guard had been absorbing its absence
   silently.
4. **`beta` hard-coded `None`** → `low_risk` was `neg_vol` alone. The regression that
   produces beta was *already running* inside `_price_extras` for `neg_idio_vol`; only its
   slope was being discarded. Now exposed.
5. **`growth_accel` clobbered** (not on the original list — the guard found it). The panel
   computes it correctly in `_yoy` from two prior-year point-in-time rows; `build_frame` then
   overwrote it with `revenue_growth − revenue_growth_prior`, and the panel never supplies
   `revenue_growth_prior`. All-NaN. `growth` was `revenue_growth` alone.

### 1a. The mechanism that hid three of them: `_f()` returned NaN, not None

`pandas` reads a blank CSV cell as `float('nan')`, and `_f()` returned it. That is not
`None`, so **every `if x is not None` guard in the panel silently accepted missing data.**

The damaging case was **`_f_score`**: `cr > cr_p if (cr is not None and cr_p is not None)` is
`True` when `cr` is NaN, and `NaN > NaN` is `False` — so a missing input was scored as a test
the company **FAILED**, *and* still counted toward the `≥6 usable` guard. Thin rows came back
as confident low scores instead of `None`. This affected `currentratio` (blank in 18.4% of
rows) and `debtnc` (18.3%). Fixing it moved `f_score` t from +2.80 to **+2.74** and its
coverage from 96.8% to 95.1% — very slightly *weaker*, because it is now honest.

Fixing `_f` also exposed a **latent crash** in `_yoy` (`None - float`) that NaN arithmetic had
been absorbing: the growth_accel branch tested `"revenue_growth" in m`, but the metrics dict
is pre-seeded with `revenue_growth=None`, so that key is *always* present.

---

## 2. THE CHEAP FIX THAT WOULD HAVE CAUGHT ALL OF THIS — coverage guard

`signal_coverage()` measures every wired number and theme, warns to stderr under 5%
coverage, and ships the result in `BACKTEST_RESULTS.json` under `signal_coverage`
(`below_floor` is the load-bearing part). Coverage is measured on the **standardized**
column, so a present-but-constant column correctly reads as unusable rather than covered.

Confirmed against the committed baseline: `roe`, `roic`, `neg_beta`, `growth_accel` were all
at **exactly 0.0%**. The guard would have flagged all four on day one.

- The floor is 5% — far below any plausible real coverage. The thinnest genuine theme,
  `institutional`, sits at 61.4%.
- Exemptions are an **explicit list** (`COVERAGE_EXEMPT_THEMES = {"sentiment"}`), not
  "any zero-weight theme". I initially inferred it from the weight and that immediately
  went wrong: zeroing `low_risk` (§3) silently disabled the guard for `neg_beta`. A theme
  zeroed because it was *measured and found wanting* still has data, and a plumbing bug in
  it must still be reported. Only genuinely source-less hooks belong on the list.
- Free performance win: `run_backtests` now builds the validated panel once with
  `keep_numbers=True` and derives coverage + per-signal IC from it, **removing a whole
  duplicate full panel build** from every run (`main()` used to rebuild it).

---

## 3. Decisions taken, and the evidence for each

### 3a. `roic` / `roe` — the two strongest signals nobody was using

| signal | median IC | IC t | coverage | rank in panel |
|---|---|---|---|---|
| **roic** | +0.0420 | **+3.38** | 96.7% | 4th of 32 |
| **roe** | +0.0439 | **+2.84** | 93.4% | 6th of 32 |

Both were contributing nothing. `quality` is now the strongest theme in the model
(+0.0363, t **+3.39**). Alone, these lifted PBO 40% → 26.7% and DSR 71.7% → 80.8%.

Correctness check worth recording: **every other signal's IC t-stat matched the baseline to
two decimals**, confirming the change perturbed nothing it shouldn't have.

### 3b. `neg_beta` — no standalone signal, but it helped the composite

`neg_beta` measures median IC **+0.0019, t −0.05** (coverage 88.0%). Betting-against-beta
does **not** replicate here as a standalone factor. Yet adding it moved DSR 80.8% → 92.9%,
long-short t 0.951 → 1.065 and top-decile alpha +5.68% → +6.20%. A zero-IC input can
legitimately help by decorrelating, but a 12-point DSR move from a t = −0.05 signal is a
large effect from a weak cause — treat as encouraging, not established.

### 3c. `neg_asset_growth` — DROPPED (wrong sign, confirmed on the full universe)

Median IC **−0.0141, t −0.70.** The investment factor says *low* asset growth should predict
high returns; here high asset growth did. Averaging it in was cancelling `neg_issuance`
(+0.0232, **t +2.25**), the one input in the theme that works. `capital_discipline` is now
issuance alone and measures **+0.0232 / t +2.25** as a theme.

It stays computed and listed in `NUMBER_THEME` so it keeps being measured — re-adding it is
one column in `factors.py`.

Measured *sequentially* (i.e. while `low_risk` was still at 0.125) the drop looked **mixed**:
PBO 26.7% → 20.0% and DSR 92.9% → 94.95%, but long-short t fell 1.065 → 0.916 and the
concentrated book gave back ~2pp.

**Re-tested in the FINAL configuration (`low_risk` = 0) and the ambiguity disappears.** Both
runs below are the full universe and differ *only* in whether `neg_asset_growth` is in the
theme:

| metric | dropped (shipped) | restored |
|---|---|---|
| PBO | 0.1333 | 0.1333 (tie) |
| Deflated Sharpe | 1.0000 | 0.9999 |
| **long-short t** | **3.485** | 3.298 |
| **top-decile alpha** | **+11.77%** | +11.52% |
| long-short ann | +17.58% | +17.39% |
| portfolio CAGR | +27.91% | +25.25% |
| monotonicity | −0.939 | **−0.976** |
| **`capital_discipline` theme IC** | **+0.0232 (t +2.25)** | +0.0062 (t +0.77) |

Dropping it wins on every criterion except monotonicity, and restoring it cuts the theme's own
IC by roughly 4×. **The earlier "mixed" verdict was an artifact of measuring the change while
`low_risk` was still scrambling the ranking** — a reminder that sequential attribution can
mislead when the factors interact. Confirmed keep.

### 3d. `low_risk` — set to ZERO weight. The single biggest change.

**Corrected finding first:** CLAUDE.md records `low_risk` as having pooled IC **−0.048**.
That does **not** replicate. On the full universe with *both* inputs finally populated the
theme measures **−0.0014 (t +0.71)** — indistinguishable from zero. It was **dead weight,
not actively harmful.** The −0.048 came from a smaller universe with `neg_beta` empty.

Zeroing its 12.5% weight produced by far the largest single improvement of the session:

| metric | with low_risk | low_risk = 0 |
|---|---|---|
| PBO | 20.0% | **13.3%** |
| Deflated Sharpe | 94.95% | **~100%** |
| Long-short ann | +6.63% | **+17.58%** |
| Long-short t | 0.916 | **3.485** |
| Monotonicity | −0.794 | **−0.939** |
| Top-decile alpha | +6.24% | **+11.77%** |

**Why a ~zero-IC theme mattered so much — verified, not assumed.** I measured the
average within-date Spearman correlation between all themes on the full panel.
**`low_risk` vs `size` = −0.352, the strongest anticorrelation in the entire matrix.**
Low-beta/low-vol names *are* large caps, and `size` is an explicit small-cap tilt
(`neg_log_mktcap`, t +1.68). At 12.5% each they were fighting each other, and `low_risk`
brought no signal of its own to the fight. Removing it let the working themes express: the
deciles went from badly scrambled to nearly monotone (D1 22.8% → 28.3%, D10 16.2% → 10.7%).

Two other correlations worth knowing: **`momentum` vs `institutional` = +0.50** (half
redundant — a candidate for consolidation), and `insider` vs `size` = +0.24.

**Applied live and reversible:** `WEIGHTS_ESTABLISHED`/`WEIGHTS_SPECULATIVE` now carry
`low_risk: 0.0`. Restore by setting it back to 0.125. The weights need not sum to 1 — the
backtest ranks on a weighted sum (scale-invariant) and the live scorer renormalizes per name.

---

## 4. `monotonicity` HAS BEEN READ BACKWARDS — correct the mental model

`quantile_backtest` orders buckets by `argsort(-comp)`, so **bucket 0 is the HIGHEST
composite**, and `monotonicity` is `Spearman(bucket index, bucket return)`. A working signal
therefore makes it **NEGATIVE**:

- **−1.0 = returns fall perfectly from D1 to D10 → perfectly ordered, the ideal**
- 0.0 = no ordering
- **+1.0 = returns RISE from D1 to D10 → the composite is exactly backwards**

Verified numerically against synthetic perfect and inverted decile series.

CLAUDE.md's *"monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
cleanly ordered"* is **inverted**: −0.68 means they *were* well ordered. So is the P4 table
logging −0.782 → −0.855 as *"slightly worse"* — that was an improvement. Every past
"monotonicity is bad" conclusion in this repo needs re-reading with the sign flipped.

Now documented in the `quantile_backtest` docstring, shipped as
`construction.monotonicity_want` in the JSON, labelled in the MD table, and pinned by
`test_monotonicity_sign_convention`.

---

## 4b. HELD-OUT CONFIRMATION — `low_risk` survives, `insider` does not

The one check CPCV and the Deflated Sharpe cannot provide: they correct for the trials inside
the *weight search*, not for a human looking at a theme's IC on the whole panel and then
dropping it. Now a permanent part of the backtest (`holdout_theme_validate()`, shipped as
`holdout_validation` in the results file), not a one-off script.

**Protocol, fixed before looking at any result.** Split the 110 dates in half by time
(early 1998-12-31..2012-07-10, late 2013-01-10..2026-04-22); **embargo the boundary date**
(2012-10-08), whose 63-day forward window is the only one that can straddle the split. Decide
on one half using a pre-specified rule — *flag a theme whose median IC on the decide half is
≤ 0* — then measure on the other half only. Run both directions.

| theme | verdict | ΔLS t (E→L) | Δtop-dec (E→L) | ΔLS t (L→E) | Δtop-dec (L→E) |
|---|---|---|---|---|---|
| **low_risk** | **confirmed** | **+1.59** | **+3.21%** | **+2.02** | **+7.86%** |
| capital_discipline | confirmed | +0.43 | +1.22% | +0.01 | +1.04% |
| quality | not_replicated | +0.39 | +1.21% | +0.17 | −1.06% |
| **insider** | **not_replicated** | +0.08 | +0.78% | −0.09 | −0.47% |
| value | rejected | +0.05 | −0.94% | +0.11 | −0.11% |
| momentum | rejected | −0.61 | −1.46% | +0.11 | −0.76% |
| size | rejected | −0.84 | −3.41% | −0.92 | −5.59% |
| institutional | rejected | −1.10 | −3.67% | 0.00 | 0.00% |

**`low_risk` = 0 is CONFIRMED.** On the pre-registered direction (decide early → measure late)
the rule fires on the early half (median IC −0.0308) *and* the effect holds on untouched data:
long-short t 0.97 → 2.56, top-decile alpha +6.09% → +9.30%. The reverse direction agrees more
strongly still. This is the largest effect in the table by a wide margin.

**`insider` = 0 is REJECTED — left at 0.125.** It helped one direction by a hair and hurt the
other. Its −0.34 full-sample t is not a stable property. This is precisely why it was tested
rather than dropped on the strength of one number.

### Two things this table reveals that are more important than the verdicts

1. **A theme's own IC does not replicate, but the benefit of removing `low_risk` does.**
   `low_risk` measures −0.0308 on the early half and **+0.0411** on the late half — it flips
   sign. So "low_risk has ~zero IC" is really "its IC is noise that averages to zero", and the
   §3d framing was too confident. The benefit survives anyway **because it never came from the
   theme's own predictive power** — it came from removing the −0.352 cancellation of `size`.
2. **That mechanism is now independently corroborated.** `size` also flips (t **+3.17** early,
   **−0.67** late: the small-cap premium worked pre-2012 and not after), and the gain from
   removing `low_risk` **tracks it** — +7.86pp in the early half where `size` is strong, only
   +3.21pp in the late half where it is dead. The effect is largest exactly where the
   mechanism predicts. That is a prediction the data could have falsified and did not.
   `size` is also the theme most damaged by zeroing (−0.84 / −0.92 t), confirming it is
   carrying real weight rather than being redundant.

**Do NOT act on the `capital_discipline` "confirmed" row.** It passes on a knife edge
(ΔLS t **+0.01** in one direction — noise), and the verdict rule only requires the sign to be
right in both directions, not the magnitude to be meaningful. That is a genuine weakness of
the rule, left un-retrofitted on purpose: changing the threshold after seeing results is the
exact sin this whole section exists to prevent. Read `confirmed` as "the sign held up twice",
not "this is worth doing". `capital_discipline` also has a healthy theme IC (+0.0232, t +2.25),
which makes the row look more like decile-metric noise than a real finding.

---

## 5. WHAT I DO NOT TRUST — read before acting on §0

1. **The held-out test confirms the DECISION, not the hypothesis generation.** Both halves come
   from the same 18-year panel, the same universe and the same data vendor, and the
   size-cancellation mechanism was hypothesised on the full sample before being checked on the
   splits. A truly clean test needs data this project has never touched. What §4b does rule out
   is the specific failure I was worried about — that zeroing `low_risk` was fitted to noise in
   the very periods it was then scored on. It was not.
2. **Deflated Sharpe "100%" is a saturated probability**, not a proof. Report it as
   ">99.9%" and do not treat the bar as permanently cleared.
3. **CPCV vs long-short disagree on magnitude.** Removing `low_risk` moved median OOS IC
   only +0.059 → +0.060 while long-short t moved 0.92 → 3.48. The gain is concentrated in
   the *tails* (deciles), where fewest names sit and noise is highest. The IC evidence for
   this change is far weaker than the decile evidence.
4. **The concentrated top-25 hold book (CAGR +27.9%, alpha vs EW +13.95%) is the noisiest
   number in the file.** CLAUDE.md records top-25 as previously *losing*. Do not quote it.
5. **Sequential attribution misled me once already** (§3c): `neg_asset_growth`'s drop looked
   mixed when measured with `low_risk` still weighted, and clearly correct once re-tested in
   the final configuration. Every "stage N vs stage N−1" comparison in this document carries
   that caveat — the factors interact, so only the final head-to-head is authoritative.
6. **Derived ROE/ROIC are quarterly rates, not annualized.** Harmless for ranking
   (everything is z-scored cross-sectionally) and consistent with how `earnings_yield` /
   `op_margin` already work here, but it lets **fiscal-quarter seasonality into the
   cross-section** — different names sit at different fiscal quarters on a given rebalance
   date. A TTM version is the obvious next refinement and I deliberately did not fold it in
   silently.
7. **`institutional` coverage is 61.4% on the full universe**, not the 81.7% recorded in
   CLAUDE.md (that figure came from a smaller universe). `insider` is 85.0%.

---

## 6. NEW finding not asked for: `insider` is the actually-negative theme

With the per-theme table finally available:

| theme | median IC | IC t | coverage |
|---|---|---|---|
| quality | +0.0363 | +3.39 | 98.0% |
| momentum | +0.0517 | +2.62 | 96.6% |
| capital_discipline | +0.0232 | +2.25 | 96.8% |
| institutional | +0.0297 | +1.81 | 61.4% |
| size | +0.0126 | +1.68 | 100% |
| growth | +0.0221 | +1.45 | 93.0% |
| value | +0.0123 | +1.34 | 100% |
| low_risk | −0.0014 | +0.71 | 99.7% |
| **insider** | **−0.0034** | **−0.34** | 85.0% |
| sentiment | n/a | n/a | 0.0% |

**`insider` is the only theme with a negative t-stat, and it still carries 12.5% weight.**
It has since been tested properly on the held-out split (§4b) and **zeroing it did NOT
replicate** — +0.08 long-short t one direction, −0.09 the other. **Left at 0.125.** Its
negative full-sample t is not a stable property, and this is the clearest illustration in the
session of why a single number is not a decision: by the same reasoning that justified zeroing
`low_risk`, `insider` looked like the obvious next cut, and it did not survive the test.

`growth_accel`, now measurable for the first time: +0.0062, **t +0.50** — no real signal.

---

## 7. What's blocked / not done

1. **CLAUDE.md's separate "P5 — robustness" item is NOT done.** Winsorization already
   existed (`zscore` clips at 2%); **median/MAD robust z-scores and industry-relative
   ranking remain untouched.**
2. **Out-of-sample confirmation of the `low_risk` removal** — the single most important
   outstanding item (§5.1).
3. `sentiment` still has no point-in-time source (grades parked; `grades.csv` is 58 bytes).
4. `bulk.EARNINGS_CODES` still unpopulated, so `earnings_dates()` returns `[]` and PEAD is
   still blocked.
5. Social preview (og:image) untouched.
6. `inst_breadth` remains in `NUMBER_THEME` (so it is measured, t +1.08) but no longer feeds
   the institutional theme — `sm_breadth` replaced it in P4. Harmless drift, but the
   "single source of truth" comment in `settings.py` overstates what `NUMBER_THEME` controls:
   `factors.py` hardcodes the theme means.

---

## 8. Recommended next step, in order

1. ~~Confirm the `low_risk` removal out-of-sample~~ **DONE — confirmed (§4b).**
2. ~~Test zeroing `insider`~~ **DONE — rejected, left at 0.125 (§4b).**
3. ~~TTM ROE/ROIC~~ **DONE — REJECTED (P6.2); quarterly is better.**
4. ~~median/MAD robust z-scores~~ **DONE — REJECTED (P6.3); costs half the long-short t.**
5. ~~Consolidate momentum/institutional~~ **DONE — REJECTED (P6.4); both earn full weight.**
6. ~~Pre-specify the holdout magnitude threshold~~ **DONE (P6.0, commit `4de6e71`).**
7. ~~Are the returns achievable net of costs?~~ **DONE — YES, breakeven 236bps vs ~37bps
   actual (P6.1).**

**Now, in order:**

1. **Get data this project has never touched.** This is now clearly the top item. The edge
   clears every internal bar and survives costs; what it has never faced is data outside this
   one 18-year Sharadar panel. A forward paper-track starting today is the cleanest and
   costs nothing but time — **and it is the natural Cowork task** (tracked "Valquo Index vs
   SPY"). → *Take the paper-track to the Cowork chat.*
2. **Unblock industry-relative ranking** (P6.3b) — one Sharadar TICKERS download. It is the
   only P6 item that could not be tested at all, and `sector_neutral` has been silently inert
   in every backtest to date, so this is also a latent-bug fix.
3. **Live-behaviour watch after the P5 deploy.** `low_risk` went 12.5% → 0, so the hot list
   will tilt smaller-cap than before. That is intended, but the first post-deploy scans should
   be eyeballed. Revert is one line in `settings.py`.
4. **PEAD from EVENTS** — still blocked on `bulk.EARNINGS_CODES` (needs Sharadar's EVENTS
   legend). This is now the most promising *new* signal, since the cheap refinements are all
   exhausted.
5. **ML tree combiner**, now clearly worthwhile — there are several genuinely real signals to
   combine, and P6 shows the linear composite is sensitive to how inputs are scaled.
6. **Re-read every past "monotonicity" conclusion with the sign flipped** (§4).
7. Social preview (og:image) — still untouched, independent of everything else.

---

## 9. Standing notes

- `data/` is gitignored, as are `*.zip` / `*.csv.gz` / `*.parquet`. Nothing licensed was
  committed; `BACKTEST_RESULTS.*` carries derived metrics only (IC, t-stats, returns,
  weights) — no raw rows, prices or per-name fundamentals.
- Bulk layout: raw zips in `data/raw/`, extracted CSVs in `data/bulk/`, caches in
  `data/bulk/prepared/`.
- `DERIVE` in `fundamental_panel.py` toggles each derived input, so a validation change can
  be attributed to one signal instead of a bundle. All four ship **on**, and
  `test_all_derived_inputs_ship_enabled` fails the suite if one is left off.
- Results-file schema is now **version 2** (adds `signal_coverage` and `per_theme`; purely
  additive).
- The most recent SF3 quarter is always incomplete (filings arrive over following weeks) —
  the 45-day `inst_lag_days` convention handles it.
- The live hot-list scan runs at 22:23 UTC and uses the FMP key.
