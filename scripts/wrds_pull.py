"""
WRDS PULL — chunked, resumable, manifested. Collection only, ZERO TRIALS.

    python -m scripts.wrds_pull --product ibes_det_epsus
    python -m scripts.wrds_pull --product crsp_delist
    python -m scripts.wrds_pull --product comp_pit
    python -m scripts.wrds_pull --verify

--------------------------------------------------------------------------------------------
THE LAW.

Licensed vendor rows are written under `D:\\wrds` and NOWHERE else. Nothing under this root is
ever committed, mirrored into the repo, or rendered on a public surface. What leaves this lane
is derived statistics -- row counts, spans, byte sizes, sha256 -- in `WRDS_CENSUS.md` and the
manifest summary. That is the same split the ThetaData harvest ran under and it is not
negotiable here either.

--------------------------------------------------------------------------------------------
RESUMABLE OR IT IS WORTHLESS -- the harvest's rule, inherited whole.

One unit = one (product, chunk). The payload is written atomically (tmp + os.replace) BEFORE its
manifest line is appended and fsynced, so a kill can lose a unit's RECORD but can never leave a
half-written payload recorded as complete. Re-running re-does any unit whose payload is absent or
whose size disagrees with its record. The chain harvest lost twelve hours to a checkpoint loop
that died while workers kept going; the shape of the fix is copied deliberately.

Chunking is by YEAR for the large products. That is not arbitrary: WRDS enforces query limits and
a 34.5M-row single SELECT is the kind of request that gets killed server-side an hour in, which
is the most expensive way to discover a limit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import wrds_client as W                            # noqa: E402

SCHEMA = 1

#: product -> how to chunk it. `year_col` None means a single unchunked pull (small tables).
PRODUCTS = {
    "ibes_det_epsus": {
        "lib": "ibes", "table": "det_epsus", "year_col": "anndats",
        "why": "IBES DETAIL estimates: per-analyst, per-revision, with announce/revision dates. "
               "This is the D6 unpark -- point-in-time estimate revisions.",
    },
    "ibes_actu_epsus": {
        "lib": "ibes", "table": "actu_epsus", "year_col": "anndats",
        "why": "IBES actuals (unadjusted) -- the realised number behind a surprise.",
    },
    "ibes_statsum_epsus": {
        "lib": "ibes", "table": "statsum_epsus", "year_col": "statpers",
        "why": "IBES summary by statistical period -- consensus level and dispersion.",
    },
    "ibes_id": {
        "lib": "ibes", "table": "id", "year_col": None,
        "why": "IBES identifier table -- the ticker/cusip bridge any join needs.",
    },
    "crsp_delist": {
        "lib": "crsp_a_stock", "table": "dsedelist", "year_col": None,
        "why": "CRSP delisting returns -- the survivorship cross-check against our ACTIONS mask.",
    },
    "crsp_msedelist": {
        "lib": "crsp_a_stock", "table": "msedelist", "year_col": None,
        "why": "CRSP monthly delisting returns.",
    },
    "crsp_dsenames": {
        "lib": "crsp_a_stock", "table": "dsenames", "year_col": None,
        "why": "CRSP name history -- PERMNO/ticker over time, the identity spine.",
    },
    "comp_pit": {
        "lib": "comp", "table": "co_ifndq", "year_col": "datadate",
        "why": "Compustat point-in-time quarterly (unrestated, with _dc data codes) -- "
               "preliminary vs final filings.",
    },
}


def product_root(product: str, root: str = "") -> str:
    p = os.path.join(W.raw_root(root), product)
    os.makedirs(p, exist_ok=True)
    return p


def manifest_path(root: str = "") -> str:
    return os.path.join(W.raw_root(root), "manifest.jsonl")


def load_manifest(root: str = "") -> dict:
    out = {}
    p = manifest_path(root)
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue            # torn final line: that unit simply re-pulls
            out[f"{r['product']}|{r['chunk']}"] = r
    return out


def append_manifest(rec: dict, root: str = "") -> None:
    with open(manifest_path(root), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())        # the checkpoint must survive a hard kill


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def needs_pull(product: str, chunk: str, man: dict, root: str = "") -> bool:
    rec = man.get(f"{product}|{chunk}")
    if not rec or rec.get("status") != "ok":
        return True
    p = os.path.join(product_root(product, root), f"{product}_{chunk}.pkl")
    if not os.path.exists(p):
        return True
    return os.path.getsize(p) != rec.get("bytes")


def chunks_for(db, product: str) -> list:
    """Chunk keys, derived from the DATA rather than assumed.

    A hard-coded year range would silently drop a year the vendor added, and silently spend
    queries on years that do not exist. Ask.
    """
    spec = PRODUCTS[product]
    if not spec["year_col"]:
        return ["all"]
    yc, lib, tbl = spec["year_col"], spec["lib"], spec["table"]
    df = db.raw_sql(f"select distinct extract(year from {yc})::int as y "
                    f"from {lib}.{tbl} where {yc} is not null order by 1")
    return [str(int(y)) for y in df["y"].tolist()]


def pull_chunk(db, product: str, chunk: str, root: str = "") -> dict:
    spec = PRODUCTS[product]
    lib, tbl, yc = spec["lib"], spec["table"], spec["year_col"]
    t0 = time.time()
    if chunk == "all":
        sql = f"select * from {lib}.{tbl}"
    else:
        y = int(chunk)
        sql = (f"select * from {lib}.{tbl} where {yc} >= '{y}-01-01' "
               f"and {yc} < '{y + 1}-01-01'")
    df = db.raw_sql(sql)
    fetch_s = time.time() - t0

    p = os.path.join(product_root(product, root), f"{product}_{chunk}.pkl")
    tmp = p + ".tmp"
    df.to_pickle(tmp, compression="gzip")
    os.replace(tmp, p)               # payload lands BEFORE its manifest line
    rec = {"schema": SCHEMA, "product": product, "chunk": chunk,
           "library": lib, "table": tbl, "rows": int(len(df)),
           "columns": int(df.shape[1]), "bytes": os.path.getsize(p),
           "sha256": sha256(p), "fetch_seconds": round(fetch_s, 1),
           "total_seconds": round(time.time() - t0, 1),
           "status": "ok" if len(df) else "empty",
           "utc": W.stamp()}
    return rec


def run(product: str, root: str = "", limit: int = 0) -> dict:
    db = W.connect()
    man = load_manifest(root)
    keys = chunks_for(db, product)
    todo = [c for c in keys if needs_pull(product, c, man, root)]
    if limit:
        todo = todo[:limit]
    print(f"[wrds] {product}: {len(keys)} chunks, {len(todo)} to pull", flush=True)
    print(f"[wrds] {PRODUCTS[product]['why']}", flush=True)

    done, gb = 0, 0.0
    t0 = time.time()
    for c in todo:
        try:
            rec = pull_chunk(db, product, c, root)
        except Exception as e:                                          # noqa: BLE001
            rec = {"schema": SCHEMA, "product": product, "chunk": c,
                   "status": "failed", "error": f"{type(e).__name__}: {str(e)[:240]}",
                   "utc": W.stamp()}
            print(f"[wrds] {product} {c}: FAILED {rec['error'][:120]}", flush=True)
        append_manifest(rec, root)
        done += 1
        gb += rec.get("bytes", 0) / 1e9
        el = time.time() - t0
        eta = (len(todo) - done) * (el / max(1, done))
        print(f"[wrds] {product} {c}: {rec.get('rows', 0):,} rows "
              f"{rec.get('bytes', 0)/1e6:.1f}MB {rec.get('status')} | "
              f"{done}/{len(todo)} {gb:.2f}GB {el/60:.0f}m elapsed "
              f"{eta/60:.0f}m left", flush=True)
    print(f"[wrds] {product} finished: {done} chunks, {gb:.2f} GB, "
          f"{(time.time()-t0)/60:.0f} min", flush=True)
    return {"product": product, "chunks": done, "gb": round(gb, 3)}


def verify(root: str = "", full: bool = False) -> dict:
    man = load_manifest(root)
    missing = bad_size = bad_hash = 0
    for k, rec in man.items():
        if rec.get("status") != "ok":
            continue
        p = os.path.join(product_root(rec["product"], root),
                         f"{rec['product']}_{rec['chunk']}.pkl")
        if not os.path.exists(p):
            missing += 1
            continue
        if os.path.getsize(p) != rec.get("bytes"):
            bad_size += 1
            continue
        if full and sha256(p) != rec.get("sha256"):
            bad_hash += 1
    res = {"records": len(man), "missing": missing, "wrong_size": bad_size,
           "wrong_hash": bad_hash, "full_hash": full}
    print(json.dumps(res, indent=1))
    return res


def summarise(root: str = "") -> dict:
    man = load_manifest(root)
    per = {}
    for rec in man.values():
        p = per.setdefault(rec["product"], {"chunks": 0, "rows": 0, "bytes": 0,
                                            "failed": 0, "empty": 0})
        if rec.get("status") == "failed":
            p["failed"] += 1
            continue
        if rec.get("status") == "empty":
            p["empty"] += 1
        p["chunks"] += 1
        p["rows"] += rec.get("rows", 0)
        p["bytes"] += rec.get("bytes", 0)
    out = {"generated_utc": W.stamp(), "trials": 0, "raw_root": W.raw_root(root),
           "products": per,
           "total_rows": sum(v["rows"] for v in per.values()),
           "total_bytes": sum(v["bytes"] for v in per.values())}
    out["total_gb"] = round(out["total_bytes"] / 1e9, 3)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="WRDS chunked pull (collection only)")
    ap.add_argument("--product", default="", choices=sorted(PRODUCTS) + [""])
    ap.add_argument("--root", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--full-hash", action="store_true")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args(argv)

    if a.verify:
        verify(a.root, a.full_hash)
        return
    if a.summary or not a.product:
        print(json.dumps(summarise(a.root), indent=1))
        return
    run(a.product, a.root, a.limit)
    print(json.dumps(summarise(a.root), indent=1))


if __name__ == "__main__":
    main()
