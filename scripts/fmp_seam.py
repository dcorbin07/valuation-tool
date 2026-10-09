# -*- coding: utf-8 -*-
"""ITEM 40 -- measure the FMP seam against Yahoo. ENABLES NOTHING.

`prices.py`'s FMP rung is configured and deliberately OFF behind `PRICES_ALLOW_FMP`, and its own
docstring states the precondition: *"its seam against the recorded series is unmeasured, so it
may not price a row until PRICES_ALLOW_FMP=1 is set deliberately ... Measure the seam first."*
This is that measurement. It is re-runnable so the answer can be refreshed the day the plan
changes, which is the only way the conclusion stops being a snapshot.

**IT TOUCHES NO PRODUCT SWITCH.** The FMP calls here are made directly with `requests`, not
through `prices._fmp_history`, so `PRICES_ALLOW_FMP` is never set and the shipped gate is never
exercised. Nothing in this file writes to `data/`, the store, or any append-only record.

**THE KEY IS NEVER PRINTED.** FMP puts the key in the QUERY STRING, so a `requests` exception
carries it verbatim -- every status line, error body and URL echoed here goes through `scrub()`.
The key is read from the environment the way the app reads it (`valuation.config` calls
`load_dotenv()`); this file never opens `.env`.

**THE ALLOWANCE IS GUARDED, because it is finite, unadvertised and shared.** No FMP response
carries a rate-limit header, batch is refused (402 on comma-separated symbols), and the nightly
scan uses the same account. So the pull ABORTS on the first quota-shaped response and reports
where it stopped: a measurement that exhausts the thing it measures has broken its own subject.
Measured 2026-10-08: `Limit Reach` after ~185 requests in a day.

Usage:
    python -m scripts.fmp_seam --probe      # which endpoints answer at all (cheap, ~8 calls)
    python -m scripts.fmp_seam --pull       # the sample, both vendors, stored to --out
    python -m scripts.fmp_seam --analyse    # read the stored pull, print the seam
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time

# --------------------------------------------------------------------------------------- #
# THE SAMPLE, STATED
#
# `/api/hotstocks` serves the top 100 only, so a 200-name sample has to be composed -- and the
# composition is named here rather than left to whatever came back. A random 200 from a
# megacap-tilted hot list does not reliably contain a REIT, and the categories ARE the finding:
# measured 2026-10-08, this key serves 0 of 16 REITs and 0 of 10 regulated utilities.
# --------------------------------------------------------------------------------------- #
BANKS = ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF", "SCHW", "BK",
         "MTB", "FITB", "HBAN", "RF"]
REITS = ["O", "SPG", "PLD", "AMT", "EQIX", "PSA", "VICI", "WELL", "DLR", "AVB", "EQR",
         "CCI", "IRM", "SBAC", "ARE", "MAA"]
UTILITIES = ["NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "ED", "WEC", "ES"]
ADRS = ["TSM", "ASML", "SAP", "SHEL", "TM", "BABA", "NVO", "AZN", "HSBC", "UL", "RIO", "BHP",
        "SONY", "MUFG", "INFY", "DEO"]

#: (ticker, split, date) -- a split comparison that does not STRADDLE a real corporate action
#: measures nothing, so the dates are named and the analysis reads them.
SPLITTERS = [("NVDA", "10:1", "2024-06-10"), ("AMZN", "20:1", "2022-06-06"),
             ("GOOGL", "20:1", "2022-07-18"), ("TSLA", "3:1", "2022-08-25"),
             ("SHOP", "10:1", "2022-06-29"), ("WMT", "3:1", "2024-02-26"),
             ("CMG", "50:1", "2024-06-26"), ("AVGO", "10:1", "2024-07-15"),
             ("SMCI", "10:1", "2024-10-01"), ("PANW", "3:1", "2022-09-14"),
             ("LRCX", "10:1", "2024-10-03"), ("MSTR", "10:1", "2024-08-08")]

CATEGORY = {}
for _t in BANKS:
    CATEGORY[_t] = "bank"
for _t in REITS:
    CATEGORY[_t] = "reit"
for _t in UTILITIES:
    CATEGORY[_t] = "utility"
for _t in ADRS:
    CATEGORY[_t] = "adr"
for _t, _s, _d in SPLITTERS:
    CATEGORY[_t] = "splitter"

SPLIT_DATE = {t: (s, d) for t, s, d in SPLITTERS}

#: FMP's two working surfaces. v3 is DEAD -- see `DEAD_V3` below.
STABLE = "https://financialmodelingprep.com/stable"

#: **THE v3 API IS GONE AND THE PROJECT STILL CALLS IT IN TWO PLACES.** Measured 2026-10-08:
#: every `/api/v3/...` path answers `403 "Legacy Endpoint : Due to Legacy endpoints being no
#: longer supported - This endpoint is only available for legacy users with a valid
#: subscription"`. So `prices.FMP_HISTORY_URL` and `sector_resolve`'s profile call cannot
#: succeed, and enabling `PRICES_ALLOW_FMP=1` today would add a rung that returns None for
#: every name. Listed, not fixed: repointing them is a behaviour change on a vendor whose
#: coverage is ~12% and whose allowance is ~250/day.
DEAD_V3 = ("valuation/screener/prices.py", "valuation/data/sector_resolve.py")

#: Both FMP bases are pulled only for these. A dividend basis is only observable on a payer,
#: and spending two requests per name against an unadvertised allowance is not a budget to
#: spend blind.
BOTH_BASES = sorted(set(BANKS) | set(REITS) | set(UTILITIES) | {"KO", "PG", "JNJ", "XOM", "T"})


def _key() -> str:
    """The key, from the environment the app's own loader populates. `.env` is never opened."""
    try:
        from valuation.config import CONFIG                            # noqa: F401
    except Exception:                                                  # noqa: BLE001
        pass
    return (os.environ.get("FMP_API_KEY") or "").strip()


