# PRE-REGISTRATION — SC-3 (TIER-E-FIN): does the financing case change at a tenor we now own?

**Committed ALONE and BLIND. Markdown only, zero `.py`. A strict git ancestor of every commit
that computes a COST VERDICT — precisely stated, because the coverage census of s2 necessarily
solves parity per pair to decide scoreability and therefore already touches rates. That census
lands in the NEXT commit, after this one, and this register is an ancestor of it too; what it is
NOT is an ancestor of the census RUN, which happened first by design and whose counts are quoted
in s2.** Options trials: **2**, booked BEFORE any runner exists.
**ADOPTS NOTHING. `O11` GOVERNS. This is a COST measurement and licenses no trade.**

---

## 1. WHAT THIS IS, AND WHY IT IS NOT A RE-RUN

`DEEPITM-FIN` measured whether a deep-ITM call is cheaper leverage than margin, at **60–90 DTE**,
and answered no: **all-in `rf + 701.87` bps/yr** — financing **342.35** + roll **340.06** +
commission **3.57** — at median DTE 73 and **5.0 rolls/yr**. Against the three retail cards it is
**more expensive than Robinhood Gold (`rf + 420`) and IBKR Pro (`rf + 150`)**, and cheaper than
only Robinhood standard (`rf + 995`).

**Its closing reading is the thing being tested here, quoted rather than paraphrased:** the
financing benefit *"REQUIRES rolling"*, so **60–90 DTE, the SHORTEST tenor, is the worst case** —
*"only clearly positive at a tenor we do not own."*

**`MB4` then closed the tenor question, and it closed it on OWNERSHIP rather than on economics:**
*"Financing improves with tenor: CLOSED as unownable — the owned cache is hard-capped at 200 DTE
and the Tier E pull reaches 858 DTE only for 2016-2018."* **`S3-I5` lifted the Tier-E quoting
block. The ground MB4 closed it on is gone**, which is what makes this a legitimate re-open rather
than a second look at a settled number.

