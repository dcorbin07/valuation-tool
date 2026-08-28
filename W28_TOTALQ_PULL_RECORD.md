# W-28 — TOTAL Q: CENSUS AND PULL
## **ZERO TRIALS. Collection only — no arm, no kill read, no verdict.** 2026-08-28.

Unblocks r1's executor pass, which accepted the Frontier Scout's `PREREG_DRAFT_w28_total_q.md`
with two amendments and recorded it **BLOCKED ON A PULL**. Raw rows on `D:\wrds` only; derived
statistics out.

---

## 1. THE BLOCKER DISSOLVES, AND NOT THE WAY THE EXECUTOR PASS EXPECTED

r1 blocked `K1` on three findings: the declared annual `comp.funda` fields are not on disk, what
is on disk is the **QUARTERLY** `comp_pit`, and *"running Peters-Taylor perpetual inventory on
quarterly flows is a construction change the draft does not name"*.

**`totalq.total_q` IS ENTITLED and it ships `q_tot` PRE-COMPUTED**, so there is no perpetual
inventory to run at all — no annual flows to assemble, no `δ_R&D` from BEA, no 20%/yr `δ_org`,
and therefore nothing for §6's deviation rule to bite on. **`K1` has a subject.** Whether it
*passes* is the register's business and is untouched here.

| | |
|---|---|
| `totalq.total_q` | **ENTITLED**, 485,746 rows, 32,894 gvkeys |
| `datadate` span | **1950-06-30 → 2025-05-31** |
| columns | `gvkey`, `datadate`, `fyear`, `k_int_know`, `k_int_org`, `k_int_offbs`, `k_int`, `q_tot` |
| rows with `q_tot` | **343,587 = 70.7%**, 29,172 gvkeys, 1958-12-31 → 2025-05-31 |
| rows where `q_tot` is NULL | **142,159 = 29.3%** — Total Q needs a market value, and the intangible-capital columns are populated earlier than it is |

`totalq_all.total_q` is the identical table (same 485,746 rows) and was not pulled twice.

**The intangible-capital components ship alongside `q_tot`** — `k_int_know` (knowledge capital),
`k_int_org` (organisation capital), `k_int_offbs`, `k_int` — which the register did not ask for
and which are on disk now because they arrive in the same rows.

---

## 2. AMENDMENT 2 HONOURED: THE JOIN IS DATED, AND DATING COSTS 13.1 POINTS

CCM is DENIED on this account, so the route is the one `W-3b` built and `D6` reused:

> panel ticker —(**CRSP `stocknames` INTERVALS, dated**)→ cusip8 —(`comp.security`)→ gvkey → `total_q`

Only the first hop needs dating, because a cusip is a stable security identifier and a **ticker is
a lease** — `W-3b` measured that 17.7% of the rows an undated ticker map offers belong to a
different company.

**Both routes were measured, so the cost of dating is a number rather than an assertion:**

| publication lag | DATED | naive undated ticker | difference |
|---|---|---|---|
| 120 days | **71.31%** (81,254 cells, 2,034 names) | 84.40% (96,166) | **+14,912 cells** |
| 180 days | 71.26% (81,202) | 84.35% (96,108) | +14,906 |

**The naive route offers 18.4% more cells and Amendment 2 says those extra cells are the hazard,
not a bonus.** The lag barely matters — 0.05pp between 120 and 180 days — because Total Q is
annual, so a two-month shift rarely crosses an observation boundary. **A register may therefore
choose its lag on grounds other than coverage**, which is a small freedom worth knowing it has.

---

## 3. COVERAGE ON THE POPULATION THE ARM WILL TEST — INCLUDING THE REGISTER'S OWN BURN-IN

| | cells | % of 113,945 |
|---|---|---|
| any prior Total Q (120d lag) | 81,254 | **71.31%** |
| **≥ 10 prior annual observations** — the register's declared burn-in | **64,475** | **56.58%** |
| what the burn-in costs | 16,779 | 14.73 pp of the panel, **20.7% of covered cells** |

**THE BURN-IN IS THE BINDING CONSTRAINT, NOT ENTITLEMENT.** Total Q reaches 71% of cells and the
register's own ≥10-year requirement removes a fifth of those.

