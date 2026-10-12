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


# ---------------------------------------------------------------------------------------------
# REGISTER §2 — `X1`, the name split, on the corrected universe
# ---------------------------------------------------------------------------------------------
def x1(panel=None):
    """`X1` re-run on the corrected universe. **Every constant and every rule is IMPORTED from
    `scripts/r4_x1_accounting_universe.py`, not retyped** (`MA5`): `THEMES`, `W`, `K_SPLITS`,
    `J_NULL`, `SEED`, `MIN_NAMES_PER_HALF`, `FRAC_HALFBOOKS`, `FRAC_BOTH`, `stable_key_half`,
    `_score`, `_assert_split`, `half_universe_null` and the verdict rule `verdict_of`.

    **ONE CONTROL IS RE-POINTED AND IT WAS DECLARED BEFORE THE RUN** (register §2). That script's
    `C1` gates on the PUBLISHED headline literals and aborts otherwise; on the corrected panel
    those cannot reproduce by construction, so as written the gate would abort the item for doing
    exactly what it was asked to do. It is re-pointed to the CORRECTED deployed literals, which
    is the property it stood in for.
    """
    import numpy as _np
    import pandas as pd
    from scripts import r4_x1_accounting_universe as X

    panel = load_panel() if panel is None else panel
    ctl = control(panel)
    log("[control] cells %d  max|dev| %r  ok=%s"
        % (ctl["cells_compared"], ctl["max_abs_dev"], ctl["ok"]))

    n_d, n_t = int(panel["date"].nunique()), int(panel["ticker"].nunique())
    out = {
        "item": "CANON-UNMEASURED",
        "part": "2 -- X1, the name split, on the corrected universe",
        "register": "PREREG_canonmove_unmeasured.md (ALONE at e4b0dae); construction and bars "
                    "from PREREG_r4_x1_accounting_and_universe_split.md, imported not retyped",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT of an already-registered construction on a new universe",
        "weighting": "DEPLOYED flat 1/7 -- X1's own W=0.125 over seven themes, which is the "
                     "SAME book: composite_from_frame renormalises by the present-weight mass, "
                     "so a uniform scaling of every weight cannot move a ranking. Verified "
                     "rather than argued: the X1 construction reproduces the corrected DEPLOYED "
                     "literals at |dev| 0.000e+00 (see control_C1).",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "constants_imported": {
            "K_SPLITS": X.K_SPLITS, "J_NULL": X.J_NULL, "SEED": X.SEED, "W": X.W,
            "THEMES": list(X.THEMES), "MIN_NAMES_PER_HALF": X.MIN_NAMES_PER_HALF,
            "FRAC_HALFBOOKS": X.FRAC_HALFBOOKS, "FRAC_BOTH": X.FRAC_BOTH,
        },
        "controls": {},
    }

    out["controls"]["C0_canonical_panel"] = {
        "n_dates": n_d, "n_names": n_t, "ok": bool(n_d >= 60 and n_t >= 9000),
        "re_pointed": "the original asked for n_names >= 2400 on the published panel; the shape "
                      "gate is re-pointed to the corrected panel's own shape",
    }
    out["controls"]["C1_corrected_deployed_headline_reproduces"] = ctl
    if not (ctl["ok"] and out["controls"]["C0_canonical_panel"]["ok"]):
        out["ABORTED"] = "C0/C1 failed -- every split result would be VOID (register 6.5)"
        return out

    universe = sorted(panel["ticker"].unique())
    rng = _np.random.default_rng(X.SEED)

    ka = [t for t in universe if X.stable_key_half(t) == 0]
    kb = [t for t in universe if X.stable_key_half(t) == 1]
    ka2 = [t for t in reversed(universe) if X.stable_key_half(t) == 0]
    # A HASH PARTITION IS BALANCED ONLY IN EXPECTATION, so its tolerance is DERIVED from the
    # sampling distribution rather than chosen: the imbalance is binomial with sd sqrt(n), and
    # 2*sqrt(n) is 4 sd (P < 1e-4). See `_assert_split`'s docstring -- this is the property C2
    # was standing in for, and asserting |imbalance| <= 1 passed on the published universe with
    # probability 0.0317.
    imb = abs(len(ka) - len(kb))
    sd_imb = float(len(universe) ** 0.5)
    tol = int(round(2.0 * len(universe) ** 0.5))
    out["controls"]["C3_stable_key_deterministic"] = {
        "n_a": len(ka), "n_b": len(kb),
        "order_independent": bool(set(ka) == set(ka2)),
        "construction": "int(sha1(ticker).hexdigest(), 16) % 2",
        "imbalance": imb,
        "imbalance_sd_under_a_fair_hash": sd_imb,
        "imbalance_z": (imb / sd_imb if sd_imb else None),
        "balance_tolerance_DERIVED_4sd": tol,
        "balanced_within_derived_tolerance": bool(imb <= tol),
        "published_universe_passed_the_old_bar_with_probability": 0.0317,
        "THE_OLD_BAR_WAS_WRONG_FOR_THIS_SPLIT": (
            "X1's C2 asserted |imbalance| <= 1 on BOTH the random splits (balanced by "
            "construction, where 1 is right and is kept) and the HASH split (balanced only in "
            "expectation). On 2,531 names it read 1266/1265 and cleared with ~3% probability; on "
            "9,645 it reads 4798/4847 at z = 0.50 and FIRED on a correct split."),
        "min_names_per_half_bar": X.MIN_NAMES_PER_HALF,
        "bar_binds": bool(min(len(ka), len(kb)) < X.MIN_NAMES_PER_HALF),
    }
    log("[C3] stable key: %d / %d  (imbalance %d, z %.2f, derived tol %d)"
        % (len(ka), len(kb), imb, imb / sd_imb, tol))

    log("[X1] scoring the stable-key split")
    sa, sb = X._score(panel, set(ka)), X._score(panel, set(kb))
    X._assert_split(ka, kb, universe, balance_tol=tol)
    ra = panel[panel["ticker"].isin(set(ka))][["date", "ticker"]]
    rb = panel[panel["ticker"].isin(set(kb))][["date", "ticker"]]
    shared = len(pd.merge(ra, rb, on=["date", "ticker"], how="inner"))
    out["controls"]["C6_halves_share_zero_keys"] = {"shared_keys": int(shared),
                                                    "ok": bool(shared == 0)}
    out["stable_key_split"] = {"half_A": sa, "half_B": sb}
    log("[X1] A alpha %+.5f ls_hac %+.4f | B alpha %+.5f ls_hac %+.4f"
        % (sa["top_decile_alpha"], sa["long_short_tstat_nw"],
           sb["top_decile_alpha"], sb["long_short_tstat_nw"]))

    log("[X1] calibrating the HALF-UNIVERSE null, %d draws" % X.J_NULL)
    null = X.half_universe_null(panel, universe, rng, X.J_NULL)
    out["half_universe_null"] = null
    log("[X1] null: alpha p95 %+.5f  ls_hac p95 %+.4f"
        % (null["alpha_p95"], null["ls_hac_p95"]))

    log("[X1] %d random splits" % X.K_SPLITS)
    splits = []
    uni = _np.array(universe)
    for i in range(X.K_SPLITS):
        idx = rng.permutation(len(uni))
        a = set(uni[idx[: len(uni) // 2]])
        b = set(uni) - a
        X._assert_split(a, b, universe)
        ra_, rb_ = X._score(panel, a), X._score(panel, b)
        if ra_ and rb_:
            splits.append({"A": ra_, "B": rb_})
        if (i + 1) % 10 == 0:
            log("    split %d/%d" % (i + 1, X.K_SPLITS))
    out["n_splits_scored"] = len(splits)

    for arm, key, p95, p05 in (("A1_top_decile_alpha", "top_decile_alpha",
                                null["alpha_p95"], null["alpha_p05"]),
                               ("A2_long_short_hac_t", "long_short_tstat_nw",
                                null["ls_hac_p95"], null["ls_hac_p05"])):
        halves = [h[k][key] for h in splits for k in ("A", "B")]
        clears = [v > p95 for v in halves]
        both = [(h["A"][key] > p95 and h["B"][key] > p95) for h in splits]
        neg_both = [(h["A"][key] < p05 and h["B"][key] < p05) for h in splits]
        prim = (sa[key] > p95 and sb[key] > p95 and sa[key] > 0 and sb[key] > 0)
        f_h = float(_np.mean(clears)) if clears else 0.0
        f_b = float(_np.mean(both)) if both else 0.0
        f_n = float(_np.mean(neg_both)) if neg_both else 0.0
        out[arm] = {
            "bar_p95_half_universe": p95,
            "primary_stable_key_A": sa[key], "primary_stable_key_B": sb[key],
            "primary_both_clear": bool(prim),
            "n_half_books": len(halves),
            "frac_half_books_clearing": f_h,
            "frac_splits_both_clear": f_b,
            "frac_splits_both_negative": f_n,
            "half_book_median": float(_np.median(halves)) if halves else None,
            "half_book_min": float(_np.min(halves)) if halves else None,
            "half_book_max": float(_np.max(halves)) if halves else None,
            "n_half_books_negative": int(sum(1 for v in halves if v < 0)),
            "corrected_full_universe_value": DEPLOYED_LANDED.get(key),
            "published_full_universe_value": X.REC.get(key),
            "published_verdict": "SURVIVES (both arms, on the published universe)",
            "half_book_values": [round(v, 8) for v in halves],
            # the VERDICT RULE IS IMPORTED so it lives in one place
            "verdict": X.verdict_of(prim, f_h, f_b, f_n),
        }
        log("[%s] %s  primary_both %s  frac_halves %.3f  frac_both %.3f  median %+.5f  neg %d"
            % (arm, out[arm]["verdict"], prim, f_h, f_b,
               out[arm]["half_book_median"], out[arm]["n_half_books_negative"]))

    out["controls"]["C4_coverage"] = {
        "half_names_median": float(_np.median([h["A"]["n_names"] for h in splits])),
        "half_rows_median": float(_np.median([h["A"]["n_rows"] for h in splits])),
        "implied_decile_size": float(_np.median([h["A"]["n_rows"] for h in splits])) / n_d / 10.0,
        "full_universe_decile_size": float(len(panel)) / n_d / 10.0,
    }
    out["controls"]["C5_x7_floors_are_EXTRAPOLATIONS_here"] = {
        "x7_published_full_universe_ls_hac_floor": X.X7_FULL_UNIVERSE_LS_HAC_FLOOR,
        "x7_published_full_universe_alpha_margin": X.X7_FULL_UNIVERSE_ALPHA_MARGIN,
        "why": ("reported BESIDE the half-universe null and never AS it (register 2.2 C5). On "
                "this universe they are an extrapolation TWICE over: a different universe and a "
                "half book. The verdicts above use the half-universe null only."),
    }
    out["what_a_pass_does_not_license"] = (
        "X1 tests generalisation across NAMES, not decision leakage -- the deployed strategy "
        "fits nothing, so there is no decision to leak. Re-running every theme decision and the "
        "weight selection under the split is NOT done.")
    return out


# ---------------------------------------------------------------------------------------------
# REGISTER §3 — `R1`'s net-of-cost factor-alpha cell
# ---------------------------------------------------------------------------------------------
#: `CORRECTED_R1_FACTOR_ALPHA.json`'s own landed GROSS intercept. Register §3.3's control: the
#: net reading is VOID unless the gross leg reproduces, because otherwise it is a different
#: regression wearing the same name.
R1_LANDED_GROSS = {"alpha_ann": 0.059397599064971024, "alpha_t_nw": 4.453158903833538}


def _two_way_series(panel, weights, top_frac=0.1):
    """A LABELLED SENSITIVITY, not R1's registered formula.

    `etf_benchmark.strategy_series` sets `turnover` to the fraction of the decile that is NEW,
    and `factor_alpha` then charges `(cost_bps/1e4) * turnover` -- so the **buy leg only**.
    `fundamental_panel.turnover_and_costs` charges `(bps/1e4) * (n_bought + n_sold)/len(held)`,
    i.e. **both legs**. R1's leg therefore undercharges by about a factor of two relative to this
    project's own cost model. **R1's formula is run as written** (`RUN_RULES` rule 3: report, do
    not quietly re-point another register's instrument); this series exists so the direction of
    that discrepancy is BOUNDED rather than asserted.

    Both counts are emitted, and the bps is the entering-name mean `one_way_cost_bps`, which is
    `strategy_series`'s own definition -- the only thing that changes is the turnover column.
    """
    import pandas as pd
    from valuation.edge.fundamental_panel import composite as _composite, one_way_cost_bps
    from valuation.screener.cross_sectional import zscore
    cols = list(weights)
    wv = np.array([float(weights[c]) for c in cols], dtype=float)
    rows, prev = [], set()
    for d, sub in panel.groupby("date"):
        comp = _composite(np.column_stack([zscore(sub[c]).values for c in cols]), wv)
        ok = np.isfinite(comp) & np.isfinite(sub["fwd_ret"].values)
        s = sub[ok].assign(_c=comp[ok]).sort_values("_c", ascending=False)
        if len(s) < 30:
            continue
        k = max(1, int(len(s) * top_frac))
        top = s.head(k)
        held = set(top["ticker"])
        enter, leave = held - prev, prev - held
        bps = (np.mean([one_way_cost_bps(v) for v in
                        top.loc[top["ticker"].isin(enter), "market_cap"]]) if enter else 0.0)
        rows.append({"date": d, "top": float(top["fwd_ret"].mean()),
                     "ew": float(s["fwd_ret"].mean()),
                     "turnover": (len(enter) + len(leave)) / max(1, k),
                     "n_enter": len(enter), "n_leave": len(leave),
                     "cost_bps": float(bps) if bps == bps else 0.0, "n": int(k)})
        prev = held
    return pd.DataFrame(rows)


def _legacy_inline(panel, weights, top_frac=0.1):
    """HEAD's `strategy_series` loop, copied VERBATIM, purely as the differential for the
    `legacy_composite=True` default. If the parameterised function's legacy branch is not
    bit-identical to this, the default is not inert and R1's landed series would move."""
    import pandas as pd
    from valuation.edge.fundamental_panel import one_way_cost_bps
    from valuation.screener.cross_sectional import zscore
    rows, prev = [], set()
    for d, sub in panel.groupby("date"):
        comp = np.zeros(len(sub))
        for c, w in weights.items():
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * w
        ok = np.isfinite(comp) & np.isfinite(sub["fwd_ret"].values)
        s = sub[ok].assign(_c=comp[ok]).sort_values("_c", ascending=False)
        if len(s) < 30:
            continue
        k = max(1, int(len(s) * top_frac))
        top = s.head(k)
        held = set(top["ticker"])
        traded = held - prev
        bps = np.mean([one_way_cost_bps(v) for v in
                       top.loc[top["ticker"].isin(traded), "market_cap"]]) if traded else 0.0
        rows.append({"date": d, "top": float(top["fwd_ret"].mean()),
                     "ew": float(s["fwd_ret"].mean()),
                     "turnover": len(traded) / max(1, k),
                     "cost_bps": float(bps) if bps == bps else 0.0, "n": int(k)})
        prev = held
    return pd.DataFrame(rows)


def _run_factor_alpha(series_csv, out_json, tag):
    cmd = [sys.executable, "-m", "scripts.factor_alpha", "--corrected-panel",
           "--panel", panel_path(), "--strategy-series", series_csv,
           # `factors/PARSED` -- `set_factor_dir` appends `ff5_daily.csv` etc, which live one
           # level down from `factors/`. Pointing at the parent raises FileNotFoundError rather
           # than returning an empty frame, which is the safe direction.
           "--factors-dir", os.path.join(_data_root(), "factors", "parsed"),
           "--json", out_json]
    log("[r1cost] %s: %s" % (tag, " ".join(cmd[2:])))
    p = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True)
    logp = os.path.join(fa(), "CANON_UNMEASURED_R1COST_%s.log" % tag)
    with io.open(logp, "w", encoding="utf-8", errors="replace") as fh:
        fh.write((p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""))
    if p.returncode != 0:
        log("[r1cost] %s FAILED rc=%s; tail:\n%s" % (tag, p.returncode, (p.stderr or "")[-2000:]))
        return None
    with io.open(out_json, encoding="utf-8") as fh:
        return json.load(fh)


def r1cost(panel=None):
    import pandas as pd
    from scripts import etf_benchmark as EB
    from valuation.screener import settings as S

    panel = load_panel() if panel is None else panel
    ctl = control(panel)
    log("[control] cells %d  max|dev| %r  ok=%s"
        % (ctl["cells_compared"], ctl["max_abs_dev"], ctl["ok"]))

    # `factor_alpha` uses the non-zero `WEIGHTS_ESTABLISHED` entries, so the cost series is
    # built on the SAME weight vector the return series is -- IMPORTED, not retyped.
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}

    out = {
        "item": "CANON-UNMEASURED",
        "part": "3 -- R1's net-of-cost factor-alpha cell",
        "register": "PREREG_canonmove_unmeasured.md (ALONE at e4b0dae); the BAR is HANDOFF_r1.md "
                    "section 1 verbatim: FF5+MOM intercept positive with Newey-West t > 2.0",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT; R1's arithmetic is NOT changed, only its INPUT grid",
        "weighting": "DEPLOYED -- factor_alpha's own non-zero WEIGHTS_ESTABLISHED entries",
        "weights": {k: float(v) for k, v in dep.items()},
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "control_weighting": ctl,
        "diagnosis": {},
        "controls": {},
    }

    # ---- the diagnosis, MEASURED ----
    shp = pd.read_csv(os.path.join(fa(), "ETF_BENCHMARK_RESULTS_strategy_series.csv"),
                      parse_dates=["date"])
    corr_dates = set(pd.to_datetime(panel["date"].unique()))
    pub_panel = os.path.join(fa(), "panel_corrected_69d.pkl")
    pub_dates = set()
    if os.path.exists(pub_panel):
        pub_dates = set(pd.to_datetime(pd.read_pickle(pub_panel)["date"].unique()))
    out["diagnosis"] = {
        "cause": ("factor_alpha's net_of_cost LEFT-joins X4's shipped strategy-series turnover "
                  "and cost_bps; that CSV is indexed on X4's own grid, so a zero-date overlap "
                  "makes `cost` all-NaN and every net cell NaN. The E-6 family -- a merge keyed "
                  "on another object's dates -- except that it produced NaN rather than silence."),
        "shipped_series_periods": int(len(shp)),
        "shipped_series_window": [str(shp["date"].min().date()), str(shp["date"].max().date())],
        "corrected_panel_dates": len(corr_dates),
        "overlap_corrected": len(set(shp["date"]) & corr_dates),
        "published_panel_dates": len(pub_dates),
        "overlap_published": (len(set(shp["date"]) & pub_dates) if pub_dates else None),
        "THE_CELL_HAS_BEEN_UNMEASURABLE_SINCE_B6": (
            "the PUBLISHED 2,531 x 69 panel shares ZERO dates with that CSV too, so R1's own "
            "net-of-cost leg could not have been measured on the published panel either. The "
            "shipped +7.85%/yr (t 5.16) is FACTOR_ALPHA_RESULTS.json's 109-period run on the "
            "VOID pre-B6 panel, which CLAUDE.md already labels void. Pre-committed in the "
            "register to be checked and reported either way."),
    }
    log("[r1cost] overlap with X4's series: corrected %d, published %s"
        % (out["diagnosis"]["overlap_corrected"], out["diagnosis"]["overlap_published"]))

    # ---- the inertness differential on the strategy_series parameter ----
    leg = EB.strategy_series(panel, dep, legacy_composite=True)
    ref = _legacy_inline(panel, dep)
    cols_cmp = ["top", "ew", "turnover", "cost_bps", "n"]
    devs = {c: float(np.max(np.abs(leg[c].values - ref[c].values))) for c in cols_cmp}
    out["controls"]["C_legacy_default_is_inert"] = {
        "rows_compared": int(len(leg)),
        "max_abs_dev_per_column": devs,
        "dates_identical": bool(list(leg["date"]) == list(ref["date"])),
        "ok": bool(len(leg) > 50 and max(devs.values()) == 0.0
                   and list(leg["date"]) == list(ref["date"])),
        "what": ("strategy_series gained legacy_composite=True; the default branch must be "
                 "bit-identical to HEAD's loop or X4's landed series would move"),
    }
    log("[C_inert] legacy default inert: %s (max dev %r)"
        % (out["controls"]["C_legacy_default_is_inert"]["ok"], max(devs.values())))

    # ---- the corrected series, both composites + the two-way sensitivity ----
    shipped = EB.strategy_series(panel, dep, legacy_composite=False)
    twoway = _two_way_series(panel, dep)
    paths = {}
    for tag, df in (("shipped", shipped), ("legacy", leg), ("twoway", twoway)):
        p = os.path.join(fa(), "CANON_UNMEASURED_R1COST_series_%s.csv" % tag)
        df.to_csv(p, index=False)
        paths[tag] = p
    out["series"] = {
        tag: {"path": paths[tag], "n_periods": int(len(df)),
              "mean_turnover": float(df["turnover"].mean()),
              "mean_cost_bps": float(df["cost_bps"].mean()),
              "implied_mean_cost_per_period": float((df["cost_bps"] / 1e4
                                                     * df["turnover"]).mean()),
              "implied_annual_one_way_turnover": float(df["turnover"].mean()
                                                       * (1.0 if tag == "twoway" else 2.0)
                                                       / 2.0 * 4.0)}
        for tag, df in (("shipped", shipped), ("legacy", leg), ("twoway", twoway))
    }

    # ---- R1's OWN path, three inputs, arithmetic untouched ----
    out["readings"] = {}
    for tag in ("shipped", "legacy", "twoway"):
        res = _run_factor_alpha(paths[tag],
                                os.path.join(fa(), "CANON_UNMEASURED_R1COST_%s.json" % tag), tag)
        if res is None:
            out["readings"][tag] = {"state": "FAILED -- see the log beside this artifact"}
            continue
        spec = ((res.get("verdict") or {}).get("primary_spec")) or "compound/full"
        gross = (((res.get("specs") or {}).get(spec) or {}).get("ff5_mom") or {}).get(
            "top_minus_ew") or {}
        nc = res.get("net_of_cost") or {}
        tme, trf = nc.get("top_minus_ew") or {}, nc.get("top_excess_rf") or {}
        gdev = {k: (None if gross.get(k) is None else abs(float(gross[k]) - v))
                for k, v in R1_LANDED_GROSS.items()}
        out["readings"][tag] = {
            "primary_spec": spec,
            "gross_alpha_ann": gross.get("alpha_ann"),
            "gross_alpha_t_nw": gross.get("alpha_t_nw"),
            "gross_reproduces_landed": bool(all(v is not None and v == 0.0
                                                for v in gdev.values())),
            "gross_dev_from_landed": gdev,
            "cost_drag_ann": nc.get("cost_drag_ann"),
            "net_top_minus_ew": {k: tme.get(k) for k in
                                 ("alpha_ann", "alpha_t_nw", "raw_ann", "n_periods", "r2")},
            "net_top_excess_rf": {k: trf.get(k) for k in
                                  ("alpha_ann", "alpha_t_nw", "raw_ann", "n_periods")},
            "clears_r1_bar": (None if tme.get("alpha_t_nw") is None else
                              bool(tme.get("alpha_ann", 0) > 0 and tme["alpha_t_nw"] > 2.0)),
            "role": {"shipped": "PRIMARY -- the shipped composite, B7's one composite",
                     "legacy": "SENSITIVITY -- the pre-B7 composite X4's own series used",
                     "twoway": "SENSITIVITY -- both trade legs charged (see _two_way_series)"}[tag],
        }
        r = out["readings"][tag]
        log("[r1cost/%s] gross %+.6f (t %+.4f, reproduces=%s) | drag %s | net %s (t %s) -> "
            "clears=%s" % (tag, r["gross_alpha_ann"] or float("nan"),
                           r["gross_alpha_t_nw"] or float("nan"), r["gross_reproduces_landed"],
                           r["cost_drag_ann"], r["net_top_minus_ew"]["alpha_ann"],
                           r["net_top_minus_ew"]["alpha_t_nw"], r["clears_r1_bar"]))

    out["reported_not_fixed"] = (
        "cost = (cost_bps/1e4) * turnover charges the one-way cost on the ENTERING side only, "
        "while fundamental_panel.turnover_and_costs charges (bps/1e4)*(n_bought+n_sold)/len(held) "
        "-- two-way. R1's leg undercharges by about 2x relative to this project's own cost "
        "model. It is R1's registered formula and is run as written; the `twoway` reading bounds "
        "the direction. Re-pointing it is a different register's business.")
    return out


# ---------------------------------------------------------------------------------------------
# REGISTER §4.1 — `P1S0` / `optionable_partition.N_PANEL_NAMES`
# ---------------------------------------------------------------------------------------------
#: the corrected panel WITH the long horizons -- the v3 rebuild, same 69 dates and 9,645 names
#: as the sweep's panel (checked, not assumed) plus `fwd_ret_h63..h504`, which `P1S0`'s 252d and
#: 504d arms cannot be scored without.
PANEL_V3_BASENAME = "UNIVERSE_BIAS_PANEL_full_v3.pkl"


def p1s0():
    """`P1S0`'s optionable partition, re-measured on the corrected grid.

    **The move table's own instruction is inherited: move the `N_PANEL_NAMES` stamp ONLY with
    its figures.** So this measures the partition and the gate, and the stamp moves only if the
    figures move with it. `P1S0`'s verdict (a both-halves failure that closed the
    options-expression family) is CARRIED, not re-decided, and `P1S0-CONTROL`'s NULL is not
    re-opened -- neither is a question this lane reopens.
    """
    import pandas as pd
    from valuation.studies.optionable_universe import (
        date_ticker_partition, coverage_report, restrict, STALE_MAX_DAYS)
    from scripts import p1s0_optionable_gate as P
    from scripts import term_structure as TS

    root = _data_root()
    v3 = os.path.join(fa(), PANEL_V3_BASENAME)
    if not os.path.exists(v3):
        raise SystemExit("REFUSING: %s is not on disk" % v3)
    panel = pd.read_pickle(v3)
    panel["date"] = pd.to_datetime(panel["date"])
    base = load_panel()

    out = {
        "item": "CANON-UNMEASURED",
        "part": "4.1 -- P1S0 / optionable_partition.N_PANEL_NAMES",
        "register": "PREREG_canonmove_unmeasured.md (ALONE at e4b0dae); construction and bars "
                    "from PREREG_p1s0_optionable_gate.md, imported not retyped",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT of an already-registered construction on a new universe",
        "weighting": "DEPLOYED -- term_structure.DEPLOYED, flat 0.125 over the seven weighted "
                     "themes, which renormalises to flat 1/7",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "p1s0_verdict_is_CARRIED_not_re_decided": (
            "P1S0 closed the options-expression family on a both-halves failure and "
            "P1S0-CONTROL returned NULL on the attribution. Neither is re-opened here; this "
            "re-measures the PARTITION the public stamp describes."),
        "controls": {},
    }

    # the v3 panel must be the SAME object the rest of the move was measured on
    out["controls"]["C_v3_is_the_same_grid"] = {
        "v3_dates": int(panel["date"].nunique()), "v3_names": int(panel["ticker"].nunique()),
        "sweep_panel_dates": int(base["date"].nunique()),
        "sweep_panel_names": int(base["ticker"].nunique()),
        "dates_identical": bool(sorted(str(x)[:10] for x in panel["date"].unique())
                                == sorted(str(x)[:10] for x in
                                          pd.to_datetime(base["date"]).unique())),
        "names_identical": bool(set(panel["ticker"]) == set(base["ticker"])),
        "horizon_cols_present": [c for c in panel.columns if c.startswith("fwd_ret_h")],
    }
    log("[C] v3 grid identical to the sweep's panel: dates=%s names=%s"
        % (out["controls"]["C_v3_is_the_same_grid"]["dates_identical"],
           out["controls"]["C_v3_is_the_same_grid"]["names_identical"]))

    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())
    counts = panel.groupby("date")["ticker"].nunique().to_dict()
    log("[p1s0] building the partition over %d names x %d dates (reads the chain cache)"
        % (len(tickers), len(dates)))
    part = date_ticker_partition(dates, tickers, data_root=root, stale_max=STALE_MAX_DAYS)
    pkl = os.path.join(fa(), "CANON_UNMEASURED_P1S0_PARTITION.pkl")
    part.to_pickle(pkl)
    cov = coverage_report(part, dates, counts)
    out["partition_pkl"] = pkl
    out["coverage"] = {k: v for k, v in cov.items() if k != "per_date"}
    out["coverage_per_date"] = cov.get("per_date")

    n_opt = int(part.loc[part["pit_liquid"] == True, "ticker"].nunique())      # noqa: E712
    n_chain = int(part["ticker"].nunique())
    out["stamp"] = {
        "N_PANEL_NAMES": {"published": 2531, "corrected": len(tickers)},
        "N_OPTIONABLE_NAMES": {"published": 619, "corrected": n_opt,
                               "mode": "pit_liquid (PRIMARY)"},
        "n_names_with_any_chain": n_chain,
        "share_of_panel_optionable": (n_opt / float(len(tickers))),
        "share_of_panel_optionable_published": 619 / 2531.0,
        "surface": "valuation/web/optionable_partition.py (committed literals)",
        "the_published_copy_says": ("'Roughly a quarter of the research panel has listed "
                                    "options' -- a DERIVED fraction, so it moves with the stamp"),
    }
    log("[p1s0] stamp: panel %d -> optionable %d (%.2f%% vs published %.2f%%)"
        % (len(tickers), n_opt, 100.0 * n_opt / len(tickers), 100.0 * 619 / 2531.0))

    # ---- the three horizon arms, the gate's own construction -------------------------------
    out["horizons"] = []
    for h in P.HORIZONS:
        row = {"horizon": h, "is_power_anchor": bool(h == P.POWER_ANCHOR),
               "in_the_frontier_gate": bool(h in P.GATE_HORIZONS)}
        for mode in P.MODES:
            rest = restrict(panel, part, mode=mode)
            ds = P.scorable_dates(rest, h)
            e, l, bnd = P.halves(ds)
            cell = {"n_scorable_dates": len(ds), "n_early": len(e), "n_late": len(l),
                    "boundary_embargoed": (str(bnd)[:10] if bnd is not None else None),
                    "n_rows": int(len(rest)), "n_names": int(rest["ticker"].nunique())}
            for lbl, dd in (("full", ds), ("early", e), ("late", l)):
                if len(dd) < 4:
                    cell[lbl] = {"status": "too few dates"}
                    continue
                a = TS.arm(rest, h, dates=dd, label="%s/%s/%s" % (mode, h, lbl))
                cell[lbl] = {k: a.get(k) for k in
                             ("n_periods", "cum_alpha", "alpha_ann", "alpha_t_hac",
                              "ls_t_hac", "monotonicity", "equal_weight_ann", "hac_lag")}
            # the FULL panel over the SAME dates -- P1S0-CONTROL's own reference leg
            if len(ds) >= 4:
                f = TS.arm(panel, h, dates=ds, label="fullpanel/%s" % h)
                cell["full_panel_same_dates"] = {k: f.get(k) for k in
                                                 ("n_periods", "cum_alpha", "alpha_ann",
                                                  "alpha_t_hac", "monotonicity")}
            row[mode] = cell
            log("[p1s0] h=%d %s: %d dates (%d/%d), alpha_ann full %s"
                % (h, mode, len(ds), len(e), len(l),
                   (cell.get("full") or {}).get("alpha_ann")))
        out["horizons"].append(row)

    out["NOT_DONE"] = [
        "the 200-draw placebo floors are NOT re-run on this universe, so no horizon here is "
        "scored against a calibrated floor and none carries a PASS/FAIL against one -- the "
        "figures are the partition's own, reported. P1S0's verdict is carried, not re-decided.",
        "P1S0-CONTROL is not re-opened and its NULL stands.",
        "the options-expression family stays CLOSED; nothing here licenses re-opening it.",
    ]
    return out


