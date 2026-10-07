# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 4 -- every public figure, current against corrected. ZERO TRIALS.

A **FACTS** table: what each public surface says today, what the same quantity is on a corrected
universe, and where the number comes from. No hypothesis, no bar, no verdict against a threshold
(`S25` / `MB3` / `PANEL-EXT-RECHECK` class).

**THREE OBJECTS, NOT TWO, AND CONFLATING ANY PAIR OF THEM IS THE WHOLE TRAP:**

  * **`published`** -- the tracked `BACKTEST_RESULTS.json`, 2,531 names, `available_end`
    2026-07-24, generated 2026-08-14. **This is the one every public figure actually reads or was
    transcribed from.**
  * **`restricted`** -- the SAME `data/backtest` universe rebuilt at the **2026-10** vintage.
  * **`corrected`** -- the full raw universe at the **same 2026-10 vintage**.

`published -> restricted` is the **VINTAGE** effect and `restricted -> corrected` is the
**UNIVERSE** effect. Reading `published -> corrected` as "the universe" would charge the universe
for two quarters of new data, which is exactly the confound this item exists to remove.

**WHERE THE PUBLIC FIGURES LIVE MATTERS AS MUCH AS WHAT THEY SAY.** Three sources, and only the
first moves on its own when the panel moves:

  * **LIVE** -- read from `BACKTEST_RESULTS.json` at request time (`/proof` is almost entirely
    this). Re-pointing the canonical panel moves these with no code change at all.
  * **TRANSCRIBED** -- a literal in python, overwhelmingly
    `valuation/screener/index_book_measured.py`, which is the entire backtested column of the
    public Index tab plus the landing page's two headline tiles. These do **not** move; somebody
    has to retype them, and that is the app fixer's lane.
  * **TYPED IN A TEMPLATE** -- `methodology.html` and `_proof_body.html` prose.

**THIS SCRIPT CHANGES NO PUBLIC PAGE AND IS PINNED NOT TO.** It reads artifacts and writes one
JSON. The app fixer owns every surface named in it.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: the three objects, in the only order that keeps vintage and universe apart.
SIDES = ("published", "restricted", "corrected")

