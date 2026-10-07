# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 1 -- the seven X7 floors, calibrated on the CORRECTED universe.

**ZERO TRIALS.** A calibration searches nothing: it measures what this pipeline reports when the
signal is definitionally worthless, so it can only ever raise or lower a BAR and never produce a
finding. `X7` charged nothing, session 10 charged nothing, `MA19` charged nothing, and the reason
is the same each time -- and `MA19`'s is sharper still, because `N` is the INPUT to the floors
being computed, so charging a trial would move `N` and invalidate the numbers as they were
written.

**WHAT IS AND IS NOT NEW HERE.** The sweep is `scripts/placebo.py`, unchanged, at the same seeds
(1000..1099), the same `n`, the same instrument and with costs measured -- exactly as `X7` and
session 10 ran it. **The only thing that differs is the universe.** This module does no
measurement at all: it reads the sweep's retained draws and tabulates them against the floors
that govern today, which are themselves DERIVED from `MB31`'s map rather than typed.

**THE COMPARATOR IS DERIVED, NEVER QUOTED.** `MB31`'s staleness map answers "what are the floors
at the live `N`" arithmetically from the banked `(margin, se)` rows, and this file calls it. That
matters because the canonical floors are a STEP FUNCTION of `N`: `W-1` re-derived three of them at
`N`=247 when seed 1003 flipped, and a table of hand-typed figures goes stale the next time a lane
books a trial.

**NOTHING IS ADOPTED AND NO PUBLIC PAGE CHANGES**, pinned by test. Whether the canonical panel
moves to the corrected universe is Don's and is pending (`DECISIONS.md`, 2026-10-07).
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# NOT CALLED AT IMPORT TIME. `_data_root` RAISES without the banked panel, and `data/` is
# gitignored -- so a module-level call takes every suite that imports this file down on a CI
# runner. This file's own test suite says so in its docstring and I wrote it this way anyway;
# the guard that would have caught it now exists ("guards that fail open in CI", one level up).
from scripts.index_best import _data_root                                   # noqa: E402


def fa():
    """`data/free_analysis`, resolved on CALL."""
    return os.path.join(_data_root(), "free_analysis")


def sweep_path():
    return os.path.join(fa(), "PLACEBO_CORRECTED.json")


def out_path():
    return os.path.join(fa(), "CORRECTED_FLOORS.json")

#: The seven floors, each named by the sweep key it is read off and the percentile that defines
#: it. These are `X7`'s own definitions -- the key and the tail, not a re-derivation of either.
#: `pbo` is the ONLY one read off the LOW tail, because a low PBO is the good direction.
FLOORS = (
    ("max_abs_theme_ic_t",        "theme IC t",             "p95", "higher is harder"),
    ("long_short_tstat",          "long-short naive t",     "p95", "higher is harder"),
    ("long_short_tstat_nw",       "long-short HAC t",       "p95", "higher is harder"),
    ("top_decile_alpha",          "top-decile alpha margin", "p95", "higher is harder"),
    ("top_decile_alpha_tstat_nw", "top-decile alpha HAC t", "p95", "higher is harder"),
    ("pbo",                       "PBO",                    "p05", "LOWER is harder"),
    ("deflated_sharpe",           "Deflated Sharpe",        "p95", "higher is harder"),
)

#: A sweep this far short of its requested draws cannot carry a p95: the 95th percentile of 20
#: draws is set by the single largest value. `X7` ran 100 and so does this; a partial read is
#: reported as PARTIAL rather than quoted as a floor.
MIN_DRAWS_FOR_A_FLOOR = 100


def current_floors():
    """The floors that govern TODAY, derived from `MB31`'s map rather than typed.

    `B7`: the map is the one definition of "which `N` were these derived at and are they still
    current", and it is CALLED. Re-typing its table here is how the record came to carry a
    1.95pp alpha margin for nine days after the sweep that superseded it.
    """
    from scripts.mb31_staleness_map import build
    m = build()
    rows = {i["key"]: i for i in m["instruments"]}
    return {
        "derived_at_N": m["adopt_set"]["floors_derived_at_N"],
        "derived_at_N_source": m["adopt_set"].get("floors_derived_at_N_source"),
        "live_equity_N": m["adopt_set"]["live_equity_N"],
        "adopt_set_identical": m["adopt_set"]["identical"],
        "next_adopt_change": m.get("next_change"),
        "floors": {k: {"value": v["shipped_value"], "status": v["status"],
                       "has_ever_moved": v["has_ever_moved"]} for k, v in rows.items()},
    }


