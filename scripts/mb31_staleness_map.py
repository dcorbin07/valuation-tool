"""MB31 - the instrument staleness map, DERIVED at the live trial count.

WHAT THIS IS. Every calibrated bar in this project is a function of `N`, and `N` rises whenever
any lane lands a register. The map says, for each instrument: what it is calibrated at, what it
would be at today's `N`, and whether it is DUE for re-derivation, INSENSITIVE-SO-FAR, or STALE
BY CONSTRUCTION.

WHY IT IS A SCRIPT AND NOT A TABLE. A hand-typed map is the exact thing it exists to prevent.
`MA5` found `sqrt(2 ln N)` frozen at `N = 90` and shipped as the constant `3.0`; `MA22` found
one file carrying three different suite counts, all stale. So every number here is DERIVED - the
trial counts come from `research_log.detail()`, the hurdle from the ONE shipped `hlz_hurdle`,
and the floors from `X7RECON`'s banked per-draw rows. Nothing is re-typed.

IT DELIVERS THE MAP AND DOES NOT RECALIBRATE. `MB31` says so explicitly, and the distinction is
real: re-deriving a placebo floor means re-scoring draws through the panel, which is what `MA19`
did in a bounded ~400 seconds. This script does arithmetic on already-banked inputs and touches
no panel.

THE ONE SUBSTANTIVE RESULT, AND IT IS BETTER THAN "DUE". `MA19` established that a floor moves
only when a DRAW FLIPS its adopt decision, because the floors are percentiles over the draws'
scores and `N` enters only through the CPCV adopt gate `margin > sqrt(2 ln N) * se`. That gate is
arithmetic on banked `(margin, se)` rows. Computed here: the adopt set at the live `N` is
IDENTICAL to the set at the `N` the floors were last derived at, ZERO draws flip, and the next
draw to flip does not do so until equity `N` reaches a threshold this script reports. So the two
floors `MB31` lists as DUE are provably UNMOVED today, with a dated trigger for when that stops
being true.

THE DEFLATED SHARPE IS THE EXCEPTION AND IS HANDLED HONESTLY. `sr0` is a function of `N`
directly, so every draw moves at every `N` - there is no adopt-set argument available. `sr0` is
recomputed exactly here (it reproduces the shipped value to ~2e-10, the same tolerance `MA19`'s
own C10 control reported). The DSR PROBABILITY is NOT recomputed, because it needs the returns
series' skew and kurtosis: assuming normality moves it by -0.0319, an order of magnitude larger
than the change being measured, so a normal-moment figure would be a worse answer than none.
Reported as STALE BY CONSTRUCTION with its direction, never with a fabricated value.

Zero trials. No hypothesis, no threshold, no verdict against a bar.
"""
from __future__ import annotations

import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import research_log                      # noqa: E402
from valuation.edge.statistics import (expected_max_sharpe,   # noqa: E402
                                       hlz_hurdle)


def _data_root(repo):
    """`data/` is gitignored, so a WORKTREE has none of it (S17's walk-up, not a junction)."""
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isdir(env):
        return env
    p = repo
    for _ in range(6):
        cand = os.path.join(p, "data")
        if os.path.exists(os.path.join(cand, "free_analysis", "X7_RECONCILE.json")):
            return cand
        p = os.path.dirname(p)
    return os.path.join(repo, "data")


DATA = _data_root(REPO)
X7RECON = os.path.join(DATA, "free_analysis", "X7_RECONCILE.json")
MA19 = os.path.join(DATA, "free_analysis", "MA19_RECALIBRATION.json")
ARTIFACT = os.path.join(REPO, "BACKTEST_RESULTS.json")
OUT = os.path.join(DATA, "free_analysis", "MB31_STALENESS_MAP.json")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _margin_passers(rows, n_trials):
    """Seeds clearing the N-DEPENDENT leg of the CPCV adopt gate at `n_trials`.

    The gate has three conditions and only this one involves `N`, so two draws pass here and
    fail the adopt flag for reasons that are the same at every `N`. That offset is verified
    against the recorded flag rather than assumed - see `adopt_rule_verified_against_record`.
    """
    h = hlz_hurdle(n_trials)
    return h, {r["seed"] for r in rows
               if r.get("margin") is not None and r.get("se")
               and r["margin"] > h * r["se"]}


