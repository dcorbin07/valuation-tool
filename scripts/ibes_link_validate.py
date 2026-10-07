# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 3 -- validate the dated IBES link as an INSTRUMENT.

    python -m scripts.ibes_link_validate

**ZERO TRIALS.** No hypothesis, no bar, no arm, and **no outcome statistic of any kind** -- no
forward return is read anywhere on this path, pinned by test. `MB15`'s rule: the instrument is
validated BEFORE any hypothesis reads it, and under `MB1-SEL` a control can only ever BLOCK a
finding, so it adds no degree of freedom.

**NO WRDS CONNECTION.** Everything is read from the 2026-08-24 pull on `D:\\wrds`, so the
one-attempt-per-session rule is not engaged.

**COVERAGE IS MEASURED ON THE PANEL'S OWN POPULATION, NEVER ON THE IDENTIFIER TABLE.** `O-1`
applied an alert-book figure to the panel and was ~17x wrong; `S25` recorded two nearly-equal
percentages on different objects. So the denominators here are the corrected panel's own cells and
names, stated as such.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import ibes_link as L                                   # noqa: E402

PANEL = "UNIVERSE_BIAS_PANEL_full.pkl"
OUT = "IBES_LINK_VALIDATION.json"
#: the project's own non-null rule, INHERITED rather than chosen here.
COVERAGE_FLOOR = 0.70


def fa():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis")


