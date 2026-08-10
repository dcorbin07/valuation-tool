# VALQUO — state of play, 2026-08-06

Written because the project felt like scramble mode. It partly was, and this file says why, what
is actually done, what is left, and what changes.

---

## 1. THE HONEST DIAGNOSIS — we are not re-breaking things

The feeling that "we fixed it, it came back, we fixed it, it's back" is real, but it is not the
same bug recurring. **The same decision is implemented in several places that do not know about
each other, and each fix only fixes one copy.**

Concretely — *"is this fair value publishable?"* is answered in **four** independent places:

| where | its answer |
|---|---|
| the valuation page (`engine/pipeline.publication_guard`) | refuse above **5×** price |
| `screener/fairvalue._growth_value` | cap at **20×** |
| `screener/fairvalue._mature_value` (multiples/EV bridge) | **no cap at all** — `implied/price = 3 + 2×(net debt / market cap)` |
| `screen.py::_enrich_with_dcf` | writes `None` on a refusal, which the next step reads as *"not computed yet"* and **replaces with a peer estimate** |

That is why KSPI's page says *"cannot value this name"* while the public hot list served
**$299.16** for it. Nothing regressed. A fifth copy of the same decision was simply found.

**This is not a new discovery — the project already documented the same disease on the scoring
side and moved on.** `CLAUDE.md`, written weeks ago:

> There are three different composite functions in the tree (selection renormalises by
> present-weight mass, measurement does not, live renormalises AND adds two interventions), so
> **no shipped code path reproduces the backtested composite exactly.**

Same shape. Same cause. Recorded, never consolidated.

**So the fix is not another bug prompt.** It is one consolidation task per duplicated decision:
computed once, consumed everywhere, with the duplicates deleted rather than aligned. Two are
known and both are now first-class roadmap items rather than things to rediscover:

- **CONSOLIDATE-1 — publication.** One function decides whether a fair value may be shown, one
  band, one reason string. Every surface calls it. `screen.py` records the refusal instead of
  erasing it.
- **CONSOLIDATE-2 — the composite.** One scoring function. The backtest, the selection step and
  the live screen call the same one, or the differences are named constants with a test asserting
  what each path is allowed to differ by.

Until these land, expect to keep finding copy N+1. That expectation is the point — it is a
finite, enumerable job, not an endless one.

---

## 2. WHERE WE ACTUALLY ARE — and the number I cannot state precisely

The external audit is **134 items**: B (26 blocking corrections) · R (10 re-derivations) ·
X (8 noise floor) · S (28 stock signals) · O (26 options) · U (8 unification) · C (7 options-bot
+ CI) · P (5 product) · D (10 data sources) · M (6 methodology).

| series | done | total | what it is |
|---|---|---|---|
| **B — corrections** | **25** | 26 | the bug series. Only **B8** left. |
| **C — options-bot + CI** | 7 | 7 | complete |
| **X — noise floor** | ~7 | 8 | complete but for X5 |
| **R — re-derivations** | 6 | 10 | R4, R5, R6, R8 open |
| **M — methodology** | ~4 | 6 | M4, M6 open |
| **P — product** | ~3 | 5 | P3, P5 open |
| **D — data sources** | ~3 | 10 | mostly money/licensing decisions |
| **U — unification** | ~1 | 8 | Session 7. Gated on the miner. |
| **O — options** | ~6 | 26 | the long tail |
| **S — stock signals** | **2** | **28** | **the actual product roadmap, barely started** |

**I cannot give you an exact percentage, and that is itself a finding.** A strict count (item
appears as a section header in the audit ledger) says **38/134 = 28%**. A loose count (item
appears in any of 32 handoff files) says **68/134 = 51%**. The truth is between, because some
matches are forward references — "feeds U1 at Session 7" is not U1 being done.

**There is no single ledger of item status.** State lives across 32 `HANDOFF_*.md` files, the
audit ledger, `CLAUDE.md`, `HANDOFF_STATUS.md`, `VALQUO_ACTION_PLAN.md` and `AGENTS.md`. Every
time the question "where do we stand" is asked, it is answered by git archaeology. **That is the
scramble.** Fixed below.

---

## 3. THE THING THAT SHOULD BE REASSURING

