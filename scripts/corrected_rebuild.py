# -*- coding: utf-8 -*-
"""`CORRECTED-REBUILD` -- ONE rebuild of the corrected full-universe panel, serving every
successor item.

    python -m scripts.corrected_rebuild

**ZERO TRIALS.** A panel build is not a search: no hypothesis, no bar, no arm, no outcome
statistic. `S25` / `X7RECON` / `PANEL-EXT-RECHECK` class.

**EXACTLY THREE THINGS DIFFER FROM `UNIVERSE-BIAS`'s BUILD, AND THEY ARE DECLARED HERE RATHER
THAN DISCOVERED LATER.**

1. `keep_numbers=True` -- so the `z_*` columns persist. `UNIVERSE-BIAS` built lean (16 columns
   against the banked panel's 75) and `CORRECTED-FLOORS` part 2 then had to report FOUR claims
   `UNMEASURED` for want of them.
2. `extra_horizons` 126 to 504 days -- what `S22`'s grid needs. The lean panel carried `fwd_ret`
   (63d) ALONE.
3. `ncfdiv` and `ncfcommon` in `_KEEP` -- batch 2's `B5`. Coverage was MEASURED on the export
   before the allowlist was touched (the COVERAGE RULE); see `data_providers._KEEP`.

**EVERYTHING ELSE IS BIT-FOR-BIT `UNIVERSE-BIAS`'s INVOCATION**, read from `CONFIG` rather than
retyped, and the same full-universe export and full-universe bulk cache. One build, so every
successor reads ONE object and no two items can quietly describe different panels.

**THE LIVE-THEME GATE RUNS BEFORE ANYTHING READS IT.** `UNIVERSE-BIAS` shipped a SIX-theme
confounded panel whose `insider` was constant at one distinct value at 100% non-null, and its
runner reported "themes 7" because it counted columns PRESENT. **Coverage is not fidelity.** So
this refuses to write unless all seven weighted themes are LIVE -- present, non-constant, and
with non-zero dispersion.

**THE BANKED PANELS ARE NOT OVERWRITTEN.** It writes `UNIVERSE_BIAS_PANEL_full_v2.pkl`, and
`panel_corrected_69d.pkl` / `UNIVERSE_BIAS_PANEL_full.pkl` are never opened for writing -- pinned
by test.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: `S22`'s grid, in trading days -- its OWN `HORIZONS` tuple, INCLUDING the base 63, pinned
#: against the import by test rather than retyped.
#:
#: **A DEFECT OF MY OWN, AND 63 IS NOT A DUPLICATE COLUMN.** v2 shipped this as `HORIZONS[1:]`
#: on the reasoning that 63 is the panel's own `horizon` and repeating it buys nothing. It buys
#: `S22`'s `C0` control: `fundamental_panel`'s own comment reads *"the BASE horizon is allowed
#: here and is the study's C0 control: `fwd_ret_h63` must equal `fwd_ret` exactly"*, and
#: `term_structure.main` reads `fwd_ret_h63` directly to check that the `extra_horizons`
#: machinery reproduces the shipped column. Dropping it made that control `KeyError` -- so the
#: arms were all fine (`ret_col(63)` returns `fwd_ret`) and the CONTROL was the casualty.
#: **A column that looks like a duplicate can BE a control**, and copying `fwd_ret` into
#: `fwd_ret_h63` instead would have made `C0` pass BY CONSTRUCTION, which is worse than the
#: KeyError: a vacuous control reads as a passing one.
EXTRA_HORIZONS = (63, 126, 189, 252, 315, 378, 441, 504)

OUT_PANEL = "UNIVERSE_BIAS_PANEL_full_v3.pkl"
OUT_JSON = "CORRECTED_REBUILD.json"

#: a theme with fewer than this many distinct values is DEAD, not thin -- `zscore` returns
#: all-NaN on a constant column and `composite` renormalises it away, so the book silently
#: scores one theme fewer. IMPORTED from UNIVERSE-BIAS rather than re-chosen (`B7`).
from scripts.universe_bias_arms import MIN_DISTINCT_PER_THEME, live_themes   # noqa: E402


def fa():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis")


def paths():
    from scripts.index_best import _data_root
    data = _data_root()
    return (os.path.join(data, "full2009", "backtest"),
            os.path.join(data, "bulk", "prepared"))


def main(argv=None):
    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel
    from valuation.screener import settings as S

    export, bulk = paths()
    dest = os.path.join(fa(), OUT_PANEL)
    if os.path.exists(dest):
        print("REFUSING: %s already exists. A rebuild that silently overwrites a panel other "
              "items have already read is how two items come to describe different objects; "
              "delete or rename it deliberately." % dest, flush=True)
        return 3

    class _C:
        wrds_data_dir = export

    prov = WRDSProvider(_C())
    prov._bulk_dir = bulk                # full-universe cache, NOT rebuilt, NOT overwritten
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready on %s: %s" % (export, msg))
    tickers = prov.universe(limit=None)
    print("universe from the export's own fundamentals index: %d names" % len(tickers),
          flush=True)
    print("THREE declared changes: keep_numbers=True | extra_horizons=%s | _KEEP + ncfdiv, "
          "ncfcommon" % (EXTRA_HORIZONS,), flush=True)

    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=63,
        keep_numbers=True,
        extra_horizons=list(EXTRA_HORIZONS),
    )
    secs = time.time() - t0
    print("built %s in %.0fs (%d names, %d dates, %d columns)"
          % (panel.shape, secs, panel["ticker"].nunique(), panel["date"].nunique(),
             len(panel.columns)), flush=True)

    # --- THE LIVE-THEME GATE, before anything reads it --------------------------------
    cols = [c for c in S.BUCKET_FACTORS["established"] if c in panel.columns]
    alive, dead = live_themes(panel, cols)
    print("\n=== LIVE THEMES (present, non-constant, non-zero dispersion)", flush=True)
    for c in cols:
        v = pd.to_numeric(panel[c], errors="coerce")
        print("   %-22s distinct %-8d sd %-12.6g nonnull %.4f  %s"
              % (c, v.nunique(dropna=True), (v.std() if v.notna().any() else 0.0),
                 v.notna().mean(), "LIVE" if c in alive else "DEAD"), flush=True)
    weighted = sorted(k for k, w in
                      ((k, S.WEIGHTS_ESTABLISHED.get(k, 0.0))
                       for k in S.BUCKET_FACTORS["established"]) if w)
    missing = [c for c in weighted if c not in alive]
    if missing:
        raise SystemExit("REFUSING TO WRITE: the weighted themes %r are not LIVE (%r). "
                         "UNIVERSE-BIAS shipped a SIX-theme confounded panel whose `insider` was "
                         "constant at one distinct value at 100pc non-null and whose runner "
                         "reported 'themes 7' because it counted columns PRESENT -- coverage is "
                         "not fidelity." % (missing, {k: dead.get(k) for k in missing}))
    print("\nall %d WEIGHTED themes are LIVE: %s" % (len(weighted), ", ".join(weighted)),
          flush=True)

    # --- what the three changes actually bought ---------------------------------------
    fwd = sorted(c for c in panel.columns if c.startswith("fwd_ret"))
    zc = sorted(c for c in panel.columns if c.startswith("z_"))
    payout = {}
    for c in ("ncfdiv", "ncfcommon"):
        hits = [k for k in panel.columns if c in k]
        payout[c] = hits
    print("\nforward-return columns (%d): %s" % (len(fwd), fwd), flush=True)
    print("z_ columns: %d" % len(zc), flush=True)
    print("payout-derived columns: %s" % payout, flush=True)

    panel.to_pickle(dest)
    print("\nwrote %s" % dest, flush=True)

    res = {
        "item": "CORRECTED-REBUILD",
        "trials": 0,
        "trial_class": "PANEL BUILD -- not a search. No hypothesis, no bar, no arm, no outcome "
                       "statistic (S25 / X7RECON / PANEL-EXT-RECHECK class).",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "panel": OUT_PANEL,
        "banked_panels_not_overwritten": ["panel_corrected_69d.pkl",
                                          "UNIVERSE_BIAS_PANEL_full.pkl",
                                          "UNIVERSE_BIAS_PANEL_full_v2.pkl"],
        "base_horizon_column_is_present_for_S22s_C0_control": (
            "fwd_ret_h63 is carried deliberately. It is NOT a duplicate of fwd_ret: it is the "
            "input to S22's C0 control, which checks that the extra_horizons machinery "
            "reproduces the shipped column. The exactness is REPORTED BY S22 ITSELF rather "
            "than re-derived here (B7) -- a second definition of one control is how two numbers "
            "for one question come about."),
        "export": export,
        "bulk_dir": bulk,
        "build_seconds": secs,
        "shape": list(panel.shape),
        "names": int(panel["ticker"].nunique()),
        "dates": int(panel["date"].nunique()),
        "columns": int(len(panel.columns)),
        "the_three_declared_changes": {
            "keep_numbers": True,
            "extra_horizons": list(EXTRA_HORIZONS),
            "keep_additions": ["ncfdiv", "ncfcommon"],
            "everything_else": "bit-for-bit UNIVERSE-BIAS's invocation, read from CONFIG rather "
                               "than retyped, same full-universe export and bulk cache",
        },
        "live_themes": {"alive": alive, "dead": dead,
                        "weighted_all_live": True,
                        "min_distinct_per_theme": MIN_DISTINCT_PER_THEME},
        "forward_return_columns": fwd,
        "z_columns": len(zc),
        "payout_columns_present": payout,
        "not_done": [
            "NOTHING READS IT YET. The successor items each gate on their own controls.",
            "The CANONICAL panel is NOT moved -- that is Don's and is PENDING (DECISIONS.md "
            "2026-10-07).",
        ],
    }
    with io.open(os.path.join(fa(), OUT_JSON), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("wrote %s" % os.path.join(fa(), OUT_JSON), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
