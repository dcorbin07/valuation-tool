#!/usr/bin/env python3
"""
CI-side scan runner for the FREE deploy (the "free bridge").

Runs the heavy scan on a GitHub Actions runner — which has real internet and
plenty of RAM — then pushes the finished snapshot to the live web app's
token-protected ingest endpoint. The 512 MB free web box only does a light DB
write, so it never has to run (or run out of memory on) a whole-market scan.

When you flip to the paid Render blueprint, its built-in cron jobs do this
in-process and you can disable the GitHub Action.

Environment:
  BASE_URL        https://your-site.onrender.com     (required)
  ADMIN_TOKEN     the same token set on the web app  (required)
  KIND            "hot" (default) or "intraday"
  # hot options
  SCAN_SCOPE      whole_market | sp500 | bundled     (default whole_market)
  SCAN_LIMIT      universe cap                        (default 1500)
  SCAN_DCF_TOP    run a full DCF on the top N         (default 12)
  # intraday options
  INTRADAY_LIMIT  cap the intraday universe           (optional)
  INTRADAY_AI_TOP AI-explain the top N                (default 10)
Also reads ANTHROPIC_API_KEY / TRADIER_TOKEN / TRADIER_ENV from the env if set.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG  # noqa: E402


def _post(path: str, payload: dict) -> None:
    base = os.environ["BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TOKEN"]
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-Admin-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            print(f"  ingest {path}: {r.status} {r.read().decode()[:200]}")
    except urllib.error.HTTPError as e:
        print(f"  ingest {path} FAILED: {e.code} {e.read().decode()[:300]}")
        sys.exit(1)


def _tmp_store():
    from valuation.screener.store import Store
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd); os.remove(path)
    return Store(path)   # screener Store takes a plain filesystem path


def run_hot() -> None:
    from valuation.screener.screen import run_scan
    scope = os.environ.get("SCAN_SCOPE", "whole_market")
    limit = int(os.environ.get("SCAN_LIMIT", "1500"))
    dcf_top = int(os.environ.get("SCAN_DCF_TOP", "12"))
    print(f"Running hot scan: scope={scope} limit={limit} dcf_top={dcf_top}")
    res = run_scan(scope=scope, limit=limit, cfg=CONFIG, store=_tmp_store(),
                   run_dcf_top=dcf_top, save=True)
    rows = res.get("rows") or []
    print(f"  scored {len(rows)} names from a universe of {res.get('universe_size')}")
    if not rows:
        print("  nothing scored — not ingesting."); sys.exit(1)
    _post("/admin/ingest-snapshot", {
        "scan_date": res["scan_date"], "provider": res.get("provider", "ci"),
        "rows": rows, "params": {"scope": scope, "universe_size": res.get("universe_size")}})


def run_intraday() -> None:
    from valuation.intraday.scan import run_intraday as _scan
    limit = os.environ.get("INTRADAY_LIMIT")
    print(f"Running intraday scan (Tradier env={CONFIG.tradier_env}, "
          f"provider={'Tradier' if CONFIG.tradier_token else 'free/delayed'})")
    res = _scan(cfg=CONFIG, limit=int(limit) if limit else None, save=False)
    rows = res.get("rows") or []
    print(f"  scored {len(rows)} of {res.get('universe')} names")
    if not rows:
        print("  nothing scored — not ingesting."); sys.exit(1)
    try:
        from valuation.intraday.ai import explain_top
        ai = explain_top(rows, CONFIG, n=int(os.environ.get("INTRADAY_AI_TOP", "10")))
        for r in rows:
            if r["ticker"] in ai:
                r["ai"] = ai[r["ticker"]]
        print(f"  AI-explained {len(ai)} top names")
    except Exception as e:  # AI is optional — never block the feed on it
        print(f"  AI step skipped: {e}")
    _post("/admin/ingest-intraday", {
        "run_time": res["run_time"], "provider": res.get("provider", "ci"), "rows": rows})


if __name__ == "__main__":
    kind = os.environ.get("KIND", "hot").strip().lower()
    (run_intraday if kind == "intraday" else run_hot)()
    print("done.")
