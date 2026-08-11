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


def _post(path: str, payload: dict) -> dict:
    """POST to an admin ingest endpoint. Returns the parsed response body ({} if unparseable).

    The body is returned rather than only printed because the snapshot ingest now also PUBLISHES
    the Valquo Index book, and whether that succeeded is the only signal the daily run gives —
    the 200-character print below would truncate it away.
    """
    base = os.environ["BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TOKEN"]
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-Admin-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode()
            print(f"  ingest {path}: {r.status} {raw[:200]}")
            try:
                return json.loads(raw) or {}
            except ValueError:
                return {}
    except urllib.error.HTTPError as e:
        print(f"  ingest {path} FAILED: {e.code} {e.read().decode()[:300]}")
        sys.exit(1)


def _tmp_store():
    """The scan's local store.

    Defaults to a PERSISTED path (`.scan-cache/screener.db`) so the 30-day fundamentals
    cache survives between CI runs — the workflow restores it with actions/cache. This is
    not a nicety: the FMP subscription has no bulk endpoint, so every uncached name costs
    three requests, and a 1,500-name universe on a cold cache is ~4,500 requests. With the
    cache warm a daily run only pays for names whose entry has aged out (~1/30th of the
    universe), which fits comfortably in a day's quota.

    Set SCAN_DB="" to force the old throwaway behaviour.
    """
    from valuation.screener.store import Store
    path = os.environ.get("SCAN_DB", os.path.join(".scan-cache", "screener.db"))
    if not path:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd); os.remove(path)
        return Store(path)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    return Store(path)   # screener Store takes a plain filesystem path


def run_hot() -> None:
    from valuation.screener.screen import run_scan
    scope = os.environ.get("SCAN_SCOPE", "whole_market")
    limit = int(os.environ.get("SCAN_LIMIT", "1500"))
    dcf_top = int(os.environ.get("SCAN_DCF_TOP", "12"))
    # Every name the PUBLIC list can serve gets asked whether the model refuses it. The web
    # tier caps `/api/hotstocks` at 500, so 500 is the whole exposed surface. Measured cost:
    # 387 names in 3.0 min at 6 workers. Set SCAN_REFUSAL_SCREEN=0 to turn it off if the
    # upstream feed is having a bad day — the scan still completes, it just publishes
    # unchecked peer estimates again, which is the pre-2026-08-07 behaviour.
    refusal_screen = int(os.environ.get("SCAN_REFUSAL_SCREEN", "500"))
    print(f"Running hot scan: scope={scope} limit={limit} dcf_top={dcf_top} "
          f"refusal_screen={refusal_screen}")
    res = run_scan(scope=scope, limit=limit, cfg=CONFIG, store=_tmp_store(),
                   run_dcf_top=dcf_top, save=True, refusal_screen=refusal_screen)
    rows = res.get("rows") or []
    print(f"  scored {len(rows)} names from a universe of {res.get('universe_size')}")
    h = res.get("health") or {}
    if h.get("universe_note"):
        print(f"  universe: {h['universe_note']}")
    if h.get("api_budget"):
        b = h["api_budget"]
        print(f"  api budget: {b['calls_used']} calls used"
              + (f" of {b['max_calls']}" if b.get("max_calls") else " (uncapped)")
              + (f", {b['names_skipped_over_budget']} names skipped over budget"
                 if b.get("names_skipped_over_budget") else ""))
    if h.get("refusal_screen"):
        rs = h["refusal_screen"]
        print(f"  refusal screen: asked {rs.get('screened')} names, "
              f"{rs.get('refused')} refused, {rs.get('errors', 0)} errors"
              + (f" ({rs['note']})" if rs.get("note") else ""))
        if rs.get("error_tickers"):
            print(f"    fetch failures (fail-open, peer estimate left unchecked): "
                  f"{', '.join(rs['error_tickers'])}")
    # LA1 — LOUD BY DEFAULT. The cold audit found the product's #1 name publishing a +204%
    # fair value its own valuation page refuses, and the reason nobody knew is that no counter
    # anywhere covered that row. This prints on every scan whether it is clean or not, so a
    # green line is evidence the check ran rather than evidence nothing was wrong.
    pa = h.get("publication_audit") or {}
    if pa:
        if pa.get("clean"):
            print(f"  publication audit: CLEAN — {pa.get('rows_checked')} served rows, "
                  f"0 asked-but-silent, 0 unverified, 0 outside the {pa.get('band')}x band"
                  + (f"; probe {pa['probe']}" if pa.get("probe") else ""))
        else:
            print("  " + "!" * 72)
            print(f"  LEAK — publication audit FAILED on {pa.get('rows_checked')} served rows")
            if pa.get("asked_but_silent"):
                print(f"    asked_but_silent ({pa['asked_but_silent_count']}): the DCF pass was "
                      f"asked and answered nothing, so a peer estimate is being published "
                      f"unchecked -> {', '.join(str(t) for t in pa['asked_but_silent'])}")
            if pa.get("unverified"):
                print(f"    unverified ({pa['unverified_count']}): asked, but NO statements "
                      f"came back, so the model had nothing to judge and the peer estimate "
                      f"is published unchecked -> "
                      f"{', '.join(str(t) for t in pa['unverified'][:25])}")
            if pa.get("probe"):
                print(f"    probe outcomes: {pa['probe']}")
            for b in pa.get("band_breach") or []:
                print(f"    band_breach: {b['ticker']} at {b['ratio']}x the price "
                      f"(method {b['method']}), not withheld")
            print(f"    {pa.get('note', '')}")
            print("  " + "!" * 72)
    if h.get("display_coverage"):
        print(f"  display coverage: {h['display_coverage']}")
    if not rows:
        print("  nothing scored — not ingesting."); sys.exit(1)
    resp = _post("/admin/ingest-snapshot", {
        "scan_date": res["scan_date"], "provider": res.get("provider", "ci"),
        "rows": rows, "params": {"scope": scope, "universe_size": res.get("universe_size")}})
    # The Valquo Index book the sandbox engine records. Printed explicitly because a book that
    # silently stopped being published is exactly how the engine came to record a 10-name book
    # while the published Index held 86 (PT-SPLIT). A refusal is a normal, reportable outcome —
    # it means this scan was too thin to build the contract-bound book — not a scan failure.
    book = (resp or {}).get("index_book") or {}
    if book:
        print(f"  index book: {'PUBLISHED' if book.get('published') else 'NOT published'} — "
              f"{book.get('reason', '')}")
    refresh_landing_sample()


