# -*- coding: utf-8 -*-
"""ITEM 41(b) -- measure Tradier's daily history against Yahoo. ENABLES NOTHING.

Items 39 and 40 established the gap: the price chain has **no rung that does not depend on
Yahoo** (`get_history_df`'s primary IS a yfinance call, and its Stooq fallback is dead), and FMP
cannot fill it on the current plan -- its configured endpoint is retired and its subscription
serves ~12% of names. The service already holds a live Tradier token that the intraday scan
uses, so this measures whether Tradier can be that rung.

**THE SAME STATED SAMPLE AS THE FMP MEASUREMENT**, imported from `scripts/fmp_seam.py` rather
than re-composed -- 222 names with named blocks of banks, REITs, ADRs, regulated utilities and
recent splitters. Two vendors measured against DIFFERENT samples produce two coverage numbers
that cannot be compared, which is the whole question here.

**READ-ONLY, MARKET DATA ONLY.** This touches `markets/history` and nothing else: no order
endpoint, no account endpoint. The standing rule is no real trades or orders, ever, and a live
token makes that a property of the code rather than of the intention.

**THE TOKEN IS NEVER PRINTED.** It rides in an `Authorization` header rather than a query
string, which is safer than FMP's shape, but an exception or a header dump would still carry it,
so everything printed goes through `scrub()`.

Usage:
    python -m scripts.tradier_seam --probe            # liveness, rate-limit headers (~3 calls)
    python -m scripts.tradier_seam --pull --out P     # the sample, both vendors, stored
    python -m scripts.tradier_seam --analyse --out P  # the seam, from the stored pull
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time

LIVE = "https://api.tradier.com/v1"
SANDBOX = "https://sandbox.tradier.com/v1"

#: Tradier publishes its allowance in RESPONSE HEADERS, which FMP does not -- so the limit can
#: be read rather than discovered by hitting it. Named here so the probe reports all three.
RATE_HEADERS = ("X-Ratelimit-Allowed", "X-Ratelimit-Used", "X-Ratelimit-Available",
                "X-Ratelimit-Expiry")


def _cfg():
    from valuation.config import CONFIG
    return CONFIG


def _token(cfg) -> str:
    return (getattr(cfg, "tradier_token", "") or "").strip()


def _base(cfg) -> str:
    return LIVE if str(getattr(cfg, "tradier_env", "")).lower() == "live" else SANDBOX


def scrub(s, token) -> str:
    return str(s).replace(token, "<TRADIER_TOKEN>") if token else str(s)


def history(symbol, cfg, days=400):
    """(status, [{date, close}], scrubbed message, rate-limit headers).

    `start` is passed explicitly. The shipped `get_bars` asks for 400 days and then **drops the
    DATES**, returning parallel close/high/low/volume lists -- which is why item 36 could not
    reconstruct a settlement price from it. A seam measurement needs the dates, so this calls
    the endpoint directly rather than through that helper.
    """
    import requests

    tok = _token(cfg)
    start = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    try:
        r = requests.get(_base(cfg) + "/markets/history",
                         params={"symbol": symbol, "interval": "daily", "start": start},
                         headers={"Authorization": "Bearer %s" % tok,
                                  "Accept": "application/json"},
                         timeout=25)
    except Exception as e:                                             # noqa: BLE001
        return None, None, "%s: %s" % (type(e).__name__, scrub(e, tok)[:140]), {}
    rl = {k: v for k, v in r.headers.items()
          if k.lower().startswith("x-ratelimit")}
    raw = r.text or ""
    if not raw.strip():
        return r.status_code, None, "EMPTY BODY", rl
    try:
        d = r.json()
    except Exception:                                                  # noqa: BLE001
        return r.status_code, None, scrub(raw, tok)[:160], rl
    # THE STATUS CODE IS CHECKED BEFORE THE BODY, and the first cut of this function did the
    # opposite -- so a **401 Unauthorized** was reported as `history: null (symbol not covered)`,
    # an AUTH failure dressed as a COVERAGE fact. That is the same shape as item 39's defect
    # (Yahoo's refusal read as a data gap) committed in the tool written to measure it: a
    # vendor saying "who are you" and a vendor saying "I don't have that name" are different
    # answers and only one of them is about the data.
    if r.status_code != 200:
        return r.status_code, None, "HTTP %s: %s" % (r.status_code, scrub(raw, tok)[:110]), rl
    # A symbol Tradier does not cover comes back as `history: null` WITH a 200.
    hist = (d or {}).get("history")
    if hist in (None, "null"):
        return r.status_code, None, "history: null (symbol not covered)", rl
    days_ = (hist or {}).get("day")
    if not days_:
        return r.status_code, None, "no day rows", rl
    if isinstance(days_, dict):
        days_ = [days_]
    out = [{"date": str(x.get("date"))[:10], "close": x.get("close")}
           for x in days_ if x.get("close") is not None]
    return r.status_code, out, "", rl


def probe(cfg):
    tok = _token(cfg)
    print("  token length %d (never printed), env=%r -> %s"
          % (len(tok), getattr(cfg, "tradier_env", None), _base(cfg)))
    print()
    for sym in ("AAPL", "O", "NEE"):
        code, rows, msg, rl = history(sym, cfg)
        print("  markets/history %-5s HTTP %-5s %s"
              % (sym, code, ("%d rows, %s..%s" % (len(rows), rows[-1]["date"], rows[0]["date"]))
                 if rows else msg[:70]))
        if rl:
            print("      rate limit: %s" % json.dumps(rl))


def pull(cfg, out_path, pause=0.1):
    import yfinance as yf
    from scripts.fmp_seam import sample

    names = sample()
    print("  sample: %d names (the SAME stated sample as the FMP measurement)" % len(names))

    yahoo = {}
    CHUNK = 40
    for basis, adj in (("as_traded", False), ("adjusted", True)):
        for i in range(0, len(names), CHUNK):
            part = names[i:i + CHUNK]
            try:
                df = yf.download(part, period="5y", auto_adjust=adj, progress=False,
                                 threads=False, group_by="ticker", timeout=60)
            except Exception as e:                                     # noqa: BLE001
                print("    yahoo %s chunk %d RAISED %s" % (basis, i // CHUNK,
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

    trad, statuses, rate_seen, reqs = {}, {}, {}, 0
    for n, t in enumerate(names, 1):
        code, rows, msg, rl = history(t, cfg)
        reqs += 1
        statuses[t] = {"status": code, "msg": msg}
        if rl:
            rate_seen = rl
        if rows:
            trad[t] = {d["date"]: float(d["close"]) for d in rows}
        if n % 40 == 0:
            print("    tradier %3d/%d  served %d  (available %s)"
                  % (n, len(names), len(trad), rate_seen.get("X-Ratelimit-Available")))
        time.sleep(pause)

    print("  tradier requests: %d, served %d" % (reqs, len(trad)))
    with open(out_path, "w") as fh:
        json.dump({"names": names, "yahoo": yahoo, "tradier": trad,
                   "tradier_status": statuses, "requests": reqs,
                   "rate_limit_last": rate_seen,
                   "pulled_at": _dt.datetime.now().isoformat(timespec="seconds")}, fh)
    print("  raw stored: %s" % out_path)


def _q(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def _pct(x):
    return "n/a" if x is None else "%.4f%%" % (100 * x)


def analyse(raw_path):
    from scripts.fmp_seam import CATEGORY, SPLIT_DATE

    D = json.load(open(raw_path))
    today = _dt.date.today().isoformat()
    names, status = D["names"], D.get("tradier_status") or {}

    served, by_cat, msgs = [], {}, {}
    for t in names:
        ok = bool(D["tradier"].get(t))
        b = by_cat.setdefault(CATEGORY.get(t, "hot-list / dip"), {"n": 0, "ok": 0})
        b["n"] += 1
        if ok:
            served.append(t)
            b["ok"] += 1
        else:
            st = status.get(t) or {}
            k = "%s %s" % (st.get("status"), (st.get("msg") or "")[:60])
            msgs[k] = msgs.get(k, 0) + 1

    print("1. COVERAGE -- the same 222-name sample the FMP measurement used")
    print("   requests %s   rate-limit headers last seen: %s"
          % (D.get("requests"), json.dumps(D.get("rate_limit_last") or {})))
    print("   served %d of %d  (%.1f%%)"
          % (len(served), len(names), 100.0 * len(served) / max(1, len(names))))
    print("   %-18s %5s %5s %7s" % ("category", "n", "ok", "rate"))
    for cat in sorted(by_cat, key=lambda c: by_cat[c]["ok"] / max(1, by_cat[c]["n"])):
        b = by_cat[cat]
        print("   %-18s %5d %5d %6.1f%%" % (cat, b["n"], b["ok"],
                                            100.0 * b["ok"] / max(1, b["n"])))
    for m, c in sorted(msgs.items(), key=lambda kv: -kv[1])[:5]:
        print("   %4d x %s" % (c, m))

    print()
    print("2. AS-TRADED CLOSES -- Yahoo auto_adjust=False vs Tradier markets/history")
    rows = []
    for t in served:
        y = (D["yahoo"].get(t) or {}).get("as_traded") or {}
        f = D["tradier"].get(t) or {}
        shared = sorted((set(y) & set(f)) - {today})
        errs = [abs(f[d] - y[d]) / y[d] for d in shared if y.get(d)]
        if len(shared) >= 60 and errs:
            rows.append((t, len(shared), _q(errs, 0.5), _q(errs, 0.95), max(errs)))
    if rows:
        med = [r[2] for r in rows]
        print("   %d names, >=60 shared sessions: median-of-medians %s  p95 %s  worst %s"
              % (len(rows), _pct(_q(med, 0.5)), _pct(_q(med, 0.95)), _pct(max(med))))
        for tol, lab in ((0.0001, "0.01%"), (0.001, "0.1%"), (0.01, "1%")):
            k = sum(1 for r in rows if r[2] <= tol)
            print("   median error within %-6s %3d of %d" % (lab, k, len(rows)))
        print("   worst by median:  %s"
              % ", ".join("%s %s" % (r[0], _pct(r[2]))
                          for r in sorted(rows, key=lambda r: -r[2])[:6]))
        print("   worst single day: %s"
              % ", ".join("%s %s" % (r[0], _pct(r[4]))
                          for r in sorted(rows, key=lambda r: -r[4])[:6]))

    print()
    print("3. THE 52-WEEK HIGH -- the number items 36 and 39 are about")
    for basis, label in (("as_traded", "as-traded (Yahoo adjust=False vs Tradier)"),
                         ("adjusted", "adjusted  (Yahoo adjust=True  vs Tradier)")):
        errs, worst = [], []
        for t in served:
            y = (D["yahoo"].get(t) or {}).get(basis) or {}
            f = D["tradier"].get(t) or {}
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
            print("   %-46s no comparable names" % label)
            continue
        print("   %-46s %d names: p50 %s p95 %s worst %s"
              % (label, len(errs), _pct(_q(errs, 0.5)), _pct(_q(errs, 0.95)), _pct(max(errs))))
        for e, t, hy, hf in sorted(worst, reverse=True)[:3]:
            print("        %-6s yahoo %-10.2f tradier %-10.2f %s" % (t, hy, hf, _pct(e)))

    print()
    print("4. SPLITS -- across a NAMED split date")
    print("   ratio = close just after / close just before; ~1 means split-adjusted.")
    for t, (split, date) in sorted(SPLIT_DATE.items()):
        def around(series):
            before = [d for d in sorted(series) if d < date][-1:]
            after = [d for d in sorted(series) if d >= date][:1]
            if not before or not after or not series[before[0]]:
                return None
            return series[after[0]] / series[before[0]]

        ry = around((D["yahoo"].get(t) or {}).get("as_traded") or {})
        rt = around(D["tradier"].get(t) or {})
        agree = ("-" if ry is None or rt is None
                 else "YES" if abs(ry - rt) / max(ry, rt) < 0.02 else "*** NO ***")
        print("   %-7s %-7s %-12s yahoo %-9s tradier %-9s %s"
              % (t, split, date,
                 "n/a" if ry is None else "%.4f" % ry,
                 "n/a" if rt is None else "%.4f" % rt, agree))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--out", default="tradier_seam_raw.json")
    a = ap.parse_args(argv)

    if a.analyse and not (a.probe or a.pull):
        analyse(a.out)
        return 0

    cfg = _cfg()
    if not _token(cfg):
        print("  no Tradier token in the environment; nothing to measure.")
        return 1
    if a.probe or not (a.pull or a.analyse):
        probe(cfg)
    if a.pull:
        pull(cfg, a.out)
    if a.analyse:
        analyse(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
