# PROMPT — data miner: the ThetaData Pro harvest. Deadline 2026-09-01.

**Owner:** data miner. **Handoff:** `HANDOFF_data_mining.md`.

**HARD DEADLINE: the ThetaData Pro subscription expires 2026-09-01** — about fifteen days.
Anything not pulled by then is permanently unreachable. Standard's 8-year window only rolls
*forward*, so the early history gets less accessible every year, never more. Every design
decision below follows from that one fact.

This is a **COLLECTION** job. You are not testing a hypothesis, you are not scoring anything,
and you charge **zero trials**. Do not analyse what you pull beyond the integrity checks.

---

## 1. The gap you are filling — measured, not assumed

The existing freeze holds 3,885 alert-days, 29,785 contract histories (O11 verified 120 of 120
sampled contracts present, median 40 mark-days, zero short of `held_days`) and 70.3M tick prints
across 3,884 days. What it does **not** hold:

> **3,869 of 3,884 full-chain days — 99.6% — are ENTRY dates.**

A banked contract can be priced across its whole life. The **entire chain on day 20 of a holding
period does not exist**. That single gap is why O10, O18, U6, O3 and O21 are dead or voided —
rolling, wing selection, re-selection and every "choose a different contract mid-flight" test
needs it. It was a bandwidth decision when the freeze was built, **not a subscription limit**.
Pro removes both the depth limit and the excuse.

## 2. Storage — decided, and not negotiable

**Raw pulls go to `D:\` (405GB free). NOT the laptop (215GB free).**

- Take the raw root as a **parameter with a `D:\` default**. Do not hardcode a path under the
  repo. `data/` in the repo is for **derived artifacts only**.
- **Derive once, read forever.** Raw chains sit cold on D:. You build the compact analysis panels
  once — a few hundred MB, not a few hundred GB — and those are what lives with the code and what
  every later backtest reads. Nothing downstream should ever re-scan the raw. If D: is an external
  drive this is the difference between a fast pipeline and a permanently slow one.
- **SECOND COPY — a requirement, not a nicety.** After 2026-09-01 none of this is re-fetchable, so
  a single-drive copy is a single point of failure for an irreplaceable asset. Don has already had
  a drive die this way (a Lexar that went read-only at the controller, unrecoverable). Write a
  **checksummed manifest of every pulled unit** alongside the payload, and **mirror the manifest
  and the derived panels to the laptop as you go**. If D: dies you lose the bulk but keep an exact
  record of what existed and what it hashed to — the difference between a setback and not knowing
  what you lost.
- **Report free space on BOTH volumes on day one, with your projected total, before pulling
  anything.** Sizing check: the tick cache alone is 4.72GB for 3,884 *entry* days. Roughly 3,885
  alerts × ~40 mark-days is ~155,000 chain-days; at EOD chains that is plausibly 40–150GB, but
  **at tick resolution across holding periods it is ~190GB+ and would not fit on the laptop at
  all.** Which of those two jobs you are running changes everything, so establish it first and
  say so in the handoff.

## 3. The queue — strictly in this order

Ordered by (research value × perishability), so that if the clock runs out, the work that got
done is the work that mattered most.

**TIER A — holding-period full chains for banked alert days in 2016–2018.**
The intersection of *most needed* and *least recoverable*: those years sit outside Standard's
window entirely, so they are gone the moment Pro lapses. Start here.

**TIER B — the same, for all remaining alert days (2018–2026).**
Same product, the rest of the book. Recoverable on a future Standard subscription, so it yields
to Tier A — but it is the largest single unblock, since five dead items depend on it.

**TIER C — 2016–2018 backfill for the P1S0 optionable universe.**
P1S0 failed its pre-registered both-halves rule because the 2016–2020 half is absent (cumulative
alpha at H=252 is −0.08%). Pipeline builder is running the control that decides whether that is a
period effect or an optionable-universe effect. **Pull the window now regardless of that answer**,
because after Sep 1 the option no longer exists.

**TIER D — 60–90 DTE chains across the delta band for the Valquo Index's 86 names.**
Serves the deep-ITM financing test (the frontier measured rf+43bps, flat across tenor) and the
pre-registered DTE × delta grid. Smallest and most speculative; last on purpose.

## 4. Engineering requirements — the deadline makes these non-negotiable

1. **RESUMABLE OR IT IS WORTHLESS.** A manifest of `(tier, symbol, date)` units with per-unit
   status, written after **every** unit, not every batch. Then **actually test the resume path —
   kill the process and restart it — before launching the real run.** Do not assume it works. A
   two-week pull that dies on day nine with no checkpoint is a total loss and cannot be redone
   after Sep 1. This is the highest-value ten minutes in the whole job.
2. **DO NOT OVERWRITE THE EXISTING FREEZE.** Write to a new dated path alongside it. The freeze
   carries fingerprints and banked verdicts depend on them; silently replacing bytes an old
   result rests on is the worst outcome available here.
3. **OVERLAP IS A TEST, NOT A WASTE.** Where a new pull covers a day the freeze already holds,
   **compare rather than skip.** Agreement validates the new data. **Disagreement STOPS THE RUN
   and is reported in full** — it means either the vendor revised history or the miner is wrong,
   and you need to know that before five unblocked items get built on it.
4. **NEVER COMMIT `data/`.** Hard project rule, gitignored, licensed vendor bytes. Commit the
   scripts and the manifest summary; never the payload. Check what a clean tree actually contains
   before your first commit — a sibling project found `git add -A` would have swept an entire
   licensed archive in from a path its ignore rule did not cover.
5. **Reuse `ThetaBulk`** (`valuation/edge/theta_bulk.py`). It already has backoff, asymmetric
   fault counting, `depth_report`, `span_is_stale` and symbol×year caching. **Respect the rate
   limits — a ban costs more than a slow run**, and there is no second attempt after Sep 1.
6. **A DAILY PROGRESS LINE** appended to the handoff: units done / units remaining / GB pulled /
   **projected finish date**. Don needs to know **by day three** whether this lands before the
   deadline, while there is still time to cut Tier D or narrow Tier B. A harvest that quietly
   runs out of clock on day fourteen is a failure that was visible on day three.

## 5. Lane safety

You own **new mining scripts** and **writes under the raw root and `data/`**. You do **not** edit
`valuation/edge/options_*.py` — options bot is live in that lane right now. If you find a bug
there, report it in your handoff; do not fix it. Do not touch `.github/`.

## 6. Report

`HANDOFF_data_mining.md`:

- free space on both volumes, the projected total, and **which job this is** (EOD chains vs tick)
- the queue with per-tier completion, and the daily progress lines
- the **overlap comparison result** — agreement rate against the existing freeze, and any
  disagreement quoted in full
- **the resume test you actually ran**, described concretely
- `## BUGS FOUND`
- **what was NOT pulled and why** — after Sep 1 this section is the permanent record of what is
  unreachable, and it is the part a future session will need most

Ledger row for the harvest. **Zero trials — collection is not a test.**
