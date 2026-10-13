# -*- coding: utf-8 -*-
"""`DECISION_canonical_move.md` steps 5 and 6 -- ONE table, every public figure, old -> new.

Addendum 1: *"hand the app fixer a single table of every public figure old -> new with where each
lives."* This builds it, and it builds it by **UNION of the artifacts that already measured each
figure** rather than by re-deriving anything -- re-deriving a landed figure in a third place is
how two numbers for one question come about (`B7`), and every row here already carries its own
register's verdict.

Sources, each already landed by this lane:

* `CORRECTED_CLAIMS.json`           -- part 1's eleven claims
* `CORRECTED_CLAIMS2_VERDICT.json`  -- part 2's fourteen (S22, hold_horizon, score_confidence,
                                       V6-B, R1 net-of-cost)
* `CORRECTED_FLOORS.json`           -- the seven calibrated floors
* `INDEX_BOOK_THREE_WAY.json`       -- the Index book's published / restricted / corrected columns
* the canonical `BACKTEST_RESULTS.json` -- the headline blocks

**THE THREE-STATE VOCABULARY IS CARRIED, NOT RE-DECIDED.** A row's `state` is whatever its own
register recorded. `UNMEASURED` rows keep their reason, because a row that cannot say why it is
unmeasured is indistinguishable from one nobody looked at.

**AND EVERY ROW NAMES ITS WEIGHTING.** Every figure is the DEPLOYED book (flat 1/7). Part 1b is
why that label is load-bearing rather than decorative: on this universe CPCV adopts
`ic-proportional`, and the adopted book's top-decile alpha is 2.83% against the deployed 6.07%.
"""
import io
import json
import os
import subprocess
import sys

# EVERY PATH IS DERIVED. **CANON-UNMEASURED: ALL THREE OF THIS FILE'S HARD-CODED PATHS WERE
# DEAD, AND THE FAILURE MODE WAS SILENT ROW LOSS.** They were `.claude/worktrees/r1b` (which no
# longer holds a `BACKTEST_RESULTS.json`) and a job scratch directory (`jobs/2f90bb74/tmp/canon`,
# since cleaned up). `load()` returns `None` for an absent file and the
# `BACKTEST_RESULTS.json` block is guarded by `if canon and before`, so regenerating the table
# today would have dropped **15 rows including every PUBLIC landing-page figure** -- and printed
# a cheerful row count. A generated file whose generator silently shrinks is worse than a
# hand-edited one, because nothing says the table got smaller.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.index_best import _data_root                                   # noqa: E402


#: THE COMMIT THAT SWAPPED THE TRACKED ARTIFACT. The "published" column is the pre-swap tracked
#: `BACKTEST_RESULTS.json`, read from GIT rather than from a scratch copy -- so it is
#: reproducible by anyone holding the repo and cannot rot when a job directory is cleaned up.
#: Item 47, "the canonical move reaches the public pages".
ARTIFACT_SWAP_COMMIT = "60871ac"

#: THE MARKDOWN GOES IN THE REPO, because addendum 1 asks for *"a single table ... handed to the
#: app fixer"* and a table in a gitignored scratch directory is not handed to anyone. The JSON
#: stays out of the repo: it is a research artifact and `data/` is where those live.
OUT_MD = os.path.join(_HERE, "CANONICAL_FIGURE_TABLE.md")



def fa():
    """`data/free_analysis`, resolved on CALL.

    **NOT AT IMPORT TIME.** `_data_root` RAISES without the banked panel and `data/` is
    gitignored, so a module-level call takes down every suite that imports this file on a CI
    runner. `scripts/corrected_floors.py`'s docstring says exactly this and I wrote the
    module-level version anyway; the suite caught it in CI, not locally.
    """
    return os.path.join(_data_root(), "free_analysis")


def out_json():
    return os.path.join(fa(), "CANONICAL_FIGURE_TABLE.json")

