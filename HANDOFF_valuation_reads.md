# HANDOFF — `VALREADS` — the valuation page's reads, recorded forward, test registered first

**2026-10-13, r1 lane.** `ZERO TRIALS` — `by_domain` is bit-identical across the log append
(equity **297**, options **319**, infra **20**). **ADOPTS NOTHING, READS NO VERDICT, CHANGES NO
PUBLIC SURFACE, AND NO ROW OF THE RECORD EXISTS YET.** Fifteen equity trials are pre-committed and
charged at the read, not now.

Register: `PREREG_valuation_reads.md`, committed **ALONE** at `5aa1ac0`, markdown only, zero
`.py`, 358 lines. Amendment 1 committed **ALONE** at `6b086c0`, markdown only. Recorder at
`f89ea47`. **The ancestry is asserted against git by test rather than claimed** — the register's
FIRST commit must be a strict ancestor of the recorder's, every commit touching the register must
be markdown-only, and they may never share a commit.

---

## 1. What this is, and why it had to be a recording decision

The valuation page's Buy / Hold / Reduce labels were never tested against returns and are now gone
(`DECISIONS.md`, "The valuation page"). Item 52 replaced them with **business quality**, **price vs
our model**, **what the price assumes** and a **DCF warning**. Those will not be tested either
unless they are recorded as served, and **they cannot be rebuilt backwards** — `V6` established
the live sub-scores are not computable point-in-time, and `S23` measured that path fetching **live
Yahoo prices to value 1999**, so a backfill would be a different number wearing an old date.

**And the archive this project already has cannot stand in.** `archive.archive_scan` keeps the top
100 hot names a day and **none of these reads**. NVDA — item 52's own worked example — sits at hot
rank 1,262, so the archive is silent about the single name the handoff reasons from.

---

## 2. The five reads, and every sign declared before any row

| id | read | type | DECLARED SIGN |
|---|---|---|---|
| `R1-BQ` | `business_quality_score` 0–100 | continuous | **POSITIVE** |
| `R2-PVM` | `price / base_fv − 1` | continuous | **NEGATIVE** |
| `R3-PIG` | the reverse-DCF implied growth | continuous | **NEGATIVE** |
| `R4-GAP` | implied growth − the business's own last-year growth | continuous | **NEGATIVE** |
| `R5-WARN` | the DCF warning flag, and which rule fired | **binary** | **NEGATIVE** |

**`R1-BQ` is disqualified in advance from being a finding about quality.** `business_quality` is a
weighted mean of the four `BUSINESS_SUBSCORES`, so a positive result would be a finding about **the
aggregation and the page's 0–100 band labels** — never a new finding that quality predicts returns,
which this project measured on the panel at theme IC *t* **+3.10**. The five sub-scores are
**recorded** and are **NOT registered arms**; they are the power control.

**`R5-WARN` is scored as a per-date mean-return difference, not an IC**, because a rank IC on a
two-valued flag is a point-biserial whose magnitude is a function of the base rate and would not be
comparable with the other four cells. **Which rule fired is recorded per name** — item 52's own
words are that `STORY_GAP_PP = 15.0` *"is a disclosure threshold and is calibrated against
nothing"*, so the trigger list is the only thing that would let a successor tell a real signal from
one rule carrying all of it. **No per-rule arm is registered and none may be read.**

---

## 3. The population is a UNION, and that is a measurement rather than a preference

`GET /api/hotstocks?top=500` ∪ `GET /api/valquo-index`, both **public and tokenless**.

**Measured before the rule was written down** (`data/free_analysis/VALREADS_COST.json`): the hot
route **caps at 500 rows whatever `top` asks for**; the Index carries **86** positions; and **only
44 of those 86 are inside the hot 500 — 42 are outside.** Union **542**.

**So a hot-list-only population would have omitted half of the product's own book** — the one
population a forward record of the valuation page's reads must certainly contain.

**THE COST THAT FORCED A POPULATION RATHER THAN THE WHOLE SCAN, measured first as the task
required.** One `pipeline.value_ticker`: **1.83 s** mean per name over a 12-name paced probe
(median 1.44 s, max 4.25 s; a second 6-name pass read 2.28 s), **one company fetch per name**, no
options chain, no AI call, no forward return. At 1.5 s pacing the union is **≈ 34 minutes** a week
and the scan's full ~1,500-name universe would be **≈ 83 minutes** — against a hot scan that
already needs most of a 90-minute budget. **The union is affordable weekly; the full universe is
not, on a free runner.**

