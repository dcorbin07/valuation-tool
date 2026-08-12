"""O10 + O18 — the passive-limit fill model and the spread-conditional cost model.

    python -m scripts.o10_o18_tickflow            # full run
    python -m scripts.o10_o18_tickflow --limit 200  # smoke test, NOT a verdict

Pre-registered in `PREREG_o10_passive_fills.md` and `PREREG_o18_spread_cost.md`, committed
together and ALONE at 34b0c11 before this file existed.

Reads O14's tick cache and the split-clean banked book. No re-mine, no book re-banked, no live
code path changed. `DEFAULT_AGGRESSION` stays 1.0 whatever the verdict — both registers fix that
routing in advance and a test pins it.

Pass 1 extracts only the TRADED contract's prints from each alert-day file and caches them, so
the 4.7 GB read happens once and every re-analysis is in memory.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import tickflow as TF             # noqa: E402
from valuation.edge import options_fill as F          # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
TICKS = os.path.join(DATA, "options_ticks")
EXTRACT = os.path.join(DATA, "free_analysis", "O10_O18_EXTRACT.pkl")
OUT = os.path.join(DATA, "free_analysis", "O10_O18_TICKFLOW.json")

MISSING_DAY = ("BUD", "2024-01-10")      # O14's one genuine feed gap; named and excluded


def _log(m):
    print("[O10/O18] %s" % m, flush=True)


def load_book() -> list:
    with open(os.path.join(UNIV, "state_r2_splitclean.pkl"), "rb") as f:
        return pickle.load(f)["rows"]


# ---- Pass 1: extract the traded contract's prints ---------------------------------------------
def extract(rows, limit=0) -> list:
    out = []
    t0 = time.time()
    for i, r in enumerate(rows):
        if limit and i >= limit:
            break
        tkr = r["ticker"]
        day = str(r["alert_ts"])[:10]
        if (tkr, day) == MISSING_DAY:
            continue
        path = os.path.join(TICKS, tkr, "%s-%s.pkl" % (tkr, day))
        if not os.path.exists(path):
            out.append({"row": i, "ok": False, "why": "no_file"})
            continue
        try:
            df = pd.read_pickle(path)["rows"]
        except Exception as exc:                                  # pragma: no cover
            out.append({"row": i, "ok": False, "why": "read:%s" % type(exc).__name__})
            continue
        if df is None or not len(df):
            out.append({"row": i, "ok": False, "why": "empty"})
            continue
        want = "C" if r["opt_right"] == "call" else "P"
        m = ((np.abs(df["strike"].astype(np.float64) - float(r["strike"])) < 1e-6)
             & (df["right"].astype(str).str.upper().str[0] == want)
             & (pd.to_datetime(df["expiration"]).dt.strftime("%Y-%m-%d") == str(r["expiry"])[:10]))
        s = df.loc[m]
        if not len(s):
            out.append({"row": i, "ok": False, "why": "contract_not_on_tape"})
            continue
        s = s.sort_values("trade_timestamp")
        tt = pd.to_datetime(s["trade_timestamp"])
        t_s = (tt.dt.hour * 3600 + tt.dt.minute * 60 + tt.dt.second).to_numpy(np.int64)
        qt = pd.to_datetime(s["quote_timestamp"])
        lag = ((tt.to_numpy("datetime64[ns]").astype("int64")
                - qt.to_numpy("datetime64[ns]").astype("int64")) // 1_000_000_000)
        out.append({
            "row": i, "ok": True,
            "t": t_s,
            "price": s["price"].to_numpy(np.float64),
            "bid": s["bid"].to_numpy(np.float64),
            "ask": s["ask"].to_numpy(np.float64),
            "size": s["size"].to_numpy(np.float64),
            "cond": s["condition"].to_numpy(np.int64),
            "lag": np.asarray(lag, dtype=np.int64),
        })
        if (i + 1) % 250 == 0:
            _log("extract %d/%d  %.0fs" % (i + 1, len(rows), time.time() - t0))
    _log("extract done: %d units, %.0fs" % (len(out), time.time() - t0))
    return out


def coverage_profile(rows, ex, codes=TF.SINGLE_LEG_CODES, min_prints=TF.MIN_PRINTS) -> dict:
    """C4 — coverage AND the excluded set's profile, because the exclusion is not random."""
    inc, exc = [], []
    for rec in ex:
        if not rec.get("ok"):
            continue
        m = TF.eligible_mask(rec["bid"], rec["ask"], rec["cond"], codes)
        (inc if int(m.sum()) >= min_prints else exc).append((rows[rec["row"]], int(m.sum())))

    def prof(g):
        if not g:
            return None
        f = lambda k: np.array([float(r.get(k) if r.get(k) is not None else np.nan)
                                for r, _ in g], dtype=np.float64)
        return {
            "n": len(g),
            "median_entry_premium": float(np.nanmedian(f("entry_premium"))),
            "median_entry_spread_pct": float(np.nanmedian(f("entry_spread_pct"))),
            "median_marketcap_musd": float(np.nanmedian(f("marketcap_musd"))),
            "median_pit_atm_oi": float(np.nanmedian(f("pit_atm_oi"))),
            "share_pit_liquid": float(np.mean([bool(r.get("pit_liquid")) for r, _ in g])),
            "median_eligible_prints": float(np.median([n for _, n in g])),
            "mean_pnl_pct": float(np.nanmean(f("pnl_pct")) * 100.0),
        }

    tot = len(inc) + len(exc)
    return {"n_included": len(inc), "n_total_on_tape": tot,
            "coverage": (len(inc) / tot) if tot else None, "bar": 0.70,
            "passes": bool(tot and (len(inc) / tot) >= 0.70),
            "included": prof(inc), "excluded": prof(exc),
            "note": ("the excluded set is the THIN-TAPE end of the book and is not a random "
                     "subsample; any cost model calibrated here is calibrated on the liquid part")}


