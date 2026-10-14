"""F-4 and F-10's cheap step: does a 25-delta rule clear the crash gate on NON-DIP income?

**NO REGISTER AND NO TRIAL.** Nothing here has a hypothesis, a bar chosen for it, or an
outcome statistic: it re-runs `SELL-PREMIUM-2`'s A2 control banking the pick columns the arm
discarded, and reads `K3` -- the predecessor's own pre-committed crash arithmetic, imported,
not re-derived -- off them. `MB1-SEL`: a control can only ever BLOCK a finding.

**WHY IT IS WORTH RUNNING AT ALL.** `SELL-PREMIUM` died when `K3` fired at 8.900816 years of
premium against a 6.0 bar, because a fixed 0.90-moneyness strike surrenders most of the
income and the income is the gate's denominator. `SELL-PREMIUM-2` showed 25 delta collects
roughly twice as much on DIP days and clears at 4.6747. F-4 and F-10 are premium-selling books
that do NOT enter on dips, so the question their re-declaration turns on is whether the 25-delta
income survives on ordinary days -- and a dip day is exactly when implied volatility, and
therefore premium, is highest.

**THE CONTROL IS THE RIGHT PROXY AND IT IS NOT THEIR POPULATION.** A2 enters the same 25-delta
30-45-DTE put in the SAME names on RANDOM days, so it is non-dip income measured on the dip
book's universe. It is NOT F-4's event-free population nor F-10's published book, and the
answer here is a statement about the STRIKE RULE's income on ordinary days, never about either
book's own names. `MB8`: never borrow a number across populations without saying which.

**BOTH QUADRANTS ARE REPORTED.** The build quadrant is where the register's own A2 ran; the
check quadrant is where the crash actually happened. Reading one alone would be choosing the
window after seeing the other.

Usage:  python -m scripts.sp2_nondip_income [--draws 5]
"""
import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402
from scripts import sellpremium2_kills as K                                  # noqa: E402
from scripts import sellpremium2_arm as A2M                                  # noqa: E402


def control_picks(book: pd.DataFrame, draws: int, label: str) -> pd.DataFrame:
    """A2's control, re-run with the PICK banked rather than only its return.

    The cell structure is the arm's own -- the same (ticker, year) counts -- so this is the
    same control, differing only in what it keeps. The draw is the same seeded generator in
    the same order, so a seed reproduces the arm's own dates.
    """
    need = book.groupby(["ticker", "year"]).size().to_dict()
    rows = []
    t0 = time.time()
    for seed in list(SP.SEEDS)[:draws]:
        rng = np.random.default_rng(1000 + seed)
        n0 = len(rows)
        for (t, y), n in need.items():
            if not SP.has_chain(t, int(y)):
                continue
            raw = SP.read_raw_chain(t, int(y))
            if raw is None:
                continue
            byd = SP.index_by_date(raw)
            spot = SP.spot_by_date(t, int(y))
            grk = SP.greeks_by_key(t, int(y))
            days = sorted(spot)
            if len(days) < n:
                continue
            for d in rng.choice(days, size=n, replace=False):
                d = str(d)
                f = SP.put_funnel(None, spot, d, mon_band=None, day=byd.get(d))
                if f.get("cands") is None:
                    continue
                pk = SP.pick_put_by_delta(f["cands"], grk, d)["pick"]
                if not pk:
                    continue
                r = dict(pk)
                r.update({"ticker": t, "year": int(y), "date": d, "seed": int(seed)})
                rows.append(r)
        print("    %s seed %d: %d picks banked (%.0fs)"
              % (label, seed, len(rows) - n0, time.time() - t0))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=5)
    a = ap.parse_args()

    art = {"item": "F-4 / F-10 cheap step - 25-delta income on NON-DIP days",
           "trials": 0, "register": None,
           "what_this_is": ("SELL-PREMIUM-2's A2 control re-run with the pick banked, so the "
                            "predecessor's own K3 arithmetic can be read on NON-DIP income. "
                            "A control, so MB1-SEL charges nothing."),
           "what_this_is_not": ("F-4's event-free population and F-10's published book are "
                                "NOT measured here. This is the 25-delta STRIKE RULE's income "
                                "on ordinary days in the dip book's own universe, and it may "
                                "not be quoted as either book's own number."),
           "bar": SP.K3_MAX_YEARS_OF_PREMIUM, "stages": {}}

    for stage, bookfile, dip_picks in (
            ("build_2016_2019_half0", "SELLPREMIUM2_BOOK.pkl", "SELLPREMIUM2_PICKS25.pkl"),
            ("check_2020_2025_half1", "SELLPREMIUM2_STAGE2_BOOK.pkl",
             "SELLPREMIUM2_STAGE2_PICKS.pkl")):
        p = D.out_path(bookfile)
        if not os.path.isfile(p):
            art["stages"][stage] = {"skipped": "book absent: %s" % bookfile}
            continue
        print("\n%s" % stage)
        bk = pd.read_pickle(p)
        cp = control_picks(bk, a.draws, stage)
        if not len(cp):
            art["stages"][stage] = {"skipped": "control produced no picks"}
            continue
        D.write_pickle(cp, D.out_path("SP2_NONDIP_PICKS_%s.pkl" % stage)) \
            if hasattr(D, "write_pickle") else cp.to_pickle(
                D.out_path("SP2_NONDIP_PICKS_%s.pkl" % stage))

        k_ctl = K.k3_from_picks(cp, "non-dip control, %s" % stage)
        dp = pd.read_pickle(D.out_path(dip_picks))
        k_dip = K.k3_from_picks(dp, "dip arm, %s" % stage)
        art["stages"][stage] = {
            "n_control_picks": int(len(cp)), "n_dip_picks": int(len(dp)),
            "k3_non_dip": k_ctl, "k3_dip": k_dip,
            "income_ratio_dip_over_nondip": (
                float(k_dip["annual_income_frac_of_secured_cash"]
                      / k_ctl["annual_income_frac_of_secured_cash"])
                if k_ctl.get("annual_income_frac_of_secured_cash") else None)}
        print("  NON-DIP : income %.4f%%/yr, worst %.4f years of premium -> %s"
              % (100 * k_ctl["annual_income_frac_of_secured_cash"],
                 k_ctl["worst_years_of_premium"],
                 "CLEARS" if k_ctl["pass"] else "FIRES"))
        print("  DIP     : income %.4f%%/yr, worst %.4f years of premium -> %s"
              % (100 * k_dip["annual_income_frac_of_secured_cash"],
                 k_dip["worst_years_of_premium"],
                 "CLEARS" if k_dip["pass"] else "FIRES"))

    passes = [v["k3_non_dip"]["pass"] for v in art["stages"].values() if "k3_non_dip" in v]
    art["non_dip_clears_in_every_measured_quadrant"] = bool(passes) and all(passes)
    art["answer"] = (
        "A 25-delta 30-45 DTE cash-secured put clears SELL-PREMIUM's 6.0-year crash gate on "
        "NON-DIP income in every quadrant measured"
        if art["non_dip_clears_in_every_measured_quadrant"] else
        "A 25-delta 30-45 DTE cash-secured put does NOT clear the 6.0-year crash gate on "
        "NON-DIP income in at least one measured quadrant")
    with io.open(D.out_path("SP2_NONDIP_INCOME.json"), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\n%s" % art["answer"])
    print("wrote %s" % D.out_path("SP2_NONDIP_INCOME.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
