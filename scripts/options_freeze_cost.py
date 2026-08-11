"""Measure what a trade-scope chain freeze COSTS, for a banked options book.

    python -m scripts.options_freeze_cost [--book data/options_universe/state_r2_corrected.pkl]

This exists because the freeze design (valuation/edge/options_freeze.py) had to CHOOSE between
copying the consumed chain rows and merely fingerprinting them, and the brief required the copy
be measured before it could be rejected. The intuition it was there to check — "the store is
27 GB, copying its rows per book must be enormous" — is wrong by two orders of magnitude,
because a book reads one DAY out of ~250 per symbol-year, not the year.

Measured 2026-08-08 on `state_r2_corrected.pkl` (3,885 trades):

    alert-day chain slice rows   2,717,072
    contract-history rows          158,702
    union (deduplicated)         2,870,079      157.88 MB pickle / 27.44 MB gzip
    store                        26.98 GB       => 0.585% pickle, 0.102% gzip
    candidate days                  33,254      run scope ESTIMATED ~1,280 MB

The run-scope figure is an extrapolation (mean measured day-slice x candidate days), not a
measurement, and must be quoted as one.

Read-only: it writes a probe file to a temp path and deletes it. It never touches the store.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import pickle
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_freeze as FZ  # noqa: E402
from valuation.edge import theta_bulk as TB  # noqa: E402


def measure(book_path: str, root: str = None) -> dict:
    import pandas as pd

    root = root or TB.CACHE_ROOT
    with open(book_path, "rb") as f:
        book = pickle.load(f)
    rows = book["rows"] if isinstance(book, dict) else book
    meta = (book.get("meta") or {}) if isinstance(book, dict) else {}
    n_cand = sum(int(v.get("n_cand") or 0) for v in meta.values() if isinstance(v, dict))

    t0 = time.time()
    tmp = os.path.join(tempfile.gettempdir(), "_freeze_probe_%d.pkl.gz" % os.getpid())
    if os.path.exists(tmp):
        os.remove(tmp)
    res = FZ.freeze_book(rows, tmp, root=root, overwrite=True)
    frozen = FZ.load_frozen(tmp)

    raw = os.path.join(tempfile.gettempdir(), "_freeze_probe_%d.pkl" % os.getpid())
    with open(raw, "wb") as f:
        pickle.dump(frozen, f, protocol=4)
    raw_bytes = os.path.getsize(raw)
    gz_bytes = os.path.getsize(tmp)
    n_rows = int(len(frozen))
    per_row = raw_bytes / max(n_rows, 1)

    store_bytes = 0
    n_sy = 0
    if os.path.isdir(root):
        for sym in os.listdir(root):
            d = os.path.join(root, sym)
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.endswith(".pkl"):
                    try:
                        store_bytes += os.path.getsize(os.path.join(d, fn))
                        n_sy += 1
                    except OSError:
                        pass

    day_rows = per_row and n_rows
    mean_slice = (res["rows"] / max(len(rows), 1)) if rows else 0.0
    out = {
        "book": os.path.basename(book_path),
        "n_trades": len(rows),
        "frozen_rows": n_rows,
        "bytes_pickle": raw_bytes, "mb_pickle": round(raw_bytes / 1e6, 2),
        "bytes_gzip": gz_bytes, "mb_gzip": round(gz_bytes / 1e6, 2),
        "bytes_per_row": round(per_row, 2),
        "store_bytes": store_bytes, "store_gb": round(store_bytes / 1e9, 2),
        "store_symbol_years": n_sy,
        "pct_of_store_pickle": round(100.0 * raw_bytes / max(store_bytes, 1), 4),
        "pct_of_store_gzip": round(100.0 * gz_bytes / max(store_bytes, 1), 4),
        "n_candidate_days": n_cand,
        "run_scope_note": "ESTIMATE, not a measurement",
        "seconds": round(time.time() - t0, 1),
    }
    for p in (tmp, raw):
        try:
            os.remove(p)
        except OSError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book",
                    default=os.path.join(TB.REPO_ROOT, "data", "options_universe",
                                         "state_r2_corrected.pkl"))
    a = ap.parse_args()
    print(json.dumps(measure(a.book), indent=1))


if __name__ == "__main__":
    main()
