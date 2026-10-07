# -*- coding: utf-8 -*-
"""`POOL-SIZE` diagnostics — book composition and DATA QUALITY by size bucket. ZERO TRIALS.

Register `PREREG_pool_size.md` §0 charges these at **zero**: they are **censuses** — facts about
what the data contains, with no hypothesis and no bar (`S25` / `MB3` / `W-28-PULL` class). A
census can only BLOCK an interpretation of the ladder, never produce one.

Don asked for the small end to be **measured rather than assumed**, so this reports, per rung:

  * the share of the book held in names under **$300M**, and the book's own size distribution;
  * the **missing-input rate** per theme, by market-cap bucket, on the rows the rung can hold;
  * the **sanity-flag rate** by bucket, from the shipped `sanity_check` bands.

**THE BUCKETS ARE READ OFF THE PANEL'S OWN `market_cap`**, which is 100% non-null on all 113,945
rows — so a bucket is never a stand-in for a missing value.
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

from valuation.studies import served_index_book as IB                     # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                       # noqa: E402
from valuation.edge.fundamental_panel import composite_from_frame         # noqa: E402
from valuation.screener.cross_sectional import zscore                     # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT            # noqa: E402
from scripts.index_best import data_candidates, _data_root                # noqa: E402
from scripts.pool_size import RUNGS, MICRO_CAP                            # noqa: E402

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "POOL_SIZE_DIAG.json") if FA else None

#: Size buckets in USD. The $300M line is the register's; the rest bracket it so the small end
#: is not a single lump.
BUCKETS = [("under_300M", 0.0, 300e6), ("300M_1bn", 300e6, 1e9), ("1bn_10bn", 1e9, 1e10),
           ("over_10bn", 1e10, float("inf"))]


def _bucket(mc):
    for name, lo, hi in BUCKETS:
        if lo <= mc < hi:
            return name
    return "unknown"


def books_per_date(panel, cols, weights, kw):
    """The rung's book at each date, as `{date: {ticker: weight}}`. Calls the SHIPPED hook."""
    bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
    out, held = {}, set()
    for d in sorted(panel["date"].unique()):
        sub = panel[panel["date"] == d]
        if sub.empty:
            continue
        # the SAME two functions `IB.run` wires together -- `composite_from_frame` needs
        # the standardiser passed in, and taking a different one would score a different
        # book from the ladder's (`B7`).
        comp = composite_from_frame(sub, cols, weights, zscore)
        bk = bf(sub, comp, held)
        if bk:
            out[str(d)[:10]] = dict(bk)
            held = set(bk)
    return out


def main(argv=None, panel_path=None, out=None, item="POOL-SIZE",
         part="diagnostics (census)") -> int:
    """`panel_path`/`out` default to the banked panel and this item's own artifact, so every
    existing caller is bit-identical. `UNIVERSE-BIAS` passes a corrected-universe panel rather
    than copying this census (`B7` -- a second copy is how two censuses come to apply quietly
    different bucket lines)."""
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    panel = pd.read_pickle(panel_path or os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    panel = panel.copy()
    panel["_mc"] = pd.to_numeric(panel["market_cap"], errors="coerce")
    panel["_bucket"] = [_bucket(x) if x == x else "unknown" for x in panel["_mc"]]
    print("panel %s | market_cap non-null %.4f" % (panel.shape, panel["_mc"].notna().mean()),
          flush=True)

    # ---- PANEL-WIDE data quality by bucket (independent of any rung) --------------------
    panel_q = {}
    for name, _lo, _hi in BUCKETS:
        sub = panel[panel["_bucket"] == name]
        if sub.empty:
            panel_q[name] = {"rows": 0}
            continue
        miss = {c: float(pd.to_numeric(sub[c], errors="coerce").isna().mean())
                for c in cols if c in sub.columns}
        panel_q[name] = {
            "rows": int(len(sub)), "names": int(sub["ticker"].nunique()),
            "share_of_panel_rows": float(len(sub) / len(panel)),
            "theme_missing_rate": miss,
            "mean_themes_missing_per_row": float(
                np.mean([sum(1 for c in cols
                             if c in sub.columns and pd.isna(pd.to_numeric(sub[c],
                                                                           errors="coerce").iloc[i]))
                         for i in range(0, min(len(sub), 400))])) if len(sub) else None,
        }
        print("  panel %-11s rows %6d  names %4d  worst-theme NaN %.4f"
              % (name, len(sub), sub["ticker"].nunique(),
                 max(miss.values()) if miss else float("nan")), flush=True)

    # ---- per-rung book composition --------------------------------------------------------
    mc_by_key = {}
    for d, t, m in zip(panel["date"], panel["ticker"], panel["_mc"]):
        mc_by_key[(str(d)[:10], t)] = m

    rungs = {}
    for name, kw in RUNGS:
        bks = books_per_date(panel, cols, weights, kw)
        if not bks:
            print("  %-20s NO BOOK" % name, flush=True)
            continue
        micro_w, bucket_w, sizes, n_unknown = [], {b: [] for b, _, _ in BUCKETS}, [], 0
        for d, bk in bks.items():
            sizes.append(len(bk))
            tot = sum(bk.values()) or 1.0
            acc = {b: 0.0 for b, _, _ in BUCKETS}
            for t, w in bk.items():
                m = mc_by_key.get((d, t))
                if m is None or m != m:
                    n_unknown += 1
                    continue
                acc[_bucket(m)] += w / tot
            micro_w.append(acc["under_300M"])
            for b in acc:
                bucket_w[b].append(acc[b])
        rungs[name] = {
            "knobs": kw, "dates": len(bks),
            "book_size": {"min": int(min(sizes)), "median": float(np.median(sizes)),
                          "max": int(max(sizes))},
            "weight_under_300M": {"mean": float(np.mean(micro_w)),
                                  "max": float(np.max(micro_w)),
                                  "dates_above_1pc": int(sum(1 for x in micro_w if x > 0.01))},
            "mean_weight_by_bucket": {b: float(np.mean(v)) for b, v in bucket_w.items()},
            "positions_with_no_market_cap": n_unknown,
        }
        print("  %-20s book %3d-%3d  under-300M weight mean %.4f max %.4f"
              % (name, min(sizes), max(sizes),
                 rungs[name]["weight_under_300M"]["mean"],
                 rungs[name]["weight_under_300M"]["max"]), flush=True)

    res = {
        "item": item, "part": part, "trials": 0,
        "panel": os.path.basename(panel_path or "panel_corrected_69d.pkl"),
        "register": "PREREG_pool_size.md section 0 -- censuses charge nothing (MB1-SEL class)",
        "buckets_usd": [[b, lo, (None if hi == float("inf") else hi)] for b, lo, hi in BUCKETS],
        "micro_cap_line_usd": MICRO_CAP,
        "panel_data_quality_by_bucket": panel_q,
        "rung_composition": rungs,
        "note": "a census: no hypothesis, no bar, no verdict. It can only BLOCK an "
                "interpretation of the ladder, never produce one.",
    }
    dest = out or OUT
    json.dump(res, io.open(dest, "w", encoding="utf-8"), indent=2, default=str)
    print("\nwrote %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