#: (label, dotted path into the payload). The path is the SAME for all three objects, so a
#: figure is never read from one block in one column and a different block in another.
FIGURES = [
    # --- universe and window ------------------------------------------------------------
    ("panel names", "universe.n_names"),
    ("panel dates", "universe.n_dates"),
    ("window start", "cleanups.panel_window.retained_start"),
    ("window end", "cleanups.panel_window.retained_end"),
    ("cross-section median", "cleanups.panel_window.cross_section_median"),
    # --- the headline -------------------------------------------------------------------
    ("top-decile alpha vs equal-weighted universe", "construction.top_decile_alpha"),
    ("top-decile alpha HAC t", "construction.top_decile_alpha_tstat_nw"),
    ("long-short /yr", "construction.long_short_ann"),
    ("long-short naive t", "construction.long_short_tstat"),
    ("long-short HAC t", "construction.long_short_tstat_nw"),
    ("monotonicity", "construction.monotonicity"),
    # --- benchmarks ---------------------------------------------------------------------
    ("equal-weight benchmark /yr", "benchmarks.equal_weight.benchmark_ann"),
    ("top decile /yr", "benchmarks.equal_weight.top_decile_ann"),
    ("excess vs equal-weight", "benchmarks.equal_weight.excess_ann"),
    ("excess vs equal-weight t", "benchmarks.equal_weight.excess_tstat_nw"),
    ("excess vs equal-weight hit rate", "benchmarks.equal_weight.hit_rate"),
    ("cap-weighted benchmark /yr", "benchmarks.cap_weighted.benchmark_ann"),
    ("excess vs cap-weighted", "benchmarks.cap_weighted.excess_ann"),
    ("excess vs cap-weighted t", "benchmarks.cap_weighted.excess_tstat_nw"),
    ("SPY /yr", "benchmarks.spy.benchmark_ann"),
    ("excess vs SPY", "benchmarks.spy.excess_ann"),
    ("excess vs SPY t", "benchmarks.spy.excess_tstat_nw"),
    ("excess vs SPY hit rate", "benchmarks.spy.hit_rate"),
    # --- costs --------------------------------------------------------------------------
    ("breakeven one-way bps", "costs.top_decile.breakeven_one_way_bps"),
    ("realised one-way bps", "costs.top_decile.realised_one_way_bps"),
    ("annual turnover", "costs.top_decile.annual_turnover"),
    ("gross alpha", "costs.top_decile.gross_alpha"),
    ("net alpha", "costs.top_decile.net_alpha"),
    ("net max drawdown", "costs.top_decile.net_max_drawdown"),
    # --- multiple testing ---------------------------------------------------------------
    ("Deflated Sharpe", "cpcv.deflated_sharpe.value"),
    ("PBO", "cpcv.pbo.value"),
    ("CPCV adopt", "cpcv.adopt"),
    ("HLZ hurdle", "multiple_testing.hlz.hurdle_sqrt_2_ln_N"),
    ("HLZ statistic", "multiple_testing.hlz.value"),
    ("clears HLZ", "multiple_testing.hlz.clears_hlz_hurdle"),
    # --- distribution (S28) -------------------------------------------------------------
    ("quarters negative (alpha)", "construction.top_decile_alpha_distribution.negative_fraction"),
    ("negative periods", "construction.top_decile_alpha_distribution.negative_periods"),
    ("worst quarter", "construction.top_decile_alpha_distribution.min"),
    ("best quarter", "construction.top_decile_alpha_distribution.max"),
    ("median quarter", "construction.top_decile_alpha_distribution.median"),
    ("mean quarter", "construction.top_decile_alpha_distribution.mean"),
    # --- portfolio / book ---------------------------------------------------------------
    ("book CAGR", "portfolio.cagr"),
    ("book held median", "portfolio.held_median"),
]

#: Public surfaces, with where the figure comes from. `source` is the census's classification:
#: LIVE = read from BACKTEST_RESULTS.json at request time; TRANSCRIBED = a python literal;
#: TEMPLATE = typed into a template.
SURFACES = [
    ("/proof + Proof tab", "_proof_body.html via valuation/web/proof.py", "LIVE",
     "almost every figure; moves with the canonical panel and needs NO code change"),
    ("/proof", "valuation/web/proof.py:293,309", "TRANSCRIBED",
     "the PBO bar 0.50 and the Deflated Sharpe bar 0.95 -- thresholds, not measurements, so "
     "they do not move with the panel"),
    ("Index tab (backtested column)", "valuation/screener/index_book_measured.py:59-154",
     "TRANSCRIBED",
     "30+ literals -- Roth 17.1619, taxable 12.2033, alpha vs own tier 4.1209, vs all-cap EW "
     "-0.0576, vs SPY 1.9488, Sharpe 1.0318, turnover 2.4372, drawdown -23.03, the power note, "
     "the caption's 2531/69. NOTHING here re-reads an artifact"),
    ("landing page", "landing.html:209,211 via index_track.py:647-648", "TRANSCRIBED",
     "'Backtested net alpha' = index_book_measured.ALPHA_VS_ALL_CAP_EW_PP and 'Net Sharpe' = "
     "SERVED_ROTH_SHARPE -- the same literals as the Index tab"),
    ("landing page", "landing.html:76", "TEMPLATE", "'18 years point-in-time, survivorship-free'"),
    ("/methodology", "methodology.html:58-60,73,89-106,124-125,189-195", "TEMPLATE",
     "breakeven 134 bps, measured 33 bps, turnover 261%, ~2,531-name panel, +6.99%/yr t 3.98, "
     "+5.1% to +10.9%, t never below 3.16, Deflated Sharpe ~0.79"),
    ("/methodology + Hot Stocks legend", "valuation/web/hold_horizon.py:70-95", "TRANSCRIBED",
     "PANEL_NAMES 2531, PANEL_DATES 69, ALPHA_ANN_FIRST_QUARTER 6.6, ALPHA_ANN_TWO_YEARS 5.1, "
     "RANK_IC 0.0336/0.0655"),
    ("/methodology + Hot Stocks legend", "valuation/web/score_confidence.py:53-68", "TRANSCRIBED",
     "PER_NAME_DATES (45,69), GROUP_DATES (21,69)"),
    ("/work (unlisted, no login)", "portfolio.html", "TEMPLATE",
     "the whole page -- 2,531 names / 69 rebalances / 2008-2026, t 2.62, t 4.38, 134 bps, "
     "33 bps, 261%, Deflated Sharpe 0.79, the HLZ 3.3 discussion"),
    ("Track Record tab", "index.html + /api/track", "LIVE",
     "the FORWARD track, not the backtest -- unaffected by a panel change"),
]


