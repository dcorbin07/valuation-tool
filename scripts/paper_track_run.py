#!/usr/bin/env python3
"""
Daily runner for the forward paper track (roadmap #12).

  python scripts/paper_track_run.py                 # the daily cycle
  python scripts/paper_track_run.py --health        # just check the sandbox creds
  python scripts/paper_track_run.py --dry-run       # broker PREVIEWS every order, places none
  python scripts/paper_track_run.py --place-equity  # also mirror the Index as equity orders

WHERE THIS SHOULD RUN. Against the SAME database the live scan writes alerts to. The alerts
live in the app's screener store on Render's persistent disk, so the scheduled path is the
token-protected `/admin/run-paper-track` endpoint (a Render cron or the GitHub Action curls
it), exactly like `/admin/run-scan` and `/admin/run-intraday`. Running this script on an
ephemeral CI runner would give it a fresh, empty database every day: it would find no alerts,
submit nothing, and lose the order state that makes the cycle idempotent — so the CI job hits
the endpoint rather than executing this file.

This script is the LOCAL path: Don's machine, or any box with the real data directory.

SAFETY. Everything routes through `paper_broker.PaperBroker`, which refuses to construct
against anything but `https://sandbox.tradier.com/v1` on the dedicated `TRADIER_PAPER_TOKEN`.
The production `TRADIER_TOKEN` is never read here and cannot be substituted.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG                                      # noqa: E402
from valuation.edge import paper_track as PT                             # noqa: E402
from valuation.edge.paper_broker import NotSandboxError, PaperBroker     # noqa: E402


def _book(store, path: str) -> dict:
    """The exported Valquo Index. Built from the latest scan if the file is not there."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    from valuation.edge.valquo_index import export
    return export(store=store, path=path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run one day of the forward paper track.")
    ap.add_argument("--dry-run", action="store_true",
                    help="send Tradier's preview=true instead of placing: validates every "
                         "order at the broker and creates nothing")
    ap.add_argument("--health", action="store_true", help="check the sandbox account and exit")
    ap.add_argument("--place-equity", action="store_true",
                    help="also mirror the Index book as sandbox equity orders (default: the "
                         "book is marked from quotes)")
    ap.add_argument("--book", default=os.path.join("data", "valquo_index.json"))
    ap.add_argument("--capital", type=float, default=100000.0,
                    help="notional the equity mirror sizes against (--place-equity only)")
    ap.add_argument("--limit", type=int, default=25, help="max new option entries per run")
    ap.add_argument("--skip-options", action="store_true")
    ap.add_argument("--skip-index", action="store_true")
    ap.add_argument("--json", action="store_true", help="print the raw result payload")
    a = ap.parse_args(argv)

    try:
        broker = PaperBroker(CONFIG, dry_run=a.dry_run)
    except NotSandboxError as e:
        print(f"REFUSED: {e}")
        return 2

    health = broker.health()
    print(f"Tradier SANDBOX {health['base']}  account {health.get('account_id') or '(unset)'}  "
          f"{'ok' if health.get('ok') else 'UNREACHABLE'}")
    if health.get("ok"):
        print(f"  paper equity ${health.get('total_equity') or 0:,.2f}  "
              f"cash ${health.get('total_cash') or 0:,.2f}")
    else:
        print(f"  {health.get('error')}")
        return 3
    if a.health:
        return 0
    if a.dry_run:
        print("  DRY RUN — orders are previewed at the broker, nothing is placed.")

    from valuation.screener.store import Store
    store = Store()
    PT.ensure_schema(store)
    out = {"health": health}

    if not a.skip_options:
        out["options"] = PT.run_options_cycle(store, broker, cfg=CONFIG, limit=a.limit)
        s, m, c = out["options"]["submitted"], out["options"]["marked"], out["options"]["closed"]
        print(f"Options: {s['submitted']} submitted, {s['skipped']} skipped, "
              f"{s['rejected']} rejected | {m['filled']} newly filled, {m['marked']} marked | "
              f"{c['closed']} closed ({c['recorded']} written to the scorecard)")
        for sk in (s.get("skips") or [])[:6]:
            print(f"   skip {sk['ticker']}: {sk['reason']}")
        for ex in (c.get("exits") or [])[:6]:
            print(f"   exit {ex['ticker']}: {ex['reason']}")

    if not a.skip_index:
        try:
            book = _book(store, a.book)
            out["seed"] = PT.seed_book(store, broker, book, place_equity=a.place_equity,
                                       capital=a.capital)
            out["index"] = PT.index_point(store, broker)
            sd, ix = out["seed"], out["index"]
            print(f"Index: {sd['held']} held, {sd['added']} added"
                  + (f", {sd['orders']} equity orders" if a.place_equity else " (quote-marked)"))
            if ix.get("ok"):
                print(f"  {ix['as_of']}: index {ix['index_ret']:+.2%} vs SPY "
                      f"{ix['bench_ret']:+.2%}  active {ix['active_ret']:+.2%}  "
                      f"({ix['n_priced']}/{ix['n_positions']} priced, since {ix['inception']})")
            else:
                print(f"  no point written: {ix.get('reason')}")
        except Exception as e:                                       # noqa: BLE001
            print(f"Index step failed: {type(e).__name__}: {e}")
            out["index_error"] = str(e)

    summary = PT.summary(store)
    print(f"\n{summary['options']['label']}")
    print(f"{summary['headline']}")
    if a.json:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
