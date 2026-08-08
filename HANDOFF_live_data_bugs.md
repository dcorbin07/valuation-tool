# HANDOFF — two live data-correctness bugs (2026-08-04)

Both were in the **deployed** path. Both are fixed, pinned by tests, and measured on real
names. One of the two briefs turned out to be **wrong about the mechanism** — the bug is real
and the fix is real, but the cause is not what the prompt said, and that is written up plainly
below rather than quietly reconciled.

| file | change |
|---|---|
| `valuation/engine/pipeline.py` | `publication_guard()` — refuse to publish a fair value we cannot stand behind |
| `valuation/screener/insider.py` | resolve the RAW Form 4 XML; stop swallowing parse errors |
| `tests/test_engine.py` | +5 tests (33/33) |
| `tests/test_screener.py` | +4 tests (67/67) |

Suites all green: **engine 33/33, screener 67/67, edge 191/191, calibration 23/23, saas 30/30,
intraday 18/18, bulk 14/14, options-greeks 22/22.**

---

## BUG 2 first — it is the clean one, and it is worse than the brief said

### What was actually wrong

`valuation/screener/insider.py`, verified live 2026-08-04:

- `:90` read `recent.get("primaryDocument")`. For a Form 4 that value is EDGAR's
  **XSL-rendered HTML view** — e.g. `xslF345X06/form4.xml`. The `.xml` suffix is a lie; the
  path serves `<!DOCTYPE html ...>`.
- `:100` built the fetch URL from it.
- `:48` `ET.fromstring(...)` raised `ParseError: mismatched tag: line 29, column 16`.
- `:49` `except Exception: return out` swallowed it and returned `[]`.
- `[]` is indistinguishable from "this insider transacted nothing", so `insider_score`
  fell through to its neutral **50.0** — for every name, on every run, always.

Proved on AAPL accession `0001140361-26-025622`:

| URL | served | bytes | `ET.fromstring` |
|---|---|---|---|
| `.../000114036126025622/xslF345X06/form4.xml` (old) | HTML | 18,351 | **ParseError** |
| `.../000114036126025622/form4.xml` (fixed) | XML | 7,692 | OK |

### Measured blast radius — worse than "99.3%"

The brief cited 99.3% of 370,681 Form 4s carrying a rendered `primaryDocument`. On a live
30-name sample of the bundled universe (90-day window, **790 Form 4 filings**):

- **790 of 790 — 100.0% — had the rendered-HTML `primaryDocument`.** Every single filing the
  live code has ever fetched for this signal failed to parse.
- OLD distinct scores across 30 names: **1** (always exactly 50.0).
- NEW: **19 distinct scores; 28 of 30 names now differ from 50**; **0 parse failures / 790 parsed.**
- NEW distribution: min 10.0, p25 10.0, **median 20.0**, p75 37.4, max 70.4. The low centre is
  correct, not a new bug — Form 4 flow is dominated by code-S sales and the weights penalise them.

### The fix

- `form4_xml_url(cik, accession, primary_document)` strips a leading `xslF345X0N/` directory —
  the raw XML sits at the same path without it. Already-raw documents pass through untouched.
- `_parse_form4` now raises `Form4ParseError` (with the first 80 bytes of what it got) instead
  of returning `[]`.
- `insider_detail()` returns `{score, form4_seen, parsed, parse_failures, fetch_failures, error}`.
- **`insider_score` now returns `None`, not 50.0, when filings were found but none could be read.**
  "We could not look" and "we looked and saw nothing" are different claims; collapsing them is
  precisely what hid this for the project's whole history. A name with genuinely no Form 4s in
  the window still scores an honest 50.
- `enrich_insider` attaches `insider_detail` alongside the score and prints a count of
  unreadable names, so a silent-zero run is visible in the output.

### Blast radius on the product — narrower than it sounds

`enrich_insider` is **opt-in** (`scan.py:45`, behind `--insider`) and writes only
`row["extra"]["insider_score"]`. It does **not** feed the composite screener score — the live
`insider` theme column is separately constant, which `tests/test_screener.py:783` already
documents. So this corrupted a **displayed/stored** field, not the ranking.

**The backtest insider theme is unaffected.** That comes from Sharadar SF2, not this scrape.
This is a live-vs-backtest divergence (audit item B7's class), **not** a change to any
backtested result. Nothing in `valuation/edge/` was touched.

### Two things found on the way, noted not fixed (out of lane)

- **`resolve_cik("XOM")` returns CIK 2115436**, an entity whose EDGAR history begins
  **2026-07-01** with 28 filings (23 `S-8 POS`, an `8-K12B`) and **no Form 4s at all** — a
  holdco reorganisation. XOM therefore scores an honest-but-misleading 50 (`form4_seen=0`).
  `valuation/data/edgar.py` is not in this lane. A consumer can already tell the difference
  from `form4_seen`, which is why it is exposed.
- **`_role_multiplier` matches the literal word "officer"**, so an `isOfficer=true` filer titled
  "SVP, GC and Secretary" gets the **director** weight 1.0. Pinned as observed behaviour in
  `test_form4_parser_reads_a_known_good_filing`, deliberately not retuned — changing role
  weights moves every live score and that is a separate, measurable decision.

---

## BUG 1 — the brief's diagnosis does not hold; the bug does

### Reproduced first, as instructed

`KSPI` on the live path, 2026-08-04: price **$92.00**, base fair value **$1,249.16**, upside
**+1,258%**. That reproduces the report (+1253%).

### But it is NOT currency-corrupted, and here is the evidence

The brief says "the DCF is projecting local-currency cash flows and comparing them to a USD
share price". Measured, that is not what happens:

- Yahoo reports `currency=USD`, `financialCurrency=KZT` for KSPI. ✓ (the setup is as described)
- `_fx_rate("KZT","USD")` **resolves fine**: 0.0021165 (≈472 KZT/USD).
- `yahoo.fetch` **does** convert — `valuation/data/yahoo.py:332-352` calls `cd.apply_fx(rate)`
  and rebases the share count to the ADR.
- The resulting CompanyData is internally consistent **and in USD**: market cap $17,482.5M =
  190.03M shares × $92.00 ✓, net income **$2,271M**, which back-converts to ≈1,073bn KZT
  against Kaspi's reported ~1,004bn KZT FY24. Revenue and equity check out the same way.

So the statements are correctly in USD before the DCF ever runs. **The currency machinery works
on this name.** What actually produces $1,249 is the DCF's own assumptions: a 10-year forecast
starting at **34.3% revenue growth** with margins ramping 33%→40%, discounted at a **WACC of
5.10%** against a **3.0% terminal growth** — a 2.1pp spread, i.e. a ~47x terminal multiple. The
WACC is that low because Yahoo hands us **beta = 0.08**.

Beta is a contributor, not the whole story — I checked rather than assumed:

| beta | WACC | fair value | upside |
|---|---|---|---|
| 0.08 (live) | 5.10% | $1,246.43 | +1,255% |
| 0.50 | 7.08% | $730.93 | +694% |
| 1.00 | 9.45% | $521.25 | +467% |
| 1.30 | 10.87% | $462.87 | +403% |

Even at a sane beta the name still prints +403%. **The valuation is self-consistent and the
inputs are aggressive — it is not a units error.** Anyone who "fixes the currency" here will
change nothing.

### What IS broken, and it is the half the brief said matters more

**The engine already knew the number was wrong and published it anyway.** `pipeline.py:236`
detected the >5x ratio and inserted a warning reading *"almost certainly a data problem
(currency or share count), not a real opportunity"* — then returned `base_fair_value = 1249.16`
and `upside = +12.58` for the UI to render as a headline. A reader sees $1,249, not the caveat.

And the FX guard genuinely was dead: **`cd.fx_unresolved` was set by `yahoo.fetch:349` and read
by nothing except `screener/providers.py:314`.** Forcing `fx_unresolved=True` on KSPI still
produced a published `base_fair_value` of $1,246.61. The engine/DCF path never benefited from
the FX machinery **at the guard level** — that is the real answer to the brief's question.

### The fix — `publication_guard()` in `valuation/engine/pipeline.py`

Refuses on two independent conditions, and marks the blend not-valuable rather than inventing a
new contract. `base_fair_value` and `upside` then return `None` through the existing property,
and the UI's existing `notValuable` state (`app.js:205`, keyed on
`base_fair_value == null && fair_value_blend.valuable === false`) renders "Not DCF-valuable"
with upside "n/a". **No web template or route was touched.** The guard runs *before*
`compute_score`, so the score cannot be computed against a number the reader never sees.

1. **Unresolved / unapplied currency** — `fx_unresolved` set, or the currencies differ and no
   `fx_rate` was applied. Every monetary input is then wrong by an unknown factor.
2. **Sanity band** — the published value exceeds **5x** the market price (`FV_BAND_HIGH`), the
   pre-existing warning threshold, now binding.

KSPI after the fix: `base_fair_value = None`, `upside = None`, and the reader gets
*"Cannot value this name: the model's $1,248.48 is 13.6x the $92.00 price. That gap is a data
problem (currency or share count), not an opportunity, so no fair value is published."*

### One deliberate narrowing, because a test caught me

I first made the guard symmetric (also refusing below 1/5 of price). That broke
`test_dcf_still_floors_at_net_cash_when_revenue_is_gone`, and **the test was right**: a
revenue-less shell worth its net cash of $0.22 against a $8.00 price is a genuine verdict, not
corruption. More generally a fair value *below* price is never the failure this targets — the
product is not telling anyone to buy, and suppressing it would hide legitimate "this is
expensive" calls. **Only the high side refuses; the low side keeps its warning unchanged.**

### Currency sweep across the live universe

241 names — the 191-name bundled scan universe plus 50 known foreign filers, since the bundled
list is almost entirely US large caps and would have made the answer trivially "none". All 241
fetched OK. Each was valued twice: once with the guard disabled (BEFORE) and once with it live.

- **35 names report in a non-USD currency**, across 11 currencies: BRL, CAD, CNY, DKK, EUR, GBP,
  INR, JPY, KZT, MXN, TWD.
- **FX unresolved on 0 of 35. A rate was applied on all 35.** The conversion path is healthy —
  which is the measurement behind the claim above that KSPI is not a currency failure.
- **32 of the 35 foreign names publish exactly as before.** The guard is not blanket-blanking
  ADRs: TSM, ASML, SAP, NVO, TM, SONY, MUFG, BABA, PDD, HDB, RY, TD, GSK, UL, VALE, PBR and the
  rest are untouched.
- **7 names newly withheld**, by |upside|:

| name | reports in | was | price | upside | now |
|---|---|---|---|---|---|
| STLA | EUR | $124.21 | $5.65 | **+2,098%** | withheld |
| KSPI | KZT | $1,245.72 | $92.00 | **+1,254%** | withheld |
| CHTR | **USD** | $1,737.16 | $144.10 | **+1,106%** | withheld |
| MRK | **USD** | $1,176.78 | $127.77 | **+821%** | withheld |
| GILD | **USD** | $941.93 | $131.15 | **+618%** | withheld |
| CI | **USD** | $1,966.23 | $282.06 | **+597%** | withheld |
| JD | CNY | $223.59 | $33.02 | **+577%** | withheld |

### This is the finding that settles the diagnosis

**Four of the seven — CHTR, MRK, GILD, CI — report in USD.** There is no currency anywhere near
them. They are US mega-caps that the live product was showing at +597% to +1,106% upside.

Checked directly, they are the KSPI mechanism exactly:

| name | beta | WACC | terminal g | spread | raw DCF |
|---|---|---|---|---|---|
| CHTR | 0.678 | 4.76% | 3.0% | **1.76pp** | $2,113 |
| MRK | 0.211 | 5.53% | 3.0% | **2.53pp** | $2,471 |
| CI | 0.321 | 5.78% | 3.0% | **2.78pp** | $1,740 |
| GILD | 0.336 | 6.09% | 3.0% | **3.09pp** | $1,955 |
| KSPI | 0.080 | 5.10% | 3.0% | **2.10pp** | $2,210 |

**The bug is that the DCF's terminal value degenerates whenever WACC approaches terminal
growth**, and Yahoo's low betas on defensive large caps make that common — not rare, not
foreign, and not a units error. `TV = FCF/(WACC − g)` with a 1.76pp denominator is a division by
near-zero. The currency brief would have fixed none of these.

---

## Caveats — do not drop these

- **THE GUARD SUPPRESSES THE SYMPTOM, IT DOES NOT FIX THE CAUSE.** Seven names are now withheld;
  the underlying DCF still computes $2,471 for MRK. The root cause — `TV = FCF/(WACC − g)` with
  a 1.76–3.09pp denominator — is untouched, and on the sampled universe it affects **7 of 241
  names (2.9%), four of them USD-reporting US mega-caps**. This is deliberately not fixed here:
  putting a floor under `WACC − g` changes *every* valuation the product has ever produced, and
  that is a modelling decision with its own before/after, not a bug fix to slip into a data-bug
  lane. It is the single most valuable follow-up in this file.
- **The withheld names are not necessarily bad companies** — the product now says nothing about
  MRK, GILD, CI, CHTR, STLA, JD and KSPI rather than something wrong. That is the intended trade,
  but it is a visible product change on well-known tickers and Don should know before deploy.
- **The 5x threshold is inherited, not derived.** It is the number the existing warning already
  used. It is a blunt instrument: a genuine 6x-upside name would now be withheld. That trade is
  deliberate — a confident wrong number costs more than a missed one — but it is a product
  decision Don may want to revisit, and it is one constant in one file.
- **The bear/base/bull rangebar is not suppressed.** When the guard fires, `fair_value_scenarios`
  still holds numbers and `app.js:224` will draw the cone. The headline and upside — the actual
  "confident wrong number" — are withheld. Making the cards agree needs an app-lane change and is
  pre-existing behaviour for every not-valuable name, not something introduced here.
  → **For the app lane:** the cards should follow the headline.
