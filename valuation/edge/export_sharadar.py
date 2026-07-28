"""
One-time bulk export: pull a historical provider (Sharadar) into local files, so the
whole-market backtest runs OFFLINE afterward — fast, unlimited re-runs, and no live key.

Why this exists: backtesting the whole market by hitting the API per-ticker on every run
is slow and rate-limited. Instead, download once during your paid month into the SAME
local layout the WRDS provider already reads, then set EDGE_DATA_PROVIDER=wrds pointing at
that folder. You can keep experimenting for the rest of the month (or until free WRDS in
October) with zero further API calls.

    python -m valuation.edge.export_sharadar            # exports to WRDS_DATA_DIR
    python -m valuation.edge.export_sharadar --limit 500 --out ./data/backtest

Output layout (what WRDSProvider expects):
    <out>/prices/<TICKER>.csv      columns: date,close
    <out>/fundamentals.csv         one row per (ticker, datekey) with all SF1 fields

NOTE ON LICENSING: this downloads data you have a live right to while subscribed. Whether
you may retain/use the files after cancelling depends on the vendor's terms — check them.
"""
from __future__ import annotations

import csv
import os


def _write_csv(path, rows):
    if not rows:
        return
    keys = sorted({k for r in rows for k in r})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def export_to_local(provider, tickers, out_dir, progress=None) -> dict:
    os.makedirs(os.path.join(out_dir, "prices"), exist_ok=True)
    fund_rows, ins_rows, inst_rows = [], [], []
    n_prices = 0
    total = len(tickers)

    def collect(getter, ticker, sink):
        for row in (getter(ticker) or []):
            row = dict(row)
            row.setdefault("ticker", ticker.upper())
            sink.append(row)

    for i, t in enumerate(tickers):
        try:
            d, c = provider.price_history(t, days=200000)
            if d and c:
                with open(os.path.join(out_dir, "prices", f"{t.upper()}.csv"), "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["date", "close"])
                    for dd, cc in zip(d, c):
                        w.writerow([dd, cc])
                n_prices += 1
            collect(provider.fundamentals_history, t, fund_rows)
            collect(provider.insider_history, t, ins_rows)
            collect(provider.institutional_history, t, inst_rows)
        except Exception:
            pass
        if progress and i % 50 == 0:
            progress(i, total)

    _write_csv(os.path.join(out_dir, "fundamentals.csv"), fund_rows)
    _write_csv(os.path.join(out_dir, "insiders.csv"), ins_rows)
    _write_csv(os.path.join(out_dir, "institutional.csv"), inst_rows)
    return {"tickers": total, "price_files": n_prices, "fundamental_rows": len(fund_rows),
            "insider_rows": len(ins_rows), "institutional_rows": len(inst_rows), "dir": out_dir}


def main(argv=None):
    import argparse
    from ..config import CONFIG
    from .data_providers import get_historical_provider

    ap = argparse.ArgumentParser(description="Export a historical provider to local files for offline backtesting.")
    ap.add_argument("--out", default=CONFIG.wrds_data_dir or "./data/backtest",
                    help="output folder (defaults to WRDS_DATA_DIR)")
    ap.add_argument("--limit", type=int, default=CONFIG.backtest_universe_limit,
                    help="max tickers (whole market can be thousands of API calls)")
    args = ap.parse_args(argv)

    prov = get_historical_provider(CONFIG)
    ok, msg = prov.ready()
    if not ok:
        print(f"Provider not ready: {msg}")
        return 1
    if hasattr(prov, "check"):                    # live key/subscription probe → clear error
        ok, msg = prov.check()
        print(msg)
        if not ok:
            return 1
    tickers = prov.universe(limit=args.limit) or []
    if not tickers:
        print("No universe returned by the provider (need a survivorship-free source with a ticker list).")
        return 1
    if "SPY" not in {t.upper() for t in tickers}:
        tickers = list(tickers) + ["SPY"]          # benchmark (an ETF; comes from SFP) for the backtest
    print(f"Exporting {len(tickers)} tickers from {prov.name} → {args.out} …")
    res = export_to_local(prov, tickers, args.out,
                          progress=lambda i, n: print(f"  {i}/{n}", flush=True))
    print(f"Done: {res}")
    print(f"Now set EDGE_DATA_PROVIDER=wrds and WRDS_DATA_DIR={args.out} to backtest offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
