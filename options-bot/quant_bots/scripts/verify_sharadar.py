"""
Verify the Sharadar subscription and answer the open schema questions.

RUN THIS FIRST, BEFORE ANY SYNC. It makes a handful of small API calls and
prints a report. It does NOT print, log, or transmit your API key — paste the
output anywhere you like.

    cd quant_bots
    python scripts/verify_sharadar.py

It answers, from your actual entitlement rather than from documentation:

  1. Does the key work, and which of the 12 bundle tables can you actually
     reach? (Nasdaq's help centre says SFP is inside SFA; the datasheet and at
     least one redistributor imply otherwise. Only your key can settle it.)

  2. THE IMPORTANT ONE — does a restatement APPEND a new ARQ row, or rewrite
     the existing one? If it appends, then the obvious "latest datekey per
     reportperiod" pulls in RESTATED figures and silently reintroduces
     look-ahead into a backtest you believe is clean. The adapter is already
     written to be correct either way (it takes the earliest datekey), but
     knowing the answer tells us whether that defensive choice costs anything.

  3. The exact SEP column list — in particular whether a `dividends` column
     exists, which differs between published sources.

  4. The real, exhaustive TICKERS.category values, so the point-in-time
     universe filter is not guessing at which strings mean "common stock".

  5. SF1 percentage-unit convention: does `roe` arrive as 0.15 or as 15.0?
     Getting this wrong scales a factor by 100x, silently.

  6. Whether closeadj / close / closeunadj behave as documented, checked
     arithmetically against a known split.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from core.sharadar import BUNDLE_TABLES, SharadarClient, SharadarError

OK, NO, WARN = "  [OK]  ", "  [--]  ", "  [!!]  "


def h(title):
    print(f"\n{'=' * 72}\n  {title}\n{'=' * 72}")


def check_entitlement(c):
    h("1. Which bundle tables can this key reach?")
    reachable = []
    for table in BUNDLE_TABLES:
        try:
            rows = list(c.fetch(table, ticker="AAPL", max_pages=1))
            print(f"{OK}{table:<9} reachable ({len(rows)} sample rows)")
            reachable.append(table)
        except SharadarError as e:
            msg = str(e)
            if "403" in msg or "QEPx" in msg:
                print(f"{NO}{table:<9} NOT ENTITLED")
            else:
                print(f"{WARN}{table:<9} error: {msg[:90]}")
    return reachable


def check_restatements(c):
    h("2. Do restatements APPEND a new AR row?  <-- the one that matters")
    print("  Looking for any (ticker, dimension, reportperiod) with >1 datekey.")
    print("  If duplicates exist, 'latest datekey' silently returns RESTATED")
    print("  figures and reintroduces look-ahead. The adapter already takes the")
    print("  EARLIEST datekey, which is correct either way.\n")

    found_any = False
    for tkr in ("GE", "KHC", "WFC", "AAPL", "MSFT", "F", "T"):
        try:
            rows = list(c.fetch("SF1", ticker=tkr, dimension="ARQ",
                                columns=["ticker", "dimension", "reportperiod",
                                         "datekey", "lastupdated"]))
        except SharadarError as e:
            print(f"{WARN}{tkr}: {str(e)[:70]}")
            continue
        counts = Counter((r["reportperiod"],) for r in rows)
        dupes = {k: v for k, v in counts.items() if v > 1}
        if dupes:
            found_any = True
            print(f"{WARN}{tkr}: {len(dupes)} reportperiod(s) have MULTIPLE datekeys "
                  f"out of {len(counts)}")
            for (rp,), n in list(dupes.items())[:3]:
                dks = sorted(r["datekey"] for r in rows if r["reportperiod"] == rp)
                print(f"           {rp} -> {n} rows, datekeys {dks}")
        else:
            print(f"{OK}{tkr}: {len(rows)} rows, every reportperiod unique")

    print()
    if found_any:
        print("  VERDICT: Sharadar APPENDS on restatement.")
        print("  => Taking the earliest datekey is REQUIRED, not merely defensive.")
        print("  => Any code doing `ORDER BY datekey DESC LIMIT 1` has look-ahead.")
    else:
        print("  VERDICT: no duplicates found — AR rows appear to be rewritten")
        print("  in place rather than appended. The earliest-datekey choice is")
        print("  then a harmless no-op. (Absence of evidence across 7 tickers is")
        print("  suggestive, not conclusive.)")


def check_sep_columns(c):
    h("3. SEP columns, and the adjustment arithmetic")
    rows = list(c.fetch("SEP", ticker="AAPL", date={"gte": "2018-12-28", "lte": "2019-01-05"}))
    if not rows:
        print(f"{WARN}no rows returned")
        return
    cols = sorted(rows[0].keys())
    print(f"  Columns ({len(cols)}): {', '.join(cols)}")
    print(f"{OK if 'dividends' in cols else NO}`dividends` column "
          f"{'present' if 'dividends' in cols else 'ABSENT'}")

    r = rows[0]
    try:
        close, unadj, adj = float(r["close"]), float(r["closeunadj"]), float(r["closeadj"])
        ratio = unadj / close if close else 0
        print(f"\n  {r['date']}  close={close:.3f}  closeunadj={unadj:.3f}  closeadj={adj:.3f}")
        print(f"  closeunadj/close = {ratio:.3f}  <- cumulative split factor "
              f"(AAPL split 4:1 in Aug 2020, so ~4.0 is correct)")
        if adj < close:
            print(f"{OK}closeadj < close, as expected: dividends have been "
                  f"back-adjusted out of the historical level")
        print("\n  => Use closeadj for RETURNS (total return, incl. dividends).")
        print("  => Use closeunadj for PRICE LEVELS (screens like 'over $20').")
        print("  => Never use plain `close` for returns: it silently omits the")
        print("     entire dividend yield.")
    except (KeyError, TypeError, ValueError) as e:
        print(f"{WARN}could not compute: {e}")


def check_categories(c):
    h("4. TICKERS.category — the real values in your data")
    print("  The PIT universe filter keys on these strings. No exhaustive list")
    print("  has ever been published, so this checks against reality.\n")
    try:
        rows = list(c.fetch("TICKERS", columns=["table", "ticker", "category", "exchange"]))
    except SharadarError as e:
        print(f"{WARN}{e}")
        return
    sep_rows = [r for r in rows if (r.get("table") or "") == "SEP"]
    counts = Counter((r.get("category") or "(blank)") for r in sep_rows)
    print(f"  {len(sep_rows):,} SEP rows across {len(counts)} distinct categories:\n")
    for cat, n in counts.most_common():
        print(f"    {n:>7,}  {cat}")

    from core.pit_universe import ADR_COMMON, DOMESTIC_COMMON
    known = set(DOMESTIC_COMMON) | set(ADR_COMMON)
    unknown = [c_ for c_ in counts if c_ not in known and c_ != "(blank)"]
    print()
    if unknown:
        print(f"{WARN}{len(unknown)} value(s) the universe builder does not know, "
              f"and therefore EXCLUDES:")
        for u in unknown:
            print(f"           {counts[u]:>7,}  {u}")
        print("\n  Check whether any of these are genuinely common equity. If so,")
        print("  add them to DOMESTIC_COMMON in core/pit_universe.py.")
    else:
        print(f"{OK}every category is accounted for by the universe builder")


def check_units(c):
    h("5. SF1 percentage units — 0.15 or 15.0?")
    print("  Getting this wrong scales a factor by 100x, silently.\n")
    try:
        rows = list(c.fetch("SF1", ticker="AAPL", dimension="ARY",
                            columns=["ticker", "calendardate", "roe", "roa",
                                     "netmargin", "grossmargin", "revenueusd"]))
    except SharadarError as e:
        print(f"{WARN}{e}")
        return
    if not rows:
        print(f"{WARN}no rows")
        return
    r = sorted(rows, key=lambda x: x.get("calendardate") or "")[-1]
    print(f"  AAPL {r.get('calendardate')}:")
    for k in ("roe", "roa", "netmargin", "grossmargin"):
        print(f"    {k:<12} {r.get(k)}")
    try:
        roe = float(r.get("roe") or 0)
        print(f"\n  => roe = {roe} — units are "
              f"{'FRACTIONS (0.15 = 15%)' if abs(roe) < 3 else 'PERCENTAGES (15.0 = 15%)'}")
    except (TypeError, ValueError):
        pass
    print(f"\n  revenueusd = {r.get('revenueusd')}")
    print("  NOTE: always prefer the *usd suffixed fields for cross-sectional")
    print("  work. Plain `revenue` is in the COMPANY'S reporting currency, and")
    print("  Sharadar covers Canadian and ADR issuers.")


def check_delisted(c):
    h("6. Survivorship: is delisted price history actually retained?")
    print("  This is the property the subscription is being bought for.\n")
    try:
        rows = list(c.fetch("TICKERS", isdelisted="Y",
                            columns=["table", "ticker", "name", "isdelisted",
                                     "firstpricedate", "lastpricedate"]))
    except SharadarError as e:
        print(f"{WARN}{e}")
        return
    sep_dead = [r for r in rows if (r.get("table") or "") == "SEP"]
    print(f"{OK}{len(sep_dead):,} delisted tickers carry SEP price history")
    if not sep_dead:
        print(f"{WARN}none found — that would be a serious problem")
        return
    sample = sep_dead[0]
    px = list(c.fetch("SEP", ticker=sample["ticker"],
                      columns=["ticker", "date", "closeadj"]))
    print(f"\n  Example — {sample['ticker']} ({(sample.get('name') or '')[:44]})")
    print(f"    listed {sample.get('firstpricedate')} .. {sample.get('lastpricedate')}")
    print(f"    {len(px):,} price bars retained after delisting")
    print("\n  => These are exactly the names a live screener CANNOT show you,")
    print("     and whose absence made every prior backtest optimistic.")


def main() -> int:
    if not os.getenv("NASDAQ_DATA_LINK_API_KEY"):
        print("\nNASDAQ_DATA_LINK_API_KEY is not set.\n\n"
              "Add it to quant_bots/.env (which is gitignored):\n"
              "    NASDAQ_DATA_LINK_API_KEY=your_key_here\n\n"
              "Key lives at https://data.nasdaq.com/account/profile\n")
        return 1

    print("\n  Sharadar verification — no key material appears in this output,")
    print("  so the whole report is safe to paste anywhere.")

    c = SharadarClient()
    try:
        check_entitlement(c)
        check_restatements(c)
        check_sep_columns(c)
        check_categories(c)
        check_units(c)
        check_delisted(c)
    except SharadarError as e:
        print(f"\n{WARN}Aborted: {e}")
        return 1

    print(f"\n{'=' * 72}\n  Done. Paste this whole report back.\n{'=' * 72}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
