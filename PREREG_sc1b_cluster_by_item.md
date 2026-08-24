# PREREG_sc1b_cluster_by_item.md — SC-1b: sharpening SC-1's CANNOT-TELL
## Cluster the prior-calibration gap by ITEM instead of by FILE, and accept whatever that resolves

**Approved by Don, queued behind the season's equity slate. Domain INFRA, 1 trial. Committed
ALONE, markdown only, zero `.py`, a strict git ancestor of every measurement commit; the trial
is booked in its own commit BEFORE the runner exists. Infra `N` gates no published claim — and
the counter is still the counter.**

---

## §0. WHAT THIS IS, AND THE ONE THING IT CHANGES

`SC-1` returned **CANNOT-TELL** and named its own successor, in writing, **before** anyone could
choose it on an outcome:

> *"Clustering by ITEM rather than by file would give many more units, and it was NOT done —
> changing the clustering key after seeing the interval is choosing the design on the outcome.
> It is named here as the obvious successor instead, and it needs its own register."*

**SC-1b changes EXACTLY ONE THING: the clustering key.** The extraction, the pair set, the
traceability rule, the exclusions, the point estimate, the bootstrap draw count, the seed, the
bars and the verdict grammar are `SC-1`'s and are reused **verbatim** — `MB1SEL`'s discipline,
which matters more than usual here because `SC-1`'s numbers are already published and any bar
re-chosen now would be re-chosen with its answer visible.

That the successor was named in advance is what licenses running it at all. **It is not a
re-run of `SC-1` and it does not re-open, re-score or re-litigate any individual trial.**

---

## §1. A STRUCTURAL BOUND ON THE OUTCOME, DERIVED BEFORE RUNNING FROM `SC-1`'s OWN BANKED FIGURES

This is the most useful thing this register can say, and it must be said first because it
changes what a reader should expect the item to deliver.

**The point estimate cannot move.** `gap = mean(p) − mean(y)` over a fixed pair set is
**−0.0500** and is independent of how the pairs are grouped. Clustering changes the INTERVAL
and nothing else.

**And the interval cannot exclude zero.** `SC-1` banked its naive (iid) bootstrap CI as
**[−0.16860, +0.06977]** — half-width **0.11919**, comfortably containing zero — and `C4`
requires the cluster bootstrap to be **no narrower** than the naive one. A wider interval around
the same point estimate still contains zero.

> **THEREFORE `OVERCONFIDENT-OPTIMISTIC` AND `OVERCONFIDENT-PESSIMISTIC` ARE BOTH UNREACHABLE,
> AND SC-1b IS A TEST OF RESOLUTION, NOT OF DIRECTION.** The only two attainable verdicts are
> **CALIBRATED-IN-THE-LARGE** and **CANNOT-TELL**, and the whole question is whether the
> item-clustered half-width falls at or under **0.15**.

**THE ANSWER IS BRACKETED IN ADVANCE, AND THE BAR SITS INSIDE THE BRACKET.** Item clusters are
nested inside file clusters, so the item-clustered half-width is expected to land between the
naive floor of **0.11919** and `SC-1`'s file-clustered **0.19167**. **0.15 sits inside that
bracket**, at 38% of its width. So this register is a genuine coin-flip on resolution and is
registered as one.

**IF THAT BOUND FAILS IT IS A FINDING, NOT A LICENCE.** If the item-clustered interval comes
back NARROWER than the naive one, `C4` has failed at this key, the bound above does not hold,
and **the interval is reported as suspect rather than read as a sharper answer** (§4 G3).

---

## §2. THE OBJECT: WHAT AN "ITEM" IS, FIXED EXACTLY

A pair's cluster is **`(source_file, the nearest preceding markdown heading of level 1 or 2)`**.

The write-ups are organised one item per top-level section — `## MB18 — ...`,
`# SC-1 + SC-2 — ...` — with `###` reserved for subsections such as *"Expectations, scored"*.
Keying on level 1 or 2 therefore names the ITEM; keying on the nearest heading of **any** level
would collide, because two different items' expectation tables both sit under a `###` heading
with the same text. The file is kept in the key so identically-titled sections in different
handoffs cannot merge.

**THE FAILURE DIRECTION IS DECLARED, AND IT IS THE SAFE ONE.** If a write-up puts an item under
a `###` heading, this rule lumps it with its neighbours — **fewer, larger clusters, a wider
interval, and a push toward CANNOT-TELL.** The heuristic can therefore cost this register its
verdict and cannot manufacture one. The realised cluster count ships in the artifact.

---

## §3. STATISTIC, BARS, GRAMMAR — `SC-1`'s, REUSED VERBATIM AND NOT RE-CHOSEN

`gap = mean(p) − mean(y)` over the OUTCOME pairs, cluster bootstrap CI95, `BOOT` and `SEED`
unchanged from `SC-1`.

* **OVERCONFIDENT-OPTIMISTIC** if `gap > 0` and CI95 excludes 0.
* **OVERCONFIDENT-PESSIMISTIC** if `gap < 0` and CI95 excludes 0.
* **CALIBRATED-IN-THE-LARGE** if CI95 includes 0 **and** its half-width **≤ 0.15**.
* **CANNOT-TELL** otherwise — *a wide interval containing zero is never "calibrated"*.

Per §1 the first two are unreachable; they are restated anyway because the grammar is `SC-1`'s
and editing it here would be exactly the re-choosing this register exists to avoid.

**THE THREE-RUNG LADDER SHIPS TOGETHER** — naive, item-clustered, file-clustered — so a reader
sees the bracket rather than one number. Only the **item-clustered** rung carries the verdict.

