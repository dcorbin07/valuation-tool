"""persistence_null.py — a null that REMEMBERS.  [MB21]

`fundamental_panel.placebo_panel` permutes the signal columns as a block **within each rebalance
date**. That is the strongest available null for a *cross-sectional* question and it is exactly
right for the questions X7 built it for. It has one property that matters here and is easy to miss:
**it destroys the signal's time-series persistence completely.** Measured on the shipped composite,
the real per-name rank autocorrelation across rebalances is 0.5677 at one quarter and still 0.3983
at two years; `placebo_panel`'s is 0.000.

Boudoukh-Richardson-Whitelaw (RFS 2008) is that a PERSISTENT regressor combined with OVERLAPPING
long-horizon returns makes long-horizon beta and R-squared rise MECHANICALLY under a
no-predictability null. A null with no memory cannot produce that artifact, so it cannot exclude
it. `S22`'s term-structure claim is measured on exactly that axis.

THE CONSTRUCTION. Draw ONE permutation of the name list and apply it at EVERY date: row
(date d, name i) takes its signal columns from row (d, pi(i)). That is the single change from
`placebo_panel` -- one permutation for the whole panel instead of an independent one per date.

  * per-name persistence is the REAL persistence, by construction: a name inherits a real name's
    whole path, so the autocorrelation is not approximated, it is inherited;
  * whole rows still move together, so the cross-theme correlation matrix survives;
  * `fwd_ret*`, `marketcap`, `sector` and `bench_ret` do not move, so the only thing destroyed is
    the association between signal and return -- which is the null.

THE COST, stated rather than discovered. A name survives a date only if its DONOR is present that
date, so coverage falls to roughly two thirds and the per-date cross-section drops from ~1,557 to
~950. `thinned_within_date_panel` below exists to price that: it applies the SAME donor-absence
mask to an ordinary within-date permutation, so coverage and memory can be told apart.

WHAT NOT TO DO, measured before it could be adopted. The obvious way to protect coverage is to
permute within exact presence-pattern strata (986 of 2,531 names live on all 69 dates; ~97% of rows
survive). It is NOT A NULL: ~170 names per draw end up paired with themselves, and the residual
association with forward returns is live -- H=504 median rank IC +0.01067 at t +4.106. Pairing
within a lifespan stratum pairs a name with a name of similar era and size, and `size` is both the
most persistent theme (0.9915) and, per `X3`, the carrier of the composite's entire significance.
**Stratifying to protect coverage smuggles the signal back in.** Kept here as
`stratified_panel` so the disqualification is reproducible, and refused by
`assert_not_primary` so it cannot quietly become the primary instrument later.

Everything here is fixed by `PREREG_mb21_persistence_null.md`, committed ALONE at ec55efe before
this file existed. Nothing in it restates a threshold from a result.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

__all__ = [
    "PRIMARY", "THINNED", "STRATIFIED", "RegisterViolation",
    "donor_map", "persistence_panel", "thinned_within_date_panel", "stratified_panel",
    "assert_not_primary", "assert_no_forward_return_permuted",
    "composite_by_date", "rank_autocorrelation", "association_ic", "coverage_block",
    "format_coverage",
]

PRIMARY = "persistence_preserving_null"
THINNED = "within_date_null_thinned"
STRATIFIED = "stratified_presence_pattern_null"

#: The register's own floor: a placebo cross-section thinner than this cannot support a decile
#: sort at n_q = 10, and a floor computed from one would be measuring the thinning.
MIN_PLACEBO_CROSS_SECTION = 100


class RegisterViolation(RuntimeError):
    """Raised when a caller asks for something the register forbids."""


# --------------------------------------------------------------------------- donors


def donor_map(names: Sequence, seed: int) -> Dict:
    """ONE uniform permutation of the name list. `donor[name]` is the name it inherits from."""
    rng = np.random.default_rng(int(seed))
    arr = np.asarray(sorted(names))
    return dict(zip(arr, arr[rng.permutation(len(arr))]))


def _row_index(panel: pd.DataFrame) -> Dict[Tuple, int]:
    d = panel["date"].to_numpy()
    t = panel["ticker"].to_numpy()
    return {(d[i], t[i]): i for i in range(len(panel))}


def _apply_donors(panel: pd.DataFrame, donor: Dict, cols: Sequence[str]):
    """Pull each row's signal columns from its donor's row on the SAME date.

    Returns `(panel_copy, source_row_or_-1)`. A row whose donor is absent that date gets NaN
    across every permuted column -- it is not silently left at its own value, which would leak
    the real signal for exactly the rows the permutation failed to move.
    """
    pos = _row_index(panel)
    d = panel["date"].to_numpy()
    t = panel["ticker"].to_numpy()
    src = np.full(len(panel), -1, dtype=np.int64)
    for i in range(len(panel)):
        j = pos.get((d[i], donor[t[i]]))
        if j is not None:
            src[i] = j
    out = panel.copy()
    ok = src >= 0
    for c in cols:
        v = pd.to_numeric(panel[c], errors="coerce").to_numpy(dtype=float)
        nv = np.full(len(panel), np.nan, dtype=float)
        nv[ok] = v[src[ok]]
        out[c] = nv
    return out, src


def assert_no_forward_return_permuted(cols: Sequence[str]) -> None:
    """S22's own guard, kept verbatim: a forward return must never be permuted."""
    leaked = [c for c in cols if str(c).startswith("fwd_ret") or str(c) in ("bench_ret",)]
    if leaked:
        raise RegisterViolation(
            "a forward return would be permuted, which fabricates predictability: %r" % (leaked,))


