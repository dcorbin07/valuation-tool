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

---

# Part 8 — The reinvestment undercharge (the CHTR class defect). PRE-COMMITMENT

**Written and committed BEFORE any candidate was run or any after-number existed.** This is my own
Part 4 item 2, quantified and deliberately left unfixed then; it is the largest known defect in
the valuation engine.

## 8.0 Two exemplars in the brief have already moved — stated before anything else

Measured on the **same 2026-08-05 pickle Part 4 used**, so this is intervening *code*, not new
data:

- **CHTR's modelled year-1 reinvestment is no longer −$79M. It is +$1,056M**, against $2,948M of
  observed net capital spend — a shortfall of **3.5% of revenue, below the 5% flag**. Its FCFF
  runs **9,104 → 10,188 on 1.124× revenue**, i.e. **+11.9% FCFF on +12.4% revenue. It does not
  double.** CHTR is currently **withheld** (`fair_value None`).
- **CI does not publish +275% at HIGH confidence.** It is withheld, `fair_value None`, confidence
  low, and its net capex is **negative** (−1,563) — it is in the control group, not the treated
  one.

So the spec's CHTR-specific success criterion ("must no longer double FCF on 1.16× revenue") is
**already satisfied by the current code** and cannot be used to score a candidate. I am not
quietly dropping it — I am recording that it no longer discriminates, and scoring on the
population instead.

**The class defect is untouched and is the real target.** On the 241-name sweep: 205 non-financials
have capex and D&A; **114 have positive net capital spend; 33 are undercharged by more than 5% of
revenue and 21 by more than 10%** (worst: ORCL 57.3%, SRE 50.4%, D 46.7%, XEL 41.7%, APD 41.1%,
AWK 31.1%, GOOGL 22.9%), concentrated in **Utilities 11, Energy 8, Technology 4, Basic Materials
4**. **XOM (−17,131) and TTE (−12,778) are charged NEGATIVE reinvestment** while spending real
money — shrinking revenue is credited as releasing capital.

## 8.1 The control group — checked FIRST, and by its defining property

Part 4's bound 1 breached because I verified a *proxy* was non-empty instead of verifying the
change could not move it. Not repeating that.

Both candidates are gated on **`net_capex = capex − D&A > 0`**. A name failing that gate never
enters the changed code path, so it is bit-identical **by construction, not by tolerance**.
Census, measured before committing:

| group | n | can the fix touch it? |
|---|---|---|
| financials (out of scope) | 31 | no |
| non-financial, capex ≤ D&A | **91** | **no — gate not entered** |
| non-financial, capex or D&A missing | **5** | **no — gate not entered** |
| non-financial, net capex > 0 | 114 | yes |

**Control group = 96 names, and its defining property is the gate itself.** CI sits in it.

## 8.2 The decisive set, and the motivating name

**Decisive set = the 33 non-financial names undercharged by >5% of revenue.** CHTR motivated the
search and **is not in the set** — at 3.5% it falls below the threshold on its own, so the
exclusion the brief asks for is automatic rather than argued. CHTR is reported separately and
carries no verdict weight, exactly as KSPI was handled in Part 2.

## 8.3 The candidates, parameters fixed now

`nc = capex − D&A` from the latest observed year. **No smoothing is available** — `CompanyData`
carries `revenue_history`, `ebit_history`, `fcf_history` and `net_income_history` but **no capex
history** — so a lumpy capex year propagates. Stated as a limitation, not fixed here.

**ARM A — decaying floor, explicit years only.**
`reinvest_t = max(growth_t, w_t · nc · rev_t/rev_0)` with `w_t = (n−t)/(n−1)`, i.e. full charge in
year 1 fading linearly to zero in the final year. **Terminal value deliberately UNCHANGED.**

**ARM B — persistent floor, explicit years AND terminal.**
`reinvest_t = max(growth_t, nc · rev_t/rev_0)` (no decay), and the terminal charge becomes
`max(g/ROIC · nopat_next, nc · rev_term/rev_0)`.

**How each interacts with the terminal, which is the whole question.** The decisive set carries a
median terminal share above 80% of EV (CHTR 84.6%, SRE 82.4%, D 81.3%). **Arm A cannot fix more
than the explicit-forecast fraction of the problem — under a fifth of EV for these names — and it
is included precisely so that limit is measured rather than asserted.** Arm B is the only arm that
can reach the terminal.

## 8.4 What "fixed" means — thresholds committed now

- **F1 — flat-revenue names are charged what they spend.** For treated names whose forecast
  revenue is roughly flat (`|rev_last/rev_1 − 1| ≤ 5%`), modelled year-1 reinvestment must land
  **within ±25% of observed net capital spend**.
- **F2 — the population tail closes.** The count of names undercharged by >5% of revenue must fall
  from **33 to at most 5**.
- **F3 — nobody is paid to shrink.** The count of treated names with **negative** modelled
  reinvestment must fall to **0**.
- **F4 — the terminal is reached.** For the decisive set, terminal FCFF must fall by a median of
  at least **5%**. Arm A is expected to score ~0 here; that is the point of running it.

## 8.5 Harm bounds

- **H1 — the control group is BIT-IDENTICAL.** All 96 names: fair value, WACC, score, confidence
  and published flag unchanged to the last digit. Any movement is a defect in my change, not a
  tolerance to widen.
- **H2 — published/withheld flips are enumerated name by name** in the treated set, and must be
  zero in the control.
- **H3 — the direction must be DOWN.** This charges more, so fair values must fall. **If a
  candidate RAISES the decisive set's median fair value, that is a red flag to investigate, not a
  result to ship.**

## 8.6 Anti-tuning, and the expectation written down first

Parameters ship at the values in 8.3. **A candidate that fails at its stated value is REJECTED,
not retuned.** No threshold moves after seeing which names it catches.

**Expectation, recorded before measuring: Arm A largely fails F4 and F2 because 80%+ of these
names' value is terminal; Arm B bites hard and its risk is the opposite one — flooring at observed
net capex double-charges genuinely growing names whose capex IS growth capital (MSFT nc 77,414 vs
a growth charge of 28,506), which may collapse fair values far beyond the defect. 60/40 that Arm B
overshoots.** This project's directional calls have been wrong more often than right; the point of
writing it down is that it keeps being wrong.

---

## Part 8 — RESULTS. VERDICT: **BOTH ARMS REJECTED. Nothing behavioural ships.**

Pre-commitment `4f99d8f`, committed alone before any candidate ran. Measured on the 241-name
2026-08-05 pickle — **fully offline and deterministic**, one process, one beta memo, so the only
difference between arms is the floor mode. `REINVESTMENT_FLOOR_MODE` ships **`"off"`**.

### 8.7 The scorecard

| bound | Arm A (decay, explicit only) | Arm B (persistent, + terminal) |
|---|---|---|
| **H1** control bit-identical (116 names) | **HELD — 0 moved** | **HELD — 0 moved** |
| **F1** flat-revenue within ±25% of net capex | HELD 8/8 | HELD 8/8 |
| **F2** names undercharged >5% of revenue ≤ 5 | HELD — 33 → **0** | HELD — 33 → **0** |
| **F3** negative modelled reinvestment → 0 | HELD — **0** | HELD — **0** |
| **F4** decisive-set terminal value ≤ −5% | **VIOLATED — +0.0%** | HELD — −67.4% |
| **H2** publish/withhold flips, 0 in control | HELD — 0 anywhere | HELD — 0 anywhere |
| **H3** decisive-set median fair value falls | HELD — −5.1% | HELD — −10.5% |

**The control bound held perfectly for both arms — 116 names, zero movement, bit-identical.** The
gate *is* the control group, so this was true by construction and the measurement confirms the
construction. That is the one part of this task that worked exactly as designed.

### 8.8 Arm A — REJECTED, and it fails in the most dangerous way available

**Arm A passes F1, F2 and F3 and still fixes almost nothing.** Its terminal change is **+0.0%,
exactly**, because it cannot touch the terminal by construction — and the decisive-set names carry
80%+ of their EV there (CHTR 84.6%, SRE 82.4%, D 81.3%).

**Three of my four success criteria are YEAR-ONE statistics, and a terminal-blind fix passes all
three trivially.** F1, F2 and F3 all read year 1 only. Had I not written F4, Arm A would have
scored 3-for-3 on "fixed" while leaving four-fifths of the affected value untouched. **This is the
brief's own warning — "an undercharge fixed in years 1–10 but not in the terminal fixes a third of
the problem" — reproduced as a measurement.** Rejected at its stated value, not retuned.

### 8.9 Arm B — REJECTED, and my pre-commitment failed to catch it

**Arm B passes ALL SIX pre-registered bounds and is obviously unshippable.** Stating that plainly
because it is the most important methodological result here: **the rejection rests on a criterion
I did not pre-register.**

| harm, none of it covered by a bound | Arm A | Arm B |
|---|---|---|
| DCF pushed from positive to non-positive | 4 | **14** |
| **negative enterprise value** | 1 | **18** |
| **negative terminal value** | 0 | **16** |
| fair value moved UP | 4 | 9 |
| names whose fair value changed at all | 49/241 | 78/241 |

ORCL's enterprise value under Arm B is **−884,065**; XEL **−156,070**; SRE **−132,247**. A
negative enterprise value is not a conservative valuation, it is not a valuation. **My bounds
asked whether the number moved in the right direction and never asked whether it was still a
number.**

### 8.10 The finding that reframes the defect — and corrects my own Part 4 statistic

**The 33-name "decisive set" is two different populations, and only one of them has the defect.**

| | n | names |
|---|---|---|
| **flat revenue — must spend to stand still** | **14** | SRE, APD, GOOGL, EOG, BHP, E, PBR, AMZN, MPC, TTE, RIO, NUE, XOM, COP |
| **capex boom — the spend IS growth capital** | **19** | ORCL, D, XEL, AWK, WEC, PCG, WMB, MSFT, NVO, META, EQIX, SO, AEP, EXC, DUK, MU, TXN, EIX, CNI |

**ORCL is the clearest case: net capex is 68.8% of revenue while revenue grows 3.1× across the
forecast.** Treating that as a permanent maintenance requirement is why its EV goes to −884,065.
The model already prices that expansion through the revenue path; charging observed net capex on
top **double-counts it**. Same for MSFT (1.69× revenue), META (1.64×), MU (1.91×).

**So Part 4's headline — "34 names undercharged by more than 5% of revenue" — conflates two
things, and I wrote it. The honest count of names with a genuine flat-revenue undercharge is
about 14, not 34.** The correction matters because the larger number is what made this "the
largest known defect in the valuation engine."

**The mechanism is right exactly where the defect is real: F1 held 8 of 8** on flat-revenue names
under both arms. Neither pre-chosen candidate separates the two populations, and **that separation
is what a third candidate has to do** — either gate the floor on forecast revenue growth, or
decompose capex into maintenance and growth components rather than using the net figure whole.
**Not attempted here: choosing that gate after seeing which names it catches is precisely the
tuning the pre-commitment forbids.** It needs its own pre-registration.

**My recorded expectation was RIGHT on both counts** — Arm A fails on the terminal, Arm B
overshoots by double-charging growing names, called at 60/40 before measuring. One correct call
does not license reasoning instead of measuring.

### 8.11 A LIVE defect found on the way, independent of either arm

**Six names are published TODAY with a non-positive DCF**, because `blend._usable` returns `None`
for any per-share value ≤ 0, silently removing the DCF lens and renormalising the rest:

| name | DCF/share | published | lenses after the drop |
|---|---|---|---|
| INTC | −0.53 | **$34.54** | multiples 48%, growth 52% |
| F | −31.92 | **$60.25** | multiples 100% |
| BA | −24.97 | **$94.27** | multiples 53%, growth 47% |
| SRE | −2.69 | **$35.27** | multiples 100% |
| CCI | −15.01 | **$33.93** | multiples 100% |
| IRM | −35.10 | **$79.27** | multiples 100% |

All six carry `confidence: low`, but they are published. **This is why charging MORE reinvestment
moved fair values UP: GM 56.35 → 108.25 (+92%) as its DCF went 2.74 → −3.71, XEL 25.85 → 44.73
(+73%), EQIX +121%.** A company whose cash-flow model collapses becomes *more* attractive, because
the collapsing lens leaves the blend.

`_usable`'s reasoning — "a non-positive fair value means the lens doesn't apply to this company" —
is right for a lens that never applied and wrong for one that applied and then failed. Pinned by
`test_a_non_positive_dcf_is_dropped_from_the_blend` as a characterisation, **not fixed**: it
changes six published numbers and needs its own bound.

### 8.12 What ships, and what I did NOT do

**Ships:** `REINVESTMENT_FLOOR_MODE` (default `"off"`, no behaviour change), `_net_capex_floor`,
the two arms behind it, and 5 tests (engine 51 → 56; 24 suites, **872 passing, 0 failures**).
The untouched terminal branch keeps its original
`nopat*(1-r)` expression verbatim — rewriting it as `nopat - nopat*r` differs in the last ulp and
would have moved every control name for no reason.

- **Did not ship either arm.** Both rejected against thresholds fixed before measurement.
- **Did not retune.** No parameter moved after seeing which names it caught.
- **Did not invent a third arm and adopt it** — the growth/maintenance split is the right idea and
  choosing its gate on these results is the exact error the anti-tuning rule exists to prevent.
- **Did not fix the blend's negative-DCF drop** (six live names) — same reasoning Part 4 used for
  this defect itself.
- **Did not touch** `valuation/edge/**`, `valuation/web/**` or `valuation/saas/**`.
- **Did not narrow the pipeline's 5%-shortfall warning**, which we now know fires on 19
  capex-boom false positives out of 33 — narrowing it on this evidence is tuning.

**Limits.** One 2026-08-05 snapshot, 241 names. `CompanyData` has **no capex history**, so `nc` is
a single lumpy year — a real weakness for a maintenance estimate and unaddressed. Two exemplars in
the brief (CHTR, CI) had already moved before I started (§8.0).

## BUGS FOUND (Part 8)

1. **A non-positive DCF is silently dropped from the blend and RAISES the published number.**
   Six names live today (INTC, F, BA, SRE, CCI, IRM). Characterised and pinned, not fixed.
2. **My own success criteria were mostly year-one statistics.** F1, F2 and F3 all read year 1, and
   a fix that provably cannot touch the terminal passed all three. Only F4 discriminated. A
   success criterion that a known-inadequate candidate passes is not a success criterion.
3. **My pre-commitment never required the output to remain a valuation.** Arm B cleared all six
   bounds while producing 18 negative enterprise values and 16 negative terminal values. The
   rejection is correct and is *not* pre-registered — stated rather than smoothed over.
4. **Part 4's "34 names undercharged by >5% of revenue" conflates two populations** — 14 genuine
   flat-revenue cases and 19 capex-boom names whose spend is growth capital already priced through
   the revenue path. Mine, and it overstated the largest known defect in the engine.
5. **`CompanyData` carries no capex history** while carrying revenue, EBIT, FCF and net-income
   histories, so any maintenance-capex estimate rests on one lumpy year.

---

# Part 9 — TERMINAL-SHARE-AWARE CONFIDENCE (PRE-COMMITMENT)

**Written before any outcome was measured, and committed alone.** Status: OUT-OF-BAND, live
product. Owner: greeks agent (engine lane).

## 9.0 The complaint

The confidence label describes *where the data came from* and *which lens carried the blend*. It
never asks what the number is MADE OF. A DCF whose terminal value is 93% of enterprise value is a
statement about year 11-to-infinity wearing a ten-year model's clothes, and the engine will happily
stamp it "high".

Both rejected reinvestment arms mean the VALUE will not change. The LABEL can still be honest.

## 9.1 The one thing I checked before committing to anything

**A control group exists: 40 of 241 names have no DCF lens in the blend at all** (financials
valued on P/B-ROE, plus names whose DCF was dropped as non-positive). Terminal share does not
describe their published number and the change must be mechanically incapable of touching them.
Part 4's bound 1 was breached because the control was a proxy; Part 8's held because the gate WAS
the control. Here the gate is again the defining property — `dcf` absent from `blend.lenses`.

