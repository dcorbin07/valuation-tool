# -*- coding: utf-8 -*-
"""D6/D7 — the analyst estimate-revision signal, built exactly as `PREREG_d6_analyst_revisions.md`
declares it and with no parameter the register does not name.

WHY THIS FILE EXISTS SEPARATELY FROM ITS RUNNER
-----------------------------------------------
The controls pass and the arm pass must build the SAME signal. `MB8`'s C2 exists because a study
rebuilt decile membership by hand and had to prove it reproduced the shipped one; the cheaper fix
is to have exactly one construction and call it twice. Every constant below is FROM THE REGISTER,
and changing one after a measurement voids the item (`MA28`'s rule, quoted in its own source).

THE THREE CHOICES THE REGISTER HAD TO MAKE, restated here because a reader of the code should not
have to fetch the register to know why these are not free parameters:

* **`det_epsus` + `act_epsus`, the SPLIT-ADJUSTED pair.** The `D6` ledger row warns in its own
  words that *"an adjusted estimate against an unadjusted actual is a units error that reads as a
  surprise"* -- and the pull that row licensed then paired ADJUSTED estimates with UNADJUSTED
  actuals, because IBES ships each file twice and the names differ by one letter. Both pairs are
  on disk, so the right choice is possible and not automatic. **The arm as registered never reads
  an actual at all**; `act_epsus` is named only so a surprise-based successor inherits the pair.
* **`fpi = '1'` (FY1).** A naive SELECT pools FY1, FY2 and the quarterly codes and measures a
  different object on every row.
* **`actdats` is the point-in-time gate.** `anndats` (when the analyst issued it) is looser -- an
  estimate can be announced before it is retrievable, and a signal built on it is usable only by
  someone who was not reading IBES. `revdats` is IBES's REVIEW date, recording when an estimate
  was last confirmed STILL CURRENT rather than when it changed; using it as a revision date is a
  known error and this module never reads it.

The cusip->ticker join is `W-3b`'s, IMPORTED and never re-implemented (`B7`). Its three measured
traps are inherited rather than re-discovered: `oftic` is a lease (17.7% of the rows it offers are
a different company), escaping ticker reuse needs a DATE rather than a different column, and
IBES's `X` cusip mask needs a POSITIONAL wildcard because a 7-character prefix rule merges 328
distinct cusips in this file.
"""
from __future__ import annotations

import collections
import datetime as _dt
import glob
import os
from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd

from valuation.edge.ibes_events import MaskedCusip

__all__ = ["FPI_FY1", "WINDOW_DAYS", "MIN_REVISIONS", "SIGNAL_COL", "OPEN_END",
           "RegisterViolation", "crsp_intervals", "load_fy1_estimates", "map_to_universe",
           "revisions", "signal_on_panel"]


class RegisterViolation(RuntimeError):
    """Raised when a caller asks for something the register does not name."""


#: EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item.
FPI_FY1 = "1"                 # FY1, the next unreported annual period
MEASURE = "EPS"
USFIRM = "1"
WINDOW_DAYS = 91              # one quarterly rebalance interval, matched not tuned
MIN_REVISIONS = 3             # the declared floor
SIGNAL_COL = "z_rev_ratio"

#: CRSP on this account is CUT AT 2024-12-31 while our names still trade and IBES still reports.
#: Left unextended, every 2025-2026 estimate falls outside every interval and is silently
#: dropped -- the vendor's cut-off masquerading as a coverage gap. `W-3b` measured this.
OPEN_END = "9999-12-31"

DEFAULT_DET_DIR = r"D:\wrds\ibes_det_epsus"
DEFAULT_DSENAMES = r"D:\wrds\crsp_dsenames\crsp_dsenames_all.pkl"

#: Columns the arm path may NEVER read. `actual`/`*_act` are the realised outcome (a surprise is
#: a different object -- register section 2a); `anndats`/`revdats` are the rejected date gates.
FORBIDDEN_COLUMNS = ("anndats", "revdats", "actual", "actdats_act", "anndats_act", "anntims_act")


