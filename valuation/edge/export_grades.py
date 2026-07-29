"""
Export FMP analyst rating actions (`stable/grades`) for offline, point-in-time backtesting.

Why this endpoint and not analyst estimates: FMP's `analyst-estimates` is NOT
point-in-time. Its `date` is the fiscal period END, there is no as-of/published field,
and there is exactly one row per fiscal target — today's consensus, restated. There is
no revision history in it to difference, at any subscription tier.

`stable/grades` is the opposite: one row per dated analyst ACTION (upgrade / downgrade /
maintain, with the previous and new grade and the firm). Every row is stamped with when
it happened, so an as-of lookup is trivially correct and there's no filing lag to model —
the action is the news. History runs from roughly 2012.

Throughput, not correctness, is the constraint. The free tier's daily request cap is a
few hundred calls and the LIVE SCREENER SHARES THE SAME KEY, so a full-universe export
cannot be done in one day on it. This exporter is therefore:

  * resumable   — it appends, and skips tickers already present in the CSV, so you can
                  run it again tomorrow (or after an upgrade) and it picks up where it
                  stopped;
  * quota-aware — on HTTP 429 it stops cleanly, writes what it has, and tells you how
                  many names remain rather than burning retries against a spent quota.

Usage:
    python -m valuation.edge.export_grades --out data/backtest --limit 250
    python -m valuation.edge.export_grades --out data/backtest --tickers AAPL,MSFT,NVDA
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

BASE = "https://financialmodelingprep.com/stable"
FIELDS = ["ticker", "date", "action", "gradingCompany", "previousGrade", "newGrade"]


class QuotaExhausted(RuntimeError):
    """HTTP 429 — the plan's request allowance is spent for now."""


def fetch_grades(ticker: str, key: str, timeout: int = 25) -> list:
    """All dated rating actions for one ticker. Raises QuotaExhausted on 429."""
    url = f"{BASE}/grades?symbol={ticker}&limit=5000&apikey={key}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise QuotaExhausted(f"429 on {ticker}") from None
        return []
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        d = (row.get("date") or "")[:10]
        if not d:
            continue
        out.append({"ticker": ticker.upper(), "date": d,
                    "action": (row.get("action") or "").lower(),
                    "gradingCompany": row.get("gradingCompany") or "",
                    "previousGrade": row.get("previousGrade") or "",
                    "newGrade": row.get("newGrade") or ""})
    return out


def quota_ok(key: str) -> tuple:
    """One cheap call to see whether the key can talk to FMP at all.

    Worth doing before a long export: a spent allowance returns 429 on EVERY endpoint
    (it's account-wide, not per-endpoint), so without this the exporter walks the whole
    ticker list getting nothing. Returns (ok, message).
    """
    try:
        with urllib.request.urlopen(f"{BASE}/quote?symbol=AAPL&apikey={key}", timeout=20) as r:
            json.loads(r.read().decode("utf-8", "replace"))
        return True, "FMP key is responding."
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return False, ("FMP is refusing calls on this key (HTTP 429, 'Limit Reach'). "
                           "The allowance is account-wide, so this also affects the live "
                           "hot-list scan until it clears.")
        return False, f"FMP returned HTTP {e.code}."
    except Exception as e:
        return False, f"Could not reach FMP ({type(e).__name__})."


def _existing(path: str) -> set:
    """Tickers already exported, so a resumed run doesn't re-spend quota on them."""
    if not os.path.exists(path):
        return set()
    seen = set()
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t = (row.get("ticker") or "").upper()
                if t:
                    seen.add(t)
    except Exception:
        pass
    return seen


def export(tickers, out_dir: str, key: str, sleep: float = 0.0,
           progress=None) -> dict:
    """Append rating actions for `tickers` to <out_dir>/grades.csv. Resumable."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "grades.csv")
    done = _existing(path)
    todo = [t for t in tickers if t.upper() not in done]

    new_file = not os.path.exists(path)
    rows_written = 0
    fetched = 0
    stopped = None
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for i, t in enumerate(todo):
            try:
                rows = fetch_grades(t, key)
            except QuotaExhausted:
                stopped = t
                break
            fetched += 1
            for r in rows:
                w.writerow(r)
                rows_written += 1
            f.flush()
            if progress and i % 25 == 0:
                progress(i, len(todo))
            if sleep:
                time.sleep(sleep)

    remaining = len(todo) - fetched
    return {"path": path, "requested": len(tickers), "already_had": len(done),
            "fetched": fetched, "rows_written": rows_written,
            "remaining": remaining, "quota_exhausted_at": stopped}


def main(argv=None):
    import argparse
    from ..config import CONFIG
    from ..screener import universe as U

    ap = argparse.ArgumentParser(description="Export FMP analyst rating actions for backtesting.")
    ap.add_argument("--out", default=os.path.join("data", "backtest"))
    ap.add_argument("--limit", type=int, default=250,
                    help="max tickers this run (the free tier's daily cap is a few hundred, "
                         "and the live screener shares the key)")
    ap.add_argument("--tickers", default="", help="explicit comma-separated list")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls")
    ap.add_argument("--check", action="store_true",
                    help="only test whether the key has allowance left, then exit "
                         "(exit 0 = usable, 3 = blocked)")
    a = ap.parse_args(argv)

    # Prefer a dedicated research key so a big export can't eat the daily allowance the
    # live 22:23 UTC hot-list scan needs. Falls back to the main key when unset.
    key = CONFIG.resolved_fmp_backtest_key
    if not key:
        print("No FMP_API_KEY set.")
        return 1
    if CONFIG.fmp_backtest_api_key.strip():
        print("Using the dedicated backtest FMP key (separate quota from the live scan).")
    else:
        print("Note: using the SAME FMP key as the live hot-list scan (22:23 UTC).\n"
              "      Set FMP_BACKTEST_API_KEY to give the backtest its own quota.")

    ok, msg = quota_ok(key)
    print(f"  preflight: {msg}")
    if a.check:
        return 0 if ok else 3
    if not ok:
        print("\n  Nothing to do until the allowance frees up — not walking the ticker\n"
              "  list to collect 429s. Re-run this when the key is responding again.")
        return 3

    if a.tickers.strip():
        tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    else:
        # Large caps first: that's where the measured edge lives, and it's the cohort
        # worth proving the signal on before paying for full-universe throughput.
        tickers = list(U.sp500_tickers(CONFIG))[:a.limit]

    print(f"Exporting analyst rating actions for {len(tickers)} tickers -> {a.out}/grades.csv")
    res = export(tickers, a.out, key, sleep=a.sleep,
                 progress=lambda i, n: print(f"  ...{i}/{n}", flush=True))
    print(f"\n  already had : {res['already_had']}")
    print(f"  fetched     : {res['fetched']}")
    print(f"  rows written: {res['rows_written']}")
    if res["quota_exhausted_at"]:
        print(f"\n  QUOTA EXHAUSTED at {res['quota_exhausted_at']} — {res['remaining']} tickers left.")
        print("  Re-run the same command later; it skips what's already in the CSV.")
        return 2
    print("\n  Done — all requested tickers exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
