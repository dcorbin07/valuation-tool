"""DIP-CALL step 1 — THE ARM. Refuses to run without a passing kill artifact.

Register: `PREREG_dipcall.md`, committed ALONE at `c5e0b31`. Trials booked at `a984ec9`
(equity 274 -> 278) BEFORE any runner existed.

FOUR ARMS: 2 news arms (A1) x 2 co-primary horizons (5, 21). Each carries its OWN verdict (A5).
Horizons 63 and 126 are SENSITIVITIES CARRYING NO VERDICT (section 1) and are computed without a
permutation bar, because the register states in advance that power dies there and that they are
where `V6` and `DC-1` already looked.

THE PASS CONDITION IS SECTION 2f's CONJUNCTION and is not restated loosely here: positive, at
least +0.67pp, clearing the within-date permutation p95 AND the derived hurdle under BOTH
clustering readings, in BOTH halves with the same sign, under BOTH abnormal-return definitions, on
the $10B tier, surviving BH at q = 0.10 with k = 10.

ONE IMPLEMENTATION DECISION BEYOND THE MODULE'S THREE, and it runs TOWARD keeping rows rather than
dropping them. The kill pass required the horizon to end inside the name's OWN surviving series,
which silently drops the final events of a name that DELISTS -- the survivor filtering section 2e
forbids. The arm therefore uses a GLOBAL session calendar: an event qualifies for horizon `h` if
its date is at or before the date `h` sessions before the end of the build quadrant, and the
forward return is then taken as `A11` requires -- TERMINAL (`last_close / c0 - 1`) when `ACTIONS`
records a delisting, bankruptcy, regulatory or voluntary delisting, acquisition or merger, and
ADMINISTRATIVELY CENSORED (dropped and COUNTED) otherwise. The arm's event set is therefore a
SUPERSET of the kill pass's, so `K1`'s floor was met on a strictly conservative count and no bar
is relaxed. Both counts ship.

THIS FILE WAS SHIPPED COMPLETE AND **NEVER RUN** (`MB1-SEL`'s precedent). `K1` fired on
2026-10-08 -- the news arms carry 614 and 1,049 events against a pre-committed 1,500 floor -- so
the gate below refused and no abnormal return was ever computed. **Two things a successor must
know before running it, because an un-run script's defects are invisible:**

  1. **IT IS NOT VALIDATED ON REAL DATA.** Only its gate and its helpers are under test
     (`tests/test_dipcall.py`); the scoring path has never executed against the panel. Treat the
     first run as an instrument build, with controls, not as a measurement.
  2. **THE PERMUTATION POOL IS BUILT IN PYTHON DICTS OF LISTS, ONE ENTRY PER ELIGIBLE NAME-DAY.**
     On the TIER (~639k name-days) that is fine. On the FULL half-0 universe it is ~6.2M entries
     per (horizon x definition) and wants vectorising to numpy before anyone runs it. Reported
     rather than fixed, because this arm is dead under the register that commissioned it and a
     successor needs its own register with possibly different arms.

Usage:  python -m scripts.dipcall_arm [--k 2.5] [--draws 500]
"""
import argparse
import io
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import power_gate, research_log                           # noqa: E402
from valuation.edge.event_spine import EventSpine                             # noqa: E402
from valuation.edge.statistics import benjamini_hochberg, hlz_hurdle          # noqa: E402
from valuation.studies import dipcall as D                                    # noqa: E402

ART = "DIPCALL_ARM.json"
KILLS = "DIPCALL_KILLS.json"


