# -*- coding: utf-8 -*-
"""`STAGE1-BATCH2` — the free pre-outcome kills, in their OWN pass.

    python -m scripts.stage1_batch2_kills

**NO FORWARD RETURN IS TOUCHED ANYWHERE IN THIS FILE**, pinned by an AST test. Every kill is a
census of the panel's own inputs or of a scaling factor, so under `MB1-SEL` it can only BLOCK and
charges **zero trials**.

**IT RUNS AND IS READ BEFORE ANY ARM IS SCORED** (`O10`: a gating control computed in the same
pass as the outcomes cannot be claimed to have been read first). The arm runner REFUSES without a
passing artifact from this one.

**THE BUILD QUADRANT ONLY** — 2009–2019 × `stable_key_half(ticker) == 0`, on
`UNIVERSE_BIAS_PANEL_full_v3.pkl`. `build_quadrant`, `costume_rho`, `stable_key_half` and
`TIERED-POOL`'s `junk_ok` are all **CALLED** and never re-implemented (`B7`).

**EVERY BAR IS THE REGISTER'S**, quoted from `PREREG_stage1_batch2.md` and not re-chosen here.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.stage1_kills import (build_quadrant, costume_rho,              # noqa: E402
                                  verdict, BUILD_HALF_SPLIT)
from scripts.tiered_pool import junk_ok                                      # noqa: E402

REGISTER = "PREREG_stage1_batch2.md"
PANEL = "UNIVERSE_BIAS_PANEL_full_v3.pkl"
OUT = "STAGE1_BATCH2_KILLS.json"

# --------------------------------------------------------------------------------------------
# THE REGISTER'S BARS. Literals, so a drift shows as a diff here (`MA13`'s idiom) and a bar can
# never be read out of the data it judges.
# --------------------------------------------------------------------------------------------
TIER_FLOOR_USD = 10e9        # the incumbent's own absolute cap floor (charter Stage 1b)
CONTRACT_MIN_POSITIONS = 50  # the tier must clear this on EVERY date or the arm is NOT ASSESSABLE

K0_IBES_FLOOR = 0.70         # B4: tier IBES coverage, cells AND names (register 0.2)
B1_INERT_MEDIAN = 0.02       # B1: median per-date share failing >= 1 screen; below this is INERT
B2_LEVERAGE_SHARE = 0.50     # B2: share of dates the UNCAPPED scaling exceeds 1.0
B3_COSTUME_BAR = 0.60        # B3: mean per-date |rho| vs the shipped `momentum` theme
B3_MOMENTUM_ONLY_AT = 0.50   # above this, a pass is read residualised on `momentum` alone
B4_COSTUME_BAR = 0.60        # B4: mean per-date |rho| vs the `size` theme
B5_NONIDENTITY_BAR = 0.99    # B5: within-date rank corr vs `z_neg_issuance` must be BELOW this

#: the full-universe IBES figure, recorded so the tier reading can never be confused with it.
FULL_UNIVERSE_IBES_CELLS = 0.6999955119640681

B3_FORMATION_MONTHS = 36     # Blitz-Huij-Martens' own window
B3_SKIP_MONTHS = 1           # most recent month skipped
MIN_NAMES_PER_DATE = 20      # the shared floor batch 1 used for a per-date statistic


def fa():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis")


def data_root():
    from scripts.index_best import _data_root
    return _data_root()


def _num(x):
    try:
        v = float(x)
        return v if v == v and np.isfinite(v) else None
    except Exception:
        return None


# ============================================================================================
# THE TIER — the governing population (charter Stage 1b)
# ============================================================================================
def tier_frame(frame):
    """The incumbent's own absolute `cap >= $10B` floor, and its per-date name count.

    **AN ABSOLUTE THRESHOLD, NOT AN ABSOLUTE RANK, AND THAT IS `INDEX-CHOICE-ARM4`'s OWN
    DISTINCTION.** A rank is a property of the POPULATION and changes meaning the moment the
    universe is halved, so `X1`'s split cannot evaluate it. A market-cap threshold is a property
    of the NAME — a $10bn company is $10bn in either ticker half — so it is invariant under the
    split. Substituting a percentile would introduce a tier that is not the one the Index trades.

    The per-date count ships because a nominal $10bn floor DRIFTS in real terms across 2009–2019
    and a reader must be able to see the tier's size moving rather than assume it fixed.
    """
    mc = pd.to_numeric(frame["market_cap"], errors="coerce")
    t = frame[mc >= TIER_FLOOR_USD].copy()
    npd = t.groupby("date")["ticker"].nunique()
    below = sorted(str(d)[:10] for d in npd[npd < CONTRACT_MIN_POSITIONS].index)
    census = {
        "floor_usd": TIER_FLOOR_USD,
        "rows": int(len(t)), "names": int(t["ticker"].nunique()),
        "dates": int(t["date"].nunique()),
        "names_per_date": {str(k)[:10]: int(v) for k, v in npd.items()},
        "names_per_date_min": int(npd.min()) if len(npd) else 0,
        "names_per_date_median": float(npd.median()) if len(npd) else 0.0,
        "dates_below_contract_min_positions": below,
        "clears_50_on_every_date": not below,
        "why_the_count_ships": "a nominal $10bn floor drifts in real terms across 2009-2019, so "
                               "the tier's size must be visible rather than assumed fixed",
    }
    return t, census


# ============================================================================================
# K0 — B4's tier IBES census (register 0.2)
# ============================================================================================
def k0_tier_ibes(tier):
    """Does the dated IBES link reach 0.70 of the TIER's cells AND names?

    **THE FULL-UNIVERSE FIGURE IS 0.6999955119640681 AND IS NOT A PASS.** It misses by 4.5e-06,
    the knife edge `W-28`'s `K1` died on, and `W-28`'s rule is that a pre-committed bar may not
    be relaxed after watching it fail. What is permitted is a DIFFERENT POPULATION, and charter
    Stage 1b makes the tier the governing one — the draft's own `B6` kill measures coverage *"on
    the TIER (the governing population)"*, so this is the batch's own convention rather than a
    relaxation. `O-1` is why it is measured rather than inherited: that item applied an
    alert-book figure to the panel and was ~17x wrong.
    """
    try:
        from valuation.edge import ibes_link as IL
    except Exception as e:                                          # pragma: no cover
        return verdict("B4", None, {"state": "NOT MEASURABLE",
                                    "why": "valuation.edge.ibes_link import failed: %s" % e})
    # THE DATED ROUTE, THROUGH THE SAME CODE THE VALIDATOR USES. `resolve_route_b` was extracted
    # from `scripts/ibes_link_validate.py` precisely so this population goes through ONE
    # implementation (`B7`) -- a second copy of a three-step dated join is how two numbers for
    # one question come about, and the newer copy is usually the one carrying the defect.
    ids = IL.ibes_id()
    cusip_spans, _ = IL.spans(ids, key="cusip")
    crsp = IL.crsp_names()
    cr = IL.crsp_spans(crsp) if crsp is not None else None
    if cr is None:
        return verdict("B4", None, {"state": "NOT MEASURABLE",
                                    "why": "crsp_stocknames is absent, so no DATED route exists "
                                           "-- and an UNDATED one is W-3b's lease hazard at "
                                           "17.7pc contamination, which is not a substitute"})
    cells_df = tier[["ticker", "date"]].drop_duplicates().copy()
    cells_df["date"] = pd.to_datetime(cells_df["date"])
    rb = IL.resolve_route_b(cusip_spans, cr, cells_df)

    states = {}
    for st in rb["state"].astype(str):
        states[st] = states.get(st, 0) + 1
    ok_mask = rb["state"] == IL.OK
    ok_names = set(rb.loc[ok_mask, "ticker"].astype(str))
    cells = int(len(rb))
    cell_cov = (int(ok_mask.sum()) / cells) if cells else 0.0
    all_names = set(rb["ticker"].astype(str))
    name_cov = (len(ok_names) / len(all_names)) if all_names else 0.0
    passes = bool(cell_cov >= K0_IBES_FLOOR and name_cov >= K0_IBES_FLOOR)
    return verdict("B4", passes, {
        "kill": "K0 — tier IBES coverage",
        "floor": K0_IBES_FLOOR,
        "tier_cell_coverage": cell_cov, "tier_name_coverage": name_cov,
        "states": states, "cells": cells, "names": len(all_names),
        "names_resolved": len(ok_names),
        "full_universe_cell_coverage_FOR_CONTRAST": FULL_UNIVERSE_IBES_CELLS,
        "note": "the full-universe figure is 0.6999955119640681 and is NOT a pass -- it misses "
                "by 4.5e-06, which W-28 forbids relaxing. This is a DIFFERENT POPULATION, the "
                "charter's own governing one, and it is measured rather than inherited (O-1).",
        "if_it_fails": "B4 is NOT RUN and k STAYS 6",
    })


# ============================================================================================
# K1 (B1) — the junk screens' inertness on the tier
# ============================================================================================
def k1_b1_inertness(tier, hist):
    """`TIERED-POOL`'s three screens, CALLED verbatim via `junk_ok`.

    **THE DRAFT CALLS THIS THE LIKELIEST KILL OF THE SIX.** The tier is already large-cap and may
    already be clean — `TIERED-POOL` measured 0.0% of incumbent weight below $300M, and the whole
    premise of *"size matters if you control your junk"* is that junk concentrates at the SMALL
    end. A filter that removes nothing cannot move a book, and reporting a near-zero change as a
    null would be a statement about the book rather than about junk.
    """
    per_date, ev_shares = {}, []
    removed_reasons = {"netinc": 0, "fcf": 0, "leverage": 0}
    kept_counts = {}
    for d in sorted(tier["date"].unique()):
        dd = str(d)[:10]
        names = sorted(tier[tier["date"] == d]["ticker"].astype(str).unique())
        if not names:
            continue
        out = junk_ok(names, hist, dd)
        ok_map = out[0] if isinstance(out, tuple) else out
        detail = out[1] if isinstance(out, tuple) and len(out) > 1 else {}
        if not isinstance(ok_map, dict):
            continue
        n = len(names)
        failed = sum(1 for t in names if not ok_map.get(t))
        per_date[dd] = {"names": n, "failed_at_least_one": failed,
                        "share_failed": (failed / n) if n else None,
                        "kept": n - failed}
        kept_counts[dd] = n - failed
        if isinstance(detail, dict):
            # THE KEY IS `removed_by_condition`, NOT `removed` -- read off `junk_ok`'s own
            # source rather than guessed. A `.get("removed")` would have tallied zeros on every
            # date and shipped a clean, confident zero from a key that does not exist, which is
            # the blank-code-counter family (`MA_FINAL_BATCH` read 0 blanks on 1.5M of them).
            rc = detail.get("removed_by_condition") or {}
            for k in removed_reasons:
                v = rc.get(k)
                if isinstance(v, int):
                    removed_reasons[k] += v
            evs = detail.get("evaluable_share")
            if isinstance(evs, (int, float)):
                ev_shares.append(float(evs))

    shares = [v["share_failed"] for v in per_date.values() if v["share_failed"] is not None]
    med = float(np.median(shares)) if shares else None
    below = sorted(d for d, k in kept_counts.items() if k < CONTRACT_MIN_POSITIONS)
    inert = (med is not None and med < B1_INERT_MEDIAN)
    passes = bool(med is not None and not inert and not below)
    return verdict("B1", passes, {
        "kill": "K1 — inertness, plus the 50-name floor on the FILTERED tier",
        "inert_below_median_share": B1_INERT_MEDIAN,
        "median_share_failing_at_least_one_screen": med,
        "share_failed_p05": float(np.percentile(shares, 5)) if shares else None,
        "share_failed_p95": float(np.percentile(shares, 95)) if shares else None,
        "dates": len(per_date),
        "per_date": per_date,
        "removed_by_reason_total": removed_reasons,
        "evaluable_share_mean": (float(np.mean(ev_shares)) if ev_shares else None),
        "filtered_tier_dates_below_50": below,
        "state": ("INERT — the filter removes essentially nothing, so the arm carries NO VERDICT"
                  if inert else
                  ("NOT ASSESSABLE — the filtered tier falls below 50 names on %d date(s)"
                   % len(below) if below else "the filter bites; the arm may run")),
        "screens_are_TIERED_POOLs_own": "junk_ok is CALLED, so _ttm collapses restatements "
                                        "(D10-a), requires four distinct quarters, and refuses a "
                                        "window spanning more than TTM_MAX_SPAN_DAYS. A "
                                        "hand-rolled sum would silently understate a flow and "
                                        "read as a junk company -- the direction that would "
                                        "FLATTER this arm.",
    })


# ============================================================================================
# monthly closes — built ONCE, cached, and used by B2 and B3
# ============================================================================================
def monthly_closes(names, cache_name="STAGE1_BATCH2_MONTHLY.pkl"):
    """Month-end split-ADJUSTED closes per name, read once and cached.

    **THE ADJUSTED CLOSE IS THE RIGHT BASIS HERE AND THAT IS NOT A DETAIL.** `close` in these
    files is SEP's split-adjusted series, which is correct for a RETURN and wrong for anything
    touching a STRIKE (`U1-SPLIT`). B2 and B3 both want returns, so adjusted is correct — and a
    RAW series would read a 2-for-1 split as a -50% month and flag exactly the names that rose.

    **NO PER-TICKER TAIL** (`B6`): the whole series is read and then resampled.
    """
    dest = os.path.join(fa(), cache_name)
    if os.path.exists(dest):
        return pd.read_pickle(dest)
    pdir = os.path.join(data_root(), "full2009", "backtest", "prices")
    if not os.path.isdir(pdir):
        pdir = os.path.join(data_root(), "backtest", "prices")
    cols = {}
    for i, tk in enumerate(sorted(set(names)), 1):
        p = os.path.join(pdir, "%s.csv" % str(tk).upper())
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_csv(p, usecols=["date", "close"]).dropna()
        except Exception:
            continue
        if df.empty:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").set_index("date")
        m = df["close"].resample("ME").last()
        if m.notna().sum() >= 12:
            cols[str(tk)] = m
        if i % 1000 == 0:
            print("    monthly closes %d/%d names" % (i, len(set(names))), flush=True)
    out = pd.DataFrame(cols).sort_index()
    out.to_pickle(dest)
    return out


# ============================================================================================
# K1 (B2) — the leverage census
# ============================================================================================
def k1_b2_leverage(tier, panel_frame, mc_monthly):
    """Is `B2` even the paper's strategy, or only the capped de-risking half of it?

    Measures the share of build-quadrant dates on which the **UNCAPPED** scaling
    `c / sigma^2_{t-1}` exceeds 1.0. Above 0.50 and the paper's effect is majority-carried by
    leverage a Roth cannot take, so the arm is recorded `NOT THE PAPER'S STRATEGY` and runs only
    as the overlay it actually is, with that label on every figure.

    `c` is set so **average exposure over the build quadrant is 1.0** — a normalisation declared
    in the register before any look, so the arm is not a disguised bet on holding less.

    **NO OUTCOME IS TOUCHED: this is a census of a scaling factor.**
    """
    # the book's own monthly return series: equal-weighted across the tier's names, which is the
    # variance the overlay would have scaled on. A book-weighted series would need the Index
    # engine's weights per date and would not change a census of a VARIANCE's magnitude.
    rets = mc_monthly.pct_change()
    dates = sorted(tier["date"].unique())
    sig2 = {}
    for d in dates:
        dd = pd.Timestamp(str(d)[:10])
        names = [t for t in tier[tier["date"] == d]["ticker"].astype(str).unique()
                 if t in rets.columns]
        if len(names) < MIN_NAMES_PER_DATE:
            continue
        win = rets.loc[(rets.index < dd), names].tail(3)   # the PRIOR rebalance window
        if win.shape[0] < 2:
            continue
        book = win.mean(axis=1).dropna()
        if len(book) < 2:
            continue
        v = float(np.var(book.values, ddof=1))
        if v > 0:
            sig2[str(d)[:10]] = v
    if not sig2:
        return verdict("B2", None, {"state": "NOT MEASURABLE",
                                    "why": "no date produced a prior-window variance"})
    inv = {d: 1.0 / v for d, v in sig2.items()}
    c = 1.0 / float(np.mean(list(inv.values())))           # average UNCAPPED exposure == 1.0
    scal = {d: c * iv for d, iv in inv.items()}
    over = [d for d, s in scal.items() if s > 1.0]
    share = len(over) / len(scal)
    passes = bool(share <= B2_LEVERAGE_SHARE)
    return verdict("B2", passes, {
        "kill": "K1 — the leverage census",
        "bar_share_above_1": B2_LEVERAGE_SHARE,
        "share_of_dates_uncapped_scaling_above_1": share,
        "dates": len(scal),
        "dates_above_1": len(over),
        "c_normalisation": c,
        "mean_uncapped_exposure": float(np.mean(list(scal.values()))),
        "median_uncapped_exposure": float(np.median(list(scal.values()))),
        "state": ("the capped overlay IS substantially the paper's strategy"
                  if passes else
                  "NOT THE PAPER'S STRATEGY — the effect is majority-carried by leverage a Roth "
                  "cannot take, so every figure carries that label"),
        "cap_is_a_declared_deviation": "the paper levers UP when volatility is low; this is a "
                                       "Roth with no margin, so exposure above 100pc is "
                                       "unavailable and an uncapped overlay would measure a "
                                       "strategy the account cannot run",
        "no_outcome_touched": True,
    })


# ============================================================================================
# K1 (B3) — residual momentum, BUILT INSIDE THE KILL PASS
# ============================================================================================
def b3_signal(frame, mc_monthly):
    """Blitz-Huij-Martens residual momentum: 36-month formation, most recent month skipped,
    residual of each name's monthly return on the panel's OWN value-weighted market return.

    **BUILT HERE, INSIDE THE KILL PASS, AND THAT IS THE FIX FOR BATCH 1's ORDERING BLOCKER.**
    `A2b` was NOT RUN because its costume bar *"cannot be evaluated before the SIGNAL exists"* —
    an ordering problem, not an outcome. Building a signal is a census of the panel's own inputs;
    no forward return is touched.

    **ONE FACTOR, DECLARED AS A DEVIATION FROM THE PAPER'S THREE, and the reason is licensing.**
    Ken French's library is *"free but permission-gated and factor-level — never a magnitude
    claim"* (`RUN_RULES` 0.2), so a signal depending on French factors could validate a build and
    could never ship in a product figure. **French is used NOWHERE here.**
    """
    rets = mc_monthly.pct_change()
    # the panel's OWN value-weighted market return, from the panel's own market caps
    capw = {}
    for d in sorted(frame["date"].unique()):
        g = frame[frame["date"] == d]
        capw[pd.Timestamp(str(d)[:10])] = dict(
            zip(g["ticker"].astype(str), pd.to_numeric(g["market_cap"], errors="coerce")))
    mkt = {}
    for ts in rets.index:
        # the most recent panel date at or before this month end
        prior = [k for k in capw if k <= ts]
        if not prior:
            continue
        w = capw[max(prior)]
        row = rets.loc[ts]
        names = [t for t in row.index if t in w and row[t] == row[t]
                 and (w[t] or 0) > 0]
        if len(names) < MIN_NAMES_PER_DATE:
            continue
        ws = np.array([w[t] for t in names], dtype=float)
        rs = np.array([row[t] for t in names], dtype=float)
        mkt[ts] = float((ws * rs).sum() / ws.sum())
    mkts = pd.Series(mkt).sort_index()

    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = pd.Timestamp(str(d)[:10])
        end = dd - pd.offsets.MonthEnd(B3_SKIP_MONTHS)
        start = end - pd.offsets.MonthEnd(B3_FORMATION_MONTHS)
        win = rets.loc[(rets.index > start) & (rets.index <= end)]
        mw = mkts.reindex(win.index)
        ok = mw.notna()
        if ok.sum() < 24:
            continue
        x = mw[ok].values.astype(float)
        X = np.column_stack([np.ones(len(x)), x])
        per = {}
        for t in win.columns:
            y = win.loc[ok.index[ok], t].values.astype(float)
            m = np.isfinite(y)
            if m.sum() < 24:
                continue
            try:
                beta, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
            except Exception:
                continue
            resid = y[m] - X[m] @ beta
            sd = float(np.std(resid, ddof=1))
            if sd <= 0:
                continue
            per[t] = float(resid.sum() / (sd * np.sqrt(len(resid))))   # t-scaled cumulative
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[str(d)[:10]] = per
    return sig


def attach_signal(frame, sig, col):
    f = frame.copy()
    key = f["date"].astype(str).str[:10]
    f[col] = [sig.get(k, {}).get(str(t)) for k, t in zip(key, f["ticker"].astype(str))]
    return f


def k1_b3_costume(frame_with_signal):
    r = costume_rho(frame_with_signal, "_b3", "momentum")
    if r is None:
        return verdict("B3", None, {"state": "NOT MEASURABLE",
                                    "why": "no date had 20+ names with both the signal and the "
                                           "momentum theme"})
    m = r["mean_abs_rho"]
    passes = bool(m < B3_COSTUME_BAR)
    return verdict("B3", passes, {
        "kill": "K1 — costume vs the shipped `momentum` theme",
        "bar": B3_COSTUME_BAR, **r,
        "read_residualised_on_momentum_alone": bool(m >= B3_MOMENTUM_ONLY_AT),
        "why_that_second_reading_is_fixed_now": "above 0.50 a pass is read residualised on "
                                                "`momentum` ALONE -- the reading that killed "
                                                "batch 1's A11 at 0.7596. Fixing it in advance "
                                                "is what stops a pass being chosen after seeing "
                                                "which reading clears.",
        "signal_built_inside_the_kill_pass": True,
        "french_used_nowhere": True,
    })


# ============================================================================================
# K1 (B4) — costume vs `size`
# ============================================================================================
def k1_b4_costume(frame_with_signal):
    r = costume_rho(frame_with_signal, "_b4", "size")
    if r is None:
        return verdict("B4-costume", None, {"state": "NOT MEASURABLE"})
    passes = bool(r["mean_abs_rho"] < B4_COSTUME_BAR)
    return verdict("B4-costume", passes, {
        "kill": "K1 — costume vs the `size` theme",
        "bar": B4_COSTUME_BAR, **r,
        "why_this_is_the_likeliest_IC_kill": "a neglect proxy is a size proxy until measured "
                                             "otherwise, and the record is unambiguous: E-1's "
                                             "graveyard aggregate died at 0.6114 against size, "
                                             "and R6's conviction signals read -0.815 to -0.854.",
    })


# ============================================================================================
# K1 (B5) — non-identity against the shipped signal
# ============================================================================================
def k1_b5_nonidentity(frame_with_signal):
    """`S16` measured that splitting net issuance into buyback and dilution legs is a RANK
    IDENTITY — within-date rank correlation `1.000000000000` on all 69 dates, because
    `max(0, -net)` and `-max(0, net)` are both non-increasing in `net`. Net payout yield is NOT
    that identity (it adds dividends and rescales by market cap) — **but the register must PROVE
    non-identity rather than assume it from the construction.**
    """
    against = "z_neg_issuance" if "z_neg_issuance" in frame_with_signal.columns \
        else "capital_discipline"
    r = costume_rho(frame_with_signal, "_b5", against)
    if r is None:
        return verdict("B5", None, {"state": "NOT MEASURABLE",
                                    "why": "no date had 20+ names with both columns"})
    passes = bool(r["mean_abs_rho"] < B5_NONIDENTITY_BAR)
    return verdict("B5", passes, {
        "kill": "K1 — non-identity vs the shipped issuance signal",
        "bar": B5_NONIDENTITY_BAR, "against": against, **r,
        "sign_convention": "net_payout = -(ncfdiv + ncfcommon) / marketcap; BOTH columns are "
                           "NEGATIVE for cash returned, verified on AAPL 2019-06-28 at -3.443bn "
                           "and -23.312bn. Backwards, it measures cash RAISED.",
        "state": ("not the shipped signal rescaled" if passes else
                  "IDENTITY — the arm is the shipped signal rescaled and carries no verdict"),
    })


def b5_signal(frame, hist):
    """`-(ncfdiv + ncfcommon) / marketcap` from the point-in-time row."""
    from scripts.tiered_pool import _pit_row
    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        g = frame[frame["date"] == d]
        per = {}
        for t, mc in zip(g["ticker"].astype(str),
                         pd.to_numeric(g["market_cap"], errors="coerce")):
            m = _num(mc)
            if m is None or m <= 0:
                continue
            row = _pit_row(hist.get(t) or [], dd)
            if not row:
                continue
            a, b = _num(row.get("ncfdiv")), _num(row.get("ncfcommon"))
            if a is None and b is None:
                continue
            per[t] = -((a or 0.0) + (b or 0.0)) / m
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    return sig


def b4_signal(frame):
    """`numest` scaled by firm size. NOT RUN unless `K0` clears, so this is only called then."""
    from valuation.edge import ibes_link as IL  # noqa: F401
    return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    f = fa()
    ppath = args.panel or os.path.join(f, PANEL)
    if not os.path.exists(ppath):
        raise SystemExit("REFUSING: no panel at %s" % ppath)
    panel = pd.read_pickle(ppath)
    quad, qcen = build_quadrant(panel)
    tier, tcen = tier_frame(quad)
    print("build quadrant %s | tier %s (%d names, min/date %d)"
          % (qcen["rows"], tcen["rows"], tcen["names"], tcen["names_per_date_min"]), flush=True)

    # PRE-SORTED HISTORY, VIA `TIERED-POOL`'s OWN HELPER (`B7`).
    #
    # A DEFECT OF MINE, CAUGHT BY DISBELIEVING A NUMBER. The first pass handed `_ttm`
    # `prov._indexed("fundamentals")`, which does NOT sort -- `fundamentals_pit` sorts for
    # itself, which is the tell. `_ttm`'s loop BREAKS at the first row whose datekey exceeds
    # `as_of`, and its docstring says "rows are pre-sorted by datekey", so on raw order it takes
    # a truncated arbitrary prefix and returns None for having fewer than four quarters. AAPL
    # and MSFT both failed at 2015-01-20 on 129 and 133 rows with four clean quarters inside a
    # 272-day span, which is what exposed it.
    #
    # The evaluable share read 0.4654 and the median failure share 0.7458 -- both artifacts, and
    # neither was reported. `tiered_pool_run._hist` is CALLED rather than re-implemented: a
    # second sort is a second chance to get the key wrong, and the key is `datekey or date`.
    from scripts.tiered_pool_run import _hist
    hist = _hist(os.path.join(data_root(), "full2009", "backtest"))

    kills = {}
    print("K0  B4 tier IBES census ...", flush=True)
    kills["B4_K0_tier_ibes"] = k0_tier_ibes(tier)

    print("K1  B1 junk inertness on the tier ...", flush=True)
    kills["B1_K1_inertness"] = k1_b1_inertness(tier, hist)

    print("monthly closes (built once, cached) ...", flush=True)
    mc = monthly_closes(sorted(quad["ticker"].astype(str).unique()))
    print("  monthly closes: %s" % (mc.shape,), flush=True)

    print("K1  B2 leverage census ...", flush=True)
    kills["B2_K1_leverage"] = k1_b2_leverage(tier, quad, mc)

    print("K1  B3 residual momentum, signal built inside the kill pass ...", flush=True)
    s3 = b3_signal(quad, mc)
    q3 = attach_signal(quad, s3, "_b3")
    kills["B3_K1_costume"] = k1_b3_costume(q3)

    print("K1  B5 net payout non-identity ...", flush=True)
    s5 = b5_signal(quad, hist)
    q5 = attach_signal(quad, s5, "_b5")
    kills["B5_K1_nonidentity"] = k1_b5_nonidentity(q5)

    res = {
        "item": "STAGE1-BATCH2 — the free pre-outcome kills",
        "register": REGISTER,
        "panel": os.path.basename(ppath),
        "trials": 0,
        "trial_class": "PRE-OUTCOME CONTROLS — can only BLOCK (MB1-SEL). No forward return is "
                       "touched anywhere in this file, pinned by test.",
        "build_quadrant": qcen,
        "tier": tcen,
        "bars_are_the_registers": {
            "K0_IBES_FLOOR": K0_IBES_FLOOR, "B1_INERT_MEDIAN": B1_INERT_MEDIAN,
            "B2_LEVERAGE_SHARE": B2_LEVERAGE_SHARE, "B3_COSTUME_BAR": B3_COSTUME_BAR,
            "B3_MOMENTUM_ONLY_AT": B3_MOMENTUM_ONLY_AT, "B4_COSTUME_BAR": B4_COSTUME_BAR,
            "B5_NONIDENTITY_BAR": B5_NONIDENTITY_BAR,
            "CONTRACT_MIN_POSITIONS": CONTRACT_MIN_POSITIONS,
        },
        "B6": "WITHDRAWN on the draft's own instruction (register 0.1); k STAYS 6",
        "kills": kills,
        "k_stays": 6,
    }
    dest = args.out or os.path.join(f, OUT)
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)
    print("\n=== KILL PASS", flush=True)
    for k, v in kills.items():
        print("  %-26s kill_passes=%s  %s"
              % (k, v.get("kill_passes"),
                 str((v.get("detail") or {}).get("state", ""))[:90]), flush=True)
    print("\nwrote %s" % dest, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
