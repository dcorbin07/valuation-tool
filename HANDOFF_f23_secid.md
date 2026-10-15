# HANDOFF — `F23-SECID`: **DOES NOT CLEAR — and the identity key was never the obstacle.** Plus the 1999-2008 rung closed as unobtainable

**Date:** 2026-10-15 · **Branch:** `worktree-r1-f23-secid` · **Lane:** r1
**Register:** `PREREG_f23_secid.md`, committed **ALONE at `fba290e`** (markdown only, zero `.py`,
178 lines, a strict git ancestor of both runners) · **1 equity trial** booked at **`8191309`**,
before any runner existed (equity 306 → 307, hurdle **3.3843308785008586**, derived)
**ADOPTS NOTHING.** No file under `valuation/` changed. No app file touched. No broker code edited.
**THE CHECK QUADRANT IS UNTOUCHED** — `INSIDER-WIDE` spent it on 2026-10-13.

---

## 1. THE 1999-2008 RUNG — closed as unobtainable, zero trials

`DECISIONS.md` 2026-10-15, closed the `S25` way: a ledger row (`INSIDER-STAGE3-RUNG`) and a
**`FIXED`-class** research-log row at **zero trials**. Verified it landed in the right bucket —
equity moved by exactly one (the `F23-SECID` trial) while `rows_fixed_not_counted` rose 106 → 107.

**The charter-style sentence, in both rows:** *for this signal the stage-3 holdout cannot exist, so
the forward paper book is the remaining test.* With the limit that binds a successor: the charter's
1999-2008 proxy is reachable **at best for 2006-2008**, three of its ten years, all adjacent to the
build window and dominated by the financial crisis — **so nobody may later treat a 2006-2008 read
as the charter's holdout.** Nothing purchased. Measurements in `HANDOFF_insider_stage3.md` §1.

---

## 2. THE REGISTERED QUESTION, AND IT IS ANSWERED CLEANLY

**ARM A (name) and ARM B (ID) come out of ONE pass over ONE source**, so the only difference
between them is the identity column. That was the register's §1 design and it is what makes the
answer interpretable — sourcing the ID arm from the SEC while leaving the name arm on SF2 would
have changed the **feed** and the **key** at once.

### 2a. Event sets — the two rules are nearly the same object

| | ARM A (name key) | ARM B (ID key) |
|---|---|---|
| events, 2007-2019 all tickers | 4,824 | 4,851 |
| **build cell** (2009-2019 × half 0) | **2,277** over 608 tickers | **2,290** over 612 tickers |
| scored at `$500M+` | 317 | 318 |

**Build-cell Jaccard 0.9874** — 2,269 shared, **8 unique to name**, **21 unique to ID**.
(The **15 / 42** split is the ALL-ERA figure and is a different number; conflating the two
was an error of mine, caught by checking the write-up against the artifact.)

### 2b. Scored — and they are indistinguishable

| | ARM B (ID) — **the verdict** | ARM A (name) — reference, no verdict |
|---|---|---|
| mean, market-adjusted | **+0.1551pp** | +0.1920pp |
| *t* (date / ticker) | **+0.168 / +0.142** | +0.207 / +0.175 |
| its own null p95 | 1.9103 | 1.9513 |
| halves (early / late) | +1.820 / **−1.258** | +1.912 / **−1.258** |
| cost (size-tiered) | 0.647pp | 0.646pp |
| **net** | **−0.4919pp** | −0.4545pp |
| A1 / A2 / A3 / A4 | **T / F / F / F** | T / F / F / F |

**VERDICT: `DOES NOT CLEAR`.** A2 fails (below its own null, and the halves **disagree in sign**),
A3 fails (*t* 0.17 against a bar of 2.0), A4 fails (net negative). Only A1 passes.

**CHANGING HOW INSIDERS ARE COUNTED MOVED THE MEAN BY 0.037pp AND THE *t* BY 0.04.** That is the
finding: **the identity key is neither the problem nor the solution.**

---

## 3. WHAT THE ID RULE SHOWS ABOUT THE NAME RULE — Don's question, answered directly

**YES, NAMES DO COUNT ONE PERSON TWICE, AND IT IS THE DOMINANT ROW-LEVEL DEFECT.**