#: Public CLAIMS, each tied to the figure that carries it, so a verdict is DERIVED from the
#: table rather than typed. Three states and the third is load-bearing:
#:
#:   SURVIVES          -- the corrected figure still supports the sentence on the page
#:   NO-LONGER-HOLDS   -- it does not
#:   UNMEASURED        -- this item did not re-measure it, so NEITHER of the above may be said
#:
#: `UNMEASURED` exists because the temptation is to let a claim nobody re-ran read as surviving.
#: `R1`'s factor alpha, `S22`'s term structure, `score_confidence`'s date counts, `payoff`'s
#: options figures and `dip_posture`'s survival figures are all in that third state: they rest on
#: the banked panel and re-measuring each is its own item.
CLAIMS = [
    # (claim as a reader sees it, surface, figure key, test)
    ("+7.17%/yr top-decile alpha vs the equal-weighted universe, t 4.38",
     "/proof benchmark table (LIVE)", "excess vs equal-weight t",
     lambda v: ("SURVIVES" if v is not None and abs(v) >= 2.0 else "NO-LONGER-HOLDS")),
    ("beat SPY by +9.99%/yr, t 3.77",
     "/proof + /methodology (LIVE + TEMPLATE)", "excess vs SPY t",
     lambda v: ("SURVIVES" if v is not None and abs(v) >= 2.0 else "NO-LONGER-HOLDS")),
    ("beat the cap-weighted panel by +10.46%/yr, t 4.29",
     "/proof benchmark table (LIVE)", "excess vs cap-weighted t",
     lambda v: ("SURVIVES" if v is not None and abs(v) >= 2.0 else "NO-LONGER-HOLDS")),
    ("top decile returned 25.3%/yr",
     "/proof decile ladder (LIVE)", "top decile /yr",
     lambda v: ("SURVIVES" if v is not None and v >= 0.22 else "NO-LONGER-HOLDS")),
    ("breakeven 134 bps against a measured 33 bps -- a 4.0x margin",
     "/proof + /methodology (LIVE + TEMPLATE)", "_cost_margin",
     lambda v: ("SURVIVES" if v is not None and v >= 3.0 else "NO-LONGER-HOLDS")),
    ("Deflated Sharpe about 0.79, below the 0.95 bar",
     "/proof + /methodology + /work (LIVE + TEMPLATE)", "Deflated Sharpe",
     lambda v: ("SURVIVES" if v is not None and v >= 0.60 else "NO-LONGER-HOLDS")),
    ("PBO 0.733, failing the <0.50 bar",
     "/proof bars table (LIVE)", "PBO",
     lambda v: ("SURVIVES" if v is not None and v >= 0.50 else "NO-LONGER-HOLDS")),
    ("lost to the market in 29% of quarters (20 of 69), worst -6.83%",
     "/proof (LIVE)", "quarters negative (alpha)",
     lambda v: ("SURVIVES" if v is not None and v <= 0.33 else "NO-LONGER-HOLDS")),
    ("the whole ~2,531-name panel / PANEL_NAMES 2531",
     "/methodology + hold_horizon.py (TEMPLATE + TRANSCRIBED)", "panel names",
     lambda v: ("SURVIVES" if v is not None and abs(v - 2531) < 600 else "NO-LONGER-HOLDS")),
    ("long-short t 2.62 Newey-West",
     "/proof bars + /work (LIVE + TEMPLATE)", "long-short HAC t",
     lambda v: ("SURVIVES" if v is not None and abs(v) >= 2.0 else "NO-LONGER-HOLDS")),
    ("the deciles are cleanly ordered (monotonicity -0.891)",
     "/proof ordering statistic (LIVE)", "monotonicity",
     lambda v: ("SURVIVES" if v is not None and v <= -0.70 else "NO-LONGER-HOLDS")),
]

