"""ONE resolver for the option chain store, and it prefers the PINNED freeze.

    from valuation.edge.chain_store import resolve_chains
    CHAINS, PROV = resolve_chains(DATA)

WHY THIS EXISTS. Every banked options result in this project was measured against
`data/options`, which the MINER writes to continuously. The options re-open list measured that
**44.2% of that store's payload units were rewritten after the books were banked** — so a re-run
of any banked construction was not reading the bytes the verdict was computed on. That is O16's
failure class (a result standing on a mutable input) on the store that carries most of the
options record.

THE MUTABLE STORE IS AN EXPLICIT OPT-OUT, NEVER A SILENT FALLBACK. If the freeze is absent or
unusable this **raises**. A resolver that quietly fell back to the mutable store when the pin was
missing would reintroduce exactly the drift it exists to remove, and would do it invisibly —
which is worse than not pinning at all, because the run would still *claim* to be pinned. To read
the mutable store you must say so, either with `allow_mutable=True` or `VALQUO_CHAINS=mutable`,
and the provenance block then records that you did.

EXISTENCE IS NOT POPULATION. `DEEPITM-FIN` shipped a loader that resolved a path with
`os.path.exists`, picked an EMPTY directory over a populated one, and reported zero rows — and
`optionable_universe.is_populated_cache` exists for the same reason one session earlier. So the
freeze counts as usable only if it is actually populated AND its own summary says the copy came
out clean.

WHAT IT DOES NOT COVER: `data/options_derived/`. The freeze holds `options/` only, so anything
reading the derived layer (`v6opt_*`, `surface_stock`, `options_greeks`) is UNPINNED and is
deliberately not repointed — there is nothing to point it at.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Optional, Tuple

# The pinned freeze. Full-hash-verified at copy by the data-miner lane.
FREEZE_DEFAULT = r"D:\thetadata\freeze_options_2026-08-17"

ENV_MODE = "VALQUO_CHAINS"          # "freeze" (default) | "mutable"
ENV_FREEZE_ROOT = "VALQUO_CHAINS_FREEZE_ROOT"

# A freeze holding fewer ticker directories than this is not the store we mean. The real one
# carries 1,000; the floor sits far below that so a partial copy is caught while an ordinary
# addition is not.
MIN_TICKER_DIRS = 500
_SPOT_CHECK_DIRS = 5


class ChainStoreError(RuntimeError):
    """Raised rather than falling back. The fallback is the defect."""


def freeze_root() -> str:
    return os.environ.get(ENV_FREEZE_ROOT) or FREEZE_DEFAULT


def _read_summary(root: str) -> Optional[dict]:
    p = os.path.join(root, "FREEZE_SUMMARY.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def is_populated(chains_dir: str, min_dirs: int = MIN_TICKER_DIRS) -> Tuple[bool, str]:
    """A directory counts as the chain store only if it actually holds chains.

    Returns (ok, reason). The reason is RETURNED rather than printed so a caller can put it in a
    provenance block instead of a log nobody reads.
    """
    if not os.path.isdir(chains_dir):
        return False, "not a directory: %s" % chains_dir
    try:
        entries = sorted(os.listdir(chains_dir))
    except OSError as e:                                             # noqa: BLE001
        return False, "unreadable: %r" % (e,)
    tickers = [d for d in entries if os.path.isdir(os.path.join(chains_dir, d))]
    if len(tickers) < min_dirs:
        return False, "only %d ticker directories (floor %d)" % (len(tickers), min_dirs)
    # Directories can exist and be empty. That is the whole point of this check.
    checked = 0
    for d in tickers[: _SPOT_CHECK_DIRS * 4]:
        try:
            files = os.listdir(os.path.join(chains_dir, d))
        except OSError:                                              # noqa: PERF203
            continue
        if any(f.endswith(".pkl") for f in files):
            checked += 1
        if checked >= _SPOT_CHECK_DIRS:
            break
    if checked < _SPOT_CHECK_DIRS:
        return False, "ticker dirs present but only %d of those sampled hold a .pkl" % checked
    return True, "%d ticker directories, %d spot-checked non-empty" % (len(tickers), checked)


def manifest_fingerprint(root: str) -> Optional[dict]:
    """A NAMED artifact: sha256 of the freeze manifest, plus its line count and size.

    Recorded beside a re-pinned row so a future reader can tell whether they are looking at the
    same bytes rather than at "the freeze" as a floating label.
    """
    p = os.path.join(root, "manifest.jsonl")
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    n = 0
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            n += chunk.count(b"\n")
    return {"manifest_sha256": h.hexdigest(), "manifest_lines": n,
            "manifest_bytes": os.path.getsize(p)}


def resolve_chains(data_root: str, *, allow_mutable: bool = False,
                   min_dirs: int = MIN_TICKER_DIRS) -> Tuple[str, dict]:
    """Return (chains_dir, provenance). Prefers the pinned freeze; RAISES rather than falling back.

    `allow_mutable=True` (or `VALQUO_CHAINS=mutable`) is the explicit opt-out. It is honoured, and
    the provenance says so in a field a write-up can print.
    """
    mode = (os.environ.get(ENV_MODE) or "").strip().lower()
    want_mutable = bool(allow_mutable) or mode == "mutable"
    mutable_dir = os.path.join(data_root, "options")

    if want_mutable:
        ok, why = is_populated(mutable_dir, min_dirs=min_dirs)
        if not ok:
            raise ChainStoreError("mutable store requested but unusable: %s" % why)
        return mutable_dir, {
            "source": "MUTABLE",
            "path": mutable_dir,
            "pinned": False,
            "opt_out": "explicit (allow_mutable=True or %s=mutable)" % ENV_MODE,
            "population": why,
            "warning": ("this store is rewritten by the miner; the re-open list measured 44.2% "
                        "of its payload units rewritten after the books were banked, so a number "
                        "produced here is NOT reproducible against the banked record"),
        }

    root = freeze_root()
    chains = os.path.join(root, "options")
    summary = _read_summary(root)
    if summary is None:
        raise ChainStoreError(
            "no FREEZE_SUMMARY.json under %s. The pinned freeze is the default source; to read "
            "the mutable store you must opt out explicitly (%s=mutable)." % (root, ENV_MODE))
    if summary.get("kind") != "chain_store_freeze":
        raise ChainStoreError("%s is not a chain_store_freeze (kind=%r)"
                              % (root, summary.get("kind")))
    # The miner verified hashes at copy. Refuse a freeze that admits it did not come out clean.
    if summary.get("hash_mismatches_at_copy"):
        raise ChainStoreError("freeze reports %r hash mismatches at copy"
                              % summary.get("hash_mismatches_at_copy"))
    if summary.get("n_source_files_not_yet_frozen"):
        raise ChainStoreError("freeze is INCOMPLETE: %r source files were not frozen"
                              % summary.get("n_source_files_not_yet_frozen"))

    ok, why = is_populated(chains, min_dirs=min_dirs)
    if not ok:
        raise ChainStoreError(
            "freeze at %s is present but NOT POPULATED (%s). Existence is not population; "
            "refusing rather than falling back to the mutable store." % (root, why))

    prov = {
        "source": "FROZEN",
        "path": chains,
        "pinned": True,
        "freeze_root": root,
        "population": why,
        "generated_utc": summary.get("generated_utc"),
        "files_recorded": summary.get("files_recorded"),
        "payload_units": summary.get("payload_units"),
        "bytes": summary.get("bytes"),
        "hash_mismatches_at_copy": summary.get("hash_mismatches_at_copy"),
        "frozen_from": summary.get("source"),
    }
    fp = manifest_fingerprint(root)
    if fp:
        prov.update(fp)
    return chains, prov
