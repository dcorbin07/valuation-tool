# HANDOFF — scout / MC12 panel-extension Stage-1 census

**2026-09-30. Zero trials, FACTS class. Register `PREREG_panel_ext_census.md`, committed ALONE
at `5cff93a` (markdown only, zero `.py`), a strict git ancestor of every measurement commit.**

`by_domain` **bit-identical** before and after — equity 248, options 310, unified 0, infra 20 —
re-read from `research_log.detail()` rather than quoted, while `rows_fixed_not_counted` rises
**84 → 85**, which is the proof the row was seen and correctly excluded. Nothing adopted, no
panel built, no successor register written.

---

## 1. THE HEADLINE

**Route S fails all three candidate start years, and the binding reason is structural rather
than thin coverage: two of the seven weighted themes have no pre-2009 source at all.**

* `institutional` reads **0.000 in every year 1995–2008**. Sharadar `sf3` carries **zero rows
  dated before 2009** — established *positively*, by scanning the 2.9 GB file for 1990s and
  2000–2008 dates and finding none, rather than inferred from a filter that returned nothing.
  `co_ifndq` carries no ownership column at all.
* `insider` runs **0.001 in 1995 to only 0.307 by 2008**, so it never approaches the 70% rule
  even after electronic Form 4 filing became mandatory in 2003.

So **a pre-2009 composite is FIVE themes, not seven**, which independently corroborates the
manager's own §6 note. An extension built on it would not be an extension *of the published
figure* — it would be a different composite wearing the same name.

Secondary: **K1** fails 1995 alone (965 names against the 1,030 bar), passing 1996 onward at
2,718 → 5,555. **K3** passes 1995 at 0.0964 and fails 1996–2008 at 0.2388 → 0.3876 against a
shipped matched-window reference of 0.1162. **K4 PASSES all fourteen years** — timely-`datekey`
share 0.985–0.995 against a 2009–2013 reference of 0.9914, median lag 40–46 days — which
**refutes the register's own expectation 4** that early SF1 would show vendor backfill.

## 2. THE ROUTE W FINDING, AND IT CONTRADICTS THE BRIEF'S OWN FRAMING

The brief calls `comp.co_ifndq` *"the entitled point-in-time quarterly"*. Measured across
1995–2008 it carries **53 `PRE_AMENDS` rows against 652,462 `STD`** — a share of **0.0000812**,
with **zero `PRE_AMENDS` in 9 of the 14 years** — and its only date-like column is `datadate`.
There is no `rdq`, no `srcdate`, no vintage of any kind, so **the table records no date at which
a row became available.**

Two consequences. **K4 cannot be run on Route W at all**, and that is reported as a finding
rather than an omission. And a panel built on Route W would score historical dates against
**restated** fundamentals — the look-ahead the project's entire point-in-time discipline exists
to prevent. Its point-in-time-ness is carried by `datafmt`/`consol`, which distinguishes
as-first-reported from restated *without dating either*.

Route W's dated link reaches **0.8258** of `stocknames` intervals; the **contaminated undated
route reaches more**, which is `W-28`'s shape exactly and is why it is reported beside the dated
figure and never counted as coverage.

Route W's price leg is **SIZED and never measured**: `co_ifndq` has no price column and
`crsp.dsf` is banked only 2008–2024, so the 14 absent years extrapolate to ~5.6M rows / ~35 MB
from the real 2008 chunk. **That chunk is panel-restricted** (1,607 permno, four columns), so
two effects push the estimate opposite ways — an extension needs names absent from today's
panel (understates) while the pre-2008 cross-section is smaller (overstates) — and **no
direction is claimed**.

## 3. PREMISE CORRECTIONS (all made before any verdict was read)

1. **`DESIGN_panel_extension.md` §1.1 says "24 distinct z-columns" and its own table lists 25,
   with no duplicates.** The AST derivation settles it at **24** and locates the cause exactly:
   **`insider` contributes ZERO z-columns**, because `factors.py` maps it as a fixed affine
   `(insider_score − 50)/25` rather than a z-score. So the prose count is right and the table's
   25th row is not a z-column. Pinned by `test_insider_contributes_no_z_column`.
2. **The manager's §7.3 `co_ifndq` row-count question is SETTLED, against `DESIGN`.** The
   manifest holds **74 chunk entries for 66 year-files** because 2021–2026 were re-pulled, each
   time returning an identical count. Summing every entry gives `DESIGN`'s **2,467,490**;
   summing the last pull per year gives `WRDS_CENSUS`'s **2,114,571**. The difference is exactly
   **352,919**, entirely re-pulls, and 6 of 6 sampled years match the frames on disk. **The
   census figure is correct.** `DESIGN`'s own sentence pairs the correct *file* count (66) with
   the double-counted *row* count in one clause, which is how it went unnoticed.
