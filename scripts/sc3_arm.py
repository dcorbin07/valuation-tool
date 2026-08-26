"""SC-3 (TIER-E-FIN) — THE ARM. All-in financing cost at 200–858 DTE, 2016–2018.

`PREREG_sc3_tier_e_financing.md` committed ALONE and BLIND at `293a1e7`; the 2 options trials
booked at `1fd7f3d` BEFORE this file existed, `N` 308 → 310.

NOTHING IS RE-IMPLEMENTED. `D.build` is `DEEPITM-FIN`'s own pair builder and produces the full
column set `annual_cost` consumes; `annual_cost`, `matched_pairs`, `implied_rate`, `call_delta`,
`pv_dividends`, `load_spot`, `load_dividends` and the `rf` source are all imported from it. **Only
the DTE band moves**, and it moves as a parameter rather than by editing that module — a second
copy of the pair builder would stop this being the same measurement at a different tenor (`B7`).

THE UNIT OF INDEPENDENCE IS THE NAME (register §3). 2.35M pairs are ~408 names observed on many
days on overlapping contracts; every headline is a per-name median and then a cross-name statistic.

    python -m scripts.sc3_arm --build     # rebuild pairs with the full column set (slow)
    python -m scripts.sc3_arm --score     # strata, cards, verdict
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge import chain_store as cs                          # noqa: E402
from valuation.edge import power_gate as pg                           # noqa: E402
from valuation.edge import research_log as rl                         # noqa: E402
from valuation.edge import statistics as st                           # noqa: E402
import deepitm_financing as D                                         # noqa: E402
import sc3_coverage as COV                                            # noqa: E402

BOOK = "SC3_PAIRS.pkl"
OUT = "SC3_ARM.json"

# ---- the register's declared constants. None is chosen here. ---------------------------------
YEARS = COV.YEARS                       # 2016-2018: the only window Tier E reaches past 200 DTE
LONG_LO, LONG_HI = COV.LONG_LO, COV.LONG_HI
STRATA = ((200, 300), (300, 450), (450, 650), (650, 858))   # §3, fixed on COVERAGE, all reported
MIN_N = D.MIN_N                         # 30, DEEPITM-FIN's own floor reused verbatim
MIN_NAMES_PER_STRATUM = 100             # §4

# Published retail cards. ASSUMPTIONS, not measurements, and labelled so everywhere (§5).
CARDS = {"robinhood_gold": 420.0, "ibkr_pro": 150.0, "robinhood_standard": 995.0}
DEEPITM_ALL_IN = 701.87                 # DEEPITM-FIN's own 60-90 DTE figure, quoted not re-derived

DRAWS = 2000
SEED = 20260825


def build() -> pd.DataFrame:
    chains, prov = cs.resolve_harvest()
    if not prov.get("pinned"):
        raise SystemExit("SC-3 reads the PINNED harvest freeze only")
    print("harvest: %s  manifest %s"
          % (chains, str(prov.get("manifest_sha256"))[:16]), flush=True)

    spot = D.load_spot()
    divs = D.load_dividends()
    if not spot:
        raise SystemExit("REFUSING: no spot series. EXISTENCE IS NOT POPULATION.")

    syms = sorted(d for d in os.listdir(chains) if os.path.isdir(os.path.join(chains, d)))
    out, ck = [], COV._out(BOOK + ".partial")
    done = set()
    if os.path.exists(ck):
        prev = pd.read_pickle(ck)
        out = [prev]
        done = set(prev["symbol"].astype(str))
        print("resuming: %d rows, %d names done" % (len(prev), len(done)), flush=True)

    old = (D.DTE_LO, D.DTE_HI)
    D.DTE_LO, D.DTE_HI = LONG_LO, LONG_HI
    try:
        for i, sym in enumerate(syms, 1):
            if sym.upper() in done:
                continue
            d = os.path.join(chains, sym)
            frames = []
            for y in YEARS:
                f = os.path.join(d, "%s-%d.pkl" % (sym, y))
                if not os.path.isfile(f):
                    continue
                try:
                    fr = COV.chain_frame(f)
                except Exception:                                      # noqa: BLE001
                    continue
                if isinstance(fr, pd.DataFrame) and len(fr):
                    frames.append(fr)
            if not frames:
                continue
            df = pd.concat(frames, ignore_index=True)
            df["date"] = pd.to_datetime(df["date"])
            df["expiration"] = pd.to_datetime(df["expiration"])
            df["dte"] = (df["expiration"] - df["date"]).dt.days
            df["symbol"] = sym.upper()
            df["right"] = df["right"].astype(str).str.upper().str[:1]
            if not len(df[(df["dte"] >= LONG_LO) & (df["dte"] <= LONG_HI)]):
                continue
            try:
                # DEEPITM-FIN's OWN builder, which emits every column annual_cost consumes.
                p = D.build(df, spot, divs)
            except RuntimeError:
                # its own refusal on an empty result - a name with no deep-ITM long pairs
                continue
            if len(p):
                out.append(p)
            if i % 100 == 0:
                pd.concat(out, ignore_index=True).to_pickle(ck)
                print("  ... %d/%d names, %d pairs (checkpointed)"
                      % (i, len(syms), sum(len(x) for x in out)), flush=True)
    finally:
        D.DTE_LO, D.DTE_HI = old

    pairs = pd.concat(out, ignore_index=True)
    pairs.to_pickle(COV._out(BOOK))        # RULE 9: draws land before anything is summarised
    if os.path.exists(ck):
        os.remove(ck)
    print("wrote %s  pairs %d  names %d"
          % (BOOK, len(pairs), pairs["symbol"].nunique()), flush=True)
    return pairs


def _per_name(pairs: pd.DataFrame, rho: float) -> pd.DataFrame:
    """Per-name median all-in cost. THE NAME IS THE UNIT (§3)."""
    x = pairs.copy()
    x["all_in"] = D.annual_cost(x, rho=rho)
    g = x.groupby("symbol")
    per = g.agg(n=("all_in", "size"),
                all_in=("all_in", "median"),
                fin=("excess_exe_bps", "median"),
                fin_mid=("excess_mid_bps", "median"),
                dte=("dte", "median"),
                call_half=("call_half_bps", "median"),
                comm=("commission_bps", "median")).reset_index()
    per = per[per["n"] >= MIN_N]
    per["rolls"] = 365.0 / per["dte"]
    per["roll_bps"] = 2.0 * per["call_half"] * rho * per["rolls"]
    per["comm_bps"] = per["comm"] * 2.0 * per["rolls"]
    return per


def _boot_median(v: np.ndarray, rng, draws: int):
    if len(v) < 5:
        return (None, None)
    d = [float(np.median(rng.choice(v, size=len(v), replace=True))) for _ in range(draws)]
    return (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def score() -> dict:
    pairs = pd.read_pickle(COV._out(BOOK))
    N = rl.detail()["by_domain"]["options"]
    crit = st.hlz_hurdle(N)
    rng = np.random.default_rng(SEED)

    res = {}
    for label, rho in (("quoted_spread_primary", 1.0),
                       ("rho_adjusted_EXTRAPOLATION", D.RHO_O18)):
        strata = {}
        for lo, hi in STRATA:
            sub = pairs[(pairs["dte"] >= lo) & (pairs["dte"] <= hi)]
            per = _per_name(sub, rho)
            key = "%d_%d" % (lo, hi)
            if len(per) < MIN_NAMES_PER_STRATUM:
                strata[key] = {"names": int(len(per)), "pairs": int(len(sub)),
                               "verdict": "UNDERPOWERED",
                               "why": "below the register's %d-name floor" % MIN_NAMES_PER_STRATUM}
                continue
            v = per["all_in"].values
            med = float(np.median(v))
            lo95, hi95 = _boot_median(v, rng, DRAWS)
            sd = float(np.std(v, ddof=1))
            mde80 = float((crit + 0.84) * sd / np.sqrt(len(v)))
            mde50 = float(crit * sd / np.sqrt(len(v)))
            cards = {}
            for cname, rate in CARDS.items():
                cards[cname] = {
                    "card_bps_ASSUMPTION": rate,
                    "option_minus_card_bps": med - rate,
                    "cheaper_than_card": bool(hi95 is not None and hi95 < rate),
                    "dearer_than_card": bool(lo95 is not None and lo95 > rate),
                }
            if cards["ibkr_pro"]["cheaper_than_card"]:
                verdict = "FLIPS-BOTH"
            elif cards["robinhood_gold"]["cheaper_than_card"]:
                verdict = "FLIPS-GOLD"
            else:
                verdict = "NO-FLIP"
            strata[key] = {
                "names": int(len(per)), "pairs": int(len(sub)),
                "median_all_in_bps": med, "ci95": [lo95, hi95],
                "cross_name_sd_bps": sd,
                "mde_80_power_bps": mde80, "mde_50_power_bps": mde50,
                "components_median": {
                    "financing_excess_exe_bps": float(per["fin"].median()),
                    "financing_excess_mid_bps": float(per["fin_mid"].median()),
                    "roll_bps_yr": float(per["roll_bps"].median()),
                    "commission_bps_yr": float(per["comm_bps"].median()),
                    "median_dte": float(per["dte"].median()),
                    "rolls_per_year": float(per["rolls"].median()),
                },
                "cards": cards, "verdict": verdict,
                # THE MECHANISM, banked rather than left in prose. The roll leg is expected to
                # collapse with tenor; whether the FINANCING leg improves is the open half, and
                # the MID spread is the spread-free read of it.
                "mechanism": {
                    "call_half_bps_median": float(sub["call_half_bps"].median()),
                    "call_half_dollars_median": float(
                        (sub["call_half_bps"] / 1e4 * sub["spot"]).median()),
                    "T_median": float(sub["T"].median()),
                    "note": ("if financing improved with tenor the MID excess would FALL; it is "
                             "reported beside the executable one so the reader can see which."),
                },
            }
        res[label] = strata

    # A NAMED CAUTION, MEASURED: the most liquid name is not the typical one, and a smoke test
    # on it would have read ~10x too cheap. Quantified so the caution is a number, not a worry.
    best = None
    sub_all = pairs[(pairs["dte"] >= 450) & (pairs["dte"] <= 650)]
    if len(sub_all):
        pn = _per_name(sub_all, 1.0)
        if "AAPL" in set(pn["symbol"]):
            a = float(pn.loc[pn["symbol"] == "AAPL", "all_in"].iloc[0])
            best = {"name": "AAPL", "stratum": "450_650", "all_in_bps": a,
                    "cross_name_median_bps": float(pn["all_in"].median()),
                    "percentile_of_names_cheaper": float(100.0 * (pn["all_in"] < a).mean()),
                    "note": ("the single-name smoke test read ~10x cheaper than the cross-name "
                             "median; the per-name unit exists for exactly this reason")}

    prim = res["quoted_spread_primary"]
    scoreable = [k for k, v in prim.items() if v.get("verdict") != "UNDERPOWERED"]
    verdicts = [prim[k]["verdict"] for k in scoreable]
    headline = ("UNDERPOWERED" if not scoreable else
                ("FLIPS-BOTH" if all(v == "FLIPS-BOTH" for v in verdicts) else
                 ("FLIPS-GOLD" if all(v in ("FLIPS-GOLD", "FLIPS-BOTH") for v in verdicts) else
                  ("MIXED-BY-TENOR" if len(set(verdicts)) > 1 else "NO-FLIP"))))

    payload = {
        "item": "SC-3 (TIER-E-FIN)", "pass": "arm",
        "register": "PREREG_sc3_tier_e_financing.md (ALONE and BLIND at 293a1e7)",
        "trials_booked_at": "1fd7f3d (N 308 -> 310, BEFORE this runner existed)",
        "window": list(YEARS), "tenor_band": [LONG_LO, LONG_HI],
        "strata": [list(s) for s in STRATA],
        "options_N": N, "crit": crit,
        "power_multipliers": {"p50": crit, "p80": crit + 0.84, "ratio": (crit + 0.84) / crit},
        "unit_of_independence": "NAME (register sec 3), never the pair",
        "verdict_basis": "EXECUTABLE leg (buy the call at the ask, sell the put at the bid)",
        "deepitm_fin_reference_bps": DEEPITM_ALL_IN,
        "cards_are_ASSUMPTIONS": CARDS,
        "n_pairs": int(len(pairs)), "n_names": int(pairs["symbol"].nunique()),
        "results": res, "headline_verdict": headline,
        "liquidity_caution": best,
        "binding_limitation": (
            "Tier E reaches past 200 DTE for 2016-2018 ONLY and that window is a near-zero-rf "
            "regime. DEEPITM-FIN found the option leg's own cost stable across five rate eras, "
            "but that is evidence from a DIFFERENT tenor; era-stability at long tenor is "
            "UNMEASURED and remains so."),
        "framing": ("ADOPTS NOTHING. O11 GOVERNS and a cost curve licenses no trade. R2 stands "
                    "and P1S0's closure of the options-expression family on the RETURN side is "
                    "not reopened. MB4's rf+702 re-open condition is NOT re-derived."),
    }
    with io.open(COV._out(OUT), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print()
    print("options N %d  crit %.4f   pairs %d over %d names"
          % (N, crit, len(pairs), pairs["symbol"].nunique()))
    for label, strata in res.items():
        print()
        print("== %s ==" % label)
        for k, v in strata.items():
            if v["verdict"] == "UNDERPOWERED":
                print("  %-10s UNDERPOWERED (%d names)" % (k, v["names"]))
                continue
            c = v["components_median"]
            print("  %-10s n_names %3d  all-in %8.1f bps  CI95 [%.1f, %.1f]  -> %s"
                  % (k, v["names"], v["median_all_in_bps"], v["ci95"][0], v["ci95"][1],
                     v["verdict"]))
            print("             fin %7.1f + roll %7.1f + comm %5.2f   DTE %5.0f  rolls %.2f/yr"
                  % (c["financing_excess_exe_bps"], c["roll_bps_yr"], c["commission_bps_yr"],
                     c["median_dte"], c["rolls_per_year"]))
            print("             MDE80 %.1f bps  MDE50 %.1f bps" % (v["mde_80_power_bps"],
                                                                   v["mde_50_power_bps"]))
    print()
    print("HEADLINE: %s   (DEEPITM-FIN at 60-90 DTE: rf + %.2f)" % (headline, DEEPITM_ALL_IN))
    print("wrote %s" % COV._out(OUT))
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.build:
        build()
    if a.score:
        score()
    if not (a.build or a.score):
        ap.error("pass --build or --score")


if __name__ == "__main__":
    main()
