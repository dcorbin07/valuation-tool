#!/usr/bin/env python3
"""
FIDELITY-2 — rebuild `institutional` and `insider` to the PANEL's definitions, then re-run the
SAME gate.

Registered in `PREREG_fidelity2_rebuild.md`, committed alone at `ef765fc` before this file
existed. The bar is NOT re-derived here: it is imported from `scripts/theme_restoration.py`,
which is the gate `PREREG_theme_restoration.md` fixed at `1d12822`.

WHAT DIVERGED (diagnosed at code level in the register, not guessed):

  institutional  the formula matches; both inputs diverge. The panel's `_inst_accum` reads
                 `totalvalue` FIRST -- DOLLARS -- and my build used SHARES on purpose. And the
                 panel at its last cross-section uses the 2025-09-30 vs 2025-06-30 quarters at a
                 45-day lag, where I used 2026-03-31 vs 2025-12-31. No overlap.

  insider        a different estimator plus a fabricated neutral. The panel sums SIGNED DOLLARS
                 unweighted and returns None when the window is empty; the live scorer sums
                 code-weighted, role-weighted SQRT of value and returns 50.0 when quiet, which
                 put 179 of 500 names in one tie block.

    python -m scripts.fidelity2_rebuild fetch13f    # two SEC datasets, ~172MB
    python -m scripts.fidelity2_rebuild fetch4      # date-aligned Form 4 crawl
    python -m scripts.fidelity2_rebuild score       # offline; the gate
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import live_theme_sources as M          # noqa: E402
from scripts import theme_restoration as R           # noqa: E402

# PREREG §2.1 — the quarters the panel would have used at its own cross-section, at the 45-day
# filing lag. Fixed at ef765fc.
PERIOD_CURR_A = "30-SEP-2025"
PERIOD_PRIOR_A = "30-JUN-2025"
WINDOW_CURR_A = "01sep2025-30nov2025"
WINDOW_PRIOR_A = "01jun2025-31aug2025"

# PREREG §2.2 — the panel's own insider constants (`fundamental_panel.py:_insider_score_at`).
INSIDER_LOOKBACK_D = 90
INSIDER_TANH_SCALE = 5e6
INSIDER_BUY_BONUS = 2.0
INSIDER_BUY_CAP = 10.0

ROOT = M.DEFAULT_ROOT
F4_DIR = os.path.join(ROOT, "form4_aligned")
F4_DIR_LIVE = os.path.join(ROOT, "form4_live")
AGG_A = os.path.join(ROOT, "13f_aggregate_aligned.json")
OUT = os.path.join("data", "free_analysis", "FIDELITY2.json")


def _panel_asof() -> str:
    _x, asof = R.panel_cross_section()
    return asof


# ------------------------------------------------------------------------------------------
# institutional — the aligned quarters, and DOLLARS
# ------------------------------------------------------------------------------------------

def fetch13f() -> dict:
    guard = M.Guard(min_interval=M.SEC_MIN_INTERVAL_S)
    agg = {"by_period": {}, "shape": {}}
    for window, period in ((WINDOW_CURR_A, PERIOD_CURR_A), (WINDOW_PRIOR_A, PERIOD_PRIOR_A)):
        path = M.download_dataset(ROOT, window, guard)
        print(f"  aggregating {period} from {os.path.basename(path)}", flush=True)
        # `aggregate_13f` returns a WRAPPER {period, shape, cusips}; the flat cusip->record map
        # `join_13f` wants is `["cusips"]`. Storing the wrapper made this print "3 CUSIPs" —
        # literally its three keys — against V2G's 22,000, which is the only reason it was
        # caught before the join silently produced an empty column.
        one = M.aggregate_13f(path, period)
        agg["by_period"][period] = one["cusips"]
        agg["shape"][period] = one["shape"]
        print(f"    {one['shape']['cusips']} CUSIPs, {one['shape']['filers']} filers, "
              f"{one['shape']['infotable_rows_kept']} share rows", flush=True)
    M._atomic_write_json(AGG_A, agg)
    print(f"wrote {AGG_A}")
    return agg


def institutional_columns() -> dict:
    """`inst_accum` on DOLLARS and `sm_breadth` on holders, over the panel-aligned quarters.

    The join, the anchor and MIN_HOLDERS are reused unchanged from V2G: they decide WHICH ISSUER
    a row is, not what is measured, and they were never the suspect.
    """
    agg = M._read_json(AGG_A)
    if not agg:
        raise SystemExit("run `fetch13f` first")
    served = M.load_served()
    # `join_13f` reads M.PERIOD_CURR / M.PERIOD_PRIOR from module scope, so point them at the
    # aligned pair rather than duplicating the join. Restored in `finally` so nothing else in
    # this process sees the swap.
    was = (M.PERIOD_CURR, M.PERIOD_PRIOR)
    M.PERIOD_CURR, M.PERIOD_PRIOR = PERIOD_CURR_A, PERIOD_PRIOR_A
    try:
        joined = M.join_13f(ROOT, served, agg)
    finally:
        M.PERIOD_CURR, M.PERIOD_PRIOR = was

    curr = agg["by_period"][PERIOD_CURR_A]
    prior = agg["by_period"][PERIOD_PRIOR_A]
    accum, breadth = {}, {}
    for tkr, d in joined.items():
        accum[tkr] = None
        breadth[tkr] = d.get("sm_breadth")
        cusip = d.get("cusip")
        if not cusip or d.get("rung") in ("anchor_failed", "too_few_holders", "ambiguous",
                                          "unmatched"):
            continue
        c, p = curr.get(cusip), prior.get(cusip)
        # DOLLARS, mirroring the panel's `totalvalue`-first field order.
        if c and p and p.get("value"):
            accum[tkr] = c["value"] / p["value"] - 1.0
    z = M._zscore
    return {"inst_accum": accum, "sm_breadth": breadth,
            "institutional": _mean(list(accum), z(accum), z(breadth)),
            "join": joined}


def _mean(tickers, *cols) -> dict:
    """`build_columns`'s nested `_mean`, reproduced exactly.

    It is a closure inside V2G's `build_columns` rather than a module function, so it cannot be
    imported. Reproduced rather than approximated: mean over the non-None FINITE values, None
    when there are none. `factors.py:267` combines the two z-scores this way, and a different
    null-handling rule here would change the theme for exactly the names where one input is
    missing — which is most of the disagreement this task is chasing.
    """
    out = {}
    for t in tickers:
        vals = [c.get(t) for c in cols]
        vals = [v for v in vals if v is not None and math.isfinite(v)]
        out[t] = (sum(vals) / len(vals)) if vals else None
    return out


# ------------------------------------------------------------------------------------------
# insider — the panel's statistic, on the panel's window
# ------------------------------------------------------------------------------------------

def parse_form4_signed(xml: str) -> list:
    """[(code, signed_value_usd)] — the panel's quantity, which the live parser does not expose.

    THE SIGN IS THE WHOLE POINT AND IT IS NOT IN `value_usd`. `screener/insider._parse_form4`
    returns `{code, value_usd, role_mult}` with `value_usd = shares x price`, both positive, and
    recovers direction through CODE_WEIGHTS instead. The panel sums SF2's `transactionshares x
    transactionpricepershare`, and SF2's share count is SIGNED — negative on a disposal.

    So the faithful mirror reads `transactionAcquiredDisposedCode` (A = acquired, D = disposed)
    and signs the value with it. Summing the live parser's unsigned values would make `net` a
    gross turnover figure, which is a different quantity again — the exact error this whole task
    exists to stop.
    """
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    out = []
    for tx in root.iter():
        if not tx.tag.endswith("nonDerivativeTransaction"):
            continue
        code = (tx.findtext(".//transactionCoding/transactionCode") or "").strip()
        sh = tx.findtext(".//transactionAmounts/transactionShares/value")
        px = tx.findtext(".//transactionAmounts/transactionPricePerShare/value")
        ad = (tx.findtext(".//transactionAmounts/transactionAcquiredDisposedCode/value")
              or "").strip().upper()
        try:
            val = float(sh) * float(px)
        except (TypeError, ValueError):
            continue
        if not val:
            continue
        out.append((code, val if ad == "A" else -val))
    return out


def _window(asof: str):
    hi = _dt.date.fromisoformat(asof)
    return (hi - _dt.timedelta(days=INSIDER_LOOKBACK_D)).isoformat(), hi.isoformat()


def fetch4(limit: int | None = None, current: bool = False) -> dict:
    """Crawl the Form 4 documents the panel's window would have contained.

    Uses the submission indexes already cached by V2G, so this is documents only. Terminal
    outcomes only are recorded (the miner's manifest rule), so a throttled document is retried
    rather than banked as "this name had no filings".
    """
    from concurrent.futures import ThreadPoolExecutor
    import datetime as _d
    if current:
        lo, hi = _window(_d.date.today().isoformat())
        out_dir = F4_DIR_LIVE
        print(f"CURRENT Form 4 window: {lo} .. {hi} — this builds the PRODUCTION cache")
    else:
        lo, hi = _window(_panel_asof())
        out_dir = F4_DIR
        print(f"aligned Form 4 window: {lo} .. {hi} (exclusive of {hi}, mirroring audit B26)")
    M._ensure(out_dir)
    served = M.load_served()
    guard = M.Guard(min_interval=M.SEC_MIN_INTERVAL_S)
    ciks = M._read_json(os.path.join(ROOT, "cik_map.json")) or {}

    jobs = []
    for row in served[:limit] if limit else served:
        t = row["ticker"]
        out_p = os.path.join(out_dir, f"{t}.json")
        if os.path.exists(out_p):
            continue
        sub = M._read_json(M.leg_path(ROOT, "submissions", t)) or {}
        cik = sub.get("cik") or (ciks.get(t.upper()) or {}).get("cik_str")
        forms = sub.get("form") or []
        accs = sub.get("accessionNumber") or []
        docs = sub.get("primaryDocument") or []
        dates = sub.get("filingDate") or []
        picks = [(accs[i], docs[i], dates[i]) for i, f in enumerate(forms)
                 if f == "4" and i < len(dates) and lo <= dates[i] < hi]
        jobs.append((t, cik, picks, out_p))

    print(f"{len(jobs)} names to crawl, {sum(len(j[2]) for j in jobs)} documents", flush=True)

    def _one(job):
        t, cik, picks, out_p = job
        rec = {"ticker": t, "window": [lo, hi], "n_filings": len(picks),
               "txns": [], "parsed": 0, "parse_failures": 0, "fetch_failures": 0}
        if cik is None:
            rec["no_cik"] = True
            M._atomic_write_json(out_p, rec)
            return t, 0
        from valuation.screener.insider import form4_xml_url
        import requests
        for acc, doc, _d in picks:
            try:
                guard.wait()
                url = form4_xml_url(int(cik), acc, doc)
                xml = requests.get(url, headers=M._headers(), timeout=25).text
            except Exception:                                    # noqa: BLE001
                rec["fetch_failures"] += 1
                continue
            try:
                txns = parse_form4_signed(xml)
            except Exception:                                    # noqa: BLE001
                rec["parse_failures"] += 1
                continue
            rec["parsed"] += 1
            for code, signed in txns:
                rec["txns"].append({"code": code, "raw": signed})
        # Only a name we could actually READ is durable. A name whose every document failed is
        # left absent so the next run retries it -- otherwise coverage inflates by hitting a wall.
        if rec["n_filings"] == 0 or rec["parsed"] > 0:
            M._atomic_write_json(out_p, rec)
        return t, rec["parsed"]

    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for t, n in ex.map(_one, jobs):
            done += 1
            if done % 50 == 0:
                print(f"  ...{done}/{len(jobs)}", flush=True)
    print(f"crawled {done} names; cached {len(os.listdir(out_dir))}")
    return {"names": done}


def insider_column() -> dict:
    """The PANEL's score, verbatim, on the aligned window. None when the window is empty."""
    served = M.load_served()
    out, shape = {}, {"scored": 0, "empty_window_none": 0, "unreadable": 0}
    for row in served:
        t = row["ticker"]
        out[t] = None
        rec = M._read_json(os.path.join(F4_DIR, f"{t}.json"))
        if rec is None:
            shape["unreadable"] += 1
            continue
        vals = [x["raw"] for x in rec.get("txns", []) if x.get("raw") is not None]
        if not vals:
            # THE PANEL'S SEMANTICS: no transaction in the window is NO OPINION, not a neutral
            # 50. This is the single change that removes a 179-name tie block.
            shape["empty_window_none"] += 1
            continue
        net = float(sum(vals))
        buys = int(sum(1 for v in vals if v > 0))
        score = max(0.0, min(100.0, 50 + 40 * math.tanh(net / INSIDER_TANH_SCALE)
                             + min(INSIDER_BUY_CAP, INSIDER_BUY_BONUS * buys)))
        out[t] = (score - 50.0) / 25.0          # factors.py:271, as V2G mapped it
        shape["scored"] += 1
    return {"insider": out, "shape": shape}


# ------------------------------------------------------------------------------------------
# the gate — imported, not re-derived
# ------------------------------------------------------------------------------------------

def score() -> dict:
    import numpy as np
    x, asof = R.panel_cross_section()
    calib = R.calibrated_bar(x)
    bar = max(R.FIDELITY_FLOOR, calib["p95_abs_rho"] or 0.0)

    inst = institutional_columns()
    ins = insider_column()
    n_served = len(M.load_served())

    rebuilt = {"institutional": inst["institutional"], "insider": ins["insider"]}
    themes = {}
    for t, lv in rebuilt.items():
        cov = R._cov(lv, n_served)
        common = [k for k in lv if k in x.index]
        a = [lv[k] if lv[k] is not None else np.nan for k in common]
        b = [x.at[k, t] if t in x.columns else np.nan for k in common]
        rho, p, n = R._spearman(a, b)
        measurable = n >= R.MIN_PAIRS
        passes = bool(measurable and rho is not None and rho > 0
                      and p is not None and p < R.MAX_P and rho >= bar)
        themes[t] = {"rho": rho, "p": p, "n_pairs": n, "bar": bar, "measurable": measurable,
                     "quintile_agreement": R._quintile_agreement(a, b), "coverage": cov,
                     "fidelity_pass": passes, "coverage_pass": cov["usable"],
                     "restores": bool(passes and cov["usable"])}

    # The first-gate numbers, carried so the movement is visible rather than asserted.
    prior = {"institutional": 0.1706, "insider": 0.3596}
    for t, v in themes.items():
        v["rho_before_rebuild"] = prior[t]
        v["delta"] = None if v["rho"] is None else round(v["rho"] - prior[t], 4)

    return {"prereg": "PREREG_fidelity2_rebuild.md", "prereg_commit": "ef765fc",
            "gate_from": "PREREG_theme_restoration.md @ 1d12822 (bar NOT re-derived)",
            "panel_asof": asof, "n_served": n_served,
            "bar": {"floor": R.FIDELITY_FLOOR, "calibrated_p95": calib["p95_abs_rho"],
                    "applied": bar},
            "aligned_periods": {"institutional": [PERIOD_PRIOR_A, PERIOD_CURR_A],
                                "insider_window": list(_window(asof))},
            "insider_shape": ins["shape"],
            "themes": themes,
            "restored": sorted(t for t, v in themes.items() if v["restores"]),
            "unrestorable": sorted(t for t, v in themes.items() if not v["restores"])}


# ------------------------------------------------------------------------------------------
# build-live — the PRODUCTION cache `valuation/screener/live_themes.py` reads
# ------------------------------------------------------------------------------------------

LIVE_CACHE = os.path.join("data", "live_cache", "theme_columns.json")


def build_live() -> dict:
    """Write today's `inst_accum`, `sm_breadth` and `insider_score` for the served universe.

    THE GATE PROVED THE ESTIMATOR, NOT THE WINDOW. Fidelity was measured on the panel's own
    quarters and its own 90-day window, which is the only way to compare two sources. Production
    applies that same estimator to the CURRENT window — the latest two complete 13F periods and
    the trailing 90 days — exactly as the panel applied it to whatever was current at each of
    its own dates.

    `insider_score` is written on the panel's 0-100 scale because `factors.py:282` maps it with
    `(score - 50)/25`. Names with no transaction in the window are OMITTED, not written as 50:
    that fabricated neutral is what put 179 names in one tie block and cost the first gate.
    """
    served = M.load_served()
    # institutional: the CURRENT quarters, on dollars.
    agg = M._read_json(os.path.join(ROOT, "13f_aggregate.json"))
    if not agg:
        raise SystemExit("V2G's 13f_aggregate.json is missing; run live_theme_sources fetch")
    joined = M.join_13f(ROOT, served, agg)
    curr = agg["by_period"][M.PERIOD_CURR]
    prior = agg["by_period"][M.PERIOD_PRIOR]

    rows, cov = {}, {"inst_accum": 0, "sm_breadth": 0, "insider_score": 0}
    for row in served:
        t = row["ticker"]
        d = joined.get(t) or {}
        rec = {}
        if d.get("cusip") and d.get("rung") not in ("anchor_failed", "too_few_holders",
                                                    "ambiguous", "unmatched"):
            c, p = curr.get(d["cusip"]), prior.get(d["cusip"])
            if c and p and p.get("value"):
                rec["inst_accum"] = c["value"] / p["value"] - 1.0
        if d.get("sm_breadth") is not None:
            rec["sm_breadth"] = d["sm_breadth"]

        f4 = M._read_json(os.path.join(F4_DIR_LIVE, f"{t}.json"))
        if f4:
            vals = [x["raw"] for x in f4.get("txns", []) if x.get("raw") is not None]
            if vals:
                net = float(sum(vals))
                buys = int(sum(1 for v in vals if v > 0))
                rec["insider_score"] = max(0.0, min(100.0, 50 + 40 * math.tanh(
                    net / INSIDER_TANH_SCALE) + min(INSIDER_BUY_CAP, INSIDER_BUY_BONUS * buys)))
        for k in cov:
            if k in rec:
                cov[k] += 1
        if rec:
            rows[t.upper()] = rec

    out = {"built": _dt.date.today().isoformat(), "n_served": len(served),
           "periods": [M.PERIOD_PRIOR, M.PERIOD_CURR],
           "insider_window_days": INSIDER_LOOKBACK_D,
           "coverage": {k: round(v / len(served), 4) for k, v in cov.items()},
           "gate": "PREREG_fidelity2_rebuild.md @ ef765fc", "rows": rows}
    os.makedirs(os.path.dirname(LIVE_CACHE), exist_ok=True)
    M._atomic_write_json(LIVE_CACHE, out)
    print(f"wrote {LIVE_CACHE}: {len(rows)} rows, coverage {out['coverage']}")
    return out


def render(p: dict) -> str:
    L = []
    A = L.append
    A("=" * 96)
    A("FIDELITY-2 — the two failed themes, rebuilt to the panel's definition")
    A(f"register {p['prereg']} @ {p['prereg_commit']}")
    A(f"gate     {p['gate_from']}")
    A(f"panel as-of {p['panel_asof']}   bar {p['bar']['applied']:.4f}   served {p['n_served']}")
    A(f"aligned  institutional quarters {p['aligned_periods']['institutional']}   "
      f"insider window {p['aligned_periods']['insider_window']}")
    A("=" * 96)
    A(f"{'theme':<16} {'rho BEFORE':>11} {'rho AFTER':>10} {'delta':>8} {'n':>6} {'cov':>7}  verdict")
    A("-" * 96)
    for t, v in p["themes"].items():
        rho = f"{v['rho']:+.4f}" if v["rho"] is not None else "  n/a"
        dl = f"{v['delta']:+.4f}" if v["delta"] is not None else "  n/a"
        verdict = ("RESTORES" if v["restores"] else
                   ("NOT MEASURABLE" if not v["measurable"] else
                    ("COVERAGE FAIL" if v["fidelity_pass"] else "UNRESTORABLE")))
        A(f"{t:<16} {v['rho_before_rebuild']:>+11.4f} {rho:>10} {dl:>8} {v['n_pairs']:>6} "
          f"{v['coverage']['coverage']:>7.3f}  {verdict}")
    A("-" * 96)
    s = p["insider_shape"]
    A(f"insider shape: scored {s['scored']}, empty-window->None {s['empty_window_none']}, "
      f"unreadable {s['unreadable']}")
    A(f"RESTORED:     {', '.join(p['restored']) or '(none)'}")
    A(f"UNRESTORABLE: {', '.join(p['unrestorable']) or '(none)'}")
    A("=" * 96)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch13f", "fetch4", "score", "build-live"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--current", action="store_true",
                    help="crawl TODAY's window to build the production cache")
    ap.add_argument("--json", default=OUT)
    a = ap.parse_args(argv)
    if a.cmd == "fetch13f":
        fetch13f()
        return 0
    if a.cmd == "build-live":
        build_live()
        return 0
    if a.cmd == "fetch4":
        fetch4(a.limit, current=a.current)
        return 0
    p = score()
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(p, fh, indent=2, default=str)
    print(render(p))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
