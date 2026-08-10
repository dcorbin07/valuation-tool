# HANDOFF — V3, noise-calibrated hot score (lane r1, 2026-08-09)

Item **V3** of `VALQUO_EXTENSIONS.md`. Pre-registered in `PREREG_v3_score_calibration.md`, committed
**blind at `251c989`** before any number existed. Harness at `935be77`.

Reproduce:

```
python -m scripts.score_calibration \
  --panel data/free_analysis/panel_corrected_69d.pkl \
  --out   data/free_analysis/SCORE_CALIBRATION.json
```

Artifacts: `data/free_analysis/SCORE_CALIBRATION.json` + `SCORE_CALIBRATION.draws.csv`
(every draw banked — RUN_RULES A9). Tests: `tests/test_score_calibration.py`, 11/11.

---

## THE HEADLINE

**The pre-registered primary statistic FAILS. The product's confidence language must weaken, and
that consequence was accepted in writing before the run.**

| | |
|---|---|
| primary statistic (PREREG §7) | composite at **rank 10**, latest cross-section |
| real | **1.0909** |
| noise p95 | **1.1117** |
| empirical p | **0.116** (58 of 500 noise draws match or beat it) |
| **verdict** | **NOT DISTINGUISHABLE** |

Both halves of the registered bar agree (the p95 test and the empirical-p test), so there is no
ambiguity to adjudicate and no NULL escape hatch. **A reader told that the #10 name "scores 97/100"
is being given a number that roughly one in nine chance-assembled universes reaches at that rank.**

---

## THE INSTRUMENT IS NOT THE ONE V3 NOMINATED, AND THAT IS THE FIRST FINDING

V3 says to point X7's placebo harness at the product. **X7's permutation cannot calibrate a score
at all, and the reason is structural rather than a matter of degree.**

X7 shuffles the signal columns as a **whole-row block**. For a return-based statistic that is
exactly right — it severs signal from return and preserves everything else. But a score has no
return in it. Under a block shuffle a name's theme vector *and* its present-weight renormalization
denominator both travel intact, and the only thing that changes is which ticker the row is labelled
with. **The sorted composite therefore comes back identical — not approximately, identically.**

Measured, on the real 1,842-name cross-section, 500 draws: **composite sd ratio 1.000000**, and in
the smoke run five seeds returned **one distinct value to full float precision**. It is pinned by
`test_block_permutation_leaves_the_composite_multiset_exactly_unchanged`, with a companion test
proving the permutation really did shuffle the rows — so the invariance cannot later pass for the
wrong reason.

**Why this is worth a test rather than a remark.** A null built this way is the real book wearing a
different name tag. It completes, prints percentiles, and looks exactly like a measurement. If
someone later "simplifies" this harness to reuse `fundamental_panel.placebo_panel`, every V3 bar
silently becomes the real book compared against itself, and nothing in the output would say so.

**What was used instead — H1, coverage-preserving within-column permutation.** Each theme shuffled
independently among the rows that have it, within (date, bucket); every NaN left exactly where it
is. Preserved: each theme's marginal distribution within the bucket, its coverage, and **every
row's coverage pattern** — hence its renormalization denominator. Destroyed: **cross-theme agreement
within a name**, and nothing else. Because the denominator is identical between real and null, a
difference in the composite is attributable to agreement alone and not to a name being scored on
fewer themes. Both properties are pinned by tests.

X7's scheme still ran, as the **registered control with its no-op predicted in advance**. It passed.

---

## THE CALIBRATION TABLE — the deliverable

