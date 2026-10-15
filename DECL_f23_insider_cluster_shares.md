# DECL — F-23: CLUSTERED INSIDER BUYING, IN SHARES (long book)

**Stage 3's forward leg.** `RESEARCH_CHARTER.md` §5: a Stage-2 survivor gets *"one read of the
1999-2008 five-theme proxy and a **forward paper book** on the `S3-I1` fleet harness."*
`DECISIONS.md` 2026-10-14: *"a forward paper book in shares on the registered construction,
started now so forward data accrues."*

**THE CONSTRUCTION IS `PREREG_insider_cluster_wide.md`'s, FROZEN, AND NOTHING HERE RE-CHOOSES
ANY OF IT.** That register (committed **ALONE at `1cc8b7e`**) confirmed the `cap >= $500M` tier at
`h`=63 on the one check-quadrant read: **+3.4888pp** market-adjusted over the next quarter,
cluster-robust *t* **+3.601 / +4.036**, **+2.9122pp net** of size-tiered costs, BH *p* 3.17e-04.
Stage 1 is `PREREG_insider_cluster.md` (`fd87870`).

**PAPER ONLY. NOTHING HERE LICENSES REAL MONEY, AND NO ORDER MAY BE PLACED AT A BROKER.**

---

## 1. THE CAVEAT THAT MUST TRAVEL WITH THIS BOOK — stated INSIDE the declaration

**THE CONFIRMED EFFECT IS CARRIED BY 2020-2022. IN 2023-2026 IT NETS ABOUT ZERO.** Measured in
the register's own §5a: the governing cell's late half is **+0.5319pp gross against 0.5766pp of
cost — −0.045pp net** — and it satisfied the both-halves clause only because each half is scored
against **its own** null and the late null's p95 is itself **negative** (−0.2420). That is the
rule as written and it is **not** the same claim as "the late half pays".

**A FORWARD BOOK TRADES THE FUTURE, AND THE FUTURE LOOKS LIKE THE LATE HALF.** So this book's
most likely honest outcome is `CANNOT-TELL`, and a `BLEEDS` verdict would be **consistent with
the register rather than a contradiction of it**. It is declared here, before the first fill, so
nobody reads a flat book as a surprise.

**AND THE EFFECT IS ONE CAP BAND.** The register's no-verdict band decomposition put essentially
all of it in **`$500M-$2B`** (+5.1841pp, *t* 3.90/3.62), the only band significant in both
quadrants, with `$10B+` at **−1.49pp** in the late half. **This book does NOT narrow to that
band** — narrowing would be a construction chosen on a diagnostic, which §2c of the register
forbids — so it knowingly holds names the diagnostic says contribute nothing.

---

## 2. THE FEED — and it is NOT VALIDATED, so this book CANNOT FILL YET

`DECISIONS.md`'s *"started now so forward data accrues"* needs filings that do not exist yet.
`insider_cluster.sf2_zip()` is a **FROZEN EXPORT ending 2026-10-02**, so the book cannot run on
it. `scripts/insider_live_feed.py` declares the SEC's own free feed — EDGAR's **daily index** plus
Form 4 XML for the live leg, and the SEC's quarterly **Insider Transactions Data Sets** (one
**8.66 MB** ZIP per quarter) as the validation instrument.

**THE BAR WAS DECLARED BEFORE THE COMPARISON RAN** — row recall **0.95**, event Jaccard **0.90**,
on 2026-07-01..2026-09-30, the overlap with SF2. **BOTH FAIL**, and the diagnosis is specific:

| key | recall | precision |
|---|---|---|
| ticker only | **1.0000** | 1.0000 |
| ticker + filing date | **0.9791** | 0.9915 |
| **+ owner name** | **0.8850** | 0.7748 |
| + owner name, SORTED TOKENS | 0.8850 | 0.7748 |

**THE TWO FEEDS AGREE ON WHICH NAMES BOUGHT AND WHEN, TO 98-99%, AND DISAGREE ON WHO THE INSIDER
IS.** Sorting the name tokens changes nothing, so it is not word order. **And it cannot be fixed
with a join key: SF2 has 24 columns and NOT ONE is an owner identifier** — only `ownername`, a
string — while the SEC supplies `RPTOWNERCIK`. So owner identity can only ever be matched by
spelling, and the two vendors spell differently (`FLORNESS DANIEL L` against
`Conifer Management, L.L.C.`).

