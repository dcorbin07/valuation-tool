# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` -- the parameterisations are proved INERT BEHAVIOURALLY, not argued.
ZERO TRIALS: a control, which under `MB1-SEL` can only ever BLOCK and never produce.

Four scripts gained `panel_path`/`out` (and `served_index_book`/`n1_band_book` a `label`), each
defaulting to the object the item already measured. The claim "every existing caller is
bit-identical" is only worth anything if it is checked, so this leaf-diffs a default-argument
re-run against the **landed** artifact.

Two keys are EXPECTED to be added and are listed rather than tolerated silently: `panel` and
`universe_label`, which exist so a reader of the file can tell which universe it describes --
the absence of exactly that stamp is what made a stale `print` readable as a clobber earlier in
this item.

`fundamental_panel`'s `--results-root` is **not** covered here: it is checked by the canonical
pair at the repo root being byte-identical before and after, which is a stronger test than a
leaf diff and is recorded in the item's own artifact.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: keys this item deliberately adds; anything else differing is a REGRESSION.
EXPECTED_NEW = ("panel", "universe_label")


def leaves(obj, prefix=""):
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


def diff(landed_path, rerun_path):
    a = leaves(json.load(io.open(landed_path, encoding="utf-8")))
    b = leaves(json.load(io.open(rerun_path, encoding="utf-8")))
    shared = set(a) & set(b)
    moved, worst = [], 0.0
    for k in sorted(shared):
        if a[k] == b[k]:
            continue
        try:
            d = abs(float(a[k]) - float(b[k]))
            worst = max(worst, d)
            if d == 0.0:
                continue
        except (TypeError, ValueError):
            d = None
        moved.append({"leaf": k, "landed": a[k], "rerun": b[k], "abs_dev": d})
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    unexpected = [k for k in added
                  if k.split(".")[0] not in EXPECTED_NEW and k not in EXPECTED_NEW]
    return {"shared": len(shared), "moved": moved, "n_moved": len(moved),
            "max_abs_dev": worst, "added": added, "removed": removed,
            "unexpected_added": unexpected,
            # MB21: a perfect zero on an empty comparison is not a pass.
            "ok": (len(shared) > 0 and not moved and not removed and not unexpected)}


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")

    pairs = [("n1_band_book", os.path.join(fa, "N1_BAND_BOOK.json"),
              os.path.join(fa, "_INERTNESS_N1.json")),
             ("served_index_book", os.path.join(fa, "INDEX_BOOK.json"),
              os.path.join(fa, "_INERTNESS_INDEX_BOOK.json"))]
    res = {"item": "UNIVERSE-BIAS", "part": "parameterisation inertness", "trials": 0,
           "expected_new_keys": list(EXPECTED_NEW), "pairs": {}}
    allok = True
    for name, landed, rerun in pairs:
        if not (os.path.exists(landed) and os.path.exists(rerun)):
            print("SKIP %s -- need both %s and %s" % (name, landed, rerun))
            res["pairs"][name] = {"skipped": True}
            allok = False
            continue
        d = diff(landed, rerun)
        res["pairs"][name] = d
        allok = allok and d["ok"]
        print("%-16s shared %4d | moved %2d | max|dev| %.3e | added %r | removed %r -> %s"
              % (name, d["shared"], d["n_moved"], d["max_abs_dev"], d["added"], d["removed"],
                 "INERT" if d["ok"] else "MOVED"), flush=True)
        for m in d["moved"][:8]:
            print("    %s: %r -> %r" % (m["leaf"], m["landed"], m["rerun"]), flush=True)

    res["all_inert"] = allok
    json.dump(res, io.open(os.path.join(fa, "UNIVERSE_BIAS_INERT.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\nall_inert = %s" % allok)
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
