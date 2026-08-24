"""
E-5 / INV-A -- the hazard curve of flagged names, as a library.

`PREREG_e5_hazard_curve.md` §2. The question is WHEN a flagged name crashes, not whether:
the conditional hazard of a >=50% cumulative loss from the flag date, by quarter, over four
quarters, flagged against kept.

**THIS MODULE OWNS THE SURVIVAL CONSTRUCTION AND NOTHING ELSE.** Every crash RATE, RATIO,
per-date difference, permutation null of the single-quarter kind, coverage report and
required-n figure comes from `valuation.studies.crash_gate` (`I-3`), which is the one shared
implementation of that arithmetic. `B7`'s lesson is why: an idea written twice is an idea
maintained once. What is genuinely new here -- entering a row, censoring it, and asking which
QUARTER its event fell in -- lives here, and it is deliberately a small surface.

WHY NO BAR HAS A DEFAULT
------------------------
`I-3`'s design decision, inherited verbatim and for the same reason. `MA5` measured that a
default is exactly how a bar freezes (`hlz_significant` defaulted to `|t| > 3.0`, which is
`sqrt(2 ln N)` at `N = 90`, and stayed there while `N` went past 90 and on to 237). Every
threshold below -- the crash level, the quarter length, the horizon, the per-date
qualification counts, the draw count and the seed -- is keyword-only with **no default**, so a
future consumer that does not declare them gets a `TypeError` rather than E-5's
pre-registration without having written one.

RIGHT-CENSORING IS THE POINT, NOT AN INCONVENIENCE
--------------------------------------------------
The obvious construction keeps only rows with four quarters of forward prices. That
**selects on survival and deletes exactly the events the question is about**: a name that
halves in quarter 1 and delists in quarter 2 has no price at quarter 4, so requiring the full
window would drop an early event and tilt the measured curve toward FLAT -- against the
hypothesis, silently. So every row is entered at k=1 and censored when its price series ends,
and `tests/test_e5_hazard_curve.py` pins that a row which crashes at k=1 and then has no
further prices is an **EVENT at k=1** rather than a dropped row.

The register (§0b) declared that before anything ran, which is what makes it a design choice
rather than a repair.

A CENSORED ROW IS NOT A CRASH-FREE ROW
---------------------------------------
`crash_gate.coverage`'s note, one level up. Delisting censoring is potentially INFORMATIVE and
runs against the hypothesis: a flagged name that dies without first printing a -50% quarter
leaves the risk set instead of being counted. `censoring_census` measures it by flag status so
the size and direction of that hole are visible, and the register's C4 bounds it by re-scoring
with distress delisting counted as an event.
"""
from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

__all__ = [
    "HAZARD_RULE",
    "apply_terminal_value",
    "censoring_census",
    "decay_statistic",
    "event_and_observable",
    "excess_share",
    "flag_persistence",
    "forward_quarters",
    "hazard_cells",
    "permutation_draws",
    "pooled_hazard",
]

HAZARD_RULE = (
    "A hazard is conditional on still being at risk. Report every quarter's rate with its EVENT "
    "COUNT and its AT-RISK count, quote the ratio rather than the difference (crash_gate's rule, "
    "which is a measurement about this panel's era-dependent base rate), and never read a "
    "censored row as a crash-free one -- it left the risk set, it did not survive it."
)


# --------------------------------------------------------------------------- construction