3. **Two Route W line items sit below the 70% rule in every year** — `xintq` ≈ 0.67, `xsgaq`
   ≈ 0.69 — and **`gpq` is 0.00 non-null throughout**, so `gross_margin` and `gp_on_capital`
   must be derived from revenue − COGS rather than taken from `gpq`. `DESIGN` §1.2's "first year
   1976" for those two is only reachable by the derived route.

## 4. BUGS FOUND — all three in my own instrument, all caught by disbelieving a number

1. **K3 compared two different objects.** The first cut put each extension year's share of names
   delisting at *any* later date against the shipped panel's *ever*-delist share (0.2797). A
   1997 cohort has ~29 years of forward observation and the shipped panel ~17, so the extension
   years read 0.60–0.82 and **thirteen of fourteen years "failed" the upper tail for that reason
   alone.** Thirteen identical failures are a broken comparison, not thirteen broken universes.
   Repaired by giving both sides the **same window length**; the bar is untouched and the
   unbounded figure ships under a `NOT_COMPARABLE` label.
2. **A knife-edge absolute bar.** `momentum` used `≥ 250` trading days and **2001 came back at
   exactly 0.000, sitting between 0.816 and 0.884** — the NYSE closed four days after 11
   September 2001 and that year holds **248** sessions, so every name failed. This is the hazard
   `E-6` closed with *"a successor must not set a knife-edge burn-in bar"*.
3. **The relative bar that fixed 2001 then went VACUOUS on 1997**, handing a bar of **one row**
   to a year holding a single session (the freeze's `sep` starts 1997-12-31) and reporting
   **93.2% available** for a theme needing twelve months of prices. Guarded with a 200-session
   floor below which the theme reads **NOT AVAILABLE**.

A fourth, smaller: the progress print sat *after* a `continue`, so a source with no in-window
rows printed nothing and read as a hang — which is why `institutional` initially looked silent.

## 5. THE DECLARED DEVIATION — WRDS IS NOT REACHABLE AND DID NOT NEED TO BE

`wrds-pgdata.wharton.upenn.edu:9737` accepts the socket, completes TLS and recognises the host
(a `dbname=postgres` probe returns `no pg_hba.conf entry for host …, user "dcorbin"`), yet PAM
rejects the credential in **~1 second with no MFA challenge** — and that credential is
**byte-identical** to the one in `%APPDATA%\postgresql\pgpass.conf` written 2026-08-28, when
WRDS demonstrably worked. A connection genuinely awaiting Duo blocks for tens of seconds, so
**no push is being issued**; this is a server-side credential or lockout state.

**Reported against myself:** my diagnostic scripts fired roughly **ten** authentication attempts
before I recognised the pattern, which may itself have contributed to a lockout. One attempt
with a long timeout was the right first move and I did the opposite. I have stopped retrying.

It does not block the work. Every table both this census and `W-6` need is **already banked on
`D:\wrds`**, so chunks are reconciled against `manifest.jsonl` — verified against the frames on
disk — instead of a live `count(*)`. That establishes *the file on disk is the file the server
returned*; it does **not** re-establish that the server's table is unchanged since 2026-08-28,
and the artifact says so.

## 6. NOT DONE — named so it is not mistaken for done

No panel is built, nothing is adopted, and **no successor register is written**. The extension is
**NOT licensed as a trial**: the manager's §6 already closed that, and this register's own
derived power table independently reproduces its arithmetic — **49.5% power at the hurdle for
n ≈ 110**, against the manager's "49%".

**K3's upper tail cannot distinguish an inverted (`B6`) universe from genuine dot-com-era
attrition.** US listings roughly halved over this window, so an elevated delisting rate in
1997–2002 may be economically real. The kill was pre-committed to fire on both tails and is
honoured as written — §7.6 forbids relaxing a bar after reading the data — but **the limitation
is the register's own and is recorded rather than resolved.** A successor wanting to separate the
two causes needs a discriminator this register does not contain.

Also not done: Route W's price leg is sized rather than measured; no `dsf` pull was made; the
1995 Route S year was not investigated beyond its K1 failure.

## 7. ARTEFACTS

`PREREG_panel_ext_census.md` · `scripts/panel_ext_census.py` · `PANEL_EXT_CENSUS.md` (tracked) ·
`D:\wrds\PANEL_EXT_CENSUS.json` (banked per rule 9, outside the repo) ·
`tests/test_panel_ext_census.py` (11 of 11 passing, every guard carrying a positive control) ·
`RESEARCH_LOG.md` and `VALQUO_LEDGER.md` rows `PANEL-EXT-CENSUS`.

Nothing under `data/`, no `*.pkl`, and nothing from `D:\wrds` is committed.
