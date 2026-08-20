# PREREG — EVOWN: buying calls into earnings as its own strategy family

**Status: BLIND. Committed ALONE, markdown only, zero `.py`, as a strict git ancestor of every
commit that scores an outcome.** The coverage census ran first, in its own pass, and **touched no
return** — its artifacts carry chain/menu counts and nothing else. No bar below was chosen before
that census; several were chosen *because* of it.

**A NEW DESIGN, NOT A RE-RUN OF `O17C4`.** Its verdict rests solely on a bar of its own that the
record already diagnoses as broken (c3's trades-per-year axis, unpassable by construction for a
subset of the book it is drawn from). Nothing from that bar is reused here.

---

## 0. What the record has already established, and what it has not

* **`O17C4`** measured the effect on **random-entry** trades: a call spanning the next
  announcement earned **+10.30%** against **+5.50%**, **+4.79pp**, positive in both halves, sign
  test **z +2.054, p 0.040** — and measured that **the ALERT SUBTRACTS VALUE inside it** (alert
  spanning +8.42% *loses* to random spanning +10.30%, z −4.4726, p 7.7e-06).
* **`MB3`** ran the sizing arithmetic on `O11`'s own simulator: required equity **$5,000**, and at
  $50k/cap-10 the alert book's earnings-spanning half ends at **$130,855** against **$24,391** for
  the non-spanning half — so **`O11`'s ruin was the non-spanning half.**
* **What nobody has done** is measure the strategy *as a strategy*: an entry rule that does not
  mention the alert, on its own universe, with survivability as a required leg rather than an
  afterthought.

---

## 1. THE CENSUS RESULT THAT CHANGES THE DESIGN, and it is the most important thing here

**On this entry rule, "spanning" is VACUOUS — it selects nothing.** Measured across all three
candidate offsets, the count of contracts whose expiry spans the announcement equals the count of
contracts the engine's rule produced at all, **exactly**:

| offset K (trading days) | events | chain on entry date | engine contract | **spans** |
|---|---|---|---|---|
| 5 | 6,361 | 6,278 (98.7%) | 4,769 (75.0%) | **4,769 (75.0%)** |
| 10 | 6,361 | 6,269 (98.6%) | 4,512 (70.9%) | **4,512 (70.9%)** |
| 15 | 6,361 | 6,244 (98.2%) | 4,607 (72.4%) | **4,607 (72.4%)** |

It is a structural certainty rather than a coincidence: the engine's own band is **45–75 DTE** and
K ≤ 15 trading days is ≤ ~21 calendar days, so the contract **cannot** expire before the
announcement. **`O17C4`'s spanning/not-spanning partition existed only because ALERT dates fall
where they fall relative to earnings.** Anchor the entry to the announcement and the partition
disappears.

**So the arm is NOT "spanning vs not-spanning".** It is the event-ownership book against a
**DTE-matched random-entry control**, and the register says so before any return is read. The
strategy's honest name is *"buy the engine's standard 45–75 DTE ~35-delta call K trading days
before an earnings announcement"* — the word "spanning" adds nothing to it.

## 1a. The universe this strategy can honestly claim

| universe | names | zero-earnings **DROPPED** | scoreable | earnings events |
|---|---|---|---|---|
| alert book | 186 | **29** | **157** | 13,484 (all history) |
| pinned freeze ∩ bars | 502 | **67** | **435** | 33,735 (all history) |

* **The 157-name cap is an artefact of the ALERT BOOK, not of the strategy.** It reproduces
  `O17C4`'s 157 exactly, which is the instrument check. **435 names are available** on the pinned
  freeze — 2.8× — and the binding constraint is the **bars cache at 502 names** (`MA25`), because
  a strike needs an underlying price. Options data is not the limit.
* **THE ARM RUNS ON THE 157**, so it is directly comparable to `O17C4` and `MB3`. **The extension
  to 435 is NOT measured here and is named as not-done** — event-level fillability was censused on
  the 157 only, and claiming the wider universe without measuring it would be the scope error this
  record has paid for repeatedly.
