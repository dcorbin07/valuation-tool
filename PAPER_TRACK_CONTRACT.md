# PAPER TRACK — EVALUATION CONTRACT

> **STATUS: IN FORCE from this commit (2026-08-09).**
> Don signed **OPTION E** — see the register in §5, which is the binding part of this document.
> Drafted 2026-08-08 (audit session 13), signed and committed 2026-08-09 (audit session 14).
> From this commit the thresholds in §5 and the meter parameters in §6 are **fixed**: changing
> any of them is not a code change, it is a breach of a pre-registration, and §5's abort rule
> makes it a whole-run void.

---

## 0a. ADDED AT SIGN-OFF (2026-08-09) — what changed since the draft Don read

**Nothing in §0–§4 below has been altered.** Those sections are what Don decided from and are
left exactly as he read them. Four things were found while committing the register, two of them
corrections to the draft's own claims. They are recorded here rather than edited in, because
silently rewriting the reasoning behind a signature is the thing this whole document exists to
prevent.

1. **CORRECTION — "the engine has never been fed" was measured on the wrong database.** §1's
   last bullet says `paper_option_orders`, `paper_index_holdings` and `paper_index_track` hold
   0 rows each. That was true of the **local development** database and is false of the **live
   Render service**, which holds 4 index days, 10 index holdings and 3 paper option orders. The
   weekly `track-backup` Action has been committing them to `data_export/` all along.

2. **THERE ARE TWO RECORDERS AND THEY RECORD DIFFERENT BOOKS.** This is the material finding
   and it is why §5 now names its source explicitly:

   | | **the published Valquo Index** | the Tradier sandbox engine |
   |---|---|---|
   | files | `data/valquo_track.json` + `valquo_track_history.csv` | `paper_index_track` → `data_export/paper_track_*` |
   | inception | **2026-07-30** | 2026-08-03 |
   | book | **86 names, score-weighted, max weight 2.3%** | 10 names, equal-weighted at 10% each |
   | read by | `valuation/screener/index_track.py` — the number the site shows | `valuation/edge/paper_track.py` |

   The engine's 10% equal weights **violate this contract's own 8% cap**, and its book is not
   the Index. So the two are not the same track recorded twice — they are different objects,
   and only one of them is the thing §5 describes. **The register binds the published Valquo
   Index.** The sandbox engine is a separate, useful, unbound record; it is not evidence for or
   against this contract, and no figure from it may be quoted as if it were.

3. **WHY DAYS 2–4 ARE MISSING: nothing in this repository writes the bound series.** It is not
   a scheduler fault, a crash or a conditional write. There is no automated writer at all —
   `index_track.py` only ever *reads* those two files, and `HANDOFF_backup.md` says so in as
   many words. The rows are produced by hand on the Cowork side, which is exactly why four of
   six are absent. **The 6-month operational gate therefore cannot pass until an automated
   daily writer exists.** That work is assigned in §7; it is outside the lane that signed this.

4. **The bound series holds 2 of 6 due rows (33.3%) and ZERO complete calendar months.** The
   second half of that sentence is the one that matters for §6: with no monthly observation in
   existence, the meter's parameters could not have been tuned to the outcome even in
   principle. That is what makes §6 a genuine pre-registration rather than a claimed one.

---

## 0. Why this document exists

Everything Valquo claims about the stock edge comes from **one** 18-year Sharadar panel that the
model was also tuned on. Everything it claims about options comes from **one** reconstructed
alert history. Both clear their internal bars. Neither has ever met data that nobody had looked
at when the rules were fixed.

The forward paper track is the only thing that fixes that. Its entire value comes from the rules
being written down **before** the outcome is known. If we decide what counts as success after
seeing how it is going, it is worth nothing — it becomes the 130th trial in a project that
already discounts its own results for having run 129.

So the rules have to be signed. That is the whole ask.

---

## 1. The state of play, stated before you choose

**Read this first, because it changes what "start fresh" means.**

The track is **already running and is currently behind SPY.**

| | |
|---|---|
| Inception recorded in the live file | **2026-07-30** |
| Days accrued | 5 trading days, to 2026-08-06 |
| Valquo Index | **+0.78%** |
| SPY | **+3.62%** |
| **Excess** | **−2.85 percentage points** |

That −2.85pp is **1.8 standard deviations of a five-day window** (two-sided p ≈ 0.08). It is an
ordinary bad week. It means nothing about the strategy. But it does mean something about *this
decision*: **you are choosing the start date already knowing the accrued period is negative.**

Discarding a stretch you know went against you is the one choice here with a bad look, and it is
the flattering direction. Keeping it costs you almost nothing — five days is 0.3% of a
five-year window and cannot change any verdict. **Every option below therefore keeps the
existing inception**, and the alternative is offered only so the choice is yours, not mine.

**And there is a deadline that is not of anyone's choosing.** The site decides for itself when
the live number stops being labelled provisional: at **60 trading days** the `thin` flag flips,
the "too early to judge" pill disappears, and `headline` switches from `"backtested"` to
`"live"` — automatically, with no one approving it
(`valuation/screener/index_track.py:223-224`). The track is on day 5. **That fires in roughly 55
more trading days — late October 2026 — at which point the site will lead with a number that
§2 shows has 13% power and cannot detect an edge below +49pp/yr.** Signing this contract before
then is what stops that happening by default rather than by decision.

Three further facts you should have before signing, none of them flattering:

- **The recorded inception is 2026-07-30, not 2026-08-03.** The task that commissioned this
  contract assumed the later date. The live file is the authority.
- **The history has gaps.** Only two rows exist — day 1 (2026-07-31) and day 5 (2026-08-06).
  Days 2, 3 and 4 were never written. A monthly series cannot be measured off a record that
  skips days, so §5's abort rule has to cover it and §6 has to fix it.
