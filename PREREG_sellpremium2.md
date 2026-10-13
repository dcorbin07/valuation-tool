# PREREG — SELL-PREMIUM-2 — the strike rule that keeps the income

**EXECUTOR'S REGISTER. COMMITTED ALONE, MARKDOWN ONLY, ZERO `.py`, A STRICT GIT ANCESTOR OF EVERY
MEASUREMENT COMMIT** (`RESEARCH_CHARTER.md` §3). Executes the Frontier Scout's
`PREREG_DRAFT_sellpremium2.md` (`1e97caf`). **4 options trials, booked BEFORE any runner exists.
Paper only; nothing adopted; no real trade, ever** (`O11` governs).

**THE DRAFT IS ACCEPTED, with twelve amendments `T1`–`T12` made BEFORE any outcome exists.**
Everything not named below carries over unchanged and is not restated: §1's diagnosis, §2's
asymmetry, §3's three reasons for the 25-delta rule and its family-closes clause, §4's
risk-selection limitation, §5's inherited findings, §6's arms and survivability grid, and §7's
void conditions and expectations. **Where an amendment and the draft disagree, the amendment
governs.**

**THE PROMPT'S TWO CONSTRAINTS ARE OBEYED AND NEITHER IS TOUCHED: the crash bar stays 6.0 and the
synthetic single-name stress row stays.** What changes is the CONSTRUCTION, which is the one thing
a successor is permitted to change, and which is the thing `SELL-PREMIUM`'s own handoff named.

---

## T1 — DON'S 2026-10-12 RULING IS NOW IN `DECISIONS.md` AND IS CITED THERE

`SELL-PREMIUM` had to quote the ruling from its lane prompt and record that `DECISIONS.md` carried
no 2026-10-12 line. **It now does** (`DECISIONS.md:36`), landed by the manager while that register
was executing, and `tests/test_sellpremium.py` already pins that the file and that register agree
clause by clause. **This register cites the file.** The pass rule it supplies:

> *"it is profitable net of realistic costs on the capital it ties up, in both halves; it beats
> the same trade placed on random days in the same names (so the timing is shown to matter); it
> survives realistic sizing and concurrency (O11) and the pre-committed crash stress. The
> comparison with simply buying the shares is REPORTED for context and carries no verdict."*

`A1` is clause (a), `A2` is clause (b), the survivability grid is clause (c), **`K3` is the
pre-committed crash stress and runs FIRST, in its own pass.**

---

## T2 — THE DRAFT'S "≈ 25 DELTA" ROW IS A 20-DELTA PUT, AND THE KNIFE EDGE IS NOT THERE

**The draft's §2 table reproduces EXACTLY** — its calibration recomputes to **IV 0.286370**
against its stated 0.2864, every row matches to two decimals, and its control row reproduces the
predecessor's **8.90** to the digit. The table is sound. **Its LABEL is not.**

§2 marks **m = 0.925** as *"≈ 25 delta"* and shows that row's delta as **−0.202**, and §3.2 then
says *"a 25-delta put sits at m ≈ 0.925 and delta −0.202"*. **A 25-delta put has delta −0.25. The
0.925 row is a TWENTY-delta put, so the declared RULE and the declared FORECAST are computed at
two different strikes.** Solved at the draft's own calibration:

| | moneyness | delta | premium / strike | income / yr | synthetic loss | **years** |
|---|---|---|---|---|---|---|
| the draft's "≈25d" row | 0.9250 | **−0.202** | 1.2770% | 7.3140% | 41.28% | **5.64** |
| **TRUE 25 delta** | **0.9398** | **−0.2500** | **1.6602%** | **9.5085%** | **42.20%** | **4.4385** |
| at `V6-OPT`'s measured median delta −0.2638 | 0.9438 | −0.2638 | — | 10.1735% | — | 4.1725 |

**SO THE FORECAST IS 4.44 YEARS AND NOT 5.64, AND THE HEADROOM IS 1.56 YEARS (26%) RATHER THAN
0.36 (6%). THE KNIFE EDGE THE DRAFT DECLARED DOES NOT EXIST AT THE RULE IT DECLARED.**

**THIS RUNS TOWARD CLEARING, SO IT IS DISCLOSED AND NOT RELIED ON.** `K3` is still computed on the
register's **own measured net income at its own strike rule** and never from this table — the
draft's void condition 4, kept. The correction is recorded because a register whose forecast is
computed at a different strike from its rule cannot score its own expectation, not because the
larger number is wanted.

**EXPECTATION 1 IS RE-PRICED BEFORE ANY OUTCOME, WITH THE REASON.** The draft put `K3` clearing at
**60/40** on the belief that it faced 6% of headroom. At 26% the honest prior is **85/15**.
Re-pricing a prior after seeing an outcome would be worthless; re-pricing it after correcting an
arithmetic label, before anything is measured, is what pre-registration is for. **Both numbers are
on the record and the draft's is not edited.**

**AND IT STRENGTHENS THE DRAFT'S OWN §3.2 ARGUMENT.** That section's ceiling — past about 0.95 the
delta passes −0.29 and assignment becomes a coin flip — now has **more** room beneath it, since
true 25 delta sits at 0.9398 rather than at the 0.95 boundary.