Latest cross-section (**2026-01-28**, n = **1,842**, decile edge #184), H1, 500 draws, seeds
3000–3499. Read a row as: *"a #k-ranked name with composite ≥ [noise p95] occurs in about 5% of
universes with no cross-theme agreement."*

| rank | real | noise p50 | **noise p95** | noise max | empirical p | clears p95 |
|---|---|---|---|---|---|---|
| 1 | 1.6367 | 1.3624 | 1.6677 | 1.9621 | 0.080 | no |
| 2 | 1.4979 | 1.2728 | 1.4538 | 1.6511 | 0.024 | yes |
| 3 | 1.4197 | 1.2127 | 1.3663 | 1.5421 | 0.010 | yes |
| 5 | 1.3417 | 1.1319 | 1.2576 | 1.3835 | 0.002 | yes |
| **10** | **1.0909** | 1.0276 | **1.1117** | 1.1762 | **0.116** | **no** |
| 15 | 1.0407 | 0.9641 | 1.0316 | 1.0764 | 0.034 | yes |
| 20 | 1.0024 | 0.9140 | 0.9780 | 1.0286 | 0.012 | yes |
| 25 | 0.9205 | 0.8779 | 0.9316 | 0.9866 | 0.110 | no |
| 50 | 0.7978 | 0.7586 | 0.7987 | 0.8454 | 0.056 | no |
| 100 | 0.6519 | 0.6271 | 0.6534 | 0.6764 | 0.064 | no |
| 184 | 0.5018 | 0.4948 | 0.5131 | 0.5337 | 0.266 | no |

**THE LADDER IS JAGGED, AND THE JAGGEDNESS IS THE POINT.** Five of eleven ranks clear, six do not,
and they alternate. The real curve sits above the noise **median** at every single rank while
crossing the noise **p95** back and forth. That is the signature of a genuine but small shift being
tested with a very noisy instrument: **a single order statistic is one number, and comparing one
number to a null distribution has almost no power.**

**This is exactly why one primary statistic was named in advance.** Rank 5 comes back at p = 0.002
and rank 20 at p = 0.012. Quoting either as the result — "noise reaches this only 0.2% of the
time" — would be the cherry-pick this project has documented itself making before. The registered
rank is 10 and rank 10 fails. **Nobody may quote rank 5.**

---

## THE THREE FINDINGS THAT OUTLIVE THE VERDICT

### 1. The book is distinguishable AS A GROUP; no individual name's position is.

| statistic | real | noise p95 | empirical p |
|---|---|---|---|
| **top-decile MEAN composite** | **0.72383** | 0.71243 | **0.008** (4 of 500) |
| composite at rank 10 | 1.0909 | 1.1117 | 0.116 |

The top-decile mean averages 184 names and is therefore a far less noisy statistic than any single
rank. It clears comfortably. **Stated as a pre-registered SECONDARY (PREREG §6), carrying no
verdict** — §7 names rank 10 as the statistic the verdict rests on, and promoting the aggregate now
because it is the flattering one would be selecting the statistic on the results.

**The defensible product sentence, and it is the one to use:** *"The top decile as a group is
better than a chance-assembled book. Where an individual name sits inside that decile is not
distinguishable from chance."*

### 2. THE COMPOSITE HAS NO EXCESS CROSS-THEME AGREEMENT — and the expectation was wrong in the way the pre-registration flagged as the risk.

Real composite sd **0.384500** against a noise median of **0.386541** — **empirical p 0.634**, i.e.
the real spread sits in the middle of the null and, if anything, slightly *below* it. **Destroying
all cross-theme agreement does not narrow the composite. It very slightly widens it.**

So the seven active themes do not co-occur in a name more than chance; on this cross-section they
co-occur marginally *less*. The high composite of a top name is not "many themes agreeing" — it is
one or two themes far out, averaged over the rest.

**PREREG §8 recorded the expectation DISTINGUISHABLE at 70/30, and it was WRONG.** It also recorded
the exact risk that killed it: *"if the active seven are close to independent, the real book will
look no more extreme than noise; if their net correlation is negative, it could look less
extreme."* The second branch is what happened. That is the project's continuing tally — writing the
expectation down first remains worth doing precisely because it keeps being wrong.

### 3. THE TOP OF THE BOOK IS THINNER ON DATA THAN CHANCE — and this one is significant.

Present weight = the share of a name's bucket weight actually scored on it, i.e. `_branch`'s
renormalization denominator. A thinly covered name's composite is an average over fewer themes and
is therefore **noisier**, which gives it better odds of landing at an extreme.

| | present weight |
|---|---|
| whole universe | **0.96324** |
| noise top decile | 0.95730 (p50) |
| **real top decile** | **0.94798** |

Two separate things are true here and they must not be merged:

* **The tilt is mechanical and exists in noise too** — even a chance book's top decile (0.95730) is
  thinner than its universe (0.96324). That is the renormalization, not the signal.
* **The real book has MORE of it than chance does: only 9 of 500 noise draws are this thin or
  thinner, empirical p 0.018.**

**Product consequence:** a name can rank highly partly *because it is missing a theme*. This is the
clearest actionable output of the item and it is not a statistical subtlety — it is a scoring rule
that rewards absent data with extra variance.

### 4. Composition is essentially what chance produces.

Share of the top decile's total absolute push, real vs noise median: `institutional` .187/.181,
`value` .177/.165, `momentum` .161/.152, `quality` .140/.156, `size` .139/.144, `insider`
.106/.121, `capital_discipline` .098/.087, `growth` .096/.130. **Every theme within 0.034 of its
noise share.** The "why this name" panel's theme mix at the top of the book is close to what the
weights alone would produce on noise, so the *mix* carries little information beyond the weights.
(`low_risk` and `sentiment` are 0.000 in both — they carry weight 0.0 and do not participate.)

---

## ROBUSTNESS — all 69 dates

*(filled in below on completion of the 69-date arm)*

---

## PLAIN SENTENCES FOR THE PRODUCT

Shipped in the artifact's `sentences` block, one per rank band. The two that matter:

* **"The top decile as a group scores better than a book assembled by chance (this happens in under
  1% of chance universes). Where a name sits within that decile is not distinguishable from
  chance."**