- **The Tradier sandbox book has recorded nothing at all.** `paper_option_orders`,
  `paper_index_holdings` and `paper_index_track` are **0 rows each**. The engine is built and
  tested (45/45 tests pass), but it has never been fed. The 5 days above come from a *different*
  mechanism — the Cowork-side `valquo_track.json` — not from the engine this contract governs.

---

## 2. The one number that decides everything: how long this takes

This is the part I would most like to be wrong about, and it is arithmetic, not opinion.

From the backtest's own published figures, the Index's top decile beat SPY by **+9.99%/yr** with
a **tracking error of 11.4pp/yr**. Divide one by the other and you get the strategy's
**information ratio: 0.88 per year.** That single number sets how fast evidence accumulates, and
it is *already optimistic* — it was measured in-sample, on the panel the model was tuned on.

*(Two approximations, both stated rather than buried. The backtested object is the plain top
decile; the live Index is that decile score-weighted and capped at 8% within the large-cap tier,
so its tracking error will be close but not identical. And 0.88 is what the strategy managed on
the data it was fitted to — the forward number is more likely to be lower than higher. Every
horizon below is therefore a **best case**.)*

A t-statistic grows with the square root of time. At an information ratio of 0.88:

| horizon | expected t-stat | chance of a "significant" result **even if the edge is entirely real** | smallest edge detectable with 80% confidence |
|---|---|---|---|
| 3 months | 0.4 | **10%** | +69 pp/yr |
| 6 months | 0.6 | **13%** | +49 pp/yr |
| **12 months** | **0.9** | **18%** | **+34 pp/yr** |
| 24 months | 1.2 | 27% | +24 pp/yr |
| **36 months** | **1.5** | **35%** | **+20 pp/yr** |
| **60 months** | **2.0** | **49%** | **+15 pp/yr** |
| 120 months | 2.8 | 74% | +11 pp/yr |

*(The percentages already include a haircut for month-to-month correlation: the project's only
measurement of that is +0.19 at lag 1, which turns 12 calendar months into about 8 independent
ones. Applied as an illustration, not as a measurement of a series that does not exist yet.)*

**Three consequences, and they are not negotiable by choosing a cleverer statistic:**

1. **A one-year verdict is not a verdict.** At 12 months the track can only detect an edge of
   **+34pp/yr** — more than three times the one we actually claim. If the strategy works exactly
   as backtested, a 12-month test still comes back "no evidence" **82% of the time.**
2. **The first horizon where the test is a coin flip rather than a formality is five years**,
   and even there it is 49%.
3. **Refuting the edge takes just as long as confirming it.** The test is symmetric; there is no
   shortcut where bad news arrives faster. Anyone who tells you a short track "disproved" this is
   making the same error as someone who says it proved it.

**What this means for the contract.** The forward track's job is not to deliver a fast verdict —
it cannot. Its job is to (a) accumulate a genuinely out-of-sample record, honestly, from a fixed
start, and (b) **stop anyone, including us, from reading three good months as proof.** The
prohibition is the deliverable. The verdict comes later.

---

## 3. The three options

Pick **one**. Each fixes all five things: start date, horizon, comparison rule, abort rule, and
what may be said publicly meanwhile.

| | **A — RECOMMENDED** | B — earlier decision point | C — add a faster secondary test |
|---|---|---|---|
| **Start** | Keep 2026-07-30 | Keep 2026-07-30 | Keep 2026-07-30 |
| **Operational gate** | 6 months | 6 months | 6 months |
| **Statistical verdict** | **60 months** (2031-07-30) | **36 months** (2029-07-30) | 60 months vs SPY **+** ~36 months vs a costed equal-weight basket |
| **Power at the verdict** | 49% | 35% | 49% / 64% |
| **Cost** | Longest wait | Very likely a wasted decision point | Needs a new benchmark built (real work) |
| **Honest summary** | Slow, but the only one where the number means what it says | Sooner, and will almost certainly say "no evidence" whatever the truth | Best-powered, but the extra benchmark is one nobody can actually buy |

### Option A — RECOMMENDED

**Start.** Keep the recorded inception, **2026-07-30**, including the five accrued days and the
−2.85pp. Reason in §1: it costs nothing and it is the only choice that cannot be read as
discarding a bad start.

**Two horizons, deliberately.**

- **Operational gate — 6 months (2027-01-30).** *Not* a test of returns. A test of whether the
  track is being recorded properly at all: daily rows with no gaps, the book turning over as
  modelled, realised costs near the 33.4 bps the backtest assumes, and no B5-class defect
  outstanding. This gate has real power because it tests execution, not performance — and §1
  shows we would fail it today. **If the gate fails, the clock restarts from the repair**, and
  that restart is logged with its reason.
- **Statistical verdict — 60 months (2031-07-30).** The first read. **Nothing before this date
  is a verdict, whatever it says.**

**The comparison rule.** The book is the **Valquo Index exactly as the site shows it** — broad
top-decile of the large-cap tier by hot score, score-weighted, capped at 8%, no discretionary
substitutions. Measured as **monthly total return minus SPY's monthly total return**, net of the
modelled transaction costs the backtest charges. One series, monthly, from inception to horizon.
At the horizon, and only then:

- **SUPPORTED** — cumulative excess is positive **and** the one-sided t on the monthly excess
  series (Newey–West, 3 lags) is **≥ 1.645**.
- **UNSUPPORTED** — the one-sided t is **≤ −1.645**.
- **NULL** — anything else.

**And it is written here in advance that NULL is the most likely single outcome even if the
strategy works exactly as advertised** (§2: 49% power). A NULL at the horizon means *the test was
too weak*, and may not be reported as a failure of the strategy — nor as a success.

