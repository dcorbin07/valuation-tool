"""I-3 -- the validation that licenses `valuation/studies/crash_gate.py` to have consumers.

`IDEAS_LEDGER.md` PART 3: *"Validation: reproduces `MA28-CARD`'s banked verdict bit-identical."*
This is that check, and it is run and read BEFORE any new register calls the library -- the
`MB15` lesson (validate the instrument before the hypothesis) and `MB16`'s two-pass discipline.

TWO INDEPENDENT COMPARISONS, because they can fail differently
---------------------------------------------------------------
A  **LIBRARY vs THE BANKED ARTIFACT.** Rebuild `MA28`'s exact frame and run the delegating
   `scripts/ma28_riskcard.py` through the library, then diff every leaf of all three windows
   against the shipped `data/free_analysis/MA28_CARD.json`. This is the required validation and
   it is the one that proves the library computes the published object.

B  **LIBRARY vs THE PRE-REFACTOR SOURCE.** Restore the four functions as they stood before the
   extraction (`git show <ref>:scripts/ma28_riskcard.py`), exec them in a namespace carrying
   `MA28`'s own constants, and require both routes to agree on the identical frame. `MA5`'s
   inertness pattern -- *"bit-identical over 400 random series, max |delta| 0.000e+00"* -- and
   it isolates the refactor from any data drift, which A alone cannot do: if the panel or the
   flag build had moved since 2026-08-16, A would fail and would not say why.

A LEAF DIFF, NOT A SPOT CHECK, AND THE COUNT IS GATED
------------------------------------------------------
`MB21`'s `C1` first passed VACUOUSLY at a perfect 0.000e+00 by comparing nothing -- an empty
frame, a `None`-skipping loop, and a control that scored perfectly on zero cells. So this walks
every leaf, counts them, and REFUSES below an expected minimum. A control that cannot say how
many things it compared is not a control.

Run:
    python -m scripts.i3_crash_gate_validate
"""
from __future__ import annotations

import io
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"

#: the leaf count below which this control refuses to report a pass (MB21's vacuity lesson).
MIN_LEAVES = 60

#: the commit at which `ma28_riskcard.py` still carried the four functions inline. Resolved at
#: run time from the file's own history so the check keeps working as the tree moves.
PRE_REFACTOR_PROBE = "scripts/ma28_riskcard.py"


def _root(explicit=None):
    """`data/` is gitignored; probe for the FILE, never the directory. DEEPITM-FIN's lesson --
    an empty `data/` in a worktree shadowed a populated one and produced a clean coverage null."""
    cands = [explicit, os.environ.get("VALQUO_DATA_ROOT"), DEFAULT_ROOT]
    here = REPO
    for _ in range(6):
        cands.append(here)
        here = os.path.dirname(here)
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "data", "free_analysis", "panel_r5r6.pkl")):
            return c
    raise SystemExit("[i3] no data root holding data/free_analysis/panel_r5r6.pkl")


def _banked(root):
    """MA28_CARD.json, read-only. It may sit in the worktree rather than the primary root."""
    for base in (REPO, root):
        p = os.path.join(base, "data", "free_analysis", "MA28_CARD.json")
        if os.path.isfile(p):
            with io.open(p, encoding="utf-8") as fh:
                return json.load(fh), p
    raise SystemExit("[i3] MA28_CARD.json not found; the validation target is missing")


def _frame(root):
    """MA28's exact scored frame: its panel, its flags, its crash column."""
    import scripts.ma28_riskcard as MA28
    panel = pickle.load(open(os.path.join(root, "data", "free_analysis", "panel_r5r6.pkl"), "rb"))
    if panel["date"].nunique() != 69:
        raise SystemExit(f"[i3] expected 69 dates, got {panel['date'].nunique()}")
    p = MA28.attach_flags(panel, os.path.join(root, "data", "backtest"))
    return p, MA28


