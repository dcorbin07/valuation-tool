"""
ARCHIVED (master audit MA59, 2026-08-15) - a CLOSED study, kept so its
result stays reproducible. It is NOT reachable from the live product and
`tests/test_ma59_quarantine.py` fails if that ever changes.
Still imported by: scripts/u2_surface_stock.py, tests/test_surface_stock.py,
valuation/studies/parity_flow.py, scripts/ma31_ma32_measure.py,
tests/test_ma31_ma32_parity_flow.py.

PATHS REPOINTED BY THE MA23 MERGE (2026-08-16). This module moved to
`valuation/studies/` under MA23, and `parity_flow` followed it here rather than
being repointed to import a study from the engine: its only importers are its
own `scripts/` runner and its own test, which is MA23's own criterion. Nothing
about the archive changed - the banner, the quarantine and the closed-study
status are untouched.
Do not extend this module; a new question needs a new register.

ONE DEFAULTED PARAMETER WAS ADDED AFTER THE ARCHIVE BANNER, AND THE TENSION IS
RECORDED RATHER THAN GLOSSED (2026-08-15, MA31/MA32). `join_pit` gained
`value_cols`, defaulting to `COMPONENT_ARMS`, so the MA31/MA32 register could
reuse the SHIPPED strictly-before join instead of re-typing it. Re-typing it is
audit B7's defect class - one definition drifting into several - which this
project has now recorded four times (`hlz_hurdle`, Benjamini-Hochberg,
`_insider_formula`, `usable_quote`), and the MA31/MA32 register forbids it by
name. Against that, MA59's directive here is "do not extend".

Both were honoured as far as they can be: the change adds no question and no
arm to U2, every existing caller is bit-identical (pinned by
`test_join_pit_default_is_bit_identical_for_existing_callers`, and U2's own 48
tests still pass), and the new importer is itself research-only, so MA59's
actual invariant - archived studies unreachable from the LIVE PRODUCT - is
untouched and `tests/test_ma59_quarantine.py` passes. If a third register wants
this join, that is the signal to lift the shared machinery OUT of this archived
module rather than to extend it again.

U2 — the options surface as a STOCK signal.

Executes `PREREG_u2_surface_stock_signals.md`. Nothing in this module may be changed to fit a
result; the register is committed alone at a strict ancestor commit.

WHAT THIS ANSWERS, AND WHAT IT DOES NOT
---------------------------------------
It asks whether three option-surface *levels* — the O16 term slope, the IV rank, and the 25-delta
smirk — predict the *underlying's* 63-day forward return, **after the seven incumbent themes are
projected out**. It does NOT test the put-call parity deviation on matched strikes (a new feature,
declined by the register's §0.5) nor the 21-day changes, so the U2 ledger row closes PARTIAL.

THREE PREMISE FACTS THAT SHAPE EVERY DEFINITION HERE
---------------------------------------------------
1. `skew_25d` is EXACTLY `iv_put_25d - iv_call_25d` (max|d| 0.000e+00 over 217,706 rows), so the
   audit's "call-minus-put implied-vol spread" at 25 delta is exactly `-skew_25d`. They are one
   arm. `assert_no_negated_duplicate` pins that they are never both carried.
2. The shipped `term_slope_60_30` is EXACTLY `atm_iv_60 - atm_iv_30` and is NOT the construction
   O16 validated, which is `atm_mid - atm_front`. Spearman between them is only +0.5744. The arm
   here uses `atm_iv_60 - atm_iv_front`; `FORBIDDEN_COLUMNS` pins that the shipped column never
   enters the arm path.
3. The derived layer starts 2016 against a panel starting 2009, so 29 of 69 rebalance dates carry
   ZERO coverage and all of them are early. Every half-split in this module is a split of the
   COVERED SUBSAMPLE. `halves` refuses to split anything shorter than `MIN_DATES * 2 + 1`.
"""
from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
#  Constants — every one fixed by the register, none discovered at runtime
# --------------------------------------------------------------------------- #
DERIVED_DIR = r"C:/Users/donni/Downloads/valuation-tool/data/options_derived"

MAX_STALE_DAYS = 7          # join staleness ceiling, calendar days
MIN_NAMES = 20              # names required in a cross-section to score it
MIN_DATES = 16              # the shipped holdout_compare_panels floor

