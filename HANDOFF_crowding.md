# HANDOFF_crowding.md — P2, model user crowding

**Item:** P2 (`VALQUO_EDGE_AUDIT.md` Part XIV) · **Lane:** r1 · **Date:** 2026-08-08
**Type:** research memo. **No code was written or changed.** Analysis ran from a scratch
directory outside the repo; nothing new is shipped.
**Depends on:** P1 (capacity, DONE `6eb5a2f`) — whose headline this memo corrects.

---

## 0 · Bottom line

**The crowding question has two answers that differ by a factor of ~700, and which one applies
is a product decision Don has already made — but made silently, and on a stale rationale.**

| the book a cohort actually buys | cohort AUM at which modelled slippage cancels the +7.17% alpha | users at $10k each |
|---|---|---|
| **live Valquo Index** — 86 names, large-cap only, median cap **$22.2B** | **$5.1B** | **~506,000** |
| all-cap **top-25** (the book P1 modelled, and what a concentrated list looks like) | **$7.4M** | **~740** |
| all-cap **top-10** (the shape of a free-tier hot list) | **$1.6M** | **~160** |

**The single most useful sentence in this memo:** crowding capacity is set almost entirely by
the **market-cap floor and the breadth** of the published list, not by the number of users. The
live Index is broad (86 names) and large-cap-only ($10B floor), and that combination is worth
about **700x** the crowding headroom of a concentrated all-cap list. **The product is already on
the safe side of this — but by a design choice whose stated reason is factually wrong (§7,
BUG 6), which means nobody currently knows it is load-bearing and it could be reversed for a
plausible-sounding reason.**

**Three findings that were not asked for and matter more than the headline:**

1. **P1's published capacity of ~$23M is overstated by 4.72x. The true figure on its own model
   is ~$4.9M.** P1 hard-coded a breakeven of 234.5bps; the live measured breakeven is
   **134.1bps** (§3). This is not my re-modelling — it is P1's own arithmetic at the corrected
   input, and it reproduces P1 to the cent before the correction.
2. **Three of P2's four factual premises are false** (§2). The Index does not publish holdings —
   it is owner-only and pinned by a test. The book is not 25 names. It is not small-cap.
3. **Slippage is not the binding crowding risk at any plausible user count.** The
   McLean–Pontiff decay channel the audit cites in passing is roughly **3x larger at 10,000
   users** — and unlike slippage it does not depend on user count at all. It is not modellable
   from anything on this disk (§6). A memo that answered only the question asked would leave the
   bigger risk unstated.

---

## 1 · Threshold, and what kind of result this is

**No adopt/reject threshold was pre-committed, because P2 is not a hypothesis test** — it asks
for an estimate, not a verdict. Per `RUN_RULES.md` A6 I say so explicitly rather than
retro-fitting one. **Verdict: not applicable. This is a MODEL, and every number is conditional
on assumptions listed in §5.**

The one threshold used is **not mine and was not chosen for this run**: the project's own
measured `costs.top_decile.breakeven_one_way_bps` = **134.113bps**, the one-way cost at which
the top-decile alpha reaches zero. "Slippage exceeds the alpha" is therefore exactly "modelled
one-way cost exceeds 134.1bps", which is the prompt's question in the project's own units.

---

## 2 · Premise verification — the audit says four things, and three are false

`RUN_RULES.md` A8: *verify the audit's claims; do not obey them.* P2's method paragraph rests on
its opening sentence, so the premises were checked before any modelling.

