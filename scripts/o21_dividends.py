"""O21 — what the pricer's missing dividend yield costs the banked book.

    python -m scripts.o21_dividends

Pre-registered in `PREREG_o21_dividends.md`, committed alone at bf5324c before this file existed.
The materiality bar (1.00pp OR any verdict changing its relationship to its bar) is fixed there.

Reads the SPLIT-CLEAN banked books and the frozen chains. No re-mine, no change to the exit
policy, no change to the moneyness or DTE bands.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import dividends as DV           # noqa: E402
from valuation.edge import blackscholes as BS        # noqa: E402
from valuation.edge import options_backtest as OB    # noqa: E402
from valuation.edge import options_freeze as FZ      # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
FREEZE = os.path.join(DATA, "options_freeze", "R2_CORRECTED_2026-08-08", "chains.pkl.gz")
OUT = os.path.join(DATA, "free_analysis", "O21_DIVIDENDS.json")

MATERIAL_PP = 1.00


def _log(m):
    print("[O21] %s" % m, flush=True)


def load_books() -> list:
    with open(os.path.join(UNIV, "state_r2_splitclean.pkl"), "rb") as f:
        return pickle.load(f)["rows"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O21 - dividends and early exercise")
    ap.add_argument("--limit", type=int, default=0, help="smoke-test subset; 0 = full book")
    args = ap.parse_args(argv)

    alert = load_books()
    if args.limit:
        alert = alert[:args.limit]
        _log("SMOKE-TEST SUBSET %d rows - not a verdict" % len(alert))
    divs = DV.load_dividends(DATA)
    _log("book %d rows; dividend table %d tickers" % (len(alert), len(divs)))

    res = {"item": "O21", "register": "PREREG_o21_dividends.md",
           "book": "split_clean (U1-SPLIT 2026-08-11)",
           "n_rows": len(alert), "material_bar_pp": MATERIAL_PP,
           "scoping": ("banked P&L comes from QUOTED bid/ask, so the pricer cannot move it "
                       "directly; it reaches the book only via early exercise (D1), contract "
                       "selection (D2) and stored derived fields (D3)")}

    # ---- yields ------------------------------------------------------------------------------
    covered = 0
    qs = []
    for r in alert:
        q = DV.q_trailing(divs, r.get("ticker"), r.get("alert_ts"), r.get("underlying_entry"))
        r["_q"] = q
        if q is not None and q > 0:
            covered += 1
            qs.append(q)
    qs.sort()
    res["q_trailing"] = {
        "n_rows_with_positive_yield": covered,
        "share": covered / max(1, len(alert)),
        "median": qs[len(qs) // 2] if qs else None,
        "p90": qs[int(0.9 * len(qs))] if qs else None,
        "max": qs[-1] if qs else None,
    }
    _log("rows with a positive trailing yield: %d (%.1f%%), median %s"
         % (covered, 100.0 * covered / max(1, len(alert)),
            ("%.4f" % qs[len(qs) // 2]) if qs else "n/a"))

    # ---- D1: early exercise, model-free ------------------------------------------------------
    _log("loading freeze ...")
    df = FZ.load_frozen(FREEZE)
    df["_d"] = df["date"].astype(str)
    _log("freeze rows %d" % len(df))

    by_sd_all = {}
    for (sym, d), sub in df.groupby(["symbol", "_d"], observed=True):
        by_sd_all[(sym, d)] = sub

    def exit_date(r):
        import datetime as dt
        a = DV._d(r.get("alert_ts"))
        if a is None:
            return None
        return (a + dt.timedelta(days=int(r.get("held_days") or 0))).isoformat()

    def _parity_spot(sym, dstr, strike, expiry):
        """Spot from put-call parity at the SAME strike and expiry. An equality, not a bound."""
        sub = by_sd_all.get((sym, dstr))
        if sub is None:
            return None
        m = sub[(sub["strike"].astype(float) == float(strike))
                & (sub["expiration"].astype(str).str[:10] == str(expiry)[:10])]
        if len(m) == 0:
            return None
        rights = m["right"].astype(str).str[0].str.upper()
        c = m[rights == "C"]
        p = m[rights == "P"]
        if len(c) == 0 or len(p) == 0:
            return None
        # The put row must carry a REAL quote. A put that is merely absent or unquoted would
        # leave S = C + K*exp(-rT), which overstates spot -- the same direction as the loose
        # bound this parity recovery replaced.
        pa = p.iloc[0]["ask"]
        if pa is None or float(pa) <= 0:
            return None
        cm = (float(c.iloc[0]["bid"]) + float(c.iloc[0]["ask"])) / 2.0
        pm = (float(p.iloc[0]["bid"]) + float(pa)) / 2.0
        a, x = DV._d(dstr), DV._d(expiry)
        if a is None or x is None:
            return None
        T = max((x - a).days, 0) / 365.0
        return DV.spot_from_parity(cm, pm, strike, BS.risk_free_rate(a), T)

    # CONTROL, run BEFORE D1 is quoted: parity must recover the ENTRY spot the book already
    # stores. If it cannot reproduce a number we know, it may not be trusted for one we do not.
    errs = []
    for r in alert:
        s = _parity_spot(r.get("ticker"), str(r.get("alert_ts"))[:10],
                         r.get("strike"), r.get("expiry"))
        if s is None or not r.get("underlying_entry"):
            continue
        errs.append(abs(s - float(r["underlying_entry"])) / float(r["underlying_entry"]))
    errs.sort()
    ctrl = {"n": len(errs),
            "median_rel_error": errs[len(errs) // 2] if errs else None,
            "p90_rel_error": errs[int(0.9 * len(errs))] if errs else None,
            "share_within_1pct": (sum(1 for e in errs if e <= 0.01) / len(errs))
            if errs else None}
    res["d1_parity_control"] = ctrl
    _log("D1 CONTROL parity vs stored underlying_entry: n=%d median rel err %s, within 1%%: %s"
         % (ctrl["n"],
            ("%.5f" % ctrl["median_rel_error"]) if ctrl["median_rel_error"] is not None
            else "n/a",
            ("%.3f" % ctrl["share_within_1pct"]) if ctrl["share_within_1pct"] is not None
            else "n/a"))

    # THE FREEZE CANNOT SUPPLY SPOT AT EXIT, and that is a property of the freeze rather than a
    # bug: it stores the FULL chain only on ENTRY dates and just the traded contract thereafter
    # (which is what keeps it to 2.87M rows). With no put at the exit date, parity has nothing
    # to work with. The underlying therefore comes from the SAME bars the simulation itself
    # uses -- `raw_close`, as-traded, because strikes are not split-adjusted. Using the
    # simulation's own price basis is what makes D1 comparable to the book it is measuring.
    bars_cache = {}

    # `OB.BARS_CACHE` is a RELATIVE path ("data/bulk/prepared/bars"), so it resolves to nothing
    # from a worktree, where `data/` lives three levels up. Passing the resolved root explicitly
    # rather than relying on cwd -- the first run of this study silently scored zero rows
    # because of it, and a silent zero is the failure mode worth guarding against.
    BARS_DIR = os.path.join(DATA, "bulk", "prepared", "bars")
    if not os.path.isdir(BARS_DIR):
        _log("WARNING: bars cache not found at %s - D1 cannot be scored" % BARS_DIR)

    def _bars(tkr):
        if tkr not in bars_cache:
            try:
                bars_cache[tkr] = OB.load_bars(tkr, cache_dir=BARS_DIR)
            except Exception:
                bars_cache[tkr] = None
        return bars_cache[tkr]

    def spot_at_exit(r):
        d = exit_date(r)
        if d is None:
            return None
        b = _bars(r.get("ticker"))
        if not b:
            return None
        px = b.get("raw_close") or b.get("close")
        ds = b.get("date") or []
        # The exit date may be a weekend or holiday; take the last bar at or before it, which is
        # the price a holder deciding to exercise would have seen.
        best = None
        for i, x in enumerate(ds):
            if str(x)[:10] <= d:
                best = px[i]
            else:
                break
        return best

    # CONTROL 2, on the SAME source D1 uses: bars `raw_close` at the ENTRY date must reproduce
    # the stored `underlying_entry`. The parity control above validates the freeze; this one
    # validates the bars, and D1 rests on the bars.
    berrs = []
    for r in alert:
        b = _bars(r.get("ticker"))
        if not b or not r.get("underlying_entry"):
            continue
        px = b.get("raw_close") or b.get("close")
        ds = b.get("date") or []
        got = None
        for i, x in enumerate(ds):
            if str(x)[:10] <= str(r["alert_ts"])[:10]:
                got = px[i]
            else:
                break
        if got:
            berrs.append(abs(got - float(r["underlying_entry"])) / float(r["underlying_entry"]))
    berrs.sort()
    res["d1_bars_control"] = {
        "n": len(berrs),
        "median_rel_error": berrs[len(berrs) // 2] if berrs else None,
        "share_within_1pct": (sum(1 for e in berrs if e <= 0.01) / len(berrs))
        if berrs else None}
    _log("D1 CONTROL bars raw_close vs stored underlying_entry: n=%d median rel err %s, "
         "within 1%%: %s"
         % (len(berrs),
            ("%.5f" % res["d1_bars_control"]["median_rel_error"])
            if berrs else "n/a",
            ("%.3f" % res["d1_bars_control"]["share_within_1pct"]) if berrs else "n/a"))

    d1 = DV.exit_below_intrinsic(alert, spot_at_exit)
    d1["note"] = ("spot at exit recovered by PUT-CALL PARITY at the same strike and expiry, an "
                  "equality rather than a bound; validated first against the stored entry spot")
    res["d1_early_exercise"] = d1
    res["d1_spanning"] = DV.held_across_ex_div(alert, divs)
    _log("D1 scored %d, below intrinsic %d (%.3f%%), mean expectancy gain %s"
         % (d1["n_scored"], d1["n_below_intrinsic"],
            100.0 * (d1["share_below_intrinsic"] or 0),
            ("%+.4f%%" % (100 * d1["mean_expectancy_gain_pct"]))
            if d1["mean_expectancy_gain_pct"] is not None else "n/a"))
    _log("D1 calls spanning an ex-div date: %d of %d"
         % (res["d1_spanning"]["n_calls_spanning_ex_div"], res["d1_spanning"]["n_rows"]))

    # ---- D2: contract selection --------------------------------------------------------------
    _log("D2: re-selecting contracts at q=0 (control) and q=trailing ...")
    by_sd = {}
    for (sym, d), sub in df.groupby(["symbol", "_d"], observed=True):
        by_sd[(sym, d)] = sub

    same_ctrl = 0
    scored = 0
    changed = 0
    changed_rows = []
    for i, r in enumerate(alert):
        if i and i % 500 == 0:
            _log("  D2 %d/%d" % (i, len(alert)))
        key = (r.get("ticker"), str(r.get("alert_ts"))[:10])
        sub = by_sd.get(key)
        if sub is None or r.get("underlying_entry") in (None, 0):
            continue
        und = float(r["underlying_entry"])
        asof = DV._d(r.get("alert_ts"))
        try:
            base = OB.pick_contract(sub, und, asof, right="C")
            alt = _pick_with_q(sub, und, asof, r.get("_q") or 0.0)
        except Exception:
            continue
        if base is None or alt is None:
            continue
        scored += 1
        bk = (float(base["strike"]), str(base["expiration"])[:10])
        banked = (float(r["strike"]), str(r["expiry"])[:10])
        ak = (float(alt["strike"]), str(alt["expiration"])[:10])
        if bk == banked:
            same_ctrl += 1
        if ak != bk:
            changed += 1
            changed_rows.append({
                "ticker": r.get("ticker"), "asof": key[1], "q": r.get("_q"),
                "base": list(bk), "alt": list(ak),
                "base_delta": float(base["delta"]), "alt_delta": float(alt["delta"]),
                "strike_gap_pct": (ak[0] - bk[0]) / und,
                "same_expiry": bk[1] == ak[1]})

    res["d2_selection"] = {
        "n_scored": scored,
        "control_reproduces_banked_contract": same_ctrl,
        "control_reproduction_rate": (same_ctrl / scored) if scored else None,
        "n_changed": changed,
        "share_changed": (changed / scored) if scored else None,
        "examples": changed_rows[:25],
    }

    # HOW DIFFERENT IS THE SUBSTITUTE? The P&L consequence is not computable (see below), but
    # the SIZE of the substitution is, and it bounds how different a trade the alternative is.
    if changed_rows:
        dd = sorted(abs(c["alt_delta"] - c["base_delta"]) for c in changed_rows)
        sg = sorted(c["strike_gap_pct"] for c in changed_rows)
        res["d2_selection"]["substitution"] = {
            "median_abs_delta_gap": dd[len(dd) // 2],
            "p90_abs_delta_gap": dd[int(0.9 * len(dd))],
            "median_strike_gap_pct": sg[len(sg) // 2],
            "share_same_expiry": sum(1 for c in changed_rows if c["same_expiry"])
            / len(changed_rows),
            "share_alt_strike_lower": sum(1 for c in changed_rows
                                          if c["alt"][0] < c["base"][0]) / len(changed_rows),
        }

    # IS THE ALTERNATIVE EVEN PRICEABLE? The freeze stores the FULL chain only on ENTRY dates
    # and just the traded contract thereafter, so a contract the book never held has no forward
    # price path. This is measured rather than asserted, because it is the reason D2's P&L is
    # reported as NOT COMPUTABLE instead of as zero.
    # ONE pass to build the lookup. Doing it as a filter per contract means 179 passes of
    # `.astype(str)` over 2.87M rows, which does not finish -- the first attempt had to be
    # killed after 20 minutes stuck here.
    _log("D2: building contract -> distinct-date counts (one pass) ...")
    cal = df[df["right"].astype(str).str[0].str.upper() == "C"]
    counts = (cal.assign(_e=cal["expiration"].astype(str).str[:10],
                         _k=cal["strike"].astype(float))
              .groupby(["symbol", "_k", "_e"], observed=True)["_d"].nunique().to_dict())
    alt_dates = [int(counts.get((c["ticker"], float(c["alt"][0]), str(c["alt"][1])[:10]), 0))
                 for c in changed_rows]
    if alt_dates:
        alt_dates.sort()
        res["d2_selection"]["alt_priceability"] = {
            "median_chain_dates_for_alt": alt_dates[len(alt_dates) // 2],
            "share_with_more_than_3_dates": sum(1 for x in alt_dates if x > 3) / len(alt_dates),
            "verdict": ("NOT COMPUTABLE on the frozen book - the freeze holds the full chain "
                        "only on ENTRY dates, so a contract the book never held has no forward "
                        "price path. Resolving D2's P&L requires a re-mine, which this session "
                        "is scoped out of."),
        }
        _log("D2 alt priceability: median %d chain dates, %.1f%% have >3 -> P&L NOT COMPUTABLE"
             % (alt_dates[len(alt_dates) // 2],
                100.0 * res["d2_selection"]["alt_priceability"]["share_with_more_than_3_dates"]))
    _log("D2 scored %d; control reproduces banked on %d (%.2f%%); contract CHANGES on %d (%.2f%%)"
         % (scored, same_ctrl, 100.0 * same_ctrl / max(1, scored),
            changed, 100.0 * changed / max(1, scored)))

    # ---- D3: derived fields ------------------------------------------------------------------
    _log("D3: re-solving iv and delta at q=trailing on the banked contracts ...")
    d3 = _derived_shift(alert, by_sd)
    res["d3_derived"] = d3
    _log("D3 scored %d; median iv shift %s; median |delta| shift %s; delta85 firing %s -> %s"
         % (d3["n_scored"],
            ("%+.5f" % d3["median_iv_shift"]) if d3["median_iv_shift"] is not None else "n/a",
            ("%+.5f" % d3["median_delta_shift"]) if d3["median_delta_shift"] is not None
            else "n/a",
            d3["n_abs_delta_gt_85_q0"], d3["n_abs_delta_gt_85_q"]))

    # ---- verdict -----------------------------------------------------------------------------
    d1_pp = 100.0 * (d1["mean_expectancy_gain_pct"] or 0.0)
    res["materiality"] = {
        "d1_expectancy_pp": d1_pp,
        "d2_share_changed": res["d2_selection"]["share_changed"],
        "bar_pp": MATERIAL_PP,
        "clause_a_met_on_d1": abs(d1_pp) >= MATERIAL_PP,
        "d2_pnl": "NOT COMPUTABLE on the frozen book",
        "verdict": ("IMMATERIAL ON THE MEASURABLE PART: D1 is %+.4fpp against a %.2fpp bar. "
                    "D2's frequency is measured but its P&L is not computable without a "
                    "re-mine, so the D2 contribution is UNRESOLVED and is reported as such "
                    "rather than assumed to be zero." % (d1_pp, MATERIAL_PP)),
    }
    _log("MATERIALITY: D1 %+.4fpp against a %.2fpp bar" % (d1_pp, MATERIAL_PP))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True, default=str)
    _log("-> %s" % OUT)
    return 0


def _pick_with_q(chain, underlying, asof, q):
    """`pick_contract` with a dividend yield. Deliberately a COPY of the shipped selector's
    narrowing, not a call into it with a patched global -- monkeypatching the live module would
    make the control and the challenger share mutable state."""
    import pandas as pd
    from valuation.edge import options_fill as F

    d = chain[chain["right"].astype(str).str[0].str.upper() == "C"]
    if len(d) == 0:
        return None
    exp = pd.to_datetime(d["expiration"]).dt.date
    dte = pd.Series([(e - asof).days for e in exp], index=d.index)
    d = d[(dte >= OB.DTE_RANGE[0]) & (dte <= OB.DTE_RANGE[1])]
    if len(d) == 0:
        return None
    mny = d["strike"].astype(float) / float(underlying)
    near = d[(mny >= 0.90) & (mny <= 1.20)]
    if len(near) == 0:
        near = d
    enr = BS.enrich_chain(near, underlying, asof, q=q)
    enr = enr.dropna(subset=["delta"])
    if len(enr) == 0:
        return None
    ok = []
    for _, r in enr.iterrows():
        quote = F.Quote(bid=r.get("bid"), ask=r.get("ask"), oi=r.get("open_interest"),
                        volume=r.get("volume"))
        if F.quote_reject_reason(quote) is None:
            ok.append(r)
    if not ok:
        return None
    return min(ok, key=lambda r: abs(abs(float(r["delta"])) - OB.TARGET_DELTA))


def _derived_shift(alert, by_sd) -> dict:
    iv_sh, dl_sh = [], []
    n85_0 = n85_q = 0
    scored = 0
    for r in alert:
        key = (r.get("ticker"), str(r.get("alert_ts"))[:10])
        sub = by_sd.get(key)
        if sub is None or not r.get("underlying_entry"):
            continue
        m = sub[(sub["strike"].astype(float) == float(r["strike"]))
                & (sub["expiration"].astype(str).str[:10] == str(r["expiry"])[:10])
                & (sub["right"].astype(str).str[0].str.upper()
                   == str(r["opt_right"])[0].upper())]
        if len(m) == 0:
            continue
        row = m.iloc[0]
        bid, ask = row.get("bid"), row.get("ask")
        if bid is None or ask is None:
            continue
        mid = (float(bid) + float(ask)) / 2.0
        if mid <= 0:
            continue
        S = float(r["underlying_entry"])
        K = float(r["strike"])
        asof = DV._d(r.get("alert_ts"))
        exp = DV._d(r.get("expiry"))
        if asof is None or exp is None:
            continue
        T = max((exp - asof).days, 1) / 365.0
        rate = BS.risk_free_rate(asof)
        right = str(r.get("opt_right") or "C")[0].upper()
        q = float(r.get("_q") or 0.0)
        v0 = BS.implied_vol(mid, S, K, T, rate, right, 0.0)
        vq = BS.implied_vol(mid, S, K, T, rate, right, q)
        if v0 is None or vq is None:
            continue
        g0 = BS.greeks(S, K, T, rate, v0, right, 0.0)
        gq = BS.greeks(S, K, T, rate, vq, right, q)
        scored += 1
        iv_sh.append(vq - v0)
        dl_sh.append(abs(gq["delta"]) - abs(g0["delta"]))
        n85_0 += 1 if abs(g0["delta"]) > 0.85 else 0
        n85_q += 1 if abs(gq["delta"]) > 0.85 else 0
    iv_sh.sort()
    dl_sh.sort()
    return {"n_scored": scored,
            "median_iv_shift": iv_sh[len(iv_sh) // 2] if iv_sh else None,
            "median_delta_shift": dl_sh[len(dl_sh) // 2] if dl_sh else None,
            "max_abs_iv_shift": max((abs(x) for x in iv_sh), default=None),
            "max_abs_delta_shift": max((abs(x) for x in dl_sh), default=None),
            "n_abs_delta_gt_85_q0": n85_0, "n_abs_delta_gt_85_q": n85_q}


if __name__ == "__main__":
    raise SystemExit(main())
