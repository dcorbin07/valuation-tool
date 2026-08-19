"""RE-PIN reproduction: how close does the FROZEN store put a banked construction to its
banked numbers? Leaf by leaf.

    python -m scripts.repin_reproduction --banked <old.json> --rerun <new.json> --label O3O4O5

ZERO TRIALS. This adjudicates nothing. It has no hypothesis, no threshold and no verdict against
a bar — it reports a distance between two artifacts and names the leaves that moved. A
divergence found here is a FINDING ABOUT THE OLD INSTRUMENT (it read a store that has since been
rewritten), never a new verdict about the strategy, and it changes no ledger verdict.

WHY THE DISTINCTION MATTERS AND IS NOT PEDANTRY. The freeze was taken from the mutable store on
2026-08-17, and this lane verified it byte-identical to that store on a 40-file sample. So the
freeze pins the FUTURE; it does not recover the bytes a 2026-08-05 book was banked on. Any
divergence reported here is drift that had ALREADY happened before the pin existed — freezing
now captures the post-drift state, it does not undo it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def leaves(obj, prefix=""):
    """Flatten to {path: scalar}. Lists are indexed so a reordering shows up as a move."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaves(v, "%s.%s" % (prefix, k) if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(leaves(v, "%s[%d]" % (prefix, i)))
    else:
        out[prefix] = obj
    return out


def _close(a, b, rel_tol=1e-9, abs_tol=1e-12):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
    return a == b


def compare(banked: dict, rerun: dict, rel_tol=1e-9):
    lb, lr = leaves(banked), leaves(rerun)
    keys_b, keys_r = set(lb), set(lr)
    moved, worst = [], []
    for k in sorted(keys_b & keys_r):
        a, b = lb[k], lr[k]
        if _close(a, b, rel_tol=rel_tol):
            continue
        rec = {"leaf": k, "banked": a, "rerun": b}
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
                and not isinstance(a, bool) and not isinstance(b, bool):
            try:
                rec["abs_delta"] = abs(b - a)
                rec["rel_delta"] = abs(b - a) / abs(a) if a else None
            except Exception:                                        # noqa: BLE001
                pass
        moved.append(rec)
    for r in moved:
        if r.get("rel_delta") is not None:
            worst.append(r)
    worst.sort(key=lambda d: -(d["rel_delta"] or 0))
    return {
        "leaves_banked": len(lb),
        "leaves_rerun": len(lr),
        "leaves_shared": len(keys_b & keys_r),
        "leaves_added": sorted(keys_r - keys_b)[:50],
        "n_added": len(keys_r - keys_b),
        "leaves_removed": sorted(keys_b - keys_r)[:50],
        "n_removed": len(keys_b - keys_r),
        "n_moved": len(moved),
        "moved": moved[:200],
        "worst_relative": worst[:20],
        "identical": (not moved) and keys_b == keys_r,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--banked", required=True)
    ap.add_argument("--rerun", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--rel-tol", type=float, default=1e-9)
    a = ap.parse_args()

    banked = json.load(open(a.banked, encoding="utf-8"))
    rerun = json.load(open(a.rerun, encoding="utf-8"))
    res = compare(banked, rerun, rel_tol=a.rel_tol)
    res["label"] = a.label
    res["banked_path"] = a.banked
    res["rerun_path"] = a.rerun
    res["what_this_is_not"] = (
        "ZERO TRIALS. No hypothesis, no threshold, no verdict. A divergence is a finding about "
        "the OLD instrument reading a store that has since been rewritten, not a new verdict, "
        "and it changes no ledger verdict.")

    print("%s: %d shared leaves, %d moved, %d added, %d removed"
          % (a.label or "reproduction", res["leaves_shared"], res["n_moved"],
             res["n_added"], res["n_removed"]))
    if res["identical"]:
        print("  BIT-IDENTICAL — the frozen store reproduces the banked artifact exactly")
    for r in res["worst_relative"][:10]:
        print("  %-60s banked %s -> rerun %s  (rel %.3e)"
              % (r["leaf"][:60], r["banked"], r["rerun"], r["rel_delta"] or 0.0))
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=2, default=str)
        print("  -> %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
