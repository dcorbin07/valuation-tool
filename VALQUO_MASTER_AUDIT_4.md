# VALQUO_MASTER_AUDIT_4.md — the frontier audit

**Commissioned by** `PROMPT_audit4_master.md`. **Executed 2026-08-19.**
**Cold auditor, strictly read-only.** No file under `valuation/`, `scripts/`, `tests/`, `data/`
or `.github/` was changed. No backtest was run. **Zero trials charged** — every measurement in
this document is a fact about what is on disk or what the code does, in the class of `S25`, the
options re-open list and `HANDOFF_data_mining.md`. Nothing is adopted, nothing is re-opened, and
no verdict moves.

**Items are IDed `MB1` … `MB42`** (`MA` is taken by audit #3). Grouped by mandate, EV-ranked
within group. **42 items; total trial cost if every one were run is 32, of which 16 is `MB2`'s
grid, which I recommend against — so the whole of the rest of this audit costs 16 trials.**

---

## 0. THE BOARD WAS QUIET, AND ONE ROW SAYS OTHERWISE FOR A REASON THAT IS ITSELF A FINDING

The commission forbids starting on a moving target. Checked four ways rather than one:

| check | result |
|---|---|
| working tree | clean but for the untracked commission itself |
| `origin/worktree-*` not an ancestor of `origin/main` | **0** |
| remote refs not merged | 2, both `rescue/*`, both relics of the 2026-08-10 `PT-WRITER` incident (MB35) |
| ledger status cells containing `IN PROGRESS` | **1** — `B13`, whose own cell reads *"PARTIAL - BLOCKED ON DATA, **NOT IN PROGRESS**"* |
| ledger status cells containing `INPROGRESS` | **1** — `D11`, and it is **stale** |

`D11`'s row is dated 2026-08-17 and reads `INPROGRESS`. Its own handoff, written the next day and
committed at `d6c943c` ("The harvest is closed"), opens: *"**Status: HARVEST CLOSED 2026-08-18.
THE MINER IS IDLE AND THE SUBSCRIPTION CAN LAPSE ON SCHEDULE.**"* All five tiers complete, 2,850
units, zero failed, frozen and hash-verified.

**So the lane is idle and its board row says it is working.** That is mandate 7's thesis
reproduced on the first check of the audit, and it is why `MB27` is ranked where it is. The board
is quiet; I proceeded.

**One more thing that had to be re-derived rather than trusted.** The commission states equity
`N` 232+, options 297+. Measured live from `research_log.detail()` at session start:

```
trials_logged 549   by_domain {'equity': 234, 'options': 300, 'unified': 0, 'infra': 15}
rows_counted 139    rows_fixed_not_counted 65    trials_domain_unresolved 0
```

**Every bar in this document is quoted at equity `N` = 234 (hurdle 3.3031261300040304) or
options `N` = 300 (hurdle 3.3775086897463940).** Where I quote a bar at a different `N`, I say so.

---

## 1. THE HONEST ONE PAGE

### The three most valuable frontiers

**FIRST — `S22`'s term-structure claim has never faced the one null that predicts its own shape,
and I measured the gap rather than asserting it (`MB21`).** Boudoukh–Richardson–Whitelaw (RFS
2008) is that with a *persistent* regressor and *overlapping* long-horizon returns, R² and
long-horizon β rise **mechanically under the no-predictability null**. `S22`'s per-horizon null is
`fixed_weights_null`, built from `placebo_panel`, which permutes signal rows **within each
rebalance date** — so the placebo signal has, by construction, no persistence at all. Measured
read-only on `panel_corrected_69d.pkl`: the **real** composite's per-name lag-1 rank
autocorrelation across rebalances is **0.5802**, still **0.4099 at lag 8 (two years)**; the
**placebo's is 0.000** (−0.0011 / +0.0010 / +0.0005 across three seeds). The most persistent theme
is `size` at **0.9915** — and `X3` measured that `size` carries the composite's entire statistical
significance. So every horizon beyond `H=63` in `S22` is scored against a null that cannot
generate the artifact it most needs to exclude, and the error grows with horizon, which is
precisely the axis `S22`'s headline lives on. **This is product-consequential**: `S22-DISPLAY`
ships *"still ahead by about 5.1% annualized two years later"* and the rank-IC-rises-with-horizon
corroboration on the hot-list card, the name row and `/methodology`. Cost to resolve: **1 infra
trial**, no new data, one session.

**SECOND — 2.7 million alternative contracts have been asked exactly one question, and the
question that decomposes `R2` has never been asked at all (`MB1`).** The harvest census pinned
~636 alternatives per entry date and 99.9% holding-period chain coverage; `O21-D2` then spent the
one authorised same-hypothesis re-open on them and came back `IMMATERIAL`, with both statistics'
CI95 inside the bar. What no prior study could do — because every prior study scored the ONE
contract the book held — is compare **menus** rather than picks: the distribution of outcomes over
the whole in-band alternative set on an alert day, against the same menu on random days. That
separates *"the day was bad"* from *"the contract was bad"*, which `R2` and `O13` between them
cannot. `O13` already measured the loss to be **entirely a within-bin rate effect** (−4.23pp to
−5.79pp against a −5.0640pp total), which makes the expected answer *"it is timing"* — and a
pre-committed confirmation of that **closes contract selection permanently for 2 trials**, which
is the cheapest closure available anywhere in the options book.

**THIRD — the incremental-IC gate that this commission itself prescribes for every proposed cross
is defective on this panel, and I reproduced the defect independently (`MB7`).** `MA58-SEAS`
found it on 2026-08-18; measured here from the panel directly: complete-case residualisation on
the seven weighted incumbents leaves **49 of 69 dates**, first date **2014-01-17**, because
`institutional` has coverage **0.7172** and starts there. Rows fall from **81.2% to 58.3%**.
Dropping `institutional` from the residualisation basis restores **69 of 69**. So **every**
mandate-2 and mandate-4 proposal in this document is silently a post-2014 test until the gate is
re-specified — and the re-specification is free. It is the highest-EV item in the audit per unit
of cost, because it costs nothing and it gates six other items.

### The state of the project, in one paragraph

Valquo has done the expensive thing properly: 549 pre-registered trials across two books, an
adversarially calibrated placebo floor, a trial denominator that feeds its own Deflated Sharpe, a
public research record, and one adoption. The equity composite clears its own calibrated bars
(top-decile alpha HAC *t* 4.3762 against a floor of 2.0540; long-short HAC *t* 2.6199 against
2.2837) and **fails** the bar derived from counting its own trials (3.3031 at `N` = 234, shortfall
0.6832) — a tension the project states honestly and correctly declines to resolve. The options
book is 300 trials with zero entry edges and several formally closed families. What the record now
shows, and what audit #4 is for, is that the *marginal* return to further searching this panel has
gone close to zero: the arithmetic in `MB13` shows that a regime contrast on the panel's single
biggest open finding would need **34 years of data on each side** and there are 17.3 years in
total, and the same shape recurs everywhere — `MA58-SEAS`, `V6`, `S19`, `MA31`/`MA32` and `U2` all
returned nulls that the projects' own power rules could not interpret. **The frontier is
therefore not another hypothesis. It is (a) instruments — a persistence-preserving null, a
repaired incremental-IC gate, a ported effective-n bar — and (b) objects the project owns and has
never read: 2.7 M alternative contracts, a 14-venue tick tape, and a banked reverse-DCF panel with
a point-in-time expectations gap in it.** Three of the four cheapest items in this audit cost zero
or one trial and two of them are corrections rather than searches.

### What I could not check

- **The three freezes are on `D:` and I did not open them.** `D:\thetadata\freeze_options_2026-08-17`
  (12,302 files / 26.98 GB), `freeze_rawpull_2026-08-18` (2,850 units / 17.69 GB) and the harvest
  census JSON are cited from `HANDOFF_data_mining.md`. Every alternatives figure in mandate 1 is
  **that handoff's**, cross-checked against the options re-open list where the two overlap (the
  699.6 mean slice reproduces across two independent passes) but not re-measured by me.
- **`data/free_analysis/MA28_CARD.json` is not on the primary checkout's disk**, though
  `valuation/web/accounting_risk.py:120` names it as the shipped card's `ARTIFACT`. Its figures
  are pinned as literals in that module and its `FORMULA_SOURCE` script exists, so nothing is
  lost — but the provenance pointer a reader is invited to follow dangles. `RUN_RULES` rule 9's
  last mile. Sibling artifacts from the same era (`S10_ACCOUNTING.json`, `MA58_SEASONALITY.json`,
  `O21D2_ALT_PNL.json`) are all present, so this is specific rather than systemic.
- **The live service.** I did not authenticate to any surface, so every claim about what renders
  is read from the module that owns the copy, never from the site.
- **`ext_condition1-4` in the tick cache read 255 on all rows of all three sampled payloads.**
  That is a sampled observation, not a census; four of the cache's 22 columns may carry no
  information and I did not prove it across 3,884 units.
- **TIDEMARK's numbers** are read from its generated documents (`POWER_GATE.md` is machine-generated
  and says so). I re-ran nothing there.

---

## MANDATE 1 — THE OPTIONS EDGE, RELOCATED

*EV-ranked. The dead questions are not re-litigated; `R2`, `U1`, `O6`, `O13` and `P1S0` are cited
against the proposals rather than around them.*

### MB1 — The alternatives **menu**, and the selection-vs-timing decomposition it uniquely permits
**EV: HIGH (a cheap permanent closure). Trials: 2, options (`N` 300 → 302). Prior: ~20% that
selection carries any of the loss.**

**Mechanism.** Every options study this project has run scored the ONE contract the book held.
`R2` therefore measures a compound: the alert chose a *day* and a *rule* chose a *contract*, and
the −5.0640pp gap cannot be attributed to either. The census pins **2,713,919 alternative
contracts, median 636 per entry date across 8 expirations and 61 strikes, on 3,885 of 3,885 entry
dates**, with a frozen full chain on every session in the Tier-C/D/E pull. That makes a
*distributional* object available for the first time: the outcome distribution of the **whole
in-band menu** on an alert day, versus the same menu construction on matched random days.

If the alert-day menu distribution and the random-day menu distribution coincide, the loss is
**100% timing** and contract selection is irrelevant — which closes contract selection for good.
If the alert-day menu is systematically worse, the alert is picking bad *chains*, not bad *days*,
and `O13`'s within-bin finding needs re-reading.

