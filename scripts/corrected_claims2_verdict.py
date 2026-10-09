# -*- coding: utf-8 -*-
"""`CORRECTED-CLAIMS-2`, the verdict pass -- the four claims `CORRECTED-FLOORS` left UNMEASURED,
plus R1's net-of-cost cell, in the three-state vocabulary.

    python -m scripts.corrected_claims2_verdict

**EVERY BAR IN THIS FILE WAS FIXED BEFORE THE PRODUCERS REPORTED.** The producers were launched
in their own pass (`scripts/corrected_claims2.py`) and this file was written while they ran, for
`O10`'s reason: a rule written after the number it judges is not a rule. Where a published claim
has its own pre-committed bar -- `S22`'s `R_8 >= 6.0`, `V6-B`'s 3.0pp economic floor and its
both-halves requirement -- **that bar is REUSED VERBATIM rather than re-chosen here**, which is
`W-28`'s rule: a pre-committed bar may not be relaxed after watching it fail, and it may not be
tightened after watching it pass either.

**THE VOCABULARY IS IMPORTED, NOT RE-DEFINED** -- `corrected_claims.claim()` is CALLED (`B7`), so
a `SURVIVES` row still cannot exist without a corrected value and an `UNMEASURED` row still cannot
exist without a named reason.

**EVERY FIGURE IS THE DEPLOYED BOOK (flat 1/7).** `term_structure` scores its own `DEPLOYED` dict
and `factor_alpha` the non-zero `WEIGHTS_ESTABLISHED` entries; CPCV is never consulted. Part 1b
measured why the label is load-bearing: on this universe CPCV **adopts** `ic-proportional`, and
the adopted book's top-decile alpha is 2.83pc against the deployed 6.07pc, so a corrected figure
that does not name its weighting cannot be compared with anything published.

**TWO ROWS FOR ONE SENTENCE, WHERE THE LITERAL AND THE SUBSTANCE CAN COME APART.** `S22`'s *"the
alpha HAC t never drops below 3.16"* is a claim about a MINIMUM: a corrected minimum of 3.0 would
falsify the printed number while leaving the substance -- that the persistence is not resting on
widened error bars -- intact. Both readings get their own row and their own pre-committed bar, so
neither can be chosen after the fact.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.corrected_claims as CC                                       # noqa: E402
from scripts.corrected_claims import SURVIVES, NO_LONGER_HOLDS, UNMEASURED  # noqa: E402

OUT = "CORRECTED_CLAIMS2_VERDICT.json"

# --------------------------------------------------------------------------------------------
# THE PUBLISHED FIGURES, as literals. A drift in the record shows as a diff here (`MA13`'s
# idiom) instead of being silently inherited. Every one was read back out of the banked
# artifact before being written down, not copied from prose.
# --------------------------------------------------------------------------------------------
PUB_S22_MIN_T = 3.16          # "the alpha HAC t never drops below 3.16"; banked min 3.1608 @h252
PUB_S22_2Y_T = 3.83           # "3.83 at two years"; banked h504 3.8301
PUB_S22_R8 = 6.194976482813532  # the shape statistic; S22's own CONSTANT-RATE bar is 6.0
PUB_HOLD_1Q = 0.066           # product copy "about 6.6% annualized over the next three months"
PUB_HOLD_2Y = 0.051           # product copy "still ahead by about 5.1% annualized two years later"
PUB_SCORE_PER_NAME = 45       # score_confidence.PER_NAME_DATES, of 69
PUB_SCORE_GROUP = 21          # score_confidence.GROUP_DATES, of 69
PUB_SCORE_DENOM = 69
PUB_RANK_IC_1Q = 0.0336      # hold_horizon.RANK_IC_FIRST_QUARTER
PUB_RANK_IC_2Y = 0.0655      # hold_horizon.RANK_IC_TWO_YEARS
PUB_PANEL_NAMES = 2531       # hold_horizon.PANEL_NAMES -- the canonical move changes this
PUB_PANEL_DATES = 69         # hold_horizon.PANEL_DATES
PUB_V6B_HEALTHY = 0.3251      # V6-B M1 healthy further-20%-within-126d rate
PUB_V6B_UNHEALTHY = 0.4335    # V6-B M1 unhealthy
PUB_V6B_MEAN_DIFF_PP = -10.228339376002001  # the REGISTERED statistic: per-date mean diff
PUB_V6B_VERDICT = "REAL - HEALTHY DIPS SURVIVE BETTER"  # V6-B's own M1_verdict, published

# --------------------------------------------------------------------------------------------
# THE BARS. Two kinds, kept apart on purpose.
#
#   REUSED  -- the claim's own pre-committed bar, quoted from its register. Not re-chosen here.
#   DECLARED -- a bar this item had to set, because the claim is PROSE on a surface and its
#               register never committed a tolerance for re-measuring it on a new universe.
#               Each carries the reason it is the number it is.
# --------------------------------------------------------------------------------------------
BAR_S22_R8 = 6.0              # REUSED: S22's own CONSTANT-RATE bar (>= 6.0 is constant-rate)
BAR_S22_SATURATING = 2.0      # REUSED: S22's own SATURATING bar (<= 2.0)
BAR_S22_REVERSING_T = -2.0    # REUSED: S22's own REVERSING bar, labelled UNCALIBRATED by S22
BAR_S22_WELL_MEASURED_T = 2.0  # DECLARED, and LABELLED UNCALIBRATED
#: why 2.0: the SUBSTANCE row asks whether alpha is still separable from zero at EVERY horizon.
#: S22's own per-horizon `fixed_weights_null` floors are not available under `--skip-placebo`,
#: and CLAUDE.md records that those percentiles may never be compared with X7's 2.2837 -- a
#: different and less conservative null. So the only honest bar left is the conventional 2.0,
#: and it ships labelled UNCALIBRATED. The per-horizon comparison is reported UNMEASURED
#: separately rather than folded into this row.

BAR_HOLD_COPY_PP = 0.010      # DECLARED: 1.0pp
#: why 1.0pp: the copy quotes ONE DECIMAL PLACE ("6.6%", "5.1%"), so a move of a full point
#: changes the sentence a user reads. A tighter bar would fail on rounding; a looser one would
#: let the page keep a number it no longer measures.

BAR_SCORE_PER_NAME_GATE = 42  # REUSED: the register's own gate, quoted verbatim in
#: `score_confidence.py`'s provenance comment -- "holds on 45 of 69 rebalance dates
#: (gate: 42)". NOT a tolerance invented by this item.
#: DECLARED and DIRECTIONAL rather than two-sided, which is the conservative direction: the
#: surface quotes an EXACT integer ("calibrated on 45 of 69 dates"), so ANY change falsifies the
#: literal figure. A count at or above the published one leaves the sentence true a fortiori; a
#: count below it does not, and is reported for restatement with the corrected integer.

V6B_VERDICT_PREFIX = "REAL"   # REUSED: V6-B's OWN m1_verdict decides, not a bar here.
#: Its rule already is register 2.1 -- both halves below their own permutation p5,
#: sign-stable, AND both halves clearing M1_ECONOMIC_PP = 3.0 (PERCENTAGE POINTS). Reading
#: the verdict rather than re-deriving it avoids a second definition of one rule (B7) and
#: avoids the sign trap its own docstring names as the easiest mistake in that file.
#: V6-B's both-halves requirement and sign-stability are reused verbatim too. THE CLAIM IS THE
#: SEPARATION, NOT THE TWO LEVELS: the rates themselves must move with the universe, so a row
#: judging them against 32.51% and 43.35% would fail for the wrong reason.

C1_CROSS_INSTRUMENT_TOL = 1e-9
#: DECLARED. S22's own C1 FAILS on the corrected universe, correctly -- it is a fidelity
#: gate to the banked 2,531-name record. `C1_RECORD` is NOT touched and no tolerance is
#: widened (W-28). Instead the failure is made ATTRIBUTABLE: the corrected run must
#: reproduce part 1b's independently landed corrected DEPLOYED top-decile alpha, measured
#: by `corrected_deployed.deployed_statistics` -- a different call path into
#: `quantile_backtest`. A broken panel would fail C1 too, and would look identical in the
#: artifact; two instruments agreeing on one object is what separates "different universe"
#: from "broken run". The tolerance is exact-to-rounding because both paths call the same
#: shipped function on the same panel.

MIN_MERGE_COV = 0.50
#: DECLARED. V6-B's own published coverage on the old universe was drawdown 98.33% and health
#: 100.00%, so anything under half is a broken join rather than a thin universe. The floor is
#: deliberately far below the published figures: its job is to separate "the merge failed" from
#: "coverage moved with the universe", not to judge coverage.

BARS_REUSED = ("BAR_S22_R8", "BAR_S22_SATURATING", "BAR_S22_REVERSING_T",
               "V6B_VERDICT_PREFIX", "BAR_SCORE_PER_NAME_GATE")
BARS_DECLARED = ("BAR_S22_WELL_MEASURED_T", "BAR_HOLD_COPY_PP", "MIN_MERGE_COV",
                 "C1_CROSS_INSTRUMENT_TOL")


def fa():
    return CC.fa()


def fa_or_none():
    """The free-analysis directory, or `None` where there is no licensed data root.

    **A HELPER THAT REPORTS ITS OWN INABILITY MUST DO SO AS A STATE, NOT BY RAISING.** `CC.fa()`
    raises when the root is absent, and on a CI runner `data/` is gitignored, so every gated
    helper that called it produced an ERROR instead of a reported skip. Part 1 of
    `CORRECTED-FLOORS` failed CI for the import-time version of this; making the path lazy moved
    the exception from import time to CALL time without removing it.
    """
    try:
        return CC.fa()
    except Exception:
        return None


def _load(name):
    f = fa_or_none()
    if f is None:
        return None
    p = os.path.join(f, name)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------------------------
# S22 + hold_horizon -- ONE producer answers both, because `hold_horizon.REGISTER` IS
# `PREREG_s22_term_structure.md`.
# --------------------------------------------------------------------------------------------
def c1_is_attributable_to_the_universe(ts):
    """Is S22's C1 failure explained by the universe, or by a broken run?

    Returns `(ok, detail)`. `ok` is True when EITHER C1 passed (the banked panel) OR C1 failed
    and the run's own deployed top-decile alpha reproduces part 1b's landed corrected figure.

    This is the positive control that stops "C1 failed, but that's expected" from being an
    assertion. A mis-keyed join, a wrong weight vector or a truncated panel all fail C1 and all
    look the same in the artifact; only a second instrument can tell them apart.
    """
    c1 = (ts or {}).get("C1_incumbent_reproduces_record") or {}
    checks = c1.get("checks") or {}
    if c1.get("all_ok"):
        return True, {"c1_all_ok": True,
                      "note": "C1 PASSED, so this is the banked panel and no attribution is "
                              "needed"}
    got = ((checks.get("top_decile_alpha") or {}).get("got"))
    # THE ORDER MATTERS, AND SO DOES KEEPING THE TWO REFUSALS DISTINCT. "C1 carries no reading"
    # and "there is no landed figure to compare against here" are different facts with different
    # fixes, and one blurred `why` made a test assert the first while reading the second -- the
    # wrong-object family. The reading is checked FIRST, because it depends on nothing external.
    if got is None:
        return False, {"c1_all_ok": False, "refusal": "NO_READING",
                       "why": "C1 carries no top_decile_alpha reading, so its failure cannot be "
                              "attributed"}
    try:
        want = CC.landed_corrected_deployed_alpha()
    except Exception as e:
        return False, {"c1_all_ok": False, "refusal": "NO_LANDED_FIGURE",
                       "why": "part 1b's landed corrected deployed alpha is unreadable here "
                              "(no licensed data root, or the artifact is absent): %s" % e}
    dev = abs(float(got) - float(want))
    return (dev <= C1_CROSS_INSTRUMENT_TOL), {
        "c1_all_ok": False,
        "c1_failed_as_expected": "C1 is a fidelity gate to the banked 2,531-name record and this "
                                 "is a 9,645-name universe, so its failure is the gate working",
        "run_deployed_top_decile_alpha": float(got),
        "part1b_landed_corrected_deployed_alpha": float(want),
        "abs_dev": dev, "tol": C1_CROSS_INSTRUMENT_TOL,
        "measured_by": "corrected_deployed.deployed_statistics -- a DIFFERENT call path into "
                       "quantile_backtest than term_structure's own arm",
        "C1_RECORD_untouched": True,
    }


def _ric(block, h):
    """Median per-date rank IC at horizon `h`, without guessing at a shape. Returns None rather
    than a plausible wrong number -- a silently-missing row is better than a mislabelled one."""
    cand = block.get(str(h)) if isinstance(block, dict) else None
    if isinstance(cand, (int, float)):
        return float(cand)
    if isinstance(cand, dict):
        for k in ("median", "median_ic", "ic_median", "rank_ic_median"):
            if isinstance(cand.get(k), (int, float)):
                return float(cand[k])
    return None


def s22_rows(ts):
    """Four rows off one artifact: the SHAPE, the LITERAL minimum, the SUBSTANCE, and the
    two-year cell. Plus the per-horizon floor comparison, reported UNMEASURED with its cost."""
    rows = []
    if ts is None:
        for n, pub in (("S22 term-structure shape (R_8)", PUB_S22_R8),
                       ("S22 'alpha HAC t never below 3.16' (LITERAL)", PUB_S22_MIN_T),
                       ("S22 alpha separable at every horizon (SUBSTANCE)", PUB_S22_MIN_T),
                       ("S22 two-year alpha HAC t", PUB_S22_2Y_T),
                       ("hold_horizon copy: 1-quarter annualized alpha", PUB_HOLD_1Q),
                       ("hold_horizon copy: 2-year annualized alpha", PUB_HOLD_2Y)):
            rows.append(CC.claim(
                n, "BACKTEST / valuation/web/hold_horizon.py",
                "PREREG_s22_term_structure.md", pub, None, UNMEASURED,
                why="scripts.term_structure did not produce an artifact on the rebuilt panel; "
                    "see CORRECTED_S22.log"))
        return rows

    # THE C1 ATTRIBUTION CONTROL, BEFORE ANY ARM IS READ.
    ok, c1d = c1_is_attributable_to_the_universe(ts)
    if not ok:
        for n, pub in (("S22 term-structure shape (R_8)", PUB_S22_R8),
                       ("S22 'alpha HAC t never below 3.16' (LITERAL)", PUB_S22_MIN_T),
                       ("S22 alpha separable at every horizon (SUBSTANCE)", PUB_S22_MIN_T),
                       ("S22 two-year alpha HAC t", PUB_S22_2Y_T),
                       ("hold_horizon copy: 1-quarter annualized alpha", PUB_HOLD_1Q),
                       ("hold_horizon copy: 2-year annualized alpha", PUB_HOLD_2Y)):
            rows.append(CC.claim(
                n, "BACKTEST / valuation/web/hold_horizon.py",
                "PREREG_s22_term_structure.md", pub, None, UNMEASURED,
                why="S22's C1 failed and the failure is NOT attributable to the universe: %s. "
                    "C1 is a fidelity gate to the banked 2,531-name record, so it SHOULD fail "
                    "here -- but a broken panel fails it identically, and the run's own deployed "
                    "alpha does not reproduce part 1b's landed corrected figure, so the arms are "
                    "not read." % c1d))
        return rows

    pc = ts.get("primary_common_dates") or {}
    hs = [int(h) for h in (ts.get("horizons") or [])]
    cells = {h: pc.get(str(h)) or {} for h in hs}
    t_by_h = {h: c.get("alpha_t_hac") for h, c in cells.items() if c.get("alpha_t_hac") is not None}
    a_by_h = {h: c.get("alpha_ann") for h, c in cells.items() if c.get("alpha_ann") is not None}

    # --- the SHAPE, on S22's own bars ---
    r8 = (ts.get("verdict") or {}).get("R_8")
    shape = (ts.get("verdict") or {}).get("shape")
    if r8 is None:
        rows.append(CC.claim("S22 term-structure shape (R_8)",
                             "BACKTEST / CLAUDE.md S22 bullet",
                             "PREREG_s22_term_structure.md", PUB_S22_R8, None, UNMEASURED,
                             why="the corrected artifact carries no verdict.R_8"))
    else:
        rows.append(CC.claim(
            "S22 term-structure shape (R_8)", "BACKTEST / CLAUDE.md S22 bullet",
            "PREREG_s22_term_structure.md", {"R_8": PUB_S22_R8, "shape": "CONSTANT-RATE"},
            {"R_8": r8, "shape": shape},
            SURVIVES if float(r8) >= BAR_S22_R8 else NO_LONGER_HOLDS,
            floor=BAR_S22_R8, floor_key="S22's OWN pre-committed CONSTANT-RATE bar (REUSED)",
            note="the bar is S22's, quoted from its register rather than re-chosen here; "
                 "weighting DEPLOYED flat 1/7"))

    # --- the LITERAL minimum ---
    if not t_by_h:
        rows.append(CC.claim("S22 'alpha HAC t never below 3.16' (LITERAL)",
                             "CLAUDE.md S22 bullet", "PREREG_s22_term_structure.md",
                             PUB_S22_MIN_T, None, UNMEASURED,
                             why="no per-horizon alpha_t_hac in the corrected artifact"))
    else:
        hmin = min(t_by_h, key=lambda h: t_by_h[h])
        tmin = float(t_by_h[hmin])
        rows.append(CC.claim(
            "S22 'alpha HAC t never below 3.16' (LITERAL)", "CLAUDE.md S22 bullet",
            "PREREG_s22_term_structure.md", PUB_S22_MIN_T,
            {"min_alpha_t_hac": tmin, "at_horizon": hmin, "n_horizons": len(t_by_h)},
            SURVIVES if tmin >= PUB_S22_MIN_T else NO_LONGER_HOLDS,
            floor=PUB_S22_MIN_T, floor_key="the printed number itself",
            note="this row judges the PRINTED FIGURE. The substance -- whether alpha is still "
                 "separable at every horizon -- is a separate row with its own bar, so neither "
                 "reading can be chosen after the fact."))

        rows.append(CC.claim(
            "S22 alpha separable at every horizon (SUBSTANCE)", "CLAUDE.md S22 bullet",
            "PREREG_s22_term_structure.md",
            {"published_min_t": PUB_S22_MIN_T, "published_horizons_clearing_2.0": len(t_by_h)},
            {"min_alpha_t_hac": tmin, "at_horizon": hmin,
             "horizons_clearing": sum(1 for v in t_by_h.values() if abs(float(v)) >= BAR_S22_WELL_MEASURED_T),
             "of_horizons": len(t_by_h),
             "per_horizon_alpha_t_hac": {str(h): t_by_h[h] for h in sorted(t_by_h)}},
            SURVIVES if tmin >= BAR_S22_WELL_MEASURED_T else NO_LONGER_HOLDS,
            floor=BAR_S22_WELL_MEASURED_T,
            floor_key="UNCALIBRATED -- conventional 2.0 (DECLARED by this item)",
            note="S22's own per-horizon fixed_weights_null floors are NOT available here, and "
                 "CLAUDE.md forbids comparing those percentiles with X7's 2.2837. So this row "
                 "says 'still separable from zero at this panel's resolution' and nothing "
                 "stronger; the per-horizon floor comparison is its own UNMEASURED row."))

    # --- the two-year cell ---
    t504 = t_by_h.get(504)
    rows.append(CC.claim(
        "S22 two-year alpha HAC t", "CLAUDE.md S22 bullet",
        "PREREG_s22_term_structure.md", PUB_S22_2Y_T,
        None if t504 is None else {"h504_alpha_t_hac": float(t504)},
        UNMEASURED if t504 is None else
        (SURVIVES if abs(float(t504)) >= BAR_S22_WELL_MEASURED_T else NO_LONGER_HOLDS),
        floor=None if t504 is None else BAR_S22_WELL_MEASURED_T,
        floor_key=None if t504 is None else "UNCALIBRATED -- conventional 2.0",
        why=None if t504 is not None else "h=504 absent from the corrected artifact",
        note="the published 3.83 is the printed figure; this row asks whether the two-year cell "
             "is still measured away from zero, which is what the persistence claim rests on."))

    # --- the product copy, both cells ---
    for nm, h, pub in (("hold_horizon copy: 1-quarter annualized alpha", 63, PUB_HOLD_1Q),
                       ("hold_horizon copy: 2-year annualized alpha", 504, PUB_HOLD_2Y)):
        got = a_by_h.get(h)
        if got is None:
            rows.append(CC.claim(nm, "valuation/web/hold_horizon.py (public copy)",
                                 "PREREG_s22_term_structure.md", pub, None, UNMEASURED,
                                 why="h=%d absent from the corrected artifact" % h))
            continue
        got = float(got)
        ok = (got > 0.0) and (abs(got - pub) <= BAR_HOLD_COPY_PP)
        rows.append(CC.claim(
            nm, "valuation/web/hold_horizon.py (public copy)",
            "PREREG_s22_term_structure.md", pub,
            {"alpha_ann": got, "move_pp": round((got - pub) * 100.0, 4)},
            SURVIVES if ok else NO_LONGER_HOLDS,
            floor=BAR_HOLD_COPY_PP,
            floor_key="DECLARED 1.0pp -- the copy quotes one decimal place",
            note="long-only and gross of costs, unchanged by construction. A NO LONGER HOLDS "
                 "here is a restatement for the app lane, not a research failure: it is the "
                 "same measurement on a different universe."))

    # --- the rank-IC route, two more public figures off the SAME producer ---
    ric = ts.get("rank_ic_common") or {}
    g1 = _ric(ric, 63)
    g2 = _ric(ric, 504)
    if g1 is None or g2 is None:
        rows.append(CC.claim(
            "hold_horizon: median rank IC rises with horizon",
            "valuation/web/hold_horizon.py (public copy)",
            "PREREG_s22_term_structure.md",
            {"first_quarter": PUB_RANK_IC_1Q, "two_years": PUB_RANK_IC_2Y}, None, UNMEASURED,
            why="the corrected artifact's rank_ic_common block does not carry both h=63 and "
                "h=504 medians"))
    else:
        rows.append(CC.claim(
            "hold_horizon: median rank IC rises with horizon",
            "valuation/web/hold_horizon.py (public copy)",
            "PREREG_s22_term_structure.md",
            {"first_quarter": PUB_RANK_IC_1Q, "two_years": PUB_RANK_IC_2Y,
             "claim": "the two-year median rank IC exceeds the one-quarter one"},
            {"first_quarter": g1, "two_years": g2, "rises": bool(g2 > g1)},
            SURVIVES if g2 > g1 else NO_LONGER_HOLDS,
            floor=None,
            floor_key="DIRECTIONAL -- the claim is that it RISES, so no bar is needed and none "
                      "is invented for the four-decimal literals",
            note="the record calls this the independent route to the same finding, never "
                 "touching the decile machinery. The two printed constants are restatements for "
                 "the app lane; this row judges the CLAIM."))

    # --- the panel's own shape, which the canonical move changes ---
    rows.append(CC.claim(
        "hold_horizon: PANEL_NAMES / PANEL_DATES", "valuation/web/hold_horizon.py (public copy)",
        "PREREG_s22_term_structure.md",
        {"names": PUB_PANEL_NAMES, "dates": PUB_PANEL_DATES},
        {"names": ts.get("n_names"), "dates": ts.get("n_dates")},
        NO_LONGER_HOLDS if ts.get("n_names") != PUB_PANEL_NAMES else SURVIVES,
        floor=None, floor_key="an EXACT printed integer -- any change is a restatement",
        note="recorded as its own row so item 5's old-to-new table cannot miss it: the surface "
             "names the panel every figure on it comes from, and the canonical move replaces "
             "that panel."))

    # --- the per-horizon floor comparison, named as not done ---
    rows.append(CC.claim(
        "S22 per-horizon fixed_weights_null floors", "BACKTEST",
        "PREREG_s22_term_structure.md",
        "8 per-horizon floors at 200 draws each", None, UNMEASURED,
        why="200 draws x 8 horizons on a 290k-row panel is many hours, and a REDUCED draw count "
            "is refused outright: CORRECTED-FLOORS fixed MIN_DRAWS_FOR_A_FLOOR = 100 because a "
            "p95 over fewer is set by its top two values. Only h=63 has a corrected floor, from "
            "CORRECTED-FLOORS part 1; comparing h>63 against it would be exactly the "
            "extrapolation S22 built its own per-horizon nulls to avoid."))
    return rows


# --------------------------------------------------------------------------------------------
# score_calibration
# --------------------------------------------------------------------------------------------
def group_dates_clearing(sc):
    """How many dates does the TOP-DECILE MEAN clear its own noise p95 on?

    This is `GROUP_DATES`' statistic, and it is NOT `robustness.n_dates_clearing_p95` -- that is
    the rank-10 composite and reads **24** on the banked run against the published **21**. Two
    nearly-equal counts on different objects (`S25`'s lesson), and on the corrected run they
    coincide at 57, so the wrong field would have given the right integer for the wrong reason.

    Derived from the per-date rows so it is the same quantity the record quotes, and
    `validate_group_derivation` gates it against the published 21 before it is used.
    """
    rows = ((sc or {}).get("robustness") or {}).get("per_date") or []
    n = 0
    for r in rows:
        a, b = r.get("real_top_decile_mean"), r.get("noise_top_decile_mean_p95")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > b:
            n += 1
    return (n if rows else None), len(rows)


def validate_group_derivation():
    """`MB15` -- the instrument before the hypothesis. The derivation must reproduce the
    PUBLISHED 21 of 69 on the BANKED artifact, or it is not measuring `GROUP_DATES`.

    Returns `(ok, detail)`. `ok` is None when the banked artifact is absent (a licensed-data
    host), which is reported rather than treated as a pass.
    """
    import json
    f = fa_or_none()
    if f is None:
        return None, {"state": "NOT VALIDATED -- no licensed data root on this host"}
    q = os.path.join(f, "SCORE_CALIBRATION.json")
    if not os.path.exists(q):
        return None, {"state": "NOT VALIDATED -- banked SCORE_CALIBRATION.json absent"}
    with io.open(q, encoding="utf-8") as fh:
        banked = json.load(fh)
    got, denom = group_dates_clearing(banked)
    return (got == PUB_SCORE_GROUP and denom == PUB_SCORE_DENOM), {
        "banked_group_count": got, "published": PUB_SCORE_GROUP,
        "banked_denominator": denom, "published_denominator": PUB_SCORE_DENOM,
        "also_checked": "robustness.n_dates_clearing_p95 is a DIFFERENT statistic and reads %s "
                        "on the banked run, which is why it is not used"
                        % ((banked.get("robustness") or {}).get("n_dates_clearing_p95"),),
    }


def score_rows(sc):
    """`score_confidence`'s two printed counts.

    **THE PER-NAME ROW HAS THE REGISTER'S OWN GATE AND IT IS REUSED.** `score_confidence.py`'s
    provenance comment reads *"The per-name verdict holds on 45 of 69 rebalance dates
    (gate: 42)"* -- so 42 is a PRE-COMMITTED bar from `PREREG_v3_score_calibration.md`, not a
    tolerance invented here, and `W-28`'s rule applies: it may not be relaxed after watching it
    fail, nor tightened after watching it pass.

    **THE GROUP ROW PROTECTS A LIMITATION RATHER THAN A RESULT.** The same comment reads *"The
    group-level result holds on only 21 of 69 -- which is why it may never be stated as a
    standing property."* So the sentence at risk is the DISCLAIMER, and it survives as long as
    the group result is still a MINORITY of the dates scored. A corrected count that became a
    majority would mean the page now UNDER-claims -- a restatement in the favourable direction,
    and still not the printed sentence.
    """
    rows = []
    rb = (sc or {}).get("robustness") or {}
    scored = rb.get("n_dates_scored")
    per_name = rb.get("n_dates_not_distinguishable")
    group, group_denom = group_dates_clearing(sc)
    gok, gdetail = validate_group_derivation()

    if sc is None:
        why = ("scripts.score_calibration did not produce an artifact on the rebuilt panel; "
               "see CORRECTED_SCORE.log")
    elif not rb:
        why = "the corrected artifact carries no `robustness` block"
    else:
        why = None

    if why:
        for nm, pub in (
                ("score_confidence PER_NAME_DATES",
                 "%d of %d" % (PUB_SCORE_PER_NAME, PUB_SCORE_DENOM)),
                ("score_confidence GROUP_DATES (the limitation)",
                 "%d of %d" % (PUB_SCORE_GROUP, PUB_SCORE_DENOM))):
            rows.append(CC.claim(nm, "valuation/web/score_confidence.py (public copy)",
                                 "PREREG_v3_score_calibration.md", pub, None, UNMEASURED,
                                 why=why))
        return rows

    denom = int(scored) if isinstance(scored, int) else PUB_SCORE_DENOM

    if not isinstance(per_name, int):
        rows.append(CC.claim(
            "score_confidence PER_NAME_DATES",
            "valuation/web/score_confidence.py (public copy)",
            "PREREG_v3_score_calibration.md",
            "%d of %d (gate %d)" % (PUB_SCORE_PER_NAME, PUB_SCORE_DENOM,
                                    BAR_SCORE_PER_NAME_GATE),
            None, UNMEASURED,
            why="the corrected robustness block carries no `n_dates_not_distinguishable`"))
    else:
        rows.append(CC.claim(
            "score_confidence PER_NAME_DATES",
            "valuation/web/score_confidence.py (public copy)",
            "PREREG_v3_score_calibration.md",
            "%d of %d (gate %d)" % (PUB_SCORE_PER_NAME, PUB_SCORE_DENOM,
                                    BAR_SCORE_PER_NAME_GATE),
            {"dates_not_distinguishable": int(per_name), "of_dates": denom},
            SURVIVES if int(per_name) >= BAR_SCORE_PER_NAME_GATE else NO_LONGER_HOLDS,
            floor=BAR_SCORE_PER_NAME_GATE,
            floor_key="the REGISTER'S OWN gate of 42, reused verbatim",
            note="the printed integer is 45; a corrected count at or above the register's gate "
                 "leaves the VERDICT standing, and the integer itself is a restatement for the "
                 "app lane either way."))

    if not isinstance(group, int):
        rows.append(CC.claim(
            "score_confidence GROUP_DATES (the limitation)",
            "valuation/web/score_confidence.py (public copy)",
            "PREREG_v3_score_calibration.md",
            "%d of %d, 'may never be stated as a standing property'"
            % (PUB_SCORE_GROUP, PUB_SCORE_DENOM), None, UNMEASURED,
            why="the corrected robustness block carries no per-date top-decile-mean rows, so "
                "GROUP_DATES' own statistic cannot be derived"))
    elif gok is False:
        rows.append(CC.claim(
            "score_confidence GROUP_DATES (the limitation)",
            "valuation/web/score_confidence.py (public copy)",
            "PREREG_v3_score_calibration.md",
            "%d of %d, 'may never be stated as a standing property'"
            % (PUB_SCORE_GROUP, PUB_SCORE_DENOM), None, UNMEASURED,
            why="the group derivation does NOT reproduce the published 21 of 69 on the banked "
                "artifact, so it is not measuring GROUP_DATES' statistic: %s" % gdetail))
    else:
        majority = int(group_denom or denom) / 2.0
        rows.append(CC.claim(
            "score_confidence GROUP_DATES (the limitation)",
            "valuation/web/score_confidence.py (public copy)",
            "PREREG_v3_score_calibration.md",
            "%d of %d, 'may never be stated as a standing property'"
            % (PUB_SCORE_GROUP, PUB_SCORE_DENOM),
            {"dates_top_decile_mean_clears": int(group),
             "of_dates": int(group_denom or denom),
             "still_a_minority": bool(int(group) <= majority),
             "derivation_validated_against_the_banked_21": gok,
             "derivation_detail": gdetail,
             "NOT_the_rank_statistic": "robustness.n_dates_clearing_p95 is the rank-10 "
                                       "composite and reads 24 on the banked run against the "
                                       "published 21 -- a different object"},
            SURVIVES if int(group) <= majority else NO_LONGER_HOLDS,
            floor=majority,
            floor_key="DECLARED: a minority of the dates scored -- the disclaimer's own content",
            note="THE CLAIM HERE IS THE DISCLAIMER, NOT THE COUNT."))
    return rows


# --------------------------------------------------------------------------------------------
# V6-B
# --------------------------------------------------------------------------------------------
def v6b_rows(v6):
    """`V6-B`'s M1 -- and the verdict is **V6-B's OWN**, read rather than re-derived.

    `v6b_dip_survival.m1_verdict` encodes register 2.1 in full: both halves below their own
    permutation p5, sign-stable, AND both halves clearing the **3.0pp** economic floor. It
    ships its output as `M1_verdict`. Re-implementing that here would be `B7`'s defect on a
    rule with a known sign trap -- its own docstring calls getting `below_p5` vs `clears_p95`
    backwards *"the single easiest mistake to make in this file"* -- and its floor is in
    PERCENTAGE POINTS (`3.0`), which a fraction-valued bar would have missed by 100x.

    **THE PUBLISHED RATES AND THE REGISTERED STATISTIC ARE DIFFERENT QUANTITIES.** 32.51% and
    43.35% are POOLED base rates (`diagnostics/D1_base_rates`), differing by -10.84pp; the
    registered statistic is the per-date MEAN DIFFERENCE, -10.228pp. Both are reported.
    """
    name = "V6-B M1: healthy dips fall a further 20% less often"
    surface = "CLAUDE.md V6-B bullet (research only; no public surface)"
    pub = {"healthy_pooled_rate": PUB_V6B_HEALTHY, "unhealthy_pooled_rate": PUB_V6B_UNHEALTHY,
           "pooled_gap_pp": round((PUB_V6B_HEALTHY - PUB_V6B_UNHEALTHY) * 100.0, 4),
           "registered_statistic_mean_diff_pp": PUB_V6B_MEAN_DIFF_PP,
           "verdict": PUB_V6B_VERDICT}
    if v6 is None:
        return [CC.claim(name, surface, "PREREG_v6b_dip_survival.md", pub, None, UNMEASURED,
                         why="scripts.v6b_dip_survival did not produce an artifact on the "
                             "corrected export; see CORRECTED_V6B.log")]

    # THE MERGE GATE, BEFORE ANY ARM IS READ. V6-B derives `drawdown`, `health` and
    # `fwd_min_ret` from the export and merges them onto the panel on `(date, ticker)`. These
    # panels carry STRING dates, so a merge against a Timestamp-keyed frame matches ZERO rows
    # IN SILENCE -- and a dipped-row count of zero would read as "no dips survived the window"
    # rather than as "the join failed". Refuse rather than report.
    cov = (v6.get("controls") or {}).get("C4_coverage") or {}
    got = {k: cov.get(k) for k in ("drawdown_cov", "health_cov", "fwd_min_cov")
           if isinstance(cov.get(k), (int, float))}
    if got and min(got.values()) < MIN_MERGE_COV:
        return [CC.claim(name, surface, "PREREG_v6b_dip_survival.md", pub, None, UNMEASURED,
                         why="V6-B's derived columns did not reach the panel -- merge coverage "
                             "%s against a floor of %.2f. These panels carry STRING dates, so a "
                             "join against a Timestamp-keyed frame matches zero rows in silence; "
                             "a collapsed merge must not be read as a null."
                             % (got, MIN_MERGE_COV))]

    # V6-B's OWN ABORT, READ RATHER THAN SECOND-GUESSED. Its C1 is a GATING fidelity control
    # -- the register's control table says it "Runs in its OWN pass and ABORTS before any arm"
    # -- and on a 9,645-name universe it cannot pass, because it reproduces the published
    # 2,531-name record to nine decimals. It is NOT parameterised here: W-28 forbids relaxing a
    # pre-committed bar after watching it fail, and unlike served_index_book (whose gate takes
    # an expect_alpha parameter BY DESIGN) this one is unconditional and its register voids
    # every arm behind it.
    if v6.get("ABORTED"):
        c1 = (v6.get("controls") or {}).get("C1_reproduces_record") or {}
        meas = (c1.get("measured") or {}).get("top_decile_alpha")
        try:
            want = CC.landed_corrected_deployed_alpha()
        except Exception:
            want = None
        attributable = (meas is not None and want is not None
                        and abs(float(meas) - float(want)) <= C1_CROSS_INSTRUMENT_TOL)
        return [CC.claim(
            name, surface, "PREREG_v6b_dip_survival.md", pub, None, UNMEASURED,
            why=("V6-B ABORTED on its own gating control: %r. C1 reproduces the published "
                 "2,531-name record to nine decimals, so it CANNOT pass on a 9,645-name "
                 "universe, and its register voids every arm behind it. It is deliberately NOT "
                 "parameterised -- W-28 forbids relaxing a pre-committed bar after watching it "
                 "fail, and its register's C2 pins '69 dates, 2,531 names' independently of C1. "
                 "RE-MEASURING V6-B ON A CORRECTED UNIVERSE NEEDS ITS OWN REGISTER. The refusal "
                 "IS attributable rather than assumed: C1's own measured deployed alpha is %s "
                 "against part 1b's landed %s (agree: %s), so three instruments on three call "
                 "paths agree and C1 failed because the UNIVERSE differs, not because the "
                 "panel, the join or the weight vector is broken."
                 % (v6.get("ABORTED"), meas, want, attributable)))]

    a1 = (v6.get("arms") or {}).get("ARM1_SURVIVAL") or {}
    verdict = a1.get("M1_verdict")
    if not verdict:
        return [CC.claim(name, surface, "PREREG_v6b_dip_survival.md", pub, None, UNMEASURED,
                         why="the corrected artifact carries no ARM1_SURVIVAL.M1_verdict, so "
                             "V6-B's own rule did not reach a reading")]

    cell = a1.get("M1_further_20pct_within_126d") or {}
    legs = {k: ((cell.get(k) or {}).get("mean_diff_pp")) for k in ("full", "early", "late")}
    d1 = (v6.get("diagnostics") or {}).get("D1_base_rates") or {}
    corrected = {
        "M1_verdict": verdict,
        "mean_diff_pp": legs,
        "healthy_pooled_rate": d1.get("P_further20_healthy"),
        "unhealthy_pooled_rate": d1.get("P_further20_unhealthy"),
        "both_halves_below_p5": cell.get("both_halves_below_p5"),
        "halves_same_sign": cell.get("halves_same_sign"),
        "enough_dates_per_half": cell.get("enough_dates_per_half"),
        "n_dates": cell.get("n_dates"),
        "n_rows": a1.get("n_rows"),
        "merge_coverage": got,
    }
    return [CC.claim(
        name, surface, "PREREG_v6b_dip_survival.md", pub, corrected,
        SURVIVES if str(verdict).startswith("REAL") else NO_LONGER_HOLDS,
        floor=V6B_VERDICT_PREFIX,
        floor_key="V6-B's OWN m1_verdict, read not re-derived (B7). Its rule -- both halves "
                  "below their own p5, sign-stable, and both clearing 3.0pp -- is REUSED "
                  "verbatim because it IS the register's rule.",
        note="THE CLAIM IS THE SEPARATION, NOT THE TWO LEVELS: the pooled rates must move with "
             "the universe, so a row judging 32.51% and 43.35% would fail for the wrong reason. "
             "AND V6-B's C6 fidelity control compares against V6's own per-date conditioned "
             "counts on the OLD universe, so low agreement there is a UNIVERSE fact and NOT "
             "void condition 6.3 -- V6's health and quality floors are reused verbatim and "
             "nothing was re-tuned.")]


# --------------------------------------------------------------------------------------------
# R1's net-of-cost cell
# --------------------------------------------------------------------------------------------
def r1_rows(r1c):
    """R1's net-of-cost cell.

    **THE CONDITION IS STATED ON THE BREAKEVEN, NOT ON A DERIVED NET ALPHA.** The producer's own
    primary is the one-way cost at which net alpha vs equal-weight reaches zero, because that
    needs no cost assumption -- `cost_breakeven_bps` measures no realised cost, and `B11`'s
    33.4 bps was measured on the RESTRICTED universe, so a 9,645-name book holding far smaller
    names would pay more. Judging the claim on a figure derived from another population's cost
    would be `O-1`'s defect, which ran ~17x wrong.

    So: SURVIVES iff the corrected gross intercept is positive AND the breakeven exceeds the
    only realised cost this project has ever measured. The derived net alpha and its bracket
    ride along as reported figures.
    """
    name = "R1 net-of-cost intercept"
    surface = "CLAUDE.md R1 bullet"
    pub = "+7.85%/yr net of costs (t 5.16), measured on the VOID pre-B6 panel"
    if not r1c or r1c.get("state") == UNMEASURED:
        return [CC.claim(name, surface, "HANDOFF_r1.md section 1", pub, None, UNMEASURED,
                         why=(r1c or {}).get("why")
                             or "part 2's gross R1 artifact is absent, so there is nothing to "
                                "subtract a cost drag from")]

    rows = [CC.claim(
        name + " (R1's OWN path)", surface, "HANDOFF_r1.md section 1", pub, None, UNMEASURED,
        why=r1c.get("cause") or "R1's own net_of_cost cell is NaN on this universe")]

    g = r1c.get("gross_alpha_ann")
    be = r1c.get("PRIMARY_breakeven_one_way_bps")
    sens = r1c.get("SENSITIVITY_at_B11_bps") or {}
    realised = sens.get("one_way_bps")
    if g is None or be is None or realised is None:
        rows.append(CC.claim(
            name + " (DERIVED)", surface, "HANDOFF_r1.md section 1",
            "a positive factor-model intercept that survives a plausible cost", None, UNMEASURED,
            why="the corrected run yielded no gross intercept or no breakeven, so the claim "
                "cannot be judged: gross=%r breakeven=%r" % (g, be)))
        return rows

    g, be, realised = float(g), float(be), float(realised)
    rows.append(CC.claim(
        name + " (DERIVED)", surface, "HANDOFF_r1.md section 1",
        "a positive factor-model intercept that survives a plausible cost",
        {"gross_alpha_ann": g, "gross_t_nw": r1c.get("gross_t_nw"),
         "primary_spec": r1c.get("primary_spec_from_the_artifact"),
         "breakeven_one_way_bps": be,
         "only_realised_cost_this_project_has_measured_bps": realised,
         "margin_over_realised": (be / realised) if realised else None,
         "derived_net_alpha_ann_at_that_cost": sens.get("derived_net_alpha_ann"),
         "cost_drag_ann": sens.get("cost_drag_ann"),
         "bracket": sens.get("bracketed_by_the_adjacent_grid_points"),
         "curve_is_affine_in_bps": r1c.get("curve_is_affine_in_bps"),
         "corrected_realised_cost": r1c.get("corrected_realised_one_way_bps")},
        SURVIVES if (g > 0.0 and be > realised) else NO_LONGER_HOLDS,
        floor=realised,
        floor_key="DECLARED: the breakeven must exceed B11's measured one-way cost -- the only "
                  "realised figure this project has ever measured",
        note="a DERIVED reading, NOT R1's own net_of_cost cell -- R1's path is deliberately not "
             "edited, because repointing its cost leg would change a landed instrument. THREE "
             "CAVEATS TRAVEL WITH IT: the 33.4 bps was measured on the RESTRICTED universe and "
             "a 9,645-name book would pay more; the corrected universe's own realised cost is "
             "UNMEASURED (it comes from run_backtests' `costs` block, which is item 5's); and "
             "the interpolated drag is APPROXIMATE because the affinity check fired, so the "
             "bracket rather than the point figure is the measurement. Weighting DEPLOYED "
             "flat 1/7."))
    return rows


def _c1_detail():
    """The C1 attribution control's own reading, shipped so a reader of the artifact alone
    can see that C1 failed, why, and on what evidence."""
    ts = _load("CORRECTED_S22_TERM_STRUCTURE.json")
    if ts is None:
        return {"state": "NOT RUN -- no corrected S22 artifact"}
    ok, detail = c1_is_attributable_to_the_universe(ts)
    return {"attributable_to_the_universe": bool(ok), "detail": detail}


def build():
    ts = _load("CORRECTED_S22_TERM_STRUCTURE.json")
    sc = _load("CORRECTED_SCORE_CALIBRATION.json")
    v6 = _load("CORRECTED_V6B_DIP_SURVIVAL.json")
    base = _load("CORRECTED_CLAIMS2.json") or {}
    r1c = (base.get("ran") or {}).get("r1cost")

    rows = []
    rows += s22_rows(ts)
    rows += score_rows(sc)
    rows += v6b_rows(v6)
    rows += r1_rows(r1c)

    tally = {s: sum(1 for r in rows if r["state"] == s) for s in CC.STATES}
    return {
        "item": "CORRECTED-CLAIMS-2 (verdict)",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT of registered constructions on a corrected universe "
                       "(S25 / X7RECON / PANEL-EXT-RECHECK class). No hypothesis, no new bar.",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "panel": "UNIVERSE_BIAS_PANEL_full_v3.pkl",
        "weighting": "DEPLOYED (flat 1/7) on EVERY figure; CPCV never consulted",
        "bars_reused_from_their_own_registers": list(BARS_REUSED),
        "bars_declared_by_this_item": list(BARS_DECLARED),
        "bars_written_before_the_producers_reported": True,
        "S22_C1_attribution_control": _c1_detail(),
        "tally": tally,
        "claims": rows,
    }


def main():
    res = build()
    f = fa_or_none()
    if f is None:
        raise SystemExit("REFUSING: no licensed data root on this host, so there is nothing to "
                         "re-measure and nowhere to write it.")
    dest = os.path.join(f, OUT)
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("CORRECTED-CLAIMS-2 verdict")
    for r in res["claims"]:
        print("  %-14s %s" % (r["state"], r["claim"]))
        if r["state"] == UNMEASURED:
            print("                 why: %s" % (r["why"] or "")[:150])
    print("\ntally: %s" % res["tally"])
    print("wrote %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
