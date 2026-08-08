# PAPER TRACK — EVALUATION CONTRACT

> **STATUS: DRAFT. NOT IN FORCE. Needs Don's sign-off.**
> Nothing in this file binds anything until Don picks an option and it is committed with his
> choice recorded. The commit that records the choice is the moment the register goes live.
> Drafted 2026-08-08 (audit session 13). No numbers in it were chosen after looking at the
> track's result — but see §1, which is the reason this needs signing *now* rather than later.

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

## 5. Register (fills in on sign-off — currently blank on purpose)

| field | value |
|---|---|
| Option chosen | *pending* |
| Signed by | *pending* |
| Date signed | *pending* |
| Inception | *pending* |
| Operational gate date | *pending* |
| Verdict date | *pending* |
| Book | Valquo Index as published — top decile, large-cap tier, score-weighted, 8% cap |
| Benchmark | SPY total return |
| Statistic | one-sided NW(3) t on monthly excess, plus cumulative excess |
| SUPPORTED / UNSUPPORTED | t ≥ +1.645 and cumulative > 0 / t ≤ −1.645 |
| Power at verdict, stated in advance | *pending* |
| Voided windows | *(none yet)* |

---

## 6. Known gaps this contract does not itself fix

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
2. **The daily write is unreliable** — two rows exist where five were due (§1). Whatever runs it
   needs to be fixed, or the 6-month gate fails by construction.
3. **The engine that this contract governs has never been fed** — 0 rows in all three paper
   tables, while the accrued 5 days come from a different mechanism. Either the sandbox engine
   becomes the source of truth or the contract should name the Cowork file as the source. **This
   must be settled before the register goes live**, because a track with two possible sources has
   no fixed start.
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
