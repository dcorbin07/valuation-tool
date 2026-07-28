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


# Every individual number that feeds a theme (all oriented higher = better), z-scored
# across the universe then averaged into its theme below. Sourced from settings so the
# factor engine and the Edge Lab number-diagnostic never drift apart.
_GRANULAR = list(S.NUMBERS_ALL)


def build_frame(metrics: list[dict], sector_neutral=None, residual_momentum=None) -> pd.DataFrame:
    """Return a DataFrame indexed by ticker with the theme columns standardized across
    the universe. sector_neutral scores each number relative to its sector peers (removes
    accidental sector bets); residual_momentum strips the beta component out of momentum.
    Both default to config."""
    from ..config import CONFIG
    if sector_neutral is None:
        sector_neutral = CONFIG.sector_neutral
    if residual_momentum is None:
        residual_momentum = CONFIG.residual_momentum
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

    # --- individual theme inputs (each oriented higher = better) ---
    def _num(c):   # always a Series aligned to df.index, even if the column is absent
        return pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
    mc = _num("market_cap")
    gp, td, te = _num("gross_profit"), _num("total_debt"), _num("total_equity")
    rev, fcf, ni = _num("revenue"), _num("fcf"), _num("net_income")
    ebit, iexp = _num("operating_income"), _num("interest_expense")
    beta, rvol = _num("beta"), _num("realized_vol")
    cap_emp = td.fillna(0.0) + te                        # capital employed ≈ debt + book equity

    df["book_to_price"] = np.where(mc > 0, te / mc, np.nan)             # value: cheapness on book
    df["gp_on_capital"] = np.where(cap_emp > 0, gp / cap_emp, np.nan)   # quality: Novy-Marx gross profitability
    df["fcf_margin"] = np.where(rev > 0, fcf / rev, np.nan)             # quality: cash profitability
    df["accruals_q"] = np.where(ni > 0, fcf / ni, np.nan)              # quality: earnings backed by cash (Sloan)
    df["interest_cov"] = np.where(iexp > 0, ebit / iexp, np.nan)        # quality: can it service its debt
    df["ret_6_1"] = _num("ret_6_1")                                    # momentum: 6-1 month return
    df["high_prox"] = _num("high_prox")                                # momentum: nearness to 52-week high
    df["neg_beta"] = -beta                                              # low-risk: betting-against-beta
    df["neg_vol"] = -rvol                                              # low-risk: low realized volatility
    df["neg_issuance"] = -_num("share_issuance")                        # capital discipline (hook)
    df["neg_asset_growth"] = -_num("asset_growth")                      # capital discipline (hook)
    df["earn_rev"] = _num("earnings_revision")                          # sentiment: estimate revisions (hook)
    df["rating_rev"] = _num("rating_rev")                               # sentiment: net analyst upgrades-downgrades
    df["neg_rating_disp"] = _num("neg_rating_disp")                     # sentiment: analyst agreement (already negated)
    df["neg_log_mktcap"] = -np.log(mc.where(mc > 0))                    # size: small-cap tilt

    # Sector-neutral: judge each number against its sector peers, not the whole market
    # (a 20% margin means different things in software vs utilities). Subtract the sector
    # median first; the global z-score below then standardizes the sector-relative value.
    if sector_neutral and "sector" in df.columns:
        _grp = df["sector"].fillna("?")
        for col in _GRANULAR:
            if col in df.columns:
                s = pd.to_numeric(df[col], errors="coerce")
                df[col] = s - s.groupby(_grp).transform("median")

    # Standardize granular metrics across the universe.
    for col in _GRANULAR:
        if col in df:
            df["z_" + col] = zscore(pd.to_numeric(df[col], errors="coerce"))
        else:
            df["z_" + col] = np.nan

    df["bucket"] = [classify_bucket(m) for m in metrics]

    # Factor columns = mean of the relevant standardized metrics.
    # Themes = mean of their (already-standardized) inputs, so a name with a missing
    # input isn't punished; an all-missing theme stays NaN and is neutralized per name.
    df["value_est"] = df[["z_earnings_yield", "z_fcf_yield", "z_ebit_ev", "z_book_to_price"]].mean(axis=1)
    df["value_spec"] = df[["z_neg_ev_sales", "z_neg_ps", "z_book_to_price"]].mean(axis=1)
    df["value"] = np.where(df["bucket"].eq("established"), df["value_est"], df["value_spec"])
    df["quality"] = df[["z_roic", "z_roe", "z_op_margin", "z_gross_margin", "z_neg_leverage",
                        "z_gp_on_capital", "z_fcf_margin", "z_accruals_q", "z_interest_cov"]].mean(axis=1)
    df["growth"] = df[["z_revenue_growth", "z_growth_accel"]].mean(axis=1)
    df["momentum"] = df[["z_ret_12_1", "z_ret_6_1", "z_high_prox"]].mean(axis=1)

    # Residual momentum: strip the beta component so momentum is stock-specific, not just
    # "high-beta names rose in an up market". Regress momentum on beta cross-sectionally
    # and keep the residual.
    if residual_momentum and "beta" in df.columns:
        _b = pd.to_numeric(df["beta"], errors="coerce")
        _m = df["momentum"]
        _mask = _b.notna() & _m.notna()
        if _mask.sum() > 10 and float(_b[_mask].std(ddof=0)) > 0:
            _bc = _b[_mask] - _b[_mask].mean()
            _slope = float((_bc * (_m[_mask] - _m[_mask].mean())).sum() / (_bc ** 2).sum())
            df.loc[_mask, "momentum"] = _m[_mask] - _slope * _bc
    df["low_risk"] = df[["z_neg_beta", "z_neg_vol"]].mean(axis=1)
    df["capital_discipline"] = df[["z_neg_issuance", "z_neg_asset_growth"]].mean(axis=1)
    # Sentiment blends whichever inputs are present: estimate revisions (still a hook —
    # no point-in-time source for them) and the analyst rating-action signals. .mean()
    # skips NaNs, so a provider carrying only one of them still gets a usable theme, and
    # a provider carrying none leaves it neutral exactly as before.
    df["sentiment"] = df[["z_earn_rev", "z_rating_rev", "z_neg_rating_disp"]].mean(axis=1)
    df["size"] = df["z_neg_log_mktcap"]
    df["institutional"] = df["z_inst_accum"]        # 13F accumulation (backtest/hook; neutral live)

    # Insider factor: metrics may carry an insider_score (0-100, 50 neutral).
    if "insider_score" in df:
        df["insider"] = (pd.to_numeric(df["insider_score"], errors="coerce") - 50.0) / 25.0
    else:
        df["insider"] = 0.0

    return df