def forward_quarters(price_dir: str, tickers: Sequence[str], dates: Sequence,
                     *, quarter_td: int, k_max: int) -> pd.DataFrame:
    """Per `(date, ticker)`: the cumulative return at each of `k_max` forward quarter ends.

    POINT-IN-TIME BY CONSTRUCTION. `c0` is the last close dated **on or before** `d`; the k-th
    quarter end is the `quarter_td * k`-th price row **strictly after** `d`. `V6-B`'s
    `forward_paths` established the `searchsorted` shape and this reuses it; what differs is
    that a short window is CENSORED rather than dropped (see the module docstring), so the
    frame carries `NaN` at the quarters it cannot see instead of losing the row.

    Also returned: `dt_k`, the calendar date of each observed quarter end, which the censoring
    census and the distress sensitivity both need, and `last_price_date`, which is how an
    administrative censor is told apart from a delisting one.
    """
    if quarter_td is None or k_max is None:
        raise ValueError("hazard_curve.forward_quarters: quarter_td and k_max are required")
    quarter_td, k_max = int(quarter_td), int(k_max)
    if quarter_td < 1 or k_max < 1:
        raise ValueError("hazard_curve.forward_quarters: quarter_td and k_max must be >= 1")

    dts = np.array([np.datetime64(str(d)[:10]) for d in dates], dtype="datetime64[D]")
    rows: List[tuple] = []
    for tk in tickers:
        p = os.path.join(price_dir, f"{str(tk).upper()}.csv")
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_csv(p, usecols=["date", "close"]).dropna()
        except Exception:
            continue
        if len(df) < 2:
            continue
        df = df.sort_values("date")
        a = df["date"].to_numpy(dtype="datetime64[D]")
        c = df["close"].to_numpy(dtype=float)
        last = a[-1]
        hi = np.searchsorted(a, dts, side="right")        # count of rows dated <= d
        for d, j in zip(dts, hi):
            if j < 1:
                continue
            c0 = float(c[j - 1])
            if not np.isfinite(c0) or c0 <= 0:
                continue
            n_fwd = int(len(c) - j)
            rec = [str(d), str(tk), c0, str(last), n_fwd, float(c[-1]) / c0 - 1.0]
            for k in range(1, k_max + 1):
                idx = j + quarter_td * k - 1              # the k-th quarter end, 0-based
                if idx < len(c) and np.isfinite(c[idx]) and c[idx] > 0:
                    rec.append(float(c[idx]) / c0 - 1.0)
                    rec.append(str(a[idx]))
                else:
                    rec.append(np.nan)
                    rec.append(None)
            rows.append(tuple(rec))
    cols = ["date", "ticker", "c0", "last_price_date", "n_forward_rows", "terminal_ret"]
    for k in range(1, k_max + 1):
        cols += [f"r_{k}", f"dt_{k}"]
    return pd.DataFrame(rows, columns=cols)


def apply_terminal_value(fw: pd.DataFrame, *, quarter_td: int, k_max: int,
                         global_last_price_date: str) -> pd.DataFrame:
    """A DELISTED name has a terminal value; a name whose data merely runs out does not.

    **THIS IS THE REPAIR K3 FOUND, AND THE DISTINCTION IS THE WHOLE POINT.** `S22` and `V6-B`
    both forbid scoring a censored window on a last-price fallback, and they are right about
    the case they were built for: right-censoring at the END OF THE DATA, where a 30-day return
    labelled as a 63-day one is a defect that lands systematically on the most recent dates.

    A ticker that STOPS TRADING is a different object. Its last close is not a short window --
    it is the terminal value of a security that ceased to exist, and there is no return after
    it. Treating it as missing deletes the name from the risk set, and names that stop trading
    are not a random subset, so deleting them is survivorship selection of exactly the kind the
    register's §0b was written to avoid.

    **MEASURED RATHER THAN ARGUED: the panel's own shipped `fwd_ret` does precisely this.** On
    the 591 panel rows where a 63-trading-day forward price does not exist, `fwd_ret` equals
    `last_close / c0 - 1` on **591 of 591 at max |delta| 0.000e+00** -- so this rule is not a
    choice made here, it is the panel's rule, recovered. On the 113,354 rows where both exist
    the two agree at max |delta| 0.000e+00 as well, which is what makes the whole series one
    instrument rather than two.

    The terminal value is placed at the FIRST quarter the series fails to reach, and every
    later quarter stays unobservable: the name is gone, so it is neither at risk nor censored
    later -- it left. Administrative ends (`last_price_date >= global_last_price_date`) are
    NOT filled and still censor, which is `S22`'s rule kept intact where it applies.
    """
    if quarter_td is None or k_max is None or global_last_price_date is None:
        raise ValueError("hazard_curve.apply_terminal_value: quarter_td, k_max and "
                         "global_last_price_date are all required")
    out = fw.copy()
    n_fwd = out["n_forward_rows"].to_numpy(dtype=int)
    delisted = out["last_price_date"].astype(str).to_numpy() < str(global_last_price_date)
    kstar = n_fwd // int(quarter_td) + 1                 # first quarter the series cannot reach
    term = out["terminal_ret"].to_numpy(dtype=float)
    filled = np.zeros(len(out), dtype=bool)
    for k in range(1, int(k_max) + 1):
        r = pd.to_numeric(out[f"r_{k}"], errors="coerce").to_numpy(dtype=float)
        take = delisted & (kstar == k) & ~np.isfinite(r)
        if take.any():
            r = np.where(take, term, r)
            out[f"r_{k}"] = r
            dt = out[f"dt_{k}"].to_numpy(dtype=object)
            out[f"dt_{k}"] = np.where(take, out["last_price_date"].to_numpy(dtype=object), dt)
            filled |= take
    out["terminal_filled"] = filled
    return out