**The bug-discovery phase is nearly over, not accelerating.** The B series — the series that
exists because things were broken — is **25 of 26 done**. The one open item is **B8**
(`holdout_theme_validate` computes `rule_fired` at `fundamental_panel.py:3048` and never reads
it, so a "confirmed out-of-sample" label is really a both-halves stability check).

Everything else that remains is **new work, not repair**: 26 stock signals, 20 options tests,
7 data-source decisions, 7 unification items. That is the roadmap. It was always going to be the
larger half.

The valuation-side bugs of the last three days are the exception that proves it — they were found
in `engine/`, `data/`, `screener/` and `web/`, **which the audit never covered.** The audit read
the edge/backtest tree. The live product had never been audited at all. That is why it produced a
burst of findings, and it is also why the burst is ending: those four directories have now had
four consecutive sessions of scrutiny.

---

## 4. WHAT IS LEFT, IN THE ORDER I WOULD DO IT

**NOW — finish what is open, do not start anything new**
1. **Session 5 closeout** (edge). Five things Session 5 declared unfinished, incl. a void −6.59pp
   figure still in the record and a runner that overwrites banked results.
2. **The miner's deep pull** — ~6h, then rescan → depth report → breadth.
3. **The engine lane's current task** — screener lens, CHTR reinvestment, the terminal-share question.
4. **`screen.py` records the refusal** instead of erasing it. One line. Closes the last known
   public leak.

**NEXT — the two consolidations.** CONSOLIDATE-1 and CONSOLIDATE-2 above. Do these *before* more
signal research, because every new signal added on top of three composite functions is a signal
whose live behaviour nobody can predict.

**THEN — B8**, which closes Part I entirely, and **M1's trial counter finished** (218 trials
recovered, N=84 equity-scoped; the Deflated Sharpe still needs re-running at true N).

**THEN — the S series.** 26 open items, and this is the product. Highest-value first:
S1 (value theme inputs), S3 (rebuild the insider score — the live one is a constant),
S20/S21 (rank composite instead of z-sum; winsorise before standardising — P6 already proved the
composite is scale-sensitive), S12, S23 (an exit rule for the equity book).

**IN PARALLEL, ALWAYS — the forward paper track.** It is the only thing that tests any of this on
data nobody has looked at. Everything else is one panel.

**LATER — O and U.** O is data-gated on the miner; U is Session 7 and gated on O. The options
entry signal is measured dead; the remaining O items are about whether anything else there is
alive, and they get run because the standing rule is that nothing is skipped.

**DECISIONS FOR DON, not agent work:** D1 (Sharadar $29/mo), D2 (ThetaData tier + licence),
D5 (ORATS), D6 (estimate revisions — parked on IBES/WRDS), FMP Starter ~$22/mo.

---

## 5. WHAT CHANGES ABOUT HOW THIS IS RUN

**a. One ledger.** `VALQUO_LEDGER.md` — one row per audit item: id, title, series, status,
verdict, the commit, the handoff it is written up in. Agents update their rows as part of the
handoff. Nobody reconstructs state from git again.

**b. Discovered bugs go to a triage list, not to the front of the queue.** The last four sessions
were driven by whatever the previous handoff happened to find. That is how the roadmap stopped
driving the work. New finding → triage list, with one exception: **live and public** gets fixed
immediately (the fair-value leak genuinely qualified; `_LAST` did not).

**c. A session finishes its series before the next one opens.** Session 5 is being closed before
Session 6 starts, and that is the pattern from here.

**d. Cowork reads the ledger, not the tea leaves.** If the ledger cannot answer "where do we
stand", the ledger is broken and that gets fixed — the answer is never another archaeology dig.

---

## 6. ON THE HOT LIST

The observation that the screener surfaces solid names trending down, and that some of that
weakness looks like sentiment rather than deterioration — that is the weights doing exactly what
they are built to do. Value carries the largest single share of the composite and quality is
second; a book built that way buys good businesses the market has marked down. It is the design,
working.

Whether it is *edge* is a different question, and one impression cannot answer it. The forward
paper track is the thing that can, which is why it stays running no matter what else is happening.

That is also the answer to "are we lost": the product does the thing it was built to do. The last
three days were spent making sure it does not also print a confident wrong number next to it.
