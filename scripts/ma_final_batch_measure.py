"""Premise measurements for audit #3's final MA batch — MA24, MA26, MA27, MA33, MA55, MA57, MA58.

**ZERO TRIALS.** Every number here is a fact about what data exists, what a shipped function
computes, or arithmetic on an already-published artifact. No hypothesis is registered, no
threshold is pre-committed and no verdict is issued against a bar. `S25`'s precedent (closing a
row on a fact about what data exists) and session 8's (declining a test that cannot resolve).

Run:  python -m scripts.ma_final_batch_measure
Out:  data/free_analysis/MA_FINAL_BATCH.json

The five questions, and why each is answerable without a trial:

  MA24/MA33  Does a MONTHLY theme panel clear `S19`'s own pre-committed kill condition?
             MA24 fixed the condition in writing: *"if the monthly panel's own MDE still exceeds
             +0.0096 ... close permanently."* The MDE is `2 x SE` and `SE = IC / t`, both of
             which the shipped `S19_MDNA.json` carries, so the quarterly MDE is DERIVED from the
             artifact rather than quoted from prose. Rescaling it to a monthly date count is
             arithmetic on a published number, not a new measurement.

  MA26-C     Is the WITHHOLDING state computable point-in-time? The audit says no. The trigger
             is `fair_value / price > FV_BAND_HIGH` and nothing else, and `S23`'s banked
             valuation panel carries both columns on the corrected 69-date window. Computing a
             base rate from two banked columns tests no hypothesis.

  MA27       Does `per_signal` really carry 53 signals? A count.

  MA55       Is the lens-disagreement width buildable from the banked panel? A coverage measure.

  MA57       Are `ownername` and `transactioncode` on disk, and is Cohen-Malloy-Pomorski's
             routine/opportunistic split buildable? The audit says the columns need a re-export
             "while the Sharadar entitlement is live". Reading the header of a file settles it.

  MA58       Has any cross-sectional return-seasonality signal been registered? A census.

The insiders leg is slow (5.6M rows, ~580MB) and is skipped unless --insiders is passed.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

OUT = os.path.join(REPO, "data", "free_analysis", "MA_FINAL_BATCH.json")

# The MD&A corpus starts here and the corrected panel ends here. Both are measured facts from
# the S19 write-up and the panel window, not choices made for this script.
MDNA_FIRST_MONTH = "2016-08"
PANEL_LAST_MONTH = "2026-01"


# --------------------------------------------------------------------------------------
# MA24 + MA33 — S19's kill condition on a monthly panel
# --------------------------------------------------------------------------------------
def s19_kill_condition(data_dir: str) -> dict:
    """Derive S19's MDE from its own artifact, then rescale it to a monthly date count.

    WHY DERIVED RATHER THAN QUOTED: `CLAUDE.md` states the MDE as +0.020549, and the artifact
    does not store it under any key. It IS recoverable — `SE = IC / t` and `MDE(|t|=2) = 2 SE` —
    so the check is that the record's number reproduces from the shipped numbers. If it did not,
    the whole kill-condition argument would be resting on prose.

    THE SCALING IS THE CONSERVATIVE DIRECTION. `SE` falls as `1/sqrt(T)` for a mean over `T`
    dates ONLY if the dates are independent. Monthly 63-day forward returns OVERLAP, and R9
    measured lag-1 autocorrelation +0.189 on this project's own quarterly spread, so the true
    monthly SE is LARGER than this and the true MDE is WORSE. A conclusion of "still
    underpowered" therefore holds a fortiori.
    """
    p = os.path.join(data_dir, "free_analysis", "S19_MDNA.json")
    if not os.path.exists(p):
        return {"available": False, "reason": f"{p} not on disk"}
    with io.open(p, "r", encoding="utf-8") as f:
        d = json.load(f)

    target = float(d["controls"]["C6_reproduces_original"]["target_residual_ic"])
    arms = {}
    for a in ("A1", "A2"):
        f_ = d["arms"][a]["full_sample"]
        ic = float(f_["residual_ic_change"])
        t = float(f_["residual_ic_t_change"])
        T_q = int(f_["n_dates"])
        se = ic / t
        arms[a] = {"n_dates_quarterly": T_q, "observed_residual_ic": ic, "t": t,
                   "se": se, "mde_at_t2_quarterly": 2.0 * se}

    # months from the first MD&A month to the panel's last date, inclusive
    fy, fm = (int(x) for x in MDNA_FIRST_MONTH.split("-"))
    ly, lm = (int(x) for x in PANEL_LAST_MONTH.split("-"))
    T_m = (ly - fy) * 12 + (lm - fm) + 1

    for a, v in arms.items():
        mde_m = v["mde_at_t2_quarterly"] * math.sqrt(v["n_dates_quarterly"] / T_m)
        v["n_dates_monthly"] = T_m
        v["mde_at_t2_monthly"] = mde_m
        v["still_above_original_effect"] = bool(mde_m > target)
        # months needed for the MDE to fall TO the original effect
        v["months_needed_to_detect"] = v["n_dates_quarterly"] * (
            v["mde_at_t2_quarterly"] / target) ** 2

    return {
        "available": True,
        "original_effect_residual_ic": target,
        "mdna_window": [MDNA_FIRST_MONTH, PANEL_LAST_MONTH],
        "arms": arms,
        "kill_condition": (
            "MA24: 'if the monthly panel's own MDE still exceeds +0.0096 on the 418+195 name "
            "corpus, the question is unanswerable on data we own and should be closed "
            "permanently rather than re-opened a third time.'"),
        "kill_condition_fires": all(v["still_above_original_effect"] for v in arms.values()),
    }


# --------------------------------------------------------------------------------------
# MA26-C — the withholding state, point-in-time
# --------------------------------------------------------------------------------------
def withhold_pit(data_dir: str) -> dict:
    """Is 'the model refused to value this name' a computable historical state?

    The audit's arm C says NO and calls naming that blocker the deliverable. The trigger is a
    pure function of two columns (`withhold.withhold_implausible_fair_values`), and S23's banked
    panel carries both point-in-time, so it is computable and this measures the base rate.
    """
    p = os.path.join(data_dir, "free_analysis", "panel_s23_fairvalue.pkl")
    if not os.path.exists(p):
        return {"available": False, "reason": f"{p} not on disk"}
    import pandas as pd
    from valuation.engine.pipeline import FV_BAND_HIGH   # the ONE definition, imported

    d = pd.read_pickle(p)
    fv = pd.to_numeric(d["fair_value"], errors="coerce")
    px = pd.to_numeric(d["price"], errors="coerce")
    ok = fv.notna() & px.notna() & (px > 0)
    ratio = fv[ok] / px[ok]
    w = ratio > float(FV_BAND_HIGH)
    per_date = d.loc[ok].assign(_w=w.values).groupby("date")["_w"].mean()
    return {
        "available": True,
        "band": float(FV_BAND_HIGH),
        "panel_rows": int(len(d)),
        "rows_with_fv_and_price": int(ok.sum()),
        "dates": int(d["date"].nunique()),
        "names": int(d["ticker"].nunique()),
        "span": [str(d["date"].min())[:10], str(d["date"].max())[:10]],
        "withheld_rows": int(w.sum()),
        "withheld_share": float(w.mean()),
        "per_date_share": {"min": float(per_date.min()), "median": float(per_date.median()),
                           "max": float(per_date.max()),
                           "dates_with_any": int((per_date > 0).sum()),
                           "dates": int(len(per_date))},
    }


# --------------------------------------------------------------------------------------
# MA55 — lens-disagreement width
# --------------------------------------------------------------------------------------
LENSES = ["dcf_ps", "comps_fv", "growth_ps"]


def lens_width(data_dir: str) -> dict:
    p = os.path.join(data_dir, "free_analysis", "panel_s23_fairvalue.pkl")
    if not os.path.exists(p):
        return {"available": False, "reason": f"{p} not on disk"}
    import pandas as pd
    d = pd.read_pickle(p)
    M = d[LENSES].apply(pd.to_numeric, errors="coerce")
    n_lens = M.notna().sum(axis=1)
    fv = pd.to_numeric(d["fair_value"], errors="coerce")
    ok = (n_lens >= 2) & fv.notna() & (fv > 0)
    w = (M.max(axis=1) - M.min(axis=1))[ok] / fv[ok]
    return {
        "available": True,
        "lens_columns": LENSES,
        "coverage": {c: float(M[c].notna().mean()) for c in LENSES},
        "rows_with_ge2_lenses": int((n_lens >= 2).sum()),
        "rows_with_3_lenses": int((n_lens == 3).sum()),
        "width_n": int(ok.sum()),
        "width_p05": float(w.quantile(0.05)), "width_median": float(w.median()),
        "width_p95": float(w.quantile(0.95)), "width_max": float(w.max()),
        "width_zero_rows": int((w == 0).sum()),
    }


# --------------------------------------------------------------------------------------
# MA27 / MA58 — signal census
# --------------------------------------------------------------------------------------
def signal_census() -> dict:
    from valuation.screener import settings as S
    import re
    seasonal = [k for k in S.NUMBER_THEME if re.search(r"seas|_month|calendar", k, re.I)]
    return {"number_theme_entries": len(S.NUMBER_THEME),
            "seasonality_shaped_keys": sorted(seasonal)}


# --------------------------------------------------------------------------------------
# MA57 — is the CMP split buildable from data on disk?
# --------------------------------------------------------------------------------------
def insiders(data_dir: str) -> dict:
    """Read the insiders export header, then classify (insider, ticker) pairs by CMP's rule.

    CMP 2012 define a ROUTINE trader as one who placed a trade in the SAME CALENDAR MONTH in
    each of three consecutive prior years; everyone else is OPPORTUNISTIC, and only the
    opportunistic trades predict. The rule is applied to the insider's whole trading record, so
    it is measured here on ALL coded rows as well as on purchases-and-sales alone.
    """
    p = os.path.join(data_dir, "backtest", "insiders.csv")
    if not os.path.exists(p):
        return {"available": False, "reason": f"{p} not on disk"}
    import pandas as pd

    with io.open(p, "r", encoding="utf-8", errors="replace") as f:
        header = f.readline().strip().split(",")

    need = ["ticker", "ownername", "transactioncode", "transactiondate",
            "transactionshares", "transactionpricepershare", "transactionvalue"]
    missing = [c for c in need if c not in header]
    if missing:
        return {"available": True, "columns": header, "missing": missing}

    pair_ps, pair_any = defaultdict(set), defaultdict(set)
    n_rows = owners = 0
    owner_set = set()
    reach_priced = reach_fallback = fb_sale_as_buy = skipped = 0
    blank_code = code_P = shares_neg = value_neg = 0

    for chunk in pd.read_csv(p, chunksize=400_000, usecols=need, low_memory=False):
        n_rows += len(chunk)
        code = chunk["transactioncode"].astype(str).str.upper().str.strip()
        td = pd.to_datetime(chunk["transactiondate"], errors="coerce")
        sh = pd.to_numeric(chunk["transactionshares"], errors="coerce")
        pr = pd.to_numeric(chunk["transactionpricepershare"], errors="coerce")
        va = pd.to_numeric(chunk["transactionvalue"], errors="coerce")
        owner_set.update(chunk["ownername"].astype(str).unique().tolist())
        # A blank code cannot be classified routine OR opportunistic -- the register's first
        # coverage control, so it is counted rather than assumed small.
        #
        # COUNTED ON THE RAW COLUMN, NOT THE NORMALISED ONE, AND THAT IS THE WHOLE POINT.
        # Under pandas' string dtype a missing cell is `pd.NA`; `astype(str)` leaves it NA
        # rather than producing "nan", and NA compares False against EVERY literal -- so
        # `code.eq("") | code.eq("NAN")` returned **0** on 1.5M genuinely blank rows. A guard
        # that reports zero because it could not see the value is the vacuous-pass defect in a
        # new costume, and it was caught only by disbelieving the zero.
        blank_code += int(chunk["transactioncode"].isna().sum())
        code_P += int(code.eq("P").sum())
        shares_neg += int((sh < 0).sum())
        value_neg += int((va < 0).sum())

        # the shipped scorer's own branch, counted rather than assumed
        priced = sh.notna() & pr.notna()
        fallback = (~priced) & va.notna()
        reach_priced += int(priced.sum())
        reach_fallback += int(fallback.sum())
        fb_sale_as_buy += int((fallback & (sh < 0)).sum())
        skipped += int(((~priced) & va.isna()).sum())

        for mask, store in ((code.isin(["P", "S"]), pair_ps),
                            (code.ne("") & code.ne("NAN"), pair_any)):
            sub = chunk[mask & td.notna()]
            if not len(sub):
                continue
            s_td = pd.to_datetime(sub["transactiondate"], errors="coerce")
            for o, t, y, m in zip(sub["ownername"].astype(str), sub["ticker"].astype(str),
                                  s_td.dt.year, s_td.dt.month):
                store[(o, t)].add((int(y), int(m)))
    owners = len(owner_set)

    def cmp_split(store):
        hit = 0
        for months in store.values():
            by_month = defaultdict(set)
            for (y, m) in months:
                by_month[m].add(y)
            found = False
            for _m, ys in by_month.items():
                for y in ys:
                    if all((y - dd) in ys for dd in (1, 2, 3)):
                        found = True
                        break
                if found:
                    break
            hit += 1 if found else 0
        n = len(store)
        return {"pairs": n, "routine_pairs": hit,
                "routine_share": (hit / n) if n else None}

    return {
        "available": True,
        "n_columns": len(header),
        "ownername_present": True,
        "transactioncode_present": True,
        "n_rows": n_rows,
        "distinct_ownername": owners,
        "blank_transactioncode": blank_code,
        "blank_transactioncode_share": blank_code / n_rows if n_rows else None,
        "code_P_rows": code_P,
        "cmp_on_purchases_and_sales": cmp_split(pair_ps),
        "cmp_on_all_coded_rows": cmp_split(pair_any),
        "signedness": {"transactionshares_negative": shares_neg,
                       "transactionvalue_negative": value_neg},
        "shipped_scorer_branches": {
            "signed_price_path": reach_priced,
            "unsigned_transactionvalue_fallback": reach_fallback,
            "fallback_rows_that_are_sales_scored_as_buys": fb_sale_as_buy,
            "silently_skipped_no_price_no_value": skipped,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(REPO), "data"))
    ap.add_argument("--insiders", action="store_true",
                    help="also scan the 580MB insiders export (slow)")
    a = ap.parse_args()

    dd = a.data_dir
    if not os.path.isdir(dd):
        alt = os.path.join(REPO, "data")
        dd = alt if os.path.isdir(alt) else dd

    out = {
        "zero_trials": True,
        "data_dir": dd,
        "ma24_ma33_s19_kill_condition": s19_kill_condition(dd),
        "ma26c_withhold_point_in_time": withhold_pit(dd),
        "ma27_ma58_signal_census": signal_census(),
        "ma55_lens_width": lens_width(dd),
    }
    if a.insiders:
        out["ma57_insiders"] = insiders(dd)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2)[:4000])
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