**The RULE is frozen; the COUNT may move.** The cap is a server-side constant this lane does not
own and the Index rebalances, so the recorder stamps `n_hot`, `n_index`, `n_index_outside_hot` and
`n_population` on **every manifest row** — a cap change shows up in the record rather than silently
shrinking the population. **Changing the rule voids the item.**

---

## 4. POWER — the part the task asked for, and it is uncomfortable

Derived with `valuation/edge/power_gate.py` (never retyped — `MA5`) from a **measured** dispersion:
`scripts/valreads_power.py`, `data/free_analysis/VALREADS_POWER.json`.

Per-date Spearman IC against `fwd_ret` on the corrected 9,645-name panel, 69 dates: `quality`
**+0.0695** at sd 0.0872, `growth` +0.0110 / 0.0592, `momentum` +0.0417 / 0.1302, `value` +0.0547 /
0.1116, `size` −0.0703 / 0.0941. Re-scaled to 542 names — `sd² = true_var + 1/(N−1)`, so the
N-independent part carries over and the sampling term is added back at the recorder's own size —
the five give **0.0715 to 0.1362**, midpoint **0.1038**.

**The effect worth detecting is this project's own best measured read, +0.0695**, not one chosen to
flatter the design.

| horizon | 80% power at the placebo-class bar 2.0 | at X7's theme-IC floor 2.7072 | at the HLZ hurdle 3.3745 |
|---|---|---|---|
| 3 months | **4.6 years** | 7.1 | 10.0 |
| 6 months | **9.1 years** | 14.1 | 19.9 |
| 12 months | **18.1 years** | 28.2 | 39.7 |

> MDE at |t| > 2.0000: detection threshold **0.0464** (50% power); **0.0659** at 80% power.
> **Power against a quality-like read of 0.0695 is 84.0%.**
> At |t| > 3.3745 (N = 297): **0.0783** / **0.0978**, power **35.2%**.

**THE HONEST STATEMENT.** The 3-month cells are powered at the first read **and only just** — 4.6
years of recording against a read at 5.0, no slack, so a year of missed weeks pushes it out. The
6-month cells are not powered until about year 9 and are read at year 10. **THE 12-MONTH CELLS DO
NOT REACH 80% POWER UNTIL ABOUT 2044, and not until about 2066 if the HLZ hurdle were gated on** —
they are read at year 10 at roughly **55%** power and the register says so now, so a 12-month null
in 2036 will mean *"this design could not see it"* and may not be reported as anything stronger.
At a smaller true effect every date moves out **quadratically**: at an IC of 0.035 the 3-month cell
needs roughly **18 years**.

**That is a finding, not a reason to skip.** The alternative is not a cheaper test — it is **no
test, ever**, because these reads cannot be rebuilt backwards.

---

## 5. The schedule — each cell read EXACTLY ONCE, and the dates are DERIVED

`INCEPTION` is the first recorded row's date and is stamped **in the record**. Every date is
derived from it and **must never be quoted from a document** — this project reset a five-year clock
three times in four days and recorded a hard-coded vintage date rotting within days (`PT-GAPDUE`).

* `INCEPTION + 1,826 days` (5y): the five **3-month** cells — **5 equity trials**.
* `INCEPTION + 3,653 days` (10y): the ten **6-** and **12-month** cells — **10 equity trials**.

Nothing read before its date; nothing re-read. **Why the split rather than all at five years:**
because at five years the 6- and 12-month cells cannot resolve, and reading them then would report
a design's blindness as a finding.

---

## 6. The bars, each shipping with its own limit

All four required; anything else is a **NULL**.

1. **Each read's own within-date permutation p95**, 500 draws, computed at verdict time from the
   record's own rows, one-sided in the declared direction. **Its limit: a within-date permutation
   has NO MEMORY** — `MB21` measured −0.0016 against a real composite's 0.5677 — so it cannot
   price the overlap artefact at long horizons, and the NW lag is the only correction.
   **No floor may be borrowed** from `2.2837` / `2.0540` / `2.7072` / `19.667%`: those are
   quarterly full-universe decile-book figures.
