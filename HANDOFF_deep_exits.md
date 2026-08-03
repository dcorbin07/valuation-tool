# HANDOFF — OPTIONS_DEEP_RESEARCH thread #1: EXIT optimization

Claude Code, options lane, 2026-08-03. Full run, **278 complete names**, 3,119 signal entries and
5,986 random entries, aggression 1.0 (buy the ask, sell the bid), 2016-01-01 .. 2025-10-15.
Not a smoke test. Gate committed results-free at `56268b6` before any policy was scored.

---

## The answer in one paragraph

**REJECT — the inherited exit is not beaten by enough to adopt anything, but the thread was worth
running twice over, because it found a real bug and a real, small, consistent effect.** The bug:
the production simulator marks a position that outlives its contract's last usable quote at **that
stale quote**, and a contract stops being quotable exactly when it is dying — so any hold-longer
policy books a price from *before* the final decay. Measured: on the hold-to-expiry policy 44.6% of
trades land in that fall-through, their last quote is a **median of 10 days before expiry**, the
stale mark is higher than true settlement in **94.7%** of cases, and **86.1%** carry a positive mark
on a contract that expires worthless. Correcting it costs that policy **6.45pp** of expectancy. The
shipped exit reaches the fall-through on 0.9% of trades, so **every earlier options result in this
project is essentially unaffected** — but the moment you test holding longer, it is not, and it
would have handed this grid a fake winner. After the fix, the surviving effect is real but small
and points one way on both entry sets: **cutting winners early and stopping out tight are both
costly.** Raising the take-profit from +100% to +150–200% is better per trade, better per day of
capital committed, better on signal entries and on random entries, positive in both held-out halves,
and wins a majority of the name-year cells it changes at FDR 10% — worth **+2.1 to +3.3 percentage
points per trade** (a ~69% relative lift on a +4.71% book). That is well short of the pre-committed
+10pp bar, so nothing is adopted. And because it replicates on **random entries** with equal or
larger size, whatever effect exists is a property of the **exit**, not of the dead entry signal —
which is exactly the question the mandate asked.

---

## What was run, and the one architectural decision that made it possible

A contract's whole life is one cached quote path. So the expensive part — pulling each contract's
daily history — is done **once per entry**, and all 21 exit policies are different readings of the
**same** path. Two consequences:

* the comparison is **exactly matched**: every policy sees the identical entry, fills and quotes,
  and differs only in when it closes;
* re-scoring the entire grid after a correction costs **minutes**, not a 25-minute re-collection —
  which is how the settlement bug below could be found, fixed and fully re-measured in one session.

**The correctness gate came first.** `replay_matches_shipped` re-derives the baseline policy from
the captured paths and compares it, trade by trade, against what the **production** simulator
produced: **3,119 shared, 0 mismatched.** A rebuilt evaluator that quietly differed would make
every number here incomparable to the rest of the project.

| | |
|---|---|
| universe | 278 complete names (410 evaluated, 132 skipped, **120 of them as thin**) |
| entries | 3,119 signal (scream-buy alert days) + 5,986 random (same name, same year, random day) |
| policies | 21, declared before the run; each family varies one dimension from the shipped exit |
| collection | 25 min, 6 workers |

---

## 1. THE FINDING: the simulator rewards holding longer, and it is an artifact

`options_backtest.simulate_trade` walks the contract's daily quotes and, if no exit trigger fires,
falls through to `round_trip(..., expired=True)` with **the last usable quote**. A quote stops being
usable when the bid hits zero, the spread blows past 25% of mid, or the market crosses — i.e.
precisely when the option is dying. So the fall-through books a mark from before the final decay.

Measured on this run, for the hold-to-expiry policy (`tp100_only`) on signal entries:

| | |
|---|---|
| trades reaching the fall-through | **1,392 of 3,119 (44.6%)** |
| of those, genuinely settled at intrinsic | 2 (0.1%) — **the rest were marked at a stale quote** |
| age of that last quote | **median 10 days** before expiry; p90 35 days; max 60 |
| more than 3 days stale | **72.3%** |
| mean return **as marked** | **−77.75%** |
| mean return **at true expiry intrinsic** | **−92.22%** |
| stale mark is the higher one | **94.7%** of cases |
| positive mark on a contract that expired worthless | **86.1%** |

**The bias scales with holding period**, so it does not add noise — it manufactures a monotone
reward for holding longer:

