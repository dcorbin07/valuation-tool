# -*- coding: utf-8 -*-
"""`STAGE1-BATCH1` — run the free pre-outcome kills. ZERO TRIALS HERE; no outcome is computed.

Register `PREREG_stage1_batch1.md`. **No forward return is read anywhere in this file**, pinned
by test: a pre-outcome control can only BLOCK (`MB1-SEL`), which is what makes these free and why
they run FIRST, in their own pass (`O10`).

Two passes, because four arms need panels that did not exist when the register was committed:

  * `--part a` — **A3, A6, A8, A10**: coverage and spine kills off the price export, the ADV
    inputs, the EVENTS cache and `S25`'s dated sector map.
  * `--part b` — **A1, A2a, A7, A11**: the `keep_numbers` panel's own columns, plus A2a's
    inertness against the `residual_momentum=True` build.

**A2b and A9 are reported with their kills NOT YET RUN**, with the reason, rather than silently
omitted: each needs a signal built first (a 36-month residual series; a dated IBES link), and a
costume kill cannot be evaluated before the signal exists.
"""
from __future__ import annotations

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

import scripts.stage1_kills as K                                            # noqa: E402
from scripts.index_best import _data_root, data_candidates                  # noqa: E402

PANEL = "UNIVERSE_BIAS_PANEL_full.pkl"
KEEPNUM = "S1_PANEL_keepnum.pkl"
RESMOM = "S1_PANEL_keepnum_resmom.pkl"


def _fa():
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    return data, os.path.join(data, "free_analysis")


# ---------------------------------------------------------------------------------------------
# A3 — information discreteness: daily-observation coverage over the 12m formation window
# ---------------------------------------------------------------------------------------------
def kill_a3(data, b):
    """Share of build-quadrant rows with >= 200 daily observations in the trailing 12 months.

    **Year-relative, with a floor.** `MC12` read exactly **0.000** on 2001 against a fixed >=250
    bar because the NYSE closed after 9/11 and the year held 248 sessions — and its year-relative
    replacement then went **vacuous on 1997**. So the requirement is
    `min(MIN_DAILY_OBS, that window's own session count)` and a window whose own count falls
    below `MIN_PLAUSIBLE_SESSIONS` is reported rather than scored.
    """
    pdir = os.path.join(data, "full2009", "backtest", "prices")
    want = sorted(b["ticker"].unique())
    dates = sorted(b["date"].unique())
    # one pass per ticker; count sessions in each trailing 12m window we actually need
    need = {}
    for d in dates:
        need[str(d)[:10]] = (str(pd.Timestamp(d) - pd.Timedelta(days=365))[:10], str(d)[:10])
    # the market's own session count per window, from a long-history name present throughout
    ref = None
    for t in ("AAPL", "MSFT", "JNJ"):
        p = os.path.join(pdir, "%s.csv" % t)
        if os.path.exists(p):
            ref = pd.read_csv(p)
            break
    sessions = {}
    if ref is not None:
        rd = ref["date"].astype(str)
        for k, (lo, hi) in need.items():
            sessions[k] = int(((rd > lo) & (rd <= hi)).sum())
    ok = tot = 0
    thin_windows = {k: v for k, v in sessions.items() if v < K.MIN_PLAUSIBLE_SESSIONS}
    per_t = {}
    t0 = time.time()
    for i, t in enumerate(want):
        p = os.path.join(pdir, "%s.csv" % t)
        if not os.path.exists(p):
            per_t[t] = 0
            continue
        rd = pd.read_csv(p)["date"].astype(str).values
        per_t[t] = rd
        if i % 500 == 0 and i:
            print("    a3 %d/%d tickers, %.0fs" % (i, len(want), time.time() - t0), flush=True)
    for d in dates:
        k = str(d)[:10]
        lo, hi = need[k]
        bar = min(K.MIN_DAILY_OBS, sessions.get(k, K.MIN_DAILY_OBS))
        g = b[b["date"] == d]
        for t in g["ticker"]:
            tot += 1
            rd = per_t.get(t)
            if rd is None or isinstance(rd, int):
                continue
            n = int(((rd > lo) & (rd <= hi)).sum())
            if n >= bar:
                ok += 1
    share = ok / max(1, tot)
    return K.verdict("A3", share >= K.COVERAGE_FLOOR, {
        "rows": tot, "with_enough_daily_obs": ok, "share": share,
        "bar": K.COVERAGE_FLOOR, "min_daily_obs": K.MIN_DAILY_OBS,
        "year_relative": True, "min_plausible_sessions": K.MIN_PLAUSIBLE_SESSIONS,
        "windows_below_plausible_floor": thin_windows,
        "session_counts_sample": dict(list(sessions.items())[:4]),
    })