---

## T3 — THE 0.85–0.95 MONEYNESS BAND IS REMOVED FROM SELECTION, AND INHERITING IT WOULD HAVE BEEN A SILENT LOW-VOL TRUNCATION

`SELL-PREMIUM`'s funnel carries a **0.85–0.95 moneyness band** as a selection step, and
`valuation/studies/sellpremium.py`'s `put_funnel` has it as a default. **A 25-delta rule must not
inherit it.** Where a 25-delta put sits in moneyness is a function of the name's own volatility —
that is the whole point of a delta target (draft §3.3) — so a fixed band truncates the rule
**exactly in the low-vol names**, where a 25-delta put sits closest to the money. At the
calibrated IV of 0.2864 true 25 delta is at **0.9398, inside the band**; at a materially lower IV
it is **outside it**, and those rows would vanish with nothing raising.

**So the search is over the WHOLE chain within the DTE band for the put nearest 25 delta, with no
moneyness filter.** The realised moneyness distribution is a **REQUIRED REPORTED FIELD**, and
**the share of picks falling outside 0.85–0.95 is measured and reported as the cost of the band
this register declined to inherit.** That is `MA58`'s rule obeyed in the safe direction: widening
a filter **on a construction argument before any arm runs** is the opposite act from widening it
after seeing returns, and the reason is recorded here so a reader can check which happened.

---

## T4 — WHERE DELTA COMES FROM, AND WHY THE FUNNEL STILL READS THE RAW LAYER

