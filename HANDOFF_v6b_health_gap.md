# HANDOFF — V6-B's health classification: panel vs live (2026-08-16, infra lane)

**Read-only pass. Nothing was fixed, nothing adopted, no file under `valuation/` changed.**
Zero trials — every statement here is a fact about what the shipped code can do, measured
against the shipped predicates, with no hypothesis and no threshold. Equity `N` stays **224**.

Prompted by the `V6B-PERNAME` ledger row's own sentence: *"a listed name can essentially never
be UNHEALTHY."* The question asked was whether the live screen is therefore applying the
condition M1 measured.

---

## 0. The answer in four lines

1. **The premise is confirmed and it is stronger than "essentially".** On the panel the
   classifier splits 73.19% unhealthy; on the live screen the unhealthy class is reachable at
   **exactly one value of `z_quality` — 0.0 — and nowhere else.**
2. **The mechanism is an upstream filter, not delisting.** The screen's own prefilter removes
   M1's entire unhealthy side *before* the classifier sees it, and the health clause is
   unreachable because the listing floor (66) sits above M1's floor (50).
3. **The served statistic measures what it claims**, because the payload's own `METHOD_NOTE`
   already frames it as a membership verification and says the unhealthy figure "describes
   companies this screen does not show".
4. **But there is no displayed statistic at all.** `renderDip` in `static/app.js` never reads
   `dip_risk`. The field, its class, its rate, its method note and its "not a probability"
   caveat are **served on `/api/dip` and rendered nowhere.** That is the finding to route.

---

## 1. What was measured, and how

Everything below runs the **shipped** predicates — `dip.prefilter_ok`, `dip.health_check`,
`dip.screen`, `dip_risk.classify` — rather than a retyped copy, so it measures the product and
not a paraphrase of it.

**The two floor sets, read from the modules:**

| | live listing (`dip.py`) | M1 classification (`dip_risk.py`) |
|---|---|---|
| quality | `z_quality >= 0.0` (prefilter) **and** 0–100 `quality >= 66` | `z_quality > 0.0` — **strict** |
| financial health | 0–100 `health >= 66` | `health >= 50.0` — **inclusive** |
| growth | 0–100 `growth >= 66` | not used |
| depth | default 20%, slider 10–40% | measured at 20% |

**Note the two "quality" objects are different variables.** The listing gate's `quality` is an
engine 0–100 sub-score; M1's is `z_quality`, a cross-sectional theme z-score. They are not the
same measurement and the prefilter is the only place `z_quality` is tested.

---

## 2. The panel side — the classifier does discriminate, roughly 1 : 2.7

From `dip_risk.N_ROWS`, transcribed from `V6B_DIP_SURVIVAL.json` and pinned to the measurement
script:

| class | rows | share | forward-fall rate |
|---|---|---|---|
| healthy | 9,924 | **26.81%** | 0.3251 |
| unhealthy | 27,090 | **73.19%** | 0.4335 |
| total | 37,014 | | |

On the population M1 measured, **nearly three quarters of dipped names are unhealthy.** That is
what makes the 10.8pp separation a real comparison there.

---

## 3. The live side — the reachable set is a single point

Swept through `dip.screen` end to end with sub-scores held comfortably over every listing floor:

```
  z_quality=-1.0       lists=False
  z_quality=-1e-06     lists=False
  z_quality=-5e-324    lists=False        <- smallest representable negative
  z_quality=0.0        lists=True   class=unhealthy
  z_quality=5e-324     lists=True   class=healthy   <- smallest representable positive
  z_quality=1e-06      lists=True   class=healthy
  z_quality=0.5        lists=True   class=healthy
  z_quality MISSING    lists=True   class=None      (unclassified, no rate attached)
```

**The unhealthy class occupies exactly `{0.0}`** — a single point in a continuous standardised
score. It is not rare; it is measure-zero up to floating-point representation.

**A caution about counting this.** A first cut of the sweep counted *combinations* on a
hand-chosen grid and reported "16.67% unhealthy". That is an artifact of the grid giving `0.0`
the same weight as every other probe value. **It is not a rate and must not be quoted as one** —
the honest object is the reachable set, not a share of an invented grid.

---

## 4. The mechanism — two independent legs, and only one of them is load-bearing

**Leg 1 — the health clause is unreachable, permanently.** A name lists only at
`health >= 66`; M1 calls it unhealthy on health only below **50**. `66 > 50`, so **every listed
name clears M1's health clause with 16 points to spare.** This leg cannot fail without someone
lowering the listing floor below 50.

**Leg 2 — the quality clause is removed by the prefilter, and this is the interesting one.**
The *real* gate, `health_check`, **never sees `z_quality`** — it takes the 0–100 sub-score dict.
Measured:

```
  z_quality=-1.5   health_check(subs all 70)=True   prefilter=False   M1 class=unhealthy
  z_quality=-0.5   health_check(subs all 70)=True   prefilter=False   M1 class=unhealthy
```

**A name with every sub-score comfortably above every listing floor, and a below-average quality
z-score, is UNHEALTHY under M1 and is kept off the page by the prefilter alone** — a component
whose own docstring reads *"THIS IS NOT THE HEALTH GATE AND MUST NEVER BE DESCRIBED AS ONE. It
is a budget-saver."*

**Reported, and then withdrawn as a risk, because it is already guarded.** The obvious worry is
that a semantic property rests on a performance optimisation, so a future change that makes
valuations cheap enough to drop the prefilter would silently start listing genuinely unhealthy
names. `tests/test_dip_risk.py::test_a_listed_name_can_essentially_never_be_classified_unhealthy`
already covers it, and covers it *well*: it asserts the floor relations **and** sweeps through
`dip.screen` end to end, so removing the prefilter at the call site fails the suite rather than
only re-flooring it. It is vacuity-checked from both sides. **No action needed on this leg.**

**Answering the three mechanisms the flag proposed:** an **upstream junk filter** — yes, this is
it, and it is the binding one. **Different floor definitions** — yes, partly: 66 vs 50, plus two
different "quality" variables. **Delisting** — no; it plays no part.

---

## 5. Does the tab's displayed statistic measure what it claims?

**There is no displayed statistic.** Traced end to end:

* `dip.py:389` attaches `dip_risk` to every row; `:417` attaches the summary block.
* `dip_risk.py:410-411` puts `method_note` and `not_a_probability` in that block.
* `grep -c dip_risk valuation/web/static/app.js` → **0**. `renderDip` builds the table from
  `ticker, drawdown, price, high_52w, health chips, fair_value, checks` and **never reads
  `dip_risk`**.
* Repo-wide, `dip_risk` is imported by exactly one module: `dip.py`. No template, no JS.

So the class, the 32.5% rate, the 43.4% baseline, the method note and the "not a probability"
caveat are **served on `/api/dip` and displayed to nobody.**

**As served, the statistic is honest.** `METHOD_NOTE` states that M1's health bar is *"a lower
bar than the one this screen lists on, so a name that appears here has in practice already
cleared it"*, and that *"the unhealthy figure describes companies this screen does not show"*.
That is exactly right, and it is the correct framing given §3 and §4: the field is a
**verification that a listed row is inside the measured group**, not a discriminator between two
groups on this surface.

**The gap worth naming.** `dip_risk.rendered_text` exists, by its own docstring, so the
banned-phrasing rule can be asserted against *"what is SERVED rather than against this file"* —
invoking V4's lesson that **rendering is where copy leaks**. Here the payload is served and the
page renders none of it, so the guard passes over copy no reader can see. The careful wording
was written to protect a reader who does not currently receive it.

---

## 6. Routed to the owning lane (greeks / app), with no fix attempted

1. **Decide whether the per-name field is meant to be visible.** If yes, `renderDip` needs to
   read `r.dip_risk` and — this is the substantive constraint — must render the **method note or
   an equivalent** alongside any rate. A bare "32.5%" chip beside a list of names would be the
   one presentation §3 and §4 do not support, because it invites reading the screen as having
   done the separating when the prefilter did it upstream.
2. **If it is deliberately payload-only, say so** in the module docstring, so the next reader
   does not conclude the UI dropped it by accident.
3. **`V6B-PERNAME`'s ledger row reads "SHIPPED 2026-08-16 — display only".** In context that
   means *"affects display only, adopts nothing"*, which is true. It could be misread as *"it is
   displayed"*, which is not. Worth one clarifying clause.

**Explicitly not recommended:** loosening the prefilter or the 66 floors to make the field
discriminate. The screen's job is to list healthy names; a gate chosen to make a display
statistic look more informative would be the tail wagging the dog, and it would change what the
screen *is* in order to decorate a number.

---

## 7. What this pass did not do

No file under `valuation/` was touched, no test was added or changed, and no verdict was
re-measured — the panel figures are read from the pinned constants, not recomputed.

**The live universe's `z_quality` distribution was not measured, and is deliberately not
quoted.** The local scan archive is entirely synthetic test output, so it cannot answer a
question about the served universe; `/api/hotstocks` returns the *ranked* list rather than the
scanned universe, and the one reading taken through a summarising fetch was internally
inconsistent (it reported both 44 and 45 rows above zero, and described a value of 0.0002 as
"effectively 0" — which is exactly the distinction §3 turns on). **None of it is quoted as a
measurement.** It is not needed: the reachable-set result in §3 is a property of the gates and is
established exhaustively over them.
