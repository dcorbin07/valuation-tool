"""Point-in-time dollar ADV and OHLC for the panel, from the FROZEN Sharadar SEP export.

`MC9` (AUDIT 6). **THIS MODULE IS AN INSTRUMENT AND NOTHING ELSE. It ranks nothing, filters
nothing and scores nothing**, and no arm may run in the pass that builds it (`MB15`'s ordering).

WHY IT EXISTS, AND THE RECORD CORRECTION IT CARRIES
---------------------------------------------------
Two claims in this record contradict each other and only one is true.

* `B13`'s ledger row says `MIN_AVG_DOLLAR_VOLUME` *"structurally cannot bind on this path"*
  because *"the price export on disk carries date and close ONLY"*, and names its re-open
  condition as **"SEP volume reaches the loader"** -- a statement that SEP volume EXISTS and is
  merely not plumbed.
* `HANDOFF_free_analysis.md:548-551` (`P1`, landed `7edf594` on **2026-08-04**) says
  *"**SEP is not on disk in any form**; the bulk extracts are ACTIONS, DAILY, EVENTS and SF3,
  none carrying volume"*, and on that basis filled **45.3% of positions** with a market-cap
  proxy.

**`B13` IS TRUE AND `P1` IS FALSE, AND `P1` WAS ALREADY FALSE WHEN IT WAS WRITTEN.**
`data/backtest_freeze_2026-08/bulk/sep.csv` is **3,223,156,161 bytes**, read-only, with header
`ticker,date,open,high,low,close,volume,closeadj,closeunadj,lastupdated` -- and its mtime is
**2026-08-02 17:14**, with the freeze root at 18:25, **two days before `P1` landed**.

**THE MECHANISM IS EXACT AND IT IS THE PORTABLE PART.** `data/bulk/` contains precisely
`actions.csv`, `daily.csv`, `events.csv` and `sf3.csv` -- the four `P1` enumerated, and nothing
else. The freeze at `data/backtest_freeze_2026-08/bulk/` contains those **plus** `sep.csv`,
`sf1.csv`, `sf2.csv` and `sf3a.csv`. **`P1` enumerated ONE directory correctly and generalised
to "in any form".** `DEEPITM-FIN`'s existence-is-not-population defect with the quantifier
inverted: there, a directory existed and was empty; here, a file existed and the search did not
reach it.

THE DEFINITION IS MATCHED TO THE LIVE SCREEN, NOT CHOSEN
--------------------------------------------------------
`valuation/screener/prices.py:243` computes the live `avg_dollar_volume` as the mean of
`close * volume` over the trailing ~60 sessions. `MIN_AVG_DOLLAR_VOLUME = 500_000` is calibrated
against that quantity, so this module reproduces it rather than inventing a window -- and it
reuses **`adv.ADV_WINDOW_SESSIONS`** rather than declaring a second 60, because two copies of a
calibrated constant is `MA5`'s frozen-hurdle family.

**THE WINDOW ENDS ON THE PRIOR SESSION.** A screen applied when selecting on date D may not read
D's own tape; the panel's other point-in-time rules are strictly-before, and volume is the axis
most correlated with the day's news. That is `adv.adv_series`'s rule and this module **CALLS it**
rather than re-implementing the roll (`B7`: one definition).

THE SPLIT TRAP, MEASURED RATHER THAN ASSUMED
---------------------------------------------
SEP ships three closes. **`close` is SPLIT-ADJUSTED, `closeunadj` is as-traded, and `volume` is
SPLIT-ADJUSTED TO MATCH `close`.** Measured on CMG the session before its 50:1 split
(2024-06-20): `close` 64.288 against `closeunadj` 3214.42 -- a ratio of exactly 50.0 -- with
`volume` 42,188,400. `close * volume` is **$2.71bn**, which is plausible for CMG; `closeunadj *
volume` would be **$135bn**, which is not.

**SO DOLLAR VOLUME IS SPLIT-INVARIANT PROVIDED THE TWO LEGS ARE ADJUSTED CONSISTENTLY** -- a
split halves the price and doubles the shares -- which is why this pairs `close` with `volume`
and why it must agree with `adv_from_bars`'s as-traded `raw_close * volume` pairing. Pairing
`closeunadj` with `volume` is the one combination that is wrong, and it is wrong by the split
factor, silently, on exactly the names that split. Pinned by test on CMG / AAPL / WMT / MSTR /
SIRI with JPM as an unsplit control.

WHAT THIS DOES NOT DO
---------------------
It does not wire `MIN_AVG_DOLLAR_VOLUME`, it does not touch the shipped price files, and
`prefilter_adv_wired` stays **false**. The OHLC and volume are emitted **BESIDE** the price
files in their own directory, so every default panel payload is bit-identical (`C3`).
"""
from __future__ import annotations

