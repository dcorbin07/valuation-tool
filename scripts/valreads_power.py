# -*- coding: utf-8 -*-
"""`VALREADS` step 0b — WHEN THIS DESIGN COULD RESOLVE, derived before it is registered.

    python -m scripts.valreads_power

`RUN_RULES` PART A rule 11: state the minimum detectable effect BEFORE the run and say which
one it is. A register that cannot detect its own hypothesis has already decided its answer, and
it decides it the flattering way. **Every figure here comes from
`valuation/edge/power_gate.py`** so the arithmetic is not retyped (`MA5`'s lesson: a second copy
of a bar is how one freezes).

**THE DISPERSION IS MEASURED, NOT ASSUMED.** A power figure resting on a guessed `sd(IC)` is an
assumption wearing a number. Per-date Spearman IC against `fwd_ret` on this project's own
corrected 9,645-name panel, 69 dates:

    read        mean IC    sd(IC)   null sd   ratio
    quality      0.0695    0.0872    0.0158    5.52
    growth       0.0110    0.0592    0.0166    3.56
    momentum     0.0417    0.1302    0.0158    8.22
    value        0.0547    0.1116    0.0156    7.15
    size        -0.0703    0.0941    0.0156    6.03

**The ratio is NOT the transferable number and treating it as one overstates the dispersion at a
smaller cross-section.** `sd(IC)^2 = true_var + 1/(N-1)`: the sampling term is tiny on a
4,106-name cross-section, so almost all of the measured dispersion is the signal's own movement
through time and is N-INDEPENDENT. The recorder's cross-section is ~542 names, so its sampling
term is larger and is added back explicitly.

**ZERO TRIALS.** A power derivation searches nothing.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import power_gate as PG                                 # noqa: E402

#: MEASURED on the corrected panel (see the docstring). `(mean IC, sd IC, median cross-section)`.
PANEL_IC = {
    "quality":  (0.0695, 0.0872, 4106),
    "growth":   (0.0110, 0.0592, 4106),
    "momentum": (0.0417, 0.1302, 4106),
    "value":    (0.0547, 0.1116, 4106),
    "size":     (-0.0703, 0.0941, 4106),
}

#: the recorder's own cross-section, from `VALREADS_COST.json`'s population census.
N_CROSS = 542

#: weeks a year, and the overlap each horizon induces on a WEEKLY record. A 3-month forward
#: return measured every week is the same return thirteen times over, so the independent count
#: is the week count divided by the overlap -- `power_gate.available_independent_n_nonoverlapping`
#: is the same arithmetic and is called rather than reproduced.
WEEKS_PER_YEAR = 52.0
HORIZON_MONTHS = (3, 6, 12)

#: The bar is NOT chosen here. The register's own rule is each read's WITHIN-DATE PERMUTATION p95,
#: computed at verdict time from the record's own rows -- the V6 / E5 / O14 construction. 2.0 is
#: used for THIS ARITHMETIC ONLY, because a permutation floor cannot exist before the rows do, and
#: this project's measured permutation floors on comparable statistics sit near it (X1's
#: half-universe long-short p95 1.4661; O14's 1.95-2.05). Labelled a PLACEHOLDER everywhere.
CRIT_PLACEHOLDER = 2.0


def true_sd(sd_ic, n_panel):
    """The N-independent part of the dispersion: `sqrt(sd^2 - 1/(N-1))`."""
    v = float(sd_ic) ** 2 - 1.0 / (float(n_panel) - 1.0)
    return (v ** 0.5) if v > 0 else 0.0


def sd_at(n_cross, sd_ic, n_panel):
    """The same signal's per-date IC dispersion on a cross-section of `n_cross` names."""
    return (true_sd(sd_ic, n_panel) ** 2 + 1.0 / (float(n_cross) - 1.0)) ** 0.5