def refresh_landing_sample() -> None:
    """Recompute the landing page's sample valuation and push it to the site.

    Runs HERE rather than on the web box because a full valuation is a multi-second,
    network-heavy job and the landing page must paint immediately — the whole point of the
    sample is to show the product working in about two seconds, which a live DCF per visitor
    would destroy.

    Deliberately NON-FATAL. This runs after the snapshot has already been ingested, and the
    ranking is the product; a stale hero sample is a cosmetic problem. Letting it fail the job
    here would turn a cosmetic miss into a red run and, worse, into a Discord alert that
    trains the reader to ignore the channel.
    """
    ticker = os.environ.get("SAMPLE_TICKER", "AAPL").strip().upper()
    try:
        from valuation.web import showcase
        sample = showcase.build(ticker, CONFIG)
        if sample.get("fair_value") is None:
            print(f"  landing sample: {ticker} produced no fair value — leaving the old one")
            return
        _post("/admin/ingest-sample", sample)
        print(f"  landing sample: {ticker} ${sample['fair_value']:.2f} "
              f"({sample.get('upside', 0) * 100:+.1f}%) ingested")
    except Exception as e:                                            # noqa: BLE001
        print(f"  landing sample failed ({type(e).__name__}: {str(e)[:160]}) — "
              f"the site keeps the previous one")


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


def _alert(text: str) -> None:
    """Ping Discord about a scan failure.

    A scan that dies is invisible: the site keeps serving the previous snapshot and nothing
    on the page changes. The July gap ran for four days before anyone noticed, so a failure
    now has to announce itself. Never raises — an alerting problem must not mask the original
    failure it is trying to report.
    """
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("  (no DISCORD_WEBHOOK_URL — failure alert not sent)")
        return
    try:
        body = json.dumps({"content": text[:1900]}).encode()
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as r:
            print(f"  discord: {r.status}")
    except Exception as e:
        print(f"  discord FAILED: {e}")


if __name__ == "__main__":
    kind = os.environ.get("KIND", "hot").strip().lower()
    try:
        (run_intraday if kind == "intraday" else run_hot)()
    except SystemExit as e:
        if e.code:
            _alert(f"🔴 **Valquo {kind} scan failed** — it exited {e.code} without ingesting. "
                   f"The site is still serving the previous snapshot.")
        raise
    except Exception as e:
        _alert(f"🔴 **Valquo {kind} scan crashed** — `{type(e).__name__}: {str(e)[:300]}`. "
               f"The site is still serving the previous snapshot.")
        raise
    print("done.")
