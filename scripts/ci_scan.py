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
import time as _time
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
    # LA5 — THE SCAN'S OWN DIAGNOSTICS MUST REACH THE RECORD. This dict used to carry only
    # `scope` and `universe_size`, so `health` and `filtered` — everything run_scan computes
    # about its own data quality — were built, printed to the Actions log a few lines above,
    # and then dropped at the one boundary where they would have persisted. `/api/hotstocks`
    # serves `params.get("health")` and `params.get("filtered")`, so both were null on every
    # served payload.
    #
    # THIS IS THE MECHANISM THAT MADE LA1 AND LA6 INVISIBLE, which is why it is worth more than
    # its one-line diff. `refusal_screen` exists so that a silent zero is the tell that the
    # publication leak is back — nobody could read it, and the 2026-08-08 scan duly reported
    # zero refusals across 500 names it could not reach with nothing anywhere saying so.
    # `theme_contributing` exists to separate "the column is full" from "the theme moves the
    # score", the distinction the 42.9%-inert finding rests on — nobody could read that either.
    #
    # Size was checked rather than assumed before sending: `filtered` is a reason->count dict
    # with at most 8 example tickers per reason, and `health` is counts plus short ticker lists.
    # Measured on a real scan it is a few KB against a rows payload of ~500 scored names.
    # THE DIP PRECOMPUTE — ITEM 35(a). Value every name the screen would value at the slider's
    # FLOOR, here, once, so a request never spends a valuation budget.
    #
    # WHY IT BELONGS IN THIS JOB AND NOT IN THE REQUEST. `/api/dip` valued `DEFAULT_SHORTLIST`
    # names per request out of ~220 qualifying -- about 5% of what it was eligible to serve --
    # and the page reported the result as though it had looked at the market. Raising the
    # per-request budget was tried and measured to buy nothing (12 -> 18 valued the same 10 rows
    # across four thresholds, at 18-28s of cold latency), because the cost is per request. This
    # job has the budget: the 2026-10-06 hot run took 21m21s against a 90-minute timeout.
    #
    # THE FLOOR COVERS THE WHOLE SLIDER. The depth test is monotone in the threshold and the
    # depth-unknown names are kept at every position, so the qualifying set at 0.10 is a
    # SUPERSET of the set at any higher setting. One pass serves 0.10 through 0.40.
    #
    # NEVER FATAL, and that is not laziness: a snapshot that fails to land is a dead product
    # surface, and a dip cache that fails to build costs the OLD behaviour, which still serves.
    # The two must not share a failure.
    dip_cache = None
    try:
        from valuation.web import dip as _dip
        from valuation.engine.pipeline import value_ticker as _value
        from valuation.screener.fairvalue import estimate_fair_values as _efv
        from valuation.web import withhold as _wh
        t0 = _time.monotonic()
        # THE PRECOMPUTE MUST SELECT FROM THE ROWS THE *REQUEST* WILL SEE, NOT THE ONES THE SCAN
        # HAS. `screen.py:794` is explicit that `estimate_fair_values` runs at SERVE time rather
        # than in the scan, and `screen_snapshot` runs it and `withhold_implausible_fair_values`
        # before it screens anything. Those two set the publication flags `disqualifier_checks`
        # reads, so selecting from the raw scan rows would qualify a DIFFERENT population from
        # the one served -- and the symptom would be mild and misleading: the missing names would
        # arrive as `n_unmeasured`, which reads as a data gap rather than as two populations.
        #
        # ON A COPY, because these passes MUTATE the rows (`fair_value`, `upside` and the
        # withheld flags) and `rows` is what gets POSTed and stored. Precomputing must not
        # change the snapshot; mutating it here would make the scan's own output depend on
        # whether the dip cache was built.
        import copy as _copy
        serve_rows = _copy.deepcopy(rows)
        _efv(serve_rows, peer_rows=serve_rows)
        _wh.withhold_implausible_fair_values(serve_rows)
        dip_cache = _dip.precompute(
            serve_rows, lambda t: _value(t, CONFIG), scan_date=res["scan_date"])
        sh = dip_cache.get("shape") or {}
        print("  dip precompute: %s of %s qualifying names valued in %.1fs at %s workers"
              % (sh.get("valued"), sh.get("qualifying"), _time.monotonic() - t0,
                 sh.get("workers")))
        if sh.get("failed"):
            # A NAME THAT WOULD NOT VALUE IS COUNTED, NOT SILENT. It reaches the page as
            # `n_unmeasured`, which the surface reports; a silent drop would read as "not in a
            # drawdown", which is the sentence item 19 exists to stop.
            print("    %s could not be valued (they serve as n_unmeasured): %s"
                  % (sh["failed"], ", ".join(sh.get("failed_tickers") or [])))
        if not sh.get("valued"):
            dip_cache = None
            print("    nothing valued — NOT sending a cache; the request path keeps its "
                  "bounded live behaviour rather than serving an all-unmeasured screen")
    except Exception as e:                                           # noqa: BLE001
        print("  dip precompute FAILED (%s: %s) — the snapshot still lands and /api/dip keeps "
              "its bounded live path" % (type(e).__name__, e))
        dip_cache = None

    resp = _post("/admin/ingest-snapshot", {
        "scan_date": res["scan_date"], "provider": res.get("provider", "ci"),
        "rows": rows, "params": {"scope": scope, "universe_size": res.get("universe_size"),
                                 "health": res.get("health"), "filtered": res.get("filtered")},
        "dip_cache": dip_cache})
    # The Valquo Index book the sandbox engine records. Printed explicitly because a book that
    # silently stopped being published is exactly how the engine came to record a 10-name book
    # while the published Index held 86 (PT-SPLIT). A refusal is a normal, reportable outcome —
    # it means this scan was too thin to build the contract-bound book — not a scan failure.
    # The service's own view of what it stored, printed because a cache the scan built and the
    # service dropped would otherwise look identical to one it never built.
    dc = (resp or {}).get("dip_cache")
    print("  dip cache on the service: %s" % (dc if dc else "NOT stored"))
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