# ---------------------------------------------------------------------------------------------
# REGISTER §4.2 — `V6-B` M1, the dip-survival rate
# ---------------------------------------------------------------------------------------------
def v6b():
    """`V6-B`'s dip survival, re-measured on the corrected panel.

    **C1's GATE IS RE-POINTED, DECLARED IN THE REGISTER BEFORE THE RUN.** The corrected attempt
    went red at `[C1] reproduces the record: False` on a panel its own C2 had just certified as
    canonical, so the arms never ran. C1's RULE is kept -- the arms must be scored against the
    same object the record describes -- and only its LITERALS move, through the new
    `--expect-record` argument whose default is the published `REC` verbatim.

    **THE EXPECTED LITERALS ARE DERIVED, NOT TYPED.** They come from a fresh `quantile_backtest`
    on V6-B's own `THEMES`/`W` construction, so a drifted panel cannot be certified by a
    hand-copied number (`MA19`'s rule, and `W-1`'s fix of importing a register's own constants).
    """
    import pandas as pd
    from scripts import v6b_dip_survival as V
    from valuation.edge import fundamental_panel as FP

    root = _data_root()
    v3 = os.path.join(fa(), PANEL_V3_BASENAME)
    panel = pd.read_pickle(v3)
    expect = FP.quantile_backtest(panel, V.THEMES, {c: V.W for c in V.THEMES},
                                  n_q=10, horizon=63) or {}
    exp = {k: float(expect[k]) for k in V.REC if expect.get(k) is not None}
    # §0's control, inside the gate the gate is being re-pointed to
    ctl_dev = {k: abs(exp[k] - v) for k, v in DEPLOYED_LANDED.items() if k in exp}
    exp_path = os.path.join(fa(), "CANON_UNMEASURED_V6B_EXPECT.json")
    write(exp_path, exp)

    out_json = os.path.join(fa(), "CANON_UNMEASURED_V6B_DIP_SURVIVAL.json")
    cmd = [sys.executable, "-m", "scripts.v6b_dip_survival",
           "--data-dir", os.path.join(root, "full2009", "backtest"),
           "--bulk-dir", os.path.join(root, "bulk"),
           "--panel-cache", v3,
           "--v6-artifact", os.path.join(fa(), "V6_DIP_DETECTOR.json"),
           "--expect-record", exp_path,
           "--json", out_json]
    log("[v6b] %s" % " ".join(cmd[2:]))
    p = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True)
    logp = os.path.join(fa(), "CANON_UNMEASURED_V6B.log")
    with io.open(logp, "w", encoding="utf-8", errors="replace") as fh:
        fh.write((p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""))
    res = None
    if os.path.exists(out_json):
        with io.open(out_json, encoding="utf-8") as fh:
            res = json.load(fh)

    out = {
        "item": "CANON-UNMEASURED",
        "part": "4.2 -- V6-B M1, the dip-survival rate",
        "register": "PREREG_canonmove_unmeasured.md (ALONE at e4b0dae); bars IMPORTED from "
                    "PREREG_v6b_dip_survival.md and never restated (its void condition 6.3)",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT of an already-registered construction on a new universe",
        "weighting": "DEPLOYED -- V6-B's own THEMES at W=0.125, which renormalises to flat 1/7",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "bars_imported": {"m1_economic_floor_pp": V.M1_ECONOMIC_PP, "n_perm": V.N_PERM,
                          "min_per_side": V.MIN_PER_SIDE,
                          "min_dates_per_half": V.MIN_DATES_PER_HALF,
                          "depth": V.DEPTH, "fwd_td": V.FWD_TD,
                          "further_drop": V.FURTHER_DROP,
                          "quality_floor": V.QUALITY_FLOOR, "health_floor": V.HEALTH_FLOOR},
        "c1_repointed": {
            "published_REC": V.REC,
            "corrected_expect_DERIVED": exp,
            "dev_from_the_move_s_own_deployed_literals": ctl_dev,
            "ok": bool(ctl_dev and max(ctl_dev.values()) == 0.0),
            "why": ("the corrected attempt aborted at C1 against the PUBLISHED literals on a "
                    "panel its own C2 had certified as canonical -- a guard firing on the clock "
                    "rather than on the property it protects"),
        },
        "returncode": p.returncode,
        "log": logp,
        "published": {"healthy_pooled_rate": 0.3251, "unhealthy_pooled_rate": 0.4335,
                      "pooled_gap_pp": -10.84},
    }
    if res is None:
        out["state"] = "FAILED -- no artifact written; see the log"
        return out
    out["controls"] = res.get("controls")
    out["aborted"] = res.get("ABORTED")
    arms = res.get("arms") or {}
    out["arms"] = arms
    m1 = (((arms.get("arm1_survival") or {}).get("M1")) or {})
    out["M1"] = m1
    return out


