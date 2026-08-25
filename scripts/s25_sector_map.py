"""S25 — pull `comp.co_hgic`, build the dated sector map, measure the look-ahead repair.

    python -m scripts.s25_sector_map --pull     # WRDS -> D:\\wrds (licensed raw, never the repo)
    python -m scripts.s25_sector_map --build    # raw -> data/free_analysis/S25_SECTOR_MAP.json
    python -m scripts.s25_sector_map --repair   # what the repair moves on the banked panel

Register: `PREREG_s25_sector_crosswalk.md`, committed ALONE before any of this existed.
**ZERO TRIALS** — an instrument plus a correctness measurement, with no hypothesis and no bar.
**NO RANKING ARM RUNS HERE**, by that register's section 6.

**THE RAW GICS ROWS ARE LICENSED AND STAY IN `D:\\wrds`.** What reaches the repo is the derived
map, which is a per-ticker sequence of (date range, sector label) — the same reduction the fleet
gates make, and for the same reason.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import sector_map as SM                      # noqa: E402

RAW_HGIC = "S25_CO_HGIC.csv"
RAW_LINK = "S25_TIC_GVKEY.csv"


def _repo() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    """The PRIMARY data root. `DEEPITM-FIN`'s defect: a worktree's empty `data/` shadows the
    populated primary and turns a real read into a silent zero."""
    here = _repo()
    for c in (os.path.join(here, "data"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))), "data")):
        if os.path.exists(os.path.join(c, "free_analysis", "panel_s23_fairvalue.pkl")):
            return c
    raise SystemExit("no data root carries the banked S23 valuation panel")


def _raw(name: str) -> str:
    from valuation.edge import wrds_client as W
    return os.path.join(W.raw_root(), name)


def universe() -> list:
    import pandas as pd
    df = pd.read_pickle(os.path.join(_data_root(), "free_analysis",
                                     "panel_s23_fairvalue.pkl"))
    return sorted({str(t).upper().strip() for t in df["ticker"] if str(t).strip()})


# ---------------------------------------------------------------------------------------
def pull() -> dict:
    from valuation.edge import wrds_client as W
    import pandas as pd

    tickers = universe()
    print("universe: %d tickers" % len(tickers))
    db = W.connect()
    try:
        # THE LINK. `crsp.ccmxpf_lnkhist` is DENIED on this account, so the route is
        # `comp.security.tic`. That table carries NO date columns, which is stated as a limit
        # rather than worked around -- see the report's `link_is_undated` note.
        inlist = ",".join("'" + t.replace("'", "") + "'" for t in tickers)
        link = db.raw_sql(
            "select tic, gvkey from comp.security where tic in (%s)" % inlist)
        link["tic"] = link["tic"].astype(str).str.upper().str.strip()
        link["gvkey"] = link["gvkey"].astype(str)
        link = link.drop_duplicates()
        gv = sorted(set(link["gvkey"]))
        print("linked: %d rows, %d distinct gvkeys" % (len(link), len(gv)))

        gvlist = ",".join("'" + g + "'" for g in gv)
        hgic = db.raw_sql(
            "select gvkey, indtype, gsector, ggroup, indfrom, indthru "
            "from comp.co_hgic where gvkey in (%s)" % gvlist)
        print("co_hgic: %d rows" % len(hgic))
    finally:
        db.close()

    link.to_csv(_raw(RAW_LINK), index=False)
    hgic.to_csv(_raw(RAW_HGIC), index=False)
    return {"tickers": len(tickers), "link_rows": int(len(link)),
            "gvkeys": len(gv), "hgic_rows": int(len(hgic)),
            "raw": [_raw(RAW_LINK), _raw(RAW_HGIC)]}


# ---------------------------------------------------------------------------------------
def build() -> dict:
    import pandas as pd

    link = pd.read_csv(_raw(RAW_LINK), dtype=str)
    hgic = pd.read_csv(_raw(RAW_HGIC), dtype=str)
    hgic = hgic[hgic["indtype"].astype(str).str.upper() == "GICS"]

    # AMBIGUOUS TICKERS ARE REFUSED, NEVER PICKED. A silently-chosen gvkey is a wrong
    # company's sector history wearing the right ticker, and on a 2009 row nothing downstream
    # could detect it. Register section 5.
    per_tic = link.groupby("tic")["gvkey"].apply(lambda s: sorted(set(s)))
    ambiguous = {t: g for t, g in per_tic.items() if len(g) > 1}
    solo = {t: g[0] for t, g in per_tic.items() if len(g) == 1}

    by_gv = {}
    for r in hgic.itertuples(index=False):
        frm = SM._d(r.indfrom)
        if frm is None:
            continue
        by_gv.setdefault(str(r.gvkey), []).append(
            (frm, SM._d(r.indthru), str(r.gsector or "").strip()))

    spans, unmapped_codes = {}, {}
    for tic, gvkey in solo.items():
        rows = by_gv.get(gvkey)
        if not rows:
            continue
        out = []
        for frm, thru, gs in sorted(rows):
            panel = SM.crosswalk(gs)
            if panel == SM.UNMAPPED:
                unmapped_codes[gs] = unmapped_codes.get(gs, 0) + 1
            out.append((frm, thru, gs, panel))
        spans[tic] = out

    smap = SM.SectorMap(spans, ambiguous, source="comp.co_hgic via comp.security.tic")

    # Panel sector TODAY, for the taxonomy-disagreement measurement.
    panel = pd.read_pickle(os.path.join(_data_root(), "free_analysis",
                                        "panel_s23_fairvalue.pkl"))
    latest = panel.sort_values("date").groupby("ticker")["sector"].last()
    panel_sector = {str(k).upper(): str(v) for k, v in latest.items() if str(v).strip()}

    dis = SM.taxonomy_disagreement(smap, panel_sector)
    trans = smap.transitions()
    rev = {}
    for t in trans:
        rev[t["revision"]] = rev.get(t["revision"], 0) + 1

    payload = {
        "register": "PREREG_s25_sector_crosswalk.md",
        "built_utc": smap.built_utc,
        "source": smap.source,
        "crosswalk": SM.GICS_TO_PANEL,
        "spans": {t: [list(r) for r in v] for t, v in smap.spans.items()},
        "ambiguous": ambiguous,
        "coverage": smap.coverage(),
        "universe": len(universe()),
        "taxonomy_disagreement": dis,
        "transitions_total": len(trans),
        "transitions_by_kind": rev,
        "unmapped_gics_codes": unmapped_codes,
        "link_is_undated": (
            "comp.security carries NO date columns, so the ticker->gvkey link is a SNAPSHOT. "
            "Simultaneous ambiguity is refused and counted; TEMPORAL reuse -- a ticker that "
            "was company A in 2009 and is company B today -- is NOT observable on this route "
            "and is bounded only by the not-covered rate below."),
    }
    out = os.path.join(_data_root(), "free_analysis", "S25_SECTOR_MAP.json")
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %s" % out)
    return payload


# ---------------------------------------------------------------------------------------
def repair() -> dict:
    """What the look-ahead repair MOVES on the banked valuation panel. No verdict, no trial.

    **THIS MEASURES INPUT MOVEMENT, NOT FAIR-VALUE MOVEMENT, and the reason is a property of
    the banked panel rather than a choice.** `ev_ebitda_used` and `ev_sales_used` are BOOLEAN
    METHOD FLAGS, not the multiples themselves -- checked, not assumed -- so the multiple a row
    was actually scored against is not recoverable and the comps leg cannot be recomputed
    without re-running the valuation. What IS recoverable is which sector-sensitive legs each
    changed row used, from `method`, and that bounds the blast radius honestly.
    """
    import pandas as pd
    from valuation.engine.assumptions import SECTOR_TARGET_MARGIN
    from valuation.engine.comps import SECTOR_MULTIPLES, _DEFAULT

    smap = SM.load(os.path.join(_data_root(), "free_analysis", "S25_SECTOR_MAP.json"))
    panel = pd.read_pickle(os.path.join(_data_root(), "free_analysis",
                                        "panel_s23_fairvalue.pkl"))

    n = len(panel)
    states, b_changed, rev_driven = {}, 0, 0
    a_reclass = 0          # GICS records a reclassification between as_of and today
    a_input = 0            # ... AND the resulting panel-sector string actually differs
    legs = {"multiples": 0, "dcf": 0, "growth": 0, "neither": 0}
    margin_delta, pe_delta, material = [], [], 0
    for r in panel.itertuples(index=False):
        tic, d, panel_sec = str(r.ticker).upper(), str(r.date)[:10], str(r.sector or "")
        at = smap.at(tic, d)
        now = smap.current(tic)
        states[at["state"]] = states.get(at["state"], 0) + 1

        # REPAIR-A (CHANGE-ONLY, the primary): override ONLY where GICS records a
        # reclassification between as_of and today. The crosswalk's taxonomy disagreement
        # cancels by construction, so what moves is look-ahead and nothing else.
        a_sec = panel_sec
        if at["state"] == "OK" and now["state"] == "OK" and at["sector"] != now["sector"]:
            a_sec = at["sector"]
            a_reclass += 1
            if str(SM.classify_transition(now["indfrom"], now["gsector"])).startswith(
                    "TAXONOMY_REVISION"):
                rev_driven += 1
        # REPAIR-B (FULL, sensitivity only, CONFOUNDED by construction).
        b_sec = at["sector"] if at["state"] == "OK" else panel_sec
        if b_sec != panel_sec:
            b_changed += 1

        if a_sec != panel_sec:
            a_input += 1
            md = (SECTOR_TARGET_MARGIN.get(a_sec, 0.12)
                  - SECTOR_TARGET_MARGIN.get(panel_sec, 0.12))
            margin_delta.append(md)
            pe_delta.append(SECTOR_MULTIPLES.get(a_sec, _DEFAULT)["pe"]
                            - SECTOR_MULTIPLES.get(panel_sec, _DEFAULT)["pe"])
            if abs(md) >= 0.05:
                material += 1
            # WHICH SECTOR-SENSITIVE LEGS THIS ROW ACTUALLY USED. A changed sector on a row
            # scored purely by justified P/B moves no engine input at all.
            m = str(getattr(r, "method", "") or "").lower()
            hit = False
            if "multiple" in m:
                legs["multiples"] += 1
                hit = True
            if "dcf" in m:
                legs["dcf"] += 1
                hit = True
            if "growth" in m:
                legs["growth"] += 1
                hit = True
            if not hit:
                legs["neither"] += 1

    def _stats(v):
        if not v:
            return {"n": 0}
        s = sorted(v)
        return {"n": len(s), "mean": round(sum(s) / len(s), 6),
                "min": round(s[0], 6), "max": round(s[-1], 6),
                "median": round(s[len(s) // 2], 6),
                "nonzero": sum(1 for x in s if abs(x) > 1e-12)}

    rep = {
        "panel_rows": n,
        "lookup_states": states,
        "repair_a_change_only": {
            "rows_reclassified": a_reclass,
            "rows_moving_an_engine_input": a_input,
            "share_of_panel": round(a_input / n, 6) if n else None,
            "reclassified_but_input_unchanged": a_reclass - a_input,
            "reclassified_but_input_unchanged_note": (
                "GICS moved the name between two codes the CROSSWALK sends to the SAME panel "
                "string, or onto the panel's own existing label. A real reclassification the "
                "engine cannot see -- reported rather than folded into either count."),
            "of_which_taxonomy_revision": rev_driven,
            "target_margin_delta": _stats(margin_delta),
            "rows_with_material_margin_move_ge_0_05": material,
            "sector_pe_delta": _stats(pe_delta),
            "legs_the_changed_rows_actually_used": legs,
        },
        "repair_b_full_CONFOUNDED": {
            "rows_changed": b_changed,
            "share_of_panel": round(b_changed / n, 6) if n else None,
            "note": ("CONFOUNDED BY CONSTRUCTION: fixes look-ahead AND switches taxonomy in "
                     "one step. Quote only beside taxonomy_disagreement, never alone."),
        },
        "fair_value_not_recomputed": (
            "ev_ebitda_used / ev_sales_used are BOOLEAN METHOD FLAGS on this panel, not the "
            "multiples, so the comps leg cannot be re-derived from what is banked. The "
            "fair-value consequence is therefore NOT measured here and is NOT reported as "
            "zero -- it needs a valuation re-run, which is its own pass."),
        "caveat": ("MEASURED, NOT WIRED. calibration.py is unchanged: changing which sector a "
                   "historical valuation is scored against is a construction change with a "
                   "real blast radius, and it is Don's call, not this pass's."),
    }
    out = os.path.join(_data_root(), "free_analysis", "S25_REPAIR.json")
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(rep, indent=2)[:2600])
    return rep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--repair", action="store_true")
    a = ap.parse_args()
    if a.pull:
        print(json.dumps(pull(), indent=2))
    if a.build:
        p = build()
        print(json.dumps({k: v for k, v in p.items()
                          if k not in ("spans", "ambiguous", "crosswalk")}, indent=2)[:2600])
    if a.repair:
        repair()
    if not (a.pull or a.build or a.repair):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
