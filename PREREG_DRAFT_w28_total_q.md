# PREREG_DRAFT_w28_total_q.md — intangible-adjusted book value as a PAIRED REPLACEMENT
## Frontier Scout draft, 2026-08-28. **BLIND. Zero trials charged by this file. No outcome statistic computed.**
## For an executor to accept or reject. **Rejection costs nothing and is the system working.**

---

## §0 · PROVENANCE, AND THE PRIOR THIS REGISTER CARRIES

**Origin:** `WIDTH_AUDIT.md` Part 1 (W-28). **Not** a Don-supplied idea and **not** selected on any
outcome — the register is derived from `SEARCH_DOCTRINE` §1.2's finding that **re-measurement is
the one correction class never tried**, and from `MB18`'s published power arithmetic.

**The prior, stated hostile-first:**

* Corrections are **0-for-7 on the alpha gate** (`S1`, `S3`×3, `S16`, `S20`/`S21`, `S27`, `LOO`).
* **`P7` already repaired this exact column** (currency corruption, `book_to_price` 892 against a
  true 0.589 on 4.1% of rows) and the composite moved **+0.05pp** of top-decile alpha
  (+11.77% → +11.82%). **A repair to this column has already been measured as nearly invisible.**
* **`S1` measured a mechanism by which this register could make the composite WORSE** — see §4.

**Nothing in this draft claims the register is likely to clear.** It claims the register is
**cheap, killable, and informative when it fails**, and §4 is where that is argued.

---

## §1 · THE HYPOTHESIS, IN ONE SENTENCE

**`book_to_price` measures a construct the composite already bets on, using a denominator that
GAAP systematically understates for intangible-heavy firms; replacing it with an
intangible-adjusted book value de-attenuates the SAME bet and improves the composite.**

**Explicitly NOT claimed:** that the corrected column carries orthogonal information. **This
register claims NON-orthogonality and is gated on it** (`K3`). `MB12`'s five-body pattern is the
reason the register is shaped this way, not an objection to it.

---

## §2 · THE ARM

**Primary arm — ONE input changes, nothing else.**

| | |
|---|---|
| incumbent | the shipped composite: 7 weighted themes, **24 distinct z-columns**, shipped weight vector |
| arm | **identical**, except `book_to_price` → `book_to_price_adj` |
| `book_to_price_adj` | `(ceq + K_int − intan) / market_cap`, PIT, same price leg as the incumbent |
| `K_int` | Peters–Taylor intangible capital = knowledge capital (perpetual inventory on `xrd`) + organization capital (perpetual inventory on a fixed share of `xsga`) |
| standardiser | **shipped `zscore`, unchanged, at both layers** — `K5` |
| universe, dates, weights, rebalance rule | **unchanged** |

**Declared SUCCESSOR — ONE, named here, NOT run here, 1 trial if ever run:**
**`W-28c`** extends the correction to `quality`'s `gp_on_capital`, which divides gross profit by
`total_equity` — a capital denominator Total Q moves directly. It runs **only if the primary
clears**; running both at once would produce a number nobody could attribute (`LOO`: NULL, 4 of 7
arms flipping sign across halves).

> **A second successor was drafted and is WITHDRAWN before reaching an executor.** `W-28b` would
> have corrected `capital_discipline`'s **asset-growth** input on the argument that a firm expensing
> R&D shows no asset growth and so scores as *disciplined*. **The shipped composite has no such
> input.** `valuation/screener/factors.py`: *"Capital discipline is now share issuance **ALONE**.
> `neg_asset_growth` was **DROPPED** … median IC −0.0141 with t −0.70 — the wrong sign."* **The
> record had already found that channel wrong-signed and removed it.** Recorded here rather than
> silently deleted, because it is the same failure as `F-13` and `F-2`: **a premise asserted from
> prose without reading the shipped path.**

**Parameters frozen at declaration, before any data is pulled:**