def _leaves(obj, prefix=""):
    """Flatten to (path, value) pairs. Lists are indexed so a reorder cannot pass silently."""
    out = []
    if isinstance(obj, dict):
        for k in sorted(obj.keys()):
            out.extend(_leaves(obj[k], f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(_leaves(v, f"{prefix}[{i}]"))
    else:
        out.append((prefix, obj))
    return out


def _diff(a, b, label_a="library", label_b="banked"):
    la, lb = dict(_leaves(a)), dict(_leaves(b))
    only_a = sorted(set(la) - set(lb))
    only_b = sorted(set(lb) - set(la))
    shared = sorted(set(la) & set(lb))
    worst, worst_at, moved = 0.0, None, []
    for k in shared:
        x, y = la[k], lb[k]
        if isinstance(x, bool) or isinstance(y, bool) or x is None or y is None \
                or isinstance(x, str) or isinstance(y, str):
            if x != y:
                moved.append((k, x, y))
            continue
        d = abs(float(x) - float(y))
        if d > worst:
            worst, worst_at = d, k
        if d > 0:
            moved.append((k, x, y))
    return {"n_shared_leaves": len(shared), f"only_in_{label_a}": only_a,
            f"only_in_{label_b}": only_b, "max_abs_delta": worst, "max_abs_delta_at": worst_at,
            "moved": moved[:20], "n_moved": len(moved)}


def _pre_refactor_source():
    """The last revision of `ma28_riskcard.py` that still defined `permutation_p95` inline."""
    log = subprocess.run(["git", "log", "--format=%H", "--", PRE_REFACTOR_PROBE],
                         cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    for sha in [ln.strip() for ln in log.stdout.splitlines() if ln.strip()]:
        show = subprocess.run(["git", "show", f"{sha}:{PRE_REFACTOR_PROBE}"], cwd=REPO,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        src = show.stdout
        if "rng = np.random.default_rng(seed)" in src and "crash_gate" not in src:
            return sha, src
    return None, None


def _exec_old(src, MA28):
    """Exec the pre-refactor bodies in a namespace carrying MA28's own constants."""
    ns = {"np": np, "pd": pd,
          "MIN_FLAGGED_PER_DATE": MA28.MIN_FLAGGED_PER_DATE,
          "MIN_KEPT_PER_DATE": MA28.MIN_KEPT_PER_DATE,
          "RATIO_FLOOR": MA28.RATIO_FLOOR, "ABS_FLOOR_PP": MA28.ABS_FLOOR_PP,
          "N_PERM": MA28.N_PERM, "PERM_SEED": MA28.PERM_SEED}
    keep, buf, grab = [], [], False
    for line in src.splitlines():
        if line.startswith("def "):
            grab = any(line.startswith(f"def {n}(") for n in
                       ("_nw_t", "per_date_diff", "pooled", "permutation_p95", "window_result"))
            if buf and keep is not None:
                pass
            buf = []
        if grab:
            buf.append(line)
            keep.append(line)
    exec("\n".join(keep), ns)                                        # noqa: S102 -- our own git blob
    return ns


def main():
    root = _root()
    banked, banked_path = _banked(root)
    print(f"[i3] data root      : {root}")
    print(f"[i3] banked artifact: {banked_path}")

    frame, MA28 = _frame(root)
    early, late, boundary = MA28.halves(frame)
    print(f"[i3] frame          : {frame.shape[0]:,} rows, "
          f"{frame['date'].nunique()} dates, boundary {boundary} embargoed")

    from valuation.studies import crash_gate as CG
    cov = CG.coverage(frame["fwd_ret"])
    print(f"[i3] outcome cover  : {cov['rows_with_outcome']:,}/{cov['rows']:,} "
          f"= {cov['coverage']:.6f}  ({cov['rows_without_outcome']:,} rows have NO computable "
          f"fwd_ret and read as 'not crashed')")

    # ---- A: library vs the banked artifact -------------------------------------------
    got = {"full_sample": MA28.window_result(frame, "full_sample"),
           "early_half": MA28.window_result(early, "early_half"),
           "late_half": MA28.window_result(late, "late_half")}
    a = _diff(got, banked["windows"], "library", "banked")
    print(f"\n[i3] A  library vs banked MA28_CARD.json")
    print(f"       leaves compared : {a['n_shared_leaves']}")
    print(f"       max |delta|     : {a['max_abs_delta']:.3e}  at {a['max_abs_delta_at']}")
    print(f"       leaves moved    : {a['n_moved']}")
    print(f"       only in library : {a['only_in_library']}")
    print(f"       only in banked  : {a['only_in_banked']}")
    for k, x, y in a["moved"]:
        print(f"         MOVED {k}: library={x!r} banked={y!r}")

    # ---- B: library vs the pre-refactor source ---------------------------------------
    sha, src = _pre_refactor_source()
    b = None
    if src:
        ns = _exec_old(src, MA28)
        old = {lbl: ns["window_result"](df, lbl) for lbl, df in
               (("full_sample", frame), ("early_half", early), ("late_half", late))}
        b = _diff(got, old, "library", "pre_refactor")
        print(f"\n[i3] B  library vs pre-refactor source @ {sha[:7]}")
        print(f"       leaves compared : {b['n_shared_leaves']}")
        print(f"       max |delta|     : {b['max_abs_delta']:.3e}  at {b['max_abs_delta_at']}")
        print(f"       leaves moved    : {b['n_moved']}")
        print(f"       only in library : {b['only_in_library']}")
        print(f"       only in old     : {b['only_in_pre_refactor']}")
        for k, x, y in b["moved"]:
            print(f"         MOVED {k}: library={x!r} old={y!r}")
    else:
        print("\n[i3] B  SKIPPED -- no pre-refactor revision found (reported, not silent)")

    # ---- the required-n hook, exercised on E-4's own numbers -------------------------
    e4 = CG.required_rows(base_rate=0.0087, ratio=2.0, flagged_share=0.0356, crit=2.0)
    print(f"\n[i3] required-n hook (E-4's clean-subset base rate 0.87%/qtr, ratio 2.0x, "
          f"flagged share 3.56%, crit 2.0, power 0.80)")
    print(f"       rows needed (actual allocation) : {e4['required_rows_total']:,}")
    print(f"       rows needed (equal allocation)  : "
          f"{e4['required_rows_equal_allocation_for_contrast']:,}"
          f"   -> ignoring allocation understates by {e4['allocation_penalty_x']:.2f}x")
    print(f"       expected crashes flagged/kept   : "
          f"{e4['expected_crashes_flagged']:.1f} / {e4['expected_crashes_kept']:.1f}"
          f"   thin={e4['normal_approximation_thin']}")

    ok = (a["max_abs_delta"] == 0.0 and a["n_moved"] == 0
          and not a["only_in_library"] and not a["only_in_banked"]
          and a["n_shared_leaves"] >= MIN_LEAVES
          and (b is None or (b["max_abs_delta"] == 0.0 and b["n_moved"] == 0
                             and b["n_shared_leaves"] >= MIN_LEAVES)))

    out = {"item": "I-3", "validates": "valuation/studies/crash_gate.py",
           "target": "data/free_analysis/MA28_CARD.json",
           "frame": {"rows": int(frame.shape[0]), "dates": int(frame["date"].nunique()),
                     "boundary_embargoed": boundary},
           "outcome_coverage": cov,
           "A_library_vs_banked": a,
           "B_library_vs_pre_refactor": b,
           "B_pre_refactor_commit": sha,
           "min_leaves_required": MIN_LEAVES,
           "required_n_hook_example_E4": e4,
           "all_pass": bool(ok)}
    dest = os.path.join(REPO, "data", "free_analysis", "I3_CRASH_GATE_VALIDATION.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"\n[i3] wrote {dest}")
    print(f"[i3] ALL PASS = {ok}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