def _read(path: str) -> pd.DataFrame:
    """`scripts/wrds_pull.py` writes `to_pickle(..., compression='gzip')` under a bare `.pkl`."""
    return pd.read_pickle(path, compression="gzip")


def crsp_intervals(tickers: Iterable[str], dsenames: str = "") -> Dict[str, List[Tuple[str, str, str]]]:
    """`ticker -> [(cusip8, from, to), ...]` from CRSP's DATED name history.

    `W-3b` measured what each naive alternative costs and both errors are large: taking EVERY
    cusip a ticker ever carried re-imports ticker reuse through a second door, and taking only the
    CURRENT cusip truncated HWM on 82.9% of its dates, MRVL on 80.6%, STX on 79.8%, GE on 79.3%.
    The interval is the fix, because reuse and continuation are one fact seen from two sides.
    """
    path = dsenames or DEFAULT_DSENAMES
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{path} is absent. CRSP name history lives on D: and is never mirrored into the "
            f"checkout; run `python -m scripts.wrds_pull --product crsp_dsenames` first.")
    sn = _read(path)
    sn["ticker"] = sn["ticker"].astype(str).str.upper().str.strip()
    want = {str(t).upper().strip() for t in tickers}
    sn = sn[sn["ticker"].isin(want)].copy()
    sn["c8"] = sn["ncusip"].fillna(sn["cusip"]).astype(str).str[:8].str.upper()
    sn = sn[sn["c8"].str.len() == 8]
    out: Dict[str, List[Tuple[str, str, str]]] = {}
    for t, g in sn.groupby("ticker"):
        g = g.sort_values("namedt")
        rows = [(str(r.c8), str(r.namedt)[:10], str(r.nameendt)[:10]) for r in g.itertuples()]
        merged: List[List[str]] = []
        for c, a, b in rows:
            # merge adjacent rows carrying the same cusip so intervals are per IDENTITY rather
            # than per CRSP name-change row (CRSP splits on any name or exchange edit).
            if merged and merged[-1][0] == c:
                merged[-1][2] = max(merged[-1][2], b)
            else:
                merged.append([c, a, b])
        if merged:
            merged[-1][2] = OPEN_END
        out[t] = [tuple(m) for m in merged]
    return out


def load_fy1_estimates(det_dir: str = "", years: Sequence[int] = ()) -> pd.DataFrame:
    """FY1 EPS detail estimates for US firms, carrying ONLY the columns the register names."""
    d = det_dir or DEFAULT_DET_DIR
    if not os.path.isdir(d):
        raise FileNotFoundError(
            f"{d} is absent. IBES detail estimates live on D: and are never mirrored into the "
            f"checkout; run `python -m scripts.wrds_pull --product ibes_det_epsus` first.")
    keep = ["cusip", "analys", "estimator", "fpedats", "value", "actdats"]
    want = set(int(y) for y in years) if years else None
    frames = []
    for f in sorted(glob.glob(os.path.join(d, "*.pkl"))):
        y = int(os.path.basename(f).split("_")[-1].split(".")[0])
        if want is not None and y not in want:
            continue
        df = _read(f)
        df = df[(df["measure"].astype(str) == MEASURE)
                & (df["usfirm"].astype(str) == USFIRM)
                & (df["fpi"].astype(str) == FPI_FY1)]
        if len(df):
            frames.append(df[keep].copy())
    if not frames:
        raise RegisterViolation("no FY1 EPS rows found -- refusing to return an empty frame, "
                                "because zero rows and 'not covered' must not read the same "
                                "(DEEPITM-FIN's existence-is-not-population defect)")
    out = pd.concat(frames, ignore_index=True)
    out["cusip"] = out["cusip"].astype(str).str.upper().str.strip()
    out["actdats"] = out["actdats"].astype(str).str[:10]
    return out


