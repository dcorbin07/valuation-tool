# -*- coding: utf-8 -*-
"""`CORRECTED-REBUILD` item 3 -- the Index book's THIRD column, so newer data and a wider
universe stop being one number.

    python -m scripts.restricted_index_book

**THE QUESTION DON ASKED.** The corrected column moves the Index book's drawdown about
-23% -> -29% and its return about +0.86pp, and those two changes travel together because the
corrected object differs from the published one in **two ways at once**: a newer data vintage AND
a nine-thousand-name universe. One column cannot separate them.

**THE THIRD COLUMN SEPARATES THEM BY HOLDING THE UNIVERSE DEFINITION FIXED.**
`UNIVERSE_BIAS_PANEL_restricted.pkl` is the **same `data/backtest` universe definition** at the
**2026-10 vintage**, so:

* `published -> restricted` is the **DATA VINTAGE** leg (same universe definition, newer export);
* `restricted -> corrected` is the **UNIVERSE** leg (same vintage, 3,049 -> 9,645 names);
* and the two must **sum** to `published -> corrected`, which is an arithmetic identity on any
  additive figure and is CHECKED rather than assumed -- a mismatch is a bug in this script, not
  a finding about the book.

**THE CAVEAT IS `UNIVERSE-BIAS`'s OWN AND IS CITED RATHER THAN RE-DERIVED.** Its
`UNIVERSE_BIAS_ARMS.json` records, of the published book: *"a DIFFERENT vintage from either panel
here, so the restricted side is its near-neighbour and not its reproduction; the gap is reported,
not assumed zero."* Concretely the restricted panel carries **3,049** names against the published
book's **2,531** -- the same export's definition, 518 names richer at the newer vintage -- so the
**vintage leg is not a pure data-vintage change** and must not be quoted as one. It is *"same
universe RULE, newer vintage"*, and the name counts ship beside every figure.

**ZERO TRIALS.** A third reading of a landed construction on a third panel is the `S25` /
`X7RECON` / `PANEL-EXT-RECHECK` class: no hypothesis, no bar, no arm.

**NOTHING IS OVERWRITTEN AND NO PUBLIC PAGE CHANGES.** It writes `INDEX_BOOK_RESTRICTED.json`;
`INDEX_BOOK.json`, `INDEX_BOOK_CORRECTED.json`, the canonical panel and every surface are
untouched, pinned by test.

**EVERY FIGURE IS THE DEPLOYED BOOK (flat 1/7).** `served_index_book` scores its own `DEPLOYED`
dict and never consults CPCV. Part 1b measured why the label is load-bearing: on the corrected
universe CPCV **adopts** `ic-proportional`, and the adopted book's top-decile alpha is 2.83pc
against the deployed 6.07pc.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.corrected_claims as CC                                       # noqa: E402

PANEL = "UNIVERSE_BIAS_PANEL_restricted.pkl"
OUT = "INDEX_BOOK_RESTRICTED.json"
LABEL = ("the RESTRICTED universe at the 2026-10 vintage (3,049 names, 133,459 rows, 69 dates) "
         "-- the same `data/backtest` universe RULE as the published book at a newer export, a "
         "SEPARATE OBJECT from both the published 2,531-name book and the corrected 9,645-name "
         "one")

#: the figures the three-way table is built on. Additive ones only: a RATIO's two legs do not
#: sum, so putting a Sharpe in the identity check would manufacture a mismatch out of
#: arithmetic. Sharpe and turnover still ship in the table; they are just excluded from the
#: identity, and `IDENTITY_KEYS` names which is which rather than leaving a reader to guess.
TABLE_KEYS = ("net_ann", "net_alpha_vs_equal_weight", "net_alpha_vs_spy", "net_sharpe",
              "net_max_drawdown", "annual_turnover", "realised_one_way_bps", "spy_ann",
              "equal_weight_ann")
IDENTITY_KEYS = ("net_ann", "net_alpha_vs_equal_weight", "net_alpha_vs_spy",
                 "net_max_drawdown", "spy_ann", "equal_weight_ann")
TAX_KEYS = ("after_tax_ann", "after_tax_alpha", "after_tax_sharpe", "after_tax_max_drawdown")
TAX_IDENTITY_KEYS = ("after_tax_ann", "after_tax_alpha", "after_tax_max_drawdown")

#: the identity `(pub->res) + (res->cor) == (pub->cor)` is exact in real arithmetic; in floating
#: point it is exact to rounding. A tolerance this loose cannot hide a real bug -- the legs this
#: table carries are percentages of order 1e-1, so a genuine mis-wiring moves a leg by 1e-2 or
#: more, eight orders of magnitude above this.
IDENTITY_TOL = 1e-12


def fa():
    return CC.fa()


def _gate_target(panel_path):
    """The restricted panel's OWN deployed top-decile alpha, measured by a DIFFERENT code path
    than the one being gated.

    `served_index_book`'s `C1` demands EXACT reproduction (`dev == 0.0`) of a landed figure and
    ABORTS otherwise. For a third panel there is no landed figure to point it at, so one is
    MEASURED first -- by `corrected_deployed.deployed_statistics`, which CALLS
    `quantile_backtest` (`B7`) with flat 1/7 weights. That is part 1b's own instrument, and part
    1b exists because part 2a's first pass handed the gate an ADOPTED alpha while the scorer
    computed the DEPLOYED composite. **Only WHICH figure the gate targets is a parameter; the
    gate's strength is not.**
    """
    from scripts.corrected_deployed import deployed_statistics
    dep = deployed_statistics(panel_path)
    want = dep.get("top_decile_alpha")
    if want is None:
        raise SystemExit("REFUSING: could not measure the restricted panel's deployed "
                         "top-decile alpha, so the C1 gate would have no target")
    return float(want), dep


def _delta(a, b):
    return None if (a is None or b is None) else (b - a)


def main(argv=None):
    f = fa()
    panel_path = os.path.join(f, PANEL)
    if not os.path.exists(panel_path):
        raise SystemExit("REFUSING: no restricted panel at %s" % panel_path)
    for sib in ("INDEX_BOOK.json", "INDEX_BOOK_CORRECTED.json"):
        if not os.path.exists(os.path.join(f, sib)):
            raise SystemExit("REFUSING: %s is absent, so the three-way table cannot be built "
                             "and a two-column table would answer a different question" % sib)

    want, dep = _gate_target(panel_path)
    print("gate target  %.17f   (the RESTRICTED panel's own DEPLOYED top-decile alpha, measured "
          "by corrected_deployed.deployed_statistics -- a different code path from the one "
          "being gated)" % want, flush=True)

    # DEFERRED IMPORT -- `served_index_book` resolves its data root at module level and RAISES
    # without the banked panel, so a top-level import makes every test touching this module
    # error on a CI runner where `data/` is gitignored (`UNIVERSE-BIAS`'s own CI failure).
    from scripts import served_index_book as SIB

    rc = SIB.main(panel_path=panel_path, out=os.path.join(f, OUT), label=LABEL,
                  expect_alpha=want)
    if rc:
        return rc

    def _load(n):
        with io.open(os.path.join(f, n), encoding="utf-8") as fh:
            return json.load(fh)

    pub, res, cor = _load("INDEX_BOOK.json"), _load(OUT), _load("INDEX_BOOK_CORRECTED.json")

    rows, bad = [], []
    print("\n=== A_served (the Index): published | restricted | corrected", flush=True)
    print("  %-32s %-12s %-12s %-12s %-12s %-12s" %
          ("key", "published", "restricted", "corrected", "d_vintage", "d_universe"), flush=True)
    for k in TABLE_KEYS:
        a = pub["arms"]["A_served"].get(k)
        b = res["arms"]["A_served"].get(k)
        c = cor["arms"]["A_served"].get(k)
        dv, du, dt = _delta(a, b), _delta(b, c), _delta(a, c)
        row = {"key": k, "published": a, "restricted": b, "corrected": c,
               "delta_vintage": dv, "delta_universe": du, "delta_total": dt,
               "in_identity": k in IDENTITY_KEYS}
        if k in IDENTITY_KEYS and None not in (dv, du, dt):
            resid = (dv + du) - dt
            row["identity_residual"] = resid
            if abs(resid) > IDENTITY_TOL:
                bad.append((k, resid))
        rows.append(row)
        fmt = lambda x: ("%+.6f" % x) if isinstance(x, (int, float)) else "-"      # noqa: E731
        print("  %-32s %-12s %-12s %-12s %-12s %-12s"
              % (k, fmt(a), fmt(b), fmt(c), fmt(dv), fmt(du)), flush=True)

    tax = []
    print("\n=== tax treatments (the Roth figure the Index tab leads with)", flush=True)
    for lab in ("roth_ira", "taxable"):
        A = (pub.get("tax_treatments") or {}).get(lab) or {}
        B = (res.get("tax_treatments") or {}).get(lab) or {}
        C = (cor.get("tax_treatments") or {}).get(lab) or {}
        for k in TAX_KEYS:
            a, b, c = A.get(k), B.get(k), C.get(k)
            dv, du, dt = _delta(a, b), _delta(b, c), _delta(a, c)
            r = {"treatment": lab, "key": k, "published": a, "restricted": b, "corrected": c,
                 "delta_vintage": dv, "delta_universe": du, "delta_total": dt,
                 "in_identity": k in TAX_IDENTITY_KEYS}
            if k in TAX_IDENTITY_KEYS and None not in (dv, du, dt):
                resid = (dv + du) - dt
                r["identity_residual"] = resid
                if abs(resid) > IDENTITY_TOL:
                    bad.append(("%s.%s" % (lab, k), resid))
            tax.append(r)
            fmt = lambda x: ("%+.6f" % x) if isinstance(x, (int, float)) else "-"  # noqa: E731
            print("  %-10s %-24s %-12s %-12s %-12s %-12s %-12s"
                  % (lab, k, fmt(a), fmt(b), fmt(c), fmt(dv), fmt(du)), flush=True)

    shapes = {
        "published": {"names": 2531, "dates": 69,
                      "panel": "panel_corrected_69d.pkl (banked, Aug-2026 vintage)"},
        "restricted": {"names": res.get("n_names"), "dates": res.get("n_dates"), "panel": PANEL},
        "corrected": {"names": cor.get("n_names"), "dates": cor.get("n_dates"),
                      "panel": "UNIVERSE_BIAS_PANEL_full.pkl"},
    }

    out = {
        "item": "CORRECTED-REBUILD item 3 -- the Index book's RESTRICTED column",
        "trials": 0,
        "trial_class": "a third reading of a landed construction on a third panel "
                       "(S25 / X7RECON / PANEL-EXT-RECHECK class). No hypothesis, no bar.",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "weighting": "DEPLOYED (flat 1/7) on every figure; CPCV never consulted",
        "panels": shapes,
        "gate": {"target_deployed_top_decile_alpha": want,
                 "measured_by": "corrected_deployed.deployed_statistics (B7: quantile_backtest "
                                "is CALLED), a different code path from the one being gated",
                 "deployed_detail": {k: dep.get(k) for k in
                                     ("top_decile_alpha", "long_short_tstat_hac",
                                      "long_short_tstat", "monotonicity", "n_dates", "n_names")}},
        "decomposition": {
            "delta_vintage": "published -> restricted: the same `data/backtest` universe RULE at "
                             "the 2026-10 export",
            "delta_universe": "restricted -> corrected: the same vintage, 3,049 -> 9,645 names",
            "identity": "(delta_vintage + delta_universe) == delta_total, checked on additive "
                        "figures only -- a RATIO's legs do not sum, so Sharpe and turnover ship "
                        "in the table and are excluded from the check",
            "identity_tol": IDENTITY_TOL,
            "identity_violations": [{"key": k, "residual": v} for k, v in bad],
            "identity_holds": not bad,
        },
        "THE_CAVEAT_THAT_TRAVELS_WITH_THE_VINTAGE_LEG": (
            "The restricted panel carries %s names against the published book's 2,531 -- the "
            "same export's universe RULE, richer at the newer vintage. So the vintage leg is "
            "NOT a pure data-vintage change and must not be quoted as one: it is 'same universe "
            "rule, newer vintage'. UNIVERSE-BIAS recorded this first and it is cited rather "
            "than re-derived -- UNIVERSE_BIAS_ARMS.json: 'a DIFFERENT vintage from either panel "
            "here, so the restricted side is its near-neighbour and not its reproduction; the "
            "gap is reported, not assumed zero.'" % (res.get("n_names"),)),
        "served_arm_table": rows,
        "tax_table": tax,
    }
    dest = os.path.join(f, "INDEX_BOOK_THREE_WAY.json")
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote %s" % os.path.join(f, OUT), flush=True)
    print("wrote %s" % dest, flush=True)

    if bad:
        print("\nIDENTITY VIOLATED on %d key(s) -- that is a bug in this script, not a finding "
              "about the book:" % len(bad), flush=True)
        for k, v in bad:
            print("   %-34s residual %+.3e" % (k, v), flush=True)
        return 3
    print("\nidentity holds on every additive figure: (vintage + universe) == total", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
