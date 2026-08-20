# DECL DRAFT — F-1: THE FILL A/B (fleet book #1)
## A cost experiment riding every other book's orders. Tag: [O10/O18 — the live question O10 itself named open]

**To be committed ALONE by the options-bot lane before any fleet order is placed.** This is
the harness's first citizen because it consumes every other book's fills and therefore has
the fleet's shortest verdict horizon.

**Hypothesis (cost, not alpha):** working entries as mid-limit orders captures a material
fraction of the quoted half-spread vs marketable orders. `O18` measured ρ = 0.6743 on banked
prints (real trades pay ~67% of the half-spread) — the A/B asks what THIS operator's paper
flow captures, forward, with zero look-ahead risk.

**Entry rule (frozen):** every order any fleet book submits is assigned by the harness's
deterministic randomizer to arm A (marketable) or arm B (limit at mid, worked 60 seconds,
then cancel-and-market; the fallback fill is recorded as B-fallback, never silently pooled).
No exceptions, no overrides; a book may opt out only in its own declaration, before fills.

**Structure/universe/sizing:** none of its own — it inherits the fleet's.

**Records:** per order — book id, arm, quote pair at submission, fill price and time (or
unfilled fate), fallback flag, venue if reported. The per-order half-spread capture is
computed at read time, not stored (no derived outcome statistics in the record stream).

**Verdict horizon:** ~60 paired fills. At the fleet's Wave-1 cadence (est. 30–60 orders/
month across books — a descriptive projection from the entry rules' firing rates, to be
re-stated at launch) that is **1–2 months**. Meter: paired mean capture difference,
anytime-valid CI per the harness; minimum effect of interest fixed now at **10% of the
quoted half-spread** (below that, execution style is a matter of taste, and the declaration
says so).

**Verdict grammar:** B-CAPTURES (CI above +10%) / NO-MATERIAL-DIFFERENCE (CI inside ±10%) /
B-COSTS (unfilled-fallback drag pushes CI below −10%) / horizon-not-reached.

**Trial:** 1, options domain, at first verdict read (harness §2).

**Void:** overriding the randomizer; reading before horizon without booking the charge;
quoting capture as strategy P&L anywhere.