def load(name, root=None):
    p = os.path.join(root or fa(), name)
    if not os.path.exists(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def load_published_artifact():
    """The pre-swap tracked `BACKTEST_RESULTS.json`, from git. REFUSES rather than returning
    `None`: a missing "published" column is exactly the silent row loss this file just paid
    for, and a loud failure is the safe direction."""
    rev = "%s^:BACKTEST_RESULTS.json" % ARTIFACT_SWAP_COMMIT
    p = subprocess.run(["git", "-C", _HERE, "show", rev], capture_output=True)
    if p.returncode != 0:
        raise SystemExit("REFUSING: cannot read %s from git (%s). The published column would "
                         "be silently absent and 15 rows would vanish."
                         % (rev, (p.stderr or b"")[-300:]))
    return json.loads(p.stdout.decode("utf-8"))


def fmt(v):
    if isinstance(v, bool) or v is None:
        return repr(v)
    if isinstance(v, float):
        return "%.6f" % v
    if isinstance(v, (dict, list)):
        return json.dumps(v)[:120]
    return str(v)


def g(doc, *path):
    cur = doc
    for p in path:
        cur = (cur or {}).get(p) if isinstance(cur, dict) else None
    return cur


# ------------------------------------------------- SUPERSEDED POINTERS, and why they are needed
# **SIX ROWS READ `UNMEASURED` WHILE A LATER ROW IN THIS SAME TABLE CARRIES THE ANSWER.** Three
# of `CORRECTED-CLAIMS part 1`'s six unmeasured cells were measured by `CORRECTED-CLAIMS-2`, and
# three of `CORRECTED-CLAIMS-2`'s were measured by `CANON-UNMEASURED` -- and nothing said so, so
# a reader of the earlier group alone would conclude nobody had looked.
#
# **THE STATE IS NOT RE-DECIDED** (this file's own carry rule): the row keeps whatever its own
# register recorded, and gains a POINTER. The pointer is an explicit pair rather than a string
# match, because the two groups phrase the same figure differently, and
# `tests/test_canon_unmeasured.py` fails if a target no longer exists -- a pointer that can rot
# is the defect one level up.
SUPERSEDED_BY = [
    ("CORRECTED-CLAIMS part 1", "R1's NET-OF-COST specification",
     ["R1 net-of-cost intercept (R1's OWN path)",
      "R1's NET-OF-COST specification (R1's OWN path) -- was UNMEASURED"]),
    ("CORRECTED-CLAIMS part 1", "t never below 3.16, 3.83 at two years (S22 term structure)",
     ["S22 'alpha HAC t never below 3.16' (LITERAL)", "S22 two-year alpha HAC t"]),
    ("CORRECTED-CLAIMS part 1",
     "beat the universe by 6.6% at one quarter, 5.1% at two years (hold horizon)",
     ["hold_horizon copy: 1-quarter annualized alpha",
      "hold_horizon copy: 2-year annualized alpha"]),
    ("CORRECTED-CLAIMS part 1", "holds on 45 of 69 / 21 of 69 dates (score calibration)",
     ["score_confidence PER_NAME_DATES", "score_confidence GROUP_DATES (the limitation)"]),
    ("CORRECTED-CLAIMS part 1", "32.5% vs 43.4% dip survival (V6-B)",
     ["V6-B M1: 32.5% vs 43.4% dip survival (the POOLED pair, LITERAL)",
      "V6-B M1 SUBSTANCE: healthy dips fall a further 20% less often"]),
    ("CORRECTED-CLAIMS-2", "V6-B M1: healthy dips fall a further 20% less often",
     ["V6-B M1 SUBSTANCE: healthy dips fall a further 20% less often",
      "V6-B M1 registered per-date statistic -- was UNMEASURED"]),
    ("CORRECTED-CLAIMS-2", "S22 per-horizon fixed_weights_null floors",
     ["S22 fixed_weights_null floor, h=63 (alpha_t_hac p95)"]),
    ("CORRECTED-CLAIMS-2", "R1 net-of-cost intercept (R1's OWN path)",
     ["R1's NET-OF-COST specification (R1's OWN path) -- was UNMEASURED"]),
]


def build():
    """Build the table. **A FUNCTION, so importing this module runs NOTHING** --
    see `fa()`. Importing it used to resolve the data root and then OVERWRITE the
    tracked markdown, which would turn a CI crash into a silent truncation."""
    rows = []

    # ------------------------------------------------------------------ parts 1 and 2, carried whole
    for src, art in (("CORRECTED-CLAIMS part 1", load("CORRECTED_CLAIMS.json")),
                     ("CORRECTED-CLAIMS-2", load("CORRECTED_CLAIMS2_VERDICT.json"))):
        if not art:
            rows.append({"group": src, "figure": "(artifact absent)", "state": "UNMEASURED",
                         "why": "artifact not on this host"})
            continue
        for c in art.get("claims") or []:
            rows.append({
                "group": src,
                "figure": c.get("claim"),
                "published": c.get("published"),
                "corrected": c.get("corrected"),
                "state": c.get("state"),
                "why": c.get("why"),
                "surface": c.get("surface"),
                "note": c.get("note"),
            })

    # ---------------------------------------------------------------------------------- the floors
    fl = load("CORRECTED_FLOORS.json")
    if fl:
        for f in fl.get("floors") or []:
            rows.append({
                "group": "calibrated floors (X7's sweep, re-run on this universe)",
                "figure": "%s floor (%s)" % (f.get("floor"), f.get("percentile")),
                "published": f.get("current"),
                "corrected": f.get("corrected"),
                "state": ("SURVIVES" if f.get("headline_clears_corrected_floor")
                          else "NO LONGER HOLDS"),
                "surface": ("valuation/web/research_record.py PLACEBO_FLOOR"
                            if f.get("key") == "long_short_tstat_nw" else None),
                "note": ("HARDER on the corrected universe" if f.get("harder")
                         else "easier on the corrected universe"),
            })

    # ------------------------------------------------------------------------------- the Index book
    tw = load("INDEX_BOOK_THREE_WAY.json")
    if tw:
        for r in tw.get("served_arm_table") or []:
            if not isinstance(r, dict):
                continue
            rows.append({
                "group": "Index book (served construction)",
                "figure": r.get("metric") or r.get("name") or r.get("key"),
                "published": r.get("published"),
                "corrected": r.get("corrected"),
                "restricted": r.get("restricted"),
                "state": ("RESTATEMENT" if r.get("published") != r.get("corrected")
                          else "SURVIVES"),
                "surface": "valuation/screener/index_book_measured.py (committed literals)",
                "note": "the RESTRICTED column separates newer data from wider universe",
            })

    # --------------------------------------------------------------------- the canonical headlines
    canon = load("BACKTEST_RESULTS.json", root=_HERE)
    before = load_published_artifact()
    if not canon:
        raise SystemExit("REFUSING: no tracked BACKTEST_RESULTS.json at %s -- the corrected column "
                         "would be silently absent and 15 rows would vanish." % _HERE)
    if canon and before:
        for label, path, surface in (
            ("top-decile alpha (annualised)", ("construction", "top_decile_alpha"), None),
            ("long-short t (naive)", ("construction", "long_short_tstat"), None),
            ("long-short t (HAC) -- THE HEADLINE",
             ("construction", "long_short_tstat_nw"),
             "valuation/web/research_record.py HEADLINE_STATISTIC"),
            ("top-decile alpha t (HAC)", ("construction", "top_decile_alpha_tstat_nw"), None),
            ("monotonicity", ("construction", "monotonicity"), None),
            # PBO and the Deflated Sharpe ship as {value, want, meaning} dicts -- the FIGURE is one
            # level down. And the hurdle key is `multiple_testing.hlz.hurdle_sqrt_2_ln_N`, not
            # `hlz_hurdle`: a wrong path here does not raise, it returns None on BOTH sides and
            # reads as "unchanged".
            #
            # ** AND THESE TWO DESCRIBE A DIFFERENT BOOK FROM EVERY OTHER ROW IN THIS GROUP. **
            # `cpcv_validate` scores whichever scheme adoption chose, and on this universe CPCV
            # ADOPTED `ic-proportional`. So `construction.*` above is the DEPLOYED book and
            # `cpcv.*` is the ADOPTED one -- see the note in the table.
            ("PBO (ADOPTED book)", ("cpcv", "pbo", "value"), None),
            ("Deflated Sharpe (ADOPTED book)", ("cpcv", "deflated_sharpe", "value"), None),
            ("HLZ hurdle sqrt(2 ln N)", ("multiple_testing", "hlz", "hurdle_sqrt_2_ln_N"), None),
            ("HLZ: clears the hurdle?", ("multiple_testing", "hlz", "clears_hlz_hurdle"), None),
            ("trials, equity", ("multiple_testing", "by_domain", "equity"), None),
            ("universe n_names", ("universe", "n_names"), None),
            ("universe n_dates", ("universe", "n_dates"), None),
            ("book_configs.roth.net_alpha (PUBLIC: landing page)",
             ("book_configs", "roth", "net_alpha"),
             "valuation/screener/settings.py measured() -> index_track.backtested"),
            ("book_configs.roth.net_max_drawdown (PUBLIC)",
             ("book_configs", "roth", "net_max_drawdown"),
             "valuation/screener/settings.py measured()"),
            ("book_configs.taxable.after_tax_alpha (PUBLIC)",
             ("book_configs", "taxable", "after_tax_alpha"),
             "valuation/screener/settings.py measured()"),
        ):
            o, n = g(before, *path), g(canon, *path)
            rows.append({
                "group": "BACKTEST_RESULTS.json (canonical, DEPLOYED book)",
                "figure": label,
                "published": o,
                "corrected": n,
                "state": ("SURVIVES" if o == n else "RESTATEMENT"),
                "surface": surface,
                "note": "the headline is the DEPLOYED flat 1/7 book (step 1)",
            })

    # ----------------------------------------------- CANON-UNMEASURED's successor rows, UNIONED IN
    # The cells this table marked UNMEASURED, measured. Read off that item's own landed artifacts by
    # its own `table_rows()` -- the union discipline this file's docstring sets out, so a figure is
    # never re-derived in a third place (`B7`). A missing artifact becomes an UNMEASURED row WITH
    # ITS REASON rather than a dropped one.
    try:
        from scripts.canon_unmeasured import table_rows as _succ
        rows += _succ()
    except Exception as _e:                                                     # noqa: BLE001
        rows.append({"group": "CANON-UNMEASURED successor rows (the UNMEASURED cells, measured)",
                     "figure": "(successor rows unavailable)", "state": "UNMEASURED",
                     "why": "scripts.canon_unmeasured.table_rows() raised: %r" % (_e,)})

    _fig = {}
    for r in rows:
        _fig.setdefault(str(r.get("figure")), []).append(r)
    for grp, fig, targets in SUPERSEDED_BY:
        src = [r for r in rows if r.get("group") == grp and str(r.get("figure")) == fig]
        live = [t for t in targets if t in _fig]
        for r in src:
            if not live:
                r["note"] = ((r.get("note") or "") + " · no successor row has landed yet.").strip()
                continue
            r["superseded_by"] = live
            r["note"] = ((r.get("note") or "")
                         + " · SUPERSEDED — the answer is in this table, at: "
                         + "; ".join(live)).strip()

    res = {
        "item": "CANONICAL-MOVE",
        "part": "steps 5 and 6 -- every public figure, old -> new, with where it lives",
        "trials": 0,
        "trial_class": "CONSOLIDATION -- a union of landed artifacts. No hypothesis, no bar, no arm, "
                       "no new outcome statistic.",
        "weighting": "DEPLOYED (flat 1/7) on every row; CPCV is never the headline (step 1)",
        "sources": ["CORRECTED_CLAIMS.json", "CORRECTED_CLAIMS2_VERDICT.json",
                    "CORRECTED_FLOORS.json", "INDEX_BOOK_THREE_WAY.json", "BACKTEST_RESULTS.json",
                    "the pre-swap BACKTEST_RESULTS.json, from git at %s^" % ARTIFACT_SWAP_COMMIT,
                    "CANON_UNMEASURED_*.json (the successor rows)"],
        "n_rows": len(rows),
        "rows": rows,
    }
    by_state = {}
    for r in rows:
        by_state[r.get("state")] = by_state.get(r.get("state"), 0) + 1
    res["tally"] = by_state

    io.open(out_json(), "w", encoding="utf-8").write(json.dumps(res, indent=1))

    # ---------------------------------------------------------------------------- the markdown table
    md = ["# The canonical move — every public figure, old → new",
          "",
          "**For the app-fixer lane.** Generated by `scripts/canon_figure_table.py`; do not hand-edit.",
          "Sources are named at the bottom. Full reasoning: `DECISION_canonical_move.md`.",
          "",
          "**Weighting: the DEPLOYED book (flat 1/7) on every row.** Step 1 made that the canonical",
          "headline, and on this universe it is load-bearing rather than decorative: **CPCV ADOPTED",
          "`ic-proportional`** (median out-of-sample IC +0.096 against the default's +0.057, positive",
          "in 100% of 15 paths), and the adopted book's top-decile alpha is **2.83%** against the",
          "deployed **6.07%**. Without step 1 the canonical headline would have re-pointed to a book",
          "nobody runs — and it would have flattered DOWNWARD.",
          "",
          "**Every row's state is its own register's verdict, carried rather than re-decided.**",
          "",
          "---",
          "",
          "## THE CAVEAT THAT BOUNDS EVERY ROW BELOW: the two panels share ZERO rebalance dates",
          "",
          "| | published | corrected |",
          "|---|---|---|",
          "| names | 2,531 | 9,645 |",
          "| rebalance dates | 69 | 69 |",
          "| first / last | 2009-01-15 / 2026-01-28 | 2009-03-27 / 2026-04-09 |",
          "| **dates in common** | — | **0** |",
          "",
          "The grid is derived from the universe's own trading calendar, so a 3.8× wider universe",
          "shifts every date. **`X2` measured the grid ALONE moving the long-short *t* by 0.81**",
          "(2.703–3.517 across seven equally valid offsets on one universe). So every `RESTATEMENT`",
          "below is a restatement under a universe change **and** a grid change, and the two are not",
          "separated. The corrected figure is still the right figure for the corrected panel — what",
          "is unattributable is *why* it moved, not *what* it is.",
          "",
          "**The measurement itself is controlled:** all seven of `CORRECTED-FLOORS` part 1b's",
          "independently landed deployed statistics reproduce in the canonical file at",
          "**|dev| 0.000e+00** on the same 9,645 names, by a different call path.",
          "",
          "---",
          "",
          "## READ THIS FIRST — what changes on the PUBLIC SITE, with no app-lane edit",
          "",
          "`BACKTEST_RESULTS.json` is **tracked**, ships in the deploy image, and",
          "`settings.measured()` reads it **at request time** → `index_track.backtested` → the",
          "landing page's *\"Backtested net alpha\"*. So these three move on the next deploy by",
          "themselves:",
          "",
          "| public figure | published | corrected |",
          "|---|---|---|",
          "| `book_configs.roth.net_alpha` | **+11.63%/yr** | **−4.70%/yr** |",
          "| `book_configs.roth.net_max_drawdown` | −26.2% | **−59.7%** |",
          "| `book_configs.taxable.after_tax_alpha` | +2.11% | **−0.57%** |",
          "",
          "**A sign flip on the headline number a visitor sees.** The direction is coherent —",
          "`roth` is a concentrated **top-25** book, and top-25-of-9,645 is the top 0.26% of a",
          "universe whose ~7,100 added names are overwhelmingly small, which is exactly where",
          "`UNIVERSE-BIAS` and `TIERED-POOL` measured that reaching down the cap scale does not pay.",
          "**It is Don's call whether this ships**; `DECISION_canonical_move.md` §8.9 states the",
          "three options and this lane's recommendation (report the `$10B` Index book, which is the",
          "book a visitor can actually buy, rather than the all-cap top-25 `roth` config).",
          "",
          "**And one result in the other direction:** the headline long-short HAC *t* now **clears",
          "the Harvey-Liu-Zhu hurdle** for the first time — 4.5945 against √(2·ln 285) = 3.3623,",
          "where the published 2.6199 fell short of 3.2899. It clears the corrected placebo floor",
          "too, so both bars pass at once. **Not a new result** — the same composite on a wider",
          "universe and a disjoint grid.",
          ""]
    groups = []
    for r in rows:
        if r["group"] not in groups:
            groups.append(r["group"])
    for grp in groups:
        md += ["## %s" % grp, "",
               "| figure | published | corrected | state | where it lives |",
               "|---|---|---|---|---|"]
        for r in rows:
            if r["group"] != grp:
                continue
            # THE SUPERSESSION MUST REACH THE MARKDOWN, not only the JSON. The markdown is the file
            # handed to the app fixer, and a bare `UNMEASURED` on a figure this very table answers
            # three groups further down is the misreading this annotation exists to remove.
            state = r.get("state")
            where = (r.get("surface") or "-- (research record only)")
            if r.get("superseded_by"):
                state = "%s -> SUPERSEDED" % state
                where = "%s -- ANSWERED BELOW at: %s" % (where, "; ".join(r["superseded_by"]))
            md.append("| %s | %s | %s | **%s** | %s |"
                      % (str(r.get("figure"))[:78].replace("|", "\\|"),
                         fmt(r.get("published")).replace("|", "\\|"),
                         fmt(r.get("corrected")).replace("|", "\\|"),
                         state,
                         where.replace("|", "\\|")))
        md.append("")
    md += ["---", "", "## Sources — every figure is read from a landed artifact, none re-derived here",
           ""] + ["* `%s`" % x for x in res["sources"]]
    io.open(OUT_MD, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")

    print("rows %d | tally %r" % (len(rows), by_state))
    print("-> %s" % out_json())
    print("-> %s" % OUT_MD)


if __name__ == "__main__":
    build()
