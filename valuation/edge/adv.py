"""Point-in-time dollar ADV for the panel, from CRSP daily stock data.

WHY THIS EXISTS
---------------
`B13`'s `MIN_AVG_DOLLAR_VOLUME` has never bound on the panel path and `S7`'s fourth interaction
(`size x liquidity`) was recorded as *"not buildable"* — both for one reason: the price export on
disk carries date and close only, and the one volume source in the project
(`data/bulk/prepared/bars`) reaches **502 of 2,531 names = 19.8%**. CRSP `dsf` reaches **2,271 =
89.7%**, which is what dissolves the block.

**THIS MODULE IS AN INSTRUMENT AND NOTHING ELSE. It ranks nothing, filters nothing, and scores
nothing.** No arm may run in the same pass that builds it (`MB15`'s ordering).

THE DEFINITION IS MATCHED TO THE LIVE SCREEN, NOT CHOSEN
--------------------------------------------------------
`valuation/screener/prices.py:243` computes the live `avg_dollar_volume` as the mean of
`close * volume` over the trailing **~60 sessions**, on the **as-traded** close. That is the
quantity `MIN_AVG_DOLLAR_VOLUME = 500_000` is calibrated against, so this module reproduces it
rather than inventing a window. **Picking a different window here would silently re-scale the
threshold and make a panel filter that shares a constant with the live screen mean something
else** — `MA5`'s frozen-constant family, one level up.

THE CRSP TRAPS, BOTH MEASURED RATHER THAN ASSUMED
--------------------------------------------------
**1. `prc` IS NEGATIVE WHEN CRSP SUBSTITUTES A BID/ASK MIDPOINT.** CRSP's own convention: a
closing price that did not trade is stored as the NEGATIVE of the bid/ask average. A naive
`prc * vol` therefore produces a NEGATIVE dollar volume for exactly the least liquid rows — the
rows a liquidity filter exists to catch — and a negative ADV compares below any floor, so the
filter would appear to work while working for the wrong reason. `abs()` is applied and the
affected share is reported, never silently absorbed.

**2. THE TICKER -> PERMNO JOIN MUST BE DATE-SCOPED.** 1,053 of our 2,271 matched tickers map to
MORE THAN ONE permno. `crsp.stocknames` is a dated name history and a ticker is a lease, not an
identity — this is `S3-I5`'s reuse problem in a third table, after the option chains and the IBES
actuals. An undated dictionary silently attributes one company's volume to another, and the
direction is not random: reused tickers concentrate in small and delisted names, which is again
exactly the population a liquidity screen is about.

WHAT CRSP CANNOT COVER, STATED BEFORE ANYTHING IS SCORED
---------------------------------------------------------
CRSP on this account is **cut at 2024-12-31**. Five of the panel's 69 rebalance dates fall after
it — 2025-01-27, 2025-04-28, 2025-07-29, 2025-10-27, 2026-01-28 — which is **9,367 of 113,945
panel rows = 8.2%**. A CRSP-based ADV covers **64 of 69 dates** and is useless for anything after
the cut. Both statements are true at once and neither substitutes for the other.
"""
from __future__ import annotations

import collections
import datetime as dt
import os
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: The live screen's own window (`prices.py:243`). Matched, never chosen -- see the module
#: docstring. Changing it re-scales what `MIN_AVG_DOLLAR_VOLUME` means.
ADV_WINDOW_SESSIONS = 60

#: A window is only usable if enough of it exists. A name with four sessions has an "average"
#: that is not one, and admitting it would let a barely-traded name clear a floor on noise.
MIN_SESSIONS = 20

#: CRSP's last date on this account, measured in the entitlement census rather than assumed.
CRSP_CUT = dt.date(2024, 12, 31)

#: Open-ended interval end, so a name still trading is not truncated at CRSP's cut when the
#: NAME history ends there for vendor reasons rather than company ones.
OPEN_END = "9999-12-31"

DEFAULT_RAW_ROOT = r"D:\wrds"


class CoverageError(LookupError):
    """Raised when an ADV is asked for where none can be computed.

    Deliberately an exception rather than 0.0 or None. **A zero ADV is BELOW every floor**, so a
    missing measure returned as zero silently converts "we cannot see this name" into "this name
    is illiquid, drop it" -- which is a survivorship filter wearing a liquidity filter's name.
    """