# ---------------------------------------------------------------------------------- the gate
def require_kills() -> dict:
    """REFUSES without a passing kill artifact, and the two refusal states are DISTINCT.

    `E-1`'s lesson: a hard-coded refusal cannot tell "the control never ran" from "the control
    ran and fired", and those are different facts about the program.
    """
    p = D.out_path(KILLS)
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: %s is ABSENT. The free pre-outcome kill pass has not been run, which is a "
            "different state from it having fired. Run `python -m scripts.dipcall_kills` first "
            "and READ it -- O10's process defect was a gating control and its outcomes sharing "
            "one pass." % p)
    with io.open(p, encoding="utf-8") as fh:
        k = json.load(fh)
    if not k.get("all_kills_pass"):
        fired = [g for g, v in (k.get("gates") or {}).items() if not v]
        raise SystemExit(
            "REFUSING: the kill pass RAN and FIRED on %s. Section 2g: a kill firing stops the "
            "program at zero further trials and is the cheapest good outcome available to it. "
            "The bars may not be relaxed after watching them fail (W-28)." % ", ".join(fired))
    return k


# -------------------------------------------------------------- A8 the half-0 market series
def build_market_and_series(k: float) -> tuple:
    """One pass over the price files. Returns (series, market, calendar, actions_terminal).

    A8: the market leg is the CAP-WEIGHTED daily return of half-0 panel names with price files,
    2009-2019 only, weights from the most recent PRIOR quarterly `market_cap`. Built from half 0
    alone because the whole universe would read `2009-2019 x half 1`, a different cell of the
    charter's 2x2 whose budget allocates it to nothing. `X1` is what licenses the proxy: halving
    the universe moved the centre of 200 half-books not at all.
    """
    sched = D.tier_schedule()
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    bq = panel[(panel["date"] >= "2009") & (panel["date"] <= D.BUILD_HI)]
    half0 = sorted(set(bq[bq["ticker"].map(D.stable_key_half) == 0]["ticker"]))

    series = {}
    num, den = {}, {}
    t0 = time.time()
    for i, t in enumerate(half0):
        f = D.name_frame(t, sched.get(t, []), k=k)
        if f is None:
            continue
        # The cap at each session, from the most recent PRIOR quarterly observation.
        caps = _cap_at(sched.get(t, []), f["date"].tolist())
        series[t] = {
            "dates": f["date"].tolist(),
            "close": f["close"].to_numpy(dtype=float),
            "ret": f["ret"].to_numpy(dtype=float),
            "vol": f["vol"].to_numpy(dtype=float),
            "z": f["z"].to_numpy(dtype=float),
            "scoreable": f["scoreable"].to_numpy(),
            "event": f["event"].to_numpy(),
            "tier": f["tier"].to_numpy(),
        }
        inb = np.array([D.BUILD_LO <= d <= D.BUILD_HI for d in f["date"].tolist()])
        r = f["ret"].to_numpy(dtype=float)
        ok = inb & np.isfinite(r) & np.isfinite(caps) & (caps > 0)
        for d, w, rr in zip(np.asarray(f["date"].tolist())[ok], caps[ok], r[ok]):
            num[d] = num.get(d, 0.0) + float(w) * float(rr)
            den[d] = den.get(d, 0.0) + float(w)
        if i and i % 500 == 0:
            print("  %d/%d names, %.0fs" % (i, len(half0), time.time() - t0))

    cal = sorted(den)
    mkt = np.array([num[d] / den[d] for d in cal], dtype=float)
    market = {"dates": cal, "ret": mkt,
              "index": {d: j for j, d in enumerate(cal)}}
    print("  market: %d sessions %s..%s, cap-weighted, half-0 only"
          % (len(cal), cal[0], cal[-1]))
    return series, market, half0


def _cap_at(schedule_for_name, dates) -> np.ndarray:
    """Most recent PRIOR quarterly market cap at each session date (A12's convention)."""
    out = np.full(len(dates), np.nan)
    if not schedule_for_name:
        return out
    pdates = np.array([x[0] for x in schedule_for_name], dtype=object)
    caps = np.array([x[1] for x in schedule_for_name], dtype=float)
    idx = np.searchsorted(pdates, np.asarray(dates, dtype=object), side="right") - 1
    ok = idx >= 0
    out[ok] = caps[idx[ok]]
    return out


def terminal_names() -> set:
    """A11. Names whose series ending is a TERMINAL value rather than an administrative censor."""
    a = pd.read_csv(D.actions_csv(), usecols=["date", "action", "ticker"], low_memory=False)
    a = a[a["action"].isin(D.TERMINAL_ACTIONS)]
    return set(a["ticker"].astype(str))


