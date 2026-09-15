# DECL DRAFT — F-2: THE MENU-BREADTH GATE (fleet-wide convention, not a book)
## Tag: [O13-Q3a (its pool refused nothing — cited) / MB1 (the fillable-menu instrument) / MB1-SEL (coverage conditions outcomes in BOTH books)]

**A GATE: hosts attach it; it holds no positions.** To be committed ALONE before any opted-in
host's first fill.

**The rule (frozen):** at order time, compute the host entry's FILLABLE IN-BAND MENU by
`MB1`'s shipped prefilter definition verbatim (calls-or-puts per the host's side → DTE band
±25% of the host's target → moneyness 0.85–1.15 → two-sided usable quotes → volume > 0).
**If the fillable count < 4, the entry is REFUSED.** No overrides.

**Host attachment rule:** a host book opts in **in its own declaration** via a
`gates: [menu_breadth]` line, before its first fill. Attachment after fills is a new
declaration. The gate applies to every entry of an opted-in host, or none.

**Records (ride the host's rows):** the menu census at order time; for REFUSED entries, the
full would-have-been quote pair and menu detail — the counterfactual is quote-marked and the
declaration states that limitation now (a quote-mark is not a fill; `O10`'s C2 lesson).

**Verdict (cross-host, per-host cells):** at first read — refused-entry counterfactual
quote-marked outcomes vs taken-entry outcomes, per host and pooled. Minimum effect of
interest, fixed now: refusal improves an opted-in host's per-trade mean by **+5pp** (long
books) / **+0.5% of secured cash** (short books). `power_gate.state()` line filled at commit.

**Verdict horizon:** reads with its hosts — earliest when any single host reaches its own
horizon with ≥10 refusals recorded; the refusal RATE is reported descriptively from week one.

**Trial:** 1, options, at first cross-host verdict read (the gate is its own question).

**Void:** refusing on any feature other than the frozen menu count (`O13`-Q3a's single-
feature caution is faced by being exactly one pre-named feature, chosen for its `MB1-SEL`-
measured mechanism); host-selective application; reading cells before the host's horizon.