# --------------------------------------------------------------------------- the null


def persistence_panel(panel: pd.DataFrame, seed: int, cols: Sequence[str]):
    """MB21's PRIMARY instrument. Returns `(panel, info)`.

    `info` carries the realised coverage and the fixed-point count, both of which the register
    requires reported rather than assumed.
    """
    cols = list(cols)
    assert_no_forward_return_permuted(cols)
    donor = donor_map(pd.unique(panel["ticker"].to_numpy()), seed)
    out, src = _apply_donors(panel, donor, cols)
    ok = src >= 0
    return out, {
        "instrument": PRIMARY, "seed": int(seed),
        "rows_total": int(len(panel)), "rows_kept": int(ok.sum()),
        "rows_kept_frac": float(ok.mean()),
        "fixed_points": int(sum(1 for k, v in donor.items() if k == v)),
        "n_names": int(len(donor)),
    }


def thinned_within_date_panel(panel: pd.DataFrame, seed: int, cols: Sequence[str]):
    """C5 -- the THINNING control, and the only way to tell coverage from memory apart.

    An ordinary within-date permutation (`placebo_panel`'s method, so NO persistence) carrying the
    SAME donor-absence mask the primary draw at this seed produces. Any floor movement it shows is
    attributable to the thinner cross-section and to nothing else.

    It is a DIAGNOSTIC. Per the register's section 7 it may never be used to rescue a crossing.
    """
    from ..edge.fundamental_panel import placebo_panel

    cols = list(cols)
    assert_no_forward_return_permuted(cols)
    donor = donor_map(pd.unique(panel["ticker"].to_numpy()), seed)
    _, src = _apply_donors(panel, donor, cols)
    mask_absent = src < 0

    out = placebo_panel(panel, seed=seed, cols=cols)
    for c in cols:
        # copy=True is load-bearing: `to_numpy` can hand back a READ-ONLY view of the frame's
        # block, and writing the mask into it raises. Caught by this module's own tests before
        # it could take down a three-hour floors run halfway through.
        v = pd.to_numeric(out[c], errors="coerce").to_numpy(dtype=float, copy=True)
        v[mask_absent] = np.nan
        out[c] = v
    return out, {
        "instrument": THINNED, "seed": int(seed),
        "rows_total": int(len(panel)), "rows_kept": int((~mask_absent).sum()),
        "rows_kept_frac": float((~mask_absent).mean()),
    }