| P2's claim | verdict | evidence |
|---|---|---|
| "The Index tab **publishes holdings**" | **FALSE** | `/api/valquo-index` — *"the constructed book: names AND weights, today"* — is in `OWNER_ONLY_PATHS` (`valuation/saas/surfaces.py:80`), reason (2) "actionable live picks". The split is enumerated and pinned by `test_public.py`; a route in neither list fails the suite. |
| "the same **25** small-cap names" (count) | **FALSE, twice** | The live book is **86 positions** (`data/valquo_index.json`, top decile of 861 eligible). Separately, even the backtest's "top-25" is mislabelled: `exit_rank = top_n * 2` (`fundamental_panel.py:1710`) so the held set converges toward **fifty** — the code ships a `label_warning` saying exactly this (`:1777`). |
| "the same 25 **small-cap** names" (size) | **FALSE for the live book** | `LARGE_CAP_MIN = 10e9` (`valuation/edge/valquo_index.py:27`). Live book median cap **$22.2B**, min $10.2B. It is TRUE of the book P1 modelled (median cap $1.0B) — which is the research book, not the product. |
| "on the same quarterly cadence" | **TRUE, with a wrinkle** | `book_configs`: taxable = 63d (quarterly), roth = **42d** (~2-month). Two cadences, user-selectable, so a cohort is already partially split across two schedules. |
| McLean–Pontiff "26% out of sample, 58% post-publication" | **TRUE** | Correctly cited (2016, *J. Finance*). See §6 — the audit quotes it and then does not use it, which is the mistake. |

**What survives.** The audit's *reasoning* is sound and its three named effects (entry impact,
consensus decay, correlated exit) are the right decomposition. Its factual picture of the
product is roughly two design generations out of date. **The item was worth doing; its method
paragraph pointed at the wrong book.**

---

## 3 · P1's headline is overstated by 4.72x

P1's model is `cost_bps = base_bps + λ·σ_daily·√(participation)·1e4`, solved for the AUM where
mean cost equals the breakeven. Two of its inputs are stale:

| input | P1 used | live value | source |
|---|---|---|---|
| breakeven one-way bps | **234.505**, hard-coded | **134.113** | `scripts/capacity.py:36` vs `BACKTEST_RESULTS.json` `costs.top_decile` |
| panel | `data/free_analysis/panel.pkl` — **110 dates, 2,710 names** (pre-B6) | 69 dates, 2,531 names | `scripts/capacity.py:124` default |