**THAT IS THE TRIGGER ITSELF.** The rule fires on **`k` >= 2 DISTINCT `ownername`**, so a feed
that disagrees about owner identity disagrees about how many distinct buyers a cluster has.
Event-level agreement on the book's own universe is **Jaccard 0.8257** against the 0.90 bar.

**CONSEQUENCE, AND IT IS A REFUSAL RATHER THAN A WORKAROUND: NO FILL UNTIL THE FEED PASSES.**
Lowering the bar after watching it fail is what `W-28`'s rule forbids. The two routes a successor
may take are named, and **both are Don's call, not a lane's**: run the book on the SEC feed's own
`RPTOWNERCIK` identities end-to-end (exact, and a **different event set** from the one that
confirmed — about 83% overlap), or wait for an SF2 refresh and accept that the book is then fed by
a quarterly export rather than a live one.

---

## 3. WHAT IS FROZEN, verbatim from the register

* **The cluster rule:** `k` = 2 or more **DISTINCT** `ownername` filing an **OPPORTUNISTIC**
  open-market purchase (`transactioncode == "P"`, a missing code **COUNTED AND SKIPPED**) on one
  ticker inside a **30-calendar-day** window, dated at the **LAST** filing, **one event per
  cluster** under a full-window cooldown, with the **STRICT** condition that the pair traded in
  **each of the two prior calendar years**.
* **The universe:** `cap >= $500M` at the name's **POINT-IN-TIME** market cap — the most recent
  **prior** observation, never a future one (`A12`).
* **The horizon:** **`h` = 63** sessions, entered the session **after** the cluster is public.
  `h`=126 carries no verdict and is not traded.
* **The clock:** the **FILING** date. A transaction-date clock is look-ahead and is a void
  condition.

---

## 4. MACHINE-CHECKABLE DECLARATION

**`fills_needed` IS DERIVED, AND THE CONCURRENCY CAP IS DERIVED FROM IT.** The smallest `n` at
which `track_meter.boundary(n, sigma, rho, alpha)/n` falls to this book's own `min_effect` is
**1,111**. At the measured event rate of **310/year** that is **3.58 years** — *provided the cap
does not bind*. **At the fleet's customary cap of 10 the book is throughput-limited to 40 fills a
year and the horizon becomes 27.8 years.** A 63-session hold on 310 events a year implies **77.5
expected concurrent positions**, so **the cap is 100**: a lower cap would **refuse events**, and
the register's result is measured on **all** events, so a binding cap would make this book a
different construction from the one that confirmed.

**`sigma` IS MEASURED, NOT A PRIOR** — the per-event SD of the market-adjusted return on the
governing cell's own 1,093 banked rows, **28.0842pp**. `track_meter`'s rule binds: it may only
ever be **RAISED**.

