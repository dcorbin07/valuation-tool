# PRE-REGISTRATION — O6 + O7 + O17, the earnings-and-surface-selection family

**One register, three items, committed ALONE before any measurement code exists.** Ledger rows
`O6` (cheapest-on-surface selection), `O7` (earnings straddles) and `O17` (earnings filter for the
long arm), all `OPEN`.

---

## §0 SCOPE FACTS, ALL MEASURED BEFORE THIS REGISTER WAS WRITTEN

No outcome, expectancy or verdict was computed first. These are structural facts only, and two of
them change what may be claimed.

### §0.1 The ledger is WRONG about two of these three rows, and the audit text exists

`VALQUO_LEDGER.md` marks `O6` **`src=auto`** with the note *"prose mentions only, no section, no
commit"* and `O17` **`src=auto`** with *"no mention anywhere in the corpus"*. **Both notes are
false.** `VALQUO_EDGE_AUDIT.md:964` is a full O6 section specifying four named sub-rules, and
`:1150` is a full O17 section specifying four named rules plus an interaction requirement. **The
definitions below are therefore QUOTED from the audit, not invented by me** — which is the opposite
of what `src=auto` would have licensed. The ledger rows are corrected as part of this item.

### §0.2 Earnings coverage is FAR BETTER than the tree's own caveat says — and its hole is systematic

`valuation/edge/bulk.py` warns that EVENTS code 22 *"appears ~2.83 times per ticker per year, not
the ~4 a full quarterly calendar would give, so EVENTS coverage of earnings is PARTIAL."* **On this
book's 186 megacaps that figure is wrong in the reassuring direction: median 3.96 and mean 4.14
dates per ticker-year, and only 0.3% of entries show an entry-to-next-announcement gap over 120
days** (the signature of a missed announcement). The 2.83 is a repo-wide average over 17,779 mostly
thin tickers and does not describe this universe. **89.1% of banked entries have both a prior and a
next announcement date.**

**The real hole is not thinness, it is a systematic exclusion, and it is the single most dangerous
fact in this register.** **29 of 186 names have ZERO earnings dates, carrying 388 trades =
10.0% of the book**, and *every one of them is a foreign private issuer*:

> AEM, ARM, ASML, AZN, BABA, BHP, BMO, BN, BNS, BTI, BUD, CM, CNQ, GSK, NTES, NVO, NVS, PDD, RIO,
> SHEL, SONY, SPOT, SU, TD, TM, TSM, TTE, UBS, UL

Foreign private issuers file 20-F and 6-K rather than 8-K, so code 22 cannot see them. **A filter
that reads "no earnings date" as "no announcement" therefore FAILS OPEN on a systematically
non-random tenth of the book** — disproportionately non-US, and this lane has already refused once
to ship an earnings filter with exactly that failure mode (`EarningsCalendar.unknown_means_safe`,
`HANDOFF_optionsbot.md` §1526). **Fixed here in advance: the 29 zero-coverage names are EXCLUDED
from every O17 and O7 arm and their exclusion is reported as a coverage figure. A missing earnings
date is UNKNOWN and never SAFE.** O6 does not use earnings data and keeps the whole book.

### §0.3 O6 is computable on the EOD cache, and NOT on the freeze — the door O21 left open

O21 established that **a contract the book never held has no forward price path in the frozen
chains**, because the freeze stores a full chain only on ENTRY dates (median 2 chain dates), and
recorded that closing it *"needs a re-mine"*. **That is true of the freeze and false of the EOD
option cache**, which carries daily NBBO for the whole chain. Measured on 60 randomly sampled
banked trades: **60 of 60 have their entry-date chain, 60 of 60 have a forward path on an
alternative contract to the banked exit**, with a median of **27** alternative candidates at the
same expiry and a median of **11** chain-days on the alternative. **So O6 is answerable today
without a re-mine.** The instrument is `data/options/<TKR>/<TKR>-<YEAR>.pkl`; the freeze is used for
nothing in this register.

### §0.4 O7's coverage is the weakest of the three and is declared now, not discovered later

On a 25-name sample, **only 46.2% of earnings events (925 of 2,001) have BOTH a pre-window and a
post-window chain day.** The full-book figure will be reported. **The COVERAGE RULE governs: the
covered and uncovered events are compared on observable characteristics (market cap, quoted spread,
year) and any systematic difference is reported beside the result**, exactly as O10/O18 did for its
71.6%. If coverage lands below **40%** on the full book, the O7 backtest arm is reported as
**COVERAGE-BOUND** and carries no verdict.

## §1 DISCLOSED PRIOR KNOWLEDGE

Seen before this register was fixed; no outcome of any arm here has been computed.

