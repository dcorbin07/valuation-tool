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
    mc = m.get("market_cap")               # USD dollars (see providers.METRICS_UNITS)
    if not mc or mc <= 0:
        return False, "no market cap"
    if mc < S.MIN_MARKET_CAP_MM * 1e6:
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


def build_frame(metrics: list[dict], sector_neutral=None, residual_momentum=None,
                value_ev_multiples=None, standardizer=None, bucket_relative=None,
                sector_relative_cols=None) -> pd.DataFrame:
    """Return a DataFrame indexed by ticker with the theme columns standardized across
    the universe. sector_neutral scores each number relative to its sector peers (removes
    accidental sector bets); residual_momentum strips the beta component out of momentum.
    value_ev_multiples also feeds EV/Sales + EV/EBITDA into the ESTABLISHED value branch
    (they already feed the speculative one). All three default to config.

    LEDGER S20/S21 — `standardizer` swaps the PER-NUMBER standardizer (layer 1: every `z_*`
    column below). It defaults to `cross_sectional.zscore`, the shipped winsorized z-score, so
    with it unset this function is behaviourally identical to before. The study passes
    `rank_score` and `zscore_nowinsor`; see PREREG_s20_s21_construction.md §3.

    Note the two documented asymmetries, which are properties of the construction rather than
    of the swap: `insider` below is NOT z-scored (it is a fixed affine map of insider_score) and
    so is untouched by this argument, and `size` is a SINGLE standardized column where every
    other theme is a mean of several."""
    from ..config import CONFIG
    if sector_neutral is None:
        sector_neutral = CONFIG.sector_neutral
    if residual_momentum is None:
        residual_momentum = CONFIG.residual_momentum
    if value_ev_multiples is None:
        value_ev_multiples = CONFIG.value_ev_multiples
    df = pd.DataFrame(metrics)
    if df.empty:
        return df
    df = df.set_index("ticker")

    # Derived oriented (higher = better) raw columns.
    df["neg_leverage"] = -pd.to_numeric(df.get("net_debt_to_ebitda"), errors="coerce")
    # AUDIT B18 — NEGATIVE ENTERPRISE VALUE, one convention for all three EV ratios. A net-cash
    # company used to rank as the CHEAPEST name in the cross-section on neg_ev_sales (negated
    # negative multiple -> large positive) while simultaneously ranking as the MOST EXPENSIVE on
    # ebit_ev. `neg_ev_ebitda` was already guarded; this one was not. A negative multiple is not
    # on the same scale as a positive one, so the defensible convention is MISSING, not extreme.
    # ~0.70% of rows.
    _evsales = pd.to_numeric(df["ev_sales"], errors="coerce") \
        if "ev_sales" in df.columns else pd.Series(np.nan, index=df.index)
    df["neg_ev_sales"] = -_evsales.where(_evsales > 0)
    # EV/EBITDA only means anything on POSITIVE EBITDA. A loss-maker's multiple comes out
    # negative, and negating it would rank the deepest losses as the greatest bargains. The
    # panel already guards this at construction; FMP hands back its raw value unguarded, so
    # the guard lives here where every provider passes through it.
    # (built as an explicit Series: df.get on an ABSENT column returns None, and
    # pd.to_numeric(None) is a bare scalar NaN with no .where — which is how the other
    # derivations here get away with a plain unary minus.)
    _evebitda = pd.to_numeric(df["ev_ebitda"], errors="coerce") \
        if "ev_ebitda" in df.columns else pd.Series(np.nan, index=df.index)
    df["neg_ev_ebitda"] = -_evebitda.where(_evebitda > 0)
    df["neg_ps"] = -pd.to_numeric(df.get("ps"), errors="coerce")
    # Growth acceleration. Derive it from this-year-vs-last-year revenue growth ONLY when a
    # provider supplies revenue_growth_prior; otherwise leave whatever the caller already
    # computed. The unconditional version silently emptied the column for the backtest panel,
    # which computes growth_accel itself in _yoy (from two prior-year point-in-time rows) and
    # never supplies revenue_growth_prior — so `growth` was effectively revenue_growth alone.
    rgp = pd.to_numeric(df.get("revenue_growth_prior"), errors="coerce") \
        if "revenue_growth_prior" in df.columns else None
    if rgp is not None and rgp.notna().any():
        df["growth_accel"] = pd.to_numeric(df.get("revenue_growth"), errors="coerce") - rgp
    elif "growth_accel" not in df.columns:
        df["growth_accel"] = np.nan

    # --- individual theme inputs (each oriented higher = better) ---
    def _num(c):   # always a Series aligned to df.index, even if the column is absent
        return pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
    mc = _num("market_cap")                              # USD dollars, like every absolute figure
    gp, td, te = _num("gross_profit"), _num("total_debt"), _num("total_equity")
    rev, fcf, ni = _num("revenue"), _num("fcf"), _num("net_income")
    ebit, iexp = _num("operating_income"), _num("interest_expense")
    beta, rvol = _num("beta"), _num("realized_vol")
    cap_emp = td.fillna(0.0) + te                        # capital employed ≈ debt + book equity

    # Value: cheapness on book. Prefer a book_to_price the caller already computed — the
    # backtest panel supplies it in USD (equityusd / market_cap), because `total_equity` is in
    # the company's REPORTING currency while market cap is USD, and dividing one by the other
    # handed foreign reporters a fake cheapness of up to ~1,500x. `total_equity` itself stays
    # local on purpose: gp_on_capital below divides local gross profit by it, and that ratio is
    # only correct while BOTH sides stay in the same currency.
    _b2p = _num("book_to_price")
    df["book_to_price"] = np.where(_b2p.notna(), _b2p,
                                   np.where(mc > 0, te / mc, np.nan))
    df["gp_on_capital"] = np.where(cap_emp > 0, gp / cap_emp, np.nan)   # quality: Novy-Marx gross profitability
    df["fcf_margin"] = np.where(rev > 0, fcf / rev, np.nan)             # quality: cash profitability
    # AUDIT B10 — this line used to overwrite `accruals_q` UNCONDITIONALLY. The backtest panel
    # computes the Sloan measure itself (`-((NI - CFO) / assets)`, fundamental_panel.py) and
    # hands it in; this then replaced it with FCF/NI restricted to profitable names. So the
    # signal REPORTED as `accruals_q` was not the one documented, its coverage fell to 75.3%
    # (consistent with the ni > 0 restriction, against ~95% for the accruals measure), and its
    # recorded IC fell from t +3.08 to +1.26. `book_to_price` and `growth_accel` above are both
    # guarded against exactly this; this one was not. The caller now wins, and the FCF/NI
    # variant is kept alongside under its own name so the two can be measured head to head
    # instead of one silently replacing the other.
    _acc = _num("accruals_q")
    df["accruals_fcf_ni"] = np.where(ni > 0, fcf / ni, np.nan)         # quality: earnings backed by cash
    df["accruals_q"] = np.where(_acc.notna(), _acc, df["accruals_fcf_ni"])
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
    # Sharadar-only additions. These arrive pre-signed from the panel (already negated
    # where "less is better"), so they need no further orientation here.
    df["f_score"] = _num("f_score")                                     # quality: Piotroski 0-9
    df["cash_op_prof"] = _num("cash_op_prof")                           # quality: cash-based op profitability
    df["neg_ret_1m"] = _num("neg_ret_1m")                               # low-risk: short-term reversal
    df["neg_max_ret"] = _num("neg_max_ret")                             # low-risk: MAX / lottery effect
    df["neg_idio_vol"] = _num("neg_idio_vol")                           # low-risk: idiosyncratic vol
    df["congress_net_buy"] = _num("congress_net_buy")                   # Congress (measured)
    df["congress_activity"] = _num("congress_activity")                 # Congress placebo
    df["govt_award_momentum"] = _num("govt_award_momentum")             # USAspend (measured)
    df["govt_award_level"] = _num("govt_award_level")                   # USAspend placebo
    df["activist_13d"] = _num("activist_13d")                           # SEC (measured only)
    df["passive_13g"] = _num("passive_13g")                             # SEC placebo
    df["neg_days_to_cover"] = _num("neg_days_to_cover")                 # FINRA (measured only)
    df["neg_short_interest_chg"] = _num("neg_short_interest_chg")       # FINRA (measured only)
    df["sm_elite_conviction"] = _num("sm_elite_conviction")             # 13F: quality-weighted (measured only)
    df["pead_car"] = _num("pead_car")                                   # PEAD: earnings CAR (measured only)
    df["pead_drift"] = _num("pead_drift")                               # PEAD: recent-only CAR (measured only)
    df["roe_ttm"] = _num("roe_ttm")                                     # quality: TTM ROE (measured only)
    df["roic_ttm"] = _num("roic_ttm")                                   # quality: TTM ROIC (measured only)
    df["inst_breadth"] = _num("inst_breadth")                           # institutional: holder breadth
    df["sm_conviction"] = _num("sm_conviction")                         # SF3: sum(position / manager AUM)
    df["sm_breadth"] = _num("sm_breadth")                               # SF3: growth in holder count
    df["sm_holders"] = _num("sm_holders")                               # SF3: number of managers holding
    df["sm_avg_position"] = _num("sm_avg_position")                     # SF3: avg $ per holder

    # Sector-neutral: judge each number against its sector peers, not the whole market
    # (a 20% margin means different things in software vs utilities). Subtract the sector
    # median first; the global z-score below then standardizes the sector-relative value.
    if sector_neutral and "sector" in df.columns:
        _grp = df["sector"].fillna("?")
        for col in _GRANULAR:
            if col in df.columns:
                s = pd.to_numeric(df[col], errors="coerce")
                df[col] = s - s.groupby(_grp).transform("median")

    # LEDGER S15 — sector-relative on a COLUMN SUBSET. The broad `sector_neutral` above
    # de-means EVERY granular metric, which is what SECTOR-NEUTRAL-B6 rejected three times;
    # S15 is the narrow variant that rejection left explicitly open, applying the same
    # operation to the VALUE theme's inputs alone. Same group, same median subtraction, same
    # global z-score below — only the column list differs. Defaults to None, so every existing
    # caller and the shipped panel are untouched.
    if sector_relative_cols and "sector" in df.columns:
        _sgrp = df["sector"].fillna("?")
        for col in sector_relative_cols:
            if col in df.columns:
                s = pd.to_numeric(df[col], errors="coerce")
                df[col] = s - s.groupby(_sgrp).transform("median")

    # LEDGER S12 — bucket-relative ranking, the audit's "add a `bucket_relative` toggle to the
    # standardisation step". Architecturally IDENTICAL to sector_neutral above (subtract the
    # group median, then let the global z-score below standardise the group-relative value); the
    # only difference is WHICH column defines the group. `bucket_relative` names that column:
    # "bucket" for the valuation split the audit specifies (established vs speculative), or a
    # cap-tier label for the framing the task asked about. Defaults to None, so every existing
    # caller is unchanged and the shipped panel is untouched.
    if bucket_relative:
        # `bucket` is not a column yet at this point — it is derived below, AFTER the granular
        # standardisation — so asking for it by name here would silently find nothing and make
        # the whole arm a NO-OP that still reports a verdict. Derive it from the metrics instead,
        # which is exactly what the line below does; any other group (e.g. `cap_tier`) is a
        # genuine metrics column and is read from the frame.
        if bucket_relative == "bucket":
            _bgrp = pd.Series([classify_bucket(m) for m in metrics], index=df.index).fillna("?")
        elif bucket_relative in df.columns:
            _bgrp = df[bucket_relative].fillna("?")
        else:
            _bgrp = None
        if _bgrp is not None:
            for col in _GRANULAR:
                if col in df.columns:
                    s = pd.to_numeric(df[col], errors="coerce")
                    df[col] = s - s.groupby(_bgrp).transform("median")

    # Standardize granular metrics across the universe.  [S20/S21 — layer 1]
    _std = zscore if standardizer is None else standardizer
    for col in _GRANULAR:
        if col in df:
            df["z_" + col] = _std(pd.to_numeric(df[col], errors="coerce"))
        else:
            df["z_" + col] = np.nan

    df["bucket"] = [classify_bucket(m) for m in metrics]

    # Factor columns = mean of the relevant standardized metrics.
    # Themes = mean of their (already-standardized) inputs, so a name with a missing
    # input isn't punished; an all-missing theme stays NaN and is neutralized per name.
    # Value is bucket-split: profitable names are judged on earnings-based yields, loss-makers
    # on sales multiples (an earnings yield is meaningless when earnings are negative).
    # value_ev_multiples extends the ESTABLISHED branch with the two EV multiples, which the
    # speculative branch has always used. EV/Sales is the 2nd-strongest value input on the full
    # panel (IC t +2.11) yet has never scored a single profitable name — see HANDOFF_growth_evsales.md.
    _est = ["z_earnings_yield", "z_fcf_yield", "z_ebit_ev", "z_book_to_price"]
    if value_ev_multiples:
        _est = _est + ["z_neg_ev_sales", "z_neg_ev_ebitda"]
    df["value_est"] = df[_est].mean(axis=1)
    df["value_spec"] = df[["z_neg_ev_sales", "z_neg_ps", "z_book_to_price"]].mean(axis=1)
    df["value"] = np.where(df["bucket"].eq("established"), df["value_est"], df["value_spec"])
    df["quality"] = df[["z_roic", "z_roe", "z_op_margin", "z_gross_margin", "z_neg_leverage",
                        "z_gp_on_capital", "z_fcf_margin", "z_accruals_q", "z_interest_cov",
                        "z_f_score"]].mean(axis=1)
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
    # The short-horizon anomalies (short-term reversal, MAX, idiosyncratic vol) are built in
    # _price_extras, are MEASURED (registered in NUMBER_THEME since R5) and do NOT feed this
    # theme. CORRECTED 2026-08-13 (R5): this comment used to say "every one carried the wrong
    # sign (median IC -0.014 / -0.072 / -0.025)". That was the 400-name / 110-rebalance
    # measurement, void under B12 and B6. On the corrected 2,531-name / 69-date panel all
    # three signs are POSITIVE (+0.00715 / +0.02634 / +0.05452) and all three are still
    # rejected -- for being weak, not for being backwards. None clears its own permutation
    # p95 in both halves. PREREG_r5_r6_alphabetical_rerun.md.
    #
    # REPORTED BECAUSE IT CUTS AGAINST THE PAIR THIS THEME DOES USE: on the same corrected
    # panel `neg_vol` reads t +0.89 and `neg_beta` reads t -0.39, so BOTH deployed inputs are
    # weaker than the two rejected volatility cousins (+1.15, +1.21). The theme carries ZERO
    # weight in the live composite, which bounds the consequence -- but anyone un-zeroing it
    # should read those four numbers first.
    df["low_risk"] = df[["z_neg_beta", "z_neg_vol"]].mean(axis=1)
    # Capital discipline is now share issuance ALONE. neg_asset_growth was DROPPED: on the
    # full 2,710-name / 110-date panel it measures median IC -0.0141 with t -0.70 — the wrong
    # sign. The investment factor says low asset growth should predict high returns; here
    # high asset growth did, so averaging it in was cancelling out neg_issuance (+0.0232,
    # t +2.25), the one input in this theme that works. It stays computed in _yoy and listed
    # in NUMBER_THEME so it keeps being measured — re-adding it is one column here.
    df["capital_discipline"] = df[["z_neg_issuance"]].mean(axis=1)
    # Sentiment blends whichever inputs are present: estimate revisions (still a hook —
    # no point-in-time source for them) and the analyst rating-action signals. .mean()
    # skips NaNs, so a provider carrying only one of them still gets a usable theme, and
    # a provider carrying none leaves it neutral exactly as before.
    df["sentiment"] = df[["z_earn_rev", "z_rating_rev", "z_neg_rating_disp"]].mean(axis=1)
    df["size"] = df["z_neg_log_mktcap"]
    # 13F: dollar accumulation plus holder-count breadth. The per-manager SF3 detail
    # isn't in the bundle, so breadth (how many institutions hold it) is the closest
    # available stand-in for "how many funds are buying".
    # Dollar accumulation + breadth of manager buying. sm_breadth (SF3 per-manager holder
    # counts) replaces inst_breadth (aggregate tally) as the breadth term: same quantity,
    # measured better.
    # RE-JUSTIFIED 2026-08-13 (R6). This swap's stated reason was "IC t +2.37 vs +1.48 on 800
    # large caps" — a comparison VOID under B12, because that universe was an ALPHABETICAL
    # slice. A LIVE SCORING DECISION was resting on it. Re-measured head to head on the
    # corrected 2,531-name / 69-date panel, on 49 covered dates at near-identical coverage
    # (0.7169 vs 0.7185):
    #     sm_breadth    median IC +0.02504  t +1.8481
    #     inst_breadth  median IC +0.02175  t +1.2371
    # THE ORDERING HOLDS, so the swap survives its own voided justification — but the gap
    # narrowed from 0.89 to 0.61 of a t, and NEITHER clears 2.0. Note also that the +1.73
    # recorded for sm_breadth below was dated 2026-08-01, three days BEFORE the B6/B7/B13
    # corrections landed, so it was never a corrected-panel figure either; +1.8481 is the
    # first. Measured, not changed: swapping a theme input is a construction change and a
    # vintage event. PREREG_r5_r6_alphabetical_rerun.md.
    df["institutional"] = df[["z_inst_accum", "z_sm_breadth"]].mean(axis=1)

    # Insider factor: metrics may carry an insider_score (0-100, 50 neutral).
    if "insider_score" in df:
        df["insider"] = (pd.to_numeric(df["insider_score"], errors="coerce") - 50.0) / 25.0
    else:
        df["insider"] = 0.0

    return df