| policy | mean held | share marked stale | honest | stale-marked | overstated by |
|---|---|---|---|---|---|
| trail25 | 11.4d | 0.5% | +0.65% | +1.06% | +0.41pp |
| shipped | 18.4d | 0.9% | +4.71% | +5.34% | +0.63pp |
| sl_none | 28.2d | 6.2% | +7.91% | +9.55% | +1.65pp |
| **tp100_only** | **45.6d** | **44.6%** | **+11.42%** | **+17.87%** | **+6.45pp** |

**Every number in this report uses honest settlement** (hold past the last quote → settle at
intrinsic against the underlying at expiry, which is what actually happens to a position you cannot
sell). The stale-mark version is computed alongside and shipped in the result file as
`stale_mark_artifact`, so the size of the artifact is a reported number rather than a caveat.

**Do earlier results need revisiting? No.** The shipped exit reaches the fall-through on 0.9% of
trades and is overstated by 0.63pp. The 22b headline (+5.14%/trade on 187 names) and every 22c
number carry that same small, uniform bias and their *comparisons* — which all use the same exit —
are unaffected. This matters only for exit research, which is why it had never surfaced.

---

## 2. The grid, honest settlement, aggression 1.0

**Signal entries (n = 3,119).** Baseline `shipped` = +100% / −50% / half-DTE.

| policy | exp | pf | hit | P(≥+100%) | held | exp/day | vs shipped |
|---|---|---|---|---|---|---|---|
| **shipped** | **+4.71%** | 1.146 | 38.9% | 23.3% | 18.4d | +0.00256 | — |
| tp50 | +1.10% | 1.037 | 45.0% | 4.9% | 15.0d | +0.00073 | −3.61pp |
| tp75 | +3.52% | 1.113 | 41.0% | 10.5% | 17.1d | +0.00206 | −1.19pp |
| **tp150** | **+6.81%** | 1.208 | 37.1% | 17.3% | 19.9d | +0.00343 | **+2.11pp** |
| **tp200** | **+7.97%** | 1.241 | 36.6% | 15.2% | 20.7d | **+0.00385** | **+3.26pp** |
| tp_none | +7.43% | 1.223 | 35.9% | 13.2% | 21.9d | +0.00339 | +2.72pp |
| sl30 | +2.09% | 1.075 | 30.2% | 19.7% | 13.0d | +0.00161 | −2.61pp |
| sl70 | +7.84% | 1.238 | 43.3% | 25.4% | 22.9d | +0.00343 | +3.13pp |
| sl_none | +7.91% | 1.236 | 44.1% | 25.7% | 28.2d | +0.00281 | +3.20pp |
| time25 | +1.58% | 1.062 | 40.7% | 13.1% | 12.5d | +0.00127 | −3.13pp |
| time75 / time100 | +5.41% / +5.80% | 1.15 | 37% | 29–31% | 21–23d | +0.00253 | +0.71 / +1.10pp |
| dte21 / dte14 / dte7 | +4.68% / +5.64% / +5.74% | 1.14–1.16 | 37–38% | 27–30% | 20–22d | ~+0.0026 | −0.03 / +0.93 / +1.03pp |
| trail25 | +0.65% | 1.027 | 30.6% | 16.2% | 11.4d | +0.00057 | −4.06pp |
| trail35 | +2.67% | 1.096 | 32.1% | 19.9% | 14.6d | +0.00182 | −2.04pp |
| trail50 | +4.73% | 1.151 | 37.2% | 23.1% | 18.5d | +0.00255 | +0.02pp |
| ratchet35 | +3.99% | 1.131 | 38.2% | 21.9% | 17.4d | +0.00229 | −0.72pp |
| run_winners | +6.41% | 1.192 | 35.9% | 11.8% | 26.0d | +0.00247 | +1.70pp |
| tp100_only | **+11.42%** | 1.255 | 48.6% | 39.3% | **45.6d** | **+0.00250** | **+6.71pp** |

**Random entries (n = 5,986)** — the mandate's key test. Baseline +10.71%.

| policy | exp | vs shipped | | policy | exp | vs shipped |
|---|---|---|---|---|---|---|
| tp50 | +6.83% | −3.89pp | | sl30 | +5.31% | −5.40pp |
| tp75 | +9.04% | −1.67pp | | sl70 | +13.98% | +3.26pp |
| **tp150** | **+12.98%** | **+2.27pp** | | sl_none | +15.28% | +4.57pp |
| **tp200** | **+14.06%** | **+3.34pp** | | trail25 | +3.74% | −6.97pp |
| tp_none | +14.47% | +3.76pp | | trail35 | +6.52% | −4.19pp |
| time25 | +5.76% | −4.95pp | | run_winners | +16.41% | +5.69pp |
| time100 | +13.53% | +2.81pp | | tp100_only | +24.40% | +13.69pp |