# --------------------------------------------------------------- abnormal returns, per name
def abnormal(series_t: dict, market: dict, h: int, terminal: bool) -> tuple:
    """Per-session forward abnormal returns for ONE name at horizon `h`.

    Returns (ar_own, ar_mkt, usable, terminal_used). Entry at the CLOSE of session t; the horizon
    runs over sessions t+1 .. t+h (A9). The own-normal leg subtracts `h x` the mean daily return
    over the SAME strictly-prior 60-session window the volatility scale uses.
    """
    c = series_t["close"]
    r = series_t["ret"]
    n = len(c)
    fwd = np.full(n, np.nan)
    end = np.arange(n) + h
    inside = end < n
    fwd[inside] = c[end[inside]] / c[np.arange(n)[inside]] - 1.0
    term_used = np.zeros(n, dtype=bool)
    if terminal and n:
        # A11: a DELISTED name has a terminal value -- a last close is not a short window, it is
        # the value of a security that ceased to exist. `E-5` verified this reproduces the panel's
        # own `fwd_ret` at max |delta| 0.000e+00 on 591 of 591 such rows.
        tail = ~inside
        fwd[tail] = c[n - 1] / c[np.arange(n)[tail]] - 1.0
        term_used[tail] = True

    # The name's own "normal" return: the trailing-window mean daily return, strictly prior.
    mu = pd.Series(r).rolling(D.VOL_WIN, min_periods=D.MIN_VOL_OBS).mean().shift(1).to_numpy()
    ar_own = fwd - h * mu

    # The market leg over EXACTLY the same window (A9), compounded on the global calendar.
    mi = market["index"]
    mr = market["ret"]
    md = market["dates"]
    cum = np.concatenate([[0.0], np.cumsum(np.log1p(np.clip(mr, -0.95, None)))])
    ar_mkt = np.full(n, np.nan)
    dates = series_t["dates"]
    for i in range(n):
        j = mi.get(dates[i])
        if j is None:
            continue
        j2 = j + h
        if j2 >= len(md):
            continue
        rm = math.expm1(cum[j2 + 1] - cum[j + 1])
        if np.isfinite(fwd[i]):
            ar_mkt[i] = fwd[i] - rm

    usable = np.isfinite(fwd)
    return ar_own, ar_mkt, usable, term_used


# ------------------------------------------------------------------------ clustered inference
def clustered(y: np.ndarray, groups: np.ndarray) -> tuple:
    """(mean, se, t, n_clusters) with a cluster-robust standard error of the MEAN.

    `se^2 = G/(G-1) * sum_g (sum_{i in g} (y_i - ybar))^2 / n^2`, the standard cluster-robust
    variance of a sample mean with the usual small-cluster correction. A2: date-clustering
    absorbs the same-day shock the census identified; name-clustering absorbs the OTHER
    dependence in this design, one name's overlapping windows, which no date-clustered se can
    see (`R9`'s +0.189 lag-1 autocorrelation, through a name rather than a date).
    """
    n = len(y)
    if n < 3:
        return float("nan"), float("nan"), float("nan"), 0
    ybar = float(np.mean(y))
    e = y - ybar
    _, inv = np.unique(groups, return_inverse=True)
    g = int(inv.max()) + 1
    sums = np.bincount(inv, weights=e, minlength=g)
    if g < 2:
        return ybar, float("nan"), float("nan"), g
    var = (g / (g - 1.0)) * float(np.sum(sums ** 2)) / (n ** 2)
    se = math.sqrt(var) if var > 0 else float("nan")
    t = (ybar / se) if se and np.isfinite(se) and se > 0 else float("nan")
    return ybar, se, t, g


