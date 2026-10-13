"""SELL-PREMIUM — shared construction. `PREREG_sellpremium.md`, committed ALONE at `2e9fe7b`.

**NOTHING SHARED IS RE-IMPLEMENTED HERE (`B7`, amendment `S5`).** The event, the point-in-time
tier and `X1`'s ticker half come from `valuation.studies.dipcall`; the settlement of a short put
held to expiry comes from `valuation.edge.assignment.settle_short`, which itself delegates to
`csp_surface.settle_put` and reproduces `V6-OPT`'s published per-trade `ret_on_strike` on 660 of
660 rows at max |delta| 0.000e+00. A second definition of either is how two registers come to
report two numbers for one question.

**THE TWO PRICE BASES, AND THEY ARE OPPOSITE (`S4`).** Measured on this repository, not assumed:
AAPL on 2018-01-02 reads **40.234** in `data/backtest/prices` and **172.260** as the chain's own
`spot`, a factor of **4.28**.

* **THE EVENT** — a daily return at or below `-2.5 x` the name's own strictly-prior 60-session
  volatility — is detected on the **ADJUSTED** series, because a return is what the adjustment
  exists to make comparable (`V6`'s `C5`: on a RAW series a 2-for-1 split reads as a -50% day,
  and companies split AFTER they rise).
* **THE STRIKE, THE MONEYNESS AND THE SETTLEMENT** read the **chain's own `spot`**, which is
  as-traded by construction (`O-1`'s MNST 3-for-1 booked a fake +1453% the other way).
  `assignment.settle_short` REFUSES an undeclared or adjusted basis, so this is enforced by the
  shipped primitive and not only by intention.

**WHY THE QUOTE FUNNEL READS THE *RAW* LAYER AND NOT THE DERIVED ONE.** Measured on AAPL-2018:
`options_derived` keeps 98,332 of 203,778 raw rows and is **two-sided on 1.0000 of them by
construction**, dropping every zero-bid row (40.66% of what it discards) and everything under
7 DTE. **So `K1`'s two-sided-quote funnel measured on the derived layer would read 1.000 having
checked nothing** — `MB21`'s `C1` family, a perfect score from comparing nothing. The funnel and
the traded quote come from the RAW layer; the derived layer supplies only `spot`, `delta` and
`iv`. The two agree where they overlap: `mid` reproduces `(bid+ask)/2` at max |dev| 0.000e+00.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from valuation.studies import dipcall as D

# ----------------------------------------------------------------------- the register's constants
# EVERY ONE IS FROM `PREREG_sellpremium.md` OR THE DRAFT IT ACCEPTS. Changing one after a
# measurement voids the item (`MA28`'s rule, inherited).
ERA_LO = "2016-01-01"
ERA_HI = "2019-12-31"

MONEYNESS_TARGET = 0.90                  # draft section 5 / void condition 1: ONE moneyness
MONEYNESS_BAND = (0.85, 0.95)            # draft section 3's funnel
DTE_BAND = (20, 60)                      # draft section 3, widened on COVERAGE before any arm

K1_MIN_EVENTS = 400                      # `S7`, the draft's floors VERBATIM and unrelaxed
K1_MIN_COVERED_DAYS = 150
K3_MAX_YEARS_OF_PREMIUM = 6.0            # draft section 6's pre-committed crash bar
K2_IV_BANDS = ((0.50, 0.65), (0.65, 0.80), (0.80, 1.01))   # `A3`'s own bands, reused verbatim

BH_Q = 0.10
BH_K = 5                                 # FIXED; a firing kill does not shrink it (`W-28`)
SEEDS = (0, 1, 2, 3, 4)                  # `A5`: five seeds minimum, the standing rule
SIZING_EQUITY = (25_000.0, 50_000.0, 100_000.0, 250_000.0)
SIZING_CAPS = (10, 50)
NULL_DRAWS = 200                         # `R3`'s shuffled null for the design effect

AS_TRADED = "as_traded"                  # the only basis `assignment` accepts


def chain_dir() -> str:
    return os.path.join(D.data_root(), "options")


def derived_dir() -> str:
    return os.path.join(D.data_root(), "options_derived")


def era_years() -> tuple:
    return tuple(range(int(ERA_LO[:4]), int(ERA_HI[:4]) + 1))


def has_chain(ticker: str, year: int) -> bool:
    return os.path.isfile(os.path.join(chain_dir(), ticker, "%s-%d.pkl" % (ticker, year)))


def read_raw_chain(ticker: str, year: int) -> Optional[pd.DataFrame]:
    """The RAW chain: `bid`/`ask` as quoted, nothing filtered. See the module docstring for why
    this and not the derived layer."""
    p = os.path.join(chain_dir(), ticker, "%s-%d.pkl" % (ticker, year))
    if not os.path.isfile(p):
        return None
    df = pd.read_pickle(p)
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["expiration"] = pd.to_datetime(df["expiration"]).dt.strftime("%Y-%m-%d")
    return df


def spot_by_date(ticker: str, year: int) -> dict:
    """The AS-TRADED underlying, one value per session, from the derived layer's own `spot`.

    **NEVER `data/backtest/prices`** — that file is split- and dividend-adjusted and reads 4.28x
    low on AAPL-2018. This is the series every strike and every settlement in this register is
    measured against.
    """
    p = os.path.join(derived_dir(), ticker, "%s-%d.pkl" % (ticker, year))
    if not os.path.isfile(p):
        return {}
    df = pd.read_pickle(p)
    if not isinstance(df, pd.DataFrame) or df.empty or "spot" not in df.columns:
        return {}
    d = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return dict(zip(d, df["spot"].astype(float)))


def greeks_by_key(ticker: str, year: int) -> dict:
    """`(date, expiration, strike) -> (delta, iv)` for PUTS, from the derived layer.

    Used by `A1`'s hedge and reported elsewhere. A missing key is a real state — the derived
    layer drops one-sided quotes — and callers must treat it as unknown, never as zero.
    """
    p = os.path.join(derived_dir(), ticker, "%s-%d.pkl" % (ticker, year))
    if not os.path.isfile(p):
        return {}
    df = pd.read_pickle(p)
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {}
    df = df[df["right"].astype(str).str.upper().str[0] == "P"]
    if df.empty:
        return {}
    d = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    e = pd.to_datetime(df["expiration"]).dt.strftime("%Y-%m-%d")
    return {(a, b, float(c)): (float(dd), float(ii))
            for a, b, c, dd, ii in zip(d, e, df["strike"], df["delta"], df["iv"])}


def dte_days(date_iso: str, expiry_iso: str) -> int:
    """CALENDAR days, which is what a DTE band means and what the chain's own `dte` column uses."""
    return int((pd.Timestamp(expiry_iso) - pd.Timestamp(date_iso)).days)