def event_and_observable(fw: pd.DataFrame, *, crash: float, k_max: int) -> pd.DataFrame:
    """Add `ev` (the quarter of the FIRST event, 0 for none) and `obs` (the last observable
    quarter, 0 for none).

    `ev` is a first-passage index measured at quarter boundaries: the smallest k with
    `r_k <= crash`. `obs` is the largest k with an observable `r_k`, and observability is a
    PREFIX -- a gap in the middle of a price series would break that assumption, so it is
    computed as a running conjunction rather than as a max, and a test pins the difference.
    """
    if crash is None or k_max is None:
        raise ValueError("hazard_curve.event_and_observable: crash and k_max are required")
    n = len(fw)
    ev = np.zeros(n, dtype=int)
    obs = np.zeros(n, dtype=int)
    still_observable = np.ones(n, dtype=bool)
    for k in range(1, int(k_max) + 1):
        r = pd.to_numeric(fw[f"r_{k}"], errors="coerce").to_numpy(dtype=float)
        seen = np.isfinite(r) & still_observable
        obs = np.where(seen, k, obs)
        still_observable = still_observable & np.isfinite(r)
        hit = seen & (r <= float(crash)) & (ev == 0)
        ev = np.where(hit, k, ev)
    out = fw.copy()
    out["ev"] = ev
    out["obs"] = obs
    return out