`SELL-PREMIUM` measured that **`options_derived` is two-sided on 1.0000 of its rows BY
CONSTRUCTION**, so a quote-coverage funnel measured there reads 1.000 having checked nothing
(`MB21`'s `C1`). It is also the only layer carrying `delta`. Both facts are honoured:

* **The COVERAGE FUNNEL and the TRADED QUOTE read the RAW layer** — unchanged.
* **Delta is JOINED onto the raw two-sided rows from the derived layer.** A raw two-sided row with
  **no derived counterpart has an UNKNOWN delta and is EXCLUDED AND COUNTED** — never read as
  zero, which would make every such row look like a deep-out-of-the-money put and bias the pick.
  The join loss is a **required reported field**, because if it is large the selection is being
  made on a filtered subset and the coverage figure means something different.

---

## T5 — `K3`'s STATISTIC IS THE PREDECESSOR'S, UNCHANGED, AND MUST REPRODUCE ITS NUMBER

The two registers' `K3` figures have to be commensurable or the comparison that justifies this
successor is meaningless. **The statistic is therefore identical in every part**: the median
premium as a fraction of strike at the **picked** contract, the median DTE, `turns_per_year =
252 / median DTE`, the loss `(x − (1 − m)) / m` at the register's own median moneyness, the same
`K3_MAX_YEARS_OF_PREMIUM = 6.0`, and the **same synthetic row** — a single name falling **1.4× the
worst index episode**, which the predecessor measured at **−45.65%** and whose 39.649% loss pins it.

**CONTROL, GATING: running this register's own `K3` code path at the PREDECESSOR's 0.90-moneyness
picks must reproduce 8.900816 years.** If it does not, the two numbers are not the same statistic
and the comparison is withdrawn before any verdict is read.

---

## T6 — THE EVENT SET IS RE-DERIVED AND MUST REPRODUCE THE BANKED ONE EXACTLY

The event, the point-in-time $10B tier and `X1`'s ticker half are **imported from
`valuation/studies/dipcall.py`** and never re-defined (`B7`). The event set is **re-derived rather
than read from `SELLPREMIUM_EVENTS.pkl`**, and then **required to equal it exactly** — 4,864 tier
events over 398 names and 759 dates. A register that reads its predecessor's event pickle cannot
tell a shared definition from a shared file.

---

## T7 — ONE CHAIN READ, TWO PICKS, A PROVABLY IDENTICAL ROW SET

`A3′` is the **paired** 25-delta-minus-0.90-moneyness difference on the **identical** events, so
both picks are made in **one pass over one chain read**. Two passes would let the row set drift and
would confound the strike rule with whatever else moved — `S3`'s and `DIP-CALL-3`'s construction,
and the reason `S25-REPAIR` could attribute its result at all. **The paired population is the
events where BOTH rules price; the coverage of each is reported separately**, and a large
difference between them is itself a finding about the band `T3` removed.

---

## T8 — `K1` IS RE-MEASURED ON THIS REGISTER'S OWN RULE, AT THE PREDECESSOR'S FLOORS

`O-1`'s lesson: coverage is measured on the arm's own population and never inherited — its
published *"~75%"* was an alert-book figure applied to the panel, ~17× wrong. **Floors unchanged
and unrelaxed: ≥ 400 priceable events and ≥ 150 distinct covered event days** (`W-28`). The
predecessor cleared them by 6.4× and 4.1× under a *narrower* filter, so a failure here would
itself be a finding about the delta search rather than about coverage.

---

## T9 — TRIALS, MULTIPLICITY AND CRITICAL VALUES

**4 OPTIONS TRIALS** — one each for `A1`, `A2`, `A3′`, `A4` — **booked BEFORE any runner exists**,
options `N` **315 → 319**. `K3` and `K1` charge **ZERO**: a control can only ever BLOCK a finding,
never produce one (`MB1-SEL`).

**BH at q = 0.10 across `k` = 4, on TWO-SIDED *p***; thresholds **0.025 / 0.05 / 0.075 / 0.10**,
membership fixed here. **`k` is FIXED and a firing kill does not shrink it** (`W-28`).

**The hurdle is DERIVED at run time, never typed** (`MA5`, `MA37`, `MB32`). At registration it
reads **3.3919235** at `N` = 315 and **3.3956416** at 319; **both are recorded as of today and
neither may be quoted later.**

**EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`), and **no X7 or
`CORRECTED-FLOORS` figure is quoted anywhere** (`UNIVERSE-BIAS` part 2).

---

## T10 — `V6-OPT`'s HEALTH FLOORS ARE IMPORTED AND RE-TUNING THEM IS A VOID CONDITION

`A4` asks whether health discriminates at 25 delta and **the expected answer is NO** — it is run
to close the question, not to open it. The floors come from `V6-OPT`'s own source (`B7`) and
**re-tuning them voids the item** (`V6-OPT` §6.3). **A null here is the prediction and may not be
reported as a disappointment.**

---

## T11 — A STAGE-1 PASS IS `ELIGIBLE-BUT-UNRESOLVED`

Inherited verbatim from `V6-OPT` through `SELL-PREMIUM`: the build quadrant's options era is
**2016–2019**, whose worst 32-session index move is **−14.31%**, so **Stage 1 contains ZERO 30%
crashes** and a short-vol book's whole risk sits in exactly those.

> **A clearing arm is recorded `ELIGIBLE-BUT-UNRESOLVED`, never `ADOPTED`, and may not be quoted
> without that label. Nobody may read a rejection here as evidence that cash-secured puts do not
> work.**

**A decisive REJECT is available to this design and a decisive ADOPT is not.** The crash question
is answered at Stage 2 — one read of 2020–2026 × half 1 — and **the check quadrant stays CLOSED in
this item.**

---

## T12 — VOID CONDITIONS

The draft's eight carry over, with two added:

1. **No grid.** One strike rule (25 delta), one tenor band (20–60 DTE), one `k` (2.5).
2. **The 6.0 bar may not be relaxed and the synthetic row may not be dropped.**
3. **No third strike rule if `K3` fires — the family closes**, then or ever.
4. `K3` may **not** be computed from the draft's §2 table; it uses the register's own measured net
   income at its own picks.
5. Quoting `V6-OPT`'s income or SD as this register's own — a different population and era
   (`MB8`: an se may not travel across perturbation sizes, and a strike change is one).
6. Quoting `A3`'s **−7.99% of max risk** against any **% of secured cash** figure as commensurable.
7. Reading a `K3` pass as evidence the book survives a crash — `K3` is stress **arithmetic**, not
   an outcome.
8. Treating `A4`'s expected null as a failure.
9. **NEW: quoting the draft's 5.64-year forecast as this register's** — it is a 20-delta figure
   (`T2`).
10. **NEW: applying a moneyness band to the 25-delta selection** (`T3`), or reporting its coverage
    against the predecessor's band-filtered figure without saying the filters differ.

---

## EXPECTATIONS

The draft's seven carry over, with expectation 1 re-priced by `T2` **before any outcome** and the
reason recorded:

1. **`K3` clears at 25 delta — the draft said 60/40 on a 6%-headroom reading; corrected to
   85/15 at 26% headroom** (`T2`). The residual risk is that measured net income lands below the
   mid-based forecast, which is the direction `T2`'s own disclosure names.
2. `A1` clears in both halves: **75/25**.
3. `A2` clears: **55/45** — the hardest arm, and the one Don's clause (b) makes a requirement.
4. `A3′` shows 25 delta beating 0.90 moneyness on return: **80/20**.
5. `A4` finds health NOT discriminating: **70/30**.
6. The whole register passes every leg: **40%**, raised from the draft's 30% by `T2` alone.
7. Don adopts it: **15%**.
8. **NEW (executor): more than 5% of 25-delta picks fall OUTSIDE 0.85–0.95 moneyness, i.e. the
   band `T3` removed would have bitten: 60/40.** Post-dip IV is elevated, which pushes a 25-delta
   put further out and back inside the band, so this is genuinely uncertain.

---

## WHAT THIS REGISTER DOES NOT SAY

It is **not** a finding that selling premium after a drop works — no arm has run. It does **not**
reopen `V6-OPT`, and it does **not** claim that register's condition 2 was wrong — only that Don
has removed it from the pass list. It does **not** weaken `SELL-PREMIUM`: its `K3` was correctly
computed, correctly fired, and **its five trials correctly stay charged**. It makes **no claim
about index options**. And it proposes **no trade**: `O11` binds, paper only, and **adoption is
Don's and is a vintage event.**