* **6,361 of the 13,484 events fall in the 2016–2025 covered window** (157 names × ~40 quarters);
  the rest predate the freeze.
* **FAIL CLOSED:** `owns_the_event` / `refuse_within` return **None for UNKNOWN**, and those names
  are **dropped, counted and listed** — never read as "no earnings". 29 foreign private issuers
  file 20-F/6-K and carry zero Sharadar code-22 coverage; treating them as unflagged would fail
  open on a systematically non-random tenth of the book.

**K = 5 trading days, FIXED ON AVAILABILITY** (highest coverage, 75.0%) **before any return was
computed** — `MA58`'s precedent, where K was fixed on availability and the alternative carried no
verdict. K = 10 and 15 are **not** run as arms and carry no verdict.

---

## 2. THE ARMS — two, both required

**A1 — does the event-ownership book beat DTE-matched random entry?**

* **Book:** for each covered (name, announcement), enter K = 5 trading days before, on the pinned
  chains freeze, using the **shipped `pick_contract`** (imported, never re-implemented). Exit by
  the **shipped `simulate_trade`**, unmodified.
* **Control: DTE-MATCHED BY DESIGN, not checked afterwards.** `O17C4` measured tenor as a confound
  *after* the fact; here each strategy trade is matched to random-entry control trades in the
  **same name, same year, and same DTE bucket** (`O17C4`'s own quartile cuts, 51 / 58 / 66 days,
  reused verbatim rather than re-chosen). A trade with no control in its cell is **dropped and
  counted**, never matched loosely.
* **Statistic: the MEAN gap.** The **median is BANNED by measurement** — `O17C4` recorded the
  effect as *"a MEAN effect, not a MEDIAN one"* (median-vs-median **+0.40pp** against means
  separating 4.79pp) and `MB1` reproduced it. Inherited from `MB1-SEL`, **pinned by AST**: no
  median is computed anywhere in the arm path.
* **Uncertainty: paired name-year cluster bootstrap**, `R3`'s own unit (design effect **2.1837**
  against a shuffled-null p95 of 1.1898), 2,000 draws, seed 20260820, percentile CI95, the same
  keys drawn for both arms.

**A2 — SURVIVABILITY, A REQUIRED LEG AND NOT A FOOTNOTE.**

Per-trade expectancy without survivability is the exact mistake `O11` exists to prevent: a book
with **+3.27%/trade positive expectancy ended at $37,059 from $50,000** at cap 10. Run on
**`O11`'s own simulator** (`options_vrp_portfolio.simulate_book`, imported) at **both account
sizes, $50,000 and $250,000**, at **cap 10 and cap 50**.

---

## 3. BARS, DERIVED BEFORE ANY OUTCOME, NONE REUSED FROM THE BROKEN c3

**A PASS REQUIRES BOTH ARMS. Neither alone is a pass, and A1 passing while A2 fails is exactly the
result `O11` says must not be reported as a strategy.**

**A1 passes iff:** the CI95 of the mean gap **excludes zero** in the **full sample AND both
halves**, **and** the point estimate is **positive** in all three.

**A2 passes iff:** final equity **exceeds initial capital at cap 10 at BOTH $50,000 and
$250,000.** Cap 10 is `O11`'s binding cell and is where its ruin was measured; cap 50 is reported
beside it and carries no verdict.

**Verdict grammar:** **VIABLE** (both pass) / **REAL-BUT-UNSURVIVABLE** (A1 passes, A2 fails) /
**NOT-DEMONSTRATED** (A1 fails) / **UNDERPOWERED** (below the floors in §4). Ambiguous against a
pre-committed threshold is a NULL (`RUN_RULES` A6).

**Nothing from `O17C4`'s c1/c2/c3/c4 is reused.** Its trades-per-year axis compared a subset to
its own superset and its name axes re-measured the foreign-issuer hole; both are discarded, not
repaired.

---

## 4. POWER, STATED BEFORE THE RUN — `MB22`'s required-n gate

