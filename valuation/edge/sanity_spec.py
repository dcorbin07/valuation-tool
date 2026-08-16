"""The plausibility bands the sanity layer judges factor VALUES against — one definition.

WHY THIS MODULE EXISTS (audit MA14, using MA39's shipped pattern). The bands lived in
`fundamental_panel.py`, which is 5,000 lines and pulls in the whole engine. The LIVE scoring
path (`valuation/screener/screen.py`) runs per request and cannot afford that import, so a
live sanity check had exactly two options: import the engine, or grow a second copy of the
bands. MA39 measured what the second option costs — `RESULT_BLOCKS` was duplicated for the
same reason, the two copies drifted, and a later change added `benchmarks` to only one of
them, leaving seven payload blocks unwatched.

So this module holds the numbers and DEPENDS ON NOTHING (stdlib only, no pandas, no numpy).
`fundamental_panel` re-exports every name, so every existing importer is untouched, and
`tests/test_ma14_live_sanity.py` pins that exactly one literal assignment of each exists in
the tree.

THE BANDS ARE NOT A GUESS AND ARE NOT RE-TUNED HERE. They were calibrated against the
known-broken (pre-P7) and known-good (post-P7) values on the same rows. Moving them into
their own file changes no number; a test asserts the values are identical to what
`fundamental_panel` shipped.
"""
from __future__ import annotations

# Plausible cross-sectional bounds for each ratio factor. Generous on purpose: the job is to
# catch a 1,500x error, not to police a fat tail. A quarterly earnings yield of 5 means the
# company earned five times its market cap in three months. This is the band that would have
# caught P7 on its first run — SK Telecom's `book_to_price` computed to 892 against a true
# 0.589, because `marketcap` is USD and the raw line items are in the reporting currency.
SANE_RANGES = {
    "book_to_price": (-50.0, 50.0),
    "earnings_yield": (-10.0, 10.0),   # quarterly earnings / market cap
    "fcf_yield": (-10.0, 10.0),
    "ebit_ev": (-25.0, 25.0),
}

# Ratios measured but intentionally exempt from the range check: they legitimately take a very
# wide range, so a band would either be useless or fire constantly. AUDIT B18 added the SIGN
# check for exactly this reason — the one place a band cannot look is the one place a sign
# error could hide.
SANE_RANGE_EXEMPT = ("ev_sales", "ev_ebitda", "ps")

# >1% of rows outside the band = systematic, not a fat tail.
SANE_VIOLATION_SHARE = 0.01

# A subgroup whose MEDIAN percentile sits this high/low is pegged. 0.70 verified against the
# pre-P7 values: it catches 4 of the 6 corrupted value ratios (book_to_price and
# earnings_yield reached 0.86 alone) with ZERO false positives on the corrected data, where
# every factor lands in 0.49-0.61. A detector threshold tuned on known-bad vs known-good data
# — it affects no return and no weight, so it is not the kind of after-the-fact tuning
# `holdout_theme_validate` exists to prevent.
SUBGROUP_PEG_PCTILE = 0.70

MC_DIVERGENCE_FACTOR = 3.0         # DAILY market cap vs shares x price
MC_DIVERGENCE_SHARE = 0.01

__all__ = ["SANE_RANGES", "SANE_RANGE_EXEMPT", "SANE_VIOLATION_SHARE",
           "SUBGROUP_PEG_PCTILE", "MC_DIVERGENCE_FACTOR", "MC_DIVERGENCE_SHARE"]
