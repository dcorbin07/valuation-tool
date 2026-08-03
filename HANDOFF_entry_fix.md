# HANDOFF — 22c: the scream-buy alert picks worse-than-random days. Why, and can it be fixed?

Claude Code, options lane, 2026-08-03. Full run, 187 names, aggression 1.0 (buy the ask, sell the
bid), window 2016-01-01 .. 2025-10-15. Not a smoke test.

---

## The answer in one paragraph

The 22b finding replicates exactly and it is **stable**: the alert loses to a random entry day in
the same name and year in **both** held-out halves (−5.88pp early, −5.96pp late) and in the two
tiers that carry the book. But the **hypothesis in the mandate is wrong, and wrong with the sign
reversed** — alert days do not carry pumped implied vol, they carry **cheaper** vol than a random
day (ATM 60-DTE IV 0.2428 vs 0.2577, paired z = −11.13; IV rank 0.345 vs 0.425). What alert days
carry is **extension**: the median alert buys a quarter of a percent below the 52-week high after a
+4.1% five-day run, against −4.7% and +0.8% for a random day. So the alert buys strength cheaply
and still does worse. **Nine corrected entries and six same-day gates were tested and all fifteen
fail.** Delaying makes it monotonically worse (+6.36% → +4.36% → +3.59% at 3, 5 and 10 sessions),
so it is not a timing offset. Fading it loses money outright (−10.54%/trade, negative in both
halves), so the anti-tilt does not invert. And the underperformance is **uniform** — the alert
loses to its control in every quartile of run-up and every quartile of IV pop — so there is no
slice to condition on, which is exactly why every filter fails. **Verdict: NOT SALVAGEABLE as an
entry timer.** The one thing that must be said alongside it: the random-entry control is a
yardstick, not a tradable alternative — it buys weakness inside name-years that only exist because
the alert fired there — so this says the alert picks a below-average day within the years it
selects, and says nothing about whether the book beats SPY. That question is still open and is the
forward paper track.

---

## What was run

| phase | what | cost |
|---|---|---|
| 1 | daily ~60-DTE ATM call IV series for all 187 names, one Black-Scholes solve per trading day | 44 min, 187 names, median **2,461 days** each, none thin |
| 2 | 9 entry arms + the rebuilt random-entry control, one frozen alert list, shared fill memo | 34 min, 6 workers |
| 3 | analysis: characterization, arm gates, held-out arm selection, 6 same-day context gates | minutes |

Everything is READ-ONLY on the miner's `data/options/`. Output goes to `data/options_entry/`.

**The gate was committed before the run** (`52a4658`, results-free) for the reason the module
docstring gives: nine arms plus six gates is a search, and a gate chosen after seeing fifteen sets
of numbers is a ranking with a significance label on it.

**Replication check first.** 22c's signal arm reproduces the 22b book **trade for trade** — 3,042
trades, every `(ticker, alert date)` shared, **zero** P&L differences, +5.14%/trade. The refactor
that made the arms possible did not move the baseline.

---

## 1. The finding replicates, and it is stable

Rebuilt control (same name, same calendar year, random day, identical contract/fill/exit rules;
seed 0, 2 draws per alert, **5,919** control trades — more than 22b's 4,238 because it is drawn
against every alert rather than every completed trade):

| | n | expectancy | profit factor | P(≥+100%) |
|---|---|---|---|---|
| **signal** (alert day) | 3,042 | **+5.14%** | 1.162 | 23.18% |
| **control** (random day) | 5,919 | **+11.07%** | 1.373 | 26.12% |

Paired by name-year: **−3.72pp**, the alert wins **44.5%** of 1,080 cells, **sign-test z = −3.48**.
22b's two-seed pooled figure was +13.22% vs +5.14% with z = −5.24; the sign and size agree.

**It is not a period effect.** This is the check that decides whether the tilt is a property of the
signal or just the strategy decaying, which this project already knows about:

| half | signal | control | diff | cells | alert win rate | sign z |
|---|---|---|---|---|---|---|
| 2016–2020 | +5.57% | +11.45% | **−5.88pp** | 441 | 44.4% | −2.20 |
| 2021–2025 | +4.86% | +10.83% | **−5.96pp** | 639 | 44.6% | −2.69 |

Negative in both halves, and almost identically so. By point-in-time cap tier:

| tier | n signal | n control | diff | cells | sign z |
|---|---|---|---|---|---|
| mega | 852 | 1,693 | −5.03pp | 258 | **−2.61** |
| large | 1,590 | 3,057 | −7.37pp | 615 | **−2.26** |
| mid | 567 | 1,110 | −4.02pp | 256 | −0.44 (ns) |
| small | 33 | 59 | +8.00pp | 15 | +0.53 (ns) |

Significant where the trades are, directionally the same in mid, and untestable in small.

---

## 2. Test 1 — what an alert day actually looks like. The mechanism, half confirmed and half refuted

Every entry-context feature, alert days vs random days, **paired within name and year** so "this
name is volatile" and "2020 was strange" cancel. Positive `paired` = higher on alert days.

### The tape half: CONFIRMED, overwhelmingly

| feature | alert (median) | random (median) | paired diff | sign z | cells alert-higher |
|---|---|---|---|---|---|
| trailing 5-day return | **+4.11%** | +0.78% | +4.23pp | **+27.92** | 92.2% |
| distance from 52-week high | **−0.24%** | −4.68% | +6.91pp | **+29.45** | 94.1% |
| extension above 20-day SMA | +4.05% | +1.27% | +3.70pp | **+26.40** | 89.9% |
| trailing 21-day return | +5.19% | +2.65% | +3.61pp | **+15.97** | 74.1% |
| trailing 63-day return | +12.57% | +8.07% | +7.39pp | +17.38 | 76.2% |
| sessions since the 63-day low | 53 | 48 | +6.67 | +10.90 | 65.6% |

The alert fires late into a run, essentially **at** the 52-week high. This is not in dispute.

### The vol half: REFUTED, with the sign reversed

| feature | alert | random | paired diff | sign z | cells alert-higher |
|---|---|---|---|---|---|
| ~60-DTE ATM IV | 0.2428 | **0.2577** | **−1.39pp** | **−11.13** | 32.9% |
| IV rank (252d, strictly prior) | 0.345 | **0.425** | **−6.98pp** | **−9.89** | 34.7% |
| IV vs its own 20-session baseline | 0.968 | 0.991 | −2.46pp | −6.56 | 39.9% |
| IV / realised vol | 1.043 | 1.062 | −0.97pp | −1.80 (ns) | 47.1% |

**Zero of four** IV proxies confirm; three refute at high significance. The alert buys *cheaper*
implied vol than a random day in the same name-year, and buys it at a *lower* percentile of the
name's own trailing year. It is economically coherent — sustained advances compress vol — but it is
the opposite of the stated mechanism.

Two supporting reads: realised 30-day vol is also **lower** on alert days (−1.74pp, z −5.18), while
the 10-day/30-day vol ratio is **higher** (+0.089, z +9.63) — short-horizon vol is picking up into
the alert while the level stays low. And the entry spread is **identical** (4.78% vs 4.80%,
z −1.52), so none of this is a fill artifact.

**E2 verdict: PARTIAL.** Run-up confirmed on 3 of 3 proxies, IV rejected on 4 of 4. Reported as
partial rather than rounded up, per the pre-committed rule requiring both halves.

---

## 3. Tests 2 and 3 — nine corrected entries, all nine fail

All arms share one frozen alert list, the same ~35Δ / 45–75 DTE contract rule, the same NBBO fills
at aggression 1.0 and the same +100% / −50% / half-DTE exits. Only the entry day changes. "vs
signal" is the **matched subset** — alerts both books traded — so a selective arm cannot be paid
for the alerts it declined.

| arm | n | expectancy | vs signal (matched) | vs control | both halves + | passes |
|---|---|---|---|---|---|---|
| signal | 3,042 | +5.14% | — | −5.93pp | yes | — |
| delay 3 sessions | 2,953 | **+6.36%** | −0.65pp | −4.71pp | yes | no |
| delay 5 sessions | 2,964 | +4.36% | −3.02pp | −6.71pp | yes | no |
| delay 10 sessions | 2,962 | +3.59% | −3.68pp | −7.48pp | yes | no |
| pullback (3% within 10d) | 1,045 | +2.62% | **+46.77pp** | −8.45pp | **no** | no |
| pullback-or-day-10 | 2,912 | +3.44% | −1.97pp | −7.63pp | yes | no |
| iv_wait (IV −5% within 10d) | 1,599 | +2.38% | −1.62pp | −8.69pp | yes | no |
| iv_cheap (no IV pop at entry) | 2,357 | +5.41% | +0.27pp (pooled) | −5.66pp | yes | no |
| fade_put (buy the put instead) | 1,771 | **−10.54%** | −18.80pp | −21.61pp | **no** | no |