* **"A high score can partly reflect missing data: names near the top are scored on less
  information than the average name, more so than chance would produce."**

**What may NOT be said any more, on this evidence:** that a specific rank, or the gap between #3 and
#12, means anything. It does not, at n = 1,842.

---

## WHAT THIS DOES NOT SAY

* **It does not touch the edge research.** X7's calibrated research bars, the long-short HAC t of
  2.620 against its 2.28 floor, R1's factor alpha — none of that is scored here. This measures the
  cross-sectional **score**, not forward returns. A composite can rank names in an order that is
  indistinguishable from chance *at a given rank* and still have a real top-minus-bottom return
  spread; those are different objects and this item settles only the first.
* **It is not a statement that the hot list is worthless.** Finding 1 is the opposite. The claim
  that dies is the *precision* of the ranking, not the existence of the edge.
* **It does not license changing any weight.** Nothing was tuned, adopted, or selected here.

## LIMITATION, DECLARED IN THE PRE-REGISTRATION RATHER THAN DISCOVERED AFTER

The panel carries no `value_est` / `value_spec` / `op_margin`, so `attribution.decompose` takes its
documented **hard-bucket branch** rather than the soft blend (`attribution.py:90-101`). The deployed
weights, within-bucket standardization and present-weight renormalization **are** the live ones —
i.e. the structure of the score is the live structure. Not exercised: the soft blend of the two
`value` branches by `p_established`. **Real and null are scored by the identical call**, so this is
a caveat on transfer to the live book, not on the internal comparison. It is stated by the artifact
itself in a `limitation` field, so it cannot travel without its caveat.

Second limit: the universe is the corrected 69-date **panel**, not a live scan. A several-hundred
name live fetch throttles the Yahoo quota and silently returns empty company data, which would have
made every bound pass vacuously. The panel's theme columns are built by the same `build_frame` the
live path uses.

## TRIAL COST

**ZERO.** A calibration searches no hypothesis space, fits nothing and adopts nothing — session-10
precedent ("a calibration searches nothing, equity `N` stays 121"). **Equity `N` stays 130.** No
`RESEARCH_LOG.md` row is owed and no weight, threshold or shipped behaviour changes.

Measured today: `research_log.detail()` reads **equity 130**, options 192, infra 4, total 326.
**CLAUDE.md still says 129 — one session stale** (session 14 moved it). Not edited here; flagged
for whoever owns that file.

## BUGS FOUND

* **`VALQUO_EXTENSIONS.md` was untracked** and existed only on this machine — the register for five
  adopted work items, unreadable by any other checkout, with the file's own rule saying the first
  agent to execute a section commits it. Fixed here (`251c989`). Same class as the records cleanup
  landed at `d1f4b04`; that this recurred one day later suggests new governing documents are
  routinely created untracked.
* **CLAUDE.md's equity `N` is stale at 129** (measured 130). Small, but `N` feeds `_trials_haircut`
  and the Deflated Sharpe, and this file is the thing agents quote from. Not my lane to edit.
* **`tests/test_guards.py` reports an XFAIL** — "a guard was fed the bug it exists to catch and did
  NOT complain". Exit code 0, so the gate stays green. Pre-existing, not touched, and the suite
  itself says it is already routed to `HANDOFF_optionsbot.md`. Recorded here per RUN_RULES A3
  because I saw it, not because I own it.

## WHAT I DID NOT DO

* **Did not change any weight, threshold, or shipped behaviour.** V3 is scoped new-files-only plus
  reads, and nothing under `valuation/` was edited.
* **Did not weaken the product's confidence language in the app.** The verdict says it must weaken;
  the templates are the app-fixer's lane (`valuation/web/**`). The sentences above are handed over
  ready to use. **This is an open dependency, not a finished item.**
* **Did not run the soft-bucket branch.** See LIMITATION — it needs a cross-section carrying
  `value_est` / `value_spec` / `op_margin`, which no artifact on this disk has.
* **Did not investigate the thin-coverage tilt's cause beyond the mechanism.** That renormalization
  amplifies variance for thin names is arithmetic; *why the real book has more of that tilt than
  noise* is not answered here and is a genuine open question.

## RECOMMENDED NEXT STEP

**Take finding 3 seriously before finding 1.** The thin-coverage tilt (p 0.018) is the only result
here that points at a fixable defect rather than at a limit of what a cross-section can support. A
minimum-coverage floor for the served list, or a variance penalty on thinly scored names, is a
cheap, pre-registerable test with a real mechanism behind it — and unlike the rank-precision
question it is not blocked by the size of the universe.

The rank-precision finding is a **communication** change, not a research one, and it belongs to the
app-fixer lane.
