# -*- coding: utf-8 -*-
"""INDEX-BOOK -- backtest the construction the Valquo Index ACTUALLY serves. ZERO TRIALS.

WHY ZERO: this is ONE construction, fully determined by `valquo_index.build_index` and the
constants beside it. There is no hypothesis, no threshold, no verdict and no degree of freedom
-- every knob is read off the live code rather than chosen here. That is the `S25` / `MB3` /
`X7RECON` / `MC10` class: a fact about what the shipped code does, logged `FIXED`, charging
nothing. `MB1-SEL`'s rule is the general form -- a measurement that cannot produce a finding,
only describe or block one, adds no degree of freedom to any published claim.

THE COUNTER-ARGUMENT, STATED BECAUSE IT IS NOT FRIVOLOUS: the output is destined for the
contract's own power arithmetic, which today uses the full-universe decile's +9.99%/yr vs SPY.
A number that moves a power calculation is load-bearing. The distinction taken is that a
re-measurement of a KNOWN construction on a KNOWN panel selects nothing -- there is no arm that
could have come back the other way, because there is no second arm. If a later reader disagrees
the row is there to amend, and the direction of that error is the safe one (`MA6`): booking a
trial raises every bar.

FOUR ARMS, ONE KNOB APART, so every difference is attributable to a named knob rather than to
two implementations. All four call the SAME live function (`B7`):

  B  all-cap tier, equal weight,  no band   -- the construction every published figure uses
  C  large-cap tier, equal weight, no band  -- + the $10B tier
  D  large-cap tier, score weight, no band  -- + score weighting and the 8% cap
  A  large-cap tier, score weight, band .30 -- THE SERVED BOOK

`B` is a same-machinery REFERENCE and is NOT the published decile: the shipped
`quantile_backtest` cuts deciles with `array_split`, this cuts `round(n * 0.10)`, and the two
differ by a name or two per date. `C1` separately proves the published figure reproduces from
the shipped path, so the two roles are kept apart rather than one standing in for the other.
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

from valuation.studies import served_index_book as IB                       # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                  # noqa: E402
from valuation.edge.valquo_index import LARGE_CAP_MIN                # noqa: E402
from valuation.edge import track_meter as tm                        # noqa: E402
# TAX RATES AND THE TAX ENGINE, IMPORTED -- the short and long rates live in one place
# (`MA5`), and retyping either here would be a second copy of a rate that moves with the law.
from valuation.edge.fundamental_panel import (after_tax_backtest as at_backtest,  # noqa: E402
                                              TAX_LONG_TERM as TAX_LONG,
                                              TAX_SHORT_TERM as TAX_SHORT)
# B6's own constants, IMPORTED rather than retyped -- the defect `W-1`'s `K4` hit when it
# scored NINE themes at 0.125 against a deployed SEVEN.
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT       # noqa: E402

PUBLISHED_ALPHA = 0.07174142332098163     # construction.top_decile_alpha
PUBLISHED_SPY_EXCESS = 0.099864           # benchmarks.spy.excess_ann (GROSS)
# costs.top_decile, verbatim -- the published full-universe equal-weighted decile net of the
# modelled cost table. Committed as literals so a drift in the artifact shows as a diff here
# (`MA13`'s idiom) rather than being silently inherited.
PUBLISHED_COSTS = {
    "net_ann": 0.23308954898392242,
    "net_alpha": 0.06069654078141906,
    "equal_weight_ann": 0.17239300820250336,
    "net_sharpe": 1.0994339357566514,
    "net_max_drawdown": -0.28479315035703734,
    "annual_turnover": 2.6069687969064415,
    "realised_one_way_bps": 33.359867748008256,
}


def _data_root():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(_HERE, "data"))
    parts = _HERE.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    for c in out:
        if os.path.exists(os.path.join(c, "free_analysis", "panel_corrected_69d.pkl")):
            return c
    raise FileNotFoundError("no data root; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
OUT = os.path.join(FA, "INDEX_BOOK.json")

ARMS = [
    ("B_all_cap_equal", dict(large_cap_min=0.0, weighting="equal", exit_frac=None)),
    ("C_large_cap_equal", dict(large_cap_min=LARGE_CAP_MIN, weighting="equal", exit_frac=None)),
    ("D_large_cap_score", dict(large_cap_min=LARGE_CAP_MIN, weighting="score", exit_frac=None)),
    ("A_served", dict(large_cap_min=LARGE_CAP_MIN, weighting="score", exit_frac=BAND_WIDTH)),
]


def c1_fidelity(panel, cols, weights, expect_alpha=None):
    """GATED. Reproduce the landed record from the SHIPPED path or abort.

    The count is gated too: `MB21`'s `C1` once scored a perfect zero on an empty frame by
    comparing nothing.

    `expect_alpha` DEFAULTS TO `PUBLISHED_ALPHA`, so every existing caller is bit-identical.
    `CORRECTED-FLOORS` part 2 passes `UNIVERSE-BIAS` part 2's own `corrected` top-decile alpha
    instead, because that panel is legitimately NOT the object the published record describes --
    and the gate is NOT weakened by it: it still demands EXACT reproduction (`dev == 0.0`) of a
    figure measured and landed ELSEWHERE, on 69 dates, and it still aborts. Only WHICH landed
    figure is a parameter. A second script calling `IB.run` would have duplicated every arm and
    every block here, which is `B7`'s defect: two implementations of one measurement, free to
    drift.
    """
    from valuation.edge.fundamental_panel import quantile_backtest
    want = PUBLISHED_ALPHA if expect_alpha is None else float(expect_alpha)
    r = quantile_backtest(panel, cols, weights, n_q=10)
    got = r.get("top_decile_alpha")
    dev = abs(float(got) - want)
    n = int(r.get("n_periods") or 0)
    ok = (dev == 0.0) and n == 69
    return {"published": want, "reproduced": got, "max_abs_dev": dev,
            "expect_alpha_is_the_default": bool(expect_alpha is None),
            "n_periods": n, "pass": bool(ok)}


def _halves(series, key):
    xs = [p for p in series if p[key] == p[key]]
    k = len(xs) // 2
    return xs[:k], xs[k:]


def _half_stats(rows):
    if not rows:
        return None
    net = [r["net"] for r in rows]
    ew = [r["equal_weight"] for r in rows]
    tew = [r["tier_equal_weight"] for r in rows]
    spy = [r["spy"] for r in rows]
    return {"n": len(rows), "first": rows[0]["date"], "last": rows[-1]["date"],
            "net_ann": IB._ann(net), "equal_weight_ann": IB._ann(ew), "spy_ann": IB._ann(spy),
            "tier_equal_weight_ann": IB._ann(tew),
            "net_alpha_vs_equal_weight": IB._ann(net) - IB._ann(ew),
            "net_alpha_vs_tier_equal_weight": (None if IB._ann(tew) is None
                                               else IB._ann(net) - IB._ann(tew)),
            "net_alpha_vs_spy": IB._ann(net) - IB._ann(spy),
            "net_sharpe": IB._sharpe(net), "net_max_drawdown": IB._mdd(net),
            "annual_turnover": float(np.mean([r["turnover_two_way"] for r in rows])) / 2.0 * 4.0}


def main(panel_path=None, out=None, label=None, expect_alpha=None) -> int:
    """`panel_path`/`out`/`expect_alpha` all default to the banked panel, this item's own
    artifact and the published alpha, so every existing caller is bit-identical.
    `UNIVERSE-BIAS` passes a corrected-universe panel rather than copying this measurement
    (`B7`), and `CORRECTED-FLOORS` part 2 passes that panel's OWN landed alpha as the gate's
    target so the gate keeps its full strength on a second object."""
    panel = pd.read_pickle(panel_path or os.path.join(FA, "panel_corrected_69d.pkl"))
    cols = list(DEPLOYED)
    weights = {c: BASE_WEIGHT for c in cols}
    print("panel %s | %d dates | %d names | %d themes at %.4f"
          % (panel.shape, panel["date"].nunique(), panel["ticker"].nunique(),
             len(cols), BASE_WEIGHT), flush=True)

    c1 = c1_fidelity(panel, cols, weights, expect_alpha=expect_alpha)
    print("C1 fidelity: published %.17f reproduced %.17f dev %.3e n %d -> %s"
          % (c1["published"], c1["reproduced"], c1["max_abs_dev"], c1["n_periods"],
             "PASS" if c1["pass"] else "FAIL"), flush=True)
    if not c1["pass"]:
        raise SystemExit("C1 FAILED -- the panel is not the object the record describes; abort")

    res = {"item": "INDEX-BOOK", "trials": 0,
           "object_label": label or "the published 2,531-name panel (the banked object)",
           "panel": panel_path or "data/free_analysis/panel_corrected_69d.pkl",
           "trial_class": "FIXED -- reproduction of a shipped construction, no bar, no verdict",
           "C1_fidelity": c1,
           "constants_source": "valuation/edge/valquo_index.py + no_trade_band.BAND_WIDTH",
           "ten_billion_applied": "NOMINAL, exactly as live -- market_cap >= 10e9, no inflation "
                                  "adjustment anywhere on the path",
           "arms": {}}

    for name, kw in ARMS:
        print("\n=== %s  %s" % (name, kw), flush=True)
        a = IB.run(panel, cols, weights, **kw)
        e, l = _halves(a["series"], "net")
        a["early_half"] = _half_stats(e)
        a["late_half"] = _half_stats(l)
        res["arms"][name] = a
        print("  net %.4f  ew %.4f  tier_ew %.4f  spy %.4f"
              % (a["net_ann"], a["equal_weight_ann"], a["tier_equal_weight_ann"],
                 a["spy_ann"]), flush=True)
        print("  alpha_ew %+.4f  alpha_TIER_ew %+.4f  alpha_spy %+.4f  (tier mirror verified "
              "on %d/%d dates)"
              % (a["net_alpha_vs_equal_weight"], a["net_alpha_vs_tier_equal_weight"],
                 a["net_alpha_vs_spy"], a["tier_mirror_verified_on_dates"],
                 a["n_periods"]), flush=True)
        print("  sharpe %.4f  maxDD %.4f  turnover %.4f  book %d/%.0f/%d  tier %d/%.0f/%d"
              % (a["net_sharpe"], a["net_max_drawdown"], a["annual_turnover"],
                 a["book_size"]["min"], a["book_size"]["median"], a["book_size"]["max"],
                 a["eligible_tier"]["min"], a["eligible_tier"]["median"],
                 a["eligible_tier"]["max"]), flush=True)
        print("  tilt %r | fallback dates %d | unlabelled %d | cap binds %d | eff caps %r"
              % (a["tilt_values"], a["dates_on_the_fallback"], a["dates_with_no_tilt_label"],
                 a["cap_binds_on_dates"], a["effective_cap_values"][:4]), flush=True)
        print("  realised %.2f bps one-way | cost drag %.4f | below contract min(%d) on %d/%d"
              % (a["realised_one_way_bps"], a["cost_drag_ann"],
                 a["contract_min_positions"], a["dates_below_contract_min_positions"],
                 a["n_periods"]), flush=True)
        print("  halves vs all-cap ew : early %+.4f | late %+.4f"
              % (a["early_half"]["net_alpha_vs_equal_weight"],
                 a["late_half"]["net_alpha_vs_equal_weight"]), flush=True)
        print("  halves vs OWN tier ew: early %+.4f | late %+.4f"
              % (a["early_half"]["net_alpha_vs_tier_equal_weight"],
                 a["late_half"]["net_alpha_vs_tier_equal_weight"]), flush=True)

    A, B = res["arms"]["A_served"], res["arms"]["B_all_cap_equal"]
    res["served_minus_all_cap_decile"] = {
        k: A[k] - B[k] for k in ("net_ann", "net_alpha_vs_equal_weight", "net_alpha_vs_spy",
                                 "net_sharpe", "net_max_drawdown", "annual_turnover")}
    # THE DECOMPOSITION THAT STOPS THE HEADLINE BEING MISREAD. The all-cap-vs-all-cap and
    # large-cap-vs-large-cap alphas are both "does the composite sort its own universe"; the
    # residual is the size premium the tier gives up, which is a property of the UNIVERSE and
    # not of the signal.
    res["tier_step_split"] = {
        "all_cap_decile_alpha_within_its_universe": B["net_alpha_vs_equal_weight"],
        "served_alpha_within_its_own_tier": A["net_alpha_vs_tier_equal_weight"],
        "signal_component": (A["net_alpha_vs_tier_equal_weight"]
                             - B["net_alpha_vs_equal_weight"]),
        "universe_component": (A["net_alpha_vs_equal_weight"]
                               - A["net_alpha_vs_tier_equal_weight"]),
        "universe_component_is": "the $10B tier's own equal-weighted return minus the all-cap "
                                 "universe's -- the size premium the tier declines to hold, a "
                                 "fact about the universe rather than about the composite",
    }
    res["one_knob_decomposition"] = {
        "tier_10bn": res["arms"]["C_large_cap_equal"]["net_alpha_vs_equal_weight"]
                     - B["net_alpha_vs_equal_weight"],
        "score_weight_and_cap": res["arms"]["D_large_cap_score"]["net_alpha_vs_equal_weight"]
                                - res["arms"]["C_large_cap_equal"]["net_alpha_vs_equal_weight"],
        "no_trade_band": A["net_alpha_vs_equal_weight"]
                         - res["arms"]["D_large_cap_score"]["net_alpha_vs_equal_weight"],
        "note": "each step is ONE knob; they sum to served minus all-cap-equal by construction",
    }
    # CONTROL, REPORTED NOT GATED. `B` is not the published decile's construction (`array_split`
    # vs `round(n * 0.10)`, and a different compounding), so requiring equality would be
    # requiring two different objects to agree. Reporting the deviations is what licenses the
    # decomposition: if `B` landed nowhere near `costs.top_decile`, every arm beside it would be
    # measured on machinery that does not reproduce the record, and the one-knob reading would
    # be worthless.
    res["control_B_vs_published_decile"] = {
        "published": PUBLISHED_COSTS,
        "reproduced": {"net_ann": B["net_ann"], "net_alpha": B["net_alpha_vs_equal_weight"],
                       "equal_weight_ann": B["equal_weight_ann"],
                       "net_sharpe": B["net_sharpe"],
                       "net_max_drawdown": B["net_max_drawdown"],
                       "annual_turnover": B["annual_turnover"],
                       "realised_one_way_bps": B["realised_one_way_bps"]},
        "abs_dev": {k: abs(v - {"net_ann": B["net_ann"],
                                "net_alpha": B["net_alpha_vs_equal_weight"],
                                "equal_weight_ann": B["equal_weight_ann"],
                                "net_sharpe": B["net_sharpe"],
                                "net_max_drawdown": B["net_max_drawdown"],
                                "annual_turnover": B["annual_turnover"],
                                "realised_one_way_bps": B["realised_one_way_bps"]}[k])
                    for k, v in PUBLISHED_COSTS.items()},
        "note": "a REFERENCE, not a fidelity gate -- C1 is the gate, and it is exact",
    }
    res["live_book_reconciliation"] = {
        "live_book_positions": 86,
        "panel_late_date_book_size": A["series"][-1]["n_book"],
        "panel_late_date_eligible_tier": A["series"][-1]["n_eligible"],
        "note": "the panel's most recent cross-section produces a book of this size from a tier "
                "of this size; the live scan's universe is not the panel's, so this is a "
                "sanity reconciliation and not an identity",
    }
    # THE CONSEQUENCE FOR THE CONTRACT, AND IT IS WHY THE MATCHED PAIRING MATTERS.
    #
    # The meter's sigma is the FULL-UNIVERSE decile's tracking error vs SPY (11.40 pp/yr,
    # inflated by `R9`'s autocorrelation design effect). Pairing that sigma with the SERVED
    # book's edge would be a numerator from one book against a denominator from another --
    # `MA19`'s own recurring defect, and `MB8`'s rule that an `se` may not be borrowed across
    # constructions. So each arm's months-to-detect is computed from ITS OWN measured tracking
    # error, with the meter's `boundary` IMPORTED and its live constants untouched (`V1`: one
    # boundary function in the project). `boundary`'s own docstring licenses the sigma argument
    # for exactly this -- probing other values -- and explicitly not for retuning the meter.
    # INDEX-BOOK-AMEND: THE SAME BOOK IN BOTH TAX TREATMENTS, from ONE function and ONE lot
    # path. The Roth/IRA figure is the taxable run with both rates set to ZERO -- not a second
    # code path -- so the tax cost is a clean difference on an identical book, identical lots and
    # identical trades. A separate no-tax implementation would make the difference the gap
    # between two constructions, which is `B7`'s defect and invisible to inspection.
    #
    # The caveat travels with the number because it runs AGAINST the taxable arm: the panel's
    # forward returns carry NO dividends, so dividend income is absent from the gross figure and
    # dividend TAX is absent from this one. Consistent, and it understates a real taxable
    # investor's drag -- most of all for a large-cap book, which is the higher-yielding end of
    # the universe. `after_tax_backtest`'s own docstring says so and it is repeated here rather
    # than left in a module a reader of this artifact will not open.
    print("\n=== tax treatments (served construction, one lot path)", flush=True)
    _bf = IB.book_fn(large_cap_min=LARGE_CAP_MIN, weighting="score", exit_frac=BAND_WIDTH)
    tax = {}
    for lab, rates in (("taxable", (TAX_SHORT, TAX_LONG)), ("roth_ira", (0.0, 0.0))):
        r = at_backtest(panel, cols, weights, top_frac=0.1, exit_frac=BAND_WIDTH,
                        short_rate=rates[0], long_rate=rates[1], book_fn=_bf)
        tax[lab] = r
        print("  %-9s gross %.4f  after_tax %.4f  alpha %+.4f  sharpe %.4f  maxDD %.4f"
              % (lab, r["gross_ann"], r["after_tax_ann"], r["after_tax_alpha"],
                 r["after_tax_sharpe"], r["after_tax_max_drawdown"]), flush=True)
    res["tax_treatments"] = {
        "taxable": tax["taxable"], "roth_ira": tax["roth_ira"],
        "short_rate": TAX_SHORT, "long_rate": TAX_LONG,
        "tax_cost_pp_per_year": (tax["roth_ira"]["after_tax_ann"]
                                 - tax["taxable"]["after_tax_ann"]),
        "roth_is": "the identical run with both tax rates set to ZERO -- net of the modelled "
                   "costs, no tax; NOT a second code path",
        "short_term_share_of_gains": tax["taxable"]["short_term_share_of_gains"],
        "no_dividends": "the panel's forward returns are price-only, so dividend income AND "
                        "dividend tax are both absent -- which understates the taxable drag, "
                        "most of all for a large-cap book",
        "lot_method": tax["taxable"]["lot_method"],
    }
    # A CONTROL ON THE ZERO-RATE ARM, because a tax figure that reads zero is exactly the shape
    # that passes vacuously. If the taxable arm realised no gains at all, both arms would agree
    # and the "tax cost" would be zero for the wrong reason.
    res["tax_treatments"]["control_taxable_arm_actually_paid_tax"] = bool(
        (tax["taxable"]["tax_paid_short"] + tax["taxable"]["tax_paid_long"]) > 0
        and (tax["roth_ira"]["tax_paid_short"] + tax["roth_ira"]["tax_paid_long"]) == 0)

    res["contract_power_input"] = {
        "in_use_today": PUBLISHED_SPY_EXCESS,
        "in_use_today_is": "the FULL-UNIVERSE equal-weighted decile, GROSS of costs, vs SPY",
        "meter_sigma_monthly_pp": tm.SIGMA_MONTHLY_PP,
        "meter_sigma_is": "the full-universe decile's own tracking error; matched only to the "
                          "all-cap arm",
        "arms": {},
    }
    for nm in ("B_all_cap_equal", "A_served"):
        a = res["arms"][nm]
        ex = np.array([p["net"] - p["spy"] for p in a["series"]
                       if p["net"] == p["net"] and p["spy"] == p["spy"]], dtype=float)
        te_ann_pp = float(ex.std(ddof=1) * np.sqrt(4.0) * 100.0)
        sig = te_ann_pp / np.sqrt(12.0) * np.sqrt(tm._DESIGN_EFFECT)
        edge = a["net_alpha_vs_spy"] * 100.0
        months = None
        for k in range(1, 6001):
            if tm.boundary(k, sigma=sig) / k * 12.0 <= edge:
                months = k
                break
        res["contract_power_input"]["arms"][nm] = {
            "net_edge_vs_spy_pp_per_year": edge,
            "tracking_error_vs_spy_pp_per_year": te_ann_pp,
            "own_sigma_monthly_pp": float(sig),
            "months_to_detect_at_own_sigma": months,
            "years_to_detect": (None if months is None else months / 12.0),
            "note": "matched pair -- this arm's edge against this arm's own tracking error",
        }
    # a run on a non-default panel must SAY so in its own artifact, or a reader of
    # the file cannot tell which universe it describes.
    res["panel"] = os.path.basename(panel_path or "panel_corrected_69d.pkl")
    res["universe_label"] = label or "incumbent data/backtest universe"
    dest = out or OUT
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nserved minus all-cap decile:", json.dumps(res["served_minus_all_cap_decile"],
                                                       indent=1))
    print("decomposition:", json.dumps(res["one_knob_decomposition"], indent=1))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