Three things in that table matter more than the pass/fail column.

**Delaying makes it monotonically worse.** +6.36% → +4.36% → +3.59% pooled, and −0.65 → −3.02 →
−3.68pp matched. Whatever is wrong with the alert day, the days after it are worse. This is not a
timing offset that can be corrected by waiting — a genuinely late signal would improve with delay,
and this does the opposite.

**`delay3` is the trap the matched comparison exists to catch.** Pooled it looks like a +1.22pp
improvement on the signal and is positive in both halves. On the alerts the two books actually
share it is **−0.65pp**. The pooled gain is a different alert set, not a better entry.

**`iv_cheap` is a pure filter** — it buys on the alert day, so on shared alerts it *is* the signal
and its matched difference is exactly zero by construction. It is therefore judged on the pooled
book (+0.27pp) with the random-drop control doing the work. Only **1,345 of the 5,953 alerts
(22.6%)** arrive with an IV pop above 1.05× their own 20-session baseline; removing them changes
essentially nothing, which is what §2's refutation of the vol hypothesis predicts.

---

## 4. The pullback arm: the sharpest picture of the damage, and it still fails

On the **867** alerts where the underlying fell 3% within 10 sessions:

* the signal book (bought on the alert day) returns **−43.59%/trade**;
* buying the dip on those same alerts returns **+3.19%/trade**;
* paired: **+46.07pp** over 570 name-year cells, alert-beaten **74.4%** of the time,
  **sign z = +11.64, p = 2.5×10⁻³¹** — the only BH-FDR discovery among all fourteen hypotheses.

That is a real and very large effect, and it is the clearest statement of what goes wrong: the
signal's disaster alerts are the ones followed by a dip, and they lose almost half the premium.

**It fails anyway, on three separate pre-committed bars:**

1. it loses to the random-day control by **8.45pp** (+2.62% vs +11.07%);
2. it is **negative in the early half** (−1.38% vs +4.72% late) — E1(c);
3. it loses to a **same-sized random drop** of the signal book: +2.62% against **+4.99%** for 1,045
   trades drawn at random from the 3,042 (E6). Keeping only the alerts that dipped is *worse* than
   keeping a random 1,045.

Waiting for the dip does not rescue those alerts. It loses less on them — and you only get the
option on the alerts that dip at all: **2,053 of 5,953 (34.5%)**, of which 1,045 had a fillable
contract on the dip day.

---

## 5. Test 4 — is the anti-tilt exploitable? No

`fade_put` buys the ~35Δ put on the alert day instead of the call:

* **−10.54%/trade**, profit factor 0.743, hit rate 24.7%
* negative in **both** halves: −15.51% early, −8.78% late
* P(≥+100%) 19.5% vs the call book's 23.2%; P(total loss) 1.81% vs 0.69%
* its spread is **wider** than the call side (6.67% vs 4.78%), so the fade pays more to trade
* Deflated Sharpe ≈ **0** at n_trials = 14

The alert marks neither a good long entry nor a top. The underlying does drift up after alerts —
calls make money and puts lose a lot — it simply drifts up **less** than on an average day of the
same year. A −5.24 sign-test tilt does not invert into a tradable edge, which is exactly what the
mandate's guardrail said to expect.

---

## 6. E7 — six same-day context gates through the committed §2 filter gate: 0 of 6 pass

These cost no new simulation: the signal arm's own trades, screened on what was knowable at entry,
threshold fitted on 2016–2020 only and applied unchanged to 2021–2025, judged against the same five
bars `term_slope` had to clear. Direction fixed by the hypothesis before the run (low extension and
low vol are the friendly states).

