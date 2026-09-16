# 03 — Start/Sit Engine: Design Specification
*Working name `ff-engine`. The code that exists is in `ff-engine/`; this document is the design it is being built toward. Written 2026-09-15, in the spirit of the valuation-tool: a model, a lab whose job is to disprove it, and a ledger that says which is which.*

## 1. What the engine claims, and what it does not

Five things will share one codebase, and they will not carry equal evidence. Stating that up front is the single most important design decision, because it is the one the valuation-tool got right and most fantasy products get wrong.

| surface | what it does | evidential status at launch |
|---|---|---|
| **Capture pipeline** | records every source, timestamped, tamper-evident | operational; `PREREG_000` decides whether it is breathing |
| **Consensus baseline** | the free crowd's rankings and projections, as of each clock, in each scoring | the ruler; measured by `PREREG_001` |
| **Projection engine** | a point estimate per player-week | **a model, not a claim**, until a register pairs it against consensus |
| **Distribution engine** | floor/ceiling/boom-bust probabilities per player-week | a model; the claimed differentiator; measured by calibration registers |
| **Decision layer** | start/sit for *your* league: slots, scoring, opponent | a model; measured by disagreement-pair accuracy |

The engine's public claim, when it has one, will be phrased exactly like this: *on N disagreement pairs across W weeks at the `final` clock in half-PPR, the engine's pick out-scored consensus's pick X% of the time against a placebo-calibrated bar of Y%, verdict Z.* Anything less specific is a screen, not a claim.

## 2. The decision problem, stated properly

A start/sit decision is a choice between two roster-eligible players for one slot, made at a known time with known information, to maximise the probability of winning a head-to-head matchup — not to maximise expected points. That has three consequences that most projection systems ignore and that the finance framing makes natural.

The objective is a probability, so the engine must output **distributions**, not points. A lineup's score is a sum of order statistics (you start your best guesses), and Jensen's inequality bites: the one public repo that tested this found calibrated distributions turned a lineup optimiser's −15.8 points per season into +94.9. Two players with the same mean and different variance are different starts depending on whether you are the favourite or the underdog that week.

