# -*- coding: utf-8 -*-
"""D9-DIAG — WHY the free route fails. ZERO TRIALS, no bar, no verdict.

`D9-FIDELITY`'s NO-GO stands whatever this finds. This is a diagnostic of a fidelity control:
`MB1-SEL` says a control can only BLOCK, never produce, so it charges nothing, and nothing here
compares anything to a threshold.

**THE PUZZLE IT EXISTS FOR.** `D9` read composite Spearman **0.4321** (0.6610 repaired) while its
themes read `value` 0.79, `momentum` 0.97, `size` 0.98 -- the blend is worse than every one of
its parts. A weighted mean of well-correlated series should not be less correlated than any of
them, so either the parts are not what the blend is built from, or the two blends are assembled
differently.

**THE DECISIVE TEST IS Q1e: make the assembly identical and re-read.** If the composite Spearman
jumps, the gap is ASSEMBLY -- how the two composites are put together -- and is fixable on the
free path. If it does not, the gap is DATA and a renewal buys a cleaner comparison of the same
disagreement.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
DATA = os.path.join(_ROOT, "data")
FA = os.path.join(DATA, "free_analysis")
LIVE = os.path.join(DATA, "live_cache", "snapshot_2026-08-08.json")
SHAR = os.path.join(FA, "D9_SHARADAR_SCORES.pkl")
OUT = os.path.join(FA, "D9_DIAG.json")
ROWS = os.path.join(FA, "D9_DIAG_ROWS.pkl")

LARGE_CAP_MIN = 1e10
PRIMARY = "freeze_2026-07-31"
SECOND = "backtest_2026-07-24"

#: The deployed seven. `growth`, `low_risk` and `sentiment` carry zero weight in the deployed
#: composite, so they are reported but never composed.
DEPLOYED7 = ("value", "quality", "momentum", "size", "insider",
             "institutional", "capital_discipline")

#: `factors.py:276` -- the quality theme's ten inputs, in its own order.
QUALITY_INPUTS = ("roic", "roe", "op_margin", "gross_margin", "neg_leverage",
                  "gp_on_capital", "fcf_margin", "accruals_q", "interest_cov", "f_score")
#: The TTM siblings the live path also carries. `P6` measured quarterly BEATING TTM on this
#: panel (roe t +2.84 vs +2.01, roic +3.38 vs +2.57), so which one a vendor serves is a
#: DEFINITIONAL difference with a known sign, not a data defect.
QUALITY_TTM = ("roe_ttm", "roic_ttm")


def _z(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    m = x.notna()
    out = pd.Series(np.nan, index=s.index, dtype=float)
    if int(m.sum()) > 1:
        sd = float(x[m].std(ddof=0)) or 1.0
        out[m] = (x[m] - float(x[m].mean())) / sd
    return out


def _sp(a, b):
    a, b = pd.Series(a, dtype=float), pd.Series(b, dtype=float)
    m = a.notna() & b.notna()
    if int(m.sum()) < 20:
        return None, int(m.sum())
    return float(a[m].corr(b[m], method="spearman")), int(m.sum())


def _load(reading=PRIMARY):
    sh = pd.read_pickle(SHAR)[reading]
    s = pd.DataFrame(sh["rows"])
    s["ticker"] = s["ticker"].astype(str).str.upper()
    s = s[~s["ticker"].duplicated()].set_index("ticker")

    with open(LIVE, encoding="utf-8") as fh:
        j = json.load(fh)
    rows = []
    for r in j["rows"]:
        e = r.get("extra") or {}
        nums = e.get("numbers") or {}
        facs = e.get("factors") or {}
        d = {"ticker": str(r["ticker"]).upper(),
             "market_cap": r.get("market_cap"), "bucket": r.get("bucket"),
             "composite_served": r.get("composite")}
        for t in DEPLOYED7:
            d[t] = facs.get(t)
        for n in set(QUALITY_INPUTS) | set(QUALITY_TTM):
            d["num_" + n] = nums.get(n)
        rows.append(d)
    l = pd.DataFrame(rows)
    l = l[~l["ticker"].duplicated()].set_index("ticker")
    return s, l, j


def main(reading=PRIMARY) -> int:
    s, l, lj = _load(reading)
    st = s[pd.to_numeric(s["market_cap"], errors="coerce") >= LARGE_CAP_MIN]
    lt = l[pd.to_numeric(l["market_cap"], errors="coerce") >= LARGE_CAP_MIN]
    both = st.index.intersection(lt.index)
    out = {"item": "D9-DIAG", "trials": 0, "sharadar_reading": reading,
           "note": ("Diagnostic of a fidelity control. No bar, no verdict; D9-FIDELITY's NO-GO "
                    "stands whatever this finds (MB1-SEL)."),
           "populations": {
               "sharadar_scored": int(len(s)), "sharadar_large_cap_tier": int(len(st)),
               "live_scored_reported": lj.get("scored"),
               "live_universe_reported": lj.get("universe_size"),
               "live_rows_in_snapshot": int(len(l)), "live_large_cap_tier": int(len(lt)),
               "overlap": int(len(both))}}

    # ---------------- Q1a. PER-THEME MISSINGNESS ON EACH SIDE
    miss = {}
    for t in DEPLOYED7:
        a = pd.to_numeric(st.loc[both, t], errors="coerce") if t in st.columns else None
        b = pd.to_numeric(lt.loc[both, t], errors="coerce") if t in lt.columns else None
        miss[t] = {
            "sharadar_present": (int(a.notna().sum()) if a is not None else 0),
            "live_present": (int(b.notna().sum()) if b is not None else 0),
            "sharadar_distinct": (int(a.nunique()) if a is not None else 0),
            "live_distinct": (int(b.nunique()) if b is not None else 0),
            "of": int(len(both))}
        # A CONSTANT IS NOT PRESENT DATA. `D9` learned this on `insider`: the theme was
        # non-null on every row and carried one value, so it looked complete and ranked nothing.
        miss[t]["live_is_constant"] = bool(miss[t]["live_distinct"] <= 1
                                           and miss[t]["live_present"] > 0)
        miss[t]["sharadar_is_constant"] = bool(miss[t]["sharadar_distinct"] <= 1
                                               and miss[t]["sharadar_present"] > 0)
    out["Q1a_per_theme_missingness"] = miss

    #: The themes that carry real ranking information on BOTH sides. Everything downstream
    #: composes over exactly these, because a constant or absent theme contributes no ranking
    #: and its presence only changes the renormalisation denominator.
    informative = [t for t in DEPLOYED7
                   if miss[t]["sharadar_present"] >= 20 and miss[t]["live_present"] >= 20
                   and not miss[t]["live_is_constant"] and not miss[t]["sharadar_is_constant"]]
    out["informative_themes_both_sides"] = informative

    # ---------------- Q1b. THE PRESENT-WEIGHT RENORMALISATION
    # `composite_from_frame` renormalises by the mass of the themes PRESENT on a row, so two
    # rows with different present-sets are averaged over different denominators -- and the same
    # name can have different sets on the two sides.
    sp_set = st.loc[both, DEPLOYED7].notna().apply(
        lambda r: tuple(sorted(c for c in DEPLOYED7 if r[c])), axis=1)
    lp_set = lt.loc[both, DEPLOYED7].notna().apply(
        lambda r: tuple(sorted(c for c in DEPLOYED7 if r[c])), axis=1)
    same = (sp_set == lp_set)
    out["Q1b_present_weight_renormalisation"] = {
        "names_with_identical_present_theme_set": int(same.sum()),
        "names_with_a_different_set": int((~same).sum()),
        "frac_different": float((~same).mean()),
        "sharadar_n_present_mean": float(st.loc[both, DEPLOYED7].notna().sum(axis=1).mean()),
        "live_n_present_mean": float(lt.loc[both, DEPLOYED7].notna().sum(axis=1).mean()),
        "note": ("A row whose present-set differs is averaged over a different denominator on "
                 "each side, so its composite is not the same functional of its themes.")}

    # ---------------- Q1c. THE STANDARDISATION CROSS-SECTION
    out["Q1c_standardisation_cross_section"] = {
        "sharadar_standardised_over": int(len(s)),
        "live_standardised_over": lj.get("scored"),
        "ratio": (float(len(s)) / float(lj.get("scored") or 1)),
        "why_it_matters": ("Each theme is a z-score over its OWN scored cross-section. Two "
                           "z-scores of the same underlying rank have different DISPERSION when "
                           "the populations differ, and a composite is a weighted SUM of levels "
                           "-- so a theme with more spread on one side carries more effective "
                           "weight there. S20/S21: rank-IC is invariant to a monotone rescale "
                           "and the composite is not.")}
    for t in informative:
        a = pd.to_numeric(st.loc[both, t], errors="coerce")
        b = pd.to_numeric(lt.loc[both, t], errors="coerce")
        out["Q1c_standardisation_cross_section"].setdefault("theme_sd_on_overlap", {})[t] = {
            "sharadar_sd": float(a.std(ddof=0)), "live_sd": float(b.std(ddof=0)),
            "sd_ratio_live_over_sharadar": (float(b.std(ddof=0)) / (float(a.std(ddof=0)) or 1.0))}

    # ---------------- Q1d. THE BUCKET SPLIT
    if "bucket" in st.columns and "bucket" in lt.columns:
        sb = st.loc[both, "bucket"].astype(str)
        lb = lt.loc[both, "bucket"].astype(str)
        out["Q1d_bucket_split"] = {
            "agree": int((sb == lb).sum()), "of": int(len(both)),
            "frac_agree": float((sb == lb).mean()),
            "sharadar_counts": sb.value_counts().to_dict(),
            "live_counts": lb.value_counts().to_dict(),
            "why_it_matters": ("The LIVE composite weights by bucket "
                              "(WEIGHTS_ESTABLISHED / WEIGHTS_SPECULATIVE), so a name the two "
                              "sides bucket differently is weighted differently before any "
                              "vendor difference is considered.")}

    # ---------------- Q1e. THE DECISIVE TEST: MAKE THE ASSEMBLY IDENTICAL
    # Four cumulative steps, each removing exactly one assembly difference, so the jump
    # attributable to each is readable rather than inferred.
    def _decile_overlap(a, b):
        """Share of the SHARADAR top decile also in the LIVE top decile -- D9's B2, one
        definition (`B7`), so Q1e and Q1f cannot drift apart on the arithmetic."""
        aa, bb = a.dropna(), b.dropna()
        if not len(aa) or not len(bb):
            return None
        k = max(1, int(round(len(aa) * 0.10)))
        return len(set(aa.nlargest(k).index) & set(bb.nlargest(k).index)) / max(1, k)

    def _comp(df, themes, restandardise, complete_case):
        d = df.loc[both, list(themes)].apply(pd.to_numeric, errors="coerce")
        if restandardise:
            d = d.apply(_z)
        if complete_case:
            d = d.dropna(axis=0, how="any")
        return d.mean(axis=1, skipna=True)

    steps = {}
    a0 = pd.to_numeric(st.loc[both, "composite"], errors="coerce")
    b0 = pd.to_numeric(lt.loc[both, "composite_served"], errors="coerce")
    steps["0_as_served"] = dict(zip(("spearman", "n"), _sp(a0, b0)))

    for key, themes, rest, cc in (
            ("1_flat_weights_deployed7", DEPLOYED7, False, False),
            ("2_informative_themes_only", informative, False, False),
            ("3_plus_restandardised_on_overlap", informative, True, False),
            ("4_plus_complete_case", informative, True, True)):
        a = _comp(st, themes, rest, cc)
        b = _comp(lt, themes, rest, cc)
        idx = a.index.intersection(b.index)
        rho, n = _sp(a.loc[idx], b.loc[idx])
        # and the decile overlap at each step, since that is D9's B2
        ov = _decile_overlap(a.loc[idx], b.loc[idx])
        steps[key] = {"spearman": rho, "n": n, "decile_overlap": ov,
                      "themes": list(themes)}
    out["Q1e_identical_assembly"] = steps

    # ---------------- Q1f. EACH THEME'S CONTRIBUTION TO THE DISAGREEMENT
    # Leave-one-out on the IDENTICAL-assembly composite: if dropping a theme RAISES the
    # composite Spearman, that theme is what the blend is losing agreement to.
    base = steps["4_plus_complete_case"]["spearman"]
    loo = {}
    for t in informative:
        rest = [x for x in informative if x != t]
        if len(rest) < 2:
            continue
        a = _comp(st, rest, True, True)
        b = _comp(lt, rest, True, True)
        idx = a.index.intersection(b.index)
        rho, n = _sp(a.loc[idx], b.loc[idx])
        loo[t] = {"spearman_without_it": rho, "n": n,
                  "decile_overlap_without_it": _decile_overlap(a.loc[idx], b.loc[idx]),
                  "delta_vs_full": (None if rho is None or base is None else rho - base)}
    out["Q1f_leave_one_theme_out"] = {
        "full": base,
        "full_decile_overlap": steps["4_plus_complete_case"]["decile_overlap"],
        "without": loo,
        "read": ("a POSITIVE delta means the blend agrees BETTER without that theme, i.e. that "
                 "theme is where the disagreement enters. The DECILE column is reported beside "
                 "it because D9's two bars are not equally hard -- identical assembly clears "
                 "neither, and B2 is the binding one, so a theme whose removal fixes B1 has not "
                 "necessarily fixed B2.")}

    # ---------------- Q2. WHICH QUALITY INPUTS DISAGREE
    q = {}
    for n in QUALITY_INPUTS + QUALITY_TTM:
        col = "num_" + n
        a = pd.to_numeric(st.loc[both, col], errors="coerce") if col in st.columns else None
        b = pd.to_numeric(lt.loc[both, col], errors="coerce") if col in lt.columns else None
        if a is None or b is None:
            q[n] = {"note": "absent on %s" % ("sharadar" if a is None else "live")}
            continue
        rho, nn = _sp(a, b)
        q[n] = {"spearman": rho, "n_both": nn,
                "sharadar_present": int(a.notna().sum()), "live_present": int(b.notna().sum()),
                "sharadar_median": (float(a.median()) if a.notna().any() else None),
                "live_median": (float(b.median()) if b.notna().any() else None),
                "of": int(len(both))}
    # AND THE CROSS-DEFINITION TEST, which is what separates definitional from vendor: does
    # Sharadar's QUARTERLY roe/roic rank the same names as the live side's TTM sibling?
    for base_n, ttm_n in (("roe", "roe_ttm"), ("roic", "roic_ttm")):
        bc, tc = "num_" + base_n, "num_" + ttm_n
        if bc in st.columns and tc in lt.columns:
            rho, nn = _sp(pd.to_numeric(st.loc[both, bc], errors="coerce"),
                          pd.to_numeric(lt.loc[both, tc], errors="coerce"))
            q["CROSSDEF_sharadar_%s_vs_live_%s" % (base_n, ttm_n)] = {
                "spearman": rho, "n_both": nn,
                "read": ("if this beats the like-named pair, the live side is serving a TTM "
                         "quantity under a quarterly name -- DEFINITIONAL and fixable")}
        if bc in st.columns and bc in lt.columns and tc in st.columns:
            rho, nn = _sp(pd.to_numeric(st.loc[both, tc], errors="coerce"),
                          pd.to_numeric(lt.loc[both, bc], errors="coerce"))
            q["CROSSDEF_sharadar_%s_vs_live_%s" % (ttm_n, base_n)] = {
                "spearman": rho, "n_both": nn}
    out["Q2_quality_inputs"] = q

    pd.to_pickle({"sharadar_tier": st, "live_tier": lt, "overlap": list(both)}, ROWS)
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT, "and", ROWS)
    return 0


if __name__ == "__main__":
    import argparse

    _ap = argparse.ArgumentParser()
    _ap.add_argument("--reading", default=PRIMARY, choices=[PRIMARY, SECOND],
                     help="which banked Sharadar reading to diagnose. D9 reported both "
                          "and they agreed; the ladder must reproduce on either, or it "
                          "is a property of one store rather than of the free route")
    _ap.add_argument("--out", default=None,
                     help="write elsewhere, so a second reading cannot clobber the "
                          "primary artifact")
    _a = _ap.parse_args()
    if _a.out:
        # BOTH artifacts move together, or a second reading clobbers the primary's per-name
        # rows while leaving its json intact -- a half-overwritten pair is worse than either.
        OUT = _a.out
        ROWS = os.path.splitext(_a.out)[0] + "_ROWS.pkl"
    raise SystemExit(main(_a.reading))