| direction | global | **within a ticker** (the unit the rule counts in) |
|---|---|---|
| one CIK under **several names** → name rule **OVER**-counts | 384 CIKs | **273 pairs** |
| one name over **several CIKs** → name rule **UNDER**-counts | 144 names | **16 pairs** |

Within a ticker, splitting beats merging **about 17 to 1**. So the name rule's dominant error is
**over**-counting distinct insiders, which means it can fire a cluster that was really **one insider
filing under two spellings** — **the false-trigger direction, and the more serious one for a book.**

**AND IT BARELY MATTERS AT THE EVENT LEVEL, WHICH IS THE OTHER HALF OF THE ANSWER.** Only **8 of
2,277** name-keyed build-cell events — **0.35%** — disappear under the ID key, and the ID key *adds*
**21** by splitting merged names apart. 58,846 distinct names resolve to 58,604 CIKs.

**SO BOTH SENTENCES ARE TRUE AND NEITHER ALONE IS HONEST:** the name key really does conflate
people, far more often than it splits them; and it changes under 1% of the events the rule fires on.

**THIS REFUTES MY OWN REGISTERED EXPECTATION 2**, which put merging as dominant at 60/40 on the
strength of the SEC's 2007Q1 quarter showing more CIKs than names. Over the full build era, at the
row level, **splitting dominates**. Expectation 1 (ID gives more events) and 4 (>90% shared) are
**right**; expectation 3 (ARM B clears) is **wrong**.

---

## 4. REPORTED AND EXPLICITLY NOT ATTRIBUTED — the SF2 gap is a JOIN problem, not a feed verdict

The **same cell** on the **licensed SF2** feed reads **+1.1319pp at *t* +2.01 / +2.25** on 1,378
events. The SEC-sourced arms read +0.19 / +0.16 at *t* ≈ 0.2 on 317 / 318. **That gap may not be
read as "the SEC feed kills the effect", because it is confounded**, and the confound is measured:

| | SEC-sourced | SF2 |
|---|---|---|
| build-cell tickers | **608** | **1,344** (only **335 shared**) |
| events resolving a point-in-time cap | **48.1%** | **83.3%** |
| scored at `$500M+` | 317 | 1,378 |

**AND THE OBVIOUS CAUSE IS RULED OUT:** blank trading symbols are **0.2%** of 2012Q1 Form 4
submissions, and the SEC pull is the **wider** source — **912,940 purchase rows over 12,464
tickers**. So this is a **ticker-join problem between the SEC's `ISSUERTRADINGSYMBOL` and the
corrected panel**, not a coverage hole in the SEC data. **It needs its own work and it is not what
this register tested.**

---

## 5. THE POWER TRAVELS WITH THE VERDICT, as the register required

The register declared **50.3% power on the gross leg and 14.7% on the net** before the run, on the
name rule's own realised build-cell `se`. **So a null here was always going to be weak evidence —
and that is stated, not discovered.**

**AND THE REALISED POWER IS FAR WORSE THAN THE DECLARED FIGURE, which I report because it cuts
against reading anything into this null at all.** The realised worst-clustering `se` is
**1.0957pp** against the declared **0.5641pp** — nearly **2x** — so the realised **MDE80 is
3.1135pp** and the arm's power against its **own** observed effect is **4.8%**, not 50.3%. Two
things compound: the `se` widened (the SEC-sourced cell has 317 events where the declared
figure assumed 1,378) and the effect itself collapsed. **This is the same family `INSIDER-WIDE`
§5d measured — a scaled `se` running optimistic — here at ~1.9x.**

**But the failure is NOT only a power failure, and that is why it is still a `DOES NOT CLEAR`
rather than an "unresolvable":** *t* **0.17** against a bar of 2.0 is not a near miss, **the
halves disagree in sign** — a separate failure a bigger sample would not fix — and the
two-sided *p* is **0.8875**, so BH at `k`=1 does not survive either. **A cell this weakly
powered cannot establish that the ID key is WORSE; it can and does establish that the ID key
does not RESCUE the cell, which is the question Don asked.**

---

## 6. CONSEQUENCE — F-23 stays declared and unfilled

Per `DECISIONS.md` and the register's §5.3, stated plainly:

