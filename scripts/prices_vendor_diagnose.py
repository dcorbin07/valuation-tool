"""
PRICES-SRC — the two measurements behind the vendor-label repair, made reproducible.

    python -m scripts.prices_vendor_diagnose --probe    # which vendor actually serves
    python -m scripts.prices_vendor_diagnose --seam     # is the track seam the adjustment flag?

`RUN_RULES` rule 9's spirit: the handoff quotes these numbers, so the way to re-derive them
lives in the tree rather than in a scratch file that disappears with the session.

**BOTH PASSES HIT THE LIVE INTERNET AND NEITHER IS PART OF ANY SUITE.** `--seam` makes ~172
yfinance calls, paced, with a canary and a running contamination check — a few hundred names
throttles Yahoo and silently returns empties, which would make the bound pass vacuously. Do not
wire this into a test.

WHAT THEY MEASURED ON 2026-08-20/21, so a re-run can be compared rather than merely read:

  --probe   Stooq served 0 of 10 (SPY AAPL KO NVDA JNJ MSFT XOM T IBM PG). The default
            `requests` user-agent gets HTTP 404; a browser user-agent gets HTTP 200 carrying a
            JavaScript bot-verification page. Never CSV. **No attempt is made to defeat that
            challenge** — evading a vendor's access control is not a fix.

  --seam    On the 86-name Index book, inception 2026-07-30 to the recorded 2026-08-06 row,
            same vendor and same dates, changing nothing but the adjustment flag:
                auto_adjust=True    valquo_pct 0.7961   spy_pct 3.6228
                auto_adjust=False   valquo_pct 0.7760   spy_pct 3.6228
                recorded row        valquo_pct 0.7760   spy_pct 3.6228
            The flag moves the book leg by +0.0201pp and the benchmark leg by +0.0000pp, and
            +0.0201pp is the whole seam `index_mark` documents. The benchmark leg is IDENTICAL
            under both settings, which is exactly why the leg that "confirmed the convention"
            could not distinguish the two conventions.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_PRIMARY = r"C:\Users\donni\Downloads\valuation-tool"
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

PROBE_TICKERS = ["SPY", "AAPL", "KO", "NVDA", "JNJ", "MSFT", "XOM", "T", "IBM", "PG"]
BASE_DATE = "2026-07-30"        # Index inception, per PAPER_TRACK_CONTRACT
MARK_DATE = "2026-08-06"        # the recorded row index_mark re-derived
MAX_EMPTY = 12                  # contamination floor: above this we are throttled, not measuring


def _data(*parts) -> str:
    p = os.path.join(_REPO, "data", *parts)
    if os.path.isdir(p):
        if os.listdir(p):
            return p
    elif os.path.exists(p):
        return p
    return os.path.join(_PRIMARY, "data", *parts)


def probe() -> dict:
    """Which vendor actually serves, and HOW the primary refuses."""
    import requests

    from valuation.screener import prices as P

    out = {"tickers": PROBE_TICKERS, "served": {}, "refusals": {}}
    for t in PROBE_TICKERS:
        time.sleep(1.0)
        url = P.STOOQ_URL.format(sym=P._stooq_symbol(t))
        try:
            r = requests.get(url, timeout=20)
            body, code = r.text[:200], r.status_code
        except Exception as e:                                          # noqa: BLE001
            body, code = "EXC %s" % type(e).__name__, None
        ok = (code == 200 and "Close" in body)
        out["served"][t] = bool(ok)
        out["refusals"][t] = {"status": code, "looks_like_csv": ("Close" in body)}
        print("%-6s http=%-5s csv=%s" % (t, code, "Close" in body))

    n = sum(1 for v in out["served"].values() if v)
    out["stooq_served"] = n
    out["stooq_served_of"] = len(PROBE_TICKERS)
    print("\nStooq served %d of %d; yfinance silently serves the rest under the OLD code"
          % (n, len(PROBE_TICKERS)))

    # the user-agent split, because the two refusals look nothing alike
    try:
        u = P.STOOQ_URL.format(sym="aapl.us")
        a = requests.get(u, timeout=20)
        time.sleep(1.0)
        b = requests.get(u, timeout=20,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        out["user_agent_split"] = {
            "default_ua_status": a.status_code,
            "browser_ua_status": b.status_code,
            "browser_ua_is_js_challenge": ("JavaScript" in b.text or "noscript" in b.text),
        }
        print("default UA -> %s ; browser UA -> %s (js challenge: %s)"
              % (a.status_code, b.status_code, out["user_agent_split"]["browser_ua_is_js_challenge"]))
    except Exception as e:                                              # noqa: BLE001
        out["user_agent_split"] = {"error": "%s: %s" % (type(e).__name__, e)}
    return out


def seam() -> dict:
    """Is `index_mark`'s +0.0201pp book-leg seam the adjustment flag? Same vendor, same dates."""
    import yfinance as yf

    book = json.load(io.open(_data("valquo_index.json"), encoding="utf-8"))
    positions = book.get("positions") or book.get("holdings") or []
    bench = book.get("benchmark") or "SPY"
    if not positions:
        raise SystemExit("no positions in the book — refusing to report a vacuous seam")
    print("book: %d positions, benchmark %s" % (len(positions), bench))

    def closes(t, adjust):
        h = yf.Ticker(t).history(start="2026-07-25", end="2026-08-12", auto_adjust=adjust)
        if h is None or h.empty:
            return {}
        return {d.strftime("%Y-%m-%d"): float(c) for d, c in zip(h.index, h["Close"].values)}

    ca, cu = closes(bench, True), closes(bench, False)
    if not ca or not cu:
        raise SystemExit("canary empty — throttled or blocked; refusing to report")

    legs, num, wsum, unpriced, empties = {}, {}, {}, {}, 0
    for adjust in (True, False):
        b = closes(bench, adjust)
        if BASE_DATE not in b or MARK_DATE not in b:
            raise SystemExit("benchmark missing a required date at adjust=%s" % adjust)
        legs[adjust] = (b[MARK_DATE] / b[BASE_DATE] - 1.0) * 100.0
        num[adjust], wsum[adjust], unpriced[adjust] = 0.0, 0.0, []

    for i, p in enumerate(positions, 1):
        for adjust in (True, False):
            time.sleep(0.7)
            m = closes(p["ticker"], adjust)
            if not m:
                empties += 1
            if BASE_DATE in m and MARK_DATE in m:
                num[adjust] += float(p["weight"]) * (m[MARK_DATE] / m[BASE_DATE] - 1.0)
                wsum[adjust] += float(p["weight"])
            else:
                unpriced[adjust].append(p["ticker"])
        if i % 20 == 0:
            print("  ... %d/%d, %d empty fetches" % (i, len(positions), empties), flush=True)
        if empties > MAX_EMPTY:
            raise SystemExit("CONTAMINATED: %d empty fetches — throttled, refusing to report"
                             % empties)

    out = {"n_positions": len(positions), "benchmark": bench, "empty_fetches": empties,
           "base": BASE_DATE, "mark": MARK_DATE, "by_basis": {}}
    for adjust in (True, False):
        v = (num[adjust] / wsum[adjust]) * 100.0 if wsum[adjust] else None
        out["by_basis"]["auto_adjust=%s" % adjust] = {
            "valquo_pct": v, "spy_pct": legs[adjust],
            "priced": len(positions) - len(unpriced[adjust]),
            "unpriced": len(unpriced[adjust])}
        print("auto_adjust=%-5s valquo_pct %.4f  spy_pct %.4f  priced %d/%d"
              % (adjust, v, legs[adjust], len(positions) - len(unpriced[adjust]), len(positions)))

    dv = (out["by_basis"]["auto_adjust=True"]["valquo_pct"]
          - out["by_basis"]["auto_adjust=False"]["valquo_pct"])
    ds = legs[True] - legs[False]
    out["book_leg_moved_pp"] = dv
    out["benchmark_leg_moved_pp"] = ds
    out["index_mark_recorded_seam_pp"] = 0.0201
    print("\nadjustment moves the BOOK leg %+.4fpp and the BENCHMARK leg %+.4fpp; "
          "index_mark's recorded seam is +0.0201pp" % (dv, ds))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--seam", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not (a.probe or a.seam):
        ap.error("pick --probe and/or --seam")
    rep = {}
    if a.probe:
        rep["probe"] = probe()
    if a.seam:
        rep["seam"] = seam()
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2)
        print("wrote", a.out)


if __name__ == "__main__":
    main()
