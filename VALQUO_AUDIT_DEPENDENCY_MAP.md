# Valquo — audit item dependency and collision map

**Companion to `VALQUO_EDGE_AUDIT.md`.** Generated from `valquo_audit_items.json`, which is verified against the staged tree at commit `7eb0046` — write-sets come from reading the code, and the import edges come from a grep of every `from`/`import` in the tree, not from inference.

Three files ship together:

| file | what it is |
|---|---|
| `valquo_audit_items.json` | machine-readable: per item, files modified, files created, dependencies |
| `check_lanes.py` | the validator — answers *can these run concurrently?* in one command |
| this document | the human/agent-readable version, with the lane assignment |

---

## The three answers you need

**1. Textual disjointness is not sufficient.** Two agents can edit different files, merge cleanly, and still break the build — because one file imports the other. The clearest example is the pair you would *most* expect to be safe:

```
$ python check_lanes.py B1 B2
SOFT COLLISIONS — import-coupled, clean merge but possible break:
  B1 x B2: valuation/edge/options_universe.py <-> valuation/edge/options_backtest.py
  B1 x B2: valuation/edge/options_universe.py <-> valuation/edge/options_fill.py
```

B1 touches `options_universe.py`, B2 touches `options_backtest.py` and `options_fill.py`. Different files, zero overlap — and `options_universe.py` imports both of them. B1 changes what `chain_summary` and `pick_contract` receive; B2 changes what they do with it. Landed independently, each is correct and the combination is untested.

The same trap sits between the two lanes you would naturally split the equity work across:

```
$ python check_lanes.py B11 S2      # a PANEL item and a FACTORS item
SOFT COLLISIONS
  B11 x S2: valuation/edge/fundamental_panel.py <-> valuation/screener/factors.py
```

**PANEL and FACTORS are not independent lanes.** `fundamental_panel.py` imports `factors.py`, `settings.py` and `cross_sectional.py`. They can run concurrently only for specific item pairs — which is what the validator is for.

**2. The parallelism is real, but it is not where you would look for it.** You cannot split the panel. What you can run concurrently is **37 items that modify no existing file at all** (read-only analysis or a new module), plus the entire second codebase, plus the miner, plus infra. That is four to six live lanes without touching the bottleneck.

**3. `fundamental_panel.py` is the programme.** 46 of the 134 items modify it. No amount of lane design changes that; it is a property of the codebase, not of the plan. Two consequences worth acting on: **B23** (four panel builds per run, ~40–50% wall-clock saving) should land early because every later item pays that cost, and a serious refactor of that file into modules would convert the biggest lane in the project into three — which is not in the audit, but is the highest-leverage engineering change available if throughput becomes the constraint.

---

## Hot files

| items | file | note |
|---|---|---|
| 46 | `valuation/edge/fundamental_panel.py` | **the bottleneck** — single owner, always |
| 14 | `valuation/screener/factors.py` | imported by the panel and by `screen.py` |
| 8 | `valuation/screener/settings.py` | 10 importers; additive edits usually merge cleanly |
| 6 | `valuation/edge/options_universe.py` | imports the rest of the options engine |
| 6 | `valuation/edge/options_backtest.py` | imported by `options_universe`, `options_live`, 4 runners |
| 6 | `valuation/edge/options_fill.py` | imported by backtest, vrp, universe, live |
| 4 | `valuation/edge/bulk.py` | loader; disjoint from the panel unless the item also writes it |
| 3 | `valuation/edge/theta_bulk.py` | miner; long jobs |
| 3 | `valuation/edge/statistics.py` | **10 importers across both lanes** — global change |
| 3 | `options-bot/screener/run_backtest.py` |  |
| 2 | `valuation/edge/options_tracker.py` | **18 references / 10 importers** — the options hub |
| 2 | `valuation/edge/paper_track.py` | B5 and P4 both land here — serialize |
| 2 | `valuation/edge/data_providers.py` | 6 importers |
| 2 | `valuation/edge/options_autopsy.py` | imported by `options_universe` |
| 2 | `options-bot/options_backtest/backtest_engine.py` |  |
| 2 | `valuation/edge/options_vrp_portfolio.py` |  |

---

## Lanes

### FREE — 37 items

No existing file is modified — read-only analysis, or a new file only. **Collision-free by construction.** Any number of these can run concurrently with each other and with every other lane.

