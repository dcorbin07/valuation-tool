# HANDOFF — PEAD (post-earnings announcement drift), roadmap #24

Session: 2026-08-03, Claude Code (growth valuation lane). Task: `PROMPT_pead.md`.
Full **2,710-name x 110-date universe** (136,478 rows), measured on the post-EV-fix panel.

**VERDICT: REJECTED.** Neither variant earns a place in a theme. Both stay MEASURED — wired,
IC and coverage reported every run — so the negative result is permanent rather than folklore,
and re-testing is one line in `factors.py`.

---

## 0. Read this first: the work was already done, and I verified it rather than redid it

`PROMPT_pead.md` describes PEAD as "the last genuinely-untested signal in the hopper". It is
not — a previous session built it, gated it, and rejected it in two commits already on `main`
(`9323a08` pre-specifying the gate before running, `2f75d60` recording the result). What was
genuinely missing was the **report**: every other agent has a `HANDOFF_*.md` and PEAD had none.

So this session did three things instead of re-running a settled experiment:

1. **Independently re-measured** every claim on a fresh full-universe run built on the
   post-EV-fix panel, which the original session did not have.
2. **Added the control the original run lacked** — the one that turns "it overlaps momentum"
   from an observation into a demonstration.
3. **Pinned the point-in-time invariant with tests.** `pead.py` is called on every panel row
   and had *zero* test coverage.

I flag this because "the prompt's premise was stale" is exactly the kind of thing that gets
quietly papered over by re-running a backtest and reporting the same answer as if it were new.

---

## 1. The signal

No point-in-time analyst estimates exist here (IBES is parked), so the surprise is measured by
**the market's own reaction** rather than reported-vs-expected. Two variants, both fixed before
the first run:

| variant | definition | coverage |
|---|---|---|
| `pead_car` | cumulative abnormal return over [t−1, t+1] around the most recent announcement, minus the benchmark | **82.33%** |
| `pead_drift` | the same CAR, but only while the announcement is younger than 63 days | **25.06%** |

Earnings dates come from EVENTS code 22 (`bulk.EARNINGS_CODES`), decoded empirically. Coverage
of that decode is **partial — ~2.83 announcements per ticker-year against ~4 expected**, so a
name with no recent announcement is *unknown*, not "no news"; the signal is left NaN and the
theme mean skips it rather than scoring a zero.

**Point-in-time, enforced twice:** the announcement must be on or before the rebalance date,
*and* its CAR window must have closed by then. The second condition is the subtle one — a CAR
is a forward-looking window by construction, so an off-by-one would silently manufacture edge
out of future returns. It raises no error and dents no coverage metric.

---

## 2. Coverage first, then the gate

Per the coverage rule, coverage before any IC. `pead_drift` at **25.06%** fails the
pre-committed `MIN_COVERAGE = 0.30` outright — a signal on a quarter of rows cannot move a book.

| signal | median IC | IC t | coverage | standalone bar (t ≥ 2.0, cov ≥ 30%) |
|---|---|---|---|---|
| `pead_car` | +0.01004 | **+2.215** | 82.33% | **PASS** |
| `pead_drift` | −0.00201 | −0.473 | 25.06% | FAIL (both) |

These reproduce the originally recorded figures (+0.0100 / +2.21 / 82.3% and −0.0020 / −0.47 /
25.1%) essentially exactly, on an independently rebuilt panel.

### The diagnostic that matters more than the IC

PEAD theory says drift is **strongest immediately after** the announcement. Here the
recent-only window scores **t −0.473** while the all-ages CAR scores **+2.215**. That is
backwards. Where both exist the two are the same number by construction (correlation
**+0.997**), so the difference is entirely *which rows* are included: on recent-announcement
rows the CAR does not predict; on the full set it does.

**Whatever `pead_car` measures, it is not post-earnings drift** — so its +2.215 must not be
read as evidence for PEAD.

---

## 3. Orthogonality — it is momentum we already own

Average within-date correlation:

| vs | this run | originally recorded |
|---|---|---|
| `ret_6_1` | **+0.301** | +0.286 |
| `high_prox` | +0.239 | +0.241 |
| `ret_12_1` | +0.208 | +0.200 |

For scale: `ret_6_1`'s own IC t is **+3.405**, about 1.5x `pead_car`'s.

**But correlation alone would have been misleading here, so I ran the incremental test.**
Residualizing `pead_car` on the three momentum inputs per date:

```
momentum inputs explain R² 11.2% of pead_car's cross-sectional variance
RAW      pead_car : median IC +0.00975   t +1.955
RESIDUAL pead_car : median IC +0.00284   t +0.020   <- what it actually ADDS
```

This is the crux. **89% of `pead_car` is orthogonal to momentum — and that orthogonal part
predicts nothing at all** (t +0.020). Judged on correlation alone it would have looked like a
promising near-independent signal. It is not: it is mostly unrelated to momentum *and* mostly
uninformative.

---

## 4. Held-out, both halves — and an honest complication

Pre-registered direction: positive drift after a positive surprise. Standing margins:
**+0.25 long-short t AND +100bps alpha, in BOTH halves.** Boundary 2012-10-08, embargoed.

Adding `pead_car` to the momentum mean, full shipped composite:

| half | long-short t | Δ | top-decile alpha | Δ |
|---|---|---|---|---|
| early | 2.7252 → 2.8585 | +0.133 | +14.80% → +15.14% | +0.33pp |
| late | 2.3026 → 2.6530 | +0.350 | +9.13% → +9.85% | +0.72pp |

**Fails.** Early misses on both t and alpha; late clears t but misses alpha. `pead_drift` fails
by more (early +0.068 t / +0.22pp, late +0.075 t / +0.07pp) on top of failing coverage.

**The complication, reported rather than smoothed over.** These deltas are *positive*, whereas
the figures recorded in `pead.py` are negative (early −0.08pp, late −0.09 t / −0.35pp). The
sign flips with the choice of book. Restricting to rows where the signal exists reproduces the
originally recorded alpha *magnitudes* and the negative early-half alpha:

| construction | early Δt | early Δalpha | late Δt | late Δalpha |
|---|---|---|---|---|
| full composite | +0.133 | +0.33pp | +0.350 | +0.72pp |
| momentum-only book | +0.027 | −0.66pp | +0.327 | +0.41pp |
| restricted to rows with the signal | +0.041 | **−1.06pp** | +0.299 | +0.54pp |

So the original numbers were most likely a restricted-universe book, and I could not pin down
the exact construction. **Every construction fails the pre-registered margins**, so the reject
is robust — but nobody should quote a specific held-out delta for PEAD without naming the book
it was measured on. That belongs in the record, given this project's history with a
sign-convention that got repeated wrongly for months.

---

## 5. The control that settles it

Residual IC of ~0 and a book that nonetheless moves is a contradiction that needs explaining.
`pead_car` correlates **most** with `ret_6_1` (+0.301), the strongest momentum input, and
**least** with `ret_12_1` (+0.208), the weakest. Adding it to a mean therefore acts as an
implicit **reweighting toward `ret_6_1`** — no earnings information required.

Tested directly, by counting `ret_6_1` twice in the momentum mean and using **no earnings data
whatsoever**:

| arm | full Δt | full Δalpha | early Δalpha |
|---|---|---|---|
| + `pead_car` | +0.271 | +0.52pp | +0.33pp |
| + `ret_6_1` again (no PEAD) | +0.115 | **+0.83pp** | **+1.45pp** |

The no-information control captures much of the t gain and **beats `pead_car` outright on
alpha**, in the early half by more than 4x. Whatever `pead_car` buys the book is a reweighting
that a single duplicated column buys more cheaply.

---

## 6. Tests — new

`pead.py` is called on every panel row and had **no test coverage at all**. Added
`tests/test_pead.py`, **12 tests**, pinning the wiring and the correctness property, not the
verdict (the `sector_neutral` precedent: a rejected signal keeps its plumbing and the plumbing
must stay honest so a re-test measures what it claims to).

The important one is a **tampering test**: it multiplies every price *after* the CAR window by
5 and asserts the signal does not change. That is the only way to demonstrate no-look-ahead
rather than assert it. Also pinned: announcements after the rebalance are invisible; a window
that has not closed is refused and becomes usable exactly one day later; the latest *past*
announcement wins; the CAR is abnormal rather than raw; a stale announcement yields *absence*
rather than a decayed number; no announcements yields no signal rather than a zero (a zero
would score as an average surprise); and both variants remain registered but absent from the
momentum composite.

All suites green: **485 tests across 16 suites.**

---

## 7. Honest caveats

- **The earnings calendar is partial** — ~2.83 announcements per ticker-year vs ~4 expected. A
  fuller calendar could change the answer, though it would have to overcome a residual IC of
  ~0, which is a large gap to close.
- **This is not a test of PEAD as the literature defines it.** It is a test of a *price-reaction
  proxy* for surprise. The proxy cannot separate "beat expectations" from "went up recently",
  and the drift-variant result says it mostly measures the latter.
- **PEAD is heavily arbitraged** since the 1990s. A null here is the expected outcome, not a
  surprising one.
- Both halves come from the same 18-year panel and universe.
- The held-out deltas are construction-sensitive (section 4). The verdict is not.

---

## 8. Recommended next step

**Do not re-open PEAD with the price-reaction proxy.** It was tested properly, the reject is
robust across constructions, and the reason is understood rather than merely observed: the
orthogonal 89% of the signal carries no information, and the book movement it produces is
bought more cheaply by duplicating a column.

The only version worth re-opening needs **real point-in-time earnings surprises** (reported vs
expected) — WRDS/IBES, still parked, same blocker as the estimate-revisions sentiment theme
(CLAUDE.md #20). If IBES ever lands, both unblock together.

With this closed, the cheap signal ideas are genuinely exhausted. The standing priorities are
unchanged: **the forward paper-track vs SPY** (CLAUDE.md #12, Cowork's lane) remains the top
item overall, and the **ML tree combiner** (#16) is the most promising remaining work — P6
showed the linear composite is sensitive to how inputs are scaled, and this session is another
instance of that (a reweighting, not a new signal, moved the book).

A smaller one from the EV session also stands open: the **negative-EV sign inconsistency**
(`HANDOFF_ev_fix.md` §8), which is one guard plus one held-out A/B.
