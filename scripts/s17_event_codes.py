"""S17 - test the remaining EVENTS codes as event-window signals.

Executes PREREG_s17_s19_events_mdna.md sections 1b, 1c and 2. NOTHING here may deviate from
that register; the arm set, the horizons, the statistic and the four significance legs are all
fixed there.

    python -m scripts.s17_event_codes --json data/free_analysis/S17_EVENT_CODES.json

C1 RUNS AND IS READ FIRST, IN ITS OWN PASS, and the run ABORTS before any arm is scored if the
event join does not reproduce the project's own decode. Session 26's defect was computing a
gating control and the outcomes in one pass, so that it could not be claimed the control was
read before the numbers.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _data_root(repo: str) -> str:
    """`data/` is gitignored, so a WORKTREE has none of it.

    Resolve up out of `.claude/worktrees/<name>` to the checkout that owns the licensed
    export rather than hardcoding a path or creating a junction — a junction has to be
    removed before the worktree is deleted or a recursive delete follows it into the
    Sharadar data. Reading by absolute path has no such hazard.
    """
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isdir(env):
        return env
    here = os.path.join(repo, "data")
    if os.path.isdir(os.path.join(here, "backtest", "prices")):
        return here
    p = repo
    for _ in range(6):
        p = os.path.dirname(p)
        cand = os.path.join(p, "data")
        if os.path.isdir(os.path.join(cand, "backtest", "prices")):
            return cand
    return here


DATA = _data_root(REPO)

# ----------------------------------------------------------------------------- #
#  REGISTERED CONSTANTS - changing any of these voids the item (register section 6.1)
# ----------------------------------------------------------------------------- #
ARM_CODES = ("91", "81", "34", "71", "52")      # five most frequent EXCLUDING 22
HORIZONS = (21, 63)                              # trading days
LOOKBACK_CAL_DAYS = 21                           # calendar days, strictly before the date
MIN_XSEC = 50                                    # scorable names required for a date to count
PRICE_FLOOR = 1.00                               # screener/settings.py
MIN_MARKET_CAP_MM = 50.0                         # screener/settings.py
N_PERM = 500
BH_Q = 0.05
DECODED_CODE = "22"
DECODE_TARGET_RATIO = 1.64                       # bulk.py:243-247
DECODE_TOL = 0.25                                # |ratio - 1.64| must be within this for C1

PRICES_DIR = os.path.join(DATA, "backtest", "prices")
EVENTS_PKL = os.path.join(DATA, "bulk", "prepared", "events.pkl")
DAILY_PKL = os.path.join(DATA, "bulk", "prepared", "daily.pkl")
CACHE = os.path.join(DATA, "free_analysis", "S17_PRICES.pkl")


def _log(m):
    print(f"[s17] {m}", flush=True)


# ----------------------------------------------------------------------------- #
#  loading
# ----------------------------------------------------------------------------- #
def load_prices(rebuild: bool = False) -> dict:
    """{ticker: (dates np.datetime64[], close float[])} - WHOLE series, never truncated.

    AUDIT B6: `price_history(days=...)` takes a per-ticker tail, which is what made the early
    cross-sections consist only of names that had already stopped trading. This reads the whole
    file and truncates nothing, pinned by control C3.
    """
    if os.path.exists(CACHE) and not rebuild:
        with open(CACHE, "rb") as f:
            return pickle.load(f)
    import csv
    out = {}
    files = sorted(os.listdir(PRICES_DIR))
    for i, fn in enumerate(files):
        if not fn.endswith(".csv"):
            continue
        tk = fn[:-4].upper()
        ds, cs = [], []
        with open(os.path.join(PRICES_DIR, fn), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d, c = r.get("date"), r.get("close")
                if not d or not c:
                    continue
                try:
                    v = float(c)
                except ValueError:
                    continue
                if v > 0:
                    ds.append(d)
                    cs.append(v)
        if len(ds) < 70:
            continue
        o = np.argsort(np.array(ds))
        out[tk] = (np.array(ds, dtype="datetime64[D]")[o], np.array(cs, dtype=float)[o])
        if (i + 1) % 500 == 0:
            _log(f"  prices {i + 1}/{len(files)}")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "wb") as f:
        pickle.dump(out, f, protocol=4)
    return out


def load_events() -> dict:
    with open(EVENTS_PKL, "rb") as f:
        return pickle.load(f)


def load_caps() -> dict:
    """{ticker: (dates, marketcap_mm)} from the monthly DAILY cache."""
    with open(DAILY_PKL, "rb") as f:
        d = pickle.load(f)
    out = {}
    for tk, rows in d.items():
        if not rows:
            continue
        ds, mc = [], []
        for r in rows:
            if r[0] and r[1] is not None:
                ds.append(r[0])
                mc.append(float(r[1]))
        if ds:
            o = np.argsort(np.array(ds))
            out[tk.upper()] = (np.array(ds, dtype="datetime64[D]")[o],
                               np.array(mc, dtype=float)[o])
    return out


# ----------------------------------------------------------------------------- #
#  statistics
# ----------------------------------------------------------------------------- #
def hac_t(x: np.ndarray, lag: int) -> tuple:
    """Newey-West t of the mean. Returns (t, mean, se, n)."""
    x = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    n = len(x)
    if n < 5:
        return float("nan"), float("nan"), float("nan"), n
    mu = float(x.mean())
    e = x - mu
    g0 = float(e @ e) / n
    s = g0
    for L in range(1, min(lag, n - 1) + 1):
        g = float(e[L:] @ e[:-L]) / n
        s += 2.0 * (1.0 - L / (lag + 1.0)) * g
    if s <= 0:
        return float("nan"), mu, float("nan"), n
    se = math.sqrt(s / n)
    return mu / se, mu, se, n


def benjamini_hochberg(pvals: list, q: float) -> list:
    """Return a boolean list: which hypotheses are rejected at FDR q."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    keep = [False] * m
    kmax = -1
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            kmax = rank
    for rank, i in enumerate(order, start=1):
        if rank <= kmax:
            keep[i] = True
    return keep


