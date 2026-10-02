# -*- coding: utf-8 -*-
"""REBAL-CADENCE — the four cadence arms, built ONCE and consumed by both passes.

`B7`: the band, the cost table, the weight drift and the formation gate all live in the shipped
`turnover_and_costs`, which this module CALLS and never re-implements. What lives here is the
only thing that is genuinely study-side: which cadences to form, and how the four overlapping
sub-books of the staggered arm combine.

`MA23`: this is a study, so it sits under `valuation/studies/` and nothing under
`valuation/web/`, `valuation/saas/` or `valuation/screener/` may import it.

THE ARMS, and these and no others -- no grid:

  1. `quarterly`   cadence 1          the incumbent, and the control everything is paired against
  2. `semiannual`  cadence 2
  3. `annual`      cadence 4
  4. `staggered`   four cadence-4 sub-books at offsets 0..3, one re-formed each quarter

WHY THE STAGGERED ARM IS NOT JUST A FOURTH CADENCE. Jegadeesh-Titman overlapping portfolios
keep an annual HOLDING period while using EVERY quarter's signal, and they remove the one thing
a single-offset annual book cannot escape: `X2` measured the rebalance-date grid ALONE moving
the long-short *t* from 2.70 to 3.52 on this panel, so "annual, formed in January" is a
measurement about January as much as about annual. Arms 2 and 3 therefore carry timing-luck
exposure BY CONSTRUCTION and arm 4 does not, which is why the offset sweep ships as a labelled
diagnostic beside them.

WHY A FIXED-SIZE BOOK AND NOT NEVER-SELL. `S23` measured never-selling at -10.89pp/yr and
diagnosed it as DILUTION rather than friction: a book that keeps buying accumulates cohorts of
every age and converges on a 417-name slice of the universe. Every arm here re-forms a book of
the SAME size on its own clock, so holding longer cannot turn into holding more.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

ARMS = ("quarterly", "semiannual", "annual", "staggered")
INCUMBENT = "quarterly"

# cadence/offset spec per arm. The staggered arm is four sub-books rather than one.
SPEC: Dict[str, List[tuple]] = {
    "quarterly": [(1, 0)],
    "semiannual": [(2, 0)],
    "annual": [(4, 0)],
    "staggered": [(4, 0), (4, 1), (4, 2), (4, 3)],
}

PER_YEAR = 4.0          # the panel is quarterly; a period is one 63-day forward window


def _compound_ann(xs) -> Optional[float]:
    xs = [x for x in xs if x == x]
    if not xs:
        return None
    return float(np.prod([1.0 + x for x in xs]) ** (PER_YEAR / len(xs)) - 1.0)


def build_arm(panel, cols, weights, cadence_spec, *, top_frac=0.1, exit_frac=0.3,
              horizon=63, turnover_fn=None) -> dict:
    """One arm's per-period series, keyed on date so arms at different cadences can be paired.

    A sub-book that forms at offset j has no position before date j, so its series starts
    there. Combining sub-books therefore means intersecting their date sets, not assuming they
    all start together -- assuming it would silently score the first quarters of the staggered
    arm on fewer than four live sub-books and call it a four-book average.
    """
    if turnover_fn is None:                     # injected only so the tests can prove delegation
        from ..edge.fundamental_panel import turnover_and_costs as turnover_fn

    legs = []
    for cad, off in cadence_spec:
        r = turnover_fn(panel, cols, weights, top_frac=top_frac, exit_frac=exit_frac,
                        horizon=horizon, cadence=cad, offset=off, return_series=True)
        if not r or "series" not in r:
            raise RuntimeError("turnover_and_costs returned no series for cadence=%r offset=%r"
                               % (cad, off))
        s = r["series"]
        legs.append({"cadence": cad, "offset": off, "summary": r,
                     "by_date": dict(zip(s["dates"], s["net"])),
                     "gross_by_date": dict(zip(s["dates"], s["gross"])),
                     "ew_by_date": dict(zip(s["dates"], s["equal_weight"])),
                     "turn_by_date": dict(zip(s["dates"], s["turnover_two_way"]))})

    common = set(legs[0]["by_date"])
    for leg in legs[1:]:
        common &= set(leg["by_date"])
    dates = sorted(common)

    net = [float(np.mean([leg["by_date"][d] for leg in legs])) for d in dates]
    gross = [float(np.mean([leg["gross_by_date"][d] for leg in legs])) for d in dates]
    # The equal-weight universe is a property of the DATE, not of the book, so every leg
    # reports the same value and averaging them is a no-op -- taken from leg 0 and ASSERTED
    # equal rather than assumed, because a disagreement would mean the legs are not on one panel.
    ew = [float(legs[0]["ew_by_date"][d]) for d in dates]
    for leg in legs[1:]:
        for d in dates:
            a, b = leg["ew_by_date"][d], legs[0]["ew_by_date"][d]
            if (a == a) and (b == b) and abs(a - b) > 1e-12:
                raise RuntimeError("legs disagree on the equal-weight universe at %s" % d)
    turn = [float(np.mean([leg["turn_by_date"][d] for leg in legs])) for d in dates]

    return {"dates": dates, "net": net, "gross": gross, "equal_weight": ew,
            "turnover_two_way": turn, "n_legs": len(legs),
            "n_periods": len(dates),
            "legs": [{"cadence": l["cadence"], "offset": l["offset"],
                      "formation_dates": l["summary"].get("formation_dates"),
                      "held_only_periods": l["summary"].get("held_only_periods"),
                      "dropped_held_name_periods":
                          l["summary"].get("dropped_held_name_periods"),
                      "annual_turnover": l["summary"].get("annual_turnover"),
                      "realised_one_way_bps": l["summary"].get("realised_one_way_bps")}
                     for l in legs]}


def build_all(panel, cols, weights, **kw) -> dict:
    return {name: build_arm(panel, cols, weights, SPEC[name], **kw) for name in ARMS}


def paired_difference(arms: dict, name: str, incumbent: str = INCUMBENT) -> dict:
    """The per-period paired NET difference against the incumbent, on their COMMON dates.

    The equal-weight universe cancels out of a paired difference of net ALPHAS -- both arms
    are scored against the same per-date benchmark -- so `net_k - net_1` IS the paired alpha
    difference and no benchmark subtraction is needed. Stated because subtracting it twice is
    the obvious way to get this wrong.
    """
    a, b = arms[name], arms[incumbent]
    ad, bd = dict(zip(a["dates"], a["net"])), dict(zip(b["dates"], b["net"]))
    dates = sorted(set(ad) & set(bd))
    diff = [float(ad[d] - bd[d]) for d in dates]
    return {"dates": dates, "diff": diff, "n": len(diff)}


def common_dates(arms: dict) -> List[str]:
    """Every arm scored on ONE date set, so no comparison is partly a difference of windows."""
    s = None
    for a in arms.values():
        s = set(a["dates"]) if s is None else (s & set(a["dates"]))
    return sorted(s or [])


def restrict(arms: dict, dates) -> dict:
    keep = set(dates)
    out = {}
    for name, a in arms.items():
        idx = [i for i, d in enumerate(a["dates"]) if d in keep]
        out[name] = {**a,
                     "dates": [a["dates"][i] for i in idx],
                     "net": [a["net"][i] for i in idx],
                     "gross": [a["gross"][i] for i in idx],
                     "equal_weight": [a["equal_weight"][i] for i in idx],
                     "turnover_two_way": [a["turnover_two_way"][i] for i in idx],
                     "n_periods": len(idx)}
    return out


def annualised(series) -> Optional[float]:
    return _compound_ann(series)


def net_alpha_ann(arm: dict) -> Optional[float]:
    """Compounded net return minus compounded equal-weight return, the `turnover_and_costs`
    convention -- COMPOUNDING, not the arithmetic annualisation `quantile_backtest` uses. The
    two differ by about 2pp on this panel and its own docstring says so; mixing them is how a
    cost figure gets compared with a construction figure."""
    n, e = _compound_ann(arm["net"]), _compound_ann(arm["equal_weight"])
    return None if (n is None or e is None) else n - e
