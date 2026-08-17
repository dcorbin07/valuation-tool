"""Tier 0 - pin the mutable EOD chain store into a fingerprinted, dated freeze.

WHY. `data/options` is the store the analysis scripts actually read -- `o3_o4_o5_surface.py`,
`o6_o7_o17_earnings.py` and `o11_o19_o22_o25_portfolio.py` all set
`CHAINS = os.path.join(DATA, "options")`, not the freeze. It is MUTABLE and rewritten in place:
measured 2026-08-17, all 5,063 units carry mtimes inside 2026-08-01..08-07 and **2,236 of them
(44.2%) were written AFTER the authoritative book was banked on 2026-08-05 19:51**. That is
audit O16's failure, on the store that matters, and larger than O16's own 19.5% because O16
measured only the files the book CONSUMED.

WHAT THIS IS NOT. This does not fetch anything. It is a byte-for-byte copy plus a sha256 per
unit, so it has no vendor deadline and cannot be lost when the ThetaData Pro window closes on
2026-09-01. It never writes into `data/options`.

WHAT IT UNLOCKS. The existing trade-scope freeze
(`data/options_freeze/R2_CORRECTED_2026-08-08/`) holds a forward path for the traded contract
and ZERO alternatives, so any question needing a contract the book never held is unanswerable
on it by construction -- audit O21-D2 exactly. Measured here: the live store carries a chain on
**3,885 of 3,885 entry dates**, the traded contract on **3,885 of 3,885**, and **2,713,919
alternative contracts** (median 636 per entry date, 8 expirations, 61 strikes). The alternatives
already exist. What they lack is a pinned referent.

COLLECTION AND PROVENANCE ONLY. Zero trials. No analysis, no verdict.

    python freeze_chain_store.py --dest D:\thetadata\freeze_options_2026-08-17
    python freeze_chain_store.py --dest ... --verify [--full-hash]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import time

REPO = r"C:\Users\donni\Downloads\valuation-tool"
SRC = os.path.join(REPO, "data", "options")
DEFAULT_DEST = r"D:\thetadata\freeze_options_" + dt.date.today().isoformat()
SCHEMA = 1
BLK = 1 << 20


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(BLK), b""):
            h.update(blk)
    return h.hexdigest()


def free_gb(path: str) -> float:
    try:
        return shutil.disk_usage(os.path.splitdrive(os.path.abspath(path))[0] + "\\").free / 1e9
    except OSError:
        return -1.0


def inventory(src: str):
    """Every file under the store, payload and sidecar alike. Sidecars are part of the state."""
    out = []
    for d in sorted(os.listdir(src)):
        dd = os.path.join(src, d)
        if not os.path.isdir(dd):
            continue
        for f in sorted(os.listdir(dd)):
            p = os.path.join(dd, f)
            if os.path.isfile(p):
                st = os.stat(p)
                out.append({"rel": f"{d}/{f}", "bytes": st.st_size, "mtime": st.st_mtime})
    return out


def _replace_retry(tmp: str, dst: str, tries: int = 8) -> None:
    """os.replace, retried.

    On Windows a freshly written file is transiently opened by the AV/indexer, and the rename
    fails with WinError 32 ("being used by another process"). That killed the first full run
    3,000 files in. It is a race, not corruption, so it is retried with backoff -- and if it
    still will not land it is raised, never skipped, because a skipped file would be a silent
    hole in the freeze.
    """
    for k in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(0.25 * (k + 1))


def manifest_path(dest: str) -> str:
    return os.path.join(dest, "manifest.jsonl")


def load_manifest(dest: str) -> dict:
    p = manifest_path(dest)
    done = {}
    if not os.path.exists(p):
        return done
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue                      # a torn final line re-copies that unit
            done[r["rel"]] = r
    return done


def append(dest: str, rec: dict) -> None:
    with open(manifest_path(dest), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def run(src: str, dest: str, limit=None) -> dict:
    os.makedirs(dest, exist_ok=True)
    inv = inventory(src)
    tot = sum(r["bytes"] for r in inv)
    done = load_manifest(dest)
    print(f"[freeze] source {src}", flush=True)
    print(f"[freeze] {len(inv)} files, {tot/1e9:.2f} GB | already recorded {len(done)} "
          f"| dest {dest} free {free_gb(dest):.0f}GB", flush=True)
    if free_gb(dest) * 1e9 < tot * 1.05:
        raise SystemExit("[freeze] ABORT: destination free space under 105% of the payload")

    todo = [r for r in inv if r["rel"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"[freeze] to copy {len(todo)}", flush=True)
    t0 = time.time()
    copied = 0
    for i, r in enumerate(todo, 1):
        s = os.path.join(src, r["rel"].replace("/", os.sep))
        d = os.path.join(dest, "options", r["rel"].replace("/", os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        tmp = d + ".tmp"
        shutil.copyfile(s, tmp)
        _replace_retry(tmp, d)                # payload lands BEFORE its manifest line
        h = sha256(d)
        hs = sha256(s)
        rec = {"rel": r["rel"], "bytes": os.path.getsize(d), "sha256": h,
               "source_sha256": hs, "match": h == hs,
               "source_mtime_utc": dt.datetime.fromtimestamp(
                   r["mtime"], dt.timezone.utc).isoformat(timespec="seconds"),
               "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        append(dest, rec)
        copied += rec["bytes"]
        if not rec["match"]:
            # The source changed under us mid-copy. That is exactly the drift this exists to
            # catch, so it is loud and it stops.
            raise SystemExit(f"[freeze] STOP: {r['rel']} copy hash != source hash")
        if i % 250 == 0:
            el = time.time() - t0
            print(f"[freeze] {i}/{len(todo)}  {copied/1e9:.2f}GB  {el:.0f}s  "
                  f"{copied/el/1e6:.0f}MB/s", flush=True)
    return summarise(src, dest)


def summarise(src: str, dest: str) -> dict:
    done = load_manifest(dest)
    inv = {r["rel"]: r for r in inventory(src)}
    payload = [r for r in done.values() if r["rel"].endswith(".pkl")]
    out = {
        "schema": SCHEMA,
        "kind": "chain_store_freeze",
        "source": src,
        "dest": dest,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "files_recorded": len(done),
        "files_in_source_now": len(inv),
        "payload_units": len(payload),
        "bytes": sum(r["bytes"] for r in done.values()),
        "hash_mismatches_at_copy": sum(1 for r in done.values() if not r.get("match")),
        "source_files_not_yet_frozen": sorted(set(inv) - set(done))[:50],
        "n_source_files_not_yet_frozen": len(set(inv) - set(done)),
        "frozen_files_gone_from_source": sorted(set(done) - set(inv))[:50],
        "n_frozen_files_gone_from_source": len(set(done) - set(inv)),
    }
    p = os.path.join(dest, "FREEZE_SUMMARY.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in out.items()
                      if not k.startswith(("source_files_not", "frozen_files_gone"))}, indent=1))
    return out


def verify(src: str, dest: str, full: bool = False) -> dict:
    """Re-hash the FROZEN copy, and separately report whether the SOURCE has drifted since."""
    done = load_manifest(dest)
    bad_size = bad_hash = missing = 0
    drifted = []
    t0 = time.time()
    for i, (rel, r) in enumerate(sorted(done.items()), 1):
        d = os.path.join(dest, "options", rel.replace("/", os.sep))
        if not os.path.exists(d):
            missing += 1
            continue
        if os.path.getsize(d) != r["bytes"]:
            bad_size += 1
            continue
        if full and sha256(d) != r["sha256"]:
            bad_hash += 1
        s = os.path.join(src, rel.replace("/", os.sep))
        if full and os.path.exists(s) and sha256(s) != r["source_sha256"]:
            drifted.append(rel)
        if i % 500 == 0:
            print(f"[verify] {i}/{len(done)}  {time.time()-t0:.0f}s", flush=True)
    res = {"records": len(done), "missing": missing, "wrong_size": bad_size,
           "wrong_hash": bad_hash, "full_hash": full,
           "source_drifted_since_freeze": len(drifted), "drift_examples": drifted[:20],
           "seconds": round(time.time() - t0, 1)}
    print(json.dumps(res, indent=1))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--dest", default=DEFAULT_DEST)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--full-hash", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--mirror", default=None, help="copy the manifest+summary here as well")
    a = ap.parse_args(argv)
    if a.verify:
        verify(a.src, a.dest, a.full_hash)
    elif a.summary:
        summarise(a.src, a.dest)
    else:
        run(a.src, a.dest, a.limit)
    if a.mirror:
        os.makedirs(a.mirror, exist_ok=True)
        for f in ("manifest.jsonl", "FREEZE_SUMMARY.json"):
            p = os.path.join(a.dest, f)
            if os.path.exists(p):
                shutil.copyfile(p, os.path.join(a.mirror, f))
        print(f"[freeze] mirrored record to {a.mirror}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
