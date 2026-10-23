# -*- coding: utf-8 -*-
"""Step 3 -- can EODHD stand in for Sharadar on the live scoring path?

**ZERO TRIALS, `FIXED`-class.** No hypothesis about returns, no bar of its own, nothing adopted.
It asks whether two vendors rank the same names the same way, which is a fact about data rather
than a claim about the market.

**THE BARS ARE `D9`'s, IMPORTED AND NOT RETYPED.** `PREREG_d9_free_route_fidelity.md` section 4
already pre-committed what a usable substitute looks like, so re-choosing a bar here with a
cross-vendor number in hand is exactly what that register's own void condition forbids. `B1` >= 0.80
composite Spearman, `B2` >= 0.60 top-decile overlap, `B3` >= 0.70 on EACH of value / quality /
momentum / size, `B4` cited from `FIDELITY-2`. **Ambiguous against a bar is NO-GO.**

**THREE DEVIATIONS FROM THE BRIEF, ALL DECLARED BEFORE ANY NUMBER WAS READ.**

1. **THE DATE IS 2026-10-02, NOT 2026-10-22.** Both Sharadar stores end `2026-10-02` (checked:
   `data/backtest/prices/AAPL.csv` and the `backtest_freeze_2026-10` copy both end there) and
   `score_universe_now` **refuses** an as-of it cannot honour exactly. So a Sharadar 10-22 book
   cannot be built without a fresh licensed pull. 10-02 is the newest date **both** vendors can be
   read at, and it is strictly the better experiment: EODHD's filing dates are real, so its side is
   cut point-in-time at the same date and **there is no vendor-gap to confound the reading**. A
   10-22 EODHD book against a 10-02 Sharadar book would have mixed a 14-trading-day drift into
   every disagreement, and `D9`'s own noise ceiling says that drift is not small.
   **A CONSEQUENCE WORTH STATING: the Sharadar side is ALREADY BANKED**
   (`D9_SHARADAR_SCORES_SAMEDATE.pkl`, 2,037 rows, 835 in the tier), so the brief's deadline -- get
   this done before the licence lapses -- **is already retired**. Nothing here needs Sharadar live.

2. **`B1` IS COMPUTED ON FOUR THEMES, WHERE `D9` USED FIVE.** `D9`'s `LIKE_FOR_LIKE` includes
   `insider`, and the EODHD side cannot carry it: the feed is **137,297 rows** over 2009-2026
   against the licensed file's **5,636,964**, about **2.4%**, and `ownerCik` is **0.0000 from 2023
   on**. Scoring a five-theme Sharadar composite against a four-theme EODHD one would not be
   like-for-like, so **both sides are composed on the same four themes** -- the four that carry a
   `B3` bar -- and `insider` is cited under `B4` exactly as `D9` already treats it.
   **SO THIS `B1` AND `D9`'s `B1` ARE NOT THE SAME STATISTIC** and may not be compared with each
   other, though they share the 0.80 bar.

3. **BOTH SIDES RUN THROUGH `score_universe_now`.** `D9` compared a Sharadar book against a
   **served** composite out of a scan JSON -- two code paths as well as two vendors. Here the only
   thing that differs is the data; see `valuation/studies/eodhd_provider.py`.

**THE PROBE GATES THE COMPARISON AND IS READ IN ITS OWN PASS.** `--probe` reports every mapped
field's non-null rate on the tier itself and **refuses** if a required column never appeared. Five
wired factors were once empty in every run of this project's history without raising, so a vendor
mapping that has not been measured is not evidence about the vendor. `--compare` exits non-zero
without a passing probe artifact.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import d9_fidelity as D9                                   # noqa: E402
from valuation.studies import eodhd_provider as EP                       # noqa: E402

#: **RESOLVED BESIDE THE INPUTS, NOT FROM THE REPO ROOT.** A worktree carries `data/` EMPTY while
#: the banked artifacts live in the primary checkout, so a repo-relative path here reads nothing and
#: a study built on it would skip or score an empty frame. `E-5`'s wrong-object family, and the
#: exact defect `W-1` had to repair in `MB31`'s own tripwire. `required=False` ASKS rather than
#: raising, because the raising form has broken a suite in CI before.
from valuation.studies import dipcall as _D                              # noqa: E402

_DATA = _D.data_root(required=False) or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FA = os.path.join(_DATA, "free_analysis")
FREEZE = os.path.join(r"D:\eodhd", "freeze_2026-10-22")
SAMEDATE = os.path.join(FA, "D9_SHARADAR_SCORES_SAMEDATE.pkl")
AS_OF = "2026-10-02"
PROBE_OUT = os.path.join(FA, "EODHD_FIDELITY_PROBE.json")
SCORES_OUT = os.path.join(FA, "EODHD_SCORES_%s.pkl" % AS_OF)
OUT = os.path.join(FA, "EODHD_FIDELITY.json")

#: The themes BOTH sides are composed on. Four, for the measured reason in the docstring.
THEMES = D9.B3_THEMES

#: A required column must resolve on at least this share of harvested rows or the probe refuses.
#: Not a performance bar -- a presence bar, and it is deliberately loose, because its job is to
#: catch a WRONG FIELD NAME (which reads 0.0000) rather than to judge the vendor's completeness.
REQUIRED_FLOOR = 0.50


def _sh_rows():
    sh = pd.read_pickle(SAMEDATE)
    blk = sh.get("same_date_%s" % AS_OF) or {}
    if "rows" not in blk:
        raise SystemExit("the banked Sharadar same-date block has no rows: %r" % (blk.get("error"),))
    return blk


def tier_names():
    """The $10B tier as of the comparison date, taken from the SHARADAR side.

    Deliberately the Sharadar tier and not a tier defined on EODHD market caps: the question is
    whether EODHD can rank the book the project actually holds, so the population is fixed by the
    incumbent and the challenger is asked about it. Defining the tier on the challenger's own caps
    would let a market-cap disagreement silently change which names are compared.
    """
    d = pd.DataFrame(_sh_rows()["rows"])
    d["ticker"] = d["ticker"].astype(str).str.upper()
    mc = pd.to_numeric(d["market_cap"], errors="coerce")
    return sorted(d.loc[mc >= D9.LARGE_CAP_MIN, "ticker"].dropna().unique())


def probe(argv=None):
    names = tier_names()
    rep = EP.probe(FREEZE, names)
    rep["as_of"] = AS_OF
    rep["tier_names_requested"] = len(names)
    rep["freeze"] = FREEZE
    rep["required_floor"] = REQUIRED_FLOOR
    rep["capex_sign"] = EP.capex_sign(FREEZE, names)
    low = {c: rep["field_non_null"].get(c) for c in EP.REQUIRED
           if (rep["field_non_null"].get(c) or 0.0) < REQUIRED_FLOOR}
    rep["required_below_floor"] = low
    rep["probe_pass"] = bool(rep["rows"] > 0 and not rep["required_missing"] and not low)
    with open(PROBE_OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    print("[probe] tier %d | payloads %d | rows %d" % (len(names), rep["names_with_a_payload"],
                                                       rep["rows"]))
    print("[probe] periods %d, with a filing date %d, dropped %d"
          % (rep["statement_periods"], rep["periods_with_filing_date"],
             rep["periods_dropped_no_filing_date"]))
    if rep["never_seen"]:
        print("[probe] FIELDS THAT NEVER APPEARED: %s" % ", ".join(rep["never_seen"]))
    for c in sorted(EP.REQUIRED):
        print("    required %-10s %.4f" % (c, rep["field_non_null"].get(c) or 0.0))
    print("[probe] capex sign: %s" % json.dumps(rep["capex_sign"]))
    print("[probe] %s -> %s" % ("PASS" if rep["probe_pass"] else "REFUSED", PROBE_OUT))
    return 0 if rep["probe_pass"] else 2


def score(argv=None):
    if not (os.path.exists(PROBE_OUT) and json.load(open(PROBE_OUT, encoding="utf-8"))
            .get("probe_pass")):
        print("[score] REFUSED: no passing probe artifact at %s" % PROBE_OUT)
        return 2
    from valuation.edge.fundamental_panel import score_universe_now
    from valuation.edge.data_providers import WRDSProvider

    class _C:
        wrds_data_dir = os.path.join(_DATA, "backtest")

    px = WRDSProvider(_C())
    ok, msg = px.ready()
    if not ok:
        print("[score] price delegate not ready: %s" % msg)
        return 2
    prov = EP.EodhdProvider(FREEZE, px)
    ok, msg = prov.ready()
    print("[score] eodhd provider: %s (%s)" % (ok, msg))
    if not ok:
        return 2
    names = tier_names()
    res = score_universe_now(prov, names, as_of=AS_OF, with_themes=True, with_numbers=True)
    # `score_universe_now` returns a dict on success and a bare list on either early exit, and
    # REFUSES an as-of it cannot honour. Both states are handled explicitly rather than read as
    # "0 rows", which is the silent-empty failure this project has paid for repeatedly.
    refused = res.get("refused") if isinstance(res, dict) else None
    if refused:
        print("[score] REFUSED by the scorer: %s" % refused)
        return 2
    rows = res.get("rows") if isinstance(res, dict) else list(res)
    print("[score] %d rows" % len(rows))
    pd.to_pickle({"as_of": AS_OF, "rows": rows, "freeze": FREEZE,
                  "return_was_dict": isinstance(res, dict)}, SCORES_OUT)
    return 0 if rows else 2


def compare(argv=None):
    if not os.path.exists(SCORES_OUT):
        print("[compare] REFUSED: no EODHD scores at %s" % SCORES_OUT)
        return 2
    sh = D9._sharadar_frame(_sh_rows()["rows"])
    eo = D9._sharadar_frame(pd.read_pickle(SCORES_OUT)["rows"])

    out = {"item": "EODHD-FIDELITY", "step": "3 cross-vendor", "trials": 0,
           "as_of": AS_OF, "class": "FIXED",
           "themes_compared": list(THEMES),
           "bars": {"B1_composite_spearman": D9.B1_COMPOSITE_SPEARMAN,
                    "B2_decile_overlap": D9.B2_DECILE_OVERLAP,
                    "B3_theme_spearman": D9.B3_THEME_SPEARMAN,
                    "B4_cited_from_FIDELITY2": D9.FIDELITY2},
           "bars_source": "PREREG_d9_free_route_fidelity.md section 4, imported not retyped",
           "sharadar_rows": int(len(sh)), "eodhd_rows": int(len(eo))}

    sh_t = sh[pd.to_numeric(sh["market_cap"], errors="coerce") >= D9.LARGE_CAP_MIN].copy()
    eo_t = eo[pd.to_numeric(eo["market_cap"], errors="coerce") >= D9.LARGE_CAP_MIN].copy()
    out["sharadar_tier_rows"] = int(len(sh_t))
    out["eodhd_tier_rows"] = int(len(eo_t))

    # The composite is built on the SAME four themes on both sides, through D9's own primitive.
    sh_t["ll"] = D9._flat_composite(sh_t, THEMES)
    eo_t["ll"] = D9._flat_composite(eo_t, THEMES)

    common = sorted(set(sh_t.index) & set(eo_t.index))
    out["overlapping_names"] = len(common)
    if len(common) < 20:
        out["verdict"] = "NO-GO (too few overlapping names to resolve any bar)"
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, sort_keys=True)
        print("[compare] only %d overlapping names -> %s" % (len(common), out["verdict"]))
        return 0
    a, b = sh_t.loc[common], eo_t.loc[common]

    rho, n = D9._sp(a["ll"], b["ll"])
    out["B1_like_for_like_composite_spearman"] = rho
    out["B1_n"] = n
    out["B1_pass"] = bool(rho is not None and rho >= D9.B1_COMPOSITE_SPEARMAN)

    k = max(1, len(common) // 10)
    ta = set(a["ll"].dropna().sort_values(ascending=False).head(k).index)
    tb = set(b["ll"].dropna().sort_values(ascending=False).head(k).index)
    out["B2_decile_n"] = k
    out["B2_overlapping_names"] = len(ta & tb)
    out["B2_decile_overlap"] = len(ta & tb) / max(1, len(ta))
    out["B2_pass"] = bool(out["B2_decile_overlap"] >= D9.B2_DECILE_OVERLAP)
    # **THE MARGIN IN NAMES, NOT IN RATE.** A decile of this size moves 1.22pp per name, so the
    # rate alone hides how thin a pass is. Quoted as a count because that is the unit the verdict
    # actually turns on.
    _one_fewer = (len(ta & tb) - 1) / max(1, len(ta))
    import math
    _min_pass = math.ceil(D9.B2_DECILE_OVERLAP * k - 1e-9)
    out["B2_minimum_passing_name_count"] = int(_min_pass)
    out["B2_margin_names_above_the_bar"] = int(len(ta & tb) - _min_pass)
    out["B2_rate_if_one_fewer_name_overlapped"] = _one_fewer
    out["B2_one_fewer_name_would_fail"] = bool(_one_fewer < D9.B2_DECILE_OVERLAP)

    out["B3_themes"] = {}
    for t in THEMES:
        if t in a.columns and t in b.columns:
            rt, nt = D9._sp(a[t], b[t])
            out["B3_themes"][t] = {"spearman": rt, "n": nt,
                                   "pass": bool(rt is not None
                                                and rt >= D9.B3_THEME_SPEARMAN)}
        else:
            out["B3_themes"][t] = {"spearman": None, "n": 0, "pass": False,
                                   "note": "theme absent on one side"}
    out["B3_pass"] = all(v["pass"] for v in out["B3_themes"].values())

    # **TWO OF THE FOUR THEMES SHARE A PRICE SOURCE, SO THEY ARE NOT VENDOR EVIDENCE.**
    # `price_history` is delegated to the Sharadar provider on BOTH sides, so `momentum` is built
    # from identical price series and is near-1 BY CONSTRUCTION. `size` is a genuine reading --
    # the only EODHD input to it is shares outstanding -- and the market-cap agreement below is
    # what licenses saying so. The diagnostic strips both price-linked themes and re-reads the
    # composite on `value` and `quality` alone. It carries NO BAR: it was not pre-registered, and
    # promoting a statistic to decisive after seeing it is what D9's void conditions forbid.
    _mc = (pd.to_numeric(a["market_cap"], errors="coerce"),
           pd.to_numeric(b["market_cap"], errors="coerce"))
    _rel = ((_mc[1] - _mc[0]).abs() / _mc[0].abs()).dropna()
    out["market_cap_spearman"] = float(_mc[0].corr(_mc[1], method="spearman"))
    out["market_cap_median_relative_difference"] = float(_rel.median()) if len(_rel) else None
    out["market_cap_share_within_1pct"] = float((_rel <= 0.01).mean()) if len(_rel) else None
    _vq, _ = D9._sp(D9._flat_composite(a, ("value", "quality")),
                    D9._flat_composite(b, ("value", "quality")))
    out["DIAGNOSTIC_composite_value_quality_only_NO_BAR"] = _vq
    out["DIAGNOSTIC_note"] = (
        "momentum is near-1 BY CONSTRUCTION because prices are delegated to the same provider on "
        "both sides, so it is a check that the delegation works and NOT evidence about EODHD. The "
        "informative B3 cells are value and quality. This diagnostic re-reads the composite "
        "without either price-linked theme and carries no bar.")
    allpass = bool(out["B1_pass"] and out["B2_pass"] and out["B3_pass"])
    out["verdict"] = "GO" if allpass else "NO-GO"
    out["how_to_read_it"] = (
        "GO means EODHD ranks this tier closely enough to stand in on the LIVE scoring path at "
        "this one date. It is NOT a statement about the backtest, about any era before 2009, or "
        "about returns, and it adopts nothing. A switch on a personal plan also needs the licence "
        "question answered, because the Index is published.")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)

    print("[compare] overlapping %d of (sharadar %d, eodhd %d)"
          % (len(common), len(sh_t), len(eo_t)))
    print("  B1 composite  %s  bar %.2f  -> %s"
          % ("%.4f" % rho if rho is not None else "None", D9.B1_COMPOSITE_SPEARMAN,
             out["B1_pass"]))
    print("  B2 top decile %.4f (n %d)  bar %.2f  -> %s"
          % (out["B2_decile_overlap"], k, D9.B2_DECILE_OVERLAP, out["B2_pass"]))
    for t in THEMES:
        v = out["B3_themes"][t]
        print("  B3 %-9s %s (n %s)  bar %.2f  -> %s"
              % (t, "%.4f" % v["spearman"] if v["spearman"] is not None else "None",
                 v["n"], D9.B3_THEME_SPEARMAN, v["pass"]))
    print("  B2 margin: %d of %d names overlap; one fewer would read %.4f and %s"
          % (out["B2_overlapping_names"], k, out["B2_rate_if_one_fewer_name_overlapped"],
             "FAIL" if out["B2_one_fewer_name_would_fail"] else "still pass"))
    print("  market cap: spearman %.4f, median rel diff %.6f"
          % (out["market_cap_spearman"], out["market_cap_median_relative_difference"]))
    print("  DIAGNOSTIC (no bar) composite on value+quality only: %.4f"
          % out["DIAGNOSTIC_composite_value_quality_only_NO_BAR"])
    print("[compare] VERDICT %s -> %s" % (out["verdict"], OUT))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args(argv)
    if a.probe:
        return probe()
    if a.score:
        return score()
    if a.compare:
        return compare()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
