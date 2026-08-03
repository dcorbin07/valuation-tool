"""OPTIONS_DEEP_RESEARCH thread #2 runner — the cross-section of one-month ATM straddle returns.

    python optxs_run.py --data-root <repo>/data --iv-series   # extend the 22c ATM-IV series
    python optxs_run.py --data-root <repo>/data --panel       # build the monthly straddle panel
    python optxs_run.py --data-root <repo>/data               # analyse the banked panel

Resumable and banked per name. Read-only on the miner's `data/options/`; writes to
`data/options_xsection/` and (shared, additive) `data/options_entry/iv_series/`.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
import warnings

warnings.filterwarnings("ignore")

_G = {}


def _init(data_root: str, iv_dir: str, market: dict, aggression: float):
    from valuation.edge.theta_bulk import ThetaBulk
    _G["prov"] = ThetaBulk(root=os.path.join(data_root, "options"), max_years_in_memory=3)
    _G["bars_dir"] = os.path.join(data_root, "bulk", "prepared", "bars")
    _G["iv_dir"] = iv_dir
    _G["market"] = market
    _G["aggression"] = aggression


def _iv_job(ticker: str):
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_entry as E
    if os.path.exists(E.iv_series_path(ticker, _G["iv_dir"])):
        return {"ticker": ticker, "n": -1}
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "n": 0}
    ser = E.build_iv_series(_G["prov"], ticker, bars)
    E.save_iv_series(ticker, ser, _G["iv_dir"])
    return {"ticker": ticker, "n": len(ser)}


def _panel_job(ticker: str):
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_entry as E
    from valuation.edge import options_xsection as X
    t0 = time.time()
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "rows": [], "skips": {"no_bars": 1},
                "seconds": time.time() - t0}
    iv = E.load_iv_series(ticker, _G["iv_dir"])
    out = X.build_name(_G["prov"], ticker, bars, _G["market"], iv,
                       aggression=_G["aggression"])
    out["seconds"] = time.time() - t0
    return out


def load_env(repo_root: str):
    path = os.path.join(repo_root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--aggression", type=float, default=1.0)
    ap.add_argument("--iv-series", action="store_true")
    ap.add_argument("--panel", action="store_true")
    ap.add_argument("--state", default=None)
    ap.add_argument("--limit", type=int, default=0, help="smoke test only; label it as one")
    ap.add_argument("--repo-root", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    load_env(a.repo_root)
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_universe as U
    from valuation.edge import options_xsection as X

    root = os.path.abspath(a.data_root)
    out_dir = os.path.join(root, "options_xsection")
    iv_dir = os.path.join(root, "options_entry", "iv_series")   # shared with 22c, additive
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(iv_dir, exist_ok=True)
    state_path = a.state or os.path.join(out_dir, "panel.pkl")
    bars_dir = os.path.join(root, "bulk", "prepared", "bars")

    state = {"rows": [], "done": [], "skips": {}, "universe": None}
    if os.path.exists(state_path):
        try:
            with open(state_path, "rb") as f:
                prev = pickle.load(f)
            if isinstance(prev, dict) and "done" in prev:
                state = prev
                print(f"[optxs] resumed: {len(state['done'])} names, "
                      f"{len(state['rows'])} straddles", flush=True)
        except (OSError, pickle.UnpicklingError):
            pass

    if state.get("universe"):
        names = state["universe"]
        print(f"[optxs] universe PINNED to {len(names)} names from the state file", flush=True)
    else:
        sel = U.universe_selection_report(root)
        if not sel.get("ok"):
            print(f"[optxs] {sel.get('reason')}")
            return 1
        names = sel["universe"]
        # The miner keeps adding names; freezing the list is what makes a resumed or re-run pass
        # score the SAME universe rather than a moving one.
        state["universe"] = names
        state["selection"] = {k: sel.get(k) for k in
                              ("n_evaluated", "n_universe", "n_skipped", "n_skipped_thin")}
        print(f"[optxs] universe {len(names)} complete names "
              f"({sel['n_skipped']} skipped, {sel['n_skipped_thin']} of them as thin)",
              flush=True)
    if a.limit:
        names = names[:a.limit]
        print(f"[optxs] SMOKE TEST: {a.limit} names only — not a verdict", flush=True)

    missing = [t for t in names if not os.path.exists(os.path.join(bars_dir, f"{t}.pkl"))]
    if missing:
        print(f"[optxs] fetching bars for {len(missing)} names ...", flush=True)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(lambda x: OB.load_bars(x, cache_dir=bars_dir), missing))

    if a.iv_series:
        from valuation.edge import options_entry as E
        todo = [t for t in names if not os.path.exists(E.iv_series_path(t, iv_dir))]
        print(f"[optxs] ATM-IV series: {len(todo)} of {len(names)} still to build "
              f"(the rest are reused from 22c)", flush=True)
        if todo:
            from multiprocessing import Pool
            t0 = time.time()
            with Pool(a.workers, initializer=_init,
                      initargs=(root, iv_dir, {}, a.aggression)) as pool:
                for i, res in enumerate(pool.imap_unordered(_iv_job, todo), 1):
                    if i % 10 == 0 or i == len(todo):
                        print(f"[optxs] iv {i}/{len(todo)} | last {res['ticker']} "
                              f"{res['n']} days | {(time.time()-t0)/60:.1f}m", flush=True)

    if a.panel:
        # The market proxy is the equal-weighted daily return of the universe, built ONCE in the
        # parent from every name's bars. No SPY: the Sharadar equity export carries no ETFs.
        print("[optxs] building the equal-weighted market proxy ...", flush=True)
        all_bars = {}
        for t in names:
            b = OB.load_bars(t, cache_dir=bars_dir)
            if b:
                all_bars[t] = b
        market = X.build_market(all_bars)
        print(f"[optxs] market proxy: {len(market)} days from {len(all_bars)} names", flush=True)
        del all_bars

        todo = [t for t in names if t not in set(state["done"])]

        def bank():
            tmp = state_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(state, f, protocol=5)
            os.replace(tmp, state_path)

        t0 = time.time()
        from multiprocessing import Pool
        with Pool(a.workers, initializer=_init,
                  initargs=(root, iv_dir, market, a.aggression)) as pool:
            for i, res in enumerate(pool.imap_unordered(_panel_job, todo), 1):
                state["rows"].extend(res.get("rows") or [])
                state["done"].append(res["ticker"])
                for k, v in (res.get("skips") or {}).items():
                    state["skips"][k] = state["skips"].get(k, 0) + v
                if i % 10 == 0 or i == len(todo):
                    bank()
                    print(f"[optxs] {i}/{len(todo)} names | {len(state['rows'])} straddles | "
                          f"{(time.time()-t0)/60:.1f}m", flush=True)
        bank()

    if not state["rows"]:
        print("[optxs] no panel — run --panel first")
        return 1

    res = X.analyse(state["rows"])
    res["selection"] = state.get("selection")
    res["skips"] = state["skips"]
    res["meta"] = {"n_names_scored": len(state["done"]), "aggression": a.aggression,
                   "smoke_test": bool(a.limit)}
    path = X.save(res, out_dir)
    _print(res)
    print(f"\nwritten: {path}", flush=True)
    return 0


def _print(res):
    from valuation.edge import options_xsection as X

    p = res["panel"]
    print("\n============ THREAD #2 — CROSS-SECTION OF 1-MONTH ATM STRADDLES ============")
    print(f"  {p['n_straddles']} straddles | {p['n_names']} names | {p['n_months']} months")
    print(f"  mean return {p['mean_return']:+.4f}  median {p['median_return']:+.4f}  "
          f"total losses {p['share_total_loss']:.1%}  median spread {p['median_spread_pct']:.4f}  "
          f"median DTE {p['median_dte']:.0f}")
    print(f"  coverage: " + "  ".join(f"{k}={v:.1%}" for k, v in p["coverage"].items()))

    print("\n---- quintile mean straddle returns (Q1 = LOW characteristic) ----")
    for c in X.CHAR_NAMES:
        ev = res["characteristics"][c]
        if not ev.get("ok"):
            print(f"  {c:>12}  not testable: {ev.get('reason')}")
            continue
        q = ev["quintile_mean_returns"]
        g = res["gate"][c]
        print(f"  {c:>12} " + " ".join(f"{x:+.3f}" for x in q)
              + f"  mono={ev['monotonicity']:+.2f}"
              + f"  Q1excess={ev['long_only_q1_excess']['mean']:+.4f}"
              + f" t={(ev['long_only_q1_excess'].get('t') or 0):+.2f}"
              + f"  months={ev['n_months']}"
              + f"  halves={ev['held_out_q1_excess']['both_positive']}"
              + f"  PASS={g['passed']}"
              + ("  CONTRADICTS-LIT" if g.get("contradicts_published_sign") else ""))

    print("\n---- long-short Q1-Q5 (RESEARCH STATISTIC ONLY — naked short leg, not investable) ----")
    for c in X.CHAR_NAMES:
        ev = res["characteristics"][c]
        if ev.get("ok"):
            ls = ev["long_short_NOT_INVESTABLE"]
            print(f"  {c:>12}  mean={ls.get('mean'):+.4f}  t={(ls.get('t') or 0):+.2f}  "
                  f"n={ls.get('n')}")

    print("\n---- multiplicity ----")
    for c, d in (res.get("fdr") or {}).items():
        print(f"  {c:>12}  p={d['p']:.4g}  discovery={d['discovery']}")
    pbo = res.get("pbo") or {}
    print(f"  PBO over the characteristic grid: "
          + (f"{pbo['pbo']:.3f} ({pbo['n_splits']} splits, passes={pbo['passes']})"
             if pbo.get("ok") else str(pbo.get("reason"))))

    print("\n---- verdict ----")
    for k, v in res["verdict"].items():
        if k != "note":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
