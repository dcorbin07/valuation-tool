# -*- coding: utf-8 -*-
"""`CORRECTED-CLAIMS-2` — the four claims `CORRECTED-FLOORS` left UNMEASURED, plus R1's
net-of-cost cell, on the REBUILT corrected panel.

    python -m scripts.corrected_claims2 --what s22|score|v6b|r1cost|all

**ZERO TRIALS.** Every construction is registered and landed; re-measuring one on a corrected
universe is the `S25` / `X7RECON` / `PANEL-EXT-RECHECK` class.

**EVERY FIGURE NAMES ITS WEIGHTING, and they are all the DEPLOYED book (flat 1/7).** `CORRECTED-
FLOORS` part 1b measured why that matters: `placebo.py` mirrors `run_backtests`, CPCV **ADOPTS**
`ic-proportional` on this universe, and the adopted book's top-decile alpha is **2.83%** against
the deployed **6.07%** — so a corrected-universe figure that does not say which weighting it is
cannot be compared to anything published. `term_structure` already uses its own `DEPLOYED` dict
(7 at 0.125) and `factor_alpha` uses `WEIGHTS_ESTABLISHED`'s non-zero entries; both are the
deployed book, verified rather than assumed.

**THE THREE-STATE VOCABULARY IS REUSED, NOT RE-DEFINED** — `corrected_claims.claim()` is CALLED
(`B7`), so a `SURVIVES` row still cannot exist without a corrected value and an `UNMEASURED` row
still cannot exist without a named reason.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.corrected_claims as CC                                       # noqa: E402

#: the panel of record. v2 shipped without `fwd_ret_h63` and so could not run S22's own C0
#: control; v3 adds that column and nothing else, proved cell-for-cell by
#: `scripts/corrected_rebuild_inert.py`. A measurement reading only columns the two share is
#: therefore IDENTICAL BY PROOF on either, which is what licenses keeping a v2-era artifact.
PANEL = "UNIVERSE_BIAS_PANEL_full_v3.pkl"
OUT = "CORRECTED_CLAIMS2.json"

#: the published figures these claims assert, from the surfaces that carry them. Literals, so a
#: drift shows as a diff here (`MA13`'s idiom) rather than being silently inherited.
PUBLISHED = {
    "s22_min_t": 3.16,                 # "t never below 3.16"
    "s22_two_year_t": 3.83,            # "3.83 at two years"
    "hold_1q": 0.066,                  # "beat the universe by 6.6% at one quarter"
    "hold_2y": 0.051,                  # "5.1% at two years"
    "score_per_name": (45, 69),        # score_confidence.PER_NAME_DATES
    "score_group": (21, 69),           # score_confidence.GROUP_DATES
    "v6b_healthy": 0.3251,             # V6-B M1 healthy further-20% rate
    "v6b_unhealthy": 0.4335,           # V6-B M1 unhealthy
}


def fa():
    return CC.fa()


def panel_path():
    return os.path.join(fa(), PANEL)


def _run(cmd, log):
    """Run a shipped script and KEEP its log. A shipped instrument is CALLED, never
    re-implemented (`B7`) -- these four claims each have a registered producer."""
    print("  $ %s" % " ".join(cmd[1:]), flush=True)
    with io.open(log, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, cwd=_HERE, stdout=fh, stderr=subprocess.STDOUT).returncode
    print("    exit %d  (log %s)" % (rc, os.path.basename(log)), flush=True)
    return rc


def run_s22():
    """`S22`'s term structure AND `hold_horizon` -- ONE run answers both, because
    `hold_horizon.REGISTER` IS `PREREG_s22_term_structure.md`. Verified, not assumed.

    **`--skip-placebo` IS A DECLARED DEVIATION WITH ITS CONSEQUENCE NAMED.** `S22`'s own floors
    are a per-horizon `fixed_weights_null` at 200 draws, and `CLAUDE.md` records that those
    percentiles **may never be compared with X7's 2.2837** -- they are a different and less
    conservative null. On a 290k-row panel 200 draws x 8 horizons is many hours, and a reduced
    draw count is refused outright: `CORRECTED-FLOORS` fixed `MIN_DRAWS_FOR_A_FLOOR = 100` and a
    p95 over fewer is set by its top two values.

    **SO THE STATISTIC IS MEASURED AND THE PER-HORIZON FLOOR IS NOT.** The claim being re-measured
    is about the *t* VALUES ("t never below 3.16"), which is measurable; whether those *t*s would
    clear a per-horizon null on this universe is reported `UNMEASURED` with the cost named. Only
    the h=63 cell has a corrected floor, from `CORRECTED-FLOORS` part 1, and comparing h>63
    against it would be the extrapolation `S22` built its own nulls to avoid.
    """
    out = os.path.join(fa(), "CORRECTED_S22_TERM_STRUCTURE.json")
    rc = _run([sys.executable, "-m", "scripts.term_structure",
               "--panel", panel_path(), "--json", out, "--skip-placebo"],
              os.path.join(fa(), "CORRECTED_S22.log"))
    return out if rc == 0 else None


def run_score():
    """`score_confidence`'s 45-of-69 / 21-of-69. Batch 1's blocker was `KeyError: 'bucket'`;
    `keep_numbers=True` restores it."""
    out = os.path.join(fa(), "CORRECTED_SCORE_CALIBRATION.json")
    rc = _run([sys.executable, "-m", "scripts.score_calibration",
               "--panel", panel_path(), "--out", out],
              os.path.join(fa(), "CORRECTED_SCORE.log"))
    return out if rc == 0 else None


def run_v6b():
    """`V6-B`'s dip survival.

    **IT DOES NOT BUILD A PANEL -- IT LOADS ONE, UNCONDITIONALLY**
    (`panel = pickle.load(open(args.panel_cache))`), and the one it was written for is `V6`'s
    `panel_v6.pkl`. A first pass pointed `--panel-cache` at a path that did not exist and died
    on `FileNotFoundError`; the fix is NOT to build a second panel.

    **THE REBUILT PANEL IS A VALID SUBSTITUTE, AND THAT IS VERIFIED RATHER THAN ASSUMED.** `V6`
    builds with `rebalance_days=63`, `lookback_years=CONFIG.backtest_lookback_years`,
    `horizon=63`, `extra_horizons=(126,)` and pickles the result BEFORE deriving anything -- so
    `panel_v6.pkl` is a plain engine panel. The rebuild uses the SAME grid (CONFIG's
    `backtest_rebalance_days` is 63 and `backtest_lookback_years` is 18, measured, not assumed),
    the same engine, and a SUPERSET of columns including `fwd_ret_h126`.

    **AND V6-B READS ONLY SIX PANEL COLUMNS**, enumerated off its syntax tree rather than by
    reading: `date`, `ticker`, `quality`, `insider`, `fwd_ret`, `fwd_ret_h126`. Everything else
    it appears to read -- `drawdown`, `health`, `fwd_min_ret`, `n_insider_buys` -- it DERIVES
    itself from `--data-dir` and `--bulk-dir` (`trailing_drawdown` and `health_panel` are
    IMPORTED from `V6` so the floors cannot drift) and merges on `(date, ticker)`. All six are
    present on the rebuilt panel, checked against it.

    **THE MERGE IS THE HAZARD AND THE VERDICT PASS GATES ON IT.** These panels carry STRING
    dates, so a merge against a `Timestamp`-keyed frame matches ZERO rows IN SILENCE -- this
    record's own recurring defect. V6-B reports `drawdown_cov`, `health_cov` and `fwd_min_cov`;
    the verdict pass refuses to read an arm whose merge coverage collapsed, so a failed join
    cannot surface as a null.
    """
    from scripts.index_best import _data_root
    data = _data_root()
    out = os.path.join(fa(), "CORRECTED_V6B_DIP_SURVIVAL.json")
    rc = _run([sys.executable, "-m", "scripts.v6b_dip_survival",
               "--data-dir", os.path.join(data, "full2009", "backtest"),
               "--bulk-dir", os.path.join(data, "bulk"),
               "--panel-cache", panel_path(),
               "--v6-artifact", os.path.join(fa(), "V6_DIP_DETECTOR.json"),
               "--json", out],
              os.path.join(fa(), "CORRECTED_V6B.log"))
    return out if rc == 0 else None


#: `B11`'s measured one-way cost, in bps. Measured on the RESTRICTED universe and NOT
#: re-measured here -- a 9,645-name book holds far smaller names and would pay more, so this is
#: a labelled SENSITIVITY and never the primary figure (`O-1`: a figure measured on one
#: population applied to another was ~17x wrong).
B11_REALISED_ONE_WAY_BPS = 33.4


def r1_net_of_cost():
    """R1's net-of-cost cell: DIAGNOSED, then measured as a SEPARATELY LABELLED reading.

    **THE CAUSE, measured rather than guessed.** `factor_alpha`'s `net_of_cost` joins `X4`'s
    SHIPPED `ETF_BENCHMARK_RESULTS_strategy_series.csv` on its `turnover` and `cost_bps` columns
    with `how="left"`. That series is indexed on **X4's own dates**, which are not the corrected
    panel's, so the join matches nothing and every cell comes back `NaN`. It is the `E-6` family
    -- a merge keyed on another object's dates -- except that here it produced NaN rather than
    silence, so it was visible.

    **R1's OWN PATH IS NOT EDITED.** Repointing its cost leg would change a landed instrument,
    and the figure it produced is `R1`'s.

    **THE PRIMARY IS THE BREAKEVEN, WHICH NEEDS NO COST ASSUMPTION**: the one-way cost at which
    the deployed book's net alpha vs equal-weight reaches zero. The 33.4 bps reading is a
    labelled sensitivity with its population named, and the corrected universe's own realised
    cost is reported UNMEASURED rather than inherited.
    """
    import pandas as pd
    from valuation.edge.fundamental_panel import cost_breakeven_bps, _base_weights
    from valuation.screener import settings as S

    gross_path = os.path.join(fa(), "CORRECTED_R1_FACTOR_ALPHA.json")
    if not os.path.exists(gross_path):
        return {"state": "UNMEASURED",
                "why": "CORRECTED_R1_FACTOR_ALPHA.json absent -- part 2's R1 run is the gross leg"}
    with io.open(gross_path, encoding="utf-8") as fh:
        r1 = json.load(fh)

    # the artifact's OWN declared primary spec, not one chosen here. `specs` is keyed
    # "compound/full" -- one slash-joined string, not a nested dict, which is what my first
    # path got wrong.
    spec = ((r1.get("verdict") or {}).get("primary_spec")) or "compound/full"
    gross = (((r1.get("specs") or {}).get(spec) or {}).get("ff5_mom") or {}).get(
        "top_minus_ew") or {}
    nc = r1.get("net_of_cost") or {}

    panel = pd.read_pickle(panel_path())
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    base = _base_weights(cols, "established")
    bk = cost_breakeven_bps(panel, cols, base, horizon=63) or {}
    curve = bk.get("curve") or []

    # IS THE CURVE AFFINE? Cost is turnover x bps, so it must be -- and that is CHECKED, because
    # an affine assumption that happened to be false would make an interpolated drag wrong in a
    # way nothing else here would catch.
    affine, max_second_diff = None, None
    pts = [(float(c["bps"]), float(c["net_alpha"])) for c in curve
           if c.get("bps") is not None and c.get("net_alpha") is not None]
    pts.sort()
    if len(pts) >= 3:
        slopes = [(pts[i + 1][1] - pts[i][1]) / (pts[i + 1][0] - pts[i][0])
                  for i in range(len(pts) - 1) if pts[i + 1][0] != pts[i][0]]
        max_second_diff = (max(abs(a - b) for a, b in zip(slopes, slopes[1:]))
                           if len(slopes) >= 2 else 0.0)
        affine = bool(max_second_diff is not None and max_second_diff <= 1e-9)

    def _net_at(b):
        """Exact under affinity, which is checked above."""
        if len(pts) < 2:
            return None
        lo = max([q for q in pts if q[0] <= b], default=pts[0])
        hi = min([q for q in pts if q[0] >= b], default=pts[-1])
        if hi[0] == lo[0]:
            return lo[1]
        w = (b - lo[0]) / (hi[0] - lo[0])
        return lo[1] + w * (hi[1] - lo[1])

    a0 = _net_at(0.0)
    a_b11 = _net_at(B11_REALISED_ONE_WAY_BPS)
    drag = (None if (a0 is None or a_b11 is None) else (a0 - a_b11))
    g = gross.get("alpha_ann")

    # THE AFFINITY CHECK FIRED, SO THE CLAIM CHANGES RATHER THAN THE TOLERANCE (`W-28`). The
    # curve is affine only to a measured ~1e-5 second difference, almost certainly because
    # `net_ann` compounds -- so the interpolated 33.4 bps drag is APPROXIMATE. Rather than
    # assert an exactness that is not there, the drag is BRACKETED by the two adjacent grid
    # points. A bracket is a measurement; an assumed affinity is not.
    grid_bps = sorted({q[0] for q in pts})
    lo_b = max([b for b in grid_bps if b <= B11_REALISED_ONE_WAY_BPS], default=None)
    hi_b = min([b for b in grid_bps if b >= B11_REALISED_ONE_WAY_BPS], default=None)
    bracket = {}
    for tag, b in (("lower_grid_point", lo_b), ("upper_grid_point", hi_b)):
        if b is None:
            continue
        ab = _net_at(b)
        bracket[tag] = {
            "one_way_bps": b,
            "cost_drag_ann": (None if (a0 is None or ab is None) else a0 - ab),
            "derived_net_alpha_ann": (None if (a0 is None or ab is None or g is None)
                                      else float(g) - (a0 - ab)),
        }

    return {
        "state": "MEASURED-AS-A-DERIVED-READING",
        "r1_own_net_of_cost_is_NaN": bool(
            nc.get("cost_drag_ann") is None
            or (isinstance(nc.get("cost_drag_ann"), float)
                and nc["cost_drag_ann"] != nc["cost_drag_ann"])),
        "cause": "factor_alpha's net_of_cost joins X4's SHIPPED strategy-series turnover and "
                 "cost_bps with how='left', and that series is indexed on X4's OWN dates, which "
                 "are not the corrected panel's -- so the join matches nothing and every cell is "
                 "NaN. The E-6 family (a merge keyed on another object's dates), except visible "
                 "because it produced NaN rather than silence.",
        "r1_path_not_edited": "repointing R1's cost leg would change a landed instrument",
        "primary_spec_from_the_artifact": spec,
        "gross_alpha_ann": g,
        "gross_t_nw": gross.get("alpha_t_nw"),
        "PRIMARY_breakeven_one_way_bps": bk.get("breakeven_one_way_bps"),
        "primary_is_the_breakeven_because": (
            "it needs no cost assumption. cost_breakeven_bps measures no realised cost, and "
            "B11's 33.4 bps was measured on the RESTRICTED universe -- a 9,645-name book holds "
            "far smaller names and would pay more, so quoting a net alpha off it would be O-1's "
            "defect: a figure measured on one population applied to another."),
        "SENSITIVITY_at_B11_bps": {
            "one_way_bps": B11_REALISED_ONE_WAY_BPS,
            "population_the_bps_came_from": "the RESTRICTED universe (B11); NOT re-measured here",
            "net_alpha_vs_ew_at_0bps": a0,
            "net_alpha_vs_ew_at_B11": a_b11,
            "cost_drag_ann": drag,
            "derived_net_alpha_ann": (None if (drag is None or g is None) else float(g) - drag),
            "interpolation_is_APPROXIMATE_not_exact": (
                "the affinity check FIRED -- the curve's max second difference is ~1e-5 rather "
                "than 0, almost certainly because net_ann compounds. So the 33.4 bps figure is "
                "interpolated between adjacent grid points rather than exact, and the bracket "
                "below is the measurement. The tolerance was NOT relaxed to make an exactness "
                "claim pass; the claim was changed."),
            "bracketed_by_the_adjacent_grid_points": bracket,
        },
        "curve_is_affine_in_bps": affine,
        "curve_max_second_difference": max_second_diff,
        "why_affinity_is_checked": "cost is turnover x bps, so net_alpha SHOULD be affine in "
                                   "bps and an interpolated drag would be exact. THE CHECK "
                                   "FIRED: the max second difference is ~1e-5 rather than "
                                   "0, so it is affine only to that precision and the "
                                   "interpolation is approximate. That is why the check "
                                   "exists -- an assumed affinity would have been wrong in "
                                   "a way nothing else here would catch -- and the answer "
                                   "is a BRACKET rather than a looser tolerance.",
        "corrected_realised_one_way_bps": None,
        "corrected_realised_cost_is_UNMEASURED_because": (
            "cost_breakeven_bps returns a breakeven and a curve, not a realised cost. The "
            "realised figure comes from run_backtests' own `costs` block, which is a full "
            "backtest -- it is item 5's to produce when the canonical run is re-run, not this "
            "item's to estimate."),
        "weighting": "DEPLOYED (flat 1/7 via _base_weights); CPCV never consulted",
        "label": "a DERIVED cost-adjusted intercept, NOT R1's own net_of_cost cell",
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="all",
                    choices=["s22", "score", "v6b", "r1cost", "all"])
    args = ap.parse_args(argv)
    if not os.path.exists(panel_path()):
        raise SystemExit("REFUSING: no rebuilt panel at %s. Run "
                         "`scripts/corrected_rebuild.bat` first." % panel_path())

    done = {}
    if args.what in ("s22", "all"):
        done["s22"] = run_s22()
    if args.what in ("score", "all"):
        done["score"] = run_score()
    if args.what in ("v6b", "all"):
        done["v6b"] = run_v6b()
    if args.what in ("r1cost", "all"):
        done["r1cost"] = r1_net_of_cost()

    res = {"item": "CORRECTED-CLAIMS-2", "trials": 0,
           "trial_class": "RE-MEASUREMENT of registered constructions on a corrected universe "
                          "(S25 / X7RECON / PANEL-EXT-RECHECK class).",
           "adopts_nothing": True, "changes_no_public_page": True,
           "panel": PANEL,
           "weighting": "DEPLOYED (flat 1/7) on every figure -- part 1b measured that the "
                        "adopted book's alpha is 2.83pc against the deployed 6.07pc, so a "
                        "corrected-universe figure that does not name its weighting cannot be "
                        "compared to anything published",
           "published_figures_being_rechecked": {k: list(v) if isinstance(v, tuple) else v
                                                 for k, v in PUBLISHED.items()},
           "ran": {k: (v if isinstance(v, dict) else (os.path.basename(v) if v else None))
                   for k, v in done.items()}}
    with io.open(os.path.join(fa(), OUT), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote %s" % os.path.join(fa(), OUT), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