def _sub(rec, codes):
    m = TF.eligible_mask(rec["bid"], rec["ask"], rec["cond"], codes)
    return {k: rec[k][m] for k in ("t", "price", "bid", "ask", "size", "cond", "lag")}


# ---- Controls ---------------------------------------------------------------------------------
def controls(rows, ex) -> dict:
    rel_ask, rel_mid, n_join = [], [], 0
    for rec in ex:
        if not rec.get("ok"):
            continue
        r = rows[rec["row"]]
        e = _sub(rec, TF.SINGLE_LEG_CODES)
        if not len(e["t"]):
            continue
        n_join += 1
        a = float(e["ask"][-1])
        mid = float((e["ask"][-1] + e["bid"][-1]) / 2.0)
        ep = float(r["entry_premium"])
        if a > 0:
            rel_ask.append(abs(ep - a) / a)
        if mid > 0:
            rel_mid.append(abs(ep - mid) / mid)
    # C2 — the condition split, on the FULL book
    prof = {}
    for rec in ex:
        if not rec.get("ok"):
            continue
        b, a, p = rec["bid"], rec["ask"], rec["price"]
        ok = (b > 0) & (a > 0) & (a > b)
        if not ok.any():
            continue
        e = TF.signed_aggression(p[ok], b[ok], a[ok])
        for c in np.unique(rec["cond"][ok]):
            mm = rec["cond"][ok] == c
            d = prof.setdefault(int(c), {"n": 0, "touch": 0, "inside": 0})
            d["n"] += int(mm.sum())
            d["touch"] += int((np.abs(np.abs(e[mm]) - 1.0) < 1e-6).sum())
            d["inside"] += int((np.abs(e[mm]) < 0.999).sum())
    codes = {}
    tot = sum(d["n"] for d in prof.values()) or 1
    for c, d in sorted(prof.items(), key=lambda kv: -kv[1]["n"]):
        if d["n"] < 200:
            continue
        codes[str(c)] = {"n": d["n"], "share": d["n"] / tot,
                         "at_touch": d["touch"] / d["n"], "inside": d["inside"] / d["n"]}
    sl = [codes[str(c)]["at_touch"] for c in TF.SINGLE_LEG_CODES if str(c) in codes]
    pk = [codes[str(c)]["at_touch"] for c in TF.PACKAGE_CODES if str(c) in codes]
    return {
        "c1_reconciliation": {
            "median_rel_err_vs_last_ask": float(np.median(rel_ask)) if rel_ask else None,
            "median_rel_err_vs_last_mid": float(np.median(rel_mid)) if rel_mid else None,
            "n": n_join, "bar": 0.05,
            "passes": bool(rel_ask and float(np.median(rel_ask)) <= 0.05),
        },
        "c2_condition_profile": codes,
        "c2_separation_holds": bool(sl and pk and min(sl) > max(pk)),
        "c5_missing_day_excluded": {"ticker": MISSING_DAY[0], "date": MISSING_DAY[1],
                                    "rows_lost": 1},
    }