def _at_risk_and_event(ev: np.ndarray, obs: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
    """AT RISK at k: no event before k, and observable at k. EVENT at k: `ev == k`.

    An event at k implies observability at k by construction (you cannot see a crash in a
    quarter whose price you do not have), which is asserted rather than assumed.
    """
    no_prior = (ev == 0) | (ev >= k)
    at_risk = no_prior & (obs >= k)
    event = ev == k
    if not bool(np.all(~event | at_risk)):
        raise AssertionError("hazard_curve: an event at k that is not at risk at k")
    return at_risk, event


def hazard_cells(df: pd.DataFrame, *, flag_col: str, date_col: str, k_max: int,
                 min_flagged_per_date: int, min_kept_per_date: int) -> pd.DataFrame:
    """One row per `(date, quarter)`: at-risk and event counts for each group, and whether the
    cell QUALIFIES under the caller's per-date floors.

    The floors are `MA28`'s own 30/100, reused verbatim by the register rather than re-picked,
    and they are required here for `I-3`'s stated reason: a library that supplied them would
    hand the next consumer a pre-registration it never wrote.

    Non-qualifying cells are RETAINED with `qualifies=False` rather than dropped, so a reader
    can see what was excluded instead of inheriting a filtered frame.
    """
    if min_flagged_per_date is None or min_kept_per_date is None:
        raise ValueError("hazard_curve.hazard_cells: both per-date floors are required")
    f_all = df[flag_col].to_numpy(dtype=bool)
    ev_all = df["ev"].to_numpy(dtype=int)
    obs_all = df["obs"].to_numpy(dtype=int)
    dates = df[date_col].to_numpy()
    rows: List[Dict[str, object]] = []
    for d in pd.unique(dates):
        m = dates == d
        f, ev, obs = f_all[m], ev_all[m], obs_all[m]
        for k in range(1, int(k_max) + 1):
            at_risk, event = _at_risk_and_event(ev, obs, k)
            nf = int((at_risk & f).sum())
            nk = int((at_risk & ~f).sum())
            rows.append({
                "date": str(d)[:10], "k": k,
                "at_risk_flagged": nf, "at_risk_kept": nk,
                "event_flagged": int((event & f).sum()),
                "event_kept": int((event & ~f).sum()),
                "qualifies": bool(nf >= int(min_flagged_per_date)
                                  and nk >= int(min_kept_per_date)),
            })
    out = pd.DataFrame(rows)
    if len(out):
        out["h_flagged"] = np.where(out["at_risk_flagged"] > 0,
                                    out["event_flagged"] / out["at_risk_flagged"].replace(0, np.nan),
                                    np.nan)
        out["h_kept"] = np.where(out["at_risk_kept"] > 0,
                                 out["event_kept"] / out["at_risk_kept"].replace(0, np.nan),
                                 np.nan)
        out["d"] = out["h_flagged"] - out["h_kept"]
    return out


# --------------------------------------------------------------------------- statistics

def pooled_hazard(cells: pd.DataFrame, ks: Sequence[int], *,
                  qualifying_only: bool = True) -> Dict[str, object]:
    """Pooled hazard over the quarters in `ks`: events summed over at-risk summed.

    Every rate ships with BOTH counts. The ratio is the figure that travels between eras
    (`crash_gate`'s measured rule); the difference is computed because the legs are defined on
    it and is never the quoted headline.
    """
    c = cells[cells["qualifies"]] if qualifying_only else cells
    c = c[c["k"].isin(list(ks))]
    ef, af = int(c["event_flagged"].sum()), int(c["at_risk_flagged"].sum())
    ek, ak = int(c["event_kept"].sum()), int(c["at_risk_kept"].sum())
    hf = (ef / af) if af else None
    hk = (ek / ak) if ak else None
    return {"quarters": [int(x) for x in ks],
            "at_risk_flagged": af, "at_risk_kept": ak,
            "event_flagged": ef, "event_kept": ek,
            "rate_flagged": hf, "rate_kept": hk,
            "ratio": (hf / hk) if (hf is not None and hk) else None,
            "n_cells": int(len(c))}


def decay_statistic(cells: pd.DataFrame, *, front: Sequence[int], back: Sequence[int],
                    qualifying_only: bool = True) -> Optional[float]:
    """`HR(front) - HR(back)`. Positive means the hazard ratio DECAYS.

    Returns `None` when either window has no kept events, rather than a large or infinite
    number: a ratio with an empty denominator is not a value and must not enter a null.
    """
    a = pooled_hazard(cells, front, qualifying_only=qualifying_only)
    b = pooled_hazard(cells, back, qualifying_only=qualifying_only)
    if a["ratio"] is None or b["ratio"] is None:
        return None
    return float(a["ratio"] - b["ratio"])


def excess_share(cells: pd.DataFrame, *, front: Sequence[int], k_max: int,
                 qualifying_only: bool = True) -> Dict[str, object]:
    """The proposal's own statistic: what share of the four-quarter EXCESS crash count falls in
    the front quarters?

    Excess at k = `at_risk_flagged(k) * (h_flagged(k) - h_kept(k))`, i.e. the flagged events
    beyond what the kept hazard at the same k would have produced on the same risk set. This is
    a ratio of differences and so inherits the era-dependence `crash_gate` warns about; the
    register keeps it as a leg because it is the proposal's stated bar, states that limitation,
    and requires the ratio leg beside it.

    A NEGATIVE total is reported and never silently made positive -- a share of a negative
    excess is meaningless, so `share` is `None` with a stated reason in that case.
    """
    c = cells[cells["qualifies"]] if qualifying_only else cells
    per_k = {}
    for k in range(1, int(k_max) + 1):
        g = c[c["k"] == k]
        ef, af = int(g["event_flagged"].sum()), int(g["at_risk_flagged"].sum())
        ek, ak = int(g["event_kept"].sum()), int(g["at_risk_kept"].sum())
        hk = (ek / ak) if ak else None
        per_k[k] = (ef - af * hk) if (hk is not None) else None
    vals = [per_k[k] for k in range(1, int(k_max) + 1)]
    if any(v is None for v in vals):
        return {"per_quarter_excess": per_k, "share": None,
                "reason": "a quarter has no kept at-risk rows, so its excess is undefined"}
    total = float(sum(vals))
    fr = float(sum(per_k[k] for k in front))
    if total <= 0:
        return {"per_quarter_excess": per_k, "total_excess": total, "front_excess": fr,
                "share": None,
                "reason": ("the four-quarter excess is not positive, so a share of it is not "
                           "interpretable; the flag did not produce excess crashes overall")}
    return {"per_quarter_excess": per_k, "total_excess": total, "front_excess": fr,
            "front_quarters": [int(x) for x in front], "share": fr / total}


# --------------------------------------------------------------------------- the null

def permutation_draws(df: pd.DataFrame, *, flag_col: str, date_col: str, k_max: int,
                      n_draws: int, seed: int,
                      min_flagged_per_date: int, min_kept_per_date: int,
                      statfn: Callable[[pd.DataFrame], Optional[float]]) -> Dict[str, object]:
    """Shuffle the FLAG within each date; recompute `statfn` on every draw.

    **THE SHUFFLE IS `I-3`'s SHUFFLE.** Same scheme, same rng call sequence: one
    `rng.permutation(len(group))` per qualifying date per draw, dates in sorted order, the
    date's flagged COUNT held exactly. That is not asserted -- `tests/test_e5_hazard_curve.py`
    drives this function on a degenerate single-quarter case and requires it to reproduce
    `crash_gate.permutation_null`'s p95, median and max **exactly** at the same seed and draw
    count. `B7` protection obtained by measurement rather than by two loops that look alike.

    A date qualifies on its k=1 counts, using the REAL flag, exactly as `I-3` does: the
    qualification is a property of the DATA, so it must not move with the shuffle.

    Draws whose statistic is undefined are counted and excluded rather than coerced to zero.
    Coercing would pad the null with fake draws and LOWER its percentile -- i.e. make the bar
    EASIER, which is the direction `V6` caught once already.
    """
    if n_draws is None or seed is None:
        raise ValueError("hazard_curve.permutation_draws: n_draws and seed are required")
    if min_flagged_per_date is None or min_kept_per_date is None:
        raise ValueError("hazard_curve.permutation_draws: both per-date floors are required")

    rng = np.random.default_rng(int(seed))
    groups: List[Tuple[object, int, np.ndarray, np.ndarray]] = []
    # THE QUALIFICATION IS A PROPERTY OF THE DATA AND MUST NOT MOVE WITH THE SHUFFLE (`I-3`'s
    # principle). It is computed ONCE here from the REAL flag, per (date, quarter), and the
    # same mask is applied to every draw -- so the null scores the SAME functional the observed
    # statistic is, which is the only way its percentile can be that statistic's bar. Marking
    # every shuffled cell as qualifying instead would pool the null over cells the observed
    # statistic excludes: two different statistics, one of them calibrating the other.
    qualify: Dict[Tuple[str, int], bool] = {}
    for d, g in df.groupby(date_col, sort=True):
        f = g[flag_col].to_numpy(dtype=bool)
        ev = g["ev"].to_numpy(dtype=int)
        obs = g["obs"].to_numpy(dtype=int)
        at_risk1, _ = _at_risk_and_event(ev, obs, 1)
        if int((at_risk1 & f).sum()) < int(min_flagged_per_date):
            continue
        if int((at_risk1 & ~f).sum()) < int(min_kept_per_date):
            continue
        for k in range(1, int(k_max) + 1):
            ar, _ = _at_risk_and_event(ev, obs, k)
            qualify[(str(d)[:10], k)] = bool(
                int((ar & f).sum()) >= int(min_flagged_per_date)
                and int((ar & ~f).sum()) >= int(min_kept_per_date))
        groups.append((d, int(f.sum()), ev, obs))
    if not groups:
        return {"draws": [], "n_draws": 0, "n_undefined": 0,
                "reason": "no qualifying dates"}

    vals: List[float] = []
    undefined = 0
    for _ in range(int(n_draws)):
        rows: List[Dict[str, object]] = []
        for d, nf, ev, obs in groups:
            idx = rng.permutation(len(ev))
            fs = np.zeros(len(ev), dtype=bool)
            fs[idx[:nf]] = True
            for k in range(1, int(k_max) + 1):
                at_risk, event = _at_risk_and_event(ev, obs, k)
                a_f = int((at_risk & fs).sum())
                a_k = int((at_risk & ~fs).sum())
                rows.append({"date": str(d)[:10], "k": k,
                             "at_risk_flagged": a_f, "at_risk_kept": a_k,
                             "event_flagged": int((event & fs).sum()),
                             "event_kept": int((event & ~fs).sum()),
                             "qualifies": qualify.get((str(d)[:10], k), False)})
        cells = pd.DataFrame(rows)
        cells["h_flagged"] = np.where(cells["at_risk_flagged"] > 0,
                                      cells["event_flagged"] / cells["at_risk_flagged"].replace(0, np.nan),
                                      np.nan)
        cells["h_kept"] = np.where(cells["at_risk_kept"] > 0,
                                   cells["event_kept"] / cells["at_risk_kept"].replace(0, np.nan),
                                   np.nan)
        cells["d"] = cells["h_flagged"] - cells["h_kept"]
        v = statfn(cells)
        if v is None or not np.isfinite(v):
            undefined += 1
            continue
        vals.append(float(v))
    arr = np.asarray(vals, dtype=float)
    if not arr.size:
        return {"draws": [], "n_draws": 0, "n_undefined": undefined,
                "reason": "every draw was undefined"}
    return {"draws": arr.tolist(), "n_draws": int(arr.size), "n_undefined": int(undefined),
            "p95": float(np.quantile(arr, 0.95)), "p50": float(np.median(arr)),
            "max": float(arr.max()), "min": float(arr.min()),
            "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
            "n_distinct": int(np.unique(arr).size)}


# --------------------------------------------------------------------------- census

def censoring_census(df: pd.DataFrame, *, flag_col: str, k_max: int,
                     global_last_price_date: str) -> Dict[str, object]:
    """Who left the risk set without an event, and why.

    ADMINISTRATIVE: the ticker's price file runs to the global last date, so the window simply
    extends past the end of the data. DELISTING: the ticker's own series stops earlier, which
    on this universe is overwhelmingly a corporate action.

    The split matters because the two censor for different reasons and only one of them can be
    informative. Reported BY FLAG STATUS with the ratio, because a differential rate is the
    thing that would bias the curve: `V6-B` measured that 82.63% of delistings here are
    ACQUISITIONS, so this census is a description and never an attribution.
    """
    ev = df["ev"].to_numpy(dtype=int)
    obs = df["obs"].to_numpy(dtype=int)
    f = df[flag_col].to_numpy(dtype=bool)
    last = df["last_price_date"].astype(str).to_numpy()
    censored = (ev == 0) & (obs < int(k_max))
    admin = censored & (last >= str(global_last_price_date))
    delist = censored & ~admin
    out: Dict[str, object] = {"global_last_price_date": str(global_last_price_date),
                              "k_max": int(k_max)}
    for name, m in (("flagged", f), ("kept", ~f)):
        n = int(m.sum())
        out[name] = {
            "rows": n,
            "censored_before_k_max": int((censored & m).sum()),
            "censored_administrative": int((admin & m).sum()),
            "censored_delisting": int((delist & m).sum()),
            "delisting_censor_rate": (float((delist & m).sum()) / n) if n else None,
        }
    a = out["flagged"]["delisting_censor_rate"]
    b = out["kept"]["delisting_censor_rate"]
    out["delisting_censor_rate_ratio"] = (a / b) if (a is not None and b) else None
    out["note"] = ("a censored row is NOT a crash-free row; if flagged rows are censored by "
                   "delisting more often, the measured flagged hazard is UNDERSTATED and the "
                   "direction of that bias must travel with the verdict")
    return out


def flag_persistence(panel: pd.DataFrame, *, flag_col: str, date_col: str, k_max: int
                     ) -> Dict[str, object]:
    """Of the names flagged at date `d`, what share are still flagged `k` panel dates later?

    Diagnostic, no verdict, and required for interpretation: it separates *"the flag's
    information decays"* from *"the flag goes away"*. Those mean different things to a consumer
    choosing an option tenor, and a hazard curve alone cannot tell them apart.
    """
    ds = sorted(pd.unique(panel[date_col]))
    by = {str(d)[:10]: set(panel.loc[(panel[date_col] == d) & panel[flag_col], "ticker"])
          for d in ds}
    keys = [str(d)[:10] for d in ds]
    out: Dict[str, object] = {}
    for k in range(1, int(k_max) + 1):
        num = den = 0
        for i in range(len(keys) - k):
            a, b = by[keys[i]], by[keys[i + k]]
            if not a:
                continue
            den += len(a)
            num += len(a & b)
        out[f"still_flagged_after_{k}_quarters"] = (num / den) if den else None
        out[f"pairs_scored_k{k}"] = den
    out["note"] = ("panel-date offsets, not calendar quarters; a name absent from the later "
                   "cross-section counts as NOT flagged, which is conservative for this reading")
    return out