| ID | item | modifies | needs first |
|---|---|---|---|
| **D1** | Sharadar direct at $29/mo | — | — |
| **D10** | Freeze verification + legend | —new file only | — |
| **D2** | ThetaData tier + licence | — | — |
| **D3** | Fetch the free factor datasets | —new file only | — |
| **D4** | Cboe Open-Close Volume Summary | — | O14 |
| **D5** | ORATS | — | O2 |
| **D6** | Estimate-revision situation | — | — |
| **D7** | WRDS reality check | — | — |
| **D8** | What not to buy | — | — |
| **D9** | Options costs are a step change | — | — |
| **M4** | Live-replay harness | —new file only | B7 |
| **M5** | Protocol for tail-hedge tests | — | — |
| **O12** | Fractional Kelly / ruin | —new file only | O11 |
| **O19** | Cheap-contract sizing artefact | —new file only | — |
| **O2** | Cross-sectional VRP | —new file only | — |
| **O22** | Capacity-constrained replay | —new file only | O11 |
| **O25** | Sell the wing after the move | —new file only | O1 |
| **O3** | Delta-hedged vs idio vol | —new file only | O2 |
| **O4** | Expected idio skewness | —new file only | O2 |
| **O5** | Volatility of volatility | —new file only | O2 |
| **O7** | Earnings straddles | —new file only | — |
| **P1** | Estimate capacity | —new file only | — |
| **P2** | Model user crowding | —new file only | P1 |
| **P5** | Decide the claim before R1 | — | — |
| **R2** | Re-run broad options study | — | B1, B3, O20 |
| **R7** | Re-commit term_slope floor | — | — |
| **S26** | Read the twenty worst holdings | —new file only | — |
| **U1** | Stock composite -> options entry | —new file only | B1, R2 |
| **U3** | Convex overlay as insurance | —new file only | O11 |
| **U5** | Tax-aware arm allocation | — | — |
| **U6** | CSPs in, covered calls out | —new file only | B1 |
| **U7** | Composite as an options veto | —new file only | — |
| **X3** | Ablate to best single signal | —new file only | — |
| **X4** | Factor-ETF benchmark | —new file only | — |
| **X5** | Bootstrap the pipeline | —new file only | B23 |
| **X6** | Structural-break test | —new file only | — |
| **X8** | Replicate on JKP / another country | —new file only | — |

### OPTIONS-BOT — 8 items

`options-bot/**` only. Shares no file with the main tree. **A genuinely free second lane** — and it contains four of the more serious defects in the whole audit.

| ID | item | modifies | needs first |
|---|---|---|---|
| **C1** | Backtest the model that ships | `run_backtest.py`, `scoring.py` | — |
| **C2** | Universe is inverse of target | `pit_universe.py`, `run_backtest.py` | — |
| **C3** | --bots reversion does nothing | `run_backtest.py` | — |
| **C4** | Wire the tracking loop | `pipeline.py`, `store.py` | — |
| **C5** | PIT universe on real data | `run_sharadar_backtest.py` | D10 |
| **C6** | Three undeployed fixes | `` | — |
| **O8** | Index VRP - run existing bt | `backtest_engine.py` | — |
| **O9** | IV rank as sell-timing | `backtest_engine.py` | O8 |

### INFRA — 4 items

CI workflow, tests, product surface, `CLAUDE.md`. Disjoint from all research code.

| ID | item | modifies | needs first |
|---|---|---|---|
| **C7** | Widen the CI gate | `land-agent-branch.yml` | — |
| **M3** | Guards with known-bad fixtures | `` | — |
| **P3** | Design for a 37% hit rate | `` | — |
| **U4** | One decision object | `` | U1, U2 |

### OPT-DATA — 2 items

The miner: `theta_bulk.py`, `thetadata_provider.py`, `options_greeks.py`. Long-running jobs; start early and let them run underneath other lanes.

| ID | item | modifies | needs first |
|---|---|---|---|
| **O14** | Tick flow, alert days only | `theta_bulk.py` +new | — |
| **O15** | Re-mine beyond 90 DTE | `options_greeks.py`, `theta_bulk.py`, `thetadata_provider.py` | — |

### LIVE — 4 items

`paper_track.py`, `paper_broker.py`, `options_tracker.py`, `options_live.py`, sizing, portfolio. ⚠ `options_tracker.py` is imported by ten modules — a signature change here reaches OPT-ENGINE.