IC_BAR = 2.71               # X7's calibrated theme-IC p95. AN EXTRAPOLATION on this subsample.
LS_HAC_FLOOR = 2.2837       # session 10's calibrated long-short HAC p95. ALSO AN EXTRAPOLATION.
POWER_BAR = 2.0             # the audit's own power-control bar

#: The seven themes that carry weight. `low_risk` is zeroed live, `growth` and `sentiment` are
#: not in the weighted set, so none of the three is an incumbent to residualise against.
INCUMBENTS: Tuple[str, ...] = ("value", "quality", "momentum", "insider",
                               "capital_discipline", "size", "institutional")

#: The ONLY derived columns the arm path may read (register §2.1). Anything else is a void
#: condition, so this tuple is the thing tests assert against rather than the code's behaviour.
ALLOWED_DERIVED_COLUMNS: Tuple[str, ...] = ("date", "atm_iv_60", "atm_iv_front",
                                            "iv_rank", "skew_25d")

#: Present on the derived layer and deliberately NOT used. `term_slope_60_30` is the near-miss of
#: register §0.3: it computes cleanly, raises nothing, and answers a question O16 never validated.
FORBIDDEN_COLUMNS: Tuple[str, ...] = ("term_slope_60_30", "atm_iv_30", "iv_call_25d",
                                      "iv_put_25d", "atm_iv_14", "iv_pct")

ARMS: Tuple[str, ...] = ("term_slope", "iv_rank", "skew_25d", "surface")
COMPONENT_ARMS: Tuple[str, ...] = ("term_slope", "iv_rank", "skew_25d")

#: Declared a priori from the literature. Xing-Zhang-Zhao: steepest-smirk stocks UNDERPERFORM,
#: and `skew_25d` is put-minus-call IV, so high smirk => low forward return => NEGATIVE IC.
#: `term_slope` and `iv_rank` have no published cross-sectional stock-return sign, so they are
#: TWO-SIDED and a sign-agreement clause between halves does the work a declared sign would.
DECLARED_SIGN: Dict[str, int] = {"skew_25d": -1}


class RegisterViolation(AssertionError):
    """Raised when a void condition of the register would be breached."""


# --------------------------------------------------------------------------- #
#  1. features
# --------------------------------------------------------------------------- #
def build_arm_columns(daily: pd.DataFrame) -> pd.DataFrame:
    """Derive the three arm columns from one ticker's daily derived frame.

    `term_slope` is `atm_iv_60 - atm_iv_front` — the O16 construction (register §0.3) — and NOT
    the shipped `term_slope_60_30`, which is a 30-day-tenor object correlating with it at only
    +0.5744. Reading the shipped column here would produce a clean-looking verdict about a
    construction O16 never validated.
    """
    if "date" not in daily.columns:
        raise RegisterViolation("derived frame has no `date` column")
    out = pd.DataFrame({"date": pd.to_datetime(daily["date"])})

    def num(c):
        return (pd.to_numeric(daily[c], errors="coerce").astype(float)
                if c in daily.columns else pd.Series(np.nan, index=daily.index, dtype=float))

    out["term_slope"] = num("atm_iv_60") - num("atm_iv_front")
    out["iv_rank"] = num("iv_rank")
    out["skew_25d"] = num("skew_25d")
    return out.sort_values("date").reset_index(drop=True)


def assert_no_negated_duplicate(frame: pd.DataFrame, cols: Sequence[str],
                               tol: float = 1e-12) -> dict:
    """C5 — no arm may be another arm's negation.

    `skew_25d` and the call-minus-put spread differ by exactly a sign, and carrying both would
    charge two trials for one hypothesis while reporting two 'independent' results that are the
    same number twice. This is the `illiq`/`spread_pct` defect class, pinned rather than trusted.
    """
    cols = [c for c in cols if c in frame.columns]
    found = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            ss = frame[[a, b]].dropna()
            if len(ss) < 50:
                continue
            x = ss[a].values.astype(float)
            y = ss[b].values.astype(float)
            if float(np.max(np.abs(x + y))) <= tol:
                found.append((a, b))
    if found:
        raise RegisterViolation(f"negated duplicate arms: {found}")
    return {"checked": list(cols), "negated_pairs": found, "ok": True}