def scrub(s, key) -> str:
    """Never let the key reach stdout. It rides in the query string of every request."""
    return str(s).replace(key, "<FMP_KEY>") if key else str(s)


def quota_shaped(status, msg) -> bool:
    m = (msg or "").lower()
    return status == 429 or "limit reach" in m or "quota" in m or "too many" in m


def fmp_get(path, params, key):
    """(status, parsed-or-None, scrubbed message).

    AN EMPTY 200 IS A REAL FMP RESPONSE and `r.json()` raises on it even when the content-type
    says JSON -- the first cut of this probe crashed there and the symptom looked like a missing
    ticker. The three states are told apart instead.
    """
    import requests

    p = dict(params)
    p["apikey"] = key
    try:
        r = requests.get(STABLE + path, params=p, timeout=25)
    except Exception as e:                                             # noqa: BLE001
        return None, None, "%s: %s" % (type(e).__name__, scrub(e, key)[:140])
    raw = r.text or ""
    if not raw.strip():
        return r.status_code, None, "EMPTY BODY"
    try:
        body = r.json()
    except Exception:                                                  # noqa: BLE001
        return r.status_code, None, scrub(raw, key)[:160]
    if isinstance(body, list):
        return r.status_code, body, ""
    return r.status_code, None, scrub(json.dumps(body), key)[:160]


def live_names():
    """The hot list and the dip screen, from the live service. Degrades to [] offline."""
    import urllib.request

    out = []
    for path in ("/api/hotstocks", "/api/dip?min_drawdown=0.10"):
        try:
            req = urllib.request.Request("https://valquo.co" + path,
                                         headers={"User-Agent": "valquo-fmp-seam"})
            d = json.loads(urllib.request.urlopen(req, timeout=120)
                           .read().decode("utf-8", "replace"))
        except Exception:                                              # noqa: BLE001
            continue
        for k in ("rows", "rows_health_not_scored"):
            for r in (d.get(k) or []):
                t = str(r.get("ticker") or "").strip().upper()
                if t:
                    out.append(t)
    return out


