"""DIP-CALL step 1 — THE ARM. Refuses to run without a passing kill artifact.

Registers: `PREREG_dipcall.md` (committed ALONE at `c5e0b31`, trials `a984ec9`) and its successor
`PREREG_dipcall2.md` (ALONE at `23be924`, trials `1971fd7`). One scoring path serves both — the
arms and the artifact prefix are PARAMETERS, because `B7`'s nine-call-sites lesson applies here
and a second scoring script is how two registers come to report two different numbers for one
question.

**THIS FILE WAS REWRITTEN BEFORE ITS FIRST REAL RUN, AND THAT IS DECLARED RATHER THAN HIDDEN.**
Its first form shipped complete and was never executed (`K1` fired under `PREREG_dipcall.md`), and
its own docstring then recorded two cautions: the scoring path was unvalidated, and the
permutation pool was built in Python dicts of lists — fine on the ~639k-row tier, roughly 6.2M
entries on the full half-0 universe. The rewrite is a REPAIR of an un-run instrument, not a second
implementation: the registered statistics, bars and conventions are unchanged, and the pool is now
numeric arrays keyed on integer date codes.

WHAT IS MEASURED, AND NONE OF IT IS CHOSEN HERE — every constant comes from the register:
  * mean abnormal return over the horizon, BOTH definitions (own-normal and vs the half-0
    cap-weighted market), and quoting one alone is FORBIDDEN (`DC-1` measured them disagreeing in
    SIGN);
  * standard errors CLUSTERED on event date AND on ticker, and the arm must clear under BOTH
    (`A2`) — date-clustering absorbs the same-day shock the census identified, name-clustering
    absorbs one name's overlapping windows, which no date-clustered se can see (`R9`);
  * the arm's OWN within-date permutation p95, 500 draws, each date's event count preserved
    exactly;
  * both halves, boundary embargoed; the $10B tier governs and the full universe is a reported
    surface; the +0.67pp economic floor; BH at q = 0.10 with `k` = 10; TWO-SIDED p.

TWO IMPLEMENTATION DECISIONS BEYOND THE MODULE'S THREE, both pre-outcome and both recorded because
the register fixes the RULE and not the mechanics:

  1. **THE HORIZON CUTOFF AND THE EMBARGO ARE BOTH TAKEN ON THE GLOBAL SESSION CALENDAR**, not on
     each name's own. The kill pass used the name's own surviving series, which silently drops the
     final events of a name that DELISTS — the survivor filtering §2e forbids. Using the global
     calendar keeps them, with `A11`'s terminal-versus-administrative split deciding the forward
     return, so **the arm's event set is a strict SUPERSET of the kill pass's and `K1`'s floor was
     met on a conservative count**. Taking the embargo the same way makes the arm rows and the
     permutation pool obey ONE rule rather than two.
  2. **THE PERMUTATION POOL IS EVERY ELIGIBLE SCOREABLE NAME-DAY OF THE SAME POPULATION**, event
     or not, which is what "shuffle the event flag within each date" means.

Usage:
  python -m scripts.dipcall_arm                                   # PREREG_dipcall.md (refuses)
  python -m scripts.dipcall_arm --prefix DIPCALL2 --arms no_news   # PREREG_dipcall2.md
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
from valuation.edge.statistics import hlz_hurdle                              # noqa: E402
from valuation.studies import dipcall as D                                    # noqa: E402

DEFAULT_PREFIX = "DIPCALL"
_NEWS_CODE = {D.NEWS: 0, D.NO_NEWS: 1, D.UNKNOWN: 2}
_CODE_NEWS = {v: k for k, v in _NEWS_CODE.items()}


# ---------------------------------------------------------------------------------- the gate
def require_kills(prefix: str) -> dict:
    """REFUSES without a passing kill artifact, and THE TWO REFUSAL STATES ARE DISTINCT.

    `E-1`'s lesson: a hard-coded refusal cannot tell "the control never ran" from "the control ran
    and fired", and those are different facts about the program.
    """
    p = D.out_path("%s_KILLS.json" % prefix)
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
            "REFUSING: the kill pass RAN and FIRED on %s. A kill firing stops the program at zero "
            "further trials and is the cheapest good outcome available to it. The bars may not be "
            "relaxed after watching them fail (W-28)." % ", ".join(fired))
    return k


# -------------------------------------------------------------- A8 the half-0 market series
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


def half0_names() -> list:
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    bq = panel[(panel["date"] >= "2009") & (panel["date"] <= D.BUILD_HI)]
    return sorted(set(bq[bq["ticker"].map(D.stable_key_half) == 0]["ticker"]))


def build_market(names, sched, k: float, lo: str = None, hi: str = None) -> dict:
    """A8: the CAP-WEIGHTED daily return of the era's panel names with price files, weights from
    the most recent PRIOR quarterly `market_cap`.

    On the BUILD era this is half 0 ALONE, deliberately: the whole universe would read
    `2009-2019 x half 1`, a different cell of the charter's 2x2 whose budget allocates it to
    nothing. `X1` licenses the proxy — halving the universe moved the centre of 200 half-books not
    at all. The half filter lives in the CALLER's `names`, not here.

    `lo`/`hi` default to the BUILD window so every landed caller is bit-identical;
    `PREREG_dipcall3.md` passes 1999-01-01 / 2008-12-31. Ken French is used NOWHERE.
    """
    lo = D.BUILD_LO if lo is None else lo
    hi = D.BUILD_HI if hi is None else hi
    num, den = {}, {}
    t0 = time.time()
    for i, t in enumerate(names):
        s = D.read_prices(t)
        if s is None or len(s) < D.VOL_WIN + 10:
            continue
        dates = s["date"].tolist()
        caps = _cap_at(sched.get(t, []), dates)
        r = s["close"].pct_change().to_numpy(dtype=float)
        inb = np.array([lo <= d <= hi for d in dates])
        ok = inb & np.isfinite(r) & np.isfinite(caps) & (caps > 0)
        for d, w, rr in zip(np.asarray(dates, dtype=object)[ok], caps[ok], r[ok]):
            num[d] = num.get(d, 0.0) + float(w) * float(rr)
            den[d] = den.get(d, 0.0) + float(w)
        if i and i % 800 == 0:
            print("  market pass %d/%d, %.0fs" % (i, len(names), time.time() - t0))
    cal = sorted(den)
    mkt = np.array([num[d] / den[d] for d in cal], dtype=float)
    # Cumulative log return, so a window's market return is one subtraction.
    cum = np.concatenate([[0.0], np.cumsum(np.log1p(np.clip(mkt, -0.95, None)))])
    return {"dates": cal, "ret": mkt, "cum": cum,
            "index": {d: j for j, d in enumerate(cal)}}


def terminal_names() -> set:
    """A11. Names whose series ending is a TERMINAL value rather than an administrative censor."""
    a = pd.read_csv(D.actions_csv(), usecols=["date", "action", "ticker"], low_memory=False)
    return set(a.loc[a["action"].isin(D.TERMINAL_ACTIONS), "ticker"].astype(str))


# --------------------------------------------------------------- abnormal returns, per name
def abnormal(close: np.ndarray, ret: np.ndarray, dcode: np.ndarray, market: dict,
             h: int, terminal: bool) -> tuple:
    """Per-session forward abnormal returns for ONE name at horizon `h`.

    Entry at the CLOSE of session t; the horizon runs over sessions t+1 .. t+h (`A9`). The
    own-normal leg subtracts `h x` the mean daily return over the SAME strictly-prior 60-session
    window the volatility scale uses. The market leg is compounded over EXACTLY that window.
    """
    n = len(close)
    idx = np.arange(n)
    end = idx + h
    fwd = np.full(n, np.nan)
    inside = end < n
    fwd[inside] = close[end[inside]] / close[idx[inside]] - 1.0
    term_used = np.zeros(n, dtype=bool)
    if terminal and n:
        # A11: a DELISTED name has a terminal value -- a last close is not a short window, it is
        # the value of a security that ceased to exist. `E-5` verified this reproduces the panel's
        # own `fwd_ret` at max |delta| 0.000e+00 on 591 of 591 such rows.
        tail = ~inside
        fwd[tail] = close[n - 1] / close[idx[tail]] - 1.0
        term_used[tail] = True

    mu = pd.Series(ret).rolling(D.VOL_WIN, min_periods=D.MIN_VOL_OBS).mean().shift(1).to_numpy()
    ar_own = fwd - h * mu

    cum, mdates = market["cum"], market["dates"]
    ar_mkt = np.full(n, np.nan)
    ok = dcode >= 0
    j = dcode[ok]
    j2 = j + h
    good = j2 < len(mdates)
    rows = idx[ok][good]
    rm = np.expm1(cum[j2[good] + 1] - cum[j[good] + 1])
    ar_mkt[rows] = fwd[rows] - rm
    return ar_own, ar_mkt, np.isfinite(fwd), term_used


# ------------------------------------------------------------------------ clustered inference
def clustered(y: np.ndarray, groups: np.ndarray) -> tuple:
    """(mean, se, t, n_clusters) with a cluster-robust standard error of the MEAN.

    `se^2 = G/(G-1) * sum_g (sum_{i in g} (y_i - ybar))^2 / n^2` -- the standard cluster-robust
    variance of a sample mean with the usual small-cluster correction.
    """
    n = len(y)
    if n < 3:
        return float("nan"), float("nan"), float("nan"), 0
    ybar = float(np.mean(y))
    e = y - ybar
    _, inv = np.unique(groups, return_inverse=True)
    g = int(inv.max()) + 1
    if g < 2:
        return ybar, float("nan"), float("nan"), g
    sums = np.bincount(inv, weights=e, minlength=g)
    var = (g / (g - 1.0)) * float(np.sum(sums ** 2)) / (n ** 2)
    se = math.sqrt(var) if var > 0 else float("nan")
    t = (ybar / se) if se and np.isfinite(se) and se > 0 else float("nan")
    return ybar, se, t, g


def permutation_null(pool_vals: np.ndarray, pool_d: np.ndarray,
                     arm_d: np.ndarray, draws: int, seed: int) -> dict:
    """`A2` leg 3. The EVENT FLAG shuffled across names WITHIN each date, preserving each date's
    event count exactly, `draws` times.

    Vectorised per date: one `argpartition` over a (draws x N_d) key matrix gives every draw's
    sample for that date at once. The first form of this function built a Python dict of lists per
    date, which is why it could not be pointed at the 6.2M-row full universe.
    """
    if not len(pool_vals) or not len(arm_d):
        return {"p95": float("nan"), "p05": float("nan"), "null_mean": float("nan"), "draws": 0}
    order = np.argsort(pool_d, kind="stable")
    d_s, v_s = pool_d[order], pool_vals[order]
    uniq, start = np.unique(d_s, return_index=True)
    sizes = np.diff(np.append(start, len(d_s)))
    want_d, want_k = np.unique(arm_d, return_counts=True)

    rng = np.random.default_rng(seed)
    acc = np.zeros(draws, dtype=np.float64)
    total = 0
    pos = np.searchsorted(uniq, want_d)
    for d, kd, i in zip(want_d, want_k, pos):
        if i >= len(uniq) or uniq[i] != d:
            continue                       # a date with no pool: contributes nothing, counted out
        seg = v_s[start[i]:start[i] + sizes[i]]
        nd = len(seg)
        if nd < kd or kd <= 0:
            continue
        if nd == kd:
            acc += float(seg.sum())
        else:
            keys = rng.random((draws, nd))
            idx = np.argpartition(keys, kd - 1, axis=1)[:, :kd]
            acc += seg[idx].sum(axis=1)
        total += int(kd)
    if not total:
        return {"p95": float("nan"), "p05": float("nan"), "null_mean": float("nan"), "draws": 0}
    out = np.sort(acc / total)
    return {"p95": float(out[int(0.95 * (draws - 1))]),
            "p05": float(out[int(0.05 * (draws - 1))]),
            "null_mean": float(out.mean()), "draws": int(draws),
            "events_used": total}


def two_sided_p(t: float) -> float:
    """`A6`. TWO-SIDED. `PREREG_dipcall2.md` §1 keeps this even though the single surviving arm
    licenses a one-sided test on Chan (2003): taking the easier form in a successor register,
    after the predecessor stopped, is the shape this project distrusts most."""
    if not np.isfinite(t):
        return float("nan")
    return float(math.erfc(abs(t) / math.sqrt(2.0)))


# --------------------------------------------------------------------------------- the arm
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=float, default=D.K_PRIMARY)
    ap.add_argument("--draws", type=int, default=D.PERMUTATION_DRAWS)
    ap.add_argument("--prefix", default=DEFAULT_PREFIX)
    ap.add_argument("--arms", default="%s,%s" % (D.NEWS, D.NO_NEWS))
    a = ap.parse_args()
    arms = tuple(x.strip() for x in a.arms.split(",") if x.strip())
    for g in arms:
        if g not in (D.NEWS, D.NO_NEWS):
            raise SystemExit("REFUSING: unknown arm %r" % g)

    kills = require_kills(a.prefix)
    n_eq = research_log.trial_count(domain="equity")
    crit = hlz_hurdle(n_eq)
    print("DIP-CALL ARM [%s]. kill pass PASSED (gated on %s)."
          % (a.prefix, ",".join(kills.get("gated_arms") or [])))
    print("arms scored: %s ; k = %.1f ; draws %d ; equity N = %d ; hurdle %.7f"
          % (",".join(arms), a.k, a.draws, n_eq, crit))
    print("EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED (V2G, R1-VAR).\n")

    sched = D.tier_schedule()
    names = half0_names()
    print("pass 1 of 2 — the half-0 cap-weighted market (A8) ...")
    market = build_market(names, sched, a.k)
    mdates = market["dates"]
    print("  market: %d sessions %s..%s\n" % (len(mdates), mdates[0], mdates[-1]))

    # The GLOBAL session calendar decides horizon eligibility AND the embargo (decision 1).
    last_build = len(mdates) - 1
    cutoff_code = {h: max(0, last_build - h)
                   for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY}
    is_early = np.array([d < D.HALF_BOUNDARY for d in mdates])
    # An event at global code j is EMBARGOED at horizon h when [j, j+h] straddles the boundary.
    emb = {}
    for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
        j2 = np.minimum(np.arange(len(mdates)) + h, len(mdates) - 1)
        emb[h] = is_early & (~is_early[j2])
    print("  horizon cutoff dates: %s"
          % {("h%d" % h): mdates[cutoff_code[h]] for h in sorted(cutoff_code)})
    print("  embargoed sessions:  %s\n"
          % {("h%d" % h): int(emb[h].sum()) for h in sorted(emb)})

    term = terminal_names()
    print("pass 2 of 2 — abnormal returns, arm rows and the permutation pools ...")
    spine = EventSpine.build(names=names, csv_path=D.events_csv())

    pool = {h: {"d": [], "own": [], "mkt": [], "tier": []} for h in D.HORIZONS_PRIMARY}
    armrows = {h: {"d": [], "t": [], "own": [], "mkt": [], "tier": [], "news": []}
               for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY}
    cens = {"administrative_dropped": 0, "terminal_used": 0, "unknown_news_rows": 0}
    t0 = time.time()
    for i, t in enumerate(names):
        s = D.name_frame(t, sched.get(t, []), k=a.k)
        if s is None:
            continue
        dates = s["date"].tolist()
        dcode = np.array([market["index"].get(d, -1) for d in dates], dtype=np.int64)
        close = s["close"].to_numpy(dtype=float)
        ret = s["ret"].to_numpy(dtype=float)
        sc = s["scoreable"].to_numpy()
        tr = s["tier"].to_numpy()
        evf = s["event"].to_numpy()
        inb = (dcode >= 0)
        d2i = {d: j for j, d in enumerate(dates)}
        ann = D.announce_sessions(spine, t, d2i)
        ncode = np.full(len(dates), _NEWS_CODE[D.UNKNOWN], dtype=np.int8)
        if ann is not None:
            ncode[:] = _NEWS_CODE[D.NO_NEWS]
            lo, hi = D.NEWS_SESSION_WINDOW
            for j in ann:
                for off in range(lo, hi + 1):
                    jj = j + off
                    if 0 <= jj < len(dates):
                        ncode[jj] = _NEWS_CODE[D.NEWS]
        is_term = t in term

        for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
            ar_own, ar_mkt, usable, tu = abnormal(close, ret, dcode, market, h, is_term)
            elig = inb & sc & (dcode <= cutoff_code[h]) & ~emb[h][np.clip(dcode, 0, None)]
            good = elig & usable & np.isfinite(ar_own) & np.isfinite(ar_mkt)
            cens["administrative_dropped"] += int((elig & ~usable).sum())
            cens["terminal_used"] += int((good & tu).sum())
            if h in D.HORIZONS_PRIMARY and good.any():
                pool[h]["d"].append(dcode[good].astype(np.int32))
                pool[h]["own"].append((ar_own[good] * 100.0).astype(np.float32))
                pool[h]["mkt"].append((ar_mkt[good] * 100.0).astype(np.float32))
                pool[h]["tier"].append(tr[good])
            m = good & evf
            if m.any():
                cens["unknown_news_rows"] += int((m & (ncode == _NEWS_CODE[D.UNKNOWN])).sum())
                armrows[h]["d"].append(dcode[m].astype(np.int32))
                armrows[h]["t"].append(np.full(int(m.sum()), i, dtype=np.int32))
                armrows[h]["own"].append((ar_own[m] * 100.0).astype(np.float32))
                armrows[h]["mkt"].append((ar_mkt[m] * 100.0).astype(np.float32))
                armrows[h]["tier"].append(tr[m])
                armrows[h]["news"].append(ncode[m])
        if i and i % 800 == 0:
            print("  %d/%d names, %.0fs" % (i, len(names), time.time() - t0))

    cat = lambda dd, key: (np.concatenate(dd[key]) if dd[key] else np.array([]))   # noqa: E731
    for h in list(pool):
        for key in pool[h]:
            pool[h][key] = cat(pool[h], key)
    for h in list(armrows):
        for key in armrows[h]:
            armrows[h][key] = cat(armrows[h], key)
    print("  arm rows built in %.0fs ; pool sizes %s\n"
          % (time.time() - t0, {("h%d" % h): int(len(pool[h]["d"])) for h in pool}))

    # ---------------------------------------------------------------------------- score
    cells, full_cells = {}, {}
    for pop in ("tier", "full"):
        for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
            R = armrows[h]
            if not len(R["d"]):
                continue
            pmask = R["tier"].astype(bool) if pop == "tier" else np.ones(len(R["d"]), bool)
            for arm in arms:
                am = pmask & (R["news"] == _NEWS_CODE[arm])
                if am.sum() < 10:
                    continue
                entry = {"n": int(am.sum())}
                for defn in ("own", "mkt"):
                    y = R[defn][am].astype(np.float64)
                    dcl = R["d"][am]
                    tcl = R["t"][am]
                    m_d, se_d, t_d, g_d = clustered(y, dcl)
                    m_n, se_n, t_n, g_n = clustered(y, tcl)
                    rec = {"mean_pp": m_d, "median_pp": float(np.median(y)),
                           "realised_sd_pp": float(np.std(y, ddof=1)) if len(y) > 1 else None,
                           "date_clustered": {"se_pp": se_d, "t": t_d, "clusters": g_d,
                                              "p_two_sided": two_sided_p(t_d)},
                           "name_clustered": {"se_pp": se_n, "t": t_n, "clusters": g_n,
                                              "p_two_sided": two_sided_p(t_n)}}
                    # MB8 / RUN_RULES rule 11: the MDE from the arm's OWN measured se, BOTH powers,
                    # never one quoted as the other (MB22).
                    for lbl, se in (("date", se_d), ("name", se_n)):
                        if se and np.isfinite(se) and se > 0:
                            rec["mde_%s_clustered" % lbl] = {
                                "detection_threshold_50pc_power":
                                    power_gate.detection_threshold(se, n_trials=n_eq),
                                "mde_80pc_power": (crit + power_gate.Z_POWER_CONVENTION) * se,
                                "power_against_economic_floor":
                                    power_gate.power_at(D.ECONOMIC_FLOOR_PP, se, n_trials=n_eq)}
                    if h in D.HORIZONS_PRIMARY:
                        P = pool[h]
                        ppm = P["tier"].astype(bool) if pop == "tier" else \
                            np.ones(len(P["d"]), bool)
                        perm = permutation_null(P[defn][ppm].astype(np.float64), P["d"][ppm],
                                                dcl, a.draws, 0)
                        perm["clears_p95"] = bool(np.isfinite(perm["p95"]) and m_d > perm["p95"])
                        rec["permutation"] = perm
                    entry[defn] = rec
                full_cells["%s|h%d|%s" % (pop, h, arm)] = entry

                # the two halves
                for half in ("early", "late"):
                    hm = am & (is_early[R["d"]] if half == "early" else ~is_early[R["d"]])
                    if hm.sum() < 10:
                        cells["%s|h%d|%s|%s" % (pop, h, arm, half)] = {"n": int(hm.sum())}
                        continue
                    hc = {"n": int(hm.sum())}
                    for defn in ("own", "mkt"):
                        y = R[defn][hm].astype(np.float64)
                        m_d, se_d, t_d, g_d = clustered(y, R["d"][hm])
                        m_n, se_n, t_n, g_n = clustered(y, R["t"][hm])
                        hc[defn] = {"mean_pp": m_d, "median_pp": float(np.median(y)),
                                    "date_clustered": {"se_pp": se_d, "t": t_d, "clusters": g_d},
                                    "name_clustered": {"se_pp": se_n, "t": t_n, "clusters": g_n}}
                    cells["%s|h%d|%s|%s" % (pop, h, arm, half)] = hc

    # ------------------------------------------------------------------- section 2f verdict
    verdicts, bh_input = {}, []
    for h in D.HORIZONS_PRIMARY:
        for arm in arms:
            label = "h%d|%s" % (h, arm)
            fc = full_cells.get("tier|%s" % label)
            if not fc:
                verdicts[label] = {"verdict": "NOT ASSESSABLE", "why": "no tier rows"}
                continue
            checks = {}
            for defn in ("own", "mkt"):
                r = fc[defn]
                e = {"positive": bool(r["mean_pp"] > 0),
                     "economic_floor": bool(r["mean_pp"] >= D.ECONOMIC_FLOOR_PP),
                     "date_clustered_t": bool(abs(r["date_clustered"]["t"]) > crit),
                     "name_clustered_t": bool(abs(r["name_clustered"]["t"]) > crit),
                     "permutation": bool(r.get("permutation", {}).get("clears_p95"))}
                hv = {hf: cells.get("tier|%s|%s" % (label, hf)) for hf in ("early", "late")}
                ok_halves = all(
                    hv[hf] and defn in hv[hf] and hv[hf][defn]["mean_pp"] > 0
                    for hf in ("early", "late"))
                e["both_halves_same_sign"] = bool(ok_halves)
                e["both_halves_clear_floor"] = bool(all(
                    hv[hf] and defn in hv[hf]
                    and hv[hf][defn]["mean_pp"] >= D.ECONOMIC_FLOOR_PP
                    for hf in ("early", "late")))
                checks[defn] = e
            passed = all(all(v.values()) for v in checks.values())
            p_bh = max(fc["own"]["date_clustered"]["p_two_sided"],
                       fc["own"]["name_clustered"]["p_two_sided"])
            bh_input.append((label, p_bh))
            verdicts[label] = {"verdict": "PASSES SECTION 2f PRE-BH" if passed else "FAILS",
                               "checks": checks, "p_for_bh": p_bh,
                               "halves": {hf: cells.get("tier|%s|%s" % (label, hf))
                                          for hf in ("early", "late")}}

    # BH at q = 0.10 with k = 10 FIXED. Shrinking k would make every surviving threshold easier.
    bh_input.sort(key=lambda x: (x[1] if x[1] == x[1] else 1.0))
    bh = []
    for i, (label, p) in enumerate(bh_input, start=1):
        thr = i * D.BH_Q / D.BH_K
        bh.append({"rank": i, "arm": label, "p_two_sided": p, "bh_threshold": thr,
                   "survives": bool(p == p and p <= thr)})
    surv = {x["arm"]: x["survives"] for x in bh}
    for label, v in verdicts.items():
        if v.get("verdict") == "PASSES SECTION 2f PRE-BH":
            v["bh_survives"] = surv.get(label, False)
            v["verdict"] = "PASSES" if v["bh_survives"] else "FAILS (BH)"
    step1 = [k for k, v in verdicts.items() if v.get("verdict") == "PASSES"]

    art = {"item": "DIP-CALL step 1 arm [%s]" % a.prefix,
           "registers": ["PREREG_dipcall.md c5e0b31", "PREREG_dipcall2.md 23be924"],
           "arms_scored": sorted(arms),
           "arms_structurally_unreachable": sorted(set((D.NEWS, D.NO_NEWS)) - set(arms)),
           "kills_artifact_all_pass": True, "kills_gated_arms": kills.get("gated_arms"),
           "equity_N": n_eq, "hlz_hurdle_equity": crit,
           "critical_values": "EVERY ONE LABELLED UNCALIBRATED (V2G, R1-VAR); no X7 or "
                              "CORRECTED-FLOORS floor is quoted for a daily event study",
           "k": a.k, "permutation_draws": a.draws,
           "p_is_two_sided": True,
           "economic_floor_pp": D.ECONOMIC_FLOOR_PP,
           "market_leg": {"construction": "cap-weighted daily return of half-0 panel names with "
                                          "price files, 2009-2019, weights from the most recent "
                                          "PRIOR quarterly market_cap (A8)",
                          "sessions": len(mdates), "first": mdates[0], "last": mdates[-1],
                          "ken_french_used": False},
           "horizon_cutoff_dates": {("h%d" % h): mdates[cutoff_code[h]]
                                    for h in sorted(cutoff_code)},
           "embargoed_sessions": {("h%d" % h): int(emb[h].sum()) for h in sorted(emb)},
           "censoring": cens,
           "half_cells": cells, "full_sample_cells": full_cells,
           "verdicts_section_2f": verdicts,
           "benjamini_hochberg": {"q": D.BH_Q, "k": D.BH_K, "rows": bh,
                                  "note": "k is FIXED at 10 from PREREG_dipcall.md section 7; "
                                          "shrinking it to the true batch size would make every "
                                          "surviving threshold EASIER (W-28)"},
           "step1_passing_arms": step1, "step1_pass": bool(step1),
           "sensitivity_horizons_carry_no_verdict": list(D.HORIZONS_SENSITIVITY)}
    with io.open(D.out_path("%s_ARM.json" % a.prefix), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)

    # ------------------------------------------------------------------------------- report
    print("=" * 108)
    print("FULL-SAMPLE CELLS — the $10B TIER GOVERNS; the full universe is a REPORTED SURFACE")
    print("=" * 108)
    for key in sorted(full_cells):
        e = full_cells[key]
        for defn in ("own", "mkt"):
            if defn not in e:
                continue
            r = e[defn]
            # The guard and the format must read the SAME object. The first cut tested
            # `p.get("p95")` and then formatted `p["p95"]`, so a sensitivity horizon -- which has
            # no permutation at all -- raised KeyError AFTER every number had been computed and
            # the artifact written. The wrong-object family, in a print statement.
            p95 = (r.get("permutation") or {}).get("p95")
            print("%-24s %-4s n %6d  mean %+8.4fpp  med %+8.4fpp  t_date %+7.3f  t_name %+7.3f"
                  "  perm p95 %s  sd %7.3f"
                  % (key, defn, e["n"], r["mean_pp"], r["median_pp"],
                     r["date_clustered"]["t"], r["name_clustered"]["t"],
                     ("%+8.4f" % p95) if isinstance(p95, float) and p95 == p95 else "     n/a",
                     r["realised_sd_pp"] or float("nan")))
    print()
    print("=" * 108)
    print("HALVES (tier, primary horizons)")
    print("=" * 108)
    for key in sorted(cells):
        if not key.startswith("tier|") or "h63" in key or "h126" in key:
            continue
        c = cells[key]
        if "own" not in c:
            print("%-32s n %6d  (too thin to score)" % (key, c["n"]))
            continue
        print("%-32s n %6d  own %+8.4fpp (t_d %+7.3f)  mkt %+8.4fpp (t_d %+7.3f)"
              % (key, c["n"], c["own"]["mean_pp"], c["own"]["date_clustered"]["t"],
                 c["mkt"]["mean_pp"], c["mkt"]["date_clustered"]["t"]))
    print()
    print("=" * 108)
    print("SECTION 2f VERDICTS — hurdle %.4f (UNCALIBRATED), economic floor +%.2fpp"
          % (crit, D.ECONOMIC_FLOOR_PP))
    print("=" * 108)
    for label in sorted(verdicts):
        v = verdicts[label]
        print("%-16s %s" % (label, v["verdict"]))
        for defn, c in (v.get("checks") or {}).items():
            fails = [kk for kk, vv in c.items() if not vv]
            print("     %-4s %s" % (defn, "all conditions met" if not fails
                                    else "FAILS: " + ", ".join(fails)))
    print("\nBH q=%.2f k=%d (TWO-SIDED p):" % (D.BH_Q, D.BH_K))
    for x in bh:
        print("  rank %d  %-16s p %.6g vs threshold %.5f -> %s"
              % (x["rank"], x["arm"], x["p_two_sided"], x["bh_threshold"],
                 "survives" if x["survives"] else "does not survive"))
    print("\nSTEP 1 PASSING ARMS: %s" % (step1 or "NONE"))
    print("wrote %s" % D.out_path("%s_ARM.json" % a.prefix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