| gate | kept (late) | late exp → filtered | gain | beats random filter | early gain | verdict |
|---|---|---|---|---|---|---|
| **trailing 21d return** | 823/1,843 (44.7%) | +4.86% → **+10.79%** | **+5.93pp** | yes (+5.07%) | **−0.83pp** | **REJECT** |
| extension vs 50-day SMA | 746/1,843 (40.5%) | +4.86% → +6.01% | +1.14pp | yes | −0.80pp | reject |
| sessions since 63-day low | 1,124/1,843 (61.0%) | +4.86% → +3.73% | −1.13pp | no | −3.64pp | reject |
| IV pop vs 20d baseline | 848/1,843 (46.0%) | +4.86% → +3.76% | −1.11pp | no | −0.81pp | reject |
| IV rank (252d) | 1,046/1,843 (56.8%) | +4.86% → +5.01% | +0.14pp | yes | +4.74pp | reject |
| IV / realised vol | 1,020/1,843 (55.3%) | +4.86% → +2.83% | −2.03pp | no | −1.73pp | reject |

**The near-miss is worth stating precisely.** "Skip the most-extended alerts" (take only alerts
whose trailing 21-day return is ≤ +4.85%) clears **four of the five** arms — late gain +5.93pp
against a +5pp bar, retention 44.7% against a 40% floor, 823 trades against a 60 floor, and it
beats a same-sized random filter (+10.79% vs +5.07%). It fails the **fifth**: the early-half gain
is −0.83pp and the bar is "> 0". That arm exists precisely because, with six gates tested at once,
the best of them will look good by chance, and a gate that only ever helps the half it was aimed at
is indistinguishable from noise that landed there. **Rejected on a pre-committed bar, not
renegotiated after the fact** — the same call made on term_slope's retention floor in 22b.

---

## 7. Why nothing works: the underperformance is uniform, not concentrated

This is the decomposition 22b's handoff named as the cheap next test. Signal minus control,
by quartile of the conditioning variable (band 0 = lowest):

| band | by trailing 21-day run-up | by IV pop vs 20d baseline |
|---|---|---|
| 0 | −7.53pp | −11.66pp |
| 1 | −2.25pp | −0.89pp |
| 2 | −10.81pp | −3.43pp |
| 3 | −3.12pp | −7.85pp |

**The alert loses to a random day in all eight cells.** There is no quartile in which alert-day
entry is the better choice, so there is no threshold to set. And within the alert book itself
neither variable orders the outcome:

* by run-up quartile: +4.87%, +9.69%, −2.18%, +8.18% — no gradient;
* by alert score quartile (median 80.5 / 82.3 / 83.0 / 85.4): +2.33%, +8.55%, +4.11%, +4.34% —
  **a higher scream-buy score does not mean a better trade**;
* by label family, nothing separates:

| label family | n | expectancy | P(≥+100%) |
|---|---|---|---|
| Uptrend (>50 & >200 DMA) | 3,001 | +4.89% | 23.1% |
| Call-heavy flow | 2,710 | +5.74% | 23.1% |
| Near 52-wk high | 2,617 | +5.10% | 23.0% |
| Breakout (upper band) | 1,918 | +4.32% | 22.2% |
| Unusual call volume vs OI | 1,865 | +6.48% | 25.0% |
| MACD bullish cross | 1,712 | +6.75% | 23.4% |
| Volume surge | 1,339 | +5.10% | 24.2% |
| Golden cross | 72 | −9.52% | 16.7% |
| Overbought | 51 | +8.92% | 31.4% |

Every family with a real sample sits in a +4.3% to +6.8% band around the book's +5.14%. In
particular the **options-flow** labels (Call-heavy flow, Unusual call volume) do not separate from
the **technical** ones — which answers 22b's open question about which half of the score does the
damage: **neither, distinguishably.** (This table only reads correctly after grouping: the live
labels embed their own reading — "Call-heavy flow (P/C 0.23)", "Volume surge 1.7x" — so keying on
the raw string split one label into sixty buckets of ~40 trades, several of which looked like
strong signals at ±30%. That was noise from the fragmentation, and it is why the grouping is now
in the code and not in a spreadsheet.)

That reconciles the two halves of §2. Alert days *are* dramatically more extended than random days,
but extension does **not** predict which alerts fail. The tilt is a level effect on the whole book,
not a slice that can be filtered out — which is why nine arms and six gates all fail, and why the
#23 autopsy's 127 hypotheses found zero survivors on this same book.

---

## 8. Multiplicity, deflation, and the held-out arm selection