# ---------------------------------------------------------------------------------------------
# A6 — N1 small/mid core: the NEW ADV coverage kill (register §4)
# ---------------------------------------------------------------------------------------------
def kill_a6(data, fa, b):
    """Point-in-time ADV computable on >= 0.70 of build-quadrant rows.

    `UNIVERSE-BIAS` part 3 measured the ADV inputs at a **0.2617** name share on the corrected
    universe, because `MC9_SEP_ADV.pkl` and `B13_ADV_PANEL.pkl` were built on `data/backtest`.
    **A name with no ADV observation fails an ADV floor exactly as a genuinely illiquid name
    does**, so without this kill A6's band becomes *"small AND present in the old ADV input"*.
    """
    names = set()
    p = os.path.join(fa, "MC9_SEP_ADV.pkl")
    if os.path.exists(p):
        d = pd.read_pickle(p)
        if isinstance(d, dict):
            names |= {str(t).upper() for t in (d.get("by_ticker") or {})}
    cells = set()
    p = os.path.join(fa, "B13_ADV_PANEL.pkl")
    if os.path.exists(p):
        a = pd.read_pickle(p)
        if isinstance(a, pd.DataFrame) and {"date", "ticker"} <= set(a.columns):
            cells = {(str(x)[:10], str(t).upper()) for x, t in zip(a["date"], a["ticker"])}
            names |= {t for _d, t in cells}
    rows = [(str(d)[:10], str(t).upper()) for d, t in zip(b["date"], b["ticker"])]
    by_name = sum(1 for _d, t in rows if t in names)
    by_cell = sum(1 for r in rows if r in cells)
    share = by_name / max(1, len(rows))
    return K.verdict("A6", share >= K.COVERAGE_FLOOR, {
        "rows": len(rows), "rows_with_adv_capable_name": by_name, "share": share,
        "rows_in_crsp_adv_cells": by_cell,
        "panel_names": int(b["ticker"].nunique()),
        "names_with_adv_input": len({t for _d, t in rows if t in names}),
        "bar": K.COVERAGE_FLOOR,
        "note": "the ADV inputs were built on data/backtest, so this is a property of the INPUT "
                "and not of the names' liquidity; extending them to the corrected universe is a "
                "prep job, not an analysis",
    })


# ---------------------------------------------------------------------------------------------
# A8 — earnings-surprise drift: spine coverage and announcements per ticker-year
# ---------------------------------------------------------------------------------------------
def kill_a8(data, b):
    """EVENTS code 22 is the announcement spine. `bulk.py` warns ~2.83 code-22 dates per
    ticker-year on the broad universe; `O6`/`O7` measured 3.96-4.14 on megacaps. The band is
    [3.0, 5.0] around the ~4 expected, registered before the look."""
    from valuation.edge.bulk import _load_cache
    ev = _load_cache("events", os.path.join(data, "bulk", "prepared")) or {}
    want = set(b["ticker"].unique())
    lo, hi = str(b["date"].min())[:10], str(b["date"].max())[:10]
    per_t, with_any = {}, 0
    for t in want:
        rows = ev.get(t) or []
        n = 0
        for r in rows:
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                d, codes = str(r[0])[:10], r[1]
            elif isinstance(r, dict):
                d, codes = str(r.get("date"))[:10], r.get("eventcodes") or r.get("codes")
            else:
                continue
            if not (lo <= d <= hi):
                continue
            # THE CACHE SHAPE IS `[(date, [codes])]` -- a LIST of code strings. My first cut
            # did `str(codes).split(",")`, which turns ['22','71','91'] into "['22'", " '71'",
            # " '91']" and can NEVER match "22" -- a parser that returned a confident
            # spine coverage of exactly 0.0000 against a cache holding 17,779 names, when
            # O6/O7 measured ~4 code-22 dates per ticker-year from this same cache. Caught by
            # disbelieving the zero, which is the only way this class of defect surfaces.
            if isinstance(codes, (list, tuple, set)):
                have = {str(x).strip() for x in codes}
            else:
                have = {x.strip() for x in str(codes or "").replace("|", ",").split(",")}
            if "22" in have:
                n += 1
        per_t[t] = n
        if n:
            with_any += 1
    years = max(1e-9, (pd.Timestamp(hi) - pd.Timestamp(lo)).days / 365.25)
    counts = np.array([v for v in per_t.values()], dtype=float)
    covered = with_any / max(1, len(want))
    ann_per_year = float(np.median(counts[counts > 0]) / years) if (counts > 0).any() else 0.0
    ok = (covered >= K.COVERAGE_FLOOR
          and K.ANN_PER_YEAR_BAND[0] <= ann_per_year <= K.ANN_PER_YEAR_BAND[1])
    return K.verdict("A8", ok, {
        "names": len(want), "names_with_any_code22": with_any, "spine_coverage": covered,
        "years_spanned": years, "median_announcements_per_ticker_year": ann_per_year,
        "band": list(K.ANN_PER_YEAR_BAND), "coverage_bar": K.COVERAGE_FLOOR,
        "events_cache_names": len(ev),
    })


