"""
I-3 -- the crash-count gate, as a library.

`IDEAS_LEDGER.md` PART 3. Extracted from `scripts/ma28_riskcard.py` so that every register
asking "do names carrying flag X go on to crash more often than names that do not?" calls ONE
implementation. **`B7`'s lesson is the whole specification**: that audit found one idea written
four times and only one copy maintained, and `MA5` then found the same shape in the
Harvey-Liu-Zhu hurdle -- four definitions, one of them a frozen constant. The named consumers
are `E-4` (the market-tail crash flag), `E-5`/`INV-A` (the hazard curve of flagged names),
`E-8`/`X-SEED-1` (accounting flags versus option prices) and `O-1`'s C1.

**ZERO TRIALS. NO VERDICTS. NO NEW OUTCOME RELATIONSHIP IS COMPUTED HERE.** This module has no
hypothesis and no bar of its own; it is arithmetic plus refusals. The one outcome relationship
it ever evaluates is `MA28-CARD`'s own already-published one, recomputed in the validation
below and compared **for equality** rather than read for a verdict.

WHY THE BARS HAVE NO DEFAULTS, AND THIS IS THE DESIGN DECISION THAT MATTERS
---------------------------------------------------------------------------
The obvious way to share this machinery is to move `MA28`'s constants into the library. That is
the wrong way, and the record says why twice over.

`MA5` measured that a default is exactly how a bar freezes: `hlz_significant` defaulted to the
constant `|t| > 3.0`, which is `sqrt(2 ln N)` at `N = 90`, and it stayed there while this
project's `N` went past 90 on 2026-08-06 and on to 236. `power_gate.critical_value()` was then
written to **refuse to guess**, requiring exactly one of `n_trials` or `crit`.

The same hazard applies here with a sharper edge, because these are *pre-committed* bars.
`MA28`'s own source says it: *"EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a
measurement voids the item."* A library default would let a future register inherit `MA28`'s
2.0x ratio floor and 0.50pp absolute floor **without ever writing them down**, which is a
pre-registration that never happened. So `window_result` takes its bars keyword-only with **no
defaults at all**, and a caller that does not declare them gets a `TypeError` rather than
somebody else's bar.

What the library does own is the *arithmetic* -- the per-date statistic, the pooled rates, the
within-date permutation null, and the shape of the verdict record. That is the part `B7` wants
shared, and it is the part that has no register in it.

THE BAR LABELS ARE GENERATED FROM THE BARS, NEVER TYPED
-------------------------------------------------------
`MA28`'s result keys read `B2_ratio_ge_2.0x` and `B3_abs_diff_ge_0.50pp` -- the bar value is in
the key. Parameterising the bars while typing those keys as literals would produce a key saying
`2.0x` above a comparison against 3.0, which is this record's most repeated defect family: a
label that disagrees with the value it labels (`MA49`'s `n_names = 9  # 8 schemes + ...`,
`MA46`'s renamed quantity, `U3`'s `drag_vs_equity_pp` printing a gain). The keys are formatted
from the bars actually used, and a test pins that `MA28`'s two keys come out byte-identical at
`MA28`'s own bars.

QUOTE THE RATIO AND BOTH RATES; NEVER THE DIFFERENCE
-----------------------------------------------------
`MA28-CARD`'s standing instruction, and it is a measurement rather than a style preference: the
base rate is era-dependent (kept 0.3413% early against 1.3595% late, a 4x move spanning COVID
2020Q1 and 2022), so the absolute gap swings **0.86pp -> 2.39pp** between halves while the
ratio barely moves (**3.42 -> 2.93**). A card quoting *"1.6pp more likely"* would be quoting an
era average that describes neither half.

The difference is still computed, because `MA28`'s B1 and B3 legs are defined on it and the
per-date statistic *is* a difference. So the distinction the library enforces is between an
internal STATISTIC and a QUOTED FIGURE: `window_result` reports the difference; `quotable()`
returns the ratio and both rates and **has no difference field at all**, pinned by test.

AND NO RATIO IS QUOTED ON A HANDFUL OF EVENTS
----------------------------------------------
`MB8` found `MA28`'s flag firing on 3.56% of the top-decile book and catching **one crash of
eighty-four**. One crash is not a rate, and 1/407 divided by 52/8081 is not a ratio -- it is a
number that will be read as one. `quotable()` therefore takes a caller-declared `min_events`
and returns `ratio=None` with a stated reason when either bucket is below it, rather than
emitting a figure whose precision it cannot support.

A MISSING OUTCOME IS NOT AN ABSENT CRASH
-----------------------------------------
`crash_flag` is `fwd_ret <= threshold`, and under that comparison a NaN forward return is
`False` -- i.e. it counts as "did not crash". That is a fail-open, it is what `MA28` did, and
it is preserved so the arithmetic is `MA28`'s. What is added is that `coverage()` reports how
many rows had no computable outcome, so a consumer can see the size of the hole instead of
inheriting it silently. `MB8`'s finding is the general form: the bucket a rule cannot evaluate
is a real bucket and is not automatically the safe one.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "CRASH_GATE_RULE",
    "coverage",
    "crash_flag",
    "halves",
    "nw_t",
    "per_date_diff",
    "permutation_null",
    "pooled",
    "quotable",
    "required_dates",
    "required_rows",
    "window_result",
]

CRASH_GATE_RULE = (
    "Quote the ratio and BOTH rates, never the difference: the base rate is era-dependent "
    "(MA28-CARD measured kept 0.3413% early against 1.3595% late), so an absolute gap "
    "describes neither half. Report every rate with its event COUNT, and refuse a ratio when "
    "either bucket is below the register's declared min_events -- one crash is not a rate."
)


# --------------------------------------------------------------------------- primitives

def nw_t(x: Sequence[float], lag: int = 1) -> Optional[float]:
    """Newey-West(lag) t of a mean. The SHIPPED definition, imported and never re-typed.

    `MA5`'s rule: one definition per idea. `valuation.edge.statistics.mean_inference` is that
    definition, and `MA28` reaches it through this same call.
    """
    from valuation.edge.statistics import mean_inference
    r = mean_inference(list(map(float, x)), lag=lag)
    return float(r["t"]) if r and r.get("t") is not None else None


def crash_flag(fwd_ret, threshold: float) -> pd.Series:
    """The named bad outcome: `fwd_ret <= threshold`, over whatever window the panel carries.

    `threshold` is REQUIRED and negative by convention (`MA28` fixed -0.50 in its register).
    A NaN forward return compares False and so reads as "did not crash" -- see `coverage()`.
    """
    if threshold is None:
        raise ValueError("crash_gate.crash_flag: threshold is required, there is no default")
    return pd.to_numeric(fwd_ret, errors="coerce") <= float(threshold)


def coverage(fwd_ret) -> Dict[str, object]:
    """How many rows carry a computable outcome at all.

    Reported because `crash_flag` fails OPEN on a missing forward return. This is the COVERAGE
    RULE applied to the outcome rather than to a signal, and `MB8`'s generalisation of it: the
    bucket a rule cannot evaluate is a real bucket and is not automatically the safe one.
    """
    v = pd.to_numeric(fwd_ret, errors="coerce")
    n = int(len(v))
    ok = int(v.notna().sum())
    return {"rows": n, "rows_with_outcome": ok, "rows_without_outcome": n - ok,
            "coverage": (ok / n) if n else None,
            "note": "a row with no computable fwd_ret counts as NOT crashed; it is not a crash-free row"}


def halves(frame: pd.DataFrame, date_col: str = "date") -> tuple:
    """Split the dates in two with the middle one EMBARGOED.

    `MA28` §3.4's split, generalised off its hard-coded 69. An odd date count embargoes the
    exact middle; an even one embargoes the lower-middle date so neither half can borrow it.
    Returns `(early_frame, late_frame, boundary_date_str)`.
    """
    ds = sorted(frame[date_col].unique())
    if len(ds) < 3:
        raise ValueError(f"crash_gate.halves: need at least 3 dates, got {len(ds)}")
    mid = (len(ds) - 1) // 2
    early, boundary, late = ds[:mid], ds[mid], ds[mid + 1:]
    return (frame[frame[date_col].isin(early)],
            frame[frame[date_col].isin(late)],
            str(boundary)[:10])


def per_date_diff(df: pd.DataFrame, *, crash_col: str, flag_col: str = "flagged",
                  date_col: str = "date",
                  min_flagged_per_date: int, min_kept_per_date: int) -> pd.DataFrame:
    """d_t = P(crash | flagged, t) - P(crash | kept, t), on qualifying dates only.

    The date-qualification floors are REQUIRED. `MA28`'s register fixed them *before any value
    was seen*, precisely so a thin date could not be dropped after its number was read; a
    library default would hand the next register that protection without it having chosen the
    floors, which is a pre-registration that never happened.
    """
    if min_flagged_per_date is None or min_kept_per_date is None:
        raise ValueError("crash_gate.per_date_diff: both per-date floors are required")
    rows: List[Dict[str, object]] = []
    for d, g in df.groupby(date_col, sort=True):
        f = g[flag_col].to_numpy(dtype=bool)
        c = g[crash_col].to_numpy(dtype=bool)
        nf, nk = int(f.sum()), int((~f).sum())
        if nf < min_flagged_per_date or nk < min_kept_per_date:
            continue
        rows.append({"date": str(d)[:10], "n_flagged": nf, "n_kept": nk,
                     "rate_flagged": float(c[f].mean()), "rate_kept": float(c[~f].mean()),
                     "n_crash_flagged": int(c[f].sum()), "n_crash_kept": int(c[~f].sum())})
    r = pd.DataFrame(rows)
    if len(r):
        r["d"] = r["rate_flagged"] - r["rate_kept"]
    return r


def pooled(df: pd.DataFrame, *, crash_col: str, flag_col: str = "flagged") -> Dict[str, object]:
    """Pooled counts and rates, with the RATIO -- the figure that travels between eras.

    Every rate ships beside its event count, so a reader can see what a rate rests on.
    """
    f = df[flag_col].to_numpy(dtype=bool)
    c = df[crash_col].to_numpy(dtype=bool)
    nf, nk = int(f.sum()), int((~f).sum())
    rf = float(c[f].mean()) if nf else None
    rk = float(c[~f].mean()) if nk else None
    return {"n_flagged": nf, "n_kept": nk,
            "n_crash_flagged": int(c[f].sum()) if nf else 0,
            "n_crash_kept": int(c[~f].sum()) if nk else 0,
            "rate_flagged": rf, "rate_kept": rk,
            "rate_all": float(c.mean()) if len(c) else None,
            "ratio": (rf / rk) if (rf is not None and rk) else None}


def permutation_null(df: pd.DataFrame, *, crash_col: str, flag_col: str = "flagged",
                     date_col: str = "date", n_draws: int, seed: int,
                     min_flagged_per_date: int, min_kept_per_date: int) -> Optional[Dict[str, float]]:
    """Shuffle the FLAG within each date. `X7`'s method, `MA28`'s B1.

    This preserves each date's flagged COUNT and its crash outcomes EXACTLY and destroys only
    which names carry the flag, so the cross-sectional and time-series structure is held fixed
    and the flag's identity is the single thing under test.

    `n_draws` and `seed` are required: the draw sequence is part of the reported number, and a
    library-chosen seed would make two registers' nulls silently correlated.
    """
    rng = np.random.default_rng(int(seed))
    groups = []
    for d, g in df.groupby(date_col, sort=True):
        f = g[flag_col].to_numpy(dtype=bool)
        c = g[crash_col].to_numpy(dtype=bool)
        if int(f.sum()) < min_flagged_per_date or int((~f).sum()) < min_kept_per_date:
            continue
        groups.append((int(f.sum()), c))
    if not groups:
        return None
    draws = np.empty(int(n_draws), dtype=float)
    for i in range(int(n_draws)):
        ds = []
        for nf, c in groups:
            idx = rng.permutation(len(c))
            fs = np.zeros(len(c), dtype=bool)
            fs[idx[:nf]] = True
            ds.append(c[fs].mean() - c[~fs].mean())
        draws[i] = float(np.mean(ds))
    return {"p95": float(np.quantile(draws, 0.95)), "p50": float(np.median(draws)),
            "max": float(draws.max()), "n_draws": int(n_draws)}


# --------------------------------------------------------------------------- the record

def window_result(df: pd.DataFrame, label: str, *, crash_col: str, flag_col: str = "flagged",
                  date_col: str = "date", ratio_floor: float, abs_floor_pp: float,
                  n_perm: int, perm_seed: int,
                  min_flagged_per_date: int, min_kept_per_date: int,
                  hac_lag: int = 1) -> Dict[str, object]:
    """The three-leg record for one window. Every bar is keyword-only and has NO default.

    B1  the mean per-date difference clears its own within-date permutation p95
    B2  the pooled ratio clears `ratio_floor`
    B3  the mean per-date difference clears `abs_floor_pp`

    The B2/B3 key names are FORMATTED from the bars actually used, never typed -- see the
    module docstring.
    """
    pdd = per_date_diff(df, crash_col=crash_col, flag_col=flag_col, date_col=date_col,
                        min_flagged_per_date=min_flagged_per_date,
                        min_kept_per_date=min_kept_per_date)
    if not len(pdd):
        return {"label": label, "VOID": "no qualifying dates"}
    mean_d = float(pdd["d"].mean())
    po = pooled(df, crash_col=crash_col, flag_col=flag_col)
    null = permutation_null(df, crash_col=crash_col, flag_col=flag_col, date_col=date_col,
                            n_draws=n_perm, seed=perm_seed,
                            min_flagged_per_date=min_flagged_per_date,
                            min_kept_per_date=min_kept_per_date)
    b1 = bool(null and mean_d > null["p95"])
    b2 = bool(po["ratio"] is not None and po["ratio"] >= ratio_floor)
    b3 = bool(mean_d * 100.0 >= abs_floor_pp)
    return {
        "label": label,
        "n_dates": int(len(pdd)),
        "mean_per_date_diff": mean_d,
        "mean_per_date_diff_pp": mean_d * 100.0,
        "nw_t": nw_t(pdd["d"].tolist(), lag=hac_lag),
        "pooled": po,
        "permutation_null": null,
        "B1_clears_permutation_p95": b1,
        f"B2_ratio_ge_{ratio_floor}x": b2,
        f"B3_abs_diff_ge_{abs_floor_pp:.2f}pp": b3,
        "clears_all_three": bool(b1 and b2 and b3),
        "dates_with_zero_flagged_crashes": int((pdd["n_crash_flagged"] == 0).sum()),
    }


def quotable(po: Dict[str, object], *, min_events: int) -> Dict[str, object]:
    """The figures a card, a page or a write-up may quote. **There is no difference field.**

    `MA28-CARD`'s instruction, enforced structurally rather than remembered: the ratio and both
    rates travel; the absolute gap does not, because it is era-dependent and describes neither
    half of this panel.

    `min_events` is the caller's declared floor on how many crashes a rate has to rest on
    before a ratio may be formed from it. Below it the ratio is `None` with a reason -- `MB8`
    measured one crash in a flagged bucket of 407 and a ratio computed there would have been
    read as a rate.
    """
    if min_events is None:
        raise ValueError("crash_gate.quotable: min_events is required, there is no default")
    nf_c = int(po.get("n_crash_flagged") or 0)
    nk_c = int(po.get("n_crash_kept") or 0)
    thin = [name for name, k in (("flagged", nf_c), ("kept", nk_c)) if k < int(min_events)]
    out = {
        "rate_flagged": po.get("rate_flagged"),
        "rate_kept": po.get("rate_kept"),
        "n_flagged": po.get("n_flagged"),
        "n_kept": po.get("n_kept"),
        "n_crash_flagged": nf_c,
        "n_crash_kept": nk_c,
        "min_events_declared": int(min_events),
        "ratio": None if thin else po.get("ratio"),
        "ratio_withheld_because": None if not thin else (
            "the " + " and ".join(thin) + " bucket carries fewer than "
            f"{int(min_events)} crashes; a rate on that few events is a count, not a rate"),
        "rule": CRASH_GATE_RULE,
    }
    return out


# --------------------------------------------------------------------------- required-n

def required_dates(effect: float, sd: float, *, n_trials: Optional[int] = None,
                   crit: Optional[float] = None, power: float = 0.80) -> Dict[str, object]:
    """How many DATES the per-date-difference statistic needs to resolve `effect`.

    `effect` and `sd` are in the same units (pp or fraction) -- the per-date difference and its
    cross-date standard deviation. Delegates to `power_gate` for both the critical value and
    the arithmetic; the critical value has no default there and none is invented here.
    """
    from valuation.edge.power_gate import critical_value, required_n, z_for_power
    c = critical_value(n_trials=n_trials, crit=crit)
    if sd is None or not (float(sd) > 0):
        raise ValueError("crash_gate.required_dates: sd must be positive")
    std_effect = float(effect) / float(sd)
    zp = z_for_power(power)
    return {"effect": float(effect), "sd": float(sd), "standardised_effect": std_effect,
            "crit": float(c), "power": float(power), "z_power": float(zp),
            "required_dates": required_n(std_effect, crit=c, z_power=zp)}


def required_rows(base_rate: float, ratio: float, flagged_share: float, *,
                  n_trials: Optional[int] = None, crit: Optional[float] = None,
                  power: float = 0.80) -> Dict[str, object]:
    """How many ROWS a pooled two-proportion crash-rate comparison needs.

    `E-4`'s hook: given the clean-subset base rate (its entry names 0.87%/qtr) and a target
    ratio, how large must the sample be before the design could see it? Answered BEFORE the
    run, which is `MB22`'s whole point and `RUN_RULES` PART A rule 11.

    THE ALLOCATION IS NOT IGNORED, AND THAT IS THE POINT. The textbook two-proportion formula
    assumes equal group sizes. This book is nowhere near it -- `MA28` flags 5.74% of the panel
    and `MB8` measured 3.56% of the top-decile book -- and an equal-n figure understates the
    requirement by roughly `1 / (4 s (1-s))`, about 7.5x at s = 0.036. So the variance is
    formed at the ACTUAL allocation:

        se^2 = p1(1-p1)/(s n) + p0(1-p0)/((1-s) n)

    and `n` is solved so that `|p1 - p0| >= (crit + z_power) * se`. The equal-n figure is
    reported beside it, labelled, so the gap is visible rather than inherited.

    It is a NORMAL APPROXIMATION and it is unreliable when the expected event count is small,
    so the expected counts ship with it and the caller is told when they are thin.
    """
    from valuation.edge.power_gate import critical_value, z_for_power
    c = float(critical_value(n_trials=n_trials, crit=crit))
    z_power = float(z_for_power(power))
    p0 = float(base_rate)
    p1 = p0 * float(ratio)
    s = float(flagged_share)
    if not (0.0 < s < 1.0):
        raise ValueError("crash_gate.required_rows: flagged_share must be strictly in (0, 1)")
    if not (0.0 < p0 < 1.0) or not (0.0 < p1 < 1.0):
        raise ValueError("crash_gate.required_rows: both rates must be strictly in (0, 1)")
    delta = p1 - p0
    if delta == 0:
        raise ValueError("crash_gate.required_rows: ratio of exactly 1.0 has no detectable effect")
    var_unit = p1 * (1 - p1) / s + p0 * (1 - p0) / (1 - s)
    n_total = ((c + z_power) ** 2) * var_unit / (delta ** 2)
    # the textbook equal-allocation figure, reported for contrast and never as the answer
    var_equal = p1 * (1 - p1) * 2.0 + p0 * (1 - p0) * 2.0
    n_equal = ((c + z_power) ** 2) * var_equal / (delta ** 2)
    exp_flag_events = n_total * s * p1
    exp_kept_events = n_total * (1 - s) * p0
    thin = bool(min(exp_flag_events, exp_kept_events) < 10.0)
    return {
        "base_rate": p0, "ratio": float(ratio), "flagged_rate": p1,
        "flagged_share": s, "crit": c, "power": float(power),
        "required_rows_total": int(math.ceil(n_total)),
        "required_rows_flagged": int(math.ceil(n_total * s)),
        "required_rows_equal_allocation_for_contrast": int(math.ceil(n_equal)),
        "allocation_penalty_x": (n_total / n_equal) if n_equal else None,
        "expected_crashes_flagged": exp_flag_events,
        "expected_crashes_kept": exp_kept_events,
        "normal_approximation_thin": thin,
        "note": ("normal approximation; expected event counts below ~10 make it unreliable and "
                 "the flag above says when that is the case"),
    }
