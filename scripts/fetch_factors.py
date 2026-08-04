#!/usr/bin/env python3
"""fetch_factors.py — the free factor datasets R1 needs.  [D3]

R1 (factor-adjusted alpha) is the single most important test in the audit and it cannot run
without a factor model to regress against. This script lands the free ones, reproducibly:

  * Ken French FF5 + momentum (daily and monthly) — the FF5+MOM regression R1 specifies
  * Hou-Xue-Zhang q-factors from global-q.org — the harder test for a quality-tilted book
  * Open Source Asset Pricing (Chen-Zimmermann) — best effort, see BEST_EFFORT below

Modifies no existing file. Everything lands under --dest (default `data/factors/`).

    python scripts/fetch_factors.py                  # fetch + verify + write manifest
    python scripts/fetch_factors.py --verify         # re-verify the cache, download nothing
    python scripts/fetch_factors.py --force          # ignore the cache and re-download

LICENCE DISCIPLINE — the reason this script sorts its output into two trees
--------------------------------------------------------------------------
Not every free dataset is free to *ship*. Anything whose licence forbids commercial use lands
under `<dest>/research_only/` and is recorded in the manifest with `commercial_ok: false`.
Product code must never read that directory. In particular **JKP / Global Factor Data
(jkpfactors.com) is CC BY-NC 4.0 — research only, never shipped into the product**, which is
why it is registered here as a deliberate non-fetch rather than omitted and forgotten.

Where a source states no explicit commercial grant, this script records `commercial_ok: null`
("unestablished") rather than guessing. Per the pre-registration, unestablished is treated as
not-commercially-usable until someone confirms it in writing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime

UA = {"User-Agent": "Mozilla/5.0 (valquo-research; factor-data fetch)"}

# R1 needs the first three. Everything else is a nice-to-have and cannot fail the item.
DATASETS = [
    {
        "key": "ff5_daily",
        "title": "Fama-French 5 factors (2x3), daily",
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
               "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
        "kind": "zip_csv",
        "required": True,
        "licence": "Ken French Data Library — free, no registration. No explicit commercial "
                   "grant is stated on the source page.",
        "commercial_ok": None,
        "cite": "Fama & French (2015), 'A five-factor asset pricing model', JFE 116(1).",
    },
    {
        "key": "mom_daily",
        "title": "Fama-French momentum factor, daily",
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
               "F-F_Momentum_Factor_daily_CSV.zip",
        "kind": "zip_csv",
        "required": True,
        "licence": "Ken French Data Library — free, no registration. No explicit commercial "
                   "grant is stated on the source page.",
        "commercial_ok": None,
        "cite": "Carhart (1997), 'On persistence in mutual fund performance', JF 52(1).",
    },
    {
        "key": "q5_daily",
        "title": "Hou-Xue-Zhang q5 factors, daily",
        # Resolved at runtime — see _resolve_globalq(). The undated .../q5_factors_daily.csv
        # still returns 200 but is a STALE 2018 snapshot; the live file is year-suffixed.
        "url": "https://global-q.org/uploads/1/2/2/6/122679606/q5_factors_daily_2025.csv",
        "resolve": "daily",
        "kind": "csv",
        "required": True,
        "licence": "global-q.org — free to download and use, citation requested.",
        "commercial_ok": None,
        "cite": "Hou, Mo, Xue & Zhang (2021), 'An augmented q-factor model', RoF 25(1); "
                "Hou, Xue & Zhang (2015), RFS 28(3).",
    },
    {
        "key": "ff5_monthly",
        "title": "Fama-French 5 factors (2x3), monthly",
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
               "F-F_Research_Data_5_Factors_2x3_CSV.zip",
        "kind": "zip_csv",
        "required": False,
        "licence": "Ken French Data Library — free, no registration.",
        "commercial_ok": None,
        "cite": "Fama & French (2015).",
    },
    {
        "key": "q5_monthly",
        "title": "Hou-Xue-Zhang q5 factors, monthly",
        "url": "https://global-q.org/uploads/1/2/2/6/122679606/q5_factors_monthly_2025.csv",
        "resolve": "monthly",
        "kind": "csv",
        "required": False,
        "licence": "global-q.org — free to download and use, citation requested.",
        "commercial_ok": None,
        "cite": "Hou, Mo, Xue & Zhang (2021).",
    },
]

# Registered so the licence is on the record, NOT fetched. See the module docstring.
DO_NOT_FETCH = [
    {
        "key": "jkp_global_factors",
        "title": "Global Factor Data (jkpfactors.com) — 153 characteristics, 93 countries",
        "url": "https://jkpfactors.com/",
        "licence": "CC BY-NC 4.0 — NON-COMMERCIAL ONLY.",
        "commercial_ok": False,
        "why_not_fetched": "Usable for research (it is the natural home for X8, the "
                           "different-country replication) but it must never reach product "
                           "code. Fetch it deliberately into research_only/ when X8 runs, "
                           "not as a side effect of a script every lane calls.",
    },
]

# Best effort: the file host redirects and may require a browser. Not required by R1.
BEST_EFFORT = [
    {
        "key": "osap_signal_docs",
        "title": "Open Source Asset Pricing (Chen-Zimmermann) — signal documentation",
        "url": "https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/"
               "SignalDoc.csv",
        "kind": "csv",
        "licence": "MIT (code) / freely redistributable data, citation requested.",
        "commercial_ok": True,
        "cite": "Chen & Zimmermann (2022), 'Open Source Cross-Sectional Asset Pricing', CAR.",
    },
]


# ---------------------------------------------------------------- fetch / cache

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _download(url: str, tries: int = 3) -> bytes:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:                      # noqa: BLE001 - report, then retry
            last = e
            if i < tries - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"download failed after {tries} tries: {last}")


def _resolve_globalq(freq: str, fallback: str) -> str:
    """Find the CURRENT year-suffixed q-factor file.

    This exists because of a live trap: `.../q5_factors_daily.csv` (no year) still returns
    HTTP 200 and looks perfectly healthy, but it is a 2018 snapshot — it would have silently
    handed R1 a factor model that ends seven years before the panel does. The listing page is
    the only authority on which file is current, so scrape it and fail loudly if that breaks.
    """
    try:
        req = urllib.request.Request("https://global-q.org/factors.html", headers=UA)
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        pat = re.compile(r"/uploads/[\w/]+/q5_factors_" + freq + r"_(\d{4})\.csv")
        hits = pat.findall(html)
        if hits:
            year = max(hits)
            path = pat.pattern.replace(r"(\d{4})", year).replace(r"[\w/]+", "1/2/2/6/122679606")
            return "https://global-q.org" + path.replace("\\", "")
    except Exception as e:                           # noqa: BLE001 - fall back, but say so
        print(f"    (global-q {freq}: listing lookup failed, {type(e).__name__}; "
              f"using pinned URL)", flush=True)
    return fallback


def _cached(raw_dir: str, key: str, url: str, force: bool) -> tuple[bytes, bool]:
    """Return (bytes, from_cache). Idempotency lives here: a second run re-reads."""
    path = os.path.join(raw_dir, key + os.path.splitext(url.split("?")[0])[1])
    if os.path.exists(path) and not force:
        with open(path, "rb") as f:
            return f.read(), True
    blob = _download(url)
    os.makedirs(raw_dir, exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    return blob, False


# ---------------------------------------------------------------- parsing

_DATE_ROW = re.compile(r"^\s*(\d{6,8})\s*,")


def _parse_french(blob: bytes) -> "pd.DataFrame":
    """Ken French CSVs carry a prose preamble, then a header, then dated rows, then
    sometimes a second annual block. Locate the block structurally rather than by a
    hard-coded skiprows, which breaks every time they edit the preamble."""
    import pandas as pd

    if blob[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            text = z.read(name).decode("latin-1")
    else:
        text = blob.decode("latin-1")

    lines = text.splitlines()
    first = next(i for i, ln in enumerate(lines) if _DATE_ROW.match(ln))
    header = lines[first - 1]
    cols = [c.strip() for c in header.split(",")]
    cols[0] = "date"

    rows = []
    for ln in lines[first:]:
        m = _DATE_ROW.match(ln)
        if not m:
            if rows:                                # end of the daily block; ignore annexes
                break
            continue
        if len(m.group(1)) != len(_DATE_ROW.match(lines[first]).group(1)):
            break                                   # monthly block gave way to annual
        rows.append([p.strip() for p in ln.split(",")])

    df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
    fmt = "%Y%m%d" if len(df["date"].iloc[0]) == 8 else "%Y%m"
    df["date"] = pd.to_datetime(df["date"], format=fmt)
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0    # percent -> decimal
    return df.dropna(how="all", subset=list(df.columns[1:])).reset_index(drop=True)


def _parse_globalq(blob: bytes) -> "pd.DataFrame":
    import pandas as pd

    df = pd.read_csv(io.BytesIO(blob))
    df.columns = [c.strip() for c in df.columns]
    dcol = df.columns[0]
    s = df[dcol].astype(str).str.replace(r"\.0$", "", regex=True)
    if s.str.contains("-").any():                    # 2025 files switched to ISO 'YYYY-MM-DD'
        df["date"] = pd.to_datetime(s, format="ISO8601")
    elif s.str.len().max() >= 8:                     # older files: compact 'YYYYMMDD'
        df["date"] = pd.to_datetime(s, format="%Y%m%d")
    else:                                            # monthly file: separate year/month cols
        ycol = [c for c in df.columns if c.lower() in ("year",)][0]
        mcol = [c for c in df.columns if c.lower() in ("month",)][0]
        df["date"] = pd.to_datetime(
            df[ycol].astype(int).astype(str) + df[mcol].astype(int).astype(str).str.zfill(2),
            format="%Y%m")
    keep = ["date"] + [c for c in df.columns if c.upper().startswith("R_")]
    df = df[keep].copy()
    for c in keep[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0    # percent -> decimal
    return df.reset_index(drop=True)


def _parse_plain(blob: bytes) -> "pd.DataFrame":
    import pandas as pd
    return pd.read_csv(io.BytesIO(blob))


# ---------------------------------------------------------------- verification

def _verify(key: str, df, required: bool) -> dict:
    """The pre-registered bar: >= 1998-01-01 -> 2025-12-31, no interior gap > 5 trading days."""
    import pandas as pd

    out = {"rows": int(len(df))}
    if "date" not in df.columns:
        out["checks"] = {"has_date": False}
        out["ok"] = not required
        return out

    d = pd.to_datetime(df["date"]).sort_values()
    out["start"], out["end"] = str(d.iloc[0].date()), str(d.iloc[-1].date())

    daily = key.endswith("_daily")
    gaps = []
    if daily:
        # The bar is "no interior gap > 5 trading days WITHIN the panel's span". Check it over
        # 1998+ only: Ken French's momentum series runs back to 1926 and has real holes in the
        # 1920s-30s that say nothing about the window R1 regresses over.
        win = d[d >= pd.Timestamp("1998-01-01")]
        bd = pd.Series(win.values)
        span = bd.diff().dt.days.fillna(0)
        for i in span[span > 9].index:               # >9 calendar days ~ >5 business days
            gaps.append({"after": str(pd.Timestamp(bd[i - 1]).date()),
                         "before": str(pd.Timestamp(bd[i]).date()),
                         "calendar_days": int(span[i])})

    # A monthly series stamps December 2025 as 2025-12-01, so requiring 12-31 would fail a
    # file that does cover the period. Daily keeps the strict end date.
    end_bar = pd.Timestamp("2025-12-31" if daily else "2025-12-01")
    checks = {
        "covers_panel_start_1998": bool(d.iloc[0] <= pd.Timestamp("1998-01-01")),
        "covers_through_2025": bool(d.iloc[-1] >= end_bar),
        "no_gap_over_5_business_days": len(gaps) == 0,
        "monotonic_unique_dates": bool(d.is_monotonic_increasing and d.is_unique),
    }
    if not daily:
        checks.pop("no_gap_over_5_business_days")
    out["checks"] = checks
    out["gaps"] = gaps[:10]
    out["ok"] = all(checks.values())
    return out


def compound_to_grid(factors, grid_dates, cols=None):
    """Compound daily factor returns onto the panel's 63-trading-day rebalance grid.  [R1]

    `grid_dates` are the panel's rebalance dates. For each adjacent pair (t, t+1) the factor
    return is the product of (1+r) over days STRICTLY AFTER t and up to and including t+1 —
    the same convention as a position opened at t's close and closed at t+1's close.

    Excluding day t itself is the point: including it would credit the portfolio with a return
    earned before it was formed, which is exactly the look-ahead R1 exists to rule out.

    Returns a frame indexed by the END date of each window, so it aligns directly with the
    panel's forward returns.
    """
    import pandas as pd

    f = factors.copy()
    f["date"] = pd.to_datetime(f["date"])
    f = f.set_index("date").sort_index()
    cols = cols or [c for c in f.columns if c.lower() != "rf"]

    g = pd.to_datetime(pd.Series(sorted(pd.to_datetime(grid_dates).unique())))
    rows = []
    for a, b in zip(g[:-1], g[1:]):
        w = f.loc[(f.index > a) & (f.index <= b), cols]
        if w.empty:
            continue
        rows.append({"start": a, "end": b, "n_days": int(len(w)),
                     **{c: float((1.0 + w[c]).prod() - 1.0) for c in cols}})
    return pd.DataFrame(rows).set_index("end")


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch the free factor datasets (D3).")
    ap.add_argument("--dest", default="data/factors")
    ap.add_argument("--verify", action="store_true", help="re-verify the cache, download nothing")
    ap.add_argument("--force", action="store_true", help="ignore the cache and re-download")
    args = ap.parse_args(argv)

    try:
        import pandas as pd                                          # noqa: F401
    except ImportError:
        print("pandas is required", file=sys.stderr)
        return 1

    raw = os.path.join(args.dest, "raw")
    parsed = os.path.join(args.dest, "parsed")
    research_only = os.path.join(args.dest, "research_only")
    for d in (raw, parsed, research_only):
        os.makedirs(d, exist_ok=True)
    with open(os.path.join(research_only, "README.txt"), "w") as f:
        f.write("Datasets here are NOT commercially usable. Product code must never read this\n"
                "directory. See ../MANIFEST.json for the per-dataset licence.\n")

    manifest = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "item": "D3",
        "purpose": "factor models for R1 (factor-adjusted alpha)",
        "datasets": {}, "not_fetched": {}, "failures": {},
    }
    failures = []

    for spec in DATASETS + BEST_EFFORT:
        key, url = spec["key"], spec["url"]
        best_effort = spec in BEST_EFFORT
        if spec.get("resolve") and not args.verify:
            url = _resolve_globalq(spec["resolve"], url)
        try:
            if args.verify:
                cand = [p for p in os.listdir(raw) if p.startswith(key + ".")]
                if not cand:
                    raise FileNotFoundError(f"{key} not in cache")
                with open(os.path.join(raw, cand[0]), "rb") as fh:
                    blob, from_cache = fh.read(), True
            else:
                blob, from_cache = _cached(raw, key, url, args.force)

            if "global-q" in url:
                df = _parse_globalq(blob)
            elif spec.get("kind") in ("zip_csv",) or "french" in url.lower():
                df = _parse_french(blob)
            else:
                df = _parse_plain(blob)

            v = _verify(key, df, bool(spec.get("required")))
            out_dir = parsed if spec.get("commercial_ok") is not False else research_only
            out_csv = os.path.join(out_dir, key + ".csv")
            df.to_csv(out_csv, index=False)

            manifest["datasets"][key] = {
                "title": spec["title"], "url": url,
                "sha256": _sha256(blob), "bytes": len(blob),
                "from_cache": from_cache, "parsed_to": out_csv.replace("\\", "/"),
                "columns": [str(c) for c in df.columns],
                "licence": spec["licence"], "commercial_ok": spec.get("commercial_ok"),
                "cite": spec.get("cite"), "required_by_R1": bool(spec.get("required")),
                **v,
            }
            flag = "ok " if v.get("ok") else ("BEST-EFFORT" if best_effort else "FAILS BAR")
            print(f"  [{flag:^11s}] {key:18s} {v.get('rows',0):>7,} rows  "
                  f"{v.get('start','?')} -> {v.get('end','?')}  "
                  f"{'(cache)' if from_cache else '(downloaded)'}", flush=True)
            if not v.get("ok") and spec.get("required"):
                failures.append(f"{key}: verification bar not met {v.get('checks')}")

        except Exception as e:                       # noqa: BLE001 - a failure is a result
            manifest["failures"][key] = {"error": f"{type(e).__name__}: {e}", "url": url,
                                         "best_effort": best_effort}
            print(f"  [{'BEST-EFFORT' if best_effort else 'FAILED':^11s}] {key:18s} "
                  f"{type(e).__name__}: {str(e)[:70]}", flush=True)
            if spec.get("required"):
                failures.append(f"{key}: {type(e).__name__}: {e}")

    for spec in DO_NOT_FETCH:
        manifest["not_fetched"][spec["key"]] = spec
        print(f"  [{'NOT FETCHED':^11s}] {spec['key']:18s} {spec['licence']}")

    mpath = os.path.join(args.dest, "MANIFEST.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nmanifest -> {mpath}")

    if failures:
        print("\nD3 INCOMPLETE — required datasets did not meet the pre-registered bar:")
        for x in failures:
            print(f"  - {x}")
        return 1
    print("\nD3 COMPLETE — every dataset R1 requires is present and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