# ---- O10 ---------------------------------------------------------------------------------------
def run_o10(rows, ex, codes=TF.SINGLE_LEG_CODES, min_prints=TF.MIN_PRINTS) -> dict:
    cells = {}
    per_day = {}
    for lam in TF.LAMBDA_GRID:
        for h in TF.HORIZONS_MIN:
            key = "lam%+.1f_h%s" % (lam, "EOD" if h is None else h)
            acc = []
            for rec in ex:
                if not rec.get("ok"):
                    continue
                r = rows[rec["row"]]
                e = _sub(rec, codes)
                if len(e["t"]) < min_prints:
                    continue
                st = TF.passive_stats(e["t"], e["price"], e["bid"], e["ask"], lam, h,
                                      float(r["entry_premium"]))
                if st is None:
                    continue
                st["date"] = str(r["alert_ts"])[:10]
                st["row"] = rec["row"]
                acc.append(st)
            if not acc:
                continue
            cells[key] = _summarise(acc)
            per_day[key] = acc
    return cells, per_day


def _summarise(acc) -> dict:
    fr = np.array([a["fill_rate"] for a in acc], dtype=np.float64)
    npa = np.array([a["npa_pp"] for a in acc], dtype=np.float64)
    gross = np.array([a["gross_pp"] for a in acc], dtype=np.float64)
    adv = np.array([a["adverse_pp"] for a in acc], dtype=np.float64)
    dates = [a["date"] for a in acc]
    fin = np.isfinite(npa)
    boot = TF.block_bootstrap_mean(npa, TF.month_blocks(dates))
    return {
        "n_contract_days": int(len(acc)),
        "n_with_fill": int(fin.sum()),
        "fill_rate": float(fr.mean()),
        "gross_pp": float(np.nanmean(gross)) if fin.any() else None,
        "adverse_pp": float(np.nanmean(adv)) if fin.any() else None,
        "npa_pp": float(np.nanmean(npa)) if fin.any() else None,
        "npa_ci95": [boot["lo"], boot["hi"]],
        "n_month_blocks": boot.get("n_blocks"),
    }


def halves(rows, per_day_cell) -> dict:
    early = [a for a in per_day_cell if a["date"] < TF.SPLIT_DATE]
    late = [a for a in per_day_cell if a["date"] >= TF.SPLIT_DATE]
    return {"early": _summarise(early) if early else None,
            "late": _summarise(late) if late else None}


# ---- O18 ---------------------------------------------------------------------------------------
FAMILIES = ("F1_quoted_spread_pct", "F2_entry_premium", "F3_dte", "F4_marketcap",
            "F5_minutes_from_open", "F6_print_size")
OPEN_S = int(9.5 * 3600)


