"""MB15 pass 2 - is the registered pre-outcome gate DISCRIMINATING?

READ-ONLY. NO ARM, NO TRIALS, NO VERDICT ABOUT ANY RETURN.

MB15's kill condition is a test OF A MAPPING: "the venue->retail mapping must reproduce the
published retail share (~60%) on the pooled cache to within +/-15pp".  The cache ships venue codes
as bare `uint8`, so the mapping is not given by the data - it would have to be chosen.  This pass
measures what choosing it buys: across ALL 2^K partitions of the observed codes into
retail/non-retail, how many land inside the band?

If a large share of arbitrary partitions clear it, the gate cannot fail against anyone free to
pick the mapping after seeing the data, so passing it is not evidence of anything.  That is a
measurement rather than an argument, which is the point - "the bar is too loose" is an opinion and
"60.43% of all partitions clear it" is not.

    python -m scripts.mb15_gate_satisfiability
"""
import io
import json
import os

import numpy as np

from scripts.mb15_venue_census import DATA

CENSUS = os.path.join(DATA, "free_analysis", "MB15_VENUE_CENSUS.json")
OUT = os.path.join(DATA, "free_analysis", "MB15_GATE_SATISFIABILITY.json")

TARGET, BAND = 0.60, 0.15
LO, HI = TARGET - BAND, TARGET + BAND


def satisfiability(shares, lo=LO, hi=HI):
    """Every subset sum and its popcount, in one pass. Returns (sums, popcounts)."""
    sums = np.zeros(1, dtype=np.float64)
    pops = np.zeros(1, dtype=np.int16)
    for s in shares:
        sums = np.concatenate([sums, sums + s])
        pops = np.concatenate([pops, pops + 1])
    return sums, pops, (sums >= lo) & (sums <= hi)


def main():
    d = json.load(io.open(CENSUS, encoding="utf-8"))
    shares = np.array(sorted(d["trade_exchange_shares"].values(), reverse=True), dtype=np.float64)
    codes = [int(k) for k in d["trade_exchange_shares"]]
    K = len(shares)
    print("K = %d venue codes, shares sum to %.10f" % (K, shares.sum()))

    sums, pops, inband = satisfiability(shares)
    n = sums.size
    assert n == 2 ** K
    n_in = int(inband.sum())
    print("subsets: %s   in band [%.2f, %.2f]: %s  (%.4f%%)"
          % ("{:,}".format(n), LO, HI, "{:,}".format(n_in), 100 * n_in / n))

    by_card = {}
    for c in range(K + 1):
        m = pops == c
        tot = int(m.sum())
        if tot:
            by_card[c] = {"subsets": tot, "in_band": int((m & inband).sum())}
            by_card[c]["share"] = by_card[c]["in_band"] / tot

    print()
    print(" |retail set|   subsets      in band     share")
    for c, v in by_card.items():
        if v["in_band"]:
            print("   %2d       %9s   %9s   %6.2f%%"
                  % (c, "{:,}".format(v["subsets"]), "{:,}".format(v["in_band"]),
                     100 * v["share"]))

    smallest = min(c for c, v in by_card.items() if v["in_band"])
    print()
    print("smallest retail set that clears the gate: %d of %d venues" % (smallest, K))

    out = {
        "item": "MB15",
        "pass": "gate-satisfiability",
        "status": "READ-ONLY MEASUREMENT - no arm, no trials, no verdict",
        "question": "over all 2^K retail/non-retail partitions of the observed venue codes, how "
                    "many reproduce the published ~60% retail share to within +/-15pp?",
        "target": TARGET, "band_pp": BAND * 100, "lo": LO, "hi": HI,
        "n_codes": K, "codes": sorted(codes),
        "n_subsets": int(n), "n_in_band": n_in, "frac_in_band": n_in / n,
        "by_cardinality": {str(k): v for k, v in by_card.items()},
        "smallest_clearing_cardinality": int(smallest),
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
