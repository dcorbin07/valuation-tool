"""Each book's OWN declared tenor, on the banked non-dip picks. No register, no trial.

**WHY THIS ADDENDUM EXISTS, AND IT IS AN `MB8` CORRECTION TO MY OWN FIRST ANSWER.**
`sp2_nondip_income.py` measured the 25-delta rule at `SELL-PREMIUM-2`'s own **20-60 DTE** band,
median 37. **F-4 declares `dte` 30 and F-10 declares 52**, and `K3`'s income is
`premium_fraction x turns`, with `turns = 252 / dte` -- so the tenor is not a detail, it is half
the denominator. Reporting a 37-DTE figure as F-10's answer would be borrowing a number across
constructions, which is the exact error the retirement memo already warns about one level up.

**IT IS FREE: the picks are already banked**, so each book's tenor is a subset of rows rather
than a new pull. `K3` is `sellpremium2_kills.k3_from_picks`, IMPORTED (`B7`).

**AND THE PREMIUM FRACTION IS RE-MEASURED AT THE TENOR RATHER THAN RESCALED.** The obvious
shortcut -- keep the 37-DTE premium and change only `turns` -- is wrong in the flattering
direction for F-4 and the harsh direction for F-10: a longer-dated put collects MORE premium,
so holding the fraction fixed while raising `turns` invents income. Each band is measured on
its own rows.

Usage:  python -m scripts.sp2_nondip_tenor
"""
import io
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402
from scripts import sellpremium2_kills as K                                  # noqa: E402

#: Read from each declaration, never retyped -- a constant here is how a bar freezes (`MA5`).
BOOKS = ("f4_eventfree_premium", "f10_clean_csp")
#: +/- this many days around the declared tenor. Wide enough to hold a real expiry ladder and
#: narrow enough that the band is the book's and not SELL-PREMIUM-2's.
HALF_WIDTH = 7
#: Below this many picks a median is not a measurement. `MB3`'s separation of reasons applies:
#: "too few rows at this tenor" is not "the gate fired".
MIN_PICKS = 200


def declared_dte(book):
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "DECL_%s.md" % book)
    from valuation.edge import fleet as F
    with io.open(p, encoding="utf-8") as fh:
        d = F.parse_declaration(fh.read())["declaration"]
    return int((d.get("structure") or {}).get("dte"))


def main():
    art = {"item": "F-4 / F-10 at their OWN declared tenor, on the banked non-dip picks",
           "trials": 0, "register": None, "bar": SP.K3_MAX_YEARS_OF_PREMIUM,
           "half_width_days": HALF_WIDTH, "min_picks": MIN_PICKS,
           "caveat": ("the population is SELL-PREMIUM-2's universe entered on RANDOM days, "
                      "which is the best available non-dip proxy and is NOT F-4's event-free "
                      "set nor F-10's published book"),
           "stages": {}}
    for book in BOOKS:
        art.setdefault("declared_dte", {})[book] = declared_dte(book)

    for stage in ("build_2016_2019_half0", "check_2020_2025_half1"):
        p = D.out_path("SP2_NONDIP_PICKS_%s.pkl" % stage)
        if not os.path.isfile(p):
            art["stages"][stage] = {"skipped": "picks absent"}
            continue
        cp = pd.read_pickle(p)
        row = {"n_all": int(len(cp)),
               "all_tenors": K.k3_from_picks(cp, "non-dip, all tenors, %s" % stage)}
        print("\n%s  (%d non-dip picks)" % (stage, len(cp)))
        print("  all tenors (median %d DTE): income %.4f%%/yr, worst %.4f yrs -> %s"
              % (row["all_tenors"]["median_dte"],
                 100 * row["all_tenors"]["annual_income_frac_of_secured_cash"],
                 row["all_tenors"]["worst_years_of_premium"],
                 "CLEARS" if row["all_tenors"]["pass"] else "FIRES"))
        for book in BOOKS:
            dte = art["declared_dte"][book]
            sub = cp[(cp["dte"] >= dte - HALF_WIDTH) & (cp["dte"] <= dte + HALF_WIDTH)]
            if len(sub) < MIN_PICKS:
                row[book] = {"n": int(len(sub)), "declared_dte": dte,
                             "verdict": "TOO FEW PICKS AT THIS TENOR - not a measurement, "
                                        "and NOT a fired gate"}
                print("  %-22s dte %2d +/-%d: only %d picks - NOT MEASURED"
                      % (book, dte, HALF_WIDTH, len(sub)))
                continue
            k = K.k3_from_picks(sub, "%s at its own %d DTE, %s" % (book, dte, stage))
            row[book] = {"n": int(len(sub)), "declared_dte": dte, "k3": k}
            print("  %-22s dte %2d +/-%d, n %4d: income %.4f%%/yr, worst %.4f yrs -> %s"
                  % (book, dte, HALF_WIDTH, len(sub),
                     100 * k["annual_income_frac_of_secured_cash"],
                     k["worst_years_of_premium"], "CLEARS" if k["pass"] else "FIRES"))
        art["stages"][stage] = row

    verdicts = {}
    for book in BOOKS:
        cells = [v[book]["k3"]["pass"] for v in art["stages"].values()
                 if isinstance(v, dict) and isinstance(v.get(book), dict)
                 and "k3" in v[book]]
        verdicts[book] = {"measured_quadrants": len(cells),
                          "clears_everywhere": bool(cells) and all(cells)}
    art["verdicts"] = verdicts
    with io.open(D.out_path("SP2_NONDIP_TENOR.json"), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\n%s" % json.dumps(verdicts))
    print("wrote %s" % D.out_path("SP2_NONDIP_TENOR.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
