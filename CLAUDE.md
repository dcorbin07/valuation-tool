# CLAUDE.md — Valquo project brief (read every session)

> **FIRST: read `RUN_RULES.md` (repo root) before starting any work. It is short and
> non-negotiable — it governs pushing, handoffs, bug reporting, pre-committed thresholds, and
> never silencing a check. Every agent, every run, no exceptions.**

You are picking up **Valquo** (valquo.co), a Python/Flask stock-analysis SaaS owned by Don
(donniecorbin6@gmail.com). Be honest, concise, and never oversell. Architecture is under
**"Core file"** below (CORRECTED 2026-08-07, claims audit: this used to say "section 4 below" —
there are no numbered sections in this file and never have been, so the pointer led nowhere);
the optimization/data research roadmap is in `OPTIMIZATION_RESEARCH.md` — read it once for detail.

## What it is
Hot-stocks screener (9-theme "hot score") + options/intraday signals + a point-in-time fundamental
**backtest / Edge Lab** that proves-or-disproves the edge and tunes the screener weights. A monthly,
purely-statistical, out-of-sample-gated self-learning loop re-tunes weights.

## How to run (you can run these directly — Don cannot / will not)
- Full backtest: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --json data/backtest/last_result.json` (or `run_backtest.bat`). Reads licensed Sharadar exports in `data/backtest`. Takes 20-40 min.
- 13F due-diligence: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --validate-institutional` (or `validate_13f.bat`).
- Tests (keep green, **currently 249/249**): `python tests/test_edge.py`. **CORRECTED 2026-08-07
  (claims audit): this line read "currently 16/16" — measured today it is 249/249, exit 0.** It is
  also not the whole gate: `tests/` holds **62** suites and the auto-land Action runs EVERY one of
  them (audit C7), so verify with a loop over `tests/test_*.py` before pushing, not with
  `test_edge.py` alone. **CORRECTED 2026-08-12 (session 29): this read "24" — measured today it is
  62, all passing. Judge them by EXIT CODE, not by grepping for `OK`:** the suites print at least
  three different summary formats (`OK`, `20 passed, 0 failed`, `14/14 bulk tests passed`), and a
  loop that scrapes for `OK` reports `test_build_ledger`, `test_bulk` and `test_calibration` as
  FAILING when they pass. A gate that cries wolf is one you learn to ignore.
- Deploy: Don runs `git_push.bat` himself (pushes to GitHub -> Render; Actions run the scans).

## HARD RULES (do not violate)
- **Never commit/push `data/`** (licensed Sharadar exports; gitignored) or `*.db`.
- **`.env` holds real secrets** (SHARADAR_API_KEY, ANTHROPIC_API_KEY, TRADIER_TOKEN, SECRET_KEY) — never print, commit, or overwrite.
- **Do NOT execute trades or move money** — a Robinhood connector exists (Cowork side); produce target/rebalance lists, Don executes.
- **Ignore Don's resume files entirely.**
- Repo is private; keep it clean. Keep `tests/test_edge.py` passing after every change.

## Core file: `valuation/edge/fundamental_panel.py` (the backtest engine)
- `build_fundamental_panel()` — builds the 9 themes point-in-time (reuses the live `build_frame`). `_yoy()` computes revenue/asset-growth/issuance -> `growth` + `capital_discipline`. `inst_lag_days` param stress-tests the 13F lag.
- 8 weight schemes (`_weight_schemes`), incl. `max-ir-decorr` (Sigma^-1*mu).
- Selection/validation: `walk_forward` (single-path, params) and **`cpcv_validate`** (Combinatorial Purged CV — the AUTHORITY for weights; reports PBO + Deflated Sharpe). If CPCV runs and rejects, keep defaults — do NOT fall back to walk-forward.
- `quantile_backtest` (decile / long-short), `regime_split` (edge by market-cap tier), `institutional_dependence`, `validate_institutional`.

## CURRENT STATE — the honest findings (do not oversell)
Rewritten 2026-07-30 after P5. Everything below is measured on the **full 2,710-name × 110-date
universe** (~18y, gross of costs). Several long-standing claims here were WRONG, not merely
stale — they are corrected in place and the corrections are called out, because this file is
the project's memory and the old versions had been repeated for months.

- **THE HEADLINE SURVIVES A SPLIT BY NAME - AN INDEPENDENCE AXIS IT HAD NEVER BEEN TESTED ON -
  AND IN THE SAME SESSION IT IS FOUND NOT TO CLEAR THE HARVEY-LIU-ZHU HURDLE (2026-08-13,
  `X1`+`R4`).** `PREREG_r4_x1_accounting_and_universe_split.md` committed **ALONE at `9aee4f7`**, a
  strict ancestor of every measurement commit. **No score moved and this is NOT a vintage event** -
  C1 gated the full-universe headline bit-identical before any split was read.
  * **X1 IS THE STRONGEST POSITIVE RESULT THIS PROGRAMME HAS PRODUCED, AND THE AUDIT SAID IT WOULD
    BE THE MOST VALUABLE TEST IN THE DOCUMENT.** Every held-out gate this project has ever run
    splits by **DATES**, which conflates *"does the signal generalise"* with *"does the PERIOD
    generalise"*. A **universe** split has **no regime confound at all**. Splitting the 2,531 names
    into disjoint halves - the audit's own stable key, `sha1(ticker) % 2`, **1266/1265**, no seed,
    reproducible by anyone holding the ticker list - plus **100 seeded random splits**, against a
    null **rebuilt for half books**:
  * **A1 (top-decile alpha) SURVIVES, and emphatically. 200 of 200 half-books clear their own bar;
    100 of 100 splits clear on BOTH sides; the median half-book is +0.07233 against the full
    universe's +0.07174; and ZERO of 400 half-book measurements came back negative.** The minimum
    across 200 half-books is **+0.04382**, nearly three times the null's p95 of +0.01724. **Halving
    the universe widened the error bars and did not move the centre** - which is what a broad,
    uniform cross-sectional effect looks like.
  * **A2 (long-short HAC *t*) SURVIVES BUT DISTINCTLY MORE MARGINALLY, and the pre-registered bars
    are what separate them:** 93.0% of half-books and 86.0% of splits, against A1's 100%/100%. Its
    median half-book *t* **+2.3617** sits BELOW the full-universe **+2.6199**, as a half-sized book
    sorting a noisier spread should, and **14 of 200 half-books fail their own bar. A1 is the
    stronger claim and should be quoted as the stronger one.**
  * **A SCOPE LIMIT FIXED BEFORE THE RUN, AND SAYING IT IS NOT A DODGE.** The audit asks to
    *"decide on half A, measure on half B"*; **that half cannot bind, because the deployed strategy
    fits NOTHING** - flat 1/7, never tuned, `cpcv.adopt` false on every run - **so there is no
    decision to leak** and X1 as run tests **generalisation across NAMES**, not decision leakage.
    **Re-running every theme decision and the weight selection under the split is NOT done** and is
    named so it is not mistaken for done.
  * **A CROSS-CHECK THAT CORROBORATES AN INDEPENDENT MEASUREMENT.** The half-universe null reads
    **ls_hac p95 1.7405**; S22 separately measured the **FULL**-universe fixed-weights null at
    **1.7494**. **Halving the universe moved the null by 0.009 of a *t*** - so the gap to X7's
    **2.2837** is almost entirely the **CPCV selection step**, which S22 already priced at
    **+0.5343**. Both are fixed-weights nulls and X1's arms use fixed weights, so it is the right
    null; two independent routes to the same number is the best evidence available that it is
    calibrated rather than merely computed.
  * **R4 CLOSES `DONE`, AND THE BULLET NOBODY HAD DELIVERED IS THE ONE THAT FAILS.** Of its four
    method bullets M1 shipped two (the log - 121 rows, **521 trials** - and the real `N` into the
    Deflated Sharpe); this session shipped the other two.
  * **BULLET 3: BH ACROSS THE EQUITY FAMILY LEAVES THREE OF FIFTY-THREE - AND THE SET CHANGES WITH
    THE INFERENCE CHOICE.** `fcf_margin` and `gp_on_capital` survive under both; **`fcf_yield` only
    under the plain *t* and `roic` only under the clustered one**, so *"three survive FDR"* is
    weaker than it sounds. **Rejected by BH:** `roic` +2.8172, `neg_issuance` +2.7556, `roe`
    +2.7303, `pead_car` +2.4572 - several of which the record has quoted as individually
    significant against the retired 2.0 convention. **The audit's analogue is the options autopsy's
    126 FEATURES, not log rows** - which matters, because `RESEARCH_LOG.md` has **no p-value
    column**, so BH across the log is **not computable and never was.**
  * **BULLET 4 IS THE FINDING, AND IT REFUTES R4'S OWN PREDICTION. THE HEADLINE DOES NOT CLEAR THE
    HLZ HURDLE:** long-short HAC ***t* 2.6199121240414884** against **√(2·ln 218) =
    3.2816139513322065**, a shortfall of **0.6617** — **and the SHIPPED artifact reads 3.2844 at
    N = 220, because this session's own two X1 trials landed between the register and the refresh.
    Both are right at their own denominator, the verdict is unchanged either way, and the hurdle
    only ever RISES as trials accumulate.** R4 predicted it *"probably clears"*; that 3.52
    was the **pre-B6 void panel**, and `N` went **8 → 218** meanwhile, so **the statistic FELL as
    the hurdle ROSE**. **The haircut was already computed on every run and used by the CPCV adopt
    gate - nothing had ever compared it to the HEADLINE**, and no `harvey`/`hlz`/`hurdle` string
    existed anywhere in the canonical file.
  * **BOTH SIDES SHIP, BECAUSE THE ANSWER IS A TENSION AND NEITHER NUMBER IS "THE" ANSWER.** The
    project **CLEARS** X7's empirically calibrated **2.2837** and **FAILS** the bar derived from
    counting its own trials. The counter-argument was **registered before the run**: **HLZ prices
    the BEST OF N draws, and the deployed composite is not the best of anything** - flat 1/7, never
    tuned, `cpcv.adopt` false - **so the 218 logged trials are overwhelmingly REJECTED ALTERNATIVES
    to it rather than candidates it beat.**
  * **IT SHIPS IN THE CANONICAL RESULTS FILE, NOT A SIDE ARTIFACT** - `multiple_testing`,
    **registered with M6's field-level guard**, no renames and nothing allow-listed, because a
    number that lives only in a study JSON is **exactly the failure R4 exists to end**.
    `statistics.benjamini_hochberg` is the shared definition; **BH already existed THREE times in
    the options lane and consolidating those is theirs to do.**
  * **A DEFECT IN MY OWN WORK, CAUGHT BY THE DOCSTRING I HAD JUST WRITTEN.** The first cut of the
    script carried **its own BH** - a **FOURTH** copy, which is the audit-B7 defect the shared
    definition exists to end, committed in the same change that argued against it. It now
    delegates, and a test pins the identity.
  * **R4's PERMANENT RESIDUAL:** BH across the **LOG** is not computable without inventing
    p-values; and **`research_log.DOMAINS` declares `unified` and it reads ZERO** - every U-series
    item testing explicitly unified equity+options hypotheses was charged to equity or options, so
    there are **three parallel single-lane families and one dead bucket**. **Measured and ROUTED**,
    since deciding it would move every published `N`. **R5's ledger row already leaned on R4's note
    as routing input.**
  * **A CORRECTION TO MY OWN REGISTER:** it said a half universe gives *"~126-name deciles against
    ~253"*; measured, it is **82.3 against 165.1** - I divided the 2,531-name universe by ten where
    the panel carries **~1,650 names per DATE** after coverage. Direction unaffected.
  * **Equity `N` 218 → 220, infra 11 → 12.** Expectations **5 right, 1 wrong, 1 split, 1
    unscorable** - the miss being that I expected at least one of 400 half-books to come back
    negative and **none did**. `data/free_analysis/R4_X1_ACCOUNTING_UNIVERSE.json`;
    `HANDOFF_edge_audit.md` R4+X1.
- **SELLING A 25-DELTA PUT IS SELLING A 25% ASSIGNMENT PROBABILITY *BY CONSTRUCTION*, SO THE
  STRIKE HAS ALREADY SPENT THE RISK EDGE — THE CSP ON HEALTHY DIPS IS REJECTED BY THE ONE CONTROL
  THAT MATTERED, AND THE `U6` "100% CALLS" BLOCKER IS RETRACTED (2026-08-13, `V6-OPT`).**
  `PREREG_v6opt_csp.md` committed **ALONE at `88685c9`** — one `.md`, zero `.py`, a strict
  ancestor of every measurement commit — and it fixed **BOTH stages** before either ran, so
  stage 2 could not be designed on stage 1's numbers. **ADOPTS NOTHING**; no live code path
  changed.
  * **STAGE 1 IS DESCRIPTIVE AND THE GATE OPENED, WHICH IS WHY STAGE 2 IS INTERPRETABLE.** On
    4,855 covered dipped rows: post-dip `atm_iv_30` sits **+17.71%** above the name's **own**
    trailing 252-day median against **+13.29%** for unhealthy dips (**ratio 1.3328**, so the
    market does **NOT** price the `M1` distinction); a real 25-delta 30–45 DTE put pays a median
    **2.550% of strike** over 32 days — **27.73% annualised** — net of the **shipped** fill
    engine at the touch; and the variance risk premium is **+0.0391** vol points (implied 0.430
    against realised 0.389). **The elevation decays away almost entirely inside 30 trading days**
    (−1.72%, −5.64%, −14.42%, **−16.56%** at t+5/10/20/30).
  * **STAGE 2 IS REJECTED, AND IT FAILS *ONLY* ON THE DISCRIMINATOR THE REGISTER NAMED AS
    DECIDING.** The healthy arm clears three of four conditions and is not marginal about it:
    **+1.1342%/trade** on the cash secured, **positive in BOTH halves** (+1.1348, +1.1178), an
    **84.39% win rate**, and it **beats random entry decisively** — pooled **+0.2612%** over five
    seeds, paired name-year sign test **z +7.2506, p 4.15e-13**, 66.96% of 457 cells positive.
    **It fails condition 2: the IDENTICAL trade on UNHEALTHY dips earns MORE (+1.2651%) and beats
    it in BOTH halves.** So the health floors do no work and the trade is **just short vol** —
    which `A3` already rejected at **−7.99%/trade**.
  * **THE MECHANISM IS MEASURED AND IT IS THE MOST PORTABLE THING HERE.** Assignment comes back
    **25.30% healthy against 25.73% unhealthy** — a 0.43pp gap — while the unhealthy name pays
    **2.978% of strike against 2.550%** because its implied vol is higher (0.474 vs 0.424).
    **A delta-targeted rule sets the strike from the name's own volatility, so it neutralises the
    very risk difference the trade was built to exploit.** Deltas are like-for-like (median
    **−0.2638** vs **−0.2658**, DTE 32 vs 31), so this is not a confound. **A risk signal can only
    pay through an option if the MONEYNESS is held fixed, not the DELTA** — and that is a **NEW
    hypothesis** needing its own register, forbidden here by void condition 3.
  * **THE RISK EDGE IS A QUARTER OF ITS HEADLINE WHERE IT CAN ACTUALLY BE TRADED, AND THE REGISTER
    PREDICTED THIS AT 80/20 BEFORE MEASURING IT.** `C5` re-measured `M1` on the covered rows at
    **−2.797pp** (healthy 29.26% vs unhealthy 32.06%) against `V6-B`'s full-panel **−10.84pp** —
    *below* even its megacap quintile's −3.787pp — because options exist on the large end and
    `V6-B` measured the separation **weakest exactly there**. Covered dips carry a median market
    cap of **$17.92bn against $2.17bn**, an **8.26× tilt**. **Any future options result on this
    population must be quoted against −2.797pp, never against −10.84pp.**
  * **A PREMISE FINDING THAT CORRECTS MY OWN PRIOR SESSION — see the `U6` bullet below.** The
    chain cache is **not** 100% calls: **1,288,750 puts against 1,288,751 calls**, zero tickers
    with no puts. The 3,870-of-3,870 measurement was of the **TRADED BOOK** and the inference from
    it was wrong. U6's **coverage** blocker stands and still carries its verdict alone.
  * **THE SETTLEMENT TRAP, CAUGHT BEFORE THE RUN RATHER THAN AFTER.** Strikes are **as-traded**
    while `data/backtest/prices` is split- **and** dividend-adjusted: AAPL's derived `spot` reads
    **300.35 against an adjusted 72.34** on 2020-01-02, and the two differ by >5% on **46.66%** of
    its days. Settling a $300 strike against $72 books a fake ~76% assignment loss **silently**.
    Session 30's rule is applied in **both** directions — the option settles on the as-traded
    `spot`, and only the **STOCK** control uses the adjusted close.
  * **COVERAGE FORBIDS A FULL-PANEL GATE FOR THE FOURTH TIME** (`S18`, `U2`, `U3`, now this):
    **4,855 of 37,982 dipped rows = 12.78%**, over **40 of 69** dates, **28 of the 29 gaps EARLY**,
    halves **20 and 19** after embargoing 2021-01-21.
  * **CONTROLS: C1 reproduces the premise counts and ABORTS otherwise; C2 ZERO point-in-time
    violations over 4,836 events; C3 `skew_25d` equals `iv_put_25d − iv_call_25d` at max abs diff
    0.000e+00 over 902,851 rows — reproducing `U2` on four times the rows, so it is ONE column and
    never two pieces of evidence; C-QUOTE the derived `mid`/`spread_frac` reconstruct the RAW
    chain's own bid to 3.815e-06 over 216,872 rows; C-D the mirror loses 1.5263%, so both sides
    are not profitable.**
  * **TWO DEFECTS IN MY OWN INSTRUMENT, both caught before the verdict and both PROVED inert by
    leaf diff rather than asserted** — the halves split each arm at its own median date instead of
    the register's single embargoed boundary (289 shared leaves, **ZERO moved**, 5 documentation
    leaves added), and stage 1 banked a contract without its `expiration` (re-run: 668 leaves,
    **ZERO moved**). **REPORTED AGAINST THE ARM:** the survivability leg compounds per-trade
    returns **sequentially** rather than simulating a capital-weighted book, so it **overstates**
    drawdown — it passes anyway, so it cannot have produced the verdict — and the absolute levels
    are severe (**−55.52%** for the arm against **−82.56%** for the stock control at cap 10).
  * **NOBODY MAY READ THIS AS EVIDENCE THAT CASH-SECURED PUTS DO NOT WORK.** The register declared
    the asymmetry in advance because the covered sample holds **one** crash, so a decisive REJECT
    was available and a decisive ADOPT was not. **Options `N` 287 → 292; equity untouched BY THIS ITEM (218 after the merge);
    72 suites, 0 failures.** Expectations **4 right, 3 wrong**.
    `data/free_analysis/V6OPT_STAGE1.json`, `V6OPT_STAGE2.json`; `HANDOFF_optionsbot.md` §57.
- **THE 800-NAME-ERA REJECTIONS ARE RE-RUN AT LAST: SIX NULLS - AND A LIVE "ALL WRONG-SIGNED"
  CLAIM IS REFUTED, EVERY SIGN HAVING FLIPPED POSITIVE ON THE CORRECTED UNIVERSE (2026-08-13,
  `R5`+`R6`).** `PREREG_r5_r6_alphabetical_rerun.md` committed **ALONE at `4b9706b`**, a strict
  ancestor of every measurement commit. **SCORES NOTHING and is NOT a vintage event** - C1 gates on
  the composite returning BIT-IDENTICAL and it did.
  * **ALL SIX NULL, AND NOT ONE CLEARS EVEN THE RETIRED 2.0 CONVENTION IN ANY WINDOW.** R5:
    `neg_ret_1m` median IC **+0.00715** (*t* +0.4546), `neg_max_ret` **+0.02634** (+1.1510),
    `neg_idio_vol` **+0.05452** (+1.2105). R6 on 50 covered dates: `sm_conviction` **+0.01597**
    (+1.2786), `sm_holders` **+0.03285** (**+1.6111**), `sm_avg_position` **+0.03240** (+1.3296).
    Bars are each signal's **own** within-date permutation p95 in both halves. **Coverage is
    comfortable everywhere** (R5 99.5-100%, R6 73.8%, floor 30%), so **no arm is a power failure.**
  * **THE HEADLINE IS NOT THE VERDICT: THE LIVE "ALL WRONG-SIGNED" CLAIM IS REFUTED.**
    `settings.py:222-224` and `factors.py:294-296` both recorded the three anomalies at median IC
    **-0.014 / -0.072 / -0.025**, measured on **400 names over 110 rebalances** - **VOID TWICE**,
    under **B12** (alphabetical slice) and under **B6** (the inverted-universe panel). On the
    corrected 2,531-name / 69-date panel **ALL THREE SIGNS ARE POSITIVE**. They remain rejected
    **for being WEAK, not for being BACKWARDS** - and a live comment had been asserting the
    opposite as current evidence. `neg_idio_vol` is the largest at +0.05452 and **+0.09658 on the
    late half** - a big IC by this panel's standards - carried on a *t* of only 1.21 because the
    early half is +0.1726. **Large and unstable, not strong.**
  * **R6's MECHANISM IS A MARKET-CAP SORT, AND IT IS THE REASON RATHER THAN A CAVEAT.** C6 puts the
    three conviction signals at **-0.815, -0.855 and -0.854** against the `size` theme and at
    **+0.777 to +0.833** against each other - so they are close to **ONE** signal and that signal is
    largely market capitalisation, which the panel already scores. **`sm_holders` is the near miss**:
    it clears its own p95 on the full sample (**+1.6111 vs 1.5285**, the only cell in the register to
    clear anything) and then reads **+0.0118** on the early half. **THE SF3 CONVICTION FAMILY IS NOW
    CLOSED** - five of five members measured on the corrected universe with none clearing.
  * **SIX ARMS ARE NOT SIX INDEPENDENT TESTS, AND THE CAVEAT MUST TRAVEL WITH THE COUNT.** By C6's
    own correlations the effective number is **nearer three** - R6's three inter-correlate 0.78-0.83
    and R5's two volatility cousins 0.698. **The SELRULE lesson.** The charge of six is paid in full
    anyway, because understating `N` overstates significance.
  * **THE LIVE `sm_breadth` SWAP SURVIVES ITS OWN VOIDED JUSTIFICATION - and this was the most
    consequential question in the register.** `factors.py:314-316` replaced `inst_breadth` with
    `sm_breadth` in the **LIVE** institutional theme mean on the strength of *"IC t +2.37 vs +1.48
    on 800 large caps"*, a comparison B12 voided: **a live scoring decision resting on a voided
    number.** Re-measured head to head at near-identical coverage (0.7169 vs 0.7185):
    **`sm_breadth` +1.8481 against `inst_breadth` +1.2371 - THE ORDERING HOLDS**, though the gap
    narrowed from 0.89 to **0.61** of a *t* and **neither clears 2.0**. **AND A REFINEMENT OF THE
    LEDGER'S OWN CLAIM: the +1.73 it cites for `sm_breadth` was dated 2026-08-01, THREE DAYS BEFORE
    the B6/B7/B13 corrections landed**, so it was never a corrected-panel figure either and
    **+1.8481 is the first.**
  * **BOTH INPUTS THE LIVE `low_risk` THEME DOES USE ARE WEAKER THAN THE TWO IT REJECTS:**
    `neg_vol` **+0.8873** and `neg_beta` **-0.3937**, against `neg_max_ret` +1.1510 and
    `neg_idio_vol` +1.2105. **The theme carries ZERO weight in the live composite**, which bounds
    the consequence entirely - **but anyone un-zeroing it should read those four numbers first.**
  * **REGISTRATION IS MEASUREMENT, NOT SCORING, AND THAT WAS GATED RATHER THAN ASSERTED.** The six
    were added to `NUMBER_THEME` (the S2 `cash_op_prof` pattern, `NUMBERS_ALL` 47 -> 53) so they
    acquire a `z_` column, a coverage entry and a per-signal IC row. Every theme mean is an
    **explicit column list**, checked in the code first; **C1 then tested EXACT equality** on
    `long_short_tstat` **2.8360640685320595** and three more headlines. **A tolerance would have let
    a real scoring change through.**
  * **FOUR STALE COMMENT SITES CORRECTED IN PLACE, AND THE DECISIONS UNTOUCHED.** The `sm_breadth`
    swap is **ROUTED, not made** - changing a theme input is a construction change and a vintage
    event. **C7 NOT TRIGGERED and reported as not-run rather than skipped** (neither volatility
    cousin replicated, so R5's own earlier size-interaction clause never fired).
  * **Equity `N` 212 -> 218**, haircut 3.2731 -> 3.2816, **under 0.009 of a *t*** - the ledger's own
    "trial cost is now negligible" argument confirmed at today's `N`. Expectations **6 right, 2
    wrong**; the informative miss is that I priced a better-than-even chance the "wrong-signed"
    finding would survive the universe correction, and **all three signs flipped**.
    `data/free_analysis/R5_R6_ALPHABETICAL.json`; `HANDOFF_edge_audit.md` R5+R6 sections 0-9.
- **THE DIP BRANCH LIVES: A HEALTHY 20% DRAWDOWN FALLS A FURTHER 20% A QUARTER LESS OFTEN, AND IT
  IS NOT A SIZE SORT - BUT THE WORD "DIED" IS NOT EARNED (2026-08-13, `V6-B`).**
  `PREREG_v6b_dip_survival.md` committed **ALONE at `dc5ae98`**, a strict ancestor of every
  measurement commit. **ADOPTS NOTHING; no file under `valuation/` changed.** The register's own
  kill condition would have closed the branch at two sessions if the primary arm had failed. **It
  did not fail.**
  * **ARM 1 M1 IS REAL AND IS THE LARGEST REPLICATED EFFECT THIS PROGRAMME HAS PRODUCED IN A LONG
    TIME.** On **37,014 dipped rows** over 68 dates, `P(a further -20% within 126 trading days)` is
    **32.51% for the HEALTHY set against 43.35% for the unhealthy** - a **10.8pp absolute, 25.0%
    relative** reduction. The registered per-date statistic is **-10.228pp at HAC *t* -10.5847**
    against its own permutation p5 of -1.7072, **replicated in BOTH halves** (-9.064pp early,
    -11.515pp late), sign-stable, and clearing the **pre-committed 3.0pp economic floor** more than
    threefold. **The effect runs FOUR TO FIVE TIMES its own minimum detectable effect in every
    window** - the exact opposite of V6 and S19, where no cell reached detection at all.
  * **M3 CORROBORATES ON A DIFFERENT STATISTIC AND THE TAIL IS WHERE IT SHOWS** (+5.853pp, *t*
    +10.9212, clearing its bar in all three windows): forward 126d drawdown **p05 -0.4635 healthy
    against -0.6472 unhealthy - an 18.4-point shallower left tail** - and worst observed -0.8907
    against -0.9954.
  * **IT IS NOT A SIZE SORT, AND THAT IS THE CAVEAT THAT DECIDED THE RESULT.** C8 measured the
    healthy dipped set at **2.06x** the median market cap of the unhealthy one - U7's and S10's
    failure mode - so C8 was deepened into a within-size stratification, **labelled POST-HOC and
    carrying NO verdict**: **five of five market-cap quintiles negative, five of five clearing their
    own p5 full-sample, FOUR of five clearing both halves, smallest effect anywhere 3.787pp - still
    above the economic floor.**
  * **BUT THE GRADIENT CUTS AGAINST THE SHIPPED BOOK, AND THIS MUST TRAVEL WITH THE HEADLINE:
    -14.287pp in the SMALLEST quintile against -3.787pp in MEGACAPS**, which is also the one
    quintile that **fails** the both-halves leg. **The live hot list is megacap-tilted, so the claim
    is strongest exactly where the product is not.**
  * **THE WORD "DIED" IS NOT EARNED, AND THIS IS THE SENTENCE THAT MATTERS MOST.** The metric that
    separated is a further **-20%** - **DEEPENING, not DYING**. **M2, the actual bankruptcy /
    regulatory-delisting metric, is VOID - UNDERPOWERED BY CONSTRUCTION** at **42 distress events
    against a floor of 60 pre-committed before any count was read**, and **none of its numbers are
    quotable** (its early half fails its own bar at *t* -1.9683 against p5 -1.9683). **The earned
    sentence is about falling further, not about defaulting.**
  * **A PREMISE THAT REWROTE THE TASK'S OWN SECOND METRIC: 82.63% OF DELISTINGS ON THIS UNIVERSE
    ARE ACQUISITIONS** (585 of 708; bankruptcy 97, regulatory 13), every one also flagged
    `delisted`. So a naive `P(delisted)` principally measures **takeover probability**. Distress is
    `bankruptcyliquidation` + `regulatorydelisting` and nothing else. **AND MY REGISTERED MECHANISM
    WAS BACKWARDS:** I argued acquisitions would run AGAINST the healthy set; measured, the
    **UNHEALTHY** set is acquired **MORE** (0.292% vs 0.484%, ratio **0.604**), so a naive
    `P(delisted)` would have **EXAGGERATED** the healthy set's advantage rather than reversing it.
    **The rule was right and the reason I gave for it was wrong.**
  * **ARM 2 (the top-decile overlay) IS NULL ON BOTH HORIZONS**, and reported because a late-half
    figure this size invites quoting: 63d **flips sign between halves** (-0.095pp/yr early,
    **+10.919pp/yr** late, full +4.993pp at *t* +1.1188 vs p95 1.6421); 126d is sign-stable but
    clears neither half (+6.375pp full, *t* +1.3840). **C7 reads 11,426 top-decile rows over 69
    dates - the identical count S10 reported independently**, which is what makes this the same
    object the published `top_decile_alpha` describes. C8 shows the tilt runs the OTHER way here
    (dipped names inside the decile are **0.58x** the size of the rest), so Arm 1's size story and
    Arm 2's are not the same story.
  * **ARM 3 (dip x insider open-market buying) IS NULL - AND NOT ON COVERAGE**, which refutes half
    my own expectation: median **106** buy-flagged dipped names per date against a floor of 10.
    Full +1.147pp/yr at *t* +0.5904; the late half is **+0.011pp (*t* +0.0041)**, i.e. absent.
    **C6 confirms it is not the shipped theme renamed: Spearman against the `insider` theme is
    +0.2935.** Built from **`transactioncode` P only** - 124,181 open-market purchases with **zero**
    negative-share rows - because `transactionvalue` is **UNSIGNED** (0 negatives in 2.6M) and the
    shipped `_insider_score` silently **skips 2,182,601 rows (38.7%)** carrying neither price nor
    value.
  * **CONTROLS: C1 gated in its OWN pass** and reproduced the record to 16 digits; **C3 ZERO
    point-in-time violations** on all three routes, including that **no ACTIONS event dated on or
    before the rebalance date counts as a forward outcome**; **C4** 968 censored rows **DROPPED**
    rather than scored on a short window; **C6 FIDELITY - the healthy share of dipped rows is
    26.8%, reproducing V6's own 0.2683**, which is the proof the floors were not re-tuned (void
    condition 6.3).
  * **`V6-OPT` (cash-secured puts) IS UNLOCKED, inheriting three caveats**: the claim is about
    falling further and **not** defaulting; it is **weakest in megacaps**; and **V6 already showed
    this same population carries NO return edge** (four nulls), so a CSP case rests on the risk
    profile and the premium, never on expected appreciation.
  * **Equity `N` 206 -> 212.** Expectations **5 right, 2 wrong, 1 split** - and both misses are
    about MECHANISM rather than verdict. `data/free_analysis/V6B_DIP_SURVIVAL.json`;
    `HANDOFF_edge_audit.md` V6-B sections 0-11.
- **THE DIP DETECTOR'S CLAIM IS NOT SUPPORTED - FOUR ARMS, FOUR NULLS - AND THE USEFUL NUMBER
  IS THAT A DRAWDOWN IS SUBSTANTIALLY AN INVERSE-MOMENTUM SORT (2026-08-13, `V6`).**
  `PREREG_v6_dip_detector.md` committed **ALONE at `93e3e60`**, one `.md`, zero `.py`, a strict
  ancestor of every measurement commit - and **registered BEFORE the tab exists and before any of
  its copy was written**, which is the strongest ordering available. Measured, not assumed: no Dip
  Detector tab, no `V6` row anywhere, and the word "dip" appears nowhere in `valuation/`.
  **ADOPTS NOTHING; no file under `valuation/` changed.**
  * **ALL FOUR ARMS NULL** (20%/30% below a 252-day trailing high x 63d/126d). Full-sample
    vs-universe: **+0.585pp, +0.705pp, -0.480pp, +0.174pp**/yr; vs-unconditioned-dips **+2.108,
    +0.977, +2.081, +0.881**. Bars are **each leg's OWN within-date permutation p95** (500 draws,
    landing at *t* **1.44-1.86**). **X7's 2.2837 and 1.95pp were NOT quoted** - X7 calibrated a
    decile-book long-short *t* and a top-decile alpha margin, and this is neither object.
  * **THE FINDING THAT IS NOT THE VERDICT, AND IT IS THE ONE THE PRODUCT NEEDS: on this panel a
    drawdown is substantially an INVERSE-MOMENTUM SORT - Spearman(drawdown, `momentum` theme)
    = +0.6642** (`low_risk` +0.4196, `size` -0.2914, `value` -0.0834). **So a dip tab would
    systematically surface names the live composite is marking down** - two screens that disagree
    by construction. **I registered that correlation below 0.4 at 60/40 and was wrong**, and the
    register's "a drawdown is a different object" claim is half right: different from *short-term
    reversal* (which is not a panel column at all), **not** different from *momentum*.
  * **SEVEN OF EIGHT LEG-SERIES FLIP SIGN BETWEEN HALVES, ALL THE SAME WAY** - negative over
    2009-01-15 -> 2017-04-20, positive over 2017-10-18 -> 2026-01-28 (2017-07-20 embargoed).
    Session 7's LOO pattern again, but **systematic rather than scattered, which sharpens the
    warning: A DIP DETECTOR BUILT AND VALIDATED ON THE LAST EIGHT YEARS ALONE WOULD HAVE LOOKED
    LIKE IT WORKED.** The early half is the only thing that stops it. **Two half-cells clear their
    own p95 - both LATE, both on the dipped-vs-dipped leg** - A1 at *t* **1.6782 vs 1.6634, a
    margin of 0.0148**, and A4 at 1.6387 vs 1.4381. **1 arm of 4 clearing 1 half of 2**; the
    family-wise clause earns its keep for the fourth time.
  * **NULL MEANS "COULD NOT BE SEPARATED AT THIS RESOLUTION", NEVER "ABSENT" - QUOTE IT WITH THE
    MDE OR DO NOT QUOTE IT.** **No full-sample cell's observed effect reaches its own minimum
    detectable effect on either reference**: A1's dipped-vs-dipped **+2.108pp against an MDE of
    +3.371pp at the register's own bar** and +4.177pp at the conventional |*t*|=2. **Both
    references are reported deliberately** - a *t*=2 MDE against a p95 bar of 1.6 overstates how
    coarse the design is, and no MDE at all understates it. S19's lesson on a new instrument.
  * **THE CONDITIONING IS PARTLY A SIZE SCREEN, WHICH IS A CAVEAT ON THE DIPPED-VS-DIPPED LEG.**
    The floors keep only **26.8%** of dipped names at 20% (22.3% at 30%) and what they keep is
    **1.73x larger by median market cap** ($4.654B vs $2.690B; 1.82x at 30%). Since that leg
    compares conditioned names against ALL dipped names, part of it is large-dipped vs
    small-dipped - **U7's and S10's failure mode**. It does not threaten a NULL verdict.
  * **THE HEALTH FLOOR BINDS HARDER THAN QUALITY, REFUTING MY OWN REGISTERED PREDICTION.** Of
    37,982 dipped rows, quality alone keeps **41.15%** and health alone **35.88%** (both 26.83%).
    The 0-100 health scale's midpoint of 50 sits above the panel's own median health of **46.02**.
  * **THE PRIOR THE TASK CITED IS REAL BUT WEAKER THAN IT SOUNDS, AND WAS FIXED IN THE REGISTER
    BEFORE ANY RESULT.** `P4-3` rejected short-term reversal on **2026-07-29** - the 800-name era
    audit **B12** showed was an **ALPHABETICAL A-C slice**, which `CLAUDE.md` already lists as
    needing a full-universe re-run. **So this null is NOT a re-rejection of short-term reversal
    and may not be reported as one**; that item is still open.
  * **THE BINDING LIMIT, COMMITTED AS AN ASYMMETRY BEFORE THE RUN: the tab's own live sub-scores
    are NOT computable point-in-time** (quality needs a WACC, and **S23** measured that path
    fetching **LIVE Yahoo prices** to value 1999). The arm used the panel's `quality` theme plus a
    point-in-time health score that **CALLS the shipped `_health_score`** rather than retyping its
    breakpoints. **So a NULL here IS informative** - it used the panel's strongest theme, IC *t*
    **+3.10** - **but a POSITIVE would NOT have licensed the tab's copy** without a separate
    live-vs-panel fidelity check. *Coverage is not fidelity.*
  * **CONTROLS: C1 GATED AND RAN IN ITS OWN PASS** (`--controls-only` exits before any arm is
    scored - session 26's defect stays repaired), reproducing the record to **all 16 digits**;
    **C2** 69 dates / 2,531 names asserted not warned; **C3** zero point-in-time violations, pinned
    by a synthetic panel where a post-date crash must not move the flag; **C4** drawdown coverage
    **98.33%**, health **100.00%**, and **zero rows took the cash-burner branch** - reported, not
    silently routed; **C5 THE SPLIT TRAP PINNED FROM BOTH SIDES** - a 2-for-1 split reads as a
    **-50% drawdown on a RAW series and as no dip at all on the adjusted basis**, and since
    companies split **after they rise**, a raw basis would have flagged the strongest names in the
    universe; **C6** no per-ticker tail (B6).
  * **FOUR DEFECTS IN MY OWN INSTRUMENT, ALL CAUGHT BEFORE ANY VERDICT EXISTED.** A degenerate
    permutation draw crashed the run, and **treating it as 0.0 would have padded the null with
    fake draws and LOWERED the p95 - i.e. made the bar EASIER**; a test of mine could have passed
    vacuously and got a positive control; **two controls were pointed at column names the panel
    does not have** - C8 read `marketcap` where the panel's column is **`market_cap`**, so a
    `.get()` would have returned `None` and read as *"no size tilt"* rather than *"this control
    never ran"*, removing the only guard against reporting a size sort as a quality finding
    (U2's near-miss class); and a speedup **whose stated justification was false** - a 500-draw
    sweep costs ~2 seconds, not minutes, and on one leg the "optimization" is **slower** - kept
    only because it is **verified inert** (KS *p* 0.4599 / 0.5089).
  * **THE APP LANE SHIPPED THE TAB WHILE THIS WAS MEASURING IT, AND BUILT THE SAME MECHANISM
    INDEPENDENTLY - SO THE CLOSE-OUT WAS DONE ON THEIRS.** `6b7c358` landed **twelve minutes
    before this pushed**, carrying `valuation/web/dip_posture.py`: modelled on the same
    `score_confidence.py`, owning the copy, pinned by test, with a three-state `STATUS`
    (`OPEN`/`POSITIVE`/`NULL`) explicitly gated on **this register** and a designed close-out.
    **Creating a second module owning the same copy is the exact defect both lanes wrote their
    docstring to prevent**, so `STATUS = NULL` and the verdict fields were filled on theirs;
    **39/39 `test_dip.py` pass.** **Their design is better than mine in one respect and it should
    be carried forward: they enumerated what may never be said in ANY state** - a `BANNED` tuple
    (*"buy the dip"*, *"will recover"*, *"oversold"*, *"sentiment-driven"*) asserted **against the
    RENDERED payload, not the source**, because rendering is where copy leaks.
  * **TWO DEFECTS THE CLOSE-OUT EXPOSED, both invisible until a real verdict existed, and the
    second is the serious one.** **(a)** `REGISTER` cited **`PREREG_v6_healthy_drawdown.md`, a file
    that does not exist** - the register is `PREREG_v6_dip_detector.md` - against a docstring
    saying the citation is there so a reader *"can check that the file exists rather than taking
    the citation on trust"*. Two lanes named the same unbuilt thing differently, which is the
    ordinary cost of registering ahead of a product; the replacement test now asserts **the file is
    on disk** rather than that the string starts with `PREREG_`. **(b) A NULL VERDICT WOULD HAVE
    SILENTLY UNBLOCKED AN OUTBOUND PUSH.** `digest_eligible` was `STATUS != OPEN`, under the comment
    *"an outbound push of a dip list is a recommendation-shaped message, so it waits for the
    evidence"* - but **a NULL is evidence NOT arriving**, so its arrival would have flipped the
    digest ON. The rule it came from (*a NULL must be exactly as reachable as a POSITIVE*) is right
    and the **copy** still obeys it; it had been carried one step too far, because **the digest does
    not push the verdict, it pushes a LIST OF NAMES.** Now `STATUS == POSITIVE`, so the close-out
    leaves the push where it was rather than opening it. **ROUTED, NOT DECIDED - whether a dip list
    should ever go out is Don's and the app lane's call.** `PT-OUTBOUND`'s family, caught before it
    could fire.
  * **THIS IS THE ONE PLACE V6 TOUCHES `valuation/web/`, AND IT IS A SCOPE CHANGE AGAINST THE
    REGISTER'S OWN SECTION 8, MADE AFTER THE RESULT EXISTED - DECLARED, NOT ABSORBED.** The
    alternative was leaving a **live** surface telling users *"we are testing it, and this page will
    say the answer when the register closes"* after it had closed - the module's own stated failure
    mode (*"Prose in a template does not stop; someone has to remember"*). Both changes move the
    product **more** conservative, and neither touches an arm.
  * **THE EXPLAINER CONSTANT IS NAMED AND IS THE APP LANE's TO BUILD:
    `valuation/web/dip_confidence.py`**, modelled on the shipped `valuation/web/score_confidence.py`
    (V3's precedent - one module owns the calibrated wording, pinned **verbatim** by a test).
    **`VERDICT = "NULL"`**, and the tab may call the screen **a filter, not a forecast**: it finds
    names well below their recent high, and the project has **not** shown they beat the market.
    **AMENDED BY THE CLOSE-OUT ABOVE: V6 touches `valuation/web/` in exactly ONE file,
    `dip_posture.py`, and nowhere else** - the boundary the register set
    before the result existed.
  * **Equity `N` 202 -> 206**, re-measured from `research_log.detail()` after this session's merge
    rather than quoted from this file - the S17/S19 defect, not repeated. Expectations **3 right,
    4 wrong, 1 split**. `data/free_analysis/V6_DIP_DETECTOR.json`; `HANDOFF_edge_audit.md` V6
    sections 0-11.
- **THE "CONVEX OVERLAY AS INSURANCE" IS NOT INSURANCE — IT IS LEVERAGE, AND IT LOSES THREE TIMES
  WHAT IT WAS SUPPOSED TO BE DIVERSIFYING; THE U-SERIES IS NOW CLOSED, THREE OF ITS ROWS BY DESIGN
  MEMO RATHER THAN BY MEASUREMENT (2026-08-13, session 37, `U3`+`U4`+`U6`+`U8`).**
  `PREREG_u3_convex_overlay.md` committed **ALONE at `9603e64`** — one `.md`, zero `.py`, a strict
  ancestor of the measurement commit. Frozen books on both sides, no panel rebuild. **ADOPTS
  NOTHING.** `U4`/`U6`/`U8` are `DESIGN-RECORDED` in `DESIGN_u4_u6_u8.md` at **zero trials** —
  the task asked for memos where a memo is the honest deliverable, and no backtest was
  manufactured for them.
  * **THE AUDIT'S PREMISE IS REFUTED BY MEASURING WHAT THE SLEEVE IS MADE OF.** It calls the
    options book a long-volatility sleeve *"built by accident"* whose conditional correlation to
    the equity book *"is the whole question"*. Measured: `opt_right` is **`call` on 3,870 of
    3,870 rows** at mean delta **+0.3725** — long vega **AND** long delta. Correlation with the
    equity top decile **+0.4371**; in the equity book's worst four covered quarters the sleeve
    returns **−84.39%** against its own **+27.52%** average quarter; in **COVID 2020Q1 the equity
    top decile fell −28.09% and the sleeve fell −76.14%**. **No capital weight can make this
    insurance.**
  * **`A1` REJECTED AT BOTH O11 CONCURRENCY CAPS, AND NOT MARGINALLY: MAXIMUM DRAWDOWN IS WORSE
    THAN THE EQUITY BOOK ALONE IN ALL TWENTY CELLS** (cap 10 ΔmaxDD −0.0002 to −0.0021; cap 50
    −0.0048 to −0.0480), improving **monotonically toward X = 100** — so a drawdown-minimising
    optimiser puts **ZERO** in the sleeve, which is `U8`'s answer for free.
  * **THE AUDIT'S OWN TWO-LEG BAR IS WHAT CATCHES IT, AND IT EARNED ITS KEEP.** Sharpe **does**
    improve at cap 10 (1.1296 → **1.2041** at X=96) — purely by **raising return** (+27.01%/yr →
    +34.19%/yr). That is exactly the case `:1284` disqualified in advance: *"a long-vol sleeve
    that improves Sharpe by raising return is not doing the job it is being hired for."* **A
    one-leg Sharpe bar would have adopted this.**
  * **THE AUDIT CONTRADICTS ITSELF AND MEASUREMENT SETTLES IT.** Its step 2 (`:1279`) conditions
    on the equity book's worst decile — **precisely the return-based conditioning its own
    `:1282` warns is an artefact** — and the two give **OPPOSITE SIGNS**: **−0.6504**
    return-conditioned on n=4, against **+0.5478** and **+0.5819** on the high- and low-IV halves.
    **The conditional MEAN is the informative statistic; the conditional CORRELATION is the trap.**
  * **THE ASYMMETRY WAS FIXED BEFORE THE RUN, from the audit's own `:1549`**: a crash-insurance
    rule cannot clear a both-halves gate unless the sample holds two comparable crashes and this
    one holds **one** (S10's trough index 44 of 69). So the register committed that **a decisive
    REJECT was available and a decisive ADOPT was not** — a clearing arm would have been recorded
    `ELIGIBLE-BUT-UNRESOLVED`, never adopted. **Nobody may read this rejection as evidence that
    portfolio insurance does not work.**
  * **NON-BLINDNESS DISCLOSED IN THE REGISTER (§0.5), not after.** A crude probe of A2's **sign**
    was run before the register existed, to decide whether U3 was measurable at all. The register
    says so, excludes that expectation from scoring, and leans on the audit's **verbatim** bar
    rather than one chosen afterwards.
  * **COVERAGE: 40 of 69 quarters, 28 uncovered EARLY and 1 late**, halves **20 and 19** after
    embargoing 2021-01-21 — **S18's and U2's situation for the third time**, so a full-panel gate
    is impossible rather than weak.
  * **`U6` IS NOT BUILDABLE AND THE REASON IS A NUMBER: 1.81% CHAIN COVERAGE.** Of **7,132**
    names entering the top decile over 68 transitions only **129** have mined chains; **median 2
    per rebalance** against a mean top-decile size of **165.6**, and **ZERO on 18 of 68 dates**.
    ~~Second, independent blocker: the entry leg is a cash-secured **put** and the cache is
    **100% calls**, so no put-chain history exists to replay against.~~ **RETRACTED 2026-08-13
    (`V6-OPT`), against my own prior session: THE CACHE IS NOT 100% CALLS.** That measurement —
    `opt_right == "call"` on 3,870 of 3,870 rows — is of the **TRADED BOOK**, and the **CACHE**
    was never checked. Measured: `data/options` holds **1,288,750 puts against 1,288,751 calls**
    across 40 sampled tickers, **exactly 0.5000 put share, ZERO tickers with no puts**, with bid,
    ask, volume and open interest; `data/options_derived` carries the same contracts with `iv`,
    `delta`, `mid` and `spread_frac`. **`V6-OPT` then priced 2,038 real 25-delta puts from that
    cache and settled them to expiry.** The **coverage** blocker is untouched and still carries
    U6's verdict on its own, so the row's status does not change — but it rests on **one**
    measured reason, not two. **A composition fact about a BOOK is not a coverage fact about a
    CACHE.** Same class as `S25` and `B13` — **unobtainable without new data**, and it stays the
    most tradeable idea in the catalogue if the data is ever bought.
  * **`U4`'s GATE HAS RESOLVED, NEGATIVE.** It was gated on `U1`/`U2`; both rejected, as did
    `U7`. So one object may carry **two independently-sourced expressions with an explicit
    statement that they are independent** — no combined score, no combined confidence, no arrow
    from view to trade. And **O11 forces an addition to the copy rule**: expectancy framing is
    necessary but **not sufficient**, so any surface quoting per-trade expectancy must quote the
    survivability result beside it.
  * **A DEFECT IN MY OWN INSTRUMENT, PRESENTATIONAL AND PROVEN SO RATHER THAN ASSERTED.** A3's
    column was named `drag_vs_equity_pp` while computing `combined − equity`, which is **positive
    when the sleeve adds return** — a gain printed under a loss's name. Renamed; the pre-fix and
    post-fix artifacts diff at **344 shared leaves, ZERO moved, 6 added, 0 removed.** Also
    disclosed: the combined book is **rebalanced to weight X every quarter** per the register, so
    the sleeve's geometric **−33.35%/yr** coexists with a **+27.52%/quarter arithmetic** mean and
    the construction **tops the sleeve back up after a crash quarter**, which flatters it.
  * **CONTROLS: C1 reproduces the record at alpha 0.07174142332098163; C3 ZERO look-ahead over
    161,610 marks; C4 `top == alpha + equal_weight` at max abs deviation 0.000e+00; C5 at ρ = 1.0
    the largest improvement is +0.000e+00; C8 X=100 reproduces the equity book at 0.000e+00.
    C7 is the one that cuts: the sleeve is closer to the equal-weighted universe (+0.4837) than
    to the top decile (+0.4371), so it is BETA, not book-specific.**
  * **THE ONLY PRODUCTION CHANGE IS ONE ADDITIVE KEY**: `quantile_backtest`'s opt-in `series`
    dict now carries `equal_weight`, because `top = alpha + equal_weight` is an identity and **you
    cannot compound an alpha**. Inside the existing `return_series` gate, so every current
    caller's payload is bit-identical; pinned by test. **Options `N` 285 → 287** (A1 and A2; A3
    charges nothing); **equity untouched at 190**. Expectations **4 right, 2 wrong, 1 excluded**.
    `data/free_analysis/U3_CONVEX_OVERLAY.json`; `HANDOFF_optionsbot.md` §56.
- **THE OPTIONS SURFACE IS GENUINELY ORTHOGONAL TO THE EQUITY PANEL AND PREDICTS NOTHING WITH
  THAT ORTHOGONALITY — THE AUDIT'S CENTRAL PREMISE IS CONFIRMED AND ITS CONCLUSION REFUTED, AND
  THE LAST LIVE DIRECTION OF THE UNIFICATION IS NOW SHUT (2026-08-13, session 36, `U2`).**
  `PREREG_u2_surface_stock_signals.md` committed **ALONE at `e8e222b`** — one `.md`, zero `.py`,
  a strict ancestor of the measurement commit. No panel rebuild. **ADOPTS NOTHING.**
  * **THE ROW CLOSES `PARTIAL`, NOT `DONE`, AND THE REGISTER FIXED THAT BEFORE ANY RESULT.** The
    audit's U2 names four features; this tested the **levels** and declined two. **The put–call
    parity deviation on matched strikes — Cremers–Weinbaum's ACTUAL measure and the largest
    effect the section cites (51 bps/week) — needs matched call/put pairs from the raw chains and
    is a NEW feature**, which the task forbade; the 21-day changes are a different hypothesis
    (surface *momentum*, not surface *level*). **Neither is a null.** Marking the row `DONE`
    would tell the next session they had been tested. S10's precedent.
  * **A DUPLICATE ARM KILLED BEFORE THE REGISTER: `skew_25d` IS EXACTLY `iv_put_25d −
    iv_call_25d`**, max |Δ| **0.000e+00** over 217,706 rows. So the audit's separately-named
    *"ATM call-minus-put implied-vol spread"* is, at 25 delta, **exactly `−skew_25d`** — one
    column and its negation, whose rank ICs are exact negatives. **ONE arm, not two.** This is
    the `illiq`/`spread_pct` defect class the O3/O4/O5 lane found in a prior lane's panel,
    **caught before the register rather than after the verdict**, and pinned by C5.
  * **THE NEAR-MISS THAT WOULD HAVE ANSWERED A DIFFERENT QUESTION ENTIRELY: the shipped
    `term_slope_60_30` is NOT the O16-validated construction.** It is exactly `atm_iv_60 −
    atm_iv_30`; O16 validated `atm_mid − atm_front`. **Spearman between them is only 0.5281** on
    the covered names. A lookup by column name computes cleanly, raises nothing, and **reports a
    U2 verdict on a construction O16 never validated** — while O16's whole finding was about
    separating `term_slope` from a front-end IV level. The arm uses **`atm_iv_60 −
    atm_iv_front`** and a **source-level test pins that the shipped column never enters the arm
    path**.
  * **COVERAGE FORBIDS A FULL-PANEL GATE — AN IMPOSSIBILITY, NOT A POWER CAVEAT.** The derived
    layer spans **2016-01-04 → 2025-12-31** against a panel starting **2009-01-15**, so **29 of
    69 rebalance dates carry ZERO coverage and ALL of them are early**; the final date
    (2026-01-28) is uncovered too. **Every split is of the COVERED SUBSAMPLE — 40 dates, 20 and
    19 after embargoing 2021-01-21**, both above the shipped `min_dates=16`. **S18's situation
    exactly, and the same replacement.** A pass on 20-date halves is not the same object as a
    pass on 34-date halves. Coverage is **~25%** of the panel cross-section (mean **436.9** names
    per covered date), better than the audit's predicted 4–14%.
  * **ALL FOUR ARMS REJECTED** against X7's calibrated **2.71** theme-IC bar in both halves.
    Incremental IC *t*, full sample: `term_slope` **+0.9862**, `iv_rank` **+0.1931**, `skew_25d`
    **+0.3471**; the composite **+0.7797 / +0.1508** across its two decide-then-measure
    directions. Raw IC *t*: **+0.6729**, **+0.0377**, **+1.4870**.
  * **THE HEADLINE IS THE DISSOCIATION, AND IT SETTLES THE AUDIT'S ARGUMENT IN BOTH DIRECTIONS.**
    The audit's case was that an options-derived signal is *"structurally orthogonal to
    everything already in the panel"* — and **it is: the seven incumbents explain only 5.5% to
    8.8% of these features' variance**, against **41.3% of `gp_on_capital`** and **78.4% of
    `ret_6_1`**. **The features really are new information. The new information does not
    predict.** Orthogonality was the audit's reason for expecting value and it is confirmed;
    what fails is the prediction, not the premise.
  * **THE POWER CONTROL THE AUDIT ITSELF DEMANDED CLEARS, SO THESE NULLS ARE INTERPRETABLE —
    AND THE SAME NUMBER CUTS AGAINST THE VERDICT.** `gp_on_capital` **2.4776** and `ret_6_1`
    **2.4762** on the identical covered rows, against the audit's 2.0 bar. **But both land BELOW
    2.71**, so the panel's own best-known signals would *not* clear the bar the arms were judged
    against on this subsample. **And there is NO valid power control for the INCREMENTAL
    statistic at all**, because every known-real signal here is already an *input* to an
    incumbent theme (which is exactly why their R² is 41% and 78%). Reported, not glossed.
  * **THE SMIRK'S PUBLISHED SIGN DOES NOT REPRODUCE.** Xing–Zhang–Zhao's negative direction was
    **declared before the run**; measured, `skew_25d`'s raw IC is **POSITIVE** (median +0.02056,
    *t* +1.4870). Far too weak to refute a published result — but on this megacap universe the
    declared direction is **not reproduced**, and a positive result on it could never have been
    a pass. Same shape as O3/O4/O5's sign reversal.
  * **C6 REFUTES THE OBVIOUS ALTERNATIVE OUTRIGHT.** A volatility-surface feature is a prime
    candidate to be a volatility theme in a new costume (U7's failure mode). The largest |mean
    per-date correlation| against ANY incumbent is **0.0844** (`skew_25d` vs `momentum`), and all
    three sit under **0.05** against `low_risk`. **These are not repackaged incumbents.**
  * **CONTROLS: C1 reproduces the record to 1e-9; C3 ZERO point-in-time violations over 17,411
    joined cells** — the join is **STRICTLY BEFORE** the rebalance date, stricter than `fwd_ret`
    requires, to remove the argument rather than win it; C5 no arm is another arm's negation.
    **The book gate and the 2.2837 long-short floor were NOT run and are NOT quoted**: the
    register runs them only on an eligible composite. **Both calibrated bars would be
    EXTRAPOLATIONS here in any case** — they were measured on the full 69-date 2,531-name panel.
  * **A DEFECT IN THE SHIPPED IC ARITHMETIC, REPORTED NOT REPAIRED, AND IT IS THE
    `SECTOR-NEUTRAL-B6` ZERO-VARIANCE GUARD IN A NEW PLACE.** `theme_ic`'s guard is `if sd > 0`,
    and whether a constant series has an exactly-zero floating-point sd is **value-dependent**:
    `[0.1, 0.1, 0.1]` has sd ≈ 5.8e-17, so the guard passes and the *t* comes back **~1.0e16**.
    Not repaired here, because repairing it would make this lane's copy stop being the shipped
    arithmetic and X7's 2.71 would then apply to a statistic it was not calibrated on. A
    degeneracy check gates the verdict instead, so an absurd *t* can never be READ as a pass.
    **Edge lane's to fix.**
  * **THE SIGNAL-TRANSFER DIRECTIONS OF THE UNIFICATION ARE NOW ALL CLOSED, AND THAT IS NOT
    THE SAME AS CLOSING THE U-SERIES**: `U1` REJECTED (composite → options entry), `U7` REJECTED
    (composite as an options veto), `U2` REJECTED on its level half and `PARTIAL` on the row.
    **FOUR U-ROWS REMAIN OPEN** — `U3` convex overlay, `U4` one decision object, `U6` CSPs in,
    `U8` one risk budget. None is a signal-transfer question, but the O-series discipline
    applies: do not report a series closed while its rows are open. **CLOSED 2026-08-13 (session
    37), and the distinction survives the closure: `U3` closed by MEASUREMENT (rejected), while
    `U4`/`U6`/`U8` closed `DESIGN-RECORDED` — a design record is NOT a measurement, and anyone
    re-opening one of those three re-opens a live question rather than a settled one.** **Equity `N` 185 → 189 for this item's four arms — though it reads
    190 after the concurrent `S14-WIDTH` landing the same day, which is why an equity figure
    must be RE-READ from `by_domain` after every merge and never quoted from a session's own
    mid-run measurement.** Expectations **5 right, 3 wrong, 1 split** — and the streak breaks: this is the first
    session in five in which **no** arm cleared **either** half.
    `data/free_analysis/U2_SURFACE_STOCK.json`; `HANDOFF_optionsbot.md` §55.
- **THE S-SERIES RESEARCH ROWS ARE CLOSED: TWELVE ARMS, TWELVE NULLS — AND BOTH NULLS ARE THE
  INFORMATIVE KIND, ONE BECAUSE IT IS NOT INERT AND THE OTHER BECAUSE IT COULD NOT HAVE DETECTED
  WHAT IT WAS HUNTING (2026-08-13, `S17`+`S19`).** One register for both,
  `PREREG_s17_s19_events_mdna.md`, committed **alone at `a92996d`**. **ADOPTS NOTHING.**
  * **`S17`'S METHOD STEP 1 CANNOT BE EXECUTED, AND THAT IS PERMANENT UNTIL `D10` RUNS.** The
    audit says *"obtain the code legend from Sharadar's documentation"*. **Sharadar ships no
    legend with the EVENTS download** (`bulk.py:20`, `:235`) and `D10` records the docs were
    never extracted. So the codes were tested **BY NUMBER, UNLABELLED** — and the register said
    in advance what that costs: **a signal on an unlabelled code is uninterpretable even if it
    works.** A positive would have been a lead requiring the legend, never an adoption. **Do not
    re-run `S17` without the legend** — it would buy the same uninterpretable numbers for another
    10 trials.
  * **THE MECHANISM QUESTION IS ANSWERED *NO*, AND THE PROJECT HAD ALREADY MEASURED IT.** The
    empirical decode that identified code 22 scored every registered arm on the way past
    (`bulk.py:243-247`): day-of median absolute return against a 1.292% baseline — **code 22 at
    1.64×**, and **91 1.15×, 71 1.13×, 81 0.98×, 52 0.96×, 34 0.94×**. Code 22's mechanism is an
    *information shock* and PEAD is drift **following** it; **the other codes have no shock for
    drift to follow.**
  * **BUT THE ARMS ARE NOT INERT, WHICH REFUTES MY OWN PRIOR WHILE THE VERDICT MATCHED IT.** All
    10 are **NULL** — **not one clears the both-halves leg** — yet **8 of 10 clear their own
    permutation p95 full-sample, 8 of 10 survive Benjamini–Hochberg at q 0.05, and ALL TEN are
    sign-stable across halves.** Annualised: code 91 **−2.2%**, code 71 **−2.0%**, code 34
    **+3.2% to +4.9%**. **They fail by being ERA-CONCENTRATED** (code 91 early *t* −3.476 / late
    −1.862; code 71 early −1.342 / late **−3.098**). **The register's hedge — day-of VOLATILITY
    is not directional DRIFT, and the two come apart for scheduled or slow-diffusing events — is
    the load-bearing part, not the prior it hedged.**
  * **"8 OF 10 CLEAR" IS NOT EIGHT FINDINGS, AND THIS CAVEAT MUST TRAVEL WITH THE NUMBER.** Two
    dependencies stack. **By construction the ten arms are FIVE signals at TWO horizons, and a
    code's 21d and 63d arms share a BIT-IDENTICAL event indicator.** **Measured**, the codes
    correlate up to **0.4227 (91~71)** at name-date level (mean |ρ| 0.1330 over 93,997
    name-dates) and the four negative codes all point the same way. **Effective independent tests
    are nearer three or four** — the SELRULE lesson, where 16 co-moving countries were worth 2–4
    draws — so **BH was fed correlated tests.**
  * **TWO EXPLANATIONS REFUTED BY MEASUREMENT, WHICH IS WHY THE ARMS ARE INTERESTING RATHER THAN
    DISMISSABLE.** They are **NOT market-cap sorts**: median cap of event vs non-event names is
    **0.93×** for code 91 and **1.07×** for code 71 (only code 81, the weakest arm, tilts at
    1.86×), so **U7's and S10's failure mode does not apply.** And **differential survival is not
    the driver** — drop rates 2.4–3.2% with gaps **under 1pp on every negative arm**.
  * **CONTROLS. C1 GATES AND RAN IN ITS OWN PASS**, aborting before any arm on failure — session
    26's defect repaired. Code 22 reproduces at **1.7423×** against 1.64×. **The ordering of the
    other codes reproduces only BROADLY, stated rather than rounded into a clean pass:** 91 and
    71 swap (within 0.007, effectively tied) and code 11 moves up two places. **C3 refutes the B6
    signature directly: 89.1% of names in the earliest cross-sections were still trading ten
    years later**, where a per-ticker tail drives that toward zero. 328 month-ends, cross-section
    median **1,649**.
  * **`S19`: BOTH ARMS NULL — AND THE NULL DOES NOT MEAN THE EFFECT IS ABSENT.** On **418
    held-out names with ZERO overlap** with the original 195 (15,893 filing pairs newly collected,
    **2.2×** the original study): **A1 `mdna_cosine_tf`@21d residual IC +0.012202 at NW *t*
    +1.1876**, **A2 `mdna_jaccard`@63d +0.021737 at +1.4012**. Neither reaches the audit's 2.0.
  * **THE SIGN DID NOT REVERSE AND THE MAGNITUDES GREW.** The register fixed the direction in
    writing first — *more MD&A change → outperform* — and **all four half-cells are POSITIVE**,
    against the original's own **+0.009607 at *t* 0.6463**. A sign flip between halves is this
    project's most repeated failure pattern and **it did not happen here.**
  * **THE DESIGN COULD NOT HAVE RETURNED A POSITIVE VERDICT EVEN IF THE EFFECT WERE EXACTLY TRUE
    — QUOTE THIS WITH THE NULL OR DO NOT QUOTE IT.** A1's **minimum detectable incremental IC at
    |*t*| = 2 is +0.020549** (A2's +0.031026) against an original effect of **+0.0096**. Its
    observed +0.0122 sits **below its own detection threshold**. **NULL means "could not be
    separated from zero at this resolution", NEVER "absent"** — V2G's lesson on a new instrument.
  * **THE BINDING CONSTRAINT IS THE PANEL'S FREQUENCY, NOT THE NAME COUNT, so collecting more
    names cannot re-open it.** MD&A scores start 2016-08 against a panel starting 2009-01-15, so
    **41 of 69 dates are covered and all sit late** — a full-panel both-halves gate is
    **impossible, not merely weak** (`S18`'s class) — and the original tested **111 MONTHLY**
    dates while the theme panel is **QUARTERLY**. Re-opening needs a **monthly theme panel**, a
    rebuild with its own register.
  * **C6 REPRODUCES ONLY LOOSELY AND THE EVIDENCE IS CONTRADICTORY, reported rather than rounded.**
    It passes on the **corrected** panel (+0.011227 vs the published +0.009607) while the **VOID
    pre-B6 panel matches the original's date count exactly (37 vs 37)** and its IC not at all.
    **Most likely neither banked panel IS the original's** — `lazy_prices_ic` builds its own.
    **A finding in passing: the original study's orthogonality block was computed on a pre-B6
    panel the project has since declared VOID**, so its numbers may not be quoted as
    corrected-panel measurements.
  * **`S10`'s ACCOUNTING HALF WAS ASSESSED FOR THIS REGISTER AND EXCLUDED, ON MEASUREMENT.** Every
    SF1 input for Beneish, Altman and external financing **exists** in the export, but **eight
    columns are absent from `WRDSProvider._KEEP`** (`assetsc`, `ppnenet`, `depamor`,
    `workingcapital`, `retearn`, `liabilities`, `ncfcommon`, `ncfdebt`), so it forces a **panel
    rebuild** where `S17`/`S19` needed none; **NT filings are not buildable from anything we own**,
    so the audit's *"flagged by two or more"* of **four** would silently become **two of three** —
    a different rule chosen after seeing what exists. **Still OPEN, scoped, charged nothing.**
  * **A DEFECT IN MY OWN REGISTER, CORRECTED HERE AND NOT EDITED AWAY.** §7 says *"equity `N` 186
    → 198"*; **186 was quoted from this file instead of re-measured after the session's own
    merge**, which brought in `U2`'s four equity trials. **The honest figure is `N` 190 → 202**
    and the charge of 12 is unchanged. **This is the exact error the record already warns about**
    — *re-read `by_domain` after merging* — committed with the warning in view.
    **`BACKTEST_RESULTS.json` was ALREADY stale at 186 against a live 190 before this session
    touched it**, so the refresh corrects `U2`'s drift too.
  * **Equity `N` 190 → 202.** Expectations **8 right, 0 wrong — and the sweep should be
    discounted, not celebrated:** three of the eight predicted NULL in a project where
    essentially everything is null, and **the reasoning behind the `S17` call was wrong even
    though its verdict was right.** Both ledger rows were `src=auto` and wrong — the **eleventh
    and twelfth** *"no section"* note to be false. `data/free_analysis/S17_EVENT_CODES.json`,
    `S19_MDNA.json`; `HANDOFF_edge_audit.md` S17+S19 §0-11.
- **THE NO-TRADE BAND'S KNEE IS IDENTIFIED AND IT IS EXACTLY WHERE THE BOUNDARY WAS — GIVEN THREE
  WIDER WIDTHS, BOTH HALVES STILL PICKED 0.30, SO `S14` IS NOW AN ADOPTION DECISION FOR DON
  (2026-08-13, `S14-WIDTH`).** `PREREG_s14_width_extension.md` committed **alone at `e63295e`**.
  **ADOPTS NOTHING — it routes a decision.** The grid gained 0.40, 0.50 and 0.75 (round
  extensions, nothing finer, `enter_frac` untouched) and the identical decide/held-out procedure
  re-ran in both directions.
  * **OUTCOME (a) OF THREE COMMITTED IN ADVANCE: THE OPTIMUM IS INTERIOR.** 0.30 is the argmax on
    **both** halves against three wider candidates, so session 35's grid-boundary caveat is
    **DISCHARGED, not repeated.** Net alpha by width, early / late: none +1.11/+10.94, 0.12
    +0.87/+11.88, 0.15 +2.02/+12.17, 0.20 +2.08/+11.91, 0.25 +2.17/+12.39, **0.30
    +2.88/+12.72**, 0.40 +2.32/+12.44, 0.50 +2.56/+11.84, 0.75 +2.74/+9.14.
  * **THE PORTABLE LESSON IS A CORRECTION TO MY OWN REASONING, NOT TO SESSION 35's: A BOUNDARY
    ARGMAX IS EVIDENCE THAT A GRID IS UNINFORMATIVE ABOUT WHAT LIES BEYOND IT — IT IS NOT EVIDENCE
    THAT THE OPTIMUM LIES BEYOND IT.** I registered the opposite lean at 60/40 and the extension
    moved the answer not at all. 0.30 happened to be both the boundary and the maximum.
  * **THE MECHANISM IS MEASURED, AND IT BOUNDS THE AXIS. Gross alpha PEAKS at exactly 0.30 on BOTH
    halves and falls away** (late +12.77 → **+13.79** → +13.33 → +12.56 → **+9.65**), because the
    cost saving is **capped** and staleness is not — at 0.30 the drag is already down to
    0.0127/0.0106, so at most ~1.1–1.3pp more exists even at zero turnover. **And the freezing
    argument, derived from the CODE before running, is now measured: the book's incumbent share
    climbs 0.359 → 0.701 at 0.30 → 0.943 at 0.75**, i.e. at 0.75 the book replaces one name in
    sixteen per rebalance and has largely stopped selecting. `_band_select` holds book SIZE fixed,
    so at an exit rank equal to the universe the book **FREEZES** — pinned by test.
  * **WHAT IT DOES NOT ADD, STATED PLAINLY: NO NEW HELD-OUT EVIDENCE ABOUT THE SIZE OF THE
    EFFECT.** The pick did not move, so the held-out measurement is **numerically identical** to
    session 35's (+1.780125pp / +1.768484pp, agreeing to **ten decimals**). The trial buys the
    **LOCATION** finding only.
  * **THE KNEE REPLICATES IN LOCATION BUT NOT IN SHARPNESS.** Decisive on the late half (0.30 →
    0.75 costs **3.59pp**); nearly **FLAT** on the early, where 0.75 is second best at **+2.74pp**,
    only **0.14pp** below the peak. **An adopt at 0.30 is well supported by the late half and
    weakly by the early one.**
  * **A DEFECT IN MY OWN CONTROL, AND IT MOVED NOTHING.** C3's first cut asserted **LIST** equality
    of the no-band book against plain top-N and failed **176 of 200** — `_band_select` returns
    survivors **first**, so the ORDER differs while the **SET is identical (200/200)**. Proved
    harmless rather than argued: a strict-rank selector swapped into the real panel moves every
    reported field by at most **2.13e-14** (the book is equal-weighted, so only the set can reach
    a number). **ZERO verdict cells moved.** **Session 35's C6 is also corrected: the EARLY-half
    surface is non-monotone too**, its monotonicity having been an artefact of the grid stopping
    at its own argmax.
  * **CONTROLS: C4 book size IDENTICAL at every width** (154.1 names early, 175.6 late), so no
    comparison is confounded by book size — S23's dilution mechanism cannot be operating here;
    **C2 turnover strictly decreasing across all nine settings on both halves** (0.75 runs about a
    fifth of the no-band book **and still loses**); **C1b all 48 shipped-width cells reproduce
    session 35's raw artifact at max |Δ| 1.33e-15.**
  * **FOR DON, AND THIS IS THE DECISION.** Width **0.30**, +1.78pp/+1.77pp net alpha held out,
    turnover roughly halved. It is **already live in the `taxable` configuration**, so an adopt
    changes the **DEFAULT**, not whether the band exists. It is a **VINTAGE EVENT**: the vintage
    was **DERIVED, not assumed** — **vintage 3, run 2, opened 2026-08-11, OPEN, i.e. TWO DAYS
    OLD** — so adopting resets the five-year clock a second time inside three days. And **roughly
    half the gain is a SIGNAL effect**, not the deterministic cost saving the original framing
    claimed. **B13 is only PARTIAL.**
  * **A THIRD EXTENSION IS FORBIDDEN by the register**, and the surface is documented end to end.
    **Equity `N` 185 → 186.** Expectations **2 right, 4 wrong, 1 split** — four of the five misses
    are the same invalid inference above. `data/free_analysis/S14_WIDTH.json`;
    `HANDOFF_edge_audit.md` S14-WIDTH.
- **THE NO-TRADE BAND CLEARS — THE FIRST ARM TO DO SO IN EIGHT SESSIONS — BUT NOT FOR THE REASON
  ITS REGISTER CLAIMED, AND ITS OPTIMUM SITS AT THE GRID BOUNDARY; SECTOR-NEUTRAL IS NOW FINISHED
  IN EVERY FORM (2026-08-12, session 35, `S14`+`S15`).** One register for both,
  `PREREG_s14_s15_band_sectorvalue.md`, committed **alone at `32051c0`**. **ADOPTS NOTHING.**
  * **`S14` IS ADOPT-ELIGIBLE, IN BOTH DIRECTIONS.** Sweeping the shipped width grid on the
    **decide** half and measuring the argmax on the **held-out** half, both directions pick width
    **0.30** and both clear: net alpha **+1.78pp / +1.77pp**, gross alpha **+1.02pp / +0.77pp**,
    measured cost saving **+0.76pp / +1.00pp**. **Turnover roughly HALVES** (2.6078 → 1.3514 and
    2.5800 → 1.4198) and the measured drag falls 0.0227 → 0.0126 and 0.0182 → 0.0106.
  * **CORRECTION TO MY OWN REGISTER #1, AND IT CHANGES WHAT THE RESULT MEANS: THE "PURE COST
    MECHANISM, NO SIGNAL CLAIM" FRAMING IS WRONG.** **Gross alpha IMPROVES**, so roughly **half**
    the gain is a *signal* effect, not a cost saving — holding a name until it leaves the top 30%
    rather than the top 10% stops the book churning on rank noise. That is a construction change
    with a real return consequence, and it means the audit's category-error argument (don't apply
    a signal margin to a mechanical saving) is only **half** applicable.
  * **CORRECTION #2: MY INDICTMENT OF THE AUDIT'S 1.5pp ALLOWANCE WAS TOO STRONG.** The register
    computed the saving at ~26 bps from the audit's quoted turnover and called the allowance **6×**
    wider than the prize. **The measured saving is 76–100 bps**, so it is ~**1.5×**. Tightening the
    guard was still right and the arm passes either way, but the magnitude asserted before the run
    was wrong.
  * **THE CAVEAT THAT MUST TRAVEL WITH THE VERDICT: THE ARGMAX IS AT THE GRID BOUNDARY IN BOTH
    DIRECTIONS.** 0.30 is the widest width the shipped grid contains and it won both times, so
    **the optimum is at or beyond the edge and the knee is NOT identified** — the selected width is
    an artefact of where the grid stops. **A wider grid is the obvious next test, not an
    adoption.** **C6 confirms the audit's noise warning**: the net-alpha surface is monotone on the
    early half and **not** on the late, where 0.20 dips below 0.15.
  * **A MECHANISM THAT SUPPORTS IT: S22 measured that top-decile alpha is still accruing at two
    years while a name typically stays in the decile for ONE rebalance.** A wider band harvests
    persistence the incumbent's tight exit throws away — the direction S22 pointed at and declined
    to test. **Recorded ELIGIBLE, not adopted** (a vintage event, and Don's call); **1 of 2 sibling
    arms**, though stronger than that label implies since it cleared **both** halves in **both**
    directions. **The band is ALREADY LIVE in the `taxable` configuration**, so an adopt would
    change the *default*, not introduce it. **B13 is only PARTIAL**, so "the book is investable"
    holds for the categorical screen and **not** the liquidity one.
  * **`S15` IS REJECTED AND ESSENTIALLY INERT — AND WITH IT, SECTOR-NEUTRAL IS FINISHED IN EVERY
    FORM.** `SECTOR-NEUTRAL-B6` named exactly two routes back: **`S25`** (closed **UNOBTAINABLE**
    in session 29) and **`S15`** (rejected here). **Both are shut.** Measured: Δalpha −0.01pp /
    −0.36pp, rank correlation **0.9879**, only **5 of 25** top names changed.
  * **CONTROL C4 IS EXACT AND IS WHAT MAKES S15 THE NARROW EXPERIMENT IT CLAIMS TO BE: every
    NON-value theme comes back BIT-IDENTICAL at max |Δ| 0.000e+00**, while `value` moves by
    1.5568. It moves the book **less** than the broad version did (0.9879 vs B6's 0.9836), as
    pre-registered. The buy-*t*-sell-alpha flag **did** fire on the late half — predicted at 55/45
    that it would not — but at −0.36pp for +0.037 of *t*, **inert describes it better than
    trade-off**.
  * **THE STANDING SECTOR CAVEAT NOW HAS NO REMEDY.** TICKERS supplies **today's** sector applied
    to 1998 rows; `S25` was the item that would have fixed it and it is closed. **Any future
    sector-aware result on this panel inherits a look-ahead that cannot be repaired on data we
    own.** **Equity `N` 183 → 185.** Expectations **4 right, 3 wrong** — the worst score in these
    sessions, and informative for it: both consequential misses are on S14, predicted to fail.
    `data/free_analysis/S14_S15.json`; `HANDOFF_edge_audit.md` §1-8.
- **THE HORIZON ENSEMBLE BUYS A REAL TURNOVER REDUCTION AT 11× TO 23× ITS OWN COST, AND THE
  BUCKET ARM MISSES BY 18 BASIS POINTS (2026-08-12, session 34, `S11`+`S12`).** One register for
  both, `PREREG_s11_s12_horizon_bucket.md`, committed **alone at `d867fe3`**. **ADOPTS NOTHING.**
  * **S11's PRIOR WAS REAL AND IS RECORDED: S22 measured the out-of-sample rank IC RISING with
    horizon (+0.034 → ~+0.072).** The counter-prior won anyway. **REJECTED in both halves and by
    the widest margin of the three arms** — Δalpha **−4.22pp / −2.05pp**, Δ*t* −2.353 / −0.927 —
    and the long-short leg moved against it **exactly as pre-registered**, because S22 had already
    measured that the persistence lives entirely in the long leg while the spread's HAC *t*
    collapses 2.7167 → 0.6846.
  * **THE AUDIT'S SECONDARY CLAIM IS CONFIRMED AND IS THE MOST USEFUL NUMBER HERE — AND IT IS A
    TERRIBLE TRADE.** Turnover falls **0.6352 → 0.4976** per rebalance, ~55pp of book per year.
    **At the project's own measured 33.4 bps one-way that saves roughly 18 bps/yr against 205–422
    bps of alpha given up — the trade runs 11× to 23× AGAINST.**
  * **C6 CONFIRMS THE COUNTER-PRIOR DIRECTLY: the two horizons' weight vectors correlate +0.9013
    and +0.9674**, so the ensemble is largely **one composite twice**. **A CONFOUND NAMED
    HONESTLY:** the blend's rank correlation against the *deployed* composite is only **0.6939**
    while the two horizons agree above 0.90 — so most of the arm's deviation comes from using
    **IC-proportional weights at all**, one of the eight schemes CPCV has always declined, not
    from blending horizons. The audit's own construction makes that unavoidable, since two
    flat-weighted composites would be identical.
  * **A SCOPE DIVERGENCE ON S12, NAMED BEFORE ANY RESULT (S10's class).** The audit's S12 is the
    **VALUATION bucket** — *"defined by how a name is valued, not by industry"* — while the task
    framed it as the **cap tier**. **Both tested as separate arms**, so the row closes on both
    readings and neither is reported as the other.
  * **A2 (VALUATION BUCKET) IS NOT_REPLICATED AND IS THE CLOSEST ANY ARM HAS COME IN THESE
    SESSIONS.** Positive on alpha in **both** halves (**+1.36pp / +0.82pp**) and positive on Δ*t*
    in both (**+0.478 / +0.347**) — it fails only because the late half misses the pre-committed
    +1.00pp bar **by 18 basis points**. **That is S21's shape exactly** (which missed by 17bps and
    was recorded not-replicated); ambiguous against a pre-committed threshold is a **NULL**
    (`RUN_RULES` A6), and it is **1 of 3 sibling arms**. Small intervention — rank corr 0.9807,
    top-25 changed 4 of 25. **NOT eligible, NOT adopted, and +1.36pp may not be quoted without
    both labels.** **The fourth consecutive session in which exactly one arm clears exactly one
    half.**
  * **A3 (CAP TIER) IS REJECTED AND NEARLY INERT** — Δalpha +0.09pp / +0.07pp. **C8 confirms the
    pre-registered mechanism**: the book's mean `size` z-score falls **0.5885 → 0.5092 (13.5%
    shrink)**, so it does neutralise the exposure X3 says carries the composite's entire
    significance — **but the alpha effect is ZERO rather than negative**, so it fails by being
    inert rather than harmful, a milder outcome than predicted.
  * **THE AUDIT'S OWN METRIC PRIORITY WAS ADOPTED VERBATIM** — *"top-decile alpha decides, not the
    t-statistic"* — and **no arm triggered the bought-*t*-sold-alpha flag**, so sector-neutral's
    failure shape did **not** recur.
  * **A NEAR-MISS CAUGHT BEFORE THE BUILD AND PINNED:** `bucket` is derived **after** the granular
    standardisation, so a naive lookup by column name would have found nothing, done nothing, and
    still reported a verdict on **an arm that never ran**. **A CONTROL THAT DID NOT RUN, REPORTED
    AS SUCH:** C7's bucket half came back empty for the same reason (the diagnostic column emitted
    `None`); the **arms are unaffected**, and the number was recovered from the key-identical
    corrected panel — **established 1,312 / speculative 339 per date**, both substantial.
  * **Equity `N` 180 → 183.** Expectations **7 right, 0 wrong**.
    `data/free_analysis/S11_S12.json`; `HANDOFF_edge_audit.md` §1-8.
- **THE O-SERIES IS CLOSED — 26 OF 26 — AND THE LAST ITEM'S BEST ARM IS A NULL THAT CLEARED
  EVERY BAR BUT ONE (2026-08-12, session 32, `O14`).** `PREREG_o14_tickflow_signals.md` committed
  **ALONE at `ea48f6b`**. Frozen book, **no live code path changed, nothing adopted.**
  * **EVERY OPTIONS IDEA IN THE CATALOGUE HAS NOW BEEN TESTED.** The `O14` ledger row is `DONE`,
    so all 26 O-rows are `DONE` and none is open. The register's own void condition forbade saying
    this before the row flipped, which is why the three previous sessions each had to qualify it.
    **These were the studies the 4.72GB alert-day tick cache was collected FOR**, so its
    justification is now paid.
  * **`sweep_share` IS THE CLOSEST THIS PROGRAMME HAS COME TO A DISCOVERY AND IS STILL A NULL.**
    Full sample LS **−0.1390 at |t| 3.061 against its own permutation p95 of 1.952**, two-sided
    permutation **p 0.00249**, and **the ONLY arm of five to survive Benjamini–Hochberg**. Its sign
    is **stable across halves** (−0.1689, −0.1086) and negative means **high sweep share earns
    MORE** — the institutional-FOLLOW direction. **It is NULL because the LATE half misses its own
    bar, 1.7741 vs 1.9357**, while the early clears at 2.6443 vs 2.1740 — **and the late bar is the
    LOWER of the two, so this is not a bar artefact.** The both-halves rule was fixed before any
    number existed and is the only thing between this and a reported discovery. **The autopsy's
    record was 0 in 126 hypotheses twice; this is 0 in 131.**
  * **NO SIGN COULD BE DECLARED, SO EVERY ARM IS TWO-SIDED — the only options register where that
    is true, and the audit's own argument forces it.** Pan–Poteshman found buyer-initiated
    put/call ratios predict, **on proprietary data with participant identification**; Bryzgalova
    et al. found retail is **>60% of options volume and LOSES money**, making signed retail flow a
    **fade** candidate; **public tick data cannot separate the two populations.** Two-sided costs
    power and that is the honest price. A **sign-agreement clause between halves** does the work a
    declared sign would.
  * **THE OTHER FOUR ARMS ARE NOWHERE**: `signed_volume` +0.0324 at 0.658, `pc_flow_imbalance`
    −0.0106 at **0.256 — the smallest of the five**, refuting my own prediction that it would be
    the largest — `block_share` −0.0212 at 0.437, `unusual_volume` +0.0771 at 1.511, none clearing
    its p95 or BH.
  * **A DAILY CROSS-SECTION IS IMPOSSIBLE, so the sort is MONTHLY**: per date median 2 names, max
    17, **ZERO dates reach 20**; per month median 31, 89 of 118 months reach 20. The same
    structural fact that redirected O3/O4/O5 and O25.
  * **THE LOOK-AHEAD CONTROL REPRODUCES AN INDEPENDENT MEASUREMENT EXACTLY**: `entry_premium`
    against the **traded contract's** last prevailing ask reads **0.0233 over 3,827 rows — the same
    0.0233 session 26 measured with a different implementation.** Lee–Ready classified a median
    **98.54%** of eligible prints.
  * **THE ONE LEDGER ROW A HUMAN WROTE IS THE ONE THAT WAS RIGHT.** Six `src=auto` rows in this
    series claimed no audit section existed and **all six were wrong**; `O14`'s `src=human` row
    named precisely the gap this register closed.
  * **THREE DEFECTS IN MY OWN INSTRUMENT, all caught before any verdict.** `classify_side`
    **contradicted its own docstring** (Lee–Ready's tick test needs the previous *different* price;
    the first cut carried the immediately preceding one, leaving runs of identical mid-prints
    unclassified) — caught by the test written to pin it. **The look-ahead control first measured
    the wrong instrument entirely**, reading a meaningless 1.5746. Plus dead code. A 4.4× speedup
    was verified **inert** on bit-identical feature values.
  * **Options `N` 280 → 285**, one per arm. Expectations **4 right, 2 wrong**.
    `data/free_analysis/O14_TICKFLOW_SIGNALS.json`; `HANDOFF_optionsbot.md` §50-53.
- **A BOOK WITH POSITIVE PER-TRADE EXPECTANCY LOSES MONEY AT REALISTIC SIZING, AND THE REASON IS
  MEASURED: THE EDGE LIVES IN THE CROWDED WEEKS AND A CONCURRENCY CAP REFUSES EXACTLY THOSE
  (2026-08-12, session 31, `O11`+`O19`+`O22`+`O25`).** `PREREG_o11_o19_o22_o25_portfolio.md`
  committed **ALONE at `1203a85`**. Frozen book, **no live code path changed, nothing adopted.**
  * **THE O-SERIES IS NOT CLOSED, AND THE WORDING WAS FIXED BEFORE ANY RESULT EXISTED.** After this
    batch **25 of 26 O-rows are DONE**; **`O14` remains OPEN** — its collection is complete and its
    first analysis landed, but the **put/call and unusual-volume studies the tick cache was
    justified by are still untested.** The accurate sentence is *"this closes the last four OPEN
    audit HYPOTHESIS rows"*, not *"the O-series is closed"*.
  * **`O11`: THREE OF FOUR CELLS UNSURVIVABLE, THE FOURTH MARGINAL, NONE SURVIVABLE.** Max drawdown
    (full): $50k/conc10 **0.6710**, $50k/conc50 **0.7769**, $250k/conc10 0.3589, $250k/conc50
    0.5842. **THE HEADLINE CONFIRMS THE AUDIT'S OWN HYPOTHESIS: a book with +3.27%/trade POSITIVE
    expectancy ENDS AT $37,059 FROM $50,000 — a −25.9% total return — at a concurrency cap of 10.**
    *Per-trade expectancy and survivability are different questions and only the first had ever
    been measured here.*
  * **THE MECHANISM, MEASURED AND THE MOST PORTABLE THING IN THE BATCH: ALERTS CLUSTER AND THE EDGE
    LIVES IN THE CROWD.** Over 483 weeks (median 7 alerts, max 38), expectancy is **−4.51% in quiet
    weeks** and **+14.28% in weeks above the 90th percentile**, with **51.5% of trades in weeks of
    >10 alerts.** So a concurrency cap refuses trades **exactly when opportunity is richest** —
    1,677 of 3,870 skipped at cap 10 — which is why the constrained small book is loss-making
    rather than merely volatile. This is the audit's own third possibility, confirmed.
  * **`O19` NOT-AN-ARTEFACT, and it RAN FIRST BY MECHANISM: the O11 stage REFUSES to run without
    O19's artifact** and embeds its verdict — demonstrated by invoking it with the artifact absent.
    This repairs session 26's defect, where a gating control and its outcomes ran in one pass.
    Equal +3.270%, contract-weighted +3.407%, dollar-weighted +3.141% — same sign, 0.27pp apart;
    premium floors move expectancy by 0.10pp. **The audit's premise barely applies here: the median
    position is THREE contracts, not twenty, because median premium is $2.57.**
  * **`O22` CAPACITY ≈ $76.6M ON THE REGISTERED MEASURE — AND IT MAY NOT BE COMPARED WITH P1's
    EQUITY $23M, FOR A MEASURED REASON: OPEN INTEREST IS A STOCK, ADV IS A FLOW.** The traded
    contract's daily volume is a median **0.1326** of its open interest (179 traded vs 1,373
    outstanding), so an OI-based capacity **overstates a flow-based one by ~7.5×** — flow-equivalent
    near **$10M**. **The registered headline stands as measured** (swapping the depth measure after
    reading the number is what the void conditions forbid) and the correction is reported beside it.
    Upper bound, λ is an assumption, and **mechanical rather than a recommendation** given R2.
  * **`O25` NULL ON BOTH ARMS, AND NOT MARGINALLY — THE WING IS RELIABLY WORSE.** At +75%
    (n 1,332) **−9.34pp vs closing and −9.69pp vs holding**; at +100% (n 1,082) **−13.03pp and
    −7.76pp** — negative in **both halves against both comparators, every CI excluding zero.**
    **The audit's own prediction is confirmed:** sd falls 0.823 → 0.707 and the share above +100%
    falls **74.2% → 56.6%**. Free by-product, no verdict: at +100% **closing BEATS holding by
    5.3pp**.
  * **THE SPLIT GUARD IS NOW SHARED AND RAISES**, as instructed after session 30's recurrence:
    `portfolio_capacity.assert_raw_spot` runs before any instrument touches a price, **raises
    rather than warns, and also raises when it can check nothing** (an empty overlap reporting
    success is the same failure in a new costume). It read **3,870 entries at median relative error
    0.00e+00**; six tests pin it and downgrading it is a void condition.
  * **THE LEDGER WAS WRONG ABOUT ALL FOUR ROWS — the third session running.** All four were
    `src=auto` / *"no mention anywhere in the corpus"*; the audit has full sections at `:1066`,
    `:1985`, `:2023`, `:2061`. **That note is not evidence of absence.** All four corrected.
  * **Options `N` 271 → 280** (2+4+1+2, exactly as pre-committed); equity and infra untouched by
    this item. Expectations **4 right, 2 wrong, 2 split**.
    `data/free_analysis/O11_O19_O22_O25_PORTFOLIO.json`, `O19_SIZING_ARTEFACT.json`;
    `HANDOFF_optionsbot.md` §46-49.
- **13F STALENESS IS COMMON ACROSS NAMES, NOT CROSS-SECTIONAL — SO DECAYING IT CANNOT RE-RANK
  ANYTHING — AND THE FRESHNESS GRADIENT THE WHOLE ITEM RESTS ON IS ABSENT
  (2026-08-12, session 33, `S8`+`S9`).** One register for both,
  `PREREG_s8_s9_freshness.md`, committed **alone at `b7804d8`**. **ADOPTS NOTHING.**
  * **THE STRUCTURAL FINDING, AND IT KILLS S8's 13F LEG OUTRIGHT: `days_since_13f` takes a mean of
    1.25 DISTINCT VALUES PER DATE** (median within-date sd **2.054 days**), because 13F
    quarter-ends are **common calendar dates** — at any rebalance every name's 13F is the same
    age. Its decay multiplier spans p05 **0.5163** to p95 **0.5427** with a **within-date sd of
    0.00587**, so the arm is not a staleness adjustment at all but a **uniform ~0.54×
    down-weighting of `institutional`** — a weight change, and the weighting family was rejected
    wholesale last session. Its rank correlation is **0.9880**, nearly inert.
  * **THE AUDIT'S PREMISE CONFLATES TWO DECAYS.** The 13F signal genuinely decays as the quarter
    ages — that is measured and real (alive Q−2 at *t* 1.36, dead Q−3 at −0.04) — but that is a
    **TIME-SERIES** decay common to every name, **not a CROSS-SECTIONAL one that could re-rank
    them.** By contrast `days_since_filing` takes **86.81 distinct values per date** (within-date
    sd ≈ 39 days), so the fundamental arm is a genuine cross-sectional variable.
  * **THE S9 DIAGNOSTIC IS THE RESULT, AND IT REFUTES THE PREMISE.** Top-decile forward return by
    filing-age quartile: **Q1 +6.15%@38d, Q2 +6.12%@66d, Q3 +6.66%@71d, Q4 +6.35%@88d.** **Not
    monotone**, whole spread ~half a point on a 6.3% base, and **Q1−Q4 = −0.78%/yr — the STALEST
    quartile very slightly outperformed the freshest.**
  * **MY REGISTERED LEAN WAS WRONG, IN THE INFORMATIVE DIRECTION.** The register was asked to
    state a lean and did: **the gradient is real, the weighted arms fail.** The weighted arms did
    fail — **but the gradient is not there either**, so both halves of the lean pointed at
    something in freshness and there is nothing.
  * **VERDICTS: all four REJECTED.** A2 freshness-as-input +0.61pp/−1.61pp; **A3 fundamental decay
    (90d) NOT_REPLICATED — late half alone at +1.73pp, Δ*t* +0.710, early −0.22pp**; A4 13F decay
    +0.03pp/−1.03pp; A5 combined −0.16pp/+0.41pp, landing **between A3 and A4 exactly as
    pre-registered**. A3 is **the THIRD CONSECUTIVE SESSION in which exactly one arm clears
    exactly one half** — the family-wise clause has now earned its keep three times. **1 of 4
    siblings, not eligible, not adopted.**
  * **C6 CONFIRMS THE PRE-REGISTERED CAVEAT: the freshness quartiles differ materially by
    sector**, largest fresh-vs-stale gap **Consumer Cyclical at 15.62pp** — fiscal year-ends
    cluster by industry, so any gradient would have been partly compositional (U7's failure mode,
    and S10's). Moot here since there is no gradient, but it binds on any re-opening.
  * **NO HALF-LIFE WAS FITTED** — 90d for fundamentals (a labelled convention), 180d for 13F from
    the project's own measured decay. Fitting on this panel then scoring on it is the in-sample
    selection already paid for (+8.43%/yr in-search → −0.04%/yr locked hold-out). **C5: zero
    negative ages**, which would have been look-ahead; **C7: the fundamental decay bites hard**
    (mean multiplier 0.4894), so A3's failure is not an inert-multiplier artefact.
  * **A DEFECT REPORTED, NOT FIXED: `bulk.prepare_daily` down-samples DAILY to ONE ROW PER
    TICKER-MONTH**, so the point-in-time market cap and the re-priced EV equity leg can be **up to
    31 days stale** while the price feeding `_price_factors` is same-day. Its docstring keeps the
    last date actually present and never a future one, so this is a **precision** defect, not a
    correctness one — and fixing it moves `size`, every EV-based ratio and the published headline,
    which needs its own register.
  * **TWO ARGUMENTS THAT LOOK SUPPORTIVE AND ARE NOT THE SAME HYPOTHESIS, separated in the
    register before running:** P6's *"recency beats smoothing"* (quarterly ROE beat TTM) is about
    the **WINDOW** a number is measured over, not the **AGE** of the observation — a quarterly
    figure filed 89 days ago is still quarterly; and **S27**, rejected last session, weighted
    **dates**, while these weight **names within a date**. **Equity `N` 176 → 180.** Expectations
    **6 right, 1 wrong**. `data/free_analysis/S8_S9_FRESHNESS.json`;
    `HANDOFF_edge_audit.md` §1-7.
- **THE SPLIT-ADJUSTED-SPOT DEFECT (U1-SPLIT'S CLASS) RECURRED IN A NEW INSTRUMENT AND WAS CAUGHT
  ONLY BY DISBELIEVING A NUMBER — READ THIS BEFORE MATCHING ANY STRIKE AGAINST A PRICE
  (2026-08-12, session 30, `O6`+`O7`+`O17`).** All ten arms NULL; two failed on exactly one
  pre-committed leg. `PREREG_o6_o7_o17_earnings_surface.md` committed **ALONE at `779d42c`**.
  Frozen book, **no live code path changed, nothing adopted.**
  * **THE DEFECT, AND IT IS THE MOST TRANSFERABLE THING HERE. Option chains are as-traded and
    UNADJUSTED; `data/bulk/prepared/bars`'s `close` is split- AND dividend-adjusted — NVDA in 2012
    reads 0.27 against a raw 11.97, a 43× ratio.** Matching an as-traded strike against an adjusted
    spot picks a contract nowhere near the money and **fails SILENTLY** — the option still prices,
    it is simply mostly intrinsic. **Measured against the book's own `underlying_entry` on 1,173
    banked entries: `raw_close` agrees EXACTLY (median rel err 0.00000, nothing >5% off) while
    `close` is off by a median 10.3% and by >5% on 67% of entries.** **RULE: `raw_close` for
    anything touching a STRIKE, `close` only for a RETURN.** My first cut reported a mean implied
    move of **19.57%** against a realised 5.26% and a confident RICH verdict — an **artefact**
    (2.82% of events >20% from the money, up to 30×). Repaired, coverage rose 0.2738 → 0.4459 and
    the implied move fell to a credible **5.45%**. **Anything else in this project matching a
    strike against `close` is suspect.** Pinned by three tests; a control that must stay empty
    reads ZERO.
  * **THE LEDGER WAS WRONG ABOUT TWO OF THE THREE ROWS**, both `src=auto`: O6 read *"prose mentions
    only, no section"* and O17 *"no mention anywhere in the corpus"*, yet `VALQUO_EDGE_AUDIT.md:964`
    and `:1150` are full sections naming four rules each. **Definitions were QUOTED, not invented.**
  * **`O6` ALL FOUR NULL, AND THE STRONGEST NUMBER IS THE CONTROL: the random-alternative-contract
    p95 is about −11.3pp/trade, so the mechanical 35-delta rule the audit wanted replaced ALREADY
    BEATS ARBITRARY IN-BAND SELECTION BY ~11 POINTS.** Gains: A1 lowest-IV **+0.074pp**, A2 IV-rank
    **−3.505pp**, A3 smile-residual **−11.099pp**, A4 vega/spread **+0.464pp**. **A3 is the audit's
    OWN headline suggestion (ORATS smoothed market value) and is the worst arm in the register.**
    **A4 is the near miss** — positive in both halves, clears both p95s, **NULL only on the audit's
    tail-concentration clause.**
  * **WHY THEY FAIL, AND IT INVALIDATES THE AUDIT'S FRAMING: the cheapness rules CHANGE THE DELTA
    rather than repricing a fixed trade.** Mean |delta gap| 0.004 / 0.248 / **0.310** / 0.125, A3
    drifting 0.374 → **0.458**. The audit claims this *"cleanly separates which NAME from which
    CONTRACT"*; on this candidate set **it cannot** — a cheapness criterion moves the exposure too.
    **A1's 0.004 gap means it is essentially the incumbent, so its null is near-tautological.**
  * **PORTABLE, from the zero-cost random-entry control arm: the same four rules reproduce the same
    ordering and magnitudes on the CONTROL book** (+0.057, −4.140, −9.382, +0.310pp over 5,984
    events). **This is contract selection generally, not the dead alert days** — so it carries to
    any future book.
  * **`O7`: EARNINGS OPTIONS ARE *RICH* ON THIS UNIVERSE, CONTRADICTING GAO–XING–ZHANG'S PUBLISHED
    SIGN.** Implied move **5.4512%** vs realised **4.7773%**, difference **−0.6739pp** (CI95
    [−0.8475, −0.5070], excludes zero); realised exceeds implied on only **35.07%** of events.
    Stated as universe-specific, not a refutation — their effect is strongest in **small** firms
    and this book has none. **The backtest is dead: −10.34% per straddle net of four crossings,
    negative in both halves.** A **declared deviation**: B2's registered non-announcement null was
    NOT computed, because it fails positivity in both halves and no null could change the
    conjunction.
  * **`O17`: AVOIDING EARNINGS GETS MONOTONICALLY WORSE** (+0.797 → −0.479 → −1.429pp at 5/10/15
    days, none clearing its null) — **the loser autopsy's IV-crush hypothesis is not merely
    unsupported, the data points the other way.** **C4 OWN-THE-EVENT fails on ONE leg only: gain
    +4.686pp/trade, POSITIVE IN BOTH HALVES (+5.748, +3.730) and CLEARING ITS NULL IN BOTH (+3.241,
    +2.941) — NULL solely because retention is 0.5706 against the pre-committed 0.70 floor.** The
    floor was fixed first and is **reported, not relaxed to fit**.
  * **THE CONFOUND THAT SHOULD HAVE KILLED C4 IS REFUTED BY MEASUREMENT.** Owning the event selects
    longer-dated contracts and O13 found expectancy climbs with tenor, so C4 could have been a
    **DTE filter wearing an earnings filter's name** (U7/S10's mode). It is not: DTE 60.0 kept vs
    56.4 refused, and **within every DTE quartile the gain stays positive** (+6.416, +6.310, +2.138,
    +2.711pp). Tenor independently reconfirms O13 (+0.376, −0.877, +6.736, +8.584pp by quartile).
  * **EARNINGS COVERAGE IS BETTER THAN `bulk.py` SAYS AND ITS HOLE IS SYSTEMATIC.** That file warns
    ~2.83 code-22 dates per ticker-year; on these megacaps it is **median 3.96 / mean 4.14**. But
    **29 of 186 names have ZERO coverage (388 trades, 10.0%) and EVERY ONE is a foreign private
    issuer** filing 20-F/6-K. **A filter reading "no date" as "no announcement" FAILS OPEN on a
    non-random tenth of the book** — the mode this lane refused once before. `refuse_within` returns
    **`None` for UNKNOWN** and callers must drop; four tests pin it.
  * **Options `N` 261 → 271** (4+2+4, exactly as pre-committed); **equity untouched BY THIS ITEM,
    though it reads 176 after the merge** (other lanes landed 15 equity trials the same day) —
    **re-read `by_domain` after merging rather than quoting a figure measured mid-session.**
    Expectations **6 right, 1 wrong**. `data/free_analysis/O6_O7_O17_EARNINGS.json`;
    `HANDOFF_optionsbot.md` §42-45.
- **EVERY PRE-REGISTERED INTERACTION IS REJECTED, ONE OF THE AUDIT'S FOUR CANNOT BE BUILT AT ALL,
  AND A CROWDING EXCLUSION MAKES DRAWDOWN WORSE — INDEPENDENTLY REPLICATING S10
  (2026-08-12, session 32, `S7`+`S18`).** One register for both,
  `PREREG_s7_s18_interactions.md`, committed **alone at `7fc6ab2`**. No panel rebuild — every
  input was already banked. **ADOPTS NOTHING.**
  * **`size × liquidity` IS NOT BUILDABLE, AND IS REPORTED RATHER THAN PROXIED.** The audit names
    four interactions; this one needs a liquidity measure and **there is none on this path** — the
    price export carries **date and close only**, so `avg_dollar_volume` cannot be computed in the
    panel at all (audit **B13**, whose ledger row was corrected last session to
    `PARTIAL — BLOCKED ON DATA` for this reason). **A market-cap or price stand-in would be a
    different hypothesis wearing this one's name**, and a test pins that no such proxy appeared.
    It charges **no trial**.
  * **SHORT INTEREST DOES NOT REACH HALF THE PANEL, AND THE MEASURED NUMBER IS NOT THE AUDIT'S.**
    The cache is real (48,539 tickers, 3,866,270 records, 2018-01-27 → 2026-07-30) but the audit
    says 40% of dates and it measures **32 of 69, 46.4%**, first covered **2018-04-20**, row
    coverage on covered dates **0.9269**. **Every covered date is in the LATE portion of a panel
    starting 2009-01-15, so S18 CANNOT satisfy a both-halves gate on the full panel** — an
    impossibility, not a power caveat. The register fixed the replacement first: S18's arms are
    gated on halves of the **covered subsample — 32 dates, 16 per half**, which is exactly
    `min_dates=16`, the thinnest split the shipped gate accepts. **A pass on 16-date halves is not
    the same object as a pass on 34-date halves.**
  * **ALL SIX TESTABLE ARMS REJECTED.** `value × quality` −1.17pp/−0.84pp; `momentum × vol
    regime` −0.48pp/−0.19pp; `value × institutional` −0.05pp/−1.09pp (coverage 0.7172, the
    handicap pre-registered); `value × short_interest` −0.49pp/−0.86pp. **`momentum ×
    short_interest` is NOT_REPLICATED — it clears the LATE half alone (+1.85pp, Δ*t* +0.812) and
    fails the early (−2.39pp).** That is **the second consecutive session in which exactly one arm
    clears exactly one half**, so the family-wise labelling clause has now earned its keep twice:
    **1 of 6 sibling arms, not eligible, not adopted.**
  * **THE EXCLUSION ARM INDEPENDENTLY REPLICATES S10 ON A DIFFERENT CRITERION.** Dropping the top
    5% most-shorted removed 4.83% of top-decile rows and moved return +27.08% → +26.77%
    (−0.31pp), while **max drawdown went −0.2809 → −0.2863 — a gain of −0.5404pp, i.e. WORSE.**
    S10 found a *valuation-band* screen worsened drawdown by 2.61pp and 3.35pp; a *crowding*
    screen worsens it too, same direction, smaller size. S10's caveats travel verbatim:
    `max_drawdown` is **negative** so the gain is `arm − base` (pinned by a test carrying the real
    measured pair), and **X7 calibrates no drawdown floor**, so this is a measurement carrying no
    verdict.
  * **THE AUDIT'S BONFERRONI PRESCRIPTION WAS DECLINED EXPLICITLY, WITH THE REASON REGISTERED
    FIRST.** It asks for *p* < 0.0125; **this project's gate is a MARGIN gate whose floors X7
    calibrated against a placebo**, and translating one into the other would invent an
    uncalibrated correspondence — the error X3 and session 10 both paid for. Multiplicity is
    honoured by **labelling** instead.
  * **CONTROL C7 IS THE CLEAN SURPRISE.** Adding an eighth input moves every theme's *relative*
    weight 1/7 → 1/8, so each arm is a **compound** change — registered in advance. Re-scoring
    with a **constant** eighth column isolates it: **+0.000173 and +0.000146 of alpha, essentially
    nil.** So the arms measure the interactions and nothing else. **This refutes the one
    expectation that missed** (I predicted the dilution would matter, 65/35).
  * **C5 zero point-in-time violations; C6 no interaction is a proxy for a parent** (largest
    |parent correlation| 0.4584). **Equity `N` 170 → 176.** Expectations **6 right, 1 wrong**.
    **Nothing was searched beyond the audit's named list** — searching the quadratic space is
    exactly what the tree combiner already did, and it *reversed* out of sample.
    `data/free_analysis/S7_S18_INTERACTIONS.json`; `HANDOFF_edge_audit.md` §1-6.
- **FIVE ALTERNATIVE WEIGHTING SCHEMES, ALL FIVE REJECTED — AND CPCV'S OWN BEST CHALLENGER MISSES
  ITS BAR BY A FACTOR OF SEVENTY-NINE (2026-08-12, session 31, `S5`+`S6`+`S13`+`S24`+`S27`).**
  ONE register for all five, `PREREG_s5_s6_s13_s24_s27_weighting.md`, committed **alone at
  `8b0917e`**. One panel build, six scorings on one frame. **ADOPTS NOTHING.**
  * **THE NUMBER TO REMEMBER, because it prices the whole family: CPCV's best challenger scheme
    (`positive-equal`) beat the deployed default by a margin of `0.000265` against a required bar
    of `0.020830` — it would have to be about 79× LARGER to clear.** `adopt=false`, PBO **0.80**.
    Weight tuning on this panel is not marginal; it is nowhere near.
  * **THREE OF THE FIVE PROPOSE BEHAVIOUR ALREADY SHIPPED, IN WHOLE OR IN PART** — all five rows
    were `src=auto`, and this is the S21 pattern for the third time. **`S27` is already shipped at
    the audit's own middle half-life**: `_theme_ic_stats` computes `0.5 ** (days_ago/halflife)`
    and **`halflife_days=1260` (≈5y) is the default of `_weighted_optimize`, `walk_forward` AND
    `cpcv_validate`**, while the audit proposes 3, 5 and 10. **`S5`'s shrinkage is half-shipped**
    as `ic-shrunk-50` (fixed 50% toward equal weight), already CPCV-rejected. **`S13`'s
    inverse-vol is shipped at the WRONG LEVEL** — `risk-parity` is inverse-vol across *themes*;
    S13 asks for it across *names*, a different object.
  * **VERDICTS.** `S5` REJECTED (−2.12pp / −1.68pp, rank corr 0.8933, shrinkage intensity
    **0.5641** so genuinely partial and not degenerate at either end). `S24` REJECTED and **very
    nearly the incumbent at rank corr 0.9907** — bagging a seven-signal set has almost nothing to
    bag. `S27` REJECTED at **both** half-lives by the widest margins of the five (−4.29pp / −2.98pp
    at 3y; −4.21pp / −2.66pp at 10y).
  * **`S6` IS THE ONLY ARM TO CLEAR ANY HALF, AND IT GETS THE FULL SKEPTICAL TREATMENT THE
    REGISTER FIXED IN ADVANCE.** Late half **+3.30pp at Δ*t* +0.678 — improves**; early half
    **−1.61pp at Δ*t* −1.289 — does not.** That is a sign flip between halves, this project's most
    repeated pattern, **and it is 1 OF 5 SIBLING ARMS**: five arms against one bar make
    at-least-one-clears roughly a **23%** event under independence. **NOT eligible, NOT adopted,
    and the +3.30pp may not be quoted without both labels.**
  * **`S13` FAILS THE ALPHA GATE WHILE IMPROVING EXACTLY WHAT IT EXISTS TO IMPROVE, AND THAT WAS
    REGISTERED AS AN INSTRUMENT MISMATCH RATHER THAN DISCOVERED.** Equal weight **+25.29%/yr,
    Sharpe 0.5866, maxDD −0.2809**; inverse-vol capped **+23.53%/yr, Sharpe 0.6261, maxDD
    −0.2804**. **Sharpe +0.0395 (≈6.7% relative), return −1.76pp, drawdown flat.** Its long-short
    leg is unchanged **by construction**, so its *t* margin is **N/A and may never be read as a
    pass**. X7 calibrates no floor for Sharpe, drawdown or turnover, so those carry no verdict.
    The drawdown barely moving is consistent with S10's finding that this book's maxDD is decided
    by one quarter (COVID 2020Q1).
  * **EXPECTATIONS SCORED 6 RIGHT, 0 WRONG — the first clean sweep in this record, and the reason
    matters more than the score.** The prior was not intuition; it was the project's own measured
    standing result — CPCV adopts nothing, the tree combiner **REVERSED** out of sample, and
    weight tuning went **+8.43%/yr in-search → −0.04%/yr on the locked hold-out**. **When the
    prior is a measurement, the calls stop being wrong.**
  * **A DEFECT IN MY OWN INSTRUMENT, resolved under the session-11 protocol.** The register's C5
    defines the reported intensity as the **shrinkage** intensity; the first cut of the code
    reported its **complement**, so the register's two degenerate ends read backwards against the
    implementation. Caught by the test written to pin it, before any verdict was read. **Proven
    presentational by diffing the pre-fix and post-fix artifacts leaf by leaf: the S5 weight
    vector is BIT-IDENTICAL (max |Δ| 0.000e+00) and ZERO gate cells moved on any arm in either
    half**, so no conclusion needed re-deriving. The register is left unedited; the code now
    matches it.
  * **A LIMITATION OF THE DESIGN AGAINST ITS OWN REGISTER, REPORTED NOT GLOSSED.** The register
    says CPCV is the authority "for every arm that produces a weight vector". **`cpcv_validate`
    selects among its OWN eight `_weight_schemes` and cannot evaluate an arbitrary vector**, so it
    does not bless or decline S5/S6/S27 individually; its authority operates here as a blanket
    keep-the-defaults rule, which is weaker than the register's wording implies.
  * **Equity `N` 165 → 170**, one trial per item. `data/free_analysis/S5_S6_S13_S24_S27.json`;
    `HANDOFF_edge_audit.md` §1-7.
- **SPLITTING NET ISSUANCE INTO TWO INPUTS CANNOT CHANGE AN ORDERING — IT IS A RANK IDENTITY,
  NOT A MEASUREMENT — AND BUYBACKS CARRY MORE OF THE THEME'S IC THAN DILUTION DOES
  (2026-08-12, session 30, `S16`).** `PREREG_s16_issuance_decomposition.md` committed **alone at
  `afc7578`**, a strict ancestor of the measurement commit. One panel build, five scorings, every
  arm a column on ONE frame. **ALL FOUR ARMS REJECTED. ADOPTS NOTHING.**
  * **THE PREMISE CHECK REMOVED HALF THE AUDIT'S METHOD BEFORE ANY ARM RAN.** All 671,417 ACTIONS
    rows carry one of nineteen action types and **NONE is a repurchase authorisation**, so
    buyback-announcement drift is **not testable on data we own**; and **`initiated` is
    index/security listing initiation** (its earliest rows are `^VIX`, `^RUT`, `^IXIC`, all
    1997-12-31), **not dividend initiation**. What IS there is `acquisitionof`/`acquisitionby` —
    8,248 dated rows each with deal values — which is the M&A leg. Same class as S25.
  * **THE DEEPEST FINDING IS AN IDENTITY, AND IT KILLS THE AUDIT'S ACTUAL PROPOSAL.** S16C's
    within-date rank correlation against the incumbent is **1.000000000000 on all 69 dates**,
    because `buyback = max(0, −net)` and `−dilution = −max(0, net)` are **both non-increasing in
    `net`** (verified directly on the real series), so the mean of their z-scores preserves the
    ordering of `neg_issuance = −net` **exactly**. **So "separate them into two inputs so the
    composite can weight them independently" cannot express any ordering the single input cannot
    — it only shrinks the theme's per-date dispersion 1.000315 → 0.774730, a 22.5% cut in
    effective weight.** The S20/S21 rank-invariance lesson in a new costume.
  * **BUYBACK CARRIES MORE OF THE IC THAN DILUTION, WHICH REFUTES TWO PRE-REGISTERED
    EXPECTATIONS.** Theme IC *t*: **S16A buyback-only +3.2066**, incumbent **+2.7530**, **S16B
    dilution-only +2.5623**. **S16A is the ONLY arm clearing X7's calibrated 2.71 theme-IC bar —
    and it still fails the gate**, which is the **fifth** demonstration that theme IC does not
    judge a construction change.
  * **VERDICTS: all four REJECTED** against the already-committed margins — S16A Δalpha
    +0.47pp / +0.05pp; S16B +0.23pp / −0.26pp; S16C +0.20pp / −0.06pp; S16D +0.17pp / −0.19pp.
    **S16D is FLAGGED DEGENERATE** by the pre-committed C6 rule (`mna_dilution` non-zero on only
    **3.19%** of rows) even though C7's own bar passed — the M&A flag fires on **5.53%** of
    dilution rows, inside the pre-registered 5–25% band.
  * **C3 DID NOT PASS ITS BAR AND IS REPORTED AS A FAILURE, NOT RECLASSIFIED.** The rebuilt
    incumbent differs from the shipped `capital_discipline` by up to **0.006676** (0.67% of one
    sd), because `build_frame` standardises over every scored name that date while the panel then
    drops names with no forward return. **Diagnosed, not asserted** — within-date rank correlation
    exactly **1.00000000**, median deviation exactly **0.000e+00**, a per-date affine rescaling
    with worst residual 1.0e-03 — **and bounded: re-running every gate against the SHIPPED column
    as baseline returns the same four rejects with deltas identical to four decimals.**
  * **ADOPTION WOULD COST MORE HERE THAN USUAL AND THE REGISTER SAID SO FIRST.** The current
    vintage is **DERIVED** per `PT-GAPDUE` — **vintage 3, opened 2026-08-11 — and its recorded
    reason IS the `capital_discipline` restoration.** So changing this theme's construction would
    close a vintage days old and open vintage 4, a second five-year clock reset on the same theme.
  * **Equity `N` 161 → 165**; options 258 untouched. Expectations **3 right, 3 wrong**. **NOT
    tested and named so it is not mistaken for tested:** buyback-announcement drift (no such data)
    and dividend-initiation drift (derivable, different signal, out of scope).
    `data/free_analysis/S16_ISSUANCE.json`; `HANDOFF_edge_audit.md` §2.
- **THE HEADLINE ALPHA IS NEGATIVE IN 29% OF QUARTERS, AND THE RESULTS FILE NOW SAYS SO
  (2026-08-12, session 30, `S28`).** Reporting infrastructure — **no hypothesis, no threshold, no
  verdict, and no published claim moves.** `statistics.distribution()` ships n, mean, sd,
  min/p05/p25/median/p75/p95/max, the count and fraction of **negative** periods, and the **dated**
  worst and best period, wired into four payload blocks (`construction.top_decile_alpha_
  distribution`, `construction.long_short_distribution`, `portfolio.return_distribution`,
  `portfolio.excess_vs_equal_weight_distribution`). `SCHEMA_VERSION` **5 → 6**, purely additive.
  * **WHAT IT SHOWS ON THE SHIPPED BOOK, which is why it was worth doing.** The published
    **+7.17%/yr** top-decile alpha is the mean of 69 quarterly draws of which **TWENTY ARE
    NEGATIVE (28.99%)**, with a **worst quarter of −6.83% (2016-01-20)** and a best of +11.47%
    (2022-07-22) — and a **median of +1.41% against a mean of +1.79%**, so the headline is
    **right-skewed and the typical quarter is worse than the average one**. The long-short spread
    is negative in **33.3%** of quarters, worst **−20.01% (2025-07-29)**.
  * **THE UNITS TRAVEL IN THE BLOCK, because the obvious misuse is annualising a quantile.**
    `top_decile_alpha` is periods-per-year × the **mean**; that scaling is a statement about a
    mean and **never about an order statistic**.
  * **CONSISTENCY IS ASSERTED, NOT ASSUMED: 4 × the distribution's mean reproduces
    `top_decile_alpha` to 4e-17** on the real panel and exactly on a synthetic one — the check
    that the block describes the SAME series the headline is a mean of. A distribution attached
    to the wrong series would look reasonable and quietly mislabel the worst quarter in the record.
  * **PINNED AS REPORTING-ONLY** by a test that fails if any threshold, gate or verdict ever
    compares or branches on a distribution field — **and that guard was checked for vacuity**: it
    inspects 14 code-level references, so it is not passing by seeing nothing. **Zero equity
    trials**; infra `N` 10 → 11 on the M2/M6 precedent, and infra `N` gates no published claim.
- **THE SURFACE-ANOMALY FAMILY IS NULL ON ALL THREE ARMS — AND THE PRIOR LANE'S ONE SUGGESTIVE
  RESULT REVERSES ITS SIGN ONCE THE INSTRUMENT IS FIXED (2026-08-12, session 29, `O3`+`O4`+`O5`).**
  One register, three arms, `PREREG_o3_o4_o5_surface.md` committed **ALONE at `d2aa5f9`** — one
  `.md`, zero `.py`. Frozen book, no re-mine, **no live code path changed, nothing adopted.**
  * **THIS IS A SECOND LOOK AT AN ALREADY-REJECTED HYPOTHESIS AND IS CHARGED AS ONE.** `64955ef`
    (now on `main`) tested all three characteristics with the published sign declared first and
    **REJECTED** them, and `HANDOFF_free_analysis.md` concluded they *"should be considered
    answered by that same run, not re-opened separately."* **The sole justification for re-opening
    is a deviation that lane declared itself and never closed:** it used a **straddle**, which is
    delta-neutral **only at inception**. This register changes the **INSTRUMENT** and nothing else
    that can be held fixed — A1 reuses that lane's own `idio_vol` values and the panel's own strike
    and expiry.
  * **THE POWER ARGUMENT HELD, WHICH IS THE ONLY REASON THE TRIALS WERE WORTH SPENDING: delta-hedged
    return dispersion is sd 0.0303 against the straddle's 0.9055 on the identical events — a 30-fold
    reduction**, and every arm's |t| rose against its straddle counterpart.
  * **ALL THREE NULL, EACH ON TWO INDEPENDENT LEGS.** `idio_vol` n 3,289, monotonicity −0.1717,
    LS *t* 2.5158 vs its **own permutation p95** 2.016; `exp_idio_skew` n 3,154, −0.0380, 1.9143 vs
    1.9229; `vol_of_vol` n 3,318, −0.0690, **2.9703 vs 1.9459 — the largest margin in the register
    and still NULL.** Monotonicity misses the 0.6 bar three- to fifteen-fold in **both halves of
    all three**, and the both-halves *t* leg fails separately — **the two arms that clear
    full-sample fail in OPPOSITE halves** (A1 late 1.1509, A3 early 1.8189). Session 7's LOO
    pattern again. **A2 misses its own bar by 0.0086 of a *t* and is recorded a NULL, not rounded
    into a pass** (`RUN_RULES` A6).
  * **THE FINDING IS THE SIGN REVERSAL, AND IT RETIRES A CLAIM RATHER THAN ADDING ONE.** On the
    straddle `idio_vol` sorted **+0.9 CONTRADICTING** the published sign (LS *t* −1.2142) — that
    lane's single most suggestive result. On the delta-hedged instrument the same characteristic on
    the same panel sorts in the **CONFIRMING** direction (+2.5158). **Both readings are now
    unquotable as settled:** this one is far too weak to clear, and the prior CONTRADICTS reading
    is an artefact of an instrument that lets the underlying's move dominate.
  * **THE INSTRUMENT BEHAVES AS THE LITERATURE SAYS, which is corroboration it is real rather than
    a bug:** mean delta-hedged gain **−0.0072** and **every quintile of every arm negative** — the
    volatility risk premium, reproduced without being targeted. Separately, `idio_vol` is **+0.8444**
    rank-correlated with ATM IV, so A1 is close to a **pure implied-vol sort**.
  * **THE FROZEN CHAINS NAMED IN THE TASK PROVABLY CANNOT DO THIS, MEASURED BEFORE THE REGISTER.**
    The freeze holds a full chain only on **ENTRY** dates: median **1** full-chain name per date,
    max 17, and **0 of 2,498 dates and 0 of 120 month-ends** reach the ~20 a quintile sort needs.
    The panel is the EOD chain cache instead — **a forced substitution, disclosed in §1 rather than
    quietly made.**
  * **A DIAGNOSTIC WITH NO VERDICT, AND BOTH OBVIOUS EXPLANATIONS ARE REFUTED: Q5 is the WORST
    bucket in ALL THREE arms while Q1–Q4 are unordered** — exactly how a significant long-short
    coexists with near-zero monotonicity. It is **not one effect three times** (`idio_vol` vs
    `vol_of_vol` rank-correlate **−0.2920**, Q5 overlap **14.0%**) and **not illiquidity** (the
    gradient runs in **opposite** directions — `idio_vol`'s Q5 is the most liquid corner,
    `vol_of_vol`'s the least). **Left OPEN for its own register; testing it here would be the fourth
    arm my own void condition 3 forbids.**
  * **A DEFECT OUTSIDE THIS LANE: in the prior lane's `panel.pkl`, `illiq` and `spread_pct` are THE
    SAME COLUMN, identical on all 3,373 rows.** Its `illiq` was **the only characteristic in that
    published run with |t| > 2 (2.46)** and is described as a mechanical liquidity control; it is
    the option's quoted spread percentage under a second name. **Reported, not repaired.**
  * **Options `N` 258 → 261** (one per arm, exactly as pre-committed); **equity untouched BY THIS
    ROW, though it now reads 161** — the `S3` lane landed three equity trials the same day, which
    is why an equity figure must be re-read after every merge rather than quoted from a session's
    own measurement. `BACKTEST_RESULTS.json` needs no re-run **for this item**; the `S3` lane
    already refreshed it at its own denominator. Expectations scored **4 right, 2 wrong** — the misses
    being the sign reversal and the fact that Boyer–Vorkink's **expected** skew is **stronger** than
    the realised version the prior lane used (1.9143 vs 1.5805).
    `data/free_analysis/O3_O4_O5_SURFACE.json`; `HANDOFF_optionsbot.md` §38-41.
- **ALL THREE INSIDER REBUILDS ARE REJECTED, AND THE AUDIT'S OWN THRESHOLD WOULD HAVE REJECTED
  THEM FOR A REASON UNRELATED TO WHAT THE COMPOSITE DID (2026-08-12, session 29, `S3`).**
  `PREREG_s3_insider_rebuild.md` was committed **alone at `b3a85fa`** — one `.md`, zero `.py`, a
  strict ancestor of the measurement commit. One panel build, four scorings, all arms columns on
  ONE frame so the row set is identical by construction. **ADOPTS NOTHING.**
  * **REJECTED on all three arms** against the already-committed margins (+0.25 long-short *t*
    AND +100bps top-decile alpha, BOTH halves, boundary embargoed, deployed flat 1/7, no grid):
    **S3A** (drop the `buys` bonus) Δalpha **+0.01pp / +0.79pp**, Δ*t* +0.116 / +0.110;
    **S3B** (scale by market cap) Δalpha **+0.82pp / +0.52pp**, Δ*t* +0.095 / +0.079;
    **S3C** (split into two z-scored inputs) Δalpha **−0.92pp / −1.24pp**, Δ*t* −0.332 / −0.120.
  * **THE UNUSUAL PART IS THE SIGN-STABILITY, AND IT CUTS BOTH WAYS.** Session 7's LOO pattern —
    arms flipping sign between halves — is this file's most repeated finding, recorded five
    times. **Here every arm is sign-stable on both metrics in both halves.** But the gains are
    far below the bar, and **V2G established there is NO CALIBRATED FLOOR for a paired
    within-panel difference**, so *"small but consistent"* is an observation, not a result.
  * **S3B IS THE BEST OF THE THREE, EXACTLY AS THE AUDIT PREDICTED** — the only arm with a
    positive theme IC (**+0.5763**) and the only one positive on alpha in both halves by more
    than a basis point. It is also the most different from the incumbent (within-date rank
    correlation **0.8721** against S3A's 0.9668). **It still does not clear.**
  * **THE AUDIT'S OWN BAR IS REFUTED AS AN INSTRUMENT, AND THE REGISTER DEMOTED IT IN ADVANCE.**
    Its threshold is *"theme IC t clears +1.0"*. **NO ARM CLEARS IT** — not even the two that
    improve alpha in both halves — **and neither does the shipped incumbent, at −0.2259.** So the
    audit's gate rejects all three for a reason unrelated to what the composite did, and +1.0
    sits far below **X7's calibrated 2.71** anyway. **Never judge a construction change by theme
    IC** — P6.3, X3, S20/S21, and now this.
  * **THE MOST INTERESTING NUMBER IS THE AVAILABILITY DIAGNOSTIC, AND IT DOES NOT CONVICT.**
    `insider` is the only theme with a materially non-zero mean (**−0.1031**) at **83.1%**
    coverage, so a name that HAS an insider score takes a small systematic negative tilt a name
    without one does not — S10's data-availability failure mode. Measured: the pure indicator
    *"has an insider score at all"* carries median IC **+0.01345 at t +1.4471**, **NOT separable
    from zero**, so the artefact is **not demonstrated**. Reported because the indicator's |*t*|
    is **LARGER than the insider theme's own (−0.2259)**: the mere presence of filings carries
    more forward-return information than the score's direction does. **Neither is significant;
    the comparison is the point.**
  * **THREE PREMISE FINDINGS, all in the register before any arm ran.** (a) One of the audit's
    own S3 items — `searchsorted(..., "right")` making a same-day Form 4 usable — is **ALREADY
    FIXED by B26** and was not re-tested. (b) **The formula was DUPLICATED** at `:737` and
    `:800`; there is now one `_insider_formula` and both paths delegate, **proved bit-identical
    to both pre-refactor copies over 20,006 cases against git HEAD's own source**. (c) **MY OWN
    OPENING HYPOTHESIS WAS REFUTED BEFORE THE REGISTER WAS WRITTEN** — I expected the non-z-scored
    affine map to leave `insider` under-dispersed and so under-weighted; measured, its per-date
    sd is **0.9600 against 0.8296** averaged over the other six, about **116% of nominal**,
    because the **multi-input** themes are the compressed ones (`quality`, ten inputs, 0.50).
  * **CONTROLS: C1 reproduces the record to sixteen digits and the run ABORTS before reading any
    arm if it does not; C3 the incumbent rebuilt from the banked raw `(net, buys)` is
    bit-identical to the shipped column, max |Δ| 0.000e+00 over 94,660 rows; C6 coverage 0.8308
    IDENTICAL across all four arms**, so S3B's comparison is not partly a universe change.
  * **A DEFECT IN MY OWN FIRST CUT: it used `build_fundamental_panel`'s DEFAULT
    `lookback_years=6` and produced a 21-date / 2,151-name panel** — a **SMOKE TEST**, from which
    the METHODOLOGY RULE forbids a verdict. Re-run at the canonical
    `CONFIG.backtest_lookback_years=18`; the script now **asserts** the shape rather than warning.
  * **Equity `N` 158 → 161**, options 258 and infra 10 untouched. **Adoption would be a VINTAGE
    EVENT** — the current vintage is **DERIVED** per `PT-GAPDUE` (**vintage 3, opened
    2026-08-11**), so it would open vintage 4 — and no arm is eligible in any case. Expectations
    scored **5 right, 2 wrong**. **Zeroing `insider` is NOT re-opened as a fallback conclusion of
    this register**; that needs its own, with its own trial charge.
    `data/free_analysis/S3_INSIDER_REBUILD.json`; `HANDOFF_edge_audit.md` §2.
- **THE POINT-IN-TIME SECTOR MAP IS UNOBTAINABLE FROM ANYTHING WE OWN — AND THE LOOK-AHEAD REACHES
  THE POINT-IN-TIME *VALUATION*, NOT JUST THE REJECTED RANKING (2026-08-12, session 29, `S25`).**
  Closed as **UNOBTAINABLE-WITHOUT-NEW-DATA**. No register and **zero trials**: every finding is a
  fact about what data exists and what the code reads, not a hypothesis tested against a
  threshold (session 8's precedent).
  * **OBTAINABILITY, MEASURED.** The TICKERS snapshot carries six fields — `sector`, `industry`,
    `country`, `exchange`, `category`, `scale` — and **ZERO date fields**, so it cannot say *when*
    a classification took effect and cannot bound reclassification even for names it covers. SF1
    `fundamentals.csv` has **112 columns and no sector or SIC**; `bulk/actions|events|sf3|daily`
    carry none; no prepared cache holds a SIC; and `valuation/data/edgar.py` fetches only
    `company_tickers.json` and companyfacts XBRL, neither of which carries a historical SIC.
  * **THE SOURCE NAMED FOR THE D-SERIES: the EDGAR filing-header `ASSIGNED-SIC`**, which IS the
    classification as of the filing date (~1 fetch per filing, ~180k for this universe). **What
    does NOT work, because it is the obvious first try: `data.sec.gov/submissions/CIK*.json`
    carries only the CURRENT `sic`** — a second snapshot, not a history.
  * **A CONFOUND THAT MUST TRAVEL WITH ANY SUCH BUILD: SIC IS NOT THE SHIPPED TAXONOMY.** The
    panel's sector is an 11-value GICS-like string, so a SIC-derived map changes point-in-timeness
    **and** taxonomy at once and **cannot cleanly measure what reclassification changes**.
    Isolating that needs the SAME taxonomy at two dates — a historical GICS snapshot, not sold as
    history.
  * **THE FINDING THE LEDGER DID NOT HAVE.** The row said *"nothing currently rests on it because
    every sector result has rejected"* — true of the RANKING, **false of the VALUATION**.
    `calibration.py:523-527` passes **today's** TICKERS sector into `pit_company` for a 1998 or
    2009 valuation, where it selects `assumptions.SECTOR_TARGET_MARGIN` (**0.100 → 0.270, a 2.70×
    spread**) and `comps.SECTOR_MULTIPLES` (**PE 2.50×, EV/Sales 6.15×**). **S23's own code pins
    BETA point-in-time two lines below while passing today's sector straight through**, so S23's
    exit-rule arms and **S10's bull-case band** both inherit it. **Not repaired — there is no data
    to repair it with — but pinned by test so it cannot rot.**
  * **CONSEQUENCE: full sector-neutral ranking stays permanently closed.** `SECTOR-NEUTRAL-B6`
    named `S25` as one of only two routes back; that route is **shut until the D-series delivers
    the EDGAR map**. `S15` (sector-relative on the value theme alone) is untouched and remains the
    other. Nothing here affects the accepted `max_sector_w` cap. **A correction against my own
    probe: its first cut reported a date-like field on the snapshot — the regex alternation
    contained `to`, which matched "sec*to*r". There is none.** `HANDOFF_edge_audit.md` §1.
- **THE FORWARD TRACK'S RECORDING GUARD DEMANDED A ROW NOBODY COULD HAVE WRITTEN YET, SO
  `recording_ok` READ FALSE EVERY WEEKDAY MORNING — AND THE ONE READING THIS SESSION EXISTED TO
  TAKE RETURNS `None`, NOT A VERDICT (2026-08-12, session 28, `PT-GAPDUE`).** Sessions 15 and 16
  both set 2026-08-12 as the date `/api/track` → `contract_track.recording_ok` would finally
  settle `PT-WRITER`. It was read. **Neither predicted branch fired, `PT-WRITER` is NOT closed
  and NOT refuted, and the ledger row stays `BLOCKED`.**
  * **THE CLOCK MOVED UNDER THE PREDICTION, AND THIS IS THE PART EVERY LANE MUST PICK UP: the
    bound inception is 2026-08-11 and the operational gate is 2027-02-11**, not the 2026-08-10 /
    2027-02-10 this file and the ledger both still assumed. The theme-restoration lane closed
    vintage 2 and opened **vintage 3** on 2026-08-11 (capital_discipline reaching a live score is
    an ADOPTED change), so **vintage 2 lasted ONE DAY** and vintage 3's first row is not owed
    until **2026-08-13**. `recording_ok` is therefore `None` — the contract's own
    not-vacuously-green rule working correctly, since no trading day is yet due. **Derive the
    vintage, never quote it from a prompt or a handoff.**
  * **A DEFECT IN THE INSTRUMENT, MINE, AND IT MADE EVERY PREVIOUS MORNING'S READING
    MEANINGLESS.** `gap_report` counted the CURRENT day as due from midnight, but a trading day's
    row is written after that day's close. **Measured: a writer holding every row it could
    possibly have written still read `recording_ok: false` on 11 of 11 replayed trading-day
    mornings, always naming the current day.** That is the exact mirror of the vacuous-PASS
    defect session 15 caught in this same function, and since **LA8 put the gap on PUBLIC
    surfaces** it was a daily false alarm on a red light that is supposed to be loud. A row now
    falls due at the start of the **next trading day**, keyed to the calendar and deliberately
    NOT to the writer's 20:01 cron — hard-coding a clock time would couple the contract's gate to
    one implementation's schedule. Detection is delayed by at most one trading day, well inside
    the contract's own **LOGGED-NOT-VOIDED** allowance for a single day's write filled the same
    week.
  * **A CORRECTION AGAINST MY OWN FIRST CUT, kept because the error is the instructive part.** I
    first reported that vintage 2 owed a row for 2026-08-11 and never received it. **It owed
    NOTHING** — under the corrected rule that row does not fall due until 2026-08-12, and vintage
    2 had already closed. The claim was an artefact of **the very off-by-one the same change
    repairs**, computed with the old rule while arguing for the new one, and it was caught by the
    test written to pin it.
  * **A SECOND REAL DEFECT: A VINTAGE EVENT SILENTLY CLEARS THE RECORDING GAP.** `gap_report` is
    scoped to the open vintage, which is correct — the contract attaches the gate to the current
    vintage — but it means a dated miss stops being reported the moment the next vintage opens.
    **Vintage 1 owed six rows and got two, and its four missing dates (2026-08-03, -04, -05, -07)
    are unreachable from anything `recording_ok` reports today.** The contract tolerates a missed
    day as LOGGED-NOT-VOIDED, but **it can only be logged if something records it, and nothing
    did.** New `track_meter.recording_history` reports every vintage side by side and reproduces
    the contract's own 2-of-6 figure; **`recording_ok` is deliberately unchanged.**
  * **ON THE WRITER ITSELF — EVIDENCE, NOT PROOF, AND THE SESSION'S OWN HYPOTHESIS IS REFUTED.**
    The bound `data/valquo_track_history.csv` has mtime **2026-08-07 18:07** and was untouched
    across **both** 2026-08-10 and 2026-08-11; no scheduled task matching the reported name
    exists; and no code in this repository writes the file (session 13's finding, still true).
    **The "the write died in the overnight restart" hypothesis is refuted by timing:** the
    machine restarted at **03:33 on 2026-08-12**, which is **7.5 hours AFTER** the 20:01 window
    on 2026-08-11, so it cannot have interrupted that write. **And the local copy is not a stale
    mirror of a healthy remote** — the weekly `track-backup` cron pulled the LIVE service's bound
    Index on 2026-08-10 18:09 and committed the same two rows; `/api/track` is owner-only and
    returns 403 unauthenticated.
  * **ZERO TRIAL COST — a correctness repair, logged `FIXED`. Equity `N` stays 158**, options
    258, infra 10, and `BACKTEST_RESULTS.json` needs no re-run. **A near-miss worth carrying:
    `RESEARCH_LOG.md` holds TWO tables with DIFFERENT 9-column schemas, and an append lands under
    the SECOND** (`id|date|domain|pre|hypothesis|metric|verdict|n|source`). My first row used the
    first table's layout, so the parser could not find its verdict cell and **counted a `FIXED`
    repair as an infra trial**; caught by diffing `by_domain` against `HEAD` rather than by
    reading the row. `HANDOFF_edge_audit.md` §1-6.
- **THE DOWNSIDE-EXCLUSION SCREEN IS NOT MERELY INERT, IT IS COUNTERPRODUCTIVE — THE NAMES IT
  DELETES OUTPERFORM THE NAMES IT KEEPS AND CRASH AT HALF THE RATE (2026-08-11, session 27,
  `S10`).** Don's own question, formalised: *should a top-decile name whose point-in-time BULL
  case already sits at or below price make the book at all?* `PREREG_s10_downside_exclusion.md`
  was committed **alone at `a041e09`** — one `.md`, zero `.py` — a strict ancestor of the
  measurement commit. **ADOPTS NOTHING and no live code path changed.**
  * **THE SCOPE DIFFERS FROM THE AUDIT'S OWN S10, DELIBERATELY, AND THE REGISTER SAID SO BEFORE
    ANY RESULT.** `VALQUO_EDGE_AUDIT.md:739` specifies S10 as an **accounting red-flag veto** —
    Beneish M-score, Altman Z-score, external financing, NT late-filing notices. **This tested
    NONE of those four.** It ran the **valuation-band** exclusion instead. The ledger row is
    therefore **`PARTIAL`, not `DONE`**: *the accounting half has never been tested and closing
    the row would tell the next session it had been.*
  * **THE MECHANISM ARM IS THE FINDING, AND IT REFUTES THE PREMISE RATHER THAN FAILING A BAR.**
    Within the top decile the **flagged** names return **+6.5125%/63d** against the unflagged
    **+6.2677%** — the names the screen would delete very slightly **OUTPERFORM** the ones it
    keeps (**+0.98pp/yr, HAC *t* +0.4775**, a clean NULL that flips sign between halves at
    −0.41pp early and +2.12pp late). **There is no information in the flag in either direction.**
  * **THE AUDIT'S OWN KEY COUNT GOES THE WRONG WAY TOO.** Its argument is that an exclusion screen
    *"only needs to avoid a small number of catastrophic outcomes"*. Measured: flagged names fall
    more than 50% in **15 of 3,129 (0.479%)** against **69 of 8,297 (0.832%)** for the names
    retained. **The screen preferentially removes the names that crash LESS often, at roughly half
    the rate of the ones it keeps.**
  * **REJECTED on both arms, and drawdown does not merely fail to improve — it WORSENS.** Against
    the audit's asymmetric bar (drawdown better by >2.0pp AND alpha worse by <1.0pp, both halves):
    `A1 DROP` −2.61pp of drawdown and −0.24pp of alpha; `A2 BACKFILL` −3.35pp and −0.93pp, with
    the late half −2.14pp. The alpha effect **flips sign between halves** (helps early, hurts
    late) — session 7's LOO pattern for the fifth time.
  * **WHY, MEASURED ON THEME z-SCORES: the screen deletes the exposure R1 says is real.** Flagged
    names carry **higher momentum** (+0.9530 vs +0.6741) and **much lower value** (+0.2728 vs
    +0.7362, the largest move in the table). R1's re-run puts the book on **UMD +0.205 (t 3.65)**
    and **HML +0.251 (t 2.93)**, so a DCF-based bull case sits below price for exactly the names
    that have already run. The screen strips momentum and tilts the remainder further into value —
    the **FNMA value-trap direction** the free-analysis lane documented. Illustration, not
    evidence: on the last scored date the screen drops 8 of 25 names and **adds Freddie Mac and
    MBIA**.
  * **IT IS ALSO SUBSTANTIALLY A SECTOR EXCLUSION WEARING A VALUATION SCREEN'S NAME — U7's failure
    mode in a new costume.** The flagged **rate** runs **51.38%** for the financial valuation
    regime against **12.66%** for hypergrowth, and by sector **48.88%** for Financial Services and
    **40.32%** for Real Estate against **15.79%** for Industrials. A three-fold spread: much of
    what this "valuation screen" does is **hold fewer banks and REITs**.
  * **A DEFECT IN MY OWN INSTRUMENT, CAUGHT BEFORE ANY VERDICT WAS READ.** `max_drawdown` is
    **negative**, so an arm improves it by being **less** negative and the gain is `arm − base`.
    The first cut computed `base − arm` and **reported a 2.61pp WORSENING as a 2.61pp
    IMPROVEMENT** — it would have left the REJECT verdict standing while **inverting the reported
    reason for it**. This is the `monotonicity` sign error one lane over, and it is now pinned by
    a **known-bad fixture carrying the real measured pair**.
  * **THE DRAWDOWN LEG IS DECIDED BY ONE QUARTER, AND THAT IS MEASURED RATHER THAN ASSERTED.** The
    worst peak-to-trough spans **exactly ONE 63-day period on every arm**, at the same trough
    index **44 of 69** — COVID 2020Q1. The register called max drawdown *"a single order
    statistic"*; this is that caveat with a number on it. **X7 calibrates no drawdown floor
    anywhere**, so the 2.0pp bar is **UNCALIBRATED** and is labelled so.
  * **THE ALPHA LEG CANNOT RESOLVE ITS OWN BAR, AND THE REGISTER SAID SO FIRST.** The audit's
    1.0pp allowance sits **BELOW X7's calibrated 1.95pp** alpha margin. It survives only because
    it is a **non-inferiority** allowance, so **a pass means "no alpha loss detectable at this
    panel's resolution", NEVER "the loss is under 1pp"** — X3's error, named in advance.
  * **CONTROLS ALL PASS. C1 is the strong one: the rebuilt panel reproduces S23's banked
    fair-value panel on all 108,241 shared keys at `max |Δ| = 0.000e+00`** across twelve base
    fields, with `valuable`/`regime`/`method`/`growth_led` **100.000000% identical** — so adding
    the band did not disturb the base by a bit. **C2** the band **IMPORTS
    `pipeline._blend_scenarios`** rather than re-implementing it, so it is the same number the
    site renders as its scenario card (B7's defect class, pinned). **C3 ZERO** ordering violations
    of `bear ≤ base ≤ bull` over 108,100 full trios. **C5 the harness reproduces the published
    record to sixteen digits and the run ABORTS before reading any arm if it does not.**
  * **Coverage first, per the COVERAGE RULE: 11,426 top-decile rows, bull-case coverage 92.42%,
    flagged 27.38%.** A name with **no** computable bull case is **KEPT, never excluded** —
    excluding on missing data is a data-availability screen wearing a valuation screen's name,
    and it would correlate silently with era, domicile and regime.
  * **Equity `N` 155 → 158** (three arms — DROP, BACKFILL, MECHANISM — each of which could
    independently have been reported as a positive finding). Expectations scored **5 right, 1
    wrong**, unusually good here **and for a stated reason: they were derived from measured facts
    already in the record** (R1's UMD/HML loadings, the free-analysis down-quarter result) rather
    than from intuition. The one miss is the audit's premise itself — the screen was predicted to
    catch a non-trivial number of genuine disasters, and it catches them at **half** the rate of
    the names it retains. `data/free_analysis/S10_DOWNSIDE_EXCLUSION.json`;
    `HANDOFF_edge_audit.md` §1-5.
- **REAL TRADES PAY ABOUT TWO THIRDS OF THE QUOTED HALF-SPREAD, A PASSIVE FILL IS NOT A FREE
  HALF-SPREAD — AND BOTH ITEMS RETURN **NO VERDICT** BECAUSE MY OWN VOID CONDITION FIRED AND
  DISQUALIFIED THE ARM THAT WOULD HAVE CLEARED THE BAR (2026-08-11, session 26, `O10` + `O18`).**
  First use of O14's tick cache. `PREREG_o10_passive_fills.md` and `PREREG_o18_spread_cost.md` were
  committed **together and ALONE at `34b0c11`** — two `.md`, zero `.py`. Frozen book, no re-mine,
  **no live code path changed**.
  * **THE SCOPE FACTS WERE MEASURED BEFORE THE REGISTERS WERE WRITTEN, AND THEY RULE OUT THE
    QUESTION MOST PEOPLE WILL THINK WAS ANSWERED.** O14's cache is **exactly the alert-days and
    nothing else**: for the 3,870 banked entries the **next session is cached for 0 of 3,870 and
    the exit day for 0 of 3,870**. The live bot submits after the close and its order rests on
    **D+1**, so **"what the live bot's limit orders fill at" is NOT ANSWERABLE on this cache** and
    no verdict is issued about it. **Only the ENTRY leg is coverable while a round trip crosses the
    spread twice.** What *is* answerable is the execution environment of the exact contracts the
    book traded, measured **quote-relatively** — no decision time, no look-ahead. Join complete:
    **3,869 of 3,869**, the one missing day (`BUD` 2024-01-10) costing exactly one row.
  * **THE VOID IS THE HEADLINE AND IT IS NOT A TECHNICALITY.** C2 required the behavioural
    condition-code split to replicate; it failed on **one code** — code 35, 4.94% of prints, reads
    at-touch **0.2496** on the full book against **0.439** on the 120-entry probe that classified
    it, below package code 125's 0.2649. **The all-codes fallback the register had already
    disqualified — for crediting multi-leg package liquidity to a single-leg resting order, an
    OPTIMISTIC bound — reads NPA 1.0029pp against the 1.00pp bar, while the registered primary
    reads 0.6318pp.** The arm ruled out in advance is exactly the one that crosses. **Reported
    because it cuts the other way: the void concealed no crossing** — the fallback's halves are
    1.0760 and 0.9352, so both-halves fails there too. Arithmetic, **not a verdict**.
  * **A PASSIVE FILL IS NOT A FREE HALF-SPREAD, AND THIS IS THE QUOTABLE MEASUREMENT.** Resting at
    the mid over 30 minutes: gross saving **+2.4555pp**, adverse selection **−1.8237pp**, net
    **+0.6318pp** (CI95 [0.5014, 0.7643]), fill rate **0.5726**. **ADVERSE SELECTION EATS 74.3% OF
    THE GROSS SAVING** — a resting bid fills when sellers are aggressive, and *"you save half the
    spread"* overstates by nearly fourfold.
  * **`ρ` = 0.6743: A REAL TRADE PAYS TWO THIRDS OF THE QUOTED HALF-SPREAD** (CI95
    [0.6617, 0.6871]; 0.6054 all-codes; unweighted agrees at 0.6737). **The decomposition keeps
    apart two things that would flatter the answer if added:** EOD half-spread **$0.1544** →
    prevailing-at-print **$0.0999** → effective **$0.0591**. The **$0.0545 availability term is
    SELECTED** — you avoid it only if you trade when the market is there — and **may never be
    quoted as a saving**; only the **$0.0408** price-improvement term is an execution property. So
    of an apparent **$9.53/contract** overcharge just **$4.08** is defensible.
  * **THE STRONGEST CONDITIONING IS ENTRY PREMIUM, NOT QUOTED SPREAD** (the registered expectation
    was wrong): `ρ` falls monotonically **0.778 → 0.597** with premium, range 0.1812 against a
    permutation p95 of 0.0376 — **4.8× the null**, negative Spearman in both halves and both arms.
    A cheap option pays nearly its whole quoted half-spread; a fixed tick on a small premium is why.
    **`F6` (print size) is DEGENERATE** — two of five bins **empty**, print size being overwhelmingly
    one contract — and is flagged, not reported as a failure, per O13's treatment of `opt_right`.
  * **THE LIMITATION THAT MUST TRAVEL WITH EVERY FIGURE ABOVE: coverage is 0.7162 and the excluded
    28% is NOT random.** The tape-thin contracts carry **62% wider spreads, ~half the market cap and
    ~half the ATM open interest, and NEGATIVE expectancy (−3.11% vs +5.82%)**. **Every number here
    is measured on the LIQUID part of the book**, and cost bites hardest on the part excluded —
    O13 already found `entry_spread_pct` q5 at −7.41%.
  * **A PROCESS DEFECT, MINE: C2 and the outcome statistics were computed in the SAME pass**, so it
    cannot be claimed the control was read before the numbers. A gating control must run and be read
    in a **separate pass**. Also: the `λ=+1` row is the instrument's own null, should read 0 by
    construction and reads **−0.07 to −0.59pp** (late-session reference moments with truncated
    windows) — a measured bias that runs **against** the passive arm, so it does not manufacture the
    null. **The O14 staleness caveat was checked and does NOT bite here: median quote lag 0.0s,
    0.19% over 60s.**
  * **NOTHING IS ADOPTED. `DEFAULT_AGGRESSION` is untouched at 1.0 and pinned by test**; a material
    result is **routed to Don**, because changing the fill constant re-prices every options figure
    the project publishes. **AND CHEAPER FILLS DO NOT RESCUE R2** — the random-entry control is
    filled by the identical rule, so the **−5.0640pp** gap is untouched. That `ρ < 1` means every
    options expectancy in the record is **understated** is *not* evidence the signal works.
  * **Options `N` 248 → 258** (4 + 6, exactly as pre-committed), **charged in full despite no
    verdict** — declining to run keeps the denominator (session 8), but running and then voiding
    does not refund the search. **Equity `N` untouched at 155.** Expectations scored **8 right,
    3 wrong, 1 split, 1 unscorable**. `data/free_analysis/O10_O18_TICKFLOW.json`;
    `HANDOFF_optionsbot.md` §34-37.
- **THE PRICER'S DIVIDEND GAP IS A CALLER BUG, NOT A MODEL BUG — IT IS CHEAP WHERE IT IS
  MEASURABLE AND ONE DOOR IS UNRESOLVED; AND THE PER-BUCKET FLOOR CANNOT DELIVER WHAT ITS OWN
  COMMENT PROMISES (2026-08-11, session 25, `O21` + `O26`).** Frozen book, no re-mine, **no live
  code path changed**. `PREREG_o21_dividends.md` and `PREREG_o26_bucket_floor.md` were committed
  **together and ALONE at `bf5324c`** — two `.md`, zero `.py`.
  * **`O21`: `bs_price`, `implied_vol` and `greeks` ALREADY take a dividend yield `q` and handle
    it correctly. Every caller uses the default `0.0`.** So **anyone who "adds dividend support
    to the pricer" is fixing the wrong thing** — pinned by a test. And the banked P&L comes from
    **QUOTED bid/ask**, so the pricer cannot move it directly; it reaches the book only through
    early exercise, contract selection and stored derived fields.
  * **EXPOSURE IS WIDESPREAD, THE MEASURED COST IS NOT.** 81.4% of trades are on dividend payers
    (median trailing yield 2.02%) and **2,107 of 3,870 calls span an ex-div date** — yet only
    **34 exits (0.879%) were booked below intrinsic, worth +0.2002pp** against a pre-registered
    1.00pp bar. **Measured MODEL-FREE (`bid < S − K`)** so the answer is not a function of the
    pricer under test. Controls first: parity recovers the stored entry spot at median relative
    error 0.00232, and the simulation's **own** bars at **0.00000, 100% within 1%**.
  * **THE UNRESOLVED DOOR, REPORTED AS UNRESOLVED RATHER THAN AS ZERO.** The `q = 0` control
    reproduces the banked contract **3,870/3,870 = 100.00%**; the corrected pricer picks a
    **different contract on 179 entries (4.63%)** and **not a near-substitute** — median
    **|delta gap| 0.129** against a 0.35 target, **93.9% moving to a LOWER strike**, the predicted
    direction. **Its P&L is NOT COMPUTABLE on the frozen book:** the freeze holds full chains
    only on **ENTRY** dates, so a contract the book never held has no forward price path (median
    **2** chain dates). **Closing it needs a re-mine and is the recommended next item.**
  * **THE PRICER IS DELIBERATELY NOT CHANGED** — neither clause of the materiality bar is met,
    and passing `q` into `pick_contract` would change **which contract the live engine buys on
    4.63% of entries**: a construction change, not a bug fix. The non-change is **pinned by two
    tests**, the discipline session 16 used for sizing and session 20 for `zscore`.
    D3 for the record: `q = 0` **understates** solved IV by a median **0.00617** (~0.62 vol
    points) and **overstates** |delta| by 0.00668; `delta85` firing moves 6 → 2 of 3,870, which
    cannot disturb its −0.02pp rejection.
  * **TWO DEFECTS IN MY OWN INSTRUMENT, both caught before any verdict was read and both pinned.**
    Spot at exit was first estimated as `max(call_bid + strike)` — parity's **loosest UPPER
    bound** — which inflated the early-exercise gain to **+5.62pp, eight times the truth**, in
    the direction that manufactures a material finding; the parity replacement then rejected
    zero-value puts and so discarded exactly the deep-ITM cases early exercise lives in, scoring
    **zero rows**. **Also found: `options_backtest.BARS_CACHE` is a RELATIVE path**, so it
    silently resolves to nothing from a git worktree and returns an empty bar set rather than an
    error.
  * **`O26`: NULL — `MIN_CLOSED_PER_BUCKET` STAYS 30, AND THAT IS NOT A VINDICATION OF 30.** The
    constant's own comment — *"enough that one lucky contract cannot flip the verdict"* — is
    testable and had never been tested. `P_flip(n)`, the chance that removing the single most
    extreme trade flips a bucket's sign, **never reaches the 0.05 bar anywhere on the
    pre-committed grid**: **0.1848 at the shipped 30** and still **0.1084 at n = 300**. Going
    30 → 300, a tenfold rise **no live bucket could supply**, buys almost nothing.
  * **THE SECOND HALF IS THE STRONGER RESULT AND IT WAS CHECKED AGAINST CLOSED FORM, NOT
    TRUSTED: half-to-half sign agreement is a COIN FLIP at every bucket size** — 0.4942 at n = 30,
    0.5482 at n = 300 — and the book's own moments (mean 0.0327, sd 0.9251) **predict that curve
    analytically** (0.5059, 0.5561). **A bucket would need ~6,148 trades for its two halves to
    agree on the SIGN of expectancy 95% of the time; the whole book is 3,870 and the largest live
    bucket is 2,058, with small-cap at 44.** So **per-bucket expectancy on this book is
    essentially unmeasurable at ANY floor** — a third independent corroboration of R2 and O13.
    **Do not raise the floor; stop making per-bucket expectancy claims on this book.** Zero live
    buckets change status.
  * **Options `N` 246 → 248** — one trial each. **O21 was first charged ZERO** on the reasoning
    that a correctness measurement is a `FIXED`-class row, and **another lane's research-page
    test rejected it**: the log schema requires every non-`FIXED` row to charge at least one
    trial, and this row is not `FIXED` because nothing was repaired. It had a pre-committed bar
    and returned a verdict against it, so it is a trial — **corrected upward**, against my own
    result. **Equity `N` untouched at 155** and `BACKTEST_RESULTS.json` needs no re-run.
    Expectations scored **6 right, 4 wrong** across the two items.
    `data/free_analysis/O21_DIVIDENDS.json`, `O26_BUCKET_FLOOR.json`;
    `HANDOFF_optionsbot.md` §29-33.
- **THE OPTIONS ANTI-SIGNAL IS DIFFUSE, ENTIRELY WITHIN-BIN, AND CANNOT BE TRADED — AND THE DEAD
  ENTRY COSTS 2.75× IN POSITION SIZE (2026-08-11, session 24, `O13` + `O12`).** Two ledger items,
  one session, on the banked split-clean books; `PREREG_o13_antisignal.md` and
  `PREREG_o12_kelly_ruin.md` were committed **together and ALONE at `b0f287d`** — two `.md`, zero
  `.py`. **R2 is NOT re-opened; this characterises the corpse.**
  * **THE FINDING THAT CLOSES OFF A FAMILY OF REPAIRS: the −5.0640pp gap is ENTIRELY a WITHIN-BIN
    (rate) effect, not composition.** Across **all 32 feature arms** the rate component runs
    **−4.23pp to −5.79pp** against the −5.0640pp total, while the largest **mix** component
    anywhere is **0.7711pp — 15.2% of the gap**, most under 0.2pp. **The alert does not lose
    because it picks different CONTRACTS from random entry; it loses inside every kind of contract
    it picks.** So "trade longer-dated / tighter spreads / bigger names" are all composition fixes
    aimed at the wrong thing.
  * **Q2 DIFFUSE and Q3 (the inverse) NULL.** Nothing clears its own calibrated p95 in **both**
    halves — 4 of 32 clear full-sample against **~1.6 expected at a 5% bar over 32 correlated
    arms**. The decide-half refusal rule **makes the measure half WORSE in both directions**
    (early→`dte`/q2 −0.0977pp, late→`iv`/q3 −0.7774pp) and **the two directions select DIFFERENT
    features** — session 7's LOO pattern for the third time. `iv` q3 is the **worst** bin on the
    late half and nearly the **best** on the early half.
  * **YOU CANNOT SHORT THE GAP, and this is the most likely misreading.** The anti-signal is
    **RELATIVE to the control, not absolute** — the alert book's own expectancy is **positive**
    (+3.2702%/trade) — so mechanically reversing it is negative before any cost, with the
    round-trip spread on top. It is a reason not to pay for the alert, not a tradeable short.
  * **REPORTED BECAUSE IT LOOKS LIKE A FINDING AND IS NOT: `dte`.** Alert expectancy climbs
    monotonically with tenor (**−0.35% → +7.63%**) while the control stays flat, and q2's gap is
    **−10.84pp** — but it **fails its own calibrated bar** (0.472 vs p95 0.497) and clears in one
    half only. **Do not act on it.** This is exactly what the X7 calibration method is for.
  * **`O12`: `f*` = 0.0403 and the verdict is NOT USABLE — but the HALVES AGREED (1.758 against a
    2.0 bar); the bootstrap CI95 [0.0000, 0.1001] includes zero.** Right answer, wrong reason.
    **At full Kelly P(drawdown > 50%) is 0.753 for a median +26.7%/yr**; quarter-Kelly keeps most
    of the growth (1.114 vs 1.267) at 0.006. **At f = 0.10 — only 2.5× Kelly — the MEDIAN outcome
    is a LOSS on a positive-expectancy book.** Kelly here is conditional on a distribution R2 has
    already shown is worse than random entry, so **no fraction is a recommendation for real
    money**; live flat 1-contract sizing is **unchanged**.
  * **R2 RESTATED IN SIZING TERMS, and it is new: the random-entry control supports `f*` 0.1110,
    2.75× the alert book's.** The dead entry costs not only expectancy but the size the book can
    carry. Flat sizing ($257/trade at the median premium) equals `f*` at **$6,371** equity — so
    the live book is under-sized above that and **over-sized below it**.
  * **THREE DEFECTS, none in the live product.** `iv_rank` is **wired and 0.0% populated on BOTH
    books** (COVERAGE-RULE class). **`opt_right` and `horizon` are CONSTANT — the banked options
    book is 100% calls and 100% `swing`** — so every options claim this project makes is about
    long calls at swing horizon only, and those two arms are flagged degenerate rather than
    reported as failures. The alert **label vocabulary is PARAMETERISED** (`Low IV 14%`…`19%`,
    `Volume surge 1.5x`…`1.9x`), inflating 17 registered arms to **32**; the registered definition
    was kept and the **trial cost corrected UPWARD**, against the register's own result.
  * **17 of 100 bins DO lose money outright** — the widest-spread, least liquid ones
    (`entry_spread_pct` q5 **−7.41%**, `pit_median_spread_pct` q5 −5.53%). That **refuted a
    pre-registered expectation** and is the recommended next item: `entry_spread_pct` as its own
    registered refusal rule, which inherits O13's discouraging Q3a prior.
  * **Options `N` 210 → 246. Equity `N` UNTOUCHED at 155** and `BACKTEST_RESULTS.json` needs no
    re-run — the trial counter is domain-scoped. Expectations scored **5 right, 1 split, 2
    wrong** across the two items — the split is flat-sizing-below-`f*`, which holds for five of
    six account sizes and fails below $6,371. `data/free_analysis/O13_ANTISIGNAL.json`, `O12_KELLY_RUIN.json`;
    `HANDOFF_optionsbot.md` §24-28.
- **CLUSTERED INFERENCE IS NOW THE DEFAULT, AND THE RESULTS FILE HAS A FIELD-LEVEL SCHEMA GUARD
  THAT IMMEDIATELY FOUND TEN COMPUTED FIELDS BEING SILENTLY DROPPED — INCLUDING B17's ENTIRE
  DISCLOSURE (2026-08-11, session 22, `M2`/`M6`).** Both **infrastructure**: no hypothesis, no
  verdict. **Equity `N` is UNCHANGED at 155** and the Deflated Sharpe is bit-identical at
  0.8340367318547941; the two rows are logged to the **infra** domain at n=1 each (infra 8 → 10)
  on the V1 precedent, and infra `N` gates no published claim. `PREREG_m2_m6.md` committed
  **alone at `af88533`**, a strict ancestor, because M2 touches the statistic every
  pre-committed gate reads.
  * **SCOPING REMOVED MOST OF THE WORK AND WAS CHECKED AGAINST THE CODE, NOT THE ITEM TEXT.**
    The `M2`/`M6` in **`SECURITY_AUDIT.md` are a DIFFERENT pair, already fixed at `96fd8bf`** —
    the ledger's id-collision warning is real. Of the real items (`VALQUO_EDGE_AUDIT.md:1507`
    and `:1557`), **M2's entire trade-level half was already delivered by R3** (date-block
    bootstrap, purge/embargo, two `n_eff` estimates against a shuffled null) and **M6's
    block-level half by B22**. The options-bot lane had already published the correct remaining
    scope — *"the FIELD-level half does not exist at all, and that is the half the R9 loss
    actually came through"* — and that report was adopted rather than re-derived.
  * **"CLUSTERED BY DEFAULT" COULD NOT MEAN REDEFINING THE EXISTING KEYS, AND THE REGISTER SAID
    SO BEFORE THE CODE EXISTED.** `long_short_tstat` is **naive** and is what
    `holdout_compare_panels` reads — the gate whose **+0.25 t** margin was committed against it,
    which decided `SECTOR-NEUTRAL-B6`, `S20` and `S21`. The floors are **statistic- AND
    lag-specific** (naive 2.1437, HAC 2.2837, alpha HAC 2.2913, all at **lag 1**). Redefining in
    place would have silently re-quoted every verdict those gates ever produced — session 10
    exists because exactly that mismatch went unnoticed for two sessions. **So clustered is the
    default by being what the one shared function returns as its unqualified `t`, not by moving
    the record.** `statistics.py::mean_inference` is now THE definition; `fundamental_panel`'s
    four hand-rolled copies delegate to it, **bit-identical over 400 random series, max |Δ|
    0.000e+00**.
  * **`n_eff` NOW TRAVELS WITH `n`** (M2's third requirement, which nothing in the equity lane
    did). Long-short lag-1 autocorrelation **0.189046**, reproducing R9's +0.189, for **n_eff
    47.06 of 69**; top-decile alpha **0.081237**, n_eff **58.63**.
  * **THE THEME IC *t* — THE STATISTIC CARRYING X7's CALIBRATED 2.71 BAR — HAD NO CLUSTERED
    VARIANT COMPUTED ANYWHERE, EVER.** Nor did `per_signal_ic`. Both now ship `ic_inference`.
    **`ic_tstat` is untouched, so the 2.71 bar still applies to exactly the number it was
    calibrated on, and `ic_inference.t` is a NEW statistic with NO calibrated floor — nobody may
    compare it to 2.71.**
  * **REPORTED BECAUSE IT CUTS AGAINST THE CHANGE, and the pre-registered expectation was WRONG:
    the theme IC series are NOT materially autocorrelated.** The clustered *t* is below the naive
    one in only **5 of 9** themes, max |ρ| is **0.164**, and **four of nine are NEGATIVE** (which
    improves precision, so `n_eff` clips at 69). `quality` 3.1015 → 2.9837, `capital_discipline`
    2.7556 → 2.6342, `momentum` 1.3118 → **1.4182** (rises). Unlike the long-short spread
    (ρ +0.189, Ljung–Box p 0.036), **there is little serial correlation to correct.** The gap
    closed is real as **completeness**; the numbers barely move.
  * **M6 FOUND FIVE LIVE DROPS, TEN FIELDS, NONE PREVIOUSLY KNOWN.** `_backtest_hold` computes
    **B17's WHOLE disclosure** (`label_warning`, `target_n`, `exit_rank`, `held_min/median/max`,
    `charges_costs`, `charges_taxes`) **and `build_payload` carried none of it** — so
    `portfolio.cagr`, the number this file calls the noisiest in the results, shipped with no
    warning that the book holds ~`exit_rank` names rather than `top_n` and pays neither costs nor
    taxes. **The fix for B17 was being computed and thrown away.** The canonical file now carries
    **`held_median = 42`** for the book labelled "top 25". Separately, **session 12's
    `adopt_detail` and `challenger_weights_cols`** — banked so "what would this run have scored
    one haircut lower" is arithmetic — never reached the file a later session would read.
    **Banking a number into a dict nobody serialises is not banking it.** `SCHEMA_VERSION` 4 → 5,
    purely additive.
  * **THE TENTH FIELD IS THE BEST EVIDENCE FOR THE GUARD, because the guard found it against its
    author.** `ev_freshness.rows` — the **denominator** of the `fresh` fraction — was caught **on
    the guard's first real run**, and it had escaped the hand-built spec because that spec was
    derived by walking each producer's AST while `ev_freshness` builds its dict incrementally
    (`out["rows"] = int(n)`). **Static analysis could not see it; a runtime producer-enumerating
    guard could.** That is M3's thesis — *a guard reading a registry cannot see an unregistered
    field* — demonstrated on my own static pass.
  * **A DEFECT IN THE CHANGE ITSELF, CAUGHT BEFORE SHIPPING: THE GUARD WOULD HAVE BEEN
    SWALLOWED.** `main()` wraps the results write in `try/except Exception` commented *"Never
    allowed to fail a completed backtest"* — right intent, but it would have caught
    `PayloadSchemaError` and printed it as a warning nobody reads. **A check that cannot fail
    anything is not a check, which is the exact pattern M6 exists to close.** It now has its own
    handler **ordered ahead of** the blanket one, keeps every artifact already written, and exits
    **non-zero**; pinned by an AST test. **No environment-variable escape hatch** (`RUN_RULES`
    A5) — the allowlist is the legitimate door and it leaves a diff.
  * **THE INTEGRATION TEST FAILED FIRST, WHICH IS WHY IT IS WORTH ANYTHING.** The full-universe
    run completed every computation and then **failed at the write step** on `ev_freshness.rows`,
    writing both files first and exiting non-zero exactly as designed; the re-run after the fix
    passes with `errors: []`. **C1 holds: leaf diff 1,217 → 2,423 leaves, 1,206 added, ZERO
    removed, and all nine real moves are last-digit float noise in the cost curves.** Every
    headline is bit-identical.
  * **`archive_scan` NOW RECORDS *WHY* A ROW WAS BLANK.** It named ten keys and stored
    `fair_value` but neither the refusal flag nor its reason, so the permanent,
    survivorship-free archive could not tell *"we declined to value this"* from *"we never
    tried"*. Reported by the live-data lane as **"edge lane, not mine"** — it was this lane's.
  * **STILL OPEN, REPORTED NOT FIXED: the CPCV embargo is ONE rebalance period against a 252-day
    feature lookback** (`ret_12_1`), so a test period's realised returns feed the momentum
    features of the next **four** training dates. M2's own last paragraph. Fixing it moves PBO,
    the Deflated Sharpe and the adopt gate, so it is a **results change** needing its own
    register. Also **`valuation/engine/calibration.py:737` is a FOURTH hand-rolled naive
    t-stat** — engine lane, untouched.
- **THE STANDARDISER IS WORTH SEVERAL POINTS OF ALPHA AND NO THEME IC CAN SEE IT — S20 REJECTED,
  S21 NOT REPLICATED, AND THE STANDING RULE IS NOW PROVED RATHER THAN ANECDOTAL (2026-08-11,
  session 21, `S20`/`S21`).** Ledger items S20 ("rank composite, not z-sum") and S21 ("winsorise
  before standardising"), both `OPEN`, both `src=auto`, neither ever run. They are the same
  decision twice — how a cross-section becomes a number before the weighted sum — and P6.3 is why
  they got a register: robust z-scores **halved the long-short *t*** while every per-signal IC
  stayed flat. `PREREG_s20_s21_construction.md` was committed **alone at `27af414`**, a strict
  ancestor of the measurement commit, running **the SAME shipped `holdout_compare_panels` gate with
  the SAME already-committed margins** (+0.25 long-short *t* AND +100bps alpha, in **both** halves,
  boundary embargoed) under **two** pre-specified weightings and no others. **One panel build,
  three scorings, 113,945 identical rows.**
  * **THE HEADLINE IS THE PAIR, NOT EITHER ARM: the two arms move top-decile alpha by −3.49pp and
    +2.43pp per year, and NOT ONE THEME IC MOVES AS MUCH AS 0.4 OF A *t*** (max |Δ| **0.1920** and
    **0.3558**; `insider` moves **exactly 0.0000**, `capital_discipline` +0.0001, `size` −0.0017).
    Judged by per-signal or per-theme IC both changes look harmless. **The standing rule — never
    judge a construction change by per-signal IC — is now demonstrated three times (P6.3, X3, here)
    and, for a rank transform, is a mathematical IDENTITY rather than an observation:** control C5
    measures `max |ΔIC| = 0.000e+00` across all 44 number columns, because Spearman IC is invariant
    to a strictly monotone transform. **The composite is a weighted SUM and is scale-sensitive; the
    book is the deliverable.**
  * **S20 (RANK) IS REJECTED — AND IT FAILS WHILE MAKING THE DECILES *BETTER* ORDERED.** Deployed:
    alpha **+7.17% → +3.68%** (−3.49pp), long-short **+11.04% → +9.04%**, *t* 2.8361 → 2.3054, HAC
    **2.6199 → 2.0588**, alpha HAC **4.3762 → 2.0028** — so the rank arm **fails BOTH calibrated
    floors** (2.2837, 2.2913; **an EXTRAPOLATION** for a challenger arm) where the shipped arm
    clears both — while **monotonicity IMPROVES −0.8909 → −0.9515**. Rejected in **both halves** and
    again under flat weights. **The dissociation is the finding:** ordering *across* deciles gets
    smoother while the **top** decile, which is the product, loses its edge — D1 25.31% → 21.82%.
    Hypothesis, not a result: rank discards the magnitude information that identifies genuinely
    extreme names.
  * **S21's PREMISE IS WRONG AND THE REGISTER SAYS SO BEFORE THE RUN: `zscore` ALREADY winsorises
    at 2% before standardising**, at both layers (`cross_sectional.py:83-87`). The audit item
    proposes the shipped behaviour — which is what `src=auto`, *"a lead, not a fact"*, exists to
    warn about. So the arm actually run is **winsorisation OFF**, and an adopt would have meant
    **removing** the shipped clip.
  * **S21 IS NOT REPLICATED, AND IT IS THE MOST INTERESTING NEGATIVE IN THE FILE.** Full sample,
    every headline improves and several hugely: alpha **+7.17% → +9.60%** (+2.43pp), long-short
    **+11.04% → +16.63%**, *t* **2.8361 → 4.9395**, HAC **2.6199 → 4.3612**, monotonicity −0.9758.
    **But the gate splits: the late half passes (Δt +2.0125, Δalpha +3.69pp) and the EARLY half
    fails on the alpha margin BY 17 BASIS POINTS** (+0.83pp against the +1.00pp bar) while clearing
    the *t* margin. **Under flat weights it REJECTS outright**, both halves negative. Paired
    within-panel: +2.43pp/yr at HAC *t* **+1.9170**, long-short +5.59pp at **+1.9365** — **both
    below even the UNCALIBRATED 2.0.** Ambiguous against its own threshold is a **NULL**
    (`RUN_RULES` A6). Session 7's LOO pattern for the fourth time.
  * **THE CAUTION THAT MUST TRAVEL WITH THAT +2.43pp, or the number will be misquoted: the
    unclipped arm's most extreme composite averages 7.14× its OWN 99th percentile, against 1.64×
    for the shipped arm**, and only **8 of the shipped top 25 names** survive it. An unclipped
    z-score is a **fragile estimator** whose book is anchored by outliers. **Winsorisation is also a
    DATA-QUALITY defence, not only a statistical choice** — P7 shipped a currency bug that computed
    `book_to_price` **892 against a true 0.589**, and with no clip such a row dominates the whole
    cross-section's mean and sd. *"Removing the outlier guard improved the backtest"* and *"the
    outlier guard is not earning its keep"* are different claims and only the first is measured.
  * **A DEFECT IN THIS REGISTER'S OWN CONTROL, FOUND BY MEASUREMENT AND CORRECTED RATHER THAN
    DROPPED: C7 claimed a rank arm must be BIT-IDENTICAL under winsorisation. IT IS NOT.** Rank is
    invariant to **strictly** monotone transforms; winsorisation is only **weakly** monotone — flat
    in the clipped tails — so it creates **ties**, and a percentile rank is not invariant to ties.
    The differences sit in the clipped tails alone and the middle of the distribution is exactly
    invariant. **So S20 does NOT strictly subsume S21**, and the same mechanism gives the asymmetry
    worth keeping: **S20 is invisible to a per-signal rank IC; S21 is visible to it.** Pinned by
    test.
  * **Single-input themes are RANK-INVARIANT under a standardiser swap and multi-input themes are
    not** — `size`, `capital_discipline` and `insider` post a within-date rank correlation of
    exactly **1.0000**, because a monotone transform of ONE column preserves its ranking, while
    `quality` (ten inputs) is the most changed theme in both arms (0.9395, 0.8215). A mean of
    monotone transforms is not a monotone transform of the mean. **The pre-registered expectation
    said `size` would move most; it cannot, and the prediction was backwards.**
  * **Controls: C1 reproduces the published record to the digit; C2 113,945 identical rows across
    all three arms, 69 dates, 2,531 names; C3 both toggles far from inert (composite rank
    correlation 0.8859 and 0.7819, ~65-69% of names change decile); C4 no new missing values;
    C5 exactly zero; C6 `sentiment` empty and `insider`'s layer-1 exemption verified at max|diff|
    0.0 over 94,660 rows; C7 falsified as above.**
  * **Equity `N` 151 → 155** (two hypotheses × two weightings, no grid), √(2·ln 155) = 3.1760.
    **ADOPTS NOTHING**, and the register fixed that in advance: an eligible arm is recorded
    **ELIGIBLE, not adopted**, and **QUEUES BEHIND the theme restoration's vintage** rather than
    spending a second five-year clock reset on the same restart. Expectations scored **2 right,
    3 wrong, 1 split** — the streak continues, which is why they are written down first.
  * **THE QUEUEING CLAUSE TURNED OUT TO BIND, WHICH IS WHY IT WAS WRITTEN BEFORE THE RESULT: the
    theme-restoration lane took the vintage event THE SAME DAY** (`c8efd00`, `PREREG_theme_restoration.md`
    committed alone at `1d12822`), restoring `capital_discipline` to the live path on a fidelity
    gate while `institutional` (+0.1706) and `insider` (+0.3596) failed it. **Nothing here
    conflicts, because both arms failed their own gate** — but had either been eligible, adopting
    it separately would have spent a **second** clock reset for one restart's worth of evidence.
    The clause cost nothing to write and would have been unarguable to add afterwards.
- **SECTOR-NEUTRAL IS REJECTED AGAIN — AND IT FAILED *DIFFERENTLY*: THE TRADE-OFF THE ORIGINAL
  REJECTION RESTED ON DOES NOT EXIST ON THE CORRECTED PANEL (2026-08-11, session 20,
  `SECTOR-NEUTRAL-B6`).** Item **B** of `HANDOFF_parked_positives.md`. Sector-neutral ranking was
  rejected twice — P10 (2026-07-31) and 2026-08-02 — but **both rejections ran on the pre-B6
  110-date / 2,710-name panel the project has since declared void**, and the decision turned on a
  **−1.58pp alpha difference measured inside a panel whose alpha LEVEL moved −4.18pp when B6 was
  removed**. `PREREG_sector_neutral_b6.md` was committed **alone at `1bdb7e0`**, a strict ancestor
  of the measurement commit, re-running **the SAME shipped `holdout_compare_panels` gate with the
  SAME already-committed margins** (+0.25 long-short *t* AND +100bps alpha, in **both** halves,
  boundary embargoed) under **two** pre-specified weightings and no others.
  * **REJECTED under BOTH weightings, failing in BOTH halves.** Deployed: top-decile alpha
    **+7.17% → +6.09%** (Δ **−1.09pp**), long-short **+11.04% → +8.51%**, long-short *t*
    **2.8361 → 2.3423**, HAC **2.6199 → 2.1505**, monotonicity −0.8909 → −0.8667. Flat weights
    give the same answer, so **the verdict does not rest on a choice of weighting**.
  * **THE FINDING IS NOT "IT FAILED AGAIN", IT IS *HOW*.** On the void panel sector-neutral
    **BOUGHT long-short *t*** (3.396 → 3.896, **+0.500**) and **sold alpha**, and the rejection was
    a *judgement* that a long-only book should not make that trade. **On the corrected panel the
    gain is GONE AND ITS SIGN IS REVERSED** — **−0.494** deployed, **−0.300** flat — so
    sector-neutral is **worse on BOTH metrics and there is no trade-off left to adjudicate.**
    The rejection no longer depends on preferring alpha to a *t*-statistic.
  * **THE CALIBRATED FLOOR SEPARATES THE ARMS: the shipped arm clears the long-short HAC floor
    (2.6199 vs 2.2837) and the sector-neutral arm does NOT (2.1505).** Both clear the alpha HAC
    floor (2.2913). Quoted where X7/session 10 calibrated them — the full-universe decile book,
    69 dates, H = 63, lag 1 — and **labelled an extrapolation for the sector-neutral arm**.
  * **ONE PANEL BUILD, TWO ARMS, A PROVABLY IDENTICAL ROW SET — an improvement on both prior
    runs, which built the arms as two SEPARATE runs.** Each cross-section calls `build_frame`
    twice on the same `metrics` list, so the **`insider` nondeterminism this file records is
    common-mode and cancels** instead of landing inside the difference. Controls: identical
    `(date, ticker)` key sets (113,945 rows each); the toggle is **not inert** (composite
    correlation 0.9836, nine of ten themes move); the flat arm **reproduces the published record
    to the digit**; **sector coverage RE-MEASURED on the corrected panel at 100.0%, 11 sectors,
    smallest sector 50 names, ZERO singletons** (the 100% in the record was measured on the *void*
    panel); `insider` untouched at exactly 0.000; no new missing values; `sentiment` empty.
  * **A DEFECT FOUND AND REPORTED, DELIBERATELY NOT REPAIRED: `cross_sectional.zscore`'s
    zero-variance guard is VALUE-DEPENDENT.** It tests `sd == 0`, but whether a constant column
    has an exactly-zero pandas variance depends on the constant — exact for 0.0, 50.0, 2.5,
    0.125, ~1e-16 for **0.9, 0.1, ⅓, 12.34**. When it misses, `zscore` returns **a fabricated
    pattern with max |z| = 1.0 built from floating-point residue, not NaN** — so *a constant
    signal does not reliably neutralise itself.* **It also corrects the record: V2G's "a constant
    `insider` makes `zscore` return all-NaN" holds only because the live `insider` is constant at
    exactly 0.0 (`(50−50)/25`), and is not a general property.** **Exposure MEASURED, not
    assumed: nil** — no theme column is degenerate on any of the 69 dates, and the smallest
    within-sector dispersion over 231 sampled cells is 0.2209. **Not repaired because `zscore` is
    on the live scoring path, so changing it is a scoring change and therefore a VINTAGE EVENT**;
    pinned by a test that fails if it is ever silently corrected.
  * **CLOSED PERMANENTLY, by a clause fixed before the run: full sector-neutral ranking may NOT
    be re-run as a re-run.** Re-opening requires **new data** (`S25`, a genuine point-in-time
    sector map — TICKERS is today's classification and is the one non-point-in-time input in the
    panel) or **a materially different construction** (`S15`, sector-relative on the **value
    theme alone**, never tested at all). Both ledger rows are now scoped rather than blank.
    **Nothing here touches the sector column's ACCEPTED use for the `max_sector_w` concentration
    cap — a risk control, not a re-ranking.**
  * **Equity `N` 149 → 151** (one hypothesis, two weightings, no grid), √(2·ln 151) = 3.1677.
    **ADOPTS NOTHING and `CONFIG.sector_neutral` is untouched at `false`.** Four of five
    pre-registered expectations were RIGHT and one split — unusual here, and the stated reasoning
    held: the corrected window is roughly the void panel's late portion, where sector-neutral
    already lost on both metrics.
- **THE EXIT RULE WAS RACED AND NOTHING BEATS THE INCUMBENT — BUT NEVER SELLING COSTS
  10.89pp/yr, AND THAT CONFIRMS S22 RATHER THAN CONTRADICTING IT
  (2026-08-11, session 19, `S23`).** The live book holds a name until it falls out of the top 50,
  min-hold 2, and that exit had never been tested against an alternative. One buy rule and an
  identical `min_hold` across every arm, so only the exit differs.
  `PREREG_s23_exit_rule.md` was committed **alone at `6a73485`**, a strict ancestor of the
  measurement commit, with **both TP/SL pairs named from published convention and NO grid swept** —
  `sweep_hold_params` already sweeps `trailing_stop` over four values and picking its best cell is
  the in-search +8.43%/yr → locked hold-out −0.04%/yr failure already paid for.
  * **NO CHALLENGER BEATS THE INCUMBENT.** Fair-value point -0.13pp/yr
    (HAC *t* -0.368), fair-value lens band
    +0.37pp (+0.866),
    O'Neil +25/−8 -0.21pp (-0.396),
    2:1 +20/−10 -0.13pp (-0.254) —
    **all under 0.4pp/yr in either direction on 69 paired periods, net of costs**; per-arm placebo floors A1_FV_POINT 1.9181, A2_FV_LENSBAND 1.8518, A3_TPSL_ONEIL 2.0260, A4_TPSL_2TO1 2.0489, C_NEVER 2.5543.
    **THREE OF THE FOUR FLIP SIGN BETWEEN HALVES**, and the only arm with a positive full-sample
    difference is exactly the one that fails the both-halves requirement. Session 7's LOO pattern
    again.
  * **THE CONTROL IS THE ONE MEASURABLE EFFECT AND IT IS LARGE: never selling costs
    10.89pp/yr at HAC *t* -3.801**, the book grows to
    **417 names** and alpha vs the equal-weighted universe collapses
    **15.48% → 3.37%**.
    **THIS DOES NOT CONTRADICT S22, AND READING IT THAT WAY IS THE MAIN WAY IT GETS MISUSED.**
    S22 measured a cohort selected on ONE date beating the universe for ~8 quarters; a never-sell
    book keeps **buying**, so it accumulates cohorts of every age and over 69 rebalances converges
    on a 417-name slice of the universe. **Dilution, not friction** —
    its gross 20.61% barely differs from its net because it never
    trades. *"The edge persists" and "hold forever" are different claims, and only the first is
    true.*
  * **THE LEVELS ARE NOT A NEW HEADLINE.** `_backtest_hold` is the concentrated top-25→50 book
    **B17** already calls the noisiest number in the results file. S23 quotes **differences
    between exit rules** on that object; the incumbent's own CAGR is not a claim it makes.
  * **THREE DEFECTS FOUND AND FIXED, all reported in their own right.** (a) **`build_valuation_panel`
    still carried the B6 per-ticker tail** — measured on the same 25 names it gave **110 rebalance
    dates from 1998-12-31** (the inverted-universe window) against the corrected **69 from
    2009-01-15**; **any prior `run_calibration` conclusion should be re-run before it is quoted.**
    (b) **The point-in-time valuation was fetching LIVE Yahoo prices** through `_resolve_beta`'s
    corroboration rung — valuing 1999 with a beta regressed on 2021-2026 returns — **157 calls per
    1,122 rows**; there is now an explicit offline mode and the build **asserts zero network
    calls**. (c) **`_backtest_hold` extracted a column once per NAME instead of once per date**,
    114,774 extractions per call, each deep-copying the panel's `.attrs`: **61 of 70 seconds**,
    fixed 15.6s → 2.7s and **proved bit-identical over 1,818 leaves**.
  * **Equity `N` 143 → 149.** **ADOPTS NOTHING** — adoption is a **VINTAGE EVENT** that resets the
    five-year clock for zero statistical gain, and is Don's call on this evidence. Whether the
    stop-loss or the take-profit does the damage is recorded **UNRESOLVED**, because the two
    arms differ in both legs at once and adding a one-legged arm now is the grid search the
    register forbids.
- **THE EDGE DOES NOT DECAY OVER TWO YEARS, THE LONG-SHORT SPREAD DOES, AND A HOT NAME LASTS
  ONE REBALANCE (2026-08-10, session 18, `S22`).** Every HEADLINE figure the project publishes is
  measured at a single 63-day forward window because `build_fundamental_panel` computes one
  `fwd_ret` and the deployed rebalance equals it — an inherited default, never a measured optimum.
  **CORRECTION TO S22's OWN REGISTER, recorded because the register is left unedited: it claimed
  "nobody has ever asked what the composite predicts at 6 months, a year, or two years", and that
  is FALSE.** `BACKTEST_RESULTS.json` has always carried a `per_horizon` block at 63/252/756 —
  but it reports **IC and weight vectors only** (no alpha, no long-short, no decile structure), and
  `run_backtests` sets `rb = max(rebalance_days, H)` so the **rebalance period moves with the
  horizon**: 69 dates at 63d, **18** at 252d, **6** at 756d, on universes of 2,531 / 2,492 / 2,206
  names. That is exactly the confound S22 was designed to remove, and six dates support no
  inference. **It does CORROBORATE the finding, which is why it is reported: that block's
  out-of-sample IC rises monotonically with horizon, 0.038990 → 0.058241 → 0.097671 — the project
  has been shipping evidence its signal predicts better at long horizons, in its own results file,
  unread.** Direction only; the IC definitions and date sets differ. Eight horizons (1–8
  quarters) were scored from **ONE** panel build, because the grid end is `len(cal) − horizon` and a
  build per horizon would vary the horizon **and** the date set **and** the cross-sections together.
  `PREREG_s22_term_structure.md` was committed **alone at `6b187dd`**, a strict git ancestor of the
  measurement commit.
  * **VERDICT CONSTANT-RATE, by the rule fixed in advance: `R(8) = 6.195` against a ≥6.0 bar.
    Annualized top-decile alpha is ESSENTIALLY FLAT from three months to two years — +6.59%,
    +6.67%, +6.03%, +6.14%, +6.23%, +5.74%, +5.07%, +5.10%** — and cumulative alpha reaches
    **+10.20%** at eight quarters. **The alpha HAC *t* never drops below 3.16** at the
    overlap-corrected lag (7 at two years), so this is not a signal surviving on widened error bars.
    Median rank IC **rises** with horizon (+0.034 → ~+0.072), an independent route to the same
    finding that never touches the decile machinery.
  * **THE SECOND HALF OF THE HEADLINE IS THE ONE THAT CONSTRAINS QUOTING: THE LONG-SHORT SPREAD
    DECAYS AND ITS SIGNIFICANCE COLLAPSES — HAC *t* 2.7167 → 0.6846**, cumulative spread peaking at
    Q5 (+7.11%) then falling. **The persistence lives entirely in the LONG leg.** That is fortunate
    rather than damaging — the shipped product is a **long-only hot list**, so the leg that persists
    is the one users receive — but **the long-short research statistic and the product statistic
    DIVERGE with horizon, and the record has been quoting them side by side.** Nobody may quote a
    long-short figure beyond about a year.
  * **REPORTED BECAUSE IT CUTS AGAINST THE VERDICT: the classification clears its bar NARROWLY
    (6.195 vs 6.0) and DOES NOT REPLICATE ACROSS HALVES** — early **8.559** (super-linear), late
    **5.470** (would read INTERMEDIATE). Both halves agree in **sign** and both still show alpha
    accruing at two years, so **the PERSISTENCE replicates and the LABEL does not.** `R(8)` is a
    ratio whose denominator is one noisy quarter; the flat annualized-alpha column is the robust
    reading of the same data.
  * **TENURE: the top decile turns over almost completely every quarter.** 7,286 spells over 1,895
    names at a median decile size of 156. **Kaplan–Meier median spell = ONE rebalance (~3 months)**,
    naive median agrees at 1.0, **70.6% of spells last exactly one**, max 19. **One-period retention
    36.6%, INSIDE the 20–50% band pre-committed from the shipped 261%/yr turnover** — so the tenure
    measurement and the cost model describe the same book and the registered BUG branch did not
    fire. **Re-entry is the norm:** persistence-with-gaps plateaus at ~19–24% out to eight
    rebalances instead of decaying to zero, and **74% of names have more than one spell.**
    **Small caps stay LONGEST** (mean 1.788 vs large 1.224), the opposite of the pre-registration.
  * **THE DEFENSIBLE PRODUCT SENTENCE, and it must travel with its caveats:** *"the top decile beat
    the equal-weighted universe by about 6.6% annualized over the next three months and was still
    ahead by about 5.1% annualized two years later, even though a given name typically stays in the
    top decile for only one quarterly rebalance"* — **long-only, gross of costs, on the same single
    in-sample panel every other published figure comes from, not a forward test.** Display is the
    **web lane's**.
  * **WHAT IT DOES NOT SAY, and this is the most likely misuse: it is NOT a finding that the book
    should rebalance less often.** `cum_alpha(H)` is the buy-and-hold return of the cohort selected
    on ONE date; a quarterly book **re-selects and compounds fresh selections**. Those are different
    claims and only the first is measured. It does make the second **worth testing** — the book pays
    261%/yr turnover to harvest an edge still accruing at two years — but **that is S23's, needs its
    own register, and adopting it is a VINTAGE EVENT that resets the five-year clock for zero
    statistical gain.**
  * **X7's floors were NOT quoted outside the one configuration they were calibrated in** (h63, 69
    dates, lag 1) — `n`, the overlap and the HAC lag all change with the horizon, and comparing
    across configurations is the error the record already paid for twice.
  * **A per-horizon placebo was built because X7's floors do not transfer** (200 draws, fixed weights, no CPCV — a DIFFERENT and less conservative null, labelled `fixed_weights_null`, whose percentiles may never be compared with 2.2837): **8 of 8 horizons clear their own alpha floor, 4 of 8 clear their own long-short floor.** Free by-product, no verdict: the same null at h63 **without** CPCV gives a long-short p95 of **1.7494** against session 10's **2.2837** **with** selection in the loop, so **putting selection in the loop raises the 95th-percentile floor by +0.5343 of a *t*.** **Do not conflate that with the figure already in this file:** it is the shift in the **p95 over all draws**, NOT X7's post-hoc **~+1.4 mean long-short *t* among the 27% of noise draws that actually adopted**. Same direction, different quantities — a large effect on a fifth of the draws moves a 95th percentile by far less than the effect itself.
  * **CONTROLS ALL EXACT: C0 `max|fwd_ret − fwd_ret_h63| = 0.000e+00` over all 113,945 rows**; C1
    reproduces the record to the digit on a **fresh** build (alpha 0.071741, LS naive 2.836064, HAC
    2.619912, alpha HAC 4.376230, monotonicity −0.890909, EW +0.181371), so the known `insider`
    nondeterminism did not bite; **C2 dates observable 69, 68, 67, 66, 65, 64, 63, 62 — exactly one
    rebalance date lost per extra quarter**, censoring removing a **suffix**, never a scatter.
    **The defect named in advance and avoided: right-censoring is NOT delisting** — a last-price
    fallback on a censored window would return a shorter realized return labelled as a long-horizon
    one, for the most recent dates specifically. Pinned from both sides.
  * **Equity `N` 135 → 143** (eight arms; tenure, the placebo and the half-splits charged at zero). **Deflated Sharpe 0.8504 → 0.8436955925493782, √(2·ln 143) = 3.1505**, and `BACKTEST_RESULTS.json` was re-run from a clean tree so the artifact matches the record (16 of 1,217 leaves moved — five the DSR chain, four provenance, seven last-digit float; every headline bit-identical, `errors` empty, `cpcv.adopt` still false).
    **THE EXPECTATIONS WERE WRONG ON BOTH HEADLINE QUESTIONS** — SATURATING predicted at 60/40 and
    the answer is CONSTANT-RATE; large-cap tenure predicted longer at 55/45 and small is longest;
    all eight incremental quarters positive against a prediction they would not be beyond k=4.
- **THE LIVE PRODUCT SCORES A FOUR-THEME BOOK, AND WHAT THAT COSTS IS NOW MEASURED: −1.31pp/yr,
  NOT SEPARABLE FROM ZERO — BUT THE LIVE BOOK FAILS THE CALIBRATED LONG-SHORT FLOOR
  (2026-08-10, session 17, `V2G`).** The greeks lane measured over 500 served rows that three of
  the seven weighted themes reach **no live score** — `insider` is **constant** (500/500 non-null,
  one distinct value, so `zscore` returns all-NaN), `capital_discipline` and `institutional` are
  **absent** (0/500). That is **0.375 of 0.875 = 42.9% of the weight mass**, so the hot list is a
  **four-theme book** (`value`, `quality`, `momentum`, `size`) wearing the weights of a
  seven-theme one. That lane declined to price it; this register did.
  `PREREG_v2g_live_theme_cost.md` was committed **alone at `6d8750a`** before the measurement code
  existed.
  * **VERDICT IMMATERIAL, BY THE RULE FIXED IN ADVANCE: top-decile alpha +7.17% → +5.86%,
    Δ −1.3133pp against a −1.95pp bar, paired HAC t −1.4040 over 69 paired dates.** Building live
    sources for the dead themes is **a nice-to-have, not the project's highest-value work**.
  * **THE POWER CAVEAT IS PART OF THE VERDICT, NOT A FOOTNOTE.** The HAC se of the paired annual
    difference is 0.9354pp, so the design resolves **1.8708pp** at |t| = 2 — well matched to its
    own bar, which is what makes the null worth anything — but power against a **true** 1.95pp gap
    is **55.0%**. *IMMATERIAL means the cost could not be separated from zero at roughly a coin
    flip's power. It does NOT mean the cost was shown to be small.*
  * **THE SECOND FINDING IS THE MORE SERIOUS ONE, and the register asked for it separately: the
    live four-theme book does NOT clear the calibrated long-short floor** — HAC t **1.8811** vs
    **2.2837** (naive 2.0044 vs 2.1437), where the deployed book clears at 2.6199. It **does**
    clear the top-decile alpha floor (**3.2087** vs 2.2913), and since the shipped product is a
    **long-only hot list** that is the product-relevant statistic. So the long-only book users
    receive stays demonstrable; the long-short figure quoted beside it does not.
  * **AN IMMATERIAL ALPHA COST IS NOT A FINDING THAT THE LIVE ABSENCE IS ACCEPTABLE.** The live
    product computes a **different composite** from the one every published figure is measured
    on — the same class of defect **B7** exists to prevent. Either build the sources or quote the
    headline for the book actually computed. **Owner: screener lane**, not the edge lane.
  * **THE RESTRICTED ARM IS THE LIVE BOOK, PROVED NOT ASSUMED: `max|dev| = 0.000e+00` over all
    113,945 rows**, for both the absent case and the constant-`insider` case, because `composite`
    renormalises by the **present-weight mass**. Harness control: the incumbent arm reproduces the
    record to the digit — alpha 0.071741423321, LS naive t 2.8361, HAC t 2.6199, alpha HAC t
    4.3762, monotonicity −0.891, equal-weight benchmark +18.137%.
  * **Both halves agree in sign and neither is significant** (early −1.14pp, late −1.48pp) — a
    better stability profile than session 7's LOO arms. **Reported because it cuts against the
    verdict:** the late-half **long-short** difference is −5.63pp/yr at HAC t **−2.0639**, which
    crosses the conventional bar; not the pre-registered primary statistic, uncalibrated, one of
    six cells.
  * **EXPLORATORY, NO VERDICT** (session 7's rule: a full-sample ablation arm is not a finding):
    dropping `institutional` is the **only** one negative in both halves (−1.41% full), so **13F is
    the source to build first**; dropping `capital_discipline` is **positive in both halves**
    (+1.37%) despite holding the second-strongest panel IC (+2.76) — **X3's lesson restated, theme
    IC does not predict marginal contribution**; dropping `insider` flips sign between halves.
  * **NO CALIBRATED FLOOR EXISTS FOR A PAIRED WITHIN-PANEL DIFFERENCE** — X7 and session 10
    calibrate *levels*. The 2.0 used here is conventional and is labelled uncalibrated everywhere
    it appears. `quantile_backtest(..., return_series=True)` now returns the per-period draws
    (opt-in; default payloads bit-identical) so future paired tests use the **shipped** arithmetic.
    **Equity `N` 131 → 135, Deflated Sharpe 0.8539 → 0.8504, √(2·ln 135) = 3.1322.**
- **THE "8% CAP VIOLATION" NEVER EXISTED — `PT-SPLIT` IS CLOSED, AND THE DIAGNOSIS THIS FILE
  CARRIED FOR TWO SESSIONS WAS WRONG (2026-08-10, session 16).** The bullets below say the
  sandbox engine holds *"10 names, equal-weighted at 10% each — which the contract's own 8% cap
  forbids"*. **It forbids no such thing.** `valquo_index.build_index` sets
  `cap = max(MAX_WEIGHT, 1/len(picks))` with a comment saying why — **ten names at 8% sum to
  80%**, so on a small book the cap must relax to equal weight or the redistribution loop never
  terminates — and the payload has always self-reported `effective_max_weight`. **The weights
  were correct for the book they described.**
  * **THE REAL DIVERGENCE IS BOOK SIZE, AND IT IS ONE CONSTRUCTION FED TWO INPUTS.**
    `n = max(MIN_NAMES, round(len(large) × TOP_DECILE))` with `MIN_NAMES = 10`, so a 10-name book
    means the eligible large-cap tier held **fewer than 100 names**; the published 86 implies a
    tier of ~860. **`/admin/run-paper-track` reads `data/valquo_index.json` when it exists and
    SILENTLY REBUILDS FROM THE STORE'S LATEST SCAN when it does not** — and that scan is a top-N
    hot list. The engine was never pointed at a different strategy; it was handed a truncated one
    with no label. That is how `PT-OUTBOUND` shipped an engine figure as an Index claim.
  * **WHY THE WRONG FRAMING WAS EXPENSIVE, not merely untidy: the fix it implies is "lower a
    cap", and the cap was already right.** The actual defect would have survived the repair.
    Same lesson as the stale-figure and wrong-file-name corrections elsewhere in this file —
    **re-derive a diagnosis from the code before acting on a repeated one.**
  * **RESOLVED BOTH WAYS AT ONCE, per Don's "no third state":** `paper_track.seed_book` now
    **refuses** to seed a book that is not the Index (**≥ `CONTRACT_MIN_POSITIONS` = 50 names AND
    the 8% cap actually binding**), loudly and non-destructively — it never liquidates, because
    doing so on a conformance rule would be worse than the split. `experiment=True` is the only
    other door and it **stamps every holding row** (on the row, not in a return value: the old
    code *did* label its fallback and no surface rendered the label). The **four recorded days
    are registered in `PAPER_TRACK_CONTRACT.md` §5b** as a separate experiment, **kept not
    deleted** — its *fills* are real evidence about execution, its *return series* is evidence
    about nothing the contract binds.
  * **STILL OPEN, and it is the app lane's:** this stops the engine *adding* to a wrong book; it
    does not make it start recording the right one. That needs a conforming
    `data/valquo_index.json` on the Render disk when the cycle runs. **No vintage opened or
    closed** — the engine's series was never the bound series.
- **THE FORWARD OPTIONS BOOK WAS RUNNING EXIT LEVELS NO BACKTEST DESCRIBES, AND HELD A NAME THE
  ALERT ITSELF REFUSED (2026-08-10, session 16, `PT-BUG12`).** Both routed in by the options-bot
  lane off the first three REAL fills, both fixed in `paper_track.py`, all expected values
  pre-committed in `PREREG_session16_paper_track_repair.md` before any code changed.
  * **`_place_entry` anchors target/stop to the SUBMIT price and `mark_open` overwrote
    `entry_premium` with the FILL without recomputing either.** Systematic, not occasional:
    `auto-scan.yml` runs the cycle after the close, so the limit comes from a post-close quote and
    the day order fills at the next open. **2 of 3 open positions were off spec** (TGT +150.7%
    target against +100%; MET −46.7% stop against −50%). Levels now derive from the fill on the
    **alert's own** policy, and an idempotent repair pass fixes already-open rows every cycle.
    **All five pre-committed criteria held exactly** — TGT 8.90 → 7.1000 / 2.225 → 1.7750, MET
    9.80 → 9.2000 / 2.450 → 2.3000, **ETN bit-identical** because its fill equalled its limit.
  * **THE REPAIR RUNS IN THE FLATTERING DIRECTION AND THAT MUST TRAVEL WITH IT.** The bug made
    targets harder and stops tighter; correcting it makes them easier and looser. Right fix
    either way — the levels were wrong against the specification — but **"we fixed a bug and the
    book improved" is the easiest way for a forward test to flatter itself.** Concretely: **MET
    sat 10.2% above a stop level no backtest ever specified**, days from recording a stop-out the
    strategy under test would not have taken.
  * **A REPAIR MAY NOT EXECUTE A TRADE.** If a corrected level is already crossed, the write is
    **deferred and reported**, never auto-exited. Untaken today (no row crosses), pinned by test.
  * **`_eligible` never read `features.sizing`**, so ETN was bought on `skip: true` / *"one
    contract costs $1,610, above the $1,000 budget"* and became the **largest position in the
    book**. The veto is now honoured; **the sizing QUANTITY deliberately is not** (that would
    change construction), pinned as a non-change. **The open ETN position is NOT unwound** —
    that gate applies to new entries, and closing a live position to tidy the record is a trade
    decision.
  * **A THIRD DEFECT, same family, found while fixing the first:** the resume branch called
    `_exit_policy` on a `paper_option_orders` row, and **that table has no `features` column**, so
    the policy silently collapsed to the DEFAULTS. **Audit B5c's own comment claims that branch
    "rebuilds … the exit policy the same way the fresh path does" — the fresh path reads the
    ALERT.** It has never fired only because all three live alerts use the default policy. **A
    defect neutralised by a coincidence in the data is not handled**, so it is pinned with a
    policy that differs.
  * `options_summary.level_conformance` now reports off-spec live rows **read-only on every
    request** — it stays after the fix precisely because the first time this book was inspected,
    2 of 3 positions were off spec and nothing anywhere said so.
- **V1 SHADOW VINTAGES IS REGISTERED, BLIND, WITH NO MEASUREMENT — AND ITS POWER TABLE IS THE
  FINDING (2026-08-10, session 16).** Rule 6 (below) says an adopted change resets the whole
  five-year clock and buys nothing statistically — which, alone, means **the model can never be
  improved again without paying five years.** V1 is the escape: the closing vintage keeps being
  scored in shadow on the same dates and the two books are compared **PAIRED**, so the market
  risk that dominates a vs-SPY test **cancels**.
  * **THE GAIN IS REAL AND THE LIMIT IS STRUCTURAL, both computed before any pair exists.** At a
    between-book tracking error of 2.0 pp/yr the 60-month detectable difference is **3.34 pp/yr
    against the vs-SPY meter's 19.01** — four-fold. **But σ is small exactly when the adoption
    changed little, and an adoption big enough to matter raises σ.** No design escapes that. **A
    shadow pair that has not crossed is the EXPECTED outcome and is NOT evidence the adoption was
    worthless** — `verdict()` carries that sentence in its own output.
  * **THE CONTROL IS EXACT:** fed the contract meter's own 11.40 pp/yr TE it reproduces
    **σ 3.9847** and **~19 pp/yr at 60 months** to the digit, because it **imports**
    `track_meter.boundary` rather than re-implementing it. ρ and α are imported too and a test
    fails if they are ever copied — one boundary function in the project.
  * **BLINDER THAN ANY PREVIOUS REGISTER HERE: no vintage pair exists.** Vintage 2 opened
    2026-08-10 with no successor, so no parameter could have been tuned to a comparison even in
    principle. Vintage 2's parameters are **pinned now, in a tracked file** (`params_id
    0060c5ef3dda`), so the shadow runs a **snapshot, never a reconstruction**.
  * **No sign branch** (AST-pinned; flipping a whole series flips the verdict and moves nothing
    else), so **HARMED is exactly as reachable as CONFIRMED-LIVE**. **Research-only and fenced off
    every public surface by a test, BEFORE it has numbers to leak** — `PT-OUTBOUND` is why that
    fence is built in advance. **It does not weaken Rule 6:** it measures the price of an
    adoption, it does not refund it.
  * `valuation/edge/shadow_vintage.py`, `PREREG_v1_shadow_vintages.md`, 26 tests.
    **Equity `N` stays 131** (infra `n = 1`); the first shadow PAIR is charged when it opens.
- **AMENDMENT 1: RUN #1 IS VOID, RUN #2 IS THE LIVE TEST, AND THE PROJECT NOW HAS A VINTAGE
  RULE (2026-08-09, session 15).** Don voided run #1 (inception 2026-07-30, ~6 days, 2 rows)
  because it measured a model that has since materially changed — growth-input fix, score fix,
  universe rebuild. **Run #2: inception 2026-08-10, gate 2027-02-10, verdict 2031-08-10, with
  ZERO accrued days.** Recorded openly in `PAPER_TRACK_CONTRACT.md` **§5a**, never as a silent
  edit, and nothing above §5a was deleted.
  * **THE VINTAGE RULE.** Any **ADOPTED** change to scoring, weights or construction closes the
    current vintage and opens the next ("adopted" = ships in the live scoring path).
    **Rebalancing under unchanged rules is NOT a vintage event.** Each vintage carries its own
    clock; **the gate and the meter attach to the CURRENT vintage**, so a verdict is a statement
    *about a vintage* and must name it. The cross-vintage chain is kept and published as **"the
    system as operated"** — the honest answer to what a user would have experienced — and is
    **explicitly not the object of a verdict**, because it mixes models.
  * **RULE 6 IS THE BRAKE, AND IT IS THE PART TO REMEMBER BEFORE SHIPPING A SCORING CHANGE: a
    vintage change resets the whole accrued clock and buys nothing statistically.** §2's
    arithmetic is unchanged — 60 months at 49% power. A vintage that closes at month 30 has
    spent 30 months for no evidence.
  * **THE AMENDMENT MOVED THE CLOCK, NOT THE STATISTICS.** σ 3.9847, ρ 3, α 0.05, the cost drag
    and the SUPPORTED/UNSUPPORTED bars are **all unchanged**, so §3's *whole-run* void clause
    (which triggers on a threshold change) is not engaged; only the window-void clause is.
    Pinned by `test_the_amendment_moved_the_clock_and_not_the_statistics`. **σ was re-checked
    against the changed model rather than assumed to survive it: the current backtest still gives
    SPY excess +9.99%/yr at implied TE 11.401 pp/yr and IR 0.8759/yr** — the figures σ came from.
  * **THE DISCLOSURE THAT MUST TRAVEL WITH IT: the voided window was KNOWN to be −2.85pp.**
    Discarding a stretch that went against the strategy is the flattering direction. Three
    answers, each checkable: the cause (a model change) is independent of the outcome and its
    clause pre-existed the run; **run #2 accrues ZERO days**, so no window's sign could inform
    the new start date; and the voided rows are **kept**, visible in `as_operated()`. §5a
    forbids the thing this must never become — voiding a vintage for a change *chosen* after
    seeing the vintage go badly.
  * **Equity `N` 130 → 131** (`PT-AMEND1`), **Deflated Sharpe 0.8547 → 0.8539,
    √(2·ln 131) = 3.1226**, and `BACKTEST_RESULTS.json` was re-run from a clean tree so the
    artifact matches (14 leaves moved, five the DSR chain, four provenance, five 0.000% float;
    every headline bit-identical). Charged because void-and-restart is a degree of freedom: each
    vintage is another chance at the same hypothesis.
  * **THE METER NOW HAS A CALLER (session 15's own item).** `track_meter.detail()` ships as
    `summary()["contract_track"]` on **`/api/track`** — before this it was a tested library
    nothing called. It names **every missing trading day** on every request, is **not vacuously
    green** before the vintage starts (`recording_ok: None`, not `true`), is labelled a different
    object from the sandbox engine, and is **reconciled against `index_track.vs_spy_claim()`**,
    the one authority for a vs-SPY claim (measured −2.8468 vs −2.8468).
  * **`PT-WRITER` IS REPORTED CLOSED AND I COULD NOT VERIFY IT — the gate stays `pending`.** The
    writer is described as Cowork task `valquo-daily-track-write`, weekdays 20:01. **No such task
    is in this machine's Task Scheduler** (413 enumerate; three Valquo tasks, none this one) and
    the name is nowhere in the repo — but **no run was due yet either**, so that is evidence, not
    proof. **THE TEST IS MECHANICAL: inception 2026-08-10 is day 0, the first row due is
    2026-08-11, so from 2026-08-12 `/api/track` answers it.** Read that block before doing
    anything else with the track.
- **THE PAPER-TRACK CONTRACT IS SIGNED AND IN FORCE — OPTION E, 2026-08-09 (session 14). THE
  PROJECT NOW HAS A PRE-REGISTERED FORWARD TEST, AND TWO RECORDERS THAT DISAGREE ABOUT WHAT IT
  IS RECORDING.** Don signed: keep inception **2026-07-30** including the accrued negative days,
  **6-month operational gate (2027-01-30)**, **60-month verdict vs SPY (2031-07-30)**, the
  ~36-month costed equal-weight-basket secondary *if it is ever built*, plus a pre-registered
  anytime-valid evidence meter first rendered at the gate and monthly thereafter, whatever it
  says. `PAPER_TRACK_CONTRACT.md` §5 is the register; §6 freezes the meter.
  * **THE REGISTER BINDS THE PUBLISHED VALQUO INDEX, NOT THE SANDBOX ENGINE — because they are
    recording DIFFERENT BOOKS.** This is the session's material finding. The Index
    (`data/valquo_track.json` + `valquo_track_history.csv`, read by `index_track.py`) is **86
    names, score-weighted, max weight 2.3%, inception 2026-07-30**. The Tradier sandbox engine
    (`paper_index_track` → `data_export/paper_track_*`) is **10 names, equal-weighted at 10%
    each — which the contract's own 8% cap forbids — inception 2026-08-03.** They are not one
    track recorded twice. **Never quote an engine figure as evidence under the contract**, and
    a B7-class split stands until the engine is re-pointed or its outputs are labelled a
    different object everywhere they surface.
  * **~~The engine has never been fed (0 rows)~~ — CORRECTED 2026-08-09 (session 14): THAT WAS
    MEASURED ON THE LOCAL DEV DATABASE.** On the live Render service the engine holds **4 index
    days, 10 holdings and 3 paper option orders**, and the weekly `track-backup` Action has been
    committing them to `data_export/` all along. The rest of this bullet's session-13 findings
    stand; this one did not.
  * **THE REAL BLOCKER IS THAT NOTHING IN THIS REPOSITORY WRITES THE BOUND SERIES.** Not a
    scheduler fault, not a crash, not a conditional write — **there is no writer.**
    `index_track.py` only ever *reads* `valquo_track_history.csv`; the rows are produced by hand
    on the Cowork side, which is exactly why **four of six due rows are missing (33.3%
    coverage)**. **The operational gate cannot pass until an automated daily write exists**, and
    that is the Cowork lane's. `valuation/edge/track_meter.py:gap_report` now names every
    missing day so the failure is dated rather than discovered at the gate.
  * **THE METER IS HONEST AND WEAK, AND THE SECOND HALF MUST TRAVEL WITH THE FIRST.** A Robbins
    normal-mixture anytime-valid confidence sequence, σ **3.9847 pp/month** (the backtest's own
    11.40pp/yr tracking error inflated by R9's AR(1) design effect **1.4661**), **ρ = 3**,
    **α = 0.05 two-sided**, cost drag **0.14529 pp/month**. Measured over 40k AR(1) paths:
    false-crossing **1.5%** against a nominal 5%, but **power at the backtested +9.99%/yr edge is
    just 13.3% by 60 months and 30.7% by 120**, needing **~19 pp/yr to cross at 60 months**.
    **A meter that has not crossed is the EXPECTED outcome and is NOT evidence against the
    strategy.** The AR(1) inflation is load-bearing, not decoration: without it the false-crossing
    rate is **6.7%**, i.e. the naive version breaks its own guarantee. **σ may never be revised
    downward** — at 1.5× the assumed volatility the false-crossing rate is **20%**.
  * **GENUINELY BLIND, which is the whole point:** at the signing commit the bound series held
    **two daily rows and ZERO complete calendar months**, so no meter parameter could have been
    tuned to the outcome even in principle. Pinned by `tests/test_track_meter.py` (20 tests,
    every constant a literal), including one that fails if the AR(1) inflation is removed and one
    that pins the render decision as invariant to flipping the sign of the entire series.
  * **THE DATED AUTO-FLIP IS CLOSED, BY THE ENGINE LANE, THE SAME DAY (`126c137`).**
    `MIN_LIVE_DAYS = 60` no longer promotes the track on its own. `index_track.gate_state()`
    parses the **`Operational gate passed` row of `PAPER_TRACK_CONTRACT.md` §5** on every
    request, and `headline` requires **both** the day count **and** that row — so at any day
    count, indefinitely, the headline stays `"backtested"` until the contract says otherwise.
    **Every unrecognised outcome is not-passed** (missing file, missing row, malformed table,
    two rows disagreeing), so the failure direction is "still backtested", never "now live".
    Session 14 filled the row as `pending` and verified the parser returns `passed: false`.
    **On gate day, set that ONE row and nothing else anywhere:**
    `| Operational gate passed | YES - 2027-01-30 |`.
  * **Equity `N` 129 → 130** (the register is charged as a trial; understating `N` overstates
    significance). **Deflated Sharpe 0.8556 → 0.8547, √(2·ln 130) = 3.1201**, and
    `BACKTEST_RESULTS.json` was re-run so the artifact matches the record rather than going
    stale on the denominator again.
- **THE FORWARD PAPER TRACK CANNOT DELIVER A VERDICT FOR ~5 YEARS (2026-08-08, session 13).
  Roadmap #12's status line was wrong.** That item says the track is built and *"what remains is
  elapsed time and reading the track, not building it."* The arithmetic below is why that is
  false, and it is unchanged by the session-14 bullet above.
  * **THE ARITHMETIC IS THE FINDING, and it is not escapable by choosing a better statistic.**
    From `benchmarks.spy` the top decile beats SPY by **+9.99%/yr at a tracking error of
    11.4pp/yr** — an **information ratio of 0.88/yr**, and that is the IN-SAMPLE figure. Since
    t grows as √time, **t = 2.0 arrives at 5.2 years** (7.6 once R9's lag-1 +0.189 is applied as
    an n_eff haircut). **At 12 months the power is 18% and the minimum detectable edge is
    +34pp/yr — over three times what the project claims.** If the strategy is exactly as good as
    backtested, a one-year forward test reports "no evidence" **82% of the time**.
  * **REFUTATION TAKES EXACTLY AS LONG AS CONFIRMATION** — the test is symmetric. There is no
    horizon at which bad news is cheap. Nobody may say a short track disproved this either.
  * **THE TRACK CANNOT PRODUCE THE SERIES A VERDICT NEEDS, IN EITHER SOURCE.**
    `paper_index_track` stores a **snapshot of currently-open holdings** measured from each
    name's own entry, not a chained series — differencing two points is not a monthly return, and
    a departed name stops contributing. `paper_track.py:735-740` says so, and says chaining
    closed stints in *"is a construction change, not a bug fix, and was not made."* The Cowork
    file chains correctly but is **missing days** (two rows exist where five were due). **The
    verdict is not computable at any horizon until one source produces a chained series.**
    **PARTLY CLOSED 2026-08-09 (session 14): the snapshot objection was about the ENGINE, and
    the engine is not the bound source.** The Index series stores cumulative-since-inception
    levels, and `track_meter.monthly_excess` chains them into calendar months — a construction
    **robust to an interior missing day**, since a month needs only its two endpoints (pinned by
    `test_an_interior_missing_day_does_not_corrupt_a_monthly_return`). A month whose *month-end*
    mark is missing or >3 trading days stale is **voided**, never silently averaged over. **What
    remains is the missing writer, not the construction.**
  * ~~**THE INCEPTION DATE EXISTS ONLY IN A GITIGNORED FILE.**~~ **CLOSED 2026-08-09 (session
    14).** `2026-07-30` is now in **tracked** files — `PAPER_TRACK_CONTRACT.md` §5 and
    `track_meter.INCEPTION`, pinned by a test. The pre-registration can now be produced by
    anyone with the repo, which is what makes it one.
  * **THE SITE PROMOTES THE TRACK TO ITS HEADLINE BY ITSELF, ON A FIXED DATE, WITH NO APPROVAL
    STEP — THE ONE ITEM HERE WITH A DEADLINE.** `index_track.py:223-224` is
    `thin = days < MIN_LIVE_DAYS` then `headline = "backtested" if thin else "live"`, and
    `MIN_LIVE_DAYS = 60`. At day 60 the *"too early to judge"* pill (`index.html:114`)
    disappears and the headline flips to **live**. **The track is on day 5: this fires ~55
    trading days out, late October 2026, at 13% power (minimum detectable edge +49pp/yr).** The
    **CLOSED 2026-08-09 (`126c137`, engine lane) — see the session-14 bullet above: the flip now
    requires the contract's `Operational gate passed` row as well as the day count, and that row
    reads `pending`.** The rest of this sub-bullet is the record of what the defect was. The
    constant was never pre-committed, does not derive from power, and disagrees 2× with
    `paper_track.MIN_DAYS_FOR_MEANING = 126` governing the same track. ~~Both sit in
    `valuation/screener/index_track.py` — outside the edge lane; it needs assigning.~~
    **CORRECTED 2026-08-09 (session 14): THEY SIT IN DIFFERENT FILES AND DIFFERENT LANES, and
    this sentence was the one assigning the work, so the wrong file name pointed the fix at the
    wrong lane.** `MIN_LIVE_DAYS` is `valuation/screener/index_track.py:44` (engine lane, fixed);
    `MIN_DAYS_FOR_MEANING` is **`valuation/edge/paper_track.py:70`** — the edge lane's, and it
    was a **second ungated door**: `hero` falls back to `paper_track.index_summary()` when the
    Cowork files are absent, which is the fresh-deploy case, and that read a pure day count.
    **Both are now gated on the contract's one row; `index_summary` delegates to
    `index_track.gate_state()` rather than parsing the contract twice, and fails closed.**
  * **STATE, as of this bullet: the track is BEHIND — inception 2026-07-30, five days, Valquo
    +0.78% vs SPY +3.62%, excess −2.85pp.** That is −1.8 SD of a five-day window (p ≈ 0.08),
    i.e. an ordinary bad week that means nothing about the strategy — **but it means the start
    date is being chosen with the sign of the accrued period known**, so discarding those days
    is the flattering direction. `PAPER_TRACK_CONTRACT.md` is a **DRAFT awaiting Don**; zero
    trial cost, equity `N` stays 129, and the trial is charged on sign-off.
- **X8 REPLICATED ON 2026-08-04 AND THIS FILE NEVER RECORDED IT — the single strongest piece of
  external evidence the project has, missing from its own memory for three days (found
  2026-08-07, session 8).** Before this bullet, `CLAUDE.md` contained the words "JKP" and "Japan"
  **zero times**, and `HANDOFF_STATUS.md` likewise; the only trace was the phrase "X8's
  international replication is the out-of-sample evidence, R1 is not", which reads as *future*
  work. **It is not future work.** The omission demonstrably misled: session 8's own prompt
  instructed the agent to "scope X8 … make that actionable instead of aspirational" — for a test
  that had already run and passed. Result, from `HANDOFF_free_analysis.md` (2026-08-04, verdict
  **REPLICATES**, threshold committed first): the untuned 5-theme equal-weighted composite,
  mapped 1:1 onto Global Factor Data with **no tuning of any kind**, monthly `vw_cap`,
  1999-01 → 2025-12, NW(12):
  * **Japan +2.05%/yr (t 3.85)** and **developed Europe +3.36%/yr (t 4.30)** — both clear the
    pre-committed t > 2.0. World ex-US +3.37% (t 5.03). **All 15 European countries positive,
    12 of 15 clear t > 2.**
  * **THE CONTROL IS THE POINT: the USA is the WEAKEST region tested (t 2.35)** — weaker than
    Japan, Europe, developed and world-ex-US. The theme structure is **not** a US artifact, and
    it is out-of-sample in vendor, country, construction and period simultaneously.
  * **REPORTED, NOT BURIED: the composite replicates while its COMPOSITION does not.** Japan's
    result is carried by value (t +2.27) and size (+1.81); **quality (−0.12) and momentum
    (+0.88) contribute nothing there**, the mirror image of the US profile (quality +3.03).
    Momentum failing in Japan is a documented stylised fact, which is evidence the data is real.
    Two of five mapped themes do not generalise to Japan.
  * **IT DOES NOT CORROBORATE VALQUO'S MAGNITUDE, AND MUST NEVER BE QUOTED AS IF IT DOES.** JKP
    earns **+2% to +3.4%/yr long-short at `vw_cap`**; Valquo's long-short is **+20.4%/yr** — a
    factor of six, on a different instrument (capped value-weighted broad factors vs an
    equal-weighted concentrated decile book). **X8 establishes that the premia are real and
    general; X4 says the margin over what a user can buy is not demonstrable since 2014.**
    Together: strong evidence for genuine factor exposure, weak evidence for implementation
    alpha. Only 5 of 7 themes map — `insider` and `institutional` have no analogue, and they are
    the same two X4 found have no retail ETF analogue.
  * **LICENCE: CC BY-NC 4.0, RESEARCH ONLY.** It validates the model and can **never ship in the
    product**. Data lives in `data/factors/research_only/jkp/` (2.1 MB, 17 regions × 324 months,
    already on disk). Reproduce with `python -m scripts.jkp_replication`.
- **WHICH SELECTION RULE PICKS A THEME TO DROP IS NOT ANSWERABLE ON THIS PANEL, AND THE TEST WAS
  DELIBERATELY NOT RUN (2026-08-07, session 8). This is a result, not a skipped task.** Session 7
  ended by nominating a pre-registered test of the *selection rule* (the decide-half argmax picked
  `momentum` and `capital_discipline`, both of which flip sign across halves, while `quality` —
  stable on both halves — was never selected). The answerability question was settled **before**
  anything was run, on the already-published session-7 arm table, so it cost **zero trials**:
  * **A three-block design on 69 dates gives 22-date blocks, and the noise on a 22-date block is
    σ = 1.57pp against a pre-committed margin of 1.00pp.** Pure noise clears that margin **26.1%**
    of the time; power under the record's own best estimates is **50.6%** — a coin flip in both
    directions. A positive result and a negative result would have been equally uninterpretable.
  * **THE DESIGN CANNOT SEPARATE THE TWO RULES EVEN IN PRINCIPLE.** Monte Carlo over the design:
    the stability rule and the incumbent argmax rule **select the same arm 90% of the time** and
    reach a **different verdict on only 5.1% of panels**. The experiment is not merely
    underpowered — it is the wrong shape, because "which rule is better" is a property of the
    distribution over panels and one panel yields one draw.
  * **THE DECISIVE FACT, and it needs no variance estimate: with one panel the paired sign test
    has n = 1, whose smallest achievable p-value is 0.50. No threshold reaches significance, so
    no possible outcome could have been quotable.**
  * **DECLINING KEPT THE DENOMINATOR: equity `N` stays 116** (Deflated Sharpe **0.8674**,
    √(2·ln 116) = **3.083**). Running the 7-arm sweep would have made it 123 → DSR 0.8609,
    √(2·ln 123) = 3.102, purchasing a coin flip with a real haircut. **Not running a test that
    cannot resolve is the cheaper action, not the lazier one.**
  * **~~IT IS ANSWERABLE ON X8's DATA~~ — VOID, REFUTED BY MEASUREMENT 2026-08-07 (session 9).
    THE WORD "INDEPENDENT" WAS AN ASSUMPTION AND IT IS FALSE.** This bullet used to say "16
    held-out countries give 16 independent draws instead of 1; a paired sign test then reaches
    α 3.84% at ≥12/16, with 80% power…". Session 9 built the gate and measured it: see the
    next bullet. **Every number in that sentence is void — the 3.84%, the 80% and the 8.5%.**
- **16 CO-MOVING COUNTRIES ARE WORTH 2 TO 4 INDEPENDENT DRAWS, NOT 16 — SO A "REPLICATES IN N
  COUNTRIES" COUNT IS WORTH FAR LESS THAN ITS N SUGGESTS (2026-08-07, session 9, SELRULE).**
  The cross-country selection-rule test session 8 pre-registered was executed in full. The
  clustering gate (`valuation/edge/cross_country.py`) was built, tested and committed BEFORE the
  measure set was touched; it re-points X7's design-effect-vs-shuffled-null machinery so the
  block is the MONTH and the observations inside it are the COUNTRIES, making the measured ICC
  the average pairwise co-movement. **Two independent kills:**
  * **THE DESIGN CANNOT RETURN A POSITIVE VERDICT AT ALL. Clustering is measurable on 10 of 10
    arm-pairs** (design effects 3.97–8.27 against a shuffled-null p95 of ~1.13), **ρ 0.198–0.484,
    n_eff 1.94–4.03 countries out of 16.** The calibrated critical count is **17 of 16** at the
    pre-committed max ρ, and **even a unanimous 16/16 gives p = 0.0546** (400k draws, se 0.0004).
    At the *median* ρ the bar is 16 of 16 — unanimity or nothing. **The rejection region is
    empty; the design's power at α 5% is zero.**
  * **THE PRE-REGISTERED 12/16 BAR CARRIES A TRUE α OF 28.7%, NOT 3.84% — a 7.5×
    UNDERSTATEMENT.** Building the gate first is the only reason this session did not quote a
    "3.84%" result that was really a 29% one. **That is what the gate is for, and any future
    claim of the form "it replicates in N countries" must now pass it.**
  * **SEPARATELY: `NO CONTRAST` — both rules select `size` on `usa`**, so every paired
    difference is identically zero. Pre-registered as an outcome before the run. **Not a NULL,
    not a tie.** Four of five arms are same-sign across both `usa` halves, so the stability
    constraint does not bind. **HYPOTHESIS ONLY, generated on the decide set: the instability
    that motivated this whole question (4 of 7 arms flip on Sharadar) may be a property of the
    69-date panel's thinness, not of the selection rule** — 324 monthly observations vs 69.
  * **X8's OWN HEADLINE IS UNAFFECTED.** X8 tests each region's premium separately with NW(12)
    errors and never pooled countries into a count, so it never made the independence assumption
    this refutes. **The gate constrains what is built ON TOP of X8, not X8.**
  * **THE SELECTION-RULE QUESTION IS NOW CLOSED ON BOTH AVAILABLE DATASETS.** One panel gives
    n = 1 (session 8); 16 co-moving countries give n_eff ≈ 2–4. That is not an engineering
    defect — it is the amount of independent evidence that exists. **Do not re-open it without
    new data.** Equity `N` 116 → **121** (5 arms, paid as pre-committed): **Deflated Sharpe
    0.8628, √(2·ln 121) = 3.097.** Reproduce with
    `python -m scripts.selection_rule_crosscountry`; `data/free_analysis/SELRULE_CROSSCOUNTRY.json`.
- **THE ML TREE COMBINER IS REJECTED, AND ITS DECILES RUN BACKWARDS OUT OF SAMPLE (2026-08-08,
  session 11, roadmap #16). The register was executed unmodified.** `PREREG_ml_combiner.md` was
  committed blind at `ec6c01d` a session before it ran: seven deployed theme z-scores,
  rank-of-`fwd_ret` target, 63d, the corrected 69-date panel, a FROZEN 8-point
  `HistGradientBoostingRegressor` grid, all selection confined to a decide half via CPCV, one
  measurement per direction, both directions.
  * **WORSE ON ALPHA IN BOTH DIRECTIONS, so REJECTED by the registered rule.** decide-early →
    measure-late: tree **+1.88%** vs linear **+11.58%**, **Δ −9.70pp**, ΔHAC t −2.118.
    decide-late → measure-early: tree **−2.66%** vs linear **+2.82%**, **Δ −5.48pp**,
    ΔHAC t −2.877. All three ADOPT criteria fail in both directions.
  * **THE FINDING IS STRONGER THAN THE VERDICT: the tree's monotonicity is +0.382 and +0.842**
    — remember **negative is well-ordered** — so its top decile underperforms its bottom decile
    out of sample. **The run contains its own control:** the linear arm scored on the IDENTICAL
    rows through the IDENTICAL `quantile_backtest` call is well-ordered (−0.903, −0.855), and the
    equal-weight benchmark matches between arms to four decimals. **It is the model, not the
    harness.**
  * **IT IS NOT A FITTING FAILURE. All 16 grid × direction cells had a POSITIVE decide-half CPCV
    out-of-sample rank IC (+0.011 to +0.024).** The model generalises across 15 purged CPCV paths
    *inside* the decide half and then **reverses across the boundary**. It learns half-specific
    structure strong enough to invert a ranking rather than merely dilute it.
  * **THE TWO DIRECTIONS SELECTED OPPOSITE ENDS OF THE GRID, monotonically.** decide-early ranks
    capacity best-to-worst (most complex wins); decide-late ranks it worst-to-best (least complex
    wins). **Whether model capacity helps is a property of which half you look at, not of the
    problem.** Same shape as session 7's LOO.
  * **QUOTE IT WITH THE PARAM-SEARCH PRECEDENT: +8.43%/yr in-search → −0.04%/yr locked hold-out.**
    The combiner is that phenomenon with a sharper edge. **Selection on this panel does not merely
    fail to generalise; it can generalise backwards.**
  * **WHAT IT DOES NOT SAY:** it does not vindicate the flat 1/7 linear form, it does not close
    roadmap #16 (a raw-signal or different-model-class variant is a NEW pre-registration, and it
    inherits this reversal as its prior), and it changes nothing in the live product.
  * **Trial cost paid as registered: equity `N` 121 → 129, Deflated Sharpe 0.8628 → 0.8556,
    √(2·ln 129) = 3.118.** Every equity claim after this is charged N = 129.
    `data/free_analysis/ML_COMBINER.json`; reproduce with `python -m scripts.ml_combiner`.
- **`N` MOVES THE LONG-SHORT t, AND THEREFORE MOVES THE CALIBRATED FLOORS. THE X7 8%-vs-7%
  DISCREPANCY IS CLOSED — IT IS ONE DRAW, SEED 1005 (2026-08-08, session 12).** Two sessions
  called it undiagnosable because X7's raw draws were never retained. The cause is a coupling
  nothing in the record described: `cpcv_validate`'s adopt gate is
  `margin > _trials_haircut(len(names)) · se`, and `_trials_haircut` (`fundamental_panel.py:2097`)
  is **floored at the research log's `N`** (audit M1); `scripts/placebo.py` then feeds the
  **adopted** weights to `quantile_backtest`. **Adoption is monotone decreasing in `N`, so raising
  `N` re-scores a draw under different weights.**
  * **X7 ran at N = 84 (haircut 2.97685); session 10 ran at N = 121 (haircut 3.09703).** Seed
    1005's margin is **0.00287097** against `se` **0.00094470**: it clears the N = 84 bar
    (0.0028122) and fails the N = 121 bar (0.0029257). Scored under the challenger's weights its
    naive `ls_t` is **2.1273**; under base weights, **1.0454**. Session 10's retained artifact
    records **1.0453572947436582** — identical to the recomputation to sixteen digits.
  * **SEED 1005 IS THE ONLY FLIP IN 100 DRAWS**, which is checkable because the gate's other two
    conditions do not depend on `N`, so adoption is monotone and the search set is the draws that
    did not adopt at N = 121.
  * **IT REPRODUCES EVERY RECORDED NUMBER ON BOTH SIDES.** Substituting the adopted value into
    session 10's 100 draws gives **exactly 8** at `t ≥ 2.0` — X7's figure. And the naive **p95
    stays 2.1437, max stays 3.436** — which is precisely why session 10's control reproduced X7's
    percentiles *to the digit* while missing one draw: **2.1273 lands just below the 95th
    percentile.** One fact explains both halves of what looked like a contradiction.
  * **THE ADOPT CURVE REPRODUCES TWO HISTORICALLY RECORDED RATES THE SCRIPT NEVER SAW.** With
    `(margin, se)` banked, adoption at any `N` is arithmetic: **N = 8 → 27 draws adopt** (X7's
    recorded **27%**), **N = 84 → 21** (M1's recorded **21%**), **N = 116/121/129 → 20**
    (session 10's artifact: **20**), N = 200 → 18, N = 400 → 17. Monotone throughout, and
    **27 → 21 is six draws stopping with none starting** — exactly the one-directional move this
    file records for M1, recovered independently from the margins.
  * **CHECKED, NOT ASSUMED: today's N = 129 still gives 20 adopters, the same as session 10's
    121, so session 10's published floors (naive 2.1437, HAC 2.2837) are still the floors at the
    current `N`.**
  * **IT ALSO EXPLAINS WHY IT LOOKED UNDIAGNOSABLE.** Session 10 reasoned that no draw sat near
    2.0 so it could not be a boundary effect. Correct — seed 1005 did not *drift* across the
    boundary, it **jumped 1.08 of a t** because its weights changed. A knife-edge crossing was
    the wrong thing to look for.
  * **THE CONSEQUENCE THAT OUTLIVES THE DISCREPANCY: A CALIBRATED PLACEBO FLOOR IS A FUNCTION OF
    `N`.** The floor is a percentile of the null `ls_t` distribution, and `N` moves individual
    draws within it. **Here the floors did not move** (2.1437 naive, 2.2837 HAC at both `N`)
    because the one affected draw landed below the percentile — **that is luck, not design.**
    Every sweep must record the `N` it ran at, and **a floor may not be compared across sweeps
    run at different `N` without checking.**
  * **THE SHIPPED STRATEGY IS UNAFFECTED, for a reason already in the record: it does not adopt,
    it keeps `current-default`,** so no haircut touches its `ls_t`. The exposure is entirely to
    the *calibration*, not the headline. Same family as X7's post-hoc "CPCV adoption manufactures
    ~+1.4 of long-short t" — now a demonstrated mechanism on a named draw rather than a split.
  * `cpcv_validate` now banks **`adopt_detail`** (margin, se, haircut, `n_trials_used`) and
    **`challenger_weights_cols`** — the challenger's weights whether or not adopted — so "what
    would this run have scored one haircut lower" is arithmetic. **Zero trial cost**; equity `N`
    stays 129. `data/free_analysis/X7_RECONCILE.json`; `python -m scripts.x7_reconcile`.
- **THE TRIAL COUNTER HAD A REAL DEFECT THAT NEVER FIRED, AND `N` DOES NOT MOVE (2026-08-08,
  session 12).** `research_log._parse` tested `\bFIXED\b` against **every cell of a row joined
  together**, so a row whose hypothesis, threshold, source or note merely contained the word
  "fixed" was dropped from `N` even where its verdict read `REJECTED`. Understating `N`
  **overstates** the significance of every DSR-gated claim — M1's own error, inside M1's own
  parser, carried three sessions. Two sibling defects of the same class were fixed with it: the
  `n=<k>` grid multiplier was grepped from the **whole line**, and the domain came from the first
  cell matching any domain name rather than the domain column.
  * **THE RECOUNT MOVES NOTHING. Equity `N` 129 → 129**, options 164, infra 3, total 296, 57 rows
    counted and 18 dropped (merged log) — identical against the **shipped module itself** and
    against **all fifteen historical revisions** of `RESEARCH_LOG.md`. No `fix*` word appears
    outside a verdict cell in any of the 72 data rows as they stood at the recount; **zero
    near-misses. No published `N` was ever wrong.** Deflated Sharpe stays **0.8556**,
    √(2·ln 129) stays **3.1176**, and all four DSR figures in this file
    (N = 84 → 0.899659, 116 → 0.867360, 121 → 0.862756, 129 → 0.855608) reproduce to six decimals.
  * **THE REPAIR NEARLY SHIPPED THE ERROR IT WAS FIXING, AND THAT IS THE MOST USEFUL THING HERE.**
    Merging `origin/main` mid-session brought in **O16**, which writes
    `|Spearman(term_slope, atm_front)|` — an absolute value — **inside a markdown table cell**.
    The unescaped `|` gives that row **11 cells against a 9-cell header**, shifting every column
    after the metric; the first-cut column parser read `n` off prose and charged it **1 trial
    instead of 5, understating options `N` by 4** — the same harmful direction, in a different
    column, and **the whole-line grep it replaced was accidentally immune**. It was caught only
    because merging and re-running the recount was written into the procedure rather than left to
    the end. Misaligned rows now resolve toward a **larger** `N` and are listed in
    `rows_malformed`. **The O16 row is NOT edited** (the register forbids it); **its pipes want
    escaping as `\|` by the lane that owns them** — it is the only malformed row in 74.
  * **WHY IT NEVER FIRED IS NOT REASSURING.** Sessions 9-11 knew about the defect and dodged it
    by choosing synonyms; the earlier rows avoid the word by luck. **A denominator protected by
    authors' word choice is not protected.** The repair is pinned by a fixture the old parser
    fails (3 real trials, of which it counts 1), and `detail()` ships
    `rows_rescued_by_parser_fix` so a silent revert would be loud.
  * The pre-registered expectation (`N` rises, 60/40) was **WRONG** — five wrong directional calls
    to one right. Procedure committed at `21069ac` before the parser was touched, including the
    rule that **no row's text may be edited to change `N`**: `PREREG_session12_recount.md`.
- **THE COMPOSITE'S COMPLEXITY IS NOT DEMONSTRATED, AND THEME IC DOES NOT PREDICT WHICH THEME
  MATTERS (2026-08-06, session 6, X3 RE-RUN). The 2026-08-03 "EARNS ITS COMPLEXITY" verdict is
  VOID — it ran on the pre-B6 110-date panel and against a 1.0pp bar that sits BELOW X7's
  1.95pp noise floor.** Re-run on the corrected 69-date panel against the calibrated bars,
  8 pre-registered arms, flat weights:
  * **The full seven-theme composite beats its own best single signal (`gp_on_capital`) by
    +4.51%/yr, CI95 [−0.14%, +9.12%] — INCLUDES ZERO, so by the pre-registered rule this is a
    NULL.** A near miss is a null. **But "decoration" is the WRONG word and must not be used:**
    `gp_on_capital` alone posts long-short *t* **0.413** against the composite's **2.836** and
    clears none of X7's bars but the alpha margin. Quote both halves: *"the seven-theme
    composite is the only arm that clears the calibrated long-short bar of 2.14, and its
    top-decile alpha advantage over the best single signal is +4.5pp/yr but not separable from
    zero on 69 periods."*
  * **THE CURVE DOES NOT FLATTEN — IT IS NOT A CURVE.** Alpha by cumulative arm (themes added
    in descending IC order): +1.12 → +0.96 → +3.77 → +4.05 → +3.22 → +4.10 → **+7.17%**. Two
    prefixes have POSITIVE monotonicity, i.e. their deciles run backwards. **Only the full arm
    clears the long-short bar; the best prefix reaches t 1.02.**
  * **THE FINDING TO CARRY: `size` has the WORST theme IC (−0.30) and carries the composite's
    entire statistical significance.** Adding it last takes alpha +4.10% → +7.17% and LS *t*
    1.02 → 2.84. **Ranking themes by IC and adding greedily measures the wrong thing** when a
    theme's value is its orthogonality. This is the P6 lesson ("a signal's IC can be flat while
    the composite built from it moves a lot") in a far starker form.
  * **EXPLORATORY leave-one-out, NO VERDICT, do not act on it:** dropping `capital_discipline`
    (2nd-best IC, one of only two clearing X7's bar) *raises* alpha to +8.54% and LS *t* to
    3.352; dropping `size` costs 3.08pp/yr. Seven correlated comparisons reported for their
    extremes. **Nothing was changed on it.** A pre-registered, held-out LOO is Session 7's
    first item.
  * **THE TRIAL COUNT ROSE AND THE HEADLINE PAID FOR IT. Equity N 84 → 104** (8 new arms plus
    12 from the void run, which had never been logged). **Deflated Sharpe 0.8997 → 0.8789;
    √(2·ln N) 2.977 → 3.048, past the Harvey–Liu–Zhu hurdle of 3.0 for the first time.** Still
    above X7's calibrated floor of 0.72. `BACKTEST_RESULTS.json` picks this up automatically on
    the next full run.
- **THE EQUITY COMPOSITE IS USELESS AS AN OPTIONS VETO, AND THE REASON IS THAT ON THIS UNIVERSE
  IT IS MOSTLY A SIZE SORT (2026-08-06, session 6, U7 — REJECTED).** Join built and pinned
  (most recent rebalance date **strictly ≤** the alert date, tested against its own look-ahead
  variant). **Coverage measured before any verdict: 98.1% of 3,885 alerts, 97.8% of 186 names.**
  * **The bottom decile — the one a veto exists to remove — is the THIRD MOST PROFITABLE
    (+10.64%).** Expectancy by composite decile is U-shaped, not monotone: D1 +18.74%,
    D2 +14.78%, middle −0.46% to +4.9%, D10 +10.64%.
  * **All three pre-registered cells go the wrong way:** bottom-decile veto lift **−0.57pp**
    (CI [−1.49, +0.32], retention 92.7%), bottom-quintile −1.04pp, within-universe decile
    −0.44pp. Retention was never the binding constraint. **It does not demonstrably HURT
    either — every CI straddles zero. The honest sentence is that the composite's bottom decile
    carries no information about which alerts to refuse.**
  * **NO INTERACTION WITH THE ALERT AT ALL.** The identical veto on the five-seed random-entry
    control lifts by −0.49pp; real minus control is **−0.08pp** [−1.02, +0.82]. The composite
    describes the UNDERLYING, not the alert.
  * **MECHANISM:** median market cap rises monotonically across deciles, **$62.7B (D1) →
    $133.5B (D9)** — inside 187 megacaps the other themes are compressed and `size` dominates,
    so the "veto" vetoes a cap bucket, which is a property of the underlying. (D10 sits at
    $106.0B and breaks the pattern; no claim is made about why.)
  * **CONSEQUENCE: DO NOT RUN U1 (composite → options ENTRY) AS WRITTEN.** The audit's own
    argument is that the veto is "strictly the easier bar". The easier bar failed *with a
    mechanism*. Reopen only with a composite built WITHIN the options universe, or with size
    neutralised.
  * **THE PROJECT'S EXPECTATION WAS WRONG AGAIN — FOURTH IN A ROW.** The pre-commitment said
    "I expect the veto to HELP, 60/40". R10, O20, the spread toll and now U7. **Do not reason
    about the direction of an effect in this project; measure it. Writing the expectation down
    first is worth doing precisely because it keeps being wrong.**
- **X8 HAS LANDED AND IT REPLICATES — THE PROJECT'S ONLY OUT-OF-SAMPLE EVIDENCE, AND THIS FILE
  RECORDED IT NOWHERE UNTIL NOW (added 2026-08-07 by the claims audit; landed 2026-08-04,
  `7edf594`, ledger X8 DONE, write-up in `HANDOFF_free_analysis.md`).** Two bullets below still
  say "still ONE panel; **X8's international replication is the out-of-sample evidence, R1 is
  not**" — written as though X8 were pending. It ran. Untuned 5-theme equal-weighted composite,
  themes mapped 1:1 with **no tuning**, on Global Factor Data (JKP), monthly `vw_cap`, matched
  window 1999-01 → 2026-04, bar committed in writing first (NW t > 2.0, 12 lags, in **both**
  Japan and developed Europe):
  * **VERDICT: REPLICATES. Japan +2.05%/yr (NW t 3.85), developed Europe +3.36%/yr (t 4.30),
    world ex-US +3.37% (t 5.03).** Europe is not one country: **all 15 positive, 12 of 15 clear
    t > 2**.
  * **THE STRIKING PART IS THE CONTROL: the USA is the WEAKEST region tested (t 2.35)** — weaker
    than Japan, Europe and world-ex-US. Whatever else is true, **the theme structure is not a US
    artefact.** It is out-of-sample in vendor, country, construction and period simultaneously.
  * **WHAT IT DOES NOT ESTABLISH — carry this with it: MAGNITUDE.** The JKP composite earns
    **+2% to +3.4%/yr** long-short at `vw_cap`; Valquo's own long-short is **+11.04%/yr**
    (`construction.long_short_ann`, corrected panel). Not comparable instruments (capped
    value-weighted broad factors vs an equal-weighted concentrated decile book), but the gap is
    a factor of 3-5 and **nothing in X8 corroborates it.** *(The X8 write-up states the gap as
    "a factor of six" against a Valquo long-short of +20.4%/yr; that figure does not match the
    landed corrected panel, which reads 11.04%. Quoted here from the artifact, not the handoff —
    the direction of the caveat is unchanged either way. Flagged for the free-analysis lane.)*
  * **The composite replicates while its COMPOSITION does not.** Japan is carried by value
    (+2.27) and size (+1.81); quality is **−0.12** and momentum +0.88 there. The US control is
    nearly the mirror image (quality +3.03, momentum +1.69, value +1.01, size +0.87). Momentum
    failing in Japan is a documented stylised fact, which is evidence the data is real rather
    than a defect. An equal-weighted blend is the right structure for that world — a quiet
    vindication of the untuned flat weights.
  * Secondary arm, reported as measured: JKP publishes **terciles**, not deciles, so monotonicity
    is across 3 points and is weaker than the pre-registration promised. 5/5 correct-sign in the
    US, 4/5 in Japan (the exception is `qmj`, consistent with quality's t there).
- **THE THRESHOLDS ARE NOW CALIBRATED — READ THIS BEFORE QUOTING ANY t, IC OR PBO
  (2026-08-05, audit X7). Every bar in this project was a CONVENTION until this run; three of
  the four are too low, and one is at the noise level.** `scripts/placebo.py` shuffles the
  signal within each rebalance date (block permutation: per-date distribution, missingness
  pattern and cross-theme correlation all preserved exactly; `fwd_ret`/`marketcap`/`sector`
  untouched) and pushes 100 draws through the REAL pipeline — CPCV, weight selection,
  quantile backtest, theme ICs, the held-out gate. The harness reproduces the shipped run
  exactly (t 2.83606, alpha 0.071741, PBO 0.73333) before any draw, and the equal-weight
  benchmark is +18.14% on all 100 draws (sd 0.00004), which is the control.

  | bar | as used | CALIBRATED (placebo p95) | how often pure noise clears the OLD bar |
  |---|---|---|---|
  | theme IC t | 2.0 | **2.71** (noise max 3.93) | **39%** |
  | long-short t (naive) | 2.0 | **2.14** (noise max 3.44) | 8% |
  | **long-short t (HAC — the one to quote)** | 2.0 | **2.28** (noise max 3.78) | 8% |
  | top-decile alpha margin | 1.0pp | **1.95pp** | 18% |
  | PBO | <50% | **<19.7%** (placebo p5; noise MEDIAN is 46.7%) | **55%** |
  | Deflated Sharpe | >0.95 | **STANDS** (noise median 0.28) | 2% |

  **THE DEFLATED SHARPE ROW IS CONFIRMED AT THE TRUE N (2026-08-06, session 5). The
  PROVISIONAL marking is LIFTED.** The placebo was re-run at `N = 84` on the identical panel
  and identical seeds. **The statistic is MORE discriminating at the honest denominator, not
  less: 0 of 100 noise draws clear 0.95, against 2 at N = 8**, and the calibrated bar (placebo
  p95) falls 0.8567 → **0.7216**. Every OTHER rate in this table is identical to the last digit
  across the two sweeps (holdout 6%, ls_t≥2 8%, maxIC_t≥2 39%, PBO<50 55%), which is the
  harness-reproduction check — so no other calibrated bar was ever in question.
  **BOTH M1 AND X7 ARE RIGHT AND THEY NEVER CONFLICTED.** The edge's 0.8997 fails the >0.95
  convention (M1) **and sits above ALL 100 placebo draws** (max 0.8649, empirical p ≤ 0.01),
  because at the honest N the 0.95 convention is STRICTER than the noise floor requires.
  **Quote it whole or not at all:** *"Deflated Sharpe 0.8997 at N = 84 — fails the conventional
  >0.95 bar, while sitting above all 100 placebo draws (calibrated bar 0.72)."* It is the one
  bar where this strategy is distinguishable from noise and still fails its threshold.
  **M1 also made the adoption gate harder for noise to pass, as a free side effect:** CPCV
  adopts on **27% → 21%** of pure-noise draws, one-directional (six draws stopped adopting,
  none started). ~~because the adopt gate reads the Deflated Sharpe~~ — **THE MECHANISM WAS
  BACKWARDS; CORRECTED 2026-08-08 (session 12). The direction and the magnitude are right and
  the mechanism was not.** The adopt gate cannot read the Deflated Sharpe: adoption is decided
  at `fundamental_panel.py:2729` and `_dsr_detail` is computed at `:2744`, **downstream of it**,
  on the returns of whichever scheme adoption just chose. What M1 actually changed is
  `_trials_haircut` (`:2097`), which is **floored at the research log's `N`** — and the adopt
  gate multiplies `se` by that haircut. Both the haircut and the DSR read `_trial_N()`; neither
  reads the other. **This matters beyond pedantry, because it means `N` MOVES `ls_t`** — see the
  session-12 bullet below. **This is NOT the run-to-run
  non-reproducibility** — that remains open; it was briefly mistaken for it before the
  one-directional pattern was checked.

  **Use these numbers, not the old ones.** They are floors for THIS panel/universe/69 dates,
  not universal constants — re-measure if the panel changes materially. Three consequences
  that are easy to get wrong: **(a)** 39% of noise draws produce at least one theme at IC
  t ≥ 2.0, because EIGHT themes are tested and the bar is applied to whichever looks best —
  the project has always read that bar as if one theme were being tested; **(b)** the
  **held-out gate (`holdout_theme_validate`) has a measured ~6% false-positive rate**, and
  `low_risk` — the theme actually zeroed on its verdict — turned up among the false confirms
  once in 100 draws, so that decision is not overturned but must be quoted with the rate;
  **(c)** the real headline is outside the placebo's [2.5, 97.5] interval on alpha (clearly),
  Deflated Sharpe, monotonicity, max theme IC t (narrowly) and long-short t (narrowly) — and
  **INSIDE it on PBO**, which is therefore not distinguishable from noise.
- **THE OPTIONS ENTRY SIGNAL IS DEAD, ON CORRECTED DATA (2026-08-05, audit session 5 / R2). The
  project's most consequential negative finding was re-derived after five defects were repaired,
  and it SURVIVED — the gap moved 0.61pp.** Every number in `HANDOFF_universe_backtest.md` was
  computed against a mis-stated underlying price (B1) plus B2/B3/B4/B15, and that file is now
  banner-marked SUPERSEDED. Re-run on the identical pinned 187-name universe:
  **CORRECTED 2026-08-11 (session 23, `U1-SPLIT`) — THE GAP IS −5.06pp, NOT −6.65pp, AND 24% OF
  THE PUBLISHED GAP WAS A CORPORATE-ACTION ARTIFACT. THE VERDICT IS UNCHANGED.** The figures
  below now read split-clean; the as-published ones are kept beside them because the
  re-derivation reproduces them **to the digit**, which is what makes the correction checkable.
  Option chains are as-traded and unadjusted for splits while `bars` ARE adjusted, and nothing in
  the options lane consulted the split table — GE's 1-for-8 reverse split (2021-08-02) let a
  $0.27 call settle against a ~$104 post-split underlying on a pre-split strike and book
  **+31,921%** against a true value of **zero**. Full repair record in `PREREG_u1split_repair.md`.

  | | as published | **split-clean (quote this)** |
  |---|---|---|
  | alert book | +3.41%/trade | **+3.2702%** (n 3,885 → 3,870) |
  | five-seed control | +10.06%/trade | **+8.3342%** (n 29,785 → 29,654) |
  | **gap** | −6.6468pp | **−5.0640pp** |
  | date-block CI95 | [−11.9152, −2.1317]pp | **[−8.5957, −1.5325]pp** |
  | paired sign-test z | −4.9027, 1,334 cells | **−4.9612, 1,332 cells (p 7e−07)** |

  **THE CONTROL IS CONTAMINATED ~12× HARDER THAN THE ALERT BOOK** (15 rows vs 131) because it
  draws many random days per name-year and so gets more shots at any split window — two GE draws
  at +269x and +261x. **The defect was therefore making R2's negative verdict look WORSE than it
  is, and correcting it runs TOWARD the alert.** It still loses decisively.
  **REPORTED BECAUSE IT CUTS AGAINST THE OBVIOUS READING: the sign test does NOT weaken — it
  strengthens slightly, −4.9027 → −4.9612.** The mean gap shrank because the artifact was a
  right-tail phenomenon in the control; the median name-year cell never depended on it. The
  alert's day-selection subtracts value. **Do not describe the live options alert as a
  day-selection edge; it is an alert-generation mechanism.**
  * **THE BREADTH CLAIM IS VOID.** "The edge survives breadth but roughly halves" is false.
    **CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean the new names read −0.5589%/trade and the
    baseline 54 megacaps +9.1391%** (as published: −0.4713% and +9.3720%, reproduced exactly).
    **The count is 132 names, not the 133 this file has said** — `UNIVERSE_RESULTS.json`'s
    `new_names_only.n_names` has always read 132. All of the book's positive expectancy is still
    the original 54 megacaps, so the claim's substance is unchanged. It is a megacap phenomenon
    that a corrupted price basis made look broader.
  * **B1's signature, for the record:** trades ROSE 3,042 → 3,885 because `no_contract_in_band`
    rejects fell 2,911 → 1,729 — an adjusted spot against as-traded strikes was throwing the
    0.90–1.20 moneyness prefilter, silently discarding 1,182 alerts. Median entry IV
    **1.4200 → 0.2497** at 100% coverage (was 75.3%). 142% was never a vol.
  * **A SINGLE CONTROL SEED CAN FLIP THIS VERDICT — RUN FIVE, AND READ THE SIGN TEST.** The
    control's own mean ranges **+6.46% to +15.34%** across five draws. Seed 0 alone reads
    INCONCLUSIVE and is the most favourable of the five; **all five point estimates are
    negative and four of five are negative at significance.** A random-day book's mean on a
    barbell payoff is set by a few +600% trades. **More control draws SHARPEN the test** (2-seed
    z −2.907 → 5-seed z −4.903), because each name-year cell's control mean averages more draws.
    The paired *t* ranges +0.162 to −1.835 and is never significant even pooled (−1.227, p 0.22)
    — it is the wrong statistic here. **Standing rule: five seeds minimum, sign test carries the
    verdict.**
  * **`term_slope` is REJECTED on the arm that matters (R7).** Its +8.89pp out-of-sample
    replication was an artefact; corrected, the filter makes its own out-of-sample book WORSE
    (gain **−1.12pp** against a +5.00pp bar) and is no longer tail-enriching. It PASSES the
    re-committed retention floor (G3a 95.6 alerts/yr, G3b 96.2% of names and 98.2% of months,
    G3c 35.9%) — so the old 40% constant WAS rejecting a genuinely broad filter, and the
    rejection now rests on economics instead of on an underived number.
  * **Deflated Sharpe fell below 95% on both books:** unfiltered 88.13% → **49.59%**,
    term_slope-filtered 95.69% → **80.63%**. The autopsy re-confirms: 64 features, 127
    hypotheses, **zero survivors**.
- **OPTIONS STATISTICS ARE CLUSTERED, BUT LESS THAN THE AUDIT PREDICTED (2026-08-05, audit R3).**
  Every options interval ever published resampled TRADES and is optimistically narrow.
  `valuation/edge/options_stats.py` adds a date-block bootstrap (calendar months resampled
  together), `n_eff`, the paired name-year sign test and paired *t*, purge/embargo for the CSCV
  splits, and the Deflated Sharpe at `n_eff`. **CORRECTED 2026-08-06 (session-5 closeout): the
  clustering factor is 2.212, NOT 1.85, and it is INSIDE the audit's predicted 2–4 — the record
  said the audit over-predicted and the record was wrong.** The 1.848 (null p95 1.266) was
  measured on the PRE-CORRECTION 3,042-trade book and never updated; the corrected 3,885-trade
  book gives **design effect 2.2121 against null p95 1.2037**, which is what
  `UNIVERSE_RESULTS.json` has always shipped — the artifact was right, the prose was stale.
  **CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean the figures are design effect 2.1837 against
  null p95 1.1898** — clustering is still measurable, the √-haircut is 1.478× rather than 1.487×,
  and no verdict moves. Removing 15 of 3,885 trades was never going to shift an ICC materially,
  and it did not; the figures are restated only so the file quotes one book throughout.
  **Every options *t* shrinks by √2.212 = 1.487×, not 1.36×**, and **no verdict changes** (checked,
  not assumed: R2 rests on the name-year sign test, the date-block intervals embed clustering by
  construction rather than applying the design effect as a haircut, and
  `deflated_sharpe_clustered` ships alongside the raw figure rather than replacing it).
  * **R3.3 is the one that mattered:** the paired sign test and paired *t* the entire options
    conclusion rested on existed in NO shipped file. They now reproduce the record exactly
    (441 of 1,052 cells, z −5.185 against the recorded −5.24; seed-0 paired t −2.6701 against
    −2.67), pinned by a test.
  * **A RAW DESIGN EFFECT IS NOT EVIDENCE OF CLUSTERING.** Found by a failing test: 600
    independent draws in 12 blocks of 50 report a design effect near 1.8 — pure sampling error
    in MSB/MSW, since that ratio is F(k−1, n−k). Applying it as a haircut would manufacture a
    correction out of noise. The design effect is now scored against its own shuffled null (the
    X7 method) and `clustering_measurable` gates it; the real book passes clearly (**corrected
    book: deff 2.2121 vs null p95 1.2037**; the pre-correction book's 1.848 vs 1.266 is what the
    record used to quote here). **Never quote a design effect without its null — and never
    without its BOOK: that is exactly how the 1.85 figure travelled out of scope.**
- **POINT-IN-TIME LIQUIDITY RAISES THE OPTIONS HEADLINE — the audit expected it to fall
  (2026-08-05, audit O20).** Applying the miner's own screen at each entry date instead of to the
  name's first cached year: **PIT-liquid 3,359 trades at +4.82% vs PIT-illiquid 495 at −7.84%**,
  coverage 99.2%. **CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean these read 3,347 at +4.7293%
  and 494 at −8.0168%** — the means reproduce as published to the digit and the correction moves
  them by hundredths, so nothing here changes. **But it does NOT rescue the signal** — the
  control is screened by the same rule and benefits too, so on the liquid subset the real book
  loses to random entry MORE decisively (z −3.475, p 0.0005). The headline stays the whole book
  at aggression 1.0.
  **THE z OF −3.475 DID NOT REPRODUCE AND IS THEREFORE NOT RESTATED (2026-08-11, `U1-SPLIT`).**
  Re-deriving the liquid-subset paired name-year sign test against the same-screened control
  gives **−4.8953 as published** and −4.8109 split-clean, not −3.475, on a construction that
  reproduces every other O20 figure exactly. The −3.475 is in no shipped artifact —
  `UNIVERSE_RESULTS.json`'s `o20_point_in_time_liquidity` block carries no z at all — so it
  cannot be reconciled from the repository, only re-derived by the lane that produced it.
  **Neither number is quoted as the corrected one here**; the discrepancy is recorded instead,
  because silently substituting a figure that happens to agree in direction is how the 1.85
  design effect travelled out of scope. **Owner: the O20 lane.** The direction of O20's claim —
  the liquid subset loses to its own control more decisively, not less — holds on every
  construction tried.
  **The audit's premise is half wrong and this is the correction:** names were ranked into the
  mining pool by TODAY's market cap (true), but the liquidity screen was already applied to the
  FIRST CACHED YEAR, not to a present-day chain (`mine_options_cache.py:160`). So O20 is an
  UPPER BOUND on the repair — names that would have failed in 2016 were never mined and no
  evaluation-time filter recovers them.
  **THE PATTERN WORTH KEEPING:** this is the third time in two sessions (R10, then O20) that a
  bias the record assumed ran in the strategy's favour ran the other way. **This project's
  expectations about the direction of its own biases have been wrong more often than right.
  Measure them; do not reason about them.**
- **THE EDGE DOES NOT CLEAR THE DEFLATED SHARPE BAR (2026-08-05, audit M1). The last bar the
  project claimed to clear fails once the denominator is honest.** Every multiple-testing claim
  was computed against `N = 8` — the eight weight schemes. `RESEARCH_LOG.md` is now populated and
  `valuation/edge/research_log.py` feeds the real count into `_deflated_sharpe` and
  `_trials_haircut`. Trial counts **as of this bullet**: equity 84, options 139, infra 1, total 224
  (session 5 added 4 options rows), against the audit's ~146 estimate; `FIXED` correctness rows
  correctly do NOT count. **CORRECTED 2026-08-07 (claims audit): those counts are STALE — measured
  today `research_log.detail()` reads equity 116, options 155, infra 1, total 272 (51 rows counted,
  17 `FIXED` rows not counted). `N` is a project quantity that keeps rising; quote the equity 116
  and the 0.8674 from the session-7 bullet below, not the 84 in the table that follows.** The table
  is kept as the record of what M1 measured on the day it landed.

  | | N = 8 (as shipped) | **N = 84 (measured)** |
  |---|---|---|
  | Deflated Sharpe | 0.9970 | **0.8997** — FAILS the >0.95 bar |
  | `sr0_benchmark` | 0.242 | **0.406** |
  | `metric` self-report | `probabilistic_sharpe_ratio_UNDEFLATED` | **`deflated_sharpe_ratio`** |
  | `_trials_haircut` | 2.04 | **2.977** |

  **There is a real win inside the failure: audit B9 is RESOLVED by measurement.** B9 argued the
  statistic was an undeflated PSR because `sr0` collapsed. With a real `N` it does not collapse —
  `sr0` rises to 0.406 against a per-period Sharpe of 0.550, deflating away 74% of it, and the
  statistic self-reports as a genuine Deflated Sharpe **for the first time**. The price of fixing
  it is that the bar is no longer cleared. That trade was pre-committed before the run.
  Also: **√(2·ln 84) = 2.977**, i.e. the multiple-testing haircut at the real `N` lands within
  0.03 of the Harvey–Liu–Zhu hurdle of 3.0 — exactly as the audit predicted.
  **`N` is domain-scoped** (the equity composite is charged the 84 equity trials, not the 218
  project-wide ones — the options autopsy is a different search for a different product), and a
  missing log degrades to `N = 8`, i.e. to the OLD behaviour, never to an unpenalised one.
- **THE HEADLINE NOW HAS A t, AND THE LONG-SHORT t IS 2.620 NOT 2.836 (2026-08-05, audit R9).**
  `top_decile_alpha` — the number on the front of the product — shipped with **no significance
  statistic of any kind**. It now carries **t +4.517, HAC t +4.376, hit rate 71.0%**. The
  long-short's naive i.i.d. t is joined by **HAC t +2.620** and a Ljung–Box diagnostic.
  **Ljung–Box rejects independence at p = 0.036** (lag-1 autocorrelation +0.189), so per the
  pre-commitment **the Newey–West t is now the number this project quotes** and the naive t is a
  diagnostic only. The 63d windows genuinely do not overlap — that dimension was fine — but
  factor spreads are autocorrelated and nothing anywhere measured it. Note the long-ONLY object
  is far better measured (t 4.38) than the long-short the project has always led with.
  ~~Comparing 2.620 to X7's calibrated floor of 2.14 is apples-to-oranges~~ — **CLOSED
  2026-08-07 (session 10). The floor is now measured on the HAC statistic: 2.28, and the
  headline clears it.** See the next bullet; quote **2.620 vs 2.28**, never 2.620 vs 2.14.
- **THE LONG-SHORT FLOOR IS NOW CALIBRATED ON THE STATISTIC THE PROJECT ACTUALLY QUOTES —
  THE HEADLINE STILL CLEARS, AND THE MARGIN ROUGHLY HALVES (2026-08-07, session 10).** X7
  calibrated 2.14 on the *naive* t; R9 then made the *HAC* t the number quoted, and the two had
  been compared to each other ever since. Re-run of X7's placebo — **same panel, same seeds
  1000–1099, same instrument, n = 100, costs measured; the only change is that the recorder now
  stores the HAC statistic `quantile_backtest` had been computing on every draw since R9 and the
  writer was silently dropping.**
  * **CALIBRATED HAC FLOOR (placebo p95) = 2.2837** (noise median 0.121, max 3.783).
    **Shipped HAC t = 2.61991 → CLEARS**, empirical p **0.03** (3 of 100 noise draws exceed it).
  * **BOTH MOVES GO AGAINST THE STRATEGY AND THE CUSHION HALVES.** The HAC floor is *higher*
    than the naive floor (2.28 vs 2.14) while the real HAC t is *lower* than the real naive t
    (2.620 vs 2.836), so the margin over the floor falls **0.692 → 0.336**. It clears; it clears
    by less than the record implied.
  * **THE OLD MISMATCH WAS MILD, NOT WILD: pure noise clears 2.14 on the HAC statistic 6% of
    the time** against the 5% the bar intends. Worth closing, not a scandal.
  * **THE CONTROL REPRODUCES X7 TO THE DIGIT:** naive p95 **2.1437** → X7's 2.14, noise max
    **3.4360** → X7's 3.44. **One discrepancy, reported not buried:** the `ls_t ≥ 2.0` rate comes
    back **7%** against the recorded **8%** — a single draw, with no draw anywhere near the 2.0
    boundary (nearest 1.885 and 2.067), so it is not rounding. **It cannot be reconciled because
    X7's raw draws were never saved.** This sweep saves all 100.
  * **FREE BY-PRODUCT, and it is the stronger number: the top-decile alpha HAC t now has a floor
    too — 2.2913 — and the shipped +4.376 sits ABOVE ALL 100 NOISE DRAWS (empirical p 0.00).**
    The long-ONLY book remains far better measured than the long-short the project leads with.
  * **R9's autocorrelation finding is corroborated:** Ljung–Box on noise draws has median
    p 0.406 and rejects at 7%, i.e. near nominal — so the real series' p 0.036 is a property of
    the real series, not an artefact the pipeline manufactures.
  * Artifact `data/free_analysis/PLACEBO_HAC.json` (all 100 draws retained); procedure
    pre-committed in `PREREG_session10_hac_floor.md`; **zero trial cost** — a calibration
    searches nothing, equity `N` stays 121.
- **THE UNINVESTABLE BENCHMARK WAS THE HARDEST ONE — the expectation was WRONG in the strategy's
  favour (2026-08-05, audit R10).** Alpha had only ever been measured against an equal-weighted
  average of every name in the panel, charged zero trading cost while the strategy pays. Both the
  audit and this session's own pre-commitment predicted that flattered the product. It does not:

  | benchmark | benchmark /yr | top-decile EXCESS /yr | HAC t |
  |---|---|---|---|
  | equal-weight universe (incumbent, cost-free) | +18.14% | **+7.17%** | +4.376 |
  | equal-weight, charged the strategy's own costs | +16.10% | +9.21% | +5.685 |
  | cap-weighted panel average | +14.85% | +10.46% | +4.292 |
  | **SPY total return** | +15.32% | **+9.99%** | +3.770 |

  Over 2009-01 → 2026-01 the equal-weighted panel returned **+18.14%/yr vs SPY's +15.32%** — a
  ~1,500-name equal-weighted book beat the cap-weighted index over a window starting at the
  post-GFC bottom. So the incumbent benchmark is uninvestable in the direction of being **too
  demanding**. **Keep publishing +7.17% as the headline** — it is the most conservative and the
  one every historical figure used, so changing it would break comparability for a number that
  only moves the flattering way. The edge now also survives an INVESTABLE benchmark: +9.99% over
  SPY (HAC t 3.77). Charging the equal-weight book the strategy's own cost table costs it
  2.04pp/yr, a genuine thumb on the scale that had sat in the strategy's favour and is now gone.
  All four ship in the `benchmarks` block on every run.
- **CPCV WEIGHT ADOPTION MANUFACTURES ~+1.4 OF LONG-SHORT t OUT OF NOTHING (X7, post-hoc —
  treat as a strong hypothesis, not a settled result).** Splitting the 100 placebo draws on
  whether CPCV adopted: when it did NOT (73 draws) mean long-short t is **−0.065** (se 0.119),
  a textbook null; when it DID (27 draws) mean t is **+1.343** (se 0.184) and mean alpha
  +0.82pp. It fires on **27% of pure-noise draws**. Mechanism: the adopted weights are chosen
  on the same panel the headline is then measured on. **The shipped strategy is UNAFFECTED —
  it does not adopt, it keeps `current-default`** — which is measured support for the existing
  rule that a CPCV rejection means keep the defaults. But any future run that DOES adopt a
  CPCV scheme has an optimistically biased headline unless measurement moves off the
  selection panel. Not pre-registered; wants a pre-registered replication.
- **CORRECTED 2026-08-03 (audit B9) — TWO OF THE THREE "statistical bars" MEASURE SOMETHING
  NARROWER THAN THE CLAIM THEY SUPPORT. Lead with the long-short t of 3.52 against the
  Harvey–Liu–Zhu hurdle of 3.0. That one is real.** The other two:
  * **The Deflated Sharpe IS deflating — the audit's mechanism for this one is REFUTED by
    measurement, and only half of its criticism survives.** The audit argued that the eight
    weight schemes are indistinguishable (out-of-sample median ICs spanning +0.061 to +0.062),
    so the cross-trial VARIANCE of Sharpes is ~0, `SR₀ ≈ 0`, and the statistic degenerates to
    Φ(SR·√(n−1)). **Measured on the full-universe run: `var_sr_across_trials` = 0.0276 (sd
    0.166, not ~0) and `sr0_benchmark` = 0.242 against a per-period Sharpe of 0.606** — the
    benchmark is deflating away 40% of the Sharpe. The audit inferred near-identical trial
    SHARPES from near-identical median ICs; those are different quantities, and the Sharpes are
    genuinely dispersed. It saturates because a per-period Sharpe of 0.61 over 110 periods is
    a large z, not because nothing is deflated. Every run now ships
    `deflated_sharpe_detail` (`sr0_benchmark`, `var_sr_across_trials`, `n_trials`) plus a
    `metric` field that reads `probabilistic_sharpe_ratio_UNDEFLATED` **if** `sr0` ever does
    collapse — so this is now a measured property of each run rather than an assumption in
    either direction.
  * **What DOES survive: `N = 8` is not the number of trials this project has run.** The
    ledger records of the order of 146 pre-registered tests. That criticism is untouched by
    the above and is the real one. Until a genuine trial counter exists (audit M1,
    `RESEARCH_LOG.md`, started but deliberately not wired), the deflated figure is computed
    against a denominator that is roughly 18x too small.
  * **PBO 6.7% scores the WEIGHT-SCHEME SELECTION STEP ONLY** — "the best of eight nearly
    identical weightings generalises". It says nothing about the ~146 signal-inclusion,
    theme-membership, universe, standardisation and construction decisions in the ledger, and
    the shipped strategy keeps `current-default` anyway, so the selection being scored is one
    the model never makes. Now shipped as `pbo_scope`.
  * The honest version of both needs a real trial counter (audit M1, the append-only research
    log). **Not done.** At N ≈ 100+, √(2·ln N) ≈ 3.0 — about the Harvey–Liu–Zhu hurdle.
- **B8 IS FIXED (2026-08-06, session 7), AND `low_risk` SURVIVES IT ON HALF THE EVIDENCE THE
  RECORD CLAIMED.** `holdout_theme_validate`'s docstring described a clean protocol — flag a
  theme on one half with a pre-specified rule, then measure removal ONLY on the other half — and
  the code never implemented step 2: `rule_fired` was computed and never read. (Line cite, current
  2026-08-07: it is set at `fundamental_panel.py:3576` and now READ at `:3594`, which is the fix.
  This bullet said `:3545` and the long-cited `:3048` had drifted into an unrelated function —
  **line numbers in this file rot within days; re-resolve before trusting one.**) Two verdicts now
  ship, named for what they are:
  * **`verdicts` / `stability_verdicts` — SEMANTICS DELIBERATELY FROZEN.** This is the
    both-halves check every shipped decision actually rested on, and **X7's measured ~6%
    false-positive rate was calibrated against this exact object** (`scripts/placebo.py:108`
    reads this key). Redefining it in place would have left that 6% describing a gate that no
    longer exists — the same class of error as the stale theme IC table.
  * **`oos_verdicts` — the documented rule enforced.** A direction counts only if its decide
    half flagged the theme. `oos_directions_tested = 0` means **no out-of-sample test was run
    at all**, which is a different statement from a negative result.
  * **NEITHER SHIPPED DECISION CHANGES:** `low_risk` `confirmed_oos`, `insider` `rejected_oos`.
    **But `low_risk` is confirmed in ONE of two directions, not two** — the rule fires only on
    the early half. Quote it whole: *"zeroing `low_risk` is confirmed out-of-sample in one of
    two split directions, and passes a both-halves stability check in both."*
  * **THE PART THAT GENERALISES: three themes (`quality`, `capital_discipline`,
    `institutional`) are `not_flagged` in both directions**, because the rule is `median IC ≤ 0`
    and their ICs are positive. `capital_discipline` is precisely the theme session 6's
    exploratory LOO nominated for dropping. **An IC-gated rule cannot express a
    marginal-contribution hypothesis** — X3's whole finding is that theme IC does not predict
    marginal contribution. Do not reach for `holdout_theme_validate` to adjudicate an ablation.
- **THE FULL-SAMPLE LEAVE-ONE-OUT DOES NOT SURVIVE A TIME SPLIT — SESSION 6'S EXPLORATORY
  RESULT IS NOT A PROPERTY OF THE PANEL (2026-08-06, session 7, LOO — NULL).** Pre-registered
  at `5a27ea1` before any number existed: select the best of seven leave-one-out arms on a
  decide half, measure only that arm on the held-out half, both directions, against the
  MIN_HOLDOUT margins committed before P6 (100bps alpha, 0.25 t).
  * **Direction 1 selects dropping `momentum` (decide +3.68%) → measure −1.30%, LS t −0.706.
    Direction 2 selects dropping `capital_discipline` (decide +2.20%) → measure +0.20%,
    LS t −0.201. Neither clears either margin; different themes selected. VERDICT NULL.**
  * **FOUR OF SEVEN ARMS CHANGE SIGN BETWEEN HALVES** (`momentum`, `insider`, `value`, and
    `capital_discipline` moves 3rd → 1st). Session 6's "+8.54% from dropping
    `capital_discipline`" is the average of +0.20% and +2.20% — carried by the late half.
    **Do not quote a full-sample ablation arm as a finding.**
  * **`size` IS CORROBORATED: it is the WORST arm to drop in BOTH halves independently
    (−2.64%, −3.46%)** — the only theme whose LOO effect is both large and stable. Stated with
    its limit: `size` was never *selected* (the rule takes the maximum), so this is the most
    stable cell in a table that carries no verdict, not a pre-registered result. Enough to say
    **"do not drop `size`, and stop treating its low IC as evidence against it."**
  * **NOT CLAIMED, DELIBERATELY:** `quality` clears both margins on both halves and was
    selected in neither direction, because the pre-registered rule takes the maximum and the
    maximum is the statistic most inflated by noise. Promoting that now would be selecting the
    RULE on the results — session 6's error one level up. Session 8 pre-registers it or nobody
    quotes it.
  * **The expectation was written down first and was RIGHT** (NULL at 70/30), breaking a
    four-run streak of wrong directional calls. One correct call after four wrong ones does not
    license reasoning about direction; keep measuring.
  * **Equity `N` 104 → 111 from this session's 7 arms, then → 116 once a concurrent lane's 5
    equity trials merged. QUOTE 116: Deflated Sharpe 0.8674, √(2·ln 116) = 3.083** (still far
    above X7's 0.7216 floor, still below the 0.95 convention). **`N` is a PROJECT quantity, not
    a session one** — it is now two sessions running that the realised count overshot its own
    pre-commitment, for a different reason each time. Also settled this session:
    **`SUPERSEDED` rows DO count toward `N`** — the schema prose said otherwise and
    `research_log.py` never implemented it; the counter is right and the prose is fixed.
- **SUPERSEDED 2026-08-04 (audit session 2, B6) — EVERY NUMBER IN THE NEXT TWO BULLETS WAS
  MEASURED ON A PANEL WHOSE FIRST THIRD HAD AN INVERTED UNIVERSE. The corrected numbers are
  WORSE and TWO OF THE THREE BARS NOW FAIL. Read the "CORRECTED PANEL" bullet below first;
  the two bullets that follow are kept only as the record of what the defect was producing.**
- **CURRENT FULL-UNIVERSE NUMBERS (2026-08-04, after the audit's Part I corrections):
  long-short t 3.884, top-decile alpha +11.78%, monotonicity −0.988, PBO 13.3%.** Measured
  against a clean pre-audit baseline re-run on identical data (t 3.520, alpha +11.88%,
  monotonicity −0.952, PBO 6.7%): the composite sorts BETTER, top-decile alpha is a rounding
  change, PBO doubles off a low base. The equal-weight benchmark did not move (+16.55% in every
  run), which is the control. **Thirteen corrections and NOT ONE held-out verdict changed** —
  the record's decisions were not resting on the defects, and the defects were not hiding a
  different model. The sanity layer's flag count fell 5 → 2 (the three negative-multiple sign
  flags cleared). Full A/B in `HANDOFF_edge_audit.md` Part 2.
- **The edge clears PBO 13.3% (want <50%), long-short t 3.851 (want >2), top-decile alpha
  +11.69%.** The single biggest driver was zeroing `low_risk`, which passed the both-halves test
  described above (decide on one half, measure on the other, both directions). On the
  pre-registered direction the rule fires on the early half (median IC −0.0308) and, measured
  on the later half, **long-short t goes 0.97 → 2.56 and top-decile alpha +6.09% → +9.30%**; the
  reverse direction agrees more strongly (t 0.55 → 2.57, alpha +6.63% → +14.49%). Do not treat
  the edge as settled — caveats at the end.
- **CORRECTED PANEL, 2026-08-04 (audit session 2, B6+B7+B13) — THESE ARE THE LIVE NUMBERS.
  Long-short t 2.836, top-decile alpha +7.17%, monotonicity −0.891, PBO 73.3%, over 69
  rebalance dates on a genuine 18.5-year window (2008-01-16 → 2026-07-24).** The equal-weight
  benchmark moved +16.55% → +18.14%, which is the control and confirms the universe itself
  changed. **CORRECTED 2026-08-05 (audit session 3, X2+X7) — THE "TWO OF THREE BARS FAIL"
  READING WAS WRONG, IN BOTH DIRECTIONS, AND BOTH ERRORS CAME FROM UNCALIBRATED BARS MEASURED
  ON ONE ARBITRARY GRID.** It used to say: "t 2.836 is BELOW the Harvey–Liu–Zhu hurdle of 3.0
  it used to clear, and PBO 73.3% is far above the <50% bar." Both halves are now retired:
  * **t 2.836 vs the 3.0 hurdle is a GRID ARTEFACT.** X2 re-ran the whole backtest on seven
    equally valid rebalance grids (offsets 0/5/10/20/30/40/50 trading days; the grid always
    started at a hard-coded TD=252 and 62 other grids existed that nobody had ever looked at).
    All seven keep 69 dates over the identical window. **Long-short t ranges 2.703 → 3.517,
    median 2.926, and CLEARS 3.0 on three of the seven.** Quote **"t 2.7–3.5 depending on
    grid, straddling the hurdle"** — never one side of 3.0 as a fact.
  * **PBO <50% IS NOT A BAR AT ALL.** X7's placebo puts the MEDIAN PBO on a definitionally
    worthless signal at **46.7%**, i.e. the "<50%" bar sits exactly at the noise level and has
    almost no power. Calibrated bar is the placebo 5th percentile, **19.7%**. PBO is
    uninformative here in either direction — do not cite it as a pass or a fail.
  * **Top-decile alpha is the one headline that PASSED its robustness test:** spread across
    the seven grids is only **1.30pp** (median **+7.52%**, range +6.84% to +8.14%), against an
    equal-weight benchmark that itself moved 2.08pp across the same grids. The signal-driven
    number is steadier than the market-driven one it is measured against.
  Only the Deflated Sharpe still passes as originally stated — and X7 now DEFENDS it
  (see the calibrated-thresholds bullet below); per B9 the surviving criticism of it is the
  trial denominator, not the statistic.
  **ATTRIBUTED, one change per run, on the full universe — B6 IS ESSENTIALLY THE WHOLE DROP:**
  reverting B6 alone (B7+B13 still fixed) restores t 3.733, alpha +11.36%, PBO 26.7% at 110
  dates, so **B6 costs t −0.897, alpha −4.18pp and PBO +46.7pp — 100% of the PBO blow-out, 88%
  of the t drop, 89% of the alpha drop.** **B7 alone is NULL on the headline** (t −0.010, alpha
  +0.01pp, PBO and equal-weight unchanged to the digit) — a correctness fix with no performance
  consequence, which is the ideal outcome for one. **B13 alone is small and points both ways**
  (t +0.122, alpha −0.51pp, EW −0.24pp): dropping 384 penny names helps the long-short and costs
  the long-only book, consistent with penny names contributing at both ends of the ranking.
  **What this means: roughly 40% of the top-decile alpha was coming from the 41 early rebalance
  dates at which every name present was one that had already stopped trading.** State it as a
  hypothesis, not a finding — a repair's effect on a fitted statistic is not evidence about the
  repair. Costs still clear comfortably: breakeven 134 bps one-way against a **measured** 33.4
  bps realised (B11 — the old "37 bps" was an assumption quoted as a measurement). **No shipped
  decision changed:** `low_risk` still `confirmed` in both split directions, `insider` still
  `rejected`. Full three-way A/B in `HANDOFF_edge_audit.md` Part 3.
- **R1 RE-RUN, DONE 2026-08-05 (audit session 4) — THE THRESHOLD IS CLEARED AGAIN ON THE
  CORRECTED PANEL, AT A LOWER LEVEL AND WITH A DIFFERENT MECHANISM. CLAIM A STILL APPLIES.**
  The pre-commitment in `HANDOFF_r1.md` section 1 was honoured unchanged ("alpha" only if the
  FF5+MOM intercept is positive with NW t > 2.0; ambiguous is a NULL). Re-run on the corrected
  69-date panel → **68 non-overlapping 63d windows, 2009-01-15 → 2025-10-27**, deployed flat
  1/7 weights, NW lag 1. Alignment check passes (SPY on MKT: beta 0.933, R² 0.988).
  * **FF5+MOM alpha +6.99%/yr, NW t +3.984, R² 0.308** on the primary object (`top − ew`).
    **ALL SIX pre-registered specs are positive with t > 2.0** — compound/sum × full/first
    half/second half, spanning **+5.08% to +10.85%**. No disagreement, so the pre-registered
    NULL veto is not triggered. **QUOTE +6.99%/yr (range +5.1% to +10.9%)**; the conservative
    single number is the first half's +5.19%.
  * **THE OLD +8.81%/yr AND THE +6.6%–8.8% RANGE ARE VOID. Do not quote them anywhere.**
  * **THE MECHANISM REVERSED ON TWO OF ITS THREE LEGS — this is the part to re-read.** Now
    loading: **HML +0.251 (t +2.93)** and **UMD +0.205 (t +3.65)**. NOT loading: **SMB +0.208
    (t +1.39)** and **RMW +0.092 (t +0.90)**, both of which loaded strongly in the void run
    (SMB t 3.84, RMW t 4.49). So the old story — "`size`, `quality`, `momentum` ARE the
    standard premia; `value` and `capital_discipline` are not what FF measures" — is
    **backwards on size and profitability** and must not be repeated. Current honest reading:
    momentum is a genuine standard-premium exposure, the book now carries a real VALUE tilt,
    and the size/profitability exposures that dominated the old story were largely an artefact
    of the inverted-universe window B6 removed. R² fell 0.465 → 0.308 — the factor models
    explain LESS of this series than of the void one.
  * The unhedged small-cap tilt caveat WEAKENS for the spread (SMB +0.208, t 1.39, vs +0.885
    before) but SURVIVES for the long-only book (SMB +0.691, t 3.89).
  * Other objects: long-only book in excess of RF **+9.33%/yr (t 4.97)**; long-short
    **+14.86%/yr (t 4.18)**; the equal-weight universe's own unexplained excess +2.34% (t 2.92).
  * **CAVEAT THAT MUST TRAVEL: the secondary q-factor model does NOT clear on the first half**
    (q4 +3.17%, t 1.712; q5 +1.56%, t 0.702), though it clears on the full sample (+6.72%,
    t 3.19) and the second half (+11.49%, t 3.84). The pre-registered threshold is stated on
    FF5+MOM so this does not veto, but the early-period result is model-dependent.
  * Against X7's floor: raw top-decile alpha +7.13% is far outside the placebo null
    [−1.33pp, +2.38pp], so R1 is decomposing something real. **X7 does NOT calibrate a
    factor-regression intercept** — no placebo floor exists for R1's own t, and none was
    invented. Still ONE panel; **X8's international replication is the out-of-sample evidence,
    R1 is not.** Full entry: `HANDOFF_edge_audit.md` Part 5.
- **SUPERSEDED 2026-08-05 by the R1 RE-RUN above. Every number in the next bullet was measured
  on the pre-B6/B7 panel over a window that no longer exists, with a composite no shipped code
  path uses. Kept only as the record of what was claimed. DO NOT QUOTE IT.**
- **SETTLED 2026-08-04 (audit R1) — THE HEADLINE IS NOT MERELY FACTOR EXPOSURE. The word
  "alpha" is now permitted, as a RANGE and with caveats.** `top_decile_alpha` is still
  `4 × (mean top-decile 63d return − mean equal-weighted universe 63d return)` with no risk
  adjustment in it, but that object has now been regressed on the factors it was suspected of
  merely re-assembling. On the full 2,710-name universe, 109 non-overlapping 63-trading-day
  windows (1998-12-31 → 2026-01-21), deployed flat 1/7 weights: **FF5+MOM alpha +8.81%/yr,
  Newey–West(1) t +5.742, R² 0.465**; Hou–Xue–Zhang **q4 +9.14% (t +5.23)**, q5 +8.33%
  (t +4.37); long-short **+12.12% (t +4.14)**. Raw was +12.13%, so **the factor models absorb
  about 27% of the headline and leave the rest** — the opposite of the pre-registered
  expectation. It passes all four pre-registered specs (compound/sum × full/ex-B6), every
  subperiod, every NW lag 0–8, **net of costs (+7.85%, t 5.16)**, and a spanning test adding the
  EW universe's own excess return (+8.25%, t 5.88; universe loading t 0.63, insignificant).
  **QUOTE THE RANGE +6.6% to +8.8%/yr** — +6.6% (t 4.41) is the value after dropping the 37
  B6-contaminated early dates, and is the right single number when only one is wanted.
  **Mechanism:** SMB +0.39 (t 3.84), RMW +0.30 (t 4.49), UMD +0.18 (t 3.49) all load — `size`,
  `quality`, `momentum` ARE the standard premia — but **HML (t 1.08) and CMA (t 1.08) do not**,
  so `value` (six ratios, EV re-priced at the rebalance date) and `capital_discipline`
  (issuance/accruals) are not what FF measures. Not a benchmark artifact: alpha is linear, so
  α(top−ew) = 14.60 − 5.80 = 8.81 exactly and the +5.80% (t 5.41) that FF5+MOM fails to explain
  about the EW universe itself **cancels out of the spread**. **CAVEATS THAT MUST TRAVEL WITH
  IT:** it is still ONE panel — a regression is a control, not new data, and **X8's international
  replication is the out-of-sample evidence, R1 is not**; **t 5.74 is NOT multiplicity-corrected**
  (audit M1 still open), though the deployed weights are flat 1/7 and were never tuned; FF5+MOM
  is a poor description of this universe so read loadings as approximate; the book carries an
  unhedged SMB +0.885 small-cap tilt with borrow/impact/capacity unmodelled; and the benchmark
  is still uninvestable (audit R10). Reconciles with X4 rather than contradicting it — over X4's
  own 2014+ window R1 gets +6.06% (t 3.16) where X4 got t 1.10, because X4 differences two
  high-variance total-return series (low power) while R1 removes that variance first (high
  power). Full write-up and the pre-commitment (written before any number) in `HANDOFF_r1.md`;
  reproduce with `python -m scripts.factor_alpha`, pinned by `tests/test_factor_alpha.py`.
- **R1 FRAGILITY (2026-08-04, same lane) — the result SURVIVED a deliberate attempt to break it,
  but it is WINDOW-DEPENDENT and has a WEAK DECADE, and it is PROVISIONAL until re-run.** Four
  criteria were committed before any cut ran; all four passed. **(1) Stable-universe window
  (≥2008, the closest available preview of what B6 will do): alpha +6.24%, t +3.986, n 73 —
  DOWN 2.57pp, about 29% of the alpha.** The discarded early period is where the raw spread is
  biggest (first third raw +21.89%/yr vs +3.53% and +11.02%), exactly the inverted-universe
  signature. **Expect the post-B6 headline near +6%, not +8.8% — quote ~+6% when one number is
  wanted.** (2) No sign flip: halves +8.98% (t 3.38) / +5.48% (t 3.12); thirds +13.51 (t 3.59) /
  **+4.33 (t 2.412, the weakest cell in the study)** / +8.10 (t 3.82). (3) **Not concentrated:**
  the best 5 of 109 periods carry 23.0% of the alpha (38.0% on the stable window, the criterion
  that came closest to tripping); dropping the best 5 leaves +7.28% (t 5.19), dropping the worst
  5 gives +10.07% — nearly symmetric, and the best 5 are spread across four regimes. (4) **Not
  specification-dependent:** CAPM +12.99%, FF3 +12.28%, FF5-no-MOM +10.03%, FF5+MOM +8.81%,
  q4 +9.14%, q5 +8.33% — all t > 2 on BOTH windows, and **FF5+MOM is nearly the most conservative
  of the six**, so the headline is quoted from the most demanding pre-registered model, not the
  most flattering. **THE ONE THING THAT LOOKS BAD: a ~10-year rolling window centred on 2009-2019
  shows alpha of only +1.66% (t 1.39).** Alpha is positive in 70 of 70 rolling windows and never
  reverses, but 8 of 70 are not significant — the full-sample t 5.742 averages a weak decade in
  with strong ones. Windows confirmed **genuinely non-overlapping** (all exactly 63 factor days,
  zero shared days), so no inference correction is needed. **BINDING: R1 MUST be re-run after B6
  and B7 land** — B6 is expected to lower alpha to +5.5-7.0%; B7's direction is unknown; a
  post-re-run alpha < +4%/yr or full-sample t ≤ 3.0 is a MATERIAL REVISION that requires
  rewriting the headline, and a stable-window t ≤ 2.0 withdraws the word "alpha" entirely. Full
  contract and every cut in `HANDOFF_r1.md` §6-8; reproduce with
  `python -m scripts.factor_alpha_fragility`, pinned by `tests/test_factor_alpha_fragility.py`.
- **Zeroing `insider` was tested the same way and REJECTED — it stays at 0.125.** It helped one
  split direction by a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample
  t-stat is not a stable property. Same reasoning as `low_risk`, opposite outcome — which is
  why every theme change now has to clear `holdout_theme_validate()` before it ships.
- **CORRECTED — "the entire edge is the institutional (13F) theme" is OBSOLETE.** Strip the
  institutional theme now and top-decile alpha is still **+10.6%** with long-short t **2.86**
  (it used to collapse to 0.71). That finding was an artifact of `quality` and `low_risk`
  running on half their inputs. 13F is a contributor, not the whole edge.
- **CORRECTED — `monotonicity`'s SIGN WAS BEING READ BACKWARDS everywhere.** Deciles are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal) and +1.0 = backwards.**
  The old bullet "monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
  cleanly ordered" said the opposite of the truth: −0.68 meant they *were* well ordered.
  Current value −0.939. Pinned by `test_monotonicity_sign_convention`.
- **CORRECTED — `low_risk` does NOT have pooled IC −0.048.** With both its inputs finally
  populated it is **−0.0014 (t +0.71)** on the full universe: indistinguishable from zero.
  It was dead weight, not actively harmful. It is **−0.352 correlated with `size`** — the
  strongest anticorrelation in the theme matrix — so it was cancelling the small-cap tilt,
  which is why removing it helped so much despite having no signal of its own.
- **CORRECTED AGAIN 2026-08-07 (claims audit) — `institutional` coverage is 71.7%, and `insider`
  is 83.1%.** This bullet read "**`institutional` coverage is 61.4%**, not the 81.7% previously
  recorded". 61.4% was measured on the P6-era 110-date panel (that file reads 0.6140 in the same
  field); the current run reads **0.7172**. It rose for a mechanical reason worth knowing: B6
  dropped the 41 pre-2008 dates, and the theme is **empty before 2013-06-30**, so removing empty
  dates raises its coverage without adding any data. Same check on `insider`: **85.0% → 83.1%**
  (0.8504 → 0.8308). Any early-period comparison involving `institutional` is still uninformative
  rather than negative.
- **THEME ICs — CORRECTED 2026-08-06 (session 6, X3 re-run). THE TABLE THAT SAT HERE WAS A
  PRE-B6 MEASUREMENT MISLABELLED "CURRENT", AND `size` IS THE ENTRY THAT MOVED MOST.** It read
  "quality +3.57, momentum +2.62, capital_discipline +2.25, institutional +1.81, size +1.68,
  value +1.52, growth +1.45, low_risk +0.71, insider −0.43". **Proven stale, not inferred
  stale:** re-running `theme_ic` on the old 110-date panel reproduces that list to the digit
  (momentum +2.62, capital_discipline +2.25, institutional +1.81, size +1.68, growth +1.45,
  low_risk +0.71), so it was measured before the B6/B7/B13 corrections of 2026-08-04 and
  carried forward with a date that made it look newer than the panel it came from.

  | theme | void (110 dates) | **CORRECTED (69 dates)** | move |
  |---|---|---|---|
  | quality | +3.57 | **+3.10** | −0.47 |
  | capital_discipline | +2.25 | **+2.76** | **+0.51 — the only riser** |
  | institutional | +1.81 | **+1.55** | −0.26 |
  | momentum | +2.62 | **+1.31** | −1.31 |
  | value | +1.52 | **+0.84** | −0.68 |
  | growth | +1.45 | **+0.75** | −0.70 |
  | low_risk | +0.71 | **+0.46** | −0.25 |
  | insider | −0.43 | **−0.24** | +0.19 |
  | **size** | **+1.68** | **−0.30** | **−1.98** |

  **Against X7's calibrated bar of 2.71, TWO of nine themes clear: `quality` and
  `capital_discipline`.** Under the retired 2.0 convention the void table showed three, and
  X7 measured that 39% of pure-noise draws produce at least one theme at t ≥ 2.0. **`size` is
  now the WORST-ranked theme and the one whose removal costs the most** — see the X3 bullet
  below. sentiment still empty.
- **A FULL BACKTEST IS NOT REPRODUCIBLE RUN TO RUN, AND THE INSIDER THEME IS WHERE IT SHOWS.
  Found 2026-08-04; unexplained; do not build on any single run's insider number.** Three
  full-universe runs on identical data gave `insider` median IC **−0.00335 (t −0.34)**,
  **+0.01551 (t +2.69)** and **−0.00339 (t −0.43)** at unchanged 85.0% coverage. The first and
  third bracket the second and agree to four decimals, so the middle run is the anomaly and
  **audit B26 (the same-day-filing exclusion) is NOT the cause** — an earlier note in this file
  said it was, and that was wrong. B26's effect was measured directly on 22,975 (ticker, date)
  score pairs: it alters **3.96% of scores at a level correlation of 0.9975**, consistent with
  the ~0 IC change between the runs that bracket it. Every other theme is stable to ±0.01 across
  all three runs. **What this means: `insider`'s IC sits so close to zero that its t-statistic is
  not a measurable quantity**, which is exactly why zeroing it came back `not_replicated`
  (Δt +0.08 one direction, −0.09 the other). It is also a reproducibility problem in its own
  right — a project whose memory is its results files needs its results files to be
  deterministic. **Next session: find the nondeterminism before trusting any marginal IC.**
  Audit item **S3** (the `+min(10, 2·buys)` bonus is unconditionally additive; `tanh(net/5e6)`
  saturates regardless of company size) is the thread that might make this theme measurable.
- **Historical note:** `insider` is the only negative theme, and still carries 12.5% weight — but
  zeroing it **did NOT replicate** out-of-sample, so it was deliberately left alone.
- **Theme ICs are NOT stable across time.** `low_risk` flips −0.031 → +0.041 between halves and
  `size` flips t +3.17 → −0.67 (the small-cap premium worked pre-2012, not after). Treat any
  single-period theme IC as weak evidence; the held-out split is what settles a decision.
- **13F is NOT a look-ahead artifact (settled July 2026, 800 names).** Feeding it *fresher,
  not-yet-filed* data at a 15d lag makes it WEAKER, not stronger (t 1.49 -> 0.66, Deflated
  Sharpe 84% -> 44%) — the opposite of the artifact signature. The panel's effective lag is
  already ~111 days (an April rebalance uses the December quarter, public since mid-February),
  i.e. more conservative than the 45d deadline. Its decay curve is sensible: peaks at Q-1,
  alive at Q-2 (t 1.36), dead by Q-3 (t -0.04).
- Edge is strongest in **large caps** (regime IC highest there).
- **P6: THE EDGE SURVIVES TRADING COSTS — BUT ITS COST PROFILE IS STALE. CORRECTED 2026-08-07
  (claims audit).** It read: *"Top-decile breakeven is **236 bps one-way** against a
  **37 bps** actual cost profile (~6.4x margin); net alpha **+11.41%/yr** after costs on 249%
  annual turnover."* On the corrected 69-date panel the `costs` block reads **breakeven 134.1 bps
  one-way against a measured 33.4 bps (4.0x margin), net top-decile alpha +6.07%/yr on 261%
  annual turnover.** (The corrected-panel bullet above already fixed breakeven and the "37 bps was
  an assumption, not a measurement" point (B11); the net alpha and turnover here were never
  updated.) **The conclusion is unchanged — a 4.0x margin still clears comfortably.** The
  bottom-decile figures in the next sentence are P6-era and were NOT re-measured by the claims
  audit — treat them as unverified, not as corrected. The short
  side does not break it either — the BOTTOM decile is *larger*-cap
  than the top ($4.50B vs $1.95B median, 29.8 vs 37 bps), so the long-short t does not rest on
  unborrowable micro-caps. Borrow cost is not modelled (affects the long-short statistic, not
  the long-only book). Quote the BREAKEVEN, not the net alpha — it needs no belief in any
  particular cost calibration. Measured on every run now (`costs` block).
- **P6: three plausible refinements were tested and ALL THREE REJECTED.** Do not re-open them
  without a new reason: **(a) TTM ROE/ROIC is WORSE than quarterly** (roe t +2.84 vs +2.01,
  roic +3.38 vs +2.57) — recency beats smoothing, and the earlier note calling quarterly a
  "wart" was wrong; **(b) median/MAD robust z-scores HALVE the long-short t** (3.485 -> 1.721);
  **(c) consolidating momentum+institutional loses** (LS t 3.48 -> 2.53) — +0.50 correlated but
  complementary, both earn a full weight.
- **P6 lesson worth keeping: a signal's IC can be flat while the composite built from it moves
  a lot.** Robust z-scores left every theme IC essentially unchanged (quality +3.39 -> +3.35)
  while halving the long-short t. Rank-IC is INVARIANT to a monotone rescaling; the composite
  is a weighted SUM of z-scores and is very much scale-sensitive. **Never judge a
  standardization or scaling change by per-signal IC.**
- **CORRECTED — `sector_neutral` WAS silently inert; it is now wired, TESTED, and REJECTED.**
  The old text ("no sector column anywhere on disk ... BLOCKED until TICKERS is downloaded") is
  obsolete: TICKERS was downloaded in P10 and the panel populates `metrics["sector"]` from it.
  Sector coverage is **100.0% of panel rows** (2,710/2,710 names, 11 sectors), so the toggle
  genuinely changes every z-scored theme instead of grouping on a constant. It was then measured
  on the full universe and **rejected in both held-out directions, twice** (P10, and an
  independent re-run 2026-08-02 on a panel that had since gained several signals). Under the
  DEPLOYED weights it raises long-short t 3.396 → 3.896 but COSTS top-decile alpha
  +11.82% → +10.24%, worsens monotonicity −0.952 → −0.915 and nearly doubles PBO 26.7% → 46.7%;
  the later half is worse on both metrics. `sector_neutral` stays **OFF**. Full numbers in
  `HANDOFF_sector_neutral.md`; wiring pinned by `tests/test_sector_neutral.py` so it cannot
  silently go inert again. TICKERS gives TODAY's classification, so applying it to 1998 rows is
  a mild look-ahead — the one non-point-in-time input in the panel, which is a reason to be MORE
  sceptical of a positive sector result, not less. It rejected anyway, so nothing rests on it.
- **P7: THE VALUE THEME WAS CURRENCY-CORRUPTED and is now fixed.** `marketcap`/`ev` are USD but
  the raw line items are in the REPORTING currency, so every value ratio was wrong for the 4.1%
  of rows that report abroad — SK Telecom's `book_to_price` computed to **892 vs a true 0.589**.
  All six value inputs improved after the fix (**value theme t +1.34 → +1.46**), **PBO halved
  13.3% → 6.7%**, monotonicity −0.939 → −0.952, top-decile alpha +11.77% → +11.82%. Foreign
  over-representation in the top decile went **1.35x → 0.56x**; in the live book, foreign names
  fell from 21 of 86 positions (28.3% of weight) to 11 (10.7%).
- **`fxusd` IS A DIVISOR, NOT A MULTIPLIER** — local units per USD (SKM 1514.2 won/USD). Using
  it as a multiplier squares the error. There is **no `netincusd`** column; use `netinccmnusd`.
  `total_equity` must stay LOCAL — `gp_on_capital` divides local gross profit by it.
- **ENTERPRISE VALUE IS NOW PRICED AT THE REBALANCE DATE (2026-08-03, shipped ON).** Sharadar's
  `ev` embeds the FILING-date market cap, so `ebit_ev`/`ev_sales`/`ev_ebitda` measured cheapness
  against a ~111-day-old quote while `earnings_yield`/`fcf_yield`/`book_to_price` used the fresh
  one. `_pit_ev()` re-prices the EQUITY leg to the PIT market cap and holds the DEBT leg at its
  last filed value (net debt is only observable at a filing — that IS point-in-time). Net debt
  must be **currency-converted before it is added** — P7 in a second costume. Re-pricing moves EV
  a **median 5.1%** (26.7% of rows >10%), and `neg_ev_sales` median IC goes **+0.0214 → +0.0363**.
  The BOOK is a wash (LS t 3.396 → 3.520, alpha +11.82% → +11.88%, PBO/monotonicity unchanged,
  net top-decile alpha slightly worse) — **it ships on correctness, not performance.** Stale, not
  look-ahead, so no past result is invalidated upward. New **`ev_freshness`** block (100.0% fresh)
  makes a silent revert loud; `EDGE_EV_POINT_IN_TIME=false` reverts. `HANDOFF_ev_fix.md`.
  STILL OPEN: negative EV (net cash > market cap, 0.70% of rows) is read as maximally cheap by
  `neg_ev_sales` and as expensive by `ebit_ev` — a live sign inconsistency, deliberately not
  bundled into this change.
- **P8: a SANITY layer now runs every backtest** (`sanity_check` block): range / subgroup-pegging
  / market-cap divergence. Coverage says a factor is PRESENT, this says it is SANE — the
  currency bug filled every column and coverage was blind to it. Verified it WOULD have caught
  P7 (foreign names sat at the 86th percentile of book_to_price and earnings_yield pre-fix).
  It legitimately fires twice on corrected data (foreign names really are large caps; 1.45% of
  rows have a >3x market-cap divergence, AIV 71x / EQC 53x). **Do not silence a flag to make the
  run green** — investigate it or record why it is expected.
- **CODE_AUDIT.md's M2 (SanDisk/WDC ~10x) does NOT reproduce.** DAILY cap and shares x price
  agree to 1.6x, the share count is plausible, and the price ran 29.6x over 17 months with zero
  discontinuities (WDC 10.3x, MU 8.5x — the whole storage complex). If it is wrong the error is
  upstream in the PRICE, which both estimates share. Unresolved, not fixed.
- **Standing caveats, do not drop them — TWO OF THEM WERE RETIRED BY MEASUREMENT AND ARE
  CORRECTED HERE 2026-08-07 (claims audit). This bullet says "do not drop them", so both wrong
  caveats were being propagated on purpose; that is why they are corrected rather than deleted.**
  * **The Deflated Sharpe caveat WAS WRONG.** It read: *"Deflated Sharpe is a saturated
    0.9999991 and, per the B9 correction at the top of this section, it is an **undeflated PSR**
    — not a proof of anything."* Both halves are void since M1 (2026-08-05): the shipped run is
    **0.8997 at N = 84 and 0.8674 at the current N = 116** — not saturated — and it self-reports
    `metric = deflated_sharpe_ratio` with `is_effectively_undeflated = false` (`sr0` 0.406
    against a per-period Sharpe of 0.550). **The live caveat is the opposite one:** it is a
    genuine Deflated Sharpe that **FAILS** the >0.95 convention while sitting above all 100
    placebo draws (X7 floor 0.72). Quote it whole, per the M1 bullet.
  * **The B8 caveat is STALE.** It read: *"the test is a **both-halves stability check rather
    than an out-of-sample confirmation** (B8)"*. B8 was fixed in session 7: `oos_verdicts` now
    enforces the documented rule alongside the frozen `stability_verdicts`, and `low_risk` reads
    `confirmed_oos`. The surviving caveat is narrower and is stated in the B8 bullet above —
    **`low_risk` is confirmed out-of-sample in ONE of two split directions, not two.**
  * Still true, unchanged: both halves come from the same panel and universe, and the
    size-cancellation mechanism was hypothesised on the full sample — so neither the decision nor
    the hypothesis generation is out-of-sample in the strict sense. The concentrated top-25 book
    is the noisiest number in the file, and per audit **B17** it holds up to FIFTY names (it sells
    only below `exit_rank = top_n × 2`) and pays neither costs nor taxes, unlike every other book
    in the results file — so it is also mislabelled. Weight-tuning itself remains noise-chasing:
    CPCV still adopts no weighting over the defaults. (All three re-verified 2026-08-07:
    `exit_rank = top_n * 2` at `fundamental_panel.py:1710`, which also ships a `label_warning`
    saying the realised book size is ~`exit_rank`, not `top_n`; `cpcv.adopt = false`.)
- **FIXED 2026-08-04 (audit session 2). The panel is now a genuine 18.5-year window,
  2008-01-16 → 2026-07-24, 69 rebalance dates, cross-sections 1,471–1,954.** `days=None` means
  the whole series and the shared calendar is cut ONCE, before the ffill. Each run ships
  `panel_window` (available vs retained range, the cut, per-date cross-section sizes) so the
  two-blocks-disagree-about-their-window failure cannot recur silently. **41 of the 110 dates
  were dropped and the headline fell with them — see the CORRECTED PANEL bullet above; this was
  the most expensive correction in the audit.** The description below is what the defect WAS:
- **The panel is 27 YEARS long, not 18, and its first third has an INVERTED universe (audit
  B6, FIXED — see above).** `WRDSProvider.price_history` truncates with `.tail(4659)`, so each
  ticker keeps its OWN last 18.5 years and the calendar is the union: 1998-12-31 → 2026-04-22,
  110 rebalance dates over 27.3 years. At a 2001 cross-section every name present is one that
  stopped trading by roughly 2019 — the inverse of classic survivorship bias, and it makes
  roughly the first 37 of 110 periods uninterpretable. Those same 37 dates have no benchmark,
  which is why `construction.n_periods` reads 110 while `portfolio.n_periods` reads 73 in the
  same JSON over undisclosed windows. Direction of the bias is genuinely unclear.
- **FIXED 2026-08-04 (audit session 2, B7/G). There is now ONE composite**, used by selection,
  measurement and live, and it renormalises by the present-weight mass — the convention
  SELECTION already used, so the deployed weights were chosen under it. `CONFIG.sector_neutral`
  and `CONFIG.residual_momentum` now default **false**. **Live and backtest score identically**
  (max abs difference 0.0), pinned by
  `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`. Measured effect on the
  headline: **NULL** (t −0.010, alpha +0.01pp) — the disagreement was real in mechanism but
  small in magnitude on this panel. The description below is what the defect WAS:
- **The LIVE product does not score names the way the backtest does (audit B7/G, FIXED — see
  above).** `screen.py:256` (now **`screen.py:232`**, re-resolved 2026-08-07) calls
  `build_frame(metrics)` with no keyword arguments — it still does, which is now CORRECT because
  the CONFIG defaults are false; at the time it inherited
  `CONFIG.sector_neutral` (default **true**) and `CONFIG.residual_momentum` (default **true**),
  while the backtest forces both `False`. Sector-neutral ranking was tested on the full universe
  and rejected in both held-out directions, twice. **Unless `SCREENER_SECTOR_NEUTRAL=false` is
  set in the environment, the hot list users see is scored under the intervention the research
  eliminated.** There are also three different composite functions in the tree (selection
  renormalises by present-weight mass, measurement does not, live renormalises AND adds the two
  interventions), so **no shipped code path reproduces the backtested composite exactly.**

**HISTORICAL — P5 era, 2026-07-30. DO NOT READ THIS FIRST; MOST OF IT IS SUPERSEDED BY THE
BULLETS ABOVE.** **CORRECTED 2026-08-07 (claims audit): this header used to read "LATEST
(2026-07-30) — SUPERSEDES much of CURRENT STATE above. Read this first." That was true when
written and is now backwards** — `CURRENT STATE` above carries material through 2026-08-06, so
the old instruction sent a cold reader to the OLDEST numbers in the file and told them they
superseded the newest. In particular the "CLEARS both bars for the first time" bullet below
(PBO 13.3%, Deflated Sharpe ~100%, long-short t 3.485, top-decile alpha +11.77%) is **void** —
it was measured on the pre-B6 110-date panel. The live numbers are t 2.836 / alpha +7.17% /
PBO 73.3% / DS 0.8674. The three era headers read newest-to-oldest: **CURRENT STATE (through
2026-08-06) → this section (2026-07-30) → PREVIOUS (2026-07-29).**
- **Five wired factors were SILENTLY EMPTY in every run this project has ever done.** The
  Sharadar export is ARQ-only and Sharadar fills its ratio/averaged columns only in ART/ARY:
  `roe`, `roic`, `assetturnover` are non-null in **0 of 197,265 rows**. `beta` was hard-coded
  `None`. `growth_accel` was overwritten with all-NaN by `build_frame`. So `quality` averaged
  **8 of its 10** inputs, `low_risk` **1 of 2**, `growth` **1 of 2** — with no error, ever.
  All four are now derived from line items that were present all along. `_f()` also returned
  NaN instead of None, which made `_f_score` count MISSING tests as FAILED ones.
- **A coverage guard now exists and would have caught every one of them**: `signal_coverage()`
  warns on any wired signal under 5% coverage and ships a `signal_coverage` block in
  BACKTEST_RESULTS.json. **Never trust a factor's IC without checking its coverage first.**
- **roic (t +3.38) and roe (t +2.84) are the 4th and 6th strongest signals in the panel** and
  were contributing nothing. `quality` is now the strongest theme (t +3.39).
- **`monotonicity`'s SIGN HAS BEEN READ BACKWARDS throughout these notes.** Buckets are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal), +1.0 = backwards.**
  The "monotonicity is negative ... the deciles aren't cleanly ordered" line above is WRONG,
  and P4's "−0.782 → −0.855, slightly worse" was an improvement. Now pinned by a test.
- **`low_risk` zeroed (live, reversible).** Its real full-universe IC is −0.0014 (t +0.71),
  NOT the −0.048 claimed below — dead weight, not harmful. It is **−0.352 correlated with
  `size`**, the strongest anticorrelation in the theme matrix: low-beta/low-vol names ARE
  large caps, so it was cancelling the small-cap tilt. `neg_asset_growth` also dropped
  (t −0.70, wrong sign).
- **The full-universe verdict CLEARS both bars for the first time: PBO 13.3%, Deflated Sharpe
  ~100% (saturated), long-short t 3.485, top-decile alpha +11.77%.** BUT the biggest
  contributor (zeroing low_risk) was chosen by looking at this same panel, so it is
  **in-sample-informed and needs out-of-sample confirmation** — HANDOFF_STATUS.md §5.
- **"The entire edge is 13F" is now OBSOLETE.** Without the institutional theme, top-decile
  alpha is still +10.6% and long-short t 2.86 (was 0.71). That finding was an artifact of
  quality/low_risk running on half their inputs.
- **`insider` is the only negative theme (t −0.34, now −0.43) and still carries 12.5% weight** —
  the obvious next candidate, deliberately NOT changed. **See the reproducibility note above:
  one of three identical-data runs returned +2.69, so this theme's t is not a measurable
  quantity in either direction. The held-out verdict is `rejected` in all three runs.**
- Real full-universe coverage: `institutional` **61.4%** (not the 81.7% below), `insider`
  85.0%. F-Score is **t +2.74** on the full universe, not +5.66.

**PREVIOUS (2026-07-29) — several claims below are corrected above:**
- **800-name large-cap run:** PBO 13%, Deflated Sharpe 77%, first CPCV "adopt" (`ic-ir`), top-decile
  +4.1%/yr vs equal-weight. BUT it's the friendlier large-cap universe (not the fair 3,000), still
  <95%, still ~1/3 13F-dependent. **The full 2,827-name run has STILL never completed** (scoring loop slow).
- **F-Score is the strongest new signal** (IC t +5.66), wired into quality; accruals + 13F-holder-breadth
  also kept. Classic anomalies (reversal, idio-vol, MAX, low-vol) did NOT replicate here.
- **`low_risk` theme has NEGATIVE pooled IC (-0.048)** and CPCV zeroed it — a live factor that's hurting;
  not yet changed (Don's call).
- **`assets` was silently dropped by the loader**, so `capital_discipline` was half-empty in every prior
  run — fixed; treat past capital_discipline conclusions as unreliable.
- **Bulk data loaded fast+safe** via `valuation/edge/bulk.py` (raw zips in `data/raw/`, extracts in
  `data/bulk/`, caches in `data/bulk/prepared/`): SF3 per-manager conviction, DAILY point-in-time
  marketcap+ratios, ACTIONS splits/delistings, EVENTS raw codes.
- **Now CONSUMED by the panel (2026-07-29 s3):** point-in-time market cap from DAILY (replaces the buggy
  shares×price path; AAPL 2015Q2 $722.6B verified), survivorship-free returns via the ACTIONS delisting
  mask (SEP is ALREADY split-adjusted, so split ratios deliberately NOT re-applied — don't "fix" that),
  SF3 conviction exposed as inputs (`sm_conviction/holders/breadth`, not yet in a theme). `institutional`
  coverage 70.5%→81.7%. STILL PENDING: scoring loop unvectorized; **full 2,827-name run has never completed.**

## METHODOLOGY RULE (hard — do not violate)
**CORRECTED 2026-08-07 (claims audit): THE FULL UNIVERSE IS ~2,531 NAMES, NOT ~2,710. This rule
used to name 2,710 and an agent seeing 2,531 could reasonably think it was looking at a subset
and withhold a verdict.** 2,710 was the P6-era 110-date panel (`git show b0f70b6:BACKTEST_RESULTS.json`
= 2,710 names / 110 dates); every run since the B6/B13 corrections of 2026-08-04 reads
**`universe.n_names` 2,531, `n_dates` 69, `label` "full"**. The rule itself is unchanged and the
code enforces it: `WRDSProvider.universe` returns the whole export when `limit` is None or >= its
size, and prints a "SMOKE-TEST SUBSET, not a verdict" banner otherwise (`data_providers.py:388-409`).
Read "~2,710" as "~2,531" wherever it still appears below.

**Report verdicts ONLY from the full ~2,531-name universe.** 400/800-name subsets systematically
flatter results (PBO 13% on 800 → 53% on full; `sm_breadth` t 2.37 on 800 is unverified on full).
**CORRECTED 2026-08-03 (audit B12): the 800-name era was an ALPHABETICAL slice, not the 800
largest.** `WRDSProvider.universe` returned `sorted(keys)[:limit]`, so those runs were names
beginning with roughly A through C. "PBO 13% on 800 → 53% on full" was therefore never measuring
how much a large-cap tier flatters results — it was measuring how much an ARBITRARY 30%
alphabetical subsample does. The function is fixed (ranked by market cap, sort key printed in the
banner, subsets labelled smoke tests), but **every 800-name-era figure needs a full-universe
re-run before it is cited again**: the first CPCV "adopt", PBO 13%, Deflated Sharpe 77%,
`f_score` t +5.66, `sm_breadth` t 2.37, the 13F look-ahead stress test, and the four
classic-anomaly rejections (short-term reversal, idio-vol, MAX, low-vol).
Small samples are dev smoke-tests only ("does it compute / not crash") and MUST be labeled as such —
never the number a keep/reject/adopt decision rests on. The full run is now fast (~75s load + ~11s
score), so there is no performance excuse to judge on a subset. If you must screen small first, say
"smoke test" explicitly and re-run the survivor on the full universe before reporting a verdict.

## IMMEDIATE NEXT TASKS (in order) — item statuses re-checked 2026-08-07 (claims audit)
> **This list is the least trustworthy section in the file. Of the three OPEN items checked
> against the tree on 2026-08-07, TWO were already closed** — #16 rejected with numbers on
> 2026-07-31, #18 shipped — **and #12 had been built in this repo while still routed to Cowork.**
> The list was stamped "updated 2026-07-30" and has taken landings from several sessions since.
> **Check `VALQUO_LEDGER.md` and the tree before starting any item here.**
1. ~~Wire the bulk caches into `build_fundamental_panel`~~ **DONE (2026-07-29 s3)** — PIT market cap from
   DAILY, ACTIONS delisting mask (splits NOT re-applied; SEP already adjusted), SF3 conviction exposed as
   inputs. (Coverage figure in that note was wrong: `institutional` is **61.4%** on the full universe.)
2. ~~**Add unit tests for `bulk.py`**~~ **DONE** — 12 tests.
3. ~~**Speed up scoring + complete the full 2,827-name run**~~ **DONE** — the full run now takes ~12 min
   end to end, and one duplicate full panel build was removed from it (2026-07-30).
4. ~~**P3 — SF3 smart-money conviction**~~ **DONE (P4 commit)** — `sm_breadth` kept, the rest rejected.
5. ~~**Fix hurting factors**~~ **DONE (2026-07-30)** — but only after discovering the factors were EMPTY;
   see LATEST. `neg_asset_growth` dropped (t −0.70), `low_risk` zeroed (IC −0.0014, −0.352 corr with size).
6. ~~**Confirm the `low_risk` removal out-of-sample**~~ **DONE (2026-07-30) — CONFIRMED.** Held-out
   time split, both directions: long-short t +1.59 / +2.02, top-decile alpha +3.21pp / +7.86pp on
   data that did not inform the decision. Now a PERMANENT check: `holdout_theme_validate()` runs on
   every backtest and ships a `holdout_validation` block in BACKTEST_RESULTS.json.
7. ~~**Test zeroing `insider`**~~ **DONE — REJECTED, left at 0.125.** Helped one split direction by
   a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample t is not stable.
8. ~~**TTM ROE/ROIC**~~ **DONE — REJECTED (P6.2).** Quarterly is BETTER (roe t +2.84 vs +2.01,
   roic +3.38 vs +2.57). Recency beats smoothing. Don't re-open without a new reason.
9. ~~**turnover/cost-aware construction**~~ **DONE (P6.1) — THE EDGE SURVIVES COSTS.** Breakeven
   236bps one-way vs ~37bps actual; net top-decile alpha +11.41%/yr. Measured on every run.
10. ~~**median/MAD robust z-scores**~~ **DONE — REJECTED (P6.3).** Halves the long-short t.
11. ~~**Consolidate momentum/institutional**~~ **DONE — REJECTED (P6.4).** Both earn full weight.

**OPEN, in priority order:**

12. ~~**Forward paper-track vs SPY**~~ **BUILT IN THIS REPO — CORRECTED 2026-08-07 (claims
    audit).** This item used to read "the top priority … → **Cowork's lane**. Tell Don to take it
    there." **Do not tell Don that.** It was built in this lane and it is here:
    `valuation/edge/paper_track.py` (its own docstring: "roadmap #12, the project's #1 remaining
    validation"), plus `paper_broker.py` (refuses any non-sandbox endpoint), `options_tracker.py`,
    `track_export.py`, and `tests/test_paper_track.py`. First landed at `cde1579`. The RATIONALE
    is unchanged and still the strongest open argument in the project — the edge has only ever
    seen this one Sharadar panel, and a forward track is the only thing that tests it on data
    nobody has looked at. What remains is elapsed time and reading the track, not building it.
13. ~~**Industry-relative ranking**~~ **DONE and now CLOSED PERMANENTLY — REJECTED a third time
    on 2026-08-11, this time on the CORRECTED panel (`SECTOR-NEUTRAL-B6`).** The two rejections
    described below both ran on the **void pre-B6 panel**; the re-run puts the same gate on the
    69-date panel and finds sector-neutral **worse on BOTH metrics**, with the long-short gain
    that motivated the trade-off **reversed** and the sector-neutral arm **below the calibrated
    long-short floor**. See the session-20 bullet in CURRENT STATE. **It may not be re-run
    again** — the only routes back are `S25` (point-in-time sector map) and `S15` (value theme
    alone). The rest of this item is the record of the earlier runs: **unblocked (P10), then
    REJECTED and re-confirmed 2026-08-02.** Sector is wired from TICKERS at 100% coverage and pinned by
    `tests/test_sector_neutral.py`; sector-neutral ranking fails the held-out gate in both
    directions under both flat and deployed weights (it buys long-short t and sells top-decile
    alpha — the wrong trade for a long-only book). Stays OFF. `HANDOFF_sector_neutral.md`.
    A NARROWER variant (sector-relative on the value theme alone) is now cheap to test and is
    the only version worth re-opening.
14. **Watch live behaviour after the P5 deploy.** `low_risk` 12.5% → 0 tilts the hot list
    smaller-cap. Intended, but eyeball the first scans; revert is one line in `settings.py`.
15. ~~**PEAD from EVENTS**~~ **DONE — REJECTED (2026-08-01, independently re-verified
    2026-08-03).** EVENTS code 22 was decoded, so it was finally testable. `pead_car` clears
    the standalone bar (median IC +0.0100, **t +2.215**, coverage 82.3%) but earns no weight;
    `pead_drift` fails outright (t −0.473, coverage 25.1% under the 30% floor). Two reasons the
    reject is solid, both stronger than the IC: **(a)** residualized on the three momentum
    inputs, pead_car's incremental IC t is **+0.020** — 89% of it is orthogonal to momentum and
    that 89% predicts nothing; **(b)** the book gain it does produce is beaten by a control
    using NO earnings data (counting `ret_6_1` twice: +0.83pp alpha vs pead_car's +0.52pp). It
    correlates most with the strongest momentum input and least with the weakest, so it acts as
    an implicit REWEIGHTING, not a new signal. Also **not actually PEAD**: theory says drift is
    strongest right after the announcement, but the recent-only window scores t −0.473 against
    the all-ages +2.215 — backwards. **Held-out deltas for PEAD are CONSTRUCTION-SENSITIVE and
    even flip sign** between the full composite and a restricted-universe book — never quote one
    without naming the book. Both variants stay MEASURED but score in no theme. Point-in-time is
    pinned by `tests/test_pead.py` (12 tests, incl. a tampering test). `HANDOFF_pead.md`.
    Re-open only with real point-in-time earnings surprises (IBES, parked — same blocker as #20).
16. ~~**ML tree combiner**~~ **DONE — TESTED AND REJECTED 2026-07-31. CORRECTED 2026-08-07
    (claims audit): this sat in the OPEN list reading "clearly worthwhile now", one day after it
    had already been rejected with numbers.** Pre-registered results-free at `620e0a5`
    (`valuation/edge/ml_combiner.py`, protocol and adoption bar fixed before any run), then
    rejected at `f53b248` — "TESTED AND REJECTED on every criterion". Numbers (`CODE_AUDIT.md:15`):
    **median OOS IC +0.0531 linear vs +0.0393 GBM; net alpha −8.2pp roth / −4.0pp taxable; fails
    in BOTH halves.** Judged on the same CPCV paths as the linear candidates. **Closed, not
    pending — re-open only with materially more data, not a different model.**
17. **Re-read every past "monotonicity" conclusion with the sign flipped** (see LATEST).
18. ~~**Social preview:** Open Graph + Twitter Card meta tags~~ **SHIPPED — CORRECTED 2026-08-07
    (claims audit).** `valuation/web/templates/_saas_base.html:34-44` carries `og:title`,
    `og:image` (+ `secure_url`, `type`, **1200×630**, `alt`) and `twitter:card=summary_large_image`,
    with a comment that `og:image` must be an ABSOLUTE https URL or LinkedIn/Slack/X silently skip
    it. Only the manual step is left: re-scrape via LinkedIn Post Inspector after a deploy.
19. **Later:** gated auto-apply of adopted weights.
20. **Estimate-revisions sentiment: PARKED** until WRDS/IBES (FMP has no point-in-time revisions at any tier;
    the free `stable/grades` workaround is real but weak and quota-starved). Don't fight the FMP free quota.

## COVERAGE RULE (hard — learned the expensive way 2026-07-30)
**Before reporting or acting on any factor's IC, check its coverage.** Five wired factors were empty
for this project's entire history and nothing surfaced it: an empty column contributes nothing to a
theme mean, raises no error, and the run completes normally. `signal_coverage()` now warns under 5%
and writes `signal_coverage.below_floor` into BACKTEST_RESULTS.json — **read that block first.**
The same class of bug has now bitten four times (`assets` in the loader allowlist, the SF3
positional-arg bug, these five, and `invcap`/`taxexp`/`ebt` missing from `_KEEP`). When adding any
signal, add its source columns to `WRDSProvider._KEEP` and confirm coverage in the next run.

## END OF EVERY SESSION: update `HANDOFF_STATUS.md`
Overwrite `HANDOFF_STATUS.md` in the repo root before you finish — what you did, concrete
numbers (test counts, PBO / Deflated Sharpe / IC / t-stats / alpha, row counts, adopt-or-reject
verdicts), what's blocked and why, and the recommended next step. Plain markdown, no colour
codes, factual. The Cowork agent reads that file directly instead of screenshots.

**Write your full end-of-session report — the complete recap you'd show Don (what shipped,
concrete numbers/verdicts, blockers, the recommended next step) — to your OWN
`HANDOFF_<name>.md`.** The Cowork agent reads that file directly, so Don never has to
screenshot. `HANDOFF_STATUS.md` stays the shared project state; `HANDOFF_<name>.md` is your
session's own full write-up, and parallel agents each own a separate file so they never
clobber each other.

## Working with Don
Concise, direct, honest. He is non-technical but sharp and rightly skeptical — show reasoning and caveats, don't inflate. Unlike the Cowork agent, you (Claude Code) can run commands yourself, so run the backtest/tests directly rather than handing him `.bat` files.

## Tool routing — Claude Code vs Cowork (IMPORTANT: tell Don when to switch)
Don runs TWO agents on this project. They do not talk live; they sync through this shared git repo/folder
(both see the same files). Each agent should explicitly tell Don to switch when a task is in the other's lane.

- **You (Claude Code)** own: running the backtest / `validate_13f.bat` / tests, editing this codebase, git,
  quant research, anything that needs to execute code locally. Do these yourself.
- **Cowork** owns: the Robinhood connector (read-only account data + producing rebalance lists — NEVER
  execute trades), the tracked "Valquo Index vs SPY", scheduled scans/tasks, and phone/mobile sessions.

**Git handoff — CORRECTED 2026-08-07 (claims audit). MERGING IS AUTOMATIC. DO NOT MERGE `main`
BY HAND.** This paragraph used to say: *"Commit directly to `main` in the primary checkout. If your
harness forces a git worktree, you MUST land the work on `main` before ending the session
(`git checkout main && git merge --ff-only <branch>`) … Don deploys from `main` with `git_push.bat`."*
**That instruction is now wrong and acting on it is dangerous** — several agents share the primary
checkout, `main` moves under you mid-session, and a hand-merge there can clobber another lane.
It also contradicted `RUN_RULES.md:76` — the file this brief's own header calls non-negotiable —
which says *"Merging is automatic — the GitHub Action lands any pushed `worktree-*` branch behind
the test gate."* `.github/workflows/land-agent-branch.yml` states the same in its header: *"No local
merge, no Vim, no git_push.bat, no you in the loop."*

**The actual close-out is:** commit in your worktree → `git push -u origin worktree-<name>` →
**verify it landed** (`git fetch origin main -q` then
`git merge-base --is-ancestor HEAD origin/main`). The Action installs deps and runs all 24 suites,
so allow time; if it never lands, the gate failed or the merge conflicted and `main` is
deliberately untouched — do not merge by hand, fix the branch. The original lesson still stands
and is the reason the Action exists: **do not strand work on an unpushed branch** (twice the P5 +
held-out work sat unmerged while `main` stayed on P4). On Windows PowerShell, paste commands on
SEPARATE lines — its old shell rejects `&&`.

When a task needs Cowork, say so plainly, e.g.: **"→ Take this to the Cowork chat — it needs the Robinhood
connector, which I don't have here."** Cowork will likewise send Don back here for heavy backtests/code.
After you commit changes, the Cowork agent sees them in the same folder next time Don opens it.

Current handoff state (July 2026): task #1 is **done** — the 13F signal has been fairly tested and is real
but too weak to trade alone (details in CURRENT STATE). Do not spend more effort tuning or re-testing 13F.

**CORRECTED 2026-08-07 (claims audit): the rest of this paragraph said "The ball is now on task #2,
estimate revisions, which needs an API key from Don (FMP or Intrinio)." Do NOT ask Don to buy that
key.** It contradicts roadmap item **#20** in this same file, which is the researched conclusion:
**FMP has no point-in-time revisions at ANY tier**, so a paid FMP key would not unblock it; the real
source is IBES, i.e. WRDS. `HANDOFF_data_spend.md` reaches the same verdict independently ("no
purchasable retail option exists at any price"). The item is **PARKED**, not waiting on a purchase.
Note also that this paragraph's numbering ("task #2") is its own, and does not match the numbered
roadmap above — estimate revisions is **#20** there.