def map_to_universe(det: pd.DataFrame, intervals: Dict[str, list]) -> pd.DataFrame:
    """Attach our ticker to each estimate, honouring BOTH the `X` mask and the dated interval.

    An estimate is ours if its `actdats` falls inside the window during which that cusip was this
    ticker's identity. That is the only rule safe against ticker reuse AND cusip continuation.
    """
    exact: Dict[str, List[Tuple[str, str, str]]] = collections.defaultdict(list)
    for t, ivs in intervals.items():
        for c8, lo, hi in ivs:
            exact[c8].append((t, lo, hi))
    all_c8 = list(exact.keys())
    cache: Dict[str, list] = {}

    def candidates(icu: str) -> list:
        if "X" not in icu:
            return exact.get(icu, [])
        if icu not in cache:
            cache[icu] = [x for c8 in all_c8 if MaskedCusip.matches(icu, c8) for x in exact[c8]]
        return cache[icu]

    rows = []
    for cu, an, ana, est, fpe, val in zip(det["cusip"], det["actdats"], det["analys"],
                                          det["estimator"], det["fpedats"], det["value"]):
        if not isinstance(cu, str) or len(cu) != 8:
            continue
        for t, lo, hi in candidates(cu):
            if lo <= an <= hi:
                rows.append((t, an, ana, est, str(fpe)[:10], val))
                break
    return pd.DataFrame(rows, columns=["ticker", "actdats", "analys", "estimator",
                                       "fpedats", "value"])


def revisions(est: pd.DataFrame) -> pd.DataFrame:
    """Consecutive estimates by the SAME analyst for the SAME fiscal period whose value CHANGED.

    An unchanged re-confirmation is not a revision. This construction is the whole reason the
    item needs `det_epsus`: a consensus change is available from `statsum` and requires no
    per-analyst timing at all.
    """
    e = est.dropna(subset=["value"]).sort_values(
        ["ticker", "analys", "estimator", "fpedats", "actdats"])
    prev = e.groupby(["ticker", "analys", "estimator", "fpedats"], sort=False)["value"].shift(1)
    rev = e[prev.notna() & (e["value"] != prev)].copy()
    rev["prev"] = prev[rev.index]
    rev["sign"] = (rev["value"] > rev["prev"]).map({True: 1, False: -1})
    return rev[["ticker", "actdats", "sign"]]


def _minus(iso: str, days: int) -> str:
    return (_dt.date(int(iso[:4]), int(iso[5:7]), int(iso[8:10]))
            - _dt.timedelta(days=days)).isoformat()


def signal_on_panel(panel: pd.DataFrame, rev: pd.DataFrame,
                    window_days: int = WINDOW_DAYS,
                    min_revisions: int = MIN_REVISIONS) -> pd.Series:
    """`(U - D) / (U + D)` over the trailing window, NaN below the floor.

    STRICTLY point-in-time: the window is `(t - window_days, t]`, so a revision activated AFTER
    the rebalance date can never enter. `K4` pins that from both sides.
    """
    if window_days != WINDOW_DAYS or min_revisions != MIN_REVISIONS:
        raise RegisterViolation(
            "the register fixes the window at %d days and the floor at %d revisions, and sweeping "
            "either is void condition 7 -- a second window is a NEW hypothesis with its own trial "
            "and its own blind register" % (WINDOW_DAYS, MIN_REVISIONS))
    by: Dict[str, List[Tuple[str, int]]] = collections.defaultdict(list)
    for t, d0, s in zip(rev["ticker"], rev["actdats"], rev["sign"]):
        by[t].append((str(d0)[:10], int(s)))
    for t in by:
        by[t].sort()
    out = []
    for t, d0 in zip(panel["ticker"].astype(str).str.upper(), panel["date"].astype(str)):
        lo = _minus(d0, window_days)
        u = dn = 0
        for rdt, s in by.get(t, ()):
            if lo < rdt <= d0:
                if s > 0:
                    u += 1
                else:
                    dn += 1
        n = u + dn
        out.append((u - dn) / n if n >= min_revisions else float("nan"))
    return pd.Series(out, index=panel.index, name=SIGNAL_COL)
