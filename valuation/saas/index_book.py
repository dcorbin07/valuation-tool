"""Publish the Valquo Index book to disk, so the sandbox engine records the RIGHT book.

WHY THIS EXISTS — the cross-lane item Session 16 §7 named to the app lane
---------------------------------------------------------------------------
`PT-SPLIT` ended with a **gate, not a repair**. `paper_track.seed_book` now refuses to seed any
book that is not the contract-bound Valquo Index (**≥ `CONTRACT_MIN_POSITIONS` = 50 names AND the
8% cap actually binding**), so the engine stopped *adding* to a wrong book. But nothing made it
start recording the right one, because:

    `/admin/run-paper-track` reads `data/valquo_index.json` when it exists, and SILENTLY
    REBUILDS from the store's latest scan when it does not.

That silent rebuild is the whole defect. `build_index` sets
`n = max(MIN_NAMES, round(len(large) * TOP_DECILE))`, so a thin scan produces a 10-name book
carrying a perfectly correct "Valquo Index" method string — which is how the engine came to
record 10 names while the published book held 86, and how `PT-OUTBOUND` shipped an engine figure
to Discord as an Index claim.

This module closes it from the other end: **the daily scan publishes the file**, so the engine
reads a real book instead of rebuilding a truncated one.

THE MEASUREMENT THAT SAYS THIS ACTUALLY WORKS NOW
-------------------------------------------------
`seed_book`'s own comment says "the store's eligible large-cap tier is under 100 names". That was
true of the scan the engine ran against in early August; **it is not true of the current scan and
the difference is why publishing is worth doing at all.** Measured against the live site on
2026-08-10 (`/api/hotstocks?top=500`, scan of 2026-08-08): **594 names scored from a universe of
800, and 499 of the 500 returned rows are ≥ $10B** — the scanned universe is the most *liquid*
names, which are overwhelmingly large caps. The eligible tier is therefore ~593, a decile is
**~59 names**, and 59 clears the floor of 50.

**The margin is real but not large, and that is the reason for the refusal below.** If the scan
degrades to the ~190-name bundled fallback (the documented behaviour when `FMP_API_KEY` is
absent), the tier collapses and the decile lands near 19 — non-conforming. Publishing that would
hand the engine exactly the truncated book the gate exists to reject.

WHAT THIS REFUSES TO DO, AND WHY THE REFUSAL IS THE FEATURE
-----------------------------------------------------------
**A non-conforming book is never written.** Not written and labelled; not written for the engine
to reject later — not written. `PT-OUTBOUND`'s lesson is that the old code *did* label its
fallback honestly (`source: "paper-sandbox"`) and no surface ever rendered the label, so the rule
here is to make the wrong artifact unreachable rather than better annotated.

**A refusal does not delete or overwrite an existing book.** Both post-refusal states are safe by
construction — the engine either reads the last good file (whose own `scan_date` shows its age) or
finds nothing, rebuilds from the same thin scan, and refuses. Neither can start recording a wrong
book. The refusal and its reason are recorded in store meta so a run that stops publishing is
diagnosable rather than merely quiet.

ONE DEFINITION OF THE RULE
--------------------------
Conformance is `valquo_index.conformance`, reached through `build_index`'s own
`contract_conformance` block — the same object `paper_track.book_conformance` reads. This module
does not re-derive the floor, the cap, or the verdict. A second copy of "is this the Index" is
precisely the failure `PT-SPLIT` documented.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

#: Store meta key holding the most recent publish attempt (success or refusal).
META_KEY = "index_book_publish"


def _conformance_of(payload: dict) -> dict:
    blk = (payload or {}).get("contract_conformance")
    return blk if isinstance(blk, dict) else {"conforms": False,
                                              "why_not": ["no conformance block in the payload"]}


def publish(store=None, path: Optional[str] = None, record: bool = True) -> dict:
    """Build the book from the store's latest scan and write it **only if it conforms**.

    Pure-ish and importable, so the behaviour can be tested without going through HTTP — the
    admin route is a caller, not the implementation.

    Returns a dict that always carries `published` (bool) and `reason` (str). It never raises:
    the daily scan's ingest must not fail because a book could not be built.
    """
    from ..edge import valquo_index as VI

    out = {"published": False, "reason": "", "path": path or VI.DEFAULT_PATH,
           "scan_date": None, "conforms": False, "why_not": [],
           "n_positions": 0, "n_eligible": 0, "n_scored": 0,
           "at": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"}
    try:
        if store is None:
            from ..screener.store import Store
            store = Store()

        scan_date = store.latest_scan_date()
        out["scan_date"] = scan_date
        if not scan_date:
            out["reason"] = "no scan in the store yet, so there is no book to publish"
            return _record(store, out, record)

        rows = store.load_snapshot(scan_date)
        if not rows:
            out["reason"] = f"scan {scan_date} has no rows"
            return _record(store, out, record)

        # PROBE FIRST, WRITE SECOND. `export()` writes unconditionally, so conformance has to be
        # decided before it is called. `build_index` is a pure function of the same rows
        # `export` will reload, so the probe and the export agree by construction — and the
        # written payload is re-checked below rather than assumed.
        probe = VI.build_index(rows)
        conf = _conformance_of(probe)
        out.update({"conforms": bool(conf.get("conforms")),
                    "why_not": list(conf.get("why_not") or []),
                    "n_positions": int(conf.get("n_positions") or 0),
                    "n_eligible": int(probe.get("n_eligible") or 0),
                    "n_scored": int(probe.get("n_scored") or 0)})

        if not conf.get("conforms"):
            out["reason"] = (
                "NOT PUBLISHED - this scan does not build the contract-bound Valquo Index: "
                + "; ".join(out["why_not"] or ["no reason recorded"])
                + ". Any existing book file was left untouched; the engine will either read the "
                  "last good one or rebuild and refuse, and neither can record a wrong book.")
            return _record(store, out, record)

        payload = VI.export(store=store, path=out["path"])
        written = _conformance_of(payload)
        out["written_conforms"] = bool(written.get("conforms"))
        out["n_positions"] = int(written.get("n_positions") or out["n_positions"])
        if not out["written_conforms"]:
            # Not expected to fire: the same pure function on the same rows. Reported rather
            # than repaired, because both outcomes are safe — the engine's own gate refuses a
            # non-conforming file — and silently deleting a file this process just wrote would
            # trade a loud inconsistency for a quiet one.
            out["reason"] = ("WROTE A BOOK THAT DOES NOT CONFORM, which should be impossible: "
                             "the probe passed and the written payload did not. The engine will "
                             "refuse it. Investigate before trusting any book file.")
            return _record(store, out, record)

        # PROVENANCE IS RECORDED BECAUSE CONFORMANCE DOES NOT TEST IT. The rule is a size and a
        # cap; it is silent about WHICH universe the decile was taken from. This book is a decile
        # of the daily live scan (~594 names), while the contract's published 86-name series was
        # a decile of the full point-in-time Sharadar universe (861 eligible). Same construction,
        # different universe — so the holdings will not match name for name. Banked here so the
        # difference is visible in the ingest response and in store meta rather than inferred
        # later from a divergence. Flagged to the contract lane; see HANDOFF_appfixes.md.
        out["source"] = payload.get("source")
        out["published"] = True
        out["reason"] = (f"published {out['n_positions']} positions from scan {scan_date} "
                         f"(eligible large-cap tier {out['n_eligible']} of {out['n_scored']} "
                         f"scored) to {out['path']}; source: {out['source']}")
        return _record(store, out, record)
    except Exception as e:                                   # noqa: BLE001 - never break ingest
        out["reason"] = f"publish failed: {type(e).__name__}: {e}"
        try:
            return _record(store, out, record)
        except Exception:
            return out


def _record(store, out: dict, record: bool) -> dict:
    """Bank the attempt so a pipeline that quietly stopped publishing is visible."""
    if record and store is not None:
        try:
            store.set_meta(META_KEY, out)
        except Exception:
            pass
    return out


def last_publish(store=None) -> Optional[dict]:
    """What the most recent publish attempt did. None if it has never run."""
    try:
        if store is None:
            from ..screener.store import Store
            store = Store()
        return store.get_meta(META_KEY)
    except Exception:
        return None
