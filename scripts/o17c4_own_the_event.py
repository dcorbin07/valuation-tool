#!/usr/bin/env python3
"""o17c4_own_the_event.py — "own the event" as its OWN strategy.  [MA54-2 / O17-C4]

Executes PREREG_o17c4_own_the_event.md, committed ALONE at aeca6f0 before this file existed.
Nothing here restates a threshold from a result.

TWO PASSES. `--bars-only` derives the breadth and concurrency bars and exits BEFORE any arm is
scored; `--arms` REFUSES to run without the bars artifact. The bars are derived first and BIND
whatever they return — the TP-BAR precedent, where the honest bar was derived first and the arm
then failed it.

    python -m scripts.o17c4_own_the_event --bars-only
    python -m scripts.o17c4_own_the_event --arms

Adopts nothing. Charged to OPTIONS: N 292 -> 294 (A1, A2).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

DATA = os.environ.get("VALQUO_DATA_ROOT", r"C:\Users\donni\Downloads\valuation-tool\data")
UNIV = os.path.join(DATA, "options_universe")
BOOK = os.path.join(UNIV, "state_r2_splitclean.pkl")
CTRL = [os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s) for s in range(5)]
BARS_JSON = os.path.join(DATA, "free_analysis", "O17C4_BARS.json")
ARMS_JSON = os.path.join(DATA, "free_analysis", "O17C4_OWN_THE_EVENT.json")

# ---- pre-registered ------------------------------------------------------------------------
N_BREADTH_DRAWS = 200          # prereg 3 B2
BREADTH_SEED0 = 4400
CONC_CAPS = (10, 50)           # prereg 3 B3 — O11's own caps, not new ones
HALF_SPLIT = "2021-01-01"      # O17's own split point, read from its artifact geometry


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _d(x):
    if x is None:
        return None
    s = str(x)[:10]
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def load_books():
    b = pd.read_pickle(BOOK)
    alert = list(b["rows"])
    ctrl = []
    for i, p in enumerate(CTRL):
        rows = pd.read_pickle(p)
        for r in rows:
            r = dict(r)
            r["_seed"] = i
            ctrl.append(r)
    return alert, ctrl


def earnings_map(names):
    from valuation.edge import bulk
    ev = bulk.prepare_events(os.path.join(DATA, "bulk", "events.csv"))
    return {t: sorted(str(x) for x in (bulk.earnings_dates(ev, t) or [])) for t in names}


def tag(rows, earn):
    """Partition by the SHIPPED rule. None is dropped and COUNTED, never folded either way."""
    from valuation.studies.earnings_surface import owns_the_event
    spans, nots, unknown = [], [], []
    for r in rows:
        v = owns_the_event(r.get("alert_ts"), r.get("expiry"), earn.get(r.get("ticker")) or [])
        if v is None:
            unknown.append(r)
        elif v:
            spans.append(r)
        else:
            nots.append(r)
    return spans, nots, unknown


# ============================================================================ bars
def breadth(rows):
    """The three axes of B1/B2. A book is trades/yr, names touched, months touched."""
    if not rows:
        return {"n": 0, "trades_per_year": 0.0, "n_names": 0, "n_months": 0,
                "share_months": 0.0}
    ds = [_d(r.get("alert_ts")) for r in rows]
    ds = [d for d in ds if d is not None]
    if not ds:
        return {"n": len(rows), "trades_per_year": 0.0, "n_names": 0, "n_months": 0,
                "share_months": 0.0}
    span_days = max(1, (max(ds) - min(ds)).days)
    months = {(d.year, d.month) for d in ds}
    total_months = max(1, round(span_days / 30.44))
    return {"n": len(rows),
            "trades_per_year": round(len(rows) / (span_days / 365.25), 3),
            "n_names": len({r.get("ticker") for r in rows}),
            "n_months": len(months),
            "share_months": round(len(months) / total_months, 4),
            "first": str(min(ds)), "last": str(max(ds))}


def concurrency(rows, caps=CONC_CAPS):
    """B3 — O11's own question. Peak simultaneous open positions, and the share of trades a
    cap refuses when filled first-come. O11 measured that a cap of 10 turned a +3.27%/trade
    book into a -25.9% total return, so a MORE concurrent book inherits that harder."""
    ev = []
    for r in rows:
        a, x = _d(r.get("alert_ts")), _d(r.get("expiry"))
        if a is None:
            continue
        held = r.get("held_days")
        if x is None and held is None:
            continue
        end = x if x is not None else a + dt.timedelta(days=int(held or 0))
        if held is not None and x is not None:
            end = min(x, a + dt.timedelta(days=int(held)))
        ev.append((a, end))
    if not ev:
        return {"n": 0, "peak": 0}
    ev.sort()
    pts = defaultdict(int)
    for a, e in ev:
        pts[a] += 1
        pts[e + dt.timedelta(days=1)] -= 1
    cur, peak = 0, 0
    for k in sorted(pts):
        cur += pts[k]
        peak = max(peak, cur)
    out = {"n": len(ev), "peak_open": peak}
    for c in caps:
        open_ends, refused = [], 0
        for a, e in ev:
            open_ends = [x for x in open_ends if x >= a]
            if len(open_ends) >= c:
                refused += 1
            else:
                open_ends.append(e)
        out["refused_at_cap_%d" % c] = refused
        out["refused_share_at_cap_%d" % c] = round(refused / len(ev), 4)
    return out


def bars():
    sys.path.insert(0, _repo())
    alert, ctrl = load_books()
    names = sorted({r.get("ticker") for r in alert} | {r.get("ticker") for r in ctrl})
    earn = earnings_map(names)
    zero = [t for t in names if not earn.get(t)]

    a_span, a_not, a_unk = tag(alert, earn)
    strat_breadth = breadth(a_span)
    book_breadth = breadth(alert)
    strat_conc = concurrency(a_span)
    book_conc = concurrency(alert)

    # B2 — 200 random entry sets of the SAME SIZE from the same grid, p5 of their breadth.
    rng = np.random.default_rng(BREADTH_SEED0)
    k = len(a_span)
    pool = alert
    draws = []
    for _ in range(N_BREADTH_DRAWS):
        idx = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
        draws.append(breadth([pool[i] for i in idx]))

    def p5(key):
        v = [d[key] for d in draws if d.get(key) is not None]
        return float(np.percentile(v, 5)) if v else None

    out = {
        "prereg": "PREREG_o17c4_own_the_event.md",
        "coverage": {
            "names": len(names), "names_zero_earnings": len(zero),
            "zero_earnings_names": zero[:40],
            "alert_n": len(alert), "alert_spans": len(a_span),
            "alert_not": len(a_not), "alert_unknown": len(a_unk),
            "unknown_is_nonzero": bool(len(a_unk) > 0),
        },
        "B1_absolute_vs_alert_book": {
            "strategy": strat_breadth, "alert_book": book_breadth,
            "pass_trades_per_year": bool(strat_breadth["trades_per_year"]
                                         >= book_breadth["trades_per_year"]),
            "pass_names": bool(strat_breadth["n_names"] >= book_breadth["n_names"]),
            "pass_months": bool(strat_breadth["n_months"] >= book_breadth["n_months"]),
            "note": "the alert book is the object every published options figure is measured "
                    "on; a strategy narrower than a book already shown to fail survivability "
                    "at $50k (O11) is not more tradeable than it",
        },
        "B2_calibrated_same_size": {
            "draws": N_BREADTH_DRAWS, "seed0": BREADTH_SEED0,
            "p5_n_names": p5("n_names"), "p5_n_months": p5("n_months"),
            "strategy_n_names": strat_breadth["n_names"],
            "strategy_n_months": strat_breadth["n_months"],
            "pass_names": bool(p5("n_names") is not None
                               and strat_breadth["n_names"] >= p5("n_names")),
            "pass_months": bool(p5("n_months") is not None
                                and strat_breadth["n_months"] >= p5("n_months")),
            "note": "asks whether the rule is concentrated BEYOND what its own trade count "
                    "forces; binding whatever it returns",
        },
        "B3_concurrency": {
            "strategy": strat_conc, "alert_book": book_conc,
            "pass_peak": bool(strat_conc.get("peak_open", 0) <= book_conc.get("peak_open", 0)),
            **{("pass_cap_%d" % c): bool(
                strat_conc.get("refused_share_at_cap_%d" % c, 1.0)
                <= book_conc.get("refused_share_at_cap_%d" % c, 0.0)) for c in CONC_CAPS},
            "note": "O11: a cap of 10 refused 1,677 of 3,870 alert trades and turned +3.27%/"
                    "trade into a -25.9% total return. A MORE concurrent book inherits that "
                    "harder, and a positive per-trade expectancy is then NOT evidence it is "
                    "tradeable.",
        },
    }
    b1 = all(out["B1_absolute_vs_alert_book"][k] for k in
             ("pass_trades_per_year", "pass_names", "pass_months"))
    b2 = all(out["B2_calibrated_same_size"][k] for k in ("pass_names", "pass_months"))
    b3 = all(v for k, v in out["B3_concurrency"].items() if k.startswith("pass_"))
    out["bars"] = {"B1": bool(b1), "B2": bool(b2), "B3": bool(b3)}
    out["all_bars_pass"] = bool(b1 and b2 and b3)

    # ---------------------------------------------------------------------------------------
    # A DEFECT IN MY OWN BARS, FOUND BY RUNNING THEM. REPORTED, SCORING NOTHING.
    #
    # The register is left UNEDITED and `bars` / `all_bars_pass` above are exactly as it
    # specified them (RUN_RULES: corrections go in the write-up). This block is a POST-HOC
    # DIAGNOSTIC added after reading them, it is labelled as such, and it deliberately does
    # NOT feed `all_bars_pass` — moving a bar after seeing it fail is the move TP-BAR exists
    # to refuse, and adding a passing criterion now would be exactly that.
    #
    # TWO OF THE THREE REGISTERED BARS DO NOT MEASURE WHAT THEY WERE WRITTEN TO MEASURE:
    #
    #   * B1's trades-per-year axis is UNPASSABLE BY CONSTRUCTION for A1. The arm is a SUBSET
    #     of the alert book, so it can never out-trade its own superset. A subset relation is
    #     not a breadth finding. (The STRATEGY is not a subset of anything — its entry
    #     universe is every day a spanning call can be bought — but A1 measures it on the
    #     banked book, which is the only place it can be measured.)
    #   * B1's and B2's NAME axes are the earnings COVERAGE HOLE re-measured. 29 of 186 names
    #     are foreign private issuers with zero earnings dates, so the spanning set is capped
    #     at 157 names before any concentration exists. It touches 157 — i.e. ALL of them.
    #     A random same-size subset draws from all 186, so B2 was comparing a capped set to an
    #     uncapped one and reading the cap as concentration.
    #
    # Against the ELIGIBLE universe the picture reverses, and this is the honest reading:
    n_elig = len(names) - len(zero)
    out["B1_B2_DEFECT_DIAGNOSTIC"] = {
        "status": "POST-HOC, REPORTED ONLY, FEEDS NO PASS/FAIL FLAG",
        "eligible_names": n_elig,
        "strategy_names": strat_breadth["n_names"],
        "share_of_eligible_names": (round(strat_breadth["n_names"] / n_elig, 4)
                                    if n_elig else None),
        "strategy_months": strat_breadth["n_months"],
        "alert_book_months": book_breadth["n_months"],
        "trades_per_year_axis_is_unpassable_for_a_subset": True,
        "why": "B1's trades/yr axis compares a subset to its superset; B1/B2's name axes "
               "compare a set capped at 157 by the foreign-issuer coverage hole against one "
               "drawn from all 186. Only B3 measures the property it was written for.",
        "corrected_reading": "breadth is NOT the binding constraint — the strategy touches "
                             "every eligible name and every month the alert book touches. "
                             "That is what the register's expectation 4 predicted; the BAR "
                             "written to test it was broken, not the prediction.",
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars-only", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, _repo())
    if a.bars_only:
        r = bars()
        os.makedirs(os.path.dirname(BARS_JSON), exist_ok=True)
        with open(BARS_JSON, "w") as fh:
            json.dump(r, fh, indent=2, default=str)
        print(json.dumps(r, indent=2, default=str))
        print("\n[o17c4] wrote %s" % BARS_JSON)
        return 0
    if a.arms:
        from scripts.o17c4_arms import run_arms
        if not os.path.exists(BARS_JSON):
            raise SystemExit("[o17c4] REFUSING: no bars artifact at %s. Run --bars-only first "
                             "— the bar is derived BEFORE the arm faces it." % BARS_JSON)
        r = run_arms(json.load(open(BARS_JSON)))
        with open(ARMS_JSON, "w") as fh:
            json.dump(r, fh, indent=2, default=str)
        print("\n[o17c4] wrote %s" % ARMS_JSON)
        print(json.dumps(r.get("verdict", {}), indent=2, default=str))
        return 0
    ap.error("pass --bars-only or --arms")


if __name__ == "__main__":
    raise SystemExit(main())