# --------------------------------------------------------------------------- #
#  2. the point-in-time join
# --------------------------------------------------------------------------- #
def join_pit(panel: pd.DataFrame, arms_by_ticker: Dict[str, pd.DataFrame],
             max_stale_days: int = MAX_STALE_DAYS,
             value_cols: Sequence[str] = COMPONENT_ARMS) -> Tuple[pd.DataFrame, dict]:
    """Attach each arm column to the panel using the last derived row STRICTLY BEFORE the date.

    `fwd_ret` runs from the rebalance date's CLOSE, so a same-day EOD surface would be
    contemporaneous rather than look-ahead. Strictly-before is used anyway: it costs one day of
    staleness on a quarterly signal and removes the argument entirely. The returned control
    counts violations, which must be exactly zero.

    `value_cols` defaults to U2's own three arms, so every existing caller is bit-identical
    (pinned by test). It is a parameter because `MA31`/`MA32` need the SAME strictly-before join
    on different columns, and re-typing this loop there would be audit B7's defect class - the
    one this project has now recorded four times.
    """
    pdates = pd.to_datetime(panel["date"]).values
    tick = panel["ticker"].values
    n = len(panel)
    value_cols = tuple(value_cols)
    cols = {a: np.full(n, np.nan) for a in value_cols}
    used = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")

    idx: Dict[str, Tuple[np.ndarray, Dict[str, np.ndarray]]] = {}
    for t, df in arms_by_ticker.items():
        d = df["date"].values.astype("datetime64[ns]")
        idx[t] = (d, {a: df[a].values.astype(float) for a in value_cols if a in df.columns})

    for i in range(n):
        ent = idx.get(tick[i])
        if ent is None:
            continue
        dts, vals = ent
        j = int(np.searchsorted(dts, pdates[i], side="left")) - 1   # STRICTLY BEFORE
        if j < 0:
            continue
        age = (pdates[i] - dts[j]).astype("timedelta64[D]").astype(int)
        if age > max_stale_days:
            continue
        used[i] = dts[j]
        for a, arr in vals.items():
            cols[a][i] = arr[j]

    out = panel.copy()
    for a in value_cols:
        out[a] = cols[a]
    out["_surface_asof"] = used

    viol = int(np.sum((~pd.isna(used)) & (used >= pdates)))
    covered = ~pd.isna(used)
    ctrl = {"n_rows": n, "n_joined": int(covered.sum()),
            "pit_violations": viol, "ok": viol == 0,
            "max_stale_days": max_stale_days}
    return out, ctrl


def covered_dates(frame: pd.DataFrame, min_names: int = MIN_NAMES) -> List:
    """Dates carrying at least `min_names` joined rows with at least one arm present."""
    have = frame[list(COMPONENT_ARMS)].notna().any(axis=1)
    g = frame.loc[have].groupby("date").size()
    return sorted(d for d, k in g.items() if k >= min_names)


def halves(dates: Sequence, min_dates: int = MIN_DATES) -> Tuple[List, List, object]:
    """Split with the boundary date EMBARGOED — the shipped `holdout_compare_panels` geometry.

    Refuses a split that cannot give both sides `min_dates`, rather than returning a thin half
    that would read like a result. Register §0.4: this may only ever be handed the COVERED
    subsample, never the full panel, whose early half contains no observations at all.
    """
    ds = list(dates)
    mid = len(ds) // 2
    early, late = ds[:mid], ds[mid + 1:]
    if len(early) < min_dates or len(late) < min_dates:
        raise RegisterViolation(
            f"cannot split {len(ds)} dates into two halves of >= {min_dates} "
            f"(got {len(early)}/{len(late)})")
    return early, late, ds[mid]


# --------------------------------------------------------------------------- #
#  3. IC, residualisation, and the verdict
# --------------------------------------------------------------------------- #
def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    ra = pd.Series(a).rank().values
    rb = pd.Series(b).rank().values
    sa, sb = ra.std(), rb.std()
    if not (sa > 0 and sb > 0):
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


#: A dispersion below this makes a t-stat meaningless. See `ic_series_degenerate`.
DEGENERATE_IC_SD = 1e-12