- **The insider sample is 30 names, not the whole universe.** Each name costs 8–104 EDGAR
  fetches; 30 names was 790. The 100.0%-rendered figure is unlikely to move (it is a property of
  how EDGAR populates `primaryDocument`), but the score *distribution* is a sample.

## A repo-wide gotcha found while doing this — worth knowing

**`.gitignore:26` is `data/`, unanchored, so ripgrep skips `valuation/data/` too.** Every
scoped content search in this repo silently returns nothing for the entire data layer —
`yahoo.py`, `fetcher.py`, `models.py`, `edgar.py`, `macro.py`. It cost me a wrong conclusion:
a clean grep for `apply_fx` returned only a test and one caller, which reads exactly like dead
code, when in fact `yahoo.py:343` calls it in production. Anyone searching this repo should use
`rg --no-ignore` or they will draw false conclusions about the data layer. Changing the pattern
to `/data/` would fix it (it still ignores the licensed exports at the repo root) — not done
here because `.gitignore` is nobody's declared lane and four agents are running.

## Next

- **Fix the WACC-vs-terminal-growth degeneracy — this is the real bug and it is still live.**
  The evidence is in the table above: five names with spreads of 1.76–3.09pp producing DCFs of
  $1,700–$2,500 against $128–$282 prices. Likely shapes: floor the spread (e.g. `WACC − g >=
  3-4pp`), floor beta (Yahoo hands us 0.08 for KSPI and 0.21 for MRK), or cap the terminal
  multiple directly. Whichever is chosen needs a before/after across the universe, because it
  moves every valuation. **Do not treat the guard as having fixed this.**
- If Don wants the withheld names visible, `FV_BAND_HIGH` in `valuation/engine/pipeline.py` is
  the single knob.
- `insider_score` returning `None` is a contract change. Only `enrich_insider` consumes it today
  and it stores the `None` deliberately; anything new must not coerce it back to 50.

---

# PART 2 — the terminal-value degeneracy (2026-08-05)

## PRE-COMMITMENT — written and committed BEFORE any number was measured

Git history is the evidence: this section is committed on its own, ahead of any code change or
measurement, precisely because this change moves every valuation the product has ever produced
and I am choosing among knobs with a visible target. Everything below is fixed in advance.

### 1. What "fixed" means for the seven currently-withheld names

STLA, KSPI, CHTR, MRK, GILD, CI, JD. Each is a PASS on exactly one of:

- **(a) Published and defensible** — it publishes a fair value inside the existing 5x guard band
  AND its terminal value is non-degenerate at the fix's own definition (spread at or above the
  floor / multiple at or below the cap). The number must be publishable *because the degeneracy
  is gone*, not because it happened to shrink.
- **(b) Withheld for a stated NON-degenerate reason** — e.g. genuinely unresolved FX, or a >5x
  value that survives with a healthy spread. I must name the reason per name.

Explicit FAIL conditions: still withheld with the same degenerate spread; or published while the
spread remains below the floor. **"It got smaller" is not a pass.**

### 2. Do-no-harm bound on the names that value fine today

The bound is enforced on the **non-degenerate population**, defined in advance as names whose
PRE-fix `WACC − g` spread is **≥ 5.0pp** — comfortably clear of every candidate floor below, so
these names have no mechanical reason to move. A spread floor should leave them literally
untouched; a beta floor will not, which is the discriminating power I want from this bound.

A candidate is **REJECTED outright**, whatever it does for the seven, if on that population:

- median |Δ fair value| **> 2%**, or
- more than **2%** of them move **> 25%**, or
- **any** name that published before is withheld after (nobody gets pushed out of the band).

Names with a pre-fix spread < 5.0pp are expected to move — that is the intervention — and are
reported, not bounded.

### 3. The knob, the parameter values, and the anti-tuning rule

Candidate parameters are chosen NOW from stated first-principles or external references, never
from how the seven names turn out:

- **A — floor on `WACC − g` at 3.0pp**, applied by lowering `g` (not by raising WACC): a Gordon
  perpetuity with spread `s` implies a terminal multiple of `1/s`, so 3.0pp is already 33.3x
  terminal FCF, the generous end of what a mature business supports; below it `d(TV)/ds`
  explodes. `g` is the assumption we control, and a terminal growth within 3pp of the discount
  rate is economically incoherent regardless of this bug.
- **B — Blume/Bloomberg adjusted beta**, `β_adj = 0.67·β_raw + 0.33·1.0`. External, published
  (Blume 1971; the standard Bloomberg "adjusted beta"), chosen for being not-ours. Maps
  0.08 → 0.387 and 0.211 → 0.474.
- **C — cap the implied terminal multiple at 25x** terminal FCF (≈ a 4% perpetual FCF yield,
  equivalent to a 4pp spread). The most interpretable of the three.
- **A+B combined**, because a spread floor and a beta floor are NOT independent: B raises WACC,
  which widens the spread on its own and may leave A with nothing to bind on. I will report how
  much of A's effect survives once B is applied rather than testing either in a vacuum.

**Anti-tuning rule.** Each parameter is used at the value stated above. If a candidate fails at
its pre-chosen value, it is REJECTED — not retuned. Should I retune anything, the result is
relabelled exploratory and reported as **NULL**, not adopted.

**KSPI is excluded from the primary decision metric.** It motivated the search and carries the
most extreme beta (0.08), so judging on it is how a tuned result gets born. The verdict rests on
the other six (CHTR, MRK, GILD, CI, STLA, JD); KSPI is reported but not decisive.

### 4. Decision rule, in order

1. Any candidate breaching §2 is REJECTED, however well it fixes the seven.
2. Among survivors, the one resolving the most of the six decisive names under §1.
3. Tie-break on interpretability (favouring C), since the prompt is right that interpretability
   is a tiebreaker and not evidence.
4. If no candidate satisfies §2 while resolving a majority of the six at its pre-chosen
   parameter, the outcome is **NULL** and nothing ships.

### 5. Untouched by commitment

`publication_guard()` stays; `FV_BAND_HIGH` stays at 5.0; no warning is silenced. If the guard
fires exactly as often afterwards, that is a null result and will be reported as one.

---

## RESULTS — measured after the pre-commitment above was committed (e36d755)

### Verdict in one line

**A / B / C on the terminal value: NULL — nothing shipped.** The pre-registered candidates
either failed the do-no-harm bound or resolved none of the decisive names. But the
investigation found the **actual root cause one level up, and that IS fixed**: an
"analyst revenue growth" input carrying EARNINGS growth, which classified Merck and Gilead
as **hypergrowth** and modelled them at 60% revenue growth for a decade.

**Part 1 of this handoff — and this prompt, which inherited its framing — were wrong that
`TV = FCF/(WACC - g)` is the root cause.** It is the mechanism for three names and a
downstream symptom for two. Corrected in detail below.

### 1. Every terminal-value path in the tree

| path | formula | protection | degenerates? |
|---|---|---|---|
| `dcf.py:99-110` FCFF Gordon | `FCFF/(WACC - g)` | floor `max(WACC - g, 0.005)` | **YES** — a 0.5pp floor is a **200x** terminal multiple, i.e. nominally a guard and effectively none. It has never bound on a real name. |
| `growth.py:256` `fundamental_sales_multiple` | `margin(1-t)(1-g/ROIC)/(r - g)` | discounts at `mature_discount_rate` (rf+ERP, **not** the company's WACC), floors the spread at 1pp, **and caps the result at `MULTIPLE_CAP = 20.0`** | no |
| `financials.py:21` `justified_pb` | `(ROE - g)/(Ke - g)` | returns **None** if `Ke - g <= 0.005`, and bounds P/B to `[0.2, 6.0]` | no |

So two of the three terminal paths already have *effective* caps; the FCFF DCF has a nominal
one. That asymmetry is what this task was really about.

Two further clamps permit the problem *by construction*, neither aware of the other:
`wacc.py:98` clamps WACC to `[0.04, 0.25]`, and `assumptions.py:151` sets terminal growth to
`max(0.015, min(cap, rf))` = 3.0%. A **1pp spread is therefore reachable by design**.

### 2. Beta diagnosis — the low betas are REAL, which kills the beta fix on its merits

Re-estimated independently against SPY. The estimator agrees with Yahoo on controls (AAPL
1.086 vs 1.071, JPM 0.977 vs 1.015, NVDA 2.215 vs 2.214), so disagreements are informative:

| name | Yahoo | my 5y-monthly | 2y-weekly | 1y-daily | read |
|---|---|---|---|---|---|
| GILD | 0.336 | 0.304 | 0.349 | 0.342 | **real** |
| CI | 0.321 | 0.282 | 0.229 | 0.204 | **real** |
| CHTR | 0.678 | 0.668 | 0.767 | 0.278 | **real** |
| MRK | (absent today) | 0.181 | 0.247 | 0.122 | **real** |
| KSPI | 0.080 | 0.897 | 1.134 | 1.028 | **ARTIFACT** (n=30 monthly; ADR listed 2024) |

A genuinely low-beta defensive stock legitimately has a low WACC. Flooring beta would assert
something false about four of the five. Only KSPI's beta is wrong — and `wacc.py:67` rejects
beta `<= 0` or `> 3.0` but has **no low-side floor and no minimum-history check**, so 0.08
sails through.

### 3. Candidate results on the 241-name universe

Non-degenerate population (pre-fix spread >= 5.0pp and publishing today): **128 names**.
109 names have a pre-fix spread below 5.0pp.

| candidate | median abs delta | moved >25% | pushed out of band | do-no-harm | decisive names resolved (of 6) |
|---|---|---|---|---|---|
| A — spread floor 3.0pp | 0.000% | 0/128 | 0 | **PASS** | **0** |
| C — terminal multiple cap 25x | 0.000% | 0/128 | 0 | **PASS** | **0** |
| B — Blume adjusted beta | **2.491%** | 3/128 (2.3%) | 0 | **BREACH** | 0 |
| A+B | **2.491%** | 3/128 (2.3%) | 0 | **BREACH** | 0 |

B and A+B breach the pre-committed 2% median bound — narrowly, at 2.491%. Per the anti-tuning
rule they are **REJECTED, not retuned**.

A and C are clean but move no name inside the guard band. Best case is C on CHTR: 11.2x price
down to 5.3x — still outside. GILD 6.0x, CI 6.4x, JD 6.2x, KSPI 9.8x.

**Why capping the terminal value cannot rescue these names:** terminal value is **76-102% of
EV** even after the caps (JD 102.4%, CI 86.9%, CHTR 76.4%). When the explicit forecast
contributes almost nothing, no terminal assumption short of destroying the model brings the
total inside 5x. That is the honest reason A and C fail — and it is what pointed at the
forecast itself.

Per decision rule 4: **NULL. `MIN_TERMINAL_SPREAD` stays 0.005 and `MAX_TERMINAL_MULTIPLE`
stays `None`** — they are now named, documented constants instead of a magic number, but the
shipped behaviour is unchanged.

### 4. THE ACTUAL ROOT CAUSE — found by asking why the forecast was so large

Merck was projected from $65.0bn revenue to **$1,118bn**, and Gilead from $29.4bn to
**$506bn** — **17.2x in ten years**, a 33% CAGR, for mature pharma. Year-10 FCF per share came
out at $117 (MRK) and $114 (GILD), roughly equal to their share prices. The chain:

1. `yahoo.py:293` sets `analyst_rev_growth_next` from `growth_estimates.loc["+1y"].iloc[0]`.
   That DataFrame is indexed by period with columns `stockTrend` / `indexTrend`, so `.iloc[0]`
   is **`stockTrend` — EARNINGS growth, not revenue** — and it explodes off a negative base
   (GILD's `0y` is -1.0838, so `+1y` reads **15.0829**; MRK's `0y` is -0.6926, `+1y` =
   **2.4942**). Yahoo's own `revenueGrowth` field is sane for both: GILD 4.4%, MRK 5.1%.
2. `classify._blended_growth` gives that input the **highest weight (0.5)** and then
   **clamped** the blend to `[-0.30, 1.00]`. Both names landed on exactly **1.00** — a tidy
   number that reads as a legitimate 100% growth forecast.
3. `gg >= 0.25` -> regime **hypergrowth**.
4. `assumptions` -> `start_growth = 0.60`, `n_years = 10` -> revenue x17.2.
5. -> DCF $2,000 (GILD) / $889 (MRK) -> withheld by the guard.

**The clamp was the concealment.** Squashing garbage onto the edge of the valid range
disguises it as data. 6 of 241 names carried an analyst "revenue growth" above 100% — GILD
15.08, BA 4.72, MRK 2.49, CPNG 1.81, MU 1.12, WBD 1.02 — every one silently clamped to 1.00.
**27 of 241 names classified as hypergrowth, including Merck, Gilead, Boeing, Intel and
Welltower.**

### 5. THE FIX (D) — reject implausible analyst growth instead of clamping it

`classify._blended_growth` now DISCARDS an analyst estimate outside `[-0.30, 1.00]` rather
than squashing it onto the boundary; the 3y CAGR and TTM then carry the estimate. **No new
tuned constant** — the band is the function's own pre-existing clamp, reinterpreted as reject.

This was NOT one of the pre-registered candidates: it was found during the work. It carries no
free parameter fitted to an outcome, which is why it is reported as a bug fix rather than a
tuned choice — but it did not go through the pre-commitment, and that is stated plainly here
rather than dressed up as a passing candidate.

Measured before/after on the same 241 names:

- **Do-no-harm: perfect.** On the 226 names whose analyst input was already inside the band,
  **median |delta| = 0.0000%, 0 moved >25%, 0 pushed out of the band.** The fix cannot touch
  them by construction.
- Regimes: hypergrowth **27 -> 22**, mature 88 -> 91, growth 52 -> 54.
- **The guard fires less: 9 names withheld -> 7.**

| name | regime before -> after | start growth | DCF before -> after | headline before -> after | price |
|---|---|---|---|---|---|
| GILD | hypergrowth -> **mature** | 0.600 -> 0.025 | $2,000 -> **$169** | withheld -> **$155** | $131.76 |
| MRK | hypergrowth -> **mature** | 0.600 -> 0.024 | $889 -> **$83** | $474 -> **$94** | $128.33 |
| MU | hypergrowth -> growth | 0.600 -> 0.236 | $323 -> $75 | $318 -> $125 | $893.19 |
| WBD | hypergrowth -> **mature** | 0.508 -> -0.001 | $40 -> $1 | $42 -> $11 | $25.97 |
| CPNG | hypergrowth -> growth | 0.600 -> 0.169 | $86 -> $10 | withheld -> $13 | $16.00 |
| BA | hypergrowth (unchanged) | 0.600 -> 0.200 | -$267 -> -$25 | $194 -> $94 | $240.19 |
| CF / VLO | cyclical (unchanged) | -0.150 -> -0.007 / -0.091 | minor | $168->$196 / $233->$229 | — |

GILD now values at **1.18x its price** and MRK at **0.73x**, from a model that previously
thought they were worth 15x and 7x. Pinned by
`test_implausible_analyst_growth_is_rejected_not_clamped` and
`test_mature_pharma_is_not_classified_hypergrowth`.

CHTR, CI and JD are **unchanged and still withheld** — their analyst inputs were clean, and for
those three the terminal-spread mechanism from Part 1 really is the story. They remain open.

### 6. Corrections to Part 1 of this handoff

- **"The root cause is `TV = FCF/(WACC - g)`" was wrong.** It is the mechanism for CHTR, CI and
  JD; for MRK and GILD it was a symptom of the contaminated growth input; for STLA it was never
  involved at all.
- **STLA was misattributed.** Its spread is a healthy **10.80%** and its terminal multiple
  9.3x. Its DCF is **negative** (-$38; TV is -196% of EV); the $125.9 headline came from the
  multiples/growth lenses, not the DCF. It does not belong in the degenerate group.
- **MRK left the withheld set by data drift, not by any fix.** Yahoo stopped returning a beta
  for MRK between 2026-08-04 and 2026-08-05, so it fell back to 1.10, WACC went 5.53% ->
  9.31%, and it published at $474. The Part 1 table's MRK row is not reproducible today.
- Part 1's KSPI beta (0.08) stands, but that beta is now shown to be an artifact.

### 7. Can the calibration harness score this?

**It can run it, but it is the wrong instrument for this decision — and the right one for a
different question.** It rebuilds fair value point-in-time on the Sharadar panel through the
live engine (so `dcf._project` and `compute_wacc` are exercised) and computes its own
point-in-time beta (`calibration.py:443`, `_beta_at`, a 120-day regression), so the degeneracy
is reachable there. But its baseline verdict on the fair-value gap is already **NULL** (median
IC +0.0092, t +0.99): measuring "did IC improve" against a non-signal cannot separate a better
model from noise, and this change touches a handful of names. **Deliberately not run for the
adopt/reject decision.** Where it would earn its keep is a mechanical question it can answer
exactly — how many point-in-time observations across 18 years carried a contaminated growth
input or a sub-3pp spread. That quantifies historical exposure, and is the recommended next use.

### 8. What I did NOT do, and why

- **Did not fix `yahoo.py:293`, which is the true upstream defect.** It is in
  `valuation/data/`, outside this task's declared lane (`valuation/engine/**` + the calibration
  harness), and Part 1 deferred the same directory. The exact patch is in BUGS FOUND below. The
  engine-side rejection is defence-in-depth and correct independently, but **the field is still
  wrong for every name** — whenever `stockTrend` happens to land inside `[-0.30, 1.00]`, an
  earnings growth rate is still silently used as a revenue growth rate. **This is the single
  most important open item in this file.**
