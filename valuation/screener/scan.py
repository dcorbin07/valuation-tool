"""
CLI scan — run the hot-stocks screener and save a dated snapshot.

    python -m valuation.screener.scan                 # bundled universe (fast)
    python -m valuation.screener.scan --whole-market  # every US filer (slow on free feed)
    python -m valuation.screener.scan --limit 800     # cap the universe size
    python -m valuation.screener.scan --insider       # add Form-4 signal to the top names
    python -m valuation.screener.scan --dcf-top 15    # run the full DCF on the top 15

This is what you schedule weekly. The web dashboard then reads the saved snapshot
instantly under the 🔥 Hot stocks tab.
"""
from __future__ import annotations

import argparse
import sys

from ..config import CONFIG
from .screen import run_scan
from .store import Store


def _progress(i, n):
    pct = (i / n * 100) if n else 0
    sys.stdout.write(f"\r  scanning… {i}/{n} ({pct:4.0f}%)")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="Hot-stocks market scan")
    ap.add_argument("--whole-market", action="store_true", help="scan every US filer (slow on free feed)")
    ap.add_argument("--limit", type=int, default=None, help="cap universe size")
    ap.add_argument("--dcf-top", type=int, default=12, help="run full DCF on the top N (default 12)")
    ap.add_argument("--insider", action="store_true", help="add SEC Form-4 signal to the top names")
    ap.add_argument("--top", type=int, default=25, help="how many to print")
    args = ap.parse_args()

    scope = "whole_market" if args.whole_market else "bundled"
    store = Store()
    print(f"Scanning ({scope})… provider auto-selected (FMP if FMP_API_KEY set, else free).")
    res = run_scan(scope=scope, limit=args.limit, cfg=CONFIG, store=store,
                   run_dcf_top=args.dcf_top, progress=_progress, save=True)
    print()
    rows = res["rows"]
    if args.insider and rows:
        from .insider import enrich_insider
        print("Fetching insider (Form 4) signals for the top names…")
        enrich_insider(rows, CONFIG, top=args.top)

    f = res.get("filtered")
    if f and f.get("total_removed"):
        parts = ", ".join(f"{v} {k}" for k, v in sorted(f["by_reason"].items(), key=lambda x: -x[1]))
        print(f"Pre-filtered {f['total_removed']} non-investable names: {parts}")
    print(f"\nScan {res['scan_date']}: {res['scored']}/{res['universe_size']} scored "
          f"via {res.get('provider')}\n")
    print(f"{'#':>3} {'TICKER':<8}{'SECTOR':<22}{'BUCKET':<12}{'HOT':>4}{'FAIRVAL':>10}{'UPSIDE':>8}")
    print("-" * 70)
    for r in rows[:args.top]:
        fv = f"${r['fair_value']:,.0f}" if r.get("fair_value") else "—"
        up = f"{r['upside']*100:+.0f}%" if r.get("upside") is not None else ""
        print(f"{r['rank']:>3} {r['ticker']:<8}{(r['sector'] or '')[:20]:<22}{(r['bucket'] or ''):<12}"
              f"{(r['hot_score'] or 0):>4.0f}{fv:>10}{up:>8}")
    print(f"\nSaved. Open the dashboard (python run.py) → 🔥 Hot stocks → Load latest.")


if __name__ == "__main__":
    main()