def ic_tstat(ics: Sequence[float]) -> Optional[float]:
    """The SHIPPED `theme_ic` arithmetic: mean / (sd_ddof1 / sqrt(n)).

    Deliberately identical to `fundamental_panel.theme_ic` so that the number compared against
    X7's 2.71 is the same statistic the bar was calibrated on. Audit M2 forbids comparing
    `ic_inference.t` — the clustered variant — to 2.71; this is not that statistic.

    A DEFECT INHERITED ON PURPOSE, REPORTED RATHER THAN SILENTLY REPAIRED. The shipped guard is
    `if sd > 0`, and whether a constant series has an exactly-zero floating-point sd is
    VALUE-DEPENDENT: `[0.1, 0.1, 0.1]` has sd ~5.8e-17, so the guard passes and this returns
    ~1.0e16. That is the same value-dependent zero-variance guard `SECTOR-NEUTRAL-B6` documented
    in `cross_sectional.zscore` (exact for 0.0 and 2.5, ~1e-16 for 0.1 and 1/3), in a new place.

    It is NOT repaired here, because repairing it would make this function stop being the shipped
    arithmetic and the 2.71 bar would then apply to a statistic it was not calibrated on. Instead
    `ic_series_degenerate` is checked by the verdict path, so an absurd t can never be READ as a
    pass. The underlying defect belongs to the edge lane and is reported, not fixed.
    """
    a = np.asarray([x for x in ics if x == x], dtype=float)
    if len(a) < 2:
        return None
    sd = float(a.std(ddof=1))
    if not (sd > 0):
        return 0.0
    return float(a.mean() / (sd / (len(a) ** 0.5)))


def ic_series_degenerate(ics: Sequence[float], tol: float = DEGENERATE_IC_SD) -> bool:
    """True when an IC series carries no usable dispersion, so its t-stat means nothing."""
    a = np.asarray([x for x in ics if x == x], dtype=float)
    if len(a) < 2:
        return True
    return float(a.std(ddof=1)) <= tol


def residualise(g: pd.DataFrame, cand: str, incumbents: Sequence[str]) -> Optional[Tuple[np.ndarray, np.ndarray, float]]:
    """Cross-sectional OLS of `cand` on the incumbent themes WITH an intercept; keep the residual.

    The PEAD template. A residual IC near zero with a strong raw IC means the candidate is a
    repackaging of what the composite already carries; a residual IC that survives is the only
    thing that justifies a new input.
    """
    inc = [c for c in incumbents if c in g.columns]
    ss = g.dropna(subset=[cand, "fwd_ret"] + inc)
    if len(ss) < MIN_NAMES or not inc:
        return None
    X = np.column_stack([np.ones(len(ss))] + [ss[c].values.astype(float) for c in inc])
    y = ss[cand].values.astype(float)
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    resid = y - X @ beta
    var = float(np.var(y))
    r2 = (1.0 - float(np.var(resid)) / var) if var > 0 else float("nan")
    return resid, ss["fwd_ret"].values.astype(float), r2


def arm_ic(frame: pd.DataFrame, cand: str, dates: Sequence,
           incumbents: Sequence[str] = INCUMBENTS) -> dict:
    """Raw and incremental IC series over `dates`, plus coverage and mean R^2."""
    raw, res, r2s, used = [], [], [], []
    sub = frame[frame["date"].isin(list(dates))]
    for d, g in sub.groupby("date"):
        ss = g.dropna(subset=[cand, "fwd_ret"])
        if len(ss) >= MIN_NAMES:
            ic = _spearman(ss[cand].values.astype(float), ss["fwd_ret"].values.astype(float))
            if ic == ic:
                raw.append(ic)
        out = residualise(g, cand, incumbents)
        if out is not None:
            r, fr, r2 = out
            ic = _spearman(r, fr)
            if ic == ic:
                res.append(ic)
                r2s.append(r2)
                used.append(d)
    cov = float(sub[cand].notna().mean()) if len(sub) else 0.0
    return {"n_dates_raw": len(raw), "n_dates_incremental": len(res),
            "raw_median_ic": float(np.median(raw)) if raw else None,
            "raw_ic_tstat": ic_tstat(raw),
            "incremental_median_ic": float(np.median(res)) if res else None,
            "incremental_ic_tstat": ic_tstat(res),
            "incremental_degenerate": ic_series_degenerate(res),
            "mean_r2_on_incumbents": float(np.mean(r2s)) if r2s else None,
            "coverage": cov}