**Why this is not `O6` in costume.** `O6` varied four cheapness rules and compared *picks*; its
decisive finding was that every rule silently **changed the delta** (mean absolute delta gap up to
0.310), so it never held exposure fixed. This scores the **entire menu, bucketed by delta**, so
delta is a reported axis rather than an uncontrolled by-product — which is exactly the remedy
`MA54-4` prescribed and `O6` could not apply. It is also not `O21-D2`: that priced **one**
alternative per entry (the dividend-corrected pricer's different pick on 179 entries) and returned
`IMMATERIAL`; this forms a distribution over ~636.

**Register.** Pre-commit, before any outcome is read: the menu definition (moneyness band and DTE
band, taken verbatim from the shipped `pick_contract` prefilter so it is the engine's own menu);
the primary statistic (menu **median** holding-period return, with menu p75 as the declared
secondary); the comparator (5-seed split-clean matched random entry, `R2`'s own control books);
the both-halves rule; and the delta-bucket reporting grid.

**Kill condition.** If the alert-day and random-day menu medians differ by **less than 1.0pp in
either half**, contract selection is declared irrelevant, the register says so in advance, and
**no further contract-selection register may be opened on this book**. A pass does not license a
trade — `O11` binds (see `MB2`).

**Inherited caveats.** `U1-SPLIT`'s rule travels: strikes are as-traded, `raw_close` for anything
touching a strike and `close` only for a return. `MA31`'s pair-availability warning travels: a
two-sided usable quote on a menu is rarer than on a single pick, so the effective menu will be
smaller than 636.

---

### MB2 — The DTE × delta grid, designed honestly — **and the design is a recommendation against running it**
**EV: MEDIUM (the design is the deliverable). Trials if run: 16, options (`N` 300 → 316; hurdle
3.3775 → 3.4034). Prior: ~7% that any cell is ACTIONABLE.**

Don has pre-committed interest in 60–90 DTE. The commission asks for the full-grid register with
multiplicity priced in advance. Here it is, and then here is why I would not spend it.

**The grid.** DTE {30, 60, 90, 180} × delta {0.15, 0.35, 0.60, 0.85} = **16 cells**. All sixteen
booked as trials in the register **before** the run and **all sixteen reported**, pass or fail —
the `n=<k>` grid convention the research log already carries.

**The survivorship rule, stated in advance.** Contracts are chosen from the frozen menu on the
entry date and settled from the frozen forward path, hold-to-expiry. A cell with **fewer than 30
closed legs in either half is UNDERPOWERED, never null** — the `V6-B` M2 / `O26` floor precedent.
Cells are not merged to reach the floor.

**What would make a cell ACTIONABLE rather than merely significant — and this is the leg that
binds.** `O11` measured that a book with **+3.27%/trade positive expectancy ends at $37,059 from
$50,000** at a concurrency cap of 10, because the edge lives in the crowded weeks (expectancy
−4.51% in quiet weeks, **+14.28%** in weeks above the 90th percentile, 51.5% of trades in weeks of
more than 10 alerts) and a cap refuses exactly those. So a cell is ACTIONABLE only if **all four**
hold: (1) expectancy positive; (2) in both halves; (3) clearing its own within-cell permutation
p95; **and (4) terminal equity above starting equity at `O11`'s cap-10, $50k configuration.** Leg 4
is the one that will fail, and a register that omits it produces a significant cell nobody can
trade — which is the exact failure `O11` exists to prevent.

**Why I recommend against it.** Three separate measurements already price the corners. The
deep-ITM long-tenor corner is `DEEPITM-FIN`: **executable financing rf + 342 bps, all-in 701.87
bps/yr**, and the roll is half of it and cannot be avoided. The 35-delta short-tenor corner is the
banked book, and `R2` is standing. The whole family that would express any winning cell was closed
by `P1S0` on a pre-registered both-halves failure, and `P1S0-CONTROL` could not move it. **16
trials to sweep a space whose corners are all measured and whose vehicle is closed is a search, not
a question.**

**If exactly one cell is to be run**, run 60–90 DTE × 0.85–0.95 delta **alone**, 1 trial, framed as
`DEEPITM-FIN`'s return-side companion — and pre-commit that its failure closes the tenor question
permanently rather than prompting a fifth tenor. `DEEPITM-FIN`'s own scope note applies verbatim:
it is a **cost** measurement and says nothing about returns.

---

### MB3 — Event ownership: **real, mean-driven, and untradeable by this operator — and the deciding arithmetic costs zero trials**
**EV: MEDIUM-HIGH (it closes a live ambiguity). Trials: 0 for the decisive arithmetic; 1, options,
only if a disclosure is wanted. Prior: ~85% it closes.**

**The record, corrected against the commission's own framing.** The commission describes `O17C4`'s
effect as having nowhere to live. The ledger is sharper than that: **`O17C4` is `DONE — REJECTED,
and solely on a bar of my own that was broken`** — c1, c2 and c4 all pass and it fails on c3. And
the register's own post-mortem (`CLAUDE.md`, session 62) diagnosed two of its three bars as not
measuring what they were written to measure: B1's trades-per-year axis is **unpassable by
construction** for a subset of the book it is drawn from, and B1/B2's name axes re-measure the
**29-name foreign-issuer coverage hole**. **Only B3 measured its property, and B3 passes.**

**So the effect stands and the rejection does not rest on it.** Measured: a call spanning the next
announcement earns **+10.30% against +5.50%** on 27,350 random-entry control trades, **+4.79pp**,
positive in both halves, sign test **z +2.054, p 0.040**.

**And the same register measured why it cannot be traded here.** It is a **MEAN** effect, not a
median one: DTE-matched, **median-vs-median is +0.40pp** (−51.41% against −51.81%). The typical
trade is a near-total loss either way. Harvesting a mean carried by a thin right tail requires many
small independent positions held without intervention — which is exactly the configuration `O11`
measured to end below its starting equity at a $50k account and cap 10.

**The decisive test that has never been run, and it charges nothing.** `O12`'s Kelly and
ruin machinery is built and its inputs are the banked per-trade returns. Ask it one arithmetic
question: **at what account equity does the cap-10 ruin arithmetic permit an earnings-spanning
book to end above where it started?** That is a computation on banked distributions with no
hypothesis and no bar — the `S25` / `X7RECON` class, **zero trials**.

**Kill condition.** If the required equity exceeds **$250,000**, the answer is final for this
operator and the family closes permanently, with the effect recorded as real and out of reach.
Below it, the question becomes a live design and needs its own blind register.

**My argued verdict, either way as the commission asks.** *Real, mean-driven, untradeable at this
account size.* The honest home for it is a **disclosure in `MA28`'s class** — "options spanning an
earnings announcement have historically had a higher mean return and an essentially unchanged
median; the mean is carried by a small tail" — not a strategy family. `O11` governs and nothing
here licenses trading it.

---

### MB4 — Expression and financing: **the door is closed, and the closing argument is arithmetic**
**EV: MEDIUM (a closed door, argued from measurements, is a legitimate deliverable). Trials: 0.**

The commission asks whether ANY expression question survives. Taken one at a time:

| expression argument | status | the measurement that closes it |
|---|---|---|
| **Cheaper leverage than margin** | CLOSED at today's brokers | `DEEPITM-FIN`: all-in **701.87 bps/yr** (financing 342.35 + roll 340.06 + commission 3.57) at median DTE 73 and 5.0 rolls/yr. Cheaper than **exactly one** of three retail cards — Robinhood standard at rf + 995 — and **more expensive** than the two an operator would use (Robinhood Gold rf + 420, IBKR Pro rf + 150). |
| **Financing improves with tenor** | CLOSED as unownable | The owned cache is hard-capped at 200 DTE (frontier §2a); the Tier E pull reaches 858 DTE but only for **2016–2018**. And the frontier's own reading is that 60–90 DTE, the shortest tenor, is the **worst case** — which is what makes the measured number the relevant one. |
| **Defined-risk sizing** | CLOSED by mechanism | `O11`'s ruin is driven by **opportunity refused at the concurrency cap**, not by tail loss. Capping the tail with a spread does not add capacity in the crowded weeks where the expectancy lives; it reduces it, because a spread ties up the same slot for less premium. |
| **Tax** | ALREADY ANSWERED | `U5` is `DONE`. |
| **Collateral** | NOT A CONSTRAINT | The operator holds no position that a share purchase would breach; there is no margin requirement for an option to relieve. |
| **Alpha in the expression** | CLOSED | `P1S0` failed at its power anchor in both halves at all three horizons and closed the options-expression family; `P1S0-CONTROL` returned NULL and could not move it. |

**Verdict: expression is CLOSED.** The one re-open condition is a *financing* fact and not a
research one, so it needs no trials and it can be stated as a number: **if the operator's
borrowing rate ever exceeds rf + 702 bps, the deep-ITM call becomes the cheaper leverage** and
`DEEPITM-FIN` has already priced it. Today's Robinhood Gold and IBKR Pro cards are both below that
line. Nobody should spend a trial re-deriving this.

---

### MB5 — The record correction the re-open list asked for landed on two rows of three
**EV: LOW-MEDIUM (free, and it is a record integrity item). Trials: 0.**

The blind re-open list found that three registers priced non-entry-day chains from the **mutable**
`data/options` store without disclosing it, and recommended the disclosure be corrected
*"regardless of whether anything is re-run"*. Measured on today's ledger: **`O6` and `O7` now
carry it; `U1` does not.** `U1`'s row still describes its grid — *"182 names x 39 rebalance dates
… 6,811 cells to 5,186 trades"* — without saying which store served it, while
`scripts/u1_entry.py`'s own docstring says *"READ-ONLY on `data/options/`"* and its dates are
rebalance dates the freeze never covered.

**Action:** one sentence on `U1`'s note. **No re-run** — the re-open list's reasoning stands
(`U1` failed all four pre-registered conditions and every decile's median trade sits between
−52.5% and −54.3%, which no chain source moves).

---

### MB6 — Tier C's small caps are an options-side object too, and the flag is not optional
**EV: MEDIUM. Trials: see `MB17` (mandate 4 owns the equity half). Pointer item.**

The 420 never-tried optionable names now hold **982 units with data, 50.6 M rows, 2016–2018** — a
population no options study has ever touched, and the only one that is small-cap. Two hard
constraints must be written into any register before it runs, both from the census: **28 of 982
units (2.9%) across 14 symbols carry another company's option data** (`pre_panel_history`, with
`panel_first_year` on every row — FOXA, IR, VG, CR, AZPN and nine others), and treating them as
the modern company is a live way to get a wrong answer; and **278 units are `empty_vendor`**, so a
name's absence is a fact about the vendor rather than about the market. The equity-side question
this population uniquely answers is in `MB17`.

---

## MANDATE 2 — COMBINATIONS AND AMPLIFIERS

### MB7 — **The incremental-IC gate is defective on this panel, and it gates everything else in this mandate**
**EV: VERY HIGH (free, and six other items depend on it). Trials: 0 — a specification correction.**

The commission requires every proposed cross to pass "the PEAD/U2 template": residualise the
candidate on the seven weighted incumbents, then test the residual IC. **On this panel that
template silently deletes 20 of 69 rebalance dates.**

Measured directly from `panel_corrected_69d.pkl`, reproducing `MA58-SEAS` independently:

| basis | rows kept | dates with ≥ 20 names | first such date |
|---|---|---|---|
| all seven incumbents (complete case) | 66,444 (**58.31%**) | **49 of 69** | **2014-01-17** |
| six incumbents, `institutional` dropped | 92,540 (**81.21%**) | **69 of 69** | 2009-01-15 |

The cause is one column: `institutional` has coverage **0.7172** and its first date carrying 20 or
more names is **2014-01-17**. Every other weighted theme starts 2009-01-15.

**Consequences, and they are not small.** (1) Any incremental-IC register on this panel **is a
post-2014 test** unless it says otherwise. (2) Its "early half" is not the panel's early half — of
the 49 surviving dates only **28** precede 2021, and once a candidate's own coverage filter is
applied on top (as `MA58-SEAS` found) that cell can fall below `S18`'s 16-date floor, which is a
second and independent reason such a design cannot return an interpretable both-halves verdict.
(3) `U2`, `MA31` and `MA32` all used this template, so their reported early halves inherit it.

**The fix, and it is a choice the register must make explicitly rather than inherit:**
either **(a)** residualise on the **six** full-window themes and report `institutional`
incrementally as a declared secondary arm, or **(b)** keep all seven and state in the register
that the test is post-2014 with a 28-date pre-2021 cell. Option (a) is better on power; option (b)
is better on comparability with `U2`/`MA31`/`MA32`. **Pick one before running anything in this
mandate.**

---

### MB8 — MA28's crash flags as a position-SIZING haircut, judged on crash count and never on alpha
**EV: HIGH. Trials: 1, equity (`N` 234 → 235; hurdle 3.3031 → 3.3042). Prior: ~50%, and the
uncertain leg is the one that decides.**

**Mechanism, and it is why sizing rather than selection.** `MA28-CARD` measured a **crash-rate
ratio**, not an alpha: names tripping two or more of Beneish M > −1.78, Altman Z < 1.81 and
top-decile external financing lost more than half their value over the next quarter at **2.6597%
against 0.8743%, ratio 3.0422×**, replicating at 3.42× early and 2.93× late, with every window's
observed value beyond the **maximum** of its own 500-draw permutation. And the effect **strengthens
monotonically with size**, 2.010× in the smallest quintile to **5.169× in megacaps**, because the
kept rate falls 14.5× across quintiles while the flagged rate falls only 5.6×. A quantity of that
shape maps onto **how much to hold**, not onto **what to hold**.

**The statistic must be a name-level crash count, and the register must say so before it runs.**
`S10-ACCT` ran the exclusion version and failed on the **portfolio-drawdown** leg — and `S10` had
already measured why that leg can never pass: this book's worst peak-to-trough spans **exactly one
63-day period on every arm, COVID 2020Q1 at trough index 44 of 69**, which no name-level rule can
move. So the primary is **the count of top-decile holdings suffering a > 50% quarterly fall**,
weighted by the haircut, which is the object the flag demonstrably predicts.

**Why this is not `S10-ACCT` in costume.** Different intervention (a 0.5× weight, not a deletion),
different primary statistic (name-level crash count, not portfolio max drawdown), and the alpha leg
is **non-inferiority** rather than improvement. The register must state all three.

**Register.** Haircut fixed at 0.5× before the run and not swept. Primary: flagged-name crash count
in the book, both halves. Secondary and gating: book top-decile alpha as a **non-inferiority** leg
against `X7`'s calibrated **1.8629pp** margin (`MA19`'s recalibrated figure at `N` = 224 — and see
`MB31`, this floor is one of the two that has already moved once and is due a re-derivation at
`N` = 234). `C7`'s eligibility sensitivity travels: **22.01% of rows carry fewer than two
computable inputs** and sit in the base-rate group by construction, so the arm must be re-read on
eligible rows only as a declared sensitivity.

**Kill condition.** If the crash-count reduction is under **20% in either half**, the sizing family
closes permanently. If alpha non-inferiority fails at the calibrated margin, the arm is REJECTED
regardless of the crash result — a risk control that costs alpha is a trade, not a free lunch, and
this register may not make that trade.

---

### MB9 — MA28's flags as a short-put veto: **REFUSED as stated**, and the moneyness version is a new hypothesis
**EV: LOW as stated. Trials: 2, options, only for the re-specified version. Prior: ~12%.**

The commission floats the crash flags as a veto on the short-put side. **It is `V6-OPT` in costume
and must be refused.** `V6-OPT`'s decisive mechanism: *selling a 25-delta put is selling a 25%
assignment probability by construction*, so the strike has already spent the risk edge — measured,
assignment came back **25.30% healthy against 25.73% unhealthy**, a 0.43pp gap, while the unhealthy
name paid **2.978% of strike against 2.550%** purely because its implied vol was higher. A crash
flag is a risk signal; a delta-targeted put is blind to a priced risk difference by construction.

**The one version that is not in costume** is the one `V6-OPT` itself named as the obvious
re-opening: **target MONEYNESS, not delta**, so the strike does not move with the name's own
volatility. That is a **new hypothesis needing its own blind register**, and it must additionally
argue past two standing closures: the options-expression family (`P1S0`) and the short-vol
question (`O9`). **I do not propose it**; I record that it is the only live form and that anyone
proposing it inherits three unfavourable priors.

---

### MB10 — V6-B's small-cap survival gradient: the honest use is a **disclosure**, not a surface and not a book change
**EV: MEDIUM. Trials: 0 for the disclosure; 1, equity, for a sizing version I recommend against.**

`V6-B` measured a large, replicated effect — healthy 20% drawdowns fall a further 20% **10.228pp**
less often at HAC *t* −10.5847, both halves, four to five times its own MDE in every window — and
attached its own standing caveat: **−14.287pp in the smallest quintile against −3.787pp in
megacaps**, so *"the claim is strongest exactly where the product is not"*.

**A small-cap surface is the wrong answer, for two reasons already in the record.** `V6` measured
that a drawdown on this panel is substantially an **inverse-momentum sort** (Spearman +0.6642
against the `momentum` theme), so a dip surface systematically surfaces names the live composite is
marking down — two screens that disagree by construction. And the megacap quintile, the one the
live hot list actually occupies, is the single quintile that **fails** `V6-B`'s own both-halves leg.

**The honest use is the `MA28-CARD-UI` pattern applied to a caveat instead of a claim**: on the
existing dip surface, state the gradient and where the displayed name sits in it. Zero trials, zero
hypotheses, and it makes a limitation legible instead of leaving it in a handoff.

**If a sizing version is wanted** it costs 1 equity trial, and its kill condition is nearly
pre-decided: `V6-B` already measured the megacap separation at **3.787pp**, so a register requiring
> 3.0pp in the megacap quintile is asking a question whose answer is on the record. **That is a
reason not to charge the trial**, and I record it rather than proposing it.

---

### MB11 — The optionable partition as a **reported diagnostic**, which is all `P1S0` left it as
**EV: MEDIUM. Trials: 0.**

`P1S0-CONTROL` measured that the optionable subset is **worse early and better late**: the full
2,531-name panel beats the optionable subset by **+1.467pp (H=63), +6.124pp (H=252), +1.527pp
(H=504)** over 2016–2020, and loses to it by **−9.704pp, −10.927pp and −1.555pp** late. The live
hot list is largely optionable names, so this is a description of where the product's own universe
has sat.

**It may be reported and it may not be used.** `P1S0`'s gate closed the family on it, and the
register's own defect note says the two effects **interact and its gate cannot separate them**. So
the copy must say the partition is a description of the past and not a rule, and it may carry no
forecast. Zero trials, and it belongs with `MB39`'s disclosure-card family.

---

### MB12 — `MA58` landed, and the pattern across three nulls is worth more than any of them
**EV: MEDIUM (a record item that constrains future registers). Trials: 0.**

The commission asks me to check the ledger for `MA58`. It landed on 2026-08-18:
**`MA58-SEAS` — `DONE — UNINTERPRETABLE, zero adopted`**, equity `N` 232 → 234. The seasonality
cross is closed for the reason `MA58` gives, and no further trial should be spent on it.

**The pattern it completes is the finding.** This panel has now produced **three** signals carrying
genuinely new information that predict nothing measurable with it:

| item | orthogonality measured | verdict |
|---|---|---|
| `U2` — options-surface features | incumbents explain only **5.5%–8.8%** of their variance (against 41.3% for `gp_on_capital`, 78.4% for `ret_6_1`) | all four arms REJECTED |
| `MA31` / `MA32` — parity deviation, open/close share | R² on the seven incumbents **0.0438 / 0.0273 / 0.0361** | all three NULL |
| `MA58-SEAS` — annual-lag seasonality | mean R² **0.0755**; largest theme correlation −0.1511 | UNINTERPRETABLE, and REJECTED on its own bars |

**So on this panel orthogonality is not evidence of value, and it has now failed as a motivation
three times.** Any future register citing "structurally orthogonal to everything in the panel" as
its reason to expect an effect must cite these three against itself. That sentence is free and it
will save trials.

---

## MANDATE 3 — THE 2016–2020 PROBLEM

### MB13 — **The regime contrast is NOT ANSWERABLE on this panel, and here is the arithmetic**
**EV: VERY HIGH (it forecloses a whole family, rigorously). Trials: 0.**

The commission asks whether there is a pre-registerable design that answers *"when does this
composite work"* without fitting the regime to the answer, and instructs me to say so plainly if
the answer is "not without another decade". **It is worse than a decade, and TIDEMARK's power-gate
method is the instrument that says it properly.**

**The inputs, all measured, none assumed.** From the shipped artifact: quarterly top-decile alpha
has mean **+1.794pp**, **sd 3.298pp**, lag-1 autocorrelation **+0.0812** — so the design effect is
**1.177** and `n_eff/n` is 0.850. From the panel's own date list: the documented quant-crisis
window holds **9** rebalance dates and the `P1S0` dead half holds **20** of 69.

**The minimum detectable regime contrast, in annualised top-decile alpha:**

| contrast | n_A | n_B | SE | MDE at abs t = 2 | **MDE at the honest hurdle 3.3031** |
|---|---|---|---|---|---|
| documented crisis vs rest | 9 | 60 | 1.279pp/qtr | 10.23pp/yr | **16.90pp/yr** |
| `P1S0` dead half vs rest | 20 | 49 | 0.949pp/qtr | 7.59pp/yr | **12.54pp/yr** |
| plain halves | 34 | 35 | 0.861pp/qtr | 6.89pp/yr | **11.38pp/yr** |

**The published total top-decile alpha is 7.17pp/yr.** Every cell in the right-hand column asks the
regime *difference* to exceed the entire strategy, by a factor of between 1.6 and 2.4.

**Read the other way round, which is TIDEMARK's more useful form** — how much history would be
needed at 80% power and the honest critical value:

| regime alpha gap | quarters required **per window** | years each side |
|---|---|---|
| 2.00 pp/yr | 1,757.7 | 439.4 |
| 4.00 pp/yr | 439.4 | 109.9 |
| **7.17 pp/yr (the whole published alpha)** | **136.8** | **34.2** |
| 10.00 pp/yr | 70.3 | 17.6 |
| 15.00 pp/yr | 31.2 | 7.8 |

**The panel supplies 17.3 years in total. The crisis window supplies 2.3.**

**Ruling, in TIDEMARK's grammar: NOT PERMITTED.** No regime-conditioning design on this panel can
return an interpretable verdict, and this does not depend on the multiplicity correction — even at
an uncorrected t = 2 the crisis contrast needs a 10.23pp/yr gap. **The naive fix the record warns
about most is not merely dangerous here; it is arithmetically futile**, which is a stronger and
more durable reason to refuse it than "it is p-hacking".

**What this forecloses:** every regime-conditioning register on this panel, permanently, until
forward time accrues at one quarter per quarter. **What it does not foreclose:** `MB14`.

---

### MB14 — The one pre-registerable thing left: a **three-state diagnostic** on an externally-dated window
**EV: HIGH (1 trial converts the project's largest open wound into a dated, powered refusal).
Trials: 1, equity (`N` 234 → 235; hurdle 3.3031 → 3.3042 — 0.0011 of a t). Prior: ~70%
CANNOT-TELL, ~20% FAILS-THROUGHOUT, ~10% WORKS-OUTSIDE. I recommend running it.**

**The regime definition comes from outside the panel and from before this project looked, which is
what makes committing to it blind meaningful.** The 2018–2020 quant crisis is a documented,
independently dated episode: Blitz, *The Quant Crisis of 2018–2020: Cornered by Big Growth*
(Robeco, published February 2021) finds that essentially the only way to outperform in that window
was to hold the largest and most expensive growth stocks, and that other factors worked only
through implicit exposure to them — and that this episode was distinct from prior value drawdowns,
which are better described as momentum rallies with collateral damage. **Replication status:** the
episode itself is not contested; it is documented across practitioner research (Robeco, Man Group,
First Sentier) and its dating is external to this project. What IS contested is any causal
mechanism, and the register must claim none.

**The discriminating fact, and it is why this design has content.** `P1S0-CONTROL`'s dead window is
**wider** than the documented crisis. Measured on the panel's own dates: 2016-01-20 to 2018-04-20
holds **10** rebalance dates that are **outside** the crisis, and 2018-07-20 to 2020-07-22 holds
**9** inside it. So the two hypotheses make different predictions on a real, disjoint sub-sample.

**Design.** Commit the window blind, before any scoring: crisis = 2018-06-01 to 2020-08-31, taken
verbatim from the published dating and not tuned. Score the composite's **sorting** statistic —
monotonicity and long-short, never a level, because `P1S0-CONTROL`'s own defect note is that its
leg 2 *"asked a LEVEL question when the item is about SORTING"* and that is exactly why it returned
NULL. Three states, fixed in advance:

- **WORKS-OUTSIDE** — the composite sorts over 2016-01 to 2018-05 and fails only inside the crisis.
- **FAILS-THROUGHOUT** — 2016–2018 fails too; the crisis explanation is refuted and the failure is
  longer and unexplained.
- **CANNOT-TELL** — the pre-committed power rule fires. `MB13` says it very probably will, and the
  register must carry `MB13`'s table so the reader can see that this was known before the run.

**Kill condition.** The register pre-commits that a **CANNOT-TELL closes regime work on this panel
permanently**, and that the only admissible re-open is accrued forward time — not a new window, not
a finer statistic, not a different regime variable. Without that clause this item becomes the first
of five.

**Why spend a trial on a probable CANNOT-TELL.** Because the alternative is leaving the project's
single most consequential open finding in a state where any future session can re-litigate it
cheaply. A dated, pre-committed, powered refusal costs 0.0011 of a t on the hurdle and removes a
recurring cost permanently.

**What the product may honestly DO with any verdict: almost nothing, and the constraint is
already shipped.** `V3` measured that **where an individual name sits inside the top decile is not
distinguishable from chance** (holding on 45 of 69 dates) and that the **group-level** result holds
on only **21 of 69** — *"which is why it may never be stated as a standing property"*. So a regime
verdict may not modify a name's score, may not gate the hot list, and may not become a standing
claim. The only honest action is a **dated disclosure carrying the power statement**, in
`MA28-CARD-UI`'s pattern: the composite did not sort over this window; the window overlaps a
documented industry-wide factor drawdown; we cannot tell which, and here is the arithmetic
(34 years per side) that says why.

---

## MANDATE 4 — UNTOUCHED INSTRUMENTS

### MB15 — **The tick cache's `exchange` field has never been read by any study, and it is the retail axis**
**EV: HIGH (a genuinely unread field on an owned 70 M-print instrument). Trials: 2, options
(`N` 300 → 302). Prior: ~15%.**

**Measured, read-only, on three sampled payloads (NVDA 2016-05-13, NVDA 2016-09-21, AAPL
2016-12-15).** Every print carries `exchange` with **14 distinct venues**, plus `bid_exchange` and
`ask_exchange` (14 and 13–14 distinct). `O14`'s five features were `signed_volume`,
`pc_flow_imbalance`, `block_share`, `unusual_volume` and `sweep_share` — **none touches venue**.
`O10`/`O18` used `condition` codes (18, 35, 106, 0, 95 dominate) and `size`. **No study in the
corpus has read `exchange`.**

**Why it matters.** Bryzgalova, Pavlova & Sikorskaya, *Retail Trading in Options and the Rise of
the Big Three Wholesalers* (Journal of Finance 78(6), 2023) identify retail options flow through
wholesaler routing and find retail is **> 60% of total options volume**, prefers cheap weekly
options at an average **12.6% bid-ask spread**, and **loses money on average**. Bogousslavsky &
Muravyev's *An Anatomy of Retail Option Trading* extends it. **Replication status: published in the
JF, widely cited, and the loses-money direction is robust** — but the identification is a
wholesaler flag this vendor does not supply, so a venue-based classifier here is a **PROXY and must
be labelled one on every output.**

Corroborating shape already visible in the cache: **`size == 1` is 24.4%–31.6% of prints** and the
median print is 3–5 contracts, consistent with a retail-dominated tape.

**The conditioning caveat, named per the commission's instruction.** The cache is **alert-days
only** — 186 symbols, 1,574 dates, and the alert screens on unusual volume versus open interest and
low IV. Retail share is mechanically higher on high-volume days, so this sample is **selected
toward the retail-heavy tail**. Two consequences the register must carry: a null may be **range
restriction** rather than absence, and a positive is measured on the part of the distribution the
alert already selects and **does not generalise to ordinary days**. `O10` measured the harder
version of the same limit: the next session is cached for **0 of 3,870** trades and the exit day
for **0 of 3,870**.

**Kill condition, and it fires before any outcome is read.** The venue → retail mapping must be
validated against an external benchmark first: it must reproduce the published retail share on the
pooled cache to within ±15pp of BPS's ~60%. **If it cannot, the arm is VOID before scoring.** That
is the strongest available kill, because it tests the instrument rather than the hypothesis.

**Register.** Fix the mapping and the validation before any outcome; both halves; the
range-restriction control (alert-day retail-share distribution against `O10`'s control book) as a
gating control run and read in a **separate pass** — `O10`'s own process defect, not repeated.

---

### MB16 — VPIN is CONTESTED, and the dispute names which version to build
**EV: MEDIUM. Trials: 1, options. Prior: ~10%.**

Easley, López de Prado & O'Hara's VPIN is proposed as an order-flow-toxicity measure. Andersen &
Bondarenko's critique is specific and it is the useful part: against a benchmark using quotes and
trades, the **Bulk Volume Classification** scheme is **inferior to a standard tick rule**, and VPIN
predicts volatility largely because rising volatility induces systematic classification errors in
BVC. The authors dispute the characterisation. **Replication status: CONTESTED, and the contested
component is the classifier.**

**That is exactly the component this project already does properly.** `O14` built a quote-based
Lee–Ready classifier and measured it classifying a median **98.54%** of eligible prints — and
found and fixed a real defect in it (the tick test needs the previous *different* price). So the
only version worth building here is **quote-classified VPIN**, which the critique does not reach.

**Kill condition, before scoring.** If quote-classified VPIN correlates above **0.90** within date
with `O14`'s already-null `signed_volume` or `unusual_volume`, it is those features renamed and the
arm is **withdrawn before any outcome is read** — the `U2` `skew_25d` precedent, where a
separately-named arm turned out to be an existing column's negation and was killed before the
register rather than after the verdict.

---

### MB17 — Tier C's 420 small caps: the one question uniquely answerable there
**EV: MEDIUM-HIGH. Trials: 1, equity. Prior: ~25% it returns an interpretable verdict at all.**

**What is unique.** `V6-B` measured its survival effect **strongest in the smallest quintile**
(−14.287pp) and weakest in megacaps (−3.787pp). `P1S0` measured the optionable subset **worse
early** — over exactly the 2016–2020 window. Tier C supplies **982 units of 2016–2018 chain data
for 420 optionable names the breadth miner never covered**, which are small by construction (2.6 MB
per symbol-year against a megacap's 8.8 MB). That is the **only** population where the composite's
dead window, the small-cap end of `V6-B`'s gradient, and options existence intersect.

**What is answerable and what is not.** Answerable: *does the composite sort the small optionable
names over 2016–2018, where the record says it should be strongest and where it also says the
optionable subset is weakest?* Not answerable: anything requiring 2019+ (Tier C is 2016–2018 only),
and anything requiring a name to be in the panel before its debut.

**Two hard requirements from the census, both mandatory before any number.** Filter
`pre_panel_history` — **28 of 982 units across 14 symbols** carry another company's option data
with `panel_first_year` stamped on every row — or resolve those symbols against a point-in-time
identifier. And treat `empty_vendor` (278 units) as a vendor fact, never as a market fact.

**Kill condition.** `MB13`'s arithmetic applies with less data: if the covered small-cap
cross-section has fewer than **16 dates per half** (`S18`'s floor) or its power control — the
panel's own known-real signals on the arm's actual rows, per `MA31`/`MA32`'s three-population
method — fails a t = 2.0 bar, the result is **UNDERPOWERED, not null**, and the population is
closed to further equity registers.

---

### MB18 — The S23 valuation panel's genuinely unread object: **the implied-growth expectations gap**
**EV: HIGH — the cheapest genuinely-new equity hypothesis in this audit. Trials: 1, equity.
Prior: ~15%.**

**Measured, read-only, on `panel_s23_fairvalue.pkl`:** 108,241 rows, **69 dates, 2,441 names,
2009-01-15 → 2026-01-28**, with `implied_growth` at **100.00%** coverage and `base_growth` at
**100.00%**. Both are solved from price and filed fundamentals **as of the date** — point-in-time.
The gap `implied_growth − base_growth` is *how much more growth the price demands than the company's
own recent trajectory*: a reverse-DCF expectations measure, and nothing in this project has ever
scored it.

**Mechanism.** Expectations errors rather than risk: prices embed a growth path, the path is
systematically too optimistic where it is most extrapolated, and the error is what earns. The
project's own measurement of the level agrees — `implied_growth` has median **0.164** against
`realized_growth`'s median **0.061** on the 81,633 rows carrying both — and
`calibration.implied_growth_realization` already exists to report it.

**The look-ahead trap, named before anything is built.** `realized_growth` is **forward** three-year
growth. It may **never** enter a signal; it is an ex-post attribution only. Any arm that touches it
is void by construction, and the register must pin that at source — the `MA31` precedent, where
`dividends.spot_from_parity` fed back as the spot would have made the arm identically zero and
nothing would have raised.

**The costume risk, named with its own kill.** A reverse-DCF implied growth is monotone in price
over fundamentals, so it may be the `value` theme renamed. **Mandatory `C6`-style control: mean
per-date Spearman against the `value` theme, and the arm is WITHDRAWN before any outcome is read at
abs rho > 0.60.**

**Register.** The incremental-IC gate **as re-specified by `MB7`** (this is one of the six items
that gate depends on); both halves; the correlation control above run and read in a separate pass;
`implied_bounded` (a 3-state solver flag at 100% coverage) reported as a data-quality partition
rather than silently pooled.

**Inherited caveats.** The panel's `fair_value` is `S23`'s reconstruction and **not** what the live
site published on the day (`MA26-C`); and `S23` itself found and fixed the path fetching **live**
Yahoo prices to value 1999, so any re-build must assert zero network calls as `S23` now does.

---

### MB19 — MA55's lens-disagreement width is buildable, and the `w_floor` is the whole design
**EV: MEDIUM. Trials: 1, equity. Prior: ~12%.**

**Verified read-only:** all three valuation lenses are present on **80,689 of 108,241 rows
(74.55%)** — `dcf_ps` 99.87%, `comps_fv` 100.00%, `growth_ps` 74.55% — so `MA55`'s premise holds
exactly as its design record states. Its measured width distribution is p05 **0.1195**, median
**0.8777**, p95 **4.1069** — with a **maximum of 3,585**, four orders of magnitude above the
median.

**That maximum is the design.** Without a floor the arm stops being a precision-weighted
mispricing signal and becomes a **disagreement screen**, which is a different hypothesis. The
`w_floor` is a free parameter and the register must pre-commit it **and** prove the verdict
insensitive across a pre-declared ±50% band.

**Kill condition.** If the verdict moves anywhere inside that band, the arm is **VOID** — a result
that depends on a free parameter is `MA58-SEAS`'s C-DEPTH finding in a new place, where K = 5 and
K = 10 told opposite stories and only the pre-committed one carried a verdict.

---

### MB20 — MA57's one-line change now has a consumer, and it is the one construction `S3` never built
**EV: MEDIUM-HIGH. Trials: 1, equity, plus a two-column `_KEEP` change. Prior: ~20% — the highest
prior on any equity arm in this audit, and still under a quarter.**

`MA57` refuted the audit's data blocker (the export has **24 columns, both `ownername` and
`transactioncode` present, 5,636,964 rows, zero missing on all 124,181 open-market purchase
rows**) and then **correctly declined** the `_KEEP` change for having no consumer. The COVERAGE RULE's
discipline is to add source columns when the signal that needs them is added.

**Here is a consumer.** Cohen–Malloy–Pomorski's routine-versus-opportunistic insider split needs
exactly those two columns, and `MA57` already computed the split on the export: **42,537 of 87,318
(`ownername`, ticker) pairs = 48.72% routine** on all coded rows. **`S3` rejected three insider
rebuilds and none of them was this one** — `S3A` dropped the `buys` bonus, `S3B` scaled by market
cap, `S3C` split into two z-scored inputs. The routine/opportunistic split is a different
construction, and it is the one the published literature says carries the signal.

**Kill condition, and it is a coverage rule not an outcome rule.** `transactioncode` is **absent on
1,544,490 rows (27.40%)**, and a blank code can be classified neither way. Pre-commit that if the
classifiable share of the panel's own insider rows falls below **60%**, the arm is **UNDERPOWERED,
not null**, and the `_KEEP` change is reverted rather than kept for a dead consumer.

**The unflattering prior, stated because it is the record's own.** `S3` measured that the pure
indicator *"has an insider score at all"* carries a **larger** absolute t (+1.4471) than the
insider theme's own direction (−0.2259). Neither is significant; the comparison is the point, and
it should be quoted in the register rather than discovered afterwards.

**Also fix in passing (reported, not repaired):** `_KEEP["insiders"]` requests a column named
`date` that the export does not have — it is `transactiondate` — so `filingdate or date` has a
fallback that **can never fire**. `MA57` found it; it is still there.

---

### MB41 — Intraday momentum is **NOT TESTABLE HERE**, named so nobody proposes it
**EV: LOW (a disqualification, and disqualifications are cheap). Trials: 0.**

Gao, Han, Li & Zhou (*JFE* 2018) find the market's first half-hour return predicts its last
half-hour return, stronger on volatile, high-volume, recession and macro-release days, and
significant out of sample as well as in. It is a plausible thing to reach for once someone hears
"70 million prints".

**It cannot be tested here, and the reason is the instrument rather than the result.** It is an
**index/ETF** phenomenon measured on SPY half-hour returns. This project's tick cache is
**single-name options prints on alert days**; the chain cache is single-name equity options only;
and the frontier already established that **no index chain is owned** (`P6`, `NEEDS-DATA`). There
is no equity tape here at all.

Marked **NOT-TESTABLE-HERE** so it does not consume a session's reading before someone reaches the
same conclusion.

---

## MANDATE 5 — CROSS-POLLINATION FROM TIDEMARK

### MB21 — **The Boudoukh–Richardson–Whitelaw null, and S22's null is mis-specified in the direction that manufactures its result**
**EV: HIGHEST IN THE AUDIT. Trials: 0 for the diagnosis (done, below); 1, infra, for the
persistence-preserving null. Prior: ~55% that at least one horizon crosses.**

**The instrument.** BRW (RFS 2008): with a persistent regressor and overlapping long-horizon
returns, R² and long-horizon β rise **mechanically under a no-predictability null**. TIDEMARK
reproduced it on its own data and the result is stark — the actual data's R² ratio rises **more
slowly than the median of pure noise at every horizon** (3, 5, 7, 10, 15 and 20 years), so what
looks like long-horizon predictability in the famous CAPE chart is, on that test, entirely a
mechanical artifact.

**Valquo's exposure.** `S22` is the term-structure item: annualised top-decile alpha essentially
flat from 3 months to 2 years, cumulative alpha reaching +10.20% at eight quarters, classified
CONSTANT-RATE on `R(8) = 6.195` against a 6.0 bar, corroborated by *"median rank IC rises with
horizon, +0.034 → ~+0.072"*. Its null is a per-horizon `fixed_weights_null` built from
`placebo_panel`, whose method is stated in its own docstring: *"Within each rebalance date, permute
the signal columns AS A BLOCK across the names present."*

**A within-date permutation destroys the signal's time-series persistence completely — and that is
the one property BRW's artifact requires.** Measured here, read-only, on
`panel_corrected_69d.pkl` with the deployed flat 1/8 weights:

| object | lag 1 (63d) | lag 2 (126d) | lag 4 (252d) | lag 8 (504d) |
|---|---|---|---|---|
| **real composite**, per-name rank autocorrelation across rebalances | **0.5802** | 0.4859 | 0.4514 | **0.4099** |
| **`placebo_panel`**, seed 1000 / 1001 / 1002 | **−0.0011 / +0.0010 / +0.0005** | — | — | — |

(68 date pairs, median 1,548 matched names per pair; real lag-1 median 0.5718, min 0.4073, max
0.7109.)

Per theme, lag 1: **`size` 0.9915**, `capital_discipline` 0.8882, `value` 0.6981, `quality` 0.6786,
`momentum` 0.6414, `insider` 0.3152, `institutional` 0.1181. **The most persistent input by a
distance is `size` — and `X3` measured that `size` carries the composite's entire statistical
significance** while having the worst theme IC. The two facts compound in the same direction.

**So `S22`'s null is a null for a signal with no memory, applied to a signal whose memory is 0.41
at two years.** It cannot generate the mechanical rise BRW describes, and the shortfall grows with
horizon — which is precisely the axis `S22`'s headline lives on. Its `H=63` result is untouched
(no overlap, lag 1, horizon equals rebalance); everything beyond it is scored against a null that is
too easy by an unmeasured amount.

**This is product-consequential, which is why it ranks first.** `S22-DISPLAY` is `DONE — SHIPPED`
and puts the registered sentence, its caveats and the misuse warning on the hot-list card, the
per-name attribution panel and `/methodology`, including the rank-IC-rises-with-horizon
corroboration (0.0336 at one quarter to 0.0655 at two years) — the exact statistic BRW's null
predicts under no predictability.

**The fix.** Build a **persistence-preserving null**: permute each name's whole signal *time series*
(or block-permute dates) rather than permuting within dates, so the placebo retains the real
signal's autocorrelation while destroying its association with forward returns. Validate it the way
`placebo_panel` was validated — assert the placebo's per-name lag-k autocorrelation matches the
real signal's within tolerance, and assert its association with `fwd_ret` is nil. Then re-run
`S22`'s per-horizon comparison against it.

**Trial accounting, and it needs deciding explicitly rather than assumed.** Constructing and
validating the null is **infrastructure** — 1 infra trial on the `HACFLOOR` / `X7RECON` precedent,
and infra `N` gates no published claim. Re-scoring `S22` against it is a **re-measurement of a
landed claim on a new instrument**, which the discipline explicitly permits (a re-open needs new
data, a new instrument, or a new design — this is a new instrument). It is not a new search and
should not be charged as one, but the register must say so before running rather than after.

**Kill condition, pre-committed both ways.** If the persistence-preserving null's H=504 alpha floor
lies **below** `S22`'s observed value, `S22` stands, the record is strengthened, and the item closes.
If it lies **above**, `S22-DISPLAY`'s two-year copy must be **withdrawn or re-scoped**, and the
register must commit to that withdrawal in writing before the number is read. Without that clause
this becomes an invitation to reinterpret.

**What it does not say.** It does not say `S22` is wrong. It says `S22` has never been tested
against the null that its own headline shape most requires, that the null it used cannot produce
that shape, and that the gap between the two is measured at 0.58 falling to 0.41 rather than
argued.

---

### MB22 — Port TIDEMARK's effective-n / required-n gate, so every register states its MDE before running
**EV: HIGH. Trials: 1, infra. Cost: ~1 session.**

**What TIDEMARK has that Valquo does not.** Valquo has `statistics.effective_n(n, rho)` (an AR(1)
closed form) and, in the options lane, `R3`'s design effect scored against a **shuffled null**
(deff 2.1837 against a null p95 of 1.1898 — and `R3`'s own lesson, that a raw design effect near
1.8 arises from pure sampling error and must never be quoted without its null, is already learned
here). What Valquo does **not** have is the last step: the conversion from available observations
to a **required-n bar**,
`required independent observations = ((sqrt(2 ln N) + z) / effect)^2`,
measured per series against a simulated no-predictability null carrying that series' **own fitted
persistence**.

**Which Valquo claims change status under it.** `MB13` is the demonstration: the regime family goes
from "open and tempting" to **NOT PERMITTED**, with the number 34.2 years attached. `V6`, `S19` and
`V6-B` each computed an MDE by hand in their own registers, inconsistently and after the fact; this
makes it a standard field. `MA58-SEAS`'s three-population power decomposition is the same
instrument built ad hoc for one item.

**Validation, borrowed intact.** TIDEMARK's own gate reproduces its charter's power table exactly
(IR 0.20 → 196.0 against a printed 196; IR 0.30 → 87.1 against 87), which is the positive control
any port should reproduce first.

**Kill condition.** None — it is infrastructure and infra `N` gates no published claim. But it must
ship with TIDEMARK's own recorded deviation attached: `POWER_GATE.md` §5.1 records that the
validation its pre-registration asked for **could not be run**, because the column it was to be
checked against is `n/h` (non-overlapping window count) and not a design-effect quantity at all —
two different quantities sitting in adjacent columns of one table. A port that re-creates that
comparison re-creates the error.

---

### MB23 — Port and verify the Hodrick (1992) 1B estimator as a **cross-check**, not a replacement
**EV: MEDIUM. Trials: 1, infra. Cost: ~1 session.**

TIDEMARK verified 1B against Wei–Wright's published Monte Carlo to fixed tolerances — **23 cells,
max abs deviation 0.016, mean 0.007 at alpha = 0, the only case 1B is valid for** — after finding
its own first implementation wrong (it summed regressors while keeping the h-period residual, which
is not 1B, and returned t ≈ 0.3 at every horizon against a bootstrap p ≈ 0.018). Post-fix, the three
instruments agree: Hodrick ≈ 2.5, design-effect-adjusted OLS ≈ 2.3, bootstrap consistent.

**Which Valquo claims change status: honestly, probably none at H = 63** — there is no overlap
there and the HAC lag is 1. The claims genuinely exposed are `S22`'s long horizons, where the HAC
lag runs to 7 and the overlap is severe. **So this is `MB21`'s companion instrument rather than an
independent item, and it should be run with it or not at all.**

**Kill condition.** If Hodrick and Newey–West agree within 10% on the shipped H = 63 statistics, the
port is recorded as a validated cross-check and **no claim moves** — which is the expected and
desirable outcome.

**The correction that must travel with it.** TIDEMARK's `POWER_GATE.md` §5.2 records that its
pre-registered cross-check criterion was **misspecified** — it asked for the 97.5th percentile of
abs t to sit within 10% of 1.96, which is the wrong quantile, and the rule **failed on the verified
case**. The corrected statistic is the rejection rate against its nominal 0.05. A port that copies
the criterion instead of the correction ships a rule that flags known-good cases.

---

### MB24 — **Data flowing from TIDEMARK: OUT OF SCOPE, and here is the fusion register I am declining to propose**
**EV: N/A — a deliberate refusal. Trials if ever run: 1 in EACH counter.**

The commission requires that any TIDEMARK series conditioning any Valquo quantity comes with a
fusion register or is marked out of scope. **I mark it out of scope**, for a reason that is
arithmetic rather than procedural.

**Why.** The only plausible fusion is a rates or credit regime series conditioning the equity
composite. `MB13` measures that Valquo has **no power for a regime contrast at all** — 34.2 years
per side against 17.3 available. Importing a conditioner for a question that cannot be answered
buys nothing and costs a trial in **both** books, permanently: TIDEMARK's `TRIALS.md` §5 forbids
revising `N_booked` downward, so the charge there is irreversible, and it would raise the critical
value in a project that has already ruled Phase 2 **NOT PERMITTED**.

**What the register would have to contain, recorded so a future session does not have to
reconstruct it.** (1) The trial charged in both counters, and Valquo's `unified` domain — declared
in `research_log.DOMAINS` and reading **zero** — is the correct home, which would make it the first
row ever charged there and would force `R4`'s permanent residual to be decided. (2) TIDEMARK's
barred list inherited whole: `us_equity_caey` is **BURNED** as its trial #0 and demoted by
`PREREG_ANCHOR_SELECTION.md` because its percentile is partly a clock. (3) The display-versus-feed
line: FRED series are public domain and may both feed and display; **Case-Shiller (S&P copyright,
explicitly not redistributable), NAREIT (terms unverified) and Ken French may not be displayed
raw**, only as derived statistics.

---

## MANDATE 6 — TIDEMARK AS A SURFACE

### MB25 — The integration, designed: a linked page, derived statistics only, and one non-vacuous test
**EV: HIGH (Don has asked for it; it is a product item with no research risk). Trials: 0.
Cost: ~1 session.**

**Lane: app-fixer** (`valuation/web/`). Not the edge lane — nothing here touches a verdict.

**Form: a linked page at `/tidemark`, not a tab inside the hot-list surface.** The two projects have
different verdict grammars and different denominators; a tab implies they are one product, and a
reader who averages a Valquo statistic with a TIDEMARK one has been misled by the layout.

**Files.**

| file | role | precedent |
|---|---|---|
| `valuation/web/tidemark_surface.py` (new) | owns the copy and the derived statistics; nothing else may hold a TIDEMARK string | `score_confidence.py`, `hold_horizon.py`, `accounting_risk.py` |
| `valuation/web/templates/tidemark.html` (new) | render only | `methodology.html` |
| a route in `valuation/web/app.py` | serve it | the existing `/methodology` pattern |
| `tests/test_tidemark_surface.py` (new) | the pin, below | `tests/test_hold_horizon.py` (19 tests, fails if either side is reworded) |

**What crosses the boundary — and TIDEMARK's own design already makes this cheap.** Only derived
statistics: **percentile, episode count, effective n, band half-width, tier label, refusal reason,
vintage, market and anchor names.** Verified read-only against the generated
`dashboard/index.html`: its `bignum` elements are percentiles and `±` band half-widths, its cards
carry tier captions and refusals, and **no raw series level appears anywhere on the page**. The
builder's own docstring states the rule — *"No forward-return numbers. None."* — and the two bands
it does show are `SE(p) = sqrt(p(1-p)/n_eff)` and `1.96/sqrt(episodes)`, neither of which requires a
licensed value. **So the licence constraint is satisfied by TIDEMARK's construction, which is the
cheapest possible compliance argument and should be cited as such.**

**The captions ship VERBATIM**, on the `V3`/`hold_horizon.py` precedent: every sentence appears
word-for-word in the source document and a test fails if either side is reworded.

**The explicit copy the commission requires**, in TIDEMARK's own words rather than a paraphrase:
*"NO PHASE-2 QUESTION MAY BE ASKED ON THIS DATA … the best-placed market has 82 of the 155
independent years required, and the worst has 25."* Plus its more useful inverse — the edge would
have to run at IR 0.41 to 0.74 for this data to detect it, against a 0.2–0.4 plausible range.
**A dashboard shipped without that sentence reads as a signal.**

**The one test that pins "no raw series reaches the payload", and why an allowlist alone is not
enough.** Name it `tests/test_tidemark_surface.py::test_no_licensed_level_reaches_the_payload`. It
has two halves: an **allowlist** of emitted keys (`market`, `anchor`, `percentile`, `episodes`,
`n_eff`, `band_sigma`, `tier`, `refusal`, `as_of`) asserting the payload contains nothing else; and
a **positive control** — feed the builder a fixture whose series level is a distinctive sentinel
(e.g. `123456.789`) and assert that string appears nowhere in the rendered HTML. The allowlist can
pass vacuously if the builder emits nothing; the sentinel is what makes it a measurement. That
distinction is this project's own most-repeated test defect (`V6`'s C8 reading a column name the
panel does not have; `MA5`'s guard firing on its own documentation; `MA23`'s stale-path guard blind
to the import syntax the codebase writes).

**Kill / staleness condition.** TIDEMARK's artifact carries a vintage (`2026-08-17`). If it is older
than a pre-committed number of days, the page renders the vintage and a staleness note **instead of**
the number — the `index_track.gate_state()` pattern, where every unrecognised outcome fails toward
"not passed" rather than toward a claim.

---

### MB26 — The one thing that must NOT ship: a combined verdict, or an unlabelled pair of denominators
**EV: MEDIUM (it prevents a specific, likely misreading). Trials: 0.**

Valquo's register stands at **549 trials** with a critical value of **3.3031** (equity) / **3.3775**
(options). TIDEMARK's stands at **66 trials** with **2.89**. A page showing both projects' outputs
without naming both denominators invites a reader to compare or average statistics that were never
measured against the same bar. **Both `N`s and both critical values go on the page**, and no
statistic from one project may appear inside a sentence about the other.

---

## MANDATE 7 — THE FACTORY, ROUND 2

### MB27 — **Board state is derivable, the derivation is already written down in prose, and nobody ran it**
**EV: HIGH. Build cost: ~half a session. False-alarm risk: designed to zero.**

**The evidence is a file in the repo root.** `ma_in_flight.json` exists to answer *"which items are
being worked RIGHT NOW"*. Its own `_meta` carries: the purpose, the method (*"measured … from local
branches ahead of origin/main plus `git worktree list`"*), a `how_to_refresh` command, an honest
caveat that uncommitted work is invisible to it, and a correction recording that the brief which
commissioned it named five in-flight items and **none of the five had a commit anywhere**.

It is dated **2026-08-14**. It lists `MA13`, `MA19`, `MA36`, `MA37`, `MA15`, `MA16`, `MA20`,
`MA35`. **Every one of them is now `DONE`.** The file is five days stale and 100% wrong, and it
contains its own refresh instructions.

**That is `MA59`/`MA60`'s lesson one level up.** Those items replaced `check_lanes.py`'s hand-typed
import dictionary with a derived graph after measuring the literal at 13 keys / 40 edges against a
real 118 / 546. The same disease is now in the board state: **a hand-typed snapshot of something
git already knows.**

**Proposal: `scripts/board_state.py`, deriving all four ingredients with no hand-typed input.**

| ingredient | derivation | value today |
|---|---|---|
| in-flight branches | `origin/worktree-*` not an ancestor of `origin/main`, plus local branches ahead | **0** |
| claimed items | ledger status cells matching `IN ?PROGRESS` | **2**, and **both are stale** (`B13` says so itself; `D11`'s handoff says the miner is idle) |
| handoff freshness | each `HANDOFF_*.md` mtime against the newest commit touching it | reported |
| stale locks | `.git/index.lock` and worktree locks, with age | the six-day-stale lock incident is a fourth ingredient at zero extra cost |

**The cry-wolf rule, honoured explicitly.** `MA21` declined a proposed warning because it would fire
on 41 legitimate rows and be switched off inside a week. **This script must not warn.** It emits a
report with four counts and **exits 0 always**. The **only** failing assertion is one that cannot
cry wolf: *the generated board file is older than the newest branch tip it claims to describe.*
That is a staleness fact about a generated artifact, not a judgement about anyone's work — the same
shape as `MA13`'s committed-literal pin on `by_domain`, which is checkable, diffable and cannot
produce a false positive.

**Kill condition.** If over four weeks the derived board and the hand-maintained one disagree on
fewer than two items, delete the generated file and keep the hand one. A second copy of a fact that
never drifts is worse than one copy.

---

### MB28 — The staleness monitor **already exists and has no clock**
**EV: MEDIUM-HIGH. Build cost: one scheduled-task registration — and it is Cowork's, not this
lane's.**

`scripts/checkout_drift.py` is built, documented and tested (`tests/test_checkout_drift.py`). Its
own header records the measurement that motivated it: the shared checkout was **1 commit ahead and
514 behind `origin/main`**, and the one local commit — the dated `PT-WRITER` failure note answering
an open ledger row — had been stranded since 2026-08-10. It deliberately reports and repairs
nothing, because *"a guard that silently repairs is a guard whose failures are invisible."*

**Measured: nothing invokes it on a schedule.** Its only caller is `check_drift.bat`, a manual
double-click. No workflow in `.github/workflows/` (`auto-scan.yml`, `land-agent-branch.yml`,
`track-backup.yml`, `track-row.yml`) touches it.

**So the alarm for "the relay dropped a packet" is itself gated on a human remembering.** That is
the mandate's thesis, again, in the guard built to answer it.

**The fix cannot live in CI, and the reason is structural rather than a preference.** It measures a
**local** checkout, which no hosted runner can see; and `MA11`'s auto-land policy **refuses any
branch touching `.github/`**, so a workflow change needs a human anyway. The honest fix is a
**Windows scheduled task on Don's machine** writing `--json` output to a fixed path the next
session reads — **Cowork's lane** under the tool-routing rule, and it should be routed there
explicitly rather than left as a wish.

**False-alarm risk: low.** It reports counts and exits non-zero only on a measured drift, which is a
fact rather than a judgement.

---

### MB29 — The prompt receipt, and this audit is its own example
**EV: MEDIUM. Build cost: a convention plus ~5 lines inside `MB27`'s script.**

**The failure named by the commission:** the manager's roadmap listed a lane as in flight *on an
intention rather than a pasted prompt*.

**The cheapest mechanization with teeth is one the project already runs elsewhere.** The register
discipline requires a `PREREG_*.md` committed **ALONE** and a strict ancestor of every measurement
commit — precisely so that intent is provably prior to result. Apply the same shape one level up:
**a lane's first commit on its branch is its prompt, committed alone, as `PROMPT_<lane>.md`.**
`MB27`'s script then reports, per in-flight branch, whether a `PROMPT_*` blob exists at its base.

**Evidence it would have bitten, from this session.** At session start `git status` read
`?? PROMPT_audit4_master.md` — **audit #4's own commission was untracked**, so at the moment this
audit began, the instruction defining it was invisible on `origin/main` and no other lane could
have discovered what was being worked. The seven existing `PROMPT_*.md` files in the root are the
convention already half-observed; this makes it complete and checkable.

**False-alarm risk: none.** It is a reported count, not an assertion.

---

### MB30 — What NOT to build, named so nobody proposes `MA21`'s sibling
**EV: N/A — a refusal. Trials: 0.**

Do not build a warning on `src=auto` rows, on blank verdict cells, or on ledger rows lacking a
handoff. `MA21` already declined the blank-verdict warning with a measurement: **41 of 230 `DONE`
rows carry a blank verdict and every one is legitimate**, because `build_ledger.py`'s own reading
guide says blank means *"not measured, or measured and reported in different words — never 'we
don't know'"*. A guard firing on 41 legitimate rows plus every prose verdict would be switched off
inside a week. The substitute `MA21` shipped instead — pinning the vocabulary literal against the
documented list so two copies of one fact cannot drift — is the correct shape and is already in
place.

---

## MANDATE 8 — INSTRUMENT CALIBRATION AGE, ROUND 2

*Deliver the staleness map; do not recalibrate.*

### MB31 — The staleness map
**EV: HIGH (it is the map every other item quotes from). Trials: 0.**

| instrument | calibrated at | today's `N` | shipped value | honest value at today's `N` | status |
|---|---|---|---|---|---|
| **HLZ hurdle**, equity | `N` = 224 | **234** | 3.2898772171176964 | **3.3031261300040304** | **STALE** — verdict unchanged (`clears_hlz_hurdle: false`); shortfall 0.6700 → **0.6832** |
| **HLZ hurdle**, options | — | **300** | — | **3.3775086897463940** | quote this for any options claim |
| **theme IC t floor** | `N` = 84 | 234 | 2.7072 | unchanged at 84, 129 and 224 | **insensitive so far** — re-derivable from banked draws |
| **long-short naive floor** | `N` = 84 | 234 | 2.1437 | unchanged at 84, 129 and 224 | **insensitive so far** |
| **long-short HAC floor** | `N` = 84 | 234 | 2.2837 | unchanged at 84, 129 and 224 | **insensitive so far** |
| **PBO p5 floor** | `N` = 84 | 234 | 19.667% | unchanged at 84, 129 and 224 | **insensitive so far** |
| **top-decile alpha margin** | `N` = 129 | 234 | **1.8629pp** | **DUE** | moved once already (1.9532 → 1.8629 between 84 and 129) |
| **top-decile alpha HAC floor** | `N` = 224 | 234 | **2.0540** | **DUE** | moved once already (2.2913 → 2.0540 between 129 and 224) |
| **Deflated Sharpe floor** | `N` = 224 | 234 | 0.6637 | **STALE BY CONSTRUCTION** | `sr0` is a function of `N`, so **every** draw moves at every `N` |
| **Deflated Sharpe, the statistic** | `N` = 224 | 234 | 0.7863 | **STALE BY CONSTRUCTION** | same channel |

**Which recalibrations are DUE, and why exactly these two.** `MA19` established the mechanism: a
p95 over 100 draws is set by the fifth and sixth largest values, so **whether a floor moves depends
not on how many draws flip but on where they sat**. The two floors that have already moved once are
the two whose flipped draws sat in the tail — the alpha HAC floor's flipped draw ranked **4th of
100**, which is exactly why it moved when the long-short floors did not. **Those two are the
candidates for a third move and they are the two the shipped product's headline is judged against.**

**The good news, and it makes the recalibration cheap.** `X7RECON` banked the per-draw
`(margin, se)` rows precisely so the adopt set at any `N` is arithmetic, and `MA19` re-scored only
**three** draws in ~400 seconds rather than re-running a 3.4-hour sweep. So the due recalibration is
a bounded job, not a sweep — and `RUN_RULES` rule 9 is the reason it is bounded.

**Which are provably insensitive: none.** Four floors have not moved across a 2.7× change in `N`,
and `MA19` explained why, but *"has not moved"* is not *"cannot move"* — session 12 recorded that
their survival was *"luck, not design"*, and on the alpha HAC floor the luck ran out. **Report them
as insensitive-so-far and never as invariant.**

---

### MB32 — Which `CLAUDE.md` comparisons now quote a bar at the wrong `N`
**EV: MEDIUM (free; it is a documentation correction). Trials: 0.**

The `X7 CALIBRATED THRESHOLDS` table's authoritative column is headed **`N` = 224 (QUOTE THIS)**
and is now one denominator behind at `N` = 234. Nothing in it changes a verdict, but two specific
sentence shapes are at risk and both are the defect `MA19` already found once:

1. **Any sentence pairing a numerator at one `N` with a floor at another.** `MA19`'s example is on
   the record — *"0.8674 vs the 0.7216 floor"* pairs an `N` = 116 Deflated Sharpe with an `N` = 84
   floor. The Deflated Sharpe moves at **every** `N`, so this shape recurs automatically unless the
   text says which `N` both sides are at.
2. **The two DUE floors above** (1.8629pp and 2.0540), which are quoted in `S10`'s, `V2G`'s and
   `MB8`'s reasoning. They are correct at `N` = 224 and should carry that label until re-derived.

**Action: label the column `N` = 224 rather than "QUOTE THIS", and add one line pointing at the live
count.** Zero trials.

---

### MB33 — The artifact–log drift is live at 10 / 8 / 1, and that is the system working
**EV: LOW-MEDIUM (a "do not act" finding, which is worth stating). Trials: 0.**

`BACKTEST_RESULTS.json` was generated **2026-08-14T02:23:56** and carries
`by_domain {equity: 224, options: 292, infra: 14}` against a live `{234, 300, 15}` — a drift of
**10 / 8 / 1**, total 530 against 549.

**This is correct behaviour, not a defect, and `MA21` enforced it in the only direction that cannot
cry wolf**: trials accumulate, so the artifact may **lag** the log and may never **lead** it. It
lags.

**Do not re-run for this reason alone.** A re-run costs 20–40 minutes, and this project's own memory
records that a run **overwrites the tracked repo-root artifact** — so a re-run from a dirty or
non-canonical tree is a live way to make the canonical file worse. Re-run when a claim's
relationship to its bar would change; here, none does (`clears_hlz_hurdle` is `false` at both 224
and 234).

---

## MANDATE 9 — SIMPLIFICATION, ROUND 2, AND THE PIONEER PAGE

### MB34 — 64 merged `worktree-*` branches are deletable, with a one-line safety proof
**EV: MEDIUM (pure hygiene, zero risk). Trials: 0.**

Measured: `git branch -r --merged origin/main | grep -c worktree-` = **64**; `--no-merged` returns
only the two `rescue/*` refs. **Every one of the 64 is an ancestor of `origin/main`**, so deleting
the ref removes no reachable commit and no history. Total remote refs: 68.

**Safety argument:** ancestry is the proof, and it is checkable in one command before each delete.
This is the one deletion in the audit with literally no downside.

---

### MB35 — The two `rescue/*` branches: **tag first, then delete** — and the reason is the record's own
**EV: MEDIUM. Trials: 0.**

| ref | commits ahead | content |
|---|---|---|
| `origin/rescue/main-41d7b12` | 1 | `41d7b12` — *"PT-WRITER 2026-08-10: cannot write row — mechanism for daily prices not documented in repo"* |
| `origin/rescue/wip-main-c4a3939` | 2 | the same commit plus `d39ec84`, a working-tree snapshot touching only `HANDOFF_STATUS.md` and `LAZY_PRICES_COVERAGE.md` |

`PT-WRITER` closed `DONE` on 2026-08-18. So both refs are relics.

**The safety argument is the interesting part.** `41d7b12` is the dated failure note that
`CLAUDE.md` cites as the **decisive evidence** for what blocked `PT-WRITER` — *"the correct
behaviour and the answer to the row"* — and it is the only object carrying that message. Deleting
the ref makes the commit unreachable and eventually collectable. **So: create an annotated tag
(`archive/pt-writer-refusal-2026-08-10`) pointing at it, verify the tag, then delete the branch.**
A tag is a permanent ref at essentially zero cost, and this project's own memory records the near
miss of deleting something "because history preserves it" without checking that history does.

`d39ec84` is a snapshot of two generated/handoff files and needs no tag.

---

### MB36 — Documentation: 258 root entries, and the move is a **rename with one real hazard**
**EV: MEDIUM. Trials: 0. Cost: one commit — but read the hazard first.**

Measured at the repo root: **68 `PREREG_*.md`, 48 `HANDOFF_*.md`, 12 `VALQUO_*.md`,
7 `PROMPT_*.md`, 2 `DESIGN_*.md`**, 258 entries in total, 168 markdown files. Repo size 28 MB.

**Do not delete any of them.** The `PREREG_*` files are the register's evidence and the whole method
depends on them being committed, dated and readable — and the repo is **public** as of 2026-08-16,
so they are now the credential rather than the paperwork. The `HANDOFF_*` files are `RUN_RULES`
rule 2's deliverable. The `PROMPT_*` files are `MB29`'s convention already half-observed.

**What is proposable: move them, as git renames, into `register/` and `handoff/`.** Precedent
`MA23`, which moved twelve modules as renames with nothing deleted and a test pinning the resulting
boundary.

**And `MA23`'s own correction must be honoured, because it is the reason this is a proposal and not
a chore.** `MA23` found, after the fact, that its move did **not** achieve one of its three stated
motivations — the deploy image was unchanged, because `.dockerignore` already excludes `*.md`. So a
documentation move buys **readability only** and must not be sold as anything else.

**The concrete hazard, and it is specific.** `valuation/web/research_record.py` — the public
research page — **lists the pre-registration documents by globbing the filesystem**, not from a
manifest. A move that does not update that glob **in the same commit** silently empties the public
page's register list, and nothing would raise. That is the `MA23` merge collision in a new place
(two branches touching different files, a clean merge, and a broken import), and it is why this item
carries a hazard rather than a checklist.

---

### MB37 — Keep the `PROMPT_*` files, and say why
**EV: LOW. Trials: 0.**

Seven of them, each a commission that produced landed work. They are the evidence for the receipt
convention `MB29` proposes to make standard; deleting them would delete the case for it. They are
also the only artifact in the tree that records *what was asked* as distinct from *what was found*,
which is exactly the asymmetry the register exists to preserve.

---

### MB38 — PIONEER, RANK 1 — **HYPOTHESIS**: publish the *denominator*, not the register — because the register already ships
**EV: HIGH for a personal/portfolio site. Trials: 0. Cheapest first artifact: one paragraph and
three numbers on a page that already exists.**

**Correcting the commission's premise, which is the useful part.** The commission proposes
"publishing the register method itself" as a novel artifact. **Half of it already ships.**
`valuation/web/research_record.py` (item `V4`) serves `/research`, sourced from `RESEARCH_LOG.md`
through **the same parse that produces the Deflated Sharpe's denominator** — deliberately, so the
page cannot become a second version of the truth. Its rule is absolute and enforced by
`withhold()` plus a test: **no performance figures, not results, not thresholds, not effect sizes.**
The repository itself went **public on 2026-08-16** under MIT.

**What exists in the world (searched).** ClinicalTrials.gov (NLM/FDA, since 2000) and the AEA RCT
Registry are the standard pre-registration registries for medicine and economics. **There is no
standardised public pre-registration registry for quantitative-finance backtests.** Deflated-Sharpe
and PBO calculators do exist as open source (`pypbo`; the `ml4t-diagnostic` package's
`effective_number_of_trials()`; browser tools) — but those compute an effective number of
**strategies tested**, inferred from a correlation structure. **None of them is a maintained, dated,
adversarially-audited count of the trials one project actually ran.**

**So the genuinely new artifact is the denominator, not the register.** A public statement of the
form: *this project has run 549 pre-registered trials — equity 234, options 300, infra 15 — the
multiplicity-corrected critical value that count implies is √(2·ln 234) = 3.3031, and the headline
long-short statistic is 2.6199, which **does not clear it***. As far as this search establishes,
no retail research record publishes its own honest denominator, derives its own hurdle from it, and
reports its own headline failing that hurdle.

**Why it is publishable when the alpha figure is not — the narrow, defensible opening.** The
withholding rule exists because of the public posture and because the Sharadar licence forbids
commercial use of the data *"or any derivation"*. **A trial count is not a derivation of vendor
data**; it is a count of this project's own decisions. The hurdle is arithmetic on that count. The
PASS/FAIL is a comparison of two numbers, one of which is already withheld — so the honest form
publishes **N, the hurdle, and the verdict word**, and continues to withhold the statistic itself.

**Cheapest first artifact:** one paragraph and three numbers appended to `/research`. No new
surface, no new data, no trials, one session.

**Kill condition.** If `withhold()` cannot be made to pass a trial count and a derived hurdle
without also passing a performance figure, **do not ship** — the posture wins, and the failure is
itself worth recording. Test it against the existing assertion that the rendered page contains no
performance figure before writing any copy.

---

### MB39 — PIONEER, RANK 2 — **HYPOTHESIS**: the disclosure-card class `MA28` opened
**EV: MEDIUM-HIGH. Trials: 0 for the strongest candidate. Cheapest first artifact: a second card
on `accounting_risk.py`'s pattern.**

**What `MA28-CARD-UI` actually established is a product class, not a statistic.** A card whose gate
was a **crash rate rather than alpha**; whose thresholds this project **did not fit** (Beneish
−1.78 and Altman 1.81 are published values); whose copy carries a **measured rule about its own
instability** — *"the base rate is era-dependent, kept 0.3413% early against 1.3595% late, so quote
the ratio and both rates, never the difference"*; and whose banned phrases are asserted against the
**rendered payload** rather than the source. That combination — a published-threshold risk
disclosure that states the conditions under which its own number misleads — is not a common product
shape.

**Three measured, un-carded candidates already in the record:**

| candidate | measured | trials to card it |
|---|---|---|
| **`S28`'s own distribution of the headline** — the published +7.17%/yr alpha is the mean of 69 quarterly draws of which **20 are negative (28.99%)**, median +1.41% against a mean +1.79%, **worst −6.83% (2016-01-20)** | already shipped in `construction.top_decile_alpha_distribution` | **0** |
| `V6-B`'s survival gradient (`MB10`) | −14.287pp smallest quintile to −3.787pp megacap | 0 |
| `P1S0`'s optionable partition (`MB11`) | worse early, better late, at all three horizons | 0 |

**The first is the strongest and nobody has proposed it.** A card stating that the product's own
headline was negative in nearly three quarters of every ten, with the worst quarter dated, is the
most honest disclosure this project could ship — and `S28` already computes it, ships it in the
canonical artifact, and pinned it as **reporting-only** with a test that fails if any threshold ever
branches on a distribution field. **The statistic is built, guarded and unused.**

**Kill condition** (inherited from `dip_posture.py`'s design): if the copy cannot pass a
BANNED-phrase assertion against the **rendered** payload, do not ship it. Rendering is where copy
leaks.

---

### MB40 — PIONEER, RANK 3 — **HYPOTHESIS**: an open effective-n calculator, and why it ranks last
**EV: LOW-MEDIUM. Trials: 0.**

TIDEMARK's instrument — design effect measured against a **simulated no-predictability null carrying
the series' own fitted persistence**, converted into required independent years at a
multiplicity-corrected critical value — is, on this search, not packaged anywhere. The existing open
tools compute effective **trials** (strategy clustering: `effective_rank`, Marchenko–Pastur,
clustering); this computes effective **observations** (time-series clustering). The distinction is
real and it is the one that bites retail backtesters, who overwhelmingly quote raw n.

**Cheapest first artifact:** one self-contained HTML page taking `(n, horizon, fitted rho, trial
count, target IR)` and returning *"you need X independent years; you have Y."* TIDEMARK's dashboard
is already exactly this shape — a single file, no external stylesheet, font or script, working with
no network — so the template exists.

**Why it ranks last, stated plainly.** It is a tool, tools need users, and this project's audience
is one person plus recruiters. Its genuine value is **internal** and is already captured by `MB22`,
where the same arithmetic becomes a standard field on every register. Ship `MB38` first; this only
if the method is written up.

---

## BUGS FOUND (`RUN_RULES` Part A rule 3 — including outside this lane)

### MB42 — A gate suite is GREEN in CI and RED on the only machine that owns the data, and the cause is a path separator
**Lane: options bot / data miner. Trials: 0. Cost: one literal.**

The audit's sanity check ran every suite by exit code, as `RUN_RULES` 0.1 requires. **115 suites,
114 passed, 1 failed** — `tests/test_o21d2_alternative_pnl.py`, at
`test_the_real_harvest_freeze_resolves_when_mounted` (20 of its 21 assertions pass).

**Diagnosed, not guessed.** The test asserts four things about the resolved harvest provenance.
Three pass — `pinned` is `True`, `hash_mismatches_at_copy` is `0`, `manifest_sha256` is 64 chars.
The fourth is:

```
assert prov["frozen_from"] == "D:/thetadata/chains"      # forward slashes
actual:  'D:\\thetadata\\chains'                          # backslashes
```

**It is a path-separator literal, not a data problem.** The freeze is intact:
`D:\thetadata\freeze_rawpull_2026-08-18`, `pinned` true, zero hash mismatches, manifest sha256
`ee6d38e5ff58…f000`.

**The part that makes it worth reporting rather than just fixing.** The test opens with a mount
guard — *"if not `os.path.isdir(CS.harvest_root())`: print SKIP; return"*. The CI runner is Linux
and has no `D:` drive, so **the assertion never executes there and the suite exits 0**. The
auto-land Action is therefore green while the same suite is red on the only machine where the
data it guards actually exists. **A guard that can only fire where nobody runs it is not
measuring anything** — the same family as `MA5`'s source sweep firing on its own documentation and
`MA23`'s stale-path guard being blind to the import syntax the codebase writes.

**Fix: compare normalised paths** (`os.path.normcase(os.path.normpath(...))` on both sides), so the
assertion means the same thing on both platforms. **Kill condition:** if normalising makes the test
pass on Windows *and* it still skips on Linux, add a fixture so the comparison runs on both — a
guard whose only real execution is skipped is the defect, not the separator.

**Not fixed here**: this audit is read-only, and it is not this lane's file.

---

## QUESTIONS FOR DON — batched, none blocking

1. **`MB21` is the audit's top item and it may end with copy being withdrawn.** If the
   persistence-preserving null shows `S22`'s long-horizon result inside it, the hot-list card's
   *"still ahead by about 5.1% annualized two years later"* comes off. Do you want that
   pre-committed in the register before the number is read (my recommendation, and the project's
   own discipline), or do you want to see the number first and decide?
2. **`MB14` spends 1 equity trial on a probable "cannot tell".** I recommend it — it converts the
   project's largest open finding into a dated, powered refusal and makes re-litigation costly. Say
   no and it stays open indefinitely, which is also a defensible choice.
3. **`MB2`: 16 trials for the full DTE × delta grid, or 1 for the 60–90 DTE cell alone, or zero.**
   I recommend zero and explain why; you have pre-committed interest in 60–90 DTE, so this is
   genuinely your call rather than mine.
4. **`MB3` needs no permission but produces a number you may not like:** the account equity at
   which an earnings-spanning book survives `O11`'s ruin arithmetic. If it comes back above
   $250,000, do you want it closed permanently or held open?
5. **`MB25` (the TIDEMARK page):** linked page at `/tidemark`, or a tab? I recommend a linked page
   and give the reason (two verdict grammars, two denominators). Also — are you content that the
   page leads with TIDEMARK's refusal sentence rather than its numbers? That is the honest ordering
   and it is a product choice.
6. **`MB28` is Cowork's, not mine:** registering a Windows scheduled task to run
   `scripts/checkout_drift.py --json` daily. It cannot be done in CI (`MA11` refuses `.github/`
   edits, and it measures a local checkout). Shall it be routed?
7. **`MB38` publishes `N`, the derived hurdle, and the word FAIL — not the statistic.** That is a
   posture decision, not a research one. Comfortable?
8. **`MB36` moves 116 markdown files into `register/` and `handoff/`.** It buys readability only
   (not image size — `MA23` proved that) and it carries one real hazard (`research_record.py`
   globs the filesystem). Worth the commit, or leave the root as-is?

---

## THE ANSWER TO THE QUESTION THIS COMMISSION ACTUALLY ASKS

After ~550 trials across two books, **the next real edge most plausibly lives in the instruments
rather than in another hypothesis** — and the strongest single candidate is not a signal at all but
a null: the composite's own persistence is 0.5802 at one quarter and still 0.4099 at two years,
while the placebo it is judged against has exactly zero, so `S22`'s term-structure claim — the one
result this project chose to put on the product's front card — has never faced the artifact that
Boudoukh–Richardson–Whitelaw say produces its exact shape. Behind it, in descending plausibility:
the 2.7 million alternative contracts, which permit the one decomposition (`R2` as timing versus
selection) that closes a family rather than opening one; the tick tape's 14-venue `exchange` field,
unread by all five `O14` features and all of `O10`/`O18`, and the literature's own retail
identifier; and the banked reverse-DCF panel's point-in-time implied-growth gap, at 100% coverage
over 69 dates and never scored. **Nobody should ever look again at**: regime conditioning of the
equity composite, where the arithmetic is not close — 34.2 years of data per side against 17.3 in
total, and the required gap exceeds the entire published alpha at any critical value; the
options-expression family, closed by `P1S0` at its power anchor and priced by `DEEPITM-FIN` at 702
bps/yr all-in against margin cards at 150 and 420; short vol, closed by `O9` and re-killed by
`V6-OPT`'s mechanism; and any register whose motivation is *"structurally orthogonal to the
incumbents"*, which has now failed three times on this panel with R² between 0.027 and 0.088 and
nothing to show for it. **And the single cheapest experiment that could genuinely surprise us is
`MB21`'s** — permute each name's whole signal time series instead of permuting within dates, rebuild
`S22`'s per-horizon floor against a null that finally remembers, and look at `H=504`. It costs one
infrastructure trial, needs no new data, runs in a session, and it is the only experiment in this
document whose most likely outcome is that the project has to take something *off* the product —
which, on a record that is overwhelmingly rejections, would be the most informative result
available.

---

## Sources cited from outside the corpus

- Blitz, D. — *The Quant Crisis of 2018–2020: Cornered by Big Growth* (Robeco, 2021).
  [robeco.com](https://www.robeco.com/en-int/insights/2021/02/the-quant-equity-crisis-of-2018-2020-cornered-by-big-growth) ·
  [PDF](https://www.robeco.com/files/docm/docu-the-quant-equity-crisis-of-2018-2020-cornered-by-big-growth-us.pdf).
  *Replication status: the episode's dating and character are corroborated across independent
  practitioner research ([Man Group](https://www.man.com/insights/the-quant-renaissance),
  [First Sentier](https://www.firstsentierinvestors.com/is/en/professional-investor/insights/lessons-from-the-quant-winter.html));
  no causal mechanism is claimed here.*
- Boudoukh, Richardson & Whitelaw — long-horizon R² rising mechanically under the null (*RFS* 2008);
  and Boudoukh, Israel & Richardson (*JFE* 2022) on bias-adjusting long-horizon regressions.
  *Cited via TIDEMARK's `CHARTER.md` §3.2, which reproduces the check on its own data.*
- Bryzgalova, Pavlova & Sikorskaya — *Retail Trading in Options and the Rise of the Big Three
  Wholesalers*, **Journal of Finance** 78(6), 2023, 3465–3514.
  [Wiley](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13285) ·
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4065019).
  *Replication status: published in the JF, widely cited. The wholesaler flag it uses is NOT
  available from this project's vendor; any venue-based classifier here is a proxy.*
  Extended by Bogousslavsky & Muravyev, *An Anatomy of Retail Option Trading*
  ([PDF](https://www.lsu.edu/business/files/event-files/2025-finance-mardi-gras/retail_option_trading_v2.pdf)).
- Easley, López de Prado & O'Hara — VPIN / *From PIN to VPIN*
  ([PDF](https://www.quantresearch.org/From%20PIN%20to%20VPIN.pdf)); **contested by** Andersen &
  Bondarenko, *Assessing Measures of Order Flow Toxicity*
  ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2292602),
  [PDF](https://pure.au.dk/ws/files/68359010/rp13_43.pdf)) and *VPIN and the Flash Crash*
  ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1881731)); response in
  [*Review of Finance* 19(1)](https://ideas.repec.org/a/oup/revfin/v19y2015i1p1-54..html).
  *Replication status: DISPUTED, and the disputed component is the Bulk Volume classifier — which
  is why only the quote-classified version is proposed (`MB16`).*
- Gao, Han, Li & Zhou — *Market Intraday Momentum*, **JFE** 2018
  ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351),
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)).
  *Marked NOT-TESTABLE-HERE in `MB17`: it is an index/ETF half-hour phenomenon and this project owns
  no index chain and no equity tape.*
- Pre-registration registries surveyed for `MB38`: [ClinicalTrials.gov](https://clinicaltrials.gov)
  (NLM/FDA) and the [AEA RCT Registry](https://www.socialscienceregistry.org).
  Open backtest-diagnostic tooling surveyed: [`pypbo`](https://github.com/esvhd/pypbo),
  [`ml4t-diagnostic`](https://www.ml4trading.io/docs/diagnostic/methods/deflated-sharpe-ratio/),
  [quant4free tools](https://quant4free.com/tools/),
  [`quantstrat::SharpeRatio.deflated`](https://rdrr.io/github/braverock/quantstrat/man/SharpeRatio.deflated.html).
  *None is a maintained count of one project's own trials.*