**The abort rule.** Precedent is audit **B5**, which found four defects in this very tracker and
**every one of them flattered it**. So:

- **VOIDS the affected window** (the window is excluded, the reason logged, and the verdict is
  read on the remaining months): any defect in the tracker that changes a recorded return —
  wrong mark, wrong price basis, missing days, a book that silently stopped rebalancing; any
  change to how the Index is constructed; a data-vendor change that alters the benchmark series.
- **VOIDS THE WHOLE RUN**: any back-fill of prices or positions after the fact, any
  discretionary override of a pick, or any change to this contract's thresholds after inception.
- **LOGGED, NOT VOIDED**: sandbox quote delay (~15 min, known and disclosed), ordinary
  rounding, missing a single day's write that is filled the same week, and *bad performance* —
  which is a result, not a defect.
- **A void is never decided after seeing what it does to the answer.** Any voided window is
  recorded, with its reason, at the time it is found — not at the horizon.

**What may be said publicly meanwhile.** Unchanged from today's posture, now as a written rule:
the track is described as **a paper account, thin, and too early to judge**, the backtest stays
the headline, and the live number is shown beside it and never blended into it. Specifically —
**no annualising a stub, no Sharpe until there is enough history, no "since inception" figure
quoted without the day count next to it, and no verdict language of any kind before the
horizon.** This applies to a good stretch exactly as much as to a bad one; a good first quarter
is when the rule is most tempting to break and most important to keep.

### Option B — earlier decision point (36 months)

Everything in A, with the statistical verdict at **36 months (2029-07-30)** instead of 60.

Take it if a decision point inside three years is worth more to you than the decision being
informative. Be clear on the trade: power **35%**, and the smallest edge it can detect is
**+20pp/yr** — double what we claim. **A NULL is roughly twice as likely as a SUPPORTED even if
the strategy is exactly as good as the backtest says.** I would rather wait than build a decision
point that is 65% likely to tell us nothing.

### Option C — add a faster secondary test

Everything in A, plus a **secondary, separately pre-registered** comparison against a **costed
equal-weighted basket of the scored universe**, read at ~36 months.

Why it is better powered: measured against that basket the backtested information ratio is
**1.41/yr** rather than 0.88, because it strips out the market movement that both books share.
That reaches a real t-statistic in roughly **half the time** — about 2 years against SPY's 5 on
the same arithmetic, or 3 against 8 once the month-to-month correlation haircut is applied.

Why it is only secondary: **nobody can buy that basket.** It tests whether the *model* picks
better than the average stock it looks at — a fair scientific question — but not whether *you*
would have been better off than buying SPY, which is the question a user asks. It also has to be
built: the basket does not exist live today, and that is real engineering, not a switch.

---

## 4. What I need from you

One line back, naming an option:

> *"Option A"* — or B, or C, or "A but start fresh from today."

If you want the fresh start instead of keeping the accrued days, say so explicitly and it will be
recorded as your choice, with §1's note that the discarded window was known to be negative. That
disclosure is not a criticism of the choice; it is what makes the choice defensible later.

Once you reply, the chosen option is committed **verbatim, with your choice and the date
recorded**, and the register is live from that commit.

---

## 5. Register — SIGNED AND IN FORCE

**Don's choice, recorded verbatim as given:**

> **OPTION E** — Option C's structure (keep 2026-07-30 inception including the accrued negative
> days; 6-month operational gate; 60-month statistical verdict vs SPY; the ~36-month costed
> equal-weight-basket secondary once built), PLUS a pre-registered anytime-valid evidence meter
> that runs from inception but **first renders at the 6-month operational gate (2027-01-30) and
> monthly thereafter — whatever it says, favourable or not.**