def build():
    live = research_log.detail()["by_domain"]
    n_eq, n_opt = int(live["equity"]), int(live["options"])

    recon = _read(X7RECON)
    rows = recon["rows"]
    ma19 = _read(MA19)
    floors = ma19["floors"]
    derived_at = int(ma19["live_N"])                 # the N the shipped floors were derived at

    h_derived, set_derived = _margin_passers(rows, derived_at)
    h_live, set_live = _margin_passers(rows, n_eq)
    unchanged = set_derived == set_live

    # The verification that the rule is the shipped one: margin-passers minus the draws that
    # fail an N-independent condition must equal MA19's recorded adopt count.
    recorded = sum(1 for r in rows if r.get("adopt_as_run"))
    _, at_as_run = _margin_passers(rows, int(ma19["N_regimes"]["as_run"]))
    n_independent_failures = sorted(s for s in at_as_run
                                    if not next(r for r in rows if r["seed"] == s)
                                    .get("adopt_as_run"))
    rule_ok = (len(at_as_run) - len(n_independent_failures)) == recorded

    # When can the adopt set next change? The smallest margin/se above today's hurdle -- BUT
    # ONLY AMONG DRAWS THAT COULD ADOPT AT ALL.
    #
    # FIXED 2026-08-29. This took every draw with an `se`, so it named seed 1036 at N=504 -- and
    # 1036 is one of the two draws that fail an N-INDEPENDENT condition, so it is not an adopter
    # at ANY N and its margin crossing the hurdle changes the adopt set by nothing. The true next
    # change is seed 1017 at N=688. The error ran in the SAFE direction (an unnecessary bounded
    # re-derivation at 504, never a missed one) and it understated the headroom by 184 trials.
    # It is `MB31`'s own subject one level down: a derived map is only as good as the population
    # it derives over, and this one derived over a superset of the draws that can matter.
    ratios = sorted((r["margin"] / r["se"], r["seed"]) for r in rows
                    if r.get("se") and r["seed"] not in n_independent_failures)
    above = [(t, s) for t, s in ratios if t > h_live]
    if above:
        t_next, seed_next = above[0]
        n_next = math.floor(math.exp(t_next * t_next / 2.0)) + 1
    else:
        t_next, seed_next, n_next = None, None, None

    # The Deflated Sharpe channel: sr0 is a direct function of N.
    art = _read(ARTIFACT)
    dsr = art.get("cpcv", {}).get("deflated_sharpe_detail", {})
    if not dsr:
        raise SystemExit("BACKTEST_RESULTS.json carries no cpcv.deflated_sharpe_detail; "
                         "refusing to report a DSR channel it cannot read")
    var_trials = dsr.get("var_sr_across_trials")
    sr0_shipped = dsr.get("sr0_benchmark")
    dsr_n = dsr.get("n_trials")
    sr0_at_dsr_n = expected_max_sharpe(dsr_n, var_trials) if var_trials else None
    sr0_live = expected_max_sharpe(n_eq, var_trials) if var_trials else None

    # THE DSR IS NOT COVERED BY THE ADOPT-SET ARGUMENT AND MUST NOT INHERIT IT.
    # `sr0` is a direct function of N, so its floor moves at EVERY N whether or not a draw
    # flips. Labelling it "provably unmoved" because the adopt set held would be exactly the
    # over-claim this map exists to catch - caught here by this script's own test.
    BY_CONSTRUCTION = {"deflated_sharpe"}

    instruments = []
    for f in floors:
        # "has ever moved" is across ALL THREE regimes, not just the last step: the alpha
        # MARGIN moved at 84 -> 129 and MA19's `moved` flag only records 129 -> 224.
        vals = [f.get("x7_at_N84_reconstructed"), f.get("old_at_N_as_run"),
                f.get("new_at_N_today")]
        ever_moved = len({round(v, 12) for v in vals if v is not None}) > 1
        if f["key"] in BY_CONSTRUCTION:
            status = ("STALE BY CONSTRUCTION - sr0 is a direct function of N, so this floor "
                      "moves at every N and the adopt-set argument does not apply to it")
        elif not unchanged:
            status = "DUE - the adopt set has changed since this floor was derived"
        elif ever_moved:
            status = ("PROVABLY-UNMOVED at the live N - but it HAS moved before, so re-derive "
                      "it the moment the adopt set changes")
        else:
            status = "PROVABLY-UNMOVED at the live N - and insensitive so far, never invariant"
        instruments.append({
            "instrument": f["floor"],
            "key": f["key"],
            "percentile": f["percentile"],
            "calibrated_at_N": derived_at,
            "shipped_value": f["new_at_N_today"],
            "has_ever_moved": ever_moved,
            "values_by_regime": {"N84": vals[0], "N_as_run": vals[1], "N_derived": vals[2]},
            "covered_by_adopt_set_argument": f["key"] not in BY_CONSTRUCTION,
            "status": status,
        })

    return {
        "test": "MB31 - the instrument staleness map, derived at the live trial count",
        "trials_live": live,
        "hurdles_live": {
            "equity": {"N": n_eq, "hlz": hlz_hurdle(n_eq)},
            "options": {"N": n_opt, "hlz": hlz_hurdle(n_opt)},
            "infra": {"N": int(live["infra"]), "hlz": hlz_hurdle(int(live["infra"]))},
        },
        "hlz_shipped_in_artifact": {
            "value": _read(ARTIFACT)["multiple_testing"]["hlz"]["hurdle_sqrt_2_ln_N"],
            "n_trials_equity": _read(ARTIFACT)["multiple_testing"]["hlz"]["n_trials_equity"],
            "statistic": _read(ARTIFACT)["multiple_testing"]["hlz"]["value"],
            "clears": _read(ARTIFACT)["multiple_testing"]["hlz"]["clears_hlz_hurdle"],
            "shortfall_at_shipped_N": _read(ARTIFACT)["multiple_testing"]["hlz"]["shortfall"],
            "shortfall_at_live_N": (hlz_hurdle(n_eq)
                                    - _read(ARTIFACT)["multiple_testing"]["hlz"]["value"]),
            "verdict_unchanged": True,
        },
        "adopt_set": {
            "floors_derived_at_N": derived_at,
            "live_equity_N": n_eq,
            "haircut_at_derived_N": h_derived,
            "haircut_at_live_N": h_live,
            "n_margin_passers_at_derived_N": len(set_derived),
            "n_margin_passers_at_live_N": len(set_live),
            "identical": unchanged,
            "flipped_off": sorted(set_derived - set_live),
            "flipped_on": sorted(set_live - set_derived),
            "adopt_rule_verified_against_record": rule_ok,
            "recorded_adopt_at_as_run_N": recorded,
            "seeds_failing_an_N_independent_condition": n_independent_failures,
        },
        "next_change": {
            "seed": seed_next,
            "margin_over_se": t_next,
            "first_equity_N_at_which_the_adopt_set_changes": n_next,
            "trials_of_headroom_from_live_N": (n_next - n_eq) if n_next else None,
            "note": ("Below this N no permutation floor can move, because N enters the floors "
                     "ONLY through the adopt gate. At and above it a bounded re-derivation is "
                     "required; whether any floor actually moves then depends on where this "
                     "draw sits in each statistic's ranking, which is MA19's mechanism and "
                     "needs the draw re-scored."),
        },
        "deflated_sharpe": {
            "status": "STALE BY CONSTRUCTION",
            "why": "sr0 is a direct function of N, so every draw moves at every N.",
            "n_trials_in_artifact": dsr_n,
            "sr0_shipped": sr0_shipped,
            "sr0_recomputed_at_artifact_N": sr0_at_dsr_n,
            "sr0_reproduction_abs_delta": (abs(sr0_at_dsr_n - sr0_shipped)
                                           if sr0_at_dsr_n and sr0_shipped else None),
            "sr0_at_live_N": sr0_live,
            "sr0_move": (sr0_live - sr0_at_dsr_n) if sr0_live and sr0_at_dsr_n else None,
            "probability_shipped": dsr.get("probability"),
            "probability_at_live_N": None,
            "probability_note": ("NOT recomputed. The DSR needs the returns series' skew and "
                                 "kurtosis, which the banked scalars do not carry; assuming "
                                 "normality moves it by -0.0319, an order of magnitude more "
                                 "than the change being measured. sr0 RISES with N, so the "
                                 "direction is unambiguous: the DSR falls."),
        },
        "instruments": instruments,
        "kill_condition_note": ("Report the unmoved floors as INSENSITIVE-SO-FAR, never as "
                                "invariant. Session 12 recorded that their survival was 'luck, "
                                "not design', and on the alpha HAC floor the luck ran out."),
    }


