# HANDOFF — `INSIDER-CLUSTER` — clustered opportunistic insider buying, tested in shares

**2026-10-13, r1 lane.** Don's queued research (`DECISIONS.md` 2026-10-13, "RESEARCH QUEUED").
**FOUR EQUITY TRIALS**, equity `N` **297 → 301**, hurdle **3.378493825582304**. **ADOPTS NOTHING**
— adoption is Don's and is a vintage event, and under `DECISIONS.md` 2026-10-06 a candidate goes to
him **quoted at half its backtested size** (McLean-Pontiff).

**ORDERING, ALL GIT-PROVABLE AND ASSERTED BY TEST.** `PREREG_insider_cluster.md` committed **ALONE
at `fd87870`** (markdown only, zero `.py`, 316 lines); **Amendment 1 ALONE at `826d0b5`**; trials
booked at **`4a34a00` BEFORE any runner existed**; the kill pass run and read in **its own
invocation** before the arm, which **REFUSES** without its artifact (`O10`'s process defect).

---

## 1. VERDICT

| cell | verdict | market-adjusted, raw | null-relative EXCESS | *t* (date / ticker) | its own MDE80 |
|---|---|---|---|---|---|
| **full universe × `h`=63** | **CLEARS all five clauses** | **+2.0926pp** | **+1.8077pp** | **5.009 / 4.888** | 1.217pp |
| full universe × `h`=126 | **NULL** (A2 fails early) | +3.4492pp | +2.7454pp | 4.939 / 4.308 | 2.275pp |
| tier `cap ≥ $10B` × 63 | **UNDERPOWERED-BY-CONSTRUCTION** | +3.0138pp | +3.0217pp | 2.584 / 2.514 | **3.407pp** |
| tier `cap ≥ $10B` × 126 | **UNDERPOWERED-BY-CONSTRUCTION** | +1.1967pp | +1.3622pp | 0.684 / 0.624 | 5.450pp |

**In one line: a cluster of opportunistic insider open-market purchases is followed by about
+1.8pp of market-adjusted return over the next quarter on the full corrected universe, which
clears every pre-committed clause — and whether that is usable in the $10B tier the Index actually
trades is NOT ESTABLISHED IN EITHER DIRECTION, because that tier carries 146 events and the design
needed 2,430.**

**SO THE ARM DOES NOT ADVANCE TO STAGE 2 AND THE CHECK QUADRANT IS NOT SPENT.** Charter Stage 1b:
the tier reading governs advancement, and a population that cannot be assessed cannot govern. That
was **declared in the register before the run**, which is why this is the cheapest honest outcome
rather than a disappointment.

---

## 2. THE OWN-NORMAL LEG IS UNUSABLE, AND THE RULE THAT CAUGHT IT IS THE REGISTER'S OWN

The register requires **both** return definitions and forbids quoting one alone (`DC-1` measured
them disagreeing). Here they disagree by **5.5×** and the reason is mechanical:

| cell | own-normal raw | market-adjusted raw |
|---|---|---|
| full × 63 | **+11.4638pp** | +2.0926pp |
| full × 126 | **+20.9313pp** | +3.4492pp |
| tier × 126 | **+25.6503pp** | +1.1967pp |

`ar_own = fwd − h × mu`, where `mu` is the mean daily return over the same strictly prior
60-session window. **Insiders buy after declines**, so `mu` is negative on this event set and
`− h × mu` is a large POSITIVE addition — and it scales with `h`, which is why the distortion
roughly doubles from 63 to 126 sessions. An abnormal return of 10–21pp over one or two quarters is
not a credible insider effect; it is a benchmark extrapolating a negative trailing drift forward
for a quarter.

**The own-normal leg's own permutation null confirms it rather than resting on the argument:** its
null MEAN is **+1.17pp to +4.51pp**, where the market leg's is +0.28pp to +0.70pp. A null centred
far from zero is a benchmark with a bias, measured.

**CONSEQUENCE: every figure quoted in this handoff is the MARKET-ADJUSTED leg**, and the
own-normal leg is reported as a diagnostic that **carries no verdict**. Had the register permitted
one leg, and had that leg been the own-normal one, this item would have reported an
11-to-21-percentage-point insider effect.

---

## 3. THE RAW MARKET-ADJUSTED MEAN IS PARTLY A SIZE TILT, AND THE NULL IS WHAT PRICES IT

**Measured on the banked pool: the AVERAGE name's 63-session market-adjusted return is +3.41pp in
2009–2014 and −1.23pp in 2015–2019.** An equal-weighted event set scored against a **cap-weighted**
market carries a size/weighting tilt whose sign flips between the halves — which is `UNIVERSE-BIAS`
(the wider pool reverses, +7.24pp → −4.14pp) and `TIERED-POOL` (the gain is a size bet) on a third
instrument.

So the within-date permutation null is not a formality here; it is the correction. **The clean
number is the excess over the null mean, and it is +1.8077pp at `h` = 63.**

**AND NULL-RELATIVE, THE LATE HALF IS STRONGER AT BOTH HORIZONS — THE OPPOSITE OF THE RAW
READING.**

| cell | raw early / late | **null-relative early / late** |
|---|---|---|
| full × 63 | +2.91 / +1.09 | **+1.33 / +2.23** |
| full × 126 | +4.59 / +1.93 | **+1.71 / +4.27** |

Read raw, this looks like a GFC-recovery effect fading. Read against each half's own null, it is
**stronger in 2015–2019**. **This correction is only visible because the per-event rows and the
pool were banked** (`RUN_RULES` rule 9), and it was needed within the hour: the late half's null
p95 came back at **0.0923pp** against the full sample's 0.8589pp, which is backwards for a smaller
sample, and the first thing checked was whether the null was broken.

**IT IS NOT BROKEN — THAT WAS ESTABLISHED, NOT ASSUMED.** A synthetic control confirms fewer
events WIDEN this null (p95 0.0050 → 0.0085 on 4,000 → 1,800 events), and the per-date
cross-sectional dispersion is near-identical across halves (**0.2450 early against 0.2617 late,
ratio 0.94×**). What differs is the pool's MEAN, measured above. The bar is low in the late half
because the typical name was *losing* to the cap-weighted market then.

---

## 4. WHY THE TIER'S APPARENT PASS IS STILL REPORTED AS UNDERPOWERED

**The tier × 63 cell clears all four of A1–A4 on its own numbers: +3.0138pp at *t* 2.584 / 2.514.**
It is reported **UNDERPOWERED-BY-CONSTRUCTION** anyway, for two reasons and neither is a
preference:

1. **The register declared it before the run**, from the event count alone: 146 events against
   2,430 required, power **7.4%**. Re-labelling a cell because the result came out favourable is
   precisely what `W-28`'s rule forbids and what `MA28`'s voids an item for.
2. **It is now also MEASURED to be unresolvable: the point estimate is 0.89× its own 80%-power
   MDE** (3.0217pp against 3.407pp). A cell with 7.4% power that nonetheless clears a *t* bar is
   in the regime where a passing estimate is **selected on significance and biased upward** — so
   the magnitude cannot be trusted even if the sign is right. `V6` and `S19`'s rule: quote the MDE
   with the verdict or do not quote the verdict.

**The honest statement is therefore not "it works in the tier" and not "it fails in the tier" —
it is that 146 events cannot tell.** What would change that is more events in the tier, which only
elapsed time supplies.

---

## 5. THE FREE KILLS — all three stopping kills pass, and one does not clear comfortably

* **K2 — the dip overlap: 0.2048 against a bar of 0.25.** Does **not** fire, and does **not** clear
  comfortably: **roughly one cluster in five is a post-dip event** (a `DIP-CALL` `z ≤ −2.5` within
  5 sessions). So this is **not** `V6-B`'s dip × insider arm, and it is **not disjoint from it
  either** — a caveat that travels with the positive result rather than being filed away.
* **K3 — the costume check: the worst theme is `insider` ITSELF at 0.1699 against 0.60.** This is
  what turns *"a null here would be a different null"* from an assertion into a measurement: the
  event flag is not the theme in disguise.
* **K4 — look-ahead: zero events dated before their own window**, with a **positive control**
  detecting a planted ROUTINE pattern and a **negative control** leaving a planted opportunistic
  one alone. A guard that refused everything would pass the first and fail the second.
* **The tier's PER-DATE NAME COUNT clears Stage 1b's floor on every one of 44 dates** — min 106,
  median 256, max 342, zero below `CONTRACT_MIN_POSITIONS` = 50. **So the tier's failure is purely
  an EVENT-count failure: it is large enough to trade and the signal fires too rarely inside it.**

---

## 6. BENJAMINI-HOCHBERG, and the bars

`k = 2` fixed in the register and never shrunk. `full_universe_h63` *p* **5.1e-07** against a
threshold of 0.05 and `full_universe_h126` *p* **8.3e-06** against 0.10 — both survive. The two
tier cells are **excluded with the exclusion declared in the register**, because K1 fires on them
before any outcome and they carry no *p* to correct (charter Stage 1a's rule).

**Every critical value is LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`): no X7 or `CORRECTED-FLOORS`
figure transfers to an event-time mean on this universe, and none is quoted. **The HLZ hurdle is
reported beside and NOT gated — 3.378493825582304 at equity `N` = 301, derived not quoted** — for
`R4`'s measured reason: HLZ prices the best of `N` draws and this construction is the
literature's, not one selected out of this record.

---

## 7. WHAT WAS NEW, AND WHAT THE THREE PRIOR NULLS DO AND DO NOT SAY

**NOT NEW, and all three are this project's own:** the `insider` theme is weak (IC *t* **−0.24**);
re-filtering its rows cannot move the blend (`MB20` moved the score on **54.83%** of scored cells
at a composite rank correlation of **0.9774** and adopted nothing); and dip × insider buying was
**NULL** (`V6-B` arm 3, late half **+0.011pp**).

**NEW, and the result does not contradict any of them.** None tested a **standalone event signal**:
`MB20` re-scored a theme at 1/7 weight, `V6-B` conditioned on a dip first (K2 bounds that overlap
at 20.5%), and the theme's IC is a cross-sectional rank statistic on a 69-date quarterly panel —
which `SEARCH_DOCTRINE` §1.4 measures as the **weakest space this project has** (80%-power MDE
0.4274–0.5071 SD, *"a merely good new signal is invisible there BY CONSTRUCTION"*). This is event
time on the daily series, where the MDE is **1.217pp** on 4,072 events. **Three nulls on a weak
instrument and one pass on a strong one are consistent, and K3 is the measurement that says so.**

---

## 8. BUGS FOUND

* **MINE, before any outcome: the cluster cooldown did not implement the register's own rule 5.**
  It suppressed a repeat only on the same day, so the next filing re-fired the same cluster —
  `ISCA` returned **29 insiders on 2008-01-04, 01-07 AND 01-08**, one cluster counted ~twenty
  times. Fixed to a full-window cooldown; it **halved the event set** (8,478 → 4,386), i.e. it
  **reduced power**, the direction that makes the design harder. Pinned by a regression test, with
  a companion test proving a genuine second cluster five months later still fires (a rule that
  suppresses everything is not a rule).
* **MINE: `cluster_events` RAISED on an empty result** instead of returning an empty frame —
  `pd.DataFrame([]).sort_values([...])` has no columns to sort on. Latent on real data (there are
  always events), and **a defect neutralised by a coincidence in the data is not handled**; found
  by the three construction tests that exercise the no-cluster cases.
* **MINE: a nullable-boolean refusal, and pandas was right to refuse.** Under the `string` dtype a
  missing `transactioncode` is `pd.NA`, so `code == "P"` is a nullable boolean and
  `.to_numpy(dtype=bool)` raises. That is the **blank-code counter** family one level up — the
  `MA-final-batch` check that read **0** blank codes on a column holding 1,544,490 because `NA`
  compares False and nothing raised. The fill is now the register's SKIP rule written out
  explicitly, and the raising behaviour is pinned by test so nobody "simplifies" it back.
* **MINE, in a test, for the ninth time in this project: a substring ban fired against the correct
  tree.** `assertNotIn("insiders.csv", src)` failed because the module's docstring explains at
  length why `data/backtest/insiders.csv` is NOT used — prose documenting the rule, containing
  exactly what the rule forbids. Reads the AST now (no string CONSTANT may name that file), with a
  positive control proving the narrowed rule still bites.
* **MINE: a guard broken by the line width of the document it reads.** A register assertion looked
  for a phrase that spans a newline in a 100-column hard-wrapped file. Whitespace-normalised now.
* **REPORTED, OUTSIDE THIS LANE** (`RUN_RULES` rule 3): **`scripts/dipcall_arm.abnormal`'s
  own-normal leg is structurally biased on any event set selected after a price decline**, for the
  reason in §2. It is correct as specified and `DIP-CALL` used it on a dip event set where the same
  bias applies — and that register's conclusions were nulls, so the direction runs toward
  *understating* their nulls rather than manufacturing a finding. **Not changed here**, because it
  is `DIP-CALL`'s instrument and editing it would move landed figures; the recommendation is that
  any future event register selected on past returns treat the own-normal leg as a diagnostic only.

---

## 9. NOT DONE, named so it is not mistaken for done

* **No Stage 2 and no check-quadrant read.** The cell is counted for feasibility (**2,669** strict
  events) and **not looked at**. The charter gives one read per construction and this item does not
  spend it.
* **Stage 3 is FORECLOSED BY CONSTRUCTION, declared in the register and now worse than declared:**
  the strict definition leaves **31** events before 2009, because a pair needs two prior years of
  observable trading and the file's early coverage cannot supply it. **A successor quoting those 31
  events as an out-of-sample check is quoting noise.**
* **`k = 3` is not scored, the broad (non-strict) opportunistic label is not scored, and the
  `h ∈ {5, 21}` sensitivity horizons are not scored.** All three are declared sensitivities
  carrying no verdict; running them later is permitted and promoting any of them to primary is a
  void condition. **A hazard was closed on the way past**: a sensitivity run would have overwritten
  the co-primary artifact under the verdict's own name, so the runner now writes sensitivities to
  `INSIDER_CLUSTER_ARM_sensitivity.json` and stamps every cell `SENSITIVITY -- NO VERDICT`.
* **The own-normal leg carries no verdict** (§2), and **no per-trade or portfolio book was
  simulated** — this is an event-time mean, not a book. The charter's question 2 (*is the book
  worth holding?*) is **unanswered**, and §4b says a register answering only question 1 has found a
  signal and not a product.
* **No sell-side arm, no net-buying construction, no size-weighted cluster, no officer/director
  split, no `transactionshares` weighting.** Each is a new hypothesis needing its own register.
* **`MB20`, `V6-B` and the `insider` theme's weight are untouched**, and nothing here is adopted or
  shipped to any public surface.