**Every direction replicates on random entries, with equal or larger magnitude.** That is the
mandate's key test and it answers cleanly: whatever effect exists lives in the **exit**, not behind
the dead entry signal.

---

## 3. What the grid actually says

Two monotone directions, consistent across both entry sets:

* **Banking winners early is costly.** +50% target −3.6pp, +75% −1.2pp, +150% **+2.1pp**, +200%
  **+3.3pp**, no target +2.7pp. The optimum sits around **+150 to +200%**, not the shipped +100%.
* **Stopping out tight is costly.** −30% stop −2.6pp, −50% (shipped) baseline, −70% +3.1pp, no stop
  +3.2pp. Trailing stops — which are tight stops in disguise — are the worst family in the grid
  (25% trail **−4.1pp**, 35% trail −2.0pp).

Both say the same thing about a convex payoff: **the shipped exit clips the right tail and cuts
positions that would have recovered.** That is economically coherent and it is the one substantive
result of the thread.

**`tp100_only` is the biggest per-trade number and should not be believed.** Three reasons, all
pre-committed checks rather than afterthoughts:

1. **Per day of capital committed it is no better than the shipped exit** — +0.00250 vs +0.00256 on
   signal entries and +0.00553 vs +0.00572 on random. It is *worse on both*. Its entire per-trade
   advantage is that it holds **2.5× longer** (45.6 days vs 18.4). X5 exists to catch exactly this.
2. **It loses a majority of the name-year cells it changes on signal entries** (sign z = −3.97)
   while winning them on random entries (z = +2.33). A policy whose paired direction flips between
   entry sets is not a stable finding.
3. **It carries 21.5% total losses** against the shipped exit's 0.67%, and pushes the tail share of
   gross winnings to 93%. That is a materially different, more extreme long-vol book — X6's
   "different strategy, not a better exit".

---

## 4. The barbell, measured: mean improvement and win-rate point in OPPOSITE directions

This is the cleanest thing the thread produced and it is worth keeping.

| policy | expectancy vs shipped | cells won (of those it changes) | sign z |
|---|---|---|---|
| sl30 (tighter stop) | **−2.61pp** | majority | **+10.65** |
| trail25 (tight trail) | **−4.06pp** | majority | **+3.76** |
| tp200 (higher target) | **+3.26pp** | majority | **+2.58** |
| tp100_only (hold to expiry) | **+6.71pp** | minority | **−3.97** |

Tightening the stop **wins more often and earns less**. Loosening it **earns more and wins less
often**. That is convexity, stated in the only two numbers that matter, and it is the same lesson
the trade autopsy taught about hit rate — a rule that raises how often you win by clipping the
right tail makes this strategy worse.

`tp150` and `tp200` are the **only** policies that are better on *both* axes at once — better mean
**and** a significant majority of the cells they change — on **both** entry sets.

*(Note on reading the cell counts: a take-profit change only alters trades that reached the old
target, so most name-year cells are exact ties. Ties are excluded from the sign test, which is why
tp200 shows a 22% raw win rate and still a significantly positive z: among the cells it actually
changes, it wins clearly more than it loses.)*

---

## 5. Multiplicity, PBO and the held-out read

* **21 policies, all counted.** Deflated Sharpe at n_trials = 21: shipped 90.9%, tp150 **99.2%**,
  tp200 **99.8%**, tp100_only 100.0% (signal entries; all four are 100.0% on random entries).
* **PBO by CSCV over the policy × time-block grid** — the textbook application, and the one
  statistic that directly answers "would picking the best backtest have been a mistake":
  **0.075 on signal entries, 0.000 on random**, over 252 splits. Both pass the 50% ceiling
  comfortably. The grid is not overfit; there simply is not much in it.
* **BH-FDR at q = 0.10** over the paired name-year tests. `tp150` and `tp200` are discoveries in the
  right direction; so are `sl30`, `trail25` and `trail35` — in the *wrong* direction (they
  significantly win more cells while losing expectancy), which is the barbell again.
* **X4, choose on one half and measure on the other, both directions:** survives on both entry
  sets — but it selects `tp100_only` every time, and §3 is why that selection should not be acted
  on. The runner-up on three of the four splits is `tp200` / `run_winners`.

---

## 6. Verdict against the pre-committed bars

| bar | result |
|---|---|
| **X1** adopt: ≥+10pp on signal AND beats shipped on random AND both halves AND ≥30 trades AND survives FDR | **none of 20** — the best is tp200 at +3.26pp |
| **X2** signal-only (entry-conditional) | **none** |
| **X3** multiplicity paid: DSR n_trials=21, BH-FDR, PBO < 50% | **passes** (PBO 0.075 / 0.000) |
| **X4** choose-on-one-half / measure-on-the-other | **survives**, but selects a policy §3 rejects |
| **X5** per-day-held reported | **decisive** — it is what disqualifies tp100_only |
| **X6** tail watched | **decisive** — tp50 removes 79% of the tail; tp100_only pushes it to 93% |