- **Did not adopt A or C despite both passing do-no-harm cleanly.** My own criteria said
  resolve-the-names; they resolved none. Adopting them anyway because they "look safe" is
  exactly the post-hoc rationalisation the pre-commitment exists to prevent. So a **56x
  terminal multiple on CHTR is still live.** A is a one-line, zero-measured-harm hardening if
  Don wants it: `MIN_TERMINAL_SPREAD = 0.030` in `valuation/engine/dcf.py`, evidence in §3.
- **Did not retune B** after it missed the bound at 2.491% vs 2%.
- **Did not ship the pinning test the prompt asked for.** It was written and confirmed to fail
  against current code — `terminal spread 2.19% - a perpetuity discounted only 2.19% above its
  own growth rate is a division by near-zero, not a valuation` — but the fix it pins was
  rejected by the pre-committed criteria, so shipping it would mean shipping a red suite. It is
  recorded here, ready to restore alongside A.
- **Did not touch `publication_guard` or `FV_BAND_HIGH`**, as instructed.

## BUGS FOUND

1. **`yahoo.py:293` reads earnings growth into a revenue-growth field** (detail in §4). Fix:
   prefer `info["revenueGrowth"]`, or take the `growth_estimates` value only after confirming
   the frame is a revenue estimate — and reject out-of-band values at the source.
   **Not fixed here (lane).**
2. **`wacc.py:67` has no low-side beta floor and no minimum-history check.** It rejects
   beta > 3.0 but accepts 0.08 derived from 30 monthly observations on a 2024 ADR listing.
3. **`dcf.py`'s 0.005 spread floor is a 200x terminal multiple** — a guard that has never
   bound. Now a named constant; behaviour unchanged pending a decision on A.
4. **`wacc.py:98` (WACC >= 4%) and `assumptions.py:151` (g = 3%) permit a 1pp spread by
   construction.** Neither clamp knows about the other; a single invariant `WACC - g >= x`
   would be the coherent place to enforce it.
5. **CHTR's forecast more than doubles free cash flow while revenue grows 16%** — year-5 FCFF
   $85.42/share against $37.04 today, on 1.16x revenue and a flat 22.8% margin. That points at
   the `sales_to_capital` reinvestment assumption under-charging a capex-heavy cable operator.
   A lead, not a finding — not investigated further.
6. **`DCFResult.terminal_growth` reported the ASSUMED growth, not the effective one.** Now
   reports the effective rate, with `assumed_terminal_growth` and `terminal_multiple` alongside
   — without which "the clamp bound" is invisible to every caller.

---

# PART 3 — the upstream growth defect, the contaminated score, and adopting A (2026-08-05)

## PRE-COMMITMENT — written and committed before any of Part 3's numbers were measured

Committed on its own, ahead of the work, for the same reason as Part 2: two of these items
have a visible target and I am the person who found them, which is exactly the setup that
produces a flattering result.

### Item 1 — blast radius of the wrong growth field

The question is how often the positional read (`stockTrend`, earnings growth) differed from the
correct revenue field *quietly* — i.e. landed inside `[-0.30, 1.00]` and so survived the engine
rejection shipped in Part 2. Fixed in advance:

- **The measurement is descriptive, not a pass/fail.** I am not predicting a number and I will
  report whatever it is, including "the quiet failures are rare", which would make my Part 2
  claim that "there is no reason to think they are rare" wrong. That is a real possible outcome
  and it will be stated in those words if it happens.
- **"Differs" means** `abs(old - new) > 0.01` (1pp of growth) where both exist. Names where the
  positional read is absent and the code already fell back to `revenueGrowth` are NOT
  contaminated and are excluded from the numerator, but reported.
- **Do-no-harm bound, same as Part 2:** on names whose growth input does NOT change, median
  |Δ fair value| must be **0.000%** — this fix is a pure input swap and cannot move them. Any
  movement there is a bug in my change, not a finding. On names whose input DOES change,
  movement is the point and is reported unbounded.
- I will **not** treat "more names moved" as success. The correct field is correct regardless of
  how many names it moves; the fix ships on correctness.

### Item 2 — what a withheld name's score should be

Committed BEFORE seeing the new distribution, because "which option looks better in the table"
is not a valid way to choose this:

- **Decision rule: a score is a claim about the name, and every claim must rest on inputs we
  publish.** Any sub-score derived from a valuation the guard withheld is dropped. The remaining
  question — partial score vs no score — is decided on whether the surviving sub-scores mean
  what the score label says, NOT on the resulting numbers.
- **My prior, stated now: a PARTIAL score from the uncontaminated sub-scores, explicitly marked
  as such.** Reason: quality, growth, health and momentum are computed from reported financials
  and price history and are unaffected by the DCF being unpublishable; suppressing them entirely
  throws away four working measurements because a fifth failed. The precedent is already in this
  codebase — `compute_score` "already tolerates None (it renormalizes)".
- **I will abandon that prior if the measurement shows** the renormalised score is not
  interpretable on the same 1-100 scale as a full score — concretely, if withheld names
  systematically land in a different part of the distribution than publishable names with
  similar fundamentals, such that the same number means two different things. That is the
  falsifier, and it is named before the run.
- **Do-no-harm: publishable names must be EXACTLY unmoved** (max |Δ score| = 0 across all names
  the guard does not withhold). This change may only affect withheld names.

### Item 3 — candidate A

Ships as instructed, and will be recorded as **ADOPTED ON COHERENCE, NULL ON PERFORMANCE**. I
will not restate it as having passed the Part 2 pre-registered test, because it did not. The
before/after numbers already measured in Part 2 §3 stand and will not be re-derived to look
better.

## PART 3 RESULTS — measured after the pre-commitment above (b671f0f)

All three items shipped. Suites: **20 suites, 692 tests, all green.**

### ITEM 1 — the wrong field. Blast radius: 194 silently-wrong names.

**Measured across the 241-name sweep** (positional read vs a real revenue figure):

| | count |
|---|---|
| names swept | 241 |
| positional read absent (already fell back) | 1 |
| both values present | 239 |
| **DIFFER by >1pp** | **202 (84.5%)** |
| — LOUD (outside `[-0.30, 1.00]`, caught by the Part 2 engine fix) | **8** |
| — **QUIET (inside the band, still silently wrong)** | **194** |

|difference| median **0.085** (8.5pp of growth), p90 **0.473**, max **15.04**.

**The Part 2 engine rejection caught 8 of 202.** My Part 2 wording — "there is no reason to
think they are rare" — was right, and it understated it: **80.5% of the universe was using an
earnings growth rate as a revenue growth rate.** Worst quiet cases: COF (+0.185 vs +11.11),
ENB (+0.109 vs +0.971), MPC (−0.290 vs +0.545), CVX (−0.183 vs +0.526), DELL, SHEL, PLTR, XOM,
GOOGL, NVDA (+0.433 vs +0.852).

**Two things the positional read did that are worse than "wrong column":**

- **BRK.B's `growth_estimates` frame has only an `indexTrend` column.** `.iloc[0]` there was
  taking **the S&P 500's growth estimate** as Berkshire's revenue growth. 239 of 241 frames had
  `[stockTrend, indexTrend]`; one had `[indexTrend]`. Positional access cannot notice this.
- **A NaN became a 100% growth forecast.** `min(1.00, nan)` returns **1.0** in Python, so the
  old blend's clamp turned a missing value into an explicit "100% revenue growth" — which is
  why **WELL (Welltower, a healthcare REIT) was classified hypergrowth**. Three names came
  through as NaN (WELL, TM, SONY). The Part 2 band check already rejects NaN; confirmed.
  This is the **third** instance of the same pattern: a clamp converting garbage into a
  plausible-looking extreme.

**The fix** (`valuation/data/yahoo.py`): `_analyst_revenue_growth()` reads
`revenue_estimate.loc["+1y", "growth"]` — a genuinely next-year *revenue* series, **selected by
name on both axes** — then falls back to `info["revenueGrowth"]`, and **rejects anything outside
`[-0.30, 1.00]` at the source**, because `revenueGrowth` is not clean either (COF: **11.11**).
239 of 241 names now resolve a plausible value.

**Effect (isolated: growth input only, everything else held):**

| | before | after |
|---|---|---|
| mature | 91 | **113** |
| growth | 54 | 31 |
| cyclical | 43 | 52 |
| **hypergrowth** | **22** | **14** |
| withheld by the guard | 7 | **5** |

Names whose input changed (n=213): median |Δ fair value| **2.323%**, 10 moved >25%.

**My pre-committed do-no-harm bound for this item could not be evaluated, and I am not going to
pretend otherwise.** I committed to "on names whose growth input does NOT change, median
|Δ fair value| must be 0.000%". After the run there were **zero names with a bit-identical
input** — the correct field differs from the wrong one essentially everywhere, so no control
group exists. My first attempt to report this bucket was also wrong twice over: it bundled
items 1–3 into one before/after, and its "unchanged" test (`abs(old-new) > 0.01`) silently
swallowed the three NaN names, because `nan > 0.01` is False — which is how WELL, a 59% mover,
landed in the "unchanged" column. Both errors are mine, both are corrected above by re-running
each item in isolation. **The bound was unmeasurable as written; item 1 ships on correctness —
the right field, selected by name — not on a do-no-harm result.**

**Pattern sweep (`.iloc` against named-column frames).** `valuation/data/**` and
`valuation/engine/**`: **exactly one instance, the one fixed here.** Every remaining `.iloc` is
1-D positional *by intent* — `closes.iloc[-126]` ("126 bars ago"), `benchf.iloc[i]`,
`share.iloc[0]` read alongside its own `share.index[0]`. No `.columns[N]`, `.iloc[:, N]`,
`.values[0]` or `.iat[]` anywhere in either tree. Statement rows are picked by label
(`_pick_row`), correctly.

### ITEM 2 — the score no longer eats the withheld valuation

**Isolated (scoring only; growth input and terminal floor held at their old values):**

- **Fair values identical: max |Δ| `0.00000000%`** — this change touches scores only.
- **Publishable names (n=234): max |Δ score| = 0.** The pre-committed bound was "EXACTLY
  unmoved", and it is met exactly.

