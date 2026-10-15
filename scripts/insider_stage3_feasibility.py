# -*- coding: utf-8 -*-
"""`INSIDER-STAGE3` — IS THE OLDER-DATA RUNG REACHABLE AT ALL? Feasibility only, ZERO TRIALS.

    python -m scripts.insider_stage3_feasibility

**NO HYPOTHESIS, NO BAR, NO VERDICT, AND NO FORWARD RETURN IS EVER LOADED** — this is a census of
what dates the frozen construction can emit an event on, plus the power that window would have.
The `S25` class: a fact about what data exists.

**IT READS THE FREEZE'S RAW SF2, WHICH IS WHAT THE CONSTRUCTION ACTUALLY READS** — the manager's
figure came from `data/backtest/insiders.csv`, and `valuation/studies/insider_cluster.sf2_zip`
points at `data/backtest_freeze_2026-10/raw/SHARADAR_SF2_2026-10-04.zip`. Those are two different
files (`INSIDER-CLUSTER` measured `data/backtest`'s top-3,000-by-today's-cap selection costing
**4.17×** the open-market purchase rows), so the gap is re-measured on the one that governs rather
than inherited.

**THE CLUSTER RULE'S TWO-PRIOR-YEAR CONDITION IS THE BINDING CONSTRAINT, NOT THE FIRST FILING
DATE.** `prior_year_presence(strict=True)` requires each insider of the pair to have traded in
**each of the two prior calendar years**, so the first year that can emit an event is the first
filing year **plus two** — and that is derived here from the shipped predicate rather than
asserted.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402

OUT = "INSIDER_STAGE3_FEASIBILITY.json"

#: The charter's Stage-3 window. The question is whether the construction can emit events in it.
PROXY_LO, PROXY_HI = "1999-01-01", "2008-12-31"


def sf2_census() -> dict:
    """Filing-year counts of OPPORTUNISTIC-eligible open-market purchase rows, from the FREEZE.

    Counts are by **filing** date, which is what the cluster rule dates an event on — a trade
    dated 2007 and filed 2008 is public in 2008 and the rule may not use it earlier. That is the
    point-in-time convention `A9` fixes and it is why the census is on `filingdate`.
    """
    z = IC.sf2_zip()
    if not os.path.isfile(z):
        return {"status": "ABSENT", "path": z}
    t0 = time.time()
    cols = ["ticker", "filingdate", "transactiondate", "transactioncode", "ownername"]
    df = pd.read_csv(z, usecols=cols, dtype=str, low_memory=False)
    out = {"path": os.path.basename(z), "rows_total": int(len(df)),
           "seconds_to_read": round(time.time() - t0, 1)}

    code = df["transactioncode"]
    out["rows_missing_transactioncode"] = int(code.isna().sum())
    # The register's SKIP rule: a missing code is COUNTED and never read as "not a purchase".
    buy = (code == IC.PURCHASE_CODE).fillna(False)
    out["rows_purchase_code_P"] = int(buy.sum())

    for label, col in (("filing", "filingdate"), ("transaction", "transactiondate")):
        d = pd.to_datetime(df.loc[buy, col], errors="coerce")
        ok = d.notna()
        out["%s_date_min" % label] = str(d[ok].min().date()) if ok.any() else None
        out["%s_date_max" % label] = str(d[ok].max().date()) if ok.any() else None
        out["%s_date_unparseable" % label] = int((~ok).sum())
        yr = d[ok].dt.year
        counts = yr.value_counts().sort_index()
        out["%s_year_counts" % label] = {int(k): int(v) for k, v in counts.items()
                                         if int(k) <= 2012}
    return out


def first_emittable(census: dict) -> dict:
    """The first date the FROZEN construction can emit a cluster event — DERIVED, not asserted.

    **TWO DIFFERENT DATE COLUMNS BIND, AND READING ONLY ONE GETS THE ANSWER WRONG.** Measured in
    the shipped source rather than assumed:

      * the event is **dated at the LAST FILING** (the register's own wording), so no event can
        exist before the first `filingdate`; and
      * `prior_year_presence` keys on **`transactiondate`** years — it requires the same
        `(ticker, ownername)` pair to appear with transaction year `yy-1` **and** `yy-2`.

    So the first emittable year is `max(first_filing_year, first_transaction_year + 2)`, and
    whether the `+2` or the filing floor binds is an empirical question about this file rather
    than arithmetic. **`insider_cluster.py:178` is the line that makes it transaction years**, and
    a census that looked only at filing dates could be wrong in either direction.

    The `+2` itself is read off the SHIPPED predicate with a positive AND a negative probe, so it
    is measured rather than restated from a docstring.
    """
    fy = sorted(int(y) for y in (census.get("filing_year_counts") or {}))
    ty = sorted(int(y) for y in (census.get("transaction_year_counts") or {}))
    if not fy or not ty:
        return {"status": "NO YEARS"}
    f0, t0 = fy[0], ty[0]

    # PROBE THE SHIPPED PREDICATE. One synthetic pair with transaction years {t0, t0+1, t0+2}:
    # the predicate must say NO for the first two and YES for the third.
    rows = []
    for y in (t0, t0 + 1, t0 + 2):
        rows.append({"ticker": "PROBE", "ownername": "A B",
                     "transactiondate": "%d-06-15" % y})
    probe_df = pd.DataFrame(rows)
    got = IC.prior_year_presence(probe_df)
    probe = {str(t0 + i): bool(got[i]) for i in range(3)}
    # NEGATIVE CONTROL: a pair with a GAP (missing yy-1) must be refused, or the predicate is
    # only testing "has any history" and the strict condition is not what it says.
    gap = pd.DataFrame([{"ticker": "G", "ownername": "C D", "transactiondate": "%d-06-15" % y}
                        for y in (t0, t0 + 2)])
    gap_got = IC.prior_year_presence(gap)

    first_yes = min((int(k) for k, v in probe.items() if v), default=None)
    derived = max(f0, t0 + 2)
    return {"first_filing_year": f0, "first_transaction_year": t0,
            "predicate_probe_by_transaction_year": probe,
            "predicate_first_yes": first_yes,
            "predicate_plus_two_measured": bool(first_yes == t0 + 2),
            "negative_control_a_gap_year_is_refused": bool(not gap_got.any()),
            "first_emittable_year": int(derived),
            "which_constraint_binds": ("the FILING floor" if f0 >= t0 + 2
                                       else "the two-prior-TRANSACTION-year condition"),
            "WHY": ("an event is dated at the LAST FILING so none can precede the first "
                    "filingdate, while prior_year_presence keys on TRANSACTION years -- so the "
                    "answer is max(first_filing_year, first_transaction_year + 2) and which term "
                    "binds is an empirical fact about this file")}


def proxy_overlap(census: dict, first_year) -> dict:
    """How much of the charter's 1999-2008 proxy window the construction can reach. ZERO is a
    legitimate answer and is the one this expects."""
    if first_year is None:
        return {"status": "UNKNOWN"}
    hi = int(PROXY_HI[:4])
    usable = max(0, hi - int(first_year) + 1)
    return {"proxy_window": [PROXY_LO, PROXY_HI],
            "first_emittable_year": int(first_year),
            "usable_years_inside_the_proxy_window": usable,
            "reachable": bool(usable > 0)}


def power_of_a_window(n_events: int) -> dict:
    """The power a window of `n_events` would have, from `INSIDER-WIDE`'s own realised `se` and
    its own measured era correction. **STATED BEFORE ANY OUTCOME**, which is the whole point.

    `INSIDER-WIDE` §5d measured the realised cluster-robust `se` running **1.41x to 1.63x** the
    `sqrt(n_build/n_check)` prediction, in all five cells, one direction — so the ~1.5x correction
    is applied rather than ignored. `MB8`: the `se` is this construction's own, never borrowed.
    """
    from valuation.edge import power_gate as PG
    a = _wide_arm()
    if not a:
        return {"status": "NO BANKED ARM"}
    gov = a["cells"]["cap_ge_500m_h63"]
    se_c = float(gov["se_worst_pp"]) / 100.0
    n_c = int(gov["n_events_scored"])
    eff = float(gov["mean_pp"]) / 100.0
    net = float(gov["net_of_cost_pp"]) / 100.0
    cost = float(gov["roundtrip_cost_pp_mean"]) / 100.0
    if n_events <= 0:
        return {"n_events": 0, "status": "NO EVENTS -- the window emits none"}
    # Scale the CHECK cell's realised se to the candidate n, then apply the measured era penalty.
    se_raw = se_c * (n_c / float(n_events)) ** 0.5
    se = se_raw * ERA_PENALTY
    return {"n_events": int(n_events),
            "anchor_cell": "cap_ge_500m_h63", "anchor_n": n_c,
            "anchor_se_pp": se_c * 100.0, "anchor_gross_pp": eff * 100.0,
            "anchor_net_pp": net * 100.0, "anchor_cost_pp": cost * 100.0,
            "se_scaled_pp": se_raw * 100.0, "era_penalty": ERA_PENALTY,
            "se_with_era_penalty_pp": se * 100.0,
            "mde80_pp": (2.0 + PG.z_for_power(0.80)) * se * 100.0,
            "power_gross": PG.power_at(eff, se, crit=2.0),
            "power_net_vs_cost_bar": PG.power_at(net, se, crit=2.0) if net > 0 else 0.0,
            "expected_t_gross": eff / se, "expected_t_net": net / se,
            "ERA_PENALTY_WHY": ("INSIDER-WIDE section 5d measured the realised clustered se at "
                                "1.41x-1.63x the sqrt(n) prediction in ALL FIVE cells, one "
                                "direction, so the midpoint is applied rather than ignored")}


#: `INSIDER-WIDE` §5d's measured range was 1.41x-1.63x; the midpoint is used and the range ships.
ERA_PENALTY = 1.5
ERA_PENALTY_RANGE = (1.41, 1.63)


def _wide_arm() -> dict:
    p = D.out_path("INSIDER_WIDE_ARM.json")
    if not os.path.isfile(p):
        return {}
    return json.load(io.open(p, encoding="utf-8"))


def events_per_year_from_the_check_cell() -> dict:
    """The observed event RATE, so a candidate window's `n` is derived rather than guessed.

    Taken from the banked rows of the governing cell — the same construction, the same cap floor —
    rather than from a rule of thumb.
    """
    p = D.out_path("INSIDER_WIDE_ROWS_cap_ge_500m_h63.pkl")
    if not os.path.isfile(p):
        return {"status": "ABSENT"}
    r = pd.read_pickle(p)
    yrs = pd.to_datetime(r["date"]).dt.year
    by = yrs.value_counts().sort_index()
    span = int(yrs.max()) - int(yrs.min()) + 1
    return {"n_events": int(len(r)), "year_min": int(yrs.min()), "year_max": int(yrs.max()),
            "years_spanned": span, "events_per_year": float(len(r)) / span,
            "by_year": {int(k): int(v) for k, v in by.items()},
            "CAVEAT": ("this is the CHECK quadrant's rate on ONE ticker half; a pre-2009 window "
                       "would be a different era with a different filing population, so it is "
                       "an ORDER OF MAGNITUDE and not a forecast")}



def banked_pre2009_events() -> dict:
    """The events the FROZEN construction actually emits before 2009 — from the banked census.

    Not re-derived: `INSIDER-CLUSTER`'s event set is the object the register declares unchanged,
    and re-building it here would be a second construction of it (`B7`).
    """
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % IC.K_PRIMARY)
    if not os.path.isfile(p):
        return {"status": "ABSENT"}
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    pre = ev[ev["era"] == "pre2009"]
    yrs = pre["date"].str[:4].value_counts().sort_index()
    return {"n_events": int(len(pre)), "n_tickers": int(pre["ticker"].nunique()),
            "date_min": str(pre["date"].min()) if len(pre) else None,
            "date_max": str(pre["date"].max()) if len(pre) else None,
            "by_year": {str(k): int(v) for k, v in yrs.items()},
            "by_ticker_half": {str(k): int(v) for k, v in pre.groupby("half").size().items()}}


def decide(out: dict) -> dict:
    """The outcome, on the terms `DECISIONS.md` 2026-10-14 and the prompt set in advance.

    Two routes to the SEC's free data and they give DIFFERENT answers, which is the whole finding:

      * the SEC's own **curated** Insider Transactions Data Sets start **2006 Q1**, so the two
        prior calendar years observable are 2006 and 2007 and the first emittable year is
        **2008** — **exactly what owned data already gives. ZERO GAIN.**
      * **raw** Form 4 XML on EDGAR is mandatory from **2003-06-30** (Release 33-8230), so
        2004 and 2005 are observable and the first emittable year is **2006** — which buys
        **2006 and 2007**, two years.

    Either way the reachable window is at most **2006-2008, three of the charter's ten proxy
    years**, all three adjacent to the build window and dominated by the GFC. **That is a real
    limitation of the rung and not of this measurement.**
    """
    n31 = (out.get("banked_pre2009") or {}).get("n_events") or 0
    rate = (out.get("observed_rate") or {}).get("events_per_year")
    sz = _sec_size()
    owned = power_of_a_window(n31) if n31 else {"status": "NO EVENTS"}

    # The event count a 2006-2008 window would carry is UNKNOWN until built, so it ships as a
    # RANGE with each end's basis named rather than as one number. `INSIDER-WIDE`'s §5d lesson:
    # a scaled figure is an estimate and must say so.
    scen = {}
    if rate:
        both = rate * 2.0            # the observed rate is ONE ticker half
        for label, mult, why in (
                ("low_recent_era_rate", 1.0,
                 "the check quadrant's own observed rate, both ticker halves, times 3 years"),
                ("high_2008_filing_volume", 4.151,
                 "scaled by the MEASURED ratio of 2008's P-row filing volume to the recent "
                 "per-year rate (108,320 against 26,092), because 2008 was a GFC buying wave")):
            n = int(round(both * 3.0 * mult))
            r = power_of_a_window(n)
            r["basis"] = why
            scen[label] = r

    reachable = bool(sz.get("build", {}).get("form_4_filings_total_to_fetch"))
    return {
        "OWNED_DATA": {
            "first_emittable_year": out["first_emittable"].get("first_emittable_year"),
            "which_constraint_binds": out["first_emittable"].get("which_constraint_binds"),
            "events_emitted_before_2009": n31,
            "power": owned,
            "VERDICT": ("THE 1999-2008 READ CANNOT BE RUN ON OWNED DATA. The construction emits "
                        "%d events, all in 2008, at %.1f%% power against its own measured effect "
                        "-- an MDE80 of %.1fpp against a +3.49pp effect, about seven-fold short."
                        % (n31, 100 * (owned.get("power_gross") or 0),
                           owned.get("mde80_pp") or float("nan"))),
        },
        "SEC_FREE_DATA": {
            "curated_data_sets_start": "2006-01 (the SEC page's own header, Jan 2006 - Sep 2026)",
            "curated_first_emittable_year": 2008,
            "curated_gain": "ZERO -- it lands on the same 2008 owned data already reaches",
            "raw_edgar_mandatory_from": "2003-06-30 (Release 33-8230, effective date)",
            "raw_edgar_first_emittable_year": 2006,
            "raw_edgar_gain": "2006 and 2007 -- two years",
            "reachable_proxy_years": 3,
            "proxy_years_total": 10,
            "CAVEAT": ("all three reachable years sit adjacent to the 2009-2019 build window and "
                       "are dominated by the GFC, so they are a WEAKER out-of-sample era than "
                       "the charter's 1999-2008 intends"),
        },
        "POWER_OF_THE_REACHABLE_WINDOW": scen,
        "N_FOR_80_PERCENT_GROSS_POWER": power_of_a_window(1560),
        "BUILD_SIZE": sz.get("build", {"status": "SIZE NOT MEASURED -- run "
                                                 "scripts.insider_stage3_sec_size"}),
        "OUTCOME": ("REPORT THE SIZE AND STOP -- a free source CAN supply a window, so the prompt's "
                    "second branch applies: Don decides whether to pay for it and this lane does "
                    "NOT build it."
                    if reachable else
                    "UNOBTAINABLE ON OWNED DATA, recorded the S25 way, and nothing is built."),
        "WHAT_IT_DOES_NOT_SAY": (
            "it is NOT a finding that clustered insider buying fails before 2009 -- the "
            "construction cannot emit events there, so the hypothesis is UNTESTED in that era "
            "rather than rejected. And the paper book carries on either way "
            "(DECISIONS.md 2026-10-14)."),
    }


def _sec_size() -> dict:
    p = D.out_path("INSIDER_STAGE3_SEC_SIZE.json")
    if not os.path.isfile(p):
        return {}
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (Exception, SystemExit):                                         # noqa: BLE001
        return {}


def main(argv=None):
    out = {"item": "INSIDER-STAGE3", "part": "feasibility of the older-data rung",
           "trials": 0,
           "CLASS": ("FACTS -- no hypothesis, no bar, no verdict, and no forward return is "
                     "loaded anywhere in this file"),
           "charter": "RESEARCH_CHARTER.md section 5 Stage 3",
           "decision": "DECISIONS.md 2026-10-14 CLUSTERED INSIDER BUYING"}

    print("[feas] censusing the FREEZE's raw SF2 (the file the construction reads) ...", flush=True)
    out["sf2_census"] = sf2_census()
    c = out["sf2_census"]
    if c.get("status") == "ABSENT":
        print("  SF2 ABSENT at %s" % c["path"], flush=True)
    else:
        print("  %d rows, %d with code P, %d missing a code" %
              (c["rows_total"], c["rows_purchase_code_P"], c["rows_missing_transactioncode"]),
              flush=True)
        print("  filing dates %s .. %s" % (c.get("filing_date_min"), c.get("filing_date_max")),
              flush=True)
        print("  transaction dates %s .. %s" % (c.get("transaction_date_min"),
                                                c.get("transaction_date_max")), flush=True)
        for y, n in sorted((c.get("filing_year_counts") or {}).items()):
            print("    filing %s: %d P-rows" % (y, n), flush=True)

    out["first_emittable"] = first_emittable(c)
    fe = out["first_emittable"]
    print("[feas] first filing year %s, first transaction year %s -> FIRST EMITTABLE %s (%s); "
          "predicate +2 measured %s, gap refused %s"
          % (fe.get("first_filing_year"), fe.get("first_transaction_year"),
             fe.get("first_emittable_year"), fe.get("which_constraint_binds"),
             fe.get("predicate_plus_two_measured"),
             fe.get("negative_control_a_gap_year_is_refused")), flush=True)

    out["proxy_overlap"] = proxy_overlap(c, out["first_emittable"].get("first_emittable_year"))
    print("[feas] usable years inside the 1999-2008 proxy window: %s"
          % out["proxy_overlap"].get("usable_years_inside_the_proxy_window"), flush=True)

    out["observed_rate"] = events_per_year_from_the_check_cell()
    if out["observed_rate"].get("events_per_year"):
        print("[feas] observed rate on the governing cell: %.1f events/yr"
              % out["observed_rate"]["events_per_year"], flush=True)

    out["banked_pre2009"] = banked_pre2009_events()
    print("[feas] events the construction emits before 2009: %s (all in %s)"
          % (out["banked_pre2009"].get("n_events"),
             ", ".join(out["banked_pre2009"].get("by_year", {}))), flush=True)

    out["DECISION"] = decide(out)
    d = out["DECISION"]
    print("\n[feas] OWNED DATA: %s" % d["OWNED_DATA"]["VERDICT"], flush=True)
    print("[feas] SEC curated start 2006-01 -> first emittable 2008 -> GAIN ZERO", flush=True)
    print("[feas] SEC raw EDGAR mandatory 2003-06-30 -> first emittable 2006 -> gains 2006-2007",
          flush=True)
    for k, v in (d.get("POWER_OF_THE_REACHABLE_WINDOW") or {}).items():
        print("[feas]   %-26s n=%-5d gross %.1f%% net %.1f%%"
              % (k, v["n_events"], 100 * v["power_gross"],
                 100 * v["power_net_vs_cost_bar"]), flush=True)
    b = d.get("BUILD_SIZE") or {}
    if b.get("form_4_filings_total_to_fetch"):
        print("[feas] BUILD SIZE: %d Form 4 filings (%.1f h at 10/s, %.1f h at 5/s)"
              % (b["form_4_filings_total_to_fetch"], b["fetch_hours_at_10_per_second"],
                 b["fetch_hours_at_a_polite_5_per_second"]), flush=True)
    print("[feas] OUTCOME: %s" % d["OUTCOME"], flush=True)

    out["era_penalty_range"] = list(ERA_PENALTY_RANGE)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[feas] wrote %s" % p, flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
