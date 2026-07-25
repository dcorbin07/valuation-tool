"""
Factor engine — turn per-name metrics into oriented, standardized factors.

Two buckets (like the screener project): profitable names ("established") are
judged on value + quality + momentum + insider; unprofitable names
("speculative") on value-vs-peers + growth + momentum + insider, so a promising
unprofitable grower is never crowded out by a mature profitable one.

Every factor is built to be "higher = better," then z-scored across the universe
by cross_sectional.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import settings as S
from .cross_sectional import zscore

JUNK_SUFFIXES = ("W", "WS", "WT", "U", "UN", "RT", "R")


def prefilter(m: dict):
    """Decide whether a name is investable enough to score. Returns (keep, reason).

    Uses ONLY security-type and tradeability tests — never quality or fundamentals —
    so a genuine top pick (which by definition trades well and is a real company) is
    never dropped. A pre-revenue growth name passes; an ETF, warrant, penny, nano-cap
    or untradeable name does not. Every rejection carries a reason for the audit.
    """
    tkr = (m.get("ticker") or "").upper()
    if any(tkr.endswith("-" + s) or tkr.endswith("." + s) for s in JUNK_SUFFIXES):
        return False, "warrant/unit/right"
    if S.EXCLUDE_FUNDS and m.get("is_fund"):
        return False, "ETF/fund"
    price = m.get("price")
    if price is None:
        return False, "no price/quote"
    if price < S.PRICE_FLOOR:
        return False, f"penny (<${S.PRICE_FLOOR:.0f})"
    mc = m.get("market_cap")               # in $ millions
    if not mc or mc <= 0:
        return False, "no market cap"
    if mc < S.MIN_MARKET_CAP_MM:
        return False, f"nano-cap (<${S.MIN_MARKET_CAP_MM:.0f}M)"
    adv = m.get("avg_dollar_volume")       # in $
    if adv is not None and adv < S.MIN_AVG_DOLLAR_VOLUME:
        return False, "illiquid"
    return True, "ok"


def passes_gates(m: dict) -> bool:
    """Backward-compatible boolean wrapper around prefilter()."""
    return prefilter(m)[0]


def classify_bucket(m: dict) -> str:
    op = m.get("operating_income")
    ni = m.get("net_income")
    profit = op if op is not None else ni
    return "established" if (profit is not None and profit > 0) else "speculative"


_GRANULAR = ["earnings_yield", "fcf_yield", "ebit_ev", "neg_ev_sales", "neg_ps",
             "roic", "roe", "op_margin", "gross_margin", "neg_leverage",
             "revenue_growth", "growth_accel", "ret_12_1"]


def build_frame(metrics: list[dict]) -> pd.DataFrame:
    """Return a DataFrame indexed by ticker with the five factor columns
    (value, quality, growth, momentum, insider) standardized across the universe."""
    df = pd.DataFrame(metrics)
    if df.empty:
        return df
    df = df.set_index("ticker")

    # Derived oriented (higher = better) raw columns.
    df["neg_leverage"] = -pd.to_numeric(df.get("net_debt_to_ebitda"), errors="coerce")
    df["neg_ev_sales"] = -pd.to_numeric(df.get("ev_sales"), errors="coerce")
    df["neg_ps"] = -pd.to_numeric(df.get("ps"), errors="coerce")
    rg = pd.to_numeric(df.get("revenue_growth"), errors="coerce")
    rgp = pd.to_numeric(df.get("revenue_growth_prior"), errors="coerce")
    df["growth_accel"] = rg - rgp

    # Standardize granular metrics across the universe.
    for col in _GRANULAR:
        if col in df:
            df["z_" + col] = zscore(pd.to_numeric(df[col], errors="coerce"))
        else:
            df["z_" + col] = np.nan

    df["bucket"] = [classify_bucket(m) for m in metrics]

    # Factor columns = mean of the relevant standardized metrics.
    df["value_est"] = df[["z_earnings_yield", "z_fcf_yield", "z_ebit_ev"]].mean(axis=1)
    df["value_spec"] = df[["z_neg_ev_sales", "z_neg_ps"]].mean(axis=1)
    df["value"] = np.where(df["bucket"].eq("established"), df["value_est"], df["value_spec"])
    df["quality"] = df[["z_roic", "z_op_margin", "z_gross_margin", "z_neg_leverage"]].mean(axis=1)
    df["growth"] = df[["z_revenue_growth", "z_growth_accel"]].mean(axis=1)
    df["momentum"] = df["z_ret_12_1"]

    # Insider factor: metrics may carry an insider_score (0-100, 50 neutral).
    if "insider_score" in df:
        df["insider"] = (pd.to_numeric(df["insider_score"], errors="coerce") - 50.0) / 25.0
    else:
        df["insider"] = 0.0

    return df
