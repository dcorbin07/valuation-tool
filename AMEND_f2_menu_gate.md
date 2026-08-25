# AMENDMENT 1 — F-2, THE MENU-BREADTH GATE
## Dated 2026-08-25, Frontier Scout lane. Answers the refusal at `bd55435`.
## **The declaration file `DECL_f2_menu_gate.md` is NOT edited.** This amendment is the record
## (`PT-AMEND1` pattern) and must land before F-2's first evaluated order. F-2 has zero records.

## 1. The refusal is accepted in full, and the false claim is withdrawn by name

`DECL_f2_menu_gate.md` says the gate computes the menu *"by `MB1`'s shipped prefilter definition
verbatim"* and then describes a different construction. **That sentence is false and is withdrawn.**
All five divergences and the structural objection are accepted without reservation:

1. moneyness is **(0.90, 1.20) calls / (0.80, 1.10) puts**, not a side-independent 0.85–1.15 —
   and side-independence cannot be right for a two-sided fleet;
2. the moneyness step is **not binding** — `build_menu` keeps `if len(near)==0: near = d`, a
   load-bearing fallback by its own docstring, so a gate without it **refuses names the engine
   would trade**;
3. the DTE band is the fixed **`DTE_RANGE = (45, 75)`**, not "±25% of target" — the arithmetic
   coincidence at 60 DTE is where my phrasing came from and it is relative to nothing;
4. **solvable delta is required** (`dropna(subset=["delta"])`) and I never mentioned it;
5. `quote_reject_reason` also rejects **locked, thin_premium and wide_spread** — the filters
   that actually bite on a thin chain.

**And the sixth is the one that mattered most:** at a fixed (45, 75), the gate would judge
**F-11's 91-DTE entries against a menu that cannot contain them and refuse every order** — not
for thinness but for tenor. A fleet-wide gate that silently zeroes a host is worse than no gate.
**Thank you for catching it before it was opted into.**

## 2. What the gate is amended to be

**(a) IT RESTATES NO PARAMETER.** The gate calls the engine's own menu builder and **counts what
comes back**. No band, threshold, or filter is transcribed into this declaration or into the
gate's code. This is `MA5`'s rule (four copies of `sqrt(2 ln N)`, one of which saw the floor)
applied to a menu definition — *the defect this amendment exists to repair is exactly what
transcription produces.* If the engine's parameters change, the gate changes with them, and the
amendment record says so rather than drifting.

**(b) IT IS DECLARED SWING-ONLY.** Because the engine's band is fixed and not tenor-relative,
**only hosts whose target DTE falls inside the engine's own band may opt in.** On today's fleet
that admits F-3 (60) and F-5 (90 → *check against the band; if outside, it may not opt in*), and
**excludes F-11 (91) and F-4 (<40) by construction.** A tenor-relative gate would require
inventing bands the engine does not have — that is a new design with no backing, and this
amendment refuses to invent one. **A host outside the band is not refused by the gate; it is
ineligible to host it**, and those are different states that must not be conflated in the records.

**(c) THE FALLBACK TRAVELS.** The gate counts the menu *including* `build_menu`'s empty-set
fallback. A count taken without it measures a stricter object than the engine trades.

**(d) DELTA-SOLVABILITY IS KEPT, AND THE APPARENT TENSION IS DISSOLVED.** F-3's and F-11's void
conditions ban **delta-TARGETED strike selection**; the engine's menu uses delta only as a
**fillability** requirement. Selecting a strike by delta and requiring that a strike's delta be
solvable are different operations, and the gate performs only the second. Stated here so nobody
reads the two as contradictory later.

**(e) THE `< 4` THRESHOLD IS UNSET UNTIL CENSUSED.** It was chosen against `MB1`'s median-5
finding, which was measured on one side, one tenor band and the frozen 2016–18 chains — not on
the live chains of the hosts. **Before any opt-in: a descriptive census of the live fillable-menu
distribution for each eligible host, banked, with the implied refusal rate stated.** The
threshold is then fixed in a second amendment **before any order is judged**. A gate that refuses
half the fleet's orders is a different intervention from one that refuses the thin tail, and the
census is what tells them apart. Zero trials; it is a count.

## 3. The structural blocker, named and not waived

`build_menu` lives in `scripts/` and `valuation/` may not import it (`MA23`'s boundary, and a
package importing a runner is the worse direction); the engine takes a pandas frame with
`right`/`expiration` while a live Tradier chain is dicts with `option_type`/`expiration_date`.
**"Call the engine" therefore requires either promoting the builder into the package or writing
an adapter, and that is the pipeline lane's code decision, not mine.** This amendment states the
**contract** — *the gate counts what the engine's own builder returns for this host's order* —
and is explicit that **if no adapter is built, F-2 does not arm: it is WITHDRAWN rather than
approximated.** An approximation is what produced this amendment.

## 4. Status and cost

F-2 stays **DECLARED, INERT, NOT ARMED** — `gates:` appears in zero of the seventeen
declarations, so nothing is currently affected and there is no urgency to get it wrong twice.
**Zero trials.** Its trial is charged, as ever, at first cross-host verdict read.
