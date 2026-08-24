"""
I-4 — build the event spine, write its census, and prove it agrees with the shipped paths.

    python -m scripts.i4_event_spine [--book <pkl>] [--out <json>]

COLLECTION-AND-PROVENANCE. Zero trials, no verdict, no arm. This script measures three things
and asserts nothing about returns:

  1. **The census** -- coverage state per name-year, FAIL_CLOSED names listed by name, the
     34/35 sunset carried alongside.
  2. **The banked reproduction** -- O17's `excluded_zero_coverage_names` and `n_excluded_trades`
     recomputed from the spine. If the spine is the canonical table it must reproduce the join
     the closed study already banked, or the difference is the finding.
  3. **THE AGREEMENT CHECK ON REAL ROWS.** `tests/test_event_spine.py` drives an exhaustive
     synthetic grid; this drives the actual alert book through BOTH the spine and the shipped
     `earnings_surface` predicates and lists every disagreeing row. Synthetic coverage proves the
     logic matches; real coverage proves the DATA feeding it matches, and those are different
     claims. A spine that agreed on invented calendars and disagreed on the book would pass the
     first check and be useless.

Any disagreement is written to the artifact as a list of rows, never as a count.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import event_spine as SP                            # noqa: E402
# The ARCHIVED study, imported HERE (a script, not a live module) purely as the comparison
# reference. `scripts/o6_o7_o17_earnings.py` already imports it the same way, and MA59's
# quarantine gates reachability from PRODUCTION entry points, which this is not.
from valuation.studies import earnings_surface as ES                    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    """The licensed store, resolved and ANNOUNCED rather than silently chosen.

    `data/` is a junction in the main checkout and is absent (or a thin stub) inside a git
    worktree, so a worktree run finds no book. Falling back to the main checkout is right, but a
    SILENT fallback would mean two runs of this script could read two different stores and report
    the same-looking numbers -- which is the two-sources defect this whole instrument exists to
    prevent, reappearing in the tool that prevents it. So the chosen root is printed, and if
    neither has the data the script says so instead of half-running.
    """
    here = os.path.join(REPO, "data")
    main = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data")
    for root, why in ((here, "worktree"), (main, "main checkout")):
        if os.path.isdir(os.path.join(root, "options_universe")):
            print(f"[i4] data root: {root}  ({why})", flush=True)
            return root
    raise SystemExit(
        f"[i4] no options_universe under {here} or {main} -- data/ is licensed, gitignored and "
        f"absent from worktrees. Pass --book/--events explicitly.")


DATA = _data_root()
#: O17 banked its join on the SPLIT-CLEAN book (3,870 trades). Reproducing against the corrected
#: book instead would differ by 15 trades for a reason that has nothing to do with earnings, and
#: an unexplained difference in a reproduction is worse than no reproduction.
DEFAULT_BOOK = os.path.join(DATA, "options_universe", "state_r2_splitclean.pkl")
FALLBACK_BOOK = os.path.join(DATA, "options_universe", "state_r2_corrected.pkl")
BANKED = os.path.join(DATA, "free_analysis", "O6_O7_O17_EARNINGS.json")
DEFAULT_OUT = os.path.join(DATA, "free_analysis", "I4_EVENT_SPINE.json")

O17_WINDOWS = (5, 10, 15)


def _load_book(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)["rows"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="I-4 event spine: build, census, agreement")
    ap.add_argument("--book", default="")
    ap.add_argument("--events", default=os.path.join(DATA, "bulk", "events.csv"))
    ap.add_argument("--cache-dir", default=os.path.join(DATA, "bulk", "prepared"))
    ap.add_argument("--panel", default=os.path.join(DATA, "free_analysis", "panel_s22_h504.pkl"),
                    help="equity panel, censused alongside the options book")
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)

    book_path = a.book or (DEFAULT_BOOK if os.path.exists(DEFAULT_BOOK) else FALLBACK_BOOK)
    rows = _load_book(book_path)
    names = sorted({str(r["ticker"]).upper() for r in rows})
    print(f"[i4] book {os.path.basename(book_path)}: {len(rows)} trades, {len(names)} names",
          flush=True)

    spine = SP.EventSpine.build(names, csv_path=a.events, cache_dir=a.cache_dir)
    print(f"[i4] spine: {len(spine.by_ticker)} covered, {len(spine.zero_coverage)} FAIL_CLOSED",
          flush=True)

    census = spine.census(names)

    # ------------------------------------------------------- the equity scope, for X-2 and O-2
    # The named consumers are equity-side, so a book-scoped census would leave them re-deriving
    # coverage for the 2,531-name panel -- which is the second derivation this instrument exists
    # to prevent. Built from the SAME spine class and the SAME rule; only the name list differs.
    panel_census = None
    if os.path.exists(a.panel):
        import pandas as pd
        pnames = sorted({str(t).upper() for t in pd.read_pickle(a.panel)["ticker"].unique()})
        pspine = SP.EventSpine.build(pnames, csv_path=a.events, cache_dir=a.cache_dir)
        panel_census = pspine.census(pnames)
        print(f"[i4] equity panel: {len(pnames)} names, "
              f"{panel_census['n_fail_closed']} FAIL_CLOSED "
              f"({100*panel_census['n_fail_closed']/max(1,len(pnames)):.1f}%)", flush=True)
    else:
        print(f"[i4] equity panel absent at {a.panel} -- book scope only", flush=True)

    # ---------------------------------------------------------------- 2. banked reproduction
    repro = {"available": os.path.exists(BANKED)}
    if repro["available"]:
        with open(BANKED, encoding="utf-8") as fh:
            b = json.load(fh)["O17"]
        banked_zero = sorted(b["excluded_zero_coverage_names"])
        mine_zero = sorted(spine.zero_coverage)
        n_excl = sum(1 for r in rows if str(r["ticker"]).upper() in set(mine_zero))
        repro.update({
            "banked_book": os.path.basename(book_path),
            "banked_zero_names": len(banked_zero),
            "spine_zero_names": len(mine_zero),
            "zero_names_identical": banked_zero == mine_zero,
            "only_in_banked": [t for t in banked_zero if t not in set(mine_zero)],
            "only_in_spine": [t for t in mine_zero if t not in set(banked_zero)],
            "banked_n_excluded_trades": b["n_excluded_trades"],
            "spine_n_excluded_trades": n_excl,
            "excluded_trades_match": n_excl == b["n_excluded_trades"],
            "excluded_trade_share": round(n_excl / max(1, len(rows)), 4),
        })
        print(f"[i4] banked repro: names identical={repro['zero_names_identical']} "
              f"trades {n_excl} vs {b['n_excluded_trades']} "
              f"match={repro['excluded_trades_match']}", flush=True)

    # ---------------------------------------------------------------- 3. agreement on real rows
    disagree = []
    counts = {"refuse_within": {}, "owns_the_event": {"agree": 0}}
    for w in O17_WINDOWS:
        counts["refuse_within"][str(w)] = {"agree": 0}
    for i, r in enumerate(rows):
        tkr = str(r["ticker"]).upper()
        entry, expiry = r.get("alert_ts"), r.get("expiry")
        shipped_cal = spine.dates_or_unknown(tkr) or []
        for w in O17_WINDOWS:
            mine = SP.refuse_within(spine, tkr, entry, w)
            theirs = ES.refuse_within(entry, shipped_cal, w)
            if mine is not theirs:
                disagree.append({"row": i, "ticker": tkr, "fn": "refuse_within", "window": w,
                                 "entry": str(entry), "spine": mine, "shipped": theirs})
            else:
                counts["refuse_within"][str(w)]["agree"] += 1
        mine = SP.owns_the_event(spine, tkr, entry, expiry)
        theirs = ES.owns_the_event(entry, expiry, shipped_cal)
        if mine is not theirs:
            disagree.append({"row": i, "ticker": tkr, "fn": "owns_the_event",
                             "entry": str(entry), "expiry": str(expiry),
                             "spine": mine, "shipped": theirs})
        else:
            counts["owns_the_event"]["agree"] += 1

    # the partition the shipped study reports, recomputed off the spine
    partitions = {}
    for w in O17_WINDOWS:
        kept = refused = unknown = 0
        for r in rows:
            d = SP.refuse_within(spine, str(r["ticker"]).upper(), r.get("alert_ts"), w)
            if d is None:
                unknown += 1
            elif d:
                refused += 1
            else:
                kept += 1
        partitions[f"C_{w}d_avoid"] = {"kept": kept, "refused": refused, "unknown": unknown,
                                       "n_known": kept + refused}
    own_kept = own_ref = own_unk = 0
    for r in rows:
        d = SP.owns_the_event(spine, str(r["ticker"]).upper(), r.get("alert_ts"), r.get("expiry"))
        if d is None:
            own_unk += 1
        elif d:
            own_ref += 1
        else:
            own_kept += 1
    partitions["C4_own_the_event"] = {"owns": own_ref, "does_not_own": own_kept,
                                      "unknown": own_unk}

    print(f"[i4] agreement on {len(rows)} real rows: "
          f"{len(disagree)} disagreements", flush=True)

    out = {
        "item": "I-4",
        "class": "collection-and-provenance",
        "trials": 0,
        "book": os.path.basename(book_path),
        "n_trades": len(rows),
        "n_names": len(names),
        "census": census,
        "panel_census": panel_census,
        "banked_reproduction": repro,
        "agreement": {
            "n_rows": len(rows),
            "windows": list(O17_WINDOWS),
            "n_disagreements": len(disagree),
            "disagreements": disagree[:500],
            "agree_counts": counts,
            "note": ("Disagreements are LISTED, never counted. An empty list is the pass; a "
                     "non-empty one names the rows so the two derivations can be reconciled "
                     "rather than argued about."),
        },
        "spine_partitions_no_verdict": partitions,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    slim = {k: v for k, v in out.items() if k not in ("census", "panel_census")}
    slim["census_summary"] = {k: census[k] for k in
                              ("n_names", "name_states", "n_fail_closed", "years")}
    if panel_census:
        slim["panel_census_summary"] = {k: panel_census[k] for k in
                                        ("n_names", "name_states", "n_fail_closed")}
    slim["agreement"]["disagreements"] = disagree[:10]
    print(json.dumps(slim, indent=1)[:3000])
    return out


if __name__ == "__main__":
    main()