---

## §4. GATES — computed and read in their own pass; `--arms` refuses without them

**G1 — IDENTITY, and it is the gate that makes this the same object.** The re-run must reproduce
`SC-1`'s banked artifact **EXACTLY** on the pair count, the gap, the naive CI, the file-clustered
CI, the Brier, both skill figures and the Murphy decomposition. Anything that moves means the
extraction changed, and then the comparison is between two different studies rather than between
two clusterings of one. **Tolerance 0.0.**

**G2 — `SC-1`'s pre-outcome kill, INHERITED.** Fewer than **25** scoreable OUTCOME pairs, or
double-entry disagreement above **15%**, and the calibration leg is CANNOT-TELL BY CONSTRUCTION
and the trial is still charged. Re-derived here rather than assumed from `SC-1`'s 43 / 11.7%.

**G3 — `C4` AT THE NEW KEY.** The item-clustered interval must be **no narrower** than the naive
one. If it is narrower, §1's bound is void, the interval is reported **SUSPECT**, and the verdict
is **CANNOT-TELL** regardless of its half-width — a bootstrap that tightens when you add
structure is not evidence, it is a symptom.

**G4 — THE SUCCESSOR MUST ACTUALLY DIFFER.** The item-cluster count must exceed `SC-1`'s **3**.
If it does not, the successor did nothing and the item is **VOID**, not a confirmation.

---

## §5. POWER — BOTH `MB22` VOCABULARIES, AND `SC-1`'s OWN D1 DEFECT REPAIRED

`SC-1`'s acceptance block declared defect **D1** before running: its §5 formed the MDE from
**Brier** variance where the gap needs **`Var(p − y)`**, making those figures optimistic, and it
directed readers to the empirical line instead (detection threshold **0.1285** at 50% power,
**0.1824** at 80%; power against a 0.10 gap **32.9%**).

**SC-1b computes it correctly rather than quoting around it**: `se = sd(p − y) / sqrt(n)`, and

* **detection threshold (50% power)** = `crit × se`;
* **MDE at 80% power** = `(crit + 0.84) × se`, `MB22`'s vocabulary, **1.42× larger at crit 2**.

Both are printed, each labelled, at `crit = 1.96`, on the same pairs. The **cluster-adjusted**
versions are reported beside them using the realised design effect, because the iid figure is
not the resolution this design actually has. **A CANNOT-TELL is quoted with these or not at all**
(`V6`/`S19`/`MB16`).

---

## §6. VOID CONDITIONS

1. Changing the clustering key again after seeing this interval — the exact error `SC-1`
   refused to commit, one level up.
2. Re-extracting, re-classifying, re-adjudicating or adding a pair. The pair set is `SC-1`'s.
3. Changing `0.15`, `BOOT`, `SEED`, the traceability rule or the verdict grammar.
4. Building `SC-1` §4.1(b)'s stability set, the shrinkage arm, or π₀ / local FDR — each is a
   separate question and charges its own trial.
5. Reading a **CALIBRATED-IN-THE-LARGE** verdict as validating any individual prior. `SC-1` §231
   already says it: calibration-in-the-large is an aggregate property, *"exactly as an index
   fund's return says nothing about any one holding"*.
6. Re-opening, re-scoring or re-litigating any individual trial on the strength of this.

---

## §7. PRIOR — AND YES, THE RECURSION IS NOTICED

**A study of whether this record's stated priors are any good, opening with a stated prior,
which will be scored afterwards exactly like the others and will itself become a row in the next
such study.** The regress is real and it is not vicious: each round is scored by the same rule,
and the alternative — declining to state a prior *here* of all places — would be the one
position the item could not defend.

**Prior: 55/45 on CALIBRATED-IN-THE-LARGE.** The arithmetic behind the lean, so it can be
checked rather than taken: the bracket is [0.11919, 0.19167] and the bar 0.15 sits at 38% of its
width, so a mid-bracket landing is CANNOT-TELL. Against that, a 3-cluster bootstrap is
pathologically lumpy — it resamples three things — and most of the distance back to the naive
floor is usually recovered by the time there are ten or more clusters. The two considerations
nearly cancel; the lean is small and deliberately so.

**Expectations, scored later:**

1. Verdict **CALIBRATED-IN-THE-LARGE** — **55/45**.
2. The CI95 contains zero, i.e. §1's structural bound holds — **90/10**.
3. The item-cluster count lands in **[8, 20]** inclusive — **60/40**.
4. `G3` holds: the item-clustered interval is no narrower than the naive one — **70/30**.
5. `G1`'s identity gate reproduces `SC-1` exactly — **95/5**.
6. The half-width falls by at least a third from `SC-1`'s 0.19167, i.e. to **≤ 0.1278** —
   **40/60**. (It cannot fall below the naive 0.11919, so this asks for a landing in the bottom
   fifth of the bracket.)
7. At least one number contradicts this list — **60/40** (`SC-1`'s own #6, reused verbatim).

---

## §8. WHAT THIS DOES NOT DO

No market data is opened — pinned by an AST test, as `SC-1`'s C3 pinned it. No equity or options
counter moves. No `/research` paragraph ships. No individual prior, item or verdict is
re-scored. **And a CALIBRATED verdict would say only that the record's priors are level-correct
ON AVERAGE at this resolution — it would not say any one of them was right, and `SC-1`'s
separate finding that they are INFORMATIVE (Brier skill +0.266) is a different statement that
this register neither strengthens nor weakens.**