def permutation_p95(pool_by_date: dict, counts_by_date: dict, draws: int, seed: int) -> tuple:
    """A2 leg 3. The event flag shuffled across names WITHIN each date, preserving each date's
    event count exactly, `draws` times. Returns (p95, p05, mean_of_null, n_draws)."""
    rng = np.random.default_rng(seed)
    dates = [d for d in counts_by_date if d in pool_by_date and
             len(pool_by_date[d]) >= counts_by_date[d] > 0]
    if not dates:
        return float("nan"), float("nan"), float("nan"), 0
    pools = [pool_by_date[d] for d in dates]
    ks = [counts_by_date[d] for d in dates]
    tot = float(sum(ks))
    out = np.empty(draws, dtype=float)
    for s in range(draws):
        acc = 0.0
        for pool, kk in zip(pools, ks):
            idx = rng.choice(len(pool), size=kk, replace=False)
            acc += float(pool[idx].sum())
        out[s] = acc / tot
    out.sort()
    return (float(out[int(0.95 * (draws - 1))]), float(out[int(0.05 * (draws - 1))]),
            float(out.mean()), draws)


def two_sided_p(t: float) -> float:
    """A6. TWO-SIDED, because A5's two arms have OPPOSITE predicted signs (Chan 2003 reversal vs
    Savor 2012 drift), so no uniform one-sided direction can be declared."""
    if not np.isfinite(t):
        return float("nan")
    return float(math.erfc(abs(t) / math.sqrt(2.0)))