def sample():
    seen, out = set(), []
    for t in list(CATEGORY) + live_names():
        t = t.strip().upper()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


# --------------------------------------------------------------------------------------- #
# PROBE
# --------------------------------------------------------------------------------------- #
def probe(key):
    import requests

    print("  key length %d (never printed). PRICES_ALLOW_FMP=%r -- the product gate is untouched"
          % (len(key), os.environ.get("PRICES_ALLOW_FMP")))
    print()
    # The v3 rung the project is configured to use.
    try:
        r = requests.get("https://financialmodelingprep.com/api/v3/historical-price-full/AAPL",
                         params={"apikey": key, "serietype": "line"}, timeout=25)
        print("  %-44s HTTP %s  %s"
              % ("v3 historical-price-full (prices.py's URL)", r.status_code,
                 scrub(r.text, key)[:90]))
    except Exception as e:                                             # noqa: BLE001
        print("  v3 historical-price-full RAISED %s" % type(e).__name__)

    for path, params, label in (
            ("/historical-price-eod/full", {"symbol": "AAPL"}, "stable eod/full"),
            ("/historical-price-eod/dividend-adjusted", {"symbol": "AAPL"},
             "stable eod/dividend-adjusted"),
            ("/historical-price-eod/full", {"symbol": "AAPL,MSFT"}, "stable eod/full BATCH"),
            ("/company-screener", {"exchange": "NYSE"}, "stable company-screener"),
            ("/profile", {"symbol": "AAPL"}, "stable profile"),
    ):
        code, body, msg = fmp_get(path, params, key)
        print("  %-44s HTTP %-5s %s"
              % (label, code, ("list of %d" % len(body)) if body else msg[:90]))


# --------------------------------------------------------------------------------------- #
# PULL
# --------------------------------------------------------------------------------------- #
def pull(key, out_path, chunk=40, years="5y"):
    import yfinance as yf

    names = sample()
    print("  sample: %d names" % len(names))

    yahoo = {}
    for basis, adj in (("as_traded", False), ("adjusted", True)):
        for i in range(0, len(names), chunk):
            part = names[i:i + chunk]
            try:
                df = yf.download(part, period=years, auto_adjust=adj, progress=False,
                                 threads=False, group_by="ticker", timeout=60)
            except Exception as e:                                     # noqa: BLE001
                print("    yahoo %s chunk %d RAISED %s" % (basis, i // chunk,
                                                           type(e).__name__))
                continue
            for t in part:
                try:
                    col = df[t]["Close"].dropna()
                except Exception:                                      # noqa: BLE001
                    continue
                if len(col):
                    yahoo.setdefault(t, {})[basis] = {str(d)[:10]: float(v)
                                                      for d, v in col.items()}
            time.sleep(1.0)
        print("    yahoo %-9s done: %d names"
              % (basis, sum(1 for v in yahoo.values() if basis in v)))

    fmp, statuses, stopped, reqs = {}, {}, None, 0
    for n, t in enumerate(names, 1):
        code, rows, msg = fmp_get("/historical-price-eod/full", {"symbol": t}, key)
        reqs += 1
        statuses[t] = {"full": {"status": code, "msg": msg}}
        if quota_shaped(code, msg):
            stopped = "full/%s after %d requests: %s" % (t, reqs, msg)
            break
        if rows:
            fmp.setdefault(t, {})["as_traded"] = {
                str(r.get("date"))[:10]: float(r["close"])
                for r in rows if r.get("close") is not None}
        if t in BOTH_BASES:
            code2, rows2, msg2 = fmp_get("/historical-price-eod/dividend-adjusted",
                                         {"symbol": t}, key)
            reqs += 1
            statuses[t]["adjusted"] = {"status": code2, "msg": msg2}
            if quota_shaped(code2, msg2):
                stopped = "adjusted/%s after %d requests: %s" % (t, reqs, msg2)
                break
            if rows2:
                fmp.setdefault(t, {})["adjusted"] = {
                    str(r.get("date"))[:10]: float(r["adjClose"])
                    for r in rows2 if r.get("adjClose") is not None}
        if n % 25 == 0:
            print("    fmp %3d/%d names, %d requests" % (n, len(names), reqs))

    print("  fmp requests spent: %d%s" % (reqs, ("  STOPPED at " + stopped) if stopped else ""))
    with open(out_path, "w") as fh:
        json.dump({"names": names, "yahoo": yahoo, "fmp": fmp, "fmp_status": statuses,
                   "fmp_requests": reqs, "stopped": stopped,
                   "pulled_at": _dt.datetime.now().isoformat(timespec="seconds")}, fh)
    print("  raw stored: %s" % out_path)