def run_o18(rows, ex, codes=TF.SINGLE_LEG_CODES, min_prints=TF.MIN_PRINTS) -> dict:
    # contract-day level rho
    cd = []
    for rec in ex:
        if not rec.get("ok"):
            continue
        r = rows[rec["row"]]
        e = _sub(rec, codes)
        if len(e["t"]) < min_prints:
            continue
        st = TF.rho_contract_day(e["price"], e["bid"], e["ask"], e["size"])
        if st is None:
            continue
        st.update({
            "date": str(r["alert_ts"])[:10], "row": rec["row"],
            "F1_quoted_spread_pct": float(r["entry_spread_pct"] or np.nan),
            "F2_entry_premium": float(r["entry_premium"]),
            "F3_dte": float(r["dte"]),
            "F4_marketcap": float(r["marketcap_musd"] or np.nan),
            "q_eod_half": float(r["entry_premium"]) * float(r["entry_spread_pct"] or np.nan) / 2.0,
            "q_print_half": st["mean_half"],
            "e": e,
        })
        cd.append(st)
    if not cd:
        return {"error": "no contract-days"}

    res = {"n_contract_days": len(cd)}
    rho_w = np.array([c["rho_w"] for c in cd])
    rho_u = np.array([c["rho_u"] for c in cd])
    res["rho_size_weighted"] = float(rho_w.mean())
    res["rho_unweighted"] = float(rho_u.mean())
    res["rho_ci95"] = TF.block_bootstrap_mean(rho_w, TF.month_blocks([c["date"] for c in cd]))

    # the decomposition: availability vs price improvement, kept apart
    qe = np.array([c["q_eod_half"] for c in cd])
    qp = np.array([c["q_print_half"] for c in cd])
    xe = np.array([c["rho_w"] * c["q_print_half"] for c in cd])
    ok = np.isfinite(qe) & np.isfinite(qp)
    res["decomposition_dollars_per_share"] = {
        "q_eod_half": float(qe[ok].mean()), "q_print_half": float(qp[ok].mean()),
        "effective_half": float(xe[ok].mean()),
        "availability_term": float((qe[ok] - qp[ok]).mean()),
        "price_improvement_term": float((qp[ok] - xe[ok]).mean()),
        "note": ("the availability term is a SELECTED quantity - you only avoid it if you trade "
                 "when the market is there - and is NOT claimed as a saving"),
    }

    # families
    fam = {}
    for f in FAMILIES:
        if f in ("F5_minutes_from_open", "F6_print_size"):
            vals, labs, dates = _print_level_family(cd, f, codes)
        else:
            vals = np.array([c["rho_w"] for c in cd])
            labs = TF.quintile_labels([c[f] for c in cd])
            dates = [c["date"] for c in cd]
        fam[f] = _family_result(vals, labs, dates)
    res["families"] = fam
    res["verdict"] = ("WARRANTED" if any(v.get("verdict") == "WARRANTED" for v in fam.values())
                      else "NULL")
    return res


def _print_level_family(cd, fname, codes):
    """Print-level attribute: bucket prints, then take each contract-day's size-weighted rho
    WITHIN each bucket, so the averaging unit stays the contract-day as registered."""
    pooled = []
    for c in cd:
        e = c["e"]
        pooled.append(e["t"] - OPEN_S if fname == "F5_minutes_from_open" else e["size"])
    edges_src = np.concatenate(pooled) if pooled else np.zeros(0)
    fin = np.isfinite(edges_src)
    if fin.sum() < TF.N_QUANTILES:
        return np.zeros(0), np.zeros(0, dtype=np.int64), []
    edges = np.quantile(edges_src[fin], np.linspace(0, 1, TF.N_QUANTILES + 1)[1:-1])
    vals, labs, dates = [], [], []
    for c in cd:
        e = c["e"]
        attr = e["t"] - OPEN_S if fname == "F5_minutes_from_open" else e["size"]
        b = (e["bid"] + e["ask"]) / 2.0
        half = (e["ask"] - e["bid"]) / 2.0
        m0 = half > 0
        if not m0.any():
            continue
        r = np.abs(e["price"][m0] - b[m0]) / half[m0]
        w = np.where(np.isfinite(e["size"][m0]) & (e["size"][m0] > 0), e["size"][m0], 1.0)
        lab = np.searchsorted(edges, attr[m0], side="right")
        for j in range(TF.N_QUANTILES):
            mm = lab == j
            if not mm.any():
                continue
            vals.append(float((r[mm] * w[mm]).sum() / w[mm].sum()))
            labs.append(j)
            dates.append(c["date"])
    return np.array(vals), np.array(labs, dtype=np.int64), dates