234.5bps is the **pre-B6 era** figure (CLAUDE.md records the old profile as "236 bps one-way
against ~37 bps"; B11 later measured 33.4bps against a **134.1bps** breakeven). P1 ran on
2026-08-04, the same day B6 landed, and took the breakeven that existed when it was written.

**Because the model is exactly `B + λ·K·√AUM`, this needs no re-fetch of data.** Fitting `B` and
`K` to P1's own fifteen published cells reproduces every one to **zero residual**
(`B = 48.5098` bps, `K = 0.03881723`), and reproduces all three published capacities to the
cent. Capacity is then `((breakeven − B)/(λK))²`:

| λ | P1 published (@234.5bps) | **corrected (@134.1bps)** |
|---|---|---|
| 0.5 | $91.8M | **$19.5M** |
| **1.0 (headline)** | **$23.0M** | **$4.9M** |
| 2.0 | $5.7M | **$1.2M** |

**P1's strategic conclusion is unchanged and in fact strengthened** — "Valquo cannot be a
managed vehicle" is more true at $4.9M than at $23M. **But the number itself has been quoted
onward** (`VALQUO_LEDGER.md` P1 row, `HANDOFF_free_analysis.md:398`) and is wrong by 4.72x.
Since it also propagates into "Don's own account is unaffected", note that the $1M case still
holds comfortably: modelled cost there is 87bps against 134bps.

---

## 4 · Independent re-run on the corrected panel

Rather than only patching P1's constant, its method was re-run end-to-end on
`panel_corrected_69d.pkl` (69 dates, 2,531 names), deployed weights, across book sizes. ADV from
the local bars cache where available, else P1's calibrated proxy
`log(ADV) = −8.718 + 1.186·log(mktcap)` (R² 0.704). **No network calls** — the Yahoo path P1
used is deliberately not re-run (it is quota-fragile and would silently degrade).

| book | median cap | median ADV | capacity @134.1bps | @234.5 (stale) | users @$10k |
|---|---|---|---|---|---|
| top-10 | $1.1B | $8.9M | **$1.6M** | $7.5M | **159** |
| top-25 | $1.4B | $11.3M | **$7.4M** | $32.8M | **737** |
| top-50 | $1.6B | $14.0M | **$21.1M** | $90.3M | **2,106** |
| top-253 (decile) | $2.3B | $20.8M | **$261.4M** | $1.0B | **26,136** |

**Consistency check:** at the stale breakeven my top-25 gives $32.8M against P1's $23.0M — same
order, differences attributable to the panel change and to ADV sourcing. The **ratio** between
stale and corrected is 4.72x in both, because it is a pure function of the two constants.

**This table's absolute levels are the weakest numbers in the memo** — real ADV coverage is only
5.7–12.7% here (the bars cache is large-cap options names; these books are small/mid-cap), so
most ADV is proxied. P1's 54.7% real coverage is better. **The stale-vs-corrected ratio and the
shape across book sizes are robust; the absolute dollar levels are not.**

---

## 5 · The live book, which is the one that matters

Modelled on the **actual shipped book** (`data/valquo_index.json`, 86 positions, scan
2026-07-24), using each name's own score-weight, real ADV for 44 of 86 names (51.2%) from the
bars cache, and the project's own `one_way_cost_bps` table.

Profile: median cap **$22.2B**, median ADV **$268M**, median daily σ **0.0234**, max weight
**2.31%**, weighted-average base cost **8.9bps** (vs 48.5bps for P1's book — large caps are
cheap).

**Cohort AUM at which weighted-average one-way cost reaches 134.1bps:**

| λ | same-day | spread over 5d | spread over 21d |
|---|---|---|---|
| 0.5 | $20.3B | $101.3B | $425.3B |
| **1.0** | **$5.1B** | **$25.3B** | **$106.3B** |
| 2.0 | $1.3B | $6.3B | $26.6B |

**Alpha decay against cohort size** (λ=1.0, same-day, full book):

| cohort AUM | modelled cost | net alpha |
|---|---|---|
| $1M | 10.7bps | 6.60% |
| $10M | 14.5bps | 6.40% |
| $100M | 26.5bps | 5.76% |
| $500M | 48.3bps | 4.59% |
| $1B | 64.6bps | 3.72% |
| $2B | 87.6bps | 2.49% |

**Concentration is the whole story.** Same book, same users, only the number of names shown:

| slice | capacity | users @$10k |
|---|---|---|
| top 10 by weight | $620.4M | 62,037 |
| top 25 by weight | $1.8B | 178,940 |
| all 86 | $5.1B | 506,297 |

**Assumptions, all load-bearing:**
1. **λ = 1.0 is an assumption, not a measurement** — P1's caveat, inherited. The range across
   λ ∈ [0.5, 2.0] is **16x**. Every headline here is the middle of a wide band.
2. **The alpha and the breakeven were measured on the all-cap top-decile backtest book, and are
   applied here to a large-cap book they were not measured on.** This is P1's caveat 3, and it
   is the weakest joint in the memo. There is no published large-cap top-decile alpha to anchor
   to; the closest is `regime.large.long_short_ann` = 9.63%, a different object.
3. Users act simultaneously and identically. Real cohorts do not — §8 quantifies the relief.
4. Square-root impact with no permanent component, so **coordinated exit is understated** (§7).
5. ADV is survivorship-biased upward (P1's caveat 1). **Every figure is an upper bound.**

---

## 6 · The channel that actually dominates, and it is not slippage

The audit cites McLean–Pontiff and then models only impact. That inverts the magnitudes.

- **Slippage** at any plausible user count is small. At 10,000 users × $10k = $100M on the live
  book, modelled cost is **26.5bps** — the alpha goes +7.17% → **+5.76%**, a 20% haircut.
- **Decay** on McLean–Pontiff's own post-publication estimate is **58%**: +7.17% → **+3.01%**,
  and it does not depend on user count at all — only on the signal becoming known.

**At 10,000 users the decay channel is roughly 3x the slippage channel, and it arrives whether
or not a single user trades.** Slippage is the effect this project can measure and therefore the
one it modelled; it is not the one that will hurt.

**This is not quantifiable from anything on this disk** and I did not fake a number for it. The
honest statement is directional: the composite's themes are *published academic factors*
(X8 confirms they are the standard premia, replicating internationally), so a large part of the
26%/58% decay **has already happened** and is inside the measured +7.17% rather than ahead of
it. That argument is a hypothesis, not a finding.

---

## 7 · Correlated exit, and the design choice nobody knows is load-bearing

**Exit.** A cohort liquidating the whole live book in one day (λ=1.0):

| cohort | 1 day | 5 days |
|---|---|---|
| $100M | 26.5bps | 16.8bps |
| $620M | 52.7bps | 28.5bps |
| $1B | 64.6bps | 33.8bps |
| $5.1B | 134.6bps | 65.1bps |

**These are understated and should not be read as reassuring.** A square-root model with no
permanent-impact term describes an orderly liquidation. The audit's concern is a *drawdown* —
correlated selling into falling liquidity, when ADV itself contracts. Nothing in this model
captures that, and I have no data to calibrate it.

**The design choice.** The live book's large-cap floor is what buys the ~700x headroom. Its
stated justification (`valuation/edge/valquo_index.py:12`) is *"the market-cap tier where the
measured IC was strongest"* — **and that is false.** Measured `regime.median_ic`: small
**0.0313** > mid **0.0304** > large **0.0287**. Large is the *weakest* tier by IC. It is the
strongest by long-short (9.63% vs 9.00%/8.25%), so the choice is defensible on other grounds —
but **the reason written down is not the reason it is right**, and CLAUDE.md repeats the same
error ("Edge is strongest in large caps (regime IC highest there)"). A future session
optimising IC could remove the floor for a good-looking reason and destroy the crowding
headroom without noticing. **That is the most actionable thing in this memo.**

---

## 8 · Mitigations, quantified

The audit proposes four. Measured against this model:

1. **Stagger entry across users — by far the best, and analytically clean.** Capacity is very
   nearly **linear** in the number of days a cohort's flow is spread over: measured 4.97x at 5
   days and 20.9x at 21 days. Spreading over a trading week is worth ~5x the crowding headroom
   for zero research cost. Composes with X2's grid-offset ensemble exactly as the audit hoped.
2. **Publish on a lag** — no effect in this model (it shifts *when* the cohort trades, not how
   concentrated it is). It addresses front-running, a different risk.
3. **Widen the published book** — already done, and it is the single largest lever in the data:
   10 → 86 names is 8.2x (§5).
4. **Publish the capacity estimate** — recommended; see §9.

**The one that is not on the audit's list and dominates all four: keep the market-cap floor.**

---

## 9 · The `/work` sentence

**Is the number worth stating publicly? Yes — with the conditional attached, never bare.**
It is consistent with the project's stated posture, and a bare "$5.1 billion" would be a
capacity *boast* resting on an assumed λ.

Proposed, one sentence:

> **Crowding:** published edges decay, so here is ours measured — on the broad large-cap book we
> track, our own impact model says everyone following it would have to buy roughly **$5bn on the
> same morning** before trading costs cancelled the measured edge, but only about **$7m** if the
> same people crowded into a concentrated all-cap top-25 instead, which is why the tracked book
> is deliberately broad and large-cap.

Shorter, if one clause is wanted: *"Our own impact model puts the point where crowding cancels
this edge at roughly $5bn bought on one morning — a number that falls to about $7m for a
concentrated all-cap list, which is why this book is broad and large-cap."*

**Do not ship either until BUG 1 is fixed.** `/work` currently publishes **void** statistics
(+8.81%/yr, t 5.74 — see BUGS FOUND); adding a fresh, correct sentence beside them raises the
page's authority while the wrong numbers stay up. **Fixing the void numbers is the more urgent
change and is a different lane's call.**

---

## BUGS FOUND

| # | where | what | severity |
|---|---|---|---|
| **1** | `valuation/web/templates/portfolio.html:479-480` (**public** `/work`) | Quotes FF5+MOM alpha **"+8.81%/yr, t = 5.74, 109 non-overlapping windows, 1998–2026"**. CLAUDE.md: *"THE OLD +8.81%/yr … ARE VOID. Do not quote them anywhere."* Corrected values: **+6.99%/yr, NW t 3.984, 68 windows, 2009-01→2025-10**. | **HIGH — void stats on a public page** |
| **2** | `valuation/web/templates/portfolio.html:244` (**public**) | Sector-neutral row quotes "+11.8% → +10.2%" — pre-B6 top-decile alpha; corrected headline is +7.17%. | MEDIUM |
| **3** | `valuation/edge/valquo_index.py:129-133` → `data/valquo_index.json` `method` | The shipped book's own description string quotes **"full 2,710-name / 110-date backtest", "+11.8%/yr", "+11.4% net", "breakeven 236bps one-way vs ~37bps actual", "top-25 … +20.7%"** — every figure pre-B6/void. Renders on the Index tab and is read by the Cowork side. **Same class as the defect found on `worktree-p6-costs-and-robustness`: stale numbers inside a shipped payload read as current, where a stale results file reads as data.** | **HIGH** |
| **4** | `scripts/capacity.py:36` | `BREAKEVEN_BPS = 234.505` hard-coded, commented *"the project's own measurement"* — stale by 4.72x in capacity terms. Should read `costs.top_decile.breakeven_one_way_bps` from `BACKTEST_RESULTS.json`. Any re-run silently reproduces the inflated headline. | **HIGH** |
| **5** | `scripts/capacity.py:124` | Defaults `--panel data/free_analysis/panel.pkl`, which is the **pre-B6 110-date/2,710-name panel**. `panel_corrected_69d.pkl` sits beside it. | MEDIUM |
| **6** | `valuation/edge/valquo_index.py:12` and CLAUDE.md | Both state the large-cap tier is where "the measured IC was strongest". Measured: large **0.0287** is the **weakest** of three (small 0.0313, mid 0.0304). Large *is* strongest by long-short (9.63%), so the design is right and the stated reason is wrong. Per §7 this floor is load-bearing for crowding. | MEDIUM — wrong rationale on a load-bearing choice |

Bugs 1–3 are the **app/product lane**. Bugs 4–5 are the **free-analysis lane** (P1's owner).
Bug 6 spans `valuation/edge/**` (pipeline builder) and the claims-audit lane. **None was fixed
here — this item is a memo, and three of the six sit in lanes held by other sessions.**

---

## What I did NOT do, and why

- **No code written or changed.** The prompt scoped P2 as a memo. The analysis ran from
  `$CLAUDE_JOB_DIR/tmp` and is reproducible from this file's method description, but **it is not
  a shipped script** — so there is no `scripts/crowding.py` and P2 has no reproduce-command of
  its own. If that is wanted, it is a follow-up, and the right move is to **fix
  `scripts/capacity.py` (bugs 4–5) and extend it** rather than add a second capacity script.
- **Did not re-run P1 against yfinance.** ADV for the small/mid-cap books is therefore mostly
  proxied (§4), which is the memo's biggest measurement weakness. Refetching would exhaust the
  Yahoo quota and silently degrade — a known failure mode in this project.
- **Did not add a `RESEARCH_LOG.md` row / did not increment equity `N`.** Nothing here searched
  over the return signal, selected a weight, or tested a predictive hypothesis; it is a cost
  model applied to an already-fixed book. Equity `N` stays **116** (Deflated Sharpe 0.8674).
  Recorded explicitly because the self-penalising direction is to add rows, and choosing not to
  needs a stated reason.
- **Did not quantify the decay channel** (§6) — no data exists on this disk to do it honestly.
- **Did not touch `valuation/web/**` or `valuation/edge/**`** — other lanes hold both.

## Reproduce

Method, in full, so this is checkable without the scratch files:

1. `B`, `K` by fitting `cost = B + λK√AUM` to any two cells of `by_aum` in
   `data/free_analysis/CAPACITY_RESULTS.json`; verify against the other thirteen (residual 0).
2. Capacity `= ((breakeven − B)/(λK))²`; reproduces P1 exactly at `breakeven = 234.505`.
3. Live-book model: `data/valquo_index.json` positions and weights; ADV from
   `data/bulk/prepared/bars/<T>.pkl` (`raw_close × volume`, trailing 63d mean) else P1's proxy;
   σ = trailing-252d std of `raw_close` returns; `base` from
   `fundamental_panel.one_way_cost_bps`; book cost = weight-average; bisect on AUM to 134.113bps.
4. Corrected-panel books: `panel_corrected_69d.pkl`, `settings.WEIGHTS_ESTABLISHED`, composite
   = Σ w·zscore, top-N per date; σ from `data/backtest/prices/<T>.csv`.