# ---------------------------------------------------------------------------------------------
# A10 — industry momentum: the DATED sector map's coverage (register §5)
# ---------------------------------------------------------------------------------------------
def kill_a10(data, b):
    """`S25`'s dated GICS map, not the panel's `sector` column, which is today's classification
    applied to historical rows. A date before a name's first classification must return
    `NOT_COVERED` and never the first span — the property `S25` pinned."""
    try:
        from valuation.edge import sector_map as SM
    except Exception as e:
        return K.verdict("A10", None, {"error": "sector_map unavailable: %s" % e})
    path = os.path.join(data, "free_analysis", "S25_SECTOR_MAP.json")
    if not os.path.exists(path):
        return K.verdict("A10", None, {"error": "S25_SECTOR_MAP.json absent at %s" % path})
    try:
        m = SM.load(path)
    except Exception as e:
        return K.verdict("A10", None, {"error": "sector_map.load failed: %s: %s"
                                                % (type(e).__name__, e), "map_path": path})
    rows = [(str(d)[:10], str(t).upper()) for d, t in zip(b["date"], b["ticker"])]
    # `at()` returns a DICT with a three-state `state`, and its own docstring warns that a
    # caller reading `sector` without `state` treats "we do not know" as "no sector" -- which
    # the engine then turns into 0.12 without saying so. So the state is counted, and a row
    # counts as resolved only on state OK.
    ok_n = 0
    states = {}
    cache = {}
    for d, t in rows:
        key = (t, d)
        r = cache.get(key)
        if r is None:
            try:
                r = m.at(t, d)
            except Exception as e:
                r = {"state": "ERROR:%s" % type(e).__name__}
            cache[key] = r
        st = str(r.get("state"))
        states[st] = states.get(st, 0) + 1
        if st == "OK" and r.get("sector"):
            ok_n += 1
    share = ok_n / max(1, len(rows))
    return K.verdict("A10", share >= K.COVERAGE_FLOOR, {
        "rows": len(rows), "dated_sector_resolved": ok_n, "share": share,
        "bar": K.COVERAGE_FLOOR, "states": states})