def _family_result(vals, labs, dates) -> dict:
    if not len(vals):
        return {"verdict": "NULL", "why": "empty"}
    out = {"n": int(len(vals))}
    out["bin_means"] = [
        (float(np.mean(vals[labs == j])) if (labs == j).any() else None)
        for j in range(TF.N_QUANTILES)]
    out["bin_n"] = [int((labs == j).sum()) for j in range(TF.N_QUANTILES)]
    # A quintile cut on a near-constant attribute collapses. Flagged as DEGENERATE rather than
    # reported as a failure to clear, the treatment O13 used for opt_right and horizon: a bin
    # that cannot exist is not evidence about the thing it would have measured.
    n_pop = sum(1 for c in out["bin_n"] if c > 0)
    out["populated_bins"] = n_pop
    out["degenerate"] = bool(n_pop < TF.N_QUANTILES)
    out["r_range"] = TF.r_range(vals, labs)
    out["spearman"] = TF.spearman(labs.astype(float), vals)
    null = TF.perm_null_r_range(vals, labs)
    out["null_p95"] = null.get("p95")
    out["clears_full"] = bool(out["r_range"] is not None and null.get("p95") is not None
                              and out["r_range"] > null["p95"])
    d = np.asarray(dates)
    parts = {}
    for nm, m in (("early", d < TF.SPLIT_DATE), ("late", d >= TF.SPLIT_DATE)):
        if m.sum() < TF.N_QUANTILES:
            parts[nm] = None
            continue
        v2, l2 = vals[m], labs[m]
        n2 = TF.perm_null_r_range(v2, l2)
        parts[nm] = {"n": int(m.sum()), "r_range": TF.r_range(v2, l2),
                     "null_p95": n2.get("p95"), "spearman": TF.spearman(l2.astype(float), v2)}
    out["halves"] = parts
    if out["degenerate"]:
        out["verdict"] = "DEGENERATE"
        return out
    e, l = parts.get("early"), parts.get("late")
    out["verdict"] = (TF.o18_family_verdict(
        e["r_range"], e["null_p95"], e["spearman"],
        l["r_range"], l["null_p95"], l["spearman"]) if (e and l) else "NULL")
    return out