**Fourteen hypotheses** were tested (8 simulated arms + 6 context gates) and all fourteen are
counted. Deflated Sharpe at **n_trials = 14**:

| arm | DSR | | arm | DSR |
|---|---|---|---|---|
| delay3 | 99.5% | | pullback_or_w | 71.6% |
| **signal** | **96.5%** | | iv_wait | 29.0% |
| iv_cheap | 93.5% | | pullback | 22.9% |
| delay5 | 89.1% | | fade_put | ~0% |
| delay10 | 75.7% | | | |

(For continuity: the 88.13% quoted in 22b is the *autopsy's* DSR, deflated by its 64 features. On
the same 3,042 trades this study's deflation by 14 gives 96.5%, and by 1 gives 99.9%. Three
different deflations of one series — quote the n_trials with the number.)

**BH-FDR at q = 0.10 across the arms: one discovery, `pullback` (p = 2.5×10⁻³¹).** It fails three
other bars, as §4 sets out. Every other arm has a one-sided p of 1.0 — none is even directionally
better than the signal on the paired test.

**The primary out-of-sample read — choose the arm on one half, measure it on the other, both
directions:**

| decide on | chose | gain on that half | measured on | gain there | beats control there |
|---|---|---|---|---|---|
| 2016–2020 | pullback | +40.13pp | 2021–2025 | **+50.04pp** | **no** |
| 2021–2025 | pullback | +50.04pp | 2016–2020 | **+40.13pp** | **no** |

The best available fix beats the signal by +40 to +50pp on the half that did not choose it, in both
directions — and **still cannot beat buying on a random day**. That single line is the cleanest
summary of how bad the entry timing is.

---

## 9. Sanity and coverage

* 185 of 187 names carry trades; largest single name **1.64%** of the book.
* **0.07%** of trades settled at intrinsic rather than on a quote.
* Exit mix: stop 48.7%, time-stop 27.2%, target 23.2%, expiry 0.9%.
* Entry spreads: signal 4.78%, control 4.80%, fade_put 6.67% (puts are wider), delayed arms
  4.65–5.00%. No arm's result is a fill effect.
* IV series coverage: 187/187 names, median **2,461** trading days, none under 200.
* **Five sanity flags fire on every arm and are expected by design**: `term_slope`, `skew_25d`,
  `vrp`, `gex_proxy` and the front-expiry `iv` all read 0% coverage, because 22c does not call
  `options_signals_v2.compute_signals` — its vol read is the ~60-DTE ATM IV series instead, and the
  term_slope filter is not under test here. Recorded in the result file as
  `sanity_expected_flags`, **not silenced**.
* **Occupancy caveat, measured not assumed**: the alert list is frozen from the signal arm, so a
  delayed arm can enter while its own previous trade is open. That happens on **313–409** of ~2,950
  entries (10.6–13.8%) for the delay arms, 0 for signal and iv_cheap. Re-deriving occupancy per arm
  would change *which* alerts fire and break the like-for-like comparison, which is the worse trade.
* Alert accounting — **5,953 alerts**, the same count 22b reported, another replication check.
  2,053 (34.5%) see a 3% dip within 10 sessions; IV comes in 5% within 10 sessions on 3,259
  (54.7%) and never does on 2,671; 1,345 (22.6%) arrive with an IV pop. The signal arm loses 2,911
  alerts to `no_contract_in_band`, unchanged from 22b.

---

## 10. Verdict against the pre-committed bars

| bar | result |
|---|---|
| **E1** an arm beats the signal by ≥10pp AND beats the control AND both halves AND ≥30 trades AND survives BH-FDR | **none of nine** |
| **E2** mechanism: pumped IV **and** extended tape | **PARTIAL** — tape confirmed 3/3, IV **refuted** 4/4 |
| **E3** anti-tilt exploitable by fading | **no** — −10.54%/trade, negative in both halves |
| **E5** best arm survives choose-on-one-half / measure-on-the-other | **no** — wins vs signal both directions, loses to control both directions |
| **E6** selective arms beat a same-sized random drop | **no** — pullback +2.62% vs +4.99% |
| **E7** same-day context gates through the §2 gate | **0 of 6** — best fails on the early-half arm |

**Label: NOT SALVAGEABLE.** The entry timing is genuinely, stably anti-predictive, and none of the
fifteen corrections tested turns that into a positive, out-of-sample, cost-surviving improvement.