# ----------------------------------------------------------------------------- #
#  C1 - the gating control, run and read in its OWN pass
# ----------------------------------------------------------------------------- #
def control_c1(prices: dict, events: dict) -> dict:
    """Reproduce bulk.py's empirical decode: day-of median |return| by code vs baseline.

    bulk.py:243-247 measured code 22 at 2.121% against a 1.292% baseline (1.64x) over 17,996
    events on 372 tickers, and every other candidate at 0.84x-1.15x. A DIFFERENT universe is
    used here (the full 2,998-name price export), so the RATIO is the reproducible quantity,
    not the levels.
    """
    codes_of_interest = [DECODED_CODE] + list(ARM_CODES) + ["11", "57"]
    abs_by_code = {c: [] for c in codes_of_interest}
    baseline = []
    n_ev = {c: 0 for c in codes_of_interest}
    tick_ev = {c: set() for c in codes_of_interest}
    shared = [t for t in prices if t in events]
    for tk in shared:
        ds, cs = prices[tk]
        if len(ds) < 30:
            continue
        r = np.empty(len(cs), dtype=float)
        r[0] = np.nan
        r[1:] = cs[1:] / cs[:-1] - 1.0
        ar = np.abs(r)
        ok = np.isfinite(ar)
        baseline.append(ar[ok])
        pos = {}
        for d, codes in events[tk]:
            dd = np.datetime64(d, "D")
            i = int(np.searchsorted(ds, dd))
            if i >= len(ds) or ds[i] != dd or not ok[i]:
                continue
            for c in codes:
                if c in abs_by_code:
                    pos.setdefault(c, []).append(i)
        for c, idxs in pos.items():
            if idxs:
                abs_by_code[c].append(ar[np.array(idxs)])
                n_ev[c] += len(idxs)
                tick_ev[c].add(tk)
    base = np.concatenate(baseline) if baseline else np.array([])
    base_med = float(np.median(base)) if base.size else float("nan")
    out = {"baseline_median_abs_return": base_med,
           "baseline_n": int(base.size),
           "n_tickers_joined": len(shared),
           "by_code": {}}
    for c in codes_of_interest:
        if abs_by_code[c]:
            v = np.concatenate(abs_by_code[c])
            med = float(np.median(v))
            out["by_code"][c] = {"median_abs_return": med,
                                 "ratio_vs_baseline": med / base_med if base_med else None,
                                 "n_events_matched": n_ev[c],
                                 "n_tickers": len(tick_ev[c])}
    r22 = (out["by_code"].get(DECODED_CODE) or {}).get("ratio_vs_baseline")
    out["code22_ratio"] = r22
    out["target_ratio"] = DECODE_TARGET_RATIO
    out["tolerance"] = DECODE_TOL
    out["ok"] = bool(r22 is not None and abs(r22 - DECODE_TARGET_RATIO) <= DECODE_TOL)
    return out