2. **Benjamini–Hochberg at q = 0.10** across the cells read that date, through
   `statistics.benjamini_hochberg` (`R4`'s one definition). **Its limit: the cells are correlated**
   — `R4-GAP = R3-PIG − business growth` by construction, `R1-BQ` is built from the sub-scores, and
   `SELRULE` measured 16 co-moving draws to be worth **2 to 4**, so the effective count is nearer
   five than fifteen.
3. **The both-halves rule**, same sign throughout. **Its cost is stated now:** a half carries
   `n_eff ≈ 9.5`, whose own 80%-power MDE is about **0.096** — larger than the effect being
   hunted — so a cell can clear the full span and fail a half, **and that is a NULL, not a
   near-miss** (`RUN_RULES` A6).
4. **The HLZ hurdle is REPORTED beside every cell and is not gated**, for `R4`'s own measured
   reason: HLZ prices the **best of N draws**, and these five reads are what the page already
   serves. §6 states what gating on it would cost, so a successor cannot claim it was a
   convenience.

---

## 7. TWO DEFECTS CAUGHT BEFORE A SINGLE ROW EXISTS

### (a) Amendment 1 — in my own register, and it is the wrong-object family again

§1 sourced `R3-PIG` from `price_assumes` → `implied`. Measured in the source while building
against it: when `is_financial` is true that function takes a **deliberate separate branch** — its
own comment says *"a bank's value is not a discounted free-cash-flow stream, so 'what growth does
the price assume' is the wrong question and the honest one is what return on equity it has to
earn"* — and returns an **implied return on equity** under the same key.

So one column would have held a growth rate **and** an ROE, and any rank IC on it would have been
**mixing two quantities** — computing cleanly, raising nothing. That is the wrong-object family
this project has recorded at least six times (`MB18`'s column literally called `gap`, `D6`'s
`long_short_tstat_hac`, `E-5`'s stranded `MA28_CARD` path, `W-1`'s `W1_FLOORS.json`, `U2`'s
`term_slope_60_30`, `MA47`'s ticker count read as ticker identity).

**`R3-PIG` and `R4-GAP` are scoped to non-financials; the ROE gets its own column carrying NO
arm.** It is not a rare branch — the smoke test found a financial among the first four hot names
(`ABCB`, blend method *"justified P/B from ROE"*). The power statement is therefore **optimistic by
the financial share** on those two reads, which is **not yet measured** and will be reported at the
first read from the record's own `regime` column; the direction is named rather than estimated — a
smaller cross-section raises `sd(IC)`, so both cells resolve **later** than §4 says, not sooner.

**Committed ALONE, markdown only, before the first row**, which is the only condition under which
this project permits an amendment (`W-1` Amendment 1, `W-28` Amendments 1 and 2 were all made
before any outcome existed). The original §1 is left standing, unedited.

### (b) REPORTED OUTSIDE THIS LANE (`RUN_RULES` rule 3) — the page's financial read never renders

**`valuation/web/app.py:369` reads `result.financial_extras`, which does not exist on
`ValuationResult`.** The field is `financial_surfaces` (`pipeline.py:123`), and it **does** carry
`reverse.implied_roe`.

**Consequence, measured:** for every financial `implied_roe` is always `None`, `price_assumes`
takes its `available: False` branch, and the page renders *"We could not work out what return on
equity this price assumes, so there is no implied read to show"* on **every bank, always** — while
the engine has the number sitting there (`ABCB`: **0.1220**, against a book ROE of 0.1011).

**NOT FIXED.** `app.py` is the app lane's file, and changing what the page renders is a public-copy
change this lane is explicitly barred from. **The recorder reads the correct field** and also
records `page_implied_available`, so the record carries the engine's figure **and** whether the
page showed anything — two different facts, and collapsing them would hide the defect. **One token
for the app lane: `financial_extras` → `financial_surfaces`.** (Note `app.py` also passes `cd.roe`
as the book ROE, which is `None` on `ABCB`; `reverse.current_roe` is the engine's own measured one.)

---

## 8. The recorder's shape, and why

**One file per week plus an append-only manifest, and the reason is COST rather than taste.**
`append_only.append` rewrites the whole file per row, so 542 rows a week into one growing CSV is
quadratic and reaches ~141,000 rows by the first read date. Each week's rows land in their own
**immutable** file — a week already on disk is **REFUSED**, not replaced, because a record whose
past can be rewritten is not evidence — and the **manifest** goes through
`append_only.append(key="date", append_only=True)`, inheriting this project's byte-prefix
guarantee, idempotent retry and backfill refusal **with nothing re-implemented** (`B7`).

**A refusal is a RECORD, never a blank.** `archive.py` is this project's own account of the
opposite: it stored `fair_value` but neither the refusal flag nor its reason, so a permanent
archive could not tell *"we declined to value this"* from *"we never tried"*. Three row states:
`OK`, `PARTIAL`, `REFUSED`.

**The canary refuses the WHOLE WEEK.** The vendor quota **does not raise when exhausted — it
silently empties `CompanyData`** (measured 2026-08-07: 302 of 403 names with `beta=None`, the tell
being many names reporting one identical WACC as it collapses to pure cost of debt). A degraded
week would be **fast, complete-looking and wrong**, so one known name is valued first and a
degraded answer aborts before a row is written, with the refusal **dated** in its own log — keyed
on the attempt's timestamp and **not** on the week, so a quota that resets leaves the week
recordable instead of turning the retry into an idempotent no-op.

**`data_export/` and not `data/`.** `data/` is gitignored, and this project has twice lost an
artifact to a directory that did not survive (`MA28_CARD.json`, `I2_BURN_IN_CENSUS.json`).
`data_export/` is where the forward Index record is already backed up, so the backup route exists
rather than being invented.

**A smoke test is BARRED from entering the record** — `--limit` computes and refuses to write.

---

## 9. Day-one self-check — six cases, every one mutation-tested

`python -m scripts.valreads_record --selfcheck` → **6 of 6**, artifact at
`data_export/valreads/VALREADS_SELFCHECK.json`. **The recorder refuses while it is ABSENT, STALE or
FAILING — three states, not one**, because "never ran" and "ran and failed" are different facts.
It runs in a **temporary tree**: a self-check that writes into the record it checks is `S3-I1`'s
own defect.

1. **A row round-trips unchanged** — 39 fields compared, 0 moved.
2. **A refused valuation records as REFUSED with its reason**, never as a blank.
3. **Nothing reads a forward return** — over the **syntax tree**, because the module's docstring
   states the rule and so contains the words a substring ban would look for.
4. **The append-only byte prefix holds**, a backward week is refused, a retry is a no-op.
5. **A recorded week is refused, not rewritten** — and the original bytes verified unchanged.
6. **The canary and mid-run degradation both refuse**, and a healthy canary and a healthy week
   both pass.

**Five of the six are MUTATION-TESTED** — each shown to **FAIL** against a deliberately broken
recorder, with the source restored **byte-for-byte and the restoration asserted** (`W-1`'s harness
rewrote a CRLF source as LF and failed its own byte check *after* the mutation had run; **a
mutation harness that cannot put a file back is worse than none**). Six passes prove nothing until
each can fail — `MB21`'s `C1` scored a perfect 0.000e+00 by comparing nothing.

**AND MY OWN GUARD FIRED ON MY OWN PROSE, IN THE FILE THAT WARNS ABOUT IT.** The
threshold-retyping test banned the substring `"STORY_GAP_PP ="` and **failed against the CORRECT
tree**, because the recorder's comment quotes item 52 saying that constant is a disclosure
threshold calibrated against nothing. **Eighth instance of the substring-ban family here**, and it
was committed with the warning in view. Repaired with an AST check on module-level assignment plus
a positive control proving the narrowed rule still bites.

**48 tests, exit 0.** Live smoke test: **8 of 8** names OK, population **542** confirmed against
the live routes.

---

## 10. For Don — one double-click

**`data/pending_workflows/valreads-record.yml` is staged** (via the tracked source at
`scripts/workflows/valreads-record.yml`, deployed with `scripts/propose_workflow.py` — `.github/`
is refused to lanes, and `data/` is gitignored so the pending copy can never be the tracked copy of
itself, which is item 44's reasoning reused).

1. **double-click `install_workflows.bat`**
2. GitHub → Actions → **valreads-record** → optionally *Run workflow* with `smoke = 8` to watch it
   once before the Sunday schedule picks it up.

**Sunday 07:11 UTC**, offset from `track-backup.yml`'s 06:17 so the two do not contend for the same
per-IP quota in the same minute. **90-minute timeout** against a measured ~34-minute run. **No
secret, no paid cron** — both routes are public and tokenless. It runs the self-check first, the
suite before the commit, and verifies the append-only byte prefix **against git** before committing
into `data_export/valreads/`. A missed Sunday is a **missing week**, recorded as missing and never
backfilled.

---

## 11. Not done, named so it is not mistaken for done

* **No verdict is read and nothing is adopted.** No cell has a value, because no row exists. The
  first verdict read is five years after the first recorded row.
* **No public surface changed by this lane.** The `app.py` defect of §7(b) is **reported**, and one
  token of it belongs to the app lane.
* **The five sub-scores are recorded and are NOT registered arms.**
* **No per-rule `R5-WARN` arm, no sector cut, no regime cut, no cap-tier cut.** Those are new
  hypotheses and need their own register.
* **`STORY_GAP_PP = 15.0` is calibrated by nothing, here or anywhere.** Recording which rule fired
  is what would let a successor calibrate it, and **that successor is not proposed.**
* **The financial share of the population is not yet measured**, so §4's power figures are
  optimistic on `R3-PIG` and `R4-GAP` by an amount the first read will report.
* **Nothing has been scheduled by this lane** — the workflow is PENDING, and that is deliberate:
  `.github/` is Don's door.