import csv
import os
from typing import Dict, Iterable, Optional, Sequence, Tuple

#: ONE definition of the live screen's window. Imported, never re-declared -- `adv.py` already
#: owns it and ties it to `prices.py:243` in its own docstring.
from .adv import ADV_WINDOW_SESSIONS, MIN_SESSIONS, adv_series as _crsp_adv_series

#: The frozen export. A freeze, not the live bulk dir: `data/bulk/` has no SEP at all, which is
#: the whole subject of the record correction above.
SEP_RELATIVE = os.path.join("backtest_freeze_2026-08", "bulk", "sep.csv")

#: The header this module was written against, asserted on every read. A silently reordered or
#: renamed column would otherwise be read positionally and produce a plausible wrong number.
SEP_HEADER = ("ticker", "date", "open", "high", "low", "close", "volume",
              "closeadj", "closeunadj", "lastupdated")

#: Emitted BESIDE the shipped `data/backtest/prices/<T>.csv`, never inside them.
OHLCV_DIRNAME = os.path.join("backtest", "ohlcv")

OHLCV_HEADER = ("date", "open", "high", "low", "close", "volume", "closeunadj")


class SepUnavailable(RuntimeError):
    """Raised rather than returning an empty result.

    A missing export must not read as "this universe has no volume". That is the shape of the
    defect this module exists to correct -- a search that did not reach a file, reported as the
    file not existing.
    """


def sep_path(data_root: str) -> str:
    return os.path.join(data_root, SEP_RELATIVE)


def assert_header(path: str) -> Tuple[str, ...]:
    """Read and verify the header. Returns it, so a caller can record what it actually saw."""
    if not os.path.exists(path):
        raise SepUnavailable("SEP export not found at %s" % path)
    with open(path, "r", encoding="utf-8", newline="") as fh:
        head = next(csv.reader(fh))
    got = tuple(h.strip() for h in head)
    if got != SEP_HEADER:
        raise SepUnavailable("SEP header changed: %r (expected %r)" % (got, SEP_HEADER))
    return got


def dollar_volume(close, volume):
    """One row's dollar volume: SPLIT-ADJUSTED close times SPLIT-ADJUSTED volume.

    Deliberately NOT `adv.dollar_volume`, and the reason is a measurement rather than a
    preference: that function applies `abs()` to honour CRSP's negative bid/ask-midpoint
    convention, which SEP does not have. Borrowing it would silently make a negative SEP close --
    which would be a data fault worth seeing -- read as a positive dollar volume. The negative
    share is REPORTED by `scan()` instead, and measured at zero.
    """
    import numpy as np
    c = np.asarray(close, dtype="float64")
    v = np.asarray(volume, dtype="float64")
    return c * v