* **R2: the options ENTRY signal is dead** — the alert book returns +3.2702%/trade against a
  five-seed random-entry control at +8.3342%, a **−5.0640pp** gap. **This register does not re-open
  R2 and cannot.**
* **O13**: the anti-signal is entirely within-bin, so composition fixes aim at the wrong thing; and
  `entry_spread_pct` q5 reads −7.41%, the worst bin in the book.
* **O18**: a real trade pays **ρ = 0.6743** of the quoted half-spread. **A straddle crosses four
  times on a round trip**, which the audit itself flags as likely fatal to O7.
* **O21**: `q = 0` is used throughout this project; it understates solved IV by a median 0.00617.
* The banked book carries `term_slope`, which **O16/O17's audit text says may be partially explained
  by the earnings calendar** — the interaction is required below, not optional.
* Book: **3,870 closed split-clean trades, 186 names, 2016-01-19 → 2025-10-15**, 100% calls, 100%
  `swing` (O13: `opt_right` and `horizon` are degenerate).

## §2 THE THREE ITEMS — DEFINITIONS FIXED HERE

### §2.1 O6 — cheapest-on-surface contract selection (4 arms)

**Held fixed:** the entry date, the expiry, and the holding period in calendar days. **Only the
STRIKE changes.** Candidates are the calls on the entry date at the **same expiry** as the banked
contract, within the engine's own **0.90–1.20 moneyness** band, excluding the banked strike itself.

**A DELIBERATE DEVIATION FROM THE AUDIT, STATED NOW.** The audit says *"keep the entry signal and
the exit exactly as they are"*. The banked exit is a target/stop on the **actual contract's**
premium path, which cannot be applied to a contract the book never held without confounding
selection with path-dependent exit dynamics. **So the horizon is matched instead: every arm,
INCLUDING the incumbent, is re-priced over the same holding period in days.** The incumbent
re-priced under this rule is control **C1** and its divergence from the banked P&L is reported.

The four rules are the audit's own, quoted:

| arm | rule (audit §O6) |
|---|---|
| **A1 — O6a** | among candidates within ±0.05 delta of the banked target delta, pick the **lowest implied vol** |
| **A2 — O6b** | pick the lowest IV **relative to that name's own trailing 252-day IV rank** |
| **A3 — O6c** | pick the lowest IV **relative to the fitted smile** — a quadratic fit of IV on log-moneyness across that date's chain, then the largest negative residual |
| **A4 — O6d** | pick the highest **vega / spread-cost** ratio |

Entry at the ask, exit at the bid (`DEFAULT_AGGRESSION = 1.0`), matching the book.

### §2.2 O7 — earnings straddles (2 arms)

Gao, Xing and Zhang (2018, *JFQA* 53(6), 2587–2617): ATM straddles bought **three days before** an
announcement and held through it earn **+3.34%**. **The published sign is declared now: straddles
are UNDERPRICED, so the tradeable side is LONG.** This inverts the retail "sell the IV crush" view
and inverts the project's own roadmap item #24.

* **B1 — the diagnostic.** Implied move = ATM straddle price / spot at the pre-window date; realised
  move = |return| over the announcement window. **Reports the distribution of realised − implied,
  pooled and by market-cap tier.** The audit calls this *"valuable regardless of the strategy
  result"* and it is the cleanest test of whether this universe's options are rich or cheap.
* **B2 — the backtest.** Buy the ATM straddle 3 calendar days before, close the day after, **net of
  four spread crossings** at the book's own aggression.

Conditioners the paper names (firm size, past earnings-surprise volatility, option volume) are
**EXPLORATORY, carry NO verdict and are charged zero trials.**

### §2.3 O17 — earnings filter for the long arm (4 arms)

The audit's own four rules, quoted, applied to the banked book:

| arm | rule (audit §O17) |
|---|---|
| **C1 — 5d** | do not open within **5** calendar days before an announcement |
| **C2 — 10d** | do not open within **10** calendar days |
| **C3 — 15d** | do not open within **15** calendar days |
| **C4 — OWN-THE-EVENT** | open only where the **expiry falls after** the next announcement |

C4 is close to the opposite of C1–C3, deliberately, because O7's published sign says owning the
event may be favourable while paying decay into it and exiting first is not.

**REQUIRED, NOT OPTIONAL (audit §O17): the interaction with `term_slope` is reported** — the
marginal effect of each filter conditional on `term_slope` tercile, and of `term_slope` conditional
on the filter. **Reported, not verdicted**: it is a decomposition, not a fifth arm.

## §3 STATISTICS AND CALIBRATED BARS

**Every bar is a permutation null's p95, never the conventional 2.0.** 2,000 draws, seed
**20260812**, month-block bootstrap for every interval (R3's standing rule; a trade-level *t* is
never quoted).