```json
{
  "book": "f23_insider_cluster_shares",
  "domain": "equity",
  "hypothesis_class": "edge",
  "side": "long",
  "sells_premium": false,
  "entry_rule": "Daily, on the FILING-DATE clock (filingdate, never transactiondate): a CLUSTER fires when 2 or more DISTINCT ownernames file an OPPORTUNISTIC open-market purchase (transactioncode P; a missing code is COUNTED AND SKIPPED, never read as not-a-purchase) on one ticker inside a 30-calendar-day window, with the STRICT condition that each insider of the pair traded in EACH of the two prior calendar years. The event is dated at the LAST filing of the cluster and one event fires per cluster under a FULL-WINDOW cooldown. Enter the session AFTER the cluster is public, at a real quote. Eligible only if the name's most recent PRIOR point-in-time market cap is at least 500 million USD. Frozen from PREREG_insider_cluster_wide.md; no parameter is chosen here.",
  "structure": {
    "strike_selection": "fixed",
    "strike_selection_note": "THIS BOOK HOLDS SHARES AND HAS NO STRIKE. `strike_selection` is a REQUIRED field of the harness and its vocabulary is option-shaped (moneyness/fixed/delta), so `fixed` is declared as the only value that asserts nothing about an option. THIS IS THE FLEET'S FIRST EQUITY BOOK -- no existing DECL_ declares domain equity -- so the harness has never been asked an equity question before. Reported, not edited: fleet.py is the S3-I1 lane's.",
    "instrument": "common shares, long, no leverage, no options",
    "entry": "market-on-open the session after the cluster is public, recorded at the real quote",
    "exit": "hold 63 sessions, then exit. No stop, no target, no discretion.",
    "horizon_sessions": 63
  },
  "universe": "Corrected full raw universe (UNIVERSE_BIAS_PANEL_full) names whose most recent PRIOR quarterly market cap is at least 500 million USD. NEVER data/backtest, whose top-3000-by-today's-cap selection is selection on a present-day property.",
  "sizing": "equal dollar per event, 1/100 of book equity per fill, no leverage, no pyramiding into the same name while a position is open",
  "concurrency_cap": 100,
  "records_schema": [
    "cluster_last_filing_date",
    "cluster_distinct_owners",
    "cluster_window_lo",
    "market_cap_at_entry",
    "cost_bps_one_way_at_entry",
    "feed_source",
    "feed_validation_sha"
  ],
  "verdict_horizon": {
    "expected_fills_per_month": 25.83,
    "expected_fills_per_month_basis": "310 events/year measured on the check quadrant's governing cell scaled to both ticker halves, divided by 12. It is an ORDER OF MAGNITUDE and not a forecast: the forward universe is the live one rather than a ticker half.",
    "min_effect": 2.9122,
    "min_effect_basis": "the register's own NET figure for the governing cell: +3.4888pp gross less the 0.5766pp event-weighted size-tiered round trip. NET, because a gross bar would let the book pass while losing money.",
    "sigma": 28.0842,
    "sigma_provenance": "MEASURED on this construction's own 1,093 banked check-quadrant rows (per-event market-adjusted return SD). Not borrowed across books or across perturbation sizes (MB8).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 1111,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED; no round number appears anywhere in this horizon.",
    "earliest_honest_read": "3.58 years from the first fill at 310 fills/year (1,111 fills), AND ONLY IF THE CAP DOES NOT BIND. At the fleet's customary cap of 10 a 63-session hold allows 40 fills/year and the horizon is 27.8 years -- which is why the cap is 100 and why a lower cap would be a different construction. No fill has occurred: the feed is NOT validated (section 2), so the clock has not started.",
    "years_to_horizon_at_projected_rate": 3.58,
    "power_gate_note": "Anytime-valid, so a fixed-n power vocabulary does not apply directly: the boundary IS the threshold at every n. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/min_effect)^2 = 730, reported beside it so both vocabularies are on the face. AND THE REGISTER'S OWN WARNING APPLIES TO THIS BOOK: the realised clustered se ran 1.41x to 1.63x the scaled prediction in all five check cells, so this horizon should be read as optimistic by roughly that factor."
  },
  "verdict_grammar": [
    "PAYS",
    "BLEEDS",
    "CANNOT-TELL(horizon)"
  ],
  "trial": {
    "domain": "equity",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```

---

## 5. Void conditions

1. **A fill before the feed validation passes** its declared row and event bars (§2).
2. **Any bar in §2 or §4 lowered** after being watched (`W-28`).
3. **Backfill.** Nothing dated before this declaration's commit counts, and the harness's
   declaration-before-fill check is what enforces it against git.
4. **A transaction-date clock**, or a blank/sale code counted toward a cluster.
5. **Narrowing to the `$500M-$2B` band**, or to any population the register did not declare.
6. **A real order at a broker**, or any sizing percentage set by a lane.
7. **The late-half caveat dropped** from any statement of this book's result (§1).
8. **Retirement rule:** a `NOT CONFIRMED` older-data read retires this book with that result.
   **The older-data rung is instead recorded as NOT REACHABLE on free data** — the construction
   emits **31 events, all in 2008**, at **6.3%** power, and the SEC's curated set starts 2006 Q1
   so its first emittable year is also 2008 (**zero gain**). **So the book CARRIES ON and says
   so**, which is `DECISIONS.md` 2026-10-14's own instruction for that branch.