# --------------------------------------------------------------------------------------- #
# ANALYSE
# --------------------------------------------------------------------------------------- #
def _q(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def _pct(x):
    return "n/a" if x is None else "%.4f%%" % (100 * x)


def analyse(raw_path):
    D = json.load(open(raw_path))
    today = _dt.date.today().isoformat()
    names, status = D["names"], (D.get("fmp_status") or {})

    served, by_cat, msgs = [], {}, {}
    for t in names:
        st = (status.get(t) or {}).get("full") or {}
        ok = bool((D["fmp"].get(t) or {}).get("as_traded"))
        b = by_cat.setdefault(CATEGORY.get(t, "hot-list / dip"),
                              {"n": 0, "ok": 0, "codes": {}})
        b["n"] += 1
        if ok:
            served.append(t)
            b["ok"] += 1
        else:
            b["codes"][st.get("status")] = b["codes"].get(st.get("status"), 0) + 1
            k = "%s %s" % (st.get("status"), (st.get("msg") or "")[:60])
            msgs[k] = msgs.get(k, 0) + 1

    attempted = [t for t in names if (status.get(t) or {}).get("full", {}).get("status")]
    print("1. COVERAGE -- what this key actually serves")
    print("   requests spent %s%s" % (D.get("fmp_requests"),
                                      "   STOPPED: " + str(D["stopped"])
                                      if D.get("stopped") else ""))
    print("   served %d of %d ATTEMPTED (%.1f%%); %d of the sample never reached"
          % (len(served), len(attempted),
             100.0 * len(served) / max(1, len(attempted)), len(names) - len(attempted)))
    print("   %-18s %5s %5s %7s  codes" % ("category", "n", "ok", "rate"))
    for cat in sorted(by_cat, key=lambda c: by_cat[c]["ok"] / max(1, by_cat[c]["n"])):
        b = by_cat[cat]
        print("   %-18s %5d %5d %6.1f%%  %s"
              % (cat, b["n"], b["ok"], 100.0 * b["ok"] / max(1, b["n"]), b["codes"] or "-"))
    for m, c in sorted(msgs.items(), key=lambda kv: -kv[1])[:4]:
        print("   %4d x %s" % (c, m))

    print()
    print("2. AS-TRADED CLOSES -- Yahoo auto_adjust=False vs FMP eod/full")
    rows = []
    for t in served:
        y = (D["yahoo"].get(t) or {}).get("as_traded") or {}
        f = (D["fmp"].get(t) or {}).get("as_traded") or {}
        shared = sorted((set(y) & set(f)) - {today})
        errs = [abs(f[d] - y[d]) / y[d] for d in shared if y.get(d)]
        if len(shared) >= 60 and errs:
            rows.append((t, len(shared), _q(errs, 0.5), _q(errs, 0.95), max(errs)))
    if rows:
        med = [r[2] for r in rows]
        print("   %d names, >=60 shared sessions:  median-of-medians %s  p95 %s  worst %s"
              % (len(rows), _pct(_q(med, 0.5)), _pct(_q(med, 0.95)), _pct(max(med))))
        for tol, lab in ((0.0001, "0.01%"), (0.001, "0.1%"), (0.01, "1%")):
            k = sum(1 for r in rows if r[2] <= tol)
            print("   median error within %-6s %3d of %d" % (lab, k, len(rows)))
        print("   worst by median: %s"
              % ", ".join("%s %s" % (r[0], _pct(r[2]))
                          for r in sorted(rows, key=lambda r: -r[2])[:5]))
        print("   worst SINGLE session: %s"
              % ", ".join("%s %s" % (r[0], _pct(r[4]))
                          for r in sorted(rows, key=lambda r: -r[4])[:5]))

    print()
    print("3. THE 52-WEEK HIGH -- the number item 39 is about")
    for basis, label in (("as_traded", "as-traded (Yahoo adjust=False vs FMP full)"),
                         ("adjusted", "adjusted  (Yahoo adjust=True vs FMP dividend-adjusted)")):
        errs, worst = [], []
        for t in served:
            y = (D["yahoo"].get(t) or {}).get(basis) or {}
            f = (D["fmp"].get(t) or {}).get(basis) or {}
            shared = sorted((set(y) & set(f)) - {today})
            if len(shared) < 200:
                continue
            last = shared[-252:]
            hy = max([y[d] for d in last if d in y] or [0]) or None
            hf = max([f[d] for d in last if d in f] or [0]) or None
            if hy and hf:
                errs.append(abs(hf - hy) / hy)
                worst.append((abs(hf - hy) / hy, t, hy, hf))
        if not errs:
            print("   %-52s no comparable names" % label)
            continue
        print("   %-52s %d names: p50 %s p95 %s worst %s"
              % (label, len(errs), _pct(_q(errs, 0.5)), _pct(_q(errs, 0.95)), _pct(max(errs))))
        for e, t, hy, hf in sorted(worst, reverse=True)[:3]:
            print("        %-6s yahoo %-10.2f fmp %-10.2f  %s" % (t, hy, hf, _pct(e)))

    print()
    print("4. SPLITS -- across a NAMED split date, so the claim is checkable")
    print("   ratio = close just after / close just before. ~1 means the source is")
    print("   split-adjusted through the event; ~1/ratio means it is not.")
    for t, (split, date) in sorted(SPLIT_DATE.items()):
        def around(series):
            before = [d for d in sorted(series) if d < date][-1:]
            after = [d for d in sorted(series) if d >= date][:1]
            if not before or not after or not series[before[0]]:
                return None
            return series[after[0]] / series[before[0]]

        ry = around((D["yahoo"].get(t) or {}).get("as_traded") or {})
        rf = around((D["fmp"].get(t) or {}).get("as_traded") or {})
        agree = ("-" if ry is None or rf is None
                 else "YES" if abs(ry - rf) / max(ry, rf) < 0.02 else "*** NO ***")
        print("   %-7s %-7s %-12s yahoo %-9s fmp %-9s %s"
              % (t, split, date,
                 "n/a" if ry is None else "%.4f" % ry,
                 "n/a" if rf is None else "%.4f" % rf, agree))

    print()
    print("5. TODAY'S ROW -- a convention both vendors share, excluded from every comparison")
    fw = sum(1 for t in served if today in ((D["fmp"].get(t) or {}).get("as_traded") or {}))
    yw = sum(1 for t in served if today in ((D["yahoo"].get(t) or {}).get("as_traded") or {}))
    print("   a row dated %s: FMP %d of %d served, Yahoo %d. BOTH do it, so it is not an"
          % (today, fw, len(served), yw))
    print("   FMP-specific hazard -- and an intraday close is why the comparisons drop it.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--out", default="fmp_seam_raw.json")
    a = ap.parse_args(argv)

    if a.analyse and not (a.probe or a.pull):
        analyse(a.out)
        return 0

    key = _key()
    if not key:
        print("  no FMP key in the environment; nothing to measure. (Never read from .env "
              "here -- `valuation.config` loads it the way the app does.)")
        return 1
    if a.probe:
        probe(key)
    if a.pull:
        pull(key, a.out)
    if a.analyse:
        analyse(a.out)
    if not (a.probe or a.pull or a.analyse):
        probe(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