def main(argv=None):
    sds = {k: round(sd_at(N_CROSS, sd, n), 4) for k, (_m, sd, n) in PANEL_IC.items()}
    lo, hi = min(sds.values()), max(sds.values())
    mid = round((lo + hi) / 2.0, 4)
    print("[power] per-date sd(IC) re-scaled to a %d-name cross-section: %s"
          % (N_CROSS, json.dumps(sds)))
    print("[power] range %.4f to %.4f, midpoint %.4f used below" % (lo, hi, mid))

    #: the effect worth detecting, and it is this project's OWN best measured read rather than a
    #: number chosen to make the design look good: `quality`'s mean IC of 0.0695 is the largest
    #: of the five, so a design that cannot see it cannot see anything this project has found.
    target = PANEL_IC["quality"][0]

    rows = []
    for h in HORIZON_MONTHS:
        overlap = h * (WEEKS_PER_YEAR / 12.0)
        for years in (1, 2, 3, 5, 10, 20):
            weeks = WEEKS_PER_YEAR * years
            # CALLED, not reproduced: the same non-overlapping reduction power_gate exposes.
            n_eff = PG.available_independent_n_nonoverlapping(weeks, overlap)
            if n_eff < 3:
                rows.append({"horizon_months": h, "years": years, "n_eff": round(n_eff, 2),
                             "status": "too few independent observations to state an MDE"})
                continue
            se = mid / (n_eff ** 0.5)
            rows.append({
                "horizon_months": h, "years": years,
                "weeks_recorded": int(weeks), "overlap_weeks": round(overlap, 2),
                "n_independent": round(n_eff, 2),
                "se_mean_ic": round(se, 5),
                "detection_threshold_50pct": round(PG.detection_threshold(
                    se, crit=CRIT_PLACEHOLDER), 5),
                "mde_80pct": round((CRIT_PLACEHOLDER + PG.z_for_power(0.80)) * se, 5),
                "power_against_quality_like_0.0695": round(
                    PG.power_at(target, se, crit=CRIT_PLACEHOLDER) * 100.0, 1),
                "state": PG.state(target, se, crit=CRIT_PLACEHOLDER),
            })

    # WHEN does each horizon first reach 80% power against a quality-like read?
    firsts = {}
    for h in HORIZON_MONTHS:
        overlap = h * (WEEKS_PER_YEAR / 12.0)
        need = None
        for y10 in range(1, 4001):                      # tenths of a year, out to 400 years
            years = y10 / 10.0
            n_eff = PG.available_independent_n_nonoverlapping(WEEKS_PER_YEAR * years, overlap)
            if n_eff < 3:
                continue
            se = mid / (n_eff ** 0.5)
            if (CRIT_PLACEHOLDER + PG.z_for_power(0.80)) * se <= target:
                need = years
                break
        firsts[str(h)] = need

    out = {
        "item": "VALREADS", "part": "step 0b -- when this design could resolve", "trials": 0,
        "trial_class": "POWER DERIVATION -- searches nothing, has no bar, reads no return",
        "measured_panel_ic": {k: {"mean_ic": m, "sd_ic": s, "n_cross": n,
                                  "true_sd_n_independent": round(true_sd(s, n), 4)}
                              for k, (m, s, n) in PANEL_IC.items()},
        "n_cross_recorder": N_CROSS,
        "sd_ic_rescaled_to_recorder": sds,
        "sd_ic_used": mid,
        "target_effect": target,
        "target_effect_is": ("`quality`'s own measured mean IC on the corrected panel -- the "
                            "LARGEST of the five, so a design that cannot see it cannot see "
                            "anything this project has measured"),
        "crit_placeholder": CRIT_PLACEHOLDER,
        "crit_placeholder_is": ("A PLACEHOLDER. The register's bar is each read's WITHIN-DATE "
                                "PERMUTATION p95 computed at verdict time from the record's own "
                                "rows; a permutation floor cannot exist before the rows do. 2.0 "
                                "is used for this arithmetic only and is near this project's "
                                "measured floors on comparable statistics (X1 1.4661, O14 "
                                "1.95-2.05)."),
        "years_to_80pct_power_against_a_quality_like_read": firsts,
        "rows": rows,
    }
    print("\n  h(mo)  years  n_indep    se      MDE80   power vs 0.0695")
    for r in rows:
        if r.get("status"):
            print("  %5d %6d  %7.2f   %s" % (r["horizon_months"], r["years"], r["n_eff"],
                                             r["status"]))
            continue
        print("  %5d %6d  %7.2f  %.5f  %.5f   %5.1f%%"
              % (r["horizon_months"], r["years"], r["n_independent"], r["se_mean_ic"],
                 r["mde_80pct"], r["power_against_quality_like_0.0695"]))
    print("\n  YEARS TO 80%% POWER against a quality-like read (IC 0.0695): %s"
          % json.dumps(firsts))

    from scripts.index_best import _data_root
    p = os.path.join(_data_root(), "free_analysis", "VALREADS_POWER.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("  wrote %s" % p)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