## 9.2 The band, argued from the distribution and NOT from CI

Measured first, on the 241-name 2026-08-05 snapshot, printing **only the input distribution** — no
ticker, no label, no upside, no score. Choosing a threshold after seeing which names it flags is
the tuning this document exists to prevent, so the step-1 harness (`tv_dist.py`) is written to make
that impossible rather than to make it unlikely.

Terminal share across the 201 DCF-participating names:

| p1 | p5 | p10 | p25 | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|
| 49.9% | 57.0% | 63.0% | 69.4% | **77.7%** | 83.7% | **87.4%** | 90.4% | 119.1% | 227.8% |

**A high terminal share is NORMAL and must not be treated as a defect.** A ten-year DCF on a mature
business at an ~8% discount rate mathematically puts two-thirds-plus of its value in the terminal;
the median here is 77.7%. A 70% threshold would flag 73% of the universe, and a label that fires on
three names in four carries no information. This is the single most important reason to argue the
band from the distribution instead of from intuition.

The histogram has a shoulder, and the bands sit on it:

```
  40- 50%    3        70- 80%   62
  50- 60%   10        80- 90%   69     <- bulk ends here
  60- 70%   42        90-100%    9     <- density collapses
                     >=100%      6     <- different object entirely
```

* **`TV_SHARE_MEDIUM = 0.90` — cap at "medium".** Just past p90 (87.4%); density falls 69 -> 9
  across the boundary. Economically: **under a tenth of the value comes from the decade we
  actually model** with company-specific inputs. Expected to bind on 15 of 201 (7.5%).
* **`TV_SHARE_LOW = 1.00` — cap at "low".** *This is not a calibrated number.* At 100% the
  terminal exceeds the whole enterprise value, so **PV(explicit forecast) is negative**: the
  modelled decade destroys value and the terminal pays for all of it plus the shortfall. A sign
  change needs no threshold argument, which makes it the sturdier of the two bands. Expected: 6.

I record the counterfactual explicitly, because CI is named in the brief at 93.5%: a band at
**95%** would catch 7 names and would NOT catch CI. I am choosing 90% on the p90-and-shoulder
argument above. If that argument does not persuade a reader, the honest response is that the band
is wrong, not that the result is.

## 9.3 What changes, and what may not

Labels only, applied AFTER every value is final:

* `blend.confidence` — the fair-value label.
* `score.confidence` — the label printed beside the recommendation.
* Both capped **monotonically downward**. The cap can never raise a label, so it cannot rescue
  anything, and a name already "low" is untouched.
* Applied whenever the DCF lens participates (`weight > 0`), without a weight threshold. That is
  the conservative choice and avoids a second free parameter; names carrying only a sliver of DCF
  are growth-led and already "low", which C7 tests rather than assumes.
* `blend.tv_share` and a note are stored so the reason is visible rather than mysterious.

## 9.4 Success criteria — what "fixed" means, with tolerances

* **C1 — VALUE BOUND. Every published fair value bit-identical, all 241 names, exact float
  equality (`==`, not a tolerance).** Zero value changes is the whole premise.
* **C2 — SCORE BOUND. Every composite score, recommendation and sub-score bit-identical.** Stops
  the label leaking into the number.
* **C3 — CONTROL BOUND. The 40 non-DCF names: confidence labels bit-identical, both fields.**
* **C4 — MONOTONE. No name's confidence rises, on either field.**
* **C5 — DO NO HARM. The 186 DCF-participating names below 90%: labels bit-identical.**
* **C6 — NOT INERT. At least one PUBLISHED name is re-labelled.** If zero move, the change is
  cosmetic and I report NULL and ship nothing — the Part 8 discipline.
* **C7 — the low-DCF-weight assumption in 9.3, stated as a bound instead of an argument: no name
  with `dcf_weight < 0.2` is moved down from "high"** (it should already be "low" via growth-led).

**C1, C2 and C3 must be mechanically impossible to breach, not merely observed to hold.** I have
been caught twice by bounds that could not fail. Verified before the run: the cap is a pure
function of `(existing_label, tv_share)` returning a string, invoked after `blend.value`,
`fv_scen` and `compute_score` are complete, and it writes only to two `confidence` attributes.
Measurement is confirmation, not the proof.

**Anti-tuning rule, unchanged from Parts 2 and 8: a band failing at its pre-chosen value is
REJECTED, not retuned.** CI motivated the brief and is therefore excluded from the argument for
the band, exactly as KSPI was in Part 2 and CHTR in Part 8.

## 9.5 Out of scope, stated in advance

`screener/fairvalue.py` computes its own `fair_value_confidence` — but that path blends multiples
and the growth lens only, has **no DCF and therefore no terminal value**, and is already capped at
"medium". Nothing to do there, and I will not invent a proxy for it.


# Part 9 — TERMINAL-SHARE-AWARE CONFIDENCE (RESULTS)

**VERDICT: ADOPTED. Labels only; every published number is bit-identical.** Measured offline on
the same 241-name 2026-08-05 pickle and disk beta memo as Part 8, one process, deterministic — so
"bit-identical" is exact float equality on identical inputs rather than a tolerance on a re-fetch.

## 9.6 The brief's exemplar does not reproduce — CI is already withheld

The brief opens with *"CI publishes +275% at HIGH confidence on a number that is 93.5% terminal
value."* Measured through current code on this snapshot:

**CI is WITHHELD. Its terminal share is 90.3%, not 93.5%, and both its labels already read
`low`.** It publishes no number and no upside. The publication guard and the Part 7 beta work
landed between the brief being written and this run; CHTR was stale in Part 8 for the same reason.
**Third stale exemplar in two parts** — check the named name before building to it.

The band still binds on CI (90.3% ≥ 90%), so it now carries the terminal note; its label cannot
move because it is already at the floor. **Had I tuned the band to catch CI, I would have achieved
nothing at all** — which is a cleaner argument for the pre-commitment than any I could have written
in advance.

**The class of problem is real regardless, and this is the finding that replaces the exemplar:
ten names published today with `score.confidence = "high"` on a DCF that is more than 90% terminal
value.** The worst is SNAP at **227.8%**.

## 9.7 All seven pre-registered criteria HELD

| | criterion | result |
|---|---|---|
| C1 | every fair value / range / upside bit-identical, 241 names | **HELD** |
| C2 | composite score, recommendation, sub-scores bit-identical | **HELD** |
| C3 | control: 40 names with no DCF lens, both labels identical | **HELD** |
| C4 | monotone — no confidence label rises | **HELD** |
| C5 | do no harm: 186 DCF names below 90%, labels identical | **HELD** |
| C6 | not inert: ≥1 published name re-labelled — **12** were | **HELD** |
| C7 | no `dcf_weight < 0.2` name demoted from "high" | **HELD** |

**The bands bound on exactly the counts predicted before the run: 9 in [90%, 100%) and 6 at
≥100%.** That is arithmetic from the step-1 distribution rather than a result, but it does confirm
the band was fixed before the outcome was seen.

**The ≥100% band is exactly the set with PV(explicit forecast) < 0** — checked as a set equality,
not asserted. That band is a sign change, not a calibration, which is why it needs no defending.

## 9.8 What moved

All 12 moved on `score.confidence`; 4 of those also moved on `blend.confidence`.

| ticker | terminal % | dcf wt | blend | score | upside | published |
|---|---|---|---|---|---|---|
| SNAP | **227.8%** | 0.36 | low | **high → low** | −31% | yes |
| WELL | 132.7% | 0.34 | medium → low | medium → low | −77% | yes |
| CPNG | 119.1% | 0.44 | medium → low | **high → low** | −16% | yes |
| SNOW | 104.0% | 0.23 | low | medium → low | −70% | yes |
| KHC | 102.2% | 0.43 | medium → low | **high → low** | −58% | yes |
| GM | 97.1% | 0.49 | medium | high → medium | −37% | yes |
| WMT | 94.5% | 0.53 | medium | high → medium | −40% | yes |
| KR | 94.1% | 0.50 | medium | high → medium | **+75%** | yes |
| SYY | 90.6% | 0.52 | medium | high → medium | **+22%** | yes |
| SLB | 90.4% | 0.60 | high → medium | high → medium | −14% | yes |
| HAL | 90.4% | 0.58 | medium | high → medium | **+7%** | yes |
| COST | 90.0% | 0.53 | medium | high → medium | −57% | yes |

Three more sit in a band and keep their label because they are already at or below the ceiling —
**CI, JD (101.7%, withheld) and PCG** — and now carry the note. The note tracks the fact, not the
label delta, so a name marked down for two reasons states both.

**Published-name confidence mix:**

| label | before | after |
|---|---|---|
| `score.confidence` | high **120** / med 66 / low 48 | high **110** / med 71 / low 53 |
| `blend.confidence` | high 96 / med 129 / low 9 | high 95 / med 127 / low 12 |

**The two labels were disagreeing, and the optimistic one was the one on the recommendation
card.** SNAP's fair-value label already said `low` while the score beside it said `high`; WELL,
KHC, CPNG and SNOW are the same shape. That is the substance of the complaint: `blend.confidence`
knows which lens carried the blend, `score.confidence` knows only DCF reliability and data
completeness, and neither knew what the number was made of.

**Only three of the twelve carry positive upside** — KR +75%, SYY +22%, HAL +7%. Those are the
ones where the label does work, because a buy recommendation is where confidence is read. The
other nine are already negative-upside names where the marking-down is cheap.

## 9.9 Why this is labels-only by construction, not by luck

`terminal_share_cap(confidence, tv_share) -> (label, note)` is a pure function of a string and a
number. It cannot see a company, a fair value or a score. It is invoked in `pipeline.py` **after**
`blend.value`, `fv_scen` and `compute_score` are all final, and writes only two `confidence`
attributes plus `blend.tv_share` and one note.

`test_the_cap_changes_labels_and_provably_not_values` runs the same company twice with the bands
at both extremes — cap nothing, then cap everything — and asserts the fair value, the range, the
composite, the recommendation and every sub-score are bit-identical while the labels differ. That
fails the day anyone routes confidence back into a number.

## 9.10 What I did NOT do

* **Did not touch `screener/fairvalue.py`.** Pre-registered as out of scope in 9.5: it blends
  multiples and the growth lens, has no DCF and therefore no terminal value, and already caps at
  "medium". Inventing a proxy there would be asserting something I have not measured.
* **Did not weight the cap by DCF share of the blend.** A name at 5% DCF weight and 95% terminal
  is barely a terminal-driven number; the unweighted rule is the conservative one and avoids a
  second free parameter. C7 held, so no low-weight name was demoted from "high" anyway.
* **Did not re-tune after seeing the outcome.** The bands are the pre-committed 0.90 and 1.00.
* **Did not fix the six non-positive-DCF names** carried over from Part 8's BUGS FOUND. SNAP at
  227.8% terminal and SNOW at 104% are adjacent to that defect — both have a positive DCF whose
  explicit decade is negative — but the fix is a different change with different bounds.
* **Did not change what is published or withheld.** C1 forbids it.

**Limits.** One 2026-08-05 snapshot of 241 names; the bands are floors for THIS universe and would
want re-measuring if the panel changed materially. Terminal share is read from the BASE scenario
only — the bear and bull DCFs have their own, unexamined. And the cap marks a valuation down
without saying whether the terminal assumption is *wrong*; a 95%-terminal DCF on a genuinely
stable compounder may be perfectly sound, and the label says "judge this on the terminal", not
"this is broken".

## BUGS FOUND (Part 9)

1. **`score.confidence` and `blend.confidence` disagreed on 5 of the 12 flagged names, and the
   more optimistic one is the one printed beside the recommendation.** SNAP read `low` on the
   fair value and `high` on the score simultaneously. Now capped together; the underlying
   divergence between the two definitions is untouched and is a real open item.
2. **A high terminal share is normal and the project had no number for it.** Median 77.7%, p90
   87.4% across 201 DCF-participating names. Any future "the terminal is doing all the work"
   claim needs that denominator, or it will fire on three names in four.
3. **The brief's exemplar was stale for the third time in two parts** (CHTR and CI in Part 8, CI
   again here). Named exemplars in prompts are written against a snapshot and rot within days.


---

# Part 10 — THE HEADLINE FLIP IS GATED ON THE CONTRACT, NOT ON A DAY COUNT (PRE-COMMITMENT)

**Committed BEFORE the change is written, in its own commit, and nothing below is edited
afterwards.** This part is not a measurement, so there is no threshold to pre-commit in the usual
sense — what is pre-committed instead is the **mechanism**, the **default**, and the list of
things that are **not allowed to move**. Those are the parts that could otherwise be chosen after
seeing what was convenient.

## 10.0 The defect, stated exactly

`valuation/screener/index_track.py:223-224`:

```python
out["thin"] = days < MIN_LIVE_DAYS
out["headline"] = "backtested" if out["thin"] else "live"
```

`MIN_LIVE_DAYS = 60`. On the 60th trading day of the forward track, three things happen at once,
with no approval step and nobody in the loop:

1. `headline` flips `"backtested"` → `"live"`;
2. `thin` flips `True` → `False`, which drops the **"too early to judge"** pill
   (`valuation/web/templates/index.html:114`, keyed on `hero.thin`);
3. `hero.may_lead` flips `False` → `True` (`valuation/web/hero.py:154`), which is the flag the
   surfaces read to decide whether the live number is allowed to lead the page.

The track's recorded inception is **2026-07-30** and it stood at 5 trading days when
`PAPER_TRACK_CONTRACT.md` was drafted, so this fires around **late October 2026** — at **13%
power**, against a test that on the contract's own arithmetic (§2) cannot detect an edge below
**+49pp/yr**. `MIN_LIVE_DAYS` was never pre-committed and does not derive from power.

**The contract says the public posture changes on the 6-month OPERATIONAL GATE** (§3, Option A:
"a test of whether the track is being recorded properly at all"), **not on a day count.** Today
the code and the contract disagree, and the code wins by default because it is the thing that
actually runs.

## 10.1 The mechanism — ONE, and which one

The instruction is explicit that there must not be two. **The authority is the contract's own
register (`PAPER_TRACK_CONTRACT.md` §5), read directly by `index_track`.** Not a constant in
`settings.py`, not an env var, not a store key.

**Why the register and not a code flag.** A code flag would be a *second* record of the same
fact: the register would say the gate passed and `settings.py` would say whatever it last said,
and the two could disagree with no way to tell which was right. Reading the register makes the
human record and the machine record **the same bytes**. It also means the gate cannot be flipped
by an edit that leaves no trace in the document Don signs.

**The known risk, stated in advance rather than discovered later.** This project has already been
bitten by parsing a markdown table: session 12's `research_log._parse` matched `\bFIXED\b` across
joined cells, and an unescaped `|` inside a cell shifted every column after it and understated
`N` by 4. Parsing prose to decide a public posture invites exactly that. Three mitigations, all
committed now:

* the parser reads **one canonical row form only**, and a row it does not recognise is not a
  pass;
* **every failure mode resolves to NOT PASSED** — file missing, unreadable, malformed, field
  absent, value unrecognised. The conservative error is a mature track still labelled
  "backtested"; the harmful error is the reverse, and it is unreachable by accident;
* the parse result is **published in the payload** (`gate` block: `passed`, `source`, `value`,
  `reason`) so a mis-parse is visible rather than silent.

**The canonical row, fixed here and quoted verbatim in the module docstring and the handoff:**

```
| Operational gate passed | YES — <date> |
```

Match is on the field cell `operational gate passed` (case- and whitespace-insensitive), and the
value cell must begin with `yes`, `passed` or `true`. `pending`, `no`, blank, or an absent row
are all NOT PASSED. **The edge lane sets exactly this row on gate day; nothing else, nowhere
else.**

## 10.2 What the change is allowed to touch

**Labels only.** The permitted writes are exactly:

* `out["headline"]` — `"backtested"` / `"live"`
* `out["thin"]` — the pill and `may_lead`
* `out["note"]` — the sentence explaining which one is in force
* `out["gate"]` — a NEW block, additive, describing the parse

**Bounds — the change is WRONG if any of these move:**

