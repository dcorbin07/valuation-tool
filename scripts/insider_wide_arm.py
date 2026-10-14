# -*- coding: utf-8 -*-
"""`INSIDER-WIDE` — THE ONE CHECK-QUADRANT READ. Stage 2 of `INSIDER-CLUSTER`.

    python -m scripts.insider_wide_checks      # FIRST, its own pass
    python -m scripts.insider_wide_arm         # then this, ONCE

Register: `PREREG_insider_cluster_wide.md`, committed **ALONE at `1cc8b7e`**, markdown only, a
strict git ancestor of this file. **Three equity trials booked at `dfbccc4` (equity 303 -> 306)
BEFORE this file existed.**

**THE CHECK QUADRANT GETS ONE READ AND THERE IS NO SECOND ONE** (`RESEARCH_CHARTER` §4b). Every
bar, population, horizon and cost is the register's; none is defined here for the first time, and
changing one after a measurement voids the item (`MA28`).

**IT REFUSES WITHOUT A PASSING PRE-READ ARTIFACT.** `O10`'s process defect was a gating control
and its outcomes running in one pass.

**THE SCORING FUNCTION IS ERA-PARAMETERISED AND IS THE SAME ONE `C1` PROVES BIT-IDENTICAL TO
STAGE 1.** `scripts/insider_cluster_arm.py` hard-wires the build window, half 0 and
`dipcall.tier_schedule` (whose own docstring says it is half-0 only), so the check cell cannot be
scored by calling it — and copying it would be the `B7` split. `C1` runs THIS function on the
BUILD cell and requires stage 1's published figures exactly, so a drift in the instrument stops
the read instead of being absorbed into it.

Every statistic is delegated to `scripts/dipcall_arm.py` (cap-weighted market, the abnormal-return
pair, two-way clustered standard errors, the within-date permutation null, the two-sided *p*) and
every cost to `fundamental_panel.one_way_cost_bps`. No second implementation of either.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import fundamental_panel as FP                          # noqa: E402
from valuation.edge import power_gate as PG                                 # noqa: E402
from valuation.edge import statistics as ST                                 # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402
from scripts import dipcall_arm as DA                                       # noqa: E402
from scripts import insider_wide_tier_choice as TC                          # noqa: E402

OUT = "INSIDER_WIDE_ARM.json"
CHECKS = "INSIDER_WIDE_CHECKS.json"

#: §2c. The population every cell is: `(label, cap floor in USD, carries a verdict?)`. The two
#: `False` rows are read in the SAME pass and reported, and carry NO verdict — §2c declares that
#: in advance so a reader cannot promote one afterwards, and §4 A5 excludes them from `BH` with
#: the exclusion declared rather than silently shrinking `k`.
CELLS = (
    ("full_universe",   0.0,   True),
    ("cap_ge_10bn",     10e9,  True),
    ("cap_ge_2bn",      2e9,   False),
    ("cap_ge_500m",     500e6, True),      # <- THE GOVERNING POPULATION (§2)
    ("cap_ge_100m",     100e6, False),
)
GOVERNING = "cap_ge_500m"

H_PRIMARY = 63                   # §2b: h=63 GOVERNS
H_REPORTED = 126                 # §2b: REPORTED ONLY, no verdict
CHECK_HALF_BOUNDARY = "2023-01-01"   # §4 A2, the midpoint of 2020-2026, FIXED IN ADVANCE
PERMUTATION_DRAWS = 500          # §1
BH_Q = 0.10                      # §4 A5
BH_K = 3                         # §4 A5, FIXED at the three verdict cells, never shrunk
T_BAR = 2.0                      # §4 A3, LABELLED UNCALIBRATED
MIN_NAMES_PER_DATE = 50          # charter Stage 1b, CONTRACT_MIN_POSITIONS

#: §5's pre-declared power table, as PUBLISHED in the register, to the precision the register
#: prints. A cell below 0.50 returns `UNDERPOWERED` on a null rather than `NOT CONFIRMED`, so
#: these numbers decide a LABEL and must be the register's own.
#:
#: **THE FIRST CUT OF THIS DICT WAS HAND-TYPED AND FOUR OF ITS TEN FIGURES WERE WRONG** — `$2B`
#: gross read 0.337 against a banked 0.0518, and `$500M`/`$100M` had their NET figures swapped
#: (0.147/0.126 against 0.127/0.148). `BETA-FORECAST` shipped a hand-typed `HLZ` hurdle wrong in
#: its FOURTH DECIMAL three items ago and the lesson is the same one: **derive a figure you are
#: going to branch on.** No verdict moved — every cell sits on the same side of 0.50 under both —
#: which is luck rather than design, and exactly what `X7RECON` says not to rely on.
POWER_REGISTER = {
    "full_universe": {"gross": 0.975, "net": 0.100},
    "cap_ge_10bn":   {"gross": 0.726, "net": 0.670},
    "cap_ge_2bn":    {"gross": 0.052, "net": 0.000},
    "cap_ge_500m":   {"gross": 0.424, "net": 0.127},
    "cap_ge_100m":   {"gross": 0.872, "net": 0.148},
}

#: The floor each label maps to in the banked tier-choice artifact, which keys on the floor in USD.
_FLOOR_KEY = {label: ("%d" % int(floor)) for (label, floor, _v) in CELLS}


def power_declared() -> dict:
    """§5's power table, DERIVED from the banked tier-choice artifact where it is readable.

    The artifact lives under `data/`, which is gitignored and absent on a CI runner, so this
    falls back to `POWER_REGISTER` — the register's own published figures — rather than raising.
    **When BOTH are available they must agree to the register's printed precision**, so a changed
    artifact goes red instead of silently re-deciding a verdict LABEL. That is `MA13`'s
    committed-literal idiom pointed at a number this code branches on.

    **THE FALLBACK'S FIRST FORM GUARDED WITH `except Exception` AND KILLED THE WHOLE SUITE IN CI.**
    `dipcall.data_root` **REFUSES** with `SystemExit` when no populated data root exists — which
    is right, and `SystemExit` derives from `BaseException`, so `except Exception` does not catch
    it. The import died at `REFUSING: no populated data root found` and `tests/test_insider_wide.py`
    went red on a runner while passing locally. **A refusing resolver raises `SystemExit`, so a
    CI-safe fallback must catch `BaseException` or name it** — the `guards-that-fail-open-in-ci`
    family inverted: instead of passing vacuously it took the suite down.
    """
    out = {k: dict(v) for k, v in POWER_REGISTER.items()}
    try:
        p = D.out_path("INSIDER_WIDE_TIER_CHOICE.json")
        if not os.path.isfile(p):
            return out
        pr = json.load(io.open(p, encoding="utf-8"))["power_realised"]
    except (Exception, SystemExit):                                         # noqa: BLE001
        return out
    for label, key in _FLOOR_KEY.items():
        row = pr.get(key)
        if not row:
            continue
        g, n = float(row["power_gross"]), float(row["power_net_vs_cost_bar"])
        for leg, v in (("gross", g), ("net", n)):
            want = POWER_REGISTER[label][leg]
            if abs(round(v, 3) - want) > 1e-9:
                raise SystemExit(
                    "REFUSING: the banked power for %s/%s is %.6f, which rounds to %.3f against "
                    "the register's published %.3f. A power figure decides whether a null reads "
                    "UNDERPOWERED or NOT CONFIRMED, so a disagreement stops the read rather than "
                    "quietly changing a label." % (label, leg, v, round(v, 3), want))
        out[label] = {"gross": g, "net": n}
    return out


POWER_DECLARED = power_declared()


def _checks() -> dict:
    p = D.out_path(CHECKS)
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: no pre-read artifact at %s. The register's section 7 checks are FREE and "
            "run in THEIR OWN PASS before any check-quadrant outcome -- run `python -m "
            "scripts.insider_wide_checks` first (O10's process defect)." % p)
    k = json.load(io.open(p, encoding="utf-8"))
    if not k.get("all_pass"):
        failed = [c for c, v in (k.get("checks") or {}).items() if not v.get("pass")]
        raise SystemExit(
            "REFUSING: pre-read check(s) %s failed. C1 failing means the instrument has drifted "
            "from stage 1's and the comparison the whole item rests on is between two different "
            "things; the read does not happen." % (failed or "?"))
    return k


def check_events() -> pd.DataFrame:
    """The banked `k`=2 event set restricted to era `check` x ticker half **1**.

    Disjoint from the build cell by construction (a different era AND a different half), which is
    `C4`. The event set itself is stage 1's, unmodified — re-deriving it here would be a second
    construction of the thing the register says is unchanged.
    """
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % IC.K_PRIMARY)
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: no banked event set at %s" % p)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    return ev[(ev["era"] == "check") & (ev["half"] == 1)].reset_index(drop=True)


def build_events() -> pd.DataFrame:
    """Stage 1's own cell — era `build` x half 0 — for `C1` ONLY. No verdict comes from here."""
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % IC.K_PRIMARY)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    return ev[(ev["era"] == "build") & (ev["half"] == 0)].reset_index(drop=True)