def stratified_panel(panel: pd.DataFrame, seed: int, cols: Sequence[str]):
    """DISQUALIFIED -- kept so the disqualification stays reproducible, never as an instrument.

    Permutes names within exact presence-pattern strata, which preserves ~97% of rows and leaves
    roughly 170 names per draw paired with THEMSELVES. See this module's docstring and section 2b
    of the register. `assert_not_primary` refuses to let it be used as the primary.
    """
    cols = list(cols)
    assert_no_forward_return_permuted(cols)
    dates = sorted(pd.unique(panel["date"].to_numpy()))
    idx = {d: i for i, d in enumerate(dates)}
    pattern: Dict = {}
    for t, g in panel.groupby("ticker", sort=False):
        k = 0
        for d in g["date"]:
            k |= 1 << idx[d]
        pattern[t] = k
    strata = defaultdict(list)
    for t, k in pattern.items():
        strata[k].append(t)

    rng = np.random.default_rng(int(seed))
    donor: Dict = {}
    pool: List = []
    for _k, ts in sorted(strata.items()):
        ts = sorted(ts)
        if len(ts) >= 2:
            arr = np.asarray(ts)
            donor.update(dict(zip(arr, arr[rng.permutation(len(arr))])))
        else:
            pool.extend(ts)
    if pool:
        arr = np.asarray(sorted(pool))
        donor.update(dict(zip(arr, arr[rng.permutation(len(arr))])))

    out, src = _apply_donors(panel, donor, cols)
    ok = src >= 0
    return out, {
        "instrument": STRATIFIED, "seed": int(seed),
        "rows_kept_frac": float(ok.mean()),
        "fixed_points": int(sum(1 for k, v in donor.items() if k == v)),
        "n_strata": int(len(strata)),
        "disqualified": True,
        "why": ("names are paired within a lifespan stratum, so ~170 per draw pair with "
                "themselves and the residual association with fwd_ret is live"),
    }


def assert_not_primary(instrument: str) -> None:
    """The register's void condition 8, enforced rather than promised."""
    if instrument == STRATIFIED:
        raise RegisterViolation(
            "the stratified presence-pattern variant is DISQUALIFIED as a null (register 2b): "
            "it leaves names paired with themselves and its residual association with fwd_ret "
            "is live. It may be reported as a measurement; it may not be the primary.")


# --------------------------------------------------------------------------- validation


def composite_by_date(panel: pd.DataFrame, cols: Sequence[str], weights: Dict,
                      dates: Optional[Sequence] = None) -> Dict:
    """{date: Series(composite indexed by ticker)} through the SHIPPED composite.

    `composite_from_frame` renormalises by the present-weight mass -- audit B7's convention, and
    the composite `S22` actually scores. The audit's own MB21 persistence figures come from a
    composite that does NOT renormalise, which is why they read 0.5802 / 0.4099 against this
    module's 0.5677 / 0.3983. Immaterial to the premise; material to reproducing a number.
    """
    from ..edge.fundamental_panel import composite_from_frame
    from ..screener.cross_sectional import zscore

    dates = sorted(pd.unique(panel["date"].to_numpy())) if dates is None else list(dates)
    out = {}
    for d in dates:
        sub = panel[panel["date"] == d]
        c = composite_from_frame(sub, list(cols), weights, zscore)
        out[d] = pd.Series(np.asarray(c, dtype=float), index=sub["ticker"].to_numpy())
    return out