# --------------------------------------------------------------------------------- the arm
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=float, default=D.K_PRIMARY)
    ap.add_argument("--draws", type=int, default=D.PERMUTATION_DRAWS)
    a = ap.parse_args()

    kills = require_kills()
    n_eq = research_log.trial_count(domain="equity")
    crit = hlz_hurdle(n_eq)
    print("DIP-CALL step 1 ARM. kill pass PASSED. equity N = %d ; hurdle %.7f" % (n_eq, crit))
    print("k = %.1f ; permutation draws %d ; every critical value LABELLED UNCALIBRATED\n"
          % (a.k, a.draws))

    print("building the half-0 cap-weighted market and the name series (A8) ...")
    series, market, half0 = build_market_and_series(a.k)
    term = terminal_names()

    # The global session calendar decides horizon eligibility, so a DELISTED name's final events
    # stay in the sample (section 2e / A11) instead of being silently dropped.
    cal_dates = market["dates"]
    last_build = len(cal_dates) - 1
    cutoff = {h: cal_dates[max(0, last_build - h)]
              for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY}
    print("  horizon cutoffs (global calendar): %s\n"
          % {("h%d" % h): cutoff[h] for h in sorted(cutoff)})

    print("classifying news (A1) ...")
    names = sorted(series)
    spine = EventSpine.build(names=names, csv_path=D.events_csv())
    ann = {}
    for t in names:
        d2i = {d: j for j, d in enumerate(series[t]["dates"])}
        ann[t] = D.announce_sessions(spine, t, d2i)

    rows = {}        # (pop, h, arm, half) -> lists
    pool = {}        # (pop, h, defn, date) -> list of AR values for the permutation
    censored = {"administrative_dropped": 0, "terminal_used": 0}
    t0 = time.time()
    for i, t in enumerate(names):
        s = series[t]
        dates = s["dates"]
        inb = np.array([D.BUILD_LO <= d <= D.BUILD_HI for d in dates])
        is_term = t in term
        for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
            ar_own, ar_mkt, usable, term_used = abnormal(s, market, h, is_term)
            elig = inb & s["scoreable"] & np.array([d <= cutoff[h] for d in dates])
            good = elig & usable & np.isfinite(ar_own) & np.isfinite(ar_mkt)
            censored["administrative_dropped"] += int((elig & ~usable).sum())
            censored["terminal_used"] += int((good & term_used).sum())
            ev = good & s["event"]
            # The permutation pool is every ELIGIBLE scoreable name-day, event or not.
            for pop in ("tier", "full"):
                m = good & (s["tier"] if pop == "tier" else True)
                if not m.any():
                    continue
                for defn, arr in (("own", ar_own), ("mkt", ar_mkt)):
                    if h not in D.HORIZONS_PRIMARY:
                        continue
                    key = (pop, h, defn)
                    pb = pool.setdefault(key, {})
                    for d, v in zip(np.asarray(dates)[m], arr[m]):
                        pb.setdefault(d, []).append(float(v))
                mm = ev & (s["tier"] if pop == "tier" else True)
                if not mm.any():
                    continue
                cls = [D.news_class(spine, t, j, ann.get(t))
                       for j in np.arange(len(dates))[mm]]
                for j, cl in zip(np.arange(len(dates))[mm], cls):
                    if cl == D.UNKNOWN:
                        continue          # A1b: excluded by name, never read as "no news"
                    if D.crosses_boundary(dates, j, h):
                        continue          # section 2d: the boundary is EMBARGOED
                    half = D.half_of(dates[j])
                    rows.setdefault((pop, h, cl, half), []).append(
                        (dates[j], t, float(ar_own[j]), float(ar_mkt[j])))
        if i and i % 500 == 0:
            print("  %d/%d names, %.0fs" % (i, len(names), time.time() - t0))

    print("  arm rows built in %.0fs\n" % (time.time() - t0))

    # --------------------------------------------------------------------- score each cell
    cells = {}
    for (pop, h, arm, half), v in sorted(rows.items()):
        dts = np.array([x[0] for x in v], dtype=object)
        tks = np.array([x[1] for x in v], dtype=object)
        for defn, col in (("own", 2), ("mkt", 3)):
            y = np.array([x[col] for x in v], dtype=float) * 100.0   # percentage points
            m_d, se_d, t_d, g_d = clustered(y, dts)
            m_n, se_n, t_n, g_n = clustered(y, tks)
            cells["%s|h%d|%s|%s|%s" % (pop, h, arm, half, defn)] = {
                "n": int(len(y)), "mean_pp": m_d,
                "date_clustered": {"se_pp": se_d, "t": t_d, "clusters": g_d,
                                   "p_two_sided": two_sided_p(t_d)},
                "name_clustered": {"se_pp": se_n, "t": t_n, "clusters": g_n,
                                   "p_two_sided": two_sided_p(t_n)},
                "median_pp": float(np.median(y)),
                "realised_sd_pp": float(np.std(y, ddof=1)) if len(y) > 1 else None,
            }

    # ------------------------------------------- full-sample cells, permutation bar and MDE
    full_cells = {}
    for pop in ("tier", "full"):
        for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
            for arm in (D.NEWS, D.NO_NEWS):
                v = rows.get((pop, h, arm, "early"), []) + rows.get((pop, h, arm, "late"), [])
                if len(v) < 10:
                    continue
                dts = np.array([x[0] for x in v], dtype=object)
                tks = np.array([x[1] for x in v], dtype=object)
                cnt = {}
                for d in dts:
                    cnt[d] = cnt.get(d, 0) + 1
                entry = {"n": int(len(v))}
                for defn, col in (("own", 2), ("mkt", 3)):
                    y = np.array([x[col] for x in v], dtype=float) * 100.0
                    m_d, se_d, t_d, g_d = clustered(y, dts)
                    m_n, se_n, t_n, g_n = clustered(y, tks)
                    rec = {"mean_pp": m_d, "median_pp": float(np.median(y)),
                           "realised_sd_pp": float(np.std(y, ddof=1)),
                           "date_clustered": {"se_pp": se_d, "t": t_d, "clusters": g_d,
                                              "p_two_sided": two_sided_p(t_d)},
                           "name_clustered": {"se_pp": se_n, "t": t_n, "clusters": g_n,
                                              "p_two_sided": two_sided_p(t_n)}}
                    # MB8 / RUN_RULES rule 11: the MDE from the arm's OWN measured se, both
                    # powers, never one quoted as the other.
                    for lbl, se in (("date", se_d), ("name", se_n)):
                        if se and np.isfinite(se) and se > 0:
                            rec["mde_%s_clustered" % lbl] = {
                                "detection_threshold_50pc_power":
                                    power_gate.detection_threshold(se, n_trials=n_eq),
                                "mde_80pc_power": (crit + power_gate.Z_POWER_CONVENTION) * se,
                                "power_against_economic_floor":
                                    power_gate.power_at(D.ECONOMIC_FLOOR_PP, se, n_trials=n_eq),
                            }
                    if h in D.HORIZONS_PRIMARY:
                        pb = pool.get((pop, h, defn), {})
                        pb_arr = {d: np.array(x, dtype=float) * 100.0 for d, x in pb.items()}
                        p95, p05, nmean, nd = permutation_p95(pb_arr, cnt, a.draws, 0)
                        rec["permutation"] = {"p95": p95, "p05": p05, "null_mean": nmean,
                                              "draws": nd,
                                              "clears_p95": bool(np.isfinite(p95)
                                                                 and m_d > p95)}
                    entry[defn] = rec
                full_cells["%s|h%d|%s" % (pop, h, arm)] = entry

    # ------------------------------------------------------------------- section 2f verdict
    verdicts = {}
    bh_input = []
    for h in D.HORIZONS_PRIMARY:
        for arm in (D.NEWS, D.NO_NEWS):
            key = "tier|h%d|%s" % (h, arm)
            fc = full_cells.get(key)
            label = "h%d|%s" % (h, arm)
            if not fc:
                verdicts[label] = {"verdict": "NOT ASSESSABLE", "why": "no tier rows"}
                continue
            checks, detail = {}, {}
            for defn in ("own", "mkt"):
                r = fc[defn]
                e = {}
                e["positive"] = bool(r["mean_pp"] > 0)
                e["economic_floor"] = bool(r["mean_pp"] >= D.ECONOMIC_FLOOR_PP)
                e["date_clustered_t"] = bool(abs(r["date_clustered"]["t"]) > crit)
                e["name_clustered_t"] = bool(abs(r["name_clustered"]["t"]) > crit)
                e["permutation"] = bool(r.get("permutation", {}).get("clears_p95"))
                hv = {}
                for half in ("early", "late"):
                    c = cells.get("tier|h%d|%s|%s|%s" % (h, arm, half, defn))
                    hv[half] = (None if c is None else
                                {"n": c["n"], "mean_pp": c["mean_pp"],
                                 "t_date": c["date_clustered"]["t"],
                                 "t_name": c["name_clustered"]["t"]})
                e["both_halves_same_sign"] = bool(
                    hv["early"] and hv["late"]
                    and hv["early"]["mean_pp"] > 0 and hv["late"]["mean_pp"] > 0)
                e["both_halves_clear_floor"] = bool(
                    hv["early"] and hv["late"]
                    and hv["early"]["mean_pp"] >= D.ECONOMIC_FLOOR_PP
                    and hv["late"]["mean_pp"] >= D.ECONOMIC_FLOOR_PP)
                checks[defn] = e
                detail[defn] = {"halves": hv}
            passed = all(all(v.values()) for v in checks.values())
            # The BH p is the LARGER (more conservative) of the two clustering readings on the
            # own-normal definition, declared here rather than chosen afterwards.
            p_bh = max(fc["own"]["date_clustered"]["p_two_sided"],
                       fc["own"]["name_clustered"]["p_two_sided"])
            bh_input.append((label, p_bh))
            verdicts[label] = {"verdict": "PASSES SECTION 2f PRE-BH" if passed else "FAILS",
                               "checks": checks, "halves": detail, "p_for_bh": p_bh}

    # BH at q = 0.10 with k = 10 FIXED (section 7): a cell that cannot be built is NOT RUN and
    # `k` stays 10, because shrinking it makes every surviving threshold easier.
    bh_input.sort(key=lambda x: (x[1] if x[1] == x[1] else 1.0))
    bh = []
    for i, (label, p) in enumerate(bh_input, start=1):
        thr = i * D.BH_Q / D.BH_K
        bh.append({"rank": i, "arm": label, "p_two_sided": p, "bh_threshold": thr,
                   "survives": bool(p == p and p <= thr)})
    bh_ok = {x["arm"]: x["survives"] for x in bh}
    for label, v in verdicts.items():
        if v.get("verdict") == "PASSES SECTION 2f PRE-BH":
            v["bh_survives"] = bh_ok.get(label, False)
            v["verdict"] = "PASSES" if v["bh_survives"] else "FAILS (BH)"

    step1_pass = [k for k, v in verdicts.items() if v.get("verdict") == "PASSES"]

    art = {
        "item": "DIP-CALL step 1 arm",
        "register": "PREREG_dipcall.md committed ALONE at c5e0b31",
        "trials_booked_at": "a984ec9 (equity 274 -> 278)",
        "kills_artifact_all_pass": True,
        "equity_N": n_eq, "hlz_hurdle_equity": crit,
        "critical_values": "EVERY ONE LABELLED UNCALIBRATED (V2G, R1-VAR); no X7 or "
                           "CORRECTED-FLOORS floor is quoted for a daily event study",
        "k": a.k, "permutation_draws": a.draws,
        "market_leg": {"construction": "cap-weighted daily return of half-0 panel names with "
                                       "price files, 2009-2019, weights from the most recent "
                                       "PRIOR quarterly market_cap (A8)",
                       "sessions": len(market["dates"]),
                       "first": market["dates"][0], "last": market["dates"][-1],
                       "ken_french_used": False},
        "horizon_cutoffs_global_calendar": {("h%d" % h): cutoff[h] for h in sorted(cutoff)},
        "censoring": censored,
        "economic_floor_pp": D.ECONOMIC_FLOOR_PP,
        "half_cells": cells, "full_sample_cells": full_cells,
        "verdicts_section_2f": verdicts,
        "benjamini_hochberg": {"q": D.BH_Q, "k": D.BH_K, "rows": bh},
        "step1_passing_arms": step1_pass,
        "step1_pass": bool(step1_pass),
        "sensitivity_horizons_carry_no_verdict": list(D.HORIZONS_SENSITIVITY),
    }
    with io.open(D.out_path(ART), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)

    # ------------------------------------------------------------------------------- report
    print("=" * 94)
    print("FULL-SAMPLE CELLS — the $10B TIER GOVERNS; the full universe is a reported surface")
    print("=" * 94)
    for key in sorted(full_cells):
        e = full_cells[key]
        for defn in ("own", "mkt"):
            r = e[defn]
            perm = r.get("permutation", {})
            print("%-22s %-4s n %6d  mean %+8.4fpp  med %+8.4fpp  t_date %+7.3f  t_name %+7.3f"
                  "  perm p95 %s"
                  % (key, defn, e["n"], r["mean_pp"], r["median_pp"],
                     r["date_clustered"]["t"], r["name_clustered"]["t"],
                     ("%+.4f" % perm["p95"]) if perm.get("p95") == perm.get("p95") else "n/a"))
    print()
    print("=" * 94)
    print("SECTION 2f VERDICTS (tier, primary horizons) — hurdle %.4f, floor +%.2fpp"
          % (crit, D.ECONOMIC_FLOOR_PP))
    print("=" * 94)
    for label in sorted(verdicts):
        v = verdicts[label]
        print("%-16s %s" % (label, v["verdict"]))
        for defn, c in (v.get("checks") or {}).items():
            print("     %-4s %s" % (defn, {k2: v2 for k2, v2 in c.items()}))
    print("\nBH q=%.2f k=%d:" % (D.BH_Q, D.BH_K))
    for x in bh:
        print("  rank %d  %-16s p %.6g vs threshold %.5f -> %s"
              % (x["rank"], x["arm"], x["p_two_sided"], x["bh_threshold"],
                 "survives" if x["survives"] else "does not survive"))
    print("\nSTEP 1 PASSING ARMS: %s" % (step1_pass or "NONE"))
    print("wrote %s" % D.out_path(ART))
    return 0


if __name__ == "__main__":
    sys.exit(main())
