# WRDS CENSUS — what THIS account can actually reach

**Measured 2026-08-24. Zero trials — facts about what exists, not a research result.**
Account: the `WRDS_USERNAME` in `.env` (never printed; credentials are materialised into libpq's
pgpass file programmatically and nothing in this lane returns a password).

Reproduce: `python -m scripts.wrds_census` → `WRDS_CENSUS.md` + `D:\wrds\WRDS_CENSUS.json`.
Raw payload lives under **`D:\wrds`** (sibling of `D:\thetadata`) and **is never committed,
never mirrored into the repo, and never rendered on a public surface.** What leaves this lane is
derived statistics: row counts, spans, byte sizes, sha256.

---

## THE HEADLINE: THE BIGGEST ITEM ON THE PULL PLAN IS NOT AVAILABLE

**OptionMetrics IvyDB — priority (a), described in the brief as "the single biggest upgrade
available" — is NOT ENTITLED on this account.** It exists in the catalogue only as the WRDS
*sample*:

| what we hoped for | what is actually there |
|---|---|
| `optionm` / `optionm_all` — IvyDB back to 1996 | **absent from this account's catalogue** |
| standardised surfaces, greeks, 1996→present | `optionmsamp_us` — **12 tables, year-suffixed 2014** |
| | `vsurfd2014`, `opprcd2014`, `stdopd2014`, `hvold2014` |
| | span **2014-03-03 → 2014-03-14 — TEN TRADING DAYS** |
| | `vsurfd2014` holds **2,600 rows**; `opprcd2014` **36,786** |

**The table names are the proof.** A production IvyDB library is not suffixed with a single
year, and a surface file covering 1996–2026 does not contain 2,600 rows. This is a demonstration
extract.

**Nothing was pulled from it**, and that is the correct outcome rather than a shortfall: ten days
of 2014 cannot support any question our own 2016+ ThetaData cache cannot already answer better.

### What entitlement WOULD have re-opened — stated because it is the case for buying it

Recorded so the value is legible if Don ever prices the subscription, and so nobody re-derives
it. **All of this remains CLOSED, not deferred-with-a-plan:**

* **A pre-2016 options history at all.** Our chain store starts 2016 and the ThetaData Pro window
  closed 2026-09-01. IvyDB reaches 1996, which is the only route to the 2000-02 and 2008 regimes —
  the two the options book has never seen. `B-13`'s alert-density regime register and every
  "does this survive a crisis" question are gated on exactly that.
* **Standardised surfaces.** `stdopd` gives fixed 30/60/91-day constant-maturity points, which is
  what makes an IV level comparable across names and dates without re-fitting a smile per
  cross-section. `O6`'s smile machinery exists because we do not have this.
* **Vendor greeks and IV on one methodology**, removing the `blackscholes.py`-vs-vendor
  reconciliation that `O2` closed by choosing an implementation.
* **`I-1`'s RND instrument** would gain a 20-year backdrop instead of a 10-year one.

**It does not unblock the tenor axis** — that was Tier E's job and it is already banked.

---

## ENTITLEMENT, MEASURED PER TABLE

A library appearing in `list_libraries()` is **not** evidence of entitlement — the catalogue is
broader than the grant, and **221 libraries are visible** to this account. Every target below was
probed with a real `SELECT`. Five states, and the distinctions matter: `DENIED` means the table
exists and we may not read it; `ABSENT` means it is not there under that name; `EMPTY` means we
read it and it holds nothing. A plan that confuses them wastes a window.

| priority | product | status | span | rows |
|---|---|---|---|---|
| **b** | `ibes.det_epsus` — detail estimates | **ENTITLED** | 1980-01-28 → 2026-05-14 | **34,540,574** |
| **b** | `ibes.detu_epsus` — detail, unadjusted | **ENTITLED** | 1980-01-28 → 2026-05-14 | 34,523,713 |
| **b** | `ibes.statsum_epsus` — summary | **ENTITLED** | 1976-01-15 → 2026-05-14 | 15,029,492 |
| **b** | `ibes.actu_epsus` — actuals | **ENTITLED** | 1976-01-15 → 2026-05-14 | 1,323,271 |
| **b** | `ibes.id` — identifier bridge | **ENTITLED** | — | 308,801 |
| b | `ibes.det_guidance` | **DENIED** | — | — |
| **c** | `crsp_a_stock.dsedelist` — delisting returns | **ENTITLED** | 1926-02-24 → 2024-12-31 | **38,872** |
| **c** | `crsp_a_stock.msedelist` | **ENTITLED** | 1926-02-24 → 2024-12-31 | 38,843 |
| **c** | `crsp_a_stock.dsenames` — name history | **ENTITLED** | — | 117,859 |
| c | `crsp_a_stock.dsf` — daily stock file | **ENTITLED** | 1925-12-31 → 2024-12-31 | (not counted) |
| **d** | `comp.co_ifndq` — point-in-time quarterly | **ENTITLED** | 1961-03-31 → 2026-07-31 | **2,114,571** |
| d | `comp.fundq` — quarterly fundamentals | **ENTITLED** | 1961-03-31 → 2026-07-31 | 2,134,745 |
| **e** | `tfn.s34`, `s34type1`, `s34type3` — 13F | **DENIED** | — | — |
| **e** | `tfn.table1`, `table2` — insiders | **DENIED** | — | — |
| **e** | `tfn.form144`, `rule10b5` | **DENIED** | — | — |
| **f** | US short-interest history | **ABSENT** | — | — |
| f | `wrds_shortvolume_samp` (sample) | ENTITLED | — | 15,883 |
| f | `wrdsapps_eushort` (European) | listed | — | — |
| **a** | OptionMetrics IvyDB | **ABSENT** | — | — |
| a | `optionmsamp_us` (sample) | ENTITLED | 2014-03-03 → 2014-03-14 | 2,600 / 36,786 |
| **g** | TAQ full | **ABSENT** | — | — |
| g | `taqsamp` / `taqmsamp` (samples) | listed | 2008-01-07..11, 2009-02-13, 2021-10-04..05 | — |