# ----------------------------------------------------------------------------- #
#  panel construction
# ----------------------------------------------------------------------------- #
def month_end_grid(prices: dict) -> list:
    """Month-end TRADING dates from the union calendar of the whole price export."""
    seen = set()
    for ds, _ in prices.values():
        seen.update(ds.tolist())
    alld = np.array(sorted(seen), dtype="datetime64[D]")
    ym = alld.astype("datetime64[M]")
    last = {}
    for d, m in zip(alld, ym):
        last[m] = d               # ascending, so the final write per month is its last day
    return [last[m] for m in sorted(last)]


def build_panel(prices: dict, events: dict, caps: dict, grid: list) -> dict:
    """Per-date arrays of forward returns and per-code event indicators, post-screen."""
    grid_arr = np.array(grid, dtype="datetime64[D]")
    per_date = {str(d): {"tickers": [], "fwd": {h: [] for h in HORIZONS},
                         "ev": {c: [] for c in ARM_CODES}} for d in grid}
    screen_counts = {"no_price_row": 0, "penny_adj_close": 0, "no_cap": 0,
                     "nano_cap": 0, "kept": 0, "penny_only_marginal": 0}

    ev_dates = {}
    for tk, rows in events.items():
        by = {}
        for d, codes in rows:
            for c in codes:
                if c in ARM_CODES:
                    by.setdefault(c, []).append(d)
        if by:
            ev_dates[tk] = {c: np.array(sorted(v), dtype="datetime64[D]")
                            for c, v in by.items()}

    for tk, (ds, cs) in prices.items():
        idx = np.searchsorted(ds, grid_arr, side="right") - 1
        cap_ds, cap_v = caps.get(tk, (None, None))
        evt = ev_dates.get(tk, {})
        for gi, d in enumerate(grid_arr):
            i = int(idx[gi])
            if i < 0:
                screen_counts["no_price_row"] += 1
                continue
            # the entry row must be reasonably fresh, else the name is not trading
            if (d - ds[i]).astype(int) > 10:
                screen_counts["no_price_row"] += 1
                continue
            px = float(cs[i])
            cap_ok = False
            if cap_ds is not None:
                j = int(np.searchsorted(cap_ds, d, side="right")) - 1
                if j >= 0 and (d - cap_ds[j]).astype(int) <= 70:
                    cap_ok = cap_v[j] >= MIN_MARKET_CAP_MM
                    if not cap_ok:
                        screen_counts["nano_cap"] += 1
                        continue
                else:
                    screen_counts["no_cap"] += 1
                    continue
            else:
                screen_counts["no_cap"] += 1
                continue
            if px < PRICE_FLOOR:
                # NOTE: this is the SPLIT-ADJUSTED close, not the traded price. Reported
                # separately so its marginal effect over the cap floor is measurable.
                screen_counts["penny_adj_close"] += 1
                screen_counts["penny_only_marginal"] += 1
                continue
            fwd = {}
            for h in HORIZONS:
                k = i + h
                fwd[h] = (float(cs[k]) / px - 1.0) if k < len(cs) else float("nan")
            if not np.isfinite(fwd[max(HORIZONS)]):
                continue
            screen_counts["kept"] += 1
            slot = per_date[str(d)]
            slot["tickers"].append(tk)
            for h in HORIZONS:
                slot["fwd"][h].append(fwd[h])
            lo = d - np.timedelta64(LOOKBACK_CAL_DAYS, "D")
            for c in ARM_CODES:
                a = evt.get(c)
                if a is None:
                    slot["ev"][c].append(0)
                else:
                    # window [d - 21d, d) - STRICTLY before the rebalance date
                    lo_i = int(np.searchsorted(a, lo, side="left"))
                    hi_i = int(np.searchsorted(a, d, side="left"))
                    slot["ev"][c].append(1 if hi_i > lo_i else 0)
    return {"per_date": per_date, "screen": screen_counts}