| | bound |
|---|---|
| B1 | every number in the `live` block is bit-identical for a given input series — `days`, `since`, `as_of`, `cum_valquo_pct`, `cum_spy_pct`, `excess_pp`, `ann_alpha`, `sharpe`, `hit_rate` |
| B2 | the `backtested` block is bit-identical |
| B3 | `series`, `available`, `days`, `inception`, `benchmark`, `config`, `min_live_days` unchanged |
| B4 | **no tracked file under `data_export/` changes** — not one byte |
| B5 | with the gate NOT passed, `headline` is `"backtested"` at **every** day count, 0 to ∞ |
| B6 | with the gate passed, the day-count floor still applies — the gate is an **additional** condition, never a replacement, so a 3-day track cannot lead just because the gate passed |
| B7 | the default on a repo with today's unsigned contract is NOT PASSED |

**B5 and B6 together are the substance:** the flip requires **both** the gate and the days. A
gate-passed flag that let a 3-day track lead would be a worse bug than the one being fixed.

## 10.3 What I will NOT do, decided now

* **Not change `MIN_LIVE_DAYS` from 60.** It is the wrong number — the contract's §2 shows 60 days
  has 10-13% power — but it now only gates *annualisation*, which is a published figure, and
  moving it would change a number rather than a label. Recorded as a bug, not fixed here.
* **Not change `ann_alpha` / `sharpe` suppression.** Same reason: those are values.
* **Not touch `valuation/web/**`** (another lane) — the fix is in the producer, so every consumer
  inherits it unchanged.
* **Not touch `paper_track.MIN_DAYS_FOR_MEANING = 126`** — it is in the edge lane's
  `valuation/edge/paper_track.py`, and it governs a *different* track.
* **Not sign, choose, date or re-threshold the contract.** My only edit to it is to add the
  register row above with the value `pending`, plus one sentence saying the row is machine-read.
  No option, no date, no threshold.

## 10.4 The test the instruction asks for

`test_day_count_alone_can_never_flip_the_headline` — runs a series **far past** `MIN_LIVE_DAYS`
with no gate and asserts `headline == "backtested"`, `thin is True`; then the same series with the
gate passed and asserts it flips. It fails if anyone restores the day-count-only rule, and it
fails if the gate becomes a *replacement* for the day count rather than an addition.



---

# Part 10 — RESULTS: THE HEADLINE FLIP IS NOW A DECISION, NOT A DATE

**VERDICT: SHIPPED. Labels only; every number in the payload is bit-identical, and no tracked
data file changed.** The pre-commitment above was committed alone at `4f2d61f`, before a line of
code, and nothing in it was edited afterwards.

## 10.5 What was actually going to happen

`index_track.summarize()` decided the site's public posture with one comparison, `days <
MIN_LIVE_DAYS`, and `MIN_LIVE_DAYS = 60`. Measured, not asserted — the day-count-only rule
against the rule now shipped:

| trading days | BEFORE: headline / thin | AFTER, gate not passed | AFTER, gate passed |
|---|---|---|---|
| 1 | backtested / thin | backtested / thin | backtested / thin |
| 20 | backtested / thin | backtested / thin | backtested / thin |
| 59 | backtested / thin | backtested / thin | backtested / thin |
| **60** | **live / NOT thin** | **backtested / thin** | live / NOT thin |
| 61 | live / NOT thin | backtested / thin | live / NOT thin |
| 90 | live / NOT thin | backtested / thin | live / NOT thin |
| 300 | live / NOT thin | backtested / thin | live / NOT thin |
| 2000 | live / NOT thin | backtested / thin | live / NOT thin |

**Three things flipped together on day 60 and none of them had an approval step:** `headline`
`"backtested"` → `"live"`; the **"too early to judge"** pill went down
(`templates/index.html:114`, keyed on `hero.thin`); and `hero.may_lead` went true
(`hero.py:154`), which is the flag deciding whether the live number may lead the page.

On the recorded inception of **2026-07-30** that lands in **late October 2026**, at a horizon the
contract's own §2 puts at **13% power**, unable to detect an edge below **+49pp/yr**. The site
would have started leading with a number that, on the project's own arithmetic, cannot mean
anything yet.

**Measured on the contract exactly as it stands on `main` today:**

```
row value : 'pending'
passed    : False
day 60    -> headline='backtested'  thin=True
note      : Live track is 60 trading days old, past the 60-day floor, but the paper-track
            contract's operational gate has not been recorded as passed, so the backtest stays
            the headline. Elapsed time alone does not promote a live number.
