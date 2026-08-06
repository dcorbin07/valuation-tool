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