| field | value |
|---|---|
| **Option chosen** | **E** — Option C's structure plus the §6 evidence meter |
| **Signed by** | Don (donniecorbin6@gmail.com) |
| **Date signed** | **2026-08-09** |
| **Amended** | **Amendment 1, 2026-08-09 — see §5a.** Run #1 VOIDED; the live test is **run #2 / vintage 2** |
| **Run / vintage now live** | **run #2, vintage 2** |
| **Inception (run #2)** | **2026-08-10** — the first trading day on or after the amendment, with **ZERO accrued days** |
| **Bound source** | the **published Valquo Index** — `data/valquo_track.json` + `data/valquo_track_history.csv`, as read by `valuation/screener/index_track.py`. **NOT** the Tradier sandbox engine (§0a.2) |
| **Book** | Valquo Index as published — top decile, large-cap tier, score-weighted, 8% cap |
| **Benchmark** | SPY total return |
| **Operational gate date** | **2027-02-10** (6 months from run #2's inception) — tests recording, not returns |
| **Operational gate passed** | ***pending*** — the gate has NOT passed. It cannot, until the bound series has a verified automated daily writer (§7.2). **This row is read by the running site; see the note below.** |
| **Verdict date** | **2031-08-10** (60 months) |
| **Secondary verdict** | ~**2029-08-10** (36 months) vs a costed equal-weighted basket of the scored universe, **only if that basket is built and separately pre-registered first**. Not built; if it does not exist, there is no secondary reading |
| **Statistic** | one-sided NW(3) t on monthly excess, plus cumulative excess |
| **SUPPORTED / UNSUPPORTED** | t ≥ +1.645 and cumulative > 0 / t ≤ −1.645; anything else NULL |
| **Power at verdict, stated in advance** | **49%** vs SPY at 60 months; **64%** for the secondary at 36 months if built |
| **Evidence meter** | pre-registered in §6, parameters **unchanged by the amendment**, first render **2027-02-10** |
| **Costs** | modelled, not measured: **0.14529 pp/month** subtracted from every monthly excess (§6) |
| **Voided windows** | **run #1 / vintage 1: 2026-07-30 → 2026-08-09 (2 recorded rows). Voided by Amendment 1, §5a.** |

**What is fixed and may not be changed:** the bound source, the book, the benchmark, the
statistic, the SUPPORTED/UNSUPPORTED thresholds, the cost constant, and every meter parameter in
§6 — **none of which Amendment 1 touched.** The current vintage's inception and its two horizons
are fixed *for that vintage* and move only when the §5a vintage rule opens the next one. Changing
a threshold voids the run under the abort rule in §3. Repairs to the *recording* (§7) are not
changes to any of these and are expected — they are what the operational gate is for.

> **THE `Operational gate passed` ROW IS READ BY THE RUNNING SITE. It is the only thing that
> can promote the live number to the headline** (added 2026-08-09 by the engine lane, closing
> what is now §7.4 — the section was renumbered when §6 became the meter, so their "§6.4" and
> this "§7.4" are the same item). `valuation/screener/index_track.gate_state()` parses this row
> on every request;
> until it reads as a pass, `headline` stays `"backtested"`, the "too early to judge" pill
> stays up, and `hero.may_lead` stays false — **at any day count, indefinitely**. The day
> count (`MIN_LIVE_DAYS`) is still required as well: the gate is an additional condition, not
> a replacement, so this row cannot promote a three-day track.
>
> On gate day, set this row and nothing else, anywhere:
>
> ```
> | Operational gate passed | YES - 2027-02-10 |
> ```
>
> The value must begin with `yes`, `passed` or `true`. **Every other outcome is not-passed,
> including a missing file, a missing row, a malformed table and two rows that disagree** —
> the failure direction is deliberately "still backtested", never "now live". Nothing else in
> the codebase carries this flag; there is exactly one copy of this fact and it is here.

---

## 5a. AMENDMENT 1 — run #1 voided, run #2 registered, and the VINTAGE RULE

**Dated 2026-08-09. Decided by Don. Recorded here in full, per §3's requirement that a void is
logged with its reason at the time it is found — never as a silent edit.** Nothing above this
section was deleted: §5's register carries the void, and run #1's two recorded rows are kept.

### What Don decided, in his words

> Void run #1 (the 2026-07-30 inception window, ~6 days) — reason: it measured a model that has
> since materially changed: growth-input fix, score fix, universe rebuild. Re-register as run #2
> with a **vintage rule**: any ADOPTED change to scoring, weights, or construction closes the
> current vintage and opens the next; each vintage carries its own clock; the operational gate
> and meter attach to the current vintage; and the cross-vintage record is kept and labelled
> "the system as operated". Rebalancing under unchanged rules is NOT a vintage event.

### Why this is the contract working, not the contract bending

§3's abort rule already lists **"any change to how the Index is constructed"** as something that
**voids the affected window**. A growth-input fix, a score fix and a universe rebuild are that
clause exactly. The window is voided by a cause that pre-dates the outcome and by a rule written
before the run started.

**No threshold was changed.** σ, ρ, α, the cost constant, the statistic, the
SUPPORTED/UNSUPPORTED bars and the book are all untouched, so §3's *whole-run* void clause
("any change to this contract's thresholds") is **not** triggered. **The amendment moves the
clock, not the statistics.**

**And σ was re-checked against the changed model rather than assumed to survive it:** the current
backtest still gives SPY excess **+9.99%/yr** at an implied tracking error of **11.401 pp/yr** and
an information ratio of **0.8759/yr** — the figures σ was derived from. Had the model change moved
the tracking error, §6.5 would have permitted raising σ and nothing else.

### THE DISCLOSURE THAT MUST TRAVEL WITH THIS AMENDMENT

**The voided window was known to be negative when it was voided.** Run #1 recorded Valquo
**+0.78%** against SPY **+3.62%**, an excess of **−2.85pp**. Discarding a stretch that went
against the strategy is the flattering direction, and §1 of this contract warned about exactly
this before anyone had signed anything.

Three things make it defensible, and they should be checked rather than taken on trust:

1. **The cause is independent of the outcome.** The model changed; that would have been true had
   run #1 been +2.85pp. The clause invoked pre-existed the run.
2. **Run #2 starts with ZERO accrued days.** Inception is 2026-08-10, the first trading day on or
   after the amendment. There is no window whose sign could have informed the new start date —
   which is the objection §1 raised against a fresh start, now unavailable by construction.
3. **The voided data is kept, not deleted.** Run #1's rows remain in the series and appear in the
   cross-vintage "system as operated" record below. Anyone can see what was excluded.

**What would NOT be defensible, and is therefore forbidden from here:** voiding a vintage for a
change that was *chosen* after seeing the vintage go badly. The vintage rule below exists to make
that distinction mechanical rather than a matter of judgement.

### THE VINTAGE RULE

1. **A vintage opens** when an ADOPTED change to **scoring, weights, or construction** lands. It
   closes the vintage that was current. "Adopted" means it ships in the live scoring path — not
   proposed, not tested, not rejected.
2. **Rebalancing under unchanged rules is NOT a vintage event.** Names entering and leaving the
   book on the existing rule set is the strategy operating, not a new strategy.
3. **Each vintage carries its own clock**: its own inception, its own 6-month operational gate,
   its own 60-month verdict date.
4. **The operational gate and the §6 meter attach to the CURRENT vintage** and are computed on
   that vintage's window alone. A verdict is a statement about a vintage, and must name it.
5. **The cross-vintage record is kept and published as "the system as operated"** — every
   vintage chained end to end, including voided ones. It is the honest answer to "what would a
   user actually have experienced", and it is explicitly **not** the contract's test: it mixes
   models, so no §5 verdict may be read from it. Both are reported; neither is substituted for
   the other.
6. **A vintage change resets the clock, and the clock is the expensive part.** §2's arithmetic is
   unchanged by any of this: 60 months at 49% power. **A vintage that closes at month 30 has
   bought nothing statistically** — this rule buys honesty about *what* is being measured, not
   speed. Anyone tempted to ship a scoring change should know it costs the whole accrued clock.

### Vintage register

| vintage | run | opened | closed | status | reason |
|---|---|---|---|---|---|
| **1** | #1 | 2026-07-30 | 2026-08-09 | **VOID** | growth-input fix, score fix, universe rebuild — the measured model no longer exists |
| **2** | #2 | **2026-08-10** | 2026-08-11 | **CLOSED** | opened by Amendment 1; closed by the theme restoration after **ONE accrued day** |
| **3** | #2 | **2026-08-11** | — | **OPEN — the live test** | opened by the theme restoration: `capital_discipline` reaches a live score after clearing a pre-registered fidelity gate (Spearman +0.8421 vs the panel's own theme). `institutional` (+0.1706) and `insider` (+0.3596) FAILED that gate and are deliberately still absent. No weight or construction parameter changed |

> **THE CLOCK RESET, AND WHAT IT COST — recorded because Rule 6 says it buys nothing
> statistically.** The gate and the meter attach to the CURRENT vintage, and
> `track_meter.INCEPTION` is *derived* from the open vintage rather than being a literal, so
> the reset is mechanical rather than a decision anyone had to remember to make:
>
> | | vintage 2 | **vintage 3 (current)** |
> |---|---|---|
> | inception | 2026-08-10 | **2026-08-11** |
> | operational gate / first render | 2027-02-10 | **2027-02-11** |
> | verdict date | 2031-08-10 | **2031-08-11** |
>
> **It cost ONE DAY, which is the entire argument for doing this now rather than later.**
> Vintage 2 had accrued a single day, so Rule 6's penalty — reset the whole clock, gain
> nothing — was as cheap as it will ever be. The same restoration a year from now would have
> discarded a year.
>
> **The §5 rows above are NOT rewritten.** They record Amendment 1's terms as signed, and
> those dates describe VINTAGE 2. Where §5 says 2027-02-10 or 2031-08-10, the current
> vintage's equivalents are one day later. The `Operational gate passed` row still reads
> `pending` and is still the one row the running site parses.
>
> **`V1`'s shadow machinery fires here for the FIRST TIME** — `open_pairs()` was documented
> as *"Empty until an adoption opens vintage 3"* and now returns exactly one pair, live 3
> shadowed by 2. Vintage 2's parameters were pinned on 2026-08-10, before any successor
> existed, so the shadow runs a snapshot rather than a reconstruction.

**Cost of the amendment: equity `N` 130 → 131.** Charged, not waived. Void-and-restart is a
researcher degree of freedom — each vintage is another chance for the same hypothesis, and the
probability that *some* vintage crosses rises with the number of vintages. Rule 6 above is the
brake; the trial charge is the accounting.

---

## 5b. THE SANDBOX ENGINE IS A REGISTERED EXPERIMENT — 2026-08-10 (session 16, `PT-SPLIT`)

§0a.2 recorded that two mechanisms record something called "the Valquo Index" and that they hold
**different books**. This section closes that split the only two ways it can honestly be closed:
the mechanism is **aligned going forward**, and the **already-recorded days are registered as a
separate experiment**. There is no third state — no book is both.

**THE ROUTED DIAGNOSIS WAS WRONG, AND THE CORRECTION IS THE USEFUL PART.** The split was reported
as the engine "violating the contract's 8% cap" by holding 10 names at 10% each. It is not a cap
violation. `valquo_index.build_index` sets `cap = max(MAX_WEIGHT, 1/len(picks))` with a comment
saying why: **ten names at 8% sum to 80%**, so on a small book the cap necessarily relaxes to
equal weight, and the payload has always self-reported `effective_max_weight`. The weights were
correct for the book they described.

**The real divergence is BOOK SIZE — 10 names against the published Index's 86 — and it is ONE
construction fed TWO inputs.** `n = max(MIN_NAMES, round(len(large) × TOP_DECILE))` with
`MIN_NAMES = 10`, so a 10-name book means the eligible large-cap tier held **fewer than 100
names**; the published 86 implies a tier of roughly 860. `/admin/run-paper-track` reads
`data/valquo_index.json` when it exists and **silently rebuilds from the store's latest scan when
it does not** — and that scan is a top-N hot list, not the universe. The engine was never pointed
at a different strategy. It was handed a truncated one, with no label saying so.

That matters beyond bookkeeping, because it is how `PT-OUTBOUND` happened: a Discord recap read
the engine and published **+0.18pp** while the bound recorder read **−2.85pp**. A book too small
to be the Index was quoted as the Index.

### The conformance rule, fixed here

A book is **the contract-bound Valquo Index** if and only if:

1. it holds at least **`CONTRACT_MIN_POSITIONS` = 50** names, and
2. the **8% cap actually binds** — `effective_max_weight ≤ MAX_WEIGHT`.

Condition 2 is not redundant. An unbound cap is the *signature* of a book too small for the cap to
be reachable, so it catches the same failure from the other side. **50 is derived, not observed:**
the 8% cap can only bind at 13 names or more, and the published method is a top *decile* of the
large-cap tier, so a book that cannot plausibly be a decile of a real universe is not the Index.
It is a floor, not a target — the published book may be 86 or 120 and conforms either way.

### What is enforced, and where

`paper_track.seed_book` **refuses to seed a non-conforming book** and says why. The refusal is
loud and non-destructive: the run continues and marks whatever is already held, because silently
liquidating a live sandbox book on a conformance rule would be a worse failure than the split it
fixes. The only other way through is `experiment=True`, which **stamps every holding row it
creates** with `REGISTERED EXPERIMENT`. The stamp is on the row rather than in a return value on
purpose — `PT-OUTBOUND`'s lesson is that the old code *did* label its fallback honestly and no
surface ever rendered the label. Make the wrong source unreachable, not merely marked.

`index_summary` carries `book_conformance` measured **from the holdings**, not remembered from a
seed run, so every surface that reads the engine reads what it is actually holding.

### The registered experiment

| | |
|---|---|
| what | Tradier sandbox engine, `paper_index_track` → `data_export/paper_track_*` |
| book | **10 names, equal-weighted at 10%** — `MIN_NAMES`, built from a truncated scan |
| inception | 2026-08-03 |
| days recorded | 4 (2026-08-03, 04, 05, 07) |
| status | **REGISTERED EXPERIMENT — never quotable as the Valquo Index, at any horizon** |
| may it be quoted at all? | Only as what it is: a sandbox execution experiment. Its **fills** are real evidence about execution (V5 uses them); its **return series** is evidence about nothing the contract binds. |

**The four days are kept, not deleted** — the same rule as the voided vintage-1 rows in §5a.
Deleting a record because it turned out to describe the wrong book is the flattering direction,
and the honest artifact is a labelled wrong book rather than an absent one.

**This does NOT open or close a vintage.** The engine's series was never the bound series, so
under §5a's Rule 6 nothing here touches run #2's clock: inception stays **2026-08-10**, the gate
stays **2027-02-10**, the verdict stays **2031-08-10**. Zero trial cost — a conformance rule
searches nothing and selects nothing; charged to infra at `n = 1`.

**What is still open after this section:** the alignment is a gate, not a repair. Nothing here
makes the engine *start* recording the real 86-name book — that needs the conforming
`data/valquo_index.json` to be present on the Render disk when the cycle runs, which is the app
lane's. Until then the gate's effect is that the engine **stops adding** to a non-conforming book
rather than starting a conforming one, and `seed_refused` says so on every cycle.

---

## 6. The evidence meter — pre-registered, parameters frozen at this commit

Don's Option E asks for a meter that runs from inception, first renders at the operational gate
and monthly thereafter, and shows whatever it shows. This section fixes it completely.
Implemented in `valuation/edge/track_meter.py`; every constant below is pinned to a literal by
`tests/test_track_meter.py`, so a later edit turns the suite red instead of passing quietly.

**Why an anytime-valid statistic and not just the t-test.** The §5 verdict is a fixed-horizon
test read once, at 60 months. Looking at a fixed-horizon t-test every month is a
multiple-testing machine: 60 monthly peeks at a 5% bar clear it far more than 5% of the time
under the null. A **confidence sequence** is valid at every *n* simultaneously, so monthly
looking costs nothing and no correction has to be invented afterwards. The price is paid up
front, in width — and it is a steep price, stated below rather than buried.

### 6.1 Construction, fixed

A **Robbins normal-mixture confidence sequence** on the running sum of monthly excess returns:

```
boundary(n) = sigma * sqrt( (n + rho) * ln( (n + rho) / (rho * alpha^2) ) )
```

The sequence crosses when the running sum of monthly excess leaves ±boundary(n).

| parameter | value | where it comes from |
|---|---|---|
| `sigma` | **3.9846917305386294** pp/month | **Not estimated from the track.** The backtest's own tracking error vs SPY, 11.40pp/yr → 3.2909pp/month, inflated by √1.4661 |
| autocorrelation handling | design effect **1.466091** | (1+r)/(1−r) at R9's measured lag-1 **r = +0.189** — the project's only measurement of it |
| `rho` | **3** | minimises the detectable edge averaged over 12/24/36/60 months; the curve is flat from ρ=2 to ρ=6, so the choice is not delicate |
| `alpha` | **0.05 two-sided** | 2.5% per direction |
| cost drag | **0.14529 pp/month** | 261% annual turnover × 33.4 bps one-way, charged both legs = 1.7435 pp/yr. The *larger* of the two readings in the record, i.e. the one that counts against the strategy |
| stale-mark limit | 3 trading days | a month whose mark is staler is **voided**, not measured from the wrong window |
| max voided fraction | 10% | above this the series is declared untrustworthy and the meter refuses to render |

**The autocorrelation inflation is load-bearing, and that is measured rather than argued.** By
Monte Carlo on autocorrelated data, the false-crossing rate is **1.5%** with the inflation and
**6.7% without it** — the naive version silently breaks its own 5% guarantee. There is a test
that fails if the inflation is removed.

### 6.2 What it actually delivers — stated plainly because it is not flattering

Measured over 40,000 simulated paths with the AR(1) structure in them:

| | |
|---|---|
| false crossing under the null | **1.5%** by 60 months, 1.9% by 120 (nominal 5% — conservative) |
| power if the edge is exactly the backtested +9.99 pp/yr | **13.3%** by 60 months, 30.7% by 120 |
| power if the edge is twice that (+20 pp/yr) | 65.8% by 60 months |

Mean excess needed to cross: **6m 63.7 · 12m 42.5 · 24m 29.6 · 36m 24.3 · 60m 19.0 · 120m 13.8
pp/yr.**

**So the meter will most likely never cross, even if the strategy is exactly as good as the
backtest says.** At 60 months it needs ~19 pp/yr against a claimed +9.99. That is the correct
behaviour of an honest anytime-valid bound, not a defect, and it is why the meter **does not
replace** the §5 verdict. Two consequences are binding:

- **A meter that has not crossed is not evidence against the strategy.** It is the expected
  outcome. Reading a flat meter as refutation is the same error as reading three good months as
  proof, and §3's public-posture rule covers both.
- **The meter can only ever end the run EARLY, and only for an effect far larger than the one
  claimed.** If nothing crosses, §5's 60-month fixed-horizon test governs, unchanged.

### 6.3 Display rule, fixed

- Computed from **the current vintage's inception** — since Amendment 1, **2026-08-10**.
  **First rendered 2027-02-10** (that vintage's operational gate), monthly thereafter,
  owner-side. Before that date the meter is computed but withheld — withheld from display, not
  left unmeasured, so nothing is reconstructed later.
  *(Amendment 1 moved this date with the vintage's clock, per §5a rule 3; the run-#1 date was
  2027-01-30, which was a Saturday and needed a note. **2027-02-10 is a Wednesday and a trading
  day**, so that wrinkle is gone. The date moves only when a vintage opens — never otherwise,
  because moving a pre-registered date is what §5 forbids.)*
- **The meter is computed on the CURRENT VINTAGE'S WINDOW ALONE** (§5a rule 4). Voided vintages
  do not feed it. The cross-vintage "system as operated" series is reported beside it and is
  **never** the object of a §5 verdict.
- **Rendering is unconditional on sign.** A suppressed unfavourable render voids the whole run
  under §3's abort rule, exactly as a back-fill does. The strongest guard is that the code
  cannot express the suppression: the render decision reads the date and the integrity of the
  series and never the result, and `test_meter_has_no_sign_branch` pins that flipping the sign
  of the entire series leaves the render decision unchanged.
- **It reaches a public or demo surface only with the day count and the band beside it**, never
  as a bare number. Until the operational gate PASSES, public surfaces keep the §3 posture
  unchanged: paper, thin, too early to judge.
- If the recorded series is too gappy (more than 10% of elapsed months voided) the meter
  **refuses to render** and says so. A meter computed over a broken series is worse than none.

### 6.4 Early-conclusion boundaries — the only legitimate early exit

If the running sum crosses ±boundary(n) before 60 months, **that is a valid conclusion**, and it
is valid precisely because the boundary was fixed at this commit with zero complete months of
data in existence:

- **Crossing UP → SUPPORTED-EARLY.** The Index's excess over SPY is positive at an anytime-valid
  2.5% level. The run may stop and be reported as supported, with the crossing month named.
- **Crossing DOWN → UNSUPPORTED-EARLY.** Symmetric, at the same level, and it must be reported
  on exactly the same terms and the same timetable. There is no version of this where bad news
  gets a longer leash.
- **No crossing → nothing is concluded.** Continue to the §5 horizon.

### 6.5 Sigma may never be revised downward

A smaller `sigma` narrows the band and makes crossing easier, so a downward revision is
indistinguishable from buying a result. If realised volatility comes in **above** the plug-in
the bound is anti-conservative and `sigma` must be **raised**, with the change logged as a
construction event. Measured: at 1.5× the assumed volatility the false-crossing rate is **20%**,
a four-fold breach. The meter reports `sigma_breach` on every call so this cannot go unnoticed.

---

## 7. Known gaps this contract does not itself fix

**Status re-checked at sign-off, 2026-08-09.** Items 1 and 3 below were written when the draft
assumed a single recorder; §0a settles what they were asking. What remains is stated after each.

Recorded so they are not mistaken for oversights, and so the operational gate has a checklist:

1. **The monthly series this contract measures CANNOT be computed from today's data, in either
   source.** This is the biggest gap and it is an engineering job, not a wait:
   - The sandbox engine's `paper_index_track` stores a **snapshot of currently-open holdings**,
     each measured since its own entry date — not a chained return series. The code says so
     explicitly, and says that chaining the closed stints in "is a construction change, not a
     bug fix, and was not made." Differencing two of those points is not a monthly return, and
     because a name that leaves the book stops contributing, the daily view drifts toward
     whatever is still held.
   - The Cowork file chains correctly *between consecutive rows it has* — but it is missing
     days (§1), so a four-day gap silently becomes one "daily" return.

   **Until one source produces a genuine chained series that includes closed positions, no
   verdict under this contract is computable.** That work belongs in the 6-month operational
   gate.

   > **RESOLVED AT SIGN-OFF for the bound source.** Naming the published Index as the source
   > (§5) retires the snapshot problem, because that objection was about the sandbox engine and
   > the engine is not bound. The Index series stores **cumulative-since-inception levels**, and
   > `track_meter.monthly_excess` chains them into calendar months the same way
   > `index_track._daily_returns` does. That construction is robust to an interior missing day —
   > a month's return needs only its two endpoints — so the "four-day gap becomes one daily
   > return" failure cannot reach the monthly series. What a gap *can* still do is leave a
   > month-end mark missing or stale; that month is **voided**, never silently averaged over,
   > and the void is recorded when found. Pinned by
   > `test_an_interior_missing_day_does_not_corrupt_a_monthly_return`.
   > **The remaining blocker is item 2, not the construction.**
2. **The daily write is unreliable** — two rows exist where five were due (§1). Whatever runs it
   needs to be fixed, or the 6-month gate fails by construction.

   > **DIAGNOSED AT SIGN-OFF, AND IT IS WORSE THAN "UNRELIABLE": there is no writer.** Not a
   > scheduler fault, not a crash, not a conditional write — **no code in this repository writes
   > `valquo_track_history.csv` at all.** `index_track.py` only reads it; `HANDOFF_backup.md`
   > records the same thing independently. The rows are produced by hand on the Cowork side,
   > which is why four of six are missing. **This is now the single blocking item for the
   > operational gate**, and it is the Cowork lane's: an automated daily write of the Index's
   > cumulative Valquo/SPY levels, on every trading day, or the gate fails by construction.
   > `track_meter.gap_report` exists so the failure is loud and dated rather than
   > discovered at the gate — it names every missing day, and it does not demand a row on
   > inception day, which is day 0.
   >
   > **STATUS 2026-08-09 (session 15): A WRITER IS REPORTED TO EXIST AND IT IS NOT YET VERIFIED,
   > IN EITHER DIRECTION.** It is described as a Cowork scheduled task `valquo-daily-track-write`,
   > weekdays 20:01. Two facts, both checkable: **(a)** no such task is visible in this machine's
   > Task Scheduler — 413 tasks enumerate, three are Valquo-related (`Valquo D Backup`,
   > `ValuationToolAutoPush`, `ValuationToolBackup`) and none is this one — and the name appears
   > nowhere in the repository; **(b)** even if it exists, **no run was due before this was
   > written**: the amendment lands Sunday 2026-08-09 and the first weekday firing is Monday
   > 2026-08-10 at 20:01. So its absence from the scheduler is evidence but not proof — it could
   > be registered under another account, or on another machine.
   > **The gate stays `pending` and the gap report is now the instrument that settles it:** from
   > run #2's inception the meter block reports every missing trading day on every request. **If
   > 2026-08-11 shows no row for 2026-08-10, the writer is not running.** That is a one-day test
   > and it needs no further investigation now.
3. **The engine that this contract governs has never been fed** — 0 rows in all three paper
   tables, while the accrued 5 days come from a different mechanism. Either the sandbox engine
   becomes the source of truth or the contract should name the Cowork file as the source. **This
   must be settled before the register goes live**, because a track with two possible sources has
   no fixed start.

   > **SETTLED AT SIGN-OFF, and the premise was wrong twice** (§0a.1 and §0a.2). The engine HAS
   > been fed — on Render, not locally — and the two recorders hold **different books**, so this
   > was never a choice between two recordings of one track. **§5 binds the published Valquo
   > Index.** The sandbox engine remains unbound and useful; it must never be quoted as evidence
   > under this contract. **The divergence is not thereby made acceptable** — two live recorders
   > whose numbers can be confused is a B7-class split, and the standing instruction is that the
   > engine's book is either re-pointed at the Index or its outputs are labelled, everywhere they
   > surface, as a different object. Not done here; assigned in the session-14 handoff.
4. **The code carries two different evidence floors, neither of them derived from power and
   neither pre-committed**: `index_track.MIN_LIVE_DAYS = 60` (~3 months) and
   `paper_track.MIN_DAYS_FOR_MEANING = 126` (~6 months). §2 shows both are far too short for any
   statistical claim — a 3-month read has **10% power** and cannot detect an edge below
   **+69pp/yr**. The 60-day one is not merely a label: it drives
   `headline = "backtested" if thin else "live"`, so **it promotes the live number to the
   headline on its own, on a date already fixed** (§1). On sign-off both should be re-pointed at
   this contract's horizon. **This is the one item that has a deadline whether or not anyone
   acts**, and it lives in `valuation/screener/index_track.py`, which is outside the lane that
   drafted this — so it needs assigning, not just noting.

   > **CORRECTION — THE TWO CONSTANTS ARE IN DIFFERENT FILES AND DIFFERENT LANES.** This item
   > says "both sit in `valuation/screener/index_track.py`", and that sentence was the one
   > assigning the work, so the wrong file name aimed the fix at the wrong lane.
   > `MIN_LIVE_DAYS` is `screener/index_track.py:44`; **`MIN_DAYS_FOR_MEANING` is
   > `valuation/edge/paper_track.py:70`**, the edge lane's.
   >
   > **BOTH ARE NOW GATED, AND THE SECOND ONE WAS A SECOND OPEN DOOR.** `hero` falls back to
   > `paper_track.index_summary()` when the Cowork tracker files are absent — the fresh-deploy
   > case, since `data/` is gitignored — and that function set `meaningful` on a pure day count,
   > so a paper track could still have led the page on elapsed time alone, one layer beneath the
   > gate. It now requires **both** the day count **and** this contract's gate row, read by
   > delegating to `index_track.gate_state()` rather than parsing this file a second time, and
   > **fails closed** on any error. Neither constant was re-pointed at a new number, because the
   > authority is this document's one row, not a constant.

   > ~~**ASSIGNED, NOT FIXED, AT SIGN-OFF.**~~ **CLOSED THE SAME DAY BY THE ENGINE LANE
   > (`126c137`), and the fix is better than the one this section asked for.** Rather than
   > re-pointing `MIN_LIVE_DAYS` at a new number, `index_track.gate_state()` now reads the
   > **`Operational gate passed` row of §5** on every request, and `headline` requires **both**
   > the day count **and** that row. So the auto-flip is gone: at any day count, indefinitely,
   > the headline stays `"backtested"` until this contract says the gate passed. Every
   > unrecognised outcome — missing file, missing row, malformed table, two rows disagreeing —
   > is not-passed, so the failure direction is "still backtested", never "now live".
   > **Verified at merge:** `gate_state()` reads the signed §5 as `passed: false`, matching
   > §6.3's rule. **The code and the contract now agree, and there is exactly one copy of the
   > fact.**
5. **The secondary 36-month benchmark does not exist.** Option E inherits Option C's costed
   equal-weighted basket, and §5 records it as conditional for that reason: the basket is not
   built, it is real engineering rather than a switch, and it must be **separately
   pre-registered before it is first computed** — not after, and not by reusing §6's parameters,
   which were fixed for a different comparison. If it is never built there is simply no
   secondary reading, and the §5 verdict stands alone.
6. **The recorded series is gross; the cost figure in §5 is modelled, not measured.** No fills
   exist for the Index — it is a paper book marked from quotes — so the 0.14529 pp/month drag is
   an assumption fixed in advance, deliberately at the larger of the two readings the record
   supports. It cannot interact with the outcome (it is a constant), but it is not evidence
   about real trading costs and must not be quoted as if it were.