def main(argv=None):
    ids = L.ibes_id()
    print("ibes_id %d rows | %d distinct IBES tickers | sdates %s -> %s"
          % (len(ids), ids["ticker"].nunique(),
             str(pd.to_datetime(ids["sdates"]).min())[:10],
             str(pd.to_datetime(ids["sdates"]).max())[:10]), flush=True)

    oftic_spans, cen_a = L.spans(ids, key="oftic")
    cusip_spans, cen_b = L.spans(ids, key="cusip")
    print("route A spans %d over %d oftic | dropped %d no-sdates, %d no-oftic"
          % (cen_a["spans"], cen_a["keys"], cen_a["dropped_no_sdates"],
             cen_a["dropped_no_oftic"]), flush=True)
    print("route B spans %d over %d cusip" % (cen_b["spans"], cen_b["keys"]), flush=True)

    panel = pd.read_pickle(os.path.join(fa(), PANEL))
    panel["_d"] = pd.to_datetime(panel["date"])
    cells = panel[["ticker", "_d"]].drop_duplicates()
    print("panel %d cells | %d names | %d dates"
          % (len(cells), cells["ticker"].nunique(), cells["_d"].nunique()), flush=True)

    crsp = L.crsp_names()
    cr = L.crsp_spans(crsp) if crsp is not None else None
    print("crsp_stocknames %s" % ("%d dated rows" % len(cr) if cr is not None else "ABSENT"),
          flush=True)

    # --- resolve every cell on both routes, VECTORISED ------------------------------------
    #
    # The first cut looped per cell and filtered the whole span table each time -- 289,659 cells
    # against 289,446 spans -- and would not have finished. `resolve_many` is an interval join.
    # THE SCALAR `resolve` REMAINS THE DEFINITION and the vectorised path must AGREE with it on a
    # sample before anything is read off it (`B7`: a second implementation is PROVED to match,
    # never assumed to).
    cl = cells.rename(columns={"_d": "date"})
    ra = L.resolve_many(oftic_spans, cl, key="oftic")
    r = pd.DataFrame({"ticker": ra["ticker"].values, "date": ra["date"].values,
                      "a": ra["resolved"].values, "state_a": ra["state"].values})
    if cr is not None:
        leg1 = L.crsp_cusip_many(cr, cl)
        ok1 = leg1[leg1["state"] == L.OK]
        # built EXPLICITLY: `ok1` already carries a `ticker` column (the PANEL ticker), so
        # renaming `cusip` -> `ticker` produced a DUPLICATE and the slice returned three columns.
        leg2_in = pd.DataFrame({"ticker": ok1["cusip"].values, "date": ok1["date"].values})
        leg2 = L.resolve_many(cusip_spans, leg2_in, key="cusip")
        b = pd.Series([None] * len(r), index=r.index, dtype=object)
        sb = pd.Series([L.NOT_COVERED] * len(r), index=r.index, dtype=object)
        # map leg-1 refusals through, then overwrite the rows leg 1 resolved
        key1 = {(t, pd.Timestamp(d)): st for t, d, st
                in leg1[["ticker", "date", "state"]].itertuples(index=False)}
        got2 = {(t, pd.Timestamp(d)): (v, st) for t, d, v, st
                in leg2[["ticker", "date", "resolved", "state"]].itertuples(index=False)}
        cus = {(t, pd.Timestamp(d)): c for t, d, c
               in ok1[["ticker", "date", "cusip"]].itertuples(index=False)}
        for i, (t, d) in enumerate(zip(r["ticker"].values, r["date"].values)):
            kk = (t, pd.Timestamp(d))
            st1 = key1.get(kk, L.UNMAPPED)
            if st1 != L.OK:
                sb.iloc[i] = st1
                continue
            c = cus.get(kk)
            v, st2 = got2.get((c, pd.Timestamp(d)), (None, L.UNMAPPED))
            b.iloc[i], sb.iloc[i] = v, st2
        r["b"], r["state_b"] = b.values, sb.values
    else:
        r["b"], r["state_b"] = None, "ROUTE_ABSENT"

    # --- B7: the vectorised path must AGREE with the scalar definition --------------------
    import random
    random.seed(1000)
    idx = random.sample(range(len(r)), min(400, len(r)))
    mism = []
    for i in idx:
        tkr, d = r["ticker"].iloc[i], r["date"].iloc[i]
        got, st = L.resolve(oftic_spans, tkr, d, key="oftic")
        if (st != r["state_a"].iloc[i]) or (got != r["a"].iloc[i] and st == L.OK):
            mism.append({"ticker": str(tkr), "date": str(d)[:10],
                         "scalar": [got, st],
                         "vector": [r["a"].iloc[i], r["state_a"].iloc[i]]})
    print("\n=== B7 -- vectorised vs the SCALAR definition on %d sampled cells: %d mismatches"
          % (len(idx), len(mism)), flush=True)
    if mism:
        for m in mism[:5]:
            print("    %s" % m, flush=True)
        raise SystemExit("the vectorised path disagrees with the scalar definition; no figure "
                         "may be read off it")
    b7 = {"sampled_cells": len(idx), "mismatches": 0, "seed": 1000,
          "note": "the SCALAR `resolve` is the definition; this proves the interval join "
                  "reproduces it rather than assuming so (B7). Non-vacuous: the sample "
                  "contains %d OK and %d refused cells."
                  % (int((r["state_a"].iloc[idx] == L.OK).sum()),
                     int((r["state_a"].iloc[idx] != L.OK).sum()))}

    def census(col, state):
        v = r[state].value_counts().to_dict()
        ok = r[r[state] == L.OK]
        return {"cells": int(len(r)),
                "states": {k: int(v.get(k, 0)) for k in sorted(v)},
                "cell_coverage": float((r[state] == L.OK).mean()),
                "name_coverage": float(ok["ticker"].nunique() / r["ticker"].nunique()),
                "names_resolved": int(ok["ticker"].nunique()),
                "names_total": int(r["ticker"].nunique())}

    ca, cb = census("a", "state_a"), census("b", "state_b")
    print("\n=== COVERAGE ON THE PANEL'S OWN POPULATION", flush=True)
    for lab, c in (("A direct oftic", ca), ("B via CRSP cusip", cb)):
        print("  %-18s cells %.4f | names %.4f (%d of %d) | %s"
              % (lab, c["cell_coverage"], c["name_coverage"], c["names_resolved"],
                 c["names_total"], c["states"]), flush=True)

    # --- THE VALIDATION: do the two routes AGREE where both resolve? ----------------------
    both = r[(r["state_a"] == L.OK) & (r["state_b"] == L.OK)]
    agree = int((both["a"] == both["b"]).sum())
    agreement = {"cells_both_resolve": int(len(both)),
                 "agree": agree,
                 "disagree": int(len(both) - agree),
                 "agreement_rate": (float(agree / len(both)) if len(both) else None)}
    print("\n=== THE VALIDATION -- two independent dated routes, agreement MEASURED", flush=True)
    print("  both resolve on %d cells | agree %d | disagree %d | rate %s"
          % (agreement["cells_both_resolve"], agreement["agree"], agreement["disagree"],
             ("%.6f" % agreement["agreement_rate"])
             if agreement["agreement_rate"] is not None else "n/a"), flush=True)
    if agreement["disagree"]:
        ex = both[both["a"] != both["b"]].head(8)
        agreement["examples"] = [{"ticker": t, "date": str(d)[:10], "route_a": a, "route_b": b}
                                 for t, d, a, _sa, b, _sb in ex.itertuples(index=False)]
        for e in agreement["examples"]:
            print("    %s %s  A=%s  B=%s" % (e["ticker"], e["date"], e["route_a"],
                                             e["route_b"]), flush=True)

    # --- THE LOOK-AHEAD REFUSAL, measured on the real table ------------------------------
    first = oftic_spans.groupby("oftic")["sdates"].min()
    f = r["ticker"].astype(str).str.strip().str.upper().map(first)
    probed = int(f.notna().sum())
    before = f.notna() & (pd.to_datetime(r["date"]) < f)
    pre = int(before.sum())
    leaked = r[before & (r["state_a"] == L.OK)]
    if len(leaked):
        raise SystemExit("LOOK-AHEAD: %d cells predate their first span and RESOLVED; the "
                         "refusal is broken. e.g. %s"
                         % (len(leaked), leaked.head(3).to_dict("records")))
    lookahead = {"cells_probed": probed, "cells_before_first_span": pre,
                 "all_refused": True,
                 "note": "every panel cell dated BEFORE its ticker's first IBES span was checked "
                         "and NONE resolved. Measured on the real table, not on a fixture -- and "
                         "non-vacuous because `cells_before_first_span` is non-zero."}
    print("\n=== LOOK-AHEAD REFUSAL: %d of %d probed cells predate their first span, "
          "ALL REFUSED" % (pre, probed), flush=True)

    # --- TEMPORAL REUSE: what an UNDATED route could not see -----------------------------
    reuse = (oftic_spans.groupby("oftic")["ibes_ticker"].nunique()
             .pipe(lambda s: s[s > 1]))
    panel_names = set(panel["ticker"].astype(str).str.strip().str.upper())
    reuse_in_panel = sorted(set(reuse.index) & panel_names)
    temporal = {
        "oftic_with_more_than_one_ibes_ticker_over_time": int(len(reuse)),
        "of_those_in_the_panel": len(reuse_in_panel),
        "share_of_panel_names": float(len(reuse_in_panel) / max(1, len(panel_names))),
        "examples": reuse_in_panel[:12],
        "why_it_matters": "THIS IS WHAT AN UNDATED ROUTE CANNOT SEE. S25 recorded that "
                          "comp.security carries no date columns, so temporal reuse -- a ticker "
                          "that was company A in 2009 and is company B today -- is not "
                          "observable there AT ALL. W-3b measured an undated ticker join "
                          "contaminating at 17.7pc and W-28 measured an undated gvkey route "
                          "assigning one company's dates to a DIFFERENT company on 54 names. "
                          "Here the figure is measured rather than feared.",
    }
    print("\n=== TEMPORAL REUSE: %d oftic map to >1 IBES ticker over time; %d of them are "
          "panel names (%.4f of the panel)"
          % (temporal["oftic_with_more_than_one_ibes_ticker_over_time"],
             temporal["of_those_in_the_panel"], temporal["share_of_panel_names"]), flush=True)

    res = {
        "item": "CORRECTED-FLOORS",
        "part": "3 -- the dated IBES link, validated as an INSTRUMENT",
        "trials": 0,
        "trial_class": "INSTRUMENT VALIDATION -- no hypothesis, no bar, no arm, and NO outcome "
                       "statistic computed anywhere on this path (pinned by test). MB15: the "
                       "instrument is validated BEFORE any hypothesis reads it; MB1-SEL: a "
                       "control can only BLOCK, never produce, so it adds no degree of freedom.",
        "no_wrds_connection": "every input is the 2026-08-24 pull on D:\\wrds, so the "
                              "one-attempt-per-session rule (DECISIONS.md 2026-10-04) is not "
                              "engaged at all",
        "no_outcome_read": True,
        "adopts_nothing": True,
        "panel": PANEL,
        "ibes_id_census": {"rows": int(len(ids)),
                           "distinct_ibes_tickers": int(ids["ticker"].nunique()),
                           "route_a": cen_a, "route_b": cen_b},
        "coverage_floor_inherited": COVERAGE_FLOOR,
        "coverage": {"route_a_direct_oftic": ca, "route_b_via_crsp_cusip": cb},
        "clears_inherited_floor": {
            "route_a_cells": bool(ca["cell_coverage"] >= COVERAGE_FLOOR),
            "route_a_names": bool(ca["name_coverage"] >= COVERAGE_FLOOR),
            "route_b_cells": bool(cb["cell_coverage"] >= COVERAGE_FLOOR),
            "route_b_names": bool(cb["name_coverage"] >= COVERAGE_FLOOR),
            "note": "the 0.70 floor is the project's own non-null rule, INHERITED rather than "
                    "chosen here. A route below it is reported below it; W-28's rule is that a "
                    "pre-committed bar may not be relaxed after watching it fail.",
        },
        "vectorised_agrees_with_the_scalar_definition": b7,
        "agreement_between_routes": agreement,
        "look_ahead_refusal": lookahead,
        "temporal_reuse": temporal,
        "not_done": [
            "NO ARM. A9 is NOT run and carries no verdict -- it needs its own blind register and "
            "its own trial, and its size-costume kill must be read FIRST (E-1 died at 0.6114 "
            "against size and R6's conviction signals read -0.815 to -0.854, so an analyst-"
            "neglect proxy is a SIZE proxy until measured otherwise).",
            "NO ESTIMATE IS JOINED. This validates the IDENTIFIER link only; joining "
            "ibes_statsum_epsus and dealing with its own staleness, revisions and fiscal-period "
            "indexing is a separate build.",
            "THE PRE-1976 ERA IS UNREACHABLE and no span is invented for it.",
        ],
    }
    dest = os.path.join(fa(), OUT)
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote %s" % dest, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