#: Claims this item did NOT re-measure. Listed so the absence is explicit.
UNMEASURED = [
    ("+6.99%/yr factor-adjusted alpha, t 3.98 (R1)", "/methodology (TEMPLATE)",
     "R1's FF5+MOM regression was not re-run on the corrected universe"),
    ("t never below 3.16, 3.83 at two years (S22 term structure)", "/methodology (TEMPLATE)",
     "S22 was not re-run"),
    ("holds on 45 of 69 / 21 of 69 dates (score calibration)",
     "/methodology + Hot Stocks legend (TRANSCRIBED)", "score_confidence was not re-measured"),
    ("beat the universe by 6.6% at one quarter, 5.1% at two years (hold horizon)",
     "/methodology + Hot Stocks legend (TRANSCRIBED)", "hold_horizon was not re-measured"),
    ("3,885 trades / 187 names / -5.06pp vs random entry (options payoff)",
     "/methodology (TRANSCRIBED)", "an OPTIONS book -- an equity panel change cannot move it"),
    ("32.5% vs 43.4% dip survival (V6-B)", "Dip Detector tab (TRANSCRIBED)",
     "V6-B was not re-run"),
    ("the Index tab's backtested column and the landing page's two tiles",
     "Index tab + landing (TRANSCRIBED, index_book_measured.py)",
     "INDEX-BOOK's own C1 fidelity gate REFUSES any panel but the banked one, so these were "
     "not re-derived here; UNIVERSE-BIAS part 2 measures the same construction at "
     "18.42% restricted against 18.02% corrected, so the universe moves them about -0.4pp"),
    ("the live/forward Track Record", "Track Record tab (LIVE)",
     "the forward track is not a backtest and no panel change touches it"),
]


