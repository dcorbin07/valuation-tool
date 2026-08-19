"""DEEPITM-FIN — is a 60-90 DTE, delta 0.85-0.95 call cheaper than margin?

Executes PREREG_v5reread_deepitm_financing.md section 2. A COST comparison, not an alpha claim.
Adopts nothing, recommends nothing, changes no live code path.

    python -m scripts.deepitm_financing --controls-only
    python -m scripts.deepitm_financing --arms

TWO-PASS BY DESIGN (the O19 / session-26 repair): the gating controls are computed AND WRITTEN in
their own pass, and --arms REFUSES to run without a passing controls artifact. A gating control
that runs in the same pass as the outcomes it gates is not a gate.

SOURCES, per the register:
  chains  data/options_freeze/R2_CORRECTED_2026-08-08/chains.pkl.gz   (NOT the mutable store)
  spot    data/bulk/prepared/bars/<SYM>.pkl -> raw_close  (AS-TRADED; never `close`)
  rf      blackscholes.risk_free_rate                     (imported, never re-typed)
  divs    data/bulk/prepared/actions.pkl -> [(date, amount)]
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import pickle
import sys
from typing import Optional

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from valuation.edge import blackscholes as BS            # noqa: E402
from valuation.edge.options_fill import COMMISSION_PER_CONTRACT  # noqa: E402

# ---------------------------------------------------------------------------------------------
# Registered constants. Every one of these is in PREREG_v5reread_deepitm_financing.md section 2.
# ---------------------------------------------------------------------------------------------
DTE_LO, DTE_HI = 60, 90
DELTA_LO, DELTA_HI = 0.85, 0.95
MIN_N = 30                                  # V5's own floor, reused deliberately (section 2.6)

C1_BAND_BPS = (0.0, 150.0)                  # gating: median (r*-rf) at MID must land here
C2_MAX_NONSENSE_FRAC = 0.05                 # gating: |K/S - 1| > 1 on at most 5% of pairs

RHO_O18 = 0.6743                            # O18's price-improvement factor (EXTRAPOLATED here)

# Retail margin rates. ASSUMPTIONS, not measurements — published rates, not something we own.
MARGIN_ROUTES = (
    ("robinhood_gold",     0.0575, "5.75% flat"),
    ("robinhood_standard", 0.1150, "11-12%, midpoint"),
    ("ibkr_pro_tiered",    None,   "~rf + 150 bps"),
)
IBKR_SPREAD_BPS = 150.0

DATA = os.path.join(_REPO, "data")
_PRIMARY_DATA = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data")


def _data(*parts) -> str:
    """Repo-anchored, falling back to the primary checkout.

    The worktree's data/ does not carry the options freeze or the bars; they live in the primary
    checkout. A RELATIVE path here would resolve against the working directory and silently find
    nothing, which is the defect options_backtest.BARS_CACHE shipped (session 25).

    EXISTENCE IS NOT POPULATION. The worktree carries an EMPTY data/bulk/prepared/bars while the
    primary checkout holds 502 files, so a plain os.path.exists() test picks the empty one and
    every spot lookup silently returns nothing. Measured, not hypothetical: the first run of this
    script reported `spot series: 0` and zero surviving pairs. A directory therefore counts as
    present only if it has entries -- the same rule optionable_universe.is_populated_cache exists
    for, repeated here because I made the identical mistake in a new file.
    """
    p = os.path.join(DATA, *parts)
    if os.path.isdir(p):
        if os.listdir(p):
            return p
    elif os.path.exists(p):
        return p
    return os.path.join(_PRIMARY_DATA, *parts)


FREEZE = os.path.join("options_freeze", "R2_CORRECTED_2026-08-08", "chains.pkl.gz")
OUT_CONTROLS = os.path.join("free_analysis", "DEEPITM_FIN_CONTROLS.json")
OUT_ARMS = os.path.join("free_analysis", "DEEPITM_FIN.json")


def _log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------------------------
def load_freeze() -> pd.DataFrame:
    path = _data(FREEZE)
    with gzip.open(path, "rb") as fh:
        df = pickle.load(fh)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["expiration"] = pd.to_datetime(df["expiration"])
    df["dte"] = (df["expiration"] - df["date"]).dt.days
    df["symbol"] = df["symbol"].astype(str).str.upper()
    return df


def load_spot() -> dict:
    """symbol -> Series indexed by date of RAW (as-traded) close.

    raw_close, never close. `close` is split- and dividend-adjusted; matching an as-traded strike
    against it is the U1-SPLIT defect and it fails SILENTLY (the option still prices, it is simply
    nowhere near the money).
    """
    root = _data(os.path.join("bulk", "prepared", "bars"))
    out = {}
    for fn in os.listdir(root):
        if not fn.endswith(".pkl"):
            continue
        sym = os.path.splitext(fn)[0].upper()
        try:
            d = pickle.load(open(os.path.join(root, fn), "rb"))
        except Exception:                                            # noqa: BLE001
            continue
        if not isinstance(d, dict) or "raw_close" not in d or "date" not in d:
            continue
        s = pd.Series(d["raw_close"], index=pd.to_datetime(d["date"]))
        out[sym] = s[~s.index.duplicated(keep="last")].sort_index()
    return out


def load_dividends() -> dict:
    path = _data(os.path.join("bulk", "prepared", "actions.pkl"))
    act = pickle.load(open(path, "rb"))
    out = {}
    for sym, rec in act.items():
        if not isinstance(rec, dict):
            continue
        divs = rec.get("dividends") or []
        if not divs:
            continue
        try:
            idx = pd.to_datetime([d for d, _ in divs])
            val = np.array([float(a) for _, a in divs], dtype="float64")
        except Exception:                                            # noqa: BLE001
            continue
        out[str(sym).upper()] = pd.Series(val, index=idx).sort_index()
    return out


# ---------------------------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------------------------
def matched_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Matched (symbol, date, expiration, strike) call/put pairs, both legs usable, in the band."""
    band = df[(df["dte"] >= DTE_LO) & (df["dte"] <= DTE_HI)].copy()
    # usable_quote is the SHARED rule (MA45). Imported, not re-typed.
    good = np.array([BS.usable_quote(b, a)
                     for b, a in zip(band["bid"].values, band["ask"].values)], dtype=bool)
    band = band[good]

    calls = band[band["right"] == "C"][["symbol", "date", "expiration", "strike", "bid", "ask"]]
    puts = band[band["right"] == "P"][["symbol", "date", "expiration", "strike", "bid", "ask"]]
    m = calls.merge(puts, on=["symbol", "date", "expiration", "strike"],
                    suffixes=("_c", "_p"), how="inner")
    m["dte"] = (m["expiration"] - m["date"]).dt.days
    m["T"] = m["dte"] / 365.0
    return m