def dollar_volume(prc, vol):
    """One row's dollar volume, honouring CRSP's negative-price convention.

    `abs(prc)`, because CRSP stores a bid/ask midpoint as a NEGATIVE price when the close did not
    trade. See the module docstring: the naive form goes negative on precisely the illiquid rows
    a liquidity screen is about.
    """
    import numpy as np
    p = np.abs(np.asarray(prc, dtype="float64"))
    v = np.asarray(vol, dtype="float64")
    return p * v


def merge_intervals(rows: Sequence[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    """Collapse adjacent CRSP name rows that carry the same key into one interval.

    CRSP splits a row on ANY name or exchange edit, so an unmerged history has many intervals per
    identity and the last one may be days long. Merging makes the interval mean "this key was
    this ticker's identity over this span", which is the property the join needs.
    """
    out: List[Tuple[str, str, str]] = []
    for k, a, b in sorted(rows, key=lambda r: r[1]):
        if out and out[-1][0] == k:
            out[-1] = (k, out[-1][1], max(out[-1][2], b))
        else:
            out.append((k, a, b))
    if out:
        out[-1] = (out[-1][0], out[-1][1], OPEN_END)
    return out


def ticker_permno_intervals(stocknames) -> Dict[str, List[Tuple[int, str, str]]]:
    """{ticker: [(permno, from, to), ...]} from CRSP's DATED name history.

    THE DATE IS THE POINT. 1,053 of our 2,271 matched tickers map to more than one permno; a
    `{ticker: permno}` dictionary attributes one company's volume to another and does it silently.
    """
    iv: Dict[str, List[Tuple[int, str, str]]] = {}
    by = collections.defaultdict(list)
    for r in stocknames.itertuples():
        t = str(r.ticker).upper().strip()
        if not t or t == "NAN":
            continue
        by[t].append((str(int(r.permno)), str(r.namedt)[:10], str(r.nameenddt)[:10]))
    for t, rows in by.items():
        iv[t] = [(int(k), a, b) for k, a, b in merge_intervals(rows)]
    return iv


def permno_on(intervals: Dict[str, List[Tuple[int, str, str]]], ticker: str,
              date) -> Optional[int]:
    """The permno this ticker denoted ON `date`, or None. Never 'the current one'."""
    d = str(date)[:10]
    for p, lo, hi in intervals.get(str(ticker).upper(), ()):
        if lo <= d <= hi:
            return p
    return None


def adv_series(daily, window: int = ADV_WINDOW_SESSIONS,
               min_sessions: int = MIN_SESSIONS):
    """Trailing-mean dollar volume per (permno, date), STRICTLY point-in-time.

    `daily` needs columns `permno`, `date`, `prc`, `vol`.

    THE WINDOW ENDS ON THE PRIOR SESSION, NOT ON `date` ITSELF. A filter applied when selecting
    on date D may not use D's own volume: the panel's other point-in-time rules are
    strictly-before and a liquidity screen that peeks at the selection day's tape is a look-ahead
    on the one axis most correlated with the day's news.
    """
    import pandas as pd
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["dv"] = dollar_volume(d["prc"], d["vol"])
    d = d.dropna(subset=["dv"]).sort_values(["permno", "date"])
    g = d.groupby("permno")["dv"]
    d["adv"] = g.transform(lambda s: s.shift(1).rolling(window, min_periods=min_sessions).mean())
    return d[["permno", "date", "adv"]].dropna(subset=["adv"])


def negative_price_share(daily) -> dict:
    """How much of the frame carries CRSP's negative (bid/ask midpoint) price.

    Reported rather than absorbed: it is a statement about how much of the panel's volume is
    inferred from quotes rather than trades, and it concentrates in the illiquid tail.
    """
    import numpy as np
    p = np.asarray(daily["prc"], dtype="float64")
    n = int(np.isfinite(p).sum())
    neg = int((p < 0).sum())
    return {"rows": n, "negative_price_rows": neg,
            "pct": round(100.0 * neg / max(1, n), 3)}


def coverage(adv_by_cell: Dict[Tuple[str, str], float],
             cells: Iterable[Tuple[str, str]]) -> dict:
    """Coverage ON THE POPULATION THE ARM WILL TEST, which is the only population that counts.

    This project spent a week learning that a coverage figure quoted for a DIFFERENT population
    than the one scored is worth nothing -- `MB8` measured a flag on the panel and the book had
    almost none of it, and `V6-OPT` re-measured `V6-B`'s separation on the covered subset and
    found it a quarter of the headline.
    """
    cs = list(cells)
    have = sum(1 for c in cs if c in adv_by_cell)
    return {"cells": len(cs), "with_adv": have,
            "pct": round(100.0 * have / max(1, len(cs)), 2),
            "without_adv": len(cs) - have}
