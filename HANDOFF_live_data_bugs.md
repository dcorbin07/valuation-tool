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