def pv_dividends(sym: str, d0, d1, divs: dict, r: float) -> float:
    """PV of cash dividends with ex-dates in (d0, d1], discounted at r.

    The frontier DROPPED payers because omitting this biases r* DOWNWARD by an amount growing
    with T. Carrying it explicitly lets payers be kept, which is strictly more informative.
    """
    s = divs.get(sym)
    if s is None or not len(s):
        return 0.0
    k = s[(s.index > d0) & (s.index <= d1)]
    if not len(k):
        return 0.0
    tot = 0.0
    for dt_, amt in k.items():
        t = max((dt_ - d0).days, 0) / 365.0
        tot += float(amt) * math.exp(-r * t)
    return tot


def implied_rate(S: float, PVD: float, C: float, P: float, K: float, T: float) -> Optional[float]:
    """Solve S - PV(D) - (C - P) = K exp(-r* T) for r*."""
    lhs = S - PVD - (C - P)
    if lhs <= 0 or K <= 0 or T <= 0:
        return None
    return -math.log(lhs / K) / T


def call_delta(S, K, T, r, put_mid) -> Optional[float]:
    """Delta of the CALL, with IV solved on the PUT leg.

    The put is OTM at this corner and so well-conditioned; a deep-ITM call's vega is near zero
    and its own IV solve is unstable. Both routines are the shipped ones.
    """
    iv = BS.implied_vol(put_mid, S, K, T, r, right="P")
    if iv is None or not np.isfinite(iv) or iv <= 0:
        return None
    g = BS.greeks(S, K, T, r, iv, right="C")
    d = g.get("delta")
    return float(d) if d is not None and np.isfinite(d) else None