# ---------------------------------------------------------------------------------------------
# REGISTER §4.4 — the live / forward Track Record
# ---------------------------------------------------------------------------------------------
def trackrecord():
    """**UNMEASURED-BY-CONSTRUCTION**, and the reason is structural rather than a shortfall of
    effort. Pre-committed in the register §4.4, before anything was run.

    The forward record accrues in CALENDAR time under `PAPER_TRACK_CONTRACT.md`. No backtest on
    any universe can produce it; backfilling it is forbidden by a standing security rule
    (`DECISIONS.md`: *"no backfill of the forward record"*); and the contract's frozen meter
    parameters are explicitly outside this lane. **This is a different state from every other
    row here and is labelled differently** -- the others could be measured and were; this one
    cannot be, by anyone, today.
    """
    import pandas as pd
    out = {
        "item": "CANON-UNMEASURED",
        "part": "4.4 -- the live / forward Track Record",
        "state": "UNMEASURED-BY-CONSTRUCTION",
        "trials": 0,
        "why": ("a forward record that accrues in calendar time under PAPER_TRACK_CONTRACT.md. "
                "A backtest on any universe cannot produce it, backfilling it is forbidden by a "
                "standing security rule, and the contract's frozen meter parameters are not "
                "touched by this lane. Not a shortfall of effort -- nobody can measure it today."),
        "what_WOULD_change_it": "elapsed calendar time, and nothing else",
        "the_canonical_move_does_not_touch_it": (
            "the move changes the BACKTEST's universe; the forward record is a different object "
            "with its own contract, inception and vintage clock. CANONICAL_MOVE_TABLE.md §7 "
            "already says the move does not touch the contract or the record."),
    }
    hist = os.path.join(_data_root(), "valquo_track_history.csv")
    if os.path.exists(hist):
        try:
            df = pd.read_csv(hist)
            out["recorded_series_rows_on_this_host"] = int(len(df))
            out["recorded_series_last_row"] = str(df.iloc[-1].to_dict())
            out["note"] = ("the recorded rows are READ only, to say how long the record is. No "
                           "figure from it is quoted as a verdict and nothing is written.")
        except Exception as e:                                              # noqa: BLE001
            out["recorded_series_read_error"] = repr(e)[:200]
    return out