**WHAT IS NOT RE-OPENED, AND `MB4` IS OBEYED HERE.** MB4's re-open condition is a **number, not a
research result**: *"if the operator's borrowing rate ever exceeds rf + 702 bps, the deep-ITM call
becomes the cheaper leverage and DEEPITM-FIN has already priced it… **Nobody should spend a trial
re-deriving this.**"* **This register does not re-derive the 60–90 DTE figure, does not re-price
the cards, and does not reopen the five other arguments MB4 closed** (defined-risk sizing, tax,
collateral, alpha-in-the-expression, and the today's-brokers comparison). It measures **one thing
MB4 could not**: the all-in cost at 200–858 DTE.

**THE MECHANISM IS ARITHMETIC AND IS STATED BEFORE THE RUN, so a reader can check whether the
answer was predictable.** The roll leg scales with **rolls/year = 365 / DTE**. DEEPITM-FIN
measured 5.0 rolls/yr at median 73 DTE; the census below measures **0.89 rolls/yr at median 409
DTE**, a **5.6× reduction in roll frequency**. If the roll leg falls proportionally, ~340 bps
becomes ~**61**, and if financing itself holds near 342 the all-in lands near **`rf + 407`** —
**below Robinhood Gold's `rf + 420` and still far above IBKR Pro's `rf + 150`.** **So the
hypothesis is that ONE of the two live cards flips and the other does not.** That is falsifiable
in three directions: both flip, neither flips, or financing does not hold near 342 at long tenor.

---

## 2. THE COVERAGE CENSUS — ALREADY RUN, AND READ BEFORE THIS REGISTER WAS WRITTEN

`O-1` returned **0.19% power** because a coverage figure measured on the ALERT BOOK was applied to
the PANEL; `W-14` died on a premise nobody had measured. **So the census ran first**, and it is a
fact about what data exists rather than an outcome — the `S25`/`MB15`/`MB3` precedent, and
`MB1-SEL`'s rule that a control can only ever BLOCK a finding, never produce one.

Measured on the **PINNED** Tier E harvest freeze, 2016–2018, `scripts/sc3_coverage.py`:

| | SC-3 (200–858 DTE, 2016–18) | `DEEPITM-FIN` (60–90 DTE, 2016–2025) |
|---|---|---|
| chain rows in band | **35,396,569** | — |
| two-sided matched pairs | **16,183,817** | — |
| **scoreable pairs** (delta band + parity solve) | **2,352,345** | **12,904** |
| **names** | **411** | 185 |
| names reaching `MIN_N` = 30 | **408** | — |
| dates | 754 | — |
| DTE min / p25 / median / p75 / max | 200 / 242 / **409** / 606 / **858** | — / — / 73 / — / — |
| rolls per year at median DTE | **0.89** | **5.0** |
| pairs by year | 2016 660,590 · 2017 778,022 · 2018 913,733 | — |

**The design is not coverage-limited and it is not power-limited** — see §4. That is the opposite
of `O-1`'s position and it is knowable in advance, which is the point of running the census first.

**AN HONESTY NOTE ON BLINDNESS, STATED BECAUSE THE HISTORY CANNOT SHOW IT.** The census computes
`excess_mid_bps` and `excess_exe_bps` per pair as a by-product of deciding which pairs are
scoreable at all — the parity solve is the scoreability test. **No summary statistic of those
columns has been computed or read, and every figure in this register comes from COUNTS and DTE
alone.** The register's blindness to the outcome is therefore a claim about what I have looked at,
weaker than the git-provable blindness of a register written before any data touched disk, and it
is recorded as the weaker claim (`EVOWN`'s ordering caveat, inherited).

---

## 3. THE OBJECT, AND THE STRATA ARE FIXED HERE

* **Instrument: `DEEPITM-FIN`'s own, IMPORTED.** `matched_pairs`, `call_delta`, `implied_rate`,
  `pv_dividends`, `annual_cost`, `load_spot`, `load_dividends`. **Only the DTE band moves.** A
  second copy of the pair builder would stop this being the same measurement at a different tenor
  (`B7`).
* **Delta band `0.85–0.95`, `MIN_N` = 30, commission and the `rf` source: all `DEEPITM-FIN`'s,
  reused verbatim** so the two numbers are comparable. Nothing in this register re-tunes them.
* **Price conventions: BOTH, as DEEPITM-FIN did.** MID (buy call at mid, sell put at mid) and
  **EXECUTABLE** (buy the call at the **ask**, sell the put at the **bid**). **The verdict is
  taken on the EXECUTABLE leg**, which is the conservative side and is the convention
  DEEPITM-FIN's own headline correction established.
* **THE UNIT OF INDEPENDENCE IS THE NAME, NOT THE PAIR.** 2.35M pairs are ~408 names observed on
  many days on overlapping contracts; treating them as independent would overstate precision by
  orders of magnitude. **Every headline is a per-name median, then a cross-name statistic over the
  408 names**, which is `DEEPITM-FIN`'s own `per_name` treatment and its `MIN_N` floor.
* **The median is used and is NOT banned here.** The ban is scoped to **RETURNS** (`EVOWN`'s
  narrowing, `MB1-SEL`'s AST pin); this is a **COST in bps**, and `DEEPITM-FIN` reported medians
  throughout. Using a mean on a rate distribution with solver outliers would be the less robust
  choice, not the more honest one.

**TENOR STRATA, FIXED BEFORE ANY COST IS READ, so nothing is swept and then reported at its best
cell:** **200–300, 300–450, 450–650, 650–858 DTE.** These are round numbers placed near the
census's own quartiles (242 / 409 / 606) so each stratum is populated. **They are chosen on
COVERAGE — where the data is — and not on any outcome**, and the distinction is the one this
record draws everywhere else. **All four strata are reported whatever they say. Quoting one
stratum without the other three is a void condition.**

---

## 4. POWER, AT BOTH VOCABULARIES, BEFORE ANY FLOOR IS WRITTEN

At the post-booking counter, options `N` = **310**, hurdle **3.3872**. The 50%-power multiplier is
**3.3872** and the 80%-power multiplier **4.2272**, larger by **1.2480×**.

**The quantity that must be resolved is a DECISION GAP against a card, not an effect against
zero:** `rf + 702` sits **+282 bps** above Robinhood Gold and **+552 bps** above IBKR Pro. With
**n = 408 names** as the independent unit, the tolerable cross-name SD at 80% power is
**282 / 4.2272 × √408 = 1,347 bps** for the Gold comparison and **2,637 bps** for IBKR Pro.
**Cross-name dispersion in implied financing spreads runs in the hundreds of bps, not thousands**,
so this design is expected to resolve both gaps comfortably. **The floor is therefore NOT the
binding constraint and is set on the instrument instead: `MIN_N` = 30 pairs per name and ≥ 100
names per stratum.** Below that a stratum is reported **UNDERPOWERED, never null.**

**THE VERDICT SHIPS WITH ITS REALISED MDE AT BOTH VOCABULARIES OR IT IS NOT REPORTED.**

---

## 5. VERDICT GRAMMAR

* **FLIPS-GOLD** — the executable all-in median at long tenor is **below `rf + 420`** with its
  interval excluding 420, and above `rf + 150`.
* **FLIPS-BOTH** — below `rf + 150` with the interval excluding it.
* **NO-FLIP** — the interval does not exclude 420 from below, i.e. the long-tenor route is not
  demonstrably cheaper than the cheaper of the two cards an operator would use.
* **UNDERPOWERED** — a stratum below the §4 floor; reported as such, never as a null.

**The card rates are ASSUMPTIONS — published retail figures, not anything measured here — and are
LABELLED as assumptions everywhere they appear**, exactly as `DEEPITM-FIN` labelled them.

---

## 6. VOID CONDITIONS

1. Reading any DTE band other than the four declared strata, or reporting fewer than all four.
2. Re-deriving `DEEPITM-FIN`'s 60–90 DTE number and presenting it as new (`MB4`'s explicit
   instruction).
3. Quoting a MID figure as the verdict; the verdict is EXECUTABLE.
4. Treating pairs as the independent unit in any interval.
5. Adjusting the delta band, `MIN_N`, or the commission to change a result.
6. Quoting any figure as evidence about RETURNS. `P1S0` closed the options-expression family on
   the return side and **this does not reopen it**; `R2` stands.
7. Reading a `close` rather than `raw_close` anywhere a strike is matched (`U1-SPLIT`).

---

## 7. THE BINDING LIMITATION, STATED BEFORE THE RUN

**Tier E reaches past 200 DTE for 2016–2018 ONLY, and that window is a near-zero-`rf` regime.**
Every figure here is measured in it. `DEEPITM-FIN` found the option route's own cost **stable
across all five rate eras (616–754 bps)** while the Gold spread swung 52–567, which is weak
evidence that the option leg travels — **but it is evidence from a DIFFERENT tenor, and whether
the long-tenor cost is era-stable is UNMEASURED and will remain so.** The verdict must carry this
sentence, and a successor wanting era-robustness needs a Tier E pull outside 2016–18, which is a
data purchase rather than an analysis.

---

## 8. PRIOR, STATED BEFORE THE RUN

**FLIPS-GOLD 45% · NO-FLIP 40% · FLIPS-BOTH 5% · UNDERPOWERED 10%.** The lean toward FLIPS-GOLD is
the §1 arithmetic; the substantial NO-FLIP weight is because **the roll leg is the half that
collapses and the financing leg is the half that may not** — a longer-dated deep-ITM call is a
larger, less liquid, wider-quoted contract, and the executable convention charges that width. **If
financing at long tenor is materially worse than 342, the collapse in roll frequency is bought
back by a wider spread on each roll, and the answer is NO-FLIP.**