| ID | item | modifies | needs first |
|---|---|---|---|
| **B5** | Four paper-track defects | `options_tracker.py`, `paper_broker.py`, `paper_track.py` | — |
| **O11** | Portfolio layer for single-leg | `options_vrp_portfolio.py` +new | B1 |
| **P4** | Fix the track's rules | `paper_track.py` | B5 |
| **U8** | One risk budget across books | `options_vrp_portfolio.py` | O11 |

### DATASETS — 3 items

`bulk.py`, `short_interest.py`, `lazy_prices_ic.py`. Loader-side; disjoint from the panel itself *unless* an item also writes `fundamental_panel.py` (those are in CROSS).

| ID | item | modifies | needs first |
|---|---|---|---|
| **S17** | Decode the rest of EVENTS | `bulk.py` | D10 |
| **S19** | MD&A anomaly left on the table | `lazy_prices_ic.py` | X1 |
| **S25** | Point-in-time sector map | `bulk.py` +new | — |

### STATS — 1 items

`statistics.py` alone. Ten importers across **both** research lanes — treat any change here as a global event, never as a parallel task.

| ID | item | modifies | needs first |
|---|---|---|---|
| **M2** | Clustered inference default | `statistics.py` | B25 |

### OPT-ENGINE — 14 items

`options_universe.py`, `options_backtest.py`, `options_fill.py`, `options_signals_v2.py`, `options_autopsy.py`, `blackscholes.py`. These import each other in a chain, so **the whole territory is one owner**, not one-owner-per-file.

| ID | item | modifies | needs first |
|---|---|---|---|
| **B16** | Quarantine dead exit module | `options_backtest.py`, `options_exit.py`, `options_fill.py` | — |
| **B2** | Exit-path quote censoring | `options_backtest.py`, `options_fill.py` | — |
| **B3** | Stale-quote expiry marks | `options_fill.py` | — |
| **O1** | Exit sweep incl. random entries | `options_backtest.py` +new | B2, B3 |
| **O10** | Passive-limit fill model | `options_fill.py` | B2, B3 |
| **O13** | Anti-signal decomposition | `options_universe.py` | B1 |
| **O16** | Is term_slope a front-IV level? | `options_signals_v2.py` | B1 |
| **O17** | Earnings filter for the long arm | `options_universe.py` | B1 |
| **O18** | Spread-conditional cost model | `options_fill.py` | — |
| **O20** | PIT option-universe selection | `options_universe.py` | B1 |
| **O23** | Exits vs the underlying | `options_backtest.py` | O1 |
| **O24** | Is term_slope an earnings cal? | `options_signals_v2.py` | O16, D10 |
| **O26** | Raise the per-bucket floor | `options_universe.py` | — |
| **O6** | Cheapest-on-surface selection | `options_backtest.py` | B1, O2 |

### FACTORS — 9 items

`factors.py`, `settings.py`, `cross_sectional.py`, `screen.py`, `config.py`. ⚠ `fundamental_panel.py` imports all of these — see the coupling note below.

| ID | item | modifies | needs first |
|---|---|---|---|
| **B10** | accruals_q silent overwrite | `factors.py`, `settings.py` | — |
| **R5** | Four classic anomalies, full universe | `factors.py`, `settings.py` | B12 |
| **R6** | SF3 conviction family | `factors.py`, `settings.py` | B12 |
| **S1** | Fix value theme inputs | `factors.py`, `settings.py` | B18 |
| **S15** | Sector-relative value only | `factors.py` | S25 |
| **S2** | Register cash_op_prof | `factors.py`, `settings.py` | — |
| **S4** | Growth theme carries zero weight | `settings.py` | — |
| **S7** | Pre-registered interactions | `factors.py`, `settings.py` | — |
| **U2** | Options surface -> stock signals | `factors.py`, `settings.py` +new | O2 |

### PANEL — 36 items

`fundamental_panel.py` and `data_providers.py`. 36 items live *only* here; another 10 CROSS items also write the panel, so **46 of 134 touch this file**. Single-owner bottleneck of the programme.

