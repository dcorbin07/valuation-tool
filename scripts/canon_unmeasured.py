# -*- coding: utf-8 -*-
"""`CANON-UNMEASURED` — the figures `CANONICAL_MOVE_TABLE.md` left UNMEASURED, measured.

    python -m scripts.canon_unmeasured --what control
    python -m scripts.canon_unmeasured --what deployed      # PBO + Deflated Sharpe, deployed book
    python -m scripts.canon_unmeasured --what inert         # the differential on the panel edit
    python -m scripts.canon_unmeasured --what x1            # the name split
    python -m scripts.canon_unmeasured --what r1cost        # R1's net-of-cost cell
    python -m scripts.canon_unmeasured --what p1s0
    python -m scripts.canon_unmeasured --what v6b

Executes `PREREG_canonmove_unmeasured.md`, committed ALONE at `e4b0dae` before this file existed.

**ZERO TRIALS.** Every item is a RE-MEASUREMENT of an already-registered construction on a
different universe (`S25` / `X7RECON` / `CORRECTED-FLOORS` class). No bar is chosen here; every
threshold is IMPORTED from the register that set it, and a bar that cannot be inherited is
labelled UNCALIBRATED rather than invented.

**EVERY FIGURE IS THE DEPLOYED FLAT-1/7 BOOK** (`DECISIONS.md` 2026-10-07) and says so.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.index_best import _data_root                                   # noqa: E402

#: the corrected panel the whole move was measured on -- the SWEEP's own panel, named in
#: `CORRECTED_DEPLOYED.json`, not a lookalike rebuilt here.
PANEL_BASENAME = "UNIVERSE_BIAS_PANEL_full.pkl"

#: `CORRECTED_DEPLOYED.json`'s own landed deployed figures. Register §0's control: the
#: re-measurement must reproduce the object it is re-measuring, at |dev| 0.000e+00, on a
#: NON-ZERO number of compared cells (`MB21`'s C1 scored a perfect zero on an empty frame).
DEPLOYED_LANDED = {
    "top_decile_alpha": 0.060674434603777944,
    "long_short_tstat_nw": 4.594456679049444,
    "monotonicity": -0.9636363636363636,
}

#: THE PUBLISHED RUN'S OWN `cpcv.deflated_sharpe_detail`, read off the pre-swap tracked artifact
#: (`git show 60871ac^:BACKTEST_RESULTS.json`) and committed as a literal so the `N`-separation
#: control does not depend on a file the artifact swap has already replaced. Its own `adopt` was
#: **False** and `recommend` was `current-default`, which is what makes it the DEPLOYED book.
PUBLISHED_DSR_DETAIL = {
    "probability": 0.7863213339664521,
    "sharpe_per_period": 0.5500328707621251,
    "sr0_benchmark": 0.4604580339477429,
    "n_trials": 224,
    "var_sr_across_trials": 0.026997967906897496,
    "n_periods": 69,
}


def fa():
    """`data/free_analysis`, resolved on CALL — a worktree carries `data/` EMPTY and the banked
    panel lives in the primary root (`E-5`'s wrong-object family, and `S3-I1`'s own repeat of
    it: an artifact written by a worktree-run script does not survive the worktree)."""
    return os.path.join(_data_root(), "free_analysis")


def panel_path():
    return os.path.join(fa(), PANEL_BASENAME)


def out_path(what):
    return os.path.join(fa(), "CANON_UNMEASURED_%s.json" % what.upper())


def log(m):
    print(m, flush=True)


def write(path, obj):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=1, default=float))
    log("wrote %s" % path)


def load_panel():
    import pandas as pd
    p = panel_path()
    if not os.path.exists(p):
        raise SystemExit("REFUSING: the corrected panel is not on disk at %s" % p)
    return pd.read_pickle(p)


def deployed_cols_and_weights(panel):
    """The DEPLOYED book: `_base_weights` over the established bucket, CPCV never consulted.
    IMPORTED rather than retyped, so the weight vector cannot drift from the shipped one."""
    from valuation.edge import fundamental_panel as FP
    from valuation.screener import settings as S
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    return cols, FP._base_weights(cols, "established")


# ---------------------------------------------------------------------------------------------
# REGISTER §0 — the weighting control. Every other figure is VOID without it.
# ---------------------------------------------------------------------------------------------
def control(panel=None):
    from valuation.edge import fundamental_panel as FP
    panel = load_panel() if panel is None else panel
    cols, base = deployed_cols_and_weights(panel)
    qb = FP.quantile_backtest(panel, cols, base, n_q=10, horizon=63) or {}
    cells, devs = [], []
    for k, want in DEPLOYED_LANDED.items():
        got = qb.get(k)
        if got is None:
            continue
        cells.append(k)
        devs.append(abs(float(got) - float(want)))
    return {
        "panel": panel_path(),
        "n_dates": int(panel["date"].nunique()),
        "n_names": int(panel["ticker"].nunique()),
        "weighting": "DEPLOYED flat 1/7 (low_risk at 0.0)",
        "nonzero_themes": sorted(k for k, v in base.items() if v),
        "weights": {k: float(v) for k, v in base.items()},
        "cells_compared": len(cells),
        "cells": cells,
        "measured": {k: (None if qb.get(k) is None else float(qb[k])) for k in DEPLOYED_LANDED},
        "landed": DEPLOYED_LANDED,
        "max_abs_dev": (max(devs) if devs else None),
        # GATED on the COUNT as well as the deviation: a perfect zero over zero cells is the
        # vacuous pass this record has hit six times.
        "ok": bool(len(cells) == len(DEPLOYED_LANDED) and devs and max(devs) == 0.0),
    }


# ---------------------------------------------------------------------------------------------
# REGISTER §1 — the DEPLOYED book's PBO and Deflated Sharpe
# ---------------------------------------------------------------------------------------------
def _subnull(sweep, adopting, keys):
    """Percentiles over the retained draws that DID or did NOT adopt. No re-sweep: rule 9 kept
    all 100, so splitting them is arithmetic. `CORRECTED-FLOORS` part 1b's matched null, and its
    own rule travels with it -- the count is reported, because a p95 over a thin split is set by
    its largest one or two values."""
    rows = [d for d in sweep["draws"] if bool(d.get("cpcv_adopt")) == adopting]
    out = {"n": len(rows), "adopting": adopting}
    for key, pct in keys:
        vals = [d.get(key) for d in rows]
        vals = [float(v) for v in vals if v is not None and v == v]
        out[key] = (float(np.percentile(vals, 5 if pct == "p05" else 95))
                    if len(vals) >= 2 else None)
        out[key + "_n"] = len(vals)
    return out


def _dsr_at_N(detail, n_new):
    """The SAME Deflated Sharpe at a DIFFERENT trial count, from banked numbers only.

    `N` enters only through `sr0`, so moving it is arithmetic on what `_deflated_sharpe_detail`
    already banks — no re-run, and no skew/kurtosis needed: the non-normality correction is
    recovered by INVERTING the banked probability. This is what separates "the universe moved"
    from "the denominator moved", which is `MA19`'s own recurring defect in reverse.
    """
    from valuation.edge.fundamental_panel import _ncdf, _nppf
    sr, sr0, n = detail["sharpe_per_period"], detail["sr0_benchmark"], detail["n_periods"]
    var_sr, prob = detail["var_sr_across_trials"], detail["probability"]
    z = _nppf(prob)
    if z == 0 or sr == sr0:
        return None
    denom = ((sr - sr0) * ((n - 1) ** 0.5) / z) ** 2
    emc = 0.5772156649015329
    import math
    sr0n = (var_sr ** 0.5) * ((1 - emc) * _nppf(1 - 1.0 / n_new)
                              + emc * _nppf(1 - 1.0 / (n_new * math.e)))
    return {"n_trials": int(n_new), "sr0_benchmark": float(sr0n),
            "probability": float(_ncdf((sr - sr0n) * ((n - 1) ** 0.5) / (denom ** 0.5))),
            "recovered_nonnormality_denom": float(denom)}


def deployed(panel=None):
    from valuation.edge import fundamental_panel as FP
    from valuation.edge import research_log as RL
    import scripts.corrected_floors as CF

    panel = load_panel() if panel is None else panel
    ctl = control(panel)
    log("[control] cells %d  max|dev| %r  ok=%s"
        % (ctl["cells_compared"], ctl["max_abs_dev"], ctl["ok"]))
    if not ctl["ok"]:
        return {"item": "CANON-UNMEASURED", "part": "1 -- deployed PBO and Deflated Sharpe",
                "ABORTED": "register §0's weighting control failed; every figure would be VOID",
                "control": ctl}

    cols, base = deployed_cols_and_weights(panel)
    n_live = RL.detail().get("by_domain", {}).get("equity")
    log("[deployed] running cpcv_validate(deployed_readings=True) -- this takes ~70s")
    r = FP.cpcv_validate(panel, cols, base, deployed_readings=True)
    dep = r.get("deployed_readings") or {}

    sweep = CF.read_sweep()
    keys = (("pbo", "p05"), ("deflated_sharpe", "p95"))
    full = {k: (sweep["null"].get(k) or {}).get(p) for k, p in keys}
    non = _subnull(sweep, False, keys)
    yes = _subnull(sweep, True, keys)

    dsr_dep = dep.get("deflated_sharpe")
    dsr_floor = non.get("deflated_sharpe")
    pbo_sel = r.get("pbo")
    pbo_dep = dep.get("pbo_no_selection")

    rows = [
        {
            "statistic": "Deflated Sharpe -- DEPLOYED book (flat 1/7)",
            "book": "DEPLOYED",
            "published": 0.7863213339664521,
            "published_N": 224,
            "published_book": "DEPLOYED (cpcv.adopt was false on the published run)",
            "corrected": dsr_dep,
            "corrected_N": n_live,
            "conventional_bar": 0.95,
            "clears_conventional": (None if dsr_dep is None else bool(dsr_dep > 0.95)),
            "calibrated_floor": dsr_floor,
            "calibrated_floor_is": ("p95 of the %d NON-ADOPTING retained draws -- the MATCHED "
                                    "null for a book that does not adopt (`MB8`: an se may not "
                                    "be borrowed across constructions)" % non["n"]),
            "clears_calibrated_floor": (None if (dsr_dep is None or dsr_floor is None)
                                        else bool(dsr_dep > dsr_floor)),
            "floor_full_null": full.get("deflated_sharpe"),
            "floor_adopting_null": yes.get("deflated_sharpe"),
            "adopted_book_for_comparison": dep.get("adopted_deflated_sharpe_for_comparison"),
            "adopted_scheme": dep.get("adopted_scheme_for_comparison"),
            "detail": dep.get("deflated_sharpe_detail"),
            # THE PUBLISHED RUN'S OWN `cpcv.adopt` WAS FALSE AND ITS `recommend` WAS
            # `current-default`, so the published 0.7863 IS the deployed book: this comparison is
            # like-for-like on the BOOK. It is NOT like-for-like on `N` (224 against 297), and
            # since `N` is an input the two effects are separated rather than pooled.
            "published_was_the_deployed_book": True,
            "at_a_COMMON_N": {
                "published_detail_at_corrected_N": _dsr_at_N(PUBLISHED_DSR_DETAIL, n_live),
                "corrected_detail_at_published_N": _dsr_at_N(
                    dep.get("deflated_sharpe_detail") or {}, 224),
            },
        },
        {
            "statistic": "PBO -- the SELECTION step (Bailey-Lopez de Prado), unchanged",
            "book": "NEITHER -- it scores the selection over the eight candidates",
            "published": 0.7333333333333333,
            "corrected": pbo_sel,
            "conventional_bar": 0.50,
            "clears_conventional": (None if pbo_sel is None else bool(pbo_sel < 0.50)),
            "calibrated_floor": full.get("pbo"),
            "calibrated_floor_is": "p05 of all 100 retained draws (`pbo` is X7's only low tail)",
            "clears_calibrated_floor": (None if (pbo_sel is None or full.get("pbo") is None)
                                        else bool(pbo_sel < full["pbo"])),
            "THE_PRECISION_CORRECTION": (
                "`_pbo` never reads `adopt` or `recommend`, so this figure is the SAME number "
                "whether or not adoption happened. `CANONICAL_MOVE_TABLE.md` §0 point 2 calls it "
                "'the ADOPTED book's PBO'; it is the selection step's PBO, and the deployed book "
                "makes no selection, so BLdP's PBO is not a statistic about it in EITHER "
                "direction. Declared in the register before the run."),
            "x7_measured_the_bar_has_no_power": (
                "X7 measured pure noise at a MEDIAN PBO of 46.7%, so '<0.50' sits at the noise "
                "level; it is cited as neither a pass nor a fail."),
        },
        {
            "statistic": "PBO_NO_SELECTION -- the DEPLOYED-book analogue (NEW statistic)",
            "book": "DEPLOYED",
            "published": None,
            "published_why": "never computed on any universe; the statistic did not exist",
            "corrected": pbo_dep,
            "conventional_bar": 0.50,
            "clears_conventional": (None if pbo_dep is None else bool(pbo_dep < 0.50)),
            "calibrated_floor": None,
            "calibrated_floor_is": "NONE -- UNCALIBRATED, see the register §1.3",
            "clears_calibrated_floor": None,
            "construction": ("`_pbo(..., fixed='current-default')`: the same rank arithmetic with "
                             "the in-sample argmax replaced by the FIXED deployed scheme"),
            "deployed_median_oos_rank": dep.get("deployed_median_oos_rank"),
            "deployed_oos_rank_per_path": dep.get("deployed_oos_rank_per_path"),
            "deployed_median_oos_ic": dep.get("deployed_median_oos_ic"),
            "n_paths": r.get("n_paths"),
            # NON-VACUITY, and it is the reading that decides what this number means.
            "per_scheme": dep.get("pbo_no_selection_per_scheme"),
            "WHAT_IT_DOES_NOT_MEAN": (
                "NOT 'the deployed book is certainly overfit'. Read through BLdP's logit rule a "
                "value of 1.0 means only 'this scheme sat at or below the OOS median of the "
                "eight on every path' -- i.e. there are better-ranking alternatives out of "
                "sample. For a book chosen by SELECTION that is evidence of selection optimism; "
                "for a book that selects NOTHING it is a RANK fact and carries no overfitting "
                "claim in either direction. The per-scheme column is the proof: the number is "
                "simply each candidate's OOS rank, low for the good ones and high for the bad."),
        },
    ]
    return {
        "item": "CANON-UNMEASURED",
        "part": "1 -- the DEPLOYED book's PBO and Deflated Sharpe",
        "register": "PREREG_canonmove_unmeasured.md (committed ALONE at e4b0dae)",
        "trials": 0,
        "trial_class": ("RE-MEASUREMENT of an already-registered construction on a different "
                        "universe. No hypothesis, no bar chosen here, no arm."),
        "weighting": "DEPLOYED flat 1/7 on every row",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "control": ctl,
        "equity_N_at_measurement": n_live,
        "N_IS_AN_INPUT": ("`sr0` is a function of `_trial_N()`, which reads RESEARCH_LOG.md at "
                          "run time, so the Deflated Sharpe moves at EVERY N. The landed "
                          "corrected ADOPTED reading (0.001561) was taken at equity N = 285. "
                          "Both sides of any DSR comparison must name their N (`MA19`)."),
        "cpcv": {k: r.get(k) for k in ("n_paths", "pbo", "deflated_sharpe", "adopt",
                                       "recommend", "verdict", "pbo_scope")},
        "candidates_median_oos_ic": {k: (v or {}).get("median_oos_ic")
                                     for k, v in (r.get("candidates") or {}).items()},
        "matched_nulls": {"full_null_n": sweep["n_draws"], "non_adopting": non, "adopting": yes},
        "rows": rows,
    }


# ---------------------------------------------------------------------------------------------
# THE INERTNESS DIFFERENTIAL on the `fundamental_panel.py` edit
# ---------------------------------------------------------------------------------------------
_PROBE = r'''
import json, os, sys
sys.path.insert(0, %(here)r)
import pandas as pd
from valuation.edge import fundamental_panel as FP
from valuation.screener import settings as S
panel = pd.read_pickle(%(panel)r)
cols = [c for c in S.BUCKET_FACTORS["established"]
        if c in panel.columns and panel[c].notna().any()]
base = FP._base_weights(cols, "established")
r = FP.cpcv_validate(panel, cols, base)
print("___JSON___" + json.dumps(r, default=float))
'''


def _run_probe(tag):
    """`cpcv_validate` at its DEFAULTS, in a subprocess, so the two sources are two processes."""
    src = _PROBE % {"here": _HERE, "panel": panel_path()}
    tmp = os.path.join(os.environ.get("TEMP", "."), "canon_probe_%s.py" % tag)
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src)
    p = subprocess.run([sys.executable, tmp], capture_output=True, text=True)
    os.remove(tmp)
    for line in (p.stdout or "").splitlines():
        if line.startswith("___JSON___"):
            return json.loads(line[len("___JSON___"):])
    raise SystemExit("probe %s produced no JSON:\n%s\n%s" % (tag, p.stdout[-3000:],
                                                             p.stderr[-3000:]))


def _leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            for x in _leaves(v, p + "." + str(k)):
                yield x
    elif isinstance(o, list):
        for i, v in enumerate(o):
            for x in _leaves(v, p + "[%d]" % i):
                yield x
    else:
        yield p, o


def inert():
    """Restore `HEAD`'s `fundamental_panel.py`, run the probe, restore the edited bytes, run it
    again, diff leaf by leaf.

    **BINARY I/O, AND THE RESTORE IS CHECKED BYTE-FOR-BYTE.** `W-1`'s mutation harness read and
    wrote TEXT with `newline` forced to LF, so restoring a CRLF source REWROTE it and the harness
    failed its own byte-for-byte check AFTER the mutation had run. A harness that cannot put a
    file back is worse than none, because it leaves the tree altered in exactly the file it was
    aimed at.
    """
    rel = os.path.join("valuation", "edge", "fundamental_panel.py")
    tgt = os.path.join(_HERE, rel)
    with io.open(tgt, "rb") as fh:
        edited = fh.read()
    head = subprocess.run(["git", "-C", _HERE, "show", "HEAD:" + rel.replace("\\", "/")],
                          capture_output=True)
    if head.returncode != 0:
        raise SystemExit("cannot read HEAD's source: %s" % head.stderr[-500:])
    baseline_bytes = head.stdout
    try:
        with io.open(tgt, "wb") as fh:
            fh.write(baseline_bytes)
        log("[inert] probing HEAD's source")
        before = _run_probe("head")
    finally:
        with io.open(tgt, "wb") as fh:
            fh.write(edited)
    with io.open(tgt, "rb") as fh:
        restored = fh.read()
    if restored != edited:
        raise SystemExit("REFUSING: the source was NOT restored byte-for-byte")
    log("[inert] source restored byte-for-byte (%d bytes)" % len(restored))
    log("[inert] probing the EDITED source")
    after = _run_probe("edited")

    lb, la = dict(_leaves(before)), dict(_leaves(after))
    moved = sorted(k for k in set(lb) & set(la) if lb[k] != la[k])
    return {
        "item": "CANON-UNMEASURED",
        "part": "the inertness differential on the fundamental_panel.py edit",
        "what_changed": ["_pbo gained an optional `fixed=` argument (default None)",
                         "cpcv_validate gained `deployed_readings=False` and adds NO KEY when off"],
        "restored_byte_for_byte": True,
        # A DEFECT IN MY OWN REPORTING, CAUGHT BY DISBELIEVING A NUMBER. The raw byte counts are
        # 310,463 and 320,543, a 10,080 difference that reads as a 10 KB edit -- and 10,080 is
        # almost exactly the CRLF count, because `git show` emits LF while the working copy is
        # CRLF. Comparing two sizes in two encodings is the wrong-object family, so both are
        # reported NORMALISED and the raw pair is kept beside them.
        "head_bytes_lf": len(baseline_bytes.replace(b"\r\n", b"\n")),
        "edited_bytes_lf": len(edited.replace(b"\r\n", b"\n")),
        "edit_bytes_added_lf": (len(edited.replace(b"\r\n", b"\n"))
                                - len(baseline_bytes.replace(b"\r\n", b"\n"))),
        "edit_lines_added": (edited.replace(b"\r\n", b"\n").count(b"\n")
                             - baseline_bytes.replace(b"\r\n", b"\n").count(b"\n")),
        "head_bytes_raw": len(baseline_bytes),
        "edited_bytes_raw": len(edited),
        "raw_sizes_are_in_DIFFERENT_encodings": "git show emits LF; the working copy is CRLF",
        "n_leaves_before": len(lb),
        "n_leaves_after": len(la),
        "keys_added": sorted(set(la) - set(lb)),
        "keys_removed": sorted(set(lb) - set(la)),
        "leaves_moved": moved,
        "top_level_keys_identical": sorted(before.keys()) == sorted(after.keys()),
        # GATED on the count: a zero-difference over zero leaves is the vacuous pass.
        "ok": bool(len(lb) > 50 and not moved and not (set(la) ^ set(lb))),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="control",
                    choices=["control", "deployed", "inert", "x1", "r1cost", "p1s0", "v6b"])
    args = ap.parse_args(argv)
    if args.what == "control":
        res = control()
        log(json.dumps(res, indent=1, default=float))
    elif args.what == "deployed":
        res = deployed()
    elif args.what == "inert":
        res = inert()
        log(json.dumps({k: v for k, v in res.items() if k != "leaves_moved"},
                       indent=1, default=float))
    else:
        raise SystemExit("--what %s is implemented in its own module pass" % args.what)
    write(out_path(args.what), res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