# ---------------------------------------------------------------------------------------------
# THE SUCCESSOR ROWS, for `scripts/canon_figure_table.py` to UNION IN
# ---------------------------------------------------------------------------------------------
GROUP = "CANON-UNMEASURED successor rows (the UNMEASURED cells, measured)"


def _a(name):
    p = os.path.join(fa(), name)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _row(figure, published, corrected, state, why, surface=None, note=None):
    return {"group": GROUP, "figure": figure, "published": published, "corrected": corrected,
            "state": state, "why": why, "surface": surface, "note": note}


def table_rows():
    """The rows this item adds to `CANONICAL_FIGURE_TABLE.md`, read off the landed artifacts.

    **A MISSING ARTIFACT BECOMES AN `UNMEASURED` ROW WITH ITS REASON, never a dropped row.**
    That is the defect this lane found in the generator itself: `load()` returned `None` for a
    dead path and `if canon and before` silently dropped fifteen rows, including every public
    landing-page figure, while the run printed a cheerful count.

    **EVERY ROW IS THE DEPLOYED FLAT-1/7 BOOK** and says so, per `DECISIONS.md` 2026-10-07.
    """
    rows = []

    # ---- §1 the deployed book's PBO and Deflated Sharpe -----------------------------------
    d = _a("CANON_UNMEASURED_DEPLOYED.json")
    if not d or d.get("ABORTED"):
        rows.append(_row("Deflated Sharpe (DEPLOYED book)", 0.7863213339664521, None,
                         "UNMEASURED", "the part-1 artifact is absent or aborted on this host"))
    else:
        by = {r["statistic"]: r for r in d["rows"]}
        dsr = by["Deflated Sharpe -- DEPLOYED book (flat 1/7)"]
        rows.append(_row(
            "Deflated Sharpe (DEPLOYED book) -- was UNMEASURED",
            dsr["published"], dsr["corrected"],
            # SURVIVES means the CLAIM's relationship to its bars is unchanged: it failed the
            # conventional 0.95 and cleared its calibrated floor before, and does both now.
            ("SURVIVES" if (dsr["clears_conventional"] is False
                            and dsr["clears_calibrated_floor"] is True) else "NO LONGER HOLDS"),
            ("fails the conventional >0.95 (as the published figure did) and CLEARS the matched "
             "non-adopting placebo floor %.6f over 84 draws -- the same relationship to both "
             "bars. The published run's own cpcv.adopt was False, so 0.7863 IS the deployed "
             "book. NOT like-for-like on N (224 vs %s), which is separated in the artifact: "
             "roughly 0.040 of the 0.0655 fall is the trial counter rising and only 0.023-0.025 "
             "is the universe and grid." % (dsr["calibrated_floor"], dsr["corrected_N"])),
            surface="-- (research record only); /proof reads it from BACKTEST_RESULTS.json"))
        pbo_dep = by["PBO_NO_SELECTION -- the DEPLOYED-book analogue (NEW statistic)"]
        rows.append(_row(
            "PBO (DEPLOYED book) -- stays UNMEASURED, now with a measured reason",
            0.7333333333333333, None, "UNMEASURABLE-BY-CONSTRUCTION",
            ("Bailey-Lopez de Prado's PBO scores a SELECTION step and the deployed book selects "
             "nothing. `_pbo` never reads `adopt` or `recommend`, so cpcv.pbo is the SAME number "
             "whether or not adoption happened -- it is not 'the adopted book's PBO'. The "
             "no-selection analogue reads %s with a median OOS rank of %s of eight, and the "
             "per-scheme control proves it is a pure RANK statistic (0.0 for the three best "
             "schemes, 1.0 for the three worst), so it may NEVER be published as a probability "
             "of overfitting." % (pbo_dep["corrected"], pbo_dep["deployed_median_oos_rank"])),
            surface="-- (research record only); /proof shows it as UNMEASURED"))

    # ---- §2 X1 ----------------------------------------------------------------------------
    d = _a("CANON_UNMEASURED_X1.json")
    if not d or d.get("ABORTED"):
        rows.append(_row("X1 half-universe split (both arms)", None, None, "UNMEASURED",
                         "the X1 artifact is absent or aborted on this host"))
    else:
        for arm, label in (("A1_top_decile_alpha", "X1 A1 -- top-decile alpha, half books"),
                           ("A2_long_short_hac_t", "X1 A2 -- long-short HAC t, half books")):
            a = d[arm]
            rows.append(_row(
                "%s -- was UNMEASURED" % label,
                a["published_full_universe_value"], a["half_book_median"],
                ("SURVIVES" if a["verdict"] == "SURVIVES" else a["verdict"]),
                ("%d half books, %d of them negative; %.1f%% clear the half-universe null's p95 "
                 "(bar %.0f%%), %.1f%% of splits clear on BOTH sides (bar %.0f%%); the "
                 "stable-key primary is A=%s B=%s and both_clear=%s. Bars IMPORTED from "
                 "PREREG_r4_x1_accounting_and_universe_split.md; X7's full-universe floors are "
                 "reported beside the half-universe null and never as it."
                 % (a["n_half_books"], a["n_half_books_negative"],
                    100 * a["frac_half_books_clearing"], 100 * d["constants_imported"]
                    ["FRAC_HALFBOOKS"], 100 * a["frac_splits_both_clear"],
                    100 * d["constants_imported"]["FRAC_BOTH"],
                    a["primary_stable_key_A"], a["primary_stable_key_B"],
                    a["primary_both_clear"])),
                note="the median is of the half books, not the full-universe value"))

    # ---- §3 R1's net-of-cost --------------------------------------------------------------
    d = _a("CANON_UNMEASURED_R1COST.json")
    if not d:
        rows.append(_row("R1's NET-OF-COST specification", None, None, "UNMEASURED",
                         "the r1cost artifact is absent on this host"))
    else:
        rd = (d.get("readings") or {})
        prim = rd.get("shipped") or {}
        tw = rd.get("twoway") or {}
        rows.append(_row(
            "R1's NET-OF-COST specification (R1's OWN path) -- was UNMEASURED",
            0.0784920195105969, (prim.get("net_top_minus_ew") or {}).get("alpha_ann"),
            ("SURVIVES" if prim.get("clears_r1_bar") else "NO LONGER HOLDS"),
            ("NaN was a zero-date LEFT JOIN against X4's 110-date series; the PUBLISHED panel "
             "shares zero dates with it too, so this cell has been unmeasurable since B6 and "
             "the shipped +7.85%%/yr (t 5.16) is the VOID pre-B6 run. Fixed by supplying a "
             "corrected --strategy-series, which is what that argument is for; R1's arithmetic "
             "is untouched and its gross leg reproduces at dev 0.000e+00. Net intercept at NW t "
             "%s against R1's own bar of 2.0. CHARGING BOTH TRADE LEGS (R1's leg charges the "
             "entering side only, ~2x under this project's own cost model) it reads %s at t %s "
             "and does NOT clear."
             % ((prim.get("net_top_minus_ew") or {}).get("alpha_t_nw"),
                (tw.get("net_top_minus_ew") or {}).get("alpha_ann"),
                (tw.get("net_top_minus_ew") or {}).get("alpha_t_nw"))),
            surface="/methodology (TEMPLATE)"))

    # ---- §4.1 P1S0 ------------------------------------------------------------------------
    d = _a("CANON_UNMEASURED_P1S0.json")
    if not d:
        rows.append(_row("optionable_partition N_PANEL_NAMES / N_OPTIONABLE_NAMES", 2531, None,
                         "UNMEASURED", "the p1s0 artifact is absent on this host"))
    else:
        st = d["stamp"]
        rows.append(_row(
            "optionable_partition N_PANEL_NAMES -- was UNMEASURED",
            st["N_PANEL_NAMES"]["published"], st["N_PANEL_NAMES"]["corrected"], "RESTATEMENT",
            "the panel the stamp describes; moved only WITH its figures, as the move table "
            "instructed", surface=st["surface"]))
        rows.append(_row(
            "optionable_partition N_OPTIONABLE_NAMES (pit_liquid) -- was UNMEASURED",
            st["N_OPTIONABLE_NAMES"]["published"], st["N_OPTIONABLE_NAMES"]["corrected"],
            "RESTATEMENT",
            ("the optionable share falls from %.2f%% to %.2f%% of the panel, so the page's "
             "'roughly a quarter' is NO LONGER TRUE and is the copy that must change. P1S0's "
             "own verdict is CARRIED, not re-decided, and the options-expression family stays "
             "closed." % (100 * st["share_of_panel_optionable_published"],
                          100 * st["share_of_panel_optionable"])),
            surface=st["surface"]))

    # ---- §4.2 V6-B ------------------------------------------------------------------------
    d = _a("CANON_UNMEASURED_V6B.json")
    if not d or d.get("state") or d.get("aborted"):
        rows.append(_row("V6-B M1: 32.5% vs 43.4% dip survival", 0.3251, None, "UNMEASURED",
                         "the V6-B re-run did not produce an artifact; see "
                         "CANON_UNMEASURED_V6B.log. Its C1 gate is now re-pointable "
                         "(--expect-record), which is what blocked the previous attempt."))
    else:
        m1 = d.get("M1") or {}
        rows.append(_row(
            "V6-B M1: healthy dips fall a further 20% less often -- was UNMEASURED",
            d["published"]["healthy_pooled_rate"], m1.get("healthy_pooled_rate"),
            ("SURVIVES" if m1.get("verdict") in ("SURVIVES", "REPLICATES") else
             (m1.get("verdict") or "UNRESOLVED")),
            "bars IMPORTED from PREREG_v6b_dip_survival.md and never restated; C1 re-pointed "
            "to the corrected panel's own DERIVED figures",
            surface="CLAUDE.md V6-B bullet + Dip Detector tab (TRANSCRIBED)"))

    # ---- §4.3 S22's per-horizon floors ----------------------------------------------------
    d = _a("CANON_UNMEASURED_S22_FLOORS.json")
    pl = (d or {}).get("placebo") or {}
    fl = pl.get("floors") or {}
    if not fl:
        rows.append(_row("S22 per-horizon fixed_weights_null floors", "8 floors at 200 draws",
                         None, "UNMEASURED",
                         "the 200-draw sweep has not landed on this host"))
    else:
        draws = pl.get("draws")
        for h in sorted(fl, key=lambda x: int(x)):
            c = fl[h]
            rows.append(_row(
                "S22 fixed_weights_null floor, h=%s (alpha_t_hac p95)" % h, None,
                c.get("alpha_t_hac_p95"),
                ("RESTATEMENT" if draws and draws >= 100 else "PARTIAL"),
                ("a DIFFERENT and LESS CONSERVATIVE null than X7's -- fixed weights, no CPCV, "
                 "permuted WITHIN each date -- so these percentiles may NEVER be compared with "
                 "the 2.2837 family. %s draws; null median %s, max %s."
                 % (draws, c.get("alpha_t_hac_median"), c.get("alpha_t_hac_max"))),
                note="ls_t_hac p95 = %s" % c.get("ls_t_hac_p95")))

    # ---- §4.4 the forward Track Record ----------------------------------------------------
    d = _a("CANON_UNMEASURED_TRACKRECORD.json")
    rows.append(_row(
        "the live / forward Track Record", None, None,
        "UNMEASURED-BY-CONSTRUCTION",
        (d or {}).get("why", "a forward record that accrues in calendar time"),
        surface="Track Record tab (LIVE)",
        note="a different state from every other row: nobody can measure it today, and only "
             "elapsed calendar time changes that"))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="control",
                    choices=["control", "deployed", "inert", "x1", "r1cost", "p1s0", "v6b",
                             "trackrecord"])
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
    elif args.what == "x1":
        res = x1()
    elif args.what == "r1cost":
        res = r1cost()
    elif args.what == "p1s0":
        res = p1s0()
    elif args.what == "v6b":
        res = v6b()
    elif args.what == "trackrecord":
        res = trackrecord()
        log(json.dumps(res, indent=1, default=float))
    else:
        raise SystemExit("--what %s is implemented in its own module pass" % args.what)
    write(out_path(args.what), res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