Players in the same game are **correlated** (a shootout lifts both quarterbacks; a blowout buries one side's passing game), so pairwise comparisons and lineup simulations must draw jointly by game, not independently by player.

Information arrives on a schedule, so the engine runs on two **clocks**, defined in `ffengine/asof.py`: `publish` (23:59 ET the night before the game — what a video recorded the night before could know) and `final` (kickoff minus 90 minutes — inactives are public). Every result names its clock.

## 3. Data architecture

Five layers, each readable only from the one below it.

**L0 — raw captures.** Built. `ffengine/store.py` stores each fetched body once by content hash and appends a manifest row for every capture, chained by hash so that editing, deleting or reordering history is detectable (`verify.py`). Thirty-five sources across three cadences (`sources.py`): daily for post-game stat files and archives, every three hours for injuries, rosters, depth charts, lines and Sleeper player state, every fifteen minutes on game days for the T-90 window. Only the nflverse side has been verified from where this was written; the Sleeper, Odds API and Open-Meteo adapters need their first run from your machine.

**L1 — canonical as-of tables.** Not built (ledger `P-008`, `P-009`). A function `build_frame(season, week, game_id, clock)` that calls `asof.load_*` with that game's cutoff and returns tidy tables keyed by `gsis_id`: availability, roster/depth, trailing production, lines, weather forecast, consensus. It never reads a file any other way. Every row carries the `capture_ts` it came from so `assert_no_future` can be called downstream.

**L2 — features.** The taxonomy in §5, each computed from L1 only, each with its own register before it enters a model.

**L3 — models.** §6.

**L4 — decision.** League scoring and roster slots from Sleeper (`/league/{id}` exposes `scoring_settings` and `roster_positions`), opponent's projected distribution, pairwise and lineup win probabilities by Monte Carlo with game-level correlation.

**L5 — ledger and report.** The weekly public record: calls, outcomes, disagreement scoring, calibration, corrections.

### Sources, with what they are for and what they cost

| source | what it gives the engine | clock availability | cost / terms |
|---|---|---|---|
| nflverse `games.csv` | kickoff, roof, surface, rest days, division flag, **closing** lines once played, current lines before | live; lines overwritten at close — snapshot | free, CC BY 4.0 (lines/weather PFR-derived) |
| nflverse injuries | official Wed/Thu/Fri practice status and game status | live; **no timestamps from 2025** — snapshot | free |
| nflverse depth charts (ESPN, 2025+) | daily timestamped depth ranks | live, `dt` field | free |
| nflverse weekly rosters | status incl. ACT/INA (post hoc) | post hoc only | free |
| nflverse stats_player_week, pbp, snap counts | targets, air yards, target/air-yards share, WOPR, RACR, EPA, xYAC, CPOE, snaps | post-game (stat corrections through Thursday) | free |
| FTN charting (2022+) | play action, motion, RPO, screens, blitzers, catchable/contested/drops | ~48 h after games | free with FTN attribution |
| Next Gen Stats | separation, cushion, time to throw, RYOE, YAC over expected | nightly, above minimum-attempt thresholds | free |
| PFR advanced stats | pressures, yards before/after contact, broken tackles, targets allowed by defender | daily | free, PFR-derived |
| participation / coverage (FTN via nflverse, 2023+) | man/zone, coverage shell, defenders in box, pressure | **post-season only** — useless live, fine for training | free, CC BY-SA |
| ffopportunity `ep_weekly` | expected fantasy points per player-week | post-game | free |
| FantasyPros ECR (DynastyProcess mirror; official API) | the consensus rank baseline; historical archive for backtests | live | mirror free (URL unverified from here); API free tier non-production, $5.99/mo personal |
| Sleeper `players`, `trending`, projections, league endpoints | injury/practice/news timestamps, depth order, sentiment, league scoring and rosters | live | free, **non-commercial only** |
| The Odds API | game lines and **player props** (pass/rush/rec yards, receptions, anytime TD); historical props from 2023-05-03 | live | 500 credits/mo free; $30/mo for 20k; props 5 credits per event per call |
| Open-Meteo | forecast at capture time (the feature a Saturday decision had); Historical Forecast API for backfill | live | free non-commercial |
| PFF Pro / Fantasy Points Data Suite / FTN Data | coverage grades, shadow assignments, man-vs-zone splits, WR/CB matchup grades — live | live | $199.99/yr (PFF Pro, API access announced), invite/subscription (Fantasy Points), $3,000/yr private (FTN) |

The last row is deferred (`P-010`): a coverage-scheme register is drafted first, and the feed is bought only if the register's power arithmetic says one season can see the effect.

## 4. Point-in-time discipline and the leakage catalogue

Every feature for a game is computed from captures at or before that game's cutoff on the named clock, and the cutoff is per game, not per week: Thursday-night actuals are known by Saturday, London games kick off before the Sunday inactive wave, Monday-night games see everything. The known leaks, each of which is a unit test in the harness when it exists:

1. Same-week `stats_player_week` rows (post-game) used as features.
2. Weekly roster `ACT`/`INA` status (compiled after the fact) used before T-90.
3. Roles defined from full-season data ("starter = 50%+ of season snaps") — roles are rolling and as-of.
4. Opponent strength computed over the full season — trailing windows only, heavily shrunk.
5. Closing lines used for a `publish`-clock decision — use the captured line at the cutoff.
6. Injury designations from the untimestamped 2025+ files treated as if known on Friday — only captures carry time.
7. Coverage/participation data (post-season release) used in a live-clock feature.
8. `pbp` pulled Monday versus Friday — pin the capture used to score a week (≥72 h after the last game).
9. Depth charts pre-2025 (week-keyed, capture time ambiguous) — use `dt ≤ cutoff` for 2025+, and treat earlier seasons as approximately `publish`-clock with the caveat attached.
10. Player IDs — join through `gsis_id` via nflverse `players`; `sleeper_id` for platform data; `pfr_id` for snaps; `espn_id` for depth charts.
11. Season boundaries — source drift (injuries schema change 2025, depth-chart source change 2025, participation source change 2023, NGS `ngs_air_yards` gone from 2024) validated explicitly per season.
12. Week-1 cold start and byes — 17 games, 6 bye weeks, roughly 14–16 usable observations per player per season; the harness prints effective sample size, never raw player-week counts.

## 5. Feature taxonomy — everything we can think of, with an honest prior on each

"Rigorous" does not mean "more features." It means every feature enters through a register with a mechanism, a verdict object and a pre-committed bar, and the ones that fail are closed in writing. The prior column is what the public literature and the sister project's experience say before any run; it decides the **order** registers are written, not their outcome.

### 5.1 Availability and role (mechanism: you cannot score from the bench)

| feature | source, clock | prior | how it enters |
|---|---|---|---|
| Game status (Out/Doubtful/Questionable) and practice participation (DNP/Limited/Full) trajectory Wed→Fri | injuries + Sleeper `practice_participation`; live | **strong** for availability; play probability by designation and practice pattern is estimable from 2009–2024 history (with `date_modified`) | play-probability model, fixed priors first (`DRAFT_002`), fitted later |
| Snap share, route participation, depth-chart rank and its daily changes | snap counts (post-game), depth charts `dt`; live for depth | **strong** as a role indicator; depth chart is noisy | rolling role state; depth-chart change as a regime flag |
| Teammate injury → opportunity redistribution (WR1 out → WR2/TE targets) | injuries + trailing shares | **moderate**; big when it happens, testable on history | conditional share model: who absorbs the vacated targets/carries, by team historical pattern |
| "Playing through it": Questionable-and-active efficiency decrement | injuries + post-game | unknown; plausible small negative | register after availability is settled |

### 5.2 Opportunity and volume (mechanism: fantasy points are volume × efficiency, and volume persists)

| feature | prior |
|---|---|
| Target share, air-yards share, WOPR, routes-run share, carry share, red-zone and goal-line share, snap share — trailing 2/4/6-game windows and their deltas | **strongest family in the literature**: target share year-over-year ≈ 0.74; the first engine arm is built on these alone |
| Expected fantasy points (ffopportunity xFP) and the actual-minus-expected residual | **moderate**: xFP is a good volume summary; the residual is mostly noise to regress |
| Team pass attempts / rush attempts / plays per game, pass rate over expectation, neutral-script pass rate, pace | **moderate**; the team-level scaffold for simulation |

### 5.3 Efficiency (mechanism: talent exists, but it is measured noisily and regresses hard)

| feature | prior |
|---|---|
| Yards per route run, aDOT, YAC over expected, EPA per target, RYOE, CPOE, success rate | **weak-to-moderate** as week-ahead predictors; useful as multi-season player priors, dangerous as recent-form signals |
| Touchdown rate (per target, per carry, per red-zone touch) | **weak**: year-over-year ≈ 0.10. Touchdowns are modelled from red-zone opportunity and team implied total, never from a player's recent TD rate |

### 5.4 Game environment (mechanism: the market has already priced the game)

| feature | prior |
|---|---|
| Vegas total, spread → implied team total, implied win probability → expected game script (pass-heavy when trailing) | **moderate-to-strong**; the one external input everyone agrees adds information. The captured line at the clock, never the close |
| Player props: receiving/rushing/passing yards lines, receptions, anytime-TD price | **potentially the strongest single external input** and the least studied publicly; history only from May 2023, so ≤3 seasons; costs credits. A dedicated register: do props add to consensus, or is consensus already props? |
| Line movement between captures | unknown; sentiment proxy |

### 5.5 Opponent and matchup (mechanism: defences differ — but by how much, and is it predictable?)

| feature | prior |
|---|---|
| Defence-vs-position points allowed (DvP), trailing | **weak**: within-season autocorrelation ≈ 0.05 (receiving) to 0.18 (rushing); the one public hierarchical model with opponent terms did not beat a 7-game rolling average. Enters as a register expected to fail; the failure is a video |
| Pass-funnel / run-funnel (opponent's EPA allowed by play type, pressure rate, defenders in box, coverage shell rates) | **weak-to-moderate**; more mechanistic than DvP; the funnel effect on *volume* is the testable part |
| Man-vs-zone rate and a receiver's man/zone splits; slot vs perimeter alignment vs opponent's slot coverage grade | **plausible, unmeasured publicly**; live data requires a paid feed; training data exists free (2023+ participation) — the register can be *backtested* on 2023–2025 before any money is spent |
| Cornerback shadow assignments (ESPN's weekly shadow report, Fantasy Points' WR/CB matchup report) | **plausible, small**; text sources, capture as-is and structure later |
| Home/away, rest days, short week, travel and time zones, altitude, primetime, division game, revenge narrative | **small-to-zero**; cheap to test, and each is a myth-busting Short |

### 5.6 Weather (mechanism: wind moves the ball; the rest mostly moves the narrative)

Wind above roughly 15 mph on passing volume and deep targets: **moderate, established**. Precipitation, temperature, snow: **small**. Roof state for retractables: unknown until game time; treat as outdoors at `publish`. Forecast at the clock is the feature; observed weather is only for scoring the forecast.

### 5.7 Regime changes (mechanism: the past stops predicting when the situation changes)

Quarterback change, offensive coordinator or head coach change, trade, star returning from injury, bye-week scheme resets. **Moderate-to-strong when present, rare.** A regime detector flags them; trailing windows reset to the regime start; the register measures whether resetting beats not resetting.

### 5.8 Seasonal priors (mechanism: who a player is before the season tells you something)

Age curves by position, rookie ramp curves, draft capital, contract year, offseason ADP as a market prior. **Moderate** as season-level priors; near zero as week-to-week signals. They enter as the prior in the hierarchical model, not as weekly features.

### 5.9 Meta-signals (mechanism: other people's information, timestamped)

Consensus rank itself (the baseline), the **spread** of expert ranks as an uncertainty measure, Sleeper trending adds/drops as sentiment, line movement. The spread is interesting: it may be the best free predictor of *variance*, which is what the distribution engine needs.

## 6. Model architecture

Layered, so each layer can be swapped and each has its own register. The first live version uses only layers 0–1 with fixed constants (`PREREG_DRAFT_002`), on purpose: if a deliberately dumb engine beats consensus, the win belongs to the mechanism, not to a model's flexibility, and if it does not, nothing more elaborate is likely to.

**Layer 0 — consensus-implied baseline.** Each position's historical points-by-rank curve (from the ECR archive and actuals) maps a consensus rank to an expected-points anchor. This is what the engine adjusts; it is also what it is scored against.

**Layer 1 — opportunity state.** A per-player state-space model of shares (targets, carries, routes, red-zone touches) with partial pooling by position and team, heavy shrinkage toward the trailing window, and regime resets. Deltas between the recent window and the consensus-formation window are the first adjustment.

**Layer 2 — team environment.** Expected plays, pass attempts and red-zone trips per team-game from pace, pass rate over expectation, and the captured line at the clock (implied total and win probability → game-script mix).

**Layer 3 — efficiency priors.** Multi-season, partially pooled per-player yards-per-opportunity and touchdown-per-red-zone-touch priors, updated slowly; recent efficiency enters only through the prior's posterior, never as a raw recent-form feature.

**Layer 4 — distribution.** Two competing arms, each its own register: (a) a structural Monte Carlo — draw team plays and pass/run mix from Layer 2, allocate shares from Layer 1, draw efficiency from Layer 3, score under the league's rules, with game-level correlation by construction; (b) a gradient-boosted quantile model (LightGBM quantile objectives at 0.1/0.25/0.5/0.75/0.9) trained walk-forward on the same L2 features, with a conformal calibration layer. The arm that calibrates better on held-out weeks (PIT histograms, interval coverage, pinball loss against an empirical-quantile baseline) is adopted; the other is kept as a check.

**Layer 5 — decision.** Given the league (Sleeper), the roster, and the opponent's projected distribution, compute pairwise P(A > B) for every candidate pair and lineup win probability by Monte Carlo with joint draws by game. The output is a start/sit ordering with probabilities, not a point projection.

Later arms, in the order the priors suggest: props as an input (§5.4), teammate-injury redistribution (§5.1), weather on passing (§5.6), regime resets (§5.7), coverage-scheme matchups backtested on 2023–2025 participation data before buying a feed (§5.5), and the folklore family (rest, primetime, revenge, DvP) run as one register with many arms, expected to return nulls, and filmed either way.

## 7. Evaluation protocol — the harness

This is the part that makes it an engine rather than a spreadsheet, and it is specified before the models on purpose.

**Universe.** Per position-week, the top-N by consensus rank at the clock (QB 24, RB 48, WR 60, TE 24), as fixed in `PREREG_001`. Scoring computed from stat lines in PPR and half-PPR; league-specific scoring from Sleeper when the decision layer runs.

**Baseline.** FantasyPros ECR (primary), Sleeper projections, a persistence floor, and the average of sources. Every engine statistic is paired against the baseline on the same player-weeks.

**Primary verdict object: disagreement-pair accuracy.** Among pairs where the engine and consensus order two players differently, the share where the engine's higher-ranked player scored more. The null is *not* 50%: an engine that is consensus plus noise picks the lower-consensus player on its disagreements and scores below 50%. So the bar is **placebo-calibrated** — 200 draws of consensus plus rank noise matched to the engine's disagreement rate, statistic recomputed per draw, bar at the 95th percentile, draws stored.

**Secondary objects.** Paired Δ-Spearman within position-week; MAE against the averaged projections; calibration of the distribution (coverage of 10/90 and 25/75 intervals, PIT histogram, pinball loss vs an empirical-quantile baseline); slot-boundary decision accuracy for 12-team leagues.

**Unit of independence.** The game. Standard errors cluster by `game_id`; bootstraps block by week (17 blocks a season, so CIs are wide and reported wide); effective sample size is printed, never raw counts.

**Power, printed before the verdict is read.** `MDE_50 = crit × se` and `MDE_80 = (crit + 0.84) × se`, both quoted, with power against the register's stated expectation. Illustrative, to be replaced by the census's real counts: at 600 disagreement pairs for one position in one season, the 80%-power detectable edge is about 5.7 percentage points; pooling four positions, about 2.9. One season cannot see a slightly better engine, and the design says so rather than reporting a null that means "invisible."

**Trial accounting.** Every register charges the counter; the t-hurdle is `max(2.0, √(2 ln N))` or the placebo bar, whichever is higher. Forward books charge at first verdict read and can be abandoned uncharged.

**Verdicts.** `ADOPTED` / `REJECTED` / `NULL` / `INCONCLUSIVE` / `DEFERRED`, plus `NO CONTRAST` when the engine and consensus barely disagree. A verdict-reader script prints the committed threshold from the register beside the number; nobody retypes a bar.

**Leakage tests.** The twelve items in §4 as unit tests: synthetic "future" rows injected into each source must never change a feature at any clock.

## 8. What is honestly backtestable, by era

| era | what exists | what it supports |
|---|---|---|
| 2009–2024 | injuries **with** `date_modified` (latest revision per player-week only), weekly rosters, pbp/stats, snap counts (2012+), NGS (2016+), FTN (2022+), participation with coverage (2016–2022 NGS; 2023–2024 FTN), ECR archive (if the DynastyProcess file resolves), PFR closing lines and kickoff weather | a partial point-in-time backtest of availability and opportunity features, with the caveat that Saturday downgrades overwriting Friday rows are lost; a full backtest of post-game-derived features; coverage-scheme registers on 2023–2024 |
| 2023-05 onward | The Odds API historical props at 5-minute snapshots (10 credits per market per region per pull) | a props-as-input register on ≤3 seasons, at a credit cost worth estimating first |
| 2025 | untimestamped injuries, timestamped depth charts, participation released after the season | depth-chart features as-of; injuries only approximately |
| 2026 onward | **everything captured live at both clocks** | the forward paper track — the real test |

The consequence is the same one the sister project reached: backtests where they are honest, a forward track for the verdict, and the scarce resource is calendar time to a decision, not trials. Launch forward books early and in parallel; spend backtest trials only where history can answer honestly (opportunity, availability, coverage on 2023–2024) or where a result gates a forward book's design.

## 9. The forward paper track

Pre-registered like `PAPER_TRACK_CONTRACT.md`: engine outputs at both clocks are written to the manifest before kickoff every week from the first live week; the ledger is scored from the pinned post-correction stats capture; the first read is after 2026 Week 18 (≈ 2027-01-14) and is labelled a read, not a verdict, unless the pre-stated bar is cleared in either direction; the verdict is on pooled 2026 + 2027 after 2027 Week 18 (≈ 2028-01-13). Adopting a change to the engine resets the clock, deliberately. The paid-tier decision for 2027 is made on the first read, on the rule written in `PREREG_DRAFT_002` §4, and nowhere else.

## 10. The public ledger

Published weekly from Week 4 (page plus the Monday video): every start/sit call at both clocks with its probability; the week's disagreement pairs and who was right; the running disagreement accuracy against the placebo band, with the CI; a calibration plot (stated probability vs realised frequency, cumulative); MAE versus the averaged free projections; the corrections record, with old values quoted and dated. What it never publishes: a headline without its clock, its scoring, its N and its bar.

## 11. Build phases

| phase | when | ledger rows | hours | outcome |
|---|---|---|---|---|
| 0 — capture breathing | this week | P-000, P-005, P-006 | 3–4 | timers on the VM; first dry-run of the API adapters; `verify` green for 7 days |
| 1 — ruler | by Week 6 | P-008, P-009, R-001 | 15–20 | scoring, universe builder, pairwise curve, block bootstrap, placebo, MDE printer; census reported once 10 weeks are captured (mid-November) |
| 2 — first arm live | Week 4 onward | R-002 | 8–10, then 1/wk | consensus + opportunity delta at both clocks, outputs pinned weekly; the ledger starts |
| 3 — distribution | November–December | new registers | 20–30 | Monte Carlo arm vs quantile-GBM arm; calibration registers; the decision layer on your own Sleeper league |
| 4 — backfill and historical registers | offseason | P-007 + registers | 30–50 | 2009–2024 availability/opportunity backtests; coverage-scheme register on 2023–2024; props register on 2023–2025; the folklore family |
| 5 — read and decide | Jan–Feb 2027 | R-002 first read | 5 | paid-tier decision on the committed rule; post-mortem video |

## 12. Running costs

Compute: the Oracle Always-Free VM, already paid for by being free; storage 15–40 MB a day in season. Data: everything required is free; The Odds API at $30 a month if props go beyond the free tier's 500 credits; FantasyPros Premium at $5.99 a month if the mirror is insufficient; PFF Pro at $199.99 a year only if a coverage register earns it. Total worst case in season one: roughly $50 a month, most of it optional.
