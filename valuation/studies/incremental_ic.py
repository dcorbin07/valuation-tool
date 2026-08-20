"""The effective-coverage rule for the incremental-IC gate — one definition (master audit MB7).

WHY THIS MODULE EXISTS, AND IT IS A MEASURED DEFECT RATHER THAN A TIDY-UP.
The PEAD/U2 template residualises a candidate on the seven weighted incumbents per date and
Spearman-correlates the residual against `fwd_ret`. Every register that has used it wrote the
same sentence — *"rows missing any input are dropped for that date"* — and none measured what
that complete-case rule costs. Measured on `panel_corrected_69d.pkl`:

    basis                                rows kept        dates with >= 20 names   first such date
    all seven incumbents (complete case) 66,444 (58.31%)  49 of 69                 2014-01-17
    six, `institutional` dropped         92,540 (81.21%)  69 of 69                 2009-01-15

The cause is exactly one column and that was verified by leave-one-out rather than assumed:
dropping ANY OTHER incumbent still leaves 49 dates; only dropping `institutional` restores 69.
It has coverage 0.7172 and its first date carrying 20 or more names is 2014-01-17, while every
other weighted theme starts 2009-01-15.

THE DEFECT IS NOT THE DROPPED DATES — IT IS THAT THE SHIPPED FLOOR IS CHECKED AGAINST A DATE
SET THE STATISTIC NEVER USES. `surface_stock.halves()` refuses a split that cannot give both
sides `MIN_DATES = 16`, which is exactly the right guard. But every caller feeds it
`covered_dates(...)`, which is computed from the ARMS' presence and knows nothing about the
incumbents. So on the full panel:

    halves(RAW 69 dates)        -> early 34 / late 34   passes its own guard, raises nothing
    ...the statistic then scores    early 14 / late 34   14 is BELOW the floor that just passed

The thin half the guard exists to refuse happens anyway, downstream, in silence. `MA58-SEAS`
hit this and reported it; the audit independently reproduced it.

THE REPAIR IS CONSTRUCTIVE, NOT A NEW BAR. Split the EFFECTIVE dates instead of the raw ones
and the shipped guard does the job it was written for:

    halves(EFFECTIVE 49 dates)  -> early 24 / late 24   both clear 16

WITH ONE DISCLOSURE THAT MUST TRAVEL: the boundary MOVES, 2017-07-20 -> 2020-01-22. A register
splitting effective dates is reporting a genuinely different early half from one splitting raw
dates, and saying so is the whole point.

WHICH REGISTERS ACTUALLY INHERITED IT — AND THE AUDIT'S OWN CLAIM IS TOO BROAD, MEASURED.
`MB7` states that `U2`, `MA31` and `MA32` all used this template so their early halves inherit
the defect. They do not. `arm_ic` has always returned `n_dates_raw` AND `n_dates_incremental`
side by side, and `MA31_MA32.json` records them EQUAL in every cell — 40/40 full, 20/20 early,
19/19 late, a shortfall of zero. The reason is structural and it generalises into the rule
below: those registers score on the OPTIONS-DERIVED layer, which begins in 2016, so every one
of their covered dates already postdates `institutional`'s 2014-01-17 start and the incumbent
dropna cannot cost them a date. `U2` landed on the identical 40-date geometry, so the same
immunity applies to it by construction (its artifact is not on disk, so that is an inference
from the shared geometry and is labelled one).

SO THE RULE IS NOT "THE TEMPLATE IS BROKEN". IT IS NARROWER AND MORE USEFUL:

    An incremental-IC register is exposed exactly when its own covered window reaches back
    before `institutional`'s first scoreable date. A register whose covered window starts in
    2016 is immune by construction; a PANEL-WIDE register is exposed and must choose.

THE CHOICE IS THE REGISTER'S AND MUST BE MADE BEFORE ANY RESULT (`MB7`, verbatim):
  (a) residualise on the SIX full-window themes and report `institutional` incrementally as a
      declared secondary arm — better on POWER; or
  (b) keep all seven and state in the register that the test is post-2014 with a 28-date
      pre-2021 cell — better on COMPARABILITY with `U2`/`MA31`/`MA32`.
`basis_for()` therefore has NO DEFAULT. That is deliberate and it is `MA5`'s lesson repaid: the
HLZ hurdle froze at `N = 90` precisely because a shared primitive carried a default nobody
re-examined, so this one refuses to guess which basis a register meant.

THIS MODULE ADOPTS NOTHING AND MOVES NO VERDICT. It computes a disclosure block and a refusal.
It does not re-run, re-score or re-open `U2`, `MA31`, `MA32` or `MA58-SEAS`, whose banked
artifacts are untouched; `MA58-SEAS`'s verdict was `UNINTERPRETABLE` and stays so.

WHY IT IMPORTS RATHER THAN RESTATES. `INCUMBENTS`, `MIN_NAMES`, `MIN_DATES` and
`RegisterViolation` come from `surface_stock`, which owns them. A second copy of the incumbent
tuple is audit B7's defect class, which this project has now recorded five times
(`hlz_hurdle`, Benjamini-Hochberg, `_insider_formula`, `usable_quote`, `RESULT_BLOCKS`).
`surface_stock` carries MA59's archive banner and its own "do not extend" directive, so it is
NOT extended here — this module is new, imports from it exactly as `parity_flow` already does,
and is itself research-only and unreachable from the live product.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from .surface_stock import (INCUMBENTS, MIN_DATES, MIN_NAMES,  # noqa: F401
                            RegisterViolation, halves)

# --------------------------------------------------------------------------- #
#  The two bases, and the one column that separates them
# --------------------------------------------------------------------------- #
#: The incumbent whose late start is the entire cause. Measured, not assumed: leave-one-out
#: over all seven shows every other theme leaves 49 dates and only this one restores 69.
LATE_STARTING_INCUMBENT = "institutional"

#: Option (b): comparable with U2/MA31/MA32, and post-2014 on a panel-wide register.
BASIS_SEVEN: Tuple[str, ...] = tuple(INCUMBENTS)

#: Option (a): the full-window themes. Restores 69 of 69 dates on the corrected panel.
BASIS_SIX: Tuple[str, ...] = tuple(c for c in INCUMBENTS if c != LATE_STARTING_INCUMBENT)

BASIS_CHOICES: Dict[str, Tuple[str, ...]] = {"seven": BASIS_SEVEN, "six": BASIS_SIX}

#: The prose every incremental-IC register must satisfy. Held as a constant so it cannot rot
#: out of step with the code that enforces it, and asserted by the test suite.
COVERAGE_RULE = (
    "Every incremental-IC register MUST (1) name its basis explicitly via basis_for('six') or "
    "basis_for('seven') and say why in the register BEFORE any result; (2) print the "
    "effective_coverage() block, which reports the dates the RESIDUALISED statistic can score "
    "separately from the study's own row coverage; (3) split the EFFECTIVE dates, never the raw "
    "covered dates, so the shipped MIN_DATES floor is checked against the geometry the verdict "
    "actually uses; and (4) run its power controls on those same effective rows. A register that "
    "reports a date count for its coverage and a different one for its verdict has not satisfied "
    "this rule."
)


def basis_for(choice: str) -> Tuple[str, ...]:
    """Resolve a named basis. NO DEFAULT, deliberately - the register must choose.

    `MA5` measured what a default costs on a shared primitive: the HLZ hurdle froze at a
    constant because nothing forced a caller to state its denominator. The same applies here,
    where the two bases test different windows of history.
    """
    if choice not in BASIS_CHOICES:
        raise RegisterViolation(
            "the incremental-IC basis must be named explicitly, one of %s - got %r. "
            "Option 'six' drops %s and is better on power; option 'seven' keeps it and is "
            "better on comparability with U2/MA31/MA32, at the cost of being a post-2014 test."
            % (sorted(BASIS_CHOICES), choice, LATE_STARTING_INCUMBENT))
    return BASIS_CHOICES[choice]


def basis_name(incumbents: Sequence[str]) -> Optional[str]:
    """Reverse lookup, so a block can record WHICH basis produced it rather than a bare tuple."""
    got = tuple(incumbents)
    for name, cols in BASIS_CHOICES.items():
        if got == cols:
            return name
    return None


# --------------------------------------------------------------------------- #
#  Effective coverage
# --------------------------------------------------------------------------- #
def effective_dates(frame: pd.DataFrame, cand: str, incumbents: Sequence[str],
                    min_names: int = MIN_NAMES, ycol: str = "fwd_ret") -> List:
    """The dates the RESIDUALISED statistic can actually score.

    This is the quantity every register has been missing. `covered_dates()` answers a different
    question - where the ARM is present - and the two differ by exactly the incumbent
    complete-case rule.
    """
    inc = [c for c in incumbents if c in frame.columns]
    sub = frame.dropna(subset=[cand, ycol] + inc)
    g = sub.groupby("date").size()
    return sorted(d for d, k in g.items() if k >= min_names)


def raw_dates(frame: pd.DataFrame, cand: str, min_names: int = MIN_NAMES,
              ycol: str = "fwd_ret") -> List:
    """Dates the RAW (un-residualised) statistic can score - the comparison the block needs."""
    sub = frame.dropna(subset=[cand, ycol])
    g = sub.groupby("date").size()
    return sorted(d for d, k in g.items() if k >= min_names)


def _split_counts(dates: Sequence, min_dates: int) -> Dict[str, object]:
    """Halve `dates` with the shipped geometry, reporting a refusal instead of raising."""
    try:
        early, late, boundary = halves(list(dates), min_dates=min_dates)
        return {"n_early": len(early), "n_late": len(late), "boundary": str(boundary)[:10],
                "ok": True, "refusal": None}
    except RegisterViolation as exc:
        return {"n_early": None, "n_late": None, "boundary": None,
                "ok": False, "refusal": str(exc)}


def effective_coverage(frame: pd.DataFrame, cand: str, incumbents: Sequence[str],
                       min_names: int = MIN_NAMES, min_dates: int = MIN_DATES,
                       ycol: str = "fwd_ret") -> Dict[str, object]:
    """THE BLOCK EVERY INCREMENTAL-IC REGISTER MUST PRINT.

    It reports the raw and effective geometries side by side, because the failure this exists
    to stop is a register quoting one number for its coverage and running its verdict on
    another. `MA58-SEAS` read 76.13% of rows over 69 dates while its verdict statistic ran on 49.

    `split_on_effective` is the split a register SHOULD report; `split_on_raw_then_intersect`
    is what it gets if it splits the raw dates first, and is included precisely so the two can
    be compared in the artifact rather than argued about afterwards.
    """
    inc = [c for c in incumbents if c in frame.columns]
    missing = [c for c in incumbents if c not in frame.columns]
    rd = raw_dates(frame, cand, min_names=min_names, ycol=ycol)
    ed = effective_dates(frame, cand, inc, min_names=min_names, ycol=ycol)
    eff_set = set(ed)

    rows_raw = int(len(frame.dropna(subset=[cand, ycol])))
    rows_eff = int(len(frame.dropna(subset=[cand, ycol] + inc)))

    split_eff = _split_counts(ed, min_dates)
    intersected: Dict[str, object] = {"n_early": None, "n_late": None, "ok": None,
                                      "boundary": None}
    if len(rd) >= 2 * min_dates:
        e_raw, l_raw, b_raw = halves(rd, min_dates=min_dates)
        n_e = len([d for d in e_raw if d in eff_set])
        n_l = len([d for d in l_raw if d in eff_set])
        intersected = {"n_early": n_e, "n_late": n_l, "boundary": str(b_raw)[:10],
                       "ok": bool(n_e >= min_dates and n_l >= min_dates)}

    pre_2021 = len([d for d in ed if pd.Timestamp(d).year < 2021])
    return {
        "candidate": cand,
        "basis": basis_name(inc) or "custom",
        "basis_columns": list(inc),
        "basis_columns_absent_from_frame": missing,
        "min_names": int(min_names),
        "min_dates": int(min_dates),
        "n_dates_raw": len(rd),
        "n_dates_effective": len(ed),
        "n_dates_lost_to_incumbent_dropna": len(rd) - len(ed),
        "first_date_raw": str(rd[0])[:10] if rd else None,
        "first_date_effective": str(ed[0])[:10] if ed else None,
        "n_dates_effective_pre_2021": pre_2021,
        "rows_raw": rows_raw,
        "rows_effective": rows_eff,
        "rows_effective_frac_of_raw": (rows_eff / rows_raw) if rows_raw else None,
        "split_on_effective": split_eff,
        "split_on_raw_then_intersect": intersected,
        "coverage_rule": COVERAGE_RULE,
    }


def require_effective_coverage(block: Dict[str, object], split_used: str = "raw") -> None:
    """Gate. Raise unless the block is present, complete and describes a usable geometry.

    Three refusals, and the third is the one `MB7` exists for:
      1. the block is absent or is missing a required key;
      2. the effective dates cannot make two halves at the shipped floor;
      3. the register split the RAW dates and the effective halves fall below the floor -
         the silent case, where `halves()` passes and the statistic is scored on a thin cell.

    `split_used` DECLARES which date list the caller actually split, and it exists because the
    first cut of this gate had a real defect: refusal 3 keys on a property of the DATA rather
    than on the caller's BEHAVIOUR, so it refused a register that had already done the right
    thing - and its own refusal message instructed that register to do what it had just done.
    Found by `MB18`, the first outside caller, on the day this module landed.

    The default is "raw", which is the STRICT reading and reproduces the original behaviour
    bit-for-bit for every existing caller: an undeclared caller is assumed to have split raw and
    is refused. A caller passing "effective" is exempt from refusal 3 ONLY - refusal 2 still
    guarantees both effective halves clear the shipped floor, which is the hazard refusal 3
    was protecting against in the first place. The raw geometry is then a DISCLOSURE the
    register must print (the boundary moves), not a refusal.
    """
    if split_used not in ("raw", "effective"):
        raise RegisterViolation(
            "split_used must be 'raw' or 'effective', got %r - name which date list the "
            "register actually split, because the gate cannot see it" % (split_used,))
    required = ("candidate", "basis", "n_dates_raw", "n_dates_effective",
                "split_on_effective", "split_on_raw_then_intersect")
    if not isinstance(block, dict):
        raise RegisterViolation("no effective-coverage block was reported at all")
    absent = [k for k in required if k not in block]
    if absent:
        raise RegisterViolation("effective-coverage block is missing %s" % absent)

    if block.get("basis") == "custom":
        raise RegisterViolation(
            "the basis is not one of the two the register may choose (%s); name it with "
            "basis_for() so the artifact records which window was tested"
            % sorted(BASIS_CHOICES))

    eff = block.get("split_on_effective") or {}
    if not eff.get("ok"):
        raise RegisterViolation(
            "the effective dates cannot make two halves at the shipped floor: %s"
            % eff.get("refusal", "no split reported"))

    if split_used == "effective":
        return          # refusal 2 above already guarantees the cells clear the floor

    inter = block.get("split_on_raw_then_intersect") or {}
    if inter.get("ok") is False:
        raise RegisterViolation(
            "splitting the RAW dates leaves an effective half of %s/%s against a floor of %s - "
            "this is the MB7 defect: halves() passed on the raw geometry and the statistic "
            "would be scored on a cell below the floor. Split the EFFECTIVE dates instead "
            "(%s/%s), and report that the boundary moves from %s to %s."
            % (inter.get("n_early"), inter.get("n_late"), block.get("min_dates"),
               eff.get("n_early"), eff.get("n_late"),
               inter.get("boundary"), eff.get("boundary")))


def format_coverage(block: Dict[str, object]) -> str:
    """One-screen rendering of the mandatory block, for a register's stdout and its handoff."""
    e = block.get("split_on_effective") or {}
    i = block.get("split_on_raw_then_intersect") or {}
    return "\n".join([
        "effective coverage - candidate %s, basis %s (%d columns)"
        % (block.get("candidate"), block.get("basis"), len(block.get("basis_columns") or [])),
        "  dates    raw %-4s effective %-4s  lost %-4s  first raw %s -> effective %s"
        % (block.get("n_dates_raw"), block.get("n_dates_effective"),
           block.get("n_dates_lost_to_incumbent_dropna"),
           block.get("first_date_raw"), block.get("first_date_effective")),
        "  rows     raw %-8s effective %-8s (%.2f%% of raw)"
        % (block.get("rows_raw"), block.get("rows_effective"),
           100.0 * (block.get("rows_effective_frac_of_raw") or 0.0)),
        "  split on EFFECTIVE dates   early %s / late %s  boundary %s  ok=%s"
        % (e.get("n_early"), e.get("n_late"), e.get("boundary"), e.get("ok")),
        "  split on RAW then intersect early %s / late %s  boundary %s  ok=%s"
        % (i.get("n_early"), i.get("n_late"), i.get("boundary"), i.get("ok")),
        "  effective dates before 2021: %s" % block.get("n_dates_effective_pre_2021"),
    ])