def build(df: pd.DataFrame, spot: dict, divs: dict, limit_names=None) -> pd.DataFrame:
    m = matched_pairs(df)
    if limit_names is not None:
        m = m[m["symbol"].isin(set(limit_names))]
    _log("matched two-sided pairs in the DTE band: %d" % len(m))

    rows = []
    rf_cache: dict = {}
    for sym, g in m.groupby("symbol", sort=False):
        s = spot.get(sym)
        if s is None:
            continue
        for t in g.itertuples(index=False):
            d0 = t.date
            try:
                S = float(s.asof(d0))
            except Exception:                                        # noqa: BLE001
                continue
            if not np.isfinite(S) or S <= 0:
                continue
            key = d0.date()
            r = rf_cache.get(key)
            if r is None:
                r = float(BS.risk_free_rate(key))
                rf_cache[key] = r

            K, T = float(t.strike), float(t.T)
            pvd = pv_dividends(sym, d0, t.expiration, divs, r)

            c_mid, p_mid = (t.bid_c + t.ask_c) / 2.0, (t.bid_p + t.ask_p) / 2.0
            dlt = call_delta(S, K, T, r, p_mid)
            if dlt is None or not (DELTA_LO <= dlt <= DELTA_HI):
                continue

            r_mid = implied_rate(S, pvd, c_mid, p_mid, K, T)
            # EXECUTABLE: buy the call at the ask, sell the put at the bid.
            r_exe = implied_rate(S, pvd, float(t.ask_c), float(t.bid_p), K, T)
            if r_mid is None or r_exe is None:
                continue

            half_c = (t.ask_c - t.bid_c) / 2.0
            half_p = (t.ask_p - t.bid_p) / 2.0
            rows.append({
                "symbol": sym, "date": d0, "expiration": t.expiration, "strike": K,
                "dte": int(t.dte), "T": T, "spot": S, "rf": r, "pvd": pvd, "delta": dlt,
                "moneyness": K / S,
                "r_mid": r_mid, "r_exe": r_exe,
                "excess_mid_bps": (r_mid - r) * 1e4,
                "excess_exe_bps": (r_exe - r) * 1e4,
                # one-way half-spread on the CALL leg, in bps of NOTIONAL (= spot), which is what
                # it costs to control one share -- not as a % of premium.
                "call_half_bps": (half_c / S) * 1e4,
                "put_half_bps": (half_p / S) * 1e4,
                "commission_bps": (COMMISSION_PER_CONTRACT / (S * 100.0)) * 1e4,
                "payer": pvd > 0.0,
            })
    out = pd.DataFrame(rows)
    _log("pairs surviving the delta band and the parity solve: %d" % len(out))
    if not len(out):
        # RAISE rather than return empty. An empty frame flows downstream and reads as "there are
        # no deep-ITM pairs in this band" -- a plausible-sounding coverage null -- when the real
        # cause is an input that never loaded. That is the failure mode MA31's two defects had
        # (0 of 113,945 rows joined, and n_dates=0 beside a coverage of 40 dates), and neither
        # raised. This one raises.
        raise RuntimeError(
            "ZERO pairs survived. This is an instrument failure, not a finding. "
            "Check that the spot series loaded (see `spot series:` above) before reading "
            "anything into it.")
    return out


