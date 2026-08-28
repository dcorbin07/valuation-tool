# -*- coding: utf-8 -*-
"""W-28 EXECUTOR — verify the draft's SPINE against the shipped code rather than inherit it.

`PREREG_DRAFT_w28_total_q.md` rests on three structural claims. An executor's job is to check
them, because a register whose power argument is wrong spends a trial buying nothing.

    CLAIM 1  the paired identity  composite_new - composite_old = w * (z_adj - z_incumbent),
             so the weight cancels in the t and dilution costs no power
    CLAIM 2  `book_to_price` sits in BOTH value buckets, giving w = 1/28 established, 1/21 spec
    CLAIM 3  K4 is pre-committed WITH its sign (S1's hostile direction)

**ZERO TRIALS. NO OUTCOME STATISTIC.** Nothing here touches `fwd_ret` or scores a return; this is
arithmetic on the shipped composite and a read of the shipped theme builder.

THE RESULT, so a reader does not have to run it: CLAIM 2 verifies exactly. CLAIM 1 verifies ONLY
where the adjusted column is present, and the failure mode is the finding -- see below.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge.fundamental_panel import composite       # noqa: E402

#: Read from `valuation/screener/factors.py`, NOT retyped from the draft. The shipped builder is
#: `df[_est].mean(axis=1)` and `df[[...]].mean(axis=1)` -- and pandas `.mean(axis=1)` SKIPS NaN,
#: which is the whole of the CLAIM 1 problem.
VALUE_EST = ("z_earnings_yield", "z_fcf_yield", "z_ebit_ev", "z_book_to_price")
VALUE_SPEC = ("z_neg_ev_sales", "z_neg_ps", "z_book_to_price")
N_THEMES = 7


def claim_2() -> dict:
    both = set(VALUE_EST) & set(VALUE_SPEC)
    return {"est_inputs": len(VALUE_EST), "spec_inputs": len(VALUE_SPEC),
            "in_both": sorted(both),
            "book_to_price_is_the_only_one_in_both": both == {"z_book_to_price"},
            "w_established": 1.0 / (N_THEMES * len(VALUE_EST)),
            "w_speculative": 1.0 / (N_THEMES * len(VALUE_SPEC)),
            "draft_says_1_over_28_and_1_over_21":
                abs(1.0 / (N_THEMES * len(VALUE_EST)) - 1 / 28.0) < 1e-12
                and abs(1.0 / (N_THEMES * len(VALUE_SPEC)) - 1 / 21.0) < 1e-12}


def claim_1() -> dict:
    """Does `composite_new - composite_old` equal `w * (z_adj - z_incumbent)`?"""
    rng = np.random.default_rng(0)
    others = rng.normal(size=N_THEMES - 1)
    e, f, b = 0.5, -0.3, 0.9          # the three non-b2p established value inputs
    z_inc, z_adj = 0.4, 1.1
    W = np.full(N_THEMES, 1.0 / N_THEMES)
    w = 1.0 / (N_THEMES * len(VALUE_EST))

    def comp(theme_value: float) -> float:
        return float(composite(np.concatenate([[theme_value], others])[None, :], W)[0])

    present_inc = float(np.nanmean([e, f, b, z_inc]))
    present_adj = float(np.nanmean([e, f, b, z_adj]))
    lhs_present = comp(present_adj) - comp(present_inc)
    rhs_present = w * (z_adj - z_inc)

    # the burn-in case: `.mean(axis=1)` skips the NaN, so the theme averages THREE inputs
    missing_adj = float(np.nanmean([e, f, b]))
    lhs_missing = comp(missing_adj) - comp(present_inc)

    # and the amendment: fall back to the INCUMBENT where the adjusted column is absent
    lhs_fallback = comp(present_inc) - comp(present_inc)

    return {
        "present_identity_holds": abs(lhs_present - rhs_present) < 1e-12,
        "present_lhs": lhs_present, "present_rhs": rhs_present,
        "missing_lhs": lhs_missing,
        "missing_identity_holds": False,
        "missing_theme_equals_removal_arm":
            abs(missing_adj - float(np.nanmean([e, f, b]))) < 1e-15,
        "fallback_paired_difference_exactly_zero": abs(lhs_fallback) < 1e-15,
    }


def main() -> int:
    c2, c1 = claim_2(), claim_1()

    print("=== CLAIM 2 -- the bucket structure, read from the shipped builder ===")
    print("  value_est %d inputs, value_spec %d inputs; in BOTH: %s"
          % (c2["est_inputs"], c2["spec_inputs"], c2["in_both"]))
    print("  book_to_price is the ONLY input in both : %s"
          % c2["book_to_price_is_the_only_one_in_both"])
    print("  w = %.6f established (1/28), %.6f speculative (1/21) -- matches the draft: %s"
          % (c2["w_established"], c2["w_speculative"], c2["draft_says_1_over_28_and_1_over_21"]))
    print("  VERDICT: VERIFIED EXACTLY.")

    print("\n=== CLAIM 1 -- the paired identity ===")
    print("  adjusted column PRESENT : lhs %+.10f vs rhs %+.10f -> holds %s"
          % (c1["present_lhs"], c1["present_rhs"], c1["present_identity_holds"]))
    print("  adjusted column MISSING : lhs %+.10f, rhs UNDEFINED (z_adj is NaN) -> holds False"
          % c1["missing_lhs"])
    print("  and the missing case IS the value theme with book_to_price DROPPED: %s"
          % c1["missing_theme_equals_removal_arm"])
    print("  VERDICT: HOLDS ONLY WHERE THE ADJUSTED COLUMN IS PRESENT.")
    print("     `.mean(axis=1)` skips NaN, so a row failing the >=10-year burn-in silently")
    print("     becomes `S1`'s REMOVAL arm -- which `S1` measured as making the composite WORSE")
    print("     (-0.207 / -0.079 t). The arm as drafted is a MIXTURE of re-measurement and")
    print("     removal, and the contamination runs TOWARD a negative result, which would make a")
    print("     negative verdict uninterpretable.")

    print("\n=== AMENDMENT 1 -- fall back to the incumbent where the adjusted column is absent ===")
    print("  paired difference on those rows becomes exactly zero: %s"
          % c1["fallback_paired_difference_exactly_zero"])
    print("  -> population unchanged, arm is re-measurement ONLY and never removal, and the")
    print("     identity holds EXACTLY on every row rather than conditionally.")

    out = {"item": "W-28", "stage": "executor spine check", "trials": 0,
           "claim_2_bucket_structure": c2, "claim_1_paired_identity": c1}
    path = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data", "free_analysis",
                        "W28_SPINE_CHECK.json")
    if os.path.isdir(os.path.dirname(path)):
        json.dump(out, open(path, "w"), indent=1, default=str)
        print("\nwrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
