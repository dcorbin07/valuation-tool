# -*- coding: utf-8 -*-
"""`INSIDER-CLUSTER` step 0b — two pre-outcome facts the first census raised, and the MDE.

    python -m scripts.insider_cluster_census2

**STILL NO OUTCOME READ.** Three questions, all feasibility:

1. **IS THE "MISSING CODE" ROW A DISTINCT POPULATION, OR THE SAME ROWS THE CLASSIFIER ALREADY
   DROPS?** The first census returned `code_missing` **3,404,501** and `UNCLASSIFIABLE`
   **3,404,613** — within 112 of each other on 11.6M rows, which is far too close to be a
   coincidence. If they are the same rows then the register's skip rule costs nothing beyond what
   classification already costs, and if they are not then two separate holes are being quoted as
   one. **Measured, not assumed.**

2. **DOES "OPPORTUNISTIC" PARTLY MEAN "NO HISTORY TO BE ROUTINE WITH"?** The classifier labels a
   pair ROUTINE only when it traded in the same month in each of the two prior years; a pair with
   no prior years at all is therefore OPPORTUNISTIC **by default**. On this universe that is a
   live worry rather than a quibble: the freeze's routine share of classifiable rows is **33.86%**
   against `MB20`'s **60.47%** under the identical three-year rule on the `data/backtest`
   population, and the difference is exactly what a wider, younger universe would produce. Left
   unmeasured, the opportunistic arm would be a **data-availability screen wearing a behavioural
   screen's name** — `S10`'s failure mode, and this project's most repeated one.

   So the STRICT form is measured here: the pair must have traded **at least once in each of the
   two prior calendar years**, so routine was POSSIBLE and did not happen. It is computed as a
   mask ALONGSIDE the shipped classifier rather than by editing it (`B7`).

3. **THE MDE, from the census's own dispersion bound**, via `power_gate` so the arithmetic is not
   retyped. Reported for both populations and every horizon, BEFORE the register fixes its bars —
   which is the whole point of running this first.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import power_gate as PG                                 # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402
from valuation.studies import insider_routine as IR                         # noqa: E402

OUT = "INSIDER_CLUSTER_CENSUS2.json"

#: The economic floor: a round trip at `B11`'s MEASURED 33.4 bps one way. `DIP-CALL`'s own
#: constant, reused verbatim rather than re-chosen.
COST_FLOOR_PP = 0.67

#: Cohen-Malloy-Pomorski's published figure, as the scout quoted it: ~82 bps/month LONG-SHORT,
#: about 1.64% over 60 days. The LONG-ONLY leg is a FRACTION of that, and the register may not
#: pretend otherwise -- both are carried so the power statement is honest about which it is
#: measuring.
CMP_LONGSHORT_60D_PP = 1.64
#: Cohen-Malloy-Pomorski's rate as PUBLISHED: ~82 bps per MONTH, long-short.
CMP_LONGSHORT_PP_PER_MONTH = 0.82
#: The long-only leg at an even split. An ASSUMPTION, labelled, used only to say what the design
#: could see -- never as an expected return.
CMP_LONGONLY_PP_PER_MONTH_ASSUMED = 0.41

#: Trading sessions in a month. The horizon scaling below needs one number and this is it.
SESSIONS_PER_MONTH = 21.0


def expected_effect_pp(h: float) -> float:
    """The hypothesised long-only drift over `h` sessions, scaled from CMP's MONTHLY rate.

    **A CORRECTION TO THIS SCRIPT'S OWN FIRST PASS, MADE BEFORE THE REGISTER WAS WRITTEN AND
    BEFORE ANY OUTCOME EXISTED.** That pass compared EVERY horizon against a flat 0.82pp, which
    is wrong in both directions at once: drift ACCUMULATES, so a flat effect understates power at
    a long horizon and overstates it at a short one. It made h=126 look UNDERPOWERED (required n
    11,689 against 8,478 available) when scaling the effect properly puts its requirement an
    order of magnitude lower, and it made h=5 look feasible when the effect there is a tenth of
    the round-trip cost.

    The algebra is the reason it matters: dispersion grows as `sqrt(h)` while drift grows as `h`,
    so `required_n` is proportional to `(sd/effect)^2` and therefore to **1/h** — LONGER horizons
    need FEWER events, which is the opposite of the first pass's reading.
    """
    return CMP_LONGONLY_PP_PER_MONTH_ASSUMED * (float(h) / SESSIONS_PER_MONTH)


def strict_opportunistic(df: pd.DataFrame, labels: pd.Series) -> dict:
    """Share of opportunistic purchase rows whose pair was OBSERVABLE in both prior years."""
    tk = df["ticker"].astype("string")
    ow = df["ownername"].astype("string")
    td = pd.to_datetime(df["transactiondate"], errors="coerce")
    ok = tk.notna() & ow.notna() & td.notna()
    y = td.dt.year
    # the (pair, year) cells that exist anywhere in the file
    seen = set(zip(tk[ok].tolist(), ow[ok].tolist(), y[ok].astype("int64").tolist()))
    code = df["transactioncode"]
    is_buy = (code == IC.PURCHASE_CODE).fillna(False).to_numpy(dtype=bool)
    opp = (labels.to_numpy() == IR.OPPORTUNISTIC) & is_buy & ok.to_numpy(dtype=bool)
    idx = np.flatnonzero(opp)
    t_l = tk.to_numpy()
    o_l = ow.to_numpy()
    y_l = y.to_numpy()
    strict = np.zeros(len(idx), dtype=bool)
    for j, i in enumerate(idx):
        yy = int(y_l[i])
        strict[j] = ((t_l[i], o_l[i], yy - 1) in seen) and ((t_l[i], o_l[i], yy - 2) in seen)
    return {
        "opportunistic_purchase_rows": int(idx.size),
        "strict_rows": int(strict.sum()),
        "strict_share": (float(strict.mean()) if idx.size else float("nan")),
        "WHY_IT_MATTERS": ("a pair with no prior years is OPPORTUNISTIC by default, so without "
                           "this the arm is partly a data-availability screen -- S10's failure "
                           "mode"),
    }


def overlap(df: pd.DataFrame, labels: pd.Series) -> dict:
    code_missing = df["transactioncode"].isna().to_numpy(dtype=bool)
    unclass = (labels.to_numpy() == IR.UNCLASSIFIABLE)
    both = int((code_missing & unclass).sum())
    return {
        "code_missing": int(code_missing.sum()),
        "unclassifiable": int(unclass.sum()),
        "both": both,
        "code_missing_only": int((code_missing & ~unclass).sum()),
        "unclassifiable_only": int((~code_missing & unclass).sum()),
        "share_of_code_missing_also_unclassifiable": (both / int(code_missing.sum())
                                                      if code_missing.any() else float("nan")),
    }


def mde_table(cens: dict) -> dict:
    """MDE per population per horizon, from the census's dispersion bound. `power_gate` only."""
    disp = cens["k2"]["dispersion_bound"]
    pops = {
        "full_universe": (cens["k2"]["build_half0"]["events"],
                          cens["k2"]["build_half0"]["distinct_tickers"]),
        "tier_cap_ge_10bn": (cens["k2"]["build_half0_tier"]["events_cap_ge_10bn"],
                             cens["k2"]["build_half0_tier"]["distinct_tickers"]),
    }
    out = {}
    for pop, (n, g) in pops.items():
        rows = {}
        for h, blk in disp.items():
            sd = float(blk["median_sd"])
            if not (n and g and np.isfinite(sd)):
                continue
            eff_pp = expected_effect_pp(float(h))
            se_naive = sd / (n ** 0.5)
            # CLUSTER INFLATION, as a pre-outcome BOUND. sqrt(n/G) is the inflation under the
            # worst case of perfect within-ticker correlation; the realised figure will be
            # smaller, so this is the CONSERVATIVE direction -- the opposite of the dispersion
            # bound above, which is optimistic. BOTH are labelled; neither is the arm's own se,
            # which is what the verdict must travel with (MB8).
            infl = (n / g) ** 0.5
            se_cl = se_naive * infl
            rows[h] = {
                "n_events": int(n), "n_ticker_clusters": int(g),
                "sd_bound": sd,
                "se_naive_pp": se_naive * 100.0,
                "cluster_inflation_worst_case": infl,
                "se_clustered_pp": se_cl * 100.0,
                "mde80_naive_pp": (2.0 + PG.z_for_power(0.80)) * se_naive * 100.0,
                "mde80_clustered_pp": (2.0 + PG.z_for_power(0.80)) * se_cl * 100.0,
                "power_vs_cost_floor_naive": PG.power_at(COST_FLOOR_PP / 100.0, se_naive,
                                                         crit=2.0),
                "power_vs_cost_floor_clustered": PG.power_at(COST_FLOOR_PP / 100.0, se_cl,
                                                             crit=2.0),
                "expected_effect_pp": eff_pp,
                "expected_effect_clears_cost_floor": bool(eff_pp > COST_FLOOR_PP),
                "power_vs_cmp_longonly_naive": PG.power_at(eff_pp / 100.0, se_naive, crit=2.0),
                "power_vs_cmp_longonly_clustered": PG.power_at(eff_pp / 100.0, se_cl, crit=2.0),
                "state_naive": PG.state(eff_pp / 100.0, se_naive, crit=2.0),
                # THE DERIVED EVENT FLOOR. `required_n` works in units of ONE OBSERVATION'S SD,
                # so the effect is standardised by the horizon's own dispersion bound -- the one
                # way this is easy to get wrong, and the library's docstring says so. This is the
                # n at which the NAIVE 80%-power MDE equals the hypothesised long-only effect; the
                # naive bound is the OPTIMISTIC end, so a cell below this floor cannot work under
                # any clustering assumption, which is what makes it a legitimate free kill rather
                # than a bar reverse-engineered to be cleared.
                "required_n_at_cmp_longonly": PG.required_n((eff_pp / 100.0) / sd, crit=2.0),
                "required_n_at_cost_floor": PG.required_n(
                    (COST_FLOOR_PP / 100.0) / sd, crit=2.0),
                "clears_required_n_at_cmp_longonly": bool(
                    n >= PG.required_n((eff_pp / 100.0) / sd, crit=2.0)),
            }
        out[pop] = rows
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mde-only", action="store_true",
                    help="skip the two premise facts (already banked) and recompute the MDE "
                         "against whatever census is on disk")
    a = ap.parse_args(argv)
    cens_p = D.out_path("INSIDER_CLUSTER_CENSUS.json")
    cens = json.load(io.open(cens_p, encoding="utf-8"))

    out = {"item": "INSIDER-CLUSTER", "part": "step 0b -- two premise facts and the MDE",
           "trials": 0,
           "trial_class": ("CENSUS + POWER DERIVATION -- no hypothesis, no bar, no outcome "
                           "statistic, no forward return"),
           "reads": os.path.basename(cens_p)}

    print("[c2] MDE from the census's own dispersion bound ...", flush=True)
    out["mde"] = mde_table(cens)
    for pop, rows in out["mde"].items():
        for h in ("5", "21", "63", "126"):
            if h in rows:
                r = rows[h]
                print("  %-18s h=%-4s n=%-6d G=%-5d  MDE80 naive %.2fpp / clustered %.2fpp  "
                      "power vs 0.82pp: %.1f%% / %.1f%%"
                      % (pop, h, r["n_events"], r["n_ticker_clusters"],
                         r["mde80_naive_pp"], r["mde80_clustered_pp"],
                         100 * r["power_vs_cmp_longonly_naive"],
                         100 * r["power_vs_cmp_longonly_clustered"]), flush=True)
                print("    effect %.2fpp (clears cost floor: %s)  required n %.0f -> clears %s"
                      % (r["expected_effect_pp"], r["expected_effect_clears_cost_floor"],
                         r["required_n_at_cmp_longonly"],
                         r["clears_required_n_at_cmp_longonly"]), flush=True)

    if a.mde_only:
        prev = json.load(io.open(D.out_path(OUT), encoding="utf-8"))
        out["code_missing_vs_unclassifiable"] = prev["code_missing_vs_unclassifiable"]
        out["strict_opportunistic"] = prev["strict_opportunistic"]
        out["NOTE"] = "premise facts carried from the previous pass; only the MDE recomputed"
    else:
        print("[c2] loading SF2 again for the two premise facts ...", flush=True)
        df = IC.load_sf2()
        labels = IC.label_rows(df)
        out["code_missing_vs_unclassifiable"] = overlap(df, labels)
        print("[c2] overlap: %s" % json.dumps(out["code_missing_vs_unclassifiable"]), flush=True)
        out["strict_opportunistic"] = strict_opportunistic(df, labels)
        print("[c2] strict: %s" % json.dumps(out["strict_opportunistic"]), flush=True)

    out["cost_floor_pp"] = COST_FLOOR_PP
    out["cmp_longshort_60d_pp"] = CMP_LONGSHORT_60D_PP
    out["cmp_longshort_pp_per_month"] = CMP_LONGSHORT_PP_PER_MONTH
    out["cmp_longonly_pp_per_month_ASSUMED"] = CMP_LONGONLY_PP_PER_MONTH_ASSUMED
    out["effect_scales_with_horizon"] = (
        "drift accumulates as h while dispersion grows as sqrt(h), so required_n is "
        "proportional to 1/h -- longer horizons need FEWER events. This script's own first pass "
        "compared every horizon against a flat 0.82pp and got that backwards; corrected before "
        "the register was written and before any outcome existed.")

    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[c2] wrote %s" % p, flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