def dig(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")
    rr = os.path.join(fa, "canonical_rerun")

    paths = {
        "published": os.path.join(_HERE, "BACKTEST_RESULTS.json"),
        "restricted": os.path.join(rr, "restricted_2026_10", "BACKTEST_RESULTS.json"),
        "corrected": os.path.join(rr, "corrected_2026_10", "BACKTEST_RESULTS.json"),
    }
    loaded, absent = {}, []
    for k, p in paths.items():
        if os.path.exists(p):
            loaded[k] = json.load(io.open(p, encoding="utf-8"))
        else:
            absent.append(k)
    if "published" not in loaded:
        print("REFUSING: the tracked canonical artifact is absent at %s" % paths["published"])
        return 2
    if absent:
        print("NOTE: %r not yet on disk -- the table will mark them PENDING rather than "
              "silently omitting the column." % absent, flush=True)

    rows = []
    for label, path in FIGURES:
        row = {"figure": label, "payload_path": path}
        for side in SIDES:
            row[side] = dig(loaded[side], path) if side in loaded else "PENDING"
        # deltas, only where both ends are numbers
        for a, b, name in (("published", "restricted", "d_vintage"),
                           ("restricted", "corrected", "d_universe"),
                           ("published", "corrected", "d_total")):
            try:
                row[name] = float(row[b]) - float(row[a])
            except (TypeError, ValueError):
                row[name] = None
        rows.append(row)

    by_fig = {r["figure"]: r for r in rows}
    # a derived figure the table does not carry directly: the cost MARGIN the pages quote
    for side in SIDES:
        try:
            be = float(by_fig["breakeven one-way bps"][side])
            rl = float(by_fig["realised one-way bps"][side])
            by_fig.setdefault("_cost_margin", {"figure": "_cost_margin"})[side] = be / rl
        except (TypeError, ValueError, KeyError, ZeroDivisionError):
            by_fig.setdefault("_cost_margin", {"figure": "_cost_margin"})[side] = None

    claims = []
    for claim, surface, key, test in CLAIMS:
        r = by_fig.get(key) or {}
        cur, corr = r.get("published"), r.get("corrected")
        if corr == "PENDING" or corr is None:
            verdict = "UNMEASURED"
        else:
            verdict = test(corr)
        claims.append({"claim": claim, "surface": surface, "figure": key,
                       "published": cur, "corrected": corr, "verdict": verdict})

    res = {
        "item": "UNIVERSE-BIAS", "part": "4 public-figure table", "trials": 0,
        "class": "FACTS -- what each surface says, what the same quantity is on a corrected "
                 "universe, and where the number comes from. No hypothesis, no bar, no verdict.",
        "objects": {
            "published": "tracked BACKTEST_RESULTS.json -- 2,531 names, available_end "
                         "2026-07-24, generated 2026-08-14. THE ONE EVERY PUBLIC FIGURE READS "
                         "OR WAS TRANSCRIBED FROM.",
            "restricted": "the SAME data/backtest universe rebuilt at the 2026-10 vintage",
            "corrected": "the full raw universe at the SAME 2026-10 vintage",
        },
        "attribution_rule": "published->restricted is the VINTAGE effect; "
                            "restricted->corrected is the UNIVERSE effect. Reading "
                            "published->corrected as 'the universe' charges the universe for "
                            "two quarters of new data.",
        "absent": absent,
        "figures": rows,
        "surfaces": [{"surface": s, "where": w, "source": src, "note": n}
                     for s, w, src, n in SURFACES],
        "claims": claims,
        "unmeasured": [{"claim": c, "surface": s, "why": w} for c, s, w in UNMEASURED],
        "verdict_vocabulary": "SURVIVES / NO-LONGER-HOLDS / UNMEASURED. The third is "
                              "load-bearing: a claim nobody re-measured must not read as one "
                              "that survived.",
        "changes_no_public_page": "this item changes no surface; every page named above is the "
                                 "app fixer's lane",
    }
    out = os.path.join(fa, "UNIVERSE_BIAS_PUBLIC.json")
    json.dump(res, io.open(out, "w", encoding="utf-8"), indent=2, default=str)

    print("\n%-46s %14s %14s %14s %10s %10s"
          % ("figure", "published", "restricted", "corrected", "d vintage", "d universe"))
    for r in rows:
        def f(v):
            if v is None:
                return "-"
            if v == "PENDING":
                return "PENDING"
            if isinstance(v, bool):
                return str(v)
            try:
                return "%.4f" % float(v)
            except (TypeError, ValueError):
                return str(v)[:14]
        print("%-46s %14s %14s %14s %10s %10s"
              % (r["figure"][:46], f(r["published"]), f(r["restricted"]), f(r["corrected"]),
                 f(r["d_vintage"]), f(r["d_universe"])))
    print("\n%-62s %12s %12s  %s" % ("public claim", "published", "corrected", "verdict"))
    for c in claims:
        def g(v):
            try:
                return "%.4f" % float(v)
            except (TypeError, ValueError):
                return str(v)
        print("%-62s %12s %12s  %s"
              % (c["claim"][:62], g(c["published"]), g(c["corrected"]), c["verdict"]))
    print("\nNOT RE-MEASURED (neither survives nor fails -- %d claims):" % len(UNMEASURED))
    for c, s_, w in UNMEASURED:
        print("  %-58s %s" % (c[:58], s_))
    print("\nwrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