```

## 10.6 The mechanism, and why there is exactly one

**The contract's own register is the authority** (`PAPER_TRACK_CONTRACT.md` §5), read on every
request by `index_track.gate_state()`. No constant in `settings.py`, no env var, no store key.

The instruction was not to invent two mechanisms, and the reason is sharper than tidiness: a code
flag would be a **second record of the same fact**, free to disagree with the document Don signs,
with no way to tell which was right. Reading the register makes the human record and the machine
record the same bytes. It also means the posture cannot be changed by an edit that leaves no
trace in the contract.

One row, and the edge lane sets it on gate day and nothing else, anywhere:

```
| Operational gate passed | YES - 2027-01-30 |
```

I added that row to §5 with the value `pending`, plus a note above it saying the running site
reads it. **I did not sign, choose, date or re-threshold anything** — no option letter, no
horizon, no statistic.

**Fail-closed, exhaustively, and each case is a test:** missing file, missing row, `pending`,
`no`, blank, a bare date, a wrong field name, a malformed row, the row **inside a fenced code
block**, and **two rows that disagree** — all resolve to NOT PASSED. The conservative error is a
mature track still labelled "backtested"; the harmful error is a thin track labelled "live", and
no accident reaches it.

## 10.7 The parser hole my own test found, and the rule I tightened

The pre-commitment said the value "must **begin with** `yes`, `passed` or `true`". Implemented
literally — leading run of letters — and `test_every_unusable_contract_resolves_to_not_passed`
immediately failed on the case I had put in it as a formality:

> **`| Operational gate passed | yes-ish, mostly |` was read as a PASS.**

That is precisely the failure this project has already paid for once, in
`research_log._parse`: prose read as a verdict. **The rule is now the first WHOLE WORD**, so
`yes-ish` is not `yes`, while dashes still separate (`YES - 2027-01-30` parses) because hyphens
do not.

**This is TIGHTER than what I pre-committed, and that direction is the reason it is allowed.**
Tightening can only make the gate harder to pass, so it cannot reach the harmful error;
loosening after seeing a result would be the move that needs defending. Recorded rather than
quietly folded in.

## 10.8 All seven bounds HELD

| | bound | result |
|---|---|---|
| B1 | every `live` number bit-identical, gate off vs on | **HELD** — `days`, `since`, `as_of`, `cum_valquo_pct`, `cum_spy_pct`, `excess_pp`, `ann_alpha`, `sharpe`, `hit_rate` all `==` |
| B2 | `backtested` block bit-identical | **HELD** |
| B3 | `series` / `available` / `days` / `min_live_days` / `config` / `benchmark` / `inception` unchanged | **HELD** |
| B4 | no tracked file under `data_export/` changes | **HELD** — three files touched, none of them data |
| B5 | gate not passed ⇒ `"backtested"` at every day count | **HELD** — checked to 2000 days |
| B6 | gate passed ⇒ the day-count floor still applies | **HELD** — 1, 5, 20 and 59 days all stay backtested with the gate open |
| B7 | today's unsigned contract defaults to NOT PASSED | **HELD** — reads `'pending'` |

**B6 is the one worth naming.** A gate-passed flag that let a three-day track lead would be a
worse bug than the one being fixed, and it is the obvious way to get this wrong. The gate is an
**additional** condition; it never replaces the day count.

## 10.9 The test the instruction asked for

`test_day_count_alone_can_never_flip_the_headline` runs 60, 61, 300 and 2000 days with no
contract and asserts `headline == "backtested"` and `thin is True` at every one — then runs the
same series with the gate passed and asserts it flips, so the first half cannot pass vacuously.
It fails if anyone restores the day-count-only rule at any horizon.

**One existing test was pinning the defect and had to be amended, which is stated rather than
buried.** `test_live_track_never_annualizes_a_stub_or_leads_with_it` asserted
`long["headline"] == "live"` at `MIN_LIVE_DAYS + 5`. The claim it still owns — that annualisation
switches on past the floor — is a *value* and is unchanged; the amendment is recorded inline in
the test with the old line quoted.

Five new tests, `83/83` in `tests/test_screener.py`, and the full gate is green.

## 10.10 What I did NOT do

* **Did not change `MIN_LIVE_DAYS` from 60.** It is the wrong number — §2 of the contract puts
  60 days at 10-13% power — but it now gates only *annualisation*, which is a published figure.
  Moving it changes a number, not a label. **Recorded as a bug below, not fixed.**
* **Did not touch `valuation/web/**`.** The fix is in the producer, so `app.py`, `hero.py` and
  `showcase.py` inherit it with no edit.
* **Did not touch `paper_track.MIN_DAYS_FOR_MEANING = 126`** — edge lane, and it opens a second
  door that is reported below rather than fixed from here.
* **Did not sign or alter the contract's terms.** One register row and one explanatory note.
* **Did not correct §6.4's file:line error** in another lane's document — reported below.

**Limits.** The gate is a *recorded human judgement*, not a measurement: nothing here checks that
the gate's actual criteria (daily rows with no gaps, turnover as modelled, realised costs near
33.4 bps) were met. If someone writes `YES` without doing the work, the site believes them. That
is the correct division — the contract makes the gate a judgement — but it should not be mistaken
for verification.

## BUGS FOUND (Part 10)

1. **THERE IS A SECOND, UNGATED DOOR TO THE SAME FLIP, and this change does not close it.**
   `hero.py:75-92` falls back to `paper_track.index_summary()` whenever the Cowork tracker has
   no live data, and takes `thin` from that payload's `meaningful` flag —
   `len(rows) >= MIN_DAYS_FOR_MEANING` (`paper_track.py:799`, 126 days). That path never
   consults the contract, so with the Cowork file absent and the sandbox book running,
   `hero.may_lead` can still flip on a day count alone, ~126 days in. **Fix is one line in the
   edge lane** — have `index_summary` (and `options_summary`) gate `meaningful` on
   `index_track.gate_state()["passed"]`, the same single authority, rather than adding a second
   flag. **Edge lane + web lane; assigned to neither so far.**
2. **`MIN_LIVE_DAYS = 60` still annualises a 60-day stub**, which is what the module's own rule 2
   forbids in spirit — compounding ~3 months of drift by 4.2x. The contract's §2 arithmetic says
   the number is meaningless at that horizon. Left alone deliberately because it is a value, not
   a label, and the instruction was labels-only. Wants its own pre-committed change.
3. **`PAPER_TRACK_CONTRACT.md` §6.4 and `CLAUDE.md` both put `paper_track.MIN_DAYS_FOR_MEANING`
   in `valuation/screener/index_track.py`. It is in `valuation/edge/paper_track.py:70`.** Both
   documents say "both live in index_track.py", and only one of the two constants does. Not
   corrected here — they belong to other lanes — but it matters, because the sentence is the one
   assigning the work, and half of it points at the wrong lane. That half is bug 1.
4. **The brief describes the contract as "now being committed as Option E".** The contract on
   `main` as merged offers **A, B and C only**, and its register reads `pending` throughout —
   nothing is signed. The gate row defaults to not-passed regardless of which option lands, so
   this is a coordination note, not a blocker: **whoever commits Option E should set the
   `Operational gate passed` row's value at the same time, or leave it `pending`.**

---

# Part 11 — V2, THE LIVE THEME-HEALTH METER (2026-08-09)

**Item:** `VALQUO_EXTENSIONS.md` **V2** — greeks lane, NEW FILES ONLY plus read-only imports.
**Pre-registration:** `PREREG_v2_theme_health.md`, committed **alone** at `25ba793` before
`scripts/theme_health.py` existed.
**Ships:** `scripts/theme_health.py`, `tests/test_theme_health.py` (23 tests),
`data/free_analysis/THEME_HEALTH.json` + two calibration artifacts.
**Reproduce:** `python -m scripts.theme_health --json data/free_analysis/THEME_HEALTH.json`
and `python -m scripts.theme_health --calibrate`.

**VERDICT: BUILT AND VALIDATED; NOT-QUOTABLE ON ALL TEN THEMES, ON ZERO USABLE ROWS.** The
refusal is the product today. The result worth acting on is not the refusal — it is the
calibration, which says the meter's usefulness is decided almost entirely by **which source
feeds it**, and the source it needs is the one nobody is currently preserving.

---

## 11.1 The pre-commitment, and why it is unusually easy to believe

Everything V2 requires to be fixed before the first computation was fixed at `25ba793`:
63-trading-day horizon; the IC is the panel's own `_spearman` **imported read-only**, not
re-implemented; monthly cadence with the 3:1 window overlap **priced into the band rather than
dropped**; a Robbins anytime-valid confidence sequence via `track_meter.boundary`, also imported
read-only, at `sigma = sqrt(3)`, `rho = 3`, and `alpha = 0.05` **family-wise across the ten
themes** (0.005 each); seven refusal floors; and the DEGRADED / CONFIRMED-LIVE / INSUFFICIENT /
NO-REFERENCE / NOT-QUOTABLE verdict table.

**At that commit the live record held ZERO closed 63-day windows.** There was no live number to
tune a threshold against, *even in principle* — which is the strongest form the pre-registration
argument takes, and the same one `track_meter.py` makes about its own frozen parameters.

Three things were measured before the file was written, all required by V2 to come first and
none of them an IC: **how many snapshot dates exist, each theme's non-null fraction, and which
provider wrote each file.** The third turned out to matter more than the first two.

**Two imports, deliberately, and they are the point of "read-only on `valuation/edge/**`".** The
correlation is the panel's `_spearman` and the band is the contract meter's `boundary`.
Re-implementing either would give the project a second definition free to drift from the first —
the defect class it has already paid for more than once.

## 11.2 What the record actually holds: nothing usable

| source | dates | usable | what is there |
|---|---|---|---|
| `data/archive/scans/` | **7** | **0** | every file is provider `"synthetic (offline test)"`, tickers `SYN0802`, `SYN0309` |
| `data/screener.db` `snapshot_rows` | **1** | **0** | one row dated **2099-01-01**, left by `tests/test_saas.py:200` |

**Total usable rows: 0.** Depth per theme: 0 non-null everywhere. Closed 63-day windows: 0.
Verdict on all ten themes: **NOT-QUOTABLE**, each carrying its own blocking reasons.

This is the same shape as roadmap #12's finding — a mechanism that is fully built and tested
while its tables hold zero rows — and V2's premise inherits half of it. V2 says the per-name
snapshots are "in the screener store since task #97". **The schema is; the data is not, on this
machine.** The real record accrues in the web service's database on Render's persistent disk:
`auto-scan.yml`'s `hot` job scans on a GitHub runner and POSTs to the site's ingest endpoint, so
the local store never receives it. **Nothing is broken — but nobody can run V2 against real data
from a checkout, and that was not previously written down anywhere.**

## 11.3 The estimator is proved anyway, because the live data cannot prove it

Zero closed windows means the live record exercises the *refusal* and nothing else. That is
exactly the situation in which a project ships a meter that has never computed anything and
finds out in nine months that it computes the wrong thing. So the estimator is validated
against panels with a **known planted IC**:

| planted Pearson | theoretical Spearman | **recovered median IC** | other nine themes |
|---|---|---|---|
| +0.5 | +0.4826 | **+0.4712** | max abs 0.0969 |
| 0.0 | 0.0000 | **−0.0714** | max abs 0.0969 |

10 monthly observations, 60 names. The +0.5 arm also **crosses UP and is labelled
CONFIRMED-LIVE**; the −0.5 arm **crosses DOWN and is labelled DEGRADED**; and **8 noise panels ×
10 themes = 80 theme-runs produced 0 crossings.**

**THE CONTROL CAUGHT A DEFECT IN ITSELF FIRST, AND THAT IS THE MOST INSTRUCTIVE THING HERE.**
The first version of the planted panel drew a score and then wrote the price that satisfied it.
With 63-day windows starting on every trading day, one date's **entry** price is an earlier
date's **mark** price, so every realised return carried an independent second term and the
recovered IC came back **+0.3575 against an expected +0.4826**. The arithmetic of that mistake
predicts attenuation by `1/sqrt(2)` → **0.341**, which matches. **A 26% attenuation looks exactly
like a broken estimator**, and would have been read as one had the expected value not been
written down first. The panel now draws a genuine multiplicative price path and derives the score
from the realised return, so the pair is bivariate normal by construction.

## 11.4 THE FINDING: the source decides whether this meter can ever return a verdict

Measured with `--calibrate` (20,000 Monte Carlo paths carrying the overlap structure the band
assumes: `z_i` an equally weighted moving average of 3 innovations, lag-1 and lag-2
autocorrelations of exactly 2/3 and 1/3), against **the backtest's own theme ICs**:

| | 100 names (the archive's top-100 book) | 800 names (the store's full universe) |
|---|---|---|
| detectable mean IC by 24m | +0.1348 | **+0.0475** |
| detectable mean IC by 60m | +0.0851 | **+0.0299** |
| power at `quality`'s +0.0356, 60m | **2.5%** | **80.3%** |
| power at `quality`'s +0.0356, 120m | 9.6% | 99.6% |
| power at `capital_discipline`'s +0.0297, 60m | 1.5% | **55.0%** |
| false crossing under the null, by 60m | 0.0010 | 0.0010 (nominal 0.005 — conservative) |

**On the top-100 archive this meter is very nearly powerless at the effect sizes the backtest
claims — 2.5% at five years, the same arithmetic that gives the forward paper track 13%. On the
full-universe store it reaches 80% at five years and is a real test.** Same band, same horizon,
same alpha; only the cross-section changes. The archive is doubly wrong for the purpose, because
its top 100 are *selected on the composite*, which range-restricts the very scores whose
correlation is being measured.

**CONSEQUENCE, and it is the actionable one: the full-universe snapshot history is the asset,
and it exists only on Render's disk.** If that disk is lost or reset, V2 does not lose months of
progress — it loses the only source that can ever answer its question. The report now prints the
typical cross-section and the IC detectable from it on every run, so nobody can read a verdict
without seeing which regime produced it.

**Timeline, stated plainly:** the first 63-day window cannot close for ~3 months after real
capture begins, the pre-registered floor is 6 closed monthly windows after that, so **the
earliest possible first reading is ~9 months from the day full-universe snapshots start being
retained**, and the first reading with real power is **~5 years**. The pre-registered expectation
(NOT-QUOTABLE on every theme, 95%) is **CONFIRMED**; the second, weaker one (INSUFFICIENT
everywhere once quotable, 60/40) is untestable for years and stays on the record.

## 11.5 One tightening, recorded

`EXCLUDE_FUTURE_DATED` — rows dated after today are dropped — is **stricter than the
pre-registration**, which did not mention them. It is recorded rather than quietly applied.
Justification is the standing one: excluding more data can only delay a verdict, while the
harmful error here is quoting an IC that is not supported. It is not hypothetical — before this
guard the 2099-01-01 fixture row became the meter's `as_of` and dragged the entire report into
the year 2099.

## 11.6 What I did NOT do

* **Did not hit production.** The real snapshot history is behind the site's admin endpoints and
  `ADMIN_TOKEN`; reading it is an owner action, not something to do from an agent session with a
  secret out of `.env`. `--db` / `--archive` take a path, so pointing the script at a downloaded
  copy is one flag.
* **Did not add a scheduled job.** V2 asks for the script and the surface data, not a cron. What
  it needs is a decision about retaining full-universe snapshots (§11.4), which is not mine.
* **Did not touch `valuation/edge/**`, `valuation/web/**` or any tracked data file.** Two
  read-only imports, two new files, plus register/ledger/handoff rows.
* **Did not surface anything publicly.** Owner-side Edge Lab instrumentation, per V2.
* **Did not fix the `tests/test_saas.py` leak** (§ BUGS FOUND, item 1) — it is another lane's
  file and the meter now defends against it.

---

## BUGS FOUND (Part 11)

1. **A TEST WRITES INTO THE REAL LOCAL DATABASE, AND ITS ROW IS DATED 2099-01-01.**
   `tests/test_saas.py:200` POSTs `{"scan_date": "2099-01-01", ...}` to
   `/admin/ingest-snapshot`, and the app writes it to `data/screener.db` — where it is sitting
   now, as the store's *only* `snapshot_rows` row. Any consumer that takes "the latest scan" as
   `MAX(scan_date)` gets a row from the year 2099. `store.latest_scan_date()` orders by
   `scan_date DESC`, so **`load_snapshot()` with no argument returns the fixture** on a machine
   that has ever run that suite. Not fixed (another lane's file, and the correct fix is a
   temp-directory database for the app tests, not a different sentinel date). The meter excludes
   future-dated rows and reports the count.

2. **`VALQUO_EXTENSIONS.md` V2's stated data source is half true, and the half that is false is
   the one an executor depends on.** "the persisted per-name snapshots (in the screener store
   since task #97)" — the schema and the writer exist (`screen.py:66` persists all ten themes
   into `extra["factors"]`), but the store a checkout can reach has never received a real scan,
   because `auto-scan.yml` runs the scan on a GitHub runner and POSTs the result to the live
   site. There is also **no task #97** in `VALQUO_LEDGER.md` or `valquo_audit_items.json` (both
   are letter-prefixed; index 97 is `O25`, "Sell the wing after the move"), so the citation
   cannot be followed. Recorded, not edited — the register belongs to whoever wrote it.

3. **The scan archive's `top=100` makes it unusable for theme health, and nothing says so.**
   `archive.py:84` keeps the top 100 names "because the tail of a 3,000-name scan is noise for
   this purpose" — true for its stated purpose, false for this one. Measured in §11.4: a
   100-name cross-section gives 2.5% power at 60 months against `quality`'s own backtested IC,
   versus 80.3% at 800. A future lane that reaches for the archive as the convenient
   survivorship-free source will build something that cannot work, and the docstring reads as
   an invitation.

4. **`insider` and `sentiment` can never receive a directional verdict from this meter, for two
   different reasons, and both are properties of the backtest rather than of the live data.**
   `insider`'s backtest median IC is −0.0052, inside the pre-committed `REF_MIN_IC` of 0.01, so
   there is no sign to be degraded relative to; `sentiment` is empty in the panel entirely
   (`coverage 0.0`, `median_ic null`). Both correctly return NO-REFERENCE / NOT-QUOTABLE rather
   than a fabricated direction. Worth knowing before someone asks why 2 of 10 themes never
   report.

---

## Part 12 — THE RATE-LIMIT-TOLERANT PATH: 46 of 403 -> 500 of 500, AND WHAT FULL BREADTH REVEALED (2026-08-10, greeks lane)

Pre-registration committed **alone at `1867a3f`**, before `scripts/live_cache.py` existed and
before any coverage number was measured: `PREREG_v2f_live_coverage.md`. Ledger row `V2F`.

### 12.1 The brief's premise was half false, and the pre-registration says so before the numbers

The brief reads *"the theme-health meter and beta source cover 46 of 403 served names because two
full-universe attempts died on vendor rate limits."* **True of the beta source, false of the
theme-health meter, and the two failures have nothing in common.**

| | covered before | why |
|---|---|---|
| beta source | **46 of 403** | genuine rate limits — runs 1 and 2 died at 176 and 297 throttled calls (Part 7.1) |
| theme-health meter | **0 of 403** | **not rate limits.** It reads the screener snapshot store, which in a checkout holds one synthetic 2099-01-01 fixture row (Part 11) |

Both are now answered, separately. **They must never be quoted as one number.**

### 12.2 What shipped

`scripts/live_cache.py` + `tests/test_live_cache.py` (**40 tests, no network in any of them**).
Four modes: `capture` pins the served universe, `fetch` pulls, `seed` replays captures into a
store, `report` measures offline.

**The design point is that the fetch and the measurement are now separate programs.** Part 7.1's
lesson was *a measurement that consumes the resource it is measuring will report on its own
exhaustion and call it a result* — and the reason it kept happening is that `_resolve_beta`
itself makes the network call (`wacc.py:166`), so measuring coverage burned the quota that
coverage depended on. Now `fetch` is the only phase that touches the network, and `report` makes
**zero** calls: it primes the estimator's own market cache and injects cached closes into the
**real** `compute_beta`, so the arithmetic executed is the shipped arithmetic. `report` is
therefore deterministic and re-runnable, and cannot be contaminated by the conditions it reports.

**Nothing under `valuation/` was edited** — not `wacc.py`, not `beta.py`. The ladder and the
estimator are imported and driven, never reimplemented.

### 12.3 The result: 0 throttle events, on the run that previously could not finish

| run | names | throttle events | outcome |
|---|---|---|---|
| 1 (Part 7.1) | 402 | 176 | invalidated |
| 2 (Part 7.1) | 403 | 297 | invalidated — 302 names arrived with `beta=None` |
| 3 (Part 7.3) | 46, paced serial | 0 | reportable, but a sample |
| **4 (this run)** | **500** | **0** | **reportable, full universe** |

**Beta-ladder coverage 46/403 (11.4%) -> 500/500 (100.0%).** B3's >=95% bar is cleared, so the
phrase "full universe" is permitted here.

**What made it affordable was BATCHING, not patience.** `yf.download` fetches many tickers in one
request: **500 monthly close series arrived in 13 requests in ~40 seconds.** Only the vendor
`beta` field cannot be batched — it lives in `.info`, one request per name — so that leg is paced
at 2.5s and took ~25 minutes. **Batch what batches; pace what does not.**

Resume is the miner's (`mine_options_cache.py`): a JSON manifest saved atomically after every
unit, skip-existing keyed on STATUS, and the tri-state rule — **a failed or throttled unit is not
recorded at all**, so it is retried, while "the vendor genuinely has nothing" is durable. That is
what makes B2 structural rather than a promise: a throttled name leaves no trace, so coverage
cannot be inflated by running into a quota wall. Pinned by test.

### 12.4 The rung distribution, full universe vs the 46-name sample — AND MY PREDICTION WAS WRONG

| rung | 46-name sample (Part 7.4) | **500-name full universe** |
|---|---|---|
| `vendor` | 34 (73.9%) | **432 (86.4%)** |
| `vendor_corroborated` | 3 (6.5%) | **31 (6.2%)** |
| `computed` | 4 (8.7%) | **14 (2.8%)** |
| `fallback` (the constant) | 5 (10.9%) | **22 (4.4%)** |
| `vendor_uncorroborated` | 0 | 1 (0.2%) |

**PRE-REGISTERED PREDICTION (60/40): the full universe would show a HIGHER fallback share than
the sample. IT IS LOWER — 10.9% -> 4.4%.** The reason is visible in hindsight and was not
reasoned about in advance: the 46-name sample was the 7 named cases **plus 5 deliberately
out-of-band names** plus every 12th served name, so it was *enriched with problem names by
construction*. It overstated the constant's reach by ~2.5x. **The lesson the record already
carries applies to my own sampling: do not reason about the direction of an effect in this
project, measure it.**

**B1 (do-no-harm) HELD, verified on real cached data, not only on the design probe.** Every
served name from the record's named cases resolves to the value already published in Part 7.6,
through an entirely different fetch path: **GILD 0.305, CI 0.288, KSPI 0.886 (n=30), CHTR
0.669** — all exact. KSPI is still rejected **for its 30 observations, not its size**, which was
the condition that would otherwise have made the original fix a FAIL. (MRK, XOM and KO turn out
not to be in the served 500 at all.)

### 12.5 The 22 names on the constant, enumerated — and the cap is the live issue

**36 of 500 names (7.2%) get a beta different from the vendor's**; 22 land on `BETA_FALLBACK = 1.0`.
They are not a random tail, they are three coherent groups:

* **7 with a vendor beta ABOVE `BETA_HIGH_CAP = 3.0`:** ARM 3.909, ALAB 3.843, BE 3.832, AFRM
  3.616, AGGI 3.371, COIN 3.361, CRDO 3.233.
* **6 with a NEGATIVE vendor beta:** BEKE -0.257, ZTO -0.220, GALDY -0.097, BAESY -0.052,
  TCOM -0.044, PDD -0.005 — mostly Chinese ADRs.
* **9 recent listings with too little history** to compute one (`MIN_COMPUTED_OBSERVATIONS = 24`):
  BSP (2 monthly closes), FDXF (3), ARXS (4), KXIAY (10), Q (10), AMRZ (14), CRCL (14), JBS (14),
  SNDK (18).

**This measures Part 7.7's open item at scale.** That note said CRDO's vendor (3.233) and own
(3.412) values *agree* the beta exceeds the cap, which is arguably evidence the cap is too low.
It is now **7 names, and they are exactly the names one would expect to be genuinely high-beta**.
Pricing ARM at a beta of 1.0 understates its risk by a wide margin. **Moving `BETA_HIGH_CAP`
still needs its own bound and its own do-no-harm run — nothing here changes it** — but the
population is no longer anecdotal.

### 12.6 The theme leg: 0 usable rows -> 500 real rows, and NOT ONE VERDICT MOVES

**The public `/api/hotstocks` endpoint is a credential-free window onto the real record**, and
Part 11 said no such window existed. It carries all ten per-name theme scores. `seed` replays a
capture through the project's **own** `Store.save_snapshot` into a **dedicated** database
(`data/live_cache/served.db`) — never `data/screener.db`, which still holds another lane's 2099
fixture.

| | before | after |
|---|---|---|
| usable rows | **0** | **500** |
| real scan dates | 0 | 1 (`2026-08-08`) |
| distinct names | 0 | 500 |
| synthetic rows | all of them | **0** |
| themes QUOTABLE | 0 of 10 | **0 of 10** |

**B4 HELD: not one of the ten verdicts changed** (predicted 95/5). **B5 HELD: still zero closed
63-day windows** — the newest scan is two days old, so no window can have closed, and real
breadth cannot manufacture one.

**What DID change is the REASON, and that is the useful part.** Seven themes moved from *"theme
is empty in the record"* to *"0 closed monthly windows"* — from blocked by absent data to blocked
by elapsed time. And the power line is now real rather than hypothetical: **at a 500-name
cross-section a live IC of +0.0379 is detectable by month 60, against `quality`'s backtested
+0.0356.** That is the V2 calibration confirmed from the other direction — the served store is
very nearly the breadth this meter needs, and the top-100 archive never was.

**The endpoint serves the LATEST scan only. It lists 9 dates in `history` and none of the other 8
can be fetched.** So the record can be accrued **forward** from a checkout, one day per run, and
**never backfilled**. Nine days of real history exist on Render that this repo cannot reach.

### 12.7 THE FINDING: 43% of the live composite's weight contributes nothing

Applying the COVERAGE RULE to the live product rather than to the panel, over 500 served rows:

| theme | non-null | distinct values | deployed weight | reaches the score? |
|---|---|---|---|---|
| value | 500 (100%) | 500 | 0.125 | yes |
| quality | 500 (100%) | 500 | 0.125 | yes |
| size | 500 (100%) | 488 | 0.125 | yes |
| momentum | 477 (95.4%) | 477 | 0.125 | yes |
| low_risk | 498 (99.6%) | 494 | 0.0 | (zero-weighted) |
| growth | 482 (96.4%) | 477 | 0.125 (speculative book) | yes |
| **insider** | **500 (100%)** | **1** | **0.125** | **NO — constant** |
| **capital_discipline** | **0 (0%)** | 0 | **0.125** | **NO — absent** |
| **institutional** | **0 (0%)** | 0 | **0.125** | **NO — absent** |
| sentiment | 0 (0%) | 0 | 0.0 | (zero-weighted, no loss) |

`WEIGHTS_ESTABLISHED` sums to 0.875. **Three themes carrying 0.375 of it — 42.9% — contribute
nothing to any live score.** `composite_score` renormalises over whatever is present
(`cross_sectional.py:105`), so the live hot list is a **four-theme** book (value, quality, size,
momentum) wearing the weights of a nine-theme one.

* **`insider` being dead is KNOWN and documented** — `screen.py:288-292` names it as the live
  example, with the mechanism (no `insider_score` -> `build_frame` fills the column with the
  constant 0.0 -> `zscore` of a zero-variance column is all-NaN -> renormalised away).
* **`capital_discipline` and `institutional` at 0% are NOT documented anywhere I can find**, and
  `capital_discipline` is the theme with the **second-strongest backtest IC (+2.76)** and one of
  only two that clear X7's calibrated bar of 2.71. The backtested edge leans on a theme the live
  product cannot compute.
* **The aggregate is what matters and nothing was reporting it.** `screen.py` already computes
  `theme_coverage` and `theme_contributing` into the scan health block for exactly this purpose —
  but the served payload's `health` key is **null**, so none of it reaches anyone.

**No claim is made here about how much this costs in return.** That is a backtest question (score
the panel with those three themes removed) and it is not this lane's, and not this run's.

### 12.8 Two defects found in MY OWN V2 meter, both by real data rather than by inspection

**(a) A DEGENERACY HOLE THAT WOULD HAVE PRODUCED A VERDICT, NOT A REFUSAL — the serious one.**
V2 froze seven coverage floors and every one counts NON-NULL ROWS. `insider` is 100% non-null and
constant, so it passed every floor. And **`_spearman` does not return NaN on a constant
predictor** — measured, it returns an arbitrary number: roughly [-0.15, +0.17] against random
targets, and **exactly +1.0 when the target happens to be monotone**. The meter would have banked
those as genuine monthly observations, and a run of them in one direction is precisely what an
anytime-valid band exists to call significant. **The absent themes were always going to refuse
safely. This one would have produced a live verdict on a column that carries no information.**

Fixed with a degeneracy floor measured **per date** (a theme is ranked within a cross-section):
`MIN_DISTINCT_VALUES = 2`, reported as its own blocking reason and marked in the depth table,
because *absent* and *constant* have different owners — one needs a data source, the other needs
a writer fix. **This is a TIGHTENING, recorded rather than slipped in**, permitted by
`PREREG_v2_theme_health.md` §10: refusing more data can only delay a verdict, never manufacture
one. Four new tests; `tests/test_theme_health.py` is now **27**.

**(b) The cache did not survive its own round trip.** Five years of monthly closes straddle
several DST changes, so serialising a tz-aware index with `str()` emits mixed UTC offsets and
`pandas` refuses to parse the list back. Normalised to UTC with the zone recorded separately.

**And the trap that motivated B1 in the first place, restated because it is silent:** batched
`yf.download` returns a **tz-naive** index while the market proxy is **tz-aware**, so the
intersection is empty, `compute_beta` reports `unavailable`, and rung 3a responds by keeping the
vendor beta. A naive batching implementation disables corroboration on **every name in the
product** and raises nothing. `_align_index` is the fix and three tests pin it.

### 12.9 Tests

**Full gate: 26 suites, 1199 tests, 0 failures, exit 0.** `tests/test_live_cache.py` 40 (new),
`tests/test_theme_health.py` 27 (23 -> 27).

### 12.10 What I did NOT do

* **Did not read production's database.** Only the public, credential-free `/api/hotstocks`.
* **Did not change any beta, any WACC, any fair value, or any published number.** This run is
  instrumentation and measurement; the ladder was driven, never modified.
* **Did not move `BETA_HIGH_CAP`**, though 12.5 now gives it a population. It needs its own bound.
* **Did not fix `capital_discipline` / `institutional` / `insider`** — `valuation/screener/` is
  not this lane's, and the scope was new files plus reads.
* **Did not add a scheduled job.** Accruing the record forward needs `capture` + `seed` on a
  daily cron, which is a Cowork/infra decision, not mine to make.
* **Did not backfill** the 8 earlier scan dates; the endpoint cannot serve them.
* **Zero trial cost** — a coverage exercise searches nothing. Equity `N` stays **129**.

### BUGS FOUND (Part 12)

1. **`capital_discipline` and `institutional` are null on 100% of served rows while carrying
   0.125 deployed weight each**, and `insider` is constant while carrying 0.125 — so **42.9% of
   the composite's weight mass reaches no live score**, and the hot list is a four-theme book.
   `insider`'s deadness is documented at `screen.py:288`; the other two are not. **Owner:
   screener lane.**
2. **The served payload's `health` key is `null`**, so `theme_coverage` / `theme_contributing` —
   which `screen.py` computes precisely to surface bug 1 — reach nobody. **Owner: screener/web.**
3. **Nothing in the repository catches a rate-limit exception.** `YFRateLimitError` appears only
   in prose; every fetch path swallows it in a bare `except Exception`, making a throttled call
   indistinguishable from "no data" everywhere except `BetaEstimate.unavailable`. **Owner:
   whoever owns `valuation/data/`.**
4. **`BETA_HIGH_CAP = 3.0` sends 7 of 500 served names (ARM, ALAB, BE, AFRM, AGGI, COIN, CRDO) to
   a beta of 1.0**, understating the risk of names whose vendor and self-computed betas agree
   they are high-beta. Escalation of Part 7.7's open item from one name to a population.
5. **`tests/test_saas.py:200` still writes a 2099-01-01 row into the real `data/screener.db`**
   (carried from Part 11, unfixed — another lane's file).

## Part 13 — FREE LIVE SOURCES FOR THE THREE DEAD THEMES: BUILT, MEASURED, AND NOT SHIPPED (2026-08-10, greeks lane)

Follow-up to Part 12, which found that **42.9% of the deployed composite weight reaches no live
score**. This builds a free, public source for each of the three dead themes and measures its
coverage against the same 500 served rows. **Everything here is an instrument. Nothing reaches
the product**, and that is enforced by a test rather than promised in prose.

Pre-registered in **`PREREG_v2g_live_theme_sources.md`, committed ALONE at `66310e7`** before any
fetch or measurement code existed. Implementation `scripts/live_theme_sources.py`, **53 tests** in
`tests/test_live_theme_sources.py`, artifact `data/free_analysis/V2G_LIVE_THEMES.json`.

### 13.1 THE HEADLINE

| theme | live state (Part 12) | **V2G measured coverage** | distinct values | floors |
|---|---|---|---|---|
| `institutional` | **null on 500/500** | **411 / 500 = 82.2%** | 410 | clears 0.30 and 0.05 |
| `capital_discipline` | **null on 500/500** | **456 / 500 = 91.2%** | 441 | clears 0.30 and 0.05 |
| `insider` | 500/500 present, **1 distinct** | **500 / 500 = 100.0%** | **297** | clears 0.30 and 0.05 |
| `quality` ← accruals input | (quality already live) | 385 / 500 = 77.0% | 385 | clears 0.30 and 0.05 |

Floors are the project's own constants, applied unchanged: `COVERAGE_FLOOR = 0.05`
(`fundamental_panel.py:3833`), `MIN_COVERAGE = 0.30` (`pead.py:121`, `elite13f.py:90`),
`MIN_DISTINCT = 2` (`theme_health.MIN_DISTINCT_VALUES`).

**Share of deployed weight that reaches a live score, mean over the 500 served names: 56.5%
today → 95.5% with these sources.** `insider` is counted as reaching nothing today, because it
does: it is present, constant, and renormalised away after standardisation. **31 names would
still sit below 80% weight coverage** — the gap is not uniformly closed and is named in §13.5.

**ALL FIVE PRE-COMMITTED BOUNDS HELD.** B1 institutional ≥ 0.30 (0.822). B2 anchor pass ≥ 95%
(423/423 = 100%). B3 external validity — most-held served name **NVDA at 5,775 distinct filers**
(≥ 2,000) and **Spearman(holder breadth, log market cap) = +0.539** (> +0.30). B4
`capital_discipline` usable. B6 `insider` ≥ 10 distinct (297).

### 13.2 WHAT WAS BUILT, AND WHY IT IS FREE

The brief's premise is correct and is what makes this possible: **SF3 is a licensed aggregation
of 13F; the underlying filings are public record.** Nothing here touches `data/backtest`.

* **`institutional`** — SEC **Form 13F structured data sets**, the quarterly zips at
  `sec.gov/files/structureddata/data/form-13f-data-sets/`. Two periods, **31-DEC-2025 →
  31-MAR-2026** (the `01jun2026-31aug2026` window is not published; Q2-2026 13Fs are due
  2026-08-14). 90.3 MB + 99.4 MB, aggregated to **22,092 and 22,626 CUSIPs** from **8,625 and
  8,741 distinct filers** over **3.08M and 3.11M** share rows. Options rows (`PUTCALL` set) and
  bond rows (`SSHPRNAMTTYPE = PRN`) are excluded; restatement amendments supersede, new-holdings
  amendments are additive. Then, exactly as `factors.py:267` builds it:
  `institutional = mean(z(inst_accum), z(sm_breadth))`, where `sm_breadth` is growth in distinct
  holder count and `inst_accum` is growth in **shares** held.
  **`inst_accum` is share-based on purpose, fixed in the register before the run:** a
  dollar-based change over a quarter is mostly the stock's own price move, which would have made
  a "13F accumulation" signal a momentum signal wearing a 13F label.
* **`capital_discipline`** — share issuance from **XBRL company facts**, two annual points,
  `neg_issuance = -(shares_t / shares_{t-1} - 1)`, matching `factors.py:254`, which is issuance
  **alone**.
* **`insider`** — the repo's **already-fixed Form 4 scraper**, imported and called unmodified,
  including its refusal contract. Then `(score - 50) / 25`, matching `factors.py:271`.

**THE BRIEF'S THIRD ASK LANDS IN A DIFFERENT THEME, AND THE REGISTER SAID SO BEFORE THE RUN.**
The brief asked for accruals under `capital_discipline`. `factors.py:254` is `neg_issuance`
alone; `accruals_q` is a **`quality`** input (`factors.py:227`), and `quality` is one of the four
themes that already works live. So **net issuance is the only input that can revive
`capital_discipline`; accruals can only improve a theme that was never dead.** Built and reported
anyway, labelled against the theme it actually feeds. No number was moved between themes to make
a total look better.

### 13.3 THE JOIN WAS THE HARD PART, AND IT IS WHERE THE INSTRUMENT IS WEAKEST

13F identifies issuers by **CUSIP**; the served universe identifies them by **ticker**; there is
no free CUSIP master. The ladder, with the rung recorded per name:

| rung | names | what it is |
|---|---|---|
| `cusip_13g` | **398** | the company's own SC 13D/G filings carry its CUSIP; every candidate must pass the **mod-10 check digit**, and the modal validated value across up to 6 filings wins |
| `name_exact` | 13 | normalised exact match on `NAMEOFISSUER` |
| `too_few_holders` | 12 | matched, then refused — see §13.4 |
| `ambiguous` | 49 | the name matched **more than one** CUSIP — a failure, never a coin flip |
| `unmatched` | 28 | no CUSIP from either rung |

**The authoritative rung did 94% of the work** (398 of 423 matched), which was predicted. The
ownership anchor — 13F dollars held over market cap, admissible in `(0, 1.50]` — passed
**423/423**, median **0.682**, p95 **0.992**, max **1.426**. A median of 68% institutional
ownership across a large-cap screen is the right answer, and it is the strongest single piece of
evidence that the join landed on the right issuers.

**THE FAILURE MODES ARE COHERENT AND NAMED, not a diffuse loss.** Of the 77 unjoined names, 16
are five-letter ADR tickers ending in `Y`, and the rest are dominated by foreign issuers whose
13F names are abbreviated beyond exact match (`PNC FINL SVCS GROUP`) or split across ADR and
ordinary lines (`ambiguous`: BCS, NWG, RY, EQNR, AMX, SLF, …).

**AND ONE COHORT IS SYSTEMATICALLY WORSE, which matters for a screener full of banks: the join
fails on 26.8% of Financial Services names against 13.2% everywhere else — twice the rate.**
The cause is `edgar13d.py`'s filer-vs-subject contamination in a new place: **a company that is
itself an asset manager files SC 13Gs ABOUT OTHER ISSUERS, and EDGAR's submissions feed for a CIK
carries the filings it MADE as well as those naming it as subject.** PFG came back with six
candidate CUSIPs at one vote each. **29 of 500 names hit that tie.** Caught during the smoke test,
before the full run: a tie is now a refusal that falls through to the name rung, rather than being
resolved by dictionary insertion order.

### 13.4 THE DEFECT I FOUND IN MY OWN INSTRUMENT — the anchor is one-sided IN EFFECT

**The pre-registered anchor band `0 < frac <= 1.50` rejects implausibly HIGH institutional
ownership and waves through implausibly LOW.** A join onto a stale or wrong CUSIP that
essentially nobody reports holding lands at `frac ≈ 1e-6` — comfortably *inside* the band.

It passed **12 names**, and they are not obscure ones: **CMCSA, RIO, BTI, HSBC, MT, AMP, CM, MGA,
SHG, IHG, TELNY, GALDY, IFNNY** — megacaps credited with **one single reporting institution**.
Two of them (AMP, MT) produced `None` anyway because no prior-quarter record existed, i.e. they
were caught **by luck, not by design**; had that CUSIP existed in both quarters they would have
produced a garbage breadth-change that passed every check in the pipeline.

**Fixed with a structural floor, not a tuned one.** `sm_breadth` is the *growth in holder count*,
and a holder count of one cannot express breadth or its change at all — `MIN_HOLDERS = 2` is the
smallest count at which the measure is **defined**, and it is not chosen to hit a coverage number.
Recorded as a **tightening** (PREREG §8 permits tightening, not loosening), and **both figures are
published rather than one replacing the other**:

* institutional coverage under the **pre-registered** rule: **421 / 500 = 84.2%**
* institutional coverage with the **tightening**: **411 / 500 = 82.2%** ← the number to quote

**RESIDUAL RISK, STATED RATHER THAN CLOSED:** four matched names still carry only 2–5 reporting
holders (KBGGY 2, HSBC 2, SMCI 5, CP 7 is above). They pass a floor of two and remain suspicious.
They are listed so a reader can see them; raising the floor further would be tuning against the
coverage number, which the register forbids.

### 13.5 THE COVERAGE GAPS ARE FOREIGN ISSUERS, AND THEY ARE THE SAME NAMES EACH TIME

* **`capital_discipline` misses 44 names**, of which **41 have ZERO annual share-count points**
  in XBRL — foreign private issuers filing 20-F do not report
  `dei:EntityCommonStockSharesOutstanding` on the US annual cadence. Three more have exactly one
  point, and issuance needs two.
* **Accruals misses 115 names (23%)** for the same reason one level deeper: IFRS filers have no
  `us-gaap:Assets` / `NetCashProvidedByUsedInOperatingActivities`. So the 77.0% figure is
  effectively "the US-GAAP share of the served universe", not a data-quality problem.
* The 31 names still below 80% weight coverage are overwhelmingly this same ADR cohort.

### 13.6 THE INSIDER THEME COMES ALIVE, AND ITS SHAPE IS THE FINDING

`insider` goes from **1 distinct value to 297** across 500 names — B6 cleared by a wide margin.
But the distribution is the part worth carrying:

* median **43.68**; **179 names (35.8%) score exactly 50.0** (genuinely quiet — no qualifying
  Form 4 activity in the 90-day window);
* **278 names score below 50 and only 43 above.** The live theme, as constructed, is
  overwhelmingly a **"who is selling least"** sort rather than a "who is buying" sort. That is not
  a defect — insiders sell for liquidity and compensation far more often than they buy — but it
  is a different signal from the one the theme's name suggests, and anyone adopting it should know
  that before, not after.
* **16 names pin at exactly 10.0** — the `50 + 40·tanh(pressure/4000)` floor. Zero names reach
  the ceiling. **This is audit item S3's mechanism corroborated on live data:** the scale constant
  (≈ √$16M) is far too small for megacap insider selling, so the strongest sellers are
  indistinguishable from each other. ABNB, ALAB, AMAT, APP, CVX, DDOG, FANG, FLEX, HSY, ILMN, MDB,
  MPWR, NTRA, TTWO, WDAY, XYZ all score identically.

**My pre-committed prediction P4 was WRONG on its second half:** I predicted ≥50% of names would
score exactly 50.0; measured **35.8%**.

### 13.7 RATE LIMITS — V2F's lesson transferred, and the fleet DID get pushed back

V2F's finding was *"batch what batches, pace what does not"*. Here **the 13F leg batches all the
way**: two ~100MB quarterly zips replace what would otherwise be tens of thousands of per-filer
fetches, and the whole aggregation runs in **~31 seconds**. Only the per-ticker legs (13G cover,
XBRL facts, Form 4) are paced.

Those legs are **latency-bound, not quota-bound**: one serial process reached ~3 req/s against
SEC's published ~10 req/s ceiling, projecting **~3 hours**. Four interleaved shards at a higher
per-process interval brought it to **~48 minutes** with the fleet under the ceiling.

**SEC pushed back 27 times across the fleet, and that is reported rather than smoothed over.**
Every one was retried with backoff and **none was recorded**: the manifest refuses a non-terminal
status by construction, so a throttled unit is simply absent and gets retried. **Final state
500/500 on all three legs**, confirmed by a serial closing sweep that found exactly one gap and
filled it. Coverage cannot inflate by running into a wall.

The other structural carry-over: **`report` makes ZERO network calls.** It drives the real
construction against the cache. A measurement that consumes the resource it measures reports on
its own exhaustion and calls it a result.

### 13.8 ADOPTION IS A SEPARATE DECISION AND MUST NOT BE SHORTCUT FROM THESE NUMBERS

Stated in the register **before** any coverage number existed, and repeated here because a table
of green ticks is exactly what gets misread:

**Coverage is a NECESSARY condition, not a sufficient one.** Before any of these enters the
composite it needs, at minimum:

1. **The pipeline builder's cost measurement.** Concretely, from this run: the 13F leg is ~190 MB
   per quarter and ~31 s of CPU — trivial. The **insider leg is the expensive one**: it fetches
   *every* Form 4 in the 90-day window with no cap, and **23 of 500 names exceeded 40 filings
   each**. A daily scan paying that cost is a real operational decision, not a rounding error.
2. **The held-out gate** — `holdout_theme_validate` / `holdout_compare_panels` at the standing
   margins, **100 bps alpha and 0.25 long-short t, in BOTH split directions**. Nothing here is
   evidence that any of these three themes *predicts returns live*. This measured whether the
   data exists, not whether it works.
3. **Acceptance of Rule 6's price.** Under **Amendment 1** (`PAPER_TRACK_CONTRACT.md` §5a) an
   ADOPTED change — one that ships in the live scoring path — **closes vintage 2 and opens
   vintage 3, resetting the entire accrued forward clock to zero and buying nothing
   statistically** (§2: 60 months at 49% power). Vintage 2 opened **2026-08-10** with
   `params_id 0060c5ef3dda`. Adopting these three themes on 2026-08-11 would discard a
   one-day-old clock — cheap today, and **the price rises every day this is deferred**, which is
   an argument for deciding soon, not for deciding casually. **V1 shadow vintages is the
   instrument that would measure whether the adoption helped**, and it is registered and blind.

**No vintage event occurred in this session.** Nothing shipped in the live scoring path.

### 13.9 SCOPE, ENFORCED

`git diff --stat origin/main...HEAD` for this work:

```
 PREREG_v2g_live_theme_sources.md |  239 +++++++++
 scripts/live_theme_sources.py    | 1091 ++++++++++++++++++++++++++++++++++++++
 tests/test_live_theme_sources.py |  627 ++++++++++++++++++++++
 3 files changed, 1957 insertions(+)
```
**Zero files under `valuation/`.** No composite change, no weight flip, no vintage event.

**B5's enforcement mechanism was changed from the register's wording, and that is recorded rather
than quietly substituted.** The register proposed asserting B5 with a raw `git diff` test. A
git-diff test **fails for any unrelated lane that legitimately edits `valuation/`**, which makes
it a nuisance rather than a check. The standing test asserts the invariant that actually matters
and is strictly more durable: **no shipped module may reference `live_theme_sources`**, and the
script may not call `build_frame`, `_decompose`, `composite_score`, `save_snapshot` or
`run_screen`. If a later change wires one of these columns in, that test fails — which is the
point. The one-off git diff was run by hand and its output is above.

### 13.10 EVERY DEVIATION FROM THE REGISTER

| # | deviation | direction | when |
|---|---|---|---|
| 1 | `MAX_FORM4_PER_NAME = 40` was **not enforced** — capping it requires editing the shipped scraper, which B5 forbids. Every filing was fetched, so the data is *more* complete than registered and the truncation caveat does not apply; `form4_truncated` is a descriptive flag (23 names). | more complete | during |
| 2 | B5's enforcement mechanism (§13.9) | more durable | during |
| 3 | CUSIP tie-break tightened to require a genuine mode | tightening | **before** any coverage number |
| 4 | `normalise_name` strips corporate suffixes from the END only, plus a leading `THE` | narrower | **before** any coverage number |
| 5 | `MIN_HOLDERS = 2` (§13.4) | tightening | **after**; both figures published |
| 6 | PREREG §4.3 quoted "10,676 filings, 10,524 filers, 147 multi" for 31-DEC-2025. That ad-hoc count included **13F-NT notices**, which carry no holdings. The aggregation correctly counts `13F-HR`/`13F-HR/A` only: **8,738 filings, 8,625 filers, 108 multi (1.25%)**. The RULE is unchanged; the descriptive figure in the register is corrected here. | correction | after |

### 13.11 PREDICTION SCORECARD — 2 right, 2 wrong, 1 not evaluable

| # | prediction | measured | verdict |
|---|---|---|---|
| P1 | `institutional` coverage 0.70–0.95 | **0.822** | **RIGHT** |
| P2 | name rung adds < 15pp | **4.0pp** (398 authoritative vs 13 by name) | **RIGHT** |
| P3 | `capital_discipline` coverage **lower** than `institutional` | **0.912 vs 0.822 — higher** | **WRONG** |
| P4 | `insider` clears B6 / ≥50% score exactly 50 | B6 cleared (297 distinct); **35.8%** at 50 | half **WRONG** |
| P5 | anchor failures concentrate in ADR / multi-class | **zero anchor failures** | **NOT EVALUABLE** |

Consistent with this project's record: writing the expectation down first keeps being worth it
precisely because it keeps being wrong.

### 13.12 THE OTHER HALF OF THIS QUESTION WAS ANSWERED IN PARALLEL, AND IT CHANGES THE PRIORITY

While this run was fetching, the **pipeline builder lane** landed its own item off the same Part
12 finding — ledger `V2G`, `HANDOFF_edge_audit.md` session 17 — asking what the three dead themes
**cost in return**. It is the half this lane explicitly declined to price, and the two results
should be read together:

* **The cost is IMMATERIAL by their pre-registered rule:** the live four-theme book scores
  **+5.86% alpha against the deployed seven-theme +7.17%**, Δ **−1.31pp** against a −1.95pp bar,
  paired HAC t **−1.40**. **Their power caveat must travel with it** — 55.0% against a true
  1.95pp gap, so "immaterial" means *could not be separated from zero at roughly a coin flip's
  power*, not *shown to be small*.
* **Their second finding is the serious one:** the live four-theme book **fails the calibrated
  long-short floor** (HAC t 1.8811 vs 2.2837) where the deployed book clears at 2.6199 — while
  still clearing the top-decile alpha floor (3.2087 vs 2.2913), which is the product-relevant
  statistic for a long-only hot list.
* **Their exploratory decomposition reorders the work this Part just made possible**, and it
  cuts against the easiest build: dropping `institutional` is the **only** arm negative in both
  halves (−1.41% full, −0.89% early, −1.91% late), so **13F is the source to build first** — and
  it is the one this run covers at 82.2%. Dropping `capital_discipline` is **POSITIVE in both
  halves** (+1.37% full) despite holding the second-strongest panel IC (+2.76), which is X3's
  finding restated: **theme IC does not predict marginal contribution.** So the theme this run
  covers *best* (91.2%, the cheapest of the three to wire) is the one with the least evidence it
  helps. Carried with their own label: exploratory, no verdict.

**The convergent conclusion, which neither result reaches alone: the reason to build these is
claims integrity, not alpha.** The live product computes a **different composite** from the one
every published figure is measured against — the same class of defect audit B7 exists to prevent —
and that is true whether or not the return difference is separable from zero.

### 13.13 TRIAL COST

**ZERO for this run.** No hypothesis about returns was tested, no arm selected, no weight chosen —
this is a coverage census of data sources, and the Deflated Sharpe chain is untouched by it.
**The denominator in force is now `N` = 135, not 131**: the pipeline builder's parallel item
charged four arms (131 → 135) and landed on `main` while this was running. Quote 135. A trial is
charged here if and when one of these columns is *selected into* the composite.

### 13.14 WHAT I DID NOT DO

* **Did not wire anything into the composite**, by design, and a test now prevents it happening
  silently.
* **Did not test whether any of these predicts returns.** That is the held-out gate's job and it
  is the whole remaining question.
* **Did not build a sentiment source.** `sentiment` is also null on 500/500 rows but carries
  **0.0** deployed weight, so it costs the live score nothing and was out of scope.
* **Did not fix the insider `tanh` saturation** (§13.6 / audit S3) — it is a shipped-scoring
  change in the screener lane, and touching it here would have been the vintage event this run
  exists to avoid.
* **Did not schedule anything.** These caches are a one-shot census. Accruing 13F quarter over
  quarter needs a job, and that is a Cowork/infra decision.

### BUGS FOUND (Part 13)

1. **My own instrument's anchor was one-sided and passed 12 mis-joins** (CMCSA, RIO, BTI, HSBC,
   MT, AMP, CM, MGA, SHG, IHG, TELNY, GALDY, IFNNY), two of which were caught only by luck.
   **FIXED** with a structural `MIN_HOLDERS = 2`; both coverage figures published. Four names with
   2–5 holders remain suspicious and are named. **Owner: me, closed.**
2. **The Form 4 insider score saturates at its `tanh` floor for 16 of 500 served names** — the
   scale constant `4000.0` (≈ √$16M) in `insider.py:174` is far too small for megacap insider
   selling, so the sixteen strongest sellers are mutually indistinguishable at exactly 10.0. This
   is **audit item S3's mechanism corroborated on live data**, not a new hypothesis. **Owner:
   screener lane.**
3. **A company that is itself an asset manager cannot be joined via its own EDGAR feed** — its
   submissions carry the SC 13Gs it FILED about other issuers. 29 of 500 names hit a candidate
   tie; join failure runs **26.8% inside Financial Services against 13.2% outside**. Refused
   safely here, but any future EDGAR work keyed on a company's own filings inherits it. **Owner:
   whoever next builds on EDGAR submissions.**
4. **`insider.insider_detail` fetches every Form 4 in its window with no cap.** 23 of 500 names
   exceeded 40 filings. Correct for a one-off census, but it makes the insider theme the dominant
   per-scan cost of any adoption, and nothing in the function signals it. **Owner: screener lane
   (cost note for adoption).**
5. **`VALQUO_LEDGER.md`'s `V2G` row is MALFORMED, and it is a RECURRENCE of a defect this
   project has already paid for once.** The pipeline builder's row writes `max|dev|` — absolute
   value notation — unescaped inside a markdown table cell, so the row has **14 fields against an
   11-field header** and its note is split into three columns: everything after `max` is shifted.
   This is exactly session 12's O16 defect (`|Spearman(term_slope, atm_front)|`, same cause, same
   shift), which cost that session a near-miss on the trial denominator.
   **AND IT IS WORSE THAN A SHIFT — THE ROW IS INVISIBLE.** `scripts/build_ledger.read_ledger()`
   returns **163 rows and `V2G` is not one of them**; `V2F` and `V2G-SRC` both are. So the
   ledger — the project's own authority for "is X done?" — **does not contain that lane's
   completed item at all**, and anyone asking whether the cost of the dead themes has been
   priced is told no. Its own suite passes because `tests/test_build_ledger.py` checks the
   totals it can see, not the rows it silently lost. **Not edited here** —
   the register forbids rewriting another lane's row, and the pipes want escaping as `\|` by the
   lane that owns them. The row is otherwise correct and its content is folded into §13.12.
   **Owner: pipeline builder.** *(Note also that `V2G` is a genuine id collision — that lane and
   this one independently registered the same id off the same Part 12 finding. Both rows are
   kept; this lane's is renamed `V2G-SRC`.)*
6. **Carried forward, still open from Part 12:** the served payload's `health` key is `null`, so
   `theme_coverage`/`theme_contributing` reach nobody; nothing in the repository catches a
   rate-limit exception; `BETA_HIGH_CAP = 3.0` sends 7 served names to beta 1.0; and
   `tests/test_saas.py:200` still writes a 2099-01-01 row into the real `data/screener.db`.

## Part 14 — LA1 AND LA3 FROM THE COLD AUDIT: THE LEAK IS DIAGNOSED, COUNTED AND LOUD; THE DENOMINATOR IS FIXED (2026-08-10, greeks lane)

Cold-audit findings **LA1 (BLOCKING)** and **LA3 (HIGH)** from `VALQUO_LIVE_AUDIT.md`.
Pre-registered in **`PREREG_la1_la3_repair.md`, committed alone at `b4c2a1a`** before any code
moved — including the diagnosis, both detection rules, the two new constants and the expected
values. Tests in `tests/test_la1_la3.py` (**37**).

### 14.1 LA1 — THE DIAGNOSIS, AND IT DISCRIMINATES THE BRIEF'S THREE CANDIDATES

The brief asked whether this was a stale snapshot predating the Bug A/B fix, deploy lag, or a
scan route that skips `record_refusal`. **It is none of those, and the payload settles it without
guessing.** Verified live 2026-08-10 on `https://valquo.co/api/hotstocks?top=3`:

```
scan_date 2026-08-08 · scored 594
KSPI  price 90.30  fair_value 274.13  method "blended"  withheld None  ratio 3.04x
SYF   price 78.59  fair_value 204.38  method "dcf"      withheld None  ratio 2.60x
STT   price 184.68 fair_value 220.21  method "dcf"      withheld None  ratio 1.19x
```

**Ranks 2 and 3 of that same scan carry `fair_value_method: "dcf"`.** Only `_enrich_with_dcf`
writes that. So the fixed code demonstrably ran, reached the network, and produced **nothing at
all** for rank 1 — not a value, not a refusal. That rules out a stale snapshot, rules out deploy
lag, and rules out a route that skips `record_refusal`, because it is the same single call.

The engine's verdict reproduces deterministically today: `blend.value` None,
`withheld_value` **530.2319195351978**, price 94.00, KZT statements at `fx_rate`
0.0021434847731143236 with `fx_unresolved False`, → **publish False, ratio 5.640765101438275**,
reason set. `record_refusal` *would* fire.

**IT IS FOUR NAMES, NOT ONE, AND THE BLAST RADIUS IS LARGER THAN THE AUDIT REPORTED.** Only **8
of the top 12** served rows carried a `dcf` method. KSPI, **DB, CIB and EC** were all peer
estimates — and all four are foreign issuers needing an FX hop their neighbours do not. Re-run
individually today, three of them produce a *publishable* DCF:

| name | model's own DCF today | served peer estimate on 2026-08-08 | ratio |
|---|---|---|---|
| DB | **42.25** | 88.69 | **2.10x the model** |
| CIB | **90.93** | 167.42 | **1.84x the model** |
| EC | 32.80 | 30.44 | 0.93x |
| KSPI | **refuses at 5.6x** | 274.13 | — |

So the fail-open did not merely risk publishing a refused name; it published numbers **up to 2.1x
the model's own valuation** on two more names, with nothing anywhere recording that the model had
been asked.

### 14.2 THE REPAIR, AND THE SECOND DOOR IT EXPOSED

Three changes shipped, fail-open **policy** unchanged — only its invisibility:

1. **The raise is retried once** (`DCF_ATTEMPTS = 2`) and then **counted**, stamped on the row as
   `dcf_error`, and surfaced as `health.refusal_screen.errors` with the tickers.
2. **The counter hole is closed.** `_screen_refusals` ran on `rows[run_dcf_top:]`, so the top 12
   — the most-read rows, and the ones the audit found the defect on — were excluded from its own
   counter by construction. Any DCF-window row that came back silent is now re-asked.
3. **`publication_audit()` runs on every scan** and `ci_scan` prints a `LEAK` banner naming every
   offending ticker.

**THEN RE-RUNNING THE SCAN FOUND A SECOND DOOR, AND FINDING IT IS THE ARGUMENT FOR RE-RUNNING.**
The repaired scan recorded **4 refusals against the previous scan's 0** and reported the audit
**CLEAN** — and KSPI, now at rank 97, was served a peer estimate of 282.48 with
`withheld: false` anyway, while refusing at 5.6x when asked on its own.

The cause is not an exception: **a throttled fetch returns PARTIAL COMPANY DATA rather than
raising.** `had` is None, and `publication.decide(None, price)` returns `publish=False` with an
**empty reason** by design — *"Not a refusal — there is simply nothing to publish"* — so the row
falls through to an unchecked peer estimate with `errors: 0`. Counting only exceptions cannot see
it. **This was pre-registered as a known second hole in §1 of the register, before the first run.**

**MY OWN DETECTOR MISSED IT, FOR THE SAME SHAPE OF REASON THE ORIGINAL DEFECT HAD.** D1 covered
only the DCF window, so a name at rank 97 sat outside it — the mirror image of `_screen_refusals`
excluding the top 12. Fixed: the probe now records **what it saw** on every row —
`valued` / `refused` / `no_value` / `no_data` — and a `no_data` row is flagged **`unverified`**.
`no_value` is deliberately *not* flagged: an ADR bank with no free cash flow is a legitimate
peer-multiple name, and a detector that fires on hundreds of rows is one nobody reads.

### 14.3 THE DETECTION, AND WHAT IT CAN AND CANNOT CATCH

| rule | what it catches |
|---|---|
| **D1 `asked_but_silent`** | a DCF-window row with no value, no refusal, no error — **KSPI's exact 2026-08-08 state** |
| **D2 `band_breach`** | a served row above `FV_BAND_HIGH` (5.0x) with `withheld` falsy |
| **D3 `unverified`** | a row that was asked and returned **no statements at all**, so nothing could be judged |

**D2 WOULD NOT HAVE CAUGHT KSPI, AND THAT IS PINNED AS A TEST RATHER THAN LEFT IN PROSE**
(`test_D2_WOULD_NOT_HAVE_CAUGHT_KSPI`). Its served ratio is **274.13/90.30 = 3.04x**, comfortably
inside the 5.0 band, because the refused 5.6x model was replaced by a *plausible-looking* peer
estimate. A reader who takes a green `band_breach` as evidence that the LA1 class cannot recur
has been misled. The register said so before any code was written.

**D2's invariant also turns out to be already ENFORCED on the serving path** by
`withhold.withhold_implausible_fair_values` (`web/app.py:504`), which is why **0 of 500** served
rows breach it and the max served ratio is 3.984 (STLA). D2 in the scan is a belt-and-braces
check on the scan's own writes; **D1 and D3 are the new detection that LA1 actually needed.**

### 14.4 THE VERIFICATION DID NOT CLOSE, AND THE REASON IS MEASURED, NOT GUESSED

**VERIFIED CLOSED ON PRODUCTION — but only on the fourth scan, and the three that failed are
reported here because they are the finding.** Four full production scans were run with the fix (each ~35 min, universe 1500, DCF top 12,
refusal screen 500, all ingested):

| run | refusals recorded | `unverified` | probe distribution |
|---|---|---|---|
| **2026-08-08 (pre-fix, for reference)** | **0** across 500 served rows | not measurable | — |
| repaired, run 1 | **4** | 0 *(D3 did not exist yet)* | — |
| repaired, run 2 | 3 | **13** | `valued 483, no_data 13, refused 3, no_value 1` |
| + slow mop-up, run 3 | 2 | **32** | `valued 464, no_data 32, refused 2, no_value 2` |

**THE MOP-UP MADE IT WORSE AND I AM RECORDING THAT AS A FAILED FIX, NOT TRIMMING IT OUT.** The
diagnosis behind it was measured and real — re-asked at **2 workers instead of 8, all 13
`no_data` names returned data, 12 valued and KSPI REFUSED at 5.6x** — so I concluded the leak was
our own instantaneous request rate and added a slow second pass. It is the wrong diagnosis at the
wrong scale: the constraint is **cumulative Yahoo quota across the whole scan**, not concurrency,
and the mop-up spent *more* quota, taking `no_data` from 13 to 32.

**THE REAL FINDING UNDERNEATH IS BIGGER THAN LA1: THE REFUSAL SCREEN IS QUOTA-BOUND AND HAS BEEN
DEGRADING SILENTLY SINCE IT SHIPPED.** The 2026-08-08 production scan recorded **zero refusals
across 500 served names** — on a list whose rank-1 name refuses at 5.6x. That is not a scan that
found nothing to refuse; it is a scan that could not look, and nothing said so. This matches
this lane's own recorded measurement that a few hundred Yahoo names throttles and *silently
empties* `CompanyData` rather than raising.

**What is delivered, and it is the thing the audit asked for:** the screen's degradation is now
**loud, named and counted** on every scan instead of silent. A `LEAK` banner listing 32 tickers
is the correct output for a scan in this state — it is what a reader needed on 2026-08-08 and did
not get.

**I deliberately did not hand-patch the production snapshot** to reach this. The only write path
is whole-snapshot `/admin/ingest-snapshot`, and re-POSTing served rows would have written peer
estimates into the store as though they were scan output — mutating production data to make one
row look right. The verification below is a real scan's output.

### 14.8 THE VERIFICATION, ON PRODUCTION

`GET https://valquo.co/api/hotstocks?top=500`, after the fourth scan:

```
scan_date 2026-08-11 · scored 786
KSPI · rank 4 · price 94.00 · fair_value None · method "withheld" · fair_value_withheld TRUE
withheld rows: RNR, KSPI, TLK, PSLV, PHYS, EXE, CHTR   (7)
band breaches: 0
```

**Against 2026-08-08: `fair_value 274.13`, `method "blended"`, `withheld None`, and ZERO withheld
rows across the whole served list.** The name the cold audit opened on now serves the refusal its
own valuation page has always given.

**WHY IT TOOK FOUR SCANS, STATED PLAINLY: KSPI reached rank 4 in this scan, which put it inside
the DCF window, where the full pass with its retry reaches it.** At rank 97 in the previous scan
it depended on the quota-bound refusal screen and leaked. **So this is a verification, not a
demonstration that the class is closed** — a name that refuses and ranks outside the top 12 on a
quota-exhausted scan will still leak, and the LEAK banner will name it. That is the honest
reading and it is why bug 1 below stays open.

**ONE LOOSE END I could not reconcile from the logs and am not going to paper over:** that same
scan's `unverified` list *also* contains `KSPI`, while its stored row is correctly withheld.
`publication_audit` excludes withheld rows from D3 by construction, so a row appearing in both is
a contradiction in the detector's bookkeeping, not in the outcome. The published row is right;
the count may over-report. **Worth a look before anyone treats `unverified_count` as exact.**

### 14.5 LA3 — THE DENOMINATOR

`summarize()` set `days = len(series)` — rows the recorder wrote — and used it as the
annualisation exponent while the recorder is missing **71%** of its days.

**Fixed: annualisation is on ELAPSED TRADING DAYS**, via one shared primitive
`market_session.trading_days_between`, pinned by test to agree with `track_meter`'s own calendar
walk so the two cannot drift — the two-sources-of-truth class this whole audit is about.

Measured on the audit's own construction (one year, identical underlying daily returns, identical
final cumulative levels, thinned three ways):

| series | rows | elapsed | **before** `ann_alpha` | **after** | sharpe before → after |
|---|---|---|---|---|---|
| complete | 252 | 252 | 24.5861% | **24.5861%** | 0.9970 → **0.9970** |
| every 2nd day | 127 | 252 | 56.0812% | **24.5861%** | 0.9674 |
| every 3rd day | 85 | 252 | 96.6239% | **24.5861%** | **withheld** |

**The alpha rows are an EQUALITY, and it holds to `0.000e+00` against a pre-committed 1e-9 bar.**
All three end at the same cumulative level over the same elapsed window, so the corrected
exponent *must* reproduce the complete series exactly. The complete series is **bit-identical**
before and after — no published figure moves on a track that was recorded properly.

**THE GATE DELIBERATELY STAYS ON RECORDED ROWS.** `MIN_LIVE_DAYS` and `MIN_SHARPE_DAYS` still
count rows. Moving them onto elapsed time would let a gappy track reach the floor **sooner** —
the flattering direction, advancing the public *"backtested → live"* posture on the strength of
days nobody recorded. Rows are the conservative denominator for a **gate** and the wrong one for
an **exponent**; the fix separates those jobs and a test pins it.

**Sharpe** is rescaled by the true observation span (`sqrt(TRADING_DAYS · n_obs / elapsed)`;
exactly 1 on a gapless series) and **WITHHELD below `MIN_COVERAGE_FOR_SHARPE = 0.5`** rather than
corrected — the same choice `track_meter.monthly_excess` makes when a month's mark is stale. That
constant was committed in the register **with its structural argument, before any coverage figure
was computed**: below half coverage the typical observation spans more than two trading days, so
the i.i.d. rescaling is doing more work than the data supports.

`coverage` and `elapsed_trading_days` now ship beside the figures, so a reader can see the
denominator rather than trust it.

**Nothing published moves today** — the real track has `days = 2`, far below the floor, so both
figures render "—". The fix changes the number that would otherwise have been published later,
which is the only moment at which it could have done harm.

### 14.6 EVERY DEVIATION FROM THE REGISTER

| # | deviation | direction |
|---|---|---|
| 1 | D3 `unverified` added — a third rule the register did not name, for the no-exception door §1 *did* predict | stricter |
| 2 | `NO_DATA_RETRY_WORKERS = 2` mop-up added on a measured diagnosis, then found to make things worse; **kept and reported as a failed fix** rather than quietly reverted | recorded |
| 3 | Expected `band_breach = 0` (§2) held: **0 of 500 served rows**, max ratio 3.984 | as predicted |
| 4 | Expected `asked_but_silent ≥ 1 including KSPI` (§2): held on the pre-fix payload shape, and the live recurrence surfaced as **D3 `unverified`** instead — the same leak through the door §1 predicted | as predicted, different rule |

### 14.7 WHAT I DID NOT DO

* **Did not hand-patch production** to make KSPI look right (§14.4).
* **Did not change the fail-open policy.** Withholding every name we could not reach is a product
  decision that would blank hundreds of rows on a genuinely bad upstream day. The leak is now
  visible; whether to fail closed is Don's call, and it is the single open question here.
* **Did not move `MIN_LIVE_DAYS`/`MIN_SHARPE_DAYS` onto elapsed time** — the flattering direction,
  explicitly out of scope in the register.
* **Did not fix the Yahoo quota ceiling.** The refusal screen cannot check 500 names against a
  free feed in one run. Bounding the screen to what the quota supports, or moving the valuation
  fetch to the paid FMP path, is a scoping decision for the screener/infra lane.

### BUGS FOUND (Part 14)

1. **The refusal screen is Yahoo-quota-bound and has been degrading silently since it shipped.**
   The 2026-08-08 production scan recorded **0 refusals across 500 served names** while its own
   rank-1 name refuses at 5.6x. A throttled fetch returns partial data rather than raising, so
   the screen reports a clean bill of health it never earned. **Now loud** (D3 + the probe
   distribution) but **not closed**. **Owner: screener/infra lane** — it needs either a smaller
   screen or a feed that can serve it.
2. **`publication.decide(None, price)` returns `publish=False` with an EMPTY reason**, so "we
   could not look" and "there is nothing to publish" are indistinguishable to every caller. The
   docstring says this is deliberate, and it is the mechanism by which a throttled name reaches
   the public list with an unchecked peer estimate. **Owner: engine lane** — a third state
   (`insufficient_data`) would let callers tell them apart.
3. **`_screen_refusals` excluded the DCF window from its own counter**, so the most-read rows on
   the site could not be counted as refused or errored. **FIXED here.**
4. **The DCF pass's fail-open left no trace of any kind** — no counter, no log, no key on the
   row. **FIXED here** (`dcf_error`, `dcf_probe`, `errors`, `error_tickers`).
5. **`index_track.summarize` annualised on row count**, inflating alpha ~3.9x and Sharpe ~1.9x at
   the observed recording rate. **FIXED here.** The module docstring's rule 2 and the UI string
   *"withheld until 60 trading days"* both described a guard measured in trading days while the
   guard was measured in rows — the sentence looked safe, which is why it survived.
6. **Carried forward, still open from Parts 12–13:** the served payload's `health` key is `null`,
   so `theme_coverage`, `theme_contributing` **and now `publication_audit`** reach nobody through
   the API — the LEAK banner is visible only in the scan log. **This one now matters more**, and
   it is the cheapest remaining win: exposing `health` would put the leak on a surface a human
   reads. **Owner: screener/web.**

### 14.9 FAIL CLOSED — Don's decision, 2026-08-11, and the evidence for it is our own measurement

**Decision: a row whose data could not be fetched this scan publishes NO fair value.** The ~5%
cost is accepted. The argument is not abstract — it is §14.1's table: failing open served peer
estimates of **88.69 against the model's own 42.25 (DB)** and **167.42 against 90.93 (CIB)**,
plus one name the model refuses outright. A peer estimate nobody checked is the
confident-wrong-number failure this project exists to prevent.

**THE TWO KINDS ARE NOW DIFFERENT CLAIMS, AND THEY RENDER DIFFERENTLY.** A new field
`fair_value_withheld_kind` carries `refused` or `unavailable`:

| kind | what it says | stability |
|---|---|---|
| `refused` | the model produced a number and the guard **rejected it** — a statement about the *valuation* | stable; it will say the same tomorrow |
| `unavailable` | the data could not be fetched, so the model **never had a view** — a statement about the *fetch* | **temporary; the next scan retries it automatically** |

The reason text says so in words — *"This is a temporary data problem, not a judgement about the
company — the next scan retries it automatically"* — and the UI renders `no data` (italic)
against `withheld`. A tooltip nobody hovers is not a distinction, so the badge itself differs,
and `test_the_ui_renders_the_two_kinds_differently` pins it against the shipped JS.

**The distinction survives the database.** `snapshot_rows` gains a `fair_value_withheld_kind`
column via the existing ALTER pattern; an older database reads as withheld-with-unspecified-kind
rather than losing the withholding. Without this the two would converge on the way to the
browser, which is exactly what the decision forbids.

**QUOTA DEGRADATION IS NOW A NUMBER.** `health.publication_audit` carries `withheld_no_data` and
`withheld_refused` on every scan. On 2026-08-08 the equivalent figure was invisible and the
screen reported zero refusals across 500 names it could not reach.

**THE MOP-UP STAYS OFF, and the constant stays with the record of why.** It was measured to make
things worse — `no_data` went **13 → 32** on the next full scan, because the binding constraint
is cumulative quota, not concurrency. Fail-closed costs **no extra requests at all**, which is
the second reason it is the better answer. `test_the_mopup_pass_is_OFF` fails if anyone wires it
back in.

**ONE DISCRIMINATOR HAD TO GET STRONGER, and an existing pin caught it.** The first cut judged
"did we look?" on `company.revenue` alone. `test_not_dcf_valuable_is_not_a_refusal` — which
exists because NVS, SAP and TD once had ordinary peer estimates of \$185.41, \$364.97 and
\$79.73 suppressed — uses a stub company with no `revenue` attribute, so revenue alone
mislabelled a legitimately-not-valuable name as unfetchable and blanked it. **The rule now also
accepts a stated DIAGNOSIS as proof we looked:** if the model can say *why* it cannot value a
name, it read the statements. A throttled fetch has nothing to say at all.

**D3 `unverified` is not redundant after this — its meaning sharpened.** The leak it detected is
now *prevented*, so it stays silent in the normal case and fires only if a `no_data` row ever
reaches the audit **unwithheld**, i.e. if fail-closed itself broke. Pinned both ways.

**48 tests in `tests/test_la1_la3.py`; full gate 42 suites, 0 failures.**


---

## Part 15 — WHY NONE OF PARTS 13 AND 14 HAD DEPLOYED: ONE F-STRING, AND THE VERSION CHECK THAT DID NOT CHECK THE VERSION (2026-08-11, greeks lane)

Parts 13 and 14 were finished, green and pushed. **They were also entirely undeployed**, and had
been for three pushes. The branch would not land, `main` took five other lanes past it, and the
gate was green locally every time it was asked. This part is the diagnosis, because the failure
mode is more reusable than the fix.

### 15.1 The fault

`scripts/live_theme_sources.py:776` contained an f-string that reused its own quote character
inside the expression:

    f'{k} {v['fetched']}+{v['done']}'

**PEP 701 legalised that in Python 3.12. On 3.11 it is a hard SyntaxError**, and
`.github/workflows/land-agent-branch.yml` pins `python-version: '3.11'`. This machine runs 3.13.

So the module could not be **imported** on the runner, and the suite that imports it —
`tests/test_live_theme_sources.py` — died at collection. **All 53 tests failed at once, for one
reason, and the reason was not in any of them.** Every other suite stayed green, which is why CI
named exactly one file and offered no further clue. The land step's `exit $fail` then did its job
and left `main` untouched.

**One character of quoting, in a progress log line, in a measured-only script that ships nothing.**
It blocked the KSPI publication leak fix, the fail-closed publication policy and the LA3
denominator repair from reaching production for a day.

### 15.2 Why my own pre-push check missed it, which is the part worth keeping

Before the earlier pushes I verified 3.11 compatibility with:

    ast.parse(src, feature_version=(3, 11))

**That argument is best-effort and does not gate tokenizer-level changes like PEP 701.** It
accepted the file without complaint. I then reported, in writing, that Python 3.11 syntax had been
ruled out — and it had not been. The check named a version it was not able to enforce.

**A version claim needs a compiler of that version.** The fix was to fetch the official 3.11.9
embeddable distribution (no install, no elevation) and compile against it. That took about two
minutes and settled in one command what three pushes and a lot of reasoning did not.

### 15.3 The guard, in two halves, because either alone is blind

Both live in `tests/test_live_theme_sources.py`:

| check | what it catches | where it fires |
|---|---|---|
| `compile()` every `.py` under the **running** interpreter | any construct, exhaustively | on CI, where the running interpreter **is** 3.11 — red with a file and a line instead of an unexplained import failure |
| tokenizer scan for the specific construct | PEP 701 quote reuse; backslash in an expression | **locally, before a push** — only 3.12+ can represent it, so this is the half that would have saved the three attempts |

`CI_PYTHON` is pinned to the workflow by a test, so bumping the runner cannot silently leave the
checks describing the old version.

### 15.4 The detector's rule was read off the compiler, not recalled — and its first cut was wrong

The rule is empirical. A table of eight constructs was run through real CPython 3.11.9 and the
verdicts recorded; the table is pinned **in both directions** (on 3.12+ it asserts the detector;
on 3.11 it asserts the table against that compiler).

**The first cut had two false positives on one correct line** — `fundamental_panel.py:4182`:

* it compared **first characters** rather than full delimiters, so a `'''`-delimited f-string
  containing a nested `'` was condemned. That is legal 3.11.
* it tracked **one** delimiter instead of a **stack**, so in `f"{(f'{y:.2f}')} {d['k']}"` the
  inner f-string's quote was still considered open and the outer one's `d['k']` was condemned.
  Also legal 3.11.

Both shapes are now rows in the fixture table. **This matters beyond tidiness: a repo-wide guard
that cries wolf on correct code is a guard every other lane learns to route around**, and it
would have been reported here as a finding about `fundamental_panel.py` that was purely my error.

### 15.5 What was verified, and what was not

* **390 files compile under real 3.11.9** — 0 failures, on the merged tree, including the other
  lane's newly landed `scripts/exit_rule.py` and `valuation/web/hold_horizon.py`.
* **57 of 58 tests in the suite pass under real 3.11.** The single error is `ModuleNotFoundError:
  numpy`, an artefact of the bare embeddable interpreter; `numpy>=1.24` is in `requirements.txt`,
  which CI installs.
* **Full gate on the merged tree: 45 suites, 0 failures.**
* **NOT verified: the Actions log itself.** I still cannot read it — no `gh`, no GitHub token.
  The diagnosis rests on reproducing the failure locally against a 3.11 compiler, which is
  stronger evidence than the log line would have been, but the causal chain to CI's specific
  run is inferred, not read.

### 15.6 The lesson, stated plainly

**"Green locally" and "green on the gate" are claims about different interpreters, and this
project had no check that knew the difference.** The repo's own standing rule — never silence a
check — has a sibling this session paid for: *never trust a check that cannot enforce what it
names.* `ast.parse(feature_version=...)` reads exactly like a version gate and is not one.

**BUGS FOUND (Part 15)**

* **`live_theme_sources.py:776` — 3.12-only f-string syntax on a 3.11 runner.** FIXED. Blocked
  every deploy from this lane for three pushes. Class-wide guard added.
* **No repo-wide check that the tree parses on the CI Python.** FIXED — two-part guard above.
  Note the tradeoff, recorded rather than hidden: the guard scans the **whole tree**, so another
  lane's 3.11-incompatible file will now redden **this** suite. That is deliberate — it is a
  repo-wide invariant and the message names the offending file and line — but it is a shared
  failure surface and the next lane to hit it should read this section rather than assume the
  suite is flaky.

---

## Part 16 — THE SCREENER BATCH: LA4, LA5, LA7, LA9, LA12, LA14 (2026-08-11, greeks lane)

Six small fixes, one branch. Every claim was verified against the code before anything moved
(RUN_RULES A8), and **the audit was right on all six** — including the one it marked HYPOTHESIS.
The measurements that verified them are the test fixtures, so each defect is pinned as a number
rather than as a description of one.

### 16.1 LA4 — the clock at the wrong end of a long operation

`scan_date = _today()` sat on the line that SAVES the snapshot: after the universe fetch, ~800
metric fetches, the DCF pass and a 500-name refusal screen, on a job the workflow allows 60
minutes. `_today()` is `date.today()` — the **runner's** local date, which on GitHub is UTC — and
`auto-scan.yml` fires a backup cron at **23:41 UTC, nineteen minutes before UTC midnight**. Any
backup run over nineteen minutes stamped the next calendar day.

**The audit's line cite had rotted**: it says `screen.py:328`; the call was at `:380`. CLAUDE.md's
own warning that line numbers here rot within days, demonstrated again.

**The damage was not only a wrong label.** `/admin/ingest-snapshot` keys idempotency on
`hot_processed_{scan_date}`, so two dates are two keys: the forward hot10 track recorded a
**second pick row for the same close** and the Discord digest **posted twice** — while the
workflow comment calls the backup "a no-op if the primary already landed".

Fixed by stamping once at the top. All three exits (including the two early returns, which each
called `_today()` separately) read that one stamp. Pinned by a fixture whose provider **advances
the clock during `get_universe`** — a fixture where no time passes cannot tell the two
implementations apart — plus an AST test that `run_scan` contains exactly one `_today()` call.

### 16.2 LA5 — the scan's own diagnostics reached nobody

The posted params carried only `scope` and `universe_size`; `health` and `filtered` were built,
printed to the Actions log, and dropped at the one boundary where they would persist.
`app.py:522-523` serves `params.get("health")` and `params.get("filtered")` — both null on every
served payload. Verified at **both** ends before changing either.

**This is the mechanism that made LA1 and LA6 invisible**, which is why a one-line diff is worth
more than its size. `refusal_screen` exists precisely so a silent zero is the tell that the
publication leak is back — and the 2026-08-08 scan duly reported **zero refusals across 500 names
it could not reach**, with nothing anywhere saying so.

Payload size was **checked, not assumed**: `filtered` is a reason→count dict with ≤8 example
tickers per reason; `health` is counts plus short ticker lists. A few KB beside ~500 scored rows.

### 16.3 LA7 — the guard that could not see, and a collision I created

Three defects, all measured first:

| | before | after |
|---|---|---|
| `status("2026-08-08")` (a **Saturday**) | `fresh` — *"As of 2026-08-08 (last close)."* | `warn`, `as_of_is_trading_day: False` |
| `status("2026-12-24" → 12-28)` | `age_trading_days: 2` | **1** |
| the stated justification | *"Holidays are not modelled — …far lower than the cost of crying wolf."* | corrected: not modelling them makes age **larger**, so the badge fires **earlier**. That **is** crying wolf. |

`is_trading_day` lived one import away and was never asked. This is what turned LA4's misdated
snapshot green, so it is load-bearing for the finding above it.

**A FOURTH DEFECT, AND IT WAS MINE.** `freshness.trading_days_between` and
`market_session.trading_days_between` had the **same name** in sibling modules and returned
**different answers** for the same interval (2 vs 1 over Christmas). The second was added by LA3
days earlier — **this batch created the collision it is now closing.** One calendar again, pinned.
A **third** copy remains at `scripts/theme_health.py:175` and is reported, not silently changed.

Deliberately **not** a new `level`: `app.js:1812-1815` switches on fresh/warn/stale/unknown and
treats stale and unknown as red. A misdated snapshot is not a dead pipeline, so it takes `warn` —
a visible note, not an alarm — and carries machine-readable `as_of_is_trading_day`. The one thing
it may never be is `fresh`.

### 16.4 LA9 — the hypothesis was TRUE, and settled without a run log

The audit asked for `gh run view`. **`gh` is not installed on this machine and there is no GitHub
token in `.env`**, so it was settled from the **workflow definition**, which is the authority on
what env a job receives; a log would only have shown the symptom.

The `hot` job passed `BASE_URL`, `ADMIN_TOKEN`, `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`,
`FMP_API_KEY`, `SEC_USER_AGENT` — and **not** `TRADIER_TOKEN` (the intraday job passes it). Both
`broker_universe.available()` and `broker_fundamentals.available()` are `bool(cfg.tradier_token)`,
so every scheduled hot scan fell back to the SEC EDGAR filer list — no price, no market cap, no
size ordering — truncated to `SCAN_LIMIT`, on the rate-limited free stack. The job's own comment
claims *"whole_market now resolves to the broker's liquidity-ranked universe (~7,100 listed
names…)"*. **That comment had been false since it was written.**

**PASSING THE TOKEN ALONE WOULD HAVE BEEN A QUIETER VERSION OF THE SAME BUG**, and this is the
part worth keeping: `CONFIG.tradier_env` defaults to `"sandbox"` (`config.py:53`) and
`broker_universe._base` routes sandbox traffic to `sandbox.tradier.com` — the job would have *had*
a broker and still not had the real universe. Both `TRADIER_TOKEN` and `TRADIER_ENV: live` are
now passed, matching intraday.

**Safety checked before adding a broker token to a job:** `providers.py` has no order or POST
path, the hot path is market data only, and `config.py:55-56` records that these fields are
deliberately **not** the paper broker's. Nothing on this path can place an order.

### 16.5 LA12 — two populations in one row

`/api/hotstocks` calls `sector_attractiveness(all_rows)` on rows straight from the database,
**before** `estimate_fair_values` has run — that runs only on the served slice. Only DCF'd names
carry an `upside`, and production runs `SCAN_DCF_TOP=12` over the whole market, so `_median`
(which drops Nones silently) returned a median over one or two names beside a `count` reporting
the entire sector.

Fixed by shipping `median_upside_n` beside it. **No floor was invented, deliberately** — a
threshold here would be an uncalibrated constant, whereas a denominator lets the reader apply
their own. **`count` was not changed**: it was never wrong, it was being read against a median
that meant something else, and "fixing" it would break the correct field to hide the symptom.

### 16.6 LA14 — a set containing a date outside the year it names

`market_holidays(2028)` contained `2027-12-31`; `market_holidays(2033)` contained `2032-12-31`.
**Dropping it is the factually correct NYSE rule, not tidiness**: the exchange does not close on
31 December when 1 January falls on a Saturday, so the holiday is not observed at all — and the
neighbouring year must not gain it either, which is checked. Inert for `is_trading_day` (which
asks `market_holidays(d.year)` and never saw the stray) and inert *correctly*; the exposure is to
any caller that **iterates** the set. Nothing does today — this closes the hole first.

The raw computation is split into `_holidays_unfiltered` so the filter is visible and testable,
and a test asserts the filter actually **removed** something. A guard that passes because it never
had anything to catch is not a guard.

### 16.7 NOT ONE OF THE SIX — the ledger parser can silently lose a row

Found by walking into it. My LA7 note contained the literal `fresh|warn|stale|unknown`, which
split the row into 15 cells against a 10-column header. **The row vanished** — `read_ledger()`
returned 177 rows without it and every "is LA7 done?" query answered no. Escaping as `\|` fixed
the markdown **render** and **not** this parser, so the row stayed invisible while looking correct
in the file. The text has to be pipe-free.

**The silent drop was the smaller half.** `main()` re-renders the table from `read_ledger()` and
preserves out-of-band rows via `extra = [k for k in existing …]` — so a row it cannot see is not
in `existing`, not in `rows`, not in `order`, and is **DELETED by the next `--write`.** The
comment a few lines below in that same function records `--write` having already deleted every
out-of-band row once before. This is the same failure one layer lower.

Same family as the `RESEARCH_LOG.md` pipe hazard, **fixed in that parser in session 12 and never
here** — two registers, one lesson, applied to one of them.

`read_ledger` now records unreadable rows and `--write` **fails closed** naming them. The
discriminator is **too many** cells (a data row that was split), not merely "wrong count": this
document also holds a 7-column series summary and a 3-column key, and flagging those would make
the guard fire constantly, which is how a warning stops being read.

**THREE ROWS ARE CURRENTLY INVISIBLE AND WOULD HAVE BEEN DELETED: `S23` (line 268, 12 cells),
`M1-PARSE` (341, 13) and `V2G` (360, 12).** None are mine. They are **reported, not rewritten** —
the register forbids editing another lane's row — so their owners should remove the stray `|`.
Until then `--write` refuses, which is strictly safer than the status quo, where it deleted them
without a word. A test fails if a **fourth** appears.

### 16.8 What I did NOT do

* **I did not read the Actions log for LA9.** No `gh`, no token. LA9 is settled from the workflow
  definition instead, which is stronger for the question asked ("does this job get the token?")
  but does **not** measure the runtime consequence — how much the universe actually improves with
  the broker attached is unmeasured, and the next scheduled scan is the first observation of it.
* **I did not fix the three malformed ledger rows.** Reported instead, per the register.
* **I did not consolidate `scripts/theme_health.py:175`**, the third trading-day calendar.
* **I did not verify LA4's fix end-to-end against a real backup-cron run** — that needs a run that
  crosses 23:41 UTC. The arithmetic and the unit fixture are pinned; the production observation is
  the next backup cron.

**35 new tests in `tests/test_la_screener_batch.py`; full gate 46 suites, 0 failures.**

**BUGS FOUND (Part 16)**

* **LA4** snapshot stamped after the scan → next-day dates, duplicate track rows, duplicate
  Discord digest. FIXED.
* **LA5** `health` and `filtered` dropped in transit. FIXED.
* **LA7** freshness endorsed non-trading-day dates; counted holidays; docstring backwards. FIXED.
* **LA7b** two `trading_days_between` functions, same name, different answers — **introduced by
  this lane's own LA3 work**. FIXED. A third copy remains at `theme_health.py:175`, reported.
* **LA9** the scheduled hot scan ran with no broker token; passing the token alone would have
  pointed it at the sandbox. FIXED (token + env).
* **LA12** `median_upside` over a stale subset beside a full-sector `count`. FIXED.
* **LA14** `market_holidays(y)` could contain a date in `y-1`. FIXED.
* **NEW** `build_ledger.read_ledger` silently dropped unparseable rows and `--write` would delete
  them; three rows (`S23`, `M1-PARSE`, `V2G`) are affected today. Guard added; rows reported, not
  rewritten.