| ID | item | modifies | needs first |
|---|---|---|---|
| **B11** | Compute the 37bps figure | `fundamental_panel.py` | — |
| **B12** | Alphabetical universe | `data_providers.py` | — |
| **B14** | Ship delisting-mask coverage | `fundamental_panel.py` | — |
| **B17** | top-25 hold holds fifty | `fundamental_panel.py` | — |
| **B19** | Sharpe uses rf=0 | `fundamental_panel.py` | — |
| **B20** | earnings_yield numerator switch | `fundamental_panel.py` | — |
| **B21** | _sector_capped never invoked | `fundamental_panel.py` | — |
| **B22** | Results file loses blocks silently | `fundamental_panel.py` | — |
| **B23** | Four panel builds per run | `fundamental_panel.py` | — |
| **B24** | sanity_check double-counts | `fundamental_panel.py` | — |
| **B26** | Same-day insider/grades | `fundamental_panel.py` | — |
| **B6** | Panel truncation + date ranges | `data_providers.py`, `fundamental_panel.py` | — |
| **B9** | DSR / PBO trial accounting | `fundamental_panel.py` | — |
| **M1** | Research log with real N | `fundamental_panel.py` +new | — |
| **M6** | Results-file schema assertion | `fundamental_panel.py` | B22 |
| **R1** | Factor-adjusted alpha | `fundamental_panel.py` +new | B6 |
| **R10** | Investable benchmark | `fundamental_panel.py` | B6 |
| **R4** | Multiple-testing accounting | `fundamental_panel.py` +new | B9 |
| **R9** | t-stat on headline; HAC | `fundamental_panel.py` | — |
| **S10** | Downside-exclusion screen | `fundamental_panel.py` +new | — |
| **S11** | Horizon ensemble | `fundamental_panel.py` | — |
| **S13** | Vol-targeted weighting | `fundamental_panel.py` | — |
| **S14** | No-trade band on net alpha | `fundamental_panel.py` | B11, B13 |
| **S22** | Term structure of the signal | `fundamental_panel.py` | — |
| **S23** | Exit rule for the equity book | `fundamental_panel.py` | — |
| **S24** | Ensemble across draws | `fundamental_panel.py` | — |
| **S27** | Weight recent observations more | `fundamental_panel.py` | X6 |
| **S28** | Distribution, not just the mean | `fundamental_panel.py` | — |
| **S3** | Rebuild the insider score | `fundamental_panel.py` | — |
| **S5** | Hierarchical shrinkage | `fundamental_panel.py` +new | X3 |
| **S6** | Factor momentum on themes | `fundamental_panel.py` +new | — |
| **S8** | Signal-freshness weighting | `fundamental_panel.py` | — |
| **S9** | Data-staleness conditioning | `fundamental_panel.py` | — |
| **X1** | Split on universe, not time | `fundamental_panel.py` | B6 |
| **X2** | Rebalance-grid offset | `fundamental_panel.py` | B6 |
| **X7** | Placebo through the pipeline | `fundamental_panel.py` +new | B23 |

### CROSS — 16 items

Spans two or more territories. Each must be scheduled **solo**, or owned by whoever holds the widest territory it touches. These are the items that produce merge messes.

| ID | item | modifies | needs first |
|---|---|---|---|
| **B1** | Price basis in options_universe | `test_edge.py`, `options_universe.py` | — |
| **B13** | prefilter in the backtest | `fundamental_panel.py`, `factors.py` | — |
| **B15** | Commission in return_pct | `options_fill.py`, `options_tracker.py` | — |
| **B18** | Negative EV read two ways | `fundamental_panel.py`, `factors.py` | — |
| **B25** | Three DSR conventions | `fundamental_panel.py`, `options_autopsy.py`, `statistics.py` | — |
| **B4** | OI sentinel into chain_summary | `options_backtest.py`, `theta_bulk.py` | — |
| **B7** | Unify the three composites | `config.py`, `fundamental_panel.py`, `factors.py`, `screen.py` | — |
| **B8** | Holdout rule vs documentation | `CLAUDE.md`, `fundamental_panel.py` | — |
| **O21** | Dividends / early exercise | `blackscholes.py`, `options_greeks.py` | — |
| **R3** | Clustered inference (options) | `options_autopsy.py`, `options_universe.py`, `statistics.py` | B1 |
| **R8** | Total return, not price-only | `bulk.py`, `fundamental_panel.py` | — |
| **S12** | Rank within bucket | `fundamental_panel.py`, `factors.py` | — |
| **S16** | Decompose net issuance | `bulk.py`, `fundamental_panel.py` | — |
| **S18** | Short interest as interaction | `fundamental_panel.py`, `short_interest.py` | — |
| **S20** | Rank composite, not z-sum | `fundamental_panel.py`, `cross_sectional.py`, `factors.py` | B7 |
| **S21** | Winsorise before standardising | `fundamental_panel.py`, `factors.py` | — |

