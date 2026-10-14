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


# --------------------------------------------------------- PREREG_sellpremium2.md: 25 DELTA
# `T2`/`T3`. SELL-PREMIUM-2 keeps the event, the tier, the tenor band, the 6.0-year crash bar and
# the synthetic stress row, and changes exactly ONE thing: the strike rule. It is `V6-OPT`'s --
# the put nearest 25 delta, solved on the PUT leg -- which is the only rule in the clearing range
# with a measured prior.
DELTA_TARGET = 0.25

# **THE MONEYNESS BAND IS NOT APPLIED TO A DELTA RULE (`T3`).** Where a 25-delta put sits in
# moneyness is a function of the name's own volatility -- that is the point of a delta target --
# so a fixed 0.85-0.95 band truncates the rule exactly in the low-vol names, where a 25-delta put
# sits closest to the money. At the register's calibrated IV of 0.2864 true 25 delta is at 0.9398,
# inside the band; at a materially lower IV it is outside it, and those rows would vanish with
# nothing raising. The band survives only as a REPORTED diagnostic.
DELTA_MON_BAND = None


def index_by_date(raw: pd.DataFrame) -> dict:
    """`date -> that session's rows`, built ONCE per ticker-year.

    Pure speed, and it changes no result: `put_funnel` scanned the whole frame per session, which
    on a 200k-row chain is the dominant cost of the pricing pass. Proved inert by the kill pass
    reproducing SELL-PREMIUM's funnel exactly.
    """
    if raw is None or not len(raw):
        return {}
    return {d: g for d, g in raw.groupby("date", sort=False)}


def pick_put_by_delta(cands: pd.DataFrame, deltas: dict, date_iso: str,
                      target: float = DELTA_TARGET) -> dict:
    """The put nearest `target` delta, solved on the PUT leg (`V6-OPT`'s rule).

    **A CANDIDATE WITH NO DELTA IS EXCLUDED AND COUNTED, NEVER READ AS ZERO (`T4`).** The delta
    comes from `options_derived`, which does not carry every raw row; treating a missing delta as
    0.0 would make every such contract look like a far-out-of-the-money put and win the selection
    outright. The caller reports `no_delta` so a large join loss is visible rather than silent.

    Ties break by the LONGER tenor and then the TIGHTER quote, so a re-run is bit-identical.
    """
    if cands is None or not len(cands):
        return {"pick": None, "no_delta": 0, "n_cands": 0}
    rows, missing = [], 0
    for _i, r in cands.iterrows():
        d = deltas.get((date_iso, str(r["expiration"]), float(r["strike"])))
        if d is None or not np.isfinite(d[0]):
            missing += 1
            continue
        rows.append((abs(abs(float(d[0])) - float(target)), -int(r["dte"]),
                     float(r["ask"]) - float(r["bid"]), r, float(d[0]), float(d[1])))
    if not rows:
        return {"pick": None, "no_delta": missing, "n_cands": int(len(cands))}
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    _gap, _nd, _sp, r, dlt, iv = rows[0]
    return {"pick": {"expiration": str(r["expiration"]), "strike": float(r["strike"]),
                     "bid": float(r["bid"]), "ask": float(r["ask"]),
                     "mid": (float(r["bid"]) + float(r["ask"])) / 2.0,
                     "spot": float(r["spot"]), "moneyness": float(r["moneyness"]),
                     "dte": int(r["dte"]), "delta": dlt, "iv": iv,
                     "open_interest": float(r.get("open_interest") or 0.0),
                     "volume": float(r.get("volume") or 0.0)},
            "no_delta": missing, "n_cands": int(len(cands))}


def put_funnel(raw: pd.DataFrame, spot: dict, date_iso: str,
               dte_band=DTE_BAND, mon_band=MONEYNESS_BAND, day: pd.DataFrame = None) -> dict:
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
    # `day` is the pre-indexed session frame (`index_by_date`). Pure speed; identical result.
    src = raw if day is None else day
    d = src[(src["date"] == date_iso)
            & (src["right"].astype(str).str.upper().str[0] == "P")]
    out["any_put"] = int(len(d))
    if not len(d):
        return out
    dte = (pd.to_datetime(d["expiration"]) - pd.Timestamp(date_iso)).dt.days
    d = d[(dte >= dte_band[0]) & (dte <= dte_band[1])]
    out["in_dte"] = int(len(d))
    if not len(d):
        return out
    # `mon_band=None` disables the band for a DELTA rule (`T3`). The default is unchanged, so
    # SELL-PREMIUM's own funnel is bit-identical.
    if mon_band is None:
        out["in_moneyness"] = int(len(d))
    else:
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


#: The widest gap, in CALENDAR days, between the last available session and an expiry that can
#: still be an expiry-date settlement. A monthly expiry is a Saturday, so 1 day is ordinary; a
#: holiday stretch reaches about 5. Ten is comfortably inert on a map that covers its own
#: trades and catches a map that stops years short. It is NOT a tuning knob: it separates
#: "the calendar had no session that day" from "this map does not reach this expiry at all".
MAX_SETTLEMENT_STALE_DAYS = 10


def settlement_spot(spot: dict, expiry_iso: str, *, max_stale_days: int) -> Optional[float]:
    """The AS-TRADED close on the expiry session, or the last session at or before it.

    A short put held to expiry needs the underlying ON the expiry date. Monthly expiries are
    Saturdays in the early part of this era, so the last session at or before the expiry is the
    right object; a caller that demanded an exact match would silently drop every monthly.

    **`max_stale_days` IS REQUIRED AND HAS NO DEFAULT, AND THAT IS THE WHOLE REPAIR.** Without
    it this function answered *"the last session at or before the expiry"* with no limit, so a
    spot map that STOPPED before the expiry returned its own final close and the caller could
    not tell. `SELL-PREMIUM-2`'s stage 2 settled **73.02%** of its book that way -- every expiry
    after 2020-12-31 against that ticker's 2020-12-31 close, GE at $10.80 and NVDA at $522.20,
    **177 of 177** tickers with two or more assigned post-2020 trades landing on exactly one
    price. **Nothing raised and nothing was dropped; the arm produced a clean, plausible, wrong
    number** -- `MA31`'s failure mode. A default here would be how that silence came back
    (`MA5`), so every caller states its own limit and a refusal is a `None` the caller counts.
    """
    if not spot:
        return None
    ds = [d for d in spot if d <= expiry_iso]
    if not ds:
        return None
    last = max(ds)
    if _days_between(last, expiry_iso) > int(max_stale_days):
        # NOT a settlement. The map does not reach this expiry, and returning its final close
        # would be an answer about the MAP wearing the costume of an answer about the market.
        return None
    return float(spot[last])


def _days_between(a_iso: str, b_iso: str) -> int:
    """Calendar days from `a` to `b`, both ISO dates. Sessions cannot be counted from a map
    that has stopped -- it has no sessions after its own end, so a session count would read
    ZERO staleness for a map that is years short. The calendar is the only axis that can see
    the gap this guards against."""
    import datetime as _dt
    a = _dt.date.fromisoformat(str(a_iso)[:10])
    b = _dt.date.fromisoformat(str(b_iso)[:10])
    return (b - a).days


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