def arm_verdict(t_early: Optional[float], t_late: Optional[float], arm: str,
                bar: float = IC_BAR, power_ok: bool = True,
                degenerate_early: bool = False, degenerate_late: bool = False) -> dict:
    """ELIGIBLE only if BOTH halves clear `bar` in absolute value AND the signs agree.

    Two-sided arms (`term_slope`, `iv_rank`) have no declared sign, so the sign-agreement clause
    substitutes for one — O14's device. `skew_25d` has a DECLARED negative sign, and a positive
    incremental IC on it is a CONTRADICTION, never a pass, however large.

    Ambiguous against the threshold is a NULL (RUN_RULES A6): `>=` is applied to the number as
    measured and nothing is rounded toward it.
    """
    if not power_ok:
        return {"verdict": "UNINTERPRETABLE",
                "why": "no power control cleared on this subsample; a null here is not a "
                       "negative result", "t_early": t_early, "t_late": t_late}
    if t_early is None or t_late is None:
        return {"verdict": "NOT_COMPUTABLE", "t_early": t_early, "t_late": t_late}
    if degenerate_early or degenerate_late:
        # An IC series with no dispersion produces a t of ~1e16 under the shipped guard
        # (see `ic_tstat`). It must never be readable as a pass.
        return {"verdict": "DEGENERATE", "t_early": t_early, "t_late": t_late,
                "why": "IC series carries no dispersion; its t-stat is meaningless"}

    declared = DECLARED_SIGN.get(arm)
    se, sl = int(np.sign(t_early)), int(np.sign(t_late))
    ce, cl = abs(t_early) >= bar, abs(t_late) >= bar

    if declared is not None:
        # A wrong-signed half cannot count toward a pass on a declared-sign arm.
        ce = ce and se == declared
        cl = cl and sl == declared
        if (abs(t_early) >= bar and se != declared) or (abs(t_late) >= bar and sl != declared):
            contradicts = True
        else:
            contradicts = False
    else:
        contradicts = False

    signs_agree = (se == sl) and se != 0
    if ce and cl and signs_agree:
        v = "ADOPT-ELIGIBLE"
    elif ce or cl:
        v = "NOT_REPLICATED"
    else:
        v = "REJECTED"
    if v == "ADOPT-ELIGIBLE" and declared is None and not signs_agree:
        v = "NOT_REPLICATED"
    return {"verdict": v, "t_early": t_early, "t_late": t_late, "bar": bar,
            "clears_early": bool(ce), "clears_late": bool(cl),
            "signs_agree": bool(signs_agree), "declared_sign": declared,
            "contradicts_declared_sign": bool(contradicts),
            "sibling_label": "1 of 4 sibling arms" if v == "NOT_REPLICATED" else None}


def power_verdict(controls: Dict[str, dict], bar: float = POWER_BAR) -> dict:
    """The audit's own gate on INTERPRETATION: does a known-real signal clear on these rows?

    If neither control clears, every null in the register is reported UNINTERPRETABLE rather than
    as a negative result. That rule is fixed in the register before the controls were run.
    """
    cleared = {k: bool(v.get("raw_ic_tstat") is not None and abs(v["raw_ic_tstat"]) >= bar)
               for k, v in controls.items()}
    return {"bar": bar, "cleared": cleared, "any_cleared": any(cleared.values()),
            "detail": {k: v.get("raw_ic_tstat") for k, v in controls.items()}}


# --------------------------------------------------------------------------- #
#  4. the composite arm — orientation learned where the measurement is not taken
# --------------------------------------------------------------------------- #
def orient_and_blend(frame: pd.DataFrame, decide_dates: Sequence,
                     components: Sequence[str] = COMPONENT_ARMS,
                     incumbents: Sequence[str] = INCUMBENTS) -> Tuple[pd.Series, dict]:
    """Sign each component by its DECIDE-half incremental IC, then blend. Measure elsewhere.

    No sign is declared for the composite, and none is invented: the orientation is fitted on the
    half where the verdict is not read (the S14 / LOO decide-then-measure discipline). A component
    whose decide-half IC is unusable is dropped from the blend rather than given an arbitrary sign.
    """
    signs, dropped = {}, []
    for c in components:
        t = arm_ic(frame, c, decide_dates, incumbents).get("incremental_ic_tstat")
        if t is None or t == 0:
            dropped.append(c)
            continue
        signs[c] = -1.0 if t < 0 else 1.0
    if not signs:
        raise RegisterViolation("no component could be oriented on the decide half")

    num = pd.Series(0.0, index=frame.index)
    den = pd.Series(0.0, index=frame.index)
    for c, s in signs.items():
        v = frame[c] * s
        ok = v.notna()
        num[ok] += v[ok]
        den[ok] += 1.0
    return (num / den).where(den > 0), {"signs": signs, "dropped": dropped}