def put_funnel(raw: pd.DataFrame, spot: dict, date_iso: str,
               dte_band=DTE_BAND, mon_band=MONEYNESS_BAND) -> dict:
    """`K1`'s funnel on ONE session, step by step, so each step's loss is attributable.

    Returns counts plus the surviving candidate frame. The steps are the draft's section 3:
    any put row -> an expiry in the DTE band -> a strike in the moneyness band -> a TWO-SIDED
    quote. The last one is what binds (147 -> 48 in the draft's 2018 spot-check).
    """
    out = {"any_put": 0, "in_dte": 0, "in_moneyness": 0, "two_sided": 0, "cands": None}
    s = spot.get(date_iso)
    if s is None or not np.isfinite(s) or s <= 0:
        out["no_spot"] = True
        return out
    d = raw[(raw["date"] == date_iso)
            & (raw["right"].astype(str).str.upper().str[0] == "P")]
    out["any_put"] = int(len(d))
    if not len(d):
        return out
    dte = (pd.to_datetime(d["expiration"]) - pd.Timestamp(date_iso)).dt.days
    d = d[(dte >= dte_band[0]) & (dte <= dte_band[1])]
    out["in_dte"] = int(len(d))
    if not len(d):
        return out
    mon = d["strike"].astype(float) / float(s)
    d = d[(mon >= mon_band[0]) & (mon <= mon_band[1])]
    out["in_moneyness"] = int(len(d))
    if not len(d):
        return out
    d = d[(d["bid"].astype(float) > 0.0) & (d["ask"].astype(float) > d["bid"].astype(float))]
    out["two_sided"] = int(len(d))
    if not len(d):
        return out
    d = d.copy()
    d["spot"] = float(s)
    d["moneyness"] = d["strike"].astype(float) / float(s)
    d["dte"] = (pd.to_datetime(d["expiration"]) - pd.Timestamp(date_iso)).dt.days
    out["cands"] = d
    return out