def score_arm(per_date: dict, dates: list, code: str, h: int, rng) -> dict:
    """Per-date mean(event) - mean(non-event), HAC t, and its own permutation null."""
    diffs, obs_dates, n_ev_tot, n_tot = [], [], 0, 0
    perm = np.zeros(N_PERM, dtype=float)
    perm_acc = [[] for _ in range(N_PERM)]
    for d in dates:
        s = per_date[d]
        y = np.asarray(s["fwd"][h], dtype=float)
        e = np.asarray(s["ev"][code], dtype=int)
        ok = np.isfinite(y)
        y, e = y[ok], e[ok]
        if y.size < MIN_XSEC or e.sum() < 3 or e.sum() > y.size - 3:
            continue
        diffs.append(float(y[e == 1].mean() - y[e == 0].mean()))
        obs_dates.append(d)
        n_ev_tot += int(e.sum())
        n_tot += int(y.size)
        k = int(e.sum())
        for p in range(N_PERM):
            sel = rng.choice(y.size, size=k, replace=False)
            m = np.zeros(y.size, dtype=bool)
            m[sel] = True
            perm_acc[p].append(float(y[m].mean() - y[~m].mean()))
    lag = max(1, int(math.ceil(h / 21.0)))
    t, mu, se, n = hac_t(np.array(diffs), lag)
    for p in range(N_PERM):
        perm[p] = hac_t(np.array(perm_acc[p]), lag)[0]
    perm = perm[np.isfinite(perm)]
    p95 = float(np.percentile(np.abs(perm), 95)) if perm.size else float("nan")
    pval = (float((np.abs(perm) >= abs(t)).sum() + 1) / (perm.size + 1)
            if perm.size and np.isfinite(t) else float("nan"))
    return {"code": code, "horizon": h, "hac_t": t, "mean_diff_per_period": mu,
            "se": se, "n_dates": n, "hac_lag": lag,
            "event_rate": n_ev_tot / n_tot if n_tot else None,
            "perm_p95_abs_t": p95, "perm_two_sided_p": pval,
            "clears_own_p95": bool(np.isfinite(t) and abs(t) > p95),
            "dates_used": obs_dates}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DATA, "free_analysis",
                                                   "S17_EVENT_CODES.json"))
    ap.add_argument("--rebuild-prices", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(20260813)

    _log("loading prices (whole series, never truncated - audit B6)")
    prices = load_prices(rebuild=a.rebuild_prices)
    _log(f"  {len(prices):,} tickers")
    _log("loading events")
    events = load_events()
    _log("loading market caps")
    caps = load_caps()

    # ---- C1 FIRST, IN ITS OWN PASS, AND THE RUN ABORTS IF IT FAILS -----------------
    _log("C1: reproducing the empirical decode BEFORE any arm is scored")
    c1 = control_c1(prices, events)
    _log(f"  code 22 ratio {c1['code22_ratio']:.4f} vs target {DECODE_TARGET_RATIO} "
         f"(baseline {c1['baseline_median_abs_return']:.5f}, "
         f"{c1['by_code'][DECODED_CODE]['n_events_matched']:,} events)")
    for c in ARM_CODES:
        b = c1["by_code"].get(c)
        if b:
            _log(f"  code {c}: {b['ratio_vs_baseline']:.3f}x "
                 f"({b['n_events_matched']:,} events)")
    if not c1["ok"]:
        _log("C1 FAILED - the event join does not reproduce the decode. "
             "Every S17 arm is VOID per register section 6.2. Aborting before any arm is scored.")
        os.makedirs(os.path.dirname(a.json), exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"item": "S17", "aborted": True, "controls": {"C1": c1}}, f, indent=2)
        return 2
    _log("C1 PASSED")

    # ---- panel -------------------------------------------------------------------
    grid = month_end_grid(prices)
    _log(f"month-end grid: {len(grid)} dates {grid[0]} -> {grid[-1]}")
    built = build_panel(prices, events, caps, grid)
    per_date = built["per_date"]
    usable = [d for d in sorted(per_date)
              if len(per_date[d]["tickers"]) >= MIN_XSEC
              and np.isfinite(np.asarray(per_date[d]["fwd"][max(HORIZONS)],
                                         dtype=float)).sum() >= MIN_XSEC]
    sizes = [len(per_date[d]["tickers"]) for d in usable]
    _log(f"usable dates {len(usable)} ({usable[0]} -> {usable[-1]}), "
         f"cross-section median {int(np.median(sizes))} max {max(sizes)}")

    half = len(usable) // 2
    halves = {"early_half": usable[:half], "late_half": usable[half:]}

    arms, pvals, keys = {}, [], []
    for c in ARM_CODES:
        for h in HORIZONS:
            k = f"code{c}@{h}d"
            _log(f"arm {k}")
            full = score_arm(per_date, usable, c, h, rng)
            hv = {}
            for hn, hd in halves.items():
                r = score_arm(per_date, hd, c, h, rng)
                r.pop("dates_used", None)
                hv[hn] = r
            full.pop("dates_used", None)
            same_sign = (np.sign(hv["early_half"]["hac_t"])
                         == np.sign(hv["late_half"]["hac_t"]))
            both = bool(same_sign and hv["early_half"]["clears_own_p95"]
                        and hv["late_half"]["clears_own_p95"])
            arms[k] = {"full_sample": full, "halves": hv,
                       "halves_same_sign": bool(same_sign),
                       "both_halves_clear": both}
            pvals.append(full["perm_two_sided_p"])
            keys.append(k)
            _log(f"  t {full['hac_t']:+.4f} vs own p95 {full['perm_p95_abs_t']:.4f}, "
                 f"p {full['perm_two_sided_p']:.5f}, both-halves {both}")

    bh = benjamini_hochberg([p if np.isfinite(p) else 1.0 for p in pvals], BH_Q)
    for k, ok in zip(keys, bh):
        arms[k]["survives_bh_q05"] = bool(ok)
        a_ = arms[k]
        a_["verdict"] = ("POSITIVE" if (a_["full_sample"]["clears_own_p95"] and ok
                                        and a_["both_halves_clear"]) else "NULL")

    # ---- C7: is the permutation null calibrated? ----------------------------------
    null_t = []
    for _ in range(200):
        d0 = usable[int(rng.integers(0, len(usable)))]
        s = per_date[d0]
        y = np.asarray(s["fwd"][HORIZONS[0]], dtype=float)
        y = y[np.isfinite(y)]
        k = max(3, int(0.05 * y.size))
        sel = rng.choice(y.size, size=k, replace=False)
        m = np.zeros(y.size, dtype=bool)
        m[sel] = True
        null_t.append(float(y[m].mean() - y[~m].mean()))
    payload = {
        "item": "S17",
        "register": "PREREG_s17_s19_events_mdna.md",
        "arm_codes": list(ARM_CODES), "horizons": list(HORIZONS),
        "n_perm": N_PERM, "bh_q": BH_Q,
        "coverage": {
            "grid_dates": len(grid), "usable_dates": len(usable),
            "first_date": usable[0], "last_date": usable[-1],
            "xsec_median": int(np.median(sizes)), "xsec_min": int(min(sizes)),
            "xsec_max": int(max(sizes)),
            "tickers_with_prices": len(prices),
            "screen": built["screen"],
            "half_split": {k: {"n": len(v), "first": v[0], "last": v[-1]}
                           for k, v in halves.items()},
        },
        "controls": {"C1_reproduces_empirical_decode": c1,
                     "C7_null_dispersion_sd": float(np.std(null_t))},
        "arms": arms,
        "any_positive": any(v["verdict"] == "POSITIVE" for v in arms.values()),
    }
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    _log(f"wrote {a.json}")
    _log(f"POSITIVE arms: {[k for k, v in arms.items() if v['verdict'] == 'POSITIVE'] or 'NONE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