| name | score | valuation sub-score | confidence |
|---|---|---|---|
| KSPI | **93 → 50** | **100.0 → None** | medium → low |
| JD | **79 → 50** | 99.4 → None | high → low |
| CI | **71 → 50** | 100.0 → None | high → low |
| CHTR | **69 → 48** | 100.0 → None | high → low |
| STLA | 45 → 44 | 49.4 → None | low → low |
| BRK.B | 58 → 58 | None → None | low → low |
| HES | 40 → 40 | None → None | low → low |

Both defects are fixed: `compute_score` drops the **entire** valuation sub-score when the blend
is not valuable (so `mc.prob_undervalued` at 0.30 and `comps_fair_value` at 0.15 cannot rebuild
it), and the ">5x is a data problem" cap now evaluates against `blend.withheld_value` — a new
field holding the value the guard suppressed, **for guards only, never published**. KSPI moving
93 → 50 is that cap firing for the first time on a withheld name.

**The decision, argued as pre-committed: a PARTIAL score from the four uncontaminated
sub-scores, explicitly labelled.** Quality, growth, financial health and momentum are computed
from reported financials and price history; none of them depends on the DCF being publishable.
Suppressing them entirely would discard four working measurements because a fifth failed, and
`compute_score` already renormalises over missing sub-scores — the machinery and the precedent
are both already here. Every such score now carries the driver *"Valuation withheld — no
fair-value, Monte Carlo or comps term contributes to this score. Scored on quality, growth,
financial health and momentum only."* and confidence is forced to **low**.

**The falsifier I named could not be evaluated, and I am flagging that rather than claiming a
pass.** I said I would abandon the partial score if withheld names systematically landed in a
different part of the distribution such that the same number meant two different things. After
all fixes there are **5 withheld names** (18, 40, 40, 47, 50) against 236 publishable ones
(min 16, p25 44, median 51, p75 65, max 85). The withheld set does sit lower — but n=5, and
three of them are pinned at ≤50 by the cap that is *supposed* to pin them. **That is not enough
evidence to evaluate the falsifier**; the mitigations are that the score is labelled in its
drivers and forced to low confidence. If the withheld set grows, re-check it.
→ **For the app lane:** it should render as a partial score, not a full one.

### ITEM 3 — candidate A: ADOPTED ON COHERENCE, NULL ON PERFORMANCE

`MIN_TERMINAL_SPREAD = 0.030` ships. **It did not pass the Part 2 pre-registered test** — that
test was resolve-the-names and it resolved none — and it is not restated here as though it did.
It ships because a 0.005 floor is a 200x terminal multiple, i.e. a floor that has never bound
and therefore is not a floor. Measured harm, isolated: median |Δ| **0.000000%**, **0 of 234
names moved >25%**, withheld count **7 → 7** (unchanged, exactly the null result Part 2
predicted). Largest single moves: PCG 16.7%, TTE 15.6%, LMT 13.8%, INFY 13.4%, COP 12.5%,
VZ 9.5% — all low-WACC names where the old floor let the multiple run.

The pinning test is restored and green:
`test_low_beta_defensive_name_does_not_degenerate_the_terminal_value`.

**Close-out on CHTR, CI and JD** (all fixes on):

| name | price | regime | terminal multiple | TV as % of EV | DCF | headline | verdict |
|---|---|---|---|---|---|---|---|
| CHTR | $153.17 | mature | **56.0 → 33.3** | 83.7% | $2,080 → $1,348 | still **withheld** (8.1x) | **model defect** |
| CI | $270.50 | mature | 37.1 → 33.3 | **93.5%** | $1,792 → $609 | **publishes $1,013** (3.7x) | fragile |
| JD | $32.54 | mature | 35.2 → 33.3 | **97.9%** | $237 → $84 | **publishes $109** (3.3x) | fragile |

- **CHTR: A cut the terminal multiple from 56.0x to 33.3x and the DCF from $2,080 to $1,348, and
  it is still withheld at 8.1x price.** The remaining gap is a **model defect, not a real
  verdict** — 83.7% of enterprise value is terminal, and BUGS FOUND #5 is unresolved: the
  forecast still more than doubles free cash flow ($37/share today to $85 in year 5) on 1.16x
  revenue and a flat margin, which points at `sales_to_capital` under-charging reinvestment for
  a capex-heavy cable operator. **CHTR is the one name where nothing shipped in Part 3 helps.**
- **CI and JD now publish — but not because the terminal fix worked.** They publish because
  item 1 reclassified them from growth to mature. And they publish numbers that are **93.5% and
  97.9% terminal value**, which is a fragile figure, not a confident one. Counting them as
  "resolved" would overstate the result.

### What I did NOT do, and why

- **Did not fix the day-to-day reproducibility problem** (MRK swinging from "cannot value" to a
  91 "Strong Buy" because Yahoo stopped returning one beta field), as instructed. What it would
  take: a **stated, stable beta fallback** — the current one silently substitutes 1.10, which is
  what moved MRK's WACC 5.53% → 9.31% overnight — plus a **provenance/staleness stamp** on the
  inputs a valuation rests on, so a headline that changed because a vendor field vanished is
  distinguishable from one that changed because the company did. The adjacent half is BUGS FOUND
  #2, still open: `wacc.py:67` has **no low-side beta floor and no minimum-history check**, so
  KSPI's 0.08 (30 monthly observations on a 2024 ADR listing) still passes as plausible.
- **Did not re-tune anything after seeing results.** The `[-0.30, 1.00]` band at the source is
  the same band the engine already used.
- **Did not touch** `valuation/edge/**`, `fundamental_panel.py`, `factors.py`, `settings.py`,
  `screen.py`, `valuation/web/**` or `valuation/report/**`.

## BUGS FOUND (Part 3)

1. **A NaN analyst growth became an explicit 100% growth forecast**, because `min(1.00, nan)`
   returns `1.0`. It classified **WELL** as hypergrowth. Third instance of "a clamp disguising
   garbage as a plausible extreme"; already rejected by the Part 2 band check, now also at
   source.
2. **`growth_estimates` is not shape-stable across names** — BRK.B's frame has only
   `indexTrend`. Any positional read of that frame is reading the index, not the company.
3. **`info["revenueGrowth"]` is itself unreliable** — COF returns **11.11**. Rejected at source.
4. **CI and JD publish fair values that are 93.5% and 97.9% terminal value.** They pass the 5x
   guard, so nothing flags them, but a number that is ~all terminal value deserves a
   confidence marker. No guard currently looks at `tv_pct_of_ev` — `DCFResult` has carried it
   all along.
