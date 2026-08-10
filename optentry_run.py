"""Roadmap 22c runner — diagnose the anti-predictive entry timing, then test nine corrections.

Three phases, each resumable and each banked per name so a kill leaves usable work:

    python optentry_run.py --data-root <repo>/data --iv-series      # daily ~60-DTE ATM IV
    python optentry_run.py --data-root <repo>/data --arms           # the nine arms + control
    python optentry_run.py --data-root <repo>/data --analyse-only

Read-only on the miner's `data/options/` cache; everything written goes to `data/options_entry/`.
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


def _init(data_root: str, aggression: float, iv_dir: str):
    from valuation.edge import options_universe as U
    from valuation.edge.theta_bulk import ThetaBulk
    _G["root"] = data_root
    _G["prov"] = ThetaBulk(root=os.path.join(data_root, "options"), max_years_in_memory=3)
    _G["bars_dir"] = os.path.join(data_root, "bulk", "prepared", "bars")
    _G["caps"] = U.load_caps(data_root)
    _G["aggression"] = aggression
    _G["iv_dir"] = iv_dir


def _iv_job(ticker: str):
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_entry as E
    t0 = time.time()
    if os.path.exists(E.iv_series_path(ticker, _G["iv_dir"])):
        return {"ticker": ticker, "n": -1, "seconds": 0.0, "cached": True}
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "n": 0, "seconds": time.time() - t0, "cached": False}
    ser = E.build_iv_series(_G["prov"], ticker, bars)
    E.save_iv_series(ticker, ser, _G["iv_dir"])
    return {"ticker": ticker, "n": len(ser), "seconds": time.time() - t0, "cached": False}


def _arms_job(arg):
    """One name: the frozen alert list, all nine arms, the control, and entry context on all."""
    ticker, draws, seed = arg
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_entry as E
    t0 = time.time()
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "arms": {}, "control": [], "no_entry": {},
                "overlaps": {}, "n_alert": 0, "rejects": {"no_bars": 1},
                "seconds": time.time() - t0}
    series = E.load_iv_series(ticker, _G["iv_dir"])
    # ONE memo for the whole name: the alert pass, all nine arms and the control all draw their
    # fills from it, so a day-and-right is picked and simulated exactly once.
    memo = {}
    got = E.alerts_for_name(_G["prov"], ticker, bars, _G["caps"],
                            aggression=_G["aggression"], memo=memo)
    alerts = got["alerts"]
    res = E.run_arms(_G["prov"], ticker, bars, series, alerts, _G["caps"],
                     aggression=_G["aggression"], memo=memo)
    arms = res["arms"]
    ctrl = E.random_entry_control(_G["prov"], ticker, bars, alerts, _G["caps"],
                                  draws=draws, seed=seed, aggression=_G["aggression"],
                                  memo=memo)
    for rows in list(arms.values()) + [ctrl]:
        E.annotate(rows, bars, series)
    return {"ticker": ticker, "arms": arms, "control": ctrl,
            "no_entry": res["no_entry"], "overlaps": res["overlaps"],
            "n_alert": got["n_alert"], "n_cand": got["n_cand"], "rejects": got["rejects"],
            "iv_days": len(series), "seconds": time.time() - t0}


def load_env(repo_root: str):
    """Bars come from Sharadar and need the key. Never printed, never written back."""
    path = os.path.join(repo_root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def pinned_universe(root: str, path: str | None) -> list:
    """The 22b name list, so 22c measures the same 187 names and not whatever the miner has
    cached since. A different universe would make every 22b comparison meaningless."""
    from valuation.edge import options_universe as U
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            names = list((pickle.load(f)["selection"])["universe"])
        print(f"[optentry] universe PINNED to {len(names)} names from {path}", flush=True)
        return names
    sel = U.universe_selection_report(root)
    return sel.get("universe") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--aggression", type=float, default=1.0)
    ap.add_argument("--iv-series", action="store_true", help="phase 1: build the ATM IV series")
    ap.add_argument("--arms", action="store_true", help="phase 2: the nine arms + control")
    ap.add_argument("--analyse-only", action="store_true")
    ap.add_argument("--control-draws", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--state", default=None)
    ap.add_argument("--universe-from", default=None)
    ap.add_argument("--limit", type=int, default=0, help="smoke test only; label it as one")
    ap.add_argument("--repo-root", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    load_env(a.repo_root)
    from valuation.edge import options_entry as E

    root = os.path.abspath(a.data_root)
    out_dir = os.path.join(root, "options_entry")
    iv_dir = os.path.join(out_dir, "iv_series")
    os.makedirs(iv_dir, exist_ok=True)
    state_path = a.state or os.path.join(out_dir, "state.pkl")

    names = pinned_universe(root, a.universe_from
                            or os.path.join(root, "options_universe", "state.pkl"))
    if not names:
        print("[optentry] no universe")
        return 1
    if a.limit:
        names = names[:a.limit]
        print(f"[optentry] SMOKE TEST: {a.limit} names only — not a verdict", flush=True)
    print(f"[optentry] universe {len(names)} names", flush=True)

    bars_dir = os.path.join(root, "bulk", "prepared", "bars")

    if a.iv_series:
        todo = [t for t in names if not os.path.exists(E.iv_series_path(t, iv_dir))]
        print(f"[optentry] IV series: {len(todo)} of {len(names)} names to build", flush=True)
        if todo:
            from multiprocessing import Pool
            t0, done = time.time(), 0
            with Pool(a.workers, initializer=_init,
                      initargs=(root, a.aggression, iv_dir)) as pool:
                for i, res in enumerate(pool.imap_unordered(_iv_job, todo), 1):
                    done += 1
                    if i % 10 == 0 or i == len(todo):
                        print(f"[optentry] iv {i}/{len(todo)} | last {res['ticker']} "
                              f"{res['n']} days | {(time.time()-t0)/60:.1f}m", flush=True)
        cov = {t: len(E.load_iv_series(t, iv_dir)) for t in names}
        empty = [t for t, n in cov.items() if n < 200]
        print(f"[optentry] IV series built for {len(names)} names, "
              f"median {sorted(cov.values())[len(cov)//2]} days, "
              f"{len(empty)} names under 200 days", flush=True)
        if empty:
            print(f"[optentry] thin IV coverage: {empty[:15]}", flush=True)

    state = {"arms": {}, "control": [], "done": [], "meta": {},
             "no_entry": {}, "overlaps": {}, "universe": names}
    if os.path.exists(state_path):
        try:
            with open(state_path, "rb") as f:
                prev = pickle.load(f)
            if isinstance(prev, dict) and "done" in prev:
                state = prev
                print(f"[optentry] resumed: {len(state['done'])} names, "
                      f"{sum(len(v) for v in state['arms'].values())} trades", flush=True)
        except (OSError, pickle.UnpicklingError):
            pass

    if a.arms:
        todo = [t for t in names if t not in set(state["done"])]
        missing_bars = [t for t in todo
                        if not os.path.exists(os.path.join(bars_dir, f"{t}.pkl"))]
        if missing_bars:
            print(f"[optentry] {len(missing_bars)} names lack cached bars — fetching", flush=True)
            from concurrent.futures import ThreadPoolExecutor

            from valuation.edge import options_backtest as OB
            with ThreadPoolExecutor(max_workers=8) as ex:
                list(ex.map(lambda x: OB.load_bars(x, cache_dir=bars_dir), missing_bars))

        def bank():
            tmp = state_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(state, f, protocol=5)
            os.replace(tmp, state_path)

        jobs = [(t, a.control_draws, a.seed) for t in todo]
        t0 = time.time()
        from multiprocessing import Pool
        with Pool(a.workers, initializer=_init,
                  initargs=(root, a.aggression, iv_dir)) as pool:
            for i, res in enumerate(pool.imap_unordered(_arms_job, jobs), 1):
                _absorb(state, res)
                if i % 3 == 0 or i == len(jobs):
                    bank()
                    _progress(state, i, len(jobs), t0)
        bank()

    arms_rows = state["arms"]
    if not arms_rows:
        print("[optentry] no trades — run --arms first")
        return 1
    print(f"\n[optentry] {len(state['done'])} names | "
          + " ".join(f"{k}={len(v)}" for k, v in sorted(arms_rows.items()))
          + f" control={len(state['control'])}", flush=True)

    res = E.analyse(arms_rows, state["control"],
                    meta={"n_names": len(state["done"]),
                          "no_entry": state["no_entry"], "overlaps": state["overlaps"],
                          "aggression": a.aggression, "control_draws": a.control_draws,
                          "control_seed": a.seed, "smoke_test": bool(a.limit),
                          "per_name": state["meta"]},
                    seed=a.seed)
    path = E.save(res, out_dir)
    # audit O16 follow-on: pin the chain bytes this book was scored against. Descriptive here;
    # blocking only on a replay (valuation/edge/options_freeze.py).
    try:
        from valuation.edge import options_freeze as FZ
        FZ.stamp_run(out_dir, os.path.basename(state_path), arms_rows)
    except Exception as e:                                               # noqa: BLE001
        print(f"[optentry] WARNING: chain stamp failed ({type(e).__name__}: {e})", flush=True)
    _print_headline(res)
    print(f"\nwritten: {path}", flush=True)
    return 0


def _absorb(state, res):
    for arm, rows in (res.get("arms") or {}).items():
        state["arms"].setdefault(arm, []).extend(rows)
    state["control"].extend(res.get("control") or [])
    state["done"].append(res["ticker"])
    for arm, d in (res.get("no_entry") or {}).items():
        tgt = state["no_entry"].setdefault(arm, {})
        for k, v in d.items():
            tgt[k] = tgt.get(k, 0) + v
    for arm, v in (res.get("overlaps") or {}).items():
        state["overlaps"][arm] = state["overlaps"].get(arm, 0) + v
    state["meta"][res["ticker"]] = {k: res.get(k) for k in
                                    ("n_cand", "n_alert", "rejects", "seconds", "iv_days")}


def _progress(state, i, n, t0):
    from valuation.edge.options_tracker import _stats
    parts = []
    for arm in ("signal", "delay5", "pullback", "iv_wait", "fade_put"):
        rows = state["arms"].get(arm) or []
        if rows:
            parts.append(f"{arm}={len(rows)}/{_stats(rows)['expectancy_pct']:+.3f}")
    print(f"[optentry] {i}/{n} names | " + " ".join(parts)
          + f" | ctrl={len(state['control'])} | {(time.time()-t0)/60:.1f}m", flush=True)


def _print_headline(res):
    print("\n================ 22c ENTRY TIMING (aggression 1.0) ================")
    b = res["signal_baseline"]["stats"]
    c = res["control"]["stats"]
    print(f"  signal   n={b['n']:>5}  exp={b['expectancy_pct']:+.4f}  pf={b['profit_factor']}  "
          f"P(tail)={b['p_tail_win']:.4f}")
    print(f"  control  n={c['n']:>5}  exp={c['expectancy_pct']:+.4f}  pf={c['profit_factor']}  "
          f"P(tail)={c['p_tail_win']:.4f}")
    p = res["control"]["paired_vs_signal"]
    if p.get("ok"):
        print(f"  paired signal-minus-control: {p['mean_diff']:+.4f} over {p['n_cells']} cells, "
              f"win {p['win_rate']:.1%}, sign z={p['sign_z']:+.2f}")

    print("\n---- Test 1: alert days vs random days (paired by name-year) ----")
    for feat, d in res["characterization"].items():
        if not d.get("ok"):
            continue
        pr = d["paired"]
        if not pr.get("ok"):
            continue
        print(f"  {feat:>18}  alert {d['median_alert']:+.4f}  random {d['median_random']:+.4f}  "
              f"paired {pr['mean_diff']:+.4f}  z={pr['sign_z']:+.2f}  "
              f"win {pr['win_rate']:.1%}")
    m = res["mechanism"]
    print(f"  MECHANISM: {m['label']}   iv={m['iv_features_confirming']}  "
          f"runup={m['runup_features_confirming']}")

    print("\n---- Tests 2-4: the corrected-entry arms (matched subset) ----")
    for arm, rep in res["arms"].items():
        ms = rep["vs_signal_matched"]
        g = res["gates"][arm]
        vc = (rep.get("vs_control") or {}).get("bootstrap") or {}
        print(f"  {arm:>14}  n={rep['n']:>5}  exp={rep['stats']['expectancy_pct']:+.4f}  "
              f"vs signal {(ms.get('expectancy_diff') or 0):+.4f} (matched {ms['n_matched']})  "
              f"vs control {(vc.get('diff') or 0):+.4f}  "
              f"halves={rep['held_out']['both_positive']}  PASS={g['passed']}")

    cs = res.get("control_stability") or {}
    print("\n---- is the anti-tilt stable? signal minus control ----")
    for half, d in (cs.get("by_half") or {}).items():
        if d.get("ok"):
            p = d.get("paired") or {}
            print(f"  {half:>6}  signal {d['signal_expectancy']:+.4f}  "
                  f"control {d['control_expectancy']:+.4f}  diff {d['diff']:+.4f}  "
                  f"cells {p.get('n_cells')}  win {p.get('win_rate')}  z={p.get('sign_z')}")
    print(f"  negative in both halves: {cs.get('negative_in_both_halves')}")

    print("\n---- E7: same-day context gates through the section-2 filter gate ----")
    for feat, d in (res.get("context_filters") or {}).items():
        if not d.get("ok"):
            print(f"  {feat:>14}  not testable: {d.get('reason')}")
            continue
        print(f"  {feat:>14}  kept {d['late_n_kept']}/{d['late_n_all']} "
              f"({d['retained']:.1%})  {d['late_exp_all']:+.4f} -> {d['late_exp_filtered']:+.4f}"
              f"  gain {d['late_gain']:+.4f}  early {d['early_gain']}  PASS={d['passed']}")

    print("\n---- E5: choose on one half, measure on the other ----")
    for k in ("decide_early", "decide_late"):
        d = res["holdout_arm_select"].get(k) or {}
        if d.get("ok"):
            print(f"  {k}: chose {d['chosen_arm']} (gain {d['gain_on_decide_half']:+.4f}) -> "
                  f"{d['measure_half']} gain {(d.get('gain_on_measure_half') or 0):+.4f}  "
                  f"beats control={d['beats_control_on_measure_half']}")
    print(f"  survives both directions: "
          f"{res['holdout_arm_select'].get('survives_both_directions')}")

    print("\n---- verdict ----")
    for k, v in res["verdict"].items():
        if k != "note":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