def pick_put(cands: pd.DataFrame, target: float = MONEYNESS_TARGET) -> Optional[dict]:
    """The contract the register trades: the strike nearest `target` moneyness, ties broken by
    the LONGER tenor and then by the TIGHTER quote — deterministic, so a re-run is bit-identical.

    **ONE moneyness and one tenor band, both fixed in the register. There is no grid here and
    adding one is void condition 1.**
    """
    if cands is None or not len(cands):
        return None
    c = cands.copy()
    c["_gap"] = (c["moneyness"] - float(target)).abs()
    c["_rel"] = (c["ask"].astype(float) - c["bid"].astype(float)) / (
        (c["ask"].astype(float) + c["bid"].astype(float)) / 2.0)
    c = c.sort_values(["_gap", "dte", "_rel"], ascending=[True, False, True])
    r = c.iloc[0]
    return {"expiration": str(r["expiration"]), "strike": float(r["strike"]),
            "bid": float(r["bid"]), "ask": float(r["ask"]),
            "mid": (float(r["bid"]) + float(r["ask"])) / 2.0,
            "spot": float(r["spot"]), "moneyness": float(r["moneyness"]),
            "dte": int(r["dte"]), "open_interest": float(r.get("open_interest") or 0.0),
            "volume": float(r.get("volume") or 0.0)}


def settlement_spot(spot: dict, expiry_iso: str) -> Optional[float]:
    """The AS-TRADED close on the expiry session, or the last session at or before it.

    A short put held to expiry needs the underlying ON the expiry date. Monthly expiries are
    Saturdays in the early part of this era, so the last session at or before the expiry is the
    right object; a caller that demanded an exact match would silently drop every monthly.
    """
    if not spot:
        return None
    ds = [d for d in spot if d <= expiry_iso]
    if not ds:
        return None
    return float(spot[max(ds)])


def years_of_premium(fall: float, moneyness: float, premium_frac: float,
                     turns_per_year: float) -> float:
    """`K3`'s statistic: how many years of premium one crash of size `fall` costs.

    The loss on secured cash for a cash-secured put struck at `moneyness x spot` when the name
    falls `fall` over the tenor is `(fall - (1 - moneyness)) / moneyness`, floored at zero.
    """
    loss = max(0.0, (float(fall) - (1.0 - float(moneyness))) / float(moneyness))
    annual = float(premium_frac) * float(turns_per_year)
    if annual <= 0:
        return float("inf")
    return loss / annual


def worst_rolling(close: np.ndarray, window: int) -> float:
    """The worst `window`-session return in a series. Used on SPY for `K3` — a property of a
    PUBLIC benchmark, so it reads no quadrant and charges nothing."""
    c = np.asarray(close, dtype=float)
    if len(c) <= window:
        return float("nan")
    r = c[window:] / c[:-window] - 1.0
    r = r[np.isfinite(r)]
    return float(np.min(r)) if len(r) else float("nan")


def benjamini_hochberg(pvals, q: float = BH_Q, k: int = BH_K) -> list:
    """BH with `k` FIXED by the register. Shrinking `k` after a kill fires would make every
    surviving threshold easier, which is what `W-28` forbids."""
    rows = sorted([(p, i) for i, p in enumerate(pvals)],
                  key=lambda x: (x[0] if x[0] == x[0] else 1.0))
    out = []
    for rank, (p, i) in enumerate(rows, start=1):
        thr = rank * float(q) / float(k)
        out.append({"rank": rank, "index": i, "p_two_sided": p, "bh_threshold": thr,
                    "survives": bool(p == p and p <= thr)})
    return out
