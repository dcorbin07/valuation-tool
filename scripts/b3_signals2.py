# -*- coding: utf-8 -*-
"""`STAGE1-BATCH3` — the four remaining arms: C1, C2, C4 and C8.

Same rules as `b3_signals`: no forward return is read, no bar is compared, nothing is sorted.

**C8 IS THE ONLY ARM THAT FITS ANYTHING, AND ITS STRICTNESS IS A PRE-COMMITTED KILL rather than
a judgement** (register amendment 0.3). The draft said *"drop it rather than fit it loosely"*,
and a judgement made after seeing whether the loose version looks good is not a judgement. So
every coefficient scoring date `d` is estimated on rows strictly BEFORE `d`, the training window
end is recorded per date so the property is checkable from the OUTPUT and not only from the code,
and `fit_is_strict()` returns the violations rather than asserting — a helper that reports its own
failure by raising turns every caller into a crash.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.tiered_pool import _num, _pit_row                              # noqa: E402
from scripts.b3_signals import (MIN_NAMES_PER_DATE, _rows_before, _scaled_delta,  # noqa: E402
                                _ttm_sum, _yoy_row, capex_outflow)


# =============================================================================================
# C1 — ABARBANELL-BUSHEE, SIX SIGNALS. Labelled SIX on every figure: employee counts, audit
# opinions and LIFO/FIFO elections are not in Sharadar at any dimension, so three of the nine
# are structurally unavailable rather than dropped by choice.
# =============================================================================================
C1_LEGS = ("d_inventory_vs_sales", "d_receivables_vs_sales", "d_gross_margin",
           "d_sgna_vs_sales", "d_capex", "d_tax_rate")


def c1_abarbanell_bushee(frame, hist, leg_sink=None):
    """Six year-over-year changes, each signed so 'good' is high, equally weighted.

    Signs, each from the paper's own direction:
      * inventory growing FASTER than sales is bad          -> negated
      * receivables growing faster than sales is bad        -> negated
      * gross margin improving is good                      -> as is
      * SG&A growing faster than sales is bad               -> negated
      * capital expenditure growing is good (investment)    -> as is
      * the effective tax rate RISING is bad                -> negated

    **A NAME NEEDS ALL SIX OR IT IS NOT SCORED.** Averaging whatever legs happen to exist is the
    `W-28` defect exactly: `df[cols].mean(axis=1)` skips NaN, so a row with four legs is a
    DIFFERENT signal wearing the six-leg signal's name, and the difference correlates with
    reporting completeness rather than with anything economic.
    """
    present = {k: 0 for k in C1_LEGS}
    sig = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        per = {}
        for t in frame.loc[frame["date"] == d, "ticker"].astype(str):
            rows = hist.get(t) or []
            now, then = _yoy_row(rows, dd, back=4)
            if not now or not then:
                continue
            s_now = _ttm_sum(rows, dd, ("revenue", "sgna", "capex", "taxexp", "ebt"))
            if not s_now:
                continue
            legs = {}

            rev_n, rev_t = s_now.get("revenue"), _num(then.get("revenue"))
            d_sales = _scaled_delta(rev_n, rev_t)

            inv = _scaled_delta(_num(now.get("inventory")), _num(then.get("inventory")))
            if inv is not None and d_sales is not None:
                legs["d_inventory_vs_sales"] = -(inv - d_sales)

            rec = _scaled_delta(_num(now.get("receivables")), _num(then.get("receivables")))
            if rec is not None and d_sales is not None:
                legs["d_receivables_vs_sales"] = -(rec - d_sales)

            gm = _scaled_delta(_num(now.get("grossmargin")), _num(then.get("grossmargin")))
            if gm is not None:
                legs["d_gross_margin"] = gm

            sg = _scaled_delta(s_now.get("sgna"), _num(then.get("sgna")))
            if sg is not None and d_sales is not None:
                legs["d_sgna_vs_sales"] = -(sg - d_sales)

            cx = _scaled_delta(capex_outflow(now), capex_outflow(then))
            if cx is not None:
                legs["d_capex"] = cx

            def _rate(r):
                te, eb = _num(r.get("taxexp")), _num(r.get("ebt"))
                if te is None or eb is None or eb == 0:
                    return None
                return te / eb

            tr = _scaled_delta(_rate(now), _rate(then))
            if tr is not None:
                legs["d_tax_rate"] = -tr

            for k in legs:
                present[k] += 1
            if len(legs) == len(C1_LEGS):
                per[t] = sum(legs.values()) / float(len(C1_LEGS))
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    if leg_sink is not None:
        leg_sink.update(present)
    return sig


# =============================================================================================
# C2 — MOHANRAM G-SCORE, SEVEN SIGNALS. Labelled SEVEN: Sharadar carries no advertising expense
# at any dimension, so the eighth is structurally unavailable.
# =============================================================================================
C2_LEGS = ("roa", "cfo_assets", "cfo_gt_roa", "roa_stability", "sales_stability",
           "rnd_intensity", "capex_intensity")
C2_VAR_QUARTERS = 20


def c2_g_score(frame, hist):
    """Seven binaries, each scored against the DATE's own cross-section median.

    Mohanram scores against the industry median; this scores against the date's cross-section,
    which is the same choice `f_score` already ships with on this panel. Stated because it is a
    deviation from the paper rather than a detail: an industry median needs a point-in-time
    sector map, and `S25`/`A10` measured that route's coverage at 0.3713 — below any usable
    floor, which is why no arm in this project conditions on sector.

    `capex_intensity` uses `capex_outflow` (amendment 0.2) and NOT `abs(capex)`.
    """
    raw = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        per = {}
        for t in frame.loc[frame["date"] == d, "ticker"].astype(str):
            rows = hist.get(t) or []
            row = _pit_row(rows, dd)
            if not row:
                continue
            a = _num(row.get("assets"))
            if a is None or a <= 0:
                continue
            s = _ttm_sum(rows, dd, ("netinc", "ncfo", "rnd", "capex", "revenue"))
            if not s:
                continue
            ni, cfo = s.get("netinc"), s.get("ncfo")
            if ni is None or cfo is None:
                continue
            pre = _rows_before(rows, dd)
            if len(pre) < C2_VAR_QUARTERS:
                continue
            roas, sales = [], []
            for r in pre[-C2_VAR_QUARTERS:]:
                n_, a_ = _num(r.get("netinc")), _num(r.get("assets"))
                rv = _num(r.get("revenue"))
                if n_ is None or a_ is None or a_ <= 0 or rv is None:
                    roas = []
                    break
                roas.append(n_ / a_)
                sales.append(rv)
            if len(roas) < C2_VAR_QUARTERS:
                continue

            def _sd(xs):
                m = sum(xs) / len(xs)
                return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

            cx = capex_outflow(row)
            per[t] = {
                "roa": ni / a,
                "cfo_assets": cfo / a,
                "cfo_gt_roa": 1.0 if cfo > ni else 0.0,
                "roa_stability": -_sd(roas),
                "sales_stability": -_sd(sales) / (abs(sum(sales) / len(sales)) or 1.0),
                "rnd_intensity": ((s.get("rnd") or 0.0) / a),
                "capex_intensity": ((cx or 0.0) / a),
            }
        if len(per) >= MIN_NAMES_PER_DATE:
            raw[dd] = per

    # the binaries: 1 where above the date's median, except `cfo_gt_roa` which is already binary
    sig = {}
    for dd, per in raw.items():
        out = {}
        meds = {}
        for leg in C2_LEGS:
            if leg == "cfo_gt_roa":
                continue
            vals = sorted(v[leg] for v in per.values())
            meds[leg] = vals[len(vals) // 2]
        for t, v in per.items():
            score = 0
            for leg in C2_LEGS:
                if leg == "cfo_gt_roa":
                    score += int(v[leg])
                else:
                    score += int(v[leg] > meds[leg])
            out[t] = float(score)
        sig[dd] = out
    return sig


# =============================================================================================
# C4 — COMPOSITE EQUITY ISSUANCE (Daniel-Titman 2006).
# =============================================================================================
import math  # noqa: E402  (used only below)

C4_YEARS = 5


def _asof(dates, values, when):
    """The last value at or before `when`, by binary search. None if there is none.

    Bisect rather than a dict: 3,545 tickers x ~7,200 closes is ~25M entries, and two parallel
    lists plus a search is memory-light where a dict per ticker is not.
    """
    import bisect
    i = bisect.bisect_right(dates, when)
    return values[i - 1] if i else None


def c4_composite_issuance(frame, prov, cov_sink=None):
    """`-[log(mcap_t / mcap_{t-5y}) - log(total return over the same window)]`.

    **BOTH LEGS COME FROM THE PROVIDER, NOT FROM THE PANEL FRAME, AND THAT IS A REPAIR OF MY OWN
    FIRST IMPLEMENTATION RATHER THAN A CHANGE OF DESIGN.** The first version read `market_cap` and
    the return history out of the panel. The corrected panel's grid starts **2009-03-27**, so for
    the 24 early-half dates of the build quadrant no five-year base existed IN THE FRAME whatever
    the data said, and C4's coverage kill fired at **0.6094**. From the untruncated sources it is
    **0.9239** (`B3_C4_SOURCE.json`; per-date min 0.8879, median 0.9370) -- so the first reading
    was a frame artefact, the same class as this lane's own `_ttm` unsorted-history defect, where
    twelve failing dates turned out to be entirely artefactual.

    **WHY IT IS THE SAME QUANTITY FROM THE SAME SOURCE, which is what makes it a repair.** The
    panel's own `market_cap` is built from the DAILY bulk cache (`cleanups.
    pit_market_cap_from_daily`), whose month-end series starts **1998-12-31**; and the panel's
    returns are TOTAL return because its `close` IS `closeadj` -- the same series
    `price_history(days=None)` returns, back to **1997-12-31**. The panel's start date is a
    property of the panel, not of the arm. **The 0.70 floor did not move** (`W-28`), and the
    panel-sourced 0.6094 stays on the record beside this.

    Both legs use ONE as-of rule -- the last observation at or before the date -- so the ratio is
    internally consistent rather than mixing a rebalance-date value with a month-end one.

    **SIGNED NEGATIVE so LOW issuance is HIGH (good)**, matching the shipped `neg_issuance`
    convention: with opposite signs the kill's rank correlation would come out near -1 and read as
    "not the same column" when it is the same column inverted.
    """
    counts = {"scored": 0, "no_five_year_mcap": 0, "no_five_year_price": 0}

    f = frame[["date", "ticker"]].copy()
    f["date"] = f["date"].astype(str).str[:10]
    tickers = sorted(set(f["ticker"].astype(str)))

    mcd, mcv, pxd, pxv = {}, {}, {}, {}
    for t in tickers:
        rows = [(str(r[0])[:10], float(r[1])) for r in (prov.daily_history(t) or [])
                if r and r[1] is not None and float(r[1]) > 0]
        mcd[t] = [r[0] for r in rows]
        mcv[t] = [r[1] for r in rows]
        d, c = prov.price_history(t, days=None)
        if d is None or c is None:
            pxd[t], pxv[t] = [], []
            continue
        pairs = [(str(x)[:10], float(y)) for x, y in zip(d, c)
                 if y is not None and y == y and float(y) > 0]
        pxd[t] = [p[0] for p in pairs]
        pxv[t] = [p[1] for p in pairs]

    sig = {}
    for dd in sorted(f["date"].unique()):
        base = "%04d%s" % (int(dd[:4]) - C4_YEARS, dd[4:])
        per = {}
        for t in f.loc[f["date"] == dd, "ticker"].astype(str):
            now = _asof(mcd.get(t) or [], mcv.get(t) or [], dd)
            then = _asof(mcd.get(t) or [], mcv.get(t) or [], base)
            if now is None or then is None:
                counts["no_five_year_mcap"] += 1
                continue
            p_now = _asof(pxd.get(t) or [], pxv.get(t) or [], dd)
            p_then = _asof(pxd.get(t) or [], pxv.get(t) or [], base)
            if p_now is None or p_then is None:
                counts["no_five_year_price"] += 1
                continue
            per[t] = -(math.log(now / then) - math.log(p_now / p_then))
            counts["scored"] += 1
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
    if cov_sink is not None:
        cov_sink.update(counts)
    return sig


# =============================================================================================
# C8 — EXPECTED INVESTMENT GROWTH, with the strict expanding-window fit.
# =============================================================================================
C8_PREDICTORS = ("tobins_q", "cfo_assets", "d_roe")


def c8_predictors(frame, hist):
    """The three point-in-time predictors, plus the realised next-year investment growth that
    the fit is trained ON (never used at the date it is scored for)."""
    out = {}
    for d in sorted(frame["date"].unique()):
        dd = str(d)[:10]
        g = frame[frame["date"] == d]
        per = {}
        for t, mc in zip(g["ticker"].astype(str), g["market_cap"]):
            m = _num(mc)
            rows = hist.get(t) or []
            row = _pit_row(rows, dd)
            if m is None or m <= 0 or not row:
                continue
            a = _num(row.get("assets"))
            if a is None or a <= 0:
                continue
            debt = _num(row.get("debt")) or 0.0
            s = _ttm_sum(rows, dd, ("ncfo",))
            if not s or s.get("ncfo") is None:
                continue
            now, then = _yoy_row(rows, dd, back=4)
            if not now or not then:
                continue

            def _roe(r):
                ni, eq = _num(r.get("netinc")), _num(r.get("equity"))
                if ni is None or eq is None or eq <= 0:
                    return None
                return ni / eq

            dr = _scaled_delta(_roe(now), _roe(then))
            if dr is None:
                continue
            # realised investment growth: year-over-year growth in the capex OUTFLOW
            inv_now, inv_then = capex_outflow(now), capex_outflow(then)
            gi = _scaled_delta(inv_now, inv_then)
            per[t] = {"tobins_q": (m + debt) / a, "cfo_assets": s["ncfo"] / a,
                      "d_roe": dr, "realised_inv_growth": gi}
        if len(per) >= MIN_NAMES_PER_DATE:
            out[dd] = per
    return out


def c8_expected_investment_growth(pred, audit_sink=None):
    """Fit next-year investment growth on the three predictors, EXPANDING WINDOW.

    For each scoring date `d` the coefficients come from every (date, name) observation whose
    date is **strictly before** `d`. The signal is the fitted value at `d`.

    **THE AUDIT TRAIL IS THE POINT.** Per date it records the training window's last date and
    the scored date, so `fit_is_strict` can check the property from the OUTPUT. A test that only
    reads the code cannot tell a strict fit from a loose one that happens to look right.
    """
    import numpy as np

    dates = sorted(pred.keys())

    #: THE TARGET IS *NEXT-YEAR* INVESTMENT GROWTH, AND MY FIRST CUT GOT THIS WRONG.
    #: It paired the predictors at `td` with the growth measured AT `td`, which fits
    #: contemporaneous growth on contemporaneous predictors -- a different model from the
    #: paper's, and one whose fitted value is not an EXPECTATION of anything. The pair is
    #: (x at `td`, y at `td_plus`), where `td_plus` is about four quarters later so that
    #: `realised_inv_growth` there covers the year FOLLOWING `td`.
    #:
    #: AND THE TARGET DATE MUST ALSO FALL STRICTLY BEFORE THE SCORED DATE. Requiring only
    #: `td < d` would let a training pair whose OUTCOME is dated at or after `d` into the fit --
    #: the predictors would be in-sample and the label would be from the future. That is exactly
    #: the leak amendment 0.3's kill exists for, and it is invisible to a check that only looks
    #: at where the predictors came from.
    def _plus_one_year(td):
        want = "%04d%s" % (int(td[:4]) + 1, td[4:])
        later = [d2 for d2 in dates if d2 >= want]
        return later[0] if later else None

    pairs = {}                                  # td -> (td_plus, rows)
    for td in dates:
        tp = _plus_one_year(td)
        if tp is None:
            continue
        rows = []
        for t, v in pred[td].items():
            y = (pred.get(tp) or {}).get(t, {}).get("realised_inv_growth")
            if y is None:
                continue
            xs = [v.get(k) for k in C8_PREDICTORS]
            if any(x is None for x in xs):
                continue
            rows.append(xs + [y])
        pairs[td] = (tp, rows)

    audit, sig = [], {}
    for i, dd in enumerate(dates):
        rows, train_end = [], None
        for td in dates[:i]:
            tp, rr = pairs.get(td, (None, []))
            if tp is None or tp >= dd:          # the LABEL would be at or after the scored date
                continue
            rows.extend(rr)
            train_end = tp if train_end is None else max(train_end, tp)
        train_dates = [train_end] if train_end else []
        if len(rows) < 200:                      # too little history to fit at all
            audit.append({"scored_date": dd, "train_end": (train_dates[-1] if train_dates
                                                           else None),
                          "n_train": len(rows), "fitted": False})
            continue
        M = np.asarray(rows, dtype=float)
        X = np.column_stack([np.ones(len(M)), M[:, :len(C8_PREDICTORS)]])
        beta, *_ = np.linalg.lstsq(X, M[:, -1], rcond=None)
        per = {}
        for t, v in pred[dd].items():
            xs = [v.get(k) for k in C8_PREDICTORS]
            if any(x is None for x in xs):
                continue
            per[t] = float(beta[0] + sum(b * x for b, x in zip(beta[1:], xs)))
        if len(per) >= MIN_NAMES_PER_DATE:
            sig[dd] = per
        audit.append({"scored_date": dd, "train_end": train_dates[-1],
                      "n_train": len(rows), "fitted": True})
    if audit_sink is not None:
        audit_sink.extend(audit)
    return sig


def fit_is_strict(audit):
    """RETURNS THE VIOLATIONS rather than asserting. A helper that reports its own failure by
    raising makes every caller a crash where the data is thin, which is the 'fails open in CI'
    family one level down.

    A violation is any fitted date whose training window reaches the scored date or beyond.
    """
    bad = []
    for a in audit:
        if not a.get("fitted"):
            continue
        te, sd = a.get("train_end"), a.get("scored_date")
        if te is None or sd is None or te >= sd:
            bad.append(a)
    return bad