* **No amendment to F-23. No F-23b.** The ID rule did not clear, so the book does not move onto it.
* **The ID-rule live-feed validation was NOT run** — the register made it conditional on clearing.
* **F-23 remains declared (`5ad68c2`) and unable to fill**, now for three independent reasons: its
  original feed validation fails on owner identity, the ID alternative does not clear, and the
  harness's own self-check is `ABSENT`.
* **NO VARIANT IS SEARCHED FOR.** A second key, a second `k`, a second tier or a second horizon
  would be a **new register with its own trial**, and **none is proposed.**

---

## 7. THE OTHER BLOCK — `SELFCHECK_ABSENT`: **Don has no step**

Measured rather than read off the docstring:

* `fleet.selfcheck_action()` → **`needed: True`, 21 of 21 declared books**, every one `ABSENT`
  (never certified) rather than `STALE`. **This is fleet-wide and not F-23's.**
* `fleet.recertify_attempt()` → **`attempt: true`, state `OWED`**, `fingerprint_before: null`
  (consistent with `ABSENT`).
* **Item 51 made it automatic AND covers this state.** `app_saas.py`'s cycle door says so in its
  own comment: *"`SELFCHECK_STALE` and `SELFCHECK_ABSENT` are what a re-run fixes, and
  `SELFCHECK_FAILING` — or a book whose stream cannot be read — is untouched."*
* **The cron is live and succeeding:** `fleet-cycle.yml` runs weekdays (`19 22 * * 1-5`) and its
  last two runs are **success in 43s and 42s** (2026-10-15 00:31, 2026-10-14 01:13).

**So the harness's own remedy string is correct: "Nothing needs doing: the next daily fleet cycle
re-certifies the harness itself and the books open again on that cycle."** The optional faster path
is **GitHub Actions → FLEET SELF-CHECK (re-certify) → Run workflow**, which is **dispatch-only by
design** because it places a real sandbox fill and cannot finish inside the cycle's 120-second cron.

**ONE HONEST QUALIFICATION:** `selfcheck_state` reads `data/fleet/…`, which is **gitignored and
local**, so the `ABSENT` above is **this checkout's** copy. Whether the *service* has already
re-certified is visible only on the service. **No broker code was edited** and the app fixer's move
of the paper books to Alpaca is not touched.

---

## 8. Defects of my own — two, both caught before anything was reported

**(a) THE FIRST CUT WOULD HAVE REPORTED ZERO EVENTS ON BOTH ARMS, WITHOUT RAISING.** I passed a
**placeholder** label Series to `opportunistic_purchases`, which keeps a row only where
`labels == IR.OPPORTUNISTIC` — so every row would have been dropped and both arms would have
scored nothing. **Caught by reading the predicate, not by anything failing.** The shipped
`insider_routine.classify` is now called (with `owner_col`, so the key varies there too — a pair's
routineness is a property of whose history you attribute trades to), behind a **zero-rows refusal**:
13 years of SEC filings with no qualifying purchase is an instrument failure, not an empty
population.

**(b) THE SUBSTRING-BAN FAMILY, ELEVENTH INSTANCE IN THIS RECORD AND THIRD IN ONE SESSION.** A test
of mine banned the substring `valuation/` and **failed against the correct tree**, because the arm's
own `ADOPTS_NOTHING` prose says *"No file under valuation/ changes"*. Its AST replacement was then
**too strict** — it demanded a direct `out_path(...)` call and fired on the correct
`pth = D.out_path(OUT); io.open(pth, "w")`. The property is about **writes to a literal path**, and
that is what it now asks, with a positive control.

---

## 9. Not done, named so it is not mistaken for done

* **Nothing adopted.** No file under `valuation/`, no app file, no broker code, no order, no
  percentage set by a lane.
* **No variant of the key, `k`, tier or horizon** — §5.3 forbids it and none is proposed.
* **The ticker-join gap (§4) is measured and NOT repaired.** It is a real finding and its own job.
* **The check quadrant is untouched and stays spent.**
* **The 1999-2008 build is not built.** Its size is reported; the decision is Don's.
* **It is NOT a finding that the SEC's insider IDs are worse.** They are the **cleaner**
  identifier — the census says so — and switching to them simply does not rescue this cell.