# ---- main --------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O10 + O18 - tick-flow execution measurement")
    ap.add_argument("--limit", type=int, default=0, help="smoke-test subset; 0 = full book")
    ap.add_argument("--refresh", action="store_true", help="re-read the tick cache")
    args = ap.parse_args(argv)

    rows = load_book()
    _log("book rows: %d" % len(rows))

    if os.path.exists(EXTRACT) and not args.refresh and not args.limit:
        with open(EXTRACT, "rb") as f:
            ex = pickle.load(f)
        _log("extract loaded from cache: %d units" % len(ex))
    else:
        ex = extract(rows, limit=args.limit)
        if not args.limit:
            os.makedirs(os.path.dirname(EXTRACT), exist_ok=True)
            with open(EXTRACT, "wb") as f:
                pickle.dump(ex, f, protocol=4)

    ok = [r for r in ex if r.get("ok")]
    _log("units with the traded contract on tape: %d of %d" % (len(ok), len(ex)))

    ctl = controls(rows, ex)
    _log("C1 median rel err vs last ask: %s (bar 0.05, passes=%s)"
         % (ctl["c1_reconciliation"]["median_rel_err_vs_last_ask"],
            ctl["c1_reconciliation"]["passes"]))
    _log("C2 separation holds: %s" % ctl["c2_separation_holds"])

    # staleness diagnostic - NOT part of the registered eligibility rule
    lags = np.concatenate([r["lag"] for r in ok]) if ok else np.zeros(0)
    stale = {"n_prints": int(len(lags)),
             "median_lag_s": float(np.median(lags)) if len(lags) else None,
             "share_lag_gt_60s": float(np.mean(lags > TF.FRESH_QUOTE_MAX_LAG_S)) if len(lags) else None,
             "share_lag_gt_1h": float(np.mean(lags > 3600)) if len(lags) else None}
    _log("quote staleness: median %ss, share>60s %s" % (stale["median_lag_s"],
                                                        stale["share_lag_gt_60s"]))

    # PREREG_o10 §3 C2: if the behavioural separation does not replicate on the full book,
    # SINGLE_LEG_CODES is VOID and only the all-codes arm is reported, WITH NO VERDICT.
    c2_ok = bool(ctl["c2_separation_holds"])
    all_codes = tuple(sorted(set(TF.SINGLE_LEG_CODES) | set(TF.PACKAGE_CODES)))

    pkey = "lam%+.1f_h%s" % (TF.PRIMARY_LAMBDA, TF.PRIMARY_HORIZON_MIN)

    cells, per_day = run_o10(rows, ex)
    prim = cells.get(pkey)
    hv = halves(rows, per_day.get(pkey, []))
    prim_verdict = TF.o10_verdict(
        (hv["early"] or {}).get("npa_pp"), (hv["early"] or {}).get("fill_rate"),
        (hv["late"] or {}).get("npa_pp"), (hv["late"] or {}).get("fill_rate"))
    _log("O10 registered-primary %s: NPA %s pp, fill %s -> %s%s"
         % (pkey, None if not prim else round(prim["npa_pp"], 4),
            None if not prim else round(prim["fill_rate"], 4), prim_verdict,
            "" if c2_ok else "   [VOID: C2 failed]"))

    # The registered fallback arm, reported in full.
    cells_all, per_day_all = run_o10(rows, ex, codes=all_codes)
    prim_all = cells_all.get(pkey)
    hv_all = halves(rows, per_day_all.get(pkey, []))
    _log("O10 all-codes fallback %s: NPA %s pp, fill %s (NO VERDICT)"
         % (pkey, None if not prim_all else round(prim_all["npa_pp"], 4),
            None if not prim_all else round(prim_all["fill_rate"], 4)))

    o18 = run_o18(rows, ex)
    o18_all = run_o18(rows, ex, codes=all_codes)
    _log("O18 registered-primary rho %.4f verdict %s%s"
         % (o18.get("rho_size_weighted", float("nan")), o18.get("verdict"),
            "" if c2_ok else "   [VOID: C2 failed]"))
    _log("O18 all-codes fallback rho %.4f (NO VERDICT)"
         % o18_all.get("rho_size_weighted", float("nan")))

    payload = {
        "item": "O10 + O18",
        "prereg": ["PREREG_o10_passive_fills.md", "PREREG_o18_spread_cost.md"],
        "prereg_commit": "34b0c11",
        "book": "state_r2_splitclean.pkl",
        "n_book_rows": len(rows),
        "n_units_attempted": len(ex),
        "n_units_on_tape": len(ok),
        "coverage_note": ("units below MIN_PRINTS are excluded from the primary; see "
                          "o10.primary.n_contract_days"),
        "controls": ctl,
        "c4_coverage_primary": coverage_profile(rows, ex),
        "c4_coverage_all_codes": coverage_profile(rows, ex, codes=all_codes),
        "quote_staleness_diagnostic": stale,
        "c2_gate": {
            "separation_holds": c2_ok,
            "consequence": (
                "PREREG_o10 §3 C2 fired: SINGLE_LEG_CODES is VOID and only the all-codes arm is "
                "reported, WITH NO VERDICT for either item." if not c2_ok else
                "C2 held; the registered primary stands."),
            "void_note": (
                "The registered-primary blocks below are kept and stamped VOID rather than "
                "deleted, so nobody recomputes them later and quotes them as a verdict."),
            "process_defect": (
                "C2 and the outcome statistics were computed in the SAME pass, so it cannot be "
                "claimed that the control was read before the numbers. A gating control must run "
                "and be read in a separate pass; that is a flaw in this runner, not in the rule."),
        },
        "o10": {
            "primary_cell": pkey,
            "registered_primary_VOID" if not c2_ok else "primary": prim,
            "registered_primary_halves_VOID" if not c2_ok else "halves": hv,
            "registered_primary_verdict_VOID" if not c2_ok else "verdict": prim_verdict,
            "registered_primary_grid_VOID" if not c2_ok else "grid": cells,
            "fallback_all_codes_no_verdict": {
                "primary_cell": prim_all, "halves": hv_all, "grid": cells_all,
                "reading": ("this arm CREDITS package liquidity to a single-leg resting order, so "
                            "its fill rate is an OPTIMISTIC bound, as the register states"),
            },
        },
        "o18": {
            "registered_primary_VOID" if not c2_ok else "primary": o18,
            "fallback_all_codes_no_verdict": o18_all,
        },
        "verdict": "NO VERDICT - registered void condition C2 fired" if not c2_ok else None,
        "routing": ("NOTHING ADOPTED. DEFAULT_AGGRESSION stays %.1f; a material result is routed "
                    "to Don as a policy change." % F.DEFAULT_AGGRESSION),
        "does_not_rescue_r2": ("the random-entry control is filled by the identical rule, so a "
                               "cheaper entry moves both books and leaves the -5.0640pp gap"),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
