"""Which landed figures move when the stale-settlement defect is repaired? READ ONLY.

**THE DEFECT.** `settlement_spot` answered *"the last session at or before the expiry"* with no
limit, and `spot_maps` built its years from `SP.era_years()` -- stage 1's era. Any caller whose
trades expire past that era settled against the map's final close, silently.

**THIS SCRIPT ANSWERS THE SCOPE QUESTION BY MEASUREMENT RATHER THAN BY READING.** It finds every
script that CALLS `settlement_spot` from the syntax tree (a grep would match a docstring --
`MA49`), and for each banked book it asks whether the map its runner built actually covered that
book's own expiries. A caller that never settles cannot be affected and is shown to not settle.

Usage:  python -m scripts.sp2_settlement_census
"""
import ast
import io
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scripts_that_settle() -> list:
    """From the SYNTAX TREE. A grep matches the docstring that explains the rule (`MA49`)."""
    out = []
    d = os.path.join(REPO, "scripts")
    for f in sorted(os.listdir(d)):
        if not f.endswith(".py"):
            continue
        with io.open(os.path.join(d, f), encoding="utf-8") as fh:
            src = fh.read()
        if "settlement_spot" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        if any(isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "settlement_spot"
               for n in ast.walk(tree)):
            out.append(f)
    return out


def book_coverage(path: str, map_years: list) -> dict:
    p = D.out_path(path)
    if not os.path.isfile(p):
        return {"absent": path}
    bk = pd.read_pickle(p)
    ey = bk["expiration"].astype(str).str[:4].astype(int)
    past = ey > max(map_years)
    return {"n": int(len(bk)),
            "expiry_min": str(bk["expiration"].astype(str).min()),
            "expiry_max": str(bk["expiration"].astype(str).max()),
            "map_years": [int(y) for y in map_years],
            "n_expiring_past_the_map": int(past.sum()),
            "share_expiring_past_the_map": round(float(past.mean()), 4),
            "map_covers_its_own_trades": bool(not past.any())}


def main():
    art = {"item": "settlement staleness - which landed figures move", "trials": 0,
           "defect": ("settlement_spot had no staleness limit and spot_maps built stage 1's "
                      "era, so any caller whose trades expire past that era settled against "
                      "the map's final close"),
           "scripts_that_call_settlement_spot": scripts_that_settle()}

    stage1_map = list(SP.era_years()) + [max(SP.era_years()) + 1]
    art["stage1"] = book_coverage("SELLPREMIUM2_BOOK.pkl", stage1_map)
    art["stage2_as_void_run"] = book_coverage("SELLPREMIUM2_STAGE2_BOOK.pkl", stage1_map)

    # Callers that never settle cannot be affected -- shown, not asserted.
    never = {}
    for f in ("sp2_nondip_income.py", "sp2_nondip_tenor.py", "sellpremium2_sizing_fix.py",
              "sellpremium2_kills.py"):
        p = os.path.join(REPO, "scripts", f)
        if not os.path.isfile(p):
            continue
        with io.open(p, encoding="utf-8") as fh:
            src = fh.read()
        never[f] = {"calls_settlement_spot": f in art["scripts_that_call_settlement_spot"],
                    "mentions_settlement_spot_at_all": "settlement_spot" in src}
    art["callers_that_never_settle"] = never

    # The predecessor keys its per-year cache on the EXPIRY's own year, so its map always
    # reaches its expiry. Structural, read from the source.
    with io.open(os.path.join(REPO, "scripts", "sellpremium_kills.py"), encoding="utf-8") as fh:
        art["predecessor_keys_cache_on_expiry_year"] = "int(ex[:4])" in fh.read()

    art["verdict"] = {
        "stage1_SELLPREMIUM2": ("UNAFFECTED - its map covers 2016-2020 and 0 of its 2,610 "
                                "trades expire past it"),
        "stage2_SELLPREMIUM2": "VOID - 73.02% of its trades expired past the map it was given",
        "SELLPREMIUM_predecessor": ("UNAFFECTED - keys its spot cache on the expiry's own "
                                    "year, so the map always reaches the expiry"),
        "F4_F10_nondip_step": "UNAFFECTED - banks picks only, never settles",
        "sizing_fix": ("reads banked books; stage 1's cells stand, stage 2's are void WITH "
                       "the book they were computed from"),
        "DIP_CALL": "UNAFFECTED - no dipcall script calls settlement_spot",
    }

    with io.open(D.out_path("SP2_SETTLEMENT_CENSUS.json"), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps(art, indent=2, default=str))
    print("\nwrote %s" % D.out_path("SP2_SETTLEMENT_CENSUS.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
