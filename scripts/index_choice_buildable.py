# -*- coding: utf-8 -*-
"""INDEX-CHOICE item 2 -- can a 25-name book be BUILT on 2026-10-22? ZERO TRIALS.

A CONTROL in the strict `MB1-SEL` sense: it can only BLOCK an arm from being servable, never
produce a finding. Its DECILE leg is additionally a REPRODUCTION of a figure `D9` has already
published, which is the control that proves this instrument is `D9`'s rather than a lookalike.

THE QUESTION IS FEASIBILITY, NOT PERFORMANCE. A top-25 book selects the top ~1.7% of a
1,500-name universe against the top 10% for arm 2, so a given per-name ranking error moves a far
larger share of the book. `D9` measured the free route's decile overlap with the Sharadar
composite at 0.2326 against its own pre-committed 0.60 bar and returned NO-GO; what has never
been measured is the overlap at a TOP-25 cut, which is arm 3's actual book.

THE HARD LIMIT, STATED BEFORE MEASURING: the live snapshot persists only 500 rows, so arm 2's
1,500-name universe CANNOT be reconstructed from the `D9` artifacts at all. What is measurable
is the overlap of the TOP-N books on `D9`'s own 431-name shared population. A top-25 of 431 is
the top 5.8% -- close in selectivity to arm 3's 1.7% of 1,500 and NOT identical, and every
figure is labelled accordingly.

`D9`'s 0.60 bar is REUSED VERBATIM, never re-chosen after seeing the number (`W-28`).
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

from scripts.index_best import data_candidates, _data_root                # noqa: E402

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "INDEX_CHOICE_BUILDABLE.json") if FA else None

READING = "freeze_2026-07-31"          # D9's own PRIMARY reading, named in D9_FIDELITY.json
D9_BAR = 0.60                          # D9's pre-committed overlap bar, reused verbatim
D9_PUBLISHED_DECILE_OVERLAP = 0.23255813953488372     # D9_FIDELITY readings.B2_decile_overlap
D9_PUBLISHED_LL_SPEARMAN = 0.43211493611995416        # ... B1_like_for_like_composite_spearman
D9_PUBLISHED_OVERLAP_N = 431
ARM3_BOOK = 25                         # arm 3's book size, from INDEX-BEST


def _overlap(a_rank, b_rank, k):
    """Share of the top-k that the two rankings agree on. Symmetric, and the denominator is k
    rather than the union, which is `D9`'s own convention."""
    A = set(a_rank[:k])
    B = set(b_rank[:k])
    return len(A & B) / float(k)


def main() -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    rows = pd.read_pickle(os.path.join(FA, "D9_FIDELITY_ROWS_%s.pkl" % READING))
    sh, lv, ov = rows["sharadar"], rows["live"], list(rows["overlap"])
    print("D9 reading %s | sharadar %d | live %d | overlap %d"
          % (READING, len(sh), len(lv), len(ov)), flush=True)

    s = sh.loc[[t for t in ov if t in sh.index], "ll_composite"].dropna()
    l = lv.loc[[t for t in ov if t in lv.index], "ll_composite"].dropna()
    common = sorted(set(s.index) & set(l.index))
    s, l = s.loc[common], l.loc[common]
    n = len(common)
    sr = list(s.sort_values(ascending=False).index)
    lr = list(l.sort_values(ascending=False).index)

    res = {"item": "INDEX-CHOICE", "part": "2 live buildability", "trials": 0,
           "class": "CONTROL -- can only BLOCK an arm from being servable (MB1-SEL); the decile "
                    "leg is additionally a REPRODUCTION of a published D9 figure",
           "reading": READING, "bar": D9_BAR, "bar_source": "D9, reused verbatim (W-28)",
           "shared_population": n,
           "limit": "the live snapshot persists only 500 rows, so arm 2's 1,500-name universe "
                    "cannot be reconstructed from the D9 artifacts AT ALL; these are TOP-N "
                    "overlaps on the 431-name shared population",
           }

    # ---- CONTROL: reproduce D9's own published decile figure on this instrument -------------
    k_dec = max(1, int(round(n * 0.10)))
    dec = _overlap(sr, lr, k_dec)
    spear = float(s.rank().corr(l.rank()))
    res["control_vs_D9"] = {
        "decile_k": k_dec,
        "decile_overlap_reproduced": dec,
        "decile_overlap_published": D9_PUBLISHED_DECILE_OVERLAP,
        "abs_dev": abs(dec - D9_PUBLISHED_DECILE_OVERLAP),
        "ll_spearman_reproduced": spear,
        "ll_spearman_published": D9_PUBLISHED_LL_SPEARMAN,
        "spearman_abs_dev": abs(spear - D9_PUBLISHED_LL_SPEARMAN),
        "overlap_n_published": D9_PUBLISHED_OVERLAP_N,
        "pass": bool(abs(dec - D9_PUBLISHED_DECILE_OVERLAP) < 1e-12
                     and abs(spear - D9_PUBLISHED_LL_SPEARMAN) < 1e-9),
    }
    print("CONTROL decile k=%d overlap %.6f vs D9's published %.6f (dev %.3e) | ll Spearman "
          "%.6f vs %.6f (dev %.3e) -> %s"
          % (k_dec, dec, D9_PUBLISHED_DECILE_OVERLAP, res["control_vs_D9"]["abs_dev"],
             spear, D9_PUBLISHED_LL_SPEARMAN, res["control_vs_D9"]["spearman_abs_dev"],
             "PASS" if res["control_vs_D9"]["pass"] else "DOES NOT REPRODUCE"), flush=True)

    # ---- THE NEW NUMBER: the top-25 overlap, which is arm 3's book -------------------------
    res["top_n_overlap"] = {}
    for k in (10, ARM3_BOOK, 50, k_dec):
        res["top_n_overlap"][str(k)] = {
            "k": k, "overlap": _overlap(sr, lr, k),
            "selectivity_of_shared_population": k / float(n),
            "clears_D9_bar": bool(_overlap(sr, lr, k) >= D9_BAR),
        }
    for k in sorted(res["top_n_overlap"], key=lambda x: int(x)):
        d = res["top_n_overlap"][k]
        print("  top-%-3s overlap %.4f  (top %.2f%% of the shared population) -> %s"
              % (k, d["overlap"], 100 * d["selectivity_of_shared_population"],
                 "CLEARS" if d["clears_D9_bar"] else "FAILS D9's 0.60 bar"), flush=True)

    a3 = res["top_n_overlap"][str(ARM3_BOOK)]["overlap"]
    res["verdict"] = {
        "arm3_top25_overlap": a3,
        "arm3_buildable_by_path_A": bool(a3 >= D9_BAR),
        "arm2_decile_overlap": dec,
        "arm2_buildable_by_path_A": bool(dec >= D9_BAR),
        "path_A": "the free route as it stands on D9's reading",
        "path_B": "renewed Sharadar, which Don plans for ~2026-10-12",
        "note": ("NEITHER book clears D9's own bar on the free route, so on this evidence "
                 "2026-10-22 needs Path B. The theme job's first run is 2026-10-04, so the two "
                 "themes contributing zero MAY improve before then -- that is a FORWARD fact "
                 "this control cannot measure and it is recorded as a condition, not assumed."
                 if not (a3 >= D9_BAR and dec >= D9_BAR) else
                 "both clear; Path A is viable on this evidence"),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\narm 3 (top 25) buildable by Path A: %s | arm 2 (decile): %s"
          % (res["verdict"]["arm3_buildable_by_path_A"],
             res["verdict"]["arm2_buildable_by_path_A"]))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
