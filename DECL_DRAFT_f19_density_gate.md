# DECL DRAFT — F-19: THE ALERT-DENSITY GATE (fleet-wide convention, not a book)
## Tag: [O11 (the measured, never-registered split: +14.28% expectancy above the 90th-percentile alert week vs −4.51% quiet, 51.5% of trades in >10-alert weeks) — B-13 is the freeze register twin; neither gates the other]

**A LABELING GATE — unlike F-2 it refuses nothing.** To be committed ALONE before any
opted-in host's first fill.

**The rule (frozen):** the harness computes, weekly, the market-wide alert-count percentile
vs the trailing 2 years (a descriptive count from the live daily scan). Every entry of an
opted-in host is **stamped** `density_pct` at order time and binned **HIGH (≥90th)** or
**NORMAL (<90th)**. No entry is blocked, sized, or timed by the stamp — the gate only
labels, so the cells are clean.

**Host attachment rule:** a host opts in **in its own declaration** via
`gates: [alert_density]`, before first fill; the stamp then rides every entry or none.
A host may also declare a **density-gated VARIANT** (trades only in HIGH weeks) — that is a
separate book with its own declaration, records, horizon, and trial; the gate itself never
mutates a host's behavior.

**Records:** the weekly percentile series (kept as a first-class fleet record with its
computation inputs), and the per-entry stamp on opted-in hosts.

**Verdict (cross-host):** at first read — HIGH-vs-NORMAL cell contrast per host and pooled,
with per-cell `O26`-floor (a cell under 15 fills is UNDERPOWERED, never null). Minimum
effect of interest, fixed now: a **+10pp per-trade** (long) / **+0.75% secured-cash**
(short) HIGH−NORMAL spread; `power_gate.state()` line at commit. **The HIGH cell will
accrue slowly by construction (~1 week in 10)** — the honest horizon is set by the HIGH
cell, not the calendar, and the declaration says so.

**Trial:** 1, options, at first cross-host verdict read.

**Void:** any host behavior change from the stamp outside a separately-declared variant;
re-binning after fills; reading cells below the floor.