---

## 11. The honest framing — what this does and does not establish

**The control is a yardstick, not a strategy.** This is the most important caveat and it cuts both
ways. The control only trades name-years in which an alert fired, so it inherits the alert's name
selection; and §2 shows exactly what a random day *is* in those years — a day **−4.68%** off the
52-week high after a **+0.78%** week, against the alert's **−0.24%** and **+4.11%**. The control is
buying weakness inside years that, by construction, contained a strong advance. You could not have
known those name-years in advance. So the correct reading is: **within the years the alert selects,
the alert picks a below-average day** — and the alert's name selection is untested, not vindicated.

**What this cannot say.** Whether the alert book beats SPY, beats buy-and-hold, or beats not
trading. Every comparison in this project's options work so far is internal. Nothing here changes
the 22b headline that the book earns +5.14%/trade gross of nothing but its own fills.

**What would change the conclusion.** A tradable benchmark that the alert book beats. Not another
entry variant — fifteen have now failed, on top of the trade autopsy's 127 hypotheses over 64 entry
features finding zero survivors on this same book.

**What was deliberately not done.** No arm was re-tuned after seeing its number; no bar was
relaxed; the 10-session wait window, the 3% pullback, the 5% IV drop and the 1.05 pop ceiling were
all fixed before the run and none was varied. The one change made mid-flight — tightening E2 from
"any one proxy" to "a majority of proxies" — was made after a 3-name smoke test, before the full
run, and makes the bar **harder**; it is recorded in the module docstring rather than left silent.

---

## 12. Recommended next step

1. **Stop treating the scream-buy alert as an entry timer, and stop quoting its per-trade
   expectancy as an edge.** The evidence is now: it picks below-average days within its own
   name-years, stably, in both halves; delaying makes it worse; fading loses money; and no gate
   rescues it.
2. **The forward paper track is the only test left that matters** — a tradable benchmark on data
   nobody has looked at. → **Cowork's lane** (tracked "Valquo Index vs SPY").
3. **If one more offline test is wanted**, the honest version is *not* another patch to this
   signal. §2 and §7 together say the control's advantage is "buy weakness in names the score
   likes". A distinct, pre-specified strategy — keep the name selection, invert the day rule, buy
   when the name is in a drawdown from its recent high rather than at it — is the natural
   follow-on. Expectations should be low: `pullback` is a weak version of exactly that and it
   failed three bars.
4. **Do not re-open**: delayed entries, IV-normalisation waits, IV-cheap gating, extension gating,
   or fading the alert. All are measured and in the result file. `ret_21d` gating is the only one
   with a near-miss (4 of 5 arms) and it fails the arm that exists to catch precisely this kind of
   near-miss.

---

## Files

| path | what |
|---|---|
| `valuation/edge/options_entry.py` | the pre-specified study: E1–E7, the arms, the IV series, the paired tests |
| `optentry_run.py` | three resumable phases (IV series / arms / analysis) |
| `tests/test_edge.py` | +14 tests pinning the design decisions |
| `data/options_entry/ENTRY_RESULTS.json` | the full result (gitignored) |
| `data/options_entry/iv_series/*.pkl` | daily ~60-DTE ATM IV, 187 names (gitignored) |
| `data/options_entry/state.pkl` | banked arm books, resumable (gitignored) |

**Tests: 156/156 edge** (142 existing + 14 new). All other suites unchanged and green.

## Three things I caught in my own work

1. **A pure filter arm whose gate was unattainable rather than failed.** `iv_cheap` buys on the
   alert day, so its matched difference against the signal is exactly zero by construction — E1(a)
   could never be met. Filter arms are now judged on the pooled book with the random-drop control
   doing the work, and the distinction is pinned by a test.
2. **A random-drop control that dropped nothing.** It sampled `len(matched)` trades out of the
   matched subset — the same set — so E6 was comparing the arm against itself. It now samples from
   the full signal book, which is what makes +2.62% vs +4.99% a real comparison.
3. **A mechanism rule a single proxy could carry.** E2 originally confirmed if *any* IV proxy fired.
   With four IV proxies that is a cherry-pick; on the full run exactly one (`iv_vs_rv`, and only in
   the 3-name smoke) would have carried a "CONFIRMED" that the full data refutes 4-to-0. Tightened
   to a majority before the run.