# ---------------------------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------------------------
def controls(pairs: pd.DataFrame, df: pd.DataFrame, index_names) -> dict:
    out: dict = {"gating": {}, "reported": {}}

    nonp = pairs[~pairs["payer"]]
    med_mid = float(np.median(nonp["excess_mid_bps"])) if len(nonp) else float("nan")
    c1 = bool(len(nonp) >= MIN_N and C1_BAND_BPS[0] <= med_mid <= C1_BAND_BPS[1])
    out["gating"]["C1_instrument_sanity"] = {
        "median_excess_mid_bps_nonpayers": med_mid, "n": int(len(nonp)),
        "band_bps": list(C1_BAND_BPS), "pass": c1,
        "note": ("a SANITY BAND, not a reproduction target: the frontier's +43bps is 15 names "
                 "and this is the freeze's 186"),
    }

    if len(pairs):
        bad = float((np.abs(pairs["moneyness"] - 1.0) > 1.0).mean())
    else:
        bad = 1.0
    c2 = bool(bad <= C2_MAX_NONSENSE_FRAC)
    out["gating"]["C2_spot_fidelity"] = {
        "frac_nonsense_moneyness": bad, "max_allowed": C2_MAX_NONSENSE_FRAC, "pass": c2,
        "note": "as-traded raw_close against as-traded strikes; a split-adjusted spot fails here",
    }

    # C3 -- PV(D) and the frontier's own bias detector: a residual DTE gradient means PV(D) is
    # not doing its job.
    buckets = [(60, 70), (70, 80), (80, 91)]
    grad = {}
    for lo, hi in buckets:
        k = pairs[(pairs["dte"] >= lo) & (pairs["dte"] < hi)]
        grad["%d-%d" % (lo, hi)] = {
            "n": int(len(k)),
            "median_excess_exe_bps": float(np.median(k["excess_exe_bps"])) if len(k) else None,
            "median_excess_mid_bps": float(np.median(k["excess_mid_bps"])) if len(k) else None,
        }
    pay, non = pairs[pairs["payer"]], pairs[~pairs["payer"]]
    out["reported"]["C3_pvd"] = {
        "dte_gradient": grad,
        "payers": {"n": int(len(pay)),
                   "median_excess_mid_bps": float(np.median(pay["excess_mid_bps"])) if len(pay) else None},
        "non_payers": {"n": int(len(non)),
                       "median_excess_mid_bps": float(np.median(non["excess_mid_bps"])) if len(non) else None},
        "note": "payers KEPT with an explicit PV(D); the frontier dropped them instead",
    }
    out["reported"]["C4_american_exercise"] = {
        "corrected": False,
        "note": ("parity is an inequality for American options. The bias is SMALLEST exactly at "
                 "this corner because the matched put is deep OTM. Declared, not corrected."),
    }
    out["reported"]["C5_o18_rho"] = {
        "rho": RHO_O18,
        "note": ("measured on 35-delta ~60DTE contracts; applying it to deep-ITM is an "
                 "EXTRAPOLATION. Quoted spread is primary."),
    }
    out["reported"]["C6_commission"] = {
        "per_contract": COMMISSION_PER_CONTRACT, "imported_from": "options_fill", }
    out["reported"]["C7_roll_realism"] = {
        "note": ("the financing benefit REQUIRES rolling -- exercising means paying the strike in "
                 "cash, which defeats the purpose -- so each roll pays a full round trip"),
    }

    cov = pairs[pairs["symbol"].isin(set(index_names))]
    out["reported"]["coverage"] = {
        "freeze_names": int(df["symbol"].nunique()),
        "pair_names": int(pairs["symbol"].nunique()) if len(pairs) else 0,
        "n_pairs": int(len(pairs)),
        "date_min": str(pairs["date"].min().date()) if len(pairs) else None,
        "date_max": str(pairs["date"].max().date()) if len(pairs) else None,
        "index_names_total": len(index_names),
        "index_names_in_pairs": int(cov["symbol"].nunique()) if len(cov) else 0,
        "index_pairs": int(len(cov)),
        "note": ("the Index-scope question is NOT answerable here; the 186-name universe is the "
                 "headline and the Index cell carries no verdict (register 2.4)"),
    }

    out["all_gating_pass"] = bool(c1 and c2)
    return out