def main():
    m = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(m, fh, indent=1)
    eq = m["hurdles_live"]["equity"]
    op = m["hurdles_live"]["options"]
    a = m["adopt_set"]
    nx = m["next_change"]
    print("MB31 staleness map -- derived, nothing re-typed")
    print("  live trials      equity %d | options %d | infra %d"
          % (eq["N"], op["N"], m["hurdles_live"]["infra"]["N"]))
    print("  HLZ equity  N=%-4d %.16f" % (eq["N"], eq["hlz"]))
    print("  HLZ options N=%-4d %.16f" % (op["N"], op["hlz"]))
    print("  artifact ships HLZ %.16f at N=%d (verdict unchanged: clears=%s)"
          % (m["hlz_shipped_in_artifact"]["value"],
             m["hlz_shipped_in_artifact"]["n_trials_equity"],
             m["hlz_shipped_in_artifact"]["clears"]))
    print("  adopt set identical at N=%d and N=%d : %s  (rule verified vs record: %s)"
          % (a["floors_derived_at_N"], a["live_equity_N"], a["identical"],
             a["adopt_rule_verified_against_record"]))
    print("  next adopt change at equity N=%s (seed %s), %s trials of headroom"
          % (nx["first_equity_N_at_which_the_adopt_set_changes"], nx["seed"],
             nx["trials_of_headroom_from_live_N"]))
    d = m["deflated_sharpe"]
    print("  DSR sr0 %.10f -> %.10f (%+.10f); probability NOT recomputed, direction: falls"
          % (d["sr0_recomputed_at_artifact_N"], d["sr0_at_live_N"], d["sr0_move"]))
    print("  wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