5. **CHTR (BUGS FOUND #5 from Part 2) is still open and is now the single worst remaining
   name**: 83.7% terminal, FCF/share modelled to more than double on 1.16x revenue.

---

# PART 4 — the screener lens, CHTR's reinvestment, and the terminal-share question (2026-08-05)

## PRE-COMMITMENT (item 1 only) — committed before the change is written or measured

Items 2 and 3 do not get one and the reasons are stated rather than assumed: **item 3 ships no
fix** (it closes on the distribution, which the prompt asked to be measured first), and **item 2
changes no published number** (diagnosis plus a diagnostic field — I assert fair values come out
bit-identical as a check, which is a correctness assertion, not a tuned bound).

The exposure measurement (task 1.2) deliberately came *first* and informs the threshold choice
(task 1.3), as the prompt sequences it. What is committed below is the do-no-harm bound on the
**effect of my change**, which has not been measured yet.

### Control groups — checked BEFORE committing, having been burned by a bound that had none

| change | control group | size | verified |
|---|---|---|---|
| add `net_debt` to `_ABSOLUTE_USD` | names with `abs(nd)/mc < 0.01` — the fix cannot move them | **13** | yes |
| absolute 5x cap on the lenses | names already below 5x — only names above it may change | **239/239** multiples, **204/206** growth | yes |

**The units control group is 13 names, and that is weak.** It can catch a gross error; it cannot
catch a subtle one. Saying so now rather than discovering it afterwards.

### The bounds

1. **Units fix.** The 13 control names must move by **< 0.1%** in multiples-lens implied value
   (pure float noise). The other 226 are expected to move — that is the fix — and are reported
   without a bound.
2. **5x cap.** Every name below 5x must be **bit-identical**. Only names above 5x may change, and
   they may only change to "no value published", never to a different number.
3. **Predicted effect, stated in advance so a surprise is visible:** with units fixed, the
   multiples lens tops out at **4.59x**, so the cap should suppress **zero** multiples names; the
   growth lens has exactly **two** names above 5x (ELV 5.44x, JD 5.09x), so lowering
   `MAX_GROWTH_VALUE` from 20 to 5 should suppress **exactly those two**. If more than two names
   are suppressed anywhere, my change has an effect I did not predict and I will investigate
   before shipping rather than explain it afterwards.

### The threshold, argued

Three bars exist for one claim: the valuation page refuses at **5x** (`FV_BAND_HIGH`),
`_growth_value` caps at **20x**, and the multiples lens has **no absolute cap at all**.
**Proposal: one bar, 5x, everywhere.** The screener's hot-list fair value and the valuation
page's fair value are the same claim about the same company, published by the same product; a
number the valuation page would refuse to print is not one the public hot-list should print
either. 20x was never reachable — the growth lens maxes at 5.44x on a real universe — so it is
not a bar, it is decoration.

**This ships on coherence, not on measured harm**, exactly as candidate A did in Part 3: the
measured tail above 5x in the multiples lens is currently **empty**. I am not going to claim it
prevents something it does not currently prevent.

## PART 4 RESULTS — measured after the pre-commitment above (887981c)

Suites: **20 suites, 699 tests, all green.**

### ITEM 1 — the multiples lens. VERDICT: ADOPTED (units fix on correctness; cap on coherence)

**Which of the two is broken: the assumption, plus a units bug nobody had found.**

The bridge arithmetic is right. `equity = ev*ratio - nd` with `ev = mc + nd` reduces exactly to
**`implied/price = r + (nd/mc)*(r - 1)`**, and at `r = MAX_RERATE = 3` that is the app lane's
`3 + 2*(nd/mc)`. Equity is a residual claim and leverage genuinely amplifies it, so the algebra
is correct. **What is indefensible is the assumption**: applying a uniform 3x enterprise re-rate
to a name that trades cheap on an enterprise multiple *because* it is levered. That is where a
3x EV move becomes an 11x equity move.

**But the far bigger finding is that the bridge has not been working at all.** `net_debt` was
**missing from `providers._ABSOLUTE_USD`**, so it alone was emitted in the provider's native
millions while `market_cap`, `ev` and `total_debt` beside it were scaled to dollars.
`screen.py::_rows_from` copies it straight into `extra`, and `fairvalue.py` then computes
`ev = market_cap + net_debt` as **dollars + millions** — making the net-debt term ~1e-6 of its
true size and silently collapsing the bridge to a bare re-rate. CHTR's real net debt / market
cap is **4.68**; the lens saw **96,644 against 20,643,866,624**.

Same class as the P7 currency bug and as everything in Parts 1-3: every column present, every
column populated, one of them in the wrong unit, no error raised.

**Real exposure — the number nobody had.** Reconstructed a 239-name universe snapshot in the
production row shape:

| | today (live units bug) | units fixed, no cap |
|---|---|---|
| multiples implied/price, median | 1.02 | 1.02 |
| p90 | 2.11 | 2.20 |
| **max** | **3.00** (exactly `MAX_RERATE`) | **4.59** (STLA) |
| **names above 5x price** | **0** | **0** |
| names above 3x | 2 | 3 |

**Zero names exceed 5x through this lens, before or after the units fix.** The app lane's
`$330 against a $10 price` required both extreme leverage *and* a full 3x re-rate; on real data
CHTR lands at 2.72x, not its 12.4x ceiling, because its EV multiples are not 3x cheaper than its
peers'. True `nd/mc` across the universe: median ~0, p90 ~0.5, **max 4.68 (CHTR)**, with 2 names
above 2.0. The ceilings are real (CHTR 12.4x, F 7.5x, BNS 6.3x, PCG 6.2x) but nothing reaches them.

**Threshold reconciliation: one bar at 5x.** The valuation page refuses at 5x (`FV_BAND_HIGH`),
`_growth_value` capped at 20x, the multiples branch had no absolute cap. `MAX_LENS_VALUE = 5.0`
now bounds both branches. 20x was never a bar — the growth lens tops out at 5.44x on a real
universe — so it was decoration, not a guard. **Adopted on coherence: the measured tail above 5x
in the multiples lens is empty, and this is not claimed to prevent anything today.**

**Against the pre-committed bounds:**

| bound | result |
|---|---|
| 2 — every name below 5x bit-identical | **PASS** — multiples 239 names, 0 changed; growth 204 names, 0 changed |
| 3 — predicted 0 multiples / exactly 2 growth suppressed | **PASS** — multiples 0, growth exactly 2 (ELV 5.44x, JD 5.09x) |
| 1 — 13 control names move < 0.1% | **BREACH — and the bound was invalid. Mine.** |

**On bound 1, plainly: I was told to check a control group existed before committing to one,
I did check, and my check was still wrong.** I verified that a *proxy* was non-empty
(13 names with `abs(nd)/mc < 0.01`) instead of verifying the *defining property* — that the
change cannot move them. It can: the bridge moves a name by up to `2*(nd/mc)`, so a 1%-leverage
tolerance permits ~2% of movement, and bounding that at 0.1% was arithmetically incoherent from
the moment I wrote it. Observed max was **1.736% on PANW**, which is `2*(nd/mc)` for PANW to
five decimal places — the fix operating exactly as the algebra says, not a side effect.

**A true control group does not exist at all: no name in the 239 has net debt of exactly zero.**
Every name is moved by this fix. So item 1's units change ships on **correctness** — a figure in
millions was being added to a figure in dollars, which is unambiguous — and not on a do-no-harm
result. Largest moves: RY +78%, F +78%, STLA +53%, EIX +47%, BBD +46%, TD +41%, TM +40%, GM +35%.

**A latent danger worth stating:** fixing the units *without* the cap would have been the
dangerous change. The `3 + 2*(nd/mc)` amplification is currently inert only because the net-debt
term is ~zero; restore it alone and CHTR's ceiling becomes 12.4x on a public endpoint. The two
changes belong together, and shipping either half by itself would have been worse than shipping
neither.

### ITEM 2 — CHTR. VERDICT: CLASS DEFECT CONFIRMED, quantified, deliberately NOT fixed

`sales_to_capital` is **not** mis-set, **not** mis-derived and **not** applied to the wrong base.
CHTR's is 1.5 (Communication Services 2.0, nudged down 0.75x for capex intensity 21.3%) — a
reasonable number, correctly derived, correctly applied. **The method itself breaks down.**

Reinvestment is modelled as `delta revenue / sales_to_capital`, i.e. **growth capital only**.
That is the standard Damodaran formulation and it is fine for a company whose capital needs
scale with growth. It collapses when revenue is flat:

| CHTR year | revenue | modelled reinvestment | FCFF | FCFF/share |
|---|---|---|---|---|
| 1 | 54,893 | **-79** | 9,817 | $82.31 |
| 5 | 59,309 | -1,152 | 9,541 | $79.99 |

CHTR's **observed net capital spend is capex 11,659 - D&A 8,711 = $2,948M/yr**. The model charges
**$79M in year 1** — an undercharge of $2,869M, and that is why free cash flow can more than
double on 1.16x revenue at a flat margin.

*(Correcting my own Part 2/3 note: I compared the model's $82.31/share FCFF with CHTR's reported
$37.04/share FCF as though they were the same measure. They are not — FCFF is unlevered, the
reported figure is after interest, and CHTR pays roughly $5bn of it. The undercharge is real; the
2.2x comparison I used to describe it was not apples to apples.)*

**The population, which matters far more than CHTR** — 205 non-financial names with capex and D&A:

- **114** have positive net capital spend (capex > D&A).
- Undercharge (net capex - modelled reinvestment): median **$141M**, p75 **$2,557M**,
  p90 **$7,106M**, max **$48,884M**.
- As a share of revenue: median 0.51%, p75 **7.24%**, p90 **13.57%**, max **57.94%**.
- **34 names undercharged by more than 5% of revenue; 22 by more than 10%.**
- Sectors: **Utilities 11, Energy 6, Basic Materials 6**, Technology 4, Communication Services 3,
  Industrials 2, Healthcare 1, Real Estate 1 — exactly the capex-heavy prediction.
- Worst: SRE 57.9% of revenue, ORCL 54.7%, D 44.1%, NVO 17.6%, MSFT 14.7% ($48.9bn), E 13.9%.
- **Several energy names have NEGATIVE modelled reinvestment** (XOM -8,088, TTE -11,108,
  E -11,016, PBR -7,219): shrinking revenue is credited as *releasing* capital the company is
  not releasing, so the model adds cash for contracting.

**Not fixed, and the reason is the same one that kept the WACC floor out of Part 2:** changing
how reinvestment is modelled moves **every** valuation in the product, and it is a modelling
decision with its own before/after, not a bug fix to slip into a lane about a screener lens.
**This is now the largest known defect in the valuation engine** — larger than anything in
Parts 1-3, because it inflates free cash flow for 34 names by more than 5% of revenue each.

What ships instead: `DCFResult` now carries `reinvestment_y1` and `observed_net_capex`, and the
pipeline emits a warning when the shortfall exceeds 5% of revenue — *"The forecast reinvests
79 in year 1 against 2,948 of observed net capital spend (capex minus D&A) — a shortfall of 5%
of revenue. Free cash flow is modelled higher than this company has been able to produce."*
No published number changes. Verified firing on CHTR (5%), SRE (58%), D (44%), ORCL (55%) and
staying silent on AAPL. Pinned by
`test_flat_revenue_capex_heavy_name_flags_its_reinvestment_shortfall`.

### ITEM 3 — a 98%-terminal figure. VERDICT: CONCERN MISPLACED, CLOSED, no fix

Measured first, as instructed. TV as a share of EV across **208 non-financial names**:

| | value |
|---|---|
| min | 45.6% |
| p25 | 70.0% |
| **median** | **76.7%** |
| p75 | 83.2% |
| p90 | 86.5% |
| above 90% | 13 names (6.2%) |
| above 95% | 9 names (4.3%) |
| above 100% | 8 names (3.8%) |

And the population that values **well** (0.5-2.0x price, n=96): median **77.5%**, p75 83.2%,
p90 **85.1%**, max 117.9%.

**The decisive number: names valuing at more than 5x price (n=3) have a median terminal share of
82.2% — LOWER than the p90 of the names that value sanely (85.1%).** Terminal share does not
separate good valuations from bad ones. A threshold on it would fire on healthy mature names and
miss the pathological ones. CI's 93.5% and JD's 97.9% sit at roughly the 93rd and 96th
percentile of a distribution whose median is 76.7% — elevated, but not a different species, and
a DCF of a mature business being three-quarters terminal value is simply what the arithmetic of
a 5-10 year explicit forecast produces.

**So I am closing this and shipping nothing for it.** My Part 3 caveat that counting CI and JD as
"resolved" would overstate the result still stands as a caveat, but the stronger claim in this
prompt — that a 98% terminal share means the number is not a valuation — is not supported by the
distribution. Recording the measurement so nobody re-opens it on intuition.

**One real thing in the tail:** the 8 names above 100% (F **785%**, BA 385%, SNAP 159%, WELL
120%, STLA 118%, CPNG 114%, SNOW 107%, KHC 102%). A terminal share above 100% means the explicit
forecast has *negative* present value — the company burns cash for the whole horizon and the
entire valuation rests on what happens after it. That is a genuinely different statement from
"93.5%", and F at 785% is worth someone's attention. Logged in BUGS FOUND, not fixed here.

### What I did NOT do, and why

- **Did not fix the reinvestment model** (item 2) — the largest known defect, deliberately left
  to its own pre-registered task for the reason above.
- **Did not add a terminal-share guard** (item 3) — the data says it would not discriminate.
- **Did not touch** `valuation/web/**` or `valuation/report/**` (the app fixer is guarding the
  public call site in parallel) or `valuation/edge/**`.
- **Did not re-tune `MAX_RERATE`.** A leverage-aware re-rate cap is the principled fix for the
  assumption I called indefensible above; it changes what the lens computes for 226 names and
  belongs with the reinvestment work, not bolted on here.

## BUGS FOUND (Part 4)

1. **`net_debt` was missing from `providers._ABSOLUTE_USD`** — emitted in millions beside
   dollar-scaled `market_cap`/`ev`, silently disabling the EV bridge for every levered name.
   Fixed. **This is the fifth unit/field-mismatch bug in this family** (P7 currency, the `assets`
   loader allowlist, the SF3 positional arg, the growth field, this).
2. **The multiples lens had no absolute cap** while the growth branch did and the valuation page
   refuses at 5x — three bars for one claim, on a public endpoint. Fixed, one bar at 5x.
3. **Fixing the units without the cap would have been actively dangerous** — the
   `3 + 2*(nd/mc)` amplification is inert only because net debt is currently ~zero to the lens.
4. **Reinvestment collapses to near-zero for flat-revenue capex-heavy names** — 34 of 205
   undercharged by >5% of revenue, 22 by >10%; several energy names are charged *negative*
   reinvestment. Flagged, not fixed. **Largest open defect in the engine.**
5. **8 names carry a terminal share above 100% of EV** — F at **785%** — meaning the explicit
   forecast has negative present value. Not investigated.
6. **`MAX_GROWTH_VALUE = 20.0` never bound on a real universe** (growth lens max 5.44x). A
   "sanity cap" that cannot fire is not a sanity cap — the same shape as `dcf.py`'s 0.005
   terminal floor from Part 2 and `wacc.py`'s beta > 3.0 check.

---

# PART 5 — CONSOLIDATE-1: one publication decision (2026-08-06)

## PRE-COMMITMENT — committed before any code change

### The control group, checked properly this time

Part 4's bound broke because I verified a *proxy* was non-empty instead of the defining
property. The defining property is: **a control group is a set the change is mechanically
incapable of touching.**

Here one genuinely exists, and it is most of the universe. This is a **pure refactor** for every
name whose fair value is currently publishable: the arithmetic that produces the number is not
touched at all, only the code path that asks *"may it be shown?"*. For a name whose ratio sits
inside the band with a resolvable currency, the consolidated decision returns the identical
verdict by construction — same value, same absent reason, same method tag.

**The comparison boundary is fixed now so it cannot be tuned later:** `ratio > band` refuses,
`ratio == band` publishes. That matches both existing forms — `pipeline.py`'s
`ratio > FV_BAND_HIGH` and `fairvalue.py`'s `out <= price * MAX_LENS_VALUE` — so no name sitting
exactly on 5.0x may change state.

### Bounds

1. **Every name the engine currently PUBLISHES must come out bit-identical** — same fair value,
   same upside, same method, no new refusal. This is the control group and it is mechanical.
   **If any such name's number changes, that is a FINDING to report, not noise to absorb.**
2. **Names the engine currently REFUSES must change, and only in one direction:** the scan row
   must carry `fair_value = None`, `fair_value_withheld = True`, and a non-empty reason. Today
   they carry a peer-substituted number. A refused name that still shows a fair value after this
   change is a failure of the task.
3. **Exactly one site may own the band after this change.** Every other site imports it. The
   census below is the before-state; the after-state must have no second definition, no literal
   `5` or `0.2` restatement, and no independently-worded refusal string in `engine/**`,
   `screener/**` or `screen.py`. (`valuation/web/**` is another lane's and already imports
   `FV_BAND_HIGH` rather than copying it — out of scope to edit, in scope to verify.)

### Predicted effect, stated in advance so a surprise is visible

The three names named in the prompt — **KSPI, STLA, CHTR** — plus any other name the engine's
guard refuses, lose their peer-substituted hot-list fair value and gain a stated refusal. I
expect the count of newly-withheld hot-list rows to equal the count of names the engine refuses,
and **no other row to change at all**. If rows change that the engine does not refuse, I will
investigate before shipping rather than explain it afterwards.

### What I will NOT fold in

The **reproducibility problem** (MRK's vanishing beta, `wacc.py:67`'s missing low-side floor and
minimum-history check). It changes valuations, and mixing it into a refactor whose whole claim is
"every published number is bit-identical" would destroy the only bound that makes this
verifiable. It gets its own task, as instructed.

## PART 5 RESULTS — measured after the pre-commitment above (739b478)

Suites: **20 suites, 712 tests, all green.**

### 1. THE CENSUS — every site that answered "may this fair value be published?"

The deliverable even where a site turned out to be fine. **Before** this task:

| # | site | file:line (before) | its bar | verdict |
|---|---|---|---|---|
| 1 | valuation page guard | `engine/pipeline.py:47` `FV_BAND_HIGH = 5.0` | 5x | **the survivor** — moved to `engine/publication.py` |
| 2 | ...and its implementation | `engine/pipeline.py:50-84` `publication_guard` | 5x + FX | folded into `publication.decide` |
| 3 | screener growth lens | `screener/fairvalue.py:79` `MAX_GROWTH_VALUE = 20.0` | **20x** | **DELETED** — never bound (lens tops out at 5.44x) |
| 4 | screener multiples lens | `screener/fairvalue.py:185` | **none at all** | now calls `decide` |
| 5 | growth-lens application | `screener/fairvalue.py:240` | 20x | now calls `decide` |
| 6 | pipeline's warning | `engine/pipeline.py:301` `ratio > 5 or ratio < 0.2` | **literals** | imports `FV_BAND_HIGH` / `FV_BAND_LOW` |
| 7 | scoring's cap | `engine/scoring.py:250` `ratio > 5 or ratio < 0.2` | **literals** | imports the constants |
| 8 | **the scan** | `screener/screen.py::_enrich_with_dcf` | **erased the refusal** | **records it** |
| 9 | the estimator | `screener/fairvalue.py:227 estimate_fair_values` | read `None` as "not computed" | honours a recorded refusal |
| 10 | re-rate cap | `screener/fairvalue.py:58` `MAX_RERATE = 3.0` | 3x on the *re-rate* | **not a publication bar** — bounds an input, left alone (see BUGS FOUND) |
| 11 | web guard | `web/withhold.py:151` | imports `FV_BAND_HIGH` | **already correct** — other lane, verified not copied |
| 12 | web row fields | `web/app.py:174-175`, `web/unified.py:242-243` | pass-through | fine |
| 13 | renderer | `web/static/app.js:205, 992` | reads the row flag | fine |

**Seven copies, not five.** Sites 6 and 7 were literal restatements that a constant-name search
does not find — I only caught them by grepping for `ratio > 5`. That is worth recording: the
census had to be done twice, by two different searches, and the second one found two more.

### 2. THE DECISION OBJECT — `valuation/engine/publication.py` (new)

```
decide(value, price, *, cd=None, growth_led=False) -> PublicationVerdict
    publish, value, withheld_value, ratio, band, reason
```

One band (`FV_BAND_HIGH = 5.0`), one low-side warning threshold (`FV_BAND_LOW = 0.2`), one
refusal sentence, one pair of canonical row keys (`ROW_WITHHELD`, `ROW_WITHHELD_REASON`), and
`record_refusal(row, reason)`.

Consumers, all of which now **import** rather than restate: `pipeline.publication_guard` (a thin
wrapper kept for existing callers, adding no threshold of its own), `pipeline`'s implausibility
warning, `scoring`'s >5x cap, `fairvalue._mature_value`, `fairvalue._growth_value`,
`fairvalue.estimate_fair_values`, `screen._enrich_with_dcf`. `FV_BAND_HIGH` is re-exported from
`engine/pipeline.py` because `web/withhold.py` imports it from there — the same object, not a
copy, so that lane needed no change.

### 3. THE SCAN RECORDS THE REFUSAL — the leak, closed

`_enrich_with_dcf` wrote `r["fair_value"] = res.base_fair_value` and nothing else. On a refusal
that is `None`, and `estimate_fair_values` reads a `None` fair value as *"no DCF computed yet"*
and substitutes a peer estimate. The publication guard's decision was erased between two lines
of the same pipeline.

**Measured on real rows, before vs after:**

| name | price | hot-list fair value BEFORE | AFTER | withheld |
|---|---|---|---|---|
| CHTR | $153.17 | **$395.09** | — | YES |
| KSPI | $92.19 | **$290.89** | — | YES |
| STLA | $5.63 | **$22.12** | — | YES |
| BRK.B | — | (none) | — | YES |
| HES | — | (none) | — | YES |

Exactly the three names the prompt named were leaking. BRK.B and HES were refused too but had no
lens inputs, so they were not publishing anything to erase. Confirmed that `web/withhold.py`
honours the flag the moment the scan sets it — its `withhold_implausible_fair_values` triggers on
a pre-marked row, so the public surface closes with no change in that lane.

*(The state-of-play records KSPI's leaked value as $299.16; my snapshot gives $290.89. Same leak,
different peer medians on a different day — not a discrepancy worth chasing.)*

### 4. AGAINST THE PRE-COMMITTED BOUNDS

| bound | result |
|---|---|
| 1 — every currently-publishable name bit-identical | **PASS. 236 publishable names, 0 changed.** Fair value, upside and method all identical. |
| 2 — refused names lose the substitute and gain a reason | **PASS.** All 5 refused names carry `fair_value = None`, `fair_value_withheld = True` and a non-empty reason; 3 of them were previously publishing a number. |
| 3 — exactly one site owns the band | **PASS**, enforced by a test rather than by inspection. |

**This is the first bound in this file that passed cleanly on the first attempt**, and the reason
is that the control group was real: the refactor genuinely cannot touch the arithmetic that
produces a publishable number, so "236 names unchanged" was a mechanical prediction rather than a
hope. Part 4's bound failed because it was a proxy; this one is the defining property.

### 5. WHAT WAS DELETED

**`MAX_GROWTH_VALUE = 20.0` is gone**, not aliased. Measured in Part 4, the growth lens tops out
at **5.44x** and the multiples lens at **4.59x** on a real 241-name universe, so a 20x cap had
never once fired. **Decoration that reads like a guard is worse than no guard** — the next person
to audit this counts it as protection. `MAX_LENS_VALUE` survives only as `MAX_LENS_VALUE =
FV_BAND_HIGH`, an alias for readers of that module, and a test asserts it `is` the same object.

### 6. THE TEST THAT STOPS COPY SIX

`test_publication_band_has_exactly_one_definition` walks `valuation/engine/**` and
`valuation/screener/**` and asserts (a) exactly one file assigns `FV_BAND_HIGH`/`FV_BAND_LOW` a
numeric literal, and (b) **no file compares a price ratio against a bare number** — the shape
that sites 6 and 7 had and that a constant-name search misses. `test_every_publication_site_
resolves_to_the_same_constant` asserts every surface, including the web lane's `withhold._band()`,
resolves to the one object, and pins the boundary (`== band` publishes, `> band` refuses).
`test_a_refused_row_is_not_re_estimated_from_peers` pins the scan leak.

**The guard was verified non-vacuous**, because this project's signature failure is a guard that
cannot see the thing it guards: I injected a sixth copy (`def _sixth_copy(ratio): return ratio > 5`
into `fairvalue.py`), confirmed the test fails and names the file, then reverted and confirmed it
passes. It is not taken on faith.

### What I did NOT do, and why

- **Did not fold in the reproducibility work** (MRK's vanishing beta, `wacc.py:67`'s missing
  low-side floor and minimum-history check), as instructed. It changes valuations, and mixing it
  into a refactor whose entire claim is "236 published numbers are bit-identical" would have
  destroyed the only bound that makes this verifiable.
- **Did not touch `MAX_RERATE`.** It bounds an *input* (how far a peer multiple may re-rate), not
  whether the output may be published — a different decision that happens to live in the same
  file. Conflating them would have re-created the problem this task exists to remove.
- **Did not edit `valuation/web/**` or `valuation/report/**`** (app-fixer lane) or
  `valuation/edge/**`. The web guard already imports the constant; verified, not modified.

## BUGS FOUND (Part 5)

1. **The census found SEVEN copies, not the five recorded in the state-of-play.**
   `engine/pipeline.py:301` and `engine/scoring.py:250` each restated `ratio > 5 or ratio < 0.2`
   as literals. A search for the constant's *name* cannot see them; only a search for the
   *number* can. Any future consolidation should search for both.
2. **`pipeline.py`'s >5x warning has been dead since Part 1.** It reads
   `result.base_fair_value`, which the publication guard sets to `None` on exactly the names
   that would trip it — so the high branch can no longer fire and only the `< 0.2` branch is
   live. Same shape as the `scoring.py` cap fixed in Part 3. Left in place (the low branch is
   real) but the high branch is now unreachable and should be deleted by whoever next touches
   that block.
3. **`MAX_RERATE = 3.0` is the last unbounded-by-construction input in this path** — Part 4
   showed the bridge implies `implied/price = r + (nd/mc)*(r-1)`, so a uniform 3x re-rate on a
   4.68x-levered name has a 12.4x ceiling. The 5x publication bar now catches the *output*, but
   the *assumption* is still that a levered name can re-rate 3x on enterprise value. Flagged in
   Part 4, still open.

---

# Part 6 — Close the public fair-value leak for real (Bug A + Bug B)

## PRE-COMMITMENT — written and committed BEFORE any outcome was measured

This section is committed on its own so its ordering is provable in git. Everything below the
`RESULTS` heading was written after. Two things were checked *before* this was written, because
committing to a bound that turns out unmeasurable is the mistake this lane has made twice:

**(i) Can the model even be run here?** Yes — `value_ticker` runs locally against the live feed.
**(ii) Does a control group exist?** Yes for both bugs, and they are named below. This was
checked first, not assumed.

### What I already know before measuring (facts, not outcomes)

Captured from **live production** (`GET https://valquo.co/api/hotstocks?top=500`, signed out,
2026-08-07) before touching anything:

- The served list is **399 rows**, scan_date 2026-08-07, universe 800, provider FMP.
- **Exactly 12 rows carry `fair_value_method = "dcf"`** — `STT, DB, UNVGY, ADBE, ACGL, HIG,
  NTAP, EC, BCS, ALL, MFC, RVMD`. That is `SCAN_DCF_TOP=12`, confirmed from the outside.
- **386 rows carry a peer estimate** (`blended` 325, `multiples` 60, `growth` 1). **398 of 399
  rows publish a fair value.**
- **0 rows carry `fair_value_withheld`.** Consistent with both "no refusal happened today" and
  "the flag cannot survive the database". The A/B below distinguishes them.
- KSPI, STLA and CHTR are **not in today's snapshot at all**, so the three names the bug was
  originally found on cannot be used as the proof today. The mechanism is what I must prove,
  on whatever names production is actually serving. I will say so plainly rather than quietly
  substituting different tickers and presenting them as the same evidence.

One measurement that changes the shape of Bug B, taken before the pre-commitment because it is
a cost fact rather than an outcome: on five real names outside the DCF window, the **Monte Carlo
costs 0.03–0.08s and the fetch costs 1.1–6.6s**, and `base_fair_value` is **identical at
`mc_trials=1500` and `mc_trials=1`**. The refusal is computed from `blend`, which the Monte
Carlo never feeds. **So the price of asking "would the model refuse this name?" is the fetch,
not the simulation.**

### Bug A — the refusal must survive the snapshot

**Success:** a row that `_enrich_with_dcf` refused comes back out of
`save_snapshot → load_snapshot → estimate_fair_values → withhold_implausible_fair_values` as
`fair_value=None, fair_value_method="withheld"`, with its reason string intact.

**CONTROL GROUP: exists, and it is every row that was never refused — all 399 today.**
**Bound: their served `fair_value` must be BIT-IDENTICAL before and after, not merely close.**
This change adds two columns and alters no arithmetic, so any movement at all on a non-refused
row is a defect in my change, not a judgement call. Committing to exact equality is only
honest because I checked first that the comparison is actually runnable.

**Migration:** old snapshots have no such columns. I commit in advance to reading a missing
column as **not withheld** — i.e. exactly today's behaviour for rows written before the fix —
and to stating in the report that this means **the leak stays open on already-stored snapshots
until the next scan overwrites them**. The alternative (treating unknown as withheld) would
blank fair values across the stored history on no evidence. I will not present a one-scan delay
as if it were instant.

### Bug B — the ~386 names that never get a DCF

Three options. I commit to the decision rule now, not the decision:

- **(a) Raise `dcf_top` to cover the served list.** Closes the leak — and also **replaces the
  published fair value on ~386 names** with a different model's number. That is a product
  change, not a leak fix.
- **(b) Ask the model only for its REFUSAL, and leave a non-refused name's published peer
  estimate exactly as it is.** Closes the leak; changes nothing else.
- **(c) Stop publishing peer fair values for un-valued names.** Closes the leak by deleting the
  feature for 386 of 399 names.

**I commit to (b) unless the measurement contradicts it**, for a reason I am fixing in writing
now so it cannot be retro-fitted: the defect is *publishing a number the model refuses*, and
(b) is the smallest change that removes exactly that. **(a) is available at identical cost** —
the fetch is the whole price and (b) pays it too — so if Don wants DCF coverage on the whole
list, it is one constant away. **That is his call, not mine to make inside a bug fix.**

**CONTROL GROUP for (b): exists — every name the model does NOT refuse.**
**Bound: their published fair value must be BIT-IDENTICAL before and after.** Under (a) no
control group would exist, because every served name's number would change route; under (c)
the same. **That a control group exists at all is a reason to prefer (b), and I am recording
that as part of the reason rather than discovering it afterwards.**

**Cost bar, fixed now:** adopt (b) only if the added scan time is **under 20 minutes** at the
scan's existing concurrency. If it exceeds that, I fall back to gating the check to the served
window rather than the whole universe, and I report the number either way — including if it
lands somewhere I would rather it did not.

**What I will NOT do:** invent a cheap proxy for the refusal (a ratio heuristic, a currency
sniff). `valuation/engine/publication.py` exists precisely because this decision had five
independent implementations. A sixth, cheaper, approximate copy in the screener would be the
same bug wearing a performance argument. If the real decision is too expensive, the honest
answer is to narrow its scope, not to approximate it.

### The verification bar, agreed in advance

**Production, not the suite.** The catch-all test walks *ratios* and every name in this class
sits under the band — it provably cannot catch this, and a green suite is necessary and not
sufficient. I commit to reporting the live production response before and after, and to saying
so explicitly if the three original names are still absent from the list when I check.

### What would make me report a failure rather than a fix

- Any non-refused name's fair value moving by any amount.
- The round-trip test passing in memory but not through a real `Store` on disk.
- The refusal surviving the DB but not the serve-time re-estimation.

## RESULTS — measured after the pre-commitment above (1f6ad92)

Both bugs are fixed. **The most consequential thing this session found was not either of them:
it was a defect pointing the OTHER WAY, in the CONSOLIDATE-1 fix I shipped, which suppresses
fair values on names nothing ever refused.** I hit it because my own first measurement made the
identical mistake.

Two numbers to hold onto before the detail:

- **Bug A was live and is now closed.** Reproduced on the real production rows, not inferred.
- **Bug B is a real structural hole whose live blast radius today is ZERO.** Asked the model
  about all 387 served names it never valued: **0 genuine refusals.** My fix therefore removes
  **no** published number from today's list. Saying otherwise would be the easy sentence and
  the wrong one.

### BUG A — the refusal did not survive the snapshot. REPRODUCED, then FIXED.

`store.save_snapshot` wrote a fixed 18-column INSERT and `snapshot_rows` had no column for
either refusal key, so the scan recorded the decision and the database discarded it.

Reproduced through a **real `Store` on disk**, on the **real 399-row production snapshot**,
refusing the rank-1 name exactly as KSPI (rank 3) was refused:

```
after record_refusal:   STT withheld=True  fair_value=None
A: serve WITHOUT the snapshot round-trip    -> fair_value=None  method=withheld   (correct)
B: read back from the DB                    -> withheld=None
B: serve THROUGH the snapshot, as prod does -> fair_value=386.68083192601813  method=blended
```

**`$386.68083192601813` is what the public list publishes for a name the model refused.** The
mechanism is not inferred.

**The fix:** two columns on `snapshot_rows`, an in-place `ALTER TABLE` migration matching the
one already used for `positions`, both keys named in the INSERT, and a reader that converts
SQLite's `0/1/NULL` to a bool. The key names are imported from `engine/publication.py` rather
than restated, so the scan, the database and the web surface cannot drift to different
spellings of one decision.

One reader detail that is easy to get wrong and would have caused a second bug: a row that was
never refused comes back carrying **neither key**, not a key set to `None`.
`withhold_implausible_fair_values` uses `setdefault` on the reason, which would happily keep a
present-but-`None` reason and blank a cell **without saying why** — the exact failure an
existing test (`test_guards.py:224`) forbids.

**After the fix, same harness:** `B: serve THROUGH the snapshot -> fair_value=None
method=withheld`.

**Pre-registered control bound: HELD.** All **399** rows, saved+loaded+served through the new
store with no refusal anywhere, reproduce the fair values production actually served
**bit-identically — 0 differences** — and **0** unrefused rows gained either new key.

**Migration, verified against a database built under the old schema:** 18 → 20 columns, the
two added, pre-existing rows read as **not withheld** (as committed in advance), and a fresh
refusal round-trips in the migrated database.

**The migration's honest cost, stated because it is a real gap and not a rounding error:** an
**already-stored** snapshot has no opinion about which of its rows were refused, so it keeps
serving what it stored **until the next scan overwrites its date**. Scans run daily, so that is
one scan — not a backfill, and not instant. Treating "unknown" as "withheld" would have blanked
fair values across the stored history on no evidence, which is worse.

### BUG B — the ~387 names that never get a DCF. FIXED, and the leak measured EMPTY today.

Confirmed from outside: **exactly 12 served rows carry `fair_value_method="dcf"`**
(`STT, DB, UNVGY, ADBE, ACGL, HIG, NTAP, EC, BCS, ALL, MFC, RVMD`) — `SCAN_DCF_TOP=12`, visible
in the public response. **387 of 399 served names publish a peer estimate that nothing has ever
checked against the valuation page's verdict.**

I then asked the real model about all 387.

| | |
|---|---|
| names asked | **387** |
| **genuine refusals** (`publication.decide` said no to a real number) | **0** |
| of which >5x band / currency | 0 / 0 |
| errored, no answer at all | **0** |
| wall clock, 6 workers | **3.0–3.8 min** (two runs) |
| per name | median **2.51s**, p90 **3.81s** |

**So the hole is structural and real, and nothing is currently falling through it.** The fix
changes no published number on today's list. I am stating that rather than quoting the "17
refusals" my first pass produced, which were not refusals at all — see the next section.

**The decision: option (b), refusal-only.** Ask the model solely *"would you refuse this
name?"*, and leave every non-refused row exactly as it was.

**The trade, named as the brief asked.** Raising `dcf_top` to cover the list costs **the same**
— the fetch is the entire price (1.1–6.6s, against 0.03–0.08s for the Monte Carlo, which is not
an input to the refusal at all) — but it would also **replace the published fair value on ~387
names** with a different model's number. That is a product decision, not a leak fix, and it is
**one constant away** (`SCAN_DCF_TOP=500`) if Don wants it. **Option (b) is also the only one of
the three that leaves a control group in existence**, which is part of why I chose it and was
recorded in the pre-commitment before any of this was measured.

**Pre-registered bound for Bug B: HELD.** The real `_screen_refusals` was run over the real
production rows and then through the real database and serve path: **387 screened, 0 refused,
399 rows compared, 0 not bit-identical, 0 moved without being refused.** Wall clock 4.2 min.
With zero refusals the control group is the entire list, which is the weakest possible version
of that bound — it demonstrates the change is inert on this data, not that it discriminates.
**The discrimination is demonstrated by the unit test, not by this run**, and pretending
otherwise would be the flattering reading.

**Cost against the pre-committed bar of 20 minutes: 3.0–3.8 min. Passes.** Wired as
`SCAN_REFUSAL_SCREEN` (default 500 = the public cap), defaulting to **0 in-process** so tests,
ad-hoc scans and the web rescan button do not silently start making hundreds of network calls.
Every scan now ships a `refusal_screen: {screened, refused}` block in the health panel —
`screened: 0` on a scan that served hundreds of names is the tell that Bug B is back.

**Fail-open on a fetch error, deliberately, and this was NOT in the pre-commitment.** A fetch
that fails tells us nothing about whether the model would refuse. The upstream feed here is
free and rate-limited — a Yahoo `401 Invalid Crumb` appeared during the 387-name run — and
failing closed would blank hundreds of fair values on a bad upstream day. **The cost of failing
open is that a name we cannot reach keeps its unchecked peer estimate.** I am flagging this as
an implementation choice surfaced by the measurement rather than a threshold I moved: it
changes no verdict above.

### THE DEFECT POINTING THE OTHER WAY — and it is live in this lane's code

**`_enrich_with_dcf` treated "the model cannot value this name" as "the model REFUSED this
name".** It refused on `base_fair_value is None and reason`, which is also true when the model
never produced a number at all — no free cash flow, no revenue, an ADR bank whose P/B–ROE
inputs are missing. Nothing has been refused about those names, and a peer multiple is exactly
the right tool for them.

**I made the identical mistake in my own first measurement**, which is how I found it: pass 1
reported "17 refusals (4.4%)" and every single reason read *"Not DCF-valuable"* or *"the inputs
a DCF or a multiple would need are missing"* — on **NVS, SAP, SPOT, TD, SMFG, ING, SAN, NGG,
TRI, BN, NU**: banks, utilities and ADRs. Not one was a data problem. `publication_guard`
returns `decide(...).reason or None`, and `decide` returns an **empty** reason when there is no
value — so those strings came from `blended_fair_value`, never from the guard.

Demonstrated on three real names that today publish ordinary peer estimates, by running the old
expression as if they had ranked inside `dcf_top`:

| name | price | published today | under the OLD code |
|---|---|---|---|
| NVS | $153.67 | **$185.41** blended | **SUPPRESSED**, "Not DCF-valuable" |
| SAP | $189.65 | **$364.97** blended | **SUPPRESSED**, "Not DCF-valuable" |
| TD | $121.15 | **$79.73** blended | **SUPPRESSED**, "Not DCF-valuable" |

**And the affected population is unstable run to run.** The identical expression over the
identical 387 names counted **17** in one run and **77** in another about 2.5 hours later, with
the slower run showing more upstream throttling. So under load, *more* names get mislabelled as
refused — the failure gets worse exactly when the feed is worst.

**Fixed by asking for the VERDICT rather than the presence of a reason string:** call
`publication.decide` on the value the model actually held (`blend.withheld_value` before the
guard blanked it) and refuse only when it gives a reason. That reads the one decision instead of
restating its threshold, which is the rule `publication.py` exists to enforce. Pinned by
`test_not_dcf_valuable_is_not_a_refusal`.

### Do any other writers in this lane drop fields the same way?

Measured, not read off the source: every producer's row was pushed through its persister, read
back, and the key sets diffed.

| writer | dropped | live? |
|---|---|---|
| `save_snapshot` | *(the two refusal keys — fixed)* | **was live** |
| `save_intraday` | `fair_value`, **`fair_value_withheld`**, `name`, `sector` | **LATENT** — the intraday path never computes a fair value today, so nothing is being lost now. It would bite silently the day someone adds one. |
| `save_track_picks` | `price`, `fair_value` | No — that table is `(source, run_date, ticker, rank)` by design. |
| `archive_scan` (**edge lane, not mine**) | names 10 keys explicitly; stores `fair_value` but **not** the refusal flag or reason | A refused row archives as a bare `None`, so no number is published — but *why* it was blank is lost from the permanent record. Reported, not touched. |

**So yes: `save_intraday` has the same shape.** Same fixed column list, same silent discard,
same field name. It is one producer away from being the same bug.

### VERIFICATION — production, not the suite

The brief is right that a green suite is not evidence here, and the reason is worth restating:
**the catch-all walks ratios**, and a refused 11x model replaced by a 3.2x peer estimate sits
comfortably *under* the 5x band. No ratio test can see this class. It was built for the AEG case
(5.25x) and still guards that correctly.

**The verification I could do, and the one I could not:**

- **KSPI, STLA and CHTR are not in today's production list at all.** Today's scan served 399
  rows from an 800-name universe and none of the three is among them. **I could not verify the
  fix on the three original names, and I am not substituting different tickers and presenting
  them as the same evidence.** The three `/api/whatdo` responses carry no fair-value block for
  them either — the only `withheld` field in each is `options.withheld`, which is the options
  surface, not this one.
- **What I did instead:** reproduced and fixed the mechanism on the **real production rows
  themselves**, including the round trip through a real database, and on the names production is
  actually serving. That is stronger than three tickers and weaker than a live re-probe.
- **The live re-probe is not possible from here and must not be claimed.** Nothing is deployed
  until Don pushes, and the fix only reaches the public surface on the **next scheduled scan**,
  because the flag is written at scan time. **The honest status is: fixed and verified locally
  against real production data; unverified on the live site until the next scan runs.**

### The new test that would have caught this class

`test_a_recorded_refusal_survives_the_snapshot_round_trip` — and the point is *where* it runs.
`test_a_refused_row_is_not_re_estimated_from_peers` has been **green the entire time production
was leaking**, because it exercises the estimator **in memory** and the database sits between
the scan and the serve. The new test crosses the same boundary the decision does:
`record_refusal` → `save_snapshot` → `load_snapshot` → `estimate_fair_values`, asserting no
value is published and that an unrefused row carries neither key.

Two more: `test_snapshot_migration_adds_the_withheld_columns_and_reads_old_rows_as_not_withheld`
and `test_not_dcf_valuable_is_not_a_refusal`.

### Suites

**24 suites, 849 tests, 0 failures.** `test_screener.py` 78/78 (was 75, +3 here);
`test_withhold.py` 29/29; `test_public.py` 17/17; `test_private.py` 30/30; `test_saas.py` 30/30.
`test_guards.py` reads 35/36 and self-reports **"1 xfail, 0 xpass, 0 failed"** — the same
pre-existing expected-failure routed to the options-bot lane, unrelated to this change.

### What I did NOT do

- **Did not touch** `valuation/web/**`, `valuation/report/**`, `valuation/edge/**`,
  `.github/**`. The web guard already honours these keys; verified by running it, not modified.
- **Did not raise `dcf_top`.** It would change the published number on ~387 names, which is
  Don's call, not a bug fix's.
- **Did not write a cheap proxy for the refusal.** `publication.py` exists because this decision
  had five independent implementations; a sixth approximate copy in the screener would be the
  same bug wearing a performance argument.
- **Did not fix `save_intraday`** — same shape, no live instance, and it is a separate change.
- **Did not claim Bug B removed anything from today's list.** It removed nothing.

## BUGS FOUND

1. **`_enrich_with_dcf` conflated "not valuable" with "REFUSED", suppressing fair values on
   names nothing refused** — live, in this lane, introduced by the CONSOLIDATE-1 fix.
   Demonstrated on NVS ($185.41), SAP ($364.97) and TD ($79.73). The mislabelled population is
   **unstable run to run — 17 vs 77 of the same 387 names** — and grows when the upstream feed
   throttles. Fixed here.
2. **`save_intraday` drops `fair_value` and `fair_value_withheld`** — the same fixed-column-list
   shape as Bug A, in the same file. Latent only because the intraday path computes no fair
   value today. Not fixed (separate change, no live instance).
3. **`archive_scan` (edge lane) stores `fair_value` but not the refusal flag or reason**, so the
   permanent archive cannot distinguish "refused" from "not computed". No number is published,
   so this is a record-keeping loss rather than a leak. Not mine to fix.
4. **The free upstream feed is not stable run to run.** The same 387 names, the same code, two
   runs ~2.5h apart: the count of names the model could not value moved **17 → 77**, and a Yahoo
   `401 Invalid Crumb` appeared under concurrency. Anything that reasons about *which* names are
   valuable needs to treat that population as noisy, not fixed.
5. **The pre-2026-08-07 "17 refusals" figure in my own first measurement was wrong** for exactly
   the reason in item 1. Recorded because the number was real, plausible, and would have been
   quotable — and a project whose memory is its write-ups should keep the retraction next to the
   claim.
6. **`VALQUO_LEDGER.md` cannot hold out-of-band work and will silently DROP it.**
   `scripts/build_ledger.py` builds `rows` by iterating the 134 ids in
   `valquo_audit_items.json`; any row whose id is not among them is not carried across, so the
   `OOB1` row added for this item disappears the next time anyone regenerates. That matters
   more than it sounds: the ledger is the project's declared answer to "where do we stand", and
   the work most likely to be out-of-band is the work found by probing production — which is how
   this leak was found **both** times. Not fixed (that file is not in my lane), but whoever owns
   the generator should either preserve unknown-id rows or give out-of-band items real ids.

---

# Part 7 — The reproducibility fix: beta provenance, a real history check, stamped inputs

## PRE-COMMITMENT — written and committed BEFORE any outcome was measured

Committed on its own so its ordering is provable. Checked **first**, because committing to a
bound that turns out unmeasurable is the mistake this lane keeps being caught by:

**(i) Is a control group real?** Yes — see the table below. **(ii) Does the instrument
reproduce?** Yes, to 0.036 worst case against my own earlier column. Both were established
before any bound below was written.

### Facts established before the pre-commitment (not outcomes)

- **The vendor beta field is INTERMITTENT, not gone.** `HANDOFF_live_data_bugs.md` §6 recorded
  MRK's beta as *absent* on 2026-08-05, which is what dropped it to the 1.10 fallback and moved
  WACC 5.53% → 9.31%. **Today it is back at 0.211.** So the defect is a field that comes and
  goes, and any fix that waits for it to vanish again is untestable. **I will simulate its
  absence rather than wait.**
- **My earlier "1y-daily" instinct is wrong and I checked before building on it.** The estimator
  my handoff validated on controls is **5y-MONTHLY**. Re-run today, 1y-daily returns
  **KO −0.286 and XOM −0.484** — negative betas for Coca-Cola and Exxon. Had I not re-derived
  which window was validated, I would have shipped that.
- **The 5y-monthly estimator reproduces**, worst |Δ| **0.036** (JPM), most within 0.006:
  AAPL 1.070, JPM 1.013, NVDA 2.217, MRK 0.180, GILD 0.305, CI 0.288, CHTR 0.669, KSPI 0.886.
- **KSPI comes back with n = 30 monthly observations**, matching the "30 monthly observations,
  ADR listed 2024" already in the record. **Every other name tested has n = 59.** So a minimum
  of 36 separates KSPI from the field, and a naive `n >= 60` would flag literally everyone.
- **Cost: the extra 5y-monthly call is 0.14s per name**, and is paid only when the ladder
  actually needs it.

### The critical constraint my own evidence imposes on this task

**A low-side beta floor applied to the VALUE alone would assert something false.** §2 of this
handoff measured GILD (0.336), CI (0.321), CHTR (0.678), MRK (0.211) and XOM (0.173) as
**genuinely** low-beta. Only KSPI's 0.08 is an artifact, and what makes it an artifact is not
its size but **the 30 observations behind it**.

So the two halves the brief names are not independent, and I commit to wiring them that way:
**the low-side value only decides WHO GETS CHECKED; the observation count decides WHO GETS
REJECTED.** A long-history name is accepted no matter how low its beta. This makes the trigger
value a low-stakes choice, and I will demonstrate that by re-running the verdict at 0.10 / 0.15
/ 0.25 rather than asserting it.

### The design being committed to

Vendor-first ladder, each rung stamped:

1. explicit `beta_override` — unchanged, wins.
2. **vendor beta in (0, 3.0] and above the low trigger → ACCEPTED UNCHANGED**, no extra call.
3. otherwise corroborate with a 5y-monthly regression vs SPY:
   * observations ≥ **36** → accept the vendor if it is in range (low betas are real), else use
     the computed value;
   * observations < 36 → the vendor value is unsupportable; use the computed value if it has
     ≥ 24 of its own, else the stated constant.
4. **stated constant**, named with its derivation, marked `substituted`.

**The constant.** Today's is a bare `1.10` with no derivation anywhere in the repo. I commit to
naming it and stating that the market portfolio's beta is **1.0 by construction**, and to
**reporting how many names actually reach rung 4** — the point of the ladder is that a missing
vendor field now lands on a computed beta rather than a constant, so rung 4 should be nearly
empty. **I will only change the value from 1.10 to 1.0 if the measured number of names reaching
it is zero or its effect is fully enumerated name by name.** Changing a constant that silently
moves valuations is the thing being fixed, not a licence to do it once more.

### BOUNDS

**CONTROL GROUP: exists and is the large majority.** Verified before this was written — all 10
names in the feasibility sample carry a valid vendor beta. The control is every name whose
vendor beta is present, in (0, 3.0], and either above the trigger or corroborated by ≥ 36
observations.

**BOUND 1 (do-no-harm, the hard one): for every control-group name, WACC and fair value must be
BIT-IDENTICAL, not merely close.** This change adds a ladder in front of an input; for a name
whose input is unchanged, no arithmetic downstream may move at all. Any movement is a defect in
my change.

**BOUND 2 (the fix must actually fire): with the vendor beta simulated ABSENT, MRK must resolve
to a computed beta near 0.18, NOT to the constant** — i.e. the 3.78pp WACC swing that produced
the "91 Strong Buy" must not reproduce. Committed threshold: **MRK's WACC with the vendor field
absent must land within 0.50pp of its WACC with the field present.**

**BOUND 3: KSPI's beta must stop being 0.08**, and must be rejected *for its 30 observations*,
not for its size. If it is rejected by a value rule alone, that is a FAIL of this design even if
the number looks better.

**BOUND 4: no control-group name may move between published and withheld.**

### What I will report even if it is unflattering

- the count of names reaching each rung, including rung 4;
- every control-group name that moves at all, if any;
- whether the verdict survives the trigger at 0.10 / 0.15 / 0.25;
- if the fix turns out to be inert on today's data — as Bug B was — I will say that plainly
  rather than quote the mechanism as though it were an effect.

### What I will NOT do

- **Not floor beta on value alone.** My own measurement says that is false for four of five
  names, and the brief's own framing ("KSPI's 0.08 came from 30 monthly observations") is a
  history argument, not a size argument.
- **Not switch every name to a self-computed beta.** It would change every valuation in the
  product and leave no control group. Vendor-first is chosen partly *because* it leaves one.
- **Not retune a threshold after seeing which names it catches.**

---

## Part 7 — RESULTS: the beta reproducibility fix, measured

**Verdict: all four pre-registered bounds HELD, on the third attempt.** The first two attempts
were invalidated by my own measurement and are reported below rather than discarded, because the
way they failed is the most useful thing in this section.

Pre-commitment: commit `04d9f12`, written and committed alone before any number existed.

### 7.1 Two invalidated runs, and why they are in the record

| run | names | rate-limited corroborations | names arriving with NO vendor beta | reportable |
|---|---|---|---|---|
| 1 | 402 | 176 | not recorded | **NO** |
| 2 | 403 | 297 | 302 | **NO** |
| 3 | 46, paced, serial | **0** | 3 (genuine) | yes |

Run 1 made 402 corroborating calls in 3.7 minutes and exhausted Yahoo's rolling quota. Run 2 was
worse: **302 of 403 names arrived with `beta=None` and largely empty `CompanyData`**, so the base
fetch was degraded too — MRK, GILD, CHTR, CI, KO and XOM all reported WACC 5.26% identically,
which is the signature of a name with no market cap whose WACC collapses to pure cost of debt.

**Bounds 2 and 3 "passed" in run 1 for a worthless reason: both arms landed on the same constant,
so the swing was 0.00pp.** A bound satisfied because nothing happened is not satisfied. Run 2 was
built to detect exactly that and did — it labelled itself contaminated and refused to report.
Run 3 added a *continuous* check that stops the moment a rate limit appears, rather than
discovering it at the end.

**The lesson is not about Yahoo.** A measurement that consumes the resource it is measuring will
report on its own exhaustion and call it a result. The guard that caught this was cheap: count the
contaminating events, print them *before* the verdict, and make the script refuse.

### 7.2 The defect the invalidated runs exposed — the important finding

Run 1 pushed **178 of 402 names onto the constant**. Not because their history was thin, but
because the corroborating call *failed*, and the first version of `_resolve_beta` could not tell
those apart. That is the MRK bug reproduced with a new trigger — and a worse one, because
**production scans 500 names at a time, which is precisely the burst that provokes throttling.**
A fix for "a vendor field vanished" that itself turns a busy network into 178 changed valuations
is not a fix.

Corroboration is now **best-effort with a failure mode of "no change"**: a vendor beta is
overruled only by positive evidence that its history is short, never by a failed check. The
invariant, stated so it can be tested: **the constant's population is never wider than it was
before this change** — it is reached only when the vendor beta is missing or out of band, which is
exactly the old `1.10` test.

### 7.3 The four bounds, measured (46 names, paced, 0 contaminated)

Sample: the 7 named cases + 5 out-of-band names + every 12th served name — deterministic and
fixed before any result. It is **a sample, not the 403-name served universe**; that is the price
paid for validity, and it is stated rather than glossed.

**BOUND 1 — do-no-harm. HELD.** 37 control-group names; **0 moved** in WACC or fair value.

**BOUND 2 — the fix must fire. HELD, and non-vacuously.** With the vendor field simulated absent:

| name | vendor | computed (n) | WACC swing, NEW | WACC swing, OLD |
|---|---|---|---|---|
| **MRK** | 0.211 | **0.180** (59) | **0.13pp** | **3.85pp** |
| KSPI | 0.080 | 0.886 (30) | 0.00pp | 4.82pp |
| GILD | 0.336 | 0.305 (59) | 0.13pp | 3.32pp |
| CI | 0.321 | 0.288 (59) | 0.11pp | 2.74pp |
| CHTR | 0.678 | 0.669 (59) | 0.01pp | 0.37pp |
| XOM | 0.173 | 0.206 (59) | 0.15pp | 4.34pp |
| KO | 0.342 | 0.308 (59) | 0.15pp | 3.38pp |

MRK's **0.133pp** clears the pre-committed 0.50pp. The old code's **3.85pp** on the same name
independently reproduces the reported 5.53% → 9.31% incident — the bug report was accurate.

**BOUND 3 — KSPI. HELD.** Rejected at **n = 30 < 36** and replaced by its own computed 0.886.
It is rejected **for its history, not its size**, which was the condition that would otherwise
have made this a FAIL however good the number looked. Its fair value is `None` before and after —
the name is not published either way, so this is a correctness result, not a headline change.

**BOUND 4 — no published/withheld flips among control names. HELD.** 0 flips.

### 7.4 Rung counts, including rung 4 — enumerated as promised

`vendor` 34 · `vendor_corroborated` 3 · `computed` 4 · `fallback` 5 · `vendor_uncorroborated` 0.

**Five names reach the constant. The pre-commitment said the 1.10 → 1.0 change ships only if that
count is zero or its effect is enumerated name by name. Enumerated:**

| name | vendor | why the constant | WACC | fair value |
|---|---|---|---|---|
| PDD | −0.005 | own beta −0.039, out of band | 10.13% → 9.63% | 217.82 → 227.33 |
| ALAB | 3.843 | own beta 4.237, out of band | 10.16% → 9.66% | 56.80 → 59.73 |
| CRDO | 3.233 | own beta 3.412, out of band | 10.16% → 9.66% | 136.26 → 143.98 |
| BE | 3.832 | own beta 3.824, out of band | 10.40% → 9.92% | 25.65 → 26.48 |
| KXIAY | none | only 9 observations | 9.97% → 9.50% | 24.79 → 25.91 |

Every one of these already received a constant under the old code. The entire effect on them is
the **1.10 → 1.0 difference: WACC −0.5pp, fair value +4 to +5%.** Nothing here is a new
substitution; it is the same substitution with a derived value instead of an underived one.

### 7.5 Trigger sensitivity — pre-committed, and the answer is "none"

| `BETA_LOW_TRIGGER` | rungs | names resolving to a DIFFERENT beta vs 0.25 |
|---|---|---|
| 0.10 | vendor 37, computed 4, fallback 5 | **0** |
| 0.15 | vendor 37, computed 4, fallback 5 | **0** |
| 0.25 (shipped) | vendor 34, corroborated 3, computed 4, fallback 5 | — |

**The trigger changes no beta at all on this sample.** It moves three names between `vendor` and
`vendor_corroborated`, which is a difference in whether a network call happens and what the stamp
says — not in the answer. This is the design claim ("the value decides who gets *checked*; the
observation count decides who gets *rejected*") measured rather than asserted. KSPI's 0.080 sits
below all three triggers, so its rejection does not depend on the choice.

### 7.6 What actually changes in the product — including the part that flatters it

**9 of 46 names (19.6%) get a different beta; 4 get a genuinely new number.** The other five are
the 1.10 → 1.0 shift above.

| name | old | new | WACC | fair value |
|---|---|---|---|---|
| KSPI | 0.080 | 0.886 (n=30) | 5.07% → 8.88% | None → None |
| ARGX | 1.100 | 0.413 (n=59) | 10.16% → 6.73% | 1053.27 → **1929.80** |
| DTEGY | 1.100 | 0.323 (n=59) | 7.71% → 5.77% | 53.62 → **86.22** |
| COP | 1.100 | 0.216 (n=59) | 9.31% → 5.52% | 77.47 → **131.18** |

**STATE THIS PLAINLY: this is the first change in this lane that moves published fair values UP,
and systematically so.** Every name with no usable vendor beta was priced at a beta of 1.10;
measuring their own gives a lower number, a lower WACC and a higher fair value — ARGX +83%,
COP +69%, DTEGY +61%. The direction is not evidence the change is right. What supports it is that
1.10 was never derived from anything, and that COP's computed 0.216 sits alongside XOM's 0.206
from the same estimator — two large integrated energy names agreeing. **A follow-up should check
whether these names now clear publication thresholds they previously failed, because a
systematically upward revision is exactly the kind of change that quietly adds Buy ratings.**
That check is not in this session's bounds and is not claimed.

### 7.7 Limits that must travel with these numbers

- **46 names, not the 403 served.** Two full-universe attempts were invalidated; a third needs a
  rate-limit-tolerant path, which is the recommended next step.
- **Under a throttled vendor feed, both old and new land on a constant for names whose vendor beta
  is missing.** Fail-open protects a name that *has* a vendor beta; it cannot invent one. Run 2
  saw 302 such names. Unchanged behaviour, not a regression — but it means the reproducibility
  hole is **narrowed, not closed**, while the feed is Yahoo.
- The estimator is 5y-monthly against SPY. **1y-daily was tried first and is wrong** — it returns
  KO −0.286 and XOM −0.484.
- `BETA_HIGH_CAP` is inherited, not derived. CRDO's vendor (3.233) and own (3.412) values *agree*
  the beta exceeds it, which is arguably evidence the cap is too low rather than that the data is
  bad. Those names sit on the constant exactly as before, so nothing regresses — but pricing a
  genuinely 3.4-beta company at 1.0 understates its risk. **Moving the cap needs its own bound.**

### 7.8 Tests

`tests/test_engine.py` **51/51**; full sweep **24 suites, 859 tests, 0 failures** (re-run after
the final change). Eight new tests, none of which touch the network — they stub the estimator, so
a throttled machine cannot turn them green or red by accident.

The test that would have caught this class:
`test_a_throttled_corroboration_keeps_the_vendor_beta` — it asserts that a `YFRateLimitError`
leaves a published beta untouched. The original bug and my near-repeat of it are the same
sentence: *an input that could not be fetched must not silently become a different number.*

## BUGS FOUND

1. **`_resolve_beta` converted a rate limit into a changed headline (MINE, found and fixed before
   ship).** "History is thin" and "the check could not run" were the same branch. Measured: 178 of
   402 names pushed onto the constant. Fixed; two tests pin it.
2. **The plausibility band was applied to the vendor's beta but not to my own.** **PDD adopted a
   computed beta of −0.039** — a value the same function refuses from a vendor — pinning WACC to
   the 4% clamp and turning a $217.82 fair value into a refusal. CRDO (3.412), ALAB (4.237) and
   KXIAY (6.713, n=9) breached the high cap. Fixed: a number is not more believable because we
   computed it ourselves.
3. **`.gitignore`'s bare `data/` also matches `valuation/data/`, which is application source.**
   `valuation/data/beta.py` was silently unaddable, and since `wacc.py` imports it lazily it would
   have shipped as a runtime `ModuleNotFoundError` on the one path it was written for. The six
   older files in that package survive only because ignore rules do not apply to already-tracked
   files. Anchored to `/data/`; verified `data/backtest`, `data/raw`, `data/bulk` and
   `data/last_result.json` all remain ignored and no licensed file became visible.
4. **The risk-free rate has the same silent-substitution shape beta had.** `macro.py` falls back to
   `cfg.default_risk_free` and nothing downstream could distinguish a live rate from a config
   constant. Now stamped. **Not measured** — no incident is attributed to it, and none is claimed.
5. **A measurement that consumes the resource it measures will report its own exhaustion as a
   result.** Two runs here did. Neither was reportable, and only the second could tell.