**CRSP ends 2024-12-31.** Not a defect — it is the vintage this account's CRSP is cut at — but it
means CRSP cannot cross-check anything in 2025 or 2026, which is exactly the window the forward
paper track lives in.

### Three products the brief assumed, that do not exist here

* **(e) Thomson insider + 13F — DENIED on all seven tables probed.** The library is visible; not
  one table is readable. Our SF3-based `institutional` theme keeps whatever weaknesses it has;
  the intra-quarter filing detail is not obtainable on this account.
* **(f) Short interest pre-2018 — ABSENT.** The only US short object is a *sample*
  (`wrds_shortvolume_samp`, 15,883 rows), and that is short VOLUME rather than short INTEREST —
  a different measurement. The S18 cache cannot be extended backward from here.
* **(g) TAQ — the brief's instruction was "flag size only, do not bulk-pull (terabytes)". THE
  PREMISE IS VOID: there is nothing terabyte-scale to avoid.** Only `taqsamp`/`taqmsamp` are
  present, containing a handful of named days (2008-01-07..11, 2009-02-13, 2021-10-04..05). The
  sampling recipe the brief asked for is moot, and the day-trading sibling project should be told
  that this account is not a TAQ source — before it plans around one.

---

## WHAT WAS PULLED, AND HOW IT WAS SIZED

Sizes are **measured on a real chunk and scaled**, never assumed. The chain harvest scored two
projections — a 3-name sample missed by **+339%**, a 393-pair measurement landed within **7.4%** —
and the method transferred here: pull one year, write it exactly as the real pull writes it, scale
from observed bytes.

**Measured on `ibes.det_epsus` year 2015:** 1,413,647 rows · fetch **108.2 s** · gzip-pickle write
57.1 s · **20.6 MB** (14.6 B/row compressed).
**Projected full product: ~503 MB and ~44 min of fetch** across 1980–2026.

Chunking is **by year** for the large products. Not arbitrary: WRDS enforces query limits, and a
34.5M-row single `SELECT` is the kind of request that gets killed server-side an hour in — the
most expensive way to discover a limit.

Resume discipline is the harvest's, inherited whole: one unit = one (product, chunk); payload
written atomically **before** its fsynced manifest line; a re-run re-does any unit whose payload
is absent or disagrees with its record.

---

## THE REVISED PULL PLAN — what the census actually licenses

The brief's a→g order assumed entitlements this account does not have. The measured order is:

| # | product | status | why it is where it is |
|---|---|---|---|
| 1 | **IBES** (`id`, `actu`, `statsum`, `det_epsus`) | **PULLING** | The only item that unparks a ledger row. `det_epsus` carries `anndats`, `revdats`, `actdats`, `analys`, `estimator`, `fpedats` — **per-analyst revision dates, point-in-time**, which is exactly D6's stated blocker |
| 2 | **CRSP delisting + names** | **DONE / PULLING** | 38,872 rows, trivial cost, and it is a *cross-check* rather than a new signal — any disagreement with our ACTIONS mask is a finding either way |
| 3 | **Compustat PIT** (`co_ifndq`) | **PULLING** | 2.1M rows; `_dc` data-code companions confirm it is the unrestated as-first-reported file |
| — | OptionMetrics / Thomson / short interest / TAQ | **BLOCKED** | Not entitled. Recorded above with evidence, not retried |

**D6 is unparked by (1) and the ledger row should say so.** `RESEARCH_LOG.md` is untouched and no
published `N` moves — a collection run charges no trials.

---

## STANDING CAVEATS

* **Entitlement can change under us.** This census is a measurement dated 2026-08-24, not a
  contract. Re-run `scripts/wrds_census.py` before planning anything on a product not pulled.
* **`ibes.det_epsus` vs `detu_epsus` is adjusted vs unadjusted for splits.** They are near-equal
  in size (34.54M vs 34.52M) and are **not interchangeable**: an adjusted estimate compared with
  an unadjusted actual is a units error that looks like a surprise. Whichever a register uses
  must be named in the register.
* **IBES is quarterly-and-annual across `fpi` codes** — a naive `SELECT *` mixes horizons. Any
  consumer must filter `fpi` and say which it took.
* **Nothing here has been analysed.** No IC, no arm, no verdict. The data exists on `D:` and is
  described here; that is the whole deliverable.