def part_a(argv=None) -> int:
    data, fa = _fa()
    panel = pd.read_pickle(os.path.join(fa, PANEL))
    b, cen = K.build_quadrant(panel)
    print("BUILD quadrant: %s" % json.dumps(cen), flush=True)
    out = {"item": "STAGE1-BATCH1", "part": "kills a (A3, A6, A8, A10)", "trials": 0,
           "quadrant": cen, "no_outcome_read": True, "kills": {}}
    for fn, label in ((kill_a6, "A6"), (kill_a8, "A8"), (kill_a10, "A10"), (kill_a3, "A3")):
        print("\n--- %s ---" % label, flush=True)
        t0 = time.time()
        try:
            v = fn(data, fa, b) if label == "A6" else fn(data, b)
        except Exception as e:
            v = K.verdict(label, None, {"error": "%s: %s" % (type(e).__name__, e)})
        out["kills"][label] = v
        print("  %s kill_passes=%s  %.0fs  %s"
              % (label, v["kill_passes"], time.time() - t0,
                 json.dumps({k: x for k, x in v["detail"].items()
                             if not isinstance(x, dict)})[:260]), flush=True)
    json.dump(out, io.open(os.path.join(fa, "STAGE1_KILLS_A.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\nKILLS A DONE")
    return 0


# ---------------------------------------------------------------------------------------------
# A1 — intangible-adjusted value: the THREE-WAY coverage reading
# ---------------------------------------------------------------------------------------------
#: The burn-in is UNDER-SPECIFIED in both the scout's draft and the register -- each says "a
#: burn-in before a name is scoreable" without fixing the number. Rather than pick one AFTER the
#: register (which would be choosing a parameter post-registration), coverage is reported at a
#: RANGE and the kill's verdict is stated as invariant across it, or not, by measurement.
A1_BURN_IN_YEARS = (3, 5, 8, 10)
#: AND THE VERDICT IS READ AT 10, ON AN ANCHOR THAT PREDATES THIS REGISTER. My register and the
#: scout's draft both say "a burn-in" without fixing it, and the coverage is NOT invariant across
#: a plausible range -- so the kill would otherwise be decided by a parameter chosen after the
#: register. PREREG_DRAFT_w28_total_q.md froze THIS construction's burn-in at >= 10 FISCAL YEARS,
#: with its own stated reason: "a perpetual inventory that has not converged is a different
#: variable." That is an external anchor inside this project, on this exact construction,
#: committed before this register -- E-6's discipline. THE COUNTERFACTUAL MATTERS AND IS
#: RECORDED: had W-28 frozen a SHORT burn-in, A1 would have PASSED, so the anchor is doing real
#: work rather than being picked to produce a kill.
A1_VERDICT_BURN_IN = 10


def kill_a1(data, b):
    """Share of build-quadrant rows with a computable `K_int`, as THREE numbers.

    **R&D is LEGITIMATELY ZERO for most firms, not missing.** Counting a true zero as missing
    understates coverage and sends the arm to the incumbent fallback for firms whose intangible
    capital really is ~0; counting missing as zero silently asserts a fact. So the reading is
    **truly non-null / structurally zero / absent**, and the 0.70 bar is read on
    `non-null + structural zero` -- the register's own rule.
    """
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import _ttm

    class _C:
        wrds_data_dir = os.path.join(data, "full2009", "backtest")

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        return K.verdict("A1", None, {"error": "provider not ready: %s" % msg})

    want = sorted(b["ticker"].unique())
    hist = {}
    for t in want:
        hist[t] = sorted(prov.fundamentals_history(t) or [],
                         key=lambda r: (r.get("datekey") or r.get("date") or ""))

    def _first_datekey(rows):
        for r in rows:
            dk = r.get("datekey") or r.get("date")
            if dk:
                return str(dk)[:10]
        return None

    first = {t: _first_datekey(hist.get(t) or []) for t in want}
    out = {"rows": 0, "by_burn_in": {}}
    rows = [(str(d)[:10], t) for d, t in zip(b["date"], b["ticker"])]
    out["rows"] = len(rows)

    # one TTM read per (date, ticker) for each of rnd and sgna, cached
    cache = {}
    for as_of, t in rows:
        key = (as_of, t)
        if key in cache:
            continue
        rws = hist.get(t) or []
        rnd = _ttm(rws, as_of, ("rnd",))
        sga = _ttm(rws, as_of, ("sgna",))
        def _v(d, k):
            if d is None:
                return None
            try:
                x = float(d.get(k))
                return x if x == x else None
            except (TypeError, ValueError):
                return None
        cache[key] = (_v(rnd, "rnd"), _v(sga, "sgna"))

    for by in A1_BURN_IN_YEARS:
        nonnull = zero = absent = short = 0
        for as_of, t in rows:
            f = first.get(t)
            if not f or (pd.Timestamp(as_of) - pd.Timestamp(f)).days < by * 365:
                short += 1
                continue
            r, g = cache[(as_of, t)]
            if g is None:
                absent += 1                 # SG&A is the org-capital leg; no SG&A, no K_org
            elif r is None:
                absent += 1
            elif r == 0.0:
                zero += 1                   # R&D legitimately zero -- K_know is 0, not unknown
            else:
                nonnull += 1
        tot = max(1, len(rows))
        share = (nonnull + zero) / tot
        out["by_burn_in"][str(by)] = {
            "truly_non_null": nonnull, "structurally_zero": zero, "absent": absent,
            "short_history": short, "share_nonnull_plus_zero": share,
            "passes": bool(share >= K.COVERAGE_FLOOR)}

    verdicts = {v["passes"] for v in out["by_burn_in"].values()}
    out["bar"] = K.COVERAGE_FLOOR
    out["verdict_invariant_across_burn_in"] = (len(verdicts) == 1)
    out["verdict_burn_in_years"] = A1_VERDICT_BURN_IN
    out["verdict_anchor"] = ("PREREG_DRAFT_w28_total_q.md froze this construction's burn-in at "
                             ">= 10 fiscal years -- an anchor predating this register, on this "
                             "exact construction (E-6). Had it frozen a SHORT burn-in, A1 would "
                             "have PASSED.")
    out["note"] = ("the burn-in is UNDER-SPECIFIED in the draft and the register; coverage is "
                   "reported at 3/5/8 years and the verdict is stated as invariant across that "
                   "range, or not, BY MEASUREMENT rather than by picking a value after the "
                   "register")
    at = out["by_burn_in"].get(str(A1_VERDICT_BURN_IN))
    passed = (bool(at["passes"]) if at else None)
    return K.verdict("A1", passed, out)


# ---------------------------------------------------------------------------------------------
# A2a — the shipped residual_momentum toggle: it must not be INERT
# ---------------------------------------------------------------------------------------------
def kill_a2a(fa, b):
    """Per-date rank correlation of the toggled composite against the untoggled one must be
    **< 0.995**. `SECTOR-NEUTRAL-B6`'s inertness check, and `S15`, which was *"nearly inert"* at
    0.9879 and told us almost nothing."""
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT
    pa = os.path.join(fa, KEEPNUM)
    pb = os.path.join(fa, RESMOM)
    for q in (pa, pb):
        if not os.path.exists(q):
            return K.verdict("A2a", None, {"error": "panel absent: %s" % q})
    A = pd.read_pickle(pa)
    B = pd.read_pickle(pb)
    keys = set(zip(b["date"].astype(str), b["ticker"]))
    cols = [c for c in DEPLOYED if c in A.columns and c in B.columns]
    w = {c: BASE_WEIGHT for c in cols}
    rs = []
    for d in sorted(b["date"].unique()):
        ga = A[(A["date"] == d)]
        gb = B[(B["date"] == d)]
        ga = ga[[(str(x), t) in keys for x, t in zip(ga["date"], ga["ticker"])]]
        gb = gb[[(str(x), t) in keys for x, t in zip(gb["date"], gb["ticker"])]]
        if len(ga) < 20 or len(gb) < 20:
            continue
        ca = composite_from_frame(ga, cols, w, zscore)
        cb = composite_from_frame(gb, cols, w, zscore)
        fa_ = pd.Series(list(ca), index=list(ga["ticker"]))
        fb_ = pd.Series(list(cb), index=list(gb["ticker"]))
        j = fa_.dropna().index.intersection(fb_.dropna().index)
        if len(j) < 20:
            continue
        r = fa_[j].rank().corr(fb_[j].rank())
        if r == r:
            rs.append(float(r))
    if not rs:
        return K.verdict("A2a", None, {"error": "no comparable date"})
    mean_r = float(np.mean(rs))
    return K.verdict("A2a", mean_r < K.INERT_BAR, {
        "mean_per_date_rank_corr": mean_r, "min": float(np.min(rs)), "max": float(np.max(rs)),
        "dates": len(rs), "bar": K.INERT_BAR,
        "reading": ("NOT INERT -- the toggle moves the ranking" if mean_r < K.INERT_BAR
                    else "INERT -- the toggle barely moves the ranking, so the arm carries no "
                         "verdict (S15 was nearly inert at 0.9879 and told us almost nothing)")})


# ---------------------------------------------------------------------------------------------
# A7 and A11 — the keep_numbers panel's own columns
# ---------------------------------------------------------------------------------------------
def kill_column(fa, b, arm, col, extra=None):
    q = os.path.join(fa, KEEPNUM)
    if not os.path.exists(q):
        return K.verdict(arm, None, {"error": "panel absent: %s" % q})
    A = pd.read_pickle(q)
    keys = set(zip(b["date"].astype(str), b["ticker"]))
    sub = A[[(str(x), t) in keys for x, t in zip(A["date"], A["ticker"])]]
    d = _nonnull(sub, col)
    d["bar"] = K.COVERAGE_FLOOR
    if extra:
        d.update(extra)
    return K.verdict(arm, (None if not d["present"] else d["share"] >= K.COVERAGE_FLOOR), d)


def _nonnull(frame, col):
    if col not in frame.columns:
        return {"present": False, "share": 0.0, "rows": int(len(frame)), "column": col}
    v = pd.to_numeric(frame[col], errors="coerce")
    return {"present": True, "column": col, "rows": int(len(frame)),
            "nonnull": int(v.notna().sum()), "share": float(v.notna().mean())}


def part_b(argv=None) -> int:
    data, fa = _fa()
    panel = pd.read_pickle(os.path.join(fa, PANEL))
    b, cen = K.build_quadrant(panel)
    print("BUILD quadrant: %s" % json.dumps(cen), flush=True)
    out = {"item": "STAGE1-BATCH1", "part": "kills b (A1, A2a, A7, A11)", "trials": 0,
           "quadrant": cen, "no_outcome_read": True, "kills": {}}

    for label, fn in (("A7", lambda: kill_column(
                           fa, b, "A7", "z_neg_issuance",
                           {"winsorisation": "the SHIPPED zscore's 2% clip, DECLARED in the "
                                             "register before the look (S21: removing the clip "
                                             "moves alpha +2.43pp/yr and is the FRAGILE "
                                             "estimator)"})),
                      ("A11", lambda: kill_column(
                           fa, b, "A11", "z_high_prox",
                           {"near_duplicate_disclosure":
                            "|rho| vs the momentum theme is already measured at 0.7596 (max "
                            "0.9502), so a pass is read as MOMENTUM MEASURED DIFFERENTLY unless "
                            "the incremental IC survives residualising on momentum ALONE -- a "
                            "required second reading, pre-committed"})),
                      ("A2a", lambda: kill_a2a(fa, b)),
                      ("A1", lambda: kill_a1(data, b))):
        print("\n--- %s ---" % label, flush=True)
        t0 = time.time()
        try:
            v = fn()
        except Exception as e:
            v = K.verdict(label, None, {"error": "%s: %s" % (type(e).__name__, e)})
        out["kills"][label] = v
        print("  %s kill_passes=%s  %.0fs  %s"
              % (label, v["kill_passes"], time.time() - t0,
                 json.dumps({k: x for k, x in v["detail"].items()
                             if not isinstance(x, dict)})[:300]), flush=True)

    # A2b and A9: reported NOT YET RUN with the reason, never silently omitted
    out["kills"]["A2b"] = K.verdict("A2b", None, {
        "status": "KILL NOT YET RUN",
        "why": "the momentum-costume kill needs the SIGNAL first -- a 36-month residual return "
               "series per name against the panel's own value-weighted market -- and a costume "
               "bar cannot be evaluated before the signal exists"})
    out["kills"]["A9"] = K.verdict("A9", None, {
        "status": "KILL NOT YET RUN",
        "why": "the size-costume kill needs a DATED IBES link first (ibes_statsum_epsus is on "
               "disk at 51 chunks and ibes_id carries sdates), and that link is the shared "
               "infrastructure the record already lists as owed -- MB15's rule is that the "
               "instrument is validated BEFORE any hypothesis reads it"})

    json.dump(out, io.open(os.path.join(fa, "STAGE1_KILLS_B.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\nKILLS B DONE")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "a" in argv or "--part-a" in argv:
        return part_a()
    if "b" in argv or "--part-b" in argv:
        return part_b()
    print("usage: python -m scripts.stage1_kills_run a   # A3 A6 A8 A10\n"
          "       python -m scripts.stage1_kills_run b   # A1 A2a A7 A11")
    return 2


if __name__ == "__main__":
    sys.exit(main())