Territories spanned:

| ID | spans |
|---|---|
| **B1** | INFRA + OPT-ENGINE |
| **B13** | FACTORS + PANEL |
| **B15** | LIVE + OPT-ENGINE |
| **B18** | FACTORS + PANEL |
| **B25** | OPT-ENGINE + PANEL + STATS |
| **B4** | OPT-DATA + OPT-ENGINE |
| **B7** | FACTORS + PANEL |
| **B8** | INFRA + PANEL |
| **O21** | OPT-DATA + OPT-ENGINE |
| **R3** | OPT-ENGINE + STATS |
| **R8** | DATASETS + PANEL |
| **S12** | FACTORS + PANEL |
| **S16** | DATASETS + PANEL |
| **S18** | DATASETS + PANEL |
| **S20** | FACTORS + PANEL |
| **S21** | FACTORS + PANEL |

---

## Using the validator

```bash
python check_lanes.py B1 C4 X3 P1      # can these four run concurrently?
python check_lanes.py --lanes          # the lane table above, regenerated
python check_lanes.py --ready B1 B3    # what unblocks once these land
python check_lanes.py --file B14       # who else touches B14's files
```

Exit code is 0 when safe, 1 on a hard collision or an unmet dependency — so it can gate a dispatch script.

`SOFT` returns 0 deliberately: import coupling is a judgement call, not an automatic block. It means *one reviewer must see both diffs before either lands*, which is weaker than "do not run in parallel" and stronger than "fine".

---

## Dependency chains that actually constrain the order

Most items are independent. These are the real edges:

| chain | why |
|---|---|
| `B1 → O13, O16, O17, O20, U6, R3 → R2` | everything downstream of the corrupted spot price |
| `B2 + B3 → O1 → O23, O25` | the exit sweep needs an uncensored exit path first |
| `B12 → R5, R6` | the alphabetical-universe fix gates both re-runs |
| `B6 → R1, R10, X1, X2` | panel truncation gates every headline re-derivation |
| `B23 → X5, X7` | four-builds-per-run makes the bootstrap and placebo affordable |
| `B7 → S20, M4` | one composite must exist before you change how it standardises |
| `O2 → O3, O4, O5, O6, U2` | one new cross-sectional module, four studies on top |
| `O11 → O12, O22, U3, U8` | the portfolio layer gates all sizing work |
| `D10 → S17, C5, O24` | time-limited — the Sharadar legend gates three items |
| `B5 → P4` | same file; P4 is urgent but must follow B5 |
| `S25 → S15, B21` | sector work needs a point-in-time sector map first |

---

## Merge protocol at the hot files

- **`fundamental_panel.py`** — one owner at a time, no exceptions. If two panel items must overlap, do them in one branch as sequential commits rather than two branches.
- **`statistics.py`** — B25 and M2 are the only items here and both are global. Land them alone, on a quiet tree, with the full suite green.
- **`options_tracker.py`** — B5 and B15 both change it. It has 18 references. Any signature change needs a repo-wide grep in the same commit.
- **`settings.py`** — several items add rows to `NUMBER_THEME`. Those are additive and usually merge cleanly, but two agents adding to the same dict will still conflict textually. Batch them: **B10, R5, R6, S2, S4** are one commit's worth of registration work, not five branches.
- **CROSS items** — assign to whoever owns the widest territory the item touches, and land them when that territory is otherwise idle.

---

## What this map does not know

Write-sets are the **audit's proposed** implementation. If an executing session solves an item a different way, its write-set changes and this map goes stale. Two mitigations:

- Have each session record its actual touched files in `HANDOFF_edge_audit.md` and update the JSON when it diverges. The map is a working file, not a fixed artefact.
- The `NEW:` entries are predictions of new module names. Where two items are marked as creating the same new file (O2/O3/O4/O5 all create `opt_xsec.py`), that is deliberate — they are one module built once and extended, and they belong to one owner.

Import edges were extracted by grep and cover the modules the audit touches. A dynamic import or a runtime lookup would not appear. Nothing in the tree suggested one, but the map cannot prove their absence.