# ---------------------------------------------------------------------------------------------
# arms
# ---------------------------------------------------------------------------------------------
def _agg(x: np.ndarray) -> dict:
    n = int(len(x))
    if n < MIN_N:
        return {"n": n, "quotable": False,
                "note": "n < %d - NOT QUOTABLE, no aggregate printed (register 2.6)" % MIN_N}
    return {"n": n, "quotable": True,
            "median": float(np.median(x)), "mean": float(np.mean(x)),
            "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75))}


def annual_cost(pairs: pd.DataFrame, rho: float = 1.0) -> np.ndarray:
    """All-in annualised option-route cost, in bps over rf.

    (r* - rf) + round-trip spread x rolls/yr + commission x rolls/yr.
    A roll pays BOTH legs of the call spread (sell the old, buy the new) -- C7.
    """
    rolls = 365.0 / pairs["dte"].values
    roll_bps = 2.0 * pairs["call_half_bps"].values * rho
    return (pairs["excess_exe_bps"].values
            + roll_bps * rolls
            + pairs["commission_bps"].values * 2.0 * rolls)


def arms(pairs: pd.DataFrame, index_names) -> dict:
    res: dict = {}
    res["A1_financing_spread_mid_bps"] = _agg(pairs["excess_mid_bps"].values)
    res["A2_financing_spread_executable_bps"] = _agg(pairs["excess_exe_bps"].values)

    tot_q = annual_cost(pairs, rho=1.0)
    tot_r = annual_cost(pairs, rho=RHO_O18)
    res["A3_all_in_option_route_bps_yr"] = {
        "quoted_spread_primary": _agg(tot_q),
        "rho_adjusted_extrapolated": _agg(tot_r),
        "components_median": {
            "financing_excess_exe_bps": float(np.median(pairs["excess_exe_bps"])),
            "roll_spread_bps_yr": float(np.median(2.0 * pairs["call_half_bps"].values
                                                  * (365.0 / pairs["dte"].values))),
            "commission_bps_yr": float(np.median(pairs["commission_bps"].values * 2.0
                                                 * (365.0 / pairs["dte"].values))),
            "median_dte": float(np.median(pairs["dte"])),
            "rolls_per_year_at_median_dte": float(365.0 / np.median(pairs["dte"])),
        },
    }

    med_q = float(np.median(tot_q))
    med_r = float(np.median(tot_r))
    comp = {}
    for name, rate, desc in MARGIN_ROUTES:
        if rate is None:
            spread = IBKR_SPREAD_BPS
        else:
            spread = float(np.median((rate - pairs["rf"].values) * 1e4))
        comp[name] = {
            "assumption": desc,
            "margin_spread_over_rf_bps": spread,
            "option_route_bps_yr_quoted": med_q,
            "option_route_bps_yr_rho_adj": med_r,
            "option_cheaper_quoted": bool(med_q < spread),
            "option_cheaper_rho_adj": bool(med_r < spread),
            "difference_bps_quoted": med_q - spread,
        }
    res["A3_vs_margin"] = comp
    res["margin_rates_are_assumptions"] = (
        "published retail rates, NOT measurements this repository owns")

    per = []
    for sym, g in pairs.groupby("symbol"):
        a = _agg(annual_cost(g, rho=1.0))
        a["symbol"] = sym
        a["is_index_name"] = sym in set(index_names)
        per.append(a)
    per.sort(key=lambda d: (not d["quotable"], d.get("median", 1e18)))
    res["per_name"] = per
    res["per_name_below_floor"] = [d["symbol"] for d in per if not d["quotable"]]

    # ---- POST-HOC, NO VERDICT -------------------------------------------------------------
    # Not registered, added after seeing A3, and labelled as such (the V6-B C8 precedent). It is
    # neither a new price convention nor a new DTE/delta band, so it does not trip void
    # condition 3 -- but it carries no pass/fail and feeds no flag.
    #
    # A FLAT margin rate against a time-varying rf means the margin SPREAD moves enormously by
    # era: at rf 0.18% (2020) a 5.75% card is rf+557, at rf 5.22% (2023) it is rf+53. So "is the
    # option cheaper" is partly a question about WHEN, not only about which card.
    eras = []
    for lo, hi in ((2016, 2018), (2018, 2020), (2020, 2022), (2022, 2024), (2024, 2026)):
        k = pairs[(pairs["date"].dt.year >= lo) & (pairs["date"].dt.year < hi)]
        if not len(k):
            continue
        med_opt = float(np.median(annual_cost(k, rho=1.0)))
        med_rf = float(np.median(k["rf"]))
        gold = (0.0575 - med_rf) * 1e4
        eras.append({"era": "%d-%d" % (lo, hi), "n": int(len(k)),
                     "median_rf_pct": med_rf * 100.0,
                     "option_all_in_bps_yr": med_opt,
                     "robinhood_gold_spread_bps": gold,
                     "option_cheaper_than_gold": bool(med_opt < gold)})
    res["POST_HOC_by_rate_era_NO_VERDICT"] = {
        "note": ("POST-HOC, added after seeing A3, carries NO verdict and feeds no flag. A flat "
                 "margin card against a moving risk-free rate makes the comparison era-dependent."),
        "eras": eras,
    }

    cov = pairs[pairs["symbol"].isin(set(index_names))]
    res["index_cell_NO_VERDICT"] = {
        "n_pairs": int(len(cov)),
        "n_names": int(cov["symbol"].nunique()) if len(cov) else 0,
        "all_in_bps_yr": _agg(annual_cost(cov, rho=1.0)) if len(cov) else {"n": 0, "quotable": False},
        "note": ("11 of 86 Index names are in the freeze; this cell is reported for completeness "
                 "and carries NO verdict (register 2.4 / void condition 4)"),
    }
    return res


# ---------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    if not (a.controls_only or a.arms):
        ap.error("choose --controls-only or --arms (two-pass by design)")

    idx_path = _data("valquo_index.json")
    index_names = sorted({p["ticker"].upper()
                          for p in json.load(open(idx_path, encoding="utf-8"))["positions"]})

    _log("loading freeze ...")
    df = load_freeze()
    _log("freeze: %d rows, %d names" % (len(df), df["symbol"].nunique()))
    spot, divs = load_spot(), load_dividends()
    _log("spot series: %d   dividend series: %d" % (len(spot), len(divs)))
    if not spot:
        raise RuntimeError("no spot series loaded - the bars directory resolved empty; see _data()")

    pairs = build(df, spot, divs)
    cpath, apath = _data(OUT_CONTROLS), _data(OUT_ARMS)
    os.makedirs(os.path.dirname(cpath), exist_ok=True)

    if a.controls_only:
        c = controls(pairs, df, index_names)
        json.dump(c, open(cpath, "w", encoding="utf-8"), indent=2, default=str)
        _log("\nCONTROLS -> %s" % cpath)
        _log(json.dumps(c["gating"], indent=2, default=str))
        _log("ALL GATING PASS: %s" % c["all_gating_pass"])
        return 0 if c["all_gating_pass"] else 1

    # --arms REFUSES without a passing controls artifact. This is the gate.
    if not os.path.exists(cpath):
        _log("REFUSING: no controls artifact at %s - run --controls-only first" % cpath)
        return 2
    c = json.load(open(cpath, encoding="utf-8"))
    if not c.get("all_gating_pass"):
        _log("REFUSING: controls did not pass; no arm is scored")
        return 2

    res = arms(pairs, index_names)
    payload = {"register": "PREREG_v5reread_deepitm_financing.md",
               "adopts": "NOTHING", "recommends": "NOTHING",
               "controls": c, "arms": res}
    json.dump(payload, open(apath, "w", encoding="utf-8"), indent=2, default=str)
    _log("\nARMS -> %s" % apath)
    _log(json.dumps({k: v for k, v in res.items() if k != "per_name"}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