Computed with the shipped `valuation/edge/power_gate.py` (verified against external power tables
by `MB22`), against the options hurdle at the booked `N`, and printed **before** any arm is
scored:

* `power_gate.state(effect, se, n_trials=N_options)` is emitted verbatim into the artifact, so
  **both MDE vocabularies travel together** — this project's published MDEs are all `crit*se`, a
  **50%-power detection threshold**, and the 80%-power figure is larger by `(crit+z)/crit`
  (**1.42×** at crit 2). Quoting the wrong one is the failure this module exists to prevent.
* **Effect for the gate:** `O17C4`'s own **+4.79pp** on random entry, which is the only prior
  estimate of this quantity and is not chosen here.
* **Floors:** fewer than **500 matched strategy trades**, or fewer than **200 in either half**, →
  **UNDERPOWERED, never null** (`O26` / `V6-B` M2 precedent).

---

## 5. Void conditions

1. The median computed anywhere in the arm path, or used as a tie-breaker.
2. Reporting A1 as a strategy result when A2 fails.
3. K re-chosen after seeing any return, or K = 10/15 reported as an arm.
4. The 435-name universe claimed on the strength of the 157-name measurement.
5. A control matched loosely when its DTE cell is empty.
6. Any bar from `O17C4`'s c3 reused.
7. Quoting a figure without the **2016–2025 / 157-name / covered-subset** conditioning.
8. Reading any result as licensing a trade. **`O11` governs.**

---

## 6. Scope

Pinned chains freeze via the shared resolver, which **raises rather than falling back**;
`pre_panel_history` filtered; settlement and strike selection on **as-traded** `raw_close`
(`U1-SPLIT`: `raw_close` for anything touching a strike, `close` only for a return). Names with no
earnings coverage dropped and listed. **The uncovered 25% of events is UNMEASURED and never read
as zero.**

---

## 7. Prior, stated as the brief requires — and it is the brief's own

| outcome | prior |
|---|---|
| **REAL-BUT-UNSURVIVABLE** | **55%** |
| VIABLE | 25% |
| NOT-DEMONSTRATED | 15% |
| UNDERPOWERED | 5% |

**I expect the effect to survive and the claim to come out materially narrower than the
arithmetic suggests, and the mechanism is concurrency.** `O11`'s finding was that alerts cluster
and the edge lives in the crowd, so a cap refuses trades exactly when opportunity is richest.
**Earnings cluster far harder than alerts** — four concentrated weeks a quarter — and this book
generates roughly **2.4× the trades `MB3` simulated** (≈4,769 against 1,987) inside those same
weeks. `MB3`'s alert-spanning book already lost **621 of 1,915** trades to the cap-10 refusal at
$50k. I expect that refusal share to rise materially here, and the honest headline to be a
positive per-trade effect that a cap-10 account cannot harvest.

**Secondary expectations:** **E1** the cap-10 refusal share exceeds `MB3`'s 32% (75%); **E2** A1's
gap is smaller than `O17C4`'s +4.79pp because the control is DTE-matched by design (60%); **E3**
$250,000 survives where $50,000 does not (55%).

---

## 8. Trial cost

**2 options trials, booked BEFORE the run: `N` 305 → 307** (one per arm; the survivability leg is
a second statistic that could independently be reported, so it is charged). The count is
**re-read from `by_domain` after merging**, never quoted from a session's own mid-run figure.

**The census charges nothing** — it scored no hypothesis and touched no return.

---

## 9. What a result here can and cannot mean

**A VIABLE verdict is not a licence to trade.** `O11` governs, and the strategy would still be a
candidate for a future book that does not exist. **A REAL-BUT-UNSURVIVABLE verdict is the more
useful outcome for this operator**, because it closes the question with a mechanism rather than
leaving it open.

Nothing here reopens `O17C4`, whose own verdict stands as recorded — `REJECTED on a broken bar` —
and nothing here is a claim about the alert entry. **`R2` stands**: the alert subtracts value
inside this very effect.