def scan(path: str, tickers: Iterable[str], start: str = "2007-01-01",
         on_ticker=None) -> dict:
    """ONE streaming pass over the 3.2 GB export, keeping only `tickers` from `start`.

    Streamed with `csv` rather than loaded: the file is larger than this machine will hold
    comfortably, and a chunked pandas read would still materialise every column.

    `on_ticker(ticker, rows)` is called once per ticker with its rows sorted by date, so a
    caller can write a sidecar file without a second pass. Returns a census.
    """
    assert_header(path)
    want = {str(t).upper() for t in tickers}
    by_t: Dict[str, list] = {}
    census = {"rows_read": 0, "rows_kept": 0, "tickers_seen": 0,
              "null_volume_rows": 0, "negative_close_rows": 0,
              "nonpositive_volume_rows": 0}
    with open(path, "r", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        next(r)
        for row in r:
            census["rows_read"] += 1
            t = row[0].upper()
            if t not in want:
                continue
            d = row[1]
            if d < start:
                continue
            try:
                o, h, lo = float(row[2]), float(row[3]), float(row[4])
                c = float(row[5])
                v = float(row[6]) if row[6] not in ("", "NA", "None") else float("nan")
                cu = float(row[8]) if row[8] not in ("", "NA", "None") else float("nan")
            except ValueError:
                census["null_volume_rows"] += 1
                continue
            if c < 0:
                census["negative_close_rows"] += 1
            if not (v > 0):
                # A zero or absent volume is COUNTED, never treated as a traded session --
                # `MissingIsNotZero`: a zero dollar volume sits below every floor, so admitting
                # it converts "we cannot see this session" into "this name did not trade".
                census["nonpositive_volume_rows"] += 1
                continue
            by_t.setdefault(t, []).append((d, o, h, lo, c, v, cu))
            census["rows_kept"] += 1
    census["tickers_seen"] = len(by_t)
    if on_ticker is not None:
        for t, rows in by_t.items():
            rows.sort(key=lambda x: x[0])
            on_ticker(t, rows)
    return {"census": census, "by_ticker": by_t}


def write_ohlcv(out_dir: str, ticker: str, rows: Sequence[tuple]) -> str:
    """Write ONE ticker's OHLCV sidecar. BESIDE the price files, never inside them (`C3`)."""
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "%s.csv" % ticker)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(OHLCV_HEADER)
        for d, o, h, lo, c, v, cu in rows:
            w.writerow([d, o, h, lo, c, v, cu])
    return p


def adv_series(by_ticker: Dict[str, Sequence[tuple]],
               window: int = ADV_WINDOW_SESSIONS,
               min_sessions: int = MIN_SESSIONS):
    """Trailing-mean dollar volume per (ticker, date), STRICTLY point-in-time.

    DELEGATES the roll to `adv.adv_series` (`B7`: one implementation of the window, so the SEP
    and CRSP series cannot drift apart in their definition). The only adaptation is the column
    vocabulary -- SEP has no `permno` and no negative-price convention -- so the frame is handed
    over with `close` in the `prc` slot and the pre-computed dollar volume is checked against it.
    """
    import pandas as pd
    recs = []
    for t, rows in by_ticker.items():
        for d, _o, _h, _lo, c, v, _cu in rows:
            recs.append((t, d, c, v))
    if not recs:
        return pd.DataFrame(columns=["ticker", "date", "adv"])
    df = pd.DataFrame(recs, columns=["permno", "date", "prc", "vol"])
    out = _crsp_adv_series(df, window=window, min_sessions=min_sessions)
    return out.rename(columns={"permno": "ticker"})


def by_cell(series) -> Dict[Tuple[str, str], float]:
    """`(ticker, 'YYYY-MM-DD') -> adv`, the shape a panel coverage census consumes."""
    return {(str(t).upper(), str(d)[:10]): float(a)
            for t, d, a in zip(series["ticker"], series["date"], series["adv"])}


def pit_adv_at(cell_index: Dict[Tuple[str, str], float], ticker: str,
               as_of: str, sessions: Sequence[str]) -> Optional[float]:
    """The ADV observable for `ticker` on `as_of`: the last session STRICTLY BEFORE it.

    A panel rebalance date need not be a trading day for every name, so the lookup walks back
    rather than requiring an exact hit -- and it walks back from STRICTLY BEFORE `as_of`, which
    is the same strictly-before rule `adv.adv_series` already applies inside the window.
    """
    t = str(ticker).upper()
    d0 = str(as_of)[:10]
    for d in reversed(sessions):
        if d < d0:
            v = cell_index.get((t, d))
            if v is not None:
                return v
    return None