* **O6's null is the sharpest thing in this register and is the reason it is worth running:** the
  comparison is against **switching to a RANDOM alternative contract** drawn from the identical
  candidate set, matched trade for trade. Any contract switch moves expectancy; this asks whether
  **cheapness specifically** does. A raw improvement over the incumbent is **not** evidence.
* **O7's null** is the same straddle construction on **random non-announcement dates**, matched per
  name and count — R2's random-entry design, reused.
* **O17's null** is **removing a RANDOM subset of the same size**, matched per arm. A filter that
  removes trades changes expectancy mechanically; this asks whether removing *these* trades does.

**Both halves** at the book's median entry date for every arm carrying a verdict.

## §4 VERDICT RULES — FIXED BEFORE ANY NUMBER EXISTS

**O6 arm is a CANDIDATE iff, in BOTH halves:** expectancy improvement over the incumbent is
positive **AND** exceeds that arm's own random-alternative-contract p95, **AND** tail concentration
does not rise (the audit's own clause: share of total P&L in the top 5 trades).

**O7-B1 returns a DIRECTION, not a pass/fail:** RICH if realised − implied is negative with a
month-block CI95 excluding zero, CHEAP if positive and excluding zero, otherwise **NULL**.
**O7-B2 is a CANDIDATE iff** expectancy is positive net of four crossings, in both halves, above
the non-announcement-date p95.

**O17 arm is a CANDIDATE iff, in BOTH halves:** expectancy improvement is positive **AND** exceeds
the matched random-removal p95, **AND** it retains at least **70%** of trades (a filter that
achieves its number by refusing almost everything is a different product, and the audit itself
calls this a one-line rule, not a new strategy).

**Ambiguous against any bar is a NULL** (`RUN_RULES` A6).

## §5 WHAT A POSITIVE WOULD AND WOULD NOT MEAN — THE DEAD-ENTRY FRAMING, FIXED FIRST

**The entry signal is dead (R2) and nothing in this register can revive it.**

* A CANDIDATE here is a **candidate for a FUTURE book that does not yet exist.** It is **not**
  evidence the alert signal works, **not** a revival of the options entry, and **not** an adoption.
* **O6 is the one arm whose positive would be genuinely portable**, because contract selection is
  logically independent of which name is chosen. **To separate those two things the four rules are
  ALSO run on the five-seed random-entry control book.** That control arm carries **NO independent
  verdict** — it is used solely to classify a primary result as *"contract selection carries
  information generally"* versus *"only on these alert days"*, and is charged **zero trials**
  because it can produce no claim of its own.
* **Nothing is adopted in this session whatever the result.** `pick_contract` is untouched; a
  material result is **routed to Don**, because changing contract selection re-prices every options
  figure the project publishes.

## §6 EXPECTATIONS — WRITTEN DOWN FIRST

| # | expectation | confidence |
|---|---|---|
| E1 | No O6 arm reaches CANDIDATE against the random-alternative null | 65/35 |
| E2 | O6's raw improvement over the incumbent is positive for at least one arm, but does NOT clear its own null — i.e. the null is what kills it | 70/30 |
| E3 | O7-B1 returns **RICH** (implied move exceeds realised) on this megacap universe, contradicting Gao–Xing–Zhang's published sign | 60/40 |
| E4 | O7-B2 is negative net of four crossings even if B1 says cheap | 80/20 |
| E5 | No O17 arm reaches CANDIDATE | 70/30 |
| E6 | C4 (own the event) beats C1–C3 (avoid the event) in point estimate | 55/45 |
| E7 | The `term_slope` interaction is material — the filters and `term_slope` overlap substantially | 50/50 |

## §7 TRIAL COST

**10 options trials: 4 (O6a–d) + 2 (O7 diagnostic, O7 backtest) + 4 (O17 rules).**
Options `N` **261 → 271**. **Equity and infra `N` untouched.**

Charged in full. The random-entry control arm, the `term_slope` decomposition, the O7 conditioners
and every C-control are charged **zero** — they carry no verdict and can produce no claim.

## §8 VOID CONDITIONS

1. Fewer than **2,000** banked trades survive O6's candidate requirement, or fewer than **500**
   usable earnings events survive for O7, or O7 full-book coverage below **40%** (that arm becomes
   COVERAGE-BOUND rather than voiding the register).
2. Any change after an outcome number is read to: the four O6 rules, the moneyness band, the
   matched-holding-period rule, the O7 windows, the four O17 rules, the 70% retention floor, the
   null constructions, the seed, the draw count, or any verdict rule.
3. Treating a missing earnings date as "no announcement" anywhere, or including any of the 29
   zero-coverage names in an O7 or O17 arm.
4. Adding a fifth O6 rule or a fifth O17 rule after seeing the first four.
5. Quoting any arm as an adoption, or as evidence about the options ENTRY signal.
