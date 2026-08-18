"""MA31 + MA32 — build the features, run the gating controls, then score the arms.

Executes `PREREG_ma31_ma32_parity_openclose.md`, committed ALONE at `a51e372`.

THREE STAGES, AND THE SEPARATION IS THE POINT
---------------------------------------------
    python -m scripts.ma31_ma32_measure --build       # features only; scores nothing
    python -m scripts.ma31_ma32_measure --controls    # gating controls; EXITS before any arm
    python -m scripts.ma31_ma32_measure --arms        # REFUSES unless the controls artifact is ok

Session 26 shipped a defect in which a gating control and the outcomes it gated were computed in
one pass, so it could not be claimed the control had been read first. `--arms` loads the controls
artifact and aborts on a failure, which is `O19`'s design and the repair for that defect.

NETWORK: none. Bars are read from the cache DIRECTLY rather than through
`options_backtest.load_bars`, which falls back to a Sharadar fetch when the cache misses. That
fallback would be licensed vendor spend triggered by a research script (`MA7`'s class), and a
silent one. `_bars_offline` cannot fetch.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import pickle
import sys
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge.chain_store import resolve_chains as _resolve_chains  # noqa: E402

from valuation.edge import blackscholes as BS                     # noqa: E402
from valuation.edge import dividends as DIV                       # noqa: E402
from valuation.studies import parity_flow as PF                   # noqa: E402
from valuation.studies import portfolio_capacity as PC            # noqa: E402
from valuation.studies import surface_stock as SS                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    """`o10_o18_tickflow._data_root`'s convention, and it is load-bearing in a worktree.

    A git worktree carries its OWN partial `data/` (app.db, bulk, free_analysis) while the raw
    chains live in the primary checkout. A relative `data/` therefore resolves to something that
    EXISTS but is missing the caches - the silent-empty failure `options_backtest.BARS_CACHE`
    already shipped once. Probing for `options/` picks the real root rather than the first one
    that happens to be a directory.
    """
    for cand in (os.path.join(ROOT, "data"), os.path.join(ROOT, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(ROOT, "data"))


DATA = _data_root()
# ---------------------------------------------------------------------------------------------
# CHAIN STORE — the PINNED freeze, resolved lazily.
#
# `data/options` is written by the miner continuously, and the options re-open list measured
# 44.2% of its payload units rewritten AFTER the books here were banked. Reading it back was
# therefore not reading the bytes these verdicts stand on. One shared resolver now owns that
# decision; the mutable store is an explicit opt-out (VALQUO_CHAINS=mutable), never a silent
# fallback.
#
# Resolved on first USE rather than at import: tests import this module and CI has no D: drive,
# so resolving at module level would raise at import time and take the suite down.
_CHAINS = None
CHAINS_PROVENANCE = None


def chains_dir():
    """The chain-store root. Raises if the pin is unusable rather than falling back."""
    global _CHAINS, CHAINS_PROVENANCE
    if _CHAINS is None:
        _CHAINS, CHAINS_PROVENANCE = _resolve_chains(DATA)
    return _CHAINS
BARS = os.path.join(DATA, "bulk", "prepared", "bars")
PANEL = os.path.join(DATA, "free_analysis", "panel_corrected_69d.pkl")
OUTDIR = os.path.join(DATA, "free_analysis")
FEATURES = os.path.join(OUTDIR, "MA31_MA32_FEATURES.pkl")
CONTROLS = os.path.join(OUTDIR, "MA31_MA32_CONTROLS.json")
RESULT = os.path.join(OUTDIR, "MA31_MA32.json")

JOIN_LOOKBACK_DAYS = 14        # window loaded before each rebalance date; the join itself is 7


def log(m):
    print(f"[ma31/32] {m}", flush=True)


# --------------------------------------------------------------------------- #
#  offline inputs
# --------------------------------------------------------------------------- #
def _bars_offline(ticker: str) -> Optional[dict]:
    """Read the bars cache and NOTHING else. Never fetches; returns None when absent."""
    p = os.path.join(BARS, f"{ticker.upper()}.pkl")
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            got = pickle.load(f)
    except (OSError, pickle.UnpicklingError):
        return None
    if not isinstance(got, dict) or "raw_close" not in got:
        return None                      # pre-`raw_close` cache: split-mixed, refuse it
    return {"date": list(got["date"]), "raw_close": [float(x) for x in got["raw_close"]],
            "close": [float(x) for x in got.get("close") or got["raw_close"]]}


def _raw_spot_map(bars: dict) -> Dict[str, float]:
    return dict(zip(bars["date"], bars["raw_close"]))


def _tickers() -> List[str]:
    return sorted(x for x in os.listdir(chains_dir()) if os.path.isdir(os.path.join(chains_dir(), x)))


# --------------------------------------------------------------------------- #
#  stage 1 — features
# --------------------------------------------------------------------------- #
def build(limit: Optional[int] = None, progress_every: int = 25) -> pd.DataFrame:
    panel = pd.read_pickle(PANEL)
    rebs = sorted(pd.to_datetime(panel["date"]).unique())
    names = set(panel["ticker"].unique())
    try:
        divs = DIV.load_dividends(DATA)
    except Exception as e:                                          # noqa: BLE001
        log(f"dividends unavailable ({type(e).__name__}); q=0 and C-DIV will say so")
        divs = {}

    universe = [t for t in _tickers() if t in names]
    if limit:
        universe = universe[:limit]
    log(f"universe: {len(universe)} tickers (cache INTERSECT panel), {len(rebs)} rebalance dates")

    # window of chain dates wanted before each rebalance date
    want = []
    for rb in rebs:
        d1 = pd.Timestamp(rb)
        want.append((d1 - pd.Timedelta(days=JOIN_LOOKBACK_DAYS), d1))

    rows, t0 = [], time.time()
    n_no_bars = 0
    for k, tkr in enumerate(universe):
        bars = _bars_offline(tkr)
        spot_of = _raw_spot_map(bars) if bars else None
        if spot_of is None:
            n_no_bars += 1
        files = sorted(glob.glob(os.path.join(chains_dir(), tkr, f"{tkr}-*.pkl")))
        by_year: Dict[int, Optional[pd.DataFrame]] = {}
        for f in files:
            try:
                y = int(os.path.basename(f).rsplit("-", 1)[-1][:-4])
            except ValueError:
                continue
            by_year[y] = None
        for lo, hi in want:
            yrs = {lo.year, hi.year}
            frames = []
            for y in sorted(yrs):
                if y not in by_year:
                    continue
                if by_year[y] is None:
                    try:
                        df = pd.read_pickle(os.path.join(chains_dir(), tkr, f"{tkr}-{y}.pkl"))
                        df["_d"] = pd.to_datetime(df["date"])
                        by_year[y] = df
                    except Exception:                               # noqa: BLE001
                        by_year[y] = False
                if by_year[y] is not False and by_year[y] is not None:
                    frames.append(by_year[y])
            if not frames:
                continue
            allx = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
            w = allx[(allx["_d"] >= lo) & (allx["_d"] < hi)]        # STRICTLY BEFORE hi
            if len(w) == 0:
                continue
            cds = sorted(w["_d"].unique())
            join_d = cds[-1]
            if (hi - pd.Timestamp(join_d)).days > SS.MAX_STALE_DAYS:
                continue
            xs = w[w["_d"] == join_d]
            rec = {"ticker": tkr, "date": pd.Timestamp(hi), "chain_date": pd.Timestamp(join_d)}

            # ---- MA31: needs an AS-TRADED spot; no spot, no arm (never a proxy) ----
            key = str(pd.Timestamp(join_d).date())
            spot = (spot_of or {}).get(key)
            if spot and spot > 0:
                r = BS.risk_free_rate(key)
                q = 0.0
                if divs:
                    qq = DIV.q_trailing(divs, tkr, key, float(spot))
                    q = float(qq) if qq is not None else 0.0
                vs = PF.volatility_spread(xs, float(spot), key, r, q)
                if vs:
                    rec.update(vs)
                    rec["spot"] = float(spot)
                    rec["q"] = q
                # C-BAND / C-AMER sensitivities: reported, no verdict
                vsw = PF.volatility_spread(xs, float(spot), key, r, q,
                                           band=PF.MONEYNESS_BAND_WIDE)
                if vsw:
                    rec["parity_dev_wide"] = vsw["parity_dev"]

            # ---- MA32: needs NO spot, so its universe is wider ----
            prevs = [d for d in cds if d < join_d]
            if prevs:
                osh = PF.open_shares(xs, w[w["_d"] == prevs[-1]], join_d, prevs[-1])
                if osh:
                    rec.update(osh)
            if len(rec) > 3:
                rows.append(rec)
        if progress_every and (k + 1) % progress_every == 0:
            el = time.time() - t0
            log(f"{k + 1}/{len(universe)} tickers, {len(rows)} rows, {el:.0f}s "
                f"(eta {el / (k + 1) * (len(universe) - k - 1):.0f}s)")

    out = pd.DataFrame(rows)
    log(f"built {len(out)} (ticker,date) rows; {n_no_bars} tickers had no bars cache")
    os.makedirs(OUTDIR, exist_ok=True)
    out.to_pickle(FEATURES)
    return out


# --------------------------------------------------------------------------- #
#  stage 2 — gating controls, read in their OWN pass
# --------------------------------------------------------------------------- #
def _joined() -> pd.DataFrame:
    """Attach the arms to the panel through `surface_stock.join_pit`.

    A DEFECT IN THIS FUNCTION, CAUGHT BY C-COV BEFORE ANY ARM WAS SCORED, and recorded because
    it would have read as a RESULT. The feature rows carry two dates: `chain_date`, the session
    the chain was observed on, and `date`, the rebalance date it was built for. `join_pit`
    implements the strictly-before rule and the 7-day staleness ceiling ITSELF, so handing it a
    frame keyed on the REBALANCE date makes it search for the last rebalance strictly before this
    one - a quarter old, so every row fails the staleness ceiling. It joined 0 of 113,945 rows.

    Nothing raised. Coverage simply read zero, and "the arms have no coverage" is a sentence this
    project has legitimately written five times (S18, U2, U3, V6-OPT, U6), so it would have been
    entirely believable. The gate is what separated a bug from a finding.
    """
    panel = pd.read_pickle(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    feats = pd.read_pickle(FEATURES)
    # the arms, plus two DIAGNOSTIC columns that carry no verdict: the wide-band sensitivity
    # (C-BAND) and the dividend yield the IV solve used (C-DIV).
    cols = [c for c in list(PF.ARMS) + ["parity_dev_wide", "q"] if c in feats.columns]
    obs = feats.rename(columns={"date": "rebalance_date", "chain_date": "date"})
    by_t = {t: g.sort_values("date").reset_index(drop=True)
            for t, g in obs.groupby("ticker")}
    j, ctrl = SS.join_pit(panel, by_t, value_cols=cols)
    j.attrs["pit"] = ctrl
    return j


def controls() -> dict:
    feats = pd.read_pickle(FEATURES)
    j = _joined()
    out = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
           "register": "PREREG_ma31_ma32_parity_openclose.md",
           "register_commit": "a51e372"}

    # C-PIT ------------------------------------------------------------------
    out["C_PIT"] = j.attrs["pit"]

    # C-SPOT -----------------------------------------------------------------
    # TWO DIRECTIONS, and only the second is informative. (a) feeding the RAW series must PASS,
    # which verifies the stored spot really is `raw_close` at the chain date rather than some
    # other column or some other date - near-tautological, but it is what catches a code path
    # that silently swapped either. (b) feeding the ADJUSTED series should RAISE; that is
    # session 30's measurement of what the trap would have cost, and if it does NOT raise it
    # means adjusted and raw agree on these names, so (b) is uninformative rather than a pass.
    have = feats.dropna(subset=["spot"]) if "spot" in feats.columns else feats.iloc[:0]
    rows, raw_by, adj_by = [], {}, {}
    for tkr, g in have.groupby("ticker"):
        b = _bars_offline(tkr)
        if not b:
            continue
        raw_s = dict(zip(b["date"], b["raw_close"]))
        adj_s = dict(zip(b["date"], b["close"]))
        for _, r in g.iterrows():
            k = str(pd.Timestamp(r["chain_date"]).date())
            if k in raw_s and k in adj_s:
                rows.append({"ticker": tkr, "alert_ts": k, "underlying_entry": float(r["spot"])})
                raw_by.setdefault(tkr, {})[k] = raw_s[k]
                adj_by.setdefault(tkr, {})[k] = adj_s[k]
    try:
        det = PC.assert_raw_spot(rows, raw_by)
        a = {"ok": True, "detail": det}
    except Exception as e:                                          # noqa: BLE001
        a = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    try:
        det_b = PC.assert_raw_spot(rows, adj_by)
        b_res = {"raised": False, "detail": det_b,
                 "note": "adjusted agrees with raw on these names, so this direction is "
                         "UNINFORMATIVE - it is not evidence the basis is right"}
    except Exception as e:                                          # noqa: BLE001
        b_res = {"raised": True, "error": f"{type(e).__name__}: {e}",
                 "note": "the adjusted series is refused, which is the trap being real"}
    out["C_SPOT"] = {"ok": a["ok"], "n_checked": len(rows), "raw_direction": a,
                     "adjusted_direction": b_res}

    # C-SENT — the B4 sentinel must actually be being removed ------------------
    ns = int(feats["n_sentinel_dropped"].fillna(0).sum()) if "n_sentinel_dropped" in feats else 0
    out["C_SENT"] = {"contract_days_dropped": ns, "ok": ns > 0,
                     "note": "a ZERO would mean the filter never reached the data"}

    # C-COV ------------------------------------------------------------------
    cov = {a: PF.coverage_report(j, a) for a in PF.ARMS if a in j.columns}
    out["C_COV"] = {a: {k: v for k, v in c.items() if k != "dates"} for a, c in cov.items()}
    ok_cov = {}
    for a, c in cov.items():
        try:
            e, l, b = SS.halves(c["dates"])
            ok_cov[a] = {"ok": True, "n_early": len(e), "n_late": len(l), "boundary": str(b)[:10]}
        except SS.RegisterViolation as err:
            ok_cov[a] = {"ok": False, "error": str(err)}
    out["C_COV_HALVES"] = ok_cov

    # C-DUP — is an arm another arm, or U2's already-rejected arm, renamed? ----
    dups = []
    if "call_open_share" in j.columns and "put_open_share" in j.columns:
        dups.append(PF.duplicate_check(j, "call_open_share", "put_open_share"))
    out["C_DUP"] = dups
    out["C_DUP_note"] = ("vs U2's -skew_25d is computed in --arms, where the derived layer is "
                         "loaded; it is a gating check there and is reported with the arms")

    gates = [out["C_PIT"]["ok"], out["C_SPOT"]["ok"], out["C_SENT"]["ok"]] + \
            [v["ok"] for v in ok_cov.values()] + [not d["duplicate"] for d in dups]
    out["ALL_GATES_OK"] = bool(all(gates))
    os.makedirs(OUTDIR, exist_ok=True)
    with open(CONTROLS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    log(f"controls written -> {CONTROLS}; ALL_GATES_OK={out['ALL_GATES_OK']}")
    return out


# --------------------------------------------------------------------------- #
#  stage 3 — arms. REFUSES unless the controls artifact exists and passed.
# --------------------------------------------------------------------------- #
def arms() -> dict:
    if not os.path.exists(CONTROLS):
        raise SystemExit("REFUSING: no controls artifact. Run --controls first and read it. "
                         "A gating control and the outcomes it gates may not share a pass.")
    with open(CONTROLS, encoding="utf-8") as f:
        ctrl = json.load(f)
    if not ctrl.get("ALL_GATES_OK"):
        raise SystemExit(f"REFUSING: gating controls failed -> {CONTROLS}")

    j = _joined()
    res = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
           "register": "PREREG_ma31_ma32_parity_openclose.md",
           "register_commit": "a51e372", "controls": ctrl, "arms": {}}

    # C-DUP vs U2's ALREADY-REJECTED arm. GATING. `-skew_25d` is the call-minus-put IV spread at
    # 25 delta; `parity_dev` is an OI-weighted matched-strike object over the whole near-money
    # chain. If they are the same thing, MA31 is U2's rejected arm wearing a new name and carries
    # no independent verdict - U2's own §0.3 discipline, applied to the item that supersedes it.
    dupu2 = {"ran": False, "reason": "derived daily layer not found"}
    if "parity_dev" in j.columns:
        derived = os.path.join(DATA, "options_derived")
        want = set(j.dropna(subset=["parity_dev"])["ticker"].unique())
        arms_by = {}
        for t in sorted(want):
            p = os.path.join(derived, t, f"{t}-daily.pkl")
            if not os.path.exists(p):
                continue
            try:
                with open(p, "rb") as fh:
                    df = pickle.load(fh)
            except Exception:                                        # noqa: BLE001
                continue
            if isinstance(df, pd.DataFrame) and "date" in df.columns:
                a = SS.build_arm_columns(df)
                a["neg_skew_25d"] = -a["skew_25d"]
                arms_by[t] = a[["date", "neg_skew_25d"]]
        if arms_by:
            j2, _ = SS.join_pit(j, arms_by, value_cols=("neg_skew_25d",))
            dupu2 = PF.duplicate_check(j2, "parity_dev", "neg_skew_25d")
            dupu2["ran"] = True
            dupu2["note"] = ("U2 rejected `skew_25d` as a stock signal; if MA31 duplicates its "
                             "negation it inherits that rejection instead of earning a verdict")
    res["C_DUP_vs_U2"] = dupu2
    if dupu2.get("ran") and dupu2.get("duplicate"):
        res["arms"]["parity_dev"] = {"verdict": "DUPLICATE", "detail": dupu2}

    for arm in PF.ARMS:
        if arm not in j.columns:
            res["arms"][arm] = {"verdict": "NOT_BUILT"}
            continue
        if res["arms"].get(arm, {}).get("verdict") == "DUPLICATE":
            continue                       # C-DUP already settled it; no independent verdict
        cov = PF.coverage_report(j, arm)
        try:
            early, late, boundary = SS.halves(cov["dates"])
        except SS.RegisterViolation as err:
            res["arms"][arm] = {"verdict": "NULL", "reasons": [str(err)], "coverage": cov}
            continue
        full = PF.arm_ic(j, arm, cov["dates"])
        a_e = PF.arm_ic(j, arm, early)
        a_l = PF.arm_ic(j, arm, late)
        sign = PF.DECLARED_SIGN.get(arm)

        if arm == "parity_dev":
            bar_e = bar_l = PF.IC_BAR                    # X7's bar. AN EXTRAPOLATION here.
            nulls = {"kind": "X7 calibrated theme-IC p95", "bar": PF.IC_BAR,
                     "extrapolation": True}
        else:
            pe = PF.permutation_bar(j, arm, early, sign)
            pl = PF.permutation_bar(j, arm, late, sign)
            bar_e = pe.get("p95") if pe.get("ok") else float("inf")
            bar_l = pl.get("p95") if pl.get("ok") else float("inf")
            nulls = {"kind": "own within-date permutation p95", "early": pe, "late": pl}

        v = PF.verdict(arm, a_e["incremental_ic_tstat"], a_l["incremental_ic_tstat"],
                       bar_e, bar_l,
                       degenerate=bool(a_e["incremental_degenerate"]
                                       or a_l["incremental_degenerate"]))
        res["arms"][arm] = {"verdict_detail": v, "verdict": v["verdict"], "full": full,
                            "early": a_e, "late": a_l, "boundary": str(boundary)[:10],
                            "coverage": {k: x for k, x in cov.items() if k != "dates"},
                            "null": nulls,
                            "declared_sign": sign}

    # C-POWER, DECOMPOSED INTO THREE NESTED POPULATIONS - and the decomposition is the finding.
    #
    #   full        the whole 69-date panel
    #   dates       the 40 COVERED dates, ALL panel names   <- what U2 published as its control
    #   rows        the 40 covered dates, only the ROWS AN ARM IS MEASURED ON
    #
    # If `full` is strong and `rows` is weak, the options-listed sub-population is genuinely
    # underpowered and every null on it is uninterpretable. If `full` were weak too, the
    # measurement would be broken. Reporting only one column cannot tell those apart.
    panel_full = pd.read_pickle(PANEL)
    panel_full["date"] = pd.to_datetime(panel_full["date"])
    all_dates = sorted(panel_full["date"].unique())
    base_arm = PF.ARMS[0] if PF.ARMS[0] in j.columns else None
    cov0 = PF.coverage_report(j, base_arm) if base_arm else None
    cdates = cov0["dates"] if cov0 else all_dates
    crows = j.dropna(subset=[base_arm]) if base_arm else j

    power = {}
    for c in ("z_gp_on_capital", "z_ret_6_1", "quality", "momentum", "value", "size"):
        if c not in panel_full.columns:
            continue
        power[c] = {
            "full_69d": PF.arm_ic(panel_full, c, all_dates).get("raw_ic_tstat"),
            "covered_dates_all_names": PF.arm_ic(j, c, cdates).get("raw_ic_tstat"),
            "covered_rows": PF.arm_ic(crows, c, cdates).get("raw_ic_tstat"),
        }
    res["C_POWER"] = power
    audit_two = [power.get(c, {}) for c in ("z_gp_on_capital", "z_ret_6_1")]
    res["C_POWER_ok"] = bool(any((x.get("covered_rows") or 0) >= PF.POWER_BAR
                                 for x in audit_two)) if audit_two else None
    res["C_POWER_note"] = (
        "The audit's own bar is 2.0. Measured ON THE ROWS THE ARMS ARE MEASURED ON, the panel's "
        "best-known signals do NOT clear it, so by the register's own rule every null here is "
        "UNINTERPRETABLE - it means 'could not be separated at this resolution', never 'absent'.")

    # REPORTED CONTROLS, NO VERDICT -----------------------------------------
    rep = {}
    if "parity_dev" in j.columns:
        mde = {}
        for arm in PF.ARMS:
            if arm not in j.columns:
                continue
            cov = PF.coverage_report(j, arm)
            ser = []
            for d, g in j[j["date"].isin(cov["dates"])].groupby("date"):
                out = PF.residualise(g, arm, PF.INCUMBENTS)
                if out is not None:
                    ic = PF._spearman(out[0], out[1])
                    if ic == ic:
                        ser.append(ic)
            bar = PF.IC_BAR if arm == "parity_dev" else PF.POWER_BAR
            # BOTH mean and median. The MDE is `bar * sd/sqrt(n)`, so the quantity it is
            # comparable with is the MEAN - `ic_tstat` is mean/(sd/sqrt(n)). Reporting only the
            # median next to an MDE invites the reader to compare two different statistics, and
            # on a skewed IC series they disagree.
            mde[arm] = {"bar_used": bar, "mde_incremental_ic":
                        PF.minimum_detectable_ic(ser, bar),
                        "observed_mean_ic": float(np.mean(ser)) if ser else None,
                        "observed_median_ic": float(np.median(ser)) if ser else None,
                        "n_dates": len(ser)}
        rep["MDE"] = mde

        # C-BAND: the 0.20 moneyness sensitivity. Reported, no verdict.
        if "parity_dev_wide" in j.columns:
            cov = PF.coverage_report(j, "parity_dev")
            rep["C_BAND"] = {
                "spearman_vs_primary": PF.duplicate_check(j, "parity_dev",
                                                          "parity_dev_wide")["spearman"],
                "wide_full": PF.arm_ic(j, "parity_dev_wide", cov["dates"]),
                "note": "a sensitivity to the a-priori band, NOT a second hypothesis"}

        # C-DIV: a mis-specified dividend yield biases iv_call - iv_put systematically. If the
        # arm exists only among payers, it is a dividend artefact rather than a parity signal.
        if "q" in j.columns:
            cov = PF.coverage_report(j, "parity_dev")
            payers = j[(j["q"].fillna(0) > 0)]
            nonpay = j[(j["q"].fillna(0) <= 0) & j["parity_dev"].notna()]
            rep["C_DIV"] = {
                "n_payer_rows": int(payers["parity_dev"].notna().sum()),
                "n_nonpayer_rows": int(nonpay["parity_dev"].notna().sum()),
                "payers": PF.arm_ic(payers, "parity_dev", cov["dates"]),
                "nonpayers": PF.arm_ic(nonpay, "parity_dev", cov["dates"]),
                "mean_parity_dev_payers": float(payers["parity_dev"].mean()),
                "mean_parity_dev_nonpayers": float(nonpay["parity_dev"].mean())}
    res["REPORTED_CONTROLS"] = rep
    res["C_AMER"] = {"ran": False,
                     "reason": "needs a rebuild of the 27 GB feature pass and carries NO verdict "
                               "by the register, so it cannot change any result. Reported as "
                               "NOT RUN rather than silently skipped."}

    with open(RESULT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=str)
    log(f"arms written -> {RESULT}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arms", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.build:
        build(limit=a.limit)
    if a.controls:
        controls()
    if a.arms:
        arms()
    if not (a.build or a.controls or a.arms):
        ap.error("choose --build, --controls or --arms")


if __name__ == "__main__":
    main()