**Label: REJECT — the inherited exit is not beaten by enough to adopt.**

---

## 7. Two things the next session should settle (I did not renegotiate either)

1. **Is the +10pp bar right for an exit tweak?** `MIN_EXPECTANCY_GAIN` was set in
   `options_backtest` for adopting a *construction* change. On a book earning +4.71%/trade,
   demanding +10pp demands a tripling. `tp200` delivers **+3.26pp, a ~69% relative lift**, on both
   entry sets, in both halves, with DSR 99.8% and PBO 0.075. I applied the bar as written and
   rejected it. Whether an *absolute* pp bar is the right instrument for a proportional improvement
   is a real question, and it is the user's call, not mine to quietly change mid-thread.
2. **X1(e) — requiring both a mean gain and a cell-win majority — may be self-defeating on a convex
   payoff.** §4 shows the two criteria point in opposite directions almost by construction here.
   The conjunction is demanding in a way I did not anticipate when I wrote it. `tp150`/`tp200` do
   satisfy both, so it is not unsatisfiable — but it should be thought about before the next
   thread reuses it.

---

## 8. What this cannot see

* **Daily closes only.** An intraday spike through a target or trail that closes back inside is not
  seen. This bites the **trailing** policies hardest — a real trailing stop would trigger more
  often than measured, so the trailing results here are, if anything, **optimistic**, and they are
  the worst family in the grid.
* **No true ATR.** The cached Sharadar bars carry date/close/volume only, so an ATR-based trail is
  not computable and was not attempted. The trails here are drawdowns from the option's own
  high-water mark. Recorded rather than quietly substituted.
* **No portfolio view.** Per-day expectancy assumes instant redeployment, which no real book gets.
  Sizing is thread #7 and nothing here answers it.
* **Universe bias unchanged**: today's-liquidity selection, already spread-screened (120 names
  skipped as thin). Both biases run toward the edge surviving.

---

## 9. Recommended next step

1. **Do not adopt anything from this thread**, but **do record the direction**: if the exit is ever
   revisited, the evidence says the target belongs nearer **+150–200%** than +100%, and the −50%
   stop is on the costly side. Both replicate on random entries.
2. **The settlement fix is the durable deliverable.** Any future work that holds positions longer —
   thread #3 (VRP), #4 (earnings), #5 (calendars) — must use honest settlement or it will
   rediscover the same fake edge. It is now pinned by a test.
3. **Next thread: #2, cross-sectional option returns** (Goyal–Saretto VRP, Cao–Han idio-vol,
   Boyer–Vorkink skewness). It is the most literature-backed item on the list and the one furthest
   from anything this project has already tested.
4. The forward paper track remains the only test of the book as a whole. → **Cowork's lane.**

---

## Files

| path | what |
|---|---|
| `valuation/edge/options_exitlab.py` | the pre-specified study: path capture, 21 policies, X1–X6, CSCV/PBO |
| `optexit_run.py` | resumable collection of signal- and random-entry paths |
| `tests/test_edge.py` | +10 tests, including the settlement fix and a PBO implementation check |
| `data/options_exitlab/EXITLAB_RESULTS.json` | full result incl. `stale_mark_artifact` (gitignored) |
| `data/options_exitlab/paths.pkl` | banked contract paths — re-score any new policy in minutes (gitignored) |

**Tests: 166/166 edge** (156 + 10 new exit-lab tests). All 14 other suites green (317 tests).

## Two bugs I caught in my own work

1. **The stale-mark settlement** (§1) — inherited from the production simulator, harmless for every
   result to date, and fatal for this thread. Found by asking why the winning policy's exit mix was
   44.6% "expiry" when the shipped exit's was 0.9%.
2. **The one-sided FDR screen took its direction from the mean but its p-value from the sign test.**
   A policy with a positive mean and a significantly *negative* sign test was being flagged as a
   discovery in the wrong direction — `sl70` (mean +2.00pp, wins 23.8% of cells, z = −7.50) was one.
   Fixed here and in the 22c entry module, which shares the pattern. **22c's conclusions are
   unchanged**: its only discovery, `pullback`, had mean +46pp *and* z = +11.64, and the one arm
   whose directions disagreed (`delay3`) has a raw sign-test p of ≈0.63 — never close to a
   discovery.