### And its bite is ERA-DEPENDENT in a way a both-halves gate will feel

| | 2009 | 2014 | 2019 | 2021 | 2022 | 2025 |
|---|---|---|---|---|---|---|
| any prior Total Q | 60.1% | 65.2% | 74.6% | 68.4% | 73.0% | **86.0%** |
| **≥10-year burn-in** | 50.8% | 56.1% | **62.0%** | **54.0%** | **52.5%** | 57.9% |

**Raw coverage rises monotonically 60.1% → 87.3%, and burn-in coverage does NOT — it peaks near
62% in 2019-20 and DIPS to 52.5% in 2022.** That dip is the IPO wave: names entering the panel
after 2020 cannot have a decade of history, so the burn-in removes them precisely where the
universe is growing.

**So the burn-in's cost correlates with the IPO cycle rather than being a fixed tax, and a
both-halves split will see a different population in each half.** Stated here, before any kill,
because a coverage trend that tracks time is exactly what turns a data artefact into a finding —
and `MA58` measured this project losing 20 of 69 dates to an unnoticed complete-case rule.

**Amendment 1 keeps this from being a REMOVAL arm**: rows failing the burn-in fall back to the
incumbent column, so the paired difference on them is exactly zero and the population is
unchanged. **This census therefore reports the share of cells on which the arm is, by
construction, measuring nothing: 43.42%.**

---

## 4. WHAT WAS PULLED

| product | rows | reconciles |
|---|---|---|
| `totalq.total_q` | **485,746** | ✔ exactly |
| `crsp.stocknames` (the dated first hop) | 83,280 | ✔ |
| `comp.security` (cusip → gvkey) | 77,546 | ✔ |

Standard resume discipline, unchanged: one unit = one (product, chunk), payload written
atomically **before** its fsynced manifest line, a torn final manifest line costs that unit and
not the file, and `--reconcile` compares pulled rows against the server's own `count(*)`.

### `comp_pit` reads SHORT BY 780 — and that is the checker working, not a hole

| year | source | pulled | delta |
|---|---|---|---|
| 2023 | 50,650 | 50,649 | +1 |
| 2024 | 51,166 | 51,158 | +8 |
| 2025 | 52,808 | 52,794 | +14 |
| **2026** | 25,582 | 24,825 | **+757** |

**Every delta is POSITIVE and 99% sits in 2025-26** — Compustat back-filling recent quarters as
companies file in the four days since that pull. **No year went down**, which is what a hole
would look like. `reconcile`'s own docstring anticipated exactly this: *"a legitimate mismatch
exists the moment the vendor adds rows after a pull, and a checker that cries wolf on ordinary
staleness gets ignored."*

**Reported, not silently refreshed.** The resume rule correctly skips a chunk already recorded
`ok`, which is what makes a pull reproducible; re-pulling would change an artifact other work may
already rest on, and that is a deliberate act rather than a side effect of running a census.

---

## 5. NOT DONE, named so it is not mistaken for done

**No arm. No `K1`–`K5` read. No composite gate. No verdict. Nothing adopted** — a composite-input
change is a vintage event and Don's call. **Zero trials**: `by_domain` is unchanged at equity
**245**, options **310**, infra **20**.

**The register is still not committed.** The scout's `PREREG_DRAFT_w28_total_q.md` and
`WIDTH_AUDIT.md` remain **unpushed on a local branch**, `worktree-scout-wrds` at `e705ba0`, which
is the scout lane's to push — this pull was executed against r1's executor write-up in
`HANDOFF_edge_audit.md`, which carries the accepted spec and both amendments. **A reader who
wants the draft's own wording still cannot get it from any pushed ref.**

**And two things the register must still decide, which this census deliberately does not:** the
publication lag (measured at two values, and coverage does not discriminate between them), and
whether the ≥10-year burn-in survives now that Peters-Taylor's own construction already embeds
one — the draft's burn-in was written for a recomputation that no longer has to happen.

`D:\wrds\W28_CENSUS.json`, `W28_COVERAGE.json`, `W28_BURNIN.json`, `W28_COMP_PIT_DRIFT.json`;
payload under `D:\wrds\totalq_total_q`, `crsp_stocknames`, `comp_security`.