def rank_autocorrelation(comp_by_date: Dict, lag: int, min_names: int = 30) -> Dict:
    """Per-name rank autocorrelation of the composite across rebalances, at `lag` rebalances."""
    from ..edge.fundamental_panel import _spearman

    dates = sorted(comp_by_date)
    vals, pairs = [], []
    for i in range(len(dates) - lag):
        a, b = comp_by_date[dates[i]], comp_by_date[dates[i + lag]]
        common = a.index.intersection(b.index)
        x = a.loc[common].to_numpy(dtype=float)
        y = b.loc[common].to_numpy(dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < min_names:
            continue
        r = _spearman(x[ok], y[ok])
        if r == r:
            vals.append(float(r))
            pairs.append(int(ok.sum()))
    if not vals:
        return {"lag": lag, "n_pairs": 0}
    return {"lag": lag, "n_pairs": len(vals), "mean": float(np.mean(vals)),
            "median": float(np.median(vals)), "min": float(np.min(vals)),
            "max": float(np.max(vals)), "median_names": int(np.median(pairs))}


def association_ic(panel: pd.DataFrame, cols: Sequence[str], weights: Dict, ret_col: str,
                   dates: Optional[Sequence] = None, min_names: int = 30) -> Dict:
    """The null's residual association with forward returns. It must be nil.

    This is the check that disqualified the stratified variant, so it is applied to the primary
    with equal force rather than being reserved for the instrument it happened to kill.
    """
    from ..edge.fundamental_panel import _spearman, _tstat

    comp = composite_by_date(panel, cols, weights, dates)
    ics = []
    for d, c in comp.items():
        sub = panel[panel["date"] == d]
        f = pd.to_numeric(sub[ret_col], errors="coerce").to_numpy(dtype=float)
        x = c.to_numpy(dtype=float)
        ok = np.isfinite(x) & np.isfinite(f)
        if ok.sum() < min_names:
            continue
        r = _spearman(x[ok], f[ok])
        if r == r:
            ics.append(float(r))
    if not ics:
        return {"ret_col": ret_col, "n_dates": 0}
    return {"ret_col": ret_col, "n_dates": len(ics), "median_ic": float(np.median(ics)),
            "mean_ic": float(np.mean(ics)), "ic_t": _tstat(ics)}


# --------------------------------------------------------------------------- coverage


def coverage_block(real: pd.DataFrame, placebo: pd.DataFrame, cols: Sequence[str],
                   dates: Optional[Sequence] = None) -> Dict:
    """MB7's rule, ported: print the coverage the statistic is ACTUALLY measured on.

    RUN_RULES PART A rule 10 requires a register to disclose its EFFECTIVE coverage rather than
    the coverage it appears to have. Here the raw panel and the panel the null scores on differ by
    a third of their rows, and a reader who is told only the raw figure is being told the wrong
    number.
    """
    dates = sorted(pd.unique(real["date"].to_numpy())) if dates is None else list(dates)
    cols = list(cols)

    def per_date(df):
        out = []
        for d in dates:
            sub = df[df["date"] == d]
            ok = sub[cols].notna().any(axis=1).to_numpy()
            out.append(int(ok.sum()))
        return out

    r = per_date(real)
    p = per_date(placebo)
    return {
        "dates_scored": len(dates),
        "real_rows_with_signal": int(sum(r)), "effective_rows_with_signal": int(sum(p)),
        "effective_row_frac": (float(sum(p)) / float(sum(r))) if sum(r) else None,
        "real_cross_section": {"min": min(r), "median": int(np.median(r)), "max": max(r)},
        "effective_cross_section": {"min": min(p), "median": int(np.median(p)), "max": max(p)},
        "min_cross_section_floor": MIN_PLACEBO_CROSS_SECTION,
        "clears_cross_section_floor": bool(min(p) >= MIN_PLACEBO_CROSS_SECTION),
    }


def format_coverage(block: Dict) -> str:
    """ASCII only -- this prints to a cp1252 console."""
    rc, ec = block["real_cross_section"], block["effective_cross_section"]
    return (
        "EFFECTIVE COVERAGE (register C8; RUN_RULES PART A rule 10)\n"
        "  dates scored            %d\n"
        "  rows with signal        real %d -> effective %d (%.1f%%)\n"
        "  per-date cross-section  real median %d [%d, %d]\n"
        "                          eff. median %d [%d, %d]\n"
        "  floor %d names/date     %s\n"
        % (block["dates_scored"], block["real_rows_with_signal"],
           block["effective_rows_with_signal"], 100.0 * (block["effective_row_frac"] or 0.0),
           rc["median"], rc["min"], rc["max"], ec["median"], ec["min"], ec["max"],
           block["min_cross_section_floor"],
           "CLEARS" if block["clears_cross_section_floor"] else "FAILS")
    )