def roundtrip_cost_pp(caps) -> np.ndarray:
    """§3. The SIZE-TIERED round trip, in percentage points, one value per event.

    `2 x one_way_cost_bps(cap) / 100`. The function is the SHIPPED one and the table is not
    retyped (`C3`), so this cannot drift from the cost model every other claim in the project is
    scored against. Stage 1's single 0.67pp floor is SUPERSEDED for the reason §3 states: it is
    2x `B11`'s realised BOOK-WEIGHTED 33.4 bps on a megacap-tilted decile book, which is not a
    cost for the name in front of you.
    """
    out = np.full(len(caps), np.nan, dtype=float)
    for i, c in enumerate(np.asarray(caps, dtype=float)):
        if np.isfinite(c) and c > 0:
            out[i] = 2.0 * float(FP.one_way_cost_bps(c)) / 100.0
    return out


def score(ev: pd.DataFrame, market: dict, sched: dict, terminal: set, names: list,
          lo: str, hi: str, h: int, floor_usd: float, half_boundary: str,
          cap_sched: dict, tag: str) -> dict:
    """One cell: the MARKET-ADJUSTED mean abnormal return at horizon `h` over `cap >= floor`.

    Era-parameterised: `lo`/`hi`, the name list and the cap schedule all come from the caller, so
    the identical function scores the BUILD cell (for `C1`) and the CHECK cell (for the verdict).

    The POOL is every scoreable session of every name in the cell that also clears the cap floor
    — the same population the permutation shuffles the event flag across, which is what makes the
    null the cell's OWN null rather than a borrowed one. `A9`'s entry convention: the horizon runs
    over sessions `t+1 … t+h`, so the event session's own return is never inside it.

    **The own-normal leg is used ONLY as stage 1's row-set filter and is never a statistic**
    (§1). `DA.abnormal` returns both; a row is kept only where BOTH are finite, exactly as stage
    1 kept it, and no own-normal VALUE reaches a mean, a null, a `t` or the artifact — pinned by
    test. Keeping the filter and dropping the statistic is what §1 actually says, and `C1` is
    what established that the two are different things.
    """
    by_tk = {t: set(g["date"].astype(str)) for t, g in ev.groupby("ticker")}
    rows = {"mkt": [], "date": [], "ticker": [], "cost_pp": [], "cap": []}
    pool = {"mkt": [], "date": []}
    n_terminal = 0
    n_no_cap = 0
    for i, tk in enumerate(sorted(set(ev["ticker"].tolist()))):
        f = D.name_frame(tk, sched.get(tk, []), k=D.K_PRIMARY)
        if f is None:
            continue
        dates = f["date"].astype(str).to_numpy()
        close = f["close"].to_numpy(dtype=float)
        ret = f["ret"].to_numpy(dtype=float)
        dcode = np.array([market["index"].get(d, -1) for d in dates], dtype=np.int64)
        ar_own, ar_mkt, ok, term = DA.abnormal(close, ret, dcode, market, h, tk in terminal)
        inb = np.array([lo <= d <= hi for d in dates])
        caps = np.array([TC.cap_at(cap_sched, tk, d) for d in dates], dtype=float)
        # **STAGE 1'S ROW-SET RULE, RESTORED — AND C1 IS WHAT CAUGHT ITS ABSENCE BEFORE THE
        # READ.** This line first read `ok & inb & np.isfinite(ar_mkt)`, because §1 says the
        # own-normal leg is dropped — and that dropped it from the POPULATION FILTER as well as
        # from the statistic. Stage 1 required BOTH legs finite to keep a row, so the two
        # instruments disagreed by **2 events (4,074 against 4,072)** and the mean by +0.0008pp.
        #
        # **THE PORTABLE PART: in a two-leg construction the discarded leg is also a FILTER, so
        # scoring one leg silently WIDENS the population.** §1 licenses dropping the own-normal
        # leg from the statistic and nowhere licenses changing which rows exist, and at the one
        # unrepeatable look a 2-row population change is still a construction change. The drift
        # ran in the arm's favour (two more events, a slightly higher mean), which is the
        # direction a gate is for.
        keep = ok & inb & np.isfinite(ar_own) & np.isfinite(ar_mkt)
        if floor_usd > 0:
            # A name with NO cap observation is DROPPED and COUNTED, never read as qualifying --
            # a missing cap is not a small company, and reading it either way silently would be
            # the `blank-code counter` family.
            keep = keep & np.isfinite(caps) & (caps >= floor_usd)
        evset = by_tk.get(tk, set())
        is_ev = np.array([d in evset for d in dates])
        n_no_cap += int((is_ev & inb & ok & ~np.isfinite(caps)).sum())
        n_terminal += int((term & keep & is_ev).sum())
        for j in np.flatnonzero(keep):
            pool["mkt"].append(ar_mkt[j]); pool["date"].append(dates[j])
            if is_ev[j]:
                rows["mkt"].append(ar_mkt[j]); rows["date"].append(dates[j])
                rows["ticker"].append(tk); rows["cap"].append(caps[j])

    # RULE 9: STORE THE DRAWS. `X7` kept 100 placebo draws as five summary rates and an 8%-vs-7%
    # mismatch sat undiagnosable for two sessions; stage 1 of this item needed its own banked
    # rows inside the hour to diagnose a half-null that read backwards.
    rows["cost_pp"] = list(roundtrip_cost_pp(rows["cap"]))
    pd.DataFrame(rows).to_pickle(D.out_path("INSIDER_WIDE_ROWS_%s.pkl" % tag))
    pd.DataFrame(pool).to_pickle(D.out_path("INSIDER_WIDE_POOL_%s.pkl" % tag))

    out = {"h": h, "floor_usd": floor_usd, "n_events_scored": len(rows["mkt"]),
           "n_pool": len(pool["mkt"]), "n_terminal_used": n_terminal,
           "n_event_rows_dropped_no_cap": n_no_cap,
           "rows_pkl": "INSIDER_WIDE_ROWS_%s.pkl" % tag,
           "pool_pkl": "INSIDER_WIDE_POOL_%s.pkl" % tag}
    if len(rows["mkt"]) < 3:
        out["status"] = "NO ROWS"
        return out

    y = np.asarray(rows["mkt"], dtype=float)
    d_arr = np.asarray(rows["date"], dtype=object)
    t_arr = np.asarray(rows["ticker"], dtype=object)
    cost = np.asarray(rows["cost_pp"], dtype=float)
    early = d_arr < half_boundary
    out["halves"] = {"early": int(early.sum()), "late": int((~early).sum()),
                     "boundary": half_boundary}
    out["n_tickers"] = int(len(set(t_arr.tolist())))

    m, se_d, t_d, g_d = DA.clustered(y, d_arr)
    _m, se_t, t_t, g_t = DA.clustered(y, t_arr)
    out["mean_pp"] = m * 100.0
    out["se_date_pp"], out["t_date"], out["n_date_clusters"] = se_d * 100.0, t_d, g_d
    out["se_ticker_pp"], out["t_ticker"], out["n_ticker_clusters"] = se_t * 100.0, t_t, g_t
    out["t_min_abs"] = float(min(abs(t_d), abs(t_t)))
    out["p_two_sided_worst"] = DA.two_sided_p(out["t_min_abs"])

    nul = DA.permutation_null(np.asarray(pool["mkt"], dtype=float),
                              np.asarray(pool["date"], dtype=object),
                              d_arr, PERMUTATION_DRAWS, seed=3000 + h)
    out["null_p95_pp"] = nul["p95"] * 100.0
    out["null_mean_pp"] = nul["null_mean"] * 100.0
    out["null_events_used"] = nul.get("events_used")
    out["null_draws"] = nul.get("draws")
    out["clears_own_null"] = bool(np.isfinite(nul["p95"]) and m > nul["p95"])
    out["over_null_mean_pp"] = out["mean_pp"] - out["null_mean_pp"]

    hv = {}
    for nm, msk in (("early", early), ("late", ~early)):
        yy, dd = y[msk], d_arr[msk]
        if len(yy) < 3:
            hv[nm] = {"status": "too few rows"}
            continue
        mm, sse, tt, gg = DA.clustered(yy, dd)
        n2 = DA.permutation_null(np.asarray(pool["mkt"], dtype=float),
                                 np.asarray(pool["date"], dtype=object),
                                 dd, PERMUTATION_DRAWS, seed=4000 + h)
        hv[nm] = {"n": int(len(yy)), "mean_pp": mm * 100.0, "t": tt, "se_pp": sse * 100.0,
                  "n_date_clusters": gg, "null_p95_pp": n2["p95"] * 100.0,
                  "null_mean_pp": n2["null_mean"] * 100.0,
                  "n_event_dates": int(len(set(dd.tolist()))),
                  "clears": bool(np.isfinite(n2["p95"]) and mm > n2["p95"])}
    out["halves_detail"] = hv
    signs = [hv.get(x, {}).get("mean_pp") for x in ("early", "late")]
    out["halves_same_sign"] = bool(all(s is not None and np.isfinite(s) for s in signs)
                                   and (signs[0] > 0) == (signs[1] > 0))
    out["both_halves_clear"] = bool(hv.get("early", {}).get("clears")
                                    and hv.get("late", {}).get("clears"))

    # THE COST BAR IS EVENT-WEIGHTED OVER THIS CELL'S OWN EVENTS (§3/§4 A4), so a wide cell is
    # charged the wide cell's cost and never the megacap book's.
    ok_c = np.isfinite(cost)
    out["roundtrip_cost_pp_mean"] = float(cost[ok_c].mean()) if ok_c.any() else float("nan")
    out["roundtrip_cost_pp_median"] = float(np.median(cost[ok_c])) if ok_c.any() else float("nan")
    out["n_events_with_cost"] = int(ok_c.sum())
    out["net_of_cost_pp"] = out["mean_pp"] - out["roundtrip_cost_pp_mean"]

    # THE MDE TRAVELS WITH THE VERDICT AND IS THIS ARM'S OWN (`MB8`: never borrow an `se`), taken
    # on the WORSE clustering because §4 A3 requires clearing under both.
    se_worst = max(se_d, se_t)
    out["se_worst_pp"] = se_worst * 100.0
    out["mde80_pp_own_se"] = (T_BAR + PG.z_for_power(0.80)) * se_worst * 100.0
    out["power_state_own_se"] = PG.state(m, se_worst, crit=T_BAR)
    out["realised_power_vs_own_mean"] = PG.power_at(m, se_worst, crit=T_BAR)

    out["A1_sign_positive"] = bool(m > 0)
    out["A2_own_null_and_both_halves"] = bool(out["clears_own_null"] and out["both_halves_clear"]
                                              and out["halves_same_sign"])
    out["A3_t_over_bar_both_clusterings"] = bool(out["t_min_abs"] > T_BAR and m > 0)
    out["A4_economic_size_tiered"] = bool(np.isfinite(out["net_of_cost_pp"])
                                          and out["net_of_cost_pp"] > 0)
    out["A1_A4_all_pass"] = bool(out["A1_sign_positive"] and out["A2_own_null_and_both_halves"]
                                 and out["A3_t_over_bar_both_clusterings"]
                                 and out["A4_economic_size_tiered"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--c1-only", action="store_true",
                    help="re-derive stage 1's BUILD cell only; writes nothing, reads no check row")
    a = ap.parse_args(argv)
    t0 = time.time()

    if a.c1_only:
        ev = build_events()
        sched = D.tier_schedule()
        names = DA.half0_names()
        print("[c1] building stage 1's half-0 market over %d names ..." % len(names), flush=True)
        market = DA.build_market(names, sched, D.K_PRIMARY)
        cell = score(ev, market, sched, DA.terminal_names(), names, D.BUILD_LO, D.BUILD_HI,
                     H_PRIMARY, 0.0, D.HALF_BOUNDARY, TC.cap_schedule(0), "C1_build_full_h63")
        print("[c1] n %d | mkt %+.10fpp t %.9f/%.9f"
              % (cell["n_events_scored"], cell["mean_pp"], cell["t_date"], cell["t_ticker"]),
              flush=True)
        return cell

    checks = _checks()
    print("[arm] pre-read artifact read: C1-C4 all pass", flush=True)

    ev = check_events()
    sched, names = D.tier_schedule_era(D.ERA_CHECK)
    cfg = D.era(D.ERA_CHECK)
    cap_sched = TC.cap_schedule(1)
    print("[arm] %d check-quadrant events over %d tickers; market over %d half-1 names ..."
          % (len(ev), ev["ticker"].nunique(), len(names)), flush=True)
    market = DA.build_market(names, sched, D.K_PRIMARY, lo=cfg["lo"], hi=cfg["hi"])
    terminal = DA.terminal_names()
    print("[arm] market built in %.0fs, %d sessions" % (time.time() - t0,
                                                        len(market["dates"])), flush=True)

    n_eq = 0
    try:
        from valuation.edge import research_log as RL
        n_eq = RL.detail()["by_domain"]["equity"]
    except Exception:                                                       # noqa: BLE001
        pass

    out = {"item": "INSIDER-WIDE", "part": "the one check-quadrant read",
           "register": "PREREG_insider_cluster_wide.md", "register_commit": "1cc8b7e",
           "trials_booked_at": "dfbccc4", "stage1_register_commit": "fd87870",
           "era": {"name": D.ERA_CHECK, "lo": cfg["lo"], "hi": cfg["hi"],
                   "ticker_half": cfg["ticker_half"],
                   "half_boundary": CHECK_HALF_BOUNDARY},
           "governing_cell": GOVERNING,
           "pre_read_checks": {"all_pass": True,
                               "C1_build_mean_pp": checks["checks"]["C1"].get("mean_pp"),
                               "C4_check_events": checks["checks"]["C4"].get("n_events")},
           "bars": {"t_bar": T_BAR,
                    "t_bar_LABEL": "UNCALIBRATED (V2G, R1-VAR) -- no X7 or CORRECTED-FLOORS "
                                   "figure transfers to a clustered event-time mean",
                    "cost": "SIZE-TIERED per event from fundamental_panel.one_way_cost_bps; "
                            "stage 1's single 0.67pp floor is SUPERSEDED (register section 3)",
                    "bh_q": BH_Q, "bh_k_fixed": BH_K,
                    "permutation_draws": PERMUTATION_DRAWS,
                    "min_names_per_date": MIN_NAMES_PER_DATE},
           "power_declared_before_the_read": POWER_DECLARED,
           "cells": {}}

    for h in (H_PRIMARY, H_REPORTED):
        for label, floor, verdicts in CELLS:
            name = "%s_h%d" % (label, h)
            print("[arm] scoring %s ..." % name, flush=True)
            c = score(ev, market, sched, terminal, names, cfg["lo"], cfg["hi"], h, floor,
                      CHECK_HALF_BOUNDARY, cap_sched, name)
            c["cell"] = label
            c["carries_a_verdict"] = bool(verdicts and h == H_PRIMARY)
            c["is_governing"] = bool(label == GOVERNING and h == H_PRIMARY)
            out["cells"][name] = c
            if "mean_pp" in c:
                print("    n %-5d | mkt %+.4fpp t %+.3f/%+.3f | null p95 %.4f | cost %.3f -> NET "
                      "%+.4fpp | A1-A4 %s"
                      % (c["n_events_scored"], c["mean_pp"], c["t_date"], c["t_ticker"],
                         c["null_p95_pp"], c["roundtrip_cost_pp_mean"], c["net_of_cost_pp"],
                         c["A1_A4_all_pass"]), flush=True)

    # ------------------------------------------------------------------- §4 A5, Benjamini-Hochberg
    batch = sorted((out["cells"][n]["p_two_sided_worst"], n)
                   for n in out["cells"]
                   if out["cells"][n].get("carries_a_verdict") and "mean_pp" in out["cells"][n])
    bh = {"q": BH_Q, "k_fixed": BH_K, "k_in_batch": len(batch), "cells": {}}
    if len(batch) != BH_K:
        bh["NOTE"] = ("k is FIXED at %d in the register and is NEVER shrunk; %d verdict cells "
                      "were scoreable. A smaller batch is reported, never used to lower the "
                      "threshold." % (BH_K, len(batch)))
    for i, (p, n) in enumerate(batch, 1):
        thr = i * BH_Q / BH_K
        bh["cells"][n] = {"p": p, "threshold": thr, "survives": bool(p <= thr)}
    out["A5_bh"] = bh
    out["excluded_from_bh"] = {
        "cells": sorted(n for n, c in out["cells"].items() if not c.get("carries_a_verdict")),
        "WHY": ("section 2c declares cap_ge_2bn and cap_ge_100m as REPORTED WITH NO VERDICT and "
                "h=126 as REPORTED ONLY, before the read. They carry no p to correct, and k stays "
                "FIXED at 3 -- charter Stage 1a's rule that an excluded arm is excluded WITH the "
                "exclusion declared in the register."),
    }

    # ------------------------------------------------------------------------------- the verdicts
    for n, c in out["cells"].items():
        if not c.get("carries_a_verdict"):
            c["verdict"] = "REPORTED -- NO VERDICT"
            c["verdict_note"] = ("declared REPORTED-ONLY in the register before the read "
                                 "(section 2b for h=126, section 2c for the two cap cells), so "
                                 "it may not be promoted to a result afterwards")
            continue
        a5 = out["A5_bh"]["cells"].get(n, {}).get("survives", False)
        c["A5_bh_survives"] = bool(a5)
        pw = POWER_DECLARED.get(c["cell"], {})
        c["power_declared_gross"] = pw.get("gross")
        c["power_declared_net"] = pw.get("net")
        if c.get("A1_A4_all_pass") and a5:
            c["verdict"] = "CONFIRMED"
            c["verdict_note"] = ("all four clauses of section 4 plus BH at q=0.10 with k fixed "
                                 "at 3, on the check quadrant, read once")
        elif (pw.get("gross") or 0.0) < 0.50:
            c["verdict"] = "UNDERPOWERED"
            c["verdict_note"] = (
                "section 5 declared this cell's power BEFORE the read at %.1f%% gross and %.1f%% "
                "net, both below half, and section 4's grammar makes a cell that cannot see its "
                "own effect return UNDERPOWERED rather than NOT CONFIRMED. A null here is "
                "INVISIBLE rather than ABSENT and is not evidence the effect is not there."
                % (100 * (pw.get("gross") or 0.0), 100 * (pw.get("net") or 0.0)))
        else:
            c["verdict"] = "NOT CONFIRMED"
            c["verdict_note"] = (
                "at least one of section 4's four clauses failed in a cell whose power was "
                "declared at %.1f%% gross BEFORE the read, so the design could see the build "
                "quadrant's own effect and did not. The MDE travels with it."
                % (100 * (pw.get("gross") or 0.0)))

    out["hlz_hurdle_reported_not_gated"] = {
        "equity_N": n_eq, "hurdle": (ST.hlz_hurdle(n_eq) if n_eq else None),
        "WHY_NOT_GATED": ("R4's measured reason, and section 4 A3 says so in advance: HLZ prices "
                          "the BEST OF N draws, and this read is a single pre-registered "
                          "confirmation of one published hypothesis rather than the best of a "
                          "search over this record."),
    }
    out["ADOPTS_NOTHING"] = ("No file under valuation/ changes and no book is declared. If this "
                            "confirms, the next rung is a forward paper book in SHARES, which is "
                            "Don's decision and not this lane's.")
    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[arm] verdicts: %s"
          % json.dumps({n: c.get("verdict") for n, c in out["cells"].items()
                        if c.get("carries_a_verdict")}), flush=True)
    print("[arm] GOVERNING cell %s_h%d -> %s"
          % (GOVERNING, H_PRIMARY, out["cells"]["%s_h%d" % (GOVERNING, H_PRIMARY)]["verdict"]),
          flush=True)
    print("[arm] wrote %s in %.0fs" % (p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