| parameter | value | why it must be frozen |
|---|---|---|
| R&D depreciation δ_R&D | **industry-varying, from the published BEA schedule, named table in the declaration** | a tuned δ is a free parameter and makes the verdict **VOID** (`MA55`'s rule) |
| SG&A share treated as investment | **30%**, the published convention | same |
| organization-capital depreciation δ_org | **20%**, the published convention | same |
| burn-in | **≥ 10 fiscal years** of prior `xrd`/`xsga` before a name-date is eligible | a perpetual inventory that has not converged is a different variable |
| `xrd` null handling | **null ≠ zero.** Nulls are declared, counted, and handled by ONE stated rule | treating null as zero is a silent imputation that flows straight into the arm |
| already-capitalized intangibles | **`intan` subtracted** to avoid double-counting acquired intangibles | otherwise acquisitive firms are counted twice |

> **No parameter above may be chosen to make the arm look better, and none may be revisited after
> any result is seen. If the census makes a value unavailable, the register WITHDRAWS rather than
> substituting.**

---

## §3 · THE VERDICT OBJECT — and the one it may NOT use

**PRIMARY (the gate):** the **composite's** top-decile alpha and long-short t, scored as a
**paired difference series across the 69 rebalance dates**, against the calibrated floors the
shipped gate already uses (`X7`-calibrated; the composite's own long-short reference is **2.6199**
against a calibrated floor of **2.2837**).

**SECONDARY, reported and non-decisive:** monotonicity, PBO, turnover, per-date IC of both
columns, and the sector-loading comparison of §5's prediction 1.

**FORBIDDEN as a gate — and this is a standing finding, not a preference:** the **value theme's
own IC**. `WIDTH_AUDIT` §0.3: the record quotes it at **0.84** (`S1` incumbent), **1.57** (`S1`
arm), **+1.34** (`P7` pre-fix) and **+1.46** (`P7` post-fix) — a spread of **0.73** across four
readings. And `S1`'s own closing line is the **`P6` rule, third instance**: *a theme's IC and the
composite it feeds move opposite ways.* **A register gating on a theme IC is measuring the wrong
object by the record's own finding.**

---

## §4 · THE GRAVEYARD, AND THE ROW THAT COULD KILL THIS

### `S1` — argued past, or not at all

> *"Dropping `book_to_price` RAISES the value theme IC t **0.84 → 1.57** and makes the composite
> WORSE in both directions (**−0.207 / −0.079 t**)."*

**`book_to_price` hurts its own theme's IC and helps the composite.** The mechanism that fits is
**decorrelation**: a noisy column with a low individual IC can still improve the theme by being less
correlated with its theme-mates (**four inputs for established names, three for the rest** — the
value theme is bucket-split, and `book_to_price` is the **only input present in BOTH buckets**).

**If that is the mechanism, this register's correction makes the composite WORSE**, because
de-attenuating the column makes it **more** like its theme-mates. **That is a directional
prediction of harm, pre-committed here, and it is `K4`.**

**Why `S1` nevertheless does not close the register:** `S1` tested **removal** and **substitution
by another owned ratio**. It did not test **re-measurement of the same construct**. Removal and
correction have **opposite** predicted effects on the column's correlation with its theme-mates.
`S1` is evidence about the column's *presence*, not about its *accuracy*.

### `S20` / `S21` — a corrected INPUT is not a corrected TRANSFORM
`S20` **REJECTED**: a rank transform at both standardisation layers costs **3.49pp/yr** of
top-decile alpha (**+7.17% → +3.68%**) and drops below both calibrated HAC floors *while improving
monotonicity* (−0.8909 → −0.9515). `S21` **NOT REPLICATED**, premise false (`zscore` already
winsorises at 2%). **Both changed the TRANSFORM applied to all 24 z-columns at once. This register
changes ONE raw input's construction and leaves the transform and the other 23 columns untouched**
— and `K5` binds it to the shipped `zscore` precisely so that it cannot become `S20`'s arm in
disguise.

### `S16` — the limiting case, and why it is cited *for* the design
`S16`'s two-input proposal was **RANK-IDENTICAL to the incumbent by arithmetic** and could not
move an ordering at all. **`K2` is the direct descendant of that finding**: a correction that
changes a number but not a decile cannot change a portfolio, so the register measures **bite**
before it measures return.

### `P7` — the precedent, and the caution, in one row
The one time this project corrected this column's **measurement**, every diagnostic improved
(**PBO 13.3% → 6.7%**, monotonicity −0.939 → −0.952, all six value inputs up) — **and the
composite moved +0.05pp.** **This register does not inherit `P7`'s "ships on correctness"
standing**: 892-versus-0.589 was a wrong number; GAAP's treatment of R&D is an accounting
standard. **This is a hypothesis and is priced as one.**

### `MB12` — cited *for* the register, and made a gate
Orthogonality has failed as a motivation **four items deep in the R² 0.027–0.145 band, with a fifth at 0.2926 / 0.2936** — none clearing.
**This register claims the opposite and `K3` holds it to it.**

---

## §5 · THREE FALSIFIABLE PREDICTIONS, WRITTEN BEFORE ANY MEASUREMENT

1. **Sector loading falls.** The corrected column shows **less** sector-explained variance than
   the incumbent. *(Measurable without touching returns.)*
2. **The IC moves away from zero in its existing direction.** De-attenuation does not flip signs.
3. **ρ between the two columns' per-date IC series is high (≥ 0.60, expected ≥ 0.95).** A low ρ
   falsifies the premise — see `K3`.

---

## §6 · THE KILLS — four of five FREE, all firing before a return is scored

| kill | fires when | cost | consequence |
|---|---|---|---|
| **K1 · CROSSWALK** | Sharadar → `gvkey` name-date coverage < **90%** on any rebalance date, or the `firstpricedate`-anchored audit finds an unresolvable share-class collision | **FREE** | STOP. W-20 re-priced. **The check may NOT be "does this ticker map to two permatickers?"** — `ticker_identity.py` records that this **fails silently on this data** |
| **K2 · BITE** | the adjustment moves the name's value-theme **decile** on **< 20%** of covered name-dates | **FREE** | STOP — the arm's real n is a fraction of the panel and §7's MDE does not apply. **Most likely to fire** |
| **K3 · PREMISE** | ρ(per-date IC series) **< 0.60** | **FREE** | **WITHDRAW.** This is an addition wearing a repair's name; `MB12`'s wall applies and the register does not re-frame itself |
| **K4 · DIRECTION** | the corrected column's IC **flips sign** | **FREE** | STOP, and **report the `S1` decorrelation reading as the finding** |
| **K5 · STANDARDISER** | any standardisation path other than shipped `zscore` at both layers | **FREE** | declaration check; `S20` applies otherwise |

**And one deviation rule:** if the census cannot supply a frozen parameter from §2, the register
**withdraws**. It does not substitute, and it does not proceed with a looser version.

---

## §7 · POWER — MB22, at both vocabularies

**Scale, with a correction to `SEARCH_DOCTRINE` §1.2 that this draft owes.** `MB18` published
**0.4274 SD** (basis six) and **0.5071 SD** (basis seven) as 80%-power detection thresholds
**at `crit` 2.71 — `MB18`'s own critical value, not the HLZ hurdle.** Inverting `MB22`'s gate
`MDE_80% = (crit + 0.84) × se` at that crit gives **se = 0.120394 SD** (basis six) and
**0.142845 SD** (basis seven). *The doctrine inverted at the hurdle and understated `se`; its
paired GAIN ratios are unaffected (they cancel `se`), its absolute MDEs were too small.*

**Counter base:** the ledger's last append reads **equity 242, hurdle 3.313287710464241**. This
register books **N 242 → 243**, `crit = 3.314532`. *(If the executing lane's re-read returns 245,
substitute `crit = 3.317004`; every MDE below moves in the fourth decimal.)*

**Unpaired — what an ADDITION would face:**

| basis | **50% power** (`crit × se`) | **80% power** (`(crit + 0.84) × se`) |
|---|---|---|
| **six** | **0.3991 SD** | **0.5002 SD** |
| seven | 0.4735 SD | 0.5935 SD |

*Context: the largest raw anchor this panel has ever carried is `z_fcf_margin` at **0.4346 SD**.
The unpaired 80%-power MDE is **115% of it** — the cross-section cannot reliably detect even the
best signal it already contains.*

**Paired — what THIS register faces.** `SE_paired = se·√(2(1−ρ))`, basis six:

| ρ | SE_paired | **MDE @ 50%** | **MDE @ 80%** | gain |
|---|---|---|---|---|
| 0.80 | 0.076144 | 0.2524 | 0.3163 | 1.58× |
| 0.90 | 0.053842 | 0.1785 | 0.2237 | 2.24× |
| **0.95 (expected)** | 0.038072 | **0.1262** | **0.1582** | **3.16×** |
| 0.98 | 0.024079 | 0.0798 | 0.1000 | 5.00× |

**`required_n = ((crit + z_power)/effect)²`** is stated in the declaration for the realised ρ,
**before the arm**, per `RUN_RULES` A-11.

**Why dilution does not cost power here — the argument that justifies the design.** For a composite
linear in its z-columns with `book_to_price` at weight `w`
(**1/28** for established names, **1/21** for the rest):
`composite_new − composite_old = w·(z_adj − z_incumbent)`. **The numerator and the standard error of
the paired difference both scale by `w`, so `w` cancels in the t.** The usual objection —
*"one input of four in one theme of seven is 1/28 of the composite, you will never see it"* — is
true of an **unpaired** comparison and **false** of the paired difference.

**And the honest counterweight, stated with equal weight:** high ρ means small SE **and** small
effect. **The paired advantage is real only if the effect shrinks more slowly than the SE**, which
depends entirely on the **bite** subpopulation. **`K2` measures that before the arm**, and this
MDE table is restated on the bite population in the declaration. *(`O-1`'s lesson: 5.89% actual
against ~75% assumed, ~17×.)*

## §8 · DATA, COVERAGE, SPAN

**Tables to probe, in order:** `totalq.total_q` (may not be entitled — the 2026-08-25 account
probe lists only `contrib_global_factor` and `contrib_char_returns`); **fallback**
`comp.funda` (`xrd`, `xsga`, `ppegt`, `ppent`, `at`, `ceq`, `intan`, `gdwl`, `che`, `dltt`, `dlc`,
`pstkrv`/`pstkl`/`pstk`, `datadate`, `fyear`, with `indfmt`/`datafmt`/`popsrc`/`consol` filters);
`comp.company`/`comp.security`; `crsp.stocknames` (`ncusip`, `namedt`, `nameendt`);
`crsp.ccmxpf_lnkhist` (`linktype`, `linkprim`, `linkdt`, `linkenddt`).

**The register is NOT gated on an unopened product.** `comp` is confirmed entitled by a successful
`SELECT`, so the fallback path is always available.

**Coverage, all three measured on the arm's own population and stated BEFORE the arm:**
(1) crosswalk coverage per rebalance date; (2) field coverage with burn-in satisfied;
(3) **bite** coverage — the fraction where the decile moves.

**Span.** Panel: **2,531 names, 69 quarterly rebalances, 2009–2026**. The account probe measured
CRSP's permno span ending **2024-12-31**, and Compustat annual lags fiscal year-end. **Expect to
lose roughly 5–8 of the 69 dates at the recent end.** The **exact usable date list is stated in
the declaration**, before the arm, because a shortened panel changes `se` and therefore every MDE
above. *(`F-13`'s lesson: name the field AND its direction in time.)*

**Licensing fence:** WRDS is **research-only, never public**; raw rows never leave `D:\wrds`.
Published artifacts carry derived columns only.

---

## §9 · TRIAL ACCOUNTING

**Zero trials charged by this draft.** **1 equity trial** if the composite gate is read.

On the **ledger-confirmed** base: N **242 → 243**, hurdle **3.313288 → 3.314532** (**Δ +0.001244**).
*(`SEARCH_DOCTRINE` shipped with 245 — see `WIDTH_AUDIT` §0.4. **The Δ is identical on either
base**; only the absolute hurdle moves, and the executing lane re-reads the counter before booking.)*

**`MB31`'s seed-1003 floor flip sits at N = 247** — five trials away on the ledger base, two on the
doctrine's. **This register does not reach it on either.**

Successor `W-28c`: **1 trial, not charged unless run.**
**All five kills fire before the composite gate is read, so the register can die for zero trials.**

## §10 · WHAT A NULL WOULD MEAN

**A null on the composite gate, with `K3` and `K4` not firing, means:** better measurement of this
construct does not help this composite — which, combined with `P7`'s **+0.05pp**, would make the
value theme's book-denominated input **a settled question** and close the re-measurement thread on
`book_to_price` permanently.

**`K4` firing means something larger, and it is why this register is worth a trial at a low
prior:** it would establish that **`book_to_price` is carried for decorrelation rather than
accuracy** — a claim no register has tested, which bears directly on `S24` (rank correlation
0.9907), on `LOO` (null, 4 of 7 arms flipping sign), and on the combination axis
`SEARCH_DOCTRINE` §1.6 left half-closed.

> **This register's most likely failure mode teaches more than its success would.** That, and not
> its prior of clearing, is the case for running it first.