def read_sweep(path=None):
    path = path or sweep_path()
    if not os.path.exists(path):
        raise SystemExit("REFUSING: no sweep at %s. Run scripts/placebo_corrected.bat first -- "
                         "this module tabulates a sweep and measures nothing itself." % path)
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def harness_control(sweep, landed):
    """Does the sweep's REAL (unpermuted) iteration reproduce the landed corrected figures?

    This is what licenses every floor below. `placebo.py` runs the real panel through the
    IDENTICAL code path as each draw, so if the two disagree the gap is a harness bug rather
    than a finding -- `X7`'s own reasoning, and `MA28`'s `C1` is why it is GATED and not merely
    reported.

    The Deflated Sharpe is expected to DIFFER and is scored separately: `sr0` is a direct
    function of the trial count, so every DSR moves at every `N` (`MB31`). It is reconciled by
    re-deriving it at the landed figure's own `N` from the sweep's banked internals, which is
    arithmetic rather than a tolerance.
    """
    real = sweep["real"]
    exact, out = [], {}
    for k, want in landed.items():
        got = real.get(k)
        dev = (None if got is None or want is None else abs(float(got) - float(want)))
        out[k] = {"landed": want, "reproduced": got, "abs_dev": dev,
                  "exact": bool(dev == 0.0)}
        if k != "deflated_sharpe":
            exact.append(dev == 0.0)
    out["_gate"] = {
        "keys_compared": len(exact),
        "all_exact_excluding_dsr": bool(exact) and all(exact),
        "note": "the Deflated Sharpe is EXCLUDED from the gate and reconciled separately -- "
                "sr0 is a direct function of N and the landed figure was computed at a "
                "different trial count",
    }
    return out


def dsr_at_n(detail, n_trials, implied_denominator):
    """Re-derive the Deflated Sharpe at an arbitrary trial count from banked internals.

    `MA19` banked `(sharpe, var_sr, n_trials)` per draw precisely so a re-denomination is
    arithmetic and never a re-run. The skew/kurtosis denominator is not banked, so it is
    recovered from the sweep's OWN reported probability and then held fixed -- which makes this
    a test of the `N` channel ALONE rather than a reimplementation of the statistic.
    """
    from valuation.edge.fundamental_panel import _ncdf, _nppf
    emc = 0.5772156649015329
    var = float(detail["var_sr_across_trials"])
    sr = float(detail["sharpe_per_period"])
    n = int(detail["n_periods"])
    sr0 = (var ** 0.5) * ((1 - emc) * _nppf(1 - 1.0 / n_trials)
                          + emc * _nppf(1 - 1.0 / (n_trials * math.e)))
    z = (sr - sr0) * ((n - 1) ** 0.5) / (implied_denominator ** 0.5)
    return {"n_trials": n_trials, "sr0": float(sr0), "dsr": float(_ncdf(z))}


def implied_denominator(detail):
    """The skew/kurtosis denominator implied by the sweep's own reported DSR."""
    from valuation.edge.fundamental_panel import _nppf
    emc = 0.5772156649015329
    var = float(detail["var_sr_across_trials"])
    sr = float(detail["sharpe_per_period"])
    n = int(detail["n_periods"])
    N = int(detail["n_trials"])
    sr0 = (var ** 0.5) * ((1 - emc) * _nppf(1 - 1.0 / N) + emc * _nppf(1 - 1.0 / (N * math.e)))
    z = _nppf(float(detail["probability"]))
    return (((sr - sr0) * math.sqrt(n - 1)) / z) ** 2


def clears(value, floor, direction):
    """Does an observed value clear a floor? `None` when either side is missing -- NEVER False,
    because "could not be compared" and "failed" are different states and only one is a verdict.
    """
    if value is None or floor is None:
        return None
    return bool(value <= floor) if direction == "LOWER is harder" else bool(value >= floor)
